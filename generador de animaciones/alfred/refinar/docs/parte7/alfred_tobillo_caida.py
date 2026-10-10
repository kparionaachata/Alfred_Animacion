# -*- coding: utf-8 -*-
"""Seccion CAIDA de `alfred_corre_tobillo_parte7.py` (se ejecuta con exec dentro de el; usa EA, AA, PB, E, WC, D0, pts, H_LOC, NB, pose_run, key_rot, key_hips_loc, key_root).
En la ultima coordenada (f = E) el pie derecho se apoya mal y el tobillo se tuerce (la espinilla gira sobre su eje y se dobla hacia fuera); tropieza (brazos arriba), cae sentado, se queda con el
pie derecho cerca, la mano derecha en el tobillo y la izquierda apoyada en el suelo, y se sobaza el tobillo (la mano sube y baja por la espinilla) con la cabeza gacha y pequenos temblores.
Brazos: IK de `docs/parte3/ik_brazos.py`; resto: FK entre poses clave (suavizadas). Alfred mira a +y (rz 0): su derecha es +x."""
import math, os
from mathutils import Euler, Quaternion, Vector
exec(open(r'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/parte3/ik_brazos.py', encoding='utf-8').read(), globals())   # fk, mundo, cabeza_cola, resolver
Dg = math.radians
F_TW, F_GR, F_GR2, F_PUSH, F_MID2, F_SIT = E + 1, E + 5, E + 25, E + 28, E + 30, E + 32        # tobillo (E+1); la CAIDA dura 4 f (E+1 -> E+5); boca abajo 20 f (E+5 -> E+25); transicion RAPIDA a sobarse (E+25 -> E+32, 7 f)
RUB0, RUB1 = E + 34, int(globals().get('RUB1', 383))                         # sobarse el tobillo: sigue frotando hasta f383 (empieza el susto al ver al creeper en f384)
F_SPIN0, F_SPIN1 = E + 26, E + 30                                           # el empty `alfred` gira 180 grados en Z (4 f) al pasar a sobarse
def rz_at(f): u = min(1.0, max(0.0, (f - F_SPIN0) / float(F_SPIN1 - F_SPIN0))); return math.pi * u * u * (3 - 2 * u)
FIN = RUB1
CICLO_RUB = 18
FWD, DER, IZQ, ARR = Vector((0, 1, 0)), Vector((1, 0, 0)), Vector((-1, 0, 0)), Vector((0, 0, 1))
P9 = Vector(pts[-1]) + D0
def coast(f): u = min(1.0, max(0.0, (f - E) / 5.0)); return 0.9 * (1 - (1 - u) ** 2)                               # la inercia lo lleva ~0.9 m
def root_at(f): return (P9.x, P9.y + coast(f), P9.z + (0.0 if f > E else 0.0))

def mk(hips_rot, spine, neck, rleg, rknee, lleg, lknee, hips_loc):
    return {"Hips_alfred": hips_rot, "Spine_alfred": (Dg(spine), 0, 0), "Spine1_alfred": (Dg(spine), 0, 0), "Spine2_alfred": (Dg(spine), 0, 0), "Neck_alfred": (neck if isinstance(neck, tuple) else (Dg(neck), 0, 0)),
            "RightUpLeg_alfred": rleg, "Rightknee_alfred": rknee, "LeftUpLeg_alfred": lleg, "Leftknee_alfred": lknee}, tuple(hips_loc)
KEYS = {}
def clave(f, hips_rot, spine, neck, rleg, rknee, lleg, lknee, hips_loc, objetivos):
    rot, hl = mk(hips_rot, spine, neck, rleg, rknee, lleg, lknee, hips_loc); KEYS[f] = dict(rot=rot, hips=hl, obj=objetivos)

wc_E = WC                                                                    # fase del ciclo de correr al llegar a la ultima coordenada
run_E = pose_run(wc_E)
KEYS[E] = dict(rot={n: run_E[n] for n in NB if "Arm" not in n and "elbow" not in n and n != "Hips_alfred"} | {"Hips_alfred": run_E["Hips_alfred"]}, hips=tuple(H_LOC), obj=None,
               arm={l: (Euler(run_E[l + "UpArm_alfred"], 'XYZ').to_quaternion(), Euler(run_E[l + "elbow_alfred"], 'XYZ').to_quaternion()) for l in ("Right", "Left")})
# objetivos de las manos (funcion de la pose y del root en ese instante -> punto en el mundo)
def alto(M, Mw, raiz, l):    # brazos arriba y adelante (se desequilibra)
    sh = Mw @ M["Spine2_alfred"].translation; return sh + FWD * 0.20 + (DER if l == "Right" else IZQ) * 0.40 + ARR * 0.50
def al_suelo(M, Mw, raiz, l):  # manos hacia el suelo para frenar la caida
    return Vector(raiz) + FWD * 0.55 + (DER if l == "Right" else IZQ) * 0.32 + ARR * 0.12
clave(F_TW, (Dg(18), 0, Dg(12)), 10, 8, (Dg(20), Dg(8), Dg(-18)), (Dg(-60), Dg(35), Dg(14)), (Dg(-40), 0, Dg(8)), (Dg(-70), 0, 0), (H_LOC.x, H_LOC.y - 0.06, H_LOC.z), {"Right": alto, "Left": alto})
def adelante(M, Mw, raiz, l):  # manos estiradas hacia delante, sobre el suelo (cae de bruces)
    sh = Mw @ M["Spine2_alfred"].translation; return Vector((sh.x + (0.30 if l == "Right" else -0.30), sh.y + 0.65, raiz[2] + 0.07))
def empujar(M, Mw, raiz, l):   # manos en el suelo junto al pecho para incorporarse (en la orientacion del empty en ese momento)
    sh = Mw @ M["Spine2_alfred"].translation; return Vector((sh.x, sh.y, raiz[2] + 0.06)) + (DER if l == "Right" else IZQ) * 0.28 + FWD * 0.12
clave(F_GR, (Dg(88), 0, Dg(-6)), -6, (Dg(-8), Dg(55), 0), (Dg(0), Dg(10), Dg(-28)), (Dg(-75), Dg(40), Dg(12)), (Dg(0), Dg(-6), Dg(10)), (Dg(-8), 0, 0), (0.0, -0.747, -0.05), {"Right": adelante, "Left": adelante})  # boca abajo, rodilla derecha doblada y torcida
def apoyo_izq(M, Mw, raiz, l): return Vector(raiz) + IZQ * 0.36 - FWD * 0.08 + ARR * 0.04
def tobillo(M, Mw, raiz, l, frac=0.86):
    h, t = cabeza_cola(M, "Rightknee_alfred", Mw); return h + (t - h) * frac + ARR * 0.03
def medio(M, Mw, raiz, l): return tobillo(M, Mw, raiz, l, 0.6) if l == "Right" else apoyo_izq(M, Mw, raiz, l)
def final(M, Mw, raiz, l): return tobillo(M, Mw, raiz, l, 0.86) if l == "Right" else apoyo_izq(M, Mw, raiz, l)
clave(F_PUSH, (Dg(40), 0, Dg(-4)), 8, 20, (Dg(45), Dg(10), Dg(-20)), (Dg(-95), Dg(25), Dg(8)), (Dg(30), 0, Dg(4)), (Dg(-75), 0, 0), (0.0, -0.55, -0.05), {"Right": empujar, "Left": empujar})
def mezcla(M, Mw, raiz, l): return (empujar(M, Mw, raiz, l) + final(M, Mw, raiz, l)) * 0.5      # la mano derecha pasa del suelo al tobillo
clave(F_MID2, (Dg(20), 0, Dg(1)), 13, 27, (Dg(105), Dg(11), Dg(-12)), (Dg(-15), Dg(10), Dg(3)), (Dg(65), Dg(-5), Dg(5)), (Dg(-120), 0, 0), (0.0, -0.60, -0.05), {"Right": mezcla, "Left": mezcla})   # intermedia: pies en el suelo mientras se sienta
clave(F_SIT, (Dg(4), 0, Dg(4)), 18, 34, (Dg(122), Dg(12), Dg(-4)), (Dg(-55), 0, 0), (Dg(84), Dg(-12), Dg(6)), (Dg(-3), 0, 0), (0.0, -0.62, -0.05), {"Right": final, "Left": apoyo_izq})

# ---- resolver los brazos (IK) en cada clave ----
orden = sorted(KEYS)
for i, f in enumerate(orden):
    K = KEYS[f]
    if K.get("obj") is None: continue
    rt = root_at(f); loc = {"Hips_alfred": K["hips"]}; rot = {n: tuple(v) for n, v in K["rot"].items()}
    rz = rz_at(f); R3 = Matrix.Rotation(rz, 3, 'Z'); FWD, DER, IZQ = R3 @ Vector((0, 1, 0)), R3 @ Vector((1, 0, 0)), R3 @ Vector((-1, 0, 0))     # ejes del cuerpo segun el giro del empty
    M = fk(rot, loc); Mw = mundo(rt, rz); K["arm"] = {}
    prev = KEYS[orden[i - 1]]["arm"]
    for l in ("Right", "Left"):
        tgt = K["obj"][l](M, Mw, rt, l); sg = 1.0 if l == "Right" else -1.0
        hint = tgt - (DER if l == "Right" else IZQ) * 0.20 + Vector((0, -0.10, -0.05))
        q0, qe0 = prev[l]; x0 = 2 * math.atan2(qe0.x, qe0.w)
        q, qe, err, codo = resolver(l, M["Spine2_alfred"], Mw, tgt, codo_hint=hint, inicio=(q0, x0), iters=5000, semilla=3)
        K["arm"][l] = (q, qe); print("IK f%d %s: error de muneca %.3f m" % (f, l, err))

KEYS[F_GR2] = {k: KEYS[F_GR][k] for k in ("rot", "hips", "arm")}; KEYS[F_GR2]["obj"] = None; orden = sorted(KEYS)       # boca abajo quieto hasta F_GR2
# ---- rebote al caer boca abajo: 3 arcos parabolicos (duracion f, altura m) cada vez mas pequenos ----
REBOTES = ((6, 0.16), (4, 0.06), (3, 0.02)); REBOTE_FRAMES = sum(d for d, _ in REBOTES); REBOTE_GRADOS = float(globals().get('REBOTE_GRADOS', 20.0))   # grados de arqueo de la columna en el pico del primer rebote
def rebote(t):
    acc = 0
    for D, A in REBOTES:
        if t < acc + D: u = (t - acc) / float(D); return A * 4 * u * (1 - u)
        acc += D
    return 0.0
# ---- posicion/pose por frame ----
def ease(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)
cerca = lambda ref, v: v + 2 * math.pi * round((ref - v) / (2 * math.pi))                                  # v desenrollado para quedar a menos de 180 grados de ref
prevE = {}
def pose_en(f):
    if f >= orden[-1]: K = KEYS[orden[-1]]; return {n: tuple(v) for n, v in K["rot"].items()}, K["hips"], K["arm"]
    j = max(k for k in range(len(orden)) if orden[k] <= f); a, b = KEYS[orden[j]], KEYS[orden[j + 1]]; u = ease((f - orden[j]) / (orden[j + 1] - orden[j]))
    rot = {}
    for n in a["rot"]:
        ea, eb = a["rot"][n], b["rot"][n]; rot[n] = tuple(ea[c] + (cerca(ea[c], eb[c]) - ea[c]) * u for c in range(3))
    hips = tuple(a["hips"][c] + (b["hips"][c] - a["hips"][c]) * u for c in range(3))
    arm = {l: (a["arm"][l][0].slerp(b["arm"][l][0] if a["arm"][l][0].dot(b["arm"][l][0]) >= 0 else -b["arm"][l][0], u), a["arm"][l][1].slerp(b["arm"][l][1] if a["arm"][l][1].dot(b["arm"][l][1]) >= 0 else -b["arm"][l][1], u)) for l in ("Right", "Left")}
    return rot, hips, arm

# ---- sobarse: la mano derecha sube y baja por la espinilla (IK entre dos puntos) ----
rt_fin = root_at(F_SIT); Kf = KEYS[F_SIT]; Mf = fk({n: tuple(v) for n, v in Kf["rot"].items()}, {"Hips_alfred": Kf["hips"]}); rz_fin = rz_at(F_SIT); R3 = Matrix.Rotation(rz_fin, 3, 'Z'); FWD, DER, IZQ = R3 @ Vector((0, 1, 0)), R3 @ Vector((1, 0, 0)), R3 @ Vector((-1, 0, 0)); Mwf = mundo(rt_fin, rz_fin)
def ik_mano(tgt):
    qa = Kf["arm"]["Right"]; x0 = 2 * math.atan2(qa[1].x, qa[1].w)
    q, qe, err, _ = resolver("Right", Mf["Spine2_alfred"], Mwf, tgt, codo_hint=tgt - DER * 0.20 + Vector((0, -0.10, -0.05)), inicio=(qa[0], x0), iters=5000, semilla=4); print("IK sobar: error %.3f m" % err); return q, qe
tA = tobillo(Mf, Mwf, rt_fin, "Right", 0.88); tB = tobillo(Mf, Mwf, rt_fin, "Right", 0.52); RUB = (ik_mano(tA), ik_mano(tB))

prevA = {}; prevR = {}
key_hips_loc(E, tuple(H_LOC))                                                 # la cadera sigue en su sitio hasta la llegada
for f in range(E + 1, FIN + 1):
    rot, hips, arm = pose_en(f); rot = {n: list(v) for n, v in rot.items()}; hl = list(hips); arm = dict(arm)
    if F_GR <= f < F_GR + REBOTE_FRAMES:                                     # rebote al caer de cara: SOLO de la cintura para arriba (la cadera y las piernas quedan en el suelo; la columna se arquea y levanta pecho, cabeza y brazos)
        for s_ in ("Spine_alfred", "Spine1_alfred", "Spine2_alfred"): rot[s_][0] -= Dg(REBOTE_GRADOS) * rebote(f - F_GR) / REBOTES[0][1] / 3.0
    if F_GR2 <= f <= F_SIT:                                                  # al incorporarse los pies no atraviesan el suelo: se dobla mas la rodilla hasta apoyarlos
        rt_ = root_at(f); loc_ = {"Hips_alfred": tuple(hl)}
        for l_ in ("Right", "Left"):
            kn_ = l_ + "knee_alfred"
            for _ in range(60):
                M_ = fk({n: tuple(v) for n, v in rot.items()}, loc_)
                if cabeza_cola(M_, kn_, mundo(rt_, 0.0))[1].z - rt_[2] >= 0.03 or rot[kn_][0] < -Dg(140): break
                rot[kn_][0] -= Dg(2)
    if f >= F_SIT:                                                           # temblores y respiracion: tras la caida y mientras se soba
        t = f - F_SIT; amp = ss((f - F_SIT) / 4.0) * (1.0 - 0.5 * ss((f - RUB1) / 8.0)); w = 2 * math.pi
        rot["Neck_alfred"][0] += Dg(3.0) * math.sin(w * t / 40.0) * amp + Dg(2.5) * amp * math.sin(w * t / 9.0) * max(0.0, 1 - t / 30.0)       # cabeza que cabecea y estremecimiento inicial
        rot["Hips_alfred"] = (rot["Hips_alfred"][0], rot["Hips_alfred"][1], rot["Hips_alfred"][2] + Dg(1.6) * math.sin(w * t / 27.0) * amp)
        for s in ("Spine_alfred", "Spine1_alfred", "Spine2_alfred"): rot[s][0] += Dg(1.4) * math.sin(w * t / 23.0 + 0.5) * amp
    if RUB0 <= f <= RUB1 + CICLO_RUB:
        ph = (f - RUB0) / CICLO_RUB; a_ = ss((f - RUB0) / 6.0) * (1.0 - ss((f - RUB1) / float(CICLO_RUB)) if f > RUB1 else 1.0); osc = 0.5 - 0.5 * math.cos(2 * math.pi * ph) if f <= RUB1 else 0.0
        qA, qB = RUB[0][0], RUB[1][0]; eA, eB = RUB[0][1], RUB[1][1]; qB = qB if qA.dot(qB) >= 0 else -qB; eB = eB if eA.dot(eB) >= 0 else -eB
        qs, es = qA.slerp(qB, osc), eA.slerp(eB, osc); q0, e0 = arm["Right"]; arm["Right"] = (q0.slerp(qs if q0.dot(qs) >= 0 else -qs, a_), e0.slerp(es if e0.dot(es) >= 0 else -es, a_))
    key_root(f, root_at(f), rz_at(f)); key_hips_loc(f, tuple(hl))
    for n, v in rot.items():
        vv = tuple(cerca(prevE.get((n, c), v[c]), v[c]) for c in range(3)); key_rot(PB[n], f, vv); prevE.update({(n, c): vv[c] for c in range(3)})
    for l in ("Right", "Left"):
        q, qe = arm[l]; ub, eb = PB[l + "UpArm_alfred"], PB[l + "elbow_alfred"]
        eu = q.to_euler('XYZ', prevA.get(l + "u", Euler(run_E[l + "UpArm_alfred"], 'XYZ'))); ee = qe.to_euler('XYZ', prevA.get(l + "e", Euler(run_E[l + "elbow_alfred"], 'XYZ'))); prevA[l + "u"], prevA[l + "e"] = eu, ee
        key_rot(ub, f, tuple(eu)); key_rot(eb, f, tuple(ee))
print("CAIDA: tobillo f%d, cae f%d-%d (4 f), boca abajo f%d-%d (20 f), empty gira 180 grados f%d-%d, sentado f%d, se soba f%d-%d, fin f%d" % (F_TW, F_TW, F_GR, F_GR, F_GR2, F_SPIN0, F_SPIN1, F_SIT, RUB0, RUB1, FIN))
