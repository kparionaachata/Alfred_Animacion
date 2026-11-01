"""Expresión procedural de Jerry creada desde palabras y prosodia."""
import bpy
import importlib
import math
import sys

sys.path.insert(0, 'C:\\Users\\user\\Desktop\\Alfred_Animacion\\generador de animaciones\\jerry\\refinar')
eye_system = importlib.import_module("jerry_animation_studio.eye_system")
GENERATED_EMOTION = 'enojo'
TRANSCRIPT = 'Como que está aquí?'
COMPONENTS = (('Enojado', 0.88), ('Sospecha', 0.12))
END_FRAME = 24
AMPLITUDE = 0.8173371688597338
PUPIL_SHIFT = 0.005
EYE_SCALE = 1.0766356512113777
SPEECH_CURVE = [(1, 0.0), (2, 0.0), (3, 0.0), (4, 0.6533058612176595), (5, 0.9578094136817369), (6, 0.9238206282798039), (7, 0.6533058612176597), (8, 0.0), (9, 0.8485221913391174), (10, 2.965043150818124e-12), (11, 0.9421363850263116), (12, 3.29216497113672e-12), (13, 0.0), (14, 0.6954660405043996), (15, 0.8925791272588781), (16, 0.6954660405043996), (17, 0.0), (18, 0.0), (19, 0.0)]
BLINK_COUNT = 1
BROW_BASE = {'sejas_1_jerry': {'euler': (0.0, 0.0, 0.0), 'loc': (0.006569, 0.000489, -0.000191)}, 'sejas_2_jerry': {'euler': (0.0, 0.0, 0.0), 'loc': (0.013395, -0.000836, 0.003522)}}
BROW_POSE = {'sejas_1_jerry': {'euler': (0.018057, 0.032724, 0.466682), 'loc': (0.00746, -0.011135, 0.000709)}, 'sejas_2_jerry': {'euler': (0.059813, -0.027015, -0.463214), 'loc': (0.020687, -0.018262, 0.005866)}}
BROW_POSE_STRENGTH = 1.0
EMOTION_SEQUENCE = []
SEQUENCE_COMPONENTS = {}
SEQUENCE_BROWS = []
TRANSITION_FRAME = 16
JAW_MAX_DEGREES = 32.0
SPEECH_PEAK = 0.9578094136817369
NORMALIZE_JAW_PEAK = True

class Settings:
    subdivide_cuts = 3
    # Las mallas de Jerry miden unos 0.085 m: las intensidades del addon se
    # expresan en metros y deben mantenerse en centésimas.
    intensity_feliz = 0.01742454257184296
    intensity_triste = 0.01742454257184296
    intensity_enojado = 0.02189939009579061
    intensity_sospecha = 0.01642454257184296
    curve_mode = "QUADRATIC"
    affect_zone = "UPPER"
    swap_axes = False
    invert_vertical = False
    invert_horizontal = False

phase_data = ((0.00,0.00),(0.12,0.00),(0.27,0.68),(0.43,1.08),(0.58,0.93),(0.73,1.01),(0.87,0.42),(1.00,0.00))

def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)

def sequence_weights(frame):
    if not EMOTION_SEQUENCE:
        return (1.0, 0.0)
    half = 4.0
    second = smoothstep((frame - (TRANSITION_FRAME - half)) / (2.0 * half))
    return (1.0 - second, second)

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
        active_components = []
        if EMOTION_SEQUENCE:
            first_weight, second_weight = sequence_weights(frame)
            active_components = [
                (name, component_weight * first_weight)
                for name, component_weight in SEQUENCE_COMPONENTS[EMOTION_SEQUENCE[0]]
            ] + [
                (name, component_weight * second_weight)
                for name, component_weight in SEQUENCE_COMPONENTS[EMOTION_SEQUENCE[1]]
            ]
        else:
            active_components = list(COMPONENTS)
        totals = {}
        for expression_name, component_weight in active_components:
            totals[expression_name] = totals.get(expression_name, 0.0) + component_weight
        for expression_name, component_weight in totals.items():
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
        first_weight, second_weight = sequence_weights(frame)
        direction = -1.0 if GENERATED_EMOTION == "enojo" else 1.0
        # Pensamiento: mirada contenida. Susto: separación breve y moderada.
        sequence_amount = (0.62 * first_weight + 0.48 * second_weight) if EMOTION_SEQUENCE else 1.0
        pupil.location.x += side * PUPIL_SHIFT * weight * direction * sequence_amount
        pupil.location.z += PUPIL_SHIFT * (0.18 * first_weight + 0.32 * second_weight) * weight
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
            jaw_level = level
            if NORMALIZE_JAW_PEAK and SPEECH_PEAK > 0.0:
                jaw_level = level / SPEECH_PEAK
            jaw.rotation_euler = base.copy()
            jaw.scale = base_scale.copy()
            # Reposo en 0 grados y apertura descendente configurable según
            # la toma. La envolvente conserva el énfasis de cada palabra.
            jaw.rotation_euler.x -= math.radians(JAW_MAX_DEGREES) * max(0.0, min(1.0, jaw_level))
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
            if EMOTION_SEQUENCE:
                first_weight, scare_weight = sequence_weights(frame)
                global_weight = emotion_weight(frame)
                # Reacción clara al descubrir el peligro, con asentamiento orgánico.
                recoil = scare_weight * global_weight
                bone.rotation_euler.x -= math.radians(5.5) * recoil * follow
                bone.rotation_euler.z += math.radians(1.8) * recoil * follow
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
            if EMOTION_SEQUENCE:
                first_weight, second_weight = sequence_weights(frame)
                first_data = SEQUENCE_BROWS[0]["pose"][bone_name]
                second_data = SEQUENCE_BROWS[1]["pose"][bone_name]
                first_mix = weight * first_weight * SEQUENCE_BROWS[0]["strength"]
                second_mix = weight * second_weight * SEQUENCE_BROWS[1]["strength"]
                for axis in range(3):
                    bone.rotation_euler[axis] = (base_data["euler"][axis]
                        + (first_data["euler"][axis] - base_data["euler"][axis]) * first_mix
                        + (second_data["euler"][axis] - base_data["euler"][axis]) * second_mix)
                    bone.location[axis] = (base_data["loc"][axis]
                        + (first_data["loc"][axis] - base_data["loc"][axis]) * first_mix
                        + (second_data["loc"][axis] - base_data["loc"][axis]) * second_mix)
            else:
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
