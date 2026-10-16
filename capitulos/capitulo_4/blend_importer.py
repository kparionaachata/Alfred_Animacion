"""
Blend Importer System
Sistema de importación de archivos .blend con coordenada marcada por
selección de cara en el viewport.

Usa EXACTAMENTE el mismo sistema que Alfred Animation Studio
(path_recorder.py) para marcar coordenadas: al activar la grabación,
seleccionar una cara en modo EDIT sobre cualquier malla registra su
coordenada global (centro de la cara). "Reproducir recorrido" importa
el objeto .blend en esa coordenada.
"""

import bpy
import os
import bmesh
from bpy.props import StringProperty, FloatVectorProperty, BoolProperty
from bpy.types import Operator, Panel, PropertyGroup
from bpy.app.handlers import persistent
from bpy_extras.io_utils import ImportHelper

bl_info = {
    "name": "Blend File Importer",
    "author": "Multi-Entity System",
    "version": (2, 0, 0),
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > Blend",
    "description": "Importa un archivo .blend en una coordenada marcada seleccionando una cara en el viewport",
    "category": "Import-Export",
}

# ============================================================================
# HANDLER — deteccion automatica de face seleccionada
# ============================================================================
# Identico en logica a _alfred_face_selection_handler de
# alfred_animation_studio/path_recorder.py: se ejecuta en cada
# depsgraph_update_post; mientras recording_active este activo y haya
# exactamente una cara seleccionada en modo EDIT sobre una malla, registra
# el centro global de esa cara como la coordenada de importacion.

def _blend_import_face_selection_handler(scene):
    settings = getattr(scene, "blend_import_settings", None)
    if settings is None or not settings.recording_active:
        return

    obj = bpy.context.active_object
    if obj is None or obj.type != 'MESH' or obj.mode != 'EDIT':
        return

    bm = bmesh.from_edit_mesh(obj.data)
    selected = [f for f in bm.faces if f.select]
    if len(selected) != 1:
        return

    face = selected[0]
    center_local = face.calc_center_median()
    center_global = obj.matrix_world @ center_local

    # Evita reescribir la misma coordenada en cada tick del depsgraph
    # mientras esa cara sigue seleccionada.
    nueva = (round(center_global.x, 6), round(center_global.y, 6), round(center_global.z, 6))
    actual = tuple(round(c, 6) for c in settings.import_location)
    if settings.point_recorded and nueva == actual:
        return

    settings.import_location = center_global
    settings.point_recorded = True

    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


_blend_import_face_selection_handler = persistent(_blend_import_face_selection_handler)


def _ensure_handler_registered():
    if _blend_import_face_selection_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_blend_import_face_selection_handler)


def _remove_handler():
    if _blend_import_face_selection_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_blend_import_face_selection_handler)


# ============================================================================
# PROPERTY GROUP
# ============================================================================

class BlendImportSettings(PropertyGroup):
    """Configuración mínima para importación de archivos .blend"""

    filepath: StringProperty(
        name="Archivo .blend",
        description="Ruta del archivo .blend a importar",
        default="",
        subtype='FILE_PATH'
    )

    import_location: FloatVectorProperty(
        name="Coordenadas",
        description="Coordenada registrada donde se importará el objeto .blend",
        default=(0.0, 0.0, 0.0),
        subtype='TRANSLATION'
    )

    recording_active: BoolProperty(
        name="Grabando",
        description="Si esta activo, seleccionar una cara en modo EDIT registra su coordenada",
        default=False
    )

    point_recorded: BoolProperty(
        name="Punto registrado",
        default=False
    )

    # Nombres (separados por "|") de TODOS los objetos importados en la
    # corrida anterior, para poder borrarlos por completo antes de volver a
    # importar (si solo se guardara un nombre, al reimportar quedarian
    # huerfanos en la escena los demas objetos de la jerarquia, ej. la malla
    # hija de un Empty).
    imported_object_names: StringProperty(default="")


# ============================================================================
# OPERATORS
# ============================================================================

class BLEND_OT_select_file(Operator, ImportHelper):
    """Seleccionar archivo .blend para importar"""
    bl_idname = "blend_import.select_file"
    bl_label = "Seleccionar Archivo .blend"
    bl_description = "Buscar y seleccionar un archivo .blend"

    filter_glob: StringProperty(
        default="*.blend",
        options={'HIDDEN'}
    )

    def execute(self, context):
        settings = context.scene.blend_import_settings
        settings.filepath = self.filepath
        self.report({'INFO'}, f"Archivo seleccionado: {os.path.basename(self.filepath)}")
        return {'FINISHED'}


class BLEND_OT_toggle_recording(Operator):
    """Inicia o detiene la grabación de la coordenada de importación"""
    bl_idname = "blend_import.toggle_recording"
    bl_label = "Iniciar grabación de recorrido"
    bl_description = (
        "Inicia la grabacion: entra en modo EDIT sobre una malla y "
        "selecciona una cara para marcar la coordenada de importacion"
    )
    bl_options = {'REGISTER'}

    def execute(self, context):
        settings = context.scene.blend_import_settings
        settings.recording_active = not settings.recording_active

        if settings.recording_active:
            _ensure_handler_registered()
            self.report({'INFO'}, "Grabación INICIADA — selecciona una cara en modo EDIT")
        else:
            self.report({'INFO'}, "Grabación DETENIDA")

        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        return {'FINISHED'}


class BLEND_OT_import_file(Operator):
    """Importa el archivo .blend en la coordenada registrada"""
    bl_idname = "blend_import.import_file"
    bl_label = "Reproducir recorrido"
    bl_description = "Importa el objeto .blend en la coordenada registrada"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.blend_import_settings

        if not settings.filepath:
            self.report({'ERROR'}, "No se ha seleccionado ningún archivo .blend")
            return {'CANCELLED'}

        if not os.path.exists(settings.filepath):
            self.report({'ERROR'}, f"El archivo no existe: {settings.filepath}")
            return {'CANCELLED'}

        if not settings.point_recorded:
            self.report({'ERROR'},
                "No hay ninguna coordenada registrada. Usa 'Iniciar grabación de "
                "recorrido' y selecciona una cara en modo EDIT.")
            return {'CANCELLED'}

        try:
            # Eliminar TODOS los objetos de una corrida anterior (empezar de
            # cero). Se borran todos los nombres guardados, no solo uno, para
            # no dejar huerfana la malla hija de un Empty al reimportar.
            #
            # IMPORTANTE: obj.data NO siempre es una Mesh. Jerarquias como
            # fogata_3 mezclan mallas con objetos tipo LIGHT (ej.
            # "campfireRun" es una PointLight parentada dentro del arbol
            # importado). Hay que borrar el datablock huerfano con la
            # coleccion de bpy.data correcta segun el tipo real del objeto,
            # o Blender lanza:
            # "BlendDataMeshes.remove(): ... expected a Mesh type, not PointLight"
            if settings.imported_object_names:
                _data_collection_by_type = {
                    'MESH': bpy.data.meshes,
                    'LIGHT': bpy.data.lights,
                    'CAMERA': bpy.data.cameras,
                    'CURVE': bpy.data.curves,
                    'SURFACE': bpy.data.curves,
                    'FONT': bpy.data.curves,
                    'META': bpy.data.metaballs,
                    'ARMATURE': bpy.data.armatures,
                    'LATTICE': bpy.data.lattices,
                    'SPEAKER': bpy.data.speakers,
                    'LIGHT_PROBE': bpy.data.lightprobes,
                    'GPENCIL': getattr(bpy.data, "grease_pencils", None),
                    'VOLUME': getattr(bpy.data, "volumes", None),
                }
                for old_name in settings.imported_object_names.split("|"):
                    old_obj = bpy.data.objects.get(old_name)
                    if old_obj is not None:
                        old_data = old_obj.data
                        old_type = old_obj.type
                        bpy.data.objects.remove(old_obj, do_unlink=True)
                        if old_data is not None and getattr(old_data, "users", 1) == 0:
                            data_collection = _data_collection_by_type.get(old_type)
                            if data_collection is not None:
                                try:
                                    data_collection.remove(old_data)
                                except (TypeError, RuntimeError):
                                    # El tipo de datablock no coincidio con la
                                    # coleccion esperada (ej. EMPTY no tiene
                                    # datablock, u otro tipo no mapeado
                                    # arriba). No es fatal: el datablock
                                    # simplemente queda huerfano con 0 users
                                    # y Blender lo purga en el siguiente
                                    # guardado/purge.
                                    pass
                settings.imported_object_names = ""

            imported_objects = []
            imported_collections = []

            with bpy.data.libraries.load(settings.filepath, link=False) as (data_from, data_to):
                data_to.collections = list(data_from.collections)
                data_to.objects = list(data_from.objects)

            for coll in data_to.collections:
                if coll:
                    imported_collections.append(coll)
                    context.scene.collection.children.link(coll)

            for obj in data_to.objects:
                if obj:
                    imported_objects.append(obj)
                    en_coleccion = any(obj.name in coll.objects for coll in imported_collections)
                    if not en_coleccion:
                        context.scene.collection.objects.link(obj)

            if not imported_objects and not imported_collections:
                self.report({'ERROR'}, f"No se encontró nada para importar en {os.path.basename(settings.filepath)}")
                return {'CANCELLED'}

            # Centrar el conjunto importado en la coordenada registrada.
            #
            # IMPORTANTE: solo se desplazan los objetos RAIZ (sin padre, o
            # cuyo padre no forma parte de este import) -- NUNCA los hijos.
            # obj.location de un objeto parentado es un offset LOCAL relativo
            # a su padre; si tambien se le sumara el offset global, el
            # desplazamiento se aplicaria dos veces (una directa sobre el
            # hijo y otra porque el padre ya lo arrastra al moverse),
            # produciendo un desfase entre el Empty raiz y su malla hija.
            target_location = settings.import_location
            imported_names = {obj.name for obj in imported_objects}
            root_objects = [
                obj for obj in imported_objects
                if obj.parent is None or obj.parent.name not in imported_names
            ]

            if root_objects:
                from mathutils import Vector
                total = Vector((0.0, 0.0, 0.0))
                for obj in root_objects:
                    total += obj.matrix_world.translation
                center = total / len(root_objects)
                offset = Vector(target_location) - center

                for obj in root_objects:
                    obj.location += offset

                # Objetos sueltos dentro de una collection importada que no
                # esten en imported_objects (caso raro) y tampoco tengan un
                # padre dentro del import -- se tratan igual como raiz.
                for coll in imported_collections:
                    for obj in coll.objects:
                        if obj not in imported_objects and (
                            obj.parent is None or obj.parent.name not in imported_names
                        ):
                            obj.location += offset

            if imported_objects:
                settings.imported_object_names = "|".join(obj.name for obj in imported_objects)

            bpy.context.view_layer.update()

            self.report({'INFO'}, (
                f"✅ Objeto importado en "
                f"({target_location[0]:.2f}, {target_location[1]:.2f}, {target_location[2]:.2f})"
            ))
            return {'FINISHED'}

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"Error al importar: {str(e)}")
            return {'CANCELLED'}


# ============================================================================
# UI PANEL
# ============================================================================

class BLEND_PT_importer_main(Panel):
    """Panel único y minimalista de importación de archivos .blend"""
    bl_label = "Blend Importer"
    bl_idname = "BLEND_PT_importer_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Blend'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.blend_import_settings

        # ── Archivo .blend ──
        row_file = layout.row(align=True)
        row_file.prop(settings, "filepath", text="")
        row_file.operator("blend_import.select_file", text="", icon='FILEBROWSER')

        layout.separator()

        # ── Grabación de coordenada ──
        rec_text = "  Detener grabación de recorrido" if settings.recording_active else "  Iniciar grabación de recorrido"
        rec_icon = "REC" if settings.recording_active else "RADIOBUT_ON"
        row_rec = layout.row()
        row_rec.scale_y = 1.3
        row_rec.operator("blend_import.toggle_recording", text=rec_text, icon=rec_icon)

        if settings.point_recorded:
            loc = settings.import_location
            layout.label(
                text=f"Coordenada: ({loc[0]:.2f}, {loc[1]:.2f}, {loc[2]:.2f})",
                icon='CHECKMARK'
            )
        else:
            layout.label(text="Selecciona una cara en modo EDIT para marcar la coordenada", icon='INFO')

        layout.separator()

        # ── Importar ──
        row_play = layout.row()
        row_play.scale_y = 1.3
        row_play.operator("blend_import.import_file", text="Reproducir recorrido", icon='PLAY')


# ============================================================================
# REGISTRATION
# ============================================================================

classes = (
    BlendImportSettings,
    BLEND_OT_select_file,
    BLEND_OT_toggle_recording,
    BLEND_OT_import_file,
    BLEND_PT_importer_main,
)


def register():
    """Registrar el addon"""
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.blend_import_settings = bpy.props.PointerProperty(
        type=BlendImportSettings
    )

    _ensure_handler_registered()

    print("=" * 70)
    print("✅ Blend Importer System registrado correctamente")
    print("   Panel disponible en: View3D > Sidebar > Blend")
    print("=" * 70)


def unregister():
    """Desregistrar el addon"""
    _remove_handler()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.blend_import_settings

    print("Blend Importer System desregistrado")


if __name__ == "__main__":
    register()
