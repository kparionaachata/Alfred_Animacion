# -*- coding: utf-8 -*-
"""Parte 7: el acercamiento de Jerry (f568-672) NO usa el hueso `scull` para rotar (su deformacion tapaba el ojo izquierdo): se le resta a `scull` rotation_euler el gesto de cabeza de `jerry_se_acerca_parte7.py` (X: cabeza gacha 0.30 al andar, 0.42+-0.07 al olfatear, 0.45+-0.10 al husmear; Y: vaiven 0.15 al olfatear;
replica exacta de `gesto()`: tras restar, `scull` queda en +-0.5 grados) y el cabeceo X se traslada a `spine_2` en f568-607 (con fundido a 0 en la rampa f608-618, donde `jerry_mira_creeper_parte7.py` toma el control para mirar al creeper). f671: gesto completo; f672: x0.44 (para que `scull` ya valga ~0 cuando arranca el susto).
El vaiven Y del olfateo se descarta (no se traslada). Orden: `jerry_se_acerca_parte7.py` (borra y rehace f568+) -> este script -> `jerry_mira_creeper_parte7.py` (deltas de `recorridos/mira_creeper_delta_parte7.json`, calculados con este estado). NO repetir sobre el mismo estado. Se ejecuta DENTRO de Blender con exec."""
import bpy, math
JA = next(o for o in bpy.data.objects if o.type == "ARMATURE" and "scull_1" in o.pose.bones)
def fcs(o): return [fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]
def C(b, a): return next(f for f in fcs(JA) if f.data_path == 'pose.bones["%s"].rotation_euler' % b and f.array_index == a)
ss = lambda t: 0.0 if t <= 0 else 1.0 if t >= 1 else t * t * (3 - 2 * t)
FPB = 20; SEGS = [("anda", 1.3), ("pausa", 14, "olfatea"), ("anda", 0.95), ("pausa", 40, "husmea")]; frames = []
for sg in SEGS:
    if sg[0] == "anda":
        for k in range(int(round(sg[1] * FPB))): frames.append(("andando", 1.0, k))
    else:
        dur, kind = sg[1], sg[2]
        for k in range(dur): frames.append((kind, ss((k + 1) / 5.0) * (ss((dur - k) / 5.0) if kind != "husmea" else 1.0), k))
def gest(i):
    kind, w, tt = frames[min(i, len(frames) - 1)]
    if kind == "andando": w = min(1.0, ss((i + 1) / 8.0)); return 0.30 * w, 0.0
    if kind == "olfatea": return (0.42 + 0.07 * math.sin(2 * math.pi * tt / 7.0)) * w, 0.15 * w * math.sin(2 * math.pi * tt / 14.0)
    return (0.45 + 0.10 * math.sin(2 * math.pi * tt / 8.0)) * w, 0.0
T0 = 568; T = {}
for ix in (0, 1):
    fc = C("scull", ix)
    for kp in fc.keyframe_points:
        f = int(round(kp.co.x))
        if T0 <= f <= 672:
            gx, gy = gest(f - T0); fac = 1.0 if f <= 671 else 0.44; dv = -(gx if ix == 0 else gy) * fac
            kp.co.y += dv; kp.handle_left.y += dv; kp.handle_right.y += dv
            if ix == 0: T[f] = gx * fac
    fc.update()
s2 = C("spine_2", 0)
for kp in s2.keyframe_points:
    f = int(round(kp.co.x))
    if f in T and f <= 670:
        dv = T[f] * (1 - ss((f - 608) / 10.0)); kp.co.y += dv; kp.handle_left.y += dv; kp.handle_right.y += dv
s2.update(); print("LISTO")
