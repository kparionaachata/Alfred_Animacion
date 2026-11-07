# -*- coding: utf-8 -*-
"""
operators_anim.py — Cerdo_1 Animation Studio v1.8
Operadores principales: Organic filters, CONCATENAR, ExportAnimation,
ImportAnimation, ExtractPose.
"""
import bpy, json, os, math, random
from datetime import datetime
from bpy.types import Operator
from bpy.props import StringProperty
from .blender_compat import get_fcurves
from mathutils import Euler, Vector
from .constants import BONES_LISTA, BONES_LISTA_FULL, _BONE_DEFAULT, EYE_BASE_TRANSFORMS
from .interpolation import apply_interp
from .pose_utils import (
    load_json_poses, get_pose_record, pose_record_to_full_dict,
    _lerp, build_segment_frames, get_root_transform_from_record,
    resolve_pose_start_frames,
)
from .properties import load_historia_json, get_key_points, ensure_eye_shapekey_migrated
from .pose_utils import get_orientacion_inicial
from .eye_system import apply_blink_sequence, apply_laugh_sequence, apply_understand_sequence, apply_expression_to_eye
from .constants import EYE_MESH_NAMES
from . import object_import_utils as _oiu_preview
from .operators_segments import _find_cerdo_1_armature

# ─── Helpers de ojos para CONCATENAR ────────────────────────────────────────

def _apply_eye_transforms_from_props(scene, eye_s):
    """Aplica posicion/rotacion/escala de las propiedades del panel a las mallas de ojos."""
    import math as _math
    mapping = {
        "ojo_izquierdo_cerdo_1": {
            "loc": (eye_s.eye_L_loc_x, eye_s.eye_L_loc_y, eye_s.eye_L_loc_z),
            "rot": (eye_s.eye_L_rot_x, eye_s.eye_L_rot_y, eye_s.eye_L_rot_z),
            "sca": (eye_s.eye_L_sca_x, eye_s.eye_L_sca_y, eye_s.eye_L_sca_z),
        },
        "ojo_derecho_cerdo_1": {
            "loc": (eye_s.eye_R_loc_x, eye_s.eye_R_loc_y, eye_s.eye_R_loc_z),
            "rot": (eye_s.eye_R_rot_x, eye_s.eye_R_rot_y, eye_s.eye_R_rot_z),
            "sca": (eye_s.eye_R_sca_x, eye_s.eye_R_sca_y, eye_s.eye_R_sca_z),
        },
    }
    for obj_name, td in mapping.items():
        obj = scene.objects.get(obj_name)
        if not obj:
            continue
        obj.location       = td["loc"]
        obj.rotation_euler = td["rot"]   # subtype=ANGLE => ya en radianes
        obj.scale          = td["sca"]
        obj.keyframe_insert(data_path="location",       frame=scene.frame_current)
        obj.keyframe_insert(data_path="rotation_euler", frame=scene.frame_current)
        obj.keyframe_insert(data_path="scale",          frame=scene.frame_current)


def _apply_eye_expression_keyframe(scene, eye_s, start_frame, end_frame):
    """Inserta keyframes de shape key de expresion segun la configuracion del panel."""
    expr  = eye_s.active_expression
    val   = eye_s.expression_value
    frame = eye_s.lib_frame_start

    # Solo insertar si el frame esta dentro del rango generado
    if frame < start_frame or frame > end_frame:
        frame = start_frame

    for name in EYE_MESH_NAMES:
        obj = scene.objects.get(name)
        if obj:
            apply_expression_to_eye(obj, expr, val, frame)

# =============================================================================
# FILTROS DE MOVIMIENTO ORGANICO  (post-proceso sobre fcurves)
# =============================================================================

def _noise_at(frame, freq, seed, dim=0):
    """Ruido procesal deterministico (sin-hash sin bpy.app.driver_namespace)."""
    v = math.sin(frame * freq * 1.3 + seed * 7.3 + dim * 3.7)
    v += math.sin(frame * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5
    v += math.sin(frame * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25
    return v / 1.75   # rango aprox. [-1, 1]

def _gaussian_smooth(values, factor):
    """Suavizado gaussiano de una lista de valores con factor [0,1]."""
    n = len(values)
    if n < 3:
        return values[:]
    out = values[:]
    w   = [0.25, 0.5, 0.25]
    for i in range(1, n - 1):
        out[i] = values[i - 1] * w[0] + values[i] * w[1] + values[i + 1] * w[2]
        out[i] = values[i] * (1 - factor) + out[i] * factor
    return out

def _apply_organic_filters(context, armature, start_frame, end_frame, org,
                            base_overrides=None, target_action=None,
                            target_action_root=None):
    """
    Aplica filtros organicos sobre las fcurves ya generadas.
    Lee los valores de los keyframes existentes, les suma las micro-variaciones
    y escribe los valores modificados de vuelta a los mismos keyframes.

    target_action / target_action_root: AISLAMIENTO REAL (Kebyn, 2026-08-05:
    "no deberia afectarle lo que pase en el segmento 2 -- falta un
    verdadero aislamiento entre segmentos"). Si se pasan, los filtros leen
    y escriben SIEMPRE sobre estas actions ya construidas (target_action
    para el armature, target_action_root para el root "cerdo_1") -- nunca
    sobre armature.animation_data.action / root.animation_data.action en
    vivo, y nunca vuelven a leer pose.bones. Con esto el resultado de un
    segmento depende UNICAMENTE de los datos ya presentes en su propia
    action (tipicamente una copia aislada de la Capa 1 de respaldo, ver
    _copy_action_range en operators_segments.py), sin importar el orden en
    que se procesen los demas segmentos, el playhead de la escena, ni el
    estado del stack NLA. base_overrides queda como fallback legado (solo
    se usa si la fcurve destino no tiene NINGUN keyframe propio todavia,
    ni siquiera fuera de rango).
    """
    scene = context.scene
    frames = list(range(start_frame, end_frame + 1))
    n = len(frames)
    if n < 3:
        return

    _arm_action = target_action
    if _arm_action is None and armature.animation_data:
        _arm_action = armature.animation_data.action

    # ── FILTRO: suavizado de fcurves ──
    if org.smooth_curves_enabled and _arm_action:
        for fc in get_fcurves(_arm_action):
            kps = sorted(fc.keyframe_points, key=lambda k: k.co.x)
            vals = [k.co.y for k in kps]
            for _ in range(org.smooth_passes):
                vals = _gaussian_smooth(vals, org.smooth_factor)
            for k, v in zip(kps, vals):
                k.co.y = v
            fc.update()

    # BUGFIX (Kebyn, 2026-08-03, quater: "los filtros estan activados pero
    # no se reproducen despues de concatenar los segmentos" -- confirmado
    # con segmentos SIN poses / "transicion directa", ej. 02_parada):
    #
    # Las tres funciones de abajo hacian "if fc is None: return" -- es
    # decir, si el bone (Body:Bend_cerdo_1, Head_cerdo_1, Head_cerdo_1, etc.) no
    # tenia TODAVIA un fcurve propio en esa action, el filtro no hacia
    # nada, en silencio. Fix: si el fcurve no existe, crearlo.
    #
    # BUGFIX (Kebyn, 2026-08-05, "aislamiento real"): el base_val para
    # frames sin keyframe propio YA NO se lee de pb.rotation_euler en
    # vivo (esa lectura es la que se contaminaba con el stack NLA de
    # otros segmentos ya concatenados -- de ahi el bug original de
    # Head_cerdo_1 saltando a -190/-241/182 grados). Ahora se evalua
    # fc.evaluate(f) sobre la MISMA fcurve destino: como esa fcurve, para
    # segmentos sin pose, es una copia directa del respaldo de Capa 1 ya
    # recortada a este rango (ver _copy_action_range), evaluarla da el
    # valor real interpolado de la Capa 1 en ese frame exacto -- sin
    # tocar el objeto, el playhead, ni ningun otro segmento.
    def _get_or_create_fc(dp, axis):
        action = target_action
        if action is None:
            if not armature.animation_data:
                armature.animation_data_create()
            if not armature.animation_data.action:
                armature.animation_data.action = bpy.data.actions.new(
                    f"{armature.name}_organic")
            action = armature.animation_data.action
        fc = get_fcurves(action).find(dp, index=axis)
        if fc is None:
            fc = get_fcurves(action).new(dp, index=axis)
        return fc

    def _mod_bone_generic(bone_name, channel, axis, deltas, base_default):
        """Suma deltas[frame_idx] al canal (rotation_euler/location/scale)
        del bone, insertando keyframes nuevos donde todavia no existan.
        El valor base para esos frames nuevos se toma SIEMPRE de la propia
        fcurve (interpolando lo que ya haya en ella) -- nunca del estado
        en vivo del armature."""
        dp = f'pose.bones["{bone_name}"].{channel}'
        fc = _get_or_create_fc(dp, axis)
        kps  = sorted(fc.keyframe_points, key=lambda k: k.co.x)
        kmap = {int(k.co.x): k for k in kps if start_frame <= int(k.co.x) <= end_frame}
        _has_curve_data = len(kps) > 0
        for i, f in enumerate(frames):
            if f in kmap:
                kmap[f].co.y += deltas[i]
            else:
                if _has_curve_data:
                    base_val = fc.evaluate(f)
                else:
                    _override = base_overrides.get((bone_name, channel)) if base_overrides else None
                    base_val = _override[axis] if _override is not None else base_default
                new_kp = fc.keyframe_points.insert(f, base_val + deltas[i])
                new_kp.interpolation = "BEZIER"
                new_kp.easing        = "AUTO"
                kmap[f] = new_kp
        fc.update()

    def _mod_bone_rot(bone_name, axis, deltas):
        _mod_bone_generic(bone_name, "rotation_euler", axis, deltas, 0.0)

    def _mod_bone_loc(bone_name, axis, deltas):
        _mod_bone_generic(bone_name, "location", axis, deltas, 0.0)

    def _mod_bone_scale(bone_name, axis, deltas):
        _mod_bone_generic(bone_name, "scale", axis, deltas, 1.0)

    # ── FILTRO: respiracion ──
    if org.breathing_enabled:
        amp   = org.breathing_amplitude
        speed = org.breathing_speed
        phase = org.breathing_phase
        deltas_x = [amp * math.sin(f * speed * 2 * math.pi + phase) for f in frames]
        deltas_z = [amp * 0.4 * math.sin(f * speed * 2 * math.pi + phase + 1.2) for f in frames]
        for bone in ("Body:Bend_cerdo_1", "Body:Bend_cerdo_1"):
            _mod_bone_rot(bone, 0, deltas_x)   # X
            _mod_bone_rot(bone, 2, deltas_z)   # Z

    # ── FILTRO: micro-movimiento de cabeza ──
    if org.head_sway_enabled:
        amp   = org.head_sway_amplitude
        speed = org.head_sway_speed
        seed  = org.head_sway_seed
        for axis in range(3):
            deltas = [amp * _noise_at(f, speed, seed, axis) for f in frames]
            for bone in ("Head_cerdo_1", "Head_cerdo_1"):
                _mod_bone_rot(bone, axis, deltas)

    # ── FILTRO: desplazamiento de peso (hips lateral) ──
    if org.weight_shift_enabled:
        amp   = org.weight_shift_amplitude
        speed = org.weight_shift_speed
        deltas_loc_x = [amp * math.sin(f * speed * 2 * math.pi) for f in frames]
        deltas_rot_z = [amp * 0.8 * math.cos(f * speed * 2 * math.pi) for f in frames]
        _mod_bone_loc("Body_cerdo_1", 0, deltas_loc_x)
        _mod_bone_rot("Body_cerdo_1", 2, deltas_rot_z)

    # ── FILTRO: noise en hombros ──
    if org.shoulder_noise_enabled:
        amp   = org.shoulder_noise_amplitude
        speed = org.shoulder_noise_speed
        seed  = org.shoulder_noise_seed
        for axis in range(3):
            for bone, s_off in (("Leg:FR_cerdo_1", 0), ("Leg:FL_cerdo_1", 17)):
                deltas = [amp * _noise_at(f, speed, seed + s_off, axis) for f in frames]
                _mod_bone_rot(bone, axis, deltas)

    # ── FILTRO: micro-escala organica ──
    if org.micro_scale_enabled:
        amp   = org.micro_scale_amplitude
        speed = org.breathing_speed  # sincronizado con respiracion
        phase = org.breathing_phase
        deltas_s = [amp * math.sin(f * speed * 2 * math.pi + phase) for f in frames]
        _mod_bone_scale("Body:Bend_cerdo_1", 2, deltas_s)   # escala Z del Spine1

    # ── FILTRO: secondary motion brazos (retardo de codos) ──
    if org.secondary_motion_enabled:
        lag     = int(round(org.secondary_motion_lag))
        damping = org.secondary_motion_damping
        if _arm_action:
            action = _arm_action
            for bone in ("Leg:FR:Bend_cerdo_1", "Leg:FL:Bend_cerdo_1"):
                dp = f'pose.bones["{bone}"].rotation_euler'
                for axis in range(3):
                    fc = get_fcurves(action).find(dp, index=axis)
                    if fc is None:
                        continue
                    kps  = sorted(fc.keyframe_points, key=lambda k: k.co.x)
                    kmap = {int(k.co.x): k for k in kps}
                    vals = [kmap[f].co.y if f in kmap else 0.0 for f in frames]
                    # Aplicar retardo: el elbow sigue al UpArm con lag frames de retraso
                    delayed = [0.0] * n
                    for i in range(n):
                        src_i = max(0, i - lag)
                        delayed[i] = vals[src_i] * (1 - damping) + vals[i] * damping
                    # Blend: 30% delayed + 70% original para no romper la pose base
                    for i, f in enumerate(frames):
                        if f in kmap:
                            kmap[f].co.y = vals[i] * 0.7 + delayed[i] * 0.3
                    fc.update()

    # ── FILTRO: noise en posicion del root ──
    if org.root_noise_enabled:
        root_obj = scene.objects.get("cerdo_1")
        root_action = target_action_root
        if root_action is None and root_obj and root_obj.animation_data:
            root_action = root_obj.animation_data.action
        if root_action:
            strength = org.root_noise_strength
            freq     = org.root_noise_frequency
            seed     = org.root_noise_seed
            for axis in range(3):
                fc = get_fcurves(root_action).find("location", index=axis)
                if fc is None:
                    continue
                kps  = sorted(fc.keyframe_points, key=lambda k: k.co.x)
                kmap = {int(k.co.x): k for k in kps}
                for i, f in enumerate(frames):
                    if f in kmap:
                        kmap[f].co.y += strength * _noise_at(f, freq, seed, axis)
                fc.update()


# =============================================================================
# CONCATENAR (incluye pos XYZ root + filtros organicos)
# =============================================================================

# Custom property con la que se etiqueta, en el propio bpy.types.Object
# importado, el uid del Cerdo_1ThrowItem "dueño" de ese objeto. Ver
# _sweep_orphan_throw_objects() y Cerdo_1ThrowItem.uid (properties.py).
_THROW_UID_TAG = "_cerdo_1_throw_uid"


def _new_throw_uid():
    """Genera un uid corto y estable para un Cerdo_1ThrowItem nuevo."""
    import uuid
    return uuid.uuid4().hex[:12]


def _sweep_orphan_throw_objects(context):
    """
    BUGFIX (Kebyn + Claude, 2026-09-01 ter): borra de bpy.data cualquier
    objeto etiquetado como "importado por el sistema Lanzar/Recoger/
    Mantener" (via _THROW_UID_TAG) cuyo item YA NO EXISTE en ningun
    segmento -- tipicamente porque el usuario lo elimino con el boton de
    basurero del panel (CERDO_1_ST_OT_ThrowRemoveItem) despues de haberlo
    concatenado al menos una vez. Sin este barrido, ese objeto quedaba
    huerfano en la escena para siempre: al elegir despues un objeto
    DISTINTO en un item nuevo (mismo u otro segmento), el huerfano viejo
    seguia ahi, y con cada "Concatenar segmentos" se iban acumulando mas
    (ademas de forzar renombrados ".001", ".002" en el objeto nuevo si
    compartia nombre base con el huerfano).

    Se llama UNA SOLA VEZ al principio de run_throws_for_segments(), y
    barre TODA la escena (no solo seg_range) -- si el item fue eliminado,
    ya no aparece en NINGUN segmento, sin importar cual se este
    concatenando en este momento.
    """
    try:
        segs = context.scene.cerdo_1_segs.segments
    except Exception:
        return
    _valid_uids = set()
    for _seg in segs:
        for _item in _seg.throws.items:
            if _item.uid:
                _valid_uids.add(_item.uid)

    for _obj in list(bpy.data.objects):
        _tag = _obj.get(_THROW_UID_TAG)
        if _tag is None:
            continue
        if _tag in _valid_uids:
            continue
        print(f"[THROW] Barrido de huerfanos: borrando '{_obj.name}' "
              f"(su item de Lanzar/Recoger/Mantener ya no existe)")
        _old_mesh = _obj.data
        try:
            bpy.data.objects.remove(_obj, do_unlink=True)
        except Exception as _e_sweep:
            print(f"[THROW] No se pudo borrar huerfano '{_obj.name}': {_e_sweep}")
            continue
        if _old_mesh is not None and getattr(_old_mesh, "users", 1) == 0:
            try:
                bpy.data.meshes.remove(_old_mesh)
            except Exception:
                pass


# ============================================================
# GESTO "BRAZO DERECHO HACIA LA ESPALDA" -- animacion de 3 pasos que
# se ejecuta SIEMPRE antes de Lanzar/Recoger/Mantener un objeto (Kebyn,
# 2026-09-01: pedido explicito, pose de referencia
# brazo_derecho__hacia_la_espalda.json, frame 21, personaje cerdo_1).
#
# Valores extraidos de ese JSON (local_space, rotation_mode XYZ) para
# los 2 bones que definen el gesto -- Leg:FR_cerdo_1 (hombro) y
# Leg:FR:Bend_cerdo_1 (codo). Se embeben como constantes (mismo patron
# que KEYFRAMES_SALTAR_SUBIR/arrodillarse_1 en generate_slots_cerdo_1.py)
# en vez de leer el .json en vivo, para no depender de una ruta de
# archivo que Kebyn tendria que copiar dentro del proyecto.
# ============================================================
PRE_THROW_REACH_BACK_BONES = ('Leg:FR_cerdo_1', 'Leg:FR:Bend_cerdo_1')

PRE_THROW_REACH_BACK_POSE = {
    'Leg:FR_cerdo_1': {
        'loc':     (0.006603, 0.096746, -0.086079),
        'rot_deg': (28.5284, 198.1061, 62.0369),
    },
    'Leg:FR:Bend_cerdo_1': {
        'loc':     (1e-05, -2e-06, 1.2e-05),
        'rot_deg': (-16.873, 18.6165, -107.9791),
    },
}

# `duration` representa el TOTAL de frames que ocupa el gesto completo
# (ida + vuelta), no cada tramo por separado -- ver bugfix 2026-09-11
# mas abajo.
PRE_THROW_REACH_BACK_DURATION = 8


def _keyframe_pose_bone_transform(pb, frame, rot_euler, loc):
    """Fija rotation_euler/location de un pose bone y clava un keyframe
    de ambos canales en `frame`. Usado por apply_pre_throw_reach_back()."""
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = rot_euler
    pb.location = loc
    pb.keyframe_insert(data_path="rotation_euler", frame=frame)
    pb.keyframe_insert(data_path="location", frame=frame)


def apply_pre_throw_reach_back(armature, anchor_frame,
                                duration=PRE_THROW_REACH_BACK_DURATION,
                                direction='AFTER'):
    """
    Anima el gesto "brazo derecho hacia la espalda" en Leg:FR_cerdo_1
    y Leg:FR:Bend_cerdo_1, en 3 pasos:

        1. frame_ini: pose por defecto -- se CAPTURA el valor que el bone
           ya tuviera animado ahi (rotation_euler + location tal como
           esten en ese momento), nunca se fuerza a rest/(0,0,0).
        2. frame_mid: pose "brazo hacia la espalda" (PRE_THROW_REACH_BACK_POSE).
        3. frame_fin: de vuelta al mismo valor capturado en el paso 1.

    BUGFIX (Kebyn + Claude, 2026-09-11 ter: "el arma debe aparecer justo
    cuando la mano llega a la espalda, no al final del gesto"): con
    direction='AFTER' (gesto de ENTRADA), `duration` ya NO es el total
    ida+vuelta -- es la mitad: cuantos frames tarda el brazo en llegar
    desde la pose por defecto (frame_ini = anchor_frame) hasta la pose
    "hacia la espalda" (frame_mid = anchor_frame + duration). El objeto
    debe aparecer EXACTO en frame_mid (el caller usa el segundo valor
    del retorno para eso), no cuando el brazo ya volvio a su pose normal.
    La vuelta a la pose por defecto (frame_fin = frame_mid + duration)
    tarda lo mismo que la ida, y sigue ocurriendo con el objeto ya
    visible en la mano.

    BUGFIX (Kebyn + Claude, 2026-09-11 cuater: "lo mismo se aplica al
    guardar -- el arma debe desaparecer cuando el brazo llega a la
    espalda, no cuando ya volvio a la normalidad"): con
    direction='BEFORE' (gesto de SALIDA/"guardar") pasa lo mismo, en
    espejo: `duration` tambien es la mitad -- cuantos frames antes de
    `anchor_frame` (item.frame_end, frame_fin) el brazo llega a la pose
    "hacia la espalda" (frame_mid = anchor_frame - duration). El objeto
    debe desaparecer EXACTO en frame_mid (mano ya en la espalda,
    guardando el objeto), no en frame_fin (que es cuando el brazo ya
    volvio a la normalidad, con el objeto ya guardado hace rato). El
    gesto arranca (pose por defecto) en frame_fin - 2*duration.

    En ambos casos el gesto siempre queda contenido DENTRO del rango
    propio del item (entre frame_start y frame_end), nunca invade el
    item anterior ni el siguiente.

    Retorna (aplicado: bool, frame_mid: int, frame_fin: int):
        - frame_mid: frame en el que el brazo llega a la pose "hacia la
          espalda" -- este es el frame correcto para mostrar el objeto
          (direction='AFTER') u ocultarlo (direction='BEFORE').
        - frame_fin: frame en el que el gesto completo termina (brazo
          de vuelta a la pose por defecto).

    Si no hay espacio suficiente (item muy cerca del frame 1), la
    duracion se comprime proporcionalmente en vez de generar keyframes
    en frames negativos/cero.
    """
    if armature is None or armature.type != 'ARMATURE' or not armature.pose:
        return False, anchor_frame, anchor_frame

    if direction == 'AFTER':
        half = max(1, int(duration))
        f_default = max(1, int(anchor_frame))
        f_action  = f_default + half
        end_frame = f_action + half
    else:  # 'BEFORE' -- gesto de "guardar": tambien mitad ida / mitad vuelta,
           # pero calculado hacia atras desde anchor_frame (item.frame_end)
        half = max(1, int(duration))
        end_frame = anchor_frame
        f_action  = end_frame - half
        f_default = f_action - half
        if f_default < 1:
            half = max(1, (end_frame - 1) // 2)
            f_action  = end_frame - half
            f_default = f_action - half

    if not armature.animation_data:
        armature.animation_data_create()

    # BUGFIX (Kebyn + Claude, 2026-09-11 quinquies: "el gesto de guardar
    # (antes de Fin) no se reproduce en Mantener cuando Inicio/Fin cubren
    # un rango largo"): antes, esta funcion solo aislaba el gesto en su
    # PROPIA pista NLA (con el rango LOCAL del gesto, no el del segmento)
    # cuando el armature NO tenia ninguna action activa al llamarla
    # (`_needs_own_nla_push`, senal de la rama "sin poses" de Concatenar
    # segmentos). En la rama "con poses" (CERDO_1_ST_OT_Concatenate) eso nunca
    # se disparaba: el gesto se horneaba directo sobre la action EN VIVO
    # del segmento contenedor del item (el que contiene item.frame_start),
    # y esa action se aisla despues a su propia pista NLA acotada a
    # [seg.frame_start, seg.frame_end). Para un item de "Mantener" con
    # Inicio/Fin largo (ej. 641->1000), el gesto de ENTRADA (cerca de
    # Inicio) suele caer dentro de ese rango y se ve bien, pero el gesto
    # de GUARDADO ("Repetir en espejo antes de Fin", direction='BEFORE',
    # cerca de Fin=1000) casi siempre cae MUY lejos del rango del
    # segmento contenedor -- al aislarse esa action a su pista NLA
    # acotada (extrapolation='NOTHING'), esos keyframes del gesto de
    # guardado quedaban fuera del strip y se descartaban: el gesto
    # simplemente no se reproducia.
    #
    # Fix: el gesto AHORA SIEMPRE se hornea en una action propia y
    # temporal (nunca sobre la action que este activa en el armature),
    # y se empuja a su PROPIA pista NLA aislada con el rango LOCAL real
    # del gesto (f_default->end_frame), sin importar que rama lo llamo
    # ni cuan lejos este del rango del segmento contenedor. La action
    # que estuviera activa antes de llamar a esta funcion (si la habia,
    # ej. la del segmento en construccion en la rama "con poses") se
    # restaura tal cual al terminar, intacta.
    _orig_action = armature.animation_data.action
    _gesture_action = bpy.data.actions.new(
        name=f"{armature.name}_reach_back_{end_frame}")
    armature.animation_data.action = _gesture_action

    aplicado = False
    for bone_name in PRE_THROW_REACH_BACK_BONES:
        pb = armature.pose.bones.get(bone_name)
        if pb is None:
            continue
        pose_data = PRE_THROW_REACH_BACK_POSE.get(bone_name)
        if pose_data is None:
            continue

        # Paso 1: capturar pose por defecto vigente en f_default.
        default_rot = tuple(pb.rotation_euler)
        default_loc = tuple(pb.location)
        _keyframe_pose_bone_transform(pb, f_default, default_rot, default_loc)

        # Paso 2: pose "hacia la espalda".
        action_rot = tuple(math.radians(v) for v in pose_data['rot_deg'])
        action_loc = pose_data['loc']
        _keyframe_pose_bone_transform(pb, f_action, action_rot, action_loc)

        # Paso 3: de vuelta a la pose por defecto del paso 1.
        _keyframe_pose_bone_transform(pb, end_frame, default_rot, default_loc)
        aplicado = True

    if aplicado and get_fcurves(_gesture_action):
        track = armature.animation_data.nla_tracks.new()
        track.name = f"ALFTHROW_reach_{end_frame}"
        strip = track.strips.new(track.name, int(f_default), _gesture_action)
        strip.use_sync_length    = False
        strip.action_frame_start = f_default
        strip.action_frame_end   = end_frame
        strip.frame_start        = f_default
        strip.frame_end          = end_frame
        strip.extrapolation      = 'NOTHING'
        strip.blend_type         = 'REPLACE'
    else:
        # No se encontro ninguno de los 2 bones (rig distinto/faltante)
        # -- no dejar la action vacia colgando.
        bpy.data.actions.remove(_gesture_action)

    # Restaurar la action que estuviera activa antes de llamar a esta
    # funcion (la del segmento en construccion, si la habia -- rama "con
    # poses" -- o None -- rama "sin poses", ya aislada previamente).
    armature.animation_data.action = _orig_action

    return aplicado, f_action, end_frame


def run_throws_for_segments(context, seg_range):
    """Ejecuta el sistema de Lanzar / Recoger / Mantener Objetos (seg.throws)
    para cada segmento en seg_range. Extraido de CERDO_1_ST_OT_Concatenate.execute()
    (2026-09-01) para poder reutilizarlo tambien desde
    CERDO_1SEG_OT_ConcatenateAll (operators_segments.py) en la rama de
    segmentos SIN poses -- esa rama nunca llama a bpy.ops.cerdo_1_st.concatenate(),
    asi que el sistema de throws (a diferencia de parpadeo/Reir/Entendiendo/
    expresiones, ya replicados ahi) nunca se ejecutaba para un segmento sin
    poses con un item de Lanzar/Recoger/Mantener configurado -- el .blend
    elegido en la interfaz jamas se importaba al concatenar.

    BUGFIX (Kebyn + Claude, 2026-09-01 bis: "aun sin poses debe importar
    los objetos .blend segun como los configure para cada segmento"):
    ademas del fix anterior, cada item (salvo bloques_dinamicos, que ya
    reimportaba siempre) ahora SIEMPRE borra el objeto de una corrida
    anterior (via item.imported_object_name) y reimporta de cero, en vez
    de reutilizar silenciosamente lo que hubiera en bpy.data bajo
    item.target_object -- ese `target_object` puede quedar apuntando a un
    objeto de una sesion/maquina anterior (viene del JSON) o a un objeto
    ya desvinculado de la escena, y reusarlo saltaba el reparenteo, el
    offset y el reseteo de keyframes de visibilidad, dejando el objeto
    "importado" pero invisible o mal ubicado. Con esto, el resultado
    depende unicamente de la configuracion ACTUAL del item en cada corrida.

    Retorna (throw_imported, throw_applied, throw_errors).
    """
    st = context.scene.cerdo_1_st
    _throw_imported = 0
    _throw_applied  = 0
    _throw_errors   = []
    _sweep_orphan_throw_objects(context)

    # BUGFIX (Kebyn + Claude, 2026-09-11 quater: "el hacha aparece en el
    # segmento equivocado / el gesto de brazo se descarta al aislar via
    # NLA"): el panel global de Lanzar/Recoger/Mantener (box_global_throw
    # en panels.py) guarda TODOS los items en segments[0].throws.items sin
    # importar el Inicio/Fin que el usuario configure para cada uno -- ese
    # "contenedor" es solo un detalle interno de almacenamiento, nunca se
    # expuso como eleccion real de segmento en la interfaz (ver comentario
    # ahi: "Internamente sigue usando el primer segmento como contenedor").
    #
    # Antes, este bucle hacia `th = seg.throws` por cada seg en seg_range,
    # asi que un item SOLO se procesaba durante el turno de SU SEGMENTO
    # CONTENEDOR (siempre el Segmento 0) -- sin importar que
    # item.frame_start/frame_end (lo que el usuario si eligio a mano, ej.
    # 641->1000) cayera fisicamente dentro de un segmento distinto de la
    # lista de 14. El gesto de brazo y la aparicion/desaparicion del
    # objeto terminaban horneados sobre la action temporal del Segmento 0
    # y se descartaban al aislarse en su propia pista NLA (acotada a
    # [start_frame, end_frame] del Segmento 0, extrapolation='NOTHING').
    #
    # Fix: se ignora por completo en que contenedor vive cada item. Se
    # junta la union de TODOS los .throws.items de TODOS los segmentos de
    # la escena (sin duplicar, por uid), y cada item se procesa UNA SOLA
    # VEZ -- durante el turno del segmento de seg_range cuyo rango
    # [frame_start, frame_end) realmente contiene item.frame_start, que es
    # el dato que el usuario configuro a mano y el que importa para
    # decidir en que momento del loop de "Concatenar segmentos" debe
    # aplicarse el gesto/import/visibilidad.
    _all_segs_throw = list(context.scene.cerdo_1_segs.segments)

    def _target_seg_for_throw_item(_it):
        for _s in _all_segs_throw:
            if _s.frame_start <= _it.frame_start < _s.frame_end:
                return _s
        # Ningun segmento contiene ese frame_start (ej. coincide justo con
        # el frame_end del ultimo segmento activo, o quedo fuera de rango
        # tras editar los segmentos) -- usar el que termine mas cerca.
        _candidates = [s for s in _all_segs_throw if s.frame_end >= _it.frame_start]
        if _candidates:
            return min(_candidates, key=lambda s: abs(s.frame_start - _it.frame_start))
        return _all_segs_throw[0] if _all_segs_throw else None

    _seg_range_ids_throw = {id(s) for s in seg_range}
    _seen_throw_uids = set()

    try:
        for _source_seg in _all_segs_throw:
            th = _source_seg.throws
            if not th.enabled:
                continue
            for item in th.items:
                if not item.uid:
                    # Item creado antes de este fix (o restaurado desde un
                    # JSON viejo sin "uid") -- se le asigna uno recien
                    # ahora, asi el barrido de huerfanos y el etiquetado de
                    # abajo pueden identificarlo de forma estable de aqui
                    # en adelante.
                    item.uid = _new_throw_uid()
                if item.uid in _seen_throw_uids:
                    # Ya se encontro este mismo item bajo otro contenedor
                    # (no deberia pasar en el uso normal -- todos viven en
                    # el mismo segmento[0] -- pero evita procesarlo dos
                    # veces si alguna vez quedan duplicados fisicos).
                    continue
                _seen_throw_uids.add(item.uid)
                if not item.enabled:
                    print(f"[THROW]   '{item.label}' -> SALTADO (item.enabled=False)")
                    continue

                seg = _target_seg_for_throw_item(item)
                if seg is None or id(seg) not in _seg_range_ids_throw:
                    # Este item le corresponde a un segmento que no es el
                    # que le toca el turno en esta pasada del loop de
                    # "Concatenar segmentos" -- se procesara cuando le
                    # toque el turno a SU segmento real.
                    continue
                print(f"[THROW]   '{item.label}' -> segmento real "
                      f"'{seg.label}' (frames {item.frame_start}->"
                      f"{item.frame_end}), contenedor original "
                      f"'{_source_seg.label}'")

                # Gesto "brazo derecho hacia la espalda" -- SIEMPRE antes
                # de lanzar/recoger/mantener un objeto (Kebyn, 2026-09-01).
                # Se ejecuta para los 3 modos (THROW/CATCH/HOLD).
                #
                # BUGFIX (Kebyn + Claude, 2026-09-11 ter: "el arma debe
                # aparecer justo cuando la mano llega a la espalda, no al
                # final del gesto"): el gesto de ENTRADA arranca en
                # item.frame_start (direction='AFTER') y el objeto aparece
                # en `_appear_frame` -- ahora el frame INTERMEDIO en el que
                # la mano llega a la pose "hacia la espalda"
                # (item.frame_start + duracion configurada), NO el frame
                # final del gesto completo (que es cuando el brazo ya
                # volvio a su pose normal, con el objeto ya en la mano).
                # Un fallo aca (o no encontrar el armature) no debe
                # bloquear la importacion del objeto en si; en ese caso
                # aparece en frame_start como antes (sin gesto que esperar).
                _appear_frame = item.frame_start
                try:
                    _reach_arm = (context.scene.objects.get(st.armature_name)
                                  if st.armature_name else None)
                    _dur_in = getattr(item, 'reach_back_duration_in',
                                       PRE_THROW_REACH_BACK_DURATION)
                    _gesto_ok, _gesto_mid, _gesto_fin = apply_pre_throw_reach_back(
                        _reach_arm, item.frame_start,
                        duration=_dur_in, direction='AFTER')
                    if _gesto_ok:
                        # Nunca dejar que el gesto empuje al objeto a
                        # aparecer despues de frame_end (item muy corto).
                        _appear_frame = min(_gesto_mid, max(item.frame_start,
                                                             item.frame_end - 1))
                        print(f"[THROW]   Gesto 'brazo hacia la espalda' "
                              f"aplicado desde frame {item.frame_start} "
                              f"(mano llega a la espalda en {_gesto_mid}, "
                              f"vuelta a normal en {_gesto_fin}) -- "
                              f"'{item.label}' aparecera en frame {_appear_frame}")
                except Exception as _e_reach:
                    print(f"[THROW]   No se pudo aplicar el gesto previo "
                          f"para '{item.label}': {_e_reach}")

                # BUGFIX/FEATURE (2026-09-01, actualizado 2026-09-11 cuater):
                # mismo gesto, en espejo, ANTES de que termine item.frame_end
                # -- simula que el personaje "guarda" el objeto (arco
                # derecho/codo van hacia la espalda y vuelven). Este rango
                # cae dentro del propio item (entre frame_start y
                # frame_end), asi que nunca invade el item siguiente. Se
                # puede desactivar por item (reach_back_enabled_out) y su
                # duracion es independiente de la del gesto de entrada
                # (reach_back_duration_out).
                #
                # El objeto ahora desaparece en `_disappear_frame` -- el
                # frame INTERMEDIO en el que la mano llega a la pose "hacia
                # la espalda" (guardando el objeto), NO en item.frame_end
                # (que es cuando el brazo ya volvio a la normalidad, con el
                # objeto ya guardado desde antes). Si el gesto esta
                # desactivado o falla, el objeto sigue desapareciendo en
                # item.frame_end como siempre.
                _disappear_frame = item.frame_end
                if getattr(item, 'reach_back_enabled_out', True):
                    try:
                        _reach_arm_out = (context.scene.objects.get(st.armature_name)
                                          if st.armature_name else None)
                        _dur_out = getattr(item, 'reach_back_duration_out',
                                            PRE_THROW_REACH_BACK_DURATION)
                        _gesto_out_ok, _gesto_out_mid, _gesto_out_fin = apply_pre_throw_reach_back(
                            _reach_arm_out, item.frame_end,
                            duration=_dur_out, direction='BEFORE')
                        if _gesto_out_ok:
                            # Nunca dejar que el objeto desaparezca antes de
                            # haber aparecido (item muy corto).
                            _disappear_frame = max(_gesto_out_mid,
                                                    min(item.frame_end, _appear_frame + 1))
                            print(f"[THROW]   Gesto 'brazo hacia la espalda' (guardar) "
                                  f"aplicado -- mano llega a la espalda en "
                                  f"{_gesto_out_mid} (ahi desaparece '{item.label}'), "
                                  f"brazo vuelve a normal en {_gesto_out_fin}")
                    except Exception as _e_reach_out:
                        print(f"[THROW]   No se pudo aplicar el gesto de guardado "
                              f"para '{item.label}': {_e_reach_out}")

                try:
                    # BUGFIX (Kebyn + Claude, 2026-09-01 bis: "aun sin poses
                    # debe importar los objetos .blend segun como los
                    # configure para cada segmento"): antes, un item normal
                    # (no bloque_dinamico) se resolvia via
                    # `bpy.data.objects.get(item.target_object or
                    # item.object_name)` y, si ese nombre YA existia en
                    # bpy.data (ej. una corrida anterior en la misma sesion
                    # de Blender, o un `target_object` residual cargado desde
                    # un JSON de otra maquina/sesion), la rama `else:` de mas
                    # abajo se limitaba a `item.target_object = obj.name` y
                    # SALTEABA por completo el import, el reparenteo, el
                    # location/rotation/scale y -- lo mas grave -- el reseteo
                    # de las keyframes de visibilidad (hide_until_frame /
                    # set_visibility_keyframes). Resultado: si el usuario
                    # cambiaba frame_start/frame_end, el bone de destino, o
                    # el offset, esos cambios NUNCA se aplicaban en la
                    # siguiente "Concatenar segmentos" -- el objeto seguia
                    # rigiendose por las keyframes/parenteo de la corrida
                    # vieja (tipicamente ocultas fuera del rango nuevo), o
                    # simplemente el objeto reusado no estaba linkeado a
                    # ninguna coleccion de la escena activa. Se replica aqui
                    # el mismo criterio "empezar siempre de cero" que ya usa
                    # run_object_imports_live() (Importacion de Objetos):
                    # se borra cualquier objeto de una corrida anterior
                    # (identificado por item.imported_object_name, NUNCA por
                    # target_object) y se reimporta fresco en cada pasada,
                    # asi el resultado depende unicamente de la config
                    # ACTUAL del item, nunca de estado residual.
                    obj = None
                    if item.imported_object_name:
                        _old_obj = bpy.data.objects.get(item.imported_object_name)
                        if _old_obj is not None:
                            print(f"[THROW]   Eliminando objeto previo '{_old_obj.name}' "
                                  f"de '{item.label}' (se reimporta de cero)")
                            _old_mesh = _old_obj.data
                            bpy.data.objects.remove(_old_obj, do_unlink=True)
                            if _old_mesh is not None and getattr(_old_mesh, "users", 1) == 0:
                                try:
                                    bpy.data.meshes.remove(_old_mesh)
                                except Exception:
                                    pass
                        item.imported_object_name = ""
                    # ── Bloques dinamicos (ej. antorchas): libreria .blend
                    # COMPLETA + renombrado secuencial global, en vez del
                    # import de un solo objeto suelto -- ver
                    # import_bloque_dinamico_full() en object_import_utils.py.
                    # Se detecta por object_folder == 'bloques_dinamicos'
                    # (carpeta reservada para este tipo de prop, hermana de
                    # 'objetos/', NO anidada dentro). Cada tramo
                    # colocar_antorcha SIEMPRE reimporta (nunca reutiliza
                    # un obj ya en escena), porque cada antorcha plantada
                    # es una instancia nueva -- a diferencia de
                    # armas/escudos (arriba) que sí se reutilizan si ya
                    # están en escena.
                    # NUEVO ("crear pared NxN bloques"): mismo mecanismo de
                    # "bloque dinamico" (import completo + renombrado
                    # secuencial) que bloques_dinamicos, pero la fuente es
                    # un .blend elegido a mano por el usuario (item.blend_path,
                    # ruta absoluta libre) en vez de un archivo fijo dentro
                    # de la carpeta reservada bloques_dinamicos/ -- por eso
                    # se marca con su propio valor de object_folder en vez
                    # de reutilizar 'bloques_dinamicos' (que asume esa
                    # carpeta fija). Ver auto-registro en
                    # operators_segments.py (CERDO_1SEG_OT_AutoSplitFromConfig).
                    _es_ruta_libre = (item.object_folder or "").strip() == "pared_nxn_bloque"
                    _es_bloque_dinamico = _es_ruta_libre or (
                        (item.object_folder or "").strip() == "bloques_dinamicos")
                    # (obj ya es None a esta altura para AMBOS casos -- ver
                    # bugfix de arriba -- asi que este flag solo decide QUE
                    # rama de importacion usar, ya no si se reimporta.)

                    if _es_bloque_dinamico:
                        if _es_ruta_libre:
                            blend_abs = bpy.path.abspath(item.blend_path)
                        else:
                            anchor = (bpy.path.abspath(st.anim_dir)
                                      if st.anim_dir else bpy.path.abspath("//"))
                            bloques_dir = _oiu_preview.get_bloques_dinamicos_path_from_anchor(
                                anchor, item.levels_up)
                            blend_abs = os.path.join(bloques_dir, item.blend_filename)

                        root_anchor, _mapa = _oiu_preview.import_bloque_dinamico_full(
                            blend_abs,
                            target_location=(item.dest_x, item.dest_y, item.dest_z),
                            base_name=item.object_name or None,
                        )
                        if root_anchor is None:
                            _throw_errors.append(
                                f"No se pudo importar bloque dinamico "
                                f"'{item.object_name}' desde {blend_abs}")
                            continue

                        import mathutils
                        obj = root_anchor
                        item.imported_object_name = obj.name
                        item.target_object        = obj.name
                        obj[_THROW_UID_TAG] = item.uid

                        # Visibilidad de TODA la jerarquia recien traida
                        # (hide_viewport/hide_render no se hereda a los
                        # hijos en el viewport, asi que se aplica objeto
                        # por objeto -- luz + mallas de la antorcha).
                        _bloque_objs = [obj] + [c for c in obj.children_recursive]
                        for _bo in _bloque_objs:
                            _oiu_preview.hide_until_frame(_bo, appear_frame=_appear_frame)
                            # La antorcha se queda plantada (transition_out
                            # 'NONE' segun el auto-registro en
                            # operators_segments.py) -- no se oculta al
                            # terminar el tramo salvo que asi se configure.
                            if getattr(item, 'transition_out', 'NONE') != 'NONE':
                                _oiu_preview.set_visibility_keyframes(_bo, _disappear_frame, visible=False)

                        # Parenteo del Empty raiz a la mano (representa
                        # "sostenida" antes de agacharse a plantarla) —
                        # idéntico criterio que el resto del sistema
                        arm_name  = (item.parent_armature or "pig.arma_cerdo_1").strip()
                        bone_name = (item.parent_bone or "").strip()
                        all_arms  = [o for o in bpy.data.objects if o.type == 'ARMATURE']
                        arm_obj   = next((o for o in all_arms if o.name == arm_name), None)
                        if arm_obj is None and len(all_arms) == 1:
                            arm_obj = all_arms[0]
                        target_bone = None
                        if arm_obj and arm_obj.pose:
                            if bone_name:
                                target_bone = arm_obj.pose.bones.get(bone_name)
                            if target_bone is None:
                                target_bone = next(
                                    (pb for pb in arm_obj.pose.bones
                                     if 'bend' in pb.name.lower()), None)
                        if target_bone:
                            obj.parent      = target_bone.id_data
                            obj.parent_bone = target_bone.name
                            obj.parent_type = 'BONE'
                            obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
                        elif arm_obj:
                            obj.parent      = arm_obj
                            obj.parent_type = 'OBJECT'
                            obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
                        if target_bone and not item.target_bone:
                            item.target_bone = target_bone.name

                        _throw_imported += 1

                    else:
                        # Resolver ruta del .blend
                        print(f"[THROW]   Importando '{item.object_name}' "
                              f"para '{item.label}' (modo={item.mode}, "
                              f"frames {item.frame_start}->{item.frame_end})")
                        if item.blend_path and os.path.isfile(
                                bpy.path.abspath(item.blend_path)):
                            blend_abs = bpy.path.abspath(item.blend_path)
                        else:
                            anchor  = (bpy.path.abspath(st.anim_dir)
                                       if st.anim_dir else bpy.path.abspath("//"))
                            obj_dir = _oiu_preview.get_objetos_base_path_from_anchor(
                                anchor, item.levels_up)
                            blend_abs = os.path.join(
                                obj_dir, item.object_folder, item.blend_filename)

                        obj = _oiu_preview.import_object_from_blend_path(
                            blend_abs, item.object_name)

                        if obj is None:
                            _throw_errors.append(
                                f"No se pudo importar '{item.object_name}'")
                            continue

                        import mathutils
                        item.imported_object_name = obj.name
                        item.target_object        = obj.name
                        obj[_THROW_UID_TAG] = item.uid

                        # Visibilidad -- aparece en _appear_frame (frame_start
                        # + duracion del gesto de entrada), NO en frame_start,
                        # para que el objeto no aparezca hasta que el gesto
                        # de "brazo hacia la espalda" haya terminado de verse.
                        # Desaparece en _disappear_frame (frame_end - duracion
                        # del gesto de guardado), NO en frame_end, para que
                        # se oculte justo cuando la mano llega a la espalda
                        # a guardarlo, no cuando el brazo ya volvio a la
                        # normalidad.
                        _oiu_preview.hide_until_frame(
                            obj, appear_frame=_appear_frame)
                        _oiu_preview.set_visibility_keyframes(
                            obj, _disappear_frame, visible=False)

                        # Parenteo idéntico a run_object_imports_live
                        arm_name  = (item.parent_armature or "pig.arma_cerdo_1").strip()
                        bone_name = (item.parent_bone or "").strip()
                        all_arms  = [o for o in bpy.data.objects
                                     if o.type == 'ARMATURE']
                        arm_obj   = next((o for o in all_arms
                                          if o.name == arm_name), None)
                        if arm_obj is None and len(all_arms) == 1:
                            arm_obj = all_arms[0]
                        target_bone = None
                        if arm_obj and arm_obj.pose:
                            if bone_name:
                                target_bone = arm_obj.pose.bones.get(bone_name)
                            if target_bone is None:
                                target_bone = next(
                                    (pb for pb in arm_obj.pose.bones
                                     if 'bend' in pb.name.lower()), None)
                        if target_bone:
                            obj.parent      = target_bone.id_data
                            obj.parent_bone = target_bone.name
                            obj.parent_type = 'BONE'
                            obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
                        elif arm_obj:
                            obj.parent      = arm_obj
                            obj.parent_type = 'OBJECT'
                            obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
                        obj.location       = (item.loc_x, item.loc_y, item.loc_z)
                        obj.rotation_euler = (item.rot_x, item.rot_y, item.rot_z)
                        obj.scale          = (item.scale_uniform,
                                              item.scale_uniform,
                                              item.scale_uniform)
                        if target_bone and not item.target_bone:
                            item.target_bone = target_bone.name

                        # Transiciones cartoon de aparicion/desaparicion
                        # (mismo sistema que Importacion de Objetos —
                        # ver Cerdo_1ThrowItem.transition_in/out). Se
                        # aplican aca, con el objeto todavia parentado en
                        # espacio local. En THROW/CATCH, apply_throw_item()
                        # (paso 2, mas abajo) limpia cualquier keyframe de
                        # `location` en su rango antes de trazar la
                        # trayectoria real, asi que de esta transicion
                        # sobrevive solo la parte de escala/rotacion/alpha
                        # -- en HOLD (donde no hay paso 2) se aplica
                        # completa, incluida la parte de location.
                        _base_scale = item.scale_uniform
                        _base_loc   = (item.loc_x, item.loc_y, item.loc_z)
                        if getattr(item, 'transition_in', 'NONE') != 'NONE':
                            _oiu_preview.apply_transition_in(obj, item, _base_scale, _base_loc)
                        if getattr(item, 'transition_out', 'NONE') != 'NONE':
                            _oiu_preview.apply_transition_out(obj, item, _base_scale, _base_loc)

                        print(f"[THROW]   ✅ '{obj.name}' importado, parentado a "
                              f"'{arm_name}'/'{bone_name}', visible "
                              f"{_appear_frame}->{_disappear_frame}")
                        _throw_imported += 1
                    # NOTA: ya no existe una rama "reusar objeto existente" --
                    # ver bugfix de arriba (comienzo del try): SIEMPRE se
                    # borra cualquier import previo y se reimporta de cero,
                    # asi que a esta altura del codigo el item o bien se
                    # importo recien (arriba) o ya hizo `continue` por error.

                    # 2. Aplicar trayectoria — el modo HOLD ("Mantener") no tiene
                    # trayectoria: el objeto ya quedó aparentado y posicionado por
                    # el offset del paso 1 (import + parent), igual que el sistema
                    # de Importacion de Objetos. Saltar apply_throw_item() por
                    # completo evita generarle keyframes de location/rotation que
                    # no corresponden (y que además desparentarían el objeto, ver
                    # apply_throw_item()).
                    if item.mode == 'HOLD':
                        _throw_applied += 1
                    else:
                        ok_traj = apply_throw_item(item, context)
                        if ok_traj:
                            _throw_applied += 1
                        else:
                            _throw_errors.append(
                                f"Trayectoria falló: '{item.object_name}'")

                except Exception as _e_item:
                    import traceback
                    _throw_errors.append(f"'{item.object_name}': {_e_item}")
                    print(f"[THROW] Error en item: {_e_item}")
                    traceback.print_exc()

    except Exception as _e_throw:
        import traceback
        print("[run_throws_for_segments] Error en Lanzar/Recoger:")
        print(traceback.format_exc())
        _throw_errors.append(f"Error general: {_e_throw}")

    for _te in _throw_errors:
        print(f"[run_throws_for_segments] {_te}")

    return _throw_imported, _throw_applied, _throw_errors


class CERDO_1_ST_OT_Concatenate(Operator):
    bl_idname    = "cerdo_1_st.concatenate"
    bl_label     = "CONCATENAR"
    bl_description = "Genera la animacion interpolando las poses en la timeline"
    bl_options   = {"REGISTER", "UNDO"}

    # Si True: NO borra la action/keyframes existentes del armature ni del
    # root antes de hornear — solo agrega los keyframes de este segmento
    # encima de lo que ya haya. Lo usa "CONCATENAR Y REPRODUCIR TODO" para
    # encadenar varios segmentos en una misma action continua sin que cada
    # llamada borre el trabajo de la anterior. El boton individual de cada
    # segmento sigue usando el default False (comportamiento de siempre).
    keep_existing_action: bpy.props.BoolProperty(default=False)

    # Si True (default: boton individual del panel de segmentos): al
    # terminar de inyectar las poses, salta al frame_start de ESTE
    # segmento y reproduce hasta su frame_end, para ver de inmediato el
    # resultado sin tener que ir a buscar otro boton. "CONCATENAR Y
    # REPRODUCIR TODO" (CERDO_1SEG_OT_ConcatenateAll) llama a este mismo
    # operador una vez por segmento en un loop; pasa auto_play=False para
    # no disparar una reproduccion parcial por cada segmento del loop y
    # reproducir la secuencia completa una sola vez al final.
    auto_play: bpy.props.BoolProperty(default=True)

    # BUGFIX (Kebyn, 2026-07-10): que segmento (indice dentro de
    # cerdo_1_segs.segments) debe usar este CONCATENAR. -1 = sin especificar,
    # cae al comportamiento viejo (segs_data.active_index).
    #
    # Por que hace falta: la lista de segmentos en el panel NO es un
    # template_list (no hay seleccion de UI real) — se dibuja como una serie
    # de boxes plegables independientes (toggle_config por segmento). Abrir
    # el box de un segmento y ver sus datos (poses, rango de frames) en
    # pantalla NO actualiza cerdo_1_segs.active_index; ese indice solo cambia
    # al agregar/duplicar un segmento. Resultado: el boton CONCATENAR que se
    # ve DENTRO del box del segmento "04_parada" podia terminar operando
    # sobre otro segmento (el que haya quedado en active_index), inyectando
    # sus poses y reproduciendo su rango en vez del que el usuario tiene
    # abierto en pantalla — ej. reproducir desde el frame 1 en vez de
    # 182->428. El panel ahora pasa seg_idx=i explicitamente al llamar a
    # este operador, asi CONCATENAR siempre opera sobre el segmento que el
    # usuario esta mirando, sin importar el active_index.
    seg_idx: bpy.props.IntProperty(default=-1)

    # AISLAMIENTO TOTAL DE SEGMENTOS (Kebyn + Claude, 2026-07-11):
    # Si True, la action horneada por ESTE segmento se empuja a su PROPIA
    # pista NLA dedicada (extrapolation='NOTHING') en vez de quedar como
    # active action compartida entre llamadas. Con esto ningun segmento
    # puede heredar keyframes, curvas de interpolacion, ni valores de
    # bones de otro segmento -- cada uno vive exclusivamente en su propio
    # rango de frames. Efecto colateral aceptado a proposito: un bone
    # compartido entre dos segmentos consecutivos (ej. piernas en dos
    # tramos de caminar) YA NO mantiene continuidad entre ellos -- cada
    # segmento vuelve a rest fuera de su propio rango. Lo usa
    # CERDO_1SEG_OT_ConcatenateAll; el boton individual de un segmento
    # sigue con el default False (comportamiento de siempre, un solo
    # segmento a la vez no necesita empujarse a NLA).
    isolate_segments: bpy.props.BoolProperty(default=False)

    # BUGFIX (Kebyn + Claude, 2026-08-04): nombres de las actions de
    # respaldo de Capa 1 (armature/root) preservadas por
    # CERDO_1SEG_OT_ConcatenateAll ANTES de que el loop de segmentos
    # empiece a destruir la action compartida. Ver comentario junto a
    # "_capa1_backup_swap" mas abajo.
    capa1_backup_arm:  bpy.props.StringProperty(default="")
    capa1_backup_root: bpy.props.StringProperty(default="")

    def execute(self, context):
        st    = context.scene.cerdo_1_st
        scene = context.scene

        # ── Si hay un segmento activo con poses definidas, usarlo como fuente ──
        # El boton CONCATENAR del panel de segmentos llama a este mismo operador,
        # pero los datos estan en cerdo_1_segs (seg.*) y no en cerdo_1_st (st.*).
        # Sincronizamos st con el segmento activo antes de continuar.
        segs_data = getattr(context.scene, "cerdo_1_segs", None)
        _active_seg_idx = None
        # Indice resuelto: preferir seg_idx explicito (pasado por el panel),
        # y solo si no vino especificado caer al viejo active_index.
        _resolved_idx = (self.seg_idx if self.seg_idx >= 0
                          else (segs_data.active_index if segs_data is not None else -1))
        if segs_data is not None:
            _segs_list = segs_data.segments
            _idx       = _resolved_idx
            if _segs_list and 0 <= _idx < len(_segs_list):
                _active_seg_idx = _idx
                seg = _segs_list[_idx]
                if len(seg.action_poses) > 0:
                    # Poses de accion intermedias (src: Cerdo_1SegmentPoseSlot, dst: Cerdo_1PoseSlotItem)
                    st.action_poses.clear()
                    for src in seg.action_poses:
                        dst = st.action_poses.add()
                        dst.json_file    = getattr(src, "json_file",   "")
                        dst.pose_name    = getattr(src, "pose_name",   "") or getattr(src, "pose_label", "")
                        dst.pose_label   = getattr(src, "pose_label",  "") or getattr(src, "pose_name",  "")
                        dst.pose_index   = getattr(src, "pose_index",  0)
                        dst.duration     = getattr(src, "duration",    24)
                        dst.entry_ratio  = getattr(src, "entry_ratio", 0.3)
                        dst.exit_ratio   = getattr(src, "exit_ratio",  0.3)
                        dst.interp_type  = getattr(src, "interp_type", "SMOOTH")
                        dst.rot_x = getattr(src, "rot_x", 0.0)
                        dst.rot_y = getattr(src, "rot_y", 0.0)
                        dst.rot_z = getattr(src, "rot_z", 0.0)
                        dst.pos_x = getattr(src, "pos_x", 0.0)
                        dst.pos_y = getattr(src, "pos_y", 0.0)
                        dst.pos_z = getattr(src, "pos_z", 0.0)
                        dst.manual_start    = getattr(src, "manual_start", False)
                        dst.frame_abs_start = getattr(src, "frame_abs_start", 0)
                    # Frame de inicio: usar frame_start del segmento
                    st.start_frame = seg.frame_start
                    # Armature y carpeta de poses desde cerdo_1_segs si estan definidos
                    if segs_data.armature_name:
                        st.armature_name = segs_data.armature_name
                    if segs_data.poses_dir:
                        st.poses_dir = segs_data.poses_dir

        # ── Construir set de bones excluidos desde el segmento activo ──
        # Cada flag filter_<x> = True significa que ese bone NO recibe poses.
        _excluded_bones = set()
        if segs_data is not None:
            _segs_list = segs_data.segments
            _idx       = _resolved_idx
            if _segs_list and 0 <= _idx < len(_segs_list):
                _seg = _segs_list[_idx]
                _FILTER_MAP = [
                    ("filter_main_bone",   "Armature"),
                    ("filter_hips",        "Body_cerdo_1"),
                    ("filter_spine",       "Body:Bend_cerdo_1"),
                    ("filter_spine1",      "Body:Bend_cerdo_1"),
                    ("filter_spine2",      "Body:Bend_cerdo_1"),
                    ("filter_neck",        "Head_cerdo_1"),
                    ("filter_face",        "Head_cerdo_1"),
                    ("filter_right_arm",   "Leg:FR_cerdo_1"),
                    ("filter_right_elbow", "Leg:FR:Bend_cerdo_1"),
                    ("filter_left_arm",    "Leg:FL_cerdo_1"),
                    ("filter_left_elbow",  "Leg:FL:Bend_cerdo_1"),
                    ("filter_right_leg",   "Leg:BR_cerdo_1"),
                    ("filter_right_knee",  "Leg:BR:Bend_cerdo_1"),
                    ("filter_left_leg",    "Leg:BL_cerdo_1"),
                    ("filter_left_knee",   "Leg:BL:Bend_cerdo_1"),
                    ("filter_no_bone_01",  "no_bone_01"),
                    ("filter_no_bone_02",  "no_bone_02"),
                    ("filter_no_bone_03",  "no_bone_03"),
                    ("filter_no_bone_04",  "no_bone_04"),
                    ("filter_no_bone_05",  "no_bone_05"),
                    ("filter_no_bone_06",  "no_bone_06"),
                    ("filter_no_bone_07",  "no_bone_07"),
                    ("filter_no_bone_08",  "no_bone_08"),
                ]
                for attr, bone_name in _FILTER_MAP:
                    if getattr(_seg, attr, False):
                        _excluded_bones.add(bone_name)

        # ── Bloqueador de bones: intervalos de frames (bone_blocks) ──────
        # BUG (reportado por Kebyn, 2026-07-07): el bloqueo simple de arriba
        # (checkbox filter_* => _excluded_bones, aplica a TODO el segmento)
        # si se aplicaba al hornear, pero los intervalos de frames por bone
        # (seg.bone_blocks / Cerdo_1BoneBlockEntry.intervals, Ini->Fin desde
        # el panel) se guardaban/exportaban/importaban correctamente pero
        # JAMAS se consultaban aqui — solo quedaban en properties.py,
        # config_ops.py, operators_segments.py y panels.py (UI/serializacion),
        # sin ningun efecto real en el bake. Se construye aqui un mapa
        # bone_name -> lista de intervalos (frame_start, frame_end) ACTIVOS
        # (enabled=True, frame_start < frame_end), traduciendo bone_key
        # ("filter_hips") a nombre real de bone ("Body_cerdo_1") con el mismo
        # _FILTER_MAP de arriba.
        _interval_blocks = {}   # bone_name -> [(frame_start, frame_end), ...]
        if segs_data is not None and _segs_list and 0 <= _idx < len(_segs_list):
            _bone_key_to_name = dict(_FILTER_MAP)
            for _bb_entry in _seg.bone_blocks:
                _bb_bone_name = _bone_key_to_name.get(_bb_entry.bone_key)
                if not _bb_bone_name:
                    continue
                for _iv in _bb_entry.intervals:
                    if not _iv.enabled:
                        continue
                    if _iv.frame_start >= _iv.frame_end:
                        continue
                    _interval_blocks.setdefault(_bb_bone_name, []).append(
                        (_iv.frame_start, _iv.frame_end)
                    )

        def _bone_blocked_at(bone_name, abs_f):
            """True si `bone_name` debe quedar excluido del keyframe en el
            frame absoluto `abs_f`: por el checkbox simple (todo el
            segmento) o por caer dentro de alguno de sus intervalos de
            bone_blocks."""
            if bone_name in _excluded_bones:
                return True
            for _fs, _fe in _interval_blocks.get(bone_name, ()):
                if _fs <= abs_f <= _fe:
                    return True
            return False

        start_frame = st.start_frame
        entry_ratio = st.entry_ratio
        exit_ratio  = st.exit_ratio

        if not st.armature_name:
            self.report({"ERROR"}, "Selecciona el armature de Cerdo_1 primero")
            return {"CANCELLED"}
        armature = scene.objects.get(st.armature_name)
        if not armature or armature.type != "ARMATURE":
            armature = _find_cerdo_1_armature(context)
            if armature is not None:
                st.armature_name = armature.name
                seg_cfg = getattr(scene, "cerdo_1_segs", None)
                if seg_cfg is not None:
                    seg_cfg.armature_name = armature.name
        if not armature or armature.type != "ARMATURE":
            self.report({"ERROR"}, f"Armature '{st.armature_name}' no valido")
            return {"CANCELLED"}
        if len(st.action_poses) == 0:
            self.report({"ERROR"}, "Agrega al menos una pose de accion")
            return {"CANCELLED"}

        action_items = list(st.action_poses)
        rec_start = get_pose_record(st.poses_dir, action_items[0].json_file, action_items[0].pose_index)
        rec_end   = get_pose_record(st.poses_dir, action_items[-1].json_file, action_items[-1].pose_index)
        if rec_start is None:
            self.report({"ERROR"}, f"No se pudo cargar la primera pose de accion ('{action_items[0].pose_name}')")
            return {"CANCELLED"}
        if rec_end is None:
            self.report({"ERROR"}, f"No se pudo cargar la ultima pose de accion ('{action_items[-1].pose_name}')")
            return {"CANCELLED"}

        d_start = pose_record_to_full_dict(rec_start)
        d_end   = pose_record_to_full_dict(rec_end)

        # Rotacion/posicion del root en la primera y ultima pose de accion
        # (actuan como anclas implicitas de inicio/fin de la animacion).
        _psx, _psy, _psz, _rsx, _rsy, _rsz = get_root_transform_from_record(rec_start)
        _pex, _pey, _pez, _rex, _rey, _rez = get_root_transform_from_record(rec_end)
        arm_rot_start = (math.radians(_rsx), math.radians(_rsy), math.radians(_rsz))
        arm_rot_end   = (math.radians(_rex), math.radians(_rey), math.radians(_rez))
        arm_pos_start = (_psx, _psy, _psz)
        arm_pos_end   = (_pex, _pey, _pez)

        segments     = []   # (d_s, d_a, d_e, n_frames, interp_type)
        seg_arm_rots = []   # (rot_s, rot_a, rot_e, n_frames, interp_type)
        seg_arm_pos  = []   # (pos_s, pos_a, pos_e, n_frames, interp_type)

        # Calcular frame_abs_start de cada pose para el handler de preview en tiempo real.
        # Respeta manual_start: si el usuario fijo un frame de inicio para una pose (y
        # no invade a la anterior), se usa tal cual; el resto se sigue apilando
        # automaticamente como siempre.
        _resolved_starts = resolve_pose_start_frames(action_items, start_frame)
        for _item, _fs in zip(action_items, _resolved_starts):
            _item.frame_abs_start = _fs

        # Propagar frame_abs_start también a seg.action_poses (Cerdo_1SegmentPoseSlot)
        # para que el semáforo del panel lo pueda leer directamente desde seg.
        if segs_data is not None:
            _segs_list = segs_data.segments
            _idx = _resolved_idx
            if _segs_list and 0 <= _idx < len(_segs_list):
                _seg_act = _segs_list[_idx]
                for _ii, _sit in enumerate(_seg_act.action_poses):
                    if _ii < len(action_items):
                        _sit.frame_abs_start = action_items[_ii].frame_abs_start

        for i, item in enumerate(action_items):
                rec_act = get_pose_record(st.poses_dir, item.json_file, item.pose_index)
                if rec_act is None:
                    self.report({"WARNING"}, f"Pose '{item.pose_name}' no encontrada, omitida")
                    continue
                d_act = pose_record_to_full_dict(rec_act)
                # ── Root: SIEMPRE se lee del .json de la pose (igual que los huesos),
                # nunca del cache item.pos_x/rot_x. Esto es lo que hace que el Root
                # persista igual que los huesos al cerrar y reabrir Blender. ──
                _px, _py, _pz, _rx, _ry, _rz = get_root_transform_from_record(rec_act)
                arm_rot_act = (math.radians(_rx), math.radians(_ry), math.radians(_rz))
                arm_pos_act = (_px, _py, _pz)

                if i == 0:
                    d_seg_s       = d_start
                    arm_rot_seg_s = arm_rot_start
                    arm_pos_seg_s = arm_pos_start
                else:
                    prev          = action_items[i-1]
                    rec_p         = get_pose_record(st.poses_dir, prev.json_file, prev.pose_index)
                    d_seg_s       = pose_record_to_full_dict(rec_p) if rec_p else d_start
                    _pxp, _pyp, _pzp, _rxp, _ryp, _rzp = get_root_transform_from_record(rec_p)
                    arm_rot_seg_s = (math.radians(_rxp), math.radians(_ryp), math.radians(_rzp))
                    arm_pos_seg_s = (_pxp, _pyp, _pzp)

                if i == len(action_items) - 1:
                    d_seg_e       = d_end
                    arm_rot_seg_e = arm_rot_end
                    arm_pos_seg_e = arm_pos_end
                else:
                    nxt           = action_items[i+1]
                    rec_n         = get_pose_record(st.poses_dir, nxt.json_file, nxt.pose_index)
                    d_seg_e       = pose_record_to_full_dict(rec_n) if rec_n else d_end
                    _pxn, _pyn, _pzn, _rxn, _ryn, _rzn = get_root_transform_from_record(rec_n)
                    arm_rot_seg_e = (math.radians(_rxn), math.radians(_ryn), math.radians(_rzn))
                    arm_pos_seg_e = (_pxn, _pyn, _pzn)

                seg_interp = item.interp_type
                segments.append((d_seg_s, d_act, d_seg_e, item.duration, seg_interp))
                seg_arm_rots.append((arm_rot_seg_s, arm_rot_act, arm_rot_seg_e, item.duration, seg_interp))
                seg_arm_pos.append((arm_pos_seg_s,  arm_pos_act, arm_pos_seg_e,  item.duration, seg_interp))

        if not segments:
            self.report({"ERROR"}, "No hay segmentos validos para concatenar")
            return {"CANCELLED"}

        context.view_layer.objects.active = armature
        if armature.mode != "POSE":
            bpy.ops.object.mode_set(mode="POSE")
        for pb in armature.pose.bones:
            pb.rotation_mode = "XYZ"
        armature.rotation_mode = "XYZ"

        # ── CAPTURA DE CAPA 1 (desplazamiento base ya horneado: caminar /
        # saltar / parada) ANTES de borrar la action. ──────────────────────
        # FIX (Kebyn, 2026-08-04): "los bones no involucrados en los
        # primeros 30 frames aparecen en posicion T en vez de caminar con
        # normalidad". Causa real: el bloque de abajo borra la action
        # COMPLETA del armature (Capa 1, horneada por cerdo_1pr.preview_path)
        # y reconstruye el segmento SOLO a partir de las poses configuradas
        # -- en cualquier frame donde ninguna pose cubre ese instante (antes
        # de la primera pose, o despues de la ultima si el segmento sigue
        # mas alla, ej. segmento [1->96] con poses que solo llegan a f70),
        # no queda ningun rastro del caminar base y los bones vuelven a su
        # rest pose (T). Las poses deben INYECTARSE sobre la animacion
        # base, no reemplazarla entera.
        #
        # Fix: antes de borrar nada, se evalua/captura frame a frame lo que
        # YA esta horneado (Capa 1) en todo el rango util del segmento
        # (hasta donde llegan las poses configuradas, o hasta el
        # seg.frame_end real si es mayor). Mas abajo, los tramos "sin
        # pose" (antes de la primera / despues de la ultima) usan estos
        # valores capturados frame a frame en vez de un rest pose fijo --
        # asi el personaje sigue caminando con normalidad hasta que entra
        # la primera pose (f30 en el ejemplo), y retoma el caminar al
        # salir de la ultima.
        _seg_real_end = None
        if _active_seg_idx is not None and segs_data is not None:
            _seg_list_cap = segs_data.segments
            if 0 <= _active_seg_idx < len(_seg_list_cap):
                _seg_end_candidate = _seg_list_cap[_active_seg_idx].frame_end
                if _seg_end_candidate and _seg_end_candidate > start_frame:
                    _seg_real_end = _seg_end_candidate

        _poses_end_estimate = (
            _resolved_starts[-1] + action_items[-1].duration - 1
            if _resolved_starts and action_items else start_frame
        )
        _cap_end_frame = max(start_frame, _poses_end_estimate, _seg_real_end or 0)

        _base_cap_bones   = {}   # abs_f -> {bone: {"rot":..,"loc":..,"scale":..}}
        _base_cap_arm_rot = {}   # abs_f -> (rx,ry,rz)
        _base_cap_arm_pos = {}   # abs_f -> (x,y,z)
        _have_base_cap    = False

        # BUGFIX (Kebyn + Claude, 2026-08-04): "despues del segmento 2 el
        # bone Head_cerdo_1 rota de golpe sin ninguna pose asignada".
        #
        # Causa real (mas profunda que el fix anterior de "hueco tras la
        # ultima pose"): AISLAMIENTO TOTAL DE SEGMENTOS borra la action
        # COMPARTIDA COMPLETA (armature.animation_data.action = None +
        # bpy.data.actions.remove(...)) cada vez que un segmento CON
        # poses se concatena -- no solo su propio rango, TODA la Capa 1
        # regenerada por cerdo_1pr.preview_path, incluyendo el rango de
        # los segmentos que TODAVIA no se procesaron. A partir del
        # PRIMER segmento con poses, la captura de arriba (pensada para
        # leer "el caminar real") en realidad lee lo que haya quedado
        # residual en pose.bones en ese instante -- no la Capa 1 real --
        # y ese residuo se hornea como si fuera caminar valido.
        #
        # CERDO_1SEG_OT_ConcatenateAll ahora guarda una COPIA intacta de
        # la Capa 1 (armature + root "cerdo_1") ANTES de arrancar su loop
        # de segmentos, y pasa el nombre de esa copia aca via
        # capa1_backup_arm/capa1_backup_root. Si esta disponible, se usa
        # como fuente de verdad para ESTA captura -- swap temporal, sin
        # tocar la action compartida real ni la copia (se restaura a
        # None apenas termina de leer, antes de que el bloque de abajo
        # borre/reconstruya la action activa).
        _capa1_backup_swap = []  # [(obj, original_action_or_None), ...]
        if self.capa1_backup_arm and armature.animation_data:
            _bk_act = bpy.data.actions.get(self.capa1_backup_arm)
            if _bk_act is not None:
                _capa1_backup_swap.append((armature, armature.animation_data.action))
                armature.animation_data.action = _bk_act
        if self.capa1_backup_root:
            _bk_root_obj = bpy.data.objects.get("cerdo_1")
            if _bk_root_obj is not None and _bk_root_obj.animation_data:
                _bk_root_act = bpy.data.actions.get(self.capa1_backup_root)
                if _bk_root_act is not None:
                    _capa1_backup_swap.append((_bk_root_obj, _bk_root_obj.animation_data.action))
                    _bk_root_obj.animation_data.action = _bk_root_act

        if armature.animation_data:
            _root_for_cap      = bpy.data.objects.get("cerdo_1")
            _frame_backup_cap  = scene.frame_current
            for _cf in range(start_frame, _cap_end_frame + 1):
                scene.frame_set(_cf)
                _fb = {}
                for _bn in BONES_LISTA:
                    _pb_cap = armature.pose.bones.get(_bn)
                    if _pb_cap:
                        _fb[_bn] = {
                            "rot":   tuple(_pb_cap.rotation_euler),
                            "loc":   tuple(_pb_cap.location),
                            "scale": tuple(_pb_cap.scale),
                        }
                if _fb:
                    _base_cap_bones[_cf] = _fb
                    _have_base_cap = True
                if _root_for_cap:
                    _base_cap_arm_rot[_cf] = tuple(_root_for_cap.rotation_euler)
                    _base_cap_arm_pos[_cf] = tuple(_root_for_cap.location)
            scene.frame_set(_frame_backup_cap)

        # Restaurar la action original (probablemente None) ANTES del
        # bloque de abajo -- así el swap temporal de la copia de Capa 1
        # nunca queda expuesto a self.keep_existing_action ni se borra
        # por accidente junto con la action real.
        for _obj_restore, _orig_action in _capa1_backup_swap:
            _obj_restore.animation_data.action = _orig_action

        if armature.animation_data and armature.animation_data.action:
            if not self.keep_existing_action:
                old_action = armature.animation_data.action
                armature.animation_data.action = None
                bpy.data.actions.remove(old_action)
        if not armature.animation_data:
            armature.animation_data_create()

        # ── Limpiar keyframes previos del root (cerdo_1 Empty) ──
        # Sin esto, keyframes viejos en frame 1 causan interpolacion
        # desde frame 1 hasta start_frame antes de que empiece la animacion.
        # Se omite si keep_existing_action=True (concatenacion multi-segmento):
        # borraria las poses de los segmentos ya horneados en esta misma pasada.
        _root_cleanup = bpy.data.objects.get("cerdo_1")
        if not self.keep_existing_action:
            if _root_cleanup and _root_cleanup.animation_data:
                if _root_cleanup.animation_data.action:
                    _old_root = _root_cleanup.animation_data.action
                    _root_cleanup.animation_data.action = None
                    bpy.data.actions.remove(_old_root)
                # Tambien limpiar NLA tracks del root para no acumular strips
                # -- SALVO en modo isolate_segments: ahi las pistas de otros
                # segmentos ya procesados en este mismo loop deben seguir
                # vivas (ver comentario junto a isolate_segments arriba).
                # CERDO_1SEG_OT_ConcatenateAll limpia sus propias pistas
                # "ALFSEG_*" al INICIO del loop completo, no aqui.
                if not self.isolate_segments:
                    for _trk in list(_root_cleanup.animation_data.nla_tracks):
                        _root_cleanup.animation_data.nla_tracks.remove(_trk)
            # Limpiar NLA tracks del armature igualmente (misma salvedad)
            if armature.animation_data and not self.isolate_segments:
                for _trk in list(armature.animation_data.nla_tracks):
                    armature.animation_data.nla_tracks.remove(_trk)

        # Construir waypoints de BONES: (frame_abs, full_pose_dict, interp_hacia_siguiente)
        # El interp_type de cada waypoint se aplica en el TRAMO que sale de ese waypoint
        # hacia el siguiente. Por eso cada waypoint lleva el tipo de curva que debe usar
        # para llegar al waypoint siguiente.
        #
        # FIX (Kebyn, 2026-08-04): "la pose se reproduce desde el frame 1 en
        # vez de respetar el @f30 que le puse". La primera pose de la lista
        # actua como "ancla implicita" del COMIENZO del segmento -- hasta
        # aca, SIEMPRE se sembraba el primer waypoint (en start_frame, el
        # frame 1 del segmento) con los valores de esa primera pose, sin
        # importar que el usuario le hubiera puesto manual_start a un frame
        # mas tarde (ej. f30). Resultado: el personaje ya aparecia en esa
        # pose desde el frame 1 del segmento -- el manual_start solo movia
        # la etiqueta "@f30" en la lista, pero no el resultado real.
        #
        # Ahora, si la primera pose tiene un hueco real antes de su propio
        # inicio resuelto (_resolved_starts[0] > start_frame -- ver
        # resolve_pose_start_frames en pose_utils.py, ya calculado arriba),
        # ese hueco NO se llena con un rest pose fijo -- se llena con el
        # caminar base capturado (Capa 1, ver captura mas arriba), escrito
        # frame a frame directamente en el loop principal de abajo (busca
        # "_first_pose_gap" en el loop de escritura). Este waypoint solo
        # actua como ancla del PUNTO DE ENTRADA hacia la primera pose (en
        # _resolved_starts[0]): usa el valor capturado del caminar base
        # EN ESE FRAME EXACTO, para que la pose empiece a mezclarse desde
        # donde el personaje realmente esta parado en el ciclo de caminata,
        # no desde un T-pose. Si no hay captura disponible (sin Capa 1
        # horneada todavia), cae a rest pose como ultimo recurso. Si no
        # hay manual_start en la primera pose (el caso de siempre),
        # _resolved_starts[0] == start_frame y el comportamiento es
        # IDENTICO al de antes.
        _first_pose_gap = max(0, _resolved_starts[0] - start_frame) if _resolved_starts else 0
        _first_seg_interp = segments[0][4] if segments else "SMOOTH"

        if _first_pose_gap > 0:
            _gap_anchor_bones = (
                _base_cap_bones.get(_resolved_starts[0]) if _have_base_cap else None
            ) or {bone: dict(_BONE_DEFAULT) for bone in BONES_LISTA}
            _gap_anchor_arm_rot = (
                _base_cap_arm_rot.get(_resolved_starts[0]) if _have_base_cap else None
            ) or (0.0, 0.0, 0.0)
            _gap_anchor_arm_pos = (
                _base_cap_arm_pos.get(_resolved_starts[0]) if _have_base_cap else None
            ) or (0.0, 0.0, 0.0)
            waypoints = [
                (start_frame,             _gap_anchor_bones, _first_seg_interp),
                (_resolved_starts[0],     _gap_anchor_bones, _first_seg_interp),
            ]
            arm_waypoints = [
                (start_frame,             _gap_anchor_arm_rot, _first_seg_interp),
                (_resolved_starts[0],     _gap_anchor_arm_rot, _first_seg_interp),
            ]
            pos_waypoints = [
                (start_frame,             _gap_anchor_arm_pos, _first_seg_interp),
                (_resolved_starts[0],     _gap_anchor_arm_pos, _first_seg_interp),
            ]
        else:
            waypoints = [(start_frame, d_start, _first_seg_interp)]
            arm_waypoints = [(start_frame, arm_rot_start, _first_seg_interp)]
            pos_waypoints = [(start_frame, arm_pos_start, _first_seg_interp)]

        # Frame de inicio resuelto de cada pose (respeta manual_start; ver
        # resolve_pose_start_frames en pose_utils.py). Un frame manual mas
        # tarde que el automatico deja un hueco entre poses -- ese hueco no
        # necesita tratamiento especial: el waypoint del medio de la pose
        # anterior y el de esta simplemente quedan mas separados, y la
        # interpolacion normal (Bezier/Linear/etc, segun interp_type) se
        # estira sola para cubrirlo sin cortes.
        _pose_starts = resolve_pose_start_frames(action_items, start_frame)

        cursor = start_frame
        for idx_seg, ((d_s, d_a, d_e, n_frames, seg_interp),
                      (ar_s, ar_a, ar_e, _, _arm_interp),
                      (ap_s, ap_a, ap_e, _, _pos_interp)) in \
                enumerate(zip(segments, seg_arm_rots, seg_arm_pos)):
            cursor = _pose_starts[idx_seg]
            mid = cursor + n_frames // 2
            # El tramo que sale del waypoint medio usa el interp del segmento SIGUIENTE
            # (o el propio interp si es el ultimo) para la transicion de salida
            if idx_seg + 1 < len(segments):
                next_interp = segments[idx_seg + 1][4]
            else:
                next_interp = seg_interp
            waypoints.append((mid, d_a, next_interp))
            arm_waypoints.append((mid, ar_a, next_interp))
            pos_waypoints.append((mid, ap_a, next_interp))
            cursor += n_frames

        end_frame  = cursor - 1
        _end_interp = segments[-1][4] if segments else "SMOOTH"
        waypoints.append((end_frame, d_end, _end_interp))
        arm_waypoints.append((end_frame, arm_rot_end, _end_interp))
        pos_waypoints.append((end_frame, arm_pos_end, _end_interp))

        # FIX (Kebyn, 2026-08-04, simetrico al del hueco inicial): si la
        # ultima pose termina antes de que acabe el segmento real (ej.
        # poses hasta f70 mientras el segmento sigue hasta f96), ese tramo
        # final tambien debe seguir caminando en vez de quedar congelado
        # en la ultima pose. _pose_end_frame marca hasta donde llega la
        # interpolacion de poses (_pose_at_frame); si hay caminar base
        # capturado mas alla de eso, se extiende end_frame para cubrirlo
        # -- el loop de escritura de mas abajo usa la captura directa
        # (no _pose_at_frame) para ese tramo extra.
        _pose_end_frame = end_frame
        if _have_base_cap and _cap_end_frame > end_frame:
            end_frame = _cap_end_frame
        total_gen = end_frame - start_frame + 1

        def _pose_at_frame(abs_f):
            for i in range(len(waypoints) - 1):
                f0, p0, itp = waypoints[i]
                f1, p1, _   = waypoints[i + 1]
                if abs_f <= f1 or i == len(waypoints) - 2:
                    span = f1 - f0
                    if span <= 0:
                        return p1
                    t = apply_interp(max(0.0, min(1.0, (abs_f - f0) / span)), itp)
                    result = {}
                    for bone in BONES_LISTA:
                        a = p0.get(bone, _BONE_DEFAULT)
                        b = p1.get(bone, _BONE_DEFAULT)
                        result[bone] = {
                            "rot":   _lerp(a["rot"],   b["rot"],   t),
                            "loc":   _lerp(a["loc"],   b["loc"],   t),
                            "scale": _lerp(a["scale"], b["scale"], t),
                        }
                    return result
            return {bone: d_end.get(bone, _BONE_DEFAULT) for bone in BONES_LISTA}

        def _arm_rot_at_frame(abs_f):
            for i in range(len(arm_waypoints) - 1):
                f0, r0, itp = arm_waypoints[i]
                f1, r1, _   = arm_waypoints[i + 1]
                if abs_f <= f1 or i == len(arm_waypoints) - 2:
                    span = f1 - f0
                    if span <= 0:
                        return r1
                    t = apply_interp(max(0.0, min(1.0, (abs_f - f0) / span)), itp)
                    return _lerp(r0, r1, t)
            return arm_rot_end

        def _arm_pos_at_frame(abs_f):
            """Interpola la posicion XYZ del root entre waypoints."""
            for i in range(len(pos_waypoints) - 1):
                f0, p0, itp = pos_waypoints[i]
                f1, p1, _   = pos_waypoints[i + 1]
                if abs_f <= f1 or i == len(pos_waypoints) - 2:
                    span = f1 - f0
                    if span <= 0:
                        return p1
                    t = apply_interp(max(0.0, min(1.0, (abs_f - f0) / span)), itp)
                    return _lerp(p0, p1, t)
            return arm_pos_end

        # Escribir keyframes — bones + rotacion + posicion del root
        #
        # FIX (Kebyn, 2026-08-04): en los tramos SIN pose (antes de
        # _resolved_starts[0], o despues de _pose_end_frame si el
        # segmento sigue mas alla) se usa la captura de Capa 1 frame a
        # frame en vez de _pose_at_frame/_arm_*_at_frame -- esas funciones
        # solo interpolan ENTRE waypoints (linea recta), lo que en el
        # tramo inicial daria un valor congelado (el mismo en todos los
        # frames del hueco). La captura, en cambio, ya tiene el caminar
        # real de cada frame, asi que el personaje sigue caminando con
        # normalidad hasta que entra la pose, y retoma el caminar al
        # salir de ella.
        for abs_f in range(start_frame, end_frame + 1):
            _in_gap = _have_base_cap and (
                abs_f < _resolved_starts[0] or abs_f > _pose_end_frame
            )
            if _in_gap and abs_f in _base_cap_bones:
                pose    = _base_cap_bones[abs_f]
                arm_rot = _base_cap_arm_rot.get(abs_f, (0.0, 0.0, 0.0))
                arm_pos = _base_cap_arm_pos.get(abs_f, (0.0, 0.0, 0.0))
            elif _in_gap and _have_base_cap and _base_cap_bones:
                # SALVAGUARDA (Kebyn + Claude, 2026-08-04): si este frame
                # exacto no quedo en la captura (no deberia pasar dado que
                # _cap_end_frame cubre todo el rango, pero por las dudas),
                # usar el frame capturado MAS CERCANO en vez de caer al
                # "else" de abajo -- ese "else" es _pose_at_frame(abs_f),
                # que mas alla del ultimo waypoint real devuelve SIEMPRE
                # el valor fijo de la ultima pose (d_end), es decir
                # exactamente el "queda pegado en la ultima pose" que se
                # queria evitar. Con esta salvaguarda, un hueco puntual en
                # la captura sigue mostrando caminar (el frame capturado
                # mas proximo) en vez de congelarse en la pose.
                _nearest_f = min(_base_cap_bones.keys(), key=lambda k: abs(k - abs_f))
                pose    = _base_cap_bones[_nearest_f]
                arm_rot = _base_cap_arm_rot.get(_nearest_f, (0.0, 0.0, 0.0))
                arm_pos = _base_cap_arm_pos.get(_nearest_f, (0.0, 0.0, 0.0))
            else:
                pose    = _pose_at_frame(abs_f)
                arm_rot = _arm_rot_at_frame(abs_f)
                arm_pos = _arm_pos_at_frame(abs_f)
            scene.frame_set(abs_f)
            # Bones — los que esten bloqueados en este frame (checkbox simple
            # para todo el segmento, o intervalo de bone_blocks que cubra
            # abs_f — ver _bone_blocked_at arriba) NO reciben la pose del
            # segmento.
            #
            # BUG (reportado por Kebyn, 2026-08-05): "el bloqueador de bones
            # por intervalo de frames no esta funcionando". Causa real: antes
            # se hacia simplemente `continue` -- es decir, NO se insertaba
            # NINGUN keyframe para ese bone en ese frame. Eso deja un hueco
            # en el fcurve, y como los keyframes ANTES y DESPUES del hueco
            # siguen siendo la pose del segmento (con interpolacion BEZIER,
            # ver el loop mas abajo que fuerza kp.interpolation="BEZIER"),
            # Blender interpola suavemente ATRAVESANDO el hueco -- la pose
            # del segmento seguia "filtrandose" visualmente durante todo el
            # intervalo marcado como bloqueado, dando la sensacion de que el
            # bloqueo no hacia nada.
            #
            # Fix: durante un intervalo bloqueado SI se escribe un keyframe,
            # pero con el valor de la animacion base (Capa 1, capturada en
            # _base_cap_bones antes de inyectar las poses) en vez del valor
            # de la pose del segmento -- asi el bone sigue haciendo lo que
            # haria sin este segmento (p.ej. seguir caminando) en lugar de
            # quedar pegado a la pose. Si no hay captura base disponible en
            # ese frame para ese bone (nunca se movio en Capa 1), se usa el
            # rest pose (rot=0, loc=0, scale=1) como ancla neutra. Cualquiera
            # de los dos casos "sella" el hueco y corta la interpolacion
            # bezier que venia arrastrando la pose del segmento.
            for bone_name, bdata in pose.items():
                if _bone_blocked_at(bone_name, abs_f):
                    _base_bdata = _base_cap_bones.get(abs_f, {}).get(bone_name)
                    if _base_bdata is not None:
                        _anchor_rot, _anchor_loc, _anchor_sca = (
                            _base_bdata["rot"], _base_bdata["loc"], _base_bdata["scale"]
                        )
                    else:
                        _anchor_rot, _anchor_loc, _anchor_sca = (
                            (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)
                        )
                    pb = armature.pose.bones.get(bone_name)
                    if pb:
                        pb.rotation_euler = Euler(_anchor_rot, "XYZ")
                        pb.location       = Vector(_anchor_loc)
                        pb.scale          = Vector(_anchor_sca)
                        pb.keyframe_insert(data_path="rotation_euler", frame=abs_f)
                        pb.keyframe_insert(data_path="location",       frame=abs_f)
                        pb.keyframe_insert(data_path="scale",          frame=abs_f)
                    continue
                pb = armature.pose.bones.get(bone_name)
                if pb:
                    pb.rotation_euler = Euler(bdata["rot"], "XYZ")
                    pb.location       = Vector(bdata["loc"])
                    pb.scale          = Vector(bdata["scale"])
                    pb.keyframe_insert(data_path="rotation_euler", frame=abs_f)
                    pb.keyframe_insert(data_path="location",       frame=abs_f)
                    pb.keyframe_insert(data_path="scale",          frame=abs_f)
            # Root object (cerdo_1 / Empty) — se omite si "Armature" esta bloqueado en este frame
            if not _bone_blocked_at("Armature", abs_f):
                root_obj = scene.objects.get("cerdo_1") or armature
                root_obj.rotation_mode = "XYZ"
                root_obj.rotation_euler = Euler(arm_rot, "XYZ")
                root_obj.location       = Vector(arm_pos)
                root_obj.keyframe_insert(data_path="rotation_euler", frame=abs_f)
                root_obj.keyframe_insert(data_path="location",       frame=abs_f)

        abs_frame = end_frame + 1

        if armature.animation_data and armature.animation_data.action:
            for fc in get_fcurves(armature.animation_data.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "BEZIER"
                    kp.easing        = "AUTO"

        # ── Guardar datos de poses configuradas como custom property ─────
        # Se serializa el contenido completo de los fcurves del armature
        # (bones con poses) y del root (cerdo_1 empty) en custom properties
        # del objeto cerdo_1. preview_path los lee y los reinyecta sobre los
        # slots base despues de regenerar la animacion de recorrido.
        import json as _json

        def _fcurves_to_dict(anim_data, skip_dp=None):
            """Serializa los fcurves de un objeto a dict {data_path_index: {frame: value}}.
            skip_dp: conjunto de data_path a omitir (ej: {"location"} para el root).
            """
            if not anim_data or not anim_data.action:
                return {}
            if skip_dp is None:
                skip_dp = set()
            result = {}
            for fc in get_fcurves(anim_data.action):
                if fc.data_path in skip_dp:
                    continue
                key = f"{fc.data_path}[{fc.array_index}]"
                result[key] = {str(int(kp.co.x)): kp.co.y
                               for kp in fc.keyframe_points}
            return result

        _root_obj_for_save = bpy.data.objects.get("cerdo_1")

        _concat_arm_data  = _fcurves_to_dict(armature.animation_data)
        # Para el root solo guardar rotation_euler — la location pertenece
        # al recorrido y no debe ser reinyectada sobre los slots base.
        _concat_root_data = (_fcurves_to_dict(_root_obj_for_save.animation_data,
                                              skip_dp={"location"})
                             if _root_obj_for_save and _root_obj_for_save.animation_data
                             else {})

        # Guardar en custom properties del objeto cerdo_1
        _save_target = _root_obj_for_save or armature
        _save_target["_concat_arm_data"]  = _json.dumps(_concat_arm_data)
        _save_target["_concat_root_data"] = _json.dumps(_concat_root_data)
        _save_target["_concat_frame_start"] = start_frame
        _save_target["_concat_frame_end"]   = end_frame

        # ── Ajustar timeline de la escena SIN reducirlo ───────────────────
        if scene.frame_start > start_frame:
            scene.frame_start = start_frame
        if scene.frame_end < abs_frame - 1:
            scene.frame_end = abs_frame - 1
        scene.frame_set(start_frame)

        # ── Post-proceso: filtros de movimiento organico ──
        # AISLAMIENTO POR SEGMENTO (Kebyn + Claude, 2026-08-03): si este
        # CONCATENAR corresponde a un segmento del Paso 3 (_active_seg_idx
        # resuelto arriba), se usan los filtros organicos PROPIOS de ESE
        # segmento (seg.organic) en vez de los globales de scene.cerdo_1_st.
        # Antes se usaba siempre st.organic -- una unica instancia
        # compartida -- por lo que cambiar un valor en el panel de
        # cualquier segmento terminaba aplicandose a TODOS los segmentos al
        # concatenar. Si el operador se llama sin contexto de segmento
        # (_active_seg_idx is None, uso directo/legacy), se sigue usando
        # st.organic como fallback.
        org = (seg.organic if _active_seg_idx is not None else st.organic)
        if org.enabled:
            _apply_organic_filters(context, armature, start_frame, end_frame, org)

        # ── Post-proceso: Oscilaciones de bones personalizadas ──────────────
        _apply_bone_oscillations(context, armature, st.bone_oscillations)

        # ── Post-proceso: expresiones de ojos y parpadeo ──
        eye_s = st.eye_expr
        if eye_s.enabled:
            # ── Reconstruir shape keys con la configuracion ACTUAL del panel ──
            # BUGFIX (Kebyn + Claude, 2026-08-03: "el parpadeo solo sobrevive
            # en el ultimo segmento al concatenar varios"): build_expression_
            # shape_keys() llama eye_obj.shape_key_clear(), que BORRA TODOS
            # los shape keys de la malla (incluido "Closed", el que usa el
            # Parpadeo automatico) y los recrea desde cero -- junto con su
            # action de animacion. Si esto se ejecuta una vez POR SEGMENTO
            # dentro del loop de "Concatenar segmentos", cada segmento
            # siguiente borra el parpadeo que el segmento anterior acababa
            # de hornear, y solo sobrevive el del ultimo segmento procesado.
            #
            # Cuando este operador corre dentro de un batch de segmentos
            # (_active_seg_idx no es None -- ver CERDO_1SEG_OT_ConcatenateAll),
            # los shape keys ya se reconstruyeron UNA sola vez, antes de
            # empezar el loop, asi que aca se omite para no volver a
            # borrarlos en cada iteracion. Solo se reconstruyen aca cuando
            # el operador corre de forma directa/individual (_active_seg_idx
            # is None), igual que antes.
            if _active_seg_idx is None:
                from .eye_system import build_expression_shape_keys, _get_eye_objects
                _eye_left, _eye_right = _get_eye_objects()
                if _eye_left and _eye_left.type == "MESH":
                    build_expression_shape_keys(_eye_left,  eye_s, is_right_eye=False)
                if _eye_right and _eye_right.type == "MESH":
                    build_expression_shape_keys(_eye_right, eye_s, is_right_eye=True)

            # Aplicar transforms (posicion/rotacion/escala) de las mallas de ojos
            _apply_eye_transforms_from_props(scene, eye_s)

            # Insertar keyframes de shape keys de expresion en el frame indicado
            _apply_eye_expression_keyframe(scene, eye_s, start_frame, end_frame)

        # BUGFIX (Kebyn + Claude, 2026-09-06: "el boton Concatenar
        # segmentos no ejecuta los sistemas de expresiones de cada
        # segmento"): Parpadeo/Reir/Entendiendo/Expresiones por
        # intervalos SALIERON de adentro de "if eye_s.enabled:" --
        # ese toggle ("Activar expresiones de ojos") es el switch
        # del sistema GLOBAL legado (shape keys sin sufijo + transforms
        # + secuencia lineal via _apply_eye_transforms_from_props /
        # _apply_eye_expression_keyframe). Los 4 sistemas por-segmento
        # ya tienen su PROPIO switch independiente (blink_enabled,
        # laugh_enabled, understand_enabled, expr_intervals_enabled),
        # pero al vivir anidados dentro del if de arriba quedaban
        # bloqueados por completo si el usuario tenia el toggle
        # maestro apagado (facil de confundir con "Expresiones por
        # intervalos", que es un switch distinto) -- resultado:
        # "Concatenar segmentos" no ejecutaba ninguno de los 4
        # sistemas por segmento aunque cada uno estuviera configurado
        # y habilitado individualmente.
        # Parpadeo automatico
        if eye_s.blink_enabled:
            # AISLAMIENTO POR SEGMENTO: los intervalos de parpadeo (bi)
            # se toman de la coleccion PROPIA de este segmento
            # (seg.blink_intervals) cuando hay contexto de segmento, en
            # vez de la global scene.cerdo_1_st.blink_intervals. Antes, al
            # ser una unica lista global compartida, CADA segmento
            # concatenado insertaba el mismo patron de parpadeo
            # (mismo rango/cantidad/duracion) sin importar cual
            # segmento se hubiera editado por ultimo.
            _blink_cont = seg if _active_seg_idx is not None else st
            if _blink_cont.blink_intervals:
                bi = _blink_cont.blink_intervals[
                    min(_blink_cont.blink_interval_idx, len(_blink_cont.blink_intervals) - 1)
                ]
                if bi.enabled:
                    apply_blink_sequence(
                        bi.frame_start, bi.frame_end,
                        bi.blink_count, bi.blink_duration,
                    )
            else:
                # Fallback legacy (campo "count" del JSON)
                apply_blink_sequence(start_frame, end_frame,
                                      eye_s.blink_count, eye_s.blink_duration)

        # Filtro "Reir" -- oscilacion vertical sincronizada de ojos
        # (Kebyn, 2026-08-18). A diferencia de Parpadeo (que solo
        # aplica el intervalo ACTIVO en la UI, comportamiento heredado
        # de mas arriba), aca se recorren TODOS los intervalos
        # habilitados de seg.laugh_intervals -- cada uno tiene su
        # propio frame_start/frame_end explicito (no se encadenan como
        # expr_intervals), asi que no hay ambiguedad en aplicarlos
        # todos: cada uno controla su propio rango de la timeline.
        if eye_s.laugh_enabled and _active_seg_idx is not None:
            for li in seg.laugh_intervals:
                if li.enabled:
                    apply_laugh_sequence(
                        li.frame_start, li.frame_end, li.oscillation_count,
                    )

        # Filtro "Entendiendo" -- glance parabolico sincronizado de
        # ojos (Kebyn, 2026-08-18). Mismo criterio que "Reir" arriba:
        # se recorren TODOS los intervalos habilitados de
        # seg.understand_intervals, cada uno con su propio
        # frame_start/frame_end/direction explicito.
        if eye_s.understand_enabled and _active_seg_idx is not None:
            for ui in seg.understand_intervals:
                if ui.enabled:
                    apply_understand_sequence(
                        ui.frame_start, ui.frame_end, ui.direction,
                    )

        # Expresiones de ojos por intervalos
        # AISLAMIENTO POR SEGMENTO (Kebyn + Claude, 2026-08-04): mismo
        # criterio que el bloque de Parpadeo automatico de arriba. Los
        # intervalos de expresion (ei) se toman de la coleccion PROPIA
        # de este segmento (seg.expr_intervals) cuando hay contexto de
        # segmento, en vez de la global scene.cerdo_1_st.expr_intervals.
        # ANTES, al ser una unica lista global compartida, agregar o
        # quitar una expresion en el panel de UN segmento se reflejaba
        # en TODOS los segmentos concatenados, sin importar cual se
        # hubiera editado por ultimo.
        if eye_s.expr_intervals_enabled:
            _expr_cont = seg if _active_seg_idx is not None else st
            active_expr_intervals_idx = [
                (idx, ei) for idx, ei in enumerate(_expr_cont.expr_intervals) if ei.enabled
            ]
            if active_expr_intervals_idx:
                from .eye_system import (
                    apply_expression_to_eye as _apply_expr_seg,
                    build_expression_shape_keys as _build_sk_seg,
                )
                _left_eye  = bpy.data.objects.get("ojo_izquierdo_cerdo_1")
                _right_eye = bpy.data.objects.get("ojo_derecho_cerdo_1")
                # AISLAMIENTO POR SEGMENTO (Kebyn + Claude, 2026-08-05):
                # cuando hay contexto de segmento, genera su propio juego
                # de shape keys ("Feliz__seg<idx>", etc.) con su config
                # PROPIA (seg.eye_shapekey), en vez de reusar el juego
                # global sin sufijo -- asi cambiar Zona/Curva/etc. en
                # este segmento no afecta a los demas ni al panel global
                # "2b Secuencia de Ojos". Fuera de contexto de segmento
                # (uso directo/legacy) se mantiene el juego global.
                _seg_sk_suffix = f"__seg{_active_seg_idx}" if _active_seg_idx is not None else ""
                if _seg_sk_suffix and _left_eye and _right_eye:
                    from .properties import ensure_expr_interval_shapekey_independent as _ensure_ei_sk_indep
                    ensure_eye_shapekey_migrated(seg, scene)
                    _ensure_ei_sk_indep(seg)

                # MODO COMPARTIDO ELIMINADO (Kebyn, 2026-09-05: "cada
                # setup de shape keys de ojos debe ser independiente
                # para cada expresion... que no sea para todas las
                # expresiones de la lista"): ANTES, una expresion sin
                # use_own_shapekey activado caia en el juego COMPARTIDO
                # del segmento (seg.eye_shapekey / _seg_sk_suffix). Ya
                # no hay fallback compartido -- TODA expresion usa
                # siempre su propio juego, con sufijo unico por
                # expresion ("__seg<idx>_ei<n>"). La migracion de
                # valores efectivos (para no cambiar el aspecto de
                # expresiones ya existentes) la hace
                # ensure_expr_interval_shapekey_independent() arriba.
                _built_sk_suffixes = set()

                def _resolve_ei_shapekey(_ei, _ei_idx):
                    return _ei.own_shapekey, f"{_seg_sk_suffix}_ei{_ei_idx}"

                if _left_eye and _right_eye:
                    # BUGFIX (Kebyn, 2026-09-05: "no limpia despues de
                    # apretar concatenar segmento... quedan residuos de
                    # la configuracion anterior que se solapan con los
                    # nuevos valores"): antes de insertar la secuencia
                    # de este segmento, se borran los keyframes que haya
                    # dejado una corrida ANTERIOR de "Expresiones de
                    # ojos" en el mismo rango [start_frame, end_frame]
                    # de este segmento -- si no, editar/agregar/quitar
                    # entradas de la lista corre los frames de la nueva
                    # secuencia pero deja los keyframes viejos en sus
                    # posiciones originales, solapados con los nuevos.
                    # Nota: suffix_filter usa coincidencia por
                    # substring, asi que "__seg2" ya cubre tanto
                    # "Feliz__seg2" (juego compartido) como
                    # "Feliz__seg2_ei0" (shape key propio de una
                    # expresion con use_own_shapekey) en un solo pase.
                    from .eye_system import _clear_expression_keyframes_in_range as _clear_expr_seg
                    _clear_suffix = _seg_sk_suffix if _active_seg_idx is not None else ""
                    for _eye_obj in (_left_eye, _right_eye):
                        _clear_expr_seg(_eye_obj, start_frame, end_frame, suffix_filter=_clear_suffix)

                    # FRAME DE INICIO ABSOLUTO (Kebyn, 2026-09-06): mismo
                    # criterio que resolve_pose_start_frames ya usa para
                    # las poses de accion -- respeta ei.manual_start (si el
                    # usuario fijo un frame de inicio y no invade a la
                    # expresion anterior, se usa tal cual); el resto se
                    # sigue encadenando automaticamente como siempre. El
                    # resultado se escribe en ei.frame_abs_start para que
                    # el panel lo muestre.
                    _active_eis = [ei for _idx, ei in active_expr_intervals_idx]
                    _resolved_ei_starts = resolve_pose_start_frames(_active_eis, start_frame)
                    for ei, _fs in zip(_active_eis, _resolved_ei_starts):
                        ei.frame_abs_start = _fs

                    for _ei_idx, ei in active_expr_intervals_idx:
                        _ei_settings, _ei_suffix = _resolve_ei_shapekey(ei, _ei_idx)
                        if _ei_suffix and _ei_suffix not in _built_sk_suffixes:
                            _build_sk_seg(_left_eye,  _ei_settings, is_right_eye=False, name_suffix=_ei_suffix)
                            _build_sk_seg(_right_eye, _ei_settings, is_right_eye=True,  name_suffix=_ei_suffix)
                            _built_sk_suffixes.add(_ei_suffix)

                        _expr_name = ei.expression.lower()
                        _val       = ei.expression_value
                        _f_start   = ei.frame_abs_start
                        _f_end     = _f_start + ei.duration - 1
                        _f_peak    = _f_start + ei.duration // 2
                        if _left_eye.data.shape_keys and _right_eye.data.shape_keys:
                            for _eye_obj in (_left_eye, _right_eye):
                                from .eye_system import apply_expression_interval
                                apply_expression_interval(_eye_obj, _expr_name, _val, _f_start, _f_end, name_suffix=_ei_suffix)

                        # FIX (2026-08-05): este operador es el que
                        # realmente procesa los segmentos CON pose de
                        # accion superpuesta (ej. "02_parada"), pero el
                        # bloque de arriba solo replicaba la intensidad
                        # del shape key -- igual que le pasaba a la rama
                        # "sin pose" de operators_segments.py -- y se
                        # olvidaba de la Posicion/Rotacion/Escala por ojo
                        # que si tiene CERDO_1_ST_OT_Concatenate2 (sistema
                        # global). Resultado: los valores editados en
                        # "Editar expresion de ojos" (loc/rot/sca) se
                        # guardaban bien en expr_intervals pero nunca se
                        # insertaban como keyframes -- Scale X se quedaba
                        # en el valor base (1.555) sin importar lo que se
                        # editara en el popup.
                        _base_L = EYE_BASE_TRANSFORMS.get("ojo_izquierdo_cerdo_1", {})
                        _base_R = EYE_BASE_TRANSFORMS.get("ojo_derecho_cerdo_1",   {})
                        _peak_L = {
                            "loc": (ei.eye_L_loc_x, ei.eye_L_loc_y, ei.eye_L_loc_z),
                            "rot": (ei.eye_L_rot_x, ei.eye_L_rot_y, ei.eye_L_rot_z),
                            "sca": (ei.eye_L_sca_x, ei.eye_L_sca_y, ei.eye_L_sca_z),
                        }
                        _peak_R = {
                            "loc": (ei.eye_R_loc_x, ei.eye_R_loc_y, ei.eye_R_loc_z),
                            "rot": (ei.eye_R_rot_x, ei.eye_R_rot_y, ei.eye_R_rot_z),
                            "sca": (ei.eye_R_sca_x, ei.eye_R_sca_y, ei.eye_R_sca_z),
                        }

                        def _keyframe_eye_transform_seg(obj, td, frame):
                            obj.location       = td["loc"]
                            obj.rotation_euler = td["rot"]
                            obj.scale          = td["sca"]
                            obj.keyframe_insert(data_path="location",       frame=frame)
                            obj.keyframe_insert(data_path="rotation_euler", frame=frame)
                            obj.keyframe_insert(data_path="scale",          frame=frame)

                        if _base_L and _base_R:
                            _keyframe_eye_transform_seg(_left_eye,  _base_L, _f_start)
                            _keyframe_eye_transform_seg(_right_eye, _base_R, _f_start)
                            _keyframe_eye_transform_seg(_left_eye,  _peak_L, _f_peak)
                            _keyframe_eye_transform_seg(_right_eye, _peak_R, _f_peak)
                            _keyframe_eye_transform_seg(_left_eye,  _base_L, _f_end)
                            _keyframe_eye_transform_seg(_right_eye, _base_R, _f_end)

        st.anim_generated   = True
        st.total_frames_gen = total_gen
        st.end_frame_gen    = abs_frame - 1

        # ── Ejecutar importacion de objetos (escudo, espada, etc.) ─────────────
        # Si hay un segmento activo, solo se procesan los items vinculados a
        # ese segmento (item.segment_idx == _active_seg_idx) o los globales
        # (item.segment_idx == -1). Si no hay segmento activo, se procesan
        # todos los items (comportamiento legacy).
        _oi_summary = ""
        try:
            _n_imp, _n_skip, _oi_errors = _oiu_preview.run_object_imports_live(
                context.scene, segment_idx=_active_seg_idx
            )
            _oi_summary = f"objetos: {_n_imp} importados / {_n_skip} omitidos"
            for _e in _oi_errors:
                print(f"[CERDO_1_ST_Concatenate] {_e}")
        except Exception as _e_oi:
            import traceback
            print("[CERDO_1_ST_Concatenate] Error en importacion de objetos:")
            print(traceback.format_exc())
            _oi_summary = f"objetos: ERROR ({_e_oi})"

        # ── Ejecutar Lanzar / Recoger Objetos ─────────────────────────────────
        # (logica real vive en run_throws_for_segments(), reutilizada tambien
        # por CERDO_1SEG_OT_ConcatenateAll para segmentos sin poses -- ver
        # operators_segments.py)
        segs = context.scene.cerdo_1_segs.segments
        # Procesar el segmento activo (o todos si no hay segmento activo)
        seg_range = ([segs[_active_seg_idx]] if _active_seg_idx is not None
                     and _active_seg_idx < len(segs)
                     else list(segs))
        _throw_imported, _throw_applied, _throw_errors = run_throws_for_segments(context, seg_range)
        _throw_summary = ""
        if _throw_imported or _throw_applied:
            _throw_summary = (f"throw: {_throw_imported} importados / "
                              f"{_throw_applied} trayectorias aplicadas")
        elif _throw_errors:
            _throw_summary = f"throw: ERROR ({_throw_errors[0]})"

        # ── Ejecutar Invisibilidad de Malla ────────────────────────────────────
        # Debajo de Lanzar / Recoger / Mantener (mismo criterio de
        # organizacion que el resto del bloque): se ejecuta para el mismo
        # seg_range ya calculado arriba.
        _hide_applied, _hide_errors = run_hide_mesh_for_segments(context, seg_range)
        _hide_summary = ""
        if _hide_applied:
            _hide_summary = f"invisibilidad: {_hide_applied} malla(s) aplicadas"
        elif _hide_errors:
            _hide_summary = f"invisibilidad: ERROR ({_hide_errors[0]})"

        # ── AISLAMIENTO TOTAL DE SEGMENTOS: empujar a NLA propia ───────────
        # Se hace ACA, despues de todo el post-proceso (filtros organicos,
        # oscilaciones, ojos, importacion de objetos, throws) para que esos
        # pasos sigan operando sobre "la action activa" tal como siempre —
        # solo al final se saca esa action de en medio y se deja viviendo
        # en su propia pista NLA, acotada exactamente a [start_frame,
        # end_frame] con extrapolation='NOTHING'. Fuera de ese rango la
        # pista no aporta NADA (ni mantiene el ultimo valor), asi que otro
        # segmento no puede heredar nada de este ni viceversa.
        if self.isolate_segments:
            _seg_label = "seg"
            _seg_idx_for_name = self.seg_idx if self.seg_idx >= 0 else 0
            if segs_data is not None and _segs_list and 0 <= _resolved_idx < len(_segs_list):
                _seg_label = _segs_list[_resolved_idx].label or "seg"
            _safe_label  = "".join(c if c.isalnum() else "_" for c in _seg_label)[:32]
            _track_base  = f"ALFSEG_{_seg_idx_for_name:02d}_{_safe_label}"

            def _push_isolated(obj, track_name):
                """Empuja la action activa de `obj` a una pista NLA nueva y
                dedicada, acotada a start_frame->end_frame, sin extrapolar
                hacia afuera. Deja obj.animation_data.action = None."""
                if obj is None or not obj.animation_data or not obj.animation_data.action:
                    return
                act = obj.animation_data.action
                if not get_fcurves(act):
                    # Segmento que no toco ningun canal de este objeto (ej.
                    # todos sus bones bloqueados) -- no hay nada que empujar.
                    obj.animation_data.action = None
                    bpy.data.actions.remove(act)
                    return
                act.name = track_name
                track = obj.animation_data.nla_tracks.new()
                track.name = track_name
                strip = track.strips.new(track_name, int(start_frame), act)
                # use_sync_length=False para poder fijar frame_start/frame_end
                # y action_frame_start/action_frame_end de forma explicita sin
                # que Blender recalcule uno en funcion del otro.
                strip.use_sync_length    = False
                strip.action_frame_start = start_frame
                strip.action_frame_end   = end_frame
                strip.frame_start        = start_frame
                strip.frame_end          = end_frame
                strip.extrapolation      = 'NOTHING'
                strip.blend_type         = 'REPLACE'
                obj.animation_data.action = None

            _push_isolated(armature,       _track_base + "_arm")
            _push_isolated(_root_cleanup,  _track_base + "_root")

            # BUGFIX (Kebyn + Claude, 2026-09-11 sexies: "el gesto de brazo
            # 'hacia la espalda' no se reproduce en Mantener/Lanzar/Recoger
            # cuando el segmento SI tiene poses"): run_throws_for_segments()
            # (mas arriba, linea ~2089) ya corria ANTES de este bloque, asi
            # que su pista NLA "ALFTHROW_reach_*" (creada por
            # apply_pre_throw_reach_back(), ver operators_anim.py) quedaba
            # agregada al stack de NLA del armature ANTES que la pista
            # "ALFSEG_..._arm" que se acaba de crear arriba en
            # _push_isolated(). Blender evalua las NLA tracks de abajo hacia
            # arriba segun su ORDEN DE CREACION -- la ultima creada queda
            # arriba del stack. Con blend_type='REPLACE' en ambas pistas y
            # rangos de frames solapados (el gesto siempre vive DENTRO del
            # rango del item, que a su vez vive dentro del segmento), la
            # pista "ALFSEG_..._arm" (el cuerpo completo del segmento,
            # creada despues) tapaba por completo la pista del gesto
            # (creada antes) en cualquier frame donde ambas se solaparan --
            # el brazo nunca se veia ir hacia la espalda, aunque los
            # keyframes del gesto existieran y fueran correctos.
            #
            # Fix: despues de aislar el cuerpo del segmento, se reapilan las
            # pistas "ALFTHROW_reach_*" del armature al TOPE del stack --
            # se capturan sus parametros de strip, se elimina la pista vieja
            # y se recrea (nla_tracks.new() siempre agrega al final/arriba),
            # preservando el mismo rango/accion/extrapolacion. Asi el gesto
            # queda garantizado por encima del cuerpo del segmento sin
            # importar el orden en que se hayan generado ambas pistas.
            def _restack_reach_tracks_on_top(obj):
                if obj is None or not obj.animation_data:
                    return
                _tracks_to_restack = [
                    t for t in obj.animation_data.nla_tracks
                    if t.name.startswith("ALFTHROW_reach_")
                ]
                for _old_track in _tracks_to_restack:
                    if not _old_track.strips:
                        obj.animation_data.nla_tracks.remove(_old_track)
                        continue
                    _old_strip = _old_track.strips[0]
                    _params = dict(
                        name               = _old_track.name,
                        action             = _old_strip.action,
                        frame_start        = _old_strip.frame_start,
                        frame_end          = _old_strip.frame_end,
                        action_frame_start = _old_strip.action_frame_start,
                        action_frame_end   = _old_strip.action_frame_end,
                        extrapolation      = _old_strip.extrapolation,
                        blend_type         = _old_strip.blend_type,
                    )
                    obj.animation_data.nla_tracks.remove(_old_track)
                    _new_track = obj.animation_data.nla_tracks.new()
                    _new_track.name = _params["name"]
                    _new_strip = _new_track.strips.new(
                        _params["name"], int(_params["frame_start"]), _params["action"])
                    _new_strip.use_sync_length    = False
                    _new_strip.action_frame_start = _params["action_frame_start"]
                    _new_strip.action_frame_end   = _params["action_frame_end"]
                    _new_strip.frame_start        = _params["frame_start"]
                    _new_strip.frame_end          = _params["frame_end"]
                    _new_strip.extrapolation      = _params["extrapolation"]
                    _new_strip.blend_type         = _params["blend_type"]

            _restack_reach_tracks_on_top(armature)

        st.status_msg = (
            f"OK  {total_gen} frames  [{start_frame} - {abs_frame-1}]  "
            f"poses={len(action_items)}  "
            f"entrada={entry_ratio:.0%}  salida={exit_ratio:.0%}"
            + ("  [filtros ON]" if org.enabled else "")
            + (f"  |  {_oi_summary}" if _oi_summary else "")
            + (f"  |  {_throw_summary}" if _throw_summary else "")
            + (f"  |  {_hide_summary}" if _hide_summary else "")
        )
        self.report({"INFO"}, st.status_msg)

        # ── Reproducir este segmento de inmediato ──────────────────────────
        # CONCATENAR ya no solo inyecta: salta al frame de inicio del
        # segmento y reproduce hasta su frame final, para ver/escuchar el
        # resultado sin un segundo click en otro boton. Se puede repetir
        # cuantas veces se quiera despues de agregar o quitar poses.
        #
        # IMPORTANTE: el rango de reproduccion tiene que ser el rango
        # MARCADO del segmento (seg.frame_start / seg.frame_end, el que se
        # ve en el panel — ej. 182->428), NO el rango que sale de sumar las
        # duraciones de las poses de este operador (start_frame/abs_frame-1):
        # en modo recorrido la duracion la manda el recorrido (Paso 2), no
        # la suma de poses, y ambos numeros pueden no coincidir. Ademas hay
        # que ASIGNAR el rango de la escena (no solo extenderlo) — si la
        # escena venia con un rango mas ancho (ej. el recorrido completo
        # 1->1119 de "Reproducir recorrido"), extender nunca lo achicaba y
        # terminaba reproduciendose sobre ese rango viejo desde el frame 1.
        if self.auto_play:
            _play_f_start, _play_f_end = start_frame, abs_frame - 1
            _segs_for_play = getattr(context.scene, "cerdo_1_segs", None)
            if _segs_for_play is not None and _active_seg_idx is not None:
                _seg_play = _segs_for_play.segments[_active_seg_idx]
                if _seg_play.frame_end > _seg_play.frame_start:
                    _play_f_start = _seg_play.frame_start
                    _play_f_end   = _seg_play.frame_end

            scene.frame_start = _play_f_start
            scene.frame_end   = _play_f_end

            if context.screen.is_animation_playing:
                bpy.ops.screen.animation_play()
            scene.frame_set(_play_f_start)

            def _deferred_play():
                if not bpy.context.screen.is_animation_playing:
                    bpy.ops.screen.animation_play()
                return None
            bpy.app.timers.register(_deferred_play, first_interval=0.01)

        return {"FINISHED"}

# =============================================================================
# HELPER: serializar secuencia completa de ojos para el .py exportado
# =============================================================================

def _build_eye_sequence_data_code(st):
    """
    Genera el bloque de codigo Python que define EYE_SEQUENCE_DATA en el .py exportado.
    Incluye: estado inicio, slots intermedios, estado fin y configuracion de parpadeo.
    Compatible con execute_animation() para reproduccion automatica al importar.
    """
    eye_s = st.eye_expr

    def _eye_transforms_dict(prefix, src):
        """Serializa loc/rot/sca de ambos ojos desde un objeto fuente con prefijo."""
        return {
            "loc": (round(getattr(src, f"{prefix}_L_loc_x"), 6),
                    round(getattr(src, f"{prefix}_L_loc_y"), 6),
                    round(getattr(src, f"{prefix}_L_loc_z"), 6)),
            "rot": (round(getattr(src, f"{prefix}_L_rot_x"), 6),
                    round(getattr(src, f"{prefix}_L_rot_y"), 6),
                    round(getattr(src, f"{prefix}_L_rot_z"), 6)),
            "sca": (round(getattr(src, f"{prefix}_L_sca_x"), 4),
                    round(getattr(src, f"{prefix}_L_sca_y"), 4),
                    round(getattr(src, f"{prefix}_L_sca_z"), 4)),
        }, {
            "loc": (round(getattr(src, f"{prefix}_R_loc_x"), 6),
                    round(getattr(src, f"{prefix}_R_loc_y"), 6),
                    round(getattr(src, f"{prefix}_R_loc_z"), 6)),
            "rot": (round(getattr(src, f"{prefix}_R_rot_x"), 6),
                    round(getattr(src, f"{prefix}_R_rot_y"), 6),
                    round(getattr(src, f"{prefix}_R_rot_z"), 6)),
            "sca": (round(getattr(src, f"{prefix}_R_sca_x"), 4),
                    round(getattr(src, f"{prefix}_R_sca_y"), 4),
                    round(getattr(src, f"{prefix}_R_sca_z"), 4)),
        }

    def _slot_item_dict(item):
        """Convierte un Cerdo_1EyeSlotItem a dict serializable."""
        eye_L, eye_R = _eye_transforms_dict("eye", item)
        return {
            "slot_label":         item.slot_label,
            "duration":           item.duration,
            "interp_type":        item.interp_type,
            "active_expression":  item.active_expression,
            "expression_value":   round(item.expression_value, 3),
            "geo_edit_mode":      item.geo_edit_mode,
            "geo_intensity":      round(item.geo_intensity, 3),
            "eye_L":              eye_L,
            "eye_R":              eye_R,
        }

    # Estado inicio
    eye_start_L, eye_start_R = _eye_transforms_dict("eye_start", st)
    start_state = {
        "duration":           st.eye_start_duration,
        "interp_type":        st.eye_start_interp,
        "blink_mode":         st.eye_start_blink_mode,
        "blink_count":        st.eye_start_blink_count,
        "blink_duration":     st.eye_start_blink_duration,
        "active_expression":  st.eye_start_expression,
        "expression_value":   round(st.eye_start_expr_value, 3),
        "eye_L":              eye_start_L,
        "eye_R":              eye_start_R,
    }

    # Slots intermedios
    slots_list = [_slot_item_dict(item) for item in st.eye_slots]

    # Estado fin
    eye_end_L, eye_end_R = _eye_transforms_dict("eye_end", st)
    end_state = {
        "duration":           st.eye_end_duration,
        "interp_type":        st.eye_end_interp,
        "blink_mode":         st.eye_end_blink_mode,
        "blink_count":        st.eye_end_blink_count,
        "blink_duration":     st.eye_end_blink_duration,
        "active_expression":  st.eye_end_expression,
        "expression_value":   round(st.eye_end_expr_value, 3),
        "eye_L":              eye_end_L,
        "eye_R":              eye_end_R,
    }

    # Configuracion global de ojos y parpadeo automatico

    def _serialize_eye_axes():
        """Lee los ejes h/v de los objetos ojo en la escena y los serializa."""
        import bpy as _bpy
        result = {
            "eye_L_h_axis": "x", "eye_L_v_axis": "z",
            "eye_R_h_axis": "x", "eye_R_v_axis": "z",
        }
        for side, name in (("L", "ojo_izquierdo_cerdo_1"), ("R", "ojo_derecho_cerdo_1")):
            obj = _bpy.data.objects.get(name)
            if not (obj and obj.type == "MESH" and obj.data.vertices):
                continue
            verts = obj.data.vertices
            xs = [v.co.x for v in verts]
            ys = [v.co.y for v in verts]
            zs = [v.co.z for v in verts]
            ranges = {
                "x": max(xs) - min(xs),
                "y": max(ys) - min(ys),
                "z": max(zs) - min(zs),
            }
            priority = {"x": 2, "z": 1, "y": 0}
            sorted_axes = sorted(
                ranges.items(),
                key=lambda i: (round(i[1], 6), priority[i[0]])
            )
            h_axis = sorted_axes[2][0]
            v_axis = sorted_axes[1][0]
            if eye_s.swap_axes:
                h_axis, v_axis = v_axis, h_axis
            result[f"eye_{side}_h_axis"] = h_axis
            result[f"eye_{side}_v_axis"] = v_axis
        return result

    global_cfg = {
        "enabled":            eye_s.enabled,
        "global_start_frame": st.eye_global_start_frame,
        "blink_enabled":      eye_s.blink_enabled,
        "blink_count":        eye_s.blink_count,
        "blink_duration":     eye_s.blink_duration,
        "blink_frame_start":  eye_s.blink_frame_start,
        "blink_frame_end":    eye_s.blink_frame_end,
        # Intervalos de parpadeo (sistema nuevo): se serializa la lista completa
        # para que _apply_eye_sequence_from_data use blink_count correcto al importar.
        "blink_interval_idx": st.blink_interval_idx,
        "blink_intervals": [
            {
                "label":          bi.label,
                "frame_start":    bi.frame_start,
                "frame_end":      bi.frame_end,
                "blink_count":    bi.blink_count,
                "blink_duration": bi.blink_duration,
                "enabled":        bi.enabled,
            }
            for bi in st.blink_intervals
        ],
        "curve_mode":         eye_s.curve_mode,
        "affect_zone":        eye_s.affect_zone,
        "intensity_feliz":    round(eye_s.intensity_feliz, 4),
        "intensity_triste":   round(eye_s.intensity_triste, 4),
        "intensity_enojado":  round(eye_s.intensity_enojado, 4),
        "intensity_sospecha": round(eye_s.intensity_sospecha, 4),
        # Parametros para construccion de shape keys de expresion en .py exportado
        "invert_vertical":    eye_s.invert_vertical,
        "invert_horizontal":  eye_s.invert_horizontal,
        "swap_axes":          eye_s.swap_axes,
        "subdivide_cuts":     eye_s.subdivide_cuts,
        # Ejes reales de los objetos ojo leidos en tiempo de exportacion.
        # Garantizan que el .py reconstruya shape keys con la misma orientacion
        # que tiene la escena, independientemente del estado de la malla en runtime.
        **_serialize_eye_axes(),
    }

    import json as _json

    data = {
        "global": global_cfg,
        "start":  start_state,
        "slots":  slots_list,
        "end":    end_state,
    }
    serialized = _json.dumps(data, indent=4, ensure_ascii=False)

    lines = [
        "# ============================================",
        "# SECUENCIA COMPLETA DE OJOS (panel 2b)",
        "# Incluye: inicio, slots intermedios, fin y parpadeo.",
        "# Se aplica automaticamente al importar con execute_animation().",
        "# ============================================",
        "",
        "import json as _json_eye",
        f"EYE_SEQUENCE_DATA = _json_eye.loads({repr(serialized)})",
        "",
        "# ============================================",
        "# FIN DE SECUENCIA DE OJOS",
        "# ============================================",
    ]
    return "\n".join(lines)


def _build_eye_base_mesh_data_code(eye_s):
    """
    Serializa las coordenadas de vertices de los ojos EN EL MOMENTO DE EXPORTAR,
    despues de que la malla ya fue subdividida con el subdivide_cuts correcto.
    Esto permite que _build_expr_shape_keys en el .py reproducido siempre
    restaure la geometria base exacta, sin depender del estado de la malla
    en la escena del reproductor (que puede tener mas o menos vertices).
    """
    import bpy as _bpy
    import json as _json

    result = {"eye_L": None, "eye_R": None, "subdivide_cuts": eye_s.subdivide_cuts}

    for side, obj_name in (("eye_L", "ojo_izquierdo_cerdo_1"), ("eye_R", "ojo_derecho_cerdo_1")):
        obj = _bpy.data.objects.get(obj_name)
        if not (obj and obj.type == "MESH"):
            continue
        # Asegurar que la malla tiene la subdivision correcta antes de capturar
        from .eye_system import _eye_ensure_subdivided
        _eye_ensure_subdivided(obj, eye_s.subdivide_cuts)
        # Serializar coordenadas base (Basis o malla actual sin shape keys activos)
        verts = []
        for v in obj.data.vertices:
            co = v.co
            # Si hay shape keys, usar las coords del Basis
            if obj.data.shape_keys:
                basis = obj.data.shape_keys.key_blocks.get("Basis")
                if basis:
                    co = basis.data[v.index].co
            verts.append((round(co.x, 6), round(co.y, 6), round(co.z, 6)))
        result[side] = verts

    serialized = _json.dumps(result, separators=(",", ":"))
    lines = [
        "# ============================================",
        "# GEOMETRIA BASE DE MALLAS DE OJOS",
        "# Coordenadas capturadas en exportacion con subdivide_cuts aplicado.",
        "# Garantiza reproduccion identica independientemente del estado",
        "# de la malla en la escena del reproductor.",
        "# ============================================",
        "",
        "import json as _json_eye_base",
        f"EYE_BASE_MESH_DATA = _json_eye_base.loads({repr(serialized)})",
        "",
    ]
    return "\n".join(lines)


# =============================================================================
# HELPER: aplicar EYE_SEQUENCE_DATA desde un .py importado
# =============================================================================

def _apply_eye_sequence_from_data(scene, eye_seq_data, start_frame, end_frame):
    """
    Aplica keyframes de ojos desde EYE_SEQUENCE_DATA exportado.
    Reproduce la secuencia: inicio -> slots intermedios -> fin,
    incluyendo loc/rot/sca de mallas y parpadeo automatico.
    """
    import math as _math
    from .eye_system import apply_blink_sequence

    global_cfg = eye_seq_data.get("global", {})
    if not global_cfg.get("enabled", False):
        return

    eye_global_start = global_cfg.get("global_start_frame", start_frame)

    # ── Reconstruir shape keys con la configuracion del archivo exportado ──
    # Usa los valores serializados en 'global' (subdivide_cuts, affect_zone,
    # invert_vertical, invert_horizontal, swap_axes) para garantizar que
    # la geometria de los shape keys sea identica a la del archivo original.
    try:
        from .eye_system import _get_eye_objects, _eye_ensure_subdivided, _eye_detect_axes, _eye_compute_vertex
        import types as _types

        # Construir un objeto settings temporal a partir del dict global_cfg
        _cfg_ns = _types.SimpleNamespace(
            subdivide_cuts     = global_cfg.get("subdivide_cuts",    3),
            affect_zone        = global_cfg.get("affect_zone",       "UPPER"),
            invert_vertical    = global_cfg.get("invert_vertical",   True),
            invert_horizontal  = global_cfg.get("invert_horizontal", False),
            swap_axes          = global_cfg.get("swap_axes",         False),
            curve_mode         = global_cfg.get("curve_mode",        "QUADRATIC"),
            intensity_feliz    = global_cfg.get("intensity_feliz",   0.18),
            intensity_triste   = global_cfg.get("intensity_triste",  0.18),
            intensity_enojado  = global_cfg.get("intensity_enojado", 0.18),
            intensity_sospecha = global_cfg.get("intensity_sospecha",0.18),
        )

        from .eye_system import build_expression_shape_keys
        _eye_left_r, _eye_right_r = _get_eye_objects()
        if _eye_left_r and _eye_left_r.type == "MESH":
            build_expression_shape_keys(_eye_left_r,  _cfg_ns, is_right_eye=False)
        if _eye_right_r and _eye_right_r.type == "MESH":
            build_expression_shape_keys(_eye_right_r, _cfg_ns, is_right_eye=True)
    except Exception as _ske:
        import traceback
        print(f"[cerdo_1_eye] Advertencia: no se pudieron reconstruir shape keys: {_ske}")
        traceback.print_exc()

    EYE_OBJS = ["ojo_izquierdo_cerdo_1", "ojo_derecho_cerdo_1"]
    EYE_EXPR_NAMES = ["enojado", "feliz", "triste", "sospecha"]

    def _apply_expr_shape_keys(frame, expr_name, expr_val, interp="LINEAR"):
        """Escribe keyframes de shape keys de expresion para el frame dado."""
        is_neutral = (not expr_name) or expr_name.lower() == "neutral"
        kf_interp = "CONSTANT" if is_neutral else interp
        for obj_name in EYE_OBJS:
            obj = scene.objects.get(obj_name)
            if not (obj and obj.data.shape_keys):
                continue
            for sk in obj.data.shape_keys.key_blocks:
                if sk.name == "Basis" or sk.name == "Closed":
                    continue
                if is_neutral:
                    sk.value = 0.0
                else:
                    sk.value = expr_val if sk.name.lower() == expr_name.lower() else 0.0
                sk.keyframe_insert(data_path="value", frame=frame)
            # Forzar interpolacion correcta en los keyframes recien insertados
            if obj.data.shape_keys.animation_data and obj.data.shape_keys.animation_data.action:
                for fc in get_fcurves(obj.data.shape_keys.animation_data.action):
                    for kp in fc.keyframe_points:
                        if abs(kp.co.x - frame) < 0.5:
                            kp.interpolation = kf_interp

    # ── Anclas NEUTRAL con interpolacion CONSTANT ──
    # Previene extrapolacion Bezier de expresiones fuera del intervalo asignado
    for obj_name in EYE_OBJS:
        obj = scene.objects.get(obj_name)
        if not (obj and obj.data.shape_keys):
            continue
        for sk in obj.data.shape_keys.key_blocks:
            if sk.name == "Basis" or sk.name == "Closed":
                continue
            sk.value = 0.0
            sk.keyframe_insert(data_path="value", frame=start_frame)
            if eye_global_start > start_frame:
                sk.keyframe_insert(data_path="value", frame=eye_global_start - 1)
            sk.keyframe_insert(data_path="value", frame=end_frame)
        # Forzar CONSTANT en todos los keyframes de ancla
        if obj.data.shape_keys.animation_data and obj.data.shape_keys.animation_data.action:
            for fc in get_fcurves(obj.data.shape_keys.animation_data.action):
                for kp in fc.keyframe_points:
                    for _af in [start_frame, eye_global_start - 1, end_frame]:
                        if abs(kp.co.x - _af) < 0.5:
                            kp.interpolation = "CONSTANT"

    def _apply_eye_obj_transforms(frame, eye_L_data, eye_R_data):
        """Inserta keyframes de loc/rot/sca en los objetos de ojos."""
        mapping = {
            "ojo_izquierdo_cerdo_1": eye_L_data,
            "ojo_derecho_cerdo_1":   eye_R_data,
        }
        for obj_name, td in mapping.items():
            obj = scene.objects.get(obj_name)
            if not obj:
                continue
            obj.location       = td["loc"]
            obj.rotation_euler = td["rot"]
            obj.scale          = td["sca"]
            obj.keyframe_insert(data_path="location",       frame=frame)
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)
            obj.keyframe_insert(data_path="scale",          frame=frame)

    def _lerp_transforms(td_a, td_b, t):
        """Interpola lineal entre dos dicts de transforms."""
        def lv(a, b, t): return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
        return {
            "loc": lv(td_a["loc"], td_b["loc"], t),
            "rot": lv(td_a["rot"], td_b["rot"], t),
            "sca": lv(td_a["sca"], td_b["sca"], t),
        }

    def _smooth(t):
        t = max(0.0, min(1.0, t))
        return t * t * (3.0 - 2.0 * t)

    # Construir segmentos: (eye_L_start, eye_L_end, eye_R_start, eye_R_end, n_frames, interp)
    start_data = eye_seq_data.get("start", {})
    end_data   = eye_seq_data.get("end",   {})
    slots      = eye_seq_data.get("slots", [])

    states = [start_data] + slots + [end_data]
    cursor = eye_global_start

    for i in range(len(states) - 1):
        s_a = states[i]
        s_b = states[i + 1]
        n   = s_b.get("duration", 20)
        itp = s_b.get("interp_type", "SMOOTH")

        eye_L_a = s_a.get("eye_L", {})
        eye_L_b = s_b.get("eye_L", {})
        eye_R_a = s_a.get("eye_R", {})
        eye_R_b = s_b.get("eye_R", {})
        expr_b  = s_b.get("active_expression", "NEUTRAL")
        val_b   = float(s_b.get("expression_value", 1.0))

        for fi in range(n):
            abs_f = cursor + fi
            if abs_f > end_frame:
                break
            raw_t = (fi + 1) / n if n > 0 else 1.0
            t = _smooth(raw_t) if itp in ("SMOOTH", "BEZIER") else raw_t

            # Interpolar y aplicar loc/rot/sca
            if eye_L_a and eye_L_b:
                el = _lerp_transforms(eye_L_a, eye_L_b, t)
                er = _lerp_transforms(eye_R_a, eye_R_b, t)
                _apply_eye_obj_transforms(abs_f, el, er)

            # Aplicar expresion para este frame
            _apply_expr_shape_keys(abs_f, expr_b, val_b)

        cursor += n

    # Keyframe de cierre adicional: forzar 0.0 al final de la secuencia
    _apply_expr_shape_keys(end_frame, "NEUTRAL", 0.0)

    # Parpadeo automatico independiente
    if global_cfg.get("blink_enabled", False):
        intervals = global_cfg.get("blink_intervals", [])
        if intervals:
            idx = global_cfg.get("blink_interval_idx", 0)
            idx = min(idx, len(intervals) - 1)
            bi = intervals[idx]
            if bi.get("enabled", True):
                apply_blink_sequence(
                    bi.get("frame_start", start_frame),
                    bi.get("frame_end",   end_frame),
                    bi.get("blink_count",    2),
                    bi.get("blink_duration", 9),
                )
        else:
            # Fallback legacy
            apply_blink_sequence(
                global_cfg.get("blink_frame_start", start_frame),
                global_cfg.get("blink_frame_end",   end_frame),
                global_cfg.get("blink_count",    2),
                global_cfg.get("blink_duration", 9),
            )


# =============================================================================
# EXPORTAR .py  —  formato slot_NNN_tipo.py  (compatible con slot_002_arrodillarse.py)
# =============================================================================

class CERDO_1_ST_OT_ExportAnimation(Operator):
    bl_idname    = "cerdo_1_st.export_animation"
    bl_label     = "Exportar .py"
    bl_description = "Exporta la animacion como slot_NNN_tipo.py compatible con el flujo cerdo_1"
    bl_options   = {"REGISTER"}

    def execute(self, context):
        st    = context.scene.cerdo_1_st
        scene = context.scene

        from .woodcut_animation import bake_woodcut_base
        _wood_pc = getattr(scene, 'cerdo_1_path', None)
        if _wood_pc and _wood_pc.anim_frame_fin >= _wood_pc.frame_inicio:
            bake_woodcut_base(scene, _wood_pc.frame_inicio, _wood_pc.anim_frame_fin)

        if not st.anim_generated:
            self.report({"ERROR"}, "Primero genera la animacion con CONCATENAR")
            return {"CANCELLED"}
        if not st.armature_name:
            self.report({"ERROR"}, "Selecciona el armature")
            return {"CANCELLED"}
        armature = scene.objects.get(st.armature_name)
        if not armature or armature.type != "ARMATURE":
            self.report({"ERROR"}, "Armature no valido")
            return {"CANCELLED"}
        if not armature.animation_data or not armature.animation_data.action:
            self.report({"ERROR"}, "No hay accion de animacion en el armature")
            return {"CANCELLED"}

        # ── Recopilar info de Paso 1 y 2 desde cerdo_1_path ──────────────────
        _pc = getattr(scene, "cerdo_1_path", None)
        _n_pts           = len(_pc.path_points) if _pc else 0
        _modo            = "una_coordenada" if _n_pts <= 1 else "multiples_coordenadas"
        _blend_filepath  = bpy.path.abspath(_pc.blend_filepath) if _pc and _pc.blend_filepath else ""
        _slot_inicio     = _pc.slot_inicio       if _pc else 1
        _frame_inicio    = _pc.frame_inicio      if _pc else st.start_frame
        _frame_fin_m     = _pc.frame_fin_manual  if _pc else st.end_frame_gen
        _frames_bloque   = _pc.frames_por_bloque if _pc else 26
        _root_rot_x_p1   = _pc.root_rot_x        if _pc else 0.0
        _root_rot_y_p1   = _pc.root_rot_y        if _pc else 0.0
        _root_rot_z_p1   = _pc.root_rot_z        if _pc else -90.0
        _output_dir_p2   = bpy.path.abspath(_pc.output_dir) if _pc and _pc.output_dir else bpy.path.abspath(st.anim_dir)
        _path_pts_list   = []
        if _pc:
            for _pt in _pc.path_points:
                _path_pts_list.append({
                    "coords":     list(_pt.coords),
                    "texture":    _pt.texture,
                    "face_index": _pt.face_index,
                })

        # ── Leer historia_cerdo_1.json para key_point y orientacion ──
        historia = load_historia_json(st.historia_json)
        kps      = get_key_points(historia)
        ori_rad  = get_orientacion_inicial(historia)   # (rx, ry, rz) en radianes
        ori_data = historia.get("configuracion", {}).get("orientacion_inicial", {})

        # Buscar el key_point seleccionado — usar root_pos_key_point (el dropdown
        # 'KeyPoint para Root' que el usuario elige en el panel de Configuracion).
        # selected_key_point es un IntProperty legacy que ya no se sincroniza con el UI.
        try:
            kp_idx_sel = int(st.root_pos_key_point)
        except (ValueError, TypeError):
            kp_idx_sel = 1
        kp_selected = next((k for k in kps if k.get("index") == kp_idx_sel), None)
        if kp_selected is None and kps:
            kp_selected = kps[0]

        eye_s = st.eye_expr

        # ── Resolver rango de frames segun el alcance de exportacion ─────────
        export_scope = getattr(st, "export_scope", "FULL")

        if export_scope == "ACTIVE":
            # Exportar solo el segmento activo en Paso 3
            try:
                seg_cfg = scene.cerdo_1_segs
                segs    = seg_cfg.segments
                if not segs or not (0 <= seg_cfg.active_index < len(segs)):
                    self.report({"ERROR"}, "No hay segmento activo en el Paso 3")
                    return {"CANCELLED"}
                seg_active = segs[seg_cfg.active_index]
                start_f      = seg_active.frame_start
                end_f        = seg_active.frame_end
                total_frames = end_f - start_f + 1
                _scope_label = f"segmento '{seg_active.label}'"
            except Exception as e:
                self.report({"ERROR"}, f"No se pudo leer el segmento activo: {e}")
                return {"CANCELLED"}

        elif export_scope == "SELECTED":
            # Exportar la union de todos los segmentos marcados con export_selected
            try:
                seg_cfg  = scene.cerdo_1_segs
                marcados = [s for s in seg_cfg.segments if s.export_selected]
                if not marcados:
                    self.report({"ERROR"}, "Ningun segmento tiene activada la opcion 'Exportar' en el Paso 3")
                    return {"CANCELLED"}
                start_f      = min(s.frame_start for s in marcados)
                end_f        = max(s.frame_end   for s in marcados)
                total_frames = end_f - start_f + 1
                _scope_label = f"{len(marcados)} segmentos marcados"
            except Exception as e:
                self.report({"ERROR"}, f"No se pudo leer los segmentos marcados: {e}")
                return {"CANCELLED"}

        else:
            # FULL — animacion completa definida en el Paso 2:
            #   · 1 coordenada  : frame_inicio → frame_fin_manual  (configuracion manual)
            #   · Multiples coords: frame_inicio → anim_frame_fin  (suma de slots generados)
            # pc.anim_frame_fin lo setea el Paso 2 en ambos casos al generar/exportar.
            _pc_full = getattr(scene, "cerdo_1_path", None)
            if _pc_full and _pc_full.frame_inicio > 0:
                start_f = _pc_full.frame_inicio
                _n_pts_full = len(_pc_full.path_points) if _pc_full else 0
                from .woodcut_animation import is_woodcut
                _is_woodcut_single = (_n_pts_full == 1 and is_woodcut(_pc_full.path_points[0].tipo_segmento))
                if _n_pts_full <= 1 and not _is_woodcut_single:
                    # 1 coordenada: usar frame_fin_manual
                    end_f = max(_pc_full.frame_fin_manual, start_f + 1)
                else:
                    # Multiples coordenadas: usar anim_frame_fin (acumulado por Paso 2)
                    if _pc_full.anim_frame_fin > 0:
                        end_f = _pc_full.anim_frame_fin
                    else:
                        # Fallback si el Paso 2 no se ejecuto aun
                        end_f = st.end_frame_gen if st.end_frame_gen > 0 else scene.frame_end
                total_frames = end_f - start_f + 1
                _scope_label = (
                    f"animacion completa (1 coord, frames {start_f}→{end_f})"
                    if _n_pts_full <= 1 else
                    f"animacion completa (recorrido {_n_pts_full} pts, frames {start_f}→{end_f})"
                )
            else:
                # Fallback si cerdo_1_path no esta disponible
                start_f      = st.start_frame
                end_f        = st.end_frame_gen
                total_frames = st.total_frames_gen
                _scope_label = "animacion completa"

        if total_frames <= 0 or end_f < start_f:
            self.report({"ERROR"}, f"Rango de frames invalido: {start_f} → {end_f}")
            return {"CANCELLED"}

        # ── Capturar keyframes de rotacion desde la timeline ──
        bone_frames = {b: {} for b in BONES_LISTA_FULL}
        # Capturar la rotacion del armature por frame (orientacion por pose)
        arm_rot_frames = {}   # local_f -> (rx, ry, rz) en radianes
        # Capturar loc + rot del root (cerdo_1 Empty) por frame
        root_obj_capture = scene.objects.get('cerdo_1')
        root_keyframes   = {}   # local_f -> {'loc': (x,y,z), 'rot': (rx,ry,rz)}
        for abs_f in range(start_f, end_f + 1):
            scene.frame_set(abs_f)
            local_f = abs_f - start_f + 1
            for bn in BONES_LISTA_FULL:
                pb = armature.pose.bones.get(bn)
                if pb:
                    e = pb.rotation_euler
                    bone_frames[bn][local_f] = (round(e.x,6), round(e.y,6), round(e.z,6))
                else:
                    bone_frames[bn][local_f] = (0.0, 0.0, 0.0)
            # Rotacion del armature (object-level)
            ae = armature.rotation_euler
            arm_rot_frames[local_f] = (round(ae.x,6), round(ae.y,6), round(ae.z,6))
            # Loc + rot del root Empty (cerdo_1)
            if root_obj_capture:
                rl = root_obj_capture.location
                rr = root_obj_capture.rotation_euler
                root_keyframes[local_f] = {
                    'loc': (round(rl.x,6), round(rl.y,6), round(rl.z,6)),
                    'rot': (round(rr.x,6), round(rr.y,6), round(rr.z,6)),
                }
        scene.frame_set(start_f)

        def frames_at(lf):
            return {b: bone_frames[b].get(lf, (0.0,0.0,0.0)) for b in BONES_LISTA_FULL}

        p_ini = frames_at(1)
        p_act = frames_at(max(1, total_frames // 2))
        p_fin = frames_at(total_frames)

        # ── Metadatos ──
        slot_num   = st.export_slot_number
        movement   = st.export_type.strip() or "custom"
        desc       = st.export_desc.strip()
        now        = datetime.now().strftime("%Y-%m-%d")
        fps_val    = st.fps
        dur_s      = round(total_frames / fps_val, 4)
        er         = round(st.entry_ratio, 2)
        xr         = round(st.exit_ratio,  2)
        anim_name  = f"cerdo_1_{movement}"

        # Nombre de archivo: slot_NNN_tipo.py
        slot_str   = f"{slot_num:03d}"
        filename   = f"slot_{slot_str}_{movement}.py"

        # ── Serializar dicts de pose ──
        def _pose_lines(d, varname):
            lines = [f"{varname} = {{"]
            for k, v in d.items():
                lines.append(f"    {repr(k)}: {v},")
            lines.append("}")
            return "\n".join(lines)

        kf_lines = ["KEYFRAME_DATA = {"]
        for bn in BONES_LISTA_FULL:
            kf_lines.append(f"    {repr(bn)}: {{")
            for lf, v in sorted(bone_frames[bn].items()):
                kf_lines.append(f"        {lf}: {v},")
            kf_lines.append("    },")
        kf_lines.append("}")

        # ── Serializar rotaciones del armature por frame ──
        arm_rot_lines = ["ARMATURE_ROTATIONS = {"]
        for lf, v in sorted(arm_rot_frames.items()):
            arm_rot_lines.append(f"    {lf}: {v},")
        arm_rot_lines.append("}")

        # ── Embedded trajectory point ──
        if kp_selected:
            co = kp_selected.get("coordinates", {"x":0,"y":0,"z":0})
            tex = kp_selected.get("texture", "?")
            fi  = kp_selected.get("face_index", "?")
            kp_idx = kp_selected.get("index", 0) # Usar el indice del keypoint encontrado
            traj_block = (
                "EMBEDDED_TRAJECTORY_POINTS = [\n"
                "    {\n"
                f"        \"index\": {kp_idx},\n"
                f"        \"coordinates\": {{\"x\": {co['x']}, \"y\": {co['y']}, \"z\": {co['z']}}},\n"
                f"        \"texture\": \"{tex}\",\n"
                f"        \"face_index\": \"{fi}\"\n"
                "    },\n"
                "]\n"
            )
            anchor_x = co['x']
            anchor_y = co['y']
            anchor_z = co['z']
        else:
            traj_block = "EMBEDDED_TRAJECTORY_POINTS = []\n"
            anchor_x = anchor_y = anchor_z = 0.0

        # Serializar ROOT_KEYFRAMES con coordenadas RELATIVAS al anchor.
        # Al ejecutar, execute_animation() suma el anchor nuevamente, por lo que
        # aqui se guarda (loc_absoluta - anchor) para evitar el doble offset.
        root_kf_lines = ["ROOT_KEYFRAMES = {"]
        for lf, kf in sorted(root_keyframes.items()):
            rel_loc = (
                round(kf['loc'][0] - anchor_x, 6),
                round(kf['loc'][1] - anchor_y, 6),
                round(kf['loc'][2] - anchor_z, 6),
            )
            root_kf_lines.append(
                f"    {lf}: {{'loc': {rel_loc}, 'rot': {kf['rot']}}},"
            )
        root_kf_lines.append("}")

        # Rotacion del root: usar frame 1 capturado del Empty cerdo_1 (real de timeline)
        # Fallback a orientacion_inicial del JSON si no hay datos capturados
        if root_keyframes:
            _rf1 = root_keyframes.get(1, root_keyframes[min(root_keyframes)])
            rx_real = round(math.degrees(_rf1['rot'][0]), 4)
            ry_real = round(math.degrees(_rf1['rot'][1]), 4)
            rz_real = round(math.degrees(_rf1['rot'][2]), 4)
        else:
            rx_real = ori_data.get('rotacion_x', 0.0)
            ry_real = ori_data.get('rotacion_y', 0.0)
            rz_real = ori_data.get('rotacion_z', 0.0)

        # Normalizar paths para evitar errores de escape en el .py generado
        _blend_filepath_safe  = _blend_filepath.replace("\\", "/")
        _output_dir_p2_safe   = _output_dir_p2.replace("\\", "/")
        _pts_repr             = repr(_path_pts_list)
        code = (
            "# -*- coding: utf-8 -*-\n"
            '"""\n'
            f"{filename}\n"
            f"Cerdo_1 - Slot {{{slot_str}}}\n\n"
            "GENERADO AUTOMATICAMENTE\n"
            f"Fecha de generacion: {now}\n\n"
            f"Tipo        : {movement}\n"
            f"Descripcion : {desc}\n"
            f"Duracion    : {total_frames} frames  ({dur_s} s @ {fps_val} fps)\n\n"
            f"MODO RECORRIDO : {_modo}  ({_n_pts} punto(s) registrado(s))\n"
            f"ALCANCE EXPORT : {_scope_label}  (frames {start_f} → {end_f})\n\n"
            "--- PASO 1 (Personaje y recorrido) ---\n"
            f"  Personaje       : {os.path.basename(_blend_filepath) if _blend_filepath else '(no especificado)'}\n"
            f"  Blend filepath  : {_blend_filepath_safe}\n"
            f"  Puntos recorrido: {_n_pts}\n\n"
            "--- PASO 2 (Configuracion de slots) ---\n"
            f"  Slot inicio         : {_slot_inicio}\n"
            f"  Frame inicial       : {_frame_inicio}\n"
            f"  Frame final         : {_frame_fin_m}\n"
            f"  Frames por bloque   : {_frames_bloque}\n"
            f"  Orientacion (X/Y/Z) : {_root_rot_x_p1} / {_root_rot_y_p1} / {_root_rot_z_p1}\n"
            f"  Carpeta de salida   : {_output_dir_p2_safe}\n"
            '"""\n\n'
            "import bpy\n"
            "import math\n\n"
            "# --- Compatibilidad Action.fcurves (eliminado en Blender 5.0+) ---\n"
            "def _get_fcurves(target):\n"
            "    anim_data = None\n"
            "    action = target\n"
            "    if isinstance(target, bpy.types.AnimData):\n"
            "        anim_data = target\n"
            "        action = anim_data.action\n"
            "    if action is None:\n"
            "        return []\n"
            "    if hasattr(action, 'fcurves'):\n"
            "        return action.fcurves\n"
            "    from bpy_extras import anim_utils as _au\n"
            "    slot = anim_data.action_slot if anim_data is not None else None\n"
            "    if slot is None and action.slots:\n"
            "        slot = action.slots[0]\n"
            "    if slot is None:\n"
            "        return []\n"
            "    channelbag = _au.action_ensure_channelbag_for_slot(action, slot)\n"
            "    return channelbag.fcurves if channelbag else []\n\n"
            "# ============================================\n"
            "# CONFIGURACION DEL SLOT\n"
            "# (inyectadas por el orquestador)\n"
            "# ============================================\n\n"
            f"SLOT_INDEX   = {slot_num}   # type: int\n"
            f"START_FRAME  = {start_f}   # type: int\n"
            f"END_FRAME    = {end_f}   # type: int\n"
            f"TOTAL_FRAMES = {total_frames}   # duracion estandar del tipo\n"
            f"ROOT_ROTATION_X = {rx_real}\n"
            f"ROOT_ROTATION_Y = {ry_real}\n"
            f"ROOT_ROTATION_Z = {rz_real}   # type: float  (grados) - fuente: root cerdo_1 timeline\n"
            f"ARMATURE_NAME   = '{st.armature_name}'   # type: str - nombre del objeto Armature en la escena\n\n"
            "# ============================================\n"
            "# MODO DE RECORRIDO Y DATOS PASO 1 / PASO 2\n"
            "# ============================================\n\n"
            f"MODO_RECORRIDO = '{_modo}'   # 'una_coordenada' | 'multiples_coordenadas'\n"
            f"PASO_1_CONFIG = {{\n"
            f"    'blend_filepath':     {repr(_blend_filepath_safe)},\n"
            f"    'n_puntos_recorrido': {_n_pts},\n"
            f"}}\n\n"
            f"PASO_2_CONFIG = {{\n"
            f"    'slot_inicio':       {_slot_inicio},\n"
            f"    'frame_inicio':      {_frame_inicio},\n"
            f"    'frame_fin_manual':  {_frame_fin_m},\n"
            f"    'frames_por_bloque': {_frames_bloque},\n"
            f"    'root_rot_x':        {_root_rot_x_p1},\n"
            f"    'root_rot_y':        {_root_rot_y_p1},\n"
            f"    'root_rot_z':        {_root_rot_z_p1},\n"
            f"    'output_dir':        {repr(_output_dir_p2_safe)},\n"
            f"}}\n\n"
            f"PATH_POINTS = {_pts_repr}\n\n"
            "# ============================================\n"
            "# FIN DE CONFIGURACION DEL SLOT\n"
            "# ============================================\n\n"
            "# ============================================\n"
            "# COORDENADAS DEL RECORRIDO PARA SLOT\n"
            "# (key_point seleccionado de historia_cerdo_1.json)\n"
            "# ============================================\n\n"
            f"{traj_block}\n"
            "# ============================================\n"
            "# FIN DE COORDENADAS DEL RECORRIDO\n"
            "# ============================================\n\n"
            f"ANIMATION_INFO = {{\n"
            f"    'name': '{filename}',\n"
            f"    'frame_count': {total_frames},\n"
            f"    'fps': {fps_val},\n"
            f"    'duration_seconds': {dur_s},\n"
            f"    'entity': 'Cerdo_1',\n"
            f"    'slot': {slot_num},\n"
            f"    'movement_type': '{movement}',\n"
            f"    'narrative_importance': 'expression',\n"
            f"    'rig_type': 'full_armature',\n"
            f"    'source': 'cerdo_1_studio_v1.3',\n"
            f"    'bones_animated': {len(BONES_LISTA_FULL)},\n"
            f"    'animation_type': 'expression'\n"
            f"}}\n\n"
            f"ANIMATION_CONFIG = {{\n"
            f"    'name': '{anim_name}',\n"
            f"    'frame_count': {total_frames},\n"
            f"    'fps': {fps_val},\n"
            f"    'duration_seconds': {dur_s},\n"
            f"    'entity': 'Cerdo_1',\n"
            f"    'slot': {slot_num},\n"
            f"    'movement_type': '{movement}',\n"
            f"}}\n\n"
            "BLINK_SEQUENCE = {\n"
            "    1: {\"closed\": 0.0,  \"hide\": False},\n"
            "    2: {\"closed\": 0.25, \"hide\": False},\n"
            "    3: {\"closed\": 0.5,  \"hide\": False},\n"
            "    4: {\"closed\": 0.75, \"hide\": False},\n"
            "    5: {\"closed\": 1.0,  \"hide\": True},\n"
            "    6: {\"closed\": 1.0,  \"hide\": True},\n"
            "    7: {\"closed\": 0.75, \"hide\": False},\n"
            "    8: {\"closed\": 0.5,  \"hide\": False},\n"
            "    9: {\"closed\": 0.25, \"hide\": False},\n"
            "}\n\n"
            f"EXPRESSION_CONFIG = {{\n"
            f"    'enabled':           {eye_s.enabled},\n"
            f"    'active_expression': '{eye_s.active_expression.lower()}',\n"
            f"    'expression_value':  {round(eye_s.expression_value, 3)},\n"
            f"    'blink_enabled':     {eye_s.blink_enabled},\n"
            f"    'blink_count':       {eye_s.blink_count},\n"
            f"    'blink_duration':    {eye_s.blink_duration},\n"
            f"    'blink_frame_start': {eye_s.blink_frame_start},\n"
            f"    'blink_frame_end':   {eye_s.blink_frame_end},\n"
            f"    'intensity_feliz':   {round(eye_s.intensity_feliz, 4)},\n"
            f"    'intensity_triste':  {round(eye_s.intensity_triste, 4)},\n"
            f"    'intensity_enojado': {round(eye_s.intensity_enojado, 4)},\n"
            f"    'intensity_sospecha':{round(eye_s.intensity_sospecha, 4)},\n"
            f"    'curve_mode':        '{eye_s.curve_mode}',\n"
            f"    'affect_zone':       '{eye_s.affect_zone}',\n"
            f"    'invert_vertical':   {eye_s.invert_vertical},\n"
            f"    'invert_horizontal': {eye_s.invert_horizontal},\n"
            f"    'swap_axes':         {eye_s.swap_axes},\n"
            f"    'subdivide_cuts':    {eye_s.subdivide_cuts},\n"
            f"}}\n\n"
            # ── EYE_SEQUENCE_DATA: secuencia completa de ojos (panel 2b) ──────
            + _build_eye_sequence_data_code(st) +
            "\n\n"
            # ── EYE_BASE_MESH_DATA: geometria base serializada en exportacion ──
            + _build_eye_base_mesh_data_code(st.eye_expr) +
            "\n\n"
            f"BONES_LISTA = {repr(BONES_LISTA_FULL)}\n\n"
            # ── BONE_OSCILLATIONS_CONFIG ──────────────────────────────────────
            + _build_bone_oscillations_code(st) +
            "\n\n"
            # ── OBJECT_IMPORTS_CONFIG ─────────────────────────────────────────
            + _build_object_imports_code(st) +
            "\n\n"
            # ── SEGMENTS_THROW_CONFIG ─────────────────────────────────────────
            + _build_throw_config_code(scene) +
            "\n\n"
            "# ── Interpolacion 3 fases ───────────────────────────────────\n\n"
            "def _lerp(a, b, t):\n"
            "    return (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t, a[2]+(b[2]-a[2])*t)\n\n"
            "def _smooth(t):\n"
            "    t = max(0.0, min(1.0, t))\n"
            "    return t * t * (3.0 - 2.0 * t)\n\n"
            f"def _interpolate_3phases(frame, total_frames, rot_start, rot_action, rot_end,\n"
            f"                          entry_ratio={er}, exit_ratio={xr}):\n"
            "    if frame <= 1:      return rot_start\n"
            "    if frame >= total_frames: return rot_end\n"
            "    entry_end  = max(2, int(total_frames * entry_ratio))\n"
            "    exit_start = min(total_frames - 1, int(total_frames * (1.0 - exit_ratio)))\n"
            "    if frame <= entry_end:\n"
            "        t = _smooth((frame - 1) / max(entry_end - 1, 1))\n"
            "        return _lerp(rot_start, rot_action, t)\n"
            "    elif frame >= exit_start:\n"
            "        t = _smooth((frame - exit_start) / max(total_frames - exit_start, 1))\n"
            "        return _lerp(rot_action, rot_end, t)\n"
            "    else:\n"
            "        return rot_action\n\n"
            "# Poses de referencia\n"
            f"# Pose inicio: {st.action_poses[0].pose_name if len(st.action_poses) else '?'}  (frame 1)\n"
            f"{_pose_lines(p_ini, 'POSE_INICIO')}\n\n"
            "# Pose accion (frame central)\n"
            f"{_pose_lines(p_act, 'POSE_ACCION')}\n\n"
            f"# Pose fin: {st.action_poses[-1].pose_name if len(st.action_poses) else '?'}  (ultimo frame)\n"
            f"{_pose_lines(p_fin, 'POSE_FIN')}\n\n"
            "def _build_bone_functions(total_frames):\n"
            '    """\n'
            "    Animacion en 3 fases:\n"
            f"      Inicio  ({st.action_poses[0].pose_name if len(st.action_poses) else '?'})  -> frame 1 exacto\n"
            "      Accion  -> frame central\n"
            f"      Fin     ({st.action_poses[-1].pose_name if len(st.action_poses) else '?'})    -> ultimo frame exacto\n"
            '    """\n'
            "    bone_functions = {}\n"
            "    for bone_name in BONES_LISTA:\n"
            "        s = POSE_INICIO.get(bone_name, (0.0, 0.0, 0.0))\n"
            "        c = POSE_ACCION.get(bone_name, s)\n"
            "        e = POSE_FIN.get(bone_name,    s)\n"
            "        bone_functions[bone_name] = (\n"
            "            lambda f, ps=s, pa=c, pe=e:\n"
            "                _interpolate_3phases(f, total_frames, ps, pa, pe)\n"
            "        )\n"
            "    return bone_functions\n\n"
            "# Keyframes exactos capturados desde la timeline de Blender\n"
            f"{chr(10).join(kf_lines)}\n\n"
            f"{chr(10).join(arm_rot_lines)}\n\n"
            f"{chr(10).join(root_kf_lines)}\n\n\n"
            "def _find_cerdo_1_objects():\n"
            "    root = bpy.data.objects.get('cerdo_1')\n"
            "    if not root:\n"
            "        root = next(\n"
            "            (o for o in bpy.data.objects\n"
            "             if o.name.lower() == 'cerdo_1' and o.type == 'EMPTY'), None)\n"
            "    armature = bpy.data.objects.get('pig.arma_cerdo_1')\n"
            "    if not armature or armature.type != 'ARMATURE':\n"
            "        if root:\n"
            "            armature = next(\n"
            "                (o for o in bpy.data.objects\n"
            "                 if o.type == 'ARMATURE' and o.parent == root), None)\n"
            "    if not armature or armature.type != 'ARMATURE':\n"
            "        armature = next(\n"
            "            (o for o in bpy.data.objects if o.type == 'ARMATURE'), None)\n"
            "    return root, armature\n\n\n"
            "def execute_animation(player_parts=None, start_frame=None, end_frame=None):\n"
            '    """\n'
            f"    Slot Cerdo_1 {movement}.\n\n"
            "    Requiere que SLOT_INDEX, START_FRAME, END_FRAME y ROOT_ROTATION_Z\n"
            "    hayan sido inyectados por el orquestador antes de llamar esta funcion,\n"
            "    o bien pasados como argumentos start_frame / end_frame.\n"
            '    """\n'
            "    if start_frame is None: start_frame = START_FRAME\n"
            "    if end_frame   is None: end_frame   = END_FRAME\n"
            "    if start_frame is None or end_frame is None:\n"
            "        raise ValueError(\n"
            "            'execute_animation: START_FRAME / END_FRAME no han sido definidos. '\n"
            "            'El orquestador debe inyectar los valores antes de ejecutar.')\n\n"
            "    total_frames = end_frame - start_frame + 1\n\n"
            "    # Obtener armature\n"
            "    armature = player_parts.get('body') if player_parts else None\n"
            "    if not armature:\n"
            "        armature = bpy.data.objects.get('pig.arma_cerdo_1')\n"
            "    if not armature or armature.type != 'ARMATURE':\n"
            "        print('Error: No se encontro el Armature'); return False\n\n"
            "    bpy.context.view_layer.objects.active = armature\n"
            "    if armature.mode != 'POSE':\n"
            "        bpy.ops.object.mode_set(mode='POSE')\n"
            "    for bone in armature.pose.bones:\n"
            "        bone.rotation_mode = 'XYZ'\n\n"
            f"    _arm_action_name = f'slot_{{SLOT_INDEX:03d}}_{anim_name}_arm'\n"
            "    if not armature.animation_data:\n"
            "        armature.animation_data_create()\n"
            "    _arm_existing = bpy.data.actions.get(_arm_action_name)\n"
            "    if _arm_existing: bpy.data.actions.remove(_arm_existing)\n"
            "    _arm_action = bpy.data.actions.new(name=_arm_action_name)\n\n"
            "    # Obtener root\n"
            "    root = bpy.data.objects.get('cerdo_1')\n"
            "    if not root:\n"
            "        root = next(\n"
            "            (o for o in bpy.data.objects\n"
            "             if o.name.lower() == 'cerdo_1' and o.type == 'EMPTY'), None)\n\n"
            "    if root:\n"
            f"        _root_action_name = f'slot_{{SLOT_INDEX:03d}}_{anim_name}_root'\n"
            "        if not root.animation_data:\n"
            "            root.animation_data_create()\n"
            "        _root_existing = bpy.data.actions.get(_root_action_name)\n"
            "        if _root_existing: bpy.data.actions.remove(_root_existing)\n"
            "        _root_action = bpy.data.actions.new(name=_root_action_name)\n"
            "        root.animation_data.action = _root_action\n\n"
            "    # Aplicar ROOT_KEYFRAMES: loc relativo + offset del anchor point\n"
            "    if root and EMBEDDED_TRAJECTORY_POINTS:\n"
            "        _pt = EMBEDDED_TRAJECTORY_POINTS[0]['coordinates']\n"
            "        _anchor_loc = (_pt['x'], _pt['y'], _pt['z'])\n"
            "        _anchor_rot = (math.radians(ROOT_ROTATION_X),\n"
            "                       math.radians(ROOT_ROTATION_Y),\n"
            "                       math.radians(ROOT_ROTATION_Z))\n"
            "        if ROOT_KEYFRAMES:\n"
            "            # Aplicar loc relativo + offset anchor, y rot capturada\n"
            "            for _lf, _kf_data in sorted(ROOT_KEYFRAMES.items()):\n"
            "                _abs_f = start_frame + (_lf - 1)\n"
            "                if _abs_f > end_frame: break\n"
            "                _rl = _kf_data['loc']\n"
            "                _offset_loc = (_anchor_loc[0] + _rl[0],\n"
            "                               _anchor_loc[1] + _rl[1],\n"
            "                               _anchor_loc[2] + _rl[2])\n"
            "                bpy.context.scene.frame_set(_abs_f)\n"
            "                root.location       = _offset_loc\n"
            "                root.rotation_euler = _kf_data['rot']\n"
            "                root.keyframe_insert(data_path='location',       frame=_abs_f)\n"
            "                root.keyframe_insert(data_path='rotation_euler', frame=_abs_f)\n"
            "        else:\n"
            "            # Fallback: anclar fijo en el anchor point\n"
            "            for _kf in range(start_frame, end_frame + 1):\n"
            "                bpy.context.scene.frame_set(_kf)\n"
            "                root.location       = _anchor_loc\n"
            "                root.rotation_euler = _anchor_rot\n"
            "                root.keyframe_insert(data_path='location',       frame=_kf)\n"
            "                root.keyframe_insert(data_path='rotation_euler', frame=_kf)\n\n"
            "    armature.animation_data.action = _arm_action\n\n"
            "    # Aplicar rotacion adicional del root si se provee via player_parts\n"
            "    cerdo_1_root = player_parts.get('root') if player_parts else None\n"
            "    if not cerdo_1_root:\n"
            "        cerdo_1_root = next(\n"
            "            (o for o in bpy.data.objects\n"
            "             if o.name == 'cerdo_1' and o.type == 'EMPTY'), None)\n\n"
            "    rz = ROOT_ROTATION_Z if ROOT_ROTATION_Z is not None else 0.0\n\n"
            "    # Aplicar keyframes de huesos\n"
            "    bone_funcs = _build_bone_functions(total_frames)\n"
            "    bones_applied = 0\n"
            "    bones_missing = []\n\n"
            "    if total_frames == TOTAL_FRAMES:\n"
            "        for bn in BONES_LISTA:\n"
            "            pb = armature.pose.bones.get(bn)\n"
            "            if not pb: bones_missing.append(bn); continue\n"
            "            pb.rotation_mode = 'XYZ'\n"
            "            for lf, rot in KEYFRAME_DATA.get(bn, {}).items():\n"
            "                abs_f = start_frame + (lf - 1)\n"
            "                pb.rotation_euler = rot\n"
            "                pb.keyframe_insert(data_path='rotation_euler', frame=abs_f)\n"
            "            bones_applied += 1\n"
            "    else:\n"
            "        for bone_name, fn in bone_funcs.items():\n"
            "            pb = armature.pose.bones.get(bone_name)\n"
            "            if not pb: bones_missing.append(bone_name); continue\n"
            "            pb.rotation_mode = 'XYZ'\n"
            "            for local_f in range(1, total_frames + 1):\n"
            "                abs_f = start_frame + (local_f - 1)\n"
            "                pb.rotation_euler = fn(local_f)\n"
            "                pb.keyframe_insert(data_path='rotation_euler', frame=abs_f)\n"
            "            bones_applied += 1\n\n"
            "    print(f'Keyframes aplicados a {bones_applied} bones')\n"
            "    if bones_missing:\n"
            "        print(f'   Bones no encontrados: {bones_missing}')\n\n"
            "    # ── Aplicar rotacion del armature por frame (orientacion por pose) ──\n"
            "    if ARMATURE_ROTATIONS:\n"
            "        armature.rotation_mode = 'XYZ'\n"
            "        if not armature.animation_data:\n"
            "            armature.animation_data_create()\n"
            "        _arm_obj_action_name = f'slot_{SLOT_INDEX:03d}_arm_obj_rot'\n"
            "        _arm_obj_existing = bpy.data.actions.get(_arm_obj_action_name)\n"
            "        if _arm_obj_existing: bpy.data.actions.remove(_arm_obj_existing)\n"
            "        _arm_obj_action = bpy.data.actions.new(name=_arm_obj_action_name)\n"
            "        armature.animation_data.action = _arm_obj_action\n"
            "        for lf, rot in ARMATURE_ROTATIONS.items():\n"
            "            abs_f = start_frame + (lf - 1)\n"
            "            bpy.context.scene.frame_set(abs_f)\n"
            "            armature.rotation_euler = rot\n"
            "            armature.keyframe_insert(data_path='rotation_euler', frame=abs_f)\n"
            "        # Suavizar curvas de rotacion del armature\n"
            "        for fc in _get_fcurves(_arm_obj_action):\n"
            "            for kp in fc.keyframe_points:\n"
            "                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'\n"
            "        # Pasar al NLA\n"
            "        armature.animation_data.action = None\n"
            "        _arm_obj_track = armature.animation_data.nla_tracks.new()\n"
            "        _arm_obj_track.name = f'Slot_{SLOT_INDEX:03d}_arm_obj_rot'\n"
            "        _arm_obj_strip = _arm_obj_track.strips.new(_arm_obj_action_name, start_frame, _arm_obj_action)\n"
            "        _arm_obj_strip.frame_end     = end_frame\n"
            "        _arm_obj_strip.extrapolation = 'NOTHING'\n"
            "        _arm_obj_strip.use_auto_blend = False\n"
            "        _arm_obj_strip.blend_in  = 0\n"
            "        _arm_obj_strip.blend_out = 0\n\n"
            "    # [FIX] Restaurar _arm_action como accion activa para keyframes de bones\n"
            "    armature.animation_data.action = _arm_action\n\n"
            "    if armature.animation_data and armature.animation_data.action:\n"
            "        for fc in _get_fcurves(armature.animation_data.action):\n"
            "            for kp in fc.keyframe_points:\n"
            "                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'\n\n"
            "    if cerdo_1_root and cerdo_1_root.animation_data and cerdo_1_root.animation_data.action:\n"
            "        for fc in _get_fcurves(cerdo_1_root.animation_data.action):\n"
            "            for kp in fc.keyframe_points:\n"
            "                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'\n\n"
            f"    print(f'ANIMACION {anim_name} APLICADA!')\n"
            "    print(f'  Frames: {start_frame}-{end_frame}')\n\n"
            # ══════════════════════════════════════════════════════════════════
            # Bloque de ojos: EYE_SEQUENCE_DATA completo (panel 2b)
            # Incluye: construccion de shape keys de expresion (geometria),
            # aplicacion de expresiones por frame, transforms loc/rot/sca,
            # y parpadeo con blink_intervals.
            # ══════════════════════════════════════════════════════════════════

            # ── Utilidades de curva ──
            "    def _eye_apply_curve_exp(factor, curve_mode):\n"
            "        if curve_mode == 'QUADRATIC': return factor ** 2\n"
            "        if curve_mode == 'CUBIC':     return factor ** 3\n"
            "        return factor\n\n"

            # ── Deteccion de ejes ──
            "    def _eye_detect_axes_exp(mesh_obj):\n"
            "        verts = [v.co for v in mesh_obj.data.vertices]\n"
            "        if not verts: return 'x', 'z', 'y'\n"
            "        xs=[v.x for v in verts]; ys=[v.y for v in verts]; zs=[v.z for v in verts]\n"
            "        ranges={'x':max(xs)-min(xs),'y':max(ys)-min(ys),'z':max(zs)-min(zs)}\n"
            "        # Desempate deterministico: x gana sobre z sobre y cuando rangos son iguales\n"
            "        priority={'x':2,'z':1,'y':0}\n"
            "        s=sorted(ranges.items(),key=lambda i:(round(i[1],6),priority[i[0]]))\n"
            "        return s[2][0], s[1][0], s[0][0]\n\n"

            # ── Calculo de vertice deformado ──
            "    def _eye_compute_vertex_exp(orig_co, h_axis, v_axis, bounds, expression, cfg, mirror_h=False):\n"
            "        cx,cy,cz=bounds['cx'],bounds['cy'],bounds['cz']\n"
            "        rx,ry,rz=bounds['rx'],bounds['ry'],bounds['rz']\n"
            "        h_val=getattr(orig_co,h_axis); v_val=getattr(orig_co,v_axis)\n"
            "        cv={'x':cx,'y':cy,'z':cz}[v_axis]; rv={'x':rx,'y':ry,'z':rz}[v_axis]\n"
            "        ch={'x':cx,'y':cy,'z':cz}[h_axis]; rh={'x':rx,'y':ry,'z':rz}[h_axis]\n"
            "        v_mult=-1 if cfg.get('invert_vertical',True) else 1\n"
            "        h_mult=-1 if cfg.get('invert_horizontal',False) else 1\n"
            "        v_factor=(v_val-cv)/(rv/2) if rv>0 else 0\n"
            "        h_factor=(h_val-ch)/(rh/2) if rh>0 else 0\n"
            "        if mirror_h: h_factor=-h_factor\n"
            "        zone=cfg.get('affect_zone','UPPER')\n"
            "        if zone=='UPPER':\n"
            "            if v_factor<=0: return orig_co.copy()\n"
            "            v_factor_norm=v_factor\n"
            "        elif zone=='LOWER':\n"
            "            if v_factor>=0: return orig_co.copy()\n"
            "            v_factor_norm=-v_factor\n"
            "        else: v_factor_norm=abs(v_factor)\n"
            "        offset=0.0\n"
            "        cm=cfg.get('curve_mode','QUADRATIC')\n"
            "        if expression in ('feliz','triste'):\n"
            "            curve=_eye_apply_curve_exp(abs(h_factor),cm)\n"
            "            intens=cfg.get('intensity_feliz',0.18) if expression=='feliz' else cfg.get('intensity_triste',0.18)\n"
            "            sign=1 if expression=='feliz' else -1\n"
            "            offset=sign*intens*curve*v_factor_norm*v_mult\n"
            "        elif expression in ('sospecha','enojado'):\n"
            "            min_h=ch-rh/2\n"
            "            h_norm=(h_val-min_h)/rh if rh>0 else 0.5\n"
            "            if mirror_h: h_norm=1.0-h_norm\n"
            "            if expression=='sospecha':\n"
            "                intens=cfg.get('intensity_sospecha',0.18)\n"
            "                offset=(intens*h_norm-intens/2)*v_factor_norm*v_mult*h_mult\n"
            "            else:\n"
            "                intens=cfg.get('intensity_enojado',0.18)\n"
            "                offset=(-intens*h_norm+intens/2)*v_factor_norm*v_mult*h_mult\n"
            "        elif expression=='cerrado': offset=-(v_val-cv)*0.85\n"
            "        elif expression=='cansado': offset=-(v_val-cv)*0.4*v_factor_norm\n"
            "        elif expression=='sorpresa': offset=(v_val-cv)*0.15*v_factor_norm\n"
            "        new_co=orig_co.copy(); setattr(new_co,v_axis,v_val+offset); return new_co\n\n"

            # ── Construccion de shape keys de expresion ──
            "    def _build_expr_shape_keys(eye_obj, cfg, is_right=False):\n"
            "        # Restaurar geometria base desde EYE_BASE_MESH_DATA (serializada en exportacion)\n"
            "        # Esto garantiza que la malla tenga exactamente los vertices correctos\n"
            "        # sin importar cuantas veces se haya ejecutado el .py o el estado\n"
            "        # previo de la malla en la escena del reproductor.\n"
            "        _side_key = 'eye_R' if is_right else 'eye_L'\n"
            "        _base_data = EYE_BASE_MESH_DATA if isinstance(EYE_BASE_MESH_DATA, dict) else {}\n"
            "        _base_verts = _base_data.get(_side_key)\n"
            "        if _base_verts and len(_base_verts) != len(eye_obj.data.vertices):\n"
            "            # Numero de vertices diferente: reconstruir malla desde cero\n"
            "            # Primero borrar shape keys para poder editar la malla\n"
            "            if eye_obj.data.shape_keys: eye_obj.shape_key_clear()\n"
            "            bpy.context.view_layer.objects.active = eye_obj\n"
            "            bpy.ops.object.mode_set(mode='EDIT')\n"
            "            bpy.ops.mesh.select_all(action='SELECT')\n"
            "            # Disolver todo y reconstruir desde un plano basico\n"
            "            bpy.ops.mesh.dissolve_limited()\n"
            "            # Volver a subdividir hasta alcanzar el conteo correcto\n"
            "            cuts = _base_data.get('subdivide_cuts', cfg.get('subdivide_cuts', 3))\n"
            "            for _ in range(cuts): bpy.ops.mesh.subdivide(number_cuts=1)\n"
            "            bpy.ops.object.mode_set(mode='OBJECT')\n"
            "        if _base_verts and len(_base_verts) == len(eye_obj.data.vertices):\n"
            "            # Restaurar coordenadas base exactas desde el snapshot exportado\n"
            "            if eye_obj.data.shape_keys: eye_obj.shape_key_clear()\n"
            "            for i, co in enumerate(_base_verts):\n"
            "                eye_obj.data.vertices[i].co.x = co[0]\n"
            "                eye_obj.data.vertices[i].co.y = co[1]\n"
            "                eye_obj.data.vertices[i].co.z = co[2]\n"
            "            eye_obj.data.update()\n"
            "        else:\n"
            "            # Fallback: comportamiento anterior si no hay datos base\n"
            "            cuts = cfg.get('subdivide_cuts', 3)\n"
            "            if cuts > 0 and len(eye_obj.data.vertices) <= 12:\n"
            "                bpy.context.view_layer.objects.active = eye_obj\n"
            "                bpy.ops.object.mode_set(mode='EDIT')\n"
            "                bpy.ops.mesh.select_all(action='SELECT')\n"
            "                for _ in range(cuts): bpy.ops.mesh.subdivide(number_cuts=1)\n"
            "                bpy.ops.object.mode_set(mode='OBJECT')\n"
            "            if eye_obj.data.shape_keys: eye_obj.shape_key_clear()\n"
            "        eye_obj.shape_key_add(name='Basis',from_mix=False)\n"
            "        mesh=eye_obj.data\n"
            "        orig=[v.co.copy() for v in mesh.vertices]\n"
            "        xs=[v.co.x for v in mesh.vertices]; ys=[v.co.y for v in mesh.vertices]; zs=[v.co.z for v in mesh.vertices]\n"
            "        bounds={'cx':(max(xs)+min(xs))/2,'cy':(max(ys)+min(ys))/2,'cz':(max(zs)+min(zs))/2,\n"
            "                'rx':max(xs)-min(xs),'ry':max(ys)-min(ys),'rz':max(zs)-min(zs)}\n"
            "        _side='R' if is_right else 'L'\n"
            "        _h_key=f'eye_{_side}_h_axis'; _v_key=f'eye_{_side}_v_axis'\n"
            "        if cfg.get(_h_key) and cfg.get(_v_key):\n"
            "            h_axis=cfg[_h_key]; v_axis=cfg[_v_key]\n"
            "        else:\n"
            "            h_axis,v_axis,_=_eye_detect_axes_exp(eye_obj)\n"
            "        if cfg.get('swap_axes',False): h_axis,v_axis=v_axis,h_axis\n"
            "        print(f'[eye_build] {eye_obj.name}: h={h_axis}, v={v_axis}, is_right={is_right}, verts={len(orig)}')\n"
            "        for expr in ('feliz','triste','enojado','sospecha','cerrado','cansado','sorpresa'):\n"
            "            sk=eye_obj.shape_key_add(name=expr.capitalize(),from_mix=False)\n"
            "            sk.value=0.0; sk.slider_min=-2.0; sk.slider_max=2.0\n"
            "            for i,o in enumerate(orig):\n"
            "                sk.data[i].co=_eye_compute_vertex_exp(o,h_axis,v_axis,bounds,expr,cfg,mirror_h=is_right)\n"
            "        sk_cl=eye_obj.shape_key_add(name='Closed',from_mix=False)\n"
            "        sk_cl.value=0.0\n"
            "        min_v=min(getattr(v.co,v_axis) for v in mesh.vertices)\n"
            "        for i,v in enumerate(mesh.vertices):\n"
            "            nc=v.co.copy(); setattr(nc,v_axis,min_v); sk_cl.data[i].co=nc\n\n"

            # ── Aplicar valor de expresion en un frame ──
            "    def _apply_expr_to_eye(eye_obj, expr_name, value, frame):\n"
            "        if not eye_obj.data.shape_keys: return\n"
            "        for sk in eye_obj.data.shape_keys.key_blocks:\n"
            "            if sk.name=='Basis': continue\n"
            "            sk.value=value if sk.name.lower()==expr_name.lower() else 0.0\n"
            "            sk.keyframe_insert(data_path='value',frame=frame)\n\n"

            "    def _set_sk_interp(eye_obj, frame, interp_type='LINEAR'):\n"
            "        \"\"\"Cambia la interpolacion del keyframe de shape key en un frame dado.\"\"\"\n"
            "        if not (eye_obj and eye_obj.data.shape_keys): return\n"
            "        action = eye_obj.data.shape_keys.animation_data.action if (\n"
            "            eye_obj.data.shape_keys.animation_data and\n"
            "            eye_obj.data.shape_keys.animation_data.action) else None\n"
            "        if not action: return\n"
            "        for fc in _get_fcurves(action):\n"
            "            for kp in fc.keyframe_points:\n"
            "                if abs(kp.co.x - frame) < 0.5:\n"
            "                    kp.interpolation = interp_type\n\n"

            "    def _set_obj_kf_interp(obj, frame, interp_type='LINEAR'):\n"
            "        \"\"\"Fija interpolacion de keyframes de loc/rot/sca del objeto en un frame.\"\"\"\n"
            "        if not (obj and obj.animation_data and obj.animation_data.action): return\n"
            "        for fc in _get_fcurves(obj.animation_data.action):\n"
            "            for kp in fc.keyframe_points:\n"
            "                if abs(kp.co.x - frame) < 0.5:\n"
            "                    kp.interpolation = interp_type\n\n"

            # ── Setup inicial: construir shape keys en ambos ojos ──
            "    _eye_data   = EYE_SEQUENCE_DATA if isinstance(EYE_SEQUENCE_DATA, dict) else {}\n"
            "    _eye_global = _eye_data.get('global', {})\n"
            "    # Fallback por compatibilidad con .py exportados antes de esta version\n"
            "    if 'EYE_BASE_MESH_DATA' not in dir():\n"
            "        EYE_BASE_MESH_DATA = {}\n"
            "    _eye_cfg    = {\n"
            "        'curve_mode':        _eye_global.get('curve_mode',        'QUADRATIC'),\n"
            "        'affect_zone':       _eye_global.get('affect_zone',       'UPPER'),\n"
            "        'invert_vertical':   _eye_global.get('invert_vertical',   True),\n"
            "        'invert_horizontal': _eye_global.get('invert_horizontal', False),\n"
            "        'swap_axes':         _eye_global.get('swap_axes',         False),\n"
            "        'subdivide_cuts':    _eye_global.get('subdivide_cuts',    3),\n"
            "        'intensity_feliz':   _eye_global.get('intensity_feliz',   0.18),\n"
            "        'intensity_triste':  _eye_global.get('intensity_triste',  0.18),\n"
            "        'intensity_enojado': _eye_global.get('intensity_enojado', 0.18),\n"
            "        'intensity_sospecha':_eye_global.get('intensity_sospecha',0.18),\n"
            "        # Ejes serializados: garantizan que se use la misma orientacion\n"
            "        # que tenia la malla cuando el usuario configuro las expresiones\n"
            "        'eye_L_h_axis':      _eye_global.get('eye_L_h_axis',      'x'),\n"
            "        'eye_L_v_axis':      _eye_global.get('eye_L_v_axis',      'z'),\n"
            "        'eye_R_h_axis':      _eye_global.get('eye_R_h_axis',      'x'),\n"
            "        'eye_R_v_axis':      _eye_global.get('eye_R_v_axis',      'z'),\n"
            "    }\n"
            "    _eye_L_obj = bpy.data.objects.get('ojo_izquierdo_cerdo_1')\n"
            "    _eye_R_obj = bpy.data.objects.get('ojo_derecho_cerdo_1')\n"
            "    if _eye_L_obj and _eye_L_obj.type=='MESH': _build_expr_shape_keys(_eye_L_obj, _eye_cfg, is_right=False)\n"
            "    if _eye_R_obj and _eye_R_obj.type=='MESH': _build_expr_shape_keys(_eye_R_obj, _eye_cfg, is_right=True)\n\n"

            # ── Procesar secuencia si está habilitada ──
            "    if _eye_global.get('enabled', False):\n"
            "        _eye_obj_map = {'ojo_izquierdo_cerdo_1': ('eye_L', False), 'ojo_derecho_cerdo_1': ('eye_R', True)}\n"

            "        def _apply_eye_frame(frame, eye_L_data, eye_R_data, expr_name, expr_val):\n"
            "            for obj_name, (key, is_r) in _eye_obj_map.items():\n"
            "                eye_obj = bpy.data.objects.get(obj_name)\n"
            "                if not eye_obj: continue\n"
            "                d = eye_L_data if key == 'eye_L' else eye_R_data\n"
            "                if d:\n"
            "                    loc=d.get('loc'); rot=d.get('rot'); sca=d.get('sca')\n"
            "                    if loc: eye_obj.location=loc\n"
            "                    if rot: eye_obj.rotation_euler=rot\n"
            "                    if sca: eye_obj.scale=sca\n"
            "                    if loc: eye_obj.keyframe_insert(data_path='location',frame=frame)\n"
            "                    if rot: eye_obj.keyframe_insert(data_path='rotation_euler',frame=frame)\n"
            "                    if sca: eye_obj.keyframe_insert(data_path='scale',frame=frame)\n"
            "                    # Forzar LINEAR en loc/rot/sca para respetar duraciones exactas\n"
            "                    _set_obj_kf_interp(eye_obj, frame, 'LINEAR')\n"
            "                _is_neutral = (not expr_name) or expr_name.lower() == 'neutral'\n"
            "                if _is_neutral:\n"
            "                    if eye_obj.data.shape_keys:\n"
            "                        for sk in eye_obj.data.shape_keys.key_blocks:\n"
            "                            if sk.name == 'Basis': continue\n"
            "                            sk.value = 0.0\n"
            "                            sk.keyframe_insert(data_path='value', frame=frame)\n"
            "                        _set_sk_interp(eye_obj, frame, 'CONSTANT')\n"
            "                else:\n"
            "                    _apply_expr_to_eye(eye_obj, expr_name.lower(), expr_val, frame)\n"
            "                    _set_sk_interp(eye_obj, frame, 'LINEAR')\n\n"

            "        def _lerp_eye_state(a, b, t):\n"
            "            def _lv(va,vb,tt):\n"
            "                if va is None or vb is None: return vb\n"
            "                return [va[i]+(vb[i]-va[i])*tt for i in range(len(va))]\n"
            "            return {ch:_lv(a.get(ch),b.get(ch),t) for ch in ('loc','rot','sca')}\n\n"

            "        _eye_gstart = _eye_global.get('global_start_frame', start_frame)\n"
            "        _cursor = _eye_gstart\n"
            "\n"
            "        # ── Anclas NEUTRAL: forzar 0.0 en start_frame, gstart-1 y end_frame ──\n"
            "        # Previene que Blender extrapole la expresion fuera del intervalo asignado\n"
            "        for _anc_name in ['ojo_izquierdo_cerdo_1', 'ojo_derecho_cerdo_1']:\n"
            "            _anc_obj = bpy.data.objects.get(_anc_name)\n"
            "            if not _anc_obj: continue\n"
            "            # Anclar loc/rot/sca en start_frame y _eye_gstart-1 (CONSTANT)\n"
            "            # Usar posicion del bloque 'start' como posicion neutra de referencia\n"
            "            _anc_st = _eye_data.get('start', {})\n"
            "            _anc_key = 'eye_L' if 'izquierdo' in _anc_name else 'eye_R'\n"
            "            _anc_st_d = _anc_st.get(_anc_key, {})\n"
            "            _anc_loc0 = _anc_st_d.get('loc'); _anc_rot0 = _anc_st_d.get('rot'); _anc_sca0 = _anc_st_d.get('sca')\n"
            "            for _af in [start_frame, _eye_gstart - 1]:\n"
            "                if _af < start_frame: continue\n"
            "                if _anc_loc0: _anc_obj.location = _anc_loc0\n"
            "                if _anc_rot0: _anc_obj.rotation_euler = _anc_rot0\n"
            "                if _anc_sca0: _anc_obj.scale = _anc_sca0\n"
            "                _anc_obj.keyframe_insert(data_path='location',       frame=_af)\n"
            "                _anc_obj.keyframe_insert(data_path='rotation_euler', frame=_af)\n"
            "                _anc_obj.keyframe_insert(data_path='scale',          frame=_af)\n"
            "                _set_obj_kf_interp(_anc_obj, _af, 'CONSTANT')\n"
            "            if not _anc_obj.data.shape_keys: continue\n"
            "            for sk in _anc_obj.data.shape_keys.key_blocks:\n"
            "                if sk.name == 'Basis' or sk.name == 'Closed': continue\n"
            "                sk.value = 0.0\n"
            "                sk.keyframe_insert(data_path='value', frame=start_frame)\n"
            "                if _eye_gstart > start_frame:\n"
            "                    sk.keyframe_insert(data_path='value', frame=_eye_gstart - 1)\n"
            "                sk.keyframe_insert(data_path='value', frame=end_frame)\n"
            "            # CONSTANT: el ancla no puede 'subir' hacia los frames vecinos\n"
            "            for _af in [start_frame, _eye_gstart - 1, end_frame]:\n"
            "                if _af < start_frame: continue\n"
            "                _set_sk_interp(_anc_obj, _af, 'CONSTANT')\n"
            "\n"
            "        _st_data  = _eye_data.get('start', {})\n"
            "        _st_dur   = int(_st_data.get('duration', 2))\n"
            "        _st_eye_L = _st_data.get('eye_L', {})\n"
            "        _st_eye_R = _st_data.get('eye_R', {})\n"
            "        _st_expr  = _st_data.get('active_expression', 'NEUTRAL')\n"
            "        _st_val   = float(_st_data.get('expression_value', 1.0))\n"
            "        for f in range(_cursor, _cursor + _st_dur):\n"
            "            _apply_eye_frame(f, _st_eye_L, _st_eye_R, _st_expr, _st_val)\n"
            "        _cursor += _st_dur\n"

            "        _prev_eye_L = _st_eye_L; _prev_eye_R = _st_eye_R\n"
            "        for _slot in _eye_data.get('slots', []):\n"
            "            _sl_dur   = int(_slot.get('duration', 4))\n"
            "            _sl_eye_L = _slot.get('eye_L', {})\n"
            "            _sl_eye_R = _slot.get('eye_R', {})\n"
            "            _sl_expr  = _slot.get('active_expression', 'NEUTRAL')\n"
            "            _sl_val   = float(_slot.get('expression_value', 1.0))\n"
            "            for _fi in range(_sl_dur):\n"
            "                _t = (_fi + 1) / _sl_dur if _sl_dur > 0 else 1.0\n"
            "                _il = _lerp_eye_state(_prev_eye_L, _sl_eye_L, _t)\n"
            "                _ir = _lerp_eye_state(_prev_eye_R, _sl_eye_R, _t)\n"
            "                _apply_eye_frame(_cursor + _fi, _il, _ir, _sl_expr, _sl_val)\n"
            "            _prev_eye_L = _sl_eye_L; _prev_eye_R = _sl_eye_R\n"
            "            _cursor += _sl_dur\n"

            "        _en_data  = _eye_data.get('end', {})\n"
            "        _en_dur   = int(_en_data.get('duration', 3))\n"
            "        _en_eye_L = _en_data.get('eye_L', {})\n"
            "        _en_eye_R = _en_data.get('eye_R', {})\n"
            "        _en_expr  = _en_data.get('active_expression', 'NEUTRAL')\n"
            "        _en_val   = float(_en_data.get('expression_value', 1.0))\n"
            "        for f in range(_cursor, _cursor + _en_dur):\n"
            "            _apply_eye_frame(f, _en_eye_L, _en_eye_R, _en_expr, _en_val)\n"
            "        # Keyframe de cierre: forzar 0.0 en shape keys y CONSTANT en loc/rot/sca\n"
            "        # en el ultimo frame del slot para evitar extrapolacion Bezier\n"
            "        for _eo_close_name in ['ojo_izquierdo_cerdo_1', 'ojo_derecho_cerdo_1']:\n"
            "            _eo_close = bpy.data.objects.get(_eo_close_name)\n"
            "            if _eo_close and _eo_close.data.shape_keys:\n"
            "                for sk in _eo_close.data.shape_keys.key_blocks:\n"
            "                    if sk.name == 'Basis' or sk.name == 'Closed': continue\n"
            "                    sk.value = 0.0\n"
            "                    sk.keyframe_insert(data_path='value', frame=end_frame)\n"
            "                _set_sk_interp(_eo_close, end_frame, 'CONSTANT')\n"
            "            # Tambien fijar loc/rot/sca CONSTANT en end_frame para bloquear extrapolacion\n"
            "            if _eo_close:\n"
            "                _eo_close.keyframe_insert(data_path='location',       frame=end_frame)\n"
            "                _eo_close.keyframe_insert(data_path='rotation_euler', frame=end_frame)\n"
            "                _eo_close.keyframe_insert(data_path='scale',          frame=end_frame)\n"
            "                _set_obj_kf_interp(_eo_close, end_frame, 'CONSTANT')\n"
            "            # Y tambien en start_frame para bloquear extrapolacion hacia atras\n"
            "            if _eo_close:\n"
            "                _eo_close.keyframe_insert(data_path='location',       frame=start_frame)\n"
            "                _eo_close.keyframe_insert(data_path='rotation_euler', frame=start_frame)\n"
            "                _eo_close.keyframe_insert(data_path='scale',          frame=start_frame)\n"
            "                _set_obj_kf_interp(_eo_close, start_frame, 'CONSTANT')\n\n"

            # ── Parpadeo: blink_intervals tiene prioridad sobre legacy ──
            "        if _eye_global.get('blink_enabled', False):\n"
            "            _intervals = _eye_global.get('blink_intervals', [])\n"
            "            if _intervals:\n"
            "                _bidx = _eye_global.get('blink_interval_idx', 0)\n"
            "                _bidx = min(_bidx, len(_intervals) - 1)\n"
            "                _bi   = _intervals[_bidx]\n"
            "                _blink_count    = _bi.get('blink_count',    2)\n"
            "                _blink_duration = _bi.get('blink_duration', 9)\n"
            "                _blink_fs       = int(_bi.get('frame_start', start_frame))\n"
            "                _blink_fe       = int(_bi.get('frame_end',   end_frame))\n"
            "                _bi_enabled     = _bi.get('enabled', True)\n"
            "            else:\n"
            "                _blink_count    = _eye_global.get('blink_count',    2)\n"
            "                _blink_duration = _eye_global.get('blink_duration', 9)\n"
            "                _blink_fs       = int(_eye_global.get('blink_frame_start', start_frame))\n"
            "                _blink_fe       = int(_eye_global.get('blink_frame_end',   end_frame))\n"
            "                _bi_enabled     = True\n"
            "            if _bi_enabled and _blink_count > 0:\n"
            "                _slot_dur = _blink_fe - _blink_fs + 1\n"
            "                _segment  = _slot_dur / _blink_count\n"
            "                _blink_starts = []\n"
            "                for _bn in range(_blink_count):\n"
            "                    _center = _blink_fs + _segment * (_bn + 0.5)\n"
            "                    _bs = int(_center - _blink_duration / 2)\n"
            "                    _bs = max(_blink_fs, min(_bs, _blink_fe - _blink_duration))\n"
            "                    _blink_starts.append(_bs)\n"
            "                for t in range(_blink_fs, _blink_fe + 1):\n"
            "                    _blink_applied = False\n"
            "                    for _blink_start in _blink_starts:\n"
            "                        if _blink_start <= t < _blink_start + _blink_duration:\n"
            "                            _blink_applied = True\n"
            "                            offset     = t - _blink_start + 1\n"
            "                            frame_data = BLINK_SEQUENCE.get(offset, {'closed': 0.0, 'hide': False})\n"
            "                            progress   = frame_data['closed']\n"
            "                            hide_eye   = frame_data['hide']\n"
            "                            for eye_name in ['ojo_izquierdo_cerdo_1', 'ojo_derecho_cerdo_1']:\n"
            "                                eye = bpy.data.objects.get(eye_name)\n"
            "                                if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:\n"
            "                                    ck = eye.data.shape_keys.key_blocks.get('Closed')\n"
            "                                    if ck:\n"
            "                                        ck.value = progress\n"
            "                                        ck.keyframe_insert(data_path='value', frame=t)\n"
            "                                        eye.hide_viewport = hide_eye\n"
            "                                        eye.hide_render   = hide_eye\n"
            "                                        eye.keyframe_insert(data_path='hide_viewport', frame=t)\n"
            "                                        eye.keyframe_insert(data_path='hide_render',   frame=t)\n"
            "                            break\n"
            "                    if not _blink_applied:\n"
            "                        for eye_name in ['ojo_izquierdo_cerdo_1', 'ojo_derecho_cerdo_1']:\n"
            "                            eye = bpy.data.objects.get(eye_name)\n"
            "                            if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:\n"
            "                                ck = eye.data.shape_keys.key_blocks.get('Closed')\n"
            "                                if ck:\n"
            "                                    ck.value = 0.0\n"
            "                                    ck.keyframe_insert(data_path='value', frame=t)\n"
            "                                    eye.hide_viewport = False\n"
            "                                    eye.hide_render   = False\n"
            "                                    eye.keyframe_insert(data_path='hide_viewport', frame=t)\n"
            "                                    eye.keyframe_insert(data_path='hide_render',   frame=t)\n"
            "    else:\n"
            "        # EYE_SEQUENCE_DATA deshabilitado: fallback legacy EXPRESSION_CONFIG\n"
            "        if EXPRESSION_CONFIG.get('blink_enabled', True):\n"
            "            _blink_count    = EXPRESSION_CONFIG.get('blink_count', 2)\n"
            "            _blink_duration = EXPRESSION_CONFIG.get('blink_duration', 9)\n"
            "            _blink_fs = EXPRESSION_CONFIG.get('blink_frame_start', start_frame)\n"
            "            _blink_fe = EXPRESSION_CONFIG.get('blink_frame_end',   end_frame)\n"
            "            _slot_dur = _blink_fe - _blink_fs + 1\n"
            "            _segment  = _slot_dur / _blink_count if _blink_count > 0 else _slot_dur\n"
            "            _blink_starts = []\n"
            "            for _bi in range(_blink_count):\n"
            "                _center = _blink_fs + _segment * (_bi + 0.5)\n"
            "                _bs = int(_center - _blink_duration / 2)\n"
            "                _bs = max(_blink_fs, min(_bs, _blink_fe - _blink_duration))\n"
            "                _blink_starts.append(_bs)\n"
            "            for t in range(_blink_fs, _blink_fe + 1):\n"
            "                _blink_applied = False\n"
            "                for _blink_start in _blink_starts:\n"
            "                    if _blink_start <= t < _blink_start + _blink_duration:\n"
            "                        _blink_applied = True\n"
            "                        offset     = t - _blink_start + 1\n"
            "                        frame_data = BLINK_SEQUENCE.get(offset, {'closed': 0.0, 'hide': False})\n"
            "                        progress   = frame_data['closed']\n"
            "                        hide_eye   = frame_data['hide']\n"
            "                        for eye_name in ['ojo_izquierdo_cerdo_1', 'ojo_derecho_cerdo_1']:\n"
            "                            eye = bpy.data.objects.get(eye_name)\n"
            "                            if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:\n"
            "                                ck = eye.data.shape_keys.key_blocks.get('Closed')\n"
            "                                if ck:\n"
            "                                    ck.value = progress\n"
            "                                    ck.keyframe_insert(data_path='value', frame=t)\n"
            "                                    eye.hide_viewport = hide_eye\n"
            "                                    eye.hide_render   = hide_eye\n"
            "                                    eye.keyframe_insert(data_path='hide_viewport', frame=t)\n"
            "                                    eye.keyframe_insert(data_path='hide_render',   frame=t)\n"
            "                        break\n"
            "                if not _blink_applied:\n"
            "                    for eye_name in ['ojo_izquierdo_cerdo_1', 'ojo_derecho_cerdo_1']:\n"
            "                        eye = bpy.data.objects.get(eye_name)\n"
            "                        if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:\n"
            "                            ck = eye.data.shape_keys.key_blocks.get('Closed')\n"
            "                            if ck:\n"
            "                                ck.value = 0.0\n"
            "                                ck.keyframe_insert(data_path='value', frame=t)\n"
            "                                eye.hide_viewport = False\n"
            "                                eye.hide_render   = False\n"
            "                                eye.keyframe_insert(data_path='hide_viewport', frame=t)\n"
            "                                eye.keyframe_insert(data_path='hide_render',   frame=t)\n\n"
            "                _bs = max(_blink_fs, min(_bs, _blink_fe - _blink_duration))\n"
            "                _blink_starts.append(_bs)\n"
            "            for t in range(_blink_fs, _blink_fe + 1):\n"
            "                _blink_applied = False\n"
            "                for _blink_start in _blink_starts:\n"
            "                    if _blink_start <= t < _blink_start + _blink_duration:\n"
            "                        _blink_applied = True\n"
            "                        offset     = t - _blink_start + 1\n"
            "                        frame_data = BLINK_SEQUENCE.get(offset, {'closed': 0.0, 'hide': False})\n"
            "                        progress   = frame_data['closed']\n"
            "                        hide_eye   = frame_data['hide']\n"
            "                        for eye_name in ['ojo_izquierdo_cerdo_1', 'ojo_derecho_cerdo_1']:\n"
            "                            eye = bpy.data.objects.get(eye_name)\n"
            "                            if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:\n"
            "                                ck = eye.data.shape_keys.key_blocks.get('Closed')\n"
            "                                if ck:\n"
            "                                    ck.value = progress\n"
            "                                    ck.keyframe_insert(data_path='value', frame=t)\n"
            "                                    eye.hide_viewport = hide_eye\n"
            "                                    eye.hide_render   = hide_eye\n"
            "                                    eye.keyframe_insert(data_path='hide_viewport', frame=t)\n"
            "                                    eye.keyframe_insert(data_path='hide_render',   frame=t)\n"
            "                        break\n"
            "                if not _blink_applied:\n"
            "                    for eye_name in ['ojo_izquierdo_cerdo_1', 'ojo_derecho_cerdo_1']:\n"
            "                        eye = bpy.data.objects.get(eye_name)\n"
            "                        if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:\n"
            "                            ck = eye.data.shape_keys.key_blocks.get('Closed')\n"
            "                            if ck:\n"
            "                                ck.value = 0.0\n"
            "                                ck.keyframe_insert(data_path='value', frame=t)\n"
            "                                eye.hide_viewport = False\n"
            "                                eye.hide_render   = False\n"
            "                                eye.keyframe_insert(data_path='hide_viewport', frame=t)\n"
            "                                eye.keyframe_insert(data_path='hide_render',   frame=t)\n\n"
            "    if bpy.context.scene.frame_end < end_frame:\n"
            "        bpy.context.scene.frame_end = end_frame\n\n"
            "    slot_label = SLOT_INDEX if SLOT_INDEX is not None else '?'\n"
            f"    print(f'OK: Slot {{slot_label}} {anim_name} completado  [{{start_frame}}-{{end_frame}}]')\n\n"
            "    # ── Forzar pose exacta en primer y ultimo frame ──\n"
            f"    _POSE_FRAME_1   = {repr(p_ini)}\n"
            f"    _POSE_FRAME_END = {repr(p_fin)}\n"
            "    for _sp_bone in armature.pose.bones:\n"
            "        _sp_bone.rotation_mode = 'XYZ'\n"
            "        if _sp_bone.name in _POSE_FRAME_1:\n"
            "            bpy.context.scene.frame_set(start_frame)\n"
            "            _sp_bone.rotation_euler = _POSE_FRAME_1[_sp_bone.name]\n"
            "            _sp_bone.keyframe_insert(data_path='rotation_euler', frame=start_frame)\n"
            "        if _sp_bone.name in _POSE_FRAME_END:\n"
            "            bpy.context.scene.frame_set(end_frame)\n"
            "            _sp_bone.rotation_euler = _POSE_FRAME_END[_sp_bone.name]\n"
            "            _sp_bone.keyframe_insert(data_path='rotation_euler', frame=end_frame)\n"
            "    # ── Fin forzado ──\n\n"
            "    # Mover Action del ARMATURE al NLA\n"
            "    if armature.animation_data and armature.animation_data.action:\n"
            "        _arm_done  = armature.animation_data.action\n"
            "        armature.animation_data.action = None\n"
            "        _arm_track = armature.animation_data.nla_tracks.new()\n"
            f"        _arm_track.name = f'Slot_{{SLOT_INDEX:03d}}_arm'\n"
            "        _arm_strip = _arm_track.strips.new(_arm_done.name, start_frame, _arm_done)\n"
            "        _arm_strip.frame_end        = end_frame\n"
            "        _arm_strip.extrapolation    = 'NOTHING'\n"
            "        _arm_strip.use_auto_blend   = False\n"
            "        _arm_strip.blend_in         = 0\n"
            "        _arm_strip.blend_out        = 0\n\n"
            "    # Mover Action del ROOT al NLA\n"
            "    if root and root.animation_data and root.animation_data.action:\n"
            "        _root_done  = root.animation_data.action\n"
            "        root.animation_data.action = None\n"
            "        _root_track = root.animation_data.nla_tracks.new()\n"
            f"        _root_track.name = f'Slot_{{SLOT_INDEX:03d}}_root'\n"
            "        _root_strip = _root_track.strips.new(_root_done.name, start_frame, _root_done)\n"
            "        _root_strip.frame_end        = end_frame\n"
            "        _root_strip.extrapolation    = 'HOLD_FORWARD'\n"
            "        _root_strip.use_auto_blend   = False\n"
            "        _root_strip.blend_in         = 0\n"
            "        _root_strip.blend_out        = 0\n\n"
            "    # ── Aplicar EYE_SEQUENCE_DATA autonomamente (para animation_engine.py) ──\n"
            "    _eye_seq_alf = EYE_SEQUENCE_DATA if isinstance(EYE_SEQUENCE_DATA, dict) else {}\n"
            "    _eye_global_alf = _eye_seq_alf.get('global', {})\n"
            "    if _eye_global_alf.get('enabled', False):\n"
            "        _eye_gstart_alf = _eye_global_alf.get('global_start_frame', start_frame)\n"
            "        def _eye_smooth_alf(t):\n"
            "            t = max(0.0, min(1.0, t)); return t * t * (3.0 - 2.0 * t)\n"
            "        def _eye_lerp_alf(a, b, t):\n"
            "            if a is None or b is None: return b\n"
            "            return [a[i] + (b[i] - a[i]) * t for i in range(len(a))]\n"
            "        def _eye_lerp_td_alf(td_a, td_b, t):\n"
            "            return {'loc': _eye_lerp_alf(td_a.get('loc'), td_b.get('loc'), t),\n"
            "                    'rot': _eye_lerp_alf(td_a.get('rot'), td_b.get('rot'), t),\n"
            "                    'sca': _eye_lerp_alf(td_a.get('sca'), td_b.get('sca'), t)}\n"
            "        def _eye_apply_td_alf(frame, eL, eR):\n"
            "            for obj_name, td in [('ojo_izquierdo_cerdo_1', eL), ('ojo_derecho_cerdo_1', eR)]:\n"
            "                _eo = bpy.data.objects.get(obj_name)\n"
            "                if not _eo: continue\n"
            "                if td.get('loc'): _eo.location = td['loc']; _eo.keyframe_insert(data_path='location', frame=frame)\n"
            "                if td.get('rot'): _eo.rotation_euler = td['rot']; _eo.keyframe_insert(data_path='rotation_euler', frame=frame)\n"
            "                if td.get('sca'): _eo.scale = td['sca']; _eo.keyframe_insert(data_path='scale', frame=frame)\n"
            "        _eye_states_alf = [_eye_seq_alf.get('start', {})] + _eye_seq_alf.get('slots', []) + [_eye_seq_alf.get('end', {})]\n"
            "        _eye_cur_alf = _eye_gstart_alf\n"
            "        for _esi in range(len(_eye_states_alf) - 1):\n"
            "            _es_a = _eye_states_alf[_esi]; _es_b = _eye_states_alf[_esi + 1]\n"
            "            _en_alf = int(_es_b.get('duration', 20)); _eitp = _es_b.get('interp_type', 'SMOOTH')\n"
            "            _eL_a = _es_a.get('eye_L', {}); _eL_b = _es_b.get('eye_L', {})\n"
            "            _eR_a = _es_a.get('eye_R', {}); _eR_b = _es_b.get('eye_R', {})\n"
            "            for _efi in range(_en_alf):\n"
            "                _eabs = _eye_cur_alf + _efi\n"
            "                if _eabs > end_frame: break\n"
            "                _raw_t = (_efi + 1) / _en_alf if _en_alf > 0 else 1.0\n"
            "                _et = _eye_smooth_alf(_raw_t) if _eitp in ('SMOOTH', 'BEZIER') else _raw_t\n"
            "                if _eL_a and _eL_b: _eye_apply_td_alf(_eabs, _eye_lerp_td_alf(_eL_a, _eL_b, _et), _eye_lerp_td_alf(_eR_a, _eR_b, _et))\n"
            "            _eye_cur_alf += _en_alf\n"
            "        if _eye_global_alf.get('blink_enabled', False):\n"
            "            _eye_intervals_alf = _eye_global_alf.get('blink_intervals', [])\n"
            "            if _eye_intervals_alf:\n"
            "                _eye_bi_alf = _eye_intervals_alf[min(_eye_global_alf.get('blink_interval_idx', 0), len(_eye_intervals_alf) - 1)]\n"
            "            else:\n"
            "                _eye_bi_alf = {'frame_start': _eye_global_alf.get('blink_frame_start', start_frame), 'frame_end': _eye_global_alf.get('blink_frame_end', end_frame), 'blink_count': _eye_global_alf.get('blink_count', 5), 'blink_duration': _eye_global_alf.get('blink_duration', 9), 'enabled': True}\n"
            "            if _eye_bi_alf.get('enabled', True):\n"
            "                _bk_sq_alf = {1:(0.0,False),2:(0.25,False),3:(0.5,False),4:(0.75,False),5:(1.0,True),6:(1.0,True),7:(0.75,False),8:(0.5,False),9:(0.25,False)}\n"
            "                _bk_sf_alf = int(_eye_bi_alf.get('frame_start', start_frame)); _bk_ef_alf = int(_eye_bi_alf.get('frame_end', end_frame))\n"
            "                _bk_cnt_alf = _eye_bi_alf.get('blink_count', 5); _bk_dur_alf = _eye_bi_alf.get('blink_duration', 9)\n"
            "                _bk_seg_alf = (_bk_ef_alf - _bk_sf_alf + 1) / _bk_cnt_alf if _bk_cnt_alf > 0 else (_bk_ef_alf - _bk_sf_alf + 1)\n"
            "                _bk_starts_alf = [max(_bk_sf_alf, min(int(_bk_sf_alf + _bk_seg_alf * (i + 0.5) - _bk_dur_alf / 2), _bk_ef_alf - _bk_dur_alf)) for i in range(_bk_cnt_alf)]\n"
            "                for _bt_alf in range(_bk_sf_alf, _bk_ef_alf + 1):\n"
            "                    _bk_done_alf = False\n"
            "                    for _bs_alf in _bk_starts_alf:\n"
            "                        if _bs_alf <= _bt_alf < _bs_alf + _bk_dur_alf:\n"
            "                            _bk_prog_alf, _bk_hide_alf = _bk_sq_alf.get(min(_bt_alf - _bs_alf + 1, 9), (0.0, False))\n"
            "                            for _eon_alf in ('ojo_izquierdo_cerdo_1', 'ojo_derecho_cerdo_1'):\n"
            "                                _eo2_alf = bpy.data.objects.get(_eon_alf)\n"
            "                                if _eo2_alf and hasattr(_eo2_alf.data, 'shape_keys') and _eo2_alf.data.shape_keys:\n"
            "                                    _ck2_alf = _eo2_alf.data.shape_keys.key_blocks.get('Closed')\n"
            "                                    if _ck2_alf: _ck2_alf.value = _bk_prog_alf; _ck2_alf.keyframe_insert(data_path='value', frame=_bt_alf)\n"
            "                                    _eo2_alf.hide_viewport = _bk_hide_alf; _eo2_alf.hide_render = _bk_hide_alf\n"
            "                                    _eo2_alf.keyframe_insert(data_path='hide_viewport', frame=_bt_alf)\n"
            "                                    _eo2_alf.keyframe_insert(data_path='hide_render', frame=_bt_alf)\n"
            "                            _bk_done_alf = True; break\n"
            "                    if not _bk_done_alf:\n"
            "                        for _eon_alf in ('ojo_izquierdo_cerdo_1', 'ojo_derecho_cerdo_1'):\n"
            "                            _eo2_alf = bpy.data.objects.get(_eon_alf)\n"
            "                            if _eo2_alf and hasattr(_eo2_alf.data, 'shape_keys') and _eo2_alf.data.shape_keys:\n"
            "                                _ck2_alf = _eo2_alf.data.shape_keys.key_blocks.get('Closed')\n"
            "                                if _ck2_alf: _ck2_alf.value = 0.0; _ck2_alf.keyframe_insert(data_path='value', frame=_bt_alf)\n"
            "                                _eo2_alf.hide_viewport = False; _eo2_alf.hide_render = False\n"
            "                                _eo2_alf.keyframe_insert(data_path='hide_viewport', frame=_bt_alf)\n"
            "                                _eo2_alf.keyframe_insert(data_path='hide_render', frame=_bt_alf)\n"
            "        print('[eye_seq_alf] EYE_SEQUENCE_DATA aplicado autonomamente')\n\n"
            "    # ── Aplicar oscilaciones de bones si estan definidas ──\n"
            "    if BONE_OSCILLATIONS_CONFIG.get('enabled') and BONE_OSCILLATIONS_CONFIG.get('items'):\n"
            "        import math as _m\n"
            "        def _noise_osc_alf(frame, speed, seed, dim=0):\n"
            "            import mathutils\n"
            "            scale = speed * 20.0\n"
            "            p = mathutils.noise.noise_vector(\n"
            "                mathutils.Vector((frame*scale+seed*13.7, dim*137.3+seed*0.17, 0.0)))\n"
            "            return p[0]\n"
            "        def _wave_val_alf(wt, frame, speed, phase, seed):\n"
            "            t = frame * speed * 2 * _m.pi + phase\n"
            "            # ── Clásicas ──────────────────────────────────────────────────\n"
            "            if wt == 'SINE': return _m.sin(t)\n"
            "            elif wt == 'TRIANGLE':\n"
            "                frac = (t/(2*_m.pi)) % 1.0\n"
            "                return 1.0 - abs(4.0*frac - 2.0) + 1.0 - 2.0\n"
            "            elif wt == 'SQUARE': return 1.0 if _m.sin(t) >= 0 else -1.0\n"
            "            elif wt == 'NOISE': return _noise_osc_alf(frame, speed, seed)\n"
            "            # ── Orgánicas suaves ──────────────────────────────────────────\n"
            "            elif wt == 'SINE_EASE':\n"
            "                s = (_m.sin(t) + 1.0) * 0.5\n"
            "                s = s*s*(3.0-2.0*s)\n"
            "                return s*2.0-1.0\n"
            "            elif wt == 'ELASTIC':\n"
            "                frac = (t/(2*_m.pi)) % 1.0\n"
            "                if frac < 0.6:\n"
            "                    v = _m.sin(frac/0.6*_m.pi*0.5)\n"
            "                else:\n"
            "                    r = (frac-0.6)/0.4; decay = _m.exp(-r*4.0)\n"
            "                    v = -decay*_m.cos(r*_m.pi*5.0)*0.35\n"
            "                return v\n"
            "            elif wt == 'BOUNCE':\n"
            "                frac = (t/(2*_m.pi)) % 1.0\n"
            "                peaks = [(0.0,1.0),(0.55,0.45),(0.78,0.18),(0.92,0.06),(1.0,0.0)]\n"
            "                for i in range(len(peaks)-1):\n"
            "                    x0,h0=peaks[i]; x1,h1=peaks[i+1]\n"
            "                    if x0 <= frac < x1:\n"
            "                        lc=(frac-x0)/(x1-x0); hm=(h0+h1)*0.5\n"
            "                        return hm*(1.0-(2.0*lc-1.0)**2)*2.0-0.5\n"
            "                return -0.5\n"
            "            elif wt == 'BREATHE':\n"
            "                frac = (t/(2*_m.pi)) % 1.0\n"
            "                if frac < 0.6: v = _m.sin(frac/0.6*_m.pi)\n"
            "                else: v = -_m.sin((frac-0.6)/0.4*_m.pi)*0.4\n"
            "                return v\n"
            "            elif wt == 'HEARTBEAT':\n"
            "                frac = (t/(2*_m.pi)) % 1.0\n"
            "                def _p(x,c,w): return _m.sin((x-c)/w*_m.pi) if abs(x-c)<w else 0.0\n"
            "                return _p(frac,0.10,0.08) + _p(frac,0.25,0.05)*0.6\n"
            "            # ── Ruido controlado ──────────────────────────────────────────\n"
            "            elif wt == 'NOISE_DRIFT':\n"
            "                hi = _noise_osc_alf(frame, speed, seed)\n"
            "                dr = _m.sin(frame*speed*0.3*_m.pi+phase)\n"
            "                return hi*0.6+dr*0.4\n"
            "            elif wt == 'NOISE_LAYERED':\n"
            "                n1=_noise_osc_alf(frame,speed,seed)\n"
            "                n2=_noise_osc_alf(frame,speed*2.7,seed+31)\n"
            "                n3=_noise_osc_alf(frame,speed*7.0,seed+97)\n"
            "                return n1*0.55+n2*0.30+n3*0.15\n"
            "            # ── Asimétricas / gestuales ───────────────────────────────────\n"
            "            elif wt == 'SAW_SMOOTH':\n"
            "                frac = (t/(2*_m.pi)) % 1.0\n"
            "                if frac < 0.8: v = (frac/0.8); v = v*v*(3.0-2.0*v)*2.0-1.0\n"
            "                else: v = 1.0-(frac-0.8)/0.2*2.0\n"
            "                return v\n"
            "            elif wt == 'SAW_REVERSE':\n"
            "                frac = (t/(2*_m.pi)) % 1.0\n"
            "                if frac < 0.2: v = frac/0.2\n"
            "                else: v = 1.0-(frac-0.2)/0.8; v = v*v*(3.0-2.0*v)\n"
            "                return v*2.0-1.0\n"
            "            elif wt == 'PENDULUM':\n"
            "                s = _m.sin(t)\n"
            "                if abs(s) < 0.9999: return _m.asin(s)/(_m.pi*0.5)\n"
            "                return _m.copysign(1.0,s)\n"
            "            elif wt == 'QUIVER':\n"
            "                env = (_m.sin(t*0.25)+1.0)*0.5\n"
            "                q   = _m.sin(t*7.0+_m.sin(t*2.3)*1.5)\n"
            "                return q*(0.4+env*0.6)\n"
            "            return _m.sin(t)\n"
            "        _arm_osc = armature  # 'armature' ya esta resuelto en este scope\n"
            "        if _arm_osc and _arm_osc.animation_data and _arm_osc.animation_data.action:\n"
            "            _act_osc = _arm_osc.animation_data.action\n"
            "            for _it in BONE_OSCILLATIONS_CONFIG['items']:\n"
            "                if not _it.get('enabled', True): continue\n"
            "                _bn  = _it.get('bone_name', '').strip()\n"
            "                if not _bn: continue\n"
            "                _sf2 = int(_it.get('frame_start', start_frame))\n"
            "                _ef2 = int(_it.get('frame_end', end_frame))\n"
            "                if _sf2 >= _ef2: continue\n"
            "                _dur2   = _ef2 - _sf2\n"
            "                _speed2 = _it.get('num_cycles', 4) / max(1, _dur2)\n"
            "                _amp2   = _m.radians(_it.get('amplitude', 30.0))\n"
            "                _off2   = _m.radians(_it.get('angle_offset', 0.0))\n"
            "                _ph2    = _it.get('phase', 0.0)\n"
            "                _wt2    = _it.get('wave_type', 'SINE')\n"
            "                _sd2    = _it.get('noise_seed', 42)\n"
            "                _fi2    = max(0, _it.get('fade_in', 6))\n"
            "                _fo2    = max(0, _it.get('fade_out', 6))\n"
            "                _axes2  = [(ax, idx) for ax, idx, key in [('X',0,'axis_x'),('Y',1,'axis_y'),('Z',2,'axis_z')] if _it.get(key, ax=='Z')]\n"
            "                _dp2    = f'pose.bones[\"{_bn}\"].rotation_euler'\n"
            "                for _ax2, _ai2 in _axes2:\n"
            "                    _fc2 = _get_fcurves(_act_osc).find(_dp2, index=_ai2)\n"
            "                    if _fc2 is None:\n"
            "                        _fc2 = _get_fcurves(_act_osc).new(_dp2, index=_ai2, action_group=_bn)\n"
            "                    _idxs2 = [i for i, kp in enumerate(_fc2.keyframe_points) if _sf2 <= int(kp.co.x) <= _ef2]\n"
            "                    for i in reversed(_idxs2): _fc2.keyframe_points.remove(_fc2.keyframe_points[i])\n"
            "                    for _f2 in range(_sf2, _ef2+1):\n"
            "                        _raw2 = _wave_val_alf(_wt2, _f2, _speed2, _ph2, _sd2)\n"
            "                        _v2   = _off2 + _amp2 * _raw2\n"
            "                        if _fi2 > 0 and (_f2-_sf2) < _fi2:\n"
            "                            _t2 = (_f2-_sf2)/_fi2; _t2 = _t2*_t2*(3-2*_t2)\n"
            "                            _v2 = _off2 + (_v2-_off2)*_t2\n"
            "                        if _fo2 > 0 and (_ef2-_f2) < _fo2:\n"
            "                            _t2 = (_ef2-_f2)/_fo2; _t2 = _t2*_t2*(3-2*_t2)\n"
            "                            _v2 = _off2 + (_v2-_off2)*_t2\n"
            "                        _fc2.keyframe_points.insert(frame=_f2, value=_v2, options={'FAST'})\n"
            "                    for kp in _fc2.keyframe_points:\n"
            "                        if _sf2 <= int(kp.co.x) <= _ef2:\n"
            "                            kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'\n"
            "                    _fc2.update()\n\n"
            "    # ── Ejecutar importacion de objetos (armas, escudos, etc.) ────────\n"
            "    try:\n"
            "        _run_object_imports(slot_file=__file__)\n"
            "    except Exception as _e_oimp:\n"
            "        print(f'  ⚠️  Error en _run_object_imports: {_e_oimp}')\n\n"
            "    return True\n\n\n"
            "if __name__ == '__main__':\n"
            "    execute_animation(None, start_frame=START_FRAME, end_frame=END_FRAME)\n"
        )

        from .woodcut_animation import build_export_appendix
        _woodcut_appendix = build_export_appendix(scene, start_f, end_f)
        if _woodcut_appendix:
            _main_marker = "if __name__ == '__main__':"
            _main_pos = code.rfind(_main_marker)
            code = code[:_main_pos] + _woodcut_appendix + "\n" + code[_main_pos:]
        out_dir  = _output_dir_p2 if _output_dir_p2 else bpy.path.abspath(st.anim_dir)
        os.makedirs(out_dir, exist_ok=True)
        filepath = os.path.join(out_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)

        # ── Copiar object_import_utils.py junto al slot exportado ──────────
        # Necesario para que _run_object_imports() pueda importarlo en runtime.
        try:
            import shutil as _shutil_oiu
            _addon_dir = os.path.dirname(os.path.abspath(__file__))
            _oiu_src = os.path.join(_addon_dir, "object_import_utils.py")
            _oiu_dst = os.path.join(out_dir, "object_import_utils.py")
            if os.path.isfile(_oiu_src) and os.path.abspath(_oiu_src) != os.path.abspath(_oiu_dst):
                _shutil_oiu.copy(_oiu_src, _oiu_dst)
        except Exception as _e_copy_oiu:
            print(f"  ⚠️  No se pudo copiar object_import_utils.py: {_e_copy_oiu}")

        st.last_export_path = filepath
        self.report({"INFO"}, f"Exportado ({_scope_label}): {filepath}")
        return {"FINISHED"}

# =============================================================================
# IMPORTAR .py
# =============================================================================

class CERDO_1_ST_OT_ImportAnimation(Operator):
    bl_idname    = "cerdo_1_st.import_animation"
    bl_label     = "Importar animacion .py"
    bl_description = "Carga un .py exportado y lo aplica en la timeline"
    bl_options   = {"REGISTER", "UNDO"}

    filepath:    StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.py", options={"HIDDEN"})

    def invoke(self, context, event):
        start = bpy.path.abspath(context.scene.cerdo_1_st.anim_dir)
        if os.path.isdir(start):
            self.filepath = start + os.sep
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        st    = context.scene.cerdo_1_st
        scene = context.scene
        path  = bpy.path.abspath(self.filepath)

        if not os.path.isfile(path):
            self.report({"ERROR"}, f"Archivo no encontrado: {path}")
            return {"CANCELLED"}
        if not st.armature_name:
            self.report({"ERROR"}, "Selecciona el armature primero")
            return {"CANCELLED"}
        armature = scene.objects.get(st.armature_name)
        if not armature or armature.type != "ARMATURE":
            self.report({"ERROR"}, "Armature no valido")
            return {"CANCELLED"}

        ns = {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                exec(compile(f.read(), path, "exec"), ns)
        except Exception as e:
            self.report({"ERROR"}, f"Error al leer .py: {e}")
            return {"CANCELLED"}

        kf_data     = ns.get("KEYFRAME_DATA", {})
        total_f     = ns.get("TOTAL_FRAMES", 0)
        bones_lista = ns.get("BONES_LISTA", BONES_LISTA)

        if not kf_data or total_f == 0:
            self.report({"ERROR"}, "El .py no contiene KEYFRAME_DATA validos")
            return {"CANCELLED"}

        context.view_layer.objects.active = armature
        if armature.mode != "POSE":
            bpy.ops.object.mode_set(mode="POSE")
        for pb in armature.pose.bones:
            pb.rotation_mode = "XYZ"

        if armature.animation_data and armature.animation_data.action:
            old = armature.animation_data.action
            armature.animation_data.action = None
            bpy.data.actions.remove(old)

        sf = st.start_frame
        for bn in bones_lista:
            pb = armature.pose.bones.get(bn)
            if not pb:
                continue
            pb.rotation_mode = "XYZ"
            for lf, rot in kf_data.get(bn, {}).items():
                abs_f = sf + (int(lf) - 1)
                pb.rotation_euler = Euler(rot, "XYZ")
                pb.keyframe_insert(data_path="rotation_euler", frame=abs_f)

        scene.frame_start = sf
        scene.frame_end   = sf + total_f - 1
        scene.frame_set(sf)

        # ── Post-proceso: EYE_SEQUENCE_DATA del .py importado (panel 2b) ──
        eye_seq = ns.get("EYE_SEQUENCE_DATA", None)
        if eye_seq and eye_seq.get("global", {}).get("enabled", False):
            # Usar la secuencia completa de ojos embebida en el archivo exportado
            _apply_eye_sequence_from_data(scene, eye_seq, sf, sf + total_f - 1)
            self.report({"INFO"}, "EYE_SEQUENCE_DATA aplicado desde el .py")
        else:
            # Fallback: usar config del panel si los ojos estan activos
            eye_s = st.eye_expr
            if eye_s.enabled and eye_s.blink_enabled:
                # Usar blink_intervals (sistema nuevo) si hay intervalos cargados
                if st.blink_intervals:
                    bi = st.blink_intervals[
                        min(st.blink_interval_idx, len(st.blink_intervals) - 1)
                    ]
                    if bi.enabled:
                        apply_blink_sequence(
                            bi.frame_start, bi.frame_end,
                            bi.blink_count, bi.blink_duration,
                        )
                else:
                    # Fallback legacy
                    apply_blink_sequence(sf, sf + total_f - 1,
                                          eye_s.blink_count, eye_s.blink_duration)

        st.anim_generated   = True
        st.total_frames_gen = total_f
        st.end_frame_gen    = sf + total_f - 1
        eye_msg = "  [ojos: EYE_SEQUENCE_DATA]" if eye_seq else ""

        # ── Post-proceso: BONE_OSCILLATIONS_CONFIG del .py importado ─────────
        bone_osc_cfg = ns.get("BONE_OSCILLATIONS_CONFIG", None)
        bone_osc_msg = ""
        if bone_osc_cfg and isinstance(bone_osc_cfg, dict):
            osc = st.bone_oscillations
            osc.enabled = bool(bone_osc_cfg.get("enabled", False))
            osc.items.clear()
            for item_data in bone_osc_cfg.get("items", []):
                item = osc.items.add()
                item.label        = item_data.get("label", "")
                item.bone_name    = item_data.get("bone_name", "")
                item.frame_start  = int(item_data.get("frame_start", 1))
                item.frame_end    = int(item_data.get("frame_end", 60))
                _legacy_axis = item_data.get("axis", "")
                item.axis_x       = bool(item_data.get("axis_x", _legacy_axis == "X"))
                item.axis_y       = bool(item_data.get("axis_y", _legacy_axis == "Y"))
                item.axis_z       = bool(item_data.get("axis_z", _legacy_axis == "Z" or not _legacy_axis))
                if "amplitude" in item_data:
                    item.amplitude = float(item_data["amplitude"])
                elif "angle_min" in item_data and "angle_max" in item_data:
                    item.amplitude = (float(item_data["angle_max"]) - float(item_data["angle_min"])) / 2.0
                else:
                    item.amplitude = 30.0
                item.angle_offset = float(item_data.get("angle_offset", 0.0))
                if "num_cycles" in item_data:
                    item.num_cycles = int(item_data["num_cycles"])
                elif "speed" in item_data:
                    dur = max(1, item.frame_end - item.frame_start)
                    item.num_cycles = max(1, round(float(item_data["speed"]) * dur))
                else:
                    item.num_cycles = 4
                item.phase        = float(item_data.get("phase", 0.0))
                item.wave_type    = item_data.get("wave_type", "SINE")
                item.fade_in      = int(item_data.get("fade_in", 6))
                item.fade_out     = int(item_data.get("fade_out", 6))
                item.noise_seed   = int(item_data.get("noise_seed", 42))
                item.enabled      = bool(item_data.get("enabled", True))
            n_osc = len(osc.items)
            bone_osc_msg = f"  [bone_osc: {n_osc}]"
            self.report({"INFO"}, f"BONE_OSCILLATIONS_CONFIG restaurado ({n_osc} oscilaciones)")

        st.status_msg = f"OK  Importado: {os.path.basename(path)} ({total_f} frames){eye_msg}{bone_osc_msg}"
        self.report({"INFO"}, st.status_msg)

        # ── Post-proceso: OBJECT_IMPORTS_CONFIG del .py importado ────────────
        obj_imp_cfg = ns.get("OBJECT_IMPORTS_CONFIG", None)
        if obj_imp_cfg and isinstance(obj_imp_cfg, dict):
            oi = st.object_imports
            oi.enabled = bool(obj_imp_cfg.get("enabled", False))
            oi.items.clear()
            for item_data in obj_imp_cfg.get("items", []):
                item = oi.items.add()
                item.label           = item_data.get("label", "Objeto")
                item.object_folder   = item_data.get("object_folder", "")
                item.blend_filename  = item_data.get("blend_filename", "")
                item.object_name     = item_data.get("object_name", "")
                item.frame_start     = int(item_data.get("frame_start", 1))
                item.frame_end       = int(item_data.get("frame_end", 60))
                item.parent_armature = item_data.get("parent_armature", "")
                item.parent_bone     = item_data.get("parent_bone", "")
                item.loc_x           = float(item_data.get("loc_x", 0.0))
                item.loc_y           = float(item_data.get("loc_y", 0.0))
                item.loc_z           = float(item_data.get("loc_z", 0.0))
                item.rot_x           = float(item_data.get("rot_x", 0.0))
                item.rot_y           = float(item_data.get("rot_y", 0.0))
                item.rot_z           = float(item_data.get("rot_z", 0.0))
                item.scale_uniform   = float(item_data.get("scale_uniform", 1.0))
                item.levels_up       = int(item_data.get("levels_up", 4))
                item.enabled         = bool(item_data.get("enabled", True))
            n_obj = len(oi.items)
            self.report({"INFO"}, f"OBJECT_IMPORTS_CONFIG restaurado ({n_obj} objetos)")

        # ── Post-proceso: SEGMENTS_THROW_CONFIG del .py importado ────────────
        throw_cfg = ns.get("SEGMENTS_THROW_CONFIG", None)
        if throw_cfg and isinstance(throw_cfg, list) and throw_cfg:
            try:
                cerdo_1_segs = context.scene.cerdo_1_segs
                segs = cerdo_1_segs.segments
                # Limpiar throws de todos los segmentos existentes
                for seg in segs:
                    seg.throws.items.clear()
                # Restaurar throws agrupados por seg_idx
                n_throws = 0
                for entry in throw_cfg:
                    seg_idx = int(entry.get("seg_idx", -1))
                    # Si el segmento no existe, crearlo con los frames del entry
                    while seg_idx >= len(segs):
                        new_seg = segs.add()
                        new_seg.label       = entry.get("seg_label", f"Segmento {len(segs)}")
                        new_seg.frame_start = int(entry.get("seg_frame_start", 1))
                        new_seg.frame_end   = int(entry.get("seg_frame_end", 48))
                    if seg_idx < 0:
                        continue
                    th   = segs[seg_idx].throws
                    th.enabled = True
                    item = th.items.add()
                    item.enabled            = bool(entry.get("enabled", True))
                    item.label              = str(entry.get("label", "Lanzamiento"))
                    item.mode               = str(entry.get("mode", "THROW"))
                    item.object_folder      = str(entry.get("object_folder", ""))
                    item.blend_filename     = str(entry.get("blend_filename", ""))
                    item.object_name        = str(entry.get("object_name", ""))
                    item.levels_up          = int(entry.get("levels_up", 4))
                    item.frame_start        = int(entry.get("frame_start", 1))
                    item.frame_end          = int(entry.get("frame_end", 30))
                    item.parent_armature    = str(entry.get("parent_armature", "pig.arma_cerdo_1"))
                    item.parent_bone        = str(entry.get("parent_bone", ""))
                    item.loc_x              = float(entry.get("loc_x", 0.0))
                    item.loc_y              = float(entry.get("loc_y", 0.0))
                    item.loc_z              = float(entry.get("loc_z", 0.0))
                    item.rot_x              = float(entry.get("rot_x", 0.0))
                    item.rot_y              = float(entry.get("rot_y", 0.0))
                    item.rot_z              = float(entry.get("rot_z", 0.0))
                    item.scale_uniform      = float(entry.get("scale_uniform", 1.0))
                    item.target_object      = str(entry.get("target_object", ""))
                    item.target_armature    = str(entry.get("target_armature", "pig.arma_cerdo_1"))
                    item.target_bone        = str(entry.get("target_bone", ""))
                    item.dest_x             = float(entry.get("dest_x", 0.0))
                    item.dest_y             = float(entry.get("dest_y", 3.0))
                    item.dest_z             = float(entry.get("dest_z", 0.0))
                    item.easing_global      = str(entry.get("easing_global", "SMOOTH"))
                    item.spin_during_flight = bool(entry.get("spin_during_flight", False))
                    item.spin_turns         = float(entry.get("spin_turns", 1.0))
                    item.imported_object_name = ""
                    item.waypoints.clear()
                    for wp_d in entry.get("waypoints", []):
                        wp         = item.waypoints.add()
                        wp.label   = str(wp_d.get("label", "Punto"))
                        wp.x       = float(wp_d.get("x", 0.0))
                        wp.y       = float(wp_d.get("y", 0.0))
                        wp.z       = float(wp_d.get("z", 2.0))
                        wp.easing  = str(wp_d.get("easing", "SMOOTH"))
                        wp.enabled = bool(wp_d.get("enabled", True))
                    n_throws += 1
                self.report({"INFO"}, f"SEGMENTS_THROW_CONFIG restaurado ({n_throws} throw(s))")
            except Exception as _e_throw_imp:
                print(f"[Cerdo_1] Error restaurando SEGMENTS_THROW_CONFIG: {_e_throw_imp}")
                import traceback; traceback.print_exc()

        return {"FINISHED"}

# =============================================================================
# EXTRAER POSE
# =============================================================================

class CERDO_1_ST_OT_ExtractPose(Operator):
    bl_idname    = "cerdo_1_st.extract_pose"
    bl_label     = "Guardar como nueva pose"
    bl_description = "Extrae la pose del frame indicado y la guarda en la libreria"
    bl_options   = {"REGISTER"}

    def execute(self, context):
        st    = context.scene.cerdo_1_st
        scene = context.scene

        label = st.extract_label.strip()
        if not label:
            self.report({"ERROR"}, "Escribe un nombre para la nueva pose")
            return {"CANCELLED"}
        if not st.armature_name:
            self.report({"ERROR"}, "Selecciona el armature")
            return {"CANCELLED"}
        armature = scene.objects.get(st.armature_name)
        if not armature or armature.type != "ARMATURE":
            self.report({"ERROR"}, "Armature no valido")
            return {"CANCELLED"}

        frame = scene.frame_current if st.extract_use_current else st.extract_frame
        if not st.extract_use_current:
            scene.frame_set(frame)
        context.view_layer.update()

        bones_data = {}
        for pb in armature.pose.bones:
            rot_e = pb.rotation_euler
            rot_q = pb.rotation_quaternion

            # Datos en local_space (identicos a raw_*, guardados tambien por compatibilidad)
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

            bones_data[pb.name] = {
                "parent":    pb.parent.name if pb.parent else None,
                "connected": pb.bone.use_connect,
                "local_space": local_space,
                "rotation_mode": pb.rotation_mode,
                # Campos raiz para retrocompatibilidad con Formato A (exportador antiguo)
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
            "timestamp":       datetime.now().isoformat(),
            "blender_version": bpy.app.version_string,
            "file":            os.path.basename(bpy.data.filepath) if bpy.data.filepath else "unsaved",
            "bone_count":      len(bones_data),
            "bones":           bones_data,
        }

        out_dir  = bpy.path.abspath(st.poses_dir)
        os.makedirs(out_dir, exist_ok=True)
        # Conservar caracteres unicode validos (letras, numeros, guiones, espacios).
        # Solo eliminar caracteres que el sistema de archivos rechaza: / \ : * ? " < > |
        _FORBIDDEN = set('/\\:*?"<>|')
        safe_label = "".join(
            c if c not in _FORBIDDEN else "_" for c in label
        ).strip().replace(" ", "_")
        if not safe_label:
            safe_label = "pose_sin_nombre"
        filename = f"{safe_label}.json"
        filepath = os.path.join(out_dir, filename)

        data = {"poses": []}
        if os.path.isfile(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

        data["poses"].append(record)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        total_saved = len(data["poses"])
        st.extract_label = ""
        self.report({"INFO"},
            f"Pose '{label}' (frame {frame}) guardada -> {filename}  ({total_saved} poses totales)")
        return {"FINISHED"}

# =============================================================================
# GUARDAR / CARGAR CONFIGURACION DE TRABAJO (.json)
# =============================================================================

# =============================================================================
# HELPER: serializar oscilaciones de bones para el .py exportado
# =============================================================================

def _build_bone_oscillations_code(st):
    """
    Genera el bloque BONE_OSCILLATIONS_CONFIG para el .py exportado de Cerdo_1.
    Incluye todas las oscilaciones definidas (enabled y disabled) para que el
    importador pueda restaurar el estado completo del panel.
    """
    osc = st.bone_oscillations
    items_list = []
    for item in osc.items:
        items_list.append({
            "label":        item.label,
            "bone_name":    item.bone_name,
            "frame_start":  item.frame_start,
            "frame_end":    item.frame_end,
            "axis_x":       item.axis_x,
            "axis_y":       item.axis_y,
            "axis_z":       item.axis_z,
            "amplitude":    round(item.amplitude, 2),
            "angle_offset": round(item.angle_offset, 2),
            "num_cycles":   item.num_cycles,
            "phase":        round(item.phase, 4),
            "wave_type":    item.wave_type,
            "fade_in":      item.fade_in,
            "fade_out":     item.fade_out,
            "noise_seed":   item.noise_seed,
            "enabled":      item.enabled,
        })
    cfg = {
        "enabled": osc.enabled,
        "items":   items_list,
    }
    import json as _json
    serialized = _json.dumps(cfg, ensure_ascii=False)
    return (
        "# ── Oscilaciones de bones (Cerdo_1) ──────────────────────────────\n"
        "import json as _json_bosc_alf\n"
        f"BONE_OSCILLATIONS_CONFIG = _json_bosc_alf.loads({repr(serialized)})\n"
    )


# =============================================================================
# FUNCION CENTRAL: APLICAR OSCILACIONES DE BONES (Cerdo_1)
# =============================================================================

def _apply_bone_oscillations(context, armature, osc_settings):
    """
    Aplica todas las oscilaciones de bones definidas en osc_settings sobre
    las fcurves del armature de Cerdo_1. Se llama desde CONCATENAR como post-proceso.
    Funciona tanto si la animacion esta en una action activa como en NLA tracks.
    """
    import math as _m

    if not osc_settings.enabled:
        return
    if not osc_settings.items:
        return
    if not armature.animation_data:
        return

    # ── Resolver la action sobre la que escribir ──────────────────────────
    # Si hay una action activa la usamos directamente (modo 1 coordenada o
    # baked). Si no hay action activa pero si NLA tracks, buscamos la action
    # del strip relevante para cada bone (modo recorrido multi-coordenada).
    action = armature.animation_data.action

    # Helper: obtener o crear fcurve en la action correcta para un bone/eje
    def _get_or_create_fc(bone_name, data_path, axis_idx):
        """Devuelve (fcurve, action_owner) buscando primero en action activa,
        luego en NLA strips que contengan el data_path."""
        if action:
            fc = get_fcurves(action).find(data_path, index=axis_idx)
            if fc is None:
                fc = get_fcurves(action).new(data_path, index=axis_idx,
                                        action_group=bone_name)
            return fc, action
        # Sin action activa: buscar en NLA strips
        if armature.animation_data:
            for _tr in armature.animation_data.nla_tracks:
                for _st in _tr.strips:
                    if _st.action is None:
                        continue
                    fc = get_fcurves(_st.action).find(data_path, index=axis_idx)
                    if fc is not None:
                        return fc, _st.action
            # No existe en ningun strip: crear en el primer strip con accion
            for _tr in armature.animation_data.nla_tracks:
                for _st in _tr.strips:
                    if _st.action is not None:
                        fc = get_fcurves(_st.action).new(data_path, index=axis_idx,
                                                     action_group=bone_name)
                        return fc, _st.action
        return None, None

    def _noise_osc(frame, speed, seed, dim=0):
        import mathutils
        scale = speed * 20.0
        p = mathutils.noise.noise_vector(
            mathutils.Vector((frame * scale + seed * 13.7,
                               dim * 137.3 + seed * 0.17,
                               0.0))
        )
        return p[0]

    def _wave_value(wave_type, frame, speed, phase, seed):
        t = frame * speed * 2 * _m.pi + phase

        # ── Clásicas ──────────────────────────────────────────────────────────
        if wave_type == "SINE":
            return _m.sin(t)

        elif wave_type == "TRIANGLE":
            frac = (t / (2 * _m.pi)) % 1.0
            return 1.0 - abs(4.0 * frac - 2.0) + 1.0 - 2.0

        elif wave_type == "SQUARE":
            return 1.0 if _m.sin(t) >= 0 else -1.0

        elif wave_type == "NOISE":
            return _noise_osc(frame, speed, seed)

        # ── Orgánicas suaves ──────────────────────────────────────────────────

        elif wave_type == "SINE_EASE":
            # Seno remapeado con smoothstep para que cada arranque/frenada
            # sea más suave que un seno puro (útil en cabeza y torso)
            s = (_m.sin(t) + 1.0) * 0.5          # 0..1
            s = s * s * (3.0 - 2.0 * s)           # smoothstep
            return s * 2.0 - 1.0                   # -1..1

        elif wave_type == "ELASTIC":
            # Ciclo normalizado 0..1, con rebote elástico hacia el final
            frac = (t / (2 * _m.pi)) % 1.0
            if frac < 0.6:
                # subida suave
                v = _m.sin(frac / 0.6 * _m.pi * 0.5)
            else:
                # rebote amortiguado: 3 mini-oscilaciones decrecientes
                r = (frac - 0.6) / 0.4             # 0..1 en la zona de rebote
                decay = _m.exp(-r * 4.0)
                v = -decay * _m.cos(r * _m.pi * 5.0) * 0.35
            return v

        elif wave_type == "BOUNCE":
            # Caída gravitatoria que rebota: simula impacto en el suelo
            frac = (t / (2 * _m.pi)) % 1.0
            # parábola invertida que rebota 3 veces con amplitud decreciente
            peaks = [(0.0, 1.0), (0.55, 0.45), (0.78, 0.18), (0.92, 0.06), (1.0, 0.0)]
            for i in range(len(peaks) - 1):
                x0, h0 = peaks[i]
                x1, h1 = peaks[i + 1]
                if x0 <= frac < x1:
                    local = (frac - x0) / (x1 - x0)  # 0..1 en el sub-arco
                    h_max = (h0 + h1) * 0.5
                    v = h_max * (1.0 - (2.0 * local - 1.0) ** 2)
                    return v * 2.0 - 0.5
            return -0.5

        elif wave_type == "BREATHE":
            # Inhalación lenta (60%) / exhalación rápida (40%), asimétrico
            frac = (t / (2 * _m.pi)) % 1.0
            if frac < 0.6:
                v = _m.sin(frac / 0.6 * _m.pi)         # 0→1→0 lento (inhala)
            else:
                v = -_m.sin((frac - 0.6) / 0.4 * _m.pi) * 0.4  # pequeño hundimiento (exhala)
            return v

        elif wave_type == "HEARTBEAT":
            # Dos pulsos rápidos (sístole/diástole) seguidos de reposo
            frac = (t / (2 * _m.pi)) % 1.0
            def _pulse(x, center, width):
                if abs(x - center) < width:
                    return _m.sin((x - center) / width * _m.pi)
                return 0.0
            v  = _pulse(frac, 0.10, 0.08)   # primer golpe fuerte
            v += _pulse(frac, 0.25, 0.05) * 0.6  # segundo golpe débil
            return v

        # ── Ruido controlado ──────────────────────────────────────────────────

        elif wave_type == "NOISE_DRIFT":
            # Noise orgánico de alta frecuencia + deriva sinusoidal lenta
            high  = _noise_osc(frame, speed,        seed)          # detalle fino
            drift = _m.sin(frame * speed * 0.3 * _m.pi + phase)   # deriva lenta
            return high * 0.6 + drift * 0.4

        elif wave_type == "NOISE_LAYERED":
            # Tres capas de noise a distintas frecuencias (1x, 2.7x, 7x)
            n1 = _noise_osc(frame, speed,        seed)
            n2 = _noise_osc(frame, speed * 2.7,  seed + 31)
            n3 = _noise_osc(frame, speed * 7.0,  seed + 97)
            return n1 * 0.55 + n2 * 0.30 + n3 * 0.15

        # ── Asimétricas / gestuales ───────────────────────────────────────────

        elif wave_type == "SAW_SMOOTH":
            # Subida lenta suavizada (80%) + caída brusca (20%)
            frac = (t / (2 * _m.pi)) % 1.0
            if frac < 0.8:
                v = frac / 0.8                          # rampa lineal lenta
                v = v * v * (3.0 - 2.0 * v) * 2.0 - 1.0  # smoothstep → -1..1
            else:
                v = 1.0 - (frac - 0.8) / 0.2 * 2.0     # caída brusca
            return v

        elif wave_type == "SAW_REVERSE":
            # Subida rápida (20%) + caída lenta suavizada (80%)
            frac = (t / (2 * _m.pi)) % 1.0
            if frac < 0.2:
                v = frac / 0.2                           # subida brusca 0..1
            else:
                v = 1.0 - (frac - 0.2) / 0.8            # caída lenta 1..0
                v = v * v * (3.0 - 2.0 * v)             # smoothstep
            return v * 2.0 - 1.0

        elif wave_type == "PENDULUM":
            # Arcoseno invertido: se mueve rápido en el centro y
            # decelera en los extremos como un péndulo físico real
            s = _m.sin(t)
            # Mapear seno a "posición de péndulo" (no lineal en el centro)
            if abs(s) < 0.9999:
                return _m.asin(s) / (_m.pi * 0.5)   # comprime el centro
            return _m.copysign(1.0, s)

        elif wave_type == "QUIVER":
            # Temblor: seno de alta frecuencia modulado por envelope lento
            envelope = (_m.sin(t * 0.25) + 1.0) * 0.5  # pulsa lento 0..1
            quiver   = _m.sin(t * 7.0 + _m.sin(t * 2.3) * 1.5)  # freq. alta irregular
            return quiver * (0.4 + envelope * 0.6)

        # fallback
        return _m.sin(t)

    for item in osc_settings.items:
        if not item.enabled:
            continue
        bone_name = item.bone_name.strip()
        if not bone_name:
            continue

        active_axes = [(ax, idx) for ax, idx, flag in
                       [("X", 0, item.axis_x), ("Y", 1, item.axis_y), ("Z", 2, item.axis_z)]
                       if flag]
        if not active_axes:
            continue

        dp   = f'pose.bones["{bone_name}"].rotation_euler'
        sf   = item.frame_start
        ef   = item.frame_end
        if sf >= ef:
            continue

        dur       = ef - sf
        speed     = item.num_cycles / max(1, dur)
        amplitude  = _m.radians(item.amplitude)
        ang_offset = _m.radians(item.angle_offset)
        phase      = item.phase
        wave_type  = item.wave_type
        seed       = item.noise_seed
        fade_in_f  = max(0, item.fade_in)
        fade_out_f = max(0, item.fade_out)

        for _ax_name, ax_idx in active_axes:
            fc, _fc_owner = _get_or_create_fc(bone_name, dp, ax_idx)
            if fc is None:
                continue

            # Leer el valor base que la pose dejo en el bone al inicio del rango.
            # La oscilacion se centra sobre ese valor, no sobre 0+offset.
            try:
                pose_base_value = fc.evaluate(sf)
            except Exception:
                pose_base_value = 0.0

            idxs = [i for i, kp in enumerate(fc.keyframe_points)
                    if sf <= int(kp.co.x) <= ef]
            for i in reversed(idxs):
                fc.keyframe_points.remove(fc.keyframe_points[i])

            for f in range(sf, ef + 1):
                raw = _wave_value(wave_type, f, speed, phase, seed)
                # Centro = valor base de la pose + offset manual
                osc_center = pose_base_value + ang_offset
                val = osc_center + amplitude * raw

                if fade_in_f > 0 and (f - sf) < fade_in_f:
                    t_fade = (f - sf) / fade_in_f
                    t_fade = t_fade * t_fade * (3.0 - 2.0 * t_fade)
                    val = osc_center + (val - osc_center) * t_fade

                if fade_out_f > 0 and (ef - f) < fade_out_f:
                    t_fade = (ef - f) / fade_out_f
                    t_fade = t_fade * t_fade * (3.0 - 2.0 * t_fade)
                    val = osc_center + (val - osc_center) * t_fade

                fc.keyframe_points.insert(frame=f, value=val, options={"FAST"})

            for kp in fc.keyframe_points:
                if sf <= int(kp.co.x) <= ef:
                    kp.interpolation = "BEZIER"
                    kp.easing = "AUTO"
            fc.update()


# =============================================================================
# OPERADORES: BONE OSCILLATIONS (Cerdo_1)
# =============================================================================

class CERDO_1_ST_OT_BoneOscAddItem(Operator):
    """Agrega una nueva oscilacion de bone a la lista."""
    bl_idname    = "cerdo_1_st.bone_osc_add_item"
    bl_label     = "Agregar oscilacion de bone"
    bl_description = "Agrega la oscilacion definida abajo a la lista"
    bl_options   = {"REGISTER", "UNDO"}

    quick_bone: bpy.props.StringProperty(default="")

    def execute(self, context):
        osc = context.scene.cerdo_1_st.bone_oscillations
        item = osc.items.add()
        item.label        = osc.edit_label
        item.bone_name    = self.quick_bone if self.quick_bone else osc.edit_bone_name
        item.frame_start  = osc.edit_frame_start
        item.frame_end    = osc.edit_frame_end
        item.axis_x       = osc.edit_axis_x
        item.axis_y       = osc.edit_axis_y
        item.axis_z       = osc.edit_axis_z
        item.amplitude    = osc.edit_amplitude
        item.angle_offset = osc.edit_angle_offset
        item.num_cycles   = osc.edit_num_cycles
        item.phase        = osc.edit_phase
        item.wave_type    = osc.edit_wave_type
        item.fade_in      = osc.edit_fade_in
        item.fade_out     = osc.edit_fade_out
        item.noise_seed   = osc.edit_noise_seed
        item.enabled      = True
        osc.active_idx    = len(osc.items) - 1
        if self.quick_bone:
            item.label = self.quick_bone
        self.report({"INFO"}, f"Oscilacion '{item.label}' agregada")
        return {"FINISHED"}


class CERDO_1_ST_OT_BoneOscRemoveItem(Operator):
    """Elimina la oscilacion de bone en el indice dado."""
    bl_idname  = "cerdo_1_st.bone_osc_remove_item"
    bl_label   = "Eliminar oscilacion"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        osc = context.scene.cerdo_1_st.bone_oscillations
        if 0 <= self.item_idx < len(osc.items):
            osc.items.remove(self.item_idx)
            osc.active_idx = max(0, min(osc.active_idx, len(osc.items) - 1))
        return {"FINISHED"}


class CERDO_1_ST_OT_BoneOscMoveItem(Operator):
    """Mueve la oscilacion seleccionada arriba o abajo."""
    bl_idname  = "cerdo_1_st.bone_osc_move_item"
    bl_label   = "Mover oscilacion"
    bl_options = {"REGISTER", "UNDO"}

    direction: bpy.props.EnumProperty(items=[("UP","Arriba",""),("DOWN","Abajo","")])

    def execute(self, context):
        osc = context.scene.cerdo_1_st.bone_oscillations
        idx = osc.active_idx
        n   = len(osc.items)
        if self.direction == "UP" and idx > 0:
            osc.items.move(idx, idx - 1)
            osc.active_idx -= 1
        elif self.direction == "DOWN" and idx < n - 1:
            osc.items.move(idx, idx + 1)
            osc.active_idx += 1
        return {"FINISHED"}


class CERDO_1_ST_OT_BoneOscDuplicateItem(Operator):
    """Duplica la oscilacion de bone en el indice dado."""
    bl_idname  = "cerdo_1_st.bone_osc_duplicate_item"
    bl_label   = "Duplicar oscilacion"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        osc = context.scene.cerdo_1_st.bone_oscillations
        if 0 <= self.item_idx < len(osc.items):
            src = osc.items[self.item_idx]
            new = osc.items.add()
            for attr in ("label", "bone_name", "frame_start", "frame_end",
                         "axis_x", "axis_y", "axis_z", "amplitude", "angle_offset",
                         "num_cycles", "phase", "wave_type", "fade_in", "fade_out",
                         "noise_seed", "enabled"):
                setattr(new, attr, getattr(src, attr))
            new.label = src.label + "_copia"
            osc.active_idx = len(osc.items) - 1
        return {"FINISHED"}


class CERDO_1_ST_OT_BoneOscToggleItem(Operator):
    """Selecciona como activo y/o activa/desactiva la oscilacion."""
    bl_idname  = "cerdo_1_st.bone_osc_toggle_item"
    bl_label   = "Seleccionar / toggle oscilacion"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        osc = context.scene.cerdo_1_st.bone_oscillations
        if 0 <= self.item_idx < len(osc.items):
            if osc.active_idx == self.item_idx:
                osc.items[self.item_idx].enabled = not osc.items[self.item_idx].enabled
            else:
                osc.active_idx = self.item_idx
        return {"FINISHED"}


class CERDO_1_ST_OT_BoneOscPickBone(Operator):
    """
    Copia el nombre del bone detectado desde el JSON de historia
    al campo 'Bone' del editor de nueva oscilacion.
    """
    bl_idname    = "cerdo_1_st.bone_osc_pick_bone"
    bl_label     = "Seleccionar bone"
    bl_description = "Usar este bone en el editor de nueva oscilacion"
    bl_options   = {"REGISTER", "UNDO"}

    bone_name: bpy.props.StringProperty(default="")

    def execute(self, context):
        osc = context.scene.cerdo_1_st.bone_oscillations
        osc.edit_bone_name = self.bone_name
        if not osc.edit_label or osc.edit_label == "Mi oscilacion":
            osc.edit_label = self.bone_name
        return {"FINISHED"}


# =============================================================================
# OPERADORES: IMPORTACION DE OBJETOS (armas, escudos, props)
# =============================================================================

def _resolve_preview_object_for_item(oi, item):
    """
    Si el usuario uso "Importar .blend al Outliner" antes de Agregar/Actualizar,
    oi.edit_imported_object_name guarda el nombre del objeto ya importado.

    Reutiliza ese objeto solo si:
      - todavia existe en bpy.data.objects, y
      - su nombre base (sin sufijo .001, .002, etc.) coincide con item.object_name

    En caso contrario retorna "" (el sistema importara uno nuevo cuando
    corresponda, ej. al apretar CONCATENAR).
    """
    name = (oi.edit_imported_object_name or "").strip()
    if not name:
        return ""

    obj = bpy.data.objects.get(name)
    if obj is None:
        return ""

    base_name = name.split('.')[0]
    if base_name != item.object_name:
        return ""

    return name


class CERDO_1_ST_OT_ObjImportAddItem(Operator):
    """Agrega un nuevo objeto de importacion a la lista."""
    bl_idname    = "cerdo_1_st.obj_import_add_item"
    bl_label     = "Agregar objeto"
    bl_description = "Agrega el objeto definido abajo a la lista de importaciones"
    bl_options   = {"REGISTER", "UNDO"}

    def execute(self, context):
        oi = context.scene.cerdo_1_st.object_imports
        item = oi.items.add()
        item.label          = oi.edit_label
        item.object_folder  = oi.edit_object_folder
        item.blend_filename = oi.edit_blend_filename
        item.object_name    = oi.edit_object_name
        item.frame_start    = oi.edit_frame_start
        item.frame_end      = oi.edit_frame_end
        item.parent_armature = oi.edit_parent_armature
        item.parent_bone    = oi.edit_parent_bone
        item.loc_x          = oi.edit_loc_x
        item.loc_y          = oi.edit_loc_y
        item.loc_z          = oi.edit_loc_z
        item.rot_x          = oi.edit_rot_x
        item.rot_y          = oi.edit_rot_y
        item.rot_z          = oi.edit_rot_z
        item.scale_uniform  = oi.edit_scale_uniform
        item.levels_up             = oi.edit_levels_up
        item.segment_idx           = oi.edit_segment_idx
        item.transition_in         = oi.edit_transition_in
        item.transition_in_duration  = oi.edit_transition_in_duration
        item.transition_out        = oi.edit_transition_out
        item.transition_out_duration = oi.edit_transition_out_duration
        item.enabled        = True

        # Reutilizar el objeto importado con "Importar .blend al Outliner" si coincide
        item.imported_object_name = _resolve_preview_object_for_item(oi, item)

        oi.active_idx = len(oi.items) - 1
        self.report({"INFO"}, f"Objeto '{item.label}' agregado")
        return {"FINISHED"}


class CERDO_1_ST_OT_ObjImportRemoveItem(Operator):
    """Elimina el objeto de importacion en el indice dado."""
    bl_idname  = "cerdo_1_st.obj_import_remove_item"
    bl_label   = "Eliminar objeto"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        oi = context.scene.cerdo_1_st.object_imports
        if 0 <= self.item_idx < len(oi.items):
            oi.items.remove(self.item_idx)
            oi.active_idx = max(0, min(oi.active_idx, len(oi.items) - 1))
        return {"FINISHED"}


class CERDO_1_ST_OT_ObjImportMoveItem(Operator):
    """Mueve el objeto seleccionado arriba o abajo."""
    bl_idname  = "cerdo_1_st.obj_import_move_item"
    bl_label   = "Mover objeto"
    bl_options = {"REGISTER", "UNDO"}

    direction: bpy.props.EnumProperty(items=[("UP", "Arriba", ""), ("DOWN", "Abajo", "")])

    def execute(self, context):
        oi  = context.scene.cerdo_1_st.object_imports
        idx = oi.active_idx
        n   = len(oi.items)
        if self.direction == "UP" and idx > 0:
            oi.items.move(idx, idx - 1)
            oi.active_idx -= 1
        elif self.direction == "DOWN" and idx < n - 1:
            oi.items.move(idx, idx + 1)
            oi.active_idx += 1
        return {"FINISHED"}


class CERDO_1_ST_OT_ObjImportDuplicateItem(Operator):
    """Duplica el objeto de importacion en el indice dado."""
    bl_idname  = "cerdo_1_st.obj_import_duplicate_item"
    bl_label   = "Duplicar objeto"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        oi = context.scene.cerdo_1_st.object_imports
        if 0 <= self.item_idx < len(oi.items):
            src = oi.items[self.item_idx]
            new = oi.items.add()
            for attr in ("label", "object_folder", "blend_filename", "object_name",
                         "frame_start", "frame_end", "parent_armature", "parent_bone",
                         "loc_x", "loc_y", "loc_z", "rot_x", "rot_y", "rot_z",
                         "scale_uniform", "levels_up", "enabled"):
                setattr(new, attr, getattr(src, attr))
            new.label = src.label + "_copia"
            oi.active_idx = len(oi.items) - 1
        return {"FINISHED"}


class CERDO_1_ST_OT_ObjImportToggleItem(Operator):
    """Selecciona como activo y/o activa/desactiva el objeto."""
    bl_idname  = "cerdo_1_st.obj_import_toggle_item"
    bl_label   = "Seleccionar / toggle objeto"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        oi = context.scene.cerdo_1_st.object_imports
        if 0 <= self.item_idx < len(oi.items):
            if oi.active_idx == self.item_idx:
                oi.items[self.item_idx].enabled = not oi.items[self.item_idx].enabled
            else:
                oi.active_idx = self.item_idx
        return {"FINISHED"}


class CERDO_1_ST_OT_ObjImportLoadToEditor(Operator):
    """Carga el objeto seleccionado en el editor para editarlo."""
    bl_idname  = "cerdo_1_st.obj_import_load_to_editor"
    bl_label   = "Editar objeto"
    bl_description = "Carga este objeto en el editor de abajo para modificarlo"
    bl_options = {"REGISTER", "UNDO"}

    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        oi = context.scene.cerdo_1_st.object_imports
        if 0 <= self.item_idx < len(oi.items):
            src = oi.items[self.item_idx]
            oi.active_idx          = self.item_idx
            oi.edit_label          = src.label
            oi.edit_object_folder  = src.object_folder
            oi.edit_blend_filename = src.blend_filename
            oi.edit_object_name    = src.object_name
            oi.edit_frame_start    = src.frame_start
            oi.edit_frame_end      = src.frame_end
            oi.edit_parent_armature = src.parent_armature
            oi.edit_parent_bone    = src.parent_bone
            oi.edit_loc_x          = src.loc_x
            oi.edit_loc_y          = src.loc_y
            oi.edit_loc_z          = src.loc_z
            oi.edit_rot_x          = src.rot_x
            oi.edit_rot_y          = src.rot_y
            oi.edit_rot_z          = src.rot_z
            oi.edit_scale_uniform  = src.scale_uniform
            oi.edit_levels_up      = src.levels_up
            oi.edit_imported_object_name = src.imported_object_name
            oi.edit_segment_idx    = src.segment_idx
            oi.edit_transition_in          = src.transition_in
            oi.edit_transition_in_duration   = src.transition_in_duration
            oi.edit_transition_out         = src.transition_out
            oi.edit_transition_out_duration  = src.transition_out_duration
        return {"FINISHED"}


class CERDO_1_ST_OT_ObjImportUpdateItem(Operator):
    """Actualiza el objeto activo con los valores del editor."""
    bl_idname  = "cerdo_1_st.obj_import_update_item"
    bl_label   = "Actualizar objeto"
    bl_description = "Sobreescribe el objeto seleccionado con los valores actuales del editor"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        oi = context.scene.cerdo_1_st.object_imports
        idx = oi.active_idx
        if 0 <= idx < len(oi.items):
            item = oi.items[idx]
            item.label          = oi.edit_label
            item.object_folder  = oi.edit_object_folder
            item.blend_filename = oi.edit_blend_filename
            item.object_name    = oi.edit_object_name
            item.frame_start    = oi.edit_frame_start
            item.frame_end      = oi.edit_frame_end
            item.parent_armature = oi.edit_parent_armature
            item.parent_bone    = oi.edit_parent_bone
            item.loc_x          = oi.edit_loc_x
            item.loc_y          = oi.edit_loc_y
            item.loc_z          = oi.edit_loc_z
            item.rot_x          = oi.edit_rot_x
            item.rot_y          = oi.edit_rot_y
            item.rot_z          = oi.edit_rot_z
            item.scale_uniform  = oi.edit_scale_uniform
            item.levels_up             = oi.edit_levels_up
            item.segment_idx           = oi.edit_segment_idx
            item.transition_in         = oi.edit_transition_in
            item.transition_in_duration  = oi.edit_transition_in_duration
            item.transition_out        = oi.edit_transition_out
            item.transition_out_duration = oi.edit_transition_out_duration

            # Si el nombre de objeto cambio y ya no coincide con el objeto
            # previamente importado, limpiar el vinculo (se re-importara).
            if item.imported_object_name:
                current = bpy.data.objects.get(item.imported_object_name)
                if current is None or current.name.split('.')[0] != item.object_name:
                    item.imported_object_name = ""

            # Si no hay objeto vinculado, intentar usar el de "Importar .blend al Outliner"
            if not item.imported_object_name:
                item.imported_object_name = _resolve_preview_object_for_item(oi, item)

            self.report({"INFO"}, f"Objeto '{item.label}' actualizado")
        return {"FINISHED"}


class CERDO_1_ST_OT_ObjImportBrowseBlend(Operator):
    """
    Abre el explorador de archivos de Blender posicionado en
    Alfred_Animacion/objetos/, para que el usuario navegue las subcarpetas
    (vanilla, jerry, guard_ribbit, ribbits, ...) y seleccione el .blend
    a importar.

    Al seleccionar un archivo:
      - oi.edit_object_folder  = ruta relativa desde objetos/ hasta la
                                  carpeta que contiene el .blend
                                  (ej. 'vanilla/shield', 'jerry/espada')
      - oi.edit_blend_filename = nombre del archivo .blend
      - oi.edit_object_name    = primer objeto encontrado dentro del .blend
                                  (si se pudo leer)
    """
    bl_idname    = "cerdo_1_st.obj_import_browse_blend"
    bl_label     = "Buscar .blend"
    bl_description = (
        "Abre el explorador de archivos en objetos/ para navegar las carpetas "
        "(vanilla, jerry, guard_ribbit, ribbits, ...) y elegir el .blend a importar. "
        "Completa automaticamente Carpeta, Archivo .blend y Nombre objeto."
    )
    bl_options   = {"REGISTER", "UNDO"}

    filepath:    bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.blend", options={"HIDDEN"})

    def invoke(self, context, event):
        st = context.scene.cerdo_1_st
        anchor_dir = bpy.path.abspath(st.anim_dir) if st.anim_dir else bpy.path.abspath("//")
        levels_up  = context.scene.cerdo_1_st.object_imports.edit_levels_up
        objetos_dir = _oiu_preview.get_objetos_base_path_from_anchor(anchor_dir, levels_up)

        start_dir = objetos_dir if os.path.isdir(objetos_dir) else anchor_dir
        self.filepath = os.path.join(start_dir, "")  # asegura separador final -> abre EN la carpeta

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        st = context.scene.cerdo_1_st
        oi = st.object_imports

        selected_path = bpy.path.abspath(self.filepath)

        if not selected_path.lower().endswith(".blend"):
            self.report({"ERROR"}, "Selecciona un archivo .blend")
            return {"CANCELLED"}

        if not os.path.isfile(selected_path):
            self.report({"ERROR"}, f"Archivo no encontrado: {selected_path}")
            return {"CANCELLED"}

        anchor_dir  = bpy.path.abspath(st.anim_dir) if st.anim_dir else bpy.path.abspath("//")
        objetos_dir = _oiu_preview.get_objetos_base_path_from_anchor(anchor_dir, oi.edit_levels_up)

        blend_dir  = os.path.dirname(selected_path)
        blend_name = os.path.basename(selected_path)

        try:
            rel_folder = os.path.relpath(blend_dir, objetos_dir)
        except ValueError:
            rel_folder = blend_dir  # distinta unidad (Windows) — usar ruta absoluta como fallback

        rel_folder = rel_folder.replace(os.sep, "/")

        if rel_folder in (".", ""):
            self.report(
                {"ERROR"},
                f"Selecciona un .blend dentro de una subcarpeta de:\n{objetos_dir}"
            )
            return {"CANCELLED"}

        if rel_folder.startswith(".."):
            self.report(
                {"WARNING"},
                f"El archivo esta fuera de objetos/ ({objetos_dir}). "
                f"Se guardara la ruta tal cual, pero puede no funcionar al exportar/CONCATENAR."
            )

        oi.edit_object_folder  = rel_folder
        oi.edit_blend_filename = blend_name

        # Intentar detectar el nombre del objeto dentro del .blend
        names = _oiu_preview.list_objects_in_blend(selected_path)
        if names:
            # Preferir un objeto cuyo nombre coincida con el de la carpeta
            # (convencion usada en shield/shield.blend, stone_sword/stone_sword.blend, etc.)
            folder_base = os.path.basename(rel_folder)
            blend_base  = os.path.splitext(blend_name)[0]
            preferred = None
            for cand in (blend_base, folder_base):
                if cand in names:
                    preferred = cand
                    break
            oi.edit_object_name = preferred or names[0]

            if len(names) > 1:
                self.report(
                    {"INFO"},
                    f"'{blend_name}' contiene {len(names)} objetos: {', '.join(names)}. "
                    f"Se selecciono '{oi.edit_object_name}' — cambia 'Nombre objeto' si no es el correcto."
                )
            else:
                self.report({"INFO"}, f"Objeto detectado: '{oi.edit_object_name}'")
        else:
            self.report(
                {"WARNING"},
                f"No se pudo leer la lista de objetos de '{blend_name}'. "
                f"Completa 'Nombre objeto' manualmente."
            )

        return {"FINISHED"}



class CERDO_1_ST_OT_ObjImportDetectArmature(Operator):
    """
    Detecta automaticamente el (unico) armature presente en la escena y
    lo asigna a oi.edit_parent_armature. Cerdo_1 tiene un solo armature
    llamado "Armature" — este boton evita que el usuario escriba a mano
    un nombre incorrecto (ej. "left_arm", que no existe en este rig).

    Si se proporciona apply_to_all=True, tambien actualiza
    item.parent_armature en todos los items existentes de la lista.
    """
    bl_idname    = "cerdo_1_st.obj_import_detect_armature"
    bl_label     = "Detectar Armature"
    bl_description = (
        "Busca el armature de la escena y lo asigna automaticamente al campo Armature, "
        "evitando nombres incorrectos escritos a mano."
    )
    bl_options   = {"REGISTER", "UNDO"}

    apply_to_all: bpy.props.BoolProperty(
        name="Aplicar a todos los items",
        description="Tambien actualiza el Armature de todos los objetos ya agregados a la lista",
        default=False,
    )

    def execute(self, context):
        oi = context.scene.cerdo_1_st.object_imports

        armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']

        if len(armatures) == 0:
            self.report({"ERROR"}, "No se encontro ningun Armature en la escena")
            return {"CANCELLED"}

        if len(armatures) > 1:
            names = ", ".join(o.name for o in armatures)
            self.report(
                {"WARNING"},
                f"Hay {len(armatures)} armatures en la escena ({names}). "
                f"Se uso '{armatures[0].name}', verifica que sea el correcto."
            )

        armature_name = armatures[0].name
        oi.edit_parent_armature = armature_name

        if self.apply_to_all:
            for item in oi.items:
                item.parent_armature = armature_name

        self.report({"INFO"}, f"Armature detectado: '{armature_name}'")
        return {"FINISHED"}


class CERDO_1_ST_OT_ObjImportPreviewNow(Operator):
    """
    Importa el objeto .blend al Outliner usando los valores del editor
    (Carpeta, .blend, Nombre objeto, Niveles arriba), SIN aplicar todavia
    parenteo, transform ni visibilidad por frames.

    Permite verificar que la malla se importa correctamente antes de
    configurar los demas parametros. Una vez importado, el objeto queda
    visible en el Outliner y se puede ajustar manualmente o seguir el
    flujo normal (Agregar objeto -> CONCATENAR).
    """
    bl_idname    = "cerdo_1_st.obj_import_preview_now"
    bl_label     = "Importar .blend al Outliner"
    bl_description = (
        "Importa la malla .blend definida arriba (Carpeta / .blend / Nombre objeto) "
        "directamente al Outliner, sin aplicar parenteo ni transformaciones todavia. "
        "Usalo para verificar que la ruta y el nombre del objeto son correctos."
    )
    bl_options   = {"REGISTER", "UNDO"}

    def execute(self, context):
        st = context.scene.cerdo_1_st
        oi = st.object_imports

        object_folder  = (oi.edit_object_folder or "").strip()
        blend_filename = (oi.edit_blend_filename or "").strip()
        object_name    = (oi.edit_object_name or "").strip()
        levels_up      = oi.edit_levels_up

        if not object_folder or not blend_filename or not object_name:
            self.report({"ERROR"}, "Completa Carpeta, Archivo .blend y Nombre objeto antes de importar")
            return {"CANCELLED"}

        anchor_dir = bpy.path.abspath(st.anim_dir) if st.anim_dir else bpy.path.abspath("//")
        base_path  = _oiu_preview.get_objetos_base_path_from_anchor(anchor_dir, levels_up)
        object_dir = _oiu_preview.resolve_object_folder_path(base_path, object_folder)
        blend_path = os.path.join(object_dir, blend_filename)

        if not os.path.exists(blend_path):
            self.report({"ERROR"}, f"No se encontro el archivo: {blend_path}")
            return {"CANCELLED"}

        obj = _oiu_preview.import_object_from_blend_path(blend_path, object_name)

        if obj is None:
            self.report(
                {"ERROR"},
                f"No se encontro el objeto '{object_name}' dentro de {blend_filename}. "
                f"Revisa el nombre exacto del objeto en el .blend."
            )
            return {"CANCELLED"}

        # Seleccionar el objeto importado y enfocarlo en el Outliner/Viewport
        for o in context.selected_objects:
            o.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj

        # Recordar este objeto para reutilizarlo al Agregar/Actualizar el item
        oi.edit_imported_object_name = obj.name

        self.report({"INFO"}, f"Objeto '{obj.name}' importado correctamente desde {blend_path}")
        return {"FINISHED"}


# =============================================================================
# SERIALIZACION / DESERIALIZACION: OBJECT_IMPORTS_CONFIG
# =============================================================================

def _build_object_imports_code(st):
    """
    Genera el bloque OBJECT_IMPORTS_CONFIG para el .py exportado de Cerdo_1.
    Incluye toda la lista de objetos (enabled y disabled) para que el
    importador pueda restaurar el estado completo del panel.
    El bloque tambien incluye el codigo de importacion ejecutable directamente.
    """
    oi = st.object_imports
    items_list = []
    for item in oi.items:
        items_list.append({
            "label":           item.label,
            "object_folder":   item.object_folder,
            "blend_filename":  item.blend_filename,
            "object_name":     item.object_name,
            "frame_start":     item.frame_start,
            "frame_end":       item.frame_end,
            "parent_armature": item.parent_armature,
            "parent_bone":     item.parent_bone,
            "loc_x":           round(item.loc_x, 6),
            "loc_y":           round(item.loc_y, 6),
            "loc_z":           round(item.loc_z, 6),
            "rot_x":           round(item.rot_x, 6),
            "rot_y":           round(item.rot_y, 6),
            "rot_z":           round(item.rot_z, 6),
            "scale_uniform":   round(item.scale_uniform, 6),
            "levels_up":       item.levels_up,
            "enabled":         item.enabled,
            "segment_idx":     getattr(item, "segment_idx", -1),
            "transition_in":           getattr(item, "transition_in", "NONE"),
            "transition_in_duration":  getattr(item, "transition_in_duration", 8),
            "transition_out":          getattr(item, "transition_out", "NONE"),
            "transition_out_duration": getattr(item, "transition_out_duration", 8),
        })
    cfg = {
        "enabled": oi.enabled,
        "items":   items_list,
    }
    import json as _json
    serialized = _json.dumps(cfg, ensure_ascii=False)
    return (
        "# ── Importacion de objetos (Cerdo_1) ────────────────────────────\n"
        "import json as _json_obj_alf\n"
        f"OBJECT_IMPORTS_CONFIG = _json_obj_alf.loads({repr(serialized)})\n"
        "\n"
        "def _run_object_imports(slot_file=__file__):\n"
        "    \"\"\"\n"
        "    Ejecuta la importacion de todos los objetos activos definidos en OBJECT_IMPORTS_CONFIG.\n"
        "    Llama a esta funcion desde setup() en el slot exportado.\n"
        "    Requiere object_import_utils.py en el PYTHONPATH o en el mismo directorio del slot.\n"
        "    \"\"\"\n"
        "    if not OBJECT_IMPORTS_CONFIG.get('enabled'):\n"
        "        return\n"
        "    try:\n"
        "        import importlib, sys, os as _os\n"
        "        _utils_path = _os.path.dirname(_os.path.abspath(slot_file))\n"
        "        if _utils_path not in sys.path:\n"
        "            sys.path.insert(0, _utils_path)\n"
        "        import object_import_utils as _oiu\n"
        "    except ImportError:\n"
        "        print('  ⚠️  object_import_utils no encontrado — omitiendo importacion de objetos')\n"
        "        return\n"
        "    for _it in OBJECT_IMPORTS_CONFIG.get('items', []):\n"
        "        if not _it.get('enabled', True):\n"
        "            continue\n"
        "        _obj = _oiu.import_object_from_blend(\n"
        "            file_dunder=slot_file,\n"
        "            object_folder=_it['object_folder'],\n"
        "            blend_filename=_it['blend_filename'],\n"
        "            object_name=_it['object_name'],\n"
        "            levels_up=_it.get('levels_up', 4),\n"
        "        )\n"
        "        if _obj is None:\n"
        "            print(f\"  ⚠️  No se pudo importar '{_it['object_name']}' — omitiendo\")\n"
        "            continue\n"
        "        _oiu.hide_until_frame(_obj, appear_frame=_it['frame_start'])\n"
        "        _oiu.set_visibility_keyframes(_obj, _it['frame_end'], visible=False)\n"
        "        _bone = _it.get('parent_bone', '').strip()\n"
        "        _arm  = _it.get('parent_armature', '').strip()\n"
        "        if _arm:\n"
        "            if _bone:\n"
        "                _oiu.parent_to_bone(_obj, armature_name=_arm, exact_bone_name=_bone)\n"
        "            else:\n"
        "                _oiu.parent_to_bone(_obj, armature_name=_arm)\n"
        "        _oiu.apply_transform(\n"
        "            _obj,\n"
        "            location=(_it['loc_x'], _it['loc_y'], _it['loc_z']),\n"
        "            rotation_euler=(_it['rot_x'], _it['rot_y'], _it['rot_z']),\n"
        "            scale=(_it['scale_uniform'], _it['scale_uniform'], _it['scale_uniform']),\n"
        "        )\n"
        "        print(f\"  ✅ Objeto '{_it['label']}' importado (frames {_it['frame_start']}→{_it['frame_end']})\")\n"
    )


def _build_throw_config_code(scene):
    """
    Genera el bloque SEGMENTS_THROW_CONFIG para el .py exportado.
    Serializa todos los throws de todos los segmentos del Paso 3 (cerdo_1_segs),
    de forma que el importador .py pueda restaurarlos automaticamente igual
    que OBJECT_IMPORTS_CONFIG.
    """
    import json as _json
    result = []
    try:
        segs = scene.cerdo_1_segs.segments
    except Exception:
        segs = []

    for seg_idx, seg in enumerate(segs):
        th = seg.throws
        for item in th.items:
            wps = [
                {"label": wp.label, "x": round(wp.x, 4), "y": round(wp.y, 4),
                 "z": round(wp.z, 4), "easing": wp.easing, "enabled": wp.enabled}
                for wp in item.waypoints
            ]
            result.append({
                "seg_idx":            seg_idx,
                "seg_label":          seg.label,
                "seg_frame_start":    seg.frame_start,
                "seg_frame_end":      seg.frame_end,
                "enabled":            item.enabled,
                "label":              item.label,
                "mode":               item.mode,
                "object_folder":      item.object_folder,
                "blend_filename":     item.blend_filename,
                "object_name":        item.object_name,
                "levels_up":          item.levels_up,
                "frame_start":        item.frame_start,
                "frame_end":          item.frame_end,
                "parent_armature":    item.parent_armature,
                "parent_bone":        item.parent_bone,
                "loc_x": round(item.loc_x, 6), "loc_y": round(item.loc_y, 6), "loc_z": round(item.loc_z, 6),
                "rot_x": round(item.rot_x, 6), "rot_y": round(item.rot_y, 6), "rot_z": round(item.rot_z, 6),
                "scale_uniform":      round(item.scale_uniform, 6),
                "target_object":      item.target_object,
                "target_armature":    item.target_armature,
                "target_bone":        item.target_bone,
                "dest_x": round(item.dest_x, 6), "dest_y": round(item.dest_y, 6), "dest_z": round(item.dest_z, 6),
                "easing_global":      item.easing_global,
                "spin_during_flight": item.spin_during_flight,
                "spin_turns":         round(item.spin_turns, 3),
                "waypoints":          wps,
            })

    serialized = _json.dumps(result, ensure_ascii=False)
    return (
        "# ── Lanzar / Recoger Objetos (throws por segmento) ─────────────────\n"
        "import json as _json_throw_alf\n"
        f"SEGMENTS_THROW_CONFIG = _json_throw_alf.loads({repr(serialized)})\n"
    )


# =============================================================================
# OPERADORES: LANZAR / RECOGER OBJETOS
# =============================================================================

THROW_EASING_TO_BLENDER = {
    'LINEAR':   ('LINEAR',  'AUTO'),
    'SMOOTH':   ('BEZIER',  'AUTO'),
    'EASE_IN':  ('BEZIER',  'EASE_IN'),
    'EASE_OUT': ('BEZIER',  'EASE_OUT'),
    'BOUNCE':   ('BOUNCE',  'AUTO'),
    'ELASTIC':  ('ELASTIC', 'EASE_OUT'),
    'BACK':     ('BACK',    'EASE_OUT'),
    'PARABOLA': ('BEZIER',  'EASE_IN'),  # se maneja manualmente con punto de control
}


def _throw_set_kf_interp(action, data_path, frame, easing_key):
    """Aplica la interpolacion correcta al keyframe mas cercano al frame dado."""
    interp, easing = THROW_EASING_TO_BLENDER.get(easing_key, ('BEZIER', 'AUTO'))
    for fc in get_fcurves(action):
        if fc.data_path != data_path:
            continue
        for kp in fc.keyframe_points:
            if abs(kp.co.x - frame) < 0.5:
                kp.interpolation = interp
                if hasattr(kp, 'easing'):
                    kp.easing = easing
                if interp == 'BACK' and hasattr(kp, 'back'):
                    kp.back = 1.7
                if interp == 'ELASTIC' and hasattr(kp, 'amplitude'):
                    kp.amplitude = 0.6
                    kp.period = 0.3


def _throw_get_bone_world_loc(armature_name, bone_name):
    """Obtiene la ubicacion mundial (world space) de la cabeza del bone."""
    arm = bpy.data.objects.get(armature_name)
    if arm is None or arm.type != 'ARMATURE':
        return (0.0, 0.0, 0.0)
    pbone = arm.pose.bones.get(bone_name)
    if pbone is None:
        return (0.0, 0.0, 0.0)
    world_mat = arm.matrix_world @ pbone.matrix
    return (world_mat.translation.x, world_mat.translation.y, world_mat.translation.z)


def _throw_ensure_action(obj):
    if obj.animation_data is None:
        obj.animation_data_create()
    if obj.animation_data.action is None:
        obj.animation_data.action = bpy.data.actions.new(f"{obj.name}_throw_anim")
    return obj.animation_data.action


def _throw_insert_loc_kf(obj, frame, x, y, z):
    obj.location = (x, y, z)
    obj.keyframe_insert(data_path="location", frame=frame)


def _throw_insert_rot_kf(obj, frame, rz):
    obj.rotation_euler[2] = rz
    obj.keyframe_insert(data_path="rotation_euler", frame=frame, index=2)


def apply_throw_filter(seg, context=None):
    """
    Aplica el filtro Lanzar/Recoger al segmento 'seg'.

    ESTRATEGIA DE PARENTEO:
    - El objeto está parentado al bone con matrix_parent_inverse=Identity.
    - Su location LOCAL (0,0,0) = cabeza del bone en world space.
    - Para moverlo en world space hay que DESVINCULAR temporalmente,
      insertar KFs en world space, luego RE-PARENTEAR con Keep Transform
      para que los KFs queden en world space sin romper el parenteo.
    - Alternativa más simple y robusta: desvincular permanentemente para
      la trayectoria (el objeto ya voló — no necesita seguir al bone).
    """
    import math
    import mathutils

    ts = seg.throw_settings
    if not ts.enabled:
        return

    obj = bpy.data.objects.get(ts.target_object)
    if obj is None:
        print(f"[THROW] ERROR: objeto '{ts.target_object}' no encontrado")
        return

    f0    = ts.frame_start
    f_end = ts.frame_end
    print(f"[THROW] frames configurados: {f0} → {f_end}")

    # ── 1. Posición mundial del bone en el frame de inicio ────────────────
    # Mover la escena al frame_start para leer la posición real del bone
    scene = bpy.context.scene if context is None else context.scene
    frame_original = scene.frame_current
    scene.frame_set(f0)
    bpy.context.view_layer.update()

    bone_loc = _throw_get_bone_world_loc(ts.target_armature, ts.target_bone)
    print(f"[THROW] bone_loc en frame {f0}: {bone_loc}")

    dest = (ts.dest_x, ts.dest_y, ts.dest_z)
    active_wps = [wp for wp in ts.waypoints if wp.enabled]
    total_frames = max(1, f_end - f0)

    # ── 2. Construir puntos de control ────────────────────────────────────
    if ts.mode == 'THROW':
        control_points = (
            [(f0,    bone_loc[0], bone_loc[1], bone_loc[2], ts.easing_global)]
            + [(None, wp.x, wp.y, wp.z, wp.easing) for wp in active_wps]
            + [(f_end, dest[0],    dest[1],    dest[2],    ts.easing_global)]
        )
    else:  # CATCH
        control_points = (
            [(f0,    dest[0],    dest[1],    dest[2],    ts.easing_global)]
            + [(None, wp.x, wp.y, wp.z, wp.easing) for wp in reversed(active_wps)]
            + [(f_end, bone_loc[0], bone_loc[1], bone_loc[2], ts.easing_global)]
        )

    # Distribuir frames intermedios equitativamente
    n = len(control_points)
    frame_step = total_frames / max(1, n - 1)
    for idx, pt in enumerate(control_points):
        if pt[0] is None:
            control_points[idx] = (int(f0 + idx * frame_step),
                                   pt[1], pt[2], pt[3], pt[4])

    print(f"[THROW] control_points: {[(p[0], round(p[1],2), round(p[2],2), round(p[3],2)) for p in control_points]}")

    # ── 3. Desvincular del bone para trabajar en world space ──────────────
    # Guardar matrix world ANTES de desvincular
    world_matrix_saved = obj.matrix_world.copy()

    obj.parent      = None
    obj.parent_bone = ""
    obj.parent_type = 'OBJECT'
    # Restaurar posición world que tenía (para no saltar al desvincular)
    obj.matrix_world = world_matrix_saved
    bpy.context.view_layer.update()

    # ── 4. Insertar keyframes en world space ──────────────────────────────
    action = _throw_ensure_action(obj)

    for (frame, x, y, z, easing) in control_points:
        scene.frame_set(int(frame))
        obj.location = (x, y, z)
        obj.keyframe_insert(data_path="location", frame=int(frame))
        print(f"[THROW]   KF location frame={frame} → ({x:.3f},{y:.3f},{z:.3f})")

    # ── 5. Aplicar easing por tramo ───────────────────────────────────────
    for (frame, x, y, z, easing) in control_points[:-1]:
        _throw_set_kf_interp(action, "location", int(frame), easing)

    # ── 6. Rotación en vuelo ──────────────────────────────────────────────
    if ts.spin_during_flight:
        turns    = ts.spin_turns
        rz_start = obj.rotation_euler[2]
        rz_end   = rz_start + math.radians(360.0 * turns)
        if ts.mode == 'CATCH':
            rz_start, rz_end = rz_end, rz_start
        scene.frame_set(f0)
        obj.rotation_euler[2] = rz_start
        obj.keyframe_insert(data_path="rotation_euler", frame=f0, index=2)
        scene.frame_set(f_end)
        obj.rotation_euler[2] = rz_end
        obj.keyframe_insert(data_path="rotation_euler", frame=f_end, index=2)
        _throw_set_kf_interp(action, "rotation_euler", f0, ts.easing_global)

    # ── 7. Restaurar frame original ───────────────────────────────────────
    scene.frame_set(frame_original)
    bpy.context.view_layer.update()

    print(f"[THROW] OK: '{ts.target_object}' modo={ts.mode} "
          f"frames={f0}→{f_end} puntos={len(control_points)} wps={len(active_wps)}")


class CERDO_1_ST_OT_ThrowScanObjects(bpy.types.Operator):
    """Escanea la escena buscando objetos parentados al armature de Cerdo_1 y muestra opciones"""
    bl_idname = "cerdo_1_st.throw_scan_objects"
    bl_label  = "Escanear objetos parentados"
    bl_description = ("Busca en la escena todos los objetos parentados al armature de Cerdo_1 "
                      "y rellena automáticamente el campo Objeto y Bone")

    seg_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        segs = context.scene.cerdo_1_segs.segments
        if self.seg_idx < 0 or self.seg_idx >= len(segs):
            self.report({'ERROR'}, "Índice de segmento inválido")
            return {'CANCELLED'}
        seg = segs[self.seg_idx]
        ts  = seg.throw_settings

        arm = bpy.data.objects.get(ts.target_armature)
        if arm is None:
            self.report({'WARNING'}, f"Armature '{ts.target_armature}' no encontrado en la escena")
            return {'CANCELLED'}

        # Buscar objetos cuyo parent sea este armature
        parented = []
        for ob in bpy.data.objects:
            if ob.parent == arm:
                bone_name = ob.parent_bone if ob.parent_bone else "(sin bone)"
                parented.append(f"  • {ob.name}  ←  {bone_name}")

        if not parented:
            self.report({'WARNING'}, f"No se encontraron objetos parentados a '{ts.target_armature}'")
            return {'CANCELLED'}

        msg = "Objetos encontrados:\n" + "\n".join(parented[:10])
        self.report({'INFO'}, f"Encontrados {len(parented)} objeto(s) parentado(s) — ver consola")
        print(f"\n[THROW SCAN] Armature: '{ts.target_armature}'")
        for line in parented:
            print(line)
        return {'FINISHED'}


class CERDO_1_ST_OT_ThrowPickObject(bpy.types.Operator):
    """Usa el objeto activo seleccionado en la escena como objeto a lanzar"""
    bl_idname = "cerdo_1_st.throw_pick_object"
    bl_label  = "Usar objeto activo"
    bl_description = "Toma el objeto activo (seleccionado en el viewport) y lo asigna como objeto a lanzar/recoger"

    seg_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        segs = context.scene.cerdo_1_segs.segments
        if self.seg_idx < 0 or self.seg_idx >= len(segs):
            self.report({'ERROR'}, "Índice de segmento inválido")
            return {'CANCELLED'}
        seg = segs[self.seg_idx]
        ts  = seg.throw_settings

        obj = context.active_object
        if obj is None:
            self.report({'WARNING'}, "No hay objeto activo en el viewport")
            return {'CANCELLED'}

        ts.target_object = obj.name
        if obj.parent and obj.parent.type == 'ARMATURE':
            ts.target_armature = obj.parent.name
            ts.target_bone = obj.parent_bone if obj.parent_bone else ""
            self.report({'INFO'}, f"Asignado: '{obj.name}' (bone: '{ts.target_bone}')")
        else:
            self.report({'INFO'}, f"Asignado: '{obj.name}' (sin parent armature detectado)")
        return {'FINISHED'}


class CERDO_1_ST_OT_ThrowPickDestFromCursor(bpy.types.Operator):
    """Toma la posición del 3D Cursor como coordenada destino"""
    bl_idname = "cerdo_1_st.throw_pick_dest_cursor"
    bl_label  = "Destino desde cursor 3D"
    bl_description = "Usa la posición actual del 3D Cursor como coordenada de destino"

    seg_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        segs = context.scene.cerdo_1_segs.segments
        if self.seg_idx < 0 or self.seg_idx >= len(segs):
            self.report({'ERROR'}, "Índice de segmento inválido")
            return {'CANCELLED'}
        seg = segs[self.seg_idx]
        ts  = seg.throw_settings
        cur = context.scene.cursor.location
        ts.dest_x = cur.x
        ts.dest_y = cur.y
        ts.dest_z = cur.z
        self.report({'INFO'}, f"Destino: ({cur.x:.3f}, {cur.y:.3f}, {cur.z:.3f})")
        return {'FINISHED'}


class CERDO_1_ST_OT_ThrowAddWaypoint(bpy.types.Operator):
    """Agrega un punto intermedio (waypoint) a la trayectoria"""
    bl_idname = "cerdo_1_st.throw_add_waypoint"
    bl_label  = "Agregar waypoint"
    bl_description = "Agrega un punto intermedio a la trayectoria. Se puede tomar del cursor 3D."

    seg_idx:       bpy.props.IntProperty(default=0)
    from_cursor:   bpy.props.BoolProperty(default=False,
                      description="Si True, toma las coordenadas del 3D Cursor")

    def execute(self, context):
        segs = context.scene.cerdo_1_segs.segments
        if self.seg_idx < 0 or self.seg_idx >= len(segs):
            self.report({'ERROR'}, "Índice de segmento inválido")
            return {'CANCELLED'}
        seg = segs[self.seg_idx]
        ts  = seg.throw_settings
        wp  = ts.waypoints.add()
        wp.label = f"Punto {len(ts.waypoints)}"
        if self.from_cursor:
            cur = context.scene.cursor.location
            wp.x = cur.x
            wp.y = cur.y
            wp.z = cur.z
            self.report({'INFO'}, f"Waypoint desde cursor: ({cur.x:.2f}, {cur.y:.2f}, {cur.z:.2f})")
        ts.waypoints_idx = len(ts.waypoints) - 1
        return {'FINISHED'}


class CERDO_1_ST_OT_ThrowRemoveWaypoint(bpy.types.Operator):
    """Elimina el waypoint seleccionado"""
    bl_idname = "cerdo_1_st.throw_remove_waypoint"
    bl_label  = "Eliminar waypoint"

    seg_idx: bpy.props.IntProperty(default=0)
    wp_idx:  bpy.props.IntProperty(default=0)

    def execute(self, context):
        segs = context.scene.cerdo_1_segs.segments
        if self.seg_idx < 0 or self.seg_idx >= len(segs):
            return {'CANCELLED'}
        ts = segs[self.seg_idx].throw_settings
        if 0 <= self.wp_idx < len(ts.waypoints):
            ts.waypoints.remove(self.wp_idx)
            ts.waypoints_idx = max(0, self.wp_idx - 1)
        return {'FINISHED'}


class CERDO_1_ST_OT_ThrowMoveWaypoint(bpy.types.Operator):
    """Mueve un waypoint arriba o abajo en la lista"""
    bl_idname = "cerdo_1_st.throw_move_waypoint"
    bl_label  = "Mover waypoint"

    seg_idx:    bpy.props.IntProperty(default=0)
    wp_idx:     bpy.props.IntProperty(default=0)
    direction:  bpy.props.EnumProperty(items=[('UP','Subir',''),('DOWN','Bajar','')], default='UP')

    def execute(self, context):
        segs = context.scene.cerdo_1_segs.segments
        if self.seg_idx < 0 or self.seg_idx >= len(segs):
            return {'CANCELLED'}
        ts  = segs[self.seg_idx].throw_settings
        idx = self.wp_idx
        n   = len(ts.waypoints)
        if self.direction == 'UP' and idx > 0:
            ts.waypoints.move(idx, idx - 1)
            ts.waypoints_idx = idx - 1
        elif self.direction == 'DOWN' and idx < n - 1:
            ts.waypoints.move(idx, idx + 1)
            ts.waypoints_idx = idx + 1
        return {'FINISHED'}


class CERDO_1_ST_OT_ThrowWaypointFromCursor(bpy.types.Operator):
    """Actualiza las coordenadas del waypoint seleccionado con la posición del 3D Cursor"""
    bl_idname = "cerdo_1_st.throw_wp_from_cursor"
    bl_label  = "Coordenadas desde cursor 3D"
    bl_description = "Copia la posición del 3D Cursor al waypoint activo"

    seg_idx: bpy.props.IntProperty(default=0)
    wp_idx:  bpy.props.IntProperty(default=0)

    def execute(self, context):
        segs = context.scene.cerdo_1_segs.segments
        if self.seg_idx < 0 or self.seg_idx >= len(segs):
            return {'CANCELLED'}
        ts = segs[self.seg_idx].throw_settings
        if 0 <= self.wp_idx < len(ts.waypoints):
            cur = context.scene.cursor.location
            wp  = ts.waypoints[self.wp_idx]
            wp.x, wp.y, wp.z = cur.x, cur.y, cur.z
            self.report({'INFO'}, f"Waypoint '{wp.label}': ({cur.x:.3f}, {cur.y:.3f}, {cur.z:.3f})")
        return {'FINISHED'}


class CERDO_1_ST_OT_ThrowApply(bpy.types.Operator):
    """Aplica el lanzamiento/recoger al objeto — genera los keyframes de trayectoria"""
    bl_idname = "cerdo_1_st.throw_apply"
    bl_label  = "Aplicar trayectoria"
    bl_description = ("Genera los keyframes de location (y rotación) en el objeto "
                      "siguiendo la trayectoria configurada con los waypoints y easings")

    seg_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        segs = context.scene.cerdo_1_segs.segments
        if self.seg_idx < 0 or self.seg_idx >= len(segs):
            self.report({'ERROR'}, "Índice de segmento inválido")
            return {'CANCELLED'}
        seg = segs[self.seg_idx]
        ts  = seg.throw_settings
        if not ts.target_object:
            self.report({'ERROR'}, "No hay objeto asignado — usa 'Usar objeto activo'")
            return {'CANCELLED'}
        if not bpy.data.objects.get(ts.target_object):
            self.report({'ERROR'}, f"Objeto '{ts.target_object}' no encontrado en la escena")
            return {'CANCELLED'}
        try:
            apply_throw_filter(seg, context)
            self.report({'INFO'}, f"Trayectoria aplicada a '{ts.target_object}' ({len(ts.waypoints)} waypoints)")
        except Exception as e:
            self.report({'ERROR'}, f"Error al aplicar trayectoria: {e}")
            import traceback; traceback.print_exc()
            return {'CANCELLED'}
        return {'FINISHED'}


class CERDO_1_ST_OT_ThrowClearKeyframes(bpy.types.Operator):
    """Elimina todos los keyframes de location/rotation generados por el lanzamiento"""
    bl_idname = "cerdo_1_st.throw_clear_keyframes"
    bl_label  = "Limpiar keyframes de trayectoria"
    bl_description = "Elimina los keyframes de location y rotation_euler del objeto en el rango del lanzamiento"

    seg_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        segs = context.scene.cerdo_1_segs.segments
        if self.seg_idx < 0 or self.seg_idx >= len(segs):
            return {'CANCELLED'}
        seg = segs[self.seg_idx]
        ts  = seg.throw_settings
        obj = bpy.data.objects.get(ts.target_object)
        if obj is None or obj.animation_data is None or obj.animation_data.action is None:
            self.report({'WARNING'}, "El objeto no tiene animación para limpiar")
            return {'CANCELLED'}
        action = obj.animation_data.action
        f0, f1 = ts.frame_start, ts.frame_end
        removed = 0
        for fc in get_fcurves(action):
            if fc.data_path not in ('location', 'rotation_euler'):
                continue
            to_remove = [i for i, kp in enumerate(fc.keyframe_points)
                         if f0 <= kp.co.x <= f1]
            for i in reversed(to_remove):
                fc.keyframe_points.remove(fc.keyframe_points[i])
                removed += 1
        self.report({'INFO'}, f"Eliminados {removed} keyframes en rango {f0}→{f1}")
        return {'FINISHED'}





# =============================================================================
# OPERADORES: LANZAR / RECOGER OBJETOS (arquitectura de colección)
# =============================================================================

THROW_EASING_TO_BLENDER = {
    'LINEAR':   ('LINEAR',  'AUTO'),
    'SMOOTH':   ('BEZIER',  'AUTO'),
    'EASE_IN':  ('BEZIER',  'EASE_IN'),
    'EASE_OUT': ('BEZIER',  'EASE_OUT'),
    'BOUNCE':   ('BOUNCE',  'AUTO'),
    'ELASTIC':  ('ELASTIC', 'EASE_OUT'),
    'BACK':     ('BACK',    'EASE_OUT'),
    'PARABOLA': ('BEZIER',  'EASE_IN'),
}


def _throw_set_kf_interp(action, data_path, frame, easing_key):
    interp, easing = THROW_EASING_TO_BLENDER.get(easing_key, ('BEZIER', 'AUTO'))
    for fc in get_fcurves(action):
        if fc.data_path != data_path:
            continue
        for kp in fc.keyframe_points:
            if abs(kp.co.x - frame) < 0.5:
                kp.interpolation = interp
                if hasattr(kp, 'easing'):   kp.easing = easing
                if interp == 'BACK'    and hasattr(kp, 'back'):      kp.back = 1.7
                if interp == 'ELASTIC' and hasattr(kp, 'amplitude'): kp.amplitude = 0.6; kp.period = 0.3


def _throw_get_bone_world_loc(armature_name, bone_name):
    arm = bpy.data.objects.get(armature_name)
    if arm is None or arm.type != 'ARMATURE':
        return (0.0, 0.0, 0.0)
    pbone = arm.pose.bones.get(bone_name)
    if pbone is None:
        return (0.0, 0.0, 0.0)
    world_mat = arm.matrix_world @ pbone.matrix
    return (world_mat.translation.x, world_mat.translation.y, world_mat.translation.z)


def _throw_ensure_action(obj):
    if obj.animation_data is None:
        obj.animation_data_create()
    if obj.animation_data.action is None:
        obj.animation_data.action = bpy.data.actions.new(f"{obj.name}_throw_anim")
    return obj.animation_data.action


def _copy_edit_to_item(th, item):
    """Copia los campos edit_* de Cerdo_1ThrowsSettings al Cerdo_1ThrowItem dado."""
    item.label              = th.edit_label
    item.mode               = th.edit_mode
    item.blend_path         = th.edit_blend_path
    item.object_folder      = th.edit_object_folder
    item.blend_filename     = th.edit_blend_filename
    item.object_name        = th.edit_object_name
    item.levels_up          = th.edit_levels_up
    item.parent_armature    = th.edit_parent_armature
    item.parent_bone        = th.edit_parent_bone
    item.loc_x              = th.edit_loc_x
    item.loc_y              = th.edit_loc_y
    item.loc_z              = th.edit_loc_z
    item.rot_x              = th.edit_rot_x
    item.rot_y              = th.edit_rot_y
    item.rot_z              = th.edit_rot_z
    item.scale_uniform      = th.edit_scale_uniform
    item.frame_start        = th.edit_frame_start
    item.frame_end          = th.edit_frame_end
    item.reach_back_duration_in  = th.edit_reach_back_duration_in
    item.reach_back_enabled_out  = th.edit_reach_back_enabled_out
    item.reach_back_duration_out = th.edit_reach_back_duration_out
    item.target_armature    = th.edit_target_armature
    item.target_bone        = th.edit_target_bone
    item.dest_x             = th.edit_dest_x
    item.dest_y             = th.edit_dest_y
    item.dest_z             = th.edit_dest_z
    item.easing_global      = th.edit_easing_global
    item.spin_during_flight = th.edit_spin_during_flight
    item.spin_turns         = th.edit_spin_turns
    item.transition_in            = th.edit_transition_in
    item.transition_in_duration   = th.edit_transition_in_duration
    item.transition_out           = th.edit_transition_out
    item.transition_out_duration  = th.edit_transition_out_duration
    # Copiar el objeto importado en el editor → target_object del item
    if th.edit_imported_object_name:
        item.imported_object_name = th.edit_imported_object_name
        item.target_object        = th.edit_imported_object_name


def _copy_item_to_edit(item, th):
    """Copia un Cerdo_1ThrowItem a los campos edit_* de Cerdo_1ThrowsSettings."""
    th.edit_imported_object_name = ""  # Limpiar para no borrar el objeto del item
    th.edit_label              = item.label
    th.edit_mode               = item.mode
    th.edit_blend_path         = item.blend_path
    th.edit_object_folder      = item.object_folder
    th.edit_blend_filename     = item.blend_filename
    th.edit_object_name        = item.object_name
    th.edit_levels_up          = item.levels_up
    th.edit_parent_armature    = item.parent_armature
    th.edit_parent_bone        = item.parent_bone
    th.edit_loc_x              = item.loc_x
    th.edit_loc_y              = item.loc_y
    th.edit_loc_z              = item.loc_z
    th.edit_rot_x              = item.rot_x
    th.edit_rot_y              = item.rot_y
    th.edit_rot_z              = item.rot_z
    th.edit_scale_uniform      = item.scale_uniform
    th.edit_frame_start        = item.frame_start
    th.edit_frame_end          = item.frame_end
    th.edit_reach_back_duration_in  = item.reach_back_duration_in
    th.edit_reach_back_enabled_out  = item.reach_back_enabled_out
    th.edit_reach_back_duration_out = item.reach_back_duration_out
    th.edit_target_armature    = item.target_armature
    th.edit_target_bone        = item.target_bone
    th.edit_dest_x             = item.dest_x
    th.edit_dest_y             = item.dest_y
    th.edit_dest_z             = item.dest_z
    th.edit_easing_global      = item.easing_global
    th.edit_spin_during_flight = item.spin_during_flight
    th.edit_spin_turns         = item.spin_turns
    th.edit_transition_in            = item.transition_in
    th.edit_transition_in_duration   = item.transition_in_duration
    th.edit_transition_out           = item.transition_out
    th.edit_transition_out_duration  = item.transition_out_duration


def _get_seg_throws(context, seg_idx):
    segs = context.scene.cerdo_1_segs.segments
    if seg_idx < 0 or seg_idx >= len(segs):
        return None
    return segs[seg_idx].throws


# ── CRUD de items ─────────────────────────────────────────────────────────────

class CERDO_1_ST_OT_ThrowAddItem(bpy.types.Operator):
    """Agrega un nuevo lanzamiento/recogida usando los valores del editor"""
    bl_idname = "cerdo_1_st.throw_add_item"
    bl_label  = "Agregar lanzamiento"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        # FIX (Kebyn): antes solo se marcaba item.enabled, y th.enabled se
        # forzaba a True desde panels.py en tiempo de draw() -- Blender 4.5
        # ya no permite escribir en datablocks de la escena dentro de un
        # draw(), asi que ahora se marca aca, en el operator, que es el
        # unico lugar correcto para mutar el estado.
        th.enabled = True
        item = th.items.add()
        _copy_edit_to_item(th, item)
        item.segment_idx = self.seg_idx
        item.enabled = True
        item.uid = _new_throw_uid()
        th.active_idx = len(th.items) - 1
        self.report({"INFO"}, f"Lanzamiento '{item.label}' agregado")
        return {"FINISHED"}


class CERDO_1_ST_OT_ThrowRemoveItem(bpy.types.Operator):
    """Elimina el lanzamiento seleccionado"""
    bl_idname = "cerdo_1_st.throw_remove_item"
    bl_label  = "Eliminar lanzamiento"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        if 0 <= self.item_idx < len(th.items):
            # BUGFIX (Kebyn + Claude, 2026-09-01 ter): borrar tambien el
            # objeto que este item ya hubiera importado a la escena --
            # antes, el boton de basurero solo quitaba la fila de la lista
            # (th.items.remove) y el .blend importado quedaba huerfano en
            # bpy.data para siempre. run_throws_for_segments() ya barre
            # estos huerfanos en la SIGUIENTE "Concatenar segmentos" (por
            # uid), pero se borra tambien aca, de inmediato, para que el
            # usuario no tenga que concatenar solo para limpiar la escena.
            _item = th.items[self.item_idx]
            _obj_name = _item.imported_object_name
            if _obj_name:
                _old_obj = bpy.data.objects.get(_obj_name)
                if _old_obj is not None:
                    _old_mesh = _old_obj.data
                    bpy.data.objects.remove(_old_obj, do_unlink=True)
                    if _old_mesh is not None and getattr(_old_mesh, "users", 1) == 0:
                        try:
                            bpy.data.meshes.remove(_old_mesh)
                        except Exception:
                            pass
            th.items.remove(self.item_idx)
            th.active_idx = max(0, self.item_idx - 1)
        return {"FINISHED"}


class CERDO_1_ST_OT_ThrowToggleItem(bpy.types.Operator):
    """Activa/desactiva el lanzamiento"""
    bl_idname = "cerdo_1_st.throw_toggle_item"
    bl_label  = "Toggle lanzamiento"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        if 0 <= self.item_idx < len(th.items):
            th.items[self.item_idx].enabled = not th.items[self.item_idx].enabled
        return {"FINISHED"}


class CERDO_1_ST_OT_ThrowLoadToEditor(bpy.types.Operator):
    """Carga el lanzamiento seleccionado en el editor para modificarlo"""
    bl_idname = "cerdo_1_st.throw_load_to_editor"
    bl_label  = "Editar lanzamiento"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        if 0 <= self.item_idx < len(th.items):
            _copy_item_to_edit(th.items[self.item_idx], th)
            th.active_idx = self.item_idx
        return {"FINISHED"}


class CERDO_1_ST_OT_ThrowUpdateItem(bpy.types.Operator):
    """Actualiza el lanzamiento activo con los valores del editor"""
    bl_idname = "cerdo_1_st.throw_update_item"
    bl_label  = "Actualizar lanzamiento"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        if 0 <= self.item_idx < len(th.items):
            _copy_edit_to_item(th, th.items[self.item_idx])
            self.report({"INFO"}, f"Lanzamiento {self.item_idx} actualizado")
        return {"FINISHED"}


# ── Bone picker ───────────────────────────────────────────────────────────────

class CERDO_1_ST_OT_ThrowPickBone(bpy.types.Operator):
    """Asigna el bone al campo Bone del editor de lanzamiento"""
    bl_idname = "cerdo_1_st.throw_pick_bone"
    bl_label  = "Seleccionar bone"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:   bpy.props.IntProperty(default=0)
    bone_name: bpy.props.StringProperty(default="")

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        th.edit_parent_bone  = self.bone_name
        th.edit_target_bone  = self.bone_name
        return {"FINISHED"}


# ── Buscar .blend ─────────────────────────────────────────────────────────────

class CERDO_1_ST_OT_ThrowBrowseBlend(bpy.types.Operator):
    """Abre el explorador para seleccionar el .blend del objeto a lanzar/recoger"""
    bl_idname    = "cerdo_1_st.throw_browse_blend"
    bl_label     = "Buscar .blend"
    bl_options   = {"REGISTER", "UNDO"}
    seg_idx:     bpy.props.IntProperty(default=0)
    filepath:    bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.blend", options={"HIDDEN"})

    def invoke(self, context, event):
        st     = context.scene.cerdo_1_st
        anchor = bpy.path.abspath(st.anim_dir) if st.anim_dir else bpy.path.abspath("//")
        th     = _get_seg_throws(context, self.seg_idx)
        lv     = th.edit_levels_up if th else 4
        obj_dir = _oiu_preview.get_objetos_base_path_from_anchor(anchor, lv)
        self.filepath = os.path.join(obj_dir if os.path.isdir(obj_dir) else anchor, "")
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        sel = bpy.path.abspath(self.filepath)
        if not sel.lower().endswith(".blend") or not os.path.isfile(sel):
            self.report({"ERROR"}, "Selecciona un archivo .blend válido")
            return {"CANCELLED"}
        st      = context.scene.cerdo_1_st
        anchor  = bpy.path.abspath(st.anim_dir) if st.anim_dir else bpy.path.abspath("//")
        obj_dir = _oiu_preview.get_objetos_base_path_from_anchor(anchor, th.edit_levels_up)
        blend_dir  = os.path.dirname(sel)
        blend_name = os.path.basename(sel)
        try:    rel = os.path.relpath(blend_dir, obj_dir).replace(os.sep, "/")
        except: rel = blend_dir
        th.edit_blend_path    = sel
        th.edit_object_folder = rel
        th.edit_blend_filename = blend_name
        names = _oiu_preview.list_objects_in_blend(sel)
        if names:
            base = os.path.splitext(blend_name)[0]
            th.edit_object_name = base if base in names else names[0]
        return {"FINISHED"}


# ── Importar objeto al outliner ───────────────────────────────────────────────

class CERDO_1_ST_OT_ThrowImportObject(bpy.types.Operator):
    """Importa el .blend y lo parentea al bone — mismo flujo que Importar Objetos"""
    bl_idname  = "cerdo_1_st.throw_import_object"
    bl_label   = "Importar objeto al Outliner"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=-1)  # -1 = usar editor

    def execute(self, context):
        import mathutils
        from . import object_import_utils as _oiu
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}

        # Si item_idx >= 0 usar ese item; si no, usar editor
        if self.item_idx >= 0 and self.item_idx < len(th.items):
            src = th.items[self.item_idx]
            blend_path = src.blend_path; object_folder = src.object_folder
            blend_filename = src.blend_filename; object_name = src.object_name
            levels_up = src.levels_up; arm_name = src.parent_armature
            bone_name = src.parent_bone; frame_start = src.frame_start
            frame_end = src.frame_end
            loc = (src.loc_x, src.loc_y, src.loc_z)
            rot = (src.rot_x, src.rot_y, src.rot_z)
            scl = src.scale_uniform
            dest = (src.dest_x, src.dest_y, src.dest_z)
        else:
            blend_path = th.edit_blend_path; object_folder = th.edit_object_folder
            blend_filename = th.edit_blend_filename; object_name = th.edit_object_name
            levels_up = th.edit_levels_up; arm_name = th.edit_parent_armature
            bone_name = th.edit_parent_bone; frame_start = th.edit_frame_start
            frame_end = th.edit_frame_end
            loc = (th.edit_loc_x, th.edit_loc_y, th.edit_loc_z)
            rot = (th.edit_rot_x, th.edit_rot_y, th.edit_rot_z)
            scl = th.edit_scale_uniform
            dest = (th.edit_dest_x, th.edit_dest_y, th.edit_dest_z)
            src = None

        # ── Bloques dinamicos (ej. antorchas): libreria .blend COMPLETA +
        # renombrado secuencial global -- ver import_bloque_dinamico_full()
        # en object_import_utils.py. Mismo criterio de deteccion que en el
        # flujo automatico de Concatenar (object_folder == 'bloques_dinamicos').
        _es_bloque_dinamico = (object_folder or "").strip() == "bloques_dinamicos"

        if _es_bloque_dinamico:
            st_main = context.scene.cerdo_1_st
            anchor  = bpy.path.abspath(st_main.anim_dir) if st_main.anim_dir else bpy.path.abspath("//")
            bloques_dir = _oiu.get_bloques_dinamicos_path_from_anchor(anchor, levels_up)
            blend_abs = os.path.join(bloques_dir, blend_filename)

            # Un bloque dinamico SIEMPRE se reimporta como instancia nueva
            # (cada antorcha plantada es distinta) -- se elimina la anterior
            # de ESTE item/editor igual que abajo, pero nunca se reutiliza.
            if src:
                prev_name = src.imported_object_name
            else:
                prev_name = th.edit_imported_object_name
                if prev_name:
                    in_use = any(item.imported_object_name == prev_name for item in th.items)
                    if in_use:
                        prev_name = ""
            if prev_name:
                old_obj = bpy.data.objects.get(prev_name)
                if old_obj:
                    for _child in list(old_obj.children_recursive):
                        bpy.data.objects.remove(_child, do_unlink=True)
                    bpy.data.objects.remove(old_obj, do_unlink=True)

            root_anchor, _mapa = _oiu.import_bloque_dinamico_full(
                blend_abs,
                target_location=dest,
                base_name=object_name or None,
            )
            if root_anchor is None:
                self.report({"ERROR"}, f"No se pudo importar bloque dinamico '{object_name}' desde {blend_abs}")
                return {"CANCELLED"}

            imported_name = root_anchor.name
            if src:
                src.imported_object_name = imported_name
                src.target_object        = imported_name
            else:
                th.edit_imported_object_name = imported_name

            # BUGFIX (Kebyn + Claude, 2026-09-11: "el hacha sigue apareciendo
            # en frame_start en vez de frame_start+duracion del gesto"): el
            # boton "Importar objeto" (preview manual desde el panel) NO
            # aplicaba el gesto de brazo ni el retraso de aparicion -- solo
            # CONCATENAR/run_throws_for_segments lo hacia. Se replica aca el
            # mismo calculo para que la vista previa manual coincida con el
            # resultado real al concatenar.
            _dur_in = (src.reach_back_duration_in if src
                       else th.edit_reach_back_duration_in)
            _reach_arm = None
            if arm_name:
                _reach_arm = bpy.data.objects.get(arm_name)
                if _reach_arm is not None and _reach_arm.type != 'ARMATURE':
                    _reach_arm = None
            if _reach_arm is None:
                _reach_arm = _find_cerdo_1_armature(context)
            _appear_frame = frame_start
            try:
                _gesto_ok, _gesto_mid, _gesto_fin = apply_pre_throw_reach_back(
                    _reach_arm, frame_start, duration=_dur_in, direction='AFTER')
                if _gesto_ok:
                    _appear_frame = min(_gesto_mid, max(frame_start, frame_end - 1))
            except Exception as _e_reach_prev:
                print(f"[THROW preview] No se pudo aplicar el gesto previo: {_e_reach_prev}")

            _bloque_objs = [root_anchor] + list(root_anchor.children_recursive)
            for _bo in _bloque_objs:
                _oiu.hide_until_frame(_bo, appear_frame=_appear_frame)

            arm_obj = None
            if arm_name:
                arm_obj = bpy.data.objects.get(arm_name)
                if arm_obj is not None and arm_obj.type != 'ARMATURE':
                    arm_obj = None
            if arm_obj is None:
                arm_obj = _find_cerdo_1_armature(context)
            target_bone = None
            if arm_obj and arm_obj.pose:
                if bone_name:
                    target_bone = arm_obj.pose.bones.get(bone_name)
                if target_bone is None:
                    target_bone = next((pb for pb in arm_obj.pose.bones if 'bend' in pb.name.lower()), None)
            if target_bone:
                root_anchor.parent = target_bone.id_data
                root_anchor.parent_bone = target_bone.name
                root_anchor.parent_type = 'BONE'
                root_anchor.matrix_parent_inverse = mathutils.Matrix.Identity(4)
            elif arm_obj:
                root_anchor.parent = arm_obj
                root_anchor.parent_type = 'OBJECT'
                root_anchor.matrix_parent_inverse = mathutils.Matrix.Identity(4)

            if src and target_bone and not src.target_bone:
                src.target_bone = target_bone.name
            self.report({"INFO"}, f"'{root_anchor.name}' (bloque dinamico) importado — "
                                   f"bone '{target_bone.name if target_bone else 'ninguno'}'")
            return {"FINISHED"}

        # Resolver ruta
        if blend_path and os.path.isfile(bpy.path.abspath(blend_path)):
            blend_abs = bpy.path.abspath(blend_path)
        else:
            st_main = context.scene.cerdo_1_st
            anchor  = bpy.path.abspath(st_main.anim_dir) if st_main.anim_dir else bpy.path.abspath("//")
            obj_dir = _oiu_preview.get_objetos_base_path_from_anchor(anchor, levels_up)
            blend_abs = os.path.join(obj_dir, object_folder, blend_filename)

        # Eliminar objeto anterior solo si corresponde a ESTE slot
        if src:
            # Modo editar item existente: eliminar el objeto previo de ese item
            prev_name = src.imported_object_name
        else:
            # Modo editor nuevo: solo eliminar si edit_imported_object_name
            # NO pertenece a ningún item existente (es un objeto temporal del editor)
            prev_name = th.edit_imported_object_name
            if prev_name:
                in_use = any(item.imported_object_name == prev_name for item in th.items)
                if in_use:
                    prev_name = ""  # No eliminar — pertenece a un item guardado
        if prev_name:
            old_obj = bpy.data.objects.get(prev_name)
            if old_obj:
                old_mesh = old_obj.data
                bpy.data.objects.remove(old_obj, do_unlink=True)
                if old_mesh and old_mesh.users == 0:
                    try: bpy.data.meshes.remove(old_mesh)
                    except: pass

        obj = _oiu.import_object_from_blend_path(blend_abs, object_name)
        if obj is None:
            self.report({"ERROR"}, f"No se pudo importar '{object_name}' desde {blend_abs}")
            return {"CANCELLED"}

        imported_name = obj.name
        if src:
            src.imported_object_name = imported_name
            src.target_object        = imported_name
        else:
            th.edit_imported_object_name = imported_name

        # BUGFIX (Kebyn + Claude, 2026-09-11: "el hacha sigue apareciendo en
        # frame_start en vez de frame_start+duracion del gesto"): mismo fix
        # que en la rama de bloques dinamicos de arriba -- el boton
        # "Importar objeto" (preview manual) tiene que aplicar el gesto de
        # brazo y retrasar la aparicion del objeto igual que CONCATENAR.
        _dur_in = (src.reach_back_duration_in if src
                   else th.edit_reach_back_duration_in)
        _reach_arm = None
        if arm_name:
            _reach_arm = bpy.data.objects.get(arm_name)
            if _reach_arm is not None and _reach_arm.type != 'ARMATURE':
                _reach_arm = None
        if _reach_arm is None:
            _reach_arm = _find_cerdo_1_armature(context)
        _appear_frame = frame_start
        try:
            _gesto_ok, _gesto_mid, _gesto_fin = apply_pre_throw_reach_back(
                _reach_arm, frame_start, duration=_dur_in, direction='AFTER')
            if _gesto_ok:
                _appear_frame = min(_gesto_mid, max(frame_start, frame_end - 1))
        except Exception as _e_reach_prev:
            print(f"[THROW preview] No se pudo aplicar el gesto previo: {_e_reach_prev}")

        # Visibilidad
        _oiu.hide_until_frame(obj, appear_frame=_appear_frame)
        _oiu.set_visibility_keyframes(obj, frame_end, visible=False)

        # Parenteo idéntico a run_object_imports_live
        # BUGFIX: antes se buscaba el armature SOLO por coincidencia exacta
        # de nombre en bpy.data.objects (arm_name == o.name), cayendo a
        # "el unico armature que haya" si eso fallaba. Si el campo Armature
        # quedaba desactualizado (ej. texto por defecto "Armature" sin
        # corresponder al objeto real) y habia mas de un Armature en
        # bpy.data (comun con props/objetos que traen su propio armature),
        # esto podia resolver el armature INCORRECTO -- o ninguno -- y el
        # objeto quedaba sin aparentar al bone, aunque el usuario lo haya
        # elegido bien en el panel. Ahora se usa el mismo resolver robusto
        # que usa CONCATENAR (_find_cerdo_1_armature), que se basa en la
        # configuracion real del rig de Cerdo_1, no en texto libre.
        arm_obj = None
        if arm_name:
            arm_obj = bpy.data.objects.get(arm_name)
            if arm_obj is not None and arm_obj.type != 'ARMATURE':
                arm_obj = None
        if arm_obj is None:
            arm_obj = _find_cerdo_1_armature(context)
        target_bone = None
        if arm_obj and arm_obj.pose:
            if bone_name:
                target_bone = arm_obj.pose.bones.get(bone_name)
            if target_bone is None:
                target_bone = next((pb for pb in arm_obj.pose.bones if 'bend' in pb.name.lower()), None)

        if target_bone:
            obj.parent = target_bone.id_data
            obj.parent_bone = target_bone.name
            obj.parent_type = 'BONE'
            obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
        elif arm_obj:
            obj.parent = arm_obj
            obj.parent_type = 'OBJECT'
            obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)

        obj.location       = loc
        obj.rotation_euler = rot
        obj.scale          = (scl, scl, scl)

        if src and target_bone and not src.target_bone:
            src.target_bone = target_bone.name

        # Aviso claro y visible (no solo INFO) si no se logro aparentar al
        # bone pedido -- antes esto quedaba mudo salvo por el texto chico
        # del reporte final, y el objeto se importaba flotando sin que
        # fuera obvio por que.
        if bone_name and target_bone is None:
            if arm_obj is None:
                self.report(
                    {"ERROR"},
                    f"'{obj.name}' importado, pero no se encontro NINGUN Armature en la escena "
                    f"-- quedo sin aparentar."
                )
            else:
                self.report(
                    {"ERROR"},
                    f"'{obj.name}' importado, pero el bone '{bone_name}' no existe en "
                    f"'{arm_obj.name}' -- quedo sin aparentar al bone (revisa el nombre en el campo Bone)."
                )
        else:
            self.report({"INFO"}, f"'{obj.name}' importado — bone '{target_bone.name if target_bone else 'ninguno'}'")
        return {"FINISHED"}


# ── Sincronizar campos del editor desde el objeto real (ej. tras rotar/mover
#    a mano en el viewport, lo que deja desfasados edit_loc_*/edit_rot_*) ────

class CERDO_1_ST_OT_ThrowSyncFromObject(bpy.types.Operator):
    """
    Lee la posicion/rotacion/escala ACTUAL del objeto importado en preview
    (th.edit_imported_object_name) y la copia a los campos edit_loc_*/
    edit_rot_*/edit_scale_uniform del panel.

    Necesario porque esos campos solo empujan valores HACIA el objeto (ver
    _th_editor_update en properties.py); si el objeto se mueve/rota a mano
    en el viewport (gizmos, N-panel, etc.) el panel no se entera solo, y
    tocar cualquier campo despues pisaria ese ajuste manual con el valor
    viejo. Este boton trae el panel al dia con lo que el objeto tiene
    realmente en escena.
    """
    bl_idname  = "cerdo_1_st.throw_sync_from_object"
    bl_label   = "Sincronizar desde el objeto"
    bl_description = (
        "Copia la posicion/rotacion/escala actual del objeto en escena "
        "(por si lo moviste o rotaste a mano en el viewport) a los campos "
        "de este panel, para que no queden desfasados"
    )
    bl_options = {"REGISTER", "UNDO"}
    seg_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None:
            return {"CANCELLED"}

        obj = bpy.data.objects.get(th.edit_imported_object_name)
        if obj is None:
            self.report({"ERROR"}, "No hay ningun objeto importado en preview para sincronizar")
            return {"CANCELLED"}

        th.edit_loc_x, th.edit_loc_y, th.edit_loc_z = obj.location
        th.edit_rot_x, th.edit_rot_y, th.edit_rot_z = obj.rotation_euler
        # La escala del objeto puede no ser perfectamente uniforme si se
        # tocaron los 3 ejes por separado en el viewport; se usa el
        # promedio para no perder el ajuste, ya que el panel solo maneja
        # un unico valor de escala uniforme.
        th.edit_scale_uniform = (obj.scale.x + obj.scale.y + obj.scale.z) / 3.0

        self.report({"INFO"}, f"Sincronizado desde '{obj.name}'")
        return {"FINISHED"}


# ── Detectar armature ─────────────────────────────────────────────────────────

class CERDO_1_ST_OT_ThrowDetectArmature(bpy.types.Operator):
    """Detecta el armature y lo asigna al editor"""
    bl_idname = "cerdo_1_st.throw_detect_armature"
    bl_label  = "Detectar Armature"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
        if not arms:
            self.report({"WARNING"}, "No se encontró ningún armature")
            return {"CANCELLED"}
        th.edit_parent_armature = arms[0].name
        th.edit_target_armature = arms[0].name
        return {"FINISHED"}


# ── Cursor 3D ─────────────────────────────────────────────────────────────────

class CERDO_1_ST_OT_ThrowPickDestFromCursor(bpy.types.Operator):
    """Toma la posición del 3D Cursor como coordenada destino del editor"""
    bl_idname = "cerdo_1_st.throw_pick_dest_cursor"
    bl_label  = "Destino desde cursor 3D"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        cur = context.scene.cursor.location
        th.edit_dest_x = cur.x; th.edit_dest_y = cur.y; th.edit_dest_z = cur.z
        self.report({"INFO"}, f"Destino: ({cur.x:.3f}, {cur.y:.3f}, {cur.z:.3f})")
        return {"FINISHED"}


# ── Waypoints del editor ──────────────────────────────────────────────────────

class CERDO_1_ST_OT_ThrowAddWaypoint(bpy.types.Operator):
    """Agrega un waypoint al item activo"""
    bl_idname = "cerdo_1_st.throw_add_waypoint"
    bl_label  = "Agregar waypoint"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:     bpy.props.IntProperty(default=0)
    item_idx:    bpy.props.IntProperty(default=0)
    from_cursor: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        if self.item_idx < 0 or self.item_idx >= len(th.items): return {"CANCELLED"}
        wp = th.items[self.item_idx].waypoints.add()
        wp.label = f"Punto {len(th.items[self.item_idx].waypoints)}"
        if self.from_cursor:
            cur = context.scene.cursor.location
            wp.x, wp.y, wp.z = cur.x, cur.y, cur.z
        return {"FINISHED"}


class CERDO_1_ST_OT_ThrowRemoveWaypoint(bpy.types.Operator):
    """Elimina un waypoint del item activo"""
    bl_idname = "cerdo_1_st.throw_remove_waypoint"
    bl_label  = "Eliminar waypoint"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)
    wp_idx:   bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        if self.item_idx < 0 or self.item_idx >= len(th.items): return {"CANCELLED"}
        wps = th.items[self.item_idx].waypoints
        if 0 <= self.wp_idx < len(wps):
            wps.remove(self.wp_idx)
        return {"FINISHED"}


class CERDO_1_ST_OT_ThrowWaypointFromCursor(bpy.types.Operator):
    """Actualiza las coordenadas del waypoint con el cursor 3D"""
    bl_idname = "cerdo_1_st.throw_wp_from_cursor"
    bl_label  = "Desde cursor 3D"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)
    wp_idx:   bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        if self.item_idx < 0 or self.item_idx >= len(th.items): return {"CANCELLED"}
        wps = th.items[self.item_idx].waypoints
        if 0 <= self.wp_idx < len(wps):
            cur = context.scene.cursor.location
            wps[self.wp_idx].x, wps[self.wp_idx].y, wps[self.wp_idx].z = cur.x, cur.y, cur.z
        return {"FINISHED"}


# ── Aplicar trayectoria ───────────────────────────────────────────────────────

def apply_throw_item(item, context):
    """Aplica la trayectoria de un Cerdo_1ThrowItem."""
    import math, mathutils
    obj = bpy.data.objects.get(item.target_object)
    if obj is None:
        print(f"[THROW] ERROR: objeto '{item.target_object}' no encontrado")
        return False

    f0    = item.frame_start
    f_end = item.frame_end
    scene = context.scene
    frame_original = scene.frame_current

    scene.frame_set(f0)
    bpy.context.view_layer.update()
    bone_loc = _throw_get_bone_world_loc(item.target_armature, item.target_bone)
    dest = (item.dest_x, item.dest_y, item.dest_z)
    active_wps   = [wp for wp in item.waypoints if wp.enabled]
    total_frames = max(1, f_end - f0)

    if item.mode == 'THROW':
        cps = ([(f0, bone_loc[0], bone_loc[1], bone_loc[2], item.easing_global)]
               + [(None, wp.x, wp.y, wp.z, wp.easing) for wp in active_wps]
               + [(f_end, dest[0], dest[1], dest[2], item.easing_global)])
    else:
        cps = ([(f0, dest[0], dest[1], dest[2], item.easing_global)]
               + [(None, wp.x, wp.y, wp.z, wp.easing) for wp in reversed(active_wps)]
               + [(f_end, bone_loc[0], bone_loc[1], bone_loc[2], item.easing_global)])

    frame_step = total_frames / max(1, len(cps) - 1)
    for idx, pt in enumerate(cps):
        if pt[0] is None:
            cps[idx] = (int(f0 + idx * frame_step), pt[1], pt[2], pt[3], pt[4])

    world_mat = obj.matrix_world.copy()
    obj.parent = None; obj.parent_bone = ""; obj.parent_type = 'OBJECT'
    obj.matrix_world = world_mat
    bpy.context.view_layer.update()

    action = _throw_ensure_action(obj)
    # Limpiar cualquier keyframe de `location` que ya exista en el rango
    # [f0, f_end] ANTES de trazar la trayectoria real. Esto es lo que hace
    # seguro combinar item.transition_in/transition_out con THROW/CATCH:
    # esas transiciones (aplicadas antes, en el paso 1 de la CONCATENAR)
    # pueden haber insertado un keyframe de location de referencia (ej.
    # SLIDE_UP/SLIDE_DOWN/SCALE_BOUNCE) en espacio LOCAL/parentado, que
    # quedaría corrompiendo la trayectoria en espacio MUNDIAL de aca abajo.
    # Los keyframes de scale/rotation_euler/alpha de la transicion NO se
    # tocan -- solo se descarta la parte de location, que en THROW/CATCH no
    # tiene sentido de todas formas (la posicion la gobierna la trayectoria).
    for fc in list(get_fcurves(action)):
        if fc.data_path != "location":
            continue
        for kp_idx in reversed([i for i, kp in enumerate(fc.keyframe_points)
                                if f0 <= kp.co.x <= f_end]):
            fc.keyframe_points.remove(fc.keyframe_points[kp_idx])
    for (frame, x, y, z, easing) in cps:
        scene.frame_set(int(frame))
        obj.location = (x, y, z)
        obj.keyframe_insert(data_path="location", frame=int(frame))
    for (frame, x, y, z, easing) in cps[:-1]:
        _throw_set_kf_interp(action, "location", int(frame), easing)

    # FIX (Kebyn, "bloques/props plantados mirando en direcciones
    # distintas"): justo arriba, al desparentar, obj.matrix_world (y por
    # lo tanto obj.rotation_euler) quedo con la rotacion MUNDIAL que tenia
    # el bone de la mano exactamente en el frame f0 -- o sea, la
    # orientacion instantanea de la muneca en ese punto puntual del gesto
    # de agacharse/lanzar (agachar/colocar), que varia levemente ciclo a
    # ciclo por interpolacion/easing/IK. Eso es lo que hacia que cada
    # antorcha/mesa/bloque de pared quedara "plantada" con una inclinacion
    # distinta e impredecible en vez de quedar derecha y consistente. La
    # rotacion de REPOSO de un objeto que se queda plantado debe ser la
    # que configura el propio item (item.rot_x/rot_y/rot_z -- 0,0,0 por
    # defecto = "de pie, sin inclinar", o el heading de la pared/recorrido
    # si el auto-registro lo especifica), nunca la heredada del hueso que
    # lo sostuvo. Se limpian primero los keyframes de rotation_euler que
    # pudieran haber quedado del parenteo/transiciones previas, igual que
    # se hace arriba con location.
    for fc in list(get_fcurves(action)):
        if fc.data_path != "rotation_euler":
            continue
        for kp_idx in reversed([i for i, kp in enumerate(fc.keyframe_points)
                                if f0 <= kp.co.x <= f_end]):
            fc.keyframe_points.remove(fc.keyframe_points[kp_idx])
    scene.frame_set(f0)
    obj.rotation_euler = (item.rot_x, item.rot_y, item.rot_z)
    obj.keyframe_insert(data_path="rotation_euler", frame=f0)
    if f_end != f0:
        scene.frame_set(f_end)
        obj.rotation_euler = (item.rot_x, item.rot_y, item.rot_z)
        obj.keyframe_insert(data_path="rotation_euler", frame=f_end)

    if item.spin_during_flight:
        rz_s = item.rot_z
        rz_e = rz_s + math.radians(360.0 * item.spin_turns)
        if item.mode == 'CATCH': rz_s, rz_e = rz_e, rz_s
        scene.frame_set(f0);    obj.rotation_euler[2] = rz_s; obj.keyframe_insert(data_path="rotation_euler", frame=f0, index=2)
        scene.frame_set(f_end); obj.rotation_euler[2] = rz_e; obj.keyframe_insert(data_path="rotation_euler", frame=f_end, index=2)

    scene.frame_set(frame_original)
    bpy.context.view_layer.update()
    print(f"[THROW] OK '{item.target_object}' {f0}→{f_end}")
    return True


class CERDO_1_ST_OT_ThrowApply(bpy.types.Operator):
    """Aplica la trayectoria del lanzamiento seleccionado"""
    bl_idname = "cerdo_1_st.throw_apply"
    bl_label  = "Aplicar trayectoria"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        if self.item_idx < 0 or self.item_idx >= len(th.items):
            self.report({"ERROR"}, "Item inválido"); return {"CANCELLED"}
        item = th.items[self.item_idx]
        # Fallback: si target_object está vacío, intentar con object_name
        if not item.target_object:
            if item.object_name and bpy.data.objects.get(item.object_name):
                item.target_object        = item.object_name
                item.imported_object_name = item.object_name
            else:
                self.report({"ERROR"},
                    f"Objeto no encontrado. Importa el objeto primero ('{item.object_name}')")
                return {"CANCELLED"}
        # Verificar que el objeto exista en escena
        if not bpy.data.objects.get(item.target_object):
            if item.object_name and bpy.data.objects.get(item.object_name):
                item.target_object = item.object_name
            else:
                self.report({"ERROR"},
                    f"Objeto '{item.target_object}' no está en la escena. Reimporta el objeto.")
                return {"CANCELLED"}
        try:
            ok = apply_throw_item(item, context)
            if ok: self.report({"INFO"}, f"Trayectoria aplicada a '{item.target_object}'")
        except Exception as e:
            self.report({"ERROR"}, f"Error: {e}"); import traceback; traceback.print_exc()
            return {"CANCELLED"}
        return {"FINISHED"}


class CERDO_1_ST_OT_ThrowClearKeyframes(bpy.types.Operator):
    """Elimina los keyframes de trayectoria del item seleccionado"""
    bl_idname = "cerdo_1_st.throw_clear_keyframes"
    bl_label  = "Limpiar keyframes"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        th = _get_seg_throws(context, self.seg_idx)
        if th is None: return {"CANCELLED"}
        if self.item_idx < 0 or self.item_idx >= len(th.items): return {"CANCELLED"}
        item = th.items[self.item_idx]
        obj  = bpy.data.objects.get(item.target_object)
        if obj is None or obj.animation_data is None or obj.animation_data.action is None:
            self.report({"WARNING"}, "Sin animación para limpiar"); return {"CANCELLED"}
        f0, f1 = item.frame_start, item.frame_end
        removed = 0
        for fc in get_fcurves(obj.animation_data.action):
            if fc.data_path not in ('location', 'rotation_euler'): continue
            for i in reversed([j for j, kp in enumerate(fc.keyframe_points) if f0 <= kp.co.x <= f1]):
                fc.keyframe_points.remove(fc.keyframe_points[i]); removed += 1
        self.report({"INFO"}, f"Eliminados {removed} keyframes")
        return {"FINISHED"}


# =============================================================================
# SISTEMA DE INVISIBILIDAD DE MALLA
# =============================================================================
# Debajo del sistema de Lanzar / Recoger / Mantener Objetos (mismo criterio
# de organizacion que el resto del archivo: helpers -> CRUD de items ->
# ejecucion). Oculta cualquier malla del escenario (obj.hide_viewport +
# obj.hide_render) durante un intervalo [frame_start, frame_end] propio de
# cada item, dejandola visible fuera de ese rango.

def _new_hide_mesh_uid():
    """Genera un uid corto y estable para un Cerdo_1HideMeshItem nuevo."""
    import uuid
    return uuid.uuid4().hex[:12]


def _copy_edit_to_hide_item(hm, item):
    """Copia los campos edit_* de Cerdo_1HideMeshSettings al Cerdo_1HideMeshItem dado."""
    item.label       = hm.edit_label
    item.mesh_object = hm.edit_mesh_object
    item.frame_start = hm.edit_frame_start
    item.frame_end   = hm.edit_frame_end


def _copy_hide_item_to_edit(item, hm):
    """Copia un Cerdo_1HideMeshItem a los campos edit_* de Cerdo_1HideMeshSettings."""
    hm.edit_label       = item.label
    hm.edit_mesh_object = item.mesh_object
    hm.edit_frame_start = item.frame_start
    hm.edit_frame_end   = item.frame_end


def _get_seg_hide_mesh(context, seg_idx):
    segs = context.scene.cerdo_1_segs.segments
    if seg_idx < 0 or seg_idx >= len(segs):
        return None
    return segs[seg_idx].hide_mesh


def apply_hide_mesh_item(item, context):
    """
    Aplica el intervalo de invisibilidad de un Cerdo_1HideMeshItem: la malla
    queda visible antes de frame_start, invisible durante
    [frame_start, frame_end], y vuelve a ser visible a partir de frame_end.

    Retorna True si se pudo aplicar (la malla existe en la escena), False
    en caso contrario.
    """
    obj = bpy.data.objects.get(item.mesh_object)
    if obj is None:
        return False

    f_start = item.frame_start
    f_end   = item.frame_end
    if f_end <= f_start:
        f_end = f_start + 1

    # Un frame antes de f_start la malla sigue visible -- asegura que la
    # transicion a "invisible" en f_start sea un corte limpio y no arrastre
    # un keyframe de visibilidad anterior que pudiera quedar mas atras.
    f_before = max(0, f_start - 1)
    if f_before < f_start:
        _oiu_preview.set_visibility_keyframes(obj, f_before, visible=True)
    _oiu_preview.set_visibility_keyframes(obj, f_start, visible=False)
    _oiu_preview.set_visibility_keyframes(obj, f_end, visible=True)
    return True


def run_hide_mesh_for_segments(context, seg_range):
    """
    Ejecuta el sistema de Invisibilidad de Malla (seg.hide_mesh) para cada
    segmento en seg_range. Mismo criterio que run_throws_for_segments():
    se llama tanto desde CERDO_1_ST_OT_Concatenate.execute() (operators_anim.py)
    como desde CERDO_1SEG_OT_ConcatenateAll (operators_segments.py, rama de
    segmentos sin poses), para que un item configurado en cualquiera de los
    dos flujos de Concatenar siempre se aplique.

    Retorna (hide_applied, hide_errors).
    """
    _hide_applied = 0
    _hide_errors  = []
    for seg in seg_range:
        hm = seg.hide_mesh
        if not hm.enabled:
            continue
        print(f"[HIDE_MESH] Segmento '{seg.label}': {len(hm.items)} item(s) "
              f"de Invisibilidad de Malla (hide_mesh.enabled=True)")
        for item in hm.items:
            if not item.uid:
                item.uid = _new_hide_mesh_uid()
            if not item.enabled:
                print(f"[HIDE_MESH]   '{item.label}' -> SALTADO (item.enabled=False)")
                continue
            if not item.mesh_object:
                print(f"[HIDE_MESH]   '{item.label}' -> SALTADO (sin malla asignada)")
                continue
            try:
                if apply_hide_mesh_item(item, context):
                    _hide_applied += 1
                    print(f"[HIDE_MESH]   '{item.label}': '{item.mesh_object}' "
                          f"invisible en [{item.frame_start}, {item.frame_end}]")
                else:
                    _hide_errors.append(
                        f"Segmento '{seg.label}': malla '{item.mesh_object}' "
                        "no encontrada en la escena")
            except Exception as _e_hide:
                _hide_errors.append(
                    f"Segmento '{seg.label}': item '{item.label}' ({_e_hide})")
    return _hide_applied, _hide_errors


# ── CRUD de items ─────────────────────────────────────────────────────────────

class CERDO_1_ST_OT_HideMeshAddItem(bpy.types.Operator):
    """Agrega un nuevo intervalo de invisibilidad usando los valores del editor"""
    bl_idname = "cerdo_1_st.hide_mesh_add_item"
    bl_label  = "Agregar invisibilidad"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        hm = _get_seg_hide_mesh(context, self.seg_idx)
        if hm is None: return {"CANCELLED"}
        if not hm.edit_mesh_object:
            self.report({"WARNING"}, "Elegí una malla del escenario")
            return {"CANCELLED"}
        # Igual criterio que CERDO_1_ST_OT_ThrowAddItem: enabled se marca aca (el
        # operator), no en draw(), porque Blender 4.5 no permite escribir en
        # datablocks de la escena durante el dibujado del panel.
        hm.enabled = True
        item = hm.items.add()
        _copy_edit_to_hide_item(hm, item)
        item.segment_idx = self.seg_idx
        item.enabled = True
        item.uid = _new_hide_mesh_uid()
        hm.active_idx = len(hm.items) - 1
        self.report({"INFO"}, f"Invisibilidad '{item.label}' agregada")
        return {"FINISHED"}


class CERDO_1_ST_OT_HideMeshRemoveItem(bpy.types.Operator):
    """Elimina el intervalo de invisibilidad seleccionado"""
    bl_idname = "cerdo_1_st.hide_mesh_remove_item"
    bl_label  = "Eliminar invisibilidad"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        hm = _get_seg_hide_mesh(context, self.seg_idx)
        if hm is None: return {"CANCELLED"}
        if 0 <= self.item_idx < len(hm.items):
            hm.items.remove(self.item_idx)
            hm.active_idx = max(0, self.item_idx - 1)
        return {"FINISHED"}


class CERDO_1_ST_OT_HideMeshToggleItem(bpy.types.Operator):
    """Activa/desactiva el intervalo de invisibilidad"""
    bl_idname = "cerdo_1_st.hide_mesh_toggle_item"
    bl_label  = "Toggle invisibilidad"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        hm = _get_seg_hide_mesh(context, self.seg_idx)
        if hm is None: return {"CANCELLED"}
        if 0 <= self.item_idx < len(hm.items):
            hm.items[self.item_idx].enabled = not hm.items[self.item_idx].enabled
        return {"FINISHED"}


class CERDO_1_ST_OT_HideMeshLoadToEditor(bpy.types.Operator):
    """Carga el intervalo de invisibilidad seleccionado en el editor para modificarlo"""
    bl_idname = "cerdo_1_st.hide_mesh_load_to_editor"
    bl_label  = "Editar invisibilidad"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        hm = _get_seg_hide_mesh(context, self.seg_idx)
        if hm is None: return {"CANCELLED"}
        if 0 <= self.item_idx < len(hm.items):
            _copy_hide_item_to_edit(hm.items[self.item_idx], hm)
            hm.active_idx = self.item_idx
        return {"FINISHED"}


class CERDO_1_ST_OT_HideMeshUpdateItem(bpy.types.Operator):
    """Actualiza el intervalo de invisibilidad activo con los valores del editor"""
    bl_idname = "cerdo_1_st.hide_mesh_update_item"
    bl_label  = "Actualizar invisibilidad"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx:  bpy.props.IntProperty(default=0)
    item_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        hm = _get_seg_hide_mesh(context, self.seg_idx)
        if hm is None: return {"CANCELLED"}
        if 0 <= self.item_idx < len(hm.items):
            _copy_edit_to_hide_item(hm, hm.items[self.item_idx])
            self.report({"INFO"}, f"Invisibilidad {self.item_idx} actualizada")
        return {"FINISHED"}


class CERDO_1_ST_OT_HideMeshPickObject(bpy.types.Operator):
    """Asigna el objeto activo del viewport al campo Malla del editor"""
    bl_idname = "cerdo_1_st.hide_mesh_pick_object"
    bl_label  = "Elegir malla activa"
    bl_options = {"REGISTER", "UNDO"}
    seg_idx: bpy.props.IntProperty(default=0)

    def execute(self, context):
        hm = _get_seg_hide_mesh(context, self.seg_idx)
        if hm is None: return {"CANCELLED"}
        obj = context.active_object
        if obj is None:
            self.report({"WARNING"}, "No hay objeto activo en el viewport")
            return {"CANCELLED"}
        if obj.type != 'MESH':
            self.report({"WARNING"}, f"'{obj.name}' no es una malla")
            return {"CANCELLED"}
        hm.edit_mesh_object = obj.name
        return {"FINISHED"}
