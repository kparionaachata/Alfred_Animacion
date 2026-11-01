# -*- coding: utf-8 -*-
# Calendario de saltos: los monos rotan entre las 7 coordenadas sin pisarse y sin atravesar hojas ni troncos.
import bpy, math, random
from mathutils import Vector

SC = bpy.context.scene
G_F = 9.81 / 24.0 ** 2
SPOTS = {1: (-75.5, 36.5, 19.0), 2: (-72.5, 22.5, 18.0), 3: (-77.5, 20.5, 16.0), 4: (-79.5, 35.5, 19.0), 5: (-70.5, 21.5, 18.0),
         6: (-76.5, 37.5, 21.0), 7: (-71.5, 20.5, 20.0)}
FIN = 1325
# (mono, spot de inicio, [ (spot, desde, hasta) ... ventanas obligatorias ])
MONOS = {
    6: (4, [(4, 173, 278), (4, 497, 596)]),
    3: (6, [(6, 1, 130), (6, 718, 834)]),
    7: (1, [(1, 518, 616)]),
    0: (5, [(5, 187, 293)]),
    1: (3, [(3, 538, 636)]),
    2: (2, [(7, 1028, 1152)]),
}
INI = {3: 6, 6: 4, 0: 5, 7: 1, 1: 3, 2: 2}
LIB = {}


def p_arco(a, b, T):
    A = Vector(SPOTS[a]); B = Vector(SPOTS[b])
    v = (B - A) / T
    v.z += 0.5 * G_F * T
    return [A + v * t - Vector((0, 0, 0.5 * G_F * t * t)) for t in range(T + 1)]


def _chequear(a, b, T, dg):
    pts = [p + Vector((0, 0, 0.9)) for p in p_arco(a, b, T)]
    for s_, e_ in zip(pts[2:-3], pts[3:-2]):
        d = e_ - s_; L = d.length
        hit, loc, nor, idx, ob, mat = SC.ray_cast(dg, s_, d / L, distance=L)
        if hit and not ob.name.startswith(('alfred', 'Alfred', 'Mesh_', 'bonobo', 'bm_', 'rat', 'Boca', 'Ojo', 'Pupila', 'Ceja', 'Nariz', 'Brillo', 'chicken', 'mesh_root')):
            return False
    return True


def precalc(frames=(1, 300, 600, 900, 1200)):
    for bk, f in enumerate(frames):
        SC.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        for a in SPOTS:
            for b in SPOTS:
                if a == b:
                    continue
                A = Vector(SPOTS[a]); B = Vector(SPOTS[b])
                d = math.hypot(B.x - A.x, B.y - A.y)
                T0 = max(18, int(d / 0.30) + 8)
                for extra in (0, 8, 16, 26, 40):
                    LIB[(a, b, T0 + extra, bk)] = _chequear(a, b, T0 + extra, dg)
    SC.frame_set(1)


def arco_libre(a, b, T, J):
    return LIB.get((a, b, T, min(4, J // 300)), False)


def T_para(a, b, J):
    A = Vector(SPOTS[a]); B = Vector(SPOTS[b])
    d = math.hypot(B.x - A.x, B.y - A.y)
    T0 = max(18, int(d / 0.30) + 8)
    for extra in (0, 8, 16, 26, 40):
        if arco_libre(a, b, T0 + extra, J):
            return T0 + extra
    return None


FAIL = {}


def _f(r):
    FAIL[r] = FAIL.get(r, 0) + 1
    return None


_PO = []


def PAIR_OK():
    if not _PO:
        ok = set()
        for (a, b, T, bk), v in LIB.items():
            if bk == 0 and v:
                ok.add((a, b))
        _PO.append(ok)
    return _PO[0]


def libre_spot(s, t0, t1, ocup, i):
    return all(not (s2 == s and m2 != i and t0 < b2 and a2 < t1) for (s2, a2, b2, m2) in ocup)


def generar(i, rnd, ocup):
    """hops de un mono caminando por el calendario (voraz): da vueltas entre estancias obligatorias"""
    spot0, vent = MONOS[i]
    wins = sorted([w for w in vent if w[2] > 1], key=lambda w: w[1])
    cur = INI[i]; t = 42
    hops = []
    objetivos = [(w[0], w[1] - 36, w[2] + 10) for w in wins] + [(None, FIN - 40, FIN)]
    for (sp_req, deadline, t_fin) in objetivos:
        guard = 0
        while guard < 60:
            guard += 1
            resto = deadline - t
            if sp_req is not None and cur != sp_req and resto < 170:
                cand = [sp_req] if (cur, sp_req) in PAIR_OK() else []
            elif resto > (170 if sp_req is not None else 70):
                cand = [s for s in SPOTS if s != cur and (cur, s) in PAIR_OK() and (sp_req is None or (s, sp_req) in PAIR_OK() or s == sp_req)]
                rnd.shuffle(cand)
            else:
                break
            if not cand:
                return None
            hecho = False
            for s in cand:
                for _ in range(6):
                    J = t + 18 + rnd.randint(0, 22)
                    T = T_para(cur, s, J)
                    if T is None:
                        break
                    L = J + T + 16
                    if s != sp_req and sp_req is not None:
                        Ab = Vector(SPOTS[s]); Bb = Vector(SPOTS[sp_req])
                        Tm = max(18, int(math.hypot(Bb.x - Ab.x, Bb.y - Ab.y) / 0.30) + 8) + 16
                        if L + 25 + Tm > deadline:
                            continue
                    if sp_req is None and L + 30 > FIN:
                        continue
                    if s == sp_req and L > deadline + 20:
                        continue
                    if libre_spot(s, J, L + (4 if s == sp_req else 52), ocup, i):
                        hops.append((i, J, T, cur, s)); cur = s; t = L; hecho = True
                        break
                if hecho:
                    break
            if not hecho:
                t += 15
                if t > deadline - 20:
                    break
        if sp_req is not None:
            if cur != sp_req:
                return None
            t = t_fin
    return hops


def intervalos(i, hops):
    out = []
    spot = INI[i]; t = 0
    for (_, J, T, a, b) in hops:
        out.append((a, t, J, i)); t = J + T + 6
        out.append((b, J, J + T + 12, i))
        spot = b
        t = J + T + 6
    out.append((spot, t, FIN + 60, i))
    return out


def choca(iv, ocup, i):
    for (s1, a1, b1, m1) in iv:
        for (s2, a2, b2, m2) in ocup:
            if m2 != i and s1 == s2 and a1 < b2 and a2 < b1:
                return True
    return False


def planificar(seed):
    rnd = random.Random(seed)
    ocup = []
    for i, (spot0, vent) in MONOS.items():
        ocup.append((INI[i], 0, 62, i))
        for (sp, a, b) in vent:
            if b > 1:
                ocup.append((sp, a - 110, b + 70, i))
    hops = []
    orden = list(MONOS)
    rnd.shuffle(orden)
    for i in orden:
        ok = False
        for _ in range(60):
            h = generar(i, rnd, ocup)
            if h is None:
                continue
            iv = intervalos(i, h)
            if choca(iv, ocup, i):
                continue
            ocup += iv
            hops += h
            ok = True
            break
        if not ok:
            return _f('mono%d' % i)
    return hops


def buscar():
    for seed in range(1, 80):
        h = planificar(seed)
        if h:
            return seed, h
    return None, None
