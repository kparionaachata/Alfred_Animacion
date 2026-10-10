# -*- coding: utf-8 -*-
"""Parte 6: Alfred (ya de pie, f348) se soba la cabeza con la mano DERECHA, confundido, "sin saber que paso" (f348-430).
Se ejecuta DENTRO de Blender con exec (necesita `bpy.app.driver_namespace["IK"]` = ik_brazos.py y `ALF_K` = poses de `alfred_se_levanta_apoyado.py`; usa la pose K5 de pie).
Mano derecha por IK en puntos de paso (la punta de la MALLA de la mano, que mide ~0.25 de grosor y termina 0.278 antes de la cola del hueso) sobre la parte alta de la cabeza, con movimientos de frote de ida y vuelta irregulares;
el cuello se mueve a la vez (giros pequenos y una inclinacion) como quien no entiende. La mano sigue a la cabeza (el objetivo se recalcula con la FK del cuello en cada punto).
Variables opcionales: PASOS, CUELLO (listas de (frame, ...))."""
import bpy, math
from mathutils import Vector, Matrix, Euler, Quaternion

ns = bpy.app.driver_namespace; g = ns["IK"]; fk = g["fk"]; REST = g["REST"]; AA = g["AA"]; Mw = AA.matrix_world.copy(); sc = bpy.context.scene
K5 = ns["ALF_K"]["K5"]; ROT = dict(K5["rot"]); LOC = dict(K5["loc_all"])
sc.frame_set(348); bpy.context.view_layer.update()
neck = AA.pose.bones["Neck_alfred"]; NECK0 = tuple(neck.rotation_euler)
ROT["Neck_alfred"] = NECK0
def pt(M, n, e="h"): return Mw @ (M[n].translation if e == "h" else M[n] @ Vector((0, REST[n][2], 0)))
# cabeza de Alfred: vertices con peso en Neck/face > 0.6 (a f348)
dg = bpy.context.evaluated_depsgraph_get(); P = []
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name.endswith("_alfred"):
        vg = [x.name for x in o.vertex_groups]
        if "Neck_alfred" in vg or "face_alfred" in vg:
            ev = o.evaluated_get(dg); me = ev.to_mesh()
            for i, v in enumerate(me.vertices):
                w = {o.vertex_groups[x.group].name: x.weight for x in o.data.vertices[i].groups}
                if w.get("Neck_alfred", 0) + w.get("face_alfred", 0) > 0.6: P.append(o.matrix_world @ v.co)
            ev.to_mesh_clear()
top = max(P, key=lambda p: p.z); cx = sum(p.x for p in P) / len(P); cy = sum(p.y for p in P) / len(P)
print("cabeza: z max", round(top.z, 3), "centro xy", round(cx, 3), round(cy, 3), "n", len(P))
M0 = fk(ROT, LOC); FACE = "face_alfred"
REF_W = Vector((cx, cy, top.z + 0.02))                                       # punto de referencia: encima de la cabeza
REF_L = (Mw @ M0[FACE]).inverted() @ REF_W                                    # en el espacio del hueso de la cara (sigue a la cabeza)
OFF = 0.278; DIR = Vector((0.0, -0.5, 0.85)).normalized()
HINT_R = Vector((-0.05, -0.30, 0.10))
# (frame, desplazamiento en mundo respecto al punto de referencia (dx, dy, dz), cuello (grados: dY, dZ))
PASOS = globals().get("PASOS") or [(348, None, (0, 0)),
    (357, (0.04, -0.05, 0.30), (-6, 2)), (364, (0.07, -0.03, 0.02), (-12, 4)),
    (368, (-0.06, 0.03, 0.0), (-12, 4)), (372, (0.05, -0.02, 0.0), (14, -2)), (375, (-0.07, 0.04, 0.0), (14, -2)),
    (380, (0.06, 0.0, 0.0), (-10, -5)), (383, (-0.04, -0.03, 0.0), (-10, -5)), (390, (0.0, 0.02, 0.0), (6, 8)),
    (396, (0.07, 0.02, 0.0), (6, 8)), (399, (-0.05, 0.0, 0.0), (-8, 4)), (403, (0.04, 0.03, 0.0), (-8, 4)), (410, (0.0, 0.0, 0.01), (2, 0)),
    (418, (0.03, -0.04, 0.28), (0, 0)), (430, None, (0, 0))]
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
ROT0r = tuple(ROT["RightUpArm_alfred"]); q_prev = Euler(ROT0r, 'XYZ').to_quaternion(); x_prev = 0.0
sol = []                                                                     # (frame, quat hombro, codo X, cuello (X,Y,Z) grados)
for (f, off, nk) in PASOS:
    r = dict(ROT); nx = math.degrees(NECK0[0]); r["Neck_alfred"] = tuple(math.radians(v) for v in (nx, nk[0], nk[1]))
    if off is None:
        q = Euler(ROT0r, 'XYZ').to_quaternion(); codo_x = 0.0
    else:
        M = fk(r, LOC); fw = Mw @ M[FACE]; objetivo_punta = fw @ REF_L + Vector(off); d = DIR
        for _ in range(2):
            obj = objetivo_punta + d * OFF; sh = pt(M, "RightUpArm_alfred")
            q, qx, err, codo = g["resolver"]("Right", M["Spine2_alfred"], Mw, obj, codo_hint=sh + HINT_R, inicio=(q_prev, x_prev), iters=5000, semilla=5, w_codo=0.3, w_giro=0.3)
            d = (obj - codo).normalized()
        codo_x = math.atan2(2 * qx.w * qx.x, qx.w * qx.w - qx.x * qx.x) if False else qx.to_euler('XYZ')[0]
        print("frame", f, "error", round(err, 3))
        q_prev, x_prev = q, codo_x
    sol.append((f, q, codo_x, (nx, nk[0], nk[1])))
# claves por frame entre puntos de paso
arm = AA.pose.bones["RightUpArm_alfred"]; elb = AA.pose.bones["Rightelbow_alfred"]; n = 0; prev_e = Euler(ROT0r, 'XYZ')
for (fa, qa, xa, na), (fb, qb, xb, nb) in zip(sol, sol[1:]):
    for f in range(fa + (0 if fa == sol[0][0] else 1), fb + 1):
        t = ss((f - fa) / (fb - fa)); q = qa.slerp(qb, t); e = q.to_euler('XYZ', prev_e); prev_e = e
        arm.rotation_euler = e; elb.rotation_euler = (xa + (xb - xa) * t, 0, 0)
        for ax in range(3): arm.keyframe_insert("rotation_euler", index=ax, frame=f, group="RightUpArm_alfred"); n += 1
        elb.keyframe_insert("rotation_euler", index=0, frame=f, group="Rightelbow_alfred"); n += 1
        neck.rotation_euler = [NECK0[0], math.radians(na[1] + (nb[1] - na[1]) * t), math.radians(na[2] + (nb[2] - na[2]) * t)]
        for ax in (1, 2): neck.keyframe_insert("rotation_euler", index=ax, frame=f, group="Neck_alfred"); n += 1
for fcv in AA.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
    for kp in fcv.keyframe_points: kp.interpolation = 'BEZIER'
sc.frame_set(120)
print("claves", n)
