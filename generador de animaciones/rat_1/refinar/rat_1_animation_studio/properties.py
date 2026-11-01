# -*- coding: utf-8 -*-
"""
properties.py — Rat 1 Animation Studio

Version minima de AlfredStudioSettings: en Alfred este PropertyGroup es
enorme (ojos, filtros organicos, oscilaciones de bones, importacion de
objetos, lanzar/recoger, invisibilidad de malla, etc. -- todo eso es
Paso 3 y sistemas adicionales que rat_1 todavia no tiene). Por ahora
rat_1 solo necesita "armature_name", que path_recorder.py sincroniza al
cargar el personaje (mismo patron que Alfred, para que un futuro Paso 3
pueda detectar el armature sin tener que volver a buscarlo).
"""

import bpy
from bpy.props import (
    StringProperty, IntProperty, FloatProperty, BoolProperty,
    EnumProperty, CollectionProperty, PointerProperty,
)
from bpy.types import PropertyGroup

from .constants import INTERP_TYPE_ITEMS, BONE_FILTER_MAP, BONE_FILTER_DEFAULT_TRUE


class Rat1StudioSettings(PropertyGroup):
    armature_name: StringProperty(
        name="Armature",
        description="Nombre del objeto Armature del personaje rat_1 en la escena",
        default="",
    )


# =============================================================================
# PASO 3 -- SEGMENTOS / POSES (port reducido desde AlfredSegmentPoseSlot /
# AlfredAnimSegment / AlfredAnimSegmentsSettings). Sin ojos, sin objetos,
# sin invisibilidad de malla, sin filtros organicos.
# =============================================================================

def _on_pose_slot_duration_update(self, context):
    """Cuando cambia la duracion de una pose ya agregada, resincroniza el
    intervalo del segmento (mismo patron que Alfred)."""
    segs = getattr(context.scene, "rat1_segs", None)
    if segs is None:
        return
    for seg in segs.segments:
        for slot in seg.action_poses:
            if slot.as_pointer() == self.as_pointer():
                from .operators_segments import _sync_seg_interval
                _sync_seg_interval(seg, segs.segments)
                return


class Rat1SegmentPoseSlot(PropertyGroup):
    """Un slot de pose (keyframes) dentro de un Rat1AnimSegment."""
    json_file:   StringProperty(default="", description="Archivo .json de la pose")
    pose_index:  IntProperty(default=0, description="Indice del registro dentro del .json")
    pose_label:  StringProperty(default="")
    pose_name:   StringProperty(default="", description="Nombre descriptivo de la pose")
    duration:    IntProperty(name="Frames", default=24, min=1, max=9999,
                              update=_on_pose_slot_duration_update)
    entry_ratio: FloatProperty(name="Entrada %", default=0.3, min=0.0, max=1.0, precision=2)
    exit_ratio:  FloatProperty(name="Salida %",  default=0.3, min=0.0, max=1.0, precision=2)
    interp_type: EnumProperty(name="Interpolacion", items=INTERP_TYPE_ITEMS, default="SMOOTH")
    rot_x: FloatProperty(name="Rot X", default=0.0, precision=4)
    rot_y: FloatProperty(name="Rot Y", default=0.0, precision=4)
    rot_z: FloatProperty(name="Rot Z", default=0.0, precision=4)
    pos_x: FloatProperty(name="Pos X", default=0.0, precision=4)
    pos_y: FloatProperty(name="Pos Y", default=0.0, precision=4)
    pos_z: FloatProperty(name="Pos Z", default=0.0, precision=4)
    frame_abs_start: IntProperty(name="Frame inicio absoluto", default=0)
    manual_start: BoolProperty(
        name="Frame de inicio manual",
        default=False,
        description=(
            "Si esta activo, 'Frame inicio absoluto' se usa tal cual en vez "
            "de calcularse automaticamente tras la pose anterior."
        ),
    )


class Rat1OrganicFilters(PropertyGroup):
    """
    Filtros de movimiento organico que se aplican como post-proceso sobre los
    keyframes generados por CONCATENAR. Eliminan la rigidez robotica agregando
    micro-variaciones fisicamente plausibles sobre rotacion/posicion/escala del
    armature y bones. Port 1:1 desde AlfredOrganicFilters (alfred_animation_
    studio/properties.py), mismos nombres de campo y mismos defaults -- solo
    cambian los bones destino (ver constants.py: ORGANIC_*), adaptados al rig
    cuadrupedo de rat_1.

    AISLAMIENTO POR SEGMENTO (mismo criterio que Alfred): esta instancia vive
    en Rat1AnimSegment.organic, NO en Rat1AnimSegmentsSettings/Scene -- cada
    segmento tiene su PROPIA copia, completamente independiente de los demas.
    """

    # ── Habilitador general ──
    enabled: BoolProperty(
        name="Activar filtros organicos",
        description="Aplica todos los filtros habilitados de este segmento al CONCATENAR",
        default=False,
    )

    # ── FILTRO 1: Respiracion ──
    breathing_enabled: BoolProperty(name="Respiracion", default=True,
        description="Agrega un ciclo suave de respiracion al torso (body2_1)")
    breathing_amplitude: FloatProperty(name="Amplitud", default=0.012, min=0.001, max=0.15, precision=3,
        description="Magnitud maxima del movimiento de respiracion en radianes")
    breathing_speed: FloatProperty(name="Velocidad", default=0.08, min=0.01, max=1.0, precision=3,
        description="Ciclos de respiracion por frame (0.08 = ~18 resp/min a 24fps)")
    breathing_phase: FloatProperty(name="Fase", default=0.0, min=0.0, max=6.28, precision=2,
        description="Offset de fase inicial del ciclo de respiracion (radianes)")

    # ── FILTRO 2: Micro-movimiento de cabeza (head sway) ──
    head_sway_enabled: BoolProperty(name="Micro-movimiento cabeza", default=True,
        description="Agrega oscilaciones organicas sutiles al cuello y cabeza (neck_1/head_1)")
    head_sway_amplitude: FloatProperty(name="Amplitud", default=0.008, min=0.001, max=0.10, precision=3,
        description="Magnitud maxima del micro-movimiento de cabeza en radianes")
    head_sway_speed: FloatProperty(name="Velocidad", default=0.05, min=0.005, max=0.5, precision=3,
        description="Velocidad de oscilacion de la cabeza por frame")
    head_sway_seed: IntProperty(name="Semilla", default=42, min=0, max=9999,
        description="Semilla aleatoria para variacion del patron de cabeza")

    # ── FILTRO 3: Weight shift (desplazamiento del peso) ──
    weight_shift_enabled: BoolProperty(name="Desplazamiento de peso", default=False,
        description="Simula el desplazamiento del centro de masa de lado a lado (body1_1)")
    weight_shift_amplitude: FloatProperty(name="Amplitud", default=0.005, min=0.001, max=0.05, precision=3,
        description="Magnitud del desplazamiento lateral en unidades Blender")
    weight_shift_speed: FloatProperty(name="Velocidad", default=0.04, min=0.005, max=0.3, precision=3,
        description="Velocidad del ciclo de desplazamiento de peso")

    # ── FILTRO 4: Noise en la posicion del ROOT ──
    root_noise_enabled: BoolProperty(name="Noise en ROOT", default=False,
        description="Agrega ruido procesal sobre la posicion del root (Empty 'rat_1')")
    root_noise_strength: FloatProperty(name="Intensidad", default=0.003, min=0.0001, max=0.05, precision=4,
        description="Intensidad maxima del ruido de posicion del root")
    root_noise_frequency: FloatProperty(name="Frecuencia", default=0.15, min=0.01, max=2.0, precision=3,
        description="Frecuencia del ruido (mayor = movimiento mas rapido)")
    root_noise_seed: IntProperty(name="Semilla", default=7, min=0, max=9999,
        description="Semilla para el ruido del root")

    # ── FILTRO 5: Secondary motion (manos, equiv. codos de Alfred) ──
    secondary_motion_enabled: BoolProperty(name="Secondary motion manos", default=False,
        description="Agrega retardo y oscilacion a las manos (follow-through); rat_1 no "
                     "tiene bone de codo, se aplica al extremo equivalente (leftHand_1/rightHand_1)")
    secondary_motion_lag: FloatProperty(name="Retardo (frames)", default=3.0, min=0.5, max=15.0, precision=1,
        description="Frames de retardo que el extremo sigue al movimiento principal")
    secondary_motion_damping: FloatProperty(name="Amortiguacion", default=0.7, min=0.1, max=0.99, precision=2,
        description="Factor de amortiguacion del movimiento secundario (0=sin amortiguar, 1=rigido)")

    # ── FILTRO 6: Suavizado de fcurves ──
    smooth_curves_enabled: BoolProperty(name="Suavizar fcurves", default=True,
        description="Aplica suavizado gaussiano a todas las fcurves del armature post-generacion")
    smooth_passes: IntProperty(name="Pasadas de suavizado", default=2, min=1, max=10,
        description="Numero de pasadas del suavizado gaussiano (mas = mas suave, mas fluido)")
    smooth_factor: FloatProperty(name="Factor suavizado", default=0.5, min=0.1, max=0.9, precision=2,
        description="Fuerza del suavizado en cada pasada (0.1=leve, 0.9=muy suave)")

    # ── FILTRO 7: Micro-escala (squash and stretch organico) ──
    micro_scale_enabled: BoolProperty(name="Micro-escala organica", default=False,
        description="Agrega variacion minima de escala en el eje Z de body2_1 para simular presion/expansion")
    micro_scale_amplitude: FloatProperty(name="Amplitud", default=0.005, min=0.001, max=0.03, precision=3,
        description="Variacion maxima de escala organica")

    # ── FILTRO 8: Noise rotacional en hombros ──
    shoulder_noise_enabled: BoolProperty(name="Noise hombros", default=False,
        description="Agrega micro-rotaciones procesuales a los brazos delanteros para mayor naturalidad")
    shoulder_noise_amplitude: FloatProperty(name="Amplitud", default=0.006, min=0.001, max=0.08, precision=3,
        description="Magnitud del noise de hombros en radianes")
    shoulder_noise_speed: FloatProperty(name="Velocidad", default=0.07, min=0.01, max=0.5, precision=3,
        description="Velocidad del noise de hombros")
    shoulder_noise_seed: IntProperty(name="Semilla", default=123, min=0, max=9999,
        description="Semilla aleatoria para noise de hombros")


class Rat1BoneBlockInterval(PropertyGroup):
    """Intervalo de frames durante el cual un bone especifico queda
    excluido de las poses del segmento (Bloqueador de bones)."""
    frame_start: IntProperty(name="Inicio", default=1, min=0)
    frame_end:   IntProperty(name="Fin", default=10, min=0)
    enabled:     BoolProperty(name="Activo", default=True)


class Rat1BoneBlockEntry(PropertyGroup):
    """Contenedor de intervalos de bloqueo para UN bone dentro de un
    segmento. 'bone_key' es el nombre del atributo filter_* del bone."""
    bone_key:      StringProperty(name="Bone", default="")
    intervals:     CollectionProperty(type=Rat1BoneBlockInterval)
    intervals_idx: IntProperty(default=0)


class Rat1AnimSegment(PropertyGroup):
    """Un segmento dentro de la animacion generada por Pasos 1+2, con su
    propia configuracion de poses (Paso 3)."""
    label: StringProperty(name="Etiqueta", default="Segmento")

    frame_start: IntProperty(name="Frame inicio", default=1, min=1, soft_max=99999)
    frame_end:   IntProperty(name="Frame fin",    default=48, min=2, soft_max=99999)

    # "Foto" del frame_start/frame_end tal como los dejo el Paso 2 (ver
    # AlfredAnimSegment.frame_start_planned en alfred_animation_studio para
    # la explicacion completa del aislamiento Paso2/Paso3).
    frame_start_planned: IntProperty(name="Frame inicio (Paso 2, fijo)", default=0, min=0, soft_max=99999)
    frame_end_planned:   IntProperty(name="Frame fin (Paso 2, fijo)",    default=0, min=0, soft_max=99999)

    action_poses:     CollectionProperty(type=Rat1SegmentPoseSlot)
    action_poses_idx: IntProperty(default=0)

    fps:         IntProperty(name="FPS", default=24, min=1, max=120)

    seg_action_name: StringProperty(name="Action del segmento", default="")

    frame_mid:      IntProperty(name="Frame intermedio", default=0, min=0, soft_max=99999)
    pose_mid_file:  StringProperty(name="Pose intermedia", default="")
    pose_mid_label: StringProperty(default="")
    interp_type:        EnumProperty(name="Interpolacion", items=INTERP_TYPE_ITEMS, default="SMOOTH")
    interp_mid_to_end:  EnumProperty(name="Interp. mid->fin", items=INTERP_TYPE_ITEMS, default="SMOOTH")

    blend_in_frames:  IntProperty(name="Blend entrada (frames)", default=8, min=0, max=120)
    blend_out_frames: IntProperty(name="Blend salida (frames)",  default=8, min=0, max=120)
    blend_strength:   FloatProperty(name="Fuerza de mezcla", default=1.0, min=0.0, max=1.0, precision=2)

    # ── Bloqueador de bones (Paso 3) ──────────────────────────
    # Los bones marcados NO reciben keyframes de pose en CONCATENAR/APLICAR.
    # Por defecto las patas traseras estan bloqueadas (el recorrido base
    # -- caminar/saltar -- las controla), mismo criterio que Alfred.
    filter_body1:       BoolProperty(name="body1_1 (raiz)", default=False)
    filter_body2:       BoolProperty(name="body2_1",        default=False)
    filter_neck:        BoolProperty(name="neck_1",         default=False)
    filter_head:        BoolProperty(name="head_1",         default=False)
    filter_left_arm:    BoolProperty(name="leftArm_1",      default=False)
    filter_left_hand:   BoolProperty(name="leftHand_1",     default=False)
    filter_right_arm:   BoolProperty(name="rightArm_1",     default=False)
    filter_right_hand:  BoolProperty(name="rightHand_1",    default=False)
    filter_left_thigh:  BoolProperty(name="leftThigh_1",    default=True)
    filter_left_foot:   BoolProperty(name="leftFoot_1",     default=True)
    filter_right_thigh: BoolProperty(name="rightThigh_1",   default=True)
    filter_right_foot:  BoolProperty(name="rightFoot_1",    default=True)
    filter_tail1:       BoolProperty(name="tail1_1",        default=False)
    filter_tail2:       BoolProperty(name="tail2_1",        default=False)

    # Intervalos de bloqueo por bone (bloqueo parcial, solo dentro de
    # ciertos frames). Un mismo bone puede tener N intervalos.
    bone_blocks: CollectionProperty(type=Rat1BoneBlockEntry)

    # ── Filtros organicos (post-proceso sobre los keyframes de ESTE
    # segmento). AISLAMIENTO POR SEGMENTO: cada Rat1AnimSegment tiene su
    # PROPIA instancia -- editar uno no afecta a los demas, y CONCATENAR
    # usa exclusivamente los valores del segmento que procesa en cada
    # paso del loop (mismo patron que AlfredAnimSegment.organic).
    organic: PointerProperty(type=Rat1OrganicFilters)

    enabled:            BoolProperty(name="Activo", default=True)
    show_config:        BoolProperty(name="Mostrar configuracion", default=True)
    single_coord_mode:  BoolProperty(name="Modo 1 coordenada", default=False)
    frame_end_auto:     IntProperty(name="Frame fin (calculado)", default=0, min=0, soft_max=99999)


class Rat1AnimSegmentsSettings(PropertyGroup):
    """Coleccion de Rat1AnimSegment y estado global del Paso 3.
    Se almacena en bpy.types.Scene.rat1_segs."""
    segments:      CollectionProperty(type=Rat1AnimSegment)
    active_index:  IntProperty(default=0)
    armature_name: StringProperty(name="Armature", default="body1_1")
    segs_applied:  BoolProperty(name="Segmentos aplicados", default=False)
    status_msg:    StringProperty(name="Estado", default="")
    poses_dir:     StringProperty(
        name="Carpeta de poses",
        default=r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\rat_1\refinar\poses",
        subtype="DIR_PATH",
    )
    config_dir: StringProperty(
        name="Carpeta de configuraciones",
        default=r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\rat_1\refinar\configuraciones",
        subtype="DIR_PATH",
        description="Carpeta donde se guardan/importan los .json de configuracion del Paso 3",
    )
    config_name: StringProperty(
        name="Nombre del archivo",
        default="mi_configuracion",
        description="Nombre del archivo de configuracion a guardar (sin extension .json)",
    )

    # ── Formulario "Crear segmento" ───────────────────────────
    edit_label: StringProperty(name="Nombre del segmento", default="Segmento")
    edit_frame_start: IntProperty(name="Frame inicio", default=1, min=1, soft_max=99999)
    edit_frame_end:   IntProperty(name="Frame fin",    default=48, min=2, soft_max=99999)

    edit_use_mid: BoolProperty(name="Usar pose intermedia", default=False)
    edit_frame_mid: IntProperty(name="Frame intermedio", default=0, min=0, soft_max=99999)
    edit_pose_mid_file:  StringProperty(name="Archivo pose intermedia", default="")
    edit_pose_mid_label: StringProperty(name="Etiqueta pose intermedia", default="")
    edit_interp:     EnumProperty(name="Interpolacion inicio->fin", items=INTERP_TYPE_ITEMS, default="SMOOTH")
    edit_interp_mid: EnumProperty(name="Interpolacion mid->fin",    items=INTERP_TYPE_ITEMS, default="SMOOTH")
    edit_start_frames: IntProperty(name="Blend entrada (frames)", default=8, min=0, max=120)
    edit_end_frames:   IntProperty(name="Blend salida (frames)",  default=8, min=0, max=120)
