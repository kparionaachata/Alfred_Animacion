# -*- coding: utf-8 -*-
"""Orienta la columna superior de Jerry hacia Alfred mientras pronuncia su frase.

Controla únicamente la rotación X de `spine_1`, en una pista NLA independiente.
Es seguro volver a ejecutar `construir()`.
"""
import bpy
import math


RIG = "Dog_001_rig"
ROOT = "jerry"
BONE = "spine_1"
ACTION_NAME = "Jerry_mira_Alfred_dialogo"
TRACK_NAME = "Mirada_Jerry_a_Alfred_dialogo"
F_BASE = 658
F_MIRA = 664
F_HABLA_FIN = 706
F_FIN = 722
ROTACION_X = math.radians(-41.24)


def construir():
    scene = bpy.context.scene
    rig = bpy.data.objects.get(RIG)
    if not rig or rig.type != "ARMATURE":
        raise RuntimeError(f"No se encontró {RIG}")
    if BONE not in rig.pose.bones:
        raise RuntimeError(f"No se encontró el hueso {BONE}")

    animation_data = rig.animation_data or rig.animation_data_create()
    for track in list(animation_data.nla_tracks):
        if track.name == TRACK_NAME:
            animation_data.nla_tracks.remove(track)
    old_action = bpy.data.actions.get(ACTION_NAME)
    if old_action:
        bpy.data.actions.remove(old_action)

    current_frame = scene.frame_current
    scene.frame_set(F_BASE)
    bpy.context.view_layer.update()
    base_x = float(rig.pose.bones[BONE].rotation_euler.x)

    action = bpy.data.actions.new(ACTION_NAME)
    slot = action.slots.new(id_type="OBJECT", name=rig.name)
    layer = action.layers.new("Mirada a Alfred")
    key_strip = layer.strips.new(type="KEYFRAME")
    channelbag = key_strip.channelbag(slot, ensure=True)
    path = f'pose.bones["{BONE}"].rotation_euler'
    curve = channelbag.fcurves.new(path, index=0, group_name=BONE)
    points = ((F_BASE, base_x), (F_MIRA, ROTACION_X), (F_HABLA_FIN, ROTACION_X), (F_FIN, base_x))
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

    track = animation_data.nla_tracks.new()
    track.name = TRACK_NAME
    strip = track.strips.new(ACTION_NAME, F_BASE, action)
    try:
        strip.action_slot = slot
    except Exception:
        pass
    strip.blend_type = "REPLACE"
    strip.extrapolation = "NOTHING"
    strip.influence = 1.0

    root = bpy.data.objects.get(ROOT)
    if root:
        root["f_mira_alfred_dialogo"] = F_MIRA
        root["f_mira_alfred_dialogo_fin"] = F_FIN
        root["spine_1_mira_alfred_x_deg"] = -41.24
    scene.frame_set(current_frame)
    return {
        "track": TRACK_NAME,
        "bone": BONE,
        "base_x_deg": math.degrees(base_x),
        "target_x_deg": -41.24,
        "start": F_BASE,
        "target": F_MIRA,
        "speech_end": F_HABLA_FIN,
        "end": F_FIN,
    }


if __name__ == "__main__":
    print(construir())
