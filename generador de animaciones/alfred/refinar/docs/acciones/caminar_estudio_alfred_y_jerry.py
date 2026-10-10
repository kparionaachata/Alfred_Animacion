# -*- coding: utf-8 -*-
"""Parte 6: Alfred y Jerry salen caminando con los CICLOS DE CAMINAR DE LOS ESTUDIOS (estilo NORMAL):
 - Alfred = `alfred_animation_studio/generate_slots_alfred.py::generate_caminar` (ciclo biomecanico: piernas/rodillas/brazos/codos/cadera/columna/cuello, 20 f por ciclo, 12.43 f por bloque, angulo cardinal/diagonal con suavizado de 12 f).
 - Jerry  = `jerry_animation_studio/generate_slots_jerry.py::generate_caminar` (SniffingSearchCycle, ciclo de 25 f, patas/columna/cola/cabeza/orejas, mismo suavizado de giro).
Rutas: `Desktop/alfred.json` y `Desktop/jerry.json` (se antepone la posicion actual de cada uno). Jerry usa el mismo ritmo que Alfred (12.43 f por bloque, el estudio deja ese parametro `frames_por_bloque` libre) para ir DETRAS de el.
Se ejecuta DENTRO de Blender con exec. Nunca `raise SystemExit`. Borra la marcha anterior (claves de huesos/raiz desde S_A / S_J y sonidos `snd6_jerry_p_camina_alfred_*` / `_jerry_*`) y mezcla los primeros 6 f desde la pose en que quedaron.
Despues de este script hay que volver a ejecutar `alfred_guarda_el_hacha_caminando.py` (sus claves del brazo derecho f869-901 se borran aqui).
Variables opcionales: S_A (861), S_J (876), FPB_J (12.43)."""
import bpy, json, math, os, traceback
from mathutils import Vector, Matrix, Euler

try:
    sc = bpy.context.scene
    ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
    S_A = int(globals().get("S_A", 861)); S_J = int(globals().get("S_J", 876)); FPB_J = float(globals().get("FPB_J", 60.0 / 4.8284)); MEZ = 6
    AA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "Hips_alfred" in o.pose.bones); EA = AA.parent
    JA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "scull_1" in o.pose.bones); EJ = bpy.data.objects["jerry"]
    def cargar(p): return [(k["coordinates"]["x"], k["coordinates"]["y"], k["coordinates"]["z"]) for k in json.load(open(p, encoding="utf-8"))["key_points"]]
    RUTA_A = cargar(r"C:\Users\user\Desktop\alfred.json"); RUTA_J = cargar(r"C:\Users\user\Desktop\jerry.json")
    # ---------- 0. borrar la marcha anterior ----------
    def borrar(obj, desde, solo_huesos):
        n = 0
        for fc in obj.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
            if solo_huesos and not fc.data_path.startswith("pose.bones"): continue
            for i in range(len(fc.keyframe_points) - 1, -1, -1):
                if fc.keyframe_points[i].co.x >= desde: fc.keyframe_points.remove(fc.keyframe_points[i]); n += 1
        return n
    print("borradas:", borrar(AA, S_A, True), borrar(EA, S_A, False), borrar(JA, S_J, True), borrar(EJ, S_J, False))
    ed = sc.sequence_editor
    for s_ in [s_ for s_ in ed.strips_all if str(s_.get("guion_id", "")).startswith(("snd6_jerry_p_camina_alfred_", "snd6_jerry_p_camina_jerry_"))]: ed.strips.remove(s_)
    # ---------- comunes (copiados de los estudios) ----------
    class RotationSmoother:
        def __init__(self, smoothing_frames=12):
            self.smoothing_frames = smoothing_frames; self.previous_rotation = None; self.transition_start_frame = None; self.transition_start_rotation = None; self.target_rotation = None
        def smooth_rotation(self, target_rotation, current_frame):
            target_rotation = self._normalize(target_rotation)
            if self.previous_rotation is None:
                self.previous_rotation = target_rotation; return target_rotation
            angle_diff = self._diff(target_rotation, self.previous_rotation)
            if abs(angle_diff) < 5:
                self.previous_rotation = target_rotation; self.transition_start_frame = None; return target_rotation
            if self.transition_start_frame is None:
                self.transition_start_frame = current_frame; self.transition_start_rotation = self.previous_rotation; self.target_rotation = target_rotation
            elapsed = current_frame - self.transition_start_frame; progress = min(elapsed / self.smoothing_frames, 1.0); eased = self._smoothstep(progress)
            smoothed = self.transition_start_rotation + self._diff(self.target_rotation, self.transition_start_rotation) * eased
            if progress >= 1.0:
                self.previous_rotation = target_rotation; self.transition_start_frame = None; return target_rotation
            return smoothed
        def _normalize(self, a):
            while a > 180: a -= 360
            while a < -180: a += 360
            return a
        def _diff(self, target, current):
            d = target - current
            while d > 180: d -= 360
            while d < -180: d += 360
            return d
        def _smoothstep(self, x):
            if x <= 0: return 0.0
            if x >= 1: return 1.0
            return x * x * (3.0 - 2.0 * x)
    def dir_angle(p0, p1, jerry):
        dx = p1[0] - p0[0]; dy = p1[1] - p0[1]
        if dx == 0 and dy == 0: return None
        ang_raw = math.degrees(math.atan2(dx, dy)); ang_rounded = round(ang_raw / 90.0) * 90.0
        ang = ang_rounded if abs(ang_raw - ang_rounded) < 45 else -ang_raw
        while ang > 180: ang -= 360
        while ang < -180: ang += 360
        if ang == 90: ang = -90
        elif ang == -90: ang = 90
        if jerry and ang == 180: ang = -180
        return ang
    def asignar(segs, total):
        dists = [max(0.0001, math.sqrt(sum((e[i] - s[i]) ** 2 for i in range(3)))) for s, e in segs]; td = sum(dists) or 1.0
        bf = [max(1, int(round(total * (d / td)))) for d in dists]; diff = total - sum(bf); i = 0
        while diff != 0:
            if diff > 0: bf[i % len(bf)] += 1; diff -= 1
            elif bf[i % len(bf)] > 1: bf[i % len(bf)] -= 1; diff += 1
            i += 1
        cum = []; acc = 0
        for f in bf: acc += f; cum.append(acc)
        return bf, cum
    def pos_de(segs, fps, cum, frame, estricto):                                       # estricto=True: `frame < cf` (Alfred, 0-indexado) / False: `frame <= cf` (Jerry, 1-indexado)
        prev = 0
        for j, cf in enumerate(cum):
            if (frame < cf) if estricto else (frame <= cf):
                s, e = segs[j]; f = max(0.0, min(1.0, (frame - prev) / max(1, fps[j]))); return tuple(s[i] + (e[i] - s[i]) * f for i in range(3))
            prev = cf
        return tuple(segs[-1][1])
    def ang_de(segs, cum, frame, estricto, jerry):
        for j, cf in enumerate(cum):
            if (frame < cf) if estricto else (frame <= cf):
                a = dir_angle(segs[j][0], segs[j][1], jerry); return a if a is not None else 0.0
        a = dir_angle(segs[-1][0], segs[-1][1], jerry); return a if a is not None else 0.0
    def cerca(b, t): return b + 2 * math.pi * round((t - b) / (2 * math.pi))             # equivalente de b (rama de Euler) mas cercano a t
    def desenrollar(prev, x):
        while x - prev > 180: x -= 360
        while x - prev < -180: x += 360
        return x
    def poner(pb, t, tgt, base, w):                                                       # mezcla desde la pose base -> valor del estudio
        e = [cerca(base[c], tgt[c]) for c in range(3)]; pb.rotation_euler = Euler(tuple(e[c] + (tgt[c] - e[c]) * w for c in range(3)), 'XYZ')
        for ax in range(3): pb.keyframe_insert("rotation_euler", index=ax, frame=t, group=pb.name)
    def fin_mezcla(pbs, bases, t_fin):                                                    # vuelve a la pose en que estaban antes de caminar
        for nm, pb in pbs.items():
            pb.rotation_euler = Euler(tuple(bases[nm]), 'XYZ')
            for ax in range(3): pb.keyframe_insert("rotation_euler", index=ax, frame=t_fin, group=pb.name)
    # ================= ALFRED =================
    sc.frame_set(S_A - 1)
    pr = AA.matrix_world @ AA.pose.bones["Rightknee_alfred"].tail; pl = AA.matrix_world @ AA.pose.bones["Leftknee_alfred"].tail
    P_ini = Vector(((pr.x + pl.x) / 2, (pr.y + pl.y) / 2, 0)); loc0 = Vector(EA.location); rz0 = EA.rotation_euler.z; d0 = Vector((loc0.x - P_ini.x, loc0.y - P_ini.y, 0)); rz0d = math.degrees(rz0)
    NB_A = ["Hips_alfred", "Spine_alfred", "Spine1_alfred", "Spine2_alfred", "Neck_alfred", "RightUpArm_alfred", "Rightelbow_alfred", "LeftUpArm_alfred", "Leftelbow_alfred", "RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred"]
    PBA = {n: AA.pose.bones[n] for n in NB_A}; BASE_A = {n: tuple(PBA[n].rotation_euler) for n in NB_A}
    ptsA = [(P_ini.x, P_ini.y, 14.0)] + RUTA_A; segA = [(ptsA[i], ptsA[i + 1]) for i in range(len(ptsA) - 1)]
    FPU = 60.0 / 4.8284; CICLO = 20.0; HALF = CICLO / 2.0; dist = sum(math.hypot(e[0] - s[0], e[1] - s[1]) for s, e in segA)
    n_half = max(1, round(dist * FPU / HALF)); TOT_A = max(1, round(n_half * HALF)); WC = TOT_A / CICLO; E_A = S_A + TOT_A - 1
    fpsA, cumA = asignar(segA, TOT_A)
    print("Alfred: ruta", round(dist, 2), "bloques ->", TOT_A, "frames (f", S_A, "-", E_A, ") ciclos:", WC)
    R = dict(arm_base_x=math.radians(90), arm_swing_y=math.radians(70), elbow_flex=math.radians(50), leg_swing_x=math.radians(50), knee_flex=math.radians(40), hip_forward=math.radians(3), hip_sway=math.radians(4), hip_tilt=math.radians(4), spine_bend=math.radians(0.1), neck_tilt=math.radians(1.5), head_stab=0.25)
    ease_s = lambda t: -(math.cos(math.pi * t) - 1) / 2
    ease_c = lambda t: 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2
    def leg_swing(ph): return R['leg_swing_x'] * math.sin(ph * 2 * math.pi)
    def arm_swing(ph):
        m = R['arm_swing_y']
        if ph < 0.5: return ease_s(ph / 0.5) * m * 2 - m
        return m - ease_s((ph - 0.5) / 0.5) * m * 2
    def elbow(ph):
        m = R['elbow_flex']
        if ph < 0.3: return ease_s(ph / 0.3) * m * 0.85 + m * 0.15
        if ph < 0.7: return m - ease_c((ph - 0.3) / 0.4) * m * 0.6
        return m * 0.4 - ease_s((ph - 0.7) / 0.3) * m * 0.25
    def knee(ph): return R['knee_flex'] * max(0.0, math.sin((ph - 0.75) * 2 * math.pi))
    def pose_alfred(wc):
        sf = math.sin(wc * 2 * math.pi + math.pi / 6) * R['spine_bend']; st = math.cos(wc * 2 * math.pi + math.pi / 3) * R['spine_bend'] * 0.75
        hf = -sf * 0.3 + R['hip_forward'] * math.sin(wc * 2 * math.pi); hs = math.sin(wc * 2 * math.pi + math.pi / 4) * R['hip_sway']; ht = math.sin(wc * 2 * math.pi) * R['hip_tilt']
        nf = -sf * R['head_stab']; nt = math.sin(wc * 2 * math.pi) * R['neck_tilt']; ns = math.cos(wc * 2 * math.pi + math.pi / 4) * R['neck_tilt'] * 0.5
        rc = (wc + 0.5) % 1.0; ra = (wc + 0.25) % 1.0; la = (wc + 0.75) % 1.0
        return {"Hips_alfred": (hf, hs, ht), "Spine_alfred": (sf, 0, st), "Spine1_alfred": (sf, 0, st), "Spine2_alfred": (sf, 0, st), "Neck_alfred": (nf, ns, nt),
                "LeftUpLeg_alfred": (leg_swing(wc), 0, 0), "Leftknee_alfred": (-knee(wc), 0, 0), "RightUpLeg_alfred": (leg_swing(rc), 0, 0), "Rightknee_alfred": (-knee(rc), 0, 0),
                "RightUpArm_alfred": (R['arm_base_x'], arm_swing(ra), 0), "Rightelbow_alfred": (0, 0, -elbow(ra)), "LeftUpArm_alfred": (R['arm_base_x'], -arm_swing(la), 0), "Leftelbow_alfred": (0, 0, elbow(la))}
    smA = RotationSmoother(12); smA.previous_rotation = 0.0; rzp = rz0d; angA = {}
    for t in range(S_A, E_A + 1):
        pf = t - S_A; pos = pos_de(segA, fpsA, cumA, pf, True) if pf < TOT_A else tuple(segA[-1][1]); a = smA.smooth_rotation(ang_de(segA, cumA, pf, True, False), t)
        rzd = desenrollar(rzp, rz0d + a); rzp = rzd; rz = math.radians(rzd); angA[t] = rz - rz0
        EA.location = Vector((pos[0], pos[1], 0)) + (Matrix.Rotation(rz - rz0, 3, 'Z') @ d0) + Vector((0, 0, loc0.z)); EA.rotation_euler = (EA.rotation_euler.x, EA.rotation_euler.y, rz)
        EA.keyframe_insert("location", frame=t); EA.keyframe_insert("rotation_euler", frame=t)
        w = ss((t - (S_A - 1)) / MEZ); P = pose_alfred((t - S_A) / max(1, E_A - S_A) * WC)
        for n in NB_A: poner(PBA[n], t, P[n], BASE_A[n], w)
    fin_mezcla(PBA, BASE_A, E_A + 8)
    FA_FIN = E_A
    # ================= JERRY =================
    sc.frame_set(S_J - 1); J_ini = (EJ.location.x, EJ.location.y, EJ.location.z); rxJ, ryJ = EJ.rotation_euler.x, EJ.rotation_euler.y; rzJ0d = math.degrees(EJ.rotation_euler.z)
    NB_J = ['shoulder.L', 'shoulder.R', 'thigh.L', 'thigh.R', 'shin.L', 'shin.R', 'foot.L', 'foot.R', 'toe.L', 'toe.R', 'front_shoulder.L', 'front_shoulder.R', 'front_thigh.L', 'front_thigh.R', 'front_shin.L', 'front_shin.R', 'front_foot.L', 'front_foot.R', 'front_toe.L', 'front_toe.R',
            'spine_1', 'spine_2', 'spine_3', 'spine_4', 'spine_5', 'spine_6', 'spine_7', 'tail_1', 'tail_2', 'tail_3', 'scull', 'jaw_top', 'ear.L', 'ear.R', 'sombrero']
    PBJ = {n: JA.pose.bones[n] for n in NB_J}; BASE_J = {n: tuple(PBJ[n].rotation_euler) for n in NB_J}
    print("Jerry base no nula:", {n: [round(math.degrees(x), 1) for x in BASE_J[n]] for n in ('scull', 'jaw_top', 'sombrero', 'tail_1', 'ear.L') })
    ptsJ = [J_ini] + [(x, y, J_ini[2]) for x, y, z in RUTA_J]; segJ = [(ptsJ[i], ptsJ[i + 1]) for i in range(len(ptsJ) - 1)]
    distJ = sum(math.hypot(e[0] - s[0], e[1] - s[1]) for s, e in segJ); TOT_J = max(24, round(distJ * FPB_J)); E_J = S_J + TOT_J - 1; CL = 25
    fpsJ, cumJ = asignar(segJ, TOT_J)
    print("Jerry: ruta", round(distJ, 2), "bloques ->", TOT_J, "frames (f", S_J, "-", E_J, ")")
    def sw(fr, period, amp, phase=0, off=0): return amp * math.sin(2 * math.pi * fr / period + phase) + off
    def nrm(fr): return ((fr - 1) % CL) + 1
    def leg_slow(fr, rear, left):
        n = nrm(fr); ph = 0 if left else math.pi; amp = 0.4 if rear else 0.3
        return (-sw(n, CL, amp, ph), -sw(n, CL, amp * 0.15, ph), -sw(n, CL, amp * 0.03, ph))
    def leg_bend(fr, rear, left):
        n = nrm(fr); ph = 0 if left else math.pi; bb = 0.3 if rear else 0.24
        return (-abs(sw(n, CL, bb, ph, bb)), -sw(n, CL, 0.1, ph), -sw(n, CL, 0.04, ph))
    def foot_strike(fr, rear, left):
        n = nrm(fr); ph = 0 if left else math.pi; ax = 0.8 if rear else 0.6
        return (-sw(n, CL, ax, ph, 0.4 if rear else -0.1), abs(sw(n, CL, 0.04, ph, 0.02)) * (1.0 if rear else 0.5), -sw(n, CL, 0.04 if rear else 0.06, ph, 0.02))
    def toe_curl(fr, rear, left):
        n = nrm(fr); ph = 0 if left else math.pi
        return (abs(sw(n, CL, 0.5, ph, 0.4)), -sw(n, CL, 0.16, ph), -sw(n, CL, 0.08, ph, 0.04))
    def tail_wag(fr):
        n = nrm(fr); return (sw(n, CL, 0.4, 0, 0.2), sw(n, CL, 0.06), sw(n, CL, 0.16))
    def ear_tw(fr):
        n = nrm(fr); return (0, sw(n, CL, 0.2), sw(n, CL, 0.1))
    def pose_jerry(fr):
        k = {}; mul = lambda v, m: tuple(x * m for x in v)
        k['shoulder.L'] = leg_slow(fr, True, True); k['shoulder.R'] = leg_slow(fr, True, False); k['thigh.L'] = mul(leg_slow(fr, True, True), 0.01); k['thigh.R'] = mul(leg_slow(fr, True, False), -0.3)
        k['shin.L'] = leg_bend(fr, True, True); k['shin.R'] = leg_bend(fr, True, False); k['foot.L'] = foot_strike(fr, True, True); k['foot.R'] = foot_strike(fr, True, False); k['toe.L'] = toe_curl(fr, True, True); k['toe.R'] = toe_curl(fr, True, False)
        k['front_shoulder.L'] = leg_slow(fr + 12, False, True); k['front_shoulder.R'] = leg_slow(fr + 12, False, False); k['front_thigh.L'] = mul(leg_slow(fr + 12, False, True), 0.6); k['front_thigh.R'] = mul(leg_slow(fr + 12, False, False), 0.4)
        k['front_shin.L'] = leg_bend(fr + 12, False, True); k['front_shin.R'] = leg_bend(fr + 12, False, False); k['front_foot.L'] = foot_strike(fr + 12, False, True); k['front_foot.R'] = foot_strike(fr + 12, False, False)
        k['front_toe.L'] = toe_curl(fr + 12, False, True); k['front_toe.R'] = toe_curl(fr + 12, False, False)
        for i in range(1, 8): k[f'spine_{i}'] = (-sw(nrm(fr), CL, 0.03, (i / 7) * math.pi, -0.08), 0, 0)
        for i in range(1, 4): k[f'tail_{i}'] = tail_wag(fr)
        n = nrm(fr); sn = sw(n, CL, 0.03); lk = sw(n, CL, 0.05); tl = sw(n, CL, 0.016)
        k['scull'] = (sn + 0.0, lk, tl); k['jaw_top'] = (0.224, 0, 0); k['ear.L'] = ear_tw(fr); k['ear.R'] = ear_tw(fr + 6); k['sombrero'] = (0, 0, 0)
        return k
    smJ = RotationSmoother(12); smJ.previous_rotation = smJ._normalize(rzJ0d); rzpJ = rzJ0d; angJ = {}
    for t in range(S_J, E_J + 1):
        pf = t - S_J + 1; pos = pos_de(segJ, fpsJ, cumJ, min(pf, TOT_J), False); a = smJ.smooth_rotation(ang_de(segJ, cumJ, pf, False, True), t)
        rzd = desenrollar(rzpJ, a); rzpJ = rzd; angJ[t] = math.radians(rzd)
        EJ.location = (pos[0], pos[1], pos[2]); EJ.rotation_euler = (rxJ, ryJ, math.radians(rzd)); EJ.keyframe_insert("location", frame=t); EJ.keyframe_insert("rotation_euler", frame=t)
        w = ss((t - (S_J - 1)) / MEZ); P = pose_jerry(t - S_J + 1)
        for n in NB_J: poner(PBJ[n], t, P[n], BASE_J[n], w)
    fin_mezcla(PBJ, BASE_J, E_J + 8)
    FJ_FIN = E_J
    sc.frame_end = max(sc.frame_end, FA_FIN + 12, FJ_FIN + 12)
    # ================= sonidos: un paso en cada apoyo (pie en su punto mas adelantado) =================
    def apoyos(arm, root, huesos, f0, f1, ang):
        out = {h: [] for h in huesos}; ser = {h: [] for h in huesos}
        for t in range(f0, f1 + 1):
            sc.frame_set(t); a = ang[t]; fwd = Vector((-math.sin(a), math.cos(a), 0)); org = root.matrix_world.translation
            for h in huesos: p = arm.matrix_world @ arm.pose.bones[h].tail; ser[h].append(((p - org).dot(fwd)))
        for h in huesos:
            s = ser[h]; m = sum(s) / len(s)
            for i in range(1, len(s) - 1):
                if s[i] > s[i - 1] and s[i] >= s[i + 1] and s[i] > m: out[h].append(f0 + i)
        return out
    apA = apoyos(AA, EA, ["Rightknee_alfred", "Leftknee_alfred"], S_A + 2, E_A, angA); apJ = apoyos(JA, EJ, ["foot.L", "foot.R", "front_foot.L", "front_foot.R"], S_J + 8, E_J, angJ)
    S = "C:\\Users\\user\\Desktop\\Alfred_Animacion\\sonidos\\sounds\\"; libre = max([s_.channel for s_ in ed.strips_all] + [30]) + 1; nS = 0; pasosA = sorted(f for v in apA.values() for f in v); pasosJ = sorted((f, h) for h, v in apJ.items() for f in v)
    for j, f in enumerate(pasosA):
        arch = f"step/grass{(j * 5) % 6 + 1}.ogg"; s_ = ed.strips.new_sound(f"SND_jerry_p_camina_alfred_{j + 1}_{f}", os.path.normpath(S + arch.replace("/", "\\")), libre + (j % 3), f)
        s_.volume = 0.35; s_["vol_base"] = 0.35; s_["mcsnd"] = "pasos"; s_["mcsnd_ev"] = "camina_alfred"; s_["guion_id"] = f"snd6_jerry_p_camina_alfred_{j + 1}"; nS += 1
    for j, (f, h) in enumerate(pasosJ):
        arch = f"step/grass{(j * 5 + 3) % 6 + 1}.ogg"; s_ = ed.strips.new_sound(f"SND_jerry_p_camina_jerry_{j + 1}_{f}", os.path.normpath(S + arch.replace("/", "\\")), libre + 3 + (j % 4), f)
        s_.volume = 0.10; s_["vol_base"] = 0.10; s_["mcsnd"] = "pasos"; s_["mcsnd_ev"] = "camina_jerry"; s_["guion_id"] = f"snd6_jerry_p_camina_jerry_{j + 1}"; nS += 1
    res = {}
    for f in (S_A - 1, S_A + 30, S_A + 60, FA_FIN):
        sc.frame_set(f); pr = AA.matrix_world @ AA.pose.bones["Rightknee_alfred"].tail; pl = AA.matrix_world @ AA.pose.bones["Leftknee_alfred"].tail; res[f"A{f}"] = [round((pr.x + pl.x) / 2, 2), round((pr.y + pl.y) / 2, 2)]
    for f in (S_J - 1, S_J + 60, FJ_FIN): sc.frame_set(f); res[f"J{f}"] = [round(EJ.location.x, 2), round(EJ.location.y, 2)]
    sc.frame_set(120); print(res); print("pasos Alfred:", pasosA); print("pasos Jerry:", [f for f, h in pasosJ]); print("sonidos:", nS, "| frame_end:", sc.frame_end); print("LISTO")
except Exception:
    traceback.print_exc()
