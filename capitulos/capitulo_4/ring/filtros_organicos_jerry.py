# -*- coding: utf-8 -*-
"""FILTROS ORGANICOS y PARPADEOS de Jerry en base_ranas_2 (despues de jerry_despierta.py y de la voz).

Mismas formulas que el estudio de Jerry (`filtros_organicos_y_parpadeos_parte7.py`), como deltas SUMADOS
a lo que ya anima cada canal (claves LINEAR por frame), f1 -> frame_end:
 - respiracion de spine_1 en X y Z (amp 0.05, vel 0.01), micro-movimiento de spine_1 (0.008, 0.05, semilla 42),
   micro-escala Z de spine_1 (0.005)
 - noise de hombros front_shoulder.R/L (0.006, 0.07, semilla 123)
 - orejas ear.L/R en Z (0.12, vel 0.06; dormido solo al 25 %)
 - cola tail_2 en Z (0.524 x 0.35, vel 0.12) solo cuando esta tranquilo (ventanas COLA)
 - parpadeos al azar (9 f, `Closed` en ojos y pupilas) cuando esta despierto, sin pisar la voz ni sus parpadeos.
Repetible: los deltas y los parpadeos se guardan en `organicos_jerry_delta.json` y se restan/borran antes.
Si se regenera jerry_despierta.py: aplicar() con QUITAR=True antes (o borrar el json, porque la animacion nueva ya no los tiene).
Uso (exec en Blender): aplicar()   /   aplicar(quitar=True)
"""
import bpy, json, math, os, random

DJ = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/organicos_jerry_delta.json"
ARM = "Dog_001_rig"
OJOS = ("ojo_izquierdo_jerry", "ojo_derecho_jerry", "pupila_izquierda_jerry", "pupila_derecha_jerry")
DESPIERTO = 147                                   # abre los ojos en f140-147
DORMIDO_HASTA = 140                               # orejas al 25 % mientras duerme (base_ranas_3: -100, no duerme)
COLA = [(268, 282), (306, 357), (505, 10 ** 6)]   # tranquilo: tras ponerse el sombrero, mirando la pelea, al final
VOZ = [(151, 167), (198, 214)]                    # "¿Ves, sombrero?" / "Otra vez"
PROPIOS = [155, 213, 244, 300, 323, 395, 455]     # parpadeos que ya trae jerry_despierta.py
SEQ = [0.0, 0.25, 0.5, 0.75, 1.0, 1.0, 0.75, 0.5, 0.25]


def ss(x):
    return 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))


def noise_at(frame, freq, seed, dim=0):
    v = math.sin(frame * freq * 1.3 + seed * 7.3 + dim * 3.7); v += math.sin(frame * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5
    v += math.sin(frame * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25
    return v / 1.75


def fcs(idb):
    return [fc for l in idb.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


def buscar(idb, dp, axis):
    return next((fc for fc in fcs(idb) if fc.data_path == dp and fc.array_index == axis), None)


def ventana(f, tramos, rampa=6.0):
    return max([ss((f - (a - rampa)) / rampa) * (1 - ss((f - b) / rampa)) for a, b in tramos] + [0.0])


def aplicar(quitar=False):
    sc = bpy.context.scene; arm = bpy.data.objects[ARM]; FIN = sc.frame_end
    PREV = json.load(open(DJ, encoding="utf-8")) if os.path.exists(DJ) else {"canales": {}, "parpadeos": []}
    NEW = {"canales": {}, "parpadeos": []}
    fr = range(1, FIN + 1)
    D = {}                                                                   # (dp, eje) -> deltas

    def suma(bone, tipo, axis, vals):
        k = ('pose.bones["%s"].%s' % (bone, tipo), axis)
        D[k] = [a + b for a, b in zip(D[k], vals)] if k in D else list(vals)

    if not quitar:
        dormido = lambda f: 1 - ss((f - DORMIDO_HASTA) / 8.0)
        suma("spine_1", "rotation_euler", 0, [0.05 * math.sin(f * 0.01 * 2 * math.pi) for f in fr])
        suma("spine_1", "rotation_euler", 2, [0.05 * 0.4 * math.sin(f * 0.01 * 2 * math.pi + 1.2) for f in fr])
        for ax in range(3): suma("spine_1", "rotation_euler", ax, [0.008 * noise_at(f, 0.05, 42, ax) for f in fr])
        suma("spine_1", "scale", 2, [0.005 * math.sin(f * 0.01 * 2 * math.pi) for f in fr])
        for ax in range(3):
            for b, off in (("front_shoulder.R", 0), ("front_shoulder.L", 17)):
                suma(b, "rotation_euler", ax, [0.006 * noise_at(f, 0.07, 123 + off, ax) for f in fr])
        for b, fase in (("ear.L", 0.0), ("ear.R", 1.57)):
            suma(b, "rotation_euler", 2, [0.12 * (1 - 0.75 * dormido(f)) * math.sin(f * 0.06 * 2 * math.pi + fase) for f in fr])
        suma("tail_2", "rotation_euler", 2, [0.524 * 0.35 * ventana(f, COLA) * math.sin(f * 0.12 * 2 * math.pi) for f in fr])
    # canales de antes que ya no se usan -> delta 0 (para restarlos)
    for clave in PREV["canales"]:
        dp, ax = clave.rsplit(":", 1); k = (dp, int(ax))
        if k not in D: D[k] = [0.0] * len(fr)
    for (dp, axis), deltas in D.items():
        fc = buscar(arm, dp, axis)
        if fc is None:
            bag = arm.animation_data.action.layers[0].strips[0].channelbags[0]
            fc = bag.fcurves.new(dp, index=axis)
        prev = PREV["canales"].get("%s:%d" % (dp, axis), {})
        estatico = 1.0 if dp.endswith("scale") else 0.0
        base = [(fc.evaluate(f) if len(fc.keyframe_points) else estatico) - prev.get(str(f), 0.0) for f in fr]
        kp = fc.keyframe_points
        for i in range(len(kp) - 1, -1, -1):
            if 1 <= kp[i].co.x <= FIN: kp.remove(kp[i], fast=True)
        kp.add(len(fr)); kp.foreach_set("co", [x for f, b, d in zip(fr, base, deltas) for x in (f, b + d)])
        for k in kp: k.interpolation = 'LINEAR'
        fc.update()
        if any(deltas): NEW["canales"]["%s:%d" % (dp, axis)] = {str(f): d for f, d in zip(fr, deltas)}
    # ---- parpadeos
    keys = [bpy.data.objects[n].data.shape_keys for n in OJOS]
    for s in PREV.get("parpadeos", []):
        for k in keys:
            fc = buscar(k, 'key_blocks["Closed"].value', 0)
            for f in range(s, s + 10): fc.keyframe_points.insert(f, 0.0, options={'FAST'})
            fc.update()
    if not quitar:
        rng = random.Random(23); f = DESPIERTO + rng.randint(20, 40); evitar = VOZ + [(p, p + 9) for p in PROPIOS]
        while f + 10 < FIN:
            if any(a - 20 <= f <= b + 20 for a, b in evitar): f += 6; continue
            NEW["parpadeos"].append(f); f += rng.randint(80, 140)
        for s in NEW["parpadeos"]:
            for k in keys:
                fc = buscar(k, 'key_blocks["Closed"].value', 0)
                for i, v in enumerate(SEQ + [0.0]):
                    p = fc.keyframe_points.insert(s + i, v, options={'FAST'}); p.interpolation = 'LINEAR'
                fc.update()
    json.dump(NEW, open(DJ, "w", encoding="utf-8"))
    sc.frame_set(sc.frame_current)
    return {"canales": len(NEW["canales"]), "parpadeos_nuevos": NEW["parpadeos"], "hasta": FIN}
