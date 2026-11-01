# -*- coding: utf-8 -*-
"""alfred_cueva_5D.blend: desde que empieza a correr, the_stalker_1 gira la cabeza para MIRAR A ALFRED (cuello de Alfred, fijo en la salida); la mandibula inferior (neck_front_1) y
jaw_1 son hijas de head_1 y la siguen. Rotacion minima de la cara (eje local -Z de head_1) hacia la direccion horizontal de Alfred (cabeceo fijo `elev`: mira al frente, no hacia arriba), limitada a LIM rad y suavizada en el tiempo; la mirada entra gradualmente (30 frames).
Se SUMA a las claves de head_1 (ejecutar despues de recorrido_tres_tramos y de las correcciones de brazos/piernas; si se repite hay que regenerar primero el recorrido).
Requiere fk_clearance.py ejecutado (fk, _q, CAD, KEYS, preparar, indexar_claves).   Uso: mirar_alfred(f_ini, f_fin)"""
import bpy, math
from mathutils import Vector, Quaternion

ALFRED = Vector((0.59, 83.9, 67.28))      # Neck_alfred (Alfred esta quieto en la salida)
LIM = 1.1


def _ss(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def mirar_alfred(f_ini, f_fin, lim=LIM, sigma=3.0, elev=0.12):
    preparar()
    indexar_claves()
    dv = {}
    for fr in range(f_ini, f_fin + 1):
        M = fk(fr, None, ["head_1"])["head_1"]
        R = M.to_3x3()
        f = (R @ Vector((0, 0, -1))).normalized()                    # la cara de la criatura
        d = ALFRED - M.translation
        if elev is None:
            fd = d.normalized()
        else:                                                           # solo gira hacia Alfred en horizontal; el cabeceo se queda mirando al frente (elev rad sobre la horizontal)
            h = Vector((d.x, d.y, 0.0)).normalized()
            fd = (h * math.cos(elev) + Vector((0, 0, math.sin(elev)))).normalized()
        rot = f.rotation_difference(fd)
        if rot.angle > lim:
            rot = Quaternion(rot.axis, lim)
        rot = Quaternion().slerp(rot, _ss((fr - f_ini) / 30.0))
        Rq = R.to_quaternion()
        dq = Rq.inverted() @ rot @ Rq                               # en el sistema local del hueso: q_nuevo = q_base @ dq
        ax, an = dq.to_axis_angle()
        dv[fr] = ax * an
    frs = sorted(dv)
    K = int(3 * sigma)
    w = [math.exp(-0.5 * (i / sigma) ** 2) for i in range(-K, K + 1)]
    out = {}
    for fr in frs:
        acc = Vector()
        tw = 0.0
        for i, wi in zip(range(-K, K + 1), w):
            g = min(frs[-1], max(frs[0], fr + i))
            acc += dv[g] * wi
            tw += wi
        out[fr] = acc / tw
    for fr in frs:
        v = out[fr]
        dq = Quaternion(v.normalized(), v.length) if v.length > 1e-6 else Quaternion()
        q = _q("head_1", fr) @ dq
        for i in range(4):
            fc = CAD[('pose.bones["head_1"].rotation_quaternion', i)]
            kp = KEYS[fc][fr]
            kp.co.y = q[i]
            kp.handle_left.y = q[i]
            kp.handle_right.y = q[i]
    for fc in CAD.values():
        fc.update()
    return {"frames": len(frs), "giro_max_rad": round(max(o.length for o in out.values()), 2)}
