# -*- coding: utf-8 -*-
"""Alfred se lleva la mano izquierda a la espalda y se soba después de colocar la antorcha.

La postura objetivo procede de `poses/sobandose la espalda.json`. La acción se añade como
una pista NLA REPLACE que sólo controla el torso, cuello y brazos; no modifica el empty de
Alfred, las piernas ni las demás animaciones. Es seguro volver a ejecutar `construir()`.
"""
import bpy
import json
import math


RIG = "Armature"
ROOT = "alfred"
POSE_JSON = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\poses\sobandose la espalda.json"
ACTION_NAME = "Alfred_sobarse_espalda"
TRACK_NAME = "Postura_Alfred_sobarse_espalda"
F_INICIO = 588
F_POSE = 600
F_FIN = 756
BONES = (
    "Spine_alfred",
    "Neck_alfred",
    "RightUpArm_alfred",
    "Rightelbow_alfred",
    "LeftUpArm_alfred",
    "Leftelbow_alfred",
)


def _leer_objetivo():
    with open(POSE_JSON, encoding="utf-8") as fh:
        pose = json.load(fh)["poses"][0]
    return {
        name: tuple(math.radians(float(pose["bones"][name]["raw_rotation_euler_deg"][axis])) for axis in ("x", "y", "z"))
        for name in BONES
    }


def _estado(objetivo, amplitud):
    """Variación asimétrica: el codo frota; hombro, torso y cuello absorben el gesto."""
    estado = {name: list(rot) for name, rot in objetivo.items()}
    d2r = math.pi / 180.0
    offsets = {
        "Leftelbow_alfred": (8.0, -3.0, 5.0),
        "LeftUpArm_alfred": (1.4, 3.0, -2.0),
        "Spine_alfred": (1.2, 0.0, 0.8),
        "Neck_alfred": (0.5, -1.2, 0.5),
        "RightUpArm_alfred": (0.6, 0.0, -0.5),
    }
    for name, delta in offsets.items():
        for axis in range(3):
            estado[name][axis] += delta[axis] * amplitud * d2r
    return {name: tuple(rot) for name, rot in estado.items()}


def construir():
    scene = bpy.context.scene
    rig = bpy.data.objects.get(RIG)
    if not rig or rig.type != "ARMATURE":
        raise RuntimeError(f"No se encontró la armature {RIG}")
    faltan = [name for name in BONES if name not in rig.pose.bones]
    if faltan:
        raise RuntimeError(f"Faltan huesos: {faltan}")

    animation_data = rig.animation_data or rig.animation_data_create()
    for track in list(animation_data.nla_tracks):
        if track.name == TRACK_NAME:
            animation_data.nla_tracks.remove(track)
    old_action = bpy.data.actions.get(ACTION_NAME)
    if old_action:
        bpy.data.actions.remove(old_action)

    current_frame = scene.frame_current
    scene.frame_set(F_INICIO)
    bpy.context.view_layer.update()
    base = {name: tuple(rig.pose.bones[name].rotation_euler) for name in BONES}
    target = _leer_objetivo()

    # Entrada y ciclos orgánicos continuos. Alfred mantiene el gesto durante la
    # frase de Jerry (659-706) y durante su propia respuesta (708-744).
    states = [(F_INICIO, base), (F_POSE, target)]
    for frame, amplitude in (
        (606, 1.00), (612, -0.78),
        (618, 0.92), (624, -0.70),
        (630, 0.82), (636, -0.60),
        (642, 0.70), (648, -0.45),
    ):
        states.append((frame, _estado(target, amplitude)))
    for frame, amplitude in (
        (654, 0.62), (660, -0.45),
        (666, 0.74), (672, -0.55),
        (678, 0.82), (684, -0.60),
        (690, 0.74), (696, -0.52),
        (702, 0.72), (708, -0.54),
        (714, 0.80), (720, -0.58),
        (726, 0.82), (732, -0.60),
        (738, 0.72), (744, -0.48),
    ):
        states.append((frame, _estado(target, amplitude)))
    states.extend(((748, target), (F_FIN, base)))

    action = bpy.data.actions.new(ACTION_NAME)
    slot = action.slots.new(id_type="OBJECT", name=rig.name)
    layer = action.layers.new("Sobarse espalda")
    key_strip = layer.strips.new(type="KEYFRAME")
    channelbag = key_strip.channelbag(slot, ensure=True)
    for bone_name in BONES:
        data_path = f'pose.bones["{bone_name}"].rotation_euler'
        for axis in range(3):
            curve = channelbag.fcurves.new(data_path, index=axis, group_name=bone_name)
            points = [(frame, values[bone_name][axis]) for frame, values in states]
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
    strip = track.strips.new(ACTION_NAME, F_INICIO, action)
    try:
        strip.action_slot = slot
    except Exception:
        pass
    strip.blend_type = "REPLACE"
    strip.extrapolation = "NOTHING"
    strip.influence = 1.0

    root = bpy.data.objects.get(ROOT)
    if root:
        root["f_sobarse_espalda"] = F_INICIO
        root["f_sobarse_espalda_pose"] = F_POSE
        root["f_sobarse_espalda_fin"] = F_FIN
    scene.frame_set(current_frame)
    return {
        "track": track.name,
        "action": action.name,
        "start": F_INICIO,
        "pose": F_POSE,
        "end": F_FIN,
        "bones": list(BONES),
    }


if __name__ == "__main__":
    print(construir())
