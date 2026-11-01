# -*- coding: utf-8 -*-
"""Recorta el INICIO de la escena abierta (sin guardar): borra los frames 1..T-1 y el frame T pasa a ser el 1. Misma logica que crear_cueva_5D.py (acciones, NLA, VSE). Ejecutar UNA vez."""
import bpy, sys

T = 1001                                   # el frame T de la escena actual pasa a ser el frame 1
FIN = bpy.context.scene.frame_end - (T - 1)
D = T - 1
sc = bpy.context.scene
res = {"acciones": 0, "claves_quitadas": 0, "ciclicas": 0, "nla_movidas": 0, "nla_quitadas": 0, "vse_movidas": 0, "vse_quitadas": 0}


def fcs(a):
    return [fc for l in a.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


ed = sc.sequence_editor
quitados = []


def datos_animados():
    vistos = set()
    for nombre in dir(bpy.data):
        c = getattr(bpy.data, nombre, None)
        if not hasattr(c, "__iter__") or isinstance(c, str) or nombre.startswith("_"):
            continue
        try:
            for idb in c:
                if getattr(idb, "animation_data", None) is not None and idb.as_pointer() not in vistos:
                    vistos.add(idb.as_pointer())
                    yield idb
        except Exception:
            continue


hechas = set()
for idb in list(datos_animados()):
    ad = idb.animation_data
    a = ad.action
    if a is not None and a.name not in hechas:
        hechas.add(a.name)
        for fc in fcs(a):
            ciclica = any(m.type == 'CYCLES' for m in fc.modifiers)
            if not ciclica:
                xs = [k.co.x for k in fc.keyframe_points]
                antes = [x for x in xs if x <= T]
                corte = min(T - 60, max(antes)) if antes else T - 60
                for i in range(len(fc.keyframe_points) - 1, -1, -1):
                    if fc.keyframe_points[i].co.x < corte:
                        fc.keyframe_points.remove(fc.keyframe_points[i], fast=True)
                        res["claves_quitadas"] += 1
            else:
                res["ciclicas"] += 1
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
sc.frame_end = FIN
sc.frame_set(1)
print("RECORTADO",  res, "quitados:", quitados, "frame_end", sc.frame_end)
