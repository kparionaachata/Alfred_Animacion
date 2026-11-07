"""Algunos insectos NO se desprenden de Alfred: desde F0 (todavia pegados) siguen al hueso de Alfred mas cercano (Child Of
horneado) y gatean por su cuerpo hasta quedar sobre la espalda (cara de arriba cuando cae tirado, f800), cerca de donde
picotean los pollos; con un pequeno gateo constante hasta el final. Los demas se caen como antes."""
import bpy, math
from mathutils import Matrix, Vector, Quaternion
sc = bpy.context.scene
al = bpy.data.objects["Armature"]; apb = al.pose.bones
F0, F1, FIN = 790, 890, sc.frame_end
SUP = 11.68
QUEDAN = {  # insecto -> sitio en la espalda de Alfred tirado (x, y)
    "fireant_1": (-19.3, -5.95), "ant_1": (-19.6, -5.7), "pillbug_1": (-19.55, -5.25),
    "whipspider_1": (-19.25, -5.5), "centipede_1": (-19.45, -4.7), "honeyant_1": (-19.25, -5.0)}
HUESOS = ["Spine2_alfred", "Spine1_alfred", "Spine_alfred", "Hips_alfred", "RightUpLeg_alfred", "LeftUpLeg_alfred",
          "Rightknee_alfred", "Leftknee_alfred"]
bmat = lambda n: al.matrix_world @ apb[n].matrix
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))

# restaurar la animacion original del F0 (por si se corre otra vez: se rehace desde las claves < F0)
sc.frame_set(F0)
W0 = {n: bpy.data.objects[n].matrix_world.copy() for n in QUEDAN}
sc.frame_set(F1)
B1 = {b: bmat(b) for b in HUESOS}
plan = {}
for n, (x, y) in QUEDAN.items():
    tgt = Vector((x, y, SUP))
    hb = min(HUESOS, key=lambda b: (B1[b].translation - tgt).length)
    yaw = W0[n].to_euler().z
    Wt = Matrix.Translation(tgt) @ Matrix.Rotation(yaw, 4, "Z")
    plan[n] = (hb, B1[hb].inverted() @ Wt)
sc.frame_set(F0)
off0 = {n: bmat(plan[n][0]).inverted() @ W0[n] for n in QUEDAN}

mats = {n: {} for n in QUEDAN}
for f in range(F0, FIN + 1):
    sc.frame_set(f)
    for i, n in enumerate(QUEDAN):
        hb, off1 = plan[n]
        t = ss((f - F0) / (F1 - 5 - F0))
        l0, r0, s0 = off0[n].decompose(); l1, r1, s1 = off1.decompose()
        off = Matrix.LocRotScale(l0.lerp(l1, t), r0.slerp(r1, t), s0.lerp(s1, t))
        tt = (f - F0) / 24.0
        g = Vector((0.035 * math.sin(tt * 1.7 + i), 0.035 * math.sin(tt * 1.3 + 2 * i), 0.0)) * ss((f - F1) / 10)
        M = bmat(hb) @ off
        mats[n][f] = Matrix.Translation(g) @ M
for n in QUEDAN:
    o = bpy.data.objects[n]; act = o.animation_data.action
    cb = act.layers[0].strips[0].channelbag(o.animation_data.action_slot)
    for fc in cb.fcurves:
        for k in [k for k in fc.keyframe_points if k.co.x >= F0][::-1]: fc.keyframe_points.remove(k)
    for f, M in mats[n].items():
        loc, rot, scl = M.decompose()
        o.location = loc; o.keyframe_insert("location", frame=f)
        if o.rotation_mode == "QUATERNION": o.rotation_quaternion = rot; o.keyframe_insert("rotation_quaternion", frame=f)
        else: o.rotation_euler = rot.to_euler(o.rotation_mode, o.rotation_euler); o.keyframe_insert("rotation_euler", frame=f)
    for fc in cb.fcurves:
        for k in fc.keyframe_points:
            if k.co.x >= F0: k.interpolation = "LINEAR"
        fc.update()
pos = {}
for f in (750, 800, 880, 960):
    sc.frame_set(f)
    pos[f] = {n: [round(v, 2) for v in bpy.data.objects[n].matrix_world.translation] for n in QUEDAN}
result = {"huesos": {n: plan[n][0] for n in QUEDAN}, "pos": pos}
