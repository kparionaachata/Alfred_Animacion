# -*- coding: utf-8 -*-
"""
Rat 1 Animation Studio v0.2 (Paso 1, 2 y 3)
Addon de Blender — Panel N, pestana "Rat 1 Studio"

ALCANCE: Paso 1 (grabar puntos por seleccion de faces, detectar tramos),
Paso 2 (configuracion/estimacion/exportacion de slots, con biomecanica
cuadrupeda real de caminar/saltar_subir/saltar_bajar) y, desde v0.2,
Paso 3 -- NUCLEO de segmentos/poses/NLA/Concatenar (pedido explicito de
Kebyn, port reducido desde alfred_animation_studio): crear segmentos
sobre la animacion de recorrido, agregar poses (keyframes) dentro de
cada uno, aislarlos con pistas NLA propias y Concatenar la secuencia
completa. Sin sistema de ojos, sin Lanzar/Recoger objetos, sin
Invisibilidad de Malla, sin filtros organicos -- rat_1 no tiene esos
sistemas todavia. Ver docs/PORT_NOTES.md para el detalle completo de
que se porto y que sigue fuera de alcance.

ESTRUCTURA MODULAR (portada desde alfred_animation_studio, reducida):
  constants.py            — Nombres de objetos de rat_1 + bones posables + interpolaciones (Paso 3)
  properties.py           — PropertyGroups: Rat1StudioSettings, Rat1AnimSegment(s) (Paso 3)
  interpolation.py        — Curvas de interpolacion profesional (Paso 3, generico)
  pose_utils.py           — Carga/interpolacion de poses .json (Paso 3, generico)
  path_recorder.py        — Paso 1 (grabacion) + Paso 2 (preview/export, con biomecanica real)
  generate_slots_rat_1.py — Generadores de slots con biomecanica cuadrupeda (caminar/saltar_subir/saltar_bajar/parada/idle)
  operators_segments.py   — Paso 3: CRUD de segmentos, poses/keyframes, NLA, Concatenar
  config_ops.py           — Guardar / cargar el recorrido (escenario_registro.json)
  panels.py               — Panel UI (Paso 1 + Paso 2 + Paso 3)
"""

bl_info = {
    "name":        "Rat 1 Animation Studio",
    "author":      "Alfred Pipeline",
    "version":     (0, 2, 0),
    "blender":     (4, 0, 0),
    "location":    "Vista 3D > Barra lateral (N) > Rat 1 Studio",
    "description": "Recorrido (Paso 1 y 2) + Segmentos/Poses/NLA/Concatenar (Paso 3) para rat_1",
    "category":    "Animation",
}

import bpy
from bpy.props import PointerProperty

if "properties" in locals():
    import importlib
    importlib.reload(constants)            # type: ignore
    importlib.reload(interpolation)        # type: ignore
    importlib.reload(pose_utils)           # type: ignore
    importlib.reload(properties)           # type: ignore
    importlib.reload(path_recorder)        # type: ignore
    importlib.reload(organic_filters)      # type: ignore
    importlib.reload(operators_segments)   # type: ignore
    importlib.reload(config_ops)           # type: ignore
    importlib.reload(panels)               # type: ignore
else:
    from . import (
        constants,
        interpolation,
        pose_utils,
        properties,
        path_recorder,
        organic_filters,
        operators_segments,
        config_ops,
        panels,
    )

from .properties import (
    Rat1StudioSettings,
    Rat1SegmentPoseSlot,
    Rat1OrganicFilters,
    Rat1BoneBlockInterval,
    Rat1BoneBlockEntry,
    Rat1AnimSegment,
    Rat1AnimSegmentsSettings,
)
from .path_recorder import (
    RAT1PathPoint,
    RAT1ParadaFrames,
    RAT1WalkStyleEntry,
    RAT1PathSettings,
    RAT1PR_OT_ToggleRecording,
    RAT1PR_OT_TogglePathViz,
    RAT1PR_OT_RemoveLast,
    RAT1PR_OT_RemovePoint,
    RAT1PR_OT_ClearPath,
    RAT1PR_OT_SyncParadasFrames,
    RAT1PR_OT_GenerateSlots,
    RAT1PR_OT_OpenBlendFile,
    RAT1PR_OT_PreviewPath,
    RAT1PR_OT_ResetPreview,
    RAT1PR_OT_SetAnimRange,
    RAT1PR_OT_ExportSlots,
    register_path_recorder,
    unregister_path_recorder,
)
from .operators_segments import register_segments, unregister_segments
from .config_ops import RAT1ST_OT_SaveConfig, RAT1ST_OT_LoadConfig
from .panels import RAT1ST_PT_PathRecorder, RAT1SEG_PT_Segments, RAT1SEG_PT_ConfigSession

# ── Lista de clases en orden de registro ─────────────────────
classes = (
    Rat1StudioSettings,
    Rat1SegmentPoseSlot,
    Rat1OrganicFilters,
    Rat1BoneBlockInterval,
    Rat1BoneBlockEntry,
    Rat1AnimSegment,
    Rat1AnimSegmentsSettings,
    RAT1ST_OT_SaveConfig,
    RAT1ST_OT_LoadConfig,
    # NOTA: las clases del Path Recorder (RAT1PathPoint, RAT1ParadaFrames,
    # RAT1WalkStyleEntry, RAT1PathSettings, RAT1PR_OT_*) NO se listan aqui:
    # se registran exclusivamente dentro de register_path_recorder()
    # (path_recorder.py), mismo patron que Alfred (ver comentario largo
    # en el __init__.py de alfred_animation_studio sobre por que). Los
    # operadores/UIList del Paso 3 (operators_segments.py) siguen el
    # mismo patron: se registran via register_segments()/unregister_segments().
    RAT1ST_PT_PathRecorder,
    RAT1SEG_PT_Segments,
    RAT1SEG_PT_ConfigSession,
)


def register():
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
        bpy.utils.register_class(cls)
    bpy.types.Scene.rat1st = PointerProperty(type=Rat1StudioSettings)
    bpy.types.Scene.rat1_segs = PointerProperty(type=Rat1AnimSegmentsSettings)
    register_path_recorder()
    register_segments()
    print("Rat 1 Animation Studio v0.2 [Paso 1, 2 y 3]: registrado OK")


def unregister():
    unregister_segments()
    unregister_path_recorder()
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
    if hasattr(bpy.types.Scene, "rat1st"):
        del bpy.types.Scene.rat1st
    if hasattr(bpy.types.Scene, "rat1_segs"):
        del bpy.types.Scene.rat1_segs
    print("Rat 1 Animation Studio: desregistrado")


if __name__ == "__main__":
    register()
