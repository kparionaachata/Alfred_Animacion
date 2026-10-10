# -*- coding: utf-8 -*-
"""
slot_012_rascar.py
chicken_1 - Slot 12

GENERADO AUTOMÁTICAMENTE
Fecha de generación: 2026-10-09

Rasca el suelo con la pata derecha tres veces, buscando comida.
Root inmóvil en 1 coordenada (punto 1 == punto 2),
igual mecanica que 'parada' pero con una pose animada en vez de rest.
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
# CONFIGURACIÓN DEL SLOT
# ============================================

SLOT_INDEX = 12
START_FRAME = 1
END_FRAME = 72  # 1 + 72 - 1
TOTAL_FRAMES = 72

# ============================================
# DATOS DE TRAYECTORIA EMBEBIDOS - SLOT 12
# ============================================

EMBEDDED_TRAJECTORY_POINTS = [
    {
        "index": 1,
        "coordinates": {"x": 0, "y": 0, "z": 0},
        "texture": "No Material",
        "face_index": "1"
    },
    {
        "index": 2,
        "coordinates": {"x": 0, "y": 0, "z": 0},
        "texture": "No Material",
        "face_index": "1"
    },
]

# ============================================
# FIN DE CONFIGURACIÓN DEL SLOT 12
# ============================================

ANIMATION_INFO = {
    'name': 'slot_012_rascar.py',
    'frame_count': 72,
    'fps': 24,
    'duration_seconds': 3.00,
    'entity': 'chicken_1',
    'slot': 12,
    'movement_type': 'rascar',
    'narrative_importance': 'expression',
    'rig_type': 'full_armature',
    'source': 'chicken_1_rig',
    'bones_animated': 7,
    'animation_type': 'accion_campo_1_coordenada',
}

# Root Location: se mantiene fijo -- punto 1 == punto 2
# (0, 0, 0)

ROOT_LOCATION_DATA = {
    1: (0, 0, 0),
    72: (0, 0, 0),
}

ROOT_ROTATION_X = 0
ROOT_ROTATION_Y = 0
ROOT_ROTATION_Z = 0   # sin trayecto (rascar) -> se usa la orientacion heredada, fija

ROOT_ROTATION_DATA = {
    1: (math.radians(0), math.radians(0), math.radians(0)),
    72:   (math.radians(0), math.radians(0), math.radians(0)),
}

KEYFRAME_DATA = {
    'Root_M_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Spine1_M_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        11: (0.050000, 0.000000, 0.000000),
        61: (0.050000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Chest_M_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        11: (0.100000, 0.000000, 0.000000),
        61: (0.100000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Neck_M_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Head_M_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Jaw_M_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Jaw_top_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Jaw_bot_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Scapula_R_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Shoulder_R_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Elbow_R_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Scapula_L_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Shoulder_L_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Elbow_L_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Hip_R_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        11: (0.400000, 0.000000, 0.000000),
        19: (-0.100000, 0.000000, 0.000000),
        27: (0.400000, 0.000000, 0.000000),
        35: (-0.100000, 0.000000, 0.000000),
        43: (0.400000, 0.000000, 0.000000),
        51: (-0.100000, 0.000000, 0.000000),
        61: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Knee_R_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        11: (0.500000, 0.000000, 0.000000),
        19: (0.100000, 0.000000, 0.000000),
        27: (0.500000, 0.000000, 0.000000),
        35: (0.100000, 0.000000, 0.000000),
        43: (0.500000, 0.000000, 0.000000),
        51: (0.100000, 0.000000, 0.000000),
        61: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Ankle_R_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        11: (-0.200000, 0.000000, 0.000000),
        19: (0.000000, 0.000000, 0.000000),
        27: (-0.200000, 0.000000, 0.000000),
        35: (0.000000, 0.000000, 0.000000),
        43: (-0.200000, 0.000000, 0.000000),
        51: (0.000000, 0.000000, 0.000000),
        61: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Hip_L_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        11: (0.150000, 0.000000, 0.000000),
        61: (0.150000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Knee_L_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        11: (0.200000, 0.000000, 0.000000),
        61: (0.200000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Ankle_L_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Knee.Right_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'Knee.Left_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'no_bone_01_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'no_bone_02_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'no_bone_03_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'no_bone_04_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'no_bone_05_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'no_bone_06_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'no_bone_07_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
    'no_bone_08_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        72: (0.000000, 0.000000, 0.000000),
    },
}


def execute_animation(player_parts, start_frame=None, end_frame=None):
    """
    Slot 12: 'rascar' de chicken_1 -- root inmóvil,
    pose de campo animada sobre base de rest.
    """
    start_frame = START_FRAME
    end_frame = END_FRAME

    armature = bpy.data.objects.get("Armature_chicken_1")
    if not armature or armature.type != 'ARMATURE':
        print("Error: No se encontró el Armature 'Armature_chicken_1'")
        return False

    if armature.mode != 'POSE':
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='POSE')

    root_obj = next((o for o in bpy.data.objects if o.name == "chicken_1"), None)

    _arm_action_name  = f'slot_{12:03d}_chicken_1_rascar_arm'
    _root_action_name = f'slot_{12:03d}_chicken_1_rascar_root'

    if not armature.animation_data:
        armature.animation_data_create()
    _arm_existing = bpy.data.actions.get(_arm_action_name)
    if _arm_existing:
        bpy.data.actions.remove(_arm_existing)
    _arm_action = bpy.data.actions.new(name=_arm_action_name)
    armature.animation_data.action = _arm_action

    if root_obj:
        if not root_obj.animation_data:
            root_obj.animation_data_create()
        _root_existing = bpy.data.actions.get(_root_action_name)
        if _root_existing:
            bpy.data.actions.remove(_root_existing)
        _root_action = bpy.data.actions.new(name=_root_action_name)
        root_obj.animation_data.action = _root_action

    bones_applied = 0
    bones_missing = []
    for bone_name, keyframes in KEYFRAME_DATA.items():
        bone = armature.pose.bones.get(bone_name)
        if not bone:
            bones_missing.append(bone_name)
            continue
        bone.rotation_mode = 'XYZ'
        for frame, rotation in keyframes.items():
            bone.rotation_euler = rotation
            bone.keyframe_insert(data_path="rotation_euler", frame=frame)
        bones_applied += 1

    print(f"Keyframes de 'rascar' aplicados a {bones_applied} bones")
    if bones_missing:
        print(f"  AVISO: huesos no encontrados en el armature: {bones_missing}")

    if root_obj:
        for frame, rotation in ROOT_ROTATION_DATA.items():
            root_obj.rotation_euler = rotation
            root_obj.keyframe_insert(data_path="rotation_euler", frame=frame)
        for frame, location in ROOT_LOCATION_DATA.items():
            root_obj.location = location
            root_obj.keyframe_insert(data_path="location", frame=frame)

    print("ANIMACIÓN 'rascar' APLICADA!")
    print(f"  Frames: {start_frame}-{end_frame}")

    if armature.animation_data and armature.animation_data.action:
        _arm_done  = armature.animation_data.action
        armature.animation_data.action = None
        _arm_track = armature.animation_data.nla_tracks.new()
        _arm_track.name = f'Slot_012_arm'
        _arm_strip = _arm_track.strips.new(_arm_done.name, start_frame, _arm_done)
        _arm_strip.frame_end      = end_frame
        _arm_strip.extrapolation  = 'NOTHING'
        _arm_strip.use_auto_blend = False
        _arm_strip.blend_in       = 0
        _arm_strip.blend_out      = 0

    if root_obj and root_obj.animation_data and root_obj.animation_data.action:
        _root_done  = root_obj.animation_data.action
        root_obj.animation_data.action = None
        _root_track = root_obj.animation_data.nla_tracks.new()
        _root_track.name = f'Slot_012_root'
        _root_strip = _root_track.strips.new(_root_done.name, start_frame, _root_done)
        _root_strip.frame_end      = end_frame
        _root_strip.extrapolation  = 'HOLD_FORWARD'
        _root_strip.use_auto_blend = False
        _root_strip.blend_in       = 0
        _root_strip.blend_out      = 0

    return True


if __name__ == "__main__":
    execute_animation(None, start_frame=START_FRAME, end_frame=END_FRAME)
