# -*- coding: utf-8 -*-
"""alfred_cueva_5D.blend: the_stalker_1 recorre la ruta hasta el pico en TRES tramos (por distancia recorrida s sobre la ruta de ruta_stalker_pico.py):
  1) CAMINAR (0..S_RUN0): el andar antinatural y asimetrico de stalker_camina_hasta_pico.py (con su animacion propia de subir/bajar bloques);
  2) CORRER (S_RUN0..S_CRAWL0): carrera propia, zancada larga y brazos que bombean, cada vez mas rapida y mas ENCORVADA (lam: 0 -> 1);
  3) GATEAR (desde S_CRAWL0): corre a cuatro patas como un cocodrilo: pecho cerca del suelo, codos y rodillas abiertos, manos y pies alternados en diagonal y ondulacion lateral de la columna.
La pose de gateo se diseno con fk_pose.py (FK estatico de la armadura: manos y pies al suelo, pecho a ~0.7 m). En correr/gatear el cuerpo se asienta en el suelo con esa misma FK
(root_1 vertical = -(punto de contacto mas bajo)).
Requiere, ejecutados antes en el mismo espacio: ruta_stalker_pico.py, stalker_camina_hasta_pico.py (_limpia/_fcs/HUESOS/POSTURA/ss/_ruido/_fase...), fk_pose.py.
Uso: recorrido_tres_tramos()"""
import bpy, math, json
from mathutils import Vector, Euler, Quaternion

S_RUN0, S_RUN1 = 30.0, 62.0       # el correr empieza en S_RUN0 y se va encorvando hasta S_RUN1
S_CRAWL0, S_CRAWL1 = 62.0, 70.0   # transicion a cuatro patas
# pose de gateo (optimizada con FK): spine, chest, neck, head, thigh pitch, thigh splay, shin, upper_arm pitch, upper_arm splay, forearm
GP = dict(sp=-1.51, ch=0.73, nk=-0.26, hd=1.19, th=0.82, ths=1.24, sh=-1.55, ua=-0.60, uas=1.21, fa=2.03)       # estilo Licker (Resident Evil): brazos y piernas muy abiertos, codos altos, vientre bajo y la cabeza ERGUIDA mirando al frente (cabeceo total ~ +0.14)


def _lerp(a, b, t):
    return a + (b - a) * t


def _mezcla(E1, E2, t):
    return {n: tuple(_lerp(a, b, t) for a, b in zip(E1[n], E2[n])) for n in E1}


def _paso_ph(ph, sw):
    """igual que _euler_paso pero con la fase dada"""
    sL, sR = math.sin(ph), math.sin(ph + 2.5)
    cL, cR = math.cos(ph), math.cos(ph + 2.5)
    sa = math.sin(ph + 3.1)
    E = {}
    E["thigh.L_1"] = (0.14 + sw * 0.55 * sL, sw * 0.12 * sL, -0.45 - sw * 0.2 * max(0.0, sL))
    E["thigh.R_1"] = (0.14 + sw * 0.28 * sR, sw * 0.05 * sR, 0.45 + sw * 0.06 * cR)
    E["shin.L_1"] = (-sw * (0.30 + 1.0 * max(0.0, cL)), 0, sw * 0.08 * sL)
    E["shin.R_1"] = (-sw * (0.60 + 0.25 * max(0.0, cR)), 0, -sw * 0.05 * sR)
    E["upper_arm.L_1"] = (sw * 0.75 * sa, sw * 0.2 * sa, -sw * 0.15)
    E["forearm.L_1"] = (sw * (0.45 + 0.9 * max(0.0, math.sin(ph + 3.7))), 0, sw * 0.10 * math.sin(ph * 0.5))
    E["upper_arm.R_1"] = (sw * (-0.18 + 0.08 * math.sin(ph * 0.5)), 0, sw * (0.30 + 0.20 * math.sin(ph * 0.5 + 1.0)))
    E["forearm.R_1"] = (sw * (1.05 + 0.15 * math.sin(ph * 0.5 + 0.8)), 0, sw * 0.12 * math.sin(ph * 0.5 + 2.0))
    E["neck_1"] = (POSTURA["neck_1"][0] + sw * 0.10 * math.sin(2 * ph + 0.4), POSTURA["neck_1"][1], POSTURA["neck_1"][2] + sw * 0.10 * math.sin(ph * 0.5 + 1.0))
    E["head_1"] = (POSTURA["head_1"][0], POSTURA["head_1"][1], POSTURA["head_1"][2] + sw * 0.18 * math.sin(ph * 0.5 + 2.0))
    E["spine_1"] = tuple(POSTURA["spine_1"][i] + (0.0, sw * 0.25 * math.sin(ph), sw * (0.12 * math.sin(ph + 1.2) + 0.10 * math.sin(ph * 0.5)))[i] for i in range(3))
    E["chest_1"] = tuple(POSTURA["chest_1"][i] + (0.0, -sw * 0.20 * math.sin(ph + 0.4), sw * 0.08 * math.sin(ph * 0.5 + 2.0))[i] for i in range(3))
    return E


def _correr(ph, lam, aw=1.0):
    """carrera propia: zancada larga asimetrica (la pierna derecha mas corta), brazos que bombean en contrafase, tronco cada vez mas encorvado (lam 0..1) y cabeza levantada mirando al frente"""
    sL, sR = math.sin(ph), math.sin(ph + math.pi + 0.35)
    cL, cR = math.cos(ph), math.cos(ph + math.pi + 0.35)
    amp = (0.75 + 0.45 * lam) * aw
    E = {}
    E["thigh.L_1"] = (0.25 + 0.2 * lam + amp * sL, 0.0, -0.32 - 0.08 * sL)
    E["thigh.R_1"] = (0.20 + 0.2 * lam + 0.8 * amp * sR, 0.0, 0.34 + 0.08 * sR)
    E["shin.L_1"] = (-(0.40 + 0.25 * lam) - (1.15 + 0.5 * lam) * aw * max(0.0, cL), 0.0, 0.0)
    E["shin.R_1"] = (-(0.45 + 0.25 * lam) - (0.90 + 0.4 * lam) * aw * max(0.0, cR), 0.0, 0.0)
    E["upper_arm.L_1"] = (0.15 + 0.35 * lam + 0.95 * aw * sR, 0.0, -0.28)
    E["upper_arm.R_1"] = (0.10 + 0.30 * lam + 0.80 * aw * sL, 0.0, 0.38)
    E["forearm.L_1"] = (1.05 + 0.45 * aw * max(0.0, sR), 0.0, 0.0)
    E["forearm.R_1"] = (0.95 + 0.50 * aw * max(0.0, sL), 0.0, 0.05)
    E["spine_1"] = (-0.50 - 0.45 * lam + 0.07 * aw * math.sin(2 * ph), 0.12 * aw * sL, 0.10 + 0.12 * aw * sL)
    E["chest_1"] = (-0.40 - 0.40 * lam, -0.10 * aw * sR, -0.08 + 0.08 * aw * sR)
    E["neck_1"] = (-0.20 + 0.50 * lam, 0.0, 0.10 + 0.06 * aw * sL)
    E["head_1"] = (0.45 - 0.35 * lam, 0.12, 0.12 + 0.10 * aw * sR)
    return E


def _gatear(ph, aw=1.0):
    """gateo de cocodrilo: base GP (pecho bajo, codos y rodillas abiertos); en diagonal (mano izq + pie dch, mano dch + pie izq) y ondulacion lateral de la columna"""
    g = GP
    sA, sB = math.sin(ph), math.sin(ph + math.pi + 0.3)
    E = {}
    E["upper_arm.L_1"] = (g["ua"] + aw * 0.55 * sA, 0.0, -g["uas"])
    E["upper_arm.R_1"] = (g["ua"] + aw * 0.50 * sB, 0.0, g["uas"])
    E["forearm.L_1"] = (g["fa"] - aw * 0.45 * max(0.0, sA), 0.0, 0.0)
    E["forearm.R_1"] = (g["fa"] - aw * 0.40 * max(0.0, sB), 0.0, 0.0)
    E["thigh.L_1"] = (g["th"] + aw * 0.45 * sB, 0.0, -g["ths"])
    E["thigh.R_1"] = (g["th"] + aw * 0.40 * sA, 0.0, g["ths"])
    E["shin.L_1"] = (g["sh"] - aw * 0.35 * max(0.0, sB), 0.0, 0.0)
    E["shin.R_1"] = (g["sh"] - aw * 0.30 * max(0.0, sA), 0.0, 0.0)
    E["spine_1"] = (g["sp"] + aw * 0.05 * math.sin(2 * ph), 0.0, aw * 0.32 * sA)
    E["chest_1"] = (g["ch"], 0.0, -aw * 0.26 * sA)
    E["neck_1"] = (g["nk"], 0.0, -aw * 0.20 * sA)
    E["head_1"] = (g["hd"], 0.0, aw * 0.18 * sA)
    return E


def _suelo_y(E, c):
    """root_1.y para que el punto de contacto mas bajo (pies; y con c>0 tambien las manos) quede a ras de suelo"""
    pose = {n: E[n] for n in HUESOS}
    P = puntos(pose, 0.0)
    mf = min(P["pieL"].z, P["pieR"].z)
    ma = min(mf, P["manoL"].z, P["manoR"].z)
    return -(mf + (ma - mf) * c)


def recorrido_tres_tramos():
    O, sc = bpy.data.objects, bpy.context.scene
    st, ar = O["the_stalker_1"], O["torso_1"]
    PB = ar.pose.bones
    sc.frame_set(1)
    fe = {(f.data_path, f.array_index): f for f in _fcs(st)}
    fa = {(f.data_path, f.array_index): f for f in _fcs(ar)}
    yaw0 = fe[("rotation_euler", 2)].evaluate(1)
    q1 = {n: Quaternion([fa[('pose.bones["%s"].rotation_quaternion' % n, i)].evaluate(1) for i in range(4)]) for n in HUESOS}
    r1 = Vector([fa[('pose.bones["root_1"].location', i)].evaluate(1) for i in range(3)])
    ruta = [Vector(p) for p in json.load(open(RUTA))]
    acum = [0.0]
    for i in range(1, len(ruta)):
        acum.append(acum[-1] + (ruta[i].xy - ruta[i - 1].xy).length)
    L = acum[-1]

    def en_ruta(sa):
        sa = max(0.0, min(L, sa))
        i = max(j for j in range(len(acum)) if acum[j] <= sa)
        if i >= len(ruta) - 1:
            return ruta[-1]
        t = (sa - acum[i]) / max(1e-6, acum[i + 1] - acum[i])
        return ruta[i].lerp(ruta[i + 1], t)

    def yaw_en(sa):
        d = (en_ruta(sa + 1.8) - en_ruta(sa)).xy
        return math.atan2(-d.x, d.y) if d.length > 1e-4 else None
    eventos, sx = [], 0.0
    while sx < L - 1.0:
        dz = en_ruta(sx + 0.9).z - en_ruta(sx).z
        if abs(dz) > 0.3:
            ult = eventos[-1] if eventos else None
            if ult and sx + 0.45 - ult[0] < 1.6 and (dz > 0) == (ult[1] > 0):
                eventos[-1] = (ult[0], ult[1] + dz)
                sx += 0.9
                continue
            eventos.append((sx + 0.45, dz))
            sx += 0.9
            continue
        sx += 0.1
    # ---- avance, fase del paso y parametros de tramo por frame ----
    ramp = lambda s, a, b: ss((s - a) / float(b - a))
    sarr, phs, par = {1: 0.0}, {1: _fase(1)}, {}
    sv, fr = 0.0, 1
    while sv < L - 0.02 and fr < 6000:
        s = sv
        r = ramp(s, S_RUN0, S_RUN0 + 4.0)
        lam = ramp(s, S_RUN0, S_RUN1)
        c = ramp(s, S_CRAWL0, S_CRAWL1)
        par[fr] = (r, lam, c)
        fr += 1
        rem = L - sv
        cerca = min((abs(sv - e[0]) for e in eventos), default=9.0)
        dph_w = _fase(fr) - _fase(fr - 1)
        dph_r = 2 * math.pi / (22.0 - 7.0 * lam)
        dph_c = 2 * math.pi / 13.0
        phs[fr] = phs[fr - 1] + _lerp(_lerp(dph_w, dph_r, r), dph_c, c)
        ph = phs[fr]
        v_w = VEL * (0.45 + 0.55 * (0.5 + 0.5 * math.sin(ph + 0.6)))
        v_r = (0.12 + 0.15 * lam) * (0.8 + 0.2 * math.sin(ph))
        v_c = 0.40 * (0.85 + 0.15 * math.sin(ph))
        v = _lerp(_lerp(v_w, v_r, r), v_c, c) * min(1.0, 0.15 + rem / 4.0) * (_lerp(0.55, 0.85, r) if cerca < 0.9 else 1.0)
        sv = min(L, sv + v)
        sarr[fr] = sv
    f_llega = fr
    par[f_llega] = (1.0, 1.0, 1.0)
    F_END = f_llega + 30
    for g in range(f_llega + 1, F_END + 1):
        sarr[g] = L
        phs[g] = phs[g - 1]
        par[g] = (1.0, 1.0, 1.0)
    sc.frame_end = F_END
    _limpia(ar, tuple('pose.bones["%s"]' % h for h in HUESOS + ("root_1",)))
    _limpia(st)
    ventanas = []
    for k, (se, dz) in enumerate(eventos):
        fc_ = next((g for g in sorted(sarr) if sarr[g] >= se), F_END)
        ventanas.append((fc_ - 10, fc_ + 10, dz, k))
    zs = {g: en_ruta(sarr[g]).z for g in sarr}

    def ventana(fr):
        for f0, f1, dz, k in ventanas:
            if f0 <= fr <= f1:
                return (fr - f0) / float(f1 - f0), dz, k
        return None
    st.rotation_mode = 'XYZ'
    yaw = yaw0
    for fr in range(F0, F_END + 1):
        w = [zs[g] for g in range(max(1, fr - 4), min(F_END, fr + 4) + 1)]
        xy = en_ruta(sarr[fr])
        zc = sum(w) / len(w)
        vw = ventana(fr)
        if vw:
            u, dz, k = vw
            zc += (0.22 * math.sin(math.pi * min(1.0, u * 1.1)) if dz > 0 else -0.05 * math.sin(math.pi * u))
        st.location = Vector((xy.x, xy.y, zc))
        yr = yaw_en(sarr[fr])
        if yr is not None:
            yaw += ((yr - yaw + math.pi) % (2 * math.pi) - math.pi) * 0.12
        st.rotation_euler = (0, 0, yaw)
        st.keyframe_insert("location", frame=fr)
        st.keyframe_insert("rotation_euler", frame=fr)
    semillas = {n: 100 + i for i, n in enumerate(HUESOS)}
    f_run0 = next((g for g in sorted(par) if par[g][0] > 0.0), f_llega)
    for fr in range(F0, F_END + 1):
        r, lam, c = par[fr]
        rem = L - sarr[fr]
        ph = phs[fr]
        aw = ss(rem / 2.0)                                           # al llegar, el movimiento se apaga
        aw_w = aw if fr > f_llega - 40 else 1.0
        sw = aw_w
        Ew = _paso_ph(ph, aw_w)
        vw = ventana(fr)
        ry_extra = 0.0
        if vw and r < 0.5:      # animacion propia de subir/bajar bloques: solo mientras camina
            u, dz, k = vw
            b = math.sin(math.pi * u) ** 1.3
            ld, tr = ("L", "R") if k % 2 == 0 else ("R", "L")
            add = lambda n, dx=0.0, dy=0.0, dzz=0.0: Ew.__setitem__(n, (Ew[n][0] + dx, Ew[n][1] + dy, Ew[n][2] + dzz))
            if dz > 0:
                lift = b * min(1.0, abs(dz) / 0.8)
                add("thigh.%s_1" % ld, 1.05 * lift); add("shin.%s_1" % ld, -1.35 * lift)
                add("thigh.%s_1" % tr, -0.25 * b); add("shin.%s_1" % tr, -0.45 * b * (1 - u))
                add("spine_1", -0.30 * b); add("chest_1", -0.15 * b); add("head_1", 0.12 * b)
                add("upper_arm.L_1", 0.55 * b, 0, 0.0); add("upper_arm.R_1", 0.55 * b, 0, 0.25 * b)
                ry_extra = -0.10 * b
            else:
                caida = ss((u - 0.45) / 0.2) * (1 - ss((u - 0.75) / 0.25))
                add("thigh.%s_1" % ld, 0.50 * b); add("shin.%s_1" % ld, -0.55 * b)
                add("shin.L_1", -0.85 * caida); add("shin.R_1", -0.85 * caida)
                add("thigh.L_1", 0.35 * caida); add("thigh.R_1", 0.35 * caida)
                add("spine_1", 0.18 * b - 0.25 * caida); add("chest_1", 0.10 * b)
                add("upper_arm.L_1", 0, 0, -0.55 * b); add("upper_arm.R_1", 0, 0, 0.55 * b)
                ry_extra = -0.16 * caida
        # mezcla de tramos: caminar -> correr (r) -> gatear (c)
        E = Ew
        if r > 0.0:
            E = _mezcla(E, _correr(ph, lam, aw), r)
        if c > 0.0:
            E = _mezcla(E, _gatear(ph, aw), c)
        tu = ss((fr - 1) / float(MEZCLA))
        for n in HUESOS:
            resp = 0.03 * math.sin(2 * math.pi * 0.012 * fr + 1) if n in ("spine_1", "chest_1") else 0.0
            sd = semillas[n]
            ex = E[n][0] + resp + 0.03 * _ruido(fr, 0.07, sd, 0)
            ey = E[n][1] + 0.018 * _ruido(fr, 0.07, sd, 1)
            ez = E[n][2] + 0.024 * _ruido(fr, 0.07, sd, 2)
            qw = Euler((ex, ey, ez)).to_quaternion()
            PB[n].rotation_quaternion = q1[n].slerp(qw, tu) if tu < 1.0 else qw
            PB[n].keyframe_insert("rotation_quaternion", frame=fr)
        ry_w = -0.0876 - sw * 0.05 * (0.5 + 0.5 * math.sin(2 * ph)) + 0.01 * _ruido(fr, 0.06, 8, 1) + ry_extra
        if r > 0.0:
            hop = 0.14 * lam * r * (1 - c) * max(0.0, math.sin(2 * ph + 1.0))      # fase de vuelo al correr
            ry_s = _suelo_y(E, c) + hop + 0.01 * _ruido(fr, 0.06, 8, 1)
            ry_w = _lerp(ry_w, ry_s, min(1.0, r * 2.0))
        rw = Vector((0.04 * _ruido(fr, 0.05, 7, 0) * (1 - c) + sw * 0.03 * math.sin(ph) * (1 - r), ry_w, sw * 0.04 * math.sin(ph) * (1 - r)))
        PB["root_1"].location = r1.lerp(rw, tu)
        PB["root_1"].keyframe_insert("location", frame=fr)
    for idb in (ar, st):
        for fc in _fcs(idb):
            for kp in fc.keyframe_points:
                if kp.co.x >= F0:
                    kp.interpolation = 'LINEAR'
            fc.update()
    sc.frame_set(1)
    return {"ruta_m": round(L, 1), "inicia_correr_en_frame": f_run0, "inicia_gateo_en_frame": next((g for g in sorted(par) if par[g][2] > 0.0), None), "llega_en_frame": f_llega, "frame_end": F_END}
