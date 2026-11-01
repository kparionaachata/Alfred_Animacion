# -*- coding: utf-8 -*-
"""alfred_cueva_5D.blend: gateo a cuatro patas con las extremidades ANCLADAS AL TERRENO.
Cada mano y cada pie sigue un ciclo de apoyo/vuelo (marcha diagonal: mano izq + pie dch, mano dch + pie izq): durante el apoyo el punto de contacto queda FIJO en el mundo, sobre el suelo real de la caverna
(rayo contra el BVH); en el vuelo viaja en arco hasta el siguiente punto de apoyo, que se coloca por delante segun la trayectoria de la criatura, y se eleva lo necesario para pasar por encima de salientes.
Las articulaciones se resuelven con IK numerica sobre la FK (hombro XYZ + codo / cadera XYZ + rodilla), el cuerpo sube y baja segun el terreno bajo los apoyos y se inclina segun la pendiente entre manos y pies,
y la columna ondula con la marcha. Se mezcla con lo anterior con el peso c de la transicion a cuatro patas.
Requiere (ejecutados antes, en este orden): ruta_stalker_pico.py, stalker_camina_hasta_pico.py, fk_pose.py, stalker_tres_recorridos.py, fk_clearance.py.
Uso: gateo_base(F0, F1)  (una vez)  ->  gateo_ik(F0, F1) (por tramos, reanudable)  ->  gateo_comprobar(F0, F1)"""
import bpy, math
from mathutils import Vector, Euler, Quaternion, Matrix

T_CICLO = 7.0           # frames por ciclo de cada extremidad
BETA = 0.60             # fraccion del ciclo en apoyo
ALTO_ARCO = 0.32        # elevacion del arco de vuelo (m)
NEUTRO = {"HL": (-0.90, 1.05), "HR": (0.90, 1.05), "FL": (-0.80, -0.10), "FR": (0.80, -0.10)}      # punto de apoyo neutro (x lateral, y delante) respecto al origen de la criatura
FASE = {"HL": 0.0, "FR": 0.0, "HR": 0.5, "FL": 0.5}
TIPO = {"HL": ("mano", "L"), "HR": ("mano", "R"), "FL": ("pierna", "L"), "FR": ("pierna", "R")}
HUESOS_TORSO = ("spine_1", "chest_1", "neck_1", "head_1")
LIM = ("upper_arm.%s_1", "forearm.%s_1")
LIMP = ("thigh.%s_1", "shin.%s_1")


def _ss(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _empty(fr):
    return Matrix.Translation(Vector([FE[("location", i)].evaluate(fr) for i in range(3)])), FE[("rotation_euler", 2)].evaluate(fr)


def _pos_yaw(fr):
    loc = Vector([FE[("location", i)].evaluate(fr) for i in range(3)])
    return loc, FE[("rotation_euler", 2)].evaluate(fr)


def _dir(yaw):
    return Vector((math.cos(yaw), math.sin(yaw), 0.0)), Vector((-math.sin(yaw), math.cos(yaw), 0.0))      # derecha, delante


def _suelo(cav, x, y, zref):
    r = cav.ray_cast(Vector((x, y, zref + 1.6)), Vector((0, 0, -1)), 5.0)
    return r[0].z if r[0] is not None else zref


def _neutro_mundo(cav, fr, nombre):
    loc, yaw = _pos_yaw(fr)
    r, f = _dir(yaw)
    nx, ny = NEUTRO[nombre]
    p = loc + r * nx + f * ny
    return Vector((p.x, p.y, _suelo(cav, p.x, p.y, loc.z) + 0.02))


def _punto_apoyo(cav, nombre, m):
    """punto de apoyo del ciclo m: el neutro en el instante medio del apoyo"""
    td = _F0 + FASE[nombre] * T_CICLO + m * T_CICLO
    return _neutro_mundo(cav, int(round(td + BETA * T_CICLO / 2)), nombre)


def objetivo(cav, nombre, fr):
    """(posicion mundo del contacto, en_apoyo)"""
    td0 = _F0 + FASE[nombre] * T_CICLO
    m = math.floor((fr - td0) / T_CICLO)
    td = td0 + m * T_CICLO
    u = (fr - td) / T_CICLO
    P0 = _punto_apoyo(cav, nombre, m)
    if u < BETA:
        return P0, True
    P1 = _punto_apoyo(cav, nombre, m + 1)
    u2 = (u - BETA) / (1.0 - BETA)
    p = P0.lerp(P1, _ss(u2))
    # elevacion: arco + lo necesario para pasar por encima de lo que haya en el recorrido
    zmax = max(_suelo(cav, *(P0.lerp(P1, k / 4.0).xy), max(P0.z, P1.z)) for k in range(5))
    p.z = max(p.z, zmax + 0.10) + ALTO_ARCO * math.sin(math.pi * u2)
    return p, False


_F0 = 686


def _s_acum(F1):
    s, out, prev = 0.0, {}, None
    for fr in range(1, F1 + 1):
        loc, _ = _pos_yaw(fr)
        if prev is not None:
            s += (loc.xy - prev.xy).length
        out[fr] = s
        prev = loc
    return out


def _c(s):
    return _ss((s - S_CRAWL0) / float(S_CRAWL1 - S_CRAWL0))


def _escribe(n, fr, q):
    for i in range(4):
        fcv = CAD[('pose.bones["%s"].rotation_quaternion' % n, i)]
        kp = KEYS[fcv].get(fr)
        if kp:
            kp.co.y = q[i]
            kp.handle_left.y = q[i]
            kp.handle_right.y = q[i]


def gateo_base(F0, F1):
    """pasada 1: pose base (GP) + ondulacion + inclinacion por la pendiente + altura del cuerpo, mezcladas con lo anterior segun c"""
    global _F0
    _F0 = F0
    preparar()
    indexar_claves()
    cav = bpy.app.driver_namespace["ruta_bvh"][0]
    sa = _s_acum(F1)
    elev = bpy.app.driver_namespace.get("elev_gateo", {})
    base_y = None
    # altura base de la pose GP: root_y para que el punto mas bajo (manos y pies) quede a ras de suelo
    E0 = _gatear(0.0, 0.0)
    ry0 = _suelo_y(E0, 1.0)
    pit = {}
    for fr in range(F0, F1 + 1):
        c = _c(sa[fr])
        if c <= 0.0:
            continue
        loc, yaw = _pos_yaw(fr)
        r, f = _dir(yaw)
        ph = 2 * math.pi * (fr - F0) / T_CICLO
        Et = _gatear(ph, 1.0)
        Eb = _gatear(ph, 0.0)
        # inclinacion por la pendiente: suelo bajo las manos vs bajo los pies
        zh = (_neutro_mundo(cav, fr, "HL").z + _neutro_mundo(cav, fr, "HR").z) / 2
        zp = (_neutro_mundo(cav, fr, "FL").z + _neutro_mundo(cav, fr, "FR").z) / 2
        pit[fr] = math.atan2(zh - zp, NEUTRO["HL"][1] - NEUTRO["FL"][1])
    # suavizado de la pendiente
    frs = sorted(pit)
    pits = {}
    for fr in frs:
        acc = tw = 0.0
        for i in range(-6, 7):
            w = math.exp(-0.5 * (i / 3.0) ** 2)
            acc += pit[min(frs[-1], max(frs[0], fr + i))] * w
            tw += w
        pits[fr] = acc / tw
    for fr in frs:
        c = _c(sa[fr])
        loc, yaw = _pos_yaw(fr)
        r, f = _dir(yaw)
        ph = 2 * math.pi * (fr - F0) / T_CICLO
        Et = _gatear(ph, 1.0)
        Eb = _gatear(ph, 0.0)
        for n in HUESOS_TORSO:
            new = Euler(Et[n]).to_quaternion()
            old = _q(n, fr)
            if new.dot(old) < 0:
                new.negate()
            _escribe(n, fr, old.slerp(new, c))
        # limbos: pose base (el IK la corrige despues)
        for n in ("upper_arm.L_1", "upper_arm.R_1", "forearm.L_1", "forearm.R_1", "thigh.L_1", "thigh.R_1", "shin.L_1", "shin.R_1"):
            new = Euler(Eb[n]).to_quaternion()
            old = _q(n, fr)
            if new.dot(old) < 0:
                new.negate()
            _escribe(n, fr, old.slerp(new, c))
        # pendiente: giro del tronco sobre el eje lateral (+ = morro arriba), aplicado a spine_1 con el peso c
        R = fk(fr, None, ["spine_1"])["spine_1"].to_3x3().to_quaternion()
        dq = R.inverted() @ Quaternion(r, pits[fr] * 0.8 * c) @ R
        _escribe("spine_1", fr, _q("spine_1", fr) @ dq)
        # altura del cuerpo: sobre la media del suelo bajo los cuatro apoyos
        zs = [_neutro_mundo(cav, fr, k).z for k in NEUTRO]
        dz = sum(zs) / 4.0 - loc.z
        fcv = CAD[('pose.bones["root_1"].location', 1)]
        kp = KEYS[fcv].get(fr)
        if kp:
            v = kp.co.y + (ry0 + dz + elev.get(fr, 0.0) - kp.co.y) * c
            kp.co.y = v
            kp.handle_left.y = v
            kp.handle_right.y = v
    for fcv in CAD.values():
        fcv.update()
    return {"frames": len(frs), "c0": frs[0] if frs else None}


def _punta(fr, nombre, extra):
    tipo, lado = TIPO[nombre]
    if tipo == "mano":
        return fk(fr, extra, ["finger_2.%s_1" % lado])["finger_2.%s_1" % lado] @ Vector((0, 0.28, 0))
    return fk(fr, extra, ["shin.%s_1" % lado])["shin.%s_1" % lado] @ Vector((0, -0.68, 0))


def _evalua(cav, fr, nombre, extra):
    """(punta, penalizacion): la punta es el contacto (mano/pie); la penalizacion crece si el codo/rodilla o el medio de los segmentos quedan a menos de 0.18 m de la caverna"""
    tipo, lado = TIPO[nombre]
    if tipo == "mano":
        hs = ["upper_arm.%s_1" % lado, "forearm.%s_1" % lado, "finger_2.%s_1" % lado]
        M = fk(fr, extra, hs)
        tip = M[hs[2]] @ Vector((0, 0.28, 0))
        pts = [M[hs[1]].translation, M[hs[0]] @ Vector((0, -0.34, 0)), M[hs[1]] @ Vector((0, -0.56, 0))]
    else:
        hs = ["thigh.%s_1" % lado, "shin.%s_1" % lado]
        M = fk(fr, extra, hs)
        tip = M[hs[1]] @ Vector((0, -0.68, 0))
        pts = [M[hs[1]].translation, M[hs[1]] @ Vector((0, -0.34, 0)), M[hs[0]] @ Vector((0, -0.27, 0))]
    pen = 0.0
    for p_ in pts:
        r = cav.find_nearest(p_)
        if r[0] is not None:
            d = (p_ - r[0]).dot(r[1])
            if d < 0.18:
                pen += (0.18 - d) ** 2
    return tip, pen


def gateo_ik(F0, F1, estado, t_max=40.0):
    """pasada 2 (reanudable): para cada frame y extremidad resuelve la IK hasta el objetivo de apoyo/vuelo y suma la correccion a las claves de base (peso c)"""
    import time
    global _F0
    _F0 = F0
    t0 = time.time()
    preparar()
    indexar_claves()
    cav = bpy.app.driver_namespace["ruta_bvh"][0]
    sa = estado.setdefault("sa", _s_acum(F1))
    prev = estado.setdefault("prev", {k: [0.0, 0.0, 0.0, 0.0] for k in NEUTRO})
    err = estado.setdefault("err", {})
    fr = estado.get("fr", F0)
    while fr <= F1 and time.time() - t0 < t_max:
        c = _c(sa[fr])
        if c <= 0.0:
            fr += 1
            continue
        for nombre in NEUTRO:
            tipo, lado = TIPO[nombre]
            n1, n2 = (LIM if tipo == "mano" else LIMP)
            n1, n2 = n1 % lado, n2 % lado
            tgt, apoyo = objetivo(cav, nombre, fr)

            def costo(p_):
                ex = dict(estado.get("extra", {}))
                ex[n1] = Euler((p_[0], p_[1], p_[2])).to_quaternion()
                ex[n2] = Euler((p_[3], 0, 0)).to_quaternion()
                tip, pen = _evalua(cav, fr, nombre, ex)
                return (tip - tgt).length_squared + 6.0 * pen + 0.004 * sum(x * x for x in p_) + 0.06 * sum((a - b) ** 2 for a, b in zip(p_, prev[nombre]))
            best, cb = list(prev[nombre]), None
            for ini in (list(prev[nombre]), [0.0, 0.0, 0.0, 0.0]):
                p_ = list(ini)
                c0 = costo(p_)
                for paso in (0.4, 0.2, 0.1, 0.05, 0.025):
                    for _ in range(4):
                        mejoro = False
                        for i in range(4):
                            for d in (paso, -paso):
                                q_ = list(p_)
                                q_[i] = max(-2.2, min(2.2, q_[i] + d))
                                cc = costo(q_)
                                if cc < c0:
                                    c0, p_, mejoro = cc, q_, True
                        if not mejoro:
                            break
                if cb is None or c0 < cb:
                    cb, best = c0, p_
            prev[nombre] = best
            ex = {n1: Euler((best[0], best[1], best[2])).to_quaternion(), n2: Euler((best[3], 0, 0)).to_quaternion()}
            e = (_evalua(cav, fr, nombre, ex)[0] - tgt).length
            err.setdefault(nombre, []).append((fr, round(e, 3), apoyo))
            # sumar la correccion (peso c) a las claves de base
            for nn, dq in ((n1, ex[n1]), (n2, ex[n2])):
                ide = Quaternion().slerp(dq, c)
                _escribe(nn, fr, _q(nn, fr) @ ide)
        fr += 1
    estado["fr"] = fr
    return fr > F1


def gateo_comprobar(F0, F1, estado):
    """error medio de contacto en apoyo, deslizamiento del punto de apoyo durante el apoyo y altura de los contactos sobre el suelo"""
    cav = bpy.app.driver_namespace["ruta_bvh"][0]
    res = {}
    for nombre, lst in estado["err"].items():
        ea = [e for fr, e, ap in lst if ap]
        res[nombre] = {"error_apoyo_medio_m": round(sum(ea) / max(1, len(ea)), 3), "max": round(max(ea) if ea else 0, 3)}
    # deslizamiento: posicion mundo real de la punta (FK con las claves finales) durante cada apoyo
    desl = {}
    for nombre in NEUTRO:
        tipo, lado = TIPO[nombre]
        td0 = F0 + FASE[nombre] * T_CICLO
        movs = []
        for m in range(int((F1 - F0) / T_CICLO) - 1):
            td = td0 + m * T_CICLO
            a, b = int(round(td + 1)), int(round(td + BETA * T_CICLO - 1))
            if a < F0 + 14 or b > F1 or b <= a:
                continue
            pts = [_punta(fr, nombre, None) for fr in range(a, b + 1)]
            movs.append(max((p - pts[0]).length for p in pts))
        desl[nombre] = round(sum(movs) / max(1, len(movs)), 3)
    return {"contacto": res, "deslizamiento_medio_en_apoyo_m": desl}


def gateo_elevacion(F0, F1, rad=0.30, ventana=4, sigma=2.5):
    """con las claves actuales calcula cuanto hay que subir el cuerpo en cada frame para que tronco, caderas, muslos y rodillas no se hundan en la caverna (holgura rad); dilatado y suavizado.
    Se guarda en bpy.app.driver_namespace['elev_gateo'] para que gateo_base lo sume a la altura; despues hay que repetir gateo_base y gateo_ik."""
    preparar()
    indexar_claves()
    cav = bpy.app.driver_namespace["ruta_bvh"][0]
    huesos = ["spine_1", "chest_1", "neck_1", "thigh.L_1", "thigh.R_1", "shin.L_1", "shin.R_1", "upper_arm.L_1", "upper_arm.R_1", "forearm.L_1", "forearm.R_1"]
    need = {}
    for fr in range(F0, F1 + 1):
        M = fk(fr, None, huesos)
        pts = []
        for n in ("spine_1", "chest_1", "neck_1"):                       # tronco: los huesos del tronco apuntan hacia arriba (+Y)
            m = M[n]
            pts += [m.translation, m @ Vector((0, 0.3, 0))]
        for n in ("thigh.L_1", "thigh.R_1"):                              # muslos y espinillas cuelgan hacia abajo desde su cabeza (-Y); el pie queda fuera (puede apoyar)
            m = M[n]
            pts += [m.translation, m @ Vector((0, -0.27, 0))]
        for n in ("shin.L_1", "shin.R_1"):
            m = M[n]
            pts += [m.translation, m @ Vector((0, -0.34, 0))]
        for n, L in (("upper_arm.L_1", 0.69), ("upper_arm.R_1", 0.69), ("forearm.L_1", 1.12), ("forearm.R_1", 1.12)):          # brazos: hombro -> codo -> muneca hacia abajo
            m = M[n]
            pts += [m.translation, m @ Vector((0, -L * 0.5, 0))]
        w = 0.0
        for p in pts:
            r = cav.find_nearest(p)
            if r[0] is None:
                continue
            d = (p - r[0]).dot(r[1])
            w = max(w, rad - d)
        need[fr] = max(0.0, w)
    frs = sorted(need)
    dil = {fr: max(need[min(frs[-1], max(frs[0], fr + i))] for i in range(-ventana, ventana + 1)) for fr in frs}
    K = int(3 * sigma)
    out = {}
    for fr in frs:
        acc = tw = 0.0
        for i in range(-K, K + 1):
            wi = math.exp(-0.5 * (i / sigma) ** 2)
            acc += dil[min(frs[-1], max(frs[0], fr + i))] * wi
            tw += wi
        out[fr] = max(acc / tw, need[fr] * 0.0)
    prev = bpy.app.driver_namespace.get("elev_gateo", {})
    for fr in out:
        out[fr] += prev.get(fr, 0.0)
    bpy.app.driver_namespace["elev_gateo"] = out
    return {"frames_con_hundimiento": sum(1 for v in need.values() if v > 0.02), "max_subida_m": round(max(out.values()), 2), "media_m": round(sum(out.values()) / len(out), 2)}
