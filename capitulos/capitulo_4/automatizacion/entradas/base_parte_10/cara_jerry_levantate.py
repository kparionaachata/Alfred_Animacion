"""Expresión procedural de Jerry creada desde palabras y prosodia."""
import bpy
import importlib
import math
import sys

sys.path.insert(0, 'C:\\Users\\user\\Desktop\\Alfred_Animacion\\generador de animaciones\\jerry\\refinar')
eye_system = importlib.import_module("jerry_animation_studio.eye_system")
GENERATED_EMOTION = 'disgusto'
TRANSCRIPT = 'Ya, ahora le van  ta te'
COMPONENTS = (('Sospecha', 0.55), ('Enojado', 0.35), ('Triste', 0.1))
END_FRAME = 94
AMPLITUDE = 0.8235056299970286
PUPIL_SHIFT = 0.005
EYE_SCALE = 1.0778105961899103
SPEECH_CURVE = [(1, 0.0), (2, 0.0), (3, 0.0), (4, 0.0), (5, 0.035341685061026855), (6, 0.6775174306128067), (7, 0.8184454354585947), (8, 0.6520788778157327), (9, 0.0), (10, 0.0), (11, 0.0), (12, 0.0), (13, 0.0), (14, 0.0), (15, 0.0), (16, 0.0), (17, 0.0), (18, 0.0), (19, 0.0), (20, 0.0), (21, 0.0), (22, 0.0), (23, 0.0), (24, 0.0), (25, 0.46437254740942047), (26, 0.6813565995926146), (27, 0.8031354559376648), (28, 0.8358428826828266), (29, 0.9452737656603918), (30, 0.796218876345288), (31, 0.5333654451249231), (32, 0.0), (33, 0.0), (34, 0.0), (35, 0.0), (36, 0.0), (37, 0.0), (38, 0.0), (39, 0.5806225943369615), (40, 0.7326868499304791), (41, 0.8319269761729402), (42, 0.8391288067520565), (43, 0.6532976273409083), (44, 0.38851998272831534), (45, 0.03211341119487317), (46, 0.0), (47, 0.0), (48, 0.0), (49, 0.0), (50, 0.0), (51, 0.0), (52, 0.0), (53, 0.0), (54, 0.0), (55, 0.38531977776610804), (56, 0.5627398062370964), (57, 0.54240895084132), (58, 0.45868251998209497), (59, 0.3852350752325743), (60, 0.28934558161992724), (61, 0.1829457138372846), (62, 0.01565632128980724), (63, 0.0), (64, 0.0), (65, 0.0), (66, 0.0), (67, 0.0), (68, 0.0), (69, 0.0), (70, 0.0), (71, 0.763834934690534), (72, 0.9216215273106035), (73, 0.7719151377717173), (74, 0.4884952860906938), (75, 0.0), (76, 0.0), (77, 0.0), (78, 0.0), (79, 0.0), (80, 0.0), (81, 0.0), (82, 0.0), (83, 0.0), (84, 0.0), (85, 0.0), (86, 0.4685604668698318), (87, 0.6345154825711735), (88, 0.5521525664440353), (89, 0.3595969908741852), (90, 0.21200555254757286), (91, 0.019108132216451374), (92, 0.0), (93, 0.0), (94, 0.0)]
BLINK_COUNT = 1
BROW_BASE = {'sejas_1_jerry': {'euler': (0.0, 0.0, 0.0), 'loc': (0.006569, 0.000489, -0.000191)}, 'sejas_2_jerry': {'euler': (0.0, 0.0, 0.0), 'loc': (0.013395, -0.000836, 0.003522)}}
BROW_POSE = {'sejas_1_jerry': {'euler': (0.018057, 0.032724, 0.466682), 'loc': (0.00746, -0.011135, 0.000709)}, 'sejas_2_jerry': {'euler': (0.059813, -0.027015, -0.463214), 'loc': (0.020687, -0.018262, 0.005866)}}
BROW_POSE_STRENGTH = 0.66

class Settings:
    subdivide_cuts = 3
    # Las mallas de Jerry miden unos 0.085 m: las intensidades del addon se
    # expresan en metros y deben mantenerse en centésimas.
    intensity_feliz = 0.018671589428486533
    intensity_triste = 0.018671589428486533
    intensity_enojado = 0.023562119237982043
    intensity_sospecha = 0.017671589428486532
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
