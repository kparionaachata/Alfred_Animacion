# -*- coding: utf-8 -*-
"""Cinematica directa de torso_1 en Python (sin evaluar la escena: ~ms por frame) leyendo las curvas de accion + prueba de choque de manos/brazos contra la caverna (BVH).
fk(fr, extra) -> {hueso: matriz mundo de la pose}; extra = {hueso: Quaternion que se multiplica a la rotacion keyed}"""
import bpy, math
from mathutils import Vector, Matrix, Quaternion, Euler

AR = None
REST = {}
RAMA = {}
CAD = {}      # fcurves por (path, idx)
FE = {}


def preparar():
    global AR, REST, CAD, FE
    O = bpy.data.objects
    AR = O["torso_1"]
    st = O["the_stalker_1"]
    REST = {b.name: b.matrix_local.copy() for b in AR.data.bones}
    CAD = {(f.data_path, f.array_index): f for l in AR.animation_data.action.layers for s in l.strips for cb in s.channelbags for f in cb.fcurves}
    FE = {(f.data_path, f.array_index): f for l in st.animation_data.action.layers for s in l.strips for cb in s.channelbags for f in cb.fcurves}


def _q(n, fr):
    return Quaternion([CAD[('pose.bones["%s"].rotation_quaternion' % n, i)].evaluate(fr) for i in range(4)]) if ('pose.bones["%s"].rotation_quaternion' % n, 0) in CAD else Quaternion((1, 0, 0, 0))


def _loc(n, fr):
    return Vector([CAD[('pose.bones["%s"].location' % n, i)].evaluate(fr) for i in range(3)]) if ('pose.bones["%s"].location' % n, 0) in CAD else Vector()


def mundo_ar(fr):
    st = bpy.data.objects["the_stalker_1"]
    loc = Vector([FE[("location", i)].evaluate(fr) for i in range(3)])
    rot = Euler((0, 0, FE[("rotation_euler", 2)].evaluate(fr)))
    return Matrix.Translation(loc) @ rot.to_matrix().to_4x4() @ AR.matrix_parent_inverse @ AR.matrix_basis


def fk(fr, extra=None, huesos=None):
    extra = extra or {}
    W = mundo_ar(fr)
    cache = {}

    def pm(n):
        if n in cache:
            return cache[n]
        b = AR.data.bones[n]
        q = _q(n, fr)
        if n in extra:
            q = q @ extra[n]
        basis = Matrix.Translation(_loc(n, fr)) @ q.to_matrix().to_4x4()
        if b.parent:
            m = pm(b.parent.name) @ (REST[b.parent.name].inverted() @ REST[n]) @ basis
        else:
            m = REST[n] @ basis
        cache[n] = m
        return m
    return {n: W @ pm(n) for n in (huesos or [])}


def puntos_mano(fr, lado, extra=None):
    """puntos de control de brazo y mano (mundo): codo, muneca/punta de antebrazo y puntas+bases de los dedos"""
    hs = ["forearm.%s_1" % lado] + ["finger_1.%s_1" % lado, "finger_2.%s_1" % lado, "finger_3.%s_1" % lado, "thumb.%s_1" % lado]
    M = fk(fr, extra, hs)
    pts = []
    for n in hs[1:]:
        m = M[n]
        h = m.translation
        t = m @ Vector((0, AR.data.bones[n].length, 0))
        pts += [h, t, h.lerp(t, 0.5)]
    f = M[hs[0]]
    pts.append(f @ Vector((0, AR.data.bones[hs[0]].length * 0.5, 0)))
    return pts


def hundimiento(bvh, pts, margen=0.2):
    """profundidad maxima (con margen de grosor) a la que alguno de los puntos esta dentro del solido o a menos de `margen` de su superficie"""
    peor = 0.0
    for i, p in enumerate(pts):
        r = bvh.find_nearest(p)
        if r[0] is None:
            continue
        v = p - r[0]
        d = v.dot(r[1])          # >0 aire
        peor = max(peor, (margen[i] if isinstance(margen, (list, tuple)) else margen) - d)
    return peor


def _candidatos():
    c = []
    for ux in (0, 0.3, -0.3, 0.6, -0.6, 0.9, -0.9, 1.2, -1.2):
        for uz in (0, 0.4, -0.4, 0.8, -0.8):
            for fx in (0, 0.4, 0.8, 1.2):
                c.append((abs(ux) + abs(uz) + 0.7 * fx, ux, uz, fx))
    c.sort(key=lambda x: x[0])
    return c


def resolver(bvh, desde, hasta, estado, margen=0.2, t_max=40.0):
    """para cada frame y brazo busca la correccion minima (upper_arm X/Z, forearm X) que deja la mano fuera del solido; guarda en estado['d'][(fr,lado)] = (ux,uz,fx). Reanudable."""
    import time
    t0 = time.time()
    cand = _candidatos()
    d = estado.setdefault("d", {})
    fr = estado.get("fr", desde)
    while fr <= hasta and time.time() - t0 < t_max:
        for lado in ("L", "R"):
            if hundimiento(bvh, puntos_mano(fr, lado), margen) <= 0.0:
                d[(fr, lado)] = (0.0, 0.0, 0.0)
                continue
            mejor, mh = None, 9.0
            for _c, ux, uz, fx in cand:
                ex = {"upper_arm.%s_1" % lado: Euler((ux, 0, uz)).to_quaternion(), "forearm.%s_1" % lado: Euler((fx, 0, 0)).to_quaternion()}
                h = hundimiento(bvh, puntos_mano(fr, lado, ex), margen)
                if h <= 0.0:
                    mejor, mh = (ux, uz, fx), h
                    break
                if h < mh:
                    mejor, mh = (ux, uz, fx), h
            d[(fr, lado)] = mejor
        fr += 1
    estado["fr"] = fr
    return fr > hasta


def suavizar(bvh, estado, desde, hasta, margen=0.2, ventana=6, sigma=3.0, iters=10):
    """convierte las correcciones discretas por frame en curvas suaves: envolvente (valor de mayor modulo en +-ventana) y gaussiana; los frames que aun chocan vuelven al valor crudo
    y se repite (hasta `iters` veces). Devuelve {lado: {fr: (ux,uz,fx)}}"""
    d = estado["d"]
    frs = list(range(desde, hasta + 1))
    res = {}
    for lado in ("L", "R"):
        crudo = {fr: d[(fr, lado)] for fr in frs}
        act = dict(crudo)
        for _ in range(iters):
            env = {}
            for fr in frs:
                v = []
                for k in range(3):
                    vals = [act[g][k] for g in range(max(desde, fr - ventana), min(hasta, fr + ventana) + 1)]
                    v.append(max(vals, key=abs))
                env[fr] = v
            sm = {}
            wk = [math.exp(-0.5 * (i / sigma) ** 2) for i in range(-int(3 * sigma), int(3 * sigma) + 1)]
            for fr in frs:
                out = []
                for k in range(3):
                    a = b = 0.0
                    for i, w in zip(range(-int(3 * sigma), int(3 * sigma) + 1), wk):
                        g = min(hasta, max(desde, fr + i))
                        a += w * env[g][k]
                        b += w
                    out.append(a / b)
                sm[fr] = tuple(out)
            malos = 0
            for fr in frs:
                ux, uz, fx = sm[fr]
                ex = {"upper_arm.%s_1" % lado: Euler((ux, 0, uz)).to_quaternion(), "forearm.%s_1" % lado: Euler((fx, 0, 0)).to_quaternion()}
                if hundimiento(bvh, puntos_mano(fr, lado, ex), margen) > 0.0:
                    malos += 1
                    act[fr] = tuple(max(abs(a), abs(b)) * (1 if (a if abs(a) >= abs(b) else b) >= 0 else -1) for a, b in zip(sm[fr], crudo[fr]))
            if not malos:
                break
        res[lado] = sm
        res[lado + "_malos"] = malos
    return res


def aplicar(sm, desde, hasta):
    """multiplica las claves de upper_arm / forearm (L y R) por la correccion suavizada"""
    ar = AR
    PB = ar.pose.bones
    for lado in ("L", "R"):
        for fr in range(desde, hasta + 1):
            ux, uz, fx = sm[lado][fr]
            for n, e in (("upper_arm.%s_1" % lado, (ux, 0, uz)), ("forearm.%s_1" % lado, (fx, 0, 0))):
                q = _q(n, fr) @ Euler(e).to_quaternion()
                for i in range(4):
                    fc = CAD[('pose.bones["%s"].rotation_quaternion' % n, i)]
                    kp = KEYS[fc].get(fr)
                    if kp:
                        kp.co.y = q[i]
                        kp.handle_left.y = q[i]
                        kp.handle_right.y = q[i]
    for fc in CAD.values():
        fc.update()


CAND2 = [(ux, uz, fx) for ux in (-0.9, -0.6, -0.3, 0.0, 0.3, 0.6) for uz in (-0.6, 0.0, 0.6) for fx in (0.0, 0.5, 1.0)]


def unarios(bvh, estado, lado, desde, hasta, margen=0.2, t_max=40.0):
    """coste por frame y candidato (magnitud + 1000*hundimiento); reanudable"""
    import time
    t0 = time.time()
    U = estado.setdefault("U" + lado, {})
    fr = estado.get("fu" + lado, desde)
    while fr <= hasta and time.time() - t0 < t_max:
        fila = []
        for ux, uz, fx in CAND2:
            ex = {"upper_arm.%s_1" % lado: Euler((ux, 0, uz)).to_quaternion(), "forearm.%s_1" % lado: Euler((fx, 0, 0)).to_quaternion()}
            h = hundimiento(bvh, puntos_mano(fr, lado, ex), margen)
            fila.append(abs(ux) + abs(uz) + 0.7 * fx + 1000.0 * max(0.0, h))
        U[fr] = fila
        fr += 1
    estado["fu" + lado] = fr
    return fr > hasta


def viterbi(estado, lado, desde, hasta, lam=2.5):
    U = estado["U" + lado]
    n = len(CAND2)
    dist = [[sum(abs(a - b) for a, b in zip(CAND2[i], CAND2[j])) for j in range(n)] for i in range(n)]
    cost = list(U[desde])
    back = {}
    for fr in range(desde + 1, hasta + 1):
        nuevo, bk = [], []
        for j in range(n):
            mi, mv = 0, 1e18
            for i in range(n):
                v = cost[i] + lam * dist[i][j]
                if v < mv:
                    mv, mi = v, i
            nuevo.append(mv + U[fr][j])
            bk.append(mi)
        cost = nuevo
        back[fr] = bk
    j = min(range(n), key=lambda k: cost[k])
    ruta = {hasta: j}
    for fr in range(hasta, desde, -1):
        j = back[fr][j]
        ruta[fr - 1] = j
    return {fr: CAND2[ruta[fr]] for fr in ruta}


# ---- piernas: igual que los brazos pero solo en los frames donde ya chocan (el resto queda en 0) ----
CAND_P = sorted([(tx, tz, sx) for tx in (0.0, 0.3, 0.6, 0.9, 1.2) for tz in (-0.3, 0.0, 0.3) for sx in (0.0, -0.4, -0.8, -1.2)], key=lambda c: abs(c[0]) + abs(c[1]) + 0.7 * abs(c[2]))


def puntos_pierna(fr, lado, extra=None):
    hs = ["thigh.%s_1" % lado, "shin.%s_1" % lado]
    M = fk(fr, extra, hs)
    sh = M[hs[1]]
    L = AR.data.bones[hs[1]].length
    th = M[hs[0]]
    LT = AR.data.bones[hs[0]].length
    return [sh.translation, sh @ Vector((0, L * 0.5, 0)), sh @ Vector((0, L, 0)), th @ Vector((0, LT * 0.5, 0))]


MARG_P = [0.14, 0.14, -0.04, 0.14]          # rodilla, medio de la tibia, pie (puede apoyar en el suelo), medio del muslo: el grosor de la malla


def unarios_pierna(bvh, estado, lado, desde, hasta, t_max=40.0):
    import time
    t0 = time.time()
    U = estado.setdefault("UP" + lado, {})
    fr = estado.get("fup" + lado, desde)
    while fr <= hasta and time.time() - t0 < t_max:
        fila = [0.0] * len(CAND_P)
        if hundimiento(bvh, puntos_pierna(fr, lado), MARG_P) > 0.0:
            for i, (tx, tz, sx) in enumerate(CAND_P):
                ex = {"thigh.%s_1" % lado: Euler((tx, 0, tz)).to_quaternion(), "shin.%s_1" % lado: Euler((sx, 0, 0)).to_quaternion()}
                h = hundimiento(bvh, puntos_pierna(fr, lado, ex), MARG_P)
                fila[i] = abs(tx) + abs(tz) + 0.7 * abs(sx) + 1000.0 * max(0.0, h)
        else:
            fila = [abs(c[0]) + abs(c[1]) + 0.7 * abs(c[2]) + 5.0 for c in CAND_P]     # sin choque: lo mejor es no tocar nada
            fila[0] = 0.0
        U[fr] = fila
        fr += 1
    estado["fup" + lado] = fr
    return fr > hasta


def resolver_piernas(bvh, estado, lado, desde, hasta, lam=1.5, dil=5, sigma=1.5, iters=4):
    import math as _m
    n = len(CAND_P)
    U = estado["UP" + lado]
    dist = [[sum(abs(a - b) for a, b in zip(CAND_P[i], CAND_P[j])) for j in range(n)] for i in range(n)]
    cost = list(U[desde])
    back = {}
    for fr in range(desde + 1, hasta + 1):
        nuevo, bk = [], []
        for j in range(n):
            mi, mv = 0, 1e18
            for i in range(n):
                v = cost[i] + lam * dist[i][j]
                if v < mv:
                    mv, mi = v, i
            nuevo.append(mv + U[fr][j])
            bk.append(mi)
        cost = nuevo
        back[fr] = bk
    j = min(range(n), key=lambda k: cost[k])
    ruta = {hasta: j}
    for fr in range(hasta, desde, -1):
        j = back[fr][j]
        ruta[fr - 1] = j
    P = {fr: CAND_P[ruta[fr]] for fr in ruta}
    crudo = dict(P)
    frs = list(range(desde, hasta + 1))
    for it in range(iters):
        # dilatacion (valor de mayor modulo en +-dil) y gaussiana corta
        env = {}
        for fr in frs:
            vv = []
            for k in range(3):
                vals = [P[g][k] for g in range(max(desde, fr - dil), min(hasta, fr + dil) + 1)]
                vv.append(max(vals, key=abs))
            env[fr] = vv
        K = int(3 * sigma)
        w = [_m.exp(-0.5 * (i / sigma) ** 2) for i in range(-K, K + 1)]
        S = {}
        for fr in frs:
            acc = [0, 0, 0]
            tw = 0
            for i, wi in zip(range(-K, K + 1), w):
                g = min(hasta, max(desde, fr + i))
                tw += wi
                for k in range(3):
                    acc[k] += wi * env[g][k]
            S[fr] = tuple(a / tw for a in acc)
        malos = []
        for fr in frs:
            if all(abs(x) < 1e-6 for x in crudo[fr]) and all(abs(x) < 1e-3 for x in S[fr]):
                continue
            tx, tz, sx = S[fr]
            ex = {"thigh.%s_1" % lado: Euler((tx, 0, tz)).to_quaternion(), "shin.%s_1" % lado: Euler((sx, 0, 0)).to_quaternion()}
            if hundimiento(bvh, puntos_pierna(fr, lado, ex), MARG_P) > 0.02:
                malos.append(fr)
        if not malos:
            break
        for fr in malos:
            P[fr] = tuple(max(abs(a), abs(b)) * (1 if (a if abs(a) >= abs(b) else b) >= 0 else -1) for a, b in zip(S[fr], crudo[fr]))
        dil += 2
    return S, len(malos)


def aplicar_piernas(S, lado, desde, hasta):
    for fr in range(desde, hasta + 1):
        tx, tz, sx = S[fr]
        if abs(tx) + abs(tz) + abs(sx) < 1e-4:
            continue
        for n, e in (("thigh.%s_1" % lado, (tx, 0, tz)), ("shin.%s_1" % lado, (sx, 0, 0))):
            q = _q(n, fr) @ Euler(e).to_quaternion()
            for i in range(4):
                fc = CAD[('pose.bones["%s"].rotation_quaternion' % n, i)]
                kp = KEYS[fc][fr]
                kp.co.y = q[i]
                kp.handle_left.y = q[i]
                kp.handle_right.y = q[i]
    for fc in CAD.values():
        fc.update()


KEYS = {}


def indexar_claves():
    KEYS.clear()
    for fc in CAD.values():
        KEYS[fc] = {round(p.co.x): p for p in fc.keyframe_points}


# ---- solver generico (manos y piernas) con margen por frame y candidatos dispersos ----
CAND_M = sorted([(ux, uz, fx) for ux in (-0.9, -0.6, -0.3, 0.0, 0.3, 0.6, 0.9) for uz in (-0.6, 0.0, 0.6) for fx in (-0.6, 0.0, 0.5, 1.0)], key=lambda c: abs(c[0]) + abs(c[1]) + 0.7 * abs(c[2]))
KIND = {
    "mano": (CAND_M, puntos_mano, ("upper_arm.%s_1", lambda c: (c[0], 0, c[1])), ("forearm.%s_1", lambda c: (c[2], 0, 0))),
    "pierna": (CAND_P, puntos_pierna, ("thigh.%s_1", lambda c: (c[0], 0, c[1])), ("shin.%s_1", lambda c: (c[2], 0, 0))),
}


def _extra(kind, lado, c):
    _, _, (n1, f1), (n2, f2) = KIND[kind]
    return {n1 % lado: Euler(f1(c)).to_quaternion(), n2 % lado: Euler(f2(c)).to_quaternion()}


def _mag(c):
    return abs(c[0]) + abs(c[1]) + 0.7 * abs(c[2])


def unarios_g(bvh, estado, kind, lado, desde, hasta, margen, t_max=40.0):
    """margen: numero, lista (por punto) o funcion fr -> numero/lista. Reanudable."""
    import time
    t0 = time.time()
    cand, pf = KIND[kind][0], KIND[kind][1]
    U = estado.setdefault((kind, lado), {})
    fr = estado.get(("f", kind, lado), desde)
    while fr <= hasta and time.time() - t0 < t_max:
        mg = margen(fr) if callable(margen) else margen
        if hundimiento(bvh, pf(fr, lado), mg) > 0.0:
            fila = []
            for c in cand:
                h = hundimiento(bvh, pf(fr, lado, _extra(kind, lado, c)), mg)
                fila.append(_mag(c) + 1000.0 * max(0.0, h))
        else:
            fila = [_mag(c) + 5.0 for c in cand]
            fila[cand.index((0.0, 0.0, 0.0))] = 0.0
        U[fr] = fila
        fr += 1
    estado[("f", kind, lado)] = fr
    return fr > hasta


def resolver_g(bvh, estado, kind, lado, desde, hasta, margen, lam=1.5, dil=5, sigma=1.5, iters=5):
    import math as _m
    cand, pf = KIND[kind][0], KIND[kind][1]
    n = len(cand)
    U = estado[(kind, lado)]
    dist = [[sum(abs(a - b) for a, b in zip(cand[i], cand[j])) for j in range(n)] for i in range(n)]
    cost = list(U[desde])
    back = {}
    for fr in range(desde + 1, hasta + 1):
        nuevo, bk = [], []
        for j in range(n):
            mi, mv = 0, 1e18
            for i in range(n):
                v = cost[i] + lam * dist[i][j]
                if v < mv:
                    mv, mi = v, i
            nuevo.append(mv + U[fr][j])
            bk.append(mi)
        cost = nuevo
        back[fr] = bk
    j = min(range(n), key=lambda k: cost[k])
    ruta = {hasta: j}
    for fr in range(hasta, desde, -1):
        j = back[fr][j]
        ruta[fr - 1] = j
    P = {fr: cand[ruta[fr]] for fr in ruta}
    crudo = dict(P)
    frs = list(range(desde, hasta + 1))
    malos = []
    for it in range(iters):
        env = {}
        for fr in frs:
            vv = []
            for k in range(3):
                vals = [P[g][k] for g in range(max(desde, fr - dil), min(hasta, fr + dil) + 1)]
                vv.append(max(vals, key=abs))
            env[fr] = vv
        K = int(3 * sigma)
        w = [_m.exp(-0.5 * (i / sigma) ** 2) for i in range(-K, K + 1)]
        S = {}
        for fr in frs:
            acc = [0, 0, 0]
            tw = 0
            for i, wi in zip(range(-K, K + 1), w):
                g = min(hasta, max(desde, fr + i))
                tw += wi
                for k in range(3):
                    acc[k] += wi * env[g][k]
            S[fr] = tuple(a / tw for a in acc)
        malos = []
        for fr in frs:
            if all(abs(x) < 1e-6 for x in crudo[fr]) and all(abs(x) < 1e-3 for x in S[fr]):
                continue
            mg = margen(fr) if callable(margen) else margen
            if hundimiento(bvh, pf(fr, lado, _extra(kind, lado, S[fr])), mg) > 0.02:
                malos.append(fr)
        if not malos:
            break
        for fr in malos:
            P[fr] = tuple(max(abs(a), abs(b)) * (1 if (a if abs(a) >= abs(b) else b) >= 0 else -1) for a, b in zip(S[fr], crudo[fr]))
        dil += 2
    return S, len(malos)


def aplicar_g(S, kind, lado, desde, hasta):
    _, _, (n1, f1), (n2, f2) = KIND[kind]
    for fr in range(desde, hasta + 1):
        c = S[fr]
        if _mag(c) < 1e-4:
            continue
        for n, e in ((n1 % lado, f1(c)), (n2 % lado, f2(c))):
            q = _q(n, fr) @ Euler(e).to_quaternion()
            for i in range(4):
                fc = CAD[('pose.bones["%s"].rotation_quaternion' % n, i)]
                kp = KEYS[fc][fr]
                kp.co.y = q[i]
                kp.handle_left.y = q[i]
                kp.handle_right.y = q[i]
    for fc in CAD.values():
        fc.update()
