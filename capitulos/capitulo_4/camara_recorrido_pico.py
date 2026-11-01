# -*- coding: utf-8 -*-
"""alfred_cueva_5C.blend: camara cinematografica que graba a the_stalker_1 desde que se levanta (F0) hasta el final del recorrido hacia el pico (F_END).
Orbita relativa a su rumbo (de frente y desde abajo -> costado -> espalda -> costado), radio, altura y focal cambiantes, siempre apuntando al pecho/cabeza.
La camara nunca atraviesa la caverna: cada frame se lanza un rayo del objetivo a la posicion deseada y, si choca, la camara se acerca antes del bloque; despues se aparta de
las paredes/techo/suelo cercanos (rayos en 6 direcciones) y se vuelve a comprobar. Requiere ruta_stalker_pico.py (usa su BVH de la caverna).
Uso: exec(ruta_stalker_pico.py); exec(este); camara_recorrido()    (repetible)
"""
import bpy, math
from mathutils import Vector, Euler

F0, F_END = 601, 1000
HOLGURA = 0.45


def _ss(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _cl(a, b, t):
    return a + (b - a) * t


def _fcs(idb):
    return {(f.data_path, f.array_index): f for l in idb.animation_data.action.layers for s in l.strips for cb in s.channelbags for f in cb.fcurves}


def camara_recorrido():
    sc = bpy.context.scene
    O = bpy.data.objects
    st, cam = O["the_stalker_1"], sc.camera
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = bpy.app.driver_namespace.get("ruta_bvh") or _bvh(dg)
    cav = bvh[0]
    fs = _fcs(st)
    fc = _fcs(cam)
    for d in (fc,) + ((_fcs(cam.data),) if cam.data.animation_data and cam.data.animation_data.action else ()):
        for f in d.values():
            for i in range(len(f.keyframe_points) - 1, -1, -1):
                if f.keyframe_points[i].co.x >= F0:
                    f.keyframe_points.remove(f.keyframe_points[i], fast=True)
    c0 = Vector([fc[("location", i)].evaluate(F0 - 1) for i in range(3)])
    lens0 = _fcs(cam.data)[("lens", 0)].evaluate(F0 - 1) if cam.data.animation_data and cam.data.animation_data.action else cam.data.lens
    P = lambda f: Vector([fs[("location", i)].evaluate(f) for i in range(3)])
    yaw = lambda f: fs[("rotation_euler", 2)].evaluate(f)

    def libre(obj, dest):
        """acerca dest hacia obj hasta antes del primer choque con la caverna"""
        d = dest - obj
        L = d.length
        r = cav.ray_cast(obj, d / L, L + HOLGURA)
        if r[0] is not None:
            return obj + d / L * max(0.3, r[3] - HOLGURA)
        return dest

    def aparta(p, obj):
        for _ in range(3):
            for ax in (Vector((1, 0, 0)), Vector((-1, 0, 0)), Vector((0, 1, 0)), Vector((0, -1, 0)), Vector((0, 0, 1)), Vector((0, 0, -1))):
                r = cav.ray_cast(p, ax, HOLGURA)
                if r[0] is not None:
                    p = p - ax * (HOLGURA - r[3] + 0.02)
        return libre(obj, p)

    n = F_END - F0 + 1
    deseada = {}
    for fr in range(F0 - 1, F_END + 1):
        u = (fr - F0) / float(n - 1)
        pos = P(fr)
        y = yaw(fr)
        f = Vector((-math.sin(y), math.cos(y), 0))
        r_ = Vector((math.cos(y), math.sin(y), 0))
        th = math.radians(_cl(165, -165, _ss(u)) + 25 * math.sin(2 * math.pi * u * 3))      # 0 = detras, 180 = de frente
        R = 4.2 + 1.8 * math.sin(2 * math.pi * u * 2 + 0.6) + 0.6 * math.sin(2 * math.pi * u * 5)
        H = 1.5 + 1.1 * math.sin(2 * math.pi * u * 2.5 - 0.5) + (-0.9 if u < 0.12 else 0.0) * (1 - _ss(u / 0.12))
        obj = pos + Vector((0, 0, 1.6))
        mejor = None
        for dd in (0, 25, -25, 50, -50, 80, -80, 120, -120, 160, 180):
            for kR in (1.0, 0.75, 0.55):
                t2 = th + math.radians(dd)
                d = -f * math.cos(t2) + r_ * math.sin(t2)
                dest = pos + d * R * kR + Vector((0, 0, (H + 0.2) * (1.0 if kR == 1.0 else 0.8)))
                dest[2] = max(dest[2], pos.z + 0.4)
                v = dest - obj
                rr = cav.ray_cast(obj, v.normalized(), v.length + HOLGURA)
                libre_ok = rr[0] is None
                if libre_ok and all(cav.ray_cast(dest, ax, HOLGURA)[0] is None for ax in (Vector((1, 0, 0)), Vector((-1, 0, 0)), Vector((0, 1, 0)), Vector((0, -1, 0)), Vector((0, 0, 1)), Vector((0, 0, -1)))):
                    mejor = dest
                    break
            if mejor is not None:
                break
        if mejor is None:                                  # sin hueco: lo mas cerca posible, sobre la criatura
            mejor = obj + Vector((0, 0, 0.8)) + f * 0.2
        dest = mejor
        deseada[fr] = (obj, dest, 30 + 10 * math.sin(2 * math.pi * u * 3 + 1.0) + (4 if u > 0.5 else 0) - 6 * math.sin(math.pi * u))
    # suavizado temporal de la posicion relativa al objetivo, luego choque
    rel = {fr: deseada[fr][1] - deseada[fr][0] for fr in deseada}
    suave = {}
    prev = c0 - deseada[F0 - 1][0]
    for fr in range(F0, F_END + 1):
        t = _ss((fr - F0) / 45.0)
        tgt = prev.lerp(rel[fr], 0.25)
        prev = tgt
        suave[fr] = c0 - deseada[F0 - 1][0] if False else tgt
    ult = c0
    prev_e = Euler([fc[("rotation_euler", i)].evaluate(F0 - 1) for i in range(3)])
    obj_prev = deseada[F0 - 1][0]
    for fr in range(F0, F_END + 1):
        obj, dest, lens = deseada[fr]
        k = _ss((fr - F0) / 40.0)                       # los primeros frames parte de la camara que ya habia
        p = ult.lerp(obj + suave[fr], 0.35 if fr > F0 + 40 else 0.12 + 0.2 * k)
        p = aparta(p, obj)
        ult = p
        e = (obj - p).to_track_quat('-Z', 'Y').to_euler('XYZ', prev_e)
        prev_e = e
        for i in range(3):
            fc[("location", i)].keyframe_points.insert(fr, p[i], options={'FAST'})
            fc[("rotation_euler", i)].keyframe_points.insert(fr, e[i], options={'FAST'})
        cam.data.lens = _cl(lens0, lens, k)
        cam.data.keyframe_insert("lens", frame=fr)
    for f in fc.values():
        f.update()
    # comprobacion final: la camara dentro de un bloque (rayo hacia fuera en 6 direcciones a menos de 0.2 en todas) o con choque hasta el objetivo
    malos = 0
    for fr in range(F0, F_END + 1):
        p = Vector([fc[("location", i)].evaluate(fr) for i in range(3)])
        obj = deseada[fr][0]
        d = obj - p
        if cav.ray_cast(p, d.normalized(), d.length)[0] is not None:
            malos += 1
    return {"frames": n, "sin_linea_de_vista": malos}
