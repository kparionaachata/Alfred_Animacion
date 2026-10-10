# -*- coding: utf-8 -*-
"""Parte 6, f1120+: encuentro Alfred - Creeper - Jerry.
 f1120-1131  Alfred gira la cabeza a la DERECHA (Neck Y -75, hacia el creeper) 3 f, la mantiene 5 f y vuelve al frente 3 f.
 f1131-1142  el creeper gira la cabeza a su IZQUIERDA (head Y +75, hacia Alfred) 3 f, 5 f y vuelve al frente 3 f.
 f1152-1162  tras 10 f el creeper gira (smoothstep, 10 f) y Alfred gira sobre sus pies en GIRO_A=2 f (f1160-1162, terminando a la vez); quedan frente a frente.
 f1162-1190  SUSTO exagerado de Alfred (Elastic In-Out, brazos en V arriba y afuera, piernas abiertas y rodillas dobladas, cadera baja, tronco hacia atras, salto al inicio, temblor) mientras el creeper hace el INTENTO DE EXPLOSION 3 (7 destellos, 54 f, f1162-1215: carga organica del estudio `explosion_runtime.py`, sin detonar; destellos con la funcion del estudio + `random/fuse.ogg`).
 f1190+      Alfred sale CORRIENDO del susto con Jerry (que arranca 2 f despues) hacia su derecha (oeste, rodeando el refugio por el norte): ciclos CORRER de los estudios (Alfred 6.2 f/bloque, ciclo 11 f; Jerry mismo ritmo, ciclo 12 f).
Se ejecuta DENTRO de Blender con exec (despues de la marcha, el final de recorrido y el creeper). Nunca `raise SystemExit`. Se puede repetir (borra sus claves y sonidos `snd6_jerry_p_huida_*`).
Variables opcionales: T0 (1120), T_SUSTO (1162), T_CORRE (1190)."""
import bpy, json, math, os, traceback
from mathutils import Vector, Matrix, Euler

def canal_libre(ed, a, b):   # el VSE solo tiene 128 canales: busca uno sin tiras en [a, b] (new_sound desplaza la tira si el canal esta ocupado)
    for ch in range(1, 129):
        if not any(t.channel == ch and t.frame_final_start < b and a < t.frame_final_end for t in ed.strips_all): return ch
    raise RuntimeError('sin canal libre')

try:
    sc = bpy.context.scene
    ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
    def ela(t):
        if t <= 0: return 0.0
        if t >= 1: return 1.0
        c5 = (2 * math.pi) / 4.5
        return -(2 ** (20 * t - 10) * math.sin((20 * t - 11.125) * c5)) / 2 if t < 0.5 else (2 ** (-20 * t + 10) * math.sin((20 * t - 11.125) * c5)) / 2 + 1
    T0 = int(globals().get("T0", 1120)); T_SUSTO = int(globals().get("T_SUSTO", 1162)); T_CORRE = int(globals().get("T_CORRE", 1190)); T_GIRO = T0 + 32; FLASH = 7; GIRO_A = int(globals().get("GIRO_A", 2)); D2R = math.pi / 180
    AA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "Hips_alfred" in o.pose.bones); EA = AA.parent
    JA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "scull_1" in o.pose.bones); EJ = bpy.data.objects["jerry"]
    CA = bpy.data.objects["creeper.arma_creeper_1"]; CR = bpy.data.objects["creeper_1"]
    cerca = lambda b, t: b + 2 * math.pi * round((t - b) / (2 * math.pi))
    def desenrollar(prev, x):
        while x - prev > 180: x -= 360
        while x - prev < -180: x += 360
        return x
    def fcs(o): return o.animation_data.action.layers[0].strips[0].channelbags[0].fcurves
    def borrar(o, desde, solo_huesos=False):
        for fc in fcs(o):
            if solo_huesos and not fc.data_path.startswith("pose.bones"): continue
            for i in range(len(fc.keyframe_points) - 1, -1, -1):
                if fc.keyframe_points[i].co.x >= desde: fc.keyframe_points.remove(fc.keyframe_points[i])
    for o, sb in ((AA, True), (EA, False), (JA, True), (EJ, False), (CA, True), (CR, False)): borrar(o, T0 - 1, sb)
    ed = sc.sequence_editor
    for s_ in [s_ for s_ in ed.strips_all if str(s_.get("guion_id", "")).startswith(("snd6_jerry_p_huida_", "snd6_jerry_p_creeper_fuse"))]: ed.strips.remove(s_)
    SND = "C:\\Users\\user\\Desktop\\Alfred_Animacion\\sonidos\\sounds\\"; libre = max([s_.channel for s_ in ed.strips_all] + [30]) + 1
    def sonido(nombre, arch, f, vol, ch, ev):
        s_ = ed.strips.new_sound(f"SND_jerry_p_{nombre}_{f}", os.path.normpath(SND + arch.replace("/", "\\")), ch, f); s_.volume = vol; s_["vol_base"] = vol; s_["mcsnd"] = "pasos" if "paso" in nombre else "objetos"; s_["mcsnd_ev"] = ev; s_["guion_id"] = "snd6_jerry_p_" + nombre.split("_%d" % f)[0]
        return s_
    # ---------- estados iniciales ----------
    sc.frame_set(T0 - 1)
    NB_A = ["Hips_alfred", "Spine_alfred", "Spine1_alfred", "Spine2_alfred", "Neck_alfred", "RightUpArm_alfred", "Rightelbow_alfred", "LeftUpArm_alfred", "Leftelbow_alfred", "RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred"]
    PBA = {n: AA.pose.bones[n] for n in NB_A}; B0 = {n: tuple(PBA[n].rotation_euler) for n in NB_A}; H_LOC0 = Vector(PBA["Hips_alfred"].location)
    pr = AA.matrix_world @ AA.pose.bones["Rightknee_alfred"].tail; pl = AA.matrix_world @ AA.pose.bones["Leftknee_alfred"].tail; PIV = Vector(((pr.x + pl.x) / 2, (pr.y + pl.y) / 2, 0))
    EA0 = Vector(EA.location); rzA0 = EA.rotation_euler.z; EJ0 = Vector(EJ.location); CR0 = Vector(CR.location); rzC0 = CR.rotation_euler.z
    NECK = PBA["Neck_alfred"]; HEADC = CA.pose.bones["head_creeper_1"]; HC0 = tuple(HEADC.rotation_euler)
    def key_rot(pb, f, v, grupo=None):
        pb.rotation_euler = v
        for ax in range(3): pb.keyframe_insert("rotation_euler", index=ax, frame=f, group=grupo or pb.name)
    # ---------- 1) cabezas ----------
    YA = -75 * D2R; YC = 75 * D2R
    def mirada(t, a, b, c, d):                                                              # 0 -> 1 en [a,b], 1 hasta c, 1 -> 0 en [c,d]
        return ss((t - a) / (b - a)) * (1 - ss((t - c) / (d - c)))
    for f in range(T0 - 1, T0 + 13):
        w = mirada(f, T0, T0 + 3, T0 + 8, T0 + 11); e = list(B0["Neck_alfred"]); e[1] = B0["Neck_alfred"][1] + (YA - B0["Neck_alfred"][1]) * w; key_rot(NECK, f, tuple(e))
    TC = T0 + 11
    for f in range(TC - 1, TC + 13):
        w = mirada(f, TC, TC + 3, TC + 8, TC + 11); e = list(HC0); e[1] = HC0[1] + (YC - HC0[1]) * w; key_rot(HEADC, f, tuple(e))
    # ---------- 2) giro simultaneo y frente a frente ----------
    bear_a = math.degrees(math.atan2(CR0.x - PIV.x, CR0.y - PIV.y)); rz_a_t = -bear_a; rz_a_t += 360 * round((math.degrees(rzA0) - 180 * 0 - rz_a_t - 0) / 360.0)
    rz_a_t = math.degrees(rzA0) + (((rz_a_t - math.degrees(rzA0)) + 180) % 360 - 180)
    if rz_a_t > math.degrees(rzA0): rz_a_t -= 360                                           # Alfred gira a la DERECHA (rz decreciente)
    bear_c = math.degrees(math.atan2(PIV.x - CR0.x, PIV.y - CR0.y)); rz_c_t = math.degrees(rzC0) + (((-bear_c - math.degrees(rzC0)) + 180) % 360 - 180)
    if rz_c_t < math.degrees(rzC0): rz_c_t += 360                                           # el creeper gira a la IZQUIERDA (rz creciente)
    print("giro Alfred", round(math.degrees(rzA0), 1), "->", round(rz_a_t, 1), "| creeper", round(math.degrees(rzC0), 1), "->", round(rz_c_t, 1))
    TG0 = T0 + 32; TG1 = TG0 + 10
    for f in list(range(T0 - 1, TG1 + 1)):
        w = ss((f - (TG1 - GIRO_A)) / float(GIRO_A)); rz = math.radians(math.degrees(rzA0) + (rz_a_t - math.degrees(rzA0)) * w)           # Alfred gira en GIRO_A (2) frames, terminando en TG1
        v = EA0 - Vector((PIV.x, PIV.y, EA0.z)); EA.location = Vector((PIV.x, PIV.y, EA0.z)) + Matrix.Rotation(rz - rzA0, 3, 'Z') @ v; EA.rotation_euler = (EA.rotation_euler.x, EA.rotation_euler.y, rz)
        EA.keyframe_insert("location", frame=f); EA.keyframe_insert("rotation_euler", frame=f)
        CR.location = CR0; CR.rotation_euler = (0, 0, math.radians(math.degrees(rzC0) + (rz_c_t - math.degrees(rzC0)) * ss((f - TG0) / 10.0))); CR.keyframe_insert("location", frame=f); CR.keyframe_insert("rotation_euler", frame=f)
    rzA1 = math.radians(rz_a_t); EAg = Vector(EA.location)
    # ---------- 3) SUSTO de Alfred (Elastic In-Out) ----------
    TS = T_SUSTO
    sc.frame_set(TS - 1)
    BS = {n: tuple(PBA[n].rotation_euler) for n in NB_A}
    V = {"RightUpArm_alfred": (-62 * D2R, 12 * D2R, 0.0), "LeftUpArm_alfred": (-62 * D2R, -12 * D2R, 0.0), "Rightelbow_alfred": (0.0, 0.0, -12 * D2R), "Leftelbow_alfred": (0.0, 0.0, 12 * D2R),
         "RightUpLeg_alfred": (BS["RightUpLeg_alfred"][0], BS["RightUpLeg_alfred"][1], -30 * D2R), "LeftUpLeg_alfred": (BS["LeftUpLeg_alfred"][0], BS["LeftUpLeg_alfred"][1], 30 * D2R),
         "Rightknee_alfred": (-25 * D2R, 0.0, 0.0), "Leftknee_alfred": (-25 * D2R, 0.0, 0.0), "Hips_alfred": (-8 * D2R, BS["Hips_alfred"][1], BS["Hips_alfred"][2]),
         "Spine1_alfred": (-12 * D2R, BS["Spine1_alfred"][1], BS["Spine1_alfred"][2]), "Neck_alfred": (10 * D2R, BS["Neck_alfred"][1], BS["Neck_alfred"][2])}
    for f in range(TS - 1, T_CORRE):
        k = (f - TS) / 9.0; w = ela(k); tr = ss((f - TS - 9) / 4.0) * 1.0
        for n in NB_A:
            if n in V:
                tg = [cerca(V[n][c], BS[n][c]) for c in range(3)]; val = [BS[n][c] + (tg[c] - BS[n][c]) * w for c in range(3)]
                if "UpArm" in n or "elbow" in n: val[0] += (1 if n.startswith("Right") else -1) * 0.0 + 3.0 * D2R * tr * math.sin(f * 2.3) * (1 if "UpArm" in n else 0)
                if "UpArm" in n: val[1] += 2.0 * D2R * tr * math.sin(f * 1.7 + (0 if n.startswith("Right") else 1.5))
            else: val = list(BS[n])
            key_rot(PBA[n], f, tuple(val))
        PBA["Hips_alfred"].location = H_LOC0 + Vector((0, -0.12 * w, 0)); [PBA["Hips_alfred"].keyframe_insert("location", index=ax, frame=f, group="Hips_alfred") for ax in range(3)]
        u = (f - TS) / 8.0; hop = 0.22 * math.sin(math.pi * u) if 0 <= u <= 1 else 0.0
        if f >= TS: EA.location = Vector((EAg.x, EAg.y, EAg.z + hop)); EA.rotation_euler = (EA.rotation_euler.x, EA.rotation_euler.y, rzA1); EA.keyframe_insert("location", frame=f); EA.keyframe_insert("rotation_euler", frame=f)
    BSC = {n: tuple(PBA[n].rotation_euler) for n in NB_A}                                  # pose del susto en T_CORRE-1
    # ---------- 4) INTENTO DE EXPLOSION 3 del creeper (estudio: carga organica + destellos) ----------
    IM = TS; CH_END = IM + FLASH * 6; ATT_END = CH_END + 11
    NAMES = [("body_creeper_1", .055, 0), ("upperbody_creeper_1", .085, .6), ("head_creeper_1", .13, 1.1), ("hip_creeper_1", .045, 2)]
    base_ro = {n: tuple(CA.pose.bones[n].rotation_euler) for n, a, p in NAMES}; base_sc = {n: tuple(CA.pose.bones[n].scale) for n, a, p in NAMES}; base_loc = {n: tuple(CA.pose.bones[n].location) for n, a, p in NAMES}
    sc.frame_set(IM - 1)
    base_ro = {n: tuple(CA.pose.bones[n].rotation_euler) for n, a, p in NAMES}
    IKS = [CA.pose.bones.get("foot.IK" + s + "_creeper_1") for s in ("", ".001", ".002", ".003")]; ik0 = [tuple(b.location) for b in IKS if b]
    cb = Vector(CR.scale);
    def key_att(f, amp_charge, t, restore):                                                  # restore: 0..1 hacia la pose base (suavizado)
        envelope = math.sin(t * math.pi / 2) ** 2; wave = math.sin(2 * math.pi * (2 * t + 3 * t * t)) * envelope; crouch = math.sin(math.pi * min(1, t / .8)) * .035
        for n, amount, phase in NAMES:
            b = CA.pose.bones[n]; r0 = base_ro[n]
            off = (amount * wave, amount * .45 * math.sin(t * 23 + phase) * envelope, amount * .35 * math.sin(t * 31 + phase) * envelope)
            b.rotation_euler = tuple(r0[c] + off[c] * amp_charge for c in range(3)); b.scale = (1 + .06 * envelope * amp_charge, 1 - .035 * envelope * amp_charge, 1 + .025 * wave * amp_charge)
            for ch in ("rotation_euler", "scale"): b.keyframe_insert(ch, frame=f, group=n)
            if n == "body_creeper_1": b.location = (0, 0, -crouch * amp_charge); b.keyframe_insert("location", frame=f, group=n)
        for i, b in enumerate(IKS):
            if b: b.location = (.015 * wave * (-1 if i % 2 else 1) * amp_charge, 0, .008 * max(0, math.sin(t * 27 + i * math.pi / 2)) * envelope * amp_charge); b.keyframe_insert("location", frame=f, group=b.name)
    for n, a, p in NAMES:                                                                   # ancla en IM-1 (estado base)
        b = CA.pose.bones[n]; b.rotation_euler = base_ro[n]; b.scale = (1, 1, 1); b.location = (0, 0, 0) if n == "body_creeper_1" else b.location
        for ch in ("rotation_euler", "scale"): b.keyframe_insert(ch, frame=IM - 1, group=n)
        if n == "body_creeper_1": b.keyframe_insert("location", frame=IM - 1, group=n)
    for b in IKS:
        if b: b.location = (0, 0, 0); b.keyframe_insert("location", frame=IM - 1, group=b.name)
    for f in range(IM, CH_END):
        t = (f - IM) / max(1, CH_END - IM - 1); key_att(f, 1.0, t, 0.0)
        a = .16 * t * t; CR.location = CR0; CR.rotation_euler = (0, 0, math.radians(rz_c_t)); CR.scale = tuple(v * (1 + a * (1 if i < 2 else .5)) for i, v in enumerate(cb))
        for ch in ("location", "rotation_euler", "scale"): CR.keyframe_insert(ch, frame=f)
    for f in range(CH_END, ATT_END + 1):
        tt = (f - CH_END + 1) / 12.0; sm = ss(tt); key_att(f, 1.0 - sm, 1.0, sm)
        a = .16 * (1 - sm); CR.location = CR0; CR.rotation_euler = (0, 0, math.radians(rz_c_t)); CR.scale = tuple(v * (1 + a * (1 if i < 2 else .5)) for i, v in enumerate(cb))
        for ch in ("location", "rotation_euler", "scale"): CR.keyframe_insert(ch, frame=f)
    src = open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\creeper_1\refinar\creeper_1_animation_studio\explosion_runtime.py", encoding="utf-8").read(); gx = {"__name__": "x"}; exec(src, gx)
    meshes = [o for o in CR.children_recursive if o.type == 'MESH']; gx["_flash_materials"](meshes, IM, CH_END, flash_count=FLASH)
    for fc in fcs(CA):
        if fc.data_path.startswith("pose.bones") and any(IM <= k.co.x <= ATT_END for k in fc.keyframe_points):
            for k in fc.keyframe_points:
                if k.co.x >= IM - 1: k.interpolation = 'LINEAR'
    s_ = sonido("creeper_fuse", "random/fuse.ogg", IM, 0.7, canal_libre(ed, IM, IM + 40), "creeper_mecha"); s_["guion_id"] = "snd6_jerry_p_creeper_fuse"
    # ---------- 5) HUIDA: Alfred y Jerry corren hacia la derecha (oeste, por el norte del refugio) ----------
    sc.frame_set(T_CORRE - 1)
    pr = AA.matrix_world @ AA.pose.bones["Rightknee_alfred"].tail; pl = AA.matrix_world @ AA.pose.bones["Leftknee_alfred"].tail; P_ini = Vector(((pr.x + pl.x) / 2, (pr.y + pl.y) / 2, 0)); locA = Vector(EA.location); rzA = EA.rotation_euler.z; d0 = Vector((locA.x - P_ini.x, locA.y - P_ini.y, 0)); locA_z = locA.z - (0.0)
    ptsA = [(P_ini.x, P_ini.y, 14.0), (-93.0, -106.3, 14.0), (-101.0, -106.3, 14.0)]; segA = [(ptsA[i], ptsA[i + 1]) for i in range(2)]
    ST = dict(speed=0.5, cycle=0.55, arm_swing=1.6, elbow=1.7, leg=1.7, knee=1.8, spine=1.8, neck_tilt=0.6, arm_base=0.85, lean=0.12, bob=0.06)
    FPU = (60.0 / 4.8284) * ST["speed"]; CICLO = 20.0 * ST["cycle"]; HALF = CICLO / 2.0; dist = sum(math.hypot(e[0] - s[0], e[1] - s[1]) for s, e in segA)
    n_half = max(1, round(dist * FPU / HALF)); TOT_A = max(1, round(n_half * HALF)); WC = TOT_A / CICLO; E_A = T_CORRE + TOT_A - 1
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
    def pos_de(segs, fps, cum, frame, estricto):
        prev = 0
        for j, cf in enumerate(cum):
            if (frame < cf) if estricto else (frame <= cf):
                s, e = segs[j]; f = max(0.0, min(1.0, (frame - prev) / max(1, fps[j]))); return tuple(s[i] + (e[i] - s[i]) * f for i in range(3))
            prev = cf
        return tuple(segs[-1][1])
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
    def ang_de(segs, cum, frame, estricto, jerry):
        for j, cf in enumerate(cum):
            if (frame < cf) if estricto else (frame <= cf):
                a = dir_angle(segs[j][0], segs[j][1], jerry); return a if a is not None else 0.0
        a = dir_angle(segs[-1][0], segs[-1][1], jerry); return a if a is not None else 0.0
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
    fpsA, cumA = asignar(segA, TOT_A)
    R = dict(arm_base_x=math.radians(90 * ST["arm_base"]), arm_swing_y=math.radians(70 * ST["arm_swing"]), elbow_flex=math.radians(50 * ST["elbow"]), leg_swing_x=math.radians(50 * ST["leg"]), knee_flex=math.radians(40 * ST["knee"]),
             hip_forward=math.radians(3), hip_sway=math.radians(4), hip_tilt=math.radians(4), spine_bend=math.radians(0.1 * ST["spine"]), neck_tilt=math.radians(1.5 * ST["neck_tilt"]), head_stab=0.25)
    ease_s = lambda t: -(math.cos(math.pi * t) - 1) / 2
    ease_c = lambda t: 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2
    def leg_swing(ph): return R['leg_swing_x'] * math.sin(ph * 2 * math.pi)
    def arm_swing(ph):
        m = R['arm_swing_y']; return ease_s(ph / 0.5) * m * 2 - m if ph < 0.5 else m - ease_s((ph - 0.5) / 0.5) * m * 2
    def elbow(ph):
        m = R['elbow_flex']
        if ph < 0.3: return ease_s(ph / 0.3) * m * 0.85 + m * 0.15
        if ph < 0.7: return m - ease_c((ph - 0.3) / 0.4) * m * 0.6
        return m * 0.4 - ease_s((ph - 0.7) / 0.3) * m * 0.25
    def knee(ph): return R['knee_flex'] * max(0.0, math.sin((ph - 0.75) * 2 * math.pi))
    def pose_alfred(wc):
        sf = math.sin(wc * 2 * math.pi + math.pi / 6) * R['spine_bend'] + ST["lean"]; st = math.cos(wc * 2 * math.pi + math.pi / 3) * R['spine_bend'] * 0.75
        hf = -sf * 0.3 + R['hip_forward'] * math.sin(wc * 2 * math.pi); hs = math.sin(wc * 2 * math.pi + math.pi / 4) * R['hip_sway']; ht = math.sin(wc * 2 * math.pi) * R['hip_tilt']
        nf = -sf * R['head_stab']; nt = math.sin(wc * 2 * math.pi) * R['neck_tilt']; ns = math.cos(wc * 2 * math.pi + math.pi / 4) * R['neck_tilt'] * 0.5
        rc = (wc + 0.5) % 1.0; ra = (wc + 0.25) % 1.0; la = (wc + 0.75) % 1.0
        return {"Hips_alfred": (hf, hs, ht), "Spine_alfred": (sf, 0, st), "Spine1_alfred": (sf, 0, st), "Spine2_alfred": (sf, 0, st), "Neck_alfred": (nf, ns, nt),
                "LeftUpLeg_alfred": (leg_swing(wc), 0, 0), "Leftknee_alfred": (-knee(wc), 0, 0), "RightUpLeg_alfred": (leg_swing(rc), 0, 0), "Rightknee_alfred": (-knee(rc), 0, 0),
                "RightUpArm_alfred": (R['arm_base_x'], arm_swing(ra), 0), "Rightelbow_alfred": (0, 0, -elbow(ra)), "LeftUpArm_alfred": (R['arm_base_x'], -arm_swing(la), 0), "Leftelbow_alfred": (0, 0, elbow(la))}
    def poner(pb, t, tgt, base, w):
        e = [cerca(base[c], tgt[c]) for c in range(3)]; key_rot(pb, t, Euler(tuple(e[c] + (tgt[c] - e[c]) * w for c in range(3)), 'XYZ'))
    smA = RotationSmoother(12); smA.prev = smA.norm(math.degrees(rzA)); rzp = math.degrees(rzA); angA = {}
    for t in range(T_CORRE, E_A + 1):
        pf = t - T_CORRE; pos = pos_de(segA, fpsA, cumA, pf, True) if pf < TOT_A else tuple(segA[-1][1]); a = smA.go(ang_de(segA, cumA, pf, True, False), t); rzd = desenrollar(rzp, a); rzp = rzd; rz = math.radians(rzd); angA[t] = rz
        wc = (t - T_CORRE) / max(1, E_A - T_CORRE) * WC; bob = ST["bob"] * (0.5 - 0.5 * math.cos(wc * 4 * math.pi))
        EA.location = Vector((pos[0], pos[1], 0)) + (Matrix.Rotation(rz - rzA, 3, 'Z') @ d0) + Vector((0, 0, locA.z + bob)); EA.rotation_euler = (EA.rotation_euler.x, EA.rotation_euler.y, rz)
        EA.keyframe_insert("location", frame=t); EA.keyframe_insert("rotation_euler", frame=t)
        w = ss((t - (T_CORRE - 1)) / 6.0); Pp = pose_alfred(wc)
        for n in NB_A: poner(PBA[n], t, Pp[n], BSC[n], w)
        hl = H_LOC0 + Vector((0, -0.12 * (1 - w), 0)); PBA["Hips_alfred"].location = hl; [PBA["Hips_alfred"].keyframe_insert("location", index=ax, frame=t, group="Hips_alfred") for ax in range(3)]
    # ----- Jerry -----
    sc.frame_set(T_CORRE + 1); J_ini = (EJ.location.x, EJ.location.y, EJ.location.z); rxJ, ryJ = EJ.rotation_euler.x, EJ.rotation_euler.y; rzJ0d = math.degrees(EJ.rotation_euler.z)
    NB_J = ['shoulder.L', 'shoulder.R', 'thigh.L', 'thigh.R', 'shin.L', 'shin.R', 'foot.L', 'foot.R', 'toe.L', 'toe.R', 'front_shoulder.L', 'front_shoulder.R', 'front_thigh.L', 'front_thigh.R', 'front_shin.L', 'front_shin.R', 'front_foot.L', 'front_foot.R', 'front_toe.L', 'front_toe.R',
            'spine_1', 'spine_2', 'spine_3', 'spine_4', 'spine_5', 'spine_6', 'spine_7', 'tail_1', 'tail_2', 'tail_3', 'scull', 'jaw_top', 'ear.L', 'ear.R', 'sombrero']
    PBJ = {n: JA.pose.bones[n] for n in NB_J}; BASE_J = {n: tuple(PBJ[n].rotation_euler) for n in NB_J}
    S_J = T_CORRE + 2; ptsJ = [J_ini, (-93.4, -105.8, J_ini[2]), (-101.0, -105.8, J_ini[2])]; segJ = [(ptsJ[i], ptsJ[i + 1]) for i in range(2)]; distJ = sum(math.hypot(e[0] - s[0], e[1] - s[1]) for s, e in segJ)
    FPB_J = FPU; TOT_J = max(24, round(distJ * FPB_J)); E_J = S_J + TOT_J - 1; CL = max(4, round(25 * 0.5)); RM = dict(leg=1.7, spine=1.6, tail=1.5, head=0.6, ear=0.7); BOBJ = 0.05
    fpsJ, cumJ = asignar(segJ, TOT_J)
    def sw(fr, period, amp, phase=0, off=0): return amp * math.sin(2 * math.pi * fr / period + phase) + off
    def nrm(fr): return ((fr - 1) % CL) + 1
    def leg_slow(fr, rear, left):
        n = nrm(fr); ph = 0 if left else math.pi; amp = (0.4 if rear else 0.3) * RM['leg']; return (-sw(n, CL, amp, ph), -sw(n, CL, amp * 0.15, ph), -sw(n, CL, amp * 0.03, ph))
    def leg_bend(fr, rear, left):
        n = nrm(fr); ph = 0 if left else math.pi; bb = (0.3 if rear else 0.24) * RM['leg']; return (-abs(sw(n, CL, bb, ph, bb)), -sw(n, CL, 0.1, ph), -sw(n, CL, 0.04, ph))
    def foot_strike(fr, rear, left):
        n = nrm(fr); ph = 0 if left else math.pi; ax = (0.8 if rear else 0.6) * RM['leg']
        return (-sw(n, CL, ax, ph, 0.4 if rear else -0.1), abs(sw(n, CL, 0.04, ph, 0.02)) * (1.0 if rear else 0.5), -sw(n, CL, 0.04 if rear else 0.06, ph, 0.02))
    def toe_curl(fr, rear, left):
        n = nrm(fr); ph = 0 if left else math.pi; amp = 0.5 * RM['leg']; return (abs(sw(n, CL, amp, ph, 0.4)), -sw(n, CL, 0.16, ph), -sw(n, CL, 0.08, ph, 0.04))
    def tail_wag(fr):
        n = nrm(fr); t = RM['tail']; return (sw(n, CL, 0.4 * t, 0, 0.2 * t), sw(n, CL, 0.06 * t), sw(n, CL, 0.16 * t))
    def ear_tw(fr):
        n = nrm(fr); return (0, sw(n, CL, 0.2 * RM['ear']), sw(n, CL, 0.1 * RM['ear']))
    def pose_jerry(fr):
        k = {}; mul = lambda v, m: tuple(x * m for x in v)
        k['shoulder.L'] = leg_slow(fr, True, True); k['shoulder.R'] = leg_slow(fr, True, False); k['thigh.L'] = mul(leg_slow(fr, True, True), 0.01); k['thigh.R'] = mul(leg_slow(fr, True, False), -0.3)
        k['shin.L'] = leg_bend(fr, True, True); k['shin.R'] = leg_bend(fr, True, False); k['foot.L'] = foot_strike(fr, True, True); k['foot.R'] = foot_strike(fr, True, False); k['toe.L'] = toe_curl(fr, True, True); k['toe.R'] = toe_curl(fr, True, False)
        k['front_shoulder.L'] = leg_slow(fr + 12, False, True); k['front_shoulder.R'] = leg_slow(fr + 12, False, False); k['front_thigh.L'] = mul(leg_slow(fr + 12, False, True), 0.6); k['front_thigh.R'] = mul(leg_slow(fr + 12, False, False), 0.4)
        k['front_shin.L'] = leg_bend(fr + 12, False, True); k['front_shin.R'] = leg_bend(fr + 12, False, False); k['front_foot.L'] = foot_strike(fr + 12, False, True); k['front_foot.R'] = foot_strike(fr + 12, False, False)
        k['front_toe.L'] = toe_curl(fr + 12, False, True); k['front_toe.R'] = toe_curl(fr + 12, False, False)
        for i in range(1, 8): k[f'spine_{i}'] = (-sw(nrm(fr), CL, 0.03 * RM['spine'], (i / 7) * math.pi, -0.08 * RM['spine']), 0, 0)
        for i in range(1, 4): k[f'tail_{i}'] = tail_wag(fr)
        n = nrm(fr); k['scull'] = (sw(n, CL, 0.03 * RM['head']) + sw(n, CL, 0.016 * RM['head']) * 0.3 * 0, sw(n, CL, 0.05 * RM['head']), sw(n, CL, 0.016 * RM['head'])); k['jaw_top'] = (0.224, 0, 0); k['ear.L'] = ear_tw(fr); k['ear.R'] = ear_tw(fr + 6); k['sombrero'] = (0, 0, 0)
        return k
    smJ = RotationSmoother(12); smJ.prev = smJ.norm(rzJ0d); rzpJ = rzJ0d; angJ = {}
    for t in range(S_J, E_J + 1):
        pf = t - S_J + 1; pos = pos_de(segJ, fpsJ, cumJ, min(pf, TOT_J), False); a = smJ.go(ang_de(segJ, cumJ, pf, False, True), t); rzd = desenrollar(rzpJ, a); rzpJ = rzd; angJ[t] = math.radians(rzd)
        nn = nrm(pf); bob = BOBJ * (0.5 - 0.5 * math.cos(2 * math.pi * nn / CL * 2))
        EJ.location = (pos[0], pos[1], pos[2] + bob); EJ.rotation_euler = (rxJ, ryJ, math.radians(rzd)); EJ.keyframe_insert("location", frame=t); EJ.keyframe_insert("rotation_euler", frame=t)
        w = ss((t - (S_J - 1)) / 6.0); Pj = pose_jerry(pf)
        for n in NB_J: poner(PBJ[n], t, Pj[n], BASE_J[n], w)
    # anclas de Jerry antes de arrancar (quieto hasta S_J-1)
    for n in NB_J: key_rot(PBJ[n], S_J - 1, BASE_J[n])
    EJ.location = J_ini; EJ.rotation_euler = (rxJ, ryJ, math.radians(rzJ0d)); EJ.keyframe_insert("location", frame=S_J - 1); EJ.keyframe_insert("rotation_euler", frame=S_J - 1)
    sc.frame_end = max(sc.frame_end, E_A + 20, E_J + 20, ATT_END + 20)
    # ---------- sonidos de pasos (apoyo = pie en su punto mas adelantado, medido en la escena) ----------
    def apoyos(arm, root, huesos, f0, f1, ang):
        ser = {h: [] for h in huesos}; out = {h: [] for h in huesos}
        for t in range(f0, f1 + 1):
            sc.frame_set(t); a = ang[t]; fwd = Vector((-math.sin(a), math.cos(a), 0)); org = root.matrix_world.translation
            for h in huesos: ser[h].append(((arm.matrix_world @ arm.pose.bones[h].tail - org).dot(fwd)))
        for h in huesos:
            s = ser[h]; m = sum(s) / len(s)
            for i in range(1, len(s) - 1):
                if s[i] > s[i - 1] and s[i] >= s[i + 1] and s[i] > m: out[h].append(f0 + i)
        return out
    apA = apoyos(AA, EA, ["Rightknee_alfred", "Leftknee_alfred"], T_CORRE + 3, E_A, angA); apJ = apoyos(JA, EJ, ["foot.L", "foot.R", "front_foot.L", "front_foot.R"], S_J + 8, E_J, angJ)
    pasosA = sorted(f for v in apA.values() for f in v); pasosJ = sorted(f for v in apJ.values() for f in v)
    for j, f in enumerate(pasosA):
        s_ = sonido(f"huida_paso_alfred_{j + 1}_{f}".replace(f"_{f}", "") + f"", f"step/grass{(j * 5) % 6 + 1}.ogg", f, 0.85, canal_libre(ed, f, f + 20), "huida_alfred"); s_["guion_id"] = f"snd6_jerry_p_huida_alfred_{j + 1}"
    for j, f in enumerate(pasosJ):
        s_ = sonido(f"huida_paso_jerry_{j + 1}", f"step/grass{(j * 5 + 3) % 6 + 1}.ogg", f, 0.32, canal_libre(ed, f, f + 20), "huida_jerry"); s_["guion_id"] = f"snd6_jerry_p_huida_jerry_{j + 1}"
    res = {}
    for f in (T0 + 5, T0 + 20, TC + 5, TG0 - 1, TG1, TS + 4, TS + 15, T_CORRE - 1, T_CORRE + 20, E_A, E_J):
        sc.frame_set(f); res[f] = {"A": [round(x, 2) for x in EA.location], "rzA": round(math.degrees(EA.rotation_euler.z), 1), "J": [round(x, 2) for x in EJ.location], "C_rz": round(math.degrees(CR.rotation_euler.z), 1), "neckY": round(math.degrees(NECK.rotation_euler[1]), 1), "headCY": round(math.degrees(HEADC.rotation_euler[1]), 1)}
    sc.frame_set(120); print("Alfred corre", round(dist, 2), "m", TOT_A, "f (f", T_CORRE, "-", E_A, ") | Jerry", round(distJ, 2), "m", TOT_J, "f (f", S_J, "-", E_J, ")"); print(res); print("pasos Alfred", pasosA); print("pasos Jerry", pasosJ); print("LISTO")
except Exception:
    traceback.print_exc()
