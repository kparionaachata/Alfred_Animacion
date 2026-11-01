# -*- coding: utf-8 -*-
"""
slot_001_parado.py
chicken_1 - Slot {001}

GENERADO AUTOMATICAMENTE
Fecha de generacion: 2026-06-23

Tipo        : parado
Descripcion : Animacion generada con Alfred Studio
Duracion    : 40 frames  (1.6667 s @ 24 fps)

MODO RECORRIDO : una_coordenada  (1 punto(s) registrado(s))

--- PASO 1 (Personaje y recorrido) ---
  Personaje       : chicken_1.blend
  Blend filepath  : C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/chicken_1/refinar/estructura/chicken_1.blend
  Puntos recorrido: 1

--- PASO 2 (Configuracion de slots) ---
  Slot inicio         : 1
  Frame inicial       : 1
  Frame final         : 40
  Frames por bloque   : 26
  Orientacion (X/Y/Z) : 0.0 / 0.0 / 0.0
  Carpeta de salida   : C:/Users/user/Desktop/
"""

import bpy
import math

# ── Compat fcurves Blender <5.0 / >=5.0 (Action.fcurves eliminado; las curvas
#    viven en action.layers[0].strips[0].channelbags[0]) ──
def _fcs(_action):
    _legacy = getattr(_action, 'fcurves', None)
    if _legacy is not None:
        return _legacy
    try:
        return _action.layers[0].strips[0].channelbags[0].fcurves
    except (IndexError, AttributeError):
        return []

# ============================================
# CONFIGURACION DEL SLOT
# (inyectadas por el orquestador)
# ============================================

SLOT_INDEX   = 1   # type: int
START_FRAME  = 1   # type: int
END_FRAME    = 40   # type: int
TOTAL_FRAMES = 40   # duracion estandar del tipo
ROOT_ROTATION_X = 0.0
ROOT_ROTATION_Y = 0.0
ROOT_ROTATION_Z = 0.0   # type: float  (grados) - fuente: root alfred timeline
ARMATURE_NAME   = 'Armature_chicken_1'   # type: str - nombre del objeto Armature en la escena
ROOT_OBJECT_NAME = 'chicken_1'   # type: str - nombre del objeto raiz (Empty/Armature) de este personaje

# ============================================
# MODO DE RECORRIDO Y DATOS PASO 1 / PASO 2
# ============================================

MODO_RECORRIDO = 'una_coordenada'   # 'una_coordenada' | 'multiples_coordenadas'
PASO_1_CONFIG = {
    'blend_filepath':     'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/chicken_1/refinar/estructura/chicken_1.blend',
    'n_puntos_recorrido': 1,
}

PASO_2_CONFIG = {
    'slot_inicio':       1,
    'frame_inicio':      1,
    'frame_fin_manual':  40,
    'frames_por_bloque': 26,
    'root_rot_x':        0.0,
    'root_rot_y':        0.0,
    'root_rot_z':        0.0,
    'output_dir':        'C:/Users/user/Desktop/',
}

PATH_POINTS = [{'coords': [0.0, 0.0, 0.0], 'texture': 'No Material', 'face_index': '1'}]

# ============================================
# FIN DE CONFIGURACION DEL SLOT
# ============================================

# ============================================
# COORDENADAS DEL RECORRIDO PARA SLOT
# (key_point seleccionado de historia_alfred.json)
# ============================================

EMBEDDED_TRAJECTORY_POINTS = []

# ============================================
# FIN DE COORDENADAS DEL RECORRIDO
# ============================================

ANIMATION_INFO = {
    'name': 'slot_001_parado.py',
    'frame_count': 40,
    'fps': 24,
    'duration_seconds': 1.6667,
    'entity': 'chicken_1',
    'slot': 1,
    'movement_type': 'parado',
    'narrative_importance': 'expression',
    'rig_type': 'full_armature',
    'source': 'general_animation_studio_v2.1',
    'bones_animated': 24,
    'animation_type': 'expression'
}

ANIMATION_CONFIG = {
    'name': 'chicken_1_parado',
    'frame_count': 40,
    'fps': 24,
    'duration_seconds': 1.6667,
    'entity': 'chicken_1',
    'slot': 1,
    'movement_type': 'parado',
}

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

EXPRESSION_CONFIG = {
    'enabled':           False,
    'active_expression': 'neutral',
    'expression_value':  1.0,
    'blink_enabled':     False,
    'blink_count':       2,
    'blink_duration':    9,
    'blink_frame_start': 1,
    'blink_frame_end':   60,
    'intensity_feliz':   0.18,
    'intensity_triste':  0.18,
    'intensity_enojado': 0.18,
    'intensity_sospecha':0.18,
    'curve_mode':        'QUADRATIC',
    'affect_zone':       'UPPER',
}

# ============================================
# SECUENCIA COMPLETA DE OJOS (panel 2b)
# Incluye: inicio, slots intermedios, fin y parpadeo.
# Se aplica automaticamente al importar con execute_animation().
# ============================================

import json as _json_eye
EYE_SEQUENCE_DATA = _json_eye.loads('{\n    "global": {\n        "enabled": false,\n        "global_start_frame": 1,\n        "blink_enabled": false,\n        "blink_count": 2,\n        "blink_duration": 9,\n        "blink_frame_start": 1,\n        "blink_frame_end": 60,\n        "blink_interval_idx": 0,\n        "blink_intervals": [],\n        "curve_mode": "QUADRATIC",\n        "affect_zone": "UPPER",\n        "intensity_feliz": 0.18,\n        "intensity_triste": 0.18,\n        "intensity_enojado": 0.18,\n        "intensity_sospecha": 0.18,\n        "invert_vertical": false,\n        "invert_horizontal": false,\n        "swap_axes": false,\n        "subdivide_cuts": 3,\n        "eye_L_h_axis": "x",\n        "eye_L_v_axis": "z",\n        "eye_R_h_axis": "x",\n        "eye_R_v_axis": "z"\n    },\n    "start": {\n        "duration": 10,\n        "interp_type": "SMOOTH",\n        "blink_mode": "BLINK",\n        "blink_count": 2,\n        "blink_duration": 9,\n        "active_expression": "NEUTRAL",\n        "expression_value": 1.0,\n        "eye_L": {\n            "loc": [\n                0.106646,\n                0.270456,\n                1.70082\n            ],\n            "rot": [\n                0.0,\n                0.0,\n                0.0\n            ],\n            "sca": [\n                1.555,\n                0.496,\n                3.55\n            ]\n        },\n        "eye_R": {\n            "loc": [\n                -0.1053,\n                0.256331,\n                1.70043\n            ],\n            "rot": [\n                0.0,\n                0.0,\n                0.0\n            ],\n            "sca": [\n                1.555,\n                0.496,\n                3.55\n            ]\n        }\n    },\n    "slots": [],\n    "end": {\n        "duration": 10,\n        "interp_type": "SMOOTH",\n        "blink_mode": "BLINK",\n        "blink_count": 2,\n        "blink_duration": 9,\n        "active_expression": "NEUTRAL",\n        "expression_value": 1.0,\n        "eye_L": {\n            "loc": [\n                0.106646,\n                0.270456,\n                1.70082\n            ],\n            "rot": [\n                0.0,\n                0.0,\n                0.0\n            ],\n            "sca": [\n                1.555,\n                0.496,\n                3.55\n            ]\n        },\n        "eye_R": {\n            "loc": [\n                -0.1053,\n                0.256331,\n                1.70043\n            ],\n            "rot": [\n                0.0,\n                0.0,\n                0.0\n            ],\n            "sca": [\n                1.555,\n                0.496,\n                3.55\n            ]\n        }\n    }\n}')

# ============================================
# FIN DE SECUENCIA DE OJOS
# ============================================

# ============================================
# CONFIGURACION COMPLETA DEL PERSONAJE
# Incluye: poses (inicio/accion/fin), filtros organicos,
# sistema de ojos completo, paso1/paso2, entry/exit ratios.
# Puede usarse para restaurar la sesion de trabajo en el studio.
# ============================================
import json as _json_full_cfg
FULL_CONFIG = _json_full_cfg.loads('{"version": "1.9", "timestamp": "2026-06-23T06:08:46.135255", "description": "Configuracion de trabajo Alfred Animation Studio", "paso1_path": {"blend_filepath": "C:\\\\Users\\\\user\\\\Desktop\\\\Alfred_Animacion\\\\generador de animaciones\\\\chicken_1\\\\refinar\\\\estructura\\\\chicken_1.blend", "slot_inicio": 1, "frame_inicio": 1, "frame_fin_manual": 40, "frames_por_bloque": 26, "root_rot_x": 0.0, "root_rot_y": 0.0, "root_rot_z": 0.0, "output_dir": "", "path_points": [{"coords": [0.0, 0.0, 0.0], "texture": "No Material", "face_index": "1"}]}, "poses_dir": "C:\\\\Users\\\\user\\\\Desktop\\\\Alfred_Animacion\\\\generador de animaciones\\\\chicken_1\\\\refinar\\\\poses\\\\", "anim_dir": "C:\\\\Users\\\\user\\\\Desktop\\\\", "historia_json": "", "config_dir": "", "armature_name": "Armature_chicken_1", "start_frame": 1, "fps": 24, "entry_ratio": 0.30000001192092896, "exit_ratio": 0.30000001192092896, "pose_inicio": {"file": "parado.json", "name": "parado", "index": 0, "duration": 10, "interp": "SMOOTH", "rot_x": 0.0, "rot_y": 0.0, "rot_z": 0.0, "pos_x": 0.0, "pos_y": 0.0, "pos_z": 0.0}, "action_poses": [{"pose_name": "parado", "json_file": "parado.json", "pose_index": 0, "duration": 20, "rot_x": 0.0, "rot_y": 0.0, "rot_z": 0.0, "pos_x": 0.0, "pos_y": 0.0, "pos_z": 0.0, "interp_type": "SMOOTH"}], "pose_fin": {"file": "parado.json", "name": "parado", "index": 0, "duration": 10, "interp": "SMOOTH", "rot_x": 0.0, "rot_y": 0.0, "rot_z": 0.0, "pos_x": 0.0, "pos_y": 0.0, "pos_z": 0.0}, "export_slot_number": 1, "export_name": "alfred_nueva_animacion", "export_type": "parado", "export_desc": "Animacion generada con Alfred Studio", "selected_key_point": 1, "root_pos_key_point": "0", "key_point_coordinates": {}, "eye_expr": {"enabled": false, "intensity_feliz": 0.18000000715255737, "intensity_triste": 0.18000000715255737, "intensity_enojado": 0.18000000715255737, "intensity_sospecha": 0.18000000715255737, "curve_mode": "QUADRATIC", "affect_zone": "UPPER", "swap_axes": false, "invert_vertical": false, "invert_horizontal": false, "subdivide_cuts": 3, "active_expression": "NEUTRAL", "expression_value": 1.0, "blink_enabled": false, "blink_count": 2, "blink_duration": 9}, "eye_sequence": {"version": "1.0", "timestamp": "2026-06-23T06:08:46.136252", "description": "Configuracion de secuencia de ojos — Alfred Animation Studio", "eye_global_start_frame": 1, "eye_inicio": {"duration": 10, "interp": "SMOOTH", "blink_mode": "BLINK", "blink_count": 2, "blink_duration": 9}, "eye_slots": [], "eye_fin": {"duration": 10, "interp": "SMOOTH", "blink_mode": "BLINK", "blink_count": 2, "blink_duration": 9}, "parpadeo": {"enabled": false, "count": 2, "duration": 9, "frame_start": 1, "frame_end": 60, "blink_intervals": [], "blink_interval_idx": 0}, "shape_keys_setup": {"subdivide_cuts": 3, "curve_mode": "QUADRATIC", "affect_zone": "UPPER", "swap_axes": false, "invert_vertical": false, "invert_horizontal": false}}, "organic": {"enabled": false, "breathing_enabled": true, "breathing_bone_a": "", "breathing_bone_b": "", "breathing_amplitude": 0.012000000104308128, "breathing_speed": 0.07999999821186066, "breathing_phase": 0.0, "head_sway_enabled": true, "head_sway_bone_a": "", "head_sway_bone_b": "", "head_sway_amplitude": 0.00800000037997961, "head_sway_speed": 0.05000000074505806, "head_sway_seed": 42, "weight_shift_enabled": false, "weight_shift_bone": "", "weight_shift_amplitude": 0.004999999888241291, "weight_shift_speed": 0.03999999910593033, "root_noise_enabled": false, "root_noise_object": "", "root_noise_strength": 0.003000000026077032, "root_noise_frequency": 0.15000000596046448, "root_noise_seed": 7, "secondary_motion_enabled": false, "secondary_motion_bone_a": "", "secondary_motion_bone_b": "", "secondary_motion_lag": 3.0, "secondary_motion_damping": 0.699999988079071, "smooth_curves_enabled": true, "smooth_passes": 2, "smooth_factor": 0.5, "micro_scale_enabled": false, "micro_scale_bone": "", "micro_scale_amplitude": 0.004999999888241291, "shoulder_noise_enabled": false, "shoulder_noise_bone_a": "", "shoulder_noise_bone_b": "", "shoulder_noise_amplitude": 0.006000000052154064, "shoulder_noise_speed": 0.07000000029802322, "shoulder_noise_seed": 123}, "root_motion": {"enabled": false, "speed": 1.0, "distance_per_cycle": 1.0, "num_cycles": 4, "frames_per_cycle": 24, "auto_frames": true, "direction": "POS_Y", "start_frame": 1, "interpolation": "LINEAR", "clear_before": true}, "level_blocks": {"enabled": false, "floor_length": 10, "floor_width": 3, "obstacle_col": 3, "obstacle_row": 0, "obstacle_height": 1}}')

BONES_LISTA = ['Root_M_chicken_1', 'Spine1_M_chicken_1', 'Chest_M_chicken_1', 'Neck_M_chicken_1', 'Head_M_chicken_1', 'Jaw_M_chicken_1', 'Jaw_top_chicken_1', 'Jaw_bot_chicken_1', 'Scapula_R_chicken_1', 'Shoulder_R_chicken_1', 'Elbow_R_chicken_1', 'Scapula_L_chicken_1', 'Shoulder_L_chicken_1', 'Elbow_L_chicken_1', 'Hip_R_chicken_1', 'Knee_R_chicken_1', 'Ankle_R_chicken_1', 'Hip_L_chicken_1', 'Knee_L_chicken_1', 'Ankle_L_chicken_1', 'Knee.Right_chicken_1', 'Knee.Left_chicken_1', 'no_bone_01_chicken_1', 'no_bone_02_chicken_1', 'no_bone_03_chicken_1', 'no_bone_04_chicken_1', 'no_bone_05_chicken_1', 'no_bone_06_chicken_1']

# ── Interpolacion 3 fases ───────────────────────────────────

def _lerp(a, b, t):
    return (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t, a[2]+(b[2]-a[2])*t)

def _smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

def _interpolate_3phases(frame, total_frames, rot_start, rot_action, rot_end,
                          entry_ratio=0.3, exit_ratio=0.3):
    if frame <= 1:      return rot_start
    if frame >= total_frames: return rot_end
    entry_end  = max(2, int(total_frames * entry_ratio))
    exit_start = min(total_frames - 1, int(total_frames * (1.0 - exit_ratio)))
    if frame <= entry_end:
        t = _smooth((frame - 1) / max(entry_end - 1, 1))
        return _lerp(rot_start, rot_action, t)
    elif frame >= exit_start:
        t = _smooth((frame - exit_start) / max(total_frames - exit_start, 1))
        return _lerp(rot_action, rot_end, t)
    else:
        return rot_action

# Poses de referencia
# Pose inicio: parado  (duracion: 10 frames)
POSE_INICIO = {
    'Root_M_chicken_1': (0.0, 0.0, 0.0),
    'Spine1_M_chicken_1': (0.0, 0.0, 0.0),
    'Chest_M_chicken_1': (0.0, 0.0, 0.0),
    'Neck_M_chicken_1': (0.0, 0.0, 0.0),
    'Head_M_chicken_1': (0.0, 0.0, 0.0),
    'Jaw_M_chicken_1': (0.0, 0.0, 0.0),
    'Jaw_top_chicken_1': (0.0, 0.0, 0.0),
    'Jaw_bot_chicken_1': (0.0, 0.0, 0.0),
    'Scapula_R_chicken_1': (0.0, 0.0, 0.0),
    'Shoulder_R_chicken_1': (0.0, 0.0, 0.0),
    'Elbow_R_chicken_1': (0.0, 0.0, 0.0),
    'Scapula_L_chicken_1': (0.0, 0.0, 0.0),
    'Shoulder_L_chicken_1': (0.0, 0.0, 0.0),
    'Elbow_L_chicken_1': (0.0, 0.0, 0.0),
    'Hip_R_chicken_1': (0.0, 0.0, 0.0),
    'Knee_R_chicken_1': (0.0, 0.0, 0.0),
    'Ankle_R_chicken_1': (0.0, 0.0, 0.0),
    'Hip_L_chicken_1': (0.0, 0.0, 0.0),
    'Knee_L_chicken_1': (0.0, 0.0, 0.0),
    'Ankle_L_chicken_1': (0.0, 0.0, 0.0),
    'Knee.Right_chicken_1': (0.0, 0.0, 0.0),
    'Knee.Left_chicken_1': (0.0, 0.0, 0.0),
    'no_bone_01_chicken_1': (0.0, 0.0, 0.0),
    'no_bone_02_chicken_1': (0.0, 0.0, 0.0),
    'no_bone_03_chicken_1': (0.0, 0.0, 0.0),
    'no_bone_04_chicken_1': (0.0, 0.0, 0.0),
    'no_bone_05_chicken_1': (0.0, 0.0, 0.0),
    'no_bone_06_chicken_1': (0.0, 0.0, 0.0),
}

# Pose accion (frame central)
POSE_ACCION = {
    'Root_M_chicken_1': (0.0, 0.0, 0.0),
    'Spine1_M_chicken_1': (0.0, 0.0, 0.0),
    'Chest_M_chicken_1': (0.0, 0.0, 0.0),
    'Neck_M_chicken_1': (0.0, 0.0, 0.0),
    'Head_M_chicken_1': (0.0, 0.0, 0.0),
    'Jaw_M_chicken_1': (0.0, 0.0, 0.0),
    'Jaw_top_chicken_1': (0.0, 0.0, 0.0),
    'Jaw_bot_chicken_1': (0.0, 0.0, 0.0),
    'Scapula_R_chicken_1': (0.0, 0.0, 0.0),
    'Shoulder_R_chicken_1': (0.0, 0.0, 0.0),
    'Elbow_R_chicken_1': (0.0, 0.0, 0.0),
    'Scapula_L_chicken_1': (0.0, 0.0, 0.0),
    'Shoulder_L_chicken_1': (0.0, 0.0, 0.0),
    'Elbow_L_chicken_1': (0.0, 0.0, 0.0),
    'Hip_R_chicken_1': (0.0, 0.0, 0.0),
    'Knee_R_chicken_1': (0.0, 0.0, 0.0),
    'Ankle_R_chicken_1': (0.0, 0.0, 0.0),
    'Hip_L_chicken_1': (0.0, 0.0, 0.0),
    'Knee_L_chicken_1': (0.0, 0.0, 0.0),
    'Ankle_L_chicken_1': (0.0, 0.0, 0.0),
    'Knee.Right_chicken_1': (0.0, 0.0, 0.0),
    'Knee.Left_chicken_1': (0.0, 0.0, 0.0),
    'no_bone_01_chicken_1': (0.0, 0.0, 0.0),
    'no_bone_02_chicken_1': (0.0, 0.0, 0.0),
    'no_bone_03_chicken_1': (0.0, 0.0, 0.0),
    'no_bone_04_chicken_1': (0.0, 0.0, 0.0),
    'no_bone_05_chicken_1': (0.0, 0.0, 0.0),
    'no_bone_06_chicken_1': (0.0, 0.0, 0.0),
}

# Pose fin: parado  (duracion: 10 frames)
POSE_FIN = {
    'Root_M_chicken_1': (0.0, 0.0, 0.0),
    'Spine1_M_chicken_1': (0.0, 0.0, 0.0),
    'Chest_M_chicken_1': (0.0, 0.0, 0.0),
    'Neck_M_chicken_1': (0.0, 0.0, 0.0),
    'Head_M_chicken_1': (0.0, 0.0, 0.0),
    'Jaw_M_chicken_1': (0.0, 0.0, 0.0),
    'Jaw_top_chicken_1': (0.0, 0.0, 0.0),
    'Jaw_bot_chicken_1': (0.0, 0.0, 0.0),
    'Scapula_R_chicken_1': (0.0, 0.0, 0.0),
    'Shoulder_R_chicken_1': (0.0, 0.0, 0.0),
    'Elbow_R_chicken_1': (0.0, 0.0, 0.0),
    'Scapula_L_chicken_1': (0.0, 0.0, 0.0),
    'Shoulder_L_chicken_1': (0.0, 0.0, 0.0),
    'Elbow_L_chicken_1': (0.0, 0.0, 0.0),
    'Hip_R_chicken_1': (0.0, 0.0, 0.0),
    'Knee_R_chicken_1': (0.0, 0.0, 0.0),
    'Ankle_R_chicken_1': (0.0, 0.0, 0.0),
    'Hip_L_chicken_1': (0.0, 0.0, 0.0),
    'Knee_L_chicken_1': (0.0, 0.0, 0.0),
    'Ankle_L_chicken_1': (0.0, 0.0, 0.0),
    'Knee.Right_chicken_1': (0.0, 0.0, 0.0),
    'Knee.Left_chicken_1': (0.0, 0.0, 0.0),
    'no_bone_01_chicken_1': (0.0, 0.0, 0.0),
    'no_bone_02_chicken_1': (0.0, 0.0, 0.0),
    'no_bone_03_chicken_1': (0.0, 0.0, 0.0),
    'no_bone_04_chicken_1': (0.0, 0.0, 0.0),
    'no_bone_05_chicken_1': (0.0, 0.0, 0.0),
    'no_bone_06_chicken_1': (0.0, 0.0, 0.0),
}

def _build_bone_functions(total_frames):
    """
    Animacion en 3 fases:
      Inicio  (parado)  -> frame 1 exacto
      Accion  -> frame central
      Fin     (parado)    -> ultimo frame exacto
    """
    bone_functions = {}
    for bone_name in BONES_LISTA:
        s = POSE_INICIO.get(bone_name, (0.0, 0.0, 0.0))
        c = POSE_ACCION.get(bone_name, s)
        e = POSE_FIN.get(bone_name,    s)
        bone_functions[bone_name] = (
            lambda f, ps=s, pa=c, pe=e:
                _interpolate_3phases(f, total_frames, ps, pa, pe)
        )
    return bone_functions

# Keyframes exactos capturados desde la timeline de Blender
KEYFRAME_DATA = {
    'Root_M_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Spine1_M_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Chest_M_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Neck_M_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Head_M_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Jaw_M_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Jaw_top_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Jaw_bot_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Scapula_R_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Shoulder_R_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Elbow_R_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Scapula_L_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Shoulder_L_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Elbow_L_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Hip_R_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Knee_R_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Ankle_R_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Hip_L_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Knee_L_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Ankle_L_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Knee.Right_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'Knee.Left_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'no_bone_01_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'no_bone_02_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'no_bone_03_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'no_bone_04_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'no_bone_05_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
    'no_bone_06_chicken_1': {
        1: (0.0, 0.0, 0.0),
        2: (0.0, 0.0, 0.0),
        3: (0.0, 0.0, 0.0),
        4: (0.0, 0.0, 0.0),
        5: (0.0, 0.0, 0.0),
        6: (0.0, 0.0, 0.0),
        7: (0.0, 0.0, 0.0),
        8: (0.0, 0.0, 0.0),
        9: (0.0, 0.0, 0.0),
        10: (0.0, 0.0, 0.0),
        11: (0.0, 0.0, 0.0),
        12: (0.0, 0.0, 0.0),
        13: (0.0, 0.0, 0.0),
        14: (0.0, 0.0, 0.0),
        15: (0.0, 0.0, 0.0),
        16: (0.0, 0.0, 0.0),
        17: (0.0, 0.0, 0.0),
        18: (0.0, 0.0, 0.0),
        19: (0.0, 0.0, 0.0),
        20: (0.0, 0.0, 0.0),
        21: (0.0, 0.0, 0.0),
        22: (0.0, 0.0, 0.0),
        23: (0.0, 0.0, 0.0),
        24: (0.0, 0.0, 0.0),
        25: (0.0, 0.0, 0.0),
        26: (0.0, 0.0, 0.0),
        27: (0.0, 0.0, 0.0),
        28: (0.0, 0.0, 0.0),
        29: (0.0, 0.0, 0.0),
        30: (0.0, 0.0, 0.0),
        31: (0.0, 0.0, 0.0),
        32: (0.0, 0.0, 0.0),
        33: (0.0, 0.0, 0.0),
        34: (0.0, 0.0, 0.0),
        35: (0.0, 0.0, 0.0),
        36: (0.0, 0.0, 0.0),
        37: (0.0, 0.0, 0.0),
        38: (0.0, 0.0, 0.0),
        39: (0.0, 0.0, 0.0),
        40: (0.0, 0.0, 0.0),
    },
}

ARMATURE_ROTATIONS = {}   # vacio: la rotacion capturada era constante (transform estatico de la escena, no animacion por pose)

ROOT_KEYFRAMES = {
    1: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    2: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    3: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    4: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    5: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    6: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    7: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    8: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    9: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    10: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    11: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    12: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    13: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    14: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    15: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    16: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    17: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    18: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    19: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    20: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    21: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    22: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    23: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    24: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    25: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    26: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    27: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    28: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    29: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    30: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    31: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    32: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    33: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    34: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    35: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    36: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    37: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    38: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    39: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
    40: {'loc': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0)},
}

ROOT_MOTION_CONFIG = {
    'speed':              1.0,
    'distance_per_cycle': 1.0,
    'num_cycles':         2,
    'frames_per_cycle':   24,
    'auto_frames':        True,
    'direction':          'POS_Y',
    'start_frame':        1,
    'interpolation':      'LINEAR',
    'clear_before':       True,
    'dist_total':         2.0,
    'frames_total':       40,
    'has_real_displacement': False,
}


def _find_alfred_objects():
    root = bpy.data.objects.get(ROOT_OBJECT_NAME)
    if not root:
        root = next(
            (o for o in bpy.data.objects
             if o.name.lower() == ROOT_OBJECT_NAME.lower() and o.type == 'EMPTY'), None)
    armature = bpy.data.objects.get(ARMATURE_NAME)
    if not armature or armature.type != 'ARMATURE':
        if root:
            armature = next(
                (o for o in bpy.data.objects
                 if o.type == 'ARMATURE' and o.parent == root), None)
    if not armature or armature.type != 'ARMATURE':
        armature = next(
            (o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
    return root, armature


def execute_animation(player_parts=None, start_frame=None, end_frame=None):
    """
    Slot chicken_1 parado.

    Requiere que SLOT_INDEX, START_FRAME, END_FRAME y ROOT_ROTATION_Z
    hayan sido inyectados por el orquestador antes de llamar esta funcion,
    o bien pasados como argumentos start_frame / end_frame.
    """
    if start_frame is None: start_frame = START_FRAME
    if end_frame   is None: end_frame   = END_FRAME
    if start_frame is None or end_frame is None:
        raise ValueError(
            'execute_animation: START_FRAME / END_FRAME no han sido definidos. '
            'El orquestador debe inyectar los valores antes de ejecutar.')

    total_frames = end_frame - start_frame + 1

    # Obtener armature
    armature = player_parts.get('body') if player_parts else None
    if not armature:
        armature = bpy.data.objects.get(ARMATURE_NAME) or bpy.data.objects.get('Armature')
    if not armature or armature.type != 'ARMATURE':
        print('Error: No se encontro el Armature'); return False

    bpy.context.view_layer.objects.active = armature
    if armature.mode != 'POSE':
        bpy.ops.object.mode_set(mode='POSE')
    for bone in armature.pose.bones:
        bone.rotation_mode = 'XYZ'

    _arm_action_name = f'slot_{SLOT_INDEX:03d}_chicken_1_parado_arm'
    if not armature.animation_data:
        armature.animation_data_create()
    _arm_existing = bpy.data.actions.get(_arm_action_name)
    if _arm_existing: bpy.data.actions.remove(_arm_existing)
    _arm_action = bpy.data.actions.new(name=_arm_action_name)

    # Obtener root
    root = player_parts.get('root') if player_parts else None
    if not root:
        root = bpy.data.objects.get(ROOT_OBJECT_NAME)
    if not root:
        root = next(
            (o for o in bpy.data.objects
             if o.name.lower() == ROOT_OBJECT_NAME.lower() and o.type == 'EMPTY'), None)

    if root:
        _root_action_name = f'slot_{SLOT_INDEX:03d}_chicken_1_parado_root'
        if not root.animation_data:
            root.animation_data_create()
        _root_existing = bpy.data.actions.get(_root_action_name)
        if _root_existing: bpy.data.actions.remove(_root_existing)
        _root_action = bpy.data.actions.new(name=_root_action_name)
        root.animation_data.action = _root_action

    # Aplicar ROOT_KEYFRAMES / ROOT_MOTION_CONFIG al root
    if root:
        if EMBEDDED_TRAJECTORY_POINTS:
            _pt = EMBEDDED_TRAJECTORY_POINTS[0]['coordinates']
            _anchor_loc = (_pt['x'], _pt['y'], _pt['z'])
        else:
            _anchor_loc = (0.0, 0.0, 0.0)
        _anchor_rot = (math.radians(ROOT_ROTATION_X),
                       math.radians(ROOT_ROTATION_Y),
                       math.radians(ROOT_ROTATION_Z))
        _rm_cfg = ROOT_MOTION_CONFIG if isinstance(ROOT_MOTION_CONFIG, dict) else {}
        _rm_has_disp = _rm_cfg.get('has_real_displacement', True)
        if ROOT_KEYFRAMES and _rm_has_disp:
            # Desplazamiento real capturado desde la timeline
            for _lf, _kf_data in sorted(ROOT_KEYFRAMES.items()):
                _abs_f = start_frame + (_lf - 1)
                if _abs_f > end_frame: break
                _rl = _kf_data['loc']
                _offset_loc = (_anchor_loc[0] + _rl[0],
                               _anchor_loc[1] + _rl[1],
                               _anchor_loc[2] + _rl[2])
                bpy.context.scene.frame_set(_abs_f)
                root.location       = _offset_loc
                root.rotation_euler = _kf_data['rot']
                root.keyframe_insert(data_path='location',       frame=_abs_f)
                root.keyframe_insert(data_path='rotation_euler', frame=_abs_f)
        elif _rm_cfg.get('dist_total', 0.0) > 0.0:
            # Desplazamiento PROCESAL desde ROOT_MOTION_CONFIG
            # (el usuario configuro el panel 1b pero no presiono 'Aplicar')
            _dirs_map = {
                'POS_Y': (0.0,  1.0, 0.0), 'NEG_Y': (0.0, -1.0, 0.0),
                'POS_X': (1.0,  0.0, 0.0), 'NEG_X': (-1.0, 0.0, 0.0),
            }
            _dx, _dy, _dz = _dirs_map.get(_rm_cfg.get('direction', 'POS_Y'), (0.0, 1.0, 0.0))
            _dist_total   = _rm_cfg['dist_total']
            _rm_interp    = _rm_cfg.get('interpolation', 'LINEAR')
            _rm_num_cyc   = max(1, _rm_cfg.get('num_cycles', 1))
            _rm_fpc       = max(1, _rm_cfg.get('frames_per_cycle', total_frames))
            def _ease_rm(t): return t * t * (3.0 - 2.0 * t)
            _steps = max(2, min(total_frames, 64))
            for _si in range(_steps + 1):
                _t  = _si / _steps
                _abs_f = start_frame + round(_t * (total_frames - 1))
                if _abs_f > end_frame: break
                _tt = _ease_rm(_t) if _rm_interp == 'EASE' else _t
                if _rm_interp == 'STEPPED':
                    _cyc_idx = int(_t * _rm_num_cyc)
                    _d = _rm_cfg.get('distance_per_cycle', _dist_total / max(1, _rm_num_cyc)) * _cyc_idx
                else:
                    _d = _dist_total * _tt
                _offset_loc = (_anchor_loc[0] + _dx * _d,
                               _anchor_loc[1] + _dy * _d,
                               _anchor_loc[2] + _dz * _d)
                bpy.context.scene.frame_set(_abs_f)
                root.location       = _offset_loc
                root.rotation_euler = _anchor_rot
                root.keyframe_insert(data_path='location',       frame=_abs_f)
                root.keyframe_insert(data_path='rotation_euler', frame=_abs_f)
            print(f'[root_motion] Desplazamiento procesal aplicado: {_dist_total:.2f} m / {total_frames} fr')
        else:
            # Fallback: anclar fijo en el anchor point
            for _kf in range(start_frame, end_frame + 1):
                bpy.context.scene.frame_set(_kf)
                root.location       = _anchor_loc
                root.rotation_euler = _anchor_rot
                root.keyframe_insert(data_path='location',       frame=_kf)
                root.keyframe_insert(data_path='rotation_euler', frame=_kf)

    armature.animation_data.action = _arm_action

    # Aplicar rotacion adicional del root si se provee via player_parts
    alfred_root = player_parts.get('root') if player_parts else None
    if not alfred_root:
        alfred_root = root if root else next(
            (o for o in bpy.data.objects
             if o.name == ROOT_OBJECT_NAME and o.type == 'EMPTY'), None)

    rz = ROOT_ROTATION_Z if ROOT_ROTATION_Z is not None else 0.0

    # Aplicar keyframes de huesos
    bone_funcs = _build_bone_functions(total_frames)
    bones_applied = 0
    bones_missing = []

    if total_frames == TOTAL_FRAMES:
        for bn in BONES_LISTA:
            pb = armature.pose.bones.get(bn)
            if not pb: bones_missing.append(bn); continue
            pb.rotation_mode = 'XYZ'
            for lf, rot in KEYFRAME_DATA.get(bn, {}).items():
                abs_f = start_frame + (lf - 1)
                pb.rotation_euler = rot
                pb.keyframe_insert(data_path='rotation_euler', frame=abs_f)
            bones_applied += 1
    else:
        for bone_name, fn in bone_funcs.items():
            pb = armature.pose.bones.get(bone_name)
            if not pb: bones_missing.append(bone_name); continue
            pb.rotation_mode = 'XYZ'
            for local_f in range(1, total_frames + 1):
                abs_f = start_frame + (local_f - 1)
                pb.rotation_euler = fn(local_f)
                pb.keyframe_insert(data_path='rotation_euler', frame=abs_f)
            bones_applied += 1

    print(f'Keyframes aplicados a {bones_applied} bones')
    if bones_missing:
        print(f'   Bones no encontrados: {bones_missing}')

    # ── Aplicar rotacion del armature por frame (orientacion por pose) ──
    if ARMATURE_ROTATIONS:
        armature.rotation_mode = 'XYZ'
        if not armature.animation_data:
            armature.animation_data_create()
        _arm_obj_action_name = f'slot_{SLOT_INDEX:03d}_arm_obj_rot'
        _arm_obj_existing = bpy.data.actions.get(_arm_obj_action_name)
        if _arm_obj_existing: bpy.data.actions.remove(_arm_obj_existing)
        _arm_obj_action = bpy.data.actions.new(name=_arm_obj_action_name)
        armature.animation_data.action = _arm_obj_action
        for lf, rot in ARMATURE_ROTATIONS.items():
            abs_f = start_frame + (lf - 1)
            bpy.context.scene.frame_set(abs_f)
            armature.rotation_euler = rot
            armature.keyframe_insert(data_path='rotation_euler', frame=abs_f)
        # Suavizar curvas de rotacion del armature
        for fc in _fcs(_arm_obj_action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'
        # Pasar al NLA
        armature.animation_data.action = None
        _arm_obj_track = armature.animation_data.nla_tracks.new()
        _arm_obj_track.name = f'Slot_{SLOT_INDEX:03d}_arm_obj_rot'
        _arm_obj_strip = _arm_obj_track.strips.new(_arm_obj_action_name, start_frame, _arm_obj_action)
        _arm_obj_strip.frame_end     = end_frame
        _arm_obj_strip.extrapolation = 'NOTHING'
        _arm_obj_strip.use_auto_blend = False
        _arm_obj_strip.blend_in  = 0
        _arm_obj_strip.blend_out = 0

    # [FIX] Restaurar _arm_action como accion activa para keyframes de bones
    armature.animation_data.action = _arm_action

    if armature.animation_data and armature.animation_data.action:
        for fc in _fcs(armature.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'

    if alfred_root and alfred_root.animation_data and alfred_root.animation_data.action:
        for fc in _fcs(alfred_root.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'

    print(f'ANIMACION chicken_1_parado APLICADA!')
    print(f'  Frames: {start_frame}-{end_frame}')

    def _eye_apply_curve_exp(factor, curve_mode):
        if curve_mode == 'QUADRATIC': return factor ** 2
        if curve_mode == 'CUBIC':     return factor ** 3
        return factor

    def _eye_detect_axes_exp(mesh_obj):
        verts = [v.co for v in mesh_obj.data.vertices]
        if not verts: return 'x', 'z', 'y'
        xs=[v.x for v in verts]; ys=[v.y for v in verts]; zs=[v.z for v in verts]
        ranges={'x':max(xs)-min(xs),'y':max(ys)-min(ys),'z':max(zs)-min(zs)}
        # Desempate deterministico: x gana sobre z sobre y cuando rangos son iguales
        priority={'x':2,'z':1,'y':0}
        s=sorted(ranges.items(),key=lambda i:(round(i[1],6),priority[i[0]]))
        return s[2][0], s[1][0], s[0][0]

    def _eye_compute_vertex_exp(orig_co, h_axis, v_axis, bounds, expression, cfg, mirror_h=False):
        cx,cy,cz=bounds['cx'],bounds['cy'],bounds['cz']
        rx,ry,rz=bounds['rx'],bounds['ry'],bounds['rz']
        h_val=getattr(orig_co,h_axis); v_val=getattr(orig_co,v_axis)
        cv={'x':cx,'y':cy,'z':cz}[v_axis]; rv={'x':rx,'y':ry,'z':rz}[v_axis]
        ch={'x':cx,'y':cy,'z':cz}[h_axis]; rh={'x':rx,'y':ry,'z':rz}[h_axis]
        v_mult=-1 if cfg.get('invert_vertical',True) else 1
        h_mult=-1 if cfg.get('invert_horizontal',False) else 1
        v_factor=(v_val-cv)/(rv/2) if rv>0 else 0
        h_factor=(h_val-ch)/(rh/2) if rh>0 else 0
        if mirror_h: h_factor=-h_factor
        zone=cfg.get('affect_zone','UPPER')
        if zone=='UPPER':
            if v_factor<=0: return orig_co.copy()
            v_factor_norm=v_factor
        elif zone=='LOWER':
            if v_factor>=0: return orig_co.copy()
            v_factor_norm=-v_factor
        else: v_factor_norm=abs(v_factor)
        offset=0.0
        cm=cfg.get('curve_mode','QUADRATIC')
        if expression in ('feliz','triste'):
            curve=_eye_apply_curve_exp(abs(h_factor),cm)
            intens=cfg.get('intensity_feliz',0.18) if expression=='feliz' else cfg.get('intensity_triste',0.18)
            sign=1 if expression=='feliz' else -1
            offset=sign*intens*curve*v_factor_norm*v_mult
        elif expression in ('sospecha','enojado'):
            min_h=ch-rh/2
            h_norm=(h_val-min_h)/rh if rh>0 else 0.5
            if mirror_h: h_norm=1.0-h_norm
            if expression=='sospecha':
                intens=cfg.get('intensity_sospecha',0.18)
                offset=(intens*h_norm-intens/2)*v_factor_norm*v_mult*h_mult
            else:
                intens=cfg.get('intensity_enojado',0.18)
                offset=(-intens*h_norm+intens/2)*v_factor_norm*v_mult*h_mult
        elif expression=='cerrado': offset=-(v_val-cv)*0.85
        elif expression=='cansado': offset=-(v_val-cv)*0.4*v_factor_norm
        elif expression=='sorpresa': offset=(v_val-cv)*0.15*v_factor_norm
        new_co=orig_co.copy(); setattr(new_co,v_axis,v_val+offset); return new_co

    def _build_expr_shape_keys(eye_obj, cfg, is_right=False):
        cuts=cfg.get('subdivide_cuts',3)
        if cuts>0 and len(eye_obj.data.vertices)<=12:
            bpy.context.view_layer.objects.active=eye_obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            for _ in range(cuts): bpy.ops.mesh.subdivide(number_cuts=1)
            bpy.ops.object.mode_set(mode='OBJECT')
        if eye_obj.data.shape_keys: eye_obj.shape_key_clear()
        eye_obj.shape_key_add(name='Basis',from_mix=False)
        mesh=eye_obj.data
        orig=[v.co.copy() for v in mesh.vertices]
        xs=[v.co.x for v in mesh.vertices]; ys=[v.co.y for v in mesh.vertices]; zs=[v.co.z for v in mesh.vertices]
        bounds={'cx':(max(xs)+min(xs))/2,'cy':(max(ys)+min(ys))/2,'cz':(max(zs)+min(zs))/2,
                'rx':max(xs)-min(xs),'ry':max(ys)-min(ys),'rz':max(zs)-min(zs)}
        # Usar ejes serializados si estan disponibles; si no, detectar
        _side='R' if is_right else 'L'
        _h_key=f'eye_{_side}_h_axis'; _v_key=f'eye_{_side}_v_axis'
        if cfg.get(_h_key) and cfg.get(_v_key):
            h_axis=cfg[_h_key]; v_axis=cfg[_v_key]
        else:
            h_axis,v_axis,_=_eye_detect_axes_exp(eye_obj)
        if cfg.get('swap_axes',False): h_axis,v_axis=v_axis,h_axis
        print(f'[eye_build] {eye_obj.name}: h={h_axis}, v={v_axis}, is_right={is_right}, verts={len(orig)}')
        for expr in ('feliz','triste','enojado','sospecha','cerrado','cansado','sorpresa'):
            sk=eye_obj.shape_key_add(name=expr.capitalize(),from_mix=False)
            sk.value=0.0; sk.slider_min=-2.0; sk.slider_max=2.0
            for i,o in enumerate(orig):
                sk.data[i].co=_eye_compute_vertex_exp(o,h_axis,v_axis,bounds,expr,cfg,mirror_h=is_right)
        sk_cl=eye_obj.shape_key_add(name='Closed',from_mix=False)
        sk_cl.value=0.0
        min_v=min(getattr(v.co,v_axis) for v in mesh.vertices)
        for i,v in enumerate(mesh.vertices):
            nc=v.co.copy(); setattr(nc,v_axis,min_v); sk_cl.data[i].co=nc

    def _apply_expr_to_eye(eye_obj, expr_name, value, frame):
        if not eye_obj.data.shape_keys: return
        for sk in eye_obj.data.shape_keys.key_blocks:
            if sk.name=='Basis': continue
            sk.value=value if sk.name.lower()==expr_name.lower() else 0.0
            sk.keyframe_insert(data_path='value',frame=frame)

    def _set_sk_interp(eye_obj, frame, interp_type='LINEAR'):
        """Cambia la interpolacion del keyframe de shape key en un frame dado."""
        if not (eye_obj and eye_obj.data.shape_keys): return
        action = eye_obj.data.shape_keys.animation_data.action if (
            eye_obj.data.shape_keys.animation_data and
            eye_obj.data.shape_keys.animation_data.action) else None
        if not action: return
        for fc in _fcs(action):
            for kp in fc.keyframe_points:
                if abs(kp.co.x - frame) < 0.5:
                    kp.interpolation = interp_type

    def _set_obj_kf_interp(obj, frame, interp_type='LINEAR'):
        """Fija interpolacion de keyframes de loc/rot/sca del objeto en un frame."""
        if not (obj and obj.animation_data and obj.animation_data.action): return
        for fc in _fcs(obj.animation_data.action):
            for kp in fc.keyframe_points:
                if abs(kp.co.x - frame) < 0.5:
                    kp.interpolation = interp_type

    _eye_data   = EYE_SEQUENCE_DATA if isinstance(EYE_SEQUENCE_DATA, dict) else {}
    _eye_global = _eye_data.get('global', {})
    _eye_cfg    = {
        'curve_mode':        _eye_global.get('curve_mode',        'QUADRATIC'),
        'affect_zone':       _eye_global.get('affect_zone',       'UPPER'),
        'invert_vertical':   _eye_global.get('invert_vertical',   True),
        'invert_horizontal': _eye_global.get('invert_horizontal', False),
        'swap_axes':         _eye_global.get('swap_axes',         False),
        'subdivide_cuts':    _eye_global.get('subdivide_cuts',    3),
        'intensity_feliz':   _eye_global.get('intensity_feliz',   0.18),
        'intensity_triste':  _eye_global.get('intensity_triste',  0.18),
        'intensity_enojado': _eye_global.get('intensity_enojado', 0.18),
        'intensity_sospecha':_eye_global.get('intensity_sospecha',0.18),
        # Ejes serializados: garantizan que se use la misma orientacion
        # que tenia la malla cuando el usuario configuro las expresiones
        'eye_L_h_axis':      _eye_global.get('eye_L_h_axis',      'x'),
        'eye_L_v_axis':      _eye_global.get('eye_L_v_axis',      'z'),
        'eye_R_h_axis':      _eye_global.get('eye_R_h_axis',      'x'),
        'eye_R_v_axis':      _eye_global.get('eye_R_v_axis',      'z'),
    }
    _eye_L_obj = bpy.data.objects.get('ojo_izquierdo_alfred')
    _eye_R_obj = bpy.data.objects.get('ojo_derecho_alfred')
    if _eye_L_obj and _eye_L_obj.type=='MESH': _build_expr_shape_keys(_eye_L_obj, _eye_cfg, is_right=False)
    if _eye_R_obj and _eye_R_obj.type=='MESH': _build_expr_shape_keys(_eye_R_obj, _eye_cfg, is_right=True)

    if _eye_global.get('enabled', False):
        _eye_obj_map = {'ojo_izquierdo_alfred': ('eye_L', False), 'ojo_derecho_alfred': ('eye_R', True)}
        def _apply_eye_frame(frame, eye_L_data, eye_R_data, expr_name, expr_val):
            for obj_name, (key, is_r) in _eye_obj_map.items():
                eye_obj = bpy.data.objects.get(obj_name)
                if not eye_obj: continue
                d = eye_L_data if key == 'eye_L' else eye_R_data
                if d:
                    loc=d.get('loc'); rot=d.get('rot'); sca=d.get('sca')
                    if loc: eye_obj.location=loc
                    if rot: eye_obj.rotation_euler=rot
                    if sca: eye_obj.scale=sca
                    if loc: eye_obj.keyframe_insert(data_path='location',frame=frame)
                    if rot: eye_obj.keyframe_insert(data_path='rotation_euler',frame=frame)
                    if sca: eye_obj.keyframe_insert(data_path='scale',frame=frame)
                    # Forzar LINEAR en loc/rot/sca para respetar duraciones exactas
                    _set_obj_kf_interp(eye_obj, frame, 'LINEAR')
                _is_neutral = (not expr_name) or expr_name.lower() == 'neutral'
                if _is_neutral:
                    if eye_obj.data.shape_keys:
                        for sk in eye_obj.data.shape_keys.key_blocks:
                            if sk.name == 'Basis': continue
                            sk.value = 0.0
                            sk.keyframe_insert(data_path='value', frame=frame)
                        _set_sk_interp(eye_obj, frame, 'CONSTANT')
                else:
                    _apply_expr_to_eye(eye_obj, expr_name.lower(), expr_val, frame)
                    _set_sk_interp(eye_obj, frame, 'LINEAR')

        def _lerp_eye_state(a, b, t):
            def _lv(va,vb,tt):
                if va is None or vb is None: return vb
                return [va[i]+(vb[i]-va[i])*tt for i in range(len(va))]
            return {ch:_lv(a.get(ch),b.get(ch),t) for ch in ('loc','rot','sca')}

        _eye_gstart = _eye_global.get('global_start_frame', start_frame)
        _cursor = _eye_gstart

        # ── Anclas NEUTRAL: forzar 0.0 en start_frame, gstart-1 y end_frame ──
        # Previene que Blender extrapole la expresion fuera del intervalo asignado
        for _anc_name in ['ojo_izquierdo_alfred', 'ojo_derecho_alfred']:
            _anc_obj = bpy.data.objects.get(_anc_name)
            if not _anc_obj: continue
            # Anclar loc/rot/sca en start_frame y _eye_gstart-1 (CONSTANT)
            # Usar posicion del bloque 'start' como posicion neutra de referencia
            _anc_st = _eye_data.get('start', {})
            _anc_key = 'eye_L' if 'izquierdo' in _anc_name else 'eye_R'
            _anc_st_d = _anc_st.get(_anc_key, {})
            _anc_loc0 = _anc_st_d.get('loc'); _anc_rot0 = _anc_st_d.get('rot'); _anc_sca0 = _anc_st_d.get('sca')
            for _af in [start_frame, _eye_gstart - 1]:
                if _af < start_frame: continue
                if _anc_loc0: _anc_obj.location = _anc_loc0
                if _anc_rot0: _anc_obj.rotation_euler = _anc_rot0
                if _anc_sca0: _anc_obj.scale = _anc_sca0
                _anc_obj.keyframe_insert(data_path='location',       frame=_af)
                _anc_obj.keyframe_insert(data_path='rotation_euler', frame=_af)
                _anc_obj.keyframe_insert(data_path='scale',          frame=_af)
                _set_obj_kf_interp(_anc_obj, _af, 'CONSTANT')
            if not _anc_obj.data.shape_keys: continue
            for sk in _anc_obj.data.shape_keys.key_blocks:
                if sk.name == 'Basis' or sk.name == 'Closed': continue
                sk.value = 0.0
                sk.keyframe_insert(data_path='value', frame=start_frame)
                if _eye_gstart > start_frame:
                    sk.keyframe_insert(data_path='value', frame=_eye_gstart - 1)
                sk.keyframe_insert(data_path='value', frame=end_frame)
            # CONSTANT: el ancla no puede 'subir' hacia los frames vecinos
            for _af in [start_frame, _eye_gstart - 1, end_frame]:
                if _af < start_frame: continue
                _set_sk_interp(_anc_obj, _af, 'CONSTANT')

        _st_data  = _eye_data.get('start', {})
        _st_dur   = int(_st_data.get('duration', 2))
        _st_eye_L = _st_data.get('eye_L', {})
        _st_eye_R = _st_data.get('eye_R', {})
        _st_expr  = _st_data.get('active_expression', 'NEUTRAL')
        _st_val   = float(_st_data.get('expression_value', 1.0))
        for f in range(_cursor, _cursor + _st_dur):
            _apply_eye_frame(f, _st_eye_L, _st_eye_R, _st_expr, _st_val)
        _cursor += _st_dur
        _prev_eye_L = _st_eye_L; _prev_eye_R = _st_eye_R
        for _slot in _eye_data.get('slots', []):
            _sl_dur   = int(_slot.get('duration', 4))
            _sl_eye_L = _slot.get('eye_L', {})
            _sl_eye_R = _slot.get('eye_R', {})
            _sl_expr  = _slot.get('active_expression', 'NEUTRAL')
            _sl_val   = float(_slot.get('expression_value', 1.0))
            for _fi in range(_sl_dur):
                _t = (_fi + 1) / _sl_dur if _sl_dur > 0 else 1.0
                _il = _lerp_eye_state(_prev_eye_L, _sl_eye_L, _t)
                _ir = _lerp_eye_state(_prev_eye_R, _sl_eye_R, _t)
                _apply_eye_frame(_cursor + _fi, _il, _ir, _sl_expr, _sl_val)
            _prev_eye_L = _sl_eye_L; _prev_eye_R = _sl_eye_R
            _cursor += _sl_dur
        _en_data  = _eye_data.get('end', {})
        _en_dur   = int(_en_data.get('duration', 3))
        _en_eye_L = _en_data.get('eye_L', {})
        _en_eye_R = _en_data.get('eye_R', {})
        _en_expr  = _en_data.get('active_expression', 'NEUTRAL')
        _en_val   = float(_en_data.get('expression_value', 1.0))
        for f in range(_cursor, _cursor + _en_dur):
            _apply_eye_frame(f, _en_eye_L, _en_eye_R, _en_expr, _en_val)
        # Keyframe de cierre: forzar 0.0 en shape keys y CONSTANT en loc/rot/sca
        # en el ultimo frame del slot para evitar extrapolacion Bezier
        for _eo_close_name in ['ojo_izquierdo_alfred', 'ojo_derecho_alfred']:
            _eo_close = bpy.data.objects.get(_eo_close_name)
            if _eo_close and _eo_close.data.shape_keys:
                for sk in _eo_close.data.shape_keys.key_blocks:
                    if sk.name == 'Basis' or sk.name == 'Closed': continue
                    sk.value = 0.0
                    sk.keyframe_insert(data_path='value', frame=end_frame)
                _set_sk_interp(_eo_close, end_frame, 'CONSTANT')
            # Tambien fijar loc/rot/sca CONSTANT en end_frame para bloquear extrapolacion
            if _eo_close:
                _eo_close.keyframe_insert(data_path='location',       frame=end_frame)
                _eo_close.keyframe_insert(data_path='rotation_euler', frame=end_frame)
                _eo_close.keyframe_insert(data_path='scale',          frame=end_frame)
                _set_obj_kf_interp(_eo_close, end_frame, 'CONSTANT')
            # Y tambien en start_frame para bloquear extrapolacion hacia atras
            if _eo_close:
                _eo_close.keyframe_insert(data_path='location',       frame=start_frame)
                _eo_close.keyframe_insert(data_path='rotation_euler', frame=start_frame)
                _eo_close.keyframe_insert(data_path='scale',          frame=start_frame)
                _set_obj_kf_interp(_eo_close, start_frame, 'CONSTANT')

        if _eye_global.get('blink_enabled', False):
            _intervals = _eye_global.get('blink_intervals', [])
            if _intervals:
                _bidx = _eye_global.get('blink_interval_idx', 0)
                _bidx = min(_bidx, len(_intervals) - 1)
                _bi   = _intervals[_bidx]
                _blink_count    = _bi.get('blink_count',    2)
                _blink_duration = _bi.get('blink_duration', 9)
                _blink_fs       = int(_bi.get('frame_start', start_frame))
                _blink_fe       = int(_bi.get('frame_end',   end_frame))
                _bi_enabled     = _bi.get('enabled', True)
            else:
                _blink_count    = _eye_global.get('blink_count',    2)
                _blink_duration = _eye_global.get('blink_duration', 9)
                _blink_fs       = int(_eye_global.get('blink_frame_start', start_frame))
                _blink_fe       = int(_eye_global.get('blink_frame_end',   end_frame))
                _bi_enabled     = True
            if _bi_enabled and _blink_count > 0:
                _slot_dur = _blink_fe - _blink_fs + 1
                _segment  = _slot_dur / _blink_count
                _blink_starts = []
                for _bn in range(_blink_count):
                    _center = _blink_fs + _segment * (_bn + 0.5)
                    _bs = int(_center - _blink_duration / 2)
                    _bs = max(_blink_fs, min(_bs, _blink_fe - _blink_duration))
                    _blink_starts.append(_bs)
                for t in range(_blink_fs, _blink_fe + 1):
                    _blink_applied = False
                    for _blink_start in _blink_starts:
                        if _blink_start <= t < _blink_start + _blink_duration:
                            _blink_applied = True
                            offset     = t - _blink_start + 1
                            frame_data = BLINK_SEQUENCE.get(offset, {'closed': 0.0, 'hide': False})
                            progress   = frame_data['closed']
                            hide_eye   = frame_data['hide']
                            for eye_name in ['ojo_izquierdo_alfred', 'ojo_derecho_alfred']:
                                eye = bpy.data.objects.get(eye_name)
                                if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                                    ck = eye.data.shape_keys.key_blocks.get('Closed')
                                    if ck:
                                        ck.value = progress
                                        ck.keyframe_insert(data_path='value', frame=t)
                                        eye.hide_viewport = hide_eye
                                        eye.hide_render   = hide_eye
                                        eye.keyframe_insert(data_path='hide_viewport', frame=t)
                                        eye.keyframe_insert(data_path='hide_render',   frame=t)
                            break
                    if not _blink_applied:
                        for eye_name in ['ojo_izquierdo_alfred', 'ojo_derecho_alfred']:
                            eye = bpy.data.objects.get(eye_name)
                            if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                                ck = eye.data.shape_keys.key_blocks.get('Closed')
                                if ck:
                                    ck.value = 0.0
                                    ck.keyframe_insert(data_path='value', frame=t)
                                    eye.hide_viewport = False
                                    eye.hide_render   = False
                                    eye.keyframe_insert(data_path='hide_viewport', frame=t)
                                    eye.keyframe_insert(data_path='hide_render',   frame=t)
    else:
        # EYE_SEQUENCE_DATA deshabilitado: fallback legacy EXPRESSION_CONFIG
        if EXPRESSION_CONFIG.get('blink_enabled', True):
            _blink_count    = EXPRESSION_CONFIG.get('blink_count', 2)
            _blink_duration = EXPRESSION_CONFIG.get('blink_duration', 9)
            _blink_fs = EXPRESSION_CONFIG.get('blink_frame_start', start_frame)
            _blink_fe = EXPRESSION_CONFIG.get('blink_frame_end',   end_frame)
            _slot_dur = _blink_fe - _blink_fs + 1
            _segment  = _slot_dur / _blink_count if _blink_count > 0 else _slot_dur
            _blink_starts = []
            for _bi in range(_blink_count):
                _center = _blink_fs + _segment * (_bi + 0.5)
                _bs = int(_center - _blink_duration / 2)
                _bs = max(_blink_fs, min(_bs, _blink_fe - _blink_duration))
                _blink_starts.append(_bs)
            for t in range(_blink_fs, _blink_fe + 1):
                _blink_applied = False
                for _blink_start in _blink_starts:
                    if _blink_start <= t < _blink_start + _blink_duration:
                        _blink_applied = True
                        offset     = t - _blink_start + 1
                        frame_data = BLINK_SEQUENCE.get(offset, {'closed': 0.0, 'hide': False})
                        progress   = frame_data['closed']
                        hide_eye   = frame_data['hide']
                        for eye_name in ['ojo_izquierdo_alfred', 'ojo_derecho_alfred']:
                            eye = bpy.data.objects.get(eye_name)
                            if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                                ck = eye.data.shape_keys.key_blocks.get('Closed')
                                if ck:
                                    ck.value = progress
                                    ck.keyframe_insert(data_path='value', frame=t)
                                    eye.hide_viewport = hide_eye
                                    eye.hide_render   = hide_eye
                                    eye.keyframe_insert(data_path='hide_viewport', frame=t)
                                    eye.keyframe_insert(data_path='hide_render',   frame=t)
                        break
                if not _blink_applied:
                    for eye_name in ['ojo_izquierdo_alfred', 'ojo_derecho_alfred']:
                        eye = bpy.data.objects.get(eye_name)
                        if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                            ck = eye.data.shape_keys.key_blocks.get('Closed')
                            if ck:
                                ck.value = 0.0
                                ck.keyframe_insert(data_path='value', frame=t)
                                eye.hide_viewport = False
                                eye.hide_render   = False
                                eye.keyframe_insert(data_path='hide_viewport', frame=t)
                                eye.keyframe_insert(data_path='hide_render',   frame=t)

                _bs = max(_blink_fs, min(_bs, _blink_fe - _blink_duration))
                _blink_starts.append(_bs)
            for t in range(_blink_fs, _blink_fe + 1):
                _blink_applied = False
                for _blink_start in _blink_starts:
                    if _blink_start <= t < _blink_start + _blink_duration:
                        _blink_applied = True
                        offset     = t - _blink_start + 1
                        frame_data = BLINK_SEQUENCE.get(offset, {'closed': 0.0, 'hide': False})
                        progress   = frame_data['closed']
                        hide_eye   = frame_data['hide']
                        for eye_name in ['ojo_izquierdo_alfred', 'ojo_derecho_alfred']:
                            eye = bpy.data.objects.get(eye_name)
                            if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                                ck = eye.data.shape_keys.key_blocks.get('Closed')
                                if ck:
                                    ck.value = progress
                                    ck.keyframe_insert(data_path='value', frame=t)
                                    eye.hide_viewport = hide_eye
                                    eye.hide_render   = hide_eye
                                    eye.keyframe_insert(data_path='hide_viewport', frame=t)
                                    eye.keyframe_insert(data_path='hide_render',   frame=t)
                        break
                if not _blink_applied:
                    for eye_name in ['ojo_izquierdo_alfred', 'ojo_derecho_alfred']:
                        eye = bpy.data.objects.get(eye_name)
                        if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                            ck = eye.data.shape_keys.key_blocks.get('Closed')
                            if ck:
                                ck.value = 0.0
                                ck.keyframe_insert(data_path='value', frame=t)
                                eye.hide_viewport = False
                                eye.hide_render   = False
                                eye.keyframe_insert(data_path='hide_viewport', frame=t)
                                eye.keyframe_insert(data_path='hide_render',   frame=t)

    if bpy.context.scene.frame_end < end_frame:
        bpy.context.scene.frame_end = end_frame

    slot_label = SLOT_INDEX if SLOT_INDEX is not None else '?'
    print(f'OK: Slot {slot_label} chicken_1_parado completado  [{start_frame}-{end_frame}]')

    # ── Forzar pose exacta en primer y ultimo frame ──
    _POSE_FRAME_1   = {'Root_M_chicken_1': (0.0, 0.0, 0.0), 'Spine1_M_chicken_1': (0.0, 0.0, 0.0), 'Chest_M_chicken_1': (0.0, 0.0, 0.0), 'Neck_M_chicken_1': (0.0, 0.0, 0.0), 'Head_M_chicken_1': (0.0, 0.0, 0.0), 'Jaw_M_chicken_1': (0.0, 0.0, 0.0), 'Jaw_top_chicken_1': (0.0, 0.0, 0.0), 'Jaw_bot_chicken_1': (0.0, 0.0, 0.0), 'Scapula_R_chicken_1': (0.0, 0.0, 0.0), 'Shoulder_R_chicken_1': (0.0, 0.0, 0.0), 'Elbow_R_chicken_1': (0.0, 0.0, 0.0), 'Scapula_L_chicken_1': (0.0, 0.0, 0.0), 'Shoulder_L_chicken_1': (0.0, 0.0, 0.0), 'Elbow_L_chicken_1': (0.0, 0.0, 0.0), 'Hip_R_chicken_1': (0.0, 0.0, 0.0), 'Knee_R_chicken_1': (0.0, 0.0, 0.0), 'Ankle_R_chicken_1': (0.0, 0.0, 0.0), 'Hip_L_chicken_1': (0.0, 0.0, 0.0), 'Knee_L_chicken_1': (0.0, 0.0, 0.0), 'Ankle_L_chicken_1': (0.0, 0.0, 0.0), 'Knee.Right_chicken_1': (0.0, 0.0, 0.0), 'Knee.Left_chicken_1': (0.0, 0.0, 0.0), 'no_bone_01_chicken_1': (0.0, 0.0, 0.0), 'no_bone_02_chicken_1': (0.0, 0.0, 0.0), 'no_bone_03_chicken_1': (0.0, 0.0, 0.0), 'no_bone_04_chicken_1': (0.0, 0.0, 0.0), 'no_bone_05_chicken_1': (0.0, 0.0, 0.0), 'no_bone_06_chicken_1': (0.0, 0.0, 0.0)}
    _POSE_FRAME_END = {'Root_M_chicken_1': (0.0, 0.0, 0.0), 'Spine1_M_chicken_1': (0.0, 0.0, 0.0), 'Chest_M_chicken_1': (0.0, 0.0, 0.0), 'Neck_M_chicken_1': (0.0, 0.0, 0.0), 'Head_M_chicken_1': (0.0, 0.0, 0.0), 'Jaw_M_chicken_1': (0.0, 0.0, 0.0), 'Jaw_top_chicken_1': (0.0, 0.0, 0.0), 'Jaw_bot_chicken_1': (0.0, 0.0, 0.0), 'Scapula_R_chicken_1': (0.0, 0.0, 0.0), 'Shoulder_R_chicken_1': (0.0, 0.0, 0.0), 'Elbow_R_chicken_1': (0.0, 0.0, 0.0), 'Scapula_L_chicken_1': (0.0, 0.0, 0.0), 'Shoulder_L_chicken_1': (0.0, 0.0, 0.0), 'Elbow_L_chicken_1': (0.0, 0.0, 0.0), 'Hip_R_chicken_1': (0.0, 0.0, 0.0), 'Knee_R_chicken_1': (0.0, 0.0, 0.0), 'Ankle_R_chicken_1': (0.0, 0.0, 0.0), 'Hip_L_chicken_1': (0.0, 0.0, 0.0), 'Knee_L_chicken_1': (0.0, 0.0, 0.0), 'Ankle_L_chicken_1': (0.0, 0.0, 0.0), 'Knee.Right_chicken_1': (0.0, 0.0, 0.0), 'Knee.Left_chicken_1': (0.0, 0.0, 0.0), 'no_bone_01_chicken_1': (0.0, 0.0, 0.0), 'no_bone_02_chicken_1': (0.0, 0.0, 0.0), 'no_bone_03_chicken_1': (0.0, 0.0, 0.0), 'no_bone_04_chicken_1': (0.0, 0.0, 0.0), 'no_bone_05_chicken_1': (0.0, 0.0, 0.0), 'no_bone_06_chicken_1': (0.0, 0.0, 0.0)}
    for _sp_bone in armature.pose.bones:
        _sp_bone.rotation_mode = 'XYZ'
        if _sp_bone.name in _POSE_FRAME_1:
            bpy.context.scene.frame_set(start_frame)
            _sp_bone.rotation_euler = _POSE_FRAME_1[_sp_bone.name]
            _sp_bone.keyframe_insert(data_path='rotation_euler', frame=start_frame)
        if _sp_bone.name in _POSE_FRAME_END:
            bpy.context.scene.frame_set(end_frame)
            _sp_bone.rotation_euler = _POSE_FRAME_END[_sp_bone.name]
            _sp_bone.keyframe_insert(data_path='rotation_euler', frame=end_frame)
    # ── Fin forzado ──

    # Mover Action del ARMATURE al NLA
    if armature.animation_data and armature.animation_data.action:
        _arm_done  = armature.animation_data.action
        armature.animation_data.action = None
        _arm_track = armature.animation_data.nla_tracks.new()
        _arm_track.name = f'Slot_{SLOT_INDEX:03d}_arm'
        _arm_strip = _arm_track.strips.new(_arm_done.name, start_frame, _arm_done)
        _arm_strip.frame_end        = end_frame
        _arm_strip.extrapolation    = 'NOTHING'
        _arm_strip.use_auto_blend   = False
        _arm_strip.blend_in         = 0
        _arm_strip.blend_out        = 0

    # Mover Action del ROOT al NLA
    if root and root.animation_data and root.animation_data.action:
        _root_done  = root.animation_data.action
        root.animation_data.action = None
        _root_track = root.animation_data.nla_tracks.new()
        _root_track.name = f'Slot_{SLOT_INDEX:03d}_root'
        _root_strip = _root_track.strips.new(_root_done.name, start_frame, _root_done)
        _root_strip.frame_end        = end_frame
        _root_strip.extrapolation    = 'HOLD_FORWARD'
        _root_strip.use_auto_blend   = False
        _root_strip.blend_in         = 0
        _root_strip.blend_out        = 0

    # ── Aplicar EYE_SEQUENCE_DATA autonomamente (para animation_engine.py) ──
    _eye_seq_alf = EYE_SEQUENCE_DATA if isinstance(EYE_SEQUENCE_DATA, dict) else {}
    _eye_global_alf = _eye_seq_alf.get('global', {})
    if _eye_global_alf.get('enabled', False):
        _eye_gstart_alf = _eye_global_alf.get('global_start_frame', start_frame)
        def _eye_smooth_alf(t):
            t = max(0.0, min(1.0, t)); return t * t * (3.0 - 2.0 * t)
        def _eye_lerp_alf(a, b, t):
            if a is None or b is None: return b
            return [a[i] + (b[i] - a[i]) * t for i in range(len(a))]
        def _eye_lerp_td_alf(td_a, td_b, t):
            return {'loc': _eye_lerp_alf(td_a.get('loc'), td_b.get('loc'), t),
                    'rot': _eye_lerp_alf(td_a.get('rot'), td_b.get('rot'), t),
                    'sca': _eye_lerp_alf(td_a.get('sca'), td_b.get('sca'), t)}
        def _eye_apply_td_alf(frame, eL, eR):
            for obj_name, td in [('ojo_izquierdo_alfred', eL), ('ojo_derecho_alfred', eR)]:
                _eo = bpy.data.objects.get(obj_name)
                if not _eo: continue
                if td.get('loc'): _eo.location = td['loc']; _eo.keyframe_insert(data_path='location', frame=frame)
                if td.get('rot'): _eo.rotation_euler = td['rot']; _eo.keyframe_insert(data_path='rotation_euler', frame=frame)
                if td.get('sca'): _eo.scale = td['sca']; _eo.keyframe_insert(data_path='scale', frame=frame)
        _eye_states_alf = [_eye_seq_alf.get('start', {})] + _eye_seq_alf.get('slots', []) + [_eye_seq_alf.get('end', {})]
        _eye_cur_alf = _eye_gstart_alf
        for _esi in range(len(_eye_states_alf) - 1):
            _es_a = _eye_states_alf[_esi]; _es_b = _eye_states_alf[_esi + 1]
            _en_alf = int(_es_b.get('duration', 20)); _eitp = _es_b.get('interp_type', 'SMOOTH')
            _eL_a = _es_a.get('eye_L', {}); _eL_b = _es_b.get('eye_L', {})
            _eR_a = _es_a.get('eye_R', {}); _eR_b = _es_b.get('eye_R', {})
            for _efi in range(_en_alf):
                _eabs = _eye_cur_alf + _efi
                if _eabs > end_frame: break
                _raw_t = (_efi + 1) / _en_alf if _en_alf > 0 else 1.0
                _et = _eye_smooth_alf(_raw_t) if _eitp in ('SMOOTH', 'BEZIER') else _raw_t
                if _eL_a and _eL_b: _eye_apply_td_alf(_eabs, _eye_lerp_td_alf(_eL_a, _eL_b, _et), _eye_lerp_td_alf(_eR_a, _eR_b, _et))
            _eye_cur_alf += _en_alf
        if _eye_global_alf.get('blink_enabled', False):
            _eye_intervals_alf = _eye_global_alf.get('blink_intervals', [])
            if _eye_intervals_alf:
                _eye_bi_alf = _eye_intervals_alf[min(_eye_global_alf.get('blink_interval_idx', 0), len(_eye_intervals_alf) - 1)]
            else:
                _eye_bi_alf = {'frame_start': _eye_global_alf.get('blink_frame_start', start_frame), 'frame_end': _eye_global_alf.get('blink_frame_end', end_frame), 'blink_count': _eye_global_alf.get('blink_count', 5), 'blink_duration': _eye_global_alf.get('blink_duration', 9), 'enabled': True}
            if _eye_bi_alf.get('enabled', True):
                _bk_sq_alf = {1:(0.0,False),2:(0.25,False),3:(0.5,False),4:(0.75,False),5:(1.0,True),6:(1.0,True),7:(0.75,False),8:(0.5,False),9:(0.25,False)}
                _bk_sf_alf = int(_eye_bi_alf.get('frame_start', start_frame)); _bk_ef_alf = int(_eye_bi_alf.get('frame_end', end_frame))
                _bk_cnt_alf = _eye_bi_alf.get('blink_count', 5); _bk_dur_alf = _eye_bi_alf.get('blink_duration', 9)
                _bk_seg_alf = (_bk_ef_alf - _bk_sf_alf + 1) / _bk_cnt_alf if _bk_cnt_alf > 0 else (_bk_ef_alf - _bk_sf_alf + 1)
                _bk_starts_alf = [max(_bk_sf_alf, min(int(_bk_sf_alf + _bk_seg_alf * (i + 0.5) - _bk_dur_alf / 2), _bk_ef_alf - _bk_dur_alf)) for i in range(_bk_cnt_alf)]
                for _bt_alf in range(_bk_sf_alf, _bk_ef_alf + 1):
                    _bk_done_alf = False
                    for _bs_alf in _bk_starts_alf:
                        if _bs_alf <= _bt_alf < _bs_alf + _bk_dur_alf:
                            _bk_prog_alf, _bk_hide_alf = _bk_sq_alf.get(min(_bt_alf - _bs_alf + 1, 9), (0.0, False))
                            for _eon_alf in ('ojo_izquierdo_alfred', 'ojo_derecho_alfred'):
                                _eo2_alf = bpy.data.objects.get(_eon_alf)
                                if _eo2_alf and hasattr(_eo2_alf.data, 'shape_keys') and _eo2_alf.data.shape_keys:
                                    _ck2_alf = _eo2_alf.data.shape_keys.key_blocks.get('Closed')
                                    if _ck2_alf: _ck2_alf.value = _bk_prog_alf; _ck2_alf.keyframe_insert(data_path='value', frame=_bt_alf)
                                    _eo2_alf.hide_viewport = _bk_hide_alf; _eo2_alf.hide_render = _bk_hide_alf
                                    _eo2_alf.keyframe_insert(data_path='hide_viewport', frame=_bt_alf)
                                    _eo2_alf.keyframe_insert(data_path='hide_render', frame=_bt_alf)
                            _bk_done_alf = True; break
                    if not _bk_done_alf:
                        for _eon_alf in ('ojo_izquierdo_alfred', 'ojo_derecho_alfred'):
                            _eo2_alf = bpy.data.objects.get(_eon_alf)
                            if _eo2_alf and hasattr(_eo2_alf.data, 'shape_keys') and _eo2_alf.data.shape_keys:
                                _ck2_alf = _eo2_alf.data.shape_keys.key_blocks.get('Closed')
                                if _ck2_alf: _ck2_alf.value = 0.0; _ck2_alf.keyframe_insert(data_path='value', frame=_bt_alf)
                                _eo2_alf.hide_viewport = False; _eo2_alf.hide_render = False
                                _eo2_alf.keyframe_insert(data_path='hide_viewport', frame=_bt_alf)
                                _eo2_alf.keyframe_insert(data_path='hide_render', frame=_bt_alf)
        print('[eye_seq_alf] EYE_SEQUENCE_DATA aplicado autonomamente')

