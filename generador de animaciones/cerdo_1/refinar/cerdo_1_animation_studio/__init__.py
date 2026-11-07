# -*- coding: utf-8 -*-
"""
Cerdo_1 Animation Studio v1.9
Addon de Blender — Panel N, pestana "Cerdo_1 Studio"

ESTRUCTURA MODULAR:
  constants.py       — Rutas, listas de bones, presets de expresion, tabla INTERP
  interpolation.py   — 40+ curvas de interpolacion profesional
  properties.py      — PropertyGroups: Cerdo_1EyeExpressionSettings, Cerdo_1OrganicFilters,
                        Cerdo_1BoneOscillationItem, Cerdo_1BoneOscillationsSettings,
                        Cerdo_1PoseSlotItem, Cerdo_1StudioSettings
  pose_utils.py      — Carga de JSONs de poses, interpolacion de bones, open_folder
  operators_base.py  — Operadores de setup, historia, reset, pick/add/edit/move slots
  eye_system.py      — Shape keys de expresion + parpadeo efecto cortina
  operators_anim.py  — Filtros organicos, CONCATENAR, Exportar, Importar, Extraer,
                        Oscilaciones de bones (BoneOsc*)
  config_ops.py      — Guardar / Cargar configuracion de sesion (.json)
  panels.py          — Todos los paneles UI y UIList
"""

bl_info = {
    "name":        "Cerdo 1 Animation Studio",
    "author":      "Cerdo_1 Pipeline",
    "version":     (2, 3, 0),
    "blender":     (4, 0, 0),
    "location":    "Cerdo 1 Studio",
    "description": "Combina poses, genera animaciones y exporta al flujo cerdo_1_*.py (slot_NNN_tipo.py). v2.2: guion 2.0 (audio, objetos, movimiento, sonidos, camara). v2.3: panel 10 Tunel (cavar): dadas la coordenada de inicio y la final, Cerdo_1 cava / pica el tunel solo",
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
    from . import woodcut_animation
    importlib.reload(woodcut_animation)
    importlib.reload(properties)       # type: ignore
    importlib.reload(operators_base)   # type: ignore
    importlib.reload(eye_system)       # type: ignore
    importlib.reload(eye_library)      # type: ignore
    importlib.reload(operators_anim)   # type: ignore
    importlib.reload(operators_segments) # type: ignore
    from . import jump_motion
    importlib.reload(jump_motion)
    importlib.reload(path_recorder)    # type: ignore
    from . import guion_v2, audio_import, audio_ops
    importlib.reload(guion_v2)
    importlib.reload(audio_import)
    importlib.reload(audio_ops)
    from . import objetos_mundo, objetos_ops
    importlib.reload(objetos_mundo)
    importlib.reload(objetos_ops)
    from . import motor_cerdo_1, movimiento_ops
    importlib.reload(motor_cerdo_1)
    importlib.reload(movimiento_ops)
    from . import claves_util, camara_guion, sonidos_guion, escena_ops
    importlib.reload(claves_util)
    importlib.reload(camara_guion)
    importlib.reload(sonidos_guion)
    importlib.reload(escena_ops)
    from . import preparar_escena, reproducir_guion, reproducir_ops
    importlib.reload(preparar_escena)
    importlib.reload(reproducir_guion)
    importlib.reload(reproducir_ops)
    from . import tunel, tunel_ops
    importlib.reload(tunel)
    importlib.reload(tunel_ops)
    from . import bloques, bloques_ops
    importlib.reload(bloques)
    importlib.reload(bloques_ops)
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
        guion_v2,
        audio_import,
        audio_ops,
        objetos_mundo,
        objetos_ops,
        motor_cerdo_1,
        movimiento_ops,
        claves_util,
        camara_guion,
        sonidos_guion,
        escena_ops,
        preparar_escena,
        reproducir_guion,
        reproducir_ops,
        tunel,
        tunel_ops,
    )

from .properties      import Cerdo_1EyeExpressionSettings, Cerdo_1OrganicFilters, \
                             Cerdo_1EyeLibEntry, Cerdo_1PoseSlotItem, \
                             Cerdo_1EyeSlotItem, Cerdo_1StudioSettings, \
                             Cerdo_1BoneOscillationItem, Cerdo_1BoneOscillationsSettings, \
                             Cerdo_1BlinkInterval, Cerdo_1LaughInterval, Cerdo_1UnderstandInterval, \
                             Cerdo_1EyeExprInterval, \
                             Cerdo_1EyeShapeKeySetup, \
                             Cerdo_1ObjectImportItem, Cerdo_1ObjectImportsSettings, \
                             Cerdo_1ThrowWaypoint, Cerdo_1ThrowItem, Cerdo_1ThrowsSettings, \
                             Cerdo_1HideMeshItem, Cerdo_1HideMeshSettings, \
                             Cerdo_1BoneBlockInterval, Cerdo_1BoneBlockEntry, \
                             Cerdo_1SegmentPoseSlot, Cerdo_1AnimSegment, Cerdo_1AnimSegmentsSettings
from .operators_base  import (
    CERDO_1_ST_OT_SetArmature, CERDO_1_ST_OT_OpenCerdo_1Blend, CERDO_1_ST_OT_OpenPosesFolder, CERDO_1_ST_OT_OpenAnimFolder,
    CERDO_1_ST_OT_RefreshPoses, CERDO_1_ST_OT_ImportPose, CERDO_1_ST_OT_ApplyImportedPose, CERDO_1_ST_OT_ReloadHistoria, CERDO_1_ST_OT_ApplyKeyPointToRoot,
    CERDO_1_ST_OT_Reset,
    CERDO_1_ST_OT_AddActionPose, CERDO_1_ST_OT_EditActionPose,
    CERDO_1_ST_OT_RemoveActionPose, CERDO_1_ST_OT_MoveActionPose,
    CERDO_1_ST_OT_AddEyeSlot, CERDO_1_ST_OT_RemoveEyeSlot, CERDO_1_ST_OT_DuplicateEyeSlot,
    CERDO_1_ST_OT_MoveEyeSlot, CERDO_1_ST_OT_EditEyeSlot,
    CERDO_1_ST_OT_ResetEyeSequence,
    CERDO_1_ST_OT_BlinkIntervalAdd, CERDO_1_ST_OT_BlinkIntervalRemove,
    CERDO_1_ST_OT_BlinkIntervalDuplicate, CERDO_1_ST_OT_BlinkIntervalMove,
    CERDO_1_ST_OT_LaughIntervalAdd, CERDO_1_ST_OT_LaughIntervalRemove,
    CERDO_1_ST_OT_LaughIntervalDuplicate, CERDO_1_ST_OT_LaughIntervalMove,
    CERDO_1_ST_OT_UnderstandIntervalAdd, CERDO_1_ST_OT_UnderstandIntervalRemove,
    CERDO_1_ST_OT_UnderstandIntervalDuplicate, CERDO_1_ST_OT_UnderstandIntervalMove,
    CERDO_1_ST_OT_ExprIntervalAdd, CERDO_1_ST_OT_ExprIntervalRemove,
    CERDO_1_ST_OT_ExprIntervalDuplicate, CERDO_1_ST_OT_ExprIntervalMove,
    CERDO_1_ST_OT_EditExprInterval,
    CERDO_1_ST_OT_ConcatenateExprIntervals,
    CERDO_1_ST_OT_ImportEyeSlotFromJson,
    CERDO_1_ST_OT_CaptureEyeToSlot,
    CERDO_1_ST_OT_PreviewEyeState,
    CERDO_1_ST_OT_Concatenate2,
)
from .eye_system      import (
    CERDO_1_ST_OT_BuildEyeShapeKeys,
    CERDO_1_ST_OT_ApplyEyeExpressionPreview,
    CERDO_1_ST_OT_ResetEyeExpressions,
)
from .eye_library     import (
    CERDO_1_ST_OT_SaveEyeExpression,
    CERDO_1_ST_OT_RefreshEyeLibrary,
    CERDO_1_ST_OT_LoadEyeExpression,
    CERDO_1_ST_OT_ImportEyeExpression,
    CERDO_1_ST_OT_KeyframeEyeExpression,
    CERDO_1_ST_OT_OpenEyeLibFolder,
    CERDO_1_ST_OT_ResetEyeTransforms,
    CERDO_1_ST_OT_ApplyEyeTransforms,
    CERDO_1_ST_OT_ApplyEyeGeometry,
)
from .operators_anim  import (
    CERDO_1_ST_OT_Concatenate,
    CERDO_1_ST_OT_ExportAnimation, CERDO_1_ST_OT_ImportAnimation,
    CERDO_1_ST_OT_ExtractPose,
    CERDO_1_ST_OT_BoneOscAddItem,
    CERDO_1_ST_OT_BoneOscRemoveItem,
    CERDO_1_ST_OT_BoneOscMoveItem,
    CERDO_1_ST_OT_BoneOscDuplicateItem,
    CERDO_1_ST_OT_BoneOscToggleItem,
    CERDO_1_ST_OT_BoneOscPickBone,
    CERDO_1_ST_OT_ObjImportAddItem,
    CERDO_1_ST_OT_ObjImportRemoveItem,
    CERDO_1_ST_OT_ObjImportMoveItem,
    CERDO_1_ST_OT_ObjImportDuplicateItem,
    CERDO_1_ST_OT_ObjImportToggleItem,
    CERDO_1_ST_OT_ObjImportLoadToEditor,
    CERDO_1_ST_OT_ObjImportUpdateItem,
    CERDO_1_ST_OT_ObjImportPreviewNow,
    # Lanzar / Recoger
    CERDO_1_ST_OT_ThrowAddItem,
    CERDO_1_ST_OT_ThrowRemoveItem,
    CERDO_1_ST_OT_ThrowToggleItem,
    CERDO_1_ST_OT_ThrowLoadToEditor,
    CERDO_1_ST_OT_ThrowUpdateItem,
    CERDO_1_ST_OT_ThrowPickBone,
    CERDO_1_ST_OT_ThrowBrowseBlend,
    CERDO_1_ST_OT_ThrowImportObject,
    CERDO_1_ST_OT_ThrowSyncFromObject,
    CERDO_1_ST_OT_ThrowDetectArmature,
    CERDO_1_ST_OT_ThrowPickDestFromCursor,
    CERDO_1_ST_OT_ThrowAddWaypoint,
    CERDO_1_ST_OT_ThrowRemoveWaypoint,
    CERDO_1_ST_OT_ThrowWaypointFromCursor,
    CERDO_1_ST_OT_ThrowApply,
    CERDO_1_ST_OT_ThrowClearKeyframes,
    CERDO_1_ST_OT_ObjImportBrowseBlend,
    CERDO_1_ST_OT_ObjImportDetectArmature,
    # Invisibilidad de Malla
    CERDO_1_ST_OT_HideMeshAddItem,
    CERDO_1_ST_OT_HideMeshRemoveItem,
    CERDO_1_ST_OT_HideMeshToggleItem,
    CERDO_1_ST_OT_HideMeshLoadToEditor,
    CERDO_1_ST_OT_HideMeshUpdateItem,
    CERDO_1_ST_OT_HideMeshPickObject,
)
from .operators_segments import (
    CERDO_1SEG_OT_Add,
    CERDO_1SEG_OT_AutoSplitFromConfig,
    CERDO_1SEG_OT_UpdateFromEstimacion,
    CERDO_1SEG_OT_Remove,
    CERDO_1SEG_OT_AddBoneInterval,
    CERDO_1SEG_OT_RemoveBoneInterval,
    CERDO_1SEG_OT_Move,
    CERDO_1SEG_OT_Duplicate,
    CERDO_1SEG_OT_PickPoseMid,
    CERDO_1SEG_OT_SetFrameStart,
    CERDO_1SEG_OT_SetFrameMid,
    CERDO_1SEG_OT_SetFrameEnd,
    CERDO_1SEG_OT_Apply,
    CERDO_1SEG_OT_ConcatenateAll,
    CERDO_1SEG_OT_SaveConfig,
    CERDO_1SEG_OT_LoadConfig,
    CERDO_1SEG_OT_PlaySegment,
    CERDO_1SEG_OT_PauseSegment,
    CERDO_1SEG_OT_StopSegment,
    CERDO_1SEG_OT_PlaySegmentRecorrido,
    CERDO_1SEG_OT_ToggleEnabled,
    CERDO_1SEG_OT_AddActionPoseSeg,
    CERDO_1SEG_OT_EditActionPoseSeg,
    CERDO_1SEG_OT_QuickPoseExtract,
    CERDO_1SEG_OT_QuickPoseImport,
    CERDO_1SEG_OT_RateActionPoseSeg,
    CERDO_1SEG_OT_RemoveActionPoseSeg,
    CERDO_1SEG_OT_MoveActionPoseSeg,
    CERDO_1SEG_OT_DuplicateActionPoseSeg,
    CERDO_1SEG_OT_ToggleConfig,
    CERDO_1SEG_OT_SetFrameStartEdit,
    CERDO_1SEG_OT_PreviewActionPose,
    CERDO_1SEG_OT_EnterEditPose,
    CERDO_1SEG_OT_SaveEditedPose,
    CERDO_1SEG_UL_Segments,
)
from .path_recorder import (
    CERDO_1PathPoint,
    CERDO_1ParadaFrames,
    CERDO_1WalkStyleEntry,
    CERDO_1PathSettings,
    CERDO_1PR_OT_ToggleRecording,
    CERDO_1PR_OT_RemoveLast,
    CERDO_1PR_OT_RemovePoint,
    CERDO_1PR_OT_ClearPath,
    CERDO_1PR_OT_SyncParadasFrames,
    CERDO_1PR_OT_GenerateSlots,
    CERDO_1PR_OT_OpenBlendFile,
    CERDO_1PR_OT_PreviewPath,
    CERDO_1PR_OT_ResetPreview,
    CERDO_1PR_OT_SetAnimRange,
    CERDO_1PR_OT_ExportSlots,
    register_path_recorder,
    unregister_path_recorder,
)
from .config_ops      import (
    CERDO_1_ST_OT_SaveConfig, CERDO_1_ST_OT_LoadConfig, CERDO_1_ST_OT_OpenConfigFolder,
    CERDO_1_ST_OT_SaveEyeConfig, CERDO_1_ST_OT_LoadEyeConfig,
)
from .panels          import (
    CERDO_1_ST_UL_ActionPoses,
    CERDO_1_ST_UL_EyeSlots,
    CERDO_1_ST_UL_BlinkIntervals,
    CERDO_1_ST_UL_LaughIntervals,
    CERDO_1_ST_UL_UnderstandIntervals,
    CERDO_1_ST_UL_EyeExprIntervals,
    CERDO_1_ST_PT_Main,
    CERDO_1_ST_PT_OrganicFilters,
    CERDO_1_ST_PT_BoneOscillations,
    CERDO_1_ST_PT_ObjectImports,
    CERDO_1_ST_PT_EyeSequence,
    CERDO_1_ST_PT_Export, CERDO_1_ST_PT_ConfigSession, CERDO_1_ST_PT_Extract,
    CERDO_1_ST_PT_PathRecorder,
    CERDO_1SEG_UL_SegmentsList,
    CERDO_1_ST_PT_Segments,
)
from .audio_ops import (
    CERDO_1_ST_OT_AudioImportar, CERDO_1_ST_OT_AudioSincronizar, CERDO_1_ST_OT_AudioInicio, CERDO_1_ST_OT_AudioQuitar, CERDO_1_ST_PT_Audio,
)
from .objetos_ops import (
    CERDO_1_ST_OT_ObjCapturarAgarre, CERDO_1_ST_OT_ObjCapturarEspalda, CERDO_1_ST_OT_ObjAplicar, CERDO_1_ST_PT_Objetos,
)
from .movimiento_ops import (
    CERDO_1_ST_OT_MovComparar, CERDO_1_ST_OT_MovHornear, CERDO_1_ST_OT_MovAprobar, CERDO_1_ST_PT_Movimiento,
)
from .escena_ops import (
    CERDO_1_ST_OT_SndCapturar, CERDO_1_ST_OT_SndAplicar, CERDO_1_ST_OT_CamAplicar, CERDO_1_ST_OT_CamCapturar, CERDO_1_ST_PT_EscenaGuion,
)
from .tunel_ops import register_tunel, unregister_tunel
from .bloques_ops import register_bloques, unregister_bloques
from .reproducir_ops import (
    CERDO_1_ST_OT_GuionCargarArchivo, CERDO_1_ST_OT_GuionReproducir, CERDO_1_ST_PT_Reproducir,
)

# ── Lista de clases en orden de registro ─────────────────────
classes = (
    # PropertyGroups (deben ir primero)
    Cerdo_1EyeExpressionSettings,
    Cerdo_1OrganicFilters,
    Cerdo_1BoneOscillationItem,
    Cerdo_1BoneOscillationsSettings,
    Cerdo_1ThrowWaypoint,
    Cerdo_1ThrowItem,
    Cerdo_1ThrowsSettings,
    Cerdo_1HideMeshItem,
    Cerdo_1HideMeshSettings,
    Cerdo_1ObjectImportItem,
    Cerdo_1ObjectImportsSettings,
    Cerdo_1BlinkInterval,
    Cerdo_1LaughInterval,
    Cerdo_1UnderstandInterval,
    # Cerdo_1EyeShapeKeySetup debe registrarse ANTES que Cerdo_1EyeExprInterval
    # (Kebyn, 2026-08-18): desde que Cerdo_1EyeExprInterval tiene su propio
    # PointerProperty "own_shapekey" apuntando a Cerdo_1EyeShapeKeySetup (ver
    # properties.py, "cada expresion tenga su propia setup de shape keys de
    # ojos"), Blender exige que el tipo apuntado ya este registrado. Antes
    # este reordenamiento no hacia falta porque Cerdo_1EyeShapeKeySetup solo
    # la usaba Cerdo_1AnimSegment (mas abajo en esta lista).
    Cerdo_1EyeShapeKeySetup,
    Cerdo_1EyeExprInterval,
    Cerdo_1EyeLibEntry,
    Cerdo_1PoseSlotItem,
    Cerdo_1EyeSlotItem,
    Cerdo_1StudioSettings,
    # Operadores de setup y secuencia
    CERDO_1_ST_OT_SetArmature, CERDO_1_ST_OT_OpenCerdo_1Blend,
    CERDO_1_ST_OT_OpenPosesFolder,
    CERDO_1_ST_OT_OpenAnimFolder,
    CERDO_1_ST_OT_RefreshPoses, CERDO_1_ST_OT_ImportPose, CERDO_1_ST_OT_ApplyImportedPose,
    CERDO_1_ST_OT_ReloadHistoria,
    CERDO_1_ST_OT_ApplyKeyPointToRoot,
    CERDO_1_ST_OT_Reset,
    CERDO_1_ST_OT_AddActionPose,
    CERDO_1_ST_OT_EditActionPose,
    CERDO_1_ST_OT_RemoveActionPose,
    CERDO_1_ST_OT_MoveActionPose,
    # Operadores de secuencia de ojos
    CERDO_1_ST_OT_AddEyeSlot,
    CERDO_1_ST_OT_RemoveEyeSlot,
    CERDO_1_ST_OT_DuplicateEyeSlot,
    CERDO_1_ST_OT_MoveEyeSlot,
    CERDO_1_ST_OT_EditEyeSlot,
    CERDO_1_ST_OT_ResetEyeSequence,
    CERDO_1_ST_OT_BlinkIntervalAdd,
    CERDO_1_ST_OT_BlinkIntervalRemove,
    CERDO_1_ST_OT_BlinkIntervalDuplicate,
    CERDO_1_ST_OT_BlinkIntervalMove,
    CERDO_1_ST_OT_LaughIntervalAdd,
    CERDO_1_ST_OT_LaughIntervalRemove,
    CERDO_1_ST_OT_LaughIntervalDuplicate,
    CERDO_1_ST_OT_LaughIntervalMove,
    CERDO_1_ST_OT_UnderstandIntervalAdd,
    CERDO_1_ST_OT_UnderstandIntervalRemove,
    CERDO_1_ST_OT_UnderstandIntervalDuplicate,
    CERDO_1_ST_OT_UnderstandIntervalMove,
    CERDO_1_ST_OT_ExprIntervalAdd,
    CERDO_1_ST_OT_ExprIntervalRemove,
    CERDO_1_ST_OT_ExprIntervalDuplicate,
    CERDO_1_ST_OT_ExprIntervalMove,
    CERDO_1_ST_OT_EditExprInterval,
    CERDO_1_ST_OT_ConcatenateExprIntervals,
    CERDO_1_ST_OT_ImportEyeSlotFromJson,
    CERDO_1_ST_OT_CaptureEyeToSlot,
    CERDO_1_ST_OT_PreviewEyeState,
    CERDO_1_ST_OT_Concatenate2,
    # Sistema de ojos (shape keys base)
    CERDO_1_ST_OT_BuildEyeShapeKeys,
    CERDO_1_ST_OT_ApplyEyeExpressionPreview,
    CERDO_1_ST_OT_ResetEyeExpressions,
    # Libreria de ojos
    CERDO_1_ST_OT_SaveEyeExpression,
    CERDO_1_ST_OT_RefreshEyeLibrary,
    CERDO_1_ST_OT_LoadEyeExpression,
    CERDO_1_ST_OT_ImportEyeExpression,
    CERDO_1_ST_OT_KeyframeEyeExpression,
    CERDO_1_ST_OT_OpenEyeLibFolder,
    CERDO_1_ST_OT_ResetEyeTransforms,
    CERDO_1_ST_OT_ApplyEyeTransforms,
    CERDO_1_ST_OT_ApplyEyeGeometry,
    # Animacion principal
    CERDO_1_ST_OT_Concatenate,
    CERDO_1_ST_OT_ExportAnimation,
    CERDO_1_ST_OT_ImportAnimation,
    CERDO_1_ST_OT_ExtractPose,
    # Oscilaciones de bones personalizadas
    CERDO_1_ST_OT_BoneOscAddItem,
    CERDO_1_ST_OT_BoneOscRemoveItem,
    CERDO_1_ST_OT_BoneOscMoveItem,
    CERDO_1_ST_OT_BoneOscDuplicateItem,
    CERDO_1_ST_OT_BoneOscToggleItem,
    CERDO_1_ST_OT_BoneOscPickBone,
    # Importacion de objetos (armas, escudos, props)
    CERDO_1_ST_OT_ObjImportAddItem,
    CERDO_1_ST_OT_ObjImportRemoveItem,
    CERDO_1_ST_OT_ObjImportMoveItem,
    CERDO_1_ST_OT_ObjImportDuplicateItem,
    CERDO_1_ST_OT_ObjImportToggleItem,
    CERDO_1_ST_OT_ObjImportLoadToEditor,
    CERDO_1_ST_OT_ObjImportUpdateItem,
    CERDO_1_ST_OT_ObjImportPreviewNow,
    CERDO_1_ST_OT_ObjImportBrowseBlend,
    CERDO_1_ST_OT_ObjImportDetectArmature,
    # Lanzar / Recoger
    CERDO_1_ST_OT_ThrowAddItem,
    CERDO_1_ST_OT_ThrowRemoveItem,
    CERDO_1_ST_OT_ThrowToggleItem,
    CERDO_1_ST_OT_ThrowLoadToEditor,
    CERDO_1_ST_OT_ThrowUpdateItem,
    CERDO_1_ST_OT_ThrowPickBone,
    CERDO_1_ST_OT_ThrowBrowseBlend,
    CERDO_1_ST_OT_ThrowImportObject,
    CERDO_1_ST_OT_ThrowSyncFromObject,
    CERDO_1_ST_OT_ThrowDetectArmature,
    CERDO_1_ST_OT_ThrowPickDestFromCursor,
    CERDO_1_ST_OT_ThrowAddWaypoint,
    CERDO_1_ST_OT_ThrowRemoveWaypoint,
    CERDO_1_ST_OT_ThrowWaypointFromCursor,
    CERDO_1_ST_OT_ThrowApply,
    CERDO_1_ST_OT_ThrowClearKeyframes,
    # Invisibilidad de Malla (debajo de Lanzar/Recoger/Mantener)
    CERDO_1_ST_OT_HideMeshAddItem,
    CERDO_1_ST_OT_HideMeshRemoveItem,
    CERDO_1_ST_OT_HideMeshToggleItem,
    CERDO_1_ST_OT_HideMeshLoadToEditor,
    CERDO_1_ST_OT_HideMeshUpdateItem,
    CERDO_1_ST_OT_HideMeshPickObject,
    # Configuracion de sesion
    CERDO_1_ST_OT_SaveConfig,
    CERDO_1_ST_OT_LoadConfig,
    CERDO_1_ST_OT_OpenConfigFolder,
    CERDO_1_ST_OT_SaveEyeConfig,
    CERDO_1_ST_OT_LoadEyeConfig,
    # Paso 3: Segmentos
    Cerdo_1SegmentPoseSlot,
    Cerdo_1BoneBlockInterval,
    Cerdo_1BoneBlockEntry,
    # Cerdo_1EyeShapeKeySetup ya se registro mas arriba (antes de
    # Cerdo_1EyeExprInterval) -- se deja esta referencia comentada como
    # nota, no duplicar el registro.
    Cerdo_1AnimSegment,
    Cerdo_1AnimSegmentsSettings,
    CERDO_1SEG_OT_Add,
    CERDO_1SEG_OT_AutoSplitFromConfig,
    CERDO_1SEG_OT_UpdateFromEstimacion,
    CERDO_1SEG_OT_Remove,
    CERDO_1SEG_OT_AddBoneInterval,
    CERDO_1SEG_OT_RemoveBoneInterval,
    CERDO_1SEG_OT_Move,
    CERDO_1SEG_OT_Duplicate,
    CERDO_1SEG_OT_PickPoseMid,
    CERDO_1SEG_OT_SetFrameStart,
    CERDO_1SEG_OT_SetFrameMid,
    CERDO_1SEG_OT_SetFrameEnd,
    CERDO_1SEG_OT_Apply,
    CERDO_1SEG_OT_ConcatenateAll,
    CERDO_1SEG_OT_SaveConfig,
    CERDO_1SEG_OT_LoadConfig,
    CERDO_1SEG_OT_PlaySegment,
    CERDO_1SEG_OT_PauseSegment,
    CERDO_1SEG_OT_StopSegment,
    CERDO_1SEG_OT_PlaySegmentRecorrido,
    CERDO_1SEG_OT_ToggleEnabled,
    CERDO_1SEG_OT_AddActionPoseSeg,
    CERDO_1SEG_OT_EditActionPoseSeg,
    CERDO_1SEG_OT_QuickPoseExtract,
    CERDO_1SEG_OT_QuickPoseImport,
    CERDO_1SEG_OT_RateActionPoseSeg,
    CERDO_1SEG_OT_RemoveActionPoseSeg,
    CERDO_1SEG_OT_MoveActionPoseSeg,
    CERDO_1SEG_OT_DuplicateActionPoseSeg,
    CERDO_1SEG_OT_ToggleConfig,
    CERDO_1SEG_OT_SetFrameStartEdit,
    CERDO_1SEG_OT_PreviewActionPose,
    CERDO_1SEG_OT_EnterEditPose,
    CERDO_1SEG_OT_SaveEditedPose,
    CERDO_1SEG_UL_Segments,
    # NOTA: las clases del Path Recorder (CERDO_1PathPoint, CERDO_1ParadaFrames,
    # CERDO_1PathSettings, CERDO_1PR_OT_*) NO se listan aqui: se registran
    # exclusivamente dentro de register_path_recorder() (path_recorder.py).
    # Antes estaban duplicadas en esta tupla y en pr_classes; si el segundo
    # registro fallaba, register_path_recorder() se cortaba antes de crear
    # Scene.cerdo_1_path, provocando el AttributeError.
    # UI
    CERDO_1_ST_UL_ActionPoses,
    CERDO_1_ST_UL_EyeSlots,
    CERDO_1_ST_UL_BlinkIntervals,
    CERDO_1_ST_UL_LaughIntervals,
    CERDO_1_ST_UL_UnderstandIntervals,
    CERDO_1_ST_UL_EyeExprIntervals,
    CERDO_1_ST_PT_PathRecorder,
    CERDO_1SEG_UL_SegmentsList,
    CERDO_1_ST_PT_Main,
    CERDO_1_ST_PT_OrganicFilters,
    CERDO_1_ST_PT_BoneOscillations,
    CERDO_1_ST_PT_ObjectImports,
    CERDO_1_ST_PT_EyeSequence,
    CERDO_1_ST_PT_Export,
    CERDO_1_ST_PT_ConfigSession,
    CERDO_1_ST_PT_Extract,
    CERDO_1_ST_PT_Segments,
    # Audio del guion (voces: importar, sincronizar con Voz Sync)
    CERDO_1_ST_OT_AudioImportar, CERDO_1_ST_OT_AudioSincronizar, CERDO_1_ST_OT_AudioInicio, CERDO_1_ST_OT_AudioQuitar,
    CERDO_1_ST_PT_Audio,
    # Objetos y mundo del guion (agarres, espalda, eventos de objetos)
    CERDO_1_ST_OT_ObjCapturarAgarre, CERDO_1_ST_OT_ObjCapturarEspalda, CERDO_1_ST_OT_ObjAplicar,
    CERDO_1_ST_PT_Objetos,
    # Movimiento de Cerdo_1 por tramos (motor_cerdo_1: comparar / hornear / aprobar)
    CERDO_1_ST_OT_MovComparar, CERDO_1_ST_OT_MovHornear, CERDO_1_ST_OT_MovAprobar,
    CERDO_1_ST_PT_Movimiento,
    # Sonidos y camara del guion
    CERDO_1_ST_OT_SndCapturar, CERDO_1_ST_OT_SndAplicar, CERDO_1_ST_OT_CamAplicar, CERDO_1_ST_OT_CamCapturar,
    CERDO_1_ST_PT_EscenaGuion,
    # Reproducir el guion completo (cargar .json + todos los pasos)
    CERDO_1_ST_OT_GuionCargarArchivo, CERDO_1_ST_OT_GuionReproducir,
    CERDO_1_ST_PT_Reproducir,
)

def register():
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
        bpy.utils.register_class(cls)
    bpy.types.Scene.cerdo_1_st = PointerProperty(type=Cerdo_1StudioSettings)
    bpy.types.Scene.cerdo_1_segs = PointerProperty(type=Cerdo_1AnimSegmentsSettings)
    register_path_recorder()
    register_tunel()
    register_bloques()
    print("Cerdo_1 Animation Studio v2.0 [modular]: registrado OK")

def unregister():
    unregister_bloques()
    unregister_tunel()
    unregister_path_recorder()
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
    if hasattr(bpy.types.Scene, "cerdo_1_st"):
        del bpy.types.Scene.cerdo_1_st
    if hasattr(bpy.types.Scene, "cerdo_1_segs"):
        del bpy.types.Scene.cerdo_1_segs
    print("Cerdo_1 Animation Studio: desregistrado")

if __name__ == "__main__":
    register()
