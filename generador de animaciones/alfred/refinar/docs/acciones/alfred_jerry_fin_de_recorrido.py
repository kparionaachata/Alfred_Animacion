# -*- coding: utf-8 -*-
"""Parte 6: al terminar su recorrido (despues de `caminar_estudio_alfred_y_jerry.py`):
 - Alfred: su empty `alfred` pasa a rz = -450 grados (mira al este) y toma la pose `poses/parado manos en la cintura.json` (solo rotaciones de los 22 huesos; las posiciones del archivo NO se aplican: Hips z del archivo 0 vs -0.197 de la escena subiria el cuerpo). Giro sobre el centro de los pies, suavizado (smoothstep) en N_A=18 frames desde F_A (la transicion del archivo `animacion_alfred (1).py` de la pose manos en la cintura: 18 f, mismos valores; se mantiene sin el regreso a neutral del archivo).
 - Jerry: su empty `jerry` pasa a rz = 270 grados en N frames desde F_J (sus huesos siguen volviendo a la pose de pie con la mezcla del script de la marcha).
Se ejecuta DENTRO de Blender con exec. Nunca `raise SystemExit`. Variables opcionales: F_A (960), F_J (973), N (12, Jerry), N_A (18, Alfred), RZ_A (-450), RZ_J (270)."""
import bpy, json, math, traceback
from mathutils import Vector, Matrix, Euler

try:
    sc = bpy.context.scene
    ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
    F_A = int(globals().get("F_A", 960)); F_J = int(globals().get("F_J", 973)); N = int(globals().get("N", 12)); N_A = int(globals().get("N_A", 18)); RZ_A = math.radians(float(globals().get("RZ_A", -450))); RZ_J = math.radians(float(globals().get("RZ_J", 270)))
    AA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "Hips_alfred" in o.pose.bones); EA = AA.parent; EJ = bpy.data.objects["jerry"]
    POSE = json.load(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\poses\parado manos en la cintura.json", encoding="utf-8"))["poses"][0]["bones"]
    cerca = lambda b, t: b + 2 * math.pi * round((t - b) / (2 * math.pi))
    # quitar la vuelta a la pose de pie de la marcha (claves de huesos y raiz de Alfred despues de F_A)
    n = 0
    for obj, solo in ((AA, True), (EA, False)):
        for fc in obj.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
            if solo and not fc.data_path.startswith("pose.bones"): continue
            for i in range(len(fc.keyframe_points) - 1, -1, -1):
                if fc.keyframe_points[i].co.x > F_A: fc.keyframe_points.remove(fc.keyframe_points[i]); n += 1
    print("claves quitadas:", n)
    # ---------------- Alfred ----------------
    sc.frame_set(F_A)
    pr = AA.matrix_world @ AA.pose.bones["Rightknee_alfred"].tail; pl = AA.matrix_world @ AA.pose.bones["Leftknee_alfred"].tail; PIV = Vector(((pr.x + pl.x) / 2, (pr.y + pl.y) / 2, 0))
    E0 = Vector(EA.location); rz_a0 = EA.rotation_euler.z; rz_t = cerca(rz_a0, RZ_A) if abs(RZ_A - rz_a0) > math.pi else RZ_A
    S0 = {nm: tuple(AA.pose.bones[nm].rotation_euler) for nm in POSE if nm in AA.pose.bones}
    T0 = {nm: tuple(POSE[nm]["local_space"]["rotation_euler_rad"][a] for a in "xyz") for nm in S0}
    print("Alfred rz:", round(math.degrees(rz_a0), 1), "->", round(math.degrees(rz_t), 1))
    for k in range(1, N_A + 1):
        t = F_A + k; w = ss(k / N_A); rz = rz_a0 + (rz_t - rz_a0) * w
        v = E0 - Vector((PIV.x, PIV.y, E0.z)); v = Vector((PIV.x, PIV.y, E0.z)) + Matrix.Rotation(rz - rz_a0, 3, 'Z') @ v
        EA.location = v; EA.rotation_euler = (EA.rotation_euler.x, EA.rotation_euler.y, rz); EA.keyframe_insert("location", frame=t); EA.keyframe_insert("rotation_euler", frame=t)
        for nm in S0:
            pb = AA.pose.bones[nm]; s = S0[nm]; tg = [cerca(T0[nm][c], s[c]) for c in range(3)]; pb.rotation_euler = Euler(tuple(s[c] + (tg[c] - s[c]) * w for c in range(3)), 'XYZ')
            for ax in range(3): pb.keyframe_insert("rotation_euler", index=ax, frame=t, group=nm)
    # ---------------- Jerry ----------------
    sc.frame_set(F_J); rz_j0 = EJ.rotation_euler.z; rz_jt = cerca(rz_j0, RZ_J) if abs(RZ_J - rz_j0) > math.pi else RZ_J
    print("Jerry rz:", round(math.degrees(rz_j0), 1), "->", round(math.degrees(rz_jt), 1))
    for fc in EJ.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        for i in range(len(fc.keyframe_points) - 1, -1, -1):
            if fc.keyframe_points[i].co.x > F_J: fc.keyframe_points.remove(fc.keyframe_points[i])
    for k in range(1, N + 1):
        t = F_J + k; rz = rz_j0 + (rz_jt - rz_j0) * ss(k / N); EJ.rotation_euler = (EJ.rotation_euler.x, EJ.rotation_euler.y, rz); EJ.keyframe_insert("rotation_euler", frame=t); EJ.keyframe_insert("location", frame=t)
    sc.frame_end = max(sc.frame_end, F_A + N_A + 12, F_J + N + 12)
    res = {}
    for f in (F_A, F_A + N_A, F_A + N_A + 20, F_J + N, F_J + N + 20):
        sc.frame_set(f); res[f] = dict(rzA=round(math.degrees(EA.rotation_euler.z), 1), rzJ=round(math.degrees(EJ.rotation_euler.z), 1), A=[round(x, 2) for x in EA.location], J=[round(x, 2) for x in EJ.location],
                                       rk=round((AA.matrix_world @ AA.pose.bones["Rightknee_alfred"].tail).z, 2), lk=round((AA.matrix_world @ AA.pose.bones["Leftknee_alfred"].tail).z, 2))
    sc.frame_set(120); print(res); print("LISTO")
except Exception:
    traceback.print_exc()
