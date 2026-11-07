"""Jerry echado: valores finales indicados por el usuario. spine_1 = (11.662, -1.1116, 5.015) grados y empty `jerry`
Z = 13.956 m mientras esta echado (con rampas de entrada/salida); se quita la correccion de scull de la mirada.
Los filtros organicos siguen sumandose encima."""
import bpy, math
sc = bpy.context.scene
j = bpy.data.objects["jerry"]; rig = bpy.data.objects["Dog_001_rig"]; pb = rig.pose.bones["spine_1"]
A, A1, B0, B = 598, 614, 772, 789
OBJ = [math.radians(v) for v in (11.662, -1.1116, 5.015)]; ZOBJ = 13.956
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
w = lambda f: ss((f - A) / (A1 - A)) * (1 - ss((f - B0) / (B - B0)))
T = {t.name: t for t in rig.animation_data.nla_tracks}; TR = {t.name: t for t in j.animation_data.nla_tracks}
# base sin la mirada ni los organicos
T["Jerry_echado_mira"].mute = True; T["Jerry_organicos"].mute = True; TR["Jerry_echado_root"].mute = True
base = {}; zb = {}
for f in range(A, B + 1):
    sc.frame_set(f); base[f] = pb.rotation_euler.copy(); zb[f] = j.matrix_world.translation.z
T["Jerry_echado_mira"].mute = False; T["Jerry_organicos"].mute = False; TR["Jerry_echado_root"].mute = False
la = T["Jerry_echado_mira"].strips[0].action; cb = la.layers[0].strips[0].channelbags[0]
for fc in [c for c in cb.fcurves if c.data_path.startswith('pose.bones["scull"]')]: cb.fcurves.remove(fc)
for i in range(3):
    fc = cb.fcurves.find('pose.bones["spine_1"].rotation_euler', index=i)
    for k in list(fc.keyframe_points)[::-1]: fc.keyframe_points.remove(k)
    for f in range(A, B + 1): fc.keyframe_points.insert(f, (OBJ[i] - base[f][i]) * w(f), options={"FAST"}).interpolation = "LINEAR"
    fc.update()
ra = TR["Jerry_echado_root"].strips[0].action
fz = [c for c in ra.layers[0].strips[0].channelbags[0].fcurves if c.data_path == "location" and c.array_index == 2][0]
for k in list(fz.keyframe_points)[::-1]: fz.keyframe_points.remove(k)
for f in range(A - 1, B + 2): fz.keyframe_points.insert(f, (ZOBJ - zb.get(f, zb[A] if f < A else zb[B])) * w(f), options={"FAST"}).interpolation = "LINEAR"
fz.update()
T["Jerry_organicos"].mute = True
r = {}
for f in (614, 650, 700, 760):
    sc.frame_set(f); r[f] = ([round(math.degrees(x), 3) for x in pb.rotation_euler], round(j.matrix_world.translation.z, 3))
T["Jerry_organicos"].mute = False
result = {"sin_organicos": r}
