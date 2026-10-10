# -*- coding: utf-8 -*-
"""Parte 6: a partir de f1035 el CREEPER camina el recorrido de `Desktop/creeper.json` (6 puntos, z 14.0) y se queda parado mirando al este (rz -90 = -450, la misma orientacion final que Alfred y Jerry).
Importa (append) el creeper de `estructura_lista/creeper_1.blend` (armature `creeper.arma_creeper_1`, root = empty `creeper_1`, 6 mallas + 2 ojos) si aun no esta en la escena; permanece oculto (hide_viewport/hide_render keyed) hasta f1035.
Marcha = `creeper_1_animation_studio/generate_slots_creeper_1.py::generate_caminar` (angulos Euler absolutos por frame): 12.43 f por bloque, total = multiplo de 12 f (medio ciclo), ciclo de 20 f; huesos `hip_creeper_1`/`Bone.002` a 0, `body`/`upperbody` (spine_bend), `head` (neck), patas delanteras `Bone`/`Bone.001` (swing X 50 grados, la derecha +0.5 ciclo), patas traseras `foot.upper.002/.003` + `foot.lower.002/.003` (formula de brazo/codo del estudio), rumbo cardinal/diagonal con RotationSmoother de 12 f.
Parada (como `parada_runtime`): al terminar la ruta la pose vuelve a neutral en 12 f y el root gira a -90 grados en esos 12 f. Pasos de pasto `SND_jerry_p_creeper_paso_*` en cada apoyo. Nunca `raise SystemExit`. Se puede repetir (borra claves y sonidos propios).
Variables opcionales: S (1035)."""
import bpy, json, math, os, traceback
from mathutils import Vector

def canal_libre(ed, a, b):   # el VSE solo tiene 128 canales: busca uno sin tiras en [a, b] (new_sound desplaza la tira si el canal esta ocupado)
    for ch in range(1, 129):
        if not any(t.channel == ch and t.frame_final_start < b and a < t.frame_final_end for t in ed.strips_all): return ch
    raise RuntimeError('sin canal libre')

try:
    sc = bpy.context.scene
    ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
    S = int(globals().get("S", 1035)); MEZ = 12
    BL = r"C:\Users\user\Desktop\Alfred_Animacion\estructura_lista\creeper_1.blend"
    if "creeper_1" not in bpy.data.objects:
        with bpy.data.libraries.load(BL, link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n != "mchar.eyeBoneK_creeper_1"]
        col = bpy.data.collections.new("creeper_1"); sc.collection.children.link(col)
        for o in dst.objects:
            if o is not None: col.objects.link(o)
        print("importados:", len([o for o in dst.objects if o is not None]), "objetos")
    ROOT = bpy.data.objects["creeper_1"]; ARM = bpy.data.objects["creeper.arma_creeper_1"]
    OBJS = [o for o in bpy.data.objects if o.name.endswith("_creeper_1") or o.name.startswith("creeper.")]
    pts = [(k["coordinates"]["x"], k["coordinates"]["y"], k["coordinates"]["z"]) for k in json.load(open(r"C:\Users\user\Desktop\creeper.json", encoding="utf-8"))["key_points"]]
    segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    for o in (ROOT, ARM):                                                                  # limpiar claves propias anteriores
        if o.animation_data and o.animation_data.action: bpy.data.actions.remove(o.animation_data.action)
        o.animation_data_create()
    ROOT.animation_data.action = bpy.data.actions.new("creeper_1_camina_y_se_para_root"); ARM.animation_data.action = bpy.data.actions.new("creeper_1_camina_y_se_para_arm")
    for pb in ARM.pose.bones: pb.rotation_mode = 'XYZ'
    # ---------- ruta y tiempos (del estudio) ----------
    FPU = 60.0 / 4.8284; HALF = 12; CICLO = 20.0
    dist = sum(math.hypot(e[0] - s[0], e[1] - s[1]) for s, e in segs); n_half = max(1, round(dist * FPU / HALF)); TOT = n_half * HALF; WC = TOT / CICLO; E = S + TOT - 1
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
                a = dir_angle(*segs[j]); return a if a is not None else -90.0
        a = dir_angle(*segs[-1]); return a if a is not None else -90.0
    class RotationSmoother:
        def __init__(self, n=12): self.n = n; self.prev = None; self.t0 = None; self.r0 = None; self.tg = None
        def norm(self, a):
            while a > 180: a -= 360
            while a < -180: a += 360
            return a
        def diff(self, t, c): return self.norm(t - c)
        def go(self, target, frame):
            target = self.norm(target)
            if self.prev is None: self.prev = target; return target
            d = self.diff(target, self.prev)
            if abs(d) < 5: self.prev = target; self.t0 = None; return target
            if self.t0 is None: self.t0 = frame; self.r0 = self.prev; self.tg = target
            p = min((frame - self.t0) / self.n, 1.0); e = p * p * (3 - 2 * p); sm = self.r0 + self.diff(self.tg, self.r0) * e
            if p >= 1.0: self.prev = target; self.t0 = None; return target
            return sm
    # ---------- biomecanica (estudio) ----------
    R = dict(arm_base_x=math.radians(90), arm_swing_y=math.radians(70), elbow_flex=math.radians(50), leg_swing_x=math.radians(50), spine_bend=math.radians(0.1), neck_tilt=math.radians(1.5), head_stab=0.25)
    ease_s = lambda t: -(math.cos(math.pi * t) - 1) / 2
    ease_c = lambda t: 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2
    def arm_swing(ph):
        m = R['arm_swing_y']
        return ease_s(ph / 0.5) * m * 2 - m if ph < 0.5 else m - ease_s((ph - 0.5) / 0.5) * m * 2
    def elbow(ph):
        m = R['elbow_flex']
        if ph < 0.3: return ease_s(ph / 0.3) * m * 0.85 + m * 0.15
        if ph < 0.7: return m - ease_c((ph - 0.3) / 0.4) * m * 0.6
        return m * 0.4 - ease_s((ph - 0.7) / 0.3) * m * 0.25
    leg = lambda ph: R['leg_swing_x'] * math.sin(ph * 2 * math.pi)
    N = "_creeper_1"
    def pose(wc):
        sf = math.sin(wc * 2 * math.pi + math.pi / 6) * R['spine_bend']; st = math.cos(wc * 2 * math.pi + math.pi / 3) * R['spine_bend'] * 0.75
        nf = -sf * R['head_stab']; nt = math.sin(wc * 2 * math.pi) * R['neck_tilt']; ns = math.cos(wc * 2 * math.pi + math.pi / 4) * R['neck_tilt'] * 0.5
        ra = (wc + 0.25) % 1.0; la = (wc + 0.75) % 1.0
        return {"hip" + N: (0, 0, 0), "Bone.002" + N: (0, 0, 0), "body" + N: (sf, 0, st), "upperbody" + N: (sf, 0, st), "head.pos" + N: (0, 0, 0), "head" + N: (nf, ns, nt),
                "Bone.001" + N: (leg(wc), 0, 0), "Bone" + N: (leg((wc + 0.5) % 1.0), 0, 0),
                "foot.upper.002" + N: (R['arm_base_x'], arm_swing(ra), 0), "foot.lower.002" + N: (0, 0, -elbow(ra)),
                "foot.upper.003" + N: (R['arm_base_x'], -arm_swing(la), 0), "foot.lower.003" + N: (0, 0, elbow(la))}
    PB = {n: ARM.pose.bones[n] for n in pose(0.0)}
    def key_pose(t, P):
        for n, v in P.items():
            PB[n].rotation_euler = v
            for ax in range(3): PB[n].keyframe_insert("rotation_euler", index=ax, frame=t, group=n)
    sm = RotationSmoother(12); rzp = None; ang_f = {}
    def unwrap(prev, x):
        if prev is None: return x
        while x - prev > 180: x -= 360
        while x - prev < -180: x += 360
        return x
    ROOT.rotation_mode = 'XYZ'
    for t in range(S, E + 1):
        pf = t - S + 1; pos = pos_de(pf) if pf <= TOT else tuple(segs[-1][1]); a = sm.go(ang_de(pf), t); rzp = unwrap(rzp, a); ang_f[t] = math.radians(rzp)
        ROOT.location = pos; ROOT.rotation_euler = (0, 0, math.radians(rzp)); ROOT.keyframe_insert("location", frame=t); ROOT.keyframe_insert("rotation_euler", frame=t)
        key_pose(t, pose((t - S) / max(1, E - S) * WC))
    # ---------- parada: pose neutral + giro a -90 (= -450, como Alfred y Jerry) ----------
    P_end = pose((E - S) / max(1, E - S) * WC); rz_fin = rzp; objetivo = -90.0
    objetivo = rz_fin + ((objetivo - rz_fin + 180) % 360 - 180)
    for k in range(1, MEZ + 1):
        t = E + k; w = ss(k / MEZ); key_pose(t, {n: tuple(v[c] * (1 - w) for c in range(3)) for n, v in P_end.items()})
        ROOT.location = tuple(segs[-1][1]); ROOT.rotation_euler = (0, 0, math.radians(rz_fin + (objetivo - rz_fin) * w)); ROOT.keyframe_insert("location", frame=t); ROOT.keyframe_insert("rotation_euler", frame=t)
    # ---------- visibilidad: oculto hasta f(S) ----------
    for o in OBJS:
        o.hide_viewport = True; o.hide_render = True; o.keyframe_insert("hide_viewport", frame=1); o.keyframe_insert("hide_render", frame=1)
        o.hide_viewport = False; o.hide_render = False; o.keyframe_insert("hide_viewport", frame=S); o.keyframe_insert("hide_render", frame=S)
        if o.animation_data and o.animation_data.action:
            for fc in o.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
                if fc.data_path.startswith("hide"):
                    for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
    for o in (ROOT, ARM):
        for fc in o.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
            if fc.data_path.startswith("hide"):
                for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
    for o in OBJS:                                                                          # la cabeza (`creeper.head.sadb_creeper_1`) tiene DRIVERS en hide_viewport/hide_render (cambio de forma de cara, `var!=1`) que ignoran las claves de arriba: se les anade `or frame<S`
        if o.animation_data:
            for d in o.animation_data.drivers:
                if d.data_path in ("hide_viewport", "hide_render") and "frame<" not in d.driver.expression.replace(" ", ""): d.driver.expression = f"({d.driver.expression}) or frame<{S}"
    sc.frame_end = max(sc.frame_end, E + MEZ + 12)
    # ---------- sonidos: pasos de pasto en cada apoyo (pierna en su punto mas adelantado: fase 0.25 + 0.5 k) ----------
    ed = sc.sequence_editor; SND = "C:\\Users\\user\\Desktop\\Alfred_Animacion\\sonidos\\sounds\\"; libre = max([s_.channel for s_ in ed.strips_all] + [30]) + 1
    for s_ in [s_ for s_ in ed.strips_all if str(s_.get("guion_id", "")).startswith("snd6_jerry_p_creeper_paso")]: ed.strips.remove(s_)
    pasos = []; k = 0
    while True:
        f = int(round(S + (0.25 + 0.5 * k) * (E - S) / WC))
        if f > E: break
        pasos.append(f); k += 1
    for j, f in enumerate(pasos):
        arch = f"step/grass{(j * 5 + 2) % 6 + 1}.ogg"; s_ = ed.strips.new_sound(f"SND_jerry_p_creeper_paso_{j + 1}_{f}", os.path.normpath(SND + arch.replace("/", "\\")), canal_libre(ed, f, f + 20), f)
        s_.volume = 0.50; s_["vol_base"] = 0.50; s_["mcsnd"] = "pasos"; s_["mcsnd_ev"] = "creeper_camina"; s_["guion_id"] = f"snd6_jerry_p_creeper_paso_{j + 1}"
    res = {}
    for f in (S - 1, S, S + 20, S + 40, E, E + MEZ, E + MEZ + 5):
        sc.frame_set(f); res[f] = {"loc": [round(x, 2) for x in ROOT.location], "rz": round(math.degrees(ROOT.rotation_euler.z), 1), "oculto": ARM.hide_viewport}
    sc.frame_set(120); print("ruta", round(dist, 2), "m ->", TOT, "frames (f", S, "-", E, ") ciclos", WC); print(res); print("pasos:", pasos); print("LISTO")
except Exception:
    traceback.print_exc()
