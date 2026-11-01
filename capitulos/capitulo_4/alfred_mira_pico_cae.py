# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: Alfred voltea la cabeza para ver caer su pico (`alfred_pico_piedra`) al darse cuenta de que lo pateo. Restriccion DAMPED_TRACK (eje Z, que es
el frente del hueso de la cara) en `face_alfred` hacia el pico, con la influencia animada: 0 -> 0.9 entre el 850 (el pico sale del borde en 853) y el 864, se mantiene
mientras dice "Creo que mejor me lo otro pico." (872-945) y vuelve a 0 (mirando a Jerry) hacia el 966.
Uso en Blender: exec(open(ruta, encoding="utf8").read()); construir()      (repetible)
"""
import bpy

CLAVES = [(850, 0.0), (864, 0.9), (945, 0.9), (966, 0.0)]


def construir():
    O = bpy.data.objects
    b = O["Armature"].pose.bones["face_alfred"]
    for c in list(b.constraints):
        if c.name == "Mirar_pico_que_cae":
            b.constraints.remove(c)
    c = b.constraints.new('DAMPED_TRACK')
    c.name, c.target, c.track_axis = "Mirar_pico_que_cae", O["alfred_pico_piedra"], 'TRACK_Z'
    for f, v in CLAVES:
        c.influence = v
        c.keyframe_insert("influence", frame=f)
    return len(CLAVES)
