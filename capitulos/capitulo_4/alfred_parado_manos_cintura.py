# -*- coding: utf-8 -*-
"""Alfred adopta la pose "parado con las manos en la cintura".

La pose objetivo procede de ``parado manos en la cintura.json``. Solo se
aplican las rotaciones de los 22 huesos: las ubicaciones locales del archivo
no se usan porque desplazarían el cuerpo respecto al suelo.

Secuencia a 24 fps: neutral, transición suave, pose sostenida, regreso y
pausa neutral. Estado: pendiente de aprobación.
"""
import math

import bpy
from mathutils import Euler


TARGET_ROTATIONS = {
    'Hips_alfred': [0.047325, -0.000283, -0.000006],
    'Spine_alfred': [0.0, 0.0, 0.0],
    'Spine1_alfred': [-0.063225, 0.000414, -0.000023],
    'Spine2_alfred': [0.0, 0.0, 0.0],
    'Neck_alfred': [-0.064246, 0.000337, -0.000012],
    'face_alfred': [0.0, 0.0, 0.0],
    'RightUpArm_alfred': [1.276101, 0.007172, 0.004379],
    'Rightelbow_alfred': [0.801533, -0.061632, -0.025640],
    'LeftUpArm_alfred': [1.100634, 0.000133, -0.002057],
    'Leftelbow_alfred': [1.285851, 0.068014, 0.650486],
    'no_bone_03': [0.0, 0.0, 0.0],
    'no_bone_04': [0.0, 0.0, 0.0],
    'RightUpLeg_alfred': [-0.030967, 0.605239, -0.163466],
    'Rightknee_alfred': [0.0, 0.0, 0.0],
    'no_bone_07': [0.0, 0.0, 0.0],
    'LeftUpLeg_alfred': [0.005388, -0.342157, 0.195707],
    'Leftknee_alfred': [0.0, 0.0, 0.0],
    'no_bone_08': [0.0, 0.0, 0.0],
    'no_bone_01': [0.0, 0.0, 0.0],
    'no_bone_02': [0.0, 0.0, 0.0],
    'no_bone_06': [0.0, 0.0, 0.0],
    'no_bone_05': [0.0, 0.0, 0.0],
}

# Pose inicial y final tomada de ``poses/parado_neutral.json``. El .blend de
# estructura abre con los brazos en T, por lo que no debe usarse como reposo.
NEUTRAL_ROTATIONS = {
    'Hips_alfred': [0.0, 0.0, 0.0],
    'Spine_alfred': [0.000873, 0.0, 0.000654],
    'Spine1_alfred': [0.0, 0.0, 0.0],
    'Spine2_alfred': [0.0, 0.0, 0.0],
    'Neck_alfred': [-0.000218, 0.009256, 0.0],
    'face_alfred': [0.0, 0.0, 0.0],
    'RightUpArm_alfred': [1.570796, 0.0, 0.0],
    'Rightelbow_alfred': [0.0, 0.0, -0.822976],
    'LeftUpArm_alfred': [1.570796, 0.0, 0.0],
    'Leftelbow_alfred': [0.0, 0.0, 0.334451],
    'no_bone_03': [0.0, 0.0, 0.0],
    'no_bone_04': [0.0, 0.0, 0.0],
    'RightUpLeg_alfred': [0.0, 0.0, 0.0],
    'Rightknee_alfred': [-0.209440, 0.0, 0.0],
    'no_bone_07': [0.0, 0.0, 0.0],
    'LeftUpLeg_alfred': [0.0, 0.0, 0.0],
    'Leftknee_alfred': [0.0, 0.0, 0.0],
    'no_bone_08': [0.0, 0.0, 0.0],
    'no_bone_01': [0.0, 0.0, 0.0],
    'no_bone_02': [0.0, 0.0, 0.0],
    'no_bone_06': [0.0, 0.0, 0.0],
    'no_bone_05': [0.0, 0.0, 0.0],
}

ANIMATION_INFO = {
    'name': 'parado_manos_cintura_alfred',
    'frames': 72,
    'fps': 24,
    'entity': 'Alfred',
    'status': 'pending_user',
    'source_pose': 'parado manos en la cintura.json',
}
FRAMES = ANIMATION_INFO['frames']


def _curves(action):
    if hasattr(action, 'fcurves'):
        return list(action.fcurves)
    return [curve for layer in action.layers for strip in layer.strips
            for bag in strip.channelbags for curve in bag.fcurves]


def _smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def _nearest_equivalent(start, target):
    return target + math.tau * round((start - target) / math.tau)


def find_rig():
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and 'Hips_alfred' in obj.pose.bones:
            return obj
    raise ValueError('Carga el rig de Alfred con el hueso Hips_alfred.')


def execute_animation(start_frame=1):
    armature = find_rig()
    missing = set(TARGET_ROTATIONS) - set(armature.pose.bones.keys())
    if missing:
        raise ValueError('Rig incompatible. Faltan huesos: ' + ', '.join(sorted(missing)))

    scene = bpy.context.scene
    starts = {}
    targets = {}
    for name, values in TARGET_ROTATIONS.items():
        bone = armature.pose.bones[name]
        bone.rotation_mode = 'XYZ'
        starts[name] = tuple(NEUTRAL_ROTATIONS[name])
        targets[name] = tuple(_nearest_equivalent(starts[name][axis], values[axis]) for axis in range(3))

    armature.animation_data_create()
    action = bpy.data.actions.new('Alfred_parado_manos_cintura')
    armature.animation_data.action = action

    for local_frame in range(FRAMES):
        if local_frame <= 5:
            weight = 0.0
        elif local_frame <= 23:
            weight = _smoothstep((local_frame - 5) / 18.0)
        elif local_frame <= 47:
            weight = 1.0
        elif local_frame <= 65:
            weight = 1.0 - _smoothstep((local_frame - 47) / 18.0)
        else:
            weight = 0.0

        frame = int(start_frame) + local_frame
        for name in TARGET_ROTATIONS:
            start = starts[name]
            target = targets[name]
            values = tuple(start[axis] + (target[axis] - start[axis]) * weight for axis in range(3))
            bone = armature.pose.bones[name]
            bone.rotation_euler = Euler(values, 'XYZ')
            bone.keyframe_insert('rotation_euler', frame=frame, group=name)

    for curve in _curves(action):
        for point in curve.keyframe_points:
            point.interpolation = 'LINEAR'

    scene.render.fps = 24
    scene.render.fps_base = 1
    scene.frame_start = min(scene.frame_start, int(start_frame))
    scene.frame_end = max(scene.frame_end, int(start_frame) + FRAMES - 1)
    scene.frame_set(int(start_frame))
    return True


def get_animation_metadata():
    return dict(ANIMATION_INFO)


if __name__ == '__main__':
    execute_animation()
