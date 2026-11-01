# -*- coding: utf-8 -*-
# Inserta un hueco de tiempo en las acciones: las teclas posteriores al corte se desplazan D frames y entre el corte y el desplazamiento la curva se mantiene.
import bpy, math


def fcs(a):
    return [c for l in a.layers for s in l.strips for b in s.channelbags for c in b.fcurves]


def hueco_curva(c, corte, D):
    kp = c.keyframe_points
    n = len(kp)
    if n == 0:
        return 0
    co = [0.0] * (2 * n); hl = [0.0] * (2 * n); hr = [0.0] * (2 * n)
    kp.foreach_get('co', co); kp.foreach_get('handle_left', hl); kp.foreach_get('handle_right', hr)
    idx = [i for i in range(n) if co[2 * i] > corte + 1e-6]
    if not idx:
        return 0
    v = c.evaluate(corte)
    prev_int = 'LINEAR'
    for i in range(n):
        if co[2 * i] <= corte + 1e-6:
            prev_int = kp[i].interpolation
    hay = any(abs(co[2 * i] - corte) < 1e-4 for i in range(n))
    for i in idx:
        co[2 * i] += D; hl[2 * i] += D; hr[2 * i] += D
    kp.foreach_set('co', co); kp.foreach_set('handle_left', hl); kp.foreach_set('handle_right', hr)
    const = prev_int == 'CONSTANT' or c.data_path.startswith(('hide', 'show'))
    if not hay:
        k = kp.insert(corte, v, options={'FAST'}); k.interpolation = 'CONSTANT' if const else 'LINEAR'
    k = kp.insert(corte + D, v, options={'FAST'}); k.interpolation = 'CONSTANT' if const else 'LINEAR'
    c.update()
    return len(idx)


def hueco_accion(a, corte, D):
    return sum(hueco_curva(c, corte, D) for c in fcs(a))
