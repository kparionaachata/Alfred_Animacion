# -*- coding: utf-8 -*-
"""Parte 6: Alfred guarda el hacha en la espalda (f646-674): el brazo derecho sube a la espalda (pose de f569, el agarre), el hacha sigue al puno y se pega a la espalda (f654-662) y la mano vuelve a colgar (f664-674).
Se ejecuta DENTRO de Blender con exec despues de `alfred_rompe_la_mesa.py` (usa las claves del brazo en f569 y f645). Nunca `raise SystemExit`.
La espalda es la de alfred.blend (`rel_espalda_alfred_blend.json`). Las fases en mano y en la espalda se emparentan despues con `alfred_herramientas_aparentadas.py`."""
import bpy, json, math, traceback
from mathutils import Vector, Matrix, Euler, Quaternion
try:
    sc = bpy.context.scene
    AA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "Hips_alfred" in o.pose.bones)
    ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
    axe = bpy.data.objects["stone_axe"]; axe.rotation_mode = 'QUATERNION'
    _RAB = json.load(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\rel_espalda_alfred_blend.json", encoding="utf-8")); _m = _RAB["herramientas"]["stone_axe"]["matriz"]; REL = Matrix([_m[0:4], _m[4:8], _m[8:12], _m[12:16]])
    arm = AA.pose.bones["RightUpArm_alfred"]; elb = AA.pose.bones["Rightelbow_alfred"]
    sc.frame_set(645); H_UP = Euler(tuple(arm.rotation_euler), 'XYZ'); H_EL = tuple(elb.rotation_euler)
    sc.frame_set(569); B_UP = Euler(tuple(arm.rotation_euler), 'XYZ'); B_EL = tuple(elb.rotation_euler)
    sc.frame_set(562); Sp1 = AA.matrix_world @ AA.pose.bones["Spine1_alfred"].matrix; l_b, q_b, s_b = (Sp1 @ REL).decompose(); ESC = Vector(s_b)
    G_LOC = Vector((-0.375, -0.438, 0)) + (Vector((0.188, 0.438, 0)) - Vector((-0.375, -0.438, 0))) * 0.30; u_loc = Vector((0.563, 0.876, 0)).normalized(); d_back = (q_b.to_matrix() @ u_loc).normalized(); D_HANG = Vector((-0.10, 0.0, -1.0)).normalized()
    T0, T1, T2, T3 = 648, 658, 664, 674
    def estado_brazo(f):
        if f <= T0: t = 0.0
        elif f <= T1: t = ss((f - T0) / (T1 - T0))
        elif f <= T2: t = 1.0
        else: t = 1 - ss((f - T2) / (T3 - T2))
        q = H_UP.to_quaternion().slerp(B_UP.to_quaternion(), t); e = q.to_euler('XYZ', H_UP) if 0 < t < 1 else (B_UP if t >= 1 else H_UP)
        return e, tuple(H_EL[i] + (B_EL[i] - H_EL[i]) * t for i in range(3))
    for f in range(646, 676):
        e, ex = estado_brazo(f); arm.rotation_euler = e; elb.rotation_euler = ex
        for ax in range(3): arm.keyframe_insert("rotation_euler", index=ax, frame=f, group="RightUpArm_alfred"); elb.keyframe_insert("rotation_euler", index=ax, frame=f, group="Rightelbow_alfred")
    def M_hacha(grip, d):
        E1 = d.normalized(); cand = Vector((0, 1, 0)); E3 = cand if (cand.cross(E1).z) <= 0 else -cand; E3 = (E3 - E1 * E3.dot(E1)).normalized(); E2 = E3.cross(E1)
        e1 = u_loc; e3 = Vector((0, 0, 1)); e2 = e3.cross(e1); Rw = Matrix(((E1.x, E2.x, E3.x), (E1.y, E2.y, E3.y), (E1.z, E2.z, E3.z))); Rl = Matrix(((e1.x, e2.x, e3.x), (e1.y, e2.y, e3.y), (e1.z, e2.z, e3.z)))
        R = Rw @ Rl.transposed(); pos = grip - R @ Vector((G_LOC.x * ESC.x, G_LOC.y * ESC.y, G_LOC.z * ESC.z)); return Matrix.Translation(pos) @ R.to_4x4() @ Matrix.Diagonal(ESC).to_4x4()
    def poner(f, M):
        l, q, s = M.decompose(); axe.location = l; axe.rotation_quaternion = q; axe.scale = s
        axe.keyframe_insert("location", frame=f); axe.keyframe_insert("rotation_quaternion", frame=f); axe.keyframe_insert("scale", frame=f)
    for f in range(646, 700):
        sc.frame_set(f); Spf = AA.matrix_world @ AA.pose.bones["Spine1_alfred"].matrix; Mg = Spf @ REL
        if f <= 664:
            h = AA.matrix_world @ AA.pose.bones["Rightelbow_alfred"].head; tl = AA.matrix_world @ AA.pose.bones["Rightelbow_alfred"].tail; df = (tl - h).normalized(); grip = h + df * 0.34
            da = D_HANG.lerp(d_back, ss((f - 646) / 10.0)).normalized(); Mh = M_hacha(grip, da); t = ss((f - 654) / 8.0)
            lh, qh, sh_ = Mh.decompose(); lg, qg, sg = Mg.decompose(); poner(f, Matrix.Translation(lh.lerp(lg, t)) @ qh.slerp(qg, t).to_matrix().to_4x4() @ Matrix.Diagonal(ESC).to_4x4())
        else: poner(f, Mg)
    for fc in AA.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        if "RightUpArm" in fc.data_path or "Rightelbow" in fc.data_path:
            for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'
    for fc in axe.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    sc.frame_set(120); print("LISTO guardar hacha")
except Exception:
    traceback.print_exc()
