# -*- coding: utf-8 -*-
"""alfred_cueva_5D.blend: the_stalker_1 sigue caminando desde su posicion del frame 1 hasta el pico (alfred_pico_piedra) por una ruta sin atravesar la caverna
(ruta_stalker_pico.py: A* con el BVH de caverna_*, JSON ruta_stalker_pico_5D.json). Mismo andar antinatural y asimetrico que en 5B (la fase del paso continua: FASE0 frames ya andados),
avance a tirones segun la fase, gira siguiendo la ruta, frena al llegar y se queda quieto con la respiracion. Frames 2..fin (se calcula con la longitud de la ruta).
Uso: exec(ruta_stalker_pico.py); exec(este); ruta = calcular_ruta()  (repetir hasta listo); caminar_hasta_pico()
"""
import bpy, math, json
from mathutils import Vector, Euler, Quaternion

F0 = 2
FASE0 = 384
V_CAMINAR = 1.5                  # factor de velocidad de la marcha (1.0 = la original de 5B)
VEL = 0.09 * V_CAMINAR
PICO = Vector((2.3741, 78.417, 6.05))
RUTA = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ruta_stalker_pico_5D.json"
MEZCLA = 20           # frames que tarda en pasar de la pose del frame 1 al andar calculado
POSTURA = {"spine_1": (-0.50, 0.0, 0.10), "chest_1": (-0.40, 0.0, -0.08), "neck_1": (-0.20, 0.0, 0.10), "head_1": (0.45, 0.12, 0.12),
           "thigh.L_1": (0.14, 0.0, -0.45), "thigh.R_1": (0.14, 0.0, 0.45)}
HUESOS = ("spine_1", "chest_1", "neck_1", "head_1", "thigh.L_1", "thigh.R_1", "shin.L_1", "shin.R_1", "upper_arm.L_1", "upper_arm.R_1", "forearm.L_1", "forearm.R_1")


def ss(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _ruido(fr, freq, seed, dim=0):
    v = math.sin(fr * freq * 1.3 + seed * 7.3 + dim * 3.7) + math.sin(fr * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5 + math.sin(fr * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25
    return v / 1.75


def _fase(fr):
    t = fr - 1 + FASE0
    return 2 * math.pi * t / CICLO + 0.6 * math.sin(2 * math.pi * t / 110.0)


CICLO = 38.0 / V_CAMINAR           # frames por paso medio (la cadencia sube con la velocidad)


def _fcs(idb):
    return [fc for l in idb.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


def _limpia(idb, prefijos=None):
    for fc in _fcs(idb):
        if prefijos is None or fc.data_path.startswith(prefijos):
            for i in range(len(fc.keyframe_points) - 1, -1, -1):
                if fc.keyframe_points[i].co.x >= F0:
                    fc.keyframe_points.remove(fc.keyframe_points[i], fast=True)


def calcular_ruta():
    """A* desde la posicion del frame 1 hasta el pico (reanudable); guarda el JSON"""
    global INICIO, PICO_XY, JSON
    st = bpy.data.objects["the_stalker_1"]
    bpy.context.scene.frame_set(1)
    ruta_mod = globals()
    ruta_mod["INICIO"] = (st.matrix_world.translation.x, st.matrix_world.translation.y)
    ruta_mod["PICO"] = (PICO.x, PICO.y)
    ruta_mod["JSON"] = RUTA
    r = buscar_ruta()
    ruta_mod["PICO"] = Vector((PICO[0], PICO[1], 6.05))
    return r


def _euler_paso(fr, sw):
    ph = _fase(fr)
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
    return E, ph


def caminar_hasta_pico():
    O, sc = bpy.data.objects, bpy.context.scene
    st, ar = O["the_stalker_1"], O["torso_1"]
    PB = ar.pose.bones
    sc.frame_set(1)
    fe = {(f.data_path, f.array_index): f for f in _fcs(st)}
    fa = {(f.data_path, f.array_index): f for f in _fcs(ar)}
    p0 = Vector([fe[("location", i)].evaluate(1) for i in range(3)])
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
    # escalones: tramos de la ruta donde el suelo sube/baja mas de 0.3 m en 0.9 m -> (s_central, altura con signo)
    def z_en(sa):
        return en_ruta(sa).z
    eventos, sx = [], 0.0
    while sx < L - 1.0:
        dz = z_en(sx + 0.9) - z_en(sx)
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
    # avance a tirones y frenada al final (y titubeo ante cada escalon)
    sarr, sv, fr = {1: 0.0}, 0.0, 1
    while sv < L - 0.02 and fr < 4000:
        fr += 1
        rem = L - sv
        cerca = min((abs(sv - e[0]) for e in eventos), default=9.0)
        v = VEL * (0.45 + 0.55 * (0.5 + 0.5 * math.sin(_fase(fr) + 0.6))) * min(1.0, 0.15 + rem / 4.0) * (0.55 if cerca < 0.9 else 1.0)
        sv = min(L, sv + v)
        sarr[fr] = sv
    f_llega = fr
    F_END = f_llega + 30
    for g in range(f_llega + 1, F_END + 1):
        sarr[g] = L
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
            zc += (0.22 * math.sin(math.pi * min(1.0, u * 1.1)) if dz > 0 else -0.05 * math.sin(math.pi * u))      # subir: el cuerpo se eleva sobre el bloque; bajar: se hunde al caer
        st.location = Vector((xy.x, xy.y, zc))
        yr = yaw_en(sarr[fr])
        if yr is not None:
            yaw += ((yr - yaw + math.pi) % (2 * math.pi) - math.pi) * 0.12
        st.rotation_euler = (0, 0, yaw)
        st.keyframe_insert("location", frame=fr)
        st.keyframe_insert("rotation_euler", frame=fr)
    semillas = {n: 100 + i for i, n in enumerate(HUESOS)}
    for fr in range(F0, F_END + 1):
        rem = L - sarr[fr]
        sw = ss(rem / 1.5) * 1.0 if fr > f_llega - 25 else 1.0          # al llegar, el paso se apaga
        E, ph = _euler_paso(fr, sw)
        vw = ventana(fr)
        ry_extra = 0.0
        if vw:
            u, dz, k = vw
            b = math.sin(math.pi * u) ** 1.3
            ld, tr = ("L", "R") if k % 2 == 0 else ("R", "L")
            add = lambda n, dx=0.0, dy=0.0, dzz=0.0: E.__setitem__(n, (E[n][0] + dx, E[n][1] + dy, E[n][2] + dzz))
            if dz > 0:       # SUBIR: la pierna guia sube la rodilla, la otra empuja, el torso se inclina hacia delante y los brazos buscan equilibrio
                lift = b * min(1.0, abs(dz) / 0.8)
                add("thigh.%s_1" % ld, 1.05 * lift); add("shin.%s_1" % ld, -1.35 * lift)
                add("thigh.%s_1" % tr, -0.25 * b); add("shin.%s_1" % tr, -0.45 * b * (1 - u))
                add("spine_1", -0.30 * b); add("chest_1", -0.15 * b); add("head_1", 0.12 * b)
                add("upper_arm.L_1", 0.55 * b, 0, 0.0); add("upper_arm.R_1", 0.55 * b, 0, 0.25 * b)
                ry_extra = -0.10 * b
            else:            # BAJAR: pierna guia tantea, rodillas amortiguan la caida, brazos se abren y el torso se echa atras
                caida = ss((u - 0.45) / 0.2) * (1 - ss((u - 0.75) / 0.25))
                add("thigh.%s_1" % ld, 0.50 * b); add("shin.%s_1" % ld, -0.55 * b)
                add("shin.L_1", -0.85 * caida); add("shin.R_1", -0.85 * caida)
                add("thigh.L_1", 0.35 * caida); add("thigh.R_1", 0.35 * caida)
                add("spine_1", 0.18 * b - 0.25 * caida); add("chest_1", 0.10 * b)
                add("upper_arm.L_1", 0, 0, -0.55 * b); add("upper_arm.R_1", 0, 0, 0.55 * b)
                ry_extra = -0.16 * caida
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
        ry_w = -0.0876 - sw * 0.05 * (0.5 + 0.5 * math.sin(2 * ph)) + 0.01 * _ruido(fr, 0.06, 8, 1)
        rw = Vector((0.04 * _ruido(fr, 0.05, 7, 0) + sw * 0.03 * math.sin(ph), ry_w, sw * 0.04 * math.sin(ph)))
        rw.y += ry_extra
        PB["root_1"].location = r1.lerp(rw, tu)
        PB["root_1"].keyframe_insert("location", frame=fr)
    for idb in (ar, st):
        for fc in _fcs(idb):
            for kp in fc.keyframe_points:
                if kp.co.x >= F0:
                    kp.interpolation = 'LINEAR'
            fc.update()
    sc.frame_set(1)
    return {"escalones": [(round(e[0], 1), round(e[1], 2)) for e in eventos], "ruta_m": round(L, 1), "llega_en_frame": f_llega, "frame_end": F_END, "final": tuple(round(v, 1) for v in ruta[-1])}
