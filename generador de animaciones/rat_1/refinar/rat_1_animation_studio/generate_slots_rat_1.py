# -*- coding: utf-8 -*-
"""
generate_slots_rat_1.py — Rat 1 Animation Studio (Paso 2)

Equivalente reducido de generate_slots_alfred.py. Contiene UNICAMENTE lo
necesario para el sistema de recorrido (deteccion de tramos, estimacion
de frames y generacion de los scripts slot_NNN_*.py), sin las 8
animaciones de accion puntual de Alfred (colocar_antorcha, golpe_estomago,
levantarse, arrodillarse, conversar, resbalarse, colocar_mesa_de_crafteo)
que no aplican a rat_1.

BIOMECANICA REAL (Kebyn, 2026-09-03): generate_caminar(), generate_saltar_subir()
y generate_saltar_bajar() ya NO son placeholders root-only -- animan los 22
bones del armature "body1_1" (cuadrupedo: 2 patas delanteras leftArm_1/
rightArm_1 + leftHand_1/rightHand_1, 2 patas traseras leftThigh_1/rightThigh_1
+ leftFoot_1/rightFoot_1, columna body2_1, cuello/cabeza neck_1/head_1, cola
tail1_1/tail2_1). No hay captura Mixamo para rat_1 (a diferencia de Alfred),
asi que las 3 animaciones son 100% procedurales: caminar usa un ciclo
biomecanico sinusoidal (trote diagonal, tipico de roedores pequeños que se
desplazan rapido), y los saltos usan una secuencia de poses clave
(agazapamiento -> despegue -> vuelo -> aterrizaje) interpoladas con
ease-in-out, en vez de curvas de mocap.

Bones faciales (eyes/ears/snout/nose/wiskers) NO se tocan -- fuera de
alcance de este pipeline (no hay sistema de ojos portado para rat_1).
"""

import math

# =============================================================================
# CONSTANTES DE TIEMPO
# =============================================================================

# Estilos de caminata: mismo esquema que Alfred (multiplicador de
# velocidad y de cadencia del ciclo biomecanico).
WALK_STYLE_PARAMS = {
    "NORMAL": {"label": "Normal", "speed_mult": 1.0, "cycle_mult": 1.0},
    "LENTO":  {"label": "Lento",  "speed_mult": 0.6, "cycle_mult": 1.4},
    "HERIDO": {"label": "Herido", "speed_mult": 0.5, "cycle_mult": 1.6},
    "RAPIDO": {"label": "Rapido", "speed_mult": 1.5, "cycle_mult": 0.75},
    "CORRER": {"label": "Correr", "speed_mult": 2.2, "cycle_mult": 0.55},
}

# Velocidad base del root (unidades Blender por frame, a velocidad de
# estilo NORMAL). Una rata tiene zancada corta pero cadencia muy alta --
# se mantiene el valor de referencia de Alfred como punto de partida
# razonable; lo que realmente define el "caracter" de rata es
# FRAMES_PER_BIO_CYCLE_BASE (mucho mas bajo que el de un biped).
FRAMES_PER_UNIT_BASE = 24.0

# Frames por ciclo biomecanico completo (2 zancadas diagonales) a estilo
# NORMAL. Alfred (biped) usa 20; una rata trotando tiene una cadencia de
# pasos mucho mas rapida en proporcion a su tamaño -- se usa 14 como
# valor de partida (ajustable a ojo desde el panel/estilo).
FRAMES_PER_BIO_CYCLE_BASE = 14.0

# Duracion (frames) de los saltos -- mismos valores de arranque que
# Alfred uso antes de tener curvas Mixamo reales; sirven de referencia
# de timing (18 = salto corto y explosivo).
SALTAR_SUBIR_FRAMES = 18
# PORTADO (Kebyn, 2026-09-03): pedido explicito -- 20 frames (antes 35).
SALTAR_BAJAR_FRAMES = 20

# Frames por defecto de una "parada" cuando no hay nada mas que lo defina.
PARADA_FRAMES_DEFAULT = 60

# Duracion (frames) de las 4 acciones puntuales de rata (Kebyn,
# 2026-09-03/04) -- 100% procedurales, sin mocap, mismo criterio de
# arranque que SALTAR_SUBIR_FRAMES/SALTAR_BAJAR_FRAMES (ajustables a ojo
# una vez validadas en Blender real).
# ACORTADAS (Kebyn, 2026-09-04): "es un raton, sus movimientos deben ser
# mas rapidos por su estado de alerta" -- se recortaron los 4 tiempos
# (mismo numero de ciclos de olfateo/escarbado/masticado, pero
# comprimidos en menos frames = mas rapidos) y se subio ROER_CYCLES de
# 6 a 8 (masticado de roedor real es muy rapido).
TOTAL_FRAMES_PARARSE_DOS_PATAS = 40   # agazapado->erguido->hold->hold->vuelta a 4 patas
TOTAL_FRAMES_OLFATEAR          = 36   # 4 ciclos de olfateo (dips de cabeza), mas rapidos
TOTAL_FRAMES_ESCARBAR          = 60   # 4 ciclos de escarbado alternado, mas rapidos
TOTAL_FRAMES_ROER              = 40   # sentada + 8 ciclos de masticado rapido

# =============================================================================
# BIOMECANICA DE RATA CUADRUPEDA -- amplitudes base (radianes)
# =============================================================================
# Marcha elegida: TROTE DIAGONAL (2 tiempos) -- pata delantera derecha +
# pata trasera izquierda se mueven en fase, y viceversa. Es la marcha mas
# natural para un roedor pequeño desplazandose con decision (a diferencia
# del paso lateral de 4 tiempos, mas propio de animales grandes y lentos).
# Las patas traseras son el motor principal (mayor amplitud, tipico de
# roedores: impulso desde atras), las delanteras sobre todo estabilizan
# y "atrapan" el paso.

BIO_CAMINAR = {
    "front_leg_swing": math.radians(30),   # leftArm_1/rightArm_1 (vaiven sagital, X)
    "hind_leg_swing":  math.radians(48),   # leftThigh_1/rightThigh_1 (motor principal)
    "front_paw_flex":  math.radians(30),   # leftHand_1/rightHand_1 (levanta la mano en el swing)
    "hind_paw_flex":   math.radians(42),   # leftFoot_1/rightFoot_1 (levanta el pie en el swing)
    "spine_bounce":    math.radians(7.0),  # body2_1 X -- rebote dorsoventral, 2x por ciclo (1 por apoyo diagonal)
    "spine_lateral":   math.radians(4.0),  # body2_1 Z -- ondulacion lateral, 1x por ciclo
    "neck_counter":    0.45,               # fraccion de spine_bounce contra-rotada en neck_1 (estabilizacion cabeza)
    "head_counter":    0.60,               # fraccion adicional contra-rotada en head_1
    "tail1_lateral":   math.radians(9.0),  # tail1_1 Z -- contrapeso, fase invertida a spine_lateral
    "tail2_lateral":   math.radians(15.0), # tail2_1 Z -- efecto latigo, mayor amplitud en la punta
    "tail_vertical":   math.radians(7.0),  # tail1_1/tail2_1 X -- ondulacion vertical con retraso de fase
    "tail_lag":        0.15,               # retraso de fase de la cola respecto a la columna (fraccion de ciclo)
}

# Amplitud de la cola en los saltos, relativa a tail1 (tail2 = "punta",
# efecto latigo: se mueve mas que la base de la cola).
TAIL2_WHIP_MULT = 1.6


# =============================================================================
# DETECCION DE TIPO DE MOVIMIENTO (solo AUTO / PARADA -- sin acciones
# puntuales de Alfred)
# =============================================================================

def detect_movement_type(p0, p1):
    """Debe coincidir siempre con _detect_move() en path_recorder.py.
    AMPLIADO (Kebyn, 2026-09-03): 4 acciones puntuales de rata, override
    SIEMPRE evaluado antes de la comparacion de coordenadas (mismo
    criterio que Alfred)."""
    tipo = p0.get("tipo_segmento", "AUTO")
    if tipo == "PARARSE_DOS_PATAS":
        return "pararse_dos_patas"
    if tipo == "OLFATEAR":
        return "olfatear"
    if tipo == "ESCARBAR":
        return "escarbar"
    if tipo == "ROER":
        return "roer"

    x0, y0, z0 = (round(p0["coordinates"]["x"], 2),
                  round(p0["coordinates"]["y"], 2),
                  round(p0["coordinates"]["z"], 2))
    x1, y1, z1 = (round(p1["coordinates"]["x"], 2),
                  round(p1["coordinates"]["y"], 2),
                  round(p1["coordinates"]["z"], 2))
    if x0 == x1 and y0 == y1 and z0 == z1:
        if p0.get("tipo_segmento", "AUTO") == "PARADA":
            return "parada"
        return "caminar"
    if z1 > z0:
        return "saltar_subir"
    if z1 < z0:
        return "saltar_bajar"
    return "caminar"


def group_segments(key_points):
    """Debe coincidir siempre con _group_segments() en path_recorder.py.

    FIX (Kebyn, 2026-09-04, "salto de coordenada tras accion puntual"):
    las 4 acciones puntuales de rata (pararse_dos_patas/olfatear/
    escarbar/roer) dejan el root FIJO en pts[i] durante todo el slot
    (ver generate_pararse_dos_patas()/etc mas abajo) -- nunca caminan
    hasta pts[i+1]. Se fusiona el tramo de alcance pts[i]->pts[i+1] con
    TODO el caminar real que le sigue en un solo segmento "caminar"
    continuo, mismo mecanismo que colocar_antorcha/golpe_estomago_1 en
    Alfred (group_segments(), alfred_animation_studio/
    generate_slots_alfred.py) -- evita tanto el salto de coordenada
    como el reinicio de fase del walk_cycle a mitad de camino."""
    pts = list(key_points)
    segments = []
    i = 0
    _ACCION_OVERRIDES = ("PARARSE_DOS_PATAS", "OLFATEAR", "ESCARBAR", "ROER")
    while i < len(pts) - 1:
        # FIX (mismo criterio que Alfred, "caminar fantasma entre Parada
        # y accion siguiente"): si pts[i] es el punto duplicado de una
        # "parada" y pts[i+1] ya esta marcado con una accion puntual, se
        # salta pts[i] sin emitir segmento -- pts[i+1] arranca su propia
        # accion en la proxima vuelta.
        if (pts[i].get("es_parada_dup", False)
                and pts[i].get("tipo_segmento", "AUTO") not in _ACCION_OVERRIDES
                and pts[i + 1].get("tipo_segmento", "AUTO") in _ACCION_OVERRIDES):
            i += 1
            continue

        move = detect_movement_type(pts[i], pts[i + 1])
        if move == "caminar":
            group = [pts[i]]
            while i < len(pts) - 1 and detect_movement_type(pts[i], pts[i + 1]) == "caminar":
                group.append(pts[i + 1])
                i += 1
            segments.append({"type": "caminar", "points": group})
        elif move in ("pararse_dos_patas", "olfatear", "escarbar", "roer"):
            segments.append({"type": move, "points": [pts[i], pts[i + 1]]})
            _c0 = pts[i]["coordinates"]
            _c1 = pts[i + 1]["coordinates"]
            _same_coord = (round(_c0["x"], 2) == round(_c1["x"], 2)
                           and round(_c0["y"], 2) == round(_c1["y"], 2)
                           and round(_c0["z"], 2) == round(_c1["z"], 2))
            _dest_es_parada = pts[i + 1].get("tipo_segmento", "AUTO") == "PARADA"
            if _same_coord or _dest_es_parada:
                i = i + 1
            else:
                group = [pts[i], pts[i + 1]]
                j = i + 1
                while j < len(pts) - 1 and detect_movement_type(pts[j], pts[j + 1]) == "caminar":
                    group.append(pts[j + 1])
                    j += 1
                segments.append({"type": "caminar", "points": group})
                i = j
        else:
            segments.append({"type": move, "points": [pts[i], pts[i + 1]]})
            i += 1
    return segments


def _compute_direction_angle(p0, p1):
    """Angulo de rumbo (rotation_euler.z, radianes) de p0 hacia p1.

    PORTADO (Kebyn, 2026-09-03): antes devolvia el angulo "crudo" de
    atan2 sin ningun ajuste -- en una diagonal el rumbo quedaba en
    cualquier valor intermedio "sucio" (ej. 43.7 grados) en vez de un
    valor limpio de 45/-45/135/-135, y el resultado se notaba
    especialmente al pasar este angulo como heading heredado
    (prev_rz_exp / prev_rot_z) a un salto o parada que sigue a un tramo
    diagonal. Ahora usa EXACTAMENTE el mismo criterio de snap
    cardinal/diagonal que _compute_direction_angle() en
    alfred_animation_studio/generate_slots_alfred.py: si el angulo real
    cae a menos de 45 grados del multiplo de 90 mas cercano, se redondea
    a ese multiplo (0/90/180/-90 = cardinal, o se conserva "sucio" solo
    si de verdad esta a mitad de camino entre dos cardinales, lo que en
    la practica cubre las diagonales de 45/-45/135/-135). Se asume,
    igual que en Alfred, que el rig de rat_1 en pose de reposo mira
    hacia +Y con rotation_euler.z = 0. Si al probar "Reproducir
    recorrido" el personaje camina de espaldas, invertir el signo de
    dx/dy aca.
    """
    dx = p1["coordinates"]["x"] - p0["coordinates"]["x"]
    dy = p1["coordinates"]["y"] - p0["coordinates"]["y"]
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return None
    ang_raw_deg = math.degrees(math.atan2(dx, dy))
    ang_rounded = round(ang_raw_deg / 90.0) * 90.0
    ang_deg = ang_rounded if abs(ang_raw_deg - ang_rounded) < 45 else -ang_raw_deg
    while ang_deg > 180: ang_deg -= 360
    while ang_deg < -180: ang_deg += 360
    if ang_deg == 90: ang_deg = -90
    elif ang_deg == -90: ang_deg = 90
    elif ang_deg == 180: ang_deg = -180
    return math.radians(ang_deg)


# =============================================================================
# BLOQUE DE CODIGO COMPARTIDO -- se embebe tal cual (sin sustitucion de
# variables) en los 3 tipos de slot. Mantenerlo como texto plano (sin
# llaves de f-string) para no tener que escapar los dict/for de Python.
# =============================================================================

_SHARED_HELPERS = '''
def ease_in_out_sine(t):
    return -(math.cos(math.pi * t) - 1) / 2


def _keyed(t, keys):
    """Interpola una pose-clave definida como lista [(t_i, valor_i), ...]
    (t_i creciente en [0,1]) usando ease-in-out entre cada par de claves
    consecutivas. Es el equivalente procedural de insertar keyframes a
    mano en las poses de agazapamiento/despegue/vuelo/aterrizaje."""
    if t <= keys[0][0]:
        return keys[0][1]
    if t >= keys[-1][0]:
        return keys[-1][1]
    for i in range(len(keys) - 1):
        t0, v0 = keys[i]
        t1, v1 = keys[i + 1]
        if t0 <= t <= t1:
            span = max(t1 - t0, 1e-6)
            return v0 + (v1 - v0) * ease_in_out_sine((t - t0) / span)
    return keys[-1][1]


def _env(t, in_frac=0.15, out_frac=0.15):
    """Envolvente de entrada/salida suave (evita 'pop' al inicio/fin de
    una pose sostenida). Usada por las acciones puntuales de rata
    (pararse_dos_patas/olfatear/escarbar/roer)."""
    if in_frac > 0 and t < in_frac:
        return ease_in_out_sine(t / in_frac)
    if out_frac > 0 and t > 1.0 - out_frac:
        return ease_in_out_sine((1.0 - t) / out_frac)
    return 1.0


def _seg_lengths(pts):
    out = []
    for i in range(len(pts) - 1):
        dx = pts[i + 1][0] - pts[i][0]
        dy = pts[i + 1][1] - pts[i][1]
        out.append(math.sqrt(dx * dx + dy * dy))
    return out


# ============================================================
# SISTEMA DE ORIENTACION -- PORTADO de alfred_animation_studio
# (generate_slots_alfred.py: _compute_direction_angle_local,
# _get_segment_angle_for_frame, RotationSmoother, 2026-09-03).
#
# Antes (_pos_and_angle) el rumbo de cada sub-tramo se calculaba con
# atan2 crudo y se aplicaba de golpe, sin snap a cardinal/diagonal ni
# transicion suave -- el giro entre dos sub-tramos con angulos
# distintos (ej. tramo recto -> tramo en diagonal) se notaba como un
# salto instantaneo de orientacion en vez de un giro progresivo, y en
# diagonales "sucias" (angulo real a pocos grados de un cardinal) el
# rumbo quedaba en un valor no limpio. Ahora se separan POSICION y
# ANGULO como en Alfred: el angulo de cada sub-tramo se snapea a
# cardinal/diagonal, y un RotationSmoother (curva S / smoothstep)
# interpola el giro real a lo largo de 12 frames cuando cambia de
# sub-tramo -- igual smoothing_frames que usa Alfred en su caminar.
# ============================================================

class RotationSmoother:
    """Suaviza cambios de orientacion con curva S (smoothstep). Identico
    al RotationSmoother de generate_slots_alfred.py (caminar)."""
    def __init__(self, smoothing_frames=12):
        self.smoothing_frames = smoothing_frames
        self.previous_rotation = None
        self.transition_start_frame = None
        self.transition_start_rotation = None
        self.target_rotation = None

    def smooth_rotation(self, target_rotation, current_frame):
        target_rotation = self._normalize(target_rotation)
        if self.previous_rotation is None:
            self.previous_rotation = target_rotation
            return target_rotation
        angle_diff = self._diff(target_rotation, self.previous_rotation)
        if abs(angle_diff) < 5:
            self.previous_rotation = target_rotation
            self.transition_start_frame = None
            return target_rotation
        if self.transition_start_frame is None:
            self.transition_start_frame = current_frame
            self.transition_start_rotation = self.previous_rotation
            self.target_rotation = target_rotation
        elapsed = current_frame - self.transition_start_frame
        progress = min(elapsed / self.smoothing_frames, 1.0)
        eased = self._smoothstep(progress)
        smoothed = self.transition_start_rotation + self._diff(
            self.target_rotation, self.transition_start_rotation) * eased
        if progress >= 1.0:
            self.previous_rotation = target_rotation
            self.transition_start_frame = None
            return target_rotation
        return smoothed

    def _normalize(self, a):
        while a > 180: a -= 360
        while a < -180: a += 360
        return a

    def _diff(self, target, current):
        d = target - current
        while d > 180: d -= 360
        while d < -180: d += 360
        return d

    def _smoothstep(self, x):
        if x <= 0: return 0.0
        if x >= 1: return 1.0
        return x * x * (3.0 - 2.0 * x)


def _compute_direction_angle_local(p0, p1):
    """Angulo cardinal/diagonal (grados) del segmento p0->p1, con p0/p1
    como (x, y, z). Mismo criterio de snap que
    _compute_direction_angle_local() en generate_slots_alfred.py."""
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return None
    ang_raw = math.degrees(math.atan2(dx, dy))
    ang_rounded = round(ang_raw / 90.0) * 90.0
    ang = ang_rounded if abs(ang_raw - ang_rounded) < 45 else -ang_raw
    while ang > 180: ang -= 360
    while ang < -180: ang += 360
    if ang == 90: ang = -90
    elif ang == -90: ang = 90
    elif ang == 180: ang = -180
    return ang


def _frames_allocation(lens, total_frames):
    """Reparte total_frames entre sub-tramos proporcional a su longitud.
    Mismo criterio que _compute_frames_allocation() en Alfred."""
    total = sum(lens) or 1.0
    base = [max(1, int(round(total_frames * (l / total)))) for l in lens]
    diff = total_frames - sum(base)
    i = 0
    while diff != 0:
        if diff > 0:
            base[i % len(base)] += 1
            diff -= 1
        else:
            if base[i % len(base)] > 1:
                base[i % len(base)] -= 1
                diff += 1
        i += 1
    cum = []
    acc = 0
    for f in base:
        acc += f
        cum.append(acc)
    return base, cum


def _pos_for_frame(pts, frames_per_seg, cum_frames, frame):
    """Posicion interpolada del sub-tramo activo para este frame
    (0-indexado, sin salto en los limites de sub-tramo). Mismo criterio
    que _get_position_for_frame() en Alfred."""
    prev = 0
    for j, cf in enumerate(cum_frames):
        if frame < cf:
            s, e = pts[j], pts[j + 1]
            steps = max(1, frames_per_seg[j])
            local = frame - prev
            f = max(0.0, min(1.0, local / steps))
            return (s[0] + (e[0] - s[0]) * f,
                    s[1] + (e[1] - s[1]) * f,
                    s[2] + (e[2] - s[2]) * f)
        prev = cf
    return tuple(pts[-1])


def _angle_for_frame(pts, cum_frames, frame, fallback_deg):
    """Angulo cardinal/diagonal (grados) del sub-tramo activo para este
    frame. Mismo criterio que _get_segment_angle_for_frame() en Alfred."""
    for j, cf in enumerate(cum_frames):
        if frame < cf:
            ang = _compute_direction_angle_local(pts[j], pts[j + 1])
            return ang if ang is not None else fallback_deg
    ang = _compute_direction_angle_local(pts[-2], pts[-1])
    return ang if ang is not None else fallback_deg


def _set_bone(pbones, name, rot_xyz, frame):
    pb = pbones.get(name) if pbones else None
    if pb is None:
        return
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = rot_xyz
    pb.keyframe_insert(data_path="rotation_euler", frame=frame)


def _set_root(root, loc, rot_xyz, frame):
    if root is None:
        return
    root.rotation_mode = "XYZ"
    root.location = loc
    root.rotation_euler = rot_xyz
    root.keyframe_insert(data_path="location", frame=frame)
    root.keyframe_insert(data_path="rotation_euler", frame=frame)
'''


def _fmt_points_tuple(points):
    return ",\n".join(
        f"    ({p['coordinates']['x']:.5f}, {p['coordinates']['y']:.5f}, {p['coordinates']['z']:.5f})"
        for p in points
    )


# =============================================================================
# GENERADORES DE SLOTS -- biomecanica real de rata cuadrupeda
# =============================================================================
# Todas devuelven (code:str, end_frame:int), igual que antes, para que
# RAT1PR_OT_ExportSlots pueda escribirlas a disco sin cambios en el resto
# del pipeline.

def generate_caminar(slot_index, frame_start, points, today, root_rot, walk_style="NORMAL"):
    fname = f"slot_{slot_index:03d}_rat_1_caminar.py"
    style = WALK_STYLE_PARAMS.get(walk_style, WALK_STYLE_PARAMS["NORMAL"])

    dist = 0.0
    for j in range(len(points) - 1):
        dx = points[j + 1]["coordinates"]["x"] - points[j]["coordinates"]["x"]
        dy = points[j + 1]["coordinates"]["y"] - points[j]["coordinates"]["y"]
        dist += math.sqrt(dx * dx + dy * dy)
    dist = max(dist, 0.0001)

    # Mismo criterio que Alfred: total_frames se redondea a un multiplo de
    # medio-ciclo biomecanico REAL de este estilo, para que el tramo
    # siempre termine con las patas en pose simetrica (evita el "pop" al
    # encadenar con el siguiente tramo 'caminar').
    frames_per_unit = FRAMES_PER_UNIT_BASE * style["speed_mult"]
    frames_per_bio_cycle = FRAMES_PER_BIO_CYCLE_BASE * style["cycle_mult"]
    half_cycle = frames_per_bio_cycle / 2.0

    raw_frames = dist * frames_per_unit
    n_half = max(1, round(raw_frames / half_cycle))
    n_frames = max(2, round(n_half * half_cycle))
    walk_cycles = n_frames / frames_per_bio_cycle
    frame_end = frame_start + n_frames - 1

    ang = _compute_direction_angle(points[0], points[-1])
    rot_z_fallback = ang if ang is not None else math.radians(root_rot[2])

    traj = _fmt_points_tuple(points)

    code = f'''# -*- coding: utf-8 -*-
"""
{fname}
Rat 1 - Slot {slot_index}
Generado {today} por Rat 1 Animation Studio (Paso 2).

Caminar cuadrupedo (trote diagonal): patas delanteras/traseras opuestas
en fase, columna con rebote dorsoventral + ondulacion lateral, cola de
contrapeso, cabeza estabilizada. 100% procedural (sin mocap).
"""

import bpy
import math

SLOT_INDEX = {slot_index}
START_FRAME = {frame_start}
END_FRAME = {frame_end}
TOTAL_FRAMES = {n_frames}
WALK_CYCLES = {walk_cycles:.4f}
FRAMES_PER_BIO_CYCLE = {frames_per_bio_cycle:.4f}
WALK_STYLE = "{walk_style}"

ROOT_ROT_X = math.radians({root_rot[0]})
ROOT_ROT_Y = math.radians({root_rot[1]})
FALLBACK_ROT_Z = {rot_z_fallback:.6f}

PATH_POINTS = [
{traj}
]

ANIMATION_INFO = {{
    'name': '{fname}',
    'entity': 'rat_1',
    'slot': {slot_index},
    'movement_type': 'caminar_cuadrupedo_trote_diagonal',
    'frame_count': {n_frames},
    'fps': 24,
    'walk_style': WALK_STYLE,
}}

root = bpy.data.objects.get('rat_1')
arm  = bpy.data.objects.get('body1_1')
pbones = arm.pose.bones if arm else None

{_SHARED_HELPERS}

# ── Amplitudes biomecanicas (radianes) ──────────────────────────────────
FRONT_LEG_SWING = math.radians({math.degrees(BIO_CAMINAR["front_leg_swing"]):.4f})
HIND_LEG_SWING  = math.radians({math.degrees(BIO_CAMINAR["hind_leg_swing"]):.4f})
FRONT_PAW_FLEX  = math.radians({math.degrees(BIO_CAMINAR["front_paw_flex"]):.4f})
HIND_PAW_FLEX   = math.radians({math.degrees(BIO_CAMINAR["hind_paw_flex"]):.4f})
SPINE_BOUNCE    = math.radians({math.degrees(BIO_CAMINAR["spine_bounce"]):.4f})
SPINE_LATERAL   = math.radians({math.degrees(BIO_CAMINAR["spine_lateral"]):.4f})
NECK_COUNTER    = {BIO_CAMINAR["neck_counter"]}
HEAD_COUNTER    = {BIO_CAMINAR["head_counter"]}
TAIL1_LATERAL   = math.radians({math.degrees(BIO_CAMINAR["tail1_lateral"]):.4f})
TAIL2_LATERAL   = math.radians({math.degrees(BIO_CAMINAR["tail2_lateral"]):.4f})
TAIL_VERTICAL   = math.radians({math.degrees(BIO_CAMINAR["tail_vertical"]):.4f})
TAIL_LAG        = {BIO_CAMINAR["tail_lag"]}


def calc_leg_swing(phase, amp):
    return amp * math.sin(phase * 2 * math.pi)


def calc_paw_flex(phase, amp):
    # Bulto de flexion solo durante el swing real (fase 0.75->1.0->0.25),
    # en 0 durante todo el apoyo (fase 0.25-0.75) -- evita que la pata
    # arrastre por el suelo al recuperarse hacia adelante.
    return amp * max(0.0, math.sin((phase - 0.75) * 2 * math.pi))


def execute_animation():
    _lens = _seg_lengths(PATH_POINTS)
    _frames_per_seg, _cum_frames = _frames_allocation(_lens, TOTAL_FRAMES)
    _fallback_deg = math.degrees(FALLBACK_ROT_Z)
    _smoother = RotationSmoother(smoothing_frames=12)

    for frame in range(START_FRAME, END_FRAME + 1):
        rf = frame - START_FRAME
        s = rf / max(TOTAL_FRAMES - 1, 1)
        walk_cycle = s * WALK_CYCLES

        pos = _pos_for_frame(PATH_POINTS, _frames_per_seg, _cum_frames, rf)
        _seg_ang = _angle_for_frame(PATH_POINTS, _cum_frames, rf, _fallback_deg)
        _smoothed_ang = _smoother.smooth_rotation(_seg_ang, rf)
        rz = math.radians(_smoothed_ang)
        _set_root(root, pos, (ROOT_ROT_X, ROOT_ROT_Y, rz), frame)

        # Marcha: trote diagonal -- RF+LH en fase, LF+RH en fase+0.5
        phase_rf = walk_cycle % 1.0
        phase_lh = walk_cycle % 1.0
        phase_lf = (walk_cycle + 0.5) % 1.0
        phase_rh = (walk_cycle + 0.5) % 1.0

        rf_swing = calc_leg_swing(phase_rf, FRONT_LEG_SWING)
        lf_swing = calc_leg_swing(phase_lf, FRONT_LEG_SWING)
        lh_swing = calc_leg_swing(phase_lh, HIND_LEG_SWING)
        rh_swing = calc_leg_swing(phase_rh, HIND_LEG_SWING)

        _set_bone(pbones, 'rightArm_1',   (rf_swing, 0.0, 0.0), frame)
        _set_bone(pbones, 'leftArm_1',    (lf_swing, 0.0, 0.0), frame)
        _set_bone(pbones, 'leftThigh_1',  (lh_swing, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightThigh_1', (rh_swing, 0.0, 0.0), frame)

        _set_bone(pbones, 'rightHand_1', (calc_paw_flex(phase_rf, FRONT_PAW_FLEX), 0.0, 0.0), frame)
        _set_bone(pbones, 'leftHand_1',  (calc_paw_flex(phase_lf, FRONT_PAW_FLEX), 0.0, 0.0), frame)
        _set_bone(pbones, 'leftFoot_1',  (calc_paw_flex(phase_lh, HIND_PAW_FLEX), 0.0, 0.0), frame)
        _set_bone(pbones, 'rightFoot_1', (calc_paw_flex(phase_rh, HIND_PAW_FLEX), 0.0, 0.0), frame)

        # Columna: rebote dorsoventral (2x por ciclo, un impacto por cada
        # apoyo diagonal) + ondulacion lateral (1x por ciclo)
        spine_x = -SPINE_BOUNCE * math.cos(walk_cycle * 4 * math.pi)
        spine_z = SPINE_LATERAL * math.sin(walk_cycle * 2 * math.pi)
        _set_bone(pbones, 'body2_1', (spine_x, 0.0, spine_z), frame)
        _set_bone(pbones, 'body1_1', (0.0, 0.0, 0.0), frame)

        # Cuello/cabeza: contra-rotacion de estabilizacion (reflejo
        # vestibular simplificado) contra el rebote de columna
        neck_x = -spine_x * NECK_COUNTER
        head_x = -spine_x * NECK_COUNTER * HEAD_COUNTER
        _set_bone(pbones, 'neck_1', (neck_x, 0.0, -spine_z * 0.3), frame)
        _set_bone(pbones, 'head_1', (head_x, 0.0, 0.0), frame)

        # Cola: contrapeso lateral con retraso de fase respecto a la
        # columna, y ondulacion vertical (efecto latigo, mas amplitud en
        # la punta tail2 que en la base tail1)
        tail_cycle = walk_cycle - TAIL_LAG
        tail_z = -TAIL1_LATERAL * math.sin(tail_cycle * 2 * math.pi)
        tail2_z = -TAIL2_LATERAL * math.sin(tail_cycle * 2 * math.pi)
        tail_x = TAIL_VERTICAL * math.cos(tail_cycle * 4 * math.pi)
        _set_bone(pbones, 'tail1_1', (tail_x, 0.0, tail_z), frame)
        _set_bone(pbones, 'tail2_1', (tail_x * 1.3, 0.0, tail2_z), frame)


execute_animation()
'''
    return code, frame_end


def generate_saltar_subir(slot_index, frame_start, points, today, root_rot):
    fname = f"slot_{slot_index:03d}_rat_1_saltar_subir.py"
    n_frames = SALTAR_SUBIR_FRAMES
    frame_end = frame_start + n_frames - 1

    ang = _compute_direction_angle(points[0], points[-1])
    rot_z_fallback = ang if ang is not None else math.radians(root_rot[2])

    p0 = points[0]["coordinates"]
    p1 = points[-1]["coordinates"]
    traj = _fmt_points_tuple(points)

    code = f'''# -*- coding: utf-8 -*-
"""
{fname}
Rat 1 - Slot {slot_index}
Generado {today} por Rat 1 Animation Studio (Paso 2).

Salto hacia arriba: agazapamiento -> despegue explosivo (patas traseras,
motor principal del salto en un roedor) -> vuelo con cuerpo plegado ->
patas delanteras extendidas para alcanzar el aterrizaje. 100% procedural
(secuencia de poses clave interpoladas con ease-in-out).
"""

import bpy
import math

SLOT_INDEX = {slot_index}
START_FRAME = {frame_start}
END_FRAME = {frame_end}
TOTAL_FRAMES = {n_frames}

ROOT_ROT_X = math.radians({root_rot[0]})
ROOT_ROT_Y = math.radians({root_rot[1]})
FALLBACK_ROT_Z = {rot_z_fallback:.6f}

P0 = ({p0["x"]:.5f}, {p0["y"]:.5f}, {p0["z"]:.5f})
P1 = ({p1["x"]:.5f}, {p1["y"]:.5f}, {p1["z"]:.5f})

ANIMATION_INFO = {{
    'name': '{fname}',
    'entity': 'rat_1',
    'slot': {slot_index},
    'movement_type': 'saltar_subir_cuadrupedo',
    'frame_count': {n_frames},
    'fps': 24,
}}

root = bpy.data.objects.get('rat_1')
arm  = bpy.data.objects.get('body1_1')
pbones = arm.pose.bones if arm else None

{_SHARED_HELPERS}

# PORTADO (Kebyn, 2026-09-03): antes calc_direction() devolvia un rumbo
# fijo para todo el salto, calculado con atan2 crudo (sin snap
# cardinal/diagonal) -- el personaje "tele-orientaba" de golpe al
# primer frame del salto en vez de girar progresivamente desde el
# heading con el que veniia caminando. Ahora el angulo objetivo se
# snapea a cardinal/diagonal (_compute_direction_angle_local) y se
# interpola con una curva S desde FALLBACK_ROT_Z (heading heredado del
# tramo anterior) durante los primeros frames del salto -- mismo
# criterio que _build_rotation_data() en generate_slots_alfred.py
# (smoothing = 8 frames, mas rapido que el caminar por ser un salto).
_TARGET_ANG_DEG = _compute_direction_angle_local(P0, P1)
_BASE_ANG_DEG = math.degrees(FALLBACK_ROT_Z)
if _TARGET_ANG_DEG is None:
    _TARGET_ANG_DEG = _BASE_ANG_DEG
_ROT_SMOOTHING_FRAMES = min(8, max(1, TOTAL_FRAMES - 1))


def calc_direction_for_frame(rf):
    """Rumbo (radianes) para el frame relativo rf (0-indexado): curva S
    desde el heading heredado (_BASE_ANG_DEG) hacia el rumbo real del
    salto (_TARGET_ANG_DEG) en _ROT_SMOOTHING_FRAMES frames."""
    if abs(_TARGET_ANG_DEG - _BASE_ANG_DEG) < 0.1:
        return math.radians(_TARGET_ANG_DEG)
    progress = min(rf / _ROT_SMOOTHING_FRAMES, 1.0)
    eased = progress * progress * (3.0 - 2.0 * progress)
    diff = _TARGET_ANG_DEG - _BASE_ANG_DEG
    while diff > 180: diff -= 360
    while diff < -180: diff += 360
    return math.radians(_BASE_ANG_DEG + diff * eased)


def calc_root_position(t):
    """Parabola ascendente (arco de salto), igual criterio que Alfred."""
    dx = P1[0] - P0[0]; dy = P1[1] - P0[1]; dz = P1[2] - P0[2]
    t_s = t * t * (3 - 2 * t)  # smoothstep
    dist_xy = math.sqrt(dx * dx + dy * dy)
    H = max(abs(dz) * 0.6, dist_xy * 0.35, 0.25)
    arc = 4 * H * t_s * (1 - t_s)
    return (P0[0] + t_s * dx, P0[1] + t_s * dy, P0[2] + t_s * dz + arc)


# ── Poses clave (radianes) por fase t en [0,1] ──────────────────────────
# t=0.00 de pie | t=0.28 agazapado (maxima flexion, impulso) |
# t=0.62 despegue extendido | t=0.85 vuelo plegado | t=1.00 aterrizaje
KEYS_HIND_SWING     = [(0.0, 0.0), (0.28, math.radians(35)),  (0.62, math.radians(-55)), (0.85, math.radians(25)), (1.0, math.radians(-8))]
KEYS_HIND_PAW       = [(0.0, 0.0), (0.28, math.radians(45)),  (0.62, math.radians(-10)), (0.85, math.radians(35)), (1.0, math.radians(10))]
KEYS_FRONT_SWING    = [(0.0, 0.0), (0.28, math.radians(15)),  (0.62, math.radians(-20)), (0.85, math.radians(30)), (1.0, math.radians(50))]
KEYS_FRONT_PAW      = [(0.0, 0.0), (0.28, math.radians(30)),  (0.62, math.radians(10)),  (0.85, math.radians(-15)), (1.0, math.radians(-30))]
KEYS_SPINE_X        = [(0.0, 0.0), (0.28, math.radians(-8)),  (0.62, math.radians(10)),  (0.85, math.radians(-5)), (1.0, math.radians(6))]
KEYS_TAIL_X         = [(0.0, 0.0), (0.28, math.radians(-10)), (0.62, math.radians(28)),  (0.85, math.radians(5)), (1.0, math.radians(-5))]

NECK_COUNTER = 0.45
HEAD_COUNTER = 0.60


def execute_animation():
    for frame in range(START_FRAME, END_FRAME + 1):
        rf = frame - START_FRAME
        t = rf / max(TOTAL_FRAMES - 1, 1)
        root_rz = calc_direction_for_frame(rf)

        _set_root(root, calc_root_position(t), (ROOT_ROT_X, ROOT_ROT_Y, root_rz), frame)

        hind_swing = _keyed(t, KEYS_HIND_SWING)
        front_swing = _keyed(t, KEYS_FRONT_SWING)
        _set_bone(pbones, 'leftThigh_1',  (hind_swing, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightThigh_1', (hind_swing, 0.0, 0.0), frame)
        _set_bone(pbones, 'leftFoot_1',   (_keyed(t, KEYS_HIND_PAW), 0.0, 0.0), frame)
        _set_bone(pbones, 'rightFoot_1',  (_keyed(t, KEYS_HIND_PAW), 0.0, 0.0), frame)
        _set_bone(pbones, 'leftArm_1',    (front_swing, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightArm_1',   (front_swing, 0.0, 0.0), frame)
        _set_bone(pbones, 'leftHand_1',   (_keyed(t, KEYS_FRONT_PAW), 0.0, 0.0), frame)
        _set_bone(pbones, 'rightHand_1',  (_keyed(t, KEYS_FRONT_PAW), 0.0, 0.0), frame)

        spine_x = _keyed(t, KEYS_SPINE_X)
        _set_bone(pbones, 'body2_1', (spine_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'body1_1', (0.0, 0.0, 0.0), frame)
        _set_bone(pbones, 'neck_1', (-spine_x * NECK_COUNTER, 0.0, 0.0), frame)
        _set_bone(pbones, 'head_1', (-spine_x * NECK_COUNTER * HEAD_COUNTER, 0.0, 0.0), frame)

        tail_x = _keyed(t, KEYS_TAIL_X)
        _set_bone(pbones, 'tail1_1', (tail_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'tail2_1', (tail_x * {TAIL2_WHIP_MULT}, 0.0, 0.0), frame)


execute_animation()
'''
    return code, frame_end


def generate_saltar_bajar(slot_index, frame_start, points, today, root_rot):
    fname = f"slot_{slot_index:03d}_rat_1_saltar_bajar.py"
    n_frames = SALTAR_BAJAR_FRAMES
    frame_end = frame_start + n_frames - 1

    ang = _compute_direction_angle(points[0], points[-1])
    rot_z_fallback = ang if ang is not None else math.radians(root_rot[2])

    p0 = points[0]["coordinates"]
    p1 = points[-1]["coordinates"]
    traj = _fmt_points_tuple(points)

    code = f'''# -*- coding: utf-8 -*-
"""
{fname}
Rat 1 - Slot {slot_index}
Generado {today} por Rat 1 Animation Studio (Paso 2).

Salto hacia abajo: caida con patas delanteras extendidas por delante
(primeras en tocar el suelo) -> impacto y absorcion profunda (columna se
comprime, patas se flexionan) -> las traseras aterrizan un instante
despues y tambien absorben -> recuperacion hacia la postura neutra.
100% procedural (secuencia de poses clave interpoladas con ease-in-out).
"""

import bpy
import math

SLOT_INDEX = {slot_index}
START_FRAME = {frame_start}
END_FRAME = {frame_end}
TOTAL_FRAMES = {n_frames}

ROOT_ROT_X = math.radians({root_rot[0]})
ROOT_ROT_Y = math.radians({root_rot[1]})
FALLBACK_ROT_Z = {rot_z_fallback:.6f}

P0 = ({p0["x"]:.5f}, {p0["y"]:.5f}, {p0["z"]:.5f})
P1 = ({p1["x"]:.5f}, {p1["y"]:.5f}, {p1["z"]:.5f})

ANIMATION_INFO = {{
    'name': '{fname}',
    'entity': 'rat_1',
    'slot': {slot_index},
    'movement_type': 'saltar_bajar_cuadrupedo',
    'frame_count': {n_frames},
    'fps': 24,
}}

root = bpy.data.objects.get('rat_1')
arm  = bpy.data.objects.get('body1_1')
pbones = arm.pose.bones if arm else None

{_SHARED_HELPERS}

# PORTADO (Kebyn, 2026-09-03): mismo criterio que en generate_saltar_subir
# -- rumbo objetivo snapeado a cardinal/diagonal, interpolado con curva S
# desde el heading heredado del tramo anterior (ver comentario detallado
# en generate_saltar_subir()).
_TARGET_ANG_DEG = _compute_direction_angle_local(P0, P1)
_BASE_ANG_DEG = math.degrees(FALLBACK_ROT_Z)
if _TARGET_ANG_DEG is None:
    _TARGET_ANG_DEG = _BASE_ANG_DEG
_ROT_SMOOTHING_FRAMES = min(8, max(1, TOTAL_FRAMES - 1))


def calc_direction_for_frame(rf):
    """Rumbo (radianes) para el frame relativo rf (0-indexado): curva S
    desde el heading heredado (_BASE_ANG_DEG) hacia el rumbo real del
    salto (_TARGET_ANG_DEG) en _ROT_SMOOTHING_FRAMES frames."""
    if abs(_TARGET_ANG_DEG - _BASE_ANG_DEG) < 0.1:
        return math.radians(_TARGET_ANG_DEG)
    progress = min(rf / _ROT_SMOOTHING_FRAMES, 1.0)
    eased = progress * progress * (3.0 - 2.0 * progress)
    diff = _TARGET_ANG_DEG - _BASE_ANG_DEG
    while diff > 180: diff -= 360
    while diff < -180: diff += 360
    return math.radians(_BASE_ANG_DEG + diff * eased)


def calc_root_position(t):
    """Parabola de proyectil (arco hacia afuera, NO caida recta): el
    personaje se impulsa hacia adelante/arriba al salir del borde y
    recien despues cae, en vez de descender pegado a la cara vertical
    del bloque/plataforma -- evita que partes de la malla atraviesen la
    geometria del borde. Misma formula de arco que calc_root_position()
    de generate_saltar_subir() (arco = 4*H*t_s*(1-t_s) sumado sobre la
    interpolacion lineal P0->P1), con H mas chico por ser un salto hacia
    abajo (impulso de salida, no de elevacion). PORTADO (Kebyn,
    2026-09-03), pedido explicito con referencia grafica."""
    dx = P1[0] - P0[0]; dy = P1[1] - P0[1]; dz = P1[2] - P0[2]
    t_s = t * t * (3 - 2 * t)  # smoothstep
    dist_xy = math.sqrt(dx * dx + dy * dy)
    H = max(abs(dz) * 0.3, dist_xy * 0.3, 0.2)
    arc = 4 * H * t_s * (1 - t_s)
    return (P0[0] + t_s * dx, P0[1] + t_s * dy, P0[2] + t_s * dz + arc)


# ── Poses clave (radianes) por fase t en [0,1] ──────────────────────────
# t=0.00 inicio de caida | t=0.50 extension maxima en el aire |
# t=0.75 impacto (delanteras aterrizan y flexionan) |
# t=0.90 compresion maxima (traseras ya aterrizaron) | t=1.00 asentado
KEYS_FRONT_SWING = [(0.0, 0.0), (0.5, math.radians(45)),  (0.75, math.radians(30)), (0.9, math.radians(5)),   (1.0, 0.0)]
KEYS_FRONT_PAW   = [(0.0, 0.0), (0.5, math.radians(-20)), (0.75, math.radians(35)), (0.9, math.radians(50)),  (1.0, math.radians(10))]
KEYS_HIND_SWING  = [(0.0, 0.0), (0.5, math.radians(-35)), (0.75, math.radians(-15)),(0.9, math.radians(30)),  (1.0, math.radians(5))]
KEYS_HIND_PAW    = [(0.0, 0.0), (0.5, math.radians(-10)), (0.75, math.radians(15)), (0.9, math.radians(48)),  (1.0, math.radians(12))]
KEYS_SPINE_X     = [(0.0, 0.0), (0.5, math.radians(8)),   (0.75, math.radians(-4)), (0.9, math.radians(-14)), (1.0, math.radians(-3))]
KEYS_TAIL_X      = [(0.0, 0.0), (0.5, math.radians(20)),  (0.75, math.radians(-8)), (0.9, math.radians(-22)), (1.0, math.radians(-4))]

NECK_COUNTER = 0.45
HEAD_COUNTER = 0.60


def execute_animation():
    for frame in range(START_FRAME, END_FRAME + 1):
        rf = frame - START_FRAME
        t = rf / max(TOTAL_FRAMES - 1, 1)
        root_rz = calc_direction_for_frame(rf)

        _set_root(root, calc_root_position(t), (ROOT_ROT_X, ROOT_ROT_Y, root_rz), frame)

        front_swing = _keyed(t, KEYS_FRONT_SWING)
        hind_swing = _keyed(t, KEYS_HIND_SWING)
        _set_bone(pbones, 'leftArm_1',    (front_swing, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightArm_1',   (front_swing, 0.0, 0.0), frame)
        _set_bone(pbones, 'leftHand_1',   (_keyed(t, KEYS_FRONT_PAW), 0.0, 0.0), frame)
        _set_bone(pbones, 'rightHand_1',  (_keyed(t, KEYS_FRONT_PAW), 0.0, 0.0), frame)
        _set_bone(pbones, 'leftThigh_1',  (hind_swing, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightThigh_1', (hind_swing, 0.0, 0.0), frame)
        _set_bone(pbones, 'leftFoot_1',   (_keyed(t, KEYS_HIND_PAW), 0.0, 0.0), frame)
        _set_bone(pbones, 'rightFoot_1',  (_keyed(t, KEYS_HIND_PAW), 0.0, 0.0), frame)

        spine_x = _keyed(t, KEYS_SPINE_X)
        _set_bone(pbones, 'body2_1', (spine_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'body1_1', (0.0, 0.0, 0.0), frame)
        _set_bone(pbones, 'neck_1', (-spine_x * NECK_COUNTER, 0.0, 0.0), frame)
        _set_bone(pbones, 'head_1', (-spine_x * NECK_COUNTER * HEAD_COUNTER, 0.0, 0.0), frame)

        tail_x = _keyed(t, KEYS_TAIL_X)
        _set_bone(pbones, 'tail1_1', (tail_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'tail2_1', (tail_x * {TAIL2_WHIP_MULT}, 0.0, 0.0), frame)


execute_animation()
'''
    return code, frame_end


def generate_parada(slot_index, frame_start, points, today, root_rot, frames_parada=PARADA_FRAMES_DEFAULT):
    fname = f"slot_{slot_index:03d}_rat_1_parada.py"
    frame_end = frame_start + max(1, frames_parada) - 1
    p0 = points[0]["coordinates"]
    rot_z = math.radians(root_rot[2])

    code = f'''# -*- coding: utf-8 -*-
"""
{fname}
Rat 1 - Slot {slot_index}
Generado {today} por Rat 1 Animation Studio (Paso 2).
Parada: el EMPTY raiz se mantiene fijo (sin biomecanica de bones -- fuera
de alcance de este port, ver PORT_NOTES.md).
"""

import bpy

root = bpy.data.objects.get('rat_1')

if root:
    root.location = ({p0["x"]:.5f}, {p0["y"]:.5f}, {p0["z"]:.5f})
    root.rotation_euler = ({math.radians(root_rot[0]):.5f}, {math.radians(root_rot[1]):.5f}, {rot_z:.5f})
    bpy.context.scene.frame_set({frame_start})
    root.keyframe_insert(data_path='location', frame={frame_start})
    root.keyframe_insert(data_path='rotation_euler', frame={frame_start})
    bpy.context.scene.frame_set({frame_end})
    root.keyframe_insert(data_path='location', frame={frame_end})
    root.keyframe_insert(data_path='rotation_euler', frame={frame_end})
'''
    return code, frame_end


def generate_idle(slot_index, frame_start, point, today, root_rot, total_frames=60):
    fname = f"slot_{slot_index:03d}_rat_1_idle.py"
    frame_end = frame_start + max(1, total_frames) - 1
    p0 = point["coordinates"]
    rot_z = math.radians(root_rot[2])

    code = f'''# -*- coding: utf-8 -*-
"""
{fname}
Rat 1 - Slot {slot_index}
Generado {today} por Rat 1 Animation Studio (Paso 2).
Idle: el EMPTY raiz se mantiene fijo (sin biomecanica de bones -- fuera
de alcance de este port, ver PORT_NOTES.md).
"""

import bpy

root = bpy.data.objects.get('rat_1')

if root:
    root.location = ({p0["x"]:.5f}, {p0["y"]:.5f}, {p0["z"]:.5f})
    root.rotation_euler = ({math.radians(root_rot[0]):.5f}, {math.radians(root_rot[1]):.5f}, {rot_z:.5f})
    bpy.context.scene.frame_set({frame_start})
    root.keyframe_insert(data_path='location', frame={frame_start})
    root.keyframe_insert(data_path='rotation_euler', frame={frame_start})
    bpy.context.scene.frame_set({frame_end})
    root.keyframe_insert(data_path='location', frame={frame_end})
    root.keyframe_insert(data_path='rotation_euler', frame={frame_end})
'''
    return code, frame_end


# =============================================================================
# ACCIONES PUNTUALES DE RATA (Kebyn, 2026-09-03)
# =============================================================================
# Agregadas siguiendo el mismo principio que las acciones puntuales de
# Alfred (alfred_animation_studio/docs/GUIA_NUEVOS_SEGMENTOS_ESPECIALES.md,
# sub-patron B: "Animacion pura", sin objeto -- ver generate_golpe_estomago_1()
# en generate_slots_alfred.py como referencia de arquitectura): el root
# queda FIJO en points[0] durante todo el slot (el desplazamiento real, si
# lo hay, lo hace el tramo 'caminar' que group_segments() agrega despues
# de forma natural), y solo GIRA hacia points[-1] con la misma curva-S de
# orientacion (RotationSmoother-like, 8 frames) que usan los saltos.
#
# Diferencia frente a Alfred: rat_1 no tiene captura Mixamo, asi que las 4
# poses son 100% procedurales (igual que caminar/saltar_subir/saltar_bajar
# de este mismo port) -- secuencias de poses clave (_keyed) o ciclos
# sinusoidales con envolvente (_env), en vez de curvas de mocap. Amplitudes
# y signos son un punto de partida razonable, pendientes de validar en
# Blender real (ver PORT_NOTES.md: si alguna pata/cola rota "al reves",
# invertir el signo de esa amplitud puntual, igual que con caminar/saltos).

def generate_pararse_dos_patas(slot_index, frame_start, points, today, root_rot):
    """La rata se yergue sobre las patas traseras (vigilar/olfatear el
    entorno desde altura): columna se endereza, patas delanteras se
    pliegan contra el pecho, cola se apoya atras como contrapeso, luego
    vuelve a 4 patas. Orejas erguidas y bigotes en abanico (postura de
    alerta/vigilancia), nariz olfatea el aire mientras esta arriba."""
    fname = f"slot_{slot_index:03d}_rat_1_pararse_dos_patas.py"
    n_frames = TOTAL_FRAMES_PARARSE_DOS_PATAS
    frame_end = frame_start + n_frames - 1

    ang = _compute_direction_angle(points[0], points[-1])
    rot_z_fallback = ang if ang is not None else math.radians(root_rot[2])

    p0 = points[0]["coordinates"]
    p1 = points[-1]["coordinates"]

    code = f'''# -*- coding: utf-8 -*-
"""
{fname}
Rat 1 - Slot {slot_index}
Generado {today} por Rat 1 Animation Studio (Paso 2).

Pararse en 2 patas: la rata se yergue sobre las patas traseras para
vigilar/olfatear el entorno. Root FIJO en P0 (no se desplaza -- igual
que golpe_estomago_1 en Alfred), gira hacia P1. 100% procedural
(secuencia de poses clave interpoladas con ease-in-out). Incluye orejas,
nariz y bigotes (postura de alerta).

FIX (Kebyn, 2026-09-04): la convencion real del rig es X POSITIVO en
body2_1 = columna se yergue, X NEGATIVO = se inclina hacia el suelo
(antes estaba invertido y la rata se hundia en el piso en vez de
pararse). Cuello/cabeza van con signo opuesto a la columna (para
mantener la cabeza mas o menos nivelada mientras la columna gira).
"""

import bpy
import math

SLOT_INDEX = {slot_index}
START_FRAME = {frame_start}
END_FRAME = {frame_end}
TOTAL_FRAMES = {n_frames}

ROOT_ROT_X = math.radians({root_rot[0]})
ROOT_ROT_Y = math.radians({root_rot[1]})
FALLBACK_ROT_Z = {rot_z_fallback:.6f}

P0 = ({p0["x"]:.5f}, {p0["y"]:.5f}, {p0["z"]:.5f})
P1 = ({p1["x"]:.5f}, {p1["y"]:.5f}, {p1["z"]:.5f})

ANIMATION_INFO = {{
    'name': '{fname}',
    'entity': 'rat_1',
    'slot': {slot_index},
    'movement_type': 'pararse_dos_patas',
    'frame_count': {n_frames},
    'fps': 24,
}}

# Root Location: FIJO en P0 durante todo el slot -- la rata esta parada
# ahi mientras se yergue sobre las patas traseras.

root = bpy.data.objects.get('rat_1')
arm  = bpy.data.objects.get('body1_1')
pbones = arm.pose.bones if arm else None

{_SHARED_HELPERS}

_TARGET_ANG_DEG = _compute_direction_angle_local(P0, P1)
_BASE_ANG_DEG = math.degrees(FALLBACK_ROT_Z)
if _TARGET_ANG_DEG is None:
    _TARGET_ANG_DEG = _BASE_ANG_DEG
# Kebyn (2026-09-04): raton en estado de alerta -- smoothing corto (5)
# para que gire mas rapido hacia la nueva orientacion.
_ROT_SMOOTHING_FRAMES = min(5, max(1, TOTAL_FRAMES - 1))


def calc_direction_for_frame(rf):
    if abs(_TARGET_ANG_DEG - _BASE_ANG_DEG) < 0.1:
        return math.radians(_TARGET_ANG_DEG)
    progress = min(rf / _ROT_SMOOTHING_FRAMES, 1.0)
    eased = progress * progress * (3.0 - 2.0 * progress)
    diff = _TARGET_ANG_DEG - _BASE_ANG_DEG
    while diff > 180: diff -= 360
    while diff < -180: diff += 360
    return math.radians(_BASE_ANG_DEG + diff * eased)


# ── Poses clave (radianes) por fase t en [0,1] ──────────────────────────
# t=0.00 en 4 patas | t=0.30 subiendo | t=0.55 erguida (inicio hold) |
# t=0.85 erguida (fin hold) | t=1.00 vuelta a 4 patas
KEYS_SPINE    = [(0.0, 0.0), (0.30, math.radians(70)),  (0.55, math.radians(70)),  (0.85, math.radians(70)),  (1.0, 0.0)]
KEYS_NECK     = [(0.0, 0.0), (0.30, math.radians(-20)), (0.55, math.radians(-20)), (0.85, math.radians(-20)), (1.0, 0.0)]
KEYS_HEAD     = [(0.0, 0.0), (0.30, math.radians(-12)), (0.55, math.radians(-12)), (0.85, math.radians(-12)), (1.0, 0.0)]
KEYS_ARM      = [(0.0, 0.0), (0.30, math.radians(90)),  (0.55, math.radians(90)),  (0.85, math.radians(90)),  (1.0, 0.0)]
KEYS_HAND     = [(0.0, 0.0), (0.30, math.radians(-35)), (0.55, math.radians(-35)), (0.85, math.radians(-35)), (1.0, 0.0)]
KEYS_THIGH    = [(0.0, 0.0), (0.30, math.radians(-12)), (0.55, math.radians(-12)), (0.85, math.radians(-12)), (1.0, 0.0)]
KEYS_FOOT     = [(0.0, 0.0), (0.30, math.radians(8)),   (0.55, math.radians(8)),   (0.85, math.radians(8)),   (1.0, 0.0)]
KEYS_TAIL1    = [(0.0, 0.0), (0.30, math.radians(18)),  (0.55, math.radians(18)),  (0.85, math.radians(18)),  (1.0, 0.0)]
KEYS_TAIL2    = [(0.0, 0.0), (0.30, math.radians(26)),  (0.55, math.radians(26)),  (0.85, math.radians(26)),  (1.0, 0.0)]
KEYS_EAR      = [(0.0, 0.0), (0.30, math.radians(25)),  (0.55, math.radians(25)),  (0.85, math.radians(25)),  (1.0, 0.0)]
KEYS_WHISKER  = [(0.0, 0.0), (0.30, math.radians(15)),  (0.55, math.radians(15)),  (0.85, math.radians(15)),  (1.0, 0.0)]
KEYS_HOLD_ENV = [(0.0, 0.0), (0.30, 1.0), (0.85, 1.0), (1.0, 0.0)]

NOSE_AMP = math.radians(10)
NOSE_CYCLES = 6


def execute_animation():
    for frame in range(START_FRAME, END_FRAME + 1):
        rf = frame - START_FRAME
        t = rf / max(TOTAL_FRAMES - 1, 1)
        root_rz = calc_direction_for_frame(rf)
        _set_root(root, P0, (ROOT_ROT_X, ROOT_ROT_Y, root_rz), frame)

        _set_bone(pbones, 'body2_1', (_keyed(t, KEYS_SPINE), 0.0, 0.0), frame)
        _set_bone(pbones, 'body1_1', (0.0, 0.0, 0.0), frame)
        _set_bone(pbones, 'neck_1', (_keyed(t, KEYS_NECK), 0.0, 0.0), frame)
        _set_bone(pbones, 'head_1', (_keyed(t, KEYS_HEAD), 0.0, 0.0), frame)

        arm_x = _keyed(t, KEYS_ARM)
        hand_x = _keyed(t, KEYS_HAND)
        _set_bone(pbones, 'leftArm_1', (arm_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightArm_1', (arm_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'leftHand_1', (hand_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightHand_1', (hand_x, 0.0, 0.0), frame)

        thigh_x = _keyed(t, KEYS_THIGH)
        foot_x = _keyed(t, KEYS_FOOT)
        _set_bone(pbones, 'leftThigh_1', (thigh_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightThigh_1', (thigh_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'leftFoot_1', (foot_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightFoot_1', (foot_x, 0.0, 0.0), frame)

        _set_bone(pbones, 'tail1_1', (_keyed(t, KEYS_TAIL1), 0.0, 0.0), frame)
        _set_bone(pbones, 'tail2_1', (_keyed(t, KEYS_TAIL2), 0.0, 0.0), frame)

        ear_x = _keyed(t, KEYS_EAR)
        whisker_x = _keyed(t, KEYS_WHISKER)
        _set_bone(pbones, 'leftEar_1', (ear_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightEar_1', (ear_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'wisker1_1', (whisker_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'wisker2_1', (whisker_x, 0.0, 0.0), frame)

        hold_env = _keyed(t, KEYS_HOLD_ENV)
        nose_x = NOSE_AMP * max(0.0, math.sin(t * NOSE_CYCLES * 2 * math.pi)) * hold_env
        _set_bone(pbones, 'nose_1', (nose_x, 0.0, 0.0), frame)


execute_animation()
'''
    return code, frame_end


def generate_olfatear(slot_index, frame_start, points, today, root_rot):
    """La rata olfatea el entorno: agachada leve y constante, con
    rapidos 'dips' de cabeza/cuello siguiendo un ritmo de olfateo, y la
    cola con un balanceo lento independiente. Nariz y bigotes tiemblan
    al doble de frecuencia que la cabeza, orejas atentas."""
    fname = f"slot_{slot_index:03d}_rat_1_olfatear.py"
    n_frames = TOTAL_FRAMES_OLFATEAR
    frame_end = frame_start + n_frames - 1

    ang = _compute_direction_angle(points[0], points[-1])
    rot_z_fallback = ang if ang is not None else math.radians(root_rot[2])

    p0 = points[0]["coordinates"]
    p1 = points[-1]["coordinates"]

    code = f'''# -*- coding: utf-8 -*-
"""
{fname}
Rat 1 - Slot {slot_index}
Generado {today} por Rat 1 Animation Studio (Paso 2).

Olfatear: la rata olfatea el entorno con movimientos rapidos de
cabeza/cuello, nariz y bigotes. Root FIJO en P0, gira hacia P1. 100%
procedural (ciclo sinusoidal con envolvente de entrada/salida).
"""

import bpy
import math

SLOT_INDEX = {slot_index}
START_FRAME = {frame_start}
END_FRAME = {frame_end}
TOTAL_FRAMES = {n_frames}

ROOT_ROT_X = math.radians({root_rot[0]})
ROOT_ROT_Y = math.radians({root_rot[1]})
FALLBACK_ROT_Z = {rot_z_fallback:.6f}

P0 = ({p0["x"]:.5f}, {p0["y"]:.5f}, {p0["z"]:.5f})
P1 = ({p1["x"]:.5f}, {p1["y"]:.5f}, {p1["z"]:.5f})

ANIMATION_INFO = {{
    'name': '{fname}',
    'entity': 'rat_1',
    'slot': {slot_index},
    'movement_type': 'olfatear',
    'frame_count': {n_frames},
    'fps': 24,
}}

root = bpy.data.objects.get('rat_1')
arm  = bpy.data.objects.get('body1_1')
pbones = arm.pose.bones if arm else None

{_SHARED_HELPERS}

_TARGET_ANG_DEG = _compute_direction_angle_local(P0, P1)
_BASE_ANG_DEG = math.degrees(FALLBACK_ROT_Z)
if _TARGET_ANG_DEG is None:
    _TARGET_ANG_DEG = _BASE_ANG_DEG
_ROT_SMOOTHING_FRAMES = min(5, max(1, TOTAL_FRAMES - 1))


def calc_direction_for_frame(rf):
    if abs(_TARGET_ANG_DEG - _BASE_ANG_DEG) < 0.1:
        return math.radians(_TARGET_ANG_DEG)
    progress = min(rf / _ROT_SMOOTHING_FRAMES, 1.0)
    eased = progress * progress * (3.0 - 2.0 * progress)
    diff = _TARGET_ANG_DEG - _BASE_ANG_DEG
    while diff > 180: diff -= 360
    while diff < -180: diff += 360
    return math.radians(_BASE_ANG_DEG + diff * eased)


OLFATEAR_CYCLES = 4
OLFATEAR_HEAD_AMP = math.radians(22)
OLFATEAR_NECK_AMP = math.radians(14)
OLFATEAR_CROUCH = math.radians(-10)
OLFATEAR_ARM_CROUCH = math.radians(-8)
OLFATEAR_TAIL_SWAY = math.radians(6)
OLFATEAR_EAR_AMP = math.radians(15)
OLFATEAR_NOSE_AMP = math.radians(18)
OLFATEAR_WHISKER_AMP = math.radians(20)


def execute_animation():
    for frame in range(START_FRAME, END_FRAME + 1):
        rf = frame - START_FRAME
        t = rf / max(TOTAL_FRAMES - 1, 1)
        root_rz = calc_direction_for_frame(rf)
        _set_root(root, P0, (ROOT_ROT_X, ROOT_ROT_Y, root_rz), frame)

        env = _env(t)
        raw = math.sin(t * OLFATEAR_CYCLES * 2 * math.pi)
        dip = max(0.0, raw) ** 0.6
        raw2 = math.sin(t * OLFATEAR_CYCLES * 4 * math.pi)
        dip2 = max(0.0, raw2) ** 0.5

        _set_bone(pbones, 'body2_1', (OLFATEAR_CROUCH * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'body1_1', (0.0, 0.0, 0.0), frame)
        _set_bone(pbones, 'neck_1', (-OLFATEAR_NECK_AMP * dip * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'head_1', (-OLFATEAR_HEAD_AMP * dip * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'leftArm_1', (OLFATEAR_ARM_CROUCH * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightArm_1', (OLFATEAR_ARM_CROUCH * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'leftHand_1', (0.0, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightHand_1', (0.0, 0.0, 0.0), frame)
        _set_bone(pbones, 'leftThigh_1', (0.0, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightThigh_1', (0.0, 0.0, 0.0), frame)
        _set_bone(pbones, 'leftFoot_1', (0.0, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightFoot_1', (0.0, 0.0, 0.0), frame)

        tail_z = OLFATEAR_TAIL_SWAY * math.sin(t * 2 * math.pi) * env
        _set_bone(pbones, 'tail1_1', (0.0, 0.0, tail_z), frame)
        _set_bone(pbones, 'tail2_1', (0.0, 0.0, tail_z * 1.3), frame)

        _set_bone(pbones, 'leftEar_1', (OLFATEAR_EAR_AMP * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightEar_1', (OLFATEAR_EAR_AMP * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'nose_1', (OLFATEAR_NOSE_AMP * dip2 * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'wisker1_1', (OLFATEAR_WHISKER_AMP * dip2 * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'wisker2_1', (OLFATEAR_WHISKER_AMP * dip2 * env, 0.0, 0.0), frame)


execute_animation()
'''
    return code, frame_end


def generate_escarbar(slot_index, frame_start, points, today, root_rot):
    """La rata escarba el suelo con las patas delanteras, alternadas
    (fuera de fase), agachada mirando hacia abajo, patas traseras
    plantadas con leve contra-apoyo. Orejas hacia atras, hocico/nariz/
    bigotes tiemblan por el polvo, sincronizados con el escarbado."""
    fname = f"slot_{slot_index:03d}_rat_1_escarbar.py"
    n_frames = TOTAL_FRAMES_ESCARBAR
    frame_end = frame_start + n_frames - 1

    ang = _compute_direction_angle(points[0], points[-1])
    rot_z_fallback = ang if ang is not None else math.radians(root_rot[2])

    p0 = points[0]["coordinates"]
    p1 = points[-1]["coordinates"]

    code = f'''# -*- coding: utf-8 -*-
"""
{fname}
Rat 1 - Slot {slot_index}
Generado {today} por Rat 1 Animation Studio (Paso 2).

Escarbar: la rata escarba el suelo con las patas delanteras, alternadas.
Root FIJO en P0, gira hacia P1. 100% procedural (ciclos alternados con
envolvente de entrada/salida). Incluye orejas, hocico, nariz y bigotes.
"""

import bpy
import math

SLOT_INDEX = {slot_index}
START_FRAME = {frame_start}
END_FRAME = {frame_end}
TOTAL_FRAMES = {n_frames}

ROOT_ROT_X = math.radians({root_rot[0]})
ROOT_ROT_Y = math.radians({root_rot[1]})
FALLBACK_ROT_Z = {rot_z_fallback:.6f}

P0 = ({p0["x"]:.5f}, {p0["y"]:.5f}, {p0["z"]:.5f})
P1 = ({p1["x"]:.5f}, {p1["y"]:.5f}, {p1["z"]:.5f})

ANIMATION_INFO = {{
    'name': '{fname}',
    'entity': 'rat_1',
    'slot': {slot_index},
    'movement_type': 'escarbar',
    'frame_count': {n_frames},
    'fps': 24,
}}

root = bpy.data.objects.get('rat_1')
arm  = bpy.data.objects.get('body1_1')
pbones = arm.pose.bones if arm else None

{_SHARED_HELPERS}

_TARGET_ANG_DEG = _compute_direction_angle_local(P0, P1)
_BASE_ANG_DEG = math.degrees(FALLBACK_ROT_Z)
if _TARGET_ANG_DEG is None:
    _TARGET_ANG_DEG = _BASE_ANG_DEG
_ROT_SMOOTHING_FRAMES = min(5, max(1, TOTAL_FRAMES - 1))


def calc_direction_for_frame(rf):
    if abs(_TARGET_ANG_DEG - _BASE_ANG_DEG) < 0.1:
        return math.radians(_TARGET_ANG_DEG)
    progress = min(rf / _ROT_SMOOTHING_FRAMES, 1.0)
    eased = progress * progress * (3.0 - 2.0 * progress)
    diff = _TARGET_ANG_DEG - _BASE_ANG_DEG
    while diff > 180: diff -= 360
    while diff < -180: diff += 360
    return math.radians(_BASE_ANG_DEG + diff * eased)


ESCARBAR_CYCLES = 4
ESCARBAR_CROUCH = math.radians(-25)
ESCARBAR_HEAD_DOWN = math.radians(15)
ESCARBAR_NECK_DOWN = math.radians(10)
ESCARBAR_ARM_SWING = math.radians(40)
ESCARBAR_HAND_FLEX = math.radians(30)
ESCARBAR_THIGH_BRACE = math.radians(-6)
ESCARBAR_FOOT_BRACE = math.radians(4)
ESCARBAR_TAIL_SWAY = math.radians(5)
ESCARBAR_EAR_AMP = math.radians(-15)
ESCARBAR_SNOUT_AMP = math.radians(12)
ESCARBAR_NOSE_AMP = math.radians(14)
ESCARBAR_WHISKER_AMP = math.radians(16)


def execute_animation():
    for frame in range(START_FRAME, END_FRAME + 1):
        rf = frame - START_FRAME
        t = rf / max(TOTAL_FRAMES - 1, 1)
        root_rz = calc_direction_for_frame(rf)
        _set_root(root, P0, (ROOT_ROT_X, ROOT_ROT_Y, root_rz), frame)

        env = _env(t)
        phase_a = (t * ESCARBAR_CYCLES) % 1.0
        phase_b = (t * ESCARBAR_CYCLES + 0.5) % 1.0
        arm_r = ESCARBAR_ARM_SWING * math.sin(phase_a * 2 * math.pi) * env
        arm_l = ESCARBAR_ARM_SWING * math.sin(phase_b * 2 * math.pi) * env
        hand_r = ESCARBAR_HAND_FLEX * max(0.0, math.sin((phase_a - 0.75) * 2 * math.pi)) * env
        hand_l = ESCARBAR_HAND_FLEX * max(0.0, math.sin((phase_b - 0.75) * 2 * math.pi)) * env

        _set_bone(pbones, 'body2_1', (ESCARBAR_CROUCH * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'body1_1', (0.0, 0.0, 0.0), frame)
        _set_bone(pbones, 'neck_1', (ESCARBAR_NECK_DOWN * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'head_1', (ESCARBAR_HEAD_DOWN * env, 0.0, 0.0), frame)

        _set_bone(pbones, 'rightArm_1', (arm_r, 0.0, 0.0), frame)
        _set_bone(pbones, 'leftArm_1', (arm_l, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightHand_1', (hand_r, 0.0, 0.0), frame)
        _set_bone(pbones, 'leftHand_1', (hand_l, 0.0, 0.0), frame)

        _set_bone(pbones, 'leftThigh_1', (ESCARBAR_THIGH_BRACE * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightThigh_1', (ESCARBAR_THIGH_BRACE * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'leftFoot_1', (ESCARBAR_FOOT_BRACE * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightFoot_1', (ESCARBAR_FOOT_BRACE * env, 0.0, 0.0), frame)

        tail_z = ESCARBAR_TAIL_SWAY * math.sin(phase_a * 2 * math.pi) * env
        _set_bone(pbones, 'tail1_1', (0.0, 0.0, tail_z), frame)
        _set_bone(pbones, 'tail2_1', (0.0, 0.0, tail_z * 1.2), frame)

        _set_bone(pbones, 'leftEar_1', (ESCARBAR_EAR_AMP * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightEar_1', (ESCARBAR_EAR_AMP * env, 0.0, 0.0), frame)
        dust = max(0.0, math.sin(phase_a * 2 * math.pi)) ** 0.5
        _set_bone(pbones, 'snout_1', (ESCARBAR_SNOUT_AMP * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'nose_1', (ESCARBAR_NOSE_AMP * dust * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'wisker1_1', (ESCARBAR_WHISKER_AMP * dust * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'wisker2_1', (ESCARBAR_WHISKER_AMP * dust * env, 0.0, 0.0), frame)


execute_animation()
'''
    return code, frame_end


def generate_roer(slot_index, frame_start, points, today, root_rot):
    """La rata se sienta sobre las ancas y sostiene algo con ambas
    patas delanteras cerca del hocico, con un rapido cabeceo de
    masticado. Nariz y bigotes tiemblan al ritmo del masticado."""
    fname = f"slot_{slot_index:03d}_rat_1_roer.py"
    n_frames = TOTAL_FRAMES_ROER
    frame_end = frame_start + n_frames - 1

    ang = _compute_direction_angle(points[0], points[-1])
    rot_z_fallback = ang if ang is not None else math.radians(root_rot[2])

    p0 = points[0]["coordinates"]
    p1 = points[-1]["coordinates"]

    code = f'''# -*- coding: utf-8 -*-
"""
{fname}
Rat 1 - Slot {slot_index}
Generado {today} por Rat 1 Animation Studio (Paso 2).

Roer / morder: la rata se sienta sobre las ancas y sostiene algo con
ambas patas delanteras cerca del hocico, masticando. Root FIJO en P0,
gira hacia P1. 100% procedural (pose sostenida + cabeceo sinusoidal
rapido, mordisqueo veloz tipico de roedor).
"""

import bpy
import math

SLOT_INDEX = {slot_index}
START_FRAME = {frame_start}
END_FRAME = {frame_end}
TOTAL_FRAMES = {n_frames}

ROOT_ROT_X = math.radians({root_rot[0]})
ROOT_ROT_Y = math.radians({root_rot[1]})
FALLBACK_ROT_Z = {rot_z_fallback:.6f}

P0 = ({p0["x"]:.5f}, {p0["y"]:.5f}, {p0["z"]:.5f})
P1 = ({p1["x"]:.5f}, {p1["y"]:.5f}, {p1["z"]:.5f})

ANIMATION_INFO = {{
    'name': '{fname}',
    'entity': 'rat_1',
    'slot': {slot_index},
    'movement_type': 'roer',
    'frame_count': {n_frames},
    'fps': 24,
}}

root = bpy.data.objects.get('rat_1')
arm  = bpy.data.objects.get('body1_1')
pbones = arm.pose.bones if arm else None

{_SHARED_HELPERS}

_TARGET_ANG_DEG = _compute_direction_angle_local(P0, P1)
_BASE_ANG_DEG = math.degrees(FALLBACK_ROT_Z)
if _TARGET_ANG_DEG is None:
    _TARGET_ANG_DEG = _BASE_ANG_DEG
_ROT_SMOOTHING_FRAMES = min(5, max(1, TOTAL_FRAMES - 1))


def calc_direction_for_frame(rf):
    if abs(_TARGET_ANG_DEG - _BASE_ANG_DEG) < 0.1:
        return math.radians(_TARGET_ANG_DEG)
    progress = min(rf / _ROT_SMOOTHING_FRAMES, 1.0)
    eased = progress * progress * (3.0 - 2.0 * progress)
    diff = _TARGET_ANG_DEG - _BASE_ANG_DEG
    while diff > 180: diff -= 360
    while diff < -180: diff += 360
    return math.radians(_BASE_ANG_DEG + diff * eased)


ROER_CYCLES = 8
ROER_SPINE_SIT = math.radians(-35)
ROER_THIGH_SIT = math.radians(-20)
ROER_FOOT_SIT = math.radians(14)
ROER_ARM_HOLD = math.radians(85)
ROER_HAND_HOLD = math.radians(-45)
ROER_HEAD_CHEW_AMP = math.radians(8)
ROER_NECK_CHEW_AMP = math.radians(4)
ROER_TAIL_SETTLE = math.radians(6)
ROER_EAR_AMP = math.radians(12)
ROER_NOSE_AMP = math.radians(16)
ROER_WHISKER_AMP = math.radians(18)


def execute_animation():
    for frame in range(START_FRAME, END_FRAME + 1):
        rf = frame - START_FRAME
        t = rf / max(TOTAL_FRAMES - 1, 1)
        root_rz = calc_direction_for_frame(rf)
        _set_root(root, P0, (ROOT_ROT_X, ROOT_ROT_Y, root_rz), frame)

        env = _env(t)
        chew = math.sin(t * ROER_CYCLES * 2 * math.pi)

        _set_bone(pbones, 'body2_1', (ROER_SPINE_SIT * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'body1_1', (0.0, 0.0, 0.0), frame)
        _set_bone(pbones, 'neck_1', (ROER_NECK_CHEW_AMP * chew * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'head_1', (ROER_HEAD_CHEW_AMP * chew * env, 0.0, 0.0), frame)

        arm_x = ROER_ARM_HOLD * env
        hand_x = ROER_HAND_HOLD * env
        _set_bone(pbones, 'leftArm_1', (arm_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightArm_1', (arm_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'leftHand_1', (hand_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightHand_1', (hand_x, 0.0, 0.0), frame)

        thigh_x = ROER_THIGH_SIT * env
        foot_x = ROER_FOOT_SIT * env
        _set_bone(pbones, 'leftThigh_1', (thigh_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightThigh_1', (thigh_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'leftFoot_1', (foot_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightFoot_1', (foot_x, 0.0, 0.0), frame)

        tail_x = ROER_TAIL_SETTLE * env
        _set_bone(pbones, 'tail1_1', (tail_x, 0.0, 0.0), frame)
        _set_bone(pbones, 'tail2_1', (tail_x * 1.2, 0.0, 0.0), frame)

        _set_bone(pbones, 'leftEar_1', (ROER_EAR_AMP * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'rightEar_1', (ROER_EAR_AMP * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'nose_1', (ROER_NOSE_AMP * chew * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'wisker1_1', (ROER_WHISKER_AMP * chew * env, 0.0, 0.0), frame)
        _set_bone(pbones, 'wisker2_1', (ROER_WHISKER_AMP * chew * env, 0.0, 0.0), frame)


execute_animation()
'''
    return code, frame_end
