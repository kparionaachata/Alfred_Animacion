# -*- coding: utf-8 -*-
"""Parte 8: despues de que Jerry dice "¿Que, recien estas aqui?" (voz hasta f2140), Alfred GIRA para mirar a Jerry (que esta arriba, en el borde de su tunel).
Ejecutar DESPUES de `alfred_se_soba_cabeza_golpe_parte8.py`. f G0..G0+DUR: el empty `alfred` gira en Z hacia Jerry (el camino mas corto) y el cuello sube a mirarlo
(`Neck_alfred` X -0.55, Y a 0) MIENTRAS SIGUE SOBANDOSE (no toca el brazo); se queda mirandolo hasta FIN. Escribe en `tunel_alfred_root` / `tunel_alfred_armature`."""
import bpy, math

G0 = globals().get('G0', 2141); DUR = 14; FIN = globals().get('FIN', 2190)
ss = lambda t: 0.0 if t <= 0 else 1.0 if t >= 1 else t * t * (3 - 2 * t)
sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'Hips_alfred' in o.pose.bones); root = arm.parent
jerry = bpy.data.objects['jerry']
def fcs(o): return {(fc.data_path, fc.array_index): fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves}
FA, FR = fcs(arm), fcs(root)
def key(fc, f, v):
    k = fc.keyframe_points.insert(f, v); k.interpolation = 'LINEAR'
NK = 'pose.bones["Neck_alfred"].rotation_euler'
SOLO = [FR[('rotation_euler', 2)]] + [FA[(NK, i)] for i in range(3)]               # SOLO el giro del cuerpo y el cuello: el brazo sigue sobandose (claves de `alfred_se_soba_cabeza_golpe_parte8.py`)
base_cuello = {f: [FA[(NK, i)].evaluate(f) for i in range(3)] for f in range(G0, FIN + 1)}
for fc in SOLO:
    for k in [k for k in fc.keyframe_points if k.co.x > G0 + 0.5][::-1]: fc.keyframe_points.remove(k)
sc.frame_set(G0); a = root.matrix_world.translation.copy(); j = jerry.matrix_world.translation.copy()
rz0 = FR[('rotation_euler', 2)].evaluate(G0); rzj = math.atan2(-(j.x - a.x), (j.y - a.y)); d = (rzj - rz0 + math.pi) % (2 * math.pi) - math.pi
for f in range(G0 + 1, FIN + 1):
    t = ss((f - G0) / DUR); n = base_cuello[f]
    key(FR[('rotation_euler', 2)], f, rz0 + d * t)
    key(FA[(NK, 0)], f, n[0] + (-0.55 - n[0]) * t); key(FA[(NK, 1)], f, n[1] * (1 - t)); key(FA[(NK, 2)], f, n[2])      # deja de buscar y mira a Jerry (arriba)
for dd in (FA, FR):
    for fc in dd.values(): fc.update()
sc.frame_end = max(sc.frame_end, FIN)
print('Alfred gira hacia Jerry f%d-%d: rz %.0f -> %.0f grados' % (G0 + 1, G0 + DUR, math.degrees(rz0), math.degrees(rz0 + d)))
