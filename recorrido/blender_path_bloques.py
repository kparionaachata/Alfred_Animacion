# -*- coding: utf-8 -*-
"""Ruta Bloques - trazado de recorridos SOBRE LAS CARAS SUPERIORES de bloques (mundo hecho de bloques sueltos / terreno de bloques).
Version para bloques de `blender_path_visual.py` (que graba caras seleccionadas en modo edicion de UNA malla): aqui cada bloque es un objeto, asi que el recorrido se traza
haciendo CLIC en el viewport sobre un bloque: se guarda el centro de su cara superior (celda i, j, k -> x = i + 0.5, y = j + 0.5, z = k + 1).

PASO 1  "Trazar sobre bloques" (modal): clic izquierdo = agrega la cara superior del bloque bajo el cursor (si haces clic en el costado, toma la cara superior de ese bloque);
        Retroceso = quita el ultimo; clic derecho / Esc / Enter = termina. La rueda y el boton central siguen moviendo la vista.
        Con "Rellenar camino" cada punto nuevo se une al anterior celda por celda (linea de celdas) siguiendo la superficie: en cada celda toma el bloque que hay a la altura
        del paso anterior (sube o baja hasta `Salto max`), asi el recorrido pasa de verdad por caras superiores y avisa si hay un hueco o un techo bajo.
PASO 2  "Añadir seleccionados": los bloques seleccionados se agregan en orden de cercania.  "Añadir cursor 3D": la cara superior bajo el cursor.
PASO 3  Exportar JSON (mismo formato de `key_points` que el de Path Recorder (blender_path_visual.py): index, coordinates{x,y,z}, texture, face_index; mas `cells` con todas las celdas del camino)
        o copiar `EMBEDDED_TRAJECTORY_POINTS` al portapapeles para pegarlo en los guiones de animacion.

API para la IA (sin interfaz):
    import importlib.util, sys
    spec = importlib.util.spec_from_file_location("blender_path_bloques", r"C:\\Users\\user\\Desktop\\Alfred_Animacion\\recorrido\\blender_path_bloques.py")
    rb = importlib.util.module_from_spec(spec); sys.modules["blender_path_bloques"] = rb; spec.loader.exec_module(rb); rb.register()
    rb.limpiar()
    rb.agregar_celda((-44, -15, -10))            # cara superior de la celda (i, j, k)  -> punto (-43.5, -14.5, -9.0)
    rb.agregar_xyz((-48.5, -22.6, 8.0))          # cara superior del bloque bajo ese punto (rayo desde arriba)
    rb.camino((-44, -15, -10), (-49, -20, -9))   # lista de celdas (i, j, k) por las que pasa, sin agregar nada
    rb.puntos(); rb.celdas(); rb.exportar(ruta_json); rb.embebido()      # lo trazado / texto EMBEDDED_TRAJECTORY_POINTS
"""
bl_info = {
    "name": "Ruta Bloques",
    "author": "Kebyn",
    "version": (1, 0, 0),
    "blender": (4, 4, 0),
    "location": "Vista 3D > barra lateral (N) > Ruta Bloques",
    "description": "Traza recorridos con clic sobre las caras superiores de bloques (objetos sueltos), rellena celda por celda y exporta JSON",
    "category": "Animation",
}

import json
import math
import re

import bpy
import gpu
from bpy.props import BoolProperty, CollectionProperty, FloatProperty, FloatVectorProperty, IntProperty, IntVectorProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

BLOQUE = re.compile(r"^bloque_(.+)_(-?\d+)_(-?\d+)_(-?\d+)(\.\d+)?$")
_ST = {"handle": None, "hover": None, "modal": False}


# ------------------------------------------------------------------------------------------------------------------------------------ datos
class RutaPunto(PropertyGroup):
    coords: FloatVectorProperty(name="Coordenadas", size=3, default=(0.0, 0.0, 0.0))
    celda: IntVectorProperty(name="Celda", size=3, default=(0, 0, 0))
    texture: StringProperty(name="Textura / tipo", default="")
    face_index: StringProperty(name="Bloque", default="")
    clave: BoolProperty(name="Punto clave", default=True)         # True: lo puso el usuario; False: relleno celda por celda
    aviso: StringProperty(name="Aviso", default="")


def P():
    return bpy.context.scene


# ------------------------------------------------------------------------------------------------------------------------------------ superficie
def _celda_de_hit(loc, nor):
    """celda (i, j, k) del bloque tocado: el punto retrocede un poco hacia adentro"""
    p = Vector(loc) - Vector(nor).normalized() * 0.01
    return (int(math.floor(p.x)), int(math.floor(p.y)), int(math.floor(p.z)))


def _tipo(ob, poly_index):
    """tipo del bloque (de su nombre) o nombre del material de la cara tocada"""
    m = BLOQUE.match(ob.name)
    if m:
        return m.group(1)
    try:
        if ob.type == 'MESH' and poly_index is not None and 0 <= poly_index < len(ob.data.polygons):
            idx = ob.data.polygons[poly_index].material_index
            if idx < len(ob.data.materials) and ob.data.materials[idx]:
                return ob.data.materials[idx].name
    except Exception:
        pass
    return ob.name


def _punto_de_celda(celda, texture="", bloque="", clave=True, aviso=""):
    i, j, k = celda
    return dict(coords=(i + 0.5, j + 0.5, k + 1.0), celda=(i, j, k), texture=texture, face_index=bloque, clave=clave, aviso=aviso)


def rayo(origen, direccion, distancia=200.0):
    """primer bloque / superficie que toca el rayo: dict(celda, texture, bloque, hit, normal) o None"""
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    ok, loc, nor, idx, ob, mw = sc.ray_cast(dg, Vector(origen), Vector(direccion).normalized(), distance=distancia)
    if not ok:
        return None
    return dict(celda=_celda_de_hit(loc, nor), texture=_tipo(ob, idx), bloque=ob.name, hit=Vector(loc), normal=Vector(nor))


def altura_en(x, y, z_ref, sube=1.6, baja=2.2):
    """cara superior horizontal que hay en (x, y) cerca de z_ref: rayo hacia abajo desde z_ref + sube; devuelve (z_superior, nombre_objeto, tipo, hit_ok) o None"""
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    o = Vector((x, y, z_ref + sube))
    for _ in range(6):
        ok, loc, nor, idx, ob, mw = sc.ray_cast(dg, o, Vector((0, 0, -1)), distance=sube + baja)
        if not ok:
            return None
        if nor.z > 0.5:
            return (loc.z, ob.name, _tipo(ob, idx))
        o = loc + Vector((0, 0, -0.02))                            # una pared: sigue hacia abajo
    return None


def _libre_arriba(x, y, z, alto=1.8):
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    ok, *_ = sc.ray_cast(dg, Vector((x, y, z + 0.05)), Vector((0, 0, 1)), distance=alto)
    return not ok


def camino(a, b, salto_max=1, comprobar=True):
    """celdas (i, j, k) que une a con b (inclusive) en linea sobre la cuadricula, cada una con su cara superior: lista de dicts(celda, texture, bloque, aviso).
    En cada paso toma la superficie que hay a la altura del paso anterior (sube / baja hasta `salto_max`)."""
    (i0, j0, k0), (i1, j1, k1) = a, b
    n = max(abs(i1 - i0), abs(j1 - j0))
    res = []
    k_prev = k0
    for s in range(n + 1):
        t = s / n if n else 0.0
        i = int(round(i0 + (i1 - i0) * t))
        j = int(round(j0 + (j1 - j0) * t))
        aviso = ""
        if s == 0:
            kk, tipo, bloque = k0, "", ""
        elif s == n:
            kk, tipo, bloque = k1, "", ""
            if abs(k1 - k_prev) > salto_max:
                aviso = f"salto de {k1 - k_prev} bloques"
        else:
            h = altura_en(i + 0.5, j + 0.5, k_prev + 1, sube=salto_max + 0.6, baja=salto_max + 1.2)
            if h is None:
                kk, tipo, bloque, aviso = k_prev, "", "", "sin bloque (hueco)"
            else:
                kk = int(round(h[0])) - 1
                tipo, bloque = h[2], h[1]
        if comprobar and not aviso and not _libre_arriba(i + 0.5, j + 0.5, kk + 1.0):
            aviso = "techo bajo (menos de 1.8 m de aire)"
        res.append(dict(celda=(i, j, kk), texture=tipo, bloque=bloque, aviso=aviso))
        k_prev = kk
    return res


# ------------------------------------------------------------------------------------------------------------------------------------ operaciones sobre la escena
def _anadir(d):
    pt = P().ruta_puntos.add()
    pt.coords, pt.celda, pt.texture, pt.face_index, pt.clave, pt.aviso = d["coords"], d["celda"], d["texture"], d["face_index"], d["clave"], d["aviso"]
    return pt


def _redibujar():
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            if a.type == 'VIEW_3D':
                a.tag_redraw()


def _ultima_clave():
    pts = P().ruta_puntos
    for i in range(len(pts) - 1, -1, -1):
        if pts[i].clave:
            return pts[i]
    return None


def agregar_celda(celda, texture="", bloque="", rellenar=None, salto_max=None):
    """agrega la cara superior de la celda (i, j, k) como punto clave; con `rellenar` (por defecto el de la escena) une con el punto clave anterior celda por celda"""
    sc = P()
    rellenar = sc.ruta_rellenar if rellenar is None else rellenar
    salto = sc.ruta_salto if salto_max is None else salto_max
    ant = _ultima_clave()
    if rellenar and ant is not None and tuple(ant.celda) != tuple(celda):
        for d in camino(tuple(ant.celda), tuple(celda), salto)[1:-1]:
            _anadir(_punto_de_celda(d["celda"], d["texture"], d["bloque"], clave=False, aviso=d["aviso"]))
    pt = _anadir(_punto_de_celda(tuple(celda), texture, bloque, clave=True))
    _redibujar()
    return pt


def agregar_xyz(xyz):
    """cara superior del bloque que hay en (x, y): con z busca cerca de esa altura; sin z, el primero desde arriba (rayo desde 150 m)"""
    x, y = xyz[0], xyz[1]
    h = altura_en(x, y, xyz[2], sube=0.5, baja=3.0) if len(xyz) > 2 else altura_en(x, y, 150.0, sube=0.0, baja=300.0)
    if h is None:
        raise RuntimeError(f"no hay bloque bajo {tuple(xyz)}")
    celda = (int(math.floor(x)), int(math.floor(y)), int(round(h[0])) - 1)
    return agregar_celda(celda, h[2], h[1])


def puntos():
    """puntos clave: [{index, coordinates, texture, face_index, cell}]"""
    res = []
    for n, p in enumerate([q for q in P().ruta_puntos if q.clave], 1):
        res.append(dict(index=n, coordinates=dict(x=round(p.coords[0], 3), y=round(p.coords[1], 3), z=round(p.coords[2], 3)), texture=p.texture, face_index=p.face_index, cell=list(p.celda)))
    return res


def celdas():
    """todas las celdas del recorrido (claves + relleno) en orden"""
    res = []
    clave = 0
    for n, p in enumerate(P().ruta_puntos, 1):
        clave += 1 if p.clave else 0
        res.append(dict(index=n, coordinates=dict(x=round(p.coords[0], 3), y=round(p.coords[1], 3), z=round(p.coords[2], 3)), texture=p.texture, face_index=p.face_index, cell=list(p.celda),
                        key_point=bool(p.clave), nearest_keypoint=clave, aviso=p.aviso))
    return res


def avisos():
    return [(c["index"], c["cell"], c["aviso"]) for c in celdas() if c["aviso"]]


def limpiar():
    P().ruta_puntos.clear()
    _ST["hover"] = None
    _redibujar()


def quitar_ultimo():
    """quita el ultimo punto clave y el relleno que llevaba"""
    pts = P().ruta_puntos
    if not len(pts):
        return False
    while len(pts) and not pts[len(pts) - 1].clave:
        pts.remove(len(pts) - 1)
    if len(pts):
        pts.remove(len(pts) - 1)
    _redibujar()
    return True


def _con_json(ruta):
    """asegura la extension .json (si no la lleva, se la pone)"""
    ruta = str(ruta)
    return ruta if ruta.lower().endswith(".json") else ruta + ".json"


def exportar(ruta):
    ruta = _con_json(ruta)
    datos = dict(path_name="recorrido_bloques", tipo="caras_superiores_de_bloques", celdas_totales=len(P().ruta_puntos), key_points=puntos(), cells=celdas(), avisos=[list(a[:1]) + [a[1], a[2]] for a in avisos()])
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(datos, fh, indent=2, ensure_ascii=False)
    return len(datos["key_points"]), len(datos["cells"])


def embebido():
    """texto EMBEDDED_TRAJECTORY_POINTS (formato de los guiones de animacion) con los puntos clave"""
    lineas = ["EMBEDDED_TRAJECTORY_POINTS = ["]
    for p in puntos():
        c = p["coordinates"]
        lineas.append(f'    {{"index": {p["index"]}, "coordinates": {{"x": {c["x"]}, "y": {c["y"]}, "z": {c["z"]}}}, "texture": "{p["texture"]}", "face_index": "{p["face_index"]}"}},')
    lineas.append("]")
    return "\n".join(lineas)


# ------------------------------------------------------------------------------------------------------------------------------------ dibujo
def _cuadro(cx, cy, z, margen=0.03):
    a, b = cx - 0.5 + margen, cx + 0.5 - margen
    c, d = cy - 0.5 + margen, cy + 0.5 - margen
    z += 0.02
    p = [(a, c, z), (b, c, z), (b, d, z), (a, d, z)]
    return [p[0], p[1], p[1], p[2], p[2], p[3], p[3], p[0]]


def dibujar():
    sc = bpy.context.scene
    if not hasattr(sc, "ruta_puntos"):
        return
    pts = list(sc.ruta_puntos)
    hover = _ST["hover"]
    if not pts and hover is None:
        return
    lineas, col_l, puntos_, col_p = [], [], [], []
    for i, p in enumerate(pts):
        c = Vector(p.coords) + Vector((0, 0, 0.04))
        puntos_.append(c)
        col_p.append((0.2, 1.0, 0.3, 1.0) if p.clave else (0.3, 0.6, 1.0, 1.0))
        if p.aviso:
            col_p[-1] = (1.0, 0.2, 0.2, 1.0)
        if i:
            lineas += [Vector(pts[i - 1].coords) + Vector((0, 0, 0.04)), c]
            col_l += [(1.0, 1.0, 0.0, 1.0)] * 2
        if p.clave:
            q = _cuadro(p.coords[0], p.coords[1], p.coords[2] - 0.02)
            lineas += [Vector(v) for v in q]
            col_l += [(0.2, 1.0, 0.3, 1.0)] * len(q)
    if hover is not None:
        q = _cuadro(hover[0] + 0.5, hover[1] + 0.5, hover[2] + 1.0, 0.0)
        lineas += [Vector(v) for v in q]
        col_l += [(1.0, 0.6, 0.1, 1.0)] * len(q)
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('LESS_EQUAL')
    if lineas:
        sh = gpu.shader.from_builtin('POLYLINE_SMOOTH_COLOR')
        b = batch_for_shader(sh, 'LINES', {"pos": lineas, "color": col_l})
        sh.bind()
        sh.uniform_float("viewportSize", gpu.state.viewport_get()[2:])
        sh.uniform_float("lineWidth", 3.0)
        b.draw(sh)
    if puntos_:
        gpu.state.point_size_set(9.0)
        sh = gpu.shader.from_builtin('POINT_FLAT_COLOR')
        b = batch_for_shader(sh, 'POINTS', {"pos": puntos_, "color": col_p})
        sh.bind()
        b.draw(sh)
    gpu.state.point_size_set(1.0)
    gpu.state.depth_test_set('NONE')
    gpu.state.blend_set('NONE')


def _asegurar_dibujo():
    if _ST["handle"] is None:
        _ST["handle"] = bpy.types.SpaceView3D.draw_handler_add(dibujar, (), 'WINDOW', 'POST_VIEW')


# ------------------------------------------------------------------------------------------------------------------------------------ operadores
class RUTABLOQUES_OT_trazar(Operator):
    bl_idname = "rutabloques.trazar"
    bl_label = "Trazar sobre bloques"
    bl_description = "Clic izquierdo: agrega la cara superior del bloque bajo el cursor. Retroceso: quita el ultimo. Clic derecho / Esc / Enter: terminar"

    def _pick(self, context, event):
        region, rv3d = context.region, context.region_data
        co = (event.mouse_region_x, event.mouse_region_y)
        o = view3d_utils.region_2d_to_origin_3d(region, rv3d, co)
        d = view3d_utils.region_2d_to_vector_3d(region, rv3d, co)
        return rayo(o, d)

    def modal(self, context, event):
        if context.area is None or context.area.type != 'VIEW_3D':
            return self.fin(context)
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'TRACKPADPAN', 'TRACKPADZOOM', 'NDOF_MOTION'} or (event.alt and event.type == 'LEFTMOUSE'):
            return {'PASS_THROUGH'}
        if event.type == 'MOUSEMOVE':
            h = self._pick(context, event)
            _ST["hover"] = h["celda"] if h else None
            context.area.tag_redraw()
            return {'PASS_THROUGH'}
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            h = self._pick(context, event)
            if h is None:
                self.report({'WARNING'}, "No hay ningun bloque bajo el cursor")
                return {'RUNNING_MODAL'}
            agregar_celda(h["celda"], h["texture"], h["bloque"])
            ult = [a for a in avisos()][-1:]
            self.report({'INFO'}, f"Punto {len(puntos())}: celda {h['celda']} ({h['texture']})" + (f"  AVISO: {ult[0][2]}" if ult else ""))
            return {'RUNNING_MODAL'}
        if event.type == 'BACK_SPACE' and event.value == 'PRESS':
            quitar_ultimo()
            return {'RUNNING_MODAL'}
        if event.type in {'RIGHTMOUSE', 'ESC', 'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
            return self.fin(context)
        return {'RUNNING_MODAL'}

    def fin(self, context):
        _ST["modal"] = False
        _ST["hover"] = None
        context.window.cursor_modal_restore()
        context.workspace.status_text_set(None)
        _redibujar()
        return {'FINISHED'}

    def invoke(self, context, event):
        if context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "Ejecutalo con el mouse sobre la vista 3D")
            return {'CANCELLED'}
        _asegurar_dibujo()
        _ST["modal"] = True
        context.window.cursor_modal_set('EYEDROPPER')
        context.workspace.status_text_set("Ruta Bloques:  clic = agregar cara superior   Retroceso = quitar ultimo   clic derecho / Esc / Enter = terminar")
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class RUTABLOQUES_OT_seleccionados(Operator):
    bl_idname = "rutabloques.seleccionados"
    bl_label = "Añadir seleccionados"
    bl_description = "Agrega la cara superior de cada bloque seleccionado, en orden de cercania (empieza por el mas cercano al ultimo punto, o el primero)"

    def execute(self, context):
        obs = [o for o in context.selected_objects if o.type == 'MESH']
        if not obs:
            self.report({'WARNING'}, "No hay bloques seleccionados")
            return {'CANCELLED'}
        _asegurar_dibujo()
        ref = Vector(_ultima_clave().coords) if _ultima_clave() else Vector(obs[0].location)
        pend = list(obs)
        n = 0
        while pend:
            pend.sort(key=lambda o: (Vector((o.location.x, o.location.y, o.location.z + 1.0)) - ref).length)
            o = pend.pop(0)
            m = BLOQUE.match(o.name)
            celda = (int(m.group(2)), int(m.group(3)), int(m.group(4))) if m else (int(math.floor(o.location.x)), int(math.floor(o.location.y)), int(round(o.location.z)))
            agregar_celda(celda, _tipo(o, None), o.name)
            ref = Vector((celda[0] + 0.5, celda[1] + 0.5, celda[2] + 1.0))
            n += 1
        self.report({'INFO'}, f"{n} bloques agregados")
        return {'FINISHED'}


class RUTABLOQUES_OT_cursor(Operator):
    bl_idname = "rutabloques.cursor"
    bl_label = "Añadir cursor 3D"
    bl_description = "Agrega la cara superior del bloque que esta bajo el cursor 3D"

    def execute(self, context):
        c = context.scene.cursor.location
        _asegurar_dibujo()
        try:
            agregar_xyz((c.x, c.y, c.z + 0.5))
        except Exception as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        return {'FINISHED'}


class RUTABLOQUES_OT_quitar(Operator):
    bl_idname = "rutabloques.quitar"
    bl_label = "Quitar ultimo"

    def execute(self, context):
        quitar_ultimo()
        return {'FINISHED'}


class RUTABLOQUES_OT_limpiar(Operator):
    bl_idname = "rutabloques.limpiar"
    bl_label = "Borrar recorrido"

    def execute(self, context):
        limpiar()
        return {'FINISHED'}


class RUTABLOQUES_OT_exportar(Operator):
    bl_idname = "rutabloques.exportar"
    bl_label = "Exportar JSON"
    bl_description = "Exporta key_points (formato Path Recorder (blender_path_visual.py)) y todas las celdas del camino"
    filepath: StringProperty(subtype="FILE_PATH", default="recorrido_bloques.json")
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    def execute(self, context):
        if not len(context.scene.ruta_puntos):
            self.report({'WARNING'}, "No hay recorrido")
            return {'CANCELLED'}
        self.filepath = _con_json(self.filepath)
        k, c = exportar(self.filepath)
        self.report({'INFO'}, f"{k} puntos clave y {c} celdas -> {self.filepath}")
        return {'FINISHED'}

    def invoke(self, context, event):
        if not self.filepath.lower().endswith(".json"):
            self.filepath = "recorrido_bloques.json"
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class RUTABLOQUES_OT_copiar(Operator):
    bl_idname = "rutabloques.copiar"
    bl_label = "Copiar EMBEDDED_TRAJECTORY_POINTS"
    bl_description = "Copia al portapapeles los puntos clave listos para pegar en un guion de animacion"

    def execute(self, context):
        context.window_manager.clipboard = embebido()
        self.report({'INFO'}, f"{len(puntos())} puntos copiados")
        return {'FINISHED'}


def _txt_coord(p):
    return f"({p.coords[0]:.1f}, {p.coords[1]:.1f}, {p.coords[2]:.1f})"


class RUTABLOQUES_OT_copiar_punto(Operator):
    bl_idname = "rutabloques.copiar_punto"
    bl_label = "Copiar coordenada"
    bl_description = "Copia al portapapeles las coordenadas de este punto, p. ej. (-76.5, -14.5, -11.0)"
    indice: IntProperty(default=-1)

    def execute(self, context):
        claves = [p for p in context.scene.ruta_puntos if p.clave]
        if not claves:
            return {'CANCELLED'}
        p = claves[self.indice]
        context.window_manager.clipboard = _txt_coord(p)
        self.report({'INFO'}, "Copiado " + _txt_coord(p))
        return {'FINISHED'}


class RUTABLOQUES_PT_panel(Panel):
    bl_idname, bl_label, bl_space_type, bl_region_type, bl_category = "RUTABLOQUES_PT_panel", "Ruta Bloques", 'VIEW_3D', 'UI', "Ruta Bloques"

    def draw(self, context):
        l, sc = self.layout, context.scene
        b = l.box()
        b.label(text="1. Trazar", icon='TRACKING')
        b.operator("rutabloques.trazar", icon='EYEDROPPER')
        b.prop(sc, "ruta_rellenar")
        if sc.ruta_rellenar:
            b.prop(sc, "ruta_salto")
        r = b.row(align=True)
        r.operator("rutabloques.seleccionados", icon='RESTRICT_SELECT_OFF')
        r.operator("rutabloques.cursor", icon='CURSOR')
        r = b.row(align=True)
        r.operator("rutabloques.quitar", icon='REMOVE')
        r.operator("rutabloques.limpiar", icon='TRASH')
        b.label(text=f"Puntos clave: {len(puntos())}   celdas: {len(sc.ruta_puntos)}")
        av = avisos()
        if av:
            c = b.column(align=True)
            c.alert = True
            for i, cel, txt in av[:5]:
                c.label(text=f"#{i} {tuple(cel)}: {txt}", icon='ERROR')
            if len(av) > 5:
                c.label(text=f"... y {len(av) - 5} avisos mas")
        claves = [p for p in sc.ruta_puntos if p.clave]
        for k in range(max(0, len(claves) - 4), len(claves)):
            p = claves[k]
            r = b.row(align=True)
            r.label(text=f"{_txt_coord(p)}  {p.texture}")
            r.operator("rutabloques.copiar_punto", text="Copiar", icon='COPYDOWN').indice = k
        e = l.box()
        e.label(text="2. Exportar", icon='EXPORT')
        e.operator("rutabloques.exportar", icon='FILE_TEXT')
        e.operator("rutabloques.copiar", icon='COPYDOWN')


CLASES = (RutaPunto, RUTABLOQUES_OT_trazar, RUTABLOQUES_OT_seleccionados, RUTABLOQUES_OT_cursor, RUTABLOQUES_OT_quitar, RUTABLOQUES_OT_limpiar, RUTABLOQUES_OT_exportar,
          RUTABLOQUES_OT_copiar, RUTABLOQUES_OT_copiar_punto, RUTABLOQUES_PT_panel)


def register():
    for c in CLASES:
        try:
            bpy.utils.register_class(c)
        except ValueError:
            pass
    bpy.types.Scene.ruta_puntos = CollectionProperty(type=RutaPunto)
    bpy.types.Scene.ruta_rellenar = BoolProperty(name="Rellenar camino", description="une cada punto con el anterior celda por celda, siguiendo la superficie", default=True)
    bpy.types.Scene.ruta_salto = IntProperty(name="Salto max (bloques)", description="cuanto puede subir o bajar el camino entre dos celdas vecinas", default=1, min=0, max=5)
    _asegurar_dibujo()


def unregister():
    if _ST["handle"] is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_ST["handle"], 'WINDOW')
        _ST["handle"] = None
    for c in reversed(CLASES):
        try:
            bpy.utils.unregister_class(c)
        except RuntimeError:
            pass
    for n in ("ruta_puntos", "ruta_rellenar", "ruta_salto"):
        if hasattr(bpy.types.Scene, n):
            delattr(bpy.types.Scene, n)


if __name__ == "__main__":
    register()
