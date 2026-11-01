# -*- coding: utf-8 -*-
"""
operators_segments.py — Chicken 1 Animation Studio v2.0
Paso 3: Segmentos de refinado sobre la animacion generada por Pasos 1+2.

LOGICA CENTRAL:
  La animacion de recorrido (generada por path_recorder) ya existe en la
  timeline con sus fcurves de bones y de root. El Paso 3 NO la borra ni la
  reemplaza: la modula.

  Por cada Chicken1AnimSegment el operador APLICAR_SEGMENTOS:
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
  CH1SEG_OT_Add            — agrega un segmento nuevo
  CH1SEG_OT_Remove         — elimina el segmento activo
  CH1SEG_OT_Move           — sube/baja el segmento activo
  CH1SEG_OT_Duplicate      — duplica el segmento activo
  CH1SEG_OT_PickPoseMid    — selecciona .json para pose intermedia
  CH1SEG_OT_SetFrameStart  — captura frame actual como frame_start
  CH1SEG_OT_SetFrameMid    — captura frame actual como frame_mid
  CH1SEG_OT_SetFrameEnd    — captura frame actual como frame_end
  CH1SEG_OT_Apply          — aplica todos los segmentos activos sobre la timeline
  CH1SEG_OT_SaveConfig     — guarda la lista de segmentos a .json
  CH1SEG_OT_LoadConfig     — carga la lista de segmentos desde .json
"""

import bpy, json, os, math, datetime
from bpy.types import Operator
from bpy.props import StringProperty, IntProperty, EnumProperty, FloatProperty, BoolProperty

from .constants import BONES_LISTA_FULL, BONES_LISTA, _BONE_DEFAULT, INTERP_TYPE_ITEMS
SECONDARY_ARMATURES = {}
from .interpolation import apply_interp
from .pose_utils import (
    load_json_poses, get_pose_record, pose_record_to_full_dict,
    list_json_files, _enum_json_files, _json_file_from_index,
    _enum_poses_from_self_json, get_root_rotation_from_record,
    get_root_transform_from_record,
    resolve_pose_start_frames,
)
from . import object_import_utils as _oiu
from .fcurve_compat import get_fcurves, ensure_fcurves


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


def _load_action_pose(item, poses_dir):
    """
    Carga la pose de accion seleccionada por el usuario en un slot de
    action_poses (Chicken1SegmentPoseSlot), respetando item.pose_index.

    A diferencia de _load_pose_from_file() -- que ante un archivo JSON con
    formato {"poses": [...]} siempre devolvia la pose [0] sin importar cual
    eligio el usuario en el dropdown "Paso 2 -- Elige la pose de accion" --
    esta funcion usa get_pose_record()/pose_record_to_full_dict() (pose_utils)
    para resolver el registro EXACTO por indice, que es la misma logica que
    ya usa el resto del addon (preview, Paso 1+2) para leer poses individuales
    de una biblioteca con varias poses por archivo.
    """
    if item is None:
        return None
    json_file  = getattr(item, "json_file", "")
    pose_index = getattr(item, "pose_index", 0)
    if not json_file:
        return None
    rec = get_pose_record(poses_dir, json_file, pose_index)
    if rec is not None:
        return pose_record_to_full_dict(rec)
    # Fallback: archivo sin formato {"poses": [...]} (pose suelta / wrapper "bones")
    return _load_pose_from_file(json_file, poses_dir)


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
    Calcula la duracion total de un segmento sumando las duraciones
    de sus poses de accion (action_poses).

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
    fc = get_fcurves(action).find(data_path, index=index)
    if fc is None:
        fc = ensure_fcurves(action).new(data_path=data_path, index=index)
    return fc


def _get_fcurve_value_at(action, data_path, index, frame):
    """Evalua un fcurve en un frame dado. Devuelve 0.0 si no existe."""
    fc = get_fcurves(action).find(data_path, index=index)
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
    # Fallback: nombre real del armature de chicken_1 (ver ARM_NAME en
    # CH1PR_OT_PreviewPath, path_recorder.py). "Dog_001_rig" (abajo) es un
    # resto de la plantilla "Jerry" de la que viene este addon -- se deja
    # como ultimo recurso por compatibilidad con .blend viejos que lo usen.
    arm = scene.objects.get("Armature_chicken_1")
    if arm and arm.type == "ARMATURE":
        return arm
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


def _push_action_to_nla(obj, action, frame_start, frame_end, track_name):
    """FIX 4 (poses no inyectadas al Concatenar -- causa raiz real):
    Port de _push_action_to_nla() en ALFREDSEG_OT_Apply/ConcatenateAll
    (alfred_animation_studio, "AISLAMIENTO TOTAL DE SEGMENTOS"), que NUNCA
    se habia portado a este addon.

    El bug real: para cada segmento en modo recorrido (single_coord_mode
    False), el loop de arriba hacia `armature.animation_data.action = action`
    -- es decir, dejaba la action DEDICADA de ESE segmento como la "active
    action" del armature. Como cada iteracion del loop pisa esa asignacion
    con la action del segmento que se esta procesando en ese momento, al
    terminar el bucle completo la UNICA action que queda activa (visible en
    la timeline) es la del ULTIMO segmento procesado -- las poses de TODOS
    los demas segmentos SI se escribieron correctamente en sus propias
    actions (Chicken1AnimSegment.seg_action_name), pero esas actions quedan
    huerfanas en bpy.data.actions, sin ninguna pista NLA ni active action
    que las evalue durante la reproduccion. Por eso se veia el recorrido
    base (Capa 1, resuelto por las pistas NLA de path_recorder.py, que
    siguen intactas debajo) sin ningun rastro de las poses.

    La solucion (igual que Alfred): en vez de dejar la action del segmento
    como active action compartida, se empuja a su PROPIA pista NLA aislada,
    acotada exactamente a [frame_start, frame_end], con extrapolation
    'NOTHING' (no se filtra fuera de su rango, dejando ver las pistas de
    abajo) y blend_type 'REPLACE' (dentro de su rango, sustituye por
    completo al recorrido base para los canales que trae -- que es
    exactamente lo que hace el mezclado alpha ya calculado en el loop).
    Se limpia armature.animation_data.action = None al final para que
    ninguna quede como "active action" flotando por encima de todo el
    stack NLA."""
    if obj is None or action is None or not get_fcurves(action):
        return
    if not obj.animation_data:
        obj.animation_data_create()
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


# Mapa de nombre de bone a bones del segmento (affect_*)
# Solo para compatibilidad con codigo antiguo — ya no se usa en CONCATENAR
_BONE_AFFECT_MAP = {
    "Root_M_chicken_1":       "affect_body",
    "Spine1_M_chicken_1":      "affect_body",
    "Scapula_R_chicken_1": "affect_right_arm",
    "Scapula_L_chicken_1":  "affect_left_arm",
    "Hip_R_chicken_1": "affect_right_leg",
    "Hip_L_chicken_1":  "affect_left_leg",
    "Armature":          "affect_root",
}

# Mapa granular: nombre de bone → propiedad filter_* del segmento
# Si filter_* es True el bone está FILTRADO (excluido de las poses)
# Mapa granular: nombre de bone → propiedad filter_* del segmento
# Si filter_* es True el bone está FILTRADO (excluido de las poses)
_BONE_FILTER_MAP = {
    # Caderas / raiz
    "Root_M_chicken_1":        "filter_hips",
    # Columna vertebral
    "Spine1_M_chicken_1":       "filter_spine",
    "Chest_M_chicken_1":      "filter_spine1",
    "Neck_M_chicken_1":      "filter_spine2",
    # Cabeza / cuello
    "Head_M_chicken_1":        "filter_neck",
    "Jaw_M_chicken_1":        "filter_face",
    "Jaw_top_chicken_1":      "filter_jaw_top",
    "Jaw_bot_chicken_1":      "filter_jaw_bot",
    # Brazo derecho
    "Scapula_R_chicken_1":  "filter_right_arm",
    "Shoulder_R_chicken_1": "filter_right_shoulder",
    "Elbow_R_chicken_1":  "filter_right_elbow",
    # Brazo izquierdo
    "Scapula_L_chicken_1":   "filter_left_arm",
    "Shoulder_L_chicken_1":  "filter_left_shoulder",
    "Elbow_L_chicken_1":   "filter_left_elbow",
    # Pierna derecha
    "Hip_R_chicken_1":  "filter_right_leg",
    "Knee_R_chicken_1":   "filter_right_knee",
    "Ankle_R_chicken_1":  "filter_right_ankle",
    # Pierna izquierda
    "Hip_L_chicken_1":   "filter_left_leg",
    "Knee_L_chicken_1":    "filter_left_knee",
    "Ankle_L_chicken_1":   "filter_left_ankle",
    # Poles de rodilla (bones sueltos)
    "Knee.Right_chicken_1": "filter_knee_pole_r",
    "Knee.Left_chicken_1":  "filter_knee_pole_l",
    # Herramientas / accesorios
    "no_bone_01_chicken_1":         "filter_no_bone_01",
    "no_bone_02_chicken_1":         "filter_no_bone_02",
    "no_bone_03_chicken_1":         "filter_no_bone_03",
    "no_bone_04_chicken_1":         "filter_no_bone_04",
    "no_bone_05_chicken_1":         "filter_no_bone_05",
    "no_bone_06_chicken_1":         "filter_no_bone_06",
}


def _activar_filtros_organicos_por_defecto(context):
    """
    En este addon 'organic' vive a nivel global (scene.ch1st.organic, no por
    segmento -- ver docstring de CH1SEG_OT_AutoSplitFromConfig). El usuario
    pidio que, cada vez que se crea un segmento (Agregar segmento / Dividir
    segmentos), la seccion "Filtros organicos" quede activada por defecto,
    en vez de arrancar desactivada (Chicken1OrganicFilters.enabled=False de
    fabrica en properties.py) y haber que tildarla a mano cada vez.
    """
    st = getattr(context.scene, "ch1st", None)
    if st is not None and not st.organic.enabled:
        st.organic.enabled = True


def _bone_is_filtered(seg, bone_name):
    """Retorna True si el bone está FILTRADO (no debe recibir poses del segmento).
    Si filter_show está desactivado, ningún bone está filtrado."""
    if not getattr(seg, "filter_show", False):
        return False
    filter_attr = _BONE_FILTER_MAP.get(bone_name)
    if filter_attr is None:
        return False  # bone sin mapeo → no filtrado
    return getattr(seg, filter_attr, False)


# =============================================================================
# OPERADOR PRINCIPAL: APLICAR SEGMENTOS
# =============================================================================

class CH1SEG_OT_Apply(Operator):
    bl_idname  = "ch1seg.apply"
    bl_label   = "APLICAR SEGMENTOS"
    bl_description = (
        "Aplica todos los segmentos activos del Paso 3 sobre la animacion de "
        "recorrido generada por los Pasos 1+2. Los bones configurados adoptaran "
        "las poses definidas en cada segmento, mezcladas con el movimiento existente."
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene    = context.scene
        seg_cfg  = scene.ch1_segs
        segments = [s for s in seg_cfg.segments if s.enabled]

        if not segments:
            self.report({"WARNING"}, "No hay segmentos activos en el Paso 3")
            return {"CANCELLED"}

        armature = _resolve_armature(seg_cfg, scene)
        if armature is None:
            self.report({"ERROR"}, f"No se encontro armature '{seg_cfg.armature_name}'")
            return {"CANCELLED"}

        # FIX 4 (parte 2): limpiar, ANTES del loop, las pistas NLA "CH1SEG_*"
        # que hayan quedado de una corrida anterior de "Concatenar segmentos"
        # -- si no, cada click del boton apila pistas nuevas encima de las
        # viejas indefinidamente (igual que hace ALFREDSEG_OT_ConcatenateAll
        # con sus pistas "ALFSEG_*" antes de su propio loop).
        if armature.animation_data:
            for _trk in list(armature.animation_data.nla_tracks):
                if _trk.name.startswith("CH1SEG_"):
                    armature.animation_data.nla_tracks.remove(_trk)
        for _sec_name in SECONDARY_ARMATURES:
            _sec_obj = scene.objects.get(_sec_name)
            if _sec_obj is not None and _sec_obj.animation_data:
                for _trk in list(_sec_obj.animation_data.nla_tracks):
                    if _trk.name.startswith("CH1SEG_"):
                        _sec_obj.animation_data.nla_tracks.remove(_trk)

        # FIX (poses no inyectadas al Concatenar): 'seg_cfg.poses_dir'
        # (scene.ch1_segs.poses_dir) es un campo que NO se expone en ningun
        # panel -- el usuario nunca puede editarlo -- y su default en
        # properties.py quedo apuntando a la carpeta de OTRO personaje
        # (Alfred) heredada de la plantilla. Las poses que el usuario agrega
        # a cada segmento se eligen siempre con la carpeta configurada en
        # "Carpetas > Poses" (ch1st.poses_dir, la unica visible en el Paso
        # 1/2 y en la seccion de Carpetas). Por eso _load_action_pose()
        # buscaba los .json en una carpeta que no existe / no tiene esos
        # archivos y devolvia None -> "sin poses cargadas, ignorado": el
        # recorrido base (Capa 1, via NLA) seguia reproduciendose porque la
        # accion del segmento casi vacia no pisaba esos canales, pero las
        # poses jamas se escribian. Se resuelve la carpeta real desde
        # ch1st.poses_dir primero, y solo se cae a seg_cfg.poses_dir si esa
        # no esta configurada (compatibilidad con .blend viejos).
        st_cfg = getattr(scene, "ch1st", None)
        _poses_dir_src = (getattr(st_cfg, "poses_dir", "") if st_cfg else "") or seg_cfg.poses_dir
        poses_dir = bpy.path.abspath(_poses_dir_src)
        applied   = 0
        errors    = []

        # FIX 2 (poses no inyectadas al Concatenar): este bloque existe en
        # ALFREDSEG_OT_Apply (alfred_animation_studio) y NO se habia portado
        # a este addon. Las poses se escriben en 'pose.bones[...].rotation_euler'
        # (ver dp_rot abajo), pero el rotation_mode por defecto de un bone en
        # Blender es QUATERNION -- con ese modo activo, Blender ignora POR
        # COMPLETO los fcurves de rotation_euler (no producen error, ni
        # warning, simplemente no mueven el bone). Por eso el recorrido base
        # (Capa 1, vía NLA, que sí usa el canal correcto para su propio modo
        # de rotacion) se seguia viendo con normalidad mientras las poses
        # quedaban escritas en el Action pero invisibles. Forzamos XYZ antes
        # de inyectar para que el canal que se escribe sea el que realmente
        # conduce al bone.
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

        for seg_idx_loop, seg in enumerate(segments):
            f_start = seg.frame_start
            _is_recorrido = not seg.single_coord_mode

            # ── Determinar frame_end y la action destino ──────────────────────
            if seg.single_coord_mode:
                total_dur = 0
                for ap in seg.action_poses:
                    total_dur += ap.duration
                total_dur  = max(total_dur, 2)
                f_end = f_start + total_dur - 1
                seg.frame_end      = f_end
                seg.frame_end_auto = f_end
                # Modo 1 coord: usar la action global del armature.
                #
                # FIX (filtros organicos con 0 targets en pipelines SIN
                # recorrido, ej. "parado"/idle): a diferencia del modo
                # recorrido -- que siempre crea/reutiliza su propia
                # seg_action dedicada mas abajo -- este branch exigia que
                # `armature.animation_data.action` YA existiera de antes
                # ("armature sin action activa" -> continue si no). En un
                # personaje sin recorrido grabado (todos los segmentos con
                # single_coord_mode=True, caso tipico de una secuencia de
                # poses estaticas) no hay ningun paso previo que deje una
                # active action puesta -- y tras el primer "Concatenar"
                # ademas queda en None porque el modo recorrido la limpia
                # explicitamente (_push_action_to_nla). Resultado: TODOS
                # los segmentos fallaban con ese error, `applied` quedaba
                # en 0, pero el operador igual devolvia FINISHED (no
                # chequeaba `applied`), asi que ConcatenateAll no se
                # enteraba -- por eso "concatenar" parecia funcionar (no
                # tiraba error visible) pero _get_organic_target_actions()
                # despues no encontraba ninguna action/pista NLA sobre la
                # que aplicar los filtros organicos ("0 action(s) ... SIN
                # ACTIONS DESTINO"). Se crea la action si falta, en vez de
                # abortar el segmento.
                if not armature.animation_data:
                    armature.animation_data_create()
                if not armature.animation_data.action:
                    _sc_action_name = f"CH1_singlecoord_{armature.name}"
                    _sc_action = bpy.data.actions.get(_sc_action_name)
                    if _sc_action is None:
                        _sc_action = bpy.data.actions.new(name=_sc_action_name)
                    armature.animation_data.action = _sc_action
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
                # FIX 4 (poses no inyectadas al Concatenar): antes se hacia
                # `armature.animation_data.action = action` aca -- dejaba la
                # action de ESTE segmento como "active action" del armature,
                # y la siguiente vuelta del loop la pisaba con la del
                # siguiente segmento. Al terminar, solo la del ULTIMO
                # segmento procesado quedaba activa/visible; las demas,
                # aunque con las poses ya escritas en sus fcurves, quedaban
                # huerfanas (sin pista NLA ni active action que las
                # evaluara) -- de ahi que solo se viera el recorrido base.
                # Ya NO se asigna aca: mas abajo, al terminar de inyectar y
                # suavizar este segmento, su action se empuja a su PROPIA
                # pista NLA aislada (_push_action_to_nla), en vez de pelear
                # por el unico slot de "active action" del armature.

            if f_end <= f_start:
                errors.append(f"Segmento '{seg.label}': frame_end <= frame_start, ignorado")
                continue

            total_frames = f_end - f_start

            # Cargar poses: la primera y ultima pose de accion actuan como
            # anclas implicitas de inicio/fin del segmento. Se usa el indice
            # exacto elegido por el usuario (item.pose_index) dentro del
            # archivo JSON de biblioteca -- no la pose [0] del archivo.
            _act_list  = list(seg.action_poses)
            pose_start = _load_action_pose(_act_list[0],  poses_dir) if _act_list else None
            pose_end   = _load_action_pose(_act_list[-1], poses_dir) if _act_list else None
            pose_mid   = _load_pose_from_file(seg.pose_mid_file,   poses_dir) if seg.pose_mid_file   else None

            if pose_start is None and pose_end is None:
                errors.append(f"Segmento '{seg.label}': sin poses cargadas, ignorado")
                continue
            if pose_start is None: pose_start = pose_end
            if pose_end   is None: pose_end   = pose_start

            # FIX 5 (blend_in/blend_out arrancaban desde T-pose en vez del
            # recorrido real): con el segmento ya aislado en su propia pista
            # NLA (blend_type='REPLACE', FIX 4 arriba), el punto de partida
            # del mezclado alpha SI importa dentro del propio rango del
            # segmento -- ya no hay una Capa 1 "por debajo" mezclandose,
            # esta action la sustituye por completo. Usar rest pose fijo
            # (rot=0, loc=0, scale=1) como base hacia que el personaje
            # "saltara" a T-pose durante las rampas de entrada/salida en vez
            # de partir del recorrido real (caminar/saltar) en ese instante.
            # Se captura aca, frame a frame, la pose YA evaluada del
            # armature (Capa 1 + segmentos previos, ya aislados en sus
            # propias pistas NLA con extrapolation='NOTHING' asi que no se
            # filtran fuera de su propio rango) ANTES de agregar la pista de
            # ESTE segmento -- exactamente lo que hace
            # ALFST_OT_Concatenate en Alfred ("CAPTURA DE CAPA 1 ... ANTES
            # de borrar la action"). Solo aplica a modo recorrido: en modo
            # 1 coordenada no hay Capa 1 -- ahi se sigue usando el valor ya
            # escrito en la action compartida (ver _get_fcurve_value_at mas
            # abajo).
            _base_capture = {}
            if _is_recorrido:
                _frame_backup = scene.frame_current
                for _cf in range(f_start, f_end + 1):
                    scene.frame_set(_cf)
                    _fb = {}
                    for _bn in BONES_LISTA_FULL:
                        _pb_cap = armature.pose.bones.get(_bn)
                        if _pb_cap is not None:
                            _fb[_bn] = (
                                tuple(_pb_cap.rotation_euler),
                                tuple(_pb_cap.location),
                                tuple(_pb_cap.scale),
                            )
                    _base_capture[_cf] = _fb
                scene.frame_set(_frame_backup)

            # ── Inyectar configuracion: respetar filtros granulares del segmento ──
            for bone_name in BONES_LISTA_FULL:
                if _bone_is_filtered(seg, bone_name):
                    continue   # bone filtrado por el usuario: no recibe poses

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

                    # FIX 3+5: punto de partida del blend alpha.
                    # - Modo recorrido (segmento aislado en su propia pista
                    #   NLA, FIX 4): usar la pose de Capa 1 capturada en
                    #   _base_capture (ver FIX 5 arriba) -- asi las rampas de
                    #   entrada/salida (blend_in/blend_out) parten del
                    #   caminar/saltar real en ese instante, no de un salto
                    #   a T-pose.
                    # - Modo 1 coordenada (accion compartida, sin Capa 1
                    #   propia): mantener _get_fcurve_value_at(), que lee lo
                    #   que ya este escrito en esa action en este frame
                    #   exacto (compatibilidad con el diseño original de
                    #   ese modo).
                    if _is_recorrido:
                        _cap = _base_capture.get(frame, {}).get(bone_name)
                        if _cap is not None:
                            _cap_rot, _cap_loc, _cap_sca = _cap
                        else:
                            _cap_rot, _cap_loc, _cap_sca = (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)
                    for axis_idx, (pv_rot, pv_loc, pv_sca) in enumerate(
                        zip(rot_pose, loc_pose, sca_pose)
                    ):
                        if _is_recorrido:
                            base_rot = _cap_rot[axis_idx]
                            base_loc = _cap_loc[axis_idx]
                            base_sca = _cap_sca[axis_idx]
                        else:
                            base_rot = _get_fcurve_value_at(bone_action, dp_rot, axis_idx, frame)
                            base_loc = _get_fcurve_value_at(bone_action, dp_loc, axis_idx, frame)
                            base_sca = _get_fcurve_value_at(bone_action, dp_scale, axis_idx, frame)
                            if get_fcurves(bone_action).find(dp_scale, index=axis_idx) is None:
                                base_sca = 1.0

                        _set_keyframe(bone_action, dp_rot, axis_idx, frame,
                                      base_rot + (pv_rot - base_rot) * alpha)
                        _set_keyframe(bone_action, dp_loc, axis_idx, frame,
                                      base_loc + (pv_loc - base_loc) * alpha)
                        _set_keyframe(bone_action, dp_scale, axis_idx, frame,
                                      base_sca + (pv_sca - base_sca) * alpha)

            # ── Suavizar SOLO fcurves de bones NO filtrados (no tocar la torta) ──
            affected_dps = set()
            for bone_name in BONES_LISTA_FULL:
                if not _bone_is_filtered(seg, bone_name):
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

            # FIX 4 (parte 3): empujar la action ya horneada de este
            # segmento a su propia pista NLA aislada, en vez de dejarla
            # como active action compartida (ver comentario en
            # _push_action_to_nla() y en la asignacion que se quito arriba,
            # justo antes de "Determinar frame_end y la action destino").
            # Modo 1 coordenada no se toca: sigue usando la action
            # compartida del armature tal cual, sin pista NLA propia.
            if _is_recorrido:
                _safe_label = "".join(
                    c if c.isalnum() else "_" for c in (seg.label or "seg")
                )[:32]
                _track_name = f"CH1SEG_{seg_idx_loop:02d}_{_safe_label}"
                _push_action_to_nla(armature, action, f_start, f_end, _track_name)

            applied += 1

        # NOTA (Kebyn, corregido): un segmento de recorrido SIN poses
        # (seg.action_poses vacio) es una configuracion VALIDA -- el tramo
        # solo aporta el recorrido base (caminar/saltar/parada) generado
        # por preview_path(), sin ningun pose extra encima; no es un
        # error. Por eso `applied == 0` con `errors` llenos de "sin poses
        # cargadas, ignorado" ya NO aborta con CANCELLED (eso rompia el
        # caso normal de un pipeline solo-recorrido + filtros organicos,
        # como el de chicken_1 "caminar/saltar/parada" sin poses
        # asignadas). El post-proceso de filtros organicos en
        # CH1SEG_OT_ConcatenateAll ahora sabe encontrar y modificar
        # directamente las pistas 'Slot_NNN_arm' del recorrido base (ver
        # _get_organic_target_actions en operators_anim.py), asi que
        # sigue funcionando aunque ningun segmento haya podido aplicar una
        # pose. Solo se advierte por consola/reporte, sin cortar el flujo.
        if applied == 0 and segments and errors:
            print(f"[JRRSTSeg] Ningun segmento aplico pose (recorrido base sin poses extra): "
                  + "; ".join(errors))

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


# =============================================================================
# DIVIDIR SEGMENTOS (Paso 3) — un segmento por cada tramo del recorrido
# =============================================================================

class CH1SEG_OT_AutoSplitFromConfig(Operator):
    """
    Port de ALFREDSEG_OT_AutoSplitFromConfig (Alfred Animation Studio, Paso 3
    -- boton 'Dividir segmentos'): en vez de que todos los tramos del
    recorrido (caminar/saltar_subir/saltar_bajar/parada) queden acumulados
    en un unico Chicken1AnimSegment gigante, este operador crea UN
    Chicken1AnimSegment por cada tramo del recorrido.

    Usa directamente la misma lista que ya se ve en el panel bajo
    "Estimacion de segmentos:" (calcular_estimacion_geometrica(), en
    path_recorder.py -- la fuente que agrupa scene.ch1_path.path_points en
    tramos caminar/saltar_subir/saltar_bajar/parada). El boton "Dividir
    segmentos" crea tantos segmentos como tramos aparecen en esa lista, con
    frame_start/frame_end calculados acumulando "frames_estimados" de cada
    tramo a partir de scene.ch1_path.frame_inicio -- el mismo orden y las
    mismas duraciones que ya se preveian en el panel antes de dividir.

    Cada segmento nuevo queda:
      - label:  "{indice:02d}_{tipo}" — ej. "04_parada", "06_caminar".
      - frame_start / frame_end: acumulados desde la estimacion.
      - single_coord_mode = False (modo recorrido).
      - seg_action dedicada, generada igual que CH1SEG_OT_Add: se evalua el
        Empty "chicken_1" frame a frame dentro de [frame_start, frame_end]
        para capturar el desplazamiento puro del root ya resuelto por el NLA.
      - Poses (action_poses) quedan en blanco: cada tramo se configura
        despues individualmente.
      - Piernas bloqueadas (filter_right_leg/knee/ankle, filter_left_leg/knee/ankle) en
        los tramos "caminar" -- el recorrido base ya anima las piernas con
        el ciclo de caminata; libres en el resto (parada/saltos), igual que
        en Alfred.

    Chicken1AnimSegment no tiene organic/blink_intervals/bone_blocks propios
    por segmento (esos sistemas viven a nivel global en scene.ch1st en este
    addon), asi que -a diferencia de la version de Alfred- este operador no
    necesita aplicar defaults organicos/parpadeo por segmento.
    """
    bl_idname  = "ch1seg.autosplit_from_config"
    bl_label   = "Dividir segmentos"
    bl_description = (
        "Crea un segmento independiente por cada tramo (caminar/saltar_subir/"
        "saltar_bajar/parada) segun la 'Estimacion de segmentos' del "
        "recorrido grabado, en vez de un unico segmento que cubre todo "
        "el recorrido"
    )
    bl_options = {"REGISTER", "UNDO"}

    reemplazar_existentes: BoolProperty(
        name="Reemplazar segmentos existentes",
        description="Si esta activo, borra todos los segmentos actuales antes de crear los nuevos",
        default=True,
        options={"SKIP_SAVE"},
    )

    def execute(self, context):
        _activar_filtros_organicos_por_defecto(context)

        scene = context.scene
        pc = getattr(scene, "ch1_path", None)
        if pc is None:
            self.report({"ERROR"}, "No se encontro el recorrido (scene.ch1_path).")
            return {"CANCELLED"}

        from .path_recorder import calcular_estimacion_geometrica
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
            tramos.append({"tipo": s["tipo"], "frame_start": fs, "frame_end": fe})
            cursor = fe + 1

        segs = context.scene.ch1_segs

        if self.reemplazar_existentes:
            for old_seg in segs.segments:
                if old_seg.seg_action_name:
                    old_act = bpy.data.actions.get(old_seg.seg_action_name)
                    if old_act:
                        bpy.data.actions.remove(old_act, do_unlink=True)
            segs.segments.clear()

        arm_obj = _resolve_armature(segs, scene)
        if arm_obj is None:
            arm_name = segs.armature_name or "Armature"
            self.report({"ERROR"},
                f"No se encontro el armature '{arm_name}'. Verifica "
                "'Nombre armature' en la config del Paso 3.")
            return {"CANCELLED"}

        root_empty = scene.objects.get("chicken_1")
        if root_empty is None or not root_empty.animation_data:
            self.report({"WARNING"},
                "No se encontro el Empty 'chicken_1' con animation_data "
                "(recorrido de Pasos 1+2). Los segmentos se crearan con "
                "frame_start/frame_end correctos pero SIN captura de "
                "desplazamiento del root; genera primero el recorrido con "
                "path_recorder.")

        # ── Auto-detectar el bone raiz real del armature ────────────────────
        # 'spine_6' es el bone raiz del rig de chicken_1 (ver CH1SEG_OT_Add
        # mas abajo, mismo criterio). Si no existe, se usa el primer pose
        # bone sin padre (raiz real de la jerarquia) como ultimo recurso.
        _root_bone_name = None
        if arm_obj.pose.bones.get("spine_6") is not None:
            _root_bone_name = "spine_6"
        if _root_bone_name is None:
            for pb in arm_obj.pose.bones:
                if pb.parent is None:
                    _root_bone_name = pb.name
                    break
        if _root_bone_name is None:
            self.report({"ERROR"},
                f"No se pudo determinar el bone raiz de '{arm_obj.name}' "
                "(no se encontro 'spine_6' ni ningun bone sin padre).")
            return {"CANCELLED"}

        st = context.scene.ch1st
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
                    fc_loc = [ensure_fcurves(seg_action).new(dp_loc, index=k) for k in range(3)]
                    fc_rot = [ensure_fcurves(seg_action).new(dp_rot, index=k) for k in range(3)]

                    for _f in range(fs, fe + 1):
                        for k in range(3):
                            fc_loc[k].keyframe_points.insert(frame=_f, value=0.0, options={"FAST"})
                            fc_rot[k].keyframe_points.insert(frame=_f, value=0.0, options={"FAST"})
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

                # ── Bloqueo de piernas segun tipo de tramo (mismo criterio que
                # Alfred): "caminar" -> piernas BLOQUEADAS (el recorrido base ya
                # las anima con el ciclo de caminata). "parada"/"saltar_*" ->
                # piernas LIBRES para que la pose del segmento las controle.
                _piernas_bloqueadas = tipo == "caminar"
                seg.filter_show       = True
                seg.filter_main_bone  = True
                seg.filter_right_leg   = _piernas_bloqueadas
                seg.filter_right_knee  = _piernas_bloqueadas
                seg.filter_right_ankle = _piernas_bloqueadas
                seg.filter_left_leg    = _piernas_bloqueadas
                seg.filter_left_knee   = _piernas_bloqueadas
                seg.filter_left_ankle  = _piernas_bloqueadas

                creados += 1

            except Exception as e_seg:
                import traceback
                print(f"[Ch1Seg] Error en tramo {i} ({tramo.get('tipo')}):")
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
                print(f"[Ch1Seg] {e}")
            self.report({"WARNING"}, msg)
        else:
            self.report({"INFO"}, msg)
        return {"FINISHED"}


# =============================================================================
# CONCATENAR SEGMENTOS (Paso 3) — aplica TODOS los segmentos activos y reproduce
# =============================================================================

class CH1SEG_OT_ConcatenateAll(Operator):
    """
    Port de ALFREDSEG_OT_ConcatenateAll (Alfred Animation Studio, Paso 3 --
    boton 'Concatenar segmentos'). En Alfred ese boton llama, uno por uno y
    de forma aislada por NLA, al operador CONCATENAR individual de cada
    segmento activo.

    En chicken_1 el equivalente directo ya existe en CH1SEG_OT_Apply
    ("ch1seg.apply" -- "Aplica todos los segmentos activos del Paso 3 sobre
    la animacion de recorrido generada por los Pasos 1+2"): ese operador
    recorre todos los segmentos activos y mezcla sus poses.

    NOTA (FIX 4, corrige el supuesto de este docstring): a diferencia de lo
    que se afirmaba aca antes ("ya no hace falta aislar por NLA, cada
    segmento respeta su propio rango de frames"), CH1SEG_OT_Apply SI
    necesitaba el mismo aislamiento por NLA que usa Alfred -- sin el, solo
    la action del ULTIMO segmento procesado quedaba activa/visible al
    terminar el loop, y las poses de los demas segmentos (aunque ya
    escritas en sus propios fcurves) nunca se veian durante la
    reproduccion. Ese aislamiento (_push_action_to_nla, dentro de
    ch1seg.apply) ya esta portado; este operador se limita a:
      1. Regenerar la Capa 1 (recorrido base caminar/saltar/parada, via
         ch1pr.preview_path) si hay algun segmento activo en modo recorrido
         -- igual que hace ALFREDSEG_OT_ConcatenateAll antes de inyectar
         poses, para no arrastrar un canvas sucio de una reproduccion previa.
      2. Ejecutar ch1seg.apply (inyeccion de poses de TODOS los segmentos
         activos).
      3. Ajustar el rango de reproduccion al tramo global cubierto por los
         segmentos activos y reproducir la secuencia completa de principio
         a fin.
    """
    bl_idname  = "ch1seg.concatenate_all"
    bl_label   = "Concatenar segmentos"
    bl_description = (
        "Ejecuta 'APLICAR SEGMENTOS' (inyectar poses -> bones configurados) "
        "para todos los segmentos activos del Paso 3, respetando la "
        "secuencia de frames propia de cada segmento, y luego reproduce "
        "todo de principio a fin"
    )
    bl_options = {"REGISTER"}   # SIN UNDO: dispara reproduccion, igual que ALFREDSEG_OT_ConcatenateAll

    def execute(self, context):
        scene   = context.scene
        seg_cfg = scene.ch1_segs

        active_segs = [s for s in seg_cfg.segments if s.enabled]
        if not active_segs:
            self.report({"WARNING"}, "No hay segmentos activos en el Paso 3")
            return {"CANCELLED"}

        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()

        # ── Regenerar Capa 1 (recorrido base) antes de inyectar poses ─────────
        # Igual que en Alfred: si el recorrido horneado en la timeline no esta
        # fresco, cada segmento sin poses (o el inicio de su ease-in) puede
        # arrancar desde lo que haya quedado ahi en vez de partir del
        # desplazamiento base real. Se omite si TODOS los segmentos activos
        # son de 1 coordenada (no pertenecen a ningun recorrido grabado).
        _hay_recorrido_activo = any(not s.single_coord_mode for s in active_segs)
        if _hay_recorrido_activo:
            _regen = bpy.ops.ch1pr.preview_path()
            if "CANCELLED" in _regen:
                self.report(
                    {"ERROR"},
                    "No se pudo regenerar el recorrido base (Capa 1) antes de "
                    "concatenar. Revisa el recorrido grabado / el .blend del "
                    "personaje.")
                return {"CANCELLED"}

        try:
            result = bpy.ops.ch1seg.apply()
        except RuntimeError as e_apply:
            self.report({"ERROR"}, f"Fallo al aplicar los segmentos: {e_apply}")
            return {"CANCELLED"}

        if "FINISHED" not in result:
            self.report({"ERROR"}, "No se pudieron concatenar los segmentos activos")
            return {"CANCELLED"}

        # ── Rango global cubierto por los segmentos activos ────────────────────
        f_min = min(s.frame_start for s in active_segs)
        f_max = None
        for s in active_segs:
            _, f_e_calc = _calc_seg_frames(s)
            f_e = s.frame_end if s.frame_end > s.frame_start else f_e_calc
            f_max = f_e if f_max is None else max(f_max, f_e)

        # ── Post-proceso: filtros de movimiento organico ──────────────────────
        # Tras inyectar las poses de todos los segmentos, se hornean los filtros
        # organicos activos (respiracion, aleteo de alas, cabeceo, etc.) sobre el
        # rango global concatenado, de modo que se REPRODUZCAN junto con la
        # secuencia al pulsar "Concatenar segmentos". El toggle maestro
        # (st.organic.enabled) se activa por defecto al crear un segmento.
        #
        # FIX (filtros organicos seguian sin reproducirse tras el fix de
        # aislamiento NLA): mismo patron de bug que describe
        # POSE_INJECTION_FIX.md pero en la resolucion del armature, no en la
        # inyeccion de poses. Este bloque resolvia el armature via
        # `scene.objects.get(st.armature_name)`, con `st = scene.ch1st`
        # (Chicken1StudioSettings.armature_name, default="" -- string
        # vacio en properties.py). Si esa property nunca se poblo en la
        # sesion actual (depende de por que flujo del Paso 1 se cargo el
        # personaje), `scene.objects.get("")` devuelve None EN SILENCIO --
        # sin error, sin warning -- y todo este bloque se saltaba entero,
        # aunque el checkbox "Filtros organicos" estuviera activo y las
        # poses ya se hubieran inyectado bien (por eso el resto de la
        # animacion SI se reproducia con normalidad). La inyeccion de
        # poses de mas arriba (bpy.ops.ch1seg.apply()) nunca tuvo este
        # problema porque usa _resolve_armature(seg_cfg, scene), que lee
        # scene.ch1_segs.armature_name (default "Armature_chicken_1") y
        # ademas cae a "Armature_chicken_1"/"Dog_001_rig" si viene vacio.
        # Se reutiliza esa misma resolucion robusta aqui para garantizar
        # que el post-proceso organico apunte SIEMPRE al mismo objeto que
        # acaba de recibir las poses.
        st  = scene.ch1st
        org = getattr(st, "organic", None)
        _org_stats_msg = ""
        if org is not None and getattr(org, "enabled", False) and f_max is not None:
            armature = _resolve_armature(seg_cfg, scene)
            if armature is not None:
                from .operators_anim import _apply_organic_filters
                try:
                    _org_stats = _apply_organic_filters(context, armature, int(f_min), int(f_max), org)
                    if _org_stats:
                        _org_stats_msg = (
                            f"organicos: {_org_stats['targets']} action(s), "
                            f"{_org_stats['fcurves_touched']} fcurves, "
                            f"{_org_stats['keys_touched']} keys modificados"
                        )
                        if _org_stats["targets"] == 0:
                            _org_stats_msg += " -- SIN ACTIONS DESTINO (revisa NLA 'CH1SEG_*'/active action)"
                        elif _org_stats["keys_touched"] == 0:
                            _org_stats_msg += " -- 0 keyframes tocados (dp/bone sin match, revisa BONES_LISTA)"
                except Exception as e_org:
                    self.report(
                        {"WARNING"},
                        f"No se pudieron aplicar los filtros organicos: {e_org}")
            else:
                _org_stats_msg = "organicos: armature no encontrado"
                self.report(
                    {"WARNING"},
                    "Filtros organicos activos pero no se encontro el "
                    "armature (revisa Carpetas/armature del Paso 1)")

        if scene.frame_start > f_min:
            scene.frame_start = f_min
        if f_max is not None and scene.frame_end < f_max:
            scene.frame_end = f_max
        scene.frame_set(f_min)

        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()

        def _deferred_play():
            if not bpy.context.screen.is_animation_playing:
                bpy.ops.screen.animation_play()
            return None
        bpy.app.timers.register(_deferred_play, first_interval=0.02)

        seg_cfg.segs_applied = True
        seg_cfg.status_msg = (
            f"Secuencia concatenada: {len(active_segs)} segmentos activos, "
            f"frames {f_min}->{f_max}"
        )
        if _org_stats_msg:
            seg_cfg.status_msg += " | " + _org_stats_msg
        self.report({"INFO"}, seg_cfg.status_msg)
        return {"FINISHED"}


# =============================================================================
# CRUD DE SEGMENTOS
# =============================================================================

class CH1SEG_OT_Add(Operator):
    bl_idname  = "ch1seg.add"
    bl_label   = "Agregar segmento"
    bl_description = "Agrega un nuevo segmento de refinado al Paso 3"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        _activar_filtros_organicos_por_defecto(context)

        segs = context.scene.ch1_segs
        pc   = context.scene.ch1_path

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
            arm_name = segs.armature_name or "Armature_chicken_1"
            arm_obj  = context.scene.objects.get(arm_name)
            root_empty = context.scene.objects.get("chicken_1")

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
                fc_loc = [ensure_fcurves(seg_action).new(dp_loc, index=i) for i in range(3)]
                fc_rot = [ensure_fcurves(seg_action).new(dp_rot, index=i) for i in range(3)]

                # FIX (2026-08-09): identidad, no copia del Empty. El
                # armature ya hereda el 100% del desplazamiento del Empty
                # via el parent -- copiar root_empty.location/rotation_euler
                # (mundo) directo al bone raiz aplicaba el desplazamiento
                # DOS VECES (parent + fcurve) -> desface Empty vs armature.
                frame_backup = context.scene.frame_current
                for _f in range(fs, fe + 1):
                    for i in range(3):
                        fc_loc[i].keyframe_points.insert(frame=_f, value=0.0, options={"FAST"})
                        fc_rot[i].keyframe_points.insert(frame=_f, value=0.0, options={"FAST"})
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

        # Copiar configuracion completa desde ch1st (el sistema de poses actual)
        st = context.scene.ch1st
        # Parametros globales
        seg.fps         = st.fps
        seg.entry_ratio = st.entry_ratio
        seg.exit_ratio  = st.exit_ratio
        seg.export_slot_number = st.export_slot_number
        seg.export_type        = st.export_type
        seg.export_desc        = st.export_desc
        # Copiar action_poses (src: Chicken1PoseSlotItem, dst: Chicken1SegmentPoseSlot)
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
        segs.active_index = len(segs.segments) - 1

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


class CH1SEG_OT_UpdateFromEstimacion(Operator):
    """
    Actualiza los segmentos YA CREADOS del Paso 3 (scene.ch1_segs.segments)
    para que reflejen los frames por parada actuales (default 'Frames por
    parada' + individuales de pc.paradas_frames), sin tener que volver a
    dividir desde cero (eso borraria poses/filtros/configuracion ya cargada
    en cada segmento).

    Port del operador equivalente de Alfred Animation Studio (Paso 1/3),
    adaptado al esquema ACTUAL de Chicken1AnimSegment (sin
    single_coord_mode / frame_start_planned / frame_end_planned, que en
    este addon todavia no existen -- ver operators_segments.py de Alfred
    si en el futuro se porta esa parte del Paso 3 tambien).

    Por que hace falta: calcular_estimacion_slots() (path_recorder.py), una
    vez que ya existen segmentos reales, lee esos segmentos TAL CUAL estan
    (fuente 'paso3_segmentos') -- ya no vuelve a mirar la geometria del
    recorrido. Si el usuario sube o baja 'Frames por parada' DESPUES de
    dividir en Paso 3, ese cambio nunca se propaga a los segmentos reales
    ni al panel "Estimacion de segmentos". Este operador cierra ese hueco.

    Logica, tramo por tramo (mismo orden que la geometria actual del
    recorrido, via calcular_estimacion_geometrica):
      - "parada": se reajusta frame_end para que coincida con el nuevo
        valor de 'Frames por parada' (default o individual).
      - "caminar": se compara el estilo elegido AHORA en el dropdown
        (pc.walk_styles[i].style) contra el estilo que quedo "horneado"
        la ultima vez (pc.walk_styles[i].applied_style). Si no cambio, el
        tramo se deja intacto. Si cambio, se reajusta con la formula de
        chicken_1 (ciclo de caminata x repeticiones -- ver
        calcular_estimacion_geometrica en path_recorder.py).
      - "saltar_subir"/"saltar_bajar": nunca se reajustan de duracion,
        solo se reubican si algun tramo anterior cambio de tamano.
      - Cualquier cambio de tamano se propaga en cascada a los siguientes.
    """
    bl_idname    = "ch1seg.update_from_estimacion"
    bl_label     = "Actualizar segmentos con la estimacion actual"
    bl_description = (
        "Reajusta el rango de frames de los tramos 'parada' ya creados en "
        "el Paso 3 segun los valores actuales de 'Frames por parada' "
        "(default e individuales). Tambien reajusta un tramo 'caminar' si "
        "se le cambio el estilo de caminata (dropdown) desde la ultima "
        "vez que se presiono este boton. Los tramos de caminata sin "
        "cambio de estilo, y los de salto, solo se reubican en cascada, "
        "nunca cambian de duracion. No borra ni modifica poses, filtros "
        "ni ninguna otra configuracion ya cargada en los segmentos"
    )
    bl_options   = {"REGISTER", "UNDO"}

    def execute(self, context):
        from .path_recorder import calcular_estimacion_geometrica

        scene = context.scene
        pc = getattr(scene, "ch1_path", None)
        segs_data = getattr(scene, "ch1_segs", None)
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

        delta_acum    = 0
        n_reajustados = 0
        n_reubicados  = 0
        segs_poses_desbordadas = []
        for rseg, slot in zip(real_segs, slots_geo):
            if delta_acum:
                rseg.frame_start += delta_acum
                rseg.frame_end   += delta_acum
                n_reubicados += 1

            if slot["tipo"] == "caminar":
                _idx = slot.get("caminar_idx")
                if _idx is not None and _idx < len(pc.walk_styles):
                    entry = pc.walk_styles[_idx]
                    if entry.applied_style == "":
                        entry.applied_style = entry.style
                    elif entry.style != entry.applied_style:
                        nuevo_dur = max(1, int(slot["frames_estimados"]))
                        actual_dur = rseg.frame_end - rseg.frame_start + 1
                        delta_dur = nuevo_dur - actual_dur
                        entry.applied_style = entry.style
                        if delta_dur != 0:
                            rseg.frame_end = rseg.frame_start + nuevo_dur - 1
                            delta_acum += delta_dur
                            n_reajustados += 1
                            if rseg.action_poses:
                                _pd = sum(int(ap.duration) for ap in rseg.action_poses)
                                if _pd > nuevo_dur:
                                    segs_poses_desbordadas.append((rseg.label, _pd, nuevo_dur))
                continue

            if slot["tipo"] != "parada":
                continue

            nuevo_dur = max(1, int(slot["frames_estimados"]))
            actual_dur = rseg.frame_end - rseg.frame_start + 1
            delta_dur = nuevo_dur - actual_dur
            if delta_dur == 0:
                continue

            rseg.frame_end = rseg.frame_start + nuevo_dur - 1
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


class CH1SEG_OT_Remove(Operator):
    bl_idname  = "ch1seg.remove"
    bl_label   = "Eliminar segmento"
    bl_description = "Elimina el segmento activo"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.ch1_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if 0 <= idx < len(segs.segments):
            segs.segments.remove(idx)
            segs.active_index = max(0, idx - 1)
            self.report({"INFO"}, "Segmento eliminado")
        else:
            self.report({"WARNING"}, "No hay segmento seleccionado")
        return {"FINISHED"}


class CH1SEG_OT_Move(Operator):
    bl_idname  = "ch1seg.move"
    bl_label   = "Mover segmento"
    bl_description = "Sube o baja el segmento activo en la lista"
    bl_options = {"REGISTER", "UNDO"}

    direction: EnumProperty(items=[("UP", "Arriba", ""), ("DOWN", "Abajo", "")])

    def execute(self, context):
        segs = context.scene.ch1_segs
        idx  = segs.active_index
        n    = len(segs.segments)
        if self.direction == "UP" and idx > 0:
            segs.segments.move(idx, idx - 1)
            segs.active_index = idx - 1
        elif self.direction == "DOWN" and idx < n - 1:
            segs.segments.move(idx, idx + 1)
            segs.active_index = idx + 1
        return {"FINISHED"}


class CH1SEG_OT_Duplicate(Operator):
    bl_idname  = "ch1seg.duplicate"
    bl_label   = "Duplicar segmento"
    bl_description = "Duplica el segmento activo"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.ch1_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "No hay segmento seleccionado")
            return {"CANCELLED"}
        src = segs.segments[idx]
        dst = segs.segments.add()
        # Copiar atributos escalares
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
        segs = context.scene.ch1_segs
        # Escribe siempre en los campos edit_* del formulario de creacion
        if self._edit_target_attr:
            setattr(segs, self._edit_target_attr, self.filepath)
        if self._edit_label_attr:
            setattr(segs, self._edit_label_attr, os.path.basename(self.filepath))
        self.report({"INFO"}, f"Pose cargada: {os.path.basename(self.filepath)}")
        return {"FINISHED"}

    def invoke(self, context, event):
        segs = context.scene.ch1_segs
        self.filepath = bpy.path.abspath(segs.poses_dir) if segs.poses_dir else ""
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class CH1SEG_OT_PickPoseMid(_PickPoseBase):
    bl_idname    = "ch1seg.pick_pose_mid"
    bl_label     = "Seleccionar pose INTERMEDIA"
    bl_description = "Abre explorador para seleccionar el .json de la pose intermedia (opcional)"
    _target_attr = "pose_mid_file"
    _label_attr  = "pose_mid_label"
    _edit_target_attr = "edit_pose_mid_file"
    _edit_label_attr  = "edit_pose_mid_label"


# =============================================================================
# CAPTURA DE FRAMES DESDE LA TIMELINE
# =============================================================================

class CH1SEG_OT_SetFrameStart(Operator):
    bl_idname  = "ch1seg.set_frame_start"
    bl_label   = "Frame actual → Inicio"
    bl_description = "Usa el frame actual de la timeline como frame de inicio del segmento"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        segs = context.scene.ch1_segs
        idx  = segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "No hay segmento seleccionado"); return {"CANCELLED"}
        segs.segments[idx].frame_start = context.scene.frame_current
        return {"FINISHED"}


class CH1SEG_OT_SetFrameMid(Operator):
    bl_idname  = "ch1seg.set_frame_mid"
    bl_label   = "Frame actual → Intermedio"
    bl_description = "Usa el frame actual de la timeline como frame intermedio del segmento"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        segs = context.scene.ch1_segs
        idx  = segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "No hay segmento seleccionado"); return {"CANCELLED"}
        segs.segments[idx].frame_mid = context.scene.frame_current
        return {"FINISHED"}


class CH1SEG_OT_SetFrameEnd(Operator):
    bl_idname  = "ch1seg.set_frame_end"
    bl_label   = "Frame actual → Fin"
    bl_description = "Usa el frame actual de la timeline como frame de fin del segmento"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        segs = context.scene.ch1_segs
        idx  = segs.active_index
        if not (0 <= idx < len(segs.segments)):
            self.report({"WARNING"}, "No hay segmento seleccionado"); return {"CANCELLED"}
        segs.segments[idx].frame_end = context.scene.frame_current
        return {"FINISHED"}


# =============================================================================
# GUARDAR / CARGAR CONFIGURACION DEL PASO 3
# =============================================================================

class CH1SEG_OT_SaveConfig(Operator):
    bl_idname  = "ch1seg.save_config"
    bl_label   = "Guardar config Paso 3"
    bl_description = "Guarda la lista de segmentos del Paso 3 a un archivo .json"
    bl_options = {"REGISTER"}

    def execute(self, context):
        segs     = context.scene.ch1_segs
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
        ]
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
            data["segments"].append(d)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.report({"INFO"}, f"Config Paso 3 guardada: {os.path.basename(filepath)}")
        except Exception as e:
            self.report({"ERROR"}, f"Error al guardar: {e}")
            return {"CANCELLED"}
        return {"FINISHED"}


class CH1SEG_OT_LoadConfig(Operator):
    bl_idname  = "ch1seg.load_config"
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

        segs = context.scene.ch1_segs
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
        ]
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

        self.report({"INFO"}, f"Config Paso 3 cargada: {len(segs.segments)} segmentos")
        return {"FINISHED"}

    def invoke(self, context, event):
        segs = context.scene.ch1_segs
        self.filepath = bpy.path.abspath(segs.config_dir) if segs.config_dir else ""
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


# =============================================================================
# NUEVOS: Reproducir / Pausar / Detener segmento + Toggle enabled
# =============================================================================

class CH1SEG_OT_PlaySegment(Operator):
    """Salta al frame de inicio del segmento y reproduce hasta el frame fin calculado."""
    bl_idname  = "ch1seg.play_segment"
    bl_label   = "Reproducir segmento"
    bl_options = {"REGISTER"}          # SIN UNDO: UNDO interfiere con animation_play

    item_idx: bpy.props.IntProperty(default=0)

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        segs  = context.scene.ch1_segs
        if self.item_idx >= len(segs.segments):
            self.report({"ERROR"}, "Indice de segmento fuera de rango")
            return {"CANCELLED"}
        seg   = segs.segments[self.item_idx]
        scene = context.scene
        pc    = getattr(scene, "ch1_path", None)

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


class CH1SEG_OT_PauseSegment(Operator):
    """Pausa la reproduccion (toggle play/pause)."""
    bl_idname  = "ch1seg.pause_segment"
    bl_label   = "Pausar segmento"
    bl_options = {"REGISTER"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        bpy.ops.screen.animation_play()
        return {"FINISHED"}


class CH1SEG_OT_StopSegment(Operator):
    """Detiene la reproduccion y vuelve al frame de inicio del segmento."""
    bl_idname  = "ch1seg.stop_segment"
    bl_label   = "Detener segmento"
    bl_options = {"REGISTER"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        segs = context.scene.ch1_segs
        # Detiene si esta reproduciendo
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
        # Vuelve al frame de inicio del segmento
        if self.item_idx < len(segs.segments):
            seg = segs.segments[self.item_idx]
            context.scene.frame_set(seg.frame_start)
        return {"FINISHED"}


class CH1SEG_OT_ToggleEnabled(Operator):
    """Activa o desactiva un segmento de la lista."""
    bl_idname  = "ch1seg.toggle_enabled"
    bl_label   = "Activar/desactivar segmento"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        segs = context.scene.ch1_segs
        if self.item_idx >= len(segs.segments):
            return {"CANCELLED"}
        seg = segs.segments[self.item_idx]
        seg.enabled = not seg.enabled
        return {"FINISHED"}


# =============================================================================
# CAPTURA DEL FRAME ACTUAL PARA EL FORMULARIO (modo 1 coordenada)
# =============================================================================

class CH1SEG_OT_SetFrameStartEdit(Operator):
    """Copia el frame actual de la timeline al campo edit_frame_start del formulario."""
    bl_idname  = "ch1seg.set_frame_start_edit"
    bl_label   = "Frame actual → Frame inicio (formulario)"
    bl_description = (
        "En modo 1 coordenada: usa el frame actual de la timeline "
        "como frame de inicio del nuevo segmento"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        segs = context.scene.ch1_segs
        segs.edit_frame_start = context.scene.frame_current
        self.report({"INFO"}, f"Frame inicio del formulario -> {context.scene.frame_current}")
        return {"FINISHED"}


# =============================================================================
# OPERADORES DE POSES INTERMEDIAS (ACTION POSES) POR SEGMENTO
# Equivalentes a ch1st.add/edit/remove/move_action_pose pero escriben
# directamente en seg.action_poses del segmento activo (o item_idx).
# =============================================================================

class CH1SEG_OT_AddActionPoseSeg(Operator):
    bl_idname    = "ch1seg.add_action_pose_seg"
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
        segs = context.scene.ch1_segs
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
        _pc = getattr(context.scene, "ch1_path", None)
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
            box2.label(text="Paso 6 -- Posicion del Root:", icon="OBJECT_ORIGIN")
            row = box2.row(align=True)
            row.prop(self, "pos_x", text="X")
            row.prop(self, "pos_y", text="Y")
            row.prop(self, "pos_z", text="Z")
            layout.separator()
            box3 = layout.box()
            box3.label(text="Paso 7 -- Orientacion del Root [auto desde JSON]:", icon="ORIENTATION_LOCAL")
            col = box3.column(align=True)
            col.prop(self, "rot_x", text="Rot X")
            col.prop(self, "rot_y", text="Rot Y")
            col.prop(self, "rot_z", text="Rot Z")

    def execute(self, context):
        if self.json_file == "NONE":
            self.report({"WARNING"}, "No hay archivos JSON en la carpeta de poses")
            return {"CANCELLED"}
        st  = context.scene.ch1st
        seg = self._get_seg(context)
        if seg is None:
            self.report({"WARNING"}, "Segmento invalido"); return {"CANCELLED"}
        jf    = _json_file_from_index(self, context)
        idx   = int(self.pose_index)
        fp    = os.path.join(bpy.path.abspath(st.poses_dir), jf)
        poses = load_json_poses(fp)
        name  = poses[idx].get("label", "?") if poses and idx < len(poses) else "?"
        if self.rot_x == 0.0 and self.rot_y == 0.0 and self.rot_z == 0.0:
            rec = get_pose_record(st.poses_dir, jf, idx)
            if rec:
                rx, ry, rz = get_root_rotation_from_record(rec)
                self.rot_x = rx; self.rot_y = ry; self.rot_z = rz
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
# segmento). Portado de alfred_animation_studio (ALFREDSEG_OT_QuickPoseExtract
# / ALFREDSEG_OT_QuickPoseImport). Ciclo de 2 clicks:
#   1) Guardar   -> detecta el armature de chicken_1 automaticamente
#                   (_find_ch1_armature), nombra la pose sola segun que
#                   huesos se movieron respecto al rest pose, y la guarda
#                   como .json en la carpeta de poses (mismo formato
#                   {"poses": [...]} que usa el resto del addon).
#   2) Importar  -> agrega esa pose recien guardada a seg.action_poses de
#                   ESTE segmento (mismo criterio que
#                   CH1SEG_OT_AddActionPoseSeg.execute) y limpia el
#                   "pendiente" (scene.ch1st.quickpose_pending_*) para el
#                   siguiente ciclo.
# =============================================================================

def _ch1_quickpose_generate_label(armature, max_bones=3):
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


def _find_ch1_armature(context):
    """
    Resuelve el armature de chicken_1 de forma fiable:
      1) Usa el mismo resolver que CONCATENAR (_resolve_armature), basado en
         scene.ch1_segs.armature_name — la fuente de verdad configurada por
         el usuario en el panel de Segmentos.
      2) Si eso falla, intenta con scene.ch1st.armature_name (Paso 1/2).
      3) Como ultimo recurso, busca por nombre "chicken" en la escena (puede
         ser ambiguo si hay armatures secundarios/objetos lanzados con ese
         texto en el nombre, asi que es solo un fallback).
    """
    scene   = context.scene
    seg_cfg = getattr(scene, "ch1_segs", None)
    if seg_cfg is not None:
        arm_obj = _resolve_armature(seg_cfg, scene)
        if arm_obj is not None:
            return arm_obj

    st = getattr(scene, "ch1st", None)
    if st is not None and getattr(st, "armature_name", ""):
        arm_obj = scene.objects.get(st.armature_name)
        if arm_obj and arm_obj.type == "ARMATURE":
            return arm_obj

    arm_obj = None
    for ob in context.scene.objects:
        if ob.type == "ARMATURE" and "chicken" in ob.name.lower():
            arm_obj = ob
            break
    if arm_obj is None:
        for ob in context.scene.objects:
            if ob.type == "ARMATURE":
                arm_obj = ob
                break
    return arm_obj


class CH1SEG_OT_QuickPoseExtract(Operator):
    """Captura la pose actual del armature de chicken_1 y la guarda como
    .json, nombrandola sola segun los huesos movidos. Reutilizar con
    'Importar' para agregarla a la lista de poses del segmento."""
    bl_idname    = "ch1seg.quickpose_extract"
    bl_label     = "Guardar pose (bones actuales)"
    bl_description = (
        "Detecta el armature de chicken_1, extrae la pose del frame actual "
        "y la guarda en la carpeta de poses con un nombre automatico "
        "segun los huesos que moviste"
    )
    bl_options   = {"REGISTER", "UNDO"}

    def execute(self, context):
        st       = context.scene.ch1st
        scene    = context.scene
        armature = _find_ch1_armature(context)
        if armature is None or armature.type != "ARMATURE":
            self.report({"ERROR"}, "No se encontro el armature de chicken_1 en la escena")
            return {"CANCELLED"}

        context.view_layer.update()
        frame = scene.frame_current
        label = _ch1_quickpose_generate_label(armature)

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


class CH1SEG_OT_QuickPoseImport(Operator):
    """Importa la pose recien guardada por 'Guardar pose (bones actuales)'
    a la lista de poses de accion de este segmento, y limpia el pendiente."""
    bl_idname    = "ch1seg.quickpose_import"
    bl_label     = "Importar a la lista de poses"
    bl_description = "Agrega la pose recien guardada a la lista de este segmento"
    bl_options   = {"REGISTER", "UNDO"}
    item_idx:    IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        return bool(context.scene.ch1st.quickpose_pending_file)

    def _get_seg(self, context):
        segs = context.scene.ch1_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if 0 <= idx < len(segs.segments):
            return segs.segments[idx]
        return None

    def execute(self, context):
        st  = context.scene.ch1st
        seg = self._get_seg(context)
        if seg is None:
            self.report({"WARNING"}, "Segmento invalido")
            return {"CANCELLED"}
        jf  = st.quickpose_pending_file
        idx = st.quickpose_pending_index
        if not jf:
            self.report({"WARNING"}, "Primero presiona 'Guardar pose (bones actuales)'")
            return {"CANCELLED"}

        # Refrescar la lista de poses (mismo criterio que CH1ST_OT_ImportPose,
        # si existe) para que el nuevo .json quede disponible en los
        # selectores/enums.
        try:
            bpy.ops.ch1st.refresh_poses()
        except RuntimeError:
            pass

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

        seg.action_poses_idx = len(seg.action_poses) - 1

        nombre_importada = item.pose_name
        # Limpiar el pendiente: listo para el siguiente ciclo.
        st.quickpose_pending_file  = ""
        st.quickpose_pending_index = 0
        st.quickpose_pending_label = ""

        self.report({"INFO"},
            f"Pose '{nombre_importada}' importada al segmento '{seg.label}'")
        return {"FINISHED"}


class CH1SEG_OT_EditActionPoseSeg(Operator):
    bl_idname    = "ch1seg.edit_action_pose_seg"
    bl_label     = "Editar pose intermedia del segmento"
    bl_options   = {"REGISTER", "UNDO"}
    item_idx:    IntProperty(default=-1)

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
        segs = context.scene.ch1_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if 0 <= idx < len(segs.segments):
            return segs.segments[idx]
        return None

    def invoke(self, context, event):
        seg = self._get_seg(context)
        if seg and seg.action_poses and 0 <= seg.action_poses_idx < len(seg.action_poses):
            item = seg.action_poses[seg.action_poses_idx]
            self.duration = item.duration; self.rot_x = item.rot_x
            self.rot_y = item.rot_y; self.rot_z = item.rot_z
            self.pos_x = item.pos_x; self.pos_y = item.pos_y; self.pos_z = item.pos_z
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
        _pc = getattr(context.scene, "ch1_path", None)
        _modo_recorrido = _pc is not None and len(_pc.path_points) > 1
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
        if _modo_recorrido:
            box_lock = layout.box()
            box_lock.label(text="Posicion y Rotacion del Root: BLOQUEADAS", icon="LOCKED")
        else:
            box2 = layout.box()
            box2.label(text="Posicion del Root:", icon="OBJECT_ORIGIN")
            row = box2.row(align=True)
            row.prop(self, "pos_x", text="X"); row.prop(self, "pos_y", text="Y"); row.prop(self, "pos_z", text="Z")
            box3 = layout.box()
            box3.label(text="Orientacion del Root:", icon="ORIENTATION_LOCAL")
            col = box3.column(align=True)
            col.prop(self, "rot_x", text="Rot X"); col.prop(self, "rot_y", text="Rot Y"); col.prop(self, "rot_z", text="Rot Z")

    def execute(self, context):
        seg = self._get_seg(context)
        if seg and seg.action_poses and 0 <= seg.action_poses_idx < len(seg.action_poses):
            item = seg.action_poses[seg.action_poses_idx]
            item.duration = self.duration; item.rot_x = self.rot_x
            item.rot_y = self.rot_y; item.rot_z = self.rot_z
            item.pos_x = self.pos_x; item.pos_y = self.pos_y; item.pos_z = self.pos_z
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


class CH1SEG_OT_RemoveActionPoseSeg(Operator):
    bl_idname  = "ch1seg.remove_action_pose_seg"
    bl_label   = "Eliminar pose intermedia del segmento"
    bl_options = {"REGISTER", "UNDO"}
    item_idx:  IntProperty(default=-1)

    def execute(self, context):
        segs = context.scene.ch1_segs
        idx  = self.item_idx if self.item_idx >= 0 else segs.active_index
        if not (0 <= idx < len(segs.segments)): return {"CANCELLED"}
        seg = segs.segments[idx]
        if seg.action_poses and 0 <= seg.action_poses_idx < len(seg.action_poses):
            seg.action_poses.remove(seg.action_poses_idx)
            seg.action_poses_idx = max(0, seg.action_poses_idx - 1)
        return {"FINISHED"}


class CH1SEG_OT_MoveActionPoseSeg(Operator):
    bl_idname  = "ch1seg.move_action_pose_seg"
    bl_label   = "Mover pose intermedia del segmento"
    bl_options = {"REGISTER", "UNDO"}
    item_idx:  IntProperty(default=-1)
    direction: EnumProperty(items=[("UP","Arriba",""),("DOWN","Abajo","")])

    def execute(self, context):
        segs = context.scene.ch1_segs
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

class CH1SEG_OT_ToggleConfig(Operator):
    """Muestra u oculta la configuracion de poses de un segmento."""
    bl_idname  = "ch1seg.toggle_config"
    bl_label   = "Configurar segmento"
    bl_options = {"REGISTER", "UNDO"}
    item_idx:  IntProperty(default=0)

    def execute(self, context):
        segs = context.scene.ch1_segs
        idx  = self.item_idx
        if 0 <= idx < len(segs.segments):
            segs.segments[idx].show_config = not segs.segments[idx].show_config
        return {"FINISHED"}




class CH1SEG_UL_Segments(bpy.types.UIList):
    """UIList para mostrar los slots de accion intermedios de un segmento."""
    bl_idname = "CH1SEG_UL_Segments"

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

seg_operator_classes = (
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
    CH1SEG_OT_ToggleConfig,
    CH1SEG_OT_SetFrameStartEdit,
    CH1SEG_UL_Segments,
)
