# -*- coding: utf-8 -*-
"""cerdo2_ring (base_ranas_3): animacion NUEVA y organica que SI mira la pelea (reemplaza el "bombea" de cerdos_animan.py).
 - La cabeza sigue al punto medio de los dos luchadores (alfred y guard_ribbit_1, leidos de sus curvas de raiz) con
   retraso suave (como un espectador real), mas micro-ruido. El giro horizontal es el eje Y local de Head (medido ~1:1).
 - Reposo: las dos patas delanteras apoyadas en la valla (la derecha en espejo de la izquierda de la pose del usuario),
   respira, cambia el peso de un lado a otro, mueve las orejas, parpadea.
 - Celebra (eventos de la pelea a favor de su luchador, mismos que el publico): levanta la pata derecha con un arco
   suave y la agita despacio, se inclina hacia el ring, asiente y chilla (boca abierta). Desanimo: cabeza y cuerpo abajo.
 - Raiz: saltito leve solo al celebrar.
Reemplaza las acciones cerdo2_ring_anima / cerdo2_ring_raiz y crea cerdo2_ring_cara (shape keys de la cabeza).
Uso (exec en Blender): construir()
"""
import bpy, math, random
from bpy_extras.anim_utils import action_get_channelbag_for_slot

DIR = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/"
PUB = {"__name__": "pub"}
exec(open(DIR + "publico_ribbits.py", encoding="utf-8").read(), PUB)
FIN = PUB["FIN"]
NOMBRE, ARM, CABEZA = "cerdo2_ring", "pig.arma_cerdo_1.001", "pig.Head_cerdo_1.001"
LUCHADOR = "guard_ribbit_1"
D = math.radians

REF = {"Body:Bend_cerdo_1": ((0, 0, 0), (-25, 0, 0)),
       "Head_cerdo_1": ((0, 0.0406, 0.087), (65.88, 0.8, -0.37)),
       "Leg:FL_cerdo_1": ((-0.1804, -0.2447, -0.1606), (15.92, -16.42, 2.03)),
       "Leg:FL:Bend_cerdo_1": ((0, 0, 0), (0, 0, 0)),
       "Leg:FR_cerdo_1": ((0.1804, -0.2447, -0.1606), (15.92, 16.42, -2.03)),          # en la valla (espejo)
       "Leg:FR:Bend_cerdo_1": ((0, 0, 0), (0, 0, 0)),
       "Leg:BL_cerdo_1": ((0, 0, 0), (-35.43, 0, 0)),
       "Leg:BR_cerdo_1": ((0, 0, 0), (-35.43, 0, 0)),
       "Ear-L_cerdo_1": ((0, 0, 0), (0, 0, 0)), "Ear-R_cerdo_1": ((0, 0, 0), (0, 0, 0))}
FR_ARRIBA_LOC, FR_ARRIBA_ROT = (0.2144, -0.118, -0.055), (87.78, 39.37, -31.81)      # pata arriba (pose del usuario)


def noise(f, freq, seed, dim=0):
    v = math.sin(f * freq * 1.3 + seed * 7.3 + dim * 3.7) + 0.5 * math.sin(f * freq * 2.7 + seed * 2.1 + dim * 5.1) + 0.25 * math.sin(f * freq * 5.1 + seed * 4.9 + dim * 1.3)
    return v / 1.75


def pos_raiz(nombre):
    o = bpy.data.objects[nombre]; ad = o.animation_data
    if not (ad and ad.action): return lambda f: o.location.copy()
    cb = action_get_channelbag_for_slot(ad.action, ad.action_slot)
    fc = {c.array_index: c for c in cb.fcurves if c.data_path == "location"}
    return lambda f: [fc[i].evaluate(f) if i in fc else o.location[i] for i in range(3)]


def claves(idb, nombre, canales):
    idb.animation_data_create()
    viejo = bpy.data.actions.get(nombre)
    if viejo: bpy.data.actions.remove(viejo)
    act = bpy.data.actions.new(nombre); idb.animation_data.action = act
    for path, cl in canales.items():
        for i in range(len(cl[0][1])):
            fc = act.fcurve_ensure_for_datablock(idb, path, index=i); fc.keyframe_points.add(len(cl))
            fc.keyframe_points.foreach_set("co", [x for f, v in cl for x in (f, v[i])]); fc.update()
    return act


def construir():
    r = bpy.data.objects[NOMBRE]; arm = bpy.data.objects[ARM]
    ev = PUB["eventos"]()
    fr_ev = dict(nombre=NOMBRE, luchador=LUCHADOR, seed=7781, prob=0.9, retraso=5, dur=26, salto=0.04)
    cel, des, sal = PUB["capas_evento"](fr_ev, ev)
    bx, by, bz = r["_cerdo_base"] if r.get("_cerdo_base") is not None else list(r.location)
    pa, pg = pos_raiz("alfred"), pos_raiz("guard_ribbit_1")
    cabeza = (bx, by + 0.19, 10.36)                                                     # cabeza del cerdo (medida)
    # rumbo de la pelea, suavizado (la cabeza llega con retraso)
    rumbo, h = {}, None
    for f in range(1, FIN + 1):
        a, g = pa(f), pg(f); mx, my = (a[0] + g[0]) / 2, (a[1] + g[1]) / 2
        t = math.degrees(math.atan2(-(mx - cabeza[0]), my - cabeza[1]))
        if h is None: h = t
        h += (((t - h + 180) % 360) - 180) * 0.12
        rumbo[f] = h
    rng = random.Random(55); blinks, f = [], rng.randint(20, 60)
    while f < FIN - 10: blinks.append(f); f += rng.randint(85, 150)
    SEQ = [0, .25, .5, .75, 1, 1, .75, .5, .25, 0]
    can = {}
    for b in REF:
        arm.pose.bones[b].rotation_mode = 'XYZ'
        can['pose.bones["%s"].rotation_euler' % b] = []; can['pose.bones["%s"].location' % b] = []
    raiz, cara = [], {'key_blocks["Mouth:Open"].value': [], 'key_blocks["Pig:Snort"].value': [], 'key_blocks["Blink"].value': []}
    for f in range(1, FIN + 1):
        wc, wd = cel.get(f, 0.0), des.get(f, 0.0)
        br = math.sin(2 * math.pi * f / 82.0); peso = math.sin(2 * math.pi * f / 143.0 + 0.7)
        agita = math.sin(2 * math.pi * f / 16.0)
        yaw = ((rumbo[f] - 180.0 + 180) % 360) - 180                                    # mira recto = rumbo 180 (hacia -y)
        d = {
            "Body:Bend_cerdo_1": (1.4 * br - 7 * wc + 9 * wd + 1.2 * noise(f, 0.03, 3), 0, 2.6 * peso),
            "Head_cerdo_1": (4 + 2.2 * noise(f, 0.045, 9, 0) - 10 * wc * (0.6 + 0.4 * max(0.0, agita)) + 16 * wd,
                             yaw + 3 * noise(f, 0.035, 21, 1), 2.5 * noise(f, 0.04, 33, 2) + 4 * wc * agita),
            "Leg:FL_cerdo_1": (0.9 * noise(f, 0.06, 57, 0), 0.6 * noise(f, 0.05, 58, 1), 0),
            "Leg:BL_cerdo_1": (1.5 * peso, 0, 0), "Leg:BR_cerdo_1": (-1.5 * peso, 0, 0),
            "Ear-L_cerdo_1": (5 * math.sin(2 * math.pi * f / 47.0) + 10 * wc * agita, 0, 3 * noise(f, 0.05, 71, 2)),
            "Ear-R_cerdo_1": (5 * math.sin(2 * math.pi * f / 47.0 + 1.7) - 10 * wc * agita, 0, -3 * noise(f, 0.05, 72, 2)),
        }
        for b, (lo, ro) in REF.items():
            dd = d.get(b, (0, 0, 0)); loc = list(lo); rot = [ro[i] + dd[i] for i in range(3)]
            if b == "Leg:FR_cerdo_1":                                                  # celebra: la pata sube en arco y se agita despacio
                k = wc
                loc = [lo[i] + (FR_ARRIBA_LOC[i] - lo[i]) * k for i in range(3)]
                rot = [ro[i] + (FR_ARRIBA_ROT[i] - ro[i]) * k for i in range(3)]
                rot[0] += 14 * k * agita; rot[2] += 8 * k * math.cos(2 * math.pi * f / 16.0)
            if b == "Leg:FR:Bend_cerdo_1": rot[0] += 10 * wc * max(0.0, agita)
            can['pose.bones["%s"].rotation_euler' % b].append((f, tuple(D(x) for x in rot)))
            can['pose.bones["%s"].location' % b].append((f, tuple(loc)))
        raiz.append((f, (bx, by, bz + 0.6 * sal.get(f, 0.0))))
        bl = max([SEQ[f - b0] for b0 in blinks if b0 <= f < b0 + 10] + [0.0])
        cara['key_blocks["Mouth:Open"].value'].append((f, (min(1.0, 0.9 * wc * (0.5 + 0.5 * abs(agita))),)))
        cara['key_blocks["Pig:Snort"].value'].append((f, (max(0.0, 0.6 * wd) + 0.3 * max(0.0, noise(f, 0.08, 5)) ** 3,)))
        cara['key_blocks["Blink"].value'].append((f, (bl,)))
    claves(arm, NOMBRE + "_anima", can)
    claves(r, NOMBRE + "_raiz", {"location": raiz})
    key = bpy.data.objects[CABEZA].data.shape_keys
    if key: claves(key, NOMBRE + "_cara", cara)
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    return {"celebra_s": round(sum(1 for v in cel.values() if v > 0.5) / 24, 1), "desanima_s": round(sum(1 for v in des.values() if v > 0.5) / 24, 1),
            "parpadeos": len(blinks), "cara": bool(key)}
