"""Expresión procedural de Jerry creada desde palabras y prosodia."""
import bpy
import importlib
import math
import sys

sys.path.insert(0, 'C:\\Users\\user\\Desktop\\Alfred_Animacion\\generador de animaciones\\jerry\\refinar')
eye_system = importlib.import_module("jerry_animation_studio.eye_system")
GENERATED_EMOTION = 'enojo'
TRANSCRIPT = 'Bueno, se acabó, o te cura solo, te mueres hoy.'
COMPONENTS = (('Enojado', 0.88), ('Sospecha', 0.12))
END_FRAME = 74
AMPLITUDE = 0.8237958745037977
PUPIL_SHIFT = 0.005
EYE_SCALE = 1.077865880857866
SPEECH_CURVE = [(1, 0.0), (2, 0.0), (3, 0.0768017135232823), (4, 0.786398526175175), (5, 0.0), (6, 0.6312220691644126), (7, 0.07965255729224165), (8, 0.0), (9, 0.0), (10, 0.0), (11, 0.0), (12, 0.0), (13, 0.5299808218779362), (14, 0.7349188041560695), (15, 0.48642256648390164), (16, 0.12577958521881982), (17, 0.625698158186209), (18, 0.8297753717056109), (19, 0.6820927461569646), (20, 0.16852180700803615), (21, 0.36315925009205796), (22, 0.0), (23, 0.0), (24, 0.0), (25, 0.0), (26, 0.0), (27, 0.0), (28, 0.0), (29, 0.0), (30, 0.0), (31, 0.0), (32, 0.0), (33, 0.0), (34, 0.28722954411876744), (35, 0.3598297371207856), (36, 0.23489528063628703), (37, 0.19223792843136844), (38, 0.02046960577782334), (39, 0.05251750364925342), (40, 0.7118134203763258), (41, 0.5522057094287934), (42, 0.518725307321166), (43, 0.950019836756834), (44, 0.0978148141307522), (45, 0.04158027596658801), (46, 0.6829473784234841), (47, 0.8294993117517251), (48, 0.5625388278521817), (49, 0.0), (50, 0.587658630946882), (51, 0.8076721815494301), (52, 0.7090689417315329), (53, 0.0630209754596468), (54, 0.0), (55, 0.0), (56, 0.0364899043438824), (57, 0.5089117150389197), (58, 0.6373449887082084), (59, 0.6175368795473114), (60, 0.4801256497746624), (61, 0.0), (62, 0.43704540266923975), (63, 0.6088643925627573), (64, 0.5904780510612073), (65, 0.422570684128439), (66, 0.05063014812580251), (67, 0.032547072727124655), (68, 0.515390525950115), (69, 0.8073836355721602), (70, 0.7510527102587145), (71, 0.4982010715278739), (72, 0.041733368291999126), (73, 0.0), (74, 0.0)]
BLINK_COUNT = 1
BROW_BASE = {'sejas_1_jerry': {'euler': (0.0, 0.0, 0.0), 'loc': (0.006569, 0.000489, -0.000191)}, 'sejas_2_jerry': {'euler': (0.0, 0.0, 0.0), 'loc': (0.013395, -0.000836, 0.003522)}}
BROW_POSE = {'sejas_1_jerry': {'euler': (0.018057, 0.032724, 0.466682), 'loc': (0.00746, -0.011135, 0.000709)}, 'sejas_2_jerry': {'euler': (0.059813, -0.027015, -0.463214), 'loc': (0.020687, -0.018262, 0.005866)}}
BROW_POSE_STRENGTH = 1.0

class Settings:
    subdivide_cuts = 3
    # Las mallas de Jerry miden unos 0.085 m: las intensidades del addon se
    # expresan en metros y deben mantenerse en centésimas.
    intensity_feliz = 0.017834619120672406
    intensity_triste = 0.017834619120672406
    intensity_enojado = 0.022446158827563206
    intensity_sospecha = 0.016834619120672405
    curve_mode = "QUADRATIC"
    affect_zone = "UPPER"
    swap_axes = False
    invert_vertical = False
    invert_horizontal = False

phase_data = ((0.00,0.00),(0.12,0.00),(0.27,0.68),(0.43,1.08),(0.58,0.93),(0.73,1.01),(0.87,0.42),(1.00,0.00))
eye_names = ("ojo_izquierdo_jerry", "ojo_derecho_jerry")
pupil_names = ("pupila_izquierda_jerry", "pupila_derecha_jerry")
for eye_index, eye_name in enumerate(eye_names):
    eye = bpy.data.objects.get(eye_name)
    if eye is None:
        raise RuntimeError("No se encontró " + eye_name)
    eye_system.build_expression_shape_keys(eye, Settings())
    eye.data.shape_keys.animation_data_clear()
    eye.animation_data_clear()
    blocks = eye.data.shape_keys.key_blocks
    base_scale = eye.scale.copy()
    base_location = eye.location.copy()
    delay = eye_index * max(1, int(END_FRAME * 0.025))
    asymmetry = 1.0 if eye_index == 0 else 0.88
    for phase, weight in phase_data:
        frame = min(END_FRAME, max(1, 1 + round((END_FRAME - 1) * phase) + (delay if 0.15 < phase < 0.86 else 0)))
        for key in blocks:
            if key.name != "Basis":
                key.value = 0.0
        for expression_name, component_weight in COMPONENTS:
            key = blocks.get(expression_name)
            if key:
                key.value = AMPLITUDE * component_weight * weight * asymmetry
                key.keyframe_insert(data_path="value", frame=frame)
        closed = blocks.get("Closed")
        if closed:
            closed.value = 0.0
            closed.keyframe_insert(data_path="value", frame=frame)
        eye.scale = base_scale.copy()
        eye.scale.x *= 1.0 + (EYE_SCALE - 1.0) * weight * asymmetry
        eye.scale.z *= 1.0 + (EYE_SCALE - 1.0) * weight * 0.55
        eye.location = base_location.copy()
        eye.location.z += 0.0025 * weight * (1.0 if eye_index == 0 else 0.72)
        eye.keyframe_insert(data_path="scale", frame=frame)
        eye.keyframe_insert(data_path="location", frame=frame)
for pupil_index, pupil_name in enumerate(pupil_names):
    pupil = bpy.data.objects.get(pupil_name)
    if pupil is None:
        continue
    pupil.animation_data_clear()
    base_location = pupil.location.copy()
    side = 1.0 if pupil_index == 0 else -1.0
    for phase, weight in phase_data:
        frame = min(END_FRAME, max(1, 1 + round((END_FRAME - 1) * phase)))
        pupil.location = base_location.copy()
        direction = -1.0 if GENERATED_EMOTION == "enojo" else 1.0
        pupil.location.x += side * PUPIL_SHIFT * weight * direction
        pupil.location.z += PUPIL_SHIFT * 0.25 * weight
        pupil.keyframe_insert(data_path="location", frame=frame)

# Usar el sistema oficial del addon: curva fisiológica 40/20/40 de 9 frames,
# con shape key Closed sincronizada tanto en escleróticas como en pupilas.
eye_system.apply_blink_with_pupils(1, END_FRAME, BLINK_COUNT, 9)

rig = bpy.data.objects.get("Dog_001_rig")
if rig and rig.pose:
    def emotion_weight(frame):
        position = (frame - 1) / max(1, END_FRAME - 1)
        for index in range(len(phase_data) - 1):
            left_t, left_v = phase_data[index]
            right_t, right_v = phase_data[index + 1]
            if left_t <= position <= right_t:
                factor = (position - left_t) / max(0.000001, right_t - left_t)
                return left_v + (right_v - left_v) * factor
        return 0.0

    speech = {int(frame): float(level) for frame, level in SPEECH_CURVE}
    # Mandíbula inferior: apertura por cada sílaba/impulso de energía.
    jaw = rig.pose.bones.get("jaw_bot")
    if jaw:
        jaw.rotation_mode = "XYZ"
        base = jaw.rotation_euler.copy()
        base_scale = jaw.scale.copy()
        for frame in range(1, END_FRAME + 1):
            level = speech.get(frame, 0.0)
            jaw.rotation_euler = base.copy()
            jaw.scale = base_scale.copy()
            # Recorrido solicitado para Jerry: reposo 0 grados y apertura
            # descendente hasta -25 grados, sin sobrepasar esos límites.
            jaw.rotation_euler.x -= math.radians(25.0) * max(0.0, min(1.0, level))
            jaw.rotation_euler.z += math.radians(0.45) * level * math.sin(frame * 0.73)
            # Compresión/expansión de la malla mandibular según énfasis.
            jaw.scale.x *= 1.0 + 0.026 * level
            jaw.scale.y *= 1.0 - 0.010 * level
            jaw.scale.z *= 1.0 + 0.014 * level
            jaw.keyframe_insert(data_path="rotation_euler", frame=frame)
            jaw.keyframe_insert(data_path="scale", frame=frame)

    # Jerry no tiene un hueso independiente de nariz. jaw_top mueve el hocico
    # superior (incluida la nariz visible) con una respuesta mucho menor.
    upper_muzzle = rig.pose.bones.get("jaw_top")
    if upper_muzzle:
        upper_muzzle.rotation_mode = "XYZ"
        base = upper_muzzle.rotation_euler.copy()
        base_scale = upper_muzzle.scale.copy()
        previous = 0.0
        for frame in range(1, END_FRAME + 1):
            level = speech.get(frame, 0.0)
            attack = max(0.0, level - previous)
            upper_muzzle.rotation_euler = base.copy()
            upper_muzzle.scale = base_scale.copy()
            upper_muzzle.rotation_euler.x -= math.radians(3.0) * level
            upper_muzzle.rotation_euler.y += math.radians(1.0) * attack
            upper_muzzle.rotation_euler.z += math.radians(0.45) * level * math.sin(frame * 0.61)
            # Deformación volumétrica sutil del hocico/nariz. La asimetría
            # acompaña el ataque de la palabra sin cambiar la identidad del rig.
            upper_muzzle.scale.x *= 1.0 + 0.035 * level
            upper_muzzle.scale.y *= 1.0 - 0.012 * level
            upper_muzzle.scale.z *= 1.0 + 0.020 * level + 0.008 * attack
            upper_muzzle.keyframe_insert(data_path="rotation_euler", frame=frame)
            upper_muzzle.keyframe_insert(data_path="scale", frame=frame)
            previous = level

    # Seguimiento orgánico de cabeza y nariz, sin alterar la orientación base.
    for bone_name, follow in (("scull", 1.0), ("scull_1", 0.55)):
        bone = rig.pose.bones.get(bone_name)
        if bone is None:
            continue
        bone.rotation_mode = "XYZ"
        base = bone.rotation_euler.copy()
        for frame in range(1, END_FRAME + 1):
            level = speech.get(frame, 0.0)
            bone.rotation_euler = base.copy()
            bone.rotation_euler.x += math.radians(1.15) * level * follow
            bone.rotation_euler.y += math.radians(0.55) * level * math.sin(frame * 0.19) * follow
            bone.keyframe_insert(data_path="rotation_euler", frame=frame)

    for brow_index, bone_name in enumerate(("sejas_1_jerry", "sejas_2_jerry")):
        bone = rig.pose.bones.get(bone_name)
        if bone is None:
            continue
        bone.rotation_mode = "XYZ"
        base_data = BROW_BASE[bone_name]
        pose_data = BROW_POSE[bone_name]
        side = 1.0 if brow_index == 0 else -1.0
        for frame in range(1, END_FRAME + 1):
            weight = emotion_weight(frame)
            speech_pulse = speech.get(frame, 0.0)
            mix = min(1.0, weight * BROW_POSE_STRENGTH)
            for axis in range(3):
                bone.rotation_euler[axis] = base_data["euler"][axis] + (pose_data["euler"][axis] - base_data["euler"][axis]) * mix
                bone.location[axis] = base_data["loc"][axis] + (pose_data["loc"][axis] - base_data["loc"][axis]) * mix
            # Oscilación sobre el eje Z real de las poses capturadas del addon.
            oscillation = math.radians(2.2) * math.sin(frame * 0.27 + brow_index * 0.24)
            bone.rotation_euler.z += side * oscillation * max(weight, speech_pulse)
            bone.rotation_euler.x += math.radians(1.6) * speech_pulse * (1.0 if brow_index == 0 else 0.86)
            bone.keyframe_insert(data_path="rotation_euler", frame=frame)
            bone.keyframe_insert(data_path="location", frame=frame)

bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = END_FRAME
bpy.context.scene.render.fps = 24
