# -*- coding: utf-8 -*-
"""Quita la frase final del primer diálogo de Alfred en la cueva.

Sustituye el sonido original por la versión que termina después de
«¡No, mi columna!» y acorta las pistas faciales con una vuelta suave a neutral.
Es seguro volver a ejecutar ``construir()``.
"""
import bpy


SOUND_NAME = "VozSync_ALFRED_alfred_oh_mi_columna_dolor"
TRACK_NAME = "VozSync_ALFRED_alfred_oh_mi_columna_dolor"
AUDIO = r"C:\Users\user\Desktop\Alfred_Animacion\audios\alfred\alfred_oh_mi_columna_sin_frase_final.wav"
F_START = 83
SOUND_CHANNEL = 35
VISUAL_BLEND_OUT = 6
ACTION_NEUTRAL_START = 165.0
ACTION_NEUTRAL_END = 171.0
EYES = ("ojo_izquierdo_alfred", "ojo_derecho_alfred")


def _sequence_collection(editor):
    collection = getattr(editor, "strips", None)
    if collection is None:
        collection = getattr(editor, "sequences", None)
    if collection is None:
        raise RuntimeError("La API del secuenciador no expone strips/sequences")
    return collection


def _action_fcurves(action):
    for layer in action.layers:
        for key_strip in layer.strips:
            for bag in key_strip.channelbags:
                yield from bag.fcurves


def _set_point(curve, frame, value):
    curve.keyframe_points.insert(float(frame), float(value), options={"REPLACE"})
    for point in curve.keyframe_points:
        if abs(point.co.x - float(frame)) < 0.0001:
            point.interpolation = "BEZIER"
            point.handle_left_type = "AUTO_CLAMPED"
            point.handle_right_type = "AUTO_CLAMPED"
            break
    curve.update()


def _visible_neutral_tail(eye, object_strip, shape_strip):
    """Evita que el recorte termine dentro de un parpadeo y restaura la malla."""
    neutral = {
        "location": tuple(eye.location),
        "scale": tuple(eye.scale),
        "rotation_euler": tuple(eye.rotation_euler),
    }
    additive = object_strip.blend_type in {"ADD", "SUBTRACT", "COMBINE"}
    for curve in _action_fcurves(object_strip.action):
        if curve.data_path not in neutral or curve.array_index >= len(neutral[curve.data_path]):
            continue
        current = curve.evaluate(ACTION_NEUTRAL_START)
        _set_point(curve, ACTION_NEUTRAL_START, current)
        target = 0.0 if additive else neutral[curve.data_path][curve.array_index]
        _set_point(curve, ACTION_NEUTRAL_END, target)

    for curve in _action_fcurves(shape_strip.action):
        if 'key_blocks["Closed"]' in curve.data_path:
            # El fragmento eliminado coincidía con el siguiente parpadeo.
            # Se suprime completo para que ninguna malla quede cerrada a medias.
            for index in range(len(curve.keyframe_points) - 1, -1, -1):
                point = curve.keyframe_points[index]
                if point.co.x >= 158.0:
                    curve.keyframe_points.remove(point)
            _set_point(curve, 158.0, 0.0)
            _set_point(curve, ACTION_NEUTRAL_END, 0.0)
        else:
            current = curve.evaluate(ACTION_NEUTRAL_START)
            _set_point(curve, ACTION_NEUTRAL_START, current)
            _set_point(curve, ACTION_NEUTRAL_END, 0.0)


def _trim_nla_track(id_block, visual_end):
    if not id_block or not id_block.animation_data:
        raise RuntimeError(f"No hay animación en {getattr(id_block, 'name', id_block)}")
    track = next((item for item in id_block.animation_data.nla_tracks if item.name == TRACK_NAME), None)
    if track is None or len(track.strips) != 1:
        raise RuntimeError(f"No se encontró una pista única {TRACK_NAME} en {id_block.name}")
    strip = track.strips[0]
    source_end = float(strip.action_frame_start) + (float(visual_end) - float(strip.frame_start))
    strip.action_frame_end = source_end
    strip.frame_end = float(visual_end)
    strip.blend_out = float(VISUAL_BLEND_OUT)
    strip.extrapolation = "NOTHING"
    return {
        "id": id_block.name,
        "frame_start": float(strip.frame_start),
        "frame_end": float(strip.frame_end),
        "action_frame_start": float(strip.action_frame_start),
        "action_frame_end": float(strip.action_frame_end),
        "blend_out": float(strip.blend_out),
    }, strip


def construir():
    scene = bpy.context.scene
    editor = scene.sequence_editor or scene.sequence_editor_create()
    collection = _sequence_collection(editor)
    for strip in list(collection):
        if strip.name == SOUND_NAME:
            collection.remove(strip)
    sound = collection.new_sound(SOUND_NAME, AUDIO, SOUND_CHANNEL, F_START)
    sound.volume = 1.0
    sound_end = int(sound.frame_final_end)
    visual_end = sound_end + VISUAL_BLEND_OUT

    tracks = []
    for eye_name in EYES:
        eye = bpy.data.objects.get(eye_name)
        if not eye:
            raise RuntimeError(f"No se encontró {eye_name}")
        object_info, object_strip = _trim_nla_track(eye, visual_end)
        tracks.append(object_info)
        if not eye.data.shape_keys:
            raise RuntimeError(f"{eye_name} no tiene shape keys")
        shape_info, shape_strip = _trim_nla_track(eye.data.shape_keys, visual_end)
        tracks.append(shape_info)
        _visible_neutral_tail(eye, object_strip, shape_strip)

    root = bpy.data.objects.get("alfred")
    if root:
        root["audio_inicial_texto"] = "¡Oh, mi columna! ¡No, mi columna!"
        root["audio_inicial_fragmento_eliminado"] = "es demasiado dolor"
        root["audio_inicial_inicio"] = F_START
        root["audio_inicial_fin"] = sound_end
        root["audio_inicial_animacion_fin"] = visual_end

    scene.frame_set(max(F_START, sound_end - 4))
    bpy.context.view_layer.update()
    return {
        "sound": sound.name,
        "audio_file": bpy.path.abspath(sound.sound.filepath),
        "audio_range": [int(sound.frame_final_start), sound_end],
        "visual_end": visual_end,
        "tracks": tracks,
        "review_frame": scene.frame_current,
    }


if __name__ == "__main__":
    print(construir())
