# -*- coding: utf-8 -*-
"""
fcurve_compat.py — Chicken 1 Animation Studio
Capa de compatibilidad para acceder a las FCurves de una Action entre:
  - Blender <= 4.4 (API clasica: action.fcurves existe directo)
  - Blender >= 5.0 (Animation Layers/Slots: action.fcurves fue ELIMINADO;
    las curvas viven en action.layers[0].strips[0].channelbags[0].fcurves)

Usar get_fcurves() para LECTURA (iterar, find(), remove(), len()).
Usar ensure_fcurves() cuando se va a llamar .new() sobre una Action que
puede ser recien creada (bpy.data.actions.new(...)) y todavia no tiene
layer/strip/channelbag/slot en Blender >=5.0.
"""


def get_fcurves(action):
    """Devuelve la coleccion de FCurves de 'action' para lectura/iteracion.
    Compatible con Blender <=4.4 y >=5.0. Devuelve [] si no hay curvas aun
    (action sin layers/strips/channelbags todavia, o action=None)."""
    if action is None:
        return []
    legacy = getattr(action, "fcurves", None)
    if legacy is not None:
        return legacy
    try:
        return action.layers[0].strips[0].channelbags[0].fcurves
    except (IndexError, AttributeError):
        return []


def ensure_fcurves(action, id_type='OBJECT'):
    """Devuelve la coleccion de FCurves de 'action' lista para .new(),
    creando slot/layer/strip/channelbag si hiciera falta (Blender >=5.0).
    En Blender <=4.4 simplemente devuelve action.fcurves."""
    if action is None:
        return None
    legacy = getattr(action, "fcurves", None)
    if legacy is not None:
        return legacy
    slot = action.slots[0] if action.slots else action.slots.new(id_type=id_type, name=action.name)
    layer = action.layers[0] if action.layers else action.layers.new("Layer")
    strip = layer.strips[0] if layer.strips else layer.strips.new(type='KEYFRAME')
    if hasattr(strip, "channelbag"):
        channelbag = strip.channelbag(slot, ensure=True)
    else:
        channelbag = strip.channelbags[0] if strip.channelbags else strip.channelbags.new(slot)
    return channelbag.fcurves
