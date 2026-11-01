# -*- coding: utf-8 -*-
"""
Jerry Animation Studio v2.0
Addon de Blender — Panel N, pestaña "Jerry Studio"

Personaje: jerry  (perro cuadrupedo)
  - Empty raiz:          jerry
  - Armature principal:  Dog_001_rig
  - Ojos/pupilas: ojo_izquierdo_jerry, ojo_derecho_jerry
  - Cejas: sejas_1_jerry, sejas_2_jerry

ESTRUCTURA MODULAR v2.0:
  constants.py           — Rutas, listas de bones, tabla INTERP
  interpolation.py       — Curvas de interpolacion profesional
  properties.py          — PropertyGroups
  pose_utils.py          — Carga de JSONs de poses, interpolacion de bones
  operators_base.py      — Setup, historia, reset, slots, eye slots, jaw
  operators_anim.py      — CONCATENAR, Exportar, Importar, Extraer pose, Bone Oscillations
  operators_segments.py  — Paso 3: Segmentos de animacion
  config_ops.py          — Guardar / Cargar configuracion de sesion (.json)
  panels.py              — Todos los paneles UI
  path_recorder.py       — Pasos 1 y 2: trazado de recorrido y generacion de slots
  eye_system.py          — Shape keys de expresion + parpadeo efecto cortina
  eye_library.py         — Biblioteca de expresiones de ojos (guardar/cargar)
"""

bl_info = {
    "name":        "Jerry Animation Studio",
    "author":      "Jerry Pipeline",
    "version":     (2, 2, 0),
    "blender":     (4, 0, 0),
    "location":    "Vista 3D > Barra lateral (N) > Jerry Studio",
    "description": "Pipeline: recorrido, slots NLA y animacion para jerry. v2.2: panel Tunel (picar): Jerry recoge un pico con la boca y pica su tunel de 1x1 m",
    "category":    "Animation",
}

import bpy
from bpy.props import PointerProperty

# ── Path Recorder ─────────────────────────────────────────────────────────────
from .path_recorder import register_path_recorder, unregister_path_recorder
from .tunel_jerry_ops import register_tunel_jerry, unregister_tunel_jerry
from .voz_rapida_ops import register_voz_rapida, unregister_voz_rapida

# ── PropertyGroups ────────────────────────────────────────────────────────────
from .properties import (
    JerryEmotionItem,
    JerryEarOscItem,
    JerryJawOscItem,
    JerryOrganicFilters,
    JerryPoseSlotItem,
    JerryBoneOscillationItem,
    JerryBoneOscillationsSettings,
    JerryEyeExpressionSettings,
    JerryEyeLibEntry,
    # Importacion de objetos y Lanzar/Recoger
    JerryObjectImportItem,
    JerryObjectImportsSettings,
    JerryThrowWaypoint,
    JerryThrowItem,
    JerryThrowsSettings,
    # Principal
    JerryStudioSettings,
    JerrySegmentPoseSlot,
    JerryBlinkInterval,
    JerryBoneBlockInterval,
    JerryBoneBlockEntry,
    JerryAnimSegment,
    JerryAnimSegmentsSettings,
)

# ── Sistema de ojos ───────────────────────────────────────────────────────────
from .eye_system import (
    JRRST_OT_BuildEyeShapeKeys,
    JRRST_OT_ApplyEyeExpressionPreview,
    JRRST_OT_ResetEyeExpressions,
    JRRST_OT_ApplyPupilGaze,
    JRRST_OT_ResetPupilGaze,
)
from .eye_library import (
    JRRST_OT_SaveEyeExpression,
    JRRST_OT_RefreshEyeLibrary,
    JRRST_OT_LoadEyeExpression,
    JRRST_OT_ImportEyeExpression,
    JRRST_OT_KeyframeEyeExpression,
    JRRST_OT_OpenEyeLibFolder,
    JRRST_OT_ResetEyeTransforms,
    JRRST_OT_ApplyEyeTransforms,
    JRRST_OT_ApplyEyeGeometry,
)

# ── Operadores base ───────────────────────────────────────────────────────────
from .operators_base import (
    JRRST_OT_SetArmature,
    JRRST_OT_OpenPosesFolder,
    JRRST_OT_OpenAnimFolder,
    JRRST_OT_RefreshPoses,
    JRRST_OT_ReloadHistoria,
    JRRST_OT_ApplyKeyPointToRoot,
    JRRST_OT_Reset,
    JRRST_OT_PickPoseStart,
    JRRST_OT_PickPoseEnd,
    JRRST_OT_AddActionPose,
    JRRST_OT_EditActionPose,
    JRRST_OT_RemoveActionPose,
    JRRST_OT_MoveActionPose,
    JRRST_OT_EnterPoseEditLive,
    JRRST_OT_SavePoseChangesLive,
    JRRST_OT_JawTalkAddInterval,
    JRRST_OT_JawTalkRemoveInterval,
)

# ── Animacion principal ───────────────────────────────────────────────────────
from .operators_anim import (
    JRRST_OT_Concatenate,
    JRRST_OT_ExportAnimation,
    JRRST_OT_ExportAnimationSingleCoord,
    JRRST_OT_ImportAnimation,
    JRRST_OT_ExtractPose,
    JRRST_OT_BoneOscAddItem,
    JRRST_OT_BoneOscRemoveItem,
    JRRSTST_OT_BoneOscMoveItem,
    JRRSTST_OT_BoneOscDuplicateItem,
    JRRSTST_OT_BoneOscToggleItem,
    JRRSTST_OT_BoneOscPickBone,
    JRRSTST_OT_BoneOscLoadToEdit,
    JRRSTST_OT_BoneOscSaveEdit,
    JRRSTST_OT_BoneOscCancelEdit,
    JRRSTST_OT_EarOscAdd,
    JRRSTST_OT_EarOscRemove,
    JRRSTST_OT_EarOscToggle,
    JRRSTST_OT_EarOscLoad,
    JRRSTST_OT_EarOscSave,
    JRRSTST_OT_EarOscCancel,
    JRRSTST_OT_JawOscAdd,
    JRRSTST_OT_JawOscRemove,
    JRRSTST_OT_JawOscToggle,
    JRRSTST_OT_JawOscLoad,
    JRRSTST_OT_JawOscSave,
    JRRSTST_OT_JawOscCancel,
    JRRSTST_OT_EmotionAdd,
    JRRSTST_OT_EmotionRemove,
    JRRSTST_OT_EmotionToggle,
    JRRSTST_OT_EmotionLoad,
    JRRSTST_OT_EmotionSave,
    JRRSTST_OT_EmotionCancel,
    JRRSTST_OT_EmotionAdd,
    JRRSTST_OT_EmotionRemove,
    JRRSTST_OT_EmotionToggle,
    JRRSTST_OT_EmotionLoad,
    JRRSTST_OT_EmotionSave,
    JRRSTST_OT_EmotionCancel,
    JRRSTST_OT_PlayFullAnimation,
    # Importacion de Objetos
    JRST_OT_ObjImportAddItem,
    JRST_OT_ObjImportRemoveItem,
    JRST_OT_ObjImportMoveItem,
    JRST_OT_ObjImportDuplicateItem,
    JRST_OT_ObjImportToggleItem,
    JRST_OT_ObjImportLoadToEditor,
    JRST_OT_ObjImportUpdateItem,
    JRST_OT_ObjImportPreviewNow,
    JRST_OT_ObjImportBrowseBlend,
    JRST_OT_ObjImportDetectArmature,
    # Lanzar / Recoger
    JRST_OT_ThrowAddItem,
    JRST_OT_ThrowRemoveItem,
    JRST_OT_ThrowToggleItem,
    JRST_OT_ThrowLoadToEditor,
    JRST_OT_ThrowUpdateItem,
    JRST_OT_ThrowPickBone,
    JRST_OT_ThrowBrowseBlend,
    JRST_OT_ThrowImportObject,
    JRST_OT_ThrowDetectArmature,
    JRST_OT_ThrowPickDestFromCursor,
    JRST_OT_ThrowAddWaypoint,
    JRST_OT_ThrowRemoveWaypoint,
    JRST_OT_ThrowWaypointFromCursor,
    JRST_OT_ThrowApply,
    JRST_OT_ThrowClearKeyframes,
)

# ── Segmentos ─────────────────────────────────────────────────────────────────
from .operators_segments import (
    JRRSTSEG_OT_Add,
    JRRSTSEG_OT_Remove,
    JRRSTSEG_OT_Move,
    JRRSTSEG_OT_Duplicate,
    JRRSTSEG_OT_AutoSplitFromConfig,
    JRRSTSEG_OT_ConcatenateAll,
    JRRSTSEG_OT_PickPoseStart,
    JRRSTSEG_OT_PickPoseMid,
    JRRSTSEG_OT_PickPoseEnd,
    JRRSTSEG_OT_SetFrameStart,
    JRRSTSEG_OT_SetFrameMid,
    JRRSTSEG_OT_SetFrameEnd,
    JRRSTSEG_OT_SaveConfig,
    JRRSTSEG_OT_LoadConfig,
    JRRSTSEG_OT_PlaySegment,
    JRRSTSEG_OT_PauseSegment,
    JRRSTSEG_OT_StopSegment,
    JRRSTSEG_OT_ToggleEnabled,
    JRRSTSEG_OT_AddActionPoseSeg,
    JRRSTSEG_OT_QuickPoseExtract,
    JRRSTSEG_OT_QuickPoseImport,
    JRRSTSEG_OT_EditActionPoseSeg,
    JRRSTSEG_OT_DuplicateActionPoseSeg,
    JRRSTSEG_OT_RemoveActionPoseSeg,
    JRRSTSEG_OT_MoveActionPoseSeg,
    JRRSTSEG_OT_ToggleConfig,
    JRRSTSEG_OT_SetFrameStartEdit,
    JRRSTSEG_OT_BlinkIntervalAddSeg,
    JRRSTSEG_OT_BlinkIntervalRemoveSeg,
    JRRSTSEG_OT_AddBoneInterval,
    JRRSTSEG_OT_RemoveBoneInterval,
)

# ── Configuracion de sesion ───────────────────────────────────────────────────
from .config_ops import (
    JRRSTST_OT_SaveConfig,
    JRRSTST_OT_LoadConfig,
    JRRSTST_OT_OpenConfigFolder,
)

# ── Paneles UI ────────────────────────────────────────────────────────────────
from .panels import (
    JRRST_UL_ActionPoses,
    JRRST_PT_Main,
    JRRST_PT_PathRecorder,
    JRRST_PT_Setup,
    JRRST_PT_OrganicFilters,
    JRRST_PT_BoneOscillations,
    JRRST_PT_ConfigSession,
    JRRST_PT_Extract,
    JRRST_PT_Export,
    JRRST_PT_ObjectImports,
)

# ── Flujo del guion 2.0 (audio, objetos y mundo, sonidos, camara, reproducir) ─────────────────
from .audio_ops import (
    JRRST_OT_AudioImportar, JRRST_OT_AudioSincronizar, JRRST_OT_AudioInicio, JRRST_OT_AudioQuitar, JRRST_PT_Audio,
)
from .objetos_ops import (
    JRRST_OT_ObjCapturarAgarre, JRRST_OT_ObjCapturarEspalda, JRRST_OT_ObjAplicar, JRRST_PT_Objetos,
)
from .escena_ops import (
    JRRST_OT_SndCapturar, JRRST_OT_SndAplicar, JRRST_OT_CamAplicar, JRRST_OT_CamCapturar, JRRST_PT_EscenaGuion,
)
from .reproducir_ops import (
    JRRST_OT_GuionCargarArchivo, JRRST_OT_GuionReproducir, JRRST_PT_Reproducir,
)

# ── Registro de clases ────────────────────────────────────────────────────────
classes = (
    # PropertyGroups (orden de dependencia)
    JerryEmotionItem,
    JerryEarOscItem,
    JerryJawOscItem,
    JerryOrganicFilters,
    JerryPoseSlotItem,
    JerryBoneOscillationItem,
    JerryBoneOscillationsSettings,
    JerryEyeExpressionSettings,
    JerryEyeLibEntry,
    # Importacion de objetos y Lanzar/Recoger (antes de JerryAnimSegment)
    JerryObjectImportItem,
    JerryObjectImportsSettings,
    JerryThrowWaypoint,
    JerryThrowItem,
    JerryThrowsSettings,
    # Principal
    JerryStudioSettings,
    JerrySegmentPoseSlot,
    JerryBlinkInterval,
    JerryBoneBlockInterval,
    JerryBoneBlockEntry,
    JerryAnimSegment,
    JerryAnimSegmentsSettings,
    # Sistema de ojos
    JRRST_OT_BuildEyeShapeKeys,
    JRRST_OT_ApplyEyeExpressionPreview,
    JRRST_OT_ResetEyeExpressions,
    JRRST_OT_ApplyPupilGaze,
    JRRST_OT_ResetPupilGaze,
    JRRST_OT_SaveEyeExpression,
    JRRST_OT_RefreshEyeLibrary,
    JRRST_OT_LoadEyeExpression,
    JRRST_OT_ImportEyeExpression,
    JRRST_OT_KeyframeEyeExpression,
    JRRST_OT_OpenEyeLibFolder,
    JRRST_OT_ResetEyeTransforms,
    JRRST_OT_ApplyEyeTransforms,
    JRRST_OT_ApplyEyeGeometry,
    JRRST_OT_JawTalkAddInterval,
    JRRST_OT_JawTalkRemoveInterval,
    # Setup y secuencia de poses
    JRRST_OT_SetArmature,
    JRRST_OT_OpenPosesFolder,
    JRRST_OT_OpenAnimFolder,
    JRRST_OT_RefreshPoses,
    JRRST_OT_ReloadHistoria,
    JRRST_OT_ApplyKeyPointToRoot,
    JRRST_OT_Reset,
    JRRST_OT_PickPoseStart,
    JRRST_OT_PickPoseEnd,
    JRRST_OT_AddActionPose,
    JRRST_OT_EditActionPose,
    JRRST_OT_RemoveActionPose,
    JRRST_OT_MoveActionPose,
    JRRST_OT_EnterPoseEditLive,
    JRRST_OT_SavePoseChangesLive,
    # Animacion principal
    JRRST_OT_Concatenate,
    JRRST_OT_ExportAnimation,
    JRRST_OT_ExportAnimationSingleCoord,
    JRRST_OT_ImportAnimation,
    JRRST_OT_ExtractPose,
    JRRST_OT_BoneOscAddItem,
    JRRST_OT_BoneOscRemoveItem,
    JRRSTST_OT_BoneOscMoveItem,
    JRRSTST_OT_BoneOscDuplicateItem,
    JRRSTST_OT_BoneOscToggleItem,
    JRRSTST_OT_BoneOscPickBone,
    JRRSTST_OT_BoneOscLoadToEdit,
    JRRSTST_OT_BoneOscSaveEdit,
    JRRSTST_OT_BoneOscCancelEdit,
    JRRSTST_OT_EarOscAdd,
    JRRSTST_OT_EarOscRemove,
    JRRSTST_OT_EarOscToggle,
    JRRSTST_OT_EarOscLoad,
    JRRSTST_OT_EarOscSave,
    JRRSTST_OT_EarOscCancel,
    JRRSTST_OT_JawOscAdd,
    JRRSTST_OT_JawOscRemove,
    JRRSTST_OT_JawOscToggle,
    JRRSTST_OT_JawOscLoad,
    JRRSTST_OT_JawOscSave,
    JRRSTST_OT_JawOscCancel,
    JRRSTST_OT_EmotionAdd,
    JRRSTST_OT_EmotionRemove,
    JRRSTST_OT_EmotionToggle,
    JRRSTST_OT_EmotionLoad,
    JRRSTST_OT_EmotionSave,
    JRRSTST_OT_EmotionCancel,
    JRRSTST_OT_PlayFullAnimation,
    # Importacion de Objetos
    JRST_OT_ObjImportAddItem,
    JRST_OT_ObjImportRemoveItem,
    JRST_OT_ObjImportMoveItem,
    JRST_OT_ObjImportDuplicateItem,
    JRST_OT_ObjImportToggleItem,
    JRST_OT_ObjImportLoadToEditor,
    JRST_OT_ObjImportUpdateItem,
    JRST_OT_ObjImportPreviewNow,
    JRST_OT_ObjImportBrowseBlend,
    JRST_OT_ObjImportDetectArmature,
    # Lanzar / Recoger
    JRST_OT_ThrowAddItem,
    JRST_OT_ThrowRemoveItem,
    JRST_OT_ThrowToggleItem,
    JRST_OT_ThrowLoadToEditor,
    JRST_OT_ThrowUpdateItem,
    JRST_OT_ThrowPickBone,
    JRST_OT_ThrowBrowseBlend,
    JRST_OT_ThrowImportObject,
    JRST_OT_ThrowDetectArmature,
    JRST_OT_ThrowPickDestFromCursor,
    JRST_OT_ThrowAddWaypoint,
    JRST_OT_ThrowRemoveWaypoint,
    JRST_OT_ThrowWaypointFromCursor,
    JRST_OT_ThrowApply,
    JRST_OT_ThrowClearKeyframes,
    # Segmentos
    JRRSTSEG_OT_Add,
    JRRSTSEG_OT_Remove,
    JRRSTSEG_OT_Move,
    JRRSTSEG_OT_Duplicate,
    JRRSTSEG_OT_AutoSplitFromConfig,
    JRRSTSEG_OT_ConcatenateAll,
    JRRSTSEG_OT_PickPoseStart,
    JRRSTSEG_OT_PickPoseMid,
    JRRSTSEG_OT_PickPoseEnd,
    JRRSTSEG_OT_SetFrameStart,
    JRRSTSEG_OT_SetFrameMid,
    JRRSTSEG_OT_SetFrameEnd,
    JRRSTSEG_OT_SaveConfig,
    JRRSTSEG_OT_LoadConfig,
    JRRSTSEG_OT_PlaySegment,
    JRRSTSEG_OT_PauseSegment,
    JRRSTSEG_OT_StopSegment,
    JRRSTSEG_OT_ToggleEnabled,
    JRRSTSEG_OT_AddActionPoseSeg,
    JRRSTSEG_OT_QuickPoseExtract,
    JRRSTSEG_OT_QuickPoseImport,
    JRRSTSEG_OT_EditActionPoseSeg,
    JRRSTSEG_OT_DuplicateActionPoseSeg,
    JRRSTSEG_OT_RemoveActionPoseSeg,
    JRRSTSEG_OT_MoveActionPoseSeg,
    JRRSTSEG_OT_ToggleConfig,
    JRRSTSEG_OT_SetFrameStartEdit,
    JRRSTSEG_OT_BlinkIntervalAddSeg,
    JRRSTSEG_OT_BlinkIntervalRemoveSeg,
    JRRSTSEG_OT_AddBoneInterval,
    JRRSTSEG_OT_RemoveBoneInterval,
    # Configuracion de sesion
    JRRSTST_OT_SaveConfig,
    JRRSTST_OT_LoadConfig,
    JRRSTST_OT_OpenConfigFolder,
    # UI listas y paneles
    JRRST_UL_ActionPoses,
    JRRST_PT_Main,
    JRRST_PT_PathRecorder,
    JRRST_PT_Setup,
    JRRST_PT_OrganicFilters,
    JRRST_PT_BoneOscillations,
    JRRST_PT_ConfigSession,
    JRRST_PT_Extract,
    JRRST_PT_Export,
    JRRST_PT_ObjectImports,
    # Guion 2.0: audio (voces), objetos y mundo, sonidos y camara, reproducir el guion completo
    JRRST_OT_AudioImportar, JRRST_OT_AudioSincronizar, JRRST_OT_AudioInicio, JRRST_OT_AudioQuitar,
    JRRST_PT_Audio,
    JRRST_OT_ObjCapturarAgarre, JRRST_OT_ObjCapturarEspalda, JRRST_OT_ObjAplicar,
    JRRST_PT_Objetos,
    JRRST_OT_SndCapturar, JRRST_OT_SndAplicar, JRRST_OT_CamAplicar, JRRST_OT_CamCapturar,
    JRRST_PT_EscenaGuion,
    JRRST_OT_GuionCargarArchivo, JRRST_OT_GuionReproducir,
    JRRST_PT_Reproducir,
)


def register():
    register_path_recorder()
    for cls in classes:
        try: bpy.utils.unregister_class(cls)
        except RuntimeError: pass
        bpy.utils.register_class(cls)
    bpy.types.Scene.jerryst    = PointerProperty(type=JerryStudioSettings)
    bpy.types.Scene.jerry_segs = PointerProperty(type=JerryAnimSegmentsSettings)
    register_tunel_jerry()
    register_voz_rapida()
    print("Jerry Animation Studio v2.2: registrado OK")


def unregister():
    unregister_voz_rapida()
    unregister_tunel_jerry()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    if hasattr(bpy.types.Scene, "jerryst"):
        del bpy.types.Scene.jerryst
    if hasattr(bpy.types.Scene, "jerry_segs"):
        del bpy.types.Scene.jerry_segs
    unregister_path_recorder()
    print("Jerry Animation Studio: desregistrado")


if __name__ == "__main__":
    register()
