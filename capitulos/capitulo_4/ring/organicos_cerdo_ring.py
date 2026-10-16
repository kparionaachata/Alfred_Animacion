# -*- coding: utf-8 -*-
"""Movimientos organicos de cerdo_ring (base_ranas_3), SUMADOS a su animacion:
respiracion del cuerpo (Body:Bend X), micro-movimiento de la cabeza (Head X/Z, ruido suave), orejas (Ear-L/R)
que se mueven solas y dan sacudidas cortas, y micro-ruido de la pata izquierda apoyada (Leg:FL).
Repetible: deltas en `organicos_cerdo_delta.json` (se restan antes de volver a aplicar). aplicar(quitar=True) los quita.
"""
import bpy, json, math, os

DJ = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/organicos_cerdo_delta.json"
ARM = "pig.arma_cerdo_1"
D = math.radians
SACUDIDAS = [64, 171, 233, 318, 402]                       # orejas: sacudida corta (6 f)


def noise(f, freq, seed, dim=0):
    v = math.sin(f * freq * 1.3 + seed * 7.3 + dim * 3.7) + 0.5 * math.sin(f * freq * 2.7 + seed * 2.1 + dim * 5.1) + 0.25 * math.sin(f * freq * 5.1 + seed * 4.9 + dim * 1.3)
    return v / 1.75


def aplicar(quitar=False):
    sc = bpy.context.scene; arm = bpy.data.objects[ARM]; act = arm.animation_data.action; FIN = sc.frame_end
    fr = list(range(1, FIN + 1))
    PREV = json.load(open(DJ, encoding="utf-8")) if os.path.exists(DJ) else {}
    Dl = {}

    def suma(bone, axis, vals):
        k = 'pose.bones["%s"].rotation_euler|%d' % (bone, axis)
        Dl[k] = [a + b for a, b in zip(Dl[k], vals)] if k in Dl else list(vals)
    if not quitar:
        suma("Body:Bend_cerdo_1", 0, [D(1.4) * math.sin(2 * math.pi * f / 80.0) for f in fr])
        for ax in (0, 2): suma("Head_cerdo_1", ax, [D(1.6) * noise(f, 0.045, 31, ax) for f in fr])
        for ax in range(3): suma("Leg:FL_cerdo_1", ax, [D(0.8) * noise(f, 0.06, 57, ax) for f in fr])
        for b, ph, sg in (("Ear-L_cerdo_1", 0.0, 1), ("Ear-R_cerdo_1", 1.7, -1)):
            sac = lambda f: max([math.sin(math.pi * (f - s) / 6.0) * math.sin(2 * math.pi * (f - s) / 3.0) for s in SACUDIDAS if s <= f <= s + 6] + [0.0])
            suma(b, 0, [D(5) * math.sin(2 * math.pi * f / 47.0 + ph) + D(14) * sac(f) for f in fr])
            suma(b, 2, [sg * D(4) * noise(f, 0.05, 11 + ph, 2) for f in fr])
    for k in PREV:
        if k not in Dl: Dl[k] = [0.0] * len(fr)
    NEW = {}
    for k, d in Dl.items():
        dp, i = k.rsplit("|", 1); i = int(i)
        fc = act.fcurve_ensure_for_datablock(arm, dp, index=i)
        prev = PREV.get(k, {})
        base = [(fc.evaluate(f) if len(fc.keyframe_points) else 0.0) - prev.get(str(f), 0.0) for f in fr]
        kp = fc.keyframe_points                                  # (la accion del cerdo tiene claves mas alla de FIN: se insertan una a una)
        for f, b0, dd in zip(fr, base, d): kp.insert(f, b0 + dd, options={'FAST'}).interpolation = 'LINEAR'
        fc.update()
        if any(d): NEW[k] = {str(f): dd for f, dd in zip(fr, d)}
    json.dump(NEW, open(DJ, "w", encoding="utf-8"))
    sc.frame_set(sc.frame_current)
    return {"canales": len(NEW)}
