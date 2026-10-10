# -*- coding: utf-8 -*-
"""Parte 6: terminada la puerta, Alfred sale caminando por la ruta de `Desktop/alfred.json` y Jerry le sigue por detras por la de `Desktop/jerry.json` (escena viva).
Se ejecuta DENTRO de Blender con exec. Nunca `raise SystemExit`.
- Rutas: polilinea de los key_points (x, y; suelo z 14.0), con las esquinas redondeadas (radio 0.35 m); rumbo = tangente de la ruta (la rotacion inicial se mezcla en los primeros 0.35 m). Velocidad `V` (m/frame) con arranque de 6 f y frenado de ~8 f.
- Alfred: empieza en `F_ALFRED` caminando a V; ciclo de marcha procedural por distancia (zancada 1.7 m): `UpLeg` X +-25 grados (X+ = muslo hacia delante), rodilla X negativa al adelantar, brazos opuestos a las piernas (X+ = brazo hacia atras: der +B sin, izq -B sin; el derecho lleva el hacha: B pequeno), rebote de cadera (Hips loc Y) y torsion del torso. Raiz = empty `alfred` (loc + rz = rumbo - 92 grados, mantiene la rama de Euler de rz).
- Jerry: empieza `F_JERRY` frames despues (detras de Alfred); ciclo = trote de sus poses guardadas (`poses/jerry_trota_al_rincon_f10_33`, 7 frames por ciclo, huesos de las patas, restados a su media y escalados x1.4) por distancia (zancada 0.5 m); raiz = empty `jerry` con rz = rumbo - 90.
- Sonidos: un paso de pasto en cada apoyo (Alfred 0.35, Jerry 0.12) como tiras `SND_jerry_p_*`.
Variables opcionales: V, F_ALFRED, F_JERRY."""
import bpy, json, math, glob, os, re, traceback
from mathutils import Vector, Matrix, Euler

try:
    sc = bpy.context.scene
    ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
    V = float(globals().get("V", 0.05)); F_ALFRED = int(globals().get("F_ALFRED", 860)); F_JERRY = int(globals().get("F_JERRY", 875)); RADIO = 0.35
    AA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "Hips_alfred" in o.pose.bones); EA = AA.parent
    JA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "scull_1" in o.pose.bones); EJ = bpy.data.objects["jerry"]
    def cargar(p): return [(k["coordinates"]["x"], k["coordinates"]["y"]) for k in json.load(open(p, encoding="utf-8"))["key_points"]]
    RUTA_A = cargar(r"C:\Users\user\Desktop\alfred.json"); RUTA_J = cargar(r"C:\Users\user\Desktop\jerry.json")
    def ruta_suave(pts, paso=0.01):
        P = [Vector(p) for p in pts]; out = [P[0]]
        for i in range(1, len(P) - 1):
            A, Vv, B = P[i - 1], P[i], P[i + 1]; r = min(RADIO, 0.5 * (A - Vv).length, 0.5 * (B - Vv).length)
            a = Vv + (A - Vv).normalized() * r; b = Vv + (B - Vv).normalized() * r; out.append(a)
            for k in range(1, 13): t = k / 12.0; out.append((1 - t) ** 2 * a + 2 * t * (1 - t) * Vv + t * t * b)
        out.append(P[-1]); res = [out[0]]; acc = 0.0
        for q in out[1:]:                                                                  # re-muestreo por longitud de arco
            seg = q - res[-1]; d = seg.length
            while d >= paso: res.append(res[-1] + seg.normalized() * paso); seg = q - res[-1]; d = seg.length
        res.append(out[-1]); return res
    def preparar(pts, theta0):
        pts = ruta_suave(pts); n = len(pts); th = []
        for i in range(n):
            a = pts[max(i - 3, 0)]; b = pts[min(i + 3, n - 1)]; th.append(math.atan2(b.y - a.y, b.x - a.x))
        for i in range(1, n):                                                              # desenrollar el angulo
            while th[i] - th[i - 1] > math.pi: th[i] -= 2 * math.pi
            while th[i] - th[i - 1] < -math.pi: th[i] += 2 * math.pi
        d0 = th[0] - theta0
        while d0 > math.pi: d0 -= 2 * math.pi
        while d0 < -math.pi: d0 += 2 * math.pi
        th0 = theta0 + d0
        L = (n - 1) * 0.01
        def en(s):
            i = min(int(round(s / 0.01)), n - 1); k = ss(s / 0.35); return pts[i], th0 + (th[i] - th0) * k if k < 1 else th[i]
        return L, en
    def perfil(L):                                                                           # [(s, v)] por frame: arranque 6 f y frenado
        s = 0.0; out = []; t = 0
        while L - s > 0.004 and t < 2000:
            v = V * min(1.0, (t + 1) / 6.0, max(0.06, (L - s) / (V * 7.0))); s += v; out.append((min(s, L), v)); t += 1
        return out
    def desenrollar(prev, x):
        while x - prev > math.pi: x -= 2 * math.pi
        while x - prev < -math.pi: x += 2 * math.pi
        return x
    # ================= ALFRED =================
    sc.frame_set(F_ALFRED); pr = AA.matrix_world @ AA.pose.bones["Rightknee_alfred"].tail; pl = AA.matrix_world @ AA.pose.bones["Leftknee_alfred"].tail
    P_ini = Vector(((pr.x + pl.x) / 2, (pr.y + pl.y) / 2, 0)); loc0 = Vector(EA.location); rz0 = EA.rotation_euler.z; d0 = Vector((loc0.x - P_ini.x, loc0.y - P_ini.y, 0))
    theta_ini = rz0 + math.radians(92.0)
    base = {pb.name: Euler(tuple(pb.rotation_euler), 'XYZ') for pb in AA.pose.bones}; hips_loc0 = Vector(AA.pose.bones["Hips_alfred"].location)
    L, en = preparar([(P_ini.x, P_ini.y)] + RUTA_A, theta_ini); pf = perfil(L)
    print("Alfred: ruta", round(L, 2), "m ->", len(pf), "frames (hasta f", F_ALFRED + len(pf), ")")
    ZANCADA_A = 1.7; AMP_PIERNA = math.radians(25.0); AMP_BRAZO_I = math.radians(18.0); AMP_BRAZO_D = math.radians(7.0)
    phi = 0.0; rz_prev = rz0; pasos_a = []; fase_prev = 0.0; n = 0
    huesosA = ["RightUpLeg_alfred", "LeftUpLeg_alfred", "Rightknee_alfred", "Leftknee_alfred", "RightUpArm_alfred", "LeftUpArm_alfred", "Spine1_alfred"]
    def clavar(pb, f, ax_list, group):
        for ax in ax_list: pb.keyframe_insert("rotation_euler", index=ax, frame=f, group=group)
    for i, (s, v) in enumerate(pf):
        f = F_ALFRED + 1 + i; pos, th = en(s); rz = desenrollar(rz_prev, th - math.radians(92.0)); rz_prev = rz
        EA.location = Vector((pos.x, pos.y, 0)) + (Matrix.Rotation(rz - rz0, 3, 'Z') @ d0) + Vector((0, 0, loc0.z)); EA.rotation_euler = (EA.rotation_euler.x, EA.rotation_euler.y, rz)
        EA.keyframe_insert("location", frame=f); EA.keyframe_insert("rotation_euler", frame=f)
        env = min(1.0, v / V); phi += 2 * math.pi * v / ZANCADA_A; sn = math.sin(phi); cs = math.cos(phi)
        for b, lado, sg in (("RightUpLeg_alfred", 1, +1), ("LeftUpLeg_alfred", -1, -1)):
            pb = AA.pose.bones[b]; e = Euler(tuple(base[b]), 'XYZ'); e.x += sg * AMP_PIERNA * sn * env; pb.rotation_euler = e; clavar(pb, f, (0,), b)
        for b, sg in (("Rightknee_alfred", +1), ("Leftknee_alfred", -1)):
            pb = AA.pose.bones[b]; e = Euler(tuple(base[b]), 'XYZ'); flex = max(0.0, sg * cs)                      # la rodilla se dobla al adelantar la pierna (muslo subiendo hacia delante)
            e.x += -(math.radians(8.0) + math.radians(38.0) * flex ** 1.3) * env; pb.rotation_euler = e; clavar(pb, f, (0,), b)
        for b, amp, sg in (("RightUpArm_alfred", AMP_BRAZO_D, +1), ("LeftUpArm_alfred", AMP_BRAZO_I, -1)):
            pb = AA.pose.bones[b]; e = Euler(tuple(base[b]), 'XYZ'); e.x += sg * amp * sn * env; pb.rotation_euler = e; clavar(pb, f, (0,), b)
        pbH = AA.pose.bones["Hips_alfred"]; pbH.location = hips_loc0 + Vector((0, -0.025 * env * (1 - math.cos(2 * phi)) / 2, 0))
        for ax in range(3): pbH.keyframe_insert("location", index=ax, frame=f, group="Hips_alfred")
        pbS = AA.pose.bones["Spine1_alfred"]; e = Euler(tuple(base["Spine1_alfred"]), 'XYZ'); e.y += math.radians(3.0) * sn * env; pbS.rotation_euler = e; clavar(pbS, f, (1,), "Spine1_alfred")
        if int(phi / math.pi - 0.5) != int(fase_prev / math.pi - 0.5) and phi > 0.5 * math.pi: pasos_a.append(f)
        fase_prev = phi; n += 1
    FA_FIN = F_ALFRED + len(pf)
    # vuelta a la pose de pie (sin amplitud) en 6 frames y reposo
    for f in range(FA_FIN + 1, FA_FIN + 7):
        for b in huesosA:
            pb = AA.pose.bones[b]; pb.rotation_euler = base[b]; clavar(pb, f, (0, 1, 2), b)
        pbH = AA.pose.bones["Hips_alfred"]; pbH.location = hips_loc0
        for ax in range(3): pbH.keyframe_insert("location", index=ax, frame=f, group="Hips_alfred")
    for fc in AA.animation_data.action.layers[0].strips[0].channelbags[0].fcurves: pass
    EA_fcs = EA.animation_data.action.layers[0].strips[0].channelbags[0].fcurves
    for fc in EA_fcs:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    # ================= JERRY =================
    sc.frame_set(F_JERRY); J_ini = Vector((EJ.location.x, EJ.location.y)); z_j = EJ.location.z; rzJ0 = EJ.rotation_euler.z; thetaJ0 = rzJ0 + math.radians(90.0)
    D = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\jerry\refinar\poses\jerry_trota_al_rincon_f10_33"
    ciclo = []
    for fr in range(15, 22):
        p = json.load(open(os.path.join(D, f"jerry_trota_al_rincon_f{fr}.json"), encoding="utf-8"))["poses"][0]["bones"]
        ciclo.append({b: [v["local_space"]["rotation_euler_deg"][a] for a in "xyz"] for b, v in p.items()})
    variables = [b for b in ciclo[0] if max(abs(c[b][i] - ciclo[0][b][i]) for c in ciclo for i in range(3)) > 0.5 and b in JA.pose.bones]
    media = {b: [sum(c[b][i] for c in ciclo) / 7.0 for i in range(3)] for b in variables}
    baseJ = {pb.name: Euler(tuple(pb.rotation_euler), 'XYZ') for pb in JA.pose.bones}
    print("Jerry: huesos del trote:", variables)
    LJ, enJ = preparar([(J_ini.x, J_ini.y)] + RUTA_J, thetaJ0); pfJ = perfil(LJ); print("Jerry: ruta", round(LJ, 2), "m ->", len(pfJ), "frames (hasta f", F_JERRY + len(pfJ), ")")
    ZANCADA_J = 0.5; AMP_J = 1.4; phiJ = 0.0; rzJ_prev = rzJ0; pasos_j = []; nJ = 0
    for i, (s, v) in enumerate(pfJ):
        f = F_JERRY + 1 + i; pos, th = enJ(s); rz = desenrollar(rzJ_prev, th - math.radians(90.0)); rzJ_prev = rz
        EJ.location = (pos.x, pos.y, z_j); EJ.rotation_euler = (EJ.rotation_euler.x, EJ.rotation_euler.y, rz); EJ.keyframe_insert("location", frame=f); EJ.keyframe_insert("rotation_euler", frame=f)
        env = min(1.0, v / V); u = (phiJ / (2 * math.pi)) % 1.0 * 7.0; i0 = int(u) % 7; i1 = (i0 + 1) % 7; k = u - int(u)
        for b in variables:
            val = [ciclo[i0][b][c] + (ciclo[i1][b][c] - ciclo[i0][b][c]) * k for c in range(3)]; pb = JA.pose.bones[b]; e = Euler(tuple(baseJ[b]), 'XYZ')
            for c in range(3): e[c] += math.radians((val[c] - media[b][c]) * AMP_J * env)
            pb.rotation_euler = e
            for ax in range(3): pb.keyframe_insert("rotation_euler", index=ax, frame=f, group=b)
        if int(phiJ / math.pi) != int((phiJ + 2 * math.pi * v / ZANCADA_J) / math.pi): pasos_j.append(f)
        phiJ += 2 * math.pi * v / ZANCADA_J; nJ += 1
    FJ_FIN = F_JERRY + len(pfJ)
    for f in range(FJ_FIN + 1, FJ_FIN + 7):
        for b in variables:
            pb = JA.pose.bones[b]; pb.rotation_euler = baseJ[b]
            for ax in range(3): pb.keyframe_insert("rotation_euler", index=ax, frame=f, group=b)
    for fc in EJ.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    sc.frame_end = max(sc.frame_end, FA_FIN + 10, FJ_FIN + 10)
    # ================= sonidos de pasos =================
    ed = sc.sequence_editor; S = "C:\\Users\\user\\Desktop\\Alfred_Animacion\\sonidos\\sounds\\"; libre = max([s_.channel for s_ in ed.strips_all] + [30]) + 1; nS = 0
    for s_ in [s_ for s_ in ed.strips_all if str(s_.get("guion_id", "")).startswith("snd6_jerry_p_camina_")]: ed.strips.remove(s_)
    for quien, pasos, vol in (("alfred", pasos_a, 0.35), ("jerry", pasos_j, 0.12)):
        for j, f in enumerate(pasos):
            arch = f"step/grass{(j * 5 + (0 if quien == 'alfred' else 3)) % 6 + 1}.ogg"; ruta = os.path.normpath(S + arch.replace("/", "\\"))
            s_ = ed.strips.new_sound(f"SND_jerry_p_camina_{quien}_{j + 1}_{f}", ruta, libre + (j % 4) + (0 if quien == "alfred" else 4), f)
            s_.volume = vol; s_["vol_base"] = vol; s_["mcsnd"] = "pasos"; s_["mcsnd_ev"] = f"camina_{quien}"; s_["guion_id"] = f"snd6_jerry_p_camina_{quien}_{j + 1}"; nS += 1
    res = {}
    for f in (F_ALFRED, F_ALFRED + 30, F_ALFRED + 70, FA_FIN, FA_FIN + 6):
        sc.frame_set(f); pr = AA.matrix_world @ AA.pose.bones["Rightknee_alfred"].tail; pl = AA.matrix_world @ AA.pose.bones["Leftknee_alfred"].tail; res[f"A{f}"] = [round((pr.x + pl.x) / 2, 2), round((pr.y + pl.y) / 2, 2)]
    for f in (F_JERRY, F_JERRY + 40, FJ_FIN, FJ_FIN + 6): sc.frame_set(f); res[f"J{f}"] = [round(EJ.location.x, 2), round(EJ.location.y, 2)]
    sc.frame_set(120); print(res); print("pasos Alfred:", len(pasos_a), "Jerry:", len(pasos_j), "sonidos:", nS, "| frame_end:", sc.frame_end); print("LISTO")
except Exception:
    traceback.print_exc()
