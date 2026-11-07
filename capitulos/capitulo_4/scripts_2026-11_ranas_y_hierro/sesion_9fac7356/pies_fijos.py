"""Los pies de Alfred no patinan aunque la cadera se adelante/atrase al empujar: IK temporal en Rightknee/Leftknee
(cadena 2) hacia la posicion de cada pie al terminar el giro (f12), horneada frame a frame (f12-fin) y quitada."""
import bpy
sc = bpy.context.scene
al = bpy.data.objects["Armature"]; pb = al.pose.bones
F0, F1 = 12, 108
act = al.animation_data.action; cb = act.layers[0].strips[0].channelbag(al.animation_data.action_slot)
sc.frame_set(F0)
pies = {k: (al.matrix_world @ pb[k].tail).copy() for k in ("Rightknee_alfred", "Leftknee_alfred")}
cad = {"Rightknee_alfred": "RightUpLeg_alfred", "Leftknee_alfred": "LeftUpLeg_alfred"}
iks = {}
for k, t in pies.items():
    e = bpy.data.objects.new("_ik_pie_" + k, None); sc.collection.objects.link(e); e.location = t
    c = pb[k].constraints.new("IK"); c.name = "_IK_pie"; c.target = e; c.chain_count = 2; c.use_tail = True
    iks[k] = (c, e); pb[k].rotation_mode = pb[cad[k]].rotation_mode = "XYZ"
err = {}
for f in range(F0, F1 + 1):
    sc.frame_set(f); bpy.context.view_layer.update()
    rots = {}
    for k in pies:
        for bn in (cad[k], k):
            rots[bn] = al.convert_space(pose_bone=pb[bn], matrix=pb[bn].matrix, from_space="POSE", to_space="LOCAL").to_euler("XYZ", pb[bn].rotation_euler)
    for c, e in iks.values(): c.mute = True
    for bn, r in rots.items(): pb[bn].rotation_euler = r; pb[bn].keyframe_insert("rotation_euler", frame=f)
    bpy.context.view_layer.update()
    err[f] = max(round((al.matrix_world @ pb[k].tail - t).length * 100, 1) for k, t in pies.items())
    for c, e in iks.values(): c.mute = False
for k, (c, e) in iks.items(): pb[k].constraints.remove(c); bpy.data.objects.remove(e)
for bn in ("RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred"):
    for i in range(3):
        fc = cb.fcurves.find('pose.bones["%s"].rotation_euler' % bn, index=i)
        if fc:
            for kp in fc.keyframe_points:
                if kp.co.x >= F0: kp.interpolation = "LINEAR"
result = {"desliz_max_cm": max(err.values()), "muestras": {f: err[f] for f in range(F0, F1 + 1, 12)}}
