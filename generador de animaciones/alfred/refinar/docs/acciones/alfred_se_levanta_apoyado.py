# -*- coding: utf-8 -*-
"""Parte 6: Alfred (sentado, dormido) se levanta apoyando la mano IZQUIERDA en la pared de madera y la DERECHA en el pasto, y se impulsa hasta ponerse de pie (f284-348).
Se ejecuta DENTRO de Blender con exec (necesita `bpy.app.driver_namespace["IK"]` = modulo docs/parte3/ik_brazos.py ya ejecutado y `ALF_POSE0` = pose actual {"rot", "loc"} por hueso).
Variables opcionales: TIP_R, TIP_L (punta real de la mano en mundo), FZ (z del dedo del pie plantado), TL (lista de poses y frames).
Poses: K0 sentado, K1 manos apoyadas, K2 impulso (cadera sube, torso inclinado 28 grados), K3 casi de pie, K4 de pie con los brazos soltando, K5 de pie con los brazos colgando.
Pies plantados por IK de pierna (UpLeg xyz + knee X), manos por `resolver` de ik_brazos (la malla de la mano termina 0.20-0.28 antes de la cola del hueso y mide ~0.25 de grosor: los objetivos son de la MALLA)."""
import bpy, math, random
from mathutils import Vector, Matrix, Euler, Quaternion

ns = bpy.app.driver_namespace; g = ns["IK"]; fk = g["fk"]; REST = g["REST"]; AA = g["AA"]; Mw = AA.matrix_world.copy(); sc = bpy.context.scene
P0 = ns["ALF_POSE0"]; ROT0 = {k: tuple(v) for k, v in P0["rot"].items()}; LOC0 = {k: tuple(v) for k, v in P0["loc"].items()}


def mat(rot, loc): return fk(rot, loc)
def pt(M, n, e="h"): return Mw @ (M[n].translation if e == "h" else M[n] @ Vector((0, REST[n][2], 0)))


def hips_loc(rot, loc, objetivo):
    base = dict(loc); base["Hips_alfred"] = (0, 0, 0); p0 = pt(mat(rot, base), "Hips_alfred"); cols = []
    for ax in range(3):
        v = [0, 0, 0]; v[ax] = 1.0; b2 = dict(loc); b2["Hips_alfred"] = tuple(v); cols.append(pt(mat(rot, b2), "Hips_alfred") - p0)
    A = Matrix(((cols[0].x, cols[1].x, cols[2].x), (cols[0].y, cols[1].y, cols[2].y), (cols[0].z, cols[1].z, cols[2].z)))
    s = A.inverted() @ (Vector(objetivo) - p0); return (s.x, s.y, s.z)


def pata(lado, rot, loc, objetivo, prior, intentos=14, seed=2):
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
        for it in range(500):
            cand = [v + rng.gauss(0, paso) for v in par]; cc = coste(cand)
            if cc < c: par, c = cand, cc
            elif it % 40 == 39: paso = max(paso * 0.7, 0.002)
        if mejor is None or c < mejor[0]: mejor = (c, par)
    p = mejor[1]; r = dict(rot); r[up] = (p[0], p[1], p[2]); r[kn] = (p[3], 0, 0)
    return p, (pt(mat(r, loc), kn, "t") - objetivo).length


FZ = float(globals().get("FZ", 12.921)); FOOT = {"Right": Vector((-95.932, -108.514, FZ)), "Left": Vector((-95.939, -108.453, FZ))}
TIP = {"Right": Vector(globals().get("TIP_R", (-95.86, -109.16, 14.24))), "Left": Vector(globals().get("TIP_L", (-95.78, -108.265, 14.35)))}
OFF = {"Right": 0.278, "Left": 0.204}; DIR = {"Right": Vector((0.05, -0.98, -0.22)), "Left": Vector((0.31, 0.38, 0.87)).normalized()}
HINT = {"Right": Vector(globals().get("HINT_R", (-0.10, -0.05, 0.38))), "Left": Vector(globals().get("HINT_L", (-0.28, -0.02, -0.22)))}      # codo derecho alto: el antebrazo pasa por encima del borde del pozo
def euler_de(q, prev): return q.to_euler('XYZ', Euler(prev, 'XYZ'))


def pose_k(hips_w, lean_deg, pies_z, manos, dz_der=0.0):
    rot = dict(ROT0); loc = dict(LOC0)
    for i, n in enumerate(("Spine_alfred", "Spine1_alfred", "Spine2_alfred")):
        e = list(ROT0[n]); e[0] = math.radians((0.3, 0.3, 0.4)[i] * lean_deg); rot[n] = tuple(e)
    loc["Hips_alfred"] = hips_loc(rot, loc, hips_w); res = {}
    for lado in ("Right", "Left"):
        ob = Vector((FOOT[lado].x, FOOT[lado].y, pies_z)); p, err = pata(lado, rot, loc, ob, [*rot[f"{lado}UpLeg_alfred"], rot[f"{lado}knee_alfred"][0]])
        rot[f"{lado}UpLeg_alfred"] = (p[0], p[1], p[2]); rot[f"{lado}knee_alfred"] = (p[3], 0, 0); res[f"pie{lado}"] = round(err, 3)
    M = mat(rot, loc)
    for lado in ("Right", "Left"):
        up = f"{lado}UpArm_alfred"; el = f"{lado}elbow_alfred"
        if manos:
            sh = pt(M, up); q0 = Euler(ROT0[up], 'XYZ').to_quaternion(); d = DIR[lado]
            for _ in range(2):
                objetivo = TAIL_FIX[lado] if "TAIL_FIX" in globals() and lado in TAIL_FIX else TIP[lado] + (Vector((0, 0, dz_der)) if lado == "Right" else Vector()) + d * OFF[lado]
                q, qx, err, codo = g["resolver"](lado, M["Spine2_alfred"], Mw, objetivo, codo_hint=sh + HINT[lado], inicio=(q0, 0.0), iters=9000, semilla=3, w_codo=0.4)
                d = (objetivo - codo).normalized()
            rot[up] = tuple(euler_de(q, ROT0[up])); rot[el] = (euler_de(qx, ROT0[el])[0], 0, 0); res[f"mano{lado}"] = round(err, 3)
    res["rot"] = rot; res["loc_all"] = loc; return res


K = {"K0": {"rot": ROT0, "loc_all": LOC0}}
# VALORES DEL USUARIO para los brazos de apoyo (2026-10-08): K1 = cuerpo sentado (igual que K0) + estos brazos; el codo DERECHO no se dio y se resuelve para que la mano llegue al pasto.
# Las puntas de mano que resultan en K1 se mantienen plantadas (IK) mientras el cuerpo sube en K2 y K3.
APOYO = globals().get("APOYO") or {"RightUpArm_alfred": (-74.957, 359.92, 180.93), "LeftUpArm_alfred": (-66.48, 8.4593, -112.68), "Leftelbow_alfred": (4.0163, -21.138, 18.623)}
HIPS0 = pt(mat(ROT0, LOC0), "Hips_alfred")
K["K1"] = pose_k(tuple(HIPS0), 0.0, 12.90, False)
for b, v in APOYO.items():
    prev = ROT0[b]; K["K1"]["rot"][b] = tuple(Euler(tuple(math.radians(x) for x in v), 'XYZ').to_quaternion().to_euler('XYZ', Euler(prev, 'XYZ'))) if b.endswith("UpArm_alfred") else tuple(math.radians(x) for x in v)
# codo derecho: busca (x flexion, y, z) para que la punta de la MALLA toque el pasto
def cola_mano(rot, loc, lado):
    M = mat(rot, loc); el = f"{lado}elbow_alfred"; return pt(M, el), pt(M, el, "t")
rng = random.Random(4); objetivoD = TIP["Right"]; mejor = None
for it in range(1500):
    e = (rng.uniform(-2.6, 0.0), rng.uniform(-0.5, 0.5), rng.uniform(-0.7, 0.7)) if it < 800 else tuple(v + rng.gauss(0, 0.05) for v in mejor[1])
    r = dict(K["K1"]["rot"]); r["Rightelbow_alfred"] = e; h, t = cola_mano(r, K["K1"]["loc_all"], "Right"); d = (t - h).normalized(); punta = h + d * (REST["Rightelbow_alfred"][2] - OFF["Right"])
    c = (punta - objetivoD).length
    if mejor is None or c < mejor[0]: mejor = (c, e)
K["K1"]["rot"]["Rightelbow_alfred"] = mejor[1]; print("codo derecho (grados)", [round(math.degrees(x), 1) for x in mejor[1]], "error punta", round(mejor[0], 3))
H1, T1 = cola_mano(K["K1"]["rot"], K["K1"]["loc_all"], "Right"); H2, T2 = cola_mano(K["K1"]["rot"], K["K1"]["loc_all"], "Left")
TAIL_FIX = {"Right": T1, "Left": T2}; print("colas fijas", [round(x, 2) for x in T1], [round(x, 2) for x in T2])
DZ_D = globals().get("DZ_D") or (-0.60, -0.70)         # la malla de la mano derecha se separa del pasto al subir el cuerpo: se baja la cola un poco en K2 y K3 para mantener el contacto
TAIL_FIX = {"Right": T1 + Vector((0, 0, DZ_D[0])), "Left": T2}
K["K2"] = pose_k((-95.80, -108.52, 13.62), 28.0, FZ, True)
TAIL_FIX = {"Right": T1 + Vector((0, 0, DZ_D[1])), "Left": T2}
K["K3"] = pose_k((-95.86, -108.50, 13.84), 12.0, FZ, True)
K["K4"] = pose_k((-95.90, -108.484, 13.905), 3.0, FZ, False)
rot5 = dict(K["K4"]["rot"])
for i, n in enumerate(("Spine_alfred", "Spine1_alfred", "Spine2_alfred")): e = list(ROT0[n]); e[0] = math.radians((0.3, 0.3, 0.4)[i] * 1.5); rot5[n] = tuple(e)
K["K5"] = {"rot": rot5, "loc_all": dict(K["K4"]["loc_all"])}
ns["ALF_K"] = K
print({k: {a: b for a, b in K[k].items() if a.startswith(("pie", "mano"))} for k in ("K1", "K2", "K3", "K4")})

ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
TL = globals().get("TL") or [("K0", 284), ("K1", 296), ("K2", 311), ("K3", 324), ("K4", 337), ("K5", 348)]
ARM = ("RightUpArm_alfred", "LeftUpArm_alfred"); ELB = ("Rightelbow_alfred", "Leftelbow_alfred")
BONES = ["Spine_alfred", "Spine1_alfred", "Spine2_alfred", "RightUpLeg_alfred", "LeftUpLeg_alfred", "Rightknee_alfred", "Leftknee_alfred"] + list(ARM) + list(ELB)


def interp(f):
    for (ka, fa), (kb, fb) in zip(TL, TL[1:]):
        if fa <= f <= fb:
            t = ss((f - fa) / (fb - fa)); A, B = K[ka], K[kb]; rot = {}
            for b in BONES:
                ra, rb = A["rot"][b], B["rot"][b]
                if b in ARM:
                    qa = Euler(ra, 'XYZ').to_quaternion(); qb = Euler(rb, 'XYZ').to_quaternion(); rot[b] = tuple(qa.slerp(qb, t).to_euler('XYZ', Euler(ra, 'XYZ')))
                else: rot[b] = tuple(ra[i] + (rb[i] - ra[i]) * t for i in range(3))
            la, lb = A["loc_all"]["Hips_alfred"], B["loc_all"]["Hips_alfred"]
            return rot, tuple(la[i] + (lb[i] - la[i]) * t for i in range(3))
    return K["K5"]["rot"], K["K5"]["loc_all"]["Hips_alfred"]


hips = AA.pose.bones["Hips_alfred"]; neck = AA.pose.bones["Neck_alfred"]; n = 0
for f in range(TL[0][1], TL[-1][1] + 1):
    rot, hl = interp(f)
    lean = math.degrees(sum(rot[b][0] for b in ("Spine_alfred", "Spine1_alfred", "Spine2_alfred")) - sum(ROT0[b][0] for b in ("Spine_alfred", "Spine1_alfred", "Spine2_alfred")))
    hips.location = hl
    for ax in range(3): hips.keyframe_insert("location", index=ax, frame=f, group="Hips_alfred"); n += 1
    for b in BONES:
        pb = AA.pose.bones[b]; pb.rotation_euler = rot[b]
        for ax in range(3): pb.keyframe_insert("rotation_euler", index=ax, frame=f, group=b); n += 1
    e = list(neck.rotation_euler); e[0] = math.radians(-25.0 - 0.6 * lean); neck.rotation_euler = e                   # la cabeza se mantiene en alerta aunque el torso se incline
    neck.keyframe_insert("rotation_euler", index=0, frame=f, group="Neck_alfred"); n += 1
for fcv in AA.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
    for kp in fcv.keyframe_points: kp.interpolation = 'BEZIER'
ms = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.endswith("_alfred")]; res = {}
for f in (296, 311, 324, 348):
    sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); ymax = -999; zg = None; zmin = 99
    for o in ms:
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        for v in me.vertices:
            p = o.matrix_world @ v.co; ymax = max(ymax, p.y); zmin = min(zmin, p.z)
            if p.y < -109.06 and (zg is None or p.z < zg): zg = p.z
        ev.to_mesh_clear()
    res[f] = {"ymax(pared -108.0)": round(ymax, 3), "z_sobre_pasto(14.0)": round(zg, 3) if zg is not None else None, "zmin": round(zmin, 3)}
sc.frame_set(120)
print("claves", n, res)
