# -*- coding: utf-8 -*-
"""
blender_compat.py — Cerdo_1 Animation Studio

Capa de compatibilidad para el cambio de API de animacion introducido en
Blender 4.4 (Slotted Actions) y consolidado en Blender 5.0+, donde el acceso
directo `Action.fcurves` fue ELIMINADO por completo. A partir de 5.0 hay que
pasar por el "slot" y el "channelbag":

    action -> slot -> layer -> strip -> channelbag -> fcurves

Esta funcion permite seguir escribiendo el resto del addon casi igual que
antes: en vez de `algo.fcurves` se llama a `get_fcurves(algo)`.

Funciona en:
  - Blender < 4.4  : Action.fcurves existe de forma nativa.
  - Blender 4.4-4.x: Action.fcurves existe como proxy "legacy" (deprecado).
  - Blender 5.0+   : Action.fcurves NO existe; se resuelve via channelbag.
"""
import bpy

try:
    from bpy_extras import anim_utils as _anim_utils
except Exception:
    _anim_utils = None


def get_fcurves(target, create=True):
    """Devuelve la coleccion de FCurves de `target`, sea cual sea la version
    de Blender.

    `target` puede ser:
      - un bpy.types.Action
      - un bpy.types.AnimData (ej. obj.animation_data)

    Si no hay accion asignada, o no se puede resolver un slot/channelbag,
    devuelve una lista vacia (nunca None), para que los `for fc in
    get_fcurves(x):` existentes no revienten.

    `create=True` (por defecto) asegura que exista layer/strip/channelbag
    para el slot en Blender 5.0+ si hace falta escribir fcurves nuevas
    (get_fcurves(x).new(...)). No tiene efecto en versiones legacy y no
    daña nada si solo se esta iterando/leyendo.
    """
    anim_data = None
    action = target

    if isinstance(target, bpy.types.AnimData):
        anim_data = target
        action = anim_data.action

    if action is None:
        return []

    # Blender < 5.0 (incluye el proxy legacy de 4.4/4.5)
    if hasattr(action, "fcurves"):
        return action.fcurves

    # Blender 5.0+: Action.fcurves ya no existe -> hay que ir por el slot
    if _anim_utils is None:
        return []

    slot = anim_data.action_slot if anim_data is not None else None
    if slot is None:
        # Sin AnimData (nos pasaron la Action pelada): usar el primer slot
        slots = getattr(action, "slots", None)
        if slots:
            slot = slots[0]
    if slot is None:
        # BUGFIX (Kebyn, 2026-09-14): una Action recien creada con
        # bpy.data.actions.new(...) que TODAVIA no se asigno a ningun
        # animation_data.action (ej. _copy_action_range() en
        # operators_segments.py, que arma la action aislada ANTES de
        # empujarla al NLA) no tiene ningun slot -- ni siquiera el
        # "legacy slot" que Blender crea automaticamente al hacer
        # obj.animation_data.action = action. Antes, en ese caso,
        # get_fcurves() devolvia [] (una lista comun), y el codigo que
        # hace get_fcurves(new_action).new(...) para crear fcurves
        # nuevas reventaba con "'list' object has no attribute 'new'"
        # (visto en consola: "[ConcatenarTodo] ... fallo al aislar el
        # tramo sin poses ('list' object has no attribute 'new')" --
        # el segmento terminaba sin pose ni desplazamiento base, y el
        # recorrido "no se reproducia"). Si create=True, se crea el
        # slot que falta -- id_type='OBJECT' porque todas las actions
        # que este addon manipula son de Objects (el armature o el
        # root "cerdo_1"), nunca de otro tipo de ID -- para poder seguir
        # armando el channelbag normalmente.
        if create:
            try:
                slot = action.slots.new(id_type='OBJECT', name=action.name)
            except Exception as e:
                print(f"get_fcurves: no se pudo crear slot para '{action.name}': {e}")
                slot = None
    if slot is None:
        return []

    if create:
        channelbag = _anim_utils.action_ensure_channelbag_for_slot(action, slot)
    else:
        channelbag = _anim_utils.action_get_channelbag_for_slot(action, slot)

    if channelbag is None:
        return []
    return channelbag.fcurves


def get_action_slot(obj):
    """Devuelve el slot activo de animacion de `obj` (o None), compatible
    con versiones sin sistema de slots (donde simplemente no existe)."""
    anim_data = getattr(obj, "animation_data", None)
    if anim_data is None:
        return None
    return getattr(anim_data, "action_slot", None)
