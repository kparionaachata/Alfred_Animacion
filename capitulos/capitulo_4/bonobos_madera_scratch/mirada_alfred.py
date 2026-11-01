# -*- coding: utf-8 -*-
# Alfred mira hacia arriba a los monos: el cuello (Neck_alfred) se resuelve por frame para apuntar la cara al objetivo.
import bpy, math
from mathutils import Vector, Matrix

P = r"C:\Users\user\AppData\Local\Temp\claude\C--Users-user-Desktop-Alfred-Animacion\593282e0-289f-4704-9bd2-cafc9b5be57b\scratchpad"
SC = bpy.context.scene
al = bpy.data.objects['alfred']
rig = [c for c in al.children if c.type == 'ARMATURE'][0]
pb = rig.pose.bones
neck = pb['Neck_alfred']
LIM_P, LIM_Y = math.radians(65), math.radians(80)


def mono_cabeza(i):
    n = 'bonobo_adulto_1' if i == 0 else 'bonobo_adulto_1.%03d' % i
    raiz = bpy.data.objects[n]
    r = [o for o in raiz.children if o.type == 'ARMATURE'][0]
    h = [b.name for b in r.data.bones if b.name.startswith('head_')][0]
    return lambda: r.matrix_world @ r.pose.bones[h].head


OBJ = {
    'm3': mono_cabeza(3), 'm6': mono_cabeza(6), 'm7': mono_cabeza(7), 'm2': mono_cabeza(2), 'm0': mono_cabeza(0), 'm1': mono_cabeza(1),
    'chick': lambda: bpy.data.objects['chicken_1'].matrix_world.translation + Vector((0, 0, 0.5)),
    'rat': lambda: bpy.data.objects['rat_1'].matrix_world.translation.copy(),
}


def cara():
    bpy.context.view_layer.update()
    M = rig.matrix_world @ pb['face_alfred'].matrix
    return (M.to_3x3() @ Vector((0, 0, 1))).normalized(), (rig.matrix_world @ pb['face_alfred'].head)


def _res1(d, px, py, pz):
    for it in range(10):
        neck.rotation_euler = (px, py, pz)
        f, _ = cara()
        r = d - f
        if r.length < 8e-3:
            break
        e = 0.02
        neck.rotation_euler = (px + e, py, pz); fx, _ = cara()
        neck.rotation_euler = (px, py + e, pz); fy, _ = cara()
        jx, jy = (fx - f) / e, (fy - f) / e
        a, b, c = jx.dot(jx), jx.dot(jy), jy.dot(jy)
        gx, gy = jx.dot(r), jy.dot(r)
        det = a * c - b * b + 1e-9
        dx, dy = (c * gx - b * gy) / det, (a * gy - b * gx) / det
        n = math.hypot(dx, dy)
        if n > 0.5:
            dx, dy = dx * 0.5 / n, dy * 0.5 / n
        px += dx; py += dy
        px = max(-LIM_P, min(LIM_P, px)); py = max(-LIM_Y, min(LIM_Y, py))
    neck.rotation_euler = (px, py, pz)
    f, _ = cara()
    return px, py, (d - f).length


def resolver(d, px, py, pz):
    mejor = None
    for (a, b) in ((px, py), (-0.9, 0.0)):
        r = _res1(d, a, b, pz)
        if mejor is None or r[2] < mejor[2]:
            mejor = r
        if r[2] < 2e-2:
            break
    neck.rotation_euler = (mejor[0], mejor[1], pz)
    return mejor[0], mejor[1]


def suave(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def dir_objetivo(linea, f, desde, mezcla=6):
    """linea: [(frame_inicio, nombre)] ; direccion unitaria hacia el objetivo vigente (con fundido)"""
    idx = max(i for i, (t, n) in enumerate(linea) if t <= f)
    t, n = linea[idx]
    d = (OBJ[n]() - desde).normalized()
    if idx > 0 and f - t < mezcla:
        dp = (OBJ[linea[idx - 1][1]]() - desde).normalized()
        w = suave((f - t + 1) / mezcla)
        d = dp.slerp(d, w) if hasattr(dp, 'slerp') else (dp * (1 - w) + d * w).normalized()
    return d.normalized()


def rastrear(frames, linea, mezcla=6, ini=None):
    """devuelve {frame: (px, py, pz)} apuntando la cara al objetivo; deja la pose del cuello sin keys"""
    out = {}
    px, py = ini if ini else (None, None)
    for f in frames:
        SC.frame_set(f); bpy.context.view_layer.update()
        pz = neck.rotation_euler.z
        _, c = cara()
        d = dir_objetivo(linea, f, c, mezcla)
        if px is None:
            px, py = neck.rotation_euler.x, neck.rotation_euler.y
        px, py = resolver(d, px, py, pz)
        out[f] = (px, py, pz)
    return out
