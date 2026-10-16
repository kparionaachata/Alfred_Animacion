# -*- coding: utf-8 -*-
"""base_ranas_3: la pelea se va al OTRO EXTREMO del ring (norte, lejos de Jerry y del cerdo) para el derribo.
Durante la fase 4 (GIRO_DESDE -> GIRO_HASTA) Alfred y el guardian, mientras pelean, van rodeando la antorcha: sus raices
(posicion y rumbo) giran juntas alrededor de la antorcha (asi nunca la cruzan ni cambian de distancia entre ellos) hasta
que Alfred queda al norte (ANGULO_DESTINO) en el frame del derribo. Despues el giro se mantiene.
Las claves originales de las raices (desde GIRO_DESDE) se guardan en `pelea_al_otro_extremo_original.json`: repetible.
Despues hay que volver a ejecutar pelea_derribo.py (lee la pose de partida ya girada).
Uso (exec en Blender): aplicar()
"""
import bpy, json, math, os
from mathutils import Vector

DIR = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/"
ORIG = DIR + "pelea_al_otro_extremo_original.json"
C = Vector((-37.5, -12.0, 0.0))
GIRO_DESDE, GIRO_HASTA, F_REF = 171, 300, 315          # F_REF: frame en que se mide donde esta Alfred antes de caer
ANGULO_DESTINO = 90.0                                   # Alfred al norte de la antorcha (+y)
RAICES = ["alfred", "guard_ribbit_1"]


def ss(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)


def curvas(o):
    a = o.animation_data.action
    return {(fc.data_path, fc.array_index): fc for l in a.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves
            if fc.data_path in ("location", "rotation_euler")}


def aplicar():
    FIN = bpy.context.scene.frame_end
    cv = {n: curvas(bpy.data.objects[n]) for n in RAICES}
    if os.path.exists(ORIG):
        orig = json.load(open(ORIG, encoding="utf-8"))
    else:
        orig = {n: {"%s|%d" % k: [list(p.co) for p in fc.keyframe_points if p.co.x >= GIRO_DESDE] for k, fc in c.items()} for n, c in cv.items()}
        json.dump(orig, open(ORIG, "w", encoding="utf-8"))
    ev = lambda n, k, f: next((v for x, v in orig[n][k] if abs(x - f) < 0.5), cv[n][tuple([k.split("|")[0], int(k.split("|")[1])])].evaluate(f))
    ax, ay = ev("alfred", "location|0", F_REF), ev("alfred", "location|1", F_REF)
    a0 = math.degrees(math.atan2(ay - C.y, ax - C.x))
    delta = ((ANGULO_DESTINO - a0 + 180) % 360) - 180                         # el camino mas corto alrededor de la antorcha
    th = lambda f: math.radians(delta) * ss((f - GIRO_DESDE) / float(GIRO_HASTA - GIRO_DESDE))
    for n in RAICES:
        o = orig[n]
        fr = [x for x, v in o["location|0"]]
        X = {x: v for x, v in o["location|0"]}; Y = {x: v for x, v in o["location|1"]}; RZ = {x: v for x, v in o["rotation_euler|2"]}
        nuevos = {"location|0": [], "location|1": [], "rotation_euler|2": []}
        for f in fr:
            t = th(f); c, s = math.cos(t), math.sin(t); dx, dy = X[f] - C.x, Y[f] - C.y
            nuevos["location|0"].append((f, C.x + c * dx - s * dy)); nuevos["location|1"].append((f, C.y + s * dx + c * dy))
            nuevos["rotation_euler|2"].append((f, RZ.get(f, cv[n][("rotation_euler", 2)].evaluate(f)) + t))
        for k, pts in nuevos.items():
            dp, i = k.split("|"); fc = cv[n][(dp, int(i))]
            for f, v in pts: fc.keyframe_points.insert(f, v, options={'FAST'}).interpolation = 'LINEAR'
            fc.update()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    return {"alfred_angulo_antes": round(a0, 1), "giro_grados": round(delta, 1)}
