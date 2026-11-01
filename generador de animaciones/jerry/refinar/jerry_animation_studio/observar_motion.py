# -*- coding: utf-8 -*-
"""
observar_motion.py -- Jerry Animation Studio

Animacion "Observar": Jerry SENTADO y en alerta, girando la cabeza de
derecha a izquierda. Es el cuarto tipo del dropdown "Tipo" de la lista
de coordenadas del Paso 1 (Caminar / Saltar / Parada / Observar).

Este modulo es Python puro (NO importa bpy): solo calcula keyframes.
Lo usan los tres consumidores que ya existian para 'Parada':
  - JRRSTPR_OT_PreviewPath   (path_recorder.py)  -> los aplica al rig
  - generate_slots_jerry.generate_parada(observar=True) -> los EMBEBE como
    texto en el slot .py exportado (Exportar / Generar slots)

POSE SENTADA
------------
SIT_POSE_ROT / SIT_POSE_LOC salen tal cual de sentado_mirar_frente.json
(Dog_001_rig, Blender 4.5.8, pose 'sentado mirar de frente'): la
rotacion euler XYZ (radianes) de cada hueso y, solo para los huesos donde
la pose tiene desplazamiento real, su location local. El mas importante
es spine_6 (pelvis): baja y se echa atras para que el perro se siente.

SECUENCIA
---------
  frames 0 .. t_sit          se sienta  (pose parado IDLE -> pose sentado)
  frames t_sit .. t_stand    en alerta: de frente, gira a un lado, cruza
                             al otro lado, vuelve al frente (1 o mas
                             barridos segun la duracion). Mientras tanto
                             sigue VIVO: respira, mueve la cola, cabecea
                             un poco y sacude las orejas (ver
                             IDLE_OSCILLATIONS / EAR_TWITCHES)
  frames t_stand .. final    se para   (pose sentado -> pose parado IDLE)
La duracion total es la del campo 'Frames' del punto (parada_frames_punto).
"""
import math

SIT_POSE_ROT = {
    "spine_6": (0.862193, -0.052717, -0.056621),
    "shoulder.R": (0.727102, 0.888502, 0.098382),
    "thigh.R": (-0.583706, -0.207750, 0.071363),
    "shin.R": (-1.021946, 0.098391, -0.053925),
    "tail_1": (-0.922989, 0.180603, 0.192899),
    "tail_2": (0.000000, 0.000000, 0.192900),
    "tail_3": (0.000000, 0.000000, -0.522965),
    "spine_5": (-0.538328, 0.000000, 0.002189),
    "spine_4": (0.106090, 0.000000, 0.002189),
    "spine_1": (-0.252613, -0.193068, 0.788733),
    "scull_1": (0.005664, 0.106769, -0.136455),
    "scull": (0.005664, 0.106769, -0.136455),
    "ear.R": (0.000000, 0.000000, 0.022580),
    "ear.L": (0.000000, 0.000000, 0.117874),
    "jaw_bot": (-0.315379, 0.000000, 0.000000),
    "sejas_1_jerry": (0.000703, -0.008879, -0.109022),
    "sejas_2_jerry": (-0.008506, 0.011381, 0.101313),
    "front_shoulder.R": (-0.138855, 0.458502, -0.504314),
    "front_thigh.R": (-0.001016, 0.473312, 0.172248),
    "front_shin.R": (-0.239363, -0.023179, -0.030848),
    "front_foot.R": (0.075974, -0.116179, -0.034857),
    "front_shoulder.L": (-0.004399, 0.375744, -0.102497),
    "front_thigh.L": (0.091310, -0.180055, -0.052904),
    "front_shin.L": (-0.308124, -0.004145, -0.000915),
    "shoulder.L": (0.615948, -0.122644, 0.124503),
    "thigh.L": (-0.598201, 0.000841, 0.000487),
    "shin.L": (-1.117248, -0.042291, 0.171941),
}

# NOTA: el JSON tambien trae un hueso "jerry" con location (-14.5, -24.5,
# 9.0): es la POSICION EN EL MUNDO del personaje cuando se capturo la pose,
# no parte de la postura -- se excluye a proposito (moverlo teletransportaria
# al perro fuera de su coordenada del recorrido).
SIT_POSE_LOC = {
    "spine_6": (0.000001, -0.092728, -0.116450),
    "ear.L": (-0.002902, 0.000113, 0.001407),
    "sejas_1_jerry": (0.008940, -0.001347, -0.000271),
    "sejas_2_jerry": (0.012851, -0.002466, 0.003037),
    "front_toe.L": (0.000000, 0.000587, -0.002096),
}

# --- Giro de cabeza --------------------------------------------------
# Huesos que giran y cuanto aporta cada uno al giro total (radianes, a
# cada lado del frente). scull_1 + scull suman ~0.75 rad (~43 grados).
YAW_BONES = (("scull", 0.45), ("scull_1", 0.30))
# Eje euler del giro lateral (oscilacion de la cabeza): 2 = Z.
# (Antes era 1 = Y, que en este rig es el eje de torsion del hueso y no el
# de giro lateral -- corregido por Kebyn, 2026-09-24.)
YAW_AXIS = 2
# +1 / -1: cambia hacia que lado mira PRIMERO (derecha -> izquierda).
# Si en tu escena arranca mirando a la izquierda, pon -1.
FIRST_SIDE_SIGN = 1
# Ladeo curioso de la cabeza al girar: (hueso, eje, rad por unidad de giro).
# Pon la amplitud en 0.0 para desactivarlo.
HEAD_TILT = ("scull_1", 1, 0.08)

# --- Tiempos -----------------------------------------------------------
SIT_RAMP_FRAMES = 12      # frames maximos de sentarse / pararse
SCAN_CYCLE_FRAMES = 72    # duracion de un barrido completo (3 s a 24 fps)
FRAMES_OBSERVAR_DEFAULT = 96
OSC_KEY_STEP = 4          # cada cuantos frames se muestrean las oscilaciones
OSC_FADE_FRAMES = 12      # fade-in / fade-out de las oscilaciones

# (fraccion del ciclo, lado)   +1 = primer lado, -1 = lado opuesto, 0 = frente
_SCAN_KEYS = (
    (0.00, 0.0), (0.08, 0.0),      # mirada al frente
    (0.24, +1.0), (0.36, +1.0),    # gira al primer lado y sostiene
    (0.66, -1.0), (0.78, -1.0),    # cruza al lado opuesto y sostiene
    (0.94, 0.0), (1.00, 0.0),      # vuelve al frente
)

# --- Movimiento secundario (sentado, en alerta) ---------------------------
# (hueso, eje euler 0=X 1=Y 2=Z, amplitud rad, periodo en frames, fase rad)
# Se SUMAN a la pose sentada. Los periodos no son multiplos entre si a
# proposito, para que no se vea mecanico. Ajusta las amplitudes a gusto.
IDLE_OSCILLATIONS = (
    # Respiracion (~1.7 s): el pecho sube, el cuello y la mandibula la siguen
    ("spine_5",  0,  0.030, 40, 0.0),
    ("spine_4",  0, -0.018, 40, 0.5),
    ("spine_1",  0,  0.014, 40, 1.0),
    ("jaw_bot",  0,  0.015, 40, 1.2),
    # Cola: barrido lateral (Z) en onda -- cada segmento va retrasado
    ("tail_1",   2,  0.10,  52, 0.0),
    ("tail_2",   2,  0.16,  52, -0.7),
    ("tail_3",   2,  0.22,  52, -1.4),
    # Cola: cabeceo vertical leve para que no sea un barrido plano
    ("tail_2",   0,  0.05,  67, 0.9),
    ("tail_3",   0,  0.07,  67, 0.2),
    # Cabeza: cabeceo sutil (olfateo / atencion)
    ("scull",    0,  0.035, 61, 0.3),
    ("scull_1",  0,  0.020, 61, 0.0),
    # Orejas: deriva lenta
    ("ear.R",    2,  0.05,  47, 0.0),
    ("ear.L",    2,  0.05,  53, 1.7),
)

# Sacudidas de oreja puntuales: (hueso, eje, amplitud rad, posicion 0..1
# dentro del tramo de alerta).
EAR_TWITCHES = (
    ("ear.L", 2,  0.30, 0.30),
    ("ear.R", 2, -0.28, 0.58),
    ("ear.L", 2,  0.25, 0.86),
)
_TWITCH_SIGMA = 2.5       # frames


def quat_to_euler_xyz(q):
    """(w, x, y, z) -> (rx, ry, rz) euler XYZ en radianes (mismo criterio
    que mathutils.Quaternion.to_euler('XYZ')). Sin dependencias."""
    w, x, y, z = q
    n = math.sqrt(w * w + x * x + y * y + z * z) or 1.0
    w, x, y, z = w / n, x / n, y / n, z / n
    rx = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    sp = 2 * (w * y - z * x)
    ry = math.copysign(math.pi / 2, sp) if abs(sp) >= 1 else math.asin(sp)
    rz = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    return (rx, ry, rz)


def _timeline(total_frames):
    """Devuelve (n, t_sit, t_stand): ultimo frame relativo, frame en que
    termina de sentarse y frame en que empieza a pararse."""
    total = max(1, int(total_frames))
    n = total - 1
    ramp = min(SIT_RAMP_FRAMES, max(2, round(total * 0.15)))
    ramp = min(ramp, max(1, n // 3))
    return n, ramp, n - ramp


def _scan_yaw_keys(t_sit, t_stand):
    """[(frame_rel, factor -1..+1)] del barrido de cabeza, entre t_sit y
    t_stand. Vacio si el tramo es demasiado corto para girar."""
    span = t_stand - t_sit
    if span < 4:
        return []
    cycles = max(1, round(span / SCAN_CYCLE_FRAMES))
    cyc = span / cycles
    keys = {}
    for c in range(cycles):
        for frac, side in _SCAN_KEYS:
            f = int(round(t_sit + (c * cyc) + frac * cyc))
            keys[f] = side * FIRST_SIDE_SIGN
    keys[t_sit] = 0.0
    keys[t_stand] = 0.0
    return sorted(keys.items())


def _smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def _yaw_factor(f, yaw_keys):
    """Factor de giro (-1..+1) en el frame `f`, con ease entre keys."""
    if not yaw_keys or f <= yaw_keys[0][0] or f >= yaw_keys[-1][0]:
        return 0.0
    for (f0, v0), (f1, v1) in zip(yaw_keys, yaw_keys[1:]):
        if f0 <= f <= f1:
            if f1 == f0:
                return v1
            return v0 + (v1 - v0) * _smoothstep((f - f0) / float(f1 - f0))
    return 0.0


def _osc_envelope(f, t_sit, t_stand):
    """0 al sentarse / pararse, 1 en pleno tramo de alerta."""
    fade = max(1.0, min(float(OSC_FADE_FRAMES), (t_stand - t_sit) / 4.0))
    return _smoothstep((f - t_sit) / fade) * _smoothstep((t_stand - f) / fade)


def build_observar_keyframes(total_frames, idle_pose_quats):
    """Keyframes de la animacion 'Observar' para `total_frames` frames.

    `idle_pose_quats`: dict hueso -> (w, x, y, z), la pose 'parado' del
    rig (IDLE_POSE_PARADA) -- de ahi se sienta y a ahi vuelve.

    Devuelve (rot_kf, loc_kf), ambos {hueso: {frame_relativo: (x, y, z)}}
    con frames relativos 0..total_frames-1. Sentarse / pararse llevan solo
    los keyframes clave; en el tramo de alerta los huesos con movimiento
    secundario (respiracion, cola, orejas, cabeceo) se muestrean cada
    OSC_KEY_STEP frames y Blender suaviza con Bezier.
    """
    n, t_sit, t_stand = _timeline(total_frames)
    yaw_keys = _scan_yaw_keys(t_sit, t_stand)
    yaw_bones = dict(YAW_BONES)
    alive = (t_stand - t_sit) >= 4

    osc = {}
    for bone, axis, amp, period, phase in IDLE_OSCILLATIONS:
        osc.setdefault(bone, []).append((axis, amp, period, phase))
    twitch = {}
    for bone, axis, amp, pos in EAR_TWITCHES:
        c = int(round(t_sit + pos * (t_stand - t_sit)))
        twitch.setdefault(bone, []).append((axis, amp, c))
    tilt_bone, tilt_axis, tilt_amp = HEAD_TILT

    idle_rot = {b: quat_to_euler_xyz(q) for b, q in idle_pose_quats.items()}
    zero = (0.0, 0.0, 0.0)

    bones = set(idle_rot) | set(SIT_POSE_ROT) | set(yaw_bones)
    if alive:
        bones |= set(osc) | set(twitch)

    grid = list(range(t_sit + OSC_KEY_STEP, t_stand - 1, OSC_KEY_STEP))

    rot_kf = {}
    for bone in sorted(bones):
        stand = idle_rot.get(bone, zero)
        sit = SIT_POSE_ROT.get(bone, zero)
        kf = {0: stand, t_sit: sit, t_stand: sit, n: stand}

        if alive:
            has_yaw = bone in yaw_bones and yaw_keys
            has_tilt = bone == tilt_bone and tilt_amp and yaw_keys
            extra = set()
            if bone in osc:
                extra.update(grid)
            if has_yaw or has_tilt:
                extra.update(f for f, _ in yaw_keys)
            for _ax, _amp, c in twitch.get(bone, ()):
                extra.update((c - 3, c, c + 3))
            for f in sorted(extra):
                if f <= t_sit or f >= t_stand:
                    continue
                r = list(sit)
                env = _osc_envelope(f, t_sit, t_stand)
                if has_yaw:
                    r[YAW_AXIS] += yaw_bones[bone] * _yaw_factor(f, yaw_keys)
                if has_tilt:
                    r[tilt_axis] += tilt_amp * _yaw_factor(f, yaw_keys)
                for axis, amp, period, phase in osc.get(bone, ()):
                    mod = 1.0 + 0.25 * math.sin(2 * math.pi * f / (period * 2.7) + phase)
                    r[axis] += env * amp * mod * math.sin(2 * math.pi * f / period + phase)
                for axis, amp, c in twitch.get(bone, ()):
                    r[axis] += amp * math.exp(-(((f - c) / _TWITCH_SIGMA) ** 2))
                kf[f] = tuple(r)
        rot_kf[bone] = dict(sorted(kf.items()))

    loc_kf = {}
    for bone, loc in SIT_POSE_LOC.items():
        loc_kf[bone] = dict(sorted({0: zero, t_sit: loc, t_stand: loc, n: zero}.items()))
    return rot_kf, loc_kf
