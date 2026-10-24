#!/usr/bin/env python3

import bpy
import math
import json
import random
import os
from pathlib import Path

ANIMATION_CONFIG = {
    # Información básica
    'name': 'slot_001_alfred_caminar_6_realistic',
    'frame_count': 100,
    'fps': 24,
    'duration_seconds': 4.17,
    'entity': 'Alfred',
    'slot': 1,
    'movement_type': 'walking_cycle_realistic',

    # Parámetros de caminata
    'walking_speed': 0.96,  # pasos/segundo
    'total_distance': 4.0,  # metros
    'step_distance': 1.0,  # metros por paso
    'walk_cycles': 4,  # número de pasos completos

    # Rangos de movimiento (en radianes)
    'ranges': {
        # Brazos (posición base para brazos pegados al cuerpo)
        'arm_base_x': math.radians(90),  # 90° = brazos pegados verticalmente
        'arm_base_y': 0,  # Sin rotación inicial en Y
        'arm_base_z': 0,  # Sin separación lateral (brazos pegados)
        'arm_swing_y': math.radians(70),  # ±70° oscilación adelante/atrás en -Y/+Y
        'arm_spread_z': 0,  # Sin separación lateral (brazos pegados)
        'elbow_flex': math.radians(50),  # Flexión de codo

        # Piernas
        'leg_swing_x': math.radians(50),  # ±50° adelante/atrás (aumentado de 35°)
        'leg_sway_z': math.radians(3),  # Balanceo lateral
        'leg_rotation_y': math.radians(4),  # Rotación interna/externa
        'knee_flex': math.radians(40),  # Flexión máxima

        # Torso
        'hip_forward': math.radians(3),  # Inclinación adelante/atrás
        'hip_sway': math.radians(4),  # Balanceo lateral
        'hip_tilt': math.radians(4),  # Rotación
        'spine_bend': math.radians(0.1),  # Flexión de columna
        'spine_compensation': 0.6,  # Factor de compensación

        # Cabeza
        'neck_tilt': math.radians(1.5),  # Inclinación
        'neck_nod': math.radians(1),  # Asentimiento
        'head_stabilization': 0.25,  # Factor de estabilización
    },

    # Fases del ciclo de caminata
    'phases': {
        'contact': 0.15,  # 0.0-0.15
        'recoil': 0.25,  # 0.15-0.25
        'swing': 0.5,  # 0.25-0.5
        'deceleration': 0.7,  # 0.5-0.7
        'preparation': 1.0,  # 0.7-1.0
    },

    # Sistema
    'minecraft_scale': '1_block_=_1m3',
    'narrative_importance': 'movement',
    'rig_type': 'full_armature',
    'bones_animated': 22,
    'improvements': 'realistic_ranges_mixamo_style_configurable_knee_fix'
}

def ease_in_out_cubic(t):
    """Suavizado cúbico - aceleración/desaceleración suave"""
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - pow(-2 * t + 2, 3) / 2

def ease_in_out_sine(t):
    """Suavizado sinusoidal - transiciones muy suaves"""
    return -(math.cos(math.pi * t) - 1) / 2

def ease_out_quad(t):
    """Desaceleración cuadrática"""
    return 1 - (1 - t) * (1 - t)

def ease_in_quad(t):
    """Aceleración cuadrática"""
    return t * t

def calculate_leg_swing(phase, config):
    """
    Calcula el swing de la pierna con oscilación sinusoidal entre ±35°
    """
    max_swing = config['ranges']['leg_swing_x']
    return max_swing * math.sin(phase * 2 * math.pi)

def calculate_knee_flex(phase, config):
    """
    ✅ CORREGIDO: Calcula la flexión de rodilla sincronizada con el swing de la pierna
    - Cuando la pierna va ADELANTE: rodilla FLEXIONADA (ángulo NEGATIVO)
    - Cuando la pierna va ATRÁS: rodilla EXTENDIDA (cerca de 0°)
    
    Biomecánica correcta de caminata humana
    """
    max_flex = config['ranges']['knee_flex']
    
    # Calcular el swing de la pierna para esta fase
    leg_swing = math.sin(phase * 2 * math.pi)
    
    # Fase del ciclo
    cycle_pos = phase % 1.0
    
    if cycle_pos < 0.5:
        # Primera mitad: pierna va hacia ADELANTE
        # La rodilla debe FLEXIONARSE (valor NEGATIVO)
        t = cycle_pos / 0.5
        # Máxima flexión en el punto medio (t=1.0)
        flex_amount = ease_in_out_sine(t)
        return -max_flex * flex_amount  # NEGATIVO = flexión hacia abajo
    else:
        # Segunda mitad: pierna va hacia ATRÁS
        # La rodilla debe EXTENDERSE (volver a 0°)
        t = (cycle_pos - 0.5) / 0.5
        # De flexión máxima a extensión completa
        flex_amount = 1.0 - ease_in_out_sine(t)
        return -max_flex * flex_amount * 0.3  # Solo 30% de flexión en fase trasera

def calculate_arm_swing(phase, config):
    """
    Calcula el swing del brazo (estilo Mixamo)
    Base en X=90°, oscilación en Y
    """
    max_swing = config['ranges']['arm_swing_y']

    # Curva sinusoidal suavizada para oscilación natural
    if phase < 0.5:
        t = phase / 0.5
        return ease_in_out_sine(t) * max_swing * 2 - max_swing
    else:
        t = (phase - 0.5) / 0.5
        return max_swing - ease_in_out_sine(t) * max_swing * 2

def calculate_elbow_flex(phase, config):
    """
    Calcula la flexión del codo en eje Z
    Mayor flexión cuando el brazo va adelante
    Rotación en Z: -Z/+Z para flexión del codo
    """
    max_flex = config['ranges']['elbow_flex']

    if phase < 0.3:
        # Brazo adelante: mayor flexión
        t = phase / 0.3
        return ease_in_out_sine(t) * max_flex * 0.85 + max_flex * 0.15
    elif phase < 0.7:
        # Transición
        t = (phase - 0.3) / 0.4
        return max_flex - ease_in_out_cubic(t) * max_flex * 0.6
    else:
        # Brazo atrás: menos flexión
        t = (phase - 0.7) / 0.3
        return max_flex * 0.4 - ease_in_out_sine(t) * max_flex * 0.25

def set_bone_rotation_internal(armature_obj, bone_name, rotation, frame):
    """Establece rotación de un hueso específico dentro de un armature"""
    if not armature_obj or armature_obj.type != 'ARMATURE':
        return False

    pose_bone = armature_obj.pose.bones.get(bone_name)
    if not pose_bone:
        return False

    if not armature_obj.animation_data:
        armature_obj.animation_data_create()
    if not armature_obj.animation_data.action:
        action = bpy.data.actions.new(name=f"{armature_obj.name}_Internal")
        armature_obj.animation_data.action = action

    pose_bone.rotation_mode = 'XYZ'
    pose_bone.rotation_euler = rotation
    data_path = f'pose.bones["{bone_name}"].rotation_euler'
    armature_obj.keyframe_insert(data_path=data_path, frame=frame)
    return True

SLOT_INDEX = 1
START_FRAME = 1
END_FRAME = 100
TOTAL_FRAMES = 100

def execute_animation(player_parts, start_frame=START_FRAME, end_frame=END_FRAME):
    """
    ✅ Slot 1 CORREGIDO: Animación de caminar por la llanura de Alfred
    SISTEMA COMPLETO: Animación de extremidades con RODILLAS CORREGIDAS
    """

    # ===== BÚSQUEDA Y VALIDACIÓN DE HUESOS (NUEVO MÉTODO) =====
    print(f"🔍 Buscando armadura y huesos de Alfred para Slot {SLOT_INDEX}...")

    armature_map = {}
    armature_obj = None

    # 1. Encontrar el objeto Armature
    possible_armature_names = ['Armature', 'Armature_alfred', 'alfred_armature']
    for name in possible_armature_names:
        if name in bpy.data.objects:
            armature_obj = bpy.data.objects[name]
            break

    if not armature_obj:
        print(f"❌ ERROR: No se encontró la armadura principal de Alfred. Nombres buscados: {possible_armature_names}")
        return False

    print(f"✅ Armadura encontrada: {armature_obj.name}")

    # 2. Mapear los huesos de la pose
    bone_mapping = {
        'main': 'Hips_alfred',
        'body': 'Spine_alfred',
        'head': 'Neck_alfred',
        'left_arm': 'LeftUpArm_alfred',
        'right_arm': 'RightUpArm_alfred',
        'left_leg': 'LeftUpLeg_alfred',
        'right_leg': 'RightUpLeg_alfred',
        'left_knee': 'Leftknee_alfred',
        'right_knee': 'Rightknee_alfred',
        'left_elbow': 'Leftelbow_alfred',
        'right_elbow': 'Rightelbow_alfred'
    }

    for part, bone_name in bone_mapping.items():
        if bone_name in armature_obj.pose.bones:
            bone = armature_obj.pose.bones[bone_name]
            bone.rotation_mode = 'XYZ'
            armature_map[part] = bone
        else:
            armature_map[part] = None

    # 3. Validar que se encontraron todos los huesos necesarios
    required_bones = list(bone_mapping.keys())
    missing_bones = [part for part in required_bones if not armature_map.get(part)]

    if missing_bones:
        print(f"❌ ERROR: Huesos faltantes en la armadura '{armature_obj.name}': {missing_bones}")
        print("INFO: Asegúrate de que la armadura de Alfred y sus huesos con sufijo '_alfred' están correctos.")
        return False

    # Configurar modo POSE para el armature principal (no para PoseBones)
    if armature_obj and armature_obj.mode != 'POSE':
        bpy.context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode='POSE')

    # ✅ CRÍTICO: Asegurar que TODOS los huesos estén en modo XYZ Euler
    print("🔧 Configurando TODOS los huesos a XYZ Euler...")
    bones_configured = 0
    for bone in armature_obj.pose.bones:
        bone.rotation_mode = 'XYZ'
        bones_configured += 1
    
    print(f"✅ {bones_configured} huesos configurados en modo XYZ Euler")
    
    # Verificar configuración de huesos principales
    print("✅ Controles de rig encontrados (modo XYZ Euler):")
    for name, arm in armature_map.items():
        print(f"  - {name}: {arm.name} [rotation_mode={arm.rotation_mode}]")

    # ===== CÁLCULO DEL CICLO DE CAMINATA CONTINUO =====
    # Calcular la duración del slot para que termine en un estado neutral
    slot_duration = end_frame - start_frame + 1
    base_cycle_duration = 24.0  # frames para un ciclo completo (2π radianes)

    # Calcular cuántos ciclos completos caben en el slot
    complete_cycles = math.floor(slot_duration / base_cycle_duration)
    remaining_frames = slot_duration % base_cycle_duration

    # Si quedan frames sueltos, ajustar para terminar en estado neutral
    if remaining_frames > 0:
        # Extender el último ciclo para que termine exactamente en 2π
        adjusted_cycle_duration = base_cycle_duration + (remaining_frames / complete_cycles) if complete_cycles > 0 else slot_duration
    else:
        adjusted_cycle_duration = base_cycle_duration

    # Calcular velocidad del ciclo para este slot
    speed = (2 * math.pi) / adjusted_cycle_duration

    print(f"🎬 Animando frames {start_frame} → {end_frame}...")
    print(f"   Ciclo: {complete_cycles} ciclos completos + {remaining_frames} frames ajustados")
    print(f"   Velocidad: {speed:.4f} rad/frame")
    print(f"   ✅ CORRECCIÓN: Rodillas con flexión biomecánica correcta")

    # ===== ANIMACIÓN FRAME POR FRAME =====
    for t in range(start_frame, end_frame + 1):
        bpy.context.scene.frame_set(t)

        # ===== ANIMACIÓN BIOMECÁNICA DE EXTREMIDADES =====
        config = ANIMATION_CONFIG
        ranges = config['ranges']

        # Fase del ciclo (0.0 - 1.0)
        walk_cycle = (t - start_frame) / (end_frame - start_frame) * config['walk_cycles'] % 1.0

        # Aplicar animación de caminata con ciclo continuo
        # Calcular el progreso del ciclo relativo al inicio del slot
        local_frame = t - start_frame
        cycle = local_frame * speed

        # ============================================
        # TORSO - Movimiento natural con compensación
        # ============================================

        # Spine - compensación del movimiento de hips
        spine_forward = math.sin(walk_cycle * 2 * math.pi + math.pi/6) * ranges['spine_bend']
        spine_sway = 0  # Sin compensación de caderas
        spine_tilt = math.cos(walk_cycle * 2 * math.pi + math.pi/3) * ranges['spine_bend'] * 0.75

        if armature_map['body']:
            armature_map['body'].rotation_euler = (spine_forward, spine_sway, spine_tilt)
            armature_map['body'].keyframe_insert(data_path="rotation_euler", frame=t)

        # ============================================
        # CABEZA - Estabilización natural
        # ============================================

        stabilization = ranges['head_stabilization']

        neck_forward = -spine_forward * stabilization
        neck_tilt = math.sin(walk_cycle * 2 * math.pi) * ranges['neck_tilt']
        neck_side = math.cos(walk_cycle * 2 * math.pi + math.pi/4) * ranges['neck_tilt'] * 0.5

        if armature_map['head']:
            armature_map['head'].rotation_euler = (neck_forward, neck_side, neck_tilt)
            armature_map['head'].keyframe_insert(data_path="rotation_euler", frame=t)

        # ============================================
        # PIERNAS - Ciclo realista calculado
        # ============================================

        # PIERNA IZQUIERDA
        left_leg_swing = calculate_leg_swing(walk_cycle, config)

        left_up_leg_bone = armature_map.get('left_leg')
        if left_up_leg_bone:
            left_up_leg_bone.rotation_euler = (left_leg_swing, 0, 0)
            left_up_leg_bone.keyframe_insert(data_path="rotation_euler", frame=t)

        # ✅ RODILLA IZQUIERDA CORREGIDA
        left_knee_flex = calculate_knee_flex(walk_cycle, config)
        left_knee_bone = armature_map.get('left_knee')
        if left_knee_bone:
            left_knee_bone.rotation_euler = (left_knee_flex, 0, 0)
            left_knee_bone.keyframe_insert(data_path="rotation_euler", frame=t)

        # PIERNA DERECHA - Fase opuesta (ciclo + 0.5)
        right_leg_cycle = (walk_cycle + 0.5) % 1.0

        right_leg_swing = calculate_leg_swing(right_leg_cycle, config)

        right_up_leg_bone = armature_map.get('right_leg')
        if right_up_leg_bone:
            right_up_leg_bone.rotation_euler = (right_leg_swing, 0, 0)
            right_up_leg_bone.keyframe_insert(data_path="rotation_euler", frame=t)

        # ✅ RODILLA DERECHA CORREGIDA
        right_knee_flex = calculate_knee_flex(right_leg_cycle, config)
        right_knee_bone = armature_map.get('right_knee')
        if right_knee_bone:
            right_knee_bone.rotation_euler = (right_knee_flex, 0, 0)
            right_knee_bone.keyframe_insert(data_path="rotation_euler", frame=t)

        # ============================================
        # BRAZOS - Estilo Mixamo (base X=90°, oscilación Y)
        # ============================================

        # BRAZO DERECHO - Sincronizado con pierna izquierda
        right_arm_phase = (walk_cycle + 0.25) % 1.0
        right_arm_swing_y = calculate_arm_swing(right_arm_phase, config)

        right_up_arm_bone = armature_map.get('right_arm')
        if right_up_arm_bone:
            right_up_arm_bone.location = (0.006604, 0.096746, -0.086079)
            right_up_arm_bone.rotation_euler = (
                ranges['arm_base_x'],  # 90° = brazos pegados al cuerpo
                right_arm_swing_y,     # Oscilación -Y/+Y (adelante/atrás)
                ranges['arm_base_z']   # 0 = sin separación lateral
            )
            right_up_arm_bone.keyframe_insert(data_path="location", frame=t)
            right_up_arm_bone.keyframe_insert(data_path="rotation_euler", frame=t)

        # Codo derecho
        right_elbow_flex = -calculate_elbow_flex(right_arm_phase, config)
        right_elbow_bone = armature_map.get('right_elbow')
        if right_elbow_bone:
            right_elbow_bone.rotation_euler = (0, 0, right_elbow_flex)
            right_elbow_bone.keyframe_insert(data_path="rotation_euler", frame=t)

        # BRAZO IZQUIERDO - Sincronizado con pierna derecha
        left_arm_phase = (walk_cycle + 0.75) % 1.0
        left_arm_swing_y = -calculate_arm_swing(left_arm_phase, config)  # Negativo para estar defasado

        left_up_arm_bone = armature_map.get('left_arm')
        if left_up_arm_bone:
            left_up_arm_bone.location = (0.013552, 0.074613, -0.085881)
            left_up_arm_bone.rotation_euler = (
                ranges['arm_base_x'],  # 90° = brazos pegados al cuerpo
                left_arm_swing_y,      # Oscilación -Y/+Y (NEGATIVO = defasado)
                ranges['arm_base_z']   # 0 = sin separación lateral
            )
            left_up_arm_bone.keyframe_insert(data_path="location", frame=t)
            left_up_arm_bone.keyframe_insert(data_path="rotation_euler", frame=t)

        # Codo izquierdo
        left_elbow_flex = calculate_elbow_flex(left_arm_phase, config)
        left_elbow_bone = armature_map.get('left_elbow')
        if left_elbow_bone:
            left_elbow_bone.rotation_euler = (0, 0, left_elbow_flex)
            left_elbow_bone.keyframe_insert(data_path="rotation_euler", frame=t)

    # ===== SUAVIZADO FINAL =====
    print(f"✅ Animación del Slot {SLOT_INDEX} completada exitosamente")
    print(f"✅ RODILLAS CORREGIDAS: Flexión biomecánica correcta aplicada")
    return True

if __name__ == "__main__":
    # Ejecutar la animación con los parámetros del slot
    player_parts = {}  # El script busca los armatures automáticamente
    execute_animation(player_parts, start_frame=START_FRAME, end_frame=END_FRAME)