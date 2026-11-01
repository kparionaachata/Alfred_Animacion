# -*- coding: utf-8 -*-
"""
Chicken 1 Animation Studio v1.9
Addon de Blender — Panel N, pestana "Chicken1 Studio"

ESTRUCTURA MODULAR:
  constants.py       — Rutas, listas de bones, presets de expresion, tabla INTERP
  interpolation.py   — 40+ curvas de interpolacion profesional
  properties.py      — PropertyGroups: Chicken1EyeExpressionSettings, Chicken1OrganicFilters,
                        Chicken1BoneOscillationItem, Chicken1BoneOscillationsSettings,
                        Chicken1PoseSlotItem, Chicken1StudioSettings
  pose_utils.py      — Carga de JSONs de poses, interpolacion de bones, open_folder
  operators_base.py  — Operadores de setup, historia, reset, pick/add/edit/move slots
  eye_system.py      — Shape keys de expresion + parpadeo efecto cortina
  operators_anim.py  — Filtros organicos, CONCATENAR, Exportar, Importar, Extraer,
                        Oscilaciones de bones (BoneOsc*)
  config_ops.py      — Guardar / Cargar configuracion de sesion (.json)
  panels.py          — Todos los paneles UI y UIList
"""

bl_info = {
    "name":        "Chicken 1 Animation Studio",
    "author":      "Alfred Pipeline",
    "version":     (2, 0, 0),
    "blender":     (4, 0, 0),
    "location":    "Vista 3D > Barra lateral (N) > Chicken1 Studio",
    "description": "Combina poses, genera animaciones y exporta slots de chicken_1 (slot_NNN_tipo.py)",
    "category":    "Animation",
}

import bpy
from bpy.props import PointerProperty

# ── Importar modulos internos ─────────────────────────────────
# El patrón correcto de Blender: importar primero como módulo,
# recargar si ya estaban cargados (re-instalación en caliente),
# luego importar los símbolos necesarios.
if "properties" in locals():
    import importlib
    importlib.reload(properties)       # type: ignore
    importlib.reload(operators_base)   # type: ignore
    importlib.reload(eye_system)       # type: ignore
    importlib.reload(eye_library)      # type: ignore
    importlib.reload(operators_anim)   # type: ignore
    importlib.reload(operators_segments) # type: ignore
    importlib.reload(path_recorder)    # type: ignore
    importlib.reload(config_ops)       # type: ignore
    importlib.reload(panels)           # type: ignore
else:
    from . import (
        properties,
        operators_base,
        eye_system,
        eye_library,
        operators_anim,
        operators_segments,
        path_recorder,
        config_ops,
        panels,
    )

from .properties      import Chicken1EyeExpressionSettings, Chicken1OrganicFilters, \
                             Chicken1EyeLibEntry, Chicken1PoseSlotItem, \
                             Chicken1EyeSlotItem, Chicken1StudioSettings, \
                             Chicken1BoneOscillationItem, Chicken1BoneOscillationsSettings, \
                             Chicken1BlinkInterval, Chicken1EyeExprInterval, \
                             Chicken1ObjectImportItem, Chicken1ObjectImportsSettings, \
                             Chicken1ThrowWaypoint, Chicken1ThrowItem, Chicken1ThrowsSettings, \
                             Chicken1SegmentPoseSlot, Chicken1AnimSegment, Chicken1AnimSegmentsSettings
from .operators_base  import (
    CH1ST_OT_SetArmature, CH1ST_OT_OpenAlfredBlend, CH1ST_OT_OpenPosesFolder, CH1ST_OT_OpenAnimFolder,
    CH1ST_OT_RefreshPoses, CH1ST_OT_ImportPose, CH1ST_OT_ApplyImportedPose, CH1ST_OT_ReloadHistoria, CH1ST_OT_ApplyKeyPointToRoot,
    CH1ST_OT_Reset,
    CH1ST_OT_AddActionPose, CH1ST_OT_EditActionPose,
    CH1ST_OT_RemoveActionPose, CH1ST_OT_MoveActionPose,
    CH1ST_OT_AddEyeSlot, CH1ST_OT_RemoveEyeSlot, CH1ST_OT_DuplicateEyeSlot,
    CH1ST_OT_MoveEyeSlot, CH1ST_OT_EditEyeSlot,
    CH1ST_OT_ResetEyeSequence,
    CH1ST_OT_BlinkIntervalAdd, CH1ST_OT_BlinkIntervalRemove,
    CH1ST_OT_BlinkIntervalDuplicate, CH1ST_OT_BlinkIntervalMove,
    CH1ST_OT_ExprIntervalAdd, CH1ST_OT_ExprIntervalRemove,
    CH1ST_OT_ExprIntervalDuplicate, CH1ST_OT_ExprIntervalMove,
    CH1ST_OT_ImportEyeSlotFromJson,
    CH1ST_OT_CaptureEyeToSlot,
    CH1ST_OT_PreviewEyeState,
    CH1ST_OT_Concatenate2,
)
from .eye_system      import (
    CH1ST_OT_BuildEyeShapeKeys,
    CH1ST_OT_ApplyEyeExpressionPreview,
    CH1ST_OT_ResetEyeExpressions,
)
from .eye_library     import (
    CH1ST_OT_SaveEyeExpression,
    CH1ST_OT_RefreshEyeLibrary,
    CH1ST_OT_LoadEyeExpression,
    CH1ST_OT_ImportEyeExpression,
    CH1ST_OT_KeyframeEyeExpression,
    CH1ST_OT_OpenEyeLibFolder,
    CH1ST_OT_ResetEyeTransforms,
    CH1ST_OT_ApplyEyeTransforms,
    CH1ST_OT_ApplyEyeGeometry,
)
from .operators_anim  import (
    CH1ST_OT_Concatenate,
    CH1ST_OT_ExportAnimation, CH1ST_OT_ImportAnimation,
    CH1ST_OT_ExtractPose,
    CH1ST_OT_BoneOscAddItem,
    CH1ST_OT_BoneOscRemoveItem,
    CH1ST_OT_BoneOscMoveItem,
    CH1ST_OT_BoneOscDuplicateItem,
    CH1ST_OT_BoneOscToggleItem,
    CH1ST_OT_BoneOscPickBone,
    CH1ST_OT_ObjImportAddItem,
    CH1ST_OT_ObjImportRemoveItem,
    CH1ST_OT_ObjImportMoveItem,
    CH1ST_OT_ObjImportDuplicateItem,
    CH1ST_OT_ObjImportToggleItem,
    CH1ST_OT_ObjImportLoadToEditor,
    CH1ST_OT_ObjImportUpdateItem,
    CH1ST_OT_ObjImportPreviewNow,
    # Lanzar / Recoger
    CH1ST_OT_ThrowAddItem,
    CH1ST_OT_ThrowRemoveItem,
    CH1ST_OT_ThrowToggleItem,
    CH1ST_OT_ThrowLoadToEditor,
    CH1ST_OT_ThrowUpdateItem,
    CH1ST_OT_ThrowPickBone,
    CH1ST_OT_ThrowBrowseBlend,
    CH1ST_OT_ThrowImportObject,
    CH1ST_OT_ThrowDetectArmature,
    CH1ST_OT_ThrowPickDestFromCursor,
    CH1ST_OT_ThrowAddWaypoint,
    CH1ST_OT_ThrowRemoveWaypoint,
    CH1ST_OT_ThrowWaypointFromCursor,
    CH1ST_OT_ThrowApply,
    CH1ST_OT_ThrowClearKeyframes,
    CH1ST_OT_ObjImportBrowseBlend,
    CH1ST_OT_ObjImportDetectArmature,
)
from .operators_segments import (
    CH1SEG_OT_Add,
    CH1SEG_OT_AutoSplitFromConfig,
    CH1SEG_OT_ConcatenateAll,
    CH1SEG_OT_Remove,
    CH1SEG_OT_Move,
    CH1SEG_OT_Duplicate,
    CH1SEG_OT_PickPoseMid,
    CH1SEG_OT_SetFrameStart,
    CH1SEG_OT_SetFrameMid,
    CH1SEG_OT_SetFrameEnd,
    CH1SEG_OT_Apply,
    CH1SEG_OT_SaveConfig,
    CH1SEG_OT_LoadConfig,
    CH1SEG_OT_PlaySegment,
    CH1SEG_OT_PauseSegment,
    CH1SEG_OT_StopSegment,
    CH1SEG_OT_ToggleEnabled,
    CH1SEG_OT_AddActionPoseSeg,
    CH1SEG_OT_EditActionPoseSeg,
    CH1SEG_OT_RemoveActionPoseSeg,
    CH1SEG_OT_MoveActionPoseSeg,
    CH1SEG_OT_QuickPoseExtract,
    CH1SEG_OT_QuickPoseImport,
    CH1SEG_OT_ToggleConfig,
    CH1SEG_OT_SetFrameStartEdit,
    CH1SEG_OT_UpdateFromEstimacion,
    CH1SEG_UL_Segments,
)
from .path_recorder import (
    CH1PathPoint,
    CH1ParadaFrames,
    CH1WalkStyleEntry,
    CH1PathSettings,
    CH1PR_OT_ToggleRecording,
    CH1PR_OT_TogglePathViz,
    CH1PR_OT_RemoveLast,
    CH1PR_OT_ClearPath,
    CH1PR_OT_SyncParadasFrames,
    CH1PR_OT_GenerateSlots,
    CH1PR_OT_OpenBlendFile,
    CH1PR_OT_PreviewPath,
    CH1PR_OT_ResetPreview,
    CH1PR_OT_SetAnimRange,
    CH1PR_OT_ExportSlots,
    register_path_recorder_ch1,
    unregister_path_recorder_ch1,
)
from .config_ops      import (
    CH1ST_OT_SaveConfig, CH1ST_OT_LoadConfig, CH1ST_OT_OpenConfigFolder,
    CH1ST_OT_SaveEyeConfig, CH1ST_OT_LoadEyeConfig,
)
from .panels          import (
    CH1ST_UL_ActionPoses,
    CH1ST_UL_EyeSlots,
    CH1ST_UL_BlinkIntervals,
    CH1ST_UL_EyeExprIntervals,
    CH1ST_PT_Main,
    CH1ST_PT_OrganicFilters,
    CH1ST_PT_BoneOscillations,
    CH1ST_PT_ObjectImports,
    CH1ST_PT_EyeSequence,
    CH1ST_PT_Export, CH1ST_PT_ConfigSession, CH1ST_PT_Extract,
    CH1ST_PT_PathRecorder,
    CH1SEG_UL_SegmentsList,
    CH1ST_PT_Segments,
)

# ── Lista de clases en orden de registro ─────────────────────
classes = (
    # PropertyGroups (deben ir primero)
    Chicken1EyeExpressionSettings,
    Chicken1OrganicFilters,
    Chicken1BoneOscillationItem,
    Chicken1BoneOscillationsSettings,
    Chicken1ThrowWaypoint,
    Chicken1ThrowItem,
    Chicken1ThrowsSettings,
    Chicken1ObjectImportItem,
    Chicken1ObjectImportsSettings,
    Chicken1BlinkInterval,
    Chicken1EyeExprInterval,
    Chicken1EyeLibEntry,
    Chicken1PoseSlotItem,
    Chicken1EyeSlotItem,
    Chicken1StudioSettings,
    # Operadores de setup y secuencia
    CH1ST_OT_SetArmature, CH1ST_OT_OpenAlfredBlend,
    CH1ST_OT_OpenPosesFolder,
    CH1ST_OT_OpenAnimFolder,
    CH1ST_OT_RefreshPoses, CH1ST_OT_ImportPose, CH1ST_OT_ApplyImportedPose,
    CH1ST_OT_ReloadHistoria,
    CH1ST_OT_ApplyKeyPointToRoot,
    CH1ST_OT_Reset,
    CH1ST_OT_AddActionPose,
    CH1ST_OT_EditActionPose,
    CH1ST_OT_RemoveActionPose,
    CH1ST_OT_MoveActionPose,
    # Operadores de secuencia de ojos
    CH1ST_OT_AddEyeSlot,
    CH1ST_OT_RemoveEyeSlot,
    CH1ST_OT_DuplicateEyeSlot,
    CH1ST_OT_MoveEyeSlot,
    CH1ST_OT_EditEyeSlot,
    CH1ST_OT_ResetEyeSequence,
    CH1ST_OT_BlinkIntervalAdd,
    CH1ST_OT_BlinkIntervalRemove,
    CH1ST_OT_BlinkIntervalDuplicate,
    CH1ST_OT_BlinkIntervalMove,
    CH1ST_OT_ExprIntervalAdd,
    CH1ST_OT_ExprIntervalRemove,
    CH1ST_OT_ExprIntervalDuplicate,
    CH1ST_OT_ExprIntervalMove,
    CH1ST_OT_ImportEyeSlotFromJson,
    CH1ST_OT_CaptureEyeToSlot,
    CH1ST_OT_PreviewEyeState,
    CH1ST_OT_Concatenate2,
    # Sistema de ojos (shape keys base)
    CH1ST_OT_BuildEyeShapeKeys,
    CH1ST_OT_ApplyEyeExpressionPreview,
    CH1ST_OT_ResetEyeExpressions,
    # Libreria de ojos
    CH1ST_OT_SaveEyeExpression,
    CH1ST_OT_RefreshEyeLibrary,
    CH1ST_OT_LoadEyeExpression,
    CH1ST_OT_ImportEyeExpression,
    CH1ST_OT_KeyframeEyeExpression,
    CH1ST_OT_OpenEyeLibFolder,
    CH1ST_OT_ResetEyeTransforms,
    CH1ST_OT_ApplyEyeTransforms,
    CH1ST_OT_ApplyEyeGeometry,
    # Animacion principal
    CH1ST_OT_Concatenate,
    CH1ST_OT_ExportAnimation,
    CH1ST_OT_ImportAnimation,
    CH1ST_OT_ExtractPose,
    # Oscilaciones de bones personalizadas
    CH1ST_OT_BoneOscAddItem,
    CH1ST_OT_BoneOscRemoveItem,
    CH1ST_OT_BoneOscMoveItem,
    CH1ST_OT_BoneOscDuplicateItem,
    CH1ST_OT_BoneOscToggleItem,
    CH1ST_OT_BoneOscPickBone,
    # Importacion de objetos (armas, escudos, props)
    CH1ST_OT_ObjImportAddItem,
    CH1ST_OT_ObjImportRemoveItem,
    CH1ST_OT_ObjImportMoveItem,
    CH1ST_OT_ObjImportDuplicateItem,
    CH1ST_OT_ObjImportToggleItem,
    CH1ST_OT_ObjImportLoadToEditor,
    CH1ST_OT_ObjImportUpdateItem,
    CH1ST_OT_ObjImportPreviewNow,
    CH1ST_OT_ObjImportBrowseBlend,
    CH1ST_OT_ObjImportDetectArmature,
    # Lanzar / Recoger
    CH1ST_OT_ThrowAddItem,
    CH1ST_OT_ThrowRemoveItem,
    CH1ST_OT_ThrowToggleItem,
    CH1ST_OT_ThrowLoadToEditor,
    CH1ST_OT_ThrowUpdateItem,
    CH1ST_OT_ThrowPickBone,
    CH1ST_OT_ThrowBrowseBlend,
    CH1ST_OT_ThrowImportObject,
    CH1ST_OT_ThrowDetectArmature,
    CH1ST_OT_ThrowPickDestFromCursor,
    CH1ST_OT_ThrowAddWaypoint,
    CH1ST_OT_ThrowRemoveWaypoint,
    CH1ST_OT_ThrowWaypointFromCursor,
    CH1ST_OT_ThrowApply,
    CH1ST_OT_ThrowClearKeyframes,
    # Configuracion de sesion
    CH1ST_OT_SaveConfig,
    CH1ST_OT_LoadConfig,
    CH1ST_OT_OpenConfigFolder,
    CH1ST_OT_SaveEyeConfig,
    CH1ST_OT_LoadEyeConfig,
    # Paso 3: Segmentos
    Chicken1SegmentPoseSlot,
    Chicken1AnimSegment,
    Chicken1AnimSegmentsSettings,
    CH1SEG_OT_Add,
    CH1SEG_OT_AutoSplitFromConfig,
    CH1SEG_OT_ConcatenateAll,
    CH1SEG_OT_Remove,
    CH1SEG_OT_Move,
    CH1SEG_OT_Duplicate,
    CH1SEG_OT_PickPoseMid,
    CH1SEG_OT_SetFrameStart,
    CH1SEG_OT_SetFrameMid,
    CH1SEG_OT_SetFrameEnd,
    CH1SEG_OT_Apply,
    CH1SEG_OT_SaveConfig,
    CH1SEG_OT_LoadConfig,
    CH1SEG_OT_PlaySegment,
    CH1SEG_OT_PauseSegment,
    CH1SEG_OT_StopSegment,
    CH1SEG_OT_ToggleEnabled,
    CH1SEG_OT_AddActionPoseSeg,
    CH1SEG_OT_EditActionPoseSeg,
    CH1SEG_OT_RemoveActionPoseSeg,
    CH1SEG_OT_MoveActionPoseSeg,
    CH1SEG_OT_QuickPoseExtract,
    CH1SEG_OT_QuickPoseImport,
    CH1SEG_OT_ToggleConfig,
    CH1SEG_OT_SetFrameStartEdit,
    CH1SEG_OT_UpdateFromEstimacion,
    CH1SEG_UL_Segments,
    # Path Recorder (Paso 2 recorrido)
    CH1PathPoint,
    CH1ParadaFrames,
    CH1WalkStyleEntry,
    CH1PathSettings,
    CH1PR_OT_ToggleRecording,
    CH1PR_OT_TogglePathViz,
    CH1PR_OT_RemoveLast,
    CH1PR_OT_ClearPath,
    CH1PR_OT_SyncParadasFrames,
    CH1PR_OT_GenerateSlots,
    CH1PR_OT_OpenBlendFile,
    CH1PR_OT_PreviewPath,
    CH1PR_OT_ResetPreview,
    CH1PR_OT_SetAnimRange,
    CH1PR_OT_ExportSlots,
    # UI
    CH1ST_UL_ActionPoses,
    CH1ST_UL_EyeSlots,
    CH1ST_UL_BlinkIntervals,
    CH1ST_UL_EyeExprIntervals,
    CH1ST_PT_PathRecorder,
    CH1SEG_UL_SegmentsList,
    CH1ST_PT_Main,
    CH1ST_PT_OrganicFilters,
    CH1ST_PT_BoneOscillations,
    CH1ST_PT_ObjectImports,
    CH1ST_PT_EyeSequence,
    CH1ST_PT_Export,
    CH1ST_PT_ConfigSession,
    CH1ST_PT_Extract,
    CH1ST_PT_Segments,
)

def register():
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
        bpy.utils.register_class(cls)
    bpy.types.Scene.ch1st = PointerProperty(type=Chicken1StudioSettings)
    bpy.types.Scene.ch1_segs = PointerProperty(type=Chicken1AnimSegmentsSettings)
    register_path_recorder_ch1()
    print("Chicken 1 Animation Studio v2.0 [modular]: registrado OK")

def unregister():
    unregister_path_recorder_ch1()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.ch1st
    if hasattr(bpy.types.Scene, "ch1_segs"):
        del bpy.types.Scene.ch1_segs
    print("Chicken 1 Animation Studio: desregistrado")

if __name__ == "__main__":
    register()
