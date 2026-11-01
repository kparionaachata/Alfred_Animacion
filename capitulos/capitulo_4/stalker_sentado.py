# -*- coding: utf-8 -*-
"""alfred_cueva_5C.blend: the_stalker_1 camina hasta una esquina de la caverna, se sienta con las piernas cruzadas y los brazos cruzados (como Ned Flanders con la camisa de fuerza)
y se queda ahi respirando, mirando al frente con la cabeza ladeada.
Frames: 1-F_CAM caminata (marcha asimetrica como en stalker_camina_pico.py) / F_CAM-F_SIT se detiene, gira de espaldas a la esquina y se sienta / F_SIT-F_ARM cruza los brazos /
        hasta el final reposa con respiracion y micro-movimiento (filtros organicos).
Esquina: paredes en x=40.95 (oeste) e y=-27.66 (norte); la criatura se sienta en (ESQ_X, ESQ_Y) mirando hacia el sureste.
Requiere: stalker_parte_zombie.py ejecutado antes (usa POSTURA, ss, _ruido).    Uso: sentar()    (repetible)
"""
import bpy, math
from mathutils import Vector, Euler, Quaternion

ESQ = Vector((41.75, -28.35, 6.02))       # centro del asiento (suelo)
YAW_SIT = math.radians(-135)              # mira hacia el sureste: la espalda queda contra la esquina
F_CAM, F_SIT, F_ARM = 90, 140, 175
CICLO = 38.0
FIN = 600                 # duracion de la animacion en frames
DIRECTO = True            # True: la animacion empieza ya sentado (frame 1 = pose sentada con los brazos cruzados); False: camina desde donde estaba y se sienta
VEL = 0.085

# pose sentada (rotaciones Euler XYZ de cada hueso, en radianes); se afinan mirando renders
SENTADO = {
    "root_y": -0.90,
    "spine_1": (-0.45, 0.0, 0.05), "chest_1": (-0.35, 0.0, -0.05), "neck_1": (-0.15, 0.0, 0.10), "head_1": (0.40, 0.0, 0.12),
}
# piernas cruzadas y brazos cruzados: cuaterniones resueltos apuntando cada hueso con direcciones en el espacio de la criatura (aim) y leidos de la pose
_Q = {
    "thigh.L_1": [0.7434, 0.5671, 0.0, -0.3545], "thigh.R_1": [0.7434, 0.5671, 0.0, 0.3545],
    "shin.L_1": [0.4256, 0.2966, 0.0, 0.8549], "shin.R_1": [0.4256, 0.2966, 0.0, -0.8549],
    "upper_arm.L_1": [0.8083, 0.5692, -0.0604, -0.1382], "upper_arm.R_1": [0.8061, 0.5729, 0.0598, 0.1357],
    "forearm.L_1": [0.6429, 0.4302, -0.0073, 0.6337], "forearm.R_1": [0.6429, 0.4094, 0.0055, -0.6473],
}
for _n, _q in _Q.items():
    SENTADO[_n] = tuple(Quaternion(_q).to_euler('XYZ'))


def _cl(a, b, t):
    return a + (b - a) * t


def _eul(t):
    return tuple(t)


def _mezcla(a, b, t):
    return tuple(_cl(x, y, t) for x, y in zip(a, b))


def _suelo(sc, dg, x, y, z0):
    p = Vector((x, y, z0 + 1.2))
    for _ in range(8):
        r = sc.ray_cast(dg, p, Vector((0, 0, -1)), distance=6)
        if not r[0]:
            return None
        if r[4].name.startswith("caverna_"):
            return r[1].z
        p = r[1] - Vector((0, 0, 0.01))


def _limpia(idb, prefijos, desde=1):
    a = idb.animation_data.action if idb.animation_data else None
    if not a:
        return
    for l in a.layers:
        for s in l.strips:
            for cb in s.channelbags:
                for fc in cb.fcurves:
                    if prefijos is None or fc.data_path.startswith(prefijos):
                        for i in range(len(fc.keyframe_points) - 1, -1, -1):
                            if fc.keyframe_points[i].co.x >= desde:
                                fc.keyframe_points.remove(fc.keyframe_points[i], fast=True)


def pose_en(fr, p0, yaw0, ruta):
    """devuelve (posicion del empty, yaw, {hueso: euler}, root_y) en el frame fr"""
    sw = ss((fr - 1) / 15.0)
    walk = fr <= F_CAM and not DIRECTO
    ph = 2 * math.pi * (fr - 1) / CICLO + 0.6 * math.sin(2 * math.pi * (fr - 1) / 110.0)
    E = {}
    if walk:
        sL, sR = math.sin(ph), math.sin(ph + 2.5)
        cL, cR = math.cos(ph), math.cos(ph + 2.5)
        sa = math.sin(ph + 3.1)
        E["thigh.L_1"] = (0.14 + sw * 0.55 * sL, sw * 0.12 * sL, -0.45 - sw * 0.2 * max(0.0, sL))
        E["thigh.R_1"] = (0.14 + sw * 0.28 * sR, sw * 0.05 * sR, 0.45 + sw * 0.06 * cR)
        E["shin.L_1"] = (-sw * (0.30 + 1.0 * max(0.0, cL)), 0, sw * 0.08 * sL)
        E["shin.R_1"] = (-sw * (0.60 + 0.25 * max(0.0, cR)), 0, -sw * 0.05 * sR)
        E["upper_arm.L_1"] = (sw * 0.75 * sa, sw * 0.2 * sa, -sw * 0.15)
        E["forearm.L_1"] = (sw * (0.45 + 0.9 * max(0.0, math.sin(ph + 3.7))), 0, sw * 0.10 * math.sin(ph * 0.5))
        E["upper_arm.R_1"] = (sw * (-0.18 + 0.08 * math.sin(ph * 0.5)), 0, sw * (0.30 + 0.20 * math.sin(ph * 0.5 + 1.0)))
        E["forearm.R_1"] = (sw * (1.05 + 0.15 * math.sin(ph * 0.5 + 0.8)), 0, sw * 0.12 * math.sin(ph * 0.5 + 2.0))
        E["spine_1"] = tuple(POSTURA["spine_1"][i] + (0.0, sw * 0.25 * math.sin(ph), sw * (0.12 * math.sin(ph + 1.2) + 0.10 * math.sin(ph * 0.5)))[i] for i in range(3))
        E["chest_1"] = tuple(POSTURA["chest_1"][i] + (0.0, -sw * 0.20 * math.sin(ph + 0.4), sw * 0.08 * math.sin(ph * 0.5 + 2.0))[i] for i in range(3))
        E["neck_1"] = POSTURA["neck_1"]
        E["head_1"] = POSTURA["head_1"]
        # avance a tirones
        v = VEL * (0.45 + 0.55 * (0.5 + 0.5 * math.sin(ph + 0.6))) * ss((fr - 1) / 25.0) * (1.0 - ss((fr - (F_CAM - 18)) / 18.0))
        return v, E, 0.0
    return 0.0, E, 0.0


def sentar():
    O, sc = bpy.data.objects, bpy.context.scene
    st, ar = O["the_stalker_1"], O["torso_1"]
    PB = ar.pose.bones
    sc.frame_set(1)
    dg = bpy.context.evaluated_depsgraph_get()
    p0 = Vector(st.matrix_world.translation)
    yaw0 = st.matrix_world.to_euler().z
    sc.frame_end = FIN
    R1 = {n: tuple(PB[n].rotation_quaternion.to_euler('XYZ')) for n in ("thigh.L_1", "thigh.R_1", "shin.L_1", "shin.R_1", "spine_1", "chest_1", "neck_1", "head_1", "upper_arm.L_1", "upper_arm.R_1", "forearm.L_1", "forearm.R_1")}
    R1["root_y"] = PB["root_1"].location[1]
    REPOSO.clear()
    REPOSO.update(pose_en(F_CAM, p0, yaw0, None)[1] if not DIRECTO else {k: v for k, v in SENTADO.items() if k != 'root_y'})
    REPOSO["root_y"] = -0.0876
    huesos = ("spine_1", "chest_1", "neck_1", "head_1", "thigh.L_1", "thigh.R_1", "shin.L_1", "shin.R_1", "upper_arm.L_1", "upper_arm.R_1", "forearm.L_1", "forearm.R_1", "root_1",
              "jaw_1", "tent_finger", "tent_thumb")
    _limpia(ar, tuple('pose.bones["%s' % h for h in huesos))
    _limpia(st, None)
    for n in ("spine_1", "chest_1", "neck_1", "head_1", "thigh.L_1", "thigh.R_1", "shin.L_1", "shin.R_1", "upper_arm.L_1", "upper_arm.R_1", "forearm.L_1", "forearm.R_1"):
        PB[n].rotation_mode = 'QUATERNION'
    # ruta de la caminata: recta hasta el punto de aproximacion (1.1 m delante del asiento, sobre la diagonal de salida)
    f_sit = Vector((-math.sin(YAW_SIT), math.cos(YAW_SIT), 0))
    aprox = ESQ + f_sit * 1.1
    D = Vector((aprox.x - p0.x, aprox.y - p0.y, 0))
    dist = D.length
    D.normalize()
    yaw_ruta = math.atan2(-D.x, D.y)
    pos, s, zprev = {}, 0.0, p0.z
    for fr in range(1, FIN + 1):
        if fr <= F_CAM:
            v, E, _ = pose_en(fr, p0, yaw0, None)
            s += v
        pos[fr] = s
    esc = dist / max(s, 1e-6)                      # escala para llegar justo al punto de aproximacion
    for fr in pos:
        pos[fr] = min(dist, pos[fr] * esc)
    for fr in range(1, FIN + 1):
        if DIRECTO:
            xy = Vector(ESQ)
            yaw = YAW_SIT
        elif fr <= F_CAM:
            t = pos[fr] / dist
            xy = p0 + D * pos[fr]
            yaw = _cl(yaw0, yaw_ruta, ss((fr - 1) / 20.0))
        else:
            t = ss((fr - F_CAM) / float(F_SIT - F_CAM))
            xy = aprox.lerp(ESQ, t)
            yaw = _cl(yaw_ruta, YAW_SIT, ss((fr - F_CAM) / 25.0))
        z = _suelo(sc, dg, xy.x, xy.y, zprev)
        zprev = z if z is not None else zprev
        st.location = Vector((xy.x, xy.y, zprev))
        st.rotation_euler = (0, 0, yaw)
        if fr > 1 or DIRECTO:
            st.keyframe_insert("location", frame=fr)
            st.keyframe_insert("rotation_euler", frame=fr)
    # huesos
    for fr in range(1, FIN + 1):
        v, E, _ = pose_en(fr, p0, yaw0, None)
        if DIRECTO:
            tsit = 1.0
            tarm = 1.0
        elif fr <= F_CAM:
            tsit = 0.0
            tarm = 0.0
        else:
            tsit = ss((fr - F_CAM) / float(F_SIT - F_CAM))
            tarm = ss((fr - F_SIT) / float(F_ARM - F_SIT))
        # transicion caminar -> sentado
        for n in ("thigh.L_1", "thigh.R_1", "shin.L_1", "shin.R_1", "spine_1", "chest_1", "neck_1", "head_1", "upper_arm.L_1", "upper_arm.R_1", "forearm.L_1", "forearm.R_1"):
            if fr <= F_CAM and not DIRECTO:
                e = _mezcla(R1[n], E[n], ss((fr - 1) / 12.0))
            else:
                base = REPOSO[n]
                objetivo = SENTADO[n]
                if n.startswith(("upper_arm", "forearm")):
                    e = _mezcla(base, objetivo, tarm)
                else:
                    e = _mezcla(base, objetivo, tsit)
            # organicos: respiracion y micro-movimiento
            amp = 0.025 if n in ("spine_1", "chest_1") else 0.02
            sd = abs(hash(n)) % 97
            org = (amp * math.sin(2 * math.pi * 0.012 * fr + sd) + 0.5 * amp * _ruido(fr, 0.06, sd, 0), 0.4 * amp * _ruido(fr, 0.06, sd, 1), 0.8 * amp * _ruido(fr, 0.06, sd, 2))
            if fr > F_SIT and n in ("thigh.L_1", "thigh.R_1", "shin.L_1", "shin.R_1"):
                org = tuple(0.3 * o for o in org)
            PB[n].rotation_quaternion = (Euler(e).to_quaternion() @ Euler(org).to_quaternion())
            if fr > 1 or DIRECTO:
                PB[n].keyframe_insert("rotation_quaternion", frame=fr)
        if DIRECTO:
            ry = SENTADO["root_y"]
        else:
            ry = _cl(R1["root_y"] if fr <= F_CAM else REPOSO["root_y"], SENTADO["root_y"], tsit) if fr > F_CAM else _cl(R1["root_y"], REPOSO["root_y"], ss((fr - 1) / 12.0))
        PB["root_1"].location = (0, ry, 0)
        if fr > 1 or DIRECTO:
            PB["root_1"].keyframe_insert("location", frame=fr)
    for idb in (ar, st):
        for l in idb.animation_data.action.layers:
            for stp in l.strips:
                for cb in stp.channelbags:
                    for fc in cb.fcurves:
                        for kp in fc.keyframe_points:
                            if kp.co.x >= 1:
                                kp.interpolation = 'LINEAR'
                        fc.update()
    sc.frame_set(1)
    return {"dist": round(dist, 2), "yaw_ruta": round(math.degrees(yaw_ruta))}


REPOSO = {}


def capturar_reposo():
    """pose en el frame 1 (fin de la caminata anterior): punto de partida de la transicion"""
    ar = bpy.data.objects["torso_1"]
    bpy.context.scene.frame_set(1)
    for n in ("thigh.L_1", "thigh.R_1", "shin.L_1", "shin.R_1", "spine_1", "chest_1", "neck_1", "head_1", "upper_arm.L_1", "upper_arm.R_1", "forearm.L_1", "forearm.R_1"):
        REPOSO[n] = tuple(ar.pose.bones[n].rotation_quaternion.to_euler('XYZ'))
    REPOSO["root_y"] = ar.pose.bones["root_1"].location[1]
