# -*- coding: utf-8 -*-
"""
operators_segments.py — Rat 1 Animation Studio
Paso 3: Segmentos de refinado sobre la animacion generada por Pasos 1+2.

Port reducido desde alfred_animation_studio (operators_segments.py +
operators_anim.py), pedido explicito de Kebyn: "solo el nucleo: crear
segmentos, poses (keyframes), NLA y Concatenar". NO incluye Lanzar/
Recoger objetos, Invisibilidad de Malla, sistema de ojos ni filtros
organicos -- rat_1 no tiene esos sistemas (ver docs/PORT_NOTES.md).

LOGICA CENTRAL (identica a Alfred):
  La animacion de recorrido (generada por path_recorder.py, Paso 1+2) ya
  existe en la timeline con sus fcurves de bones (body1_1) y de root
  (rat_1). El Paso 3 NO la borra ni la reemplaza: la modula.

  RAT1SEG_OT_Apply (equivalente a ALFREDSEG_OT_Apply):
    Por cada segmento activo, escribe/mezcla las poses de accion
    directamente sobre los fcurves EXISTENTES del recorrido, en el
    mismo rango [frame_start, frame_end]. Rapido, pero no aisla un
    segmento de otro (comparten la misma action del armature).

  RAT1SEG_OT_ConcatenateAll (equivalente a ALFREDSEG_OT_ConcatenateAll +
  ALFST_OT_Concatenate): por cada segmento activo (ordenados por
  frame_start), construye una action NUEVA y aislada:
    - Si el segmento tiene poses: copia el tramo [frame_start,frame_end]
      de la Capa 1 (recorrido base, respaldado ANTES del loop para que
      ningun segmento pise a otro) y le mezcla encima las poses
      configuradas, respetando el Bloqueador de bones.
    - Si el segmento no tiene poses: copia el tramo de Capa 1 tal cual.
    Esa action aislada se empuja a su PROPIA pista NLA
    (extrapolation='NOTHING'), igual que el resto del pipeline
    (ver constants: "ConcatenateAll con NLA track isolation").

OPERADORES:
  RAT1SEG_OT_Add / Remove / Move / Duplicate / ToggleEnabled — CRUD de segmentos
  RAT1SEG_OT_SetFrameStart / SetFrameMid / SetFrameEnd — capturar frame actual
  RAT1SEG_OT_PickPoseMid — seleccionar .json para pose intermedia
  RAT1SEG_OT_AddActionPoseSeg / RemoveActionPoseSeg / MoveActionPoseSeg /
    EditActionPoseSeg — CRUD de poses (keyframes) dentro de un segmento
  RAT1SEG_OT_QuickPoseExtract — capturar la pose actual del armature a .json
  RAT1SEG_OT_AddBoneInterval / RemoveBoneInterval — Bloqueador de bones
  RAT1SEG_OT_Apply — aplica poses sobre la timeline existente (rapido, sin aislar)
  RAT1SEG_OT_ConcatenateAll — arma la secuencia completa aislada por NLA y reproduce
  RAT1SEG_OT_PlaySegment / PauseSegment / StopSegment — reproduccion de 1 segmento
  RAT1SEG_OT_SaveConfig / LoadConfig — guarda/carga configuracion_paso3.json
"""

import bpy, json, os, datetime
from bpy.types import Operator, UIList
from bpy.props import StringProperty, IntProperty, EnumProperty, FloatProperty, BoolProperty

from .constants import (
    BONES_LISTA, BONES_LISTA_FULL, _BONE_DEFAULT, INTERP_TYPE_ITEMS,
    BONE_FILTER_MAP, BONE_FILTER_ATTRS, ARM_NAME, ROOT_NAME,
)
from .organic_filters import apply_organic_filters
from .interpolation import apply_interp
from .pose_utils import (
    load_json_poses, get_pose_record, pose_record_to_full_dict,
    list_json_files, _enum_json_files, _json_file_from_index,
    _enum_poses_from_self_json, get_root_rotation_from_record,
    get_root_transform_from_record, resolve_pose_start_frames,
    open_folder,
)


# =============================================================================
# UTILIDADES INTERNAS (identicas en espiritu a operators_segments.py de Alfred)
# =============================================================================

def _load_pose_from_file(filepath, poses_dir):
    """Carga un .json de pose y devuelve el dict completo de bones."""
    path = bpy.path.abspath(filepath)
    if not os.path.isfile(path):
        candidate = os.path.join(bpy.path.abspath(poses_dir), os.path.basename(filepath))
        if os.path.isfile(candidate):
            path = candidate
        else:
            return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            if "bones" in data:
                return data["bones"]
            if "poses" in data:
                poses = data["poses"]
                if poses:
                    return poses[0].get("bones", poses[0])
            return data
    except Exception as e:
        print(f"[RAT1Seg] Error cargando pose '{path}': {e}")
    return None


def _get_bone_value(pose_dict, bone_name, channel):
    """Extrae (rx,ry,rz) / (lx,ly,lz) / (sx,sy,sz) de un dict de pose."""
    default = _BONE_DEFAULT
    d = default if pose_dict is None else pose_dict.get(bone_name, default)
    if isinstance(d, dict):
        val = d.get(channel, default[channel])
    else:
        val = default[channel]
    if isinstance(val, (list, tuple)):
        return tuple(val)
    return (0.0, 0.0, 0.0)


def _lerp3(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def _calc_seg_frames(seg):
    """Duracion total de un segmento -> (total_frames, frame_end_calculado).
    Mismo criterio que Alfred (_calc_seg_frames): si el segmento ya tiene
    un rango fijo del Paso 2 (frame_end_planned > frame_start_planned),
    ese rango manda siempre. Si no, la suma de duraciones de sus poses
    define el total. Si tampoco hay poses, se usa el rango existente."""
    if (not seg.single_coord_mode) and seg.frame_end_planned > seg.frame_start_planned:
        return seg.frame_end_planned - seg.frame_start_planned + 1, seg.frame_end_planned

    if seg.action_poses:
        starts = resolve_pose_start_frames(list(seg.action_poses), seg.frame_start)
        last_end = starts[-1] + max(1, int(seg.action_poses[-1].duration)) - 1
        total = last_end - seg.frame_start + 1
        if total > 0:
            return total, last_end

    existing_span = seg.frame_end - seg.frame_start + 1
    if existing_span > 0:
        return existing_span, seg.frame_end
    return 1, seg.frame_start


def _sync_seg_interval(seg, segs_collection=None):
    """Mantiene frame_end/frame_end_auto sincronizado con la suma de
    duraciones de las poses de accion, y desplaza en cascada a los
    segmentos posteriores si el rango de este cambio (mismo patron que
    Alfred: _sync_seg_interval)."""
    if not seg.action_poses:
        return
    old_end = seg.frame_end
    total, new_end = _calc_seg_frames(seg)
    delta = new_end - old_end
    seg.frame_end = new_end
    if seg.single_coord_mode:
        seg.frame_end_auto = new_end

    if delta != 0 and segs_collection is not None:
        seg_ptr = seg.as_pointer()
        for other in segs_collection:
            if other.as_pointer() == seg_ptr:
                continue
            if other.frame_start > seg.frame_start:
                other.frame_start += delta
                other.frame_end += delta
                if other.single_coord_mode:
                    other.frame_end_auto += delta
    return total, new_end


def _interpolate_pose_value(pose_start, pose_mid, pose_end, t_global, bone_name, channel,
                             interp_start, interp_mid_end):
    val_s = _get_bone_value(pose_start, bone_name, channel)
    val_e = _get_bone_value(pose_end, bone_name, channel)
    if pose_mid is not None:
        val_m = _get_bone_value(pose_mid, bone_name, channel)
        if t_global < 0.5:
            t_curved = apply_interp(t_global * 2.0, interp_start)
            return _lerp3(val_s, val_m, t_curved)
        else:
            t_curved = apply_interp((t_global - 0.5) * 2.0, interp_mid_end)
            return _lerp3(val_m, val_e, t_curved)
    t_curved = apply_interp(t_global, interp_start)
    return _lerp3(val_s, val_e, t_curved)


def _blend_alpha(t_global, total_frames, blend_in_frames, blend_out_frames, blend_strength):
    frame_idx = t_global * total_frames
    alpha = 1.0
    if blend_in_frames > 0 and frame_idx < blend_in_frames:
        a = min(frame_idx / blend_in_frames, 1.0)
        alpha = a * a * (3 - 2 * a)
    frames_from_end = total_frames - frame_idx
    if blend_out_frames > 0 and frames_from_end < blend_out_frames:
        a_out = min(frames_from_end / blend_out_frames, 1.0)
        a_out = a_out * a_out * (3 - 2 * a_out)
        alpha = min(alpha, a_out)
    return alpha * blend_strength


def _get_or_create_fcurve(action, data_path, index):
    fc = action.fcurves.find(data_path, index=index)
    if fc is None:
        fc = action.fcurves.new(data_path=data_path, index=index)
    return fc


def _set_keyframe(action, data_path, index, frame, value):
    fc = _get_or_create_fcurve(action, data_path, index)
    for kp in fc.keyframe_points:
        if abs(kp.co.x - frame) < 0.5:
            kp.co.y = value
            fc.update()
            return
    fc.keyframe_points.insert(frame=frame, value=value, options={"FAST"})
    fc.update()


def _resolve_armature(seg_cfg, scene):
    arm = scene.objects.get(seg_cfg.armature_name or ARM_NAME)
    if arm and arm.type == "ARMATURE":
        return arm
    arm = scene.objects.get(ARM_NAME)
    if arm and arm.type == "ARMATURE":
        return arm
    return None


def _bone_full_blocked(seg, bone_name):
    """True si el bone esta bloqueado por el checkbox simple del
    Bloqueador de bones (bloqueado en TODO el segmento)."""
    attr = BONE_FILTER_MAP.get(bone_name)
    if attr is None:
        return False
    return getattr(seg, attr, False)


def _get_bone_block_entry(seg, bone_key, create=False):
    for entry in seg.bone_blocks:
        if entry.bone_key == bone_key:
            return entry
    if create:
        entry = seg.bone_blocks.add()
        entry.bone_key = bone_key
        return entry
    return None


def _bone_blocked_in_intervals(seg, bone_name, frame):
    """True si 'frame' cae dentro de algun intervalo de bloqueo parcial
    definido para este bone."""
    attr = BONE_FILTER_MAP.get(bone_name)
    if attr is None:
        return False
    entry = _get_bone_block_entry(seg, attr, create=False)
    if entry is None:
        return False
    for iv in entry.intervals:
        if iv.enabled and iv.frame_start <= frame <= iv.frame_end:
            return True
    return False


def _bone_is_filtered(seg, bone_name, frame=None):
    if _bone_full_blocked(seg, bone_name):
        return True
    if frame is not None and _bone_blocked_in_intervals(seg, bone_name, frame):
        return True
    return False


def _copy_action_range(src_action, frame_start, frame_end, new_action_name):
    """Copia a una action NUEVA, en memoria, los keyframes de src_action
    dentro de [frame_start, frame_end]. Operacion puramente sobre datos:
    no toca ningun objeto de la escena. Usado para aislar cada segmento
    de la Capa 1 real (recorrido base), sin importar en que orden se
    procesen los demas segmentos (mismo patron que Alfred: _copy_action_range)."""
    if src_action is None:
        return None
    new_action = bpy.data.actions.new(new_action_name)
    any_kp = False
    for src_fc in src_action.fcurves:
        kps = sorted(
            [kp for kp in src_fc.keyframe_points if frame_start <= kp.co.x <= frame_end],
            key=lambda k: k.co.x,
        )
        if not kps:
            continue
        new_fc = new_action.fcurves.new(
            src_fc.data_path, index=src_fc.array_index,
            action_group=src_fc.group.name if src_fc.group else "")
        new_fc.keyframe_points.add(len(kps))
        for i, kp in enumerate(kps):
            nkp = new_fc.keyframe_points[i]
            nkp.co = kp.co
            nkp.interpolation = kp.interpolation
            nkp.easing = kp.easing
            nkp.handle_left = kp.handle_left
            nkp.handle_right = kp.handle_right
            nkp.handle_left_type = kp.handle_left_type
            nkp.handle_right_type = kp.handle_right_type
        new_fc.update()
        any_kp = True
    if not any_kp:
        bpy.data.actions.remove(new_action)
        return None
    return new_action


def _push_action_to_nla(obj, action, frame_start, frame_end, track_name):
    """Empuja una action YA CONSTRUIDA a su propia pista NLA dedicada y
    aislada (extrapolation='NOTHING'). Deja animation_data.action = None
    despues, para que ninguna action activa quede pisando el stack NLA."""
    if obj is None or action is None or not action.fcurves:
        if action is not None:
            bpy.data.actions.remove(action)
        return
    if not obj.animation_data:
        obj.animation_data_create()
    track = obj.animation_data.nla_tracks.new()
    track.name = track_name
    strip = track.strips.new(track_name, int(frame_start), action)
    strip.use_sync_length = False
    strip.action_frame_start = frame_start
    strip.action_frame_end = frame_end
    strip.frame_start = frame_start
    strip.frame_end = frame_end
    strip.extrapolation = 'NOTHING'
    strip.blend_type = 'REPLACE'
    obj.animation_data.action = None


def _bake_poses_into_action(seg, action, poses_dir, f_start, f_end):
    """Escribe las poses de accion del segmento en `action`, dentro de
    [f_start, f_end], respetando el Bloqueador de bones. Es el nucleo
    compartido entre RAT1SEG_OT_Apply (in-place) y RAT1SEG_OT_ConcatenateAll
    (sobre una action aislada nueva)."""
    total_frames = f_end - f_start
    if total_frames <= 0:
        return False, "frame_end <= frame_start"

    act_list = list(seg.action_poses)
    pose_start = _load_pose_from_file(act_list[0].json_file, poses_dir) if act_list else None
    pose_end = _load_pose_from_file(act_list[-1].json_file, poses_dir) if act_list else None
    pose_mid = _load_pose_from_file(seg.pose_mid_file, poses_dir) if seg.pose_mid_file else None

    if pose_start is None and pose_end is None:
        return False, "sin poses cargadas"
    if pose_start is None:
        pose_start = pose_end
    if pose_end is None:
        pose_end = pose_start

    for bone_name in BONES_LISTA_FULL:
        if _bone_full_blocked(seg, bone_name):
            continue
        dp_rot = f'pose.bones["{bone_name}"].rotation_euler'
        dp_loc = f'pose.bones["{bone_name}"].location'
        dp_scale = f'pose.bones["{bone_name}"].scale'

        for frame in range(f_start, f_end + 1):
            if _bone_blocked_in_intervals(seg, bone_name, frame):
                continue
            t_global = (frame - f_start) / max(1, total_frames)
            alpha = _blend_alpha(t_global, total_frames, seg.blend_in_frames,
                                  seg.blend_out_frames, seg.blend_strength)
            if alpha <= 0.0:
                continue
            rot_pose = _interpolate_pose_value(pose_start, pose_mid, pose_end, t_global,
                                                bone_name, "rot", seg.interp_type, seg.interp_mid_to_end)
            loc_pose = _interpolate_pose_value(pose_start, pose_mid, pose_end, t_global,
                                                bone_name, "loc", seg.interp_type, seg.interp_mid_to_end)
            sca_pose = _interpolate_pose_value(pose_start, pose_mid, pose_end, t_global,
                                                bone_name, "scale", seg.interp_type, seg.interp_mid_to_end)
            for axis_idx, (pv_rot, pv_loc, pv_sca) in enumerate(zip(rot_pose, loc_pose, sca_pose)):
                # El blend nunca parte de un valor ya presente en el fcurve
                # (independencia entre segmentos): siempre desde el rest pose.
                _set_keyframe(action, dp_rot, axis_idx, frame, 0.0 + pv_rot * alpha)
                _set_keyframe(action, dp_loc, axis_idx, frame, 0.0 + pv_loc * alpha)
                _set_keyframe(action, dp_scale, axis_idx, frame, 1.0 + (pv_sca - 1.0) * alpha)
    return True, ""


# =============================================================================
# OPERADOR: APLICAR SEGMENTOS (in-place, rapido, sin aislar por NLA)
# =============================================================================

class RAT1SEG_OT_Apply(Operator):
    bl_idname = "rat1seg.apply"
    bl_label = "APLICAR SEGMENTOS"
    bl_description = (
        "Aplica todos los segmentos activos del Paso 3 sobre la animacion de "
        "recorrido generada por los Pasos 1+2. Los bones configurados adoptaran "
        "las poses definidas en cada segmento, mezcladas con el movimiento existente."
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        seg_cfg = scene.rat1_segs
        segments = [s for s in seg_cfg.segments if s.enabled]
        if not segments:
            self.report({"WARNING"}, "No hay segmentos activos en el Paso 3")
            return {"CANCELLED"}

        armature = _resolve_armature(seg_cfg, scene)
        if armature is None:
            self.report({"ERROR"}, f"No se encontro armature '{seg_cfg.armature_name}'")
            return {"CANCELLED"}

        if armature.pose:
            for bone_name in BONES_LISTA_FULL:
                pb = armature.pose.bones.get(bone_name)
                if pb is not None and pb.rotation_mode != "XYZ":
                    pb.rotation_mode = "XYZ"

        if not armature.animation_data or not armature.animation_data.action:
            self.report({"ERROR"}, "El armature no tiene una action activa (corre 'Reproducir recorrido' primero)")
            return {"CANCELLED"}
        action = armature.animation_data.action

        poses_dir = bpy.path.abspath(seg_cfg.poses_dir)
        applied, errors = 0, []
        for seg in segments:
            ok, err = _bake_poses_into_action(seg, action, poses_dir, seg.frame_start, seg.frame_end)
            if ok:
                applied += 1
            else:
                errors.append(f"Segmento '{seg.label}': {err}, ignorado")

        seg_cfg.segs_applied = True
        msg = f"{applied} segmentos aplicados"
        if errors:
            msg += f" | {len(errors)} advertencias"
            for e in errors:
                print(f"[Rat1Seg] {e}")
        seg_cfg.status_msg = msg
        self.report({"INFO"}, msg)
        return {"FINISHED"}


# =============================================================================
# OPERADOR: CONCATENAR SEGMENTOS (NLA aislado por segmento)
# =============================================================================

class RAT1SEG_OT_ConcatenateAll(Operator):
    """Para CADA segmento activo (ordenado por frame_start), construye una
    action aislada (poses mezcladas sobre una copia intacta de la Capa 1)
    y la empuja a su PROPIA pista NLA. Al terminar reproduce la secuencia
    completa de principio a fin."""
    bl_idname = "rat1seg.concatenate_all"
    bl_label = "Concatenar segmentos"
    bl_description = (
        "Ejecuta CONCATENAR (inyectar poses -> bones configurados, aislado por "
        "NLA) para todos los segmentos activos del Paso 3, respetando la "
        "secuencia de frames propia de cada uno, y reproduce todo de principio a fin"
    )
    bl_options = {"REGISTER"}

    def execute(self, context):
        scene = context.scene
        seg_cfg = scene.rat1_segs

        indexed = [s for s in seg_cfg.segments if s.enabled]
        indexed.sort(key=lambda s: s.frame_start)
        if not indexed:
            self.report({"WARNING"}, "No hay segmentos activos en el Paso 3")
            return {"CANCELLED"}

        armature = _resolve_armature(seg_cfg, scene)
        root_empty = scene.objects.get(ROOT_NAME)
        if armature is None:
            self.report({"ERROR"}, f"No se encontro armature '{seg_cfg.armature_name}'")
            return {"CANCELLED"}

        # Regenerar la Capa 1 (recorrido base: caminar/saltar/parada) antes de
        # inyectar ninguna pose, para que el canvas de partida este fresco
        # (mismo fix que Alfred: ALFREDSEG_OT_ConcatenateAll).
        if bpy.ops.rat1pr.preview_path.poll():
            regen = bpy.ops.rat1pr.preview_path()
            if "CANCELLED" in regen:
                self.report({"ERROR"}, "No se pudo regenerar el recorrido base (Capa 1) antes de concatenar.")
                return {"CANCELLED"}
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()

        # ── Respaldo intacto de la Capa 1 (armature + root) ──────────────
        # Ningun segmento debe pisar la fuente que usan los demas: se copia
        # UNA VEZ antes del loop y nunca se modifica durante este.
        for stale in list(bpy.data.actions):
            if stale.name.startswith("RAT1_CAPA1_BACKUP_"):
                bpy.data.actions.remove(stale)

        backup_arm_action = None
        backup_root_action = None
        if armature.animation_data and armature.animation_data.action:
            backup_arm_action = armature.animation_data.action.copy()
            backup_arm_action.name = f"RAT1_CAPA1_BACKUP_arm_{scene.name}"
            backup_arm_action.use_fake_user = True
        if root_empty is not None and root_empty.animation_data and root_empty.animation_data.action:
            backup_root_action = root_empty.animation_data.action.copy()
            backup_root_action.name = f"RAT1_CAPA1_BACKUP_root_{scene.name}"
            backup_root_action.use_fake_user = True

        if backup_arm_action is None:
            self.report({"ERROR"}, "El armature no tiene animacion base (Capa 1) para concatenar.")
            return {"CANCELLED"}

        poses_dir = bpy.path.abspath(seg_cfg.poses_dir)
        original_active = seg_cfg.active_index
        f_min, f_max = None, None
        done, errors = 0, []

        for orig_idx, seg in enumerate(indexed):
            f_start = seg.frame_start
            _, f_end_calc = _calc_seg_frames(seg)
            f_end = seg.frame_end if seg.frame_end > f_start else f_end_calc
            if f_end <= f_start:
                errors.append(f"Segmento '{seg.label}': frame_end <= frame_start, ignorado")
                continue

            # Copiar el tramo de la Capa 1 respaldada (nunca la version en
            # vivo, que ya pudo haber sido pisada por un segmento anterior).
            seg_action_name = f"rat1seg_{seg.label.replace(' ', '_')}"[:63]
            old = bpy.data.actions.get(seg_action_name)
            if old is not None:
                bpy.data.actions.remove(old)
            seg_action = _copy_action_range(backup_arm_action, f_start, f_end, seg_action_name)
            if seg_action is None:
                seg_action = bpy.data.actions.new(seg_action_name)

            if seg.action_poses:
                ok, err = _bake_poses_into_action(seg, seg_action, poses_dir, f_start, f_end)
                if not ok:
                    errors.append(f"Segmento '{seg.label}': {err}")
            else:
                errors.append(f"Segmento '{seg.label}': sin poses de accion, se dejo solo el recorrido base")

            # El root (desplazamiento del recorrido) tambien se aisla igual,
            # copiado de su propio respaldo de Capa 1. Se construye ANTES de
            # aplicar los filtros organicos (necesitan las dos actions ya
            # armadas para poder escribir tanto en bones del armature como
            # en la posicion del objeto raiz "rat_1" en el mismo pase).
            root_seg_action = None
            if root_empty is not None and backup_root_action is not None:
                root_seg_name = f"rat1seg_root_{seg.label.replace(' ', '_')}"[:63]
                old_root = bpy.data.actions.get(root_seg_name)
                if old_root is not None:
                    bpy.data.actions.remove(old_root)
                root_seg_action = _copy_action_range(backup_root_action, f_start, f_end, root_seg_name)

            # ── Filtros organicos (post-proceso, aislado por segmento) ──
            # Se aplican SIEMPRE (con o sin poses de accion) para que la
            # respiracion/head-sway/etc. tambien cubran los tramos sin pose,
            # igual que en alfred_animation_studio (mismo bugfix documentado
            # ahi: "los filtros organicos no se reproducen en segmentos sin
            # poses"). org = seg.organic -> instancia PROPIA de ESTE
            # segmento, aislada de los demas.
            org = getattr(seg, "organic", None)
            if org is not None and org.enabled:
                apply_organic_filters(
                    context, armature, f_start, f_end, org,
                    target_action=seg_action,
                    target_action_root=root_seg_action,
                )

            _push_action_to_nla(armature, seg_action, f_start, f_end, f"Rat1Seg_{orig_idx:02d}_{seg.label}")

            if root_empty is not None and root_seg_action is not None:
                _push_action_to_nla(root_empty, root_seg_action, f_start, f_end, f"Rat1SegRoot_{orig_idx:02d}_{seg.label}")

            done += 1
            f_min = f_start if f_min is None else min(f_min, f_start)
            f_max = f_end if f_max is None else max(f_max, f_end)

        seg_cfg.active_index = original_active

        for final_obj in (armature, root_empty):
            if final_obj is not None and final_obj.animation_data:
                final_obj.animation_data.action = None

        if backup_arm_action is not None:
            bpy.data.actions.remove(backup_arm_action)
        if backup_root_action is not None:
            bpy.data.actions.remove(backup_root_action)

        if done == 0:
            self.report({"ERROR"}, "Ningun segmento pudo concatenarse: " + " | ".join(errors))
            return {"CANCELLED"}

        if f_min is not None:
            if scene.frame_start > f_min:
                scene.frame_start = f_min
            if scene.frame_end < f_max:
                scene.frame_end = f_max
            scene.frame_set(f_min)

        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()

        def _deferred_play():
            if not bpy.context.screen.is_animation_playing:
                bpy.ops.screen.animation_play()
            return None
        bpy.app.timers.register(_deferred_play, first_interval=0.02)

        seg_cfg.segs_applied = True
        seg_cfg.status_msg = (
            f"Secuencia concatenada: {done}/{len(indexed)} segmentos, frames {f_min}->{f_max}"
            + (f" | {len(errors)} advertencias" if errors else "")
        )
        for e in errors:
            print(f"[ConcatenarTodo] {e}")
        self.report({"INFO"}, seg_cfg.status_msg)
        return {"FINISHED"}


# =============================================================================
# CRUD DE SEGMENTOS
# =============================================================================

class RAT1SEG_OT_Add(Operator):
    bl_idname = "rat1seg.add"
    bl_label = "Agregar segmento"
    bl_description = "Agrega un nuevo segmento de refinado al Paso 3"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        segs = context.scene.rat1_segs
        fs = segs.edit_frame_start
        fe = segs.edit_frame_end

        if fe <= fs:
            self.report({"ERROR"}, f"Frame fin {fe} invalido (debe ser mayor que el inicio {fs})")
            return {"CANCELLED"}

        for i, s in enumerate(segs.segments):
            if not s.enabled:
                continue
            if fs <= s.frame_end and fe >= s.frame_start:
                self.report({"ERROR"}, f"Solapamiento con segmento [{i+1}] ({s.frame_start}->{s.frame_end})")
                return {"CANCELLED"}

        seg = segs.segments.add()
        seg.label = segs.edit_label or f"Segmento {len(segs.segments)}"
        seg.frame_start = fs
        seg.frame_end = fe
        seg.frame_start_planned = fs
        seg.frame_end_planned = fe
        seg.frame_end_auto = 0
        seg.enabled = True

        if segs.edit_use_mid:
            seg.frame_mid = segs.edit_frame_mid
            seg.pose_mid_file = segs.edit_pose_mid_file
            seg.pose_mid_label = segs.edit_pose_mid_label
        seg.interp_type = segs.edit_interp
        seg.interp_mid_to_end = segs.edit_interp_mid
        seg.blend_in_frames = segs.edit_start_frames
        seg.blend_out_frames = segs.edit_end_frames

        segs.active_index = len(segs.segments) - 1
        self.report({"INFO"}, f"Segmento '{seg.label}' agregado [{fs}->{fe}]")
        return {"FINISHED"}


class RAT1SEG_OT_AutoSplitFromConfig(Operator):
    """
    Port de ALFREDSEG_OT_AutoSplitFromConfig (alfred_animation_studio,
    operators_segments.py): en vez de que todo el recorrido (caminar/
    saltar_subir/saltar_bajar/parada) quede acumulado en un unico
    Rat1AnimSegment gigante, este operador crea UN Rat1AnimSegment por
    cada tramo del recorrido, leyendo directamente la misma lista que ya
    se ve en el panel del Paso 2 bajo "Estimacion de segmentos:"
    (calcular_estimacion_geometrica(), path_recorder.py -- la fuente que
    agrupa scene.rat1_path.path_points en tramos). El boton "Dividir
    segmentos" crea tantos segmentos como tramos aparecen en esa lista,
    con frame_start/frame_end calculados acumulando "frames_estimados"
    de cada tramo a partir de scene.rat1_path.frame_inicio -- el mismo
    orden y las mismas duraciones que ya se preveian en el panel antes
    de dividir.

    JERARQUIA (adaptado a rat_1, NO copiado de Alfred): Alfred es un
    rig bipedo (bone raiz "Hips_alfred", piernas "leg/knee") y ademas
    auto-registra objetos (antorcha/mesa de crafteo) que rat_1 no tiene.
    rat_1 es un rig cuadrupedo de 22 bones (ver constants.py): el bone
    raiz real es ROOT_BONE='body1_1', y las "piernas" son las 4 patas
    (filter_left_thigh/foot, filter_right_thigh/foot -- equivalentes a
    BONE_FILTER_DEFAULT_TRUE). No hay sistema de Lanzar/Recoger objetos
    en rat_1 (docs/PORT_NOTES.md), asi que ese bloque de Alfred
    (colocar_antorcha/colocar_mesa_de_crafteo) no aplica aca -- los
    unicos tipos de tramo posibles son caminar/saltar_subir/
    saltar_bajar/parada (ver calcular_estimacion_geometrica).

    Cada segmento nuevo queda:
      - label: "{indice:02d}_{tipo}" -- ej. "04_parada", "06_caminar".
      - frame_start/frame_end (y su "foto" frame_start_planned/
        frame_end_planned): acumulados desde la estimacion.
      - Bloqueador de bones: las 4 patas quedan BLOQUEADAS solo en
        tramos "caminar" (el recorrido base ya las anima ahi; en
        "parada"/"saltar_*" quedan LIBRES para que la pose del
        segmento controle el cuerpo completo -- mismo criterio que
        Alfred con sus piernas, aplicado a la jerarquia de rat_1).
      - Poses (action_poses) quedan en blanco: cada tramo se configura
        despues individualmente, igual que en Alfred.

    RAT1SEG_OT_ConcatenateAll no necesita sampleo frame a frame del
    Empty raiz como el AutoSplit de Alfred (que arma su propia
    seg_action): reconstruye cada segmento copiando el tramo
    [frame_start,frame_end] desde un respaldo de la Capa 1 (recorrido
    base ya grabado por 'Reproducir recorrido', Paso 2) -- ver
    _copy_action_range() mas arriba. Por eso este operador solo necesita
    fijar frame_start/frame_end correctos, sin tocar ninguna action.
    """
    bl_idname = "rat1seg.autosplit_from_config"
    bl_label = "Dividir segmentos"
    bl_description = (
        "Crea un segmento independiente por cada tramo (caminar/saltar_subir/"
        "saltar_bajar/parada) segun la 'Estimacion de segmentos' del "
        "recorrido grabado, en vez de un unico segmento que cubre todo "
        "el recorrido"
    )
    bl_options = {"REGISTER", "UNDO"}

    reemplazar_existentes: BoolProperty(
        name="Reemplazar segmentos existentes",
        description="Si esta activo, borra todos los segmentos actuales antes de crear los nuevos",
        default=True,
        options={"SKIP_SAVE"},
    )

    def execute(self, context):
        scene = context.scene
        pc = getattr(scene, "rat1_path", None)
        if pc is None:
            self.report({"ERROR"}, "No se encontro el recorrido (scene.rat1_path).")
            return {"CANCELLED"}

        from .path_recorder import calcular_estimacion_geometrica
        slots_est = calcular_estimacion_geometrica(scene)
        if not slots_est:
            self.report({"ERROR"},
                "No hay 'Estimacion de segmentos' para dividir. Graba primero "
                "un recorrido en el Paso 1 (2 o mas puntos) para que aparezca "
                "la lista 'Estimacion de segmentos' en el panel del Paso 2.")
            return {"CANCELLED"}

        base_frame = pc.frame_inicio if pc.frame_inicio else 1
        tramos = []
        cursor = base_frame
        for s in slots_est:
            dur = max(1, int(s["frames_estimados"]))
            fs = cursor
            fe = fs + dur - 1
            tramos.append({"tipo": s["tipo"], "frame_start": fs, "frame_end": fe})
            cursor = fe + 1

        segs = scene.rat1_segs

        if self.reemplazar_existentes:
            segs.segments.clear()

        armature = _resolve_armature(segs, scene)
        if armature is None:
            self.report({"ERROR"},
                f"No se encontro el armature '{segs.armature_name}'. Verifica "
                "'Armature' en la config del Paso 3.")
            return {"CANCELLED"}

        root_empty = scene.objects.get(ROOT_NAME)
        if root_empty is None or not root_empty.animation_data:
            self.report({"WARNING"},
                f"No se encontro el Empty '{ROOT_NAME}' con animation_data "
                "(recorrido de Pasos 1+2). Los segmentos se crean igual con "
                "frame_start/frame_end correctos, pero corre 'Reproducir "
                "recorrido' (Paso 2) antes de Concatenar para que haya "
                "desplazamiento real que copiar en cada tramo.")

        # FIX (mismo criterio que Alfred: "los movimientos del personaje solo
        # se reproducen hasta X"): tramos[] se arma arriba con el total EN
        # VIVO de calcular_estimacion_geometrica() (lee los valores actuales
        # del Paso 1/2). Si el recorrido grabado (accion del armature, fijada
        # la ultima vez que se corrio 'Reproducir recorrido') termina antes
        # que la estimacion actual, los ultimos frames del ultimo tramo
        # quedarian sin movimiento real que copiar al Concatenar. Se detecta
        # el desfase ANTES de crear nada.
        if armature.animation_data and armature.animation_data.action:
            _real_end = armature.animation_data.action.frame_range[1]
            _est_end = tramos[-1]["frame_end"] if tramos else None
            if _est_end is not None and abs(_real_end - _est_end) >= 1:
                self.report({"ERROR"},
                    f"El recorrido grabado llega solo hasta el frame {_real_end:.0f}, "
                    f"pero la 'Estimacion de segmentos' actual suma {_est_end} frames "
                    "-- probablemente cambiaste frames por parada (u otro tramo) "
                    "despues de la ultima vez que corriste 'Reproducir recorrido'. "
                    "Corre 'Reproducir recorrido' (Paso 2) de nuevo y despues "
                    "volve a dividir segmentos.")
                return {"CANCELLED"}

        creados = 0
        errores = []
        for i, tramo in enumerate(tramos, start=1):
            tipo = tramo["tipo"]
            fs = tramo["frame_start"]
            fe = tramo["frame_end"]
            if fe <= fs:
                errores.append(f"Tramo {i} ({tipo}): frame_end <= frame_start, omitido")
                continue

            seg = segs.segments.add()
            seg.label = f"{i:02d}_{tipo}"
            seg.frame_start = fs
            seg.frame_end = fe
            # Foto del Paso 2 (ver Rat1AnimSegment.frame_start_planned en
            # properties.py): esta es la unica vez que estos dos campos se
            # setean al DIVIDIR el recorrido -- de aca en mas las poses del
            # Paso 3 pueden mover frame_start/frame_end libremente sin
            # afectarlos.
            seg.frame_start_planned = fs
            seg.frame_end_planned = fe
            seg.frame_end_auto = 0
            seg.single_coord_mode = False
            seg.enabled = True
            seg.show_config = False
            seg.interp_type = "SMOOTH"
            seg.blend_in_frames = 0
            seg.blend_out_frames = 0
            seg.blend_strength = 1.0

            # ── Bloqueador de bones: jerarquia REAL de rat_1 (ver docstring
            # de la clase) -- las 4 patas bloqueadas solo en "caminar",
            # libres en "parada"/"saltar_subir"/"saltar_bajar". La raiz
            # (filter_body1) queda libre: el desplazamiento del recorrido lo
            # controla el Empty "rat_1", nunca este filtro.
            _patas_bloqueadas = (tipo == "caminar")
            seg.filter_body1 = False
            seg.filter_left_thigh = _patas_bloqueadas
            seg.filter_left_foot = _patas_bloqueadas
            seg.filter_right_thigh = _patas_bloqueadas
            seg.filter_right_foot = _patas_bloqueadas

            creados += 1

        segs.active_index = len(segs.segments) - 1 if segs.segments else 0

        for area in context.screen.areas:
            area.tag_redraw()

        msg = f"{creados}/{len(tramos)} segmentos creados"
        if errores:
            msg += f"  |  {len(errores)} con problemas (ver consola)"
            for e in errores:
                print(f"[Rat1Seg] {e}")
            self.report({"WARNING"}, msg)
        else:
            self.report({"INFO"}, msg)
        segs.status_msg = msg
        return {"FINISHED"}


class RAT1SEG_OT_Remove(Operator):
    bl_idname = "rat1seg.remove"
    bl_label = "Eliminar segmento"
    bl_description = "Elimina el segmento activo"
    bl_options = {"REGISTER", "UNDO"}
    item_idx: IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.rat1_segs
        idx = self.item_idx if self.item_idx >= 0 else segs.active_index
        if 0 <= idx < len(segs.segments):
            segs.segments.remove(idx)
            segs.active_index = max(0, idx - 1)
            self.report({"INFO"}, "Segmento eliminado")
        else:
            self.report({"WARNING"}, "No hay segmento seleccionado")
        return {"FINISHED"}


class RAT1SEG_OT_Move(Operator):
    bl_idname = "rat1seg.move"
    bl_label = "Mover segmento"
    bl_description = "Sube o baja el segmento activo en la lista"
    bl_options = {"REGISTER", "UNDO"}
    direction: EnumProperty(items=[("UP", "Arriba", ""), ("DOWN", "Abajo", "")])

    def execute(self, context):
        segs = context.scene.rat1_segs
        idx = segs.active_index
        n = len(segs.segments)
        if self.direction == "UP" and idx > 0:
            segs.segments.move(idx, idx - 1)
            segs.active_index = idx - 1
        elif self.direction == "DOWN" and idx < n - 1:
            segs.segments.move(idx, idx + 1)
            segs.active_index = idx + 1
        return {"FINISHED"}


class RAT1SEG_OT_Duplicate(Operator):
    bl_idname = "rat1seg.duplicate"
    bl_label = "Duplicar segmento"
    bl_description = "Duplica el segmento activo"
    bl_options = {"REGISTER", "UNDO"}
    item_idx: IntProperty(default=-1)

    _scalar_attrs = (
        "label", "frame_start", "frame_end", "frame_mid",
        "frame_start_planned", "frame_end_planned",
        "single_coord_mode", "frame_end_auto", "fps",
        "pose_mid_file", "pose_mid_label",
        "interp_type", "interp_mid_to_end",
        "blend_in_frames", "blend_out_frames", "blend_strength",
        "enabled", "show_config",
    ) + tuple(BONE_FILTER_ATTRS)
    _slot_attrs = (
        "json_file", "pose_label", "pose_name", "duration",
        "entry_ratio", "exit_ratio", "interp_type",
        "rot_x", "rot_y", "rot_z", "pos_x", "pos_y", "pos_z",
        "manual_start", "frame_abs_start",
    )

    def execute(self, context):
        segs = context.scene.rat1_segs
        idx = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "No hay segmento seleccionado")
            return {"CANCELLED"}
        src = segs.segments[idx]
        dst = segs.segments.add()
        for attr in self._scalar_attrs:
            try:
                setattr(dst, attr, getattr(src, attr))
            except Exception:
                pass
        dst.action_poses.clear()
        for src_slot in src.action_poses:
            dst_slot = dst.action_poses.add()
            for a in self._slot_attrs:
                try:
                    setattr(dst_slot, a, getattr(src_slot, a))
                except Exception:
                    pass
        dst.label = src.label + " (copia)"
        segs.active_index = len(segs.segments) - 1
        return {"FINISHED"}


class RAT1SEG_OT_ToggleEnabled(Operator):
    bl_idname = "rat1seg.toggle_enabled"
    bl_label = "Activar/desactivar segmento"
    bl_options = {"REGISTER", "UNDO"}
    item_idx: IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.rat1_segs
        idx = self.item_idx if self.item_idx >= 0 else segs.active_index
        if 0 <= idx < len(segs.segments):
            segs.segments[idx].enabled = not segs.segments[idx].enabled
        return {"FINISHED"}


# =============================================================================
# BLOQUEADOR DE BONES: intervalos de bloqueo parcial
# =============================================================================

class RAT1SEG_OT_AddBoneInterval(Operator):
    bl_idname = "rat1seg.add_bone_interval"
    bl_label = "Agregar intervalo de bloqueo"
    bl_description = "Agrega un intervalo de frames en el que este bone quedara bloqueado"
    bl_options = {"REGISTER", "UNDO"}
    item_idx: IntProperty(default=-1)
    bone_key: StringProperty(default="")

    def execute(self, context):
        segs = context.scene.rat1_segs
        idx = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "Segmento invalido")
            return {"CANCELLED"}
        seg = segs.segments[idx]
        entry = _get_bone_block_entry(seg, self.bone_key, create=True)
        if len(entry.intervals):
            new_start = entry.intervals[-1].frame_end + 1
        else:
            new_start = seg.frame_start
        new_end = new_start + 10
        iv = entry.intervals.add()
        iv.frame_start = max(0, new_start)
        iv.frame_end = max(iv.frame_start + 1, new_end)
        entry.intervals_idx = len(entry.intervals) - 1
        return {"FINISHED"}


class RAT1SEG_OT_RemoveBoneInterval(Operator):
    bl_idname = "rat1seg.remove_bone_interval"
    bl_label = "Eliminar intervalo de bloqueo"
    bl_options = {"REGISTER", "UNDO"}
    item_idx: IntProperty(default=-1)
    bone_key: StringProperty(default="")
    interval_idx: IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.rat1_segs
        idx = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)):
            return {"CANCELLED"}
        seg = segs.segments[idx]
        entry = _get_bone_block_entry(seg, self.bone_key, create=False)
        if entry is None or not (0 <= self.interval_idx < len(entry.intervals)):
            return {"CANCELLED"}
        entry.intervals.remove(self.interval_idx)
        entry.intervals_idx = max(0, min(entry.intervals_idx, len(entry.intervals) - 1))
        return {"FINISHED"}


# =============================================================================
# CAPTURA DE FRAMES DESDE LA TIMELINE Y SELECTOR DE POSE INTERMEDIA
# =============================================================================

class RAT1SEG_OT_SetFrameStart(Operator):
    bl_idname = "rat1seg.set_frame_start"
    bl_label = "Frame actual -> Inicio"
    bl_description = "Usa el frame actual de la timeline como frame de inicio del segmento"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        segs = context.scene.rat1_segs
        idx = segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "No hay segmento seleccionado")
            return {"CANCELLED"}
        segs.segments[idx].frame_start = context.scene.frame_current
        return {"FINISHED"}


class RAT1SEG_OT_SetFrameMid(Operator):
    bl_idname = "rat1seg.set_frame_mid"
    bl_label = "Frame actual -> Intermedio"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        segs = context.scene.rat1_segs
        idx = segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "No hay segmento seleccionado")
            return {"CANCELLED"}
        segs.segments[idx].frame_mid = context.scene.frame_current
        return {"FINISHED"}


class RAT1SEG_OT_SetFrameEnd(Operator):
    bl_idname = "rat1seg.set_frame_end"
    bl_label = "Frame actual -> Fin"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        segs = context.scene.rat1_segs
        idx = segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "No hay segmento seleccionado")
            return {"CANCELLED"}
        segs.segments[idx].frame_end = context.scene.frame_current
        return {"FINISHED"}


class RAT1SEG_OT_PickPoseMid(Operator):
    bl_idname = "rat1seg.pick_pose_mid"
    bl_label = "Seleccionar pose INTERMEDIA"
    bl_description = "Abre explorador para seleccionar el .json de la pose intermedia (opcional)"
    bl_options = {"REGISTER", "UNDO"}
    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context):
        segs = context.scene.rat1_segs
        segs.edit_pose_mid_file = self.filepath
        segs.edit_pose_mid_label = os.path.basename(self.filepath)
        self.report({"INFO"}, f"Pose cargada: {os.path.basename(self.filepath)}")
        return {"FINISHED"}

    def invoke(self, context, event):
        segs = context.scene.rat1_segs
        self.filepath = bpy.path.abspath(segs.poses_dir) if segs.poses_dir else ""
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


# =============================================================================
# POSES (KEYFRAMES) DENTRO DE UN SEGMENTO
# =============================================================================

class RAT1SEG_OT_AddActionPoseSeg(Operator):
    bl_idname = "rat1seg.add_action_pose_seg"
    bl_label = "Agregar pose al segmento"
    bl_description = "Agrega una pose de accion (keyframe) a este segmento"
    bl_options = {"REGISTER", "UNDO"}
    item_idx: IntProperty(default=-1)

    json_file: EnumProperty(name="Archivo JSON", items=_enum_json_files)
    pose_index: EnumProperty(name="Pose", items=_enum_poses_from_self_json)
    duration: IntProperty(name="Duracion (frames)", default=20, min=2, max=9999)
    interp_type: EnumProperty(name="Interpolacion", items=INTERP_TYPE_ITEMS, default="SMOOTH")
    manual_start: BoolProperty(name="Elegir frame de inicio", default=False)
    frame_abs_start: IntProperty(name="Frame de inicio", default=0, min=0)

    def _get_seg(self, context):
        segs = context.scene.rat1_segs
        idx = self.item_idx if self.item_idx >= 0 else segs.active_index
        if 0 <= idx < len(segs.segments):
            return segs.segments[idx]
        return None

    def invoke(self, context, event):
        seg = self._get_seg(context)
        if seg is not None:
            starts = resolve_pose_start_frames(list(seg.action_poses), seg.frame_start)
            if seg.action_poses:
                self.frame_abs_start = starts[-1] + max(1, int(seg.action_poses[-1].duration))
            else:
                self.frame_abs_start = seg.frame_start
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        layout = self.layout
        seg = self._get_seg(context)
        layout.label(text="Archivo JSON de poses:")
        layout.prop(self, "json_file", text="")
        layout.label(text="Pose dentro del archivo:")
        layout.prop(self, "pose_index", text="")
        layout.separator()
        layout.prop(self, "duration", text="Frames")
        layout.prop(self, "interp_type", text="")
        box = layout.box()
        box.prop(self, "manual_start")
        if self.manual_start:
            row = box.row()
            row.prop(self, "frame_abs_start")
            if seg is not None:
                row.label(text=f"(rango: {seg.frame_start} -> {seg.frame_end})")

    def execute(self, context):
        if self.json_file == "NONE":
            self.report({"WARNING"}, "No hay archivos JSON en la carpeta de poses")
            return {"CANCELLED"}
        segs = context.scene.rat1_segs
        seg = self._get_seg(context)
        if seg is None:
            self.report({"WARNING"}, "Segmento invalido")
            return {"CANCELLED"}
        jf = _json_file_from_index(self, context)
        idx = int(self.pose_index)
        fp = os.path.join(bpy.path.abspath(segs.poses_dir), jf)
        poses = load_json_poses(fp)
        name = poses[idx].get("label", "?") if poses and idx < len(poses) else "?"

        item = seg.action_poses.add()
        item.pose_name = name
        item.json_file = jf
        item.pose_index = idx
        item.duration = self.duration
        item.interp_type = self.interp_type
        item.manual_start = self.manual_start

        rec = get_pose_record(segs.poses_dir, jf, idx)
        if rec:
            px, py, pz, rx, ry, rz = get_root_transform_from_record(rec)
            item.pos_x, item.pos_y, item.pos_z = px, py, pz
            item.rot_x, item.rot_y, item.rot_z = rx, ry, rz

        if self.manual_start:
            prev_poses = list(seg.action_poses)[:-1]
            min_allowed = seg.frame_start
            if prev_poses:
                prev_starts = resolve_pose_start_frames(prev_poses, seg.frame_start)
                min_allowed = prev_starts[-1] + max(1, int(prev_poses[-1].duration))
            if self.frame_abs_start < min_allowed:
                self.report({"WARNING"},
                    f"Frame de inicio {self.frame_abs_start} invade la pose anterior "
                    f"(termina en {min_allowed - 1}); se usa apilado automatico.")
                item.manual_start = False
            else:
                item.frame_abs_start = self.frame_abs_start

        seg.action_poses_idx = len(seg.action_poses) - 1
        total, new_end = _sync_seg_interval(seg, segs.segments)
        self.report({"INFO"}, f"Pose agregada: '{name}' [{jf}] | intervalo: [{seg.frame_start}->{new_end}] ({total}f)")
        return {"FINISHED"}


class RAT1SEG_OT_RemoveActionPoseSeg(Operator):
    bl_idname = "rat1seg.remove_action_pose_seg"
    bl_label = "Eliminar pose del segmento"
    bl_options = {"REGISTER", "UNDO"}
    item_idx: IntProperty(default=-1)
    pose_idx: IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.rat1_segs
        idx = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)):
            return {"CANCELLED"}
        seg = segs.segments[idx]
        p_idx = self.pose_idx if self.pose_idx >= 0 else seg.action_poses_idx
        if 0 <= p_idx < len(seg.action_poses):
            seg.action_poses.remove(p_idx)
            seg.action_poses_idx = max(0, min(seg.action_poses_idx, len(seg.action_poses) - 1))
            _sync_seg_interval(seg, segs.segments)
        return {"FINISHED"}


class RAT1SEG_OT_MoveActionPoseSeg(Operator):
    bl_idname = "rat1seg.move_action_pose_seg"
    bl_label = "Mover pose dentro del segmento"
    bl_options = {"REGISTER", "UNDO"}
    item_idx: IntProperty(default=-1)
    direction: EnumProperty(items=[("UP", "Arriba", ""), ("DOWN", "Abajo", "")])

    def execute(self, context):
        segs = context.scene.rat1_segs
        idx = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)):
            return {"CANCELLED"}
        seg = segs.segments[idx]
        p_idx = seg.action_poses_idx
        n = len(seg.action_poses)
        if self.direction == "UP" and p_idx > 0:
            seg.action_poses.move(p_idx, p_idx - 1)
            seg.action_poses_idx = p_idx - 1
        elif self.direction == "DOWN" and p_idx < n - 1:
            seg.action_poses.move(p_idx, p_idx + 1)
            seg.action_poses_idx = p_idx + 1
        _sync_seg_interval(seg, segs.segments)
        return {"FINISHED"}


class RAT1SEG_OT_EditActionPoseSeg(Operator):
    bl_idname = "rat1seg.edit_action_pose_seg"
    bl_label = "Editar pose del segmento"
    bl_description = "Edita la duracion/interpolacion/frame de inicio de esta pose"
    bl_options = {"REGISTER", "UNDO"}
    item_idx: IntProperty(default=-1)
    pose_idx: IntProperty(default=-1)

    duration: IntProperty(name="Duracion (frames)", default=20, min=2, max=9999)
    interp_type: EnumProperty(name="Interpolacion", items=INTERP_TYPE_ITEMS, default="SMOOTH")
    manual_start: BoolProperty(name="Elegir frame de inicio", default=False)
    frame_abs_start: IntProperty(name="Frame de inicio", default=0, min=0)

    def _get(self, context):
        segs = context.scene.rat1_segs
        idx = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)):
            return None, None
        seg = segs.segments[idx]
        p_idx = self.pose_idx if self.pose_idx >= 0 else seg.action_poses_idx
        if not (0 <= p_idx < len(seg.action_poses)):
            return seg, None
        return seg, seg.action_poses[p_idx]

    def invoke(self, context, event):
        seg, slot = self._get(context)
        if slot is not None:
            self.duration = slot.duration
            self.interp_type = slot.interp_type
            self.manual_start = slot.manual_start
            self.frame_abs_start = slot.frame_abs_start
        return context.window_manager.invoke_props_dialog(self, width=380)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "duration")
        layout.prop(self, "interp_type", text="")
        layout.prop(self, "manual_start")
        if self.manual_start:
            layout.prop(self, "frame_abs_start")

    def execute(self, context):
        seg, slot = self._get(context)
        if slot is None:
            self.report({"WARNING"}, "Pose invalida")
            return {"CANCELLED"}
        slot.duration = self.duration
        slot.interp_type = self.interp_type
        slot.manual_start = self.manual_start
        slot.frame_abs_start = self.frame_abs_start
        _sync_seg_interval(seg, context.scene.rat1_segs.segments)
        return {"FINISHED"}


# =============================================================================
# EXTRAER POSE RAPIDA: captura la pose actual del armature -> .json
# =============================================================================

class RAT1SEG_OT_QuickPoseExtract(Operator):
    bl_idname = "rat1seg.quick_pose_extract"
    bl_label = "Extraer pose actual"
    bl_description = (
        "Guarda la pose actual del armature body1_1 (en el frame de la "
        "timeline) como un nuevo archivo .json en la carpeta de poses"
    )
    bl_options = {"REGISTER", "UNDO"}

    label: StringProperty(name="Nombre de la pose", default="")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=380)

    def draw(self, context):
        self.layout.prop(self, "label")

    def execute(self, context):
        segs = context.scene.rat1_segs
        arm = _resolve_armature(segs, context.scene)
        if arm is None:
            self.report({"ERROR"}, "No se encontro el armature body1_1")
            return {"CANCELLED"}

        bones_data = {}
        for bone_name in BONES_LISTA_FULL:
            pb = arm.pose.bones.get(bone_name)
            if pb is None:
                continue
            if pb.rotation_mode != "XYZ":
                rot = pb.rotation_quaternion.to_euler("XYZ")
            else:
                rot = pb.rotation_euler
            bones_data[bone_name] = {
                "rotation_mode": "XYZ",
                "raw_rotation_euler_deg": {
                    "x": rot.x * 57.29577951308232,
                    "y": rot.y * 57.29577951308232,
                    "z": rot.z * 57.29577951308232,
                },
                "raw_location": {"x": pb.location.x, "y": pb.location.y, "z": pb.location.z},
                "raw_scale": {"x": pb.scale.x, "y": pb.scale.y, "z": pb.scale.z},
            }

        root = context.scene.objects.get(ROOT_NAME)
        root_data = {}
        if root is not None:
            root_data = {
                "root": {
                    "location": {"x": root.location.x, "y": root.location.y, "z": root.location.z},
                    "rotation_euler_deg": {
                        "x": root.rotation_euler.x * 57.29577951308232,
                        "y": root.rotation_euler.y * 57.29577951308232,
                        "z": root.rotation_euler.z * 57.29577951308232,
                    },
                }
            }

        label = self.label.strip() or f"pose_{context.scene.frame_current}"
        poses_dir = bpy.path.abspath(segs.poses_dir)
        os.makedirs(poses_dir, exist_ok=True)
        filename = f"{label}.json"
        filepath = os.path.join(poses_dir, filename)

        data = {"poses": [{"label": label, "bones": bones_data, **root_data}]}
        if os.path.isfile(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                if isinstance(existing, dict) and "poses" in existing:
                    existing["poses"].append(data["poses"][0])
                    data = existing
            except Exception:
                pass

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self.report({"INFO"}, f"Pose '{label}' guardada en {filename}")
        return {"FINISHED"}


# =============================================================================
# REPRODUCCION DE UN SEGMENTO
# =============================================================================

class RAT1SEG_OT_PlaySegment(Operator):
    bl_idname = "rat1seg.play_segment"
    bl_label = "Reproducir segmento"
    bl_options = {"REGISTER"}
    item_idx: IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.rat1_segs
        idx = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "No hay segmento seleccionado")
            return {"CANCELLED"}
        seg = segs.segments[idx]
        scene = context.scene
        scene.frame_start = seg.frame_start
        scene.frame_end = seg.frame_end
        scene.frame_set(seg.frame_start)
        if not context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
        return {"FINISHED"}


class RAT1SEG_OT_PauseSegment(Operator):
    bl_idname = "rat1seg.pause_segment"
    bl_label = "Pausar"
    bl_options = {"REGISTER"}

    def execute(self, context):
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
        return {"FINISHED"}


class RAT1SEG_OT_StopSegment(Operator):
    bl_idname = "rat1seg.stop_segment"
    bl_label = "Detener"
    bl_options = {"REGISTER"}

    def execute(self, context):
        segs = context.scene.rat1_segs
        idx = segs.active_index
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
        if 0 <= idx < len(segs.segments):
            context.scene.frame_set(segs.segments[idx].frame_start)
        return {"FINISHED"}


# =============================================================================
# GUARDAR / CARGAR CONFIGURACION DEL PASO 3
# =============================================================================

_SEG_SCALAR_ATTRS = (
    "label", "frame_start", "frame_end", "frame_start_planned", "frame_end_planned",
    "fps", "seg_action_name", "frame_mid", "pose_mid_file", "pose_mid_label",
    "interp_type", "interp_mid_to_end", "blend_in_frames", "blend_out_frames",
    "blend_strength", "enabled", "show_config", "single_coord_mode", "frame_end_auto",
) + tuple(BONE_FILTER_ATTRS)

_SLOT_ATTRS = (
    "json_file", "pose_index", "pose_label", "pose_name", "duration",
    "entry_ratio", "exit_ratio", "interp_type",
    "rot_x", "rot_y", "rot_z", "pos_x", "pos_y", "pos_z",
    "frame_abs_start", "manual_start",
)

# Atributos de Rat1OrganicFilters (seg.organic) a guardar/cargar. Igual
# que _SEG_SCALAR_ATTRS pero para el PointerProperty anidado -- no viaja
# solo con getattr(seg, attr) porque "organic" es un PropertyGroup, no un
# valor escalar.
_ORGANIC_ATTRS = (
    "enabled",
    "breathing_enabled", "breathing_amplitude", "breathing_speed", "breathing_phase",
    "head_sway_enabled", "head_sway_amplitude", "head_sway_speed", "head_sway_seed",
    "weight_shift_enabled", "weight_shift_amplitude", "weight_shift_speed",
    "root_noise_enabled", "root_noise_strength", "root_noise_frequency", "root_noise_seed",
    "secondary_motion_enabled", "secondary_motion_lag", "secondary_motion_damping",
    "smooth_curves_enabled", "smooth_passes", "smooth_factor",
    "micro_scale_enabled", "micro_scale_amplitude",
    "shoulder_noise_enabled", "shoulder_noise_amplitude", "shoulder_noise_speed", "shoulder_noise_seed",
)


class RAT1SEG_OT_SaveConfig(Operator):
    bl_idname = "rat1seg.save_config"
    bl_label = "Guardar Configuracion"
    bl_description = (
        "Guarda la sesion de trabajo COMPLETA (recorrido y ajustes del "
        "Paso 1+2, y la secuencia de segmentos del Paso 3: poses, "
        "interpolaciones, duraciones, bloqueador de bones) como archivo "
        ".json en la carpeta de configuraciones"
    )
    bl_options = {"REGISTER"}

    config_name: StringProperty(
        name="Nombre del archivo",
        default="mi_configuracion",
        description="Nombre del archivo de configuracion a guardar (sin extension .json)",
    )

    def invoke(self, context, event):
        self.config_name = context.scene.rat1_segs.config_name or "mi_configuracion"
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        pc = context.scene.rat1_path
        segs = context.scene.rat1_segs
        layout.label(text="Nombre del archivo de configuracion:", icon="FILE_BLANK")
        layout.prop(self, "config_name", text="")
        layout.separator()
        out_dir = bpy.path.abspath(segs.config_dir)
        _FORBIDDEN = set('/\\:*?"<>|')
        safe = "".join(c if c not in _FORBIDDEN else "_" for c in self.config_name).strip()
        fname = f"{safe or 'configuracion'}.json"
        layout.label(text=f"  -> {os.path.join(out_dir, fname)}", icon="INFO")
        layout.separator()
        layout.label(text="Se guardara:", icon="CHECKMARK")
        layout.label(text=f"  - Paso 1+2: {len(pc.path_points)} punto(s) de recorrido, slots, frames")
        n_segs = len(segs.segments)
        n_poses = sum(len(s.action_poses) for s in segs.segments)
        layout.label(text=f"  - Paso 3: {n_segs} segmento(s), {n_poses} pose(s) de accion en total")
        layout.label(text="  - Interpolaciones, duraciones y Bloqueador de bones por segmento")
        layout.label(text="  - Filtros organicos por segmento (respiracion, sway, noise, etc.)")

    def execute(self, context):
        pc = context.scene.rat1_path
        segs = context.scene.rat1_segs

        _FORBIDDEN = set('/\\:*?"<>|')
        safe = "".join(c if c not in _FORBIDDEN else "_" for c in self.config_name).strip()
        if not safe:
            safe = "configuracion"
        filename = f"{safe}.json"

        segs.config_name = self.config_name

        out_dir = bpy.path.abspath(segs.config_dir)
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            self.report({"ERROR"}, f"No se pudo crear la carpeta: {e}")
            return {"CANCELLED"}

        filepath = os.path.join(out_dir, filename)
        from .config_ops import _serialize_path
        data = {
            "personaje": "rat_1",
            "timestamp": datetime.datetime.now().isoformat(),
            # ── Paso 1+2 (recorrido, slots, estilos de caminata) ──────────
            "path_recorder": _serialize_path(pc),
            # ── Paso 3 (segmentos) ────────────────────────────────────────
            "armature_name": segs.armature_name,
            "poses_dir": segs.poses_dir,
            "segments": [],
        }
        for seg in segs.segments:
            s = {attr: getattr(seg, attr) for attr in _SEG_SCALAR_ATTRS}
            s["action_poses"] = [
                {attr: getattr(slot, attr) for attr in _SLOT_ATTRS} for slot in seg.action_poses
            ]
            s["organic"] = {attr: getattr(seg.organic, attr) for attr in _ORGANIC_ATTRS}
            s["bone_blocks"] = [
                {
                    "bone_key": entry.bone_key,
                    "intervals": [
                        {"frame_start": iv.frame_start, "frame_end": iv.frame_end, "enabled": iv.enabled}
                        for iv in entry.intervals
                    ],
                }
                for entry in seg.bone_blocks
            ]
            data["segments"].append(s)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.report({"ERROR"}, f"Error al escribir el archivo: {e}")
            return {"CANCELLED"}

        n_segs = len(segs.segments)
        self.report({"INFO"},
            f"Configuracion guardada: {filename}  "
            f"({len(pc.path_points)} punto(s) de recorrido, {n_segs} segmento(s))  ->  {filepath}")
        return {"FINISHED"}


class RAT1SEG_OT_LoadConfig(Operator):
    bl_idname = "rat1seg.load_config"
    bl_label = "Importar Configuracion"
    bl_description = (
        "Carga una sesion de trabajo completa desde un .json de la carpeta "
        "de configuraciones. Restaura el recorrido y ajustes del Paso 1+2 "
        "(si el archivo los tiene) y la secuencia de segmentos del Paso 3: "
        "poses, interpolaciones y Bloqueador de bones"
    )
    bl_options = {"REGISTER", "UNDO"}
    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        start = bpy.path.abspath(context.scene.rat1_segs.config_dir)
        if os.path.isdir(start):
            self.filepath = start + os.sep
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        path = bpy.path.abspath(self.filepath)
        if not os.path.isfile(path):
            self.report({"ERROR"}, f"No se encontro {path}")
            return {"CANCELLED"}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "segments" not in data:
            self.report({"WARNING"},
                "El archivo no parece una configuracion del Paso 3 de rat_1 "
                "(falta 'segments'). Se intentara importar igual.")

        # ── Paso 1+2 (recorrido, slots, estilos de caminata): solo si el
        # archivo lo trae -- archivos viejos guardados antes de este cambio
        # (o generados con RAT1ST_OT_SaveConfig, "solo recorrido") pueden no
        # tenerlo, en cuyo caso se deja el recorrido actual tal cual.
        n_pts = None
        if "path_recorder" in data:
            from .config_ops import _deserialize_path
            pc = context.scene.rat1_path
            n_pts = _deserialize_path(pc, data["path_recorder"])

        # ── Paso 3 (segmentos) ────────────────────────────────────────────
        segs = context.scene.rat1_segs
        segs.segments.clear()
        segs.armature_name = data.get("armature_name", segs.armature_name)
        segs.poses_dir = data.get("poses_dir", segs.poses_dir)

        for s in data.get("segments", []):
            seg = segs.segments.add()
            for attr in _SEG_SCALAR_ATTRS:
                if attr in s:
                    try:
                        setattr(seg, attr, s[attr])
                    except Exception:
                        pass
            for slot_data in s.get("action_poses", []):
                slot = seg.action_poses.add()
                for attr in _SLOT_ATTRS:
                    if attr in slot_data:
                        try:
                            setattr(slot, attr, slot_data[attr])
                        except Exception:
                            pass
            for attr, val in s.get("organic", {}).items():
                if attr in _ORGANIC_ATTRS:
                    try:
                        setattr(seg.organic, attr, val)
                    except Exception:
                        pass
            for bb in s.get("bone_blocks", []):
                entry = seg.bone_blocks.add()
                entry.bone_key = bb.get("bone_key", "")
                for iv_data in bb.get("intervals", []):
                    iv = entry.intervals.add()
                    iv.frame_start = iv_data.get("frame_start", 0)
                    iv.frame_end = iv_data.get("frame_end", 0)
                    iv.enabled = iv_data.get("enabled", True)

        segs.active_index = 0
        n_segs = len(segs.segments)
        ts = data.get("timestamp", "")[:19].replace("T", " ")
        pts_txt = f"{n_pts} punto(s) de recorrido, " if n_pts is not None else ""
        self.report({"INFO"},
            f"Configuracion cargada: {os.path.basename(path)}  {ts}  "
            f"({pts_txt}{n_segs} segmento(s))")
        return {"FINISHED"}


class RAT1SEG_OT_OpenConfigFolder(Operator):
    bl_idname = "rat1seg.open_config_folder"
    bl_label = "Abrir carpeta configuraciones"
    bl_description = "Abre la carpeta de configuraciones del Paso 3 en el explorador de archivos"

    def execute(self, context):
        open_folder(bpy.path.abspath(context.scene.rat1_segs.config_dir))
        return {"FINISHED"}


# =============================================================================
# UILIST
# =============================================================================

class RAT1SEG_UL_Segments(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "enabled", text="")
        row.label(text=f"[{index+1}] {item.label}", icon="ANIM")
        row.label(text=f"{item.frame_start}->{item.frame_end}")
        row.label(text=f"{len(item.action_poses)} poses", icon="POSE_HLT")


classes = (
    RAT1SEG_OT_Add,
    RAT1SEG_OT_AutoSplitFromConfig,
    RAT1SEG_OT_Remove,
    RAT1SEG_OT_Move,
    RAT1SEG_OT_Duplicate,
    RAT1SEG_OT_ToggleEnabled,
    RAT1SEG_OT_AddBoneInterval,
    RAT1SEG_OT_RemoveBoneInterval,
    RAT1SEG_OT_SetFrameStart,
    RAT1SEG_OT_SetFrameMid,
    RAT1SEG_OT_SetFrameEnd,
    RAT1SEG_OT_PickPoseMid,
    RAT1SEG_OT_AddActionPoseSeg,
    RAT1SEG_OT_RemoveActionPoseSeg,
    RAT1SEG_OT_MoveActionPoseSeg,
    RAT1SEG_OT_EditActionPoseSeg,
    RAT1SEG_OT_QuickPoseExtract,
    RAT1SEG_OT_PlaySegment,
    RAT1SEG_OT_PauseSegment,
    RAT1SEG_OT_StopSegment,
    RAT1SEG_OT_Apply,
    RAT1SEG_OT_ConcatenateAll,
    RAT1SEG_OT_SaveConfig,
    RAT1SEG_OT_LoadConfig,
    RAT1SEG_OT_OpenConfigFolder,
    RAT1SEG_UL_Segments,
)


def register_segments():
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
        bpy.utils.register_class(cls)


def unregister_segments():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
