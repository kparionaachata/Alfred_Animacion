# -*- coding: utf-8 -*-
"""Parte 8: FILTROS ORGANICOS de Alfred (los del paso 3 de cada segmento del estudio `alfred_animation_studio`, `_apply_organic_filters`, con sus valores por omision; la parte 8
se construyo con scripts y no los tenia). Mismo metodo que `parte7/filtros_organicos_y_parpadeos_parte7.py`: deltas aditivos por frame SUMADOS al valor de cada canal (claves LINEAR):
 - respiracion `Spine_alfred` / `Spine1_alfred` X y Z (amp 0.020, vel 0.010, fase 0.00: valores del usuario); micro-escala Z de `Spine1_alfred` (0.010);
 - micro-movimiento de cabeza `Neck_alfred` / `face_alfred` (amp 0.023, vel 0.079, semilla 693), APAGADO con rampa en la reaccion a la flecha (VENTANAS_SIN_CABEZA) para no tapar el golpe.
Rango f1 - frame_end. Repetible: los deltas se guardan en `organicos_delta_alfred_parte8.json` y se restan antes de volver a aplicar. Si se vuelve a ejecutar un script de ANIMACION de Alfred,
ejecutar ANTES este con `QUITAR = True` y DESPUES con QUITAR = False. Despues de aplicar, re-hornea la flecha clavada para que siga el cuello (`flecha_alfred`). Sin parpadeos (no pedidos)."""
import bpy, json, math, os
sc = bpy.context.scene
DJ = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\parte8\organicos_delta_alfred_parte8.json"
QUITAR = bool(globals().get('QUITAR', False)); F0 = 1; F1 = sc.frame_end
VENTANAS_SIN_CABEZA = [(2534, 2558)]
PREV = json.load(open(DJ, encoding="utf-8")) if os.path.exists(DJ) else {}; NEW = {}
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
def noise_at(frame, freq, seed, dim=0):
    v = math.sin(frame * freq * 1.3 + seed * 7.3 + dim * 3.7); v += math.sin(frame * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5; v += math.sin(frame * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25
    return v / 1.75
AA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "Hips_alfred" in o.pose.bones)
FC = {(fc.data_path, fc.array_index): fc for l in AA.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves}
def aplicar(dp, axis, deltas, clave):
    fc = FC[(dp, axis)]; prev = PREV.get(clave, {}); f0, f1 = F0, F0 + len(deltas) - 1
    base = {f: fc.evaluate(f) - prev.get(str(f), 0.0) for f in range(f0, f1 + 1)}
    for i in range(len(fc.keyframe_points) - 1, -1, -1):
        if f0 <= fc.keyframe_points[i].co.x <= f1: fc.keyframe_points.remove(fc.keyframe_points[i])
    for f in range(f0, f1 + 1):
        kp = fc.keyframe_points.insert(f, base[f] + deltas[f - f0], options={'FAST'}); kp.interpolation = 'LINEAR'
    fc.update(); NEW[clave] = {str(f): deltas[f - f0] for f in range(f0, f1 + 1) if deltas[f - f0] != 0.0}
fr = range(F0, F1 + 1); D = {}
def sumar(b, tipo, ax, vals):
    k = (b, tipo, ax); D[k] = [x + y for x, y in zip(D.get(k, [0.0] * len(vals)), vals)]
if not QUITAR:
    amp, sp, ph = 0.020, 0.010, 0.0                                                             # respiracion: valores del usuario (panel: amplitud 0.020, velocidad 0.010, fase 0.00)
    for b in ("Spine_alfred", "Spine1_alfred"):
        sumar(b, "rotation_euler", 0, [amp * math.sin(f * sp * 2 * math.pi + ph) for f in fr]); sumar(b, "rotation_euler", 2, [amp * 0.4 * math.sin(f * sp * 2 * math.pi + ph + 1.2) for f in fr])
    mask = lambda f: 1.0 - max([ss((f - (a - 6)) / 6.0) * (1 - ss((f - b) / 6.0)) for a, b in VENTANAS_SIN_CABEZA] + [0.0])
    for ax in range(3):
        d = [0.023 * noise_at(f, 0.079, 693, ax) * mask(f) for f in fr]
        for b in ("Neck_alfred", "face_alfred"): sumar(b, "rotation_euler", ax, d)
    sumar("Spine1_alfred", "scale", 2, [0.010 * math.sin(f * sp * 2 * math.pi + ph) for f in fr])
for clave in list(PREV.keys()):                                                             # canales con deltas anteriores que ya no se aplican: se restan
    b, tipo, ax = clave.split(":")
    if (b, tipo, int(ax)) not in D: D[(b, tipo, int(ax))] = [0.0] * len(fr)
for (b, tipo, ax), vals in D.items():
    aplicar('pose.bones["%s"].%s' % (b, tipo), ax, vals, "%s:%s:%d" % (b, tipo, ax))
json.dump(NEW, open(DJ, "w", encoding="utf-8"))
# re-hornear la flecha clavada (sigue al cuello con su offset del impacto)
fl = bpy.data.objects.get("flecha_alfred")
if fl and fl.animation_data and fl.animation_data.action:
    FF = {(fc.data_path, fc.array_index): fc for l in fl.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves}
    IMP = 2536; cuello = lambda: AA.matrix_world @ AA.pose.bones["Neck_alfred"].matrix
    sc.frame_set(IMP); OFF = cuello().inverted() @ fl.matrix_world; ultimo = int(max(k.co.x for k in FF[("location", 0)].keyframe_points))
    for f in range(IMP + 1, ultimo + 1):
        sc.frame_set(f); l, q, s = (cuello() @ OFF).decompose()
        for i in range(3): FF[("location", i)].keyframe_points.insert(f, l[i]).interpolation = 'LINEAR'
        for i in range(4): FF[("rotation_quaternion", i)].keyframe_points.insert(f, q[i]).interpolation = 'LINEAR'
    for fc in FF.values(): fc.update()
print(("QUITADO" if QUITAR else "Filtros organicos de Alfred f%d-%d (%d canales)" % (F0, F1, len(NEW))))
