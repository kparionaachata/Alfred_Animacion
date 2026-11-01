# -*- coding: utf-8 -*-
"""
panels.py — Chicken 1 Animation Studio v1.8
Paneles UI: Main, Setup, Sequence, OrganicFilters, EyeExpressions,
Export, ConfigSession, Extract. UIList de slots.
"""
import bpy
import os
from bpy.types import Panel, UIList
from .constants import INTERP_TYPE_ITEMS
from .operators_segments import _calc_seg_frames

class CH1ST_UL_ActionPoses(UIList):
    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.label(text="", icon="POSE_HLT")
            col = row.column()
            col.label(text=item.pose_name)
            sub = row.row()
            sub.alignment = "RIGHT"
            # Mostrar tipo de interpolacion
            sub.label(text=item.interp_type, icon="IPO_BEZIER")
            # Mostrar rotacion si es no-cero
            has_rot = abs(item.rot_x) > 0.01 or abs(item.rot_y) > 0.01 or abs(item.rot_z) > 0.01
            if has_rot:
                sub.label(text=f"r({item.rot_x:.0f},{item.rot_y:.0f},{item.rot_z:.0f})")
            # Frame de inicio manual, si el usuario lo fijo
            if getattr(item, "manual_start", False):
                sub.label(text=f"@f{item.frame_abs_start}", icon="KEYFRAME_HLT")
            sub.label(text=f"{item.duration}f")
        elif self.layout_type == "GRID":
            layout.label(text=item.pose_name)

# =============================================================================
# PANELES
# =============================================================================

class CH1ST_PT_Main(Panel):
    bl_label       = "Chicken 1 Animation Studio"
    bl_idname      = "CH1ST_PT_main"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Chicken1 Studio"
    bl_order       = 1

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Chicken 1 Animation Studio  v1.3", icon="ARMATURE_DATA")
        row_open = layout.row()
        row_open.scale_y = 1.2
        row_open.operator("ch1st.open_chicken_1_blend", text="Abrir alfred.blend", icon="FILE_BLEND")
        row = layout.row()
        row.scale_y = 1.3
        row.alert   = True
        row.operator("ch1st.reset", text="RESET  -  Limpiar escena", icon="TRASH")




class CH1ST_PT_OrganicFilters(Panel):
    bl_label       = "3  Filtros Organicos"
    bl_idname      = "CH1ST_PT_organic"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Chicken1 Studio"
    bl_parent_id   = "CH1ST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        # Se oculta cuando hay segmentos: el panel de segmentos los incluye inline
        segs = getattr(context.scene, "ch1_segs", None)
        if segs is not None and len(segs.segments) > 0:
            return False
        return True

    def draw_header(self, context):
        org = context.scene.ch1st.organic
        self.layout.prop(org, "enabled", text="")

    def draw(self, context):
        layout = self.layout
        st  = context.scene.ch1st
        org = st.organic

        layout.active = org.enabled
        layout.label(text="Post-proceso sobre keyframes generados:", icon="MOD_WAVE")

        # ── Suavizado de fcurves ──
        box = layout.box()
        row = box.row()
        row.prop(org, "smooth_curves_enabled", text="")
        row.label(text="Suavizar fcurves (elimina rigidez)", icon="SMOOTHCURVE")
        if org.smooth_curves_enabled:
            col = box.column(align=True)
            col.prop(org, "smooth_passes",  text="Pasadas")
            col.prop(org, "smooth_factor",  text="Factor", slider=True)

        # ── Respiracion ──
        box = layout.box()
        row = box.row()
        row.prop(org, "breathing_enabled", text="")
        row.label(text="Respiracion (pecho/torso)", icon="FORCE_WIND")
        if org.breathing_enabled:
            col = box.column(align=True)
            col.prop(org, "breathing_amplitude", text="Amplitud")
            col.prop(org, "breathing_speed",     text="Velocidad")
            col.prop(org, "breathing_phase",     text="Fase")

        # ── Aleteo de alas ──
        box = layout.box()
        row = box.row()
        row.prop(org, "flap_enabled", text="")
        row.label(text="Aleteo de alas (Scapula/Shoulder/Elbow)", icon="MOD_ARRAY")
        if org.flap_enabled:
            col = box.column(align=True)
            col.prop(org, "flap_amplitude", text="Amplitud")
            col.prop(org, "flap_speed",     text="Velocidad")
            col.prop(org, "flap_openness",  text="Apertura base")
            col.prop(org, "flap_asymmetry", text="Asimetria L/R")

        # ── Cabeceo / picoteo ──
        box = layout.box()
        row = box.row()
        row.prop(org, "head_sway_enabled", text="")
        row.label(text="Cabeceo / picoteo (Neck/Head/Jaw)", icon="BONE_DATA")
        if org.head_sway_enabled:
            col = box.column(align=True)
            col.prop(org, "head_sway_amplitude", text="Amplitud")
            col.prop(org, "head_sway_speed",     text="Velocidad")
            col.prop(org, "head_sway_seed",      text="Semilla")

        # ── Balanceo de peso ──
        box = layout.box()
        row = box.row()
        row.prop(org, "weight_shift_enabled", text="")
        row.label(text="Balanceo de peso (patas)", icon="CON_LOCLIKE")
        if org.weight_shift_enabled:
            col = box.column(align=True)
            col.prop(org, "weight_shift_amplitude", text="Amplitud")
            col.prop(org, "weight_shift_speed",     text="Velocidad")

        # ── Noise de alas (temblor de plumas) ──
        box = layout.box()
        row = box.row()
        row.prop(org, "shoulder_noise_enabled", text="")
        row.label(text="Noise de alas (Scapula L/R)", icon="MOD_NOISE")
        if org.shoulder_noise_enabled:
            col = box.column(align=True)
            col.prop(org, "shoulder_noise_amplitude", text="Amplitud")
            col.prop(org, "shoulder_noise_speed",     text="Velocidad")
            col.prop(org, "shoulder_noise_seed",      text="Semilla")

        # ── Follow-through de alas ──
        box = layout.box()
        row = box.row()
        row.prop(org, "secondary_motion_enabled", text="")
        row.label(text="Follow-through de alas (Elbow L/R)", icon="CON_FOLLOWPATH")
        if org.secondary_motion_enabled:
            col = box.column(align=True)
            col.prop(org, "secondary_motion_lag",     text="Retardo (frames)")
            col.prop(org, "secondary_motion_damping", text="Amortiguacion", slider=True)

        # ── Micro-escala ──
        box = layout.box()
        row = box.row()
        row.prop(org, "micro_scale_enabled", text="")
        row.label(text="Micro-escala pecho (Chest)", icon="FULLSCREEN_ENTER")
        if org.micro_scale_enabled:
            box.prop(org, "micro_scale_amplitude", text="Amplitud")

        # ── Noise ROOT ──
        box = layout.box()
        row = box.row()
        row.prop(org, "root_noise_enabled", text="")
        row.label(text="Noise posicion ROOT (chicken_1)", icon="EMPTY_AXIS")
        if org.root_noise_enabled:
            col = box.column(align=True)
            col.prop(org, "root_noise_strength",   text="Intensidad")
            col.prop(org, "root_noise_frequency",  text="Frecuencia")
            col.prop(org, "root_noise_seed",       text="Semilla")

        layout.separator()
        layout.label(text="Los filtros se aplican al presionar CONCATENAR", icon="INFO")




class CH1ST_PT_Export(Panel):
    bl_label       = "3  Exportar / Importar"
    bl_idname      = "CH1ST_PT_export"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Chicken1 Studio"
    bl_parent_id   = "CH1ST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        st     = context.scene.ch1st

        box = layout.box()
        box.label(text="Exportar slot_NNN_tipo.py", icon="EXPORT")
        col = box.column(align=True)
        col.prop(st, "export_slot_number", text="Numero de slot")
        col.prop(st, "export_type",  text="Tipo movimiento  (ej: arrodillarse)")
        col.prop(st, "export_desc",  text="Descripcion")

        # ── Alcance de exportacion ────────────────────────────────────────────
        box_scope = box.box()
        box_scope.label(text="Alcance de exportacion:", icon="CAMERA_DATA")
        row_scope = box_scope.row(align=True)
        row_scope.prop(st, "export_scope", expand=True)

        # Info contextual segun el scope elegido
        scope = st.export_scope
        if scope == "ACTIVE":
            try:
                seg_cfg = context.scene.ch1_segs
                segs    = seg_cfg.segments
                if segs and 0 <= seg_cfg.active_index < len(segs):
                    seg = segs[seg_cfg.active_index]
                    box_scope.label(
                        text=f"  Segmento: \"{seg.label}\"   frames {seg.frame_start} → {seg.frame_end}",
                        icon="INFO",
                    )
                else:
                    box_scope.label(text="  (sin segmento activo en Paso 3)", icon="ERROR")
            except Exception:
                box_scope.label(text="  (sin segmento activo en Paso 3)", icon="ERROR")
        elif scope == "SELECTED":
            try:
                seg_cfg  = context.scene.ch1_segs
                marcados = [s for s in seg_cfg.segments if s.export_selected]
                if marcados:
                    f_min = min(s.frame_start for s in marcados)
                    f_max = max(s.frame_end   for s in marcados)
                    box_scope.label(
                        text=f"  {len(marcados)} segmento(s) marcado(s)   frames {f_min} → {f_max}",
                        icon="INFO",
                    )
                else:
                    box_scope.label(text="  (ningun segmento tiene 'Exportar' activado)", icon="ERROR")
            except Exception:
                box_scope.label(text="  (sin segmentos en Paso 3)", icon="ERROR")
        else:  # FULL
            try:
                pc_disp  = context.scene.ch1_path
                n_p      = len(pc_disp.path_points)
                sf       = pc_disp.frame_inicio
                if n_p <= 1:
                    ef   = max(pc_disp.frame_fin_manual, sf + 1)
                    modo_txt = "1 coordenada — frame fin manual"
                else:
                    ef   = pc_disp.anim_frame_fin if pc_disp.anim_frame_fin > 0 else 0
                    modo_txt = f"recorrido {n_p} puntos"
                if ef > 0:
                    box_scope.label(
                        text=f"  {modo_txt}   frames {sf} → {ef}   ({ef - sf + 1} fr)",
                        icon="INFO",
                    )
                else:
                    box_scope.label(
                        text=f"  {modo_txt}   (ejecuta el Paso 2 primero)",
                        icon="ERROR",
                    )
            except Exception:
                box_scope.label(
                    text=f"  Frames {st.start_frame} → {st.end_frame_gen}   ({st.total_frames_gen} frames)",
                    icon="INFO",
                )

        # Preview del nombre de archivo
        sn   = f"{st.export_slot_number:03d}"
        tp   = st.export_type.strip() or "custom"
        box.label(text=f"  -> slot_{sn}_{tp}.py", icon="FILE_SCRIPT")

        # ── Info Paso 1 y Paso 2 ──────────────────────────────────────────
        try:
            pc     = context.scene.ch1_path
            n_pts  = len(pc.path_points)
            modo   = "1 coordenada  (parado/idle)" if n_pts <= 1 else f"recorrido  ({n_pts} puntos)"
            box_p  = box.box()
            box_p.label(text=f"Paso 1 — Modo: {modo}", icon="CON_FOLLOWPATH")
            bname  = os.path.basename(pc.blend_filepath) if pc.blend_filepath else "(sin seleccionar)"
            box_p.label(text=f"  Personaje: {bname}", icon="ARMATURE_DATA")
            box_p.label(text=f"Paso 2 — Slot {pc.slot_inicio}   Frames {pc.frame_inicio} → {pc.frame_fin_manual}", icon="SETTINGS")
            _carpeta_nombre = os.path.basename(pc.output_dir.rstrip('/\\')) if pc.output_dir else "(sin definir)"
            box_p.label(text=f"  Orientacion Z: {pc.root_rot_z:.1f}°   |   Carpeta: {_carpeta_nombre}", icon="FILE_FOLDER")
        except Exception:
            box.label(text="  Paso 1/2: (datos no disponibles)", icon="INFO")

        # Indicar si ojos seran incluidos
        eye_s = st.eye_expr
        if eye_s.enabled:
            box_eye = box.box()
            box_eye.label(text="  Ojos (panel 2b): INCLUIDOS en el .py", icon="HIDE_OFF")
            box_eye.label(text=f"  {len(st.eye_slots)} slots intermedios  |  parpadeo: {'SI' if eye_s.blink_enabled else 'NO'}  |  expr: {'SI' if eye_s.expr_intervals_enabled else 'NO'}", icon="INFO")
        else:
            box.label(text="  Ojos (panel 2b): desactivados", icon="HIDE_ON")

        row = box.row()
        row.scale_y = 1.6
        row.enabled = st.anim_generated
        row.operator("ch1st.export_animation", text="EXPORTAR slot_NNN_tipo.py", icon="FILE_SCRIPT")
        if not st.anim_generated:
            box.label(text="  Genera la animacion primero", icon="INFO")
        if st.last_export_path:
            box.label(text=f"  OK: {os.path.basename(st.last_export_path)}", icon="CHECKMARK")

        layout.separator()

        box = layout.box()
        box.label(text="Importar animacion .py", icon="IMPORT")
        row = box.row()
        row.scale_y = 1.4
        row.operator("ch1st.import_animation", text="Seleccionar .py...", icon="FILE_FOLDER")

class CH1ST_PT_ConfigSession(Panel):
    bl_label       = "5  Guardar / Importar Configuracion"
    bl_idname      = "CH1ST_PT_config_session"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Chicken1 Studio"
    bl_parent_id   = "CH1ST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        st     = context.scene.ch1st

        # ─── Informacion: que es esta funcion ───
        box_info = layout.box()
        box_info.label(text="Guardar / recuperar sesion de trabajo", icon="BOOKMARKS")
        box_info.label(text="  Exporta la SECUENCIA completa como .json:", icon="INFO")
        box_info.label(text="  Poses, rotaciones, posiciones del root,")
        box_info.label(text="  interpolaciones, duraciones y filtros organicos.")
        box_info.label(text="  (No es la animacion acabada .py)")

        layout.separator()

        # ─── Carpeta de configuraciones ───
        box_dir = layout.box()
        box_dir.label(text="Carpeta de configuraciones", icon="FILEBROWSER")
        box_dir.prop(st, "config_dir", text="")
        box_dir.operator("ch1st.open_config_folder",
                         text="Abrir carpeta", icon="FOLDER_REDIRECT")

        layout.separator()

        # ─── GUARDAR ───
        box_save = layout.box()
        box_save.label(text="GUARDAR configuracion actual", icon="FILE_TICK")

        col = box_save.column(align=True)
        col.prop(st, "config_name", text="Nombre")

        # Preview nombre de archivo
        _FORBIDDEN = set('/\\:*?"<>|')
        safe = "".join(c if c not in _FORBIDDEN else "_" for c in st.config_name).strip()
        fname_preview = f"{safe or 'configuracion'}.json"
        box_save.label(text=f"  -> {fname_preview}", icon="FILE_BLANK")

        # Resumen de lo que se guardara
        n_act  = len(st.action_poses)
        box_save.label(
            text=f"  Secuencia: {n_act} poses de accion",
            icon="NLA"
        )

        row_save = box_save.row()
        row_save.scale_y = 1.7
        row_save.operator("ch1st.save_config",
                          text="  GUARDAR CONFIGURACION  (.json)", icon="FILE_TICK")

        layout.separator()

        # ─── IMPORTAR ───
        box_load = layout.box()
        box_load.label(text="IMPORTAR configuracion guardada", icon="FILE_FOLDER")
        box_load.label(text="  Restaura toda la secuencia de poses,", icon="INFO")
        box_load.label(text="  interpolaciones y ajustes de la sesion.")

        row_load = box_load.row()
        row_load.scale_y = 1.7
        row_load.operator("ch1st.load_config",
                          text="  IMPORTAR CONFIGURACION  (.json)", icon="FILE_FOLDER")


class CH1ST_PT_Extract(Panel):
    bl_label       = "4  Extraer Nueva Pose"
    bl_idname      = "CH1ST_PT_extract"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Chicken1 Studio"
    bl_parent_id   = "CH1ST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        st     = context.scene.ch1st
        scene  = context.scene

        box = layout.box()
        box.label(text="Capturar pose del frame", icon="BONE_DATA")
        col = box.column(align=True)
        col.prop(st, "extract_use_current", text="Usar frame actual del timeline")
        if st.extract_use_current:
            col.label(text=f"  Frame actual: {scene.frame_current}", icon="TIME")
        else:
            col.prop(st, "extract_frame", text="Frame especifico")

        row = col.row(align=True)
        row.operator("screen.frame_jump",    text="", icon="REW").end       = False
        row.operator("screen.keyframe_jump", text="", icon="PREV_KEYFRAME").next = False
        row.operator("screen.keyframe_jump", text="", icon="NEXT_KEYFRAME").next = True
        row.operator("screen.frame_jump",    text="", icon="FF").end        = True

        col.separator()
        col.label(text="Nombre de la nueva pose:")
        col.prop(st, "extract_label", text="")

        row = box.row()
        row.scale_y = 1.6
        row.operator("ch1st.extract_pose", text="GUARDAR COMO NUEVA POSE", icon="PINNED")

        # Boton actualizar poses (para que la nueva pose aparezca en los selectores)
        row2 = box.row(align=True)
        row2.scale_y = 1.2
        row2.operator("ch1st.refresh_poses", text="Actualizar lista de poses", icon="FILE_REFRESH")
        row2.operator("ch1st.import_pose", text="Importar pose", icon="IMPORT")

        row3 = box.row()
        row3.scale_y = 1.4
        row3.operator("ch1st.apply_imported_pose", text="EJECUTAR POSE EN EL PERSONAJE", icon="PLAY")

        _FORBIDDEN = set('/\\:*?"<>|')
        safe_label = "".join(
            c if c not in _FORBIDDEN else "_" for c in st.extract_label
        ).strip().replace(" ", "_")
        display_name = f"{safe_label}.json" if safe_label else "<nombre>.json"
        box.label(text=f"  -> {display_name}", icon="INFO")



# =============================================================================
# UIList para los slots de ojos
# =============================================================================
# UIList para los slots de ojos
# =============================================================================

class CH1ST_UL_EyeLibEntries(UIList):
    """UIList para la libreria de expresiones de ojos"""
    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.label(text="", icon="ASSET_MANAGER")
            row.label(text=item.name)
        elif self.layout_type == "GRID":
            layout.label(text=item.name)


class CH1ST_UL_EyeSlots(UIList):
    """Lista de estados de ojos intermedios"""
    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.label(text="", icon="HIDE_OFF")
            col = row.column()
            col.label(text=item.slot_label)
            sub = row.row()
            sub.alignment = "RIGHT"
            sub.label(text=item.interp_type, icon="IPO_BEZIER")
            sub.label(text=item.active_expression.capitalize(), icon="MESH_CIRCLE")
            sub.label(text=f"{item.duration}f")
        elif self.layout_type == "GRID":
            layout.label(text=item.slot_label)


class CH1ST_UL_BlinkIntervals(UIList):
    """Lista de intervalos de parpadeo automatico"""
    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.prop(item, "enabled", text="",
                     icon="HIDE_OFF" if item.enabled else "HIDE_ON")
            row.label(text=item.label, icon="SEQUENCE")
            sub = row.row()
            sub.alignment = "RIGHT"
            sub.label(text=f"{item.frame_start}→{item.frame_end}")
            sub.label(text=f"x{item.blink_count}")
        elif self.layout_type == "GRID":
            layout.label(text=item.label)


class CH1ST_UL_EyeExprIntervals(UIList):
    """Lista de intervalos de expresiones de ojos"""
    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.prop(item, "enabled", text="",
                     icon="HIDE_OFF" if item.enabled else "HIDE_ON")
            row.label(text=item.label, icon="SHAPEKEY_DATA")
            sub = row.row()
            sub.alignment = "RIGHT"
            sub.label(text=item.expression.capitalize(), icon="MESH_CIRCLE")
            sub.label(text=f"{item.frame_start}|{item.frame_peak}|{item.frame_end}")
        elif self.layout_type == "GRID":
            layout.label(text=item.label)


# =============================================================================
# HELPERS DE DIBUJO
# =============================================================================

def _draw_eye_state_transforms(layout, data_src, prefix_or_item, is_item=False):
    """
    Dibuja Expresion + Geometria + Loc/Rot/Sca para ambos ojos.
    Si is_item=True, data_src es el Chicken1EyeSlotItem (acceso directo a atributos).
    Si is_item=False, data_src es st y se usa prefix 'start'/'end' con f-string.
    """
    if is_item:
        item = data_src

        box_expr = layout.box()
        box_expr.label(text="Expresion", icon="HIDE_OFF")
        col = box_expr.column(align=True)
        col.prop(item, "active_expression", text="")
        col.prop(item, "expression_value",  text="Valor", slider=True)

        box_geo = layout.box()
        box_geo.label(text="Geometria / Forma", icon="MESH_CIRCLE")
        col = box_geo.column(align=True)
        col.prop(item, "geo_edit_mode",  text="Forma")
        col.prop(item, "geo_intensity",  text="Intensidad", slider=True)

        sub_L = layout.box()
        sub_L.label(text="Ojo Izquierdo", icon="BLANK1")
        col = sub_L.column(align=True)
        col.label(text="Posicion", icon="EMPTY_AXIS")
        row = col.row(align=True); row.prop(item, "eye_L_loc_x", text="X"); row.prop(item, "eye_L_loc_y", text="Y"); row.prop(item, "eye_L_loc_z", text="Z")
        col.label(text="Rotacion", icon="ORIENTATION_GIMBAL")
        row2 = col.row(align=True); row2.prop(item, "eye_L_rot_x", text="X"); row2.prop(item, "eye_L_rot_y", text="Y"); row2.prop(item, "eye_L_rot_z", text="Z")
        col.label(text="Escala", icon="FULLSCREEN_ENTER")
        row3 = col.row(align=True); row3.prop(item, "eye_L_sca_x", text="X"); row3.prop(item, "eye_L_sca_y", text="Y"); row3.prop(item, "eye_L_sca_z", text="Z")

        sub_R = layout.box()
        sub_R.label(text="Ojo Derecho", icon="BLANK1")
        col = sub_R.column(align=True)
        col.label(text="Posicion", icon="EMPTY_AXIS")
        row = col.row(align=True); row.prop(item, "eye_R_loc_x", text="X"); row.prop(item, "eye_R_loc_y", text="Y"); row.prop(item, "eye_R_loc_z", text="Z")
        col.label(text="Rotacion", icon="ORIENTATION_GIMBAL")
        row2 = col.row(align=True); row2.prop(item, "eye_R_rot_x", text="X"); row2.prop(item, "eye_R_rot_y", text="Y"); row2.prop(item, "eye_R_rot_z", text="Z")
        col.label(text="Escala", icon="FULLSCREEN_ENTER")
        row3 = col.row(align=True); row3.prop(item, "eye_R_sca_x", text="X"); row3.prop(item, "eye_R_sca_y", text="Y"); row3.prop(item, "eye_R_sca_z", text="Z")

    else:
        st = data_src
        p  = prefix_or_item

        box_expr = layout.box()
        box_expr.label(text="Expresion", icon="HIDE_OFF")
        col = box_expr.column(align=True)
        col.prop(st, f"eye_{p}_expression", text="")
        col.prop(st, f"eye_{p}_expr_value", text="Valor", slider=True)

        box_geo = layout.box()
        box_geo.label(text="Geometria / Forma", icon="MESH_CIRCLE")
        col = box_geo.column(align=True)
        col.prop(st, f"eye_{p}_geo_mode",      text="Forma")
        col.prop(st, f"eye_{p}_geo_intensity",  text="Intensidad", slider=True)

        sub_L = layout.box()
        sub_L.label(text="Ojo Izquierdo  —  base: (0.1066, 0.2705, 1.7008)", icon="BLANK1")
        col = sub_L.column(align=True)
        col.label(text="Posicion", icon="EMPTY_AXIS")
        row = col.row(align=True); row.prop(st, f"eye_{p}_L_loc_x", text="X"); row.prop(st, f"eye_{p}_L_loc_y", text="Y"); row.prop(st, f"eye_{p}_L_loc_z", text="Z")
        col.label(text="Rotacion", icon="ORIENTATION_GIMBAL")
        row2 = col.row(align=True); row2.prop(st, f"eye_{p}_L_rot_x", text="X"); row2.prop(st, f"eye_{p}_L_rot_y", text="Y"); row2.prop(st, f"eye_{p}_L_rot_z", text="Z")
        col.label(text="Escala", icon="FULLSCREEN_ENTER")
        row3 = col.row(align=True); row3.prop(st, f"eye_{p}_L_sca_x", text="X"); row3.prop(st, f"eye_{p}_L_sca_y", text="Y"); row3.prop(st, f"eye_{p}_L_sca_z", text="Z")

        sub_R = layout.box()
        sub_R.label(text="Ojo Derecho  —  base: (-0.1053, 0.2563, 1.7004)", icon="BLANK1")
        col = sub_R.column(align=True)
        col.label(text="Posicion", icon="EMPTY_AXIS")
        row = col.row(align=True); row.prop(st, f"eye_{p}_R_loc_x", text="X"); row.prop(st, f"eye_{p}_R_loc_y", text="Y"); row.prop(st, f"eye_{p}_R_loc_z", text="Z")
        col.label(text="Rotacion", icon="ORIENTATION_GIMBAL")
        row2 = col.row(align=True); row2.prop(st, f"eye_{p}_R_rot_x", text="X"); row2.prop(st, f"eye_{p}_R_rot_y", text="Y"); row2.prop(st, f"eye_{p}_R_rot_z", text="Z")
        col.label(text="Escala", icon="FULLSCREEN_ENTER")
        row3 = col.row(align=True); row3.prop(st, f"eye_{p}_R_sca_x", text="X"); row3.prop(st, f"eye_{p}_R_sca_y", text="Y"); row3.prop(st, f"eye_{p}_R_sca_z", text="Z")


# =============================================================================
# HELPER: leer bones desde historia_chicken_1 JSON
# =============================================================================

def _get_bones_from_historia(context):
    """
    Lee el archivo historia_*.json configurado en el panel y extrae
    la lista de bones desde rig_info.categorias_animacion.completo.
    Si esa clave no existe, aplana bones_principales.
    Devuelve lista de strings o [] si falla.
    """
    import bpy, json, os
    try:
        st = context.scene.ch1st
        filepath = bpy.path.abspath(st.historia_json)
        if not filepath or not os.path.isfile(filepath):
            return []
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        rig = data.get("rig_info", {})

        # Fuente 1: categorias_animacion.completo
        completo = rig.get("categorias_animacion", {}).get("completo", [])
        if completo and isinstance(completo, list):
            return [b for b in completo if isinstance(b, str)]

        # Fuente 2: aplanar bones_principales
        bp = rig.get("bones_principales", {})
        bones = []
        def _flatten(obj):
            if isinstance(obj, list):
                for item in obj: _flatten(item)
            elif isinstance(obj, dict):
                for v in obj.values(): _flatten(v)
            elif isinstance(obj, str):
                if obj not in bones: bones.append(obj)
        _flatten(bp)
        return bones

    except Exception as e:
        print(f"[AlfredStudio] _get_bones_from_historia error: {e}")
        return []


def _get_bones_from_chicken_1_json(context):
    """
    Lee el JSON de Alfred (historia_json) y extrae la lista de bones
    desde la estructura real del archivo:
      collections.scene_collection.objects[N].bone_hierarchy  (árbol recursivo)
    Filtra los bones cuyo nombre empiece con 'no_bone'.
    Compatible con el formato generado por alfred_animation_studio.
    """
    import bpy, json, os

    def _flatten_bone_hierarchy(nodes):
        result = []
        for node in nodes:
            name = node.get("name", "")
            if name and not name.lower().startswith("no_bone"):
                result.append(name)
            children = node.get("children", [])
            if children:
                result.extend(_flatten_bone_hierarchy(children))
        return result

    try:
        st = context.scene.ch1st
        filepath = bpy.path.abspath(st.historia_json)
        if not filepath or not os.path.isfile(filepath):
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Fuente 1: rig_info.categorias_animacion.completo (formato antiguo)
        rig = data.get("rig_info", {})
        completo = rig.get("categorias_animacion", {}).get("completo", [])
        if completo and isinstance(completo, list):
            return [b for b in completo if isinstance(b, str)]

        # Fuente 2: aplanar bones_principales (formato antiguo alternativo)
        bp = rig.get("bones_principales", {})
        if bp:
            bones = []
            def _flatten_bp(obj):
                if isinstance(obj, list):
                    for item in obj: _flatten_bp(item)
                elif isinstance(obj, dict):
                    for v in obj.values(): _flatten_bp(v)
                elif isinstance(obj, str):
                    if obj not in bones: bones.append(obj)
            _flatten_bp(bp)
            if bones:
                return bones

        # Fuente 3: collections.scene_collection.objects[N].bone_hierarchy (formato actual)
        objects = (data
                   .get("collections", {})
                   .get("scene_collection", {})
                   .get("objects", []))
        for obj in objects:
            if obj.get("type") == "ARMATURE":
                hier = obj.get("bone_hierarchy", [])
                if hier:
                    return _flatten_bone_hierarchy(hier)

        return []

    except Exception as e:
        print(f"[AlfredStudio] _get_bones_from_chicken_1_json error: {e}")
        return []


# =============================================================================
# PANEL: OSCILACIONES DE BONES (Alfred)
# =============================================================================

class CH1ST_PT_BoneOscillations(Panel):
    bl_label       = "3b  Oscilaciones de Bones"
    bl_idname      = "CH1ST_PT_bone_osc"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Chicken1 Studio"
    bl_parent_id   = "CH1ST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        segs = getattr(context.scene, "ch1_segs", None)
        if segs is not None and len(segs.segments) > 0:
            return False
        return True

    def draw_header(self, context):
        osc = context.scene.ch1st.bone_oscillations
        self.layout.prop(osc, "enabled", text="")

    def draw(self, context):
        layout = self.layout
        st  = context.scene.ch1st
        osc = st.bone_oscillations

        layout.active = osc.enabled

        # ── LISTA DE OSCILACIONES EXISTENTES ────────────────────────────────
        box_list = layout.box()
        box_list.label(text="Lista de oscilaciones:", icon="NLA")

        if osc.items:
            for i, item in enumerate(osc.items):
                is_selected = (i == osc.active_idx)
                row_item = box_list.row(align=True)

                icon_sel = "RADIOBUT_ON" if is_selected else "RADIOBUT_OFF"
                op_sel = row_item.operator("ch1st.bone_osc_toggle_item", text="", icon=icon_sel, emboss=False)
                op_sel.item_idx = i

                icon_en = "HIDE_OFF" if item.enabled else "HIDE_ON"
                op_en = row_item.operator("ch1st.bone_osc_toggle_item", text="", icon=icon_en)
                op_en.item_idx = i

                wave_icon = {"SINE": "MOD_WAVE", "TRIANGLE": "GRAPH",
                             "SQUARE": "SNAP_INCREMENT", "NOISE": "MOD_NOISE"}.get(item.wave_type, "MOD_WAVE")
                axes_str = "".join(a for a, b in [("X", item.axis_x), ("Y", item.axis_y), ("Z", item.axis_z)] if b) or "?"
                label_text = (
                    f"  {item.label or item.bone_name}  [{item.bone_name}]  "
                    f"{axes_str}  \xb1{item.amplitude:.0f}\xb0  {item.frame_start}\u2192{item.frame_end}"
                )
                row_item.label(text=label_text[:56], icon=wave_icon)

                op_dup = row_item.operator("ch1st.bone_osc_duplicate_item", text="", icon="DUPLICATE")
                op_dup.item_idx = i
                op_del = row_item.operator("ch1st.bone_osc_remove_item", text="", icon="X")
                op_del.item_idx = i

            if len(osc.items) > 1:
                row_move = box_list.row(align=True)
                op_up = row_move.operator("ch1st.bone_osc_move_item", text="Subir",  icon="TRIA_UP")
                op_up.direction = "UP"
                op_dn = row_move.operator("ch1st.bone_osc_move_item", text="Bajar",  icon="TRIA_DOWN")
                op_dn.direction = "DOWN"
        else:
            box_list.label(text="  (sin oscilaciones — agrega una abajo)", icon="INFO")

        layout.separator()

        # ── EDITOR DE NUEVA OSCILACION ───────────────────────────────────────
        box_edit = layout.box()
        box_edit.label(text="Nueva oscilacion:", icon="ADD")

        col = box_edit.column(align=True)
        col.prop(osc, "edit_label",     text="Etiqueta")
        col.prop(osc, "edit_bone_name", text="Bone")

        # ── BONES DETECTADOS DESDE historia_chicken_1_2.json ───────────────────
        bones_json = _get_bones_from_historia(context)
        box_bones = box_edit.box()

        if bones_json:
            import bpy as _bpy, os as _os
            json_name = _os.path.basename(_bpy.path.abspath(st.historia_json))
            row_bh = box_bones.row()
            row_bh.label(text=f"Bones del personaje  ({json_name}):", icon="BONE_DATA")
            grid = box_bones.grid_flow(row_major=True, columns=2, align=True)
            for bone_name in bones_json:
                op_b = grid.operator("ch1st.bone_osc_pick_bone", text=bone_name, emboss=True)
                op_b.bone_name = bone_name
        else:
            box_bones.label(text="  Sin bones detectados", icon="ERROR")
            box_bones.label(text="  Verifica la ruta del JSON en Configuracion", icon="INFO")
            box_bones.label(text="  (tambien puedes escribir el nombre manualmente)", icon="INFO")

        box_edit.separator()

        row_frames = box_edit.row(align=True)
        row_frames.prop(osc, "edit_frame_start", text="Inicio")
        row_frames.prop(osc, "edit_frame_end",   text="Fin")

        row_axis = box_edit.row(align=True)
        row_axis.label(text="Ejes:")
        row_axis.prop(osc, "edit_axis_x", toggle=True)
        row_axis.prop(osc, "edit_axis_y", toggle=True)
        row_axis.prop(osc, "edit_axis_z", toggle=True)

        box_edit.separator()

        col_ang = box_edit.column(align=True)
        col_ang.label(text="Rango angular:", icon="DRIVER_ROTATIONAL_DIFFERENCE")
        col_ang.prop(osc, "edit_amplitude",    text="Amplitud (grad)")
        col_ang.prop(osc, "edit_angle_offset", text="Offset base (grad)")

        box_edit.separator()

        col_wave = box_edit.column(align=True)
        col_wave.label(text="Oscilacion:", icon="MOD_WAVE")
        col_wave.prop(osc, "edit_num_cycles", text="Numero de ciclos")
        col_wave.prop(osc, "edit_wave_type",  text="Transicion")
        col_wave.prop(osc, "edit_phase",      text="Fase (rad)")
        if osc.edit_wave_type == "NOISE":
            col_wave.prop(osc, "edit_noise_seed", text="Semilla noise")

        box_edit.separator()

        col_fade = box_edit.column(align=True)
        col_fade.label(text="Transicion suave:", icon="SMOOTHCURVE")
        row_fade = col_fade.row(align=True)
        row_fade.prop(osc, "edit_fade_in",  text="Fade in (fr)")
        row_fade.prop(osc, "edit_fade_out", text="Fade out (fr)")

        box_edit.separator()

        dur_frames = max(1, osc.edit_frame_end - osc.edit_frame_start)
        axes_sel = "".join(a for a, b in [("X", osc.edit_axis_x), ("Y", osc.edit_axis_y), ("Z", osc.edit_axis_z)] if b) or "(sin eje)"
        box_edit.label(
            text=f"  {osc.edit_num_cycles} ciclos en {dur_frames} frames  |  ejes: {axes_sel}  |  bone: {osc.edit_bone_name or '(sin definir)'}",
            icon="INFO",
        )

        row_add = box_edit.row()
        row_add.scale_y = 1.4
        row_add.active_default = True
        op_add = row_add.operator("ch1st.bone_osc_add_item", text="+ Agregar oscilacion", icon="CHECKMARK")
        op_add.quick_bone = ""

        layout.separator()
        layout.label(text="Las oscilaciones se aplican al presionar CONCATENAR", icon="INFO")


# =============================================================================
# PANEL: IMPORTACION DE OBJETOS (armas, escudos, props)
# =============================================================================

class CH1ST_PT_ObjectImports(Panel):
    bl_label       = "3c  Importacion de Objetos"
    bl_idname      = "CH1ST_PT_object_imports"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Chicken1 Studio"
    bl_parent_id   = "CH1ST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        segs = getattr(context.scene, "ch1_segs", None)
        if segs is not None and len(segs.segments) > 0:
            return False
        return True

    def draw_header(self, context):
        oi = context.scene.ch1st.object_imports
        self.layout.prop(oi, "enabled", text="")

    def draw(self, context):
        layout = self.layout
        st = context.scene.ch1st
        oi = st.object_imports

        layout.active = oi.enabled

        # ── LISTA DE OBJETOS ─────────────────────────────────────────────────
        box_list = layout.box()
        box_list.label(text="Lista de objetos a importar:", icon="OBJECT_DATA")

        if oi.items:
            for i, item in enumerate(oi.items):
                is_selected = (i == oi.active_idx)
                row_item = box_list.row(align=True)

                icon_sel = "RADIOBUT_ON" if is_selected else "RADIOBUT_OFF"
                op_sel = row_item.operator("ch1st.obj_import_toggle_item", text="", icon=icon_sel, emboss=False)
                op_sel.item_idx = i

                icon_en = "HIDE_OFF" if item.enabled else "HIDE_ON"
                op_en = row_item.operator("ch1st.obj_import_toggle_item", text="", icon=icon_en)
                op_en.item_idx = i

                _ti = getattr(item, 'transition_in',  'NONE')
                _to = getattr(item, 'transition_out', 'NONE')
                _trans_str = ""
                if _ti != 'NONE':
                    _trans_str += f" ↑{_ti}"
                if _to != 'NONE':
                    _trans_str += f" ↓{_to}"
                label_text = (
                    f"  {item.label or item.object_name}"
                    f"  [{item.object_name}]"
                    f"  {item.frame_start}\u2192{item.frame_end}"
                    + _trans_str
                )
                row_item.label(text=label_text[:64], icon="IMPORT")

                op_edit = row_item.operator("ch1st.obj_import_load_to_editor", text="", icon="GREASEPENCIL")
                op_edit.item_idx = i
                op_dup = row_item.operator("ch1st.obj_import_duplicate_item", text="", icon="DUPLICATE")
                op_dup.item_idx = i
                op_del = row_item.operator("ch1st.obj_import_remove_item", text="", icon="X")
                op_del.item_idx = i

            if len(oi.items) > 1:
                row_move = box_list.row(align=True)
                op_up = row_move.operator("ch1st.obj_import_move_item", text="Subir",  icon="TRIA_UP")
                op_up.direction = "UP"
                op_dn = row_move.operator("ch1st.obj_import_move_item", text="Bajar",  icon="TRIA_DOWN")
                op_dn.direction = "DOWN"
        else:
            box_list.label(text="  (sin objetos — agrega uno abajo)", icon="INFO")

        layout.separator()

        # ── EDITOR DE NUEVO / EDITAR OBJETO ──────────────────────────────────
        is_editing = 0 <= oi.active_idx < len(oi.items)
        box_edit = layout.box()
        box_edit.label(
            text=f"Editar objeto #{oi.active_idx + 1}:" if is_editing else "Nuevo objeto:",
            icon="GREASEPENCIL" if is_editing else "ADD"
        )

        col = box_edit.column(align=True)
        col.prop(oi, "edit_label",          text="Etiqueta")
        col.separator()

        row_browse = box_edit.row(align=True)
        row_browse.scale_y = 1.2
        row_browse.operator("ch1st.obj_import_browse_blend", text="Buscar .blend...", icon="FILEBROWSER")

        col.prop(oi, "edit_object_folder",  text="Carpeta")
        col.prop(oi, "edit_blend_filename", text="Archivo .blend")
        col.prop(oi, "edit_object_name",    text="Nombre objeto")

        row_preview = box_edit.row(align=True)
        row_preview.scale_y = 1.2
        row_preview.operator("ch1st.obj_import_preview_now", text="Importar .blend al Outliner", icon="IMPORT")

        box_edit.separator()

        row_frames = box_edit.row(align=True)
        row_frames.prop(oi, "edit_frame_start", text="Inicio")
        row_frames.prop(oi, "edit_frame_end",   text="Fin")

        box_edit.separator()

        col_par = box_edit.column(align=True)
        col_par.label(text="Parenteo:", icon="BONE_DATA")
        row_arm = col_par.row(align=True)
        row_arm.prop(oi, "edit_parent_armature", text="Armature")
        row_arm.operator("ch1st.obj_import_detect_armature", text="", icon="VIEWZOOM")
        col_par.prop(oi, "edit_parent_bone",     text="Bone")

        box_edit.separator()

        col_tr = box_edit.column(align=True)
        col_tr.label(text="Transformacion:", icon="OBJECT_ORIGIN")
        row_loc = col_tr.row(align=True)
        row_loc.prop(oi, "edit_loc_x", text="X")
        row_loc.prop(oi, "edit_loc_y", text="Y")
        row_loc.prop(oi, "edit_loc_z", text="Z")
        col_tr.label(text="Rotacion (grados):", icon="DRIVER_ROTATIONAL_DIFFERENCE")
        row_rot = col_tr.row(align=True)
        row_rot.prop(oi, "edit_rot_x", text="X")
        row_rot.prop(oi, "edit_rot_y", text="Y")
        row_rot.prop(oi, "edit_rot_z", text="Z")
        col_tr.prop(oi, "edit_scale_uniform", text="Escala uniforme")

        box_edit.separator()
        box_edit.prop(oi, "edit_levels_up", text="Niveles arriba (proyecto)")

        box_edit.separator()
        col_seg = box_edit.column(align=True)
        col_seg.label(text="Segmento:", icon="SEQUENCE")
        col_seg.prop(oi, "edit_segment_idx", text="Indice (-1 = global)")
        col_seg.label(
            text="  -1 = se ejecuta con el CONCATENAR de cualquier segmento. "
                 "0,1,2... = solo con el CONCATENAR de ese segmento (numero en la lista, empieza en 0).",
            icon="INFO"
        )

        box_edit.separator()

        # ── Transiciones ─────────────────────────────────────────────────
        box_trans = box_edit.box()
        row_trans_hdr = box_trans.row(align=True)
        row_trans_hdr.label(text="Transiciones cartoon:", icon="ANIM")

        # --- Aparicion ---
        col_ti = box_trans.column(align=True)
        col_ti.label(text="Aparicion (frame inicio):", icon="KEYFRAME")
        row_ti = col_ti.row(align=True)
        row_ti.scale_y = 1.15
        if hasattr(oi, "edit_transition_in"):
            row_ti.prop(oi, "edit_transition_in", text="")
            t_in_val = getattr(oi, "edit_transition_in", "NONE")
            if t_in_val and t_in_val != 'NONE':
                row_ti2 = col_ti.row(align=True)
                row_ti2.prop(oi, "edit_transition_in_duration", text="Duracion (frames)")
        else:
            row_ti.label(text="(recarga el addon)", icon="ERROR")

        box_trans.separator(factor=0.3)

        # --- Desaparicion ---
        col_to = box_trans.column(align=True)
        col_to.label(text="Desaparicion (frame fin):", icon="KEYFRAME_HLT")
        row_to = col_to.row(align=True)
        row_to.scale_y = 1.15
        if hasattr(oi, "edit_transition_out"):
            row_to.prop(oi, "edit_transition_out", text="")
            t_out_val = getattr(oi, "edit_transition_out", "NONE")
            if t_out_val and t_out_val != 'NONE':
                row_to2 = col_to.row(align=True)
                row_to2.prop(oi, "edit_transition_out_duration", text="Duracion (frames)")
        else:
            row_to.label(text="(recarga el addon)", icon="ERROR")

        box_edit.separator()

        dur = max(1, oi.edit_frame_end - oi.edit_frame_start)
        box_edit.label(
            text=f"  '{oi.edit_object_name}'  {dur} frames  |  bone: {oi.edit_parent_bone or '(armature)'}",
            icon="INFO",
        )

        row_btns = box_edit.row(align=True)
        row_btns.scale_y = 1.3

        if is_editing:
            row_btns.operator("ch1st.obj_import_update_item", text="Actualizar", icon="CHECKMARK")
            row_btns.operator("ch1st.obj_import_add_item",    text="+ Agregar nuevo", icon="ADD")
        else:
            row_btns.active_default = True
            row_btns.operator("ch1st.obj_import_add_item", text="+ Agregar objeto", icon="CHECKMARK")

        layout.separator()
        layout.label(text="Los objetos se incluyen en el .py al EXPORTAR", icon="INFO")


# =============================================================================
# PANEL ÚNICO DE SECUENCIA DE OJOS
# =============================================================================

class CH1ST_PT_EyeSequence(Panel):
    """
    Panel unico de ojos:
      · Setup de shape keys
      · Frame de inicio global de la secuencia de ojos
      · Posicion inicio / N cambios (con importar .json) / Posicion fin
      · Parpadeo automatico
      · CONCATENAR_2 — inserta keyframes definitivos desde el frame de inicio configurado
    """
    bl_label       = "2b  Secuencia de Ojos"
    bl_idname      = "CH1ST_PT_eye_sequence"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Chicken1 Studio"
    bl_parent_id   = "CH1ST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        segs = getattr(context.scene, "ch1_segs", None)
        if segs is not None and len(segs.segments) > 0:
            return False
        return True

    def draw_header(self, context):
        self.layout.prop(context.scene.ch1st.eye_expr, "enabled", text="")

    def draw(self, context):
        layout = self.layout
        st     = context.scene.ch1st
        eye_s  = st.eye_expr
        layout.active = eye_s.enabled

        # ══════════════════════════════════════════════════════
        # ══════════════════════════════════════════════════════
        # A) FRAME DE INICIO GENERAL DE LA SECUENCIA DE OJOS
        # ══════════════════════════════════════════════════════
        box = layout.box()
        box.label(text="Frame de inicio  (secuencia de ojos)", icon="TIME")
        row = box.row(align=True)
        row.prop(st, "eye_global_start_frame", text="Frame inicio ojos")
        box.label(text="  CONCATENAR_2 inserta keyframes a partir de este frame", icon="INFO")

        layout.separator(factor=0.5)

        # ══════════════════════════════════════════════════════
        # B) ESTADO INICIO DE OJOS
        # ══════════════════════════════════════════════════════
        box = layout.box()
        box.label(text="INICIO  (Ojos)", icon="KEYFRAME")
        col = box.column(align=True)
        row = col.row(align=True)
        row.label(text="Duracion:", icon="TIME")
        row.prop(st, "eye_start_duration", text="frames")
        row2 = col.row(align=True)
        row2.label(text="Interpolacion salida:", icon="IPO_BEZIER")
        row2.prop(st, "eye_start_interp", text="")
        box.separator(factor=0.3)
        # Modo: posicion fija o parpadeo
        row_mode = box.row(align=True)
        row_mode.label(text="Comportamiento:", icon="HIDE_OFF")
        row_mode.prop(st, "eye_start_blink_mode", expand=True)
        if st.eye_start_blink_mode == "BLINK":
            col_b = box.column(align=True)
            col_b.prop(st, "eye_start_blink_count",    text="Numero parpadeos")
            col_b.prop(st, "eye_start_blink_duration", text="Frames por parpadeo")
        else:
            box.label(text="  Ojos fijos en posicion base", icon="INFO")

        layout.separator(factor=0.4)

        # ══════════════════════════════════════════════════════
        # C) CAMBIOS INTERMEDIOS DE OJOS
        # ══════════════════════════════════════════════════════
        box = layout.box()
        # ── Toggle del sistema de cambios intermedios ──────────────────────
        row_chg_hdr = box.row(align=True)
        row_chg_hdr.prop(st, "eye_changes_enabled", text="", icon="HIDE_OFF" if st.eye_changes_enabled else "HIDE_ON")
        row_chg_hdr.label(text="N° CAMBIOS DE OJOS  (intermedios)", icon="NLA")
        if not st.eye_changes_enabled:
            box.label(text="  Sistema desactivado — solo se ejecutara el Parpadeo automatico", icon="INFO")
        box.active = st.eye_changes_enabled

        # ── Setup de Shape Keys — va aquí porque solo afecta a los intermedios ──
        sub_sk = box.box()
        sub_sk.label(text="Setup de Shape Keys de ojos", icon="MESH_PLANE")
        col_sk = sub_sk.column(align=True)
        col_sk.prop(eye_s, "subdivide_cuts", text="Subdivisiones previas")
        row_sk = col_sk.row(align=True)
        row_sk.prop(eye_s, "swap_axes",         toggle=True)
        row_sk.prop(eye_s, "invert_vertical",   toggle=True, text="Inv V")
        row_sk.prop(eye_s, "invert_horizontal", toggle=True, text="Inv H")
        col_sk.prop(eye_s, "affect_zone", text="Zona")
        col_sk.prop(eye_s, "curve_mode",  text="Curva")
        row_build = sub_sk.row()
        row_build.scale_y = 1.3
        row_build.operator("ch1st.build_eye_shape_keys", icon="FILE_REFRESH",
                            text="Crear / Recrear Shape Keys")

        box.separator(factor=0.3)

        row = box.row()
        row.template_list(
            "CH1ST_UL_EyeSlots", "",
            st, "eye_slots",
            st, "eye_slot_idx",
            rows=4,
        )
        col = row.column(align=True)
        col.operator("ch1st.add_eye_slot",       text="", icon="ADD")
        col.operator("ch1st.remove_eye_slot",    text="", icon="REMOVE")
        col.operator("ch1st.duplicate_eye_slot", text="", icon="COPYDOWN")
        col.separator()
        op = col.operator("ch1st.move_eye_slot", text="", icon="TRIA_UP");   op.direction = "UP"
        op = col.operator("ch1st.move_eye_slot", text="", icon="TRIA_DOWN"); op.direction = "DOWN"
        col.separator()
        col.operator("ch1st.edit_eye_slot", text="", icon="GREASEPENCIL")

        row_add = box.row(align=True)
        row_add.scale_y = 1.4
        row_add.active_default = True
        row_add.operator("ch1st.add_eye_slot",              text="  + Agregar",         icon="ADD")
        row_add.operator("ch1st.duplicate_eye_slot",        text="  Copiar",            icon="COPYDOWN")
        row_add.operator("ch1st.import_eye_slot_from_json", text="  Importar .json...", icon="FILE_FOLDER")

        if not st.eye_slots:
            box.label(text="  Sin cambios: transicion directa inicio → fin", icon="INFO")
        else:
            total_dur = sum(item.duration for item in st.eye_slots)
            box.label(text=f"  {len(st.eye_slots)} estados  |  {total_dur} frames totales", icon="TIME")

            if 0 <= st.eye_slot_idx < len(st.eye_slots):
                sel = st.eye_slots[st.eye_slot_idx]
                sub = box.box()
                row = sub.row(align=True)
                row.label(text=f"{sel.slot_label}", icon="HIDE_OFF")
                row.operator("ch1st.edit_eye_slot", icon="GREASEPENCIL", text="Editar...")
                row2 = sub.row(align=True)
                row2.prop(sel, "duration",    text="Frames")
                row2.prop(sel, "interp_type", text="")

        layout.separator(factor=0.4)

        # ══════════════════════════════════════════════════════
        # D) ESTADO FINAL DE OJOS
        # ══════════════════════════════════════════════════════
        box = layout.box()
        box.label(text="FIN  (Ojos)", icon="KEYFRAME_HLT")
        col = box.column(align=True)
        row = col.row(align=True)
        row.label(text="Duracion:", icon="TIME")
        row.prop(st, "eye_end_duration", text="frames")
        row2 = col.row(align=True)
        row2.label(text="Interpolacion entrada:", icon="IPO_BEZIER")
        row2.prop(st, "eye_end_interp", text="")
        box.separator(factor=0.3)
        # Modo: posicion fija o parpadeo
        row_mode = box.row(align=True)
        row_mode.label(text="Comportamiento:", icon="HIDE_OFF")
        row_mode.prop(st, "eye_end_blink_mode", expand=True)
        if st.eye_end_blink_mode == "BLINK":
            col_b = box.column(align=True)
            col_b.prop(st, "eye_end_blink_count",    text="Numero parpadeos")
            col_b.prop(st, "eye_end_blink_duration", text="Frames por parpadeo")
        else:
            box.label(text="  Ojos fijos en posicion base", icon="INFO")

        layout.separator(factor=0.4)

        # ══════════════════════════════════════════════════════
        # E) PARPADEO AUTOMATICO  (multi-intervalo)
        # ══════════════════════════════════════════════════════
        box = layout.box()
        row_blink_hdr = box.row(align=True)
        row_blink_hdr.prop(eye_s, "blink_enabled", text="", icon="HIDE_OFF" if eye_s.blink_enabled else "HIDE_ON")
        row_blink_hdr.label(text="Parpadeo automatico — Lista de intervalos", icon="SEQUENCE")

        if eye_s.blink_enabled:
            # ── Lista de intervalos de parpadeo ──────────────────────────────
            row_lst = box.row()
            row_lst.template_list(
                "CH1ST_UL_BlinkIntervals", "",
                st, "blink_intervals",
                st, "blink_interval_idx",
                rows=3,
            )
            col_lst = row_lst.column(align=True)
            col_lst.operator("ch1st.blink_interval_add",       text="", icon="ADD")
            col_lst.operator("ch1st.blink_interval_remove",    text="", icon="REMOVE")
            col_lst.operator("ch1st.blink_interval_duplicate", text="", icon="COPYDOWN")
            col_lst.separator()
            op = col_lst.operator("ch1st.blink_interval_move", text="", icon="TRIA_UP");  op.direction = "UP"
            op = col_lst.operator("ch1st.blink_interval_move", text="", icon="TRIA_DOWN"); op.direction = "DOWN"

            # ── Detalle del intervalo seleccionado ───────────────────────────
            if 0 <= st.blink_interval_idx < len(st.blink_intervals):
                bi = st.blink_intervals[st.blink_interval_idx]
                sub = box.box()
                row_bi_hdr = sub.row(align=True)
                row_bi_hdr.prop(bi, "enabled", text="", icon="HIDE_OFF" if bi.enabled else "HIDE_ON")
                row_bi_hdr.prop(bi, "label", text="")
                col_bi = sub.column(align=True)
                row_rng = col_bi.row(align=True)
                row_rng.label(text="Rango:", icon="TIME")
                row_rng.prop(bi, "frame_start", text="Ini")
                row_rng.prop(bi, "frame_end",   text="Fin")
                row_cnt = col_bi.row(align=True)
                row_cnt.prop(bi, "blink_count",    text="N° parpadeos")
                row_cnt.prop(bi, "blink_duration", text="Frames/parpadeo")
                sub.label(
                    text=f"  {bi.blink_count} parpadeos entre frame {bi.frame_start} y {bi.frame_end}",
                    icon="INFO",
                )
            elif not st.blink_intervals:
                box.label(text="  + Agrega un intervalo para definir cuando parpadea", icon="INFO")

            total_blinks = sum(b.blink_count for b in st.blink_intervals if b.enabled)
            if st.blink_intervals:
                box.label(
                    text=f"  {len([b for b in st.blink_intervals if b.enabled])} intervalos activos"
                         f"  |  {total_blinks} parpadeos totales",
                    icon="TIME",
                )
        else:
            box.label(text="  Activar para insertar parpadeos automaticos por intervalos", icon="INFO")

        # ══════════════════════════════════════════════════════
        # E2) EXPRESIONES DE OJOS  (multi-intervalo)
        # ══════════════════════════════════════════════════════
        box_ei = layout.box()
        row_ei_hdr = box_ei.row(align=True)
        row_ei_hdr.prop(eye_s, "expr_intervals_enabled", text="",
                        icon="HIDE_OFF" if eye_s.expr_intervals_enabled else "HIDE_ON")
        row_ei_hdr.label(text="Expresiones de ojos — Lista de intervalos", icon="SHAPEKEY_DATA")

        if eye_s.expr_intervals_enabled:
            # ── Lista de intervalos de expresion ─────────────────────────────
            row_ei = box_ei.row()
            row_ei.template_list(
                "CH1ST_UL_EyeExprIntervals", "",
                st, "expr_intervals",
                st, "expr_interval_idx",
                rows=3,
            )
            col_ei = row_ei.column(align=True)
            col_ei.operator("ch1st.expr_interval_add",       text="", icon="ADD")
            col_ei.operator("ch1st.expr_interval_remove",    text="", icon="REMOVE")
            col_ei.operator("ch1st.expr_interval_duplicate", text="", icon="COPYDOWN")
            col_ei.separator()
            op = col_ei.operator("ch1st.expr_interval_move", text="", icon="TRIA_UP");  op.direction = "UP"
            op = col_ei.operator("ch1st.expr_interval_move", text="", icon="TRIA_DOWN"); op.direction = "DOWN"

            # ── Detalle del intervalo seleccionado ───────────────────────────
            if 0 <= st.expr_interval_idx < len(st.expr_intervals):
                ei = st.expr_intervals[st.expr_interval_idx]
                sub_ei = box_ei.box()
                row_ei_top = sub_ei.row(align=True)
                row_ei_top.prop(ei, "enabled", text="", icon="HIDE_OFF" if ei.enabled else "HIDE_ON")
                row_ei_top.prop(ei, "label", text="")

                col_ei2 = sub_ei.column(align=True)
                # Tres fases del intervalo
                row_frames = col_ei2.row(align=True)
                row_frames.label(text="Inicio:", icon="KEYFRAME")
                row_frames.prop(ei, "frame_start", text="")
                row_frames.label(text="Pico:")
                row_frames.prop(ei, "frame_peak",  text="")
                row_frames.label(text="Fin:", icon="KEYFRAME_HLT")
                row_frames.prop(ei, "frame_end",   text="")

                row_expr = col_ei2.row(align=True)
                row_expr.label(text="Expresion:", icon="SHAPEKEY_DATA")
                row_expr.prop(ei, "expression", text="")
                row_expr.prop(ei, "expression_value", text="Intensidad")

                row_itp = col_ei2.row(align=True)
                row_itp.label(text="Interp entrada:", icon="IPO_BEZIER")
                row_itp.prop(ei, "interp_in",  text="")
                row_itp.label(text="Interp salida:")
                row_itp.prop(ei, "interp_out", text="")

                sub_ei.label(
                    text=f"  Inicio→Pico ({ei.frame_start}→{ei.frame_peak})  "
                         f"Pico→Fin ({ei.frame_peak}→{ei.frame_end})",
                    icon="INFO",
                )
            elif not st.expr_intervals:
                box_ei.label(text="  + Agrega un intervalo de expresion de ojos", icon="INFO")

            active_ei = [e for e in st.expr_intervals if e.enabled]
            if st.expr_intervals:
                box_ei.label(
                    text=f"  {len(active_ei)} intervalos activos en la timeline",
                    icon="TIME",
                )
            box_ei.label(text="  Los intervalos pueden solaparse con el parpadeo — usan frames distintos", icon="INFO")
        else:
            box_ei.label(text="  Activar para definir emociones por intervalos de frames", icon="INFO")

        box.label(text="  Ambos sistemas se ejecutan al presionar CONCATENAR_2", icon="INFO")

        layout.separator(factor=0.4)

        # ══════════════════════════════════════════════════════
        # F) RESUMEN + CONCATENAR_2 + RESET
        # ══════════════════════════════════════════════════════
        box_sum = layout.box()
        box_sum.label(text="Resumen de duracion de ojos:", icon="TIME")
        dur_ini = st.eye_start_duration
        dur_mid = sum(item.duration for item in st.eye_slots) if st.eye_slots else 0
        dur_fin = st.eye_end_duration
        total   = dur_ini + dur_mid + dur_fin
        box_sum.label(
            text=f"  Inicio {dur_ini}f  +  Cambios {dur_mid}f  +  Fin {dur_fin}f  =  {total}f total"
        )
        box_sum.label(
            text=f"  Desde frame {st.eye_global_start_frame}  →  "
                 f"hasta frame {st.eye_global_start_frame + total - 1}",
            icon="KEYFRAME",
        )
        row_itp = box_sum.row(align=False)
        row_itp.label(text=f"  INICIO: {st.eye_start_interp}", icon="IPO_BEZIER")
        if st.eye_slots:
            interps = list(dict.fromkeys(s.interp_type for s in st.eye_slots))
            row_itp.label(text="  CAMBIOS: " + " / ".join(interps))
        row_itp.label(text=f"  FIN: {st.eye_end_interp}")

        layout.separator(factor=0.3)

        # ── BOTON CONCATENAR_2 ───────────────────────────────────────────────
        row_cat2 = layout.row()
        row_cat2.scale_y = 2.2
        row_cat2.operator(
            "ch1st.concatenate_2",
            text="  CONCATENAR_2  (Ojos)",
            icon="PLAY",
        )
        n_blink_intervals = len([b for b in st.blink_intervals if b.enabled]) if eye_s.blink_enabled else 0
        n_expr_intervals  = len([e for e in st.expr_intervals  if e.enabled]) if eye_s.expr_intervals_enabled else 0
        layout.label(
            text=f"  Inserta keyframes de ojos desde frame {st.eye_global_start_frame}"
                 + (f"  +  {n_blink_intervals} intervalos parpadeo" if n_blink_intervals else "")
                 + (f"  +  {n_expr_intervals} intervalos expresion"  if n_expr_intervals  else ""),
            icon="INFO",
        )

        layout.separator(factor=0.3)

        # ── BOTON RESET ──────────────────────────────────────────────────────
        row_reset = layout.row()
        row_reset.scale_y = 1.6
        row_reset.alert   = True
        row_reset.operator(
            "ch1st.reset_eye_sequence",
            text="  RESET  Sistema de Ojos",
            icon="LOOP_BACK",
        )

        layout.separator(factor=0.4)

        # ── EXPORTAR / IMPORTAR CONFIGURACION DE OJOS ────────────────────────
        box_cfg = layout.box()
        box_cfg.label(text="Configuracion de ojos  (.json)", icon="FILE_BLANK")
        box_cfg.label(
            text=r"  Carpeta: ...\refinar\configuraciones_ojos",
            icon="FOLDER_REDIRECT",
        )
        row_cfg = box_cfg.row(align=True)
        row_cfg.scale_y = 1.5
        row_cfg.operator(
            "ch1st.save_eye_config",
            text="  Exportar config ojos",
            icon="EXPORT",
        )
        row_cfg.operator(
            "ch1st.load_eye_config",
            text="  Importar config ojos",
            icon="IMPORT",
        )



# =============================================================================
# PASO 2: RECORRIDO (Path Recorder)
# =============================================================================

class CH1ST_PT_PathRecorder(Panel):
    bl_label       = "0  Recorrido y Slots"
    bl_idname      = "CH1ST_PT_path_recorder"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Chicken1 Studio"

    def draw(self, context):
        layout = self.layout
        pc = context.scene.ch1_path

        # ── PASO 1: Personaje y grabacion de recorrido ────────────────────────
        box_paso1 = layout.box()
        box_paso1.label(text="PASO 1 — Trazar recorrido", icon="CON_FOLLOWPATH")

        # Personaje .blend
        col_blend = box_paso1.column(align=True)
        col_blend.label(text="Personaje (.blend):", icon="ARMATURE_DATA")
        row_blend = col_blend.row(align=True)
        row_blend.prop(pc, "blend_filepath", text="")
        row_blend.operator("ch1pr.open_blend", text="", icon="FILEBROWSER")

        box_paso1.separator(factor=0.5)

        # Boton grabacion
        rec_text = "  Detener grabacion de recorrido" if pc.recording_active else "  Iniciar grabacion de recorrido"
        rec_icon = "REC" if pc.recording_active else "RADIOBUT_ON"
        row_rec = box_paso1.row()
        row_rec.scale_y = 1.3
        row_rec.operator("ch1pr.toggle_recording", text=rec_text, icon=rec_icon)

        # NUEVO (Kebyn, 2026-08-02): boton para ver el recorrido trazado
        # en el viewport (linea + numeros de orden) sin necesidad de estar
        # grabando -- antes, al presionar "Detener grabacion" el trazado
        # desaparecia por completo del viewport.
        viz_text = "  Ocultar recorrido" if pc.show_path_viz else "  Visualizar recorrido"
        viz_icon = "HIDE_OFF" if pc.show_path_viz else "HIDE_ON"
        row_viz = box_paso1.row()
        row_viz.operator("ch1pr.toggle_path_viz", text=viz_text, icon=viz_icon)
        row_viz.enabled = len(pc.path_points) > 0

        # Puntos grabados + botones quitar/limpiar
        row_pts = box_paso1.row(align=True)
        row_pts.label(text=f"Puntos registrados: {len(pc.path_points)}")
        row_remove = box_paso1.row(align=True)
        row_remove.operator("ch1pr.remove_last", text="Quitar ultimo", icon="REMOVE")
        row_remove.operator("ch1pr.clear_path",  text="Limpiar todo",  icon="X")

        if not pc.blend_filepath:
            box_paso1.label(text="Selecciona el archivo .blend del personaje", icon="ERROR")
        else:
            n_reg = len(pc.path_points)
            if n_reg == 0:
                box_paso1.label(text="Selecciona faces para trazar el recorrido", icon="INFO")
            elif n_reg == 1:
                box_paso1.label(text="Modo: 1 coordenada  (parado/idle)", icon="RADIOBUT_ON")
            else:
                box_paso1.label(text=f"Modo: recorrido  ({n_reg} puntos)", icon="CON_FOLLOWPATH")

        # ── Lista de coordenadas seleccionadas (EDITABLE) ──────────────────────
        n_pts_lista = len(pc.path_points)
        if n_pts_lista > 0:
            from .path_recorder import _detect_move

            box_lista = box_paso1.box()

            # Cabecera colapsable via prop guardada en pc (usamos un bool auxiliar)
            header_row = box_lista.row(align=True)
            header_row.prop(
                pc, "show_coords_list",
                icon="TRIA_DOWN" if pc.show_coords_list else "TRIA_RIGHT",
                text=f"Coordenadas seleccionadas  ({n_pts_lista})",
                emboss=False,
            )

            if pc.show_coords_list:
                n_marcadas = sum(1 for pt in pc.path_points if pt.tipo_segmento == "PARADA")
                n_saltos   = sum(1 for pt in pc.path_points if pt.tipo_segmento == "SALTAR")
                info_row = box_lista.row()
                if n_marcadas == 0 and n_saltos == 0:
                    info_row.label(
                        text="Todos en 'Caminar': el recorrido sera solo caminata/saltos",
                        icon="INFO",
                    )
                else:
                    partes = []
                    if n_marcadas:
                        partes.append(f"{n_marcadas} en 'Parada'")
                    if n_saltos:
                        partes.append(f"{n_saltos} en 'Saltar'")
                    info_row.label(
                        text=" | ".join(partes) + " marcado(s)",
                        icon="PAUSE",
                    )

                pts_list = list(pc.path_points)
                col_lista = box_lista.column(align=False)

                # NUEVO (Kebyn, 2026-09-02): cuando un punto se marca SALTAR,
                # consume los DOS puntos siguientes (pico/aterrizaje) --
                # igual criterio que _group_segments()/group_segments(). Se
                # muestran como parte del grupo (sin su propio dropdown
                # editable) en vez de listarlos como tramos "caminar" sueltos.
                consumidos_por_salto = 0

                for i, pt in enumerate(pts_list):
                    row_pt = col_lista.row(align=True)

                    # Numero de punto
                    row_pt.label(text=f"{i+1:>2}.", icon="LAYER_USED")

                    # Coordenadas redondeadas
                    x, y, z = round(pt.coords[0], 2), round(pt.coords[1], 2), round(pt.coords[2], 2)
                    row_pt.label(text=f"({x},  {y},  {z})")

                    if consumidos_por_salto > 0:
                        etiqueta = "salto: pico" if consumidos_por_salto == 2 else "salto: aterrizaje"
                        row_pt.label(text=etiqueta, icon="FORCE_TURBULENCE")
                        consumidos_por_salto -= 1
                        col_lista.separator(factor=0.3)
                        continue

                    # NUEVO (Kebyn, 2026-08-02): el dropdown Caminar/Parada
                    # SOLO se muestra editable en tramos donde la geometria
                    # real (diferencia de Z entre este punto y el siguiente)
                    # da "caminar". Las coordenadas de saltar_subir/
                    # saltar_bajar no se pueden alterar -- se muestran fijas,
                    # igual que antes, sin dropdown.
                    if i < len(pts_list) - 1:
                        real_move = _detect_move(pt, pts_list[i + 1])
                        if real_move == "caminar":
                            row_pt.prop(pt, "tipo_segmento", text="")
                            if pt.tipo_segmento == "PARADA":
                                row_pt.prop(pt, "parada_frames_punto", text="Frames")
                            elif pt.tipo_segmento == "SALTAR":
                                # Necesita 2 puntos mas adelante (pico +
                                # aterrizaje); si no alcanzan, el marcador se
                                # ignora en la generacion (ver _group_segments).
                                if i < len(pts_list) - 2:
                                    row_pt.label(text="despegue", icon="FORCE_TURBULENCE")
                                    consumidos_por_salto = 2
                                else:
                                    row_pt.label(text="(faltan puntos)", icon="ERROR")
                        elif real_move == "saltar_subir":
                            row_pt.label(text="subir", icon="SORT_DESC")
                        else:  # saltar_bajar
                            row_pt.label(text="bajar", icon="SORT_ASC")
                    else:
                        # Ultimo punto: destino final, sin tramo de salto
                        # asociado -- se puede marcar como parada igual.
                        row_pt.prop(pt, "tipo_segmento", text="")
                        if pt.tipo_segmento == "PARADA":
                            row_pt.prop(pt, "parada_frames_punto", text="Frames")
                        row_pt.label(text="(final)", icon="KEYFRAME")

                    # Textura (compacta, solo nombre sin extension)
                    tex = pt.texture or ""
                    if tex:
                        short_tex = tex.replace("grass_block_top", "grass").replace(".png", "")
                        col_lista.label(text=f"       Textura: {short_tex}", icon="TEXTURE")

                    col_lista.separator(factor=0.3)

        # ── PASO 2: Configuracion de slots ───────────────────────────────────
        n_pts_reg = len(pc.path_points)
        is_idle      = (n_pts_reg == 1)
        is_recorrido = (n_pts_reg > 1)

        box_paso2 = layout.box()
        box_paso2.label(text="PASO 2 — Configuracion de slots", icon="SETTINGS")
        col2 = box_paso2.column(align=True)
        col2.prop(pc, "slot_inicio",  text="Slot inicio")
        col2.prop(pc, "frame_inicio", text="Frame inicial")

        # Frame final: solo en modo 1 coordenada (parado/idle)
        if is_idle:
            col2.prop(pc, "frame_fin_manual", text="Frame final")

        # Frames/bloque: solo en recorrido multi-coordenada
        if is_recorrido:
            col2.prop(pc, "frames_por_bloque", text="Frames/bloque (caminar)")
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

        # Estimacion de segmentos
        #
        # FIX (Kebyn, 2026-07-11): esta seccion SIEMPRE recalculaba desde
        # cero con _group_segments() (path_recorder.py), que solo conoce 4
        # tipos geometricos (caminar/saltar_subir/saltar_bajar/parada) y no
        # tiene forma de saber que un tramo "caminar" largo puede venir
        # dividido en sub-tramos por el pipeline externo (ej.
        # "05_caminar" + "06_caminar_intervalo_caminata_normal" +
        # "07_caminar"), asi que nunca coincidia con lo que
        # AutoSplitFromConfig / LoadConfig ya dejan armado en
        # scene.ch1_segs.segments (Paso 3 — ver la lista "Segmentos
        # creados"), que SI trae esa division real (viene tal cual de
        # paso1_path.segmentos_recorrido del configuracion.json).
        #
        # REFACTOR (Kebyn, 2026-08-02): la logica de estimacion (ambas
        # fuentes: segmentos reales del Paso 3, o fallback geometrico) se
        # movio a path_recorder.calcular_estimacion_slots() para poder
        # reusarla tambien al exportar (ver "estimacion_slots" en
        # _serialize_configuracion(), config_ops.py) -- antes esta
        # informacion solo existia mientras se dibujaba el panel y se
        # perdia al guardar el .json. El panel ahora solo la pide y la
        # dibuja; el calculo vive en un unico lugar.
        from .path_recorder import (
            calcular_estimacion_slots, _group_segments, _expand_points_with_paradas,
        )

        # El boton de sincronizacion de paradas_frames necesita saber
        # cuantas paradas hay en el recorrido AUN si ya existen segmentos
        # reales del Paso 3 (edge case: recorrido re-grabado sin re-dividir)
        # -- se sigue calculando aparte, es una revision de integridad
        # distinta de la estimacion en si.
        if len(pc.path_points) > 1:
            pts = list(pc.path_points)
            expanded_pts, _ = _expand_points_with_paradas(pts)
            segs_chk = _group_segments(expanded_pts)
            n_paradas_actual = sum(1 for s in segs_chk if s["type"] == "parada")
            if len(pc.paradas_frames) != n_paradas_actual:
                row_sync = box_paso2.row()
                row_sync.alert = True
                row_sync.operator(
                    "ch1pr.sync_paradas_frames",
                    text=f"Sincronizar frames por parada ({n_paradas_actual} detectada(s))",
                    icon="FILE_REFRESH",
                )

        _slots_est, _fuente_est = calcular_estimacion_slots(context.scene)
        if _fuente_est == "paso3_segmentos":
            box_est = box_paso2.box()
            row_est_head = box_est.row(align=True)
            row_est_head.label(text="Estimacion de segmentos:", icon="INFO")
            row_est_head.operator(
                "ch1seg.update_from_estimacion",
                text="Actualizar", icon="FILE_REFRESH",
            )
            box_est.label(text=f"  ({len(_slots_est)} segmento(s) — Paso 3)", icon="NLA")
            _caminar_idx_ui = 0
            for _s in _slots_est:
                row_seg = box_est.row(align=True)
                row_seg.label(
                    text=f"  Segmento {_s['slot']}: {_s['label']}  ({_s['frames_estimados']} f)"
                )
                if _s["tipo"] == "caminar":
                    if _caminar_idx_ui < len(pc.walk_styles):
                        row_seg.prop(pc.walk_styles[_caminar_idx_ui], "style", text="")
                    _caminar_idx_ui += 1
        elif _fuente_est == "estimacion_geometrica":
            box_est = box_paso2.box()
            box_est.label(text="Estimacion de segmentos:", icon="INFO")
            box_est.label(
                text="  (estimacion geometrica — sin dividir en Paso 3 todavia)",
                icon="INFO",
            )
            _caminar_idx_ui = 0
            for _s in _slots_est:
                row_seg = box_est.row(align=True)
                if _s["tipo"] == "caminar":
                    row_seg.label(text=f"  Segmento {_s['slot']}: {_s['label']} (~{_s['frames_estimados']} f)")
                    if _caminar_idx_ui < len(pc.walk_styles):
                        row_seg.prop(pc.walk_styles[_caminar_idx_ui], "style", text="")
                    _caminar_idx_ui += 1
                elif _s["tipo"] in ("saltar_subir", "saltar_bajar", "saltar"):
                    row_seg.label(text=f"  Segmento {_s['slot']}: {_s['label']} ({_s['frames_estimados']} f)")
                elif _s["label"] == "parada (sin sincronizar)":
                    row_seg.label(text=f"  Segmento {_s['slot']}: parada ({_s['frames_estimados']} f, sin sincronizar)")
                else:  # parada, sincronizada
                    row_seg.label(text=f"  Segmento {_s['slot']}: parada (~{_s['frames_estimados']} f)")
            if len(pc.path_points) > 1:
                _n_caminar_real = sum(1 for _s in _slots_est if _s["tipo"] == "caminar")
                if len(pc.walk_styles) != _n_caminar_real:
                    row_sync_ws = box_est.row()
                    row_sync_ws.alert = True
                    row_sync_ws.operator(
                        "ch1pr.sync_paradas_frames",
                        text=f"Sincronizar estilos de caminata ({_n_caminar_real} tramo(s) detectado(s))",
                        icon="FILE_REFRESH",
                    )


        # Duracion calculada
        if pc.anim_frame_fin > 0:
            box_dur = box_paso2.box()
            total_f = pc.anim_frame_fin - pc.frame_inicio + 1
            box_dur.label(
                text=f"Duracion: {total_f} frames  ({total_f / 24:.2f}s @ 24fps)",
                icon="TIME"
            )
            box_dur.label(
                text=f"Frame {pc.frame_inicio}  →  {pc.anim_frame_fin}",
                icon="ARROW_LEFTRIGHT",
            )

        # ── Selector de estilo de caminata (multiplexor) ───────────────
        # ACTUALIZADO (pedido de Kebyn, 2026-08-02): el estilo de caminata
        # ya NO se elige de forma global para todo el recorrido -- cada
        # tramo 'caminar' detectado tiene su propio selector inline,
        # dibujado junto a su fila dentro de "Estimacion de segmentos"
        # (mas arriba en este mismo panel). Ver pc.walk_styles /
        # sync_walk_styles() en path_recorder.py.

        # Botones de accion
        layout.separator(factor=0.5)
        row_play = layout.row()
        row_play.scale_y = 1.5
        row_play.operator("ch1pr.preview_path", text="  Reproducir recorrido", icon="PLAY")

        box_exp = layout.box()
        box_exp.label(text="Exportar slots (opcional):", icon="EXPORT")
        box_exp.label(text="  Solo animacion base sin poses avanzadas", icon="INFO")
        row_exp = box_exp.row()
        row_exp.scale_y = 1.3
        row_exp.operator("ch1pr.export_slots", text="  Exportar recorrido", icon="EXPORT")

        layout.separator(factor=0.3)
        layout.label(text="  ¿Poses avanzadas? → Configura el PASO 3 abajo", icon="QUESTION")
        row_reset = layout.row()
        row_reset.operator("ch1pr.reset_preview", text="  Reset recorrido", icon="LOOP_BACK")

        if pc.anim_frame_fin > 0:
            layout.label(text=f"Rango fijado: {pc.frame_inicio}→{pc.anim_frame_fin}", icon="PINNED")



# =============================================================================
# PASO 3: SEGMENTOS (Refinado de poses sobre el recorrido)
# =============================================================================

# =============================================================================
# PASO 3: SEGMENTOS (Refinado de poses sobre el recorrido)
# =============================================================================

class CH1SEG_UL_SegmentsList(UIList):
    bl_idname = "CH1SEG_UL_SegmentsList"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.prop(item, "enabled", text="")
            row.prop(item, "label", text="", emboss=False,
                     icon="KEYFRAME_HLT" if item.enabled else "KEYFRAME")
            row.label(text=f"{item.frame_start}→{item.frame_end}", icon="TIME")
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text=item.label)


class CH1ST_PT_Segments(Panel):
    bl_label       = "3  Segmentos (Poses sobre recorrido)"
    bl_idname      = "CH1ST_PT_segments"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Chicken1 Studio"
    bl_options     = {"DEFAULT_CLOSED"}
    bl_order       = 0

    def draw(self, context):
        layout    = self.layout
        segs_data = context.scene.ch1_segs
        pc        = context.scene.ch1_path
        st        = context.scene.ch1st

        n_pts = len(pc.path_points)
        _modo_1coord = (n_pts <= 1)

        # ── Cabecera PASO 3 ───────────────────────────────────────────────────
        box3 = layout.box()
        row_title3 = box3.row()
        row_title3.alert = True
        row_title3.label(text="PASO 3 — Crear segmento", icon="KEYFRAME")

        if _modo_1coord:
            # ── MODO 1 COORDENADA ─────────────────────────────────────────────
            _fs_1c = pc.frame_inicio

            box_info = box3.box()
            col_info3 = box_info.column(align=True)
            col_info3.scale_y = 0.85
            col_info3.label(
                text=f"Frame inicio (Paso 1):  {_fs_1c}",
                icon="KEYFRAME"
            )
            col_info3.label(
                text="Frame fin: calculado al CONCATENAR",
                icon="TIME"
            )
            col_info3.label(
                text="(pose inicio + N poses + pose fin)",
                icon="INFO"
            )

            box3.separator(factor=0.3)
            box3.prop(segs_data, "edit_label", text="Nombre")

            layout.separator(factor=0.5)
            row_crear = layout.row()
            row_crear.scale_y = 2.2
            row_crear.alert   = True
            row_crear.operator("ch1seg.add", text="+ CREAR SEGMENTO", icon="ADD")

        else:
            # ── MODO RECORRIDO (2+ coordenadas) ───────────────────────────────
            import math as _math
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
                    [(s.frame_start, s.frame_end) for s in segs_data.segments if s.enabled],
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
                "ch1seg.autosplit_from_config",
                text="Dividir segmentos",
                icon="MOD_ARRAY",
            )
            box3.label(
                text="  Crea un segmento por cada tramo (caminar/salto/parada) del JSON",
                icon="INFO",
            )

            box3.separator(factor=0.3)
            box3.prop(segs_data, "edit_label", text="Nombre")

            box_fr = box3.box()
            box_fr.label(text="Intervalo del segmento:", icon="KEYFRAME")
            col_fr = box_fr.column(align=True)

            _fs_edit = segs_data.edit_frame_start
            _fe_edit = segs_data.edit_frame_end
            _fs_ok   = False
            _fe_ok   = False
            _overlap = False

            if _total_est == 0:
                col_fr.label(text="  Agrega al menos 2 puntos al recorrido", icon="INFO")
                row_fs = col_fr.row(align=True)
                row_fs.enabled = False
                row_fs.prop(segs_data, "edit_frame_start", text="Frame inicio")
                row_fe = col_fr.row(align=True)
                row_fe.enabled = False
                row_fe.prop(segs_data, "edit_frame_end", text="Frame fin")
            else:
                _fs_ok   = _anim_f_inicio <= _fs_edit <= _anim_f_fin
                _fe_ok   = (_anim_f_inicio <= _fe_edit <= _anim_f_fin) and (_fe_edit > _fs_edit)
                _overlap = any(_fs_edit <= _fe3 and _fe_edit >= _fs3 for _fs3, _fe3 in _occupied)

                row_fs = col_fr.row(align=True)
                row_fs.alert = not _fs_ok
                row_fs.prop(segs_data, "edit_frame_start", text="Frame inicio")

                row_fe = col_fr.row(align=True)
                row_fe.alert = not _fe_ok
                row_fe.prop(segs_data, "edit_frame_end", text="Frame fin")

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
            row_crear.operator("ch1seg.add", text="+ CREAR SEGMENTO", icon="ADD")
            if not _puede_crear and _total_est > 0:
                layout.label(text="  Corrige los frames antes de crear", icon="ERROR")

        # ── Concatenar segmentos: ejecuta APLICAR SEGMENTOS (inyeccion de
        #    poses de CADA segmento activo, respetando el rango de frames
        #    propio de cada uno) y reproduce todas las secuencias encadenadas
        #    de principio a fin ──────────────────────────────────────────────
        layout.separator(factor=0.5)
        _n_enabled = sum(1 for s in segs_data.segments if s.enabled)
        row_concat = layout.row()
        row_concat.scale_y = 1.8
        row_concat.enabled = _n_enabled > 0
        row_concat.operator(
            "ch1seg.concatenate_all",
            text=f"▶ Concatenar segmentos ({_n_enabled})",
            icon="SEQUENCE",
        )
        if _n_enabled == 0:
            layout.label(text="  Activa al menos un segmento para concatenar", icon="INFO")

        # ── Lista acumulada de segmentos (ambos modos) ────────────────────────
        layout.separator(factor=0.5)
        box_list = layout.box()
        box_list.label(text="Segmentos creados:", icon="NLA")

        if segs_data.segments:
            for i, seg in enumerate(segs_data.segments):
                box_seg = box_list.box()

                # ── Cabecera: toggle enable + label + toggle config ────────────
                row_seg_hdr = box_seg.row(align=True)
                icon_en = "HIDE_OFF" if seg.enabled else "HIDE_ON"
                op_en = row_seg_hdr.operator("ch1seg.toggle_enabled", text="", icon=icon_en, emboss=False)
                op_en.item_idx = i

                _seg_total_fr, _seg_f_end = _calc_seg_frames(seg)

                if seg.single_coord_mode:
                    _fe_txt  = str(_seg_f_end)
                    _dur_txt = f"{_seg_total_fr}f"
                    row_seg_hdr.label(
                        text=(f"[{i+1}] {seg.label or 'Segmento'}  |  "
                              f"inicio:{seg.frame_start}  fin:{_fe_txt}  [{_dur_txt}]"),
                        icon="PINNED"
                    )
                else:
                    _dur_i = seg.frame_end - seg.frame_start + 1
                    row_seg_hdr.label(
                        text=(f"[{i+1}] {seg.label or 'Segmento'}  |  "
                              f"recorrido {seg.frame_start}→{seg.frame_end}  ({_dur_i}f)"),
                        icon="SEQUENCE"
                    )

                # Boton configuracion (chevron)
                _cfg_icon = "TRIA_DOWN" if seg.show_config else "TRIA_RIGHT"
                op_cfg = row_seg_hdr.operator("ch1seg.toggle_config", text="", icon=_cfg_icon, emboss=False)
                op_cfg.item_idx = i

                # ── Controles: frames (readonly en recorrido) + duplicar + eliminar ──
                row_play = box_seg.row(align=True)
                row_play.scale_y = 1.3
                if seg.single_coord_mode:
                    row_play.prop(seg, "frame_start", text="Ini")
                    row_play.prop(seg, "frame_end",   text="Fin")
                else:
                    _ro = row_play.row(align=True)
                    _ro.enabled = False
                    _ro.prop(seg, "frame_start", text="Ini")
                    _ro.prop(seg, "frame_end",   text="Fin")
                row_play.separator()
                op_dup = row_play.operator("ch1seg.duplicate", text="", icon="DUPLICATE")
                op_dup.item_idx = i
                op_del = row_play.operator("ch1seg.remove",    text="", icon="X")
                op_del.item_idx = i

                # ── Barra de duracion calculada en tiempo real ────────────────
                _fps = context.scene.render.fps
                _dur_s = round(_seg_total_fr / _fps, 2) if _fps > 0 else 0
                _n_slots = len(seg.action_poses)
                _dur_row = box_seg.row()
                _dur_row.enabled = False
                _dur_parts = (
                    f"{_n_slots} pose{'s' if _n_slots != 1 else ''} ({sum(ap.duration for ap in seg.action_poses)}f)"
                    + f"  =  {_seg_total_fr}f  ({_dur_s}s)"
                )
                _dur_row.label(text=_dur_parts, icon="TIME")

                # ── CONFIGURACION EXPANDIDA ─────────────────────────────────────────
                if seg.show_config:
                    box_cfg = box_seg.box()

                    # ── Titulo ────────────────────────────────────────────────────────────
                    row_cfg_title = box_cfg.row()
                    row_cfg_title.alert = False
                    row_cfg_title.label(
                        text=f"Configuracion del segmento [{i+1}]: {seg.label}",
                        icon="SETTINGS"
                    )

                    # ── Armature + Carpetas ───────────────────────────────────────────────
                    box_setup = box_cfg.box()
                    box_setup.label(text="Armature principal", icon="ARMATURE_DATA")
                    row_arm = box_setup.row(align=True)
                    row_arm.prop(st, "armature_name", text="")
                    row_arm.operator("ch1st.set_armature", text="", icon="EYEDROPPER")

                    box_dirs = box_cfg.box()
                    box_dirs.label(text="Carpetas", icon="FILE_FOLDER")
                    col_dirs = box_dirs.column(align=True)
                    col_dirs.prop(st, "poses_dir",  text="Poses")
                    col_dirs.prop(st, "anim_dir",   text="Animaciones")
                    col_dirs.prop(st, "config_dir", text="Configuraciones")
                    row_dirs = box_dirs.row(align=True)
                    row_dirs.operator("ch1st.open_poses_folder", text="Poses", icon="FILE_FOLDER")
                    row_dirs.operator("ch1st.open_anim_folder",  text="Anims", icon="FILE_FOLDER")
                    row_dirs.operator("ch1st.refresh_poses",     text="",      icon="FILE_REFRESH")
                    box_cfg.operator("ch1st.reset", text="Reset todo", icon="LOOP_BACK")

                    # ── Filtrar bones ─────────────────────────────────────────────────────
                    box_filt = box_cfg.box()
                    row_filt_hdr = box_filt.row(align=True)
                    _filt_icon = "DOWNARROW_HLT" if seg.filter_show else "RIGHTARROW"
                    row_filt_hdr.prop(
                        seg, "filter_show",
                        text="  Filtrar bones",
                        icon=_filt_icon,
                        toggle=True,
                        emboss=False,
                    )
                    if seg.filter_show:
                        box_filt.label(
                            text="Bones marcados NO reciben poses del segmento:",
                            icon="INFO"
                        )
                        # ── Root del personaje (Empty "chicken_1") ─────────────
                        col_flt = box_filt.column(align=True)
                        col_flt.label(text="Root del personaje:")
                        col_flt.prop(seg, "filter_main_bone", text="chicken_1 (Root — pos/rot global)", icon="EMPTY_AXIS")

                        # ── Caderas / columna ──────────────────────────────────
                        col_flt.separator()
                        col_flt.label(text="Caderas / columna:")
                        col_flt.prop(seg, "filter_hips",   icon="BONE_DATA")
                        col_flt.prop(seg, "filter_spine",  icon="BONE_DATA")
                        col_flt.prop(seg, "filter_spine1", icon="BONE_DATA")
                        col_flt.prop(seg, "filter_spine2", icon="BONE_DATA")

                        # ── Cabeza / cuello ────────────────────────────────────
                        col_flt.separator()
                        col_flt.label(text="Cabeza / cuello:")
                        col_flt.prop(seg, "filter_neck", icon="BONE_DATA")
                        col_flt.prop(seg, "filter_face", icon="BONE_DATA")
                        col_flt.prop(seg, "filter_jaw_top", icon="BONE_DATA")
                        col_flt.prop(seg, "filter_jaw_bot", icon="BONE_DATA")

                        # ── Brazos ─────────────────────────────────────────────
                        col_flt.separator()
                        col_flt.label(text="Brazos:")
                        col_flt.prop(seg, "filter_right_arm",      icon="BONE_DATA")
                        col_flt.prop(seg, "filter_right_shoulder", icon="BONE_DATA")
                        col_flt.prop(seg, "filter_right_elbow",    icon="BONE_DATA")
                        col_flt.prop(seg, "filter_left_arm",       icon="BONE_DATA")
                        col_flt.prop(seg, "filter_left_shoulder",  icon="BONE_DATA")
                        col_flt.prop(seg, "filter_left_elbow",     icon="BONE_DATA")

                        # ── Piernas ────────────────────────────────────────────
                        col_flt.separator()
                        col_flt.label(text="Piernas:")
                        col_flt.prop(seg, "filter_right_leg",   icon="BONE_DATA")
                        col_flt.prop(seg, "filter_right_knee",  icon="BONE_DATA")
                        col_flt.prop(seg, "filter_right_ankle", icon="BONE_DATA")
                        col_flt.prop(seg, "filter_left_leg",    icon="BONE_DATA")
                        col_flt.prop(seg, "filter_left_knee",   icon="BONE_DATA")
                        col_flt.prop(seg, "filter_left_ankle",  icon="BONE_DATA")
                        col_flt.prop(seg, "filter_knee_pole_r", icon="BONE_DATA")
                        col_flt.prop(seg, "filter_knee_pole_l", icon="BONE_DATA")

                        # ── Accesorios / no_bone ───────────────────────────────
                        col_flt.separator()
                        col_flt.label(text="Accesorios (no_bone):")
                        col_flt.prop(seg, "filter_no_bone_01", icon="BONE_DATA")
                        col_flt.prop(seg, "filter_no_bone_02", icon="BONE_DATA")
                        col_flt.prop(seg, "filter_no_bone_03", icon="BONE_DATA")
                        col_flt.prop(seg, "filter_no_bone_04", icon="BONE_DATA")
                        col_flt.prop(seg, "filter_no_bone_05", icon="BONE_DATA")
                        col_flt.prop(seg, "filter_no_bone_06", icon="BONE_DATA")

                        # ── Resumen de bones filtrados activos ─────────────────
                        _filtrados = [
                            n for attr, n in [
                                ("filter_main_bone", "chicken_1 (Root)"),
                                ("filter_hips",      "Root_M_chicken_1"),
                                ("filter_spine",     "Spine1_M_chicken_1"),
                                ("filter_spine1",    "Chest_M_chicken_1"),
                                ("filter_spine2",    "Neck_M_chicken_1"),
                                ("filter_neck",      "Head_M_chicken_1"),
                                ("filter_face",      "Jaw_M_chicken_1"),
                                ("filter_jaw_top",   "Jaw_top_chicken_1"),
                                ("filter_jaw_bot",   "Jaw_bot_chicken_1"),
                                ("filter_right_arm",      "Scapula_R_chicken_1"),
                                ("filter_right_shoulder", "Shoulder_R_chicken_1"),
                                ("filter_right_elbow",    "Elbow_R_chicken_1"),
                                ("filter_left_arm",       "Scapula_L_chicken_1"),
                                ("filter_left_shoulder",  "Shoulder_L_chicken_1"),
                                ("filter_left_elbow",     "Elbow_L_chicken_1"),
                                ("filter_right_leg",   "Hip_R_chicken_1"),
                                ("filter_right_knee",  "Knee_R_chicken_1"),
                                ("filter_right_ankle", "Ankle_R_chicken_1"),
                                ("filter_left_leg",    "Hip_L_chicken_1"),
                                ("filter_left_knee",   "Knee_L_chicken_1"),
                                ("filter_left_ankle",  "Ankle_L_chicken_1"),
                                ("filter_knee_pole_r", "Knee.Right_chicken_1"),
                                ("filter_knee_pole_l", "Knee.Left_chicken_1"),
                                ("filter_no_bone_01",  "no_bone_01_chicken_1"),
                                ("filter_no_bone_02",  "no_bone_02_chicken_1"),
                                ("filter_no_bone_03",  "no_bone_03_chicken_1"),
                                ("filter_no_bone_04",  "no_bone_04_chicken_1"),
                                ("filter_no_bone_05",  "no_bone_05_chicken_1"),
                                ("filter_no_bone_06",  "no_bone_06_chicken_1"),
                            ]
                            if getattr(seg, attr, False)
                        ]
                        if _filtrados:
                            box_filt.separator(factor=0.3)
                            box_filt.label(
                                text="Excluidos: " + ", ".join(_filtrados),
                                icon="CHECKMARK"
                            )

                    # ── SEGMENTO activo + CONCATENAR ──────────────────────────────────────
                    box_conc = box_cfg.box()
                    _rng_txt = (
                        f"[{seg.frame_start}→{'?' if seg.single_coord_mode and seg.frame_end_auto <= seg.frame_start else seg.frame_end}]"
                    )
                    box_conc.label(
                        text=f"Segmento activo: {seg.label}  {_rng_txt}",
                        icon="SEQUENCE"
                    )

                    # ── POSES DE ACCION (intermedias) ─────────────────────────────────────
                    box_ac = box_cfg.box()
                    box_ac.label(text="POSES DE ACCION (intermedias)", icon="NLA")
                    row_ac = box_ac.row()
                    row_ac.template_list(
                        "CH1ST_UL_ActionPoses", f"seg_{i}",
                        seg, "action_poses",
                        seg, "action_poses_idx",
                        rows=4,
                    )
                    col_ac = row_ac.column(align=True)
                    op_add_ac = col_ac.operator("ch1seg.add_action_pose_seg",    text="", icon="ADD")
                    op_add_ac.item_idx = i
                    op_rem_ac = col_ac.operator("ch1seg.remove_action_pose_seg", text="", icon="REMOVE")
                    op_rem_ac.item_idx = i
                    col_ac.separator()
                    op_up_ac = col_ac.operator("ch1seg.move_action_pose_seg", text="", icon="TRIA_UP")
                    op_up_ac.item_idx = i; op_up_ac.direction = "UP"
                    op_dn_ac = col_ac.operator("ch1seg.move_action_pose_seg", text="", icon="TRIA_DOWN")
                    op_dn_ac.item_idx = i; op_dn_ac.direction = "DOWN"
                    col_ac.separator()
                    op_ed_ac = col_ac.operator("ch1seg.edit_action_pose_seg", text="", icon="GREASEPENCIL")
                    op_ed_ac.item_idx = i

                    row_add_ac = box_ac.row()
                    row_add_ac.scale_y = 1.4
                    row_add_ac.active_default = True
                    op_add_ac2 = row_add_ac.operator(
                        "ch1seg.add_action_pose_seg",
                        text="  + Agregar pose de accion", icon="ADD"
                    )
                    op_add_ac2.item_idx = i

                    if not seg.action_poses:
                        box_ac.label(text="  Sin acciones: transicion directa", icon="INFO")
                    else:
                        _total_ac = sum(ap.duration for ap in seg.action_poses)
                        box_ac.label(
                            text=f"  {len(seg.action_poses)} poses | {_total_ac} frames totales",
                            icon="TIME"
                        )
                        # Slot activo info
                        if seg.action_poses_idx < len(seg.action_poses):
                            slot = seg.action_poses[seg.action_poses_idx]
                            box_slot = box_ac.box()
                            col_slot = box_slot.column(align=True)
                            col_slot.label(
                                text=f"Slot activo: {slot.pose_name or slot.json_file or '-- vacio --'}"
                            )
                            if getattr(slot, "manual_start", False):
                                col_slot.label(
                                    text=f"Frame de inicio manual: {slot.frame_abs_start}",
                                    icon="KEYFRAME_HLT",
                                )
                            col_slot.prop(slot, "duration",    text="Frames")
                            col_slot.prop(slot, "interp_type", text="Interpolacion")

                    # ── EXTRAER POSE RAPIDA (bones del armature chicken_1) ─────────────
                    # Debajo del sistema de agregar poses (mismo criterio que "4 Extraer
                    # Nueva Pose" del Paso 1, pero automatico: detecta el armature/bones
                    # de chicken_1 solo, nombra la pose segun los huesos que se movieron,
                    # y con "Importar" la agrega directo a esta lista).
                    box_qp = box_ac.box()
                    row_qp_hdr = box_qp.row(align=True)
                    row_qp_hdr.label(text="Extraer pose rapida (bones actuales)", icon="BONE_DATA")
                    row_qp_btn = box_qp.row(align=True)
                    row_qp_btn.scale_y = 1.3
                    row_qp_btn.operator(
                        "ch1seg.quickpose_extract",
                        text="  Guardar pose (bones actuales)", icon="PINNED"
                    )
                    _st_qp = context.scene.ch1st
                    row_qp_imp = box_qp.row(align=True)
                    row_qp_imp.scale_y = 1.3
                    op_qp_imp = row_qp_imp.operator(
                        "ch1seg.quickpose_import",
                        text="  Importar a la lista de poses", icon="IMPORT"
                    )
                    op_qp_imp.item_idx = i
                    if _st_qp.quickpose_pending_file:
                        box_qp.label(
                            text=f"  -> {_st_qp.quickpose_pending_file}  (\"{_st_qp.quickpose_pending_label}\")",
                            icon="INFO"
                        )
                    else:
                        box_qp.label(
                            text="  Mueve los huesos y presiona Guardar",
                            icon="INFO"
                        )

                    # ── Resumen duracion ──────────────────────────────────────────────────
                    if seg.action_poses:
                        box_sum = box_cfg.box()
                        box_sum.label(text="Resumen de duracion:", icon="TIME")
                        _dur_act  = sum(ap.duration for ap in seg.action_poses)
                        _total_fr = _dur_act
                        _fps_sc   = context.scene.render.fps or 24
                        box_sum.label(
                            text=f"  {len(seg.action_poses)} poses de accion  =  {_total_fr}f  ({round(_total_fr/_fps_sc,2)}s)"
                        )

                    # ── CONCATENAR ────────────────────────────────────────────────────────
                    box_conc.separator(factor=0.3)
                    _ready_seg = bool(seg.action_poses)
                    row_conc = box_conc.row()
                    row_conc.scale_y = 2.0
                    row_conc.enabled = _ready_seg
                    _conc_text = (
                        "CONCATENAR"
                        if seg.single_coord_mode
                        else "CONCATENAR  (inyectar poses → bones configurados)"
                    )
                    row_conc.operator("ch1st.concatenate", text=_conc_text, icon="PLAY")
                    if not _ready_seg:
                        box_conc.label(text="  Agrega al menos una pose de accion para continuar", icon="INFO")
                    elif not seg.single_coord_mode:
                        box_conc.label(
                            text="  Inyecta las poses configuradas sobre el desplazamiento del recorrido",
                            icon="INFO"
                        )
                        box_conc.label(
                            text="  Luego presiona REPRODUCIR para agregar caminar/saltar a los bones restantes",
                            icon="INFO"
                        )
                    else:
                        box_conc.label(
                            text="  Genera la animacion de poses dentro del segmento activo",
                            icon="INFO"
                        )
                    box_conc.label(
                        text=f"  Indice de este segmento (para 'Importacion de Objetos'): {i}",
                        icon="INFO"
                    )

                    # ── Filtros Organicos ─────────────────────────────────────────────────
                    box_og = box_cfg.box()
                    org = st.organic
                    row_og_hdr = box_og.row()
                    row_og_hdr.prop(org, "enabled", text="Filtros organicos")
                    if org.enabled:
                        box_b = box_og.box()
                        box_b.prop(org, "breathing_enabled", text="Respiracion (pecho/torso)")
                        if org.breathing_enabled:
                            col_b = box_b.column(align=True)
                            col_b.prop(org, "breathing_amplitude", text="Amplitud")
                            col_b.prop(org, "breathing_speed",     text="Velocidad")
                            col_b.prop(org, "breathing_phase",     text="Fase")
                        box_fl = box_og.box()
                        box_fl.prop(org, "flap_enabled", text="Aleteo de alas (Scapula/Shoulder/Elbow)")
                        if org.flap_enabled:
                            col_fl = box_fl.column(align=True)
                            col_fl.prop(org, "flap_amplitude", text="Amplitud")
                            col_fl.prop(org, "flap_speed",     text="Velocidad")
                            col_fl.prop(org, "flap_openness",  text="Apertura base")
                            col_fl.prop(org, "flap_asymmetry", text="Asimetria L/R")
                        box_h = box_og.box()
                        box_h.prop(org, "head_sway_enabled", text="Cabeceo / picoteo (Neck/Head/Jaw)")
                        if org.head_sway_enabled:
                            col_h = box_h.column(align=True)
                            col_h.prop(org, "head_sway_amplitude", text="Amplitud")
                            col_h.prop(org, "head_sway_speed",     text="Velocidad")
                            col_h.prop(org, "head_sway_seed",      text="Semilla")
                        box_w = box_og.box()
                        box_w.prop(org, "weight_shift_enabled", text="Balanceo de peso (patas)")
                        if org.weight_shift_enabled:
                            col_w = box_w.column(align=True)
                            col_w.prop(org, "weight_shift_amplitude", text="Amplitud")
                            col_w.prop(org, "weight_shift_speed",     text="Velocidad")
                        box_r = box_og.box()
                        box_r.prop(org, "root_noise_enabled", text="Noise posicion ROOT (chicken_1)")
                        if org.root_noise_enabled:
                            col_r = box_r.column(align=True)
                            col_r.prop(org, "root_noise_strength",  text="Intensidad")
                            col_r.prop(org, "root_noise_frequency", text="Frecuencia")
                            col_r.prop(org, "root_noise_seed",      text="Semilla")
                        box_sec = box_og.box()
                        box_sec.prop(org, "secondary_motion_enabled", text="Follow-through de alas (Elbow L/R)")
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
                        box_ms.prop(org, "micro_scale_enabled", text="Micro-escala pecho (Chest)")
                        if org.micro_scale_enabled:
                            box_ms.prop(org, "micro_scale_amplitude", text="Amplitud")
                        box_sh = box_og.box()
                        box_sh.prop(org, "shoulder_noise_enabled", text="Noise de alas (Scapula L/R)")
                        if org.shoulder_noise_enabled:
                            col_sh = box_sh.column(align=True)
                            col_sh.prop(org, "shoulder_noise_amplitude", text="Amplitud")
                            col_sh.prop(org, "shoulder_noise_speed",     text="Velocidad")
                            col_sh.prop(org, "shoulder_noise_seed",      text="Semilla")

                    # ── Oscilaciones de Bones ─────────────────────────────────────────────
                    osc = st.bone_oscillations
                    box_osc = box_cfg.box()
                    row_osc_hdr = box_osc.row()
                    row_osc_hdr.prop(osc, "enabled", text="Oscilaciones de Bones")
                    if osc.enabled:
                        box_osc_list = box_osc.box()
                        box_osc_list.label(text="Lista de oscilaciones:", icon="NLA")
                        if osc.items:
                            for _oi, _oitem in enumerate(osc.items):
                                _row = box_osc_list.row(align=True)
                                _icon_en = "HIDE_OFF" if _oitem.enabled else "HIDE_ON"
                                _op_en = _row.operator("ch1st.bone_osc_toggle_item", text="", icon=_icon_en)
                                _op_en.item_idx = _oi
                                _axes = "".join(a for a, b in [("X", _oitem.axis_x),("Y", _oitem.axis_y),("Z", _oitem.axis_z)] if b) or "?"
                                _row.label(text=f"  {_oitem.label or _oitem.bone_name}  [{_axes}]  ±{_oitem.amplitude:.0f}°  {_oitem.frame_start}\u2192{_oitem.frame_end}")
                                _op_del = _row.operator("ch1st.bone_osc_remove_item", text="", icon="X")
                                _op_del.item_idx = _oi

                                _row_edit = box_osc_list.row(align=True)
                                _row_edit.prop(_oitem, "label", text="Etiqueta")
                                _row_edit.prop(_oitem, "bone_name", text="Bone")

                                _row_edit2 = box_osc_list.row(align=True)
                                _row_edit2.prop(_oitem, "frame_start", text="Inicio")
                                _row_edit2.prop(_oitem, "frame_end", text="Fin")

                                _row_edit3 = box_osc_list.row(align=True)
                                _row_edit3.label(text="Ejes:")
                                _row_edit3.prop(_oitem, "axis_x", toggle=True)
                                _row_edit3.prop(_oitem, "axis_y", toggle=True)
                                _row_edit3.prop(_oitem, "axis_z", toggle=True)

                                _row_edit4 = box_osc_list.row(align=True)
                                _row_edit4.prop(_oitem, "amplitude", text="Amplitud")
                                _row_edit4.prop(_oitem, "phase", text="Fase")

                                _row_edit5 = box_osc_list.row(align=True)
                                _row_edit5.prop(_oitem, "num_cycles", text="Ciclos")
                                _row_edit5.prop(_oitem, "wave_type", text="")

                                _row_edit6 = box_osc_list.row(align=True)
                                _row_edit6.prop(_oitem, "fade_in", text="Fade in")
                                _row_edit6.prop(_oitem, "fade_out", text="Fade out")
                                _row_edit6.prop(_oitem, "noise_seed", text="Semilla")

                                box_osc_list.separator()
                        else:
                            box_osc_list.label(text="  (sin oscilaciones)", icon="INFO")
                        box_osc_edit = box_osc.box()
                        box_osc_edit.label(text="Nueva oscilacion:", icon="ADD")
                        col_oe = box_osc_edit.column(align=True)
                        col_oe.prop(osc, "edit_label",     text="Etiqueta")
                        col_oe.prop(osc, "edit_bone_name", text="Bone")
                        row_of = box_osc_edit.row(align=True)
                        row_of.prop(osc, "edit_frame_start", text="Inicio")
                        row_of.prop(osc, "edit_frame_end",   text="Fin")
                        row_oa = box_osc_edit.row(align=True)
                        row_oa.label(text="Ejes:")
                        row_oa.prop(osc, "edit_axis_x", toggle=True)
                        row_oa.prop(osc, "edit_axis_y", toggle=True)
                        row_oa.prop(osc, "edit_axis_z", toggle=True)
                        col_oamp = box_osc_edit.column(align=True)
                        col_oamp.prop(osc, "edit_amplitude",  text="Amplitud (grad)")
                        col_oamp.prop(osc, "edit_num_cycles", text="Ciclos")
                        col_oamp.prop(osc, "edit_wave_type",  text="Transicion")
                        row_oadd = box_osc_edit.row()
                        row_oadd.scale_y = 1.4
                        _op_oadd = row_oadd.operator("ch1st.bone_osc_add_item", text="+ Agregar oscilacion", icon="CHECKMARK")
                        _op_oadd.quick_bone = ""
                        box_osc.label(text="Las oscilaciones se aplican al CONCATENAR", icon="INFO")

                    # ── Importacion de Objetos ────────────────────────────────────────────
                    try:
                        oi = st.object_imports
                        box_obj = box_cfg.box()
                        row_obj_hdr = box_obj.row()
                        row_obj_hdr.prop(oi, "enabled", text="Importacion de Objetos")
                        if oi.enabled:
                            box_obj_list = box_obj.box()
                            box_obj_list.label(text="Lista de objetos:", icon="OBJECT_DATA")
                            if oi.items:
                                for _ii, _iitem in enumerate(oi.items):
                                    _row_obj = box_obj_list.row(align=True)
                                    _icon_en_obj = "HIDE_OFF" if _iitem.enabled else "HIDE_ON"
                                    _op_en_obj = _row_obj.operator("ch1st.obj_import_toggle_item", text="", icon=_icon_en_obj)
                                    _op_en_obj.item_idx = _ii
                                    _row_obj.label(
                                        text=f"  {_iitem.label or _iitem.object_name}  [{_iitem.object_name}]  {_iitem.frame_start}\u2192{_iitem.frame_end}"
                                    )
                                    _op_del_obj = _row_obj.operator("ch1st.obj_import_remove_item", text="", icon="X")
                                    _op_del_obj.item_idx = _ii

                                    _row_o1 = box_obj_list.row(align=True)
                                    _row_o1.prop(_iitem, "label",          text="Etiqueta")
                                    _row_o1.prop(_iitem, "object_name",    text="Nombre")

                                    _row_o2 = box_obj_list.row(align=True)
                                    _row_o2.prop(_iitem, "object_folder",  text="Carpeta")
                                    _row_o2.prop(_iitem, "blend_filename", text=".blend")

                                    _row_o3 = box_obj_list.row(align=True)
                                    _row_o3.prop(_iitem, "frame_start",    text="Inicio")
                                    _row_o3.prop(_iitem, "frame_end",      text="Fin")

                                    _row_o4 = box_obj_list.row(align=True)
                                    _row_o4.prop(_iitem, "parent_armature", text="Armature")
                                    _row_o4.prop(_iitem, "parent_bone",     text="Bone")

                                    _col_loc = box_obj_list.column(align=True)
                                    _col_loc.label(text="Posicion:", icon="OBJECT_ORIGIN")
                                    _row_loc = _col_loc.row(align=True)
                                    _row_loc.prop(_iitem, "loc_x", text="X")
                                    _row_loc.prop(_iitem, "loc_y", text="Y")
                                    _row_loc.prop(_iitem, "loc_z", text="Z")

                                    _col_rot = box_obj_list.column(align=True)
                                    _col_rot.label(text="Rotacion (grados):", icon="DRIVER_ROTATIONAL_DIFFERENCE")
                                    _row_rot2 = _col_rot.row(align=True)
                                    _row_rot2.prop(_iitem, "rot_x", text="X")
                                    _row_rot2.prop(_iitem, "rot_y", text="Y")
                                    _row_rot2.prop(_iitem, "rot_z", text="Z")

                                    _row_o5 = box_obj_list.row(align=True)
                                    _row_o5.prop(_iitem, "scale_uniform", text="Escala")
                                    _row_o5.prop(_iitem, "levels_up",     text="Niveles arriba")

                                    # ── Transiciones cartoon ──────────────────────────
                                    _box_tr = box_obj_list.box()
                                    _box_tr.label(text="Transiciones cartoon:", icon="ANIM")
                                    _col_tin = _box_tr.column(align=True)
                                    _col_tin.label(text="Aparicion (frame inicio):", icon="KEYFRAME")
                                    _row_tin = _col_tin.row(align=True)
                                    _row_tin.scale_y = 1.1
                                    if hasattr(_iitem, "transition_in"):
                                        _row_tin.prop(_iitem, "transition_in", text="")
                                        if getattr(_iitem, "transition_in", "NONE") != "NONE":
                                            _col_tin.prop(_iitem, "transition_in_duration", text="Duracion entrada (frames)")
                                    else:
                                        _row_tin.label(text="(reinstala el addon)", icon="ERROR")
                                    _col_tout = _box_tr.column(align=True)
                                    _col_tout.label(text="Desaparicion (frame fin):", icon="KEYFRAME_HLT")
                                    _row_tout = _col_tout.row(align=True)
                                    _row_tout.scale_y = 1.1
                                    if hasattr(_iitem, "transition_out"):
                                        _row_tout.prop(_iitem, "transition_out", text="")
                                        if getattr(_iitem, "transition_out", "NONE") != "NONE":
                                            _col_tout.prop(_iitem, "transition_out_duration", text="Duracion salida (frames)")
                                    else:
                                        _row_tout.label(text="(reinstala el addon)", icon="ERROR")

                                    if _iitem.imported_object_name and bpy.data.objects.get(_iitem.imported_object_name):
                                        box_obj_list.label(
                                            text=f"  Vista previa en vivo: '{_iitem.imported_object_name}' "
                                                 f"(los valores se aplican al instante)",
                                            icon="HIDE_OFF"
                                        )
                                    else:
                                        box_obj_list.label(
                                            text="  Presiona CONCATENAR para importar y previsualizar este objeto",
                                            icon="INFO"
                                        )

                                    box_obj_list.separator()
                            else:
                                box_obj_list.label(text="  (sin objetos — agrega uno abajo)", icon="INFO")

                            box_obj_edit = box_obj.box()
                            box_obj_edit.label(text="Nuevo objeto:", icon="ADD")
                            col_oe2 = box_obj_edit.column(align=True)
                            col_oe2.prop(oi, "edit_label",          text="Etiqueta")

                            row_browse2 = box_obj_edit.row(align=True)
                            row_browse2.scale_y = 1.2
                            row_browse2.operator("ch1st.obj_import_browse_blend", text="Buscar .blend...", icon="FILEBROWSER")

                            col_oe2.prop(oi, "edit_object_name",    text="Nombre objeto")
                            col_oe2.prop(oi, "edit_object_folder",  text="Carpeta")
                            col_oe2.prop(oi, "edit_blend_filename", text="Archivo .blend")
                            row_oprev2 = box_obj_edit.row(align=True)
                            row_oprev2.operator("ch1st.obj_import_preview_now", text="Importar .blend al Outliner", icon="IMPORT")
                            row_of2 = box_obj_edit.row(align=True)
                            row_of2.prop(oi, "edit_frame_start", text="Inicio")
                            row_of2.prop(oi, "edit_frame_end",   text="Fin")
                            col_op2 = box_obj_edit.column(align=True)
                            row_arm2 = col_op2.row(align=True)
                            row_arm2.prop(oi, "edit_parent_armature", text="Armature")
                            row_arm2.operator("ch1st.obj_import_detect_armature", text="", icon="VIEWZOOM")
                            col_op2.prop(oi, "edit_parent_bone",     text="Bone")

                            col_tr2 = box_obj_edit.column(align=True)
                            col_tr2.label(text="Posicion:", icon="OBJECT_ORIGIN")
                            row_loc2 = col_tr2.row(align=True)
                            row_loc2.prop(oi, "edit_loc_x", text="X")
                            row_loc2.prop(oi, "edit_loc_y", text="Y")
                            row_loc2.prop(oi, "edit_loc_z", text="Z")

                            col_tr2.label(text="Rotacion (grados):", icon="DRIVER_ROTATIONAL_DIFFERENCE")
                            row_rot4 = col_tr2.row(align=True)
                            row_rot4.prop(oi, "edit_rot_x", text="X")
                            row_rot4.prop(oi, "edit_rot_y", text="Y")
                            row_rot4.prop(oi, "edit_rot_z", text="Z")

                            row_sc2 = box_obj_edit.row(align=True)
                            row_sc2.prop(oi, "edit_scale_uniform", text="Escala")
                            row_sc2.prop(oi, "edit_levels_up",     text="Niveles arriba")

                            # ── Transiciones cartoon ──────────────────────────
                            box_tr2 = box_obj_edit.box()
                            box_tr2.label(text="Transiciones cartoon:", icon="ANIM")
                            col_tin2 = box_tr2.column(align=True)
                            col_tin2.label(text="Aparicion (frame inicio):", icon="KEYFRAME")
                            row_tin2 = col_tin2.row(align=True)
                            row_tin2.scale_y = 1.1
                            if hasattr(oi, "edit_transition_in"):
                                row_tin2.prop(oi, "edit_transition_in", text="")
                                if getattr(oi, "edit_transition_in", "NONE") != "NONE":
                                    col_tin2.prop(oi, "edit_transition_in_duration", text="Duracion entrada (frames)")
                            else:
                                row_tin2.label(text="(reinstala el addon)", icon="ERROR")
                            col_tout2 = box_tr2.column(align=True)
                            col_tout2.label(text="Desaparicion (frame fin):", icon="KEYFRAME_HLT")
                            row_tout2 = col_tout2.row(align=True)
                            row_tout2.scale_y = 1.1
                            if hasattr(oi, "edit_transition_out"):
                                row_tout2.prop(oi, "edit_transition_out", text="")
                                if getattr(oi, "edit_transition_out", "NONE") != "NONE":
                                    col_tout2.prop(oi, "edit_transition_out_duration", text="Duracion salida (frames)")
                            else:
                                row_tout2.label(text="(reinstala el addon)", icon="ERROR")

                            if oi.edit_imported_object_name and bpy.data.objects.get(oi.edit_imported_object_name):
                                box_obj_edit.label(
                                    text=f"  Vista previa en vivo: '{oi.edit_imported_object_name}' "
                                         f"(los valores se aplican al instante)",
                                    icon="HIDE_OFF"
                                )

                            row_oadd2 = box_obj_edit.row()
                            row_oadd2.scale_y = 1.4
                            row_oadd2.operator("ch1st.obj_import_add_item", text="+ Agregar objeto", icon="CHECKMARK")
                            box_obj.label(text="Los objetos se incluyen en el .py al EXPORTAR", icon="INFO")

                    except Exception as _e_obj:
                        box_cfg.label(text=f"[Importacion de Objetos: {_e_obj}]", icon="ERROR")

                    # ── 3d: Lanzar / Recoger Objetos ─────────────────────────────────────
                    try:
                        th = seg.throws
                        box_th = box_cfg.box()

                        # Header con checkbox (se carga automaticamente desde JSON igual que los demas filtros)
                        row_th_hdr = box_th.row(align=True)
                        row_th_hdr.prop(th, "enabled",
                            text="Lanzar / Recoger Objetos", icon="FORCE_WIND")

                        if th.enabled:
                            # ── Lista de items ────────────────────────────────
                            for _ti, _titem in enumerate(th.items):
                                box_ti = box_th.box()
                                box_ti.active = _titem.enabled

                                row_ti_hdr = box_ti.row(align=True)
                                # Toggle activo
                                _icon_en = "HIDE_OFF" if _titem.enabled else "HIDE_ON"
                                _op_tog = row_ti_hdr.operator(
                                    "ch1st.throw_toggle_item", text="", icon=_icon_en)
                                _op_tog.seg_idx = i; _op_tog.item_idx = _ti
                                # Label
                                _mode_icon = "FORCE_WIND" if _titem.mode == 'THROW' else "IMPORT"
                                row_ti_hdr.label(
                                    text=f"  {_titem.label}  [{_titem.object_name}]"
                                         f"  {_titem.frame_start}→{_titem.frame_end}",
                                    icon=_mode_icon)
                                # Botones editar / limpiar / eliminar
                                # (importar + aplicar trayectoria lo hace CONCATENAR)
                                _op_ed = row_ti_hdr.operator(
                                    "ch1st.throw_load_to_editor", text="", icon="GREASEPENCIL")
                                _op_ed.seg_idx = i; _op_ed.item_idx = _ti
                                _op_cl = row_ti_hdr.operator(
                                    "ch1st.throw_clear_keyframes", text="", icon="TRASH")
                                _op_cl.seg_idx = i; _op_cl.item_idx = _ti
                                _op_rm = row_ti_hdr.operator(
                                    "ch1st.throw_remove_item", text="", icon="X")
                                _op_rm.seg_idx = i; _op_rm.item_idx = _ti

                                if _titem.enabled and _titem.imported_object_name:
                                    box_ti.label(
                                        text=f"En escena: '{_titem.imported_object_name}'",
                                        icon="CHECKMARK")

                                # Waypoints del item
                                if _titem.enabled and _titem.waypoints:
                                    box_ti_wp = box_ti.box()
                                    box_ti_wp.label(
                                        text=f"Waypoints ({len(_titem.waypoints)}):",
                                        icon="IPO_BEZIER")
                                    for _wi, _wp in enumerate(_titem.waypoints):
                                        row_wp = box_ti_wp.row(align=True)
                                        row_wp.prop(_wp, "enabled", text="")
                                        row_wp.label(text=f"{_wp.label}  ({_wp.x:.2f},{_wp.y:.2f},{_wp.z:.2f})")
                                        row_wp.prop(_wp, "easing", text="")
                                        _op_wfc = row_wp.operator(
                                            "ch1st.throw_wp_from_cursor", text="", icon="PIVOT_CURSOR")
                                        _op_wfc.seg_idx = i; _op_wfc.item_idx = _ti; _op_wfc.wp_idx = _wi
                                        _op_wrm = row_wp.operator(
                                            "ch1st.throw_remove_waypoint", text="", icon="X")
                                        _op_wrm.seg_idx = i; _op_wrm.item_idx = _ti; _op_wrm.wp_idx = _wi

                            # ── Editor de nuevo / editar item ─────────────────
                            box_edit = box_th.box()
                            box_edit.label(text="Nuevo lanzamiento / editar:", icon="ADD")

                            # Modo
                            row_ed_mode = box_edit.row(align=True)
                            row_ed_mode.scale_y = 1.1
                            row_ed_mode.prop(th, "edit_mode", expand=True)

                            # Etiqueta
                            box_edit.prop(th, "edit_label", text="Etiqueta")

                            # Buscar .blend
                            row_ed_br = box_edit.row(align=True)
                            row_ed_br.scale_y = 1.2
                            _op_br = row_ed_br.operator(
                                "ch1st.throw_browse_blend", text="Buscar .blend...", icon="FILEBROWSER")
                            _op_br.seg_idx = i
                            col_ed = box_edit.column(align=True)
                            col_ed.prop(th, "edit_object_name",   text="Nombre objeto")
                            col_ed.prop(th, "edit_object_folder",  text="Carpeta")
                            col_ed.prop(th, "edit_blend_filename", text="Archivo .blend")
                            col_ed.prop(th, "edit_levels_up",      text="Niveles arriba")

                            # Frames
                            box_edit.separator(factor=0.3)
                            row_ed_f = box_edit.row(align=True)
                            row_ed_f.prop(th, "edit_frame_start", text="Inicio")
                            row_ed_f.prop(th, "edit_frame_end",   text="Fin")

                            # Aparentamiento
                            box_edit.separator(factor=0.3)
                            box_edit.label(text="Aparentamiento:", icon="BONE_DATA")
                            row_ed_arm = box_edit.row(align=True)
                            row_ed_arm.prop(th, "edit_parent_armature", text="Armature")
                            _op_det = row_ed_arm.operator(
                                "ch1st.throw_detect_armature", text="", icon="VIEWZOOM")
                            _op_det.seg_idx = i
                            box_edit.prop(th, "edit_parent_bone", text="Bone")

                            # Grilla de bones
                            _CHICKEN_BONES = [
                                "Root_M_chicken_1","Spine1_M_chicken_1","Chest_M_chicken_1","Neck_M_chicken_1",
                                "Head_M_chicken_1","Jaw_M_chicken_1","Scapula_R_chicken_1","Elbow_R_chicken_1",
                                "Scapula_L_chicken_1","Elbow_L_chicken_1","Hip_R_chicken_1",
                                "Knee_R_chicken_1","Hip_L_chicken_1","Knee_L_chicken_1",
                            ]
                            box_bones = box_edit.box()
                            box_bones.label(text="Bones de Chicken:", icon="BONE_DATA")
                            _tgrid = box_bones.grid_flow(row_major=True, columns=2, align=True)
                            for _bn in _CHICKEN_BONES:
                                _op_tb = _tgrid.operator(
                                    "ch1st.throw_pick_bone", text=_bn, emboss=True,
                                    depress=(th.edit_parent_bone == _bn))
                                _op_tb.seg_idx = i; _op_tb.bone_name = _bn

                            # Offset
                            box_edit.separator(factor=0.3)
                            box_edit.label(text="Offset sobre el bone:", icon="OBJECT_ORIGIN")
                            row_ed_loc = box_edit.row(align=True)
                            row_ed_loc.prop(th, "edit_loc_x", text="X")
                            row_ed_loc.prop(th, "edit_loc_y", text="Y")
                            row_ed_loc.prop(th, "edit_loc_z", text="Z")
                            row_ed_rot = box_edit.row(align=True)
                            row_ed_rot.prop(th, "edit_rot_x", text="X")
                            row_ed_rot.prop(th, "edit_rot_y", text="Y")
                            row_ed_rot.prop(th, "edit_rot_z", text="Z")
                            box_edit.prop(th, "edit_scale_uniform", text="Escala")

                            # Info: el CONCATENAR se encarga de importar y aplicar
                            box_edit.separator(factor=0.3)
                            box_edit.label(
                                text="El CONCATENAR importa el objeto y aplica la trayectoria",
                                icon="INFO")

                            # Destino
                            box_edit.separator(factor=0.3)
                            box_edit.label(text="Referencia de trayectoria:", icon="FORCE_WIND")
                            box_edit.prop(th, "edit_target_bone", text="Bone origen")
                            _mode_lbl = "destino" if th.edit_mode == 'THROW' else "origen"
                            box_edit.label(
                                text=f"Coordenada {_mode_lbl} (mundo):", icon="CURSOR")
                            row_ed_cur = box_edit.row()
                            _op_cur = row_ed_cur.operator(
                                "ch1st.throw_pick_dest_cursor",
                                text="Tomar del cursor 3D", icon="PIVOT_CURSOR")
                            _op_cur.seg_idx = i
                            row_ed_xyz = box_edit.row(align=True)
                            row_ed_xyz.prop(th, "edit_dest_x", text="X")
                            row_ed_xyz.prop(th, "edit_dest_y", text="Y")
                            row_ed_xyz.prop(th, "edit_dest_z", text="Z")
                            box_edit.prop(th, "edit_easing_global", text="Curva general")

                            # Avanzado
                            row_ed_spin = box_edit.row(align=True)
                            row_ed_spin.prop(th, "edit_spin_during_flight", text="Rotacion en vuelo")
                            if th.edit_spin_during_flight:
                                row_ed_spin.prop(th, "edit_spin_turns", text="vueltas")

                            # Waypoints del editor
                            box_edit.separator(factor=0.3)
                            if th.active_idx >= 0 and th.active_idx < len(th.items):
                                row_ed_wp = box_edit.row(align=True)
                                _op_wpa = row_ed_wp.operator(
                                    "ch1st.throw_add_waypoint",
                                    text="+ Waypoint", icon="ADD")
                                _op_wpa.seg_idx = i; _op_wpa.item_idx = th.active_idx; _op_wpa.from_cursor = False
                                _op_wpc = row_ed_wp.operator(
                                    "ch1st.throw_add_waypoint",
                                    text="Desde cursor", icon="PIVOT_CURSOR")
                                _op_wpc.seg_idx = i; _op_wpc.item_idx = th.active_idx; _op_wpc.from_cursor = True

                            # Botones agregar / actualizar
                            box_edit.separator(factor=0.5)
                            row_ed_btns = box_edit.row(align=True)
                            row_ed_btns.scale_y = 1.3
                            _op_add = row_ed_btns.operator(
                                "ch1st.throw_add_item",
                                text="+ Agregar lanzamiento", icon="ADD")
                            _op_add.seg_idx = i
                            if th.active_idx >= 0 and th.active_idx < len(th.items):
                                _op_upd = row_ed_btns.operator(
                                    "ch1st.throw_update_item",
                                    text="Actualizar", icon="FILE_REFRESH")
                                _op_upd.seg_idx = i; _op_upd.item_idx = th.active_idx

                    except Exception as _e_throw:
                        box_cfg.label(text=f"[Lanzar/Recoger: {_e_throw}]", icon="ERROR")
                    # ── Secuencia de Ojos (inline completo) ──────────────────────────────
                    eye_s = st.eye_expr
                    box_eye_root = box_cfg.box()
                    row_eye_hdr = box_eye_root.row()
                    row_eye_hdr.prop(eye_s, "enabled", text="Secuencia de Ojos")
                    box_eye_root.active = eye_s.enabled

                    # A) Frame de inicio
                    box_eya = box_eye_root.box()
                    box_eya.label(text="Frame de inicio  (secuencia de ojos)", icon="TIME")
                    box_eya.prop(st, "eye_global_start_frame", text="Frame inicio ojos")
                    box_eya.label(text="  CONCATENAR_2 inserta keyframes a partir de este frame", icon="INFO")

                    box_eye_root.separator(factor=0.3)

                    # B) Estado inicio de ojos
                    box_eyb = box_eye_root.box()
                    box_eyb.label(text="INICIO  (Ojos)", icon="KEYFRAME")
                    col_eyb = box_eyb.column(align=True)
                    row_eyb = col_eyb.row(align=True)
                    row_eyb.label(text="Duracion:", icon="TIME")
                    row_eyb.prop(st, "eye_start_duration", text="frames")
                    row_eyb2 = col_eyb.row(align=True)
                    row_eyb2.label(text="Interpolacion salida:", icon="IPO_BEZIER")
                    row_eyb2.prop(st, "eye_start_interp", text="")
                    box_eyb.separator(factor=0.3)
                    row_eyb_mode = box_eyb.row(align=True)
                    row_eyb_mode.label(text="Comportamiento:", icon="HIDE_OFF")
                    row_eyb_mode.prop(st, "eye_start_blink_mode", expand=True)
                    if st.eye_start_blink_mode == "BLINK":
                        col_eyb2 = box_eyb.column(align=True)
                        col_eyb2.prop(st, "eye_start_blink_count",    text="Numero parpadeos")
                        col_eyb2.prop(st, "eye_start_blink_duration", text="Frames por parpadeo")
                    else:
                        box_eyb.label(text="  Ojos fijos en posicion base", icon="INFO")

                    box_eye_root.separator(factor=0.3)

                    # C) Cambios intermedios
                    box_eyc = box_eye_root.box()
                    row_chg_hdr = box_eyc.row(align=True)
                    row_chg_hdr.prop(st, "eye_changes_enabled", text="", icon="HIDE_OFF" if st.eye_changes_enabled else "HIDE_ON")
                    row_chg_hdr.label(text="N° CAMBIOS DE OJOS  (intermedios)", icon="NLA")
                    if not st.eye_changes_enabled:
                        box_eyc.label(text="  Sistema desactivado — solo se ejecutara el Parpadeo automatico", icon="INFO")
                    box_eyc.active = st.eye_changes_enabled

                    sub_sk = box_eyc.box()
                    sub_sk.label(text="Setup de Shape Keys de ojos", icon="MESH_PLANE")
                    col_sk = sub_sk.column(align=True)
                    col_sk.prop(eye_s, "subdivide_cuts", text="Subdivisiones previas")
                    row_sk = col_sk.row(align=True)
                    row_sk.prop(eye_s, "swap_axes",         toggle=True)
                    row_sk.prop(eye_s, "invert_vertical",   toggle=True, text="Inv V")
                    row_sk.prop(eye_s, "invert_horizontal", toggle=True, text="Inv H")
                    col_sk.prop(eye_s, "affect_zone", text="Zona")
                    col_sk.prop(eye_s, "curve_mode",  text="Curva")
                    row_build = sub_sk.row()
                    row_build.scale_y = 1.3
                    row_build.operator("ch1st.build_eye_shape_keys", icon="FILE_REFRESH",
                                       text="Crear / Recrear Shape Keys")

                    box_eyc.separator(factor=0.3)
                    row_slots = box_eyc.row()
                    row_slots.template_list(
                        "CH1ST_UL_EyeSlots", "seg_eye",
                        st, "eye_slots",
                        st, "eye_slot_idx",
                        rows=4,
                    )
                    col_slots = row_slots.column(align=True)
                    col_slots.operator("ch1st.add_eye_slot",       text="", icon="ADD")
                    col_slots.operator("ch1st.remove_eye_slot",    text="", icon="REMOVE")
                    col_slots.operator("ch1st.duplicate_eye_slot", text="", icon="COPYDOWN")
                    col_slots.separator()
                    op_up = col_slots.operator("ch1st.move_eye_slot", text="", icon="TRIA_UP");   op_up.direction = "UP"
                    op_dn = col_slots.operator("ch1st.move_eye_slot", text="", icon="TRIA_DOWN"); op_dn.direction = "DOWN"
                    col_slots.separator()
                    col_slots.operator("ch1st.edit_eye_slot", text="", icon="GREASEPENCIL")

                    row_add_sl = box_eyc.row(align=True)
                    row_add_sl.scale_y = 1.4
                    row_add_sl.active_default = True
                    row_add_sl.operator("ch1st.add_eye_slot",              text="  + Agregar",         icon="ADD")
                    row_add_sl.operator("ch1st.duplicate_eye_slot",        text="  Copiar",            icon="COPYDOWN")
                    row_add_sl.operator("ch1st.import_eye_slot_from_json", text="  Importar .json...", icon="FILE_FOLDER")

                    if not st.eye_slots:
                        box_eyc.label(text="  Sin cambios: transicion directa inicio → fin", icon="INFO")
                    else:
                        total_eyc = sum(item.duration for item in st.eye_slots)
                        box_eyc.label(text=f"  {len(st.eye_slots)} estados  |  {total_eyc} frames totales", icon="TIME")
                        if 0 <= st.eye_slot_idx < len(st.eye_slots):
                            sel_ey = st.eye_slots[st.eye_slot_idx]
                            sub_ey = box_eyc.box()
                            row_ey = sub_ey.row(align=True)
                            row_ey.label(text=f"{sel_ey.slot_label}", icon="HIDE_OFF")
                            row_ey.operator("ch1st.edit_eye_slot", icon="GREASEPENCIL", text="Editar...")
                            row_ey2 = sub_ey.row(align=True)
                            row_ey2.prop(sel_ey, "duration",    text="Frames")
                            row_ey2.prop(sel_ey, "interp_type", text="")

                    box_eye_root.separator(factor=0.3)

                    # D) Estado final de ojos
                    box_eyd = box_eye_root.box()
                    box_eyd.label(text="FIN  (Ojos)", icon="KEYFRAME_HLT")
                    col_eyd = box_eyd.column(align=True)
                    row_eyd = col_eyd.row(align=True)
                    row_eyd.label(text="Duracion:", icon="TIME")
                    row_eyd.prop(st, "eye_end_duration", text="frames")
                    row_eyd2 = col_eyd.row(align=True)
                    row_eyd2.label(text="Interpolacion entrada:", icon="IPO_BEZIER")
                    row_eyd2.prop(st, "eye_end_interp", text="")
                    box_eyd.separator(factor=0.3)
                    row_eyd_mode = box_eyd.row(align=True)
                    row_eyd_mode.label(text="Comportamiento:", icon="HIDE_OFF")
                    row_eyd_mode.prop(st, "eye_end_blink_mode", expand=True)
                    if st.eye_end_blink_mode == "BLINK":
                        col_eyd2 = box_eyd.column(align=True)
                        col_eyd2.prop(st, "eye_end_blink_count",    text="Numero parpadeos")
                        col_eyd2.prop(st, "eye_end_blink_duration", text="Frames por parpadeo")
                    else:
                        box_eyd.label(text="  Ojos fijos en posicion base", icon="INFO")

                    box_eye_root.separator(factor=0.3)

                    # E) Parpadeo automatico
                    box_eye_blink = box_eye_root.box()
                    row_blink_hdr = box_eye_blink.row(align=True)
                    row_blink_hdr.prop(eye_s, "blink_enabled", text="", icon="HIDE_OFF" if eye_s.blink_enabled else "HIDE_ON")
                    row_blink_hdr.label(text="Parpadeo automatico — Lista de intervalos", icon="SEQUENCE")
                    if eye_s.blink_enabled:
                        row_bli = box_eye_blink.row()
                        row_bli.template_list(
                            "CH1ST_UL_BlinkIntervals", "seg_blink",
                            st, "blink_intervals",
                            st, "blink_interval_idx",
                            rows=3,
                        )
                        col_bli = row_bli.column(align=True)
                        col_bli.operator("ch1st.blink_interval_add",       text="", icon="ADD")
                        col_bli.operator("ch1st.blink_interval_remove",    text="", icon="REMOVE")
                        col_bli.operator("ch1st.blink_interval_duplicate", text="", icon="COPYDOWN")
                        col_bli.separator()
                        op_bu = col_bli.operator("ch1st.blink_interval_move", text="", icon="TRIA_UP");  op_bu.direction = "UP"
                        op_bd = col_bli.operator("ch1st.blink_interval_move", text="", icon="TRIA_DOWN"); op_bd.direction = "DOWN"
                        if 0 <= st.blink_interval_idx < len(st.blink_intervals):
                            bi = st.blink_intervals[st.blink_interval_idx]
                            sub_bi = box_eye_blink.box()
                            row_bi_hdr = sub_bi.row(align=True)
                            row_bi_hdr.prop(bi, "enabled", text="", icon="HIDE_OFF" if bi.enabled else "HIDE_ON")
                            row_bi_hdr.prop(bi, "label", text="")
                            col_bi = sub_bi.column(align=True)
                            row_rng = col_bi.row(align=True)
                            row_rng.label(text="Rango:", icon="TIME")
                            row_rng.prop(bi, "frame_start", text="Ini")
                            row_rng.prop(bi, "frame_end",   text="Fin")
                            row_cnt = col_bi.row(align=True)
                            row_cnt.prop(bi, "blink_count",    text="N° parpadeos")
                            row_cnt.prop(bi, "blink_duration", text="Frames/parpadeo")
                        elif not st.blink_intervals:
                            box_eye_blink.label(text="  + Agrega un intervalo para definir cuando parpadea", icon="INFO")
                        total_blinks = sum(b.blink_count for b in st.blink_intervals if b.enabled)
                        if st.blink_intervals:
                            box_eye_blink.label(
                                text=f"  {len([b for b in st.blink_intervals if b.enabled])} intervalos activos  |  {total_blinks} parpadeos totales",
                                icon="TIME",
                            )
                    else:
                        box_eye_blink.label(text="  Activar para insertar parpadeos automaticos por intervalos", icon="INFO")

                    # E2) Expresiones de ojos
                    box_ei = box_eye_root.box()
                    row_ei_hdr = box_ei.row(align=True)
                    row_ei_hdr.prop(eye_s, "expr_intervals_enabled", text="",
                                    icon="HIDE_OFF" if eye_s.expr_intervals_enabled else "HIDE_ON")
                    row_ei_hdr.label(text="Expresiones de ojos — Lista de intervalos", icon="SHAPEKEY_DATA")
                    if eye_s.expr_intervals_enabled:
                        row_ei_lst = box_ei.row()
                        row_ei_lst.template_list(
                            "CH1ST_UL_EyeExprIntervals", "seg_expr",
                            st, "expr_intervals",
                            st, "expr_interval_idx",
                            rows=3,
                        )
                        col_ei2 = row_ei_lst.column(align=True)
                        col_ei2.operator("ch1st.expr_interval_add",       text="", icon="ADD")
                        col_ei2.operator("ch1st.expr_interval_remove",    text="", icon="REMOVE")
                        col_ei2.operator("ch1st.expr_interval_duplicate", text="", icon="COPYDOWN")
                        col_ei2.separator()
                        op_eu = col_ei2.operator("ch1st.expr_interval_move", text="", icon="TRIA_UP");  op_eu.direction = "UP"
                        op_ed = col_ei2.operator("ch1st.expr_interval_move", text="", icon="TRIA_DOWN"); op_ed.direction = "DOWN"
                        if 0 <= st.expr_interval_idx < len(st.expr_intervals):
                            ei = st.expr_intervals[st.expr_interval_idx]
                            sub_ei = box_ei.box()
                            row_ei_top = sub_ei.row(align=True)
                            row_ei_top.prop(ei, "enabled", text="", icon="HIDE_OFF" if ei.enabled else "HIDE_ON")
                            row_ei_top.prop(ei, "label", text="")
                            col_ei3 = sub_ei.column(align=True)
                            row_frames = col_ei3.row(align=True)
                            row_frames.label(text="Inicio:", icon="KEYFRAME")
                            row_frames.prop(ei, "frame_start", text="")
                            row_frames.label(text="Pico:")
                            row_frames.prop(ei, "frame_peak",  text="")
                            row_frames.label(text="Fin:", icon="KEYFRAME_HLT")
                            row_frames.prop(ei, "frame_end",   text="")
                            row_expr = col_ei3.row(align=True)
                            row_expr.label(text="Expresion:", icon="SHAPEKEY_DATA")
                            row_expr.prop(ei, "expression", text="")
                            row_expr.prop(ei, "expression_value", text="Intensidad")
                            row_itp_ei = col_ei3.row(align=True)
                            row_itp_ei.label(text="Interp entrada:", icon="IPO_BEZIER")
                            row_itp_ei.prop(ei, "interp_in",  text="")
                            row_itp_ei.label(text="Interp salida:")
                            row_itp_ei.prop(ei, "interp_out", text="")
                        elif not st.expr_intervals:
                            box_ei.label(text="  + Agrega un intervalo de expresion de ojos", icon="INFO")
                        active_ei_list = [e for e in st.expr_intervals if e.enabled]
                        if st.expr_intervals:
                            box_ei.label(text=f"  {len(active_ei_list)} intervalos activos en la timeline", icon="TIME")
                        box_ei.label(text="  Los intervalos pueden solaparse con el parpadeo", icon="INFO")
                    else:
                        box_ei.label(text="  Activar para definir emociones por intervalos de frames", icon="INFO")

                    box_eye_root.label(text="  Ambos sistemas se ejecutan al presionar CONCATENAR_2", icon="INFO")
                    box_eye_root.separator(factor=0.3)

                    # F) Resumen + CONCATENAR_2
                    box_eysum = box_eye_root.box()
                    box_eysum.label(text="Resumen de duracion de ojos:", icon="TIME")
                    _dur_ini_ey = st.eye_start_duration
                    _dur_mid_ey = sum(item.duration for item in st.eye_slots) if st.eye_slots else 0
                    _dur_fin_ey = st.eye_end_duration
                    _total_ey   = _dur_ini_ey + _dur_mid_ey + _dur_fin_ey
                    box_eysum.label(text=f"  Inicio {_dur_ini_ey}f  +  Cambios {_dur_mid_ey}f  +  Fin {_dur_fin_ey}f  =  {_total_ey}f total")
                    box_eysum.label(
                        text=f"  Desde frame {st.eye_global_start_frame}  →  hasta frame {st.eye_global_start_frame + _total_ey - 1}",
                        icon="KEYFRAME",
                    )

                    row_cat2 = box_eye_root.row()
                    row_cat2.scale_y = 2.0
                    row_cat2.operator("ch1st.concatenate_2", text="  CONCATENAR_2  (Ojos)", icon="PLAY")

                    row_rst_ey = box_eye_root.row()
                    row_rst_ey.scale_y = 1.4
                    row_rst_ey.alert = True
                    row_rst_ey.operator("ch1st.reset_eye_sequence", text="  RESET  Sistema de Ojos", icon="LOOP_BACK")

                else:
                    # Resumen compacto cuando esta colapsado
                    col_info = box_seg.column(align=True)
                    col_info.scale_y = 0.75
                    if seg.pose_mid_label or seg.pose_mid_file:
                        col_info.label(text=f"  Interm: {seg.pose_mid_label or seg.pose_mid_file}  fr{seg.frame_mid}", icon="DOT")
        else:
            box_list.label(text="  (sin segmentos — crea uno arriba)", icon="INFO")
