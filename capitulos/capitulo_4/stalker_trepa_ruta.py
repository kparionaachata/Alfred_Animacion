# -*- coding: utf-8 -*-
"""alfred_cueva_5E.blend: la trepada completa hasta Alfred. Se ejecuta DESPUES de stalker_trepa_base.py y stalker_trepa_pared.py y redefine cuerpo/objetivo/_plantas_trepa:
la criatura sube por el acantilado (muro y = 91.3), gira en la esquina (radio R_ESQ) bajo la plataforma de bloques del tunel de la salida y avanza boca arriba por su cara inferior hasta quedar justo
debajo de la coordenada de Alfred (0.56, 84.07). Las manos y pies se apoyan donde el rayo (contra la superficie, en la direccion -normal del cuerpo) encuentra el agarre que mas sobresale.
Uso: bv = bvh_caverna(); P = planear(bv); preparar_plan(bv, P); trayecto(bv, P); resolver(bv, P, estado); escribir(P, estado)"""
import bpy, math
from mathutils import Vector, Quaternion, Euler, Matrix

R_ESQ = 1.4                   # radio de la esquina muro/techo
ALFRED_XY = (0.56, 84.07)
Z_BLOQ = 58.0


def techo(bv, x, y):
    """z de la cara inferior de la plataforma sobre (x, y) (rayo hacia arriba), None si no hay"""
    r = bv.ray_cast(Vector((x, y, Z_BLOQ)), Vector((0, 0, 1)), 20.0)
    return r[0].z if r[0] is not None else None


def techo_ef(bv, x, y):
    zs = [techo(bv, x + dx, y + dy) for dx in (-0.6, 0.0, 0.6) for dy in (-0.6, 0.0, 0.6)]
    zs = [z for z in zs if z is not None]
    return min(zs) if zs else 65.0


def _suave(vals, sigma=5.0):
    n = len(vals)
    K = int(3 * sigma)
    w = [math.exp(-0.5 * (i / sigma) ** 2) for i in range(-K, K + 1)]
    out = []
    for i in range(n):
        a = t = 0.0
        for k, wi in zip(range(-K, K + 1), w):
            a += wi * vals[min(n - 1, max(0, i + k))]
            t += wi
        out.append(a / t)
    return out


def trayecto(bv, P):
    """para cada frame de la trepada calcula el origen del cuerpo (en el plano de la superficie), el pitch y el roll: sube por el muro, gira en la esquina bajo la plataforma y avanza por su cara inferior
    hasta quedar bajo Alfred. P['clim'][f] = (origen, pitch, roll); fija F_FIN."""
    global F_FIN
    P.pop("clim", None)
    P.pop("cache", None)
    a0, p0, _, _ = cuerpo(bv, P, F_L1)
    O0 = origen_de(a0, p0, 0.0, 0.0)
    ywc = pared_ef(bv, 0.56, 60.0)
    zcc = techo_ef(bv, 0.56, ywc - R_ESQ)
    z_arc0 = zcc - R_ESQ
    dw = z_arc0 - O0.z
    arc = math.pi * R_ESQ / 2
    y_fin = ALFRED_XY[1] + 0.15
    cen_y = ywc - R_ESQ
    dc = cen_y - y_fin
    L = dw + arc + dc
    P["trayecto"] = {"ywc": ywc, "zcc": zcc, "dw": dw, "arc": arc, "L": L}
    # avance: arranque suave y frenado al llegar
    ss_, a = 0.0, 0
    S = {F_L1: 0.0}
    while L - ss_ > 0.02 and a < 3000:
        a += 1
        v = V_TREPA * (1.0 - math.exp(-a / 8.0)) * min(1.0, 0.10 + (L - ss_) / 4.0)
        ss_ += v
        S[F_L1 + a] = ss_
    f_llega = F_L1 + a
    F_FIN = f_llega + 14
    for f in range(f_llega + 1, F_FIN + 1):
        S[f] = L
    frs = sorted(S)
    raw = {}
    for f in frs:
        s = S[f]
        if s <= dw:
            z = O0.z + s
            x = P["ancla_J1"].x + (0.56 - P["ancla_J1"].x) * ss(s / max(dw, 1e-6))
            raw[f] = ("w", x, z, pared_ef(bv, x, z))
        elif s <= dw + arc:
            raw[f] = ("a", 0.56, s - dw, None)
        else:
            y = cen_y - (s - dw - arc)
            raw[f] = ("c", 0.56, y, techo_ef(bv, 0.56, y))
    ws = _suave([raw[f][3] if raw[f][0] == "w" else ywc for f in frs], 6.0)
    cs = _suave([raw[f][3] if raw[f][0] == "c" else zcc for f in frs], 6.0)
    clim = {}
    for i, f in enumerate(frs):
        tipo, x, u, _ = raw[f]
        a_ = f - F_L1
        roll = 0.05 * math.sin(2 * math.pi * a_ / T_TREPA)
        sway = 0.10 * math.sin(2 * math.pi * a_ / T_TREPA) * (1.0 if f <= f_llega else 0.0)
        if tipo == "w":
            O = Vector((x + sway, ws[i] - 0.02, u))
            pitch = 1.50 + 0.04 * math.sin(2 * math.pi * a_ / (T_TREPA * 2))
        elif tipo == "a":
            th = u / R_ESQ
            O = Vector((0.56 + sway, ywc - R_ESQ + (R_ESQ - 0.02) * math.cos(th), zcc - R_ESQ + (R_ESQ - 0.02) * math.sin(th)))
            pitch = 1.50 + th * (math.pi - 1.50) / (math.pi / 2)
        else:
            O = Vector((0.56 + sway, u, cs[i] - 0.02))
            pitch = math.pi
        clim[f] = (O, pitch, roll)
    P["clim"] = clim
    P["f_llega"] = f_llega
    return {"F_FIN": F_FIN, "L": round(L, 1), "dw": round(dw, 1), "ywc": ywc, "zcc": zcc, "f_llega": f_llega}


def cuerpo(bv, P, f):
    """(ancla, pitch, yaw, roll) del cuerpo en el frame f: encogerse y echarse atras (impulso), embestida a cuatro patas, agacharse otra vez justo antes de despegar, salto estirado en arco, impacto al aterrizar"""
    yaw = P["yaw"]
    if f <= F_RUN0:
        u = ss((f - 1) / float(F_RUN0 - 1))
        a = P["ancla_ini"].copy()
        a.y -= 0.28 * u
        a.z -= 0.24 * u
        return a, -0.10 * u + 0.04 * math.sin(math.pi * u), yaw, 0.0
    if f <= F_J0:
        u2 = (f - F_RUN0) / float(F_J0 - F_RUN0)
        a0 = P["ancla_ini"].copy()
        a0.y -= 0.28
        a = a0.lerp(P["ancla_J0"], u2 ** 1.3)
        sal = 0.24 * (1.0 - ss(u2 * 4.0))                                   # sale del encogimiento
        pre = ss((u2 - 0.72) / 0.28)                                         # ultimo tramo: se agacha y se alza de pecho para el impulso
        a.z = suelo(bv, a.x, a.y) + 0.68 - sal - 0.24 * pre + 0.07 * math.sin(2 * math.pi * (f - F_RUN0) / T_CORRE) * (1.0 - pre)
        return a, -0.10 * (1.0 - ss(u2 * 3.0)) + 0.10 * ss(u2) + 0.22 * pre, yaw, 0.0
    if f <= F_J1:
        u = (f - F_J0) / float(F_J1 - F_J0)
        A, B = P["ancla_J0"], P["ancla_J1"]
        y = A.y + (B.y - A.y) * (0.75 * u + 0.25 * ss(u))
        x = A.x + (B.x - A.x) * u
        z = A.z + (B.z - A.z) * (1.0 - (1.0 - u) ** 2.2) + 1.7 * math.sin(math.pi * u) ** 0.85
        pitch = 0.32 + (P["pitch_J1"] - 0.32) * ss(u) ** 0.9 + 0.10 * math.sin(math.pi * u)
        return Vector((x, y, z)), pitch, yaw, 0.05 * math.sin(2 * math.pi * u)
    if f <= F_L1:
        u = ss((f - F_J1) / float(F_L1 - F_J1))
        pitch = P["pitch_J1"] + (1.50 - P["pitch_J1"]) * u
        x = P["ancla_J1"].x
        zt = P["zc_ancla"]
        yw = pared_ef(bv, x, zt)
        a1 = Vector((x, yw - 0.62, zt))
        a = P["ancla_J1"].lerp(a1, u)
        imp = math.sin(math.pi * min(1.0, (f - F_J1) / float(F_L1 - F_J1) * 1.5))          # el impacto empuja el cuerpo contra el muro y rebota
        a.y += 0.30 * imp
        a.z -= 0.22 * imp
        return a, pitch, yaw, 0.0
    if "clim" in P:
        O, pitch, roll = P["clim"][min(f, max(P["clim"]))]
        return O + R_de(pitch, yaw, roll) @ B0, pitch, yaw, roll
    z = ancla_trepa_z(P, f)
    return Vector((X_MURO, pared_ef(bv, X_MURO, z) - 0.62, z)), 1.50, yaw, 0.0


def _plantas_trepa(P, bv, n, m):
    """punto de apoyo m (m>=1) de la extremidad n: nominal (lateral, adelante) en el marco del cuerpo en el centro del apoyo; entre candidatos cercanos elige el agarre que mas sobresale de la superficie y que esta al alcance"""
    if m <= 0:
        return P["plant0"][n].copy()
    cache = P.setdefault("cache", {})
    if (n, m) in cache:
        return cache[(n, m)].copy()
    td = F_L1 - BETA_T * T_TREPA + FASE[n] * T_TREPA + m * T_TREPA
    fm = min(int(round(td + BETA_T * T_TREPA / 2)), F_FIN)
    a, pit, yaw, roll = cuerpo(bv, P, fm)
    o = origen_de(a, pit, yaw, roll)
    R = R_de(pit, yaw, roll)
    nrm = R @ Vector((0, 0, 1))
    raiz = _raiz_miembro(P, bv, n, fm)
    l0 = LAT[n] * (1.0 + 0.10 * _jit(n, m, 1))
    f0 = ADEL_T[n] + 0.22 * _jit(n, m, 0)
    mejor, cm = None, 1e9
    for dl in (-0.4, 0.0, 0.4):
        for df in (-0.5, -0.25, 0.0, 0.25, 0.5):
            q = o + R @ Vector((l0 + dl, f0 + df, 0.0)) + nrm * 1.2
            r = bv.ray_cast(q, -nrm, 3.0)
            if r[0] is None:
                continue
            h = r[0] + nrm * 0.02
            d = (h - raiz).length
            c = abs(r[3] - 1.2) + 0.4 * (abs(dl) + abs(df)) + (6.0 * (d - ALCANCE[n[0]]) if d > ALCANCE[n[0]] else 0.0)
            if c < cm:
                mejor, cm = h, c
    if mejor is None:
        mejor = o + R @ Vector((l0, f0, 0.0))
    cache[(n, m)] = mejor
    return mejor.copy()


def objetivo(bv, P, n, f):
    """posicion mundo deseada de la punta de la extremidad n en el frame f"""
    if f <= F_RUN0:
        return P["tip0"][n].copy()
    if f <= F_J0:
        td0 = F_RUN0 - BETA_C * T_CORRE + FASE[n] * T_CORRE
        m = math.floor((f - td0) / T_CORRE)
        u = (f - td0) / T_CORRE - m
        P0 = _plantas_corre(P, bv, n, m)
        if u < BETA_C:
            return P0
        P1 = _plantas_corre(P, bv, n, m + 1)
        u2 = (u - BETA_C) / (1.0 - BETA_C)
        p = P0.lerp(P1, ss(u2))
        zm = max(suelo(bv, p.x, p.y, p.z + 1.5), P0.z, P1.z)
        p.z = max(p.z, zm + 0.10) + 0.32 * math.sin(math.pi * u2)
        return p
    if f <= F_J1:
        u = (f - F_J0) / float(F_J1 - F_J0)
        offA = mundo_a_local(P, bv, F_J0, objetivo(bv, P, n, F_J0))
        if n[0] == "H":
            offC = mundo_a_local(P, bv, F_J1, P["hit_mano"][n])
            e = ss(min(1.0, u * 1.1)) ** 0.9
            off = offA.lerp(offC, e)
            off.z += 0.45 * math.sin(math.pi * min(1.0, u * 1.1))
            off.y -= 0.55 * math.sin(math.pi * min(1.0, u / 0.4)) * (1.0 - ss(u / 0.4))       # los brazos se echan atras un instante y salen disparados hacia delante
        else:
            atras = Vector((LAT[n] * 0.95, -1.0, -0.15))                                      # las patas empujan y quedan estiradas detras
            tuck = Vector((LAT[n] * 0.9, -0.55, 0.55))
            if u < 0.4:
                off = offA.lerp(atras, ss(u / 0.4))
            else:
                off = atras.lerp(tuck, ss((u - 0.4) / 0.6))
        return local_a_mundo(P, bv, f, off)
    if f <= F_L1:
        if n[0] == "H":
            return P["hit_mano"][n].copy()
        u = ss((f - F_J1 - 2) / float(F_L1 - F_J1 - 2))
        tuck = local_a_mundo(P, bv, F_J1, Vector((LAT[n] * 0.9, -0.55, 0.55)))
        p = tuck.lerp(P["plant0"][n], u)
        p.y -= 0.35 * math.sin(math.pi * u)
        return p
    td0 = F_L1 - BETA_T * T_TREPA + FASE[n] * T_TREPA
    m = math.floor((f - td0) / T_TREPA)
    u = (f - td0) / T_TREPA - m
    P0 = _plantas_trepa(P, bv, n, m)
    if u < BETA_T:
        return P0
    P1 = _plantas_trepa(P, bv, n, m + 1)
    u2 = (u - BETA_T) / (1.0 - BETA_T)
    p = P0.lerp(P1, ss(u2))
    a, pit, yaw, roll = cuerpo(bv, P, f)
    nrm = R_de(pit, yaw, roll) @ Vector((0, 0, 1))
    return p + nrm * (0.32 * math.sin(math.pi * u2))
