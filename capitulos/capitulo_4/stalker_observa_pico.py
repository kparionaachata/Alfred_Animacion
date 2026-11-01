# -*- coding: utf-8 -*-
"""alfred_cueva_5D.blend: al llegar al pico (f_llega) la criatura SE DETIENE, ACOMODA las extremidades (cada mano y pie se coloca en su punto de apoyo, uno tras otro), MIRA DETALLADAMENTE el pico de piedra
(la cabeza recorre el pico de un extremo a otro y se acerca) y por ultimo ALZA EL PECHO y ROTA LA CABEZA Y LA MANDIBULA HACIA ARRIBA.
Alarga la animacion hasta f_end: las claves de la criatura (armature torso_1 y empty the_stalker_1) quedan congeladas con la pose de f_llega y encima se suma todo lo anterior.
Requiere (ejecutados antes): ruta_stalker_pico.py, stalker_camina_hasta_pico.py, fk_pose.py, stalker_tres_recorridos.py, fk_clearance.py, gateo_terreno.py
Uso: observa_pico_cuerpo()  (una vez)  ->  observa_pico_extremidades(estado) (por tramos, reanudable hasta devolver True)"""
import bpy, math
from mathutils import Vector, Quaternion, Euler

F_LLEGA = 891
F_FIN = 1011
F_ASIENTA = 915            # las cuatro extremidades ya estan colocadas
F_INSPECC1 = 975           # fin de la inspeccion del pico
F_ARRIBA1 = 1005           # cabeza y mandibula arriba del todo
ORDEN = {"HL": 0, "FR": 2, "HR": 6, "FL": 8}          # frame (relativo a la llegada) en que cada extremidad empieza a colocarse
DUR = 10                                               # frames que tarda cada extremidad en colocarse


def _ss(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _fcurves(act):
    for lay in act.layers:
        for st in lay.strips:
            for cb in st.channelbags:
                for fc in cb.fcurves:
                    yield fc


def _congela(act, f0, f1):
    for fc in _fcurves(act):
        v = fc.evaluate(f0)
        ex = {int(round(k.co.x)): k for k in fc.keyframe_points}
        for fr in range(f0 + 1, f1 + 1):
            k = ex.get(fr)
            if k is None:
                fc.keyframe_points.insert(fr, v, options={'FAST'})
            else:
                k.co.y = v
                k.handle_left.y = v
                k.handle_right.y = v
                k.interpolation = 'LINEAR'
        fc.update()
        for k in fc.keyframe_points:
            if k.co.x > f0:
                k.co.y = v
                k.handle_left.y = v
                k.handle_right.y = v
                k.interpolation = 'LINEAR'
        fc.update()


def _escribe_q(n, fr, q):
    for i in range(4):
        fcv = CAD[('pose.bones["%s"].rotation_quaternion' % n, i)]
        kp = KEYS[fcv].get(fr)
        if kp:
            kp.co.y = q[i]
            kp.handle_left.y = q[i]
            kp.handle_right.y = q[i]


def _puntos_pico():
    o = bpy.data.objects["alfred_pico_piedra"]
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    c = sum(pts, Vector()) / len(pts)
    mejor = (0.0, c, c)
    for a in pts:
        for b in pts:
            if (a - b).length > mejor[0]:
                mejor = ((a - b).length, a, b)
    A, B = mejor[1], mejor[2]
    if A.x > B.x:
        A, B = B, A
    return A.lerp(c, 0.15), B.lerp(c, 0.15), c


def _objetivo_mirada(fr, A, B, C):
    """punto que mira la cabeza durante la inspeccion: centro -> extremo A -> extremo B -> centro, acercandose"""
    t = fr - F_LLEGA
    knots = [(F_LLEGA + 12, C), (F_ASIENTA + 8, C), (F_ASIENTA + 20, A), (F_ASIENTA + 30, A), (F_ASIENTA + 45, B), (F_ASIENTA + 52, B), (F_INSPECC1, C)]
    if fr <= knots[0][0]:
        return knots[0][1]
    for (f0, p0), (f1, p1) in zip(knots, knots[1:]):
        if fr <= f1:
            return p0.lerp(p1, _ss((fr - f0) / float(f1 - f0)))
    return knots[-1][1]


def observa_pico_cuerpo():
    """congela la criatura desde f_llega hasta F_FIN y escribe el movimiento del tronco, el cuello y la cabeza (las extremidades se resuelven despues)"""
    NS = bpy.app.driver_namespace
    NS.pop("observa_orig", None)
    sc = bpy.context.scene
    arm = bpy.data.objects["torso_1"]
    emp = bpy.data.objects["the_stalker_1"]
    _congela(arm.animation_data.action, F_LLEGA, F_FIN)
    _congela(emp.animation_data.action, F_LLEGA, F_FIN)
    sc.frame_end = max(sc.frame_end, F_FIN)
    preparar()
    indexar_claves()
    cav = NS["ruta_bvh"][0]
    # punto de apoyo de cada extremidad y donde esta ahora (antes de tocar el tronco)
    tip0 = {k: _punta(F_LLEGA, k, None) for k in NEUTRO}
    P = {k: _neutro_mundo(cav, F_LLEGA, k) for k in NEUTRO}
    NS["obs_extr"] = {"tip0": tip0, "P": P}
    A, B, C = _puntos_pico()
    NS["obs_pico"] = (A, B, C)
    y = FE[("rotation_euler", 2)].evaluate(F_LLEGA)
    right = Vector((math.cos(y), math.sin(y), 0.0))
    base = {}
    for n in ("spine_1", "chest_1", "neck_1", "head_1"):
        base[n] = _q(n, F_LLEGA).copy()
    elev_arriba = 1.15
    for fr in range(F_LLEGA, F_FIN + 1):
        t = fr - F_LLEGA
        a_in = _ss((fr - (F_LLEGA + 4)) / 12.0)                         # empieza a girar la cabeza hacia el pico mientras acomoda las extremidades
        a_ins = _ss((fr - F_ASIENTA) / 10.0) * (1.0 - _ss((fr - (F_INSPECC1 - 6)) / 10.0))      # agachado durante la inspeccion
        a_alto = _ss((fr - F_INSPECC1) / float(F_ARRIBA1 - F_INSPECC1))
        ang = -0.30 * a_ins + 0.55 * a_alto
        ex = {}
        for n, f_ in (("spine_1", 0.2), ("chest_1", 0.35), ("neck_1", 0.45)):
            R = fk(fr, None, [n])[n].to_3x3().to_quaternion()
            ex[n] = R.inverted() @ Quaternion(right, ang * f_) @ R
        M = fk(fr, ex, ["head_1"])["head_1"]
        R3 = M.to_3x3()
        f = (R3 @ Vector((0, 0, -1))).normalized()
        d_pico = (_objetivo_mirada(fr, A, B, C) - M.translation).normalized()
        h = Vector((d_pico.x, d_pico.y, 0.0)).normalized()
        d_arr = (h * math.cos(elev_arriba) + Vector((0, 0, math.sin(elev_arriba)))).normalized()
        fd = (d_pico * (1.0 - a_alto) + d_arr * a_alto).normalized()
        rot = f.rotation_difference(fd)
        if rot.angle > 1.8:
            rot = Quaternion(rot.axis, 1.8)
        rot = Quaternion().slerp(rot, a_in)
        sniff = 0.05 * math.sin(t * 0.8) * a_ins
        rot = Quaternion(right, sniff) @ rot
        Rq = R3.to_quaternion()
        dqh = Rq.inverted() @ rot @ Rq
        for n in ("spine_1", "chest_1", "neck_1"):
            _escribe_q(n, fr, base[n] @ ex[n])
        _escribe_q("head_1", fr, base["head_1"] @ dqh)
    for fc in CAD.values():
        fc.update()
    return {"frames": F_FIN - F_LLEGA + 1}


def observa_pico_extremidades(estado, t_max=40.0):
    """IK de cada extremidad hacia su objetivo (se coloca en su punto de apoyo con un pequeno arco y luego queda plantada), con el tronco ya movido. Reanudable."""
    import time
    t0 = time.time()
    NS = bpy.app.driver_namespace
    preparar()
    indexar_claves()
    cav = NS["ruta_bvh"][0]
    tip0, P = NS["obs_extr"]["tip0"], NS["obs_extr"]["P"]
    prev = estado.setdefault("prev", {k: [0.0, 0.0, 0.0, 0.0] for k in NEUTRO})
    err = estado.setdefault("err", {})
    fr = estado.get("fr", F_LLEGA)
    while fr <= F_FIN and time.time() - t0 < t_max:
        for nombre in NEUTRO:
            tipo, lado = TIPO[nombre]
            n1, n2 = (LIM if tipo == "mano" else LIMP)
            n1, n2 = n1 % lado, n2 % lado
            u = _ss((fr - F_LLEGA - ORDEN[nombre]) / float(DUR))
            tgt = tip0[nombre].lerp(P[nombre], u)
            tgt.z += 0.22 * math.sin(math.pi * u)

            def costo(p_):
                ex = {n1: Euler((p_[0], p_[1], p_[2])).to_quaternion(), n2: Euler((p_[3], 0, 0)).to_quaternion()}
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
            err.setdefault(nombre, []).append((fr, round((_evalua(cav, fr, nombre, ex)[0] - tgt).length, 3)))
            for nn in (n1, n2):
                _escribe_q(nn, fr, _q(nn, fr) @ ex[nn])
        fr += 1
    estado["fr"] = fr
    for fc in CAD.values():
        fc.update()
    return fr > F_FIN
