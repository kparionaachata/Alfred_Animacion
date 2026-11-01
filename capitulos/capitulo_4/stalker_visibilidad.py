# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: oculta (o muestra) a The Stalker (`the_stalker_1` y todo lo que cuelga de el, mas sus luces `stalker_fx_*`) en la vista y en el render.
Durante toda la escena de Alfred y Jerry en la salida del tunel (hasta el final, frame 820) debe seguir invisible.
Uso en Blender: exec(open(ruta, encoding="utf8").read()); ocultar()      /      ocultar(False) para mostrarlo
"""
import bpy


def ocultar(oculto=True):
    O = bpy.data.objects
    raiz = O["the_stalker_1"]
    obs = {raiz} | set(raiz.children_recursive) | {o for o in O if o.name.startswith("stalker_fx_")}
    for o in obs:
        o.hide_viewport = oculto
        o.hide_render = oculto
    return len(obs)
