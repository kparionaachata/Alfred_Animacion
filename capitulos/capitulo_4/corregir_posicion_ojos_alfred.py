# -*- coding: utf-8 -*-
"""Restaura las mallas de los ojos de Alfred delante del rostro.

Las profundidades proceden de las posiciones neutras aprobadas del personaje.
También corrige las curvas Y de las pistas NLA para evitar que una animación de
voz vuelva a introducir los ojos dentro de la cabeza. Es seguro reejecutarlo.
"""
import bpy


EYE_DEPTH = {
    "ojo_izquierdo_alfred": 0.27046,
    "ojo_derecho_alfred": 0.25633,
}
REVIEW_FRAME = 262
TRACK_NAME = "Correccion_profundidad_ojos_Alfred"


def _fcurves(action):
    for layer in action.layers:
        for key_strip in layer.strips:
            for bag in key_strip.channelbags:
                yield from bag.fcurves


def _zero_existing_depth(action):
    changed = 0
    for curve in _fcurves(action):
        if curve.data_path != "location" or curve.array_index != 1:
            continue
        for point in curve.keyframe_points:
            delta = -float(point.co.y)
            point.co.y = 0.0
            point.handle_left.y += delta
            point.handle_right.y += delta
            changed += 1
        curve.update()
    return changed


def _create_depth_action(eye, target_y, frame_end):
    action_name = f"Correccion_profundidad_{eye.name}"
    ad = eye.animation_data or eye.animation_data_create()
    for track in list(ad.nla_tracks):
        if track.name == TRACK_NAME:
            ad.nla_tracks.remove(track)
    old = bpy.data.actions.get(action_name)
    if old:
        bpy.data.actions.remove(old)

    action = bpy.data.actions.new(action_name)
    slot = action.slots.new(id_type="OBJECT", name=eye.name)
    layer = action.layers.new("Profundidad frontal")
    key_strip = layer.strips.new(type="KEYFRAME")
    bag = key_strip.channelbag(slot, ensure=True)
    curve = bag.fcurves.new("location", index=1, group_name="Ojos Alfred")
    curve.keyframe_points.add(2)
    curve.keyframe_points.foreach_set("co", (1.0, target_y, float(frame_end), target_y))
    for point in curve.keyframe_points:
        point.interpolation = "LINEAR"
    curve.update()

    track = ad.nla_tracks.new()
    track.name = TRACK_NAME
    strip = track.strips.new(action_name, 1, action)
    try:
        strip.action_slot = slot
    except Exception:
        pass
    strip.blend_type = "ADD"
    strip.extrapolation = "NOTHING"
    strip.influence = 1.0
    return track, strip, action


def construir():
    scene = bpy.context.scene
    scene.frame_set(REVIEW_FRAME)
    bpy.context.view_layer.update()
    report = []
    for eye_name, target_y in EYE_DEPTH.items():
        eye = bpy.data.objects.get(eye_name)
        if not eye or eye.type != "MESH":
            raise RuntimeError(f"No se encontró la malla {eye_name}")
        eye.hide_viewport = False
        eye.hide_render = False
        cleaned = []
        if eye.animation_data:
            for old_track in eye.animation_data.nla_tracks:
                if old_track.name == TRACK_NAME:
                    continue
                for old_strip in old_track.strips:
                    if old_strip.action:
                        cleaned.append({
                            "action": old_strip.action.name,
                            "keys": _zero_existing_depth(old_strip.action),
                        })
        # El valor base y las acciones existentes evalúan Y=0. Una pista ADD
        # permanente mantiene la separación frontal sin alterar X/Z ni la voz.
        eye.location.y = 0.0
        track, strip, action = _create_depth_action(eye, target_y, scene.frame_end)
        tracks = [{
            "track": track.name,
            "action": action.name,
            "blend": strip.blend_type,
            "range": [float(strip.frame_start), float(strip.frame_end)],
            "offset_y": target_y,
            "cleaned_actions": cleaned,
        }]

        eye["alfred_eye_front_y"] = target_y
        report.append({"eye": eye_name, "base_y": float(eye.location.y), "tracks": tracks})

    root = bpy.data.objects.get("alfred")
    if root:
        root["ojos_posicion_frontal_corregida"] = True
        root["ojo_izquierdo_y"] = EYE_DEPTH["ojo_izquierdo_alfred"]
        root["ojo_derecho_y"] = EYE_DEPTH["ojo_derecho_alfred"]

    scene.frame_set(REVIEW_FRAME)
    bpy.context.view_layer.update()
    return {"frame": REVIEW_FRAME, "eyes": report}


if __name__ == "__main__":
    print(construir())
