"""Brazo derecho mientras sostiene la pala descansando (f104-150): valores del usuario (puestos en f116).
Se quitan las claves del brazo derecho entre 104 y 150 y se ponen esas en 104 y 150 (euler continuo, sin vueltas);
la pala se vuelve a hornear en la mano (valores de la skill) de 91 a 150."""
import bpy, math
from mathutils import Vector, Matrix, Euler
sc = bpy.context.scene
al = bpy.data.objects["Armature"]; pb = al.pose.bones; pala = bpy.data.objects["stone_shovel"]
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
U = {"RightUpArm_alfred": (58.2956, -8.5636, -19.6531), "Rightelbow_alfred": (-6.6013, 16.83, -38.8683)}
act = al.animation_data.action; cb = act.layers[0].strips[0].channelbag(al.animation_data.action_slot)
for bn, vals in U.items():
    fcs = [cb.fcurves.find('pose.bones["%s"].rotation_euler' % bn, index=i) for i in range(3)]
    ref = Euler([fcs[i].evaluate(90) for i in range(3)])
    e = Euler([math.radians(v) for v in vals]).to_quaternion().to_euler("XYZ", ref)       # continuo con f90
    for fc in fcs:
        for k in [k for k in fc.keyframe_points if 90.5 < k.co.x][::-1]: fc.keyframe_points.remove(k)
    for f in (104, 150):
        for i, fc in enumerate(fcs):
            kp = fc.keyframe_points.insert(f, e[i]); kp.interpolation = "BEZIER"
    for fc in fcs: fc.update()
# pala en la mano derecha (skill), fundido desde su posicion del f90
Lfix = Matrix.LocRotScale(Vector((0.21937, 0.32673, -0.001575)), Euler([math.radians(d) for d in (7.9831, 17.876, -56.916)]).to_quaternion(), Vector((0.82,) * 3))
sc.frame_set(90); p90 = pala.matrix_world.copy()
pcb = pala.animation_data.action.layers[0].strips[0].channelbag(pala.animation_data.action_slot)
for fc in pcb.fcurves:
    for k in [k for k in fc.keyframe_points if k.co.x > 90.5][::-1]: fc.keyframe_points.remove(k)
for f in range(91, 151):
    sc.frame_set(f); mano = al.matrix_world @ pb["Rightelbow_alfred"].matrix @ Lfix; w = ss((f - 90) / 14.0)
    pala.matrix_world = Matrix.LocRotScale(p90.translation.lerp(mano.translation, w), p90.to_quaternion().slerp(mano.to_quaternion(), w), mano.to_scale())
    pala.keyframe_insert("location", frame=f); pala.keyframe_insert("rotation_euler", frame=f)
for fc in pcb.fcurves:
    if fc.data_path == "rotation_euler":
        prev = None
        for k in sorted(fc.keyframe_points, key=lambda k: k.co.x):
            if prev is not None:
                while k.co.y - prev > math.pi: k.co.y -= 2 * math.pi
                while k.co.y - prev < -math.pi: k.co.y += 2 * math.pi
            prev = k.co.y
        fc.update()
sc.frame_set(116)
result = {bn: [round(math.degrees(x), 3) for x in pb[bn].rotation_euler] for bn in U}
