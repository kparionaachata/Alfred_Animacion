# -*- coding: utf-8 -*-
"""Parte 8: al terminar su recorrido del tunel (llega en `LLEGADA`), Jerry se SIENTA automaticamente (SITTING_POSE de `Downloads/animacion_jerry (7).py`)
y despues mueve la cabeza de izquierda a derecha mirando la enorme cueva.
- Se ejecuta DESPUES de "Crear tunel" del panel de Jerry (acciones `tjerry_root`, `tjerry_armature`, `tjerry_pico`); borra sus claves > LLEGADA y las rehace.
- Sentarse: 14 f (smoothstep) a la SITTING_POSE; la raiz baja 0.187 m (sentado la malla flotaria 0.187 m, ver la guia).
  La cabeza de la pose original (`scull` -25 / 3 / 8 grados) va a `spine_2` (NUNCA se rota `scull`: deforma el ojo izquierdo); `jaw_top` queda en 0 (lleva el pico en la boca).
- Mirar la cueva: giro de la cabeza con `spine_2` Z (+ un poco `spine_1` Z): izquierda -> derecha -> centro, con pausas, hasta FIN.
- El pico se vuelve a hornear sobre la cabeza (hueso `scull`) con la misma forma de llevarlo de antes.
Ejecutar en Blender:  exec(open(RUTA, encoding='utf-8').read())"""
import bpy, math
from mathutils import Matrix

LLEGADA = globals().get('LLEGADA', 1900); FIN = globals().get('FIN', 2070); BAJA = 0.187
ss = lambda t: 0.0 if t <= 0 else 1.0 if t >= 1 else t * t * (3 - 2 * t)
D = math.radians
SITTING_POSE = {
    'shoulder.R': (D(30.7941), D(17.2106), D(12.1341)), 'thigh.R': (D(-37.8749), D(-0.08667), D(-0.29331)), 'shin.R': (D(-60.7645), D(5.85033), D(-3.20637)), 'foot.R': (0, 0, 0),
    'toe.R': (D(32.7165), D(-3.13541), D(-3.85954)), 'shoulder.L': (D(36.6239), D(-7.29244), D(7.40292)), 'thigh.L': (D(-35.5687), D(0.050003), D(0.028891)),
    'shin.L': (D(-66.431), D(-2.51456), D(10.2236)), 'foot.L': (0, 0, 0), 'toe.L': (D(13.1202), D(3.13541), D(-0.724126)),
    'front_shoulder.R': (D(0.104614), D(4.64061), D(-13.2978)), 'front_thigh.R': (D(-3.19165), D(0.713985), D(6.77661)), 'front_shin.R': (D(-20.4907), D(0.349145), D(-0.494996)),
    'front_foot.R': (D(41.3328), D(-5.89264), D(-5.23815)), 'front_shoulder.L': (D(1.44402), D(9.35442), D(1.89138)), 'front_thigh.L': (D(0.89341), D(-0.37494), D(-4.55577)),
    'front_shin.L': (D(-18.3209), D(-0.246426), D(-0.054384)), 'front_foot.L': (0, 0, 0),
    'spine_1': (D(13.2537), D(2.15474), D(2.55871)), 'spine_4': (D(6.06694), 0, 0), 'spine_5': (D(-32.2499), 0, 0), 'spine_6': (D(60.3763), D(-7.91597), D(-1.48891)),
    'tail_1': (D(-54.5851), D(10.5782), D(-10.7713)), 'tail_2': (D(-40.0), D(15.0), D(-8.0)), 'tail_3': (D(-25.0), D(12.0), D(-5.0)),
    'ear.L': (D(15.0), D(5.0), D(8.0)), 'ear.R': (D(12.0), D(-5.0), D(-8.0)),
    'spine_2': (D(15.0), D(3.0), D(8.0)),                                      # cabeza hacia ABAJO (mira la cueva / a Alfred; la pose original miraba arriba con `scull` -25)
}

sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'scull_1' in o.pose.bones); root = arm.parent; pk = bpy.data.objects['tunel_jerry_pico']
def fcs(o): return {(fc.data_path, fc.array_index): fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves}
FA, FR, FP = fcs(arm), fcs(root), fcs(pk)
def borrar(fcd):
    for fc in fcd.values():
        for k in [k for k in fc.keyframe_points if k.co.x > LLEGADA + 0.5][::-1]: fc.keyframe_points.remove(k)
for d in (FA, FR, FP): borrar(d)

huesos = sorted({dp.split('"')[1] for dp, i in FA if dp.startswith('pose.bones')})
P0 = {n: tuple(FA[('pose.bones["%s"].rotation_euler' % n, i)].evaluate(LLEGADA) for i in range(3)) for n in huesos}
x0, y0, z0 = (FR[('location', i)].evaluate(LLEGADA) for i in range(3)); rz0 = FR[('rotation_euler', 2)].evaluate(LLEGADA)
SENT = {n: SITTING_POSE.get(n, (0.0, 0.0, 0.0)) if n not in ('jaw_top', 'jaw_bot', 'scull', 'scull_1', 'sombrero') else P0[n] for n in huesos}

def mirar(f):
    """giro de cabeza (rad, Z de spine_2): izquierda -> derecha -> centro con pausas"""
    pts = [(LLEGADA + 22, 0.0), (LLEGADA + 40, 0.65), (LLEGADA + 62, 0.65), (LLEGADA + 92, -0.65), (LLEGADA + 116, -0.65), (LLEGADA + 136, 0.3), (LLEGADA + 150, 0.3), (LLEGADA + 164, 0.0)]
    if f <= pts[0][0]: return 0.0
    for (a, va), (b, vb) in zip(pts, pts[1:]):
        if f <= b: return va + (vb - va) * ss((f - a) / (b - a))
    return 0.0

def key(fc, f, v):
    k = fc.keyframe_points.insert(f, v); k.interpolation = 'LINEAR'
for f in range(LLEGADA + 1, FIN + 1):
    t = ss((f - LLEGADA) / 14.0); g = mirar(f)
    for n in huesos:
        v = [P0[n][i] + (SENT[n][i] - P0[n][i]) * t for i in range(3)]
        if n == 'spine_2': v[2] += g
        if n == 'spine_1': v[2] += 0.35 * g
        if n.startswith('tail_'): v[1] += 0.12 * math.sin(2 * math.pi * f / 26.0) * t       # cola tranquila
        for i in range(3): key(FA[('pose.bones["%s"].rotation_euler' % n, i)], f, v[i])
    key(FR[('location', 0)], f, x0); key(FR[('location', 1)], f, y0); key(FR[('location', 2)], f, z0 - BAJA * t); key(FR[('rotation_euler', 2)], f, rz0)
for d in (FA, FR):
    for fc in d.values(): fc.update()

# el pico sigue a la cabeza con la misma forma de llevarlo
sc.frame_set(LLEGADA); OFF = (arm.matrix_world @ arm.pose.bones['scull'].matrix).inverted() @ pk.matrix_world; prev = None
for f in range(LLEGADA + 1, FIN + 1):
    sc.frame_set(f); M = arm.matrix_world @ arm.pose.bones['scull'].matrix @ OFF
    l, q, s = M.decompose(); e = q.to_euler('XYZ', prev) if prev is not None else q.to_euler('XYZ'); prev = e
    for i in range(3): key(FP[('location', i)], f, l[i]); key(FP[('rotation_euler', i)], f, e[i])
for fc in FP.values(): fc.update()
sc.frame_end = max(sc.frame_end, FIN); sc.frame_set(LLEGADA + 40)
print('Jerry: se sienta f%d-%d y mira la cueva hasta f%d' % (LLEGADA + 1, LLEGADA + 14, FIN))
