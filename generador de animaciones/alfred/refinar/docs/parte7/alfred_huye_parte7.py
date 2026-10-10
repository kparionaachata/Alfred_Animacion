# -*- coding: utf-8 -*-
"""Parte 7: el creeper (tumbado) da una convulsion y empieza a brillar (f668, `creeper_convulsion_parte7.py`); Alfred se asusta y SALE CORRIENDO por `recorridos/alfred_2.json` (de (-109.5, -88.5) a (-109.5, -84.5), hacia +y), pero con el TOBILLO ADOLORIDO.
- f671-681 SUSTO (ELASTIC IN-OUT, 8 f + 2 quietos): cabeza arriba, el torso se echa hacia atras y los brazos RECTOS suben hacia los lados; mientras, gira hacia el rumbo de la carrera.
- f681-: INTENTA CORRER CON EL TOBILLO ADOLORIDO (carrera cojeando): el ciclo CORRER del estudio (el de `alfred_corre_tobillo_parte7.py`) pero lento (velocidad 60 %, ciclo de ~14 f), la pierna derecha (la del tobillo) oscila solo 45 % y flexiona la rodilla 50 %,
  el torso mas inclinado (+7.5 grados) y la cabeza gacha (+10), la cadera cae hacia el lado sano y el cuerpo baja ~4.5 cm al apoyar la derecha; el susto se funde al ciclo en 6 f con la velocidad subiendo de 0 a la normal en esos 6 f.
- AL FINAL DEL RECORRIDO (a `D_TORCER` = 1.5 bloques del ultimo punto: mas cerca, al caer boca abajo con los brazos adelante atravesaria el bloque de la plataforma que empieza en y -84) SE LE VUELVE A TORCER EL TOBILLO y CAE DE CARA AL SUELO otra vez, igual que la primera vez (`alfred_tobillo_caida.py`): tobillo torcido (1 f: la espinilla gira 35 grados y se dobla 14, brazos arriba),
  caida de 4 f hasta quedar boca abajo con los brazos adelante, la inercia lo lleva 0.35 m, rebote SOLO de la cintura para arriba (3 arcos de 6, 4 y 3 f, columna 20 grados) y se queda boca abajo hasta el final.
Parte de la pose de f670 y borra sus claves >= f671. Se ejecuta dentro de Blender: exec(open(RUTA, encoding='utf-8').read()). Variables opcionales: T_HUYE (671), D_TORCER (1.5), V_COJO (0.6)."""
import bpy, math, json
from mathutils import Vector, Matrix, Euler, Quaternion

sc = bpy.context.scene
exec(open(r'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/parte3/ik_brazos.py', encoding='utf-8').read(), globals())     # fk, mundo, REST, resolver, cabeza_cola, AA, OO
EA = OO
DOCS = 'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/parte7/'
T_R = int(globals().get('T_HUYE', 671)); RUTA = r'C:/Users/user/Desktop/alfred_2.json'; D_TORCER = float(globals().get('D_TORCER', 1.5)); V_COJO = float(globals().get('V_COJO', 0.6))
NB = ["Hips_alfred", "Spine_alfred", "Spine1_alfred", "Spine2_alfred", "Neck_alfred", "RightUpArm_alfred", "Rightelbow_alfred", "LeftUpArm_alfred", "Leftelbow_alfred", "RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred"]
PB = {n: AA.pose.bones[n] for n in NB}
Dg = math.radians
ss = lambda x: 0.0 if x <= 0 else 1.0 if x >= 1 else x * x * (3 - 2 * x)
cerca = lambda ref, v: v + 2 * math.pi * round((ref - v) / (2 * math.pi))
def ela(t):                                                                  # ELASTIC in-out (como creeper_susto_y_huida.py)
    if t <= 0: return 0.0
    if t >= 1: return 1.0
    c5 = (2 * math.pi) / 4.5
    return -(2 ** (20 * t - 10) * math.sin((20 * t - 11.125) * c5)) / 2 if t < 0.5 else (2 ** (-20 * t + 10) * math.sin((20 * t - 11.125) * c5)) / 2 + 1
def qint(q0, q1, u):
    d = q0.rotation_difference(q1); ax, an = d.to_axis_angle(); return q0 @ Quaternion(ax, an * u) if an > 1e-9 else q0.copy()
H_LOC = Vector((0.029, 0.026, -0.197))

# ---------- ciclo CORRER del estudio (definiciones de `alfred_corre_tobillo_parte7.py`, sin ejecutar su limpieza) ----------
src = open(DOCS + 'alfred_corre_tobillo_parte7.py', encoding='utf-8').read(); ns = {'math': math}
exec(src[src.index("ST = dict(speed=0.5"):src.index("dist = sum(")], ns)
pose_run, ST, FPU, CICLO = ns['pose_run'], ns['ST'], ns['FPU'], ns['CICLO']
CICLO_C = CICLO / V_COJO * 0.78                                              # ciclo mas largo al correr cojeando (~14 f)
def pose_cojo(wc):                                                           # CARRERA CON EL TOBILLO ADOLORIDO: la derecha apenas se apoya, la izquierda carga con todo, torso y cabeza gachos
    pr = dict(pose_run(wc))
    r = list(pr["RightUpLeg_alfred"]); r[0] *= 0.45; pr["RightUpLeg_alfred"] = tuple(r)
    k = list(pr["Rightknee_alfred"]); k[0] *= 0.5; pr["Rightknee_alfred"] = tuple(k)
    for sp in ("Spine_alfred", "Spine1_alfred", "Spine2_alfred"): a = list(pr[sp]); a[0] += Dg(2.5); pr[sp] = tuple(a)
    nk = list(pr["Neck_alfred"]); nk[0] += Dg(10.0); pr["Neck_alfred"] = tuple(nk)
    h = list(pr["Hips_alfred"]); h[2] += Dg(3.0) * math.sin(wc * 2 * math.pi); pr["Hips_alfred"] = tuple(h)           # la cadera cae hacia el lado sano al apoyar
    return pr
def bob_cojo(wc): return -0.045 * max(0.0, math.sin((wc + 0.5) * 2 * math.pi + math.pi / 2)) + 0.012 * math.sin(wc * 4 * math.pi)

# ---------- pose de partida (antes de tocar las claves) ----------
sc.frame_set(T_R - 1); bpy.context.view_layer.update()
BASE = {n: tuple(PB[n].rotation_euler) for n in NB}; BASE_H = Vector(PB["Hips_alfred"].location); ROOT0 = Vector(EA.location); RZ0 = EA.rotation_euler.z; rx, ry = EA.rotation_euler.x, EA.rotation_euler.y
M0 = fk({}, {"Hips_alfred": tuple(H_LOC)}); Mw0 = mundo((0, 0, 0), 0.0)
tails = [Mw0 @ (M0[n] @ Vector((0, REST[n][2], 0))) for n in ("Rightknee_alfred", "Leftknee_alfred")]; D0 = Vector((-(tails[0].x + tails[1].x) / 2, -(tails[0].y + tails[1].y) / 2, 0.0))
P_FEET = Vector((ROOT0.x, ROOT0.y, ROOT0.z)) - Matrix.Rotation(RZ0, 3, 'Z') @ D0                       # punto entre los pies ahora
RUTA_PTS = [Vector((k['coordinates']['x'], k['coordinates']['y'], k['coordinates']['z'])) for k in json.load(open(RUTA))['key_points']]
PATH = [Vector((P_FEET.x, P_FEET.y, ROOT0.z))] + RUTA_PTS
SEG = [(PATH[i + 1] - PATH[i]).length for i in range(len(PATH) - 1)]; LTOT = sum(SEG)
def en_camino(d):
    d = min(max(d, 0.0), LTOT); acc = 0.0
    for i, L in enumerate(SEG):
        if d <= acc + L or i == len(SEG) - 1: f = (d - acc) / max(L, 1e-9); return PATH[i].lerp(PATH[i + 1], min(1.0, max(0.0, f))), (PATH[i + 1] - PATH[i])
        acc += L
def rumbo_en(d): v = en_camino(min(d + 0.2, LTOT))[1]; v = v if v.length > 1e-6 else Vector((0, 1, 0)); return -math.atan2(v.x, v.y)

# ---------- pose del susto: cabeza arriba, torso atras, brazos rectos hacia los lados y arriba ----------
R3 = Matrix.Rotation(RZ0, 3, 'Z'); DER, IZQ, ARR = R3 @ Vector((1, 0, 0)), R3 @ Vector((-1, 0, 0)), Vector((0, 0, 1))
S = dict(BASE)
for sp in ("Spine_alfred", "Spine1_alfred", "Spine2_alfred"): S[sp] = (Dg(-4.0), BASE[sp][1], BASE[sp][2])
S["Neck_alfred"] = (Dg(-10.0), 0.0, 0.0)
Mw = mundo(tuple(ROOT0), RZ0); MS = fk(S, {"Hips_alfred": tuple(BASE_H)})
def qdir(l, M, d):                                                           # rotacion del hombro para que el brazo ESTIRADO apunte a la direccion mundo d
    Rsp = REST["Spine2_alfred"][0]; Rup = REST[l + "UpArm_alfred"][0]; A = (Mw @ (M["Spine2_alfred"] @ (Rsp.inverted() @ Rup))).to_3x3()
    dl = A.inverted() @ Vector(d); dl.normalize(); return Vector((0, 1, 0)).rotation_difference(dl)
for l in ("Right", "Left"):
    th = Dg(45.0); d = (DER if l == "Right" else IZQ) * math.cos(th) + ARR * math.sin(th); q = qdir(l, MS, d)
    q0 = Euler(BASE[l + "UpArm_alfred"], 'XYZ').to_quaternion(); q = q if q0.dot(q) >= 0 else -q
    S[l + "UpArm_alfred"] = tuple(q.to_euler('XYZ', Euler(BASE[l + "UpArm_alfred"], 'XYZ'))); S[l + "elbow_alfred"] = (0.0, 0.0, 0.0)

# ---------- claves ----------
act = AA.animation_data.action
for fc in [fc for l in act.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]:
    for i in range(len(fc.keyframe_points) - 1, -1, -1):
        if fc.keyframe_points[i].co.x >= T_R: fc.keyframe_points.remove(fc.keyframe_points[i])
if EA.animation_data and EA.animation_data.action:
    for fc in [fc for l in EA.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]:
        for i in range(len(fc.keyframe_points) - 1, -1, -1):
            if fc.keyframe_points[i].co.x >= T_R: fc.keyframe_points.remove(fc.keyframe_points[i])
def key_rot(pb, f, v):
    pb.rotation_euler = v
    for ax in range(3): pb.keyframe_insert("rotation_euler", index=ax, frame=f, group=pb.name)
def key_hips(f, v):
    PB["Hips_alfred"].location = v
    for ax in range(3): PB["Hips_alfred"].keyframe_insert("location", index=ax, frame=f, group="Hips_alfred")
def key_root(f, loc, rz):
    EA.location = loc; EA.rotation_euler = (rx, ry, rz); EA.keyframe_insert("location", frame=f); EA.keyframe_insert("rotation_euler", frame=f)
prev = {n: Euler(BASE[n], 'XYZ') for n in NB}
def mezcla(A, B, u):                                                         # por cuaternion (u puede pasarse de 1 con el elastico) para brazos; lineal para el resto
    out = {}
    for n in NB:
        if n.endswith("UpArm_alfred"):
            qa = Euler(A[n], 'XYZ').to_quaternion(); qb = Euler(B[n], 'XYZ').to_quaternion(); qb = qb if qa.dot(qb) >= 0 else -qb
            e = qint(qa, qb, u).to_euler('XYZ', prev[n]); prev[n] = e; out[n] = tuple(e)
        else:
            e = [cerca(A[n][c], B[n][c]) for c in range(3)]; out[n] = tuple(A[n][c] + (e[c] - A[n][c]) * u for c in range(3))
    return out
key_root(T_R - 1, tuple(ROOT0), RZ0); key_hips(T_R - 1, tuple(BASE_H))
for n in NB: key_rot(PB[n], T_R - 1, BASE[n])
t = T_R; RZ = RZ0; N_S = 8
RZ_RUN0 = rumbo_en(0.0); RZ_RUN0 += 2 * math.pi * round((RZ0 - RZ_RUN0) / (2 * math.pi))
for k in range(1, N_S + 3):                                                  # SUSTO: elastico en 8 f y 2 quietos; empieza a girar hacia el rumbo a mitad del susto
    u = ela(min(1.0, k / float(N_S))); vals = mezcla(BASE, S, u)
    RZ = RZ0 + (RZ_RUN0 - RZ0) * ss((k - 3) / 7.0)
    key_root(t, (ROOT0.x, ROOT0.y, ROOT0.z), RZ); key_hips(t, tuple(BASE_H))
    for n in NB: key_rot(PB[n], t, vals[n])
    t += 1
# CORRER COJEANDO: del susto al ciclo en 6 f, velocidad 0 -> V_COJO en esos 6 f, hasta D_TORCER bloques antes del ultimo punto
RAMP = 6; wc = 0.0; d = 0.0; k = 0; prev_rz = RZ; T_RUN0 = t; D_FALL = LTOT - D_TORCER
BLOCKS_PER_F = 1.0 / FPU
last = None
while d < D_FALL - 1e-6:
    v = (ss((k + 1) / float(RAMP)) if k < RAMP else 1.0) * V_COJO
    d = min(D_FALL, d + BLOCKS_PER_F * v); wc += v / V_COJO / CICLO_C
    p, _ = en_camino(d); tgt = rumbo_en(d); tgt += 2 * math.pi * round((prev_rz - tgt) / (2 * math.pi)); RZ = prev_rz + max(-0.25, min(0.25, tgt - prev_rz)); prev_rz = RZ
    wr = ss((k + 1) / float(RAMP)); pr = pose_cojo(wc % 1.0)
    vals = {n: tuple(S[n][c] + (cerca(S[n][c], pr[n][c]) - S[n][c]) * wr for c in range(3)) for n in NB}
    bob = bob_cojo(wc) * wr; Do = (Matrix.Rotation(RZ, 3, 'Z') @ D0)
    key_root(t, (p.x + Do.x, p.y + Do.y, p.z + bob), RZ); key_hips(t, tuple(BASE_H.lerp(H_LOC, wr)))
    for n in NB: key_rot(PB[n], t, vals[n])
    last = vals; t += 1; k += 1
T_TW = t - 1                                                                 # ultimo frame de la carrera; el tobillo se tuerce en el siguiente
p_fall = en_camino(D_FALL)[0]

# ---------- SE LE VUELVE A TORCER EL TOBILLO Y CAE DE CARA (mismas poses que `alfred_tobillo_caida.py`: F_TW tobillo, F_GR boca abajo, con IK de los brazos) ----------
F_TW, F_GR = T_TW + 1, T_TW + 5                                              # tobillo (1 f), caida de 4 f
def mk(hips_rot, spine, neck, rleg, rknee, lleg, lknee):
    return {"Hips_alfred": hips_rot, "Spine_alfred": (Dg(spine), 0, 0), "Spine1_alfred": (Dg(spine), 0, 0), "Spine2_alfred": (Dg(spine), 0, 0), "Neck_alfred": (neck if isinstance(neck, tuple) else (Dg(neck), 0, 0)),
            "RightUpLeg_alfred": rleg, "Rightknee_alfred": rknee, "LeftUpLeg_alfred": lleg, "Leftknee_alfred": lknee}
def coast(f): u = min(1.0, max(0.0, (f - T_TW) / 5.0)); return 0.35 * (1 - (1 - u) ** 2)                 # la inercia lo lleva ~0.35 m
def root_en(f):
    p = p_fall + Vector((0, coast(f), 0)); Do_ = Matrix.Rotation(RZ, 3, 'Z') @ D0; return (p.x + Do_.x, p.y + Do_.y, p.z + 0.07 * ss((f - T_TW) / 5.0))                         # +7 cm: boca abajo la malla queda en z 14.99 como en la primera caida (si no, 14.92)
FRA = {F_TW: (mk((Dg(18), 0, Dg(12)), 10, 8, (Dg(20), Dg(8), Dg(-18)), (Dg(-60), Dg(35), Dg(14)), (Dg(-40), 0, Dg(8)), (Dg(-70), 0, 0)), (H_LOC.x, H_LOC.y - 0.06, H_LOC.z)),
       F_GR: (mk((Dg(88), 0, Dg(-6)), -6, (Dg(-8), Dg(55), 0), (Dg(0), Dg(10), Dg(-28)), (Dg(-75), Dg(40), Dg(12)), (Dg(0), Dg(-6), Dg(10)), (Dg(-8), 0, 0)), (0.0, -0.747, -0.05))}
R3f = Matrix.Rotation(RZ, 3, 'Z'); FWDf, DERf, IZQf = R3f @ Vector((0, 1, 0)), R3f @ Vector((1, 0, 0)), R3f @ Vector((-1, 0, 0))
def alto(M, Mw_, raiz, l): sh = Mw_ @ M["Spine2_alfred"].translation; return sh + FWDf * 0.20 + (DERf if l == "Right" else IZQf) * 0.40 + ARR * 0.50          # brazos arriba y adelante (se desequilibra)
def adelante(M, Mw_, raiz, l): sh = Mw_ @ M["Spine2_alfred"].translation; return Vector((sh.x + (0.30 if l == "Right" else -0.30), sh.y + 0.65, raiz[2] + 0.07))   # manos estiradas hacia delante sobre el suelo
OBJ = {F_TW: alto, F_GR: adelante}
ARMS = {}                                                                    # frame -> {l: (q hombro, q codo)}
qprev = {l: (Euler(last[l + "UpArm_alfred"], 'XYZ').to_quaternion(), Euler(last[l + "elbow_alfred"], 'XYZ').to_quaternion()) for l in ("Right", "Left")}
for f in (F_TW, F_GR):
    rot_, hips_ = FRA[f]; rt = root_en(f); Mk = fk(rot_, {"Hips_alfred": hips_}); Mwk = mundo(rt, RZ); ARMS[f] = {}
    for l in ("Right", "Left"):
        tgt = OBJ[f](Mk, Mwk, rt, l); hint = tgt - (DERf if l == "Right" else IZQf) * 0.20 + Vector((0, -0.10, -0.05)); q0, qe0 = qprev[l]; x0 = 2 * math.atan2(qe0.x, qe0.w)
        q, qe, err, _ = resolver(l, Mk["Spine2_alfred"], Mwk, tgt, codo_hint=hint, inicio=(q0, x0), iters=5000, semilla=3); ARMS[f][l] = (q, qe); qprev[l] = (q, qe); print("IK caida f%d %s: error de muneca %.3f m" % (f, l, err))
KEYS = {T_TW: dict(rot={n: tuple(last[n]) for n in NB if "Arm" not in n and "elbow" not in n}, hips=tuple(H_LOC), arm={l: (Euler(last[l + "UpArm_alfred"], 'XYZ').to_quaternion(), Euler(last[l + "elbow_alfred"], 'XYZ').to_quaternion()) for l in ("Right", "Left")})}
for f in (F_TW, F_GR): KEYS[f] = dict(rot=FRA[f][0], hips=FRA[f][1], arm=ARMS[f])
orden = sorted(KEYS)
REBOTES = ((6, 0.16), (4, 0.06), (3, 0.02)); REBOTE_FRAMES = sum(d_ for d_, _ in REBOTES); REBOTE_GRADOS = 20.0
def rebote(tt):
    acc = 0
    for D_, A_ in REBOTES:
        if tt < acc + D_: u = (tt - acc) / float(D_); return A_ * 4 * u * (1 - u)
        acc += D_
    return 0.0
def pose_en(f):
    if f >= orden[-1]: K = KEYS[orden[-1]]; return {n: tuple(v) for n, v in K["rot"].items()}, K["hips"], K["arm"]
    j = max(k_ for k_ in range(len(orden)) if orden[k_] <= f); a, b = KEYS[orden[j]], KEYS[orden[j + 1]]; u = ss((f - orden[j]) / float(orden[j + 1] - orden[j]))
    rot = {}
    for n in a["rot"]:
        ea, eb = a["rot"][n], b["rot"][n]; rot[n] = tuple(ea[c] + (cerca(ea[c], eb[c]) - ea[c]) * u for c in range(3))
    hips = tuple(a["hips"][c] + (b["hips"][c] - a["hips"][c]) * u for c in range(3))
    arm = {l: (a["arm"][l][0].slerp(b["arm"][l][0] if a["arm"][l][0].dot(b["arm"][l][0]) >= 0 else -b["arm"][l][0], u), a["arm"][l][1].slerp(b["arm"][l][1] if a["arm"][l][1].dot(b["arm"][l][1]) >= 0 else -b["arm"][l][1], u)) for l in ("Right", "Left")}
    return rot, hips, arm
prevE = {}; prevA = {}
T_FIN = F_GR + REBOTE_FRAMES + 1
for f in range(F_TW, T_FIN + 1):
    rot, hips, arm = pose_en(f); rot = {n: list(v) for n, v in rot.items()}; hl = list(hips)
    if F_GR <= f < F_GR + REBOTE_FRAMES:                                     # rebote al caer de cara: SOLO de la cintura para arriba (la cadera y las piernas quedan en el suelo; la columna se arquea)
        for s_ in ("Spine_alfred", "Spine1_alfred", "Spine2_alfred"): rot[s_][0] -= Dg(REBOTE_GRADOS) * rebote(f - F_GR) / REBOTES[0][1] / 3.0
    key_root(f, root_en(f), RZ); key_hips(f, tuple(hl))
    for n, v in rot.items():
        vv = tuple(cerca(prevE.get((n, c), v[c]), v[c]) for c in range(3)); key_rot(PB[n], f, vv); prevE.update({(n, c): vv[c] for c in range(3)})
    for l in ("Right", "Left"):
        q, qe = arm[l]
        eu = q.to_euler('XYZ', prevA.get(l + "u", Euler(last[l + "UpArm_alfred"], 'XYZ'))); ee = qe.to_euler('XYZ', prevA.get(l + "e", Euler(last[l + "elbow_alfred"], 'XYZ'))); prevA[l + "u"], prevA[l + "e"] = eu, ee
        key_rot(PB[l + "UpArm_alfred"], f, tuple(eu)); key_rot(PB[l + "elbow_alfred"], f, tuple(ee))
for fc in [fc for l in act.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves] + [fc for l in EA.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]:
    for kp in fc.keyframe_points:
        if kp.co.x >= T_R - 1: kp.interpolation = 'LINEAR'
sc.frame_end = max(sc.frame_end, T_FIN)
sc.frame_set(T_R - 1)
print("Alfred huye: susto f%d-%d (elastico), corre cojeando f%d-%d por %d puntos (%.2f bloques, de (%.2f, %.2f) a (%.2f, %.2f)), se le tuerce el tobillo en f%d, cae de cara f%d-%d, rebota hasta f%d y se queda boca abajo" % (
    T_R, T_R + N_S + 1, T_RUN0, T_TW, len(RUTA_PTS), LTOT, P_FEET.x, P_FEET.y, RUTA_PTS[-1].x, RUTA_PTS[-1].y, F_TW, F_TW, F_GR, T_FIN))
