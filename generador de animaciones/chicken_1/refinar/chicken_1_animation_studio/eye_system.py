# -*- coding: utf-8 -*-
"""
eye_system.py — Chicken 1 Animation Studio v1.8
Sistema de expresiones de mallas rectangulares de ojos (shape keys)
y parpadeo de efecto cortina.
"""
import bpy
from bpy.types import Operator
from .constants import EYE_MESH_NAMES
from .fcurve_compat import get_fcurves, ensure_fcurves

# =============================================================================
# UTILIDADES DE EXPRESION DE MALLAS
# =============================================================================

def _eye_apply_curve(factor, curve_mode):
    if curve_mode == "QUADRATIC":  return factor ** 2
    if curve_mode == "CUBIC":      return factor ** 3
    return factor

def _eye_detect_axes(mesh_obj):
    """Detecta ejes horizontal, vertical y profundidad por rango de coordenadas."""
    verts = [v.co for v in mesh_obj.data.vertices]
    if not verts:
        return "x", "z", "y"
    xs = [v.x for v in verts]; ys = [v.y for v in verts]; zs = [v.z for v in verts]
    ranges = {"x": max(xs) - min(xs), "y": max(ys) - min(ys), "z": max(zs) - min(zs)}
    sorted_r = sorted(ranges.items(), key=lambda i: i[1])
    depth_axis      = sorted_r[0][0]
    vertical_axis   = sorted_r[1][0]
    horizontal_axis = sorted_r[2][0]
    return horizontal_axis, vertical_axis, depth_axis

def _eye_compute_vertex(orig_co, h_axis, v_axis, bounds, expression, settings, mirror_h=False):
    """
    Desplaza un vertice segun la expresion. Devuelve nueva coordenada.
    mirror_h=True invierte el eje horizontal para el ojo derecho,
    garantizando simetria especular correcta en expresiones asimetricas
    como 'enojado' y 'sospecha'.
    """
    cx, cy, cz = bounds["cx"], bounds["cy"], bounds["cz"]
    rx, ry, rz = bounds["rx"], bounds["ry"], bounds["rz"]

    h_val = getattr(orig_co, h_axis)
    v_val = getattr(orig_co, v_axis)

    center_v = {"x": cx, "y": cy, "z": cz}[v_axis]
    range_v  = {"x": rx, "y": ry, "z": rz}[v_axis]
    center_h = {"x": cx, "y": cy, "z": cz}[h_axis]
    range_h  = {"x": rx, "y": ry, "z": rz}[h_axis]

    v_mult = -1 if settings.invert_vertical   else 1
    h_mult = -1 if settings.invert_horizontal else 1

    v_factor = (v_val - center_v) / (range_v / 2) if range_v > 0 else 0
    h_factor = (h_val - center_h) / (range_h / 2) if range_h > 0 else 0

    # Aplicar espejo horizontal para el ojo derecho en expresiones
    # que tienen componente asimetrica (enojado, sospecha).
    if mirror_h:
        h_factor = -h_factor

    zone = settings.affect_zone
    if zone == "UPPER":
        if v_factor <= 0:
            return orig_co.copy()
        v_factor_norm = v_factor
    elif zone == "LOWER":
        if v_factor >= 0:
            return orig_co.copy()
        v_factor_norm = -v_factor
    else:
        v_factor_norm = abs(v_factor)

    offset = 0.0
    if expression in ("feliz", "triste"):
        curve = _eye_apply_curve(abs(h_factor), settings.curve_mode)
        intens = settings.intensity_feliz if expression == "feliz" else settings.intensity_triste
        sign   = 1 if expression == "feliz" else -1
        offset = sign * intens * curve * v_factor_norm * v_mult

    elif expression in ("sospecha", "enojado"):
        min_h  = center_h - range_h / 2
        # h_norm calculado sobre h_val original (geometria) + efecto espejo via h_factor
        h_norm = (h_val - min_h) / range_h if range_h > 0 else 0.5
        if mirror_h:
            # Espejo: el lado "interior" del ojo derecho corresponde al lado "exterior"
            h_norm = 1.0 - h_norm
        if expression == "sospecha":
            intens = settings.intensity_sospecha
            offset = (intens * h_norm - intens / 2) * v_factor_norm * v_mult * h_mult
        else:
            intens = settings.intensity_enojado
            offset = (-intens * h_norm + intens / 2) * v_factor_norm * v_mult * h_mult

    elif expression == "cerrado":
        offset = -(v_val - center_v) * 0.85

    elif expression == "cansado":
        # Mitad superior comprimida al 50%
        offset = -(v_val - center_v) * 0.4 * v_factor_norm

    elif expression == "sorpresa":
        # Expande ligeramente los vertices superiores
        offset = (v_val - center_v) * 0.15 * v_factor_norm

    new_co = orig_co.copy()
    setattr(new_co, v_axis, v_val + offset)
    return new_co


def _eye_ensure_subdivided(eye_obj, cuts):
    """Subdivide la malla si tiene muy pocos vertices."""
    if cuts <= 0 or len(eye_obj.data.vertices) > 12:
        return
    import bpy as _bpy
    _bpy.context.view_layer.objects.active = eye_obj
    _bpy.ops.object.mode_set(mode="EDIT")
    _bpy.ops.mesh.select_all(action="SELECT")
    for _ in range(cuts):
        _bpy.ops.mesh.subdivide(number_cuts=1)
    _bpy.ops.object.mode_set(mode="OBJECT")


def build_expression_shape_keys(eye_obj, settings, is_right_eye=False):
    """
    Crea o regenera todos los shape keys de expresion para una malla de ojo.
    Nombres de shape keys: Basis, Feliz, Triste, Enojado, Sospecha, Cerrado, Cansado, Sorpresa, Closed

    is_right_eye=True activa el espejo horizontal para garantizar simetria especular
    correcta en expresiones asimetricas (enojado, sospecha).
    """
    _eye_ensure_subdivided(eye_obj, settings.subdivide_cuts)

    # Limpiar shape keys anteriores de expresion (conservar Basis)
    if eye_obj.data.shape_keys:
        keep = {"Basis"}
        to_remove = [sk.name for sk in eye_obj.data.shape_keys.key_blocks if sk.name not in keep]
        eye_obj.shape_key_clear()  # limpia todo

    # Crear Basis
    if not eye_obj.data.shape_keys:
        eye_obj.shape_key_add(name="Basis", from_mix=False)

    mesh = eye_obj.data
    orig_coords = [v.co.copy() for v in mesh.vertices]

    # Calcular bounds  (MeshVertex expone .co, no .x/.y/.z directamente)
    xs = [v.co.x for v in mesh.vertices]
    ys = [v.co.y for v in mesh.vertices]
    zs = [v.co.z for v in mesh.vertices]
    bounds = {
        "cx": (max(xs)+min(xs))/2, "cy": (max(ys)+min(ys))/2, "cz": (max(zs)+min(zs))/2,
        "rx": max(xs)-min(xs),     "ry": max(ys)-min(ys),     "rz": max(zs)-min(zs),
    }

    h_axis, v_axis, _ = _eye_detect_axes(eye_obj)
    if settings.swap_axes:
        h_axis, v_axis = v_axis, h_axis

    all_expressions = ["feliz", "triste", "enojado", "sospecha", "cerrado", "cansado", "sorpresa"]

    for expr_lower in all_expressions:
        sk = eye_obj.shape_key_add(name=expr_lower.capitalize(), from_mix=False)
        sk.value = 0.0
        sk.slider_min = -2.0
        sk.slider_max = 2.0
        for i, orig in enumerate(orig_coords):
            sk.data[i].co = _eye_compute_vertex(
                orig, h_axis, v_axis, bounds, expr_lower, settings,
                mirror_h=is_right_eye,
            )

    # Shape key "Closed" para parpadeo cortina (lleva todos los vertices al Z minimo)
    sk_closed = eye_obj.shape_key_add(name="Closed", from_mix=False)
    sk_closed.value = 0.0
    min_z = min(v.co.z for v in mesh.vertices)
    for i, v in enumerate(mesh.vertices):
        new_co = v.co.copy()
        new_co.z = min_z
        sk_closed.data[i].co = new_co

    return True


def apply_expression_to_eye(eye_obj, expression_name, value, frame):
    """Aplica el valor de un shape key de expresion en el frame dado."""
    if not eye_obj.data.shape_keys:
        return
    for sk in eye_obj.data.shape_keys.key_blocks:
        if sk.name == "Basis":
            continue
        target_val = value if sk.name.lower() == expression_name.lower() else 0.0
        sk.value = target_val
        sk.keyframe_insert(data_path="value", frame=frame)


def _get_eye_objects():
    """Devuelve (ojo_izq, ojo_der) o (None, None) si no se encuentran."""
    left  = bpy.data.objects.get("ojo_izquierdo_chicken_1")
    right = bpy.data.objects.get("ojo_derecho_chicken_1")
    return left, right


# =============================================================================
# OPERADORES DE EXPRESIONES DE OJOS
# =============================================================================

class CH1ST_OT_BuildEyeShapeKeys(Operator):
    bl_idname     = "ch1st.build_eye_shape_keys"
    bl_label      = "Crear/Recrear Shape Keys de Expresion"
    bl_description = (
        "Genera (o regenera) los shape keys de expresion y parpadeo "
        "en las mallas ojo_izquierdo_chicken_1 y ojo_derecho_chicken_1"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        eye_s = context.scene.ch1st.eye_expr
        left, right = _get_eye_objects()
        if not left or not right:
            self.report({"ERROR"}, "No se encontraron ojo_izquierdo_chicken_1 / ojo_derecho_chicken_1")
            return {"CANCELLED"}
        ok = True
        for eye in (left, right):
            if eye.type != "MESH":
                self.report({"WARNING"}, f"{eye.name} no es una malla"); ok = False; continue
            is_right = (eye == right)
            build_expression_shape_keys(eye, eye_s, is_right_eye=is_right)
        if ok:
            self.report({"INFO"}, "Shape keys de expresion creados en ambos ojos")
        return {"FINISHED"}


class CH1ST_OT_ApplyEyeExpressionPreview(Operator):
    bl_idname     = "ch1st.apply_eye_expression_preview"
    bl_label      = "Aplicar Expresion en Frame Actual"
    bl_description = "Inserta keyframe con la expresion activa en el frame actual de la timeline"
    bl_options    = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene  = context.scene
        eye_s  = scene.ch1st.eye_expr
        expr   = eye_s.active_expression.lower()
        val    = eye_s.expression_value
        frame  = scene.frame_current
        left, right = _get_eye_objects()
        if not left or not right:
            self.report({"ERROR"}, "Ojos no encontrados"); return {"CANCELLED"}
        for eye in (left, right):
            if not eye.data.shape_keys:
                self.report({"WARNING"}, f"Crea los shape keys primero ({eye.name})")
                return {"CANCELLED"}
            apply_expression_to_eye(eye, expr, val, frame)
        self.report({"INFO"}, f"Expresion '{expr}' (val={val:.2f}) aplicada en frame {frame}")
        return {"FINISHED"}


class CH1ST_OT_ResetEyeExpressions(Operator):
    bl_idname     = "ch1st.reset_eye_expressions"
    bl_label      = "Resetear Expresiones (frame actual)"
    bl_description = "Pone todos los shape keys de expresion a 0 en el frame actual"
    bl_options    = {"REGISTER", "UNDO"}

    def execute(self, context):
        frame  = context.scene.frame_current
        left, right = _get_eye_objects()
        for eye in (left, right):
            if eye and eye.data.shape_keys:
                for sk in eye.data.shape_keys.key_blocks:
                    if sk.name != "Basis":
                        sk.value = 0.0
                        sk.keyframe_insert(data_path="value", frame=frame)
        self.report({"INFO"}, f"Expresiones reseteadas en frame {frame}")
        return {"FINISHED"}


# =============================================================================
# SISTEMA DE PARPADEO (efecto cortina) — funciones de runtime
# =============================================================================

BLINK_SEQUENCE_BASE = {
    1: {"closed": 0.00, "hide": False},
    2: {"closed": 0.25, "hide": False},
    3: {"closed": 0.50, "hide": False},
    4: {"closed": 0.75, "hide": False},
    5: {"closed": 1.00, "hide": True},
    6: {"closed": 1.00, "hide": True},
    7: {"closed": 0.75, "hide": False},
    8: {"closed": 0.50, "hide": False},
    9: {"closed": 0.25, "hide": False},
}

def _ensure_closed_shape_key(eye_obj):
    """Crea shape key Closed (cortina) si no existe ya."""
    if not eye_obj or eye_obj.type != "MESH":
        return
    if not eye_obj.data.shape_keys:
        eye_obj.shape_key_add(name="Basis", from_mix=False)
    names = [sk.name for sk in eye_obj.data.shape_keys.key_blocks]
    if "Closed" not in names:
        sk = eye_obj.shape_key_add(name="Closed", from_mix=False)
        min_z = min(v.co.z for v in eye_obj.data.vertices)
        for i, v in enumerate(eye_obj.data.vertices):
            new_co = v.co.copy()
            new_co.z = min_z
            sk.data[i].co = new_co


def _clear_blink_keyframes_in_range(eye, start_frame, end_frame):
    """
    Elimina keyframes previos de 'Closed', hide_viewport y hide_render
    en el rango [start_frame, end_frame] para evitar interpolacion desde frame 1.
    """
    if eye is None:
        return
    # Limpiar hide_viewport / hide_render del objeto
    if eye.animation_data and eye.animation_data.action:
        for dp in ("hide_viewport", "hide_render"):
            fc = get_fcurves(eye.animation_data.action).find(dp)
            if fc:
                to_remove = [kp for kp in fc.keyframe_points
                             if start_frame <= kp.co.x <= end_frame]
                for kp in reversed(to_remove):
                    fc.keyframe_points.remove(kp)
    # Limpiar shape key 'Closed'
    if (eye.data and hasattr(eye.data, "shape_keys")
            and eye.data.shape_keys
            and eye.data.shape_keys.animation_data
            and eye.data.shape_keys.animation_data.action):
        fc = get_fcurves(eye.data.shape_keys.animation_data.action).find(
            "key_blocks[\"Closed\"].value")
        if fc:
            to_remove = [kp for kp in fc.keyframe_points
                         if start_frame <= kp.co.x <= end_frame]
            for kp in reversed(to_remove):
                fc.keyframe_points.remove(kp)


def apply_blink_sequence(start_frame, end_frame, blink_count, blink_duration):
    """
    Inserta keyframes de parpadeo distribuidos uniformemente entre start_frame y end_frame.
    Usa shape key 'Closed' + hide_viewport/hide_render.
    """
    left, right = _get_eye_objects()
    for eye in (left, right):
        if eye:
            _ensure_closed_shape_key(eye)
            # [FIX] Limpiar keyframes previos del rango para evitar
            # interpolacion indeseada desde frame 1 hasta start_frame.
            _clear_blink_keyframes_in_range(eye, start_frame, end_frame)

    slot_dur = end_frame - start_frame + 1
    # Distribuir parpadeos uniformemente: N segmentos iguales, parpadeo centrado en cada uno
    blink_starts = []
    _segment = slot_dur / blink_count if blink_count > 0 else slot_dur
    for i in range(blink_count):
        _center = start_frame + _segment * (i + 0.5)
        bs = int(_center - blink_duration / 2)
        bs = max(start_frame, min(bs, end_frame - blink_duration))
        blink_starts.append(bs)

    blink_ranges = set()
    for bs in blink_starts:
        for offset in range(blink_duration):
            blink_ranges.add(bs + offset)

    for t in range(start_frame, end_frame + 1):
        blink_applied = False
        for bs in blink_starts:
            if bs <= t < bs + blink_duration:
                blink_applied = True
                offset = t - bs + 1
                fd     = BLINK_SEQUENCE_BASE.get(min(offset, 9), {"closed": 0.0, "hide": False})
                progress = fd["closed"]
                hide     = fd["hide"]
                for eye in (left, right):
                    if eye and eye.data.shape_keys:
                        ck = eye.data.shape_keys.key_blocks.get("Closed")
                        if ck:
                            ck.value = progress
                            ck.keyframe_insert(data_path="value", frame=t)
                        eye.hide_viewport = hide
                        eye.hide_render   = hide
                        eye.keyframe_insert(data_path="hide_viewport", frame=t)
                        eye.keyframe_insert(data_path="hide_render",   frame=t)
                break
        if not blink_applied:
            for eye in (left, right):
                if eye and eye.data.shape_keys:
                    ck = eye.data.shape_keys.key_blocks.get("Closed")
                    if ck:
                        ck.value = 0.0
                        ck.keyframe_insert(data_path="value", frame=t)
                    eye.hide_viewport = False
                    eye.hide_render   = False
                    eye.keyframe_insert(data_path="hide_viewport", frame=t)
                    eye.keyframe_insert(data_path="hide_render",   frame=t)


# =============================================================================
# FILTROS DE MOVIMIENTO ORGANICO  (post-proceso sobre fcurves)
# =============================================================================

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
        for fc in get_fcurves(action):
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
        fc   = get_fcurves(armature.animation_data.action).find(dp, index=axis)
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
        fc = get_fcurves(armature.animation_data.action).find(dp, index=axis)
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
        fc = get_fcurves(armature.animation_data.action).find(dp, index=axis)
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
        for bone in ("Spine1_M_chicken_1", "Chest_M_chicken_1"):
            _mod_bone_rot(bone, 0, deltas_x)   # X
            _mod_bone_rot(bone, 2, deltas_z)   # Z

    # ── FILTRO: micro-movimiento de cabeza ──
    if org.head_sway_enabled:
        amp   = org.head_sway_amplitude
        speed = org.head_sway_speed
        seed  = org.head_sway_seed
        for axis in range(3):
            deltas = [amp * _noise_at(f, speed, seed, axis) for f in frames]
            for bone in ("Head_M_chicken_1", "Jaw_M_chicken_1"):
                _mod_bone_rot(bone, axis, deltas)

    # ── FILTRO: desplazamiento de peso (hips lateral) ──
    if org.weight_shift_enabled:
        amp   = org.weight_shift_amplitude
        speed = org.weight_shift_speed
        deltas_loc_x = [amp * math.sin(f * speed * 2 * math.pi) for f in frames]
        deltas_rot_z = [amp * 0.8 * math.cos(f * speed * 2 * math.pi) for f in frames]
        _mod_bone_loc("Root_M_chicken_1", 0, deltas_loc_x)
        _mod_bone_rot("Root_M_chicken_1", 2, deltas_rot_z)

    # ── FILTRO: noise en hombros ──
    if org.shoulder_noise_enabled:
        amp   = org.shoulder_noise_amplitude
        speed = org.shoulder_noise_speed
        seed  = org.shoulder_noise_seed
        for axis in range(3):
            for bone, s_off in (("Scapula_R_chicken_1", 0), ("Scapula_L_chicken_1", 17)):
                deltas = [amp * _noise_at(f, speed, seed + s_off, axis) for f in frames]
                _mod_bone_rot(bone, axis, deltas)

    # ── FILTRO: micro-escala organica ──
    if org.micro_scale_enabled:
        amp   = org.micro_scale_amplitude
        speed = org.breathing_speed  # sincronizado con respiracion
        phase = org.breathing_phase
        deltas_s = [amp * math.sin(f * speed * 2 * math.pi + phase) for f in frames]
        _mod_bone_scale("Chest_M_chicken_1", 2, deltas_s)   # escala Z del Spine1

    # ── FILTRO: secondary motion brazos (retardo de codos) ──
    if org.secondary_motion_enabled:
        lag     = int(round(org.secondary_motion_lag))
        damping = org.secondary_motion_damping
        if armature.animation_data and armature.animation_data.action:
            action = armature.animation_data.action
            for bone in ("Elbow_R_chicken_1", "Elbow_L_chicken_1"):
                dp = f'pose.bones["{bone}"].rotation_euler'
                for axis in range(3):
                    fc = get_fcurves(action).find(dp, index=axis)
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

    # ── FILTRO: noise en posicion del root ──
    if org.root_noise_enabled:
        root_obj = scene.objects.get("chicken_1")
        if root_obj and root_obj.animation_data and root_obj.animation_data.action:
            root_action = root_obj.animation_data.action
            strength = org.root_noise_strength
            freq     = org.root_noise_frequency
            seed     = org.root_noise_seed
            for axis in range(3):
                fc = get_fcurves(root_action).find("location", index=axis)
                if fc is None:
                    continue
                kps  = sorted(fc.keyframe_points, key=lambda k: k.co.x)
                kmap = {int(k.co.x): k for k in kps}
                for i, f in enumerate(frames):
                    if f in kmap:
                        kmap[f].co.y += strength * _noise_at(f, freq, seed, axis)
                fc.update()


