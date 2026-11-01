# -*- coding: utf-8 -*-
"""alfred_cueva_5C.blend: despues de estar sentado (hasta F0-1) the_stalker_1 descruza brazos y piernas, se levanta y camina hacia el pico (alfred_pico_piedra)
con el andar antinatural y asimetrico de stalker_camina_pico.py (pierna izquierda larga, derecha corta, brazo derecho rigido, tronco retorcido, organicos).
Frames F0..F_END. F0-F_UP: se levanta (la pose sentada se mezcla con la de pie y gira hacia el pico); desde F_UP el avance es a tirones segun la fase del paso.
Uso: exec(open(ruta, encoding="utf8").read()); levantar_y_caminar()    (repetible)
"""
import bpy, math, json
from mathutils import Vector, Euler, Quaternion

F0, F_UP, F_END = 601, 650, 1000
CICLO = 38.0
VEL = 0.09
PICO = Vector((2.4, 78.4, 6.05))
RUTA = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ruta_stalker_pico.json"      # la genera ruta_stalker_pico.py (A* sin atravesar la caverna)
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
    t = fr - F_UP
    return 2 * math.pi * t / CICLO + 0.6 * math.sin(2 * math.pi * t / 110.0)


def _fcs(idb):
    a = idb.animation_data.action
    return [fc for l in a.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


def _limpia(idb, prefijos=None):
    for fc in _fcs(idb):
        if prefijos is None or fc.data_path.startswith(prefijos):
            for i in range(len(fc.keyframe_points) - 1, -1, -1):
                if fc.keyframe_points[i].co.x >= F0:
                    fc.keyframe_points.remove(fc.keyframe_points[i], fast=True)


def _caminar_euler(fr):
    """rotaciones Euler del paso (las de stalker_camina_pico.py) en el frame fr; sw = entrada gradual del movimiento"""
    ph = _fase(fr)
    sw = ss((fr - F_UP) / 20.0)
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
    E["head_1"] = (POSTURA["head_1"][0], POSTURA["head_1"][1] + sw * 0.0, POSTURA["head_1"][2] + sw * 0.18 * math.sin(ph * 0.5 + 2.0))
    E["spine_1"] = tuple(POSTURA["spine_1"][i] + (0.0, sw * 0.25 * math.sin(ph), sw * (0.12 * math.sin(ph + 1.2) + 0.10 * math.sin(ph * 0.5)))[i] for i in range(3))
    E["chest_1"] = tuple(POSTURA["chest_1"][i] + (0.0, -sw * 0.20 * math.sin(ph + 0.4), sw * 0.08 * math.sin(ph * 0.5 + 2.0))[i] for i in range(3))
    return E, sw, ph


def levantar_y_caminar():
    O, sc = bpy.data.objects, bpy.context.scene
    st, ar = O["the_stalker_1"], O["torso_1"]
    PB = ar.pose.bones
    sc.frame_end = max(sc.frame_end, F_END)
    # estado sentado en F0-1 (antes de borrar nada)
    q_sit = {n: Quaternion([next(fc for fc in _fcs(ar) if fc.data_path == 'pose.bones["%s"].rotation_quaternion' % n and fc.array_index == i).evaluate(F0 - 1) for i in range(4)]) for n in HUESOS}
    ry_sit = next(fc for fc in _fcs(ar) if fc.data_path == 'pose.bones["root_1"].location' and fc.array_index == 1).evaluate(F0 - 1)
    p0 = Vector([next(fc for fc in _fcs(st) if fc.data_path == "location" and fc.array_index == i).evaluate(F0 - 1) for i in range(3)])
    yaw0 = next(fc for fc in _fcs(st) if fc.data_path == "rotation_euler" and fc.array_index == 2).evaluate(F0 - 1)
    ruta = [Vector(p) for p in json.load(open(RUTA))]
    ruta[0] = Vector((p0.x, p0.y, ruta[0].z))
    acum = [0.0]
    for i in range(1, len(ruta)):
        acum.append(acum[-1] + (ruta[i].xy - ruta[i - 1].xy).length)

    def en_ruta(sa):
        sa = max(0.0, min(acum[-1], sa))
        i = max(j for j in range(len(acum)) if acum[j] <= sa)
        if i >= len(ruta) - 1:
            return ruta[-1], (ruta[-1] - ruta[-2]).xy.normalized()
        t = (sa - acum[i]) / max(1e-6, acum[i + 1] - acum[i])
        return ruta[i].lerp(ruta[i + 1], t), (ruta[i + 1] - ruta[i]).xy.normalized()

    def yaw_ruta_en(sa):
        a_ = en_ruta(sa)[0]
        b_ = en_ruta(sa + 1.8)[0]
        d_ = (b_ - a_).xy
        return math.atan2(-d_.x, d_.y) if d_.length > 1e-4 else None
    yaw_ruta = yaw_ruta_en(0.0)
    _limpia(ar, tuple('pose.bones["%s"]' % h for h in HUESOS + ("root_1",)))
    _limpia(st)
    # avance a tirones (arco recorrido sobre la ruta)
    sarr, sv = {F0 - 1: 0.0}, 0.0
    for fr in range(F0, F_END + 1):
        if fr > F_UP:
            ph = _fase(fr)
            sv += VEL * (0.45 + 0.55 * (0.5 + 0.5 * math.sin(ph + 0.6))) * ss((fr - F_UP) / 25.0)
        sarr[fr] = sv
    zs = {fr: en_ruta(sv)[0].z for fr, sv in sarr.items()}
    st.rotation_mode = 'XYZ'
    yaw_prev = yaw0
    for fr in range(F0, F_END + 1):
        w = [zs[g] for g in range(max(F0 - 1, fr - 4), min(F_END, fr + 4) + 1)]
        xy = en_ruta(sarr[fr])[0]
        st.location = Vector((xy.x, xy.y, sum(w) / len(w)))
        yr = yaw_ruta_en(sarr[fr])
        yr = yaw_ruta if yr is None else yr
        if fr <= F_UP:
            yaw_prev = yaw0 + (yaw_ruta - yaw0) * ss((fr - F0) / float(F_UP - F0))
        else:
            yaw_prev += ((yr - yaw_prev + math.pi) % (2 * math.pi) - math.pi) * 0.12
        st.rotation_euler = (0, 0, yaw_prev)
        st.keyframe_insert("location", frame=fr)
        st.keyframe_insert("rotation_euler", frame=fr)
    semillas = {n: 100 + i for i, n in enumerate(HUESOS)}
    for fr in range(F0, F_END + 1):
        E, sw, ph = _caminar_euler(fr)
        tu = ss((fr - F0 + 1) / float(F_UP - F0 + 1))           # 0 = sentado, 1 = de pie
        for n in HUESOS:
            amp = 0.03
            resp = 0.03 * math.sin(2 * math.pi * 0.012 * fr + 1) if n in ("spine_1", "chest_1") else 0.0
            sd = semillas[n]
            ex = E[n][0] + resp + amp * _ruido(fr, 0.07, sd, 0)
            ey = E[n][1] + amp * 0.6 * _ruido(fr, 0.07, sd, 1)
            ez = E[n][2] + amp * 0.8 * _ruido(fr, 0.07, sd, 2)
            qw = Euler((ex, ey, ez)).to_quaternion()
            PB[n].rotation_quaternion = q_sit[n].slerp(qw, tu) if tu < 1.0 else qw
            PB[n].keyframe_insert("rotation_quaternion", frame=fr)
        rn = lambda sd, a, f, d: a * _ruido(fr, f, sd, d)
        ry_w = -0.0876 - sw * 0.05 * (0.5 + 0.5 * math.sin(2 * ph)) + rn(8, 0.01, 0.06, 1)
        PB["root_1"].location = (rn(7, 0.02, 0.05, 0) * 2 + sw * 0.03 * math.sin(ph) if tu >= 1.0 else 0.0,
                                 ry_sit + (ry_w - ry_sit) * tu,
                                 sw * 0.04 * math.sin(ph))
        PB["root_1"].keyframe_insert("location", frame=fr)
    for idb in (ar, st):
        for fc in _fcs(idb):
            for kp in fc.keyframe_points:
                if kp.co.x >= F0:
                    kp.interpolation = 'LINEAR'
            fc.update()
    sc.frame_set(F0)
    return {"origen": tuple(round(v, 2) for v in p0), "yaw_ruta_grados": round(math.degrees(yaw_ruta)), "recorrido_m": round(sv, 1), "ruta_m": round(acum[-1], 1)}
