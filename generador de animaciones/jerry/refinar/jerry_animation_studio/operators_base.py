
from .blender_compat import get_fcurves as _get_action_fcurves, new_fcurve as _new_fcurve

# -*- coding: utf-8 -*-
"""
operators_base.py — Jerry Animation Studio v1.0
Operadores: Setup, Historia, Reset, PickPose, AddEditRemoveMove de slots.
"""
import bpy, json, os
from bpy.types import Operator
from bpy.props import (
    IntProperty, FloatProperty, StringProperty,
    BoolProperty, EnumProperty, CollectionProperty, PointerProperty,
)
from .constants import (
    BONES_LISTA, BONES_LISTA_FULL, INTERP_TYPE_ITEMS, EYE_BASE_TRANSFORMS,
    ROOT_NAME, ARM_NAME,
)
from .pose_utils import (
    list_json_files, load_json_poses, get_pose_record,
    pose_record_to_full_dict, open_folder,
    _enum_json_files, _json_file_from_index, _enum_poses_from_self_json,
    invalidate_enum_cache, get_root_rotation_from_record,
    get_root_transform_from_record,
    capture_live_bone_pose, capture_live_root_transform, export_pose_changes,
)
from .properties import load_historia_json, get_key_points
from .pose_utils import get_orientacion_inicial

# =============================================================================
# OPERADORES — SETUP
# =============================================================================

class JRRST_OT_SetArmature(Operator):
    bl_idname    = "jerryst.set_armature"
    bl_label     = "Usar seleccionado"
    bl_description = "Asigna el objeto activo como armature principal"

    def execute(self, context):
        obj = context.active_object
        if obj and obj.type == "ARMATURE":
            context.scene.jerryst.armature_name = obj.name
            self.report({"INFO"}, f"Armature set -> {obj.name}")
        else:
            self.report({"WARNING"}, "El objeto activo no es un armature")
        return {"FINISHED"}

class JRRST_OT_OpenPosesFolder(Operator):
    bl_idname = "jerryst.open_poses_folder"
    bl_label  = "Abrir carpeta poses"

    def execute(self, context):
        open_folder(bpy.path.abspath(context.scene.jerryst.poses_dir))
        return {"FINISHED"}

class JRRST_OT_OpenAnimFolder(Operator):
    bl_idname = "jerryst.open_anim_folder"
    bl_label  = "Abrir carpeta animaciones"

    def execute(self, context):
        open_folder(bpy.path.abspath(context.scene.jerryst.anim_dir))
        return {"FINISHED"}


class JRRST_OT_RefreshPoses(Operator):
    bl_idname    = "jerryst.refresh_poses"
    bl_label     = "Actualizar poses"
    bl_description = (
        "Escanea la carpeta de poses y actualiza la lista de archivos JSON disponibles. "
        "Usalo despues de exportar nuevas poses para que aparezcan en los selectores"
    )

    def execute(self, context):
        st     = context.scene.jerryst
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
        # Invalidar cache de EnumProperty para que el nuevo archivo aparezca
        # en el desplegable de "Agregar pose de accion" sin reiniciar Blender
        invalidate_enum_cache()
        self.report(
            {"INFO"},
            f"Poses actualizadas: {len(files)} archivo(s)  —  {total_poses} pose(s) en total"
        )
        return {"FINISHED"}

class JRRST_OT_ReloadHistoria(Operator):
    """Recarga el historia_jerry.json y actualiza info del key_point."""
    bl_idname    = "jerryst.reload_historia"
    bl_label     = "Recargar JSON historia"
    bl_description = "Lee historia_jerry.json y actualiza la lista de key_points disponibles"

    def execute(self, context):
        st = context.scene.jerryst
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

class JRRST_OT_ApplyKeyPointToRoot(Operator):
    """Aplica la coordenada del key_point al Empty 'jerry' que es la raiz del personaje."""
    bl_idname = "jerryst.apply_key_point_to_root"
    bl_label = "Aplicar KeyPoint a Posicion Root"
    bl_description = "Mueve el Empty 'jerry' a la coordenada del KeyPoint de la historia"

    def execute(self, context):
        st = context.scene.jerryst

        # 1. Encontrar el objeto Empty 'jerry' que es la raiz del personaje.
        root_empty = context.scene.objects.get("jerry")
        if not root_empty or root_empty.type != 'EMPTY':
            self.report({"WARNING"}, "No se encuentra el Empty raiz 'jerry'.")
            return {"CANCELLED"}

        # 2. Cargar datos del JSON de historia
        historia = load_historia_json(st.historia_json)
        kps = get_key_points(historia)
        if not kps:
            self.report({"WARNING"}, "No hay key_points cargados desde historia_jerry.json")
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

        # 5. Aplicar al Empty 'jerry' con conversion de coordenadas
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

        # Limpiar fcurves de location del Empty jerry para evitar conflictos
        # con keyframes anteriores que puedan arrastrar al root a (0,0,0).
        if root_empty.animation_data and root_empty.animation_data.action:
            action = root_empty.animation_data.action
            for fc in list(_get_action_fcurves(action)):
                if fc.data_path == "location":
                    _get_action_fcurves(action).remove(fc)

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
        st.pose_start_pos_x = pos_x
        st.pose_start_pos_y = pos_y
        st.pose_start_pos_z = pos_z
        st.pose_end_pos_x   = pos_x
        st.pose_end_pos_y   = pos_y
        st.pose_end_pos_z   = pos_z

        self.report({"INFO"}, (
            f"Posicion de la raiz '{root_empty.name}' fijada en: "
            f"({new_loc[0]:.2f}, {new_loc[1]:.2f}, {new_loc[2]:.2f}) "
            f"durante toda la animacion (frames {frame_start}-{frame_end})."
        ))

        return {"FINISHED"}


# =============================================================================
# RESET
# =============================================================================

class JRRST_OT_Reset(Operator):
    bl_idname    = "jerryst.reset"
    bl_label     = "RESET - Limpiar escena"
    bl_description = "Limpia la secuencia, vuelve al T-pose y borra la animacion generada"
    bl_options   = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        st    = context.scene.jerryst
        scene = context.scene

        # ── Secuencia de poses ──────────────────────────────────────────────
        st.pose_start_file     = ""
        st.pose_start_name     = ""
        st.pose_start_idx      = 0
        st.pose_start_duration = 10
        st.pose_start_interp   = "SMOOTH"
        st.pose_start_rot_x    = 0.0
        st.pose_start_rot_y    = 0.0
        st.pose_start_rot_z    = 0.0
        st.pose_start_pos_x    = 0.0
        st.pose_start_pos_y    = 0.0
        st.pose_start_pos_z    = 0.0
        st.pose_end_file       = ""
        st.pose_end_name       = ""
        st.pose_end_idx        = 0
        st.pose_end_duration   = 10
        st.pose_end_interp     = "SMOOTH"
        st.pose_end_rot_x      = 0.0
        st.pose_end_rot_y      = 0.0
        st.pose_end_rot_z      = 0.0
        st.pose_end_pos_x      = 0.0
        st.pose_end_pos_y      = 0.0
        st.pose_end_pos_z      = 0.0
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

        # ── jerry no tiene sistema de ojos — nada que limpiar ──────────

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

        # ── Objeto root "jerry": limpiar action y posicion ─────────────────
        root_obj = scene.objects.get("jerry")
        if root_obj and root_obj != scene.objects.get(st.armature_name):
            if root_obj.animation_data and root_obj.animation_data.action:
                old_root = root_obj.animation_data.action
                root_obj.animation_data.action = None
                bpy.data.actions.remove(old_root)
            root_obj.location       = (0.0, 0.0, 0.0)
            root_obj.rotation_euler = (0.0, 0.0, 0.0)

        scene.frame_set(st.start_frame)
        self.report({"INFO"}, "Escena limpiada -- personaje en estado inicial")
        return {"FINISHED"}

# =============================================================================
# SELECCION DE POSES  (con duracion en inicio y fin)
# =============================================================================

class JRRST_OT_PickPoseStart(Operator):
    bl_idname    = "jerryst.pick_pose_start"
    bl_label     = "Elegir pose INICIO"
    bl_description = "Selecciona el archivo JSON, la pose de inicio y su duracion en frames"
    bl_options   = {"REGISTER", "UNDO"}

    json_file:  EnumProperty(name="Archivo JSON", items=_enum_json_files)
    pose_index: EnumProperty(name="Pose",         items=_enum_poses_from_self_json)
    duration:   IntProperty(
        name="Duracion pose inicio (frames)",
        description="Cuantos frames se mantiene la pose inicial antes de la transicion",
        default=10, min=1, soft_max=300,
    )
    rot_x: FloatProperty(name="Rot X (grados)", default=0.0,
        description="Rotacion X del root en esta pose (0 = sin rotacion)")
    rot_y: FloatProperty(name="Rot Y (grados)", default=0.0,
        description="Rotacion Y del root en esta pose (0 = sin rotacion)")
    rot_z: FloatProperty(name="Rot Z (grados)", default=0.0,
        description="Rotacion Z del root en esta pose (0 = sin rotacion)")
    pos_x: FloatProperty(name="Pos X", default=0.0,
        description="Posicion X del root (jerry/Empty) en la pose INICIO")
    pos_y: FloatProperty(name="Pos Y", default=0.0,
        description="Posicion Y del root (jerry/Empty) en la pose INICIO")
    pos_z: FloatProperty(name="Pos Z", default=0.0,
        description="Posicion Z del root (jerry/Empty) en la pose INICIO")
    interp_type: EnumProperty(
        name="Interpolacion de salida",
        description="Curva de interpolacion profesional al salir de la pose INICIO hacia la accion",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )

    def invoke(self, context, event):
        st = context.scene.jerryst
        if st.pose_start_file:
            files = list_json_files(st.poses_dir)
            if st.pose_start_file in files:
                self.json_file = str(files.index(st.pose_start_file))
        self.duration    = st.pose_start_duration
        self.rot_x       = st.pose_start_rot_x
        self.rot_y       = st.pose_start_rot_y
        self.rot_z       = st.pose_start_rot_z
        self.pos_x       = st.pose_start_pos_x
        self.pos_y       = st.pose_start_pos_y
        self.pos_z       = st.pose_start_pos_z
        self.interp_type = st.pose_start_interp
        # [FIX] Auto-rellenar posicion Y rotacion del root desde el JSON de la
        # pose. Antes solo se traia la rotacion (get_root_rotation_from_record)
        # y la posicion se quedaba con el valor previo/0.0, causando que el
        # personaje saltara a (0,0,0) al generar la animacion.
        jf = _json_file_from_index(self, context)
        if jf:
            fp  = os.path.join(bpy.path.abspath(st.poses_dir), jf)
            rec = get_pose_record(st.poses_dir, jf, int(self.pose_index))
            if rec:
                _root = get_root_transform_from_record(rec)
                self.pos_x, self.pos_y, self.pos_z = _root["pos"]
                self.rot_x, self.rot_y, self.rot_z = _root["rot_deg"]
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        layout = self.layout
        _pc = getattr(context.scene, "jerry_path", None)
        _modo_recorrido = _pc is not None and len(_pc.path_points) > 1

        layout.label(text="Paso 1 -- Elige el archivo JSON:")
        layout.prop(self, "json_file", text="")
        layout.separator()
        layout.label(text="Paso 2 -- Elige la pose:")
        layout.prop(self, "pose_index", text="")
        layout.separator()
        layout.label(text="Paso 3 -- Duracion de la pose inicio:")
        layout.prop(self, "duration", text="Frames")
        layout.separator()
        box = layout.box()
        box.label(text="Paso 4 -- Interpolacion de salida:", icon="IPO_BEZIER")
        box.prop(self, "interp_type", text="")
        layout.separator()
        if _modo_recorrido:
            box_lock = layout.box()
            box_lock.label(text="Posicion y Rotacion del Root: BLOQUEADAS", icon="LOCKED")
            box_lock.label(text="  El recorrido (Paso 2) controla XYZ y orientacion del root", icon="INFO")
        else:
            box2 = layout.box()
            box2.label(text="Paso 5 -- Posicion del Root (jerry/Empty):", icon="OBJECT_ORIGIN")
            row = box2.row(align=True)
            row.prop(self, "pos_x", text="X")
            row.prop(self, "pos_y", text="Y")
            row.prop(self, "pos_z", text="Z")
            layout.separator()
            box3 = layout.box()
            box3.label(text="Paso 6 -- Orientacion del Root (rotacion) [auto desde JSON]:", icon="ORIENTATION_LOCAL")
            box3.label(text="  (ajusta si la pose requiere orientacion diferente)", icon="INFO")
            col = box3.column(align=True)
            col.prop(self, "rot_x", text="Rot X")
            col.prop(self, "rot_y", text="Rot Y")
            col.prop(self, "rot_z", text="Rot Z")

    def execute(self, context):
        if self.json_file == "NONE":
            self.report({"WARNING"}, "No hay archivos JSON en la carpeta de poses")
            return {"CANCELLED"}
        st       = context.scene.jerryst
        jf       = _json_file_from_index(self, context)
        idx      = int(self.pose_index)
        fp       = os.path.join(bpy.path.abspath(st.poses_dir), jf)
        poses    = load_json_poses(fp)
        st.pose_start_file     = jf
        st.pose_start_idx      = idx
        st.pose_start_name     = poses[idx].get("label", "?") if poses and idx < len(poses) else "?"
        st.pose_start_duration = self.duration
        st.pose_start_rot_x    = self.rot_x
        st.pose_start_rot_y    = self.rot_y
        st.pose_start_rot_z    = self.rot_z
        st.pose_start_pos_x    = self.pos_x
        st.pose_start_pos_y    = self.pos_y
        st.pose_start_pos_z    = self.pos_z
        st.pose_start_interp   = self.interp_type
        self.report({"INFO"}, f"Pose inicio -> '{st.pose_start_name}'  [{jf}]  rot_y={self.rot_y:.3f}°  interp={self.interp_type}")
        return {"FINISHED"}

class JRRST_OT_PickPoseEnd(Operator):
    bl_idname    = "jerryst.pick_pose_end"
    bl_label     = "Elegir pose FIN"
    bl_description = "Selecciona el archivo JSON, la pose de fin y su duracion en frames"
    bl_options   = {"REGISTER", "UNDO"}

    json_file:  EnumProperty(name="Archivo JSON", items=_enum_json_files)
    pose_index: EnumProperty(name="Pose",         items=_enum_poses_from_self_json)
    duration:   IntProperty(
        name="Duracion pose fin (frames)",
        description="Cuantos frames se mantiene la pose final al terminar la transicion",
        default=10, min=1, soft_max=300,
    )
    rot_x: FloatProperty(name="Rot X (grados)", default=0.0,
        description="Rotacion X del root en esta pose (0 = sin rotacion)")
    rot_y: FloatProperty(name="Rot Y (grados)", default=0.0,
        description="Rotacion Y del root en esta pose (0 = sin rotacion)")
    rot_z: FloatProperty(name="Rot Z (grados)", default=0.0,
        description="Rotacion Z del root en esta pose (0 = sin rotacion)")
    pos_x: FloatProperty(name="Pos X", default=0.0,
        description="Posicion X del root (jerry/Empty) en la pose FIN")
    pos_y: FloatProperty(name="Pos Y", default=0.0,
        description="Posicion Y del root (jerry/Empty) en la pose FIN")
    pos_z: FloatProperty(name="Pos Z", default=0.0,
        description="Posicion Z del root (jerry/Empty) en la pose FIN")
    interp_type: EnumProperty(
        name="Interpolacion de entrada",
        description="Curva de interpolacion profesional al llegar a la pose FIN desde la ultima accion",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )

    def invoke(self, context, event):
        st = context.scene.jerryst
        if st.pose_end_file:
            files = list_json_files(st.poses_dir)
            if st.pose_end_file in files:
                self.json_file = str(files.index(st.pose_end_file))
        self.duration    = st.pose_end_duration
        self.rot_x       = st.pose_end_rot_x
        self.rot_y       = st.pose_end_rot_y
        self.rot_z       = st.pose_end_rot_z
        self.pos_x       = st.pose_end_pos_x
        self.pos_y       = st.pose_end_pos_y
        self.pos_z       = st.pose_end_pos_z
        self.interp_type = st.pose_end_interp
        # [FIX] Auto-rellenar posicion Y rotacion del root desde el JSON de la
        # pose. Antes solo se traia la rotacion (get_root_rotation_from_record)
        # y la posicion se quedaba con el valor previo/0.0, causando que el
        # personaje saltara a (0,0,0) al generar la animacion.
        jf = _json_file_from_index(self, context)
        if jf:
            rec = get_pose_record(st.poses_dir, jf, int(self.pose_index))
            if rec:
                _root = get_root_transform_from_record(rec)
                self.pos_x, self.pos_y, self.pos_z = _root["pos"]
                self.rot_x, self.rot_y, self.rot_z = _root["rot_deg"]
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        layout = self.layout
        _pc = getattr(context.scene, "jerry_path", None)
        _modo_recorrido = _pc is not None and len(_pc.path_points) > 1

        layout.label(text="Paso 1 -- Elige el archivo JSON:")
        layout.prop(self, "json_file", text="")
        layout.separator()
        layout.label(text="Paso 2 -- Elige la pose:")
        layout.prop(self, "pose_index", text="")
        layout.separator()
        layout.label(text="Paso 3 -- Duracion de la pose fin:")
        layout.prop(self, "duration", text="Frames")
        layout.separator()
        box = layout.box()
        box.label(text="Paso 4 -- Interpolacion de entrada:", icon="IPO_BEZIER")
        box.prop(self, "interp_type", text="")
        layout.separator()
        if _modo_recorrido:
            box_lock = layout.box()
            box_lock.label(text="Posicion y Rotacion del Root: BLOQUEADAS", icon="LOCKED")
            box_lock.label(text="  El recorrido (Paso 2) controla XYZ y orientacion del root", icon="INFO")
        else:
            box2 = layout.box()
            box2.label(text="Paso 5 -- Posicion del Root (jerry/Empty):", icon="OBJECT_ORIGIN")
            row = box2.row(align=True)
            row.prop(self, "pos_x", text="X")
            row.prop(self, "pos_y", text="Y")
            row.prop(self, "pos_z", text="Z")
            layout.separator()
            box3 = layout.box()
            box3.label(text="Paso 6 -- Orientacion del Root (rotacion) [auto desde JSON]:", icon="ORIENTATION_LOCAL")
            box3.label(text="  (ajusta si la pose requiere orientacion diferente)", icon="INFO")
            col = box3.column(align=True)
            col.prop(self, "rot_x", text="Rot X")
            col.prop(self, "rot_y", text="Rot Y")
            col.prop(self, "rot_z", text="Rot Z")

    def execute(self, context):
        if self.json_file == "NONE":
            self.report({"WARNING"}, "No hay archivos JSON en la carpeta de poses")
            return {"CANCELLED"}
        st    = context.scene.jerryst
        jf    = _json_file_from_index(self, context)
        idx   = int(self.pose_index)
        fp    = os.path.join(bpy.path.abspath(st.poses_dir), jf)
        poses = load_json_poses(fp)
        st.pose_end_file     = jf
        st.pose_end_idx      = idx
        st.pose_end_name     = poses[idx].get("label", "?") if poses and idx < len(poses) else "?"
        st.pose_end_duration = self.duration
        st.pose_end_rot_x    = self.rot_x
        st.pose_end_rot_y    = self.rot_y
        st.pose_end_rot_z    = self.rot_z
        st.pose_end_pos_x    = self.pos_x
        st.pose_end_pos_y    = self.pos_y
        st.pose_end_pos_z    = self.pos_z
        st.pose_end_interp   = self.interp_type
        self.report({"INFO"}, f"Pose fin -> '{st.pose_end_name}'  [{jf}]  rot_y={self.rot_y:.3f}°  interp={self.interp_type}")
        return {"FINISHED"}

# =============================================================================
# POSES DE ACCION (sin cambios respecto a v1.2)
# =============================================================================

class JRRST_OT_AddActionPose(Operator):
    bl_idname    = "jerryst.add_action_pose"
    bl_label     = "Agregar pose de accion"
    bl_description = "Agrega una pose intermedia a la secuencia"
    bl_options   = {"REGISTER", "UNDO"}

    json_file:  EnumProperty(name="Archivo JSON", items=_enum_json_files)
    pose_index: EnumProperty(name="Pose",         items=_enum_poses_from_self_json)
    duration:   IntProperty(name="Duracion (frames)", default=20, min=2, soft_max=300)
    rot_x: FloatProperty(name="Rot X (grados)", default=0.0,
        description="Rotacion X del root en esta pose (0 = sin rotacion)")
    rot_y: FloatProperty(name="Rot Y (grados)", default=0.0,
        description="Rotacion Y del root en esta pose (0 = sin rotacion)")
    rot_z: FloatProperty(name="Rot Z (grados)", default=0.0,
        description="Rotacion Z del root en esta pose (0 = sin rotacion)")
    pos_x: FloatProperty(name="Pos X", default=0.0,
        description="Posicion X del root (jerry/Empty) en esta pose de accion")
    pos_y: FloatProperty(name="Pos Y", default=0.0,
        description="Posicion Y del root (jerry/Empty) en esta pose de accion")
    pos_z: FloatProperty(name="Pos Z", default=0.0,
        description="Posicion Z del root (jerry/Empty) en esta pose de accion")
    interp_type: EnumProperty(
        name="Interpolacion",
        description="Curva de interpolacion profesional para esta pose de accion",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )

    def invoke(self, context, event):
        # [FIX] Pre-rellenar rot desde la última pose de acción si ya hay alguna,
        # para que el diálogo no arranque siempre en 0/0/0.
        st = context.scene.jerryst
        if st.action_poses:
            last = st.action_poses[-1]
            self.rot_x = last.rot_x
            self.rot_y = last.rot_y
            self.rot_z = last.rot_z
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        layout = self.layout
        _pc = getattr(context.scene, "jerry_path", None)
        _modo_recorrido = _pc is not None and len(_pc.path_points) > 1

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
        if _modo_recorrido:
            box_lock = layout.box()
            box_lock.label(text="Posicion y Rotacion del Root: BLOQUEADAS", icon="LOCKED")
            box_lock.label(text="  El recorrido (Paso 2) controla XYZ y orientacion del root", icon="INFO")
        else:
            box2 = layout.box()
            box2.label(text="Paso 5 -- Posicion del Root (jerry/Empty):", icon="OBJECT_ORIGIN")
            row = box2.row(align=True)
            row.prop(self, "pos_x", text="X")
            row.prop(self, "pos_y", text="Y")
            row.prop(self, "pos_z", text="Z")
            layout.separator()
            box3 = layout.box()
            box3.label(text="Paso 6 -- Orientacion del Root (rotacion) [auto desde JSON]:", icon="ORIENTATION_LOCAL")
            box3.label(text="  (ajusta si la pose requiere orientacion diferente)", icon="INFO")
            col = box3.column(align=True)
            col.prop(self, "rot_x", text="Rot X")
            col.prop(self, "rot_y", text="Rot Y")
            col.prop(self, "rot_z", text="Rot Z")

    def execute(self, context):
        if self.json_file == "NONE":
            self.report({"WARNING"}, "No hay archivos JSON en la carpeta de poses")
            return {"CANCELLED"}
        st    = context.scene.jerryst
        jf    = _json_file_from_index(self, context)
        idx   = int(self.pose_index)
        fp    = os.path.join(bpy.path.abspath(st.poses_dir), jf)
        poses = load_json_poses(fp)
        name  = poses[idx].get("label", "?") if poses and idx < len(poses) else "?"

        # [FIX] Auto-rellenar posicion Y rotacion del root desde el JSON de la
        # pose. Antes solo se traia la rotacion (get_root_rotation_from_record)
        # y la posicion se quedaba en 0.0, causando que el personaje saltara
        # a (0,0,0) al generar/concatenar la animacion.
        rec = get_pose_record(st.poses_dir, jf, idx)
        if rec:
            _root = get_root_transform_from_record(rec)
            self.pos_x, self.pos_y, self.pos_z = _root["pos"]
            self.rot_x, self.rot_y, self.rot_z = _root["rot_deg"]

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
        self.report({"INFO"}, f"Pose agregada: '{name}'  [{jf}]  rot_y={self.rot_y:.3f}°  interp={self.interp_type}")
        return {"FINISHED"}


class JRRST_OT_EditActionPose(Operator):
    bl_idname    = "jerryst.edit_action_pose"
    bl_label     = "Editar pose de accion"
    bl_description = "Cambia la duracion, posicion, orientacion e interpolacion de la pose seleccionada"
    bl_options   = {"REGISTER", "UNDO"}

    duration: IntProperty(name="Duracion (frames)", default=20, min=2, soft_max=300)
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
        st = context.scene.jerryst
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
        _pc = getattr(context.scene, "jerry_path", None)
        _modo_recorrido = _pc is not None and len(_pc.path_points) > 1

        layout.prop(self, "duration")
        layout.separator()
        box = layout.box()
        box.label(text="Tipo de interpolacion:", icon="IPO_BEZIER")
        box.prop(self, "interp_type", text="")
        layout.separator()
        if _modo_recorrido:
            box_lock = layout.box()
            box_lock.label(text="Posicion y Rotacion del Root: BLOQUEADAS", icon="LOCKED")
            box_lock.label(text="  El recorrido (Paso 2) controla XYZ y orientacion del root", icon="INFO")
        else:
            box2 = layout.box()
            box2.label(text="Posicion del Root (jerry/Empty):", icon="OBJECT_ORIGIN")
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
        st = context.scene.jerryst
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

class JRRST_OT_RemoveActionPose(Operator):
    bl_idname = "jerryst.remove_action_pose"
    bl_label  = "Eliminar pose"

    def execute(self, context):
        st = context.scene.jerryst
        if st.action_poses and 0 <= st.action_pose_idx < len(st.action_poses):
            st.action_poses.remove(st.action_pose_idx)
            st.action_pose_idx = max(0, st.action_pose_idx - 1)
        return {"FINISHED"}

class JRRST_OT_MoveActionPose(Operator):
    bl_idname = "jerryst.move_action_pose"
    bl_label  = "Mover pose"
    direction: EnumProperty(items=[("UP","Arriba",""),("DOWN","Abajo","")])

    def execute(self, context):
        st  = context.scene.jerryst
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
# SISTEMA DE OJOS POR SEGMENTO ("Secuencia de Ojos" / CONCATENAR_2) ELIMINADO
# (Kebyn, 2026-08-27): panel, propiedades (eye_slots, eye_start_*, eye_end_*,
# eye_global_start_frame, eye_expr de JerryAnimSegmentsSettings) y todos los
# operadores de este bloque (add/remove/duplicate/move/edit/import eye_slot,
# capture/preview eye state, concatenate_2, reset_eye_sequence, reset_blink)
# se retiraron por no usarse. El sistema de expresiones/shape-keys de ojos a
# nivel de personaje (context.scene.jerryst.eye_expr, ver eye_system.py /
# eye_library.py) NO se toco -- es independiente y sigue intacto.
# =============================================================================


class JRRST_OT_JawTalkAddInterval(Operator):
    """Agrega un intervalo de habla a la lista del filtro Hablar."""
    bl_idname  = "jrrst.jaw_talk_add_interval"
    bl_label   = "Agregar intervalo de habla"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        org = context.scene.jerry_segs.organic
        try:
            intervals = json.loads(org.jaw_talk_intervals_json or "[]")
        except Exception:
            intervals = []

        sf     = org.jaw_talk_edit_sf
        ef     = org.jaw_talk_edit_ef
        cycles = org.jaw_talk_edit_cycles

        if sf >= ef:
            self.report({"ERROR"}, "Frame inicio debe ser menor que Frame fin")
            return {"CANCELLED"}

        intervals.append({"sf": sf, "ef": ef, "cycles": cycles})
        intervals.sort(key=lambda x: x["sf"])
        org.jaw_talk_intervals_json = json.dumps(intervals)
        self.report({"INFO"}, f"Intervalo agregado: {sf} → {ef}  ({cycles or 'auto'} ciclos)")
        return {"FINISHED"}


class JRRST_OT_JawTalkRemoveInterval(Operator):
    """Elimina un intervalo de habla de la lista."""
    bl_idname  = "jrrst.jaw_talk_remove_interval"
    bl_label   = "Quitar intervalo de habla"
    bl_options = {"REGISTER", "UNDO"}

    interval_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        org = context.scene.jerry_segs.organic
        try:
            intervals = json.loads(org.jaw_talk_intervals_json or "[]")
        except Exception:
            intervals = []

        idx = self.interval_idx
        if 0 <= idx < len(intervals):
            removed = intervals.pop(idx)
            org.jaw_talk_intervals_json = json.dumps(intervals)
            self.report({"INFO"}, f"Intervalo eliminado: {removed['sf']} → {removed['ef']}")
        else:
            self.report({"WARNING"}, "Indice de intervalo no valido")
        return {"FINISHED"}


# =============================================================================
# EDITOR DE POSE EN VIVO — "Editar pose..." / "Guardar cambios"
# =============================================================================

class JRRST_OT_EnterPoseEditLive(Operator):
    """
    Entra a Pose Mode sobre el armature ('Dog_001_rig') para ajustar los
    huesos con las herramientas nativas de Blender (panel N). El Root
    (Empty 'jerry') se ajusta aparte, seleccionandolo y usando el panel
    nativo Properties > Object > Transform — no hay campos custom para eso.
    """
    bl_idname      = "jerryst.enter_pose_edit_live"
    bl_label       = "Editar pose"
    bl_description = ("Entra a Pose Mode para ajustar los huesos (panel N). "
                      "Para el Root, selecciona el Empty 'jerry' y ajustalo "
                      "en Properties > Object > Transform")
    bl_options      = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        arm = scene.objects.get(ARM_NAME)
        if arm is None:
            self.report({"ERROR"}, f"No se encontro el armature '{ARM_NAME}' en la escena")
            return {"CANCELLED"}

        if context.object and context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        for ob in context.selected_objects:
            ob.select_set(False)
        arm.select_set(True)
        context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode='POSE')

        self.report({"INFO"},
                    "Pose Mode activo. Ajusta los huesos y, para el Root, "
                    f"selecciona el Empty '{ROOT_NAME}' (Properties > Object "
                    "> Transform). Cuando termines, pulsa Guardar cambios.")
        return {"FINISHED"}


class JRRST_OT_SavePoseChangesLive(Operator):
    """
    Lee la pose ACTUAL de la escena (huesos en Pose Mode + transform en vivo
    del Root/Empty 'jerry') y la exporta a un .json en la carpeta de cambios
    (scene.jerryst.pose_changes_dir). No modifica el JSON original de la
    libreria de poses. Tambien actualiza el snapshot de solo lectura
    (Pos/Rot del Root) que se muestra en el panel para el slot activo.
    """
    bl_idname      = "jerryst.save_pose_changes_live"
    bl_label       = "Guardar cambios"
    bl_description = "Guarda la pose actual (huesos + Root) en la carpeta de cambios"
    bl_options      = {"REGISTER", "UNDO"}

    item_idx: IntProperty(
        default=-1,
        description="Indice del segmento cuyo slot activo se actualiza "
                    "(-1 = usar el segmento activo de la lista)",
    )

    def execute(self, context):
        scene = context.scene
        st    = scene.jerryst

        arm  = scene.objects.get(ARM_NAME)
        root = scene.objects.get(ROOT_NAME)
        if arm is None or root is None:
            self.report({"ERROR"},
                        f"No se encontraron '{ARM_NAME}' y/o el Empty "
                        f"'{ROOT_NAME}' en la escena")
            return {"CANCELLED"}

        bone_data      = capture_live_bone_pose(arm, BONES_LISTA_FULL)
        root_transform = capture_live_root_transform(root)

        # Slot activo (segmento -> action_poses) para nombrar el archivo y
        # refrescar el snapshot de solo lectura mostrado en el panel.
        slot = None
        segs = getattr(scene, "jerry_segs", None)
        if segs and segs.segments:
            idx = self.item_idx if self.item_idx >= 0 else segs.active_index
            if 0 <= idx < len(segs.segments):
                seg = segs.segments[idx]
                if seg.action_poses and 0 <= seg.action_poses_idx < len(seg.action_poses):
                    slot = seg.action_poses[seg.action_poses_idx]

        pose_name     = (slot.pose_name if slot and slot.pose_name
                         else (slot.json_file if slot and slot.json_file else "pose_editada"))
        base_filename = slot.json_file if (slot and slot.json_file) else None

        try:
            filepath = export_pose_changes(
                pose_changes_dir=st.pose_changes_dir,
                pose_name=pose_name,
                bone_data=bone_data,
                root_transform=root_transform,
                base_filename=base_filename,
                root_name=ROOT_NAME,
            )
        except Exception as e:
            self.report({"ERROR"}, f"No se pudo guardar: {e}")
            return {"CANCELLED"}

        if slot is not None:
            slot.pos_x, slot.pos_y, slot.pos_z = root_transform["pos"]
            slot.rot_x, slot.rot_y, slot.rot_z = root_transform["rot_deg"]

        if context.object and context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        self.report({"INFO"}, f"Cambios guardados: {filepath}")
        return {"FINISHED"}