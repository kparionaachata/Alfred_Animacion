
from .blender_compat import get_fcurves as _get_action_fcurves, new_fcurve as _new_fcurve

# -*- coding: utf-8 -*-
"""
operators_anim.py — Jerry Animation Studio v1.0
Operadores principales: Organic filters, CONCATENAR, ExportAnimation,
ImportAnimation, ExtractPose.
"""
import bpy, json, os, math, random
from datetime import datetime
from bpy.types import Operator
from bpy.props import StringProperty, IntProperty
from mathutils import Euler, Vector
from .constants import BONES_LISTA, BONES_LISTA_FULL, _BONE_DEFAULT, SECONDARY_ARMATURES
from .interpolation import apply_interp
from .pose_utils import (
    load_json_poses, get_pose_record, pose_record_to_full_dict,
    _lerp, build_segment_frames, invalidate_enum_cache,
    resolve_pose_start_frames,
)
from .properties import load_historia_json, get_key_points
from .pose_utils import get_orientacion_inicial
from . import object_import_utils as _oiu_preview


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

def _organic_item_range(item, start_frame, end_frame):
    """Devuelve el rango absoluto (frames de la escena/Blender) de un item
    organico (oreja, mandibula o emocion).

    FIX (Kebyn + Claude, 2026-08-24, segunda vuelta): la version anterior
    trataba de ADIVINAR si frame_start/frame_end eran relativos al segmento
    o absolutos de escena, comparandolos contra la duracion del segmento.
    Se probo con una config real (segmento "03_parada", frame_start=105,
    frame_end=604) y quedo confirmado que Kebyn tipea SIEMPRE los numeros
    que ve en la linea de tiempo de Blender (absolutos): el item de orejas
    de ese segmento tiene frame_start=105/frame_end=604 -- exactamente los
    limites absolutos del segmento -- y el primer item de emocion tiene
    frame_start=105, coincidiendo con el inicio absoluto del segmento.
    Cualquier heuristica que reinterprete esos numeros como "relativos" y
    les sume un offset (105+150-1=254 en vez de 150, etc.) mueve la
    oscilacion/emocion a un frame distinto del que Kebyn selecciono en la
    interfaz -- exactamente el bug reportado ("no respeta los frames
    seleccionados"). Por eso ahora esta funcion NO convierte nada: los
    frames que carga la UI son siempre absolutos y se devuelven tal cual.
    """
    return int(item.frame_start), int(item.frame_end)


def _apply_organic_filters(context, armature, start_frame, end_frame, org, filtered_bones=None):
    """
    Aplica filtros organicos sobre las fcurves ya generadas.
    Lee los valores de los keyframes existentes, les suma las micro-variaciones
    y escribe los valores modificados de vuelta a los mismos keyframes.
    """
    scene = context.scene
    filtered_bones = set(filtered_bones or ())
    frames = list(range(start_frame, end_frame + 1))
    n = len(frames)
    if n < 3:
        return

    # ── FILTRO: suavizado de fcurves ──
    if org.smooth_curves_enabled and armature.animation_data and armature.animation_data.action:
        action = armature.animation_data.action
        for fc in _get_action_fcurves(action):
            kps = sorted(fc.keyframe_points, key=lambda k: k.co.x)
            vals = [k.co.y for k in kps]
            for _ in range(org.smooth_passes):
                vals = _gaussian_smooth(vals, org.smooth_factor)
            for k, v in zip(kps, vals):
                k.co.y = v
            fc.update()

    # ── Funciones auxiliares para modificar pose bones por frame ──
    def _mod_bone_rot(bone_name, axis, deltas):
        """Suma deltas al bone, excepto si conserva la animación base."""
        if bone_name in filtered_bones:
            return
        if not armature.animation_data or not armature.animation_data.action:
            return
        dp   = f'pose.bones["{bone_name}"].rotation_euler'
        fc   = _get_action_fcurves(action).find(dp, index=axis)
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
        if bone_name in filtered_bones:
            return
        if not armature.animation_data or not armature.animation_data.action:
            return
        dp = f'pose.bones["{bone_name}"].location'
        fc = _get_action_fcurves(action).find(dp, index=axis)
        if fc is None:
            return
        kps  = sorted(fc.keyframe_points, key=lambda k: k.co.x)
        kmap = {int(k.co.x): k for k in kps if start_frame <= int(k.co.x) <= end_frame}
        for i, f in enumerate(frames):
            if f in kmap:
                kmap[f].co.y += deltas[i]
        fc.update()

    def _mod_bone_scale(bone_name, axis, deltas):
        if bone_name in filtered_bones:
            return
        if not armature.animation_data or not armature.animation_data.action:
            return
        dp = f'pose.bones["{bone_name}"].scale'
        fc = _get_action_fcurves(action).find(dp, index=axis)
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
        for bone in ("spine_1",):
            _mod_bone_rot(bone, 0, deltas_x)   # X
            _mod_bone_rot(bone, 2, deltas_z)   # Z

    # ── FILTRO: micro-movimiento de cabeza ──
    if org.head_sway_enabled:
        amp   = org.head_sway_amplitude
        speed = org.head_sway_speed
        seed  = org.head_sway_seed
        for axis in range(3):
            deltas = [amp * _noise_at(f, speed, seed, axis) for f in frames]
            for bone in ("spine_1",):
                _mod_bone_rot(bone, axis, deltas)

    # ── FILTRO: desplazamiento de peso (hips lateral) ──
    if org.weight_shift_enabled:
        amp   = org.weight_shift_amplitude
        speed = org.weight_shift_speed
        deltas_loc_x = [amp * math.sin(f * speed * 2 * math.pi) for f in frames]
        deltas_rot_z = [amp * 0.8 * math.cos(f * speed * 2 * math.pi) for f in frames]
        _mod_bone_loc("Dog_001_rig", 0, deltas_loc_x)
        _mod_bone_rot("Dog_001_rig", 2, deltas_rot_z)

    # ── FILTRO: noise en hombros ──
    if org.shoulder_noise_enabled:
        amp   = org.shoulder_noise_amplitude
        speed = org.shoulder_noise_speed
        seed  = org.shoulder_noise_seed
        for axis in range(3):
            for bone, s_off in (("front_shoulder.R", 0), ("front_shoulder.L", 17)):
                deltas = [amp * _noise_at(f, speed, seed + s_off, axis) for f in frames]
                _mod_bone_rot(bone, axis, deltas)

    # ── FILTRO: micro-escala organica ──
    if org.micro_scale_enabled:
        amp   = org.micro_scale_amplitude
        speed = org.breathing_speed  # sincronizado con respiracion
        phase = org.breathing_phase
        deltas_s = [amp * math.sin(f * speed * 2 * math.pi + phase) for f in frames]
        _mod_bone_scale("spine_1", 2, deltas_s)   # escala Z del body

    # ── FILTRO: secondary motion brazos (retardo de codos) ──
    if org.secondary_motion_enabled:
        lag     = int(round(org.secondary_motion_lag))
        damping = org.secondary_motion_damping
        if armature.animation_data and armature.animation_data.action:
            action = armature.animation_data.action
            for bone in ("front_shoulder.R", "front_shoulder.L"):
                dp = f'pose.bones["{bone}"].rotation_euler'
                for axis in range(3):
                    fc = _get_action_fcurves(action).find(dp, index=axis)
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

        # jerry no tiene cola — se aplica a tail_2 (oscilacion de lanza).
        # El rango queda clampeado a [-amp, +amp] = [-30°, +30°] en Z.
        tail_bones = [
            ("tail_2", 0.0),   # lanza — unico bone disponible
        ]

        # Los bones de la cola pueden no tener fcurves propias en la accion
        # (el usuario no los animo en las poses). Se crean aqui directamente
        # en lugar de usar _mod_bone_rot que silenciosamente ignora bones sin fcurve.
        if armature.animation_data and armature.animation_data.action:
            action = armature.animation_data.action
            for bone_name, bone_lag in tail_bones:
                dp = f'pose.bones["{bone_name}"].rotation_euler'
                # Obtener o crear la fcurve del eje Z (index=2)
                fc = _get_action_fcurves(action).find(dp, index=2)
                if fc is None:
                    fc = _new_fcurve(_get_action_fcurves(action), dp, index=2, action_group=bone_name)

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

    # ── FILTRO: oscilacion de orejas (ear.L / ear.R) ──
    if org.ear_osc_enabled and armature.animation_data and armature.animation_data.action:
        action = armature.animation_data.action
        _axis_map = {"X": 0, "Y": 1, "Z": 2}
        for item in org.ear_items:
            if not item.enabled:
                continue
            _item_start, _item_end = _organic_item_range(item, start_frame, end_frame)
            _item_start = max(start_frame, _item_start)
            _item_end = min(end_frame, _item_end)
            seg_frames = list(range(_item_start, _item_end + 1))
            if len(seg_frames) < 2:
                print(f"[JerryST] Oreja: intervalo '{item.label}' "
                      f"(frames absolutos {item.frame_start}->{item.frame_end}) "
                      f"cae fuera del rango absoluto real del segmento "
                      f"({start_frame}->{end_frame}) y se omitio.")
                continue
            ax = _axis_map.get(item.axis, 2)
            amp   = item.amplitude
            speed = item.speed
            for bone_name, phase in (("ear.L", item.phase_l), ("ear.R", item.phase_r)):
                dp = f'pose.bones["{bone_name}"].rotation_euler'
                fc = _get_action_fcurves(action).find(dp, index=ax)
                if fc is None:
                    fc = _new_fcurve(_get_action_fcurves(action), dp, index=ax, action_group=bone_name)
                # Limpiar keyframes anteriores del rango
                idxs = [i for i, kp in enumerate(fc.keyframe_points)
                        if _item_start <= int(kp.co.x) <= _item_end]
                for i in reversed(idxs):
                    fc.keyframe_points.remove(fc.keyframe_points[i])
                # Insertar nueva oscilacion
                for f in seg_frames:
                    val = amp * math.sin(f * speed * 2 * math.pi + phase)
                    fc.keyframe_points.insert(frame=f, value=val, options={"FAST"})
                for kp in fc.keyframe_points:
                    if _item_start <= int(kp.co.x) <= _item_end:
                        kp.interpolation = "BEZIER"
                        kp.easing = "AUTO"
                fc.update()

    # ── FILTRO: oscilacion de mandibula (jaw_bot) ──
    if org.jaw_osc_enabled and armature.animation_data and armature.animation_data.action:
        action = armature.animation_data.action
        import random as _rnd
        # jaw_bot solo se mueve rotando su eje X local: ese eje es relativo al
        # propio hueso (rest/roll), no al mundo, asi que abrir/cerrar la boca
        # es correcto sin importar hacia donde mire o rote el personaje.
        _JAW_AXIS_IDX = 0
        for item in org.jaw_items:
            if not item.enabled:
                continue
            _item_start, _item_end = _organic_item_range(item, start_frame, end_frame)
            _item_start = max(start_frame, _item_start)
            _item_end = min(end_frame, _item_end)
            seg_frames = list(range(_item_start, _item_end + 1))
            if len(seg_frames) < 2:
                print(f"[JerryST] Mandibula: intervalo '{item.label}' "
                      f"(frames absolutos {item.frame_start}->{item.frame_end}) "
                      f"cae fuera del rango absoluto real del segmento "
                      f"({start_frame}->{end_frame}) y se omitio. Revisa que el "
                      f"segmento cubra hasta el frame '{item.frame_end}'.")
                continue
            amp   = math.radians(item.amplitude)   # grados → radianes (0° a 30°)
            n_frames = max(1, _item_end - _item_start)
            speed = item.cycles / n_frames          # ciclos / frames → frecuencia
            phase = item.phase
            dp = 'pose.bones["jaw_bot"].rotation_euler'
            fc = _get_action_fcurves(action).find(dp, index=_JAW_AXIS_IDX)
            if fc is None:
                fc = _new_fcurve(_get_action_fcurves(action), dp, index=_JAW_AXIS_IDX, action_group="jaw_bot")
            # Limpiar rango (eje X, el unico usado)
            idxs = [i for i, kp in enumerate(fc.keyframe_points)
                        if _item_start <= int(kp.co.x) <= _item_end]
            for i in reversed(idxs):
                fc.keyframe_points.remove(fc.keyframe_points[i])
            # Limpiar residuos en Y/Z que pudieran quedar de intervalos
            # guardados antes de fijar el eje X (configs viejas con otro eje).
            for _stale_idx in (1, 2):
                _fc_stale = _get_action_fcurves(action).find(dp, index=_stale_idx)
                if _fc_stale is None:
                    continue
                _stale_kp = [i for i, kp in enumerate(_fc_stale.keyframe_points)
                             if _item_start <= int(kp.co.x) <= _item_end]
                for i in reversed(_stale_kp):
                    _fc_stale.keyframe_points.remove(_fc_stale.keyframe_points[i])
                _fc_stale.update()
            # Insertar segun patron

            # jaw_bot se abre en negativo: 0° cerrada → -30° abierta al maximo
            _rnd.seed(item.noise_seed)
            _prev_noise = 0.0
            for f in seg_frames:
                t = (f - _item_start) * speed
                if item.transition == "SINE":
                    raw = max(0.0, math.sin(t * 2 * math.pi + phase))
                elif item.transition == "TRIANGLE":
                    tt = (t + phase / (2 * math.pi)) % 1.0
                    raw = 1.0 - abs(2 * tt - 1)
                else:  # NOISE
                    target = _rnd.uniform(0.0, 1.0)
                    _prev_noise = _prev_noise * 0.7 + target * 0.3
                    raw = _prev_noise
                raw = max(0.0, min(1.0, raw))
                val = -amp * raw   # negativo: 0 (cerrada) → -amp (abierta)
                fc.keyframe_points.insert(frame=f, value=val, options={"FAST"})
            for kp in fc.keyframe_points:
                if _item_start <= int(kp.co.x) <= _item_end:
                    kp.interpolation = "BEZIER"
                    kp.easing = "AUTO"
            fc.update()


    # ── FILTRO: emociones (sejas_1_jerry / sejas_2_jerry) ──
    if org.emotion_enabled and armature.animation_data and armature.animation_data.action:
        action = armature.animation_data.action

        # Posicion BASE (A) capturada del rig en reposo.
        # Los bones pasan de A→B con el envelope como t (0=base, 1=emocion).
        _BASE = {
            "sejas_1_jerry": {
                "quat": (1.0, 0.0, 0.0, 0.0),
                "loc":  (0.006569,  0.000489, -0.000191),
            },
            "sejas_2_jerry": {
                "quat": (1.0, 0.0, 0.0, 0.0),
                "loc":  (0.013395, -0.000836,  0.003522),
            },
        }

        # Poses objetivo (B) por emocion — euler XYZ en radianes capturados del rig.
        _EMOTION_POSES = {
            "enojado": {
                "sejas_1_jerry": {"euler": ( 0.018057,  0.032724,  0.466682), "loc": (0.00746,  -0.011135,  0.000709)},
                "sejas_2_jerry": {"euler": ( 0.059813, -0.027015, -0.463214), "loc": (0.020687, -0.018262,  0.005866)},
            },
            "triste": {
                "sejas_1_jerry": {"euler": ( 0.002696, -0.051839, -0.649442), "loc": (0.008732, -0.027737,  0.001994)},
                "sejas_2_jerry": {"euler": (-0.046540,  0.063158,  0.554100), "loc": (0.020013, -0.031002,  0.003717)},
            },
            "sorprendido": {
                "sejas_1_jerry": {"euler": ( 0.001155, -0.049993, -0.613817), "loc": (0.019916, -0.009849, -0.000639)},
                "sejas_2_jerry": {"euler": (-0.047893,  0.064076,  0.570414), "loc": (0.010334, -0.010014,  0.000792)},
            },
            "levanta_la_ceja_derecha": {
                "sejas_1_jerry": {"euler": (-0.001606, -0.008090, -0.098054), "loc": (0.019472, -0.003857, -0.000569)},
                "sejas_2_jerry": {"euler": (-0.020113,  0.020089,  0.198146), "loc": (0.00855,  -0.031592,  0.002454)},
            },
            "levanta_la_ceja_izquierda": {
                "sejas_1_jerry": {"euler": (-0.002724, -0.014304, -0.180244), "loc": (0.016415, -0.030631,  0.001622)},
                "sejas_2_jerry": {"euler": (-0.020113,  0.020089,  0.198146), "loc": (0.01384,   0.000266,  0.000305)},
            },
        }

        _EMOTION_BONES = ("sejas_1_jerry", "sejas_2_jerry")

        def _slerp_ab(t, aw, ax, ay, az, bw, bx, by, bz):
            """Slerp de quat A hacia quat B con parametro t (0=A, 1=B)."""
            import math as _m
            dot = aw*bw + ax*bx + ay*by + az*bz
            if dot < 0.0:
                bw, bx, by, bz = -bw, -bx, -by, -bz
                dot = -dot
            dot = min(1.0, dot)
            if dot > 0.9995:
                rw = aw + t*(bw-aw)
                rx = ax + t*(bx-ax)
                ry = ay + t*(by-ay)
                rz = az + t*(bz-az)
            else:
                theta_0 = _m.acos(dot)
                theta   = theta_0 * t
                sin_t   = _m.sin(theta)
                sin_0   = _m.sin(theta_0)
                s0 = _m.cos(theta) - dot * sin_t / sin_0
                s1 = sin_t / sin_0
                rw = s0*aw + s1*bw
                rx = s0*ax + s1*bx
                ry = s0*ay + s1*by
                rz = s0*az + s1*bz
            mag = (rw*rw+rx*rx+ry*ry+rz*rz)**0.5
            if mag > 1e-8:
                rw/=mag; rx/=mag; ry/=mag; rz/=mag
            return (rw, rx, ry, rz)

        for em_item in org.emotion_items:
            if not em_item.enabled:
                continue
            pose_key  = em_item.emotion
            pose_data = _EMOTION_POSES.get(pose_key)
            if pose_data is None:
                continue

            # frame_start/frame_end son frames ABSOLUTOS de la escena/Blender
            # (ver _organic_item_range, Kebyn + Claude 2026-08-24).
            _em_start, _em_end = _organic_item_range(em_item, start_frame, end_frame)
            _f_in  = _em_start - em_item.transition_in   # base→emocion empieza
            _f0    = _em_start                           # emocion plena empieza
            _f1    = _em_end                             # emocion plena termina
            _f_out = _em_end + em_item.transition_out   # emocion→base termina
            _itp   = em_item.interp_type

            if _f1 <= _f0:
                continue

            for bone_name in _EMOTION_BONES:
                bpose = pose_data.get(bone_name)
                if bpose is None:
                    continue
                bbase = _BASE[bone_name]

                al = bbase["loc"]
                bl = bpose["loc"]
                ae = (0.0, 0.0, 0.0)
                be = bpose["euler"]

                dp_euler = f'pose.bones["{bone_name}"].rotation_euler'
                dp_loc   = f'pose.bones["{bone_name}"].location'

                def _insert_4kf(fc, v_base, v_emo):
                    """Inserta 4 keyframes: entrada base, inicio emocion, fin emocion, salida base."""
                    _rng_lo = min(_f_in, _f0, _f1, _f_out)
                    _rng_hi = max(_f_in, _f0, _f1, _f_out)
                    idxs = [i for i, kp in enumerate(fc.keyframe_points)
                            if _rng_lo <= int(kp.co.x) <= _rng_hi]
                    for i in reversed(idxs):
                        fc.keyframe_points.remove(fc.keyframe_points[i])
                    # 4 keyframes: base_in, emocion_start, emocion_end, base_out
                    fc.keyframe_points.insert(frame=_f_in,  value=v_base, options={"FAST"})
                    fc.keyframe_points.insert(frame=_f0,    value=v_emo,  options={"FAST"})
                    fc.keyframe_points.insert(frame=_f1,    value=v_emo,  options={"FAST"})
                    fc.keyframe_points.insert(frame=_f_out, value=v_base, options={"FAST"})
                    for kp in fc.keyframe_points:
                        if _rng_lo <= int(kp.co.x) <= _rng_hi:
                            kp.interpolation = "BEZIER"
                            kp.easing        = "AUTO"
                    fc.update()

                # ── rotation_euler ──
                for axis_idx in range(3):
                    fc = _get_action_fcurves(action).find(dp_euler, index=axis_idx)
                    if fc is None:
                        fc = _new_fcurve(_get_action_fcurves(action), dp_euler, index=axis_idx, action_group=bone_name)
                    _insert_4kf(fc, ae[axis_idx], be[axis_idx])

                # ── location ──
                for axis_idx in range(3):
                    fc = _get_action_fcurves(action).find(dp_loc, index=axis_idx)
                    if fc is None:
                        fc = _new_fcurve(_get_action_fcurves(action), dp_loc, index=axis_idx, action_group=bone_name)
                    _insert_4kf(fc, al[axis_idx], bl[axis_idx])

    # ── FILTRO: noise en posicion del root ──
    if org.root_noise_enabled:
        root_obj = scene.objects.get("jerry")
        if root_obj and root_obj.animation_data and root_obj.animation_data.action:
            root_action = root_obj.animation_data.action
            strength = org.root_noise_strength
            freq     = org.root_noise_frequency
            seed     = org.root_noise_seed
            for axis in range(3):
                fc = _get_action_fcurves(root_action).find("location", index=axis)
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

class JRRST_OT_Concatenate(Operator):
    bl_idname    = "jerryst.concatenate"
    bl_label     = "CONCATENAR"
    bl_description = "Genera la animacion interpolando las poses en la timeline"
    bl_options   = {"REGISTER", "UNDO"}

    # FIX (Kebyn, 2026-08-12): antes este operador SOLO leia segs.active_index
    # para saber sobre que segmento operar, y active_index nunca se
    # actualizaba al expandir el panel de configuracion de otro segmento en
    # la lista (jerryseg.toggle_config) -- solo cambiaba al crear/duplicar/
    # eliminar segmentos. Resultado: sin importar que segmento expandieras
    # (2, 5, el que sea) y le dieras a CONCATENAR, siempre se concatenaba el
    # ULTIMO segmento creado (que es el que dejaba active_index apuntado).
    # Se agrega item_idx (mismo patron item_idx=-1 que ya usan el resto de
    # los operadores por-segmento de operators_segments.py) para que el
    # boton de CADA segmento en el panel pueda pasar explicitamente SU
    # PROPIO indice, sin depender de que active_index este sincronizado.
    item_idx: bpy.props.IntProperty(
        default=-1,
        description="Indice del segmento sobre el que operar. -1 = usar segs.active_index",
    )

    def execute(self, context):
        st    = context.scene.jerryst
        scene = context.scene

        entry_ratio = st.entry_ratio
        exit_ratio  = st.exit_ratio

        # ── Leer frame_start y frame_end del segmento activo ─────────────────
        # Cada segmento define su propio intervalo dentro del recorrido.
        # CONCATENAR genera la animacion DENTRO de ese intervalo.
        segs = getattr(scene, "jerry_segs", None)
        _active_seg = None
        if segs and len(segs.segments) > 0:
            if 0 <= self.item_idx < len(segs.segments):
                idx = self.item_idx
            else:
                idx = max(0, min(segs.active_index, len(segs.segments) - 1))
            segs.active_index = idx
            _active_seg = segs.segments[idx]

        if _active_seg is None:
            self.report({"ERROR"}, "No hay segmento activo. Crea un segmento en el Paso 3 antes de concatenar.")
            return {"CANCELLED"}

        start_frame   = _active_seg.frame_start

        # ── Calcular seg_frame_end real en modo 1 coordenada ─────────────────
        # En modo single_coord_mode el frame_end del segmento es provisional
        # (igual a frame_start) hasta que CONCATENAR lo calcula.
        # Se reconstruye aqui sumando las duraciones de poses para que el clip
        # de "no escribir mas alla" sea correcto y no corte la animacion a 1 frame.
        if _active_seg.single_coord_mode:
            # NOTA (Kebyn, 2026-08-06): seg.pose_start_duration/pose_end_duration
            # ya no existen (ver refactor pose_inicio/pose_fin -> action_poses,
            # igual que en Alfred). El primer y ultimo item de action_poses son
            # ahora las anclas de inicio/fin y consumen su propia duracion, asi
            # que el total es simplemente la suma de TODAS las duraciones.
            _dur_total = sum(_ap.duration for _ap in _active_seg.action_poses)
            _dur_total = max(_dur_total, 2)
            seg_frame_end = start_frame + _dur_total - 1
        else:
            seg_frame_end = _active_seg.frame_end   # limite maximo del segmento

        # ── Sincronizar configuracion del segmento activo → st (jerryst) ─────
        # NOTA (Kebyn, 2026-08-06): el sistema de "Pose INICIO"/"Pose FIN" propio
        # del segmento (seg.pose_start_*/seg.pose_end_*) ya no existe -- se
        # elimino junto con pose_inicio/pose_fin (mismo refactor ya aplicado en
        # Alfred). `action_poses` es ahora la unica fuente de datos: el primer
        # y el ultimo item cumplen el rol de anclas de inicio/fin, y TODOS los
        # items (incluidos primero y ultimo) consumen su propia duracion como
        # segmentos reales -- ya no hay un tramo de "hold" estatico separado
        # (los antiguos dur_ini/dur_fin basados en pose_start_duration/
        # pose_end_duration se eliminaron mas abajo).
        _ap_list = list(_active_seg.action_poses)
        if not _ap_list:
            # SEGMENTO SIN POSES (Kebyn, 2026-08-12): CONCATENAR ya no debe
            # exigir poses configuradas para poder reproducirse. Un segmento
            # es valido si solo tiene recorrido + filtros organicos +
            # oscilaciones, sin ninguna pose de accion inyectada sobre los
            # bones -- exactamente el mismo caso que ya soporta
            # "Concatenar segmentos" (jerryseg.concatenate_all) a traves de
            # _bake_organic_only_segment() en operators_segments.py. Se
            # reutiliza esa misma funcion aca para que el boton CONCATENAR
            # individual del segmento tenga el mismo comportamiento en vez
            # de bloquearse con un error.
            from .operators_segments import _bake_organic_only_segment

            if not st.armature_name:
                self.report({"ERROR"}, "Selecciona el armature de Jerry primero")
                return {"CANCELLED"}
            armature = scene.objects.get(st.armature_name)
            if not armature or armature.type != "ARMATURE":
                self.report({"ERROR"}, f"Dog_001_rig '{st.armature_name}' no valido")
                return {"CANCELLED"}

            _seg_end_np = seg_frame_end if seg_frame_end > start_frame else start_frame + 1

            try:
                # _bake_organic_only_segment aplica tanto filtros organicos
                # como oscilaciones de bones (ver operators_segments.py,
                # Kebyn 2026-08-12) sobre la pose evaluada del recorrido base.
                _organic_ok = _bake_organic_only_segment(
                    context, _active_seg, armature, start_frame, _seg_end_np
                )
            except Exception as e_org:
                self.report({"ERROR"}, f"Fallo al aplicar filtros/oscilaciones ({e_org})")
                return {"CANCELLED"}

            if not _organic_ok:
                self.report(
                    {"WARNING"},
                    "Este segmento no tiene poses ni filtros organicos activos: "
                    "no hay nada que hornear. Activa 'Filtros organicos' en el "
                    "segmento, agrega oscilaciones, o agrega poses en el Paso 3."
                )
                return {"FINISHED"}

            scene.frame_set(start_frame)
            st.status_msg = (
                f"Segmento '{_active_seg.label}' sin poses: recorrido + filtros "
                f"organicos + oscilaciones aplicados ({start_frame}->{_seg_end_np})."
            )
            self.report({"INFO"}, st.status_msg)
            return {"FINISHED"}

        _ap_first = _ap_list[0]
        _ap_last  = _ap_list[-1]

        st.pose_start_file     = _ap_first.json_file
        st.pose_start_idx      = 0
        st.pose_start_name     = _ap_first.pose_name
        st.pose_start_duration = _ap_first.duration
        st.pose_start_interp   = _ap_first.interp_type
        st.pose_start_rot_x    = _ap_first.rot_x
        st.pose_start_rot_y    = _ap_first.rot_y
        st.pose_start_rot_z    = _ap_first.rot_z
        st.pose_start_pos_x    = _ap_first.pos_x
        st.pose_start_pos_y    = _ap_first.pos_y
        st.pose_start_pos_z    = _ap_first.pos_z

        st.pose_end_file     = _ap_last.json_file
        st.pose_end_idx      = 0
        st.pose_end_name     = _ap_last.pose_name
        st.pose_end_duration = _ap_last.duration
        st.pose_end_interp   = _ap_last.interp_type
        st.pose_end_rot_x    = _ap_last.rot_x
        st.pose_end_rot_y    = _ap_last.rot_y
        st.pose_end_rot_z    = _ap_last.rot_z
        st.pose_end_pos_x    = _ap_last.pos_x
        st.pose_end_pos_y    = _ap_last.pos_y
        st.pose_end_pos_z    = _ap_last.pos_z

        # Se copia la lista COMPLETA (no solo los items intermedios): el primer
        # y ultimo item tambien deben generar su propio segmento con su propia
        # duracion mas abajo, en vez de quedar reducidos a un simple punto de
        # anclaje sin duracion propia.
        st.action_poses.clear()
        for src in _ap_list:
            dst = st.action_poses.add()
            dst.json_file   = src.json_file
            dst.pose_label  = src.pose_label
            dst.pose_name   = src.pose_name
            dst.duration    = src.duration
            dst.entry_ratio = src.entry_ratio
            dst.exit_ratio  = src.exit_ratio
            dst.interp_type = src.interp_type
            dst.rot_x = src.rot_x
            dst.rot_y = src.rot_y
            dst.rot_z = src.rot_z
            dst.pos_x = src.pos_x
            dst.pos_y = src.pos_y
            dst.pos_z = src.pos_z
            dst.manual_start    = getattr(src, "manual_start", False)
            dst.frame_abs_start = getattr(src, "frame_abs_start", 0)
        entry_ratio = _active_seg.entry_ratio if _active_seg.entry_ratio > 0 else st.entry_ratio
        exit_ratio  = _active_seg.exit_ratio  if _active_seg.exit_ratio  > 0 else st.exit_ratio

        # ── Detectar modo recorrido (>1 coordenada) ──────────────────────────
        # Si el path_recorder tiene mas de 1 punto, la posicion XYZ del root
        # ya esta definida por el recorrido generado en el Paso 2.
        # En ese caso NO usamos los pos_x/y/z de la configuracion de poses.
        pc = getattr(scene, "jerry_path", None)
        _recorrido_activo = pc is not None and len(pc.path_points) > 1

        # Pre-capturar posiciones del recorrido frame a frame desde el Empty
        # jerry (que tiene la animacion del Paso 2 en sus fcurves).
        # Se hace ANTES de tocar la timeline para no perder datos.
        _recorrido_pos = {}   # frame -> (x, y, z)
        _recorrido_rot = {}   # frame -> (rx, ry, rz)  en radianes
        if _recorrido_activo:
            _root_empty = scene.objects.get("jerry")
            if _root_empty and _root_empty.animation_data and _root_empty.animation_data.action:
                _root_act = _root_empty.animation_data.action
                # Evaluar fcurves de location y rotation_euler en cada frame del rango
                _fc_loc = [_get_action_fcurves(_root_act).find("location", index=i) for i in range(3)]
                _fc_rot = [_get_action_fcurves(_root_act).find("rotation_euler", index=i) for i in range(3)]
                # Rango: desde start_frame hasta anim_frame_fin (o frame_end de escena)
                _f_fin = getattr(pc, "anim_frame_fin", scene.frame_end)
                for _f in range(start_frame, _f_fin + 1):
                    _recorrido_pos[_f] = tuple(
                        fc.evaluate(_f) if fc else 0.0 for fc in _fc_loc
                    )
                    _recorrido_rot[_f] = tuple(
                        fc.evaluate(_f) if fc else 0.0 for fc in _fc_rot
                    )

        if not st.armature_name:
            self.report({"ERROR"}, "Selecciona el armature de Jerry primero")
            return {"CANCELLED"}
        armature = scene.objects.get(st.armature_name)
        if not armature or armature.type != "ARMATURE":
            self.report({"ERROR"}, f"Dog_001_rig '{st.armature_name}' no valido")
            return {"CANCELLED"}
        if not st.pose_start_file:
            self.report({"ERROR"}, "Selecciona la pose de INICIO en la configuracion del segmento activo")
            return {"CANCELLED"}
        if not st.pose_end_file:
            self.report({"ERROR"}, "Selecciona la pose de FIN en la configuracion del segmento activo")
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

        # Frame de inicio resuelto de cada pose (respeta manual_start; ver
        # resolve_pose_start_frames en pose_utils.py). PORTADO desde
        # alfred_animation_studio (Kebyn, 2026-08-06). Se calcula ACA (antes
        # de tocar la timeline / borrar la action) porque tambien se usa
        # para saber hasta donde capturar la Capa 1 (ver bloque de captura
        # mas abajo, antes de borrar la action).
        _pose_starts = (
            resolve_pose_start_frames(action_items, start_frame)
            if action_items else [start_frame]
        )
        for _item, _fs in zip(action_items, _pose_starts):
            _item.frame_abs_start = _fs
        # Propagar frame_abs_start también a seg.action_poses (JerrySegmentPoseSlot)
        # para que el panel lo pueda leer directamente desde el segmento.
        for _ii, _sit in enumerate(_active_seg.action_poses):
            if _ii < len(_pose_starts):
                _sit.frame_abs_start = _pose_starts[_ii]

        # NOTA (Kebyn, 2026-08-06): se elimino el tramo de "hold" estatico
        # basado en pose_start_duration (dur_ini) -- la pose de inicio ya no
        # se sostiene aparte: es el primer item de action_poses y genera su
        # propio segmento con su propia duracion dentro del bucle de abajo.
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

        # NOTA (Kebyn, 2026-08-06): idem para pose_end_duration (dur_fin) -- la
        # pose de fin es el ultimo item de action_poses y ya genero su propio
        # segmento con su propia duracion en el bucle de arriba.
        if not segments:
            self.report({"ERROR"}, "No hay segmentos validos para concatenar")
            return {"CANCELLED"}

        context.view_layer.objects.active = armature
        if armature.mode != "POSE":
            bpy.ops.object.mode_set(mode="POSE")
        for pb in armature.pose.bones:
            pb.rotation_mode = "XYZ"
        armature.rotation_mode = "XYZ"

        # ── CAPTURA DE CAPA 1 (desplazamiento base ya horneado: caminar /
        # saltar / parada) ANTES de borrar la action. ────────────────────
        # PORTADO desde alfred_animation_studio (Kebyn, 2026-08-06): "los
        # bones no involucrados en el hueco antes/despues de una pose con
        # frame de inicio manual aparecen en posicion T en vez de seguir
        # caminando con normalidad". Causa: el bloque de abajo borra la
        # action COMPLETA del armature (Capa 1, horneada por
        # jerrypr.preview_path) y reconstruye el segmento SOLO a partir de
        # las poses configuradas -- en cualquier frame donde ninguna pose
        # cubre ese instante (antes de la primera pose si tiene manual_start
        # a un frame posterior, o despues de la ultima si termina antes de
        # seg_frame_end), no queda ningun rastro del caminar base y los
        # bones vuelven a su rest pose (T). Las poses deben INYECTARSE sobre
        # la animacion base, no reemplazarla entera.
        #
        # Fix: antes de borrar nada, se evalua/captura frame a frame lo que
        # YA esta horneado (Capa 1, o lo que sea que este activo -- accion
        # directa o NLA evaluado) en todo el rango util del segmento (hasta
        # donde llegan las poses configuradas, o hasta seg_frame_end si es
        # mayor). Mas abajo, los tramos "sin pose" (antes de la primera /
        # despues de la ultima) usan estos valores capturados frame a frame
        # en vez de un rest pose fijo -- asi el personaje sigue caminando
        # con normalidad hasta que entra la primera pose, y retoma el
        # caminar al salir de la ultima.
        _poses_end_estimate = (
            _pose_starts[-1] + action_items[-1].duration - 1
            if _pose_starts and action_items else start_frame
        )
        _cap_end_frame = max(start_frame, _poses_end_estimate, seg_frame_end)

        _base_cap_bones   = {}   # abs_f -> {bone: {"rot":..,"loc":..,"scale":..}}
        _base_cap_arm_rot = {}   # abs_f -> (rx,ry,rz)
        _base_cap_arm_pos = {}   # abs_f -> (x,y,z)
        _have_base_cap    = False

        if armature.animation_data:
            _root_for_cap     = bpy.data.objects.get("jerry")
            _frame_backup_cap = scene.frame_current
            for _cf in range(start_frame, _cap_end_frame + 1):
                scene.frame_set(_cf)
                _fb = {}
                for _bn in BONES_LISTA_FULL:
                    _pb_cap = armature.pose.bones.get(_bn)
                    if _pb_cap:
                        _fb[_bn] = {
                            "rot":   tuple(_pb_cap.rotation_euler),
                            "loc":   tuple(_pb_cap.location),
                            "scale": tuple(_pb_cap.scale),
                        }
                if _fb:
                    _base_cap_bones[_cf] = _fb
                    _have_base_cap = True
                if _root_for_cap:
                    _base_cap_arm_rot[_cf] = tuple(_root_for_cap.rotation_euler)
                    _base_cap_arm_pos[_cf] = tuple(_root_for_cap.location)
            scene.frame_set(_frame_backup_cap)

        if armature.animation_data and armature.animation_data.action:
            old_action = armature.animation_data.action
            armature.animation_data.action = None
            bpy.data.actions.remove(old_action)
        if not armature.animation_data:
            armature.animation_data_create()

        # ── Limpiar keyframes del root solo en modo estatico ──────────────────
        # En modo recorrido (>1 coordenada) la accion del jerry contiene
        # el recorrido generado en el Paso 2. NO se borra — la configuracion de
        # poses se superpone SOLO en los bones del armature.
        _root_cleanup = bpy.data.objects.get("jerry")
        if not _recorrido_activo:
            # Modo estatico: limpiar la accion del root normalmente
            if _root_cleanup and _root_cleanup.animation_data:
                if _root_cleanup.animation_data.action:
                    _old_root = _root_cleanup.animation_data.action
                    _root_cleanup.animation_data.action = None
                    bpy.data.actions.remove(_old_root)
                for _trk in list(_root_cleanup.animation_data.nla_tracks):
                    _root_cleanup.animation_data.nla_tracks.remove(_trk)
        # else: en modo recorrido se conserva intacta la accion del root

        # Limpiar NLA tracks del armature de bones
        # En modo recorrido: PRESERVAR los tracks del recorrido (Slot_*_arm).
        # La configuracion se escribe directamente en la seg_action del segmento
        # (que ya contiene el desplazamiento).  Se elimina cualquier JRRST_Config_*
        # previo del NLA porque ya no se usa esa arquitectura.
        # En modo estatico: limpiar todo normalmente.
        if _recorrido_activo:
            # Obtener la seg_action del segmento activo para escribir la config ahi
            _seg_action_name = getattr(_active_seg, "seg_action_name", "")
            _seg_action = bpy.data.actions.get(_seg_action_name) if _seg_action_name else None
            if _seg_action is None:
                # Si no existe (segmento creado sin recorrido previo), crearla ahora
                _seg_action_name = f"jerryseg_{_active_seg.label.replace(' ','_')}"
                _seg_action = bpy.data.actions.get(_seg_action_name)
                if _seg_action is None:
                    _seg_action = bpy.data.actions.new(name=_seg_action_name)
                _active_seg.seg_action_name = _seg_action_name

            # Limpiar fcurves de config previos en la seg_action
            # (los de bones configurados, pero NO los de desplazamiento del root)
            _root_bone_name = armature.name  # "Dog_001_rig"
            _disp_prefixes = (
                f'pose.bones["{_root_bone_name}"].location',
                f'pose.bones["{_root_bone_name}"].rotation_euler',
            )
            _fcurves_to_remove = [
                fc for fc in list(_get_action_fcurves(_seg_action))
                if not any(fc.data_path.startswith(dp) for dp in _disp_prefixes)
            ]
            for _fc in _fcurves_to_remove:
                _get_action_fcurves(_seg_action).remove(_fc)

            # Desconectar cualquier action directa y eliminar tracks JRRST_Config_* obsoletos
            if armature.animation_data and armature.animation_data.action:
                _old_direct = armature.animation_data.action
                armature.animation_data.action = None
                if _old_direct and _old_direct != _seg_action and not _old_direct.name.startswith("Slot_"):
                    bpy.data.actions.remove(_old_direct)
            if armature.animation_data:
                for _trk in list(armature.animation_data.nla_tracks):
                    if _trk.name.startswith("JRRST_Config_"):
                        armature.animation_data.nla_tracks.remove(_trk)

            # Asignar seg_action como action activa para recibir los keyframes de config
            armature.animation_data.action = _seg_action

        else:
            # Modo estatico: limpiar todo
            if armature.animation_data:
                if armature.animation_data.action:
                    _old_act = armature.animation_data.action
                    armature.animation_data.action = None
                    bpy.data.actions.remove(_old_act)
                for _trk in list(armature.animation_data.nla_tracks):
                    armature.animation_data.nla_tracks.remove(_trk)

        # Limpiar keyframes previos de los armatures secundarios (shield y spear)
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
        #
        # PORTADO desde alfred_animation_studio (Kebyn, 2026-08-06): si la
        # primera pose tiene manual_start a un frame mas tarde que start_frame
        # (ver _pose_starts, resolve_pose_start_frames en pose_utils.py), NO
        # se siembra el primer waypoint en start_frame con los valores de la
        # primera pose -- eso haria que el personaje ya aparezca en esa pose
        # desde el frame 1 del segmento, ignorando el hueco pedido. Ese hueco
        # se llena con el caminar base capturado (Capa 1, ver bloque de
        # captura mas arriba, antes de borrar la action), escrito frame a
        # frame directamente en el loop de escritura de mas abajo (busca
        # "_first_pose_gap"). Si no hay manual_start en la primera pose (el
        # caso de siempre), _pose_starts[0] == start_frame y el
        # comportamiento es IDENTICO al de antes.
        _first_pose_gap   = max(0, _pose_starts[0] - start_frame) if _pose_starts else 0
        _first_seg_interp = segments[0][4] if segments else "SMOOTH"

        if _first_pose_gap > 0:
            _gap_anchor_bones = (
                _base_cap_bones.get(_pose_starts[0]) if _have_base_cap else None
            ) or {bone: dict(_BONE_DEFAULT) for bone in BONES_LISTA_FULL}
            _gap_anchor_arm_rot = (
                _base_cap_arm_rot.get(_pose_starts[0]) if _have_base_cap else None
            ) or (0.0, 0.0, 0.0)
            _gap_anchor_arm_pos = (
                _base_cap_arm_pos.get(_pose_starts[0]) if _have_base_cap else None
            ) or (0.0, 0.0, 0.0)
            waypoints = [
                (start_frame,      _gap_anchor_bones, _first_seg_interp),
                (_pose_starts[0],  _gap_anchor_bones, _first_seg_interp),
            ]
            arm_waypoints = [
                (start_frame,      _gap_anchor_arm_rot, _first_seg_interp),
                (_pose_starts[0],  _gap_anchor_arm_rot, _first_seg_interp),
            ]
            pos_waypoints = [
                (start_frame,      _gap_anchor_arm_pos, _first_seg_interp),
                (_pose_starts[0],  _gap_anchor_arm_pos, _first_seg_interp),
            ]
        else:
            waypoints     = [(start_frame, d_start,       _first_seg_interp)]
            arm_waypoints = [(start_frame, arm_rot_start,  _first_seg_interp)]
            pos_waypoints = [(start_frame, arm_pos_start,  _first_seg_interp)]

        cursor = start_frame
        for idx_seg, ((d_s, d_a, d_e, n_frames, seg_interp),
                      (ar_s, ar_a, ar_e, _, _arm_interp),
                      (ap_s, ap_a, ap_e, _, _pos_interp)) in \
                enumerate(zip(segments, seg_arm_rots, seg_arm_pos)):
            cursor = _pose_starts[idx_seg] if idx_seg < len(_pose_starts) else cursor
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
        # Respetar el limite del segmento: no escribir mas alla de seg_frame_end
        if end_frame > seg_frame_end:
            end_frame = seg_frame_end
            total_gen = end_frame - start_frame + 1
        waypoints.append((end_frame, d_end, st.pose_end_interp))
        arm_waypoints.append((end_frame, arm_rot_end, st.pose_end_interp))
        pos_waypoints.append((end_frame, arm_pos_end, st.pose_end_interp))

        # PORTADO desde alfred_animation_studio (Kebyn, 2026-08-06),
        # simetrico al del hueco inicial: si la ultima pose termina antes de
        # que acabe el segmento real (seg_frame_end), ese tramo final
        # tambien debe seguir caminando en vez de quedar congelado en la
        # ultima pose. _pose_end_frame marca hasta donde llega la
        # interpolacion de poses (_pose_at_frame); el loop de escritura de
        # mas abajo usa la captura de Capa 1 (no _pose_at_frame) para el
        # tramo entre _pose_end_frame y seg_frame_end.
        _pose_end_frame = end_frame

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

        # ── En modo recorrido: mutar temporalmente los NLA tracks del recorrido ──
        # Durante la escritura de keyframes de la config, los NLA tracks del recorrido
        # deben estar mutados para que frame_set() no interfiera con la evaluacion de poses.
        # Se restauran al terminar.
        _muted_tracks = []
        if _recorrido_activo and armature.animation_data:
            for _trk in armature.animation_data.nla_tracks:
                if not _trk.mute:
                    _trk.mute = True
                    _muted_tracks.append(_trk)

        # Escribir keyframes — bones + rotacion + posicion del root
        # FILTRO DE BONES: los bones marcados en seg.filter_* NO reciben
        # keyframes de configuracion. Su animacion viene del recorrido base
        # (generado por "Reproducir recorrido"). Por defecto las patas estan
        # filtradas; el usuario puede cambiar esto en "Filtrar bones" del segmento.
        _BONE_FILTER_MAP = {
            "spine_6":           "filter_spine_6",
            "spine_7":           "filter_spine_7",
            "Dog_001_rig":       "filter_main_bone",

            "front_shoulder.L":  "filter_left_arm",
            "front_shoulder.R":  "filter_right_arm",
            "front_thigh.L":     "filter_front_thigh_l",
            "front_thigh.R":     "filter_front_thigh_r",
            "front_shin.L":      "filter_front_shin_l",
            "front_shin.R":      "filter_front_shin_r",
            "front_foot.L":      "filter_front_foot_l",
            "front_foot.R":      "filter_front_foot_r",
            "front_toe.L":       "filter_front_toe_l",
            "front_toe.R":       "filter_front_toe_r",
            "shoulder.R":        "filter_right_leg",
            "shoulder.L":        "filter_left_leg",
            "thigh.L":           "filter_thigh_l",
            "thigh.R":           "filter_thigh_r",
            "shin.L":            "filter_shin_l",
            "shin.R":            "filter_shin_r",
            "foot.L":            "filter_foot_l",
            "foot.R":            "filter_foot_r",
            "toe.L":             "filter_toe_l",
            "toe.R":             "filter_toe_r",
            "tail_1":            "filter_shield",
            "tail_2":            "filter_spear",
            "tail_3":            "filter_tail_3",
            "jaw_bot":           "filter_jaw_bot",
            "jaw_top":           "filter_jaw_top",
            "scull":             "filter_scull",
            "scull_1":           "filter_scull_1",
            "ear.L":             "filter_ear_l",
            "ear.R":             "filter_ear_r",
            "sombrero":          "filter_sombrero",
            "sejas_1_jerry":     "filter_sejas_1",
            "sejas_2_jerry":     "filter_sejas_2",
            "no_bone_01":        "filter_no_bone_01",
            "no_bone_02":        "filter_no_bone_02",
            "no_bone_03":        "filter_no_bone_03",
            "no_bone_04":        "filter_no_bone_04",
        }
        # Construir set de bones filtrados segun las propiedades del segmento activo
        _FILTERED_BONES = {
            bone for bone, prop in _BONE_FILTER_MAP.items()
            if getattr(_active_seg, prop, False)
        }

        # PORTADO desde alfred_animation_studio (Kebyn, 2026-08-08): ademas
        # del bloqueo total (_FILTERED_BONES, checkbox simple), un bone
        # puede tener intervalos de frames especificos ("dividir en
        # partes" el bloqueo). Import local para evitar import circular
        # (operators_segments.py ya importa de este mismo archivo).
        from .operators_segments import _bone_blocked_in_intervals as _bone_blocked_in_intervals_seg

        # Purgar fcurves existentes de bones filtrados en la action activa
        # (residuo de ejecuciones anteriores de CONCATENAR)
        _active_action = armature.animation_data.action if armature.animation_data else None
        if _active_action and _FILTERED_BONES:
            _fcs_to_remove = [
                fc for fc in list(_get_action_fcurves(_active_action))
                if any(f'pose.bones["{bn}"]' in fc.data_path for bn in _FILTERED_BONES)
            ]
            for _lfc in _fcs_to_remove:
                _get_action_fcurves(_active_action).remove(_lfc)

        _full_end = seg_frame_end  # siempre el limite del segmento
        # PORTADO desde alfred_animation_studio (Kebyn, 2026-08-06): en los
        # tramos SIN pose (antes de _pose_starts[0], o despues de
        # _pose_end_frame si el segmento sigue mas alla) se usa la captura
        # de Capa 1 frame a frame en vez de _pose_at_frame/_arm_*_at_frame
        # -- esas funciones solo interpolan ENTRE waypoints (linea recta),
        # lo que en el tramo del hueco daria un valor congelado (el mismo
        # en todos los frames del hueco). La captura, en cambio, ya tiene el
        # caminar real de cada frame.
        for abs_f in range(start_frame, _full_end + 1):
            _in_gap = _have_base_cap and (
                (_pose_starts and abs_f < _pose_starts[0]) or abs_f > _pose_end_frame
            )
            if _in_gap and abs_f in _base_cap_bones:
                pose    = _base_cap_bones[abs_f]
                arm_rot = _base_cap_arm_rot.get(abs_f, (0.0, 0.0, 0.0))
                arm_pos = _base_cap_arm_pos.get(abs_f, (0.0, 0.0, 0.0))
            elif _in_gap and _base_cap_bones:
                # SALVAGUARDA: si este frame exacto no quedo en la captura
                # (no deberia pasar, _cap_end_frame cubre todo el rango),
                # usar el frame capturado MAS CERCANO en vez de caer al
                # "else" de abajo -- ese "else" es _pose_at_frame(abs_f), que
                # mas alla del ultimo waypoint real devuelve SIEMPRE el
                # valor fijo de la ultima pose (d_end), exactamente el
                # "queda pegado en la ultima pose" que se queria evitar.
                _nearest_f = min(_base_cap_bones.keys(), key=lambda k: abs(k - abs_f))
                pose    = _base_cap_bones[_nearest_f]
                arm_rot = _base_cap_arm_rot.get(_nearest_f, (0.0, 0.0, 0.0))
                arm_pos = _base_cap_arm_pos.get(_nearest_f, (0.0, 0.0, 0.0))
            else:
                pose    = _pose_at_frame(abs_f)
                arm_rot = _arm_rot_at_frame(abs_f)
                arm_pos = _arm_pos_at_frame(abs_f)
            # PERF (Kebyn/Claude, 2026-08-24): scene.frame_set(abs_f) aca
            # forzaba una evaluacion COMPLETA del depsgraph por cada frame
            # del segmento (400 frames en el caso reportado), aunque
            # pose/arm_rot/arm_pos ya vienen resueltos por matematica pura
            # (interpolacion entre waypoints o lectura de _base_cap_bones,
            # ambos precalculados arriba) y keyframe_insert(frame=abs_f) ya
            # es explicito sobre el frame -- no depende de donde este el
            # playhead. Era el grueso del tiempo que tardaba CONCATENAR en
            # segmentos largos (ver 03_parada, 400f, ~52s antes de este fix).
            #
            # Bones del armature principal — excluir bones filtrados
            # FIX (Kebyn, 2026-08-08): los bones filtrados NO deben quedar sin
            # keyframes fuera de los huecos. Antes, "continue" los dejaba sin
            # ningun dato en los frames CUBIERTOS por una pose (la inmensa
            # mayoria del segmento) porque la action "Capa 1" (caminar/saltar,
            # horneada por "Reproducir recorrido") ya fue borrada mas arriba
            # y jamas existio en NLA (los tracks "Slot_*_arm" son solo
            # plantillas del pipeline externo, nunca se crean en la sesion
            # viva de Blender) -- resultado: patas estaticas durante toda la
            # duracion del segmento. La captura de Capa 1 (_base_cap_bones)
            # SI cubre el rango completo del segmento (no solo los huecos),
            # asi que ahora los bones filtrados siempre toman su valor de ahi
            # en vez de depender de una fuente NLA que no existe.
            for bone_name, bdata in pose.items():
                _bloqueado_total = bone_name in _FILTERED_BONES
                # PORTADO desde alfred_animation_studio (Kebyn, 2026-08-08):
                # ademas del bloqueo total (todo el segmento), un bone puede
                # estar bloqueado SOLO en este frame por un intervalo
                # especifico del Filtro de bones ("dividir en partes").
                _bloqueado_intervalo = (not _bloqueado_total) and _bone_blocked_in_intervals_seg(
                    _active_seg, bone_name, abs_f
                )
                if _bloqueado_total or _bloqueado_intervalo:
                    _fb_data = _base_cap_bones.get(abs_f) if _have_base_cap else None
                    if _fb_data is None and _base_cap_bones:
                        _nearest_ff = min(_base_cap_bones.keys(), key=lambda k: abs(k - abs_f))
                        _fb_data = _base_cap_bones[_nearest_ff]
                    if _fb_data is None:
                        continue   # no hay captura de caminar disponible, no tocar el bone
                    _fbd = _fb_data.get(bone_name)
                    if not _fbd:
                        continue
                    pb = armature.pose.bones.get(bone_name)
                    if pb:
                        pb.rotation_euler = Euler(_fbd["rot"], "XYZ")
                        pb.location       = Vector(_fbd["loc"])
                        pb.scale          = Vector(_fbd["scale"])
                        pb.keyframe_insert(data_path="rotation_euler", frame=abs_f)
                        pb.keyframe_insert(data_path="location",       frame=abs_f)
                        pb.keyframe_insert(data_path="scale",          frame=abs_f)
                    continue
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
            # Root object (jerry / Empty) — solo en modo estatico
            # En modo recorrido el root ya tiene su animacion del Paso 2, no se toca
            if not _recorrido_activo:
                root_obj = scene.objects.get("jerry") or armature
                root_obj.rotation_mode = "XYZ"
                root_obj.rotation_euler = Euler(arm_rot, "XYZ")
                root_obj.location       = Vector(arm_pos)
                root_obj.keyframe_insert(data_path="rotation_euler", frame=abs_f)
                root_obj.keyframe_insert(data_path="location",       frame=abs_f)

        abs_frame = end_frame + 1

        if armature.animation_data and armature.animation_data.action:
            action = armature.animation_data.action
            for fc in _get_action_fcurves(action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "BEZIER"
                    kp.easing        = "AUTO"
        # Suavizado BEZIER para los armatures secundarios (shield y spear)
        for _sec_name in SECONDARY_ARMATURES:
            _sec = scene.objects.get(_sec_name)
            if _sec and _sec.animation_data and _sec.animation_data.action:
                _sec_action = _sec.animation_data.action
                for fc in _get_action_fcurves(_sec_action):
                    for kp in fc.keyframe_points:
                        kp.interpolation = "BEZIER"
                        kp.easing        = "AUTO"

        # ── Ajustar timeline de la escena SIN reducirlo ──────────────────────
        # Si AnimBlocks ya configuró un timeline mas largo, lo respetamos.
        # Solo expandimos si los frames de este personaje quedan fuera del rango actual.
        if scene.frame_start > start_frame:
            scene.frame_start = start_frame
        if scene.frame_end < abs_frame - 1:
            scene.frame_end = abs_frame - 1
        scene.frame_set(start_frame)

        # ── Post-proceso: filtros de movimiento organico ──
        # AISLAMIENTO POR SEGMENTO (Kebyn + Claude, 2026-08-06): se usan los
        # filtros organicos PROPIOS de ESTE segmento (_active_seg.organic)
        # en vez de los globales de scene.jerryst -- antes se usaba siempre
        # st.organic, una unica instancia compartida por todos los
        # segmentos (mismo fix ya aplicado en Alfred el 2026-08-03).
        org = _active_seg.organic
        if org.enabled:
            _apply_organic_filters(
                context, armature, start_frame, end_frame, org,
                filtered_bones=_FILTERED_BONES,
            )

        # ── Post-proceso: Oscilaciones de bones ──────────────────────────────
        _apply_bone_oscillations(
            context, armature, st.bone_oscillations,
            filtered_bones=_FILTERED_BONES,
        )



        # ── Restaurar NLA tracks del recorrido (desmutar) ─────────────────────
        for _trk in _muted_tracks:
            _trk.mute = False

        # ── FIX desincronizacion root/armature ────────────────────────────────
        # En modo recorrido, el armature (Dog_001_rig) es hijo del
        # root empty (jerry). Su transformacion LOCAL debe ser siempre
        # (0,0,0) para que el root sea el unico portador de posicion mundial.
        # CONCATENAR puede dejar valores residuales en armature.location si
        # frame_set() evalua el NLA con strips desactivados y la action directa
        # tiene offsets. Se normaliza aqui antes de que Reproducir recorrido
        # vuelva a evaluar la escena.
        if _recorrido_activo:
            armature.location       = (0.0, 0.0, 0.0)
            armature.rotation_euler = (0.0, 0.0, 0.0)
            armature.scale          = (1.0, 1.0, 1.0)
            context.view_layer.update()

        # ��─ En modo recorrido: la config ya quedo escrita en seg_action ───────
        # CONCATENAR escribio los keyframes de config directamente en la
        # seg_action (que fue asignada como action activa antes del loop de frames).
        # No hay que hacer push al NLA. La seg_action permanece como action activa
        # y contiene: desplazamiento (capa 1) + config de bones (capa 2).
        # La capa 3 (animacion base de bones no configurados) se inyecta en REPRODUCIR.

        # ── Escribir frame_end real al segmento activo ───────────────────────
        # SOLO en single_coord_mode: ahi el frame_end era provisional
        # (= frame_start) y CONCATENAR es quien lo define por primera vez,
        # sumando las duraciones de las poses. Se guarda el frame_end real
        # para que PlaySegment (y _calc_seg_frames) usen el rango correcto.
        #
        # FIX (Kebyn, 2026-08-12): en el resto de los casos (segmentos
        # creados por AutoSplitFromConfig / division manual, con
        # single_coord_mode=False) frame_start/frame_end se definen AGUAS
        # ARRIBA, en el Paso 3 (creacion/division de segmentos). Agregar o
        # editar poses/oscilaciones es un flujo AGUAS ABAJO y no debe poder
        # retroalimentar y modificar limites que pertenecen a una etapa
        # anterior del pipeline. Antes este bloque no chequeaba
        # single_coord_mode y sobreescribia frame_end con abs_frame-1
        # (derivado de la suma de duraciones de poses) cada vez que se
        # concatenaba, encogiendo o corriendo el rango fijado en el Paso 3
        # apenas la suma de poses no llenaba el segmento exacto.
        if _active_seg is not None and _active_seg.single_coord_mode:
            _real_end = abs_frame - 1
            _active_seg.frame_end      = _real_end
            _active_seg.frame_end_auto = _real_end

        st.anim_generated   = True
        st.total_frames_gen = total_gen
        st.end_frame_gen    = abs_frame - 1

        # ── Ejecutar importacion de objetos (escudo, espada, etc.) ─────────────
        # Si hay un segmento activo, solo se procesan los items vinculados a
        # ese segmento (item.segment_idx == idx) o los globales
        # (item.segment_idx == -1). Si no hay segmento activo, se procesan
        # todos los items (comportamiento legacy).
        _oi_summary = ""
        try:
            _n_imp, _n_skip, _oi_errors = _oiu_preview.run_object_imports_live(
                context.scene, segment_idx=idx
            )
            _oi_summary = f"objetos: {_n_imp} importados / {_n_skip} omitidos"
            for _e in _oi_errors:
                print(f"[JRST_Concatenate] {_e}")
        except Exception as _e_oi:
            import traceback
            print("[JRST_Concatenate] Error en importacion de objetos:")
            print(traceback.format_exc())
            _oi_summary = f"objetos: ERROR ({_e_oi})"

        # ── Ejecutar Lanzar / Recoger Objetos ─────────────────────────────────
        _throw_summary = ""
        try:
            segs_all = context.scene.jerry_segs.segments
            _throw_imported = 0
            _throw_applied  = 0
            _throw_errors   = []

            # Procesar el segmento activo (o todos si no hay segmento activo)
            seg_range = ([segs_all[idx]] if idx is not None
                         and idx < len(segs_all)
                         else list(segs_all))

            for seg in seg_range:
                th = seg.throws
                if not th.enabled:
                    continue
                for item in th.items:
                    if not item.enabled:
                        continue
                    try:
                        # 1. Importar objeto si no está en escena
                        obj_name = item.target_object or item.object_name
                        obj = bpy.data.objects.get(obj_name) if obj_name else None
                        if obj is None:
                            # Resolver ruta del .blend
                            if item.blend_path and os.path.isfile(
                                    bpy.path.abspath(item.blend_path)):
                                blend_abs = bpy.path.abspath(item.blend_path)
                            else:
                                anchor  = (bpy.path.abspath(st.anim_dir)
                                           if st.anim_dir else bpy.path.abspath("//"))
                                obj_dir = _oiu_preview.get_objetos_base_path_from_anchor(
                                    anchor, item.levels_up)
                                blend_abs = os.path.join(
                                    obj_dir, item.object_folder, item.blend_filename)

                            obj = _oiu_preview.import_object_from_blend_path(
                                blend_abs, item.object_name)

                            if obj is None:
                                _throw_errors.append(
                                    f"No se pudo importar '{item.object_name}'")
                                continue

                            import mathutils
                            item.imported_object_name = obj.name
                            item.target_object        = obj.name

                            # Visibilidad
                            _oiu_preview.hide_until_frame(
                                obj, appear_frame=item.frame_start)
                            _oiu_preview.set_visibility_keyframes(
                                obj, item.frame_end, visible=False)

                            # Parenteo idéntico a run_object_imports_live
                            arm_name  = (item.parent_armature or "Dog_001_rig").strip()
                            bone_name = (item.parent_bone or "").strip()
                            all_arms  = [o for o in bpy.data.objects
                                         if o.type == 'ARMATURE']
                            arm_obj   = next((o for o in all_arms
                                              if o.name == arm_name), None)
                            if arm_obj is None and len(all_arms) == 1:
                                arm_obj = all_arms[0]
                            target_bone = None
                            if arm_obj and arm_obj.pose:
                                if bone_name:
                                    target_bone = arm_obj.pose.bones.get(bone_name)
                                if target_bone is None:
                                    target_bone = next(
                                        (pb for pb in arm_obj.pose.bones
                                         if 'jaw' in pb.name.lower()), None)
                            if target_bone:
                                obj.parent      = target_bone.id_data
                                obj.parent_bone = target_bone.name
                                obj.parent_type = 'BONE'
                                obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
                            elif arm_obj:
                                obj.parent      = arm_obj
                                obj.parent_type = 'OBJECT'
                                obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
                            obj.location       = (item.loc_x, item.loc_y, item.loc_z)
                            obj.rotation_euler = (item.rot_x, item.rot_y, item.rot_z)
                            obj.scale          = (item.scale_uniform,
                                                  item.scale_uniform,
                                                  item.scale_uniform)
                            if target_bone and not item.target_bone:
                                item.target_bone = target_bone.name
                            _throw_imported += 1
                        else:
                            item.target_object = obj.name

                        # 2. Aplicar trayectoria
                        ok_traj = apply_throw_item(item, context)
                        if ok_traj:
                            _throw_applied += 1
                        else:
                            _throw_errors.append(
                                f"Trayectoria falló: '{item.object_name}'")

                    except Exception as _e_item:
                        import traceback
                        _throw_errors.append(f"'{item.object_name}': {_e_item}")
                        print(f"[THROW] Error en item: {_e_item}")
                        traceback.print_exc()

            if _throw_imported or _throw_applied:
                _throw_summary = (f"throw: {_throw_imported} importados / "
                                  f"{_throw_applied} trayectorias aplicadas")
            for _te in _throw_errors:
                print(f"[JRST_Concatenate THROW] {_te}")

        except Exception as _e_throw:
            import traceback
            print("[JRST_Concatenate] Error en Lanzar/Recoger:")
            print(traceback.format_exc())
            _throw_summary = f"throw: ERROR ({_e_throw})"

        # ── SISTEMA 2 — Parpadeo sincronizado (ahora integrado en CONCATENAR) ─
        # Antes esto exigia presionar "APLICAR PARPADEO (Sistema 2)" aparte
        # despues de CONCATENAR. Ese boton fue eliminado del panel: CONCATENAR
        # ahora aplica tambien el parpadeo cuando el Sistema 2 (o AMBOS) esta
        # seleccionado, usando el mismo rango/valores del panel "Sistema 2 —
        # Parpadeo Sincronizado" (eye_s.blink_frame_start/end/count/duration).
        # Logica identica a la que tenia JRRST_OT_ConcatenateBlink.
        _blink_summary = ""
        eye_s = getattr(getattr(scene, "jerry_segs", None), "eye_expr", None)
        if eye_s is not None and eye_s.active_eye_system in ("SISTEMA_2", "AMBOS"):
            _bsf = eye_s.blink_frame_start
            _bef = eye_s.blink_frame_end
            if _bsf < _bef:
                try:
                    from .eye_system import apply_blink_sequence
                    apply_blink_sequence(_bsf, _bef, eye_s.blink_count,
                                          eye_s.blink_duration, eye_s)
                    _blink_summary = (
                        f"parpadeo: {eye_s.blink_count}x{eye_s.blink_duration}f "
                        f"[{_bsf}-{_bef}]"
                    )
                except Exception as _e_blink:
                    import traceback
                    print("[JRST_Concatenate] Error aplicando parpadeo (Sistema 2):")
                    print(traceback.format_exc())
                    _blink_summary = f"parpadeo: ERROR ({_e_blink})"
            else:
                print("[JRST_Concatenate] Sistema 2/AMBOS seleccionado pero "
                      "Frame inicio >= Frame fin del parpadeo; se omitio.")
                _blink_summary = "parpadeo: omitido (rango invalido)"

        st.status_msg = (
            f"OK  {total_gen} frames  [{start_frame} - {abs_frame-1}]  "
            f"ini={st.pose_start_duration}f({st.pose_start_interp})  "
            f"fin={st.pose_end_duration}f({st.pose_end_interp})  "
            f"entrada={entry_ratio:.0%}  salida={exit_ratio:.0%}"
            + ("  [filtros ON]" if org.enabled else "")
            + (f"  |  {_oi_summary}" if _oi_summary else "")
            + (f"  |  {_throw_summary}" if _throw_summary else "")
            + (f"  |  {_blink_summary}" if _blink_summary else "")
        )
        self.report({"INFO"}, st.status_msg)
        return {"FINISHED"}

class JRRST_OT_ExportAnimation(Operator):
    bl_idname    = "jerryst.export_animation"
    bl_label     = "Exportar .py"
    bl_description = "Exporta la animacion como slot_NNN_tipo.py compatible con el flujo jerry"
    bl_options   = {"REGISTER"}

    def execute(self, context):
        st    = context.scene.jerryst
        scene = context.scene

        if not st.anim_generated:
            self.report({"ERROR"}, "Primero genera la animacion con CONCATENAR")
            return {"CANCELLED"}
        if not st.armature_name:
            self.report({"ERROR"}, "Selecciona el armature")
            return {"CANCELLED"}
        armature = scene.objects.get(st.armature_name)
        if not armature or armature.type != "ARMATURE":
            self.report({"ERROR"}, "Dog_001_rig no valido")
            return {"CANCELLED"}
        if not armature.animation_data or not armature.animation_data.action:
            self.report({"ERROR"}, "No hay accion de animacion en el armature")
            return {"CANCELLED"}

        # ── Leer historia_jerry.json para key_point y orientacion ──
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

        # ── Leer rango real del segmento activo ──────────────────────────────
        # st.start_frame es el frame GLOBAL del Paso 1 (siempre 1).
        # El segmento activo tiene su propio frame_start/frame_end.
        _segs_st = getattr(scene, 'jerry_segs', None)
        _active_seg_export = None
        if _segs_st and len(_segs_st.segments) > 0:
            _idx_exp = max(0, min(_segs_st.active_index, len(_segs_st.segments)-1))
            _active_seg_export = _segs_st.segments[_idx_exp]

        if _active_seg_export is not None:
            start_f      = _active_seg_export.frame_start
            end_f        = _active_seg_export.frame_end if _active_seg_export.frame_end > _active_seg_export.frame_start else _active_seg_export.frame_end_auto
            total_frames = end_f - start_f + 1
        else:
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

        # ── Capturar keyframes de rotacion desde la timeline ──────────────────
        # Estrategia de doble captura para modo recorrido con filtros:
        #   PASO A — bones FILTRADOS (piernas, etc.):
        #     Desmutar NLA del recorrido temporalmente y capturar el rango
        #     COMPLETO del recorrido (pc.frame_inicio → pc.anim_frame_fin).
        #     Estos bones tienen su animacion en el NLA, no en el segmento.
        #   PASO B — bones NO filtrados (brazos, cuerpo, etc.):
        #     Con NLA muteados, capturar desde la action del segmento.
        #     Para frames fuera del segmento, clampar al borde del segmento.

        # Determinar bones filtrados del segmento activo
        _BFMAP_EXP = {
            'spine_6':           'filter_spine_6',
            'Dog_001_rig':       'filter_main_bone',
            'spine_1':           'filter_body',
            'spine_2':           'filter_spine_2',
            'spine_3':           'filter_spine_3',
            'spine_4':           'filter_spine_4',
            'spine_5':           'filter_spine_5',
            'spine_7':           'filter_spine_7',
            'front_shoulder.L':  'filter_left_arm',
            'front_shoulder.R':  'filter_right_arm',
            'front_thigh.L':     'filter_front_thigh_l',
            'front_thigh.R':     'filter_front_thigh_r',
            'front_shin.L':      'filter_front_shin_l',
            'front_shin.R':      'filter_front_shin_r',
            'front_foot.L':      'filter_front_foot_l',
            'front_foot.R':      'filter_front_foot_r',
            'front_toe.L':       'filter_front_toe_l',
            'front_toe.R':       'filter_front_toe_r',
            'shoulder.R':        'filter_right_leg',
            'shoulder.L':        'filter_left_leg',
            'thigh.L':           'filter_thigh_l',
            'thigh.R':           'filter_thigh_r',
            'shin.L':            'filter_shin_l',
            'shin.R':            'filter_shin_r',
            'foot.L':            'filter_foot_l',
            'foot.R':            'filter_foot_r',
            'toe.L':             'filter_toe_l',
            'toe.R':             'filter_toe_r',
            'tail_1':            'filter_shield',
            'tail_2':            'filter_spear',
            'tail_3':            'filter_tail_3',
            'jaw_bot':           'filter_jaw_bot',
            'jaw_top':           'filter_jaw_top',
            'scull':             'filter_scull',
            'scull_1':           'filter_scull_1',
            'ear.L':             'filter_ear_l',
            'ear.R':             'filter_ear_r',
            'sombrero':          'filter_sombrero',
            'sejas_1_jerry':     'filter_sejas_1',
            'sejas_2_jerry':     'filter_sejas_2',
            'no_bone_01':        'filter_no_bone_01',
            'no_bone_02':        'filter_no_bone_02',
            'no_bone_03':        'filter_no_bone_03',
            'no_bone_04':        'filter_no_bone_04',
        }
        _exp_filtered = set()
        if _active_seg_export is not None:
            _exp_filtered = {bn for bn, prop in _BFMAP_EXP.items()
                             if getattr(_active_seg_export, prop, False)}

        # Rango de captura: recorrido completo si aplica, sino solo segmento
        _pc_exp = getattr(scene, 'jerry_path', None)
        _recorrido_exp = _pc_exp is not None and len(_pc_exp.path_points) > 1
        if _recorrido_exp:
            _cap_s = int(getattr(_pc_exp, 'frame_inicio',  start_f))
            _cap_e = int(getattr(_pc_exp, 'anim_frame_fin', end_f))
        else:
            _cap_s = start_f
            _cap_e = end_f

        bone_frames      = {b: {} for b in BONES_LISTA_FULL}
        arm_rot_frames   = {}
        root_keyframes   = {}
        root_obj_capture = scene.objects.get('jerry')

        def _capture_bone(pb_obj, lf, bn):
            if pb_obj:
                e = pb_obj.rotation_euler; l = pb_obj.location; s = pb_obj.scale
                bone_frames[bn][lf] = {
                    'rot': (round(e.x,6), round(e.y,6), round(e.z,6)),
                    'loc': (round(l.x,6), round(l.y,6), round(l.z,6)),
                    'sca': (round(s.x,6), round(s.y,6), round(s.z,6)),
                }
            else:
                bone_frames[bn][lf] = {'rot':(0.,0.,0.),'loc':(0.,0.,0.),'sca':(1.,1.,1.)}

        def _find_pb(bn):
            pb = armature.pose.bones.get(bn)
            if pb is None:
                for _sn in SECONDARY_ARMATURES:
                    _so = scene.objects.get(_sn)
                    if _so and _so.type == 'ARMATURE':
                        pb = _so.pose.bones.get(bn)
                        if pb: break
            return pb

        # PASO A: bones filtrados — NLA activos, capturar rango completo
        # El flujo del usuario es: Reproducir → Concatenar → Reproducir → Exportar.
        # Despues del segundo Reproducir los NLA tracks estan DESMUTEADOS.
        # Guardamos el estado original de cada track y forzamos el estado
        # correcto para cada paso, restaurando al final.
        # Estado para Paso A (bones filtrados del NLA): todos los tracks ACTIVOS.
        # Estado para Paso B (bones del segmento):      todos los tracks MUTEADOS.

        # Guardar estado original de mute de todos los NLA tracks del armature
        _nla_original_mute = {}
        if armature.animation_data:
            for _trk in armature.animation_data.nla_tracks:
                _nla_original_mute[_trk.name] = _trk.mute

        if _exp_filtered:
            # Forzar todos los NLA activos (desmuteados) para Paso A
            if _recorrido_exp and armature.animation_data:
                for _trk in armature.animation_data.nla_tracks:
                    _trk.mute = False
            for _abs_f in range(_cap_s, _cap_e + 1):
                scene.frame_set(_abs_f)
                _lf = _abs_f - _cap_s + 1
                for _bn in _exp_filtered:
                    _capture_bone(_find_pb(_bn), _lf, _bn)
                ae = armature.rotation_euler
                arm_rot_frames[_lf] = (round(ae.x,6), round(ae.y,6), round(ae.z,6))
                if root_obj_capture:
                    rl = root_obj_capture.location; rr = root_obj_capture.rotation_euler
                    root_keyframes[_lf] = {
                        'loc': (round(rl.x,6), round(rl.y,6), round(rl.z,6)),
                        'rot': (round(rr.x,6), round(rr.y,6), round(rr.z,6)),
                    }

        # PASO B: bones NO filtrados — forzar NLA muteados, capturar del segmento
        # Con todos los NLA muteados, Blender evalua solo la action activa del
        # armature (la action del segmento con las poses de configuracion).
        if armature.animation_data:
            for _trk in armature.animation_data.nla_tracks:
                _trk.mute = True
        _non_filtered = [b for b in BONES_LISTA_FULL if b not in _exp_filtered]
        for _abs_f in range(_cap_s, _cap_e + 1):
            _eval_f = max(start_f, min(end_f, _abs_f))
            scene.frame_set(_eval_f)
            _lf = _abs_f - _cap_s + 1
            for _bn in _non_filtered:
                _capture_bone(_find_pb(_bn), _lf, _bn)
            if _lf not in arm_rot_frames:
                ae = armature.rotation_euler
                arm_rot_frames[_lf] = (round(ae.x,6), round(ae.y,6), round(ae.z,6))
            if root_obj_capture and _lf not in root_keyframes:
                rl = root_obj_capture.location; rr = root_obj_capture.rotation_euler
                root_keyframes[_lf] = {
                    'loc': (round(rl.x,6), round(rl.y,6), round(rl.z,6)),
                    'rot': (round(rr.x,6), round(rr.y,6), round(rr.z,6)),
                }

        # Restaurar estado original de mute de todos los NLA tracks
        if armature.animation_data:
            for _trk in armature.animation_data.nla_tracks:
                _trk.mute = _nla_original_mute.get(_trk.name, _trk.mute)


        # Actualizar rango de exportacion al rango real capturado
        if _recorrido_exp:
            start_f      = _cap_s
            end_f        = _cap_e
            total_frames = _cap_e - _cap_s + 1

        scene.frame_set(start_f)

        def frames_at(lf):
            return {b: bone_frames[b].get(lf, {'rot':(0.0,0.0,0.0),'loc':(0.0,0.0,0.0),'sca':(1.0,1.0,1.0)}) 
                    for b in BONES_LISTA_FULL}

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
        # Tag corto del personaje para aislar actions/tracks de distintos rigs en NLA
        char_tag   = st.armature_name  # e.g. "Dog_001_rig"

        # Nombre de archivo: slot_NNN_tipo.py
        slot_str   = f"{slot_num:03d}"
        filename   = f"slot_{slot_str}_{movement}.py"

        # ── Serializar dicts de pose ──
        def _pose_lines(d, varname):
            lines = [f"{varname} = {{"]
            for k, v in d.items():
                # v es ahora un dict {'rot':..., 'loc':..., 'sca':...}
                rot = v['rot'] if isinstance(v, dict) else v
                loc = v['loc'] if isinstance(v, dict) else (0.0, 0.0, 0.0)
                sca = v['sca'] if isinstance(v, dict) else (1.0, 1.0, 1.0)
                lines.append(f"    {repr(k)}: {{'rot': {rot}, 'loc': {loc}, 'sca': {sca}}},")
            lines.append("}")
            return "\n".join(lines)

        kf_lines = ["KEYFRAME_DATA = {"]
        for bn in BONES_LISTA_FULL:
            kf_lines.append(f"    {repr(bn)}: {{")
            for lf, v in sorted(bone_frames[bn].items()):
                kf_lines.append(
                    f"        {lf}: {{'rot': {v['rot']}, 'loc': {v['loc']}, 'sca': {v['sca']}}},")
            kf_lines.append("    },")
        kf_lines.append("}")

        # ── Serializar rotaciones del armature por frame ──
        arm_rot_lines = ["ARMATURE_ROTATIONS = {"]
        for lf, v in sorted(arm_rot_frames.items()):
            arm_rot_lines.append(f"    {lf}: {v},")
        arm_rot_lines.append("}")

        # Serializar ROOT_KEYFRAMES (loc + rot del Empty jerry por frame)
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

        # Rotacion del root: usar frame 1 capturado del Empty jerry (real de timeline)
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
        _blink_code = _blink_sequence_to_code(_build_blink_sequence_data(scene, start_f, end_f))
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
            "# --- Compatibilidad Action.fcurves (eliminado en Blender 5.0+) ---\n"
            "def _get_action_fcurves(target):\n"
            "    anim_data = None\n"
            "    action = target\n"
            "    if isinstance(target, bpy.types.AnimData):\n"
            "        anim_data = target\n"
            "        action = anim_data.action\n"
            "    if action is None:\n"
            "        return []\n"
            "    if hasattr(action, 'fcurves'):\n"
            "        return action.fcurves\n"
            "    from bpy_extras import anim_utils as _au\n"
            "    slot = anim_data.action_slot if anim_data is not None else None\n"
            "    if slot is None and action.slots:\n"
            "        slot = action.slots[0]\n"
            "    if slot is None:\n"
            "        return []\n"
            "    channelbag = _au.action_ensure_channelbag_for_slot(action, slot)\n"
            "    return channelbag.fcurves if channelbag else []\n\n"
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
            "# (key_point seleccionado de historia_jerry.json)\n"
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
        ) + _blink_code + (
            f"EXPRESSION_CONFIG = {{\n"
            f"}}\n\n"
            "\n\n"
            f"BONES_LISTA = {repr(BONES_LISTA_FULL)}\n\n"
            "# ── Armatures secundarios del personaje ──\n"
            f"SECONDARY_ARMATURES = {repr(SECONDARY_ARMATURES)}\n\n"
            f"ARMATURE_NAME = {repr(st.armature_name)}  # identificador unico del personaje\n\n"
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
            "        s = POSE_INICIO.get(bone_name, {'rot':(0.0,0.0,0.0),'loc':(0.0,0.0,0.0),'sca':(1.0,1.0,1.0)})\n"
            "        c = POSE_ACCION.get(bone_name, s)\n"
            "        e = POSE_FIN.get(bone_name,    s)\n"
            "        bone_functions[bone_name] = (\n"
            "            lambda f, ps=s, pa=c, pe=e: {\n"
            "                'rot': _interpolate_3phases(f, total_frames, ps['rot'], pa['rot'], pe['rot']),\n"
            "                'loc': _interpolate_3phases(f, total_frames, ps['loc'], pa['loc'], pe['loc']),\n"
            "                'sca': _interpolate_3phases(f, total_frames, ps['sca'], pa['sca'], pe['sca']),\n"
            "            }\n"
            "        )\n"
            "    return bone_functions\n\n"
            "# Keyframes exactos capturados desde la timeline de Blender\n"
            f"{chr(10).join(kf_lines)}\n\n"
            f"{chr(10).join(arm_rot_lines)}\n\n"
            f"{chr(10).join(root_kf_lines)}\n\n\n"
            "def _find_jerry_objects():\n"
            "    root = bpy.data.objects.get('jerry')\n"
            "    if not root:\n"
            "        root = next(\n"
            "            (o for o in bpy.data.objects\n"
            "             if o.name.lower() == 'jerry' and o.type == 'EMPTY'), None)\n"
            "    armature = bpy.data.objects.get('Dog_001_rig')\n"
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
            "        armature = bpy.data.objects.get('Dog_001_rig')\n"
            "    if not armature or armature.type != 'ARMATURE':\n"
            "        print('Error: No se encontro el Dog_001_rig'); return False\n\n"
            "    bpy.context.view_layer.objects.active = armature\n"
            "    if armature.mode != 'POSE':\n"
            "        bpy.ops.object.mode_set(mode='POSE')\n"
            "    for bone in armature.pose.bones:\n"
            "        bone.rotation_mode = 'XYZ'\n\n"
            f"    _arm_action_name = f'slot_{{SLOT_INDEX:03d}}_{anim_name}_{char_tag}_arm'\n"
            "    if not armature.animation_data:\n"
            "        armature.animation_data_create()\n"
            "    _arm_existing = bpy.data.actions.get(_arm_action_name)\n"
            "    if _arm_existing: bpy.data.actions.remove(_arm_existing)\n"
            "    _arm_action = bpy.data.actions.new(name=_arm_action_name)\n\n"
            "    # Obtener root\n"
            "    root = bpy.data.objects.get('jerry')\n"
            "    if not root:\n"
            "        root = next(\n"
            "            (o for o in bpy.data.objects\n"
            "             if o.name.lower() == 'jerry' and o.type == 'EMPTY'), None)\n\n"
            "    if root:\n"
            f"        _root_action_name = f'slot_{{SLOT_INDEX:03d}}_{anim_name}_{char_tag}_root'\n"
            "        if not root.animation_data:\n"
            "            root.animation_data_create()\n"
            "        _root_existing = bpy.data.actions.get(_root_action_name)\n"
            "        if _root_existing: bpy.data.actions.remove(_root_existing)\n"
            "        _root_action = bpy.data.actions.new(name=_root_action_name)\n"
            "        root.animation_data.action = _root_action\n\n"
            "    # ── Aplicar posicion del ROOT (jerry Empty) ──────────────────\n"
            "    if root and EMBEDDED_TRAJECTORY_POINTS:\n"
            "        _n_pts = len(EMBEDDED_TRAJECTORY_POINTS)\n"
            "        if _n_pts == 1:\n"
            "            # MODO COORD FIJA: si hay ROOT_KEYFRAMES capturados, usarlos.\n"
            "            # Contienen la posicion absoluta real frame a frame, incluyendo\n"
            "            # el pos_z de cada action_pose (ej. 8.8 o 9.0 segun el JSON).\n"
            "            _pt = EMBEDDED_TRAJECTORY_POINTS[0]['coordinates']\n"
            "            _anchor_rot = (math.radians(ROOT_ROTATION_X),\n"
            "                           math.radians(ROOT_ROTATION_Y),\n"
            "                           math.radians(ROOT_ROTATION_Z))\n"
            "            if ROOT_KEYFRAMES:\n"
            "                # Usar posicion absoluta capturada (respeta pos_z del JSON)\n"
            "                _n_rkf = len(ROOT_KEYFRAMES)\n"
            "                for _frame in range(start_frame, end_frame + 1):\n"
            "                    bpy.context.scene.frame_set(_frame)\n"
            "                    _lf = max(1, min(_frame - start_frame + 1, _n_rkf))\n"
            "                    _rkf = ROOT_KEYFRAMES.get(_lf)\n"
            "                    if _rkf:\n"
            "                        root.location       = _rkf['loc']\n"
            "                        root.rotation_euler = _rkf['rot']\n"
            "                    else:\n"
            "                        root.location       = (_pt['x'], _pt['y'], _pt['z'])\n"
            "                        root.rotation_euler = _anchor_rot\n"
            "                    root.keyframe_insert(data_path='location',       frame=_frame)\n"
            "                    root.keyframe_insert(data_path='rotation_euler', frame=_frame)\n"
            "            else:\n"
            "                # Sin ROOT_KEYFRAMES: anclar estatico en la coordenada\n"
            "                for _kf in range(start_frame, end_frame + 1):\n"
            "                    bpy.context.scene.frame_set(_kf)\n"
            "                    root.location       = (_pt['x'], _pt['y'], _pt['z'])\n"
            "                    root.rotation_euler = _anchor_rot\n"
            "                    root.keyframe_insert(data_path='location',       frame=_kf)\n"
            "                    root.keyframe_insert(data_path='rotation_euler', frame=_kf)\n"
            "        else:\n"
            "            # MODO RECORRIDO: usar ROOT_KEYFRAMES capturados desde la timeline.\n"
            "            # Estos keyframes incluyen el arco real de saltos (saltar_subir /\n"
            "            # saltar_bajar) generado por 'Reproducir recorrido', por lo que el\n"
            "            # personaje salta correctamente en lugar de atravesar el bloque en\n"
            "            # linea recta.\n"
            "            # Mapeo: frame local 1..N  <->  ROOT_KEYFRAMES key 1..N\n"
            "            _n_rkf = len(ROOT_KEYFRAMES)\n"
            "            for _frame in range(start_frame, end_frame + 1):\n"
            "                bpy.context.scene.frame_set(_frame)\n"
            "                _lf_rk = _frame - start_frame + 1\n"
            "                # Clampar al rango disponible en ROOT_KEYFRAMES\n"
            "                _lf_rk = max(1, min(_lf_rk, _n_rkf))\n"
            "                _kf = ROOT_KEYFRAMES.get(_lf_rk)\n"
            "                if _kf:\n"
            "                    root.location       = _kf['loc']\n"
            "                    root.rotation_euler = _kf['rot']\n"
            "                root.keyframe_insert(data_path='location',       frame=_frame)\n"
            "                root.keyframe_insert(data_path='rotation_euler', frame=_frame)\n\n"
            "    armature.animation_data.action = _arm_action\n\n"
            "    rz = ROOT_ROTATION_Z if ROOT_ROTATION_Z is not None else 0.0\n\n"
            "    # Aplicar keyframes de huesos\n"
            "    bone_funcs = _build_bone_functions(total_frames)\n"
            "    bones_applied = 0\n"
            "    bones_missing = []\n\n"
            "    # En modo recorrido (>1 punto de trayectoria) el Empty jerry\n"
            "    # ya es el portador de la posicion mundo frame a frame (ROOT_KEYFRAMES).\n"
            "    # Durante 'Reproducir recorrido' el bone raiz 'Dog_001_rig' nunca\n"
            "    # tiene offset de ubicacion (solo rotacion). Si se aplica el loc capturado\n"
            "    # del segmento (e.g. 0.367415, 0, 0.02507) el armature queda desplazado\n"
            "    # visualmente respecto al Empty -> desincronizacion.\n"
            "    # Solucion: en modo recorrido forzar loc=(0,0,0) en el bone raiz.\n"
            "    _recorrido_mode = len(EMBEDDED_TRAJECTORY_POINTS) > 1\n"
            "    _ROOT_BONE_NAME = 'spine_6'  # bone raiz del rig Jerry\n\n"
            "    if total_frames == TOTAL_FRAMES:\n"
            "        for bn in BONES_LISTA:\n"
            "            pb = armature.pose.bones.get(bn)\n"
            "            if not pb: bones_missing.append(bn); continue\n"
            "            pb.rotation_mode = 'XYZ'\n"
            "            for lf, kf in KEYFRAME_DATA.get(bn, {}).items():\n"
            "                abs_f = start_frame + (lf - 1)\n"
            "                pb.rotation_euler = kf['rot']\n"
            "                # En modo recorrido el bone raiz no lleva offset de loc:\n"
            "                # la posicion mundo ya esta en el Empty (ROOT_KEYFRAMES).\n"
            "                if _recorrido_mode and bn == _ROOT_BONE_NAME:\n"
            "                    pb.location = (0.0, 0.0, 0.0)\n"
            "                else:\n"
            "                    pb.location = kf['loc']\n"
            "                pb.scale          = kf['sca']\n"
            "                pb.keyframe_insert(data_path='rotation_euler', frame=abs_f)\n"
            "                pb.keyframe_insert(data_path='location',       frame=abs_f)\n"
            "                pb.keyframe_insert(data_path='scale',          frame=abs_f)\n"
            "            bones_applied += 1\n"
            "    else:\n"
            "        for bone_name, fn in bone_funcs.items():\n"
            "            pb = armature.pose.bones.get(bone_name)\n"
            "            if not pb: bones_missing.append(bone_name); continue\n"
            "            pb.rotation_mode = 'XYZ'\n"
            "            for local_f in range(1, total_frames + 1):\n"
            "                abs_f = start_frame + (local_f - 1)\n"
            "                kf = fn(local_f)\n"
            "                pb.rotation_euler = kf['rot']\n"
            "                if _recorrido_mode and bone_name == _ROOT_BONE_NAME:\n"
            "                    pb.location = (0.0, 0.0, 0.0)\n"
            "                else:\n"
            "                    pb.location = kf['loc']\n"
            "                pb.scale          = kf['sca']\n"
            "                pb.keyframe_insert(data_path='rotation_euler', frame=abs_f)\n"
            "                pb.keyframe_insert(data_path='location',       frame=abs_f)\n"
            "                pb.keyframe_insert(data_path='scale',          frame=abs_f)\n"
            "            bones_applied += 1\n\n"
            "    print(f'Keyframes aplicados a {bones_applied} bones')\n"
            "    if bones_missing:\n"
            "        print(f'   Bones no encontrados: {bones_missing}')\n\n"
            "    # ── Aplicar keyframes a armatures secundarios (shield y spear) ──\n"
            "    for _sec_name in SECONDARY_ARMATURES:\n"
            "        _sec_obj = bpy.data.objects.get(_sec_name)\n"
            "        if not _sec_obj or _sec_obj.type != 'ARMATURE':\n"
            "            continue\n"
            "        bpy.context.view_layer.objects.active = _sec_obj\n"
            "        if _sec_obj.mode != 'POSE':\n"
            "            bpy.ops.object.mode_set(mode='POSE')\n"
            "        if not _sec_obj.animation_data:\n"
            "            _sec_obj.animation_data_create()\n"
            "        _sec_action_name = f'slot_{SLOT_INDEX:03d}_{_sec_name}_sec'\n"
            "        _sec_existing = bpy.data.actions.get(_sec_action_name)\n"
            "        if _sec_existing: bpy.data.actions.remove(_sec_existing)\n"
            "        _sec_action = bpy.data.actions.new(name=_sec_action_name)\n"
            "        _sec_obj.animation_data.action = _sec_action\n"
            "        if total_frames == TOTAL_FRAMES:\n"
            "            for bn in BONES_LISTA:\n"
            "                _sec_pb = _sec_obj.pose.bones.get(bn)\n"
            "                if not _sec_pb: continue\n"
            "                _sec_pb.rotation_mode = 'XYZ'\n"
            "                for lf, kf in KEYFRAME_DATA.get(bn, {}).items():\n"
            "                    abs_f = start_frame + (lf - 1)\n"
            "                    _sec_pb.rotation_euler = kf['rot']\n"
            "                    _sec_pb.location       = kf['loc']\n"
            "                    _sec_pb.scale          = kf['sca']\n"
            "                    _sec_pb.keyframe_insert(data_path='rotation_euler', frame=abs_f)\n"
            "                    _sec_pb.keyframe_insert(data_path='location',       frame=abs_f)\n"
            "                    _sec_pb.keyframe_insert(data_path='scale',          frame=abs_f)\n"
            "        else:\n"
            "            for bone_name, fn in bone_funcs.items():\n"
            "                _sec_pb = _sec_obj.pose.bones.get(bone_name)\n"
            "                if not _sec_pb: continue\n"
            "                _sec_pb.rotation_mode = 'XYZ'\n"
            "                for local_f in range(1, total_frames + 1):\n"
            "                    abs_f = start_frame + (local_f - 1)\n"
            "                    kf = fn(local_f)\n"
            "                    _sec_pb.rotation_euler = kf['rot']\n"
            "                    _sec_pb.location       = kf['loc']\n"
            "                    _sec_pb.scale          = kf['sca']\n"
            "                    _sec_pb.keyframe_insert(data_path='rotation_euler', frame=abs_f)\n"
            "                    _sec_pb.keyframe_insert(data_path='location',       frame=abs_f)\n"
            "                    _sec_pb.keyframe_insert(data_path='scale',          frame=abs_f)\n"
            "        for fc in _get_action_fcurves(_sec_action):\n"
            "            for kp in fc.keyframe_points:\n"
            "                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'\n"
            "        _sec_obj.animation_data.action = None\n"
            "        _sec_track = _sec_obj.animation_data.nla_tracks.new()\n"
            "        _sec_track.name = f'Slot_{SLOT_INDEX:03d}_{_sec_name}'\n"
            "        _sec_strip = _sec_track.strips.new(_sec_action_name, start_frame, _sec_action)\n"
            "        _sec_strip.frame_end        = end_frame\n"
            "        _sec_strip.extrapolation    = 'NOTHING'\n"
            "        _sec_strip.use_auto_blend   = False\n"
            "        _sec_strip.blend_in         = 0\n"
            "        _sec_strip.blend_out        = 0\n"
            "    # ── Restaurar contexto al armature principal ──\n"
            "    bpy.context.view_layer.objects.active = armature\n"
            "    bpy.ops.object.mode_set(mode='POSE')\n"
            "    armature.animation_data.action = _arm_action\n\n"
            "    # ���─ Aplicar rotacion del armature por frame (orientacion por pose) ──\n"
            "    if ARMATURE_ROTATIONS:\n"
            "        armature.rotation_mode = 'XYZ'\n"
            "        if not armature.animation_data:\n"
            "            armature.animation_data_create()\n"
            "        _arm_obj_action_name = f'slot_{SLOT_INDEX:03d}_{ARMATURE_NAME}_arm_obj_rot'\n"
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
            "        for fc in _get_action_fcurves(_arm_obj_action):\n"
            "            for kp in fc.keyframe_points:\n"
            "                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'\n"
            "        # Pasar al NLA\n"
            "        armature.animation_data.action = None\n"
            "        _arm_obj_track = armature.animation_data.nla_tracks.new()\n"
            "        _arm_obj_track.name = f'Slot_{SLOT_INDEX:03d}_{ARMATURE_NAME}_arm_obj_rot'\n"
            "        _arm_obj_strip = _arm_obj_track.strips.new(_arm_obj_action_name, start_frame, _arm_obj_action)\n"
            "        _arm_obj_strip.frame_end     = end_frame\n"
            "        _arm_obj_strip.extrapolation = 'NOTHING'\n"
            "        _arm_obj_strip.use_auto_blend = False\n"
            "        _arm_obj_strip.blend_in  = 0\n"
            "        _arm_obj_strip.blend_out = 0\n\n"
            "    # [FIX] Restaurar _arm_action como accion activa para keyframes de bones\n"
            "    armature.animation_data.action = _arm_action\n\n"
            "    if armature.animation_data and armature.animation_data.action:\n"
            "        for fc in _get_action_fcurves(_arm_action):\n"
            "            for kp in fc.keyframe_points:\n"
            "                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'\n\n"
            "    if root and root.animation_data and root.animation_data.action:\n"
            "        for fc in _get_action_fcurves(root.animation_data.action):\n"
            "            for kp in fc.keyframe_points:\n"
            "                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'\n\n"
            f"    print(f'ANIMACION {anim_name} APLICADA!')\n"
            "    print(f'  Frames: {start_frame}-{end_frame}')\n\n"
            "    # ── Aplicar BLINK_SEQUENCE a los ojos del personaje ─────────────────\n"
            "    if BLINK_SEQUENCE:\n"
            "        _eye_names   = ['ojo_izquierdo_jerry', 'ojo_derecho_jerry']\n"
            "        _pupil_names = ['pupila_izquierda_jerry', 'pupila_derecha_jerry']\n"
            "        _all_eye_obj = [bpy.data.objects.get(n) for n in _eye_names   if bpy.data.objects.get(n)]\n"
            "        _all_pup_obj = [bpy.data.objects.get(n) for n in _pupil_names if bpy.data.objects.get(n)]\n"
            "        for _eye_obj in _all_eye_obj + _all_pup_obj:\n"
            "            if not _eye_obj or _eye_obj.type != 'MESH': continue\n"
            "            if not _eye_obj.data.shape_keys:\n"
            "                _eye_obj.shape_key_add(name='Basis', from_mix=False)\n"
            "            # Reconstruir 'Closed' con geometria cortina (verts -> min_z_mundo)\n"
            "            _ck = _eye_obj.data.shape_keys.key_blocks.get('Closed')\n"
            "            if _ck: _eye_obj.shape_key_remove(_ck)\n"
            "            import mathutils as _mub\n"
            "            _ck = _eye_obj.shape_key_add(name='Closed', from_mix=False)\n"
            "            _mw = _eye_obj.matrix_world; _ml = _mw.inverted()\n"
            "            _vwl = [_mw @ v.co for v in _eye_obj.data.vertices]\n"
            "            _minz = min(v.z for v in _vwl)\n"
            "            for _vi, _vc in enumerate(_vwl): _ck.data[_vi].co = _ml @ _mub.Vector((_vc.x, _vc.y, _minz))\n"
            "            for _lf, _bdata in sorted(BLINK_SEQUENCE.items()):\n"
            "                _abs_f = start_frame + (_lf - 1)\n"
            "                _ck.value = float(_bdata.get('closed', 0.0))\n"
            "                _ck.keyframe_insert(data_path='value', frame=_abs_f)\n"
            "            for _lf, _bdata in sorted(BLINK_SEQUENCE.items()):\n"
            "                _abs_f = start_frame + (_lf - 1)\n"
            "                _eye_obj.hide_render   = bool(_bdata.get('hide', False))\n"
            "                _eye_obj.hide_viewport = bool(_bdata.get('hide', False))\n"
            "                _eye_obj.keyframe_insert(data_path='hide_render',   frame=_abs_f)\n"
            "                _eye_obj.keyframe_insert(data_path='hide_viewport', frame=_abs_f)\n"
            "        _n_eyes = len(_all_eye_obj) + len(_all_pup_obj)\n"
            "        if _n_eyes:\n"
            "            print(f'  Parpadeo: {len(BLINK_SEQUENCE)} frames aplicados en {_n_eyes} objetos')\n"
            "        else:\n"
            "            print('  Parpadeo: sin mallas de ojos en escena (omitido)')\n"
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
            "            _kf1 = _POSE_FRAME_1[_sp_bone.name]\n"
            "            _sp_bone.rotation_euler = _kf1['rot']\n"
            "            # En modo recorrido el bone raiz no lleva loc (el Empty es el portador).\n"
            "            if _recorrido_mode and _sp_bone.name == _ROOT_BONE_NAME:\n"
            "                _sp_bone.location = (0.0, 0.0, 0.0)\n"
            "            else:\n"
            "                _sp_bone.location = _kf1['loc']\n"
            "            _sp_bone.scale          = _kf1['sca']\n"
            "            _sp_bone.keyframe_insert(data_path='rotation_euler', frame=start_frame)\n"
            "            _sp_bone.keyframe_insert(data_path='location',       frame=start_frame)\n"
            "            _sp_bone.keyframe_insert(data_path='scale',          frame=start_frame)\n"
            "        if _sp_bone.name in _POSE_FRAME_END:\n"
            "            bpy.context.scene.frame_set(end_frame)\n"
            "            _kfE = _POSE_FRAME_END[_sp_bone.name]\n"
            "            _sp_bone.rotation_euler = _kfE['rot']\n"
            "            if _recorrido_mode and _sp_bone.name == _ROOT_BONE_NAME:\n"
            "                _sp_bone.location = (0.0, 0.0, 0.0)\n"
            "            else:\n"
            "                _sp_bone.location = _kfE['loc']\n"
            "            _sp_bone.scale          = _kfE['sca']\n"
            "            _sp_bone.keyframe_insert(data_path='rotation_euler', frame=end_frame)\n"
            "            _sp_bone.keyframe_insert(data_path='location',       frame=end_frame)\n"
            "            _sp_bone.keyframe_insert(data_path='scale',          frame=end_frame)\n"
            "    # ── Fin forzado ──\n\n"
            "    # Mover Action del ARMATURE al NLA\n"
            "    if armature.animation_data and armature.animation_data.action:\n"
            "        _arm_done  = armature.animation_data.action\n"
            "        armature.animation_data.action = None\n"
            "        _arm_track = armature.animation_data.nla_tracks.new()\n"
            f"        _arm_track.name = f'Slot_{{SLOT_INDEX:03d}}_{char_tag}_arm'\n"
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
            f"        _root_track.name = f'Slot_{{SLOT_INDEX:03d}}_{char_tag}_root'\n"
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

        # ── Dispatch segun export_mode ────────────────────────────────────────
        mode     = st.export_mode
        out_dir  = bpy.path.abspath(st.anim_dir)
        os.makedirs(out_dir, exist_ok=True)

        segs_settings = getattr(scene, "jerry_segments", None)
        pc            = getattr(scene, "jerry_path",     None)

        # ── MODO FULL: recapturar con el rango COMPLETO del recorrido ─────────
        # El rango del segmento activo (start_f/end_f ya calculados) solo cubre
        # una parte del recorrido (C→D en el diagrama). El modo FULL necesita
        # A→B = pc.frame_inicio → pc.anim_frame_fin (386 frames en el ejemplo).
        if mode == "FULL":
            _pc_full = getattr(scene, "jerry_path", None)
            if _pc_full is not None:
                _full_start = int(getattr(_pc_full, "frame_inicio",  scene.frame_start))
                _full_end   = int(getattr(_pc_full, "anim_frame_fin", scene.frame_end))
            else:
                _full_start = scene.frame_start
                _full_end   = scene.frame_end
            _full_total = _full_end - _full_start + 1

            # Recapturar bones y root para el rango completo
            _full_bone_frames = {b: {} for b in BONES_LISTA_FULL}
            _full_arm_rot     = {}
            _full_root_kf     = {}
            _root_obj_full    = scene.objects.get('jerry')
            for _abs_f in range(_full_start, _full_end + 1):
                scene.frame_set(_abs_f)
                _lf = _abs_f - _full_start + 1
                for _bn in BONES_LISTA_FULL:
                    _pb = armature.pose.bones.get(_bn)
                    if _pb is None:
                        for _sn in SECONDARY_ARMATURES:
                            _so = scene.objects.get(_sn)
                            if _so and _so.type == 'ARMATURE':
                                _pb = _so.pose.bones.get(_bn)
                                if _pb: break
                    if _pb:
                        _e = _pb.rotation_euler; _l = _pb.location; _s = _pb.scale
                        _full_bone_frames[_bn][_lf] = {
                            'rot': (round(_e.x,6), round(_e.y,6), round(_e.z,6)),
                            'loc': (round(_l.x,6), round(_l.y,6), round(_l.z,6)),
                            'sca': (round(_s.x,6), round(_s.y,6), round(_s.z,6)),
                        }
                    else:
                        _full_bone_frames[_bn][_lf] = {'rot':(0.,0.,0.),'loc':(0.,0.,0.),'sca':(1.,1.,1.)}
                _ae = armature.rotation_euler
                _full_arm_rot[_lf] = (round(_ae.x,6), round(_ae.y,6), round(_ae.z,6))
                if _root_obj_full:
                    _rl = _root_obj_full.location; _rr = _root_obj_full.rotation_euler
                    _full_root_kf[_lf] = {
                        'loc': (round(_rl.x,6), round(_rl.y,6), round(_rl.z,6)),
                        'rot': (round(_rr.x,6), round(_rr.y,6), round(_rr.z,6)),
                    }
            scene.frame_set(_full_start)

            # Sobreescribir variables que usa el bloque de generacion de codigo
            start_f      = _full_start
            end_f        = _full_end
            total_frames = _full_total
            bone_frames  = _full_bone_frames
            arm_rot_frames = _full_arm_rot
            root_keyframes = _full_root_kf

            # Recalcular poses de referencia con el nuevo rango
            def _fat_full(lf):
                return {b: bone_frames[b].get(lf, {'rot':(0.,0.,0.),'loc':(0.,0.,0.),'sca':(1.,1.,1.)}) for b in BONES_LISTA_FULL}
            p_ini = _fat_full(1)
            p_act = _fat_full(max(1, total_frames // 2))
            p_fin = _fat_full(total_frames)

            # Reconstruir kf_lines, arm_rot_lines, root_kf_lines con datos completos
            kf_lines = ["KEYFRAME_DATA = {"]
            for _bn in BONES_LISTA_FULL:
                kf_lines.append(f"    {repr(_bn)}: {{")
                for _lf, _v in sorted(bone_frames[_bn].items()):
                    kf_lines.append(f"        {_lf}: {{'rot': {_v['rot']}, 'loc': {_v['loc']}, 'sca': {_v['sca']}}},")
                kf_lines.append("    },")
            kf_lines.append("}")

            arm_rot_lines = ["ARMATURE_ROTATIONS = {"]
            for _lf, _v in sorted(arm_rot_frames.items()):
                arm_rot_lines.append(f"    {_lf}: {_v},")
            arm_rot_lines.append("}")

            root_kf_lines = ["ROOT_KEYFRAMES = {"]
            for _lf, _kf in sorted(root_keyframes.items()):
                root_kf_lines.append(f"    {_lf}: {{'loc': {_kf['loc']}, 'rot': {_kf['rot']}}},")
            root_kf_lines.append("}")

            # Recalcular dur_s y regenerar code completo
            dur_s = round(total_frames / (st.fps if st.fps > 0 else 24), 4)
            # (code se regenera abajo en el bloque FULL usando estos valores)

        # Helper: obtener EMBEDDED_TRAJECTORY_POINTS para un rango de frames
        def _traj_block_for_range(f_ini, f_fin):
            """Devuelve el bloque EMBEDDED_TRAJECTORY_POINTS adecuado.
            Si hay recorrido (>1 coord) incluye todos los puntos que caen
            dentro del rango; si es 1 coordenada usa el punto unico."""
            if pc is None:
                return "EMBEDDED_TRAJECTORY_POINTS = []\n"
            pts = list(pc.path_points)
            if not pts:
                return "EMBEDDED_TRAJECTORY_POINTS = []\n"
            if len(pts) == 1:
                pt  = pts[0]
                co  = {"x": round(pt.coords[0],6), "y": round(pt.coords[1],6), "z": round(pt.coords[2],6)}
                tex = pt.texture or ""
                fi  = getattr(pt, "face_index", "?")
                return (
                    "EMBEDDED_TRAJECTORY_POINTS = [\n"
                    "    {\n"
                    f"        \"index\": 0,\n"
                    f"        \"coordinates\": {{\"x\": {co['x']}, \"y\": {co['y']}, \"z\": {co['z']}}},\n"
                    f"        \"texture\": \"{tex}\",\n"
                    f"        \"face_index\": \"{fi}\"\n"
                    "    },\n"
                    "]\n"
                )
            # Recorrido: todos los puntos
            lines = ["EMBEDDED_TRAJECTORY_POINTS = ["]
            for i, pt in enumerate(pts):
                co  = {"x": round(pt.coords[0],6), "y": round(pt.coords[1],6), "z": round(pt.coords[2],6)}
                tex = pt.texture or ""
                fi  = getattr(pt, "face_index", "?")
                lines.append(
                    "    {\n"
                    f"        \"index\": {i},\n"
                    f"        \"coordinates\": {{\"x\": {co['x']}, \"y\": {co['y']}, \"z\": {co['z']}}},\n"
                    f"        \"texture\": \"{tex}\",\n"
                    f"        \"face_index\": \"{fi}\"\n"
                    "    },"
                )
            lines.append("]")
            return "\n".join(lines) + "\n"

        def _write(filepath, content):
            with open(filepath, "w", encoding="utf-8") as _fh:
                _fh.write(content)
            st.last_export_path = filepath

        # ── MODO ACTIVO (comportamiento anterior) ─────────────────────────────
        if mode == "ACTIVE":
            # traj_block ya fue calculado arriba usando kp_selected
            filepath = os.path.join(out_dir, filename)
            # Reemplazar traj_block con la version completa del recorrido
            code_out = code.replace(traj_block, _traj_block_for_range(start_f, end_f))
            _write(filepath, code_out)
            self.report({"INFO"}, f"Exportado (activo): {filepath}")
            return {"FINISHED"}

        # ── MODO FULL (toda la animacion) ─────────────────────────────────────
        if mode == "FULL":
            # start_f, end_f, total_frames, kf_lines, arm_rot_lines,
            # root_kf_lines y dur_s ya fueron sobreescritos arriba con el
            # rango completo del recorrido (A→B).
            # Parchamos el `code` generado con los valores correctos:
            import re as _re
            _full_traj = _traj_block_for_range(start_f, end_f)
            code_out = code
            # 1. Constantes de frame
            code_out = _re.sub(r'START_FRAME\s*=\s*\d+', f'START_FRAME  = {start_f}', code_out, count=1)
            code_out = _re.sub(r'END_FRAME\s*=\s*\d+',   f'END_FRAME    = {end_f}',   code_out, count=1)
            code_out = _re.sub(r'TOTAL_FRAMES\s*=\s*\d+', f'TOTAL_FRAMES = {total_frames}', code_out, count=1)
            # 2. Trayectoria
            code_out = code_out.replace(traj_block, _full_traj, 1)
            # 3. KEYFRAME_DATA completo
            _kf_new = '\n'.join(kf_lines)
            code_out = _re.sub(r'KEYFRAME_DATA\s*=\s*\{.*?^\}',
                               _kf_new, code_out, count=1, flags=_re.DOTALL | _re.MULTILINE)
            # 4. ARMATURE_ROTATIONS completo
            _ar_new = '\n'.join(arm_rot_lines)
            code_out = _re.sub(r'ARMATURE_ROTATIONS\s*=\s*\{.*?^\}',
                               _ar_new, code_out, count=1, flags=_re.DOTALL | _re.MULTILINE)
            # 5. ROOT_KEYFRAMES completo
            _rk_new = '\n'.join(root_kf_lines)
            code_out = _re.sub(r'ROOT_KEYFRAMES\s*=\s*\{.*?^\}',
                               _rk_new, code_out, count=1, flags=_re.DOTALL | _re.MULTILINE)
            filepath = os.path.join(out_dir, filename)
            _write(filepath, code_out)
            self.report({"INFO"}, f"Exportado (completo {total_frames}f | {start_f}-{end_f}): {filepath}")
            return {"FINISHED"}

        # ── MODOS ALL / SELECTED — necesitan lista de segmentos ───────────────
        if segs_settings is None or not segs_settings.segments:
            self.report({"ERROR"}, "No hay segmentos definidos en el Paso 3")
            return {"CANCELLED"}

        segments_to_export = []
        if mode == "ALL":
            segments_to_export = list(segs_settings.segments)
        elif mode == "SELECTED":
            segments_to_export = [s for s in segs_settings.segments if getattr(s, "export_selected", False)]
            if not segments_to_export:
                self.report({"ERROR"}, "Ningún segmento marcado para exportar")
                return {"CANCELLED"}

        exported_files = []
        base_slot = st.export_slot_number
        for seg_i, seg in enumerate(segments_to_export):
            seg_slot_num = base_slot + seg_i
            seg_type     = (seg.export_type.strip() or st.export_type.strip() or "custom")
            seg_sn       = f"{seg_slot_num:03d}"
            seg_fname    = f"slot_{seg_sn}_{seg_type}.py"
            seg_filepath = os.path.join(out_dir, seg_fname)

            seg_f_ini = seg.frame_start
            seg_f_fin = seg.frame_end
            seg_total = seg_f_fin - seg_f_ini + 1
            if seg_total <= 0:
                continue

            fps_val = st.fps if st.fps > 0 else 24
            dur_s   = round(seg_total / fps_val, 4)

            # ── Capturar frames del segmento ──
            seg_bone_frames = {b: {} for b in BONES_LISTA_FULL}
            seg_arm_rot     = {}
            seg_root_kf     = {}
            root_obj_cap    = scene.objects.get("jerry")
            for abs_f in range(seg_f_ini, seg_f_fin + 1):
                scene.frame_set(abs_f)
                local_f = abs_f - seg_f_ini + 1
                for bn in BONES_LISTA_FULL:
                    pb = armature.pose.bones.get(bn)
                    if pb is None:
                        for sec_name_c in SECONDARY_ARMATURES:
                            sec_c = scene.objects.get(sec_name_c)
                            if sec_c and sec_c.type == "ARMATURE":
                                pb = sec_c.pose.bones.get(bn)
                                if pb: break
                    if pb:
                        e = pb.rotation_euler; l = pb.location; s = pb.scale
                        seg_bone_frames[bn][local_f] = {
                            "rot": (round(e.x,6), round(e.y,6), round(e.z,6)),
                            "loc": (round(l.x,6), round(l.y,6), round(l.z,6)),
                            "sca": (round(s.x,6), round(s.y,6), round(s.z,6)),
                        }
                    else:
                        seg_bone_frames[bn][local_f] = {"rot":(0.,0.,0.),"loc":(0.,0.,0.),"sca":(1.,1.,1.)}
                ae = armature.rotation_euler
                seg_arm_rot[local_f] = (round(ae.x,6), round(ae.y,6), round(ae.z,6))
                if root_obj_cap:
                    rl = root_obj_cap.location; rr = root_obj_cap.rotation_euler
                    seg_root_kf[local_f] = {
                        "loc": (round(rl.x,6), round(rl.y,6), round(rl.z,6)),
                        "rot": (round(rr.x,6), round(rr.y,6), round(rr.z,6)),
                    }
            scene.frame_set(seg_f_ini)

            def _seg_frames_at(lf, _bf=seg_bone_frames):
                return {b: _bf[b].get(lf, {"rot":(0.,0.,0.),"loc":(0.,0.,0.),"sca":(1.,1.,1.)}) for b in BONES_LISTA_FULL}

            sp_ini = _seg_frames_at(1)
            sp_act = _seg_frames_at(max(1, seg_total // 2))
            sp_fin = _seg_frames_at(seg_total)

            # ── Rotacion root frame 1 ──
            if seg_root_kf:
                _rf1     = seg_root_kf.get(1, seg_root_kf[min(seg_root_kf)])
                rx_s     = round(math.degrees(_rf1["rot"][0]), 4)
                ry_s     = round(math.degrees(_rf1["rot"][1]), 4)
                rz_s     = round(math.degrees(_rf1["rot"][2]), 4)
            else:
                rx_s = ori_data.get("rotacion_x", 0.0)
                ry_s = ori_data.get("rotacion_y", 0.0)
                rz_s = ori_data.get("rotacion_z", 0.0)

            # ── Coordenadas del recorrido para este segmento ──
            seg_traj_block = _traj_block_for_range(seg_f_ini, seg_f_fin)

            seg_desc    = (seg.export_desc or st.export_desc or "").strip()
            anim_name_s = f"jerry_{seg_type}"
            char_tag_s  = st.armature_name
            er = round(st.entry_ratio, 2)
            xr = round(st.exit_ratio,  2)

            def _pose_lines_s(d, varname):
                lines = [f"{varname} = {{"]
                for k, v in d.items():
                    rot = v["rot"] if isinstance(v, dict) else v
                    loc = v["loc"] if isinstance(v, dict) else (0.,0.,0.)
                    sca = v["sca"] if isinstance(v, dict) else (1.,1.,1.)
                    lines.append(f"    {repr(k)}: {{'rot': {rot}, 'loc': {loc}, 'sca': {sca}}},")
                lines.append("}")
                return "\n".join(lines)

            kf_lines_s  = ["KEYFRAME_DATA = {"]
            for bn in BONES_LISTA_FULL:
                kf_lines_s.append(f"    {repr(bn)}: {{")
                for lf, v in sorted(seg_bone_frames[bn].items()):
                    kf_lines_s.append(f"        {lf}: {{'rot': {v['rot']}, 'loc': {v['loc']}, 'sca': {v['sca']}}},")
                kf_lines_s.append("    },")
            kf_lines_s.append("}")

            arm_rot_lines_s = ["ARMATURE_ROTATIONS = {"]
            for lf, v in sorted(seg_arm_rot.items()):
                arm_rot_lines_s.append(f"    {lf}: {v},")
            arm_rot_lines_s.append("}")

            root_kf_lines_s = ["ROOT_KEYFRAMES = {"]
            for lf, kf_d in sorted(seg_root_kf.items()):
                root_kf_lines_s.append(f"    {lf}: {{'loc': {kf_d['loc']}, 'rot': {kf_d['rot']}}},")
            root_kf_lines_s.append("}")

            seg_code = (
                "# -*- coding: utf-8 -*-\n"
                '''"""\n'''
                f"{seg_fname}\n"
                f"Jerry - Slot {seg_sn}\n\n"
                "GENERADO AUTOMATICAMENTE\n"
                f"Fecha de generacion: {now}\n\n"
                f"Tipo        : {seg_type}\n"
                f"Descripcion : {seg_desc}\n"
                f"Segmento    : [{seg_i+1}] {seg.label}\n"
                f"Duracion    : {seg_total} frames  ({dur_s} s @ {fps_val} fps)\n\n"
                '''"""\n\n'''
                "import bpy\n"
                "import math\n\n"
                "# --- Compatibilidad Action.fcurves (eliminado en Blender 5.0+) ---\n"
                "def _get_action_fcurves(target):\n"
                "    anim_data = None\n"
                "    action = target\n"
                "    if isinstance(target, bpy.types.AnimData):\n"
                "        anim_data = target\n"
                "        action = anim_data.action\n"
                "    if action is None:\n"
                "        return []\n"
                "    if hasattr(action, 'fcurves'):\n"
                "        return action.fcurves\n"
                "    from bpy_extras import anim_utils as _au\n"
                "    slot = anim_data.action_slot if anim_data is not None else None\n"
                "    if slot is None and action.slots:\n"
                "        slot = action.slots[0]\n"
                "    if slot is None:\n"
                "        return []\n"
                "    channelbag = _au.action_ensure_channelbag_for_slot(action, slot)\n"
                "    return channelbag.fcurves if channelbag else []\n\n"
                f"SLOT_INDEX   = {seg_slot_num}\n"
                f"START_FRAME  = {seg_f_ini}\n"
                f"END_FRAME    = {seg_f_fin}\n"
                f"TOTAL_FRAMES = {seg_total}\n"
                f"ROOT_ROTATION_X = {rx_s}\n"
                f"ROOT_ROTATION_Y = {ry_s}\n"
                f"ROOT_ROTATION_Z = {rz_s}\n\n"
                f"# Segmento: {seg.label}  frames {seg_f_ini}→{seg_f_fin}\n\n"
                f"{seg_traj_block}\n"
                f"ANIMATION_INFO = {{\n"
                f"    'name': '{seg_fname}',\n"
                f"    'frame_count': {seg_total},\n"
                f"    'fps': {fps_val},\n"
                f"    'duration_seconds': {dur_s},\n"
                f"    'slot': {seg_slot_num},\n"
                f"    'movement_type': '{seg_type}',\n"
                f"}}\n\n"
                f"BONES_LISTA = {repr(BONES_LISTA_FULL)}\n\n"
                f"SECONDARY_ARMATURES = {repr(SECONDARY_ARMATURES)}\n\n"
                f"ARMATURE_NAME = {repr(st.armature_name)}\n\n"
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
                f"{_pose_lines_s(sp_ini, 'POSE_INICIO')}\n\n"
                f"{_pose_lines_s(sp_act, 'POSE_ACCION')}\n\n"
                f"{_pose_lines_s(sp_fin, 'POSE_FIN')}\n\n"
                f"{chr(10).join(kf_lines_s)}\n\n"
                f"{chr(10).join(arm_rot_lines_s)}\n\n"
                f"{chr(10).join(root_kf_lines_s)}\n\n\n"
                "def execute_animation(player_parts=None, start_frame=None, end_frame=None):\n"
                '''    """\n'''
                f"    Slot {seg_type} — segmento {seg.label}.\n"
                '''    """\n'''
                "    if start_frame is None: start_frame = START_FRAME\n"
                "    if end_frame   is None: end_frame   = END_FRAME\n"
                "    total_frames = end_frame - start_frame + 1\n\n"
                "    armature = player_parts.get('body') if player_parts else None\n"
                "    if not armature:\n"
                "        armature = bpy.data.objects.get('Dog_001_rig')\n"
                "    if not armature or armature.type != 'ARMATURE':\n"
                "        print('Error: No se encontro el Dog_001_rig'); return False\n\n"
                "    bpy.context.view_layer.objects.active = armature\n"
                "    if armature.mode != 'POSE':\n"
                "        bpy.ops.object.mode_set(mode='POSE')\n"
                "    for bone in armature.pose.bones:\n"
                "        bone.rotation_mode = 'XYZ'\n\n"
                f"    _arm_action_name = f'slot_{{SLOT_INDEX:03d}}_{anim_name_s}_{char_tag_s}_arm'\n"
                "    if not armature.animation_data:\n"
                "        armature.animation_data_create()\n"
                "    _arm_existing = bpy.data.actions.get(_arm_action_name)\n"
                "    if _arm_existing: bpy.data.actions.remove(_arm_existing)\n"
                "    _arm_action = bpy.data.actions.new(name=_arm_action_name)\n"
                "    armature.animation_data.action = _arm_action\n\n"
                "    if ARMATURE_ROTATIONS:\n"
                "        armature.rotation_mode = 'XYZ'\n"
                "        for lf, rot in ARMATURE_ROTATIONS.items():\n"
                "            abs_f = start_frame + (lf - 1)\n"
                "            bpy.context.scene.frame_set(abs_f)\n"
                "            armature.rotation_euler = rot\n"
                "            armature.keyframe_insert(data_path='rotation_euler', frame=abs_f)\n\n"
                "    for bn in BONES_LISTA:\n"
                "        pb = armature.pose.bones.get(bn)\n"
                "        if not pb: continue\n"
                "        pb.rotation_mode = 'XYZ'\n"
                "        for lf, kf in KEYFRAME_DATA.get(bn, {}).items():\n"
                "            abs_f = start_frame + (lf - 1)\n"
                "            pb.rotation_euler = kf['rot']\n"
                "            pb.location       = kf['loc']\n"
                "            pb.scale          = kf['sca']\n"
                "            pb.keyframe_insert(data_path='rotation_euler', frame=abs_f)\n"
                "            pb.keyframe_insert(data_path='location',       frame=abs_f)\n"
                "            pb.keyframe_insert(data_path='scale',          frame=abs_f)\n\n"
                "    if armature.animation_data and armature.animation_data.action:\n"
                "        for fc in _get_action_fcurves(_arm_action):\n"
                "            for kp in fc.keyframe_points:\n"
                "                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'\n\n"
                f"    print(f'OK: Slot {{SLOT_INDEX}} {anim_name_s} completado  [{{start_frame}}-{{end_frame}}]')\n"
                "    return True\n\n\n"
                "if __name__ == '__main__':\n"
                "    execute_animation(None, start_frame=START_FRAME, end_frame=END_FRAME)\n"
            )

            _write(seg_filepath, seg_code)
            exported_files.append(seg_fname)

        if exported_files:
            self.report({"INFO"}, f"Exportados {len(exported_files)} archivos: " + ", ".join(exported_files))
        else:
            self.report({"WARNING"}, "Ningun archivo exportado (revisa los segmentos)")
        return {"FINISHED"}

# =============================================================================
# =============================================================================
# EXPORTAR .py — MODO UNA SOLA COORDENADA
# Exportador dedicado para el caso single_coord_mode (1 punto de trayectoria).
# Captura bones/root con NLA activos (igual que el exportador antiguo) y genera
# el mismo .py con la jerarquia completa del exportador multi-coord:
#   KEYFRAME_DATA + ARMATURE_ROTATIONS + ROOT_KEYFRAMES + execute_animation()
#   con secondary armatures, NLA push, forzado de primer/ultimo frame, etc.
# =============================================================================

class JRRST_OT_ExportAnimationSingleCoord(Operator):
    bl_idname    = "jerryst.export_animation_single_coord"
    bl_label     = "Exportar .py (1 coord)"
    bl_description = "Exporta para el caso de una sola coordenada: captura rot/loc/sca completo de todos los bones y del root (con efectos organicos, filtros y oscilaciones) y genera el slot completo"
    bl_options   = {"REGISTER"}

    def execute(self, context):
        st    = context.scene.jerryst
        scene = context.scene

        if not st.anim_generated:
            self.report({"ERROR"}, "Primero genera la animacion con CONCATENAR")
            return {"CANCELLED"}
        if not st.armature_name:
            self.report({"ERROR"}, "Selecciona el armature")
            return {"CANCELLED"}
        armature = scene.objects.get(st.armature_name)
        if not armature or armature.type != "ARMATURE":
            self.report({"ERROR"}, "Dog_001_rig no valido")
            return {"CANCELLED"}

        # ── Verificar que realmente es modo 1 coordenada ──────────────────────
        _pc = getattr(scene, "jerry_path", None)
        _n_pts = len(_pc.path_points) if _pc is not None else 0
        if _n_pts > 1:
            self.report({"ERROR"},
                "Este exportador es solo para 1 coordenada. "
                "Para recorridos con multiples puntos usa el exportador principal.")
            return {"CANCELLED"}

        # ── Leer historia_jerry.json para key_point y orientacion ────
        historia = load_historia_json(st.historia_json)
        kps      = get_key_points(historia)
        ori_data = historia.get("configuracion", {}).get("orientacion_inicial", {})

        try:
            kp_idx_sel = int(st.root_pos_key_point)
        except (ValueError, TypeError):
            kp_idx_sel = 1
        kp_selected = next((k for k in kps if k.get("index") == kp_idx_sel), None)
        if kp_selected is None and kps:
            kp_selected = kps[0]

        # ── Leer rango del segmento activo ────────────────────────────────────
        _segs_st = getattr(scene, "jerry_segs", None)
        _active_seg = None
        if _segs_st and len(_segs_st.segments) > 0:
            _idx = max(0, min(_segs_st.active_index, len(_segs_st.segments)-1))
            _active_seg = _segs_st.segments[_idx]

        if _active_seg is not None:
            start_f      = _active_seg.frame_start
            _fe_raw      = _active_seg.frame_end
            _fe_auto     = _active_seg.frame_end_auto
            end_f        = _fe_raw if _fe_raw > _active_seg.frame_start else _fe_auto
            total_frames = end_f - start_f + 1
        else:
            start_f      = st.start_frame
            end_f        = st.end_frame_gen
            total_frames = st.total_frames_gen

        # ── Anchor point ──────────────────────────────────────────────────────
        # CRITICO: el anchor debe ser el mismo punto que execute_animation usa
        # para reconstruir la posicion del root. En modo 1 coordenada eso es
        # EMBEDDED_TRAJECTORY_POINTS[0], que viene del path recorder.
        # Si no hay path recorder, se usa kp_selected de la historia.
        anchor_x = anchor_y = anchor_z = 0.0
        if _pc is not None and len(_pc.path_points) == 1:
            # Misma fuente que traj_block y que execute_animation
            _pt0 = _pc.path_points[0]
            anchor_x = _pt0.coords[0]
            anchor_y = _pt0.coords[1]
            anchor_z = _pt0.coords[2]
        elif kp_selected:
            co = kp_selected.get("coordinates", {"x": 0, "y": 0, "z": 0})
            anchor_x = co["x"]; anchor_y = co["y"]; anchor_z = co["z"]

        # ── Captura de bones con TODOS los NLA ACTIVOS (igual que exportador
        #    antiguo): la action del segmento ya esta en el NLA como strip, y
        #    con NLA activos Blender evalua la pose real incluyendo filtros,
        #    oscilaciones organicas, etc. ─────────────────────────────────────
        root_obj_capture = scene.objects.get("jerry")
        bone_frames    = {b: {} for b in BONES_LISTA_FULL}
        arm_rot_frames = {}
        root_keyframes = {}

        # Desmutar todos los NLA tracks del armature para la captura
        _nla_mute_backup = {}
        if armature.animation_data:
            for _trk in armature.animation_data.nla_tracks:
                _nla_mute_backup[_trk.name] = _trk.mute
                _trk.mute = False

        def _find_pb(bn):
            pb = armature.pose.bones.get(bn)
            if pb is None:
                for _sn in SECONDARY_ARMATURES:
                    _so = scene.objects.get(_sn)
                    if _so and _so.type == "ARMATURE":
                        pb = _so.pose.bones.get(bn)
                        if pb: break
            return pb

        for abs_f in range(start_f, end_f + 1):
            scene.frame_set(abs_f)
            lf = abs_f - start_f + 1
            for bn in BONES_LISTA_FULL:
                pb = _find_pb(bn)
                if pb:
                    e = pb.rotation_euler; l = pb.location; s = pb.scale
                    bone_frames[bn][lf] = {
                        "rot": (round(e.x,6), round(e.y,6), round(e.z,6)),
                        "loc": (round(l.x,6), round(l.y,6), round(l.z,6)),
                        "sca": (round(s.x,6), round(s.y,6), round(s.z,6)),
                    }
                else:
                    bone_frames[bn][lf] = {
                        "rot": (0.0,0.0,0.0), "loc": (0.0,0.0,0.0), "sca": (1.0,1.0,1.0)
                    }
            ae = armature.rotation_euler
            arm_rot_frames[lf] = (round(ae.x,6), round(ae.y,6), round(ae.z,6))
            if root_obj_capture:
                rl = root_obj_capture.location
                rr = root_obj_capture.rotation_euler
                rs = root_obj_capture.scale
                # Guardar posicion ABSOLUTA del root (no offset relativo al anchor).
                # El anchor se usa solo para posicionar el punto de la trayectoria,
                # pero la posicion real del root incluye el pos_z de cada action_pose
                # (ej. 8.8 vs 9.0), que debe preservarse exactamente tal como el JSON manda.
                root_keyframes[lf] = {
                    "loc": (round(rl.x, 6),
                            round(rl.y, 6),
                            round(rl.z, 6)),
                    "rot": (round(rr.x,6), round(rr.y,6), round(rr.z,6)),
                    "sca": (round(rs.x,6), round(rs.y,6), round(rs.z,6)),
                }

        # Restaurar estado de mute original
        if armature.animation_data:
            for _trk in armature.animation_data.nla_tracks:
                _trk.mute = _nla_mute_backup.get(_trk.name, _trk.mute)

        scene.frame_set(start_f)

        # ── Poses de referencia ───────────────────────────────────────────────
        def frames_at(lf):
            return {b: bone_frames[b].get(
                lf, {"rot":(0.0,0.0,0.0), "loc":(0.0,0.0,0.0), "sca":(1.0,1.0,1.0)})
                    for b in BONES_LISTA_FULL}

        p_ini = frames_at(1)
        p_act = frames_at(max(1, total_frames // 2))
        p_fin = frames_at(total_frames)

        # ── Metadatos ─────────────────────────────────────────────────────────
        slot_num  = st.export_slot_number
        movement  = st.export_type.strip() or "custom"
        desc      = st.export_desc.strip()
        now       = datetime.now().strftime("%Y-%m-%d")
        fps_val   = st.fps
        dur_s     = round(total_frames / fps_val, 4)
        er        = round(st.entry_ratio, 2)
        xr        = round(st.exit_ratio,  2)
        anim_name = f"jerry_{movement}"
        char_tag  = st.armature_name
        slot_str  = f"{slot_num:03d}"
        filename  = f"slot_{slot_str}_{movement}.py"

        # ── Rotacion del root: extraer del frame 1 capturado ─────────────────
        if root_keyframes:
            _rf1 = root_keyframes.get(1, root_keyframes[min(root_keyframes)])
            rx_real = round(math.degrees(_rf1["rot"][0]), 4)
            ry_real = round(math.degrees(_rf1["rot"][1]), 4)
            rz_real = round(math.degrees(_rf1["rot"][2]), 4)
        else:
            rx_real = ori_data.get("rotacion_x", 0.0)
            ry_real = ori_data.get("rotacion_y", 0.0)
            rz_real = ori_data.get("rotacion_z", 0.0)

        # ── Trajectory block (1 punto fijo desde el path recorder o historia) ─
        if _pc is not None and _n_pts == 1:
            _pt_rec = _pc.path_points[0]
            traj_block = (
                "EMBEDDED_TRAJECTORY_POINTS = [\n"
                "    {\n"
                f"        \"index\": 0,\n"
                f"        \"coordinates\": {{\"x\": {_pt_rec.coords[0]}, "
                f"\"y\": {_pt_rec.coords[1]}, \"z\": {_pt_rec.coords[2]}}},\n"
                f"        \"texture\": \"{_pt_rec.texture}\",\n"
                f"        \"face_index\": \"{_pt_rec.face_index}\"\n"
                "    },\n"
                "]\n"
            )
        elif kp_selected:
            co  = kp_selected.get("coordinates", {"x":0,"y":0,"z":0})
            tex = kp_selected.get("texture", "?")
            fi  = kp_selected.get("face_index", "?")
            traj_block = (
                "EMBEDDED_TRAJECTORY_POINTS = [\n"
                "    {\n"
                f"        \"index\": {kp_selected.get('index', 0)},\n"
                f"        \"coordinates\": {{\"x\": {co['x']}, \"y\": {co['y']}, \"z\": {co['z']}}},\n"
                f"        \"texture\": \"{tex}\",\n"
                f"        \"face_index\": \"{fi}\"\n"
                "    },\n"
                "]\n"
            )
        else:
            traj_block = "EMBEDDED_TRAJECTORY_POINTS = []\n"

        # ── Serializar dicts de pose ──────────────────────────────────────────
        def _pose_lines(d, varname):
            lines = [f"{varname} = {{"]
            for k, v in d.items():
                rot = v["rot"] if isinstance(v, dict) else v
                loc = v["loc"] if isinstance(v, dict) else (0.0, 0.0, 0.0)
                sca = v["sca"] if isinstance(v, dict) else (1.0, 1.0, 1.0)
                lines.append(f"    {repr(k)}: {{'rot': {rot}, 'loc': {loc}, 'sca': {sca}}},")
            lines.append("}")
            return "\n".join(lines)

        kf_lines = ["KEYFRAME_DATA = {"]
        for bn in BONES_LISTA_FULL:
            kf_lines.append(f"    {repr(bn)}: {{")
            for lf, v in sorted(bone_frames[bn].items()):
                kf_lines.append(
                    f"        {lf}: {{'rot': {v['rot']}, 'loc': {v['loc']}, 'sca': {v['sca']}}},")
            kf_lines.append("    },")
        kf_lines.append("}")

        arm_rot_lines = ["ARMATURE_ROTATIONS = {"]
        for lf, v in sorted(arm_rot_frames.items()):
            arm_rot_lines.append(f"    {lf}: {v},")
        arm_rot_lines.append("}")

        # ROOT_KEYFRAMES: en modo 1 coord, el orquestador usa el anchor fijo,
        # pero incluimos los keyframes capturados para referencia/debug.
        root_kf_lines = ["ROOT_KEYFRAMES = {"]
        for lf, kf in sorted(root_keyframes.items()):
            root_kf_lines.append(
                f"    {lf}: {{'loc': {kf['loc']}, 'rot': {kf['rot']}, 'sca': {kf.get('sca', (1.0,1.0,1.0))}}},")
        root_kf_lines.append("}")

        # ── Generar codigo del slot (misma jerarquia que exportador multi-coord)
        _blink_code = _blink_sequence_to_code(_build_blink_sequence_data(scene, start_f, end_f))
        code = (
            "# -*- coding: utf-8 -*-\n"
            '"""\n'
            f"{filename}\n"
            f"Jerry - Slot {{{slot_str}}}\n\n"
            "GENERADO AUTOMATICAMENTE  [MODO 1 COORDENADA]\n"
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
            "# --- Compatibilidad Action.fcurves (eliminado en Blender 5.0+) ---\n"
            "def _get_action_fcurves(target):\n"
            "    anim_data = None\n"
            "    action = target\n"
            "    if isinstance(target, bpy.types.AnimData):\n"
            "        anim_data = target\n"
            "        action = anim_data.action\n"
            "    if action is None:\n"
            "        return []\n"
            "    if hasattr(action, 'fcurves'):\n"
            "        return action.fcurves\n"
            "    from bpy_extras import anim_utils as _au\n"
            "    slot = anim_data.action_slot if anim_data is not None else None\n"
            "    if slot is None and action.slots:\n"
            "        slot = action.slots[0]\n"
            "    if slot is None:\n"
            "        return []\n"
            "    channelbag = _au.action_ensure_channelbag_for_slot(action, slot)\n"
            "    return channelbag.fcurves if channelbag else []\n\n"
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
            "# (1 coordenada fija — modo parado/idle)\n"
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
        ) + _blink_code + (
            f"EXPRESSION_CONFIG = {{\n"
            f"}}\n\n"
            "\n\n"
            f"BONES_LISTA = {repr(BONES_LISTA_FULL)}\n\n"
            "# ── Armatures secundarios del personaje ──\n"
            f"SECONDARY_ARMATURES = {repr(SECONDARY_ARMATURES)}\n\n"
            f"ARMATURE_NAME = {repr(st.armature_name)}  # identificador unico del personaje\n\n"
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
            "        s = POSE_INICIO.get(bone_name, {'rot':(0.0,0.0,0.0),'loc':(0.0,0.0,0.0),'sca':(1.0,1.0,1.0)})\n"
            "        c = POSE_ACCION.get(bone_name, s)\n"
            "        e = POSE_FIN.get(bone_name,    s)\n"
            "        bone_functions[bone_name] = (\n"
            "            lambda f, ps=s, pa=c, pe=e: {\n"
            "                'rot': _interpolate_3phases(f, total_frames, ps['rot'], pa['rot'], pe['rot']),\n"
            "                'loc': _interpolate_3phases(f, total_frames, ps['loc'], pa['loc'], pe['loc']),\n"
            "                'sca': _interpolate_3phases(f, total_frames, ps['sca'], pa['sca'], pe['sca']),\n"
            "            }\n"
            "        )\n"
            "    return bone_functions\n\n"
            "# Keyframes exactos capturados desde la timeline de Blender\n"
            f"{chr(10).join(kf_lines)}\n\n"
            f"{chr(10).join(arm_rot_lines)}\n\n"
            f"{chr(10).join(root_kf_lines)}\n\n\n"
            "def _find_jerry_objects():\n"
            "    root = bpy.data.objects.get('jerry')\n"
            "    if not root:\n"
            "        root = next(\n"
            "            (o for o in bpy.data.objects\n"
            "             if o.name.lower() == 'jerry' and o.type == 'EMPTY'), None)\n"
            "    armature = bpy.data.objects.get('Dog_001_rig')\n"
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
            f"    Slot Jerry {movement}  [MODO 1 COORDENADA].\n\n"
            "    El root (jerry) se ancla en EMBEDDED_TRAJECTORY_POINTS[0].\n"
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
            "        armature = bpy.data.objects.get('Dog_001_rig')\n"
            "    if not armature or armature.type != 'ARMATURE':\n"
            "        print('Error: No se encontro el Dog_001_rig'); return False\n\n"
            "    bpy.context.view_layer.objects.active = armature\n"
            "    if armature.mode != 'POSE':\n"
            "        bpy.ops.object.mode_set(mode='POSE')\n"
            "    for bone in armature.pose.bones:\n"
            "        bone.rotation_mode = 'XYZ'\n\n"
            f"    _arm_action_name = f'slot_{{SLOT_INDEX:03d}}_{anim_name}_{char_tag}_arm'\n"
            "    if not armature.animation_data:\n"
            "        armature.animation_data_create()\n"
            "    _arm_existing = bpy.data.actions.get(_arm_action_name)\n"
            "    if _arm_existing: bpy.data.actions.remove(_arm_existing)\n"
            "    _arm_action = bpy.data.actions.new(name=_arm_action_name)\n\n"
            "    # Obtener root\n"
            "    root = bpy.data.objects.get('jerry')\n"
            "    if not root:\n"
            "        root = next(\n"
            "            (o for o in bpy.data.objects\n"
            "             if o.name.lower() == 'jerry' and o.type == 'EMPTY'), None)\n\n"
            "    if root:\n"
            f"        _root_action_name = f'slot_{{SLOT_INDEX:03d}}_{anim_name}_{char_tag}_root'\n"
            "        if not root.animation_data:\n"
            "            root.animation_data_create()\n"
            "        _root_existing = bpy.data.actions.get(_root_action_name)\n"
            "        if _root_existing: bpy.data.actions.remove(_root_existing)\n"
            "        _root_action = bpy.data.actions.new(name=_root_action_name)\n"
            "        root.animation_data.action = _root_action\n\n"
            "    # ── Aplicar posicion del ROOT: MODO 1 COORDENADA ─────────────────────\n"
            "    # ROOT_KEYFRAMES contiene posicion ABSOLUTA (x,y,z) capturada frame a\n"
            "    # frame desde la timeline. El pos_z refleja exactamente el valor del\n"
            "    # JSON (ej. 8.8 o 9.0 segun cada action_pose). Se aplica directamente.\n"
            "    if root and EMBEDDED_TRAJECTORY_POINTS:\n"
            "        _pt = EMBEDDED_TRAJECTORY_POINTS[0]['coordinates']\n"
            "        _anchor_x = _pt['x']; _anchor_y = _pt['y']; _anchor_z = _pt['z']\n"
            "        _base_rot = (math.radians(ROOT_ROTATION_X),\n"
            "                     math.radians(ROOT_ROTATION_Y),\n"
            "                     math.radians(ROOT_ROTATION_Z))\n"
            "        if ROOT_KEYFRAMES:\n"
            "            # Aplicar keyframes reales capturados con posicion absoluta.\n"
            "            # La posicion incluye el pos_z real de cada action_pose\n"
            "            # (puede ser 8.8, 9.0, etc. segun el JSON de configuracion).\n"
            "            for lf in range(1, total_frames + 1):\n"
            "                abs_f = start_frame + (lf - 1)\n"
            "                bpy.context.scene.frame_set(abs_f)\n"
            "                _kf = ROOT_KEYFRAMES.get(lf)\n"
            "                if _kf:\n"
            "                    _abs = _kf['loc']  # posicion absoluta, no offset\n"
            "                    root.location = (_abs[0], _abs[1], _abs[2])\n"
            "                    root.rotation_euler = _kf['rot']\n"
            "                    root.scale          = _kf.get('sca', (1.0, 1.0, 1.0))\n"
            "                else:\n"
            "                    root.location       = (_anchor_x, _anchor_y, _anchor_z)\n"
            "                    root.rotation_euler = _base_rot\n"
            "                    root.scale          = (1.0, 1.0, 1.0)\n"
            "                root.keyframe_insert(data_path='location',       frame=abs_f)\n"
            "                root.keyframe_insert(data_path='rotation_euler', frame=abs_f)\n"
            "                root.keyframe_insert(data_path='scale',          frame=abs_f)\n"
            "        else:\n"
            "            # Sin ROOT_KEYFRAMES: anclar estatico en la coordenada\n"
            "            for _kf in range(start_frame, end_frame + 1):\n"
            "                bpy.context.scene.frame_set(_kf)\n"
            "                root.location       = (_anchor_x, _anchor_y, _anchor_z)\n"
            "                root.rotation_euler = _base_rot\n"
            "                root.scale          = (1.0, 1.0, 1.0)\n"
            "                root.keyframe_insert(data_path='location',       frame=_kf)\n"
            "                root.keyframe_insert(data_path='rotation_euler', frame=_kf)\n"
            "                root.keyframe_insert(data_path='scale',          frame=_kf)\n\n"
            "    armature.animation_data.action = _arm_action\n\n"
            "    # Aplicar keyframes de huesos\n"
            "    bone_funcs = _build_bone_functions(total_frames)\n"
            "    bones_applied = 0\n"
            "    bones_missing = []\n\n"
            "    # Modo 1 coordenada: rot/loc/sca de todos los bones se aplican\n"
            "    # tal como fueron capturados desde la timeline (incluyendo root bone).\n"
            "    # El root OBJETO (jerry empty) ya se posiciono arriba con\n"
            "    # ROOT_KEYFRAMES, por lo que el root BONE debe conservar su loc real.\n"
            "    if total_frames == TOTAL_FRAMES:\n"
            "        for bn in BONES_LISTA:\n"
            "            pb = armature.pose.bones.get(bn)\n"
            "            if not pb: bones_missing.append(bn); continue\n"
            "            pb.rotation_mode = 'XYZ'\n"
            "            for lf, kf in KEYFRAME_DATA.get(bn, {}).items():\n"
            "                abs_f = start_frame + (lf - 1)\n"
            "                pb.rotation_euler = kf['rot']\n"
            "                pb.location       = kf['loc']\n"
            "                pb.scale          = kf['sca']\n"
            "                pb.keyframe_insert(data_path='rotation_euler', frame=abs_f)\n"
            "                pb.keyframe_insert(data_path='location',       frame=abs_f)\n"
            "                pb.keyframe_insert(data_path='scale',          frame=abs_f)\n"
            "            bones_applied += 1\n"
            "    else:\n"
            "        for bone_name, fn in bone_funcs.items():\n"
            "            pb = armature.pose.bones.get(bone_name)\n"
            "            if not pb: bones_missing.append(bone_name); continue\n"
            "            pb.rotation_mode = 'XYZ'\n"
            "            for local_f in range(1, total_frames + 1):\n"
            "                abs_f = start_frame + (local_f - 1)\n"
            "                kf = fn(local_f)\n"
            "                pb.rotation_euler = kf['rot']\n"
            "                pb.location       = kf['loc']\n"
            "                pb.scale          = kf['sca']\n"
            "                pb.keyframe_insert(data_path='rotation_euler', frame=abs_f)\n"
            "                pb.keyframe_insert(data_path='location',       frame=abs_f)\n"
            "                pb.keyframe_insert(data_path='scale',          frame=abs_f)\n"
            "            bones_applied += 1\n\n"
            "    print(f'Keyframes aplicados a {bones_applied} bones')\n"
            "    if bones_missing:\n"
            "        print(f'   Bones no encontrados: {bones_missing}')\n\n"
            "    # ── Aplicar keyframes a armatures secundarios (shield y spear) ──\n"
            "    for _sec_name in SECONDARY_ARMATURES:\n"
            "        _sec_obj = bpy.data.objects.get(_sec_name)\n"
            "        if not _sec_obj or _sec_obj.type != 'ARMATURE':\n"
            "            continue\n"
            "        bpy.context.view_layer.objects.active = _sec_obj\n"
            "        if _sec_obj.mode != 'POSE':\n"
            "            bpy.ops.object.mode_set(mode='POSE')\n"
            "        if not _sec_obj.animation_data:\n"
            "            _sec_obj.animation_data_create()\n"
            "        _sec_action_name = f'slot_{SLOT_INDEX:03d}_{_sec_name}_sec'\n"
            "        _sec_existing = bpy.data.actions.get(_sec_action_name)\n"
            "        if _sec_existing: bpy.data.actions.remove(_sec_existing)\n"
            "        _sec_action = bpy.data.actions.new(name=_sec_action_name)\n"
            "        _sec_obj.animation_data.action = _sec_action\n"
            "        if total_frames == TOTAL_FRAMES:\n"
            "            for bn in BONES_LISTA:\n"
            "                _sec_pb = _sec_obj.pose.bones.get(bn)\n"
            "                if not _sec_pb: continue\n"
            "                _sec_pb.rotation_mode = 'XYZ'\n"
            "                for lf, kf in KEYFRAME_DATA.get(bn, {}).items():\n"
            "                    abs_f = start_frame + (lf - 1)\n"
            "                    _sec_pb.rotation_euler = kf['rot']\n"
            "                    _sec_pb.location       = kf['loc']\n"
            "                    _sec_pb.scale          = kf['sca']\n"
            "                    _sec_pb.keyframe_insert(data_path='rotation_euler', frame=abs_f)\n"
            "                    _sec_pb.keyframe_insert(data_path='location',       frame=abs_f)\n"
            "                    _sec_pb.keyframe_insert(data_path='scale',          frame=abs_f)\n"
            "        else:\n"
            "            for bone_name, fn in bone_funcs.items():\n"
            "                _sec_pb = _sec_obj.pose.bones.get(bone_name)\n"
            "                if not _sec_pb: continue\n"
            "                _sec_pb.rotation_mode = 'XYZ'\n"
            "                for local_f in range(1, total_frames + 1):\n"
            "                    abs_f = start_frame + (local_f - 1)\n"
            "                    kf = fn(local_f)\n"
            "                    _sec_pb.rotation_euler = kf['rot']\n"
            "                    _sec_pb.location       = kf['loc']\n"
            "                    _sec_pb.scale          = kf['sca']\n"
            "                    _sec_pb.keyframe_insert(data_path='rotation_euler', frame=abs_f)\n"
            "                    _sec_pb.keyframe_insert(data_path='location',       frame=abs_f)\n"
            "                    _sec_pb.keyframe_insert(data_path='scale',          frame=abs_f)\n"
            "        for fc in _get_action_fcurves(_sec_action):\n"
            "            for kp in fc.keyframe_points:\n"
            "                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'\n"
            "        _sec_obj.animation_data.action = None\n"
            "        _sec_track = _sec_obj.animation_data.nla_tracks.new()\n"
            "        _sec_track.name = f'Slot_{SLOT_INDEX:03d}_{_sec_name}'\n"
            "        _sec_strip = _sec_track.strips.new(_sec_action_name, start_frame, _sec_action)\n"
            "        _sec_strip.frame_end        = end_frame\n"
            "        _sec_strip.extrapolation    = 'NOTHING'\n"
            "        _sec_strip.use_auto_blend   = False\n"
            "        _sec_strip.blend_in         = 0\n"
            "        _sec_strip.blend_out        = 0\n"
            "    # ── Restaurar contexto al armature principal ──\n"
            "    bpy.context.view_layer.objects.active = armature\n"
            "    bpy.ops.object.mode_set(mode='POSE')\n"
            "    armature.animation_data.action = _arm_action\n\n"
            "    # ── Aplicar rotacion del armature por frame (orientacion por pose) ──\n"
            "    if ARMATURE_ROTATIONS:\n"
            "        armature.rotation_mode = 'XYZ'\n"
            "        if not armature.animation_data:\n"
            "            armature.animation_data_create()\n"
            f"        _arm_obj_action_name = f'slot_{{SLOT_INDEX:03d}}_{char_tag}_arm_obj_rot'\n"
            "        _arm_obj_existing = bpy.data.actions.get(_arm_obj_action_name)\n"
            "        if _arm_obj_existing: bpy.data.actions.remove(_arm_obj_existing)\n"
            "        _arm_obj_action = bpy.data.actions.new(name=_arm_obj_action_name)\n"
            "        armature.animation_data.action = _arm_obj_action\n"
            "        for lf, rot in ARMATURE_ROTATIONS.items():\n"
            "            abs_f = start_frame + (lf - 1)\n"
            "            bpy.context.scene.frame_set(abs_f)\n"
            "            armature.rotation_euler = rot\n"
            "            armature.keyframe_insert(data_path='rotation_euler', frame=abs_f)\n"
            "        for fc in _get_action_fcurves(_arm_obj_action):\n"
            "            for kp in fc.keyframe_points:\n"
            "                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'\n"
            "        armature.animation_data.action = None\n"
            f"        _arm_obj_track = armature.animation_data.nla_tracks.new()\n"
            f"        _arm_obj_track.name = f'Slot_{{SLOT_INDEX:03d}}_{char_tag}_arm_obj_rot'\n"
            "        _arm_obj_strip = _arm_obj_track.strips.new(_arm_obj_action_name, start_frame, _arm_obj_action)\n"
            "        _arm_obj_strip.frame_end     = end_frame\n"
            "        _arm_obj_strip.extrapolation = 'NOTHING'\n"
            "        _arm_obj_strip.use_auto_blend = False\n"
            "        _arm_obj_strip.blend_in  = 0\n"
            "        _arm_obj_strip.blend_out = 0\n\n"
            "    # [FIX] Restaurar _arm_action como accion activa para keyframes de bones\n"
            "    armature.animation_data.action = _arm_action\n\n"
            "    if armature.animation_data and armature.animation_data.action:\n"
            "        for fc in _get_action_fcurves(_arm_action):\n"
            "            for kp in fc.keyframe_points:\n"
            "                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'\n\n"
            "    if root and root.animation_data and root.animation_data.action:\n"
            "        for fc in _get_action_fcurves(root.animation_data.action):\n"
            "            for kp in fc.keyframe_points:\n"
            "                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'\n\n"
            f"    print(f'ANIMACION {anim_name} APLICADA!')\n"
            "    print(f'  Frames: {start_frame}-{end_frame}')\n\n"
            "    # ── Aplicar BLINK_SEQUENCE a los ojos del personaje ─────────────────\n"
            "    if BLINK_SEQUENCE:\n"
            "        _eye_names   = ['ojo_izquierdo_jerry', 'ojo_derecho_jerry']\n"
            "        _pupil_names = ['pupila_izquierda_jerry', 'pupila_derecha_jerry']\n"
            "        _all_eye_obj = [bpy.data.objects.get(n) for n in _eye_names   if bpy.data.objects.get(n)]\n"
            "        _all_pup_obj = [bpy.data.objects.get(n) for n in _pupil_names if bpy.data.objects.get(n)]\n"
            "        for _eye_obj in _all_eye_obj + _all_pup_obj:\n"
            "            if not _eye_obj or _eye_obj.type != 'MESH': continue\n"
            "            if not _eye_obj.data.shape_keys:\n"
            "                _eye_obj.shape_key_add(name='Basis', from_mix=False)\n"
            "            # Reconstruir 'Closed' con geometria cortina (verts -> min_z_mundo)\n"
            "            _ck = _eye_obj.data.shape_keys.key_blocks.get('Closed')\n"
            "            if _ck: _eye_obj.shape_key_remove(_ck)\n"
            "            import mathutils as _mub\n"
            "            _ck = _eye_obj.shape_key_add(name='Closed', from_mix=False)\n"
            "            _mw = _eye_obj.matrix_world; _ml = _mw.inverted()\n"
            "            _vwl = [_mw @ v.co for v in _eye_obj.data.vertices]\n"
            "            _minz = min(v.z for v in _vwl)\n"
            "            for _vi, _vc in enumerate(_vwl): _ck.data[_vi].co = _ml @ _mub.Vector((_vc.x, _vc.y, _minz))\n"
            "            for _lf, _bdata in sorted(BLINK_SEQUENCE.items()):\n"
            "                _abs_f = start_frame + (_lf - 1)\n"
            "                _ck.value = float(_bdata.get('closed', 0.0))\n"
            "                _ck.keyframe_insert(data_path='value', frame=_abs_f)\n"
            "            for _lf, _bdata in sorted(BLINK_SEQUENCE.items()):\n"
            "                _abs_f = start_frame + (_lf - 1)\n"
            "                _eye_obj.hide_render   = bool(_bdata.get('hide', False))\n"
            "                _eye_obj.hide_viewport = bool(_bdata.get('hide', False))\n"
            "                _eye_obj.keyframe_insert(data_path='hide_render',   frame=_abs_f)\n"
            "                _eye_obj.keyframe_insert(data_path='hide_viewport', frame=_abs_f)\n"
            "        _n_eyes = len(_all_eye_obj) + len(_all_pup_obj)\n"
            "        if _n_eyes:\n"
            "            print(f'  Parpadeo: {len(BLINK_SEQUENCE)} frames aplicados en {_n_eyes} objetos')\n"
            "        else:\n"
            "            print('  Parpadeo: sin mallas de ojos en escena (omitido)')\n"
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
            "            _kf1 = _POSE_FRAME_1[_sp_bone.name]\n"
            "            _sp_bone.rotation_euler = _kf1['rot']\n"
            "            _sp_bone.location       = _kf1['loc']\n"
            "            _sp_bone.scale          = _kf1['sca']\n"
            "            _sp_bone.keyframe_insert(data_path='rotation_euler', frame=start_frame)\n"
            "            _sp_bone.keyframe_insert(data_path='location',       frame=start_frame)\n"
            "            _sp_bone.keyframe_insert(data_path='scale',          frame=start_frame)\n"
            "        if _sp_bone.name in _POSE_FRAME_END:\n"
            "            bpy.context.scene.frame_set(end_frame)\n"
            "            _kfE = _POSE_FRAME_END[_sp_bone.name]\n"
            "            _sp_bone.rotation_euler = _kfE['rot']\n"
            "            _sp_bone.location       = _kfE['loc']\n"
            "            _sp_bone.scale          = _kfE['sca']\n"
            "            _sp_bone.keyframe_insert(data_path='rotation_euler', frame=end_frame)\n"
            "            _sp_bone.keyframe_insert(data_path='location',       frame=end_frame)\n"
            "            _sp_bone.keyframe_insert(data_path='scale',          frame=end_frame)\n"
            "    # ── Fin forzado ──\n\n"
            "    # Mover Action del ARMATURE al NLA\n"
            "    if armature.animation_data and armature.animation_data.action:\n"
            "        _arm_done  = armature.animation_data.action\n"
            "        armature.animation_data.action = None\n"
            "        _arm_track = armature.animation_data.nla_tracks.new()\n"
            f"        _arm_track.name = f'Slot_{{SLOT_INDEX:03d}}_{char_tag}_arm'\n"
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
            f"        _root_track.name = f'Slot_{{SLOT_INDEX:03d}}_{char_tag}_root'\n"
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
        self.report({"INFO"}, f"Exportado (1 coord): {filepath}")
        return {"FINISHED"}


# =============================================================================
# IMPORTAR .py
# =============================================================================

class JRRST_OT_ImportAnimation(Operator):
    bl_idname    = "jerryst.import_animation"
    bl_label     = "Importar animacion .py"
    bl_description = "Carga un .py exportado y lo aplica en la timeline"
    bl_options   = {"REGISTER", "UNDO"}

    filepath:    StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.py", options={"HIDDEN"})

    def invoke(self, context, event):
        start = bpy.path.abspath(context.scene.jerryst.anim_dir)
        if os.path.isdir(start):
            self.filepath = start + os.sep
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        st    = context.scene.jerryst
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
            self.report({"ERROR"}, "Dog_001_rig no valido")
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

        # Compatibilidad con el formato del conversor de Mixamo (Kebyn,
        # 2026-09-14): ese formato no define TOTAL_FRAMES/BONES_LISTA como
        # variables sueltas -- el frame count vive dentro de
        # ANIMATION_INFO['frame_count'] y la lista de bones son las claves
        # de KEYFRAME_DATA. Sin este fallback, total_f quedaba en 0 y el
        # operador cancelaba sin insertar ningun keyframe (el rig se
        # quedaba en la pose actual, dando la impresion de que "no pasa
        # nada").
        if total_f == 0 and kf_data:
            anim_info = ns.get("ANIMATION_INFO", {})
            total_f = anim_info.get("frame_count", 0)
            if total_f == 0:
                total_f = max(
                    (max(bone_kf.keys()) for bone_kf in kf_data.values() if bone_kf),
                    default=0,
                )
        if bones_lista is BONES_LISTA and kf_data and not any(
            bn in kf_data for bn in BONES_LISTA
        ):
            bones_lista = list(kf_data.keys())

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

class JRRST_OT_ExtractPose(Operator):
    bl_idname    = "jerryst.extract_pose"
    bl_label     = "Guardar como nueva pose"
    bl_description = "Extrae la pose del frame indicado y la guarda en la libreria"
    bl_options   = {"REGISTER"}

    def execute(self, context):
        st    = context.scene.jerryst
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
            self.report({"ERROR"}, "Dog_001_rig no valido")
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

        # Capturar la posicion/orientacion del Root (Empty "jerry") en este
        # frame. Sin esto, get_root_transform_from_record() no encuentra la
        # entrada "jerry" en bones_data y la pose se reproduce en (0,0,0) al
        # concatenarla, sin importar donde estaba parado el Empty al extraer.
        root_obj = scene.objects.get("jerry")
        if root_obj is not None:
            loc = root_obj.location
            rot = root_obj.rotation_euler
            root_local_space = {
                "location": {
                    "x": round(loc.x, 6),
                    "y": round(loc.y, 6),
                    "z": round(loc.z, 6),
                },
                "rotation_euler_rad": {
                    "x": round(rot.x, 6),
                    "y": round(rot.y, 6),
                    "z": round(rot.z, 6),
                },
                "rotation_euler_deg": {
                    "x": round(math.degrees(rot.x), 4),
                    "y": round(math.degrees(rot.y), 4),
                    "z": round(math.degrees(rot.z), 4),
                },
                "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
            }
            bones_data["jerry"] = {
                "parent":    None,
                "connected": False,
                "local_space": root_local_space,
                "rotation_mode": "XYZ",
                "raw_rotation_euler_deg": root_local_space["rotation_euler_deg"],
                "raw_rotation_quaternion": None,
                "raw_location": root_local_space["location"],
                "raw_scale":    root_local_space["scale"],
            }
        else:
            self.report({"WARNING"},
                "No se encontro el Empty 'jerry' en la escena; la pose se "
                "guardara sin coordenada de Root (se reproducira en 0,0,0).")

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

# =============================================================================
# HELPER: generar BLINK_SEQUENCE real desde eye_system para el .py exportado
# =============================================================================

def _build_blink_sequence_data(scene, start_f, end_f):
    """
    Calcula el mapa de parpadeo usando la misma logica que apply_blink_with_pupils
    en eye_system.py, leyendo los parametros reales del eye_system configurado
    en la escena (blink_count, blink_duration, blink_frame_start, blink_frame_end).

    Devuelve un dict  { local_frame: {"closed": float, "hide": bool} }
    donde local_frame es relativo a start_f (local_frame 1 = start_f).

    Si el parpadeo no esta habilitado o no hay configuracion, devuelve {}.
    """
    _segs_st = getattr(scene, "jerry_segs", None)
    if _segs_st is None:
        return {}

    eye_s = getattr(_segs_st, "eye_expr", None)
    if eye_s is None:
        return {}

    if not getattr(eye_s, "blink_enabled", False):
        # Tambien activar si el sistema activo incluye parpadeo
        active_sys = getattr(eye_s, "active_eye_system", "SISTEMA_1")
        if active_sys not in ("SISTEMA_2", "AMBOS"):
            return {}

    blink_count    = getattr(eye_s, "blink_count",    2)
    blink_duration = getattr(eye_s, "blink_duration", 9)
    blink_start    = getattr(eye_s, "blink_frame_start", start_f)
    blink_end      = getattr(eye_s, "blink_frame_end",   end_f)

    # Acotar al rango real del slot
    sf = max(start_f, blink_start)
    ef = min(end_f,   blink_end)
    if sf >= ef:
        return {}

    dur          = max(blink_duration, 6)
    total_frames = ef - sf + 1

    # ── Misma curva que _blink_curve_value en eye_system.py ──────────────
    def _blink_curve_value(offset, total_dur):
        import math as _m
        t          = max(0.0, min(1.0, (offset - 1) / max(total_dur - 1, 1)))
        close_end  = 0.40
        open_start = 0.60
        if t <= close_end:
            p = t / close_end
            return p * p * (3.0 - 2.0 * p)
        elif t <= open_start:
            return 1.0
        else:
            p = (t - open_start) / (1.0 - open_start)
            return 1.0 - (p * p * (3.0 - 2.0 * p))

    # ── Calcular frames de inicio de cada parpadeo ────────────────────────
    # Dividir el rango en blink_count slots iguales y centrar cada parpadeo
    # dentro de su slot — garantiza exactamente blink_count parpadeos visibles.
    slot_size    = total_frames / blink_count
    blink_starts = []
    for i in range(blink_count):
        slot_center = sf + slot_size * i + slot_size / 2
        bs = int(slot_center - dur / 2)
        bs = max(sf, min(bs, ef - dur + 1))
        blink_starts.append(bs)

    # ── Construir mapa frame_absoluto → valor ────────────────────────────
    blink_map = {}
    for bs in blink_starts:
        for offset in range(1, dur + 1):
            frm = bs + offset - 1
            if frm > ef:
                break
            val = _blink_curve_value(offset, dur)
            blink_map[frm] = max(blink_map.get(frm, 0.0), val)

    # ── Keyframes de anclaje en 0.0 ──────────────────────────────────────
    anchor_zeros = set()
    for bs in blink_starts:
        anchor_zeros.add(max(sf, bs - 1))
        anchor_zeros.add(min(ef, bs + dur))
    anchor_zeros.add(sf)
    anchor_zeros.add(ef)

    all_kf_frames = sorted(set(list(blink_map.keys()) + list(anchor_zeros)))

    # ── Convertir a frames locales (1-based relativo a start_f) ──────────
    result = {}
    for abs_f in all_kf_frames:
        lf  = abs_f - start_f + 1
        val = round(blink_map.get(abs_f, 0.0), 6)
        closed_val = val
        hide       = closed_val >= 1.0
        result[lf] = {"closed": closed_val, "hide": hide}

    return result


def _blink_sequence_to_code(blink_data):
    """
    Serializa el dict devuelto por _build_blink_sequence_data como bloque
    Python literal para incluir en el .py exportado.
    """
    if not blink_data:
        return "BLINK_SEQUENCE = {}\n\n"
    lines = ["BLINK_SEQUENCE = {"]
    for lf in sorted(blink_data.keys()):
        d = blink_data[lf]
        lines.append(
            f"    {lf}: {{\"closed\": {d['closed']}, \"hide\": {d['hide']}}},")
    lines.append("}\n")
    return "\n".join(lines) + "\n"


# =============================================================================
# HELPER: serializar oscilaciones de bones para el .py exportado
# =============================================================================

def _build_bone_oscillations_code(st):
    """
    Genera el bloque BONE_OSCILLATIONS_CONFIG para el .py exportado de jerry.
    Incluye todas las oscilaciones definidas (enabled y disabled) para que el
    importador pueda restaurar el estado completo del panel.
    """
    osc = st.bone_oscillations
    items_list = []
    for item in osc.items:
        items_list.append({
            "label":        item.label,
            "bone_name":    item.bone_name,
            "frame_start":  item.frame_start,
            "frame_end":    item.frame_end,
            "axis_x":       item.axis_x,
            "axis_y":       item.axis_y,
            "axis_z":       item.axis_z,
            "amplitude":    round(item.amplitude, 2),
            "angle_offset": round(item.angle_offset, 2),
            "num_cycles":   item.num_cycles,
            "phase":        round(item.phase, 4),
            "wave_type":    item.wave_type,
            "fade_in":      item.fade_in,
            "fade_out":     item.fade_out,
            "noise_seed":   item.noise_seed,
            "enabled":      item.enabled,
        })
    cfg = {
        "enabled": osc.enabled,
        "items":   items_list,
    }
    import json as _json
    serialized = _json.dumps(cfg, ensure_ascii=False)
    return (
        "# ── Oscilaciones de bones (jerry) ───────────────────────\n"
        "import json as _json_bosc_jerry\n"
        f"BONE_OSCILLATIONS_CONFIG = _json_bosc_jerry.loads({repr(serialized)})\n"
    )


# =============================================================================
# FUNCION CENTRAL: APLICAR OSCILACIONES DE BONES (jerry)
# =============================================================================

def _apply_bone_oscillations(context, armature, osc_settings, filtered_bones=None):
    """
    Aplica todas las oscilaciones de bones definidas en osc_settings sobre
    las fcurves del armature de jerry. Se llama desde CONCATENAR
    como post-proceso.
    """
    import math as _m
    filtered_bones = set(filtered_bones or ())

    if not osc_settings.enabled:
        return
    if not osc_settings.items:
        return
    if not armature.animation_data or not armature.animation_data.action:
        return

    action = armature.animation_data.action

    def _noise_osc(frame, speed, seed, dim=0):
        import mathutils
        scale = speed * 20.0
        p = mathutils.noise.noise_vector(
            mathutils.Vector((frame * scale + seed * 13.7,
                               dim * 137.3 + seed * 0.17,
                               0.0))
        )
        return p[0]

    def _wave_value(wave_type, frame, speed, phase, seed):
        t = frame * speed * 2 * _m.pi + phase

        if wave_type == "SINE":
            return _m.sin(t)

        elif wave_type == "TRIANGLE":
            frac = (t / (2 * _m.pi)) % 1.0
            return 1.0 - abs(4.0 * frac - 2.0) + 1.0 - 2.0

        elif wave_type == "SQUARE":
            return 1.0 if _m.sin(t) >= 0 else -1.0

        elif wave_type == "NOISE":
            return _noise_osc(frame, speed, seed)

        elif wave_type == "SINE_EASE":
            s = (_m.sin(t) + 1.0) * 0.5
            s = s * s * (3.0 - 2.0 * s)
            return s * 2.0 - 1.0

        elif wave_type == "ELASTIC":
            frac = (t / (2 * _m.pi)) % 1.0
            if frac < 0.6:
                v = _m.sin(frac / 0.6 * _m.pi * 0.5)
            else:
                r = (frac - 0.6) / 0.4
                decay = _m.exp(-r * 4.0)
                v = -decay * _m.cos(r * _m.pi * 5.0) * 0.35
            return v

        elif wave_type == "BOUNCE":
            frac = (t / (2 * _m.pi)) % 1.0
            peaks = [(0.0, 1.0), (0.55, 0.45), (0.78, 0.18), (0.92, 0.06), (1.0, 0.0)]
            for i in range(len(peaks) - 1):
                x0, h0 = peaks[i]
                x1, h1 = peaks[i + 1]
                if x0 <= frac < x1:
                    local = (frac - x0) / (x1 - x0)
                    h_max = (h0 + h1) * 0.5
                    v = h_max * (1.0 - (2.0 * local - 1.0) ** 2)
                    return v * 2.0 - 0.5
            return -0.5

        elif wave_type == "BREATHE":
            frac = (t / (2 * _m.pi)) % 1.0
            if frac < 0.6:
                v = _m.sin(frac / 0.6 * _m.pi)
            else:
                v = -_m.sin((frac - 0.6) / 0.4 * _m.pi) * 0.4
            return v

        elif wave_type == "HEARTBEAT":
            frac = (t / (2 * _m.pi)) % 1.0
            def _pulse(x, center, width):
                if abs(x - center) < width:
                    return _m.sin((x - center) / width * _m.pi)
                return 0.0
            v  = _pulse(frac, 0.10, 0.08)
            v += _pulse(frac, 0.25, 0.05) * 0.6
            return v

        elif wave_type == "NOISE_DRIFT":
            high  = _noise_osc(frame, speed,        seed)
            drift = _m.sin(frame * speed * 0.3 * _m.pi + phase)
            return high * 0.6 + drift * 0.4

        elif wave_type == "NOISE_LAYERED":
            n1 = _noise_osc(frame, speed,        seed)
            n2 = _noise_osc(frame, speed * 2.7,  seed + 31)
            n3 = _noise_osc(frame, speed * 7.0,  seed + 97)
            return n1 * 0.55 + n2 * 0.30 + n3 * 0.15

        elif wave_type == "SAW_SMOOTH":
            frac = (t / (2 * _m.pi)) % 1.0
            if frac < 0.8:
                v = frac / 0.8
                v = v * v * (3.0 - 2.0 * v) * 2.0 - 1.0
            else:
                v = 1.0 - (frac - 0.8) / 0.2 * 2.0
            return v

        elif wave_type == "SAW_REVERSE":
            frac = (t / (2 * _m.pi)) % 1.0
            if frac < 0.2:
                v = frac / 0.2
            else:
                v = 1.0 - (frac - 0.2) / 0.8
                v = v * v * (3.0 - 2.0 * v)
            return v * 2.0 - 1.0

        elif wave_type == "PENDULUM":
            s = _m.sin(t)
            if abs(s) < 0.9999:
                return _m.asin(s) / (_m.pi * 0.5)
            return _m.copysign(1.0, s)

        elif wave_type == "QUIVER":
            envelope = (_m.sin(t * 0.25) + 1.0) * 0.5
            quiver   = _m.sin(t * 7.0 + _m.sin(t * 2.3) * 1.5)
            return quiver * (0.4 + envelope * 0.6)

        return _m.sin(t)

    for item in osc_settings.items:
        if not item.enabled:
            continue
        bone_name = item.bone_name.strip()
        if not bone_name or bone_name in filtered_bones:
            continue

        active_axes = [(ax, idx) for ax, idx, flag in
                       [("X", 0, item.axis_x), ("Y", 1, item.axis_y), ("Z", 2, item.axis_z)]
                       if flag]
        if not active_axes:
            continue

        dp   = f'pose.bones["{bone_name}"].rotation_euler'
        sf   = item.frame_start
        ef   = item.frame_end
        if sf >= ef:
            continue

        dur        = ef - sf
        speed      = item.num_cycles / max(1, dur)
        amplitude  = _m.radians(item.amplitude)
        ang_offset = _m.radians(item.angle_offset)
        phase      = item.phase
        wave_type  = item.wave_type
        seed       = item.noise_seed
        fade_in_f  = max(0, item.fade_in)
        fade_out_f = max(0, item.fade_out)

        for _ax_name, ax_idx in active_axes:
            fc = _get_action_fcurves(action).find(dp, index=ax_idx)
            if fc is None:
                fc = _new_fcurve(_get_action_fcurves(action), dp, index=ax_idx, action_group=bone_name)

            try:
                pose_base_value = fc.evaluate(sf)
            except Exception:
                pose_base_value = 0.0

            idxs = [i for i, kp in enumerate(fc.keyframe_points)
                    if sf <= int(kp.co.x) <= ef]
            for i in reversed(idxs):
                fc.keyframe_points.remove(fc.keyframe_points[i])

            for f in range(sf, ef + 1):
                raw = _wave_value(wave_type, f, speed, phase, seed)
                osc_center = pose_base_value + ang_offset
                val = osc_center + amplitude * raw

                if fade_in_f > 0 and (f - sf) < fade_in_f:
                    t_fade = (f - sf) / fade_in_f
                    t_fade = t_fade * t_fade * (3.0 - 2.0 * t_fade)
                    val = osc_center + (val - osc_center) * t_fade

                if fade_out_f > 0 and (ef - f) < fade_out_f:
                    t_fade = (ef - f) / fade_out_f
                    t_fade = t_fade * t_fade * (3.0 - 2.0 * t_fade)
                    val = osc_center + (val - osc_center) * t_fade

                fc.keyframe_points.insert(frame=f, value=val, options={"FAST"})

            for kp in fc.keyframe_points:
                if sf <= int(kp.co.x) <= ef:
                    kp.interpolation = "BEZIER"
                    kp.easing = "AUTO"
            fc.update()


# =============================================================================
# OPERADORES: BONE OSCILLATIONS (jerry)
# =============================================================================

class JRRST_OT_BoneOscAddItem(Operator):
    """Agrega una nueva oscilacion de bone a la lista."""
    bl_idname    = "jerryst.bone_osc_add_item"
    bl_label     = "Agregar oscilacion de bone"
    bl_description = "Agrega la oscilacion definida abajo a la lista"
    bl_options   = {"REGISTER", "UNDO"}

    quick_bone: bpy.props.StringProperty(default="")

    def execute(self, context):
        osc = context.scene.jerryst.bone_oscillations
        item = osc.items.add()
        item.label        = osc.edit_label
        item.bone_name    = self.quick_bone if self.quick_bone else osc.edit_bone_name
        item.frame_start  = osc.edit_frame_start
        item.frame_end    = osc.edit_frame_end
        item.axis_x       = osc.edit_axis_x
        item.axis_y       = osc.edit_axis_y
        item.axis_z       = osc.edit_axis_z
        item.amplitude    = osc.edit_amplitude
        item.angle_offset = osc.edit_angle_offset
        item.num_cycles   = osc.edit_num_cycles
        item.phase        = osc.edit_phase
        item.wave_type    = osc.edit_wave_type
        item.fade_in      = osc.edit_fade_in
        item.fade_out     = osc.edit_fade_out
        item.noise_seed   = osc.edit_noise_seed
        item.enabled      = True
        osc.active_idx    = len(osc.items) - 1
        if self.quick_bone:
            item.label = self.quick_bone
        self.report({"INFO"}, f"Oscilacion '{item.label}' agregada")
        return {"FINISHED"}


class JRRST_OT_BoneOscRemoveItem(Operator):
    """Elimina la oscilacion de bone en el indice dado."""
    bl_idname  = "jerryst.bone_osc_remove_item"
    bl_label   = "Eliminar oscilacion"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        osc = context.scene.jerryst.bone_oscillations
        if 0 <= self.item_idx < len(osc.items):
            osc.items.remove(self.item_idx)
            osc.active_idx = max(0, min(osc.active_idx, len(osc.items) - 1))
        return {"FINISHED"}


class JRRSTST_OT_BoneOscMoveItem(Operator):
    """Mueve la oscilacion seleccionada arriba o abajo."""
    bl_idname  = "jerryst.bone_osc_move_item"
    bl_label   = "Mover oscilacion"
    bl_options = {"REGISTER", "UNDO"}

    direction: bpy.props.EnumProperty(items=[("UP","Arriba",""),("DOWN","Abajo","")])

    def execute(self, context):
        osc = context.scene.jerryst.bone_oscillations
        idx = osc.active_idx
        n   = len(osc.items)
        if self.direction == "UP" and idx > 0:
            osc.items.move(idx, idx - 1)
            osc.active_idx -= 1
        elif self.direction == "DOWN" and idx < n - 1:
            osc.items.move(idx, idx + 1)
            osc.active_idx += 1
        return {"FINISHED"}


class JRRSTST_OT_BoneOscDuplicateItem(Operator):
    """Duplica la oscilacion de bone en el indice dado."""
    bl_idname  = "jerryst.bone_osc_duplicate_item"
    bl_label   = "Duplicar oscilacion"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        osc = context.scene.jerryst.bone_oscillations
        if 0 <= self.item_idx < len(osc.items):
            src = osc.items[self.item_idx]
            new = osc.items.add()
            for attr in ("label", "bone_name", "frame_start", "frame_end",
                         "axis_x", "axis_y", "axis_z", "amplitude", "angle_offset",
                         "num_cycles", "phase", "wave_type", "fade_in", "fade_out",
                         "noise_seed", "enabled"):
                setattr(new, attr, getattr(src, attr))
            new.label = src.label + "_copia"
            osc.active_idx = len(osc.items) - 1
        return {"FINISHED"}


class JRRSTST_OT_BoneOscToggleItem(Operator):
    """Selecciona como activo y/o activa/desactiva la oscilacion."""
    bl_idname  = "jerryst.bone_osc_toggle_item"
    bl_label   = "Seleccionar / toggle oscilacion"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        osc = context.scene.jerryst.bone_oscillations
        if 0 <= self.item_idx < len(osc.items):
            if osc.active_idx == self.item_idx:
                osc.items[self.item_idx].enabled = not osc.items[self.item_idx].enabled
            else:
                osc.active_idx = self.item_idx
        return {"FINISHED"}


class JRRSTST_OT_BoneOscPickBone(Operator):
    """
    Copia el nombre del bone detectado desde el JSON de historia
    al campo 'Bone' del editor de nueva oscilacion.
    """
    bl_idname    = "jerryst.bone_osc_pick_bone"
    bl_label     = "Seleccionar bone"
    bl_description = "Usar este bone en el editor de nueva oscilacion"
    bl_options   = {"REGISTER", "UNDO"}

    bone_name: bpy.props.StringProperty(default="")

    def execute(self, context):
        osc = context.scene.jerryst.bone_oscillations
        osc.edit_bone_name = self.bone_name
        if not osc.edit_label or osc.edit_label == "Mi oscilacion":
            osc.edit_label = self.bone_name
        return {"FINISHED"}


# =============================================================================
# HELPER: resolver "organic" del segmento activo (aislamiento por segmento)
# =============================================================================

def _resolve_seg_organic(context, seg_idx):
    """Devuelve la instancia de JerryOrganicFilters correspondiente.

    AISLAMIENTO POR SEGMENTO (Kebyn + Claude, 2026-08-06): los operadores de
    orejas/mandibula/emociones de aca abajo antes escribian siempre sobre
    scene.jerryst.organic -- una UNICA instancia global -- sin importar
    desde que box de segmento se hubiera presionado el boton. Eso hacia que
    agregar/editar/quitar un intervalo en el box de un segmento lo
    agregara/quitara para TODOS los segmentos, porque en realidad todos
    apuntaban al mismo dato (mismo bug que el de seg.organic, ver
    JerryAnimSegment en properties.py).

    Ahora cada boton del panel pasa su propio `seg_idx` (indice del
    segmento cuyo box se esta dibujando, ver panels.py) y esta funcion
    resuelve la instancia PROPIA de ESE segmento (segs.segments[seg_idx].organic).
    seg_idx = -1 (default) es el fallback a scene.jerryst.organic, para
    paneles fuera de un segmento o compatibilidad con llamadas antiguas.
    """
    if seg_idx is not None and seg_idx >= 0:
        segs = getattr(context.scene, "jerry_segs", None)
        if segs is not None and 0 <= seg_idx < len(segs.segments):
            return segs.segments[seg_idx].organic
    return context.scene.jerryst.organic


# =============================================================================
# OPERADORES: OREJAS  (ear.L / ear.R)
# =============================================================================

class JRRSTST_OT_EarOscAdd(Operator):
    """Agrega un intervalo de oscilacion de orejas."""
    bl_idname = "jerryst.ear_osc_add"
    bl_label  = "Agregar intervalo orejas"
    bl_options = {"REGISTER", "UNDO"}

    seg_idx: IntProperty(default=-1)

    def execute(self, context):
        og = _resolve_seg_organic(context, self.seg_idx)
        item = og.ear_items.add()
        item.label       = og.ear_edit_label
        item.frame_start = og.ear_edit_frame_start
        item.frame_end   = og.ear_edit_frame_end
        item.amplitude   = og.ear_edit_amplitude
        item.speed       = og.ear_edit_speed
        item.phase_l     = og.ear_edit_phase_l
        item.phase_r     = og.ear_edit_phase_r
        item.axis        = og.ear_edit_axis
        item.enabled     = True
        og.ear_active_idx = len(og.ear_items) - 1
        self.report({"INFO"}, f"Intervalo orejas '{item.label}' agregado")
        return {"FINISHED"}


class JRRSTST_OT_EarOscRemove(Operator):
    """Elimina un intervalo de oscilacion de orejas."""
    bl_idname = "jerryst.ear_osc_remove"
    bl_label  = "Eliminar intervalo orejas"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)
    seg_idx: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        og = _resolve_seg_organic(context, self.seg_idx)
        if 0 <= self.item_idx < len(og.ear_items):
            og.ear_items.remove(self.item_idx)
            og.ear_active_idx = max(0, min(og.ear_active_idx, len(og.ear_items) - 1))
        return {"FINISHED"}


class JRRSTST_OT_EarOscToggle(Operator):
    """Activa/desactiva un intervalo de orejas."""
    bl_idname = "jerryst.ear_osc_toggle"
    bl_label  = "Toggle intervalo orejas"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)
    seg_idx: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        og = _resolve_seg_organic(context, self.seg_idx)
        if 0 <= self.item_idx < len(og.ear_items):
            if og.ear_active_idx == self.item_idx:
                og.ear_items[self.item_idx].enabled = not og.ear_items[self.item_idx].enabled
            else:
                og.ear_active_idx = self.item_idx
        return {"FINISHED"}


class JRRSTST_OT_EarOscLoad(Operator):
    """Carga un intervalo de orejas al formulario para editarlo."""
    bl_idname = "jerryst.ear_osc_load"
    bl_label  = "Editar intervalo orejas"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)
    seg_idx: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        og = _resolve_seg_organic(context, self.seg_idx)
        if 0 <= self.item_idx < len(og.ear_items):
            src = og.ear_items[self.item_idx]
            og.ear_edit_label       = src.label
            og.ear_edit_frame_start = src.frame_start
            og.ear_edit_frame_end   = src.frame_end
            og.ear_edit_amplitude   = src.amplitude
            og.ear_edit_speed       = src.speed
            og.ear_edit_phase_l     = src.phase_l
            og.ear_edit_phase_r     = src.phase_r
            og.ear_edit_axis        = src.axis
            og.ear_active_idx       = self.item_idx
            og.ear_edit_mode        = "EDIT"
            og.ear_edit_source_idx  = self.item_idx
        return {"FINISHED"}


class JRRSTST_OT_EarOscSave(Operator):
    """Guarda los cambios del formulario sobre el intervalo de orejas."""
    bl_idname = "jerryst.ear_osc_save"
    bl_label  = "Guardar intervalo orejas"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        og = _resolve_seg_organic(context, self.seg_idx)
        idx = og.ear_edit_source_idx
        if 0 <= idx < len(og.ear_items):
            dst = og.ear_items[idx]
            dst.label       = og.ear_edit_label
            dst.frame_start = og.ear_edit_frame_start
            dst.frame_end   = og.ear_edit_frame_end
            dst.amplitude   = og.ear_edit_amplitude
            dst.speed       = og.ear_edit_speed
            dst.phase_l     = og.ear_edit_phase_l
            dst.phase_r     = og.ear_edit_phase_r
            dst.axis        = og.ear_edit_axis
            og.ear_edit_mode       = "ADD"
            og.ear_edit_source_idx = -1
            self.report({"INFO"}, f"Intervalo orejas '{dst.label}' actualizado")
        return {"FINISHED"}


class JRRSTST_OT_EarOscCancel(Operator):
    """Cancela la edicion de orejas."""
    bl_idname = "jerryst.ear_osc_cancel"
    bl_label  = "Cancelar edicion orejas"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        og = _resolve_seg_organic(context, self.seg_idx)
        og.ear_edit_mode       = "ADD"
        og.ear_edit_source_idx = -1
        return {"FINISHED"}


# =============================================================================
# OPERADORES: MANDIBULA  (jaw_bot)
# =============================================================================

class JRRSTST_OT_JawOscAdd(Operator):
    """Agrega un intervalo de oscilacion de mandibula."""
    bl_idname = "jerryst.jaw_osc_add"
    bl_label  = "Agregar intervalo mandibula"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        og = _resolve_seg_organic(context, self.seg_idx)
        item = og.jaw_items.add()
        item.label       = og.jaw_edit_label
        item.frame_start = og.jaw_edit_frame_start
        item.frame_end   = og.jaw_edit_frame_end
        item.amplitude   = og.jaw_edit_amplitude
        item.cycles      = og.jaw_edit_cycles
        item.phase       = og.jaw_edit_phase
        item.transition  = og.jaw_edit_transition
        item.noise_seed  = og.jaw_edit_noise_seed
        item.enabled     = True
        og.jaw_active_idx = len(og.jaw_items) - 1
        self.report({"INFO"}, f"Intervalo mandibula '{item.label}' agregado")
        return {"FINISHED"}


class JRRSTST_OT_JawOscRemove(Operator):
    """Elimina un intervalo de oscilacion de mandibula."""
    bl_idname = "jerryst.jaw_osc_remove"
    bl_label  = "Eliminar intervalo mandibula"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)
    seg_idx: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        og = _resolve_seg_organic(context, self.seg_idx)
        if 0 <= self.item_idx < len(og.jaw_items):
            og.jaw_items.remove(self.item_idx)
            og.jaw_active_idx = max(0, min(og.jaw_active_idx, len(og.jaw_items) - 1))
        return {"FINISHED"}


class JRRSTST_OT_JawOscToggle(Operator):
    """Activa/desactiva un intervalo de mandibula."""
    bl_idname = "jerryst.jaw_osc_toggle"
    bl_label  = "Toggle intervalo mandibula"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)
    seg_idx: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        og = _resolve_seg_organic(context, self.seg_idx)
        if 0 <= self.item_idx < len(og.jaw_items):
            if og.jaw_active_idx == self.item_idx:
                og.jaw_items[self.item_idx].enabled = not og.jaw_items[self.item_idx].enabled
            else:
                og.jaw_active_idx = self.item_idx
        return {"FINISHED"}


class JRRSTST_OT_JawOscLoad(Operator):
    """Carga un intervalo de mandibula al formulario para editarlo."""
    bl_idname = "jerryst.jaw_osc_load"
    bl_label  = "Editar intervalo mandibula"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)
    seg_idx: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        og = _resolve_seg_organic(context, self.seg_idx)
        if 0 <= self.item_idx < len(og.jaw_items):
            src = og.jaw_items[self.item_idx]
            og.jaw_edit_label       = src.label
            og.jaw_edit_frame_start = src.frame_start
            og.jaw_edit_frame_end   = src.frame_end
            og.jaw_edit_amplitude   = src.amplitude
            og.jaw_edit_cycles      = src.cycles
            og.jaw_edit_phase       = src.phase
            og.jaw_edit_transition  = src.transition
            og.jaw_edit_noise_seed  = src.noise_seed
            og.jaw_active_idx       = self.item_idx
            og.jaw_edit_mode        = "EDIT"
            og.jaw_edit_source_idx  = self.item_idx
        return {"FINISHED"}


class JRRSTST_OT_JawOscSave(Operator):
    """Guarda los cambios del formulario sobre el intervalo de mandibula."""
    bl_idname = "jerryst.jaw_osc_save"
    bl_label  = "Guardar intervalo mandibula"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        og = _resolve_seg_organic(context, self.seg_idx)
        idx = og.jaw_edit_source_idx
        if 0 <= idx < len(og.jaw_items):
            dst = og.jaw_items[idx]
            dst.label       = og.jaw_edit_label
            dst.frame_start = og.jaw_edit_frame_start
            dst.frame_end   = og.jaw_edit_frame_end
            dst.amplitude   = og.jaw_edit_amplitude
            dst.cycles      = og.jaw_edit_cycles
            dst.phase       = og.jaw_edit_phase
            dst.transition  = og.jaw_edit_transition
            dst.noise_seed  = og.jaw_edit_noise_seed
            og.jaw_edit_mode       = "ADD"
            og.jaw_edit_source_idx = -1
            self.report({"INFO"}, f"Intervalo mandibula '{dst.label}' actualizado")
        return {"FINISHED"}


class JRRSTST_OT_JawOscCancel(Operator):
    """Cancela la edicion de mandibula."""
    bl_idname = "jerryst.jaw_osc_cancel"
    bl_label  = "Cancelar edicion mandibula"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        og = _resolve_seg_organic(context, self.seg_idx)
        og.jaw_edit_mode       = "ADD"
        og.jaw_edit_source_idx = -1
        return {"FINISHED"}



# =============================================================================
# EMOTION FILTER OPERATORS
# =============================================================================

class JRRSTST_OT_EmotionAdd(Operator):
    """Agrega un intervalo de emocion de cejas."""
    bl_idname  = "jerryst.emotion_add"
    bl_label   = "Agregar intervalo de emocion"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        og   = _resolve_seg_organic(context, self.seg_idx)
        item = og.emotion_items.add()
        item.label          = og.emotion_edit_label
        item.frame_start    = og.emotion_edit_frame_start
        item.frame_end      = og.emotion_edit_frame_end
        item.transition_in  = og.emotion_edit_transition_in
        item.transition_out = og.emotion_edit_transition_out
        item.interp_type    = og.emotion_edit_interp_type
        item.emotion        = og.emotion_edit_emotion
        item.enabled        = True
        og.emotion_active_idx = len(og.emotion_items) - 1
        self.report({"INFO"}, f"Emocion '{item.label}' agregada")
        return {"FINISHED"}


class JRRSTST_OT_EmotionRemove(Operator):
    """Elimina un intervalo de emocion de cejas."""
    bl_idname  = "jerryst.emotion_remove"
    bl_label   = "Eliminar intervalo de emocion"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)
    seg_idx: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        og = _resolve_seg_organic(context, self.seg_idx)
        if 0 <= self.item_idx < len(og.emotion_items):
            og.emotion_items.remove(self.item_idx)
            og.emotion_active_idx = max(0, min(og.emotion_active_idx, len(og.emotion_items) - 1))
        return {"FINISHED"}


class JRRSTST_OT_EmotionToggle(Operator):
    """Activa/desactiva un intervalo de emocion."""
    bl_idname  = "jerryst.emotion_toggle"
    bl_label   = "Toggle intervalo de emocion"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)
    seg_idx: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        og = _resolve_seg_organic(context, self.seg_idx)
        if 0 <= self.item_idx < len(og.emotion_items):
            if og.emotion_active_idx == self.item_idx:
                og.emotion_items[self.item_idx].enabled = not og.emotion_items[self.item_idx].enabled
            else:
                og.emotion_active_idx = self.item_idx
        return {"FINISHED"}


class JRRSTST_OT_EmotionLoad(Operator):
    """Carga un intervalo de emocion al formulario para editarlo."""
    bl_idname  = "jerryst.emotion_load"
    bl_label   = "Editar intervalo de emocion"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)
    seg_idx: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        og = _resolve_seg_organic(context, self.seg_idx)
        if 0 <= self.item_idx < len(og.emotion_items):
            src = og.emotion_items[self.item_idx]
            og.emotion_edit_label          = src.label
            og.emotion_edit_frame_start    = src.frame_start
            og.emotion_edit_frame_end      = src.frame_end
            og.emotion_edit_transition_in  = src.transition_in
            og.emotion_edit_transition_out = src.transition_out
            og.emotion_edit_interp_type    = src.interp_type
            og.emotion_edit_emotion        = src.emotion
            og.emotion_active_idx       = self.item_idx
            og.emotion_edit_mode        = "EDIT"
            og.emotion_edit_source_idx  = self.item_idx
        return {"FINISHED"}


class JRRSTST_OT_EmotionSave(Operator):
    """Guarda los cambios del formulario sobre el intervalo de emocion."""
    bl_idname  = "jerryst.emotion_save"
    bl_label   = "Guardar intervalo de emocion"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        og  = _resolve_seg_organic(context, self.seg_idx)
        idx = og.emotion_edit_source_idx
        if 0 <= idx < len(og.emotion_items):
            dst = og.emotion_items[idx]
            dst.label          = og.emotion_edit_label
            dst.frame_start    = og.emotion_edit_frame_start
            dst.frame_end      = og.emotion_edit_frame_end
            dst.transition_in  = og.emotion_edit_transition_in
            dst.transition_out = og.emotion_edit_transition_out
            dst.interp_type    = og.emotion_edit_interp_type
            dst.emotion        = og.emotion_edit_emotion
            og.emotion_edit_mode       = "ADD"
            og.emotion_edit_source_idx = -1
            self.report({"INFO"}, f"Emocion '{dst.label}' actualizada")
        return {"FINISHED"}


class JRRSTST_OT_EmotionCancel(Operator):
    """Cancela la edicion de emocion."""
    bl_idname  = "jerryst.emotion_cancel"
    bl_label   = "Cancelar edicion de emocion"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        og = _resolve_seg_organic(context, self.seg_idx)
        og.emotion_edit_mode       = "ADD"
        og.emotion_edit_source_idx = -1
        return {"FINISHED"}


class JRRSTST_OT_BoneOscLoadToEdit(Operator):
    """Carga una oscilacion existente al formulario para editarla."""
    bl_idname    = "jerryst.bone_osc_load_to_edit"
    bl_label     = "Editar oscilacion"
    bl_description = "Carga esta oscilacion en el formulario para modificarla"
    bl_options   = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        osc = context.scene.jerryst.bone_oscillations
        if 0 <= self.item_idx < len(osc.items):
            src = osc.items[self.item_idx]
            osc.edit_label        = src.label
            osc.edit_bone_name    = src.bone_name
            osc.edit_frame_start  = src.frame_start
            osc.edit_frame_end    = src.frame_end
            osc.edit_axis_x       = src.axis_x
            osc.edit_axis_y       = src.axis_y
            osc.edit_axis_z       = src.axis_z
            osc.edit_amplitude    = src.amplitude
            osc.edit_angle_offset = src.angle_offset
            osc.edit_num_cycles   = src.num_cycles
            osc.edit_phase        = src.phase
            osc.edit_wave_type    = src.wave_type
            osc.edit_fade_in      = src.fade_in
            osc.edit_fade_out     = src.fade_out
            osc.edit_noise_seed   = src.noise_seed
            osc.active_idx        = self.item_idx
            osc.edit_mode         = "EDIT"
            osc.edit_source_idx   = self.item_idx
            self.report({"INFO"}, f"Editando oscilacion '{src.label}'")
        return {"FINISHED"}


class JRRSTST_OT_BoneOscSaveEdit(Operator):
    """Guarda los cambios del formulario sobre la oscilacion que se estaba editando."""
    bl_idname    = "jerryst.bone_osc_save_edit"
    bl_label     = "Guardar cambios"
    bl_description = "Aplica los cambios del formulario a la oscilacion seleccionada"
    bl_options   = {"REGISTER", "UNDO"}

    def execute(self, context):
        osc = context.scene.jerryst.bone_oscillations
        idx = osc.edit_source_idx
        if 0 <= idx < len(osc.items):
            dst = osc.items[idx]
            dst.label        = osc.edit_label
            dst.bone_name    = osc.edit_bone_name
            dst.frame_start  = osc.edit_frame_start
            dst.frame_end    = osc.edit_frame_end
            dst.axis_x       = osc.edit_axis_x
            dst.axis_y       = osc.edit_axis_y
            dst.axis_z       = osc.edit_axis_z
            dst.amplitude    = osc.edit_amplitude
            dst.angle_offset = osc.edit_angle_offset
            dst.num_cycles   = osc.edit_num_cycles
            dst.phase        = osc.edit_phase
            dst.wave_type    = osc.edit_wave_type
            dst.fade_in      = osc.edit_fade_in
            dst.fade_out     = osc.edit_fade_out
            dst.noise_seed   = osc.edit_noise_seed
            osc.edit_mode      = "ADD"
            osc.edit_source_idx = -1
            self.report({"INFO"}, f"Oscilacion '{dst.label}' actualizada")
        else:
            self.report({"WARNING"}, "Indice invalido — no se guardo nada")
        return {"FINISHED"}


class JRRSTST_OT_BoneOscCancelEdit(Operator):
    """Cancela la edicion en curso y vuelve el formulario al modo 'agregar'."""
    bl_idname    = "jerryst.bone_osc_cancel_edit"
    bl_label     = "Cancelar edicion"
    bl_description = "Descarta los cambios y vuelve al modo de agregar nueva oscilacion"
    bl_options   = {"REGISTER", "UNDO"}

    def execute(self, context):
        osc = context.scene.jerryst.bone_oscillations
        osc.edit_mode       = "ADD"
        osc.edit_source_idx = -1
        return {"FINISHED"}


class JRRSTST_OT_PlayFullAnimation(Operator):
    """Reproduce la animacion completa desde el frame inicio hasta el fin del recorrido."""
    bl_idname  = "jerryst.play_full_animation"
    bl_label   = "Reproducir animacion completa"
    bl_description = (
        "Pone el frame actual al inicio del recorrido y arranca la reproduccion "
        "de toda la animacion (recorrido + configuracion de bones)"
    )
    bl_options = {"REGISTER"}

    def execute(self, context):
        pc   = getattr(context.scene, "jerry_path", None)
        segs = getattr(context.scene, "jerry_segs", None)
        st   = context.scene.jerryst

        # Determinar frame inicio y fin
        if pc and len(pc.path_points) > 1:
            f_inicio = getattr(pc, "frame_inicio", context.scene.frame_start)
            f_fin    = getattr(pc, "anim_frame_fin", context.scene.frame_end)
        elif segs and len(segs.segments) > 0:
            f_inicio = segs.segments[0].frame_start
            f_fin    = segs.segments[len(segs.segments) - 1].frame_end
        else:
            f_inicio = context.scene.frame_start
            f_fin    = context.scene.frame_end

        # Asegurar que el armature no tenga accion directa activa
        # (bloquea la evaluacion de los NLA tracks del recorrido)
        arm_name = getattr(st, "armature_name", "Dog_001_rig")
        armature = context.scene.objects.get(arm_name)
        if armature and armature.animation_data:
            if armature.animation_data.action:
                armature.animation_data.action = None
            # Desmutar todos los NLA tracks (por si quedaron mutados tras REPRODUCIR)
            for _trk in armature.animation_data.nla_tracks:
                _trk.mute = False
            # El armature debe ser el objeto activo para que Blender
            # evalue correctamente los NLA tracks en el depsgraph
            context.view_layer.objects.active = armature

        # Mismo para el root
        root_obj = context.scene.objects.get("jerry")
        if root_obj and root_obj.animation_data:
            if root_obj.animation_data.action:
                root_obj.animation_data.action = None
            for _trk in root_obj.animation_data.nla_tracks:
                _trk.mute = False

        context.scene.frame_start = f_inicio
        context.scene.frame_end   = f_fin
        context.scene.frame_set(f_inicio)
        bpy.ops.screen.animation_play()
        self.report({"INFO"}, f"Reproduciendo: frames {f_inicio} → {f_fin}  ({f_fin - f_inicio + 1} fr)")
        return {"FINISHED"}


# =============================================================================
# FILTRO: IMPORTACION DE OBJETOS + SISTEMA DE LANZAR / RECOGER
# (portado desde Alfred Animation Studio)
# =============================================================================

def _resolve_preview_object_for_item(oi, item):
    """
    Si el usuario uso "Importar .blend al Outliner" antes de Agregar/Actualizar,
    oi.edit_imported_object_name guarda el nombre del objeto ya importado.

    Reutiliza ese objeto solo si:
      - todavia existe en bpy.data.objects, y
      - su nombre base (sin sufijo .001, .002, etc.) coincide con item.object_name

    En caso contrario retorna "" (el sistema importara uno nuevo cuando
    corresponda, ej. al apretar CONCATENAR).
    """
    name = (oi.edit_imported_object_name or "").strip()
    if not name:
        return ""

    obj = bpy.data.objects.get(name)
    if obj is None:
        return ""

    base_name = name.split('.')[0]
    if base_name != item.object_name:
        return ""

    return name


class JRST_OT_ObjImportAddItem(Operator):
    """Agrega un nuevo objeto de importacion a la lista."""
    bl_idname    = "jrst.obj_import_add_item"
    bl_label     = "Agregar objeto"
    bl_description = "Agrega el objeto definido abajo a la lista de importaciones"
    bl_options   = {"REGISTER", "UNDO"}

    def execute(self, context):
        oi = context.scene.jerryst.object_imports
        item = oi.items.add()
        item.label          = oi.edit_label
        item.object_folder  = oi.edit_object_folder
        item.blend_filename = oi.edit_blend_filename
        item.object_name    = oi.edit_object_name
        item.frame_start    = oi.edit_frame_start
        item.frame_end      = oi.edit_frame_end
        item.parent_armature = oi.edit_parent_armature
        item.parent_bone    = oi.edit_parent_bone
        item.loc_x          = oi.edit_loc_x
        item.loc_y          = oi.edit_loc_y
        item.loc_z          = oi.edit_loc_z
        item.rot_x          = oi.edit_rot_x
        item.rot_y          = oi.edit_rot_y
        item.rot_z          = oi.edit_rot_z
        item.scale_uniform  = oi.edit_scale_uniform
        item.levels_up             = oi.edit_levels_up
        item.segment_idx           = oi.edit_segment_idx
        item.transition_in         = oi.edit_transition_in
        item.transition_in_duration  = oi.edit_transition_in_duration
        item.transition_out        = oi.edit_transition_out
        item.transition_out_duration = oi.edit_transition_out_duration
        item.enabled        = True

        # Reutilizar el objeto importado con "Importar .blend al Outliner" si coincide
        item.imported_object_name = _resolve_preview_object_for_item(oi, item)

        oi.active_idx = len(oi.items) - 1
        self.report({"INFO"}, f"Objeto '{item.label}' agregado")
        return {"FINISHED"}


class JRST_OT_ObjImportRemoveItem(Operator):
    """Elimina el objeto de importacion en el indice dado."""
    bl_idname  = "jrst.obj_import_remove_item"
    bl_label   = "Eliminar objeto"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        oi = context.scene.jerryst.object_imports
        if 0 <= self.item_idx < len(oi.items):
            oi.items.remove(self.item_idx)
            oi.active_idx = max(0, min(oi.active_idx, len(oi.items) - 1))
        return {"FINISHED"}


class JRST_OT_ObjImportMoveItem(Operator):
    """Mueve el objeto seleccionado arriba o abajo."""
    bl_idname  = "jrst.obj_import_move_item"
    bl_label   = "Mover objeto"
    bl_options = {"REGISTER", "UNDO"}

    direction: bpy.props.EnumProperty(items=[("UP", "Arriba", ""), ("DOWN", "Abajo", "")])

    def execute(self, context):
        oi  = context.scene.jerryst.object_imports
        idx = oi.active_idx
        n   = len(oi.items)
        if self.direction == "UP" and idx > 0:
            oi.items.move(idx, idx - 1)
            oi.active_idx -= 1
        elif self.direction == "DOWN" and idx < n - 1:
            oi.items.move(idx, idx + 1)
            oi.active_idx += 1
        return {"FINISHED"}


class JRST_OT_ObjImportDuplicateItem(Operator):
    """Duplica el objeto de importacion en el indice dado."""
    bl_idname  = "jrst.obj_import_duplicate_item"
    bl_label   = "Duplicar objeto"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        oi = context.scene.jerryst.object_imports
        if 0 <= self.item_idx < len(oi.items):
            src = oi.items[self.item_idx]
            new = oi.items.add()
            for attr in ("label", "object_folder", "blend_filename", "object_name",
                         "frame_start", "frame_end", "parent_armature", "parent_bone",
                         "loc_x", "loc_y", "loc_z", "rot_x", "rot_y", "rot_z",
                         "scale_uniform", "levels_up", "enabled"):
                setattr(new, attr, getattr(src, attr))
            new.label = src.label + "_copia"
            oi.active_idx = len(oi.items) - 1
        return {"FINISHED"}


class JRST_OT_ObjImportToggleItem(Operator):
    """Selecciona como activo y/o activa/desactiva el objeto."""
    bl_idname  = "jrst.obj_import_toggle_item"
    bl_label   = "Seleccionar / toggle objeto"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        oi = context.scene.jerryst.object_imports
        if 0 <= self.item_idx < len(oi.items):
            if oi.active_idx == self.item_idx:
                oi.items[self.item_idx].enabled = not oi.items[self.item_idx].enabled
            else:
                oi.active_idx = self.item_idx
        return {"FINISHED"}


class JRST_OT_ObjImportLoadToEditor(Operator):
    """Carga el objeto seleccionado en el editor para editarlo."""
    bl_idname  = "jrst.obj_import_load_to_editor"
    bl_label   = "Editar objeto"
    bl_description = "Carga este objeto en el editor de abajo para modificarlo"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        oi = context.scene.jerryst.object_imports
        if 0 <= self.item_idx < len(oi.items):
            src = oi.items[self.item_idx]
            oi.active_idx          = self.item_idx
            oi.edit_label          = src.label
            oi.edit_object_folder  = src.object_folder
            oi.edit_blend_filename = src.blend_filename
            oi.edit_object_name    = src.object_name
            oi.edit_frame_start    = src.frame_start
            oi.edit_frame_end      = src.frame_end
            oi.edit_parent_armature = src.parent_armature
            oi.edit_parent_bone    = src.parent_bone
            oi.edit_loc_x          = src.loc_x
            oi.edit_loc_y          = src.loc_y
            oi.edit_loc_z          = src.loc_z
            oi.edit_rot_x          = src.rot_x
            oi.edit_rot_y          = src.rot_y
            oi.edit_rot_z          = src.rot_z
            oi.edit_scale_uniform  = src.scale_uniform
            oi.edit_levels_up      = src.levels_up
            oi.edit_imported_object_name = src.imported_object_name
            oi.edit_segment_idx    = src.segment_idx
            oi.edit_transition_in          = src.transition_in
            oi.edit_transition_in_duration   = src.transition_in_duration
            oi.edit_transition_out         = src.transition_out
            oi.edit_transition_out_duration  = src.transition_out_duration
        return {"FINISHED"}


class JRST_OT_ObjImportUpdateItem(Operator):
    """Actualiza el objeto activo con los valores del editor."""
    bl_idname  = "jrst.obj_import_update_item"
    bl_label   = "Actualizar objeto"
    bl_description = "Sobreescribe el objeto seleccionado con los valores actuales del editor"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        oi = context.scene.jerryst.object_imports
        idx = oi.active_idx
        if 0 <= idx < len(oi.items):
            item = oi.items[idx]
            item.label          = oi.edit_label
            item.object_folder  = oi.edit_object_folder
            item.blend_filename = oi.edit_blend_filename
            item.object_name    = oi.edit_object_name
            item.frame_start    = oi.edit_frame_start
            item.frame_end      = oi.edit_frame_end
            item.parent_armature = oi.edit_parent_armature
            item.parent_bone    = oi.edit_parent_bone
            item.loc_x          = oi.edit_loc_x
            item.loc_y          = oi.edit_loc_y
            item.loc_z          = oi.edit_loc_z
            item.rot_x          = oi.edit_rot_x
            item.rot_y          = oi.edit_rot_y
            item.rot_z          = oi.edit_rot_z
            item.scale_uniform  = oi.edit_scale_uniform
            item.levels_up             = oi.edit_levels_up
            item.segment_idx           = oi.edit_segment_idx
            item.transition_in         = oi.edit_transition_in
            item.transition_in_duration  = oi.edit_transition_in_duration
            item.transition_out        = oi.edit_transition_out
            item.transition_out_duration = oi.edit_transition_out_duration

            # Si el nombre de objeto cambio y ya no coincide con el objeto
            # previamente importado, limpiar el vinculo (se re-importara).
            if item.imported_object_name:
                current = bpy.data.objects.get(item.imported_object_name)
                if current is None or current.name.split('.')[0] != item.object_name:
                    item.imported_object_name = ""

            # Si no hay objeto vinculado, intentar usar el de "Importar .blend al Outliner"
            if not item.imported_object_name:
                item.imported_object_name = _resolve_preview_object_for_item(oi, item)

            self.report({"INFO"}, f"Objeto '{item.label}' actualizado")
        return {"FINISHED"}


class JRST_OT_ObjImportBrowseBlend(Operator):
    """
    Abre el explorador de archivos de Blender posicionado en
    Jerry_Animacion/objetos/, para que el usuario navegue las subcarpetas
    (vanilla, jerry, guard_ribbit, ribbits, ...) y seleccione el .blend
    a importar.

    Al seleccionar un archivo:
      - oi.edit_object_folder  = ruta relativa desde objetos/ hasta la
                                  carpeta que contiene el .blend
                                  (ej. 'vanilla/shield', 'jerry/espada')
      - oi.edit_blend_filename = nombre del archivo .blend
      - oi.edit_object_name    = primer objeto encontrado dentro del .blend
                                  (si se pudo leer)
    """
    bl_idname    = "jrst.obj_import_browse_blend"
    bl_label     = "Buscar .blend"
    bl_description = (
        "Abre el explorador de archivos en objetos/ para navegar las carpetas "
        "(vanilla, jerry, guard_ribbit, ribbits, ...) y elegir el .blend a importar. "
        "Completa automaticamente Carpeta, Archivo .blend y Nombre objeto."
    )
    bl_options   = {"REGISTER", "UNDO"}

    filepath:    bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.blend", options={"HIDDEN"})

    def invoke(self, context, event):
        st = context.scene.jerryst
        anchor_dir = bpy.path.abspath(st.anim_dir) if st.anim_dir else bpy.path.abspath("//")
        levels_up  = context.scene.jerryst.object_imports.edit_levels_up
        objetos_dir = _oiu_preview.get_objetos_base_path_from_anchor(anchor_dir, levels_up)

        start_dir = objetos_dir if os.path.isdir(objetos_dir) else anchor_dir
        self.filepath = os.path.join(start_dir, "")  # asegura separador final -> abre EN la carpeta

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        st = context.scene.jerryst
        oi = st.object_imports

        selected_path = bpy.path.abspath(self.filepath)

        if not selected_path.lower().endswith(".blend"):
            self.report({"ERROR"}, "Selecciona un archivo .blend")
            return {"CANCELLED"}

        if not os.path.isfile(selected_path):
            self.report({"ERROR"}, f"Archivo no encontrado: {selected_path}")
            return {"CANCELLED"}

        anchor_dir  = bpy.path.abspath(st.anim_dir) if st.anim_dir else bpy.path.abspath("//")
        objetos_dir = _oiu_preview.get_objetos_base_path_from_anchor(anchor_dir, oi.edit_levels_up)

        blend_dir  = os.path.dirname(selected_path)
        blend_name = os.path.basename(selected_path)

        try:
            rel_folder = os.path.relpath(blend_dir, objetos_dir)
        except ValueError:
            rel_folder = blend_dir  # distinta unidad (Windows) — usar ruta absoluta como fallback

        rel_folder = rel_folder.replace(os.sep, "/")

        if rel_folder in (".", ""):
            self.report(
                {"ERROR"},
                f"Selecciona un .blend dentro de una subcarpeta de:\n{objetos_dir}"
            )
            return {"CANCELLED"}

        if rel_folder.startswith(".."):
            self.report(
                {"WARNING"},
                f"El archivo esta fuera de objetos/ ({objetos_dir}). "
                f"Se guardara la ruta tal cual, pero puede no funcionar al exportar/CONCATENAR."
            )

        oi.edit_object_folder  = rel_folder
        oi.edit_blend_filename = blend_name

        # Intentar detectar el nombre del objeto dentro del .blend
        names = _oiu_preview.list_objects_in_blend(selected_path)
        if names:
            # Preferir un objeto cuyo nombre coincida con el de la carpeta
            # (convencion usada en shield/shield.blend, stone_sword/stone_sword.blend, etc.)
            folder_base = os.path.basename(rel_folder)
            blend_base  = os.path.splitext(blend_name)[0]
            preferred = None
            for cand in (blend_base, folder_base):
                if cand in names:
                    preferred = cand
                    break
            oi.edit_object_name = preferred or names[0]

            if len(names) > 1:
                self.report(
                    {"INFO"},
                    f"'{blend_name}' contiene {len(names)} objetos: {', '.join(names)}. "
                    f"Se selecciono '{oi.edit_object_name}' — cambia 'Nombre objeto' si no es el correcto."
                )
            else:
                self.report({"INFO"}, f"Objeto detectado: '{oi.edit_object_name}'")
        else:
            self.report(
                {"WARNING"},
                f"No se pudo leer la lista de objetos de '{blend_name}'. "
                f"Completa 'Nombre objeto' manualmente."
            )

        return {"FINISHED"}


class JRST_OT_ObjImportDetectArmature(Operator):
    """
    Detecta automaticamente el (unico) armature presente en la escena y
    lo asigna a oi.edit_parent_armature. Jerry tiene un solo armature
    llamado "Dog_001_rig" — este boton evita que el usuario escriba a mano
    un nombre incorrecto (ej. "left_arm", que no existe en este rig).

    Si se proporciona apply_to_all=True, tambien actualiza
    item.parent_armature en todos los items existentes de la lista.
    """
    bl_idname    = "jrst.obj_import_detect_armature"
    bl_label     = "Detectar Armature"
    bl_description = (
        "Busca el armature de la escena y lo asigna automaticamente al campo Armature, "
        "evitando nombres incorrectos escritos a mano."
    )
    bl_options   = {"REGISTER", "UNDO"}

    apply_to_all: bpy.props.BoolProperty(
        name="Aplicar a todos los items",
        description="Tambien actualiza el Armature de todos los objetos ya agregados a la lista",
        default=False,
    )

    def execute(self, context):
        oi = context.scene.jerryst.object_imports

        armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']

        if len(armatures) == 0:
            self.report({"ERROR"}, "No se encontro ningun Armature en la escena")
            return {"CANCELLED"}

        if len(armatures) > 1:
            names = ", ".join(o.name for o in armatures)
            self.report(
                {"WARNING"},
                f"Hay {len(armatures)} armatures en la escena ({names}). "
                f"Se uso '{armatures[0].name}', verifica que sea el correcto."
            )

        armature_name = armatures[0].name
        oi.edit_parent_armature = armature_name

        if self.apply_to_all:
            for item in oi.items:
                item.parent_armature = armature_name

        self.report({"INFO"}, f"Armature detectado: '{armature_name}'")
        return {"FINISHED"}


class JRST_OT_ObjImportPreviewNow(Operator):
    """
    Importa el objeto .blend al Outliner usando los valores del editor
    (Carpeta, .blend, Nombre objeto, Niveles arriba), SIN aplicar todavia
    parenteo, transform ni visibilidad por frames.

    Permite verificar que la malla se importa correctamente antes de
    configurar los demas parametros. Una vez importado, el objeto queda
    visible en el Outliner y se puede ajustar manualmente o seguir el
    flujo normal (Agregar objeto -> CONCATENAR).
    """
    bl_idname    = "jrst.obj_import_preview_now"
    bl_label     = "Importar .blend al Outliner"
    bl_description = (
        "Importa la malla .blend definida arriba (Carpeta / .blend / Nombre objeto) "
        "directamente al Outliner, sin aplicar parenteo ni transformaciones todavia. "
        "Usalo para verificar que la ruta y el nombre del objeto son correctos."
    )
    bl_options   = {"REGISTER", "UNDO"}

    def execute(self, context):
        st = context.scene.jerryst
        oi = st.object_imports

        object_folder  = (oi.edit_object_folder or "").strip()
        blend_filename = (oi.edit_blend_filename or "").strip()
        object_name    = (oi.edit_object_name or "").strip()
        levels_up      = oi.edit_levels_up

        if not object_folder or not blend_filename or not object_name:
            self.report({"ERROR"}, "Completa Carpeta, Archivo .blend y Nombre objeto antes de importar")
            return {"CANCELLED"}

        anchor_dir = bpy.path.abspath(st.anim_dir) if st.anim_dir else bpy.path.abspath("//")
        base_path  = _oiu_preview.get_objetos_base_path_from_anchor(anchor_dir, levels_up)
        object_dir = _oiu_preview.resolve_object_folder_path(base_path, object_folder)
        blend_path = os.path.join(object_dir, blend_filename)

        if not os.path.exists(blend_path):
            self.report({"ERROR"}, f"No se encontro el archivo: {blend_path}")
            return {"CANCELLED"}

        obj = _oiu_preview.import_object_from_blend_path(blend_path, object_name)

        if obj is None:
            self.report(
                {"ERROR"},
                f"No se encontro el objeto '{object_name}' dentro de {blend_filename}. "
                f"Revisa el nombre exacto del objeto en el .blend."
            )
            return {"CANCELLED"}

        # Seleccionar el objeto importado y enfocarlo en el Outliner/Viewport
        for o in context.selected_objects:
            o.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj

        # Recordar este objeto para reutilizarlo al Agregar/Actualizar el item
        oi.edit_imported_object_name = obj.name

        self.report({"INFO"}, f"Objeto '{obj.name}' importado correctamente desde {blend_path}")
        return {"FINISHED"}


def _copy_edit_to_item(th, item):
    """Copia los campos edit_* de JerryThrowsSettings al JerryThrowItem dado."""
    item.label              = th.edit_label
    item.mode               = th.edit_mode
    item.blend_path         = th.edit_blend_path
    item.object_folder      = th.edit_object_folder
    item.blend_filename     = th.edit_blend_filename
    item.object_name        = th.edit_object_name
    item.levels_up          = th.edit_levels_up
    item.parent_armature    = th.edit_parent_armature
    item.parent_bone        = th.edit_parent_bone
    item.loc_x              = th.edit_loc_x
    item.loc_y              = th.edit_loc_y
    item.loc_z              = th.edit_loc_z
    item.rot_x              = th.edit_rot_x
    item.rot_y              = th.edit_rot_y
    item.rot_z              = th.edit_rot_z
    item.scale_uniform      = th.edit_scale_uniform
    item.frame_start        = th.edit_frame_start
    item.frame_end          = th.edit_frame_end
    item.target_armature    = th.edit_target_armature
    item.target_bone        = th.edit_target_bone
    item.dest_x             = th.edit_dest_x
    item.dest_y             = th.edit_dest_y
    item.dest_z             = th.edit_dest_z
    item.easing_global      = th.edit_easing_global
    item.spin_during_flight = th.edit_spin_during_flight
    item.spin_turns         = th.edit_spin_turns
    # Copiar el objeto importado en el editor → target_object del item
    if th.edit_imported_object_name:
        item.imported_object_name = th.edit_imported_object_name
        item.target_object        = th.edit_imported_object_name


def _copy_item_to_edit(item, th):
    """Copia un JerryThrowItem a los campos edit_* de JerryThrowsSettings."""
    th.edit_imported_object_name = ""  # Limpiar para no borrar el objeto del item
    th.edit_label              = item.label
    th.edit_mode               = item.mode
    th.edit_blend_path         = item.blend_path
    th.edit_object_folder      = item.object_folder
    th.edit_blend_filename     = item.blend_filename
    th.edit_object_name        = item.object_name
    th.edit_levels_up          = item.levels_up
    th.edit_parent_armature    = item.parent_armature
    th.edit_parent_bone        = item.parent_bone
    th.edit_loc_x              = item.loc_x
    th.edit_loc_y              = item.loc_y
    th.edit_loc_z              = item.loc_z
    th.edit_rot_x              = item.rot_x
    th.edit_rot_y              = item.rot_y
    th.edit_rot_z              = item.rot_z
    th.edit_scale_uniform      = item.scale_uniform
    th.edit_frame_start        = item.frame_start
    th.edit_frame_end          = item.frame_end
    th.edit_target_armature    = item.target_armature
    th.edit_target_bone        = item.target_bone
    th.edit_dest_x             = item.dest_x
    th.edit_dest_y             = item.dest_y
    th.edit_dest_z             = item.dest_z
    th.edit_easing_global      = item.easing_global
    th.edit_spin_during_flight = item.spin_during_flight
    th.edit_spin_turns         = item.spin_turns


def _get_seg_throws(context, seg_idx):
    segs = context.scene.jerry_segs.segments
    if seg_idx < 0 or seg_idx >= len(segs):
        return None
    return segs[seg_idx].throws


class JRST_OT_ThrowAddItem(bpy.types.Operator):
    """Agrega un nuevo lanzamiento/recogida usando los valores del editor"""
    bl_idname = "jrst.throw_add_item"
    bl_label  = "Agregar lanzamiento"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        item = th.items.add()
        _copy_edit_to_item(th, item)
        item.enabled = True
        th.active_idx = len(th.items) - 1
        self.report({"INFO"}, f"Lanzamiento '{item.label}' agregado")
        return {"FINISHED"}


class JRST_OT_ThrowRemoveItem(bpy.types.Operator):
    """Elimina el lanzamiento seleccionado"""
    bl_idname = "jrst.throw_remove_item"
    bl_label  = "Eliminar lanzamiento"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        if 0 <= self.item_idx < len(th.items):
            th.items.remove(self.item_idx)
            th.active_idx = max(0, self.item_idx - 1)
        return {"FINISHED"}


class JRST_OT_ThrowToggleItem(bpy.types.Operator):
    """Activa/desactiva el lanzamiento"""
    bl_idname = "jrst.throw_toggle_item"
    bl_label  = "Toggle lanzamiento"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        if 0 <= self.item_idx < len(th.items):
            th.items[self.item_idx].enabled = not th.items[self.item_idx].enabled
        return {"FINISHED"}


class JRST_OT_ThrowLoadToEditor(bpy.types.Operator):
    """Carga el lanzamiento seleccionado en el editor para modificarlo"""
    bl_idname = "jrst.throw_load_to_editor"
    bl_label  = "Editar lanzamiento"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        if 0 <= self.item_idx < len(th.items):
            _copy_item_to_edit(th.items[self.item_idx], th)
            th.active_idx = self.item_idx
        return {"FINISHED"}


class JRST_OT_ThrowUpdateItem(bpy.types.Operator):
    """Actualiza el lanzamiento activo con los valores del editor"""
    bl_idname = "jrst.throw_update_item"
    bl_label  = "Actualizar lanzamiento"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        if 0 <= self.item_idx < len(th.items):
            _copy_edit_to_item(th, th.items[self.item_idx])
            self.report({"INFO"}, f"Lanzamiento {self.item_idx} actualizado")
        return {"FINISHED"}


class JRST_OT_ThrowPickBone(bpy.types.Operator):
    """Asigna el bone al campo Bone del editor de lanzamiento"""
    bl_idname = "jrst.throw_pick_bone"
    bl_label  = "Seleccionar bone"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:   bpy.props.IntProperty(default=0)
    bone_name: bpy.props.StringProperty(default="")

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        th.edit_parent_bone  = self.bone_name
        th.edit_target_bone  = self.bone_name
        return {"FINISHED"}


class JRST_OT_ThrowBrowseBlend(bpy.types.Operator):
    """Abre el explorador para seleccionar el .blend del objeto a lanzar/recoger"""
    bl_idname    = "jrst.throw_browse_blend"
    bl_label     = "Buscar .blend"
    bl_options   = {"REGISTER", "UNDO"}
    seg_idx:     bpy.props.IntProperty(default=0)
    filepath:    bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.blend", options={"HIDDEN"})

    def invoke(self, context, event):
        st     = context.scene.jerryst
        anchor = bpy.path.abspath(st.anim_dir) if st.anim_dir else bpy.path.abspath("//")
        th     = _get_seg_throws(context, self.seg_idx)
        lv     = th.edit_levels_up if th else 4
        obj_dir = _oiu_preview.get_objetos_base_path_from_anchor(anchor, lv)
        self.filepath = os.path.join(obj_dir if os.path.isdir(obj_dir) else anchor, "")
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        sel = bpy.path.abspath(self.filepath)
        if not sel.lower().endswith(".blend") or not os.path.isfile(sel):
            self.report({"ERROR"}, "Selecciona un archivo .blend válido")
            return {"CANCELLED"}
        st      = context.scene.jerryst
        anchor  = bpy.path.abspath(st.anim_dir) if st.anim_dir else bpy.path.abspath("//")
        obj_dir = _oiu_preview.get_objetos_base_path_from_anchor(anchor, th.edit_levels_up)
        blend_dir  = os.path.dirname(sel)
        blend_name = os.path.basename(sel)
        try:    rel = os.path.relpath(blend_dir, obj_dir).replace(os.sep, "/")
        except: rel = blend_dir
        th.edit_blend_path    = sel
        th.edit_object_folder = rel
        th.edit_blend_filename = blend_name
        names = _oiu_preview.list_objects_in_blend(sel)
        if names:
            base = os.path.splitext(blend_name)[0]
            th.edit_object_name = base if base in names else names[0]
        return {"FINISHED"}


class JRST_OT_ThrowImportObject(bpy.types.Operator):
    """Importa el .blend y lo parentea al bone — mismo flujo que Importar Objetos"""
    bl_idname  = "jrst.throw_import_object"
    bl_label   = "Importar objeto al Outliner"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=-1)  # -1 = usar editor

    def execute(self, context):
        import mathutils
        from . import object_import_utils as _oiu
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}

        # Si item_idx >= 0 usar ese item; si no, usar editor
        if self.item_idx >= 0 and self.item_idx < len(th.items):
            src = th.items[self.item_idx]
            blend_path = src.blend_path; object_folder = src.object_folder
            blend_filename = src.blend_filename; object_name = src.object_name
            levels_up = src.levels_up; arm_name = src.parent_armature
            bone_name = src.parent_bone; frame_start = src.frame_start
            frame_end = src.frame_end
            loc = (src.loc_x, src.loc_y, src.loc_z)
            rot = (src.rot_x, src.rot_y, src.rot_z)
            scl = src.scale_uniform
        else:
            blend_path = th.edit_blend_path; object_folder = th.edit_object_folder
            blend_filename = th.edit_blend_filename; object_name = th.edit_object_name
            levels_up = th.edit_levels_up; arm_name = th.edit_parent_armature
            bone_name = th.edit_parent_bone; frame_start = th.edit_frame_start
            frame_end = th.edit_frame_end
            loc = (th.edit_loc_x, th.edit_loc_y, th.edit_loc_z)
            rot = (th.edit_rot_x, th.edit_rot_y, th.edit_rot_z)
            scl = th.edit_scale_uniform
            src = None

        # Resolver ruta
        if blend_path and os.path.isfile(bpy.path.abspath(blend_path)):
            blend_abs = bpy.path.abspath(blend_path)
        else:
            st_main = context.scene.jerryst
            anchor  = bpy.path.abspath(st_main.anim_dir) if st_main.anim_dir else bpy.path.abspath("//")
            obj_dir = _oiu_preview.get_objetos_base_path_from_anchor(anchor, levels_up)
            blend_abs = os.path.join(obj_dir, object_folder, blend_filename)

        # Eliminar objeto anterior solo si corresponde a ESTE slot
        if src:
            # Modo editar item existente: eliminar el objeto previo de ese item
            prev_name = src.imported_object_name
        else:
            # Modo editor nuevo: solo eliminar si edit_imported_object_name
            # NO pertenece a ningún item existente (es un objeto temporal del editor)
            prev_name = th.edit_imported_object_name
            if prev_name:
                in_use = any(item.imported_object_name == prev_name for item in th.items)
                if in_use:
                    prev_name = ""  # No eliminar — pertenece a un item guardado
        if prev_name:
            old_obj = bpy.data.objects.get(prev_name)
            if old_obj:
                old_mesh = old_obj.data
                bpy.data.objects.remove(old_obj, do_unlink=True)
                if old_mesh and old_mesh.users == 0:
                    try: bpy.data.meshes.remove(old_mesh)
                    except: pass

        obj = _oiu.import_object_from_blend_path(blend_abs, object_name)
        if obj is None:
            self.report({"ERROR"}, f"No se pudo importar '{object_name}' desde {blend_abs}")
            return {"CANCELLED"}

        imported_name = obj.name
        if src:
            src.imported_object_name = imported_name
            src.target_object        = imported_name
        else:
            th.edit_imported_object_name = imported_name

        # Visibilidad
        _oiu.hide_until_frame(obj, appear_frame=frame_start)
        _oiu.set_visibility_keyframes(obj, frame_end, visible=False)

        # Parenteo idéntico a run_object_imports_live
        all_arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
        arm_obj  = next((o for o in all_arms if o.name == arm_name), None)
        if arm_obj is None and len(all_arms) == 1:
            arm_obj = all_arms[0]
        target_bone = None
        if arm_obj and arm_obj.pose:
            if bone_name:
                target_bone = arm_obj.pose.bones.get(bone_name)
            if target_bone is None:
                target_bone = next((pb for pb in arm_obj.pose.bones if 'bend' in pb.name.lower()), None)

        if target_bone:
            obj.parent = target_bone.id_data
            obj.parent_bone = target_bone.name
            obj.parent_type = 'BONE'
            obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
        elif arm_obj:
            obj.parent = arm_obj
            obj.parent_type = 'OBJECT'
            obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)

        obj.location       = loc
        obj.rotation_euler = rot
        obj.scale          = (scl, scl, scl)

        if src and target_bone and not src.target_bone:
            src.target_bone = target_bone.name
        self.report({"INFO"}, f"'{obj.name}' importado — bone '{target_bone.name if target_bone else 'ninguno'}'")
        return {"FINISHED"}


class JRST_OT_ThrowDetectArmature(bpy.types.Operator):
    """Detecta el armature y lo asigna al editor"""
    bl_idname = "jrst.throw_detect_armature"
    bl_label  = "Detectar Armature"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
        if not arms:
            self.report({"WARNING"}, "No se encontró ningún armature")
            return {"CANCELLED"}
        th.edit_parent_armature = arms[0].name
        th.edit_target_armature = arms[0].name
        return {"FINISHED"}


class JRST_OT_ThrowPickDestFromCursor(bpy.types.Operator):
    """Toma la posición del 3D Cursor como coordenada destino del editor"""
    bl_idname = "jrst.throw_pick_dest_cursor"
    bl_label  = "Destino desde cursor 3D"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        cur = context.scene.cursor.location
        th.edit_dest_x = cur.x; th.edit_dest_y = cur.y; th.edit_dest_z = cur.z
        self.report({"INFO"}, f"Destino: ({cur.x:.3f}, {cur.y:.3f}, {cur.z:.3f})")
        return {"FINISHED"}


class JRST_OT_ThrowAddWaypoint(bpy.types.Operator):
    """Agrega un waypoint al item activo"""
    bl_idname = "jrst.throw_add_waypoint"
    bl_label  = "Agregar waypoint"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:     bpy.props.IntProperty(default=0)
    item_idx:    bpy.props.IntProperty(default=0)
    from_cursor: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        if self.item_idx < 0 or self.item_idx >= len(th.items): return {"CANCELLED"}
        wp = th.items[self.item_idx].waypoints.add()
        wp.label = f"Punto {len(th.items[self.item_idx].waypoints)}"
        if self.from_cursor:
            cur = context.scene.cursor.location
            wp.x, wp.y, wp.z = cur.x, cur.y, cur.z
        return {"FINISHED"}


class JRST_OT_ThrowRemoveWaypoint(bpy.types.Operator):
    """Elimina un waypoint del item activo"""
    bl_idname = "jrst.throw_remove_waypoint"
    bl_label  = "Eliminar waypoint"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)
    wp_idx:   bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        if self.item_idx < 0 or self.item_idx >= len(th.items): return {"CANCELLED"}
        wps = th.items[self.item_idx].waypoints
        if 0 <= self.wp_idx < len(wps):
            wps.remove(self.wp_idx)
        return {"FINISHED"}


class JRST_OT_ThrowWaypointFromCursor(bpy.types.Operator):
    """Actualiza las coordenadas del waypoint con el cursor 3D"""
    bl_idname = "jrst.throw_wp_from_cursor"
    bl_label  = "Desde cursor 3D"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)
    wp_idx:   bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        if self.item_idx < 0 or self.item_idx >= len(th.items): return {"CANCELLED"}
        wps = th.items[self.item_idx].waypoints
        if 0 <= self.wp_idx < len(wps):
            cur = context.scene.cursor.location
            wps[self.wp_idx].x, wps[self.wp_idx].y, wps[self.wp_idx].z = cur.x, cur.y, cur.z
        return {"FINISHED"}


def apply_throw_item(item, context):
    """Aplica la trayectoria de un JerryThrowItem."""
    import math, mathutils
    obj = bpy.data.objects.get(item.target_object)
    if obj is None:
        print(f"[THROW] ERROR: objeto '{item.target_object}' no encontrado")
        return False

    f0    = item.frame_start
    f_end = item.frame_end
    scene = context.scene
    frame_original = scene.frame_current

    scene.frame_set(f0)
    bpy.context.view_layer.update()
    bone_loc = _throw_get_bone_world_loc(item.target_armature, item.target_bone)
    dest = (item.dest_x, item.dest_y, item.dest_z)
    active_wps   = [wp for wp in item.waypoints if wp.enabled]
    total_frames = max(1, f_end - f0)

    if item.mode == 'THROW':
        cps = ([(f0, bone_loc[0], bone_loc[1], bone_loc[2], item.easing_global)]
               + [(None, wp.x, wp.y, wp.z, wp.easing) for wp in active_wps]
               + [(f_end, dest[0], dest[1], dest[2], item.easing_global)])
    else:
        cps = ([(f0, dest[0], dest[1], dest[2], item.easing_global)]
               + [(None, wp.x, wp.y, wp.z, wp.easing) for wp in reversed(active_wps)]
               + [(f_end, bone_loc[0], bone_loc[1], bone_loc[2], item.easing_global)])

    frame_step = total_frames / max(1, len(cps) - 1)
    for idx, pt in enumerate(cps):
        if pt[0] is None:
            cps[idx] = (int(f0 + idx * frame_step), pt[1], pt[2], pt[3], pt[4])

    world_mat = obj.matrix_world.copy()
    obj.parent = None; obj.parent_bone = ""; obj.parent_type = 'OBJECT'
    obj.matrix_world = world_mat
    bpy.context.view_layer.update()

    action = _throw_ensure_action(obj)
    for (frame, x, y, z, easing) in cps:
        scene.frame_set(int(frame))
        obj.location = (x, y, z)
        obj.keyframe_insert(data_path="location", frame=int(frame))
    for (frame, x, y, z, easing) in cps[:-1]:
        _throw_set_kf_interp(action, "location", int(frame), easing)

    if item.spin_during_flight:
        rz_s = obj.rotation_euler[2]
        rz_e = rz_s + math.radians(360.0 * item.spin_turns)
        if item.mode == 'CATCH': rz_s, rz_e = rz_e, rz_s
        scene.frame_set(f0);    obj.rotation_euler[2] = rz_s; obj.keyframe_insert(data_path="rotation_euler", frame=f0, index=2)
        scene.frame_set(f_end); obj.rotation_euler[2] = rz_e; obj.keyframe_insert(data_path="rotation_euler", frame=f_end, index=2)

    scene.frame_set(frame_original)
    bpy.context.view_layer.update()
    print(f"[THROW] OK '{item.target_object}' {f0}→{f_end}")
    return True


class JRST_OT_ThrowApply(bpy.types.Operator):
    """Aplica la trayectoria del lanzamiento seleccionado"""
    bl_idname = "jrst.throw_apply"
    bl_label  = "Aplicar trayectoria"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        if self.item_idx < 0 or self.item_idx >= len(th.items):
            self.report({"ERROR"}, "Item inválido"); return {"CANCELLED"}
        item = th.items[self.item_idx]
        # Fallback: si target_object está vacío, intentar con object_name
        if not item.target_object:
            if item.object_name and bpy.data.objects.get(item.object_name):
                item.target_object        = item.object_name
                item.imported_object_name = item.object_name
            else:
                self.report({"ERROR"},
                    f"Objeto no encontrado. Importa el objeto primero ('{item.object_name}')")
                return {"CANCELLED"}
        # Verificar que el objeto exista en escena
        if not bpy.data.objects.get(item.target_object):
            if item.object_name and bpy.data.objects.get(item.object_name):
                item.target_object = item.object_name
            else:
                self.report({"ERROR"},
                    f"Objeto '{item.target_object}' no está en la escena. Reimporta el objeto.")
                return {"CANCELLED"}
        try:
            ok = apply_throw_item(item, context)
            if ok: self.report({"INFO"}, f"Trayectoria aplicada a '{item.target_object}'")
        except Exception as e:
            self.report({"ERROR"}, f"Error: {e}"); import traceback; traceback.print_exc()
            return {"CANCELLED"}
        return {"FINISHED"}


class JRST_OT_ThrowClearKeyframes(bpy.types.Operator):
    """Elimina los keyframes de trayectoria del item seleccionado"""
    bl_idname = "jrst.throw_clear_keyframes"
    bl_label  = "Limpiar keyframes"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        if self.item_idx < 0 or self.item_idx >= len(th.items): return {"CANCELLED"}
        item = th.items[self.item_idx]
        obj  = bpy.data.objects.get(item.target_object)
        if obj is None or obj.animation_data is None or obj.animation_data.action is None:
            self.report({"WARNING"}, "Sin animación para limpiar"); return {"CANCELLED"}
        f0, f1 = item.frame_start, item.frame_end
        removed = 0
        for fc in _get_action_fcurves(obj.animation_data.action):
            if fc.data_path not in ('location', 'rotation_euler'): continue
            for i in reversed([j for j, kp in enumerate(fc.keyframe_points) if f0 <= kp.co.x <= f1]):
                fc.keyframe_points.remove(fc.keyframe_points[i]); removed += 1
        self.report({"INFO"}, f"Eliminados {removed} keyframes")
        return {"FINISHED"}
