# -*- coding: utf-8 -*-
"""
config_ops.py — Chicken 1 Animation Studio v1.8
Operadores de configuracion de sesion: SaveConfig, LoadConfig, OpenConfigFolder.
Serializacion/deserializacion completa incluyendo eye_expr y organic.
"""
import bpy, json, os
from datetime import datetime
from bpy.types import Operator
from bpy.props import StringProperty
from .pose_utils import open_folder
from .properties import load_historia_json, get_key_points

def _get_key_point_coordinates(st):
    """Lee las coordenadas reales del key_point seleccionado (root_pos_key_point)
    desde historia_chicken_1.json y las devuelve como dict para embeber en el JSON guardado.
    """
    try:
        historia = load_historia_json(st.historia_json)
        kps = get_key_points(historia)
        kp_idx = int(st.root_pos_key_point)
        kp = next((k for k in kps if k.get("index") == kp_idx), None)
        if kp:
            return {
                "index":      kp.get("index"),
                "coordinates": kp.get("coordinates", {"x": 0, "y": 0, "z": 0}),
                "texture":    kp.get("texture", ""),
                "face_index": kp.get("face_index", ""),
            }
    except Exception:
        pass
    return {}


def _serialize_configuracion(st):
    """
    Serializa toda la configuracion activa del trabajo (secuencia, poses,
    interpolaciones, posiciones, rotaciones, ajustes de timeline, etc.)
    en un diccionario listo para guardar como JSON.
    NO incluye keyframes de animacion acabada: eso es el .py exportado.
    """
    # Poses de accion
    action_poses_data = []
    for item in st.action_poses:
        action_poses_data.append({
            "pose_name":  item.pose_name,
            "json_file":  item.json_file,
            "pose_index": item.pose_index,
            "duration":   item.duration,
            "rot_x": item.rot_x,
            "rot_y": item.rot_y,
            "rot_z": item.rot_z,
            "pos_x": item.pos_x,
            "pos_y": item.pos_y,
            "pos_z": item.pos_z,
            "interp_type": item.interp_type,
            "manual_start":    bool(item.manual_start),
            "frame_abs_start": int(item.frame_abs_start),
        })

    # Filtros organicos
    org = st.organic
    organic_data = {
        "enabled":                   org.enabled,
        "breathing_enabled":         org.breathing_enabled,
        "breathing_amplitude":       org.breathing_amplitude,
        "breathing_speed":           org.breathing_speed,
        "breathing_phase":           org.breathing_phase,
        "flap_enabled":              org.flap_enabled,
        "flap_amplitude":            org.flap_amplitude,
        "flap_speed":                org.flap_speed,
        "flap_openness":             org.flap_openness,
        "flap_asymmetry":            org.flap_asymmetry,
        "head_sway_enabled":         org.head_sway_enabled,
        "head_sway_amplitude":       org.head_sway_amplitude,
        "head_sway_speed":           org.head_sway_speed,
        "head_sway_seed":            org.head_sway_seed,
        "weight_shift_enabled":      org.weight_shift_enabled,
        "weight_shift_amplitude":    org.weight_shift_amplitude,
        "weight_shift_speed":        org.weight_shift_speed,
        "root_noise_enabled":        org.root_noise_enabled,
        "root_noise_strength":       org.root_noise_strength,
        "root_noise_frequency":      org.root_noise_frequency,
        "root_noise_seed":           org.root_noise_seed,
        "secondary_motion_enabled":  org.secondary_motion_enabled,
        "secondary_motion_lag":      org.secondary_motion_lag,
        "secondary_motion_damping":  org.secondary_motion_damping,
        "smooth_curves_enabled":     org.smooth_curves_enabled,
        "smooth_passes":             org.smooth_passes,
        "smooth_factor":             org.smooth_factor,
        "micro_scale_enabled":       org.micro_scale_enabled,
        "micro_scale_amplitude":     org.micro_scale_amplitude,
        "shoulder_noise_enabled":    org.shoulder_noise_enabled,
        "shoulder_noise_amplitude":  org.shoulder_noise_amplitude,
        "shoulder_noise_speed":      org.shoulder_noise_speed,
        "shoulder_noise_seed":       org.shoulder_noise_seed,
    }

    # Expresiones de ojos
    eye_s = st.eye_expr
    eye_data = {
        "enabled":              eye_s.enabled,
        "intensity_feliz":      eye_s.intensity_feliz,
        "intensity_triste":     eye_s.intensity_triste,
        "intensity_enojado":    eye_s.intensity_enojado,
        "intensity_sospecha":   eye_s.intensity_sospecha,
        "curve_mode":           eye_s.curve_mode,
        "affect_zone":          eye_s.affect_zone,
        "swap_axes":            eye_s.swap_axes,
        "invert_vertical":      eye_s.invert_vertical,
        "invert_horizontal":    eye_s.invert_horizontal,
        "subdivide_cuts":       eye_s.subdivide_cuts,
        "active_expression":    eye_s.active_expression,
        "expression_value":     eye_s.expression_value,
        "blink_enabled":        eye_s.blink_enabled,
        "blink_count":          eye_s.blink_count,
        "blink_duration":       eye_s.blink_duration,
    }

    # ── Paso 1 y 2: ch1_path (recorrido, personaje, slots, frames) ──
    paso1_data = {}
    try:
        pc = bpy.context.scene.ch1_path
        path_points_data = []
        for pt in pc.path_points:
            path_points_data.append({
                "coords":              list(pt.coords),
                "texture":             pt.texture,
                "face_index":          pt.face_index,
                # NUEVO (port Paso 1 de Alfred, 2026-08-10): tipo de
                # segmento editable por punto ("AUTO"/"PARADA") y frames
                # que dura esa parada especifica -- ver CH1PathPoint en
                # path_recorder.py.
                "tipo_segmento":       pt.tipo_segmento,
                "parada_frames_punto": pt.parada_frames_punto,
            })
        paso1_data = {
            "blend_filepath":    bpy.path.abspath(pc.blend_filepath) if pc.blend_filepath else "",
            "slot_inicio":       pc.slot_inicio,
            "frame_inicio":      pc.frame_inicio,
            "frame_fin_manual":  pc.frame_fin_manual,
            "frames_por_bloque": pc.frames_por_bloque,
            # NUEVO (port Paso 1 de Alfred): duracion por defecto de una
            # parada sin sincronizar todavia, y las duraciones reales
            # (una por cada parada detectada, ver CH1ParadaFrames /
            # sync_paradas_frames en path_recorder.py).
            "frames_parada":     pc.frames_parada,
            "paradas_frames":    [pf.frames for pf in pc.paradas_frames],
            # NUEVO (port Paso 1 de Alfred): estilo de caminata por cada
            # tramo 'caminar' detectado (ver CH1WalkStyleEntry /
            # sync_walk_styles en path_recorder.py).
            "walk_styles":       [
                {"style": ws.style, "applied_style": ws.applied_style}
                for ws in pc.walk_styles
            ],
            "root_rot_x":        pc.root_rot_x,
            "root_rot_y":        pc.root_rot_y,
            "root_rot_z":        pc.root_rot_z,
            "output_dir":        bpy.path.abspath(pc.output_dir) if pc.output_dir else "",
            "path_points":       path_points_data,
        }
    except Exception as e:
        print(f"[Alfred] advertencia: no se pudo serializar ch1_path: {e}")

    return {
        "version": "1.9",
        "timestamp": datetime.now().isoformat(),
        "description": "Configuracion de trabajo Chicken 1 Animation Studio",
        # ── Paso 1 y 2 (ch1_path) ──
        "paso1_path": paso1_data,
        # ── Rutas ──
        "poses_dir":    bpy.path.abspath(st.poses_dir),
        "anim_dir":     bpy.path.abspath(st.anim_dir),
        "historia_json": bpy.path.abspath(st.historia_json),
        "config_dir":   bpy.path.abspath(st.config_dir),
        # ── Armature ──
        "armature_name": st.armature_name,
        # ── Timeline ──
        "start_frame": st.start_frame,
        "fps":         st.fps,
        "entry_ratio": st.entry_ratio,
        "exit_ratio":  st.exit_ratio,
        # ── Pose INICIO ──
        # ── Poses de accion ──
        "action_poses": action_poses_data,
        # ── Pose FIN ──
        # ── Exportacion ──
        "export_slot_number": st.export_slot_number,
        "export_name":        st.export_name,
        "export_type":        st.export_type,
        "export_desc":        st.export_desc,
        "selected_key_point": st.selected_key_point,
        "root_pos_key_point": st.root_pos_key_point,
        "key_point_coordinates": _get_key_point_coordinates(st),
        # ── Filtros organicos ──
        "organic": organic_data,
        # ── Expresiones de ojos (legacy) ──
        "eye_expr": eye_data,
        # ── Secuencia de ojos completa (inicio/intermedios/fin + parpadeo) ──
        "eye_sequence": _serialize_eye_config(st),
        # ── Oscilaciones de bones personalizadas ──
        "bone_oscillations": _serialize_bone_oscillations(st),
        # ── Importacion de Objetos (escudo, espada, etc.) ──
        "object_imports": _serialize_object_imports(st),
        # ── Segmentos del Paso 3 (frames, poses, filtros, throws incluidos) ──
        "ch1_segs": _serialize_ch1_segs(st),
        # ── Lanzar / Recoger Objetos (por segmento) — mantenido por compatibilidad ──
        "segments_throw": _serialize_throw_settings(st),
    }


def _aplicar_configuracion(st, data):
    """
    Aplica el diccionario deserializado del JSON de configuracion
    sobre el Chicken1StudioSettings activo.
    Omite silenciosamente claves que no existan (compatibilidad hacia atras).
    """
    def _get(d, *keys, default=None):
        cur = d
        for k in keys:
            if not isinstance(cur, dict):
                return default
            cur = cur.get(k, default)
        return cur

    # ── Paso 1 y 2: ch1_path (recorrido, personaje, slots, frames) ──
    paso1_data = data.get("paso1_path", {})
    if paso1_data:
        try:
            import bpy as _bpy
            pc = _bpy.context.scene.ch1_path

            if paso1_data.get("blend_filepath"):
                pc.blend_filepath    = paso1_data["blend_filepath"]
            if "slot_inicio"       in paso1_data: pc.slot_inicio       = paso1_data["slot_inicio"]
            if "frame_inicio"      in paso1_data: pc.frame_inicio      = paso1_data["frame_inicio"]
            if "frame_fin_manual"  in paso1_data: pc.frame_fin_manual  = paso1_data["frame_fin_manual"]
            if "frames_por_bloque" in paso1_data: pc.frames_por_bloque = paso1_data["frames_por_bloque"]
            if "frames_parada"     in paso1_data: pc.frames_parada     = paso1_data["frames_parada"]
            if "root_rot_x"        in paso1_data: pc.root_rot_x        = paso1_data["root_rot_x"]
            if "root_rot_y"        in paso1_data: pc.root_rot_y        = paso1_data["root_rot_y"]
            if "root_rot_z"        in paso1_data: pc.root_rot_z        = paso1_data["root_rot_z"]
            if paso1_data.get("output_dir"):
                pc.output_dir = paso1_data["output_dir"]

            # Restaurar puntos del recorrido
            pts_data = paso1_data.get("path_points", [])
            if pts_data:
                pc.path_points.clear()
                for ptd in pts_data:
                    pt            = pc.path_points.add()
                    pt.coords     = tuple(ptd.get("coords", [0.0, 0.0, 0.0]))
                    pt.texture    = ptd.get("texture", "")
                    pt.face_index = ptd.get("face_index", "")
                    # NUEVO (port Paso 1 de Alfred, 2026-08-10)
                    pt.tipo_segmento       = ptd.get("tipo_segmento", "AUTO")
                    pt.parada_frames_punto = ptd.get("parada_frames_punto", 24)

            # NUEVO (port Paso 1 de Alfred): restaurar duraciones de
            # paradas y estilos de caminata por tramo. Se restauran
            # DESPUES de los path_points para que _expand_points_with_
            # paradas()/_group_segments() ya vean el recorrido completo
            # si algun operador dispara un sync automatico mientras carga.
            paradas_frames_data = paso1_data.get("paradas_frames", [])
            if paradas_frames_data:
                pc.paradas_frames.clear()
                for f in paradas_frames_data:
                    item = pc.paradas_frames.add()
                    item.frames = f

            walk_styles_data = paso1_data.get("walk_styles", [])
            if walk_styles_data:
                pc.walk_styles.clear()
                for wsd in walk_styles_data:
                    item = pc.walk_styles.add()
                    item.style          = wsd.get("style", "NORMAL")
                    item.applied_style  = wsd.get("applied_style", "")
        except Exception as e:
            print(f"[Alfred] advertencia: no se pudo restaurar ch1_path: {e}")

    # Rutas (solo si el usuario quiere recuperarlas; no sobreescribir si estan vacias)
    if _get(data, "poses_dir"):
        st.poses_dir     = data["poses_dir"]
    if _get(data, "anim_dir"):
        st.anim_dir      = data["anim_dir"]
    if _get(data, "historia_json"):
        st.historia_json = data["historia_json"]
    if _get(data, "config_dir"):
        st.config_dir    = data["config_dir"]

    # Armature
    if _get(data, "armature_name"):
        st.armature_name = data["armature_name"]

    # Timeline
    if "start_frame" in data: st.start_frame = data["start_frame"]
    if "fps"         in data: st.fps         = data["fps"]
    if "entry_ratio" in data: st.entry_ratio = data["entry_ratio"]
    if "exit_ratio"  in data: st.exit_ratio  = data["exit_ratio"]

    # Poses de accion
    st.action_poses.clear()
    for ap in data.get("action_poses", []):
        item             = st.action_poses.add()
        item.pose_name   = ap.get("pose_name",  "")
        item.json_file   = ap.get("json_file",  "")
        item.pose_index  = ap.get("pose_index", 0)
        item.duration    = ap.get("duration",   20)
        item.rot_x       = ap.get("rot_x",      0.0)
        item.rot_y       = ap.get("rot_y",      0.0)
        item.rot_z       = ap.get("rot_z",      0.0)
        item.pos_x       = ap.get("pos_x",      0.0)
        item.pos_y       = ap.get("pos_y",      0.0)
        item.pos_z       = ap.get("pos_z",      0.0)
        item.interp_type = ap.get("interp_type","SMOOTH")
        item.manual_start    = bool(ap.get("manual_start", False))
        item.frame_abs_start = int(ap.get("frame_abs_start", 0))

    # Exportacion
    if "export_slot_number" in data: st.export_slot_number = data["export_slot_number"]
    if "export_name"        in data: st.export_name        = data["export_name"]
    if "export_type"        in data: st.export_type        = data["export_type"]
    if "export_desc"        in data: st.export_desc        = data["export_desc"]
    if "selected_key_point" in data: st.selected_key_point = data["selected_key_point"]
    if "root_pos_key_point" in data:
        try:
            st.root_pos_key_point = str(data["root_pos_key_point"])
        except Exception:
            pass

    # Filtros organicos
    org_data = data.get("organic", {})
    if org_data:
        org = st.organic
        for key, val in org_data.items():
            try:
                setattr(org, key, val)
            except Exception:
                pass

    # Expresiones de ojos (legacy)
    eye_data_load = data.get("eye_expr", {})
    if eye_data_load:
        eye_s = st.eye_expr
        for key, val in eye_data_load.items():
            try:
                setattr(eye_s, key, val)
            except Exception:
                pass

    # Secuencia de ojos completa (inicio/intermedios/fin + parpadeo)
    eye_seq = data.get("eye_sequence", {})
    if eye_seq:
        # _aplicar_eye_config ya recrea shape keys internamente si hay shape_keys_setup
        _aplicar_eye_config(st, eye_seq)

        # Ejecutar CONCATENAR_2 automaticamente para insertar los keyframes de ojos
        # (equivalente al flujo manual: Crear Shape Keys → CONCATENAR_2)
        try:
            result = bpy.ops.ch1st.concatenate_2()
            if result == {"FINISHED"}:
                print("[Alfred] CONCATENAR_2 ejecutado automaticamente al importar configuracion")
            else:
                print("[Alfred] ADVERTENCIA: CONCATENAR_2 no pudo ejecutarse automaticamente — ejecutalo manualmente")
        except Exception as e:
            print(f"[Alfred] No se pudo ejecutar CONCATENAR_2 automaticamente: {e}")

    # ── Oscilaciones de bones ──────────────────────────────────────────────
    bone_osc_data = data.get("bone_oscillations", {})
    if bone_osc_data:
        _aplicar_bone_oscillations(st, bone_osc_data)

    # ── Importacion de Objetos (escudo, espada, etc.) ───────────────────────
    obj_imports_data = data.get("object_imports", {})
    if obj_imports_data:
        _aplicar_object_imports(st, obj_imports_data)

    # ── Segmentos del Paso 3 (frames, poses, filtros, throws incluidos) ──────
    # Primero intentar con la clave nueva "ch1_segs" (version >= 2.0).
    # Si no existe, caer en la clave legacy "segments_throw" para JSONs antiguos.
    segs_data = data.get("ch1_segs", [])
    if segs_data:
        try:
            _aplicar_ch1_segs(st, segs_data)
        except Exception as _e_segs:
            print(f"[Alfred] advertencia ch1_segs: {_e_segs}")
            import traceback; traceback.print_exc()
    else:
        # Compatibilidad con JSONs viejos: solo restaurar los throws
        throw_data = data.get("segments_throw", [])
        if throw_data:
            try:
                _aplicar_throw_settings(st, throw_data)
            except Exception as _e_throw:
                print(f"[Alfred] advertencia throw_settings (legacy): {_e_throw}")


def _serialize_ch1_segs(st):
    """
    Serializa todos los segmentos del Paso 3 (ch1_segs.segments),
    incluyendo poses, filtros de bones y throws (Lanzar/Recoger).
    """
    result = []
    try:
        scene = st.id_data
        segs  = scene.ch1_segs.segments
    except Exception:
        return result

    for seg in segs:
        # Slots de accion del segmento
        action_poses_data = []
        for ap in seg.action_poses:
            action_poses_data.append({
                "json_file":   ap.json_file,
                "pose_label":  ap.pose_label,
                "pose_name":   ap.pose_name,
                "pose_index":  ap.pose_index,
                "duration":    ap.duration,
                "entry_ratio": round(ap.entry_ratio, 3),
                "exit_ratio":  round(ap.exit_ratio, 3),
                "interp_type": ap.interp_type,
                "rot_x": round(ap.rot_x, 4), "rot_y": round(ap.rot_y, 4), "rot_z": round(ap.rot_z, 4),
                "pos_x": round(ap.pos_x, 4), "pos_y": round(ap.pos_y, 4), "pos_z": round(ap.pos_z, 4),
                "manual_start":    bool(ap.manual_start),
                "frame_abs_start": int(ap.frame_abs_start),
            })

        # Throws del segmento
        th = seg.throws
        throw_items = []
        for item in th.items:
            wps = [{"label": wp.label, "x": round(wp.x,4), "y": round(wp.y,4),
                    "z": round(wp.z,4), "easing": wp.easing, "enabled": wp.enabled}
                   for wp in item.waypoints]
            throw_items.append({
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
                "loc_x": round(item.loc_x,4), "loc_y": round(item.loc_y,4), "loc_z": round(item.loc_z,4),
                "rot_x": round(item.rot_x,4), "rot_y": round(item.rot_y,4), "rot_z": round(item.rot_z,4),
                "scale_uniform":      round(item.scale_uniform, 3),
                "target_object":      item.target_object,
                "target_armature":    item.target_armature,
                "target_bone":        item.target_bone,
                "dest_x": round(item.dest_x,4), "dest_y": round(item.dest_y,4), "dest_z": round(item.dest_z,4),
                "easing_global":      item.easing_global,
                "spin_during_flight": item.spin_during_flight,
                "spin_turns":         round(item.spin_turns, 2),
                "waypoints":          wps,
            })

        result.append({
            "label":       seg.label,
            "frame_start": seg.frame_start,
            "frame_end":   seg.frame_end,
            "single_coord_mode": seg.single_coord_mode,
            "enabled":     seg.enabled,
            "seg_action_name": seg.seg_action_name,
            # Pose inicio
            # Pose fin
            # Slots intermedios
            "action_poses": action_poses_data,
            # Config
            "fps":         seg.fps,
            "entry_ratio": round(seg.entry_ratio, 3),
            "exit_ratio":  round(seg.exit_ratio, 3),
            "export_slot_number": seg.export_slot_number,
            "export_type":        seg.export_type,
            "export_desc":        seg.export_desc,
            "blend_in_frames":    seg.blend_in_frames,
            "blend_out_frames":   seg.blend_out_frames,
            # Grupos afectados
            "affect_body":      seg.affect_body,
            "affect_left_arm":  seg.affect_left_arm,
            "affect_right_arm": seg.affect_right_arm,
            "affect_left_leg":  seg.affect_left_leg,
            "affect_right_leg": seg.affect_right_leg,
            "affect_root":      seg.affect_root,
            "affect_shield":    seg.affect_shield,
            "affect_spear":     seg.affect_spear,
            # Filtros de bones
            "filter_show":         seg.filter_show,
            "filter_main_bone":    seg.filter_main_bone,
            "filter_hips":         seg.filter_hips,
            "filter_body":         seg.filter_body,
            "filter_spine":        seg.filter_spine,
            "filter_spine1":       seg.filter_spine1,
            "filter_spine2":       seg.filter_spine2,
            "filter_neck":         seg.filter_neck,
            "filter_face":         seg.filter_face,
            "filter_jaw_top":      seg.filter_jaw_top,
            "filter_jaw_bot":      seg.filter_jaw_bot,
            "filter_right_arm":      seg.filter_right_arm,
            "filter_right_shoulder": seg.filter_right_shoulder,
            "filter_right_elbow":    seg.filter_right_elbow,
            "filter_left_arm":       seg.filter_left_arm,
            "filter_left_shoulder":  seg.filter_left_shoulder,
            "filter_left_elbow":     seg.filter_left_elbow,
            "filter_right_leg":    seg.filter_right_leg,
            "filter_right_knee":   seg.filter_right_knee,
            "filter_right_ankle":  seg.filter_right_ankle,
            "filter_left_leg":     seg.filter_left_leg,
            "filter_left_knee":    seg.filter_left_knee,
            "filter_left_ankle":   seg.filter_left_ankle,
            "filter_knee_pole_r":  seg.filter_knee_pole_r,
            "filter_knee_pole_l":  seg.filter_knee_pole_l,
            "filter_no_bone_01":   seg.filter_no_bone_01,
            "filter_no_bone_02":   seg.filter_no_bone_02,
            "filter_no_bone_03":   seg.filter_no_bone_03,
            "filter_no_bone_04":   seg.filter_no_bone_04,
            "filter_no_bone_05":   seg.filter_no_bone_05,
            "filter_no_bone_06":   seg.filter_no_bone_06,
            # Throws (Lanzar/Recoger)
            "throws_enabled": th.enabled,
            "throws_items":   throw_items,
        })
    return result


def _aplicar_ch1_segs(st, data_list):
    """
    Restaura los segmentos del Paso 3 desde la lista serializada.
    Crea los segmentos desde cero (limpia los existentes) y aplica
    todas sus propiedades incluyendo los throws.
    """
    try:
        scene = st.id_data
        segs  = scene.ch1_segs
    except Exception as e:
        print(f"[SEGS_IMPORT] ERROR accediendo ch1_segs: {e}")
        return

    segs.segments.clear()

    for seg_data in data_list:
        seg = segs.segments.add()
        seg.label            = seg_data.get("label", "Segmento")
        seg.frame_start      = int(seg_data.get("frame_start", 1))
        seg.frame_end        = int(seg_data.get("frame_end", 48))
        seg.single_coord_mode = bool(seg_data.get("single_coord_mode", False))
        seg.enabled          = bool(seg_data.get("enabled", True))
        seg.seg_action_name  = seg_data.get("seg_action_name", "")
        # Slots intermedios
        seg.action_poses.clear()
        for ap_data in seg_data.get("action_poses", []):
            ap = seg.action_poses.add()
            ap.json_file   = ap_data.get("json_file", "")
            ap.pose_label  = ap_data.get("pose_label", "")
            ap.pose_name   = ap_data.get("pose_name", "")
            ap.pose_index  = int(ap_data.get("pose_index", 0))
            ap.duration    = int(ap_data.get("duration", 24))
            ap.entry_ratio = float(ap_data.get("entry_ratio", 0.3))
            ap.exit_ratio  = float(ap_data.get("exit_ratio", 0.3))
            try: ap.interp_type = ap_data.get("interp_type", "SMOOTH")
            except Exception: pass
            ap.rot_x = float(ap_data.get("rot_x", 0.0))
            ap.rot_y = float(ap_data.get("rot_y", 0.0))
            ap.rot_z = float(ap_data.get("rot_z", 0.0))
            ap.pos_x = float(ap_data.get("pos_x", 0.0))
            ap.pos_y = float(ap_data.get("pos_y", 0.0))
            ap.pos_z = float(ap_data.get("pos_z", 0.0))
            ap.manual_start    = bool(ap_data.get("manual_start", False))
            ap.frame_abs_start = int(ap_data.get("frame_abs_start", 0))
        # Config
        seg.fps            = int(seg_data.get("fps", 24))
        seg.entry_ratio    = float(seg_data.get("entry_ratio", 0.3))
        seg.exit_ratio     = float(seg_data.get("exit_ratio", 0.3))
        seg.export_slot_number = int(seg_data.get("export_slot_number", 1))
        seg.export_type    = seg_data.get("export_type", "idle")
        seg.export_desc    = seg_data.get("export_desc", "")
        seg.blend_in_frames  = int(seg_data.get("blend_in_frames", 8))
        seg.blend_out_frames = int(seg_data.get("blend_out_frames", 8))
        # Grupos afectados
        seg.affect_body      = bool(seg_data.get("affect_body", True))
        seg.affect_left_arm  = bool(seg_data.get("affect_left_arm", True))
        seg.affect_right_arm = bool(seg_data.get("affect_right_arm", True))
        seg.affect_left_leg  = bool(seg_data.get("affect_left_leg", True))
        seg.affect_right_leg = bool(seg_data.get("affect_right_leg", True))
        seg.affect_root      = bool(seg_data.get("affect_root", False))
        seg.affect_shield    = bool(seg_data.get("affect_shield", False))
        seg.affect_spear     = bool(seg_data.get("affect_spear", False))
        # Filtros de bones
        seg.filter_show        = bool(seg_data.get("filter_show", False))
        seg.filter_main_bone   = bool(seg_data.get("filter_main_bone", False))
        seg.filter_hips        = bool(seg_data.get("filter_hips", False))
        seg.filter_body        = bool(seg_data.get("filter_body", False))
        seg.filter_spine       = bool(seg_data.get("filter_spine", False))
        seg.filter_spine1      = bool(seg_data.get("filter_spine1", False))
        seg.filter_spine2      = bool(seg_data.get("filter_spine2", False))
        seg.filter_neck        = bool(seg_data.get("filter_neck", False))
        seg.filter_face        = bool(seg_data.get("filter_face", False))
        seg.filter_jaw_top     = bool(seg_data.get("filter_jaw_top", False))
        seg.filter_jaw_bot     = bool(seg_data.get("filter_jaw_bot", False))
        seg.filter_right_arm      = bool(seg_data.get("filter_right_arm", False))
        seg.filter_right_shoulder = bool(seg_data.get("filter_right_shoulder", False))
        seg.filter_right_elbow    = bool(seg_data.get("filter_right_elbow", False))
        seg.filter_left_arm       = bool(seg_data.get("filter_left_arm", False))
        seg.filter_left_shoulder  = bool(seg_data.get("filter_left_shoulder", False))
        seg.filter_left_elbow     = bool(seg_data.get("filter_left_elbow", False))
        seg.filter_right_leg   = bool(seg_data.get("filter_right_leg", True))
        seg.filter_right_knee  = bool(seg_data.get("filter_right_knee", True))
        seg.filter_right_ankle = bool(seg_data.get("filter_right_ankle", True))
        seg.filter_left_leg    = bool(seg_data.get("filter_left_leg", True))
        seg.filter_left_knee   = bool(seg_data.get("filter_left_knee", True))
        seg.filter_left_ankle  = bool(seg_data.get("filter_left_ankle", True))
        seg.filter_knee_pole_r = bool(seg_data.get("filter_knee_pole_r", False))
        seg.filter_knee_pole_l = bool(seg_data.get("filter_knee_pole_l", False))
        seg.filter_no_bone_01  = bool(seg_data.get("filter_no_bone_01", False))
        seg.filter_no_bone_02  = bool(seg_data.get("filter_no_bone_02", False))
        seg.filter_no_bone_03  = bool(seg_data.get("filter_no_bone_03", False))
        seg.filter_no_bone_04  = bool(seg_data.get("filter_no_bone_04", False))
        seg.filter_no_bone_05  = bool(seg_data.get("filter_no_bone_05", False))
        seg.filter_no_bone_06  = bool(seg_data.get("filter_no_bone_06", False))
        # Throws (Lanzar/Recoger)
        th = seg.throws
        th.enabled = bool(seg_data.get("throws_enabled", False))
        th.items.clear()
        for item_data in seg_data.get("throws_items", []):
            item = th.items.add()
            item.enabled            = bool(item_data.get("enabled", True))
            item.label              = str(item_data.get("label", "Lanzamiento"))
            item.mode               = str(item_data.get("mode", "THROW"))
            item.blend_path         = str(item_data.get("blend_path", ""))
            item.object_folder      = str(item_data.get("object_folder", ""))
            item.blend_filename     = str(item_data.get("blend_filename", ""))
            item.object_name        = str(item_data.get("object_name", ""))
            item.levels_up          = int(item_data.get("levels_up", 4))
            item.frame_start        = int(item_data.get("frame_start", 1))
            item.frame_end          = int(item_data.get("frame_end", 30))
            item.parent_armature    = str(item_data.get("parent_armature", "Armature"))
            item.parent_bone        = str(item_data.get("parent_bone", ""))
            item.loc_x              = float(item_data.get("loc_x", 0.0))
            item.loc_y              = float(item_data.get("loc_y", 0.0))
            item.loc_z              = float(item_data.get("loc_z", 0.0))
            item.rot_x              = float(item_data.get("rot_x", 0.0))
            item.rot_y              = float(item_data.get("rot_y", 0.0))
            item.rot_z              = float(item_data.get("rot_z", 0.0))
            item.scale_uniform      = float(item_data.get("scale_uniform", 1.0))
            item.target_object      = str(item_data.get("target_object", ""))
            item.target_armature    = str(item_data.get("target_armature", "Armature"))
            item.target_bone        = str(item_data.get("target_bone", ""))
            item.dest_x             = float(item_data.get("dest_x", 0.0))
            item.dest_y             = float(item_data.get("dest_y", 3.0))
            item.dest_z             = float(item_data.get("dest_z", 0.0))
            item.easing_global      = str(item_data.get("easing_global", "SMOOTH"))
            item.spin_during_flight = bool(item_data.get("spin_during_flight", False))
            item.spin_turns         = float(item_data.get("spin_turns", 1.0))
            item.imported_object_name = ""
            item.waypoints.clear()
            for wp_data in item_data.get("waypoints", []):
                wp         = item.waypoints.add()
                wp.label   = str(wp_data.get("label", "Punto"))
                wp.x       = float(wp_data.get("x", 0.0))
                wp.y       = float(wp_data.get("y", 0.0))
                wp.z       = float(wp_data.get("z", 2.0))
                wp.easing  = str(wp_data.get("easing", "SMOOTH"))
                wp.enabled = bool(wp_data.get("enabled", True))
        print(f"[SEGS_IMPORT] seg '{seg.label}' [{seg.frame_start}→{seg.frame_end}] "
              f"{len(th.items)} throw(s)")


def _serialize_bone_oscillations(st):
    """Serializa la config completa de bone_oscillations para el JSON."""
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
    return {
        "enabled": osc.enabled,
        "items":   items_list,
    }


def _aplicar_bone_oscillations(st, data):
    """Restaura la config de bone_oscillations desde un dict deserializado."""
    osc = st.bone_oscillations
    osc.enabled = bool(data.get("enabled", False))
    osc.items.clear()
    for item_data in data.get("items", []):
        item = osc.items.add()
        item.label        = item_data.get("label", "")
        item.bone_name    = item_data.get("bone_name", "")
        item.frame_start  = int(item_data.get("frame_start", 1))
        item.frame_end    = int(item_data.get("frame_end", 60))
        _legacy = item_data.get("axis", "")
        item.axis_x       = bool(item_data.get("axis_x", _legacy == "X"))
        item.axis_y       = bool(item_data.get("axis_y", _legacy == "Y"))
        item.axis_z       = bool(item_data.get("axis_z", _legacy == "Z" or not _legacy))
        item.amplitude    = float(item_data.get("amplitude", 30.0))
        item.angle_offset = float(item_data.get("angle_offset", 0.0))
        item.num_cycles   = int(item_data.get("num_cycles", 4))
        item.phase        = float(item_data.get("phase", 0.0))
        item.wave_type    = item_data.get("wave_type", "SINE")
        item.fade_in      = int(item_data.get("fade_in", 6))
        item.fade_out     = int(item_data.get("fade_out", 6))
        item.noise_seed   = int(item_data.get("noise_seed", 42))
        item.enabled      = bool(item_data.get("enabled", True))


def _serialize_object_imports(st):
    """Serializa la config completa de Importacion de Objetos (escudo, espada, etc.) para el JSON."""
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
        # ── Editor de nuevo objeto (para continuar editando donde se dejo) ──
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
    """Restaura la config de Importacion de Objetos desde un dict deserializado."""
    oi = st.object_imports
    oi.enabled = bool(data.get("enabled", False))
    oi.items.clear()
    for item_data in data.get("items", []):
        item = oi.items.add()
        item.label                = item_data.get("label", "Objeto")
        item.object_folder        = item_data.get("object_folder", "shield")
        item.blend_filename       = item_data.get("blend_filename", "shield.blend")
        item.object_name          = item_data.get("object_name", "shield")
        item.frame_start          = int(item_data.get("frame_start", 1))
        item.frame_end            = int(item_data.get("frame_end", 60))
        item.parent_armature      = item_data.get("parent_armature", "Armature")
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
        t_in = item_data.get("transition_in", "NONE")
        if hasattr(item, "transition_in"):
            item.transition_in = t_in if t_in else "NONE"
        t_in_dur = item_data.get("transition_in_duration", 8)
        if hasattr(item, "transition_in_duration"):
            item.transition_in_duration = int(t_in_dur)
        t_out = item_data.get("transition_out", "NONE")
        if hasattr(item, "transition_out"):
            item.transition_out = t_out if t_out else "NONE"
        t_out_dur = item_data.get("transition_out_duration", 8)
        if hasattr(item, "transition_out_duration"):
            item.transition_out_duration = int(t_out_dur)
        # imported_object_name NO se restaura: el objeto de una sesion anterior
        # ya no existe en esta escena. Se reimportara limpio en el proximo CONCATENAR.
        item.imported_object_name = ""

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
        oi.edit_loc_x           = float(editor.get("edit_loc_x",           oi.edit_loc_x))
        oi.edit_loc_y           = float(editor.get("edit_loc_y",           oi.edit_loc_y))
        oi.edit_loc_z           = float(editor.get("edit_loc_z",           oi.edit_loc_z))
        oi.edit_rot_x           = float(editor.get("edit_rot_x",           oi.edit_rot_x))
        oi.edit_rot_y           = float(editor.get("edit_rot_y",           oi.edit_rot_y))
        oi.edit_rot_z           = float(editor.get("edit_rot_z",           oi.edit_rot_z))
        oi.edit_scale_uniform   = float(editor.get("edit_scale_uniform",   oi.edit_scale_uniform))
        oi.edit_levels_up       = int(editor.get("edit_levels_up",   oi.edit_levels_up))
        oi.edit_segment_idx     = int(editor.get("edit_segment_idx", oi.edit_segment_idx))




def _serialize_throw_settings(st):
    """Serializa los throws de TODOS los segmentos. Un entry por item de cada segmento."""
    result = []
    try:
        scene = st.id_data
        segs  = scene.ch1_segs.segments
    except Exception:
        return result

    for seg_idx, seg in enumerate(segs):
        th = seg.throws
        for item_idx, item in enumerate(th.items):
            wps = [{"label": wp.label, "x": round(wp.x,4), "y": round(wp.y,4),
                    "z": round(wp.z,4), "easing": wp.easing, "enabled": wp.enabled}
                   for wp in item.waypoints]
            result.append({
                "seg_idx":            seg_idx,
                "item_idx":           item_idx,
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
    return result


def _aplicar_throw_settings(st, data_list):
    """Restaura los throws de los segmentos desde la lista serializada."""
    try:
        scene = st.id_data
        segs  = scene.ch1_segs.segments
    except Exception as e:
        print(f"[THROW_IMPORT] ERROR: {e}")
        return

    # Limpiar items existentes antes de reconstruir
    for seg in segs:
        seg.throws.items.clear()

    for entry in data_list:
        seg_idx = int(entry.get("seg_idx", -1))
        if seg_idx < 0 or seg_idx >= len(segs):
            continue
        th   = segs[seg_idx].throws
        th.enabled = True  # Si hay items en JSON, el filtro estaba activo
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
        item.parent_armature    = str(entry.get("parent_armature", "Armature"))
        item.parent_bone        = str(entry.get("parent_bone", ""))
        item.loc_x              = float(entry.get("loc_x", 0.0))
        item.loc_y              = float(entry.get("loc_y", 0.0))
        item.loc_z              = float(entry.get("loc_z", 0.0))
        item.rot_x              = float(entry.get("rot_x", 0.0))
        item.rot_y              = float(entry.get("rot_y", 0.0))
        item.rot_z              = float(entry.get("rot_z", 0.0))
        item.scale_uniform      = float(entry.get("scale_uniform", 1.0))
        item.target_object      = str(entry.get("target_object", ""))
        item.target_armature    = str(entry.get("target_armature", "Armature"))
        item.target_bone        = str(entry.get("target_bone", ""))
        item.dest_x             = float(entry.get("dest_x", 0.0))
        item.dest_y             = float(entry.get("dest_y", 3.0))
        item.dest_z             = float(entry.get("dest_z", 0.0))
        item.easing_global      = str(entry.get("easing_global", "SMOOTH"))
        item.spin_during_flight = bool(entry.get("spin_during_flight", False))
        item.spin_turns         = float(entry.get("spin_turns", 1.0))
        item.imported_object_name = ""
        item.waypoints.clear()
        for wp_data in entry.get("waypoints", []):
            wp         = item.waypoints.add()
            wp.label   = str(wp_data.get("label", "Punto"))
            wp.x       = float(wp_data.get("x", 0.0))
            wp.y       = float(wp_data.get("y", 0.0))
            wp.z       = float(wp_data.get("z", 2.0))
            wp.easing  = str(wp_data.get("easing", "SMOOTH"))
            wp.enabled = bool(wp_data.get("enabled", True))
        print(f"[THROW_IMPORT] seg[{seg_idx}] item[{len(th.items)-1}]: "
              f"'{item.object_name}' {item.frame_start}→{item.frame_end}")


class CH1ST_OT_SaveConfig(Operator):
    bl_idname    = "ch1st.save_config"
    bl_label     = "Guardar Configuracion"
    bl_description = (
        "Guarda la secuencia completa de trabajo (poses, rotaciones, posiciones, "
        "interpolaciones, duraciones, filtros) como archivo .json en la carpeta "
        "de configuraciones. NO incluye los keyframes de la animacion terminada"
    )
    bl_options = {"REGISTER"}

    config_name: bpy.props.StringProperty(
        name="Nombre del archivo",
        default="mi_configuracion",
        description="Nombre del archivo de configuracion a guardar (sin extension .json)",
    )

    def invoke(self, context, event):
        self.config_name = context.scene.ch1st.config_name or "mi_configuracion"
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        st = context.scene.ch1st
        layout.label(text="Nombre del archivo de configuracion:", icon="FILE_BLANK")
        layout.prop(self, "config_name", text="")
        layout.separator()
        out_dir = bpy.path.abspath(st.config_dir)
        _FORBIDDEN = set('/\\:*?"<>|')
        safe = "".join(c if c not in _FORBIDDEN else "_" for c in self.config_name).strip()
        fname = f"{safe or 'configuracion'}.json"
        layout.label(text=f"  -> {os.path.join(out_dir, fname)}", icon="INFO")
        layout.separator()
        layout.label(text="Se guardara la sesion completa:", icon="CHECKMARK")
        # Paso 1 y 2
        try:
            pc = context.scene.ch1_path
            n_pts = len(pc.path_points)
            blend_name = os.path.basename(pc.blend_filepath) if pc.blend_filepath else "(sin seleccionar)"
            layout.label(text=f"  - Paso 1: personaje '{blend_name}',  {n_pts} punto(s) de recorrido")
            layout.label(text=f"  - Paso 2: slot {pc.slot_inicio},  frame {pc.frame_inicio}→{pc.frame_fin_manual},  rot Z {pc.root_rot_z:.1f}°")
        except Exception:
            layout.label(text="  - Paso 1 y 2: (no disponible)")
        layout.separator()
        layout.label(text=f"  - Pose INICIO: nombre, archivo, duracion, interp, pos, rot")
        layout.label(text=f"  - Poses de ACCION: todas las poses intermedias")
        layout.label(text=f"  - Pose FIN: nombre, archivo, duracion, interp, pos, rot")
        layout.label(text=f"  - Configuracion: fps, frames, blend, filtros organicos")
        try:
            oi = context.scene.ch1st.object_imports
            n_oi = len(oi.items)
            layout.label(text=f"  - Importacion de Objetos: {n_oi} objeto(s) (escudo, espada, etc.)")
        except Exception:
            pass

    def execute(self, context):
        st = context.scene.ch1st

        _FORBIDDEN = set('/\\:*?"<>|')
        safe = "".join(c if c not in _FORBIDDEN else "_" for c in self.config_name).strip()
        if not safe:
            safe = "configuracion"
        filename = f"{safe}.json"

        # Guardar nombre para uso futuro
        st.config_name = self.config_name

        out_dir = bpy.path.abspath(st.config_dir)
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            self.report({"ERROR"}, f"No se pudo crear la carpeta: {e}")
            return {"CANCELLED"}

        filepath = os.path.join(out_dir, filename)
        cfg = _serialize_configuracion(st)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.report({"ERROR"}, f"Error al escribir el archivo: {e}")
            return {"CANCELLED"}

        n_acciones = len(st.action_poses)
        self.report({"INFO"},
            f"Configuracion guardada: {filename}  "
            f"({n_acciones} pose(s) de accion)  ->  {filepath}")
        return {"FINISHED"}


class CH1ST_OT_LoadConfig(Operator):
    bl_idname    = "ch1st.load_config"
    bl_label     = "Importar Configuracion"
    bl_description = (
        "Carga una configuracion de trabajo desde un .json de la carpeta de "
        "configuraciones. Restaura toda la secuencia: poses, interpolaciones, "
        "posiciones, rotaciones y filtros organicos"
    )
    bl_options = {"REGISTER", "UNDO"}

    filepath:    bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        start = bpy.path.abspath(context.scene.ch1st.config_dir)
        if os.path.isdir(start):
            self.filepath = start + os.sep
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        st   = context.scene.ch1st
        path = bpy.path.abspath(self.filepath)

        if not os.path.isfile(path):
            self.report({"ERROR"}, f"Archivo no encontrado: {path}")
            return {"CANCELLED"}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.report({"ERROR"}, f"Error al leer el JSON: {e}")
            return {"CANCELLED"}

        # Validacion basica
        if "pose_inicio" not in data and "action_poses" not in data:
            self.report({"WARNING"},
                "El archivo no parece una configuracion de Chicken1 Studio "
                "(faltan 'pose_inicio' / 'action_poses'). Se intentara importar igual.")

        _aplicar_configuracion(st, data)

        n_acciones = len(st.action_poses)
        n_obj_imp  = len(st.object_imports.items)
        version    = data.get("version", "?")
        ts         = data.get("timestamp", "")[:19].replace("T", " ")
        self.report({"INFO"},
            f"Configuracion cargada: {os.path.basename(path)}  "
            f"v{version}  {ts}  "
            f"({n_acciones} pose(s) de accion, {n_obj_imp} objeto(s) importado(s))")
        return {"FINISHED"}


class CH1ST_OT_OpenConfigFolder(Operator):
    bl_idname    = "ch1st.open_config_folder"
    bl_label     = "Abrir carpeta configuraciones"
    bl_description = "Abre la carpeta de configuraciones en el explorador de archivos"

    def execute(self, context):
        open_folder(bpy.path.abspath(context.scene.ch1st.config_dir))
        return {"FINISHED"}


# ───────────────────────────────────��─────────────────────────────────────────
# CONFIGURACION DE OJOS — serializar / deserializar
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_EYE_CONFIG_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\alfred\refinar\configuraciones_ojos"
)


def _serialize_eye_config(st):
    """
    Serializa toda la secuencia de ojos activa:
      - Frame de inicio global
      - Estado INICIO (duracion, interp)
      - Slots intermedios completos (loc/rot/sca ambos ojos, expresion, geometria, interp)
      - Estado FIN (duracion, interp)
      - Configuracion de parpadeo
    Formato identico al de poses (inicio / intermedios / fin).
    """
    eye_s = st.eye_expr

    # Slots intermedios
    slots_data = []
    for slot in st.eye_slots:
        slots_data.append({
            "slot_label":       slot.slot_label,
            "duration":         slot.duration,
            "interp_type":      slot.interp_type,
            "active_expression": slot.active_expression,
            "expression_value": slot.expression_value,
            "geo_edit_mode":    slot.geo_edit_mode,
            "geo_intensity":    slot.geo_intensity,
            "eye_L_loc_x": slot.eye_L_loc_x, "eye_L_loc_y": slot.eye_L_loc_y, "eye_L_loc_z": slot.eye_L_loc_z,
            "eye_L_rot_x": slot.eye_L_rot_x, "eye_L_rot_y": slot.eye_L_rot_y, "eye_L_rot_z": slot.eye_L_rot_z,
            "eye_L_sca_x": slot.eye_L_sca_x, "eye_L_sca_y": slot.eye_L_sca_y, "eye_L_sca_z": slot.eye_L_sca_z,
            "eye_R_loc_x": slot.eye_R_loc_x, "eye_R_loc_y": slot.eye_R_loc_y, "eye_R_loc_z": slot.eye_R_loc_z,
            "eye_R_rot_x": slot.eye_R_rot_x, "eye_R_rot_y": slot.eye_R_rot_y, "eye_R_rot_z": slot.eye_R_rot_z,
            "eye_R_sca_x": slot.eye_R_sca_x, "eye_R_sca_y": slot.eye_R_sca_y, "eye_R_sca_z": slot.eye_R_sca_z,
        })

    return {
        "version":   "1.0",
        "timestamp": datetime.now().isoformat(),
        "description": "Configuracion de secuencia de ojos — Chicken 1 Animation Studio",
        # Frame de inicio
        "eye_global_start_frame": st.eye_global_start_frame,
        # Estado INICIO
        "eye_inicio": {
            "duration":       st.eye_start_duration,
            "interp":         st.eye_start_interp,
            "blink_mode":     st.eye_start_blink_mode,
            "blink_count":    st.eye_start_blink_count,
            "blink_duration": st.eye_start_blink_duration,
        },
        # Slots intermedios
        "eye_slots": slots_data,
        # Estado FIN
        "eye_fin": {
            "duration":       st.eye_end_duration,
            "interp":         st.eye_end_interp,
            "blink_mode":     st.eye_end_blink_mode,
            "blink_count":    st.eye_end_blink_count,
            "blink_duration": st.eye_end_blink_duration,
        },
        # Parpadeo independiente
        "parpadeo": {
            "enabled":      eye_s.blink_enabled,
            "count":        eye_s.blink_count,
            "duration":     eye_s.blink_duration,
            "frame_start":  eye_s.blink_frame_start,
            "frame_end":    eye_s.blink_frame_end,
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
            "blink_interval_idx": st.blink_interval_idx,
        },
        # Setup de shape keys
        "shape_keys_setup": {
            "subdivide_cuts":    eye_s.subdivide_cuts,
            "curve_mode":        eye_s.curve_mode,
            "affect_zone":       eye_s.affect_zone,
            "swap_axes":         eye_s.swap_axes,
            "invert_vertical":   eye_s.invert_vertical,
            "invert_horizontal": eye_s.invert_horizontal,
        },
    }


def _aplicar_eye_config(st, data):
    """
    Restaura la secuencia de ojos desde el diccionario leído del JSON.
    Omite claves inexistentes (compatibilidad hacia atrás).
    Al final recrea automáticamente los shape keys con el setup guardado.
    """
    eye_s = st.eye_expr

    # Frame de inicio global
    if "eye_global_start_frame" in data:
        st.eye_global_start_frame = data["eye_global_start_frame"]

    # Estado INICIO
    ei = data.get("eye_inicio", {})
    if ei:
        st.eye_start_duration = ei.get("duration", 20)
        st.eye_start_interp   = ei.get("interp",   "SMOOTH")
        try: st.eye_start_blink_mode     = ei.get("blink_mode",     "BLINK")
        except Exception: pass
        st.eye_start_blink_count    = ei.get("blink_count",    2)
        st.eye_start_blink_duration = ei.get("blink_duration", 9)

    # Estado FIN
    ef = data.get("eye_fin", {})
    if ef:
        st.eye_end_duration = ef.get("duration", 20)
        st.eye_end_interp   = ef.get("interp",   "SMOOTH")
        try: st.eye_end_blink_mode     = ef.get("blink_mode",     "BLINK")
        except Exception: pass
        st.eye_end_blink_count    = ef.get("blink_count",    2)
        st.eye_end_blink_duration = ef.get("blink_duration", 9)

    # Slots intermedios
    st.eye_slots.clear()
    for sd in data.get("eye_slots", []):
        slot = st.eye_slots.add()
        slot.slot_label        = sd.get("slot_label",        "cambio")
        slot.duration          = sd.get("duration",          20)
        slot.interp_type       = sd.get("interp_type",       "SMOOTH")
        slot.active_expression = sd.get("active_expression", "NEUTRAL")
        slot.expression_value  = min(sd.get("expression_value",  0.05), 0.05)
        slot.geo_edit_mode     = sd.get("geo_edit_mode",     "NONE")
        slot.geo_intensity     = sd.get("geo_intensity",     1.0)
        slot.eye_L_loc_x = sd.get("eye_L_loc_x",  0.106646)
        slot.eye_L_loc_y = sd.get("eye_L_loc_y",  0.270456)
        slot.eye_L_loc_z = sd.get("eye_L_loc_z",  1.700815)
        slot.eye_L_rot_x = sd.get("eye_L_rot_x",  0.0)
        slot.eye_L_rot_y = sd.get("eye_L_rot_y",  0.0)
        slot.eye_L_rot_z = sd.get("eye_L_rot_z",  0.0)
        slot.eye_L_sca_x = sd.get("eye_L_sca_x",  1.555)
        slot.eye_L_sca_y = sd.get("eye_L_sca_y",  0.496018)
        slot.eye_L_sca_z = sd.get("eye_L_sca_z",  3.55)
        slot.eye_R_loc_x = sd.get("eye_R_loc_x", -0.1053)
        slot.eye_R_loc_y = sd.get("eye_R_loc_y",  0.256331)
        slot.eye_R_loc_z = sd.get("eye_R_loc_z",  1.700426)
        slot.eye_R_rot_x = sd.get("eye_R_rot_x",  0.0)
        slot.eye_R_rot_y = sd.get("eye_R_rot_y",  0.0)
        slot.eye_R_rot_z = sd.get("eye_R_rot_z",  0.0)
        slot.eye_R_sca_x = sd.get("eye_R_sca_x",  1.555)
        slot.eye_R_sca_y = sd.get("eye_R_sca_y",  0.496018)
        slot.eye_R_sca_z = sd.get("eye_R_sca_z",  3.55)

    # Parpadeo
    pb = data.get("parpadeo", {})
    if pb:
        eye_s.blink_enabled     = pb.get("enabled",     False)
        eye_s.blink_count       = pb.get("count",       2)
        eye_s.blink_duration    = pb.get("duration",    9)
        eye_s.blink_frame_start = pb.get("frame_start", 1)
        eye_s.blink_frame_end   = pb.get("frame_end",   60)

        # Restaurar la coleccion completa de intervalos de parpadeo
        intervals_data = pb.get("blink_intervals", [])
        if intervals_data:
            st.blink_intervals.clear()
            for bd in intervals_data:
                bi = st.blink_intervals.add()
                bi.label          = bd.get("label",          "Parpadeo")
                bi.frame_start    = bd.get("frame_start",    1)
                bi.frame_end      = bd.get("frame_end",      60)
                bi.blink_count    = bd.get("blink_count",    2)
                bi.blink_duration = bd.get("blink_duration", 9)
                bi.enabled        = bd.get("enabled",        True)
            st.blink_interval_idx = min(
                pb.get("blink_interval_idx", 0),
                max(0, len(st.blink_intervals) - 1)
            )

    # ── Setup shape keys — PRIMERO aplicar los valores, LUEGO recrear ────────
    sk = data.get("shape_keys_setup", {})
    if sk:
        # Aplicar todos los parámetros de configuración al eye_s
        try:
            eye_s.subdivide_cuts     = sk.get("subdivide_cuts",    2)
        except Exception:
            pass
        try:
            eye_s.curve_mode         = sk.get("curve_mode",        "SMOOTH")
        except Exception:
            pass
        try:
            eye_s.affect_zone        = sk.get("affect_zone",       "FULL")
        except Exception:
            pass
        eye_s.swap_axes          = sk.get("swap_axes",          False)
        eye_s.invert_vertical    = sk.get("invert_vertical",    False)
        eye_s.invert_horizontal  = sk.get("invert_horizontal",  False)

        # Recrear shape keys automáticamente con el setup recién restaurado
        try:
            result = bpy.ops.ch1st.build_eye_shape_keys()
            if result == {"FINISHED"}:
                print("[Alfred] Shape keys recreados automáticamente al importar config de ojos")
            else:
                print("[Alfred] ADVERTENCIA: build_eye_shape_keys no pudo ejecutarse — hazlo manualmente")
        except Exception as e:
            print(f"[Alfred] No se pudo recrear shape keys automáticamente: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# OPERADORES EXPORTAR / IMPORTAR CONFIGURACION DE OJOS
# ─────────────────────────────────────────────────────────────────────────────

class CH1ST_OT_SaveEyeConfig(Operator):
    bl_idname    = "ch1st.save_eye_config"
    bl_label     = "Exportar configuracion de ojos"
    bl_description = (
        "Guarda la secuencia completa de ojos (inicio / intermedios / fin + parpadeo) "
        "como archivo .json en la carpeta de configuraciones de ojos"
    )
    bl_options = {"REGISTER"}

    config_name: bpy.props.StringProperty(
        name="Nombre del archivo",
        default="ojos_config",
        description="Nombre del archivo (sin .json)",
    )

    def invoke(self, context, event):
        self.config_name = context.scene.ch1st.eye_config_name or "ojos_config"
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        layout = self.layout
        st     = context.scene.ch1st
        layout.label(text="Nombre del archivo:", icon="FILE_BLANK")
        layout.prop(self, "config_name", text="")
        layout.separator()
        _FORBIDDEN = set('/\\:*?"<>|')
        safe  = "".join(c if c not in _FORBIDDEN else "_" for c in self.config_name).strip()
        fname = f"{safe or 'ojos_config'}.json"
        layout.label(text=f"  -> {os.path.join(DEFAULT_EYE_CONFIG_DIR, fname)}", icon="INFO")
        layout.separator()
        layout.label(text="Se guardara la secuencia completa de ojos:", icon="CHECKMARK")
        layout.label(text=f"  - INICIO: duracion + interp")
        n = len(st.eye_slots)
        layout.label(text=f"  - {n} cambio(s) intermedio(s) con transforms + expresion + geo")
        layout.label(text=f"  - FIN: duracion + interp")
        layout.label(text=f"  - Parpadeo: {'activado' if st.eye_expr.blink_enabled else 'desactivado'}")

    def execute(self, context):
        st = context.scene.ch1st

        _FORBIDDEN = set('/\\:*?"<>|')
        safe = "".join(c if c not in _FORBIDDEN else "_" for c in self.config_name).strip()
        if not safe:
            safe = "ojos_config"
        filename = f"{safe}.json"
        st.eye_config_name = self.config_name

        out_dir = DEFAULT_EYE_CONFIG_DIR
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            self.report({"ERROR"}, f"No se pudo crear la carpeta: {e}")
            return {"CANCELLED"}

        filepath = os.path.join(out_dir, filename)
        cfg = _serialize_eye_config(st)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.report({"ERROR"}, f"Error al escribir: {e}")
            return {"CANCELLED"}

        self.report({"INFO"},
            f"Config ojos guardada: {filename}  "
            f"({len(st.eye_slots)} slot(s))  ->  {filepath}")
        return {"FINISHED"}


class CH1ST_OT_LoadEyeConfig(Operator):
    bl_idname    = "ch1st.load_eye_config"
    bl_label     = "Importar configuracion de ojos"
    bl_description = (
        "Carga una configuracion de ojos desde un .json. "
        "Restaura inicio / intermedios / fin y parpadeo"
    )
    bl_options = {"REGISTER", "UNDO"}

    filepath:    bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        start = DEFAULT_EYE_CONFIG_DIR
        if os.path.isdir(start):
            self.filepath = start + os.sep
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        st   = context.scene.ch1st
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

        if "eye_slots" not in data and "eye_inicio" not in data:
            self.report({"WARNING"},
                "El archivo no parece una configuracion de ojos de Chicken1 Studio")

        _aplicar_eye_config(st, data)

        n      = len(st.eye_slots)
        ts     = data.get("timestamp", "")[:19].replace("T", " ")
        has_sk = bool(data.get("shape_keys_setup"))
        sk_msg = "  — Shape keys recreados automaticamente" if has_sk else ""
        self.report({"INFO"},
            f"Config ojos cargada: {os.path.basename(path)}  "
            f"{ts}  ({n} slot(s)){sk_msg}")
        return {"FINISHED"}



