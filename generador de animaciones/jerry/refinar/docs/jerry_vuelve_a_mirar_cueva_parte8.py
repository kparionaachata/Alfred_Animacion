# -*- coding: utf-8 -*-
"""Parte 8: despues de que Alfred sube al escalon para colocar la antorcha (aterriza f2370), Jerry ROTA para volver a mirar la cueva y la vuelve a recorrer con la cabeza.
- G0..G0+DUR: gira en su sitio (-131.5, -71.32, 10) de rz 15 a 90 grados (-x) DANDO PASITOS: ciclo de caminar del estudio (SniffingSearchCycle, `tunel_jerry.Ciclo`) en patas,
  columna y cola, con la amplitud entrando y saliendo (x0.7); la cabeza pasa de mirar abajo a Alfred (`spine_2` X +0.45, `spine_1` X +0.20) a mirar la cueva (+0.15 / 0).
- Despues (desde G0+DUR+4 hasta FIN) mueve la cabeza de un lado a otro mirando la cueva: `spine_2` Z (+ = SU DERECHA) +-0.5 con pausas, `spine_1` Z x0.35; cola tranquila.
Ejecutar DESPUES de `jerry_se_para_mira_alfred_parte8.py` (y de las voces). Repetible: guarda la base de los canales en `scene["jerry_mira_cueva_base"]`. Nunca rota `scull`."""
import bpy, math
import jerry_animation_studio.tunel_jerry as tj
G0 = globals().get('G0', 2372); DUR = 18; FIN = globals().get('FIN', 2480); RZ = math.radians(90.0)
ss = lambda t: 0.0 if t <= 0 else 1.0 if t >= 1 else t * t * (3 - 2 * t)
sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'scull_1' in o.pose.bones); root = arm.parent
def fcs(o): return {(fc.data_path, fc.array_index): fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves}
FA, FR = fcs(arm), fcs(root)
cic = tj.Ciclo(25); muestra = cic.pose(1)
HUESOS = [n for n in muestra if ('pose.bones["%s"].rotation_euler' % n, 0) in FA and n not in tj.SIN_ROTAR]
CAN = [('pose.bones["%s"].rotation_euler' % n, i) for n in HUESOS for i in range(3)]
R = range(G0, FIN + 1)
base = sc.get("jerry_mira_cueva_base")
if base is None or len(list(base.values())[0]) != len(R):
    base = {"%s|%d" % c: [FA[c].evaluate(f) for f in R] for c in CAN}; base["rz"] = [FR[('rotation_euler', 2)].evaluate(f) for f in R]; sc["jerry_mira_cueva_base"] = base
def key(fc, f, v):
    k = fc.keyframe_points.insert(f, v); k.interpolation = 'LINEAR'
rz0 = base["rz"][0]
def mirar(f):
    t0 = G0 + DUR + 4; pts = [(t0, 0.0), (t0 + 14, 0.5), (t0 + 30, 0.5), (t0 + 50, -0.5), (t0 + 66, -0.5), (t0 + 80, 0.2), (t0 + 90, 0.2), (t0 + 100, 0.0)]
    if f <= pts[0][0]: return 0.0
    for (a, va), (b, vb) in zip(pts, pts[1:]):
        if f <= b: return va + (vb - va) * ss((f - a) / (b - a))
    return 0.0
for j, f in enumerate(R):
    u = (f - G0) / DUR; amp = 0.7 * ss(min(u / 0.25, (1 - u) / 0.25)) if 0 <= u <= 1 else 0.0; w = ss(u)
    pc = cic.pose(f - G0 + 1); g = mirar(f)
    for n in HUESOS:
        for i in range(3):
            v = base["%s|%d" % ('pose.bones["%s"].rotation_euler' % n, i)][j] + amp * pc[n][i]
            if n == 'spine_2' and i == 0: v = v + (0.15 - 0.45) * w
            if n == 'spine_1' and i == 0: v = v + (0.0 - 0.20) * w
            if n == 'spine_2' and i == 2: v += g
            if n == 'spine_1' and i == 2: v += 0.35 * g
            key(FA[('pose.bones["%s"].rotation_euler' % n, i)], f, v)
    key(FR[('rotation_euler', 2)], f, rz0 + (RZ - rz0) * w)
for d in (FA, FR):
    for fc in d.values(): fc.update()
print('Jerry gira dando pasitos f%d-%d y mira la cueva de lado a lado hasta f%d' % (G0, G0 + DUR, FIN))
