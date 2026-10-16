# -*- coding: utf-8 -*-
"""RING: los dos CERDOS espectadores alientan a su luchador.
Pose base = la que dejo el usuario en cerdo_ring (pata delantera izquierda apoyada en la barra, la derecha arriba).
Encima, animacion propia de cada cerdo (ritmo, fase y gestos distintos) + reacciones a la pelea (mismos eventos que el publico):
- cerdo_ring (Alfred): agita la pata delantera derecha, la cabeza asiente y se ladea, el cuerpo rebota.
- cerdo2_ring (guardian): bombea la pata (golpes al aire), la cabeza cabecea rapido, rebote mas fuerte.
Celebra: pata mas arriba, cabeza arriba, saltito. Desanimo: cabeza abajo, cuerpo encogido. Repetible."""
import bpy, math, random
from bpy_extras import anim_utils

PUB = {"__name__": "pub"}
exec(open("C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/publico_ribbits.py", encoding="utf-8").read(), PUB)
FIN = PUB["FIN"]

# pose de referencia del usuario (cerdo_ring): hueso -> (location, rotation_euler en grados)
REF = {"Body:Bend_cerdo_1": ((0, 0, 0), (-25, 0, 0)),
       "Head_cerdo_1": ((0, 0.0406, 0.087), (65.88, 0.8, -0.37)),
       "Leg:FL_cerdo_1": ((-0.1804, -0.2447, -0.1606), (15.92, -16.42, 2.03)),
       "Leg:FL:Bend_cerdo_1": ((0, 0, 0), (0, 0, 0)),
       "Leg:FR_cerdo_1": ((0.2144, -0.118, -0.055), (87.78, 39.37, -31.81)),
       "Leg:FR:Bend_cerdo_1": ((0, 0, 0), (-3.01, 3.12, 5.43)),
       "Leg:BL_cerdo_1": ((0, 0, 0), (-35.43, 0, 0)),
       "Leg:BR_cerdo_1": ((0, 0, 0), (-35.43, 0, 0))}

CERDOS = [dict(nombre="cerdo_ring", luchador="alfred", estilo="agita", per=13, fase=0.4, amp=1.0),
          dict(nombre="cerdo2_ring", luchador="guard_ribbit_1", estilo="bombea", per=10, fase=2.1, amp=1.15)]


def deltas(c, f, wc, wd):
    """sumas en grados a la pose de referencia, por hueso (x, y, z)"""
    ph = 2 * math.pi * f / c["per"] + c["fase"]; a = c["amp"]; d = {}
    if c["estilo"] == "agita":
        d["Body:Bend_cerdo_1"] = (-4 * abs(math.sin(ph)) * a - 6 * wc - 8 * wd, 0, 3 * math.sin(ph * 0.5))     # (+ empuja hacia la valla)
        d["Head_cerdo_1"] = (10 * math.sin(ph * 0.5 + 1) - 14 * wc + 18 * wd, 0, 12 * math.sin(ph * 0.25))
        d["Leg:FR_cerdo_1"] = (25 * math.sin(ph) * a * (1 + 0.6 * wc) - 20 * wc, 0, 15 * math.cos(ph) * a)
        d["Leg:FR:Bend_cerdo_1"] = (15 * math.sin(ph + 0.8), 0, 0)
        d["Leg:FL_cerdo_1"] = (3 * math.sin(ph * 0.5), 0, 0)
    else:
        bomba = max(0.0, math.sin(ph)) ** 2
        d["Body:Bend_cerdo_1"] = (-6 * abs(math.sin(ph)) * a - 6 * wc - 8 * wd, 0, 0)
        d["Head_cerdo_1"] = (14 * math.sin(2 * ph) - 14 * wc + 18 * wd, 0, 8 * math.sin(ph * 0.3))
        d["Leg:FR_cerdo_1"] = (35 * bomba * a * (1 + 0.5 * wc), 0, 8 * math.sin(ph * 0.5))
        d["Leg:FR:Bend_cerdo_1"] = (25 * bomba, 0, 0)
        d["Leg:FL_cerdo_1"] = (5 * math.sin(2 * ph), 0, 0)
    d["Leg:BL_cerdo_1"] = (4 * math.sin(ph * 0.5), 0, 0)
    d["Leg:BR_cerdo_1"] = (-4 * math.sin(ph * 0.5), 0, 0)
    return d


def claves(obj, nombre, canales):
    obj.animation_data_create()
    viejo = bpy.data.actions.get(nombre)
    if viejo: bpy.data.actions.remove(viejo)
    act = bpy.data.actions.new(nombre); obj.animation_data.action = act
    for path, cl in canales.items():
        for i in range(len(cl[0][1])):
            fc = act.fcurve_ensure_for_datablock(obj, path, index=i); fc.keyframe_points.add(len(cl))
            fc.keyframe_points.foreach_set("co", [x for f, v in cl for x in (f, v[i])]); fc.update()
    return act


def construir():
    ev = PUB["eventos"](); out = {}
    for c in CERDOS:
        r = bpy.data.objects[c["nombre"]]
        arm = next(x for x in r.children_recursive if x.type == 'ARMATURE' and len(x.pose.bones) > 3 and "extras" not in x.name)
        rr = random.Random(c["nombre"])
        fr = dict(nombre=c["nombre"], luchador=c["luchador"], seed=rr.randint(0, 10 ** 6), prob=0.9, retraso=rr.randint(2, 6),
                  dur=rr.randint(18, 28), salto=0.07)
        cel, des, sal = PUB["capas_evento"](fr, ev)
        if r.get("_cerdo_base") is None: r["_cerdo_base"] = list(r.location)
        bx, by, bz = r["_cerdo_base"]
        canales = {}
        for h in REF:
            arm.pose.bones[h].rotation_mode = 'XYZ'
            canales['pose.bones["%s"].rotation_euler' % h] = []; canales['pose.bones["%s"].location' % h] = []
        raiz = []
        for f in range(1, FIN + 1):
            wc = cel.get(f, 0.0); wd = des.get(f, 0.0); d = deltas(c, f, wc, wd)
            for h, (lo, ro) in REF.items():
                dd = d.get(h, (0, 0, 0))
                canales['pose.bones["%s"].rotation_euler' % h].append((f, tuple(math.radians(ro[i] + dd[i]) for i in range(3))))
                canales['pose.bones["%s"].location' % h].append((f, tuple(lo)))
            raiz.append((f, (bx, by, bz + sal.get(f, 0.0))))
        claves(arm, c["nombre"] + "_anima", canales)
        claves(r, c["nombre"] + "_raiz", {"location": raiz})
        out[c["nombre"]] = dict(celebra_s=round(sum(1 for v in cel.values() if v > 0.5) / 24, 1), desanima_s=round(sum(1 for v in des.values() if v > 0.5) / 24, 1))
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    return out
