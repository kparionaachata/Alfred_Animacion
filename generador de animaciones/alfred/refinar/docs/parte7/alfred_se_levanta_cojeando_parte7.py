# -*- coding: utf-8 -*-
"""Parte 7: a partir de f494 Alfred (sentado, girado 180 grados, tras cubrirse la cara y levantar la cabeza, como lo deja `alfred_tira_pollo_parte7.py` hasta f493) SE LEVANTA COJEANDO: el tobillo derecho esta danado.
- f494-499: recoge las piernas (los pies vienen hacia la cadera), el torso se inclina hacia delante y las manos bajan al suelo a los lados de la cadera.
- f499-505: empuja con las manos (se quedan plantadas, IK) y la cadera sube sobre el pie izquierdo; torso muy inclinado (62 grados).
- f505-514: la cadera sigue subiendo, el torso se endereza y las manos se despegan del suelo.
- f514-524: de pie cojeando: el peso en la pierna izquierda (cadera desplazada hacia la izquierda), el pie derecho adelantado y solo apoyado de punta (talon a ~8 cm), brazos colgando (el izquierdo un poco abierto para el equilibrio), cabeza gacha hacia el tobillo.
Despues se queda asi (sin mas claves). Piernas con IK propia (UpLeg xyz + knee X, objetivo = cola del hueso `knee`), brazos con `resolver` de `docs/parte3/ik_brazos.py`; la cadera la coloca `hips_loc` (resuelve la traslacion local del hueso Hips para un punto mundo).
Se ejecuta dentro de Blender: exec(open(RUTA, encoding='utf-8').read()). Idempotente (parte de la pose de T_BASE (f491, con la cabeza ya levantada), que esta antes de las claves propias; borra sus claves >= f494). Variables: T_LEVANTA (494), T_BASE (491: frame de donde lee la pose de partida: cabeza levantada tras cubrirse la cara), HZ, FIX."""
import bpy, math, random
from mathutils import Vector, Matrix, Euler, Quaternion

sc = bpy.context.scene
exec(open(r'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/parte3/ik_brazos.py', encoding='utf-8').read(), globals())     # fk, mundo, resolver, REST, AA, OO
EA = OO
T0 = int(globals().get('T_LEVANTA', 494)); T_BASE = int(globals().get('T_BASE', 491)); HZ = float(globals().get('HZ', 15.16))
import json, os
_FJ = r'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/parte7/alfred_se_levanta_cojeando_fix.json'
_FD = {(k.split(':')[0], int(k.split(':')[1])): v for k, v in json.load(open(_FJ)).items()} if os.path.isfile(_FJ) else {}
FIX = dict(globals().get('FIX') or _FD)                                       # correcciones de z por frame de IK {('fL'|'fR'|'hL'|'hR', f): dz} medidas con las mallas (la cola del hueso no es la suela del pie ni la base de la mano); por defecto las del archivo alfred_se_levanta_cojeando_fix.json
Dg = math.radians
ss = lambda x: 0.0 if x <= 0 else 1.0 if x >= 1 else x * x * (3 - 2 * x)
cerca = lambda ref, v: v + 2 * math.pi * round((ref - v) / (2 * math.pi))
BONES = ["Hips_alfred", "Spine_alfred", "Spine1_alfred", "Spine2_alfred", "Neck_alfred", "RightUpArm_alfred", "Rightelbow_alfred", "LeftUpArm_alfred", "Leftelbow_alfred", "RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred"]
ARM = ("RightUpArm_alfred", "LeftUpArm_alfred"); SP = ("Spine_alfred", "Spine1_alfred", "Spine2_alfred")

# ---------- pose de partida (antes de tocar las claves) ----------
sc.frame_set(T_BASE); bpy.context.view_layer.update()
ROT0 = {b: tuple(AA.pose.bones[b].rotation_euler) for b in BONES}; LOC0 = tuple(AA.pose.bones["Hips_alfred"].location)
rt = tuple(EA.location); rz = EA.rotation_euler.z; Mw = mundo(rt, rz)
R3 = Matrix.Rotation(rz, 3, 'Z'); FWD, DER, IZQ, ARR = R3 @ Vector((0, 1, 0)), R3 @ Vector((1, 0, 0)), R3 @ Vector((-1, 0, 0)), Vector((0, 0, 1))
GZ = rt[2]                                                                    # suelo

def mat(rot, loc): return fk(rot, loc)
def pt(M, n, e="h"): return Mw @ (M[n].translation if e == "h" else M[n] @ Vector((0, REST[n][2], 0)))
def hips_loc(rot, loc, objetivo):
    base = dict(loc); base["Hips_alfred"] = (0, 0, 0); p0 = pt(mat(rot, base), "Hips_alfred"); cols = []
    for ax in range(3):
        v = [0, 0, 0]; v[ax] = 1.0; b2 = dict(loc); b2["Hips_alfred"] = tuple(v); cols.append(pt(mat(rot, b2), "Hips_alfred") - p0)
    A = Matrix(((cols[0].x, cols[1].x, cols[2].x), (cols[0].y, cols[1].y, cols[2].y), (cols[0].z, cols[1].z, cols[2].z)))
    s = A.inverted() @ (Vector(objetivo) - p0); return (s.x, s.y, s.z)
def pata(lado, rot, loc, objetivo, prior, intentos=2, seed=2, iters=500):
    up, kn = f"{lado}UpLeg_alfred", f"{lado}knee_alfred"; rng = random.Random(seed); objetivo = Vector(objetivo)
    def coste(p):
        r = dict(rot); r[up] = (p[0], p[1], p[2]); r[kn] = (p[3], 0, 0); c = (pt(mat(r, loc), kn, "t") - objetivo).length
        if p[3] > 0.02: c += 5 * (p[3] - 0.02)
        if p[3] < -2.6: c += 5 * (-2.6 - p[3])
        return c + 0.004 * sum(abs(p[i] - prior[i]) for i in range(4))
    mejor = None
    arr = [list(prior)] + [[prior[0] + rng.uniform(-1.5, 1.5), prior[1] + rng.uniform(-0.8, 0.8), prior[2] + rng.uniform(-0.6, 0.6), rng.uniform(-2.4, 0)] for _ in range(intentos)]
    for par in arr:
        c = coste(par); paso = 0.4
        for it in range(iters):
            cand = [v + rng.gauss(0, paso) for v in par]; cc = coste(cand)
            if cc < c: par, c = cand, cc
            elif it % 40 == 39: paso = max(paso * 0.7, 0.002)
        if mejor is None or c < mejor[0]: mejor = (c, par)
    p = mejor[1]; r = dict(rot); r[up] = (p[0], p[1], p[2]); r[kn] = (p[3], 0, 0)
    return p, (pt(mat(r, loc), kn, "t") - objetivo).length

# ---------- plan: estados clave (offset de frame, cadera mundo, inclinacion total del torso en grados, cuello X en grados, pie izq, pie der) ----------
V = lambda x, y, z: Vector((x, y, z))
P_L = lambda y, z=GZ: V(rt[0] + 0.135, y, z)                                      # pie izquierdo (cola del hueso knee): Alfred esta de frente a -y, su izquierda es +x
P_R = lambda y, z=GZ: V(rt[0] - 0.147, y, z)
ZP = GZ - 0.113                                                                   # de pie con la pierna estirada la cola del hueso queda 0.11 m BAJO la suela (pose por defecto: cola z 14.887 con el root a 15)
ST = [  # (offset, hips, lean, neck, footL, footR)
    (5,  V(rt[0] + 0.005, rt[1] - 0.09, 15.30), 38.0,  6.0, P_L(rt[1] - 0.44), P_R(rt[1] - 0.59)),
    (11, V(rt[0] + 0.055, rt[1] - 0.40, 15.55), 62.0, -8.0, P_L(rt[1] - 0.44), P_R(rt[1] - 0.59)),
    (20, V(rt[0] + 0.040, rt[1] - 0.20, 15.80), 26.0,  0.0, P_L(rt[1] - 0.20, ZP), P_R(rt[1] - 0.44, ZP + 0.05)),
    (30, V(rt[0] + 0.055, rt[1] - 0.04, 15.88),  6.0, 12.0, P_L(rt[1] - 0.00, ZP), P_R(rt[1] - 0.34, ZP + 0.09)),
]
HAND_G = {"Right": V(rt[0] - 0.52, rt[1] - 0.45, HZ), "Left": V(rt[0] + 0.52, rt[1] - 0.45, HZ)}                              # manos apoyadas a los lados (y un poco delante) de la cadera
HAND_R = {"Right": V(rt[0] - 0.50, rt[1] - 0.30, HZ + 0.40), "Left": V(rt[0] + 0.50, rt[1] - 0.30, HZ + 0.40)}                # al despegarse suben y se acercan al cuerpo
HIPS_ROT0 = ROT0["Hips_alfred"]
S0 = (0, pt(mat(ROT0, {"Hips_alfred": LOC0}), "Hips_alfred"), math.degrees(sum(ROT0[s][0] for s in SP)), math.degrees(ROT0["Neck_alfred"][0]),
      pt(mat(ROT0, {"Hips_alfred": LOC0}), "Leftknee_alfred", "t"), pt(mat(ROT0, {"Hips_alfred": LOC0}), "Rightknee_alfred", "t"))
STS = [S0] + ST
def plan(f):
    o = f - T0
    for a, b in zip(STS, STS[1:]):
        if a[0] <= o <= b[0]:
            t = ss((o - a[0]) / float(b[0] - a[0])); L = lambda x, y: x + (y - x) * t
            return dict(h=a[1].lerp(b[1], t), lean=L(a[2], b[2]), neck=L(a[3], b[3]), fL=a[4].lerp(b[4], t), fR=a[5].lerp(b[5], t))
    b = STS[-1]; return dict(h=b[1], lean=b[2], neck=b[3], fL=b[4], fR=b[5])
def hand_target(lado, f, M):
    o = f - T0
    if o <= 11: return HAND_G[lado]
    if o <= 20: t = ss((o - 11) / 9.0); return HAND_G[lado].lerp(HAND_R[lado], t)
    t = ss((o - 20) / 10.0); sh = pt(M, f"{lado}UpArm_alfred"); lado_v = DER if lado == "Right" else IZQ
    colgar = sh + lado_v * (0.18 if lado == "Right" else 0.34) + Vector((0, 0, -0.88)) + FWD * 0.03
    return HAND_R[lado].lerp(colgar, t)

# ---------- IK en frames sueltos (cada 2 f desde K1) ----------
SOL = [(T0, dict(rot=dict(ROT0), loc=LOC0))]
F_IK = sorted(set([T0 + 5] + list(range(T0 + 7, T0 + 30, 2)) + [T0 + 30]))
prior_leg = {l: [*ROT0[f"{l}UpLeg_alfred"], ROT0[f"{l}knee_alfred"][0]] for l in ("Right", "Left")}
prior_arm = {l: (Euler(ROT0[f"{l}UpArm_alfred"], 'XYZ').to_quaternion(), 2 * math.atan2(Euler(ROT0[f"{l}elbow_alfred"], 'XYZ').to_quaternion().x, Euler(ROT0[f"{l}elbow_alfred"], 'XYZ').to_quaternion().w)) for l in ("Right", "Left")}
errs = {}
for k, f in enumerate(F_IK):
    pl = plan(f); rot = dict(ROT0); loc = {}
    for s in SP: e = list(ROT0[s]); e[0] = Dg(pl["lean"] / 3.0); rot[s] = tuple(e)
    e = list(ROT0["Neck_alfred"]); e[0] = Dg(pl["neck"]); rot["Neck_alfred"] = tuple(e)
    w = ss((f - T0) / 30.0); rot["Hips_alfred"] = tuple(HIPS_ROT0[i] * (1 - w) for i in range(3))
    loc["Hips_alfred"] = hips_loc(rot, {"Hips_alfred": LOC0}, pl["h"])
    for lado, fp in (("Left", pl["fL"] + Vector((0, 0, FIX.get(('fL', f), 0.0)))), ("Right", pl["fR"] + Vector((0, 0, FIX.get(('fR', f), 0.0))))):
        p, err = pata(lado, rot, loc, fp, prior_leg[lado], intentos=(14 if k == 0 else 2), seed=3 + k); prior_leg[lado] = p
        rot[f"{lado}UpLeg_alfred"] = (p[0], p[1], p[2]); rot[f"{lado}knee_alfred"] = (p[3], 0, 0); errs[f"pie{lado}{f}"] = round(err, 3)
    M = mat(rot, loc)
    for lado in ("Right", "Left"):
        up, el = f"{lado}UpArm_alfred", f"{lado}elbow_alfred"; sh = pt(M, up); lado_v = DER if lado == "Right" else IZQ
        obj = hand_target(lado, f, M) + Vector((0, 0, FIX.get(('h' + lado[0], f), 0.0))); hint = sh + lado_v * 0.30 - Vector((0, 0, 0.25))
        q, qx, err, codo = resolver(lado, M["Spine2_alfred"], Mw, obj, codo_hint=hint, inicio=prior_arm[lado], iters=(9000 if k == 0 else 2400), semilla=3 + k, w_codo=float(globals().get('W_CODO', 0.05)))
        prior_arm[lado] = (q, 2 * math.atan2(qx.x, qx.w)); errs[f"mano{lado}{f}"] = round(err, 3)
        rot[up] = tuple(q.to_euler('XYZ', Euler(ROT0[up], 'XYZ'))); rot[el] = (2 * math.atan2(qx.x, qx.w), 0, 0)
    SOL.append((f, dict(rot=rot, loc=loc["Hips_alfred"])))
print("errores IK (m): max %.3f" % max(errs.values()), {k: v for k, v in errs.items() if v > 0.05})

# ---------- frames intermedios: arcos de brazo por cuaternion, resto lineal ----------
def estado(f):
    for (fa, A), (fb, B) in zip(SOL, SOL[1:]):
        if fa <= f <= fb:
            t = 0.0 if fa == fb else (f - fa) / float(fb - fa); rot = {}
            for b in BONES:
                ra = A["rot"][b]; rb = tuple(cerca(ra[i], B["rot"][b][i]) for i in range(3))
                if b in ARM:
                    qa = Euler(ra, 'XYZ').to_quaternion(); qb = Euler(B["rot"][b], 'XYZ').to_quaternion(); qb = qb if qa.dot(qb) >= 0 else -qb
                    rot[b] = tuple(qa.slerp(qb, t).to_euler('XYZ', Euler(ra, 'XYZ')))
                else: rot[b] = tuple(ra[i] + (rb[i] - ra[i]) * t for i in range(3))
            la, lb = A["loc"], B["loc"]; return rot, tuple(la[i] + (lb[i] - la[i]) * t for i in range(3))
    return SOL[-1][1]["rot"], SOL[-1][1]["loc"]

# ---------- claves ----------
act = AA.animation_data.action
for fc in [fc for l in act.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]:
    for i in range(len(fc.keyframe_points) - 1, -1, -1):
        if fc.keyframe_points[i].co.x >= T0 - 1: fc.keyframe_points.remove(fc.keyframe_points[i])            # idempotente (incluye el ancla de T0-1)
hips = AA.pose.bones["Hips_alfred"]
def key_frame(f, rot, hl):
    hips.location = hl
    for ax in range(3): hips.keyframe_insert("location", index=ax, frame=f, group="Hips_alfred")
    for b in BONES:
        pb = AA.pose.bones[b]; pb.rotation_euler = rot[b]
        for ax in range(3): pb.keyframe_insert("rotation_euler", index=ax, frame=f, group=b)
key_frame(T0 - 1, ROT0, LOC0)                                                  # ancla: Alfred mantiene la pose de f470 hasta f493
for f in range(T0, T0 + 31):
    rot, hl = estado(f); key_frame(f, rot, hl)
for fc in [fc for l in act.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]:
    for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
sc.frame_end = max(sc.frame_end, T0 + 30)
sc.frame_set(T0 - 1)
print("Alfred se levanta cojeando: f%d-%d (manos plantadas hasta f%d, de pie con el peso en la pierna izquierda en f%d); se queda asi" % (T0, T0 + 30, T0 + 11, T0 + 30))
