bl_info = {
    "name": "Ejecutor de Configuración de Plano/Cámara",
    "author": "Kebyn Pipeline",
    "version": (2, 4, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Plano Generador",
    "description": "Ejecuta un archivo .py de configuración que crea la cámara "
                   "y uno o más planos-filtro asociados (todos paralelos entre "
                   "sí, a distinta distancia), con ancho/alto/distancia/"
                   "intensidad (brillo + opacidad) editables.",
    "category": "Add Mesh",
}

import bpy
import bmesh
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import StringProperty, FloatProperty, PointerProperty
from bpy_extras.io_utils import ImportHelper, ExportHelper


# =============================================================================
#   UTILIDADES
# =============================================================================

def _reconstruir_malla_plano(obj, width, height):
    """Reconstruye la malla del plano activo con nuevas dimensiones,
    manteniendo UVs 0-1."""
    hw, hh = width / 2.0, height / 2.0
    verts = [(-hw, -hh, 0.0), (hw, -hh, 0.0), (hw, hh, 0.0), (-hw, hh, 0.0)]

    mesh = obj.data
    mesh.clear_geometry()

    bm = bmesh.new()
    bm_verts = [bm.verts.new(v) for v in verts]
    bm.verts.ensure_lookup_table()
    face = bm.faces.new(bm_verts)
    bm.normal_update()

    uv_layer = bm.loops.layers.uv.verify()
    uv_coords = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    for loop, uv in zip(face.loops, uv_coords):
        loop[uv_layer].uv = uv

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def _actualizar_plano_en_vivo(self, context):
    """Callback: al cambiar ancho/alto/distancia en el panel, reconstruye
    y reposiciona el plano activo (posición LOCAL respecto a su cámara
    padre, en -distance sobre el eje -Z local)."""
    obj = self.active_plane
    if obj is None or obj.name not in context.scene.objects:
        return
    try:
        _reconstruir_malla_plano(obj, self.plane_width, self.plane_height)
        obj.location = (0.0, 0.0, -self.plane_distance)
        obj["plano_width"] = self.plane_width
        obj["plano_height"] = self.plane_height
        obj["plano_distance_from_camera"] = self.plane_distance
    except RuntimeError:
        pass


def _aplicar_intensidad_en_plano(obj, intensity):
    """Aplica la 'intensidad' (brillo + opacidad combinados) al material
    del plano activo. Un solo valor controla dos cosas a la vez:
      - Brillo: Strength de nodos Emission, y Emission Strength de
        Principled BSDF (sin techo, puede pasar de 1.0).
      - Opacidad: Alpha de Principled BSDF, siempre entre 0.0 y 1.0.
    Si el material no tiene ninguno de esos nodos, no hace nada (no
    inventa nodos nuevos: solo controla lo que ya existe)."""
    if obj is None or not obj.data.materials:
        return
    mat = obj.data.materials[0]
    if mat is None or not mat.use_nodes or mat.node_tree is None:
        return

    alpha = max(0.0, min(1.0, intensity))
    afecto_alpha = False

    for node in mat.node_tree.nodes:
        if node.type == 'EMISSION' and 'Strength' in node.inputs:
            node.inputs['Strength'].default_value = intensity
        elif node.type == 'BSDF_PRINCIPLED':
            if 'Alpha' in node.inputs:
                node.inputs['Alpha'].default_value = alpha
                afecto_alpha = True
            if 'Emission Strength' in node.inputs:
                node.inputs['Emission Strength'].default_value = intensity

    # Sin esto, bajar el Alpha del nodo no se ve transparente en el
    # visor (Eevee ignora el alpha del nodo si el material sigue en
    # modo 'OPAQUE').
    if afecto_alpha and hasattr(mat, "blend_method"):
        mat.blend_method = 'BLEND' if alpha < 1.0 else 'OPAQUE'

    obj["plano_intensity"] = intensity


def _actualizar_intensidad_en_vivo(self, context):
    """Callback: al mover el slider de intensidad (o usar los botones
    subir/bajar), la aplica en vivo al plano activo."""
    obj = self.active_plane
    if obj is None or obj.name not in context.scene.objects:
        return
    try:
        _aplicar_intensidad_en_plano(obj, self.plane_intensity)
    except RuntimeError:
        pass


# Propiedades base de bpy.types.Node que NO queremos volcar por el bucle
# genérico: o las genera el resto del código por su cuenta (location,
# width, image, color_ramp...), o son de solo lectura / no sirven fuera
# del editor (rna_type, dimensions, select...).
_NODE_PROPS_EXCLUIR = {
    'rna_type', 'type', 'bl_idname', 'bl_label', 'bl_description', 'bl_icon',
    'bl_static_type', 'bl_width_default', 'bl_width_min', 'bl_width_max',
    'bl_height_default', 'bl_height_min', 'bl_height_max',
    'inputs', 'outputs', 'internal_links',
    'name', 'location', 'location_absolute', 'width', 'width_hidden',
    'height', 'dimensions', 'parent', 'select',
    'image', 'node_tree', 'color_ramp', 'texture_mapping', 'color_mapping',
    'color',  # se guarda aparte, solo si use_custom_color está activo
}


def _propiedades_genericas_de_nodo(node):
    """Recorre TODAS las propiedades RNA del nodo -- no una lista fija
    por tipo -- y devuelve los nombres de las que son valores simples
    configurables desde el editor de Shading: enums (operación de un
    Math node, tipo de ruido, distribución del Principled BSDF...),
    booleanos (use_clamp, mute, hide...), floats/ints sueltos, strings
    (label) e interpolación/extensión/proyección de texturas de imagen.

    Antes esto dependía de `_PROPS_POR_TIPO`, una lista manual por
    bl_idname que SIEMPRE se queda corta apenas el usuario toca algo
    en Shading que no estaba anticipado (p. ej. la proyección de un
    Image Texture, o el 'distribution' de un Principled BSDF). Con el
    bucle genérico, cualquier ajuste que se pueda hacer en el panel N
    del nodo queda capturado automáticamente, sin mantenimiento."""
    nombres = []
    for prop in node.bl_rna.properties:
        ident = prop.identifier
        if ident in _NODE_PROPS_EXCLUIR or prop.is_readonly:
            continue
        if prop.type not in {'BOOLEAN', 'INT', 'FLOAT', 'ENUM', 'STRING'}:
            continue
        # Excluye vectores/arrays a nivel de nodo (location, etc. ya
        # están afuera; esto cubre casos similares que puedan aparecer
        # en nodos de versiones futuras de Blender).
        if getattr(prop, 'array_length', 0) not in (0,):
            continue
        nombres.append(ident)
    return nombres


def _generar_codigo_material(mat):
    """Genera las líneas Python (indentadas a nivel de función) que
    recrean un material simple por nodos (Image Texture, Emission,
    Principled BSDF, etc.). Si el plano no tiene material, devuelve
    un 'pass'.

    NOTA: los sockets se referencian por ÍNDICE, no por nombre. Varios
    nodos (Math, Vector Math, etc.) tienen más de un socket de entrada
    con el mismo `.name` ("Value", "Value", "Value"...), así que
    `inputs['Value']` siempre devolvía el primero y pisaba los demás.
    Además cada asignación queda envuelta en try/except: si el Blender
    que carga el archivo es de otra versión y un nodo tiene un socket
    de más o de menos (p. ej. 'Weight' en Mix Shader/BSDFs), esa línea
    se salta en vez de tirar abajo toda la ejecución.
    """
    if mat is None or not getattr(mat, "use_nodes", False) or mat.node_tree is None:
        return "    pass  # el plano original no tenía material con nodos"

    lineas = []
    lineas.append(f"    mat = bpy.data.materials.new({mat.name!r})")
    lineas.append("    mat.use_nodes = True")
    if hasattr(mat, "blend_method"):
        lineas.append(f"    mat.blend_method = {mat.blend_method!r}")
    if hasattr(mat, "shadow_method"):
        lineas.append(f"    mat.shadow_method = {mat.shadow_method!r}")
    lineas.append(f"    mat.use_backface_culling = {mat.use_backface_culling!r}")
    lineas.append("    nt = mat.node_tree")
    lineas.append("    nt.nodes.clear()")

    node_vars = {}
    for i, node in enumerate(mat.node_tree.nodes):
        var = f"nodo_{i}"
        node_vars[node.name] = var
        lineas.append(f"    {var} = nt.nodes.new({node.bl_idname!r})")
        lineas.append(f"    {var}.location = {tuple(node.location)!r}")
        lineas.append(f"    {var}.name = {node.name!r}")
        lineas.append(f"    if hasattr({var}, 'width'): {var}.width = {node.width!r}")
        if getattr(node, "use_custom_color", False):
            lineas.append(f"    {var}.use_custom_color = True")
            lineas.append(f"    {var}.color = {tuple(node.color)!r}")

        # --- TODAS las propiedades RNA simples del nodo (operation,
        # blend_type, noise_type, distribution, mute, hide, label,
        # interpolation/extension/projection de texturas, etc.) ---
        for prop_name in _propiedades_genericas_de_nodo(node):
            valor = getattr(node, prop_name)
            lineas.append("    try:")
            lineas.append(f"        {var}.{prop_name} = {valor!r}")
            lineas.append("    except Exception:")
            lineas.append(f"        pass  # '{prop_name}' no existe/no es asignable en esta versión")

        # --- Color Ramp: hay que recrear sus elementos, no son sockets ---
        if node.bl_idname == 'ShaderNodeValToRGB' and node.color_ramp is not None:
            ramp = node.color_ramp
            lineas.append(f"    {var}.color_ramp.interpolation = {ramp.interpolation!r}")
            lineas.append(f"    {var}.color_ramp.color_mode = {ramp.color_mode!r}")
            for idx, el in enumerate(ramp.elements):
                if idx == 0:
                    lineas.append(f"    {var}.color_ramp.elements[0].position = {el.position!r}")
                    lineas.append(f"    {var}.color_ramp.elements[0].color = {tuple(el.color)!r}")
                else:
                    lineas.append(
                        f"    _el = {var}.color_ramp.elements.new({el.position!r})"
                    )
                    lineas.append(f"    _el.color = {tuple(el.color)!r}")

        if node.bl_idname == 'ShaderNodeGroup' and node.node_tree is not None:
            # LIMITACIÓN: no se exporta el contenido interno del grupo de
            # nodos, solo la referencia por nombre. Si el archivo destino
            # ya tiene un grupo con ese nombre (mismo .blend, o grupo
            # compartido vía biblioteca), se reconecta solo; si no
            # existe, este nodo queda vacío y se avisa en consola en vez
            # de romper el resto de la configuración.
            lineas.append("    try:")
            lineas.append(
                f"        {var}.node_tree = bpy.data.node_groups[{node.node_tree.name!r}]"
            )
            lineas.append("    except KeyError:")
            lineas.append(
                f"        print(\"[Plano Generador] Grupo de nodos "
                f"'{node.node_tree.name}' no existe en este archivo -- "
                f"{var} queda sin contenido\")"
            )

        if node.type == 'TEX_IMAGE' and node.image is not None:
            ruta = bpy.path.abspath(node.image.filepath)
            colorspace = node.image.colorspace_settings.name
            lineas.append("    try:")
            lineas.append(
                f"        {var}.image = bpy.data.images.load({ruta!r}, check_existing=True)"
            )
            lineas.append(
                f"        {var}.image.colorspace_settings.name = {colorspace!r}"
            )
            lineas.append("    except Exception:")
            lineas.append(f"        pass  # no se encontró la imagen original: {ruta}")

        for idx, inp in enumerate(node.inputs):
            if not hasattr(inp, "default_value"):
                continue
            if inp.type not in {'VALUE', 'RGBA', 'VECTOR', 'BOOLEAN', 'INT', 'STRING'}:
                continue
            try:
                if inp.type in {'VALUE', 'INT', 'BOOLEAN', 'STRING'}:
                    valor = inp.default_value
                else:
                    valor = tuple(inp.default_value)
                lineas.append("    try:")
                lineas.append(
                    f"        {var}.inputs[{idx}].default_value = {valor!r}"
                )
                lineas.append("    except (IndexError, KeyError, TypeError):")
                lineas.append(
                    f"        pass  # socket #{idx} ('{inp.name}') no existe en esta versión de Blender"
                )
            except Exception:
                pass

    for link in mat.node_tree.links:
        from_var = node_vars.get(link.from_node.name)
        to_var = node_vars.get(link.to_node.name)
        if from_var and to_var:
            from_idx = list(link.from_node.outputs).index(link.from_socket)
            to_idx = list(link.to_node.inputs).index(link.to_socket)
            lineas.append("    try:")
            lineas.append(
                f"        nt.links.new({from_var}.outputs[{from_idx}], {to_var}.inputs[{to_idx}])"
            )
            lineas.append("    except (IndexError, KeyError):")
            lineas.append("        pass  # socket de conexión no existe en esta versión")

    lineas.append("    plano_obj.data.materials.append(mat)")
    return "\n".join(lineas)


def _generar_codigo_plano(plano_obj, indice):
    """Genera el bloque que crea UN plano-filtro (mesh + material).
    Asume que ya existen `cam_obj` y la lista `planos_creados` en el
    scope de aplicar_en_blender(); reutiliza los nombres locales
    `mesh`/`plano_obj`/`mat`/`nt` en cada bloque (no hay problema:
    el código generado es secuencial, no un loop real, así que cada
    bloque los reasigna sin pisar nada que ya se necesite)."""
    width = plano_obj.get("plano_width", 2.0)
    height = plano_obj.get("plano_height", 2.0)
    distance = plano_obj.get("plano_distance_from_camera", 1.0)
    intensity = plano_obj.get("plano_intensity", 1.0)
    alpha = max(0.0, min(1.0, intensity))
    mat = plano_obj.data.materials[0] if plano_obj.data.materials else None
    material_code = _generar_codigo_material(mat)

    # Solo tiene sentido reaplicar la intensidad si hubo material
    # generado arriba (si no, `mat` ni existe en el código generado).
    if mat is not None and mat.use_nodes and mat.node_tree is not None:
        intensidad_code = f'''
    # --- Intensidad del plano (brillo + opacidad combinados) ---
    for _nodo in nt.nodes:
        if _nodo.type == 'EMISSION' and 'Strength' in _nodo.inputs:
            _nodo.inputs['Strength'].default_value = {intensity!r}
        elif _nodo.type == 'BSDF_PRINCIPLED':
            if 'Alpha' in _nodo.inputs:
                _nodo.inputs['Alpha'].default_value = {alpha!r}
                mat.blend_method = {('BLEND' if alpha < 1.0 else 'OPAQUE')!r}
            if 'Emission Strength' in _nodo.inputs:
                _nodo.inputs['Emission Strength'].default_value = {intensity!r}
'''
    else:
        intensidad_code = ""

    return f'''    # === Plano {indice}: {plano_obj.name} ===
    mesh = bpy.data.meshes.new({plano_obj.data.name!r})
    plano_obj = bpy.data.objects.new({plano_obj.name!r}, mesh)
    bpy.context.collection.objects.link(plano_obj)
    plano_obj.parent = cam_obj

    width, height, distance = {width!r}, {height!r}, {distance!r}
    hw, hh = width / 2.0, height / 2.0
    verts = [(-hw, -hh, 0.0), (hw, -hh, 0.0), (hw, hh, 0.0), (-hw, hh, 0.0)]
    bm = bmesh.new()
    bm_verts = [bm.verts.new(v) for v in verts]
    bm.verts.ensure_lookup_table()
    face = bm.faces.new(bm_verts)
    bm.normal_update()
    uv_layer = bm.loops.layers.uv.verify()
    uv_coords = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    for loop, uv in zip(face.loops, uv_coords):
        loop[uv_layer].uv = uv
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    plano_obj.location = (0.0, 0.0, -distance)
    plano_obj["es_plano_generado"] = True
    plano_obj["plano_width"] = width
    plano_obj["plano_height"] = height
    plano_obj["plano_distance_from_camera"] = distance
    plano_obj["plano_intensity"] = {intensity!r}

    # --- Material del plano ---
{material_code}
{intensidad_code}
    planos_creados.append(plano_obj)
'''


def _generar_codigo_configuracion(cam_obj, planos):
    """Genera el texto completo de un archivo .py ejecutable (mismo
    formato que espera 'Ejecutar Configuración'): define
    aplicar_en_blender(), la ejecuta y deja _cam_obj / _planos_obj
    (lista) como variables de nivel superior. `planos` es la lista de
    objetos plano-filtro hijos de cam_obj (todos paralelos entre sí:
    mismo parent, misma orientación, solo cambia la distancia)."""
    cam_data = cam_obj.data
    cam_matrix_rows = [tuple(row) for row in cam_obj.matrix_world]

    if cam_data.type == 'ORTHO':
        cam_extra = f"    cam_data.ortho_scale = {cam_data.ortho_scale!r}\n"
    else:
        cam_extra = (
            f"    cam_data.lens = {cam_data.lens!r}\n"
            f"    cam_data.sensor_width = {cam_data.sensor_width!r}\n"
            f"    cam_data.sensor_height = {cam_data.sensor_height!r}\n"
        )

    bloques_planos = "\n".join(
        _generar_codigo_plano(p, i) for i, p in enumerate(planos)
    )

    codigo = f'''"""
Configuración de Cámara + Planos-Filtro ({len(planos)} plano{"s" if len(planos) != 1 else ""})
Exportado automáticamente por 'Plano Generador' addon.
Cámara original: {cam_obj.name}
Planos originales: {", ".join(p.name for p in planos)}
"""

import bpy
import bmesh
import mathutils


def aplicar_en_blender():
    # --- Cámara ---
    cam_data = bpy.data.cameras.new({cam_data.name!r})
    cam_data.type = {cam_data.type!r}
{cam_extra}    cam_data.clip_start = {cam_data.clip_start!r}
    cam_data.clip_end = {cam_data.clip_end!r}

    cam_obj = bpy.data.objects.new({cam_obj.name!r}, cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.matrix_world = mathutils.Matrix({cam_matrix_rows!r})

    # --- Planos-filtro (todos hijos de la misma cámara y sin rotación
    #     relativa entre sí -> quedan paralelos, solo varía la distancia) ---
    planos_creados = []

{bloques_planos}
    return cam_obj, planos_creados


_cam_obj, _planos_obj = aplicar_en_blender()
_plano_obj = _planos_obj[0] if _planos_obj else None  # compatibilidad con configuraciones de 1 plano
'''
    return codigo


# =============================================================================
#   PROPIEDADES
# =============================================================================

class PlanoGeneradorProperties(PropertyGroup):

    execute_file_path: StringProperty(
        name="Archivo de Configuración",
        description=(
            "Archivo .py que define aplicar_en_blender() y crea la cámara "
            "y su plano-filtro asociado"
        ),
        default="",
        subtype='FILE_PATH',
    )

    active_camera: PointerProperty(
        name="Cámara Generada",
        description="Cámara creada por la última configuración ejecutada",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'CAMERA',
    )

    active_plane: PointerProperty(
        name="Plano Activo",
        description=(
            "Plano-filtro seleccionado actualmente para editar (una cámara "
            "puede tener varios planos-filtro paralelos, a distinta distancia)"
        ),
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'MESH' and obj.get("es_plano_generado", False),
    )

    plane_width: FloatProperty(
        name="Ancho del Plano",
        description="Ancho del plano-filtro (unidades de escena)",
        default=2.0,
        min=0.001,
        unit='LENGTH',
        update=_actualizar_plano_en_vivo,
    )

    plane_height: FloatProperty(
        name="Alto del Plano",
        description="Alto del plano-filtro (unidades de escena)",
        default=2.0,
        min=0.001,
        unit='LENGTH',
        update=_actualizar_plano_en_vivo,
    )

    plane_distance: FloatProperty(
        name="Distancia a la Cámara",
        description="Distancia del plano al frente de su cámara (espacio local)",
        default=1.0,
        min=0.001,
        unit='LENGTH',
        update=_actualizar_plano_en_vivo,
    )

    plane_intensity: FloatProperty(
        name="Intensidad",
        description=(
            "Brillo y opacidad combinados del plano-filtro. 1.0 = valores "
            "originales del material. 0.0 = opacidad 0 (invisible) y "
            "brillo 0 (apagado). Por encima de 1.0 solo sigue subiendo "
            "el brillo (la opacidad se satura en 1.0)"
        ),
        default=1.0,
        min=0.0,
        soft_max=3.0,
        update=_actualizar_intensidad_en_vivo,
    )


# =============================================================================
#   OPERADOR: EJECUTAR CONFIGURACIÓN
# =============================================================================

class PLANOGEN_OT_execute_config(Operator, ImportHelper):
    """Ejecuta el archivo .py seleccionado (con __name__ == '__main__'),
    igual que Scripting > Run Script, para crear la cámara y su plano"""
    bl_idname = "planogen.execute_config"
    bl_label = "Ejecutar Configuración (.py)"
    bl_options = {'REGISTER', 'UNDO'}
    filename_ext = ".py"

    filter_glob: StringProperty(default="*.py", options={'HIDDEN'})

    def invoke(self, context, event):
        props = context.scene.plano_generador_props
        if props.execute_file_path:
            self.filepath = bpy.path.abspath(props.execute_file_path)
        return super().invoke(context, event)

    def execute(self, context):
        props = context.scene.plano_generador_props
        props.execute_file_path = self.filepath

        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                codigo = f.read()
        except OSError as e:
            self.report({'ERROR'}, f"No se pudo leer el archivo: {e}")
            return {'CANCELLED'}

        namespace = {"__name__": "__main__", "__file__": self.filepath}
        try:
            exec(compile(codigo, self.filepath, 'exec'), namespace)
        except Exception as e:
            self.report({'ERROR'}, f"Error al ejecutar la configuración: {e}")
            return {'CANCELLED'}

        # El script deja _cam_obj / _planos_obj (lista) como variables de
        # nivel superior -> quedan disponibles en namespace tras el exec().
        # Compatibilidad: los .py exportados por la versión anterior del
        # addon (1 solo plano) solo dejan _plano_obj.
        cam_obj = namespace.get("_cam_obj")
        planos_obj = namespace.get("_planos_obj")
        if planos_obj is None:
            plano_obj_legacy = namespace.get("_plano_obj")
            planos_obj = [plano_obj_legacy] if plano_obj_legacy is not None else []

        if cam_obj is not None and getattr(cam_obj, "type", None) == 'CAMERA':
            props.active_camera = cam_obj

        planos_validos = [
            p for p in planos_obj if p is not None and getattr(p, "type", None) == 'MESH'
        ]
        if planos_validos:
            ultimo = planos_validos[-1]
            props.active_plane = ultimo
            props.plane_width = ultimo.get("plano_width", props.plane_width)
            props.plane_height = ultimo.get("plano_height", props.plane_height)
            props.plane_distance = ultimo.get(
                "plano_distance_from_camera", props.plane_distance
            )
            props.plane_intensity = ultimo.get("plano_intensity", 1.0)

        self.report(
            {'INFO'},
            f"Cámara y {len(planos_validos)} plano(s) creados desde: {self.filepath}",
        )
        return {'FINISHED'}


# =============================================================================
#   OPERADORES: MÚLTIPLES PLANOS POR CÁMARA
# =============================================================================

class PLANOGEN_OT_add_plane(Operator):
    """Agrega un nuevo plano-filtro hijo de la cámara activa. Queda
    paralelo a los demás (mismo parent, sin rotación relativa, solo
    cambia la distancia). Si ya hay planos, duplica el activo (o el
    último) como punto de partida y lo ubica más lejos que todos"""
    bl_idname = "planogen.add_plane"
    bl_label = "Agregar Plano"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.plano_generador_props
        cam_obj = props.active_camera
        if cam_obj is None or cam_obj.name not in context.scene.objects:
            self.report({'ERROR'}, "Primero generá o seleccioná una cámara")
            return {'CANCELLED'}

        planos_existentes = [
            o for o in cam_obj.children
            if o.type == 'MESH' and o.get("es_plano_generado", False)
        ]

        base = None
        if props.active_plane and props.active_plane in planos_existentes:
            base = props.active_plane
        elif planos_existentes:
            base = planos_existentes[-1]

        if base is not None:
            nuevo = base.copy()
            nuevo.data = base.data.copy()
            nuevo.name = f"{base.name}_{len(planos_existentes)}"
            context.collection.objects.link(nuevo)
            nuevo.parent = cam_obj
            distancia = max(
                (o.get("plano_distance_from_camera", 1.0) for o in planos_existentes),
                default=0.0,
            ) + 1.0
            ancho = base.get("plano_width", 2.0)
            alto = base.get("plano_height", 2.0)
            intensidad = base.get("plano_intensity", 1.0)
        else:
            mesh = bpy.data.meshes.new(f"{cam_obj.name}_Plano_Filtro_mesh")
            nuevo = bpy.data.objects.new(f"{cam_obj.name}_Plano_Filtro", mesh)
            context.collection.objects.link(nuevo)
            nuevo.parent = cam_obj
            distancia, ancho, alto, intensidad = 1.0, 2.0, 2.0, 1.0

        _reconstruir_malla_plano(nuevo, ancho, alto)
        nuevo.location = (0.0, 0.0, -distancia)
        nuevo["es_plano_generado"] = True
        nuevo["plano_width"] = ancho
        nuevo["plano_height"] = alto
        nuevo["plano_distance_from_camera"] = distancia
        nuevo["plano_intensity"] = intensidad

        props.active_plane = nuevo
        props.plane_width = ancho
        props.plane_height = alto
        props.plane_distance = distancia
        props.plane_intensity = intensidad

        self.report({'INFO'}, f"Plano agregado: {nuevo.name} (distancia {distancia:.2f})")
        return {'FINISHED'}


class PLANOGEN_OT_select_plane(Operator):
    """Selecciona un plano-filtro existente como 'plano activo' para
    editar su ancho/alto/distancia en el panel"""
    bl_idname = "planogen.select_plane"
    bl_label = "Seleccionar Plano"
    bl_options = {'REGISTER', 'UNDO'}

    plane_name: StringProperty(options={'HIDDEN'})

    def execute(self, context):
        props = context.scene.plano_generador_props
        obj = context.scene.objects.get(self.plane_name)
        if obj is None:
            self.report({'ERROR'}, "Ese plano ya no existe")
            return {'CANCELLED'}
        props.active_plane = obj
        props.plane_width = obj.get("plano_width", props.plane_width)
        props.plane_height = obj.get("plano_height", props.plane_height)
        props.plane_distance = obj.get("plano_distance_from_camera", props.plane_distance)
        props.plane_intensity = obj.get("plano_intensity", 1.0)
        return {'FINISHED'}


class PLANOGEN_OT_remove_plane(Operator):
    """Elimina el plano-filtro activo (objeto + malla)"""
    bl_idname = "planogen.remove_plane"
    bl_label = "Eliminar Plano"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.plano_generador_props
        obj = props.active_plane
        if obj is None or obj.name not in context.scene.objects:
            self.report({'ERROR'}, "No hay ningún plano activo para eliminar")
            return {'CANCELLED'}
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
        props.active_plane = None
        self.report({'INFO'}, "Plano eliminado")
        return {'FINISHED'}


class PLANOGEN_OT_adjust_intensity(Operator):
    """Sube o baja la intensidad (brillo + opacidad) del plano activo
    en pasos fijos, sin tener que arrastrar el slider"""
    bl_idname = "planogen.adjust_intensity"
    bl_label = "Ajustar Intensidad"
    bl_options = {'REGISTER', 'UNDO'}

    delta: FloatProperty(default=0.1, options={'HIDDEN'})

    def execute(self, context):
        props = context.scene.plano_generador_props
        obj = props.active_plane
        if obj is None or obj.name not in context.scene.objects:
            self.report({'ERROR'}, "No hay ningún plano activo")
            return {'CANCELLED'}

        # Asignar el nuevo valor a la propiedad dispara su callback
        # de update automáticamente (misma ruta que mover el slider).
        props.plane_intensity = max(0.0, props.plane_intensity + self.delta)
        self.report({'INFO'}, f"Intensidad: {props.plane_intensity:.2f}")
        return {'FINISHED'}


# =============================================================================
#   OPERADOR: PREVISUALIZAR
# =============================================================================

class PLANOGEN_OT_preview_camera(Operator):
    """Abre una ventana nueva en vista de cámara, mostrando exactamente
    lo que ve la cámara activa de la escena (incluye el plano-filtro,
    ya que usa shading Material para ver su color/transparencia)"""
    bl_idname = "planogen.preview_camera"
    bl_label = "Previsualizar Cámara"

    def execute(self, context):
        cam_obj = context.scene.camera
        if cam_obj is None:
            self.report({'ERROR'}, "No hay ninguna cámara activa en la escena")
            return {'CANCELLED'}

        bpy.ops.wm.window_new()
        nueva_ventana = context.window_manager.windows[-1]
        area = nueva_ventana.screen.areas[0]
        area.type = 'VIEW_3D'

        space = area.spaces.active
        space.region_3d.view_perspective = 'CAMERA'
        space.shading.type = 'MATERIAL'
        space.overlay.show_overlays = False

        self.report({'INFO'}, f"Previsualizando: {cam_obj.name}")
        return {'FINISHED'}


# =============================================================================
#   OPERADOR: EXPORTAR CONFIGURACIÓN
# =============================================================================

class PLANOGEN_OT_export_config(Operator, ExportHelper):
    """Exporta la cámara y el plano-filtro activos a un archivo .py
    ejecutable (mismo formato que 'Ejecutar Configuración'), incluyendo
    transform, dimensiones, distancia y el material/textura del plano
    si usa nodos"""
    bl_idname = "planogen.export_config"
    bl_label = "Exportar Configuración (.py)"
    bl_options = {'REGISTER'}
    filename_ext = ".py"

    filter_glob: StringProperty(default="*.py", options={'HIDDEN'})

    def invoke(self, context, event):
        props = context.scene.plano_generador_props
        cam_obj = props.active_camera
        nombre_base = cam_obj.name if cam_obj else "configuracion_plano"
        self.filepath = f"{nombre_base}.py"
        return super().invoke(context, event)

    def execute(self, context):
        props = context.scene.plano_generador_props
        cam_obj = props.active_camera

        if cam_obj is None or cam_obj.name not in context.scene.objects:
            self.report({'ERROR'}, "No hay ninguna cámara activa para exportar")
            return {'CANCELLED'}

        planos = [
            o for o in cam_obj.children
            if o.type == 'MESH' and o.get("es_plano_generado", False)
        ]
        # Orden estable: de más cerca a más lejos de la cámara.
        planos.sort(key=lambda o: o.get("plano_distance_from_camera", 0.0))

        if not planos:
            self.report({'ERROR'}, "La cámara activa no tiene ningún plano-filtro")
            return {'CANCELLED'}

        try:
            codigo = _generar_codigo_configuracion(cam_obj, planos)
            with open(self.filepath, 'w', encoding='utf-8') as f:
                f.write(codigo)
        except Exception as e:
            self.report({'ERROR'}, f"Error al exportar la configuración: {e}")
            return {'CANCELLED'}

        self.report(
            {'INFO'},
            f"Configuración exportada ({len(planos)} plano{'s' if len(planos) != 1 else ''}) a: {self.filepath}",
        )
        return {'FINISHED'}


# =============================================================================
#   PANEL
# =============================================================================

class PLANOGEN_PT_panel(Panel):
    bl_label = "Plano Generador"
    bl_idname = "PLANOGEN_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Plano Generador'

    def draw(self, context):
        layout = self.layout
        props = context.scene.plano_generador_props

        box = layout.box()
        box.label(text="Configuración (.py)", icon='FILE_SCRIPT')
        box.prop(props, "execute_file_path", text="")

        box = layout.box()
        box.label(text="Secuencia al ejecutar:", icon='INFO')
        col = box.column(align=True)
        col.label(text="1. Crea la cámara")
        col.label(text="2. Crea el plano-filtro")
        col.label(text="   al frente, aparentado")
        col.label(text="   a esa cámara")

        row = layout.row()
        row.scale_y = 1.6
        row.operator("planogen.execute_config", text="▶ Ejecutar Configuración", icon='PLAY')

        row = layout.row()
        row.scale_y = 1.3
        row.operator("planogen.preview_camera", text="🎬 Previsualizar", icon='VIEW_CAMERA')

        box = layout.box()
        box.label(text="Planos de la cámara activa:", icon='MESH_PLANE')

        planos = []
        if props.active_camera and props.active_camera.name in context.scene.objects:
            planos = [
                o for o in props.active_camera.children
                if o.type == 'MESH' and o.get("es_plano_generado", False)
            ]
            planos.sort(key=lambda o: o.get("plano_distance_from_camera", 0.0))

        if planos:
            col = box.column(align=True)
            for p in planos:
                row = col.row(align=True)
                icon = 'RADIOBUT_ON' if p == props.active_plane else 'RADIOBUT_OFF'
                dist = p.get("plano_distance_from_camera", 0.0)
                op = row.operator(
                    "planogen.select_plane",
                    text=f"{p.name}  (d={dist:.2f})",
                    icon=icon,
                )
                op.plane_name = p.name
        else:
            box.label(text="Esta cámara aún no tiene planos", icon='INFO')

        row = box.row(align=True)
        row.scale_y = 1.2
        row.enabled = bool(props.active_camera)
        row.operator("planogen.add_plane", text="➕ Agregar Plano", icon='ADD')
        sub = row.row(align=True)
        sub.enabled = bool(props.active_plane)
        sub.operator("planogen.remove_plane", text="🗑 Eliminar", icon='REMOVE')

        if props.active_plane:
            col = box.column(align=True)
            col.label(text=f"Editando: {props.active_plane.name}", icon='CHECKMARK')
            col.prop(props, "plane_width")
            col.prop(props, "plane_height")
            col.prop(props, "plane_distance")

            col.separator()
            col.label(text="Intensidad (brillo + opacidad):", icon='LIGHT')
            col.prop(props, "plane_intensity", slider=True, text="")
            row_int = col.row(align=True)
            op = row_int.operator(
                "planogen.adjust_intensity", text="➖ Bajar", icon='TRIA_DOWN'
            )
            op.delta = -0.1
            op = row_int.operator(
                "planogen.adjust_intensity", text="➕ Subir", icon='TRIA_UP'
            )
            op.delta = 0.1

        box = layout.box()
        box.label(text="Exportar configuración actual:", icon='EXPORT')
        row = box.row()
        row.scale_y = 1.3
        row.enabled = bool(props.active_camera and props.active_plane)
        row.operator(
            "planogen.export_config",
            text="💾 Exportar Configuración",
            icon='FILE_TICK',
        )
        if not (props.active_camera and props.active_plane):
            box.label(text="Genera primero una cámara y un plano", icon='INFO')


# =============================================================================
#   REGISTRO
# =============================================================================

classes = (
    PlanoGeneradorProperties,
    PLANOGEN_OT_execute_config,
    PLANOGEN_OT_export_config,
    PLANOGEN_OT_add_plane,
    PLANOGEN_OT_select_plane,
    PLANOGEN_OT_remove_plane,
    PLANOGEN_OT_adjust_intensity,
    PLANOGEN_OT_preview_camera,
    PLANOGEN_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.plano_generador_props = PointerProperty(type=PlanoGeneradorProperties)


def unregister():
    del bpy.types.Scene.plano_generador_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
