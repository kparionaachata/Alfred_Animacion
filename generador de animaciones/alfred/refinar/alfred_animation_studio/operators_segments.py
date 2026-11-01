# -*- coding: utf-8 -*-
"""
operators_segments.py — Alfred Animation Studio v2.0
Paso 3: Segmentos de refinado sobre la animacion generada por Pasos 1+2.

LOGICA CENTRAL:
  La animacion de recorrido (generada por path_recorder) ya existe en la
  timeline con sus fcurves de bones y de root. El Paso 3 NO la borra ni la
  reemplaza: la modula.

  Por cada AlfredAnimSegment el operador APLICAR_SEGMENTOS:
    1. Lee los fcurves ya existentes del armature en el rango [frame_start, frame_end].
    2. Carga las poses .json de inicio / intermedio / final.
    3. Para cada frame del segmento calcula:
         t  = posicion normalizada [0,1] dentro del segmento
         pose_valor = interpolar( pose_start, pose_mid, pose_end, t, interp_type )
         blend  = calcular_alpha( t, blend_in_frames, blend_out_frames ) * blend_strength
         nuevo  = lerp( fcurve_existente[frame], pose_valor, blend )
    4. Escribe el nuevo valor directamente en el keyframe existente del fcurve.
       Si no hay keyframe en ese frame lo inserta.

  El resultado es que la personaje sigue su recorrido (traslacion del root, ciclo de
  caminar/saltar) pero los bones seleccionados adoptan la pose configurada
  durante ese intervalo, con transiciones suaves de entrada y salida.

OPERADORES:
  ALFREDSEG_OT_Add            — agrega un segmento nuevo
  ALFREDSEG_OT_Remove         — elimina el segmento activo
  ALFREDSEG_OT_Move           — sube/baja el segmento activo
  ALFREDSEG_OT_Duplicate      — duplica el segmento activo
  ALFREDSEG_OT_PickPoseMid    — selecciona .json para pose intermedia
  ALFREDSEG_OT_SetFrameStart  — captura frame actual como frame_start
  ALFREDSEG_OT_SetFrameMid    — captura frame actual como frame_mid
  ALFREDSEG_OT_SetFrameEnd    — captura frame actual como frame_end
  ALFREDSEG_OT_Apply          — aplica todos los segmentos activos sobre la timeline
  ALFREDSEG_OT_SaveConfig     — guarda la lista de segmentos a .json
  ALFREDSEG_OT_LoadConfig     — carga la lista de segmentos desde .json
"""

import bpy, json, os, math, datetime, copy
from .blender_compat import get_fcurves
from bpy.types import Operator
from bpy.props import StringProperty, IntProperty, EnumProperty, FloatProperty, BoolProperty

from .constants import BONES_LISTA_FULL, BONES_LISTA, _BONE_DEFAULT, INTERP_TYPE_ITEMS, EYE_BASE_TRANSFORMS
SECONDARY_ARMATURES = {}

# =============================================================================
# DEFAULTS DE reglas_alfred.zip (Kebyn, 2026-08-03): "los segmentos del Paso 3
# tendran por defecto los filtros organicos y el sistema de parpadeo
# configurados como lo dice reglas_alfred.zip".
#
# Filtros organicos (AlfredOrganicFilters) y parpadeo (AlfredEyeExpressionSettings.
# blink_enabled + scene.alfst.blink_intervals) viven a nivel de ESCENA
# (scene.alfst), GLOBAL a toda la animacion -- NO son propiedades por
# segmento (ver comentario en ALFREDSEG_OT_ConcatenateAll: "el sistema de
# ojos vive en scene.alfst -- es GLOBAL... NO por segmento"). Por eso
# "cada segmento tendra por defecto" se traduce en: la PRIMERA vez que se
# crea o divide un segmento en el Paso 3, si el usuario todavia no activo
# manualmente estos sistemas, se dejan configurados con los valores fijos
# que reglas_alfred.zip exige (alfred_story_generator.py: _crear_organic() /
# _crear_eye_sequence()."parpadeo"). Si el usuario ya los toco a mano
# (enabled/blink_enabled=True) NO se pisan.
_ORGANIC_DEFAULTS_REGLAS_ALFRED = {
    "enabled":                  True,
    "breathing_enabled":        True,
    "breathing_amplitude":      0.040,
    "breathing_speed":          0.020,
    "breathing_phase":          1.97,
    "head_sway_enabled":        True,
    "head_sway_amplitude":      0.023,
    "head_sway_speed":          0.079,
    "head_sway_seed":           693,
    "weight_shift_enabled":     False,
    "weight_shift_amplitude":   0.0,
    "weight_shift_speed":       0.0,
    "root_noise_enabled":       False,
    "root_noise_strength":      0.0,
    "root_noise_frequency":     0.0,
    "root_noise_seed":          0,
    "secondary_motion_enabled": True,
    "secondary_motion_lag":     3.9,
    "secondary_motion_damping": 0.51,
    "smooth_curves_enabled":    True,
    "smooth_passes":            3,
    "smooth_factor":            0.63,
    "micro_scale_enabled":      True,
    "micro_scale_amplitude":    0.010,
    "shoulder_noise_enabled":   False,
    "shoulder_noise_amplitude": 0.016,
    "shoulder_noise_speed":     0.091,
    "shoulder_noise_seed":      3449,
}


def _aplicar_defaults_organicos_y_parpadeo(context, seg=None):
    """Deja los filtros organicos y el parpadeo de UN segmento (seg.organic /
    seg.blink_intervals) configurados con los valores fijos de
    reglas_alfred.zip, SOLO si ese segmento en particular todavia no los
    activo a mano (no pisa una configuracion ya en uso).

    AISLAMIENTO POR SEGMENTO (Kebyn + Claude, 2026-08-03): antes esta
    funcion escribia sobre scene.alfst.organic / scene.alfst.blink_intervals
    -- una UNICA instancia global aplicada a TODOS los segmentos por igual,
    que es exactamente lo que causaba que "al cambiar un filtro o parpadeo
    en un segmento, se reprodujera en todos los demas al concatenar". Ahora
    escribe exclusivamente sobre la copia PROPIA del segmento recibido en
    `seg`; cada segmento queda completamente independiente de los demas.

    `seg` es obligatorio en el uso normal (se llama una vez por segmento,
    justo despues de crearlo/dividirlo). Si no se recibe `seg` la funcion
    no hace nada (ya no existe un "default global" que aplicar)."""
    if seg is None:
        return

    # ── Filtros organicos (propios de este segmento) ──
    if not seg.organic.enabled:
        for _attr, _val in _ORGANIC_DEFAULTS_REGLAS_ALFRED.items():
            setattr(seg.organic, _attr, _val)

    # ── Sistema de parpadeo / Secuencia de ojos (switches maestros
    #    globales, se activan una sola vez; los intervalos en si son
    #    propios de este segmento) ──
    # FIX (Kebyn, 2026-08-03: "el sistema de parpadeo/ojos aparece
    # desactivado en todos los segmentos"): antes solo se forzaba
    # blink_enabled=True, pero ALFST_OT_Concatenate.execute exige
    # eye_s.enabled == True como condicion PREVIA para ejecutar cualquier
    # cosa del sistema de ojos (construccion de shape keys, expresiones Y
    # parpadeo -- ver "if eye_s.enabled: ... if eye_s.blink_enabled: ...").
    # Sin encender tambien "enabled", el checkbox "Secuencia de Ojos"
    # quedaba apagado (default de fabrica = False) y el parpadeo, aunque
    # ya tuviera sus intervalos propios por segmento, nunca llegaba a
    # aplicarse en ningun segmento. Se enciende aca junto con
    # blink_enabled para que el sistema de ojos/parpadeo quede realmente
    # activo por defecto, tal como pide reglas_alfred.zip.
    st = getattr(context.scene, "alfst", None)
    _eyes_ready = all(
        context.scene.objects.get(_n) is not None
        for _n in ("ojo_izquierdo_alfred", "ojo_derecho_alfred")
    )
    if st is not None and _eyes_ready:
        if not st.eye_expr.enabled:
            st.eye_expr.enabled = True
        if not st.eye_expr.blink_enabled:
            st.eye_expr.blink_enabled = True
    elif st is not None:
        # Un paquete corporal/portable debe poder concatenarse aunque el
        # .blend destino no contenga las mallas opcionales de ojos.
        st.eye_expr.enabled = False
        st.eye_expr.blink_enabled = False
        print("[ALFST] Ojos de Alfred ausentes: sistema de ojos omitido")

    # FIX (Kebyn, 2026-08-03: "solo esta parpadeando el primer segmento,
    # ademas lo hace de forma asimetrica, al inicio y no a la mitad"):
    # eye_start_blink_mode / eye_end_blink_mode traian de fabrica el valor
    # "BLINK" -- eso hace que ALFST_OT_Concatenate2 (disparado automatica-
    # mente por "Concatenar segmentos" desde el fix anterior) inserte SU
    # PROPIO mini-parpadeo de Inicio/Fin en un rango fijo de ~20 frames al
    # principio de TODA la timeline (eye_global_start_frame .. +~20),
    # totalmente independiente del sistema de Parpadeo automatico por
    # segmento. Como ese rango cae adentro del primer segmento, se veia
    # como "el parpadeo del segmento 1" -- pegado al inicio (no centrado) y
    # ausente en el resto de los segmentos, que es exactamente lo
    # reportado. Se fuerza aca a "Posicion fija" (FIXED) para que el UNICO
    # sistema que controle el parpadeo sea el de Parpadeo automatico por
    # segmento (seg.blink_intervals, ya centrado en la mitad de cada uno).
    if st is not None:
        st.eye_start_blink_mode = "FIXED"
        st.eye_end_blink_mode   = "FIXED"

    if len(seg.blink_intervals) == 0:
        _iv = seg.blink_intervals.add()
        _repair_only = False
    elif (len(seg.blink_intervals) == 1
            and seg.blink_intervals[0].label == "Parpadeo"
            and (seg.blink_intervals[0].frame_end - seg.blink_intervals[0].frame_start) < seg.blink_intervals[0].blink_duration):
        # REPARACION (Kebyn + Claude, 2026-08-03): este segmento ya tenia UN
        # intervalo generado por esta misma funcion en una version anterior
        # con el bug de rango casi nulo (ver comentario abajo) -- se detecta
        # por su etiqueta default sin modificar ("Parpadeo") y por tener un
        # rango mas corto que su propia duracion de parpadeo (imposible que
        # se vea un ciclo completo). Se recalcula el rango real en vez de
        # dejarlo tal cual (que ya no entraria por el "len == 0" de arriba).
        _iv = seg.blink_intervals[0]
        _repair_only = True
    else:
        _iv = None
        _repair_only = False

    if _iv is not None:
        # BUGFIX (Kebyn + Claude, 2026-08-03: "el personaje no esta
        # parpadeando en ningun segmento"): aca se usaba seg.frame_end
        # directamente, pero ese campo casi nunca esta poblado de verdad
        # -- el rango real de un segmento se calcula dinamicamente a
        # partir de la duracion de sus poses (o de un rango ya asignado
        # por AutoSplit), via _calc_seg_frames(). Con seg.frame_end en 0
        # (su default de fabrica), el intervalo de parpadeo quedaba con
        # frame_end = frame_start + 1 -- un rango de apenas 1-2 frames,
        # demasiado corto para que se vea el ciclo de parpadeo completo
        # (9 frames), asi que en la practica no parpadeaba nunca en
        # ningun segmento. Ahora se usa el mismo calculo de rango real
        # que usa el resto del addon, con un piso minimo de 9 frames
        # (blink_duration) + margen para que el parpadeo siempre entre
        # completo dentro del intervalo.
        _, _frame_end_calc = _calc_seg_frames(seg)
        _frame_end = max(_frame_end_calc, seg.frame_start + 9)
        _iv.label        = "Parpadeo"
        _iv.frame_start  = seg.frame_start
        _iv.frame_end    = _frame_end
        # DEFAULT (Kebyn, 2026-08-03: "configura el sistema de parpadeo
        # para que por defecto tenga 1 parpadeo por segmento"): antes el
        # default era 9 parpadeos por segmento (pensado para el viejo
        # intervalo global unico que cubria toda la timeline). Ahora que
        # cada segmento tiene su propio intervalo (tipicamente mas corto,
        # un tramo de caminar/saltar/parada puntual), 1 parpadeo por
        # segmento es el default mas natural.
        _iv.blink_count  = 1
        _iv.blink_duration = 9
        _iv.enabled      = True
        seg.blink_interval_idx = 0


def _copy_action_range(src_action, frame_start, frame_end, new_action_name):
    """AISLAMIENTO REAL (Kebyn, 2026-08-05: "no deberia afectarle lo que
    pase en el segmento 2, falta un verdadero aislamiento entre
    segmentos"). Copia a una action NUEVA, en memoria, los keyframes de
    `src_action` dentro de [frame_start, frame_end], fcurve por fcurve.

    Operacion puramente sobre DATOS: nunca toca ningun objeto de la
    escena, el playhead, animation_data.action de nadie, ni el stack NLA.
    Se usa para construir el tramo de un segmento "sin poses" leyendo
    directamente del respaldo intacto de Capa 1 (_capa1_backup_arm_name /
    _capa1_backup_root_name en ALFREDSEG_OT_ConcatenateAll) -- asi el
    resultado depende solo de esos datos ya horneados una vez al
    principio, nunca de si otro segmento con o sin poses ya se proceso
    antes, en que orden, o de donde estaba parado el playhead.

    Devuelve la action nueva, o None si src_action es None o no hay
    ningun keyframe dentro del rango (limpiando la action creada en ese
    caso, para no dejar basura en bpy.data.actions)."""
    if src_action is None:
        return None
    new_action = bpy.data.actions.new(new_action_name)
    any_kp = False
    for src_fc in get_fcurves(src_action):
        kps_in_range = sorted(
            [kp for kp in src_fc.keyframe_points
             if frame_start <= kp.co.x <= frame_end],
            key=lambda k: k.co.x,
        )
        if not kps_in_range:
            continue
        _group_kw = 'action_group' if hasattr(new_action, 'fcurves') else 'group_name'
        new_fc = get_fcurves(new_action).new(
            src_fc.data_path, index=src_fc.array_index,
            **{_group_kw: src_fc.group.name if src_fc.group else ""})
        new_fc.keyframe_points.add(len(kps_in_range))
        for i, kp in enumerate(kps_in_range):
            nkp = new_fc.keyframe_points[i]
            nkp.co               = kp.co
            nkp.interpolation     = kp.interpolation
            nkp.easing            = kp.easing
            nkp.handle_left       = kp.handle_left
            nkp.handle_right      = kp.handle_right
            nkp.handle_left_type  = kp.handle_left_type
            nkp.handle_right_type = kp.handle_right_type
        new_fc.update()
        any_kp = True

    if not any_kp:
        bpy.data.actions.remove(new_action)
        return None
    return new_action


def _push_action_to_nla(obj, action, frame_start, frame_end, track_name):
    """Empuja una action YA CONSTRUIDA (ver _copy_action_range, o la
    action propia horneada por un segmento CON poses) a su propia pista
    NLA dedicada y aislada (extrapolation='NOTHING').

    BUGFIX (Kebyn, 2026-08-05, "aislamiento real"): a diferencia de la
    version anterior de esta funcion (_push_organic_slice_to_nla), que
    LEIA obj.animation_data.action en vivo para decidir que copiar --
    dependiendo asi de que ningun otro segmento hubiera tocado esa
    action mientras tanto, del playhead, o del stack NLA ya presente --
    esta version solo recibe una action ya lista y la empuja tal cual.
    No lee ni evalua nada del objeto en vivo. Esto es lo que garantiza
    que cada segmento quede 100% aislado: su contenido final depende
    unicamente de los datos que se le pasaron, nunca del orden de
    procesamiento ni del estado de otros segmentos.

    Ademas (BUGFIX Kebyn + Claude, 2026-08-04 ter, que se mantiene aca):
    deja obj.animation_data.action = None apenas la action nueva queda
    aislada en su propia pista -- si no, esa action quedaria colgada
    como "active action" por ENCIMA de todo el stack NLA (extrapolation
    'HOLD' por defecto), pisando las pistas ya aisladas de los demas
    segmentos."""
    if obj is None or action is None or not get_fcurves(action):
        if action is not None:
            bpy.data.actions.remove(action)
        return
    if not obj.animation_data:
        obj.animation_data_create()
    track = obj.animation_data.nla_tracks.new()
    track.name = track_name
    strip = track.strips.new(track_name, int(frame_start), action)
    if hasattr(strip, 'action_slot') and getattr(action, 'slots', None):
        strip.action_slot = action.slots[0]
    strip.use_sync_length    = False
    strip.action_frame_start = frame_start
    strip.action_frame_end   = frame_end
    strip.frame_start        = frame_start
    strip.frame_end          = frame_end
    strip.extrapolation      = 'NOTHING'
    strip.blend_type         = 'REPLACE'
    obj.animation_data.action = None


# Snapshot en memoria de los valores ANTES de editar una pose (huesos + root del
# slot + record completo original), capturado por ALFREDSEG_OT_EnterEditPose y
# consumido por ALFREDSEG_OT_SaveEditedPose para completar el "despues" en el
# .json de cambios de ESTA edicion. Clave: (json_file, pose_index).
_POSE_EDIT_SNAPSHOTS = {}


def _cambios_dir_for(poses_dir):
    d = os.path.join(os.path.dirname(poses_dir.rstrip("\\/")), "cambios")
    os.makedirs(d, exist_ok=True)
    return d


def _new_pose_change_filepath(poses_dir, json_file, pose_idx):
    """Genera la ruta de un .json de 'cambios' nuevo y unico para ESTA edicion
    de pose (uno por cada vez que se pulsa 'Editar pose...'). El nombre
    incluye el archivo de pose original, el indice y un timestamp para que
    no se pisen entre si y quede un historial completo en la carpeta
    'cambios'."""
    cambios_dir = _cambios_dir_for(poses_dir)
    base = os.path.splitext(os.path.basename(json_file or "pose"))[0]
    ts = datetime.datetime.now()
    filename = f"cambios_{base}_pose{pose_idx}_{ts.strftime('%Y%m%d_%H%M%S_%f')}.json"
    return os.path.join(cambios_dir, filename)

from .interpolation import apply_interp
from .pose_utils import (
    load_json_poses, get_pose_record, pose_record_to_full_dict,
    list_json_files, _enum_json_files, _json_file_from_index,
    _enum_poses_from_self_json, get_root_rotation_from_record,
    get_root_transform_from_record,
    guardar_calificacion_pose, leer_calificacion_actual, leer_nombre_legible,
    resolve_pose_start_frames,
)
from . import object_import_utils as _oiu
from .path_recorder import calcular_estimacion_geometrica


# =============================================================================
# UTILIDADES INTERNAS
# =============================================================================

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
        # Buscar por nombre exacto o por alias sin sufijo _alfred
        d = pose_dict.get(bone_name, None)
        if d is None:
            short = bone_name.replace("_alfred", "")
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
    Calcula la duracion total de un segmento.

    Devuelve (total_frames, frame_end_calculado).
    Util para mostrar la duracion en tiempo real en el header del segmento
    y para que el botón Play sepa hasta que frame reproducir.

    FIX (Kebyn, 2026-08-04): "el rango de un segmento ya dividido en el
    Paso 2/3 no debe cambiar segun las poses que se le agreguen" -- antes,
    la duracion del segmento SIEMPRE se recalculaba como la suma de
    duraciones de sus action_poses (via resolve_pose_start_frames), asi
    que un segmento de 96f (ej. "01_caminar", ya delimitado por
    AutoSplitFromConfig) colapsaba a 20f apenas se le cargaba UNA pose de
    20f. Las poses son contenido DENTRO del segmento, no la definicion
    del segmento.

    Ahora, si el segmento ya trae un rango fijo definido por el Paso 2/3
    (frame_end_planned > frame_start_planned -- ver AlfredAnimSegment en
    properties.py) Y no esta en modo 1 coordenada, ESE rango manda
    siempre, tenga o no poses cargadas: las poses solo tienen que caber
    dentro de esos frames (se advierte en otro lado si se pasan, ver
    ALFREDSEG_UL_ActionPoses / draw_item). El unico caso en que la suma
    de duraciones de las poses SIGUE definiendo el total es:
      - Modo 1 coordenada (single_coord_mode): aca no hay division de
        Paso 2 que reservar -- el propio diseño dice que frame_end "se
        calculara al CONCATENAR como la suma de duraciones de todas las
        poses + filtros" (ver ALFREDSEG_OT_Add).
      - Segmentos viejos/sin foto del Paso 2 (frame_end_planned == 0,
        ej. cargados de un configuracion.json anterior a este fix):
        se cae al comportamiento historico (poses definen el total, o el
        rango existente, o 1f de fallback) para no romper proyectos ya
        guardados.
    """
    if (not seg.single_coord_mode) and seg.frame_end_planned > seg.frame_start_planned:
        return seg.frame_end_planned - seg.frame_start_planned + 1, seg.frame_end_planned

    if seg.action_poses:
        _starts = resolve_pose_start_frames(list(seg.action_poses), seg.frame_start)
        _last_end = _starts[-1] + max(1, int(seg.action_poses[-1].duration)) - 1
        total = _last_end - seg.frame_start + 1
        if total > 0:
            return total, _last_end

    existing_span = seg.frame_end - seg.frame_start + 1
    if existing_span > 0:
        return existing_span, seg.frame_end

    return 1, seg.frame_start



def _sync_seg_interval(seg, segs_collection=None):
    """
    Sistema de poses flexible (Kebyn, 2026-07-10): mantiene el intervalo del
    segmento (frame_end / frame_end_auto) SIEMPRE sincronizado con la suma
    de duraciones de sus poses de accion. Se llama cada vez que se agrega,
    quita, o edita la duracion de una pose — asi el rango marcado en el
    panel ("Segmento activo: X [ini→fin]") nunca queda desactualizado y no
    hace falta ajustarlo a mano despues de tocar las poses.

    Si el segmento no tiene poses todavia, no se toca el rango (se deja el
    que haya, para no romper un segmento recien creado y vacio).

    CASCADA (Kebyn, 2026-07-10): si el frame_end de ESTE segmento cambia
    (delta != 0) y se paso `segs_collection` (alfred_segs.segments), todos
    los DEMAS segmentos cuyo frame_start sea posterior al de este se
    desplazan el mismo delta (frame_start y frame_end, y frame_end_auto si
    corresponde). Asi la secuencia completa (segmentos anteriores y
    posteriores en la timeline) se mantiene contigua y no se desfasa cuando
    un segmento intermedio crece o se achica por agregar/quitar poses. Cada
    segmento desplazado conserva su propia duracion (solo cambia DONDE cae
    en la timeline), y si alguno de ellos tiene sus propias poses, su
    duracion sigue viniendo de ellas — esto solo reubica el rango.
    """
    if not seg.action_poses:
        return
    old_end = seg.frame_end
    total, new_end = _calc_seg_frames(seg)
    delta = new_end - old_end
    seg.frame_end = new_end
    if seg.single_coord_mode:
        seg.frame_end_auto = new_end

    if delta != 0 and segs_collection is not None:
        _seg_ptr = seg.as_pointer()
        for other in segs_collection:
            if other.as_pointer() == _seg_ptr:
                continue
            if other.frame_start > seg.frame_start:
                other.frame_start += delta
                other.frame_end   += delta
                if other.single_coord_mode:
                    other.frame_end_auto += delta

    return total, new_end


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
    fc = get_fcurves(action).find(data_path, index=index)
    if fc is None:
        fc = get_fcurves(action).new(data_path=data_path, index=index)
    return fc


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
    # Fallback historico.
    arm = scene.objects.get("Dog_001_rig")
    if arm and arm.type == "ARMATURE":
        return arm
    # Los .blend importados pueden renombrar Armature a Armature.001 o usar
    # otro nombre. Preferir el rig que realmente contiene los huesos de
    # Alfred; si solo existe un armature, usarlo como ultimo recurso.
    candidatos = [ob for ob in scene.objects if ob.type == "ARMATURE"]
    huesos_clave = (
        "Hips_alfred", "Spine1_alfred", "Rightelbow_alfred",
        "Leftelbow_alfred", "Head_alfred",
    )
    if candidatos:
        arm = max(
            candidatos,
            key=lambda ob: sum(1 for nombre in huesos_clave if ob.pose.bones.get(nombre)),
        )
        if any(arm.pose.bones.get(nombre) for nombre in huesos_clave) or len(candidatos) == 1:
            seg_cfg.armature_name = arm.name
            st = getattr(scene, "alfst", None)
            if st is not None:
                st.armature_name = arm.name
            print("[ALFST] Armature de Alfred resuelto automaticamente: %s" % arm.name)
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
# Solo para compatibilidad con codigo antiguo — ya no se usa en CONCATENAR
_BONE_AFFECT_MAP = {
    "Hips_alfred":       "affect_body",
    "Spine_alfred":      "affect_body",
    "RightUpArm_alfred": "affect_right_arm",
    "LeftUpArm_alfred":  "affect_left_arm",
    "RightUpLeg_alfred": "affect_right_leg",
    "LeftUpLeg_alfred":  "affect_left_leg",
    "Armature":          "affect_root",
}

# Mapa granular: nombre de bone → propiedad filter_* del segmento
# Si filter_* es True el bone está FILTRADO (excluido de las poses)
# Mapa granular: nombre de bone → propiedad filter_* del segmento
# Si filter_* es True el bone está FILTRADO (excluido de las poses)
_BONE_FILTER_MAP = {
    # Caderas / raiz
    "Hips_alfred":        "filter_hips",
    # Columna vertebral
    "Spine_alfred":       "filter_spine",
    "Spine1_alfred":      "filter_spine1",
    "Spine2_alfred":      "filter_spine2",
    # Cabeza / cuello
    "Neck_alfred":        "filter_neck",
    "face_alfred":        "filter_face",
    # Brazo derecho
    "RightUpArm_alfred":  "filter_right_arm",
    "Rightelbow_alfred":  "filter_right_elbow",
    # Brazo izquierdo
    "LeftUpArm_alfred":   "filter_left_arm",
    "Leftelbow_alfred":   "filter_left_elbow",
    # Pierna derecha
    "RightUpLeg_alfred":  "filter_right_leg",
    "Rightknee_alfred":   "filter_right_knee",
    # Pierna izquierda
    "LeftUpLeg_alfred":   "filter_left_leg",
    "Leftknee_alfred":    "filter_left_knee",
    # Herramientas / accesorios
    "no_bone_01":         "filter_no_bone_01",
    "no_bone_02":         "filter_no_bone_02",
    "no_bone_03":         "filter_no_bone_03",
    "no_bone_04":         "filter_no_bone_04",
    "no_bone_05":         "filter_no_bone_05",
    "no_bone_06":         "filter_no_bone_06",
    "no_bone_07":         "filter_no_bone_07",
    "no_bone_08":         "filter_no_bone_08",
}

# Lista de todos los atributos booleanos del Bloqueador de bones (bloqueo total),
# usada por el exportador/importador de configuracion del Paso 3.
_BONE_FILTER_ATTRS = [
    "filter_show", "filter_main_bone",
    "filter_hips", "filter_spine", "filter_spine1", "filter_spine2",
    "filter_neck", "filter_face",
    "filter_right_arm", "filter_right_elbow",
    "filter_left_arm", "filter_left_elbow",
    "filter_right_leg", "filter_right_knee",
    "filter_left_leg", "filter_left_knee",
    "filter_no_bone_01", "filter_no_bone_02", "filter_no_bone_03", "filter_no_bone_04",
    "filter_no_bone_05", "filter_no_bone_06", "filter_no_bone_07", "filter_no_bone_08",
]


def _get_bone_block_entry(seg, bone_key, create=False):
    """Ubica (o crea) el AlfredBoneBlockEntry de un bone dentro de un segmento."""
    for entry in seg.bone_blocks:
        if entry.bone_key == bone_key:
            return entry
    if create:
        entry = seg.bone_blocks.add()
        entry.bone_key = bone_key
        return entry
    return None


def _bone_full_blocked(seg, bone_name):
    """Retorna True si el bone esta bloqueado por el checkbox simple
    (bloqueo total: en todos los frames del segmento)."""
    filter_attr = _BONE_FILTER_MAP.get(bone_name)
    if filter_attr is None:
        return False
    return getattr(seg, filter_attr, False)


def _bone_blocked_in_intervals(seg, bone_name, frame):
    """Retorna True si 'frame' cae dentro de algun intervalo de bloqueo
    definido para este bone (Bloqueador de bones)."""
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
    """Retorna True si el bone está BLOQUEADO (no debe recibir poses del segmento).
    El bloqueador de bones esta siempre activo: cada bone marcado individualmente
    queda excluido, sin necesidad de un interruptor maestro.

    - Si el checkbox simple del bone esta activo, queda bloqueado en TODO el
      segmento (sin importar 'frame').
    - Si ademas (o en su lugar) tiene intervalos de frames definidos, queda
      bloqueado solo dentro de esos rangos. Para esto se debe pasar 'frame'."""
    if _bone_full_blocked(seg, bone_name):
        return True
    if frame is not None and _bone_blocked_in_intervals(seg, bone_name, frame):
        return True
    return False


# =============================================================================
# OPERADOR PRINCIPAL: APLICAR SEGMENTOS
# =============================================================================

class ALFREDSEG_OT_Apply(Operator):
    bl_idname  = "alfredseg.apply"
    bl_label   = "APLICAR SEGMENTOS"
    bl_description = (
        "Aplica todos los segmentos activos del Paso 3 sobre la animacion de "
        "recorrido generada por los Pasos 1+2. Los bones configurados adoptaran "
        "las poses definidas en cada segmento, mezcladas con el movimiento existente."
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene    = context.scene
        seg_cfg  = scene.alfred_segs
        segments = [s for s in seg_cfg.segments if s.enabled]

        if not segments:
            self.report({"WARNING"}, "No hay segmentos activos en el Paso 3")
            return {"CANCELLED"}

        armature = _resolve_armature(seg_cfg, scene)
        if armature is None:
            self.report({"ERROR"}, f"No se encontro armature '{seg_cfg.armature_name}'")
            return {"CANCELLED"}

        poses_dir = bpy.path.abspath(seg_cfg.poses_dir)
        applied   = 0
        errors    = []

        # ── Forzar modo de rotacion euler XYZ en todos los bones afectados ──────
        # Los keyframes se escriben en pose.bones[...].rotation_euler; si el bone
        # esta en modo QUATERNION (default de Blender) esos fcurves se ignoran por
        # completo y las poses no se ven, aunque los keyframes existan. Este bloque
        # garantiza que el canal correcto sea el que realmente conduce al bone.
        if armature.pose:
            for bone_name in BONES_LISTA_FULL:
                pb = armature.pose.bones.get(bone_name)
                if pb is not None and pb.rotation_mode != "XYZ":
                    pb.rotation_mode = "XYZ"
        for sec_name in SECONDARY_ARMATURES:
            sec_obj = scene.objects.get(sec_name)
            if sec_obj is not None and sec_obj.type == "ARMATURE" and sec_obj.pose:
                for bone_name in ("tail_1", "tail_2"):
                    pb = sec_obj.pose.bones.get(bone_name)
                    if pb is not None and pb.rotation_mode != "XYZ":
                        pb.rotation_mode = "XYZ"

        for seg in segments:
            f_start = seg.frame_start

            # ── Determinar frame_end y la action destino ──────────────────────
            if seg.single_coord_mode:
                total_dur = 0
                for ap in seg.action_poses:
                    total_dur += ap.duration
                total_dur  = max(total_dur, 2)
                f_end = f_start + total_dur - 1
                seg.frame_end      = f_end
                seg.frame_end_auto = f_end
                # Modo 1 coord: usar la action global del armature
                if not armature.animation_data or not armature.animation_data.action:
                    errors.append(f"Segmento '{seg.label}': armature sin action activa")
                    continue
                action = armature.animation_data.action
            else:
                f_end = seg.frame_end
                # Modo recorrido: usar la action dedicada del segmento
                seg_action = bpy.data.actions.get(seg.seg_action_name)
                if seg_action is None:
                    # Fallback: crear action vacia si no existe (segmento importado de JSON)
                    seg_action_name = f"alfredseg_{seg.label.replace(' ','_')}"
                    seg_action = bpy.data.actions.get(seg_action_name)
                    if seg_action is None:
                        seg_action = bpy.data.actions.new(name=seg_action_name)
                    seg.seg_action_name = seg_action_name
                action = seg_action
                # Asignar como action activa para que los keyframes se evaluen
                armature.animation_data.action = action

            if f_end <= f_start:
                errors.append(f"Segmento '{seg.label}': frame_end <= frame_start, ignorado")
                continue

            total_frames = f_end - f_start

            # Cargar poses: la primera y ultima pose de accion actuan como
            # anclas implicitas de inicio/fin del segmento.
            _act_list  = list(seg.action_poses)
            pose_start = _load_pose_from_file(_act_list[0].json_file, poses_dir) if _act_list else None
            pose_end   = _load_pose_from_file(_act_list[-1].json_file, poses_dir) if _act_list else None
            pose_mid   = _load_pose_from_file(seg.pose_mid_file,   poses_dir) if seg.pose_mid_file   else None

            if pose_start is None and pose_end is None:
                errors.append(f"Segmento '{seg.label}': sin poses cargadas, ignorado")
                continue
            if pose_start is None: pose_start = pose_end
            if pose_end   is None: pose_end   = pose_start

            # ── Inyectar configuracion: respetar filtros granulares del segmento ──
            for bone_name in BONES_LISTA_FULL:
                if _bone_full_blocked(seg, bone_name):
                    continue   # bone bloqueado por completo: no recibe poses

                is_secondary = bone_name in ("tail_1", "tail_2")
                if is_secondary:
                    arm_obj = _resolve_secondary(bone_name, scene)
                    if arm_obj is None or not arm_obj.animation_data or not arm_obj.animation_data.action:
                        continue
                    bone_action = arm_obj.animation_data.action
                else:
                    bone_action = action

                dp_rot   = f'pose.bones["{bone_name}"].rotation_euler'
                dp_loc   = f'pose.bones["{bone_name}"].location'
                dp_scale = f'pose.bones["{bone_name}"].scale'

                for frame in range(f_start, f_end + 1):
                    if _bone_blocked_in_intervals(seg, bone_name, frame):
                        continue   # bloqueado en este frame por un intervalo del Bloqueador de bones

                    t_global = (frame - f_start) / max(1, total_frames)
                    alpha = _blend_alpha(
                        t_global, total_frames,
                        seg.blend_in_frames, seg.blend_out_frames,
                        seg.blend_strength,
                    )
                    if alpha <= 0.0:
                        continue

                    rot_pose = _interpolate_pose_value(
                        pose_start, pose_mid, pose_end,
                        t_global, bone_name, "rot",
                        seg.interp_type, seg.interp_mid_to_end,
                    )
                    loc_pose = _interpolate_pose_value(
                        pose_start, pose_mid, pose_end,
                        t_global, bone_name, "loc",
                        seg.interp_type, seg.interp_mid_to_end,
                    )
                    sca_pose = _interpolate_pose_value(
                        pose_start, pose_mid, pose_end,
                        t_global, bone_name, "scale",
                        seg.interp_type, seg.interp_mid_to_end,
                    )

                    # ── Independencia entre segmentos ──────────────────────────
                    # El blend NUNCA se calcula contra el valor ya presente en el
                    # fcurve (eso acoplaria este segmento a lo que haya escrito
                    # el recorrido base u OTRO segmento, p.ej. en single_coord_mode
                    # donde varios segmentos comparten la misma action). El punto
                    # de partida del alpha-blend es siempre el rest pose fijo del
                    # bone (rot=0.0, loc=0.0, scale=1.0), no una lectura externa.
                    for axis_idx, (pv_rot, pv_loc, pv_sca) in enumerate(
                        zip(rot_pose, loc_pose, sca_pose)
                    ):
                        base_rot = 0.0
                        _set_keyframe(bone_action, dp_rot, axis_idx, frame,
                                      base_rot + (pv_rot - base_rot) * alpha)

                        base_loc = 0.0
                        _set_keyframe(bone_action, dp_loc, axis_idx, frame,
                                      base_loc + (pv_loc - base_loc) * alpha)

                        base_sca = 1.0
                        _set_keyframe(bone_action, dp_scale, axis_idx, frame,
                                      base_sca + (pv_sca - base_sca) * alpha)

            # ── Suavizar SOLO fcurves de bones NO bloqueados por completo ──────────
            affected_dps = set()
            for bone_name in BONES_LISTA_FULL:
                if not _bone_full_blocked(seg, bone_name):
                    affected_dps.add(f'pose.bones["{bone_name}"].rotation_euler')
                    affected_dps.add(f'pose.bones["{bone_name}"].location')
                    affected_dps.add(f'pose.bones["{bone_name}"].scale')

            for fc in get_fcurves(action):
                if fc.data_path not in affected_dps:
                    continue   # no tocar animaciones base
                kps_in_range = [kp for kp in fc.keyframe_points if f_start <= kp.co.x <= f_end]
                if len(kps_in_range) < 3:
                    continue
                vals     = [kp.co.y for kp in kps_in_range]
                smoothed = vals[:]
                for i in range(1, len(vals) - 1):
                    smoothed[i] = vals[i-1]*0.25 + vals[i]*0.5 + vals[i+1]*0.25
                for kp, v in zip(kps_in_range, smoothed):
                    kp.co.y = v
                fc.update()

            applied += 1

        # ── Ejecutar importacion de objetos (escudo, espada, etc.) ────────────
        oi_summary = ""
        try:
            n_imp, n_skip, oi_errors = _oiu.run_object_imports_live(scene)
            oi_summary = f"objetos: {n_imp} importados / {n_skip} omitidos"
            if n_imp or n_skip:
                print(f"[JRRSTSeg] Importacion de {oi_summary}")
            for e in oi_errors:
                print(f"[JRRSTSeg] {e}")
                errors.append(e)
        except Exception as e_oi:
            import traceback
            print(f"[JRRSTSeg] Error en importacion de objetos:")
            print(traceback.format_exc())
            errors.append(f"Importacion de objetos: {e_oi}")
            oi_summary = f"objetos: ERROR ({e_oi})"

        seg_cfg.segs_applied = True
        msg_parts = [f"{applied} segmentos concatenados"]
        if oi_summary:
            msg_parts.append(oi_summary)
        if errors:
            msg_parts.append(f"{len(errors)} advertencias")
            for e in errors:
                print(f"[JRRSTSeg] {e}")
        seg_cfg.status_msg = " | ".join(msg_parts)
        self.report({"INFO"}, seg_cfg.status_msg)
        return {"FINISHED"}


class ALFREDSEG_OT_ConcatenateAll(Operator):
    """Ejecuta, para CADA segmento activo, el mismo proceso que el boton
    CONCATENAR individual (operador alfst.concatenate: inyecta poses ->
    bones configurados), uno por uno, respetando el rango de frames PROPIO
    de cada segmento (su propia secuencia). Al terminar reproduce todas las
    secuencias encadenadas de principio a fin, en el orden de sus
    frame_start."""
    bl_idname  = "alfredseg.concatenate_all"
    bl_label   = "Concatenar segmentos"
    bl_description = (
        "Ejecuta CONCATENAR (inyectar poses -> bones configurados) para "
        "todos los segmentos activos del Paso 3, uno por uno, respetando "
        "la secuencia de frames propia de cada segmento, y luego reproduce "
        "todo de principio a fin"
    )
    bl_options = {"REGISTER"}   # SIN UNDO: dispara reproduccion, igual que play_segment

    def execute(self, context):
        scene   = context.scene
        seg_cfg = scene.alfred_segs

        # Indices originales (dentro de seg_cfg.segments) de los segmentos
        # activos, ordenados por frame_start — asi se procesan (e inyectan
        # sus poses) en el mismo orden en que se reproducen sus respectivas
        # secuencias, cada una en su propio rango de frames.
        _indexed = [(i, s) for i, s in enumerate(seg_cfg.segments) if s.enabled]
        _indexed.sort(key=lambda pair: pair[1].frame_start)

        if not _indexed:
            self.report({"WARNING"}, "No hay segmentos activos en el Paso 3")
            return {"CANCELLED"}

        # FIX (Kebyn, 2026-08-03: "al concatenar los N° segmentos no se
        # estan reproduciendo los filtros y parpadeos"): los defaults de
        # reglas_alfred.zip (_aplicar_defaults_organicos_y_parpadeo) solo se
        # disparaban al CREAR/DIVIDIR un segmento (alfredseg.add /
        # alfredseg.autosplit_from_config). Un segmento creado ANTES de esa
        # actualizacion del addon (o cargado via "Cargar config Paso 3")
        # nunca pasa por ninguno de esos dos operadores, asi que se quedaba
        # sin filtros organicos/parpadeo propios. Se asegura aca tambien,
        # justo antes de concatenar, para que SIEMPRE queden activos (salvo
        # que el usuario ya los haya configurado a mano en ESE segmento).
        #
        # AISLAMIENTO POR SEGMENTO (Kebyn + Claude, 2026-08-03): se aplica
        # UNA VEZ POR SEGMENTO (no una sola vez global) para que cada uno
        # reciba su PROPIA copia independiente de AlfredOrganicFilters y su
        # PROPIA coleccion de intervalos de parpadeo. Esto tambien migra
        # automaticamente proyectos guardados con el bug anterior (donde
        # todos los segmentos compartian scene.alfst.organic): la primera
        # vez que se concatenan despues de esta actualizacion, cada
        # segmento que aun no tenga su organic.enabled propio ni sus
        # propios blink_intervals recibe los defaults de forma aislada.
        for _, _seg_defaults in _indexed:
            _aplicar_defaults_organicos_y_parpadeo(context, _seg_defaults)

        # FIX (Kebyn, 2026-07-11): este operador solo inyectaba poses (Capa 2,
        # via alfst.concatenate) SIN regenerar antes la Capa 1 (el recorrido
        # base: caminar/saltar/parada, via alfredpr.preview_path). Si la Capa 1
        # horneada en la timeline no estaba fresca (o nunca se genero), cada
        # segmento "parada" arrancaba su ease-in (entry_ratio) desde lo que
        # hubiera quedado ahi -- tipicamente la ultima pose de caminar del
        # segmento anterior -- en vez de partir de un canvas de rest limpio.
        # Eso se veia como "el personaje se mueve lentamente" en los tramos
        # de una sola coordenada: en realidad es un arrastre desde la pose de
        # caminata hacia la primera pose configurada. Se regenera la Capa 1
        # aqui, igual que ya hace alfredseg.play_segment_recorrido, antes de
        # inyectar ninguna pose.
        #
        # BUGFIX (Kebyn, 2026-08-03): el regen de Capa 1 (alfredpr.preview_path)
        # SIEMPRE fuerza root_empty.location = (0,0,0) antes de recalcular la
        # animacion base a partir de scene.alfred_path.path_points (el
        # recorrido multi-punto grabado). Eso esta bien para segmentos que
        # SI son parte de ese recorrido (single_coord_mode=False), pero para
        # segmentos "1 coordenada" (single_coord_mode=True -- una secuencia
        # de poses fija en un punto, sin relacion con el recorrido grabado)
        # este regen no tiene nada que ver con lo que se va a reproducir y
        # ademas teletransportaba al personaje al origen (0,0,0) en vez de
        # dejarlo en su posicion real. Ahora solo se regenera la Capa 1 si
        # ALGUNO de los segmentos activos realmente pertenece al recorrido
        # (single_coord_mode=False); si TODOS los activos son de 1 coordenada,
        # se omite el regen por completo.
        _hay_recorrido_activo = any(not s.single_coord_mode for _, s in _indexed)
        if _hay_recorrido_activo:
            _regen = bpy.ops.alfredpr.preview_path()
            if "CANCELLED" in _regen:
                self.report(
                    {"ERROR"},
                    "No se pudo regenerar el recorrido base (Capa 1) antes de "
                    "concatenar. Revisa el recorrido grabado / el .blend del "
                    "personaje.")
                return {"CANCELLED"}
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()

        # BUGFIX (Kebyn + Claude, 2026-08-04): "despues del segmento 2 el
        # bone Neck_alfred rota de golpe sin ninguna pose asignada" --
        # causa real, ver comentario largo junto a "_capa1_backup_swap"
        # en ALFST_OT_Concatenate (operators_anim.py). Resumen: cada
        # segmento CON poses concatenado mas abajo borra la action
        # COMPARTIDA COMPLETA (Capa 1 recien regenerada arriba), no solo
        # su propio rango -- asi que el segmento SIGUIENTE (con o sin
        # poses) ya no tiene forma de leer "el caminar real" para su
        # propio tramo, y termina horneando sobre un residuo/basura de
        # pose.bones en vez de la Capa 1 real.
        #
        # Fix: se guarda aca, ANTES de arrancar el loop, una COPIA
        # intacta de la action de Capa 1 (armature + root "alfred").
        # Esta copia NUNCA se toca ni se borra durante el loop -- se le
        # pasa el NOMBRE a cada llamada de alfst.concatenate
        # (capa1_backup_arm/root) y se usa directamente en la rama "sin
        # poses" de mas abajo, para que ambos casos lean siempre la
        # Capa 1 real sin importar cuantos segmentos con poses ya se
        # hayan concatenado antes.
        _capa1_backup_arm_name  = ""
        _capa1_backup_root_name = ""
        _arm_for_backup  = _resolve_armature(seg_cfg, scene)
        _root_for_backup = bpy.data.objects.get("alfred")
        # Limpiar copias de respaldo que hayan quedado de una corrida
        # anterior (use_fake_user=True evita que Blender las purgue solo,
        # asi que si no se limpian aca se acumulan una por corrida).
        for _stale_act in list(bpy.data.actions):
            if _stale_act.name.startswith("ALFRED_CAPA1_BACKUP_"):
                bpy.data.actions.remove(_stale_act)
        if (_arm_for_backup is not None and _arm_for_backup.animation_data
                and _arm_for_backup.animation_data.action):
            _bk = _arm_for_backup.animation_data.action.copy()
            _bk.name = f"ALFRED_CAPA1_BACKUP_arm_{scene.name}"
            _bk.use_fake_user = True
            _capa1_backup_arm_name = _bk.name
        if (_root_for_backup is not None and _root_for_backup.animation_data
                and _root_for_backup.animation_data.action):
            _bk = _root_for_backup.animation_data.action.copy()
            _bk.name = f"ALFRED_CAPA1_BACKUP_root_{scene.name}"
            _bk.use_fake_user = True
            _capa1_backup_root_name = _bk.name

        _original_active = seg_cfg.active_index
        _f_min, _f_max = None, None
        _done, _errors = 0, []

        # ── AUTOMATIZACION DE OJOS: INICIO / N CAMBIOS / FIN ─────────────────
        # (Kebyn, 2026-07-13; reordenado Kebyn + Claude, 2026-08-03: "la
        # funcion de concatenar ojos ahora la realizara el boton de
        # concatenar segmentos"). Antes esto se ejecutaba DESPUES del loop
        # de segmentos, una vez terminada la inyeccion de poses de los N
        # segmentos. Problema: ALFST_OT_Concatenate2 (alfst.concatenate_2)
        # empieza SIEMPRE borrando la action de shape keys de los ojos
        # ("Limpiar actions previas... Y shape keys") para reconstruir el
        # sistema Inicio->Intermedios->Fin desde cero -- pero esa MISMA
        # action de shape keys es donde alfst.concatenate (dentro del loop
        # de segmentos, mas abajo) inserta el Parpadeo automatico propio de
        # cada segmento (shape key "Closed"). Ejecutar concatenate_2
        # DESPUES del loop borraba, sin darse cuenta, todo el parpadeo por
        # segmento que se acababa de hornear.
        #
        # Ahora se ejecuta ANTES del loop: primero se deja lista la base
        # Inicio/Intermedios/Fin (si el usuario la usa), y RECIEN DESPUES
        # el loop de segmentos agrega (sin borrar) el parpadeo propio de
        # cada uno sobre esa misma action ya construida.
        #
        # Gate: antes solo se disparaba con "eye_changes_enabled" (el
        # sub-toggle de "N Cambios intermedios"), dejando afuera a quienes
        # solo quieren Inicio/Fin sin intermedios. Ahora se dispara con el
        # interruptor MAESTRO "eye_expr.enabled" ("Sistema de Ojos activo"),
        # que es el mismo que gatea todo el sistema de ojos/parpadeo en
        # alfst.concatenate -- consistente con "concatenar segmentos hace
        # todo el trabajo de ojos".
        st_eyes = getattr(scene, "alfst", None)
        if st_eyes is not None and getattr(st_eyes.eye_expr, "enabled", False):
            _faltan_ojos = [
                _n for _n in ("ojo_izquierdo_alfred", "ojo_derecho_alfred")
                if scene.objects.get(_n) is None
            ]
            if _faltan_ojos:
                st_eyes.eye_expr.enabled = False
                st_eyes.eye_expr.blink_enabled = False
                print("[ALFST] Sistema de ojos omitido; faltan: %s" % ", ".join(_faltan_ojos))
        if st_eyes is not None and getattr(st_eyes.eye_expr, "enabled", False):
            # Una parada con animacion .py guarda los ojos en pistas NLA
            # Slot_NNN_eye_object_* / Slot_NNN_eye_shapes_*. La reconstruccion
            # global historica hacia shape_key_clear(), reemplazaba el datablock
            # Key y dejaba inutiles esas pistas al pulsar "Concatenar segmentos".
            # Detectamos ese caso y pedimos una actualizacion no destructiva:
            # conserva geometria/actions/NLA importadas y crea solo lo faltante.
            _preserve_imported_eyes = False
            for _eye_name in ("ojo_izquierdo_alfred", "ojo_derecho_alfred"):
                _eye_obj = bpy.data.objects.get(_eye_name)
                if _eye_obj is None:
                    continue
                _eye_anim_owners = [_eye_obj]
                if getattr(_eye_obj.data, "shape_keys", None) is not None:
                    _eye_anim_owners.append(_eye_obj.data.shape_keys)
                for _owner in _eye_anim_owners:
                    _ad = getattr(_owner, "animation_data", None)
                    if _ad and any(
                        _trk.name.startswith("Slot_") and "_eye_" in _trk.name
                        for _trk in _ad.nla_tracks
                    ):
                        _preserve_imported_eyes = True
                        break
                if _preserve_imported_eyes:
                    break
            try:
                _sk_result = bpy.ops.alfst.build_eye_shape_keys(
                    preserve_existing=_preserve_imported_eyes)
                if "FINISHED" not in _sk_result:
                    _errors.append("Ojos: 'Crear/Recrear Shape Keys' no finalizo correctamente")
            except Exception as e_sk:
                _errors.append(f"Ojos: fallo 'Crear/Recrear Shape Keys' ({e_sk})")

            try:
                _c2_result = bpy.ops.alfst.concatenate_2()
                if "FINISHED" not in _c2_result:
                    _errors.append("Ojos: 'CONCATENAR_2' no finalizo correctamente")
            except Exception as e_c2:
                _errors.append(f"Ojos: fallo 'CONCATENAR_2' ({e_c2})")

        # AISLAMIENTO TOTAL DE SEGMENTOS (Kebyn + Claude, 2026-07-11):
        # Cada segmento ahora se hornea en su PROPIA action y se empuja a
        # su PROPIA pista NLA dedicada (isolate_segments=True en
        # alfst.concatenate, extrapolation='NOTHING'), en vez de acumular
        # keyframes sobre una unica action compartida. Con esto ningun
        # segmento puede heredar valores, curvas de interpolacion, ni
        # bones de otro -- cada uno vive exclusivamente dentro de su propio
        # frame_start->frame_end. Efecto colateral ACEPTADO a proposito:
        # un bone compartido entre dos segmentos consecutivos (ej. piernas
        # en dos tramos de caminar) ya NO mantiene continuidad entre ellos.
        #
        # Reemplaza el viejo parche "_bone_last_seg" (reset de cola por
        # bone al terminar su ultimo uso): ya no hace falta, porque
        # extrapolation='NOTHING' en cada pista NLA logra lo mismo de
        # forma estructural, no como parche posterior.
        #
        # Se limpian aqui, ANTES del loop, todas las pistas "ALFSEG_*" que
        # hayan quedado de una concatenacion anterior -- si no, cada vez
        # que se pulsa "Concatenar segmentos" se acumularian pistas viejas
        # encima de las nuevas.
        _root_obj_pre = bpy.data.objects.get("alfred")
        seg_cfg_armature_pre = _resolve_armature(seg_cfg, scene)
        for _obj_pre in (_root_obj_pre, seg_cfg_armature_pre):
            if _obj_pre is not None and _obj_pre.animation_data:
                for _trk in list(_obj_pre.animation_data.nla_tracks):
                    if _trk.name.startswith("ALFSEG_"):
                        _obj_pre.animation_data.nla_tracks.remove(_trk)

        for pos, (orig_idx, seg) in enumerate(_indexed):
            # FIX (Kebyn, 2026-08-03: "al concatenar todos los segmentos no
            # sera necesario que me pida poses"; corregido el mismo dia:
            # "que no este por defecto parado.json al concatenar"): un
            # segmento sin action_poses YA NO se salta ni inyecta ninguna
            # pose por defecto (antes forzaba "parado.json", hardcodeado).
            # NO se llama a alfst.concatenate para ese segmento (ahi vive
            # la inyeccion de poses) -- se deja tal cual el desplazamiento
            # base ya horneado por la Capa 1 (regen de alfredpr.preview_path,
            # mas arriba en este mismo operador) en su rango [frame_start,
            # frame_end], sin ninguna pose superpuesta.
            #
            # BUGFIX (Kebyn, 2026-08-03, bis: "no se reproducen los filtros
            # organicos, solo los parpadeos"): _apply_organic_filters() SOLO
            # se ejecuta dentro de ALFST_OT_Concatenate.execute() (alfst.
            # concatenate) -- al saltarnos esa llamada para segmentos sin
            # poses, esos tramos se quedaban sin ningun post-proceso organico
            # (a diferencia del parpadeo, que es un sistema GLOBAL aparte via
            # alfst.concatenate_2, y por eso seguia sonando igual). Se aplica
            # aca manualmente sobre la Capa 1 ya horneada de este segmento,
            # para que la respiracion/head-sway/etc. tambien cubran los
            # tramos sin poses, igual que los que si tienen.
            #
            # BUGFIX (Kebyn, 2026-08-03, ter): el fix anterior modificaba
            # los fcurves de la action COMPARTIDA de Capa 1, pero nunca la
            # aislaba en su propia pista NLA -- el siguiente segmento CON
            # poses de la lista la borraba entera al concatenarse
            # (keep_existing_action=False borra TODA la action, no solo su
            # propio rango), asi que cualquier segmento sin poses procesado
            # antes de uno con poses perdia sus filtros organicos (y hasta
            # su desplazamiento base). Ver _copy_action_range() + _push_action_to_nla() (reescritos 2026-08-05 para aislamiento real).
            if not seg.action_poses:
                _done += 1
                f_s = seg.frame_start
                _, f_e_calc = _calc_seg_frames(seg)
                f_e = seg.frame_end if seg.frame_end > f_s else f_e_calc
                _f_min = f_s if _f_min is None else min(_f_min, f_s)
                _f_max = f_e if _f_max is None else max(_f_max, f_e)

                _arm_for_organic = _resolve_armature(seg_cfg, scene)
                # AISLAMIENTO POR SEGMENTO: usar la copia PROPIA de organic
                # de ESTE segmento (seg.organic), no la global de scene.alfst.
                _org = getattr(seg, "organic", None)

                _safe_label = "".join(
                    c if c.isalnum() else "_" for c in (seg.label or "seg")
                )[:32]
                _track_base_nofx = f"ALFSEG_{orig_idx:02d}_{_safe_label}_base"

                # AISLAMIENTO REAL (Kebyn, 2026-08-05: "si yo no he tocado
                # el segmento 3, no deberia afectarle lo que pase en el
                # segmento 2 -- falta un verdadero aislamiento entre
                # segmentos"). El fix anterior (base_overrides capturado
                # justo antes de mover el playhead) segia dependiendo de
                # tocar armature.animation_data.action y scene.frame_set()
                # -- es decir, del estado EN VIVO del objeto, que puede
                # verse afectado por el orden de procesamiento de otros
                # segmentos o por donde este parado el playhead.
                #
                # Ahora este tramo se construye ENTERO en dos actions
                # nuevas, en memoria (_copy_action_range), copiando
                # directamente los keyframes de [f_s, f_e] desde el
                # respaldo INTACTO de Capa 1 (_capa1_backup_arm_name /
                # _capa1_backup_root_name, guardado una sola vez ANTES de
                # arrancar el loop, ver mas arriba). Ni el armature ni el
                # root "alfred" en vivo se tocan en ningun momento -- no
                # hay swap de action, no hay frame_set(). El resultado de
                # ESTE segmento depende unicamente de esos datos ya
                # horneados, sin importar que otros segmentos (con o sin
                # poses) ya se hayan procesado antes o despues.
                if f_e > f_s:
                    try:
                        _bk_arm_act  = bpy.data.actions.get(_capa1_backup_arm_name) if _capa1_backup_arm_name else None
                        _bk_root_act = bpy.data.actions.get(_capa1_backup_root_name) if _capa1_backup_root_name else None

                        _new_arm_action  = _copy_action_range(_bk_arm_act,  f_s, f_e, _track_base_nofx + "_arm")
                        _new_root_action = _copy_action_range(_bk_root_act, f_s, f_e, _track_base_nofx + "_root")

                        if (_org is not None and _org.enabled
                                and _arm_for_organic is not None
                                and (_new_arm_action is not None or _new_root_action is not None)):
                            from .operators_anim import _apply_organic_filters
                            _apply_organic_filters(
                                context, _arm_for_organic, f_s, f_e, _org,
                                target_action=_new_arm_action,
                                target_action_root=_new_root_action)

                        _root_obj_nofx = bpy.data.objects.get("alfred")
                        if _arm_for_organic is not None:
                            _push_action_to_nla(
                                _arm_for_organic, _new_arm_action, f_s, f_e, _track_base_nofx + "_arm")
                        elif _new_arm_action is not None:
                            bpy.data.actions.remove(_new_arm_action)
                        if _root_obj_nofx is not None:
                            _push_action_to_nla(
                                _root_obj_nofx, _new_root_action, f_s, f_e, _track_base_nofx + "_root")
                        elif _new_root_action is not None:
                            bpy.data.actions.remove(_new_root_action)

                        if _bk_arm_act is None and _bk_root_act is None:
                            _errors.append(
                                f"Segmento '{seg.label}': no se encontro "
                                "respaldo de Capa 1 -- tramo sin "
                                "desplazamiento base")
                    except Exception as e_org:
                        _errors.append(
                            f"Segmento '{seg.label}': fallo al aislar el "
                            f"tramo sin poses ({e_org})")

                # BUGFIX (Kebyn, 2026-08-03: "no se estan reproduciendo los
                # parpadeos por defecto que son 1 por cada segmento
                # creado"): el parpadeo por-segmento (seg.blink_intervals)
                # solo se insertaba dentro de bpy.ops.alfst.concatenate(),
                # que esta rama NUNCA llama (los segmentos sin
                # action_poses hacen "continue" antes de llegar a esa
                # llamada, mas abajo). Resultado: cualquier segmento sin
                # pose superpuesta -- caminar/parada/saltar puros --
                # se quedaba sin su parpadeo default, aunque
                # _aplicar_defaults_organicos_y_parpadeo ya le hubiera
                # creado su intervalo. Se replica aqui el mismo bloque de
                # insercion de parpadeo que usa alfst.concatenate (ver
                # operators_anim.py, seccion "Parpadeo automatico"), leyendo
                # siempre la coleccion PROPIA de este segmento.
                _st_blink = getattr(scene, "alfst", None)
                _eye_s = getattr(_st_blink, "eye_expr", None) if _st_blink else None
                # BUGFIX (Kebyn + Claude, 2026-09-06): igual criterio que el
                # fix hermano en operators_anim.py -- "enabled" (Activar
                # expresiones de ojos) es el switch del sistema GLOBAL
                # legado, no debe bloquear el Parpadeo por-segmento, que
                # tiene su propio switch (blink_enabled). Antes exigia
                # ambos, asi que con el toggle maestro apagado el parpadeo
                # tampoco se aplicaba a los segmentos "sin pose" -- unico
                # de los 4 sistemas por-segmento de esta rama con esa
                # dependencia extra (Reir/Entendiendo/Expresiones aca abajo
                # ya solo miraban su propio switch).
                if (_eye_s is not None
                        and getattr(_eye_s, "blink_enabled", False)
                        and seg.blink_intervals):
                    try:
                        from .eye_system import apply_blink_sequence
                        _bi = seg.blink_intervals[
                            min(seg.blink_interval_idx, len(seg.blink_intervals) - 1)
                        ]
                        if _bi.enabled and _bi.frame_end > _bi.frame_start:
                            apply_blink_sequence(
                                _bi.frame_start, _bi.frame_end,
                                _bi.blink_count, _bi.blink_duration,
                            )
                    except Exception as e_blink:
                        _errors.append(
                            f"Segmento '{seg.label}': fallo al aplicar "
                            f"parpadeo ({e_blink})")

                # Filtro "Reir" -- oscilacion vertical sincronizada de ojos
                # (Kebyn, 2026-08-18). Mismo criterio que el bloque de
                # Parpadeo/Expresiones de arriba: esta rama ("sin pose")
                # nunca pasa por bpy.ops.alfst.concatenate(), asi que se
                # replica aca la aplicacion de seg.laugh_intervals. A
                # diferencia de Parpadeo (que solo usa el intervalo activo
                # en la UI), se recorren TODOS los intervalos habilitados
                # -- cada uno con su propio frame_start/frame_end explicito.
                if (_eye_s is not None and getattr(_eye_s, "laugh_enabled", False)
                        and seg.laugh_intervals):
                    try:
                        from .eye_system import apply_laugh_sequence
                        for _li in seg.laugh_intervals:
                            if _li.enabled and _li.frame_end > _li.frame_start:
                                apply_laugh_sequence(
                                    _li.frame_start, _li.frame_end, _li.oscillation_count,
                                )
                    except Exception as e_laugh:
                        _errors.append(
                            f"Segmento '{seg.label}': fallo al aplicar "
                            f"Reir ({e_laugh})")

                # Filtro "Entendiendo" -- glance parabolico sincronizado de
                # ojos (Kebyn, 2026-08-18). Mismo criterio que el bloque de
                # "Reir" arriba: esta rama ("sin pose") nunca pasa por
                # bpy.ops.alfst.concatenate(), asi que se replica aca la
                # aplicacion de seg.understand_intervals -- se recorren
                # TODOS los intervalos habilitados, cada uno con su propio
                # frame_start/frame_end/direction explicito.
                if (_eye_s is not None and getattr(_eye_s, "understand_enabled", False)
                        and seg.understand_intervals):
                    try:
                        from .eye_system import apply_understand_sequence
                        for _ui in seg.understand_intervals:
                            if _ui.enabled and _ui.frame_end > _ui.frame_start:
                                apply_understand_sequence(
                                    _ui.frame_start, _ui.frame_end, _ui.direction,
                                )
                    except Exception as e_und:
                        _errors.append(
                            f"Segmento '{seg.label}': fallo al aplicar "
                            f"Entendiendo ({e_und})")

                # BUGFIX (Kebyn + Claude, 2026-08-04): igual que el parpadeo
                # arriba -- las expresiones de ojos por-segmento
                # (seg.expr_intervals) solo se insertaban dentro de
                # bpy.ops.alfst.concatenate(), que esta rama NUNCA llama.
                # Se replica aca el mismo bloque de insercion de expresiones
                # que usa alfst.concatenate (ver operators_anim.py, seccion
                # "Expresiones de ojos por intervalos"), leyendo siempre la
                # coleccion PROPIA de este segmento.
                if (_eye_s is not None
                        and getattr(_eye_s, "expr_intervals_enabled", False)
                        and seg.expr_intervals):
                    try:
                        from .eye_system import (
                            apply_expression_to_eye as _apply_expr_nofx,
                            build_expression_shape_keys as _build_sk_nofx,
                        )
                        _active_ei_idx = [(idx, ei) for idx, ei in enumerate(seg.expr_intervals) if ei.enabled]
                        _left_eye_nofx  = bpy.data.objects.get("ojo_izquierdo_alfred")
                        _right_eye_nofx = bpy.data.objects.get("ojo_derecho_alfred")
                        # AISLAMIENTO POR SEGMENTO (Kebyn + Claude, 2026-08-05):
                        # genera el juego de shape keys PROPIO de este
                        # segmento ("Feliz__seg<orig_idx>", etc.) con su
                        # propia config (seg.eye_shapekey: Zona/Curva/
                        # Subdivisiones/Swap/Inv/intensidades) en vez de
                        # reusar el juego global sin sufijo -- asi Zona
                        # "Superior" en este segmento no afecta a los demas.
                        _seg_sk_suffix_nofx = f"__seg{orig_idx}"
                        if _active_ei_idx and _left_eye_nofx and _right_eye_nofx:
                            from .properties import (
                                ensure_eye_shapekey_migrated as _ensure_sk_mig_nofx,
                                ensure_expr_interval_shapekey_independent as _ensure_ei_sk_indep_nofx,
                            )
                            _ensure_sk_mig_nofx(seg, scene)
                            _ensure_ei_sk_indep_nofx(seg)

                        # MODO COMPARTIDO ELIMINADO (Kebyn, 2026-09-05: mismo
                        # criterio que en operators_anim.py -- toda expresion
                        # usa siempre su propio juego de shape keys
                        # independiente (ei.own_shapekey), sin fallback al
                        # juego compartido del segmento.
                        _built_sk_suffixes_nofx = set()

                        def _resolve_ei_shapekey_nofx(_ei, _ei_idx):
                            return _ei.own_shapekey, f"{_seg_sk_suffix_nofx}_ei{_ei_idx}"

                        if _active_ei_idx and _left_eye_nofx and _right_eye_nofx:
                            # BUGFIX (Kebyn, 2026-09-05, mismo problema
                            # reportado para operators_anim.py: "no limpia
                            # despues de apretar concatenar segmento... quedan
                            # residuos de la configuracion anterior"): esta
                            # rama ("sin pose superpuesta") replicaba la
                            # insercion de expresiones sin borrar antes los
                            # keyframes de una corrida previa en este mismo
                            # rango -- se aplica aca la misma limpieza.
                            from .eye_system import _clear_expression_keyframes_in_range as _clear_expr_nofx
                            for _eye_obj_clear in (_left_eye_nofx, _right_eye_nofx):
                                _clear_expr_nofx(_eye_obj_clear, f_s, f_e, suffix_filter=_seg_sk_suffix_nofx)
                            # FRAME DE INICIO ABSOLUTO (Kebyn, 2026-09-06):
                            # mismo criterio que la rama "con pose" de
                            # operators_anim.py -- resuelve manual_start
                            # via resolve_pose_start_frames y lo escribe en
                            # ei.frame_abs_start para que el panel lo muestre.
                            _active_eis_nofx = [ei for _idx, ei in _active_ei_idx]
                            _resolved_ei_starts_nofx = resolve_pose_start_frames(_active_eis_nofx, f_s)
                            for ei, _fs in zip(_active_eis_nofx, _resolved_ei_starts_nofx):
                                ei.frame_abs_start = _fs

                            for _ei_idx_nofx, ei in _active_ei_idx:
                                _ei_settings_nofx, _ei_suffix_nofx = _resolve_ei_shapekey_nofx(ei, _ei_idx_nofx)
                                if _ei_suffix_nofx not in _built_sk_suffixes_nofx:
                                    _build_sk_nofx(_left_eye_nofx,  _ei_settings_nofx, is_right_eye=False, name_suffix=_ei_suffix_nofx)
                                    _build_sk_nofx(_right_eye_nofx, _ei_settings_nofx, is_right_eye=True,  name_suffix=_ei_suffix_nofx)
                                    _built_sk_suffixes_nofx.add(_ei_suffix_nofx)

                                _expr_name_nofx = ei.expression.lower()
                                _f_start_nofx   = ei.frame_abs_start
                                _f_end_nofx     = _f_start_nofx + ei.duration - 1
                                _f_peak_nofx    = _f_start_nofx + ei.duration // 2
                                if _left_eye_nofx.data.shape_keys and _right_eye_nofx.data.shape_keys:
                                    for _eye_obj_nofx in (_left_eye_nofx, _right_eye_nofx):
                                        from .eye_system import apply_expression_interval
                                        apply_expression_interval(_eye_obj_nofx, _expr_name_nofx, ei.expression_value, _f_start_nofx, _f_end_nofx, name_suffix=_ei_suffix_nofx)

                                # FIX (2026-08-05): igual que arriba con el
                                # parpadeo/intensidad -- este bloque replicaba
                                # solo la intensidad del shape key de
                                # alfst.concatenate y se olvidaba por completo
                                # de la Posicion/Rotacion/Escala por ojo (ver
                                # operators_base.py, seccion "Expresiones de
                                # ojos -- multi-intervalo"). Resultado: los
                                # valores editados en "Editar expresion de
                                # ojos" (loc/rot/sca) quedaban guardados en
                                # seg.expr_intervals pero jamas se insertaban
                                # como keyframes en segmentos sin pose
                                # superpuesta -- las mallas de ojos no se
                                # movian aunque la intensidad de expresion si
                                # se aplicaba.
                                _base_L_nofx = EYE_BASE_TRANSFORMS.get("ojo_izquierdo_alfred", {})
                                _base_R_nofx = EYE_BASE_TRANSFORMS.get("ojo_derecho_alfred",   {})
                                _peak_L_nofx = {
                                    "loc": (ei.eye_L_loc_x, ei.eye_L_loc_y, ei.eye_L_loc_z),
                                    "rot": (ei.eye_L_rot_x, ei.eye_L_rot_y, ei.eye_L_rot_z),
                                    "sca": (ei.eye_L_sca_x, ei.eye_L_sca_y, ei.eye_L_sca_z),
                                }
                                _peak_R_nofx = {
                                    "loc": (ei.eye_R_loc_x, ei.eye_R_loc_y, ei.eye_R_loc_z),
                                    "rot": (ei.eye_R_rot_x, ei.eye_R_rot_y, ei.eye_R_rot_z),
                                    "sca": (ei.eye_R_sca_x, ei.eye_R_sca_y, ei.eye_R_sca_z),
                                }

                                def _keyframe_eye_transform_nofx(obj, td, frame):
                                    obj.location       = td["loc"]
                                    obj.rotation_euler = td["rot"]
                                    obj.scale          = td["sca"]
                                    obj.keyframe_insert(data_path="location",       frame=frame)
                                    obj.keyframe_insert(data_path="rotation_euler", frame=frame)
                                    obj.keyframe_insert(data_path="scale",          frame=frame)

                                if _base_L_nofx and _base_R_nofx:
                                    _keyframe_eye_transform_nofx(_left_eye_nofx,  _base_L_nofx, _f_start_nofx)
                                    _keyframe_eye_transform_nofx(_right_eye_nofx, _base_R_nofx, _f_start_nofx)
                                    _keyframe_eye_transform_nofx(_left_eye_nofx,  _peak_L_nofx, _f_peak_nofx)
                                    _keyframe_eye_transform_nofx(_right_eye_nofx, _peak_R_nofx, _f_peak_nofx)
                                    _keyframe_eye_transform_nofx(_left_eye_nofx,  _base_L_nofx, _f_end_nofx)
                                    _keyframe_eye_transform_nofx(_right_eye_nofx, _base_R_nofx, _f_end_nofx)
                    except Exception as e_expr:
                        _errors.append(
                            f"Segmento '{seg.label}': fallo al aplicar "
                            f"expresion de ojos ({e_expr})")

                # BUGFIX (Kebyn, 2026-09-01: "al apretar concatenar segmentos,
                # no se esta importando el objeto .blend que se escoje en la
                # interfaz"): igual criterio que Parpadeo/Reir/Entendiendo/
                # expresiones arriba -- el sistema de Lanzar/Recoger/Mantener
                # Objetos (seg.throws) solo se ejecutaba dentro de
                # bpy.ops.alfst.concatenate(), que esta rama ("sin poses")
                # NUNCA llama. Cualquier segmento sin pose superpuesta
                # (caminar/parada/salto puros) con un item de throw
                # configurado se quedaba sin importar/aplicar su objeto.
                # Se reutiliza run_throws_for_segments() (extraida de
                # operators_anim.py) pasandole solo este segmento.
                if seg.throws.enabled:
                    try:
                        from .operators_anim import run_throws_for_segments
                        _thr_imp_nofx, _thr_app_nofx, _thr_errs_nofx = \
                            run_throws_for_segments(context, [seg])
                        for _te_nofx in _thr_errs_nofx:
                            _errors.append(
                                f"Segmento '{seg.label}': throw ({_te_nofx})")
                    except Exception as e_thr_nofx:
                        _errors.append(
                            f"Segmento '{seg.label}': fallo al aplicar "
                            f"Lanzar/Recoger/Mantener ({e_thr_nofx})")

                # Mismo criterio que el bloque de throws de arriba: la
                # Invisibilidad de Malla (seg.hide_mesh) tambien depende de
                # run_hide_mesh_for_segments(), que solo se llama dentro de
                # bpy.ops.alfst.concatenate(); se reutiliza aca para que un
                # segmento sin poses tambien aplique sus intervalos de
                # invisibilidad configurados.
                if seg.hide_mesh.enabled:
                    try:
                        from .operators_anim import run_hide_mesh_for_segments
                        _hid_app_nofx, _hid_errs_nofx = \
                            run_hide_mesh_for_segments(context, [seg])
                        for _he_nofx in _hid_errs_nofx:
                            _errors.append(
                                f"Segmento '{seg.label}': invisibilidad ({_he_nofx})")
                    except Exception as e_hid_nofx:
                        _errors.append(
                            f"Segmento '{seg.label}': fallo al aplicar "
                            f"Invisibilidad de Malla ({e_hid_nofx})")

                _errors.append(
                    f"Segmento '{seg.label}': sin poses de accion, se dejo "
                    "solo el desplazamiento base (sin pose superpuesta)")
                continue

            # BUGFIX (Kebyn, 2026-07-10): pasar seg_idx explicitamente ademas
            # de active_index. alfst.concatenate ahora prioriza seg_idx, asi
            # que esto asegura que CADA llamada del loop inyecte las poses
            # del segmento que corresponde (orig_idx) y respete su propio
            # frame_start/frame_end, aunque active_index cambie mientras tanto.
            #
            # keep_existing_action=False (a diferencia de antes): cada
            # segmento arranca de una action limpia propia -- ya no
            # acumula sobre la del anterior. isolate_segments=True evita
            # que eso borre las pistas NLA de los segmentos ya empujados.
            seg_cfg.active_index = orig_idx

            # BUGFIX (Kebyn + Claude, 2026-07-13): bpy.ops.alfst.concatenate,
            # cuando no puede cargar una pose (self.report({'ERROR'}, ...) +
            # return {'CANCELLED'}), NO devuelve simplemente {'CANCELLED'} al
            # ser llamado desde Python -- Blender lo convierte en una
            # excepcion RuntimeError. Sin este try/except, esa excepcion se
            # propagaba sin capturar y tumbaba TODO "Concatenar segmentos"
            # (los 13 segmentos), en vez de solo marcar como fallido el
            # segmento con el dato problematico (ej. una pose faltante en
            # poses_dir) y seguir con el resto.
            try:
                result = bpy.ops.alfst.concatenate(
                    keep_existing_action=False, auto_play=False,
                    seg_idx=orig_idx, isolate_segments=True,
                    capa1_backup_arm=_capa1_backup_arm_name,
                    capa1_backup_root=_capa1_backup_root_name,
                )
            except RuntimeError as e_cat:
                _errors.append(f"Segmento '{seg.label}': fallo al concatenar ({e_cat})")
                continue

            if "FINISHED" not in result:
                _errors.append(f"Segmento '{seg.label}': fallo al concatenar")
                continue

            _done += 1
            f_s = seg.frame_start
            _, f_e_calc = _calc_seg_frames(seg)
            f_e = seg.frame_end if seg.frame_end > f_s else f_e_calc
            _f_min = f_s if _f_min is None else min(_f_min, f_s)
            _f_max = f_e if _f_max is None else max(_f_max, f_e)

        seg_cfg.active_index = _original_active

        # RED DE SEGURIDAD (Kebyn + Claude, 2026-08-04 ter): ademas del fix
        # en _push_action_to_nla (que ya deja obj.animation_data
        # action = None apenas aisla cada segmento sin poses), se fuerza
        # aca tambien -- por si algun camino distinto del loop de arriba
        # dejara una action colgando como "active action" del armature/
        # root. Con todo ya aislado en pistas NLA (extrapolation=
        # 'NOTHING'), no debe quedar ninguna action activa por encima:
        # cualquier action colgante ahi se evalua con action_extrapolation
        # 'HOLD' (default de Blender) y pisa el resto de la timeline fuera
        # de su propio rango.
        for _final_obj in (_arm_for_backup, _root_for_backup):
            if _final_obj is not None and _final_obj.animation_data:
                _final_obj.animation_data.action = None

        # Limpiar las copias de respaldo de Capa 1 -- ya cumplieron su
        # funcion (cada segmento las uso, si hacia falta, durante su
        # propio paso por el loop de arriba).
        for _bk_name in (_capa1_backup_arm_name, _capa1_backup_root_name):
            if _bk_name:
                _bk_act_cleanup = bpy.data.actions.get(_bk_name)
                if _bk_act_cleanup is not None:
                    bpy.data.actions.remove(_bk_act_cleanup)

        if _done == 0:
            self.report({"ERROR"}, "Ningun segmento pudo concatenarse: " + " | ".join(_errors))
            return {"CANCELLED"}

        # (La automatizacion de ojos -- build_eye_shape_keys + concatenate_2 --
        # ahora corre ANTES de este loop, no aca. Ver comentario mas arriba.)

        # ── Corrige las custom properties de reinyeccion (_concat_frame_start/
        #    _concat_frame_end) para que reflejen el rango GLOBAL de todos los
        #    segmentos concatenados, no solo el del ultimo procesado ──────────
        _root_obj = bpy.data.objects.get("alfred")
        seg_cfg_armature = _resolve_armature(seg_cfg, scene)
        for _obj in (_root_obj, seg_cfg_armature):
            if _obj is not None and _f_min is not None:
                _obj["_concat_frame_start"] = _f_min
                _obj["_concat_frame_end"]   = _f_max

        from .woodcut_animation import regenerate_woodcut_props
        regenerate_woodcut_props(scene, _f_min, _f_max)

        try:   # concatenar borra las pistas NLA del personaje (tambien las de voz de Voz Sync): se vuelven a crear (audio_import)
            from . import audio_import as _audio_import
            _audio_import.post_concatenar(context)
        except Exception as _e:
            print(f"[ConcatenarTodo] audio: {_e}")

        # Reproducir tambien los elementos del Guion 2.0 asociados a la
        # configuracion. Antes el usuario tenia que pulsar por separado
        # "Aplicar objetos y mundo" y "Aplicar sonidos", por lo que una
        # configuracion portable parecia incompleta tras CONCATENAR.
        # Ambos motores son idempotentes: reutilizan la antorcha ya
        # importada y actualizan/mueven las tiras de sonido existentes.
        try:
            from . import audio_import as _guion_ai
            _guion = _guion_ai.guion_de_escena(scene)
            if _guion and (_guion.get("objetos") or _guion.get("mundo")):
                from . import objetos_mundo as _guion_obj
                _obj_res = _guion_obj.calcular(context, _guion)
                _obj_n = _guion_obj.aplicar(context, _obj_res)
                _obj_vis = _guion_obj.aplicar_mundo_visibilidad(context, _guion)
                print(f"[ConcatenarTodo] Guion objetos: {_obj_n} horneados; mundo={_obj_vis}")
            if _guion and ((_guion.get("sonidos") or {}).get("manuales")):
                from . import sonidos_guion as _guion_snd
                _snd_res = _guion_snd.aplicar_sonidos(context, _guion, auto=False)
                print(f"[ConcatenarTodo] Guion sonidos: {_snd_res}")
        except Exception as _e_guion:
            _errors.append(f"Guion objetos/sonidos: {_e_guion}")
            print(f"[ConcatenarTodo] Guion objetos/sonidos: {_e_guion}")

        # ── Lanza la reproduccion de la secuencia completa, de principio a fin ──
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

        seg_cfg.segs_applied = True
        seg_cfg.status_msg = (
            f"Secuencia concatenada: {_done}/{len(_indexed)} segmentos, "
            f"frames {_f_min}->{_f_max}"
            + (f"  |  {len(_errors)} advertencias" if _errors else "")
        )
        for _e in _errors:
            print(f"[ConcatenarTodo] {_e}")
        self.report({"INFO"}, seg_cfg.status_msg)
        return {"FINISHED"}


# =============================================================================
# CRUD DE SEGMENTOS
# =============================================================================

class ALFREDSEG_OT_Add(Operator):
    bl_idname  = "alfredseg.add"
    bl_label   = "Agregar segmento"
    bl_description = "Agrega un nuevo segmento de refinado al Paso 3"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        segs = context.scene.alfred_segs
        pc   = context.scene.alfred_path

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
        # Foto del Paso 2 al momento de crear el segmento (ver
        # AlfredAnimSegment.frame_start_planned en properties.py). En
        # modo 1 coordenada fe es provisional (fs == fe); igual se guarda
        # como punto de partida, ya que en ese modo no hay "Estimacion de
        # segmentos" del Paso 2 que dependa de este valor.
        seg.frame_start_planned = fs
        seg.frame_end_planned = fe

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
            root_empty = context.scene.objects.get("alfred")

            seg_action_name = f"alfredseg_{seg.label.replace(' ','_')}"
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

                # Crear fcurves de desplazamiento en la seg_action
                fc_loc = [get_fcurves(seg_action).new(dp_loc, index=i) for i in range(3)]
                fc_rot = [get_fcurves(seg_action).new(dp_rot, index=i) for i in range(3)]

                # Evaluar el Empty frame a frame: su posicion/rotacion provienen
                # del NLA del Paso 2 y representan el desplazamiento puro del personaje
                frame_backup = context.scene.frame_current
                for _f in range(fs, fe + 1):
                    context.scene.frame_set(_f)
                    context.view_layer.update()
                    loc = root_empty.location
                    rot = root_empty.rotation_euler
                    for i in range(3):
                        fc_loc[i].keyframe_points.insert(frame=_f, value=loc[i], options={"FAST"})
                        fc_rot[i].keyframe_points.insert(frame=_f, value=rot[i], options={"FAST"})
                for fc in fc_loc + fc_rot:
                    for kp in fc.keyframe_points:
                        kp.interpolation = "BEZIER"
                        kp.easing = "AUTO"
                    fc.update()

                context.scene.frame_set(frame_backup)

                # Restaurar action previa del armature si existia
                if arm_obj and _prev_arm_action:
                    arm_obj.animation_data.action = _prev_arm_action

            # Asignar la seg_action como action activa del armature
            if arm_obj:
                if not arm_obj.animation_data:
                    arm_obj.animation_data_create()
                arm_obj.animation_data.action = seg_action

        # Copiar configuracion completa desde alfst (el sistema de poses actual)
        st = context.scene.alfst
        # Parametros globales
        seg.fps         = st.fps
        seg.entry_ratio = st.entry_ratio
        seg.exit_ratio  = st.exit_ratio
        seg.export_slot_number = st.export_slot_number
        seg.export_type        = st.export_type
        seg.export_desc        = st.export_desc
        # Copiar action_poses (src: AlfredPoseSlotItem, dst: AlfredSegmentPoseSlot)
        seg.action_poses.clear()
        for src_slot in st.action_poses:
            dst_slot = seg.action_poses.add()
            dst_slot.json_file   = getattr(src_slot, "json_file",   "")
            dst_slot.pose_name   = getattr(src_slot, "pose_name",   "")
            dst_slot.pose_label  = getattr(src_slot, "pose_label",  "") or getattr(src_slot, "pose_name", "")
            dst_slot.duration    = getattr(src_slot, "duration",    24)
            dst_slot.entry_ratio = getattr(src_slot, "entry_ratio", 0.3)
            dst_slot.exit_ratio  = getattr(src_slot, "exit_ratio",  0.3)
            dst_slot.interp_type = getattr(src_slot, "interp_type", "SMOOTH")
            dst_slot.rot_x = getattr(src_slot, "rot_x", 0.0)
            dst_slot.rot_y = getattr(src_slot, "rot_y", 0.0)
            dst_slot.rot_z = getattr(src_slot, "rot_z", 0.0)
            dst_slot.pos_x = getattr(src_slot, "pos_x", 0.0)
            dst_slot.pos_y = getattr(src_slot, "pos_y", 0.0)
            dst_slot.pos_z = getattr(src_slot, "pos_z", 0.0)
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

        # ── FIX (reportado por Kebyn: "algo esta bloqueando la reproduccion
        # de las poses en donde solo hay una coordenada"): filter_right_leg/
        # filter_right_knee/filter_left_leg/filter_left_knee tienen
        # default=True en properties.py ("el recorrido base las controla"),
        # pensado para tramos caminar/saltar donde el path_recorder SI anima
        # las piernas. En modo 1 coordenada (_single_coord) no existe ningun
        # recorrido — nada mas controla las piernas — asi que ese default
        # dejaba las poses con articulacion de piernas sin reproducirse
        # nunca (bones excluidos del bake, ver _excluded_bones/
        # _bone_blocked_at en operators_anim.py). Se destraban aqui
        # explicitamente para que el segmento 1-coord reproduzca la pose
        # completa, piernas incluidas.
        if _single_coord:
            seg.filter_right_leg  = False
            seg.filter_right_knee = False
            seg.filter_left_leg   = False
            seg.filter_left_knee  = False

        segs.active_index = len(segs.segments) - 1

        # Filtros organicos + parpadeo por defecto (reglas_alfred.zip),
        # PROPIOS de este segmento nuevo -- no afectan a los demas.
        _aplicar_defaults_organicos_y_parpadeo(context, seg)

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


class ALFREDSEG_OT_AutoSplitFromConfig(Operator):
    """
    NUEVO (pedido de Kebyn): en vez de que TODOS los tramos del recorrido
    (caminar/saltar_subir/saltar_bajar/parada) terminen acumulados en un
    solo AlfredAnimSegment gigante (ej. 1->1322), este operador crea UN
    AlfredAnimSegment por cada tramo del recorrido.

    ACTUALIZADO (Kebyn, 2026-08-02): ya no lee un configuracion.json por
    dialogo de archivo -- usa directamente la misma lista que ya se ve
    en el panel bajo "Estimacion de segmentos:" (calcular_estimacion_
    geometrica() / calcular_estimacion_slots() en path_recorder.py, la
    fuente que agrupa scene.alfred_path.path_points en tramos caminar/
    saltar_subir/saltar_bajar/parada). El boton "Dividir segmentos" crea
    tantos segmentos como tramos aparecen en esa lista, con frame_start/
    frame_end calculados acumulando "frames_estimados" de cada tramo a
    partir de scene.alfred_path.frame_inicio -- el mismo orden y las
    mismas duraciones que ya se preveian en el panel antes de dividir.

    Cada segmento nuevo queda:
      - label:  "{indice:02d}_{tipo}" — ej. "04_parada", "06_caminar".
      - frame_start / frame_end: acumulados desde la estimacion.
      - single_coord_mode = False (modo recorrido).
      - seg_action dedicada, generada igual que ALFREDSEG_OT_Add: se
        evalua el Empty "alfred" frame a frame dentro de [frame_start,
        frame_end] para capturar el desplazamiento puro del root ya
        resuelto por el NLA.
      - Poses (action_poses) y Bloqueador de bones
        quedan en blanco: cada tramo se configura despues individualmente.
    """
    bl_idname  = "alfredseg.autosplit_from_config"
    bl_label   = "Dividir segmentos"
    bl_description = (
        "Crea un segmento independiente por cada tramo (caminar/saltar_subir/"
        "saltar_bajar/parada) segun la 'Estimacion de segmentos' del "
        "recorrido grabado, en vez de un unico segmento que cubre todo "
        "el recorrido"
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
        pc = getattr(scene, "alfred_path", None)
        if pc is None:
            self.report({"ERROR"}, "No se encontro el recorrido (scene.alfred_path).")
            return {"CANCELLED"}

        slots_est = calcular_estimacion_geometrica(scene)
        if not slots_est:
            self.report({"ERROR"},
                "No hay 'Estimacion de segmentos' para dividir. Graba primero "
                "un recorrido en el Paso 2 (o carga una configuracion con "
                "recorrido) para que aparezca la lista en el panel.")
            return {"CANCELLED"}

        base_frame = pc.frame_inicio if pc.frame_inicio else 1
        tramos = []
        cursor = base_frame
        for s in slots_est:
            dur = max(1, int(s["frames_estimados"]))
            fs = cursor
            fe = fs + dur - 1
            tramo_entry = {"tipo": s["tipo"], "frame_start": fs, "frame_end": fe}
            # NUEVO (Kebyn, 2026-08-21): pasa la coordenada de destino de
            # la antorcha (seg_pts[1], ver calcular_estimacion_geometrica
            # en path_recorder.py) para que el bloque de abajo pueda
            # auto-registrar el AlfredThrowItem sin recalcular geometria.
            if s["tipo"] == "colocar_antorcha" and "torch_dest" in s:
                tramo_entry["torch_dest"] = s["torch_dest"]
            # NUEVO (Kebyn, 2026-08-22): mismo mecanismo que torch_dest de
            # arriba, para que el bloque de abajo auto-registre el
            # AlfredThrowItem de la mesa de crafteo sin recalcular
            # geometria (ver "table_dest" en calcular_estimacion_geometrica,
            # path_recorder.py).
            if s["tipo"] == "colocar_mesa_de_crafteo" and "table_dest" in s:
                tramo_entry["table_dest"] = s["table_dest"]
            # NUEVO (Kebyn, "crear pared NxN bloques"): mismo mecanismo que
            # torch_dest/table_dest de arriba, pero UNA lista de destinos
            # (uno por celda de la grilla) en vez de un solo punto -- ver
            # "wall_blocks_est" en calcular_estimacion_geometrica
            # (path_recorder.py). Tambien se pasa la ruta .blend elegida a
            # mano, que es la MISMA para todos los bloques del slot.
            if s["tipo"] == "crear_pared_nxn" and "wall_blocks_est" in s:
                tramo_entry["wall_blocks_est"] = s["wall_blocks_est"]
                tramo_entry["pared_bloque_blend_path"] = s.get("pared_bloque_blend_path", "")
            tramos.append(tramo_entry)
            cursor = fe + 1

        segs = context.scene.alfred_segs

        if self.reemplazar_existentes:
            for old_seg in segs.segments:
                if old_seg.seg_action_name:
                    old_act = bpy.data.actions.get(old_seg.seg_action_name)
                    if old_act:
                        bpy.data.actions.remove(old_act, do_unlink=True)
            segs.segments.clear()

        arm_obj = _resolve_armature(segs, scene)
        if arm_obj is None:
            arm_name = segs.armature_name or "Alfred"
            self.report({"ERROR"},
                f"No se encontro el armature '{arm_name}'. Verifica "
                "'Nombre armature' en la config del Paso 3.")
            return {"CANCELLED"}

        root_empty = scene.objects.get("alfred")
        if root_empty is None or not root_empty.animation_data:
            self.report({"WARNING"},
                "No se encontro el Empty 'alfred' con animation_data (recorrido "
                "de Pasos 1+2). Los segmentos se crearan con frame_start/"
                "frame_end correctos pero SIN captura de desplazamiento del "
                "root; genera primero el recorrido con path_recorder.")

        # FIX (Kebyn, "los movimientos del personaje solo se reproducen
        # hasta el 690, no hasta el 710"): tramos[] se arma arriba con el
        # total EN VIVO de calcular_estimacion_geometrica() (lee
        # pt.parada_frames_punto/frames por tramo tal como estan AHORA
        # en el Paso 1). Pero el desplazamiento real del root que este
        # operador va a samplear frame a frame mas abajo (root_empty.
        # location/rotation_euler, ver el for _f in range(fs, fe+1) de
        # abajo) es el que quedo GRABADO la ultima vez que se corrio
        # "Reproducir recorrido" (ALFREDPR_OT_PreviewPath, path_recorder.py)
        # -- ese es el que fijo pc.anim_frame_fin y el frame_range real
        # de la accion de root_empty.
        #
        # Si el usuario edita frames por parada (u otro tramo) DESPUES de
        # la ultima "Reproducir recorrido" y despues aprieta "Dividir
        # segmentos" sin volver a reproducir, el estimado en vivo (710)
        # queda MAS LARGO que el movimiento realmente grabado (690): los
        # ultimos frames del ultimo segmento (691-710 en este caso) no
        # tienen desplazamiento real que samplear -- root_empty.location
        # simplemente devuelve el ULTIMO valor evaluado (congelado), asi
        # que el personaje deja de moverse ahi aunque el segmento "exista"
        # hasta 710. Por eso el sintoma es "se reproduce solo hasta 690".
        #
        # En vez de dividir igual con datos muertos al final, se detecta
        # el desfase ANTES de crear nada y se le pide al usuario que
        # vuelva a correr "Reproducir recorrido" primero, para que el
        # movimiento grabado quede sincronizado con la estimacion actual.
        if root_empty is not None and root_empty.animation_data and root_empty.animation_data.action:
            _real_end = root_empty.animation_data.action.frame_range[1]
            _est_end  = tramos[-1]["frame_end"] if tramos else None
            if _est_end is not None and abs(_real_end - _est_end) >= 1:
                self.report({"ERROR"},
                    f"El recorrido grabado llega solo hasta el frame {_real_end:.0f}, "
                    f"pero la 'Estimacion de segmentos' actual suma {_est_end} frames "
                    f"-- probablemente cambiaste frames por parada (u otro tramo) "
                    f"despues de la ultima vez que corriste 'Reproducir recorrido'. "
                    f"Corre 'Reproducir recorrido' (Paso 2) de nuevo para regrabar el "
                    f"desplazamiento del root con los valores actuales y despues "
                    f"volve a dividir segmentos -- si divides ahora, los ultimos "
                    f"frames del ultimo tramo quedarian sin movimiento real (congelados).")
                return {"CANCELLED"}

        # ── Auto-detectar el bone raiz real del armature ────────────────────
        # 'Hips_alfred' es el raiz del rig humanoide de Alfred (BONES_LISTA_FULL,
        # constants.py). 'spine_6' es del rig cuadrupedo de Jerry (Dog_001_rig).
        # Se intenta en ese orden y, si ninguno existe, se usa el primer pose
        # bone sin padre (raiz real de la jerarquia) como ultimo recurso.
        _root_bone_name = None
        for _candidate in ("Hips_alfred", "spine_6"):
            if arm_obj.pose.bones.get(_candidate) is not None:
                _root_bone_name = _candidate
                break
        if _root_bone_name is None:
            for pb in arm_obj.pose.bones:
                if pb.parent is None:
                    _root_bone_name = pb.name
                    break
        if _root_bone_name is None:
            self.report({"ERROR"},
                f"No se pudo determinar el bone raiz de '{arm_obj.name}' "
                "(no se encontro 'Hips_alfred', 'spine_6' ni ningun bone sin padre).")
            return {"CANCELLED"}

        st = context.scene.alfst
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

                suffix = "_intervalo_caminata_normal" if tramo.get("intervalo_caminata_normal") else ""
                label = f"{i:02d}_{tipo}{suffix}"

                seg = segs.segments.add()
                seg.label = label
                seg.frame_start = fs
                seg.frame_end = fe
                seg.single_coord_mode = False
                seg.frame_end_auto = 0
                # Foto del Paso 2 (ver comentario en properties.py,
                # AlfredAnimSegment.frame_start_planned): esta es la unica
                # vez que estos dos campos se setean al DIVIDIR el
                # recorrido -- de aca en mas las poses del Paso 3 pueden
                # mover frame_start/frame_end libremente sin afectarlos.
                seg.frame_start_planned = fs
                seg.frame_end_planned = fe

                seg_action_name = f"alfredseg_{label}"[:63]
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
                    fc_loc = [get_fcurves(seg_action).new(dp_loc, index=k) for k in range(3)]
                    fc_rot = [get_fcurves(seg_action).new(dp_rot, index=k) for k in range(3)]

                    for _f in range(fs, fe + 1):
                        scene.frame_set(_f)
                        context.view_layer.update()
                        loc = root_empty.location
                        rot = root_empty.rotation_euler
                        for k in range(3):
                            fc_loc[k].keyframe_points.insert(frame=_f, value=loc[k], options={"FAST"})
                            fc_rot[k].keyframe_points.insert(frame=_f, value=rot[k], options={"FAST"})
                    for fc in fc_loc + fc_rot:
                        for kp in fc.keyframe_points:
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

                # ── FIX 2026-07-12 (pedido de Kebyn: "necesito que el addon
                # solo importe la configuracion.json" — el bloqueo de
                # piernas no debe depender de un paso manual en el panel,
                # debe derivarse 100% de tramo["tipo"] tal como ya viaja
                # en configuracion.json):
                #
                #   - "caminar" (incluye "..._intervalo_caminata_normal"):
                #     piernas BLOQUEADAS (filter_*_leg/knee = True). El
                #     recorrido base (path_recorder.py) ya anima las
                #     piernas con el ciclo de caminata; si la pose del
                #     segmento tambien las tocara, se pisarian entre si.
                #   - "parada": mecanicamente el root queda detenido (sin
                #     recorrido real bajo los pies en ese rango).
                #     SECUENCIA_PIPELINE.md documenta que ahi la pose debe
                #     controlar el cuerpo libremente -> piernas LIBRES
                #     (filter_*_leg/knee = False) ademas de torso/cabeza/
                #     brazos (que ya nacen en False).
                #   - "saltar_subir" / "saltar_bajar": la mecanica de
                #     salto necesita libertad total de piernas -> LIBRES
                #     (False), igual que parada.
                #
                # Root/Armature (filter_main_bone) SI se mantiene
                # bloqueado siempre, para los 4 tipos por igual, por
                # REGLA_ROOT_BLOQUEADO_MULTICOORDENADA (el desplazamiento
                # del root en todo el recorrido lo controla unicamente el
                # Empty "alfred" capturado arriba, nunca la pose del
                # segmento) — se fija explicito aqui en vez de confiar en
                # el default de la property, para que no dependa de que
                # alguien lo haya tildado a mano alguna vez en el panel.
                #
                # Con esto, un config.json fresco generado por el
                # pipeline (reglas/alfred_evolution_engine.py) produce
                # segmentos con el bloqueo correcto desde el primer
                # AutoSplit, sin ningun ajuste manual posterior en el
                # panel para que "parada"/"saltar_*" reproduzcan la pose
                # completa. Si un caso puntual necesitara lo contrario
                # (ej. una parada con piernas quietas a proposito), el
                # usuario sigue pudiendo tildar/destildar el filtro a
                # mano despues — esto solo fija el punto de partida
                # correcto por tipo.
                _piernas_bloqueadas = tipo == "caminar"
                seg.filter_main_bone  = True
                seg.filter_right_leg  = _piernas_bloqueadas
                seg.filter_right_knee = _piernas_bloqueadas
                seg.filter_left_leg   = _piernas_bloqueadas
                seg.filter_left_knee  = _piernas_bloqueadas

                # Filtros organicos + parpadeo por defecto (reglas_alfred.zip),
                # PROPIOS de ESTE segmento -- cada tramo generado por AutoSplit
                # queda aislado del resto (ver _aplicar_defaults_organicos_y_parpadeo).
                _aplicar_defaults_organicos_y_parpadeo(context, seg)

                # ── NUEVO (Kebyn, 2026-08-21): auto-registro de la antorcha ──
                # via el Sistema de Lanzar/Recoger/Mantener Objetos. Para un
                # tramo "colocar_antorcha", se agrega automaticamente UN
                # AlfredThrowItem modo THROW (el objeto "sale" de la mano y
                # llega a destino, exactamente el mismo mecanismo que ya usa
                # el sistema para armas/objetos) con transition_out='NONE' --
                # la antorcha NO desaparece al terminar: se queda plantada en
                # el suelo para el resto de la escena. La fuente es siempre
                # antorcha_1.blend (bloques_dinamicos/antorcha_1/), empezando
                # por el Empty raiz "antorcha_1"; las siguientes antorchas del
                # mismo recorrido se numeran solas via
                # aplicar_sufijo_numerico_anticolision() (object_import_utils.py)
                # al momento de importar, asi que aca no hace falta enumerar
                # manualmente antorcha_2/antorcha_3/etc.
                if tipo == "colocar_antorcha":
                    _torch_dest = tramo.get("torch_dest")
                    if _torch_dest is None:
                        errores.append(
                            f"Tramo {i} (colocar_antorcha): sin coordenada de "
                            "destino (torch_dest) -- no se registro el throw "
                            "de la antorcha, agregala a mano en 'Lanzar/Recoger'.")
                    else:
                        # ACTUALIZADO (Kebyn, 2026-08-21): la antorcha ya NO
                        # recorre una trayectoria de lanzamiento a lo largo
                        # de todo el tramo (fs->fe) -- debe permanecer
                        # oculta y aparecer de golpe EXACTAMENTE en el frame
                        # en que el cuerpo esta en la pose de
                        # inclinado_colocando_antorcha.json (ver
                        # MID_FRAME_COLOCAR_ANTORCHA/TORCH_APPEAR_FRAME en
                        # generate_slots_alfred.py). frame_start==frame_end
                        # en ese instante hace que apply_throw_item()
                        # coloque el objeto directo en destino sin arco de
                        # vuelo, y hide_until_frame(appear_frame=frame_start)
                        # lo mantiene oculto hasta entonces.
                        from .generate_slots_alfred import MID_FRAME_COLOCAR_ANTORCHA as _MFCA
                        _torch_appear_frame = fs + _MFCA
                        seg.throws.enabled = True
                        _titem = seg.throws.items.add()
                        _titem.label          = f"Antorcha (tramo {i:02d})"
                        _titem.enabled        = True
                        _titem.mode           = 'THROW'
                        _titem.object_folder  = 'bloques_dinamicos'
                        _titem.blend_filename = 'antorcha_1.blend'
                        _titem.object_name    = 'antorcha_1'
                        _titem.levels_up      = 4
                        # Sale de la mano derecha (mismo bone que sostiene
                        # objetos de "lanzar/recoger" -- Rightelbow_alfred
                        # es el ultimo bone disponible del brazo derecho en
                        # BONES_LISTA_FULL; si el rig llegara a tener un
                        # bone de mano/muneca dedicado, cambiar aca).
                        _titem.parent_armature = arm_obj.name
                        _titem.parent_bone     = "Rightelbow_alfred"
                        _titem.frame_start    = _torch_appear_frame
                        _titem.frame_end      = _torch_appear_frame
                        _titem.target_armature = arm_obj.name
                        _titem.target_bone     = "Rightelbow_alfred"
                        _titem.dest_x = _torch_dest["x"]
                        _titem.dest_y = _torch_dest["y"]
                        _titem.dest_z = _torch_dest["z"]
                        _titem.easing_global = 'EASE_OUT'
                        # La antorcha se queda plantada -- no desaparece.
                        _titem.transition_in  = 'NONE'
                        _titem.transition_out = 'NONE'

                # ── NUEVO (Kebyn, 2026-08-22): auto-registro de la mesa ──
                # de crafteo, misma arquitectura EXACTA que el bloque de
                # "colocar_antorcha" de arriba -- ver ese comentario para el
                # detalle completo. La fuente es siempre
                # mesa_de_crafteo_1.blend (bloques_dinamicos/mesa_de_crafteo_1/),
                # empezando por el Empty raiz "mesa_de_crafteo_1"; las
                # siguientes mesas del mismo recorrido se numeran solas
                # (mesa_de_crafteo_2, mesa_de_crafteo_3...) via
                # aplicar_sufijo_numerico_anticolision() (object_import_utils.py)
                # al momento de importar.
                if tipo == "colocar_mesa_de_crafteo":
                    _table_dest = tramo.get("table_dest")
                    if _table_dest is None:
                        errores.append(
                            f"Tramo {i} (colocar_mesa_de_crafteo): sin coordenada de "
                            "destino (table_dest) -- no se registro el throw "
                            "de la mesa, agregala a mano en 'Lanzar/Recoger'.")
                    else:
                        # La mesa permanece oculta y aparece de golpe
                        # EXACTAMENTE en el frame en que el cuerpo esta en
                        # la pose de colocando_mesa_de_crafteo.json (ver
                        # MID_FRAME_COLOCAR_MESA_CRAFTEO en
                        # generate_slots_alfred.py). frame_start==frame_end
                        # en ese instante hace que apply_throw_item()
                        # coloque el objeto directo en destino sin arco de
                        # vuelo, y hide_until_frame(appear_frame=frame_start)
                        # lo mantiene oculto hasta entonces.
                        from .generate_slots_alfred import MID_FRAME_COLOCAR_MESA_CRAFTEO as _MFCM
                        _table_appear_frame = fs + _MFCM
                        seg.throws.enabled = True
                        _titem = seg.throws.items.add()
                        _titem.label          = f"Mesa de crafteo (tramo {i:02d})"
                        _titem.enabled        = True
                        _titem.mode           = 'THROW'
                        _titem.object_folder  = 'bloques_dinamicos'
                        _titem.blend_filename = 'mesa_de_crafteo_1.blend'
                        _titem.object_name    = 'mesa_de_crafteo_1'
                        _titem.levels_up      = 4
                        # Sale de la mano derecha, mismo bone que la
                        # antorcha (ver comentario de arriba).
                        _titem.parent_armature = arm_obj.name
                        _titem.parent_bone     = "Rightelbow_alfred"
                        _titem.frame_start    = _table_appear_frame
                        _titem.frame_end      = _table_appear_frame
                        _titem.target_armature = arm_obj.name
                        _titem.target_bone     = "Rightelbow_alfred"
                        _titem.dest_x = _table_dest["x"]
                        _titem.dest_y = _table_dest["y"]
                        _titem.dest_z = _table_dest["z"]
                        _titem.easing_global = 'EASE_OUT'
                        # La mesa se queda plantada -- no desaparece.
                        _titem.transition_in  = 'NONE'
                        _titem.transition_out = 'NONE'

                # ── NUEVO ("crear pared NxN bloques"): auto-registro, UN ──
                # AlfredThrowItem por celda de la grilla (no uno solo como
                # antorcha/mesa) -- misma arquitectura de "aparece de golpe
                # y se queda plantado", pero la fuente es el .blend elegido
                # a mano por el usuario (item.blend_path), marcada con
                # object_folder='pared_nxn_bloque' para que
                # apply_throw_item() (operators_anim.py) la resuelva por
                # ruta libre en vez de la carpeta fija bloques_dinamicos/
                # (ver ese comentario ahi para el detalle completo).
                if tipo == "crear_pared_nxn":
                    _wall_blocks = tramo.get("wall_blocks_est")
                    _wall_blend_path = (tramo.get("pared_bloque_blend_path") or "").strip()
                    if not _wall_blocks:
                        errores.append(
                            f"Tramo {i} (crear_pared_nxn): sin grilla de bloques "
                            "(wall_blocks_est) -- no se registraron los throws, "
                            "agregalos a mano en 'Lanzar/Recoger'.")
                    elif not _wall_blend_path:
                        errores.append(
                            f"Tramo {i} (crear_pared_nxn): no se eligio el archivo "
                            ".blend del bloque de 1m3 en el Paso 1 -- no se "
                            "registraron los throws.")
                    else:
                        seg.throws.enabled = True
                        for _wb in _wall_blocks:
                            _block_appear_frame = fs + int(_wb.get("appear_frame_rel", 0))
                            _titem = seg.throws.items.add()
                            _titem.label          = (
                                f"Pared bloque r{_wb['row']}c{_wb['col']} (tramo {i:02d})")
                            _titem.enabled        = True
                            _titem.mode           = 'THROW'
                            _titem.blend_path     = _wall_blend_path
                            _titem.object_folder  = 'pared_nxn_bloque'
                            _titem.blend_filename = ''
                            _titem.object_name    = ''
                            _titem.levels_up      = 4
                            # Sale de la mano derecha, mismo bone que
                            # antorcha/mesa (ver comentario de arriba).
                            _titem.parent_armature = arm_obj.name
                            _titem.parent_bone     = "Rightelbow_alfred"
                            _titem.frame_start    = _block_appear_frame
                            _titem.frame_end      = _block_appear_frame
                            _titem.target_armature = arm_obj.name
                            _titem.target_bone     = "Rightelbow_alfred"
                            _titem.dest_x = _wb["x"]
                            _titem.dest_y = _wb["y"]
                            _titem.dest_z = _wb["z"]
                            # FIX ("crear pared NxN" colocaba cada bloque
                            # mirando en una direccion distinta): antes acá
                            # NUNCA se tocaban rot_x/rot_y/rot_z (quedaban
                            # en su default 0.0), y apply_throw_item()
                            # tampoco los usaba -- el bloque quedaba con la
                            # rotacion MUNDIAL instantanea de la mano de
                            # Alfred en el frame exacto en que se "suelta"
                            # (ver fix en apply_throw_item, operators_anim.py),
                            # que varia levemente de un bloque a otro por
                            # interpolacion/easing. Ahora se fija
                            # explicitamente al heading de la pared
                            # (wall_blocks_est[].rot_z, calculado una sola
                            # vez para toda la grilla en
                            # _compute_wall_grid_coords) -- todos los
                            # bloques quedan orientados IGUAL entre si, de
                            # frente al recorrido.
                            _titem.rot_x = 0.0
                            _titem.rot_y = 0.0
                            _titem.rot_z = _wb.get("rot_z", 0.0)
                            _titem.easing_global = 'EASE_OUT'
                            # Cada bloque de la pared se queda plantado --
                            # no desaparece.
                            _titem.transition_in  = 'NONE'
                            _titem.transition_out = 'NONE'

                creados += 1

            except Exception as e_seg:
                import traceback
                print(f"[JRRSTSeg] Error en tramo {i} ({tramo.get('tipo')}):")
                print(traceback.format_exc())
                errores.append(f"Tramo {i} ({tramo.get('tipo')}): {e_seg}")
                # Si se alcanzo a crear el seg pero fallo despues, no lo dejamos a medias
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

        for area in context.screen.areas:
            area.tag_redraw()

        msg = f"{creados}/{len(tramos)} segmentos creados (root bone: '{_root_bone_name}')"
        if errores:
            msg += f"  |  {len(errores)} con problemas (ver consola)"
            for e in errores:
                print(f"[JRRSTSeg] {e}")
            self.report({"WARNING"}, msg)
        else:
            self.report({"INFO"}, msg)
        return {"FINISHED"}


class ALFREDSEG_OT_UpdateFromEstimacion(Operator):
    """
    Actualiza los segmentos YA CREADOS del Paso 3 (scene.alfred_segs.segments)
    para que reflejen los frames por parada actuales (default 'Frames por
    parada' + individuales de pc.paradas_frames), sin tener que volver a
    dividir desde cero (eso borraria poses/filtros/configuracion ya cargada
    en cada segmento -- ver ALFREDSEG_OT_AutoSplitFromConfig).

    Por que hace falta: calcular_estimacion_slots() (path_recorder.py), una
    vez que ya existen segmentos reales, lee esos segmentos TAL CUAL estan
    (fuente 'paso3_segmentos') -- ya no vuelve a mirar la geometria del
    recorrido. Si el usuario sube o baja 'Frames por parada' DESPUES de
    dividir en Paso 3, ese cambio nunca se propaga a los segmentos reales
    ni al panel "Estimacion de segmentos". Este operador cierra ese hueco.

    Logica, tramo por tramo (mismo orden que la geometria actual del
    recorrido, via calcular_estimacion_geometrica):
      - Si el tramo es de tipo "parada" y el segmento real correspondiente
        NO tiene action_poses propias (nunca se le agrego una pose
        intermedia): se reajusta frame_end para que coincida con el nuevo
        valor de 'Frames por parada' (default o individual).
      - Si el tramo es de tipo "caminar": se compara el estilo elegido
        AHORA en el dropdown (pc.walk_styles[i].style) contra el estilo
        que quedo "horneado" la ultima vez (pc.walk_styles[i].applied_style,
        ver ALFREDWalkStyleEntry en path_recorder.py). Si el usuario NO
        cambio el estilo, el tramo se deja intacto (misma logica de
        siempre: la duracion real puede venir del pipeline externo --
        historia, obstaculos, numero de pasos -- y no de esta formula
        geometrica). Si el usuario SI cambio el estilo (ej. de "Caminar
        Rapido" a "Caminar Herido"), se asume que quiere que la duracion
        refleje ese estilo nuevo y se reajusta frame_end con la formula
        geometrica (distancia del tramo x velocidad del estilo elegido),
        exactamente igual que se hace con "parada" mas abajo.
      - CORREGIDO (2026-08-05): un segmento con action_poses YA NO queda
        excluido del reajuste. Desde el fix del 2026-08-04 en
        _calc_seg_frames()/panels.py, frame_end_planned es siempre la
        fuente de verdad del rango en modo recorrido y las poses solo
        tienen que caber adentro -- este operador ahora reajusta esos
        segmentos igual que uno sin poses (las poses en si no se tocan;
        si dejan de caber en el nuevo rango, se avisa al terminar, mismo
        criterio que el warning "Las poses ocupan Xf pero el segmento
        solo tiene Yf" del panel del Paso 3).
      - Los tramos "saltar_subir"/"saltar_bajar" NUNCA se reajustan de
        duracion aqui. Solo se reubican (se desplazan) si algun tramo
        anterior cambio de tamano, para mantener la secuencia contigua.
      - En todos los casos, cualquier cambio de tamano se propaga en
        cascada a todos los segmentos siguientes.
    """
    bl_idname    = "alfredseg.update_from_estimacion"
    bl_label     = "Actualizar segmentos con la estimacion actual"
    bl_description = (
        "Reajusta el rango de frames de los tramos 'parada' ya creados en "
        "el Paso 3 segun los valores actuales de 'Frames por parada' "
        "(default e individuales). Tambien reajusta un tramo 'caminar' si "
        "se le cambio el estilo de caminata (dropdown) desde la ultima "
        "vez que se presiono este boton, usando la formula geometrica del "
        "estilo nuevo. Los tramos de caminata sin cambio de estilo, y los "
        "de salto, solo se reubican en cascada, nunca cambian de "
        "duracion. No borra ni modifica poses, filtros ni ninguna otra "
        "configuracion ya cargada en los segmentos"
    )
    bl_options   = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        pc = getattr(scene, "alfred_path", None)
        segs_data = getattr(scene, "alfred_segs", None)
        if pc is None or segs_data is None or not segs_data.segments:
            self.report({"WARNING"},
                "No hay segmentos del Paso 3 para actualizar. Usa "
                "'Auto-dividir' primero.")
            return {"CANCELLED"}

        slots_geo = calcular_estimacion_geometrica(scene)
        if not slots_geo:
            self.report({"WARNING"},
                "No se pudo calcular la estimacion geometrica del recorrido "
                "(graba o carga un recorrido de 2+ puntos primero).")
            return {"CANCELLED"}

        real_segs = list(segs_data.segments)
        if len(slots_geo) != len(real_segs):
            self.report({"WARNING"},
                f"La cantidad de tramos detectados en el recorrido "
                f"({len(slots_geo)}) no coincide con los segmentos ya "
                f"creados ({len(real_segs)}). Si agregaste o quitaste "
                "paradas/tramos del recorrido, usa 'Auto-dividir' para "
                "re-crear los segmentos desde cero (perderas las poses "
                "cargadas). Si solo cambiaste los frames de una parada "
                "existente, esto no deberia pasar -- revisa el orden.")
            return {"CANCELLED"}

        delta_acum   = 0
        n_reajustados = 0
        n_reubicados  = 0
        # NUEVO (Kebyn, 2026-08-05): segmentos que quedaron mas cortos que
        # la suma de duracion de sus action_poses tras el reajuste -- se
        # avisa al final (mismo criterio que el warning de panels.py,
        # "Las poses ocupan Xf pero el segmento solo tiene Yf"), las poses
        # en si NO se tocan.
        segs_poses_desbordadas = []
        for rseg, slot in zip(real_segs, slots_geo):
            if delta_acum:
                rseg.frame_start += delta_acum
                rseg.frame_end   += delta_acum
                if rseg.single_coord_mode:
                    rseg.frame_end_auto += delta_acum
                # La foto del Paso 2 (frame_start_planned/frame_end_planned)
                # tambien se reubica en cascada aca -- este operador SI es
                # un cambio legitimo del Paso 2 (frames por parada nuevos),
                # a diferencia de las poses del Paso 3, que nunca deben
                # tocar estos dos campos.
                rseg.frame_start_planned += delta_acum
                rseg.frame_end_planned   += delta_acum
                n_reubicados += 1

            # CORREGIDO (Kebyn, 2026-08-05): antes, cualquier segmento con
            # action_poses quedaba EXCLUIDO de por vida de este reajuste
            # ("su duracion la siguen definiendo esas poses"). Eso quedo
            # desactualizado por el fix del mismo dia 2026-08-04 en
            # _calc_seg_frames()/panels.py: desde ese fix, frame_end_planned
            # (la foto del Paso 2/3) es SIEMPRE la fuente de verdad del
            # rango del segmento en modo recorrido -- las poses solo tienen
            # que CABER dentro de ese rango (si no caben, el panel ya avisa
            # con "Las poses ocupan Xf pero el segmento solo tiene Yf").
            # Con la version vieja de este operador, apenas una parada
            # tenia una sola pose cargada, subir/bajar su "Frames" en el
            # Paso 1 dejaba de tener efecto para siempre en ese tramo --
            # exactamente el bug reportado. Ahora se reajusta igual que un
            # segmento sin poses; las poses de adentro NO se tocan (ni se
            # recortan ni se re-escalan), solo puede quedar de sobra o de
            # menos espacio para ellas dentro del nuevo rango (se avisa
            # abajo si se pasan). single_coord_mode se deja afuera a
            # proposito: ahi la duracion SI la siguen definiendo las poses
            # (ver _calc_seg_frames), pero este operador solo procesa
            # segmentos de recorrido (single_coord_mode = False siempre en
            # AutoSplitFromConfig), asi que es una salvaguarda defensiva.
            if rseg.single_coord_mode:
                continue

            # NUEVO (Kebyn, 2026-08-04): un tramo "caminar" SI se reajusta,
            # pero solo cuando el usuario cambio el dropdown de estilo
            # desde la ultima vez que se aplico -- no en cada click de
            # "Actualizar" (eso seguiria corrompiendo tramos cuya duracion
            # real viene del pipeline externo, ver el bug historico de
            # '01_caminar' 96f -> 20f). Se detecta comparando
            # walk_styles[i].style (lo elegido AHORA) contra
            # walk_styles[i].applied_style (lo horneado la ULTIMA vez).
            if slot["tipo"] == "caminar":
                _idx = slot.get("caminar_idx")
                if _idx is not None and _idx < len(pc.walk_styles):
                    entry = pc.walk_styles[_idx]
                    if entry.applied_style == "":
                        # Sin "foto" todavia (archivo viejo o tramo recien
                        # creado): solo se establece, sin recalcular nada,
                        # para no alterar una duracion real ya cargada.
                        entry.applied_style = entry.style
                    elif entry.style != entry.applied_style:
                        nuevo_dur = max(1, int(slot["frames_estimados"]))
                        actual_dur = rseg.frame_end - rseg.frame_start + 1
                        delta_dur = nuevo_dur - actual_dur
                        entry.applied_style = entry.style
                        if delta_dur != 0:
                            rseg.frame_end = rseg.frame_start + nuevo_dur - 1
                            if rseg.single_coord_mode:
                                rseg.frame_end_auto = rseg.frame_end
                            rseg.frame_end_planned = rseg.frame_end
                            if not rseg.frame_start_planned:
                                rseg.frame_start_planned = rseg.frame_start
                            delta_acum += delta_dur
                            n_reajustados += 1
                            if rseg.action_poses:
                                _pd = sum(int(ap.duration) for ap in rseg.action_poses)
                                if _pd > nuevo_dur:
                                    segs_poses_desbordadas.append((rseg.label, _pd, nuevo_dur))
                continue

            # SOLO se reajusta la duracion de tramos "parada" (lo unico que,
            # ademas del caso "caminar" de arriba, este boton promete
            # sincronizar) -- 'Frames por parada'. Los tramos
            # saltar_subir/saltar_bajar NO se tocan: la formula geometrica
            # (calcular_estimacion_geometrica) es solo una ESTIMACION y el
            # pipeline externo que genero el segmento real puede haber
            # usado otra logica (historia, obstaculos, numero de pasos,
            # etc.) cuya duracion es la fuente de verdad. Igual se reubican
            # con el resto en cascada arriba.
            if slot["tipo"] != "parada":
                continue

            nuevo_dur = max(1, int(slot["frames_estimados"]))
            actual_dur = rseg.frame_end - rseg.frame_start + 1
            delta_dur = nuevo_dur - actual_dur
            if delta_dur == 0:
                continue

            rseg.frame_end = rseg.frame_start + nuevo_dur - 1
            if rseg.single_coord_mode:
                rseg.frame_end_auto = rseg.frame_end
            rseg.frame_end_planned = rseg.frame_end
            if not rseg.frame_start_planned:
                rseg.frame_start_planned = rseg.frame_start
            delta_acum += delta_dur
            n_reajustados += 1
            if rseg.action_poses:
                _pd = sum(int(ap.duration) for ap in rseg.action_poses)
                if _pd > nuevo_dur:
                    segs_poses_desbordadas.append((rseg.label, _pd, nuevo_dur))

        for area in context.screen.areas:
            area.tag_redraw()

        if n_reajustados == 0 and n_reubicados == 0:
            self.report({"INFO"}, "Los segmentos ya coinciden con la estimacion actual.")
        else:
            msg = (f"{n_reajustados} segmento(s) reajustado(s) | "
                   f"{n_reubicados} reubicado(s) en cascada")
            if segs_poses_desbordadas:
                detalle = ", ".join(
                    f"{lbl} ({pd}f de poses > {nd}f nuevos)"
                    for lbl, pd, nd in segs_poses_desbordadas
                )
                self.report({"WARNING"},
                    msg + f" | ATENCION: {detalle} -- revisa/recorta esas poses.")
            else:
                self.report({"INFO"}, msg)
        return {"FINISHED"}


class ALFREDSEG_OT_Remove(Operator):
    bl_idname  = "alfredseg.remove"
    bl_label   = "Eliminar segmento"
    bl_description = "Elimina el segmento activo"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.alfred_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if 0 <= idx < len(segs.segments):
            segs.segments.remove(idx)
            segs.active_index = max(0, idx - 1)
            self.report({"INFO"}, "Segmento eliminado")
        else:
            self.report({"WARNING"}, "No hay segmento seleccionado")
        return {"FINISHED"}


class ALFREDSEG_OT_AddBoneInterval(Operator):
    """Agrega un nuevo intervalo de bloqueo de frames para un bone especifico
    del Bloqueador de bones de este segmento."""
    bl_idname  = "alfredseg.add_bone_interval"
    bl_label   = "Agregar intervalo de bloqueo"
    bl_description = "Agrega un intervalo de frames en el que este bone quedara bloqueado"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: IntProperty(default=-1)
    bone_key: StringProperty(default="")

    def execute(self, context):
        segs = context.scene.alfred_segs
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


class ALFREDSEG_OT_RemoveBoneInterval(Operator):
    """Elimina un intervalo de bloqueo especifico de un bone."""
    bl_idname  = "alfredseg.remove_bone_interval"
    bl_label   = "Eliminar intervalo de bloqueo"
    bl_options = {"REGISTER", "UNDO"}

    item_idx:     IntProperty(default=-1)
    bone_key:     StringProperty(default="")
    interval_idx: IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.alfred_segs
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


class ALFREDSEG_OT_Move(Operator):
    bl_idname  = "alfredseg.move"
    bl_label   = "Mover segmento"
    bl_description = "Sube o baja el segmento activo en la lista"
    bl_options = {"REGISTER", "UNDO"}

    direction: EnumProperty(items=[("UP", "Arriba", ""), ("DOWN", "Abajo", "")])

    def execute(self, context):
        segs = context.scene.alfred_segs
        idx  = segs.active_index
        n    = len(segs.segments)
        if self.direction == "UP" and idx > 0:
            segs.segments.move(idx, idx - 1)
            segs.active_index = idx - 1
        elif self.direction == "DOWN" and idx < n - 1:
            segs.segments.move(idx, idx + 1)
            segs.active_index = idx + 1
        return {"FINISHED"}


class ALFREDSEG_OT_Duplicate(Operator):
    bl_idname  = "alfredseg.duplicate"
    bl_label   = "Duplicar segmento"
    bl_description = "Duplica el segmento activo"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.alfred_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "No hay segmento seleccionado")
            return {"CANCELLED"}
        src = segs.segments[idx]
        dst = segs.segments.add()
        # Copiar atributos escalares
        scalar_attrs = (
            "label","frame_start","frame_end","frame_mid",
            "frame_start_planned","frame_end_planned",
            "single_coord_mode","frame_end_auto",
            "fps","entry_ratio","exit_ratio",
            "export_slot_number","export_type","export_desc",
            "pose_mid_file","pose_mid_label",
            "interp_type","interp_mid_to_end",
            "blend_in_frames","blend_out_frames","blend_strength",
            "affect_body","affect_left_arm","affect_right_arm",
            "affect_left_leg","affect_right_leg","affect_root",
            "affect_shield","affect_spear","enabled",
        )
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

        # ── Copiar Filtros organicos + Parpadeo (propios de cada segmento) ──
        # AISLAMIENTO POR SEGMENTO: dst.organic / dst.blink_intervals son una
        # instancia PROPIA e independiente de dst (no una referencia a la de
        # src) -- se copian los valores explicitamente para que el segmento
        # duplicado arranque igual al original, pero editar uno de los dos
        # despues no afecta al otro.
        for _attr in _ORGANIC_DEFAULTS_REGLAS_ALFRED.keys():
            try:
                setattr(dst.organic, _attr, getattr(src.organic, _attr))
            except Exception:
                pass
        dst.blink_intervals.clear()
        _bi_attrs = ("label", "frame_start", "frame_end", "blink_count",
                     "blink_duration", "enabled")
        for src_bi in src.blink_intervals:
            dst_bi = dst.blink_intervals.add()
            for a in _bi_attrs:
                try:
                    setattr(dst_bi, a, getattr(src_bi, a))
                except Exception:
                    pass
        dst.blink_interval_idx = src.blink_interval_idx

        # ── Copiar intervalos del filtro "Reir" (propios de cada segmento) ──
        # (Kebyn, 2026-08-18) -- mismo criterio que blink_intervals arriba.
        dst.laugh_intervals.clear()
        _li_attrs = ("label", "frame_start", "frame_end", "oscillation_count", "enabled")
        for src_li in src.laugh_intervals:
            dst_li = dst.laugh_intervals.add()
            for a in _li_attrs:
                try:
                    setattr(dst_li, a, getattr(src_li, a))
                except Exception:
                    pass
        dst.laugh_interval_idx = src.laugh_interval_idx

        # ── Copiar intervalos del filtro "Entendiendo" (propios de cada
        # segmento) ── (Kebyn, 2026-08-18) -- mismo criterio que
        # laugh_intervals arriba.
        dst.understand_intervals.clear()
        _ui_attrs = ("label", "frame_start", "frame_end", "direction", "enabled")
        for src_ui in src.understand_intervals:
            dst_ui = dst.understand_intervals.add()
            for a in _ui_attrs:
                try:
                    setattr(dst_ui, a, getattr(src_ui, a))
                except Exception:
                    pass
        dst.understand_interval_idx = src.understand_interval_idx

        # ── Copiar Expresiones de ojos (propias de cada segmento) ──────────
        # AISLAMIENTO POR SEGMENTO (Kebyn + Claude, 2026-08-04): mismo
        # criterio que blink_intervals arriba -- dst.expr_intervals es una
        # coleccion PROPIA e independiente de dst.
        dst.expr_intervals.clear()
        # Definido aca (antes de usarse en el loop de expr_intervals) porque
        # tambien se reutiliza mas abajo para dst.eye_shapekey -- mismos
        # atributos, misma PropertyGroup (AlfredEyeShapeKeySetup).
        _sk_attrs = ("curve_mode", "affect_zone", "swap_axes",
                     "invert_vertical", "invert_horizontal", "subdivide_cuts",
                     "intensity_feliz", "intensity_triste",
                     "intensity_enojado", "intensity_sospecha")
        _ei_attrs = ("label", "duration",
                     "expression", "expression_value", "interp_in", "interp_out", "enabled",
                     "manual_start", "frame_abs_start",
                     "eye_L_loc_x", "eye_L_loc_y", "eye_L_loc_z",
                     "eye_L_rot_x", "eye_L_rot_y", "eye_L_rot_z",
                     "eye_L_sca_x", "eye_L_sca_y", "eye_L_sca_z",
                     "eye_R_loc_x", "eye_R_loc_y", "eye_R_loc_z",
                     "eye_R_rot_x", "eye_R_rot_y", "eye_R_rot_z",
                     "eye_R_sca_x", "eye_R_sca_y", "eye_R_sca_z")
        for src_ei in src.expr_intervals:
            dst_ei = dst.expr_intervals.add()
            for a in _ei_attrs:
                try:
                    setattr(dst_ei, a, getattr(src_ei, a))
                except Exception:
                    pass
            # Setup de Shape Keys de ojos PROPIO de esta expresion (Kebyn,
            # 2026-08-18) -- se copia igual que dst.eye_shapekey abajo, para
            # que el segmento duplicado conserve el override por-expresion
            # (si lo tenia) de forma independiente del original.
            try:
                dst_ei.use_own_shapekey = src_ei.use_own_shapekey
            except Exception:
                pass
            for a in _sk_attrs:
                try:
                    setattr(dst_ei.own_shapekey, a, getattr(src_ei.own_shapekey, a))
                except Exception:
                    pass
        dst.expr_interval_idx = src.expr_interval_idx

        # ── Copiar Setup de Shape Keys de ojos (propio de cada segmento) ───
        # AISLAMIENTO POR SEGMENTO (Kebyn + Claude, 2026-08-05): mismo
        # criterio que organic/blink_intervals/expr_intervals arriba --
        # dst.eye_shapekey es una instancia PROPIA e independiente de dst.
        # (_sk_attrs ya se definio arriba, junto con el loop de expr_intervals).
        for a in _sk_attrs:
            try:
                setattr(dst.eye_shapekey, a, getattr(src.eye_shapekey, a))
            except Exception:
                pass

        dst.label = src.label + " (copia)"
        segs.active_index = len(segs.segments) - 1
        return {"FINISHED"}


# =============================================================================
# SELECTORES DE POSE (.json) para cada campo
# =============================================================================

class _PickPoseBase(Operator):
    """Base para los operadores de seleccion de pose .json."""
    bl_options = {"REGISTER", "UNDO"}
    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})
    _label_attr  = ""  # "pose_mid_label" / ...
    _edit_target_attr = ""   # "edit_pose_mid_file" / ...
    _edit_label_attr  = ""   # "edit_pose_mid_label" / ...

    def execute(self, context):
        segs = context.scene.alfred_segs
        # Escribe siempre en los campos edit_* del formulario de creacion
        if self._edit_target_attr:
            setattr(segs, self._edit_target_attr, self.filepath)
        if self._edit_label_attr:
            setattr(segs, self._edit_label_attr, os.path.basename(self.filepath))
        self.report({"INFO"}, f"Pose cargada: {os.path.basename(self.filepath)}")
        return {"FINISHED"}

    def invoke(self, context, event):
        segs = context.scene.alfred_segs
        self.filepath = bpy.path.abspath(segs.poses_dir) if segs.poses_dir else ""
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class ALFREDSEG_OT_PickPoseMid(_PickPoseBase):
    bl_idname    = "alfredseg.pick_pose_mid"
    bl_label     = "Seleccionar pose INTERMEDIA"
    bl_description = "Abre explorador para seleccionar el .json de la pose intermedia (opcional)"
    _target_attr = "pose_mid_file"
    _label_attr  = "pose_mid_label"
    _edit_target_attr = "edit_pose_mid_file"
    _edit_label_attr  = "edit_pose_mid_label"


# =============================================================================
# CAPTURA DE FRAMES DESDE LA TIMELINE
# =============================================================================

class ALFREDSEG_OT_SetFrameStart(Operator):
    bl_idname  = "alfredseg.set_frame_start"
    bl_label   = "Frame actual → Inicio"
    bl_description = "Usa el frame actual de la timeline como frame de inicio del segmento"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        segs = context.scene.alfred_segs
        idx  = segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "No hay segmento seleccionado"); return {"CANCELLED"}
        segs.segments[idx].frame_start = context.scene.frame_current
        return {"FINISHED"}


class ALFREDSEG_OT_SetFrameMid(Operator):
    bl_idname  = "alfredseg.set_frame_mid"
    bl_label   = "Frame actual → Intermedio"
    bl_description = "Usa el frame actual de la timeline como frame intermedio del segmento"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        segs = context.scene.alfred_segs
        idx  = segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "No hay segmento seleccionado"); return {"CANCELLED"}
        segs.segments[idx].frame_mid = context.scene.frame_current
        return {"FINISHED"}


class ALFREDSEG_OT_SetFrameEnd(Operator):
    bl_idname  = "alfredseg.set_frame_end"
    bl_label   = "Frame actual → Fin"
    bl_description = "Usa el frame actual de la timeline como frame de fin del segmento"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        segs = context.scene.alfred_segs
        idx  = segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "No hay segmento seleccionado"); return {"CANCELLED"}
        segs.segments[idx].frame_end = context.scene.frame_current
        return {"FINISHED"}


# =============================================================================
# GUARDAR / CARGAR CONFIGURACION DEL PASO 3
# =============================================================================

class ALFREDSEG_OT_SaveConfig(Operator):
    bl_idname  = "alfredseg.save_config"
    bl_label   = "Guardar config Paso 3"
    bl_description = "Guarda la lista de segmentos del Paso 3 a un archivo .json"
    bl_options = {"REGISTER"}

    def execute(self, context):
        segs     = context.scene.alfred_segs
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
        ] + _BONE_FILTER_ATTRS
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
            # Bloqueador de bones: intervalos de frames por bone
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

            # Filtros organicos propios de este segmento (AISLAMIENTO POR
            # SEGMENTO): se guardan explicitamente porque ahora viven en
            # seg.organic, no en una unica config global de escena.
            _organic_attrs = list(_ORGANIC_DEFAULTS_REGLAS_ALFRED.keys())
            d["organic"] = {a: getattr(seg.organic, a) for a in _organic_attrs}

            # Intervalos de parpadeo propios de este segmento (idem: viven
            # en seg.blink_intervals, no en scene.alfst.blink_intervals).
            d["blink_intervals"] = [
                {
                    "label":          bi.label,
                    "frame_start":    bi.frame_start,
                    "frame_end":      bi.frame_end,
                    "blink_count":    bi.blink_count,
                    "blink_duration": bi.blink_duration,
                    "enabled":        bi.enabled,
                }
                for bi in seg.blink_intervals
            ]
            d["blink_interval_idx"] = seg.blink_interval_idx

            # Intervalos del filtro "Reir" propios de este segmento (Kebyn,
            # 2026-08-18) -- idem blink_intervals arriba.
            d["laugh_intervals"] = [
                {
                    "label":             li.label,
                    "frame_start":       li.frame_start,
                    "frame_end":         li.frame_end,
                    "oscillation_count": li.oscillation_count,
                    "enabled":           li.enabled,
                }
                for li in seg.laugh_intervals
            ]
            d["laugh_interval_idx"] = seg.laugh_interval_idx

            # Intervalos del filtro "Entendiendo" propios de este segmento
            # (Kebyn, 2026-08-18) -- idem laugh_intervals arriba.
            d["understand_intervals"] = [
                {
                    "label":       ui.label,
                    "frame_start": ui.frame_start,
                    "frame_end":   ui.frame_end,
                    "direction":   ui.direction,
                    "enabled":     ui.enabled,
                }
                for ui in seg.understand_intervals
            ]
            d["understand_interval_idx"] = seg.understand_interval_idx

            # Intervalos de expresion de ojos propios de este segmento
            # (AISLAMIENTO POR SEGMENTO, Kebyn + Claude, 2026-08-04: idem
            # blink_intervals -- viven en seg.expr_intervals, no en
            # scene.alfst.expr_intervals).
            d["expr_intervals"] = [
                {
                    "label":             ei.label,
                    "duration":          ei.duration,
                    "expression":        ei.expression,
                    "expression_value":  ei.expression_value,
                    "interp_in":         ei.interp_in,
                    "interp_out":        ei.interp_out,
                    "enabled":           ei.enabled,
                    # Frame de inicio absoluto (Kebyn, 2026-09-06) — mismo
                    # esquema que AlfredSegmentPoseSlot.
                    "manual_start":      ei.manual_start,
                    "frame_abs_start":   ei.frame_abs_start,
                    "eye_L_loc_x": ei.eye_L_loc_x, "eye_L_loc_y": ei.eye_L_loc_y, "eye_L_loc_z": ei.eye_L_loc_z,
                    "eye_L_rot_x": ei.eye_L_rot_x, "eye_L_rot_y": ei.eye_L_rot_y, "eye_L_rot_z": ei.eye_L_rot_z,
                    "eye_L_sca_x": ei.eye_L_sca_x, "eye_L_sca_y": ei.eye_L_sca_y, "eye_L_sca_z": ei.eye_L_sca_z,
                    "eye_R_loc_x": ei.eye_R_loc_x, "eye_R_loc_y": ei.eye_R_loc_y, "eye_R_loc_z": ei.eye_R_loc_z,
                    "eye_R_rot_x": ei.eye_R_rot_x, "eye_R_rot_y": ei.eye_R_rot_y, "eye_R_rot_z": ei.eye_R_rot_z,
                    "eye_R_sca_x": ei.eye_R_sca_x, "eye_R_sca_y": ei.eye_R_sca_y, "eye_R_sca_z": ei.eye_R_sca_z,
                    # Setup de Shape Keys de ojos PROPIO de esta expresion
                    # (Kebyn, 2026-08-18: "cada expresion tenga su propia
                    # setup de shape keys de ojos"). Default retrocompatible:
                    # use_own_shapekey=False => sigue heredando d["eye_shapekey"].
                    "use_own_shapekey": ei.use_own_shapekey,
                    "own_shapekey": {
                        "curve_mode":         ei.own_shapekey.curve_mode,
                        "affect_zone":        ei.own_shapekey.affect_zone,
                        "swap_axes":          ei.own_shapekey.swap_axes,
                        "invert_vertical":    ei.own_shapekey.invert_vertical,
                        "invert_horizontal":  ei.own_shapekey.invert_horizontal,
                        "subdivide_cuts":     ei.own_shapekey.subdivide_cuts,
                        "intensity_feliz":    ei.own_shapekey.intensity_feliz,
                        "intensity_triste":   ei.own_shapekey.intensity_triste,
                        "intensity_enojado":  ei.own_shapekey.intensity_enojado,
                        "intensity_sospecha": ei.own_shapekey.intensity_sospecha,
                    },
                }
                for ei in seg.expr_intervals
            ]
            d["expr_interval_idx"] = seg.expr_interval_idx

            # Setup de Shape Keys de ojos propio de este segmento
            # (AISLAMIENTO POR SEGMENTO, Kebyn + Claude, 2026-08-05: vive
            # en seg.eye_shapekey, no en scene.alfst.eye_expr).
            _sk = seg.eye_shapekey
            d["eye_shapekey"] = {
                "curve_mode":         _sk.curve_mode,
                "affect_zone":        _sk.affect_zone,
                "swap_axes":          _sk.swap_axes,
                "invert_vertical":    _sk.invert_vertical,
                "invert_horizontal":  _sk.invert_horizontal,
                "subdivide_cuts":     _sk.subdivide_cuts,
                "intensity_feliz":    _sk.intensity_feliz,
                "intensity_triste":   _sk.intensity_triste,
                "intensity_enojado":  _sk.intensity_enojado,
                "intensity_sospecha": _sk.intensity_sospecha,
            }

            data["segments"].append(d)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.report({"INFO"}, f"Config Paso 3 guardada: {os.path.basename(filepath)}")
        except Exception as e:
            self.report({"ERROR"}, f"Error al guardar: {e}")
            return {"CANCELLED"}
        return {"FINISHED"}


class ALFREDSEG_OT_LoadConfig(Operator):
    bl_idname  = "alfredseg.load_config"
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

        segs = context.scene.alfred_segs
        segs.segments.clear()

        if "armature_name" in data:
            segs.armature_name = data["armature_name"]
        if "poses_dir" in data:
            segs.poses_dir = data["poses_dir"]

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
        ] + _BONE_FILTER_ATTRS
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
            # Bloqueador de bones: intervalos de frames por bone
            seg.bone_blocks.clear()
            for bb_data in seg_data.get("bone_blocks", []):
                entry = seg.bone_blocks.add()
                entry.bone_key = str(bb_data.get("bone_key", ""))
                for iv_data in bb_data.get("intervals", []):
                    iv = entry.intervals.add()
                    iv.frame_start = int(iv_data.get("frame_start", 0))
                    iv.frame_end   = int(iv_data.get("frame_end", 0))
                    iv.enabled     = bool(iv_data.get("enabled", True))

            # Filtros organicos propios de este segmento (AISLAMIENTO POR
            # SEGMENTO). Si el .json es de una version anterior sin este
            # bloque (no tiene "organic"), se dejan los defaults de
            # reglas_alfred.zip via _aplicar_defaults_organicos_y_parpadeo
            # mas abajo, igual que un segmento recien creado.
            _organic_data = seg_data.get("organic")
            if _organic_data:
                for a, v in _organic_data.items():
                    try:
                        setattr(seg.organic, a, v)
                    except Exception:
                        pass

            # Intervalos de parpadeo propios de este segmento
            seg.blink_intervals.clear()
            for bi_data in seg_data.get("blink_intervals", []):
                bi = seg.blink_intervals.add()
                bi.label          = str(bi_data.get("label", "Parpadeo"))
                bi.frame_start    = int(bi_data.get("frame_start", seg.frame_start))
                bi.frame_end      = int(bi_data.get("frame_end", seg.frame_end))
                bi.blink_count    = int(bi_data.get("blink_count", 1))
                bi.blink_duration = int(bi_data.get("blink_duration", 9))
                bi.enabled        = bool(bi_data.get("enabled", True))
            seg.blink_interval_idx = int(seg_data.get("blink_interval_idx", 0))

            # Intervalos del filtro "Reir" propios de este segmento (Kebyn,
            # 2026-08-18). Retrocompatible: json viejo sin este bloque -> lista vacia.
            seg.laugh_intervals.clear()
            for li_data in seg_data.get("laugh_intervals", []):
                li = seg.laugh_intervals.add()
                li.label             = str(li_data.get("label", "Reir"))
                li.frame_start       = int(li_data.get("frame_start", seg.frame_start))
                li.frame_end         = int(li_data.get("frame_end", seg.frame_end))
                li.oscillation_count = int(li_data.get("oscillation_count", 3))
                li.enabled           = bool(li_data.get("enabled", True))
            seg.laugh_interval_idx = int(seg_data.get("laugh_interval_idx", 0))

            # Intervalos del filtro "Entendiendo" propios de este segmento
            # (Kebyn, 2026-08-18). Retrocompatible: json viejo sin este
            # bloque -> lista vacia.
            seg.understand_intervals.clear()
            for ui_data in seg_data.get("understand_intervals", []):
                ui_ = seg.understand_intervals.add()
                ui_.label       = str(ui_data.get("label", "Entendiendo"))
                ui_.frame_start = int(ui_data.get("frame_start", seg.frame_start))
                ui_.frame_end   = int(ui_data.get("frame_end", seg.frame_end))
                ui_.direction   = str(ui_data.get("direction", "IZQUIERDA"))
                ui_.enabled     = bool(ui_data.get("enabled", True))
            seg.understand_interval_idx = int(seg_data.get("understand_interval_idx", 0))

            # Intervalos de expresion de ojos propios de este segmento
            # (AISLAMIENTO POR SEGMENTO, Kebyn + Claude, 2026-08-04)
            seg.expr_intervals.clear()
            for ei_data in seg_data.get("expr_intervals", []):
                ei = seg.expr_intervals.add()
                ei.label            = str(ei_data.get("label", "Expresion"))
                ei.duration         = int(ei_data.get("duration", 40))
                ei.expression       = str(ei_data.get("expression", "NEUTRAL"))
                ei.expression_value = float(ei_data.get("expression_value", 0.06))
                ei.interp_in        = str(ei_data.get("interp_in", "SMOOTH"))
                ei.interp_out       = str(ei_data.get("interp_out", "SMOOTH"))
                ei.enabled          = bool(ei_data.get("enabled", True))
                # Frame de inicio absoluto (Kebyn, 2026-09-06). Default
                # retrocompatible: .json de version anterior sin estos
                # campos queda en manual_start=False/frame_abs_start=0,
                # es decir encadenado automatico como siempre.
                ei.manual_start     = bool(ei_data.get("manual_start", False))
                ei.frame_abs_start  = int(ei_data.get("frame_abs_start", 0))
                for _ax in ("eye_L_loc_x", "eye_L_loc_y", "eye_L_loc_z",
                            "eye_L_rot_x", "eye_L_rot_y", "eye_L_rot_z",
                            "eye_L_sca_x", "eye_L_sca_y", "eye_L_sca_z",
                            "eye_R_loc_x", "eye_R_loc_y", "eye_R_loc_z",
                            "eye_R_rot_x", "eye_R_rot_y", "eye_R_rot_z",
                            "eye_R_sca_x", "eye_R_sca_y", "eye_R_sca_z"):
                    if _ax in ei_data:
                        try:
                            setattr(ei, _ax, ei_data[_ax])
                        except Exception:
                            pass
                # Setup de Shape Keys de ojos PROPIO de esta expresion
                # (Kebyn, 2026-08-18). Default retrocompatible: si el .json
                # es de una version anterior sin "use_own_shapekey", queda
                # en False (la expresion sigue heredando seg.eye_shapekey).
                ei.use_own_shapekey = bool(ei_data.get("use_own_shapekey", False))
                _ei_sk_data = ei_data.get("own_shapekey")
                if _ei_sk_data:
                    for _a, _v in _ei_sk_data.items():
                        try:
                            setattr(ei.own_shapekey, _a, _v)
                        except Exception:
                            pass
            seg.expr_interval_idx = int(seg_data.get("expr_interval_idx", 0))

            # Setup de Shape Keys de ojos propio de este segmento
            # (AISLAMIENTO POR SEGMENTO, Kebyn + Claude, 2026-08-05). Si el
            # .json es de una version anterior sin este bloque, se dejan
            # los defaults de AlfredEyeShapeKeySetup (equivalentes a los
            # que ya traia scene.alfst.eye_expr por defecto).
            _sk_data = seg_data.get("eye_shapekey")
            if _sk_data:
                for a, v in _sk_data.items():
                    try:
                        setattr(seg.eye_shapekey, a, v)
                    except Exception:
                        pass
                # El .json ya trae valores propios explicitos -> no se debe
                # volver a pisar con una migracion automatica desde el panel
                # global (ver ensure_eye_shapekey_migrated, properties.py).
                seg.eye_shapekey.migrated_from_global = True

            # Migracion: .json viejo (sin "organic"/"blink_intervals") ->
            # se le dan los defaults de reglas_alfred.zip a ESTE segmento,
            # aislados de los demas, igual que a uno creado desde cero.
            if not _organic_data and not seg.blink_intervals:
                _aplicar_defaults_organicos_y_parpadeo(context, seg)

        self.report({"INFO"}, f"Config Paso 3 cargada: {len(segs.segments)} segmentos")
        return {"FINISHED"}

    def invoke(self, context, event):
        segs = context.scene.alfred_segs
        self.filepath = bpy.path.abspath(segs.config_dir) if segs.config_dir else ""
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


# =============================================================================
# NUEVOS: Reproducir / Pausar / Detener segmento + Toggle enabled
# =============================================================================

class ALFREDSEG_OT_PlaySegment(Operator):
    """Salta al frame de inicio del segmento y reproduce hasta el frame fin calculado."""
    bl_idname  = "alfredseg.play_segment"
    bl_label   = "Reproducir segmento"
    bl_options = {"REGISTER"}          # SIN UNDO: UNDO interfiere con animation_play

    item_idx: bpy.props.IntProperty(default=0)

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        segs  = context.scene.alfred_segs
        if self.item_idx >= len(segs.segments):
            self.report({"ERROR"}, "Indice de segmento fuera de rango")
            return {"CANCELLED"}
        seg   = segs.segments[self.item_idx]
        scene = context.scene
        pc    = getattr(scene, "alfred_path", None)

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


class ALFREDSEG_OT_PauseSegment(Operator):
    """Pausa la reproduccion (toggle play/pause)."""
    bl_idname  = "alfredseg.pause_segment"
    bl_label   = "Pausar segmento"
    bl_options = {"REGISTER"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        bpy.ops.screen.animation_play()
        return {"FINISHED"}


class ALFREDSEG_OT_StopSegment(Operator):
    """Detiene la reproduccion y vuelve al frame de inicio del segmento."""
    bl_idname  = "alfredseg.stop_segment"
    bl_label   = "Detener segmento"
    bl_options = {"REGISTER"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        segs = context.scene.alfred_segs
        # Detiene si esta reproduciendo
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
        # Vuelve al frame de inicio del segmento
        if self.item_idx < len(segs.segments):
            seg = segs.segments[self.item_idx]
            context.scene.frame_set(seg.frame_start)
        return {"FINISHED"}


class ALFREDSEG_OT_PlaySegmentRecorrido(Operator):
    """Reproduce el recorrido con las MISMAS funciones que el boton
    superior 'Reproducir recorrido' (Paso 2 / ALFREDPR_OT_PreviewPath):
    regenera la animacion base (caminar/salto/parada), reinyecta las
    poses de "Concatenar segmentos" si ya se ejecuto antes, y aplica los
    filtros organicos — exactamente igual que el boton global.

    CORREGIDO (Kebyn, 2026-07-11): la version anterior de este boton NO
    regeneraba nada; solo acotaba scene.frame_start/frame_end asumiendo
    que ya habia una animacion horneada en la timeline. Esto no cumplia
    con el pedido de que este boton tuviera "las mismas funciones" que
    el de arriba.

    OPTIMIZADO (Kebyn, 2026-07-11): regenerar TODO el recorrido en cada
    click (llamando a alfredpr.preview_path) es correcto pero lento en
    recorridos largos. Como este boton necesita las mismas funciones que
    el de arriba pero no necesita rehacer trabajo que ya esta hecho, se
    compara una huella (fingerprint) del recorrido actual contra la
    guardada la ultima vez que se genero: si coincide y la animacion
    horneada sigue presente en el armature, se reusa tal cual (rapido);
    si no coincide (o no hay nada horneado todavia), se regenera
    completo — identico al boton superior.
    """
    bl_idname  = "alfredseg.play_segment_recorrido"
    bl_label   = "Reproducir recorrido"
    bl_description = (
        "Reproduce en loop SOLO los frames de ESTE segmento. Regenera el "
        "recorrido completo (igual que el boton superior) solo si algo "
        "cambio desde la ultima vez"
    )
    bl_options = {"REGISTER"}   # SIN UNDO: dispara reproduccion

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        segs = context.scene.alfred_segs
        if self.item_idx >= len(segs.segments):
            self.report({"ERROR"}, "Indice de segmento fuera de rango")
            return {"CANCELLED"}
        seg = segs.segments[self.item_idx]

        scene = context.scene

        # Detener reproduccion previa (si la habia), igual que hace el
        # boton superior antes de arrancar la suya.
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()

        # ── Decidir si hace falta regenerar ─────────────────────────────────
        # Se reusa la bake existente SOLO si: (a) hay una huella guardada de
        # una generacion previa, (b) coincide con el estado actual del
        # recorrido/segmentos/concatenado, y (c) el armature todavia tiene
        # esa animacion (accion o NLA tracks) presente.
        from . import path_recorder as _pr
        armature = _resolve_armature(segs, scene)
        alfred_obj = bpy.data.objects.get("alfred")
        _tiene_bake = bool(
            armature is not None
            and armature.animation_data
            and (armature.animation_data.action or armature.animation_data.nla_tracks)
        )
        _huella_actual  = _pr.compute_recorrido_fingerprint(context)
        _huella_guardada = alfred_obj.get("_last_preview_fingerprint", "") if alfred_obj else ""
        _reusar_bake = _tiene_bake and _huella_guardada == _huella_actual

        if not _reusar_bake:
            # ── Regenerar el recorrido COMPLETO: misma llamada que dispara
            # el boton superior "Reproducir recorrido" (Paso 2). Reconstruye
            # Capa 1 (caminar/saltar/parada), reinyecta Capa 2 (poses de
            # "Concatenar segmentos" del Paso 3, si ya se ejecuto antes) y
            # aplica los filtros organicos — asi este boton queda
            # funcionalmente identico al de arriba. Al terminar, ese
            # operador deja el playback corriendo sobre el recorrido
            # completo.
            result = bpy.ops.alfredpr.preview_path()
            if "CANCELLED" in result:
                self.report(
                    {"ERROR"},
                    "No se pudo generar el recorrido. Revisa el recorrido "
                    "grabado / el .blend del personaje (mismo requisito que "
                    "el boton 'Reproducir recorrido' superior)."
                )
                return {"CANCELLED"}

        # ── Determinar el frame_end real de este segmento ──────────────────
        f_start = seg.frame_start
        if seg.single_coord_mode and seg.frame_end_auto > f_start:
            f_end = seg.frame_end_auto
        elif seg.single_coord_mode or seg.frame_end <= f_start:
            _, f_end = _calc_seg_frames(seg)
        else:
            f_end = seg.frame_end

        # ── Acotar la reproduccion SOLO a los frames de este segmento ──────
        scene.frame_start = f_start
        scene.frame_end   = f_end
        scene.frame_set(f_start)

        # Si se reuso la bake (no se llamo a preview_path), la reproduccion
        # todavia no esta corriendo — hay que arrancarla aqui. Si se
        # regenero, preview_path ya la dejo corriendo y no hay que
        # togglearla de nuevo (eso la detendria en vez de acotarla).
        if _reusar_bake and not context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()

        _total = f_end - f_start + 1
        self.report(
            {"INFO"},
            f"Reproduciendo '{seg.label}'  frames {f_start}->{f_end}  ({_total}f)"
        )
        return {"FINISHED"}


class ALFREDSEG_OT_ToggleEnabled(Operator):
    """Activa o desactiva un segmento de la lista."""
    bl_idname  = "alfredseg.toggle_enabled"
    bl_label   = "Activar/desactivar segmento"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        segs = context.scene.alfred_segs
        if self.item_idx >= len(segs.segments):
            return {"CANCELLED"}
        seg = segs.segments[self.item_idx]
        seg.enabled = not seg.enabled
        return {"FINISHED"}


# =============================================================================
# CAPTURA DEL FRAME ACTUAL PARA EL FORMULARIO (modo 1 coordenada)
# =============================================================================

class ALFREDSEG_OT_SetFrameStartEdit(Operator):
    """Copia el frame actual de la timeline al campo edit_frame_start del formulario."""
    bl_idname  = "alfredseg.set_frame_start_edit"
    bl_label   = "Frame actual → Frame inicio (formulario)"
    bl_description = (
        "En modo 1 coordenada: usa el frame actual de la timeline "
        "como frame de inicio del nuevo segmento"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        segs = context.scene.alfred_segs
        segs.edit_frame_start = context.scene.frame_current
        self.report({"INFO"}, f"Frame inicio del formulario -> {context.scene.frame_current}")
        return {"FINISHED"}


# =============================================================================
# PICK POSE PARA SEGMENTO EXISTENTE (con item_idx)
# =============================================================================

# =============================================================================
# OPERADORES DE POSES INTERMEDIAS (ACTION POSES) POR SEGMENTO
# Equivalentes a alfst.add/edit/remove/move_action_pose pero escriben
# directamente en seg.action_poses del segmento activo (o item_idx).
# =============================================================================

class ALFREDSEG_OT_AddActionPoseSeg(Operator):
    bl_idname    = "alfredseg.add_action_pose_seg"
    bl_label     = "Agregar pose intermedia al segmento"
    bl_description = "Agrega una pose de accion a este segmento"
    bl_options   = {"REGISTER", "UNDO"}
    item_idx:    IntProperty(default=-1)

    json_file:   EnumProperty(name="Archivo JSON", items=_enum_json_files)
    pose_index:  EnumProperty(name="Pose",         items=_enum_poses_from_self_json)
    duration:    IntProperty(name="Duracion (frames)", default=20, min=2, max=300)
    rot_x:       FloatProperty(name="Rot X (grados)", default=0.0)
    rot_y:       FloatProperty(name="Rot Y (grados)", default=0.0)
    rot_z:       FloatProperty(name="Rot Z (grados)", default=0.0)
    pos_x:       FloatProperty(name="Pos X", default=0.0)
    pos_y:       FloatProperty(name="Pos Y", default=0.0)
    pos_z:       FloatProperty(name="Pos Z", default=0.0)
    interp_type: EnumProperty(name="Interpolacion", items=INTERP_TYPE_ITEMS, default="SMOOTH")
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
        segs = context.scene.alfred_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if 0 <= idx < len(segs.segments):
            return segs.segments[idx]
        return None

    def invoke(self, context, event):
        seg = self._get_seg(context)
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
        _pc = getattr(context.scene, "alfred_path", None)
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
            box2.label(text="Root (Alfred): se toma del .json de la pose elegida", icon="OBJECT_ORIGIN")
            box2.label(text="  (igual que los huesos). Se ajusta despues con el Empty", icon="BLANK1")
            box2.label(text="  'alfred' + 'Guardar cambios'.", icon="BLANK1")

    def execute(self, context):
        if self.json_file == "NONE":
            self.report({"WARNING"}, "No hay archivos JSON en la carpeta de poses")
            return {"CANCELLED"}
        st  = context.scene.alfst
        seg = self._get_seg(context)
        if seg is None:
            self.report({"WARNING"}, "Segmento invalido"); return {"CANCELLED"}
        jf    = _json_file_from_index(self, context)
        idx   = int(self.pose_index)
        fp    = os.path.join(bpy.path.abspath(st.poses_dir), jf)
        poses = load_json_poses(fp)
        name  = poses[idx].get("label", "?") if poses and idx < len(poses) else "?"
        # ── Root: siempre se toma del .json de la pose, igual que los huesos.
        # Sin prefill de "la pose anterior", sin tipeo manual. ──
        rec = get_pose_record(st.poses_dir, jf, idx)
        if rec:
            _px, _py, _pz, _rx, _ry, _rz = get_root_transform_from_record(rec)
            self.pos_x, self.pos_y, self.pos_z = _px, _py, _pz
            self.rot_x, self.rot_y, self.rot_z = _rx, _ry, _rz
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
        info = leer_calificacion_actual(context, jf, 0)
        if info:
            item.rating_avg_cache    = info["avg"]
            item.rating_count_cache  = info["count"]
            item.rating_status_cache = info["status"]
        seg.action_poses_idx = len(seg.action_poses) - 1
        _total, _new_end = _sync_seg_interval(seg, context.scene.alfred_segs.segments)
        self.report({"INFO"},
                    f"Pose agregada al segmento: '{name}'  [{jf}]  interp={self.interp_type}  "
                    f"| Intervalo ajustado: [{seg.frame_start}→{_new_end}]  ({_total}f)")
        return {"FINISHED"}


# =============================================================================
# EXTRAER POSE RAPIDA (debajo del sistema de agregar poses, dentro de cada
# segmento). Copia el sistema "4 Extraer Nueva Pose" (Paso 1, panels.py /
# ALFST_OT_ExtractPose) pero simplificado a un ciclo de 2 clicks:
#   1) Guardar  -> detecta el armature/bones de Alfred automaticamente
#                  (_find_alfred_armature), nombra la pose sola segun que
#                  huesos se movieron respecto al rest pose, y la guarda
#                  como .json en la carpeta de poses (mismo formato
#                  {"poses": [...]}  que usa ALFST_OT_ExtractPose, para que
#                  sea compatible con el resto del addon).
#   2) Importar -> agrega esa pose recien guardada a seg.action_poses de
#                  ESTE segmento (mismo criterio que
#                  ALFREDSEG_OT_AddActionPoseSeg.execute) y limpia el
#                  "pendiente" (scene.alfst.quickpose_pending_*) para el
#                  siguiente ciclo.
# =============================================================================

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


class ALFREDSEG_OT_QuickPoseExtract(Operator):
    """Captura la pose actual del armature de Alfred y la guarda como .json,
    nombrandola sola segun los huesos movidos. Reutilizar con 'Importar'
    para agregarla a la lista de poses del segmento."""
    bl_idname    = "alfredseg.quickpose_extract"
    bl_label     = "Guardar pose (bones actuales)"
    bl_description = (
        "Detecta el armature de Alfred, extrae la pose del frame actual "
        "y la guarda en la carpeta de poses con un nombre automatico "
        "segun los huesos que moviste"
    )
    bl_options   = {"REGISTER", "UNDO"}

    def execute(self, context):
        st       = context.scene.alfst
        scene    = context.scene
        armature = _find_alfred_armature(context)
        if armature is None or armature.type != "ARMATURE":
            self.report({"ERROR"}, "No se encontro el armature de Alfred en la escena")
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


class ALFREDSEG_OT_QuickPoseImport(Operator):
    """Importa la pose recien guardada por 'Guardar pose (bones actuales)'
    a la lista de poses de accion de este segmento, y limpia el pendiente."""
    bl_idname    = "alfredseg.quickpose_import"
    bl_label     = "Importar a la lista de poses"
    bl_description = "Agrega la pose recien guardada a la lista de este segmento"
    bl_options   = {"REGISTER", "UNDO"}
    item_idx:    IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        return bool(context.scene.alfst.quickpose_pending_file)

    def _get_seg(self, context):
        segs = context.scene.alfred_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if 0 <= idx < len(segs.segments):
            return segs.segments[idx]
        return None

    def execute(self, context):
        st  = context.scene.alfst
        seg = self._get_seg(context)
        if seg is None:
            self.report({"WARNING"}, "Segmento invalido")
            return {"CANCELLED"}
        jf  = st.quickpose_pending_file
        idx = st.quickpose_pending_index
        if not jf:
            self.report({"WARNING"}, "Primero presiona 'Guardar pose (bones actuales)'")
            return {"CANCELLED"}

        # Refrescar la lista de poses (mismo criterio que ALFST_OT_ImportPose)
        # para que el nuevo .json quede disponible en los selectores/enums.
        bpy.ops.alfst.refresh_poses()

        rec = get_pose_record(st.poses_dir, jf, idx)
        if not rec:
            self.report({"ERROR"}, f"No se pudo leer la pose recien guardada ({jf})")
            return {"CANCELLED"}

        _px, _py, _pz, _rx, _ry, _rz = get_root_transform_from_record(rec)

        item              = seg.action_poses.add()
        item.pose_name    = st.quickpose_pending_label or rec.get("label", "?")
        item.json_file    = jf
        item.pose_index   = idx
        item.duration     = 20
        item.rot_x, item.rot_y, item.rot_z = _rx, _ry, _rz
        item.pos_x, item.pos_y, item.pos_z = _px, _py, _pz
        item.interp_type  = "SMOOTH"
        item.manual_start = False

        info = leer_calificacion_actual(context, jf, 0)
        if info:
            item.rating_avg_cache    = info["avg"]
            item.rating_count_cache  = info["count"]
            item.rating_status_cache = info["status"]

        seg.action_poses_idx = len(seg.action_poses) - 1
        _total, _new_end = _sync_seg_interval(seg, context.scene.alfred_segs.segments)

        nombre_importada = item.pose_name
        # Limpiar el pendiente: listo para el siguiente ciclo.
        st.quickpose_pending_file  = ""
        st.quickpose_pending_index = 0
        st.quickpose_pending_label = ""

        self.report({"INFO"},
            f"Pose '{nombre_importada}' importada al segmento '{seg.label}'  "
            f"| Intervalo ajustado: [{seg.frame_start}→{_new_end}]  ({_total}f)")
        return {"FINISHED"}


class ALFREDSEG_OT_EditActionPoseSeg(Operator):
    bl_idname    = "alfredseg.edit_action_pose_seg"
    bl_label     = "Editar pose intermedia del segmento"
    bl_options   = {"REGISTER", "UNDO"}
    item_idx:    IntProperty(default=-1)

    duration:    IntProperty(name="Duracion (frames)", default=20, min=2, max=300)
    interp_type: EnumProperty(name="Interpolacion", items=INTERP_TYPE_ITEMS, default="SMOOTH")
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
        segs = context.scene.alfred_segs
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
        box2.label(text="El Root se edita con el Empty 'alfred' + 'Editar pose...'", icon="INFO")
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
            _sync_seg_interval(seg, context.scene.alfred_segs.segments)
        return {"FINISHED"}


class ALFREDSEG_OT_RateActionPoseSeg(Operator):
    """
    Guarda una calificacion (1-10) para la pose intermedia activa del
    segmento: 10 = la pose representa EXACTAMENTE lo que se pidio en el
    texto/historia. Se escribe en el .json propio de la pose y en
    pose_library.json (carpeta 'reglas'), para que el generador de
    configuraciones por IA pueda usarla como referencia de calidad.
    """
    bl_idname  = "alfredseg.rate_action_pose_seg"
    bl_label   = "Calificar pose de accion"
    bl_options = {"REGISTER", "UNDO"}
    item_idx:  IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.alfred_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"ERROR"}, "Segmento invalido.")
            return {"CANCELLED"}
        seg = segs.segments[idx]
        if not (seg.action_poses and 0 <= seg.action_poses_idx < len(seg.action_poses)):
            self.report({"ERROR"}, "No hay una pose de accion seleccionada.")
            return {"CANCELLED"}

        item = seg.action_poses[seg.action_poses_idx]
        if not item.json_file:
            self.report({"ERROR"}, "Esta pose no tiene archivo .json asociado.")
            return {"CANCELLED"}
        # Auto-rellenar rating_query con nombre_legible si está vacío
        if not item.rating_query.strip():
            nombre = leer_nombre_legible(context, item.json_file)
            if nombre:
                item.rating_query = nombre
            else:
                self.report({"WARNING"}, "No se encontro nombre_legible en pose_library.json. "
                                         "Escribe manualmente 'Que se pidio'.")
                # Continuar de todas formas con json_file como fallback
                item.rating_query = item.json_file

        ok, msg, promedio, cantidad, estado = guardar_calificacion_pose(
            context, item.json_file, 0,
            item.rating_query, item.rating_score, item.rating_comment,
        )
        item.rating_avg_cache    = promedio
        item.rating_count_cache  = cantidad
        item.rating_status_cache = estado

        if ok:
            self.report({"INFO"}, f"Calificacion {item.rating_score}/10 guardada.")
        else:
            self.report({"ERROR"}, msg)
        return {"FINISHED"} if ok else {"CANCELLED"}


class ALFREDSEG_OT_DuplicateActionPoseSeg(Operator):
    """Copia la pose de accion seleccionada y la agrega al final de la lista
    de este segmento, para no tener que reimportar la misma pose a mano
    (boton 'copiar' en la barra lateral de POSES DE ACCION)."""
    bl_idname    = "alfredseg.duplicate_action_pose_seg"
    bl_label     = "Copiar pose intermedia del segmento"
    bl_description = "Duplica la pose seleccionada y la agrega al final de la lista"
    bl_options   = {"REGISTER", "UNDO"}
    item_idx:    IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.alfred_segs
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
        _pose_index   = src.pose_index
        _pose_label   = src.pose_label
        _pose_name    = src.pose_name
        _duration     = src.duration
        _entry_ratio  = src.entry_ratio
        _exit_ratio   = src.exit_ratio
        _interp_type  = src.interp_type
        _rot_x, _rot_y, _rot_z = src.rot_x, src.rot_y, src.rot_z
        _pos_x, _pos_y, _pos_z = src.pos_x, src.pos_y, src.pos_z
        _rating_query   = src.rating_query
        _rating_score   = src.rating_score
        _rating_comment = src.rating_comment
        _rating_avg_cache    = src.rating_avg_cache
        _rating_count_cache  = src.rating_count_cache
        _rating_status_cache = src.rating_status_cache

        new_item = seg.action_poses.add()
        new_item.json_file    = _json_file
        new_item.pose_index   = _pose_index
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
        new_item.rating_query    = _rating_query
        new_item.rating_score    = _rating_score
        new_item.rating_comment  = _rating_comment
        new_item.rating_avg_cache    = _rating_avg_cache
        new_item.rating_count_cache  = _rating_count_cache
        new_item.rating_status_cache = _rating_status_cache

        seg.action_poses_idx = len(seg.action_poses) - 1
        _total, _new_end = _sync_seg_interval(seg, segs.segments)
        self.report({"INFO"},
            f"Pose '{_pose_name or _json_file}' copiada y agregada al final del segmento "
            f"| Intervalo ajustado: [{seg.frame_start}→{_new_end}]  ({_total}f)")
        return {"FINISHED"}


class ALFREDSEG_OT_RemoveActionPoseSeg(Operator):
    bl_idname  = "alfredseg.remove_action_pose_seg"
    bl_label   = "Eliminar pose intermedia del segmento"
    bl_options = {"REGISTER", "UNDO"}
    item_idx:  IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.alfred_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)): return {"CANCELLED"}
        seg = segs.segments[idx]
        if seg.action_poses and 0 <= seg.action_poses_idx < len(seg.action_poses):
            seg.action_poses.remove(seg.action_poses_idx)
            seg.action_poses_idx = max(0, seg.action_poses_idx - 1)
            _sync_seg_interval(seg, segs.segments)
        return {"FINISHED"}


class ALFREDSEG_OT_MoveActionPoseSeg(Operator):
    bl_idname  = "alfredseg.move_action_pose_seg"
    bl_label   = "Mover pose intermedia del segmento"
    bl_options = {"REGISTER", "UNDO"}
    item_idx:  IntProperty(default=-1)
    direction: EnumProperty(items=[("UP","Arriba",""),("DOWN","Abajo","")])

    def execute(self, context):
        segs = context.scene.alfred_segs
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

class ALFREDSEG_OT_ToggleConfig(Operator):
    """Muestra u oculta la configuracion de poses de un segmento."""
    bl_idname  = "alfredseg.toggle_config"
    bl_label   = "Configurar segmento"
    bl_options = {"REGISTER", "UNDO"}
    item_idx:  IntProperty(default=0)

    def execute(self, context):
        segs = context.scene.alfred_segs
        idx  = self.item_idx
        if 0 <= idx < len(segs.segments):
            segs.segments[idx].show_config = not segs.segments[idx].show_config
        return {"FINISHED"}




class ALFREDSEG_UL_Segments(bpy.types.UIList):
    """UIList para mostrar los slots de accion intermedios de un segmento."""
    bl_idname = "ALFREDSEG_UL_Segments"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.label(text=item.pose_name or item.json_file or "(sin pose)",
                      icon="POSE_HLT")
            row.label(text=f"{item.duration}f")
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text=item.pose_name or "pose")

# =============================================================================
# REGISTRO
# =============================================================================

class ALFREDSEG_OT_PreviewActionPose(Operator):
    """Aplica la pose seleccionada al armature en el frame actual para previsualizar"""
    bl_idname  = "alfredseg.preview_action_pose"
    bl_label   = "Previsualizar pose"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: IntProperty(default=0)

    def execute(self, context):
        st  = context.scene.alfst
        seg = st.segments[st.segments_idx] if st.segments and 0 <= st.segments_idx < len(st.segments) else None
        if seg is None:
            self.report({"WARNING"}, "No hay segmento activo")
            return {"CANCELLED"}

        poses_dir = bpy.path.abspath(st.poses_dir)
        idx = seg.action_poses_idx
        if not (0 <= idx < len(seg.action_poses)):
            return {"CANCELLED"}

        slot = seg.action_poses[idx]
        rec  = get_pose_record(poses_dir, slot.json_file, getattr(slot, "pose_index", 0))
        if rec is None:
            self.report({"WARNING"}, f"No se pudo leer la pose: {slot.json_file}")
            return {"CANCELLED"}

        # Buscar el armature de Alfred en la escena
        arm_obj = None
        for ob in context.scene.objects:
            if ob.type == "ARMATURE" and "alfred" in ob.name.lower():
                arm_obj = ob
                break
        if arm_obj is None:
            for ob in context.scene.objects:
                if ob.type == "ARMATURE":
                    arm_obj = ob
                    break
        if arm_obj is None:
            self.report({"WARNING"}, "No se encontro armature en la escena")
            return {"CANCELLED"}

        bones_data = pose_record_to_full_dict(rec)

        # Aplicar pose hueso a hueso en pose mode
        prev_mode = arm_obj.mode
        prev_active = context.view_layer.objects.active
        context.view_layer.objects.active = arm_obj

        try:
            bpy.ops.object.mode_set(mode="POSE")
            for bone_name, bvals in bones_data.items():
                pb = arm_obj.pose.bones.get(bone_name)
                if pb is None:
                    continue
                pb.rotation_mode = "XYZ"
                rot = bvals.get("rot", (0.0, 0.0, 0.0))
                loc = bvals.get("loc", (0.0, 0.0, 0.0))
                pb.rotation_euler = rot
                pb.location       = loc
            bpy.ops.object.mode_set(mode=prev_mode if prev_mode != "EDIT" else "OBJECT")
        except Exception as e:
            self.report({"WARNING"}, f"Error aplicando pose: {e}")
            try:
                bpy.ops.object.mode_set(mode="OBJECT")
            except Exception:
                pass

        context.view_layer.objects.active = prev_active

        # Forzar redibujado del viewport
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()

        self.report({"INFO"}, f"Preview: {slot.json_file}")
        return {"FINISHED"}


def _find_alfred_armature(context):
    """
    Resuelve el armature de Alfred de forma fiable:
      1) Usa el mismo resolver que CONCATENAR (_resolve_armature), basado en
         scene.alfred_segs.armature_name — la fuente de verdad configurada
         por el usuario en el panel de Segmentos.
      2) Si eso falla, intenta con scene.alfst.armature_name (Paso 1/2).
      3) Como ultimo recurso, busca por nombre "alfred" en la escena (puede
         ser ambiguo si hay armatures secundarios/objetos lanzados con ese
         texto en el nombre, asi que es solo un fallback).
    """
    scene   = context.scene
    seg_cfg = getattr(scene, "alfred_segs", None)
    if seg_cfg is not None:
        arm_obj = _resolve_armature(seg_cfg, scene)
        if arm_obj is not None:
            return arm_obj

    st = getattr(scene, "alfst", None)
    if st is not None and getattr(st, "armature_name", ""):
        arm_obj = scene.objects.get(st.armature_name)
        if arm_obj and arm_obj.type == "ARMATURE":
            return arm_obj

    arm_obj = None
    for ob in context.scene.objects:
        if ob.type == "ARMATURE" and "alfred" in ob.name.lower():
            arm_obj = ob
            break
    if arm_obj is None:
        for ob in context.scene.objects:
            if ob.type == "ARMATURE":
                arm_obj = ob
                break
    return arm_obj


class ALFREDSEG_OT_EnterEditPose(Operator):
    """
    Aplica la pose del slot activo sobre el armature y deja Blender en
    Pose Mode con el hueso recomendado seleccionado, para que el animador
    pueda corregir manualmente Posicion/Rotacion/Escala desde el panel
    Item (N) del viewport — igual que se ve en el ejemplo de referencia.
    Cuando termine de ajustar, debe usar "Guardar cambios en la pose"
    para escribir esos valores de vuelta en el .json.
    """
    bl_idname  = "alfredseg.enter_edit_pose"
    bl_label   = "Editar pose (entrar a Pose Mode)"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: IntProperty(default=0)

    def execute(self, context):
        segs = context.scene.alfred_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"ERROR"}, "Segmento invalido.")
            return {"CANCELLED"}
        seg = segs.segments[idx]
        if not (seg.action_poses and 0 <= seg.action_poses_idx < len(seg.action_poses)):
            self.report({"ERROR"}, "No hay una pose de accion seleccionada.")
            return {"CANCELLED"}

        st = context.scene.alfst
        poses_dir = bpy.path.abspath(st.poses_dir)
        slot = seg.action_poses[seg.action_poses_idx]
        if not slot.json_file:
            self.report({"ERROR"}, "Esta pose no tiene archivo .json asociado.")
            return {"CANCELLED"}

        rec = get_pose_record(poses_dir, slot.json_file, getattr(slot, "pose_index", 0))
        if rec is None:
            self.report({"WARNING"}, f"No se pudo leer la pose: {slot.json_file}")
            return {"CANCELLED"}

        arm_obj = _find_alfred_armature(context)
        if arm_obj is None:
            self.report({"WARNING"}, "No se encontro armature en la escena")
            return {"CANCELLED"}

        bones_data = pose_record_to_full_dict(rec)

        # ── ROOT (Empty "alfred"): se sincroniza SIEMPRE desde lo guardado en
        # el .json de la pose (clave "root"), exactamente igual que los huesos
        # (pose_record_to_full_dict arriba). Sin gating por "slot en blanco":
        # esa logica era la que impedia que el Root recien guardado se
        # recargara cuando el slot ya traia algun valor (ej. precargado desde
        # la pose anterior del segmento). ──
        _px, _py, _pz, _rx, _ry, _rz = get_root_transform_from_record(rec)
        slot.pos_x, slot.pos_y, slot.pos_z = _px, _py, _pz
        slot.rot_x, slot.rot_y, slot.rot_z = _rx, _ry, _rz

        # Se deja el Empty "alfred" listo con los valores del slot para que
        # el animador pueda ajustarlo en Properties > Object > Transform,
        # exactamente igual que un hueso mas. "Guardar cambios" lee su
        # Location/Rotation real, ya no se escriben a mano.
        root_obj = bpy.data.objects.get("alfred") or arm_obj
        try:
            root_obj.rotation_mode = "XYZ"
            root_obj.location = (slot.pos_x, slot.pos_y, slot.pos_z)
            root_obj.rotation_euler = (
                math.radians(slot.rot_x),
                math.radians(slot.rot_y),
                math.radians(slot.rot_z),
            )
        except Exception as e_root:
            print(f"[AlfredSeg] No se pudo preparar el Root '{root_obj.name}': {e_root}")

        prev_active = context.view_layer.objects.active

        # ── Asegurar que el armature es visible/seleccionable ──────────────
        # FIX (Kebyn, 2026-08-04: "al apretar el boton editar poses, no me
        # permite editar las poses, solo me sale el mensaje..."): el mensaje
        # de exito se mostraba aunque el cambio a Pose Mode hubiera fallado
        # silenciosamente (bpy.ops.object.mode_set no siempre lanza excepcion
        # si el poll() falla, p.ej. cuando el armature esta oculto o excluido
        # de la vista) y aunque los huesos afectados estuvieran en una capa /
        # coleccion de huesos no visible (serian seleccionados internamente
        # pero invisibles en el viewport, dando la sensacion de que "no pasa
        # nada"). Ahora se fuerza visibilidad del objeto y de cada hueso
        # antes de intentar el cambio de modo, y se verifica el resultado.
        try:
            if arm_obj.hide_get():
                arm_obj.hide_set(False)
        except Exception:
            pass
        arm_obj.hide_viewport = False
        try:
            arm_obj.select_set(True)
        except Exception:
            pass
        context.view_layer.objects.active = arm_obj

        try:
            if arm_obj.mode != "POSE":
                result = bpy.ops.object.mode_set(mode="POSE")
                # ── Reintento con override de contexto ──────────────────────
                # Si el poll() fallo silenciosamente (el boton se pulso desde
                # una region/area que Blender no considera valida para este
                # operador), se reintenta apuntando explicitamente a un area
                # VIEW_3D de la ventana actual.
                if "FINISHED" not in result or arm_obj.mode != "POSE":
                    for win in context.window_manager.windows:
                        for area in win.screen.areas:
                            if area.type == "VIEW_3D":
                                region = next((r for r in area.regions if r.type == "WINDOW"), None)
                                if region is None:
                                    continue
                                override = {
                                    "window": win, "screen": win.screen, "area": area,
                                    "region": region, "active_object": arm_obj,
                                    "object": arm_obj,
                                }
                                try:
                                    with context.temp_override(**override):
                                        bpy.ops.object.mode_set(mode="POSE")
                                except Exception:
                                    pass
                                if arm_obj.mode == "POSE":
                                    break
                        if arm_obj.mode == "POSE":
                            break

            if arm_obj.mode != "POSE":
                self.report(
                    {"ERROR"},
                    "No se pudo entrar a Pose Mode (revisa que el armature "
                    "no este oculto ni excluido de la vista)."
                )
                return {"CANCELLED"}

            bpy.ops.pose.select_all(action="DESELECT")
            first_bone = None
            for bone_name, bvals in bones_data.items():
                pb = arm_obj.pose.bones.get(bone_name)
                if pb is None:
                    continue
                # Forzar visibilidad del hueso: si esta oculto, o su capa /
                # coleccion de huesos esta desactivada, se ve como si "no
                # pasara nada" al seleccionarlo (queda seleccionado pero
                # invisible en el viewport).
                bone_data = pb.bone
                bone_data.hide = False
                if hasattr(bone_data, "collections") and bone_data.collections:
                    for bcoll in bone_data.collections:
                        try:
                            bcoll.is_visible = True
                        except Exception:
                            pass
                if hasattr(bone_data, "layers") and hasattr(arm_obj.data, "layers"):
                    try:
                        for _li, _on in enumerate(bone_data.layers):
                            if _on:
                                arm_obj.data.layers[_li] = True
                    except Exception:
                        pass
                pb.rotation_mode = "XYZ"
                pb.rotation_euler = bvals.get("rot", (0.0, 0.0, 0.0))
                pb.location       = bvals.get("loc", (0.0, 0.0, 0.0))
                pb.scale          = bvals.get("scale", (1.0, 1.0, 1.0))
                bone_data.select = True
                if first_bone is None:
                    first_bone = pb
            if first_bone is not None:
                arm_obj.data.bones.active = first_bone.bone
        except Exception as e:
            self.report({"ERROR"}, f"Error entrando a modo edicion: {e}")
            return {"CANCELLED"}

        # ── Crear el archivo de "cambios" para ESTA edicion: una copia exacta
        # de la pose (mismo formato que los .json de poses_dir) guardada como
        # "antes". "Guardar cambios en la pose" completara "despues" en este
        # MISMO archivo, tambien en formato completo de pose. ──
        cache_key = (slot.json_file, getattr(slot, "pose_index", 0))
        change_filepath = None
        try:
            change_filepath = _new_pose_change_filepath(
                poses_dir, slot.json_file, getattr(slot, "pose_index", 0)
            )
            change_doc = {
                "pose_original_file": slot.json_file,
                "pose_index":         getattr(slot, "pose_index", 0),
                "pose_name":          rec.get("label") or slot.pose_name or "",
                "timestamp_antes":    datetime.datetime.now().isoformat(),
                "timestamp_despues":  None,
                "guardado":           False,
                # "antes" y "despues" usan el MISMO formato que los .json de
                # poses (label, frame, armature, bones, root, etc.) — "antes"
                # es una copia exacta de la pose tal como estaba en disco.
                "antes":   copy.deepcopy(rec),
                "despues": None,
            }
            with open(change_filepath, "w", encoding="utf-8") as f:
                json.dump(change_doc, f, indent=2, ensure_ascii=False)
        except Exception as e_log:
            print(f"[AlfredSeg] No se pudo crear el archivo de cambios: {e_log}")
            change_filepath = None

        # ── Snapshot en memoria: a que archivo de cambios pertenece esta edicion ──
        _POSE_EDIT_SNAPSHOTS[cache_key] = {
            "bones": bones_data,  # tal cual estaba en el .json antes de editar
            "root_pos": (slot.pos_x, slot.pos_y, slot.pos_z),
            "root_rot": (slot.rot_x, slot.rot_y, slot.rot_z),
            "change_filepath": change_filepath,
            "rec_antes": rec,  # record completo original, por si hace falta como fallback
        }

        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()

        self.report(
            {"INFO"},
            f"Editando '{slot.pose_name or slot.json_file}': en el panel N (lateral "
            f"derecho del viewport) abre la pestaña 'Item' (no esta pestaña de "
            f"'Alfred Studio') para ver Location/Rotation/Scale del hueso activo, "
            f"o arrastralo directo en el viewport. El Root: selecciona el Empty "
            f"'alfred' y ajustalo en Properties > Object > Transform. Luego pulsa "
            f"'Guardar cambios en la pose'."
        )
        return {"FINISHED"}


class ALFREDSEG_OT_SaveEditedPose(Operator):
    """
    Lee la pose actual de TODOS los huesos del armature (en Pose Mode, tal
    como quedaron despues de ajustarlos manualmente) y sobreescribe el
    registro correspondiente dentro del .json de la pose (carpeta
    'poses_dir'), conservando el resto de metadatos del registro
    (label, timestamp original, calificaciones, etc). Tras guardar, hay
    que volver a pulsar CONCATENAR para que el sistema reproduzca la
    pose ya actualizada.
    """
    bl_idname  = "alfredseg.save_edited_pose"
    bl_label   = "Guardar cambios en la pose"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: IntProperty(default=0)

    def execute(self, context):
        segs = context.scene.alfred_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"ERROR"}, "Segmento invalido.")
            return {"CANCELLED"}
        seg = segs.segments[idx]
        if not (seg.action_poses and 0 <= seg.action_poses_idx < len(seg.action_poses)):
            self.report({"ERROR"}, "No hay una pose de accion seleccionada.")
            return {"CANCELLED"}

        st = context.scene.alfst
        poses_dir = bpy.path.abspath(st.poses_dir)
        slot = seg.action_poses[seg.action_poses_idx]
        if not slot.json_file:
            self.report({"ERROR"}, "Esta pose no tiene archivo .json asociado.")
            return {"CANCELLED"}

        arm_obj = _find_alfred_armature(context)
        if arm_obj is None:
            self.report({"WARNING"}, "No se encontro armature en la escena")
            return {"CANCELLED"}

        filepath = os.path.join(poses_dir, slot.json_file)
        if not os.path.isfile(filepath):
            self.report({"ERROR"}, f"No se encontro el archivo: {filepath}")
            return {"CANCELLED"}

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            self.report({"ERROR"}, f"No se pudo leer el JSON: {e}")
            return {"CANCELLED"}

        poses = doc.get("poses", [])
        pose_idx = getattr(slot, "pose_index", 0)
        if not (0 <= pose_idx < len(poses)):
            self.report({"ERROR"}, "Indice de pose invalido dentro del archivo.")
            return {"CANCELLED"}

        # ── Capturar el estado ACTUAL de los huesos en el armature ──
        bones_data = {}
        for bone_name in BONES_LISTA:
            pb = arm_obj.pose.bones.get(bone_name)
            if pb is None:
                continue
            pb.rotation_mode = "XYZ"
            rot_e = pb.rotation_euler
            rot_q = pb.rotation_quaternion
            local_space = {
                "location": {
                    "x": round(pb.location.x, 6),
                    "y": round(pb.location.y, 6),
                    "z": round(pb.location.z, 6),
                },
                "rotation_euler_rad": {
                    "x": round(rot_e.x, 6),
                    "y": round(rot_e.y, 6),
                    "z": round(rot_e.z, 6),
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
                    "x": round(pb.scale.x, 6),
                    "y": round(pb.scale.y, 6),
                    "z": round(pb.scale.z, 6),
                },
            }
            bones_data[bone_name] = {
                "parent":    pb.parent.name if pb.parent else None,
                "connected": pb.bone.use_connect,
                "local_space": local_space,
                "rotation_mode": "XYZ",
                "raw_rotation_euler_deg":  local_space["rotation_euler_deg"],
                "raw_rotation_quaternion": None,
                "raw_location": local_space["location"],
                "raw_scale":    local_space["scale"],
            }

        # ── Capturar el ROOT (Empty "alfred") tal como haya quedado posicionado
        # en Properties > Object > Transform — ya no se escribe a mano, se lee
        # igual que un hueso mas. Si no existe el Empty, se usa el armature
        # como fallback, pero se AVISA: el armature normalmente esta en
        # (0,0,0) y guardar eso pisa silenciosamente un Root ya configurado. ──
        root_obj = bpy.data.objects.get("alfred")
        if root_obj is None:
            root_obj = arm_obj
            self.report(
                {"WARNING"},
                "No se encontro el Empty 'alfred' en la escena: se uso "
                f"'{arm_obj.name}' como Root (probablemente (0,0,0)). "
                "Si esto no es lo esperado, revisa que el Empty 'alfred' "
                "este presente ANTES de pulsar 'Guardar cambios'."
            )
        root_obj.rotation_mode = "XYZ"
        slot.pos_x = round(root_obj.location.x, 4)
        slot.pos_y = round(root_obj.location.y, 4)
        slot.pos_z = round(root_obj.location.z, 4)
        slot.rot_x = round(math.degrees(root_obj.rotation_euler.x), 4)
        slot.rot_y = round(math.degrees(root_obj.rotation_euler.y), 4)
        slot.rot_z = round(math.degrees(root_obj.rotation_euler.z), 4)

        record = poses[pose_idx]
        # Copia completa ANTES de mutar — sirve como "antes" en formato pose
        # completo si el usuario guardo sin pasar antes por "Editar pose...".
        record_before_edit = copy.deepcopy(record)

        # ── Salvaguarda: nunca sobreescribir con una pose vacia ──
        # Si por algun motivo no se pudo leer NINGUN hueso del armature
        # (ej: se resolvio el objeto equivocado), abortamos sin tocar el
        # archivo en disco para no corromper la pose original.
        if not bones_data:
            self.report(
                {"ERROR"},
                f"No se pudo leer ningun hueso del armature '{arm_obj.name}' "
                f"(0/{len(BONES_LISTA)} coincidencias). Cancelado para no sobreescribir "
                f"la pose con datos vacios. Revisa que '{arm_obj.name}' sea el armature correcto."
            )
            return {"CANCELLED"}

        record["bones"] = bones_data
        record["bone_count"] = len(bones_data)
        record["edited_manualmente"] = True
        record["edited_timestamp"] = datetime.datetime.now().isoformat()
        # ── Root (Empty "alfred") — se guarda DENTRO de la pose, no solo en el
        # segmento. Asi al reabrir Blender y volver a elegir esta pose en
        # cualquier segmento nuevo, el Root se autocompleta desde el .json. ──
        record["root"] = {
            "location": {"x": slot.pos_x, "y": slot.pos_y, "z": slot.pos_z},
            "rotation_euler_deg": {"x": slot.rot_x, "y": slot.rot_y, "z": slot.rot_z},
        }
        poses[pose_idx] = record
        doc["poses"] = poses

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.report({"ERROR"}, f"No se pudo guardar el JSON: {e}")
            return {"CANCELLED"}

        # ── ARCHIVO DE CAMBIOS: completar el "despues" (mismo formato completo
        # de pose que "antes") en el .json creado por "Editar pose...". ──
        try:
            cache_key = (slot.json_file, pose_idx)
            snapshot  = _POSE_EDIT_SNAPSHOTS.pop(cache_key, None)

            _ts_after = datetime.datetime.now()
            change_filepath = snapshot.get("change_filepath") if snapshot else None

            if change_filepath and os.path.isfile(change_filepath):
                with open(change_filepath, "r", encoding="utf-8") as f:
                    change_doc = json.load(f)
            else:
                # No se paso por "Editar pose..." antes de guardar (o el
                # archivo no se pudo crear entonces): crear uno ahora, usando
                # la copia capturada justo antes de mutar el record como
                # "antes" (mismo formato completo de pose de todas formas).
                change_filepath = _new_pose_change_filepath(poses_dir, slot.json_file, pose_idx)
                change_doc = {
                    "pose_original_file": slot.json_file,
                    "pose_index":         pose_idx,
                    "pose_name":          record.get("label") or slot.pose_name or "",
                    "timestamp_antes":    _ts_after.isoformat(),
                    "timestamp_despues":  None,
                    "guardado":           False,
                    "antes":   record_before_edit,
                    "despues": None,
                }

            # "despues" = copia completa del record YA guardado en el .json de
            # la pose (mismo formato: label, frame, armature, bones, root...).
            change_doc["despues"]            = copy.deepcopy(record)
            change_doc["timestamp_despues"]  = _ts_after.isoformat()
            change_doc["guardado"]           = True

            with open(change_filepath, "w", encoding="utf-8") as f:
                json.dump(change_doc, f, indent=2, ensure_ascii=False)
        except Exception as e_log:
            # El archivo de cambios nunca debe bloquear el guardado principal de la pose.
            print(f"[AlfredSeg] No se pudo escribir el archivo de cambios: {e_log}")

        self.report(
            {"INFO"},
            f"Pose '{slot.pose_name or slot.json_file}' guardada en '{filepath}' "
            f"(huesos + root pos=({slot.pos_x},{slot.pos_y},{slot.pos_z}) "
            f"rot=({slot.rot_x},{slot.rot_y},{slot.rot_z})). Vuelve a pulsar CONCATENAR."
        )
        return {"FINISHED"}


classes = (
    ALFREDSEG_OT_Add,
    ALFREDSEG_OT_AutoSplitFromConfig,
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
    ALFREDSEG_OT_SaveConfig,
    ALFREDSEG_OT_LoadConfig,
    ALFREDSEG_OT_PlaySegment,
    ALFREDSEG_OT_PauseSegment,
    ALFREDSEG_OT_StopSegment,
    ALFREDSEG_OT_PreviewActionPose,
    ALFREDSEG_OT_EnterEditPose,
    ALFREDSEG_OT_SaveEditedPose,
    ALFREDSEG_OT_ToggleEnabled,
    ALFREDSEG_OT_AddActionPoseSeg,
    ALFREDSEG_OT_EditActionPoseSeg,
    ALFREDSEG_OT_RemoveActionPoseSeg,
    ALFREDSEG_OT_MoveActionPoseSeg,
    ALFREDSEG_OT_ToggleConfig,
    ALFREDSEG_OT_SetFrameStartEdit,
    ALFREDSEG_UL_Segments,
)
