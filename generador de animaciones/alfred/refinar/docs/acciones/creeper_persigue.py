# -*- coding: utf-8 -*-
"""Parte 6: terminado el INTENTO DE EXPLOSION 3 (f1215) el creeper SIGUE a Alfred y a Jerry como en el juego: camina tras ellos por su misma ruta de huida (norte (-93.0,-106.3) y luego oeste, rodeando el refugio por el norte) hasta quedarse a ~2.5 m del punto donde ellos paran ((-101.0,-106.3)), mirando al oeste.
Marcha = estudio del creeper (`creeper_camina_y_se_para.py`: 12.43 f/bloque, total multiplo de 12 f, ciclo 20 f, rumbo cardinal/diagonal suavizado 12 f) con mezcla de 6 f desde la pose en que acaba el intento. Pasos de pasto `SND_jerry_p_creeper_sigue_*`.
Se ejecuta DENTRO de Blender con exec DESPUES de `creeper_susto_y_huida.py` (que borra las claves del creeper desde f1119). Nunca `raise SystemExit`. Se puede repetir (borra sus claves y sonidos).
Variables opcionales: S (1216), X_FIN (-98.5)."""
import bpy, math, os, traceback
from mathutils import Vector

def canal_libre(ed, a, b):   # el VSE solo tiene 128 canales: busca uno sin tiras en [a, b] (new_sound desplaza la tira si el canal esta ocupado)
    for ch in range(1, 129):
        if not any(t.channel == ch and t.frame_final_start < b and a < t.frame_final_end for t in ed.strips_all): return ch
    raise RuntimeError('sin canal libre')

try:
    sc = bpy.context.scene
    ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
    S = int(globals().get("S", 1216)); X_FIN = float(globals().get("X_FIN", -98.5))
    CA = bpy.data.objects["creeper.arma_creeper_1"]; CR = bpy.data.objects["creeper_1"]; N = "_creeper_1"
    def fcs(o): return o.animation_data.action.layers[0].strips[0].channelbags[0].fcurves
    for o, sb in ((CA, True), (CR, False)):
        for fc in fcs(o):
            if sb and not fc.data_path.startswith("pose.bones"): continue
            for i in range(len(fc.keyframe_points) - 1, -1, -1):
                if fc.keyframe_points[i].co.x >= S: fc.keyframe_points.remove(fc.keyframe_points[i])
    sc.frame_set(S - 1); P0 = Vector(CR.location); rz0 = math.degrees(CR.rotation_euler.z); sx0 = Vector(CR.scale)
    pts = [(P0.x, P0.y, 14.0), (-93.0, -106.3, 14.0), (X_FIN, -106.3, 14.0)]; segs = [(pts[i], pts[i + 1]) for i in range(2)]
    FPU = 60.0 / 4.8284; HALF = 12; CICLO = 20.0; dist = sum(math.hypot(e[0] - s[0], e[1] - s[1]) for s, e in segs); n_half = max(1, round(dist * FPU / HALF)); TOT = n_half * HALF; WC = TOT / CICLO; E = S + TOT - 1
    def asignar(total):
        dists = [max(0.0001, math.sqrt(sum((e[i] - s[i]) ** 2 for i in range(3)))) for s, e in segs]; td = sum(dists) or 1.0
        bf = [max(1, int(round(total * (d / td)))) for d in dists]; diff = total - sum(bf); i = 0
        while diff != 0:
            if diff > 0: bf[i % len(bf)] += 1; diff -= 1
            elif bf[i % len(bf)] > 1: bf[i % len(bf)] -= 1; diff += 1
            i += 1
        cum = []; acc = 0
        for f in bf: acc += f; cum.append(acc)
        return bf, cum
    fps, cum = asignar(TOT)
    def pos_de(frame):
        prev = 0
        for j, cf in enumerate(cum):
            if frame <= cf:
                s, e = segs[j]; f = max(0.0, min(1.0, (frame - prev) / max(1, fps[j]))); return tuple(s[i] + (e[i] - s[i]) * f for i in range(3))
            prev = cf
        return tuple(segs[-1][1])
    def dir_angle(p0, p1):
        dx = p1[0] - p0[0]; dy = p1[1] - p0[1]
        if dx == 0 and dy == 0: return None
        ang_raw = math.degrees(math.atan2(dx, dy)); ang_rounded = round(ang_raw / 90.0) * 90.0
        ang = ang_rounded if abs(ang_raw - ang_rounded) < 45 else -ang_raw
        while ang > 180: ang -= 360
        while ang < -180: ang += 360
        if ang == 90: ang = -90
        elif ang == -90: ang = 90
        return ang
    def ang_de(frame):
        for j, cf in enumerate(cum):
            if frame <= cf:
                a = dir_angle(*segs[j]); return a if a is not None else 0.0
        a = dir_angle(*segs[-1]); return a if a is not None else 0.0
    class RotationSmoother:
        def __init__(self, n=12): self.n = n; self.prev = None; self.t0 = None; self.r0 = None; self.tg = None
        def norm(self, a):
            while a > 180: a -= 360
            while a < -180: a += 360
            return a
        def go(self, target, frame):
            target = self.norm(target)
            if self.prev is None: self.prev = target; return target
            d = self.norm(target - self.prev)
            if abs(d) < 5: self.prev = target; self.t0 = None; return target
            if self.t0 is None: self.t0 = frame; self.r0 = self.prev; self.tg = target
            p = min((frame - self.t0) / self.n, 1.0); e = p * p * (3 - 2 * p); sm = self.r0 + self.norm(self.tg - self.r0) * e
            if p >= 1.0: self.prev = target; self.t0 = None; return target
            return sm
    R = dict(arm_base_x=math.radians(90), arm_swing_y=math.radians(70), elbow_flex=math.radians(50), leg_swing_x=math.radians(50), spine_bend=math.radians(0.1), neck_tilt=math.radians(1.5), head_stab=0.25)
    ease_s = lambda t: -(math.cos(math.pi * t) - 1) / 2
    ease_c = lambda t: 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2
    def arm_swing(ph):
        m = R['arm_swing_y']; return ease_s(ph / 0.5) * m * 2 - m if ph < 0.5 else m - ease_s((ph - 0.5) / 0.5) * m * 2
    def elbow(ph):
        m = R['elbow_flex']
        if ph < 0.3: return ease_s(ph / 0.3) * m * 0.85 + m * 0.15
        if ph < 0.7: return m - ease_c((ph - 0.3) / 0.4) * m * 0.6
        return m * 0.4 - ease_s((ph - 0.7) / 0.3) * m * 0.25
    leg = lambda ph: R['leg_swing_x'] * math.sin(ph * 2 * math.pi)
    def pose(wc):
        sf = math.sin(wc * 2 * math.pi + math.pi / 6) * R['spine_bend']; st = math.cos(wc * 2 * math.pi + math.pi / 3) * R['spine_bend'] * 0.75
        nf = -sf * R['head_stab']; nt = math.sin(wc * 2 * math.pi) * R['neck_tilt']; ns = math.cos(wc * 2 * math.pi + math.pi / 4) * R['neck_tilt'] * 0.5
        ra = (wc + 0.25) % 1.0; la = (wc + 0.75) % 1.0
        return {"hip" + N: (0, 0, 0), "Bone.002" + N: (0, 0, 0), "body" + N: (sf, 0, st), "upperbody" + N: (sf, 0, st), "head.pos" + N: (0, 0, 0), "head" + N: (nf, ns, nt),
                "Bone.001" + N: (leg(wc), 0, 0), "Bone" + N: (leg((wc + 0.5) % 1.0), 0, 0),
                "foot.upper.002" + N: (R['arm_base_x'], arm_swing(ra), 0), "foot.lower.002" + N: (0, 0, -elbow(ra)), "foot.upper.003" + N: (R['arm_base_x'], -arm_swing(la), 0), "foot.lower.003" + N: (0, 0, elbow(la))}
    PB = {n: CA.pose.bones[n] for n in pose(0.0)}; BASE = {n: tuple(PB[n].rotation_euler) for n in PB}
    def key_pose(t, P, w):
        for n, v in P.items():
            PB[n].rotation_euler = tuple(BASE[n][c] + (v[c] - BASE[n][c]) * w for c in range(3))
            for ax in range(3): PB[n].keyframe_insert("rotation_euler", index=ax, frame=t, group=n)
    sm = RotationSmoother(12); sm.prev = sm.norm(rz0); rzp = rz0
    def unwrap(prev, x):
        while x - prev > 180: x -= 360
        while x - prev < -180: x += 360
        return x
    for t in range(S, E + 1):
        pf = t - S + 1; pos = pos_de(pf) if pf <= TOT else tuple(segs[-1][1]); a = sm.go(ang_de(pf), t); rzp = unwrap(rzp, a)
        CR.location = pos; CR.rotation_euler = (0, 0, math.radians(rzp)); CR.scale = sx0; CR.keyframe_insert("location", frame=t); CR.keyframe_insert("rotation_euler", frame=t); CR.keyframe_insert("scale", frame=t)
        key_pose(t, pose((t - S) / max(1, E - S) * WC), ss((t - (S - 1)) / 6.0))
    sc.frame_end = max(sc.frame_end, E + 20)
    ed = sc.sequence_editor; SND = "C:\\Users\\user\\Desktop\\Alfred_Animacion\\sonidos\\sounds\\"; libre = max([s_.channel for s_ in ed.strips_all] + [30]) + 1
    for s_ in [s_ for s_ in ed.strips_all if str(s_.get("guion_id", "")).startswith("snd6_jerry_p_creeper_sigue")]: ed.strips.remove(s_)
    pasos = []; k = 0
    while True:
        f = int(round(S + (0.25 + 0.5 * k) * (E - S) / WC))
        if f > E: break
        pasos.append(f); k += 1
    for j, f in enumerate(pasos):
        arch = f"step/grass{(j * 5 + 4) % 6 + 1}.ogg"; s_ = ed.strips.new_sound(f"SND_jerry_p_creeper_sigue_{j + 1}_{f}", os.path.normpath(SND + arch.replace("/", "\\")), canal_libre(ed, f, f + 20), f)
        s_.volume = 0.60; s_["vol_base"] = 0.60; s_["mcsnd"] = "pasos"; s_["mcsnd_ev"] = "creeper_sigue"; s_["guion_id"] = f"snd6_jerry_p_creeper_sigue_{j + 1}"
    res = {}
    for f in (S - 1, S, S + 30, S + 60, E, E + 10):
        sc.frame_set(f); res[f] = {"loc": [round(x, 2) for x in CR.location], "rz": round(math.degrees(CR.rotation_euler.z), 1)}
    sc.frame_set(120); print("sigue", round(dist, 2), "m ->", TOT, "frames (f", S, "-", E, ")"); print(res); print("pasos:", len(pasos), pasos[:4], "..."); print("LISTO")
except Exception:
    traceback.print_exc()
