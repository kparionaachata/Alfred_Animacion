
from .blender_compat import get_fcurves as _get_action_fcurves, new_fcurve as _new_fcurve

# -*- coding: utf-8 -*-
"""
operators_segments.py — Jerry Animation Studio v2.0
Paso 3: Segmentos de refinado sobre la animacion generada por Pasos 1+2.

LOGICA CENTRAL:
  La animacion de recorrido (generada por path_recorder) ya existe en la
  timeline con sus fcurves de bones y de root. El Paso 3 NO la borra ni la
  reemplaza: la modula.

  Por cada JerryAnimSegment el operador APLICAR_SEGMENTOS:
    1. Lee los fcurves ya existentes del armature en el rango [frame_start, frame_end].
    2. Carga las poses .json de inicio / intermedio / final.
    3. Para cada frame del segmento calcula:
         t  = posicion normalizada [0,1] dentro del segmento
         pose_valor = interpolar( pose_start, pose_mid, pose_end, t, interp_type )
         blend  = calcular_alpha( t, blend_in_frames, blend_out_frames ) * blend_strength
         nuevo  = lerp( fcurve_existente[frame], pose_valor, blend )
    4. Escribe el nuevo valor directamente en el keyframe existente del fcurve.
       Si no hay keyframe en ese frame lo inserta.

  El resultado es que la rana sigue su recorrido (traslacion del root, ciclo de
  caminar/saltar) pero los bones seleccionados adoptan la pose configurada
  durante ese intervalo, con transiciones suaves de entrada y salida.

OPERADORES:
  JRRSTSEG_OT_Add            — agrega un segmento nuevo
  JRRSTSEG_OT_Remove         — elimina el segmento activo
  JRRSTSEG_OT_Move           — sube/baja el segmento activo
  JRRSTSEG_OT_Duplicate      — duplica el segmento activo
  JRRSTSEG_OT_PickPoseStart  — selecciona .json para pose inicio
  JRRSTSEG_OT_PickPoseMid    — selecciona .json para pose intermedia
  JRRSTSEG_OT_PickPoseEnd    — selecciona .json para pose fin
  JRRSTSEG_OT_SetFrameStart  — captura frame actual como frame_start
  JRRSTSEG_OT_SetFrameMid    — captura frame actual como frame_mid
  JRRSTSEG_OT_SetFrameEnd    — captura frame actual como frame_end
  JRRSTSEG_OT_SaveConfig     — guarda la lista de segmentos a .json
  JRRSTSEG_OT_LoadConfig     — carga la lista de segmentos desde .json
"""

import bpy, json, os, math, datetime
from mathutils import Matrix
from bpy.types import Operator
from bpy.props import StringProperty, IntProperty, EnumProperty, FloatProperty, BoolProperty

from .constants import BONES_LISTA_FULL, BONES_LISTA, SECONDARY_ARMATURES, _BONE_DEFAULT, INTERP_TYPE_ITEMS, ROOT_NAME
from .interpolation import apply_interp
from .pose_utils import (
    load_json_poses, get_pose_record, pose_record_to_full_dict,
    list_json_files, _enum_json_files, _json_file_from_index,
    _enum_poses_from_self_json, get_root_rotation_from_record,
    get_root_transform_from_record,
    resolve_pose_start_frames,
)
from .eye_system import apply_blink_with_pupils, apply_blink_intervals_multi
from .config_ops import (
    _ser_throws, _load_throws,
    _ser_blink_intervals, _load_blink_intervals,
    _ser_organic, _load_organic,
    _SEGMENT_FILTER_FIELDS,
    _aplicar_parpadeo_default_seg,
)


# =============================================================================
# UTILIDADES INTERNAS
# =============================================================================

# PORTADO desde alfred_animation_studio (Kebyn, 2026-08-05): valores de
# "reglas_alfred.zip" para que los filtros organicos queden con un baseline
# ya afinado apenas se crea el primer segmento, en vez de que el usuario
# tenga que ir a tocar cada slider a mano. Los campos genericos (respiracion,
# sway de cabeza, weight_shift, root_noise, secondary_motion, smooth_curves,
# micro_scale, shoulder_noise) usan EXACTAMENTE los mismos valores que Alfred
# -- son parametros de post-proceso sobre fcurves ya keyframeadas, no
# dependen de que el rig sea bipedo o cuadrupedo. Los campos propios de Jerry
# (tail_wag, ear_osc, jaw_osc) usan los defaults ya declarados en
# JerryOrganicFilters (properties.py), que Kebyn afino especificamente para
# el rig de perro (ej. tail_wag_amplitude=0.524 rad = 30 grados de meneo).
#
# AISLAMIENTO POR SEGMENTO (Kebyn + Claude, 2026-08-06): "organic" ahora es
# un campo POR SEGMENTO (seg.organic), aislado entre segmentos, exactamente
# igual que en alfred_animation_studio (AlfredAnimSegment.organic, ver
# properties.py). Este baseline se aplica una vez POR SEGMENTO, justo
# despues de crearlo (idempotente: solo si ese segmento en particular
# todavia tiene "enabled" en False, no pisa ajustes que el usuario ya haya
# hecho a mano en ESE segmento).
_ORGANIC_DEFAULTS_REGLAS_JERRY = {
    "enabled":                  True,
    "breathing_enabled":        True,
    "breathing_amplitude":      0.05,
    "breathing_speed":          0.01,
    "breathing_phase":          0.0,
    "head_sway_enabled":        True,
    "head_sway_amplitude":      0.008,
    "head_sway_speed":          0.05,
    "head_sway_seed":           42,
    "weight_shift_enabled":     True,
    "weight_shift_amplitude":   0.005,
    "weight_shift_speed":       0.04,
    "root_noise_enabled":       False,
    "root_noise_strength":      0.003,
    "root_noise_frequency":     0.15,
    "root_noise_seed":          7,
    "secondary_motion_enabled": True,
    "secondary_motion_lag":     3.0,
    "secondary_motion_damping": 0.7,
    "smooth_curves_enabled":    True,
    "smooth_passes":            2,
    "smooth_factor":            0.5,
    "micro_scale_enabled":      True,
    "micro_scale_amplitude":    0.005,
    "shoulder_noise_enabled":   True,
    "shoulder_noise_amplitude": 0.006,
    "shoulder_noise_speed":     0.07,
    "shoulder_noise_seed":      123,
    "tail_wag_enabled":         True,
    "tail_wag_amplitude":       0.524,
    "tail_wag_speed":           0.12,
    "tail_wag_phase":           0.0,
    "tail_wag_lag":             0.35,
    # ear_osc_enabled / jaw_osc_enabled / emotion_enabled: reglas.zip
    # (jerry_template_1600.json) los marca como TRUE + "OBLIGATORIOS" para
    # los JSON generados por jerry_story_generator.py (deben traer minimo 1
    # item cada uno -- ver REGLA_FILTROS_ORGANICOS_OBLIGATORIOS en
    # jerry_filter.py). Esa regla es para el PIPELINE de historias con IA,
    # que arma esos items a partir de la historia (que orejas reaccionan,
    # que dice/ladra Jerry, que emocion tiene la ceja en cada momento) --
    # no hay un "item generico" razonable para poblar solo al tocar el
    # boton Agregar Segmento en el addon (una emocion por defecto, ej.
    # "enojado", quedaria mal aplicada a TODOS los segmentos nuevos). Se
    # dejan en False aca; si esta config se guarda/exporta hacia el
    # pipeline de reglas.zip, agregar los items a mano segun la historia.
    #
    # 2026-08-08 (Kebyn): orejas ahora se activa por defecto TAMBIEN al
    # crear el segmento en el addon, con un item generico ("Orejas
    # (default)", el mismo baseline que usa jerry_story_generator.py
    # cuando forzar_expresion no disparo nada organicamente -- ver
    # amplitude/speed/frame_end en JerryEarOscItem/ear_edit_* de
    # properties.py). jaw_osc_enabled y emotion_enabled se dejan en False
    # porque no tienen un "item generico" razonable (mandibula/cejas
    # dependen 100% de que dice/siente el personaje en ese segmento).
    "ear_osc_enabled":          True,
    "jaw_osc_enabled":          False,
    "emotion_enabled":          False,
}

# Item generico de orejas aplicado a seg.organic.ear_items cuando el
# segmento se crea y todavia no tiene ninguno (mismo baseline que
# "Orejas (default)" en jerry_story_generator.py). frame_start/frame_end
# son ABSOLUTOS -- ver _organic_item_range en operators_anim.py (Kebyn +
# Claude, 2026-08-24, segunda vuelta): se confirmo con una config real que
# Kebyn siempre tipea los numeros que ve en la linea de tiempo de Blender,
# asi que esta plantilla se ajusta por segmento a sus propios frame_start/
# frame_end absolutos en vez de arrancar en 1 (ver mas abajo).
_EAR_ITEM_DEFAULT_JERRY = {
    "label":       "Orejas (default)",
    "frame_start": 1,   # placeholder; se sobreescribe con seg.frame_start abajo
    "frame_end":   80,  # placeholder; se recorta a seg.frame_end abajo
    "amplitude":   0.12,
    "speed":       0.06,
    "phase_l":     0.0,
    "phase_r":     1.57,
    "axis":        "Z",
    "enabled":     True,
}


def _aplicar_defaults_organicos_jerry(context, seg=None):
    """Deja los filtros organicos de UN segmento (seg.organic) configurados
    con el baseline de _ORGANIC_DEFAULTS_REGLAS_JERRY (valores reales de
    reglas.zip / jerry_template_1600.json), SOLO si ese segmento en
    particular todavia no los activo a mano (idempotente — no pisa una
    configuracion ya en uso).

    AISLAMIENTO POR SEGMENTO (Kebyn + Claude, 2026-08-06): antes esta
    funcion escribia sobre scene.jerryst.organic -- una UNICA instancia
    global aplicada a TODOS los segmentos por igual, que es exactamente lo
    que causaba que "al cambiar un filtro organico en un segmento, se
    reprodujera en todos los demas al concatenar" (mismo bug que ya se
    habia corregido en Alfred el 2026-08-03). Ahora escribe exclusivamente
    sobre la copia PROPIA del segmento recibido en `seg`.

    `seg` es obligatorio en el uso normal (se llama una vez por segmento,
    justo despues de crearlo). Si no se recibe `seg` la funcion no hace
    nada (ya no existe un "default global" que aplicar).

    Cada segmento es independiente entre si: esta funcion se llama UNA VEZ
    por segmento (justo al crearlo) y escribe solo sobre `seg.organic`, asi
    que el item de orejas que arma (frame_end recortado a la duracion de
    ESE segmento en particular) nunca se comparte ni se pisa entre
    segmentos distintos."""
    if seg is None:
        return
    org = getattr(seg, "organic", None)
    if org is None or org.enabled:
        return
    for _attr, _val in _ORGANIC_DEFAULTS_REGLAS_JERRY.items():
        if hasattr(org, _attr):
            setattr(org, _attr, _val)
    # Orejas: ademas del flag ear_osc_enabled, la coleccion ear_items
    # necesita al menos 1 item para que la oscilacion realmente se vea
    # (el flag solo no alcanza -- ver _EAR_ITEM_DEFAULT_JERRY arriba).
    if hasattr(org, "ear_items") and len(org.ear_items) == 0:
        _it = org.ear_items.add()
        for _attr, _val in _EAR_ITEM_DEFAULT_JERRY.items():
            if hasattr(_it, _attr):
                setattr(_it, _attr, _val)
        # Ajustar frame_start/frame_end a los limites ABSOLUTOS reales de
        # ESTE segmento (Kebyn + Claude, 2026-08-24, segunda vuelta):
        # _organic_item_range ya no convierte relativo->absoluto, asi que
        # el item por defecto debe nacer con los frames absolutos propios
        # del segmento (su frame_start, y hasta 80 frames despues sin pasar
        # su frame_end) en vez de 1..80.
        _f_start = getattr(seg, "frame_start", None)
        _f_end = getattr(seg, "frame_end", None)
        if _f_start is not None and _f_end is not None:
            _f_start = int(_f_start)
            _f_end = int(_f_end)
            _it.frame_start = _f_start
            _it.frame_end = max(_f_start + 1, min(_f_start + 79, _f_end))


# NOTA (Kebyn, 2026-08-07): _aplicar_parpadeo_default_seg vivia aca antes;
# se movio a config_ops.py (se importa arriba) para poder reutilizarla
# tambien desde _load_segment() -- el loader de config completa / formato
# evolutivo que alimenta Paso 3 desde los .json de reglas.zip -- sin crear
# un import circular entre este archivo y config_ops.py.


def _sync_blink_sistema2_con_segmentos(context):
    """Mantiene el Sistema 2 de ojos (parpadeo sincronizado, GLOBAL a toda
    la escena -- ver JerryEyeExpressionSettings en properties.py) en sync
    con la cantidad de segmentos del Paso 3: UN parpadeo por segmento
    habilitado (Kebyn, 2026-08-07), y el rango [blink_frame_start,
    blink_frame_end] cubriendo desde el inicio del primer segmento hasta
    el fin del ultimo.

    A diferencia de _aplicar_parpadeo_default_seg (Sistema 1, por-segmento,
    idempotente), el Sistema 2 es UN UNICO valor global -- no hay "por
    segmento" que pisar -- asi que esta funcion simplemente recalcula
    blink_count/frame_start/frame_end cada vez que la lista de segmentos
    cambia (agregar/eliminar/duplicar/auto-split). Solo actua si el
    Sistema 2 (o AMBOS) esta seleccionado; si el usuario esta en Sistema 1
    puro no se toca nada."""
    segs = getattr(context.scene, "jerry_segs", None)
    if segs is None:
        return
    eye_s = getattr(segs, "eye_expr", None)
    if eye_s is None:
        return
    if eye_s.active_eye_system not in ("SISTEMA_2", "AMBOS"):
        return

    enabled = [s for s in segs.segments if s.enabled]
    if not enabled:
        return

    n = len(enabled)
    eye_s.blink_count = max(1, min(n, 20))   # clamp al IntProperty (min=1, max=20)
    eye_s.blink_frame_start = min(s.frame_start for s in enabled)
    eye_s.blink_frame_end   = max(s.frame_end for s in enabled)


def _recolectar_parpadeos_segmento(seg, f_s, f_e, sink):
    """Agrega a `sink` (lista de tuplas start,end,count,duration) los
    intervalos de parpadeo HABILITADOS de un segmento, recortados al rango
    REAL [f_s, f_e] que ese segmento termino ocupando al concatenar (que
    puede diferir del frame_start/frame_end guardados en el intervalo si el
    segmento es de 1-coordenada, cuyo largo real solo se conoce en este
    punto -- ver _calc_seg_frames).

    Este es el consumidor real de seg.blink_intervals (Kebyn + Claude,
    2026-08-07): antes de esto, "Parpadeo automatico (por segmento)" se
    guardaba/cargaba/mostraba en el panel pero NINGUN codigo lo convertia
    en keyframes -- por eso no se reproducia ningun parpadeo aunque cada
    segmento ya tuviera como minimo un intervalo configurado. Ver
    JRRSTSEG_OT_ConcatenateAll, que llama a esta funcion por cada segmento
    y despues renderiza todo junto con apply_blink_intervals_multi."""
    if f_e <= f_s:
        return
    for bi in seg.blink_intervals:
        if not bi.enabled:
            continue
        bs = max(f_s, min(bi.frame_start, f_e))
        be = max(f_s, min(bi.frame_end,   f_e))
        if be <= bs:
            be = min(f_e, bs + max(bi.blink_duration, 6))
        if be <= bs:
            continue
        sink.append((bs, be, max(1, bi.blink_count), bi.blink_duration))


def _load_pose_from_file(filepath, poses_dir):
    """Carga un .json de pose y devuelve el dict completo de bones."""
    path = bpy.path.abspath(filepath)
    if not os.path.isfile(path):
        # intentar relativo a poses_dir
        candidate = os.path.join(bpy.path.abspath(poses_dir), os.path.basename(filepath))
        if os.path.isfile(candidate):
            path = candidate
        else:
            return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Puede ser un dict directo {bone: {rot,loc,scale}} o un wrapper
        if isinstance(data, dict):
            # Si tiene la clave "bones" es un wrapper
            if "bones" in data:
                return data["bones"]
            # Si tiene la clave "poses" (lista) tomar la primera
            if "poses" in data:
                poses = data["poses"]
                if poses:
                    return poses[0].get("bones", poses[0])
            # Si las claves son nombres de bones directamente
            return data
    except Exception as e:
        print(f"[JRRSTSeg] Error cargando pose '{path}': {e}")
    return None


def _get_bone_value(pose_dict, bone_name, channel):
    """Extrae (rx,ry,rz) o (lx,ly,lz) o (sx,sy,sz) de un dict de pose."""
    default = _BONE_DEFAULT
    if pose_dict is None:
        d = default
    else:
        # Buscar por nombre exacto o por alias sin sufijo _jerry
        d = pose_dict.get(bone_name, None)
        if d is None:
            short = bone_name.replace("_jerry", "")
            d = pose_dict.get(short, default)
    if isinstance(d, dict):
        val = d.get(channel, default[channel])
    else:
        val = default[channel]
    if isinstance(val, (list, tuple)):
        return tuple(val)
    return (0.0, 0.0, 0.0)


def _lerp3(a, b, t):
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


def _calc_seg_frames(seg):
    """
    Calcula la duracion total de un segmento sumando la duracion de cada
    Accion (slot) configurada en seg.action_poses.

    NOTA (Kebyn, 2026-08-06): antes sumaba tambien pose_start_duration /
    pose_end_duration (bookends de "Pose INICIO"/"Pose FIN" por-segmento) --
    ese sistema se elimino por ser logica de versiones antiguas. Ahora la
    duracion total del segmento es simplemente la suma de sus Acciones.

    Devuelve (total_frames, frame_end_calculado).
    Funciona antes de CONCATENAR — no requiere que frame_end_auto este seteado.
    Util para mostrar la duracion en tiempo real en el header del segmento
    y para que el botón Play sepa hasta que frame reproducir.
    """
    total = 0
    for ap in seg.action_poses:
        total += ap.duration
    total = max(total, 1)
    return total, seg.frame_start + total - 1


def _interpolate_pose_value(pose_start, pose_mid, pose_end,
                             t_global, bone_name, channel,
                             interp_start, interp_mid_end):
    """
    Interpola el valor de un canal (rot/loc/scale) de un bone entre las tres poses.
    t_global: [0, 1] a lo largo del segmento completo.
    Si pose_mid existe: t<0.5 interpola start->mid, t>=0.5 interpola mid->end.
    """
    val_s = _get_bone_value(pose_start, bone_name, channel)
    val_e = _get_bone_value(pose_end,   bone_name, channel)

    if pose_mid is not None:
        val_m = _get_bone_value(pose_mid, bone_name, channel)
        if t_global < 0.5:
            t_local = t_global * 2.0
            t_curved = apply_interp(t_local, interp_start)
            return _lerp3(val_s, val_m, t_curved)
        else:
            t_local = (t_global - 0.5) * 2.0
            t_curved = apply_interp(t_local, interp_mid_end)
            return _lerp3(val_m, val_e, t_curved)
    else:
        t_curved = apply_interp(t_global, interp_start)
        return _lerp3(val_s, val_e, t_curved)


def _blend_alpha(t_global, total_frames, blend_in_frames, blend_out_frames, blend_strength):
    """
    Calcula el factor de mezcla (0..1) en un frame dado.
    blend_in_frames:  frames de fade-in desde 0 hasta 1.
    blend_out_frames: frames de fade-out desde 1 hasta 0.
    blend_strength:   escala global del blend.
    """
    frame_idx = t_global * total_frames  # frame relativo flotante

    alpha = 1.0
    if blend_in_frames > 0 and frame_idx < blend_in_frames:
        alpha = min(frame_idx / blend_in_frames, 1.0)
        # smoothstep
        alpha = alpha * alpha * (3 - 2 * alpha)

    frames_from_end = total_frames - frame_idx
    if blend_out_frames > 0 and frames_from_end < blend_out_frames:
        alpha_out = min(frames_from_end / blend_out_frames, 1.0)
        alpha_out = alpha_out * alpha_out * (3 - 2 * alpha_out)
        alpha = min(alpha, alpha_out)

    return alpha * blend_strength


def _get_or_create_fcurve(action, data_path, index):
    """Obtiene o crea un fcurve en la action dada."""
    fc = _get_action_fcurves(action).find(data_path, index=index)
    if fc is None:
        fc = _get_action_fcurves(action).new(data_path=data_path, index=index)
    return fc


def _get_fcurve_value_at(action, data_path, index, frame):
    """Evalua un fcurve en un frame dado. Devuelve 0.0 si no existe."""
    fc = _get_action_fcurves(action).find(data_path, index=index)
    if fc is None:
        return 0.0
    return fc.evaluate(frame)


def _set_keyframe(action, data_path, index, frame, value):
    """Inserta o actualiza un keyframe en un fcurve."""
    fc = _get_or_create_fcurve(action, data_path, index)
    # Buscar si ya existe keyframe en ese frame
    for kp in fc.keyframe_points:
        if abs(kp.co.x - frame) < 0.5:
            kp.co.y = value
            fc.update()
            return
    fc.keyframe_points.insert(frame=frame, value=value, options={"FAST"})
    fc.update()


def _resolve_armature(seg_cfg, scene):
    """Devuelve el objeto armature principal."""
    arm = scene.objects.get(seg_cfg.armature_name)
    if arm and arm.type == "ARMATURE":
        return arm
    # Fallback
    arm = scene.objects.get("Dog_001_rig")
    if arm and arm.type == "ARMATURE":
        return arm
    return None


def _resolve_secondary(bone_name, scene):
    """Para bones de armatures secundarios (shield/spear), devuelve el objeto."""
    for sec_name in SECONDARY_ARMATURES:
        obj = scene.objects.get(sec_name)
        if obj and obj.type == "ARMATURE":
            if obj.pose.bones.get(bone_name):
                return obj
    return None


# Mapa de nombre de bone a bones del segmento (affect_*)
# Solo para compatibilidad con código antiguo — ya no se usa en CONCATENAR
_BONE_AFFECT_MAP = {
    "spine_1":          "affect_body",
    "front_shoulder.L": "affect_left_arm",
    "front_shoulder.R": "affect_right_arm",
    "shoulder.L":       "affect_left_leg",
    "shoulder.R":       "affect_right_leg",
    "Dog_001_rig":      "affect_root",
    "tail_1":           "affect_shield",
    "tail_2":           "affect_spear",
}

# Mapa granular: nombre de bone → propiedad filter_* del segmento
# Si filter_* es True el bone está FILTRADO (excluido de las poses)
_BONE_FILTER_MAP = {
    # Columna vertebral
    "spine_1":           "filter_body",
    "spine_2":           "filter_spine_2",
    "spine_3":           "filter_spine_3",
    "spine_4":           "filter_spine_4",
    "spine_5":           "filter_spine_5",
    "spine_6":           "filter_spine_6",
    "spine_7":           "filter_spine_7",
    # En este rig, Dog_001_rig es el bone raíz que aparece en la lista de UI.
    "Dog_001_rig":       "filter_main_bone",
    # Patas delanteras izquierda
    "front_shoulder.L":  "filter_left_arm",
    "front_thigh.L":     "filter_front_thigh_l",
    "front_shin.L":      "filter_front_shin_l",
    "front_foot.L":      "filter_front_foot_l",
    "front_toe.L":       "filter_front_toe_l",
    # Patas delanteras derecha
    "front_shoulder.R":  "filter_right_arm",
    "front_thigh.R":     "filter_front_thigh_r",
    "front_shin.R":      "filter_front_shin_r",
    "front_foot.R":      "filter_front_foot_r",
    "front_toe.R":       "filter_front_toe_r",
    # Patas traseras izquierda
    "shoulder.L":        "filter_left_leg",
    "thigh.L":           "filter_thigh_l",
    "shin.L":            "filter_shin_l",
    "foot.L":            "filter_foot_l",
    "toe.L":             "filter_toe_l",
    # Patas traseras derecha
    "shoulder.R":        "filter_right_leg",
    "thigh.R":           "filter_thigh_r",
    "shin.R":            "filter_shin_r",
    "foot.R":            "filter_foot_r",
    "toe.R":             "filter_toe_r",
    # Cola
    "tail_1":            "filter_shield",
    "tail_2":            "filter_spear",
    "tail_3":            "filter_tail_3",
    # Cabeza
    "scull":             "filter_scull",
    "scull_1":           "filter_scull_1",
    "jaw_top":           "filter_jaw_top",
    "jaw_bot":           "filter_jaw_bot",
    "ear.L":             "filter_ear_l",
    "ear.R":             "filter_ear_r",
    "sombrero":          "filter_sombrero",
    # Cejas
    "sejas_1_jerry":     "filter_sejas_1",
    "sejas_2_jerry":     "filter_sejas_2",
}


def _get_bone_block_entry(seg, bone_key, create=False):
    """PORTADO desde alfred_animation_studio (Kebyn, 2026-08-08): ubica (o
    crea) el JerryBoneBlockEntry de un bone dentro de un segmento."""
    for entry in seg.bone_blocks:
        if entry.bone_key == bone_key:
            return entry
    if create:
        entry = seg.bone_blocks.add()
        entry.bone_key = bone_key
        return entry
    return None


def _bone_blocked_in_intervals(seg, bone_name, frame):
    """PORTADO desde alfred_animation_studio (Kebyn, 2026-08-08): True si
    'frame' cae dentro de algun intervalo de bloqueo definido para este
    bone (ademas del checkbox simple que bloquea todo el segmento)."""
    filter_attr = _BONE_FILTER_MAP.get(bone_name)
    if filter_attr is None:
        return False
    entry = _get_bone_block_entry(seg, filter_attr, create=False)
    if entry is None:
        return False
    for iv in entry.intervals:
        if iv.enabled and iv.frame_start <= frame <= iv.frame_end:
            return True
    return False


def _bone_is_filtered(seg, bone_name, frame=None):
    """Retorna True si el bone está FILTRADO y conserva la animación base.

    ``filter_show`` solo controla si el panel se despliega; no debe cambiar el
    comportamiento del filtro. Así, una selección guardada se respeta aunque
    el usuario cierre el panel antes de CONCATENAR.

    PORTADO desde alfred_animation_studio (Kebyn, 2026-08-08): ademas del
    checkbox simple (bloqueo de TODO el segmento), un bone puede tener
    intervalos de frames especificos ("dividir en partes" el bloqueo, ver
    JerryBoneBlockEntry). Si se pasa 'frame', tambien se consulta esos
    intervalos; si no se pasa, el comportamiento es identico al anterior
    (solo el checkbox simple).
    """
    filter_attr = _BONE_FILTER_MAP.get(bone_name)
    if filter_attr is None:
        return False  # bone sin mapeo → no filtrado
    if bool(getattr(seg, filter_attr, False)):
        return True
    if frame is not None and _bone_blocked_in_intervals(seg, bone_name, frame):
        return True
    return False


def _apply_default_bone_filters(seg):
    """Selecciona por defecto root y todos los huesos de las cuatro patas."""
    defaults = (
        "filter_main_bone",
        "filter_left_arm", "filter_right_arm",
        "filter_front_thigh_l", "filter_front_thigh_r",
        "filter_front_shin_l", "filter_front_shin_r",
        "filter_front_foot_l", "filter_front_foot_r",
        "filter_front_toe_l", "filter_front_toe_r",
        "filter_left_leg", "filter_right_leg",
        "filter_thigh_l", "filter_thigh_r",
        "filter_shin_l", "filter_shin_r",
        "filter_foot_l", "filter_foot_r",
        "filter_toe_l", "filter_toe_r",
    )
    for attr in defaults:
        if hasattr(seg, attr):
            setattr(seg, attr, True)


# =============================================================================
# JRRSTSEG_OT_Apply fue ELIMINADO (Kebyn, 2026-08-06): codigo muerto, no
# enganchado a ningun panel/boton, y referenciaba seg.pose_start_file/
# pose_start_duration/pose_end_file/pose_end_duration/pose_mid_file -- todos
# atributos ya removidos de JerryAnimSegment (ver refactor pose_inicio/
# pose_fin -> action_poses). Invocarlo (bpy.ops.jerryseg.apply) hubiera
# lanzado AttributeError de inmediato. El flujo real y soportado es
# jerryst.concatenate (operators_anim.py) por segmento activo, o
# jerryseg.concatenate_all para todos los segmentos.
# =============================================================================


# =============================================================================
# CRUD DE SEGMENTOS
# =============================================================================

# =============================================================================
# OBSOLETO (Kebyn, 2026-08-07): _empty_world_to_root_bone_basis() quedo
# reemplazada por keyframes constantes en 0,0,0. Se deja documentado el
# razonamiento erroneo para que no se reintroduzca el bug:
#
# La funcion intentaba despejar matrix_basis para que spine_6 "terminara" en
# empty_matrix_world:
#     matrix_basis = bone.matrix_local.inverted()
#                    @ arm_obj.matrix_world.inverted()
#                    @ empty_matrix_world
# El error estaba en el planteo, no en el algebra: arm_obj (Dog_001_rig) esta
# parentado al Empty "jerry" con transform local (0,0,0), por lo que
# arm_obj.matrix_world YA hereda el 100% del recorrido automaticamente via el
# parenting de Blender -- sin que spine_6 tenga que compensar nada. Forzar
# ademas que spine_6 "llegue" a empty_matrix_world reintroducia el
# desplazamiento una segunda vez (uno por el parent, otro por las fcurves del
# hueso), lo cual se manifestaba como una rotacion residual espuria
# (ej. el -38.529 en spine_6.rotation_euler.x que en realidad es la inversa
# de la orientacion de rest del hueso, no un valor real de movimiento).
#
# El valor correcto de spine_6 (bone raiz de Jerry) es CONSTANTE 0,0,0 en
# location y 0,0,0 en rotation_euler durante todo el segmento -- no depende
# del recorrido, del Empty, ni de ninguna conversion de matrices.
# =============================================================================


class JRRSTSEG_OT_Add(Operator):
    bl_idname  = "jerryseg.add"
    bl_label   = "Agregar segmento"
    bl_description = "Agrega un nuevo segmento de refinado al Paso 3"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        segs = context.scene.jerry_segs
        pc   = context.scene.jerry_path

        # Validar rango de la animacion
        f_inicio = pc.frame_inicio
        f_fin    = pc.anim_frame_fin
        n_pts    = len(pc.path_points)

        # ── Modo 1 coordenada ─────────────────────────────────────────────────
        # Con una sola coordenada no hay recorrido calculado, por lo que
        # frame_end es INDETERMINADO en el momento de crear el segmento.
        # Se crea el segmento con frame_end = frame_start (provisional) y
        # single_coord_mode = True; el frame_end real se calculara al CONCATENAR
        # como la suma de duraciones de todas las poses + filtros.
        _single_coord = n_pts <= 1

        if _single_coord:
            # En modo 1 coordenada, el frame inicio se extrae DIRECTAMENTE
            # de pc.frame_inicio (el valor que el usuario fijo en el Paso 1).
            # El usuario no puede ni debe modificarlo en el Paso 3.
            fs = f_inicio   # <- Paso 1: frame_inicio
            fe = fs         # provisional; se calculara al CONCATENAR
            # Sin validacion de solapamiento por frame_end (es provisional),
            # pero si verificar que no haya un segmento 1-coord duplicado.
            for i, s in enumerate(segs.segments):
                if not s.enabled:
                    continue
                if s.single_coord_mode and s.frame_start == fs:
                    self.report({"ERROR"},
                        f"Ya existe un segmento 1-coord iniciando en el frame {fs} "
                        f"(segmento [{i+1}]: {s.label}). "
                        "Cambia el frame inicio en el Paso 1 antes de crear otro.")
                    return {"CANCELLED"}
        else:
            # ── Modo multi-coordenada: comportamiento original ─────────────────
            if n_pts <= 1 and f_fin <= f_inicio:
                f_fin = pc.frame_fin_manual
                pc.anim_frame_fin = f_fin
            fs = segs.edit_frame_start
            fe = segs.edit_frame_end

            if f_fin <= f_inicio:
                self.report({"ERROR"}, "Configura el recorrido (Paso 2) antes de crear segmentos")
                return {"CANCELLED"}
            if not (f_inicio <= fs <= f_fin):
                self.report({"ERROR"}, f"Frame inicio {fs} fuera del rango [{f_inicio}, {f_fin}]")
                return {"CANCELLED"}
            if not (f_inicio <= fe <= f_fin) or fe <= fs:
                self.report({"ERROR"}, f"Frame fin {fe} invalido (debe ser > {fs} y <= {f_fin})")
                return {"CANCELLED"}

            for i, s in enumerate(segs.segments):
                if not s.enabled:
                    continue
                if fs <= s.frame_end and fe >= s.frame_start:
                    self.report({"ERROR"},
                        f"Solapamiento con segmento [{i+1}] ({s.frame_start}→{s.frame_end})")
                    return {"CANCELLED"}

        seg = segs.segments.add()
        seg.label            = segs.edit_label or f"Segmento {len(segs.segments)}"
        seg.frame_start      = fs
        seg.frame_end        = fe
        seg.single_coord_mode = _single_coord
        seg.frame_end_auto   = 0  # sin calcular todavia

        # ── Modo recorrido: crear action dedicada con solo el desplazamiento ──
        # El desplazamiento del personaje vive en el Empty "jerry"
        # (NLA tracks Slot_*_root generados por path_recorder).
        # Se evalua el Empty frame a frame para capturar location y rotation
        # ya resueltos por el NLA, y se guardan en la seg_action del armature
        # como fcurves de pose.bones["Dog_001_rig"].location/rotation.
        # Los bones de animacion base (caminar/saltar) NO se copian aqui;
        # se inyectaran en REPRODUCIR para los bones no afectados por la config.
        if not _single_coord:
            arm_name = segs.armature_name or "Dog_001_rig"
            arm_obj  = context.scene.objects.get(arm_name)
            root_empty = context.scene.objects.get("jerry")

            seg_action_name = f"jerryseg_{seg.label.replace(' ','_')}"
            old_act = bpy.data.actions.get(seg_action_name)
            if old_act:
                bpy.data.actions.remove(old_act, do_unlink=True)
            seg_action = bpy.data.actions.new(name=seg_action_name)
            seg.seg_action_name = seg_action_name

            if root_empty and root_empty.animation_data:
                # Asegurar que el armature no tenga action directa activa
                # (interferiria con la evaluacion del NLA del root)
                _prev_arm_action = None
                if arm_obj and arm_obj.animation_data and arm_obj.animation_data.action:
                    _prev_arm_action = arm_obj.animation_data.action
                    arm_obj.animation_data.action = None

                # spine_6 es el bone raiz del rig Jerry (Dog_001_rig es el objeto, no un bone)
                _root_bone_name = 'spine_6'
                dp_loc = f'pose.bones["{_root_bone_name}"].location'
                dp_rot = f'pose.bones["{_root_bone_name}"].rotation_euler'

                # Dog_001_rig esta parentado al Empty "jerry" con transform local
                # (0,0,0): el armature ya hereda el 100% del desplazamiento del
                # recorrido automaticamente via el parent de Blender. spine_6
                # (bone raiz) no compensa nada -- su valor correcto es
                # CONSTANTE 0,0,0 / 0,0,0 en todo el rango del segmento (no se
                # evalua el Empty ni se convierten matrices; ver nota
                # "OBSOLETO" mas arriba para el detalle del bug anterior).
                fc_loc = [_get_action_fcurves(seg_action).new(dp_loc, index=i) for i in range(3)]
                fc_rot = [_get_action_fcurves(seg_action).new(dp_rot, index=i) for i in range(3)]
                for fc in fc_loc + fc_rot:
                    for _f in (fs, fe):
                        kp = fc.keyframe_points.insert(frame=_f, value=0.0, options={"FAST"})
                        kp.interpolation = "BEZIER"
                        kp.easing = "AUTO"
                    fc.update()

                # Restaurar action previa del armature si existia
                if arm_obj and _prev_arm_action:
                    arm_obj.animation_data.action = _prev_arm_action

            # Asignar la seg_action como action activa del armature
            if arm_obj:
                if not arm_obj.animation_data:
                    arm_obj.animation_data_create()
                arm_obj.animation_data.action = seg_action

        # Copiar configuracion completa desde jerryst (el sistema de poses actual)
        st = context.scene.jerryst
        # NOTA (Kebyn, 2026-08-06): ya no se copian pose_start_*/pose_end_* --
        # ese sistema de bookends por-segmento fue eliminado (logica antigua).
        # Parametros globales
        seg.fps         = st.fps
        seg.entry_ratio = st.entry_ratio
        seg.exit_ratio  = st.exit_ratio
        seg.export_slot_number = st.export_slot_number
        seg.export_type        = st.export_type
        seg.export_desc        = st.export_desc
        # Copiar action_poses
        seg.action_poses.clear()
        for src_slot in st.action_poses:
            dst_slot = seg.action_poses.add()
            dst_slot.json_file   = src_slot.json_file
            dst_slot.pose_label  = src_slot.pose_label
            dst_slot.pose_name   = src_slot.pose_name
            dst_slot.duration    = src_slot.duration
            dst_slot.entry_ratio = src_slot.entry_ratio
            dst_slot.exit_ratio  = src_slot.exit_ratio
            dst_slot.interp_type = src_slot.interp_type
            dst_slot.rot_x = src_slot.rot_x
            dst_slot.rot_y = src_slot.rot_y
            dst_slot.rot_z = src_slot.rot_z
            dst_slot.pos_x = src_slot.pos_x
            dst_slot.pos_y = src_slot.pos_y
            dst_slot.pos_z = src_slot.pos_z
        # Legacy modulator
        seg.frame_mid        = segs.edit_frame_mid if segs.edit_use_mid else 0
        seg.pose_mid_file    = segs.edit_pose_mid_file
        seg.pose_mid_label   = segs.edit_pose_mid_label
        seg.interp_type      = segs.edit_interp
        if segs.edit_use_mid:
            seg.interp_mid_to_end = segs.edit_interp_mid
        seg.blend_in_frames  = segs.edit_start_frames
        seg.blend_out_frames = segs.edit_end_frames
        seg.enabled          = True
        seg.show_config      = True   # La config se despliega automaticamente al crear el segmento
        seg.blend_strength   = 1.0
        seg.affect_body      = True
        seg.affect_left_arm  = True
        seg.affect_right_arm = True
        seg.affect_left_leg  = True
        seg.affect_right_leg = True
        # Root y extremidades continúan con la animación base por defecto.
        _apply_default_bone_filters(seg)
        segs.active_index = len(segs.segments) - 1

        # PORTADO desde alfred_animation_studio (Kebyn, 2026-08-05): antes
        # los filtros organicos (scene.jerryst.organic, global) quedaban en
        # su default de fabrica ("Activar filtros organicos" = False), asi
        # que aunque el usuario creara segmentos el personaje nunca
        # respiraba, ni tenia sway de cabeza, ni meneo de cola, hasta que
        # alguien entraba manualmente al panel de Filtros Organicos y
        # prendia todo a mano. Ahora, al crear un segmento, se aplica el
        # baseline real de reglas.zip (_ORGANIC_DEFAULTS_REGLAS_JERRY) sobre
        # la copia PROPIA de ESTE segmento (aislamiento por segmento,
        # 2026-08-06 -- no pisa nada si el usuario ya los activo/ajusto en
        # este segmento en particular), y ademas se deja "un parpadeo por
        # segmento" configurado en este segmento.
        _aplicar_defaults_organicos_jerry(context, seg)
        _aplicar_parpadeo_default_seg(seg)
        _sync_blink_sistema2_con_segmentos(context)

        # Preparar el formulario para el siguiente segmento
        segs.edit_label = f"Segmento {len(segs.segments) + 1}"
        if _single_coord:
            # En modo 1 coord frame_end se calcula al CONCATENAR;
            # el siguiente frame de inicio queda como sugerencia para el usuario.
            segs.edit_frame_start = fs
            self.report({"INFO"},
                f"Segmento '{seg.label}' creado en modo 1 coordenada. "
                f"Frame inicio: {fs}. Frame fin se calculara al CONCATENAR.")
        else:
            segs.edit_frame_start = fe + 1
            segs.edit_frame_end   = min(fe + 1 + (fe - fs), f_fin)
            self.report({"INFO"}, f"Segmento creado: {seg.label}  {fs}→{fe}  ({fe-fs}f)")
        return {"FINISHED"}


class JRRSTSEG_OT_Remove(Operator):
    bl_idname  = "jerryseg.remove"
    bl_label   = "Eliminar segmento"
    bl_description = "Elimina el segmento activo"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.jerry_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if 0 <= idx < len(segs.segments):
            segs.segments.remove(idx)
            segs.active_index = max(0, idx - 1)
            _sync_blink_sistema2_con_segmentos(context)
            self.report({"INFO"}, "Segmento eliminado")
        else:
            self.report({"WARNING"}, "No hay segmento seleccionado")
        return {"FINISHED"}


class JRRSTSEG_OT_Move(Operator):
    bl_idname  = "jerryseg.move"
    bl_label   = "Mover segmento"
    bl_description = "Sube o baja el segmento activo en la lista"
    bl_options = {"REGISTER", "UNDO"}

    direction: EnumProperty(items=[("UP", "Arriba", ""), ("DOWN", "Abajo", "")])

    def execute(self, context):
        segs = context.scene.jerry_segs
        idx  = segs.active_index
        n    = len(segs.segments)
        if self.direction == "UP" and idx > 0:
            segs.segments.move(idx, idx - 1)
            segs.active_index = idx - 1
        elif self.direction == "DOWN" and idx < n - 1:
            segs.segments.move(idx, idx + 1)
            segs.active_index = idx + 1
        return {"FINISHED"}


class JRRSTSEG_OT_Duplicate(Operator):
    bl_idname  = "jerryseg.duplicate"
    bl_label   = "Duplicar segmento"
    bl_description = "Duplica el segmento activo"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.jerry_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "No hay segmento seleccionado")
            return {"CANCELLED"}
        src = segs.segments[idx]
        dst = segs.segments.add()
        # Copiar atributos escalares
        # NOTA (Kebyn, 2026-08-06): se quitaron las claves fantasma
        # "pose_start_*"/"pose_end_*" (seg ya no tiene esos atributos --
        # el primer/ultimo item de action_poses son ahora las anclas) y se
        # agregaron las 44 flags "filter_*" que antes NO se duplicaban
        # (un segmento duplicado perdia los bones bloqueados del original).
        scalar_attrs = (
            "label","frame_start","frame_end","frame_mid",
            "single_coord_mode","frame_end_auto",
            "fps","entry_ratio","exit_ratio",
            "export_slot_number","export_type","export_desc",
            "pose_mid_file","pose_mid_label",
            "interp_type","interp_mid_to_end",
            "blend_in_frames","blend_out_frames","blend_strength",
            "affect_body","affect_left_arm","affect_right_arm",
            "affect_left_leg","affect_right_leg","affect_root",
            "affect_shield","affect_spear","enabled",
        ) + tuple(_SEGMENT_FILTER_FIELDS)
        for attr in scalar_attrs:
            try:
                setattr(dst, attr, getattr(src, attr))
            except Exception:
                pass
        # Copiar action_poses
        dst.action_poses.clear()
        slot_attrs = ("json_file","pose_label","pose_name","duration",
                      "entry_ratio","exit_ratio","interp_type",
                      "rot_x","rot_y","rot_z","pos_x","pos_y","pos_z")
        for src_slot in src.action_poses:
            dst_slot = dst.action_poses.add()
            for a in slot_attrs:
                try:
                    setattr(dst_slot, a, getattr(src_slot, a))
                except Exception:
                    pass
        # Copiar parpadeo, filtros organicos (aislados por segmento) y
        # lanzar/recoger (antes tampoco se duplicaban)
        _load_blink_intervals(dst.blink_intervals, _ser_blink_intervals(src.blink_intervals))
        _load_organic(dst.organic, _ser_organic(src.organic))
        _load_throws(dst.throws, _ser_throws(src.throws))
        dst.label = src.label + " (copia)"
        segs.active_index = len(segs.segments) - 1
        _sync_blink_sistema2_con_segmentos(context)
        return {"FINISHED"}


class JRRSTSEG_OT_AutoSplitFromConfig(Operator):
    """
    PORTADO desde alfred_animation_studio (ALFREDSEG_OT_AutoSplitFromConfig),
    2026-08-06: en vez de que todos los tramos del recorrido (caminar/
    saltar_subir/saltar_bajar/parada) terminen acumulados en un solo
    JerryAnimSegment gigante, este operador crea UN JerryAnimSegment por
    cada tramo detectado, con frame_start/frame_end calculados acumulando
    "frames_estimados" de calcular_estimacion_geometrica() (path_recorder.py)
    a partir de scene.jerry_path.frame_inicio -- el mismo orden y las mismas
    duraciones que ya se preveian en el panel bajo "Estimacion de slots".

    Cada segmento nuevo queda:
      - label:  "{indice:02d}_{tipo}" -- ej. "04_parada", "06_caminar".
      - frame_start / frame_end: acumulados desde la estimacion.
      - single_coord_mode = False (modo recorrido).
      - seg_action dedicada, generada igual que JRRSTSEG_OT_Add: se evalua
        el Empty "jerry" frame a frame dentro de [frame_start, frame_end]
        para capturar el desplazamiento puro del root ya resuelto por el NLA.
      - Poses (action_poses) quedan en blanco: cada tramo se configura
        despues individualmente en el Paso 3.
      - Patas traseras (filter_left_leg/filter_right_leg) bloqueadas SOLO en
        tramos "caminar" (el recorrido base ya las anima); en "parada" y
        "saltar_*" quedan libres para que la pose del segmento controle el
        cuerpo por completo. El root (filter_main_bone) se mantiene
        bloqueado siempre: su desplazamiento lo controla unicamente el
        Empty "jerry" capturado arriba.
    """
    bl_idname  = "jerryseg.autosplit_from_config"
    bl_label   = "Dividir segmentos"
    bl_description = (
        "Crea un segmento independiente por cada tramo (caminar/saltar_subir/"
        "saltar_bajar/parada) segun la 'Estimacion de slots' del recorrido "
        "grabado, en vez de un unico segmento que cubre todo el recorrido"
    )
    bl_options = {"REGISTER", "UNDO"}

    reemplazar_existentes: bpy.props.BoolProperty(
        name="Reemplazar segmentos existentes",
        description="Si esta activo, borra todos los segmentos actuales antes de crear los nuevos",
        default=True,
        options={"SKIP_SAVE"},
    )

    def execute(self, context):
        scene = context.scene
        pc = getattr(scene, "jerry_path", None)
        if pc is None:
            self.report({"ERROR"}, "No se encontro el recorrido (scene.jerry_path).")
            return {"CANCELLED"}

        from .path_recorder import calcular_estimacion_geometrica
        slots_est = calcular_estimacion_geometrica(scene)
        if not slots_est:
            self.report({"ERROR"},
                "No hay 'Estimacion de slots' para dividir. Graba primero "
                "un recorrido de 2+ puntos en el Paso 1 (o carga una "
                "configuracion con recorrido) para que aparezca la lista "
                "en el panel.")
            return {"CANCELLED"}

        base_frame = pc.frame_inicio if pc.frame_inicio else 1
        tramos = []
        cursor = base_frame
        for s in slots_est:
            dur = max(1, int(s["frames_estimados"]))
            fs = cursor
            fe = fs + dur - 1
            tramos.append({"tipo": s["tipo"], "frame_start": fs, "frame_end": fe})
            cursor = fe + 1

        segs = context.scene.jerry_segs

        if self.reemplazar_existentes:
            for old_seg in segs.segments:
                if old_seg.seg_action_name:
                    old_act = bpy.data.actions.get(old_seg.seg_action_name)
                    if old_act:
                        bpy.data.actions.remove(old_act, do_unlink=True)
            segs.segments.clear()

        arm_obj = _resolve_armature(segs, scene)
        if arm_obj is None:
            arm_name = segs.armature_name or "Dog_001_rig"
            self.report({"ERROR"},
                f"No se encontro el armature '{arm_name}'. Verifica "
                "'Nombre armature' en la config del Paso 3.")
            return {"CANCELLED"}

        root_empty = scene.objects.get("jerry")
        if root_empty is None or not root_empty.animation_data:
            self.report({"WARNING"},
                "No se encontro el Empty 'jerry' con animation_data (recorrido "
                "de Pasos 1+2). Los segmentos se crearan con frame_start/"
                "frame_end correctos pero SIN captura de desplazamiento del "
                "root; genera primero el recorrido con path_recorder.")

        # 'spine_6' es el bone raiz del rig cuadrupedo de Jerry (Dog_001_rig
        # es el objeto armature, no un bone -- ver JRRSTSEG_OT_Add mas arriba).
        _root_bone_name = "spine_6"
        if arm_obj.pose.bones.get(_root_bone_name) is None:
            _root_bone_name = None
            for pb in arm_obj.pose.bones:
                if pb.parent is None:
                    _root_bone_name = pb.name
                    break
        if _root_bone_name is None:
            self.report({"ERROR"},
                f"No se pudo determinar el bone raiz de '{arm_obj.name}' "
                "(no se encontro 'spine_6' ni ningun bone sin padre).")
            return {"CANCELLED"}

        st = context.scene.jerryst
        creados = 0
        errores = []

        _prev_arm_action = None
        if arm_obj.animation_data and arm_obj.animation_data.action:
            _prev_arm_action = arm_obj.animation_data.action

        frame_backup = scene.frame_current

        for i, tramo in enumerate(tramos, start=1):
            try:
                tipo = tramo.get("tipo", "desconocido")
                fs   = int(tramo.get("frame_start", 0))
                fe   = int(tramo.get("frame_end", 0))
                if fe <= fs:
                    errores.append(f"Tramo {i} ({tipo}): frame_end <= frame_start, omitido")
                    continue

                label = f"{i:02d}_{tipo}"

                seg = segs.segments.add()
                seg.label = label
                seg.frame_start = fs
                seg.frame_end = fe
                seg.single_coord_mode = False
                seg.frame_end_auto = 0

                seg_action_name = f"jerryseg_{label}"[:63]
                old_act = bpy.data.actions.get(seg_action_name)
                if old_act:
                    bpy.data.actions.remove(old_act, do_unlink=True)
                seg_action = bpy.data.actions.new(name=seg_action_name)
                seg.seg_action_name = seg_action_name

                if root_empty and root_empty.animation_data:
                    if arm_obj.animation_data:
                        arm_obj.animation_data.action = None

                    dp_loc = f'pose.bones["{_root_bone_name}"].location'
                    dp_rot = f'pose.bones["{_root_bone_name}"].rotation_euler'
                    fc_loc = [_get_action_fcurves(seg_action).new(dp_loc, index=k) for k in range(3)]
                    fc_rot = [_get_action_fcurves(seg_action).new(dp_rot, index=k) for k in range(3)]

                    # Dog_001_rig hereda el 100% del recorrido via el parent
                    # al Empty "jerry" (transform local 0,0,0). spine_6 no
                    # compensa nada: CONSTANTE 0,0,0 / 0,0,0 en todo el tramo
                    # (ver nota "OBSOLETO" junto a la vieja
                    # _empty_world_to_root_bone_basis mas arriba en este archivo).
                    for fc in fc_loc + fc_rot:
                        for _f in (fs, fe):
                            kp = fc.keyframe_points.insert(frame=_f, value=0.0, options={"FAST"})
                            kp.interpolation = "BEZIER"
                            kp.easing = "AUTO"
                        fc.update()

                seg.fps         = st.fps
                seg.entry_ratio = st.entry_ratio
                seg.exit_ratio  = st.exit_ratio
                seg.export_slot_number = st.export_slot_number
                seg.export_type        = st.export_type
                seg.export_desc        = f"Tramo {i}: {tipo}"
                seg.interp_type      = "SMOOTH"
                seg.blend_in_frames  = 0
                seg.blend_out_frames = 0
                seg.blend_strength   = 1.0
                seg.affect_body      = True
                seg.affect_left_arm  = True
                seg.affect_right_arm = True
                seg.affect_left_leg  = True
                seg.affect_right_leg = True
                seg.enabled          = True
                seg.show_config      = False

                # El root y las cuatro extremidades quedan filtrados en todos
                # los segmentos nuevos: continúan con caminar/saltar/subir/
                # bajar mientras el Paso 3 modifica el resto del rig.
                _apply_default_bone_filters(seg)

                # Filtros organicos y parpadeo por defecto de este segmento
                # (idempotente, aislado por segmento -- ver
                # _aplicar_defaults_organicos_jerry / _aplicar_parpadeo_default_seg
                # mas arriba en este archivo).
                _aplicar_defaults_organicos_jerry(context, seg)
                _aplicar_parpadeo_default_seg(seg)

                creados += 1

            except Exception as e_seg:
                import traceback
                print(f"[JerrySeg] Error en tramo {i} ({tramo.get('tipo')}):")
                print(traceback.format_exc())
                errores.append(f"Tramo {i} ({tramo.get('tipo')}): {e_seg}")
                if segs.segments and segs.segments[-1].frame_start == tramo.get("frame_start"):
                    segs.segments.remove(len(segs.segments) - 1)
                continue

        try:
            scene.frame_set(frame_backup)
        except Exception:
            pass
        if arm_obj.animation_data and _prev_arm_action:
            arm_obj.animation_data.action = _prev_arm_action

        segs.active_index = len(segs.segments) - 1 if segs.segments else 0
        _sync_blink_sistema2_con_segmentos(context)

        for area in context.screen.areas:
            area.tag_redraw()

        msg = f"{creados}/{len(tramos)} segmentos creados (root bone: '{_root_bone_name}')"
        if errores:
            msg += f"  |  {len(errores)} con problemas (ver consola)"
            for e in errores:
                print(f"[JerrySeg] {e}")
            self.report({"WARNING"}, msg)
        else:
            self.report({"INFO"}, msg)
        return {"FINISHED"}


def _build_base_cache_action(armature, base_capture, frame_start, frame_end):
    """FIX (Claude, 2026-08-07): reconstruye una action temporal con los
    valores YA CAPTURADOS de Capa 1 (ver `_base_capture` en ConcatenateAll,
    capturado UNA sola vez, correctamente, antes de tocar ningun segmento) y
    la devuelve para ser asignada como action activa del armature.

    BUG que esto corrige: `_push_seg_result_to_nla` deja
    `armature.animation_data.action = None` al terminar cada segmento (para
    aislarlo en su propia pista NLA). Pero tanto `jerryst.concatenate()`
    (operators_anim.py, bloque "CAPTURA DE CAPA 1") como
    `_bake_organic_only_segment()` (mas abajo en este archivo) necesitan
    volver a leer la Capa 1 para el SIGUIENTE segmento evaluando el armature
    en vivo con `scene.frame_set(frame)` + lectura de `armature.pose.bones`.
    Sin una action activa, `scene.frame_set()` ya no mueve la pose: los
    huesos quedan "congelados" en los ultimos valores que tenian (los del
    segmento anterior). Resultado: a partir del segundo segmento procesado,
    caminar/saltar_subir/etc. se hornean con una pose pegada/incorrecta, y
    solo el segmento con poses configuradas de punta a punta (calculadas
    desde los JSON, no desde esta captura en vivo) se ve bien -- que es
    exactamente el bug reportado ("solo se reproduce saltar_bajar").

    Al reasignar esta action (construida con los valores correctos ya
    guardados en `base_capture`) como action activa antes de cada segmento,
    `scene.frame_set()` vuelve a evaluar la pose real de Capa 1 para ESE
    segmento en vez de quedar pegada a la del anterior.

    PERF (Claude, 2026-08-24 -- "el Paso 3 de Jerry tarda demasiado a
    diferencia de Alfred"): esta funcion se llama UNA VEZ POR SEGMENTO
    dentro del loop de ConcatenateAll. Antes de este fix, `frame_start`/
    `frame_end` que recibia eran SIEMPRE el rango acumulado de TODOS los
    segmentos activos (`_capture_start`/`_capture_end`, fijo antes del
    loop) -- es decir, en el segmento 5 de una escena con 8 segmentos se
    volvia a reconstruir, desde cero, el tramo horneado de los primeros 8
    segmentos completos, solo para poder leer el propio. Eso da una
    complejidad O(N segmentos x T frames totales) en vez de O(T frames
    totales) una sola vez -- exactamente el cuello de botella que Alfred
    evita capturando su respaldo de Capa 1 UNA sola vez (action.copy(),
    ver ALFREDSEG_OT_ConcatenateAll) y copiando despues, por segmento,
    solo su PROPIO rango de frames (ver `_copy_action_range` en
    alfred_animation_studio/operators_segments.py).

    ConcatenateAll ahora le pasa a esta funcion unicamente el rango PROPIO
    del segmento que se esta por procesar (`f_s`, `f_e`) -- que es todo lo
    que necesitan leer tanto jerryst.concatenate() (su propia "CAPTURA DE
    CAPA 1" nunca lee mas alla de `[start_frame, seg_frame_end]`, ver
    operators_anim.py) como `_bake_organic_only_segment()` (idem, solo lee
    `[start_frame, end_frame]` del segmento). Con eso el trabajo total del
    loop pasa a ser, en la practica, O(T frames totales) una sola vez
    (la suma de los rangos de cada segmento), igual que en Alfred.

    Ademas, el llenado de fcurves ahora se hace en bloque
    (`keyframe_points.add(n)` + `foreach_set`) en vez de un
    `keyframe_points.insert()` individual por hueso/eje/frame -- cada
    `insert()` es una llamada Python->C separada, mientras que `add` +
    `foreach_set` construye toda la curva en una sola pasada.
    """
    if not base_capture or armature is None:
        return None
    name = "_JRRST_base_cache_arm"
    old = bpy.data.actions.get(name)
    if old:
        bpy.data.actions.remove(old, do_unlink=True)
    action = bpy.data.actions.new(name=name)
    _comp_paths = (
        ("rotation", "rotation_euler"),
        ("location", "location"),
        ("scale",    "scale"),
    )
    # Primero se agrupan todos los puntos por fcurve (data_path, idx) en
    # listas planas -- recien despues se crea cada fcurve y se llena en
    # una sola pasada bulk. Evita crear/buscar la fcurve y llamar a
    # insert() en cada frame individual.
    _series = {}   # (data_path, idx) -> [(frame, value), ...]
    _bone_of = {}  # data_path -> bone_name (para action_group)
    for frame in range(int(frame_start), int(frame_end) + 1):
        pose = base_capture.get(frame)
        if not pose:
            continue
        for bone_name, values in pose.items():
            for comp_key, comp_path in _comp_paths:
                vals = values.get(comp_key)
                if vals is None:
                    continue
                data_path = f'pose.bones["{bone_name}"].{comp_path}'
                _bone_of[data_path] = bone_name
                for idx in range(3):
                    _series.setdefault((data_path, idx), []).append(
                        (frame, vals[idx])
                    )

    for (data_path, idx), points in _series.items():
        fc = _new_fcurve(
            _get_action_fcurves(action),
            data_path, index=idx, action_group=_bone_of[data_path]
        )
        fc.keyframe_points.add(len(points))
        flat_co = [0.0] * (len(points) * 2)
        flat_co[0::2] = [p[0] for p in points]
        flat_co[1::2] = [p[1] for p in points]
        fc.keyframe_points.foreach_set("co", flat_co)
        fc.update()

    if not _get_action_fcurves(action):
        bpy.data.actions.remove(action, do_unlink=True)
        return None
    if not armature.animation_data:
        armature.animation_data_create()
    armature.animation_data.action = action
    return action


def _push_seg_result_to_nla(obj, frame_start, frame_end, track_name):
    """
    PORTADO/ADAPTADO desde alfred_animation_studio (_push_action_to_nla,
    2026-08-06): toma la action que haya quedado ACTIVA en `obj` justo
    despues de un CONCATENAR individual (jerryst.concatenate) y la empuja a
    su propia pista NLA dedicada y aislada (extrapolation='NOTHING'), en vez
    de dejarla como "active action" -- que quedaria pisando por encima del
    resto del stack NLA (extrapolation 'HOLD' por defecto) apenas se
    concatene el SIGUIENTE segmento.

    A diferencia de Alfred (que copia un RANGO de una action de respaldo con
    _copy_action_range), en Jerry cada segmento en modo recorrido ya tiene su
    PROPIA action dedicada (seg.seg_action_name, ver JRRSTSEG_OT_Add /
    JRRST_OT_Concatenate) -- por eso aca alcanza con tomar la action ya
    activa tal cual y aislarla, sin necesidad de copiar/recortar nada.

    No hace nada si `obj` no tiene animation_data o no tiene action activa
    (ej. un segmento sin pose_start/pose_end que no llego a concatenarse).
    """
    if obj is None or not obj.animation_data or not obj.animation_data.action:
        return
    action = obj.animation_data.action
    if not _get_action_fcurves(action):
        obj.animation_data.action = None
        return
    track = obj.animation_data.nla_tracks.new()
    track.name = track_name
    strip = track.strips.new(track_name, int(frame_start), action)
    strip.use_sync_length    = False
    strip.action_frame_start = frame_start
    strip.action_frame_end   = frame_end
    strip.frame_start        = frame_start
    strip.frame_end          = frame_end
    strip.extrapolation      = "NOTHING"
    strip.blend_type         = "REPLACE"
    obj.animation_data.action = None


# PERF (Kebyn/Claude, 2026-08-24): _capture_base_bones recorre frame por
# frame TODO el rango [_capture_start, _capture_end] (el recorrido completo:
# en el caso reportado, 1->504) haciendo scene.frame_set() + view_layer.
# update() en cada uno -- eso es una evaluacion completa del depsgraph por
# frame, y es la razon real de que "Concatenar segmentos" se sienta como si
# recalculara todo de nuevo cada vez: JRRSTSEG_OT_ConcatenateAll llama a esto
# de forma INCONDICIONAL en cada ejecucion, aunque lo unico que haya cambiado
# desde el click anterior sea una pose de un segmento del Paso 3 (que no
# toca ni el recorrido/Capa 1 ni el armature en absoluto).
#
# Cache: se guarda el resultado junto con una "firma" barata de todo lo que
# realmente puede alterar la Capa 1 (puntos del recorrido, walk styles,
# rotacion raiz, el armature usado y el rango capturado). Si al volver a
# entrar la firma es identica a la ultima, se reusa el diccionario ya
# capturado y se evita por completo el paso frame-a-frame. Si el usuario
# graba de nuevo el recorrido, mueve un punto, cambia walk styles o el rango
# de segmentos activos, la firma cambia y se recaptura normalmente.
_BASE_CAPTURE_CACHE = {"sig": None, "data": None}


def _base_capture_signature(pc, armature, start_frame, end_frame):
    pts_sig = tuple(
        (
            round(pt.coords[0], 5), round(pt.coords[1], 5), round(pt.coords[2], 5),
            pt.tipo_segmento, pt.parada_frames_punto,
        )
        for pt in (pc.path_points if pc is not None else [])
    )
    styles_sig = tuple(
        getattr(item, "name", "") for item in (getattr(pc, "walk_styles", []) or [])
    )
    root_rot_sig = (
        (round(pc.root_rot_x, 5), round(pc.root_rot_y, 5), round(pc.root_rot_z, 5))
        if pc is not None else None
    )
    return (
        armature.name if armature is not None else None,
        int(start_frame), int(end_frame),
        pts_sig, styles_sig, root_rot_sig,
    )


def _capture_base_bones(context, armature, start_frame, end_frame, pc=None):
    """Captura la evaluación de la Capa 1 antes de aplicar Paso 3.

    Reusa el resultado de la última captura (ver _BASE_CAPTURE_CACHE) si la
    firma del recorrido/armature/rango no cambió desde entonces.
    """
    if armature is None:
        return {}

    sig = _base_capture_signature(pc, armature, start_frame, end_frame)
    if sig == _BASE_CAPTURE_CACHE["sig"] and _BASE_CAPTURE_CACHE["data"] is not None:
        return _BASE_CAPTURE_CACHE["data"]

    scene = context.scene
    backup = scene.frame_current
    captured = {}
    for frame in range(int(start_frame), int(end_frame) + 1):
        scene.frame_set(frame)
        context.view_layer.update()
        captured[frame] = {
            bone.name: {
                "rotation": tuple(bone.rotation_euler),
                "location": tuple(bone.location),
                "scale": tuple(bone.scale),
            }
            for bone in armature.pose.bones
        }
    scene.frame_set(backup)
    context.view_layer.update()

    _BASE_CAPTURE_CACHE["sig"] = sig
    _BASE_CAPTURE_CACHE["data"] = captured
    return captured


def _push_base_overlay_to_nla(armature, frame_start, frame_end, track_name,
                              captured, filtered_bones):
    """Añade la animación base solo para los huesos filtrados.

    Los strips del Paso 3 usan REPLACE. Por eso la base no puede quedarse en
    una pista inferior: el strip de poses ocultaría caminar y saltos aunque
    sus huesos estén filtrados. Esta pista superior contiene únicamente los
    huesos azules y deja intactos los huesos que controla el Paso 3.
    """
    if armature is None or not captured or not filtered_bones:
        return False
    if not armature.animation_data:
        armature.animation_data_create()
    old_track = armature.animation_data.nla_tracks.get(track_name)
    if old_track:
        armature.animation_data.nla_tracks.remove(old_track)
    action = bpy.data.actions.get(track_name)
    if action:
        bpy.data.actions.remove(action, do_unlink=True)
    action = bpy.data.actions.new(track_name)
    for bone_name in sorted(filtered_bones):
        if bone_name == "Dog_001_rig":
            continue
        for index, component in enumerate(("rotation", "location", "scale")):
            data_path = f'pose.bones["{bone_name}"].{component}'
            fc = _get_action_fcurves(action).new(data_path=data_path, index=index)
            for frame in range(int(frame_start), int(frame_end) + 1):
                values = captured.get(frame, {}).get(bone_name)
                if values is not None:
                    fc.keyframe_points.insert(frame, values[component][index], options={"FAST"})
            for key in fc.keyframe_points:
                key.interpolation = "BEZIER"
    if not _get_action_fcurves(action):
        bpy.data.actions.remove(action, do_unlink=True)
        return False
    track = armature.animation_data.nla_tracks.new()
    track.name = track_name
    strip = track.strips.new(track_name, int(frame_start), action)
    strip.action_frame_start = int(frame_start)
    strip.action_frame_end = int(frame_end)
    strip.frame_start = int(frame_start)
    strip.frame_end = int(frame_end)
    strip.extrapolation = "NOTHING"
    strip.blend_type = "REPLACE"
    strip.use_auto_blend = False
    strip.blend_in = 0
    strip.blend_out = 0
    return True


def _bake_organic_only_segment(context, seg, armature, start_frame, end_frame,
                                precaptured=None):
    """Hornea la Capa 1 (y opcionalmente filtros/oscilaciones) de un segmento
    que no tiene Action Poses.

    CONCATENAR tradicional necesita poses para reconstruir una action, pero los
    segmentos creados automáticamente pueden contener únicamente filtros
    orgánicos, o directamente nada propio (un tramo "caminar"/"correr" que
    solo debe reproducir el recorrido base). En ambos casos se captura la pose
    evaluada del recorrido base y se crea una action propia para ese rango,
    aislada en su propio strip NLA.

    BUG (Kebyn, 2026-09-27): jerrypr.preview_path() hornea TODO el recorrido
    (parada/caminar/saltar) en una UNICA action directa del armature
    ("_jerry_preview_arm"). En cuanto el PRIMER segmento del Paso 3 pasa por
    jerryst.concatenate(), esa action se desasigna y se BORRA (ver "FIX 2" en
    JRRSTSEG_OT_ConcatenateAll). Un segmento posterior sin poses, sin filtros
    orgánicos y sin oscilaciones (ej. un tramo "caminar"/"correr" que solo
    necesita el desplazamiento base) hacia return False ANTES de llegar al
    horneado de mas abajo -- nunca se creaba ni se empujaba a NLA ninguna
    action para su rango, así que sus bones quedaban sin ninguna animación
    (el personaje se trasladaba via el Empty "jerry", pero sin mover huesos).
    Por eso ahora también se hornea cuando el segmento pertenece al recorrido
    (`not seg.single_coord_mode`), aunque no tenga filtros ni oscilaciones:
    hay que preservar el ciclo de caminar/correr capturado en `precaptured`.

    PERF (Kebyn/Claude, 2026-08-24): esta funcion recapturaba frame por frame
    (scene.frame_set + view_layer.update, una evaluacion COMPLETA del
    depsgraph por frame) la misma Capa 1 que ConcatenateAll YA capturo un
    momento antes en _capture_base_bones() para el rango combinado de todos
    los segmentos activos -- trabajo duplicado y caro (era el grueso de los
    ~11s que tardaba un segmento de 88 frames SIN ninguna pose). Si el
    caller (JRRSTSEG_OT_ConcatenateAll) ya tiene esos datos, los pasa via
    `precaptured` (mismo formato que devuelve _capture_base_bones: dict
    frame -> {bone_name: {rotation, location, scale}}) y aca se reusan sin
    volver a tocar la escena. Solo si no viene nada precapturado (llamado
    desde otro lado, ej. el boton CONCATENAR individual de un segmento sin
    poses) se recae en el capture-loop original.
    """
    org = getattr(seg, "organic", None)
    if armature is None:
        return False

    # (Kebyn, 2026-08-12): antes esta funcion exigia filtros organicos
    # habilitados (org.enabled) para hornear NADA -- un segmento con solo
    # oscilaciones de bones (sin filtros organicos) se descartaba en
    # silencio. Ahora se procede si hay filtros organicos O oscilaciones
    # habilitadas.
    #
    # FIX (Kebyn, 2026-09-27): tambien se procede si el segmento pertenece
    # al recorrido (not single_coord_mode), aunque no tenga filtros ni
    # oscilaciones -- ver docstring arriba. Sin esto, un tramo "caminar"/
    # "correr" sin poses ni filtros no dejaba NINGUN rastro en el NLA y sus
    # bones quedaban congelados. Solo un segmento de 1 coordenada (sin
    # recorrido base que preservar) sigue devolviendo False cuando no tiene
    # ni filtros ni oscilaciones: ahi realmente no hay nada que hornear.
    _jerryst_osc = getattr(context.scene, "jerryst", None)
    _osc_settings = getattr(_jerryst_osc, "bone_oscillations", None) if _jerryst_osc else None
    _has_osc = bool(_osc_settings and _osc_settings.enabled and len(_osc_settings.items) > 0)
    _has_org = bool(org is not None and org.enabled)
    _is_recorrido_seg = not getattr(seg, "single_coord_mode", False)
    if not _has_org and not _has_osc and not _is_recorrido_seg:
        return False

    if not armature.animation_data:
        armature.animation_data_create()

    scene = context.scene
    frame_backup = scene.frame_current

    if precaptured and all(f in precaptured for f in range(int(start_frame), int(end_frame) + 1)):
        captured = [(f, precaptured[f]) for f in range(int(start_frame), int(end_frame) + 1)]
    else:
        captured = []
        for frame in range(start_frame, end_frame + 1):
            scene.frame_set(frame)
            context.view_layer.update()
            captured.append((frame, {
                bone.name: {
                    "rotation": tuple(bone.rotation_euler),
                    "location": tuple(bone.location),
                    "scale": tuple(bone.scale),
                }
                for bone in armature.pose.bones
            }))

    action_name = getattr(seg, "seg_action_name", "") or f"jerryseg_{seg.label}"
    action_name = action_name[:63]
    old_action = bpy.data.actions.get(action_name)
    if old_action:
        bpy.data.actions.remove(old_action, do_unlink=True)
    action = bpy.data.actions.new(name=action_name)
    seg.seg_action_name = action_name
    armature.animation_data.action = action

    # PERF: los valores ya estan en `captured` -- no hace falta volver a
    # frame_set() por cada uno, keyframe_insert(frame=...) ya es explicito.
    for frame, pose in captured:
        for bone_name, values in pose.items():
            bone = armature.pose.bones.get(bone_name)
            if bone is None:
                continue
            bone.rotation_mode = "XYZ"
            bone.rotation_euler = values["rotation"]
            bone.location = values["location"]
            bone.scale = values["scale"]
            bone.keyframe_insert(data_path="rotation_euler", frame=frame)
            bone.keyframe_insert(data_path="location", frame=frame)
            bone.keyframe_insert(data_path="scale", frame=frame)

    from .operators_anim import _apply_organic_filters, _apply_bone_oscillations
    _filtered = {
        bone_name for bone_name, filter_attr in _BONE_FILTER_MAP.items()
        if getattr(seg, filter_attr, False)
    }
    if _has_org:
        _apply_organic_filters(
            context, armature, start_frame, end_frame, org,
            filtered_bones=_filtered,
        )
    # Oscilaciones de bones (ear/jaw/tail/etc): un segmento sin poses tambien
    # puede tener oscilaciones configuradas y deben viajar en el mismo strip
    # horneado aca, igual que las reciben los segmentos CON poses via
    # jerryst.concatenate() (Kebyn, 2026-08-12).
    if _has_osc:
        _apply_bone_oscillations(
            context, armature, _osc_settings,
            filtered_bones=_filtered,
        )
    scene.frame_set(frame_backup)
    return True


class JRRSTSEG_OT_ConcatenateAll(Operator):
    """
    PORTADO desde alfred_animation_studio (ALFREDSEG_OT_ConcatenateAll),
    2026-08-06: ejecuta, para CADA segmento activo del Paso 3 que ya tenga
    pose de INICIO y pose de FIN configuradas, el mismo proceso que el boton
    CONCATENAR individual (jerryst.concatenate), uno por uno, respetando el
    rango de frames PROPIO de cada segmento. Al terminar reproduce todas las
    secuencias encadenadas de principio a fin, en el orden de sus
    frame_start.

    AISLAMIENTO ENTRE SEGMENTOS: apenas se concatena un segmento, la action
    que jerryst.concatenate dejo activa en el armature (y, en segmentos de 1
    coordenada, tambien en el Empty "jerry") se empuja a su propia pista NLA
    dedicada (ver _push_seg_result_to_nla) antes de pasar al siguiente --
    asi el CONCATENAR del segmento 2 nunca pisa lo que ya quedo horneado
    para el segmento 1.
    """
    bl_idname  = "jerryseg.concatenate_all"
    bl_label   = "Concatenar segmentos"
    bl_description = (
        "Ejecuta CONCATENAR para todos los segmentos activos del Paso 3 que "
        "ya tengan pose de inicio y fin configuradas, uno por uno, "
        "respetando la secuencia de frames propia de cada segmento, y luego "
        "reproduce todo de principio a fin"
    )
    bl_options = {"REGISTER"}   # SIN UNDO: dispara reproduccion

    def execute(self, context):
        # DEBUG PERF (Kebyn/Claude, 2026-08-24): instrumentacion temporal
        # para medir donde se va el tiempo real de "Concatenar segmentos".
        # Imprime en la consola de Blender (Window > Toggle System Console
        # en Windows, o la terminal si abriste Blender desde ahi) un
        # timestamp por fase. Sacar este bloque (y los _t_mark() de mas
        # abajo) una vez identificado el cuello de botella real.
        import time as _time_dbg
        _t0 = _time_dbg.perf_counter()
        _t_prev = [_t0]
        def _t_mark(label):
            _now = _time_dbg.perf_counter()
            print(f"[PERF ConcatenarTodo] {label}: {_now - _t_prev[0]:.3f}s "
                  f"(total {_now - _t0:.3f}s)")
            _t_prev[0] = _now

        scene   = context.scene
        seg_cfg = scene.jerry_segs

        _indexed = [(i, s) for i, s in enumerate(seg_cfg.segments) if s.enabled]
        _indexed.sort(key=lambda pair: pair[1].frame_start)

        if not _indexed:
            self.report({"WARNING"}, "No hay segmentos activos en el Paso 3")
            return {"CANCELLED"}

        # Filtros organicos y parpadeo por defecto, idempotente y AISLADO
        # POR SEGMENTO (ver _aplicar_defaults_organicos_jerry /
        # _aplicar_parpadeo_default_seg mas arriba en este archivo).
        for _, _seg_default in _indexed:
            _aplicar_defaults_organicos_jerry(context, _seg_default)
            _aplicar_parpadeo_default_seg(_seg_default)
        _sync_blink_sistema2_con_segmentos(context)
        _t_mark("defaults organicos/parpadeo")

        # Regenerar Capa 1 (recorrido base: caminar/saltar/parada) antes de
        # inyectar ninguna pose, para que cada segmento parta de un canvas
        # fresco -- igual que hace jerryseg.play_segment_recorrido. Solo si
        # ALGUNO de los segmentos activos pertenece al recorrido (no es
        # single_coord_mode); si TODOS son de 1 coordenada, se omite.
        pc = getattr(scene, "jerry_path", None)
        _hay_recorrido_activo = any(not s.single_coord_mode for _, s in _indexed)
        if _hay_recorrido_activo and pc is not None and len(pc.path_points) > 1:
            _regen = bpy.ops.jerrypr.preview_path()
            _t_mark("jerrypr.preview_path() [regenerar Capa 1]")
            if "CANCELLED" in _regen:
                self.report({"ERROR"},
                    "No se pudo regenerar el recorrido base (Capa 1) antes de "
                    "concatenar. Revisa el recorrido grabado / el .blend del "
                    "personaje.")
                return {"CANCELLED"}

        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()

        # Limpiar pistas NLA "JRRSEG_*" de una concatenacion anterior, tanto
        # del armature como del Empty "jerry" -- si no, se acumularian
        # pistas viejas encima de las nuevas en cada corrida.
        arm_pre  = _resolve_armature(seg_cfg, scene)
        root_pre = scene.objects.get("jerry")
        for _obj_pre in (arm_pre, root_pre):
            if _obj_pre is not None and _obj_pre.animation_data:
                for _trk in list(_obj_pre.animation_data.nla_tracks):
                    if _trk.name.startswith("JRRSEG_") or _trk.name.startswith("JRRBASE_"):
                        _obj_pre.animation_data.nla_tracks.remove(_trk)
        _t_mark("limpieza pistas NLA previas")

        # Capturar la Capa 1 ya evaluada antes de escribir poses del Paso 3.
        # Se usara para reinyectar caminar/saltar solo en los huesos filtrados.
        _base_capture = {}
        if _hay_recorrido_activo and arm_pre is not None:
            _capture_start = min(s.frame_start for _, s in _indexed)
            _capture_end = max(
                (s.frame_end if (not s.single_coord_mode and s.frame_end > s.frame_start)
                 else _calc_seg_frames(s)[1])
                for _, s in _indexed
            )
            _base_capture = _capture_base_bones(
                context, arm_pre, _capture_start, _capture_end, pc
            )
        _t_mark("_capture_base_bones() [Capa 1]")

        # FIX (Claude, 2026-08-07 -- ver docstring de _build_base_cache_action
        # mas arriba en este archivo): Capa 1 se reconstruye como action-cache
        # a partir de _base_capture (ya correcto) y se deja asignada como
        # action activa del armature -- DENTRO del loop de abajo, una vez por
        # segmento (ver comentario "FIX 2" mas abajo: jerryst.concatenate()
        # borra la action activa al terminar cada segmento, asi que reusar la
        # misma referencia revienta con ReferenceError apenas se llega al
        # segundo segmento). Aca solo se inicializa la variable.
        _base_cache_action = None

        # NOTA (Kebyn, 2026-08-27): la automatizacion de "Sistema 1" (Secuencia
        # de Ojos por-segmento: build_eye_shape_keys + jerryst.concatenate_2)
        # se elimino junto con ese sistema por no usarse -- ver panels.py /
        # operators_base.py / properties.py. _errors se conserva vacio porque
        # el resto de esta funcion sigue reportando su contenido mas abajo.
        _errors = []

        _original_active = seg_cfg.active_index
        _f_min, _f_max = None, None
        _done = 0
        _sin_acciones = []
        # Acumula (frame_start, frame_end, blink_count, blink_duration) de
        # TODOS los segmentos activos, para renderizar el parpadeo real de
        # "Parpadeo automatico (por segmento)" en una sola pasada al final
        # del loop (ver _recolectar_parpadeos_segmento mas arriba).
        _blink_render_queue = []

        for pos, (orig_idx, seg) in enumerate(_indexed):
            _t_seg0 = _time_dbg.perf_counter()
            f_s = seg.frame_start
            _, f_e_calc = _calc_seg_frames(seg)
            f_e = seg.frame_end if (not seg.single_coord_mode and seg.frame_end > f_s) else f_e_calc
            _f_min = f_s if _f_min is None else min(_f_min, f_s)
            _f_max = f_e if _f_max is None else max(_f_max, f_e)

            # FIX (Claude, 2026-08-07): re-hidratar Capa 1 antes de procesar
            # ESTE segmento (ver docstring de _build_base_cache_action mas
            # arriba). El segmento anterior puede haber dejado
            # armature.animation_data.action = None (via
            # _push_seg_result_to_nla) -- sin esto, la captura "en vivo" de
            # Capa 1 que hacen jerryst.concatenate() /
            # _bake_organic_only_segment() para ESTE segmento leeria una
            # pose congelada en vez de caminar/saltar_subir/etc.
            #
            # FIX 2 (Claude, 2026-08-07): jerryst.concatenate() (ver
            # operators_anim.py, bloque "limpiar action directa previa" cerca
            # de la linea 827) toma la action que este ACTIVA en el armature
            # al empezar, la desasigna Y LA BORRA con bpy.data.actions.remove()
            # -- pensado para limpiar restos de una action directa vieja, pero
            # como aca dejamos _base_cache_action activa a proposito, ese
            # cleanup la destruye de verdad (RNA invalido) apenas termina el
            # PRIMER segmento. Al llegar al SEGUNDO segmento, reasignar la
            # misma referencia Python revienta con
            # "ReferenceError: StructRNA of type Action has been removed" --
            # y de paso, sin Capa 1 valida, los bones filtrados (por defecto
            # las 4 patas, ver _apply_default_bone_filters) quedan congelados
            # en vez de conservar caminar/saltar_subir/etc. Por eso se
            # RECONSTRUYE la action-cache en cada iteracion (a partir de
            # _base_capture, que es un dict de Python normal y sobrevive sin
            # problema) en vez de reutilizar la misma referencia.
            #
            # PERF (Claude, 2026-08-24 -- ver docstring completo de
            # _build_base_cache_action): se le pasa el rango PROPIO de ESTE
            # segmento (f_s, f_e), NO el rango acumulado de todos los
            # segmentos (_capture_start, _capture_end). jerryst.concatenate()
            # y _bake_organic_only_segment() solo leen, para este segmento,
            # frames dentro de su propio [f_s, f_e] -- reconstruir el tramo
            # completo de los demas segmentos en cada iteracion no aportaba
            # nada y era la causa real de que el Paso 3 de Jerry tardara
            # mucho mas que el de Alfred (que solo copia el rango propio de
            # cada segmento, ver _copy_action_range).
            if _base_capture and arm_pre is not None:
                _base_cache_action = _build_base_cache_action(
                    arm_pre, _base_capture, f_s, f_e
                )
                _arm_rehydrate = _resolve_armature(seg_cfg, scene)
                if _arm_rehydrate is not None:
                    if not _arm_rehydrate.animation_data:
                        _arm_rehydrate.animation_data_create()
                    _arm_rehydrate.animation_data.action = _base_cache_action

            if len(seg.action_poses) == 0:
                # Un segmento puede ser válido aunque solo tenga filtros
                # orgánicos. Se hornea sobre la pose evaluada del recorrido
                # base y se aisla en su propio strip NLA.
                arm_now = _resolve_armature(seg_cfg, scene)
                try:
                    _organic_done = _bake_organic_only_segment(
                        context, seg, arm_now, f_s, f_e,
                        precaptured=_base_capture,
                    )
                except Exception as e_org:
                    _errors.append(
                        f"Segmento '{seg.label}': fallo en filtros organicos ({e_org})"
                    )
                    _organic_done = False
                if _organic_done:
                    _safe_label = "".join(
                        c if c.isalnum() else "_" for c in (seg.label or "seg")
                    )[:32]
                    _track_name = f"JRRSEG_{orig_idx:02d}_{_safe_label}"
                    _push_seg_result_to_nla(
                        arm_now, f_s, f_e, _track_name + "_arm"
                    )
                    _done += 1
                    _recolectar_parpadeos_segmento(seg, f_s, f_e, _blink_render_queue)
                else:
                    _sin_acciones.append(seg.label)
                print(f"[PERF ConcatenarTodo] segmento '{seg.label}' (sin poses, "
                      f"{f_s}->{f_e}): {_time_dbg.perf_counter() - _t_seg0:.3f}s")
                continue

            seg_cfg.active_index = orig_idx
            try:
                result = bpy.ops.jerryst.concatenate()
            except RuntimeError as e_cat:
                _errors.append(f"Segmento '{seg.label}': fallo al concatenar ({e_cat})")
                continue

            if "FINISHED" not in result:
                _errors.append(f"Segmento '{seg.label}': fallo al concatenar")
                continue

            # Aislar el resultado de ESTE segmento en su propia pista NLA
            # antes de pasar al siguiente (ver _push_seg_result_to_nla).
            _safe_label = "".join(c if c.isalnum() else "_" for c in (seg.label or "seg"))[:32]
            _track_name = f"JRRSEG_{orig_idx:02d}_{_safe_label}"
            arm_now  = _resolve_armature(seg_cfg, scene)
            root_now = scene.objects.get("jerry")
            _push_seg_result_to_nla(arm_now,  f_s, f_e, _track_name + "_arm")
            if seg.single_coord_mode:
                _push_seg_result_to_nla(root_now, f_s, f_e, _track_name + "_root")

            _done += 1
            _recolectar_parpadeos_segmento(seg, f_s, f_e, _blink_render_queue)
            print(f"[PERF ConcatenarTodo] segmento '{seg.label}' ({f_s}->{f_e}, "
                  f"{len(seg.action_poses)} poses): "
                  f"{_time_dbg.perf_counter() - _t_seg0:.3f}s")

        _t_mark("loop de segmentos (jerryst.concatenate x N)")

        # FIX (Claude, 2026-08-07): limpiar la action-cache de Capa 1 (ver
        # _base_cache_action mas arriba) despues del loop. En el caso comun
        # ya queda en None (la ultima llamada a _push_seg_result_to_nla la
        # limpia), pero si el ULTIMO segmento no llego a empujar nada (ej.
        # "_organic_done" False), el armature se quedaria con esta action-
        # cache como action DIRECTA activa -- lo cual tapa TODO el stack NLA
        # (JRRSEG_*/JRRBASE_*) que se armo, ya que una action directa tiene
        # prioridad sobre las pistas NLA. Se limpia siempre por las dudas.
        #
        # FIX 3 (Kebyn, 2026-08-24): si el ULTIMO segmento del bucle SI paso
        # por bpy.ops.jerryst.concatenate() (no por el atajo "solo organico"),
        # ese operador ya desasigna Y BORRA la action activa del armature al
        # terminar (ver "FIX 2" arriba) -- que en ese momento es precisamente
        # ESTE _base_cache_action, reconstruido para ese segmento. La
        # referencia Python sigue viva pero el StructRNA subyacente ya no
        # existe, asi que volver a llamar bpy.data.actions.remove() sobre
        # ella revienta con "ReferenceError: StructRNA of type Action has
        # been removed". Se verifica que la action siga siendo valida
        # (tocando .name dentro de un try) antes de tocarla de nuevo.
        if _base_cache_action is not None:
            try:
                _base_cache_name = _base_cache_action.name
            except ReferenceError:
                _base_cache_name = None  # ya fue borrada por jerryst.concatenate()

            if _base_cache_name is not None:
                _arm_cleanup = _resolve_armature(seg_cfg, scene)
                if (_arm_cleanup is not None and _arm_cleanup.animation_data
                        and _arm_cleanup.animation_data.action
                        and _arm_cleanup.animation_data.action.name == _base_cache_name):
                    _arm_cleanup.animation_data.action = None
                bpy.data.actions.remove(_base_cache_action, do_unlink=True)

        # La acción de cada segmento es REPLACE y puede ocultar las pistas
        # Slot_* del recorrido. Reinyectar una pista superior con solo los
        # huesos filtrados garantiza que caminar, saltar subir y saltar bajar
        # sigan visibles mientras el resto recibe las poses del Paso 3.
        if _base_capture and arm_pre is not None:
            for _overlay_idx, _overlay_seg in _indexed:
                _overlay_start = _overlay_seg.frame_start
                _, _overlay_calc_end = _calc_seg_frames(_overlay_seg)
                _overlay_end = (
                    _overlay_seg.frame_end
                    if (not _overlay_seg.single_coord_mode and
                        _overlay_seg.frame_end > _overlay_start)
                    else _overlay_calc_end
                )
                _overlay_filtered = {
                    _bone_name for _bone_name, _filter_attr in _BONE_FILTER_MAP.items()
                    if getattr(_overlay_seg, _filter_attr, False)
                }
                _push_base_overlay_to_nla(
                    arm_pre, _overlay_start, _overlay_end,
                    f"JRRBASE_{_overlay_idx:02d}",
                    _base_capture, _overlay_filtered,
                )

        seg_cfg.active_index = _original_active

        # Renderizar TODO el parpadeo "por segmento" acumulado en una sola
        # pasada de keyframes (ver _recolectar_parpadeos_segmento y
        # apply_blink_intervals_multi) -- esto es lo que realmente hacia
        # falta: antes de este parche, seg.blink_intervals se guardaba,
        # cargaba y se veia en el panel, pero ningun codigo lo convertia en
        # keyframes sobre las mallas de ojo, por lo que no se reproducia
        # ningun parpadeo aunque cada segmento ya trajera como minimo un
        # intervalo configurado.
        _blink_msg = ""
        if _blink_render_queue:
            try:
                _blink_ok = apply_blink_intervals_multi(_blink_render_queue)
                if _blink_ok:
                    _blink_msg = f"  |  parpadeo: {len(_blink_render_queue)} intervalo(s)"
                else:
                    _blink_msg = ("  |  parpadeo: no se encontraron las mallas de ojo "
                                  "(ojo_izquierdo_jerry / ojo_derecho_jerry)")
            except Exception as e_bl:
                import traceback
                print("[JerrySeg ConcatenarTodo] Error aplicando parpadeo por segmento:")
                print(traceback.format_exc())
                _blink_msg = f"  |  parpadeo: ERROR ({e_bl})"

        if _done == 0:
            if _errors:
                # Hubo fallos REALES de concatenacion (no solo segmentos sin
                # Acciones/slots) -> esto si es un error bloqueante.
                self.report({"ERROR"},
                    "Ningun segmento pudo concatenarse: " + " | ".join(_errors))
                return {"CANCELLED"}
            # Todos los segmentos activos estan simplemente sin Acciones/
            # slots configurados (caso normal cuando el Paso 3 solo necesita
            # el desplazamiento base -- caminar/saltar/parada de Capa 1, ya
            # generado por jerrypr.preview_path() mas arriba). No es un
            # error: se deja reproducir con esa base tal cual, sin exigir
            # poses que no hacen falta.
            if _sin_acciones:
                self.report({"INFO"},
                    f"{len(_sin_acciones)} segmento(s) sin Acciones/slots "
                    "configurados; se reproduce solo el desplazamiento base.")

        if _f_min is not None:
            if scene.frame_start > _f_min:
                scene.frame_start = _f_min
            if scene.frame_end < _f_max:
                scene.frame_end = _f_max
            scene.frame_set(_f_min)

        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()

        def _deferred_play():
            if not bpy.context.screen.is_animation_playing:
                bpy.ops.screen.animation_play()
            return None
        bpy.app.timers.register(_deferred_play, first_interval=0.02)

        msg = (
            f"Secuencia concatenada: {_done}/{len(_indexed)} segmentos, "
            f"frames {_f_min}->{_f_max}"
            + (f"  |  {len(_errors)} advertencias" if _errors else "")
            + _blink_msg
        )
        for _e in _errors:
            print(f"[JerrySeg ConcatenarTodo] {_e}")
        _t_mark("post-proceso (overlay base + parpadeo + timeline)")
        try:   # concatenar borra las pistas NLA del personaje (tambien las de voz): se vuelven a crear (audio_import)
            from . import audio_import as _audio_import
            _audio_import.post_concatenar(context)
        except Exception as _e:
            print(f"[ConcatenarTodo] audio: {_e}")
        try:   # elementos del guion 2.0 de la configuracion: objetos y mundo, sonidos (idempotentes)
            from . import audio_import as _guion_ai
            _guion = _guion_ai.guion_de_escena(context.scene)
            if _guion and (_guion.get("objetos") or _guion.get("mundo")):
                from . import objetos_mundo as _guion_obj
                _obj_res = _guion_obj.calcular(context, _guion)
                _obj_n = _guion_obj.aplicar(context, _obj_res)
                _obj_vis = _guion_obj.aplicar_mundo_visibilidad(context, _guion)
                print(f"[ConcatenarTodo] Guion objetos: {_obj_n} horneados; mundo={_obj_vis}")
            if _guion and ((_guion.get("sonidos") or {}).get("manuales")):
                from . import sonidos_guion as _guion_snd
                print(f"[ConcatenarTodo] Guion sonidos: {_guion_snd.aplicar_sonidos(context, _guion, auto=False)}")
        except Exception as _e:
            print(f"[ConcatenarTodo] guion 2.0: {_e}")
        print(f"[PERF ConcatenarTodo] TOTAL: {_time_dbg.perf_counter() - _t0:.3f}s")
        self.report({"INFO"}, msg)
        return {"FINISHED"}


# =============================================================================
# SELECTORES DE POSE (.json) para cada campo
# =============================================================================

class _PickPoseBase(Operator):
    """Base para los operadores de seleccion de pose .json."""
    bl_options = {"REGISTER", "UNDO"}
    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})
    _target_attr = ""  # "pose_start_file" / "pose_mid_file" / "pose_end_file"
    _label_attr  = ""  # "pose_start_label" / ...
    _edit_target_attr = ""   # "edit_pose_start_file" / ...
    _edit_label_attr  = ""   # "edit_pose_start_label" / ...

    def execute(self, context):
        segs = context.scene.jerry_segs
        # Escribe siempre en los campos edit_* del formulario de creacion
        if self._edit_target_attr:
            setattr(segs, self._edit_target_attr, self.filepath)
        if self._edit_label_attr:
            setattr(segs, self._edit_label_attr, os.path.basename(self.filepath))
        self.report({"INFO"}, f"Pose cargada: {os.path.basename(self.filepath)}")
        return {"FINISHED"}

    def invoke(self, context, event):
        segs = context.scene.jerry_segs
        self.filepath = bpy.path.abspath(segs.poses_dir) if segs.poses_dir else ""
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class JRRSTSEG_OT_PickPoseStart(_PickPoseBase):
    bl_idname    = "jerryseg.pick_pose_start"
    bl_label     = "Seleccionar pose INICIO"
    bl_description = "Abre explorador para seleccionar el .json de la pose de inicio del segmento"
    _target_attr = "pose_start_file"
    _label_attr  = "pose_start_label"
    _edit_target_attr = "edit_pose_start_file"
    _edit_label_attr  = "edit_pose_start_label"


class JRRSTSEG_OT_PickPoseMid(_PickPoseBase):
    bl_idname    = "jerryseg.pick_pose_mid"
    bl_label     = "Seleccionar pose INTERMEDIA"
    bl_description = "Abre explorador para seleccionar el .json de la pose intermedia (opcional)"
    _target_attr = "pose_mid_file"
    _label_attr  = "pose_mid_label"
    _edit_target_attr = "edit_pose_mid_file"
    _edit_label_attr  = "edit_pose_mid_label"


class JRRSTSEG_OT_PickPoseEnd(_PickPoseBase):
    bl_idname    = "jerryseg.pick_pose_end"
    bl_label     = "Seleccionar pose FIN"
    bl_description = "Abre explorador para seleccionar el .json de la pose final del segmento"
    _target_attr = "pose_end_file"
    _label_attr  = "pose_end_label"
    _edit_target_attr = "edit_pose_end_file"
    _edit_label_attr  = "edit_pose_end_label"


# =============================================================================
# CAPTURA DE FRAMES DESDE LA TIMELINE
# =============================================================================

class JRRSTSEG_OT_SetFrameStart(Operator):
    bl_idname  = "jerryseg.set_frame_start"
    bl_label   = "Frame actual → Inicio"
    bl_description = "Usa el frame actual de la timeline como frame de inicio del segmento"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        segs = context.scene.jerry_segs
        idx  = segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "No hay segmento seleccionado"); return {"CANCELLED"}
        segs.segments[idx].frame_start = context.scene.frame_current
        return {"FINISHED"}


class JRRSTSEG_OT_SetFrameMid(Operator):
    bl_idname  = "jerryseg.set_frame_mid"
    bl_label   = "Frame actual → Intermedio"
    bl_description = "Usa el frame actual de la timeline como frame intermedio del segmento"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        segs = context.scene.jerry_segs
        idx  = segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "No hay segmento seleccionado"); return {"CANCELLED"}
        segs.segments[idx].frame_mid = context.scene.frame_current
        return {"FINISHED"}


class JRRSTSEG_OT_SetFrameEnd(Operator):
    bl_idname  = "jerryseg.set_frame_end"
    bl_label   = "Frame actual → Fin"
    bl_description = "Usa el frame actual de la timeline como frame de fin del segmento"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        segs = context.scene.jerry_segs
        idx  = segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "No hay segmento seleccionado"); return {"CANCELLED"}
        segs.segments[idx].frame_end = context.scene.frame_current
        return {"FINISHED"}


# =============================================================================
# GUARDAR / CARGAR CONFIGURACION DEL PASO 3
# =============================================================================

class JRRSTSEG_OT_SaveConfig(Operator):
    bl_idname  = "jerryseg.save_config"
    bl_label   = "Guardar config Paso 3"
    bl_description = "Guarda la lista de segmentos del Paso 3 a un archivo .json"
    bl_options = {"REGISTER"}

    def execute(self, context):
        segs     = context.scene.jerry_segs
        cfg_dir  = bpy.path.abspath(segs.config_dir)
        cfg_name = segs.config_name or "segs_config"
        if not cfg_dir:
            self.report({"ERROR"}, "Configura la carpeta de configuracion primero")
            return {"CANCELLED"}
        os.makedirs(cfg_dir, exist_ok=True)
        filepath = os.path.join(cfg_dir, f"{cfg_name}_paso3.json")

        data = {
            "armature_name":      segs.armature_name,
            "poses_dir":          segs.poses_dir,
            "export_slot_number": segs.export_slot_number,
            "export_type":        segs.export_type,
            "segments": []
        }

        # Atributos escalares del segmento (sin action_poses)
        # NOTA (Kebyn, 2026-08-06): se quitaron las claves fantasma
        # "pose_start_*"/"pose_end_*" (ya no existen en seg -- el primer y
        # ultimo item de action_poses son las anclas de inicio/fin) y se
        # agregaron las 44 flags "filter_*", que antes NO se guardaban en
        # absoluto desde este exportador (jerryseg.save_config, distinto del
        # de config_ops.py / jerryst.save_config).
        scalar_attrs = [
            "label", "frame_start", "frame_end",
            "single_coord_mode", "frame_end_auto",
            "fps", "entry_ratio", "exit_ratio",
            "export_slot_number", "export_type", "export_desc",
            # legacy modulator
            "frame_mid", "pose_mid_file", "pose_mid_label",
            "interp_type", "interp_mid_to_end",
            "blend_in_frames", "blend_out_frames", "blend_strength",
            "affect_body", "affect_left_arm", "affect_right_arm",
            "affect_left_leg", "affect_right_leg", "affect_root",
            "affect_shield", "affect_spear", "enabled",
        ] + list(_SEGMENT_FILTER_FIELDS)
        # Atributos de cada slot de accion
        slot_attrs = [
            "json_file", "pose_label", "pose_name", "duration",
            "entry_ratio", "exit_ratio", "interp_type",
            "rot_x", "rot_y", "rot_z", "pos_x", "pos_y", "pos_z",
        ]

        for seg in segs.segments:
            d = {a: getattr(seg, a) for a in scalar_attrs if hasattr(seg, a)}
            d["action_poses"] = [
                {a: getattr(slot, a) for a in slot_attrs}
                for slot in seg.action_poses
            ]
            # Parpadeo por segmento, filtros organicos (aislados por
            # segmento, ver JerryAnimSegment.organic) y lanzar/recoger
            # objetos -- antes tampoco se guardaban en este exportador.
            d["blink_intervals"] = _ser_blink_intervals(seg.blink_intervals)
            d["organic"] = _ser_organic(seg.organic)
            d["throws"] = _ser_throws(seg.throws)
            # Intervalos de bloqueo por bone ("dividir en partes" el
            # bloqueo, PORTADO desde alfred_animation_studio, Kebyn 2026-08-08)
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
            data["segments"].append(d)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.report({"INFO"}, f"Config Paso 3 guardada: {os.path.basename(filepath)}")
        except Exception as e:
            self.report({"ERROR"}, f"Error al guardar: {e}")
            return {"CANCELLED"}
        return {"FINISHED"}


class JRRSTSEG_OT_LoadConfig(Operator):
    bl_idname  = "jerryseg.load_config"
    bl_label   = "Cargar config Paso 3"
    bl_description = "Carga la lista de segmentos del Paso 3 desde un archivo .json"
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*_paso3.json;*.json", options={"HIDDEN"})

    def execute(self, context):
        path = bpy.path.abspath(self.filepath)
        if not os.path.isfile(path):
            self.report({"ERROR"}, f"Archivo no encontrado: {path}")
            return {"CANCELLED"}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.report({"ERROR"}, f"Error al leer: {e}")
            return {"CANCELLED"}

        segs = context.scene.jerry_segs
        segs.segments.clear()

        if "armature_name" in data:
            segs.armature_name = data["armature_name"]
        if "poses_dir" in data:
            segs.poses_dir = data["poses_dir"]

        # NOTA (Kebyn, 2026-08-06): mismo fix que en SaveConfig -- se quitaron
        # las claves fantasma "pose_start_*"/"pose_end_*" y se agregaron las
        # 44 flags "filter_*" (ver _SEGMENT_FILTER_FIELDS en config_ops.py).
        scalar_attrs = [
            "label", "frame_start", "frame_end",
            "single_coord_mode", "frame_end_auto",
            "fps", "entry_ratio", "exit_ratio",
            "export_slot_number", "export_type", "export_desc",
            "frame_mid", "pose_mid_file", "pose_mid_label",
            "interp_type", "interp_mid_to_end",
            "blend_in_frames", "blend_out_frames", "blend_strength",
            "affect_body", "affect_left_arm", "affect_right_arm",
            "affect_left_leg", "affect_right_leg", "affect_root",
            "affect_shield", "affect_spear", "enabled",
        ] + list(_SEGMENT_FILTER_FIELDS)
        slot_attrs = [
            "json_file", "pose_label", "pose_name", "duration",
            "entry_ratio", "exit_ratio", "interp_type",
            "rot_x", "rot_y", "rot_z", "pos_x", "pos_y", "pos_z",
        ]

        for seg_data in data.get("segments", []):
            seg = segs.segments.add()
            for a in scalar_attrs:
                if a in seg_data:
                    try:
                        setattr(seg, a, seg_data[a])
                    except Exception:
                        pass
            # Cargar action_poses del segmento
            seg.action_poses.clear()
            for slot_data in seg_data.get("action_poses", []):
                slot = seg.action_poses.add()
                for a in slot_attrs:
                    if a in slot_data:
                        try:
                            setattr(slot, a, slot_data[a])
                        except Exception:
                            pass
            # Parpadeo por segmento, filtros organicos (aislados por
            # segmento, ver JerryAnimSegment.organic) y lanzar/recoger
            # objetos -- antes tampoco se cargaban desde este exportador.
            _load_blink_intervals(seg.blink_intervals, seg_data.get("blink_intervals", []))
            _load_organic(seg.organic, seg_data.get("organic", {}))
            _load_throws(seg.throws, seg_data.get("throws", {}))

            # Intervalos de bloqueo por bone (PORTADO desde
            # alfred_animation_studio, Kebyn 2026-08-08)
            seg.bone_blocks.clear()
            for bb_data in seg_data.get("bone_blocks", []):
                entry = seg.bone_blocks.add()
                entry.bone_key = str(bb_data.get("bone_key", ""))
                for iv_data in bb_data.get("intervals", []):
                    iv = entry.intervals.add()
                    iv.frame_start = int(iv_data.get("frame_start", 0))
                    iv.frame_end   = int(iv_data.get("frame_end", 0))
                    iv.enabled     = bool(iv_data.get("enabled", True))

            # GARANTIA "un parpadeo por segmento como minimo" (Kebyn, 2026-08-07):
            # si el .json cargado no traia "blink_intervals" (configs viejas,
            # guardadas antes de que existiera este sistema, o exportadas desde
            # un pipeline que todavia no lo puebla), _load_blink_intervals()
            # de arriba deja seg.blink_intervals VACIO. Sin este llamado el
            # segmento quedaria sin parpadear hasta que alguien presione
            # CONCATENAR (que aplica el mismo default como red de seguridad) o
            # abra el panel y lo agregue a mano. Idempotente: si el .json SI
            # traia intervalos, _aplicar_parpadeo_default_seg no hace nada.
            _aplicar_parpadeo_default_seg(seg)

        _sync_blink_sistema2_con_segmentos(context)
        self.report({"INFO"}, f"Config Paso 3 cargada: {len(segs.segments)} segmentos")
        return {"FINISHED"}

    def invoke(self, context, event):
        segs = context.scene.jerry_segs
        self.filepath = bpy.path.abspath(segs.config_dir) if segs.config_dir else ""
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


# =============================================================================
# NUEVOS: Reproducir / Pausar / Detener segmento + Toggle enabled
# =============================================================================

class JRRSTSEG_OT_PlaySegment(Operator):
    """Salta al frame de inicio del segmento y reproduce hasta el frame fin calculado."""
    bl_idname  = "jerryseg.play_segment"
    bl_label   = "Reproducir segmento"
    bl_options = {"REGISTER"}          # SIN UNDO: UNDO interfiere con animation_play

    item_idx: bpy.props.IntProperty(default=0)

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        segs  = context.scene.jerry_segs
        if self.item_idx >= len(segs.segments):
            self.report({"ERROR"}, "Indice de segmento fuera de rango")
            return {"CANCELLED"}
        seg   = segs.segments[self.item_idx]
        scene = context.scene
        pc    = getattr(scene, "jerry_path", None)

        _n_pts      = len(pc.path_points) if pc else 0
        _is_recorrido = not seg.single_coord_mode and _n_pts >= 2
        f_start = seg.frame_start

        # Calcular frame_end del subsegmento
        if seg.single_coord_mode and seg.frame_end_auto > seg.frame_start:
            f_end = seg.frame_end_auto
        elif seg.single_coord_mode or seg.frame_end <= seg.frame_start:
            _total_fr, f_end = _calc_seg_frames(seg)
        else:
            f_end = seg.frame_end

        # Detener reproduccion previa
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()

        # ── Configurar rango y disparar reproduccion ───────────────────────────
        # En modo recorrido la animacion base (caminar/saltar) + la configuracion
        # de bones (Capa 2) se combinan mediante el boton "Reproducir recorrido"
        # del Paso 2, que escribe ambas en _grb7_preview_arm respetando los bones
        # afectados por cada segmento. Este boton solo ajusta el rango y lanza
        # la reproduccion; usa "Reproducir recorrido" del Paso 2 para ver todo.
        if _is_recorrido:
            _anim_inicio = pc.frame_inicio if pc else seg.frame_start
            _anim_fin    = getattr(pc, "anim_frame_fin", 0) if pc else 0
            if _anim_fin <= _anim_inicio:
                _anim_fin = f_end
            scene.frame_start = _anim_inicio
            scene.frame_end   = _anim_fin
            scene.frame_set(seg.frame_start)
            self.report({"INFO"},
                f"Subsegmento '{seg.label}' [{f_start}→{f_end}]. "
                f"Presiona 'Reproducir recorrido' (Paso 2) para ver recorrido + configuracion."
            )
        else:
            # ── MODO 1 COORDENADA: rango del segmento ────────────────────────
            scene.frame_start = seg.frame_start
            scene.frame_end   = f_end
            scene.frame_set(seg.frame_start)
            _total = f_end - seg.frame_start + 1
            self.report({"INFO"},
                f"Reproduciendo '{seg.label}'  frames {seg.frame_start}→{f_end}  ({_total}f)"
            )

        def _deferred_play():
            if not bpy.context.screen.is_animation_playing:
                bpy.ops.screen.animation_play()
            return None

        bpy.app.timers.register(_deferred_play, first_interval=0.01)
        return {"FINISHED"}


class JRRSTSEG_OT_PauseSegment(Operator):
    """Pausa la reproduccion (toggle play/pause)."""
    bl_idname  = "jerryseg.pause_segment"
    bl_label   = "Pausar segmento"
    bl_options = {"REGISTER"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        bpy.ops.screen.animation_play()
        return {"FINISHED"}


class JRRSTSEG_OT_StopSegment(Operator):
    """Detiene la reproduccion y vuelve al frame de inicio del segmento."""
    bl_idname  = "jerryseg.stop_segment"
    bl_label   = "Detener segmento"
    bl_options = {"REGISTER"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        segs = context.scene.jerry_segs
        # Detiene si esta reproduciendo
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
        # Vuelve al frame de inicio del segmento
        if self.item_idx < len(segs.segments):
            seg = segs.segments[self.item_idx]
            context.scene.frame_set(seg.frame_start)
        return {"FINISHED"}


class JRRSTSEG_OT_ToggleEnabled(Operator):
    """Activa o desactiva un segmento de la lista."""
    bl_idname  = "jerryseg.toggle_enabled"
    bl_label   = "Activar/desactivar segmento"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        segs = context.scene.jerry_segs
        if self.item_idx >= len(segs.segments):
            return {"CANCELLED"}
        seg = segs.segments[self.item_idx]
        seg.enabled = not seg.enabled
        return {"FINISHED"}


# =============================================================================
# CAPTURA DEL FRAME ACTUAL PARA EL FORMULARIO (modo 1 coordenada)
# =============================================================================

class JRRSTSEG_OT_SetFrameStartEdit(Operator):
    """Copia el frame actual de la timeline al campo edit_frame_start del formulario."""
    bl_idname  = "jerryseg.set_frame_start_edit"
    bl_label   = "Frame actual → Frame inicio (formulario)"
    bl_description = (
        "En modo 1 coordenada: usa el frame actual de la timeline "
        "como frame de inicio del nuevo segmento"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        segs = context.scene.jerry_segs
        segs.edit_frame_start = context.scene.frame_current
        self.report({"INFO"}, f"Frame inicio del formulario -> {context.scene.frame_current}")
        return {"FINISHED"}


# =============================================================================
# PICK POSE PARA SEGMENTO EXISTENTE (con item_idx)
# =============================================================================

# NOTA (Kebyn, 2026-08-06): se elimino el sistema de Pose INICIO / Pose FIN
# por-segmento (_PickPoseSegBase, JRRSTSEG_OT_PickPoseStartSeg/EndSeg) --
# logica de versiones antiguas. El primer y ultimo item de seg.action_poses
# cumplen ahora ese rol dentro de JRRST_OT_Concatenate (operators_anim.py).


# =============================================================================
# OPERADORES DE POSES INTERMEDIAS (ACTION POSES) POR SEGMENTO
# Equivalentes a jerryst.add/edit/remove/move_action_pose pero escriben
# directamente en seg.action_poses del segmento activo (o item_idx).
# =============================================================================

class JRRSTSEG_OT_AddActionPoseSeg(Operator):
    bl_idname    = "jerryseg.add_action_pose_seg"
    bl_label     = "Agregar pose intermedia al segmento"
    bl_description = "Agrega una pose de accion a este segmento"
    bl_options   = {"REGISTER", "UNDO"}
    item_idx:    IntProperty(default=-1)

    json_file:   EnumProperty(name="Archivo JSON", items=_enum_json_files)
    pose_index:  EnumProperty(name="Pose",         items=_enum_poses_from_self_json)
    duration:    IntProperty(name="Duracion (frames)", default=20, min=2, soft_max=300)
    rot_x:       FloatProperty(name="Rot X (grados)", default=0.0)
    rot_y:       FloatProperty(name="Rot Y (grados)", default=0.0)
    rot_z:       FloatProperty(name="Rot Z (grados)", default=0.0)
    pos_x:       FloatProperty(name="Pos X", default=0.0)
    pos_y:       FloatProperty(name="Pos Y", default=0.0)
    pos_z:       FloatProperty(name="Pos Z", default=0.0)
    interp_type: EnumProperty(name="Interpolacion", items=INTERP_TYPE_ITEMS, default="SMOOTH")
    # PORTADO desde alfred_animation_studio (Kebyn, 2026-08-06): permite
    # elegir el frame de inicio (absoluto, dentro del rango del segmento)
    # de esta pose en vez de que se apile automaticamente tras la anterior.
    manual_start:    BoolProperty(
        name="Elegir frame de inicio",
        default=False,
        description=(
            "Si esta activo, tu eliges el frame (absoluto, dentro del rango "
            "del segmento) en que empieza esta pose, en vez de que se apile "
            "automaticamente despues de la pose anterior"
        ),
    )
    frame_abs_start: IntProperty(
        name="Frame de inicio", default=0, min=0,
        description="Frame absoluto (dentro del rango del segmento) en que debe empezar esta pose",
    )

    def _get_seg(self, context):
        segs = context.scene.jerry_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if 0 <= idx < len(segs.segments):
            return segs.segments[idx]
        return None

    def invoke(self, context, event):
        seg = self._get_seg(context)
        if seg and seg.action_poses:
            last = seg.action_poses[-1]
            self.rot_x = last.rot_x
            self.rot_y = last.rot_y
            self.rot_z = last.rot_z
        if seg is not None:
            # Sugerencia por defecto: si el usuario activa "Elegir frame de
            # inicio", que arranque mostrando donde caeria automaticamente
            # (frame_start del segmento + duracion acumulada de las poses
            # ya agregadas), no en 0.
            _starts = resolve_pose_start_frames(list(seg.action_poses), seg.frame_start)
            if seg.action_poses:
                self.frame_abs_start = _starts[-1] + max(1, int(seg.action_poses[-1].duration))
            else:
                self.frame_abs_start = seg.frame_start
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        layout = self.layout
        _pc = getattr(context.scene, "jerry_path", None)
        _modo_recorrido = _pc is not None and len(_pc.path_points) > 1
        seg = self._get_seg(context)
        layout.label(text="Paso 1 -- Elige el archivo JSON:")
        layout.prop(self, "json_file", text="")
        layout.separator()
        layout.label(text="Paso 2 -- Elige la pose de accion:")
        layout.prop(self, "pose_index", text="")
        layout.separator()
        layout.label(text="Paso 3 -- Duracion de este segmento:")
        layout.prop(self, "duration", text="Frames")
        layout.separator()
        box_fs = layout.box()
        box_fs.label(text="Paso 4 -- Frame de inicio dentro del segmento:", icon="TIME")
        box_fs.prop(self, "manual_start")
        if self.manual_start:
            row_fs = box_fs.row()
            row_fs.prop(self, "frame_abs_start")
            if seg is not None:
                row_fs.label(text=f"  (rango del segmento: {seg.frame_start} → {seg.frame_end})")
        else:
            box_fs.label(text="  Automatico: se apila justo tras la pose anterior.", icon="INFO")
        layout.separator()
        box = layout.box()
        box.label(text="Paso 5 -- Tipo de interpolacion:", icon="IPO_BEZIER")
        box.prop(self, "interp_type", text="")
        layout.separator()
        if _modo_recorrido:
            box_lock = layout.box()
            box_lock.label(text="Posicion y Rotacion del Root: BLOQUEADAS", icon="LOCKED")
            box_lock.label(text="  El recorrido (Paso 2) controla XYZ y orientacion del root", icon="INFO")
        else:
            box2 = layout.box()
            box2.label(text="Root (Jerry): se toma del .json de la pose elegida", icon="OBJECT_ORIGIN")
            box2.label(text="  (igual que los huesos). Se ajusta despues con el Empty", icon="BLANK1")
            box2.label(text="  'jerry' + 'Guardar cambios'.", icon="BLANK1")

    def execute(self, context):
        if self.json_file == "NONE":
            self.report({"WARNING"}, "No hay archivos JSON en la carpeta de poses")
            return {"CANCELLED"}
        st  = context.scene.jerryst
        seg = self._get_seg(context)
        if seg is None:
            self.report({"WARNING"}, "Segmento invalido"); return {"CANCELLED"}
        jf    = _json_file_from_index(self, context)
        idx   = int(self.pose_index)
        fp    = os.path.join(bpy.path.abspath(st.poses_dir), jf)
        poses = load_json_poses(fp)
        name  = poses[idx].get("label", "?") if poses and idx < len(poses) else "?"
        # ── Root: siempre se toma del .json de la pose (posicion Y rotacion),
        # igual que los huesos. Sin prefill de "la pose anterior", sin tipeo
        # manual. Antes solo se traia la rotacion (get_root_rotation_from_record)
        # y la posicion se quedaba fija en 0.0, causando que el personaje
        # saltara a (0,0,0) al concatenar. ──
        rec = get_pose_record(st.poses_dir, jf, idx)
        if rec:
            _root = get_root_transform_from_record(rec)
            self.pos_x, self.pos_y, self.pos_z = _root["pos"]
            self.rot_x, self.rot_y, self.rot_z = _root["rot_deg"]
        item             = seg.action_poses.add()
        item.pose_name   = name
        item.json_file   = jf
        item.pose_index  = idx
        item.duration    = self.duration
        item.rot_x       = self.rot_x
        item.rot_y       = self.rot_y
        item.rot_z       = self.rot_z
        item.pos_x       = self.pos_x
        item.pos_y       = self.pos_y
        item.pos_z       = self.pos_z
        item.interp_type = self.interp_type
        item.manual_start = self.manual_start
        if self.manual_start:
            # Validar que no invada a la pose anterior (la que era la ultima
            # ANTES de agregar esta, ya que 'item' recien se agrego al final).
            _prev_poses = list(seg.action_poses)[:-1]
            _min_allowed = seg.frame_start
            if _prev_poses:
                _prev_starts = resolve_pose_start_frames(_prev_poses, seg.frame_start)
                _min_allowed = _prev_starts[-1] + max(1, int(_prev_poses[-1].duration))
            if self.frame_abs_start < _min_allowed:
                self.report({"WARNING"},
                    f"Frame de inicio {self.frame_abs_start} invade a la pose anterior "
                    f"(termina en {_min_allowed - 1}); se ignora y se usa el apilado automatico.")
                item.manual_start = False
                item.frame_abs_start = 0
            else:
                item.frame_abs_start = self.frame_abs_start
        seg.action_poses_idx = len(seg.action_poses) - 1
        self.report({"INFO"}, f"Pose agregada al segmento: '{name}'  [{jf}]  interp={self.interp_type}")
        return {"FINISHED"}


# =============================================================================
# EXTRAER POSE RAPIDA (debajo del sistema de agregar poses, dentro de cada
# segmento). PORTADO desde alfred_animation_studio (Kebyn, 2026-09-04):
# copia el sistema "Extraer pose rapida (bones actuales)" de Alfred
# (ALFREDSEG_OT_QuickPoseExtract / ALFREDSEG_OT_QuickPoseImport), adaptado al
# armature/rig de Jerry (Dog_001_rig) y al formato de get_root_transform_from_record
# de este addon (dict {"pos":..,"rot_deg":..} en vez de tupla). Ciclo de 2 clicks:
#   1) Guardar  -> detecta el armature de Jerry automaticamente
#                  (_find_jerry_armature), nombra la pose sola segun que
#                  huesos se movieron respecto al rest pose, y la guarda
#                  como .json en la carpeta de poses (mismo formato
#                  {"poses": [...]} que usa el resto del addon).
#   2) Importar -> agrega esa pose recien guardada a seg.action_poses de
#                  ESTE segmento (mismo criterio que
#                  JRRSTSEG_OT_AddActionPoseSeg.execute) y limpia el
#                  "pendiente" (scene.jerryst.quickpose_pending_*) para el
#                  siguiente ciclo.
# =============================================================================

def _find_jerry_armature(context):
    """
    Resuelve el armature de Jerry de forma fiable:
      1) Usa el mismo resolver que CONCATENAR (_resolve_armature), basado en
         scene.jerry_segs.armature_name — la fuente de verdad configurada
         por el usuario en el panel de Segmentos.
      2) Si eso falla, intenta con scene.jerryst.armature_name.
      3) Como ultimo recurso, busca por nombre "Dog_001_rig" / "jerry" en la
         escena (puede ser ambiguo si hay armatures secundarios, asi que es
         solo un fallback).
    """
    scene   = context.scene
    seg_cfg = getattr(scene, "jerry_segs", None)
    if seg_cfg is not None:
        arm_obj = _resolve_armature(seg_cfg, scene)
        if arm_obj is not None:
            return arm_obj

    st = getattr(scene, "jerryst", None)
    if st is not None and getattr(st, "armature_name", ""):
        arm_obj = scene.objects.get(st.armature_name)
        if arm_obj and arm_obj.type == "ARMATURE":
            return arm_obj

    arm_obj = None
    for ob in context.scene.objects:
        if ob.type == "ARMATURE" and ("jerry" in ob.name.lower() or "dog_001_rig" in ob.name.lower()):
            arm_obj = ob
            break
    if arm_obj is None:
        for ob in context.scene.objects:
            if ob.type == "ARMATURE":
                arm_obj = ob
                break
    return arm_obj


def _find_jerry_root_empty(context):
    """Resuelve el Empty Root 'jerry' (el mismo que usa el resto del addon
    para el desplazamiento del personaje), para leer su transform ACTUAL
    y no depender de datos que la pose rapida nunca guarda."""
    root_empty = context.scene.objects.get(ROOT_NAME)
    if root_empty is not None and root_empty.type == "EMPTY":
        return root_empty
    return None


def _quickpose_generate_label(armature, max_bones=3):
    """
    Nombra la pose segun los huesos que el usuario movio respecto al rest
    pose (location=0, rotacion=identidad). Se ordenan por magnitud de
    movimiento (traslacion + rotacion combinadas) y se usan los N con mayor
    movimiento para armar el nombre. Sin movimiento detectado -> "pose_neutra".
    """
    scored = []
    for pb in armature.pose.bones:
        loc_mag = pb.location.length
        if pb.rotation_mode == 'QUATERNION':
            q = pb.rotation_quaternion
            w = max(-1.0, min(1.0, q.w))
            ang_deg = math.degrees(2 * math.acos(abs(w)))
        else:
            e = pb.rotation_euler
            ang_deg = math.degrees(abs(e.x) + abs(e.y) + abs(e.z))
        # Ponderacion simple: la rotacion (en grados) pesa mas que la
        # traslacion (normalmente pequeña en huesos de pose), pero ambas
        # cuentan para decidir que huesos "se movieron mas".
        score = ang_deg + loc_mag * 10
        if ang_deg > 0.5 or loc_mag > 0.001:
            scored.append((score, pb.name))
    if not scored:
        return "pose_neutra"
    scored.sort(key=lambda t: -t[0])
    top_names = [name for _, name in scored[:max_bones]]
    return "_".join(top_names)


class JRRSTSEG_OT_QuickPoseExtract(Operator):
    """Captura la pose actual del armature de Jerry y la guarda como .json,
    nombrandola sola segun los huesos movidos. Reutilizar con 'Importar'
    para agregarla a la lista de poses del segmento."""
    bl_idname    = "jerryseg.quickpose_extract"
    bl_label     = "Guardar pose (bones actuales)"
    bl_description = (
        "Detecta el armature de Jerry, extrae la pose del frame actual "
        "y la guarda en la carpeta de poses con un nombre automatico "
        "segun los huesos que moviste"
    )
    bl_options   = {"REGISTER", "UNDO"}

    def execute(self, context):
        st       = context.scene.jerryst
        scene    = context.scene
        armature = _find_jerry_armature(context)
        if armature is None or armature.type != "ARMATURE":
            self.report({"ERROR"}, "No se encontro el armature de Jerry en la escena")
            return {"CANCELLED"}

        context.view_layer.update()
        frame = scene.frame_current
        label = _quickpose_generate_label(armature)

        bones_data = {}
        for pb in armature.pose.bones:
            rot_e = pb.rotation_euler
            rot_q = pb.rotation_quaternion
            local_space = {
                "location": {
                    "x": round(pb.location.x, 6),
                    "y": round(pb.location.y, 6),
                    "z": round(pb.location.z, 6),
                },
                "rotation_euler_rad": {
                    "x": round(rot_e.x, 6), "y": round(rot_e.y, 6), "z": round(rot_e.z, 6),
                },
                "rotation_euler_deg": {
                    "x": round(math.degrees(rot_e.x), 4),
                    "y": round(math.degrees(rot_e.y), 4),
                    "z": round(math.degrees(rot_e.z), 4),
                },
                "rotation_quaternion": {
                    "w": round(rot_q.w, 6), "x": round(rot_q.x, 6),
                    "y": round(rot_q.y, 6), "z": round(rot_q.z, 6),
                },
                "scale": {
                    "x": round(pb.scale.x, 6), "y": round(pb.scale.y, 6), "z": round(pb.scale.z, 6),
                },
            }
            bones_data[pb.name] = {
                "parent":    pb.parent.name if pb.parent else None,
                "connected": pb.bone.use_connect,
                "local_space": local_space,
                "rotation_mode": pb.rotation_mode,
                "raw_rotation_euler_deg": local_space["rotation_euler_deg"],
                "raw_rotation_quaternion": local_space["rotation_quaternion"]
                    if pb.rotation_mode == "QUATERNION" else None,
                "raw_location": local_space["location"],
                "raw_scale":    local_space["scale"],
            }

        record = {
            "label":           label,
            "frame":           frame,
            "armature":        armature.name,
            "character":       armature.parent.name if armature.parent else armature.name,
            "timestamp":       datetime.datetime.now().isoformat(),
            "blender_version": bpy.app.version_string,
            "file":            os.path.basename(bpy.data.filepath) if bpy.data.filepath else "unsaved",
            "bone_count":      len(bones_data),
            "bones":           bones_data,
        }

        out_dir = bpy.path.abspath(st.poses_dir)
        os.makedirs(out_dir, exist_ok=True)
        _FORBIDDEN = set('/\\:*?"<>|')
        safe_label = "".join(c if c not in _FORBIDDEN else "_" for c in label).strip().replace(" ", "_")
        if not safe_label:
            safe_label = "pose_sin_nombre"

        # Nombre de archivo unico por captura (a diferencia de "Extraer Nueva
        # Pose", que ACUMULA varias poses bajo el mismo nombre elegido a
        # mano): asi cada click de "Guardar" queda en su propio .json, sin
        # ambiguedad de que registro es "el recien guardado" al Importar.
        base_filename = f"{safe_label}_f{frame}"
        filename = f"{base_filename}.json"
        filepath = os.path.join(out_dir, filename)
        _suffix = 2
        while os.path.isfile(filepath):
            filename = f"{base_filename}_{_suffix}.json"
            filepath = os.path.join(out_dir, filename)
            _suffix += 1

        data = {"poses": [record]}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        st.quickpose_pending_file  = filename
        st.quickpose_pending_index = 0
        st.quickpose_pending_label = label

        self.report({"INFO"},
            f"Pose '{label}' (frame {frame}) guardada -> {filename}. Presiona 'Importar' para agregarla a la lista.")
        return {"FINISHED"}


class JRRSTSEG_OT_QuickPoseImport(Operator):
    """Importa la pose recien guardada por 'Guardar pose (bones actuales)'
    a la lista de poses de accion de este segmento, y limpia el pendiente."""
    bl_idname    = "jerryseg.quickpose_import"
    bl_label     = "Importar a la lista de poses"
    bl_description = "Agrega la pose recien guardada a la lista de este segmento"
    bl_options   = {"REGISTER", "UNDO"}
    item_idx:    IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        return bool(context.scene.jerryst.quickpose_pending_file)

    def _get_seg(self, context):
        segs = context.scene.jerry_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if 0 <= idx < len(segs.segments):
            return segs.segments[idx]
        return None

    def execute(self, context):
        st  = context.scene.jerryst
        seg = self._get_seg(context)
        if seg is None:
            self.report({"WARNING"}, "Segmento invalido")
            return {"CANCELLED"}
        jf  = st.quickpose_pending_file
        idx = st.quickpose_pending_index
        if not jf:
            self.report({"WARNING"}, "Primero presiona 'Guardar pose (bones actuales)'")
            return {"CANCELLED"}

        # Refrescar la lista de poses (mismo criterio que JRRST_OT_ImportPose,
        # via refresh_poses) para que el nuevo .json quede disponible en los
        # selectores/enums.
        bpy.ops.jerryst.refresh_poses()

        rec = get_pose_record(st.poses_dir, jf, idx)
        if not rec:
            self.report({"ERROR"}, f"No se pudo leer la pose recien guardada ({jf})")
            return {"CANCELLED"}

        # BUGFIX (Kebyn, 2026-09-04): get_root_transform_from_record() busca
        # una entrada "jerry"/"Dog_001_rig" dentro de rec["bones"], pero
        # JRRSTSEG_OT_QuickPoseExtract SOLO captura huesos del armature (por
        # diseno: el Root/Empty se ajusta aparte, ver cabecera de este
        # bloque). Esa entrada nunca existe en una pose rapida, asi que
        # get_root_transform_from_record() caia siempre a su default
        # (0,0,0)/(0,0,0), y ese cero se guardaba en item.pos_x/y/z. Como
        # CONCATENAR usa item.pos_x/y/z como punto de interpolacion del
        # Empty "jerry" (ver arm_pos_act en operators_anim.py), el personaje
        # terminaba viajando al origen en cada pose rapida importada.
        #
        # Fix: heredar la posicion/rotacion ACTUAL del Empty "jerry" en
        # escena (la pose rapida no debe mover el Root), en vez de la que
        # (no) haya en el record.
        root_empty = _find_jerry_root_empty(context)
        if root_empty is not None:
            _px, _py, _pz = root_empty.location.x, root_empty.location.y, root_empty.location.z
            _rot = root_empty.rotation_euler
            _rx = math.degrees(_rot.x)
            _ry = math.degrees(_rot.y)
            _rz = math.degrees(_rot.z)
        else:
            # Ultimo recurso si no se encuentra el Empty: no inventar un
            # (0,0,0) silencioso, heredar de la ultima pose ya cargada en
            # este segmento (si hay), para no cortar la continuidad.
            if len(seg.action_poses) > 0:
                _prev = seg.action_poses[-1]
                _px, _py, _pz = _prev.pos_x, _prev.pos_y, _prev.pos_z
                _rx, _ry, _rz = _prev.rot_x, _prev.rot_y, _prev.rot_z
            else:
                _px = _py = _pz = 0.0
                _rx = _ry = _rz = 0.0
            self.report({"WARNING"},
                f"No se encontro el Empty '{ROOT_NAME}' en la escena; se "
                "heredo la posicion de la pose anterior en vez de (0,0,0).")

        item              = seg.action_poses.add()
        item.pose_name    = st.quickpose_pending_label or rec.get("label", "?")
        item.json_file    = jf
        item.pose_index   = idx
        item.duration     = 20
        item.rot_x, item.rot_y, item.rot_z = _rx, _ry, _rz
        item.pos_x, item.pos_y, item.pos_z = _px, _py, _pz
        item.interp_type  = "SMOOTH"
        item.manual_start = False

        seg.action_poses_idx = len(seg.action_poses) - 1

        nombre_importada = item.pose_name
        # Limpiar el pendiente: listo para el siguiente ciclo.
        st.quickpose_pending_file  = ""
        st.quickpose_pending_index = 0
        st.quickpose_pending_label = ""

        self.report({"INFO"},
            f"Pose '{nombre_importada}' importada al segmento '{seg.label}'")
        return {"FINISHED"}


class JRRSTSEG_OT_EditActionPoseSeg(Operator):
    bl_idname    = "jerryseg.edit_action_pose_seg"
    bl_label     = "Editar pose intermedia del segmento"
    bl_options   = {"REGISTER", "UNDO"}
    item_idx:    IntProperty(default=-1)

    duration:    IntProperty(name="Duracion (frames)", default=20, min=2, soft_max=300)
    interp_type: EnumProperty(name="Interpolacion", items=INTERP_TYPE_ITEMS, default="SMOOTH")
    # PORTADO desde alfred_animation_studio (Kebyn, 2026-08-06).
    manual_start:    BoolProperty(
        name="Elegir frame de inicio",
        default=False,
        description=(
            "Si esta activo, tu eliges el frame (absoluto, dentro del rango "
            "del segmento) en que empieza esta pose, en vez de que se apile "
            "automaticamente despues de la pose anterior"
        ),
    )
    frame_abs_start: IntProperty(
        name="Frame de inicio", default=0, min=0,
        description="Frame absoluto (dentro del rango del segmento) en que debe empezar esta pose",
    )

    def _get_seg(self, context):
        segs = context.scene.jerry_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if 0 <= idx < len(segs.segments):
            return segs.segments[idx]
        return None

    def invoke(self, context, event):
        seg = self._get_seg(context)
        if seg and seg.action_poses and 0 <= seg.action_poses_idx < len(seg.action_poses):
            item = seg.action_poses[seg.action_poses_idx]
            self.duration = item.duration
            self.interp_type = item.interp_type
            self.manual_start = item.manual_start
            if item.manual_start and item.frame_abs_start > 0:
                self.frame_abs_start = item.frame_abs_start
            else:
                _starts = resolve_pose_start_frames(list(seg.action_poses), seg.frame_start)
                self.frame_abs_start = _starts[seg.action_poses_idx]
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        seg = self._get_seg(context)
        layout.prop(self, "duration")
        layout.separator()
        box_fs = layout.box()
        box_fs.label(text="Frame de inicio dentro del segmento:", icon="TIME")
        box_fs.prop(self, "manual_start")
        if self.manual_start:
            row_fs = box_fs.row()
            row_fs.prop(self, "frame_abs_start")
            if seg is not None:
                row_fs.label(text=f"  (rango del segmento: {seg.frame_start} → {seg.frame_end})")
        else:
            box_fs.label(text="  Automatico: se apila justo tras la pose anterior.", icon="INFO")
        layout.separator()
        box = layout.box()
        box.label(text="Tipo de interpolacion:", icon="IPO_BEZIER")
        box.prop(self, "interp_type", text="")
        layout.separator()
        box2 = layout.box()
        box2.label(text="El Root se edita con el Empty 'jerry' + 'Editar pose...'", icon="INFO")
        box2.label(text="  + 'Guardar cambios' (no se tipea aqui).", icon="BLANK1")

    def execute(self, context):
        seg = self._get_seg(context)
        if seg and seg.action_poses and 0 <= seg.action_poses_idx < len(seg.action_poses):
            item = seg.action_poses[seg.action_poses_idx]
            item.duration = self.duration
            item.interp_type = self.interp_type
            item.manual_start = self.manual_start
            if self.manual_start:
                _others = [p for _i, p in enumerate(seg.action_poses) if _i != seg.action_poses_idx and _i < seg.action_poses_idx]
                _min_allowed = seg.frame_start
                if _others:
                    _prev_starts = resolve_pose_start_frames(_others, seg.frame_start)
                    _min_allowed = _prev_starts[-1] + max(1, int(_others[-1].duration))
                if self.frame_abs_start < _min_allowed:
                    self.report({"WARNING"},
                        f"Frame de inicio {self.frame_abs_start} invade a la pose anterior "
                        f"(termina en {_min_allowed - 1}); se ignora y se usa el apilado automatico.")
                    item.manual_start = False
                    item.frame_abs_start = 0
                else:
                    item.frame_abs_start = self.frame_abs_start
            else:
                item.frame_abs_start = 0
        return {"FINISHED"}


class JRRSTSEG_OT_DuplicateActionPoseSeg(Operator):
    """Copia la pose de accion seleccionada y la agrega al final de la lista
    de este segmento, para no tener que reimportar la misma pose a mano
    (boton 'copiar' en la barra lateral de Acciones (slots)).
    PORTADO desde alfred_animation_studio (ALFREDSEG_OT_DuplicateActionPoseSeg,
    Kebyn, 2026-08-06)."""
    bl_idname    = "jerryseg.duplicate_action_pose_seg"
    bl_label     = "Copiar pose intermedia del segmento"
    bl_description = "Duplica la pose seleccionada y la agrega al final de la lista"
    bl_options   = {"REGISTER", "UNDO"}
    item_idx:    IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.jerry_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)):
            return {"CANCELLED"}
        seg = segs.segments[idx]
        if not seg.action_poses or not (0 <= seg.action_poses_idx < len(seg.action_poses)):
            self.report({"WARNING"}, "Selecciona una pose de la lista para copiar")
            return {"CANCELLED"}

        # Capturar los valores ANTES de action_poses.add(): agregar un item
        # a la coleccion puede invalidar la referencia 'src' que ya
        # teniamos, asi que se leen a variables locales primero.
        src = seg.action_poses[seg.action_poses_idx]
        _json_file    = src.json_file
        _pose_label   = src.pose_label
        _pose_name    = src.pose_name
        _duration     = src.duration
        _entry_ratio  = src.entry_ratio
        _exit_ratio   = src.exit_ratio
        _interp_type  = src.interp_type
        _rot_x, _rot_y, _rot_z = src.rot_x, src.rot_y, src.rot_z
        _pos_x, _pos_y, _pos_z = src.pos_x, src.pos_y, src.pos_z

        new_item = seg.action_poses.add()
        new_item.json_file    = _json_file
        new_item.pose_label   = _pose_label
        new_item.pose_name    = _pose_name
        new_item.duration     = _duration
        new_item.entry_ratio  = _entry_ratio
        new_item.exit_ratio   = _exit_ratio
        new_item.interp_type  = _interp_type
        new_item.rot_x, new_item.rot_y, new_item.rot_z = _rot_x, _rot_y, _rot_z
        new_item.pos_x, new_item.pos_y, new_item.pos_z = _pos_x, _pos_y, _pos_z
        # Siempre se apila automaticamente al final (no hereda un frame de
        # inicio manual del original, si tenia uno, para no invadir la
        # pose que ahora queda justo antes que ella en la lista).
        new_item.manual_start    = False
        new_item.frame_abs_start = 0

        seg.action_poses_idx = len(seg.action_poses) - 1
        self.report({"INFO"},
            f"Pose '{_pose_name or _json_file}' copiada y agregada al final del segmento")
        return {"FINISHED"}


class JRRSTSEG_OT_RemoveActionPoseSeg(Operator):
    bl_idname  = "jerryseg.remove_action_pose_seg"
    bl_label   = "Eliminar pose intermedia del segmento"
    bl_options = {"REGISTER", "UNDO"}
    item_idx:  IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.jerry_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)): return {"CANCELLED"}
        seg = segs.segments[idx]
        if seg.action_poses and 0 <= seg.action_poses_idx < len(seg.action_poses):
            seg.action_poses.remove(seg.action_poses_idx)
            seg.action_poses_idx = max(0, seg.action_poses_idx - 1)
        return {"FINISHED"}


class JRRSTSEG_OT_MoveActionPoseSeg(Operator):
    bl_idname  = "jerryseg.move_action_pose_seg"
    bl_label   = "Mover pose intermedia del segmento"
    bl_options = {"REGISTER", "UNDO"}
    item_idx:  IntProperty(default=-1)
    direction: EnumProperty(items=[("UP","Arriba",""),("DOWN","Abajo","")])

    def execute(self, context):
        segs = context.scene.jerry_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)): return {"CANCELLED"}
        seg  = segs.segments[idx]
        pidx = seg.action_poses_idx
        lst  = seg.action_poses
        if self.direction == "UP" and pidx > 0:
            lst.move(pidx, pidx-1); seg.action_poses_idx = pidx-1
        elif self.direction == "DOWN" and pidx < len(lst)-1:
            lst.move(pidx, pidx+1); seg.action_poses_idx = pidx+1
        return {"FINISHED"}


# =============================================================================
# TOGGLE SHOW_CONFIG DE UN SEGMENTO
# =============================================================================

class JRRSTSEG_OT_ToggleConfig(Operator):
    """Muestra u oculta la configuracion de poses de un segmento."""
    bl_idname  = "jerryseg.toggle_config"
    bl_label   = "Configurar segmento"
    bl_options = {"REGISTER", "UNDO"}
    item_idx:  IntProperty(default=0)

    def execute(self, context):
        segs = context.scene.jerry_segs
        idx  = self.item_idx
        if 0 <= idx < len(segs.segments):
            segs.segments[idx].show_config = not segs.segments[idx].show_config
            # FIX (Kebyn, 2026-08-12): sincronizar segs.active_index con el
            # segmento que el usuario acaba de expandir/seleccionar en la
            # lista. Sin esto, active_index se queda pegado en el ultimo
            # valor que le puso una creacion/duplicado/eliminado (ver
            # JRRSTSEG_OT_Add* / Duplicate / Remove, que si lo actualizan) y
            # TODOS los operadores que operan sobre "el segmento activo" --
            # CONCATENAR (jerryst.concatenate), oscilaciones e intervalos
            # con item_idx=-1, etc. -- terminan actuando siempre sobre ese
            # segmento viejo (tipicamente el ultimo creado) sin importar
            # cual panel abrio o edito el usuario despues.
            segs.active_index = idx
        return {"FINISHED"}


# =============================================================================
# PARPADEO POR SEGMENTO — Add/Remove
# =============================================================================
# PORTADO desde alfred_animation_studio (Kebyn, 2026-08-05): version
# simplificada de alfst.blink_interval_add/remove, adaptada al patron
# item_idx=-1 (por defecto opera sobre el segmento ACTIVO) que ya usan el
# resto de los operadores de listas por-segmento de este archivo
# (JRRSTSEG_OT_AddActionPoseSeg, etc.), en vez de duplicar un sistema de
# UIList + active_index propio solo para esta lista.

class JRRSTSEG_OT_BlinkIntervalAddSeg(Operator):
    bl_idname  = "jerryseg.blink_interval_add_seg"
    bl_label   = "Agregar intervalo de parpadeo"
    bl_description = "Agrega un intervalo de parpadeo automatico a este segmento"
    bl_options = {"REGISTER", "UNDO"}
    item_idx:  IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.jerry_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "Segmento invalido")
            return {"CANCELLED"}
        seg = segs.segments[idx]
        bi = seg.blink_intervals.add()
        bi.label        = f"Parpadeo {len(seg.blink_intervals)}"
        bi.frame_start  = seg.frame_start
        bi.frame_end    = max(seg.frame_end, seg.frame_start + 9)
        bi.blink_count  = 1
        bi.blink_duration = 9
        bi.enabled      = True
        seg.blink_interval_idx = len(seg.blink_intervals) - 1
        return {"FINISHED"}


class JRRSTSEG_OT_BlinkIntervalRemoveSeg(Operator):
    bl_idname  = "jerryseg.blink_interval_remove_seg"
    bl_label   = "Quitar intervalo de parpadeo"
    bl_description = "Elimina el intervalo de parpadeo seleccionado de este segmento"
    bl_options = {"REGISTER", "UNDO"}
    item_idx:  IntProperty(default=-1)
    # Indice EXPLICITO del intervalo a borrar dentro de seg.blink_intervals.
    # FIX (Kebyn + Claude, 2026-08-05): la version original de este operador
    # leia seg.blink_interval_idx, que el panel tenia que "preparar" mutando
    # esa propiedad en pleno draw() -- exactamente el patron que otro
    # comentario de este mismo archivo (ver "NOTA: NO mutar slot.rating_query
    # aqui") advierte que hace que Blender aborte el panel en silencio. Ahora
    # el boton de cada fila pasa su propio indice directamente, sin mutar
    # nada durante el dibujado.
    bi_idx:    IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.jerry_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "Segmento invalido")
            return {"CANCELLED"}
        seg = segs.segments[idx]
        bidx = self.bi_idx if self.bi_idx >= 0 else seg.blink_interval_idx
        if 0 <= bidx < len(seg.blink_intervals):
            seg.blink_intervals.remove(bidx)
            seg.blink_interval_idx = max(0, min(bidx, len(seg.blink_intervals) - 1))
        return {"FINISHED"}


class JRRSTSEG_OT_AddBoneInterval(Operator):
    """PORTADO desde alfred_animation_studio (ALFREDSEG_OT_AddBoneInterval,
    Kebyn, 2026-08-08): agrega un nuevo intervalo de bloqueo de frames para
    un bone especifico del Filtro de bones de este segmento (permite
    "dividir en partes" el bloqueo: ej. bloqueado 60-100 y otra vez
    500-630, independiente entre si)."""
    bl_idname  = "jerryseg.add_bone_interval"
    bl_label   = "Agregar intervalo de bloqueo"
    bl_description = "Agrega un intervalo de frames en el que este bone quedara bloqueado"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: IntProperty(default=-1)
    bone_key: StringProperty(default="")

    def execute(self, context):
        segs = context.scene.jerry_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "Segmento invalido")
            return {"CANCELLED"}
        seg   = segs.segments[idx]
        entry = _get_bone_block_entry(seg, self.bone_key, create=True)

        # Sugerir un rango que continue despues del ultimo intervalo existente
        if len(entry.intervals):
            last = entry.intervals[-1]
            new_start = last.frame_end + 1
        else:
            new_start = seg.frame_start
        new_end = new_start + 10

        iv = entry.intervals.add()
        iv.frame_start = max(0, new_start)
        iv.frame_end   = max(iv.frame_start + 1, new_end)
        entry.intervals_idx = len(entry.intervals) - 1
        return {"FINISHED"}


class JRRSTSEG_OT_RemoveBoneInterval(Operator):
    """PORTADO desde alfred_animation_studio (ALFREDSEG_OT_RemoveBoneInterval,
    Kebyn, 2026-08-08): elimina un intervalo de bloqueo especifico de un bone."""
    bl_idname  = "jerryseg.remove_bone_interval"
    bl_label   = "Eliminar intervalo de bloqueo"
    bl_options = {"REGISTER", "UNDO"}

    item_idx:     IntProperty(default=-1)
    bone_key:     StringProperty(default="")
    interval_idx: IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.jerry_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)):
            return {"CANCELLED"}
        seg   = segs.segments[idx]
        entry = _get_bone_block_entry(seg, self.bone_key, create=False)
        if entry is None or not (0 <= self.interval_idx < len(entry.intervals)):
            return {"CANCELLED"}
        entry.intervals.remove(self.interval_idx)
        entry.intervals_idx = max(0, min(entry.intervals_idx, len(entry.intervals) - 1))
        return {"FINISHED"}


# =============================================================================
# REGISTRO
# =============================================================================

seg_operator_classes = (
    JRRSTSEG_OT_Add,
    JRRSTSEG_OT_Remove,
    JRRSTSEG_OT_Move,
    JRRSTSEG_OT_Duplicate,
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
