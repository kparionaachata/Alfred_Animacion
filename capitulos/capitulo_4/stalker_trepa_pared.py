# -*- coding: utf-8 -*-
"""alfred_cueva_5E.blend: la criatura (the_stalker_1) estaba mirando hacia arriba junto al pico; se agacha, corre hacia el muro norte, SALTA sobre el (como los Lickers de Resident Evil), aterriza con las
manos y los pies agarrados a la pared y TREPA hacia arriba, hacia la cornisa donde esta Alfred. Todo se calcula en Python (FK propia de stalker_trepa_base.py) y al final se escribe como claves.
Frames: F_RUN0 empieza a correr, F_J0 despega, F_J1 las manos tocan el muro, F_L1 ya esta trepando, F_FIN fin.
Cuerpo: ancla (centro del cuerpo) + pitch/yaw del empty; el empty the_stalker_1 se coloca para que el ancla quede donde toca (origen = ancla - R*B0).
Uso:  exec(stalker_trepa_base.py); exec(este); plan = planear(); resolver(plan, estado)  (reanudable) ; escribir(plan)"""
import bpy, math, json
from mathutils import Vector, Quaternion, Euler, Matrix

F_RUN0, F_J0, F_J1, F_L1, F_FIN = 24, 46, 66, 80, 230
B0 = Vector((0.0, 0.15, 0.6))              # ancla del cuerpo en el marco local del empty
V_TREPA = 0.10                              # m por frame (2.4 m/s)
T_TREPA, BETA_T = 16.0, 0.60                # ciclo de las extremidades al trepar
T_CORRE, BETA_C = 7.0, 0.60
FASE = {"HL": 0.0, "FR": 0.0, "HR": 0.5, "FL": 0.5}
LAT = {"HL": -0.90, "HR": 0.90, "FL": -0.80, "FR": 0.80}
ADEL_T = {"HL": 1.35, "HR": 1.35, "FL": -0.30, "FR": -0.30}        # posicion de apoyo al trepar, delante del ancla (m, a lo largo del cuerpo)
NEUT_C = {"HL": (-0.90, 1.05), "HR": (0.90, 1.05), "FL": (-0.80, -0.10), "FR": (0.80, -0.10)}
X_MURO = 1.6
Y_SAL = 86.0                                # desde aqui salen los rayos hacia +Y contra el muro
TORSO = ("spine_1", "chest_1", "neck_1", "head_1")
ALFRED = Vector((0.56, 84.07, 65.55))


def R_de(pitch, yaw=0.0, roll=0.0):
    return Euler((pitch, roll, yaw), 'XYZ').to_matrix()


def origen_de(ancla, pitch, yaw=0.0, roll=0.0):
    return ancla - R_de(pitch, yaw, roll) @ B0


def muro(bv, x, z):
    """punto del muro (rayo hacia +Y a la altura z); si no hay, None"""
    r = bv.ray_cast(Vector((x, Y_SAL, z)), Vector((0, 1, 0)), 12.0)
    return r[0]


def suelo(bv, x, y, z0=12.0):
    r = bv.ray_cast(Vector((x, y, z0)), Vector((0, 0, -1)), 30.0)
    return r[0].z if r[0] is not None else 6.0


def planear(bv):
    """trayectorias del cuerpo y calendario de apoyos; devuelve el plan (dict) sin tocar la escena"""
    P = {}
    base_t = cargar_pose(800)
    p1011 = cargar_pose(1011)
    P["torso_ini"] = {n: p1011["q"][n].copy() for n in TORSO}
    P["torso_base"] = {n: base_t["q"][n].copy() for n in TORSO}
    P["root_ini"] = p1011["loc"]["root_1"].copy()
    P["root_base"] = base_t["loc"]["root_1"].copy()
    em0 = (Vector(EMP.location) if False else Vector((2.4058494567871094, 77.22034454345703, 6.015699863433838)), (0.0, 0.0, 0.018636204302310944))
    P["em0"] = em0
    P["pose0"] = p1011
    P["tip0"] = {n: punta(p1011, em0, n) for n in NEUTRO}
    # --- contacto con el muro
    zc = 14.3
    hit = {n: muro(bv, X_MURO + (-0.9 if n == "HL" else 0.9), zc) for n in ("HL", "HR")}
    P["hit_mano"] = hit
    ywall = sum(h.y for h in hit.values()) / 2.0
    P["ancla_J1"] = Vector((X_MURO, ywall - 1.1, zc - 0.21))
    P["pitch_J1"] = 0.75
    # --- despegue
    yaw0 = 0.0
    P["yaw"] = yaw0
    x0 = em0[0].x
    yt = 80.3
    zt = suelo(bv, x0, yt) + 0.68
    P["ancla_J0"] = Vector((x0 - 0.2, yt, zt))
    # --- ancla al correr: del punto actual a P["ancla_J0"]
    a_ini = em0[0] + R_de(0.0, em0[1][2]) @ B0
    P["ancla_ini"] = a_ini
    # --- trepa: cuerpo en la pared
    P["zc_ancla"] = zc - 0.95
    # parabola de vuelo
    T = (F_J1 - F_J0) / 24.0
    d = P["ancla_J1"] - P["ancla_J0"]
    g = 9.8
    P["v_vuelo"] = Vector((d.x / T, d.y / T, (d.z + 0.5 * g * T * T) / T))
    return P


def ancla_trepa_z(P, f):
    """altura del ancla durante F_L1..F_FIN: sube con velocidad V_TREPA (arranque suave)"""
    a = f - F_L1
    if a <= 0:
        return P["zc_ancla"]
    s = V_TREPA * (a - 8.0 * (1 - math.exp(-a / 8.0)))                       # aceleracion inicial
    return P["zc_ancla"] + s


def pared_ef(bv, x, z, rad=1.6):
    """y de la pared bajo el cuerpo: la menor (mas cercana) en una ventana alrededor de (x, z)"""
    ys = []
    for dz in (-0.5, 0.5, 1.5):
        for dx in (-0.6, 0.0, 0.6):
            h = muro(bv, x + dx, z + dz)
            if h is not None:
                ys.append(h.y)
    return min(ys) if ys else 90.5


def cuerpo(bv, P, f):
    """(ancla, pitch, yaw, roll) del cuerpo en el frame f"""
    yaw = P["yaw"]
    if f <= F_RUN0:
        return P["ancla_ini"], 0.0, yaw, 0.0
    if f <= F_J0:
        u = ss((f - F_RUN0) / float(F_J0 - F_RUN0))
        u2 = (f - F_RUN0) / float(F_J0 - F_RUN0)
        a = P["ancla_ini"].lerp(P["ancla_J0"], u2 ** 1.3)
        a.z = suelo(bv, a.x, a.y) + 0.68 + 0.10 * math.sin(2 * math.pi * (f - F_RUN0) / T_CORRE)
        return a, 0.10 * u, yaw, 0.0
    if f <= F_J1:
        t = (f - F_J0) / 24.0
        v = P["v_vuelo"]
        a = P["ancla_J0"] + Vector((v.x * t, v.y * t, v.z * t - 0.5 * 9.8 * t * t))
        u = (f - F_J0) / float(F_J1 - F_J0)
        return a, 0.10 + (P["pitch_J1"] - 0.10) * ss(u) ** 0.8, yaw, 0.0
    if f <= F_L1:
        u = ss((f - F_J1) / float(F_L1 - F_J1))
        pitch = P["pitch_J1"] + (1.50 - P["pitch_J1"]) * u
        x = P["ancla_J1"].x
        zt = ancla_trepa_z(P, F_L1)
        yw = pared_ef(bv, x, zt)
        a1 = Vector((x, yw - 0.62, zt))
        return P["ancla_J1"].lerp(a1, u), pitch, yaw, 0.0
    z = ancla_trepa_z(P, f)
    sway = 0.10 * math.sin(2 * math.pi * (f - F_L1) / T_TREPA)
    x = X_MURO + sway
    yw = pared_ef(bv, x, z)
    return Vector((x, yw - 0.62, z)), 1.50 + 0.04 * math.sin(2 * math.pi * (f - F_L1) / (T_TREPA * 2)), yaw, 0.05 * math.sin(2 * math.pi * (f - F_L1) / T_TREPA)


def _jit(n, m, k):
    import random
    return random.Random(hash((n, m, k)) % 100003 + (7 if n[0] == "H" else 3)).uniform(-1, 1)


def local_a_mundo(P, bv, f, off):
    a, pit, yaw, roll = cuerpo(bv, P, f)
    o = origen_de(a, pit, yaw, roll)
    return o + R_de(pit, yaw, roll) @ Vector(off)


def mundo_a_local(P, bv, f, p):
    a, pit, yaw, roll = cuerpo(bv, P, f)
    o = origen_de(a, pit, yaw, roll)
    return R_de(pit, yaw, roll).inverted() @ (p - o)


def _plantas_corre(P, bv, n, m):
    """punto de apoyo m de la extremidad n al correr: el neutro, en el centro del apoyo (m=0: donde ya esta)"""
    if m <= 0:
        return P["tip0"][n].copy()
    td = F_RUN0 - BETA_C * T_CORRE + FASE[n] * T_CORRE + m * T_CORRE
    fm = int(round(td + BETA_C * T_CORRE / 2))
    fm = min(fm, F_J0)
    p = local_a_mundo(P, bv, fm, (NEUT_C[n][0], NEUT_C[n][1], 0.0))
    p.z = suelo(bv, p.x, p.y, p.z + 1.5) + 0.02
    return p


def _raiz_miembro(P, bv, n, f):
    """hombro / cadera de la extremidad n en el mundo en el frame f"""
    a, pit, yaw, roll = cuerpo(bv, P, f)
    em = (origen_de(a, pit, yaw, roll), (pit, roll, yaw))
    h = ("upper_arm.%s_1" if n[0] == "H" else "thigh.%s_1") % TIPO[n][1]
    return fk(pose_frame(P, f), em, None, [h])[h].translation


ALCANCE = {"H": 1.75, "F": 1.02}


def _plantas_trepa(P, bv, n, m):
    """punto de apoyo m (m>=1) de la extremidad n al trepar; m=0 es el de aterrizaje. Entre varios candidatos cerca del nominal elige el agarre que sobresale mas hacia el cuerpo y esta al alcance"""
    if m <= 0:
        return P["plant0"][n].copy()
    cache = P.setdefault("cache", {})
    if (n, m) in cache:
        return cache[(n, m)].copy()
    td = F_L1 - BETA_T * T_TREPA + FASE[n] * T_TREPA + m * T_TREPA
    fm = int(round(td + BETA_T * T_TREPA / 2))
    zc = ancla_trepa_z(P, fm) - B0.y + ADEL_T[n] + 0.22 * _jit(n, m, 0)
    xc = X_MURO + LAT[n] * (1.0 + 0.10 * _jit(n, m, 1))
    ywall = pared_ef(bv, X_MURO, ancla_trepa_z(P, fm))
    raiz = _raiz_miembro(P, bv, n, fm)
    mejor, cm = None, 1e9
    for dx in (-0.4, 0.0, 0.4):
        for dz in (-0.5, -0.25, 0.0, 0.25, 0.5):
            x, z = xc + dx, zc + dz
            h = muro(bv, x, z)
            if h is None:
                continue
            h = h + Vector((0, -0.02, 0))
            d = (h - raiz).length
            c = abs(h.y - ywall) + 0.4 * (abs(dx) + abs(dz)) + (6.0 * (d - ALCANCE[n[0]]) if d > ALCANCE[n[0]] else 0.0)
            if c < cm:
                mejor, cm = h, c
    if mejor is None:
        mejor = Vector((xc, ywall + 0.4, zc))
    cache[(n, m)] = mejor
    return mejor.copy()


def preparar_plan(bv, P):
    """puntos de aterrizaje de los pies (se calculan una vez)"""
    zf = ancla_trepa_z(P, F_L1) - B0.y + ADEL_T["FL"]
    P["plant0"] = {}
    for n in NEUTRO:
        if n[0] == "H":
            P["plant0"][n] = P["hit_mano"][n]
        else:
            x = X_MURO + LAT[n]
            h = muro(bv, x, zf + 0.1 * (1 if n == "FR" else -1))
            P["plant0"][n] = h + Vector((0, -0.02, 0))
    # posicion en el marco del cuerpo durante el vuelo: de donde salen a donde llegan
    return P


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
            e = ss(min(1.0, u * 1.15)) ** 0.9
            off = offA.lerp(offC, e)
            off.z += 0.45 * math.sin(math.pi * min(1.0, u * 1.1))
        else:
            tuck = Vector((LAT[n] * 0.9, -0.55, 0.55))
            off = offA.lerp(tuck, ss(u * 1.3))
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
    p.y -= 0.32 * math.sin(math.pi * u2)
    return p


def torso_pose(P, f):
    t = ss((f - 1) / float(F_RUN0 + 6))
    q = {}
    for n in TORSO:
        a, b = P["torso_ini"][n], P["torso_base"][n]
        if a.dot(b) < 0:
            b = b.copy()
            b.negate()
        q[n] = a.slerp(b, t)
    root = P["root_ini"].lerp(P["root_base"], t)
    return q, root


def pose_frame(P, f):
    q, root = torso_pose(P, f)
    pose = copia(P["pose0"])
    pose["q"].update(q)
    pose["loc"]["root_1"] = root
    return pose


def _onda(fase):
    return math.sin(fase + 0.55 * math.sin(fase))


def modular(P, pose, em, f):
    """movimientos del torso encima de la pose base (antes de resolver las extremidades, asi las manos y pies no se deslizan): respiracion, cabeza y cuello levantados mirando hacia delante/arriba (hacia Alfred)
    al trepar, y la mandibula abierta en el grito del salto y entreabierta al respirar. Devuelve {hueso: Quaternion} ya sumados a pose['q']."""
    env = ss((f - 1) / 12.0)
    w = 0.05 if f < F_J0 else 0.09 if f < F_L1 else 0.075
    fase = 2 * math.pi * w * f
    s = _onda(fase)
    a = 1.0 + 0.5 * ss((f - F_RUN0) / 20.0)
    # extension de cuello y cabeza hacia delante/arriba (eje lateral del cuerpo): sube en el salto y se mantiene al trepar
    ext = 0.0 if f <= F_J0 else 0.55 * ss((f - F_J0) / float(F_L1 - F_J0))
    ext += 0.06 * math.sin(2 * math.pi * f / 37.0) * ss((f - F_L1) / 10.0)
    grito = ss((f - (F_J0 - 3)) / 6.0) * (1.0 - ss((f - (F_L1 + 6)) / 10.0))
    boca = 0.55 * grito + 0.05 * max(0.0, -s) * a * env
    ex = {}
    for n, amp in (("spine_1", 0.03), ("chest_1", 0.05)):
        ex[n] = Euler((amp * a * s * env, 0, 0)).to_quaternion()
        pose["q"][n] = pose["q"][n] @ ex[n]
    # impulso: la espalda se encorva al encogerse y al agacharse antes de despegar, y se arquea (pecho arriba) en la explosion del salto
    enc = ss((f - 1) / float(F_RUN0 - 1)) * (1.0 - ss((f - F_RUN0) / 8.0)) + ss((f - (F_J0 - 8)) / 6.0) * (1.0 - ss((f - F_J0) / 2.0))
    arq = ss((f - F_J0) / 3.0) * (1.0 - ss((f - (F_J0 + 10)) / 8.0)) + 0.5 * ss((f - (F_J0 + 10)) / 6.0) * (1.0 - ss((f - F_J1) / 4.0))
    flex = -0.22 * enc + 0.30 * arq
    for n, k in (("spine_1", 0.4), ("chest_1", 0.6)):
        R = fk(pose, em, None, [n])[n].to_3x3().to_quaternion()
        d = R.inverted() @ Quaternion((1, 0, 0), flex * k) @ R
        pose["q"][n] = pose["q"][n] @ d
        ex[n] = ex[n] @ d
    for n, k in (("neck_1", 0.45), ("head_1", 0.55)):
        R = fk(pose, em, None, [n])[n].to_3x3().to_quaternion()
        d = R.inverted() @ Quaternion((1, 0, 0), ext * k) @ R
        ex[n] = d
        pose["q"][n] = pose["q"][n] @ d
    for n in ("jaw_1", "neck_front_1"):
        ex[n] = Euler((-boca, 0, 0)).to_quaternion()
        pose["q"][n] = pose["q"][n] @ ex[n]
    return ex


def resolver(bv, P, estado, f_max=None, t_max=40.0):
    """para cada frame calcula el empty, el torso y la IK de las cuatro extremidades; estado['res'][f] = {'em':..., 'q':{hueso:Quaternion}, 'root':Vector, 'err':{n:m}}. Reanudable."""
    import time
    t0 = time.time()
    f_max = f_max or F_FIN
    res = estado.setdefault("res", {})
    prev = estado.setdefault("prev", {n: [0.0, 0.0, 0.0, 0.0] for n in NEUTRO})
    f = estado.get("f", 1)
    while f <= f_max and time.time() - t0 < t_max:
        a, pit, yaw, roll = cuerpo(bv, P, f)
        em = (origen_de(a, pit, yaw, roll), (pit, roll, yaw))
        pose = pose_frame(P, f)
        modular(P, pose, em, f)
        q = dict((n, pose["q"][n].copy()) for n in TORSO + ("jaw_1", "neck_front_1"))
        err = {}
        for n in NEUTRO:
            tgt = objetivo(bv, P, n, f)
            ex, par, e = ik(bv, pose, em, n, tgt, prev[n], holgura=0.10)
            prev[n] = par
            err[n] = round(e, 3)
            for b, dq in ex.items():
                q[b] = pose["q"][b] @ dq
        res[f] = {"em": em, "q": q, "root": pose["loc"]["root_1"].copy(), "err": err}
        f += 1
    estado["f"] = f
    return f > f_max


def escribir(P, estado):
    """claves de todo lo calculado: empty (location, rotation_euler) y huesos (rotation_quaternion + root_1.location)"""
    sc = bpy.context.scene
    res = estado["res"]
    for ob in (EMP, AR):
        if ob.animation_data:
            ob.animation_data_clear()
    EMP.rotation_mode = 'XYZ'
    for n in ["root_1"] + list(TORSO) + [b for n in NEUTRO for b in (s % TIPO[n][1] for s in LIM[TIPO[n][0]])]:
        AR.pose.bones[n].rotation_mode = 'QUATERNION'
    for f in sorted(res):
        r = res[f]
        EMP.location = r["em"][0]
        EMP.rotation_euler = r["em"][1]
        EMP.keyframe_insert("location", frame=f)
        EMP.keyframe_insert("rotation_euler", frame=f)
        for b, q in r["q"].items():
            pb = AR.pose.bones[b]
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=f)
        rb = AR.pose.bones["root_1"]
        rb.location = r["root"]
        rb.keyframe_insert("location", frame=f)
    sc.frame_start = 1
    sc.frame_end = max(sc.frame_end, max(res))
    sc.frame_set(1)
    return {"frames": len(res), "huesos": len(res[min(res)]["q"])}
