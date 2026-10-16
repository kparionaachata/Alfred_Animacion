# -*- coding: utf-8 -*-
"""
slot_001_nadando_1.py
Jerry (Dog) nadando en el mar - Animación cuadrúpeda generada matemáticamente
Compatible con estructura jerry_dog.blend
Sistema jerárquico con 40 bones (completo según jerry_outliner_data.json)
Perro nadando estilo dog paddle en el océano

MODIFICACIONES ESPECÍFICAS:
1. front_thigh y thigh: Rotación X siguiendo ciclo diagonal (FR+BL, FL+BR)
2. front_shin y shin: Flexión en retorno, extensión en empuje
3. scull: Rotación +20° fija en X
4. spine: Onda sinusoidal viajera para torsión lateral

GENERADO MATEMÁTICAMENTE basado en jerry_outliner_data.json + comportamiento canino de nadar
Frames: 1-120 (10 entrada + 100 principal + 10 salida)
Bones animados: 40 (todos los bones del rig Dog_001_rig)
"""

import bpy

def _action_fcurves(action):
    """Devuelve las curvas tanto en acciones antiguas como en Blender 5."""
    if action is None:
        return ()
    legacy = getattr(action, "fcurves", None)
    if legacy is not None:
        return legacy
    curves = []
    for layer in getattr(action, "layers", ()):
        for strip in getattr(layer, "strips", ()):
            for channelbag in getattr(strip, "channelbags", ()):
                curves.extend(channelbag.fcurves)
    return curves

import math

# ============================================
# CONFIGURACIÓN DEL SLOT
# ============================================

SLOT_INDEX = 30
START_FRAME = 1421
END_FRAME = 1580  # 160 frames: 1421-1580
TOTAL_FRAMES = 160

ANIMATION_INFO = {
    'name': 'slot_030_jerry_caminar_llanura',
    'frame_count': 160,
    'fps': 24,
    'duration_seconds': 6.67,
    'entity': 'Jerry',
    'character_type': 'dog_quadruped',
    'slot': 30,
    'movement_type': 'walking_plains',
    'minecraft_scale': '1_block_=_1m3',
    'narrative_importance': 'behavioral',
    'rig_type': 'quadruped_hierarchy',
    'source': 'jerry_dog_rig_mathematical',
    'bones_animated': 40,
    'animation_type': 'mathematical',
    'bone_count': 40,
    'data_source': 'jerry_outliner_data.json',
    'complete_rig_coverage': True,
    'reference': 'dog_walking_plains_terrain',
    'entry_frames': 10,
    'exit_frames': 10,
    'main_animation_frames': 80,
    # === DESPLAZAMIENTO EMBEBIDO (Slot 30) ===
    'trajectory': [
        {"index": 98, "coordinates": {"x": -117.5, "y": -15.5, "z": 7.5}, "texture": "water_still", "face_index": "3530"},
        {"index": 99, "coordinates": {"x": -116.5, "y": -14.5, "z": 7.5}, "texture": "water_still", "face_index": "3681"},
        {"index": 100, "coordinates": {"x": -116.5, "y": -13.5, "z": 7.5}, "texture": "water_still", "face_index": "3680"},
        {"index": 101, "coordinates": {"x": -116.5, "y": -12.5, "z": 7.5}, "texture": "water_still", "face_index": "3679"},
        {"index": 102, "coordinates": {"x": -115.5, "y": -11.5, "z": 7.5}, "texture": "water_still", "face_index": "3815"},
        {"index": 103, "coordinates": {"x": -114.5, "y": -10.5, "z": 7.5}, "texture": "water_still", "face_index": "3940"},
        {"index": 104, "coordinates": {"x": -113.5, "y": -10.5, "z": 7.5}, "texture": "water_still", "face_index": "4062"},
        {"index": 105, "coordinates": {"x": -112.5, "y": -9.5, "z": 7.5}, "texture": "water_still", "face_index": "4183"},
        {"index": 106, "coordinates": {"x": -111.5, "y": -8.5, "z": 7.5}, "texture": "water_still", "face_index": "4312"},
        {"index": 107, "coordinates": {"x": -110.5, "y": -8.5, "z": 7.5}, "texture": "water_still", "face_index": "4442"},
        {"index": 108, "coordinates": {"x": -109.5, "y": -7.5, "z": 7.5}, "texture": "water_still", "face_index": "4583"},
        {"index": 109, "coordinates": {"x": -108.5, "y": -6.5, "z": 7.5}, "texture": "water_still", "face_index": "4724"},
        {"index": 110, "coordinates": {"x": -108.5, "y": -5.5, "z": 7.5}, "texture": "water_still", "face_index": "4721"},
    ]
}

# ============================================================================
# CONFIGURACIÓN DE ANIMACIÓN CAMINAR/ NADAR
# ============================================================================

# Frecuencias ajustadas para 160 frames (ciclos completos)
SWIMMING_CONFIG = {
    # 160 frames / 20 = 8 ciclos completos
    'paddle_frequency': 8.0,      # Hz - 8 ciclos en 160 frames
    'spine_wave_frequency': 4.0,  # Hz - 4 ciclos en 160 frames (onda viajera)
    'tail_wag_frequency': 6.0,    # Hz - 6 ciclos en 160 frames
    'body_roll_angle': 0.15,      # rad - inclinación lateral del cuerpo
    'head_pitch_angle': -math.radians(20),  # rad - -20° hocico ARRIBA
    'leg_extend_factor': 0.6,     # factor de extensión de patas
    'ear_retraction': 0.2,        # rad - orejas hacia atrás
    'scull_fixed_pitch': -math.radians(20),  # -20° hocico ARRIBA
    
    # === POSICIÓN DE REMO (PADDLING) - PATAS DELANTERAS ===
    # Front Right (FR) - Valores en radianes
    'front_shoulder_R': (math.radians(98.4163), math.radians(63.6823), math.radians(50.9194)),
    'front_thigh_R': (math.radians(19.6673), math.radians(-65.29), math.radians(13.7423)),
    'front_shin_R': (math.radians(-45.407), math.radians(-10.923), math.radians(4.58696)),
    'front_foot_R': (math.radians(26.4423), math.radians(-0.140239), math.radians(0.23186)),
    'front_toe_R': (math.radians(10.2319), math.radians(0.106867), 0),
    
    # Front Left (FL) - Valores en radianes (específicos para lado izquierdo)
    'front_shoulder_L': (math.radians(93.99), math.radians(-61.9984), math.radians(-51.193)),
    'front_thigh_L': (math.radians(23.2084), math.radians(65.6919), math.radians(-13.9064)),
    'front_shin_L': (math.radians(-39.9578), math.radians(11.2598), math.radians(4.58696)),
    'front_foot_L': (math.radians(29.0981), math.radians(-0.140239), math.radians(-0.104916)),
    'front_toe_L': (math.radians(10.2319), math.radians(0.106867), 0),
    
    # === PATAS TRASERAS (PROPULSIÓN) ===
    # Back Right (BR) - Valores en radianes
    'shoulder_R': (math.radians(-31.601), math.radians(-23.2069), math.radians(-1.77821)),
    'thigh_R': (math.radians(-12.2604), math.radians(5.34809), math.radians(-23.05)),
    'shin_R': (math.radians(-30.4334), math.radians(-20.3849), math.radians(3.23327)),
    'foot_R': (math.radians(-20), 0, 0),
    
    # Back Left (BL) - Valores en radianes
    'shoulder_L': (math.radians(-31.601), math.radians(23.2069), math.radians(-1.77821)),
    'thigh_L': (math.radians(-12.2604), math.radians(5.34809), math.radians(23.05)),
    'shin_L': (math.radians(-30.4334), math.radians(-20.3849), math.radians(3.23327)),
    'foot_L': (math.radians(-20), 0, 0),
}


# ============================================================================
# FUNCIONES MATEMÁTICAS PARA GENERAR MOVIMIENTOS DE NATACIÓN
# ============================================================================

def get_animation_phase(frame):
    """
    Determina la fase de la animación basada en el frame
    Returns: ('entry', adjusted_frame) | ('main', adjusted_frame) | ('exit', adjusted_frame)
    """
    if frame <= 16:  # 10% de entrada = 16 frames
        return ('entry', frame)
    elif frame <= 144:  # 80% principal = 128 frames
        return ('main', frame)
    else:
        return ('exit', frame - 144)  # 10% salida = 16 frames


def apply_animation_phase(frame, movement_func):
    """
    Aplica la lógica de fases de entrada/salida con transiciones suaves
    """
    phase, adjusted_frame = get_animation_phase(frame)
    
    if phase == 'main':
        # Fase principal: usar frame real para continuidad
        return movement_func(adjusted_frame)
    else:
        if phase == 'entry':
            transition_factor = (frame - 1) / 15.0
            # Usar frame real para continuidad (frame 16 -> frame 17)
            animation_values = movement_func(frame)
        else:  # exit
            transition_factor = (160 - frame) / 15.0
            # Usar frame 144 como base para continuidad
            animation_values = movement_func(144)
        
        base_values = (0, 0, 0)
        smooth_values = tuple(
            base * (1 - transition_factor) + anim * transition_factor
            for base, anim in zip(base_values, animation_values)
        )
        return smooth_values


# ============================================================================
# PATRÓN DIAGONAL - FR con BL, FL con BR
# ============================================================================
# Diagonal 1: FR (front_shoulder.R) + BL (shoulder.L)
# Diagonal 2: FL (front_shoulder.L) + BR (shoulder.R)

def calculate_diagonal_cycle(t, frequency=2.0):
    """
    Calcula el ciclo diagonal para las patas.
    Diagonal 1: FR + BL (FR con Back Left)
    Diagonal 2: FL + BR (FL con Back Right)
    """
    cycle = t * frequency * 2 * math.pi
    
    # Diagonal 1: FR + BL (front_shoulder.R + shoulder.L)
    diag1 = math.cos(cycle)
    
    # Diagonal 2: FL + BR (front_shoulder.L + shoulder.R) - opuesto
    diag2 = -diag1
    
    return (diag1, diag2, cycle)


# ============================================================================
# COLUMNA VERTEBRAL - Onda sinusoidal viajera para torsión lateral
# ============================================================================

def calculate_spine_movement_swimming(frame, segment_id):
    """
    Movimiento de columna vertebral:
    - Onda sinusoidal viajera (de cola a cabeza)
    - Torsión lateral realista
    - spine_2: Offset +X° adicional para arqueo del cuello
    """
    t = frame / TOTAL_FRAMES  # Usar TOTAL_FRAMES (160)
    
    spine_factor = segment_id / 7.0  # 0 a 1
    wave_freq = SWIMMING_CONFIG['spine_wave_frequency']  # 4.0 Hz
    
    # Onda viajera: la fase se desplaza a lo largo de la columna
    phase_shift = spine_factor * math.pi * 2  # Onda completa traveling
    
    # Torsión lateral (yaw) - onda viajera
    torsion_amplitude = 0.20
    yaw = math.sin(t * wave_freq * 2 * math.pi + phase_shift) * torsion_amplitude
    
    # Inclinación lateral (roll) - onda opuesta
    roll_amplitude = 0.15
    roll = math.sin(t * wave_freq * 2 * math.pi + phase_shift + math.pi) * roll_amplitude
    
    # Ondulación vertical (pitch)
    pitch_amplitude = 0.12
    pitch = math.sin(t * wave_freq * 2 * math.pi + phase_shift) * pitch_amplitude
    
    # spine_2 (segment_id=5): Offset +X° adicional para arqueo del cuello (+10°)
    if segment_id == 5:
        pitch += math.radians(10)
    
    # spine_5 (segment_id=2): Offset +15° en X para curvatura
    if segment_id == 2:
        pitch += math.radians(15)
    
    return (pitch, yaw, roll)


# ============================================================================
# CABEZA - scull con +20° fijos
# ============================================================================

def calculate_head_movement_swimming(frame):
    """
    Movimiento de cabeza durante la animación
    """
    t = frame / TOTAL_FRAMES
    
    # Cabeza con HOCICO ARRIBA (-20°)
    base_pitch = -math.radians(20)
    
    # Movimiento sutil de balanceo
    balance = math.sin(t * SWIMMING_CONFIG['paddle_frequency'] * 2 * math.pi) * 0.015
    
    pitch = base_pitch + balance
    yaw = math.sin(t * 1.5 * math.pi) * 0.02
    roll = math.sin(t * 2 * math.pi) * 0.01
    
    return (pitch, yaw, roll)


def calculate_scull_movement_swimming(frame):
    """
    Movimiento del scull: ROTACIÓN FIJA DE -20° EN X
    """
    t = frame / TOTAL_FRAMES
    
    # Pitch FIJO a -20°
    fixed_pitch = -math.radians(20)
    
    # Movimiento sutil adicional
    subtle_pitch = math.sin(t * 2 * math.pi) * 0.008
    yaw = math.sin(t * 1.5 * math.pi) * 0.008
    roll = math.sin(t * 2 * math.pi + math.pi/4) * 0.008
    
    return (fixed_pitch + subtle_pitch, yaw, roll)


# ============================================================================
# OREJAS Y MANDÍBULA
# ============================================================================

def calculate_ear_movement_swimming(frame, side='R'):
    """Orejas relajadas hacia atrás"""
    t = frame / TOTAL_FRAMES
    
    base_pitch = -SWIMMING_CONFIG['ear_retraction']
    base_yaw = 0.1 if side == 'L' else -0.1
    base_roll = 0.05
    
    wave = math.sin(t * 2 * math.pi + (0 if side == 'R' else math.pi)) * 0.02
    
    return (base_pitch + wave, base_yaw + wave * 0.5, base_roll + wave * 0.3)


def calculate_jaw_movement_swimming(frame, is_upper=True):
    """Movimiento mínimo de mandíbula"""
    t = frame / TOTAL_FRAMES
    breath_cycle = math.sin(t * 0.5 * math.pi) * 0.01
    
    if is_upper:
        return (breath_cycle, 0.02, 0.01)
    else:
        return (-breath_cycle * 0.5, 0.02, 0.01)


# ============================================================================
# COLA
# ============================================================================

def calculate_tail_movement_swimming(frame, segment_id):
    """Movimiento de cola como timón"""
    t = frame / TOTAL_FRAMES
    tail_factor = segment_id / 3.0
    tail_freq = SWIMMING_CONFIG['tail_wag_frequency']
    
    lateral_wag = math.sin(t * tail_freq * 2 * math.pi) * 0.25 * (1 + tail_factor)
    vertical_motion = math.sin(t * tail_freq * 2 * math.pi + math.pi/2) * 0.1 * tail_factor
    wave = math.sin(t * tail_freq * 2 * math.pi + tail_factor * math.pi) * 0.08 * tail_factor
    
    return (vertical_motion + wave, lateral_wag, wave * 0.5)


# ============================================================================
# PATA TRASERA DERECHA (BR = Back Right)
# ============================================================================

def calculate_rear_right_leg_swimming(frame):
    """
    shoulder.R - Pata trasera derecha (BR)
    - POSICIÓN DE PROPULSIÓN
    - Pertenece al Diagonal 2 (con FL)
    """
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    
    # BR está en Diagonal 2 (con FL)
    stroke_power = max(0, diag2)
    phase_offset = cycle + math.pi
    
    # Base: posición de propulsión
    base_pitch, base_yaw, base_roll = SWIMMING_CONFIG['shoulder_R']
    
    # Movimiento de brazada: variación sobre la base (OSCILACIÓN MÁXIMA)
    pitch_variation = -stroke_power * 0.65
    yaw_variation = math.sin(phase_offset) * 0.30 * stroke_power
    roll_variation = math.cos(phase_offset) * 0.20 * stroke_power
    
    return (base_pitch + pitch_variation, base_yaw + yaw_variation, base_roll + roll_variation)


def calculate_rear_right_thigh_swimming(frame):
    """
    thigh.R - Muslo pata trasera derecha
    - POSICIÓN DE PROPULSIÓN
    - CICLO DIAGONAL en X: sigue Diagonal 2 (con FL)
    """
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    
    # Muslo sigue Diagonal 2 (con FL)
    diagonal_power = max(0, diag2)
    phase_offset = cycle + math.pi
    
    # Base: posición de propulsión
    base_pitch, base_yaw, base_roll = SWIMMING_CONFIG['thigh_R']
    
    # Variación diagonal (OSCILACIÓN MÁXIMA)
    pitch_variation = diagonal_power * 0.70
    yaw_variation = math.sin(phase_offset + math.pi/4) * 0.15 * diagonal_power
    roll_variation = math.cos(phase_offset) * 0.12 * diagonal_power
    
    return (base_pitch + pitch_variation, base_yaw + yaw_variation, base_roll + roll_variation)


def calculate_rear_right_shin_swimming(frame):
    """
    shin.R - Espinilla pata trasera derecha
    - POSICIÓN DE PROPULSIÓN
    - FLEXIÓN en retorno, EXTENSIÓN en empuje
    - Pertenece al Diagonal 2
    """
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    
    stroke_power = max(0, diag2)
    phase = cycle + math.pi
    
    # Base: posición de propulsión
    base_pitch, base_yaw, base_roll = SWIMMING_CONFIG['shin_R']
    
    # Variación de brazada (OSCILACIÓN MÁXIMA)
    push_extend = -0.50 * max(0, math.sin(phase))
    return_flex = 0.40 * max(0, -math.sin(phase))
    pitch_variation = push_extend + return_flex
    
    yaw_variation = math.sin(phase) * 0.08 * stroke_power
    
    return (base_pitch + pitch_variation, base_yaw + yaw_variation, base_roll)


def calculate_rear_right_foot_swimming(frame):
    """foot.R - Pie pata trasera derecha - POSICIÓN DE PROPULSIÓN"""
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    stroke_power = max(0, diag2)
    phase = cycle + math.pi
    
    # Base: posición de propulsión
    base_pitch, base_yaw, base_roll = SWIMMING_CONFIG['foot_R']
    
    # Variación (OSCILACIÓN MÁXIMA)
    pitch_variation = stroke_power * 0.50
    roll_variation = math.sin(phase) * 0.10 * stroke_power
    
    return (base_pitch + pitch_variation, base_yaw, base_roll + roll_variation)


def calculate_rear_right_toe_swimming(frame):
    """toe.R - Dedos pata trasera derecha"""
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    stroke_power = max(0, diag2)
    phase = cycle + math.pi
    
    pitch = stroke_power * 0.15
    yaw = math.sin(phase) * 0.02 * stroke_power
    roll = 0
    
    return (pitch, yaw, roll)


# ============================================================================
# PATA TRASERA IZQUIERDA (BL = Back Left)
# ============================================================================

def calculate_rear_left_leg_swimming(frame):
    """
    shoulder.L - Pata trasera izquierda (BL)
    - POSICIÓN DE PROPULSIÓN
    - Pertenece al Diagonal 1 (con FR)
    """
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    
    # BL está en Diagonal 1 (con FR)
    stroke_power = max(0, diag1)
    phase_offset = cycle
    
    # Base: posición de propulsión
    base_pitch, base_yaw, base_roll = SWIMMING_CONFIG['shoulder_L']
    
    # Movimiento de brazada: variación sobre la base (OSCILACIÓN MÁXIMA)
    pitch_variation = -stroke_power * 0.65
    yaw_variation = math.sin(phase_offset) * 0.30 * stroke_power
    roll_variation = math.cos(phase_offset) * 0.20 * stroke_power
    
    return (base_pitch + pitch_variation, base_yaw + yaw_variation, base_roll + roll_variation)


def calculate_rear_left_thigh_swimming(frame):
    """
    thigh.L - Muslo pata trasera izquierda
    - POSICIÓN DE PROPULSIÓN
    - CICLO DIAGONAL en X: sigue Diagonal 1 (con FR)
    """
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    
    # Muslo sigue Diagonal 1 (con FR)
    diagonal_power = max(0, diag1)
    phase_offset = cycle
    
    # Base: posición de propulsión
    base_pitch, base_yaw, base_roll = SWIMMING_CONFIG['thigh_L']
    
    # Variación diagonal (OSCILACIÓN MÁXIMA)
    pitch_variation = diagonal_power * 0.70
    yaw_variation = -math.sin(phase_offset + math.pi/4) * 0.15 * diagonal_power
    roll_variation = -math.cos(phase_offset) * 0.12 * diagonal_power
    
    return (base_pitch + pitch_variation, base_yaw + yaw_variation, base_roll + roll_variation)


def calculate_rear_left_shin_swimming(frame):
    """
    shin.L - Espinilla pata trasera izquierda
    - POSICIÓN DE PROPULSIÓN
    - FLEXIÓN en retorno, EXTENSIÓN en empuje
    - Pertenece al Diagonal 1
    """
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    
    stroke_power = max(0, diag1)
    phase = cycle
    
    # Base: posición de propulsión
    base_pitch, base_yaw, base_roll = SWIMMING_CONFIG['shin_L']
    
    # Variación de brazada (OSCILACIÓN MÁXIMA)
    push_extend = -0.50 * max(0, math.sin(phase))
    return_flex = 0.40 * max(0, -math.sin(phase))
    pitch_variation = push_extend + return_flex
    
    yaw_variation = -math.sin(phase) * 0.08 * stroke_power
    
    return (base_pitch + pitch_variation, base_yaw + yaw_variation, base_roll)


def calculate_rear_left_foot_swimming(frame):
    """foot.L - Pie pata trasera izquierda - POSICIÓN DE PROPULSIÓN"""
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    stroke_power = max(0, diag1)
    phase = cycle
    
    # Base: posición de propulsión
    base_pitch, base_yaw, base_roll = SWIMMING_CONFIG['foot_L']
    
    # Variación (OSCILACIÓN MÁXIMA)
    pitch_variation = stroke_power * 0.50
    roll_variation = -math.sin(phase) * 0.10 * stroke_power
    
    return (base_pitch + pitch_variation, base_yaw, base_roll + roll_variation)


def calculate_rear_left_toe_swimming(frame):
    """toe.L - Dedos pata trasera izquierda"""
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    stroke_power = max(0, diag1)
    phase = cycle
    
    pitch = stroke_power * 0.15
    yaw = -math.sin(phase) * 0.02 * stroke_power
    roll = 0
    
    return (pitch, yaw, roll)


# ============================================================================
# PATA DELANTERA DERECHA (FR = Front Right)
# ============================================================================

def calculate_front_right_leg_swimming(frame):
    """
    front_shoulder.R - Pata delantera derecha (FR)
    - POSICIÓN DE REMO (paddling)
    - Pertenece al Diagonal 1 (con BL)
    """
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    
    # FR está en Diagonal 1 (con BL)
    stroke_power = max(0, diag1)
    phase_offset = cycle
    
    # Base: posición de remo
    base_pitch, base_yaw, base_roll = SWIMMING_CONFIG['front_shoulder_R']
    
    # Movimiento de brazada: variación sobre la base (OSCILACIÓN MÁXIMA)
    pitch_variation = -stroke_power * 0.55
    yaw_variation = math.sin(phase_offset) * 0.25 * stroke_power
    roll_variation = math.cos(phase_offset) * 0.15 * stroke_power
    
    return (base_pitch + pitch_variation, base_yaw + yaw_variation, base_roll + roll_variation)


def calculate_front_right_thigh_swimming(frame):
    """
    front_thigh.R - Muslo pata delantero derecha
    - POSICIÓN DE REMO
    - CICLO DIAGONAL en X: sigue Diagonal 1 (con BL)
    """
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    
    # Muslo sigue Diagonal 1 (con BL)
    diagonal_power = max(0, diag1)
    phase_offset = cycle
    
    # Base: posición de remo
    base_pitch, base_yaw, base_roll = SWIMMING_CONFIG['front_thigh_R']
    
    # Variación diagonal (OSCILACIÓN MÁXIMA)
    pitch_variation = diagonal_power * 0.50
    yaw_variation = math.sin(phase_offset + math.pi/4) * 0.12 * diagonal_power
    roll_variation = math.cos(phase_offset) * 0.10 * diagonal_power
    
    return (base_pitch + pitch_variation, base_yaw + yaw_variation, base_roll + roll_variation)


def calculate_front_right_shin_swimming(frame):
    """
    front_shin.R - Espinilla pata delantero derecha
    - POSICIÓN DE REMO
    - FLEXIÓN en retorno, EXTENSIÓN en empuje
    """
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    
    stroke_power = max(0, diag1)
    phase = cycle
    
    # Base: posición de remo
    base_pitch, base_yaw, base_roll = SWIMMING_CONFIG['front_shin_R']
    
    # Variación de brazada (OSCILACIÓN MÁXIMA)
    push_extend = -0.40 * max(0, math.sin(phase))
    return_flex = 0.30 * max(0, -math.sin(phase))
    pitch_variation = push_extend + return_flex
    
    yaw_variation = math.sin(phase) * 0.06 * stroke_power
    
    return (base_pitch + pitch_variation, base_yaw + yaw_variation, base_roll)


def calculate_front_right_foot_swimming(frame):
    """front_foot.R - Pie pata delantero derecha - POSICIÓN DE REMO"""
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    stroke_power = max(0, diag1)
    phase = cycle
    
    # Base: posición de remo
    base_pitch, base_yaw, base_roll = SWIMMING_CONFIG['front_foot_R']
    
    # Variación (OSCILACIÓN MÁXIMA)
    pitch_variation = stroke_power * 0.40
    roll_variation = math.sin(phase) * 0.08 * stroke_power
    
    return (base_pitch + pitch_variation, base_yaw, base_roll + roll_variation)


def calculate_front_right_toe_swimming(frame):
    """front_toe.R - Dedos pata delantero derecha - POSICIÓN DE REMO"""
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    stroke_power = max(0, diag1)
    phase = cycle
    
    # Base: posición de remo
    base_pitch, base_yaw, base_roll = SWIMMING_CONFIG['front_toe_R']
    
    pitch_variation = stroke_power * 0.08
    yaw_variation = math.sin(phase) * 0.01 * stroke_power
    
    return (base_pitch + pitch_variation, base_yaw + yaw_variation, base_roll)


# ============================================================================
# PATA DELANTERA IZQUIERDA (FL = Front Left)
# ============================================================================

def calculate_front_left_leg_swimming(frame):
    """
    front_shoulder.L - Pata delantero izquierda (FL)
    - Pertenece al Diagonal 2 (con BR)
    """
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    
    # FL está en Diagonal 2 (con BR)
    stroke_power = max(0, diag2)
    phase_offset = cycle + math.pi
    
    # Base: posición de remo
    base_pitch, base_yaw, base_roll = SWIMMING_CONFIG['front_shoulder_L']
    
    # Movimiento de brazada: variación sobre la base (OSCILACIÓN MÁXIMA)
    pitch_variation = -stroke_power * 0.55
    yaw_variation = math.sin(phase_offset) * 0.25 * stroke_power
    roll_variation = math.cos(phase_offset) * 0.15 * stroke_power
    
    return (base_pitch + pitch_variation, base_yaw + yaw_variation, base_roll + roll_variation)


def calculate_front_left_thigh_swimming(frame):
    """
    front_thigh.L - Muslo pata delantero izquierda
    - CICLO DIAGONAL en X: sigue Diagonal 2 (con BR)
    """
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    
    # Muslo sigue Diagonal 2 (con BR)
    diagonal_power = max(0, diag2)
    phase_offset = cycle + math.pi
    
    # Base: posición de remo
    base_pitch, base_yaw, base_roll = SWIMMING_CONFIG['front_thigh_L']
    
    # Variación diagonal (OSCILACIÓN MÁXIMA)
    pitch_variation = diagonal_power * 0.50
    yaw_variation = -math.sin(phase_offset + math.pi/4) * 0.12 * diagonal_power
    roll_variation = -math.cos(phase_offset) * 0.10 * diagonal_power
    
    return (base_pitch + pitch_variation, base_yaw + yaw_variation, base_roll + roll_variation)


def calculate_front_left_shin_swimming(frame):
    """
    front_shin.L - Espinilla pata delantero izquierda
    - FLEXIÓN en retorno, EXTENSIÓN en empuje
    - Pertenece al Diagonal 2
    """
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    
    stroke_power = max(0, diag2)
    phase = cycle + math.pi
    
    # Base: posición de remo
    base_pitch, base_yaw, base_roll = SWIMMING_CONFIG['front_shin_L']
    
    # Variación de brazada (OSCILACIÓN MÁXIMA)
    push_extend = -0.40 * max(0, math.sin(phase))
    return_flex = 0.30 * max(0, -math.sin(phase))
    pitch_variation = push_extend + return_flex
    
    yaw_variation = -math.sin(phase) * 0.06 * stroke_power
    
    return (base_pitch + pitch_variation, base_yaw + yaw_variation, base_roll)


def calculate_front_left_foot_swimming(frame):
    """front_foot.L - Pie pata delantero izquierda"""
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    stroke_power = max(0, diag2)
    phase = cycle + math.pi
    
    # Base: posición de remo
    base_pitch, base_yaw, base_roll = SWIMMING_CONFIG['front_foot_L']
    
    # Variación (OSCILACIÓN MÁXIMA)
    pitch_variation = stroke_power * 0.40
    roll_variation = -math.sin(phase) * 0.08 * stroke_power
    
    return (base_pitch + pitch_variation, base_yaw, base_roll + roll_variation)


def calculate_front_left_toe_swimming(frame):
    """front_toe.L - Dedos pata delantero izquierda"""
    t = frame / TOTAL_FRAMES
    paddle_freq = SWIMMING_CONFIG['paddle_frequency']
    
    diag1, diag2, cycle = calculate_diagonal_cycle(t, paddle_freq)
    stroke_power = max(0, diag2)
    phase = cycle + math.pi
    
    # Base: posición de remo
    base_pitch, base_yaw, base_roll = SWIMMING_CONFIG['front_toe_L']
    
    pitch_variation = stroke_power * 0.08
    yaw_variation = -math.sin(phase) * 0.01 * stroke_power
    
    return (base_pitch + pitch_variation, base_yaw + yaw_variation, base_roll)


# ============================================================================
# CONTROL BONES
# ============================================================================

def calculate_no_bone_movement(frame, bone_id):
    """Movimiento mínimo para bones de control"""
    t = frame / TOTAL_FRAMES
    amplitude = 0.002
    movement = math.sin(t * 2 * math.pi + bone_id) * amplitude
    return (movement, 0, 0)


# ============================================================================
# SISTEMA DE SUAVIZADO DE ROTACIÓN
# ============================================================================

class RotationSmoother:
    """Suaviza cambios de rotación para movimientos más naturales"""
    def __init__(self, smoothing_frames=12):
        self.smoothing_frames = smoothing_frames
        self.previous_rotation = None
        self.transition_start_frame = None
        self.transition_start_rotation = None
        self.target_rotation = None

    def smooth_rotation(self, target_rotation, current_frame):
        """Aplica suavizado a la rotación objetivo"""
        target_rotation = self._normalize_angle(target_rotation)

        if self.previous_rotation is None:
            self.previous_rotation = target_rotation
            return target_rotation

        angle_diff = self._angle_difference(target_rotation, self.previous_rotation)

        # Si el cambio es pequeño, aplicar directamente
        if abs(angle_diff) < 5:  # 5 grados de tolerancia
            self.previous_rotation = target_rotation
            self.transition_start_frame = None
            return target_rotation

        # Si hay un cambio significativo, iniciar transición suave
        if self.transition_start_frame is None:
            self.transition_start_frame = current_frame
            self.transition_start_rotation = self.previous_rotation
            self.target_rotation = target_rotation

        # Calcular progreso de la transición
        frames_elapsed = current_frame - self.transition_start_frame
        progress = min(frames_elapsed / self.smoothing_frames, 1.0)

        # Aplicar función de easing (smoothstep)
        eased_progress = self._smoothstep(progress)

        # Interpolar entre rotación inicial y objetivo
        smoothed_rotation = self.transition_start_rotation + angle_diff * eased_progress

        # Si la transición terminó, actualizar estado
        if progress >= 1.0:
            self.previous_rotation = target_rotation
            self.transition_start_frame = None
            return target_rotation

        return smoothed_rotation

    def _normalize_angle(self, angle):
        """Normaliza ángulo al rango [-180, 180]"""
        while angle > 180:
            angle -= 360
        while angle < -180:
            angle += 360
        return angle

    def _angle_difference(self, target, current):
        """Calcula la diferencia angular más corta considerando la discontinuidad en 360°"""
        diff = target - current
        while diff > 180:
            diff -= 360
        while diff < -180:
            diff += 360
        return diff

    def _smoothstep(self, x):
        """Función de easing smoothstep para transiciones naturales"""
        if x < 0:
            return 0
        if x > 1:
            return 1
        return x * x * (3 - 2 * x)


# Instancia global del suavizador de rotación
rotation_smoother = RotationSmoother(smoothing_frames=12)  # 12 frames = 0.5 segundos a 24fps


# ============================================================================
# DICCIONARIO DE FUNCIONES DE MOVIMIENTO POR BONE
# ============================================================================

BONE_FUNCTIONS = {
    # === COLUMNA VERTEBRAL (7 bones) - Onda viajera ===
    'spine_6': lambda f: apply_animation_phase(f, lambda af: calculate_spine_movement_swimming(af, 0)),
    'spine_7': lambda f: apply_animation_phase(f, lambda af: calculate_spine_movement_swimming(af, 1)),
    'spine_5': lambda f: apply_animation_phase(f, lambda af: calculate_spine_movement_swimming(af, 2)),
    'spine_4': lambda f: apply_animation_phase(f, lambda af: calculate_spine_movement_swimming(af, 3)),
    'spine_3': lambda f: apply_animation_phase(f, lambda af: calculate_spine_movement_swimming(af, 4)),
    'spine_2': lambda f: apply_animation_phase(f, lambda af: calculate_spine_movement_swimming(af, 5)),
    'spine_1': lambda f: apply_animation_phase(f, lambda af: calculate_spine_movement_swimming(af, 6)),

    # === CABEZA Y CARA (6 bones) - scull con +20° fijos ===
    'scull_1': lambda f: apply_animation_phase(f, lambda af: calculate_head_movement_swimming(af)),
    'scull': lambda f: apply_animation_phase(f, lambda af: calculate_scull_movement_swimming(af)),
    'ear.R': lambda f: apply_animation_phase(f, lambda af: calculate_ear_movement_swimming(af, 'R')),
    'ear.L': lambda f: apply_animation_phase(f, lambda af: calculate_ear_movement_swimming(af, 'L')),
    'jaw_top': lambda f: apply_animation_phase(f, lambda af: calculate_jaw_movement_swimming(af, True)),
    'jaw_bot': lambda f: apply_animation_phase(f, lambda af: calculate_jaw_movement_swimming(af, False)),

    # === COLA (3 bones) ===
    'tail_1': lambda f: apply_animation_phase(f, lambda af: calculate_tail_movement_swimming(af, 1)),
    'tail_2': lambda f: apply_animation_phase(f, lambda af: calculate_tail_movement_swimming(af, 2)),
    'tail_3': lambda f: apply_animation_phase(f, lambda af: calculate_tail_movement_swimming(af, 3)),

    # === PATA TRASERA DERECHA (BR = Back Right) - Diagonal 2 ===
    'shoulder.R': lambda f: apply_animation_phase(f, lambda af: calculate_rear_right_leg_swimming(af)),
    'thigh.R': lambda f: apply_animation_phase(f, lambda af: calculate_rear_right_thigh_swimming(af)),  # X diagonal
    'shin.R': lambda f: apply_animation_phase(f, lambda af: calculate_rear_right_shin_swimming(af)),    # Flex/ext
    'foot.R': lambda f: apply_animation_phase(f, lambda af: calculate_rear_right_foot_swimming(af)),
    'toe.R': lambda f: apply_animation_phase(f, lambda af: calculate_rear_right_toe_swimming(af)),

    # === PATA TRASERA IZQUIERDA (BL = Back Left) - Diagonal 1 ===
    'shoulder.L': lambda f: apply_animation_phase(f, lambda af: calculate_rear_left_leg_swimming(af)),
    'thigh.L': lambda f: apply_animation_phase(f, lambda af: calculate_rear_left_thigh_swimming(af)),   # X diagonal
    'shin.L': lambda f: apply_animation_phase(f, lambda af: calculate_rear_left_shin_swimming(af)),     # Flex/ext
    'foot.L': lambda f: apply_animation_phase(f, lambda af: calculate_rear_left_foot_swimming(af)),
    'toe.L': lambda f: apply_animation_phase(f, lambda af: calculate_rear_left_toe_swimming(af)),

    # === PATA DELANTERA DERECHA (FR = Front Right) - Diagonal 1 ===
    'front_shoulder.R': lambda f: apply_animation_phase(f, lambda af: calculate_front_right_leg_swimming(af)),
    'front_thigh.R': lambda f: apply_animation_phase(f, lambda af: calculate_front_right_thigh_swimming(af)),  # X diagonal
    'front_shin.R': lambda f: apply_animation_phase(f, lambda af: calculate_front_right_shin_swimming(af)),    # Flex/ext
    'front_foot.R': lambda f: apply_animation_phase(f, lambda af: calculate_front_right_foot_swimming(af)),
    'front_toe.R': lambda f: apply_animation_phase(f, lambda af: calculate_front_right_toe_swimming(af)),

    # === PATA DELANTERA IZQUIERDA (FL = Front Left) - Diagonal 2 ===
    'front_shoulder.L': lambda f: apply_animation_phase(f, lambda af: calculate_front_left_leg_swimming(af)),
    'front_thigh.L': lambda f: apply_animation_phase(f, lambda af: calculate_front_left_thigh_swimming(af)),   # X diagonal
    'front_shin.L': lambda f: apply_animation_phase(f, lambda af: calculate_front_left_shin_swimming(af)),     # Flex/ext
    'front_foot.L': lambda f: apply_animation_phase(f, lambda af: calculate_front_left_foot_swimming(af)),
    'front_toe.L': lambda f: apply_animation_phase(f, lambda af: calculate_front_left_toe_swimming(af)),

    # === CONTROL BONES (4 bones) ===
    'no_bone_01': lambda f: apply_animation_phase(f, lambda af: calculate_no_bone_movement(af, 1)),
    'no_bone_02': lambda f: apply_animation_phase(f, lambda af: calculate_no_bone_movement(af, 2)),
    'no_bone_03': lambda f: apply_animation_phase(f, lambda af: calculate_no_bone_movement(af, 3)),
    'no_bone_04': lambda f: apply_animation_phase(f, lambda af: calculate_no_bone_movement(af, 4)),
}



# ============================================
# SISTEMA DE PARPADEO CORREGIDO
#    - Reset automatico de ojos cuando no hay parpadeo activo
#    - Keyframes correctos en shape keys
#    - Debug mejorado
# ============================================

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

EYE_OBJECT_NAMES = ["ojo_izquierdo_jerry", "ojo_derecho_jerry"]


def _create_curtain_effect(eye_obj, shape_key):
    mesh = eye_obj.data
    vertices = [v.co for v in mesh.vertices]
    min_z = min(v.z for v in vertices)
    for i, vert in enumerate(mesh.vertices):
        new_co = vert.co.copy()
        new_co.z = min_z
        shape_key.data[i].co = new_co


def setup_blink_shape_keys():
    import bpy
    for obj_name in EYE_OBJECT_NAMES:
        eye_obj = bpy.data.objects.get(obj_name)
        if not eye_obj or eye_obj.type != "MESH":
            print(f"   setup_blink: WARNING '{obj_name}' no encontrado o no es mesh")
            continue
        if not eye_obj.data.shape_keys:
            eye_obj.shape_key_add(name="Basis", from_mix=False)
            print(f"   setup_blink: Basis creado en '{obj_name}'")
        existing = [sk.name for sk in eye_obj.data.shape_keys.key_blocks]
        if "Closed" not in existing:
            closed_key = eye_obj.shape_key_add(name="Closed", from_mix=False)
            _create_curtain_effect(eye_obj, closed_key)
            print(f"   setup_blink: Shape key 'Closed' creado en '{obj_name}'")
        else:
            print(f"   setup_blink: 'Closed' ya existe en '{obj_name}' -- OK")


def _apply_blink_phase(start_frame, end_frame):
    import bpy
    slot_duration = end_frame - start_frame + 1
    blink_starts = [
        start_frame + int(slot_duration * 0.33),
        start_frame + int(slot_duration * 0.66),
    ]
    print(f"   Parpadeos programados en frames: {blink_starts}")
    setup_blink_shape_keys()
    for t in range(start_frame, end_frame + 1):
        blink_applied = False
        for blink_start in blink_starts:
            if blink_start <= t < blink_start + 9:
                blink_applied = True
                offset = t - blink_start + 1
                frame_data = BLINK_SEQUENCE.get(offset, {"closed": 0.0, "hide": False})
                progress = frame_data["closed"]
                hide_eye = frame_data["hide"]
                print(f"   Parpadeo frame {t} (offset {offset}, progreso {progress:.2f})")
                for obj_name in EYE_OBJECT_NAMES:
                    eye = bpy.data.objects.get(obj_name)
                    if eye and hasattr(eye.data, "shape_keys") and eye.data.shape_keys:
                        ck = eye.data.shape_keys.key_blocks.get("Closed")
                        if ck:
                            ck.value = progress
                            ck.keyframe_insert(data_path="value", frame=t)
                            eye.hide_viewport = hide_eye
                            eye.hide_render = hide_eye
                            eye.keyframe_insert(data_path="hide_viewport", frame=t)
                            eye.keyframe_insert(data_path="hide_render", frame=t)
                break
        # RESET AUTOMATICO: ojos abiertos cuando no hay parpadeo activo
        if not blink_applied:
            for obj_name in EYE_OBJECT_NAMES:
                eye = bpy.data.objects.get(obj_name)
                if eye and hasattr(eye.data, "shape_keys") and eye.data.shape_keys:
                    ck = eye.data.shape_keys.key_blocks.get("Closed")
                    if ck:
                        ck.value = 0.0
                        ck.keyframe_insert(data_path="value", frame=t)
                        eye.hide_viewport = False
                        eye.hide_render = False
                        eye.keyframe_insert(data_path="hide_viewport", frame=t)
                        eye.keyframe_insert(data_path="hide_render", frame=t)
    print(f"   Fase parpadeo completada: frames {start_frame}->{end_frame}")

def execute_animation(player_parts, start_frame=1, end_frame=120):
    """Ejecuta la animación de nadar/caminar para Jerry Dog"""
    armature = player_parts.get('body')

    if not armature:
        print("❌ Error: No se encontró la parte 'body' (armature)")
        return False

    if not hasattr(armature, 'type') or armature.type != 'ARMATURE':
        print("❌ Error: La parte 'body' no es un Armature válido")
        return False

    # Asegurar que animation_data existe
    if not armature.animation_data:
        armature.animation_data_create()

    # ============================================================
    # SISTEMA NLA CORRECTO - Preserva animaciones anteriores
    # ============================================================
    # NO limpiamos animation_data.action ni nla_tracks existentes
    
    # Crear nueva acción
    action_name = ANIMATION_INFO.get('name', f'slot_{SLOT_INDEX}_animation')
    action = bpy.data.actions.new(name=action_name)
    
    # Crear NLA track para este slot
    nla_track = armature.animation_data.nla_tracks.new()
    nla_track.name = f"Slot_{SLOT_INDEX}"
    
    # Crear strip en el NLA track
    nla_strip = nla_track.strips.new(action_name, start_frame, action)
    nla_strip.frame_end = end_frame

    # ============================================================
    # APLICAR DESPLAZAMIENTO (TRAYECTORIA EMBEBIDA)
    # ============================================================
    trajectory = ANIMATION_INFO.get('trajectory', [])
    
    if trajectory:
        print(f"🐕 Aplicando trayectoria: {len(trajectory)} puntos")
        
        # Buscar el objeto root de Jerry (puede ser mesh o empty)
        root_obj = None
        for obj in bpy.data.objects:
            if obj.type in ['MESH', 'EMPTY'] and "jerry" in obj.name.lower():
                if "armature" not in obj.name.lower():
                    root_obj = obj
                    print(f"   📍 Root encontrado: {root_obj.name}")
                    break
        
        if not root_obj:
            # Usar el armature como root si no hay otro objeto
            root_obj = armature
            print(f"   📍 Usando armature como root: {root_obj.name}")
        
        # Aplicar keyframes de ubicación y rotación suavizada
        for i, point in enumerate(trajectory):
            coords = point.get('coordinates', {})
            x = coords.get('x', 0)
            y = coords.get('y', 0)
            z = coords.get('z', 0)
            
            # Calcular frame para este punto (distribuir a lo largo del slot)
            points_count = len(trajectory)
            frame_progress = i / (points_count - 1) if points_count > 1 else 0
            point_frame = int(start_frame + frame_progress * (end_frame - start_frame))
            
            # Insertar keyframe de ubicación
            root_obj.location = (x, y, z)
            root_obj.keyframe_insert(data_path="location", frame=point_frame)
            
            # Calcular rotación basada en la dirección del movimiento
            if i < len(trajectory) - 1:
                next_coords = trajectory[i + 1].get('coordinates', {})
                dx = next_coords.get('x', x) - x
                dy = next_coords.get('y', y) - y
                
                # Calcular ángulo de rotación
                ang = math.degrees(math.atan2(dx, dy))
                
                # ✅ LÓGICA CONDICIONAL: Detectar cardinales vs diagonales
                ang_rounded = round(ang / 90.0) * 90.0
                ang_diff = abs(ang - ang_rounded)
                
                if ang_diff < 45:
                    # Movimiento cardinal: usar ángulo redondeado
                    ang = ang_rounded
                else:
                    # Movimiento diagonal: invertir dirección
                    ang = -ang
                
                # Normalización de ángulo
                while ang > 180:
                    ang -= 360
                while ang < -180:
                    ang += 360
                
                # Corrección de Blender (eje Y invertido)
                if ang == 90:
                    ang = -90
                elif ang == -90:
                    ang = 90
                
                # ✅ APLICAR SUAVIZADO DE ROTACIÓN
                smoothed_ang = rotation_smoother.smooth_rotation(ang, point_frame)
                root_obj.rotation_euler = (0, 0, math.radians(smoothed_ang))
                root_obj.keyframe_insert(data_path="rotation_euler", frame=point_frame)
            else:
                # Último punto: mantener la última rotación
                root_obj.keyframe_insert(data_path="rotation_euler", frame=point_frame)
            
        print(f"   ✅ Trayectoria aplicada: {len(trajectory)} keyframes con rotación suavizada")
    else:
        print("   ⚠️ No hay trayectoria definida en ANIMATION_INFO")
    
    if armature.mode != 'POSE':
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='POSE')

    print(f"✅ Armature encontrado: {armature.name}")
    print(f"🔢 Generando animación para {len(BONE_FUNCTIONS)} bones")
    print(f"📊 Slot {SLOT_INDEX}: Frames {start_frame}-{end_frame}")

    bones_applied = 0
    bones_missing = []

    for bone_name, movement_func in BONE_FUNCTIONS.items():
        bone = armature.pose.bones.get(bone_name)
        if not bone:
            bones_missing.append(bone_name)
            continue

        bone.rotation_mode = 'XYZ'

        for frame in range(1, TOTAL_FRAMES + 1):
            adjusted_frame = start_frame + (frame - 1)
            rotation = movement_func(frame)
            bone.rotation_euler = rotation
            bone.keyframe_insert(data_path="rotation_euler", frame=adjusted_frame)

        bones_applied += 1

    if bones_missing:
        print(f"⚠️ Bones no encontrados: {len(bones_missing)}")
        for bone in bones_missing[:5]:
            print(f"   - {bone}")

    print(f"✅ Keyframes aplicados a {bones_applied} bones")

    # Configurar interpolación BEZIER
    if armature.animation_data and armature.animation_data.action:
        for fcurve in _action_fcurves(armature.animation_data.action):
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = 'BEZIER'
                keyframe.easing = 'AUTO'

    print("\n" + "=" * 70)
    print(f"✅ ANIMACIÓN APLICADA - Slot {SLOT_INDEX}")
    print("=" * 70)
    print(f"   📊 Frames: {start_frame}-{end_frame} ({TOTAL_FRAMES} frames)")
    print(f"   🦴 Bones: {bones_applied} animados")
    print(f"   🐕 Sistema: Jerry Dog")
    print(f"   🔢 Método: Funciones Trigonométricas")
    print(f"   🎯 Sistema NLA: Slot_{SLOT_INDEX} creado correctamente")
    trajectory_count = len(ANIMATION_INFO.get('trajectory', []))
    print(f"   📍 Trayectoria: {trajectory_count} puntos con rotación suavizada")
    print(f"   🔄 Suavizado: 12 frames (smoothstep) para transiciones naturales")
    print("=" * 70)

    # ============================================
    # FASE PARPADEO - Sistema de parpadeo corregido
    # ============================================
    print("\nIniciando sistema de parpadeo corregido...")
    _apply_blink_phase(start_frame, end_frame)


    return True


def get_animation_metadata():
    """Retorna metadata de la animación"""
    return {
        'slot': SLOT_INDEX,
        'type': 'walking_plains',
        'requires_previous_slot': False,
        'minecraft_equivalent': 'Dog swimming ocean',
        'rig_type': 'quadruped_hierarchy',
        'source': 'jerry_dog_rig_mathematical',
        'bones_count': 40,
        'animation_type': 'mathematical',
        'character_type': 'dog',
        'generation_method': 'trigonometric_functions',
        'data_source': 'jerry_outliner_data.json',
        'complete_rig_coverage': True,
        'swimming_style': 'dog_paddle',
        'environment': 'ocean',
        'paddle_frequency_hz': SWIMMING_CONFIG['paddle_frequency'],
        'spine_wave_frequency_hz': SWIMMING_CONFIG['spine_wave_frequency'],
        'entry_frames': 10,
        'exit_frames': 10,
        'main_animation_frames': 100,
        'total_frames': 120,
        'modifications': {
            'thigh_rotation_x_diagonal': True,
            'front_thigh_rotation_x_diagonal': True,
            'shin_flex_extend_cycle': True,
            'front_shin_flex_extend_cycle': True,
            'scull_fixed_pitch_degrees': 20,
            'spine_traveling_wave': True
        }
    }


if __name__ == "__main__":
    armature_obj = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and ("jerry" in obj.name.lower() or "dog" in obj.name.lower()):
            armature_obj = obj
            break

    if not armature_obj:
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature_obj = obj
                break

    if armature_obj:
        player_parts = {'body': armature_obj}
        execute_animation(player_parts, start_frame=START_FRAME, end_frame=END_FRAME)
    else:
        print("❌ Error: No se encontró el armature de Jerry/Dog")
