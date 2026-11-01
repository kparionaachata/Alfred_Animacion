# -*- coding: utf-8 -*-
"""
panels.py — Rat 1 Animation Studio

Version reducida de ALFST_PT_PathRecorder: solo Paso 1 (trazar
recorrido) y Paso 2 (configuracion/estimacion/exportacion de slots).
Sin Paso 3, sin ojos, sin filtros organicos -- ese UI no existe en este
addon todavia.
"""

from bpy.types import Panel


class RAT1ST_PT_PathRecorder(Panel):
    bl_label       = "Recorrido y Slots (Paso 1 y 2)"
    bl_idname      = "RAT1ST_PT_path_recorder"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Rat 1 Studio"

    def draw(self, context):
        layout = self.layout
        pc = context.scene.rat1_path

        # ── PASO 1: Personaje y grabacion de recorrido ────────────────────
        box_paso1 = layout.box()
        box_paso1.label(text="PASO 1 — Trazar recorrido", icon="CON_FOLLOWPATH")

        col_blend = box_paso1.column(align=True)
        col_blend.label(text="Personaje (.blend):", icon="ARMATURE_DATA")
        row_blend = col_blend.row(align=True)
        row_blend.prop(pc, "blend_filepath", text="")
        row_blend.operator("rat1pr.open_blend", text="", icon="FILEBROWSER")

        box_paso1.separator(factor=0.5)

        rec_text = "  Detener grabacion de recorrido" if pc.recording_active else "  Iniciar grabacion de recorrido"
        rec_icon = "REC" if pc.recording_active else "RADIOBUT_ON"
        row_rec = box_paso1.row()
        row_rec.scale_y = 1.3
        row_rec.operator("rat1pr.toggle_recording", text=rec_text, icon=rec_icon)

        viz_text = "  Ocultar recorrido" if pc.show_path_viz else "  Visualizar recorrido"
        viz_icon = "HIDE_OFF" if pc.show_path_viz else "HIDE_ON"
        row_viz = box_paso1.row()
        row_viz.operator("rat1pr.toggle_path_viz", text=viz_text, icon=viz_icon)
        row_viz.enabled = len(pc.path_points) > 0

        row_pts = box_paso1.row(align=True)
        row_pts.label(text=f"Puntos registrados: {len(pc.path_points)}")
        row_remove = box_paso1.row(align=True)
        row_remove.operator("rat1pr.remove_last", text="Quitar ultimo", icon="REMOVE")
        row_remove.operator("rat1pr.clear_path",  text="Limpiar todo",  icon="X")

        if not pc.blend_filepath:
            box_paso1.label(text="Selecciona el archivo .blend del personaje (o usa la escena actual)", icon="INFO")
        n_reg = len(pc.path_points)
        if n_reg == 0:
            box_paso1.label(text="Selecciona faces para trazar el recorrido", icon="INFO")
        elif n_reg == 1:
            box_paso1.label(text="Modo: 1 coordenada  (parado/idle)", icon="RADIOBUT_ON")
        else:
            box_paso1.label(text=f"Modo: recorrido  ({n_reg} puntos)", icon="CON_FOLLOWPATH")

        # ── Lista de coordenadas seleccionadas (EDITABLE) ──────────────────
        n_pts_lista = len(pc.path_points)
        if n_pts_lista > 0:
            from .path_recorder import _detect_move_geom

            box_lista = box_paso1.box()
            header_row = box_lista.row(align=True)
            header_row.prop(
                pc, "show_coords_list",
                icon="TRIA_DOWN" if pc.show_coords_list else "TRIA_RIGHT",
                text=f"Coordenadas seleccionadas  ({n_pts_lista})",
                emboss=False,
            )

            if pc.show_coords_list:
                n_marcadas = sum(1 for pt in pc.path_points if pt.tipo_segmento == "PARADA")
                info_row = box_lista.row()
                if n_marcadas == 0:
                    info_row.label(text="Todos en 'Caminar': el recorrido sera solo caminata/saltos", icon="INFO")
                else:
                    info_row.label(text=f"{n_marcadas} punto(s) marcado(s) como 'Parada'", icon="PAUSE")

                pts_list = list(pc.path_points)
                col_lista = box_lista.column(align=False)

                for i, pt in enumerate(pts_list):
                    row_pt = col_lista.row(align=True)

                    op_del_pt = row_pt.operator("rat1pr.remove_point", text="", icon="X", emboss=False)
                    op_del_pt.index = i

                    row_pt.label(text=f"{i+1:>2}.", icon="LAYER_USED")

                    x, y, z = round(pt.coords[0], 2), round(pt.coords[1], 2), round(pt.coords[2], 2)
                    row_pt.label(text=f"({x},  {y},  {z})")

                    if i < len(pts_list) - 1:
                        geom_move = _detect_move_geom(pt, pts_list[i + 1])
                        if geom_move == "caminar":
                            row_pt.prop(pt, "tipo_segmento", text="")
                            if pt.tipo_segmento == "PARADA":
                                row_pt.prop(pt, "parada_frames_punto", text="Frames")
                        elif geom_move == "saltar_subir":
                            row_pt.label(text="subir", icon="SORT_DESC")
                        else:
                            row_pt.label(text="bajar", icon="SORT_ASC")
                    else:
                        row_pt.prop(pt, "tipo_segmento", text="")
                        if pt.tipo_segmento == "PARADA":
                            row_pt.prop(pt, "parada_frames_punto", text="Frames")
                        row_pt.label(text="(final)", icon="KEYFRAME")

                    tex = pt.texture or ""
                    if tex:
                        col_lista.label(text=f"       Textura: {tex}", icon="TEXTURE")
                    col_lista.separator(factor=0.3)

        # ── PASO 2: Configuracion de slots ─────────────────────────────────
        n_pts_reg = len(pc.path_points)
        is_idle      = (n_pts_reg == 1)
        is_recorrido = (n_pts_reg > 1)

        box_paso2 = layout.box()
        box_paso2.label(text="PASO 2 — Configuracion de slots", icon="SETTINGS")
        box_paso2.label(text="  Biomecanica cuadrupeda real: trote diagonal + saltos con patas/columna/cola", icon="INFO")
        col2 = box_paso2.column(align=True)
        col2.prop(pc, "slot_inicio",  text="Slot inicio")
        col2.prop(pc, "frame_inicio", text="Frame inicial")

        if is_idle:
            col2.prop(pc, "frame_fin_manual", text="Frame final")
        if is_recorrido:
            col2.prop(pc, "frames_por_unidad", text="Frames/unidad (caminar, referencia)")
            col2.prop(pc, "frames_parada", text="Frames por parada (default)")

        col2.separator()
        col2.label(text="Orientacion inicial:", icon="ORIENTATION_GIMBAL")
        row_rot = col2.row(align=True)
        row_rot.prop(pc, "root_rot_x", text="X")
        row_rot.prop(pc, "root_rot_y", text="Y")
        row_rot.prop(pc, "root_rot_z", text="Z")

        col2.separator()
        col2.label(text="Carpeta de salida:", icon="FILE_FOLDER")
        col2.prop(pc, "output_dir", text="")

        from .path_recorder import calcular_estimacion_geometrica, _group_segments, _expand_points_with_paradas

        if len(pc.path_points) > 1:
            pts = list(pc.path_points)
            expanded_pts, _ = _expand_points_with_paradas(pts)
            segs_chk = _group_segments(expanded_pts)
            n_paradas_actual = sum(1 for s in segs_chk if s["type"] == "parada")
            if len(pc.paradas_frames) != n_paradas_actual:
                row_sync = box_paso2.row()
                row_sync.alert = True
                row_sync.operator("rat1pr.sync_paradas_frames",
                                   text=f"Sincronizar frames por parada ({n_paradas_actual} detectada(s))",
                                   icon="FILE_REFRESH")

        _slots_est = calcular_estimacion_geometrica(context.scene)
        if _slots_est:
            box_est = box_paso2.box()
            box_est.label(text="Estimacion de segmentos:", icon="INFO")
            _caminar_idx_ui = 0
            for _s in _slots_est:
                row_seg = box_est.row(align=True)
                row_seg.label(text=f"  Segmento {_s['slot']}: {_s['label']} (~{_s['frames_estimados']} f)")
                if _s["tipo"] == "caminar":
                    if _caminar_idx_ui < len(pc.walk_styles):
                        row_seg.prop(pc.walk_styles[_caminar_idx_ui], "style", text="")
                    _caminar_idx_ui += 1
            if len(pc.path_points) > 1:
                _n_caminar_real = sum(1 for _s in _slots_est if _s["tipo"] == "caminar")
                if len(pc.walk_styles) != _n_caminar_real:
                    row_sync_ws = box_est.row()
                    row_sync_ws.alert = True
                    row_sync_ws.operator("rat1pr.sync_paradas_frames",
                                          text=f"Sincronizar estilos de caminata ({_n_caminar_real} tramo(s) detectado(s))",
                                          icon="FILE_REFRESH")

        if pc.anim_frame_fin > 0:
            box_dur = box_paso2.box()
            total_f = pc.anim_frame_fin - pc.frame_inicio + 1
            box_dur.label(text=f"Duracion: {total_f} frames  ({total_f / 24:.2f}s @ 24fps)", icon="TIME")
            box_dur.label(text=f"Frame {pc.frame_inicio}  →  {pc.anim_frame_fin}", icon="ARROW_LEFTRIGHT")

        layout.separator(factor=0.5)
        row_play = layout.row()
        row_play.scale_y = 1.5
        row_play.operator("rat1pr.preview_path", text="  Reproducir recorrido", icon="PLAY")

        box_exp = layout.box()
        box_exp.label(text="Exportar slots (opcional):", icon="EXPORT")
        box_exp.label(text="  Incluye biomecanica de los 22 bones (patas/columna/cola)", icon="INFO")
        row_exp = box_exp.row()
        row_exp.scale_y = 1.3
        row_exp.operator("rat1pr.export_slots", text="  Exportar recorrido", icon="EXPORT")

        layout.separator(factor=0.3)
        row_reset = layout.row()
        row_reset.operator("rat1pr.reset_preview", text="  Reset recorrido", icon="LOOP_BACK")

        if pc.anim_frame_fin > 0:
            layout.label(text=f"Rango fijado: {pc.frame_inicio}→{pc.anim_frame_fin}", icon="PINNED")


class RAT1SEG_PT_Segments(Panel):
    """PASO 3 -- Segmentos, poses (keyframes), NLA y Concatenar.
    Port reducido desde ALFST_PT (ver docs/PORT_NOTES.md): sin ojos, sin
    Lanzar/Recoger objetos, sin Invisibilidad de Malla, sin filtros
    organicos -- rat_1 no tiene esos sistemas."""
    bl_label       = "Segmentos, Poses y Concatenar (Paso 3)"
    bl_idname      = "RAT1SEG_PT_segments"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Rat 1 Studio"

    def draw(self, context):
        layout = self.layout
        segs = context.scene.rat1_segs
        pc = context.scene.rat1_path

        row_arm = layout.row(align=True)
        row_arm.prop(segs, "armature_name")
        row_arm.prop(segs, "poses_dir", text="")

        n_pts = len(pc.path_points)
        _modo_1coord = (n_pts <= 1)

        # ── Cabecera PASO 3 (port de ALFST_PT_Segments, alfred_animation_
        # studio/panels.py -- mismo layout, adaptado a scene.rat1_path/
        # scene.rat1_segs y a los tramos caminar/saltar_subir/saltar_bajar/
        # parada de calcular_estimacion_geometrica) ─────────────────────
        box3 = layout.box()
        row_title3 = box3.row()
        row_title3.alert = True
        row_title3.label(text="PASO 3 — Crear segmento", icon="KEYFRAME")

        if _modo_1coord:
            # ── MODO 1 COORDENADA ─────────────────────────────────────
            box_info = box3.box()
            col_info3 = box_info.column(align=True)
            col_info3.scale_y = 0.85
            col_info3.label(
                text=f"Frame inicio (Paso 1):  {pc.frame_inicio}",
                icon="KEYFRAME"
            )
            col_info3.label(text="Frame fin: calculado al CONCATENAR", icon="TIME")
            col_info3.label(text="(N poses de accion)", icon="INFO")

            box3.separator(factor=0.3)
            box3.prop(segs, "edit_label", text="Nombre")

            layout.separator(factor=0.5)
            row_crear = layout.row()
            row_crear.scale_y = 2.2
            row_crear.alert = True
            row_crear.operator("rat1seg.add", text="+ CREAR SEGMENTO", icon="ADD")

        else:
            # ── MODO RECORRIDO (2+ coordenadas) ───────────────────────
            try:
                _anim_f_inicio = pc.frame_inicio
                _anim_f_fin    = getattr(pc, "anim_frame_fin", _anim_f_inicio + 1)
                _total_est     = max(0, _anim_f_fin - _anim_f_inicio + 1) if _anim_f_fin > _anim_f_inicio else 0
            except Exception:
                _anim_f_inicio = 1
                _anim_f_fin    = 1
                _total_est     = 0

            try:
                _occupied = sorted(
                    [(s.frame_start, s.frame_end) for s in segs.segments if s.enabled],
                    key=lambda x: x[0]
                )
            except Exception:
                _occupied = []

            box_rng = box3.box()
            col_rng = box_rng.column(align=True)
            col_rng.scale_y = 0.85
            col_rng.label(
                text=f"Rango animacion:  {_anim_f_inicio} → {_anim_f_fin}  ({_total_est} fr)",
                icon="TIME"
            )
            if _occupied:
                used_str = "  ".join(f"{_fs}→{_fe}" for _fs, _fe in _occupied)
                col_rng.label(text=f"Ocupados: {used_str}", icon="KEYFRAME_HLT")
            _free_ranges = []
            _cur = _anim_f_inicio
            for _fs2, _fe2 in _occupied:
                if _cur < _fs2:
                    _free_ranges.append((_cur, _fs2 - 1))
                _cur = max(_cur, _fe2 + 1)
            if _cur <= _anim_f_fin:
                _free_ranges.append((_cur, _anim_f_fin))
            if _free_ranges:
                free_str = "  ".join(f"{_a}→{_b}({_b-_a+1}f)" for _a, _b in _free_ranges)
                col_rng.label(text=f"Libres: {free_str}", icon="CHECKMARK")
            else:
                col_rng.label(text="Sin frames libres", icon="ERROR")

            box3.separator(factor=0.3)
            row_auto = box3.row()
            row_auto.scale_y = 1.4
            row_auto.operator(
                "rat1seg.autosplit_from_config",
                text="Dividir segmentos",
                icon="MOD_ARRAY",
            )
            box3.label(
                text="  Crea un segmento por cada tramo (caminar/salto/parada) del recorrido",
                icon="INFO",
            )

            box3.separator(factor=0.3)
            box3.prop(segs, "edit_label", text="Nombre")

            box_fr = box3.box()
            box_fr.label(text="Intervalo del segmento:", icon="KEYFRAME")
            col_fr = box_fr.column(align=True)

            _fs_edit = segs.edit_frame_start
            _fe_edit = segs.edit_frame_end
            _fs_ok   = False
            _fe_ok   = False
            _overlap = False

            if _total_est == 0:
                col_fr.label(text="  Graba un recorrido de 2+ puntos en el Paso 1", icon="INFO")
                row_fs = col_fr.row(align=True)
                row_fs.enabled = False
                row_fs.prop(segs, "edit_frame_start", text="Frame inicio")
                row_fe = col_fr.row(align=True)
                row_fe.enabled = False
                row_fe.prop(segs, "edit_frame_end", text="Frame fin")
            else:
                _fs_ok   = _anim_f_inicio <= _fs_edit <= _anim_f_fin
                _fe_ok   = (_anim_f_inicio <= _fe_edit <= _anim_f_fin) and (_fe_edit > _fs_edit)
                _overlap = any(_fs_edit <= _fe3 and _fe_edit >= _fs3 for _fs3, _fe3 in _occupied)

                row_fs = col_fr.row(align=True)
                row_fs.alert = not _fs_ok
                row_fs.prop(segs, "edit_frame_start", text="Frame inicio")

                row_fe = col_fr.row(align=True)
                row_fe.alert = not _fe_ok
                row_fe.prop(segs, "edit_frame_end", text="Frame fin")

                if _fe_edit > _fs_edit:
                    col_fr.label(text=f"  Duracion: {_fe_edit - _fs_edit} frames", icon="INFO")
                if not _fs_ok or not _fe_ok:
                    box_fr.label(
                        text=f"  Debe estar entre {_anim_f_inicio} y {_anim_f_fin}",
                        icon="ERROR")
                if _overlap:
                    box_fr.label(text="  Solapamiento con otro segmento", icon="ERROR")

            layout.separator(factor=0.5)
            _puede_crear = _fs_ok and _fe_ok and not _overlap and _total_est > 0
            row_crear = layout.row()
            row_crear.scale_y = 2.2
            row_crear.alert   = True
            row_crear.enabled = _puede_crear
            row_crear.operator("rat1seg.add", text="+ CREAR SEGMENTO", icon="ADD")
            if not _puede_crear and _total_est > 0:
                layout.label(text="  Corrige los frames antes de crear", icon="ERROR")

        # ── Concatenar segmentos: ejecuta CONCATENAR de CADA segmento
        #    activo, respetando el rango de frames propio de cada uno, y
        #    reproduce todas las secuencias encadenadas de principio a fin ──
        layout.separator(factor=0.5)
        _n_enabled = sum(1 for s in segs.segments if s.enabled)
        row_concat = layout.row()
        row_concat.scale_y = 1.8
        row_concat.enabled = _n_enabled > 0
        row_concat.operator(
            "rat1seg.concatenate_all",
            text=f"▶ Concatenar segmentos ({_n_enabled})",
            icon="SEQUENCE",
        )
        if _n_enabled == 0:
            layout.label(text="  Activa al menos un segmento para concatenar", icon="INFO")

        layout.separator(factor=0.5)

        # ── Lista de segmentos ───────────────────────────────────────────
        box_list = layout.box()
        box_list.label(text=f"Segmentos ({len(segs.segments)})", icon="NLA")
        row_list = box_list.row()
        row_list.template_list("RAT1SEG_UL_Segments", "", segs, "segments", segs, "active_index", rows=5)
        col_ops = row_list.column(align=True)
        col_ops.operator("rat1seg.move", text="", icon="TRIA_UP").direction = "UP"
        col_ops.operator("rat1seg.move", text="", icon="TRIA_DOWN").direction = "DOWN"
        col_ops.separator()
        col_ops.operator("rat1seg.duplicate", text="", icon="DUPLICATE")
        col_ops.operator("rat1seg.remove", text="", icon="X")

        idx = segs.active_index
        if not (0 <= idx < len(segs.segments)):
            layout.label(text="Selecciona o crea un segmento", icon="INFO")
            return
        seg = segs.segments[idx]

        # ── Configuracion del segmento activo ────────────────────────────
        box_seg = layout.box()
        box_seg.prop(seg, "label")
        row_fs = box_seg.row(align=True)
        row_fs.prop(seg, "frame_start")
        row_fs.operator("rat1seg.set_frame_start", text="", icon="PLAY_REVERSE")
        row_fe = box_seg.row(align=True)
        row_fe.prop(seg, "frame_end")
        row_fe.operator("rat1seg.set_frame_end", text="", icon="PLAY")
        box_seg.label(text=f"Duracion actual: {max(0, seg.frame_end - seg.frame_start + 1)} frames")

        row_play = box_seg.row(align=True)
        row_play.operator("rat1seg.play_segment", text="Reproducir", icon="PLAY").item_idx = idx
        row_play.operator("rat1seg.pause_segment", text="", icon="PAUSE")
        row_play.operator("rat1seg.stop_segment", text="", icon="SNAP_FACE")

        # ── Poses (keyframes) del segmento ───────────────────────────────
        box_poses = layout.box()
        box_poses.label(text=f"Poses de accion ({len(seg.action_poses)})", icon="POSE_HLT")
        for p_idx, slot in enumerate(seg.action_poses):
            row_p = box_poses.row(align=True)
            row_p.label(text=f"{p_idx+1}. {slot.pose_name or slot.json_file}  ({slot.duration}f, {slot.interp_type})")
            op_edit = row_p.operator("rat1seg.edit_action_pose_seg", text="", icon="GREASEPENCIL")
            op_edit.item_idx, op_edit.pose_idx = idx, p_idx
            op_up = row_p.operator("rat1seg.move_action_pose_seg", text="", icon="TRIA_UP")
            op_up.item_idx, op_up.direction = idx, "UP"
            op_dn = row_p.operator("rat1seg.move_action_pose_seg", text="", icon="TRIA_DOWN")
            op_dn.item_idx, op_dn.direction = idx, "DOWN"
            op_rm = row_p.operator("rat1seg.remove_action_pose_seg", text="", icon="X")
            op_rm.item_idx, op_rm.pose_idx = idx, p_idx

        row_add_pose = box_poses.row(align=True)
        row_add_pose.operator("rat1seg.add_action_pose_seg", text="  Agregar pose", icon="PLUS").item_idx = idx
        row_add_pose.operator("rat1seg.quick_pose_extract", text="  Extraer pose actual", icon="COPYDOWN")

        # ── Pose intermedia + interpolacion ──────────────────────────────
        box_mid = layout.box()
        box_mid.label(text="Pose intermedia (opcional)", icon="IPO_BEZIER")
        row_mid_f = box_mid.row(align=True)
        row_mid_f.prop(seg, "frame_mid")
        row_mid_f.operator("rat1seg.set_frame_mid", text="", icon="TRACKING")
        box_mid.label(text=seg.pose_mid_label or "(sin pose intermedia)")
        box_mid.prop(seg, "interp_type", text="Interp. inicio->mid")
        box_mid.prop(seg, "interp_mid_to_end", text="Interp. mid->fin")

        # ── Blend entrada/salida ─────────────────────────────────────────
        box_blend = layout.box()
        box_blend.label(text="Mezcla con el recorrido base", icon="IPO_EASE_IN_OUT")
        row_bl = box_blend.row(align=True)
        row_bl.prop(seg, "blend_in_frames")
        row_bl.prop(seg, "blend_out_frames")
        box_blend.prop(seg, "blend_strength")

        # ── Bloqueador de bones ──────────────────────────────────────────
        box_lock = layout.box()
        box_lock.label(text="Bloqueador de bones (no reciben pose)", icon="LOCKED")
        col_lock = box_lock.column(align=True)
        for attr in (
            "filter_body1", "filter_body2", "filter_neck", "filter_head",
            "filter_left_arm", "filter_left_hand", "filter_right_arm", "filter_right_hand",
            "filter_left_thigh", "filter_left_foot", "filter_right_thigh", "filter_right_foot",
            "filter_tail1", "filter_tail2",
        ):
            col_lock.prop(seg, attr)

        # ── Filtros organicos (post-proceso, aislado por segmento) ─────────
        # AISLAMIENTO POR SEGMENTO: org apunta a la instancia PROPIA de este
        # segmento (seg.organic), no a una copia global -- cada segmento
        # guarda y reproduce sus propios valores (mismo patron que Alfred).
        box_og = layout.box()
        org = seg.organic
        row_og_hdr = box_og.row()
        row_og_hdr.prop(org, "enabled", text="Filtros organicos", icon="MOD_NOISE")
        if org.enabled:
            box_b = box_og.box()
            box_b.prop(org, "breathing_enabled", text="Respiracion (body2_1)")
            if org.breathing_enabled:
                col_b = box_b.column(align=True)
                col_b.prop(org, "breathing_amplitude", text="Amplitud")
                col_b.prop(org, "breathing_speed",     text="Velocidad")
                col_b.prop(org, "breathing_phase",     text="Fase")

            box_h = box_og.box()
            box_h.prop(org, "head_sway_enabled", text="Micro-movimiento cabeza (neck_1/head_1)")
            if org.head_sway_enabled:
                col_h = box_h.column(align=True)
                col_h.prop(org, "head_sway_amplitude", text="Amplitud")
                col_h.prop(org, "head_sway_speed",     text="Velocidad")
                col_h.prop(org, "head_sway_seed",      text="Semilla")

            box_w = box_og.box()
            box_w.prop(org, "weight_shift_enabled", text="Desplazamiento de peso (body1_1)")
            if org.weight_shift_enabled:
                col_w = box_w.column(align=True)
                col_w.prop(org, "weight_shift_amplitude", text="Amplitud")
                col_w.prop(org, "weight_shift_speed",     text="Velocidad")

            box_r = box_og.box()
            box_r.prop(org, "root_noise_enabled", text="Noise posicion ROOT (rat_1)")
            if org.root_noise_enabled:
                col_r = box_r.column(align=True)
                col_r.prop(org, "root_noise_strength",  text="Intensidad")
                col_r.prop(org, "root_noise_frequency", text="Frecuencia")
                col_r.prop(org, "root_noise_seed",      text="Semilla")

            box_sec = box_og.box()
            box_sec.prop(org, "secondary_motion_enabled", text="Secondary motion manos")
            if org.secondary_motion_enabled:
                col_sec = box_sec.column(align=True)
                col_sec.prop(org, "secondary_motion_lag",     text="Retardo (frames)")
                col_sec.prop(org, "secondary_motion_damping", text="Amortiguacion")

            box_sm = box_og.box()
            box_sm.prop(org, "smooth_curves_enabled", text="Suavizar fcurves")
            if org.smooth_curves_enabled:
                col_sm = box_sm.column(align=True)
                col_sm.prop(org, "smooth_passes", text="Pasadas")
                col_sm.prop(org, "smooth_factor", text="Factor", slider=True)

            box_ms = box_og.box()
            box_ms.prop(org, "micro_scale_enabled", text="Micro-escala organica (body2_1)")
            if org.micro_scale_enabled:
                box_ms.prop(org, "micro_scale_amplitude", text="Amplitud")

            box_sh = box_og.box()
            box_sh.prop(org, "shoulder_noise_enabled", text="Noise hombros (leftArm_1/rightArm_1)")
            if org.shoulder_noise_enabled:
                col_sh = box_sh.column(align=True)
                col_sh.prop(org, "shoulder_noise_amplitude", text="Amplitud")
                col_sh.prop(org, "shoulder_noise_speed",     text="Velocidad")
                col_sh.prop(org, "shoulder_noise_seed",      text="Semilla")

            box_og.label(text="Se aplican al presionar CONCATENAR SEGMENTOS", icon="INFO")

        layout.separator(factor=0.5)

        # ── Aplicar (rapido, sin aislar) ────────────────────────────────
        # El boton "Concatenar segmentos (N)" que arma la secuencia aislada
        # por NLA ya esta arriba, junto al resto de la cabecera del Paso 3
        # (mismo lugar que en alfred_animation_studio) -- aca solo queda
        # APLICAR, la variante rapida que escribe directo sobre la action
        # existente sin aislar un segmento de otro.
        box_run = layout.box()
        row_apply = box_run.row()
        row_apply.scale_y = 1.3
        row_apply.operator("rat1seg.apply", text="  APLICAR SEGMENTOS", icon="MOD_ARMATURE")
        if segs.status_msg:
            box_run.label(text=segs.status_msg, icon="INFO")


class RAT1SEG_PT_ConfigSession(Panel):
    """Panel INDEPENDIENTE de Guardar/Importar configuracion, a imagen de
    ALFST_PT_ConfigSession en alfred_animation_studio (ahi cuelga de
    ALFST_PT_main, NUNCA de la Segments -- guarda la sesion de trabajo
    completa, no solo el Paso 3).

    FIX (pedido de Kebyn): antes este panel era subpanel de
    RAT1SEG_PT_segments (bl_parent_id apuntaba ahi) y solo guardaba/
    restauraba los segmentos del Paso 3, pese a que "Guardar/Importar
    Configuracion" debe cubrir TODO lo aplicado en el Paso 1 (recorrido),
    Paso 2 (slots/frames/estilos de caminata) y Paso 3 (segmentos/poses).
    Ahora es un panel de primer nivel (sin bl_parent_id -- no depende de
    la jerarquia de Segmentos) y rat1seg.save_config/load_config
    (operators_segments.py) incluyen el recorrido completo del Paso 1+2
    (via config_ops._serialize_path/_deserialize_path) ademas de los
    segmentos del Paso 3 en el mismo .json."""
    bl_label       = "Guardar / Importar Configuracion (Pasos 1-3)"
    bl_idname      = "RAT1SEG_PT_config_session"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Rat 1 Studio"
    bl_options     = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        pc = context.scene.rat1_path
        segs = context.scene.rat1_segs

        # ── Informacion: que es esta funcion ───────────────────────────────
        box_info = layout.box()
        box_info.label(text="Guardar / recuperar la sesion de trabajo completa", icon="BOOKMARKS")
        box_info.label(text="  Exporta el recorrido y ajustes del Paso 1+2,", icon="INFO")
        box_info.label(text="  y los segmentos, poses, interpolaciones,")
        box_info.label(text="  duraciones, bloqueador de bones y filtros")
        box_info.label(text="  organicos del Paso 3 (por segmento) como .json.")

        layout.separator()

        # ── Carpeta de configuraciones ──────────────────────────────────────
        box_cfgdir = layout.box()
        box_cfgdir.label(text="Carpeta de configuraciones", icon="FILEBROWSER")
        box_cfgdir.prop(segs, "config_dir", text="")
        box_cfgdir.operator("rat1seg.open_config_folder", text="Abrir carpeta", icon="FOLDER_REDIRECT")

        layout.separator()

        # ── GUARDAR ──────────────────────────────────────────────────────
        box_cfgsave = layout.box()
        box_cfgsave.label(text="GUARDAR configuracion actual", icon="FILE_TICK")
        col_cfg = box_cfgsave.column(align=True)
        col_cfg.prop(segs, "config_name", text="Nombre")

        _FORBIDDEN = set('/\\:*?"<>|')
        safe = "".join(c if c not in _FORBIDDEN else "_" for c in segs.config_name).strip()
        box_cfgsave.label(text=f"  -> {safe or 'configuracion'}.json", icon="FILE_BLANK")

        box_cfgsave.label(text=f"  Paso 1+2: {len(pc.path_points)} punto(s) de recorrido", icon="CON_FOLLOWPATH")
        n_segs_total = len(segs.segments)
        n_poses_total = sum(len(s.action_poses) for s in segs.segments)
        box_cfgsave.label(text=f"  Paso 3: {n_segs_total} segmento(s), {n_poses_total} poses de accion", icon="NLA")

        row_cfgsave = box_cfgsave.row()
        row_cfgsave.scale_y = 1.7
        row_cfgsave.operator("rat1seg.save_config", text="  GUARDAR CONFIGURACION  (.json)", icon="FILE_TICK")

        layout.separator()

        # ── IMPORTAR ─────────────────────────────────────────────────────
        box_cfgload = layout.box()
        box_cfgload.label(text="IMPORTAR configuracion guardada", icon="FILE_FOLDER")
        box_cfgload.label(text="  Restaura el recorrido (Paso 1+2) y toda la", icon="INFO")
        box_cfgload.label(text="  secuencia de segmentos, poses, interpolaciones")
        box_cfgload.label(text="  y bloqueador de bones (Paso 3).")

        row_cfgload = box_cfgload.row()
        row_cfgload.scale_y = 1.7
        row_cfgload.operator("rat1seg.load_config", text="  IMPORTAR CONFIGURACION  (.json)", icon="FILE_FOLDER")
