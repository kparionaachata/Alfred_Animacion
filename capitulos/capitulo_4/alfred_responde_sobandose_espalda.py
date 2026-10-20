# -*- coding: utf-8 -*-
"""Integra la respuesta de Alfred sin interrumpir el gesto de sobarse la espalda.

Usa la curva de voz y la geometría expresiva exportadas por Audio a expresión,
pero las coloca en pistas NLA independientes para no borrar animaciones previas.
Es seguro volver a ejecutar ``construir()``.
"""
import ast
import bpy
import importlib
import json
import math


SOURCE_EXPRESSION = r"C:\Users\user\Desktop\Alfred_Animacion\audios\alfred\alfred_nada_no_me_ha_dicho_nada_expresion.py"
AUDIO_WAV = r"C:\Users\user\Desktop\Alfred_Animacion\audios\alfred\alfred_nada_no_me_ha_dicho_nada.wav"
RUB_SCRIPT = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sobarse_espalda.py"

F_START = 708
F_REVIEW = 726
SOUND_NAME = "VozSync_ALFRED_nada_no_me_ha_dicho_nada"
SOUND_CHANNEL = 51
TRACK_PREFIX = "VozSync_ALFRED_respuesta_espalda"
ACTION_PREFIX = "Alfred_respuesta_espalda"


def _read_constants():
    wanted = {
        "GENERATED_EMOTION", "TRANSCRIPT", "COORDINATES", "END_FRAME",
        "SHAPE_VALUE", "SCALE_X", "SCALE_Z", "VERTICAL", "ROTATION",
        "ATTACK_ROTATION", "LATERAL", "BLINK_CENTERS", "SPEECH_CURVE",
        "SPEECH_VERTICAL", "SPEECH_SCALE_X", "SPEECH_SCALE_Z",
        "DOUBT_LEFT_EYE_SCALE",
    }
    with open(SOURCE_EXPRESSION, "r", encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=SOURCE_EXPRESSION)
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in wanted:
                values[name] = ast.literal_eval(node.value)
    missing = sorted(wanted - values.keys())
    if missing:
        raise RuntimeError(f"Faltan constantes en la expresión: {missing}")
    return values


def _remove_track_and_action(id_block, track_name, action_name):
    ad = id_block.animation_data
    if ad:
        for track in list(ad.nla_tracks):
            if track.name == track_name:
                ad.nla_tracks.remove(track)
    old = bpy.data.actions.get(action_name)
    if old:
        bpy.data.actions.remove(old)


def _create_action(id_block, action_name, layer_name, curves):
    action = bpy.data.actions.new(action_name)
    slot = action.slots.new(id_type=id_block.id_type, name=id_block.name)
    layer = action.layers.new(layer_name)
    strip = layer.strips.new(type="KEYFRAME")
    bag = strip.channelbag(slot, ensure=True)
    for data_path, index, group, points in curves:
        curve = bag.fcurves.new(data_path, index=index, group_name=group)
        curve.keyframe_points.add(len(points))
        flat = []
        for frame, value in points:
            flat.extend((float(frame), float(value)))
        curve.keyframe_points.foreach_set("co", flat)
        for point in curve.keyframe_points:
            point.interpolation = "BEZIER"
            point.handle_left_type = "AUTO_CLAMPED"
            point.handle_right_type = "AUTO_CLAMPED"
        curve.update()
    return action, slot


def _add_nla(id_block, track_name, action, slot):
    ad = id_block.animation_data or id_block.animation_data_create()
    track = ad.nla_tracks.new()
    track.name = track_name
    strip = track.strips.new(action.name, F_START, action)
    try:
        strip.action_slot = slot
    except Exception:
        pass
    strip.blend_type = "REPLACE"
    strip.extrapolation = "NOTHING"
    strip.influence = 1.0
    return track, strip


def _weight(frame, end_frame):
    phases = ((0.00, 0.00), (0.12, 0.00), (0.28, 0.70), (0.42, 1.08),
              (0.57, 0.92), (0.72, 1.02), (0.86, 0.48), (1.00, 0.00))
    position = (frame - 1) / max(1, end_frame - 1)
    for (left_t, left_v), (right_t, right_v) in zip(phases, phases[1:]):
        if left_t <= position <= right_t:
            factor = (position - left_t) / max(0.000001, right_t - left_t)
            return left_v + (right_v - left_v) * factor
    return 0.0


def _quoted_key_path(name):
    return f"key_blocks[{json.dumps(name, ensure_ascii=False)}].value"


def _add_sound(scene):
    editor = scene.sequence_editor or scene.sequence_editor_create()
    collection = getattr(editor, "strips", getattr(editor, "sequences", None))
    if collection is None:
        raise RuntimeError("La API del secuenciador no expone strips/sequences")
    for strip in list(collection):
        if strip.name == SOUND_NAME:
            collection.remove(strip)
    sound = collection.new_sound(SOUND_NAME, AUDIO_WAV, SOUND_CHANNEL, F_START)
    sound.volume = 1.0
    return sound


def construir():
    values = _read_constants()
    end_frame = int(values["END_FRAME"])
    coordinates = values["COORDINATES"]
    speech = {int(frame): float(level) for frame, level in values["SPEECH_CURVE"]}
    blink_centers = {int(frame) for frame in values["BLINK_CENTERS"]}
    eye_system = importlib.import_module("alfred_animation_studio.eye_system")
    scene = bpy.context.scene
    current_frame = scene.frame_current

    # Regenera la pista corporal extendida hasta después de la respuesta.
    with open(RUB_SCRIPT, "r", encoding="utf-8") as handle:
        rub_code = compile(handle.read(), RUB_SCRIPT, "exec")
    rub_namespace = {"__name__": "alfred_sobarse_espalda_integrado"}
    exec(rub_code, rub_namespace)
    rub_info = rub_namespace["construir"]()

    generated = []
    for eye_index, (eye_name, shape_coordinates) in enumerate(coordinates.items()):
        eye = bpy.data.objects.get(eye_name)
        if eye is None:
            raise RuntimeError(f"No se encontró {eye_name}")
        eye_system._eye_ensure_subdivided(eye, 3)
        if len(eye.data.vertices) != len(shape_coordinates):
            raise RuntimeError(
                f"Topología incompatible en {eye_name}: {len(eye.data.vertices)} != {len(shape_coordinates)}"
            )
        if not eye.data.shape_keys:
            eye.shape_key_add(name="Basis", from_mix=False)
        key_data = eye.data.shape_keys
        blocks = key_data.key_blocks

        transform_track = f"{TRACK_PREFIX}_{eye_name}_transform"
        transform_action = f"{ACTION_PREFIX}_{eye_name}_transform"
        shape_track = f"{TRACK_PREFIX}_{eye_name}_formas"
        shape_action = f"{ACTION_PREFIX}_{eye_name}_formas"
        _remove_track_and_action(eye, transform_track, transform_action)
        _remove_track_and_action(key_data, shape_track, shape_action)

        old_shape = blocks.get("Audio_procedural")
        if old_shape:
            eye.shape_key_remove(old_shape)
        shape = eye.shape_key_add(name="Audio_procedural", from_mix=False)
        shape.slider_min = -2.0
        shape.slider_max = 2.0
        for vertex, coordinate in enumerate(shape_coordinates):
            shape.data[vertex].co = coordinate
        blocks = key_data.key_blocks
        for block in blocks:
            if block.name != "Basis":
                block.value = 0.0

        base_location = tuple(eye.location)
        base_scale = tuple(eye.scale)
        base_rotation = tuple(eye.rotation_euler)
        side = 1.0 if eye.matrix_world.translation.x > 0 else -1.0
        eye_amount = 1.0 if eye_index == 0 else 0.86
        previous_speech = 0.0
        locations = [[], [], []]
        scales = [[], [], []]
        rotations = [[], [], []]
        shape_points = []
        closed_points = []
        zero_shape_points = {block.name: [] for block in blocks if block.name not in ("Basis", "Closed", "Audio_procedural")}

        for frame in range(1, end_frame + 1):
            weight = _weight(frame, end_frame)
            speech_level = speech.get(frame, 0.0)
            attack = max(0.0, speech_level - previous_speech)
            wave = math.sin(frame * 1.34 + eye_index * 0.16)
            vertical_pulse = values["SPEECH_VERTICAL"] * speech_level * wave * eye_amount
            stretch = wave * speech_level

            location = list(base_location)
            location[0] += side * values["LATERAL"] * weight * (1.0 if eye_index == 0 else -0.55)
            location[2] += values["VERTICAL"] * weight * (1.0 if frame < end_frame * 0.60 else 0.65)
            location[2] += vertical_pulse

            scale = list(base_scale)
            scale[0] *= 1.0 + (values["SCALE_X"] - 1.0) * weight * eye_amount
            scale[2] *= 1.0 + (values["SCALE_Z"] - 1.0) * weight * eye_amount
            scale[0] *= 1.0 + values["SPEECH_SCALE_X"] * speech_level - 0.040 * stretch
            scale[1] *= 1.0 - 0.025 * speech_level
            scale[2] *= 1.0 + values["SPEECH_SCALE_Z"] * speech_level + 0.065 * stretch + 0.025 * attack
            if values["GENERATED_EMOTION"] == "duda" and eye_name == "ojo_izquierdo_alfred":
                doubt_size = 1.0 + (values["DOUBT_LEFT_EYE_SCALE"] - 1.0) * weight
                scale = [component * doubt_size for component in scale]

            rotation = list(base_rotation)
            rotation[1] += side * values["ROTATION"] * weight * eye_amount
            rotation[1] += side * values["ATTACK_ROTATION"] * attack * eye_amount

            for axis in range(3):
                locations[axis].append((frame, location[axis]))
                scales[axis].append((frame, scale[axis]))
                rotations[axis].append((frame, rotation[axis]))
            shape_points.append((frame, values["SHAPE_VALUE"] * weight * eye_amount))
            closed_points.append((frame, 1.0 if frame in blink_centers else 0.0))
            for name in zero_shape_points:
                zero_shape_points[name].append((frame, 0.0))
            previous_speech = speech_level

        transform_curves = []
        for axis in range(3):
            transform_curves.append(("location", axis, eye_name, locations[axis]))
            transform_curves.append(("scale", axis, eye_name, scales[axis]))
            transform_curves.append(("rotation_euler", axis, eye_name, rotations[axis]))
        action, slot = _create_action(eye, transform_action, "Voz y expresión", transform_curves)
        _, transform_strip = _add_nla(eye, transform_track, action, slot)

        shape_curves = [(_quoted_key_path("Audio_procedural"), 0, "Expresión", shape_points)]
        if blocks.get("Closed"):
            shape_curves.append((_quoted_key_path("Closed"), 0, "Parpadeo", closed_points))
        for name, points in zero_shape_points.items():
            shape_curves.append((_quoted_key_path(name), 0, "Neutralizar otras expresiones", points))
        sk_action, sk_slot = _create_action(key_data, shape_action, "Formas faciales", shape_curves)
        _, shape_strip = _add_nla(key_data, shape_track, sk_action, sk_slot)
        generated.append({
            "eye": eye_name,
            "transform_range": [transform_strip.frame_start, transform_strip.frame_end],
            "shape_range": [shape_strip.frame_start, shape_strip.frame_end],
        })

    sound = _add_sound(scene)
    root = bpy.data.objects.get("alfred")
    if root:
        root["respuesta_audio_inicio"] = F_START
        root["respuesta_audio_fin"] = int(sound.frame_final_end)
        root["respuesta_texto"] = values["TRANSCRIPT"]
        root["respuesta_emocion"] = values["GENERATED_EMOTION"]
        root["respuesta_continua_sobandose"] = True

    scene.frame_set(F_REVIEW)
    bpy.context.view_layer.update()
    return {
        "audio": SOUND_NAME,
        "audio_range": [int(sound.frame_final_start), int(sound.frame_final_end)],
        "transcript": values["TRANSCRIPT"],
        "emotion": values["GENERATED_EMOTION"],
        "eyes": generated,
        "rub": rub_info,
        "review_frame": F_REVIEW,
    }


if __name__ == "__main__":
    print(construir())
