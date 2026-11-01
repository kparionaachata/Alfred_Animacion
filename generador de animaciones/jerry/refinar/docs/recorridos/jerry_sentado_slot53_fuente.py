#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
slot_54_hablar.py - ANIMACIÓN DE PERSONAJE JERRY
ANIMACIÓN DE HABLAR (MOVIMIENTO DE MANDÍBULA)

Slot 54: Jerry habla/mueve la mandíbula para simular que está hablando.
  - Movimiento de la mandíbula inferior (jaw_bot)
  - Movimientos sutiles en cola, orejas, cabeza y cuerpo
  - Expresión facial simulada

Frames: 2560-2609 (50 frames ≈ 2.08 s a 24 FPS)
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
# ANIMATION_INFO
# ============================================
ANIMATION_INFO = {
    'name': 'slot_054_jerry_hablar',
    'frame_count': 50,
    'fps': 24,
    'duration_seconds': 2.083,
    'entity': 'Jerry',
    'character_type': 'dog_quadruped',
    'slot': 54,
    'movement_type': 'hablar',
    'minecraft_scale': '1_block_=_1m3',
    'narrative_importance': 'action',
    'rig_type': 'quadruped_hierarchy',
    'source': 'jerry_dog_rig_mathematical',
    'bones_animated': 35,
    'animation_type': 'speech_simulation',
    'bone_count': 35,
    'data_source': 'jerry_outliner_data.json',
    'complete_rig_coverage': True,
    'entry_frames': 5,
    'exit_frames': 5,
    'main_animation_frames': 40,
    'requires_previous_slot': True,
    'previous_slot': 53,
}

# ============================================
# COORDENADAS DEL RECORRIDO PARA SLOT 54
# ============================================
EMBEDDED_TRAJECTORY_POINTS = [
    {
        "index": 151,
        "coordinates": {"x": -99.5, "y": -1.5, "z": 10.75},
        "texture": "grass_block_top"
    }
]

# ============================================
# CONFIGURACIÓN DEL SLOT
# ============================================
SLOT_INDEX = 54
START_FRAME = 2560
END_FRAME = 2609  # 50 frames (2560-2609)
TOTAL_FRAMES = 50

# ============================================
# POSICIÓN Y ORIENTACIÓN DE JERRY (Sentado)
# ============================================
ROOT_POSITION = {"x": -99.5, "y": -1.5, "z": 10.75}
ROOT_ROTATION_Z = math.radians(105)

# ============================================
# POSICIÓN BASE (SENTADO - Slot 53)
# ============================================
SITTING_POSE = {
    # Piernas traseras
    'shoulder.R': (math.radians(30.7941), math.radians(17.2106), math.radians(12.1341)),
    'thigh.R': (math.radians(-37.8749), math.radians(-0.08667), math.radians(-0.29331)),
    'shin.R': (math.radians(-60.7645), math.radians(5.85033), math.radians(-3.20637)),
    'foot.R': (0.0, 0.0, 0.0),
    'toe.R': (math.radians(32.7165), math.radians(-3.13541), math.radians(-3.85954)),
    'shoulder.L': (math.radians(36.6239), math.radians(-7.29244), math.radians(7.40292)),
    'thigh.L': (math.radians(-35.5687), math.radians(0.050003), math.radians(0.028891)),
    'shin.L': (math.radians(-66.431), math.radians(-2.51456), math.radians(10.2236)),
    'foot.L': (0.0, 0.0, 0.0),
    'toe.L': (math.radians(13.1202), math.radians(3.13541), math.radians(-0.724126)),
    # Piernasdelanteras
    'front_shoulder.R': (math.radians(0.104614), math.radians(4.64061), math.radians(-13.2978)),
    'front_thigh.R': (math.radians(-3.19165), math.radians(0.713985), math.radians(6.77661)),
    'front_shin.R': (math.radians(-20.4907), math.radians(0.349145), math.radians(-0.494996)),
    'front_foot.R': (math.radians(41.3328), math.radians(-5.89264), math.radians(-5.23815)),
    'front_shoulder.L': (math.radians(1.44402), math.radians(9.35442), math.radians(1.89138)),
    'front_thigh.L': (math.radians(0.89341), math.radians(-0.37494), math.radians(-4.55577)),
    'front_shin.L': (math.radians(-18.3209), math.radians(-0.246426), math.radians(-0.054384)),
    'front_foot.L': (0.0, 0.0, 0.0),
    # Columna
    'spine_1': (math.radians(13.2537), math.radians(2.15474), math.radians(2.55871)),
    'spine_4': (math.radians(6.06694), 0.0, 0.0),
    'spine_5': (math.radians(-32.2499), 0.0, 0.0),
    'spine_6': (math.radians(60.3763), math.radians(-7.91597), math.radians(-1.48891)),
    # Cola
    'tail_1': (math.radians(-54.5851), math.radians(10.5782), math.radians(-10.7713)),
    'tail_2': (math.radians(-40.0), math.radians(15.0), math.radians(-8.0)),
    'tail_3': (math.radians(-25.0), math.radians(12.0), math.radians(-5.0)),
    # Orejas
    'ear.L': (math.radians(15.0), math.radians(5.0), math.radians(8.0)),
    'ear.R': (math.radians(12.0), math.radians(-5.0), math.radians(-8.0)),
    # Cabeza
    'scull': (math.radians(-25.0), math.radians(3.0), math.radians(8.0)),
    'jaw_top': (math.radians(10.0), 0.0, 0.0),
}

# ============================================
# POSICIÓN DE HABLANDO (con jaw_bot animado)
# ============================================
TALKING_POSE = {
    # Mandíbula inferior - clave para hablar
    'jaw_bot': (math.radians(15.0), 0.0, 0.0),  # Abre la boca
    # Cabeza - leve movimiento
    'scull': (math.radians(-23.0), math.radians(4.0), math.radians(10.0)),
    # Cola - movimiento expresivo
    'tail_1': (math.radians(-50.0), math.radians(15.0), math.radians(-8.0)),
    'tail_2': (math.radians(-35.0), math.radians(20.0), math.radians(-5.0)),
    'tail_3': (math.radians(-20.0), math.radians(18.0), math.radians(-3.0)),
    # Orejas - expresivas
    'ear.L': (math.radians(18.0), math.radians(8.0), math.radians(10.0)),
    'ear.R': (math.radians(15.0), math.radians(-8.0), math.radians(-10.0)),
    # Cuerpo - leve movimiento
    'spine_1': (math.radians(14.0), math.radians(3.0), math.radians(4.0)),
    'spine_4': (math.radians(7.0), math.radians(1.0), math.radians(1.0)),
}

# ============================================
# FUNCIONES AUXILIARES
# ============================================

def ease_in_out(t):
    return t * t * (3 - 2 * t)

def lerp(a, b, t):
    return a + (b - a) * t

def lerp_tuple(a, b, t):
    if a is None or b is None:
        return b if b is not None else a
    return tuple(lerp(ai, bi, t) for ai, bi in zip(a, b))

def sin_wave(frame, period, amplitude, phase=0.0, offset=0.0):
    """Onda sinusoidal para movimientos oscilantes."""
    return amplitude * math.sin(2.0 * math.pi * frame / period + phase) + offset

def jaw_open_close(frame, total_frames, max_angle=math.radians(35)):
    """
    Simula abrir y cerrar la mandíbula para hablar.
    Movimiento suave: abrir → mantener → cerrar → pausa
    """
    # Dividir la animación en ciclos suaves (4 ciclos)
    cycle_count = 4
    cycle_length = total_frames / cycle_count
    position_in_cycle = frame % cycle_length
    cycle_progress = position_in_cycle / cycle_length
    
    # Patrón: abrir (rápido) → mantener → cerrar (lento) → pausa
    # Duración de cada fase (% del ciclo)
    open_duration = 0.15
    hold_duration = 0.25
    close_duration = 0.25
    pause_duration = 0.35
    
    if cycle_progress < open_duration:
        # Fase de apertura: suave Ease In
        t = cycle_progress / open_duration
        t = ease_in_out(t)  # Ease in para apertura
        return max_angle * t
    
    elif cycle_progress < open_duration + hold_duration:
        # Fase de mantener abierto: leve oscilación
        return max_angle * 0.9
    
    elif cycle_progress < open_duration + hold_duration + close_duration:
        # Fase de cierre: suave Ease Out
        t = (cycle_progress - open_duration - hold_duration) / close_duration
        t = ease_in_out(t)  # Ease out para cierre
        return max_angle * (1 - t)
    
    else:
        # Fase de pausa: mandíbula cerrada
        return 0.0


# ============================================
# GENERACIÓN DE KEYFRAMES PARA HABLAR
# ============================================

def generate_talking_keyframes(total_frames=50):
    """
    Genera keyframes para la animación de hablar.
    - Mandíbula (jaw_bot) se mueve en ciclos
    - Cola tiene movimiento expresivo
    - Orejas se mueven ligeramente
    - Cabeza tiene micro-movimientos
    """
    kf = {}
    
    # Huesos que mantienen posición base
    base_bones = [
        'shoulder.L', 'shoulder.R', 'thigh.L', 'thigh.R',
        'shin.L', 'shin.R', 'foot.L', 'foot.R', 'toe.L', 'toe.R',
        'front_shoulder.L', 'front_shoulder.R', 'front_thigh.L', 'front_thigh.R',
        'front_shin.L', 'front_shin.R', 'front_foot.L', 'front_foot.R',
        'spine_5', 'spine_6',
    ]
    
    for frame in range(1, total_frames + 1):
        t = (frame - 1) / (total_frames - 1)
        
        # ----- Huesos base (mantienen posición sentada) -----
        for bone_name in base_bones:
            base_rot = SITTING_POSE.get(bone_name, (0, 0, 0))
            kf.setdefault(bone_name, {})[frame] = base_rot
        
        # ----- MANDÍBULA (jaw_bot) - animación principal -----
        # Patrón de habla: abrir y cerrar en ciclos
        jaw_angle = jaw_open_close(frame, total_frames, math.radians(35))
        kf.setdefault('jaw_bot', {})[frame] = (jaw_angle, 0, 0)
        
        # ----- Cola: movimiento expresivo -----
        # Oscilación más intensa cuando habla, REDUCIENDO lentamente la amplitud
        tail_amplitude = 1.0 - (t * 0.6)  # Reduce de 100% a 40% durante la animación
        
        for i, bone_name in enumerate(['tail_1', 'tail_2', 'tail_3']):
            base_rot = SITTING_POSE.get(bone_name, (0, 0, 0))
            # Movimiento de balanceo más expresivo con reducción
            wave_x = sin_wave(frame, 8, 0.08 * (i + 1) * tail_amplitude, 0, 0)
            wave_y = sin_wave(frame, 6, 0.15 * (i + 1) * tail_amplitude, 0.5, 0)
            wave_z = sin_wave(frame, 10, 0.05 * (i + 1) * tail_amplitude, 0, 0)
            
            kf.setdefault(bone_name, {})[frame] = (
                base_rot[0] + wave_x,
                base_rot[1] + wave_y,
                base_rot[2] + wave_z
            )
        
        # ----- Orejas: movimiento expresivo -----
        for i, bone_name in enumerate(['ear.L', 'ear.R']):
            base_rot = SITTING_POSE.get(bone_name, (0, 0, 0))
            # Movimiento sutil de oreja
            wave_y = sin_wave(frame, 7, 0.08, i * math.pi, 0)
            wave_z = sin_wave(frame, 9, 0.05, i * math.pi, 0)
            
            kf.setdefault(bone_name, {})[frame] = (
                base_rot[0],
                base_rot[1] + wave_y,
                base_rot[2] + wave_z
            )
        
        # ----- Cabeza: micro-movimientos -----
        bone_name = 'scull'
        base_rot = SITTING_POSE.get(bone_name, (0, 0, 0))
        # Movimiento sutil de cabeza
        wave_y = sin_wave(frame, 12, 0.02, 0, 0)
        wave_z = sin_wave(frame, 15, 0.015, 0, 0)
        
        kf.setdefault(bone_name, {})[frame] = (
            base_rot[0],
            base_rot[1] + wave_y,
            base_rot[2] + wave_z
        )
        
        # ----- jaw_top:伴随 jaw_bot -----
        base_rot = SITTING_POSE.get('jaw_top', (0, 0, 0))
        jaw_top_angle = jaw_angle * 0.05  # Movimiento mínimo
        kf.setdefault('jaw_top', {})[frame] = (
            base_rot[0] + jaw_top_angle,
            base_rot[1],
            base_rot[2]
        )
        
        # ----- Spine: leve movimiento de cuerpo -----
        for i, bone_name in enumerate(['spine_1', 'spine_4']):
            base_rot = SITTING_POSE.get(bone_name, (0, 0, 0))
            wave_y = sin_wave(frame, 10, 0.015 * (i + 1), 0, 0)
            wave_z = sin_wave(frame, 14, 0.01 * (i + 1), 0, 0)
            
            kf.setdefault(bone_name, {})[frame] = (
                base_rot[0],
                base_rot[1] + wave_y,
                base_rot[2] + wave_z
            )
    
    return kf


# ============================================
# FUNCIÓN PRINCIPAL DE EJECUCIÓN
# ============================================


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

def execute_animation(player_parts, start_frame=None, end_frame=None):
    """
    Slot 54: Jerry habla (movimiento de mandíbula).
    Animación cíclica de 50 frames con movimientos expresivos.
    """
    start_frame = START_FRAME
    end_frame = END_FRAME

    print(f"🎬 Slot {SLOT_INDEX}: Frames {start_frame} - {end_frame}")
    print("🐕 Animación: HABLAR (MOVIMIENTO DE MANDÍBULA + EXPRESIONES)")

    # ------------------------------------------------------------------
    # 1. Obtener armature
    # ------------------------------------------------------------------
    armature = player_parts.get('body') if player_parts else None

    if not armature:
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE' and ('jerry' in obj.name.lower() or 'wolf' in obj.name.lower()):
                armature = obj
                break
    if not armature:
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break

    if not armature:
        print("❌ ERROR: No se encontró armature")
        return False

    # ------------------------------------------------------------------
    # 2. Buscar el root de Jerry
    # ------------------------------------------------------------------
    root = None
    for obj in bpy.data.objects:
        if obj.name.lower() == 'jerry':
            root = obj
            break
    if not root:
        root = armature

    # ------------------------------------------------------------------
    # 3. Sistema NLA
    # ------------------------------------------------------------------
    action_name = ANIMATION_INFO.get('name', f'slot_{SLOT_INDEX}_animation')
    action = bpy.data.actions.new(name=action_name)

    if not armature.animation_data:
        armature.animation_data_create()

    nla_track = armature.animation_data.nla_tracks.new()
    nla_track.name = f"Slot_{SLOT_INDEX:03d}"
    nla_strip = nla_track.strips.new(action_name, start_frame, action)
    nla_strip.frame_end = end_frame

    print(f"✅ NLA track '{nla_track.name}' creado")

    # ------------------------------------------------------------------
    # 4. Configurar modo POSE
    # ------------------------------------------------------------------
    bpy.context.view_layer.objects.active = armature
    if armature.mode != 'POSE':
        bpy.ops.object.mode_set(mode='POSE')

    for bone in armature.pose.bones:
        bone.rotation_mode = 'XYZ'

    # ------------------------------------------------------------------
    # 5. Generar keyframes para hablar
    # ------------------------------------------------------------------
    print("🔄 Generando animación de hablar con movimientos expresivos...")
    
    keyframes = generate_talking_keyframes(total_frames=TOTAL_FRAMES)
    bones_applied = 0

    for bone_name, frame_dict in keyframes.items():
        bone = armature.pose.bones.get(bone_name)
        if not bone:
            print(f"  ⚠️ Hueso no encontrado: {bone_name}")
            continue
        for local_frame, rotation in frame_dict.items():
            abs_frame = start_frame + (local_frame - 1)
            bone.rotation_euler = rotation
            bone.keyframe_insert(data_path="rotation_euler", frame=abs_frame)
        bones_applied += 1

    print(f"✅ Keyframes aplicados: {bones_applied} huesos")

    # ------------------------------------------------------------------
    # 6. Suavizar interpolación
    # ------------------------------------------------------------------
    if armature.animation_data and armature.animation_data.action:
        for fc in _action_fcurves(armature.animation_data.action):
            for kp in fc.keyframe_points:
                if start_frame <= kp.co[0] <= end_frame:
                    kp.interpolation = 'BEZIER'
                    kp.easing = 'AUTO'

    # ------------------------------------------------------------------
    # 7. Posición raíz (permanece sentada)
    # ------------------------------------------------------------------
    root_x = ROOT_POSITION["x"]
    root_y = ROOT_POSITION["y"]
    root_z = ROOT_POSITION["z"]

    for frame_offset in range(1, TOTAL_FRAMES + 1):
        abs_frame = start_frame + frame_offset - 1
        
        # Mantener posición sentada con micro-movimiento
        t = (frame_offset - 1) / (TOTAL_FRAMES - 1)
        micro_y = sin_wave(frame_offset, 20, 0.02, 0, 0)
        
        bpy.context.scene.frame_set(abs_frame)
        root.location = (root_x, root_y + micro_y, root_z)
        root.rotation_euler = (0, 0, ROOT_ROTATION_Z)
        root.keyframe_insert(data_path="location", frame=abs_frame)
        root.keyframe_insert(data_path="rotation_euler", frame=abs_frame)

    print(f"📍 Posición raíz: ({root_x}, {root_y}, {root_z}) - Estable con micro-movimiento")

    # ------------------------------------------------------------------
    # 8. Finalizar
    # ------------------------------------------------------------------
    bpy.context.scene.frame_set(start_frame)

    print(f"✅ Slot {SLOT_INDEX} completado - Animación de hablar")

    # ============================================
    # FASE PARPADEO - Sistema de parpadeo corregido
    # ============================================
    print("\nIniciando sistema de parpadeo corregido...")
    _apply_blink_phase(start_frame, end_frame)

    return True


# ============================================
# METADATA
# ============================================

def get_animation_metadata():
    return {
        'slot': SLOT_INDEX,
        'type': 'hablar',
        'requires_previous_slot': True,
        'previous_slot': 53,
        'minecraft_equivalent': 'Jerry talks/barks',
        'rig_type': 'quadruped_hierarchy',
        'source': 'jerry_dog_rig_mathematical',
        'bones_count': 25,
        'animation_type': 'speech_simulation',
        'character_type': 'dog',
        'total_frames': 50,
        'position': ROOT_POSITION,
        'main_bone_animated': 'jaw_bot',
        'subtle_animations': ['tail_wag_expressive', 'ear_movement', 'head_tilt', 'body_sway'],
    }


# ============================================
# EJECUCIÓN DIRECTA
# ============================================

if __name__ == "__main__":
    armature_obj = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and ('jerry' in obj.name.lower() or 'wolf' in obj.name.lower()):
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
        print("❌ Error: No se encontró el armature de Jerry")
