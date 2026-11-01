# -*- coding: utf-8 -*-
"""Parte 8: FILTROS ORGANICOS de Jerry (los del estudio `jerry_animation_studio`, valores por omision; mismo metodo aditivo que la parte 7,
`alfred/refinar/docs/parte7/filtros_organicos_y_parpadeos_parte7.py`, seccion JERRY): deltas por frame SUMADOS al valor de cada canal (claves LINEAR), f1 - frame_end:
 - respiracion `spine_1` X y Z (amp 0.05, vel 0.01) + micro-movimiento de `spine_1` (0.008, 0.05, semilla 42) + micro-escala Z de `spine_1` (0.005);
 - noise de hombros `front_shoulder.R` / `.L` (0.006, 0.07, semilla 123 / 140); orejas `ear.L` / `ear.R` en Z (0.12, vel 0.06, fases 0 y 1.57);
 - cola `tail_2` en Z (0.524 x 0.35, vel 0.12) SOLO cuando esta tranquilo (VENTANAS_COLA: sentado mirando la cueva, de pie hablando con Alfred, mirando la cueva al final).
El pico que lleva en la boca (horneado sobre `scull`) se re-hornea con su offset ANTERIOR a los filtros para que siga en la boca hasta que lo suelta (SUELTA).
Repetible: deltas en `filtros_organicos_jerry_parte8.json` (`QUITAR = True` los resta). Si se rehace una animacion de Jerry: este con QUITAR -> la animacion -> este. Sin parpadeos (no pedidos)."""
import bpy, json, math, os
sc = bpy.context.scene
DJ = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\jerry\refinar\docs\filtros_organicos_jerry_parte8.json"
QUITAR = bool(globals().get('QUITAR', False)); F0 = 1; F1 = sc.frame_end; SUELTA = globals().get('SUELTA', 2010)
VENTANAS_COLA = [(1914, 2000), (2098, 2372), (2392, F1)]
PREV = json.load(open(DJ, encoding="utf-8")) if os.path.exists(DJ) else {}; NEW = {}
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
def noise_at(frame, freq, seed, dim=0):
    v = math.sin(frame * freq * 1.3 + seed * 7.3 + dim * 3.7); v += math.sin(frame * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5; v += math.sin(frame * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25
    return v / 1.75
JA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "scull_1" in o.pose.bones)
def fcs(o): return {(fc.data_path, fc.array_index): fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves}
FC = fcs(JA)
# 1) offset del pico respecto a la cabeza ANTES de los filtros
pk = bpy.data.objects.get("tunel_jerry_pico"); REL = {}
if pk and pk.animation_data and pk.animation_data.action:
    for f in range(F0, SUELTA + 1):
        sc.frame_set(f); REL[f] = (JA.matrix_world @ JA.pose.bones["scull"].matrix).inverted() @ pk.matrix_world
# 2) deltas
fr = range(F0, F1 + 1); D = {}
def sumar(b, tipo, ax, vals):
    k = (b, tipo, ax); D[k] = [x + y for x, y in zip(D.get(k, [0.0] * len(vals)), vals)]
if not QUITAR:
    amp, sp, ph = 0.05, 0.01, 0.0
    sumar("spine_1", "rotation_euler", 0, [amp * math.sin(f * sp * 2 * math.pi + ph) for f in fr]); sumar("spine_1", "rotation_euler", 2, [amp * 0.4 * math.sin(f * sp * 2 * math.pi + ph + 1.2) for f in fr])
    for ax in range(3): sumar("spine_1", "rotation_euler", ax, [0.008 * noise_at(f, 0.05, 42, ax) for f in fr])
    sumar("spine_1", "scale", 2, [0.005 * math.sin(f * 0.01 * 2 * math.pi) for f in fr])
    for ax in range(3):
        for b, off in (("front_shoulder.R", 0), ("front_shoulder.L", 17)): sumar(b, "rotation_euler", ax, [0.006 * noise_at(f, 0.07, 123 + off, ax) for f in fr])
    for b, fase in (("ear.L", 0.0), ("ear.R", 1.57)): sumar(b, "rotation_euler", 2, [0.12 * math.sin(f * 0.06 * 2 * math.pi + fase) for f in fr])
    cola = lambda f: max([ss((f - (a - 6)) / 6.0) * (1 - ss((f - b) / 6.0)) for a, b in VENTANAS_COLA] + [0.0])
    sumar("tail_2", "rotation_euler", 2, [0.524 * 0.35 * cola(f) * math.sin(f * 0.12 * 2 * math.pi) for f in fr])
for clave in list(PREV.keys()):
    b, tipo, ax = clave.split("|")
    if (b, tipo, int(ax)) not in D: D[(b, tipo, int(ax))] = [0.0] * len(fr)
for (b, tipo, ax), vals in D.items():
    dp = 'pose.bones["%s"].%s' % (b, tipo); fc = FC.get((dp, ax)); clave = "%s|%s|%d" % (b, tipo, ax)
    if fc is None:
        fc = JA.animation_data.action.layers[0].strips[0].channelbag(JA.animation_data.action_slot, ensure=True).fcurves.new(dp, index=ax); FC[(dp, ax)] = fc
    prev = PREV.get(clave, {}); est = (JA.pose.bones[b].scale[ax] if tipo == "scale" else JA.pose.bones[b].rotation_euler[ax])
    base = {f: (fc.evaluate(f) if len(fc.keyframe_points) else est) - prev.get(str(f), 0.0) for f in fr}
    for i in range(len(fc.keyframe_points) - 1, -1, -1):
        if F0 <= fc.keyframe_points[i].co.x <= F1: fc.keyframe_points.remove(fc.keyframe_points[i])
    for f in fr:
        kp = fc.keyframe_points.insert(f, base[f] + vals[f - F0], options={'FAST'}); kp.interpolation = 'LINEAR'
    fc.update(); NEW[clave] = {str(f): vals[f - F0] for f in fr if vals[f - F0] != 0.0}
json.dump(NEW, open(DJ, "w", encoding="utf-8"))
# 3) re-hornear el pico en la boca
if REL:
    FP = fcs(pk); prev_e = None
    for f in range(F0, SUELTA + 1):
        if not any(abs(k.co.x - f) < 0.5 for k in FP[("location", 0)].keyframe_points): continue
        sc.frame_set(f); M = (JA.matrix_world @ JA.pose.bones["scull"].matrix) @ REL[f]; l, q, s = M.decompose()
        e = q.to_euler('XYZ', prev_e) if prev_e is not None else q.to_euler('XYZ'); prev_e = e
        for i in range(3): FP[("location", i)].keyframe_points.insert(f, l[i]).interpolation = 'LINEAR'; FP[("rotation_euler", i)].keyframe_points.insert(f, e[i]).interpolation = 'LINEAR'
    for fc in FP.values(): fc.update()
print("QUITADO" if QUITAR else "Filtros organicos de Jerry f%d-%d (%d canales), pico re-horneado hasta f%d" % (F0, F1, len(NEW), SUELTA))
