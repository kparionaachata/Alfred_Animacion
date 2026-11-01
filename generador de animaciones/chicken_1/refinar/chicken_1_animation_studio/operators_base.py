# -*- coding: utf-8 -*-
"""
operators_base.py — Chicken 1 Animation Studio v1.8
Operadores: Setup, Historia, Reset, PickPose, AddEditRemoveMove de slots.
"""
import bpy, json, os
from bpy.types import Operator
from bpy.props import (
    IntProperty, FloatProperty, StringProperty,
    BoolProperty, EnumProperty, CollectionProperty, PointerProperty,
)
from .constants import BONES_LISTA, INTERP_TYPE_ITEMS, EYE_BASE_TRANSFORMS
from .pose_utils import (
    list_json_files, load_json_poses, get_pose_record,
    pose_record_to_full_dict, open_folder,
    _enum_json_files, _json_file_from_index, _enum_poses_from_self_json,
)
from .properties import load_historia_json, get_key_points
from .pose_utils import get_orientacion_inicial
from .fcurve_compat import get_fcurves, ensure_fcurves

# =============================================================================
# OPERADORES — SETUP
# =============================================================================

class CH1ST_OT_OpenAlfredBlend(Operator):
    bl_idname    = "ch1st.open_chicken_1_blend"
    bl_label     = "Abrir alfred.blend"
    bl_description = "Abre C:/Users/user/Desktop/Alfred_Animacion/estructura_lista/alfred.blend"
    bl_options   = {"REGISTER"}

    def execute(self, context):
        path = r"C:\Users\user\Desktop\Alfred_Animacion\estructura_lista\alfred.blend"
        if not os.path.isfile(path):
            self.report({"ERROR"}, f"No encontrado: {path}")
            return {"CANCELLED"}
        bpy.ops.wm.open_mainfile(filepath=path)
        return {"FINISHED"}


class CH1ST_OT_SetArmature(Operator):
    bl_idname    = "ch1st.set_armature"
    bl_label     = "Usar seleccionado"
    bl_description = "Asigna el objeto activo como armature de Alfred"

    def execute(self, context):
        obj = context.active_object
        if obj and obj.type == "ARMATURE":
            context.scene.ch1st.armature_name = obj.name
            self.report({"INFO"}, f"Armature -> {obj.name}")
        else:
            self.report({"WARNING"}, "El objeto activo no es un armature")
        return {"FINISHED"}

class CH1ST_OT_OpenPosesFolder(Operator):
    bl_idname = "ch1st.open_poses_folder"
    bl_label  = "Abrir carpeta poses"

    def execute(self, context):
        open_folder(bpy.path.abspath(context.scene.ch1st.poses_dir))
        return {"FINISHED"}

class CH1ST_OT_OpenAnimFolder(Operator):
    bl_idname = "ch1st.open_anim_folder"
    bl_label  = "Abrir carpeta animaciones"

    def execute(self, context):
        open_folder(bpy.path.abspath(context.scene.ch1st.anim_dir))
        return {"FINISHED"}


class CH1ST_OT_ImportPose(Operator):
    bl_idname    = "ch1st.import_pose"
    bl_label     = "Importar pose"
    bl_description = "Importa un archivo .json de pose a la carpeta de poses de la libreria"
    bl_options   = {"REGISTER", "UNDO"}

    filepath:    StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        start = bpy.path.abspath(context.scene.ch1st.poses_dir)
        if os.path.isdir(start):
            self.filepath = start + os.sep
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        import shutil
        st = context.scene.ch1st
        src = bpy.path.abspath(self.filepath)

        if not os.path.isfile(src) or not src.lower().endswith(".json"):
            self.report({"ERROR"}, f"Archivo .json no valido: {src}")
            return {"CANCELLED"}

        try:
            with open(src, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.report({"ERROR"}, f"No se pudo leer el JSON: {e}")
            return {"CANCELLED"}

        out_dir = bpy.path.abspath(st.poses_dir)
        os.makedirs(out_dir, exist_ok=True)

        dst = os.path.join(out_dir, os.path.basename(src))
        if os.path.abspath(src) != os.path.abspath(dst):
            try:
                shutil.copy(src, dst)
            except Exception as e:
                self.report({"ERROR"}, f"No se pudo copiar el archivo: {e}")
                return {"CANCELLED"}

        bpy.ops.ch1st.refresh_poses()

        n_poses = len(data) if isinstance(data, list) else 1
        self.report({"INFO"}, f"Pose(s) importada(s): {os.path.basename(dst)} ({n_poses})")
        return {"FINISHED"}


class CH1ST_OT_ApplyImportedPose(Operator):
    bl_idname    = "ch1st.apply_imported_pose"
    bl_label     = "Ejecutar pose en el personaje"
    bl_description = "Aplica la pose seleccionada de la libreria directamente al armature, en el frame actual"
    bl_options   = {"REGISTER", "UNDO"}

    json_file:  EnumProperty(name="Archivo JSON", items=_enum_json_files)
    pose_index: EnumProperty(name="Pose",         items=_enum_poses_from_self_json)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Archivo JSON:")
        layout.prop(self, "json_file", text="")
        layout.separator()
        layout.label(text="Pose:")
        layout.prop(self, "pose_index", text="")

    def execute(self, context):
        from mathutils import Euler, Vector
        st    = context.scene.ch1st
        scene = context.scene

        armature = scene.objects.get(st.armature_name) if st.armature_name else None
        if not armature or armature.type != "ARMATURE":
            armature = next((o for o in scene.objects if o.type == "ARMATURE"), None)

        if not armature:
            blend_path = r"C:\Users\user\Desktop\Alfred_Animacion\estructura_lista\alfred.blend"
            if not os.path.isfile(blend_path):
                self.report({"ERROR"}, f"No hay armature en la escena y no se encontro: {blend_path}")
                return {"CANCELLED"}
            try:
                with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
                    arm_names = [n for n in data_from.objects if "chicken_1" in n.lower() or "rig" in n.lower()] or list(data_from.objects)
                    data_to.objects = arm_names
                for obj in data_to.objects:
                    if obj is None:
                        continue
                    scene.collection.objects.link(obj)
                    if obj.type == "ARMATURE":
                        armature = obj
                    for child in obj.children_recursive:
                        if child.name not in scene.objects:
                            scene.collection.objects.link(child)
                        if child.type == "ARMATURE" and armature is None:
                            armature = child
            except Exception as e:
                self.report({"ERROR"}, f"No se pudo importar el personaje desde {blend_path}: {e}")
                return {"CANCELLED"}

        if not armature or armature.type != "ARMATURE":
            self.report({"ERROR"}, "No se encontro ningun armature (ni en la escena ni en alfred.blend)")
            return {"CANCELLED"}

        st.armature_name = armature.name

        try:
            idx = int(self.pose_index)
        except (TypeError, ValueError):
            idx = 0

        files = list_json_files(st.poses_dir)
        if not (0 <= int(self.json_file) < len(files)):
            self.report({"ERROR"}, "Archivo JSON no valido")
            return {"CANCELLED"}
        json_file = files[int(self.json_file)]

        record = get_pose_record(st.poses_dir, json_file, idx)
        if not record:
            self.report({"ERROR"}, "Pose no encontrada en el archivo seleccionado")
            return {"CANCELLED"}

        pose_dict = pose_record_to_full_dict(record)

        context.view_layer.objects.active = armature
        applied = 0
        for bone_name, bdata in pose_dict.items():
            pb = armature.pose.bones.get(bone_name)
            if not pb:
                continue
            pb.rotation_mode = "XYZ"
            pb.rotation_euler = Euler(bdata["rot"], "XYZ")
            pb.location       = Vector(bdata["loc"])
            if "scale" in bdata:
                pb.scale = Vector(bdata["scale"])
            applied += 1

        context.view_layer.update()
        self.report({"INFO"}, f"Pose '{record.get('label', json_file)}' aplicada ({applied} huesos)")
        return {"FINISHED"}


class CH1ST_OT_RefreshPoses(Operator):
    bl_idname    = "ch1st.refresh_poses"
    bl_label     = "Actualizar poses"
    bl_description = (
        "Escanea la carpeta de poses y actualiza la lista de archivos JSON disponibles. "
        "Usalo despues de exportar nuevas poses para que aparezcan en los selectores"
    )

    def execute(self, context):
        st     = context.scene.ch1st
        folder = bpy.path.abspath(st.poses_dir)
        if not folder or not os.path.isdir(folder):
            self.report({"WARNING"}, f"Carpeta no encontrada: {folder}")
            return {"CANCELLED"}
        files = sorted(f for f in os.listdir(folder) if f.endswith(".json"))
        # Contar poses totales en todos los archivos
        total_poses = 0
        for fn in files:
            fp = os.path.join(folder, fn)
            total_poses += len(load_json_poses(fp))
        # Forzar re-evaluacion de EnumProperty tocando poses_dir
        tmp = st.poses_dir
        st.poses_dir = ""
        st.poses_dir = tmp
        self.report(
            {"INFO"},
            f"Poses actualizadas: {len(files)} archivo(s)  —  {total_poses} pose(s) en total"
        )
        return {"FINISHED"}

class CH1ST_OT_ReloadHistoria(Operator):
    """Recarga el historia_chicken_1.json y actualiza info del key_point."""
    bl_idname    = "ch1st.reload_historia"
    bl_label     = "Recargar JSON historia"
    bl_description = "Lee historia_chicken_1.json y actualiza la lista de key_points disponibles"

    def execute(self, context):
        st = context.scene.ch1st
        historia = load_historia_json(st.historia_json)
        kps = get_key_points(historia)
        ori = historia.get("configuracion", {}).get("orientacion_inicial", {})
        if kps:
            self.report({"INFO"},
                f"JSON cargado: {len(kps)} key_points  |  orientacion_inicial rz={ori.get('rotacion_z', 0)}")
            st.key_point_info = (
                f"{len(kps)} puntos  |  rz={ori.get('rotacion_z', 0)}"
            )
        else:
            self.report({"WARNING"}, "No se encontraron key_points en el JSON")
            st.key_point_info = "-- sin key_points --"
        return {"FINISHED"}

class CH1ST_OT_ApplyKeyPointToRoot(Operator):
    """Aplica la coordenada del key_point al Empty 'chicken_1' que es la raiz del personaje."""
    bl_idname = "ch1st.apply_key_point_to_root"
    bl_label = "Aplicar KeyPoint a Posicion Root"
    bl_description = "Mueve el Empty 'chicken_1' a la coordenada del KeyPoint, convirtiendo el sistema de coordenadas (asume Y-arriba en JSON)"

    def execute(self, context):
        st = context.scene.ch1st

        # 1. Encontrar el objeto Empty 'chicken_1' que es la raiz del personaje.
        root_empty = context.scene.objects.get("chicken_1")
        if not root_empty or root_empty.type != 'EMPTY':
            self.report({"WARNING"}, "No se encuentra el objeto Empty 'chicken_1' que actua como raiz del personaje.")
            return {"CANCELLED"}

        # 2. Cargar datos del JSON de historia
        historia = load_historia_json(st.historia_json)
        kps = get_key_points(historia)
        if not kps:
            self.report({"WARNING"}, "No hay key_points cargados desde historia_chicken_1.json")
            return {"CANCELLED"}

        # 3. Encontrar el key_point seleccionado
        selected_idx = int(st.root_pos_key_point)
        target_kp = next((kp for kp in kps if kp.get("index") == selected_idx), None)

        if not target_kp:
            self.report({"WARNING"}, f"No se encontro el key_point con indice {selected_idx}")
            return {"CANCELLED"}

        # 4. Obtener coordenadas del JSON
        coords = target_kp.get("coordinates", {})
        pos_x = coords.get("x", 0.0)
        pos_y = coords.get("y", 0.0)
        pos_z = coords.get("z", 0.0)

        # 5. Aplicar al Empty 'chicken_1' con conversion de coordenadas
        # Z del JSON es la altura, igual que en Blender (Z-up). Se realiza un mapeo directo.
        # Conversion: (X_json, Y_json, Z_json) -> (X_blend, Y_blend, Z_blend)
        new_loc = (pos_x, pos_y, pos_z)

        # Asegurarse de que estamos en modo objeto para mover el Empty
        if context.object and context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        root_empty.location = new_loc

        # 6. CRITICO: Insertar keyframes en TODOS los frames de la animacion para
        #    fijar la posicion del root. Sin esto, Blender interpola desde (0,0,0)
        #    al reproducir y el personaje regresa al origen.
        scene = context.scene
        frame_start = scene.frame_start
        frame_end   = scene.frame_end

        # Limpiar fcurves de location del Empty alfred para evitar conflictos
        # con keyframes anteriores que puedan arrastrar al root a (0,0,0).
        if root_empty.animation_data and root_empty.animation_data.action:
            action = root_empty.animation_data.action
            for fc in list(get_fcurves(action)):
                if fc.data_path == "location":
                    get_fcurves(action).remove(fc)

        # Insertar un keyframe en frame_start y frame_end con la nueva posicion.
        # Esto crea una curva plana constante: el root no se mueve durante toda
        # la animacion.
        for frm in (frame_start, frame_end):
            scene.frame_set(frm)
            root_empty.location = new_loc
            root_empty.keyframe_insert(data_path="location", frame=frm)

        # Restaurar el frame actual al frame de inicio para no desorientar al usuario.
        scene.frame_set(frame_start)

        # 7. Actualizar las propiedades de posicion de inicio/fin del addon para
        #    que cuando se regenere la animacion (Exportar / Importar) el root
        #    arranque desde esta coordenada y no desde (0,0,0).

        self.report({"INFO"}, (
            f"Posicion de la raiz '{root_empty.name}' fijada en: "
            f"({new_loc[0]:.2f}, {new_loc[1]:.2f}, {new_loc[2]:.2f}) "
            f"durante toda la animacion (frames {frame_start}-{frame_end})."
        ))

        return {"FINISHED"}


# =============================================================================
# RESET
# =============================================================================

class CH1ST_OT_Reset(Operator):
    bl_idname    = "ch1st.reset"
    bl_label     = "RESET - Limpiar escena"
    bl_description = "Limpia la secuencia, vuelve al T-pose y borra la animacion generada"
    bl_options   = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        st    = context.scene.ch1st
        scene = context.scene

        # ── Secuencia de poses ──────────────────────────────────────────────
        st.action_poses.clear()
        st.action_pose_idx     = 0

        # ── Estado general ──────────────────────────────────────────────────
        st.anim_generated      = False
        st.total_frames_gen    = 0
        st.end_frame_gen       = 0
        st.status_msg          = ""
        st.last_export_path    = ""
        st.extract_label       = ""
        st.key_point_info      = "-- carga el JSON primero --"

        # ── Sistema de ojos: propiedades ─────────────────────────────────────
        eye_s = st.eye_expr
        eye_s.enabled            = False
        eye_s.active_expression  = "NEUTRAL"
        eye_s.expression_value   = 1.0
        eye_s.blink_enabled      = False
        eye_s.blink_count        = 2
        eye_s.blink_duration     = 9
        eye_s.blink_frame_start  = 1
        eye_s.blink_frame_end    = 60
        eye_s.lib_frame_start    = 1
        eye_s.lib_duration       = 20
        eye_s.lib_interp_type    = "SMOOTH"
        eye_s.geo_edit_mode      = "NONE"
        eye_s.geo_intensity      = 1.0
        # Transforms a posicion base de Alfred
        eye_s.eye_L_loc_x, eye_s.eye_L_loc_y, eye_s.eye_L_loc_z =  0.106646, 0.270456, 1.70082
        eye_s.eye_L_rot_x = eye_s.eye_L_rot_y = eye_s.eye_L_rot_z = 0.0
        eye_s.eye_L_sca_x = eye_s.eye_L_sca_y = eye_s.eye_L_sca_z = 1.0
        eye_s.eye_R_loc_x, eye_s.eye_R_loc_y, eye_s.eye_R_loc_z = -0.1053,   0.256331, 1.70043
        eye_s.eye_R_rot_x = eye_s.eye_R_rot_y = eye_s.eye_R_rot_z = 0.0
        eye_s.eye_R_sca_x = eye_s.eye_R_sca_y = eye_s.eye_R_sca_z = 1.0

        # ── Sistema de ojos: objetos en escena ───────────────────────────────
        _EYE_BASE = {
            obj_name: (td["loc"], td["rot"], td["sca"])
            for obj_name, td in EYE_BASE_TRANSFORMS.items()
        }
        for obj_name, (loc, rot, sca) in _EYE_BASE.items():
            obj = scene.objects.get(obj_name)
            if not obj:
                continue
            # Limpiar action propia del ojo
            if obj.animation_data and obj.animation_data.action:
                old_act = obj.animation_data.action
                obj.animation_data.action = None
                bpy.data.actions.remove(old_act)
            # Restaurar transforms a posicion base
            obj.location       = loc
            obj.rotation_euler = rot
            obj.scale          = sca
            # Resetear todos los shape keys a 0
            if obj.data.shape_keys:
                for kb in obj.data.shape_keys.key_blocks:
                    if kb.name != "Basis":
                        kb.value = 0.0

        # ── Libreria de ojos: limpiar lista ─────────────────────────────────
        st.eye_lib_entries.clear()
        st.eye_lib_idx       = 0
        st.eye_lib_save_name = ""
        st.eye_lib_save_desc = ""

        # ── Armature: T-pose y limpiar animacion ─────────────────────────────
        if st.armature_name:
            arm = scene.objects.get(st.armature_name)
            if arm and arm.animation_data and arm.animation_data.action:
                old = arm.animation_data.action
                arm.animation_data.action = None
                bpy.data.actions.remove(old)
            if arm and arm.type == "ARMATURE":
                context.view_layer.objects.active = arm
                if arm.mode != "POSE":
                    bpy.ops.object.mode_set(mode="POSE")
                for pb in arm.pose.bones:
                    pb.rotation_mode  = "XYZ"
                    pb.rotation_euler = (0.0, 0.0, 0.0)
                    pb.location       = (0.0, 0.0, 0.0)
                    pb.scale          = (1.0, 1.0, 1.0)

        # ── Objeto root "chicken_1": limpiar action y posicion ─────────────────
        root_obj = scene.objects.get("chicken_1")
        if root_obj and root_obj != scene.objects.get(st.armature_name):
            if root_obj.animation_data and root_obj.animation_data.action:
                old_root = root_obj.animation_data.action
                root_obj.animation_data.action = None
                bpy.data.actions.remove(old_root)
            root_obj.location       = (0.0, 0.0, 0.0)
            root_obj.rotation_euler = (0.0, 0.0, 0.0)
            root_obj.scale          = (1.0, 1.0, 1.0)

        scene.frame_set(st.start_frame)
        self.report({"INFO"}, "Escena limpiada -- personaje en estado inicial")
        return {"FINISHED"}

# =============================================================================
# POSES DE ACCION (sin cambios respecto a v1.2)
# =============================================================================

class CH1ST_OT_AddActionPose(Operator):
    bl_idname    = "ch1st.add_action_pose"
    bl_label     = "Agregar pose de accion"
    bl_description = "Agrega una pose intermedia a la secuencia"
    bl_options   = {"REGISTER", "UNDO"}

    json_file:  EnumProperty(name="Archivo JSON", items=_enum_json_files)
    pose_index: EnumProperty(name="Pose",         items=_enum_poses_from_self_json)
    duration:   IntProperty(name="Duracion (frames)", default=20, min=2, soft_max=99999)
    rot_x: FloatProperty(name="Rot X (grados)", default=0.0,
        description="Rotacion X del root en esta pose (0 = sin rotacion)")
    rot_y: FloatProperty(name="Rot Y (grados)", default=0.0,
        description="Rotacion Y del root en esta pose (0 = sin rotacion)")
    rot_z: FloatProperty(name="Rot Z (grados)", default=0.0,
        description="Rotacion Z del root en esta pose (0 = sin rotacion)")
    pos_x: FloatProperty(name="Pos X", default=0.0,
        description="Posicion X del root (alfred/Empty) en esta pose de accion")
    pos_y: FloatProperty(name="Pos Y", default=0.0,
        description="Posicion Y del root (alfred/Empty) en esta pose de accion")
    pos_z: FloatProperty(name="Pos Z", default=0.0,
        description="Posicion Z del root (alfred/Empty) en esta pose de accion")
    interp_type: EnumProperty(
        name="Interpolacion",
        description="Curva de interpolacion profesional para esta pose de accion",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Paso 1 -- Elige el archivo JSON:")
        layout.prop(self, "json_file", text="")
        layout.separator()
        layout.label(text="Paso 2 -- Elige la pose de accion:")
        layout.prop(self, "pose_index", text="")
        layout.separator()
        layout.label(text="Paso 3 -- Duracion de este segmento:")
        layout.prop(self, "duration", text="Frames")
        layout.separator()
        box = layout.box()
        box.label(text="Paso 4 -- Tipo de interpolacion:", icon="IPO_BEZIER")
        box.prop(self, "interp_type", text="")
        layout.separator()
        box2 = layout.box()
        box2.label(text="Paso 5 -- Posicion del Root (alfred/Empty):", icon="OBJECT_ORIGIN")
        row = box2.row(align=True)
        row.prop(self, "pos_x", text="X")
        row.prop(self, "pos_y", text="Y")
        row.prop(self, "pos_z", text="Z")
        layout.separator()
        box3 = layout.box()
        box3.label(text="Paso 6 -- Orientacion del Root (rotacion):", icon="ORIENTATION_LOCAL")
        box3.label(text="  (deja en 0 si no necesitas rotacion especifica)", icon="INFO")
        col = box3.column(align=True)
        col.prop(self, "rot_x", text="Rot X")
        col.prop(self, "rot_y", text="Rot Y")
        col.prop(self, "rot_z", text="Rot Z")

    def execute(self, context):
        if self.json_file == "NONE":
            self.report({"WARNING"}, "No hay archivos JSON en la carpeta de poses")
            return {"CANCELLED"}
        st    = context.scene.ch1st
        jf    = _json_file_from_index(self, context)
        idx   = int(self.pose_index)
        fp    = os.path.join(bpy.path.abspath(st.poses_dir), jf)
        poses = load_json_poses(fp)
        name  = poses[idx].get("label", "?") if poses and idx < len(poses) else "?"

        item             = st.action_poses.add()
        item.pose_name   = name
        item.json_file   = jf
        item.pose_index  = idx
        item.duration    = self.duration
        item.rot_x       = self.rot_x
        item.rot_y       = self.rot_y
        item.rot_z       = self.rot_z
        item.pos_x       = self.pos_x
        item.pos_y       = self.pos_y
        item.pos_z       = self.pos_z
        item.interp_type = self.interp_type
        st.action_pose_idx = len(st.action_poses) - 1
        self.report({"INFO"}, f"Pose agregada: '{name}'  [{jf}]  pos=({self.pos_x:.2f},{self.pos_y:.2f},{self.pos_z:.2f})  interp={self.interp_type}")
        return {"FINISHED"}


class CH1ST_OT_EditActionPose(Operator):
    bl_idname    = "ch1st.edit_action_pose"
    bl_label     = "Editar pose de accion"
    bl_description = "Cambia la duracion, posicion, orientacion e interpolacion de la pose seleccionada"
    bl_options   = {"REGISTER", "UNDO"}

    duration: IntProperty(name="Duracion (frames)", default=20, min=2, soft_max=99999)
    rot_x: FloatProperty(name="Rot X (grados)", default=0.0)
    rot_y: FloatProperty(name="Rot Y (grados)", default=0.0)
    rot_z: FloatProperty(name="Rot Z (grados)", default=0.0)
    pos_x: FloatProperty(name="Pos X", default=0.0)
    pos_y: FloatProperty(name="Pos Y", default=0.0)
    pos_z: FloatProperty(name="Pos Z", default=0.0)
    interp_type: EnumProperty(
        name="Interpolacion",
        description="Curva de interpolacion profesional para esta pose de accion",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )

    def invoke(self, context, event):
        st = context.scene.ch1st
        if st.action_poses and 0 <= st.action_pose_idx < len(st.action_poses):
            item = st.action_poses[st.action_pose_idx]
            self.duration    = item.duration
            self.rot_x       = item.rot_x
            self.rot_y       = item.rot_y
            self.rot_z       = item.rot_z
            self.pos_x       = item.pos_x
            self.pos_y       = item.pos_y
            self.pos_z       = item.pos_z
            self.interp_type = item.interp_type
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "duration")
        layout.separator()
        box = layout.box()
        box.label(text="Tipo de interpolacion:", icon="IPO_BEZIER")
        box.prop(self, "interp_type", text="")
        layout.separator()
        box2 = layout.box()
        box2.label(text="Posicion del Root (alfred/Empty):", icon="OBJECT_ORIGIN")
        row = box2.row(align=True)
        row.prop(self, "pos_x", text="X")
        row.prop(self, "pos_y", text="Y")
        row.prop(self, "pos_z", text="Z")
        layout.separator()
        box3 = layout.box()
        box3.label(text="Orientacion del Root (rotacion):", icon="ORIENTATION_LOCAL")
        col = box3.column(align=True)
        col.prop(self, "rot_x", text="Rot X")
        col.prop(self, "rot_y", text="Rot Y")
        col.prop(self, "rot_z", text="Rot Z")

    def execute(self, context):
        st = context.scene.ch1st
        if st.action_poses and 0 <= st.action_pose_idx < len(st.action_poses):
            item             = st.action_poses[st.action_pose_idx]
            item.duration    = self.duration
            item.rot_x       = self.rot_x
            item.rot_y       = self.rot_y
            item.rot_z       = self.rot_z
            item.pos_x       = self.pos_x
            item.pos_y       = self.pos_y
            item.pos_z       = self.pos_z
            item.interp_type = self.interp_type
        return {"FINISHED"}

class CH1ST_OT_RemoveActionPose(Operator):
    bl_idname = "ch1st.remove_action_pose"
    bl_label  = "Eliminar pose"

    def execute(self, context):
        st = context.scene.ch1st
        if st.action_poses and 0 <= st.action_pose_idx < len(st.action_poses):
            st.action_poses.remove(st.action_pose_idx)
            st.action_pose_idx = max(0, st.action_pose_idx - 1)
        return {"FINISHED"}

class CH1ST_OT_MoveActionPose(Operator):
    bl_idname = "ch1st.move_action_pose"
    bl_label  = "Mover pose"
    direction: EnumProperty(items=[("UP","Arriba",""),("DOWN","Abajo","")])

    def execute(self, context):
        st  = context.scene.ch1st
        idx = st.action_pose_idx
        lst = st.action_poses
        if self.direction == "UP" and idx > 0:
            lst.move(idx, idx-1)
            st.action_pose_idx = idx-1
        elif self.direction == "DOWN" and idx < len(lst)-1:
            lst.move(idx, idx+1)
            st.action_pose_idx = idx+1
        return {"FINISHED"}



# =============================================================================
# OPERADORES DE SECUENCIA DE OJOS
# =============================================================================

class CH1ST_OT_AddEyeSlot(Operator):
    """Agrega un nuevo estado de ojos a la lista de cambios intermedios"""
    bl_idname  = "ch1st.add_eye_slot"
    bl_label   = "Agregar estado de ojos"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        st   = context.scene.ch1st
        slot = st.eye_slots.add()
        slot.slot_label = f"Estado ojos {len(st.eye_slots)}"
        st.eye_slot_idx = len(st.eye_slots) - 1
        return {"FINISHED"}


class CH1ST_OT_RemoveEyeSlot(Operator):
    """Elimina el estado de ojos seleccionado"""
    bl_idname  = "ch1st.remove_eye_slot"
    bl_label   = "Eliminar estado de ojos"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        st = context.scene.ch1st
        if st.eye_slots and 0 <= st.eye_slot_idx < len(st.eye_slots):
            st.eye_slots.remove(st.eye_slot_idx)
            st.eye_slot_idx = max(0, st.eye_slot_idx - 1)
        return {"FINISHED"}


class CH1ST_OT_DuplicateEyeSlot(Operator):
    """Copia el estado de ojos seleccionado y lo pega al final de la lista"""
    bl_idname   = "ch1st.duplicate_eye_slot"
    bl_label    = "Copiar estado de ojos"
    bl_description = (
        "Duplica el estado de ojos seleccionado (todos sus valores: "
        "expresion, geometria, posicion, rotacion, escala) y lo agrega al final de la lista"
    )
    bl_options = {"REGISTER", "UNDO"}

    # Lista completa de campos a copiar — debe coincidir con Chicken1EyeSlotItem
    _FIELDS = (
        "slot_label", "duration", "interp_type",
        "active_expression", "expression_value",
        "geo_edit_mode", "geo_intensity",
        "eye_L_loc_x", "eye_L_loc_y", "eye_L_loc_z",
        "eye_L_rot_x", "eye_L_rot_y", "eye_L_rot_z",
        "eye_L_sca_x", "eye_L_sca_y", "eye_L_sca_z",
        "eye_R_loc_x", "eye_R_loc_y", "eye_R_loc_z",
        "eye_R_rot_x", "eye_R_rot_y", "eye_R_rot_z",
        "eye_R_sca_x", "eye_R_sca_y", "eye_R_sca_z",
    )

    def execute(self, context):
        st  = context.scene.ch1st
        idx = st.eye_slot_idx

        if not st.eye_slots:
            self.report({"WARNING"}, "No hay estados de ojos para copiar")
            return {"CANCELLED"}
        if not (0 <= idx < len(st.eye_slots)):
            self.report({"WARNING"}, "Selecciona un estado de ojos antes de copiar")
            return {"CANCELLED"}

        src = st.eye_slots[idx]

        # Capturar todos los valores ANTES de agregar (add() puede invalidar el ref)
        snapshot = {f: getattr(src, f) for f in self._FIELDS}

        # Agregar nuevo slot al final y copiar valores
        new_slot = st.eye_slots.add()
        for field, val in snapshot.items():
            if field == "slot_label":
                # Añadir sufijo " (copia)" para que sea identificable
                setattr(new_slot, field, f"{val} (copia)")
            else:
                setattr(new_slot, field, val)

        # Seleccionar el nuevo slot
        st.eye_slot_idx = len(st.eye_slots) - 1

        self.report({"INFO"},
            f"Estado '{snapshot['slot_label']}' copiado al final "
            f"({len(st.eye_slots)} estados en total)")
        return {"FINISHED"}


class CH1ST_OT_MoveEyeSlot(Operator):
    """Mueve el estado de ojos seleccionado arriba o abajo"""
    bl_idname  = "ch1st.move_eye_slot"
    bl_label   = "Mover estado de ojos"
    bl_options = {"REGISTER", "UNDO"}

    direction: EnumProperty(
        items=[("UP", "Arriba", ""), ("DOWN", "Abajo", "")],
    )

    def execute(self, context):
        st  = context.scene.ch1st
        idx = st.eye_slot_idx
        lst = st.eye_slots
        if self.direction == "UP" and idx > 0:
            lst.move(idx, idx - 1)
            st.eye_slot_idx = idx - 1
        elif self.direction == "DOWN" and idx < len(lst) - 1:
            lst.move(idx, idx + 1)
            st.eye_slot_idx = idx + 1
        return {"FINISHED"}

# =============================================================================
# OPERADORES CRUD — INTERVALOS DE PARPADEO AUTOMATICO
# =============================================================================

class CH1ST_OT_BlinkIntervalAdd(Operator):
    """Agrega un nuevo intervalo de parpadeo automatico"""
    bl_idname  = "ch1st.blink_interval_add"
    bl_label   = "Agregar intervalo de parpadeo"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        st = context.scene.ch1st
        bi = st.blink_intervals.add()
        bi.label          = f"Parpadeo {len(st.blink_intervals)}"
        bi.frame_start    = 1
        bi.frame_end      = 60
        bi.blink_count    = 2
        bi.blink_duration = 9
        st.blink_interval_idx = len(st.blink_intervals) - 1
        return {"FINISHED"}


class CH1ST_OT_BlinkIntervalRemove(Operator):
    """Elimina el intervalo de parpadeo seleccionado"""
    bl_idname  = "ch1st.blink_interval_remove"
    bl_label   = "Eliminar intervalo de parpadeo"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        st = context.scene.ch1st
        if st.blink_intervals and 0 <= st.blink_interval_idx < len(st.blink_intervals):
            st.blink_intervals.remove(st.blink_interval_idx)
            st.blink_interval_idx = max(0, st.blink_interval_idx - 1)
        return {"FINISHED"}


class CH1ST_OT_BlinkIntervalDuplicate(Operator):
    """Copia el intervalo de parpadeo seleccionado"""
    bl_idname  = "ch1st.blink_interval_duplicate"
    bl_label   = "Copiar intervalo de parpadeo"
    bl_options = {"REGISTER", "UNDO"}
    _FIELDS    = ("label", "frame_start", "frame_end", "blink_count", "blink_duration", "enabled")

    def execute(self, context):
        st  = context.scene.ch1st
        idx = st.blink_interval_idx
        if not st.blink_intervals or not (0 <= idx < len(st.blink_intervals)):
            self.report({"WARNING"}, "Selecciona un intervalo primero")
            return {"CANCELLED"}
        snap = {f: getattr(st.blink_intervals[idx], f) for f in self._FIELDS}
        new  = st.blink_intervals.add()
        for f, v in snap.items():
            setattr(new, f, f"{v} (copia)" if f == "label" else v)
        st.blink_interval_idx = len(st.blink_intervals) - 1
        return {"FINISHED"}


class CH1ST_OT_BlinkIntervalMove(Operator):
    """Mueve el intervalo de parpadeo arriba o abajo"""
    bl_idname  = "ch1st.blink_interval_move"
    bl_label   = "Mover intervalo de parpadeo"
    bl_options = {"REGISTER", "UNDO"}
    direction: EnumProperty(items=[("UP", "Arriba", ""), ("DOWN", "Abajo", "")])

    def execute(self, context):
        st  = context.scene.ch1st
        idx = st.blink_interval_idx
        lst = st.blink_intervals
        if self.direction == "UP" and idx > 0:
            lst.move(idx, idx - 1); st.blink_interval_idx = idx - 1
        elif self.direction == "DOWN" and idx < len(lst) - 1:
            lst.move(idx, idx + 1); st.blink_interval_idx = idx + 1
        return {"FINISHED"}


# =============================================================================
# OPERADORES CRUD — INTERVALOS DE EXPRESIONES DE OJOS
# =============================================================================

class CH1ST_OT_ExprIntervalAdd(Operator):
    """Agrega un nuevo intervalo de expresion de ojos"""
    bl_idname  = "ch1st.expr_interval_add"
    bl_label   = "Agregar intervalo de expresion"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        st = context.scene.ch1st
        ei = st.expr_intervals.add()
        ei.label       = f"Expresion {len(st.expr_intervals)}"
        ei.frame_start = 1
        ei.frame_peak  = 20
        ei.frame_end   = 40
        st.expr_interval_idx = len(st.expr_intervals) - 1
        return {"FINISHED"}


class CH1ST_OT_ExprIntervalRemove(Operator):
    """Elimina el intervalo de expresion seleccionado"""
    bl_idname  = "ch1st.expr_interval_remove"
    bl_label   = "Eliminar intervalo de expresion"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        st = context.scene.ch1st
        if st.expr_intervals and 0 <= st.expr_interval_idx < len(st.expr_intervals):
            st.expr_intervals.remove(st.expr_interval_idx)
            st.expr_interval_idx = max(0, st.expr_interval_idx - 1)
        return {"FINISHED"}


class CH1ST_OT_ExprIntervalDuplicate(Operator):
    """Copia el intervalo de expresion seleccionado"""
    bl_idname  = "ch1st.expr_interval_duplicate"
    bl_label   = "Copiar intervalo de expresion"
    bl_options = {"REGISTER", "UNDO"}
    _FIELDS    = ("label", "frame_start", "frame_peak", "frame_end",
                  "expression", "expression_value", "interp_in", "interp_out", "enabled")

    def execute(self, context):
        st  = context.scene.ch1st
        idx = st.expr_interval_idx
        if not st.expr_intervals or not (0 <= idx < len(st.expr_intervals)):
            self.report({"WARNING"}, "Selecciona un intervalo primero")
            return {"CANCELLED"}
        snap = {f: getattr(st.expr_intervals[idx], f) for f in self._FIELDS}
        new  = st.expr_intervals.add()
        for f, v in snap.items():
            setattr(new, f, f"{v} (copia)" if f == "label" else v)
        st.expr_interval_idx = len(st.expr_intervals) - 1
        return {"FINISHED"}


class CH1ST_OT_ExprIntervalMove(Operator):
    """Mueve el intervalo de expresion arriba o abajo"""
    bl_idname  = "ch1st.expr_interval_move"
    bl_label   = "Mover intervalo de expresion"
    bl_options = {"REGISTER", "UNDO"}
    direction: EnumProperty(items=[("UP", "Arriba", ""), ("DOWN", "Abajo", "")])

    def execute(self, context):
        st  = context.scene.ch1st
        idx = st.expr_interval_idx
        lst = st.expr_intervals
        if self.direction == "UP" and idx > 0:
            lst.move(idx, idx - 1); st.expr_interval_idx = idx - 1
        elif self.direction == "DOWN" and idx < len(lst) - 1:
            lst.move(idx, idx + 1); st.expr_interval_idx = idx + 1
        return {"FINISHED"}



class CH1ST_OT_ResetEyeSequence(Operator):
    """
    Resetea completamente el sistema de ojos:
      - Borra todos los slots intermedios
      - Limpia la action animada de los shape keys de los ojos
      - Restaura los shape keys a 0
      - Resetea las propiedades de parpadeo
      - Devuelve los ojos a su posicion base en el rostro de Alfred
    """
    bl_idname   = "ch1st.reset_eye_sequence"
    bl_label    = "RESET  Sistema de Ojos"
    bl_description = (
        "Limpia toda la animacion de ojos: borra slots intermedios, "
        "elimina keyframes de shape keys y restaura los ojos a su estado base"
    )
    bl_options  = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        st    = context.scene.ch1st
        eye_s = st.eye_expr

        # ── Borrar slots intermedios ─────────────────────────────────────────
        st.eye_slots.clear()
        st.eye_slot_idx = 0

        # ── Resetear propiedades de secuencia ────────────────────────────────
        st.eye_global_start_frame    = 1
        st.eye_start_duration        = 20
        st.eye_start_interp          = "SMOOTH"
        st.eye_start_blink_mode      = "BLINK"
        st.eye_start_blink_count     = 2
        st.eye_start_blink_duration  = 9
        st.eye_end_duration          = 20
        st.eye_end_interp            = "SMOOTH"
        st.eye_end_blink_mode        = "BLINK"
        st.eye_end_blink_count       = 2
        st.eye_end_blink_duration    = 9

        # ── Resetear parpadeo y listas de intervalos ─────────────────────────
        eye_s.blink_enabled     = False
        eye_s.blink_count       = 2
        eye_s.blink_duration    = 9
        eye_s.blink_frame_start = 1
        eye_s.blink_frame_end   = 60
        # Limpiar intervalos multi-sistema
        st.blink_intervals.clear()
        st.blink_interval_idx = 0
        eye_s.expr_intervals_enabled = False
        st.expr_intervals.clear()
        st.expr_interval_idx = 0

        # ── Limpiar animacion y restaurar transforms reales de los ojos ──────
        for obj_name, base in EYE_BASE_TRANSFORMS.items():
            obj = scene.objects.get(obj_name)
            if not obj:
                continue
            # Limpiar action de shape keys
            if obj.data.shape_keys and obj.data.shape_keys.animation_data:
                anim = obj.data.shape_keys.animation_data
                if anim.action:
                    bpy.data.actions.remove(anim.action)
                    anim.action = None
            # Resetear valores de shape keys a 0
            if obj.data.shape_keys:
                for kb in obj.data.shape_keys.key_blocks:
                    if kb.name != "Basis":
                        kb.value = 0.0
            # Limpiar action del objeto
            if obj.animation_data and obj.animation_data.action:
                bpy.data.actions.remove(obj.animation_data.action)
                obj.animation_data.action = None
            # Restaurar transforms reales (loc/rot/sca del .blend original)
            obj.location       = base["loc"]
            obj.rotation_euler = base["rot"]
            obj.scale          = base["sca"]

        scene.frame_set(1)
        self.report({"INFO"}, "Sistema de ojos reseteado — geometria base restaurada")
        return {"FINISHED"}


class CH1ST_OT_EditEyeSlot(Operator):
    """Edita los parametros del estado de ojos seleccionado (popup)"""
    bl_idname   = "ch1st.edit_eye_slot"
    bl_label    = "Editar estado de ojos"
    bl_options  = {"REGISTER", "UNDO"}

    from .constants import INTERP_TYPE_ITEMS, EXPRESSION_PRESETS

    # ── Identificador ────────────────────────────────────────────────────
    slot_label: StringProperty(name="Etiqueta", default="Estado ojos")
    duration:   IntProperty(name="Frames", default=20, min=1, soft_max=99999)
    interp_type: EnumProperty(
        name="Transicion",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )

    # ── Expresion ────────────────────────────────────────────────────────
    active_expression: EnumProperty(name="Expresion", items=EXPRESSION_PRESETS, default="NEUTRAL")
    expression_value:  FloatProperty(name="Valor expresion", default=0.05, min=0.0, max=0.05, precision=2)

    # ── Geometria ────────────────────────────────────────────────────────
    geo_edit_mode: EnumProperty(
        name="Forma de ojo",
        items=[
            ("NONE",   "Sin cambio",    ""),
            ("ROUND",  "Redondo",       ""),
            ("SQUINT", "Entrecerrado",  ""),
            ("WIDE",   "Abierto ancho", ""),
            ("FLAT",   "Plano/cerrado", ""),
            ("CUSTOM", "Personalizado", ""),
        ],
        default="NONE",
    )
    geo_intensity: FloatProperty(name="Intensidad forma", default=1.0, min=0.0, max=2.0, precision=2)

    # ── Ojo Izquierdo ────────────────────────────────────────────────────
    eye_L_loc_x: FloatProperty(name="Loc X", default=0.106646, precision=4)
    eye_L_loc_y: FloatProperty(name="Loc Y", default=0.270456, precision=4)
    eye_L_loc_z: FloatProperty(name="Loc Z", default=1.70082,  precision=4)
    eye_L_rot_x: FloatProperty(name="Rot X", default=0.0, subtype="ANGLE")
    eye_L_rot_y: FloatProperty(name="Rot Y", default=0.0, subtype="ANGLE")
    eye_L_rot_z: FloatProperty(name="Rot Z", default=0.0, subtype="ANGLE")
    eye_L_sca_x: FloatProperty(name="Sca X", default=1.555, min=0.001, max=10.0, precision=3)
    eye_L_sca_y: FloatProperty(name="Sca Y", default=0.496018, min=0.001, max=10.0, precision=3)
    eye_L_sca_z: FloatProperty(name="Sca Z", default=3.55, min=0.001, max=10.0, precision=3)

    # ── Ojo Derecho ──────────────────────────────────────────────────────
    eye_R_loc_x: FloatProperty(name="Loc X", default=-0.1053,  precision=4)
    eye_R_loc_y: FloatProperty(name="Loc Y", default=0.256331, precision=4)
    eye_R_loc_z: FloatProperty(name="Loc Z", default=1.70043,  precision=4)
    eye_R_rot_x: FloatProperty(name="Rot X", default=0.0, subtype="ANGLE")
    eye_R_rot_y: FloatProperty(name="Rot Y", default=0.0, subtype="ANGLE")
    eye_R_rot_z: FloatProperty(name="Rot Z", default=0.0, subtype="ANGLE")
    eye_R_sca_x: FloatProperty(name="Sca X", default=1.555, min=0.001, max=10.0, precision=3)
    eye_R_sca_y: FloatProperty(name="Sca Y", default=0.496018, min=0.001, max=10.0, precision=3)
    eye_R_sca_z: FloatProperty(name="Sca Z", default=3.55, min=0.001, max=10.0, precision=3)

    def invoke(self, context, event):
        st = context.scene.ch1st
        if st.eye_slots and 0 <= st.eye_slot_idx < len(st.eye_slots):
            item = st.eye_slots[st.eye_slot_idx]
            # Copiar datos del slot al operador
            for attr in ("slot_label", "duration", "interp_type",
                         "active_expression", "expression_value",
                         "geo_edit_mode", "geo_intensity",
                         "eye_L_loc_x", "eye_L_loc_y", "eye_L_loc_z",
                         "eye_L_rot_x", "eye_L_rot_y", "eye_L_rot_z",
                         "eye_L_sca_x", "eye_L_sca_y", "eye_L_sca_z",
                         "eye_R_loc_x", "eye_R_loc_y", "eye_R_loc_z",
                         "eye_R_rot_x", "eye_R_rot_y", "eye_R_rot_z",
                         "eye_R_sca_x", "eye_R_sca_y", "eye_R_sca_z"):
                setattr(self, attr, getattr(item, attr))
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Identificador", icon="GREASEPENCIL")
        box.prop(self, "slot_label", text="Etiqueta")
        row = box.row(align=True)
        row.prop(self, "duration",    text="Frames")
        row.prop(self, "interp_type", text="Transicion")

        box = layout.box()
        box.label(text="Expresion", icon="HIDE_OFF")
        col = box.column(align=True)
        col.prop(self, "active_expression", text="")
        col.prop(self, "expression_value",  text="Valor", slider=True)

        box = layout.box()
        box.label(text="Geometria / Forma", icon="MESH_CIRCLE")
        col = box.column(align=True)
        col.prop(self, "geo_edit_mode",  text="Forma")
        col.prop(self, "geo_intensity",  text="Intensidad", slider=True)

        box = layout.box()
        box.label(text="Ojo Izquierdo  —  Posicion / Rotacion / Escala", icon="BLANK1")
        col = box.column(align=True)
        col.label(text="Posicion", icon="EMPTY_AXIS")
        row = col.row(align=True)
        row.prop(self, "eye_L_loc_x", text="X")
        row.prop(self, "eye_L_loc_y", text="Y")
        row.prop(self, "eye_L_loc_z", text="Z")
        col.label(text="Rotacion", icon="ORIENTATION_GIMBAL")
        row2 = col.row(align=True)
        row2.prop(self, "eye_L_rot_x", text="X")
        row2.prop(self, "eye_L_rot_y", text="Y")
        row2.prop(self, "eye_L_rot_z", text="Z")
        col.label(text="Escala", icon="FULLSCREEN_ENTER")
        row3 = col.row(align=True)
        row3.prop(self, "eye_L_sca_x", text="X")
        row3.prop(self, "eye_L_sca_y", text="Y")
        row3.prop(self, "eye_L_sca_z", text="Z")

        box = layout.box()
        box.label(text="Ojo Derecho  —  Posicion / Rotacion / Escala", icon="BLANK1")
        col = box.column(align=True)
        col.label(text="Posicion", icon="EMPTY_AXIS")
        row = col.row(align=True)
        row.prop(self, "eye_R_loc_x", text="X")
        row.prop(self, "eye_R_loc_y", text="Y")
        row.prop(self, "eye_R_loc_z", text="Z")
        col.label(text="Rotacion", icon="ORIENTATION_GIMBAL")
        row2 = col.row(align=True)
        row2.prop(self, "eye_R_rot_x", text="X")
        row2.prop(self, "eye_R_rot_y", text="Y")
        row2.prop(self, "eye_R_rot_z", text="Z")
        col.label(text="Escala", icon="FULLSCREEN_ENTER")
        row3 = col.row(align=True)
        row3.prop(self, "eye_R_sca_x", text="X")
        row3.prop(self, "eye_R_sca_y", text="Y")
        row3.prop(self, "eye_R_sca_z", text="Z")

    def execute(self, context):
        st = context.scene.ch1st
        if st.eye_slots and 0 <= st.eye_slot_idx < len(st.eye_slots):
            item = st.eye_slots[st.eye_slot_idx]
            for attr in ("slot_label", "duration", "interp_type",
                         "active_expression", "expression_value",
                         "geo_edit_mode", "geo_intensity",
                         "eye_L_loc_x", "eye_L_loc_y", "eye_L_loc_z",
                         "eye_L_rot_x", "eye_L_rot_y", "eye_L_rot_z",
                         "eye_L_sca_x", "eye_L_sca_y", "eye_L_sca_z",
                         "eye_R_loc_x", "eye_R_loc_y", "eye_R_loc_z",
                         "eye_R_rot_x", "eye_R_rot_y", "eye_R_rot_z",
                         "eye_R_sca_x", "eye_R_sca_y", "eye_R_sca_z"):
                setattr(item, attr, getattr(self, attr))
        return {"FINISHED"}


class CH1ST_OT_ImportEyeSlotFromJson(Operator):
    """
    Importa un archivo .json de expresion de ojos y lo agrega
    como nuevo slot intermedio en la lista de cambios de ojos.
    El JSON debe tener el mismo formato que exporta 'Guardar en libreria'.
    """
    bl_idname   = "ch1st.import_eye_slot_from_json"
    bl_label    = "Importar cambio de ojos desde .json"
    bl_description = (
        "Selecciona un archivo .json de la libreria de ojos y lo agrega "
        "como nuevo estado intermedio en la secuencia de ojos"
    )
    bl_options  = {"REGISTER", "UNDO"}

    filepath:    StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        st      = context.scene.ch1st
        lib_dir = bpy.path.abspath(st.eye_lib_dir) if hasattr(st, "eye_lib_dir") else ""
        if lib_dir and os.path.isdir(lib_dir):
            self.filepath = lib_dir + os.sep
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        import json as _json
        if not self.filepath or not os.path.isfile(self.filepath):
            self.report({"ERROR"}, "Archivo no encontrado")
            return {"CANCELLED"}

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = _json.load(f)
        except Exception as e:
            self.report({"ERROR"}, f"No se pudo leer el JSON: {e}")
            return {"CANCELLED"}

        st   = context.scene.ch1st
        slot = st.eye_slots.add()
        st.eye_slot_idx = len(st.eye_slots) - 1

        # Nombre del slot: usar 'name' del JSON o el nombre del archivo
        slot.slot_label = data.get("name",
                          os.path.splitext(os.path.basename(self.filepath))[0])
        slot.duration   = int(data.get("duration",   20))
        slot.interp_type = data.get("interp_type", "SMOOTH")

        # Expresion
        expr = data.get("active_expression", "NEUTRAL")
        try:
            slot.active_expression = expr
        except Exception:
            pass
        slot.expression_value = float(data.get("expression_value", 1.0))

        # Geometria
        geo_mode = data.get("geo_edit_mode", "NONE")
        try:
            slot.geo_edit_mode = geo_mode
        except Exception:
            pass
        slot.geo_intensity = float(data.get("geo_intensity", 1.0))

        # Transforms ojo izquierdo
        tfL = data.get("transforms", {}).get("ojo_izquierdo_chicken_1", {})
        if tfL:
            _base_L = EYE_BASE_TRANSFORMS["ojo_izquierdo_chicken_1"]
            loc = tfL.get("location", list(_base_L["loc"]))
            rot = tfL.get("rotation_euler", list(_base_L["rot"]))
            sca = tfL.get("scale", list(_base_L["sca"]))
            slot.eye_L_loc_x, slot.eye_L_loc_y, slot.eye_L_loc_z = loc[0], loc[1], loc[2]
            import math as _math
            slot.eye_L_rot_x = _math.radians(rot[0])
            slot.eye_L_rot_y = _math.radians(rot[1])
            slot.eye_L_rot_z = _math.radians(rot[2])
            slot.eye_L_sca_x, slot.eye_L_sca_y, slot.eye_L_sca_z = sca[0], sca[1], sca[2]

        # Transforms ojo derecho
        tfR = data.get("transforms", {}).get("ojo_derecho_chicken_1", {})
        if tfR:
            _base_R = EYE_BASE_TRANSFORMS["ojo_derecho_chicken_1"]
            loc = tfR.get("location", list(_base_R["loc"]))
            rot = tfR.get("rotation_euler", list(_base_R["rot"]))
            sca = tfR.get("scale", list(_base_R["sca"]))
            slot.eye_R_loc_x, slot.eye_R_loc_y, slot.eye_R_loc_z = loc[0], loc[1], loc[2]
            slot.eye_R_rot_x = _math.radians(rot[0])
            slot.eye_R_rot_y = _math.radians(rot[1])
            slot.eye_R_rot_z = _math.radians(rot[2])
            slot.eye_R_sca_x, slot.eye_R_sca_y, slot.eye_R_sca_z = sca[0], sca[1], sca[2]

        name = slot.slot_label
        self.report({"INFO"}, f"Importado '{name}' como nuevo estado de ojos")
        return {"FINISHED"}


class CH1ST_OT_CaptureEyeToSlot(Operator):
    """
    Captura los valores actuales del panel global de ojos (eye_expr y st.eye_*)
    y los vuelca en el estado de ojos seleccionado de la lista.
    """
    bl_idname   = "ch1st.capture_eye_to_slot"
    bl_label    = "Capturar estado actual al slot"
    bl_description = (
        "Copia los parametros del panel de ojos (Transforms, Expresion, Geometria) "
        "al slot de ojos actualmente seleccionado"
    )
    bl_options  = {"REGISTER", "UNDO"}

    target: EnumProperty(
        name="Destino",
        items=[
            ("SLOT",  "Slot seleccionado", "Vuelca al slot intermedio activo"),
            ("START", "Estado INICIO",     "Vuelca al estado inicial de ojos"),
            ("END",   "Estado FIN",        "Vuelca al estado final de ojos"),
        ],
        default="SLOT",
    )

    def execute(self, context):
        st    = context.scene.ch1st
        eye_s = st.eye_expr

        def _write_to(item, prefix=""):
            """Escribe valores de eye_expr y transforms al item (slot/start/end)"""
            if prefix:
                # start / end: atributos directos en st con prefijo
                setattr(st, f"eye_{prefix}_expression",  eye_s.active_expression)
                setattr(st, f"eye_{prefix}_expr_value",  eye_s.expression_value)
                setattr(st, f"eye_{prefix}_geo_mode",    eye_s.geo_edit_mode)
                setattr(st, f"eye_{prefix}_geo_intensity", eye_s.geo_intensity)
                for side in ("L", "R"):
                    for axis in ("x", "y", "z"):
                        for trf in ("loc", "rot", "sca"):
                            src_attr = f"eye_{side}_{trf}_{axis}"
                            dst_attr = f"eye_{prefix}_{side}_{trf}_{axis}"
                            setattr(st, dst_attr, getattr(eye_s, src_attr))
            else:
                # slot intermedio
                item.active_expression = eye_s.active_expression
                item.expression_value  = eye_s.expression_value
                item.geo_edit_mode     = eye_s.geo_edit_mode
                item.geo_intensity     = eye_s.geo_intensity
                for side in ("L", "R"):
                    for axis in ("x", "y", "z"):
                        for trf in ("loc", "rot", "sca"):
                            src_attr = f"eye_{side}_{trf}_{axis}"
                            setattr(item, src_attr, getattr(eye_s, src_attr))

        if self.target == "SLOT":
            if not st.eye_slots or not (0 <= st.eye_slot_idx < len(st.eye_slots)):
                self.report({"WARNING"}, "No hay slot seleccionado")
                return {"CANCELLED"}
            _write_to(st.eye_slots[st.eye_slot_idx])
            self.report({"INFO"}, "Estado de ojos volcado al slot seleccionado")
        elif self.target == "START":
            _write_to(None, "start")
            self.report({"INFO"}, "Estado de ojos volcado a INICIO")
        elif self.target == "END":
            _write_to(None, "end")
            self.report({"INFO"}, "Estado de ojos volcado a FIN")

        return {"FINISHED"}


# =============================================================================
# PREVIEW DE UN ESTADO PUNTUAL DE OJOS EN EL VIEWPORT
# =============================================================================

class CH1ST_OT_PreviewEyeState(Operator):
    """
    Aplica en el viewport (sin keyframes) el estado de ojos indicado:
    START, END o el SLOT seleccionado.
    Util para verificar visualmente cada configuracion antes de concatenar.
    """
    bl_idname   = "ch1st.preview_eye_state"
    bl_label    = "Preview estado de ojos"
    bl_description = (
        "Mueve y escala los ojos en el viewport para previsualizar "
        "el estado seleccionado (sin insertar keyframes)"
    )
    bl_options  = {"REGISTER", "UNDO"}

    target: EnumProperty(
        name="Estado a previsualizar",
        items=[
            ("START", "Inicio", "Aplica el estado inicial de ojos"),
            ("SLOT",  "Slot",   "Aplica el slot intermedio seleccionado"),
            ("END",   "Fin",    "Aplica el estado final de ojos"),
        ],
        default="START",
    )

    # ── Helpers ──────────────────────────────────────────────────────────────
    @staticmethod
    def _get_params(context, target):
        """Devuelve un dict con loc/rot/sca para L y R segun el target."""
        st = context.scene.ch1st

        if target == "SLOT":
            if not st.eye_slots or not (0 <= st.eye_slot_idx < len(st.eye_slots)):
                return None
            s = st.eye_slots[st.eye_slot_idx]
            return {
                "L": {"loc": (s.eye_L_loc_x, s.eye_L_loc_y, s.eye_L_loc_z),
                       "rot": (s.eye_L_rot_x, s.eye_L_rot_y, s.eye_L_rot_z),
                       "sca": (s.eye_L_sca_x, s.eye_L_sca_y, s.eye_L_sca_z)},
                "R": {"loc": (s.eye_R_loc_x, s.eye_R_loc_y, s.eye_R_loc_z),
                       "rot": (s.eye_R_rot_x, s.eye_R_rot_y, s.eye_R_rot_z),
                       "sca": (s.eye_R_sca_x, s.eye_R_sca_y, s.eye_R_sca_z)},
                "expression": s.active_expression,
                "expr_value":  s.expression_value,
                "geo_mode":    s.geo_edit_mode,
                "geo_intensity": s.geo_intensity,
            }

        p = "start" if target == "START" else "end"
        return {
            "L": {"loc": (getattr(st, f"eye_{p}_L_loc_x"),
                           getattr(st, f"eye_{p}_L_loc_y"),
                           getattr(st, f"eye_{p}_L_loc_z")),
                   "rot": (getattr(st, f"eye_{p}_L_rot_x"),
                           getattr(st, f"eye_{p}_L_rot_y"),
                           getattr(st, f"eye_{p}_L_rot_z")),
                   "sca": (getattr(st, f"eye_{p}_L_sca_x"),
                           getattr(st, f"eye_{p}_L_sca_y"),
                           getattr(st, f"eye_{p}_L_sca_z"))},
            "R": {"loc": (getattr(st, f"eye_{p}_R_loc_x"),
                           getattr(st, f"eye_{p}_R_loc_y"),
                           getattr(st, f"eye_{p}_R_loc_z")),
                   "rot": (getattr(st, f"eye_{p}_R_rot_x"),
                           getattr(st, f"eye_{p}_R_rot_y"),
                           getattr(st, f"eye_{p}_R_rot_z")),
                   "sca": (getattr(st, f"eye_{p}_R_sca_x"),
                           getattr(st, f"eye_{p}_R_sca_y"),
                           getattr(st, f"eye_{p}_R_sca_z"))},
            "expression":  getattr(st, f"eye_{p}_expression"),
            "expr_value":  getattr(st, f"eye_{p}_expr_value"),
            "geo_mode":    getattr(st, f"eye_{p}_geo_mode"),
            "geo_intensity": getattr(st, f"eye_{p}_geo_intensity"),
        }

    @staticmethod
    def _apply_transforms(params):
        """Aplica Location / Rotation / Scale a las mallas de ojos en el viewport."""
        import mathutils
        EYE_NAMES = {
            "L": "ojo_izquierdo_chicken_1",
            "R": "ojo_derecho_chicken_1",
        }
        for side, name in EYE_NAMES.items():
            obj = bpy.data.objects.get(name)
            if obj is None:
                continue
            p   = params[side]
            obj.location = p["loc"]
            obj.rotation_euler = mathutils.Euler(p["rot"], "XYZ")
            obj.scale = p["sca"]

    def execute(self, context):
        params = self._get_params(context, self.target)
        if params is None:
            self.report({"WARNING"}, "No hay slot de ojos seleccionado")
            return {"CANCELLED"}

        self._apply_transforms(params)

        # Aplicar expresion de shape key si el sistema esta activo
        from .eye_system import apply_expression_to_eye
        eye_names = ["ojo_izquierdo_chicken_1", "ojo_derecho_chicken_1"]
        expr  = params.get("expression", "NEUTRAL")
        val   = params.get("expr_value",  1.0)
        frame = context.scene.frame_current
        for name in eye_names:
            obj = bpy.data.objects.get(name)
            if obj:
                try:
                    apply_expression_to_eye(obj, expr, val, frame)
                except Exception:
                    pass  # Si no hay shape keys aun, silencioso

        label_map = {"START": "INICIO", "SLOT": "SLOT activo", "END": "FIN"}
        self.report({"INFO"}, f"Preview de ojos: {label_map.get(self.target, self.target)} aplicado")
        return {"FINISHED"}


# =============================================================================
# REPRODUCIR SECUENCIA COMPLETA DE OJOS  (inserta keyframes de prueba)
# =============================================================================

class CH1ST_OT_Concatenate2(Operator):
    """
    Genera la secuencia de ojos (INICIO → cambios intermedios → FIN)
    e inserta keyframes definitivos en la timeline a partir del frame
    de inicio de ojos configurado en el panel.
    """
    bl_idname   = "ch1st.concatenate_2"
    bl_label    = "CONCATENAR_2  (Ojos)"
    bl_description = (
        "Genera la secuencia de ojos (Inicio → N cambios → Fin) "
        "e inserta keyframes en la timeline a partir del frame de inicio de ojos"
    )
    bl_options  = {"REGISTER", "UNDO"}

    def _build_states(self, context):
        """
        Devuelve lista ordenada de estados: [start, *slots, end].
        Inicio y Fin usan coordenadas base fijas de Alfred (sin transforms).
        Solo los slots intermedios llevan transforms/expresion/geometria.
        """
        st = context.scene.ch1st

        # Coordenadas base fijas — posicion correcta en el rostro de Alfred
        _BASE_L = {
            "loc": EYE_BASE_TRANSFORMS["ojo_izquierdo_chicken_1"]["loc"],
            "rot": EYE_BASE_TRANSFORMS["ojo_izquierdo_chicken_1"]["rot"],
            "sca": EYE_BASE_TRANSFORMS["ojo_izquierdo_chicken_1"]["sca"],
        }
        _BASE_R = {
            "loc": EYE_BASE_TRANSFORMS["ojo_derecho_chicken_1"]["loc"],
            "rot": EYE_BASE_TRANSFORMS["ojo_derecho_chicken_1"]["rot"],
            "sca": EYE_BASE_TRANSFORMS["ojo_derecho_chicken_1"]["sca"],
        }

        state_start = {
            "label":      "Inicio",
            "duration":   st.eye_start_duration,
            "interp":     st.eye_start_interp,
            "L":          _BASE_L,
            "R":          _BASE_R,
            "expression": "NEUTRAL",
            "expr_value": 0.0,
        }
        state_end = {
            "label":      "Fin",
            "duration":   st.eye_end_duration,
            "interp":     st.eye_end_interp,
            "L":          _BASE_L,
            "R":          _BASE_R,
            "expression": "NEUTRAL",
            "expr_value": 0.0,
        }

        states = [state_start]
        for slot in st.eye_slots:
            states.append({
                "label":      slot.slot_label,
                "duration":   slot.duration,
                "interp":     slot.interp_type,
                "L": {"loc": (slot.eye_L_loc_x, slot.eye_L_loc_y, slot.eye_L_loc_z),
                      "rot": (slot.eye_L_rot_x, slot.eye_L_rot_y, slot.eye_L_rot_z),
                      "sca": (slot.eye_L_sca_x, slot.eye_L_sca_y, slot.eye_L_sca_z)},
                "R": {"loc": (slot.eye_R_loc_x, slot.eye_R_loc_y, slot.eye_R_loc_z),
                      "rot": (slot.eye_R_rot_x, slot.eye_R_rot_y, slot.eye_R_rot_z),
                      "sca": (slot.eye_R_sca_x, slot.eye_R_sca_y, slot.eye_R_sca_z)},
                "expression": slot.active_expression,
                "expr_value": slot.expression_value,
            })
        states.append(state_end)
        return states

    @staticmethod
    def _insert_eye_keyframes(obj, frame):
        """Inserta keyframes de Location, Rotation y Scale en el frame dado."""
        if obj is None:
            return
        obj.keyframe_insert(data_path="location",       frame=frame)
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
        obj.keyframe_insert(data_path="scale",          frame=frame)

    @staticmethod
    def _set_interp(obj, frame, interp):
        """Ajusta el tipo de interpolacion del keyframe recien insertado."""
        INTERP_MAP = {
            "SMOOTH":   "BEZIER",
            "LINEAR":   "LINEAR",
            "CONSTANT": "CONSTANT",
            "EASE_IN":  "BEZIER",
            "EASE_OUT": "BEZIER",
        }
        bpy_interp = INTERP_MAP.get(interp, "BEZIER")
        if obj and obj.animation_data and obj.animation_data.action:
            for fc in get_fcurves(obj.animation_data.action):
                for kp in fc.keyframe_points:
                    if abs(kp.co.x - frame) < 0.5:
                        kp.interpolation = bpy_interp

    def execute(self, context):
        from .interpolation import apply_interp
        from .pose_utils    import _lerp
        from .eye_system    import apply_expression_to_eye, apply_blink_sequence

        scene       = context.scene
        st          = context.scene.ch1st
        eye_s       = st.eye_expr                      # ← variable que faltaba
        states      = self._build_states(context)
        start_frame = st.eye_global_start_frame

        EYE_NAMES = {"L": "ojo_izquierdo_chicken_1", "R": "ojo_derecho_chicken_1"}

        # ── Verificar objetos ─────────────────────────────────────────────────
        missing = [n for n in EYE_NAMES.values() if scene.objects.get(n) is None]
        if missing:
            self.report({"ERROR"}, f"No se encontraron: {', '.join(missing)}")
            return {"CANCELLED"}
        if len(states) < 2:
            self.report({"ERROR"}, "Se necesita al menos estado inicio y fin")
            return {"CANCELLED"}

        # ── Determinar si hay secuencia de expresiones que generar ────────────
        # Solo se necesitan shape keys si hay slots intermedios con expresiones
        # distintas de NEUTRAL, o si inicio/fin difieren.
        has_expressions = any(
            s.get("expression", "NEUTRAL") != "NEUTRAL" or s.get("expr_value", 0.0) > 0.0
            for s in states
        )

        # ── Verificar shape keys solo si se va a animar expresiones ──────────
        if has_expressions:
            for obj_name in EYE_NAMES.values():
                obj = scene.objects.get(obj_name)
                if not obj or not obj.data.shape_keys:
                    self.report({"WARNING"},
                        f"'{obj_name}' no tiene shape keys — "
                        f"presiona 'Crear / Recrear Shape Keys' primero")
                    return {"CANCELLED"}

        # ── Calcular duración total y end_frame ───────────────────────────────
        total_dur = sum(s.get("duration", 20) for s in states)
        end_frame = start_frame + total_dur - 1

        # ── Limpiar actions previas de objeto (loc/rot/sca) Y shape keys ──────
        # Sin limpiar ambas, keyframes viejos en frame 1 causan interpolacion
        # extraña desde frame 1 hasta eye_global_start_frame.
        for obj_name in EYE_NAMES.values():
            obj = scene.objects.get(obj_name)
            if not obj:
                continue
            # Limpiar action del objeto (transforms: loc/rot/sca)
            if obj.animation_data and obj.animation_data.action:
                _old_obj = obj.animation_data.action
                obj.animation_data.action = None
                bpy.data.actions.remove(_old_obj)
            # Limpiar action de shape keys
            if (obj.data and hasattr(obj.data, 'shape_keys')
                    and obj.data.shape_keys
                    and obj.data.shape_keys.animation_data
                    and obj.data.shape_keys.animation_data.action):
                _old_sk = obj.data.shape_keys.animation_data.action
                obj.data.shape_keys.animation_data.action = None
                bpy.data.actions.remove(_old_sk)

        # ── Construir waypoints de transforms ────────────────────────────────
        # Un waypoint en el CENTRO de cada segmento (mismo esquema que CONCATENAR)
        tf_waypoints = []   # (frame_abs, {L:{loc,rot,sca}, R:{loc,rot,sca}}, interp)

        def _st(s):
            return {"L": s["L"], "R": s["R"]}

        # Waypoint 0: frame de inicio con el estado inicial
        tf_waypoints.append((start_frame, _st(states[0]), states[0].get("interp", "SMOOTH")))

        cursor = start_frame
        for state in states:
            dur = state.get("duration", 20)
            mid = cursor + dur // 2
            tf_waypoints.append((mid, _st(state), state.get("interp", "SMOOTH")))
            cursor += dur

        # Waypoint final: último frame con el estado final
        tf_waypoints.append((end_frame, _st(states[-1]), states[-1].get("interp", "SMOOTH")))

        def _transforms_at(abs_f):
            """Interpola loc/rot/sca de ambos ojos en abs_f."""
            for i in range(len(tf_waypoints) - 1):
                f0, tr0, itp = tf_waypoints[i]
                f1, tr1, _   = tf_waypoints[i + 1]
                if abs_f <= f1 or i == len(tf_waypoints) - 2:
                    span = f1 - f0
                    if span <= 0:
                        return tr1
                    t = apply_interp(max(0.0, min(1.0, (abs_f - f0) / span)), itp)
                    result = {}
                    for side in ("L", "R"):
                        result[side] = {
                            "loc": tuple(_lerp(tr0[side]["loc"], tr1[side]["loc"], t)),
                            "rot": tuple(_lerp(tr0[side]["rot"], tr1[side]["rot"], t)),
                            "sca": tuple(_lerp(tr0[side]["sca"], tr1[side]["sca"], t)),
                        }
                    return result
            return _st(states[-1])

        # ── Determinar si los transforms cambian realmente ────────────────────
        # Compara cada slot con la base — si todos son iguales a la base,
        # no hace falta animar transforms (evita keyframes innecesarios)
        _BL = EYE_BASE_TRANSFORMS["ojo_izquierdo_chicken_1"]
        _BR = EYE_BASE_TRANSFORMS["ojo_derecho_chicken_1"]
        has_transforms = any(
            s["L"]["loc"] != _BL["loc"] or s["L"]["sca"] != _BL["sca"] or
            s["R"]["loc"] != _BR["loc"] or s["R"]["sca"] != _BR["sca"]
            for s in states[1:-1]   # solo intermedios
        )

        # ── Generar keyframes de shape keys de expresion ──────────────────────
        if has_expressions:
            # Construir waypoints de expresion
            expr_waypoints = []
            cursor = start_frame
            first = states[0]
            expr_waypoints.append((start_frame, first.get("expression", "NEUTRAL"), first.get("expr_value", 0.0)))
            for state in states:
                dur = state.get("duration", 20)
                mid = cursor + dur // 2
                expr_waypoints.append((mid, state.get("expression", "NEUTRAL"), state.get("expr_value", 0.0)))
                cursor += dur
            last = states[-1]
            expr_waypoints.append((end_frame, last.get("expression", "NEUTRAL"), last.get("expr_value", 0.0)))

            def _expr_at(abs_f):
                for i in range(len(expr_waypoints) - 1):
                    f0, e0, v0 = expr_waypoints[i]
                    f1, e1, v1 = expr_waypoints[i + 1]
                    if abs_f <= f1 or i == len(expr_waypoints) - 2:
                        span = f1 - f0
                        if span <= 0:
                            return {e1: v1}
                        t = apply_interp(max(0.0, min(1.0, (abs_f - f0) / span)), "SMOOTH")
                        if e0 == e1:
                            return {e0: v0 + (v1 - v0) * t}
                        return {e0: v0 * (1.0 - t), e1: v1 * t}
                return {last.get("expression", "NEUTRAL"): last.get("expr_value", 0.0)}

        import mathutils

        # ── Escribir un keyframe por frame: transforms + shape keys ───────────
        for abs_f in range(start_frame, end_frame + 1):
            scene.frame_set(abs_f)

            # Transforms (loc/rot/sca) del objeto
            if has_transforms:
                tr = _transforms_at(abs_f)
                for side, obj_name in EYE_NAMES.items():
                    obj = scene.objects.get(obj_name)
                    if obj is None:
                        continue
                    obj.location       = mathutils.Vector(tr[side]["loc"])
                    obj.rotation_euler = mathutils.Euler(tr[side]["rot"], "XYZ")
                    obj.scale          = mathutils.Vector(tr[side]["sca"])
                    obj.keyframe_insert(data_path="location",       frame=abs_f)
                    obj.keyframe_insert(data_path="rotation_euler", frame=abs_f)
                    obj.keyframe_insert(data_path="scale",          frame=abs_f)

            # Shape keys de expresion
            if has_expressions:
                expr_vals = _expr_at(abs_f)
                for obj_name in EYE_NAMES.values():
                    obj = scene.objects.get(obj_name)
                    if not obj or not obj.data.shape_keys:
                        continue
                    for sk in obj.data.shape_keys.key_blocks:
                        if sk.name == "Basis":
                            continue
                        sk_val = 0.0
                        for expr_name, val in expr_vals.items():
                            if sk.name.lower() == expr_name.lower():
                                sk_val = val
                                break
                        sk.value = sk_val
                        sk.keyframe_insert(data_path="value", frame=abs_f)

        # ── Ajustar interpolacion de fcurves a BEZIER ─────────────────────────
        for obj_name in EYE_NAMES.values():
            obj = scene.objects.get(obj_name)
            if not obj:
                continue
            # Objeto (transforms)
            if obj.animation_data and obj.animation_data.action:
                for fc in get_fcurves(obj.animation_data.action):
                    for kp in fc.keyframe_points:
                        kp.interpolation = "BEZIER"
                        kp.easing        = "AUTO"
            # Shape keys
            if obj.data.shape_keys and obj.data.shape_keys.animation_data:
                action = obj.data.shape_keys.animation_data.action
                if action:
                    for fc in get_fcurves(action):
                        for kp in fc.keyframe_points:
                            kp.interpolation = "BEZIER"
                            kp.easing        = "AUTO"

        # ── Ajustar rango de timeline ─────────────────────────────────────────
        if end_frame > scene.frame_end:
            scene.frame_end = end_frame
        scene.frame_set(start_frame)

        # ── Parpadeo en INICIO si modo = BLINK ───────────────────────────────
        blink_start_msg = ""
        if st.eye_start_blink_mode == "BLINK":
            b_s = start_frame
            b_e = start_frame + st.eye_start_duration - 1
            if b_e > b_s:
                apply_blink_sequence(b_s, b_e,
                                     st.eye_start_blink_count,
                                     st.eye_start_blink_duration)
                blink_start_msg = f"  INICIO: {st.eye_start_blink_count} parpadeos ({b_s}→{b_e})"

        # ── Parpadeo en FIN si modo = BLINK ──────────────────────────────────
        blink_end_msg = ""
        if st.eye_end_blink_mode == "BLINK":
            b_s = end_frame - st.eye_end_duration + 1
            b_e = end_frame
            if b_e > b_s:
                apply_blink_sequence(b_s, b_e,
                                     st.eye_end_blink_count,
                                     st.eye_end_blink_duration)
                blink_end_msg = f"  FIN: {st.eye_end_blink_count} parpadeos ({b_s}→{b_e})"

        # ── Parpadeo automatico — multi-intervalo (sección E del panel) ─────────
        blink_ind_msg = ""
        if eye_s.blink_enabled:
            active_blink_intervals = [bi for bi in st.blink_intervals if bi.enabled]
            if not active_blink_intervals:
                self.report({"WARNING"}, "Parpadeo activado pero sin intervalos — agrega al menos uno")
            for bi in active_blink_intervals:
                b_start = bi.frame_start
                b_end   = bi.frame_end
                if b_end > b_start:
                    apply_blink_sequence(b_start, b_end, bi.blink_count, bi.blink_duration)
                    if b_end > scene.frame_end:
                        scene.frame_end = b_end
                    blink_ind_msg += f"  +parpadeo({b_start}→{b_end}x{bi.blink_count})"
                else:
                    self.report({"WARNING"}, f"Intervalo parpadeo '{bi.label}': frame fin debe ser mayor que inicio")

        # ── Expresiones de ojos — multi-intervalo (sección E2 del panel) ──────
        if eye_s.expr_intervals_enabled:
            active_expr_intervals = [ei for ei in st.expr_intervals if ei.enabled]
            if not active_expr_intervals:
                self.report({"WARNING"}, "Expresiones activadas pero sin intervalos — agrega al menos uno")
            for ei in active_expr_intervals:
                from .eye_system import apply_expression_to_eye as _apply_expr
                left_eye  = __import__("bpy").data.objects.get("ojo_izquierdo_chicken_1")
                right_eye = __import__("bpy").data.objects.get("ojo_derecho_chicken_1")
                if not left_eye or not right_eye:
                    self.report({"WARNING"}, "Ojos no encontrados para expresion por intervalos")
                    continue
                if not left_eye.data.shape_keys or not right_eye.data.shape_keys:
                    self.report({"WARNING"}, f"Crea los shape keys primero (expresion '{ei.label}')")
                    continue
                expr_name = ei.expression.lower()
                val       = ei.expression_value
                f_start   = ei.frame_start
                f_peak    = ei.frame_peak
                f_end     = ei.frame_end
                # Fase entrada: neutral → expresion
                for eye in (left_eye, right_eye):
                    _apply_expr(eye, expr_name, 0.0, f_start)
                    _apply_expr(eye, expr_name, val,  f_peak)
                    _apply_expr(eye, expr_name, 0.0, f_end)
                if f_end > scene.frame_end:
                    scene.frame_end = f_end
                blink_ind_msg += f"  +expr({ei.expression},{f_start}|{f_peak}|{f_end})"

        total_frames = end_frame - start_frame + 1
        expr_msg = f"{len(states)} estados, {total_frames}f" if has_expressions else "solo parpadeo"
        self.report({"INFO"},
            f"CONCATENAR_2: {expr_msg} ({start_frame}→{end_frame})"
            f"{blink_start_msg}{blink_end_msg}{blink_ind_msg}")
        return {"FINISHED"}
