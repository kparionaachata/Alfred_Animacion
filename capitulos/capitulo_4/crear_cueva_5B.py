# -*- coding: utf-8 -*-
"""Crea alfred_cueva_5B.blend a partir de alfred_cueva_5A.blend: el estado del frame 920 de 5A pasa a ser el frame 1 de 5B (todo lo que viene despues se adelanta 919 frames y lo anterior se descarta).
Se hace SIN interfaz, sobre una COPIA guardada de la escena viva (el borrado en vivo no hace falta):
    blender -b <copia_5A.blend> --python crear_cueva_5B.py -- <salida_5B.blend> [frame=920]
Que se desplaza:
 - las claves de las acciones ACTIVAS de cada dato (objetos, formas, luces, camaras, escena con las rampas de volumen del sonido, materiales...), conservando solo la ultima clave anterior al
   frame 920 y 60 frames antes (para que la interpolacion no cambie);
 - las tiras NLA (voces, ojos): se mueven con frame_start_ui sin tocar sus acciones; las que terminaron antes del 920 y no son pistas base se quitan;
 - las tiras del editor de secuencias (sonidos): las que terminaron antes se quitan, las que cruzan el 920 se recortan al frame 1, las demas se mueven.
frame_end = frame_end - 919. Los datos no animados (mallas, materiales) no se tocan.
"""
import bpy, sys

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SALIDA = args[0]
T = int(args[1]) if len(args) > 1 else 920
D = T - 1
sc = bpy.context.scene


def fcs(a):
    return [fc for l in a.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


def datos_animados():
    vistos = set()
    for nombre in dir(bpy.data):
        col = getattr(bpy.data, nombre, None)
        if not hasattr(col, "__iter__") or isinstance(col, str) or nombre.startswith("_"):
            continue
        try:
            for idb in col:
                if getattr(idb, "animation_data", None) is not None and idb.as_pointer() not in vistos:
                    vistos.add(idb.as_pointer())
                    yield idb
        except Exception:
            continue


hechas = set()
res = {"acciones": 0, "claves_quitadas": 0, "nla_movidas": 0, "nla_quitadas": 0, "vse_movidas": 0, "vse_quitadas": 0}
for idb in list(datos_animados()):
    ad = idb.animation_data
    a = ad.action
    if a is not None and a.name not in hechas:
        hechas.add(a.name)
        for fc in fcs(a):
            xs = [k.co.x for k in fc.keyframe_points]
            antes = [x for x in xs if x <= T]
            corte = min(T - 60, max(antes)) if antes else T - 60
            for i in range(len(fc.keyframe_points) - 1, -1, -1):
                if fc.keyframe_points[i].co.x < corte:
                    fc.keyframe_points.remove(fc.keyframe_points[i], fast=True)
                    res["claves_quitadas"] += 1
            for k in fc.keyframe_points:
                k.co.x -= D
                k.handle_left.x -= D
                k.handle_right.x -= D
            fc.update()
        res["acciones"] += 1
    for tr in list(ad.nla_tracks):
        for s in list(tr.strips):
            es_base = "Base" in tr.name or s.extrapolation != 'NOTHING'
            if s.frame_end < T and not es_base:
                tr.strips.remove(s)
                res["nla_quitadas"] += 1
            else:
                s.frame_start_ui -= D
                res["nla_movidas"] += 1
        if not tr.strips and "Base" not in tr.name:
            ad.nla_tracks.remove(tr)
ed = sc.sequence_editor
if ed:
    for s in sorted(list(ed.strips_all), key=lambda x: x.frame_final_start):
        if s.frame_final_end <= T:
            ed.strips.remove(s)
            res["vse_quitadas"] += 1
        else:
            s.frame_start -= D
            if s.frame_final_start < 1:
                s.frame_final_start = 1
            res["vse_movidas"] += 1
sc.frame_start = 1
sc.frame_end = max(2, sc.frame_end - D)
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=SALIDA)
print("CREADO", SALIDA, res, "frame_end", sc.frame_end)
