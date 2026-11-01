
from .blender_compat import get_fcurves as _get_action_fcurves, new_fcurve as _new_fcurve

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_slots_jerry.py
=======================
Generador automatico de slots de animacion para Jerry (perro cuadrupedo).

ESTRUCTURA DE CARPETAS:
    carpeta_jerry/
        generate_slots_jerry.py
        ejecutar_jerry.bat
        archivo_json/
            recorrido_jerry.json

TIPOS DE SLOT:
    - saltar_subir  : 15 frames  - Z sube entre dos puntos  (DogJumpCycle)
    - caminar       : 140 frames  - Z constante N puntos     (SniffingSearchCycle)
    - saltar_bajar  : 24 frames  - Z baja entre dos puntos  (QuadrupedWalkPlainCycle)

PERSONAJE:
    - Root  : Empty llamado 'jerry'
    - Bones : sin sufijo especial
    - Ojos  : ojo_izquierdo_jerry / ojo_derecho_jerry

SISTEMA DE PARPADEO:
    - Los 3 tipos de slot incluyen setup_blink_shape_keys() + _create_curtain_effect()
    - saltar_subir (15f) : 1 parpadeo al 50% del slot
    - saltar_bajar (24f) : 1 parpadeo al 50% del slot
    - caminar     (140f) : 2 parpadeos al 25% y 75% del slot
    - BLINK_SEQUENCE de 9 frames (0.375s) con hide_viewport en el pico
"""

import json
import os
import sys
from datetime import date

# ============================================================
# DETECCION DE SEGMENTOS
# ============================================================


import importlib.util as _jump_import
from pathlib import Path as _JumpPath
_jump_spec = _jump_import.spec_from_file_location(__name__ + '_jump_motion', _JumpPath(__file__).with_name('jump_motion.py'))
_adaptive_jump = _jump_import.module_from_spec(_jump_spec)
_jump_spec.loader.exec_module(_adaptive_jump)
jump_frame_count = _adaptive_jump.jump_frame_count

def detect_movement_type(p_current, p_next):
    if p_current.get('tipo_segmento','AUTO') == 'SALTAR':
        z0,z1=round(p_current['coordinates']['z'],2),round(p_next['coordinates']['z'],2)
        return 'saltar_subir' if z1>z0 else 'saltar_bajar' if z1<z0 else 'saltar_horizontal'
    # FIX (Kebyn, 2026-09-24): dos puntos IDENTICOS (x/y/z a 4 decimales) =
    # "parada" -- el mismo criterio que _detect_move() en path_recorder.py y
    # que el docstring de generate_parada() ya daba por hecho. Sin esto,
    # el punto duplicado que _expand_points_with_paradas() inserta detras
    # de una Parada/Observar se exportaba como un 'caminar' de largo cero y
    # generate_parada() nunca se llamaba desde Exportar recorrido.
    _ca, _cb = p_current['coordinates'], p_next['coordinates']
    if (round(_ca['x'], 4) == round(_cb['x'], 4)
            and round(_ca['y'], 4) == round(_cb['y'], 4)
            and round(_ca['z'], 4) == round(_cb['z'], 4)):
        return 'parada'
    # FIX (portado de Alfred, Kebyn, 2026-08-19): redondeo a 4 decimales
    # antes de comparar -- mismo criterio que _detect_move() en
    # path_recorder.py, para que las 3 detecciones (interfaz, estimacion
    # de frames, generacion real) coincidan siempre entre si.
    z0 = round(p_current['coordinates']['z'], 4)
    z1 = round(p_next['coordinates']['z'], 4)
    if z1 > z0:
        return 'saltar_subir'
    elif z1 < z0:
        return 'saltar_bajar'
    else:
        return 'caminar'

def group_segments(key_points):
    """Agrupa key_points en segmentos por tipo de movimiento."""
    segments = []
    i = 0
    while i < len(key_points) - 1:
        p0 = key_points[i]
        p1 = key_points[i + 1]
        move = detect_movement_type(p0, p1)

        if move == 'caminar':
            group = [p0]
            while i < len(key_points) - 1:
                nxt = key_points[i + 1]
                if detect_movement_type(key_points[i], nxt) == 'caminar':
                    group.append(nxt)
                    i += 1
                else:
                    break
            segments.append({'type': 'caminar', 'points': group})
        else:
            segments.append({'type': move, 'points': [p0, p1]})
            i += 1
    return segments

# ============================================================
# HELPERS DE DIRECCION
# ============================================================

def _compute_direction_angle(p0, p1):
    import math as _m
    dx = p1['x'] - p0['x']
    dy = p1['y'] - p0['y']
    if dx == 0 and dy == 0:
        return None
    ang_raw = _m.degrees(_m.atan2(dx, dy))
    ang_rounded = round(ang_raw / 90.0) * 90.0
    ang_diff = abs(ang_raw - ang_rounded)
    ang = ang_rounded if ang_diff < 45 else -ang_raw
    while ang >  180: ang -= 360
    while ang < -180: ang += 360
    if   ang ==  90: ang = -90
    elif ang == -90: ang =  90
    elif ang == 180: ang = -180
    return ang

def _smoothstep_val(x):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    return x * x * (3.0 - 2.0 * x)

def _angle_diff_shortest(target, current):
    d = target - current
    if d > 180:
        d -= 360
    elif d < -180:
        d += 360
    return d

def _fmt_trajectory(points):
    lines = ["EMBEDDED_TRAJECTORY_POINTS = ["]
    for p in points:
        c = p['coordinates']
        lines.append(f'    {{"index": {p["index"]}, '
                     f'"coordinates": {{"x": {c["x"]}, "y": {c["y"]}, "z": {c["z"]}}}, '
                     f'"texture": "{p.get("texture","grass_block_top")}"}},'  )
    lines.append("]")
    return "\n".join(lines)

# ============================================================
# BLOQUES DE CODIGO COMUN (embebidos en cada slot generado)
# ============================================================

COMMON_MATH = '''
def sin_wave(frame, period, amplitude, phase=0, offset=0):
    return amplitude * math.sin(2 * math.pi * frame / period + phase) + offset

def cos_wave(frame, period, amplitude, phase=0, offset=0):
    return amplitude * math.cos(2 * math.pi * frame / period + phase) + offset

def lerp(start, end, t):
    return start + (end - start) * t

def ease_in_out(t):
    return t * t * (3 - 2 * t)

def ease_out(t):
    return 1 - (1 - t) * (1 - t)

def ease_in(t):
    return t * t
'''

DIRECTION_HELPERS = '''
def _compute_direction_angle(p0, p1):
    dx = p1['x'] - p0['x']
    dy = p1['y'] - p0['y']
    if dx == 0 and dy == 0:
        return None
    ang_raw = math.degrees(math.atan2(dx, dy))
    ang_rounded = round(ang_raw / 90.0) * 90.0
    ang = ang_rounded if abs(ang_raw - ang_rounded) < 45 else -ang_raw
    while ang >  180: ang -= 360
    while ang < -180: ang += 360
    if   ang ==  90: ang = -90
    elif ang == -90: ang =  90
    elif ang == 180: ang = -180
    return ang

def _smoothstep_val(x):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    return x * x * (3.0 - 2.0 * x)

def _angle_diff_shortest(target, current):
    d = target - current
    while d >  180: d -= 360
    while d < -180: d += 360
    return d
'''

ROTATION_SMOOTHER_CLASS = '''
class RotationSmoother:
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
        if abs(angle_diff) < 2:
            self.previous_rotation = target_rotation
            self.transition_start_frame = None
            return target_rotation
        if self.transition_start_frame is None:
            self.transition_start_frame = current_frame
            self.transition_start_rotation = self.previous_rotation
            self.target_rotation = target_rotation
        elapsed  = current_frame - self.transition_start_frame
        progress = min(elapsed / self.smoothing_frames, 1.0)
        eased    = self._smoothstep(progress)
        smoothed = self.transition_start_rotation + self._diff(self.target_rotation, self.transition_start_rotation) * eased
        if progress >= 1.0:
            self.previous_rotation = target_rotation
            self.transition_start_frame = None
            return target_rotation
        return smoothed

    def _normalize(self, a):
        while a >  180: a -= 360
        while a < -180: a += 360
        return a

    def _diff(self, target, current):
        d = target - current
        while d >  180: d -= 360
        while d < -180: d += 360
        return d

    def _smoothstep(self, x):
        if x <= 0: return 0.0
        if x >= 1: return 1.0
        return x * x * (3.0 - 2.0 * x)
'''

# Bloque de parpadeo completo con setup de shape keys
# Se inyecta en los 3 tipos de slot
BLINK_SYSTEM_BLOCK = '''
# ============================================================
# SISTEMA DE PARPADEO
# ============================================================

BLINK_SEQUENCE = {
    1: {"closed": 0.0,  "hide": False},
    2: {"closed": 0.25, "hide": False},
    3: {"closed": 0.5,  "hide": False},
    4: {"closed": 0.75, "hide": False},
    5: {"closed": 1.0,  "hide": True},
    6: {"closed": 1.0,  "hide": True},
    7: {"closed": 0.75, "hide": False},
    8: {"closed": 0.5,  "hide": False},
    9: {"closed": 0.25, "hide": False},
}

EYE_NAMES = ["ojo_izquierdo_jerry", "ojo_derecho_jerry"]


def _create_curtain_effect(eye_obj, shape_key):
    """Deforma la shape key bajando todos los vertices al minimo Z (efecto parpado)."""
    mesh    = eye_obj.data
    min_z   = min(v.co.z for v in mesh.vertices)
    for i, vert in enumerate(mesh.vertices):
        new_co     = vert.co.copy()
        new_co.z   = min_z
        shape_key.data[i].co = new_co


def setup_blink_shape_keys():
    """Crea Basis + Closed en los ojos si no existen. Seguro llamar multiples veces."""
    import bpy
    for obj_name in EYE_NAMES:
        eye_obj = bpy.data.objects.get(obj_name)
        if not eye_obj or eye_obj.type != "MESH":
            print(f"   setup_blink: WARNING '{obj_name}' no encontrado o no es MESH")
            continue
        if not eye_obj.data.shape_keys:
            eye_obj.shape_key_add(name="Basis", from_mix=False)
            print(f"   setup_blink: Basis creado en '{obj_name}'")
        existing = [sk.name for sk in eye_obj.data.shape_keys.key_blocks]
        if "Closed" not in existing:
            closed_key = eye_obj.shape_key_add(name="Closed", from_mix=False)
            _create_curtain_effect(eye_obj, closed_key)
            print(f"   setup_blink: Shape key 'Closed' creada en '{obj_name}'")
        else:
            print(f"   setup_blink: 'Closed' ya existe en '{obj_name}' -- OK")
'''

# ============================================================
# GENERADOR: SALTAR SUBIR  (15 frames, DogJumpCycle)
# ============================================================

# Fuente unica de verdad de la duracion de saltar_subir/saltar_bajar,
# usada tanto por los generadores de abajo como por el panel de
# estimacion de slots (panels.py) para que ambos numeros nunca se
# desincronicen (Kebyn, 2026-08-24 - fix estimacion de frames).
SALTAR_SUBIR_FRAMES = 15
SALTAR_BAJAR_FRAMES = 24


def generate_saltar_subir(slot_index, start_frame, points, today, prev_rz, root_rot=(0, 0, -90), fps=24.0):
    return _adaptive_jump.generate_jump(slot_index,start_frame,points,root_rot,'subir',fps,None)

# ============================================================
# GENERADOR: IDLE  (personaje parado, 1 coordenada)
# ============================================================

# Template del slot idle — usa .format() para evitar conflictos con f-strings anidados
_IDLE_TEMPLATE = """# -*- coding: utf-8 -*-
import bpy, math
from mathutils import Quaternion

SLOT_INDEX   = __SLOT__
START_FRAME  = __SF__
END_FRAME    = __EF__
TOTAL_FRAMES = __TF__
ROOT_ROTATION_X = __RX__
ROOT_ROTATION_Y = __RY__
ROOT_ROTATION_Z = __RZ__

KEYPOINT = {"index": __PI__, "coordinates": {"x": __PX__, "y": __PY__, "z": __PZ__}, "texture": "__TEX__"}

IDLE_POSE = {
    "spine_6":          (1.0,      0.0,       0.0,       0.0     ),
    "shoulder.R":       (1.0,      0.0,       0.0,       0.0     ),
    "thigh.R":          (0.998338,-0.025782,  0.042195,  0.029608),
    "shin.R":           (0.994427, 0.015862,  0.082995, -0.063043),
    "foot.R":           (0.996655, 0.081519, -0.005796, -0.000377),
    "toe.R":            (0.999005,-0.040315,  0.017105,  0.008429),
    "spine_7":          (1.0,      0.0,       0.0,       0.0     ),
    "tail_1":           (1.0,      0.0,       0.0,       0.0     ),
    "tail_2":           (1.0,      0.0,       0.0,       0.0     ),
    "tail_3":           (1.0,      0.0,       0.0,       0.0     ),
    "spine_5":          (1.0,      0.0,       0.0,       0.0     ),
    "spine_4":          (1.0,      0.0,       0.0,       0.0     ),
    "spine_3":          (1.0,      0.0,       0.0,       0.0     ),
    "spine_2":          (1.0,      0.0,       0.0,       0.0     ),
    "spine_1":          (1.0,      0.0,       0.0,       0.0     ),
    "scull_1":          (1.0,      0.0,       0.0,       0.0     ),
    "scull":            (0.999945, 0.010519,  0.0,       0.0     ),
    "ear.R":            (1.0,      0.0,       0.0,       0.0     ),
    "ear.L":            (0.999945, 0.002396,  0.009347,  0.004159),
    "jaw_top":          (0.999955,-0.009430,  0.0,       0.0     ),
    "jaw_bot":          (1.0,      0.0,       0.0,       0.0     ),
    "sombrero":         (1.0,      0.0,       0.0,       0.0     ),
    "front_shoulder.R": (1.0,      0.0,       0.0,       0.0     ),
    "front_thigh.R":    (0.999326, 0.000806, -0.019173,  0.031282),
    "front_shin.R":     (0.999651,-0.026395, -0.001057, -0.000234),
    "front_foot.R":     (0.997441, 0.045186,  0.018651, -0.052181),
    "front_toe.R":      (1.0,      0.0,       0.0,       0.0     ),
    "front_shoulder.L": (1.0,      0.0,       0.0,       0.0     ),
    "front_thigh.L":    (0.999276, 0.006675,  0.019077, -0.032223),
    "front_shin.L":     (0.989825,-0.018532,  0.141046, -0.003009),
    "front_foot.L":     (0.999560, 0.022467, -0.018879, -0.004336),
    "front_toe.L":      (0.990863, 0.003916, -0.008821,  0.134525),
    "shoulder.L":       (1.0,      0.0,       0.0,       0.0     ),
    "thigh.L":          (1.0,      0.0,       0.0,       0.0     ),
    "shin.L":           (0.998899,-0.039855,  0.001751,  0.024680),
    "foot.L":           (1.0,      0.0,       0.0,       0.0     ),
    "toe.L":            (0.967064, 0.102424, -0.212854,  0.094812),
}
__COMMON_MATH__
__BLINK_BLOCK__

def run():
    arm_obj  = bpy.data.objects.get("Dog_001_rig")
    root_obj = bpy.data.objects.get("jerry")
    if arm_obj is None:
        print("[idle] ERROR: Dog_001_rig no encontrado"); return
    if root_obj is None:
        print("[idle] ERROR: jerry no encontrado"); return
    bpy.context.view_layer.objects.active = arm_obj
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    arm_obj.select_set(True)
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    root_obj.location = (__PX__, __PY__, __PZ__)
    root_obj.rotation_euler = (
        math.radians(ROOT_ROTATION_X),
        math.radians(ROOT_ROTATION_Y),
        math.radians(ROOT_ROTATION_Z),
    )
    root_obj.keyframe_insert(data_path='location',       frame=START_FRAME)
    root_obj.keyframe_insert(data_path='rotation_euler', frame=START_FRAME)
    root_obj.keyframe_insert(data_path='location',       frame=END_FRAME)
    root_obj.keyframe_insert(data_path='rotation_euler', frame=END_FRAME)
    step = 6
    applied = 0
    for frame in range(START_FRAME, END_FRAME + 1, step):
        bpy.context.scene.frame_set(frame)
        for bname, (qw, qx, qy, qz) in IDLE_POSE.items():
            b = pb.get(bname)
            if b is None: continue
            b.rotation_mode = "XYZ"
            b.rotation_euler = Quaternion((qw, qx, qy, qz)).to_euler("XYZ")
            b.keyframe_insert(data_path='rotation_euler', frame=frame)
            if frame == START_FRAME: applied += 1
    if (END_FRAME - START_FRAME) % step != 0:
        bpy.context.scene.frame_set(END_FRAME)
        for bname, (qw, qx, qy, qz) in IDLE_POSE.items():
            b = pb.get(bname)
            if b is None: continue
            b.rotation_mode = "XYZ"
            b.rotation_euler = Quaternion((qw, qx, qy, qz)).to_euler("XYZ")
            b.keyframe_insert(data_path='rotation_euler', frame=END_FRAME)
    bpy.ops.object.mode_set(mode="OBJECT")
    setup_blink_shape_keys()
    print("Slot __SLOT__ idle: " + str(applied) + " bones, __TF__ frames OK")

run()
"""


def generate_idle(slot_index, start_frame, point, today, root_rot=(0, 0, -90), total_frames=24):
    """Genera un slot Python con la pose estatica parado de Jerry."""
    end_frame  = start_frame + total_frames - 1
    rx, ry, rz = root_rot
    px  = point['coordinates']['x']
    py  = point['coordinates']['y']
    pz  = point['coordinates']['z']
    tex = point.get('texture', 'grass_block_top')
    pi  = point['index']

    code = (
        _IDLE_TEMPLATE
        .replace("__SLOT__",        str(slot_index))
        .replace("__SF__",          str(start_frame))
        .replace("__EF__",          str(end_frame))
        .replace("__TF__",          str(total_frames))
        .replace("__RX__",          str(rx))
        .replace("__RY__",          str(ry))
        .replace("__RZ__",          str(rz))
        .replace("__PI__",          str(pi))
        .replace("__PX__",          str(px))
        .replace("__PY__",          str(py))
        .replace("__PZ__",          str(pz))
        .replace("__TEX__",         str(tex))
        .replace("__COMMON_MATH__", COMMON_MATH)
        .replace("__BLINK_BLOCK__", BLINK_SYSTEM_BLOCK)
    )
    return code, end_frame


# ============================================================
# GENERADOR: PARADA  (root inmovil, canvas limpio para poses de segmento)
# ============================================================
#
# Portado de Alfred (generate_parada), 2026-08-05: el root se detiene por
# completo en una coordenada elegida por el usuario (dropdown "Tipo" en
# la lista del Paso 1, ver JRRSTPathPoint.tipo_segmento), para dejar un
# hueco donde tenga sentido animar una accion puntual via el sistema de
# poses del Paso 3, en vez de forzarla sobre una caminata en curso.
#
# A diferencia de saltar_subir/saltar_bajar/caminar, una parada NO anima
# ningun ciclo de bones -- fuerza todos los bones de IDLE_POSE (misma
# pose de rest "parado" que usa generate_idle(), ver parado.json /
# Dog_001_rig) durante todo el rango, para que el canvas quede limpio y
# el Paso 3 tenga donde superponer su propia animacion.
FRAMES_PARADA_DEFAULT = 60


# ============================================================
# ANIMACION IMPORTADA (.py) PARA PUNTOS DE "PARADA" -- portado de
# alfred_animation_studio (Kebyn, 2026-09-14)
# ============================================================
# NUEVO: en el Paso 1 (Path Recorder / panels.py), un punto marcado como
# "Parada" ahora puede tener asociado un archivo .py de animacion
# importada (ver JRRSTPathPoint.parada_anim_file en path_recorder.py),
# tipicamente exportado por el conversor de Mixamo/pose-capture de
# Kebyn -- un modulo con un diccionario module-level KEYFRAME_DATA de
# bone -> {frame: (rx, ry, rz)}. Estas funciones cargan ese archivo en
# tiempo de GENERACION (dentro de Blender, no en el .py exportado) y
# arman el bloque de codigo que generate_parada() embebe en el slot
# generado. Rig-agnostico: itera los nombres de bone tal cual vienen en
# el KEYFRAME_DATA del archivo, sin asumir nomenclatura Mixamo/Rigify --
# funciona igual para Jerry (Dog_001_rig) que para Alfred.

def _fmt_keyframes(kf_dict, start_frame):
    """Convierte keyframes relativos (0-based) a frames absolutos y los
    formatea como codigo Python. Portado tal cual de generate_slots_alfred.py."""
    lines = []
    lines.append("KEYFRAME_DATA = {")
    for bone, frames in kf_dict.items():
        lines.append(f"    '{bone}': {{")
        for rel_frame, rot in frames.items():
            abs_frame = start_frame + rel_frame
            lines.append(f"        {abs_frame}: ({rot[0]:.6f}, {rot[1]:.6f}, {rot[2]:.6f}),")
        lines.append("    },")
    lines.append("}")
    return "\n".join(lines)


def _load_keyframe_data_from_anim_file(filepath):
    """Carga KEYFRAME_DATA desde un script .py de animacion importada.
    Portado tal cual de generate_slots_alfred.py -- ver docstring
    original ahi para el detalle completo. Devuelve
    (keyframe_data_0based, frame_count), o (None, None) si el archivo no
    existe, no se pudo ejecutar, o no define KEYFRAME_DATA (fallback
    silencioso -- generate_parada() vuelve entonces a la pose estatica
    'parado'/IDLE_POSE de siempre)."""
    import os as _os_mod
    import importlib.util as _ilu_mod

    if not filepath or not _os_mod.path.isfile(filepath):
        print(f"generate_parada: archivo de animacion importada no encontrado: {filepath}")
        return None, None

    try:
        _spec = _ilu_mod.spec_from_file_location("_jerry_parada_anim_importada", filepath)
        _mod = _ilu_mod.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
    except Exception as e:
        print(f"generate_parada: no se pudo ejecutar el archivo de animacion importada '{filepath}': {e}")
        return None, None

    raw_kf = getattr(_mod, "KEYFRAME_DATA", None)
    if not raw_kf:
        print(f"generate_parada: '{filepath}' no define KEYFRAME_DATA -- se ignora")
        return None, None

    all_frames = [f for bone_kf in raw_kf.values() for f in bone_kf.keys()]
    if not all_frames:
        return None, None

    src_min = min(all_frames)
    src_max = max(all_frames)
    normalized = {
        bone: {f - src_min: rot for f, rot in bone_kf.items()}
        for bone, bone_kf in raw_kf.items()
    }
    frame_count = src_max - src_min + 1
    return normalized, frame_count


def _build_parada_anim_importada_block_jerry(anim_kf_data, start_frame, slot_index, anim_src_label):
    """Bloque de codigo (texto ya formateado) que aplica una animacion
    .py IMPORTADA durante esta parada, en vez del reset a IDLE_POSE.
    Portado de _build_parada_anim_importada_block (generate_slots_alfred.py).
    `anim_kf_data` ya viene normalizado a 0-based (ver
    _load_keyframe_data_from_anim_file). El root sigue inmovil (sin
    cambios) -- solo el cuerpo reproduce el clip importado."""
    kf_code = _fmt_keyframes(anim_kf_data, start_frame)
    label_literal = repr(anim_src_label)
    return f'''{kf_code}

    bones_applied = 0
    for _bone_name, _bone_kf in KEYFRAME_DATA.items():
        _bone = armature.pose.bones.get(_bone_name)
        if _bone is None:
            continue
        _bone.rotation_mode = 'XYZ'
        for _frame, _rot in _bone_kf.items():
            _bone.rotation_euler = _rot
            _bone.keyframe_insert(data_path="rotation_euler", frame=_frame)
        bones_applied += 1

    if armature.animation_data.action:
        _arm_action_obj = armature.animation_data.action
        _fcurves_list = (
            _arm_action_obj.fcurves if hasattr(_arm_action_obj, 'fcurves')
            else [fc for _slot in getattr(_arm_action_obj, 'slots', [])
                  for fc in getattr(_slot, 'fcurves', [])]
        )
        for fcurve in _fcurves_list:
            for kp in fcurve.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.easing = 'AUTO'

    print("   " + str(bones_applied) + " bones animados con animacion importada: " + {label_literal})'''


# FIX (Kebyn, 2026-09-24): las plantillas de parada llamaban a
# `_get_action_fcurves(action)` DENTRO del script exportado, pero esa funcion
# solo existe en los modulos del addon (blender_compat.get_fcurves) -- el slot
# generado la usaba sin definirla y `action` tampoco existia, asi que toda
# parada exportada terminaba en NameError. Este bloque se pega en el script
# generado para que sea autonomo (Blender < 5.0: Action.fcurves; 5.0+: via
# slot/channelbag).
FCURVES_COMPAT_BLOCK = '''
def _get_action_fcurves(act):
    if act is None:
        return []
    if hasattr(act, 'fcurves'):
        return act.fcurves
    try:
        from bpy_extras import anim_utils as _anim_utils
        _out = []
        for _slot in getattr(act, 'slots', []):
            _cb = _anim_utils.action_get_channelbag_for_slot(act, _slot)
            if _cb is not None:
                _out.extend(_cb.fcurves)
        return _out
    except Exception:
        return []
'''


def _load_observar_motion():
    try:
        from . import observar_motion as _om
        return _om
    except ImportError:
        import importlib.util as _ilu
        from pathlib import Path as _P
        _sp = _ilu.spec_from_file_location(__name__ + '_observar_motion',
                                           _P(__file__).with_name('observar_motion.py'))
        _om = _ilu.module_from_spec(_sp)
        _sp.loader.exec_module(_om)
        return _om


def _fmt_location_keyframes(loc_kf, start_frame):
    """Igual que _fmt_keyframes() pero para location de huesos."""
    lines = ["LOCATION_DATA = {"]
    for bone, frames in loc_kf.items():
        lines.append(f"    '{bone}': {{")
        for rel_frame, v in frames.items():
            lines.append(f"        {start_frame + rel_frame}: ({v[0]:.6f}, {v[1]:.6f}, {v[2]:.6f}),")
        lines.append("    },")
    lines.append("}")
    return "\n".join(lines)


def _build_observar_block_jerry(rot_kf, loc_kf, start_frame):
    """Bloque de codigo (texto) que aplica la animacion 'Observar' (sentado
    + giro de cabeza) al armature: rotacion de todos los huesos y location de
    los pocos que la pose sentada desplaza (pelvis, etc.)."""
    return f'''{_fmt_keyframes(rot_kf, start_frame)}

    {_fmt_location_keyframes(loc_kf, start_frame)}

    bones_applied = 0
    for _bone_name, _bone_kf in KEYFRAME_DATA.items():
        _bone = armature.pose.bones.get(_bone_name)
        if _bone is None:
            continue
        _bone.rotation_mode = 'XYZ'
        for _frame, _rot in _bone_kf.items():
            _bone.rotation_euler = _rot
            _bone.keyframe_insert(data_path="rotation_euler", frame=_frame)
        bones_applied += 1
    for _bone_name, _bone_kf in LOCATION_DATA.items():
        _bone = armature.pose.bones.get(_bone_name)
        if _bone is None:
            continue
        for _frame, _loc in _bone_kf.items():
            _bone.location = _loc
            _bone.keyframe_insert(data_path="location", frame=_frame)

    for fcurve in _get_action_fcurves(armature.animation_data.action):
        for kp in fcurve.keyframe_points:
            kp.interpolation = 'BEZIER'
            kp.easing = 'AUTO'

    print("   " + str(bones_applied) + " bones animados: sentado + giro de cabeza + respiracion/cola/orejas (Observar)")'''


# BUG PREEXISTENTE encontrado y corregido (Kebyn, 2026-09-14, al portar el
# sistema de animacion importada): generate_parada() de mas abajo hacia
# `IDLE_POSE = {IDLE_POSE!r}` dentro de su plantilla, pero `IDLE_POSE`
# JAMAS estuvo definido como variable real en este archivo -- el unico
# "IDLE_POSE = {...}" que existe aca es puro TEXTO dentro del string
# _IDLE_TEMPLATE (otro generador, no una variable de modulo). Cualquier
# "parada" exportada por JRRSTPR_OT_ExportSlots (Paso 3) tronaba con
# `NameError: name 'IDLE_POSE' is not defined` apenas se llamaba a
# gen.generate_parada(). Fix: mismo dict real que ya usa
# IDLE_POSE_PARADA en path_recorder.py (pose de rest "parado" del rig
# Dog_001_rig) definido aca tambien como constante real.
IDLE_POSE_PARADA_DEFAULT = {
    "spine_6":          (1.0,      0.0,       0.0,       0.0     ),
    "shoulder.R":       (1.0,      0.0,       0.0,       0.0     ),
    "thigh.R":          (0.998338,-0.025782,  0.042195,  0.029608),
    "shin.R":           (0.994427, 0.015862,  0.082995, -0.063043),
    "foot.R":           (0.996655, 0.081519, -0.005796, -0.000377),
    "toe.R":            (0.999005,-0.040315,  0.017105,  0.008429),
    "spine_7":          (1.0,      0.0,       0.0,       0.0     ),
    "tail_1":           (1.0,      0.0,       0.0,       0.0     ),
    "tail_2":           (1.0,      0.0,       0.0,       0.0     ),
    "tail_3":           (1.0,      0.0,       0.0,       0.0     ),
    "spine_5":          (1.0,      0.0,       0.0,       0.0     ),
    "spine_4":          (1.0,      0.0,       0.0,       0.0     ),
    "spine_3":          (1.0,      0.0,       0.0,       0.0     ),
    "spine_2":          (1.0,      0.0,       0.0,       0.0     ),
    "spine_1":          (1.0,      0.0,       0.0,       0.0     ),
    "scull_1":          (1.0,      0.0,       0.0,       0.0     ),
    "scull":            (0.999945, 0.010519,  0.0,       0.0     ),
    "ear.R":            (1.0,      0.0,       0.0,       0.0     ),
    "ear.L":            (0.999945, 0.002396,  0.009347,  0.004159),
    "jaw_top":          (0.999955,-0.009430,  0.0,       0.0     ),
    "jaw_bot":          (1.0,      0.0,       0.0,       0.0     ),
    "sombrero":         (1.0,      0.0,       0.0,       0.0     ),
    "front_shoulder.R": (1.0,      0.0,       0.0,       0.0     ),
    "front_thigh.R":    (0.999326, 0.000806, -0.019173,  0.031282),
    "front_shin.R":     (0.999651,-0.026395, -0.001057, -0.000234),
    "front_foot.R":     (0.997441, 0.045186,  0.018651, -0.052181),
    "front_toe.R":      (1.0,      0.0,       0.0,       0.0     ),
    "front_shoulder.L": (1.0,      0.0,       0.0,       0.0     ),
    "front_thigh.L":    (0.999276, 0.006675,  0.019077, -0.032223),
    "front_shin.L":     (0.989825,-0.018532,  0.141046, -0.003009),
    "front_foot.L":     (0.999560, 0.022467, -0.018879, -0.004336),
    "front_toe.L":      (0.990863, 0.003916, -0.008821,  0.134525),
    "shoulder.L":       (1.0,      0.0,       0.0,       0.0     ),
    "thigh.L":          (1.0,      0.0,       0.0,       0.0     ),
    "shin.L":           (0.998899,-0.039855,  0.001751,  0.024680),
    "foot.L":           (1.0,      0.0,       0.0,       0.0     ),
    "toe.L":            (0.967064, 0.102424, -0.212854,  0.094812),
}


def generate_parada(slot_index, start_frame, points, today, root_rot=(0, 0, -90), frames_parada=None,
                     anim_file_path=None, observar=False):
    """Genera un slot de 'parada': root inmovil `frames_parada` frames, con
    los bones forzados a la pose de rest "parado" (IDLE_POSE) -- canvas
    limpio para la pose que superponga el Paso 3.

    `frames_parada`: sin limite -- cualquier entero >= 1. Si no se pasa
    (None), usa FRAMES_PARADA_DEFAULT como fallback.

    `anim_file_path`: NUEVO (Kebyn, 2026-09-14, portado de Alfred) --
    ruta a un script .py de animacion importada (modulo con un
    diccionario KEYFRAME_DATA de bone -> {frame: (rx, ry, rz)}). Si se
    pasa y el archivo es valido, esta parada reproduce esa animacion
    completa en vez del reset a IDLE_POSE de siempre -- el root sigue
    inmovil (sigue siendo una 'parada': no camina), pero el cuerpo
    reproduce el clip importado. La duracion de este slot pasa a ser la
    del clip importado (se ignora `frames_parada` en ese caso). Si el
    archivo no existe o no se puede leer, fallback silencioso (con
    mensaje en consola) al comportamiento de 'parada' de siempre.

    `observar`: NUEVO (Kebyn, 2026-09-24) -- si es True el slot es una
    'Observar' en vez de una parada quieta: el root sigue inmovil, pero
    Jerry se sienta (pose de sentado_mirar_frente.json), gira la cabeza de
    derecha a izquierda en alerta y se vuelve a parar. Dura `frames_parada`
    frames (default FRAMES_OBSERVAR_DEFAULT) e ignora `anim_file_path`. Ver
    observar_motion.py. Se genera como `slot_NNN_jerry_observar`.

    `points` debe ser una lista de 2 puntos IDENTICOS (misma x/y/z) --
    exactamente lo que produce `group_segments()` cuando
    `detect_movement_type` devuelve "parada".
    """
    _kind = 'observar' if observar else 'parada'
    _anim_kf_data = None
    _anim_frame_count = None
    if anim_file_path and not observar:
        _anim_kf_data, _anim_frame_count = _load_keyframe_data_from_anim_file(anim_file_path)

    if observar:
        _om = _load_observar_motion()
        total_frames = frames_parada if frames_parada is not None else _om.FRAMES_OBSERVAR_DEFAULT
    elif _anim_kf_data and _anim_frame_count:
        total_frames = _anim_frame_count
    else:
        total_frames = frames_parada if frames_parada is not None else FRAMES_PARADA_DEFAULT
    end_frame = start_frame + total_frames - 1
    p0 = points[0]['coordinates'] if len(points) > 0 else {'x': 0, 'y': 0, 'z': 0}
    p1 = points[1]['coordinates'] if len(points) > 1 else p0
    traj = _fmt_trajectory(points)
    rx, ry, rz = root_rot

    blink_start_val = start_frame + int(total_frames * 0.50)

    if observar:
        _rot_kf, _loc_kf = _om.build_observar_keyframes(
            total_frames,
            {b: q for b, q in IDLE_POSE_PARADA_DEFAULT.items()})
        _bones_block = _build_observar_block_jerry(_rot_kf, _loc_kf, start_frame)
        _movement_type_label = "observar"
        _animation_type_label = "sit_alert_look_around"
        _docstring_nota = (
            'NOTA: este slot mantiene el root inmovil. Jerry se sienta (pose de\n'
            'sentado_mirar_frente.json), gira la cabeza de derecha a izquierda en\n'
            'alerta y se vuelve a parar -- ver observar_motion.py.'
        )
    elif _anim_kf_data:
        import os as _os_mod_gp
        _anim_src_label = _os_mod_gp.path.basename(anim_file_path)
        _bones_block = _build_parada_anim_importada_block_jerry(
            _anim_kf_data, start_frame, slot_index, _anim_src_label)
        _movement_type_label = "parada_animada"
        _animation_type_label = "imported_animation"
        _docstring_nota = (
            f'NOTA: este slot mantiene el root inmovil y reproduce la animacion\n'
            f'importada "{_anim_src_label}" en vez de la postura estatica IDLE_POSE --\n'
            f'ver anim_file_path en generate_parada() / parada_anim_file en\n'
            f'JRRSTPathPoint (path_recorder.py).'
        )
    else:
        _bones_block = '''bones_applied = 0
    for bname, (qw, qx, qy, qz) in IDLE_POSE.items():
        b = armature.pose.bones.get(bname)
        if b is None:
            continue
        b.rotation_mode = 'XYZ'
        b.rotation_euler = Quaternion((qw, qx, qy, qz)).to_euler('XYZ')
        b.keyframe_insert(data_path='rotation_euler', frame=START_FRAME)
        b.keyframe_insert(data_path='rotation_euler', frame=END_FRAME)
        bones_applied += 1

    if armature.animation_data.action:
        for fcurve in _get_action_fcurves(armature.animation_data.action):
            for kp in fcurve.keyframe_points:
                kp.interpolation = 'CONSTANT'

    print(f"   {bones_applied} bones puestos en postura 'parado' para canvas limpio")'''
        _movement_type_label = "parada"
        _animation_type_label = "stop_hold_reset"
        _docstring_nota = (
            'NOTA: este slot mantiene el root inmovil y fuerza todos los bones\n'
            'animables a la postura base "parado" (Dog_001_rig, IDLE_POSE) durante\n'
            'todo el rango -- canvas limpio para que el Paso 3 superponga su pose,\n'
            'sin heredar la ultima pose congelada del segmento anterior.'
        )

    _aplicada_txt = (
        "OBSERVAR APLICADA -- root inmovil, Jerry sentado en alerta mirando a los lados"
        if observar else
        "PARADA APLICADA -- root inmovil, bones en postura 'parado'"
    )

    code = f'''# -*- coding: utf-8 -*-
"""
slot_{slot_index:03d}_jerry_{_kind}.py
Jerry (perro) - Slot {slot_index}
GENERADO AUTOMATICAMENTE - {today}
Tipo: {_kind}  |  Frames: {start_frame}-{end_frame}  ({total_frames} frames)

{_docstring_nota}
"""

import bpy
import math
from mathutils import Quaternion

SLOT_INDEX   = {slot_index}
START_FRAME  = {start_frame}
END_FRAME    = {end_frame}
TOTAL_FRAMES = {total_frames}

{traj}

ANIMATION_INFO = {{
    'name': 'slot_{slot_index:03d}_jerry_{_kind}',
    'frame_count': {total_frames},
    'fps': 24,
    'duration_seconds': {total_frames/24:.3f},
    'entity': 'Jerry',
    'slot': {slot_index},
    'movement_type': '{_movement_type_label}',
    'animation_type': '{_animation_type_label}',
}}
{COMMON_MATH}
{FCURVES_COMPAT_BLOCK}
{BLINK_SYSTEM_BLOCK}

ROOT_LOCATION_DATA = {{
    {start_frame}: ({p0['x']}, {p0['y']}, {p0['z']}),
    {end_frame}:   ({p1['x']}, {p1['y']}, {p1['z']}),
}}
ROOT_ROTATION_X = {rx}
ROOT_ROTATION_Y = {ry}
ROOT_ROTATION_Z = {rz}   # sin trayecto (parada) -> orientacion base, fija
ROOT_ROTATION_DATA = {{
    {start_frame}: (math.radians({rx}), math.radians({ry}), math.radians({rz})),
    {end_frame}:   (math.radians({rx}), math.radians({ry}), math.radians({rz})),
}}

IDLE_POSE = {IDLE_POSE_PARADA_DEFAULT!r}


def execute_animation(player_parts, start_frame=START_FRAME, end_frame=END_FRAME):
    start_frame = START_FRAME; end_frame = END_FRAME

    root = next((o for o in bpy.data.objects if o.name.lower() == 'jerry'), None)
    if not root:
        root = next((o for o in bpy.data.objects if 'jerry' in o.name.lower() and o.type in ('EMPTY','ARMATURE')), None)
    if not root:
        print("ERROR: No se encontro el empty 'jerry'"); return False

    armature = next((o for o in bpy.data.objects if o.type == 'ARMATURE' and o.parent == root), None)
    if not armature:
        armature = bpy.data.objects.get("Dog_001_rig")
    if not armature:
        armature = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
    if not armature:
        print("ERROR: No se encontro el Armature"); return False

    _arm_action_name  = f'slot_{{SLOT_INDEX:03d}}_jerry_{_kind}_arm'
    _root_action_name = f'slot_{{SLOT_INDEX:03d}}_jerry_{_kind}_root'

    if not armature.animation_data:
        armature.animation_data_create()
    _arm_existing = bpy.data.actions.get(_arm_action_name)
    if _arm_existing:
        bpy.data.actions.remove(_arm_existing)
    _arm_action = bpy.data.actions.new(name=_arm_action_name)
    armature.animation_data.action = _arm_action

    bpy.context.view_layer.objects.active = armature
    if armature.mode != 'POSE': bpy.ops.object.mode_set(mode='POSE')

    {_bones_block}

    if not root.animation_data:
        root.animation_data_create()
    _root_existing = bpy.data.actions.get(_root_action_name)
    if _root_existing:
        bpy.data.actions.remove(_root_existing)
    _root_action = bpy.data.actions.new(name=_root_action_name)
    root.animation_data.action = _root_action

    for frame, rotation in ROOT_ROTATION_DATA.items():
        root.rotation_euler = rotation
        root.keyframe_insert(data_path="rotation_euler", frame=frame)
    for frame, location in ROOT_LOCATION_DATA.items():
        root.location = location
        root.keyframe_insert(data_path="location", frame=frame)

    if root.animation_data.action:
        for fcurve in _get_action_fcurves(root.animation_data.action):
            for kp in fcurve.keyframe_points:
                kp.interpolation = 'CONSTANT'

    print({_aplicada_txt!r})
    print(f"  Frames: {{start_frame}}-{{end_frame}}")

    blink_start = {blink_start_val}
    setup_blink_shape_keys()
    for t in range(start_frame, end_frame + 1):
        blink_applied = False
        if blink_start <= t < blink_start + 9:
            blink_applied = True
            offset     = t - blink_start + 1
            frame_data = BLINK_SEQUENCE.get(offset, {{"closed": 0.0, "hide": False}})
            progress   = frame_data["closed"]
            hide_eye   = frame_data["hide"]
            for eye_name in EYE_NAMES:
                eye = bpy.data.objects.get(eye_name)
                if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                    ck = eye.data.shape_keys.key_blocks.get("Closed")
                    if ck:
                        ck.value = progress
                        ck.keyframe_insert(data_path='value', frame=t)
                        eye.hide_viewport = hide_eye
                        eye.hide_render   = hide_eye
                        eye.keyframe_insert(data_path="hide_viewport", frame=t)
                        eye.keyframe_insert(data_path="hide_render",   frame=t)
        if not blink_applied:
            for eye_name in EYE_NAMES:
                eye = bpy.data.objects.get(eye_name)
                if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                    ck = eye.data.shape_keys.key_blocks.get("Closed")
                    if ck:
                        ck.value = 0.0
                        ck.keyframe_insert(data_path='value', frame=t)
                        eye.hide_viewport = False
                        eye.hide_render   = False
                        eye.keyframe_insert(data_path="hide_viewport", frame=t)
                        eye.keyframe_insert(data_path="hide_render",   frame=t)

    if armature.animation_data and armature.animation_data.action:
        _arm_done  = armature.animation_data.action
        armature.animation_data.action = None
        _arm_track = armature.animation_data.nla_tracks.new()
        _arm_track.name = f'Slot_{{SLOT_INDEX:03d}}_{_kind}_arm'
        _arm_strip = _arm_track.strips.new(_arm_done.name, start_frame, _arm_done)
        _arm_strip.frame_end      = end_frame
        _arm_strip.extrapolation  = 'NOTHING'
        _arm_strip.use_auto_blend = False
        _arm_strip.blend_in       = 0
        _arm_strip.blend_out      = 0

    if root.animation_data and root.animation_data.action:
        _root_done  = root.animation_data.action
        root.animation_data.action = None
        _root_track = root.animation_data.nla_tracks.new()
        _root_track.name = f'Slot_{{SLOT_INDEX:03d}}_{_kind}_root'
        _root_strip = _root_track.strips.new(_root_done.name, start_frame, _root_done)
        _root_strip.frame_end      = end_frame
        _root_strip.extrapolation  = 'HOLD_FORWARD'
        _root_strip.use_auto_blend = False
        _root_strip.blend_in       = 0
        _root_strip.blend_out      = 0

    return True


if __name__ == "__main__":
    execute_animation({{}}, START_FRAME, END_FRAME)
'''
    return code, end_frame


# ============================================================
# GENERADOR: SALTAR BAJAR  (24 frames, QuadrupedWalkPlainCycle)
# ============================================================

def generate_saltar_bajar(slot_index, start_frame, points, today, prev_rz, root_rot=(0, 0, -90), fps=24.0):
    return _adaptive_jump.generate_jump(slot_index,start_frame,points,root_rot,'bajar',fps,None)


# ============================================================
# ESTILOS DE CAMINATA (multiplexor) — portado de Alfred, 2026-08-05
# ============================================================
# Igual que WALK_STYLE_PARAMS en generate_slots_alfred.py: cada estilo
# escala la MISMA SniffingSearchCycle (base = NORMAL) en vez de tener
# ciclos de animacion separados por estilo. Fuente unica de verdad para
# los 3 lugares que animan a Jerry caminando: este generador
# (ExportSlots), _gen_caminar() en path_recorder.py (GenerateSlots), y
# la instancia "en vivo" de SniffingSearchCycle usada por
# JRRSTPR_OT_PreviewPath (_bones_caminar) -- los tres importan este
# dict para no desincronizarse entre si.
#
#   - speed_mult    : multiplica el "costo" en frames por unidad de
#                     distancia (frames_por_bloque efectivo). >1 =
#                     tramo mas lento (mas frames para la misma
#                     distancia). <1 = mas rapido.
#   - cycle_mult    : escala cycle_length (el ciclo base de
#                     SniffingSearchCycle, 25 frames en NORMAL). >1 =
#                     zancada mas lenta/larga. <1 = cadencia mas rapida.
#   - range_mult    : multiplicadores de amplitud sobre los mismos
#                     valores que ya usaba SniffingSearchCycle
#                     (leg_slow_walk/leg_bend/foot_strike/toe_curl,
#                     spine_undulation, tail_wag_alert, cabeza/hocico,
#                     orejas), agrupados por zona del cuerpo.
#   - vertical_bob  : rebote vertical extra (metros) del root en cada
#                     apoyo -- 0.0 en los estilos que no lo necesitan.
#   - asym_rear_leg : 0.0-1.0 -- cuanto se debilita la pata TRASERA
#                     DERECHA (amplitud de swing/flexion) para simular
#                     cojera. Solo HERIDO lo usa; el resto va en 0.0
#                     (simetrico).
WALK_STYLE_PARAMS = {
    'NORMAL': {
        'label': 'Caminar Normal',
        'speed_mult': 1.0, 'cycle_mult': 1.0,
        'range_mult': {'leg': 1.0, 'spine': 1.0, 'tail': 1.0, 'head': 1.0, 'ear': 1.0},
        'vertical_bob': 0.0, 'asym_rear_leg': 0.0,
    },
    'LENTO': {
        'label': 'Caminar Lento',
        'speed_mult': 1.3, 'cycle_mult': 1.2,
        'range_mult': {'leg': 0.7, 'spine': 0.8, 'tail': 0.55, 'head': 1.15, 'ear': 1.1},
        'vertical_bob': 0.0, 'asym_rear_leg': 0.0,
    },
    'HERIDO': {
        'label': 'Caminar Herido',
        'speed_mult': 1.55, 'cycle_mult': 1.35,
        'range_mult': {'leg': 0.6, 'spine': 1.3, 'tail': 0.35, 'head': 0.7, 'ear': 0.6},
        'vertical_bob': 0.035, 'asym_rear_leg': 0.55,
    },
    'RAPIDO': {
        'label': 'Caminar Rapido',
        'speed_mult': 0.75, 'cycle_mult': 0.8,
        'range_mult': {'leg': 1.25, 'spine': 1.15, 'tail': 1.2, 'head': 0.9, 'ear': 0.9},
        'vertical_bob': 0.015, 'asym_rear_leg': 0.0,
    },
    'CORRER': {
        'label': 'Correr',
        'speed_mult': 0.45, 'cycle_mult': 0.5,
        'range_mult': {'leg': 1.7, 'spine': 1.6, 'tail': 1.5, 'head': 0.6, 'ear': 0.7},
        'vertical_bob': 0.05, 'asym_rear_leg': 0.0,
    },
    # NUEVO: variante de CORRER con +50% de velocidad de desplazamiento
    # y +50% de amplitud en todos los huesos (patas, columna, cola,
    # cabeza, orejas), para demostrar que Jerry esta corriendo aun mas
    # rapido que en CORRER. speed_mult se reduce en la misma proporcion
    # (/1.5) porque es "costo en frames por unidad de distancia": bajarlo
    # un 33% (1/1.5) equivale a subir la velocidad real un 50%.
    'CORRER_2': {
        'label': 'Correr 2 (rapido +50%)',
        'speed_mult': 0.45 / 1.5, 'cycle_mult': 0.5,
        'range_mult': {'leg': 1.7 * 1.5, 'spine': 1.6 * 1.5, 'tail': 1.5 * 1.5,
                        'head': 0.6 * 1.5, 'ear': 0.7 * 1.5},
        'vertical_bob': 0.05 * 1.5, 'asym_rear_leg': 0.0,
    },
}


# ============================================================
# GENERADOR: CAMINAR  (SniffingSearchCycle, duracion segun distancia)
# ============================================================

def generate_caminar(slot_index, start_frame, points, today, prev_rz, root_rot=(0, 0, -90),
                      walk_style='NORMAL', frames_por_bloque=32):
    import math as _math
    style = WALK_STYLE_PARAMS.get(walk_style, WALK_STYLE_PARAMS['NORMAL'])
    _rm = style['range_mult']

    # CORREGIDO (Kebyn, 2026-08-05): antes total_frames quedaba FIJO en
    # 140 frames sin importar la distancia real del tramo ni el estilo
    # elegido. Ahora escala con la distancia (frames_por_bloque, igual
    # que _gen_caminar()/GENERAR SLOTS) y con el speed_mult del estilo.
    dist_total = 0.0
    for i in range(len(points) - 1):
        c0 = points[i]['coordinates']; c1 = points[i + 1]['coordinates']
        dx = c1['x'] - c0['x']; dy = c1['y'] - c0['y']
        dist_total += _math.sqrt(dx * dx + dy * dy)
    fpb_efectivo = frames_por_bloque * style['speed_mult']
    total_frames = max(24, round(dist_total * fpb_efectivo))
    end_frame = start_frame + total_frames - 1
    n_pts = len(points)
    traj = _fmt_trajectory(points)
    idx_start = points[0]['index']
    idx_end = points[-1]['index']
    rx, ry, rz = root_rot

    code = f'''# -*- coding: utf-8 -*-
"""
slot_{slot_index:03d}_caminar.py
Jerry (perro) - Slot {slot_index}
GENERADO AUTOMATICAMENTE - {today}
Tipo: caminar  |  Frames: {start_frame}-{end_frame}  ({total_frames} frames)
Trayectoria: punto {idx_start} -> punto {idx_end}  ({n_pts} puntos)
"""

import bpy
import math

SLOT_INDEX   = {slot_index}
START_FRAME  = {start_frame}
END_FRAME    = {end_frame}
TOTAL_FRAMES = {total_frames}

ROOT_ROTATION_X = {rx}
ROOT_ROTATION_Y = {ry}
ROOT_ROTATION_Z = {prev_rz}

{traj}

ANIMATION_INFO = {{
    'name': 'slot_{slot_index:03d}_jerry_caminar',
    'frame_count': {total_frames},
    'fps': 24,
    'duration_seconds': {total_frames/24:.3f},
    'entity': 'Jerry',
    'slot': {slot_index},
    'movement_type': 'caminar',
    'walk_style': '{walk_style}',
}}

# ============================================================
# ESTILO DE CAMINATA (multiplexor) — Kebyn, 2026-08-05
# ============================================================
WALK_STYLE      = "{walk_style}"                # NORMAL/LENTO/HERIDO/RAPIDO/CORRER/CORRER_2
CYCLE_LENGTH    = {max(4, round(25 * style['cycle_mult']))}                  # frames por ciclo de zancada (base 25)
RANGE_MULT      = {{'leg': {_rm['leg']:.4f}, 'spine': {_rm['spine']:.4f}, 'tail': {_rm['tail']:.4f}, 'head': {_rm['head']:.4f}, 'ear': {_rm['ear']:.4f}}}
VERTICAL_BOB    = {style['vertical_bob']}                # metros, rebote vertical extra del root
ASYM_REAR_LEG   = {style['asym_rear_leg']}              # 0.0-1.0, debilita pata trasera derecha (cojera, solo HERIDO)
{COMMON_MATH}
{DIRECTION_HELPERS}
{BLINK_SYSTEM_BLOCK}

# ============================================================
# SISTEMA DE SUAVIZADO DE ROTACION
# ============================================================
{ROTATION_SMOOTHER_CLASS}

def _compute_direction_angle_local(p0, p1):
    dx = p1[0]-p0[0]; dy = p1[1]-p0[1]
    if dx == 0 and dy == 0: return None
    ang_raw = math.degrees(math.atan2(dx, dy))
    ang_rounded = round(ang_raw/90.0)*90.0
    ang = ang_rounded if abs(ang_raw-ang_rounded) < 45 else -ang_raw
    while ang >  180: ang -= 360
    while ang < -180: ang += 360
    if   ang ==  90: ang = -90
    elif ang == -90: ang =  90
    if ang == 180: ang = -180
    return ang

def _get_segment_angle_for_frame(segments, frames_per_seg, cum_frames, frame):
    prev = 0
    for j, cf in enumerate(cum_frames):
        if frame <= cf:
            ang = _compute_direction_angle_local(segments[j]['start'], segments[j]['end'])
            return ang if ang is not None else ROOT_ROTATION_Z
        prev = cf
    ang = _compute_direction_angle_local(segments[-1]['start'], segments[-1]['end'])
    return ang if ang is not None else ROOT_ROTATION_Z

_rotation_smoother = RotationSmoother(smoothing_frames=12)

# ============================================================
# CICLO DE CAMINATA CUADRUPEDO (SniffingSearchCycle)
# ============================================================

class SniffingSearchCycle:
    # NUEVO (portado de Alfred, Kebyn 2026-08-05): range_mult/asym_rear
    # aplican el estilo de caminata elegido (RANGE_MULT/ASYM_REAR_LEG
    # arriba) sobre la MISMA formula base -- no se duplica el ciclo por
    # estilo, solo se escala su amplitud.
    def __init__(self, cycle_length=25, total_frames=100, range_mult=None, asym_rear=0.0):
        self.cycle_length  = cycle_length
        self.total_frames  = total_frames
        self.rm   = range_mult or {{'leg': 1.0, 'spine': 1.0, 'tail': 1.0, 'head': 1.0, 'ear': 1.0}}
        self.asym = asym_rear  # 0.0-1.0, debilita la pata trasera derecha (cojera)

    def normalize_frame(self, frame):
        return ((frame - 1) % self.cycle_length) + 1

    def sniff_down(self, frame):
        n = self.normalize_frame(frame)
        return (sin_wave(n, self.cycle_length, 0.03 * self.rm['head'], 0, 0), 0, 0)

    def look_around(self, frame):
        n = self.normalize_frame(frame)
        return (0, sin_wave(n, self.cycle_length, 0.05 * self.rm['head'], 0, 0), 0)

    def head_tilt(self, frame):
        n = self.normalize_frame(frame)
        return (0, 0, sin_wave(n, self.cycle_length, 0.016 * self.rm['head'], 0, 0))

    def ear_twitch(self, frame):
        n = self.normalize_frame(frame)
        return (0, sin_wave(n, self.cycle_length, 0.2 * self.rm['ear'], 0, 0), sin_wave(n, self.cycle_length, 0.1 * self.rm['ear'], 0, 0))

    def tail_wag_alert(self, frame):
        n = self.normalize_frame(frame)
        t = self.rm['tail']
        return (sin_wave(n, self.cycle_length, 0.4*t, 0, 0.2*t), sin_wave(n, self.cycle_length, 0.06*t, 0, 0), sin_wave(n, self.cycle_length, 0.16*t, 0, 0))

    def leg_slow_walk(self, frame, is_rear=False, is_left=True):
        n = self.normalize_frame(frame)
        phase = 0 if is_left else math.pi
        amp   = (0.4 if is_rear else 0.3) * self.rm['leg']
        # ASYM_REAR_LEG (solo HERIDO): la pata trasera DERECHA (is_rear
        # and not is_left) se debilita para simular cojera.
        if is_rear and not is_left:
            amp *= (1.0 - self.asym)
        return (-sin_wave(n, self.cycle_length, amp, phase, 0),
                -sin_wave(n, self.cycle_length, amp*0.15, phase, 0),
                -sin_wave(n, self.cycle_length, amp*0.03, phase, 0))

    def leg_bend(self, frame, is_rear=False, is_left=True):
        n = self.normalize_frame(frame)
        phase = 0 if is_left else math.pi
        bb    = (0.3 if is_rear else 0.24) * self.rm['leg']
        if is_rear and not is_left:
            bb *= (1.0 - self.asym)
        return (-abs(sin_wave(n, self.cycle_length, bb, phase, bb)),
                -sin_wave(n, self.cycle_length, 0.1, phase, 0),
                -sin_wave(n, self.cycle_length, 0.04, phase, 0))

    def foot_strike(self, frame, is_rear=False, is_left=True):
        n = self.normalize_frame(frame)
        phase = 0 if is_left else math.pi
        amp_x = (0.8 if is_rear else 0.6) * self.rm['leg']
        if is_rear and not is_left:
            amp_x *= (1.0 - self.asym)
        x = -sin_wave(n, self.cycle_length, amp_x, phase, 0.4 if is_rear else -0.1)
        y = abs(sin_wave(n, self.cycle_length, 0.04, phase, 0.02)) * (1.0 if is_rear else 0.5)
        z = -sin_wave(n, self.cycle_length, 0.04 if is_rear else 0.06, phase, 0.02)
        return (x, y, z)

    def toe_curl(self, frame, is_rear=False, is_left=True):
        n = self.normalize_frame(frame)
        phase = 0 if is_left else math.pi
        amp = 0.5 * self.rm['leg']
        if is_rear and not is_left:
            amp *= (1.0 - self.asym)
        return (abs(sin_wave(n, self.cycle_length, amp, phase, 0.4)),
                -sin_wave(n, self.cycle_length, 0.16, phase, 0),
                -sin_wave(n, self.cycle_length, 0.08, phase, 0.04))

    def spine_undulation(self, frame, segment, total_segments=7):
        n = self.normalize_frame(frame)
        ph = (segment / total_segments) * math.pi
        return (-sin_wave(n, self.cycle_length, 0.03 * self.rm['spine'], ph, -0.08 * self.rm['spine']), 0, 0)

    def vertical_bob(self, frame):
        # NUEVO: rebote vertical extra del root en cada apoyo de pata
        # trasera -- solo se nota en estilos con VERTICAL_BOB > 0
        # (HERIDO/RAPIDO/CORRER). En HERIDO se acentua en el apoyo de la
        # pata trasera sana para compensar la cojera.
        n = self.normalize_frame(frame)
        bob = VERTICAL_BOB * (0.5 - 0.5 * math.cos(2 * math.pi * n / self.cycle_length * 2))
        if self.asym > 0.0:
            bob += max(0.0, math.sin(2 * math.pi * n / self.cycle_length)) * VERTICAL_BOB * self.asym
        return bob


def generate_keyframes(total_frames=140):
    cl    = min(CYCLE_LENGTH, max(4, total_frames))
    cycle = SniffingSearchCycle(cycle_length=cl, total_frames=total_frames,
                                 range_mult=RANGE_MULT, asym_rear=ASYM_REAR_LEG)
    kf    = {{}}
    for frame in range(1, total_frames + 1):
        kf.setdefault('shoulder.L', {{}})[frame] = cycle.leg_slow_walk(frame, True, True)
        kf.setdefault('shoulder.R', {{}})[frame] = cycle.leg_slow_walk(frame, True, False)
        kf.setdefault('thigh.L', {{}})[frame]    = tuple(x*0.01  for x in cycle.leg_slow_walk(frame, True, True))
        kf.setdefault('thigh.R', {{}})[frame]    = tuple(x*-0.3  for x in cycle.leg_slow_walk(frame, True, False))
        kf.setdefault('shin.L', {{}})[frame]     = cycle.leg_bend(frame, True, True)
        kf.setdefault('shin.R', {{}})[frame]     = cycle.leg_bend(frame, True, False)
        kf.setdefault('foot.L', {{}})[frame]     = cycle.foot_strike(frame, True, True)
        kf.setdefault('foot.R', {{}})[frame]     = cycle.foot_strike(frame, True, False)
        kf.setdefault('toe.L', {{}})[frame]      = cycle.toe_curl(frame, True, True)
        kf.setdefault('toe.R', {{}})[frame]      = cycle.toe_curl(frame, True, False)
        kf.setdefault('front_shoulder.L', {{}})[frame] = cycle.leg_slow_walk(frame+12, False, True)
        kf.setdefault('front_shoulder.R', {{}})[frame] = cycle.leg_slow_walk(frame+12, False, False)
        kf.setdefault('front_thigh.L', {{}})[frame]    = tuple(x*0.6 for x in cycle.leg_slow_walk(frame+12, False, True))
        kf.setdefault('front_thigh.R', {{}})[frame]    = tuple(x*0.4 for x in cycle.leg_slow_walk(frame+12, False, False))
        kf.setdefault('front_shin.L', {{}})[frame]     = cycle.leg_bend(frame+12, False, True)
        kf.setdefault('front_shin.R', {{}})[frame]     = cycle.leg_bend(frame+12, False, False)
        kf.setdefault('front_foot.L', {{}})[frame]     = cycle.foot_strike(frame+12, False, True)
        kf.setdefault('front_foot.R', {{}})[frame]     = cycle.foot_strike(frame+12, False, False)
        kf.setdefault('front_toe.L', {{}})[frame]      = cycle.toe_curl(frame+12, False, True)
        kf.setdefault('front_toe.R', {{}})[frame]      = cycle.toe_curl(frame+12, False, False)
        for i in range(1, 8):
            kf.setdefault(f'spine_{{i}}', {{}})[frame] = cycle.spine_undulation(frame, i, 7)
        for i in range(1, 4):
            kf.setdefault(f'tail_{{i}}', {{}})[frame] = cycle.tail_wag_alert(frame)
        sniff = cycle.sniff_down(frame); look = cycle.look_around(frame); tilt = cycle.head_tilt(frame)
        kf.setdefault('scull', {{}})[frame]   = (sniff[0]+tilt[0]*0.3, look[1], tilt[2])
        kf.setdefault('jaw_top', {{}})[frame] = (0.224, 0, 0)
        kf.setdefault('ear.L', {{}})[frame]   = cycle.ear_twitch(frame)
        kf.setdefault('ear.R', {{}})[frame]   = cycle.ear_twitch(frame+6)
        kf.setdefault('sombrero', {{}})[frame]= (0, 0, 0)
    return kf


def _load_segments():
    pts  = EMBEDDED_TRAJECTORY_POINTS
    segs = []
    for i in range(len(pts)-1):
        s = pts[i]['coordinates']; e = pts[i+1]['coordinates']
        segs.append({{'start':[s['x'],s['y'],s['z']], 'end':[e['x'],e['y'],e['z']], 'texture': pts[i].get('texture','grass_block_top')}})
    return segs

def _compute_frames_allocation(segments, total_frames):
    dists = []
    for seg in segments:
        s,e = seg['start'],seg['end']
        dx,dy,dz = e[0]-s[0],e[1]-s[1],e[2]-s[2]
        dists.append(max(0.0001, math.sqrt(dx*dx+dy*dy+dz*dz)))
    total_dist = sum(dists) or 1.0
    bf = [max(1,int(round(total_frames*(d/total_dist)))) for d in dists]
    diff = total_frames - sum(bf); i = 0
    while diff != 0:
        if diff > 0: bf[i%len(bf)] += 1; diff -= 1
        else:
            if bf[i%len(bf)] > 1: bf[i%len(bf)] -= 1; diff += 1
        i += 1
    cum = []; acc = 0
    for f in bf: acc += f; cum.append(acc)
    return bf, cum

def _get_position_for_frame(segments, frames_per_seg, cum_frames, frame):
    prev = 0
    for j, cf in enumerate(cum_frames):
        if frame <= cf:
            s,e = segments[j]['start'],segments[j]['end']
            steps = max(1, frames_per_seg[j]); local = frame - prev
            f = max(0.0, min(1.0, local/steps))
            return (s[0]+(e[0]-s[0])*f, s[1]+(e[1]-s[1])*f, s[2]+(e[2]-s[2])*f)
        prev = cf
    return tuple(segments[-1]['end'])


def execute_animation(player_parts, start_frame=START_FRAME, end_frame=END_FRAME):
    start_frame = START_FRAME; end_frame = END_FRAME

    root = next((o for o in bpy.data.objects if o.name.lower() == 'jerry'), None)
    if not root:
        root = next((o for o in bpy.data.objects if 'jerry' in o.name.lower() and o.type in ('EMPTY','ARMATURE')), None)
    if not root:
        print("ERROR: No se encontro el empty 'jerry'"); return False

    armature = next((o for o in bpy.data.objects if o.type == 'ARMATURE' and o.parent == root), None)
    if not armature:
        armature = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
    if not armature:
        print("ERROR: No se encontro el Armature"); return False

    # ============================================
    # SETUP DE ACCIONES NLA
    # ============================================
    _arm_action_name  = f'slot_{{{slot_index}:03d}}_jerry_caminar_arm'
    _root_action_name = f'slot_{{{slot_index}:03d}}_jerry_caminar_root'

    if not armature.animation_data:
        armature.animation_data_create()
    _arm_existing = bpy.data.actions.get(_arm_action_name)
    if _arm_existing:
        bpy.data.actions.remove(_arm_existing)
    _arm_action = bpy.data.actions.new(name=_arm_action_name)
    armature.animation_data.action = _arm_action

    if not root.animation_data:
        root.animation_data_create()
    _root_existing = bpy.data.actions.get(_root_action_name)
    if _root_existing:
        bpy.data.actions.remove(_root_existing)
    _root_action = bpy.data.actions.new(name=_root_action_name)
    root.animation_data.action = _root_action

    bpy.context.view_layer.objects.active = armature
    if armature.mode != 'POSE': bpy.ops.object.mode_set(mode='POSE')
    for bone in armature.pose.bones: bone.rotation_mode = 'XYZ'

    kf_data = generate_keyframes(TOTAL_FRAMES)
    bones_applied = 0
    for bone_name, fd in kf_data.items():
        bone = armature.pose.bones.get(bone_name)
        if not bone: continue
        bone.rotation_mode = 'XYZ'
        for frame, rot in fd.items():
            adj = START_FRAME + (frame - 1)
            bone.rotation_euler = rot
            bone.keyframe_insert(data_path="rotation_euler", frame=adj)
        bones_applied += 1

    segments = _load_segments()
    frames_per_seg, cum_global = _compute_frames_allocation(segments, TOTAL_FRAMES)

    # Parpadeos al 25% y 75% del slot
    slot_duration = end_frame - start_frame + 1
    blink_starts  = [start_frame + int(slot_duration * 0.25), start_frame + int(slot_duration * 0.75)]

    setup_blink_shape_keys()

    # Ciclo auxiliar SOLO para el rebote vertical del root (VERTICAL_BOB)
    # -- reusa el mismo cycle_length/asimetria que ya animo los bones,
    # asi que el rebote queda sincronizado con el apoyo de las patas.
    _bob_cycle = SniffingSearchCycle(cycle_length=min(CYCLE_LENGTH, max(4, TOTAL_FRAMES)),
                                      total_frames=TOTAL_FRAMES, asym_rear=ASYM_REAR_LEG)

    for t in range(start_frame, end_frame + 1):
        path_frame  = t - start_frame + 1
        pos         = _get_position_for_frame(segments, frames_per_seg, cum_global, min(path_frame, TOTAL_FRAMES))
        seg_ang     = _get_segment_angle_for_frame(segments, frames_per_seg, cum_global, path_frame)
        smoothed_ang= _rotation_smoother.smooth_rotation(seg_ang, t)

        bpy.context.scene.frame_set(t)
        if VERTICAL_BOB > 0.0:
            _bob = _bob_cycle.vertical_bob(min(path_frame, TOTAL_FRAMES))
            pos = (pos[0], pos[1], pos[2] + _bob)
        root.location       = pos
        root.rotation_euler = (math.radians(ROOT_ROTATION_X), math.radians(ROOT_ROTATION_Y), math.radians(smoothed_ang))
        root.keyframe_insert(data_path="location",       frame=t)
        root.keyframe_insert(data_path="rotation_euler", frame=t)

        blink_applied = False
        for blink_start in blink_starts:
            if blink_start <= t < blink_start + 9:
                blink_applied = True
                offset     = t - blink_start + 1
                frame_data = BLINK_SEQUENCE.get(offset, {{"closed": 0.0, "hide": False}})
                progress   = frame_data["closed"]
                hide_eye   = frame_data["hide"]
                for eye_name in EYE_NAMES:
                    eye = bpy.data.objects.get(eye_name)
                    if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                        ck = eye.data.shape_keys.key_blocks.get("Closed")
                        if ck:
                            ck.value = progress
                            ck.keyframe_insert(data_path='value', frame=t)
                            eye.hide_viewport = hide_eye
                            eye.hide_render   = hide_eye
                            eye.keyframe_insert(data_path="hide_viewport", frame=t)
                            eye.keyframe_insert(data_path="hide_render",   frame=t)
                break
        if not blink_applied:
            for eye_name in EYE_NAMES:
                eye = bpy.data.objects.get(eye_name)
                if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                    ck = eye.data.shape_keys.key_blocks.get("Closed")
                    if ck:
                        ck.value = 0.0
                        ck.keyframe_insert(data_path='value', frame=t)
                        eye.hide_viewport = False
                        eye.hide_render   = False
                        eye.keyframe_insert(data_path="hide_viewport", frame=t)
                        eye.keyframe_insert(data_path="hide_render",   frame=t)

    print(f"Slot {{SLOT_INDEX}} caminar completado: {{bones_applied}} bones, {{TOTAL_FRAMES}} frames")

    # ============================================
    # EMPUJAR ACCIONES AL NLA
    # ============================================
    if armature.animation_data and armature.animation_data.action:
        _arm_done  = armature.animation_data.action
        armature.animation_data.action = None
        _arm_track = armature.animation_data.nla_tracks.new()
        _arm_track.name = f'Slot_{{{slot_index}:03d}}_arm'
        _arm_strip = _arm_track.strips.new(_arm_done.name, start_frame, _arm_done)
        _arm_strip.frame_end      = end_frame
        _arm_strip.extrapolation  = 'NOTHING'
        _arm_strip.use_auto_blend = False
        _arm_strip.blend_in       = 0
        _arm_strip.blend_out      = 0

    if root.animation_data and root.animation_data.action:
        _root_done  = root.animation_data.action
        root.animation_data.action = None
        _root_track = root.animation_data.nla_tracks.new()
        _root_track.name = f'Slot_{{{slot_index}:03d}}_root'
        _root_strip = _root_track.strips.new(_root_done.name, start_frame, _root_done)
        _root_strip.frame_end      = end_frame
        _root_strip.extrapolation  = 'HOLD_FORWARD'
        _root_strip.use_auto_blend = False
        _root_strip.blend_in       = 0
        _root_strip.blend_out      = 0

    return True


if __name__ == "__main__":
    execute_animation({{}}, START_FRAME, END_FRAME)
'''
    return code, end_frame


# ============================================================
# FUNCIONES AUXILIARES DEL GENERADOR
# ============================================================

def pedir_entero(mensaje, minimo=0):
    while True:
        try:
            valor = int(input(mensaje).strip())
            if valor < minimo:
                print(f"  [!] El valor minimo es {minimo}.")
                continue
            return valor
        except ValueError:
            print("  [!] Ingresa un numero entero valido.")

def pedir_float(mensaje):
    while True:
        try:
            return float(input(mensaje).strip())
        except ValueError:
            print("  [!] Ingresa un numero valido (ej: -90  o  0  o  135).")


# ============================================================
# MAIN - INTERACTIVO
# ============================================================

def main():
    script_dir  = os.path.dirname(os.path.abspath(__file__))
    json_folder = os.path.dirname(script_dir)  # Directorio padre

    print("=" * 60)
    print("   GENERADOR DE SLOTS - JERRY (PERRO)")
    print("   Sistema de parpadeo incluido en los 3 tipos de slot")
    print("=" * 60)

    historia_json = "historia_jerry.json"
    json_path = os.path.join(json_folder, historia_json)
    if not os.path.isfile(json_path):
        print(f"\n[ERROR] No se encontro el archivo: {historia_json} en {json_folder}")
        print("  Coloca el archivo historia_jerry.json en el directorio padre.")
        input("\nPresiona ENTER para salir...")
        sys.exit(1)

    chosen_json = historia_json
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] No se pudo leer el archivo historia_jerry.json: {e}")
        input("\nPresiona ENTER para salir..."); sys.exit(1)

    key_points = data.get('recorrido', {}).get('key_points', [])
    if len(key_points) < 2:
        print("[ERROR] El JSON necesita al menos 2 key_points.")
        input("\nPresiona ENTER para salir..."); sys.exit(1)

    print(f"  Trayectoria cargada: {len(key_points)} puntos")

    segments = group_segments(key_points)
    print(f"  Segmentos detectados: {len(segments)}")
    print()
    print(f"  {'N':>3}  {'TIPO':<16} {'PUNTOS':<14} {'CANT'}")
    print(f"  {'-'*3}  {'-'*16} {'-'*14} {'-'*4}")
    for i, seg in enumerate(segments):
        pts_desc = f"{seg['points'][0]['index']} -> {seg['points'][-1]['index']}"
        print(f"  {i+1:>3}  {seg['type'].upper():<16} {pts_desc:<14} ({len(seg['points'])} pts)")

    print()
    print("-" * 60)
    print("  Configuracion de la secuencia:")
    print("-" * 60)

    start_slot  = pedir_entero("  1. Numero del primer slot  (ej: 57): ", minimo=1)
    start_frame = pedir_entero("  2. Frame inicial en Blender (ej: 2680): ", minimo=0)

    print()
    print("  3. Orientacion inicial del root 'jerry' en grados:")
    print("     Ejemplo comun: X=0  Y=0  Z=-90")
    root_x = pedir_float("     X: ")
    root_y = pedir_float("     Y: ")
    root_z = pedir_float("     Z (ej: -90): ")
    root_rot = (root_x, root_y, root_z)
    prev_rz = root_z

    output_name = f"slots_jerry_historia_desde_{start_slot}"
    output_dir  = os.path.join(script_dir, output_name)

    print()
    print(f"  Carpeta de salida: {output_name}/")
    print(f"  Orientacion root : X={root_x}  Y={root_y}  Z={root_z} grados")
    print(f"  Parpadeo         : setup automatico de shape keys en Blender")
    print("-" * 60)
    print()

    confirmar = input("  Continuar con la generacion? [S/N]: ").strip().upper()
    if confirmar != 'S':
        print("\n  Operacion cancelada.")
        input("\nPresiona ENTER para salir..."); sys.exit(0)

    os.makedirs(output_dir, exist_ok=True)
    today         = date.today().isoformat()
    slot_index    = start_slot
    current_frame = start_frame
    generated     = []

    print()
    print("  Generando archivos...")
    print()

    for seg in segments:
        move_type = seg['type']
        points    = seg['points']

        # Compute direction angle for the segment
        if len(points) >= 2:
            p0 = points[0]['coordinates']
            p1 = points[-1]['coordinates']
            dir_angle = _compute_direction_angle(p0, p1)
        else:
            dir_angle = None

        if move_type == 'saltar_subir':
            code, end_frame = generate_saltar_subir(slot_index, current_frame, points, today, prev_rz, root_rot)
            filename = f"slot_{slot_index:03d}_saltar_subir.py"
        elif move_type == 'saltar_bajar':
            code, end_frame = generate_saltar_bajar(slot_index, current_frame, points, today, prev_rz, root_rot)
            filename = f"slot_{slot_index:03d}_saltar_bajar.py"
        else:
            code, end_frame = generate_caminar(slot_index, current_frame, points, today, prev_rz, root_rot)
            filename = f"slot_{slot_index:03d}_caminar.py"

        # Update prev_rz for next slot
        if dir_angle is not None:
            prev_rz = dir_angle

        with open(os.path.join(output_dir, filename), 'w', encoding='utf-8') as f:
            f.write(code)

        frames_used = end_frame - current_frame + 1
        generated.append({
            'slot': slot_index, 'type': move_type, 'file': filename,
            'start_frame': current_frame, 'end_frame': end_frame, 'frames': frames_used,
        })
        print(f"  [OK] {filename:<42} frames {current_frame}-{end_frame}  ({frames_used} frames)")

        current_frame = end_frame + 1
        slot_index   += 1

    total_frames  = current_frame - start_frame
    total_seconds = total_frames / 24.0
    print()
    print("=" * 60)
    print("  GENERACION COMPLETADA")
    print("=" * 60)
    print(f"  Slots generados : {len(generated)}")
    print(f"  Frames totales  : {total_frames}  ({total_seconds:.2f} segundos a 24fps)")
    print(f"  Frame inicial   : {start_frame}")
    print(f"  Frame final     : {current_frame - 1}")
    print(f"  Ultimo slot     : {slot_index - 1}")
    print(f"  Archivos en     : {output_dir}")
    print("=" * 60)

    summary = {
        "personaje": "jerry",
        "json_source": chosen_json,
        "start_slot": start_slot, "start_frame": start_frame,
        "end_slot": slot_index - 1, "end_frame": current_frame - 1,
        "root_rotation": {"x": root_x, "y": root_y, "z": root_z},
        "total_slots": len(generated), "total_frames": total_frames,
        "total_seconds": round(total_seconds, 3),
        "slots": generated,
    }
    with open(os.path.join(output_dir, "_resumen_slots_jerry.json"), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"  Resumen JSON    : _resumen_slots_jerry.json")
    print()
    input("  Presiona ENTER para cerrar...")


if __name__ == "__main__":
    main()
def generate_saltar_horizontal(slot_index, start_frame, points, today, prev_rz, root_rot=(0, 0, -90), fps=24.0):
    return _adaptive_jump.generate_jump(slot_index,start_frame,points,root_rot,"horizontal",fps,None)
