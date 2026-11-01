# -*- coding: utf-8 -*-
"""alfred_cueva_5D.blend: camara cinematografica que graba a the_stalker_1 en TODO momento (frame 2 al final): camina, corre, gatea, llega al pico, lo observa y mira hacia arriba.
Orbita relativa a su rumbo (de frente -> costado -> espalda -> costado -> de frente y desde abajo al final), radio, altura y focal que cambian segun la etapa; siempre apunta al pecho/cabeza.
Cada golpe a un zombie (GOLPES) acerca un poco la camara. La camara nunca atraviesa la caverna: se lanza un rayo del objetivo a la posicion deseada y, si choca, se prueban otros angulos/radios;
despues se aparta de paredes/techo/suelo cercanos (rayos en 6 direcciones). Requiere ruta_stalker_pico.py (BVH de la caverna) ejecutado.
Uso: exec(ruta_stalker_pico.py); exec(este); camara_seguimiento()    (repetible)"""
import bpy, math
from mathutils import Vector, Euler

F0, F_END = 2, 1011
F_CORRE, F_GATEA, F_LLEGA, F_ARRIBA0, F_ARRIBA1 = 458, 686, 891, 975, 1005
GOLPES_F = (105, 205, 305, 405)
F_ZENIT0, F_ZENIT1 = 950, 990        # al mirar hacia arriba la camara sube y lo graba desde arriba
HOLGURA = 0.45
# angulo de la camara respecto al rumbo (grados; 0 = detras, 180 = de frente), por frames clave
TH = [(2, 165), (200, 110), (400, 55), (560, 10), (686, -40), (800, -100), (891, -140), (960, -160), (1011, -178)]
RR = [(2, 6.0), (250, 7.0), (458, 7.5), (686, 6.5), (800, 7.5), (891, 6.5), (960, 6.0), (1011, 6.5)]
HH = [(2, 1.2), (250, 2.2), (458, 2.0), (686, 1.2), (800, 1.6), (891, 0.9), (960, 0.6), (1011, 0.6)]


def _ss(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _cl(a, b, t):
    return a + (b - a) * t


def _perfil(ks, fr):
    if fr <= ks[0][0]:
        return ks[0][1]
    for (a, va), (b, vb) in zip(ks, ks[1:]):
        if fr <= b:
            return _cl(va, vb, _ss((fr - a) / float(b - a)))
    return ks[-1][1]


def _fcs(idb):
    return {(f.data_path, f.array_index): f for l in idb.animation_data.action.layers for s in l.strips for cb in s.channelbags for f in cb.fcurves}


class _Obst:
    """caverna + mallas de superficie (ocultas en el visor pero que SI salen en el render): rayos contra todas y prueba de 'dentro de un solido' por paridad de rayos"""

    def __init__(self, bvhs, solidos):
        self.bvhs = bvhs
        self.solidos = solidos

    def ray_cast(self, o, d, L):
        mejor = (None, None, None, None)
        for b in self.bvhs:
            r = b.ray_cast(o, d, L)
            if r[0] is not None and (mejor[0] is None or r[3] < mejor[3]):
                mejor = r
        return mejor

    def dentro(self, p):
        for b in self.solidos:
            n = 0
            for d in (Vector((0.3, 0.5, 1)).normalized(), Vector((1, 0.2, 0.1)).normalized(), Vector((-0.4, 1, 0.2)).normalized()):
                k, q = 0, p.copy()
                while True:
                    r = b.ray_cast(q, d)
                    if r[0] is None:
                        break
                    k += 1
                    q = r[0] + d * 1e-4
                n += k % 2
            if n >= 2:
                return True
        return False


def _obstaculos():
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    sol = []
    for nombre in ("cueva_superficie_este", "cueva_superficie_oeste"):
        o = bpy.data.objects.get(nombre)
        if o is None or o.hide_render:
            continue
        e = o.evaluated_get(dg)
        me = e.to_mesh()
        sol.append(BVHTree.FromPolygons([e.matrix_world @ v.co for v in me.vertices], [tuple(p.vertices) for p in me.polygons]))
        e.to_mesh_clear()
    return _Obst([bpy.app.driver_namespace["ruta_bvh"][0]] + sol, sol)


def _volumen(paso=6):
    """centro y radio de encuadre de la criatura (todas sus mallas) cada `paso` frames, interpolados; radio = media diagonal de la caja * 0.85 + 0.2"""
    sc = bpy.context.scene
    st = bpy.data.objects["the_stalker_1"]

    def desc(o):
        for c in o.children:
            yield c
            yield from desc(c)
    ms = [o for o in desc(st) if o.type == 'MESH']
    f_ant = sc.frame_current
    mu = {}
    for fr in sorted(set(list(range(F0 - 1, F_END + 1, paso)) + [F_END])):
        sc.frame_set(fr)
        dg = bpy.context.evaluated_depsgraph_get()
        mn, mx = Vector((1e9,) * 3), Vector((-1e9,) * 3)
        for o in ms:
            e = o.evaluated_get(dg)
            for c in e.bound_box:
                w = e.matrix_world @ Vector(c)
                for i in range(3):
                    mn[i], mx[i] = min(mn[i], w[i]), max(mx[i], w[i])
        mu[fr] = ((mn + mx) / 2, (mx - mn).length * 0.5 * 0.85 + 0.2)
    sc.frame_set(f_ant)
    ks = sorted(mu)
    out = {}
    for fr in range(F0 - 1, F_END + 1):
        b = next((k for k in ks if k >= fr), ks[-1])
        a = max([k for k in ks if k <= fr] or [ks[0]])
        t = 0.0 if b == a else (fr - a) / float(b - a)
        out[fr] = (mu[a][0].lerp(mu[b][0], t), _cl(mu[a][1], mu[b][1], t))
    return out


def camara_seguimiento():
    sc = bpy.context.scene
    O = bpy.data.objects
    st, cam = O["the_stalker_1"], sc.camera
    cav = _obstaculos()
    fs = _fcs(st)
    fc = _fcs(cam)
    fl = _fcs(cam.data)
    for d in (fc, fl):
        for f in d.values():
            for i in range(len(f.keyframe_points) - 1, -1, -1):
                if f.keyframe_points[i].co.x >= F0:
                    f.keyframe_points.remove(f.keyframe_points[i], fast=True)
    for f in fl.values():
        if f.data_path == "lens":
            for i in range(len(f.keyframe_points) - 1, -1, -1):
                if f.keyframe_points[i].co.x >= F0 - 1:
                    f.keyframe_points.remove(f.keyframe_points[i], fast=True)
    vol = _volumen()
    c0 = Vector([fc[("location", i)].evaluate(F0 - 1) for i in range(3)])
    lens0 = 38.0
    P = lambda f: Vector([fs[("location", i)].evaluate(f) for i in range(3)])
    yaw = lambda f: fs[("rotation_euler", 2)].evaluate(f)

    def aparta(p, obj):
        ejes = (Vector((1, 0, 0)), Vector((-1, 0, 0)), Vector((0, 1, 0)), Vector((0, -1, 0)), Vector((0, 0, 1)), Vector((0, 0, -1)))
        for _ in range(3):
            for ax in ejes:
                r = cav.ray_cast(p, ax, HOLGURA)
                if r[0] is not None:
                    p = p - ax * (HOLGURA - r[3] + 0.02)
        d = p - obj
        L = d.length
        r = cav.ray_cast(obj, d / L, L + HOLGURA)
        if r[0] is not None:
            return obj + d / L * max(0.3, r[3] - HOLGURA)
        return p

    ejes = (Vector((1, 0, 0)), Vector((-1, 0, 0)), Vector((0, 1, 0)), Vector((0, -1, 0)), Vector((0, 0, 1)), Vector((0, 0, -1)))
    deseada = {}
    for fr in range(F0 - 1, F_END + 1):
        pos = P(fr)
        y = yaw(fr)
        f = Vector((-math.sin(y), math.cos(y), 0))
        r_ = Vector((math.cos(y), math.sin(y), 0))
        th = math.radians(_perfil(TH, fr) + 8 * math.sin(fr / 37.0))
        R = _perfil(RR, fr) + 0.5 * math.sin(fr / 53.0 + 0.6)
        H = _perfil(HH, fr)
        golpe = max([math.exp(-((fr - g - 6) / 14.0) ** 2) for g in GOLPES_F])
        R -= 0.5 * golpe
        # altura del objetivo: de pie 1.6, corriendo 1.3, a cuatro patas 1.0, y al final sigue a la cabeza que se alza
        oz = _cl(1.6, 1.3, _ss((fr - (F_CORRE - 30)) / 60.0))
        oz = _cl(oz, 1.0, _ss((fr - (F_GATEA - 20)) / 40.0))
        oz = _cl(oz, 1.1, _ss((fr - F_LLEGA) / 10.0)) + 0.3 * _ss((fr - F_ARRIBA0) / float(F_ARRIBA1 - F_ARRIBA0))
        obj = vol[fr][0]
        mejor = None
        for mind in (4.5, 3.2, 0.0):                       # primero lejos (se ve entera), si no hay hueco mas cerca
            for dd in (0, 25, -25, 50, -50, 80, -80, 120, -120, 160, 180):
                for kR, hk in ((1.0, 1.0), (0.75, 1.0), (0.55, 1.0), (1.0, 2.2), (0.75, 2.2), (1.0, 3.5), (0.75, 3.5), (0.55, 2.2)):
                    t2 = th + math.radians(dd)
                    d = -f * math.cos(t2) + r_ * math.sin(t2)
                    dest = pos + d * R * kR + Vector((0, 0, (H * hk + 0.2) * (1.0 if kR == 1.0 else 0.8)))
                    dest[2] = max(dest[2], pos.z + 0.95)
                    v = dest - obj
                    if v.length >= mind and not cav.dentro(dest) and cav.ray_cast(obj, v.normalized(), v.length + HOLGURA)[0] is None and all(cav.ray_cast(dest, ax, HOLGURA)[0] is None for ax in ejes):
                        mejor = dest
                        break
                if mejor is not None:
                    break
            if mejor is not None:
                break
        if mejor is None:                                  # sin hueco: lo mas cerca posible, sobre la criatura
            mejor = obj + Vector((0, 0, 0.8)) + f * 0.2
        w = _ss((fr - F_ZENIT0) / float(F_ZENIT1 - F_ZENIT0))
        if w > 0.0:                                         # plano cenital: sobre la criatura, algo adelantada para ver cara y cuerpo
            for alto in (6.5, 5.0, 3.8, 2.8):
                for adel in (2.0, 1.2, 0.0):
                    cen = obj + f * adel + Vector((0, 0, alto))
                    v = cen - obj
                    if cav.ray_cast(obj, v.normalized(), v.length + HOLGURA)[0] is None and all(cav.ray_cast(cen, ax, HOLGURA)[0] is None for ax in ejes):
                        mejor = mejor.lerp(cen, w)
                        break
                else:
                    continue
                break
        deseada[fr] = (obj, mejor, 0.0)
    rel = {fr: deseada[fr][1] - deseada[fr][0] for fr in deseada}
    suave = {}
    prev = c0 - deseada[F0 - 1][0]
    for fr in range(F0, F_END + 1):
        prev = prev.lerp(rel[fr], 0.25)
        suave[fr] = prev
    ult = c0
    fit = {}
    prev_e = Euler([fc[("rotation_euler", i)].evaluate(F0 - 1) for i in range(3)])
    for fr in range(F0, F_END + 1):
        obj, dest, lens = deseada[fr]
        k = _ss((fr - F0) / 40.0)                       # los primeros frames parte de la camara que ya habia
        p = ult.lerp(obj + suave[fr], 0.35 if fr > F0 + 40 else 0.12 + 0.2 * k)
        p = aparta(p, obj)
        if cav.dentro(p):
            p = ult
        ult = p
        e = (obj - p).to_track_quat('-Z', 'Y').to_euler('XYZ', prev_e)
        prev_e = e
        for i in range(3):
            fc[("location", i)].keyframe_points.insert(fr, p[i], options={'FAST'})
            fc[("rotation_euler", i)].keyframe_points.insert(fr, e[i], options={'FAST'})
        D = (obj - p).length
        fit[fr] = max(10.0, min(40.0, 10.125 * D / vol[fr][1]))
    frs = sorted(fit)
    mn = {fr: min(fit[min(frs[-1], max(frs[0], fr + i))] for i in range(-6, 7)) for fr in frs}       # nunca mas larga que la mas estrecha cercana
    for fr in [F0 - 1] + frs:
        acc = tw = 0.0
        for i in range(-8, 9):
            w = math.exp(-0.5 * (i / 3.5) ** 2)
            acc += mn[min(frs[-1], max(frs[0], fr + i))] * w
            tw += w
        fl[("lens", 0)].keyframe_points.insert(fr, acc / tw, options={'FAST'})
    for f in list(fc.values()) + list(fl.values()):
        f.update()
    malos, dmax, dmin = 0, 0.0, 1e9
    for fr in range(F0, F_END + 1):
        p = Vector([fc[("location", i)].evaluate(fr) for i in range(3)])
        obj = deseada[fr][0]
        d = obj - p
        if cav.ray_cast(p, d.normalized(), d.length)[0] is not None:
            malos += 1
        dmax, dmin = max(dmax, d.length), min(dmin, d.length)
    return {"frames": F_END - F0 + 1, "sin_linea_de_vista": malos, "distancia_min": round(dmin, 2), "distancia_max": round(dmax, 2)}
