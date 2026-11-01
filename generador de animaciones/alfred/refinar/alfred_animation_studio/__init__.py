# -*- coding: utf-8 -*-
"""
Alfred Animation Studio v1.9
Addon de Blender — Panel N, pestana "Alfred Studio"

ESTRUCTURA MODULAR:
  constants.py       — Rutas, listas de bones, presets de expresion, tabla INTERP
  interpolation.py   — 40+ curvas de interpolacion profesional
  properties.py      — PropertyGroups: AlfredEyeExpressionSettings, AlfredOrganicFilters,
                        AlfredBoneOscillationItem, AlfredBoneOscillationsSettings,
                        AlfredPoseSlotItem, AlfredStudioSettings
  pose_utils.py      — Carga de JSONs de poses, interpolacion de bones, open_folder
  operators_base.py  — Operadores de setup, historia, reset, pick/add/edit/move slots
  eye_system.py      — Shape keys de expresion + parpadeo efecto cortina
  operators_anim.py  — Filtros organicos, CONCATENAR, Exportar, Importar, Extraer,
                        Oscilaciones de bones (BoneOsc*)
  config_ops.py      — Guardar / Cargar configuracion de sesion (.json)
  panels.py          — Todos los paneles UI y UIList
"""

bl_info = {
    "name":        "Alfred Animation Studio",
    "author":      "Alfred Pipeline",
    "version":     (2, 3, 0),
    "blender":     (4, 0, 0),
    "location":    "Vista 3D > Barra lateral (N) > Alfred Studio",
    "description": "Combina poses, genera animaciones y exporta al flujo alfred_*.py (slot_NNN_tipo.py). v2.2: guion 2.0 (audio, objetos, movimiento, sonidos, camara). v2.3: panel 10 Tunel (cavar): dadas la coordenada de inicio y la final, Alfred cava / pica el tunel solo",
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
    from . import motor_alfred, movimiento_ops
    importlib.reload(motor_alfred)
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
        motor_alfred,
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

from .properties      import AlfredEyeExpressionSettings, AlfredOrganicFilters, \
                             AlfredEyeLibEntry, AlfredPoseSlotItem, \
                             AlfredEyeSlotItem, AlfredStudioSettings, \
                             AlfredBoneOscillationItem, AlfredBoneOscillationsSettings, \
                             AlfredBlinkInterval, AlfredLaughInterval, AlfredUnderstandInterval, \
                             AlfredEyeExprInterval, \
                             AlfredEyeShapeKeySetup, \
                             AlfredObjectImportItem, AlfredObjectImportsSettings, \
                             AlfredThrowWaypoint, AlfredThrowItem, AlfredThrowsSettings, \
                             AlfredHideMeshItem, AlfredHideMeshSettings, \
                             AlfredBoneBlockInterval, AlfredBoneBlockEntry, \
                             AlfredSegmentPoseSlot, AlfredAnimSegment, AlfredAnimSegmentsSettings
from .operators_base  import (
    ALFST_OT_SetArmature, ALFST_OT_OpenAlfredBlend, ALFST_OT_OpenPosesFolder, ALFST_OT_OpenAnimFolder,
    ALFST_OT_RefreshPoses, ALFST_OT_ImportPose, ALFST_OT_ApplyImportedPose, ALFST_OT_ReloadHistoria, ALFST_OT_ApplyKeyPointToRoot,
    ALFST_OT_Reset,
    ALFST_OT_AddActionPose, ALFST_OT_EditActionPose,
    ALFST_OT_RemoveActionPose, ALFST_OT_MoveActionPose,
    ALFST_OT_AddEyeSlot, ALFST_OT_RemoveEyeSlot, ALFST_OT_DuplicateEyeSlot,
    ALFST_OT_MoveEyeSlot, ALFST_OT_EditEyeSlot,
    ALFST_OT_ResetEyeSequence,
    ALFST_OT_BlinkIntervalAdd, ALFST_OT_BlinkIntervalRemove,
    ALFST_OT_BlinkIntervalDuplicate, ALFST_OT_BlinkIntervalMove,
    ALFST_OT_LaughIntervalAdd, ALFST_OT_LaughIntervalRemove,
    ALFST_OT_LaughIntervalDuplicate, ALFST_OT_LaughIntervalMove,
    ALFST_OT_UnderstandIntervalAdd, ALFST_OT_UnderstandIntervalRemove,
    ALFST_OT_UnderstandIntervalDuplicate, ALFST_OT_UnderstandIntervalMove,
    ALFST_OT_ExprIntervalAdd, ALFST_OT_ExprIntervalRemove,
    ALFST_OT_ExprIntervalDuplicate, ALFST_OT_ExprIntervalMove,
    ALFST_OT_EditExprInterval,
    ALFST_OT_ConcatenateExprIntervals,
    ALFST_OT_ImportEyeSlotFromJson,
    ALFST_OT_CaptureEyeToSlot,
    ALFST_OT_PreviewEyeState,
    ALFST_OT_Concatenate2,
)
from .eye_system      import (
    ALFST_OT_BuildEyeShapeKeys,
    ALFST_OT_ApplyEyeExpressionPreview,
    ALFST_OT_ResetEyeExpressions,
)
from .eye_library     import (
    ALFST_OT_SaveEyeExpression,
    ALFST_OT_RefreshEyeLibrary,
    ALFST_OT_LoadEyeExpression,
    ALFST_OT_ImportEyeExpression,
    ALFST_OT_KeyframeEyeExpression,
    ALFST_OT_OpenEyeLibFolder,
    ALFST_OT_ResetEyeTransforms,
    ALFST_OT_ApplyEyeTransforms,
    ALFST_OT_ApplyEyeGeometry,
)
from .operators_anim  import (
    ALFST_OT_Concatenate,
    ALFST_OT_ExportAnimation, ALFST_OT_ImportAnimation,
    ALFST_OT_ExtractPose,
    ALFST_OT_BoneOscAddItem,
    ALFST_OT_BoneOscRemoveItem,
    ALFST_OT_BoneOscMoveItem,
    ALFST_OT_BoneOscDuplicateItem,
    ALFST_OT_BoneOscToggleItem,
    ALFST_OT_BoneOscPickBone,
    ALFST_OT_ObjImportAddItem,
    ALFST_OT_ObjImportRemoveItem,
    ALFST_OT_ObjImportMoveItem,
    ALFST_OT_ObjImportDuplicateItem,
    ALFST_OT_ObjImportToggleItem,
    ALFST_OT_ObjImportLoadToEditor,
    ALFST_OT_ObjImportUpdateItem,
    ALFST_OT_ObjImportPreviewNow,
    # Lanzar / Recoger
    ALFST_OT_ThrowAddItem,
    ALFST_OT_ThrowRemoveItem,
    ALFST_OT_ThrowToggleItem,
    ALFST_OT_ThrowLoadToEditor,
    ALFST_OT_ThrowUpdateItem,
    ALFST_OT_ThrowPickBone,
    ALFST_OT_ThrowBrowseBlend,
    ALFST_OT_ThrowImportObject,
    ALFST_OT_ThrowSyncFromObject,
    ALFST_OT_ThrowDetectArmature,
    ALFST_OT_ThrowPickDestFromCursor,
    ALFST_OT_ThrowAddWaypoint,
    ALFST_OT_ThrowRemoveWaypoint,
    ALFST_OT_ThrowWaypointFromCursor,
    ALFST_OT_ThrowApply,
    ALFST_OT_ThrowClearKeyframes,
    ALFST_OT_ObjImportBrowseBlend,
    ALFST_OT_ObjImportDetectArmature,
    # Invisibilidad de Malla
    ALFST_OT_HideMeshAddItem,
    ALFST_OT_HideMeshRemoveItem,
    ALFST_OT_HideMeshToggleItem,
    ALFST_OT_HideMeshLoadToEditor,
    ALFST_OT_HideMeshUpdateItem,
    ALFST_OT_HideMeshPickObject,
)
from .operators_segments import (
    ALFREDSEG_OT_Add,
    ALFREDSEG_OT_AutoSplitFromConfig,
    ALFREDSEG_OT_UpdateFromEstimacion,
    ALFREDSEG_OT_Remove,
    ALFREDSEG_OT_AddBoneInterval,
    ALFREDSEG_OT_RemoveBoneInterval,
    ALFREDSEG_OT_Move,
    ALFREDSEG_OT_Duplicate,
    ALFREDSEG_OT_PickPoseMid,
    ALFREDSEG_OT_SetFrameStart,
    ALFREDSEG_OT_SetFrameMid,
    ALFREDSEG_OT_SetFrameEnd,
    ALFREDSEG_OT_Apply,
    ALFREDSEG_OT_ConcatenateAll,
    ALFREDSEG_OT_SaveConfig,
    ALFREDSEG_OT_LoadConfig,
    ALFREDSEG_OT_PlaySegment,
    ALFREDSEG_OT_PauseSegment,
    ALFREDSEG_OT_StopSegment,
    ALFREDSEG_OT_PlaySegmentRecorrido,
    ALFREDSEG_OT_ToggleEnabled,
    ALFREDSEG_OT_AddActionPoseSeg,
    ALFREDSEG_OT_EditActionPoseSeg,
    ALFREDSEG_OT_QuickPoseExtract,
    ALFREDSEG_OT_QuickPoseImport,
    ALFREDSEG_OT_RateActionPoseSeg,
    ALFREDSEG_OT_RemoveActionPoseSeg,
    ALFREDSEG_OT_MoveActionPoseSeg,
    ALFREDSEG_OT_DuplicateActionPoseSeg,
    ALFREDSEG_OT_ToggleConfig,
    ALFREDSEG_OT_SetFrameStartEdit,
    ALFREDSEG_OT_PreviewActionPose,
    ALFREDSEG_OT_EnterEditPose,
    ALFREDSEG_OT_SaveEditedPose,
    ALFREDSEG_UL_Segments,
)
from .path_recorder import (
    ALFREDPathPoint,
    ALFREDParadaFrames,
    ALFREDWalkStyleEntry,
    ALFREDPathSettings,
    ALFREDPR_OT_ToggleRecording,
    ALFREDPR_OT_RemoveLast,
    ALFREDPR_OT_RemovePoint,
    ALFREDPR_OT_ClearPath,
    ALFREDPR_OT_SyncParadasFrames,
    ALFREDPR_OT_GenerateSlots,
    ALFREDPR_OT_OpenBlendFile,
    ALFREDPR_OT_PreviewPath,
    ALFREDPR_OT_ResetPreview,
    ALFREDPR_OT_SetAnimRange,
    ALFREDPR_OT_ExportSlots,
    register_path_recorder,
    unregister_path_recorder,
)
from .config_ops      import (
    ALFST_OT_SaveConfig, ALFST_OT_LoadConfig, ALFST_OT_OpenConfigFolder,
    ALFST_OT_SaveEyeConfig, ALFST_OT_LoadEyeConfig,
)
from .panels          import (
    ALFST_UL_ActionPoses,
    ALFST_UL_EyeSlots,
    ALFST_UL_BlinkIntervals,
    ALFST_UL_LaughIntervals,
    ALFST_UL_UnderstandIntervals,
    ALFST_UL_EyeExprIntervals,
    ALFST_PT_Main,
    ALFST_PT_OrganicFilters,
    ALFST_PT_BoneOscillations,
    ALFST_PT_ObjectImports,
    ALFST_PT_EyeSequence,
    ALFST_PT_Export, ALFST_PT_ConfigSession, ALFST_PT_Extract,
    ALFST_PT_PathRecorder,
    ALFREDSEG_UL_SegmentsList,
    ALFST_PT_Segments,
)
from .audio_ops import (
    ALFST_OT_AudioImportar, ALFST_OT_AudioSincronizar, ALFST_OT_AudioInicio, ALFST_OT_AudioQuitar, ALFST_PT_Audio,
)
from .objetos_ops import (
    ALFST_OT_ObjCapturarAgarre, ALFST_OT_ObjCapturarEspalda, ALFST_OT_ObjAplicar, ALFST_PT_Objetos,
)
from .movimiento_ops import (
    ALFST_OT_MovComparar, ALFST_OT_MovHornear, ALFST_OT_MovAprobar, ALFST_PT_Movimiento,
)
from .escena_ops import (
    ALFST_OT_SndCapturar, ALFST_OT_SndAplicar, ALFST_OT_CamAplicar, ALFST_OT_CamCapturar, ALFST_PT_EscenaGuion,
)
from .tunel_ops import register_tunel, unregister_tunel
from .bloques_ops import register_bloques, unregister_bloques
from .reproducir_ops import (
    ALFST_OT_GuionCargarArchivo, ALFST_OT_GuionReproducir, ALFST_PT_Reproducir,
)

# ── Lista de clases en orden de registro ─────────────────────
classes = (
    # PropertyGroups (deben ir primero)
    AlfredEyeExpressionSettings,
    AlfredOrganicFilters,
    AlfredBoneOscillationItem,
    AlfredBoneOscillationsSettings,
    AlfredThrowWaypoint,
    AlfredThrowItem,
    AlfredThrowsSettings,
    AlfredHideMeshItem,
    AlfredHideMeshSettings,
    AlfredObjectImportItem,
    AlfredObjectImportsSettings,
    AlfredBlinkInterval,
    AlfredLaughInterval,
    AlfredUnderstandInterval,
    # AlfredEyeShapeKeySetup debe registrarse ANTES que AlfredEyeExprInterval
    # (Kebyn, 2026-08-18): desde que AlfredEyeExprInterval tiene su propio
    # PointerProperty "own_shapekey" apuntando a AlfredEyeShapeKeySetup (ver
    # properties.py, "cada expresion tenga su propia setup de shape keys de
    # ojos"), Blender exige que el tipo apuntado ya este registrado. Antes
    # este reordenamiento no hacia falta porque AlfredEyeShapeKeySetup solo
    # la usaba AlfredAnimSegment (mas abajo en esta lista).
    AlfredEyeShapeKeySetup,
    AlfredEyeExprInterval,
    AlfredEyeLibEntry,
    AlfredPoseSlotItem,
    AlfredEyeSlotItem,
    AlfredStudioSettings,
    # Operadores de setup y secuencia
    ALFST_OT_SetArmature, ALFST_OT_OpenAlfredBlend,
    ALFST_OT_OpenPosesFolder,
    ALFST_OT_OpenAnimFolder,
    ALFST_OT_RefreshPoses, ALFST_OT_ImportPose, ALFST_OT_ApplyImportedPose,
    ALFST_OT_ReloadHistoria,
    ALFST_OT_ApplyKeyPointToRoot,
    ALFST_OT_Reset,
    ALFST_OT_AddActionPose,
    ALFST_OT_EditActionPose,
    ALFST_OT_RemoveActionPose,
    ALFST_OT_MoveActionPose,
    # Operadores de secuencia de ojos
    ALFST_OT_AddEyeSlot,
    ALFST_OT_RemoveEyeSlot,
    ALFST_OT_DuplicateEyeSlot,
    ALFST_OT_MoveEyeSlot,
    ALFST_OT_EditEyeSlot,
    ALFST_OT_ResetEyeSequence,
    ALFST_OT_BlinkIntervalAdd,
    ALFST_OT_BlinkIntervalRemove,
    ALFST_OT_BlinkIntervalDuplicate,
    ALFST_OT_BlinkIntervalMove,
    ALFST_OT_LaughIntervalAdd,
    ALFST_OT_LaughIntervalRemove,
    ALFST_OT_LaughIntervalDuplicate,
    ALFST_OT_LaughIntervalMove,
    ALFST_OT_UnderstandIntervalAdd,
    ALFST_OT_UnderstandIntervalRemove,
    ALFST_OT_UnderstandIntervalDuplicate,
    ALFST_OT_UnderstandIntervalMove,
    ALFST_OT_ExprIntervalAdd,
    ALFST_OT_ExprIntervalRemove,
    ALFST_OT_ExprIntervalDuplicate,
    ALFST_OT_ExprIntervalMove,
    ALFST_OT_EditExprInterval,
    ALFST_OT_ConcatenateExprIntervals,
    ALFST_OT_ImportEyeSlotFromJson,
    ALFST_OT_CaptureEyeToSlot,
    ALFST_OT_PreviewEyeState,
    ALFST_OT_Concatenate2,
    # Sistema de ojos (shape keys base)
    ALFST_OT_BuildEyeShapeKeys,
    ALFST_OT_ApplyEyeExpressionPreview,
    ALFST_OT_ResetEyeExpressions,
    # Libreria de ojos
    ALFST_OT_SaveEyeExpression,
    ALFST_OT_RefreshEyeLibrary,
    ALFST_OT_LoadEyeExpression,
    ALFST_OT_ImportEyeExpression,
    ALFST_OT_KeyframeEyeExpression,
    ALFST_OT_OpenEyeLibFolder,
    ALFST_OT_ResetEyeTransforms,
    ALFST_OT_ApplyEyeTransforms,
    ALFST_OT_ApplyEyeGeometry,
    # Animacion principal
    ALFST_OT_Concatenate,
    ALFST_OT_ExportAnimation,
    ALFST_OT_ImportAnimation,
    ALFST_OT_ExtractPose,
    # Oscilaciones de bones personalizadas
    ALFST_OT_BoneOscAddItem,
    ALFST_OT_BoneOscRemoveItem,
    ALFST_OT_BoneOscMoveItem,
    ALFST_OT_BoneOscDuplicateItem,
    ALFST_OT_BoneOscToggleItem,
    ALFST_OT_BoneOscPickBone,
    # Importacion de objetos (armas, escudos, props)
    ALFST_OT_ObjImportAddItem,
    ALFST_OT_ObjImportRemoveItem,
    ALFST_OT_ObjImportMoveItem,
    ALFST_OT_ObjImportDuplicateItem,
    ALFST_OT_ObjImportToggleItem,
    ALFST_OT_ObjImportLoadToEditor,
    ALFST_OT_ObjImportUpdateItem,
    ALFST_OT_ObjImportPreviewNow,
    ALFST_OT_ObjImportBrowseBlend,
    ALFST_OT_ObjImportDetectArmature,
    # Lanzar / Recoger
    ALFST_OT_ThrowAddItem,
    ALFST_OT_ThrowRemoveItem,
    ALFST_OT_ThrowToggleItem,
    ALFST_OT_ThrowLoadToEditor,
    ALFST_OT_ThrowUpdateItem,
    ALFST_OT_ThrowPickBone,
    ALFST_OT_ThrowBrowseBlend,
    ALFST_OT_ThrowImportObject,
    ALFST_OT_ThrowSyncFromObject,
    ALFST_OT_ThrowDetectArmature,
    ALFST_OT_ThrowPickDestFromCursor,
    ALFST_OT_ThrowAddWaypoint,
    ALFST_OT_ThrowRemoveWaypoint,
    ALFST_OT_ThrowWaypointFromCursor,
    ALFST_OT_ThrowApply,
    ALFST_OT_ThrowClearKeyframes,
    # Invisibilidad de Malla (debajo de Lanzar/Recoger/Mantener)
    ALFST_OT_HideMeshAddItem,
    ALFST_OT_HideMeshRemoveItem,
    ALFST_OT_HideMeshToggleItem,
    ALFST_OT_HideMeshLoadToEditor,
    ALFST_OT_HideMeshUpdateItem,
    ALFST_OT_HideMeshPickObject,
    # Configuracion de sesion
    ALFST_OT_SaveConfig,
    ALFST_OT_LoadConfig,
    ALFST_OT_OpenConfigFolder,
    ALFST_OT_SaveEyeConfig,
    ALFST_OT_LoadEyeConfig,
    # Paso 3: Segmentos
    AlfredSegmentPoseSlot,
    AlfredBoneBlockInterval,
    AlfredBoneBlockEntry,
    # AlfredEyeShapeKeySetup ya se registro mas arriba (antes de
    # AlfredEyeExprInterval) -- se deja esta referencia comentada como
    # nota, no duplicar el registro.
    AlfredAnimSegment,
    AlfredAnimSegmentsSettings,
    ALFREDSEG_OT_Add,
    ALFREDSEG_OT_AutoSplitFromConfig,
    ALFREDSEG_OT_UpdateFromEstimacion,
    ALFREDSEG_OT_Remove,
    ALFREDSEG_OT_AddBoneInterval,
    ALFREDSEG_OT_RemoveBoneInterval,
    ALFREDSEG_OT_Move,
    ALFREDSEG_OT_Duplicate,
    ALFREDSEG_OT_PickPoseMid,
    ALFREDSEG_OT_SetFrameStart,
    ALFREDSEG_OT_SetFrameMid,
    ALFREDSEG_OT_SetFrameEnd,
    ALFREDSEG_OT_Apply,
    ALFREDSEG_OT_ConcatenateAll,
    ALFREDSEG_OT_SaveConfig,
    ALFREDSEG_OT_LoadConfig,
    ALFREDSEG_OT_PlaySegment,
    ALFREDSEG_OT_PauseSegment,
    ALFREDSEG_OT_StopSegment,
    ALFREDSEG_OT_PlaySegmentRecorrido,
    ALFREDSEG_OT_ToggleEnabled,
    ALFREDSEG_OT_AddActionPoseSeg,
    ALFREDSEG_OT_EditActionPoseSeg,
    ALFREDSEG_OT_QuickPoseExtract,
    ALFREDSEG_OT_QuickPoseImport,
    ALFREDSEG_OT_RateActionPoseSeg,
    ALFREDSEG_OT_RemoveActionPoseSeg,
    ALFREDSEG_OT_MoveActionPoseSeg,
    ALFREDSEG_OT_DuplicateActionPoseSeg,
    ALFREDSEG_OT_ToggleConfig,
    ALFREDSEG_OT_SetFrameStartEdit,
    ALFREDSEG_OT_PreviewActionPose,
    ALFREDSEG_OT_EnterEditPose,
    ALFREDSEG_OT_SaveEditedPose,
    ALFREDSEG_UL_Segments,
    # NOTA: las clases del Path Recorder (ALFREDPathPoint, ALFREDParadaFrames,
    # ALFREDPathSettings, ALFREDPR_OT_*) NO se listan aqui: se registran
    # exclusivamente dentro de register_path_recorder() (path_recorder.py).
    # Antes estaban duplicadas en esta tupla y en pr_classes; si el segundo
    # registro fallaba, register_path_recorder() se cortaba antes de crear
    # Scene.alfred_path, provocando el AttributeError.
    # UI
    ALFST_UL_ActionPoses,
    ALFST_UL_EyeSlots,
    ALFST_UL_BlinkIntervals,
    ALFST_UL_LaughIntervals,
    ALFST_UL_UnderstandIntervals,
    ALFST_UL_EyeExprIntervals,
    ALFST_PT_PathRecorder,
    ALFREDSEG_UL_SegmentsList,
    ALFST_PT_Main,
    ALFST_PT_OrganicFilters,
    ALFST_PT_BoneOscillations,
    ALFST_PT_ObjectImports,
    ALFST_PT_EyeSequence,
    ALFST_PT_Export,
    ALFST_PT_ConfigSession,
    ALFST_PT_Extract,
    ALFST_PT_Segments,
    # Audio del guion (voces: importar, sincronizar con Voz Sync)
    ALFST_OT_AudioImportar, ALFST_OT_AudioSincronizar, ALFST_OT_AudioInicio, ALFST_OT_AudioQuitar,
    ALFST_PT_Audio,
    # Objetos y mundo del guion (agarres, espalda, eventos de objetos)
    ALFST_OT_ObjCapturarAgarre, ALFST_OT_ObjCapturarEspalda, ALFST_OT_ObjAplicar,
    ALFST_PT_Objetos,
    # Movimiento de Alfred por tramos (motor_alfred: comparar / hornear / aprobar)
    ALFST_OT_MovComparar, ALFST_OT_MovHornear, ALFST_OT_MovAprobar,
    ALFST_PT_Movimiento,
    # Sonidos y camara del guion
    ALFST_OT_SndCapturar, ALFST_OT_SndAplicar, ALFST_OT_CamAplicar, ALFST_OT_CamCapturar,
    ALFST_PT_EscenaGuion,
    # Reproducir el guion completo (cargar .json + todos los pasos)
    ALFST_OT_GuionCargarArchivo, ALFST_OT_GuionReproducir,
    ALFST_PT_Reproducir,
)

def register():
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
        bpy.utils.register_class(cls)
    bpy.types.Scene.alfst = PointerProperty(type=AlfredStudioSettings)
    bpy.types.Scene.alfred_segs = PointerProperty(type=AlfredAnimSegmentsSettings)
    register_path_recorder()
    register_tunel()
    register_bloques()
    print("Alfred Animation Studio v2.0 [modular]: registrado OK")

def unregister():
    unregister_bloques()
    unregister_tunel()
    unregister_path_recorder()
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
    if hasattr(bpy.types.Scene, "alfst"):
        del bpy.types.Scene.alfst
    if hasattr(bpy.types.Scene, "alfred_segs"):
        del bpy.types.Scene.alfred_segs
    print("Alfred Animation Studio: desregistrado")

if __name__ == "__main__":
    register()
