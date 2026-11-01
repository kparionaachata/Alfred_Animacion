# -*- coding: utf-8 -*-
"""Parte 8: despues de que Alfred dice "¡Hey! ¿Que paso?" (f2060-2082), Jerry SE PARA (de la pose sentada a la de pie) y VOLTEA a ver a Alfred (abajo a su derecha).
- Ejecutar DESPUES de `jerry_se_sienta_mira_cueva_parte8.py` y `jerry_lanza_pico_a_alfred_parte8.py`; despues la voz (`voz_jerry_recien_estas_aqui_parte8.py`).
- f P0..P0+14: se levanta (la raiz sube los 0.187 m que bajo al sentarse) y gira el cuerpo de rz 90 a RZ (hacia Alfred) desplazandose DY hacia +y (si gira en el sitio la cola
  entra en la pared del tunel); la cabeza baja para mirar a Alfred (`spine_2` X +0.45, `spine_1` X +0.20; nunca `scull`). Despues queda de pie respirando, cola y orejas, hasta FIN."""
import bpy, math

P0 = globals().get('P0', 2084); DUR = 14; FIN = globals().get('FIN', 2150); RZ = math.radians(15.0); DY = 0.18
ss = lambda t: 0.0 if t <= 0 else 1.0 if t >= 1 else t * t * (3 - 2 * t)
sw = lambda f, p, a, ph=0: a * math.sin(2 * math.pi * f / p + ph)
sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'scull_1' in o.pose.bones); root = arm.parent
def fcs(o): return {(fc.data_path, fc.array_index): fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves}
FA, FR = fcs(arm), fcs(root)
huesos = sorted({dp.split('"')[1] for dp, i in FA if dp.startswith('pose.bones') and dp.endswith('rotation_euler')})
S0 = {n: tuple(FA[('pose.bones["%s"].rotation_euler' % n, i)].evaluate(P0) for i in range(3)) for n in huesos}
x0, y0, z0 = (FR[('location', i)].evaluate(P0) for i in range(3)); rz0 = FR[('rotation_euler', 2)].evaluate(P0)
for d in (FA, FR):
    for fc in d.values():
        for k in [k for k in fc.keyframe_points if k.co.x > P0 + 0.5][::-1]: fc.keyframe_points.remove(k)
DE_PIE = {n: (0.0, 0.0, 0.0) for n in huesos}
DE_PIE.update({'spine_2': (0.45, 0.0, 0.0), 'spine_1': (0.20, 0.0, 0.0)})
for n in ('jaw_bot', 'jaw_top', 'scull', 'scull_1', 'sombrero'):
    if n in DE_PIE: DE_PIE[n] = S0[n]
def key(fc, f, v):
    k = fc.keyframe_points.insert(f, v); k.interpolation = 'LINEAR'
for f in range(P0 + 1, FIN + 1):
    t = ss((f - P0) / DUR); tg = ss((f - P0 - 2) / (DUR - 2))
    vivo = min(1.0, max(0.0, (f - P0 - DUR) / 6.0))
    for n in huesos:
        v = [S0[n][i] + (DE_PIE[n][i] - S0[n][i]) * t for i in range(3)]
        if n == 'spine_4': v[0] += vivo * sw(f, 48, 0.015)
        if n.startswith('tail_'): v[2] += vivo * sw(f, 22, 0.22, int(n[-1]) * 0.6)
        if n in ('ear.L', 'ear.R'): v[1] += vivo * sw(f, 70, 0.08, 1.0 if n == 'ear.R' else 0.0)
        for i in range(3): key(FA[('pose.bones["%s"].rotation_euler' % n, i)], f, v[i])
    key(FR[('location', 0)], f, x0); key(FR[('location', 1)], f, y0 + DY * tg); key(FR[('location', 2)], f, z0 + (10.0 - z0) * ss((f - P0) / (DUR * 0.45)))          # la raiz sube ANTES (las patas aun dobladas no atraviesan el piso)
    key(FR[('rotation_euler', 2)], f, rz0 + (RZ - rz0) * tg)
for d in (FA, FR):
    for fc in d.values(): fc.update()
sc.frame_end = max(sc.frame_end, FIN)
print('Jerry se para y voltea hacia Alfred f%d-%d (rz %.0f -> %.0f grados), de pie hasta f%d' % (P0 + 1, P0 + DUR, math.degrees(rz0), math.degrees(RZ), FIN))
