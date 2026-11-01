# -*- coding: utf-8 -*-
"""
organic_filters.py — Rat 1 Animation Studio

Filtros de movimiento organico: post-proceso sobre las fcurves ya
generadas por Pasos 1+2+3, que elimina la rigidez robotica agregando
micro-variaciones fisicamente plausibles (respiracion, sway de cabeza,
desplazamiento de peso, noise en hombros/root, secondary motion,
suavizado, micro-escala).

Port 1:1 desde alfred_animation_studio/operators_anim.py
(_noise_at, _gaussian_smooth, _apply_organic_filters), pedido explicito
de Kebyn como PRIMER subsistema a portar de Alfred a rat_1
(2026-09-03), antes de Lanzar/Recoger/Mantener, Sistema de ojos y
Oscilaciones de huesos.

UNICO CAMBIO respecto a Alfred: los nombres de bones/objeto destino,
adaptados al rig cuadrupedo de rat_1 (ver constants.py: ORGANIC_*, con
la tabla de equivalencias Alfred -> rat_1). La logica matematica de
cada filtro (formulas de seno/noise/suavizado/retardo) es identica.
"""

import math
from .constants import (
    ORGANIC_HIPS_BONE,
    ORGANIC_SPINE_BONES,
    ORGANIC_HEAD_BONES,
    ORGANIC_SHOULDER_BONES,
    ORGANIC_SECONDARY_BONES,
    ORGANIC_ROOT_OBJECT,
)

import bpy  # noqa: F401  (usado solo para type hints / claridad, no se llama directo aca)


def _noise_at(frame, freq, seed, dim=0):
    """Ruido procesal deterministico (sin-hash sin bpy.app.driver_namespace)."""
    v = math.sin(frame * freq * 1.3 + seed * 7.3 + dim * 3.7)
    v += math.sin(frame * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5
    v += math.sin(frame * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25
    return v / 1.75  # rango aprox. [-1, 1]


def _gaussian_smooth(values, factor):
    """Suavizado gaussiano de una lista de valores con factor [0,1]."""
    n = len(values)
    if n < 3:
        return values[:]
    out = values[:]
    w = [0.25, 0.5, 0.25]
    for i in range(1, n - 1):
        out[i] = values[i - 1] * w[0] + values[i] * w[1] + values[i + 1] * w[2]
        out[i] = values[i] * (1 - factor) + out[i] * factor
    return out


def apply_organic_filters(context, armature, start_frame, end_frame, org,
                           base_overrides=None, target_action=None,
                           target_action_root=None):
    """
    Aplica filtros organicos sobre las fcurves ya generadas.
    Lee los valores de los keyframes existentes, les suma las
    micro-variaciones y escribe los valores modificados de vuelta a los
    mismos keyframes.

    target_action / target_action_root: AISLAMIENTO REAL (mismo criterio
    que Alfred). Si se pasan, los filtros leen y escriben SIEMPRE sobre
    estas actions ya construidas (target_action para el armature,
    target_action_root para el objeto raiz "rat_1") -- nunca sobre
    armature.animation_data.action / root.animation_data.action en vivo.
    Con esto el resultado de un segmento depende UNICAMENTE de los datos
    ya presentes en su propia action (copia aislada de la Capa 1,
    ver _copy_action_range en operators_segments.py), sin importar el
    orden en que se procesen los demas segmentos ni el playhead de la
    escena. base_overrides queda como fallback (solo se usa si la fcurve
    destino no tiene NINGUN keyframe propio todavia).
    """
    scene = context.scene
    frames = list(range(start_frame, end_frame + 1))
    n = len(frames)
    if n < 3:
        return

    _arm_action = target_action
    if _arm_action is None and armature.animation_data:
        _arm_action = armature.animation_data.action

    # ── FILTRO: suavizado de fcurves ──
    if org.smooth_curves_enabled and _arm_action:
        for fc in _arm_action.fcurves:
            kps = sorted(fc.keyframe_points, key=lambda k: k.co.x)
            vals = [k.co.y for k in kps]
            for _ in range(org.smooth_passes):
                vals = _gaussian_smooth(vals, org.smooth_factor)
            for k, v in zip(kps, vals):
                k.co.y = v
            fc.update()

    def _get_or_create_fc(dp, axis):
        action = target_action
        if action is None:
            if not armature.animation_data:
                armature.animation_data_create()
            if not armature.animation_data.action:
                armature.animation_data.action = bpy.data.actions.new(
                    f"{armature.name}_organic")
            action = armature.animation_data.action
        fc = action.fcurves.find(dp, index=axis)
        if fc is None:
            fc = action.fcurves.new(dp, index=axis)
        return fc

    def _mod_bone_generic(bone_name, channel, axis, deltas, base_default):
        """Suma deltas[frame_idx] al canal (rotation_euler/location/scale)
        del bone, insertando keyframes nuevos donde todavia no existan.
        El valor base para esos frames nuevos se toma SIEMPRE de la
        propia fcurve (interpolando lo que ya haya en ella) -- nunca del
        estado en vivo del armature."""
        dp = f'pose.bones["{bone_name}"].{channel}'
        fc = _get_or_create_fc(dp, axis)
        kps = sorted(fc.keyframe_points, key=lambda k: k.co.x)
        kmap = {int(k.co.x): k for k in kps if start_frame <= int(k.co.x) <= end_frame}
        _has_curve_data = len(kps) > 0
        for i, f in enumerate(frames):
            if f in kmap:
                kmap[f].co.y += deltas[i]
            else:
                if _has_curve_data:
                    base_val = fc.evaluate(f)
                else:
                    _override = base_overrides.get((bone_name, channel)) if base_overrides else None
                    base_val = _override[axis] if _override is not None else base_default
                new_kp = fc.keyframe_points.insert(f, base_val + deltas[i])
                new_kp.interpolation = "BEZIER"
                new_kp.easing = "AUTO"
                kmap[f] = new_kp
        fc.update()

    def _mod_bone_rot(bone_name, axis, deltas):
        _mod_bone_generic(bone_name, "rotation_euler", axis, deltas, 0.0)

    def _mod_bone_loc(bone_name, axis, deltas):
        _mod_bone_generic(bone_name, "location", axis, deltas, 0.0)

    def _mod_bone_scale(bone_name, axis, deltas):
        _mod_bone_generic(bone_name, "scale", axis, deltas, 1.0)

    # ── FILTRO: respiracion (equiv. Spine/Spine1 -> body2_1) ──
    if org.breathing_enabled:
        amp = org.breathing_amplitude
        speed = org.breathing_speed
        phase = org.breathing_phase
        deltas_x = [amp * math.sin(f * speed * 2 * math.pi + phase) for f in frames]
        deltas_z = [amp * 0.4 * math.sin(f * speed * 2 * math.pi + phase + 1.2) for f in frames]
        for bone in ORGANIC_SPINE_BONES:
            _mod_bone_rot(bone, 0, deltas_x)  # X
            _mod_bone_rot(bone, 2, deltas_z)  # Z

    # ── FILTRO: micro-movimiento de cabeza (equiv. Neck/face -> neck_1/head_1) ──
    if org.head_sway_enabled:
        amp = org.head_sway_amplitude
        speed = org.head_sway_speed
        seed = org.head_sway_seed
        for axis in range(3):
            deltas = [amp * _noise_at(f, speed, seed, axis) for f in frames]
            for bone in ORGANIC_HEAD_BONES:
                _mod_bone_rot(bone, axis, deltas)

    # ── FILTRO: desplazamiento de peso (equiv. Hips -> body1_1) ──
    if org.weight_shift_enabled:
        amp = org.weight_shift_amplitude
        speed = org.weight_shift_speed
        deltas_loc_x = [amp * math.sin(f * speed * 2 * math.pi) for f in frames]
        deltas_rot_z = [amp * 0.8 * math.cos(f * speed * 2 * math.pi) for f in frames]
        _mod_bone_loc(ORGANIC_HIPS_BONE, 0, deltas_loc_x)
        _mod_bone_rot(ORGANIC_HIPS_BONE, 2, deltas_rot_z)

    # ── FILTRO: noise en hombros (equiv. UpArm L/R -> leftArm_1/rightArm_1) ──
    if org.shoulder_noise_enabled:
        amp = org.shoulder_noise_amplitude
        speed = org.shoulder_noise_speed
        seed = org.shoulder_noise_seed
        for axis in range(3):
            for bone, s_off in ORGANIC_SHOULDER_BONES:
                deltas = [amp * _noise_at(f, speed, seed + s_off, axis) for f in frames]
                _mod_bone_rot(bone, axis, deltas)

    # ── FILTRO: micro-escala organica (equiv. Spine1 -> body2_1) ──
    if org.micro_scale_enabled:
        amp = org.micro_scale_amplitude
        speed = org.breathing_speed  # sincronizado con respiracion
        phase = org.breathing_phase
        deltas_s = [amp * math.sin(f * speed * 2 * math.pi + phase) for f in frames]
        for bone in ORGANIC_SPINE_BONES:
            _mod_bone_scale(bone, 2, deltas_s)  # escala Z

    # ── FILTRO: secondary motion (equiv. codos -> manos, rat_1 no tiene codo) ──
    if org.secondary_motion_enabled:
        lag = int(round(org.secondary_motion_lag))
        damping = org.secondary_motion_damping
        if _arm_action:
            action = _arm_action
            for bone in ORGANIC_SECONDARY_BONES:
                dp = f'pose.bones["{bone}"].rotation_euler'
                for axis in range(3):
                    fc = action.fcurves.find(dp, index=axis)
                    if fc is None:
                        continue
                    kps = sorted(fc.keyframe_points, key=lambda k: k.co.x)
                    kmap = {int(k.co.x): k for k in kps}
                    vals = [kmap[f].co.y if f in kmap else 0.0 for f in frames]
                    # Aplicar retardo: el bone sigue al movimiento principal con lag frames de retraso
                    delayed = [0.0] * n
                    for i in range(n):
                        src_i = max(0, i - lag)
                        delayed[i] = vals[src_i] * (1 - damping) + vals[i] * damping
                    # Blend: 30% delayed + 70% original para no romper la pose base
                    for i, f in enumerate(frames):
                        if f in kmap:
                            kmap[f].co.y = vals[i] * 0.7 + delayed[i] * 0.3
                    fc.update()

    # ── FILTRO: noise en posicion del root (equiv. objeto "alfred" -> "rat_1") ──
    if org.root_noise_enabled:
        root_obj = scene.objects.get(ORGANIC_ROOT_OBJECT)
        root_action = target_action_root
        if root_action is None and root_obj and root_obj.animation_data:
            root_action = root_obj.animation_data.action
        if root_action:
            strength = org.root_noise_strength
            freq = org.root_noise_frequency
            seed = org.root_noise_seed
            for axis in range(3):
                fc = root_action.fcurves.find("location", index=axis)
                if fc is None:
                    continue
                kps = sorted(fc.keyframe_points, key=lambda k: k.co.x)
                kmap = {int(k.co.x): k for k in kps}
                for i, f in enumerate(frames):
                    if f in kmap:
                        kmap[f].co.y += strength * _noise_at(f, freq, seed, axis)
                fc.update()
