# -*- coding: utf-8 -*-
"""Parte 7: a partir de f420 Alfred (sentado, girado 180 grados) coge con su MANO DERECHA el cuello del pollo (que esta a su derecha, a ~1.3 m) y se lo lanza al creeper a la cara.
- f420-427: se inclina hacia el pollo (la inclinacion y el giro del torso los resuelve una busqueda con el IK de `docs/parte3/ik_brazos.py` para que la muñeca llegue al cuello del pollo), mirandolo; la mano izquierda se apoya en el suelo.
- f427: agarra el cuello (el pollo pasa a seguir la mano: `pollo_atrapado_parte7.py`). f428-434: lo levanta y toma impulso (brazo atras y arriba, torso girado). f434-437: lanzamiento (aceleracion, 3 f) hacia el creeper; SUELTA en f437.
- f437-440: la mano sigue de largo (follow-through); f440-446: REFLEJO: se cubre la cara con los dos antebrazos (torso encogido, cabeza gacha) con ELASTIC IN-OUT, y asi sigue hasta f481; f481-489: PRIMERA REACCION, levanta la cabeza para ver que no paso nada (torso mas erguido, cuello arriba, los antebrazos bajan de la cara al pecho) y mantiene hasta f493; en f494 empieza a levantarse (`alfred_se_levanta_cojeando_parte7.py`). Mira al pollo hasta el lanzamiento.
Parte de la pose de f419 (la ultima de `alfred_ve_creeper_parte7.py`) y NO toca nada anterior a f420. Se ejecuta dentro de Blender: exec(open(RUTA, encoding='utf-8').read()). Idempotente (borra sus claves >= f420, tambien las de levantarse: volver a ejecutar `alfred_se_levanta_cojeando_parte7.py` despues)."""
import bpy, math
from mathutils import Euler, Quaternion, Vector

T_ST, T_GRAB, T_WIND, T_REL, T_OVER, T_RELAX, FIN = 420, 427, 434, 437, 440, 446, 493                     # T_RELAX = f446: ya tiene los brazos cubriendo la cara; los mantiene hasta f481, luego levanta la cabeza (f481-489) y mantiene esa pose hasta FIN (f493, el frame anterior a levantarse en f494)
Dg = math.radians
sc = bpy.context.scene
exec(open(r'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/parte3/ik_brazos.py', encoding='utf-8').read(), globals())     # fk, mundo, resolver, AA, OO
EA = OO; CHA = bpy.data.objects['Armature_chicken_1']
ss = lambda x: 0.0 if x <= 0 else 1.0 if x >= 1 else x * x * (3 - 2 * x)
def qint(q0, q1, u):
    d = q0.rotation_difference(q1); ax, an = d.to_axis_angle(); return q0 @ Quaternion(ax, an * u) if an > 1e-9 else q0.copy()
def ela(t):                                                                      # ELASTIC in-out (como creeper_susto_y_huida.py)
    if t <= 0: return 0.0
    if t >= 1: return 1.0
    c5 = (2 * math.pi) / 4.5
    return -(2 ** (20 * t - 10) * math.sin((20 * t - 11.125) * c5)) / 2 if t < 0.5 else (2 ** (-20 * t + 10) * math.sin((20 * t - 11.125) * c5)) / 2 + 1
cerca = lambda ref, v: v + 2 * math.pi * round((ref - v) / (2 * math.pi))

# ---------- limpiar claves >= f420 y leer la pose de f419 ----------
act = AA.animation_data.action
for fc in [fc for l in act.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]:
    for i in range(len(fc.keyframe_points) - 1, -1, -1):
        if fc.keyframe_points[i].co.x >= T_ST: fc.keyframe_points.remove(fc.keyframe_points[i])
sc.frame_set(T_GRAB); bpy.context.view_layer.update()
neck_h = CHA.matrix_world @ CHA.pose.bones['Neck_M_chicken_1'].head; neck_t = CHA.matrix_world @ CHA.pose.bones['Neck_M_chicken_1'].tail
NECK_PT = neck_h + (neck_t - neck_h) * 0.6                                  # donde agarra el cuello
sc.frame_set(T_ST - 1); bpy.context.view_layer.update()
BON = ["Hips_alfred", "Spine_alfred", "Spine1_alfred", "Spine2_alfred", "Neck_alfred", "RightUpArm_alfred", "Rightelbow_alfred", "LeftUpArm_alfred", "Leftelbow_alfred", "RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred"]
PB = {n: AA.pose.bones[n] for n in BON}
R0 = {n: tuple(PB[n].rotation_euler) for n in BON}; H0 = tuple(PB["Hips_alfred"].location); rt = tuple(EA.location); rz = EA.rotation_euler.z
R3 = Matrix.Rotation(rz, 3, 'Z'); FWD, DER, IZQ, ARR = R3 @ Vector((0, 1, 0)), R3 @ Vector((1, 0, 0)), R3 @ Vector((-1, 0, 0)), Vector((0, 0, 1))
Mw = mundo(rt, rz); SP = ("Spine_alfred", "Spine1_alfred", "Spine2_alfred")
A0 = {l: (Euler(R0[l + "UpArm_alfred"], 'XYZ').to_quaternion(), Euler(R0[l + "elbow_alfred"], 'XYZ').to_quaternion()) for l in ("Right", "Left")}
def torso(lx, ty, sz, neck=None):
    r = {n: R0[n] for n in BON}
    for s in SP: r[s] = (Dg(lx), Dg(ty), Dg(sz))
    if neck: r["Neck_alfred"] = neck
    return r
def brazo(l, rot, tgt, prev, iters=4000, semilla=3, hint=None):
    M = fk(rot, {"Hips_alfred": H0}); q0, qe0 = prev; x0 = 2 * math.atan2(qe0.x, qe0.w)
    q, qe, err, _ = resolver(l, M["Spine2_alfred"], Mw, tgt, codo_hint=hint, inicio=(q0, x0), iters=iters, semilla=semilla); return (q, qe), err

# ---------- 1) inclinacion del torso para llegar al cuello del pollo (busqueda con el IK) ----------
mejor = None
for lx in (15, 25, 35):
    for ty in (-30, -15, 0, 15, 30):
        for sz in (-15, 0, 15):
            rot = torso(lx, ty, sz); M = fk(rot, {"Hips_alfred": H0}); sh = Mw @ M["Spine2_alfred"].translation
            _, err = brazo("Right", rot, NECK_PT, A0["Right"], iters=1200, hint=(sh + NECK_PT) / 2 + DER * 0.15 + ARR * 0.10)
            costo = err + 0.0004 * (lx + abs(ty) + abs(sz))
            if mejor is None or costo < mejor[0]: mejor = (costo, lx, ty, sz, err)
_, LX, TY, SZ, err_busca = mejor
print("torso para agarrar: inclinacion %d, giro %d, lateral %d grados por segmento de columna | error de muneca %.3f m (cuello del pollo en %s)" % (LX, TY, SZ, err_busca, [round(c, 2) for c in NECK_PT]))

# ---------- 2) poses clave: (frame, torso, cuello, brazo der, brazo izq) ----------
def pose(frame, rot, tgt_der, tgt_izq, prev_d, prev_i, semilla=3, hint_d=None):
    rd, e1 = brazo("Right", rot, tgt_der, prev_d, hint=hint_d, semilla=semilla); ri, e2 = brazo("Left", rot, tgt_izq, prev_i, semilla=semilla + 1, hint=(tgt_izq + (Mw @ fk(rot, {"Hips_alfred": H0})["Spine2_alfred"].translation)) / 2 + IZQ * 0.10)
    print("  f%d: error de muneca der %.3f izq %.3f m" % (frame, e1, e2)); return dict(f=frame, rot=rot, R=rd, L=ri)
def hombro(rot): return Mw @ fk(rot, {"Hips_alfred": H0})["Spine2_alfred"].translation
apoyo = lambda: Vector(rt) + IZQ * 0.45 - FWD * 0.15 + ARR * 0.05            # mano izquierda en el suelo (para no caerse al inclinarse)
P0 = dict(f=T_ST - 1, rot=R0, R=A0["Right"], L=A0["Left"])
Rg = torso(LX, TY, SZ, (Dg(18), Dg(-45), 0.0)); Pg = pose(T_GRAB, Rg, NECK_PT, apoyo(), A0["Right"], A0["Left"], hint_d=(hombro(Rg) + NECK_PT) / 2 + DER * 0.15 + ARR * 0.10)
Rw = torso(8, TY, 0, (Dg(10), Dg(-45), 0.0)); sw = hombro(Rw); Pw = pose(T_WIND, Rw, sw + DER * 0.45 + ARR * 0.55 - FWD * 0.45, apoyo(), Pg["R"], Pg["L"], hint_d=sw + DER * 0.55 + ARR * 0.20 - FWD * 0.2)
Rt = torso(20, -0.5 * TY, 0, (Dg(-4), 0.0, 0.0)); st = hombro(Rt); Pt = pose(T_REL, Rt, st + FWD * 0.85 + ARR * 0.30, apoyo(), Pw["R"], Pw["L"], hint_d=st + FWD * 0.4 + DER * 0.1 - ARR * 0.1)
Ro = torso(24, -0.5 * TY, 0, (Dg(-2), 0.0, 0.0)); so = hombro(Ro); Po = pose(T_OVER, Ro, so + FWD * 1.0 + ARR * 0.05, apoyo(), Pt["R"], Pt["L"], hint_d=so + FWD * 0.5 - ARR * 0.15)
Rr = torso(18, 0, 0, (Dg(14), 0.0, 0.0)); Mr = fk(Rr, {"Hips_alfred": H0}); srr = hombro(Rr)                  # cubrirse la cara: torso encogido y cabeza gacha
N3 = Mr["Neck_alfred"].to_3x3(); Mw3 = Mw.to_3x3(); HC = Mw @ (Mr["Neck_alfred"] @ Vector((0, 0.265, 0.025)))                      # centro de la cabeza (cubo de ~0.57-0.6 m: de 0 a 0.56 a lo largo del cuello y +-0.28 de lado)
FD = (Mw3 @ (N3 @ Vector((0, -0.089, 0.996)))).normalized(); UD = (Mw3 @ (N3 @ Vector((0, 1, 0)))).normalized()                    # hacia donde mira la cara (eje local +z del hueso del cuello) y hacia arriba de la cabeza
LX = Mw3 @ (N3 @ Vector((1, 0, 0))); RD = (LX if LX.dot(DER) > 0 else -LX).normalized()                                              # lado derecho de Alfred
CARA_D = float(globals().get('CARA_D', 0.76))                                      # muneca (cola del hueso) a CARA_D del centro de la cabeza: la cara esta a ~0.30 y la mano (malla) termina ~0.25 antes de la cola
LAT = float(globals().get('LAT', 0.12))                                             # separacion lateral de las munecas respecto al centro de la cara
SUBE = float(globals().get('SUBE', 0.24))                                          # la malla de la mano termina ~0.33 antes de la cola del hueso (hacia abajo): la muneca va mas arriba para que la mano cubra el centro de la cara
Pr = pose(T_RELAX, Rr, HC + FD * CARA_D + RD * LAT + UD * SUBE, HC + FD * CARA_D - RD * LAT + UD * SUBE, Po["R"], Po["L"], hint_d=(srr + HC) / 2 + DER * 0.30 - ARR * 0.15)
# primera reaccion antes de levantarse: levanta la cabeza para ver que no paso nada (f481-489, suave): el torso se endereza (10 grados), el cuello sube (X -6) y los antebrazos bajan de la cara al pecho; mantiene hasta FIN
T_PEEK0, T_PEEK1 = int(globals().get('T_PEEK0', 481)), int(globals().get('T_PEEK0', 481)) + 8
Rk = torso(10, 0, 0, (Dg(-6), 0.0, 0.0)); Mk = fk(Rk, {"Hips_alfred": H0}); srk = hombro(Rk); N3k = Mk["Neck_alfred"].to_3x3(); HCk = Mw @ (Mk["Neck_alfred"] @ Vector((0, 0.265, 0.025)))
FDk = (Mw3 @ (N3k @ Vector((0, -0.089, 0.996)))).normalized(); UDk = (Mw3 @ (N3k @ Vector((0, 1, 0)))).normalized(); LXk = Mw3 @ (N3k @ Vector((1, 0, 0))); RDk = (LXk if LXk.dot(DER) > 0 else -LXk).normalized()
BAJA = float(globals().get('BAJA', 0.55))                                           # los antebrazos bajan hasta ~BAJA m por debajo del centro de la cabeza (pecho)
Pk = pose(T_PEEK1, Rk, HCk + FDk * 0.45 + RDk * 0.22 - UDk * BAJA, HCk + FDk * 0.45 - RDk * 0.22 - UDk * BAJA, Pr["R"], Pr["L"], hint_d=(srk + HCk) / 2 + DER * 0.30 - ARR * 0.20)
CLAVES = [P0, Pg, dict(Pg, f=T_GRAB + 1), Pw, Pt, Po, Pr, dict(Pr, f=T_PEEK0), Pk, dict(Pk, f=FIN)]
ENT = {T_GRAB: lambda t: ss(t), T_GRAB + 1: lambda t: ss(t), T_WIND: lambda t: ss(t), T_REL: lambda t: t * t * t, T_OVER: lambda t: ss(t), T_RELAX: lambda t: ss(t)}
EASE = {T_ST - 1: lambda t: ss(t) ** 0.7, T_GRAB: lambda t: t, T_GRAB + 1: lambda t: ss(t), T_WIND: lambda t: t * t, T_REL: lambda t: ss(t), T_OVER: ela, T_RELAX: lambda t: t, T_PEEK0: lambda t: ss(t), T_PEEK1: lambda t: t}   # easing del tramo que EMPIEZA en cada clave

# ---------- 3) claves por frame ----------
def key_rot(pb, f, v):
    pb.rotation_euler = v
    for ax in range(3): pb.keyframe_insert("rotation_euler", index=ax, frame=f, group=pb.name)
prev = {}
def ec(n, q, ref):
    e = q.to_euler('XYZ', prev.get(n, Euler(ref, 'XYZ'))); prev[n] = e; return tuple(e)
for n in BON: key_rot(PB[n], T_ST - 1, R0[n])
for f in range(T_ST, FIN + 1):
    k = max(i for i in range(len(CLAVES)) if CLAVES[i]["f"] <= f); k2 = min(k + 1, len(CLAVES) - 1); a, b = CLAVES[k], CLAVES[k2]
    t = 0.0 if a["f"] == b["f"] else (f - a["f"]) / float(b["f"] - a["f"]); u = EASE.get(a["f"], lambda x: ss(x))(t) if a["f"] != b["f"] else 1.0
    for n in BON:
        if "Arm" in n or "elbow" in n: continue
        ea, eb = a["rot"][n], b["rot"][n]; key_rot(PB[n], f, tuple(ea[c] + (cerca(ea[c], eb[c]) - ea[c]) * u for c in range(3)))
    for l in ("Right", "Left"):
        (qa, ea_), (qb, eb_) = a["R" if l == "Right" else "L"], b["R" if l == "Right" else "L"]
        qq = qint(qa, qb if qa.dot(qb) >= 0 else -qb, u); ee = qint(ea_, eb_ if ea_.dot(eb_) >= 0 else -eb_, u)
        key_rot(PB[l + "UpArm_alfred"], f, ec(l + "u", qq, R0[l + "UpArm_alfred"])); key_rot(PB[l + "elbow_alfred"], f, ec(l + "e", ee, R0[l + "elbow_alfred"]))
for fc in [fc for l in act.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]:
    for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
sc.frame_end = max(sc.frame_end, FIN)
sc.frame_set(T_ST - 1)
print("Alfred tira al pollo: se inclina f%d-%d, agarra f%d, toma impulso f%d-%d, lanza f%d-%d (suelta f%d), relaja f%d-%d, fin f%d" % (T_ST, T_GRAB, T_GRAB, T_GRAB + 1, T_WIND, T_WIND, T_REL, T_REL, T_OVER, T_RELAX, FIN))
