# -*- coding: utf-8 -*-
"""Parte 6: Jerry (de pie, f555+) sacude la cabeza de +30 a -30 en Y (4 sacudidas rapidas, como un perro): se le cae el `sombrero_jerry`; se detiene, lo recoge con la pata delantera IZQUIERDA y se lo vuelve a poner (f555-636).
Se ejecuta DENTRO de Blender con exec (escena viva de la parte 6). Que hace:
 - `scull_1` Y: +30/-30 con extremos en f557, 559, 562, 564, 567, 569, 572, 574 (2-3 f cada medio giro) y se detiene en f576-578; las orejas aletean.
 - El sombrero original (malla con piel, 2 modificadores Armature) se oculta de f554 a f616 y lo sustituye `sombrero_jerry_libre` (copia rigida horneada en la pose f554) animada por matrices: sigue al hueso `sombrero` hasta que sale despedido en f564, vuelo balistico con giro
   de 360 grados (14 f), cae en el pasto, 2 rebotes, queda en el suelo; f594 la pata IZQUIERDA lo engancha (IK de la pata, 6 grados de libertad) y lo sube a la cabeza (f606), se coloca (f606-614: suavizado a la pose original) y vuelve a aparecer el original en f617.
 - Mientras tanto la cabeza mira hacia abajo/izquierda hacia el sombrero (f578-598) y vuelve a la normalidad antes de colocarlo.
Variables opcionales: ATERRIZA (x, y) del centro del sombrero en el suelo, SUELO (z del pasto)."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler, Quaternion

sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "scull_1" in o.pose.bones)
hat = bpy.data.objects["sombrero_jerry"]
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
FPS = 24.0; G = 7.0
SUELO = float(globals().get("SUELO", 14.0)); ATERRIZA = tuple(globals().get("ATERRIZA", (-95.78, -109.27)))

# ---------- 0) estado de pie en f554 ----------
sc.frame_set(554); bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
cur = {pb.name: [math.degrees(x) for x in pb.rotation_euler] for pb in arm.pose.bones}
MWa = arm.matrix_world.copy()
BW0 = MWa @ arm.pose.bones["sombrero"].matrix
# ---------- 1) copia rigida del sombrero horneada en f554 (coordenadas de mundo) ----------
ev = hat.evaluated_get(dg); me = ev.to_mesh(); bm = bmesh.new(); bm.from_mesh(me); ev.to_mesh_clear()
bm.transform(hat.matrix_world)
if "sombrero_jerry_libre" in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects["sombrero_jerry_libre"], do_unlink=True)
mesh = bpy.data.meshes.new("sombrero_jerry_libre"); bm.to_mesh(mesh); bm.free()
for m in hat.data.materials: mesh.materials.append(m)
H = bpy.data.objects.new("sombrero_jerry_libre", mesh)
for c in hat.users_collection: c.objects.link(H)
H.rotation_mode = 'QUATERNION'
pts = [v.co.copy() for v in mesh.vertices]
C_BASE = sum(pts, Vector()) / len(pts); ZMIN = min(p.z for p in pts); ZMAX = max(p.z for p in pts); print("sombrero: centro", [round(x, 3) for x in C_BASE], "z", round(ZMIN, 3), round(ZMAX, 3))
Q_ID = Quaternion((1, 0, 0, 0))

# ---------- 2) cinematica de la pata delantera izquierda ----------
def basis(n, a): pb = arm.pose.bones[n]; return Matrix.LocRotScale(pb.location, Euler(tuple(math.radians(x) for x in a[n]), 'XYZ'), pb.scale)
def fk(a, names):
    out = {}
    def M(n):
        if n in out: return out[n]
        pb = arm.pose.bones[n]; rest = pb.bone.matrix_local
        out[n] = (rest @ basis(n, a)) if pb.parent is None else (M(pb.parent.name) @ (pb.parent.bone.matrix_local.inverted() @ rest) @ basis(n, a))
        return out[n]
    for n in names: M(n)
    return out
LEG = ["front_shoulder.L", "front_thigh.L", "front_shin.L", "front_foot.L", "front_toe.L"]
def toe(a):
    m = fk(a, LEG); return MWa @ (m["front_toe.L"] @ Vector((0, arm.pose.bones["front_toe.L"].bone.length, 0)))
def resolver(objetivo, prior, seed=1, intentos=12):
    """prior: dict hueso -> [x,y,z] grados; libres: hombro xyz, muslo x, espinilla x, pie x (en radianes internamente)"""
    rng = random.Random(seed); objetivo = Vector(objetivo)
    p0 = [math.radians(v) for v in prior["front_shoulder.L"]] + [math.radians(prior["front_thigh.L"][0]), math.radians(prior["front_shin.L"][0]), math.radians(prior["front_foot.L"][0])]
    def ang(p):
        a = dict(cur); a["front_shoulder.L"] = [math.degrees(p[0]), math.degrees(p[1]), math.degrees(p[2])]
        for i, n in enumerate(("front_thigh.L", "front_shin.L", "front_foot.L")): v = list(cur[n]); v[0] = math.degrees(p[3 + i]); a[n] = v
        return a
    def coste(p): return (toe(ang(p)) - objetivo).length + 0.01 * sum(abs(p[i] - p0[i]) for i in range(6))
    mejor = None
    arr = [list(p0)] + [[p0[0] + rng.uniform(-1.2, 1.2), p0[1] + rng.uniform(-0.6, 0.6), p0[2] + rng.uniform(-0.6, 0.6), p0[3] + rng.uniform(-1.5, 1.5), p0[4] + rng.uniform(-1.5, 1.5), p0[5] + rng.uniform(-1, 1)] for _ in range(intentos)]
    for par in arr:
        c = coste(par); paso = 0.35
        for it in range(600):
            cand = [v + rng.gauss(0, paso) for v in par]; cc = coste(cand)
            if cc < c: par, c = cand, cc
            elif it % 50 == 49: paso = max(paso * 0.7, 0.002)
        if mejor is None or c < mejor[0]: mejor = (c, par)
    a = ang(mejor[1]); return {n: list(a[n]) for n in LEG[:4]}, (toe(a) - objetivo).length

PIE = {n: list(cur[n]) for n in LEG[:4]}
HC = Vector(C_BASE)                                                           # centro del sombrero puesto (cabeza neutra)
LAND = Vector((ATERRIZA[0], ATERRIZA[1], SUELO + (C_BASE.z - ZMIN)))           # centro del sombrero tirado (apoyado sobre el ala)
D = Vector((0.0, 0.06, 0.0475))                                                # centro del sombrero respecto a la punta de la pata al llevarlo
DT = int(globals().get("DT", 23))                                              # retraso de todo lo posterior a la sacudida respecto a la version corta (la sacudida ahora dura mas)
WP = [(578 + DT, None), (588 + DT, (LAND.x - 0.02, LAND.y - 0.05, SUELO + 0.22)), (594 + DT, (LAND.x, LAND.y - 0.06, SUELO + 0.05)), (600 + DT, (LAND.x + 0.06, LAND.y - 0.11, SUELO + 0.40)),
      (606 + DT, (HC.x, HC.y - 0.06 + 0.0, HC.z - D.z - 0.07)), (613 + DT, (HC.x, HC.y - 0.06, HC.z - D.z - 0.07)), (624 + DT, None)]
SOL = []; prev = PIE
for f, objetivo in WP:
    if objetivo is None: SOL.append((f, PIE)); prev = PIE; continue
    a, err = resolver(objetivo, prev, seed=f); SOL.append((f, a)); prev = a; print("pata f", f, "error", round(err, 3))
def leg_en(f):
    if f <= SOL[0][0]: return SOL[0][1]
    for (fa, A), (fb, B) in zip(SOL, SOL[1:]):
        if fa <= f <= fb:
            t = ss((f - fa) / (fb - fa)); return {n: [A[n][i] + (B[n][i] - A[n][i]) * t for i in range(3)] for n in LEG[:4]}
    return SOL[-1][1]
def toe_en(f): a = dict(cur); a.update(leg_en(f)); return toe(a)

# ---------- 3) claves de los huesos ----------
def clavar(pb, f, e, grupo=None):
    pb.rotation_euler = [math.radians(x) for x in e]
    for ax in range(3): pb.keyframe_insert("rotation_euler", index=ax, frame=f, group=grupo or pb.name)
EXT = globals().get("EXT") or [(555, 0), (559, 60), (564, -50), (568, 60), (574, -50), (578, 60), (583, -50), (587, 60), (593, -50), (597, 15), (601, 0)]    # +60 / -50 grados, 4 oscilaciones de ~10 f
def sacudida(f):
    for (fa, va), (fb, vb) in zip(EXT, EXT[1:]):
        if fa <= f <= fb: return va + (vb - va) * ss((f - fa) / (fb - fa))
    return 0.0
FIN_SAC = EXT[-1][0]
def mirada(f):                                   # (X, Z) de scull_1 mirando hacia abajo y a la izquierda (hacia el sombrero) y volviendo
    t = ss((f - (578 + DT)) / 10.0) * (1 - ss((f - (598 + DT)) / 12.0)); return 24.0 * t, -18.0 * t
sk = arm.pose.bones["scull_1"]; n = 0
for f in range(554, 637 + DT):
    x, z = mirada(f); clavar(sk, f, [cur["scull_1"][0] + x, sacudida(f) if f <= FIN_SAC else 0.0, cur["scull_1"][2] + z]); n += 3
for b, sg in (("ear.L", 1), ("ear.R", -1)):
    pb = arm.pose.bones[b]
    for f in range(554, FIN_SAC + 4):
        env = ss((f - 555) / 2.0) * (1 - ss((f - (FIN_SAC - 8)) / 8.0)); osc = math.sin(2 * math.pi * (f - 555) / 7.5 + (0 if sg > 0 else 0.5))
        clavar(pb, f, [cur[b][0], cur[b][1], cur[b][2] + 28 * env * osc]); n += 3
pl = {nm: arm.pose.bones[nm] for nm in LEG[:4]}
for f in range(578 + DT, 625 + DT):
    a = leg_en(f)
    for nm in LEG[:4]: clavar(pl[nm], f, a[nm]); n += 3
# ---------- 4) animacion del sombrero ----------
DESPEDIDO, NV, NB = int(globals().get("DESPEDIDO", 583)), 14, 16                 # sale despedido en el 6.o extremo de la sacudida
fe = DESPEDIDO + NV
def matriz_sombrero_puesto(f):                    # sigue al hueso `sombrero`: M(f) = BW(f) @ BW0^-1 (necesita la escena evaluada en f)
    sc.frame_set(f); return (MWa @ arm.pose.bones["sombrero"].matrix) @ BW0.inverted()
poses = {}
for f in range(554, DESPEDIDO + 1): poses[f] = matriz_sombrero_puesto(f)
def descomponer(M): l, q, s = M.decompose(); return l, q
def poner(f, M):
    l, q = descomponer(M); H.location = l; H.rotation_quaternion = q
    H.keyframe_insert("location", frame=f); H.keyframe_insert("rotation_quaternion", frame=f)
def M_de(c, q): return Matrix.Translation(c) @ q.to_matrix().to_4x4() @ Matrix.Translation(-C_BASE)
H.location = (0, 0, 0); H.rotation_quaternion = Q_ID; H.keyframe_insert("location", frame=553); H.keyframe_insert("rotation_quaternion", frame=553)
for f in range(554, DESPEDIDO + 1): poner(f, poses[f])
M0 = poses[DESPEDIDO]; c0 = M0 @ C_BASE; q0 = M0.to_quaternion(); yaw = math.radians(32)
qf = Quaternion((0, 0, 1), yaw); eje = Vector((1.0, 0.4, 0.0)).normalized()
tA = NV / FPS; v0 = Vector(((LAND.x - c0.x) / tA, (LAND.y - c0.y) / tA, (LAND.z - c0.z) / tA + 0.5 * G * tA))
for i in range(1, NV + 1):
    t = i / FPS; c = c0 + v0 * t - Vector((0, 0, 0.5 * G * t * t)); s = ss(i / NV)
    q = Quaternion(eje, math.radians(360 * i / NV)) @ q0.slerp(qf, s); poner(DESPEDIDO + i, M_de(c, q))
for (alt, nn, dx) in ((0.06, 5, 0.03), (0.02, 3, 0.02)):
    base = fe if alt == 0.06 else fe + 5
    for i in range(1, nn + 1):
        u = i / nn; poner(base + i, M_de(LAND + Vector((dx * u, 0, alt * 4 * u * (1 - u))), qf))
f_quieto = fe + 8
poner(f_quieto, M_de(LAND, qf)); poner(594 + DT, M_de(LAND, qf))
for f in range(595 + DT, 607 + DT):                 # la pata lo lleva: centro = punta + D
    c = toe_en(f) + D; t = ss((f - (600 + DT)) / 6.0); poner(f, M_de(c, Quaternion(qf).slerp(Q_ID, t)))
c_sale = toe_en(606 + DT) + D
for f in range(607 + DT, 615 + DT):                 # se coloca sobre la cabeza
    t = ss((f - (606 + DT)) / 8.0); c = c_sale.lerp(HC, t); poner(f, M_de(c, Q_ID))
poner(615 + DT, Matrix.Identity(4)); poner(616 + DT, Matrix.Identity(4))
for fc in H.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
    for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
# visibilidad: el original se oculta mientras el rigido lo sustituye
def vis(o, f, oculto):
    o.hide_viewport = oculto; o.hide_render = oculto; o.keyframe_insert("hide_viewport", frame=f); o.keyframe_insert("hide_render", frame=f)
vis(hat, 553, False); vis(hat, 554, True); vis(hat, 616 + DT, True); vis(hat, 617 + DT, False)
vis(H, 553, True); vis(H, 554, False); vis(H, 616 + DT, False); vis(H, 617 + DT, True)
for o in (hat, H):
    for fc in o.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT' if fc.data_path.startswith("hide") else kp.interpolation
for fc in arm.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
    for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'
# ---------- verificacion ----------
res = {}
for f in (554, DESPEDIDO, DESPEDIDO + 7, DESPEDIDO + 14, 594 + DT, 600 + DT, 606 + DT, 612 + DT, 617 + DT, 636 + DT):
    sc.frame_set(f); dg2 = bpy.context.evaluated_depsgraph_get(); o = H if f < 617 + DT else hat
    ev2 = o.evaluated_get(dg2); me2 = ev2.to_mesh(); pp = [o.matrix_world @ v.co for v in me2.vertices]; ev2.to_mesh_clear()
    c = sum(pp, Vector()) / len(pp); res[f] = {"centro": [round(x, 2) for x in c], "z_min": round(min(p.z for p in pp), 3), "punta_pata": [round(x, 2) for x in (MWa @ arm.pose.bones["front_toe.L"].tail)]}
sc.frame_set(120)
print(res)
