# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: inserta N frames vacios en la linea de tiempo desde el frame T (todo lo que ocurre desde T se retrasa N frames).
Desplaza las claves de las acciones ACTIVAS de Alfred (`alfred`, `Armature`), Jerry (`jerry`, `Dog_001_rig`) y del pico (`alfred_pico_piedra`), las tiras NLA de las voces
y ojos (con `frame_start_ui`, sin tocar sus acciones) y las tiras de sonido del editor de secuencias desde T. NO toca: la camara (se rehace con camara_caverna_replay.py),
las criaturas (se rehacen con criaturas_caverna.py), las acciones de parpadeo (se rehacen con organicos_parpadeos_cueva5A.py) ni los sonidos `caverna_viaje` (se rehacen
con camara_caverna_sonidos.py). Antes de insertar hay que quitar los filtros organicos (`organicos_parpadeos_cueva5A.aplicar(quitar=True)`) y volver a aplicarlos despues.
Uso en Blender: exec(open(ruta, encoding="utf8").read()); insertar(570, 300)
"""
import bpy

OBJETOS = ("alfred", "Armature", "jerry", "Dog_001_rig", "alfred_pico_piedra")


def _fcs(a):
    return [fc for l in a.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


def insertar(T, N):
    sc = bpy.context.scene
    O = bpy.data.objects
    res = {"claves": 0, "nla": 0, "vse": 0}
    for n in OBJETOS:
        a = O[n].animation_data.action
        for fc in _fcs(a):
            for kp in fc.keyframe_points:
                if kp.co.x >= T:
                    kp.co.x += N
                    kp.handle_left.x += N
                    kp.handle_right.x += N
                    res["claves"] += 1
            fc.update()
    ids = []
    for ob in O:
        if ob.animation_data:
            ids.append(ob)
        if ob.type == 'MESH' and ob.data.shape_keys and ob.data.shape_keys.animation_data:
            ids.append(ob.data.shape_keys)
    for idb in ids:
        for t in idb.animation_data.nla_tracks:
            for s in sorted(t.strips, key=lambda x: -x.frame_start):
                if s.frame_start >= T:
                    s.frame_start_ui += N
                    res["nla"] += 1
    ed = sc.sequence_editor
    for s in sorted(ed.strips_all, key=lambda x: -x.frame_start):
        if s.frame_final_start >= T:
            s.frame_start += N
            res["vse"] += 1
    sc.frame_end += N
    sc.frame_set(1)
    return res
