# -*- coding: utf-8 -*-
"""ANIMACION DEL BRAZO DERECHO HACIA LA ESPALDA para sacar / guardar una herramienta, del archivo del usuario `Downloads/animacion_alfred (1).py` ("llevar_brazo_derecho_espalda_alfred", 32 frames a 24 fps: ida 16 f -- llega a la espalda en el 13.o (indice 12) y pausa --,
regreso 12 f y pausa inicial 4 f). Euler XYZ del brazo derecho (hombro `RightUpArm_alfred` y codo `Rightelbow_alfred`); el brazo izquierdo no se mueve en ese archivo (nota: el usuario lo llamo "brazo izquierdo" pero el archivo es del brazo DERECHO, el que lleva a la espalda).
Pose de la espalda del archivo: RightUpArm (266.17, -35.4, 190.21) = (-93.83, -35.4, 190.21) en nuestra rama de Euler (X - 360), Rightelbow (7.8244, -2.384, -111.53). Los valores bajan por canal (negativos, antihorario).
Se usa el REPARTO por canal del archivo (progreso de cada canal Euler) entre la pose de partida real y la de la espalda: si el brazo parte colgando (X -90, Y 180, Z 180) es identico al archivo.
Tramos: (1) sacar para la mesa: ida f554-566, pausa f567-569, agarre en f569 (el hacha pasa a la mano), mano -> lista f569-574; (2) guardar: ida f646-658, pausa f659-661, el hacha vuelve a la espalda en f662, regreso f662-673; (3) sacar para la puerta: ida f742-754, pausa f755-757, agarre en f757, mano -> lista f757-762.
Se ejecuta DENTRO de Blender con exec despues de `alfred_herramientas_aparentadas.py` (reescribe las claves del hombro f554-860 como cadena de Euler continua y recalcula el `basis` de `Mano` del hacha en las mezclas). Nunca `raise SystemExit`."""
import bpy, json, math, traceback
from mathutils import Vector, Matrix, Euler, Quaternion
try:
    sc = bpy.context.scene
    AA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "Hips_alfred" in o.pose.bones)
    ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
    axe = bpy.data.objects["stone_axe"]; arm = AA.pose.bones["RightUpArm_alfred"]; elb = AA.pose.bones["Rightelbow_alfred"]
    PL = {k: {"rotation_euler": list(v) + list(reversed(v[:12])) + [v[0]] * 4} for k, v in json.load(open("C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/animacion_brazo_derecho_espalda.json", encoding="utf-8")).items() if k.startswith("Right")}   # animacion del usuario (copia local del archivo de Descargas)
    VA = [(a, b, c) for a, b, c in PL["RightUpArm_alfred"]["rotation_euler"]]; VE = [tuple(v) for v in PL["Rightelbow_alfred"]["rotation_euler"]]
    VA = [(x - 2 * math.pi if x > math.pi else x, y, z) for x, y, z in VA]                            # X 266-270 grados -> -94..-90 (misma rama que nuestro brazo colgando)
    print("frames del archivo:", len(VA), "| espalda hombro (grados):", [round(math.degrees(x), 2) for x in VA[12]], "codo:", [round(math.degrees(x), 2) for x in VE[12]])
    RAB = json.load(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\rel_espalda_alfred_blend.json", encoding="utf-8")); m = RAB["herramientas"]["stone_axe"]["matriz"]; REL = Matrix([m[0:4], m[4:8], m[8:12], m[12:16]])
    F0, F1 = 554, 860
    def progreso(V, idx):                                                                            # progreso por canal (0 = inicio, 1 = espalda) del archivo
        out = []
        for c in range(3):
            d = V[12][c] - V[0][c]; out.append((V[idx][c] - V[0][c]) / d if abs(d) > 1e-9 else 0.0)
        return out
    def desde_archivo(V, S, idx, B=None):                                                            # pose en el indice idx del archivo, partiendo de S y llegando a la espalda del archivo (o a B, su equivalente en otra rama de Euler)
        p = progreso(V, idx); B = B if B is not None else V[12]; return Euler(tuple(S[c] + (B[c] - S[c]) * p[c] for c in range(3)), 'XYZ')
    # ---- 1) cuaternion actual por frame (para los frames que NO cambian) y estados de partida ----
    Q = {}; EL = {}
    for f in range(F0 - 8, F1 + 2):
        sc.frame_set(f); Q[f] = Euler(tuple(arm.rotation_euler), 'XYZ').to_quaternion(); EL[f] = Euler(tuple(elb.rotation_euler), 'XYZ')
    sc.frame_set(F0 - 1); S1 = Euler(tuple(arm.rotation_euler), 'XYZ'); S1E = Euler(tuple(elb.rotation_euler), 'XYZ')
    sc.frame_set(645); S2 = Euler(tuple(arm.rotation_euler), 'XYZ'); S2E = Euler(tuple(elb.rotation_euler), 'XYZ')
    sc.frame_set(741); S3 = Euler(tuple(arm.rotation_euler), 'XYZ'); S3E = Euler(tuple(elb.rotation_euler), 'XYZ')
    print("partida mesa:", [round(math.degrees(x), 1) for x in S1], "| guardar:", [round(math.degrees(x), 1) for x in S2], "| puerta:", [round(math.degrees(x), 1) for x in S3])
    E = {}; EN = {}
    def lerp_e(A, Bq, t): return Euler(tuple(A[i] + (Bq[i] - A[i]) * t for i in range(3)), 'XYZ')
    def cadena(f, prev): return Q[f].to_euler('XYZ', prev)
    BA = Euler(VA[12], 'XYZ'); BE = Euler(VE[12], 'XYZ')
    # tramo 1: mesa. El hombro parte de lo que haya en f553 (colgando)
    for f in range(F0, 570):
        i = min(f - F0, 15); E[f] = desde_archivo(VA, S1, i); EN[f] = desde_archivo(VE, S1E, i)
    E574 = Q[574].to_euler('XYZ', BA)
    for f in range(570, 575): t = ss((f - 569) / 5.0); E[f] = lerp_e(BA, E574, t); EN[f] = lerp_e(BE, EL[574], t)
    for f in range(575, 646): E[f] = cadena(f, E[f - 1])
    # tramo 2: guardar. ida 646-658, pausa 659-661, regreso 662-673 (indices 16-27 del archivo), 674 = colgando (misma representacion que f645)
    HANG = Euler(tuple(E[645]), 'XYZ'); HANGE = Euler(tuple(EL[645]), 'XYZ')
    for f in range(646, 662): i = min(f - 646, 15); E[f] = desde_archivo(VA, HANG, i); EN[f] = desde_archivo(VE, HANGE, i)
    for f in range(662, 674): i = 16 + (f - 662); E[f] = desde_archivo(VA, HANG, i); EN[f] = desde_archivo(VE, HANGE, i)
    E[674] = HANG; EN[674] = HANGE
    for f in range(675, 742): E[f] = cadena(f, E[f - 1])
    # tramo 3: puerta. ida 742-754, pausa 755-757, mano -> lista 758-762
    S3 = Euler(tuple(E[741]), 'XYZ')
    B3 = list(VA[12])
    for c in range(3):                                                                              # rama de Euler de la espalda mas cercana a la partida (en la puerta la partida es la pose de pie de Mixamo: Z -28 -> -169.8 en vez de +190.2, valores negativos)
        for k in (-2 * math.pi, 0.0, 2 * math.pi):
            if abs(VA[12][c] + k - S3[c]) < abs(B3[c] - S3[c]): B3[c] = VA[12][c] + k
    B3 = Euler(tuple(B3), 'XYZ'); print("espalda en la puerta (rama de Euler):", [round(math.degrees(x), 1) for x in B3])
    for f in range(742, 758): i = min(f - 742, 15); E[f] = desde_archivo(VA, S3, i, B3); EN[f] = desde_archivo(VE, S3E, i)
    E762 = Q[762].to_euler('XYZ', B3)
    for f in range(758, 763): t = ss((f - 757) / 5.0); E[f] = lerp_e(B3, E762, t); EN[f] = lerp_e(BE, EL[762], t)
    for f in range(763, F1 + 1): E[f] = cadena(f, E[f - 1])
    # ---- 2) escribir ----
    n = 0
    for f in range(F0, F1 + 1):
        arm.rotation_euler = E[f]
        for ax in range(3): arm.keyframe_insert("rotation_euler", index=ax, frame=f, group="RightUpArm_alfred"); n += 1
        if f in EN:
            elb.rotation_euler = EN[f]
            for ax in range(3): elb.keyframe_insert("rotation_euler", index=ax, frame=f, group="Rightelbow_alfred"); n += 1
    for fc in AA.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        if "RightUpArm" in fc.data_path or "Rightelbow" in fc.data_path:
            for kp in fc.keyframe_points: kp.interpolation = 'LINEAR' if (F0 <= kp.co.x <= 569 or 646 <= kp.co.x <= 674 or 742 <= kp.co.x <= 757) else 'BEZIER'          # tramos del archivo: lineal, como el original
    print("claves reescritas:", n)
    # ---- 3) hacha: basis relativo a la mano donde se mezcla con la espalda ----
    sc.frame_set(562); l_b, q_b, s_b = (AA.matrix_world @ AA.pose.bones["Spine1_alfred"].matrix @ REL).decompose(); ESC = Vector(s_b)
    G_LOC = Vector((-0.375, -0.438, 0)) + (Vector((0.188, 0.438, 0)) - Vector((-0.375, -0.438, 0))) * 0.30; u_loc = Vector((0.563, 0.876, 0)).normalized(); e1 = u_loc; e3 = Vector((0, 0, 1)); e2 = e3.cross(e1)
    vs = [v.co.copy() for v in axe.data.vertices]; ordenados = sorted(vs, key=lambda v: v.dot(e1)); cab = ordenados[-max(1, len(vs) // 4):]; S_BLADE = 1.0 if sum(v.dot(e2) for v in cab) / len(cab) >= 0 else -1.0
    D_HANG = Vector((-0.10, 0.0, -1.0)).normalized(); D_READY_Y = Vector((-0.55, 0.0, 0.83)).normalized(); D_READY_X = Vector((0.0, 0.55, 0.83)).normalized(); d_back = (q_b.to_matrix() @ u_loc).normalized()
    def M_hacha(grip, d, lat):
        E1 = d.normalized(); E3 = lat if (S_BLADE * lat.cross(E1).z) <= 0 else -lat; E3 = (E3 - E1 * E3.dot(E1)).normalized(); E2 = E3.cross(E1)
        Rw = Matrix(((E1.x, E2.x, E3.x), (E1.y, E2.y, E3.y), (E1.z, E2.z, E3.z))); Rl = Matrix(((e1.x, e2.x, e3.x), (e1.y, e2.y, e3.y), (e1.z, e2.z, e3.z)))
        R = Rw @ Rl.transposed(); pos = grip - R @ Vector((G_LOC.x * ESC.x, G_LOC.y * ESC.y, G_LOC.z * ESC.z)); return Matrix.Translation(pos) @ R.to_4x4() @ Matrix.Diagonal(ESC).to_4x4()
    def Mb_de(f): sc.frame_set(f); return AA.matrix_world @ AA.pose.bones["Spine1_alfred"].matrix @ REL
    def mano(f): sc.frame_set(f); return AA.matrix_world @ AA.pose.bones["Rightelbow_alfred"].matrix
    def grip_de(f):
        sc.frame_set(f); h = AA.matrix_world @ AA.pose.bones["Rightelbow_alfred"].head; t = AA.matrix_world @ AA.pose.bones["Rightelbow_alfred"].tail; return h + (t - h).normalized() * 0.34
    def fijar_basis(f, W):
        Mn = mano(f).inverted() @ W; l, q, s = Mn.decompose(); axe.location = l; axe.rotation_quaternion = q; axe.scale = s
        axe.keyframe_insert("location", frame=f); axe.keyframe_insert("rotation_quaternion", frame=f); axe.keyframe_insert("scale", frame=f)
    def blend(Ma, Mb2, t):
        la, qa, sa = Ma.decompose(); lb, qb, sb = Mb2.decompose(); return Matrix.Translation(la.lerp(lb, t)) @ qa.slerp(qb, t).to_matrix().to_4x4() @ Matrix.Diagonal(ESC).to_4x4()
    LATY = Vector((0, 1, 0)); LATX = Vector((1, 0, 0))
    for f in range(569, 574):
        k = ss((f - 562) / 4.0) if f <= 566 else 1.0; da = D_HANG.lerp(D_READY_Y, k).normalized(); fijar_basis(f, blend(Mb_de(f), M_hacha(grip_de(f), da, LATY), ss((f - 569) / 6.0)))
    for f in range(646, 662):                                                                          # guardar: la mano llega en f658; el hacha vuelve a la espalda f656-662
        da = D_HANG.lerp(d_back, ss((f - 646) / 12.0)).normalized(); fijar_basis(f, blend(M_hacha(grip_de(f), da, LATY), Mb_de(f), ss((f - 656) / 6.0)))
    for f in range(757, 762):
        k = ss((f - 750) / 4.0) if f <= 754 else 1.0; da = D_HANG.lerp(D_READY_X, k).normalized(); fijar_basis(f, blend(Mb_de(f), M_hacha(grip_de(f), da, LATX), ss((f - 757) / 6.0)))
    for fc in axe.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT' if "influence" in fc.data_path else 'LINEAR'
    # ---- 4) verificacion ----
    mx = 0.0; en = None
    for f in range(F0 + 1, F1 + 1):
        d = max(abs(math.degrees(E[f][i] - E[f - 1][i])) for i in range(3))
        if d > mx: mx, en = d, f
    print("maximo cambio de Euler por frame (hombro):", round(mx, 1), "grados en f", en)
    for fr in (554, 557, 560, 563, 566, 569, 572, 574): print(" mesa", fr, [round(math.degrees(x), 1) for x in E[fr]])
    sc.frame_set(566); fist = grip_de(566); grip = axe.matrix_world @ G_LOC
    print("puno vs agarre del hacha en f566:", round((fist - grip).length, 3), "m")
    sc.frame_set(120); print("LISTO")
except Exception:
    traceback.print_exc()
