# -*- coding: utf-8 -*-
"""
slot_009_picotear.py
chicken_1 - Slot 9

GENERADO AUTOMÁTICAMENTE
Fecha de generación: 2026-10-09

Picotea el suelo dos veces (busca comida en el campo).
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

SLOT_INDEX = 9
START_FRAME = 1
END_FRAME = 24  # 1 + 24 - 1
TOTAL_FRAMES = 24

# ============================================
# DATOS DE TRAYECTORIA EMBEBIDOS - SLOT 9
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
# FIN DE CONFIGURACIÓN DEL SLOT 9
# ============================================

ANIMATION_INFO = {
    'name': 'slot_009_picotear.py',
    'frame_count': 24,
    'fps': 24,
    'duration_seconds': 1.00,
    'entity': 'chicken_1',
    'slot': 9,
    'movement_type': 'picotear',
    'narrative_importance': 'expression',
    'rig_type': 'full_armature',
    'source': 'chicken_1_rig',
    'bones_animated': 17,
    'animation_type': 'accion_campo_1_coordenada',
}

# Root Location: se mantiene fijo -- punto 1 == punto 2
# (0, 0, 0)

ROOT_LOCATION_DATA = {
    1: (0, 0, 0),
    24: (0, 0, 0),
}

ROOT_ROTATION_X = 0
ROOT_ROTATION_Y = 0
ROOT_ROTATION_Z = 0   # sin trayecto (picotear) -> se usa la orientacion heredada, fija

ROOT_ROTATION_DATA = {
    1: (math.radians(0), math.radians(0), math.radians(0)),
    24:   (math.radians(0), math.radians(0), math.radians(0)),
}

KEYFRAME_DATA = {
    'Root_M_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        5: (-0.101497, -0.587429, -0.429626),
        9: (-0.081907, -0.366621, -0.268227),
        13: (-0.101497, -0.587429, -0.429626),
        17: (-0.081907, -0.366621, -0.268227),
        21: (-0.101497, -0.587429, -0.429626),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Spine1_M_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        5: (0.000000, 0.000000, -0.057758),
        9: (0.000000, 0.000000, -0.057758),
        13: (0.000000, 0.000000, -0.057758),
        17: (0.000000, 0.000000, -0.057758),
        21: (0.000000, 0.000000, -0.057758),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Chest_M_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Neck_M_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        5: (0.035529, 0.021366, 0.811495),
        9: (0.035529, 0.021366, 0.811495),
        13: (0.035529, 0.021366, 0.811495),
        17: (0.035529, 0.021366, 0.811495),
        21: (0.035529, 0.021366, 0.811495),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Head_M_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        5: (0.002050, -0.016973, 0.068711),
        9: (0.002050, -0.016973, 0.068711),
        13: (0.002050, -0.016973, 0.068711),
        17: (0.002050, -0.016973, 0.068711),
        21: (0.002050, -0.016973, 0.068711),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Jaw_M_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Jaw_top_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Jaw_bot_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        5: (0.014282, 0.002370, 0.199558),
        9: (0.005508, 0.001263, 0.077786),
        13: (0.014282, 0.002370, 0.199558),
        17: (0.005508, 0.001263, 0.077786),
        21: (0.014282, 0.002370, 0.199558),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Scapula_R_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        5: (0.039920, 0.003396, 0.009017),
        9: (0.039920, 0.003396, 0.009017),
        13: (0.039920, 0.003396, 0.009017),
        17: (0.039920, 0.003396, 0.009017),
        21: (0.039920, 0.003396, 0.009017),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Shoulder_R_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        5: (0.000000, 0.000000, 0.000000),
        9: (0.044896, -0.177540, 0.227072),
        13: (0.000000, 0.000000, 0.000000),
        17: (0.044896, -0.177540, 0.227072),
        21: (0.000000, 0.000000, 0.000000),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Elbow_R_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        5: (-0.000514, 0.000111, 0.000410),
        9: (-0.000514, 0.000111, 0.000410),
        13: (-0.000514, 0.000111, 0.000410),
        17: (-0.000514, 0.000111, 0.000410),
        21: (-0.000514, 0.000111, 0.000410),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Scapula_L_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        5: (-0.038990, -0.021690, 0.029171),
        9: (-0.038990, -0.021690, 0.029171),
        13: (-0.038990, -0.021690, 0.029171),
        17: (-0.038990, -0.021690, 0.029171),
        21: (-0.038990, -0.021690, 0.029171),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Shoulder_L_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        5: (0.000000, 0.000000, 0.000000),
        9: (-0.074251, 0.358489, 0.405442),
        13: (0.000000, 0.000000, 0.000000),
        17: (-0.074251, 0.358489, 0.405442),
        21: (0.000000, 0.000000, 0.000000),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Elbow_L_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        5: (0.056852, -0.022933, 0.107060),
        9: (0.056852, -0.022933, 0.107060),
        13: (0.056852, -0.022933, 0.107060),
        17: (0.056852, -0.022933, 0.107060),
        21: (0.056852, -0.022933, 0.107060),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Hip_R_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        5: (0.077848, 0.015892, -0.241300),
        9: (0.042587, 0.008053, 0.045127),
        13: (0.077848, 0.015892, -0.241300),
        17: (0.042587, 0.008053, 0.045127),
        21: (0.077848, 0.015892, -0.241300),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Knee_R_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        5: (0.022594, 0.032831, -1.024320),
        9: (0.022594, 0.032831, -1.024320),
        13: (0.022594, 0.032831, -1.024320),
        17: (0.022594, 0.032831, -1.024320),
        21: (0.022594, 0.032831, -1.024320),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Ankle_R_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        5: (0.007063, -0.078315, -0.572789),
        9: (0.007063, -0.078315, -0.572789),
        13: (0.007063, -0.078315, -0.572789),
        17: (0.007063, -0.078315, -0.572789),
        21: (0.007063, -0.078315, -0.572789),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Hip_L_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        5: (0.000000, 0.000000, 0.000000),
        9: (0.028868, -0.011023, 0.203584),
        13: (0.000000, 0.000000, 0.000000),
        17: (0.028868, -0.011023, 0.203584),
        21: (0.000000, 0.000000, 0.000000),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Knee_L_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        5: (-0.050605, -0.063817, -1.288281),
        9: (-0.050605, -0.063817, -1.288281),
        13: (-0.050605, -0.063817, -1.288281),
        17: (-0.050605, -0.063817, -1.288281),
        21: (-0.050605, -0.063817, -1.288281),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Ankle_L_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        5: (0.002794, 0.042751, -0.678758),
        9: (0.002794, 0.042751, -0.678758),
        13: (0.002794, 0.042751, -0.678758),
        17: (0.002794, 0.042751, -0.678758),
        21: (0.002794, 0.042751, -0.678758),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Knee.Right_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        24: (0.000000, 0.000000, 0.000000),
    },
    'Knee.Left_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        24: (0.000000, 0.000000, 0.000000),
    },
    'no_bone_01_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        24: (0.000000, 0.000000, 0.000000),
    },
    'no_bone_02_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        24: (0.000000, 0.000000, 0.000000),
    },
    'no_bone_03_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        24: (0.000000, 0.000000, 0.000000),
    },
    'no_bone_04_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        24: (0.000000, 0.000000, 0.000000),
    },
    'no_bone_05_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        24: (0.000000, 0.000000, 0.000000),
    },
    'no_bone_06_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        24: (0.000000, 0.000000, 0.000000),
    },
    'no_bone_07_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        24: (0.000000, 0.000000, 0.000000),
    },
    'no_bone_08_chicken_1': {
        1: (0.000000, 0.000000, 0.000000),
        24: (0.000000, 0.000000, 0.000000),
    },
}


def execute_animation(player_parts, start_frame=None, end_frame=None):
    """
    Slot 9: 'picotear' de chicken_1 -- root inmóvil,
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

    _arm_action_name  = f'slot_{9:03d}_chicken_1_picotear_arm'
    _root_action_name = f'slot_{9:03d}_chicken_1_picotear_root'

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

    print(f"Keyframes de 'picotear' aplicados a {bones_applied} bones")
    if bones_missing:
        print(f"  AVISO: huesos no encontrados en el armature: {bones_missing}")

    if root_obj:
        for frame, rotation in ROOT_ROTATION_DATA.items():
            root_obj.rotation_euler = rotation
            root_obj.keyframe_insert(data_path="rotation_euler", frame=frame)
        for frame, location in ROOT_LOCATION_DATA.items():
            root_obj.location = location
            root_obj.keyframe_insert(data_path="location", frame=frame)

    print("ANIMACIÓN 'picotear' APLICADA!")
    print(f"  Frames: {start_frame}-{end_frame}")

    if armature.animation_data and armature.animation_data.action:
        _arm_done  = armature.animation_data.action
        armature.animation_data.action = None
        _arm_track = armature.animation_data.nla_tracks.new()
        _arm_track.name = f'Slot_009_arm'
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
        _root_track.name = f'Slot_009_root'
        _root_strip = _root_track.strips.new(_root_done.name, start_frame, _root_done)
        _root_strip.frame_end      = end_frame
        _root_strip.extrapolation  = 'HOLD_FORWARD'
        _root_strip.use_auto_blend = False
        _root_strip.blend_in       = 0
        _root_strip.blend_out      = 0

    return True


if __name__ == "__main__":
    execute_animation(None, start_frame=START_FRAME, end_frame=END_FRAME)
