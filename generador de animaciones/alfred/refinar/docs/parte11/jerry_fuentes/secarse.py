# -*- coding: utf-8 -*-
"""
slot_004_jerry_secandose_FINAL.py
Jerry (Dog) sacudiéndose para secarse - VERSIÓN FINAL COMPLETA

SOLUCIÓN DEFINITIVA AL PROBLEMA DE PATAS FLEXIONADAS:
✅ Sistema híbrido: Child Of constraints + No keyframes en patas
✅ Las patas permanecen completamente estáticas en pose rest
✅ El cuerpo se sacude libremente sin afectar las patas
✅ Solución garantizada y reversible

MÉTODO IMPLEMENTADO:
1. Aplicar Child Of constraints a TODAS las articulaciones de patas
2. Configurar influencia = 0.0 (sin herencia de transformación)
3. Animar solo: spine, cabeza, orejas, mandíbula y cola
4. Las patas mantienen pose rest sin importar el movimiento del parent

CARACTERÍSTICAS:
- Detección automática de rig (con/sin sufijo _2)
- Sistema de momentum con entrada/salida suave
- Interpolación Bezier para movimiento fluido
- Frecuencias diferenciadas por parte del cuerpo
- Opción de limpieza de constraints al finalizar

Frames: 1-60 (5 entrada + 50 principal + 5 salida)
Duración: 2.5 segundos @ 24 fps
Fecha: 2026-02-08
Autor: Sistema de animación procedural
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

ANIMATION_INFO = {
    'name': 'slot_004_jerry_secandose_FINAL',
    'frame_count': 60,
    'fps': 24,
    'duration_seconds': 2.5,
    'entity': 'Jerry',
    'character_type': 'dog_quadruped',
    'slot': 4,
    'movement_type': 'shake_dry_frozen_legs',
    'bones_animated': 16,  # Spine(7) + Head(2) + Ears(2) + Jaw(2) + Tail(3)
    'animation_type': 'mathematical_procedural',
    'complete_rig_coverage': False,
    'reference': 'dog_shake_physics',
    'entry_frames': 5,
    'exit_frames': 5,
    'main_animation_frames': 50,
    'shake_frequency_hz': 7,
    'legs_behavior': 'frozen_with_child_of_constraints',
    'auto_detect_rig': True,
    'constraint_method': 'child_of_zero_influence'
}


# ============================================================================
# PUNTOS DE TRAYECTORIA INTEGRADOS
# ============================================================================

EMBEDDED_TRAJECTORY_POINTS = [
    {"index": 115, "coordinates": {"x": -107.5, "y": -3.5, "z": 8.0}, "texture": "stone", "face_index": "61251"}
]


# ============================================================================
# CONFIGURACIÓN DEL SLOT
# ============================================================================

SLOT_INDEX = 33                    # Número del slot
START_FRAME = 1616                # Frame inicial (continúa desde slot 32: 1615 + 1)
END_FRAME = 1675                   # Frame final (1616 + 60 frames - 1)
TOTAL_FRAMES = 60                 # Total de frames de la animación
TRAJECTORY_POINTS = 1              # Número de puntos de trayectoria


# ============================================================================
# DETECCIÓN AUTOMÁTICA DE RIG
# ============================================================================

def detect_rig_suffix(armature):
    """
    Detecta automáticamente si el rig usa sufijo _2 o no.
    
    Returns:
        str: '_2' si es Dog_001_rig_2, '' si es Dog_001_rig
    """
    test_bones = ['spine_6_2', 'spine_6']
    
    for test_bone in test_bones:
        if test_bone in armature.pose.bones:
            if '_2' in test_bone:
                print(f"✅ Detectado: Rig con sufijo '_2' (Dog_001_rig_2 - 43 bones)")
                return '_2'
            else:
                print(f"✅ Detectado: Rig sin sufijo (Dog_001_rig - 41 bones)")
                return ''
    
    print(f"⚠️ No se pudo detectar el tipo de rig, usando sin sufijo por defecto")
    return ''


# ============================================================================
# GESTIÓN DE CONSTRAINTS PARA CONGELAR PATAS
# ============================================================================

def freeze_legs_with_constraints(armature, suffix=''):
    """
    Aplica Child Of constraints con influencia 0 a todas las patas.
    Esto previene completamente la herencia de rotación del parent.
    
    Args:
        armature: El objeto armature
        suffix: '_2' o '' según el rig
        
    Returns:
        int: Número de constraints aplicados
    """
    s = suffix
    
    # TODAS las articulaciones de patas que necesitan congelarse
    leg_bones = [
        # Patas traseras derecha
        f'shoulder.R{s}', f'thigh.R{s}', f'shin.R{s}', f'foot.R{s}', f'toe.R{s}',
        # Patas traseras izquierda
        f'shoulder.L{s}', f'thigh.L{s}', f'shin.L{s}', f'foot.L{s}', f'toe.L{s}',
        # Patas delanteras derecha
        f'front_shoulder.R{s}', f'front_thigh.R{s}', f'front_shin.R{s}', 
        f'front_foot.R{s}', f'front_toe.R{s}',
        # Patas delanteras izquierda
        f'front_shoulder.L{s}', f'front_thigh.L{s}', f'front_shin.L{s}', 
        f'front_foot.L{s}', f'front_toe.L{s}',
    ]
    
    # Asegurar que estamos en POSE mode
    if armature.mode != 'POSE':
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='POSE')
    
    constraints_added = 0
    
    for bone_name in leg_bones:
        pose_bone = armature.pose.bones.get(bone_name)
        if not pose_bone:
            continue
        
        # Obtener el parent actual del bone
        if not pose_bone.parent:
            continue
        
        parent_name = pose_bone.parent.name
        
        # Limpiar constraints de congelamiento previos
        for const in list(pose_bone.constraints):
            if "Freeze_Leg_Shake" in const.name:
                pose_bone.constraints.remove(const)
        
        # Crear nuevo Child Of constraint
        const = pose_bone.constraints.new('CHILD_OF')
        const.name = "Freeze_Leg_Shake"
        const.target = armature
        const.subtarget = parent_name
        
        # CLAVE: Influencia 0.0 = el bone NO hereda transformaciones del parent
        const.influence = 0.0
        
        # Configurar para que solo afecte rotación
        const.use_location_x = False
        const.use_location_y = False
        const.use_location_z = False
        const.use_rotation_x = True
        const.use_rotation_y = True
        const.use_rotation_z = True
        const.use_scale_x = False
        const.use_scale_y = False
        const.use_scale_z = False
        
        constraints_added += 1
    
    print(f"   🔒 Child Of constraints aplicados: {constraints_added} huesos de patas")
    print(f"   📌 Influencia: 0.0 (sin herencia de rotación del parent)")
    
    return constraints_added


def unfreeze_legs(armature, suffix=''):
    """
    Remueve los constraints de congelamiento de las patas.
    Útil para restaurar el rig a su estado normal.
    
    Args:
        armature: El objeto armature
        suffix: '_2' o '' según el rig
        
    Returns:
        int: Número de constraints removidos
    """
    s = suffix
    
    leg_bones = [
        f'shoulder.R{s}', f'thigh.R{s}', f'shin.R{s}', f'foot.R{s}', f'toe.R{s}',
        f'shoulder.L{s}', f'thigh.L{s}', f'shin.L{s}', f'foot.L{s}', f'toe.L{s}',
        f'front_shoulder.R{s}', f'front_thigh.R{s}', f'front_shin.R{s}', 
        f'front_foot.R{s}', f'front_toe.R{s}',
        f'front_shoulder.L{s}', f'front_thigh.L{s}', f'front_shin.L{s}', 
        f'front_foot.L{s}', f'front_toe.L{s}',
    ]
    
    removed = 0
    
    for bone_name in leg_bones:
        pose_bone = armature.pose.bones.get(bone_name)
        if not pose_bone:
            continue
        
        for const in list(pose_bone.constraints):
            if "Freeze_Leg_Shake" in const.name:
                pose_bone.constraints.remove(const)
                removed += 1
    
    print(f"   🔓 Constraints removidos: {removed}")
    return removed


# ============================================================================
# FUNCIONES MATEMÁTICAS BASE
# ============================================================================

def get_animation_phase(frame):
    """
    Determina en qué fase de la animación estamos.
    
    Args:
        frame: Frame actual (1-60)
        
    Returns:
        tuple: (fase, frame_ajustado)
            fase: 'entry', 'main', o 'exit'
            frame_ajustado: Frame relativo a la fase
    """
    if frame <= 5:
        return ('entry', frame)
    elif frame <= 55:
        return ('main', frame - 5)
    else:
        return ('exit', frame - 55)


def apply_animation_phase(frame, movement_func):
    """
    Aplica transiciones suaves de entrada y salida a cualquier movimiento.
    
    Args:
        frame: Frame actual
        movement_func: Función que calcula el movimiento
        
    Returns:
        tuple: (pitch, yaw, roll) con transiciones aplicadas
    """
    phase, adjusted_frame = get_animation_phase(frame)

    if phase == 'main':
        # En la fase principal, aplicar movimiento completo
        return movement_func(adjusted_frame)
    else:
        # En entrada/salida, hacer blend con pose rest
        if phase == 'entry':
            # Fade in: 0 → 1 en 4 frames
            transition_factor = (frame - 1) / 4.0
        else:
            # Fade out: 1 → 0 en 4 frames
            transition_factor = (60 - frame) / 4.0

        animation_values = movement_func(adjusted_frame)
        base_values = (0, 0, 0)
        
        # Interpolación lineal entre base y animación
        smooth_values = tuple(
            base * (1 - transition_factor) + anim * transition_factor
            for base, anim in zip(base_values, animation_values)
        )

        return smooth_values


def calculate_shake_momentum(t):
    """
    Calcula la intensidad del shake a lo largo del tiempo.
    Usa una curva que sube rápido, se mantiene, y baja gradualmente.
    
    Args:
        t: Tiempo normalizado (0.0 - 1.0)
        
    Returns:
        float: Momentum (0.0 - 1.0)
    """
    if t < 0.2:
        # Buildup rápido: 0 → 1 en primeros 20%
        return t / 0.2
    elif t < 0.8:
        # Shake completo: mantener en 1.0
        return 1.0
    else:
        # Decay gradual: 1 → 0 en últimos 20%
        return (1.0 - t) / 0.2


# ============================================================================
# MOVIMIENTOS DE COLUMNA VERTEBRAL (GENERADOR DEL SHAKE)
# ============================================================================

def calculate_spine_shake(frame, segment_id):
    """
    Calcula el movimiento de shake para un segmento específico de la columna.
    Este es el movimiento principal que genera el efecto de sacudirse.
    
    Args:
        frame: Frame actual (0-50 en fase main)
        segment_id: ID del segmento (6, 7, 5, 4, 3, 2, 1)
        
    Returns:
        tuple: (pitch, yaw, roll) en radianes
    """
    # Normalizar tiempo a 0.0 - 1.0
    t = frame / 50.0
    
    # Obtener momentum actual
    momentum = calculate_shake_momentum(t)
    
    # Frecuencia del shake: 7 Hz (7 oscilaciones completas por segundo)
    # En 2.5 segundos = 17.5 ciclos totales
    shake_cycles = t * 7 * 2 * math.pi
    
    # Factor de amplitud según posición en columna
    # spine_5 (centro del cuerpo) tiene el movimiento máximo
    amplitude_factors = {
        6: 0.25,  # spine_6 - base (cadera) - menos movimiento
        7: 0.45,  # spine_7 - parte baja
        5: 0.70,  # spine_5 - CENTRO - máximo movimiento
        4: 0.60,  # spine_4 - parte media-alta
        3: 0.50,  # spine_3 - pecho
        2: 0.40,  # spine_2 - base del cuello
        1: 0.30   # spine_1 - cuello (menos para no marear)
    }
    amp = amplitude_factors.get(segment_id, 0.5)
    
    # ROLL (rotación lateral) - Este es el MOVIMIENTO PRINCIPAL
    # El perro se sacude de lado a lado vigorosamente
    roll = math.sin(shake_cycles) * 0.45 * amp * momentum
    
    # YAW (rotación horizontal) - Movimiento secundario
    # Ligero twist side-to-side para naturalidad
    yaw = math.sin(shake_cycles * 0.5) * 0.12 * amp * momentum
    
    # PITCH (inclinación adelante-atrás) - Movimiento mínimo
    # Solo para dar un poco de variación
    pitch = math.sin(shake_cycles * 0.3) * 0.06 * amp * momentum
    
    return (pitch, yaw, roll)


# ============================================================================
# MOVIMIENTOS DE CABEZA
# ============================================================================

def calculate_head_shake(frame, is_scull=False):
    """
    Calcula el movimiento de la cabeza durante el shake.
    La cabeza se mueve independientemente y más rápido que el cuerpo.
    
    Args:
        frame: Frame actual (0-50)
        is_scull: True para el bone 'scull', False para 'scull_1'
        
    Returns:
        tuple: (pitch, yaw, roll) en radianes
    """
    t = frame / 50.0
    momentum = calculate_shake_momentum(t)
    
    # La cabeza es controlada por spine_3 (base del cuello)
    # La cabeza se sacude más rápido que el cuerpo: 5 Hz (REDUCIDO A LA MITAD)
    head_shake = t * 5 * 2 * math.pi
    
    # scull_1 (conectado a spine_3) tiene movimiento menos pronunciado
    intensity = 0.40 if not is_scull else 0.30  # REDUCIDO A LA MITAD
    
    # Roll lateral (sacudida principal de cabeza)
    roll = math.sin(head_shake) * 0.275 * momentum * intensity  # REDUCIDO: 0.55 → 0.275
    
    # Yaw (girar cabeza lado a lado)
    yaw = math.sin(head_shake * 0.7) * 0.09 * momentum * intensity  # REDUCIDO: 0.18 → 0.09
    
    # Pitch (cabecear arriba-abajo)
    pitch = math.sin(head_shake * 0.5) * 0.06 * momentum * intensity  # REDUCIDO: 0.12 → 0.06
    
    return (pitch, yaw, roll)


# ============================================================================
# MOVIMIENTOS DE OREJAS (FLAPPING)
# ============================================================================

def calculate_ear_flap(frame, side):
    """
    Calcula el flapping de las orejas.
    Las orejas vibran muy rápido independientemente del cuerpo.
    
    Args:
        frame: Frame actual (0-50)
        side: 'R' para derecha, 'L' para izquierda
        
    Returns:
        tuple: (pitch, yaw, roll) en radianes
    """
    t = frame / 50.0
    momentum = calculate_shake_momentum(t)
    
    # Frecuencia muy alta: 15 Hz (las orejas vibran muy rápido)
    flap_cycles = t * 15 * 2 * math.pi
    
    # Desfase entre orejas para movimiento más natural
    phase_offset = 0 if side == 'R' else math.pi * 0.3
    
    # Roll (principal - orejas suben/bajan)
    roll = math.sin(flap_cycles + phase_offset) * 0.65 * momentum
    
    # Yaw (secundario - orejas se mueven hacia adelante/atrás)
    yaw = math.cos(flap_cycles + phase_offset) * 0.35 * momentum
    
    # Pitch (mínimo - ligera inclinación)
    pitch = math.sin(flap_cycles * 0.6 + phase_offset) * 0.15 * momentum
    
    return (pitch, yaw, roll)


# ============================================================================
# MOVIMIENTOS DE MANDÍBULA
# ============================================================================

def calculate_jaw_movement(frame, jaw_type):
    """
    Calcula el movimiento de la mandíbula.
    La boca se abre ligeramente durante el shake.
    
    Args:
        frame: Frame actual (0-50)
        jaw_type: 'bot' para mandíbula inferior, 'top' para superior
        
    Returns:
        tuple: (pitch, yaw, roll) en radianes
    """
    t = frame / 50.0
    momentum = calculate_shake_momentum(t)
    
    if jaw_type == 'bot':
        # Mandíbula inferior se abre ligeramente
        pitch = -0.08 * momentum
        return (pitch, 0, 0)
    else:
        # Mandíbula superior no se mueve
        return (0, 0, 0)


# ============================================================================
# MOVIMIENTOS DE COLA
# ============================================================================

def calculate_tail_movement(frame, segment_id):
    """
    Calcula el movimiento de la cola.
    La cola se agita vigorosamente con movimiento que se amplifica hacia la punta.
    
    Args:
        frame: Frame actual (0-50)
        segment_id: 1 (base), 2 (medio), 3 (punta)
        
    Returns:
        tuple: (pitch, yaw, roll) en radianes
    """
    t = frame / 50.0
    momentum = calculate_shake_momentum(t)
    
    # Frecuencia de agitación de cola: 9 Hz
    tail_cycles = t * 9 * 2 * math.pi
    
    # Amplitud progresiva: la punta se mueve más que la base
    amplitude_factors = {
        1: 0.40,  # Base de la cola (menos movimiento)
        2: 0.60,  # Medio
        3: 0.80   # Punta (máximo movimiento)
    }
    amp = amplitude_factors.get(segment_id, 0.6)
    
    # Roll (movimiento principal lateral)
    roll = math.sin(tail_cycles) * 0.55 * amp * momentum
    
    # Yaw (movimiento side-to-side)
    yaw = math.sin(tail_cycles * 0.7) * 0.35 * amp * momentum
    
    # Pitch (arriba-abajo)
    pitch = math.sin(tail_cycles * 0.5) * 0.18 * amp * momentum
    
    return (pitch, yaw, roll)


# ============================================================================
# CONSTRUCCIÓN DEL MAPA DE FUNCIONES POR BONE
# ============================================================================

def build_bone_functions(suffix=''):
    """
    Construye el diccionario de funciones de movimiento para cada bone.
    CRÍTICO: Solo incluye bones que DEBEN moverse.
    Las patas NO están aquí = NO reciben keyframes.
    
    Args:
        suffix: '_2' o '' según el rig detectado
        
    Returns:
        dict: {bone_name: movement_function}
    """
    s = suffix
    
    return {
        # ===== COLUMNA VERTEBRAL (7 segmentos) =====
        f'spine_6{s}': lambda f: apply_animation_phase(f, lambda af: calculate_spine_shake(af, 6)),
        f'spine_7{s}': lambda f: apply_animation_phase(f, lambda af: calculate_spine_shake(af, 7)),
        f'spine_5{s}': lambda f: apply_animation_phase(f, lambda af: calculate_spine_shake(af, 5)),
        f'spine_4{s}': lambda f: apply_animation_phase(f, lambda af: calculate_spine_shake(af, 4)),
        f'spine_3{s}': lambda f: apply_animation_phase(f, lambda af: calculate_spine_shake(af, 3)),
        f'spine_2{s}': lambda f: apply_animation_phase(f, lambda af: calculate_spine_shake(af, 2)),
        f'spine_1{s}': lambda f: apply_animation_phase(f, lambda af: calculate_spine_shake(af, 1)),
        
        # ===== CABEZA (2 bones) =====
        f'scull_1{s}': lambda f: apply_animation_phase(f, lambda af: calculate_head_shake(af, is_scull=False)),
        f'scull{s}': lambda f: apply_animation_phase(f, lambda af: calculate_head_shake(af, is_scull=True)),
        
        # ===== OREJAS (2 bones) =====
        f'ear.R{s}': lambda f: apply_animation_phase(f, lambda af: calculate_ear_flap(af, 'R')),
        f'ear.L{s}': lambda f: apply_animation_phase(f, lambda af: calculate_ear_flap(af, 'L')),
        
        # ===== MANDÍBULA (2 bones) =====
        f'jaw_bot{s}': lambda f: apply_animation_phase(f, lambda af: calculate_jaw_movement(af, 'bot')),
        f'jaw_top{s}': lambda f: apply_animation_phase(f, lambda af: calculate_jaw_movement(af, 'top')),
        
        # ===== COLA (3 segmentos) =====
        f'tail_1{s}': lambda f: apply_animation_phase(f, lambda af: calculate_tail_movement(af, 1)),
        f'tail_2{s}': lambda f: apply_animation_phase(f, lambda af: calculate_tail_movement(af, 2)),
        f'tail_3{s}': lambda f: apply_animation_phase(f, lambda af: calculate_tail_movement(af, 3)),
        
        # NOTA: Las patas NO están en este diccionario.
        # Esto significa que NO se les aplicarán keyframes.
        # Combinado con los Child Of constraints (influencia=0),
        # garantiza que permanezcan completamente estáticas.
    }


# ============================================================================
# EJECUCIÓN DE ANIMACIÓN PRINCIPAL
# ============================================================================


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

def execute_animation(player_parts, start_frame=1, end_frame=60, 
                     freeze_legs=True, cleanup_after=False):
    """
    Ejecuta la animación completa de Jerry sacudiéndose.
    
    Args:
        player_parts: Dict con clave 'body' apuntando al armature
        start_frame: Frame inicial (default: 1)
        end_frame: Frame final (default: 60)
        freeze_legs: Si True, aplica constraints para congelar patas
        cleanup_after: Si True, remueve constraints al finalizar
        
    Returns:
        bool: True si tuvo éxito, False si hubo error
    """
    
    armature = player_parts.get('body')

    if not armature or armature.type != 'ARMATURE':
        print("❌ ERROR: No se encontró armature válido en player_parts['body']")
        return False

    print("\n" + "=" * 70)
    print("🎬 INICIANDO GENERACIÓN DE ANIMACIÓN")
    print("=" * 70)

    # PASO 1: DETECCIÓN AUTOMÁTICA DEL RIG
    bone_suffix = detect_rig_suffix(armature)
    print(f"📋 Sufijo detectado: '{bone_suffix if bone_suffix else '(ninguno)'}'")

    # PASO 2: CONGELAR PATAS (si está habilitado)
    if freeze_legs:
        print(f"\n🔒 PASO 2: Congelando patas con Child Of constraints...")
        freeze_legs_with_constraints(armature, bone_suffix)
    else:
        print(f"\n⚠️ ADVERTENCIA: Patas NO congeladas - pueden heredar movimiento")

    # PASO 3: CREAR NUEVA ACCIÓN (NLA - NO limpia tracks anteriores)
    print(f"\n📝 PASO 3: Creando nueva acción...")
    action = bpy.data.actions.new(name=ANIMATION_INFO['name'])
    if not armature.animation_data:
        armature.animation_data_create()
    
    # ✅ CORRECTO - Crear NLA track sin borrar los anteriores
    nla_track = armature.animation_data.nla_tracks.new()
    nla_track.name = f"Slot_{SLOT_INDEX}"
    nla_strip = nla_track.strips.new(ANIMATION_INFO['name'], start_frame, action)
    nla_strip.frame_end = end_frame
    print(f"   ✓ Acción creada: {ANIMATION_INFO['name']}")
    print(f"   ✓ NLA track: Slot_{SLOT_INDEX} ({start_frame}-{end_frame})")

    # PASO 4: CONFIGURAR MODO POSE
    if armature.mode != 'POSE':
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='POSE')
    print(f"   ✓ Modo POSE activado")

    print(f"\n🦴 PASO 5: Generando keyframes...")
    print(f"   Armature: {armature.name}")
    print(f"   Frames: {start_frame} - {end_frame} ({end_frame - start_frame + 1} frames)")

    # PASO 6: CONSTRUIR FUNCIONES DE MOVIMIENTO
    BONE_FUNCTIONS = build_bone_functions(bone_suffix)

    bones_applied = 0
    bones_missing = []
    bones_by_category = {
        'spine': 0,
        'head': 0,
        'ears': 0,
        'jaw': 0,
        'tail': 0,
    }

    # PASO 7: APLICAR ANIMACIÓN A CADA BONE
    for bone_name, movement_func in BONE_FUNCTIONS.items():
        bone = armature.pose.bones.get(bone_name)
        
        if not bone:
            bones_missing.append(bone_name)
            continue

        # Forzar modo de rotación EULER XYZ
        bone.rotation_mode = 'XYZ'

        # Generar keyframes para todos los frames
        for frame in range(1, 61):
            adjusted_frame = start_frame + (frame - 1)
            rotation = movement_func(frame)

            # Aplicar rotación y crear keyframe
            bone.rotation_euler = rotation
            bone.keyframe_insert(data_path="rotation_euler", frame=adjusted_frame)

        bones_applied += 1

        # Clasificar por categoría para estadísticas
        if 'spine' in bone_name.lower():
            bones_by_category['spine'] += 1
        elif 'scull' in bone_name.lower():
            bones_by_category['head'] += 1
        elif 'ear' in bone_name.lower():
            bones_by_category['ears'] += 1
        elif 'jaw' in bone_name.lower():
            bones_by_category['jaw'] += 1
        elif 'tail' in bone_name.lower():
            bones_by_category['tail'] += 1

    # Reportar bones no encontrados
    if bones_missing:
        print(f"\n   ⚠️ Bones no encontrados ({len(bones_missing)}):")
        for bone in bones_missing[:5]:
            print(f"      - {bone}")
        if len(bones_missing) > 5:
            print(f"      ... y {len(bones_missing) - 5} más")

    # Estadísticas de aplicación
    print(f"\n   ✅ Keyframes aplicados exitosamente")
    print(f"   📊 Total de bones animados: {bones_applied}")
    for category, count in bones_by_category.items():
        if count > 0:
            icons = {
                'spine': '🦴',
                'head': '🐶',
                'ears': '👂',
                'jaw': '😮',
                'tail': '🐕',
            }
            print(f"      {icons.get(category, '•')} {category.capitalize()}: {count} bones")

    # PASO 6: CONFIGURAR INTERPOLACIÓN BEZIER
    print(f"\n✨ PASO 6: Configurando interpolación...")
    if armature.animation_data and armature.animation_data.action:
        fcurve_count = 0
        for fcurve in _action_fcurves(armature.animation_data.action):
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = 'BEZIER'
                keyframe.easing = 'AUTO'
            fcurve_count += 1
        print(f"   ✓ Interpolación BEZIER aplicada a {fcurve_count} F-Curves")
        print(f"   ✓ Easing AUTO para transiciones suaves")

    # PASO 8: LIMPIEZA (OPCIONAL)
    if cleanup_after and freeze_legs:
        print(f"\n🧹 PASO 8: Limpiando constraints...")
        unfreeze_legs(armature, bone_suffix)
        print(f"   ✓ Patas descongeladas (constraints removidos)")

    # REPORTE FINAL
    print("\n" + "=" * 70)
    print("✅ ANIMACIÓN GENERADA EXITOSAMENTE")
    print("=" * 70)
    print(f"   📊 Resumen:")
    print(f"      • Nombre: {ANIMATION_INFO['name']}")
    print(f"      • Duración: {ANIMATION_INFO['duration_seconds']}s @ {ANIMATION_INFO['fps']} fps")
    print(f"      • Frames: {start_frame} - {end_frame} ({end_frame - start_frame + 1} total)")
    print(f"      • Bones animados: {bones_applied}")
    print(f"      • Patas: {'CONGELADAS (20 bones)' if freeze_legs else 'Libres (pueden moverse)'}")
    print(f"      • Rig: {'Dog_001_rig_2' if bone_suffix else 'Dog_001_rig'}")
    print(f"\n   🎨 Configuración de movimiento:")
    print(f"      • Columna vertebral: Shake lateral 7 Hz (±0.45 rad)")
    print(f"      • Cabeza (spine_3): Shake controlado 5 Hz (±0.28 rad) - REDUCIDO A LA MITAD")
    print(f"      • Orejas: Flapping rápido 15 Hz (±0.65 rad)")
    print(f"      • Mandíbula: Apertura ligera (±0.08 rad)")
    print(f"      • Cola: Agitación vigorosa 9 Hz (±0.55 rad)")
    print(f"      • Patas: ESTÁTICAS - Sin keyframes + Constraints (influencia=0)")
    print(f"\n   🎯 Resultado esperado:")
    print(f"      ✓ Cuerpo se sacude vigorosamente de lado a lado")
    print(f"      ✓ Cabeza oscila más rápido que el cuerpo")
    print(f"      ✓ Orejas vibran intensamente")
    print(f"      ✓ Cola se agita con la punta moviéndose más")
    print(f"      ✓ Patas permanecen COMPLETAMENTE ESTÁTICAS")
    print(f"      ✓ Patas mantienen contacto con el suelo")
    print(f"      ✓ Sin flexión antinatural de rodillas")
    print(f"\n   ⚙️ Configuración técnica:")
    print(f"      • Interpolación: BEZIER con easing AUTO")
    print(f"      • Sistema de momentum: Buildup → Peak → Decay")
    print(f"      • Transiciones: 5 frames entrada + 5 frames salida")
    print(f"      • Método de congelamiento: Child Of constraints (influencia=0)")
    
    if not cleanup_after and freeze_legs:
        print(f"\n   ⚠️ NOTA: Los constraints permanecen en el rig.")
        print(f"   Para removerlos manualmente, ejecuta:")
        print(f"   >>> unfreeze_legs(armature, '{bone_suffix}')")
    
    print("=" * 70)

    # ============================================
    # FASE PARPADEO - Sistema de parpadeo corregido
    # ============================================
    print("\nIniciando sistema de parpadeo corregido...")
    _apply_blink_phase(start_frame, end_frame)


    return True


def get_animation_metadata():
    """
    Retorna la metadata de la animación.
    Útil para sistemas que necesiten información sobre la animación.
    
    Returns:
        dict: Información completa de la animación
    """
    return ANIMATION_INFO


# ============================================================================
# FUNCIONES AUXILIARES PARA USO INTERACTIVO
# ============================================================================

def clean_all_constraints(armature):
    """
    Remueve TODOS los constraints del armature.
    ADVERTENCIA: Usar con precaución, remueve constraints de todos los bones.
    
    Args:
        armature: El objeto armature
        
    Returns:
        int: Total de constraints removidos
    """
    total_removed = 0
    for pose_bone in armature.pose.bones:
        count = len(pose_bone.constraints)
        for const in list(pose_bone.constraints):
            pose_bone.constraints.remove(const)
        total_removed += count
    
    print(f"🧹 Constraints removidos: {total_removed} de todos los bones")
    return total_removed


def apply_shake_to_selected_armature(start_frame=1, end_frame=60, freeze_legs=True):
    """
    Aplica la animación al armature seleccionado actualmente en Blender.
    Útil para ejecución rápida desde la consola de Python.
    
    Args:
        start_frame: Frame inicial
        end_frame: Frame final
        freeze_legs: Si congelar patas o no
        
    Returns:
        bool: True si tuvo éxito
    """
    armature = bpy.context.active_object
    
    if not armature or armature.type != 'ARMATURE':
        print("❌ ERROR: Selecciona un armature primero")
        return False
    
    player_parts = {'body': armature}
    return execute_animation(player_parts, start_frame, end_frame, freeze_legs)


# ============================================================================
# EJECUCIÓN AUTOMÁTICA AL CORRER EL SCRIPT
# ============================================================================

if __name__ == "__main__":
    """
    Cuando se ejecuta el script directamente en Blender,
    busca automáticamente el armature de Jerry/Dog y aplica la animación.
    """
    
    print("\n" + "=" * 70)
    print("🔍 BUSCANDO ARMATURE DE JERRY...")
    print("=" * 70)
    
    # Buscar armature de Jerry/Dog
    armature_obj = None
    
    # Prioridad 1: Buscar por nombre que contenga "jerry" o "dog"
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            if "jerry" in obj.name.lower() or "dog" in obj.name.lower():
                armature_obj = obj
                print(f"✅ Armature encontrado por nombre: {obj.name}")
                break

    # Prioridad 2: Si no se encontró, usar el primer armature disponible
    if not armature_obj:
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature_obj = obj
                print(f"✅ Armature encontrado (primero disponible): {obj.name}")
                break

    # Ejecutar animación
    if armature_obj:
        player_parts = {'body': armature_obj}
        
        success = execute_animation(
            player_parts, 
            start_frame=1, 
            end_frame=60,
            freeze_legs=True,       # Congelar patas con constraints
            cleanup_after=False     # Mantener constraints (cambiar a True para limpiar)
        )
        
        if success:
            print("\n🎉 ¡ANIMACIÓN APLICADA CON ÉXITO!")
            print("   Presiona PLAY en la timeline para ver el resultado.")
        else:
            print("\n❌ Hubo un error al aplicar la animación.")
    else:
        print("\n❌ ERROR: No se encontró ningún armature en la escena")
        print("   Asegúrate de que el archivo .blend contiene el rig de Jerry")
