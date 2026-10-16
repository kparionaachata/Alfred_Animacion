"""Expresión procedural de Jerry creada desde palabras y prosodia."""
import bpy
import importlib
import math
import sys

sys.path.insert(0, 'C:\\Users\\user\\Desktop\\Alfred_Animacion\\generador de animaciones\\jerry\\refinar')
eye_system = importlib.import_module("jerry_animation_studio.eye_system")
GENERATED_EMOTION = 'disgusto'
TRANSCRIPT = 'Bueno, si no se vuelve a levantarte, vas pal el rio, ok?'
COMPONENTS = (('Sospecha', 0.55), ('Enojado', 0.35), ('Triste', 0.1))
END_FRAME = 71
AMPLITUDE = 0.7844941997337924
PUPIL_SHIFT = 0.005
EYE_SCALE = 1.0703798475683415
SPEECH_CURVE = [(1, 0.0), (2, 0.0), (3, 0.0), (4, 0.0), (5, 0.0), (6, 0.0), (7, 0.0), (8, 0.05822953311057294), (9, 0.8003429035071963), (10, 0.652245027348473), (11, 0.0), (12, 0.6375601904153759), (13, 0.604756367390128), (14, 0.06270446414881273), (15, 0.018361798295214407), (16, 0.2855251179755607), (17, 0.3588882583669311), (18, 0.33025783554063554), (19, 0.03251546154503637), (20, 0.04536512165357332), (21, 0.6178113259130463), (22, 0.08880598186679418), (23, 0.06898299144859009), (24, 0.7461390218630102), (25, 0.091098925082366), (26, 0.05281183421284956), (27, 0.7278628017981362), (28, 0.7298777472731107), (29, 0.3695779183714683), (30, 0.38053332312072213), (31, 0.6694460696075605), (32, 0.6426482136894844), (33, 0.06411413689647008), (34, 0.045333638547843835), (35, 0.647528528396791), (36, 0.824722554989371), (37, 0.08262213619643251), (38, 0.05456832792253482), (39, 0.0), (40, 0.0), (41, 0.0), (42, 0.0), (43, 0.7344375592765885), (44, 0.36419072282363907), (45, 0.6627615504055963), (46, 0.08722534235531983), (47, 0.0), (48, 0.43166126129960847), (49, 0.9275335642155211), (50, 0.9373945497437843), (51, 0.6460254092336677), (52, 0.05300467057455514), (53, 0.031662746215763565), (54, 0.5377239470170906), (55, 0.90241759714585), (56, 0.968984260592359), (57, 0.7743213356847294), (58, 0.07866718488319953), (59, 0.4408235153662431), (60, 0.3016905344650091), (61, 0.03858772927287402), (62, 0.7624103135708067), (63, 0.7852687592817386), (64, 0.07929876211557665), (65, 0.25859092604935546), (66, 0.20739081389801742), (67, 0.0), (68, 0.0), (69, 0.0), (70, 0.0), (71, 0.0)]
BLINK_COUNT = 1
BROW_BASE = {'sejas_1_jerry': {'euler': (0.0, 0.0, 0.0), 'loc': (0.006569, 0.000489, -0.000191)}, 'sejas_2_jerry': {'euler': (0.0, 0.0, 0.0), 'loc': (0.013395, -0.000836, 0.003522)}}
BROW_POSE = {'sejas_1_jerry': {'euler': (0.018057, 0.032724, 0.466682), 'loc': (0.00746, -0.011135, 0.000709)}, 'sejas_2_jerry': {'euler': (0.059813, -0.027015, -0.463214), 'loc': (0.020687, -0.018262, 0.005866)}}
BROW_POSE_STRENGTH = 0.66

class Settings:
    subdivide_cuts = 3
    # Las mallas de Jerry miden unos 0.085 m: las intensidades del addon se
    # expresan en metros y deben mantenerse en centésimas.
    intensity_feliz = 0.017556977135251214
    intensity_triste = 0.017556977135251214
    intensity_enojado = 0.022075969513668282
    intensity_sospecha = 0.016556977135251214
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
