# -*- coding: utf-8 -*-
"""
operators_anim.py — Guard Ribbit 7 Animation Studio v1.0
Operadores principales: Organic filters, CONCATENAR, ExportAnimation,
ImportAnimation, ExtractPose.
"""
import bpy, json, os, math, random
from datetime import datetime
from bpy.types import Operator
from bpy.props import StringProperty
from mathutils import Euler, Vector
from .constants import BONES_LISTA, BONES_LISTA_FULL, _BONE_DEFAULT, SECONDARY_ARMATURES
from .interpolation import apply_interp
from .pose_utils import (
    load_json_poses, get_pose_record, pose_record_to_full_dict,
    _lerp, build_segment_frames, invalidate_enum_cache,
)
from .properties import load_historia_json, get_key_points
from .pose_utils import get_orientacion_inicial


def _noise_at(frame, freq, seed, dim=0):
    """Ruido procesal deterministico (sin-hash sin bpy.app.driver_namespace)."""
    v = math.sin(frame * freq * 1.3 + seed * 7.3 + dim * 3.7)
    v += math.sin(frame * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5
    v += math.sin(frame * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25
    return v / 1.75   # rango aprox. [-1, 1]

def _gaussian_smooth(values, factor):
    """Suavizado gaussiano de una lista de valores con factor [0,1]."""
    n = len(values)
    if n < 3:
        return values[:]
    out = values[:]
    w   = [0.25, 0.5, 0.25]
    for i in range(1, n - 1):
        out[i] = values[i - 1] * w[0] + values[i] * w[1] + values[i + 1] * w[2]
        out[i] = values[i] * (1 - factor) + out[i] * factor
    return out

def _apply_organic_filters(context, armature, start_frame, end_frame, org):
    """
    Aplica filtros organicos sobre las fcurves ya generadas.
    Lee los valores de los keyframes existentes, les suma las micro-variaciones
    y escribe los valores modificados de vuelta a los mismos keyframes.
    """
    scene = context.scene
    frames = list(range(start_frame, end_frame + 1))
    n = len(frames)
    if n < 3:
        return

    # ── FILTRO: suavizado de fcurves ──
    if org.smooth_curves_enabled and armature.animation_data and armature.animation_data.action:
        action = armature.animation_data.action
        for fc in action.fcurves:
            kps = sorted(fc.keyframe_points, key=lambda k: k.co.x)
            vals = [k.co.y for k in kps]
            for _ in range(org.smooth_passes):
                vals = _gaussian_smooth(vals, org.smooth_factor)
            for k, v in zip(kps, vals):
                k.co.y = v
            fc.update()

    # ── Funciones auxiliares para modificar pose bones por frame ──
    def _mod_bone_rot(bone_name, axis, deltas):
        """Suma deltas[frame_idx] al rotation_euler[axis] del bone ya keyframeado."""
        if not armature.animation_data or not armature.animation_data.action:
            return
        dp   = f'pose.bones["{bone_name}"].rotation_euler'
        fc   = armature.animation_data.action.fcurves.find(dp, index=axis)
        if fc is None:
            return
        kps = sorted(fc.keyframe_points, key=lambda k: k.co.x)
        # Construir mapa frame->kp para los frames en rango
        kmap = {int(k.co.x): k for k in kps if start_frame <= int(k.co.x) <= end_frame}
        for i, f in enumerate(frames):
            if f in kmap:
                kmap[f].co.y += deltas[i]
        fc.update()

    def _mod_bone_loc(bone_name, axis, deltas):
        if not armature.animation_data or not armature.animation_data.action:
            return
        dp = f'pose.bones["{bone_name}"].location'
        fc = armature.animation_data.action.fcurves.find(dp, index=axis)
        if fc is None:
            return
        kps  = sorted(fc.keyframe_points, key=lambda k: k.co.x)
        kmap = {int(k.co.x): k for k in kps if start_frame <= int(k.co.x) <= end_frame}
        for i, f in enumerate(frames):
            if f in kmap:
                kmap[f].co.y += deltas[i]
        fc.update()

    def _mod_bone_scale(bone_name, axis, deltas):
        if not armature.animation_data or not armature.animation_data.action:
            return
        dp = f'pose.bones["{bone_name}"].scale'
        fc = armature.animation_data.action.fcurves.find(dp, index=axis)
        if fc is None:
            return
        kps  = sorted(fc.keyframe_points, key=lambda k: k.co.x)
        kmap = {int(k.co.x): k for k in kps if start_frame <= int(k.co.x) <= end_frame}
        for i, f in enumerate(frames):
            if f in kmap:
                kmap[f].co.y += deltas[i]
        fc.update()

    # ── FILTRO: respiracion ──
    if org.breathing_enabled:
        amp   = org.breathing_amplitude
        speed = org.breathing_speed
        phase = org.breathing_phase
        deltas_x = [amp * math.sin(f * speed * 2 * math.pi + phase) for f in frames]
        deltas_z = [amp * 0.4 * math.sin(f * speed * 2 * math.pi + phase + 1.2) for f in frames]
        for bone in ("body_guard_ribbit_7",):
            _mod_bone_rot(bone, 0, deltas_x)   # X
            _mod_bone_rot(bone, 2, deltas_z)   # Z

    # ── FILTRO: micro-movimiento de cabeza ──
    if org.head_sway_enabled:
        amp   = org.head_sway_amplitude
        speed = org.head_sway_speed
        seed  = org.head_sway_seed
        for axis in range(3):
            deltas = [amp * _noise_at(f, speed, seed, axis) for f in frames]
            for bone in ("body_guard_ribbit_7",):
                _mod_bone_rot(bone, axis, deltas)

    # ── FILTRO: desplazamiento de peso (hips lateral) ──
    if org.weight_shift_enabled:
        amp   = org.weight_shift_amplitude
        speed = org.weight_shift_speed
        deltas_loc_x = [amp * math.sin(f * speed * 2 * math.pi) for f in frames]
        deltas_rot_z = [amp * 0.8 * math.cos(f * speed * 2 * math.pi) for f in frames]
        _mod_bone_loc("main_guard_ribbit_7", 0, deltas_loc_x)
        _mod_bone_rot("main_guard_ribbit_7", 2, deltas_rot_z)

    # ── FILTRO: noise en hombros ──
    if org.shoulder_noise_enabled:
        amp   = org.shoulder_noise_amplitude
        speed = org.shoulder_noise_speed
        seed  = org.shoulder_noise_seed
        for axis in range(3):
            for bone, s_off in (("right_arm_guard_ribbit_7", 0), ("left_arm_guard_ribbit_7", 17)):
                deltas = [amp * _noise_at(f, speed, seed + s_off, axis) for f in frames]
                _mod_bone_rot(bone, axis, deltas)

    # ── FILTRO: micro-escala organica ──
    if org.micro_scale_enabled:
        amp   = org.micro_scale_amplitude
        speed = org.breathing_speed  # sincronizado con respiracion
        phase = org.breathing_phase
        deltas_s = [amp * math.sin(f * speed * 2 * math.pi + phase) for f in frames]
        _mod_bone_scale("body_guard_ribbit_7", 2, deltas_s)   # escala Z del body

    # ── FILTRO: secondary motion brazos (retardo de codos) ──
    if org.secondary_motion_enabled:
        lag     = int(round(org.secondary_motion_lag))
        damping = org.secondary_motion_damping
        if armature.animation_data and armature.animation_data.action:
            action = armature.animation_data.action
            for bone in ("right_arm_guard_ribbit_7", "left_arm_guard_ribbit_7"):
                dp = f'pose.bones["{bone}"].rotation_euler'
                for axis in range(3):
                    fc = action.fcurves.find(dp, index=axis)
                    if fc is None:
                        continue
                    kps  = sorted(fc.keyframe_points, key=lambda k: k.co.x)
                    kmap = {int(k.co.x): k for k in kps}
                    vals = [kmap[f].co.y if f in kmap else 0.0 for f in frames]
                    # Aplicar retardo: el elbow sigue al UpArm con lag frames de retraso
                    delayed = [0.0] * n
                    for i in range(n):
                        src_i = max(0, i - lag)
                        delayed[i] = vals[src_i] * (1 - damping) + vals[i] * damping
                    # Blend: 30% delayed + 70% original para no romper la pose base
                    for i, f in enumerate(frames):
                        if f in kmap:
                            kmap[f].co.y = vals[i] * 0.7 + delayed[i] * 0.3
                    fc.update()

    # ── FILTRO: oscilacion de cola ──
    if org.tail_wag_enabled:
        amp   = org.tail_wag_amplitude      # max 0.524 rad = 30 grados
        speed = org.tail_wag_speed
        phase = org.tail_wag_phase
        lag   = org.tail_wag_lag * (1.0 / max(speed, 0.001))  # desfase en frames

        # guard_ribbit_7 no tiene cola — se aplica a spear_guard_ribbit_7 (oscilacion de lanza).
        # El rango queda clampeado a [-amp, +amp] = [-30°, +30°] en Z.
        tail_bones = [
            ("spear_guard_ribbit_7", 0.0),   # lanza — unico bone disponible
        ]

        # Los bones de la cola pueden no tener fcurves propias en la accion
        # (el usuario no los animo en las poses). Se crean aqui directamente
        # en lugar de usar _mod_bone_rot que silenciosamente ignora bones sin fcurve.
        if armature.animation_data and armature.animation_data.action:
            action = armature.animation_data.action
            for bone_name, bone_lag in tail_bones:
                dp = f'pose.bones["{bone_name}"].rotation_euler'
                # Obtener o crear la fcurve del eje Z (index=2)
                fc = action.fcurves.find(dp, index=2)
                if fc is None:
                    fc = action.fcurves.new(dp, index=2, action_group=bone_name)

                # Eliminar keyframes previos del rango para no acumular.
                # Blender invalida los punteros al eliminar; hay que recorrer
                # en reversa por indice para evitar el RuntimeError.
                indices_to_remove = [
                    i for i, kp in enumerate(fc.keyframe_points)
                    if start_frame <= int(kp.co.x) <= end_frame
                ]
                for i in reversed(indices_to_remove):
                    fc.keyframe_points.remove(fc.keyframe_points[i])

                # Insertar un keyframe por frame con el valor sinusoidal
                for i, f in enumerate(frames):
                    val = amp * math.sin(
                        f * speed * 2 * math.pi + phase
                        - bone_lag * speed * 2 * math.pi
                    )
                    val = max(-amp, min(amp, val))   # clamp a ±30°
                    fc.keyframe_points.insert(frame=f, value=val,
                                              options={"FAST"})

                # Interpolacion suave y actualizar
                for kp in fc.keyframe_points:
                    if start_frame <= int(kp.co.x) <= end_frame:
                        kp.interpolation = "BEZIER"
                        kp.easing = "AUTO"
                fc.update()

    # ── FILTRO: noise en posicion del root ──
    if org.root_noise_enabled:
        root_obj = scene.objects.get("guard_ribbit_7")
        if root_obj and root_obj.animation_data and root_obj.animation_data.action:
            root_action = root_obj.animation_data.action
            strength = org.root_noise_strength
            freq     = org.root_noise_frequency
            seed     = org.root_noise_seed
            for axis in range(3):
                fc = root_action.fcurves.find("location", index=axis)
                if fc is None:
                    continue
                kps  = sorted(fc.keyframe_points, key=lambda k: k.co.x)
                kmap = {int(k.co.x): k for k in kps}
                for i, f in enumerate(frames):
                    if f in kmap:
                        kmap[f].co.y += strength * _noise_at(f, freq, seed, axis)
                fc.update()


# =============================================================================
# CONCATENAR (incluye pos XYZ root + filtros organicos)
# =============================================================================

class GRB7ST_OT_Concatenate(Operator):
    bl_idname    = "grb7st.concatenate"
    bl_label     = "CONCATENAR"
    bl_description = "Genera la animacion interpolando las poses en la timeline"
    bl_options   = {"REGISTER", "UNDO"}

    def execute(self, context):
        st    = context.scene.grb7st
        scene = context.scene

        start_frame = st.start_frame
        entry_ratio = st.entry_ratio
        exit_ratio  = st.exit_ratio

        if not st.armature_name:
            self.report({"ERROR"}, "Selecciona el armature de Jerry primero")
            return {"CANCELLED"}
        armature = scene.objects.get(st.armature_name)
        if not armature or armature.type != "ARMATURE":
            self.report({"ERROR"}, f"main_guard_ribbit_7 '{st.armature_name}' no valido")
            return {"CANCELLED"}
        if not st.pose_start_file:
            self.report({"ERROR"}, "Selecciona la pose de INICIO")
            return {"CANCELLED"}
        if not st.pose_end_file:
            self.report({"ERROR"}, "Selecciona la pose de FIN")
            return {"CANCELLED"}

        rec_start = get_pose_record(st.poses_dir, st.pose_start_file, st.pose_start_idx)
        rec_end   = get_pose_record(st.poses_dir, st.pose_end_file,   st.pose_end_idx)
        if rec_start is None:
            self.report({"ERROR"}, "No se pudo cargar la pose de INICIO del JSON")
            return {"CANCELLED"}
        if rec_end is None:
            self.report({"ERROR"}, "No se pudo cargar la pose de FIN del JSON")
            return {"CANCELLED"}

        d_start = pose_record_to_full_dict(rec_start)
        d_end   = pose_record_to_full_dict(rec_end)

        # Rotaciones del root por pose (grados -> radianes)
        arm_rot_start = (math.radians(st.pose_start_rot_x), math.radians(st.pose_start_rot_y), math.radians(st.pose_start_rot_z))
        arm_rot_end   = (math.radians(st.pose_end_rot_x),   math.radians(st.pose_end_rot_y),   math.radians(st.pose_end_rot_z))
        # Posiciones XYZ del root por pose
        arm_pos_start = (st.pose_start_pos_x, st.pose_start_pos_y, st.pose_start_pos_z)
        arm_pos_end   = (st.pose_end_pos_x,   st.pose_end_pos_y,   st.pose_end_pos_z)

        action_items = list(st.action_poses)
        segments     = []   # (d_s, d_a, d_e, n_frames, interp_type)
        seg_arm_rots = []   # (rot_s, rot_a, rot_e, n_frames, interp_type)
        seg_arm_pos  = []   # (pos_s, pos_a, pos_e, n_frames, interp_type)

        dur_ini = st.pose_start_duration
        if dur_ini > 0:
            segments.append((d_start, d_start, d_start, dur_ini, st.pose_start_interp))
            seg_arm_rots.append((arm_rot_start, arm_rot_start, arm_rot_start, dur_ini, st.pose_start_interp))
            seg_arm_pos.append((arm_pos_start,  arm_pos_start,  arm_pos_start,  dur_ini, st.pose_start_interp))

        if not action_items:
            segments.append((d_start, d_start, d_end, 30, "SMOOTH"))
            seg_arm_rots.append((arm_rot_start, arm_rot_start, arm_rot_end, 30, "SMOOTH"))
            seg_arm_pos.append((arm_pos_start,  arm_pos_start,  arm_pos_end,  30, "SMOOTH"))
        else:
            for i, item in enumerate(action_items):
                rec_act = get_pose_record(st.poses_dir, item.json_file, item.pose_index)
                if rec_act is None:
                    self.report({"WARNING"}, f"Pose '{item.pose_name}' no encontrada, omitida")
                    continue
                d_act       = pose_record_to_full_dict(rec_act)
                arm_rot_act = (math.radians(item.rot_x), math.radians(item.rot_y), math.radians(item.rot_z))
                arm_pos_act = (item.pos_x, item.pos_y, item.pos_z)

                if i == 0:
                    d_seg_s       = d_start
                    arm_rot_seg_s = arm_rot_start
                    arm_pos_seg_s = arm_pos_start
                else:
                    prev          = action_items[i-1]
                    rec_p         = get_pose_record(st.poses_dir, prev.json_file, prev.pose_index)
                    d_seg_s       = pose_record_to_full_dict(rec_p) if rec_p else d_start
                    arm_rot_seg_s = (math.radians(prev.rot_x), math.radians(prev.rot_y), math.radians(prev.rot_z))
                    arm_pos_seg_s = (prev.pos_x, prev.pos_y, prev.pos_z)

                if i == len(action_items) - 1:
                    d_seg_e       = d_end
                    arm_rot_seg_e = arm_rot_end
                    arm_pos_seg_e = arm_pos_end
                else:
                    nxt           = action_items[i+1]
                    rec_n         = get_pose_record(st.poses_dir, nxt.json_file, nxt.pose_index)
                    d_seg_e       = pose_record_to_full_dict(rec_n) if rec_n else d_end
                    arm_rot_seg_e = (math.radians(nxt.rot_x), math.radians(nxt.rot_y), math.radians(nxt.rot_z))
                    arm_pos_seg_e = (nxt.pos_x, nxt.pos_y, nxt.pos_z)

                seg_interp = item.interp_type
                segments.append((d_seg_s, d_act, d_seg_e, item.duration, seg_interp))
                seg_arm_rots.append((arm_rot_seg_s, arm_rot_act, arm_rot_seg_e, item.duration, seg_interp))
                seg_arm_pos.append((arm_pos_seg_s,  arm_pos_act, arm_pos_seg_e,  item.duration, seg_interp))

        dur_fin = st.pose_end_duration
        if dur_fin > 0:
            segments.append((d_end, d_end, d_end, dur_fin, st.pose_end_interp))
            seg_arm_rots.append((arm_rot_end, arm_rot_end, arm_rot_end, dur_fin, st.pose_end_interp))
            seg_arm_pos.append((arm_pos_end,  arm_pos_end,  arm_pos_end,  dur_fin, st.pose_end_interp))

        if not segments:
            self.report({"ERROR"}, "No hay segmentos validos para concatenar")
            return {"CANCELLED"}

        context.view_layer.objects.active = armature
        if armature.mode != "POSE":
            bpy.ops.object.mode_set(mode="POSE")
        for pb in armature.pose.bones:
            pb.rotation_mode = "XYZ"
        armature.rotation_mode = "XYZ"

        if armature.animation_data and armature.animation_data.action:
            old_action = armature.animation_data.action
            armature.animation_data.action = None
            bpy.data.actions.remove(old_action)
        if not armature.animation_data:
            armature.animation_data_create()

        # ── Limpiar keyframes previos del root (guard_ribbit_7 Empty) ──
        # Sin esto, keyframes viejos en frame 1 causan interpolacion
        # desde frame 1 hasta start_frame antes de que empiece la animacion.
        _root_cleanup = bpy.data.objects.get("guard_ribbit_7")
        if _root_cleanup and _root_cleanup.animation_data:
            if _root_cleanup.animation_data.action:
                _old_root = _root_cleanup.animation_data.action
                _root_cleanup.animation_data.action = None
                bpy.data.actions.remove(_old_root)
            # Tambien limpiar NLA tracks del root para no acumular strips
            for _trk in list(_root_cleanup.animation_data.nla_tracks):
                _root_cleanup.animation_data.nla_tracks.remove(_trk)
        # Limpiar NLA tracks del armature igualmente
        if armature.animation_data:
            for _trk in list(armature.animation_data.nla_tracks):
                armature.animation_data.nla_tracks.remove(_trk)
        # ── Limpiar keyframes previos de los armatures secundarios (shield y spear) ──
        for _sec_name in SECONDARY_ARMATURES:
            _sec = bpy.data.objects.get(_sec_name)
            if _sec and _sec.animation_data:
                if _sec.animation_data.action:
                    _old_sec = _sec.animation_data.action
                    _sec.animation_data.action = None
                    bpy.data.actions.remove(_old_sec)
                for _trk in list(_sec.animation_data.nla_tracks):
                    _sec.animation_data.nla_tracks.remove(_trk)

        # Construir waypoints de BONES: (frame_abs, full_pose_dict, interp_hacia_siguiente)
        # El interp_type de cada waypoint se aplica en el TRAMO que sale de ese waypoint
        # hacia el siguiente. Por eso cada waypoint lleva el tipo de curva que debe usar
        # para llegar al waypoint siguiente.
        waypoints = []
        waypoints.append((start_frame, d_start, segments[0][4] if segments else "SMOOTH"))

        arm_waypoints = []
        arm_waypoints.append((start_frame, arm_rot_start, seg_arm_rots[0][4] if seg_arm_rots else "SMOOTH"))

        pos_waypoints = []
        pos_waypoints.append((start_frame, arm_pos_start, seg_arm_pos[0][4] if seg_arm_pos else "SMOOTH"))

        cursor = start_frame
        for idx_seg, ((d_s, d_a, d_e, n_frames, seg_interp),
                      (ar_s, ar_a, ar_e, _, _arm_interp),
                      (ap_s, ap_a, ap_e, _, _pos_interp)) in \
                enumerate(zip(segments, seg_arm_rots, seg_arm_pos)):
            mid = cursor + n_frames // 2
            # El tramo que sale del waypoint medio usa el interp del segmento SIGUIENTE
            # (o pose_end_interp si es el último) para la transición de salida
            if idx_seg + 1 < len(segments):
                next_interp = segments[idx_seg + 1][4]
            else:
                next_interp = st.pose_end_interp
            waypoints.append((mid, d_a, next_interp))
            arm_waypoints.append((mid, ar_a, next_interp))
            pos_waypoints.append((mid, ap_a, next_interp))
            cursor += n_frames

        total_gen  = cursor - start_frame
        end_frame  = cursor - 1
        waypoints.append((end_frame, d_end, st.pose_end_interp))
        arm_waypoints.append((end_frame, arm_rot_end, st.pose_end_interp))
        pos_waypoints.append((end_frame, arm_pos_end, st.pose_end_interp))

        def _pose_at_frame(abs_f):
            for i in range(len(waypoints) - 1):
                f0, p0, itp = waypoints[i]
                f1, p1, _   = waypoints[i + 1]
                if abs_f <= f1 or i == len(waypoints) - 2:
                    span = f1 - f0
                    if span <= 0:
                        return p1
                    t = apply_interp(max(0.0, min(1.0, (abs_f - f0) / span)), itp)
                    result = {}
                    for bone in BONES_LISTA_FULL:
                        a = p0.get(bone, _BONE_DEFAULT)
                        b = p1.get(bone, _BONE_DEFAULT)
                        result[bone] = {
                            "rot":   _lerp(a["rot"],   b["rot"],   t),
                            "loc":   _lerp(a["loc"],   b["loc"],   t),
                            "scale": _lerp(a["scale"], b["scale"], t),
                        }
                    return result
            return {bone: d_end.get(bone, _BONE_DEFAULT) for bone in BONES_LISTA_FULL}

        def _arm_rot_at_frame(abs_f):
            for i in range(len(arm_waypoints) - 1):
                f0, r0, itp = arm_waypoints[i]
                f1, r1, _   = arm_waypoints[i + 1]
                if abs_f <= f1 or i == len(arm_waypoints) - 2:
                    span = f1 - f0
                    if span <= 0:
                        return r1
                    t = apply_interp(max(0.0, min(1.0, (abs_f - f0) / span)), itp)
                    return _lerp(r0, r1, t)
            return arm_rot_end

        def _arm_pos_at_frame(abs_f):
            """Interpola la posicion XYZ del root entre waypoints."""
            for i in range(len(pos_waypoints) - 1):
                f0, p0, itp = pos_waypoints[i]
                f1, p1, _   = pos_waypoints[i + 1]
                if abs_f <= f1 or i == len(pos_waypoints) - 2:
                    span = f1 - f0
                    if span <= 0:
                        return p1
                    t = apply_interp(max(0.0, min(1.0, (abs_f - f0) / span)), itp)
                    return _lerp(p0, p1, t)
            return arm_pos_end

        # Escribir keyframes — bones + rotacion + posicion del root
        for abs_f in range(start_frame, end_frame + 1):
            pose    = _pose_at_frame(abs_f)
            arm_rot = _arm_rot_at_frame(abs_f)
            arm_pos = _arm_pos_at_frame(abs_f)
            scene.frame_set(abs_f)
            # Bones del armature principal
            for bone_name, bdata in pose.items():
                pb = armature.pose.bones.get(bone_name)
                if pb:
                    pb.rotation_euler = Euler(bdata["rot"], "XYZ")
                    pb.location       = Vector(bdata["loc"])
                    pb.scale          = Vector(bdata["scale"])
                    pb.keyframe_insert(data_path="rotation_euler", frame=abs_f)
                    pb.keyframe_insert(data_path="location",       frame=abs_f)
                    pb.keyframe_insert(data_path="scale",          frame=abs_f)
            # Bones de los armatures secundarios (shield y spear)
            for sec_name in SECONDARY_ARMATURES:
                sec_obj = scene.objects.get(sec_name)
                if not sec_obj or sec_obj.type != "ARMATURE":
                    continue
                if not sec_obj.animation_data:
                    sec_obj.animation_data_create()
                for bone_name, bdata in pose.items():
                    pb = sec_obj.pose.bones.get(bone_name)
                    if pb:
                        pb.rotation_mode  = "XYZ"
                        pb.rotation_euler = Euler(bdata["rot"], "XYZ")
                        pb.location       = Vector(bdata["loc"])
                        pb.scale          = Vector(bdata["scale"])
                        pb.keyframe_insert(data_path="rotation_euler", frame=abs_f)
                        pb.keyframe_insert(data_path="location",       frame=abs_f)
                        pb.keyframe_insert(data_path="scale",          frame=abs_f)
            # Root object (guard_ribbit_7 / Empty) — rotacion Y posicion interpoladas
            root_obj = scene.objects.get("guard_ribbit_7") or armature
            root_obj.rotation_mode = "XYZ"
            root_obj.rotation_euler = Euler(arm_rot, "XYZ")
            root_obj.location       = Vector(arm_pos)
            root_obj.keyframe_insert(data_path="rotation_euler", frame=abs_f)
            root_obj.keyframe_insert(data_path="location",       frame=abs_f)

        abs_frame = end_frame + 1

        if armature.animation_data and armature.animation_data.action:
            for fc in armature.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "BEZIER"
                    kp.easing        = "AUTO"
        # Suavizado BEZIER para los armatures secundarios (shield y spear)
        for _sec_name in SECONDARY_ARMATURES:
            _sec = scene.objects.get(_sec_name)
            if _sec and _sec.animation_data and _sec.animation_data.action:
                for fc in _sec.animation_data.action.fcurves:
                    for kp in fc.keyframe_points:
                        kp.interpolation = "BEZIER"
                        kp.easing        = "AUTO"

        scene.frame_start = start_frame
        scene.frame_end   = abs_frame - 1
        scene.frame_set(start_frame)

        # ── Post-proceso: filtros de movimiento organico ──
        org = st.organic
        if org.enabled:
            _apply_organic_filters(context, armature, start_frame, end_frame, org)

        # ── Post-proceso: expresiones de ojos y parpadeo ──



        st.anim_generated   = True
        st.total_frames_gen = total_gen
        st.end_frame_gen    = abs_frame - 1
        st.status_msg = (
            f"OK  {total_gen} frames  [{start_frame} - {abs_frame-1}]  "
            f"ini={st.pose_start_duration}f({st.pose_start_interp})  "
            f"fin={st.pose_end_duration}f({st.pose_end_interp})  "
            f"entrada={entry_ratio:.0%}  salida={exit_ratio:.0%}"
            + ("  [filtros ON]" if org.enabled else "")
        )
        self.report({"INFO"}, st.status_msg)
        return {"FINISHED"}

class GRB7ST_OT_ExportAnimation(Operator):
    bl_idname    = "grb7st.export_animation"
    bl_label     = "Exportar .py"
    bl_description = "Exporta la animacion como slot_NNN_tipo.py compatible con el flujo jerry"
    bl_options   = {"REGISTER"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=540)

    def draw(self, context):
        layout = self.layout
        st = context.scene.grb7st

        box = layout.box()
        box.label(text="Identificacion del slot", icon="FILE_SCRIPT")
        col = box.column(align=True)
        col.prop(st, "export_slot_number", text="Numero de slot")
        col.prop(st, "export_type",        text="Tipo  (ej: arrodillarse)")
        col.prop(st, "export_desc",        text="Descripcion")

        box2 = layout.box()
        box2.label(text="Key point del recorrido (historia_guard_ribbit_7.json)", icon="TRACKER")
        box2.prop(st, "root_pos_key_point", text="KeyPoint")
        box2.label(text=f"  JSON: {os.path.basename(bpy.path.abspath(st.historia_json))}", icon="FILEBROWSER")

    def execute(self, context):
        st    = context.scene.grb7st
        scene = context.scene

        if not st.anim_generated:
            self.report({"ERROR"}, "Primero genera la animacion con CONCATENAR")
            return {"CANCELLED"}
        if not st.armature_name:
            self.report({"ERROR"}, "Selecciona el armature")
            return {"CANCELLED"}
        armature = scene.objects.get(st.armature_name)
        if not armature or armature.type != "ARMATURE":
            self.report({"ERROR"}, "main_guard_ribbit_7 no valido")
            return {"CANCELLED"}
        if not armature.animation_data or not armature.animation_data.action:
            self.report({"ERROR"}, "No hay accion de animacion en el armature")
            return {"CANCELLED"}

        # ── Leer historia_guard_ribbit_7.json para key_point y orientacion ──
        historia = load_historia_json(st.historia_json)
        kps      = get_key_points(historia)
        ori_rad  = get_orientacion_inicial(historia)   # (rx, ry, rz) en radianes
        ori_data = historia.get("configuracion", {}).get("orientacion_inicial", {})

        # Buscar el key_point seleccionado — usar root_pos_key_point (el dropdown
        # 'KeyPoint para Root' que el usuario elige en el panel de Configuracion).
        # selected_key_point es un IntProperty legacy que ya no se sincroniza con el UI.
        try:
            kp_idx_sel = int(st.root_pos_key_point)
        except (ValueError, TypeError):
            kp_idx_sel = 1
        kp_selected = next((k for k in kps if k.get("index") == kp_idx_sel), None)
        if kp_selected is None and kps:
            kp_selected = kps[0]

        start_f      = st.start_frame
        end_f        = st.end_frame_gen
        total_frames = st.total_frames_gen

        # Obtener coordenadas del anchor point (para calcular offsets relativos)
        anchor_x = anchor_y = anchor_z = 0.0
        if kp_selected:
            co = kp_selected.get("coordinates", {"x":0,"y":0,"z":0})
            anchor_x = co['x']
            anchor_y = co['y']
            anchor_z = co['z']

        # ── Capturar keyframes de rotacion desde la timeline ──
        bone_frames = {b: {} for b in BONES_LISTA_FULL}
        # Capturar la rotacion del armature por frame (orientacion por pose)
        arm_rot_frames = {}   # local_f -> (rx, ry, rz) en radianes
        # Capturar loc + rot del root (guard_ribbit_7 Empty) por frame
        root_obj_capture = scene.objects.get('guard_ribbit_7')
        root_keyframes   = {}   # local_f -> {'loc': (x,y,z), 'rot': (rx,ry,rz)}
        for abs_f in range(start_f, end_f + 1):
            scene.frame_set(abs_f)
            local_f = abs_f - start_f + 1
            for bn in BONES_LISTA_FULL:
                pb = armature.pose.bones.get(bn)
                if pb:
                    e = pb.rotation_euler
                    bone_frames[bn][local_f] = (round(e.x,6), round(e.y,6), round(e.z,6))
                else:
                    bone_frames[bn][local_f] = (0.0, 0.0, 0.0)
            # Rotacion del armature (object-level)
            ae = armature.rotation_euler
            arm_rot_frames[local_f] = (round(ae.x,6), round(ae.y,6), round(ae.z,6))
            # Loc + rot del root Empty (jerry) - guardar como OFFSET relativo al anchor
            if root_obj_capture:
                rl = root_obj_capture.location
                rr = root_obj_capture.rotation_euler
                # Calcular offset relativo al anchor point
                offset_x = round(rl.x - anchor_x, 6)
                offset_y = round(rl.y - anchor_y, 6)
                offset_z = round(rl.z - anchor_z, 6)
                root_keyframes[local_f] = {
                    'loc': (offset_x, offset_y, offset_z),
                    'rot': (round(rr.x,6), round(rr.y,6), round(rr.z,6)),
                }
        scene.frame_set(start_f)

        def frames_at(lf):
            return {b: bone_frames[b].get(lf, (0.0,0.0,0.0)) for b in BONES_LISTA_FULL}

        p_ini = frames_at(1)
        p_act = frames_at(max(1, total_frames // 2))
        p_fin = frames_at(total_frames)

        # ── Metadatos ──
        slot_num   = st.export_slot_number
        movement   = st.export_type.strip() or "custom"
        desc       = st.export_desc.strip()
        now        = datetime.now().strftime("%Y-%m-%d")
        fps_val    = st.fps
        dur_s      = round(total_frames / fps_val, 4)
        er         = round(st.entry_ratio, 2)
        xr         = round(st.exit_ratio,  2)
        anim_name  = f"jerry_{movement}"

        # Nombre de archivo: slot_NNN_tipo.py
        slot_str   = f"{slot_num:03d}"
        filename   = f"slot_{slot_str}_{movement}.py"

        # ── Serializar dicts de pose ──
        def _pose_lines(d, varname):
            lines = [f"{varname} = {{"]
            for k, v in d.items():
                lines.append(f"    {repr(k)}: {v},")
            lines.append("}")
            return "\n".join(lines)

        kf_lines = ["KEYFRAME_DATA = {"]
        for bn in BONES_LISTA_FULL:
            kf_lines.append(f"    {repr(bn)}: {{")
            for lf, v in sorted(bone_frames[bn].items()):
                kf_lines.append(f"        {lf}: {v},")
            kf_lines.append("    },")
        kf_lines.append("}")

        # ── Serializar rotaciones del armature por frame ──
        arm_rot_lines = ["ARMATURE_ROTATIONS = {"]
        for lf, v in sorted(arm_rot_frames.items()):
            arm_rot_lines.append(f"    {lf}: {v},")
        arm_rot_lines.append("}")

        # Serializar ROOT_KEYFRAMES (loc + rot del Empty guard_ribbit_7 por frame)
        root_kf_lines = ["ROOT_KEYFRAMES = {"]
        for lf, kf in sorted(root_keyframes.items()):
            root_kf_lines.append(
                f"    {lf}: {{'loc': {kf['loc']}, 'rot': {kf['rot']}}},"
            )
        root_kf_lines.append("}")

        # ── Embedded trajectory point ──
        if kp_selected:
            co = kp_selected.get("coordinates", {"x":0,"y":0,"z":0})
            tex = kp_selected.get("texture", "?")
            fi  = kp_selected.get("face_index", "?")
            kp_idx = kp_selected.get("index", 0)
            traj_block = (
                "EMBEDDED_TRAJECTORY_POINTS = [\n"
                "    {\n"
                f"        \"index\": {kp_idx},\n"
                f"        \"coordinates\": {{\"x\": {co['x']}, \"y\": {co['y']}, \"z\": {co['z']}}},\n"
                f"        \"texture\": \"{tex}\",\n"
                f"        \"face_index\": \"{fi}\"\n"
                "    },\n"
                "]\n"
            )
        else:
            traj_block = "EMBEDDED_TRAJECTORY_POINTS = []\n"

        # Rotacion del root: usar frame 1 capturado del Empty guard_ribbit_7 (real de timeline)
        # Fallback a orientacion_inicial del JSON si no hay datos capturados
        if root_keyframes:
            _rf1 = root_keyframes.get(1, root_keyframes[min(root_keyframes)])
            rx_real = round(math.degrees(_rf1['rot'][0]), 4)
            ry_real = round(math.degrees(_rf1['rot'][1]), 4)
            rz_real = round(math.degrees(_rf1['rot'][2]), 4)
        else:
            rx_real = ori_data.get('rotacion_x', 0.0)
            ry_real = ori_data.get('rotacion_y', 0.0)
            rz_real = ori_data.get('rotacion_z', 0.0)

        # ── Generar codigo del slot ──
        code = (
            "# -*- coding: utf-8 -*-\n"
            '"""\n'
            f"{filename}\n"
            f"Jerry - Slot {{{slot_str}}}\n\n"
            "GENERADO AUTOMATICAMENTE\n"
            f"Fecha de generacion: {now}\n\n"
            f"Tipo        : {movement}\n"
            f"Descripcion : {desc}\n"
            f"Duracion    : {total_frames} frames  ({dur_s} s @ {fps_val} fps)\n\n"
            "IMPORTANTE: Este archivo es una PLANTILLA. Los valores de SLOT_INDEX,\n"
            "START_FRAME, END_FRAME y ROOT_ROTATION_Z deben ser inyectados por el\n"
            "proceso orquestador antes de llamar a execute_animation().\n\n"
            "Constantes que el orquestador debe definir / sobreescribir:\n"
            "    SLOT_INDEX      = <int>\n"
            "    START_FRAME     = <int>\n"
            "    END_FRAME       = <int>\n"
            "    ROOT_ROTATION_Z = <float>   # en radianes\n"
            '"""\n\n'
            "import bpy\n"
            "import math\n\n"
            "# ============================================\n"
            "# CONFIGURACION DEL SLOT\n"
            "# (inyectadas por el orquestador)\n"
            "# ============================================\n\n"
            f"SLOT_INDEX   = {slot_num}   # type: int\n"
            f"START_FRAME  = {start_f}   # type: int\n"
            f"END_FRAME    = {end_f}   # type: int\n"
            f"TOTAL_FRAMES = {total_frames}   # duracion estandar del tipo\n"
            f"ROOT_ROTATION_X = {rx_real}\n"
            f"ROOT_ROTATION_Y = {ry_real}\n"
            f"ROOT_ROTATION_Z = {rz_real}   # type: float  (grados) - fuente: root jerry timeline\n\n"
            "# ============================================\n"
            "# FIN DE CONFIGURACION DEL SLOT\n"
            "# ============================================\n\n"
            "# ============================================\n"
            "# COORDENADAS DEL RECORRIDO PARA SLOT\n"
            "# (key_point seleccionado de historia_guard_ribbit_7.json)\n"
            "# ============================================\n\n"
            f"{traj_block}\n"
            "# ============================================\n"
            "# FIN DE COORDENADAS DEL RECORRIDO\n"
            "# ============================================\n\n"
            f"ANIMATION_INFO = {{\n"
            f"    'name': '{filename}',\n"
            f"    'frame_count': {total_frames},\n"
            f"    'fps': {fps_val},\n"
            f"    'duration_seconds': {dur_s},\n"
            f"    'entity': 'Jerry',\n"
            f"    'slot': {slot_num},\n"
            f"    'movement_type': '{movement}',\n"
            f"    'narrative_importance': 'expression',\n"
            f"    'rig_type': 'full_armature',\n"
            f"    'source': 'jerry_studio_v1.3',\n"
            f"    'bones_animated': {len(BONES_LISTA_FULL)},\n"
            f"    'animation_type': 'expression'\n"
            f"}}\n\n"
            f"ANIMATION_CONFIG = {{\n"
            f"    'name': '{anim_name}',\n"
            f"    'frame_count': {total_frames},\n"
            f"    'fps': {fps_val},\n"
            f"    'duration_seconds': {dur_s},\n"
            f"    'entity': 'Jerry',\n"
            f"    'slot': {slot_num},\n"
            f"    'movement_type': '{movement}',\n"
            f"}}\n\n"
            "BLINK_SEQUENCE = {\n"
            "    1: {\"closed\": 0.0,  \"hide\": False},\n"
            "    2: {\"closed\": 0.25, \"hide\": False},\n"
            "    3: {\"closed\": 0.5,  \"hide\": False},\n"
            "    4: {\"closed\": 0.75, \"hide\": False},\n"
            "    5: {\"closed\": 1.0,  \"hide\": True},\n"
            "    6: {\"closed\": 1.0,  \"hide\": True},\n"
            "    7: {\"closed\": 0.75, \"hide\": False},\n"
            "    8: {\"closed\": 0.5,  \"hide\": False},\n"
            "    9: {\"closed\": 0.25, \"hide\": False},\n"
            "}\n\n"
            f"EXPRESSION_CONFIG = {{\n"
            f"}}\n\n"
            "\n\n"
            f"BONES_LISTA = {repr(BONES_LISTA_FULL)}\n\n"
            "# ── Armatures secundarios del personaje ──\n"
            f"SECONDARY_ARMATURES = {repr(SECONDARY_ARMATURES)}\n\n"
            "# ── Interpolacion 3 fases ───────────────────────────────────\n\n"
            "def _lerp(a, b, t):\n"
            "    return (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t, a[2]+(b[2]-a[2])*t)\n\n"
            "def _smooth(t):\n"
            "    t = max(0.0, min(1.0, t))\n"
            "    return t * t * (3.0 - 2.0 * t)\n\n"
            f"def _interpolate_3phases(frame, total_frames, rot_start, rot_action, rot_end,\n"
            f"                          entry_ratio={er}, exit_ratio={xr}):\n"
            "    if frame <= 1:      return rot_start\n"
            "    if frame >= total_frames: return rot_end\n"
            "    entry_end  = max(2, int(total_frames * entry_ratio))\n"
            "    exit_start = min(total_frames - 1, int(total_frames * (1.0 - exit_ratio)))\n"
            "    if frame <= entry_end:\n"
            "        t = _smooth((frame - 1) / max(entry_end - 1, 1))\n"
            "        return _lerp(rot_start, rot_action, t)\n"
            "    elif frame >= exit_start:\n"
            "        t = _smooth((frame - exit_start) / max(total_frames - exit_start, 1))\n"
            "        return _lerp(rot_action, rot_end, t)\n"
            "    else:\n"
            "        return rot_action\n\n"
            "# Poses de referencia\n"
            f"# Pose inicio: {st.pose_start_name}  (duracion: {st.pose_start_duration} frames)\n"
            f"{_pose_lines(p_ini, 'POSE_INICIO')}\n\n"
            "# Pose accion (frame central)\n"
            f"{_pose_lines(p_act, 'POSE_ACCION')}\n\n"
            f"# Pose fin: {st.pose_end_name}  (duracion: {st.pose_end_duration} frames)\n"
            f"{_pose_lines(p_fin, 'POSE_FIN')}\n\n"
            "def _build_bone_functions(total_frames):\n"
            '    """\n'
            "    Animacion en 3 fases:\n"
            f"      Inicio  ({st.pose_start_name})  -> frame 1 exacto\n"
            "      Accion  -> frame central\n"
            f"      Fin     ({st.pose_end_name})    -> ultimo frame exacto\n"
            '    """\n'
            "    bone_functions = {}\n"
            "    for bone_name in BONES_LISTA:\n"
            "        s = POSE_INICIO.get(bone_name, (0.0, 0.0, 0.0))\n"
            "        c = POSE_ACCION.get(bone_name, s)\n"
            "        e = POSE_FIN.get(bone_name,    s)\n"
            "        bone_functions[bone_name] = (\n"
            "            lambda f, ps=s, pa=c, pe=e:\n"
            "                _interpolate_3phases(f, total_frames, ps, pa, pe)\n"
            "        )\n"
            "    return bone_functions\n\n"
            "# Keyframes exactos capturados desde la timeline de Blender\n"
            f"{chr(10).join(kf_lines)}\n\n"
            f"{chr(10).join(arm_rot_lines)}\n\n"
            f"{chr(10).join(root_kf_lines)}\n\n\n"
            "def _find_jerry_objects():\n"
            "    root = bpy.data.objects.get('guard_ribbit_7')\n"
            "    if not root:\n"
            "        root = next(\n"
            "            (o for o in bpy.data.objects\n"
            "             if o.name.lower() == 'guard_ribbit_7' and o.type == 'EMPTY'), None)\n"
            "    armature = bpy.data.objects.get('main_guard_ribbit_7')\n"
            "    if not armature or armature.type != 'ARMATURE':\n"
            "        if root:\n"
            "            armature = next(\n"
            "                (o for o in bpy.data.objects\n"
            "                 if o.type == 'ARMATURE' and o.parent == root), None)\n"
            "    if not armature or armature.type != 'ARMATURE':\n"
            "        armature = next(\n"
            "            (o for o in bpy.data.objects if o.type == 'ARMATURE'), None)\n"
            "    return root, armature\n\n\n"
            "def execute_animation(player_parts=None, start_frame=None, end_frame=None):\n"
            '    """\n'
            f"    Slot Jerry {movement}.\n\n"
            "    Requiere que SLOT_INDEX, START_FRAME, END_FRAME y ROOT_ROTATION_Z\n"
            "    hayan sido inyectados por el orquestador antes de llamar esta funcion,\n"
            "    o bien pasados como argumentos start_frame / end_frame.\n"
            '    """\n'
            "    if start_frame is None: start_frame = START_FRAME\n"
            "    if end_frame   is None: end_frame   = END_FRAME\n"
            "    if start_frame is None or end_frame is None:\n"
            "        raise ValueError(\n"
            "            'execute_animation: START_FRAME / END_FRAME no han sido definidos. '\n"
            "            'El orquestador debe inyectar los valores antes de ejecutar.')\n\n"
            "    total_frames = end_frame - start_frame + 1\n\n"
            "    # Obtener armature\n"
            "    armature = player_parts.get('body') if player_parts else None\n"
            "    if not armature:\n"
            "        armature = bpy.data.objects.get('main_guard_ribbit_7')\n"
            "    if not armature or armature.type != 'ARMATURE':\n"
            "        print('Error: No se encontro el main_guard_ribbit_7'); return False\n\n"
            "    bpy.context.view_layer.objects.active = armature\n"
            "    if armature.mode != 'POSE':\n"
            "        bpy.ops.object.mode_set(mode='POSE')\n"
            "    for bone in armature.pose.bones:\n"
            "        bone.rotation_mode = 'XYZ'\n\n"
            f"    _arm_action_name = f'slot_{{SLOT_INDEX:03d}}_{anim_name}_arm'\n"
            "    if not armature.animation_data:\n"
            "        armature.animation_data_create()\n"
            "    _arm_existing = bpy.data.actions.get(_arm_action_name)\n"
            "    if _arm_existing: bpy.data.actions.remove(_arm_existing)\n"
            "    _arm_action = bpy.data.actions.new(name=_arm_action_name)\n\n"
            "    # Obtener root\n"
            "    root = bpy.data.objects.get('guard_ribbit_7')\n"
            "    if not root:\n"
            "        root = next(\n"
            "            (o for o in bpy.data.objects\n"
            "             if o.name.lower() == 'guard_ribbit_7' and o.type == 'EMPTY'), None)\n\n"
            "    if root:\n"
            f"        _root_action_name = f'slot_{{SLOT_INDEX:03d}}_{anim_name}_root'\n"
            "        if not root.animation_data:\n"
            "            root.animation_data_create()\n"
            "        _root_existing = bpy.data.actions.get(_root_action_name)\n"
            "        if _root_existing: bpy.data.actions.remove(_root_existing)\n"
            "        _root_action = bpy.data.actions.new(name=_root_action_name)\n"
            "        root.animation_data.action = _root_action\n\n"
            "    # Aplicar ROOT_KEYFRAMES: offsets relativos al anchor point\n"
            "    if root and EMBEDDED_TRAJECTORY_POINTS:\n"
            "        _pt = EMBEDDED_TRAJECTORY_POINTS[0]['coordinates']\n"
            "        _anchor_loc = (_pt['x'], _pt['y'], _pt['z'])\n"
            "        _anchor_rot = (math.radians(ROOT_ROTATION_X),\n"
            "                       math.radians(ROOT_ROTATION_Y),\n"
            "                       math.radians(ROOT_ROTATION_Z))\n"
            "        if ROOT_KEYFRAMES:\n"
            "            # Aplicar offsets relativos (ROOT_KEYFRAMES['loc']) sumados al anchor\n"
            "            for _lf, _kf_data in sorted(ROOT_KEYFRAMES.items()):\n"
            "                _abs_f = start_frame + (_lf - 1)\n"
            "                if _abs_f > end_frame: break\n"
            "                _rl = _kf_data['loc']  # offset relativo al anchor\n"
            "                _offset_loc = (_anchor_loc[0] + _rl[0],\n"
            "                               _anchor_loc[1] + _rl[1],\n"
            "                               _anchor_loc[2] + _rl[2])\n"
            "                bpy.context.scene.frame_set(_abs_f)\n"
            "                root.location       = _offset_loc\n"
            "                root.rotation_euler = _kf_data['rot']\n"
            "                root.keyframe_insert(data_path='location',       frame=_abs_f)\n"
            "                root.keyframe_insert(data_path='rotation_euler', frame=_abs_f)\n"
            "        else:\n"
            "            # Fallback: anclar fijo en el anchor point\n"
            "            for _kf in range(start_frame, end_frame + 1):\n"
            "                bpy.context.scene.frame_set(_kf)\n"
            "                root.location       = _anchor_loc\n"
            "                root.rotation_euler = _anchor_rot\n"
            "                root.keyframe_insert(data_path='location',       frame=_kf)\n"
            "                root.keyframe_insert(data_path='rotation_euler', frame=_kf)\n\n"
            "    armature.animation_data.action = _arm_action\n\n"
            "    # Aplicar rotacion adicional del root si se provee via player_parts\n"
            "    jerry_root = player_parts.get('root') if player_parts else None\n"
            "    if not jerry_root:\n"
            "        jerry_root = next(\n"
            "            (o for o in bpy.data.objects\n"
            "             if o.name == 'guard_ribbit_7' and o.type == 'EMPTY'), None)\n\n"
            "    rz = ROOT_ROTATION_Z if ROOT_ROTATION_Z is not None else 0.0\n\n"
            "    # Aplicar keyframes de huesos\n"
            "    bone_funcs = _build_bone_functions(total_frames)\n"
            "    bones_applied = 0\n"
            "    bones_missing = []\n\n"
            "    if total_frames == TOTAL_FRAMES:\n"
            "        for bn in BONES_LISTA:\n"
            "            pb = armature.pose.bones.get(bn)\n"
            "            if not pb: bones_missing.append(bn); continue\n"
            "            pb.rotation_mode = 'XYZ'\n"
            "            for lf, rot in KEYFRAME_DATA.get(bn, {}).items():\n"
            "                abs_f = start_frame + (lf - 1)\n"
            "                pb.rotation_euler = rot\n"
            "                pb.keyframe_insert(data_path='rotation_euler', frame=abs_f)\n"
            "            bones_applied += 1\n"
            "    else:\n"
            "        for bone_name, fn in bone_funcs.items():\n"
            "            pb = armature.pose.bones.get(bone_name)\n"
            "            if not pb: bones_missing.append(bone_name); continue\n"
            "            pb.rotation_mode = 'XYZ'\n"
            "            for local_f in range(1, total_frames + 1):\n"
            "                abs_f = start_frame + (local_f - 1)\n"
            "                pb.rotation_euler = fn(local_f)\n"
            "                pb.keyframe_insert(data_path='rotation_euler', frame=abs_f)\n"
            "            bones_applied += 1\n\n"
            "    print(f'Keyframes aplicados a {bones_applied} bones')\n"
            "    if bones_missing:\n"
            "        print(f'   Bones no encontrados: {bones_missing}')\n\n"
            "    # ── Aplicar rotacion del armature por frame (orientacion por pose) ──\n"
            "    if ARMATURE_ROTATIONS:\n"
            "        armature.rotation_mode = 'XYZ'\n"
            "        if not armature.animation_data:\n"
            "            armature.animation_data_create()\n"
            "        _arm_obj_action_name = f'slot_{SLOT_INDEX:03d}_arm_obj_rot'\n"
            "        _arm_obj_existing = bpy.data.actions.get(_arm_obj_action_name)\n"
            "        if _arm_obj_existing: bpy.data.actions.remove(_arm_obj_existing)\n"
            "        _arm_obj_action = bpy.data.actions.new(name=_arm_obj_action_name)\n"
            "        armature.animation_data.action = _arm_obj_action\n"
            "        for lf, rot in ARMATURE_ROTATIONS.items():\n"
            "            abs_f = start_frame + (lf - 1)\n"
            "            bpy.context.scene.frame_set(abs_f)\n"
            "            armature.rotation_euler = rot\n"
            "            armature.keyframe_insert(data_path='rotation_euler', frame=abs_f)\n"
            "        # Suavizar curvas de rotacion del armature\n"
            "        for fc in _arm_obj_action.fcurves:\n"
            "            for kp in fc.keyframe_points:\n"
            "                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'\n"
            "        # Pasar al NLA\n"
            "        armature.animation_data.action = None\n"
            "        _arm_obj_track = armature.animation_data.nla_tracks.new()\n"
            "        _arm_obj_track.name = f'Slot_{SLOT_INDEX:03d}_arm_obj_rot'\n"
            "        _arm_obj_strip = _arm_obj_track.strips.new(_arm_obj_action_name, start_frame, _arm_obj_action)\n"
            "        _arm_obj_strip.frame_end     = end_frame\n"
            "        _arm_obj_strip.extrapolation = 'NOTHING'\n"
            "        _arm_obj_strip.use_auto_blend = False\n"
            "        _arm_obj_strip.blend_in  = 0\n"
            "        _arm_obj_strip.blend_out = 0\n\n"
            "    # [FIX] Restaurar _arm_action como accion activa para keyframes de bones\n"
            "    armature.animation_data.action = _arm_action\n\n"
            "    if armature.animation_data and armature.animation_data.action:\n"
            "        for fc in armature.animation_data.action.fcurves:\n"
            "            for kp in fc.keyframe_points:\n"
            "                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'\n\n"
            "    if jerry_root and jerry_root.animation_data and jerry_root.animation_data.action:\n"
            "        for fc in jerry_root.animation_data.action.fcurves:\n"
            "            for kp in fc.keyframe_points:\n"
            "                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'\n\n"
            f"    print(f'ANIMACION {anim_name} APLICADA!')\n"
            "    print(f'  Frames: {start_frame}-{end_frame}')\n\n"
            "    # guard_ribbit_7 no tiene mallas de ojos — sin parpadeo\n"
"    if bpy.context.scene.frame_end < end_frame:\n"
            "        bpy.context.scene.frame_end = end_frame\n\n"
            "    slot_label = SLOT_INDEX if SLOT_INDEX is not None else '?'\n"
            f"    print(f'OK: Slot {{slot_label}} {anim_name} completado  [{{start_frame}}-{{end_frame}}]')\n\n"
            "    # ── Forzar pose exacta en primer y ultimo frame ──\n"
            f"    _POSE_FRAME_1   = {repr(p_ini)}\n"
            f"    _POSE_FRAME_END = {repr(p_fin)}\n"
            "    for _sp_bone in armature.pose.bones:\n"
            "        _sp_bone.rotation_mode = 'XYZ'\n"
            "        if _sp_bone.name in _POSE_FRAME_1:\n"
            "            bpy.context.scene.frame_set(start_frame)\n"
            "            _sp_bone.rotation_euler = _POSE_FRAME_1[_sp_bone.name]\n"
            "            _sp_bone.keyframe_insert(data_path='rotation_euler', frame=start_frame)\n"
            "        if _sp_bone.name in _POSE_FRAME_END:\n"
            "            bpy.context.scene.frame_set(end_frame)\n"
            "            _sp_bone.rotation_euler = _POSE_FRAME_END[_sp_bone.name]\n"
            "            _sp_bone.keyframe_insert(data_path='rotation_euler', frame=end_frame)\n"
            "    # ── Fin forzado ──\n\n"
            "    # Mover Action del ARMATURE al NLA\n"
            "    if armature.animation_data and armature.animation_data.action:\n"
            "        _arm_done  = armature.animation_data.action\n"
            "        armature.animation_data.action = None\n"
            "        _arm_track = armature.animation_data.nla_tracks.new()\n"
            f"        _arm_track.name = f'Slot_{{SLOT_INDEX:03d}}_arm'\n"
            "        _arm_strip = _arm_track.strips.new(_arm_done.name, start_frame, _arm_done)\n"
            "        _arm_strip.frame_end        = end_frame\n"
            "        _arm_strip.extrapolation    = 'NOTHING'\n"
            "        _arm_strip.use_auto_blend   = False\n"
            "        _arm_strip.blend_in         = 0\n"
            "        _arm_strip.blend_out        = 0\n\n"
            "    # Mover Action del ROOT al NLA\n"
            "    if root and root.animation_data and root.animation_data.action:\n"
            "        _root_done  = root.animation_data.action\n"
            "        root.animation_data.action = None\n"
            "        _root_track = root.animation_data.nla_tracks.new()\n"
            f"        _root_track.name = f'Slot_{{SLOT_INDEX:03d}}_root'\n"
            "        _root_strip = _root_track.strips.new(_root_done.name, start_frame, _root_done)\n"
            "        _root_strip.frame_end        = end_frame\n"
            "        _root_strip.extrapolation    = 'HOLD_FORWARD'\n"
            "        _root_strip.use_auto_blend   = False\n"
            "        _root_strip.blend_in         = 0\n"
            "        _root_strip.blend_out        = 0\n\n"
            "    return True\n\n\n"
            "if __name__ == '__main__':\n"
            "    execute_animation(None, start_frame=START_FRAME, end_frame=END_FRAME)\n"
        )

        out_dir  = bpy.path.abspath(st.anim_dir)
        os.makedirs(out_dir, exist_ok=True)
        filepath = os.path.join(out_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)

        st.last_export_path = filepath
        self.report({"INFO"}, f"Exportado: {filepath}")
        return {"FINISHED"}

# =============================================================================
# IMPORTAR .py
# =============================================================================

class GRB7ST_OT_ImportAnimation(Operator):
    bl_idname    = "grb7st.import_animation"
    bl_label     = "Importar animacion .py"
    bl_description = "Carga un .py exportado y lo aplica en la timeline"
    bl_options   = {"REGISTER", "UNDO"}

    filepath:    StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.py", options={"HIDDEN"})

    def invoke(self, context, event):
        start = bpy.path.abspath(context.scene.grb7st.anim_dir)
        if os.path.isdir(start):
            self.filepath = start + os.sep
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        st    = context.scene.grb7st
        scene = context.scene
        path  = bpy.path.abspath(self.filepath)

        if not os.path.isfile(path):
            self.report({"ERROR"}, f"Archivo no encontrado: {path}")
            return {"CANCELLED"}
        if not st.armature_name:
            self.report({"ERROR"}, "Selecciona el armature primero")
            return {"CANCELLED"}
        armature = scene.objects.get(st.armature_name)
        if not armature or armature.type != "ARMATURE":
            self.report({"ERROR"}, "main_guard_ribbit_7 no valido")
            return {"CANCELLED"}

        ns = {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                exec(compile(f.read(), path, "exec"), ns)
        except Exception as e:
            self.report({"ERROR"}, f"Error al leer .py: {e}")
            return {"CANCELLED"}

        kf_data     = ns.get("KEYFRAME_DATA", {})
        total_f     = ns.get("TOTAL_FRAMES", 0)
        bones_lista = ns.get("BONES_LISTA", BONES_LISTA)

        if not kf_data or total_f == 0:
            self.report({"ERROR"}, "El .py no contiene KEYFRAME_DATA validos")
            return {"CANCELLED"}

        context.view_layer.objects.active = armature
        if armature.mode != "POSE":
            bpy.ops.object.mode_set(mode="POSE")
        for pb in armature.pose.bones:
            pb.rotation_mode = "XYZ"

        if armature.animation_data and armature.animation_data.action:
            old = armature.animation_data.action
            armature.animation_data.action = None
            bpy.data.actions.remove(old)

        sf = st.start_frame
        for bn in bones_lista:
            pb = armature.pose.bones.get(bn)
            if not pb:
                continue
            pb.rotation_mode = "XYZ"
            for lf, rot in kf_data.get(bn, {}).items():
                abs_f = sf + (int(lf) - 1)
                pb.rotation_euler = Euler(rot, "XYZ")
                pb.keyframe_insert(data_path="rotation_euler", frame=abs_f)

        scene.frame_start = sf
        scene.frame_end   = sf + total_f - 1
        scene.frame_set(sf)


        st.anim_generated   = True
        st.total_frames_gen = total_f
        st.end_frame_gen    = sf + total_f - 1
        self.report({"INFO"}, st.status_msg)
        return {"FINISHED"}

# =============================================================================
# EXTRAER POSE
# =============================================================================

class GRB7ST_OT_ExtractPose(Operator):
    bl_idname    = "grb7st.extract_pose"
    bl_label     = "Guardar como nueva pose"
    bl_description = "Extrae la pose del frame indicado y la guarda en la libreria"
    bl_options   = {"REGISTER"}

    def execute(self, context):
        st    = context.scene.grb7st
        scene = context.scene

        label = st.extract_label.strip()
        if not label:
            self.report({"ERROR"}, "Escribe un nombre para la nueva pose")
            return {"CANCELLED"}
        if not st.armature_name:
            self.report({"ERROR"}, "Selecciona el armature")
            return {"CANCELLED"}
        armature = scene.objects.get(st.armature_name)
        if not armature or armature.type != "ARMATURE":
            self.report({"ERROR"}, "main_guard_ribbit_7 no valido")
            return {"CANCELLED"}

        frame = scene.frame_current if st.extract_use_current else st.extract_frame
        if not st.extract_use_current:
            scene.frame_set(frame)
        context.view_layer.update()

        def _capture_pose_bones(arm_obj, bones_dict):
            """Captura todos los pose bones de un armature y los agrega a bones_dict."""
            for pb in arm_obj.pose.bones:
                rot_e = pb.rotation_euler
                rot_q = pb.rotation_quaternion
                local_space = {
                    "location": {
                        "x": round(pb.location.x, 6),
                        "y": round(pb.location.y, 6),
                        "z": round(pb.location.z, 6),
                    },
                    "rotation_euler_rad": {
                        "x": round(rot_e.x, 6),
                        "y": round(rot_e.y, 6),
                        "z": round(rot_e.z, 6),
                    },
                    "rotation_euler_deg": {
                        "x": round(math.degrees(rot_e.x), 4),
                        "y": round(math.degrees(rot_e.y), 4),
                        "z": round(math.degrees(rot_e.z), 4),
                    },
                    "rotation_quaternion": {
                        "w": round(rot_q.w, 6), "x": round(rot_q.x, 6),
                        "y": round(rot_q.y, 6), "z": round(rot_q.z, 6),
                    },
                    "scale": {
                        "x": round(pb.scale.x, 6),
                        "y": round(pb.scale.y, 6),
                        "z": round(pb.scale.z, 6),
                    },
                }
                bones_dict[pb.name] = {
                    "parent":    pb.parent.name if pb.parent else None,
                    "connected": pb.bone.use_connect,
                    "local_space": local_space,
                    "rotation_mode": pb.rotation_mode,
                    # Campos raiz para retrocompatibilidad con Formato A (exportador antiguo)
                    "raw_rotation_euler_deg": local_space["rotation_euler_deg"],
                    "raw_rotation_quaternion": local_space["rotation_quaternion"]
                        if pb.rotation_mode == "QUATERNION" else None,
                    "raw_location": local_space["location"],
                    "raw_scale":    local_space["scale"],
                }

        bones_data = {}
        # Capturar bones del armature principal
        _capture_pose_bones(armature, bones_data)
        # Capturar bones de los armatures secundarios (shield y spear)
        for sec_name in SECONDARY_ARMATURES:
            sec_obj = scene.objects.get(sec_name)
            if sec_obj and sec_obj.type == "ARMATURE":
                _capture_pose_bones(sec_obj, bones_data)

        record = {
            "label":           label,
            "frame":           frame,
            "armature":        armature.name,
            "character":       armature.parent.name if armature.parent else armature.name,
            "timestamp":       datetime.now().isoformat(),
            "blender_version": bpy.app.version_string,
            "file":            os.path.basename(bpy.data.filepath) if bpy.data.filepath else "unsaved",
            "bone_count":      len(bones_data),
            "bones":           bones_data,
        }

        out_dir  = bpy.path.abspath(st.poses_dir)
        os.makedirs(out_dir, exist_ok=True)
        # Conservar caracteres unicode validos (letras, numeros, guiones, espacios).
        # Solo eliminar caracteres que el sistema de archivos rechaza: / \ : * ? " < > |
        _FORBIDDEN = set('/\\:*?"<>|')
        safe_label = "".join(
            c if c not in _FORBIDDEN else "_" for c in label
        ).strip().replace(" ", "_")
        # Quitar extension .json si el usuario ya la escribio en el nombre
        # para evitar el doble sufijo: mi_pose.json -> mi_pose.json.json
        while safe_label.lower().endswith(".json"):
            safe_label = safe_label[:-5]
        if not safe_label:
            safe_label = "pose_sin_nombre"
        filename = f"{safe_label}.json"
        filepath = os.path.join(out_dir, filename)

        data = {"poses": []}
        if os.path.isfile(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

        data["poses"].append(record)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        total_saved = len(data["poses"])
        st.extract_label = ""
        # Invalidar cache del EnumProperty para que la nueva pose aparezca
        # inmediatamente en el selector "Poses de accion (intermedias)"
        invalidate_enum_cache()
        self.report({"INFO"},
            f"Pose '{label}' (frame {frame}) guardada -> {filename}  ({total_saved} poses totales)")
        return {"FINISHED"}

# =============================================================================
# GUARDAR / CARGAR CONFIGURACION DE TRABAJO (.json)
# =============================================================================

