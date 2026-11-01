# -*- coding: utf-8 -*-
"""
config_ops.py — Jerry Animation Studio
Guardar / Cargar SNAPSHOT COMPLETO de sesion en JSON.

Cubre absolutamente todos los valores del addon:
  Paso 1  : Importacion (.blend, armature, carpetas, orientacion, frame inicio)
  Paso 2  : Path recorder (coordenadas, slot inicio, FPS, rotacion root,
             frames por bloque, carpeta salida, execute_inscene)
  Paso 2b : Filtros organicos (9 filtros completos)
  Paso 2c : Oscilaciones de bones (lista completa de items)
  Paso 3  : Segmentos (lista completa: poses, action_poses, filtros de bones,
             blend, interp, frame_start/end, afectados, etc.)
  Global  : Exportacion (slot number, tipo, desc), config_name
"""
import bpy, json, os
from bpy.types import Operator
from bpy.props import StringProperty
from .pose_utils import open_folder
try:
    from . import guion_v2 as _gv2          # guion 2.0 (secciones nuevas opcionales); si falta, todo sigue como antes
except Exception:
    _gv2 = None


# =============================================================================
# COMPATIBILIDAD CON EL FORMATO "EVOLUTIVO" (jerry_config_*.json generado por
# jerry_story_generator.py / jerry_evolution_engine.py — mismo formato que usa
# Alfred: paso1_path, pose_inicio/pose_fin, eye_sequence, jerry_segs).
#
# Ese formato es distinto del snapshot nativo v2.0 de este addon (paso_1,
# paso_2_recorrido, pose_start/pose_end, eye_system, paso_3_segmentos). Las
# funciones de abajo traducen el formato evolutivo al nativo ANTES de que
# JRRSTST_OT_LoadConfig procese el resto del archivo, para que ambos formatos
# se puedan cargar con el mismo boton "Cargar configuracion".
# =============================================================================

# Mapeo de flags "affect_*" cuadrupedo (jerry_segs) -> propiedad nativa real
# de JerryAnimSegment. Los nombres de propiedad son legado de Alfred/Guard
# Ribbit (brazo/pierna/escudo/lanza) pero ya apuntan a los bones reales de
# Jerry (ver properties.py): affect_left_arm -> pata delantera izq,
# affect_shield -> base de la cola. No existe una propiedad nativa para
# "cabeza" a nivel affect_ (solo a nivel filter_), por eso no tiene mapeo.
_AFFECT_MAP_EVOLUTIVO = {
    "affect_body":            "affect_body",
    "affect_front_left_leg":  "affect_left_arm",
    "affect_front_right_leg": "affect_right_arm",
    "affect_back_left_leg":   "affect_left_leg",
    "affect_back_right_leg":  "affect_right_leg",
    "affect_tail":            "affect_shield",
    "affect_root":            "affect_root",
}

# Mapeo de flags "filter_*" cuadrupedo (jerry_segs) -> una o varias
# propiedades nativas reales (algunos flags cuadrupedos cubren varios bones
# nativos a la vez, p.ej. filter_tail -> tail_1 + tail_2 + tail_3).
_FILTER_MAP_EVOLUTIVO = {
    "filter_show":            ["filter_show"],
    "filter_main_bone":       ["filter_main_bone"],
    "filter_root":            ["filter_main_bone"],
    "filter_front_left_leg":  ["filter_left_arm"],
    "filter_front_right_leg": ["filter_right_arm"],
    "filter_back_left_leg":   ["filter_left_leg"],
    "filter_back_right_leg":  ["filter_right_leg"],
    "filter_tail":            ["filter_shield", "filter_spear", "filter_tail_3"],
    "filter_ears":            ["filter_ear_l", "filter_ear_r"],
    "filter_jaw":             ["filter_jaw_top", "filter_jaw_bot"],
    "filter_head":            ["filter_scull", "filter_scull_1"],
    "filter_spine":           ["filter_body", "filter_spine_2", "filter_spine_3",
                                "filter_spine_4", "filter_spine_5", "filter_spine_6",
                                "filter_spine_7"],
    # "cuello" no tiene bone dedicado en el rig de Jerry (spine_1/spine_2 hacen
    # de cuello) — se mapea al tramo de columna mas cercano a la cabeza.
    "filter_neck":            ["filter_spine_2"],
}


def _convertir_pose_slot_plano(d, prefix):
    """Extrae un pose_start/pose_end NIDO desde los campos PLANOS con prefijo
    (pose_start_file, pose_start_name, ...) que usa jerry_segs (formato
    evolutivo). Si no hay campos con ese prefijo, devuelve {}."""
    out = {}
    campos = ("file", "name", "idx", "index", "duration", "interp",
              "rot_x", "rot_y", "rot_z", "pos_x", "pos_y", "pos_z")
    encontrado = False
    for c in campos:
        clave = f"{prefix}_{c}"
        if clave in d:
            out[c] = d[clave]
            encontrado = True
    return out if encontrado else {}


def _convertir_jerry_seg_a_nativo(d):
    """Traduce UNA entrada de 'jerry_segs' (formato evolutivo, campos planos y
    vocabulario cuadrupedo) al formato nativo que espera _load_segment()
    (pose_start/pose_end anidados, affect_/filter_ con nombres de propiedad
    reales, throws como dict {enabled, items})."""
    nativo = dict(d)  # copia superficial; conserva label/frame_start/... que ya calzan

    # pose_start / pose_end: de campos planos a dict anidado
    ps = _convertir_pose_slot_plano(d, "pose_start")
    if ps:
        nativo["pose_start"] = ps
    pe = _convertir_pose_slot_plano(d, "pose_end")
    if pe:
        nativo["pose_end"] = pe

    # affect_*: traducir nombres cuadrupedos a propiedades reales
    for clave_evo, clave_nativa in _AFFECT_MAP_EVOLUTIVO.items():
        if clave_evo in d:
            nativo[clave_nativa] = d[clave_evo]

    # filter_*: un flag cuadrupedo puede expandirse a varias propiedades
    for clave_evo, claves_nativas in _FILTER_MAP_EVOLUTIVO.items():
        if clave_evo in d:
            for cn in claves_nativas:
                nativo[cn] = d[clave_evo]

    # throws_items (lista plana, formato evolutivo) -> throws {enabled, items}
    if "throws_items" in d:
        nativo["throws"] = {
            "enabled": d.get("throws_enabled", bool(d.get("throws_items"))),
            "items":   d.get("throws_items", []),
        }

    return nativo


# NOTA (Kebyn, 2026-08-27): _cargar_eye_slots_evolutivo eliminada junto con
# el sistema de "Secuencia de Ojos" por-segmento (st.eye_slots) -- ver nota
# equivalente mas abajo junto a _ser_eye_expr/_load_eye_expr.


# ---------------------------------------------------------------------------
# Helpers de serializacion
# ---------------------------------------------------------------------------

def _ser_organic(og):
    return {
        "enabled":                   og.enabled,
        "breathing_enabled":         og.breathing_enabled,
        "breathing_amplitude":       og.breathing_amplitude,
        "breathing_speed":           og.breathing_speed,
        "breathing_phase":           og.breathing_phase,
        "head_sway_enabled":         og.head_sway_enabled,
        "head_sway_amplitude":       og.head_sway_amplitude,
        "head_sway_speed":           og.head_sway_speed,
        "head_sway_seed":            og.head_sway_seed,
        "weight_shift_enabled":      og.weight_shift_enabled,
        "weight_shift_amplitude":    og.weight_shift_amplitude,
        "weight_shift_speed":        og.weight_shift_speed,
        "root_noise_enabled":        og.root_noise_enabled,
        "root_noise_strength":       og.root_noise_strength,
        "root_noise_frequency":      og.root_noise_frequency,
        "root_noise_seed":           og.root_noise_seed,
        "secondary_motion_enabled":  og.secondary_motion_enabled,
        "secondary_motion_lag":      og.secondary_motion_lag,
        "secondary_motion_damping":  og.secondary_motion_damping,
        "smooth_curves_enabled":     og.smooth_curves_enabled,
        "smooth_passes":             og.smooth_passes,
        "smooth_factor":             og.smooth_factor,
        "micro_scale_enabled":       og.micro_scale_enabled,
        "micro_scale_amplitude":     og.micro_scale_amplitude,
        "shoulder_noise_enabled":    og.shoulder_noise_enabled,
        "shoulder_noise_amplitude":  og.shoulder_noise_amplitude,
        "shoulder_noise_speed":      og.shoulder_noise_speed,
        "shoulder_noise_seed":       og.shoulder_noise_seed,
        "tail_wag_enabled":          og.tail_wag_enabled,
        "tail_wag_amplitude":        og.tail_wag_amplitude,
        "tail_wag_speed":            og.tail_wag_speed,
        "tail_wag_phase":            og.tail_wag_phase,
        "tail_wag_lag":              og.tail_wag_lag,
        # -- Oscilacion orejas --
        "ear_osc_enabled": og.ear_osc_enabled,
        "ear_items": [
            {
                "label":       it.label,
                "frame_start": it.frame_start,
                "frame_end":   it.frame_end,
                "amplitude":   it.amplitude,
                "speed":       it.speed,
                "phase_l":     it.phase_l,
                "phase_r":     it.phase_r,
                "axis":        it.axis,
                "enabled":     it.enabled,
            }
            for it in og.ear_items
        ],
        # -- Oscilacion mandibula --
        "jaw_osc_enabled": og.jaw_osc_enabled,
        "jaw_items": [
            {
                "label":       it.label,
                "frame_start": it.frame_start,
                "frame_end":   it.frame_end,
                "amplitude":   it.amplitude,
                "cycles":      it.cycles,
                "phase":       it.phase,
                "axis":        it.axis,
                "transition":  it.transition,
                "noise_seed":  it.noise_seed,
                "enabled":     it.enabled,
            }
            for it in og.jaw_items
        ],
        # -- Emociones cejas --
        "emotion_enabled": og.emotion_enabled,
        "emotion_items": [
            {
                "label":          it.label,
                "frame_start":    it.frame_start,
                "frame_end":      it.frame_end,
                "transition_in":  it.transition_in,
                "transition_out": it.transition_out,
                "interp_type":    it.interp_type,
                "emotion":        it.emotion,
                "enabled":        it.enabled,
            }
            for it in og.emotion_items
        ],
    }


def _load_organic(og, o):
    if not o:
        return
    og.enabled                  = o.get("enabled",                  og.enabled)
    og.breathing_enabled        = o.get("breathing_enabled",        og.breathing_enabled)
    og.breathing_amplitude      = o.get("breathing_amplitude",      og.breathing_amplitude)
    og.breathing_speed          = o.get("breathing_speed",          og.breathing_speed)
    og.breathing_phase          = o.get("breathing_phase",          og.breathing_phase)
    og.head_sway_enabled        = o.get("head_sway_enabled",        og.head_sway_enabled)
    og.head_sway_amplitude      = o.get("head_sway_amplitude",      og.head_sway_amplitude)
    og.head_sway_speed          = o.get("head_sway_speed",          og.head_sway_speed)
    og.head_sway_seed           = o.get("head_sway_seed",           og.head_sway_seed)
    og.weight_shift_enabled     = o.get("weight_shift_enabled",     og.weight_shift_enabled)
    og.weight_shift_amplitude   = o.get("weight_shift_amplitude",   og.weight_shift_amplitude)
    og.weight_shift_speed       = o.get("weight_shift_speed",       og.weight_shift_speed)
    og.root_noise_enabled       = o.get("root_noise_enabled",       og.root_noise_enabled)
    og.root_noise_strength      = o.get("root_noise_strength",      og.root_noise_strength)
    og.root_noise_frequency     = o.get("root_noise_frequency",     og.root_noise_frequency)
    og.root_noise_seed          = o.get("root_noise_seed",          og.root_noise_seed)
    og.secondary_motion_enabled = o.get("secondary_motion_enabled", og.secondary_motion_enabled)
    og.secondary_motion_lag     = o.get("secondary_motion_lag",     og.secondary_motion_lag)
    og.secondary_motion_damping = o.get("secondary_motion_damping", og.secondary_motion_damping)
    og.smooth_curves_enabled    = o.get("smooth_curves_enabled",    og.smooth_curves_enabled)
    og.smooth_passes            = o.get("smooth_passes",            og.smooth_passes)
    og.smooth_factor            = o.get("smooth_factor",            og.smooth_factor)
    og.micro_scale_enabled      = o.get("micro_scale_enabled",      og.micro_scale_enabled)
    og.micro_scale_amplitude    = o.get("micro_scale_amplitude",    og.micro_scale_amplitude)
    og.shoulder_noise_enabled   = o.get("shoulder_noise_enabled",   og.shoulder_noise_enabled)
    og.shoulder_noise_amplitude = o.get("shoulder_noise_amplitude", og.shoulder_noise_amplitude)
    og.shoulder_noise_speed     = o.get("shoulder_noise_speed",     og.shoulder_noise_speed)
    og.shoulder_noise_seed      = o.get("shoulder_noise_seed",      og.shoulder_noise_seed)
    og.tail_wag_enabled         = o.get("tail_wag_enabled",         og.tail_wag_enabled)
    og.tail_wag_amplitude       = o.get("tail_wag_amplitude",       og.tail_wag_amplitude)
    og.tail_wag_speed           = o.get("tail_wag_speed",           og.tail_wag_speed)
    og.tail_wag_phase           = o.get("tail_wag_phase",           og.tail_wag_phase)
    og.tail_wag_lag             = o.get("tail_wag_lag",             og.tail_wag_lag)

    # -- Oscilacion orejas --
    og.ear_osc_enabled = o.get("ear_osc_enabled", og.ear_osc_enabled)
    og.ear_items.clear()
    for d in o.get("ear_items", []):
        it = og.ear_items.add()
        it.label       = d.get("label",       "Orejas")
        it.frame_start = d.get("frame_start", 1)
        it.frame_end   = d.get("frame_end",   80)
        it.amplitude   = d.get("amplitude",   0.12)
        it.speed       = d.get("speed",       0.06)
        it.phase_l     = d.get("phase_l",     0.0)
        it.phase_r     = d.get("phase_r",     1.57)
        it.axis        = d.get("axis",        "Z")
        it.enabled     = d.get("enabled",     True)

    # -- Oscilacion mandibula --
    og.jaw_osc_enabled = o.get("jaw_osc_enabled", og.jaw_osc_enabled)
    og.jaw_items.clear()
    for d in o.get("jaw_items", []):
        it = og.jaw_items.add()
        it.label       = d.get("label",       "Mandibula")
        it.frame_start = d.get("frame_start", 1)
        it.frame_end   = d.get("frame_end",   60)
        it.amplitude   = d.get("amplitude",   30.0)
        it.cycles      = d.get("cycles",      4)
        it.phase       = d.get("phase",       0.0)
        it.axis        = d.get("axis",        "Z")
        it.transition  = d.get("transition",  "SINE")
        it.noise_seed  = d.get("noise_seed",  55)
        it.enabled     = d.get("enabled",     True)

    # -- Emociones cejas --
    og.emotion_enabled = o.get("emotion_enabled", og.emotion_enabled)
    og.emotion_items.clear()
    for d in o.get("emotion_items", []):
        it = og.emotion_items.add()
        it.label          = d.get("label",          "Emocion")
        it.frame_start    = d.get("frame_start",    1)
        it.frame_end      = d.get("frame_end",      60)
        it.transition_in  = d.get("transition_in",  8)
        it.transition_out = d.get("transition_out", 8)
        it.interp_type    = d.get("interp_type",    "EASE_IN_OUT_SIN")
        it.emotion        = d.get("emotion",        "enojado")
        it.enabled        = d.get("enabled",        True)


def _ser_osc_item(item):
    return {
        "label":        item.label,
        "bone_name":    item.bone_name,
        "frame_start":  item.frame_start,
        "frame_end":    item.frame_end,
        "axis_x":       item.axis_x,
        "axis_y":       item.axis_y,
        "axis_z":       item.axis_z,
        "amplitude":    item.amplitude,
        "angle_offset": item.angle_offset,
        "num_cycles":   item.num_cycles,
        "phase":        item.phase,
        "wave_type":    item.wave_type,
        "enabled":      item.enabled,
    }


def _load_osc_items(collection, data_list):
    collection.clear()
    for d in data_list:
        item = collection.add()
        item.label        = d.get("label",        "Oscilacion")
        item.bone_name    = d.get("bone_name",    "")
        item.frame_start  = d.get("frame_start",  1)
        item.frame_end    = d.get("frame_end",    60)
        item.axis_x       = d.get("axis_x",       False)
        item.axis_y       = d.get("axis_y",       False)
        item.axis_z       = d.get("axis_z",       True)
        item.amplitude    = d.get("amplitude",    30.0)
        item.angle_offset = d.get("angle_offset", 0.0)
        item.num_cycles   = d.get("num_cycles",   4)
        item.phase        = d.get("phase",        0.0)
        item.wave_type    = d.get("wave_type",    "SINE")
        item.enabled      = d.get("enabled",      True)


def _ser_action_poses(collection):
    """Serializa una CollectionProperty de JerrySegmentPoseSlot."""
    result = []
    for slot in collection:
        d = {
            "json_file":   slot.json_file,
            "pose_label":  slot.pose_label,
            "pose_name":   slot.pose_name,
            "duration":    slot.duration,
            "entry_ratio": slot.entry_ratio,
            "exit_ratio":  slot.exit_ratio,
            "interp_type": slot.interp_type,
            "rot_x": slot.rot_x, "rot_y": slot.rot_y, "rot_z": slot.rot_z,
            "pos_x": slot.pos_x, "pos_y": slot.pos_y, "pos_z": slot.pos_z,
            "manual_start":    bool(getattr(slot, "manual_start", False)),
            "frame_abs_start": int(getattr(slot, "frame_abs_start", 0)),
        }
        # Campos opcionales presentes en JerryPoseSlotItem (formato v1) pero no en
        # JerrySegmentPoseSlot — se guardan solo si existen para mantener
        # compatibilidad al cargar JSONs del formato antiguo.
        for _opt in ("pose_idx", "pose_index"):
            if hasattr(slot, _opt):
                d[_opt] = getattr(slot, _opt)
        result.append(d)
    return result


def _ser_blink_intervals(collection):
    """Serializa una CollectionProperty de JerryBlinkInterval (parpadeo por segmento)."""
    result = []
    for item in collection:
        result.append({
            "label":          item.label,
            "frame_start":    item.frame_start,
            "frame_end":      item.frame_end,
            "blink_count":    item.blink_count,
            "blink_duration": item.blink_duration,
            "enabled":        item.enabled,
        })
    return result


def _load_blink_intervals(collection, data_list):
    """Carga una lista de dicts en una CollectionProperty de JerryBlinkInterval."""
    collection.clear()
    for bd in data_list:
        item = collection.add()
        item.label          = bd.get("label", "Parpadeo")
        item.frame_start    = bd.get("frame_start", 1)
        item.frame_end      = bd.get("frame_end", 60)
        item.blink_count    = bd.get("blink_count", 1)
        item.blink_duration = bd.get("blink_duration", 9)
        item.enabled        = bd.get("enabled", True)


def _aplicar_parpadeo_default_seg(seg):
    """Deja a UN segmento con "un parpadeo por segmento" (Kebyn, 2026-08-05;
    movido a config_ops.py el 2026-08-07 para poder reutilizarlo tambien
    desde el importador de config completa / formato evolutivo mas abajo
    en este mismo archivo, sin import circular con operators_segments.py),
    agregando un unico JerryBlinkInterval que cubre todo el rango del
    segmento, SOLO si el segmento todavia no tiene ninguno (idempotente,
    no pisa parpadeos ya configurados o cargados desde un .json).

    frame_start/frame_end se recalculan dinamicamente en jerryst.concatenate
    (operators_anim.py) o en JRRSTSEG_OT_ConcatenateAll a partir del rango
    REAL del segmento en ese momento (igual que hace Alfred con
    _calc_seg_frames) -- aca solo se deja un valor inicial razonable para
    que el intervalo no aparezca vacio en el panel."""
    if len(seg.blink_intervals) > 0:
        return
    bi = seg.blink_intervals.add()
    bi.label          = "Parpadeo"
    bi.frame_start     = seg.frame_start
    bi.frame_end        = max(seg.frame_end, seg.frame_start + 9)
    bi.blink_count      = 1
    bi.blink_duration   = 9
    bi.enabled          = True
    seg.blink_interval_idx = 0


def _load_action_poses(collection, data_list):
    """Carga una lista de dicts en una CollectionProperty de JerrySegmentPoseSlot."""
    collection.clear()
    for pd in data_list:
        slot = collection.add()
        slot.json_file   = pd.get("json_file",   "")
        slot.pose_label  = pd.get("pose_label",  "")
        slot.pose_name   = pd.get("pose_name",   pd.get("pose_label", ""))
        slot.duration    = pd.get("duration",    24)
        slot.entry_ratio = pd.get("entry_ratio", 0.3)
        slot.exit_ratio  = pd.get("exit_ratio",  0.3)
        slot.interp_type = pd.get("interp_type", "SMOOTH")
        slot.rot_x = pd.get("rot_x", 0.0); slot.rot_y = pd.get("rot_y", 0.0)
        slot.rot_z = pd.get("rot_z", 0.0)
        slot.pos_x = pd.get("pos_x", 0.0); slot.pos_y = pd.get("pos_y", 0.0)
        slot.pos_z = pd.get("pos_z", 0.0)
        if hasattr(slot, "manual_start"):
            slot.manual_start = bool(pd.get("manual_start", False))
        if hasattr(slot, "frame_abs_start"):
            slot.frame_abs_start = int(pd.get("frame_abs_start", 0))


def _ser_pose_slot(prefix, st_or_seg):
    """Serializa pose_start o pose_end dado un prefijo."""
    return {
        "file":     getattr(st_or_seg, f"{prefix}_file",     ""),
        "name":     getattr(st_or_seg, f"{prefix}_name",     ""),
        "idx":      getattr(st_or_seg, f"{prefix}_idx",      0),
        "duration": getattr(st_or_seg, f"{prefix}_duration", 10),
        "interp":   getattr(st_or_seg, f"{prefix}_interp",   "SMOOTH"),
        "rot_x":    getattr(st_or_seg, f"{prefix}_rot_x",    0.0),
        "rot_y":    getattr(st_or_seg, f"{prefix}_rot_y",    0.0),
        "rot_z":    getattr(st_or_seg, f"{prefix}_rot_z",    0.0),
        "pos_x":    getattr(st_or_seg, f"{prefix}_pos_x",    0.0),
        "pos_y":    getattr(st_or_seg, f"{prefix}_pos_y",    0.0),
        "pos_z":    getattr(st_or_seg, f"{prefix}_pos_z",    0.0),
    }


def _load_pose_slot(prefix, target, data):
    """Carga pose_start/pose_end (o pose_inicio/pose_fin de un segmento) desde
    un dict. Compatible con dos formatos de clave para el indice:
      - formato nativo (v2.0, Guardar/Cargar de este addon): "idx"
      - formato evolutivo (jerry_config_*.json, jerry_story_generator.py): "index"
    """
    if not data:
        return
    for field, default in [
        ("file", ""), ("name", ""), ("idx", 0), ("duration", 10),
        ("interp", "SMOOTH"),
        ("rot_x", 0.0), ("rot_y", 0.0), ("rot_z", 0.0),
        ("pos_x", 0.0), ("pos_y", 0.0), ("pos_z", 0.0),
    ]:
        attr = f"{prefix}_{field}"
        if not hasattr(target, attr):
            continue
        if field == "idx":
            valor = data.get("idx", data.get("index", getattr(target, attr, default)))
        else:
            valor = data.get(field, getattr(target, attr, default))
        setattr(target, attr, valor)


# Nombres COMPLETOS de todos los flags "filter_*" de JerryAnimSegment
# (properties.py). Usada por _ser_segment/_load_segment para no dejar
# ninguno afuera del guardado/carga de configuracion.
# NOTA (Kebyn, 2026-08-06): antes solo se guardaban 8 de 44 -- faltaban
# filter_spine_2..7, todos los filter_front_*, filter_thigh/shin/foot/toe_l/r,
# filter_jaw/scull/ear/sombrero/sejas/no_bone_* -- causa real de "no guarda
# correctamente los valores aplicados".
_SEGMENT_FILTER_FIELDS = [
    "filter_show", "filter_main_bone", "filter_body",
    "filter_left_arm", "filter_right_arm", "filter_right_leg", "filter_left_leg",
    "filter_shield", "filter_spear", "filter_tail_3",
    "filter_spine_2", "filter_spine_3", "filter_spine_4",
    "filter_spine_5", "filter_spine_6", "filter_spine_7",
    "filter_front_thigh_l", "filter_front_thigh_r",
    "filter_front_shin_l", "filter_front_shin_r",
    "filter_front_foot_l", "filter_front_foot_r",
    "filter_front_toe_l", "filter_front_toe_r",
    "filter_thigh_l", "filter_thigh_r",
    "filter_shin_l", "filter_shin_r",
    "filter_foot_l", "filter_foot_r",
    "filter_toe_l", "filter_toe_r",
    "filter_jaw_bot", "filter_jaw_top",
    "filter_scull", "filter_scull_1",
    "filter_ear_l", "filter_ear_r", "filter_sombrero",
    "filter_sejas_1", "filter_sejas_2",
    "filter_no_bone_01", "filter_no_bone_02",
    "filter_no_bone_03", "filter_no_bone_04",
]


def _ser_segment(seg):
    """Serializa un JerryAnimSegment completo."""
    d = {
        # ── Identidad y rango ──────────────────────────────────────────────
        "label":            seg.label,
        "enabled":          seg.enabled,
        "show_config":      seg.show_config,
        "frame_start":      seg.frame_start,
        "frame_end":        seg.frame_end,
        "single_coord_mode": seg.single_coord_mode,
        "frame_end_auto":   seg.frame_end_auto,
        "seg_action_name":  seg.seg_action_name,
        # ── Poses de accion (el primer y ultimo item son las anclas de
        #    inicio/fin -- ver refactor pose_inicio/pose_fin -> action_poses,
        #    seg ya no tiene pose_start_*/pose_end_* propios) ──────────────
        "action_poses":     _ser_action_poses(seg.action_poses),
        # ── Parametros globales del segmento ──────────────────────────────
        "fps":              seg.fps,
        "entry_ratio":      seg.entry_ratio,
        "exit_ratio":       seg.exit_ratio,
        "interp_type":      seg.interp_type,
        "interp_mid_to_end": seg.interp_mid_to_end,
        "blend_in_frames":  seg.blend_in_frames,
        "blend_out_frames": seg.blend_out_frames,
        "blend_strength":   seg.blend_strength,
        # ── Bones afectados (afectan cuales bones procesa CONCATENAR) ─────
        "affect_body":      seg.affect_body,
        "affect_left_arm":  seg.affect_left_arm,
        "affect_right_arm": seg.affect_right_arm,
        "affect_left_leg":  seg.affect_left_leg,
        "affect_right_leg": seg.affect_right_leg,
        "affect_root":      seg.affect_root,
        "affect_shield":    seg.affect_shield,
        "affect_spear":     seg.affect_spear,
        # ── Lanzar / Recoger objetos ──────────────────────────────────────
        "throws": _ser_throws(seg.throws),
        # ── Parpadeo automatico propio de este segmento ────────────────────
        "blink_intervals": _ser_blink_intervals(seg.blink_intervals),
        # ── Filtros organicos propios de este segmento (aislamiento por
        #    segmento, Kebyn + Claude 2026-08-06 -- ver JerryAnimSegment.organic
        #    en properties.py) ────────────────────────────────────────────
        "organic": _ser_organic(seg.organic),
    }
    # ── Filtros de bones (excluidos del bake de CONCATENAR) — TODOS ───────
    for f in _SEGMENT_FILTER_FIELDS:
        d[f] = getattr(seg, f, False)
    # ── Intervalos de bloqueo por bone ("dividir en partes" el bloqueo,
    #    PORTADO desde alfred_animation_studio, Kebyn 2026-08-08) ─────────
    d["bone_blocks"] = [
        {
            "bone_key": entry.bone_key,
            "intervals": [
                {
                    "frame_start": iv.frame_start,
                    "frame_end":   iv.frame_end,
                    "enabled":     iv.enabled,
                }
                for iv in entry.intervals
            ],
        }
        for entry in seg.bone_blocks
    ]
    return d


def _load_segment(seg, d):
    """Carga todos los campos de un JerryAnimSegment desde un dict."""
    seg.label            = d.get("label",            seg.label)
    seg.enabled          = d.get("enabled",          seg.enabled)
    seg.show_config      = d.get("show_config",      seg.show_config)
    seg.frame_start      = d.get("frame_start",      seg.frame_start)
    seg.frame_end        = d.get("frame_end",        seg.frame_end)
    seg.single_coord_mode = d.get("single_coord_mode", seg.single_coord_mode)
    seg.frame_end_auto   = d.get("frame_end_auto",   seg.frame_end_auto)
    seg.seg_action_name  = d.get("seg_action_name",  seg.seg_action_name)
    # Poses. "pose_start"/"pose_end" solo se leen por compatibilidad con
    # configs viejas (seg ya no tiene esos atributos -- _load_pose_slot
    # los salta en silencio via hasattr). Los datos reales de hoy viven
    # en action_poses (primer/ultimo item = anclas de inicio/fin).
    _load_pose_slot("pose_start", seg, d.get("pose_start", {}))
    _load_pose_slot("pose_end",   seg, d.get("pose_end",   {}))
    _load_action_poses(seg.action_poses, d.get("action_poses", []))
    # Parametros
    seg.fps              = d.get("fps",              seg.fps)
    seg.entry_ratio      = d.get("entry_ratio",      seg.entry_ratio)
    seg.exit_ratio       = d.get("exit_ratio",       seg.exit_ratio)
    if hasattr(seg, "interp_type"):
        seg.interp_type      = d.get("interp_type",     seg.interp_type)
    if hasattr(seg, "interp_mid_to_end"):
        seg.interp_mid_to_end = d.get("interp_mid_to_end", seg.interp_mid_to_end)
    seg.blend_in_frames  = d.get("blend_in_frames",  seg.blend_in_frames)
    seg.blend_out_frames = d.get("blend_out_frames",  seg.blend_out_frames)
    seg.blend_strength   = d.get("blend_strength",    seg.blend_strength)
    # Bones afectados
    seg.affect_body      = d.get("affect_body",      seg.affect_body)
    seg.affect_left_arm  = d.get("affect_left_arm",  seg.affect_left_arm)
    seg.affect_right_arm = d.get("affect_right_arm", seg.affect_right_arm)
    seg.affect_left_leg  = d.get("affect_left_leg",  seg.affect_left_leg)
    seg.affect_right_leg = d.get("affect_right_leg", seg.affect_right_leg)
    seg.affect_root      = d.get("affect_root",      seg.affect_root)
    seg.affect_shield    = d.get("affect_shield",    seg.affect_shield)
    seg.affect_spear     = d.get("affect_spear",     seg.affect_spear)
    # Filtros de bones — TODOS (ver _SEGMENT_FILTER_FIELDS)
    for f in _SEGMENT_FILTER_FIELDS:
        if f in d and hasattr(seg, f):
            setattr(seg, f, d[f])
    # Lanzar / Recoger
    _load_throws(seg.throws, d.get("throws", {}))
    # Parpadeo automatico propio de este segmento
    _load_blink_intervals(seg.blink_intervals, d.get("blink_intervals", []))
    # GARANTIA "un parpadeo por segmento como minimo" (Kebyn, 2026-08-07):
    # los .json viejos (o los generados por el pipeline evolutivo de
    # reglas.zip que todavia no puebla "blink_intervals") dejan la carga de
    # arriba VACIA -- sin esto el segmento importado quedaria sin parpadear.
    # Idempotente: no hace nada si "blink_intervals" ya trajo datos.
    _aplicar_parpadeo_default_seg(seg)
    # Filtros organicos propios de este segmento (aislamiento por segmento)
    _load_organic(seg.organic, d.get("organic", {}))
    # Intervalos de bloqueo por bone (PORTADO desde alfred_animation_studio,
    # Kebyn 2026-08-08)
    seg.bone_blocks.clear()
    for bb_data in d.get("bone_blocks", []):
        entry = seg.bone_blocks.add()
        entry.bone_key = str(bb_data.get("bone_key", ""))
        for iv_data in bb_data.get("intervals", []):
            iv = entry.intervals.add()
            iv.frame_start = int(iv_data.get("frame_start", 0))
            iv.frame_end   = int(iv_data.get("frame_end", 0))
            iv.enabled     = bool(iv_data.get("enabled", True))


# =============================================================================
# GUARDAR SNAPSHOT COMPLETO
# =============================================================================

# NOTA (Kebyn, 2026-08-27): _ser_eye_expr / _load_eye_expr / _cargar_eye_slots_evolutivo
# eliminadas junto con el sistema de "Secuencia de Ojos" por-segmento (segs_cfg.eye_expr,
# st.eye_slots) -- ver panels.py / operators_base.py / properties.py para el resto
# retirado. jerryst.eye_expr (sistema de expresiones a nivel de personaje) no se toco.


class JRRSTST_OT_SaveConfig(Operator):
    bl_idname      = "jerryst.save_config"
    bl_label       = "Guardar configuracion"
    bl_description = "Guarda un snapshot completo de todos los valores del addon en un archivo JSON"

    def execute(self, context):
        st  = context.scene.jerryst
        og  = st.organic
        pc  = getattr(context.scene, "jerry_path", None)
        osc = getattr(st, "bone_oscillations", None)

        raw_name = st.config_name.strip() or "config_jerry"
        while raw_name.lower().endswith(".json"):
            raw_name = raw_name[:-5]
        filename = raw_name + ".json"

        # ── Paso 2: path recorder ─────────────────────────────────────────
        recorrido = {}
        if pc is not None:
            recorrido = {
                "blend_filepath":    pc.blend_filepath,
                "slot_inicio":       pc.slot_inicio,
                "frame_inicio":      pc.frame_inicio,
                "frame_fin_manual":  pc.frame_fin_manual,
                "frames_por_bloque": pc.frames_por_bloque,
                # NUEVO (portado de Alfred, Kebyn 2026-08-05): estilo de
                # caminata por tramo ("Normal"/"Lento"/"Herido"/"Rapido"/
                # "Correr"). walk_style es el default global para tramos
                # 'caminar' nuevos; walk_styles es la coleccion real (una
                # entrada por tramo, mismo orden que el recorrido) que
                # decide la animacion generada.
                "walk_style":        pc.walk_style,
                "walk_styles":       [
                    {"style": item.style, "applied_style": item.applied_style}
                    for item in pc.walk_styles
                ],
                "root_rot_x":        pc.root_rot_x,
                "root_rot_y":        pc.root_rot_y,
                "root_rot_z":        pc.root_rot_z,
                "output_dir":        pc.output_dir,
                "execute_inscene":   pc.execute_inscene,
                # Coordenadas grabadas del recorrido
                "path_points": [
                    {
                        "x": round(pt.coords[0], 6),
                        "y": round(pt.coords[1], 6),
                        "z": round(pt.coords[2], 6),
                        "texture":    pt.texture,
                        "face_index": pt.face_index,
                        # FIX (Kebyn, 2026-08-12): el dropdown "Caminar/Parada"
                        # (tipo_segmento) y los frames de parada por-punto
                        # (parada_frames_punto) que se editan en la lista del
                        # Paso 1 no se estaban guardando -- al reimportar el
                        # .json todos los puntos volvian a AUTO, perdiendo
                        # las paradas marcadas a mano.
                        "tipo_segmento":       pt.tipo_segmento,
                        "parada_frames_punto": pt.parada_frames_punto,
                        # NUEVO (Kebyn, 2026-09-14, portado de Alfred):
                        # animacion .py importada por punto de parada --
                        # normalizada a ruta ABSOLUTA (bpy.path.abspath)
                        # antes de guardar, para que siga siendo valida al
                        # importar el config desde otro .blend/carpeta.
                        "parada_anim_file": (
                            bpy.path.abspath(pt.parada_anim_file)
                            if pt.parada_anim_file else ""
                        ),
                        # NUEVO (Kebyn, 2026-09-14, portado de Alfred):
                        # orientacion (heading) guardada a mano para este
                        # punto de parada -- ver
                        # JRRSTPathPoint.parada_rot_saved/parada_rot_z y
                        # JRRSTPR_OT_SaveParadaRot (path_recorder.py).
                        "parada_rot_saved": bool(pt.parada_rot_saved),
                        "parada_rot_z": float(pt.parada_rot_z),
                    }
                    for pt in pc.path_points
                ],
                # Duracion individual de cada parada detectada (una entrada
                # por segmento tipo 'parada', mismo orden que _group_segments()).
                # FIX (Kebyn, 2026-08-12): tampoco se estaba guardando.
                "paradas_frames": [
                    {"frames": item.frames} for item in pc.paradas_frames
                ],
            }

        # ── Oscilaciones de bones (jerryst.bone_oscillations) ─────────────
        osc_data = {}
        if osc is not None:
            osc_data = {
                "enabled":    osc.enabled,
                "active_idx": osc.active_idx,
                "items": [_ser_osc_item(item) for item in osc.items],
            }

        # ── Paso 3: segmentos ─────────────────────────────────────────────
        segs_cfg  = getattr(context.scene, "jerry_segs", None)
        segmentos = []
        if segs_cfg is not None:
            for seg in segs_cfg.segments:
                segmentos.append(_ser_segment(seg))

        # NOTA (Kebyn, 2026-08-27): serializacion de eye_expr/eye_slots por-
        # segmento eliminada junto con el sistema -- ver nota en linea ~650.
        eye_expr_data  = {}
        eye_slots_data = []

        cfg = {
            "_version": "2.0",
            "_info": "Snapshot completo JRRST Animation Studio — todos los pasos",

            # ── Paso 1: importacion y rutas ───────────────────────────────
            "paso_1": {
                "armature_name": st.armature_name,
                "poses_dir":     st.poses_dir,
                "anim_dir":      st.anim_dir,
                "config_dir":    st.config_dir,
                "historia_json": st.historia_json,
            },

            # ── Tiempos y parametros globales ─────────────────────────────
            "global": {
                "fps":            st.fps,
                "start_frame":    st.start_frame,
                "entry_ratio":    st.entry_ratio,
                "exit_ratio":     st.exit_ratio,
                "root_pos_key_point": st.root_pos_key_point,
                "key_point_info":     st.key_point_info,
                # Estado de animacion generada (para restaurar el panel exportar)
                "anim_generated":   st.anim_generated,
                "total_frames_gen": st.total_frames_gen,
                "end_frame_gen":    st.end_frame_gen,
            },

            # ── Exportacion ───────────────────────────────────────────────
            "exportacion": {
                "slot_number": st.export_slot_number,
                "tipo":        st.export_type,
                "descripcion": st.export_desc,
            },

            # ── Pose INICIO (Paso 1 / Paso 3 global) ─────────────────────
            "pose_start": _ser_pose_slot("pose_start", st),
            "pose_end":   _ser_pose_slot("pose_end",   st),

            # ── Slots de accion intermedios (Paso 1) ─────────────────────
            "action_poses": _ser_action_poses(st.action_poses),

            # ── Paso 2: path recorder ─────────────────────────────────────
            "paso_2_recorrido": recorrido,

            # ── Filtros organicos ─────────────────────────────────────────
            "organic": _ser_organic(og),

            # ── Oscilaciones de bones ─────────────────────────────────────
            "bone_oscillations": osc_data,

            # ── Paso 3: segmentos ──────���──────────────────────────────────
            "paso_3_segmentos": {
                "armature_name": segs_cfg.armature_name if segs_cfg else st.armature_name,
                "active_index":  segs_cfg.active_index  if segs_cfg else 0,
                "segments":      segmentos,
            },

            # ── Sistema de parpadeo ───────────────────────────────────────
            "eye_system": eye_expr_data,

            # ── Secuencia rica de ojos (eye_slots) ─────────────────────────
            "eye_slots_nativo": eye_slots_data,

            # ── Importacion de objetos (escudo, hueso, etc.) ──────────────
            "object_imports": _serialize_object_imports(st),

            # ── Compatibilidad: claves legacy del formato v1 ──────────────
            "armature_name":  st.armature_name,
            "fps":            st.fps,
            "start_frame":    st.start_frame,
            "entry_ratio":    st.entry_ratio,
            "exit_ratio":     st.exit_ratio,
            "export_slot_number": st.export_slot_number,
            "export_type":    st.export_type,
            "export_desc":    st.export_desc,
        }

        if _gv2 is not None:                       # conserva las secciones del guion 2.0 (audio, camara, objetos, sonidos...) que el panel no edita
            try:
                _gv2.fusionar_en(cfg, _gv2.recordado(bpy.context.scene))
            except Exception as e:
                print('[guion_v2] no se pudieron conservar las secciones 2.0:', e)

        folder = bpy.path.abspath(st.config_dir)
        if not os.path.isdir(folder):
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception as e:
                self.report({"ERROR"}, f"No se pudo crear carpeta: {e}")
                return {"CANCELLED"}

        out_path = os.path.join(folder, filename)
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            n_pts  = len(recorrido.get("path_points", []))
            n_segs = len(segmentos)
            self.report({"INFO"},
                f"Snapshot guardado: {filename}  "
                f"({n_pts} punto(s) recorrido | {n_segs} segmento(s) Paso 3)"
            )
        except Exception as e:
            self.report({"ERROR"}, f"Error al guardar: {e}")
            return {"CANCELLED"}
        return {"FINISHED"}


# =============================================================================
# CARGAR SNAPSHOT COMPLETO
# =============================================================================

class JRRSTST_OT_LoadConfig(Operator):
    bl_idname      = "jerryst.load_config"
    bl_label       = "Cargar configuracion"
    bl_description = "Carga un snapshot completo de sesion desde un archivo JSON"

    filepath:    StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        start = bpy.path.abspath(context.scene.jerryst.config_dir)
        if os.path.isdir(start):
            self.filepath = start + os.sep
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        st  = context.scene.jerryst
        og  = st.organic
        pc  = getattr(context.scene, "jerry_path", None)
        osc = getattr(st, "bone_oscillations", None)

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            self.report({"ERROR"}, f"No se pudo leer JSON: {e}")
            return {"CANCELLED"}

        version = cfg.get("_version", "1.0")
        if _gv2 is not None:                       # recuerda las secciones del guion 2.0 para no perderlas al volver a guardar
            try:
                _gv2.recordar(cfg, bpy.context.scene)
            except Exception as e:
                print('[guion_v2] no se pudieron recordar las secciones 2.0:', e)

        # ── Paso 1: rutas e importacion ───────────────────────────────────
        p1 = cfg.get("paso_1", cfg)   # fallback al root para formato v1
        st.armature_name = p1.get("armature_name", cfg.get("armature_name", st.armature_name))
        st.poses_dir     = p1.get("poses_dir",     cfg.get("poses_dir",     st.poses_dir))
        st.anim_dir      = p1.get("anim_dir",      cfg.get("anim_dir",      st.anim_dir))
        st.config_dir    = p1.get("config_dir",    cfg.get("config_dir",    st.config_dir))
        st.historia_json = p1.get("historia_json", cfg.get("historia_json", st.historia_json))

        # ── Parametros globales ───────────────────────────────────────────
        g = cfg.get("global", cfg)
        st.fps         = g.get("fps",         cfg.get("fps",         st.fps))
        st.start_frame = g.get("start_frame", cfg.get("start_frame", st.start_frame))
        st.entry_ratio = g.get("entry_ratio", cfg.get("entry_ratio", st.entry_ratio))
        st.exit_ratio  = g.get("exit_ratio",  cfg.get("exit_ratio",  st.exit_ratio))
        if "root_pos_key_point" in g or "root_pos_key_point" in cfg:
            try:
                st.root_pos_key_point = str(
                    g.get("root_pos_key_point", cfg.get("root_pos_key_point", "1")))
            except Exception:
                pass
        st.key_point_info = g.get("key_point_info", cfg.get("key_point_info", st.key_point_info))
        # Restaurar estado de animacion si el JSON lo incluye (formato nuevo)
        if "anim_generated" in g:
            st.anim_generated   = bool(g["anim_generated"])
            st.total_frames_gen = int(g.get("total_frames_gen", st.total_frames_gen))
            st.end_frame_gen    = int(g.get("end_frame_gen",    st.end_frame_gen))

        # ── Exportacion ───────────────────────────────────────────────────
        ex = cfg.get("exportacion", cfg)
        st.export_slot_number = ex.get("slot_number", cfg.get("export_slot_number", st.export_slot_number))
        st.export_type        = ex.get("tipo",        cfg.get("export_type",        st.export_type))
        st.export_desc        = ex.get("descripcion", cfg.get("export_desc",        st.export_desc))

        # ── Pose INICIO / FIN globales ────────────────────────────────────
        # "pose_start"/"pose_end" = formato nativo. "pose_inicio"/"pose_fin" =
        # formato evolutivo (jerry_config_*.json / alfred_config_*.json).
        _load_pose_slot("pose_start", st, cfg.get("pose_start", cfg.get("pose_inicio", {})))
        _load_pose_slot("pose_end",   st, cfg.get("pose_end",   cfg.get("pose_fin",    {})))

        # ── Slots de accion intermedios ───────────────────────────────────
        # Misma clave "action_poses" y mismos campos en ambos formatos.
        _load_action_poses(st.action_poses, cfg.get("action_poses", []))

        # ── Paso 2: path recorder ─────────────────────────────────────────
        # "paso_2_recorrido" = formato nativo. "paso1_path" = formato evolutivo.
        pr = cfg.get("paso_2_recorrido", cfg.get("paso1_path", {}))
        if pr and pc is not None:
            pc.slot_inicio       = pr.get("slot_inicio",       pc.slot_inicio)
            pc.frame_inicio      = pr.get("frame_inicio",      pc.frame_inicio)
            pc.frame_fin_manual  = pr.get("frame_fin_manual",  pc.frame_fin_manual)
            pc.frames_por_bloque = pr.get("frames_por_bloque", pc.frames_por_bloque)
            pc.root_rot_x        = pr.get("root_rot_x",        pc.root_rot_x)
            pc.root_rot_y        = pr.get("root_rot_y",        pc.root_rot_y)
            pc.root_rot_z        = pr.get("root_rot_z",        pc.root_rot_z)
            if pr.get("output_dir"):
                pc.output_dir    = pr["output_dir"]
            pc.execute_inscene   = pr.get("execute_inscene",   pc.execute_inscene)
            # Personaje .blend — NUNCA se guardaba ni cargaba antes de este
            # parche (blend_filepath no estaba en ningun formato persistido).
            if pr.get("blend_filepath"):
                pc.blend_filepath = pr["blend_filepath"]
            # Restaurar coordenadas del recorrido. Formato nativo: x/y/z
            # sueltos. Formato evolutivo: "coords": [x, y, z].
            pc.path_points.clear()
            for pd in pr.get("path_points", []):
                pt = pc.path_points.add()
                coords = pd.get("coords")
                if isinstance(coords, (list, tuple)) and len(coords) >= 3:
                    cx, cy, cz = coords[0], coords[1], coords[2]
                else:
                    cx = pd.get("x", 0.0); cy = pd.get("y", 0.0); cz = pd.get("z", 0.0)
                pt.coords     = (cx, cy, cz)
                pt.texture    = pd.get("texture",    "")
                pt.face_index = pd.get("face_index", "")
                # FIX (Kebyn, 2026-08-12): restaurar el tipo de segmento
                # (dropdown Caminar/Parada, pt.tipo_segmento) y los frames
                # de parada por-punto (pt.parada_frames_punto) editados en
                # la lista del Paso 1 -- antes NO se guardaban en el .json
                # y todos los puntos volvian a AUTO al reimportar.
                pt.tipo_segmento       = str(pd.get("tipo_segmento_raw") or pd.get("tipo_segmento") or "AUTO").upper()   # los guiones portables guardan "parada" en minusculas (+ `tipo_segmento_raw` = "PARADA"); el enum es AUTO / SALTAR / PARADA / OBSERVAR
                pt.parada_frames_punto = pd.get("parada_frames_punto", pt.parada_frames_punto)
                # NUEVO (Kebyn, 2026-09-14, portado de Alfred): restaurar
                # la animacion .py importada de este punto de parada, si
                # el JSON la trae (JSON viejo sin la clave -> "", sin
                # animacion importada -- comportamiento normal).
                pt.parada_anim_file = pd.get("parada_anim_file", "")
                # NUEVO (Kebyn, 2026-09-14, portado de Alfred): restaurar
                # la orientacion (heading) guardada a mano para este punto
                # de parada, si el JSON la trae. Si no viene la clave
                # (JSON viejo, o el punto no tenia orientacion guardada),
                # se deja en False -- comportamiento de heading automatico
                # normal.
                pt.parada_rot_saved = bool(pd.get("parada_rot_saved", False))
                pt.parada_rot_z = float(pd.get("parada_rot_z", 0.0))

            # Restaurar duracion de cada parada detectada (pc.paradas_frames).
            # FIX (Kebyn, 2026-08-12): tampoco se guardaba/restauraba antes;
            # se hace ANTES de sync_paradas_frames() para que, si la cantidad
            # de paradas coincide con el recorrido recien cargado (caso
            # normal), no haya nada que ajustar y los frames queden
            # exactamente como se guardaron.
            if "paradas_frames" in pr:
                pc.paradas_frames.clear()
                for _pf in pr["paradas_frames"]:
                    _item = pc.paradas_frames.add()
                    _item.frames = int(_pf.get("frames", pc.frames_parada) if isinstance(_pf, dict) else _pf)      # nativo: [{"frames": n}]; portables / evolutivo: [n]

            # Restaurar estilo de caminata (portado de Alfred, Kebyn
            # 2026-08-05). Se restaura ANTES de sync_walk_styles() para
            # que, si la cantidad de tramos 'caminar' coincide con el
            # recorrido recien cargado (caso normal), no haya nada que
            # ajustar y los estilos queden exactamente como se guardaron.
            if "walk_style" in pr:
                pc.walk_style = pr["walk_style"]
            if "walk_styles" in pr:
                pc.walk_styles.clear()
                for _ws in pr["walk_styles"]:
                    _item = pc.walk_styles.add()
                    _item.style = _ws.get("style", "NORMAL")
                    _item.applied_style = _ws.get("applied_style", "")

            from .path_recorder import sync_paradas_frames as _sync_pf, sync_walk_styles as _sync_ws
            _sync_pf(pc)
            _sync_ws(pc)

        # También aceptar key_point_coordinates (formato evolutivo, raiz del
        # archivo) como respaldo si paso1_path/paso_2_recorrido no trae nada
        # util para el punto de posicion seleccionado.
        kpc = cfg.get("key_point_coordinates", {})
        if kpc and "root_pos_key_point" not in cfg and "root_pos_key_point" not in g:
            try:
                st.root_pos_key_point = str(kpc.get("index", st.root_pos_key_point))
            except Exception:
                pass

        # ── Filtros organicos ─────────────────────────────────────────────
        _load_organic(og, cfg.get("organic", {}))

        # ── Oscilaciones de bones ─────────────────────────────────────────
        osc_data = cfg.get("bone_oscillations", {})
        if osc_data and osc is not None:
            osc.enabled    = osc_data.get("enabled",    osc.enabled)
            osc.active_idx = osc_data.get("active_idx", osc.active_idx)
            _load_osc_items(osc.items, osc_data.get("items", []))

        # ── Paso 3: segmentos ─────────────────────────────────────────────
        # "paso_3_segmentos.segments" = formato nativo (dicts ya anidados).
        # "jerry_segs" = formato evolutivo (lista plana en la raiz, vocabulario
        # cuadrupedo affect_front_left_leg/filter_tail/etc, throws_items plano).
        segs_cfg  = getattr(context.scene, "jerry_segs", None)
        p3        = cfg.get("paso_3_segmentos", {})
        segs_data_evolutivo = cfg.get("jerry_segs") if not p3 else None

        if p3 and segs_cfg is not None:
            if "armature_name" in p3:
                segs_cfg.armature_name = p3["armature_name"]
            segs_data = p3.get("segments", [])
            segs_cfg.segments.clear()
            for sd in segs_data:
                seg = segs_cfg.segments.add()
                _load_segment(seg, sd)
            if "active_index" in p3:
                total = len(segs_cfg.segments)
                segs_cfg.active_index = max(0, min(p3["active_index"], total - 1)) if total > 0 else 0
        elif segs_data_evolutivo and segs_cfg is not None:
            segs_cfg.segments.clear()
            for sd in segs_data_evolutivo:
                if "_NOTA" in sd:
                    continue
                seg = segs_cfg.segments.add()
                _load_segment(seg, _convertir_jerry_seg_a_nativo(sd))
            segs_cfg.active_index = 0

        # NOTA (Kebyn, 2026-08-27): carga de eye_expr/eye_slots por-segmento
        # eliminada junto con el sistema -- ver nota en linea ~650. Se
        # conserva eye_slots_list=[] para no romper el conteo del resumen
        # mas abajo (n_eye).
        eye_slots_list = []

        # ── Importacion de objetos (escudo, hueso, etc.) ──────────────────
        oi_data = cfg.get("object_imports", {})
        if oi_data and hasattr(st, "object_imports"):
            _aplicar_object_imports(st, oi_data)

        # ── Restaurar estado de animacion generada ────────────────────────
        # Solo calcular si el JSON no tenia los campos en el bloque "global"
        # (JSONs guardados antes de la correccion). Para JSONs nuevos ya se
        # restauraron arriba al leer el bloque global.
        if "anim_generated" not in g:
            # El frame real de inicio viene del segmento o del path recorder,
            # NO de global.start_frame (que puede ser 1 aunque la animacion
            # empiece en un frame mucho mayor, ej. frame 1331).
            _real_start = st.start_frame  # fallback al valor ya cargado

            # Fuente 1: frame_start del primer segmento cargado
            if segs_cfg is not None and len(segs_cfg.segments) > 0:
                _fs = getattr(segs_cfg.segments[0], "frame_start", 0)
                if _fs > 0:
                    _real_start = _fs

            # Fuente 2: frame_inicio del path recorder (si no habia segmento util)
            if _real_start == st.start_frame and pc is not None:
                _fi = getattr(pc, "frame_inicio", 0)
                if _fi > 0:
                    _real_start = _fi

            # Actualizar start_frame con el valor real de inicio de la animacion
            st.start_frame = _real_start

            # Total y fin desde el ultimo segmento cargado
            _total = 0
            if segs_cfg is not None and len(segs_cfg.segments) > 0:
                _seg_last = segs_cfg.segments[-1]
                _end_auto = getattr(_seg_last, "frame_end_auto", 0)
                _end_raw  = getattr(_seg_last, "frame_end",      0)
                _seg_end  = _end_raw if _end_raw > getattr(_seg_last, "frame_start", 1) else _end_auto
                if _seg_end >= _real_start:
                    _total = _seg_end - _real_start + 1

            # Fallback: sumar duraciones de poses si no habia segmentos
            if _total == 0:
                _ps_dur = cfg.get("pose_start", {}).get("duration", 0)
                _pe_dur = cfg.get("pose_end",   {}).get("duration", 0)
                _ap_dur = sum(ap.get("duration", 0) for ap in cfg.get("action_poses", []))
                _total  = _ps_dur + _ap_dur + _pe_dur

            if _total > 0:
                st.total_frames_gen = _total
                st.end_frame_gen    = _real_start + _total - 1
                st.anim_generated   = True

        # Nombre del archivo cargado → config_name
        loaded_name = os.path.splitext(os.path.basename(self.filepath))[0]
        st.config_name = loaded_name

        try:   # assets portables declarados por el JSON (objetos con su .blend): visibles desde que se carga, antes de concatenar
            from . import objetos_mundo as _objetos_mundo
            _objetos_mundo.asegurar_portables_al_cargar(cfg)
        except Exception as _e:
            print(f"[guion] assets portatiles al cargar: {_e}")
        try:   # guion 2.0 con voces: se sincronizan con Voz Sync en el inicio que dice el guion (audio_import)
            from . import audio_import as _audio_import
            _audio_import.post_cargar(context)
        except Exception as _e:
            print(f"[guion] audio: {_e}")

        # Resumen en statusbar
        n_pts  = len(pr.get("path_points", []))   if pr  else 0
        n_segs = len(p3.get("segments", []))      if p3  else len(segs_data_evolutivo or [])
        n_osc  = len(osc_data.get("items", []))   if osc_data else 0
        n_eye  = len(eye_slots_list)
        formato = "evolutivo" if (segs_data_evolutivo or "paso1_path" in cfg or "pose_inicio" in cfg) else "nativo"
        self.report({"INFO"},
            f"Snapshot cargado: {loaded_name}.json  (formato {formato})  "
            f"(v{version} | {n_pts} pt recorrido | {n_segs} seg | {n_osc} osc | {n_eye} eye_slots)"
        )
        return {"FINISHED"}


# =============================================================================
# ABRIR CARPETA CONFIG
# =============================================================================

class JRRSTST_OT_OpenConfigFolder(Operator):
    bl_idname = "jerryst.open_config_folder"
    bl_label  = "Abrir carpeta configuraciones"

    def execute(self, context):
        open_folder(bpy.path.abspath(context.scene.jerryst.config_dir))
        return {"FINISHED"}


# =============================================================================
# HELPERS: SERIALIZAR / RESTAURAR THROWS Y OBJECT_IMPORTS
# (portado desde Alfred Animation Studio)
# =============================================================================

def _ser_throws(th):
    """Serializa un JerryThrowsSettings (de un segmento) a dict."""
    items_list = []
    for item in th.items:
        wps = [{"label": wp.label, "x": round(wp.x, 4), "y": round(wp.y, 4),
                "z": round(wp.z, 4), "easing": wp.easing, "enabled": wp.enabled}
               for wp in item.waypoints]
        items_list.append({
            "enabled":            item.enabled,
            "label":              item.label,
            "mode":               item.mode,
            "blend_path":         item.blend_path,
            "object_folder":      item.object_folder,
            "blend_filename":     item.blend_filename,
            "object_name":        item.object_name,
            "levels_up":          item.levels_up,
            "frame_start":        item.frame_start,
            "frame_end":          item.frame_end,
            "parent_armature":    item.parent_armature,
            "parent_bone":        item.parent_bone,
            "loc_x":              round(item.loc_x, 4),
            "loc_y":              round(item.loc_y, 4),
            "loc_z":              round(item.loc_z, 4),
            "rot_x":              round(item.rot_x, 4),
            "rot_y":              round(item.rot_y, 4),
            "rot_z":              round(item.rot_z, 4),
            "scale_uniform":      round(item.scale_uniform, 3),
            "target_object":      item.target_object,
            "target_armature":    item.target_armature,
            "target_bone":        item.target_bone,
            "dest_x":             round(item.dest_x, 4),
            "dest_y":             round(item.dest_y, 4),
            "dest_z":             round(item.dest_z, 4),
            "easing_global":      item.easing_global,
            "spin_during_flight": item.spin_during_flight,
            "spin_turns":         round(item.spin_turns, 2),
            "waypoints":          wps,
        })
    return {"enabled": th.enabled, "items": items_list}


def _load_throws(th, data):
    """Restaura un JerryThrowsSettings desde un dict."""
    if not data:
        return
    th.enabled = bool(data.get("enabled", False))
    th.items.clear()
    for entry in data.get("items", []):
        item = th.items.add()
        item.enabled            = bool(entry.get("enabled", True))
        item.label              = str(entry.get("label", "Lanzamiento"))
        item.mode               = str(entry.get("mode", "THROW"))
        item.blend_path         = str(entry.get("blend_path", ""))
        item.object_folder      = str(entry.get("object_folder", ""))
        item.blend_filename     = str(entry.get("blend_filename", ""))
        item.object_name        = str(entry.get("object_name", ""))
        item.levels_up          = int(entry.get("levels_up", 4))
        item.frame_start        = int(entry.get("frame_start", 1))
        item.frame_end          = int(entry.get("frame_end", 30))
        item.parent_armature    = str(entry.get("parent_armature", "Dog_001_rig"))
        item.parent_bone        = str(entry.get("parent_bone", ""))
        item.loc_x              = float(entry.get("loc_x", 0.0))
        item.loc_y              = float(entry.get("loc_y", 0.0))
        item.loc_z              = float(entry.get("loc_z", 0.0))
        item.rot_x              = float(entry.get("rot_x", 0.0))
        item.rot_y              = float(entry.get("rot_y", 0.0))
        item.rot_z              = float(entry.get("rot_z", 0.0))
        item.scale_uniform      = float(entry.get("scale_uniform", 1.0))
        item.target_object      = str(entry.get("target_object", ""))
        item.target_armature    = str(entry.get("target_armature", "Dog_001_rig"))
        item.target_bone        = str(entry.get("target_bone", ""))
        item.dest_x             = float(entry.get("dest_x", 0.0))
        item.dest_y             = float(entry.get("dest_y", 3.0))
        item.dest_z             = float(entry.get("dest_z", 0.0))
        item.easing_global      = str(entry.get("easing_global", "SMOOTH"))
        item.spin_during_flight = bool(entry.get("spin_during_flight", False))
        item.spin_turns         = float(entry.get("spin_turns", 1.0))
        item.imported_object_name = ""  # No restaurar: se reimporta en CONCATENAR
        item.waypoints.clear()
        for wp_data in entry.get("waypoints", []):
            wp         = item.waypoints.add()
            wp.label   = str(wp_data.get("label", "Punto"))
            wp.x       = float(wp_data.get("x", 0.0))
            wp.y       = float(wp_data.get("y", 0.0))
            wp.z       = float(wp_data.get("z", 2.0))
            wp.easing  = str(wp_data.get("easing", "SMOOTH"))
            wp.enabled = bool(wp_data.get("enabled", True))


def _serialize_object_imports(st):
    """Serializa la config completa de Importacion de Objetos para el JSON."""
    oi = st.object_imports
    items_list = []
    for item in oi.items:
        items_list.append({
            "label":               item.label,
            "object_folder":       item.object_folder,
            "blend_filename":      item.blend_filename,
            "object_name":         item.object_name,
            "frame_start":         item.frame_start,
            "frame_end":           item.frame_end,
            "parent_armature":     item.parent_armature,
            "parent_bone":         item.parent_bone,
            "loc_x":               round(item.loc_x, 4),
            "loc_y":               round(item.loc_y, 4),
            "loc_z":               round(item.loc_z, 4),
            "rot_x":               round(item.rot_x, 4),
            "rot_y":               round(item.rot_y, 4),
            "rot_z":               round(item.rot_z, 4),
            "scale_uniform":       round(item.scale_uniform, 4),
            "levels_up":           item.levels_up,
            "enabled":             item.enabled,
            "segment_idx":         item.segment_idx,
            "transition_in":           getattr(item, "transition_in", "NONE"),
            "transition_in_duration":  getattr(item, "transition_in_duration", 8),
            "transition_out":          getattr(item, "transition_out", "NONE"),
            "transition_out_duration": getattr(item, "transition_out_duration", 8),
            "imported_object_name": item.imported_object_name,
        })
    return {
        "enabled": oi.enabled,
        "items":   items_list,
        "editor": {
            "edit_label":           oi.edit_label,
            "edit_object_folder":   oi.edit_object_folder,
            "edit_blend_filename":  oi.edit_blend_filename,
            "edit_object_name":     oi.edit_object_name,
            "edit_frame_start":     oi.edit_frame_start,
            "edit_frame_end":       oi.edit_frame_end,
            "edit_parent_armature": oi.edit_parent_armature,
            "edit_parent_bone":     oi.edit_parent_bone,
            "edit_loc_x":           round(oi.edit_loc_x, 4),
            "edit_loc_y":           round(oi.edit_loc_y, 4),
            "edit_loc_z":           round(oi.edit_loc_z, 4),
            "edit_rot_x":           round(oi.edit_rot_x, 4),
            "edit_rot_y":           round(oi.edit_rot_y, 4),
            "edit_rot_z":           round(oi.edit_rot_z, 4),
            "edit_scale_uniform":   round(oi.edit_scale_uniform, 4),
            "edit_levels_up":       oi.edit_levels_up,
            "edit_segment_idx":     oi.edit_segment_idx,
        },
    }


def _aplicar_object_imports(st, data):
    """Restaura la config de Importacion de Objetos desde un dict."""
    oi = st.object_imports
    oi.enabled = bool(data.get("enabled", False))
    oi.items.clear()
    for item_data in data.get("items", []):
        item = oi.items.add()
        item.label                = item_data.get("label", "Objeto")
        item.object_folder        = item_data.get("object_folder", "vanilla/shield")
        item.blend_filename       = item_data.get("blend_filename", "shield.blend")
        item.object_name          = item_data.get("object_name", "shield")
        item.frame_start          = int(item_data.get("frame_start", 1))
        item.frame_end            = int(item_data.get("frame_end", 60))
        item.parent_armature      = item_data.get("parent_armature", "Dog_001_rig")
        item.parent_bone          = item_data.get("parent_bone", "")
        item.loc_x                = float(item_data.get("loc_x", 0.0))
        item.loc_y                = float(item_data.get("loc_y", 0.0))
        item.loc_z                = float(item_data.get("loc_z", 0.0))
        item.rot_x                = float(item_data.get("rot_x", 0.0))
        item.rot_y                = float(item_data.get("rot_y", 0.0))
        item.rot_z                = float(item_data.get("rot_z", 0.0))
        item.scale_uniform        = float(item_data.get("scale_uniform", 1.0))
        item.levels_up            = int(item_data.get("levels_up", 4))
        item.enabled              = bool(item_data.get("enabled", True))
        item.segment_idx          = int(item_data.get("segment_idx", -1))
        if hasattr(item, "transition_in"):
            v = item_data.get("transition_in", "NONE")
            item.transition_in = v if v else "NONE"
        if hasattr(item, "transition_in_duration"):
            item.transition_in_duration = int(item_data.get("transition_in_duration", 8))
        if hasattr(item, "transition_out"):
            v = item_data.get("transition_out", "NONE")
            item.transition_out = v if v else "NONE"
        if hasattr(item, "transition_out_duration"):
            item.transition_out_duration = int(item_data.get("transition_out_duration", 8))
        item.imported_object_name = ""  # No restaurar: se reimporta en CONCATENAR

    editor = data.get("editor", {})
    if editor:
        oi.edit_label           = editor.get("edit_label",           oi.edit_label)
        oi.edit_object_folder   = editor.get("edit_object_folder",   oi.edit_object_folder)
        oi.edit_blend_filename  = editor.get("edit_blend_filename",  oi.edit_blend_filename)
        oi.edit_object_name     = editor.get("edit_object_name",     oi.edit_object_name)
        oi.edit_frame_start     = int(editor.get("edit_frame_start", oi.edit_frame_start))
        oi.edit_frame_end       = int(editor.get("edit_frame_end",   oi.edit_frame_end))
        oi.edit_parent_armature = editor.get("edit_parent_armature", oi.edit_parent_armature)
        oi.edit_parent_bone     = editor.get("edit_parent_bone",     oi.edit_parent_bone)
        oi.edit_loc_x           = float(editor.get("edit_loc_x",     oi.edit_loc_x))
        oi.edit_loc_y           = float(editor.get("edit_loc_y",     oi.edit_loc_y))
        oi.edit_loc_z           = float(editor.get("edit_loc_z",     oi.edit_loc_z))
        oi.edit_rot_x           = float(editor.get("edit_rot_x",     oi.edit_rot_x))
        oi.edit_rot_y           = float(editor.get("edit_rot_y",     oi.edit_rot_y))
        oi.edit_rot_z           = float(editor.get("edit_rot_z",     oi.edit_rot_z))
        oi.edit_scale_uniform   = float(editor.get("edit_scale_uniform", oi.edit_scale_uniform))
        oi.edit_levels_up       = int(editor.get("edit_levels_up",   oi.edit_levels_up))
        oi.edit_segment_idx     = int(editor.get("edit_segment_idx", oi.edit_segment_idx))
