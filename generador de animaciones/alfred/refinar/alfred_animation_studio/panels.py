# -*- coding: utf-8 -*-
"""
panels.py — Alfred Animation Studio v1.8
Paneles UI: Main, Setup, Sequence, OrganicFilters, EyeExpressions,
Export, ConfigSession, Extract. UIList de slots.
"""
import bpy
import os
from bpy.types import Panel, UIList
from .constants import INTERP_TYPE_ITEMS
from .properties import ensure_eye_shapekey_migrated, ensure_expr_interval_shapekey_independent
from .operators_segments import _calc_seg_frames, _find_alfred_armature


def _draw_parada_anim_row(layout, pt, idx):
    """NUEVO (Kebyn, 2026-09-13): fila auxiliar (en paralelo al campo
    'Frames') que aparece bajo cada punto marcado como 'Parada' en la
    lista "Coordenadas seleccionadas" (Paso 1). Deja importar un script
    .py de animacion (ej. exportado por el conversor de Mixamo, mismo
    formato que slot_001_parado_discutiendo_dba2c3.py) para que ESE
    punto de parada reproduzca esa animacion completa en vez de la pose
    estatica por defecto al apretar "Reproducir recorrido" -- ver
    ALFREDPR_OT_ImportParadaAnim / anim_file_path en
    generate_parada() (generate_slots_alfred.py).

    Si el punto ya tiene una animacion asociada, se muestra su nombre
    (recortado si es muy largo) con un boton 'X' para quitarla; si no,
    se muestra el boton para elegir el archivo.
    """
    row_anim = layout.row(align=True)
    row_anim.separator(factor=2.2)
    if pt.parada_anim_file:
        anim_name = os.path.basename(pt.parada_anim_file)
        if len(anim_name) > 26:
            anim_name = anim_name[:23] + "..."
        row_anim.label(text=f"Animacion: {anim_name}", icon="ARMATURE_DATA")
        op_clear_anim = row_anim.operator(
            "alfredpr.clear_parada_anim", text="", icon="X", emboss=False)
        op_clear_anim.index = idx
    else:
        op_imp_anim = row_anim.operator(
            "alfredpr.import_parada_anim",
            text="Importar animacion (.py)", icon="FILEBROWSER")
        op_imp_anim.index = idx


def _draw_interaccion_row(layout, pt, idx):
    """NUEVO (Kebyn): fila auxiliar que aparece bajo un punto marcado
    como 'Interactuar' -- solo puede estar marcado asi si el punto es un
    punto de encuentro real con el recorrido de Jerry (ver
    _point_is_meeting_point()/_tipo_segmento_items() en
    path_recorder.py). Deja elegir, de un dropdown, cual de los .py de
    DEFAULT_INTERACTION_DIR_ALFRED reproducir aqui.
    """
    row = layout.row(align=True)
    row.separator(factor=2.2)
    row.label(text="Interactuar con:", icon="COMMUNITY")
    row.prop(pt, "interaccion_anim_choice", text="")
    row.operator(
        "alfredpr.open_interaction_folder", text="", icon="FILEBROWSER")
    if pt.interaccion_anim_choice == "NONE":
        row_warn = layout.row(align=True)
        row_warn.separator(factor=2.2)
        row_warn.label(
            text="Todavia no hay animaciones .py en la carpeta de interaccion",
            icon="ERROR")


def _draw_parada_rot_row(layout, pt, idx):
    """NUEVO (Kebyn, 2026-09-13): fila auxiliar bajo cada punto marcado
    como 'Parada' que deja rotar el empty root ('alfred') a mano y
    guardar esa orientacion para este punto -- ver
    ALFREDPathPoint.parada_rot_saved/parada_rot_z y
    ALFREDPR_OT_RotateParadaRoot / ALFREDPR_OT_SaveParadaRot /
    ALFREDPR_OT_ClearParadaRot (path_recorder.py). Mientras la
    orientacion este guardada, se usa como heading desde este punto de
    parada en adelante (Pasos 2 y 3) hasta el proximo tramo con
    desplazamiento real o hasta que se vuelva a editar.
    """
    row_rot = layout.row(align=True)
    row_rot.separator(factor=2.2)
    op_rot = row_rot.operator(
        "alfredpr.rotate_parada_root", text="Rotar root (alfred)", icon="ORIENTATION_GIMBAL")
    if pt.parada_rot_saved:
        row_rot.label(text=f"Orientacion: {pt.parada_rot_z:.1f}°", icon="CHECKMARK")
        op_clear_rot = row_rot.operator(
            "alfredpr.clear_parada_rot", text="", icon="X", emboss=False)
        op_clear_rot.index = idx
    else:
        op_save_rot = row_rot.operator(
            "alfredpr.save_parada_rot", text="Guardar orientacion", icon="FILE_TICK")
        op_save_rot.index = idx


# NUEVO (Kebyn, fix "ultimo punto sin aviso"): tipos de tramo que abarcan
# ESTE punto y el SIGUIENTE (el personaje camina hasta el proximo punto y
# ahi hace la accion) -- ver comentario de uso en el 'else' de "Ultimo
# punto" mas abajo (draw() del panel de recorrido) y _detect_move()/
# calcular_estimacion_geometrica() en path_recorder.py, que solo miran
# seg_pts[0] (nunca el ultimo punto de la lista) para decidir el tipo de
# tramo real.
_TIPOS_REQUIEREN_PUNTO_SIGUIENTE = (
    "COLOCAR_ANTORCHA", "GOLPE_ESTOMAGO_1", "COLOCAR_MESA_CRAFTEO",
    "LEVANTARSE_1", "LEVANTARSE_2", "ARRODILLARSE_1", "CONVERSAR_1",
    "RESBALARSE_1",
)
# NUEVO (Kebyn, "crear pared no debe pedir punto siguiente"): a diferencia
# de los tipos de arriba, "Crear pared NxN bloques" NO necesita un punto
# siguiente real -- la pared siempre se planta 1m adelante del personaje
# segun su orientacion actual (ver el caso "degenerado" points[0]==points[1]
# en _compute_object_placement_target()/_compute_wall_grid_coords(),
# generate_slots_alfred.py, y el fix equivalente al final de
# _group_segments_legacy() en path_recorder.py/generate_slots_alfred.py).
# Por eso se saco de _TIPOS_REQUIEREN_PUNTO_SIGUIENTE y se dibuja su propia
# fila de configuracion tambien en el ULTIMO punto (ver mas abajo).


def _draw_pared_nxn_row(layout, pt, idx):
    """NUEVO (Kebyn, "crear pared NxN bloques"): fila auxiliar bajo cada
    punto marcado como 'Crear pared NxN bloques' -- deja elegir el
    archivo .blend del bloque de 1m3 a importar (ruta libre, a mano) y
    la cantidad de filas/columnas de la grilla. Mismo patron que
    _draw_parada_anim_row()/_draw_parada_rot_row() de arriba. Ver
    ALFREDPathPoint.pared_bloque_blend_path/pared_filas/pared_columnas
    (path_recorder.py) y generate_crear_pared_nxn()
    (generate_slots_alfred.py).
    """
    row_blk = layout.row(align=True)
    row_blk.separator(factor=2.2)
    row_blk.prop(pt, "pared_bloque_blend_path", text="Bloque (.blend)")
    row_dim = layout.row(align=True)
    row_dim.separator(factor=2.2)
    row_dim.label(text="Pared:", icon="MESH_GRID")
    row_dim.prop(pt, "pared_filas", text="Filas")
    row_dim.prop(pt, "pared_columnas", text="Columnas")
    # NUEVO (Kebyn, "elegir cuantos frames dura toda la animacion de
    # crear pared"): 0 = automatico -- ver pared_total_frames
    # (path_recorder.py) y resolve_pared_nxn_timing()
    # (generate_slots_alfred.py).
    row_dur = layout.row(align=True)
    row_dur.separator(factor=2.2)
    row_dur.prop(pt, "pared_total_frames", text="Duracion total (frames)")
    if not (pt.pared_bloque_blend_path or "").strip():
        row_warn = layout.row(align=True)
        row_warn.separator(factor=2.2)
        row_warn.label(
            text="Elegi el archivo .blend del bloque antes de generar",
            icon="ERROR")


class ALFST_UL_ActionPoses(UIList):
    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.label(text="", icon="POSE_HLT")
            col = row.column()
            col.label(text=item.pose_name)
            sub = row.row()
            sub.alignment = "RIGHT"
            # Calificacion (1-10) si ya se evaluo esta pose alguna vez
            rating_count = getattr(item, "rating_count_cache", 0)
            if rating_count > 0:
                rating_avg = getattr(item, "rating_avg_cache", 0.0)
                rating_icon = (
                    "SOLO_ON" if rating_avg >= 8.0 else
                    "QUESTION" if rating_avg >= 5.0 else
                    "ERROR"
                )
                sub.label(text=f"{rating_avg:.1f}/10", icon=rating_icon)
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

class ALFST_PT_Main(Panel):
    bl_label       = "Alfred Animation Studio"
    bl_idname      = "ALFST_PT_main"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Alfred Studio"
    bl_order       = 1

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Alfred Animation Studio  v1.3", icon="ARMATURE_DATA")
        row_open = layout.row()
        row_open.scale_y = 1.2
        row_open.operator("alfst.open_alfred_blend", text="Abrir alfred.blend", icon="FILE_BLEND")
        row = layout.row()
        row.scale_y = 1.3
        row.alert   = True
        row.operator("alfst.reset", text="RESET  -  Limpiar escena", icon="TRASH")




class ALFST_PT_OrganicFilters(Panel):
    bl_label       = "3  Filtros Organicos"
    bl_idname      = "ALFST_PT_organic"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Alfred Studio"
    bl_parent_id   = "ALFST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        # Se oculta cuando hay segmentos: el panel de segmentos los incluye inline
        segs = getattr(context.scene, "alfred_segs", None)
        if segs is not None and len(segs.segments) > 0:
            return False
        return True

    def draw_header(self, context):
        org = context.scene.alfst.organic
        self.layout.prop(org, "enabled", text="")

    def draw(self, context):
        layout = self.layout
        st  = context.scene.alfst
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
        row.label(text="Respiracion (Spine/Spine1)", icon="FORCE_WIND")
        if org.breathing_enabled:
            col = box.column(align=True)
            col.prop(org, "breathing_amplitude", text="Amplitud")
            col.prop(org, "breathing_speed",     text="Velocidad")
            col.prop(org, "breathing_phase",     text="Fase")

        # ── Micro-movimiento de cabeza ──
        box = layout.box()
        row = box.row()
        row.prop(org, "head_sway_enabled", text="")
        row.label(text="Micro-movimiento cabeza (Neck/face)", icon="BONE_DATA")
        if org.head_sway_enabled:
            col = box.column(align=True)
            col.prop(org, "head_sway_amplitude", text="Amplitud")
            col.prop(org, "head_sway_speed",     text="Velocidad")
            col.prop(org, "head_sway_seed",      text="Semilla")

        # ── Desplazamiento de peso ──
        box = layout.box()
        row = box.row()
        row.prop(org, "weight_shift_enabled", text="")
        row.label(text="Desplazamiento de peso (Hips)", icon="CON_LOCLIKE")
        if org.weight_shift_enabled:
            col = box.column(align=True)
            col.prop(org, "weight_shift_amplitude", text="Amplitud")
            col.prop(org, "weight_shift_speed",     text="Velocidad")

        # ── Noise hombros ──
        box = layout.box()
        row = box.row()
        row.prop(org, "shoulder_noise_enabled", text="")
        row.label(text="Noise hombros (UpArm L/R)", icon="MOD_NOISE")
        if org.shoulder_noise_enabled:
            col = box.column(align=True)
            col.prop(org, "shoulder_noise_amplitude", text="Amplitud")
            col.prop(org, "shoulder_noise_speed",     text="Velocidad")
            col.prop(org, "shoulder_noise_seed",      text="Semilla")

        # ── Secondary motion ──
        box = layout.box()
        row = box.row()
        row.prop(org, "secondary_motion_enabled", text="")
        row.label(text="Secondary motion codos", icon="CON_FOLLOWPATH")
        if org.secondary_motion_enabled:
            col = box.column(align=True)
            col.prop(org, "secondary_motion_lag",     text="Retardo (frames)")
            col.prop(org, "secondary_motion_damping", text="Amortiguacion", slider=True)

        # ── Micro-escala ──
        box = layout.box()
        row = box.row()
        row.prop(org, "micro_scale_enabled", text="")
        row.label(text="Micro-escala organica (Spine1)", icon="FULLSCREEN_ENTER")
        if org.micro_scale_enabled:
            box.prop(org, "micro_scale_amplitude", text="Amplitud")

        # ── Noise ROOT ──
        box = layout.box()
        row = box.row()
        row.prop(org, "root_noise_enabled", text="")
        row.label(text="Noise posicion ROOT (alfred)", icon="EMPTY_AXIS")
        if org.root_noise_enabled:
            col = box.column(align=True)
            col.prop(org, "root_noise_strength",   text="Intensidad")
            col.prop(org, "root_noise_frequency",  text="Frecuencia")
            col.prop(org, "root_noise_seed",       text="Semilla")

        layout.separator()
        layout.label(text="Los filtros se aplican al presionar CONCATENAR", icon="INFO")




class ALFST_PT_Export(Panel):
    bl_label       = "3  Exportar / Importar"
    bl_idname      = "ALFST_PT_export"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Alfred Studio"
    bl_parent_id   = "ALFST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        st     = context.scene.alfst

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
                seg_cfg = context.scene.alfred_segs
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
                seg_cfg  = context.scene.alfred_segs
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
                pc_disp  = context.scene.alfred_path
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
            pc     = context.scene.alfred_path
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
        row.operator("alfst.export_animation", text="EXPORTAR slot_NNN_tipo.py", icon="FILE_SCRIPT")
        if not st.anim_generated:
            box.label(text="  Genera la animacion primero", icon="INFO")
        if st.last_export_path:
            box.label(text=f"  OK: {os.path.basename(st.last_export_path)}", icon="CHECKMARK")

        layout.separator()

        box = layout.box()
        box.label(text="Importar animacion .py", icon="IMPORT")
        row = box.row()
        row.scale_y = 1.4
        row.operator("alfst.import_animation", text="Seleccionar .py...", icon="FILE_FOLDER")

class ALFST_PT_ConfigSession(Panel):
    bl_label       = "5  Guardar / Importar Configuracion"
    bl_idname      = "ALFST_PT_config_session"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Alfred Studio"
    bl_parent_id   = "ALFST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        st     = context.scene.alfst

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
        box_dir.operator("alfst.open_config_folder",
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
        row_save.operator("alfst.save_config",
                          text="  GUARDAR CONFIGURACION  (.json)", icon="FILE_TICK")

        layout.separator()

        # ─── IMPORTAR ───
        box_load = layout.box()
        box_load.label(text="IMPORTAR configuracion guardada", icon="FILE_FOLDER")
        box_load.label(text="  Restaura toda la secuencia de poses,", icon="INFO")
        box_load.label(text="  interpolaciones y ajustes de la sesion.")

        row_load = box_load.row()
        row_load.scale_y = 1.7
        row_load.operator("alfst.load_config",
                          text="  IMPORTAR CONFIGURACION  (.json)", icon="FILE_FOLDER")


class ALFST_PT_Extract(Panel):
    bl_label       = "4  Extraer Nueva Pose"
    bl_idname      = "ALFST_PT_extract"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Alfred Studio"
    bl_parent_id   = "ALFST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        st     = context.scene.alfst
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
        row.operator("alfst.extract_pose", text="GUARDAR COMO NUEVA POSE", icon="PINNED")

        # Boton actualizar poses (para que la nueva pose aparezca en los selectores)
        row2 = box.row(align=True)
        row2.scale_y = 1.2
        row2.operator("alfst.refresh_poses", text="Actualizar lista de poses", icon="FILE_REFRESH")
        row2.operator("alfst.import_pose", text="Importar pose", icon="IMPORT")

        row3 = box.row()
        row3.scale_y = 1.4
        row3.operator("alfst.apply_imported_pose", text="EJECUTAR POSE EN EL PERSONAJE", icon="PLAY")

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

class ALFST_UL_EyeLibEntries(UIList):
    """UIList para la libreria de expresiones de ojos"""
    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.label(text="", icon="ASSET_MANAGER")
            row.label(text=item.name)
        elif self.layout_type == "GRID":
            layout.label(text=item.name)


class ALFST_UL_EyeSlots(UIList):
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


class ALFST_UL_BlinkIntervals(UIList):
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


class ALFST_UL_LaughIntervals(UIList):
    """Lista de intervalos del filtro 'Reir' (oscilacion vertical de ojos)"""
    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.prop(item, "enabled", text="",
                     icon="HIDE_OFF" if item.enabled else "HIDE_ON")
            row.label(text=item.label, icon="MOD_SIMPLEDEFORM")
            sub = row.row()
            sub.alignment = "RIGHT"
            sub.label(text=f"{item.frame_start}→{item.frame_end}")
            sub.label(text=f"x{item.oscillation_count}")
        elif self.layout_type == "GRID":
            layout.label(text=item.label)


class ALFST_UL_UnderstandIntervals(UIList):
    """Lista de intervalos del filtro 'Entendiendo' (glance parabolico de ojos)"""
    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.prop(item, "enabled", text="",
                     icon="HIDE_OFF" if item.enabled else "HIDE_ON")
            row.label(text=item.label, icon="TRACKING_FORWARDS")
            sub = row.row()
            sub.alignment = "RIGHT"
            sub.label(text=f"{item.frame_start}→{item.frame_end}")
            sub.label(text="Izq" if item.direction == "IZQUIERDA" else "Der")
        elif self.layout_type == "GRID":
            layout.label(text=item.label)


class ALFST_UL_EyeExprIntervals(UIList):
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
            # Frame de inicio absoluto — EN VIVO (Kebyn, 2026-09-06 ter:
            # "no esta detectando la secuencia de frames, no se estan
            # sumando como en el sistema de poses"). item.frame_abs_start
            # SOLO se escribe de verdad al presionar "Concatenar
            # expresiones" (o "Concatenar segmentos") -- igual que
            # AlfredSegmentPoseSlot.frame_abs_start solo se escribe al
            # presionar CONCATENAR. Para que la lista siempre refleje el
            # encadenado real apenas se agrega/reordena/activa una
            # expresion (sin tener que ejecutar nada), se recalcula aca
            # mismo en el draw con resolve_pose_start_frames, usando solo
            # los items ACTIVOS hasta e incluyendo este (mismo criterio de
            # encadenado que usa el boton). 'data' es la coleccion dueña
            # (seg o st) pasada a template_list -- expone .expr_intervals
            # y .frame_start (segmento) / .eye_global_start_frame (global).
            _fs_display = item.frame_abs_start
            try:
                from .pose_utils import resolve_pose_start_frames
                _coll = getattr(data, "expr_intervals", None)
                _start = getattr(data, "frame_start", None)
                if _start is None:
                    _start = getattr(data, "eye_global_start_frame", 1)
                if _coll is not None and item.enabled:
                    _active = [e for e in _coll if e.enabled]
                    _ptrs = [e.as_pointer() for e in _active]
                    _pos = _ptrs.index(item.as_pointer())
                    _resolved = resolve_pose_start_frames(_active[:_pos + 1], _start)
                    _fs_display = _resolved[-1]
            except Exception:
                pass
            _fs_icon = "KEYFRAME_HLT" if getattr(item, "manual_start", False) else "KEYFRAME"
            sub.label(text=f"@f{_fs_display}", icon=_fs_icon)
            sub.label(text=f"{item.duration}f")
        elif self.layout_type == "GRID":
            layout.label(text=item.label)


# =============================================================================
# HELPERS DE DIBUJO
# =============================================================================

def _draw_eye_state_transforms(layout, data_src, prefix_or_item, is_item=False):
    """
    Dibuja Expresion + Geometria + Loc/Rot/Sca para ambos ojos.
    Si is_item=True, data_src es el AlfredEyeSlotItem (acceso directo a atributos).
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
# HELPER: leer bones desde historia_alfred JSON
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
        st = context.scene.alfst
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


def _get_bones_from_alfred_json(context):
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
        st = context.scene.alfst
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
        print(f"[AlfredStudio] _get_bones_from_alfred_json error: {e}")
        return []


# =============================================================================
# PANEL: OSCILACIONES DE BONES (Alfred)
# =============================================================================

class ALFST_PT_BoneOscillations(Panel):
    bl_label       = "3b  Oscilaciones de Bones"
    bl_idname      = "ALFST_PT_bone_osc"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Alfred Studio"
    bl_parent_id   = "ALFST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        segs = getattr(context.scene, "alfred_segs", None)
        if segs is not None and len(segs.segments) > 0:
            return False
        return True

    def draw_header(self, context):
        osc = context.scene.alfst.bone_oscillations
        self.layout.prop(osc, "enabled", text="")

    def draw(self, context):
        layout = self.layout
        st  = context.scene.alfst
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
                op_sel = row_item.operator("alfst.bone_osc_toggle_item", text="", icon=icon_sel, emboss=False)
                op_sel.item_idx = i

                icon_en = "HIDE_OFF" if item.enabled else "HIDE_ON"
                op_en = row_item.operator("alfst.bone_osc_toggle_item", text="", icon=icon_en)
                op_en.item_idx = i

                wave_icon = {"SINE": "MOD_WAVE", "TRIANGLE": "GRAPH",
                             "SQUARE": "SNAP_INCREMENT", "NOISE": "MOD_NOISE"}.get(item.wave_type, "MOD_WAVE")
                axes_str = "".join(a for a, b in [("X", item.axis_x), ("Y", item.axis_y), ("Z", item.axis_z)] if b) or "?"
                label_text = (
                    f"  {item.label or item.bone_name}  [{item.bone_name}]  "
                    f"{axes_str}  \xb1{item.amplitude:.0f}\xb0  {item.frame_start}\u2192{item.frame_end}"
                )
                row_item.label(text=label_text[:56], icon=wave_icon)

                op_dup = row_item.operator("alfst.bone_osc_duplicate_item", text="", icon="DUPLICATE")
                op_dup.item_idx = i
                op_del = row_item.operator("alfst.bone_osc_remove_item", text="", icon="X")
                op_del.item_idx = i

            if len(osc.items) > 1:
                row_move = box_list.row(align=True)
                op_up = row_move.operator("alfst.bone_osc_move_item", text="Subir",  icon="TRIA_UP")
                op_up.direction = "UP"
                op_dn = row_move.operator("alfst.bone_osc_move_item", text="Bajar",  icon="TRIA_DOWN")
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

        # ── BONES DETECTADOS DESDE historia_alfred_2.json ───────────────────
        bones_json = _get_bones_from_historia(context)
        box_bones = box_edit.box()

        if bones_json:
            import bpy as _bpy, os as _os
            json_name = _os.path.basename(_bpy.path.abspath(st.historia_json))
            row_bh = box_bones.row()
            row_bh.label(text=f"Bones del personaje  ({json_name}):", icon="BONE_DATA")
            grid = box_bones.grid_flow(row_major=True, columns=2, align=True)
            for bone_name in bones_json:
                op_b = grid.operator("alfst.bone_osc_pick_bone", text=bone_name, emboss=True)
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
        op_add = row_add.operator("alfst.bone_osc_add_item", text="+ Agregar oscilacion", icon="CHECKMARK")
        op_add.quick_bone = ""

        layout.separator()
        layout.label(text="Las oscilaciones se aplican al presionar CONCATENAR", icon="INFO")


# =============================================================================
# PANEL: IMPORTACION DE OBJETOS (armas, escudos, props)
# =============================================================================

class ALFST_PT_ObjectImports(Panel):
    bl_label       = "3c  Importacion de Objetos"
    bl_idname      = "ALFST_PT_object_imports"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Alfred Studio"
    bl_parent_id   = "ALFST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        segs = getattr(context.scene, "alfred_segs", None)
        if segs is not None and len(segs.segments) > 0:
            return False
        return True

    def draw_header(self, context):
        oi = context.scene.alfst.object_imports
        self.layout.prop(oi, "enabled", text="")

    def draw(self, context):
        layout = self.layout
        st = context.scene.alfst
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
                op_sel = row_item.operator("alfst.obj_import_toggle_item", text="", icon=icon_sel, emboss=False)
                op_sel.item_idx = i

                icon_en = "HIDE_OFF" if item.enabled else "HIDE_ON"
                op_en = row_item.operator("alfst.obj_import_toggle_item", text="", icon=icon_en)
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

                op_edit = row_item.operator("alfst.obj_import_load_to_editor", text="", icon="GREASEPENCIL")
                op_edit.item_idx = i
                op_dup = row_item.operator("alfst.obj_import_duplicate_item", text="", icon="DUPLICATE")
                op_dup.item_idx = i
                op_del = row_item.operator("alfst.obj_import_remove_item", text="", icon="X")
                op_del.item_idx = i

            if len(oi.items) > 1:
                row_move = box_list.row(align=True)
                op_up = row_move.operator("alfst.obj_import_move_item", text="Subir",  icon="TRIA_UP")
                op_up.direction = "UP"
                op_dn = row_move.operator("alfst.obj_import_move_item", text="Bajar",  icon="TRIA_DOWN")
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
        row_browse.operator("alfst.obj_import_browse_blend", text="Buscar .blend...", icon="FILEBROWSER")

        col.prop(oi, "edit_object_folder",  text="Carpeta")
        col.prop(oi, "edit_blend_filename", text="Archivo .blend")
        col.prop(oi, "edit_object_name",    text="Nombre objeto")

        row_preview = box_edit.row(align=True)
        row_preview.scale_y = 1.2
        row_preview.operator("alfst.obj_import_preview_now", text="Importar .blend al Outliner", icon="IMPORT")

        box_edit.separator()

        row_frames = box_edit.row(align=True)
        row_frames.prop(oi, "edit_frame_start", text="Inicio")
        row_frames.prop(oi, "edit_frame_end",   text="Fin")

        box_edit.separator()

        col_par = box_edit.column(align=True)
        col_par.label(text="Parenteo:", icon="BONE_DATA")
        row_arm = col_par.row(align=True)
        row_arm.prop(oi, "edit_parent_armature", text="Armature")
        row_arm.operator("alfst.obj_import_detect_armature", text="", icon="VIEWZOOM")
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
            row_btns.operator("alfst.obj_import_update_item", text="Actualizar", icon="CHECKMARK")
            row_btns.operator("alfst.obj_import_add_item",    text="+ Agregar nuevo", icon="ADD")
        else:
            row_btns.active_default = True
            row_btns.operator("alfst.obj_import_add_item", text="+ Agregar objeto", icon="CHECKMARK")

        layout.separator()
        layout.label(text="Los objetos se incluyen en el .py al EXPORTAR", icon="INFO")


# =============================================================================
# PANEL ÚNICO DE SECUENCIA DE OJOS
# =============================================================================

class ALFST_PT_EyeSequence(Panel):
    """
    Panel unico de ojos:
      · Setup de shape keys
      · Frame de inicio global de la secuencia de ojos
      · Posicion inicio / N cambios (con importar .json) / Posicion fin
      · Parpadeo automatico
      · CONCATENAR_2 — inserta keyframes definitivos desde el frame de inicio configurado
    """
    bl_label       = "2b  Secuencia de Ojos"
    bl_idname      = "ALFST_PT_eye_sequence"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Alfred Studio"
    bl_parent_id   = "ALFST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        # ANTES: este panel se ocultaba por completo en cuanto existia al
        # menos un segmento en el Paso 3 (return False). Como INICIO /
        # N CAMBIOS INTERMEDIOS / FIN (y CONCATENAR_2 / RESET) son un
        # sistema GLOBAL de una sola pasada sobre TODA la timeline (usa
        # scene.alfst.eye_start_*/eye_slots/eye_end_* directamente, sin
        # ningun concepto de "por segmento"), ocultar este panel era lo
        # unico que obligaba a duplicar ese mismo bloque, identico e
        # inline, dentro de CADA segmento del Paso 3 -- de ahi la
        # confusion de que "cada segmento" tuviera su propio Inicio/
        # Intermedio/Fin cuando en realidad todos compartian el mismo.
        # Ahora el panel se mantiene visible siempre; la configuracion
        # vive en UN solo lugar.
        return True

    def draw_header(self, context):
        self.layout.prop(context.scene.alfst.eye_expr, "enabled", text="")

    def draw(self, context):
        layout = self.layout
        st     = context.scene.alfst
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
        row_build.operator("alfst.build_eye_shape_keys", icon="FILE_REFRESH",
                            text="Crear / Recrear Shape Keys")

        box.separator(factor=0.3)

        row = box.row()
        row.template_list(
            "ALFST_UL_EyeSlots", "",
            st, "eye_slots",
            st, "eye_slot_idx",
            rows=4,
        )
        col = row.column(align=True)
        col.operator("alfst.add_eye_slot",       text="", icon="ADD")
        col.operator("alfst.remove_eye_slot",    text="", icon="REMOVE")
        col.operator("alfst.duplicate_eye_slot", text="", icon="COPYDOWN")
        col.separator()
        op = col.operator("alfst.move_eye_slot", text="", icon="TRIA_UP");   op.direction = "UP"
        op = col.operator("alfst.move_eye_slot", text="", icon="TRIA_DOWN"); op.direction = "DOWN"
        col.separator()
        col.operator("alfst.edit_eye_slot", text="", icon="GREASEPENCIL")

        row_add = box.row(align=True)
        row_add.scale_y = 1.4
        row_add.active_default = True
        row_add.operator("alfst.add_eye_slot",              text="  + Agregar",         icon="ADD")
        row_add.operator("alfst.duplicate_eye_slot",        text="  Copiar",            icon="COPYDOWN")
        row_add.operator("alfst.import_eye_slot_from_json", text="  Importar .json...", icon="FILE_FOLDER")

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
                row.operator("alfst.edit_eye_slot", icon="GREASEPENCIL", text="Editar...")
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
                "ALFST_UL_BlinkIntervals", "",
                st, "blink_intervals",
                st, "blink_interval_idx",
                rows=3,
            )
            col_lst = row_lst.column(align=True)
            col_lst.operator("alfst.blink_interval_add",       text="", icon="ADD")
            col_lst.operator("alfst.blink_interval_remove",    text="", icon="REMOVE")
            col_lst.operator("alfst.blink_interval_duplicate", text="", icon="COPYDOWN")
            col_lst.separator()
            op = col_lst.operator("alfst.blink_interval_move", text="", icon="TRIA_UP");  op.direction = "UP"
            op = col_lst.operator("alfst.blink_interval_move", text="", icon="TRIA_DOWN"); op.direction = "DOWN"

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

        # ════���═════════════════════════════════════════════════
        # E2) EXPRESIONES DE OJOS  (multi-intervalo)
        # ═══════════════════════════════════════����═════════════
        box_ei = layout.box()
        row_ei_hdr = box_ei.row(align=True)
        row_ei_hdr.prop(eye_s, "expr_intervals_enabled", text="",
                        icon="HIDE_OFF" if eye_s.expr_intervals_enabled else "HIDE_ON")
        row_ei_hdr.label(text="Expresiones de ojos — Lista de intervalos", icon="SHAPEKEY_DATA")

        # ── Setup de Shape Keys — FIX (Kebyn, 2026-08-04: "dentro de las
        # configuraciones de expresiones de ojos falta el sistema de
        # subdivisiones, Swap, etc"): estos controles (subdivide_cuts,
        # swap_axes, invert_vertical/horizontal, affect_zone, curve_mode)
        # y el boton "Crear/Recrear Shape Keys" ya existian, pero solo se
        # dibujaban dentro de la seccion C) "N Cambios de ojos", con
        # box.active = st.eye_changes_enabled -- es decir, se veian
        # deshabilitados o de plano invisibles si el usuario solo usaba
        # Expresiones de ojos (E2) sin activar Cambios intermedios (C).
        # Las propiedades (eye_s.subdivide_cuts, etc.) son las MISMAS que
        # usa build_expression_shape_keys() para las mallas de ojos --
        # afectan por igual a parpadeo, cambios intermedios Y expresiones.
        # Se duplica aqui el mismo bloque, siempre visible y habilitado en
        # esta seccion, para que el sistema de subdivisiones quede
        # accesible tambien desde "Expresiones de ojos".
        sub_sk_ei = box_ei.box()
        sub_sk_ei.label(text="Setup de Shape Keys de ojos", icon="MESH_PLANE")
        col_sk_ei = sub_sk_ei.column(align=True)
        col_sk_ei.prop(eye_s, "subdivide_cuts", text="Subdivisiones previas")
        row_sk_ei = col_sk_ei.row(align=True)
        row_sk_ei.prop(eye_s, "swap_axes",         toggle=True)
        row_sk_ei.prop(eye_s, "invert_vertical",   toggle=True, text="Inv V")
        row_sk_ei.prop(eye_s, "invert_horizontal", toggle=True, text="Inv H")
        col_sk_ei.prop(eye_s, "affect_zone", text="Zona")
        col_sk_ei.prop(eye_s, "curve_mode",  text="Curva")
        row_build_ei = sub_sk_ei.row()
        row_build_ei.scale_y = 1.3
        row_build_ei.operator("alfst.build_eye_shape_keys", icon="FILE_REFRESH",
                               text="Crear / Recrear Shape Keys")

        if eye_s.expr_intervals_enabled:
            # ── Lista de intervalos de expresion ─────────────────────────────
            row_ei = box_ei.row()
            row_ei.template_list(
                "ALFST_UL_EyeExprIntervals", "",
                st, "expr_intervals",
                st, "expr_interval_idx",
                rows=3,
            )
            col_ei = row_ei.column(align=True)
            col_ei.operator("alfst.expr_interval_add",       text="", icon="ADD")
            col_ei.operator("alfst.expr_interval_remove",    text="", icon="REMOVE")
            col_ei.operator("alfst.expr_interval_duplicate", text="", icon="COPYDOWN")
            col_ei.separator()
            op = col_ei.operator("alfst.expr_interval_move", text="", icon="TRIA_UP");  op.direction = "UP"
            op = col_ei.operator("alfst.expr_interval_move", text="", icon="TRIA_DOWN"); op.direction = "DOWN"
            col_ei.separator()
            col_ei.operator("alfst.edit_expr_interval", text="", icon="GREASEPENCIL")

            # ── Detalle del intervalo seleccionado ───────────────────────────
            if 0 <= st.expr_interval_idx < len(st.expr_intervals):
                ei = st.expr_intervals[st.expr_interval_idx]
                sub_ei = box_ei.box()
                row_ei_top = sub_ei.row(align=True)
                row_ei_top.prop(ei, "enabled", text="", icon="HIDE_OFF" if ei.enabled else "HIDE_ON")
                row_ei_top.prop(ei, "label", text="")

                col_ei2 = sub_ei.column(align=True)
                # Duracion del intervalo (encadenado tras el anterior)
                row_frames = col_ei2.row(align=True)
                row_frames.label(text="Frames:", icon="KEYFRAME")
                row_frames.prop(ei, "duration", text="")

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
                    text=f"  Dura {ei.duration} frames — se encadena tras el intervalo anterior",
                    icon="INFO",
                )
                row_edit_ei_g = sub_ei.row()
                row_edit_ei_g.operator("alfst.edit_expr_interval", icon="GREASEPENCIL",
                                        text="Editar posicion / rotacion / escala de cada ojo...")
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
            "alfst.concatenate_2",
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
            "alfst.reset_eye_sequence",
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
            "alfst.save_eye_config",
            text="  Exportar config ojos",
            icon="EXPORT",
        )
        row_cfg.operator(
            "alfst.load_eye_config",
            text="  Importar config ojos",
            icon="IMPORT",
        )



# =============================================================================
# PASO 2: RECORRIDO (Path Recorder)
# =============================================================================

from .woodcut_animation import is_woodcut

class ALFST_PT_PathRecorder(Panel):
    bl_label       = "0  Recorrido y Slots"
    bl_idname      = "ALFST_PT_path_recorder"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Alfred Studio"

    def draw(self, context):
        layout = self.layout
        pc = context.scene.alfred_path

        # ── PASO 1: Personaje y grabacion de recorrido ────────────────────────
        box_paso1 = layout.box()
        box_paso1.label(text="PASO 1 — Trazar recorrido", icon="CON_FOLLOWPATH")

        # Personaje .blend
        col_blend = box_paso1.column(align=True)
        col_blend.label(text="Personaje (.blend):", icon="ARMATURE_DATA")
        row_blend = col_blend.row(align=True)
        row_blend.prop(pc, "blend_filepath", text="")
        row_blend.operator("alfredpr.open_blend", text="", icon="FILEBROWSER")

        box_paso1.separator(factor=0.5)

        # Boton grabacion
        rec_text = "  Detener grabacion de recorrido" if pc.recording_active else "  Iniciar grabacion de recorrido"
        rec_icon = "REC" if pc.recording_active else "RADIOBUT_ON"
        row_rec = box_paso1.row()
        row_rec.scale_y = 1.3
        row_rec.operator("alfredpr.toggle_recording", text=rec_text, icon=rec_icon)

        # NUEVO (Kebyn, 2026-08-02): boton para ver el recorrido trazado
        # en el viewport (linea + numeros de orden) sin necesidad de estar
        # grabando -- antes, al presionar "Detener grabacion" el trazado
        # desaparecia por completo del viewport.
        viz_text = "  Ocultar recorrido" if pc.show_path_viz else "  Visualizar recorrido"
        viz_icon = "HIDE_OFF" if pc.show_path_viz else "HIDE_ON"
        row_viz = box_paso1.row()
        row_viz.operator("alfredpr.toggle_path_viz", text=viz_text, icon=viz_icon)
        row_viz.enabled = len(pc.path_points) > 0

        # Puntos grabados + botones quitar/limpiar
        row_pts = box_paso1.row(align=True)
        row_pts.label(text=f"Puntos registrados: {len(pc.path_points)}")
        row_remove = box_paso1.row(align=True)
        row_remove.operator("alfredpr.remove_last", text="Quitar ultimo", icon="REMOVE")
        row_remove.operator("alfredpr.clear_path",  text="Limpiar todo",  icon="X")

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
                info_row = box_lista.row()
                if n_marcadas == 0:
                    info_row.label(
                        text="Todos en 'Caminar': el recorrido sera solo caminata/saltos",
                        icon="INFO",
                    )
                else:
                    info_row.label(
                        text=f"{n_marcadas} punto(s) marcado(s) como 'Parada'",
                        icon="PAUSE",
                    )

                pts_list = list(pc.path_points)
                col_lista = box_lista.column(align=False)

                for i, pt in enumerate(pts_list):
                    row_pt = col_lista.row(align=True)

                    # Boton eliminar esta coordenada (Kebyn: "agrega un
                    # boton para eliminar la coordenada que no quiera
                    # utilizar"). Va primero en la fila para tener una
                    # posicion fija sin importar el tipo de punto (caminar/
                    # parada/subir/bajar/final), que cambian el resto del
                    # layout de la fila mas abajo.
                    op_del_pt = row_pt.operator(
                        "alfredpr.remove_point", text="", icon="X", emboss=False)
                    op_del_pt.index = i

                    # Numero de punto
                    row_pt.label(text=f"{i+1:>2}.", icon="LAYER_USED")

                    # Coordenadas redondeadas
                    x, y, z = round(pt.coords[0], 2), round(pt.coords[1], 2), round(pt.coords[2], 2)
                    row_pt.label(text=f"({x},  {y},  {z})")

                    # NUEVO (Kebyn): badge "punto de encuentro" -- se
                    # muestra en CUALQUIER punto cuya coordenada coincida
                    # con una del recorrido de Jerry, independientemente
                    # del tipo_segmento actual, para que el usuario vea
                    # donde puede activar 'Interactuar' (ver
                    # _point_is_meeting_point() en path_recorder.py).
                    from .path_recorder import _point_is_meeting_point
                    if _point_is_meeting_point(context, pt):
                        row_pt.label(text="", icon="LINKED")

                    # NUEVO (Kebyn, 2026-08-02): el dropdown Caminar/Parada
                    # SOLO se muestra editable en tramos donde la geometria
                    # real (diferencia de Z entre este punto y el siguiente)
                    # da "caminar". Las coordenadas de saltar_subir/
                    # saltar_bajar no se pueden alterar -- se muestran fijas,
                    # igual que antes, sin dropdown.
                    if i < len(pts_list) - 1:
                        # FIX (Kebyn, 2026-08-21 v2): se decide si mostrar el
                        # dropdown editable con _detect_move_geom() (SOLO
                        # geometria, ignora el override ya aplicado) en vez
                        # de _detect_move() -- asi "Colocar antorcha" queda
                        # seleccionable/editable de forma PERSISTENTE, igual
                        # que "Parada", en vez de desaparecer del panel apenas
                        # se elige (ver docstring de _detect_move_geom()).
                        from .path_recorder import _detect_move_geom
                        geom_move = _detect_move_geom(pt, pts_list[i + 1])
                        if geom_move == "caminar":
                            row_pt.prop(pt, "tipo_segmento", text="")
                            if pt.tipo_segmento == 'SALTAR':
                                col_lista.label(text=f"Salto: punto {i+1} a {i+2}", icon='IPO_QUAD')
                            if pt.tipo_segmento == "PARADA":
                                row_pt.prop(pt, "parada_frames_punto", text="Frames")
                                _draw_parada_anim_row(col_lista, pt, i)
                                _draw_parada_rot_row(col_lista, pt, i)
                            elif pt.tipo_segmento == "COLOCAR_ANTORCHA":
                                row_pt.label(text="", icon="OUTLINER_OB_LIGHT")
                            elif pt.tipo_segmento == "GOLPE_ESTOMAGO_1":
                                row_pt.label(text="", icon="ARMATURE_DATA")
                            elif pt.tipo_segmento == "COLOCAR_MESA_CRAFTEO":
                                row_pt.label(text="", icon="OUTLINER_OB_MESH")
                            elif pt.tipo_segmento == "LEVANTARSE_1":
                                row_pt.label(text="", icon="ARMATURE_DATA")
                            elif pt.tipo_segmento == "LEVANTARSE_2":
                                row_pt.label(text="", icon="ARMATURE_DATA")
                            elif pt.tipo_segmento == "ARRODILLARSE_1":
                                row_pt.label(text="", icon="ARMATURE_DATA")
                            elif pt.tipo_segmento == "CONVERSAR_1":
                                row_pt.label(text="", icon="ARMATURE_DATA")
                            elif pt.tipo_segmento == "RESBALARSE_1":
                                row_pt.label(text="", icon="MOD_PHYSICS")
                            elif pt.tipo_segmento == "CREAR_PARED_NXN":
                                row_pt.label(text="", icon="MESH_GRID")
                                _draw_pared_nxn_row(col_lista, pt, i)
                            elif pt.tipo_segmento == "INTERACTUAR":
                                _draw_interaccion_row(col_lista, pt, i)
                        elif geom_move == "saltar_subir":
                            row_pt.label(text="subir", icon="SORT_DESC")
                        else:  # saltar_bajar
                            row_pt.label(text="bajar", icon="SORT_ASC")
                    else:
                        # Ultimo punto: destino final, sin tramo de salto
                        # asociado -- se puede marcar como parada igual.
                        row_pt.prop(pt, "tipo_segmento", text="")
                        if pt.tipo_segmento == "PARADA":
                            row_pt.prop(pt, "parada_frames_punto", text="Frames")
                            _draw_parada_anim_row(col_lista, pt, i)
                            _draw_parada_rot_row(col_lista, pt, i)
                        elif pt.tipo_segmento == "INTERACTUAR":
                            _draw_interaccion_row(col_lista, pt, i)
                        elif pt.tipo_segmento == "CREAR_PARED_NXN":
                            # NUEVO (Kebyn, "crear pared no debe pedir punto
                            # siguiente"): a diferencia de "Colocar antorcha"/
                            # etc, esta SI se puede elegir en el ultimo punto
                            # -- no depende de un punto siguiente real, la
                            # pared se planta 1m adelante segun la orientacion
                            # actual del personaje (ver _group_segments_legacy(),
                            # caso final duplicado).
                            row_pt.label(text="", icon="MESH_GRID")
                            _draw_pared_nxn_row(col_lista, pt, i)
                        elif pt.tipo_segmento in _TIPOS_REQUIEREN_PUNTO_SIGUIENTE:
                            # FIX (Kebyn, "no me salen las opciones de la
                            # pared NxN en el ultimo punto"): estos tipos
                            # ("Colocar antorcha", "Colocar mesa de crafteo",
                            # "Golpe estomago", etc. -- "Crear pared NxN
                            # bloques" YA NO esta en esta lista, ver el elif
                            # de arriba) abarcan ESTE punto y el SIGUIENTE -- el
                            # personaje camina hasta el proximo punto y ahi
                            # hace la accion (ver _detect_move()/
                            # calcular_estimacion_geometrica() en
                            # path_recorder.py, que solo usa seg_pts[0] --
                            # nunca el ultimo punto -- para decidir el tipo
                            # de tramo). En el ULTIMO punto no hay "punto
                            # siguiente", asi que esta eleccion no tiene
                            # ningun efecto real al generar: antes se
                            # quedaba en silencio (sin campos, sin aviso),
                            # lo cual confundia. Ahora se avisa explicito en
                            # vez de fallar callado.
                            col_lista.label(
                                text="       Este tipo necesita un punto "
                                     "siguiente -- elegilo en un punto "
                                     "anterior al ultimo",
                                icon="ERROR")
                        row_pt.label(text="(final)", icon="KEYFRAME")

                    # Textura (compacta, solo nombre sin extension)
                    tex = pt.texture or ""
                    if tex:
                        short_tex = tex.replace("grass_block_top", "grass").replace(".png", "")
                        col_lista.label(text=f"       Textura: {short_tex}", icon="TEXTURE")

                    col_lista.separator(factor=0.3)

        # ── PASO 2: Configuracion de slots ───────────────────────────────────
        n_pts_reg = len(pc.path_points)
        _woodcut_single = n_pts_reg == 1 and is_woodcut(pc.path_points[0].tipo_segmento)
        is_idle      = (n_pts_reg == 1 and not _woodcut_single)
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

            # NUEVO (Kebyn, transiciones entre tramos): solo tiene sentido
            # ofrecer esto si el recorrido tiene AL MENOS dos tipos de
            # tramo distintos consecutivos -- con un recorrido 100%
            # "Caminar" no hay ningun corte que suavizar.
            from .path_recorder import _detect_move
            _tipos_tramos = []
            _pts_para_tipos = list(pc.path_points)
            for _i in range(len(_pts_para_tipos) - 1):
                _tipos_tramos.append(_detect_move(_pts_para_tipos[_i], _pts_para_tipos[_i + 1]))
            _hay_tramos_distintos = any(
                _tipos_tramos[_i] != _tipos_tramos[_i + 1]
                for _i in range(len(_tipos_tramos) - 1)
            )
            if _hay_tramos_distintos:
                box_trans = box_paso2.box()
                row_trans = box_trans.row()
                row_trans.prop(pc, "usar_transiciones", icon="IPO_EASE_IN_OUT")
                if pc.usar_transiciones:
                    row_trans.prop(pc, "frames_transicion", text="Frames")

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
        # scene.alfred_segs.segments (Paso 3 — ver la lista "Segmentos
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
        if len(pc.path_points) > 1 or _woodcut_single:
            pts = list(pc.path_points)
            expanded_pts, _, _, _ = _expand_points_with_paradas(pts)
            segs_chk = _group_segments(expanded_pts)
            n_paradas_actual = sum(1 for s in segs_chk if s["type"] == "parada")
            if len(pc.paradas_frames) != n_paradas_actual:
                row_sync = box_paso2.row()
                row_sync.alert = True
                row_sync.operator(
                    "alfredpr.sync_paradas_frames",
                    text=f"Sincronizar frames por parada ({n_paradas_actual} detectada(s))",
                    icon="FILE_REFRESH",
                )

        _slots_est, _fuente_est = calcular_estimacion_slots(context.scene)
        if _fuente_est == "paso3_segmentos":
            box_est = box_paso2.box()
            row_est_head = box_est.row(align=True)
            row_est_head.label(text="Estimacion de segmentos:", icon="INFO")
            row_est_head.operator(
                "alfredseg.update_from_estimacion",
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
                elif _s["tipo"] in ("saltar_subir", "saltar_bajar", "saltar_horizontal"):
                    row_seg.label(text=f"  Segmento {_s['slot']}: {_s['label']} ({_s['frames_estimados']} f)")
                elif is_woodcut(_s["tipo"]):
                    row_seg.label(text=f"  Segmento {_s['slot']}: {_s['tipo'].replace('_', ' ')} ({_s['frames_estimados']} f)", icon="MOD_BUILD")
                elif _s["tipo"] == "colocar_antorcha":
                    row_seg.label(
                        text=f"  Segmento {_s['slot']}: colocar antorcha ({_s['frames_estimados']} f)",
                        icon="OUTLINER_OB_LIGHT",
                    )
                elif _s["tipo"] == "colocar_mesa_de_crafteo":
                    row_seg.label(
                        text=f"  Segmento {_s['slot']}: colocar mesa de crafteo ({_s['frames_estimados']} f)",
                        icon="OUTLINER_OB_MESH",
                    )
                elif _s["tipo"] == "crear_pared_nxn":
                    # Misma arquitectura que "colocar_mesa_de_crafteo" de
                    # arriba -- rama propia para que no caiga en el 'else'
                    # final (ver comentario del bug de "golpe_estomago_1"
                    # mas abajo, mismo mecanismo). "frames_estimados" aca
                    # ya depende de filas*columnas (ver
                    # calcular_estimacion_geometrica(), path_recorder.py).
                    row_seg.label(
                        text=(f"  Segmento {_s['slot']}: crear pared "
                              f"{_s.get('pared_filas', '?')}x{_s.get('pared_columnas', '?')} "
                              f"({_s['frames_estimados']} f)"),
                        icon="MESH_GRID",
                    )
                elif _s["tipo"] == "golpe_estomago_1":
                    # FIX (Kebyn, "el golpe estomago aparece como parada en
                    # la lista de segmentos"): a este if/elif le faltaba la
                    # rama para "golpe_estomago_1" -- caminar/saltar_subir/
                    # saltar_bajar/colocar_antorcha/colocar_mesa_de_crafteo
                    # ya tenian la suya, pero golpe_estomago_1 caia directo
                    # al 'else' de mas abajo (pensado solo para "parada"),
                    # que no distingue tipo -- por eso se veia listado como
                    # "parada (~100 f)" en vez de como su propio segmento.
                    # calcular_estimacion_geometrica() en path_recorder.py
                    # SI devolvia el "tipo"/"frames_estimados" correctos
                    # (ver su rama "elif seg_type == 'golpe_estomago_1':")
                    # -- el bug era puramente de dibujado aca. Mismo icono
                    # que ya usa el dropdown del Paso 1 para este tipo (ver
                    # mas arriba, ALFREDPathPoint.tipo_segmento ==
                    # "GOLPE_ESTOMAGO_1").
                    row_seg.label(
                        text=f"  Segmento {_s['slot']}: golpe estomago ({_s['frames_estimados']} f)",
                        icon="ARMATURE_DATA",
                    )
                elif _s["tipo"] == "levantarse_1":
                    # Misma arquitectura que "golpe_estomago_1" de arriba
                    # -- rama propia para que no caiga en el 'else' final
                    # (ver comentario del bug arriba, mismo mecanismo).
                    row_seg.label(
                        text=f"  Segmento {_s['slot']}: levantarse ({_s['frames_estimados']} f)",
                        icon="ARMATURE_DATA",
                    )
                elif _s["tipo"] == "levantarse_2":
                    # Segunda variante de "levantarse_1" de arriba, misma
                    # arquitectura -- rama propia por el mismo motivo
                    # (ver comentario del bug de golpe_estomago_1 arriba).
                    row_seg.label(
                        text=f"  Segmento {_s['slot']}: levantarse variante 2 ({_s['frames_estimados']} f)",
                        icon="ARMATURE_DATA",
                    )
                elif _s["tipo"] == "arrodillarse_1":
                    # Misma arquitectura que "levantarse_1"/"levantarse_2"
                    # de arriba -- rama propia por el mismo motivo (ver
                    # comentario del bug de golpe_estomago_1 arriba).
                    row_seg.label(
                        text=f"  Segmento {_s['slot']}: arrodillarse ({_s['frames_estimados']} f)",
                        icon="ARMATURE_DATA",
                    )
                elif _s["tipo"] == "resbalarse_1":
                    # Misma arquitectura que "arrodillarse_1"/"levantarse_1"/
                    # "levantarse_2" de arriba -- rama propia por el mismo
                    # motivo (ver comentario del bug de golpe_estomago_1
                    # arriba).
                    row_seg.label(
                        text=f"  Segmento {_s['slot']}: resbalarse ({_s['frames_estimados']} f)",
                        icon="MOD_PHYSICS",
                    )
                elif _s["label"] == "parada (sin sincronizar)":
                    row_seg.label(text=f"  Segmento {_s['slot']}: parada ({_s['frames_estimados']} f, sin sincronizar)")
                else:  # parada, sincronizada
                    row_seg.label(text=f"  Segmento {_s['slot']}: parada (~{_s['frames_estimados']} f)")
            if len(pc.path_points) > 1 or _woodcut_single:
                _n_caminar_real = sum(1 for _s in _slots_est if _s["tipo"] == "caminar")
                if len(pc.walk_styles) != _n_caminar_real:
                    row_sync_ws = box_est.row()
                    row_sync_ws.alert = True
                    row_sync_ws.operator(
                        "alfredpr.sync_paradas_frames",
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
        row_play.operator("alfredpr.preview_path", text="  Reproducir recorrido", icon="PLAY")

        box_exp = layout.box()
        box_exp.label(text="Exportar slots (opcional):", icon="EXPORT")
        box_exp.label(text="  Solo animacion base sin poses avanzadas", icon="INFO")
        row_exp = box_exp.row()
        row_exp.scale_y = 1.3
        row_exp.operator("alfredpr.export_slots", text="  Exportar recorrido", icon="EXPORT")

        layout.separator(factor=0.3)
        layout.label(text="  ¿Poses avanzadas? → Configura el PASO 3 abajo", icon="QUESTION")
        row_reset = layout.row()
        row_reset.operator("alfredpr.reset_preview", text="  Reset recorrido", icon="LOOP_BACK")

        if pc.anim_frame_fin > 0:
            layout.label(text=f"Rango fijado: {pc.frame_inicio}→{pc.anim_frame_fin}", icon="PINNED")



# =============================================================================
# PASO 3: SEGMENTOS (Refinado de poses sobre el recorrido)
# =============================================================================

class ALFREDSEG_UL_SegmentsList(UIList):
    bl_idname = "ALFREDSEG_UL_SegmentsList"

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


def _draw_bone_block_row(layout, seg, seg_idx, filter_attr):
    """
    Dibuja la fila de bloqueo de UN bone dentro del Bloqueador de bones:
      - Checkbox de bloqueo total (bloquea el bone en todo el segmento).
      - Boton [+] para agregar un intervalo de frames de bloqueo especifico.
      - Lista de los intervalos ya creados para ese bone (Inicio / Fin / activo / eliminar).
    Un mismo bone puede tener varios intervalos independientes
    (ej: bloqueado 60→100, luego otra vez 500→630).
    """
    row = layout.row(align=True)
    row.prop(seg, filter_attr, icon="BONE_DATA")
    op_add = row.operator("alfredseg.add_bone_interval", text="", icon="ADD")
    op_add.item_idx = seg_idx
    op_add.bone_key = filter_attr

    entry = None
    for e in seg.bone_blocks:
        if e.bone_key == filter_attr:
            entry = e
            break

    if entry is not None and len(entry.intervals):
        box_iv = layout.box()
        for iv_idx, iv in enumerate(entry.intervals):
            row_iv = box_iv.row(align=True)
            row_iv.prop(iv, "enabled", text="")
            row_iv.prop(iv, "frame_start", text="Ini")
            row_iv.prop(iv, "frame_end",   text="Fin")
            op_rm = row_iv.operator("alfredseg.remove_bone_interval", text="", icon="X")
            op_rm.item_idx     = seg_idx
            op_rm.bone_key     = filter_attr
            op_rm.interval_idx = iv_idx


class ALFST_PT_Segments(Panel):
    bl_label       = "3  Segmentos (Poses sobre recorrido)"
    bl_idname      = "ALFST_PT_segments"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Alfred Studio"
    bl_options     = {"DEFAULT_CLOSED"}
    bl_order       = 0

    def draw(self, context):
        layout    = self.layout
        segs_data = context.scene.alfred_segs
        pc        = context.scene.alfred_path
        st        = context.scene.alfst

        n_pts = len(pc.path_points)
        _modo_1coord = (n_pts <= 1 and not (n_pts == 1 and is_woodcut(pc.path_points[0].tipo_segmento)))

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
                text="(N poses de accion)",
                icon="INFO"
            )

            box3.separator(factor=0.3)
            box3.prop(segs_data, "edit_label", text="Nombre")

            layout.separator(factor=0.5)
            row_crear = layout.row()
            row_crear.scale_y = 2.2
            row_crear.alert   = True
            row_crear.operator("alfredseg.add", text="+ CREAR SEGMENTO", icon="ADD")

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
                "alfredseg.autosplit_from_config",
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
            row_crear.operator("alfredseg.add", text="+ CREAR SEGMENTO", icon="ADD")
            if not _puede_crear and _total_est > 0:
                layout.label(text="  Corrige los frames antes de crear", icon="ERROR")

        # ── Concatenar segmentos: ejecuta CONCATENAR de CADA segmento activo,
        #    respetando el rango de frames propio de cada uno, y reproduce
        #    todas las secuencias encadenadas de principio a fin ───────────
        layout.separator(factor=0.5)
        _n_enabled = sum(1 for s in segs_data.segments if s.enabled)
        row_concat = layout.row()
        row_concat.scale_y = 1.8
        row_concat.enabled = _n_enabled > 0
        row_concat.operator(
            "alfredseg.concatenate_all",
            text=f"▶ Concatenar segmentos ({_n_enabled})",
            icon="SEQUENCE",
        )
        if _n_enabled == 0:
            layout.label(text="  Activa al menos un segmento para concatenar", icon="INFO")

        # ── Sistema global de objetos ────────────────────────────────────────
        # Se administra al mismo nivel que los segmentos. Cada item conserva
        # su segment_idx y la ejecución sigue usando la configuración de ese
        # segmento, sin duplicar este panel dentro de cada tarjeta.
        box_global_throw = layout.box()
        box_global_throw.label(text="Lanzar / Recoger / Mantener Objetos", icon="FORCE_WIND")
        if segs_data.segments:
            # El sistema es independiente de la cantidad de segmentos creados:
            # no se le pide al usuario elegir un segmento. Internamente sigue
            # usando el primer segmento como contenedor de almacenamiento,
            # pero eso ya no se expone en la interfaz.
            _global_seg_idx = 0
            _global_seg = segs_data.segments[_global_seg_idx]
            _global_th = _global_seg.throws
            # Siempre activo: si se está configurando un lanzamiento/recogida/
            # mantenimiento es porque se quiere que se ejecute, así que no se
            # expone un checkbox para desactivarlo.
            # FIX (Kebyn): esto NO puede escribirse aca -- draw() es de solo
            # lectura en Blender 4.5 y mutar un PropertyGroup de la Scene
            # durante el dibujado tira "Writing to ID classes in this
            # context is not allowed". th.enabled ahora se garantiza True
            # en el momento en que se crea el item (ALFST_OT_ThrowAddItem
            # y los auto-registros de colocar_antorcha/mesa_de_crafteo en
            # operators_segments.py), que es el lugar correcto para
            # mutar estado.
            row_global_hdr = box_global_throw.row(align=True)
            row_global_hdr.label(text=f"{len(_global_th.items)} objeto(s)")
            for _gti, _gtitem in enumerate(_global_th.items):
                _grow = box_global_throw.row(align=True)
                _grow.prop(_gtitem, "enabled", text="")
                _grow.label(text=f"{_gtitem.label} [{_gtitem.mode}] — {_gtitem.object_name}", icon="FORCE_WIND")
                _ged = _grow.operator("alfst.throw_load_to_editor", text="", icon="GREASEPENCIL")
                _ged.seg_idx = _global_seg_idx; _ged.item_idx = _gti
                _grm = _grow.operator("alfst.throw_remove_item", text="", icon="X")
                _grm.seg_idx = _global_seg_idx; _grm.item_idx = _gti
            box_global_throw.label(text="Nuevo lanzamiento / editar", icon="ADD")
            row_global_mode = box_global_throw.row(align=True)
            row_global_mode.prop(_global_th, "edit_mode", expand=True)
            box_global_throw.prop(_global_th, "edit_label", text="Etiqueta")
            row_global_br = box_global_throw.row(align=True)
            row_global_br.scale_y = 1.2
            _op_global_br = row_global_br.operator(
                "alfst.throw_browse_blend", text="Buscar .blend...", icon="FILEBROWSER")
            _op_global_br.seg_idx = _global_seg_idx
            col_global_obj = box_global_throw.column(align=True)
            col_global_obj.prop(_global_th, "edit_object_name", text="Nombre objeto")
            col_global_obj.prop(_global_th, "edit_object_folder", text="Carpeta")
            col_global_obj.prop(_global_th, "edit_blend_filename", text="Archivo .blend")
            row_global_frames = box_global_throw.row(align=True)
            row_global_frames.prop(_global_th, "edit_frame_start", text="Inicio")
            row_global_frames.prop(_global_th, "edit_frame_end", text="Fin")

            # ── Gesto de brazo "hacia la espalda" (reach-back) ────────────
            # Duracion configurable del gesto: es la MITAD del recorrido --
            # cuantos frames tarda el brazo en ir desde Inicio hasta la pose
            # "hacia la espalda" (ahi mismo aparece el objeto, no al volver
            # a la normalidad). Opcion de repetir el mismo gesto en espejo
            # antes de Fin (para simular que el personaje "guarda" el objeto).
            box_global_reach = box_global_throw.box()
            box_global_reach.label(text="Gesto de brazo (hacia la espalda):", icon="ARMATURE_DATA")
            box_global_reach.prop(
                _global_th, "edit_reach_back_duration_in",
                text="Frames hasta la pose (objeto aparece ahí)")
            box_global_reach.prop(
                _global_th, "edit_reach_back_enabled_out",
                text="Repetir en espejo antes de Fin (guardar)")
            if _global_th.edit_reach_back_enabled_out:
                box_global_reach.prop(
                    _global_th, "edit_reach_back_duration_out",
                    text="Frames antes de Fin (objeto desaparece ahí)")

            row_global_parent = box_global_throw.row(align=True)
            row_global_parent.prop(_global_th, "edit_parent_armature", text="Armature")
            _arm_obj_gth = bpy.data.objects.get(_global_th.edit_parent_armature)
            if _arm_obj_gth is None or _arm_obj_gth.type != 'ARMATURE':
                _arm_obj_gth = _find_alfred_armature(context)
            if _arm_obj_gth is not None and _arm_obj_gth.type == 'ARMATURE':
                row_global_parent.prop_search(
                    _global_th, "edit_parent_bone",
                    _arm_obj_gth.pose, "bones", text="Bone")
            else:
                row_global_parent.prop(_global_th, "edit_parent_bone", text="Bone")
            # ── Importar objeto (preview en vivo) + Guardar configuracion ──
            # "Importar objeto" trae el .blend a la escena y lo aparenta al
            # bone elegido arriba; mientras el objeto siga en preview
            # (_global_th.edit_imported_object_name), los campos de
            # Posicion/Rotacion/Escala de abajo actualizan su transform en
            # tiempo real (ver _th_editor_update en properties.py), para
            # poder ver el resultado ANTES de concatenar los segmentos.
            # "Guardar configuracion" persiste esos valores en un item para
            # que el CONCATENAR importe el objeto ya con esa configuracion.
            row_global_import = box_global_throw.row(align=True)
            row_global_import.scale_y = 1.2
            _op_global_import = row_global_import.operator(
                "alfst.throw_import_object", text="Importar objeto", icon="IMPORT")
            _op_global_import.seg_idx  = _global_seg_idx
            _op_global_import.item_idx = -1

            if _global_th.edit_imported_object_name:
                box_global_xform = box_global_throw.box()
                row_global_xform_hdr = box_global_xform.row(align=True)
                row_global_xform_hdr.label(
                    text=f"Editando en vivo: '{_global_th.edit_imported_object_name}'",
                    icon="OBJECT_ORIGIN")
                _op_global_sync = row_global_xform_hdr.operator(
                    "alfst.throw_sync_from_object", text="", icon="FILE_REFRESH")
                _op_global_sync.seg_idx = _global_seg_idx
                box_global_xform.label(
                    text="Si moviste/rotaste el objeto a mano en el viewport, tocá el ícono de arriba para sincronizar",
                    icon="INFO")
                row_global_loc = box_global_xform.row(align=True)
                row_global_loc.prop(_global_th, "edit_loc_x", text="X")
                row_global_loc.prop(_global_th, "edit_loc_y", text="Y")
                row_global_loc.prop(_global_th, "edit_loc_z", text="Z")
                row_global_rot = box_global_xform.row(align=True)
                row_global_rot.prop(_global_th, "edit_rot_x", text="X")
                row_global_rot.prop(_global_th, "edit_rot_y", text="Y")
                row_global_rot.prop(_global_th, "edit_rot_z", text="Z")
                box_global_xform.prop(_global_th, "edit_scale_uniform", text="Escala")

            row_global_buttons = box_global_throw.row(align=True)
            row_global_buttons.scale_y = 1.2
            row_global_add = row_global_buttons.operator(
                "alfst.throw_add_item", text="Guardar configuracion", icon="FILE_TICK")
            row_global_add.seg_idx = _global_seg_idx
            box_global_throw.label(text="No importa cuántos segmentos se hayan creado.", icon="INFO")
        else:
            box_global_throw.label(text="Crea un segmento para configurar objetos.", icon="INFO")

        # ── Sistema global de Invisibilidad de Malla ──────────────────────────
        # Debajo del sistema de Lanzar / Recoger / Mantener Objetos (mismo
        # criterio de la seccion de arriba): se administra al mismo nivel
        # que los segmentos, sin duplicar el panel dentro de cada tarjeta, y
        # usa el primer segmento como contenedor de almacenamiento.
        box_global_hide = layout.box()
        box_global_hide.label(text="Invisibilidad de Malla", icon="HIDE_ON")
        if segs_data.segments:
            _global_seg_idx_h = 0
            _global_seg_h = segs_data.segments[_global_seg_idx_h]
            _global_hm = _global_seg_h.hide_mesh
            row_global_hide_hdr = box_global_hide.row(align=True)
            row_global_hide_hdr.label(text=f"{len(_global_hm.items)} intervalo(s)")
            for _ghi, _ghitem in enumerate(_global_hm.items):
                _ghrow = box_global_hide.row(align=True)
                _ghrow.prop(_ghitem, "enabled", text="")
                _ghrow.label(
                    text=f"{_ghitem.label} — {_ghitem.mesh_object} "
                         f"[{_ghitem.frame_start}→{_ghitem.frame_end}]",
                    icon="MESH_DATA")
                _ghed = _ghrow.operator("alfst.hide_mesh_load_to_editor", text="", icon="GREASEPENCIL")
                _ghed.seg_idx = _global_seg_idx_h; _ghed.item_idx = _ghi
                _ghrm = _ghrow.operator("alfst.hide_mesh_remove_item", text="", icon="X")
                _ghrm.seg_idx = _global_seg_idx_h; _ghrm.item_idx = _ghi
            box_global_hide.label(text="Nuevo intervalo / editar", icon="ADD")
            box_global_hide.prop(_global_hm, "edit_label", text="Etiqueta")
            row_global_hide_obj = box_global_hide.row(align=True)
            row_global_hide_obj.prop_search(
                _global_hm, "edit_mesh_object",
                bpy.data, "objects", text="Malla")
            _op_global_pick = row_global_hide_obj.operator(
                "alfst.hide_mesh_pick_object", text="", icon="EYEDROPPER")
            _op_global_pick.seg_idx = _global_seg_idx_h
            row_global_hide_frames = box_global_hide.row(align=True)
            row_global_hide_frames.prop(_global_hm, "edit_frame_start", text="Inicio")
            row_global_hide_frames.prop(_global_hm, "edit_frame_end", text="Fin")

            row_global_hide_buttons = box_global_hide.row(align=True)
            row_global_hide_buttons.scale_y = 1.2
            row_global_hide_add = row_global_hide_buttons.operator(
                "alfst.hide_mesh_add_item", text="Guardar configuracion", icon="FILE_TICK")
            row_global_hide_add.seg_idx = _global_seg_idx_h
            box_global_hide.label(text="No importa cuántos segmentos se hayan creado.", icon="INFO")
        else:
            box_global_hide.label(text="Crea un segmento para configurar invisibilidad.", icon="INFO")

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
                op_en = row_seg_hdr.operator("alfredseg.toggle_enabled", text="", icon=icon_en, emboss=False)
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
                op_cfg = row_seg_hdr.operator("alfredseg.toggle_config", text="", icon=_cfg_icon, emboss=False)
                op_cfg.item_idx = i

                # ── Boton propio de este segmento: "Reproducir recorrido" ─────
                # Genera el recorrido completo (Capa 1 + Capa 2 reinyectada) y
                # acota la reproduccion SOLO a los frames de este segmento.
                row_play_seg = box_seg.row(align=True)
                row_play_seg.scale_y = 1.5
                op_play_seg = row_play_seg.operator(
                    "alfredseg.play_segment_recorrido",
                    text="  Reproducir recorrido", icon="PLAY"
                )
                op_play_seg.item_idx = i

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
                op_dup = row_play.operator("alfredseg.duplicate", text="", icon="DUPLICATE")
                op_dup.item_idx = i
                op_del = row_play.operator("alfredseg.remove",    text="", icon="X")
                op_del.item_idx = i

                # ── Barra de duracion calculada en tiempo real ────────────────
                _fps = context.scene.render.fps
                _dur_s = round(_seg_total_fr / _fps, 2) if _fps > 0 else 0
                _n_slots = len(seg.action_poses)
                _poses_dur = sum(ap.duration for ap in seg.action_poses)
                _dur_row = box_seg.row()
                _dur_row.enabled = False
                # FIX (Kebyn, 2026-08-04): antes decia "... = {total}f", dando
                # a entender que el total del segmento ES la suma de sus
                # poses. Desde que el rango del segmento queda fijo por el
                # Paso 2/3 (ver _calc_seg_frames, operators_segments.py), las
                # poses solo ocupan una parte de esos frames -- se muestra
                # "de {total}f disponibles" para reflejar eso, salvo en modo
                # 1 coordenada donde el total SI sigue siendo la suma de poses.
                _fixed_range = (not seg.single_coord_mode) and seg.frame_end_planned > seg.frame_start_planned
                _conector = "de" if _fixed_range else "="
                _sufijo   = "disponibles" if _fixed_range else ""
                _dur_parts = (
                    f"{_n_slots} pose{'s' if _n_slots != 1 else ''} ({_poses_dur}f)"
                    + f"  {_conector}  {_seg_total_fr}f {_sufijo}  ({_dur_s}s)"
                )
                _dur_row.label(text=_dur_parts, icon="TIME")
                if _fixed_range and _poses_dur > _seg_total_fr:
                    _warn_row = box_seg.row()
                    _warn_row.alert = True
                    _warn_row.label(
                        text=(f"  Las poses ocupan {_poses_dur}f pero el segmento "
                              f"solo tiene {_seg_total_fr}f -- se van a solapar/cortar"),
                        icon="ERROR")

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
                    row_arm.operator("alfst.set_armature", text="", icon="EYEDROPPER")

                    box_dirs = box_cfg.box()
                    box_dirs.label(text="Carpetas", icon="FILE_FOLDER")
                    col_dirs = box_dirs.column(align=True)
                    col_dirs.prop(st, "poses_dir",  text="Poses")
                    col_dirs.prop(st, "anim_dir",   text="Animaciones")
                    col_dirs.prop(st, "config_dir", text="Configuraciones")
                    row_dirs = box_dirs.row(align=True)
                    row_dirs.operator("alfst.open_poses_folder", text="Poses", icon="FILE_FOLDER")
                    row_dirs.operator("alfst.open_anim_folder",  text="Anims", icon="FILE_FOLDER")
                    row_dirs.operator("alfst.refresh_poses",     text="",      icon="FILE_REFRESH")
                    box_cfg.operator("alfst.reset", text="Reset todo", icon="LOOP_BACK")

                    # ── Bloqueador de bones ───────────────────────────────────────────────
                    box_filt = box_cfg.box()
                    row_filt_hdr = box_filt.row(align=True)
                    row_filt_hdr.label(text="  Bloqueador de bones", icon="BONE_DATA")

                    box_filt.label(
                        text="Bones marcados NO reciben poses del segmento:",
                        icon="INFO"
                    )
                    # ── Armature root ──────────────────────────────────────
                    col_flt = box_filt.column(align=True)
                    col_flt.label(text="Root / Armature:")
                    _draw_bone_block_row(col_flt, seg, i, "filter_main_bone")

                    # ── Caderas / columna ──────────────────────────────────
                    col_flt.separator()
                    col_flt.label(text="Caderas / columna:")
                    _draw_bone_block_row(col_flt, seg, i, "filter_hips")
                    _draw_bone_block_row(col_flt, seg, i, "filter_spine")
                    _draw_bone_block_row(col_flt, seg, i, "filter_spine1")
                    _draw_bone_block_row(col_flt, seg, i, "filter_spine2")

                    # ── Cabeza / cuello ────────────────────────────────────
                    col_flt.separator()
                    col_flt.label(text="Cabeza / cuello:")
                    _draw_bone_block_row(col_flt, seg, i, "filter_neck")
                    _draw_bone_block_row(col_flt, seg, i, "filter_face")

                    # ── Brazos ─────────────────────────────────────────────
                    col_flt.separator()
                    col_flt.label(text="Brazos:")
                    _draw_bone_block_row(col_flt, seg, i, "filter_right_arm")
                    _draw_bone_block_row(col_flt, seg, i, "filter_right_elbow")
                    _draw_bone_block_row(col_flt, seg, i, "filter_left_arm")
                    _draw_bone_block_row(col_flt, seg, i, "filter_left_elbow")

                    # ── Piernas ────────────────────────────────────────────
                    col_flt.separator()
                    col_flt.label(text="Piernas:")
                    _draw_bone_block_row(col_flt, seg, i, "filter_right_leg")
                    _draw_bone_block_row(col_flt, seg, i, "filter_right_knee")
                    _draw_bone_block_row(col_flt, seg, i, "filter_left_leg")
                    _draw_bone_block_row(col_flt, seg, i, "filter_left_knee")

                    # ── Accesorios / no_bone ───────────────────────────────
                    col_flt.separator()
                    col_flt.label(text="Accesorios (no_bone):")
                    _draw_bone_block_row(col_flt, seg, i, "filter_no_bone_01")
                    _draw_bone_block_row(col_flt, seg, i, "filter_no_bone_02")
                    _draw_bone_block_row(col_flt, seg, i, "filter_no_bone_03")
                    _draw_bone_block_row(col_flt, seg, i, "filter_no_bone_04")
                    _draw_bone_block_row(col_flt, seg, i, "filter_no_bone_05")
                    _draw_bone_block_row(col_flt, seg, i, "filter_no_bone_06")
                    _draw_bone_block_row(col_flt, seg, i, "filter_no_bone_07")
                    _draw_bone_block_row(col_flt, seg, i, "filter_no_bone_08")

                    # ── Resumen de bones bloqueados activos ────────────────
                    _filtrados = [
                        n for attr, n in [
                            ("filter_main_bone", "Armature"),
                            ("filter_hips",      "Hips_alfred"),
                            ("filter_spine",     "Spine_alfred"),
                            ("filter_spine1",    "Spine1_alfred"),
                            ("filter_spine2",    "Spine2_alfred"),
                            ("filter_neck",      "Neck_alfred"),
                            ("filter_face",      "face_alfred"),
                            ("filter_right_arm",   "RightUpArm_alfred"),
                            ("filter_right_elbow", "Rightelbow_alfred"),
                            ("filter_left_arm",    "LeftUpArm_alfred"),
                            ("filter_left_elbow",  "Leftelbow_alfred"),
                            ("filter_right_leg",   "RightUpLeg_alfred"),
                            ("filter_right_knee",  "Rightknee_alfred"),
                            ("filter_left_leg",    "LeftUpLeg_alfred"),
                            ("filter_left_knee",   "Leftknee_alfred"),
                            ("filter_no_bone_01",  "no_bone_01"),
                            ("filter_no_bone_02",  "no_bone_02"),
                            ("filter_no_bone_03",  "no_bone_03"),
                            ("filter_no_bone_04",  "no_bone_04"),
                            ("filter_no_bone_05",  "no_bone_05"),
                            ("filter_no_bone_06",  "no_bone_06"),
                            ("filter_no_bone_07",  "no_bone_07"),
                            ("filter_no_bone_08",  "no_bone_08"),
                        ]
                        if getattr(seg, attr, False)
                    ]
                    if _filtrados:
                        box_filt.separator(factor=0.3)
                        box_filt.label(
                            text="Bloqueados: " + ", ".join(_filtrados),
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
                        "ALFST_UL_ActionPoses", f"seg_{i}",
                        seg, "action_poses",
                        seg, "action_poses_idx",
                        rows=4,
                    )
                    col_ac = row_ac.column(align=True)
                    op_add_ac = col_ac.operator("alfredseg.add_action_pose_seg",    text="", icon="ADD")
                    op_add_ac.item_idx = i
                    op_rem_ac = col_ac.operator("alfredseg.remove_action_pose_seg", text="", icon="REMOVE")
                    op_rem_ac.item_idx = i
                    col_ac.separator()
                    op_up_ac = col_ac.operator("alfredseg.move_action_pose_seg", text="", icon="TRIA_UP")
                    op_up_ac.item_idx = i; op_up_ac.direction = "UP"
                    op_dn_ac = col_ac.operator("alfredseg.move_action_pose_seg", text="", icon="TRIA_DOWN")
                    op_dn_ac.item_idx = i; op_dn_ac.direction = "DOWN"
                    col_ac.separator()
                    op_ed_ac = col_ac.operator("alfredseg.edit_action_pose_seg", text="", icon="GREASEPENCIL")
                    op_ed_ac.item_idx = i
                    op_cp_ac = col_ac.operator("alfredseg.duplicate_action_pose_seg", text="", icon="DUPLICATE")
                    op_cp_ac.item_idx = i

                    row_add_ac = box_ac.row()
                    row_add_ac.scale_y = 1.4
                    row_add_ac.active_default = True
                    op_add_ac2 = row_add_ac.operator(
                        "alfredseg.add_action_pose_seg",
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

                    # ── EXTRAER POSE RAPIDA (bones del armature Alfred) ────────────────
                    # Debajo del sistema de agregar poses (mismo criterio que "4 Extraer
                    # Nueva Pose" del Paso 1, pero automatico: detecta el armature/bones
                    # de Alfred solo, nombra la pose segun los huesos que se movieron, y
                    # con "Importar" la agrega directo a esta lista).
                    box_qp = box_ac.box()
                    row_qp_hdr = box_qp.row(align=True)
                    row_qp_hdr.label(text="Extraer pose rapida (bones actuales)", icon="BONE_DATA")
                    row_qp_btn = box_qp.row(align=True)
                    row_qp_btn.scale_y = 1.3
                    row_qp_btn.operator(
                        "alfredseg.quickpose_extract",
                        text="  Guardar pose (bones actuales)", icon="PINNED"
                    )
                    _st_qp = context.scene.alfst
                    row_qp_imp = box_qp.row(align=True)
                    row_qp_imp.scale_y = 1.3
                    op_qp_imp = row_qp_imp.operator(
                        "alfredseg.quickpose_import",
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

                    if seg.action_poses:
                        # ── SEMÁFORO: indica qué pose se reproduce en el frame actual ──
                        # Blender redibuja el panel en cada frame durante la reproducción,
                        # así que simplemente leemos context.scene.frame_current aquí.
                        try:
                            _cur_frame = context.scene.frame_current
                            _poses_ac  = seg.action_poses

                            # Encontrar qué pose corresponde al frame actual
                            _active_semaforo = -1
                            for _si, _sp in enumerate(_poses_ac):
                                _fs = getattr(_sp, "frame_abs_start", 0)
                                _fe = _fs + _sp.duration
                                if _fs > 0 and _fs <= _cur_frame < _fe:
                                    _active_semaforo = _si
                                    break

                            if _active_semaforo >= 0:
                                # Semáforo activo: mostrar franja con la pose actual
                                box_sem = box_ac.box()
                                col_sem = box_sem.column(align=True)
                                _sp_act = _poses_ac[_active_semaforo]
                                _fs_act = getattr(_sp_act, "frame_abs_start", 0)
                                _fe_act = _fs_act + _sp_act.duration
                                _prog   = (_cur_frame - _fs_act) / max(_sp_act.duration, 1)
                                _pct    = int(_prog * 100)

                                # Fila superior: indicador + nombre pose + frame actual
                                row_sem_top = col_sem.row(align=True)
                                row_sem_top.label(text="", icon="RADIOBUT_ON")
                                _nombre_sem = _sp_act.pose_name or _sp_act.json_file or "---"
                                if len(_nombre_sem) > 38:
                                    _nombre_sem = _nombre_sem[:36] + "…"
                                row_sem_top.label(text=f"▶  {_nombre_sem}")
                                row_sem_top.label(text=f"f {_cur_frame}")

                                # Progreso dentro de la pose
                                row_sem_bar = col_sem.row(align=True)
                                row_sem_bar.label(
                                    text=f"  [{_fs_act} → {_fe_act}]   {_pct}%  "
                                         f"({_cur_frame - _fs_act + 1}/{_sp_act.duration}f)"
                                )

                                # Contexto: anterior ← ACTIVA → siguiente
                                row_sem_ctx = col_sem.row(align=True)
                                if _active_semaforo > 0:
                                    _prev_n = _poses_ac[_active_semaforo - 1].pose_name \
                                              or _poses_ac[_active_semaforo - 1].json_file or "?"
                                    if len(_prev_n) > 14: _prev_n = _prev_n[:13] + "…"
                                    row_sem_ctx.label(text=f"◀ {_prev_n}", icon="FRAME_PREV")
                                else:
                                    row_sem_ctx.label(text="◀ [inicio]", icon="FRAME_PREV")
                                row_sem_ctx.label(text=" ● ", icon="BLANK1")
                                if _active_semaforo < len(_poses_ac) - 1:
                                    _next_n = _poses_ac[_active_semaforo + 1].pose_name \
                                              or _poses_ac[_active_semaforo + 1].json_file or "?"
                                    if len(_next_n) > 14: _next_n = _next_n[:13] + "…"
                                    row_sem_ctx.label(text=f"{_next_n} ▶", icon="FRAME_NEXT")
                                else:
                                    row_sem_ctx.label(text="[fin] ▶", icon="FRAME_NEXT")
                            else:
                                # Fuera del rango — indicador apagado
                                row_sem_off = box_ac.row()
                                row_sem_off.label(
                                    text=f"  f{_cur_frame} — haz CONCATENAR para activar semaforo",
                                    icon="RADIOBUT_OFF"
                                )
                        except Exception:
                            pass  # El semáforo nunca debe interrumpir el resto del panel
                        # Slot activo info
                        if seg.action_poses_idx < len(seg.action_poses):
                            slot = seg.action_poses[seg.action_poses_idx]
                            try:
                                box_slot = box_ac.box()
                                col_slot = box_slot.column(align=True)

                                # Fila: nombre + botón preview
                                row_prev = col_slot.row(align=True)
                                row_prev.label(
                                    text=f"Slot activo: {slot.pose_name or slot.json_file or '-- vacio --'}"
                                )
                                if getattr(slot, "manual_start", False):
                                    col_slot.label(
                                        text=f"Frame de inicio manual: {slot.frame_abs_start}",
                                        icon="KEYFRAME_HLT",
                                    )
                                op_prev = row_prev.operator(
                                    "alfredseg.preview_action_pose",
                                    text="", icon="HIDE_OFF", emboss=True
                                )
                                op_prev.item_idx = seg.action_poses_idx

                                # ── EDITAR POSE (pos/rot/escala via Pose Mode + N-panel) ──
                                row_edit = col_slot.row(align=True)
                                row_edit.scale_y = 1.1
                                op_edit = row_edit.operator(
                                    "alfredseg.enter_edit_pose",
                                    text="  Editar pose...", icon="GREASEPENCIL"
                                )
                                op_edit.item_idx = i
                                op_save = row_edit.operator(
                                    "alfredseg.save_edited_pose",
                                    text="  Guardar cambios", icon="FILE_TICK"
                                )
                                op_save.item_idx = i
                                col_slot.label(
                                    text="Editar entra a Pose Mode y selecciona el hueso.",
                                    icon="INFO"
                                )
                                col_slot.label(
                                    text="Abre la pestaña 'Item' de este panel N (arriba",
                                    icon="BLANK1"
                                )
                                col_slot.label(
                                    text="derecha, junto a 'Alfred Studio') para ver/editar",
                                    icon="BLANK1"
                                )
                                col_slot.label(
                                    text="Location/Rotation/Scale del hueso activo.",
                                    icon="BLANK1"
                                )
                                col_slot.label(
                                    text="El Root: selecciona el Empty 'alfred' y ajustalo en",
                                    icon="BLANK1"
                                )
                                col_slot.label(
                                    text="Properties > Object > Transform. Guardar escribe ambos.",
                                    icon="BLANK1"
                                )

                                # ── ROOT (Alfred / Empty) de ESTA pose intermedia ──────────
                                # Solo lectura: estos valores se editan posicionando el
                                # Empty "alfred" en Properties > Object > Transform (igual
                                # que un hueso mas) y se capturan al presionar "Guardar
                                # cambios". No se escriben a mano aqui.
                                box_root = col_slot.box()
                                box_root.label(text="Root (Alfred) de esta pose [solo lectura]:", icon="OBJECT_ORIGIN")
                                row_root_pos = box_root.row(align=True)
                                row_root_pos.label(text=f"Pos X {slot.pos_x:.4f}")
                                row_root_pos.label(text=f"Pos Y {slot.pos_y:.4f}")
                                row_root_pos.label(text=f"Pos Z {slot.pos_z:.4f}")
                                row_root_rot = box_root.row(align=True)
                                row_root_rot.label(text=f"Rot X {slot.rot_x:.4f}")
                                row_root_rot.label(text=f"Rot Y {slot.rot_y:.4f}")
                                row_root_rot.label(text=f"Rot Z {slot.rot_z:.4f}")
                                box_root.label(
                                    text="Editar con el Empty 'alfred' + 'Guardar cambios'",
                                    icon="INFO"
                                )
                                box_root.label(
                                    text="Se aplica al CONCATENAR. Persiste con Guardar Config.",
                                    icon="BLANK1"
                                )

                                # ── NOMBRE LEGIBLE desde pose_library.json ────
                                _nombre_leg = None
                                try:
                                    from .pose_utils import leer_nombre_legible
                                    _nombre_leg = leer_nombre_legible(context, slot.json_file)
                                except Exception:
                                    pass

                                if _nombre_leg:
                                    _MAX = 60
                                    try:
                                        if len(_nombre_leg) <= _MAX:
                                            col_slot.label(text=f"↳ {_nombre_leg}", icon="INFO")
                                        else:
                                            _partes = _nombre_leg.split(", ")
                                            _linea  = ""
                                            for _p in _partes:
                                                if len(_linea) + len(_p) + 2 <= _MAX:
                                                    _linea = _linea + (", " if _linea else "") + _p
                                                else:
                                                    col_slot.label(text=f"↳ {_linea}", icon="INFO")
                                                    _linea = _p
                                            if _linea:
                                                col_slot.label(text=f"  {_linea}", icon="BLANK1")
                                    except Exception:
                                        col_slot.label(text=f"↳ {str(_nombre_leg)[:60]}", icon="INFO")
                                # NOTA: NO mutar slot.rating_query aquí — mutar RNA en draw()
                                # hace que Blender aborte silenciosamente el resto del panel.

                                col_slot.prop(slot, "duration",    text="Frames")
                                col_slot.prop(slot, "interp_type", text="Interpolacion")

                            except Exception as _slot_err:
                                box_ac.label(
                                    text=f"[Error dibujando slot: {_slot_err}]",
                                    icon="ERROR"
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
                    # BUGFIX (Kebyn, 2026-07-10): pasar el indice de ESTE
                    # segmento explicitamente. Antes el operador dependia de
                    # alfred_segs.active_index, que no se actualiza al abrir
                    # el box de un segmento (no es un template_list) — asi
                    # que CONCATENAR podia terminar usando las poses y el
                    # rango de OTRO segmento distinto al que se ve en pantalla.
                    op_conc = row_conc.operator("alfst.concatenate", text=_conc_text, icon="PLAY")
                    op_conc.seg_idx = i
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
                    # AISLAMIENTO POR SEGMENTO: org apunta a la instancia PROPIA de
                    # este segmento (seg.organic), no a scene.alfst.organic (global).
                    # Cada segmento guarda y reproduce sus propios valores.
                    box_og = box_cfg.box()
                    org = seg.organic
                    row_og_hdr = box_og.row()
                    row_og_hdr.prop(org, "enabled", text="Filtros organicos")
                    if org.enabled:
                        box_b = box_og.box()
                        box_b.prop(org, "breathing_enabled", text="Respiracion (Spine/Spine1)")
                        if org.breathing_enabled:
                            col_b = box_b.column(align=True)
                            col_b.prop(org, "breathing_amplitude", text="Amplitud")
                            col_b.prop(org, "breathing_speed",     text="Velocidad")
                            col_b.prop(org, "breathing_phase",     text="Fase")
                        box_h = box_og.box()
                        box_h.prop(org, "head_sway_enabled", text="Micro-movimiento cabeza (Neck/face)")
                        if org.head_sway_enabled:
                            col_h = box_h.column(align=True)
                            col_h.prop(org, "head_sway_amplitude", text="Amplitud")
                            col_h.prop(org, "head_sway_speed",     text="Velocidad")
                            col_h.prop(org, "head_sway_seed",      text="Semilla")
                        box_w = box_og.box()
                        box_w.prop(org, "weight_shift_enabled", text="Desplazamiento de peso (Hips)")
                        if org.weight_shift_enabled:
                            col_w = box_w.column(align=True)
                            col_w.prop(org, "weight_shift_amplitude", text="Amplitud")
                            col_w.prop(org, "weight_shift_speed",     text="Velocidad")
                        box_r = box_og.box()
                        box_r.prop(org, "root_noise_enabled", text="Noise posicion ROOT (alfred)")
                        if org.root_noise_enabled:
                            col_r = box_r.column(align=True)
                            col_r.prop(org, "root_noise_strength",  text="Intensidad")
                            col_r.prop(org, "root_noise_frequency", text="Frecuencia")
                            col_r.prop(org, "root_noise_seed",      text="Semilla")
                        box_sec = box_og.box()
                        box_sec.prop(org, "secondary_motion_enabled", text="Secondary motion codos")
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
                        box_ms.prop(org, "micro_scale_enabled", text="Micro-escala organica (Spine1)")
                        if org.micro_scale_enabled:
                            box_ms.prop(org, "micro_scale_amplitude", text="Amplitud")
                        box_sh = box_og.box()
                        box_sh.prop(org, "shoulder_noise_enabled", text="Noise hombros (UpArm L/R)")
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
                                _op_en = _row.operator("alfst.bone_osc_toggle_item", text="", icon=_icon_en)
                                _op_en.item_idx = _oi
                                _axes = "".join(a for a, b in [("X", _oitem.axis_x),("Y", _oitem.axis_y),("Z", _oitem.axis_z)] if b) or "?"
                                _row.label(text=f"  {_oitem.label or _oitem.bone_name}  [{_axes}]  ±{_oitem.amplitude:.0f}°  {_oitem.frame_start}\u2192{_oitem.frame_end}")
                                _op_del = _row.operator("alfst.bone_osc_remove_item", text="", icon="X")
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
                        _op_oadd = row_oadd.operator("alfst.bone_osc_add_item", text="+ Agregar oscilacion", icon="CHECKMARK")
                        _op_oadd.quick_bone = ""
                        box_osc.label(text="Las oscilaciones se aplican al CONCATENAR", icon="INFO")

                    # ── Importacion de Objetos (removido) ────────────────────────────────
                    # Sistema eliminado (Kebyn, 2026-07-14): esta UI duplicaba, dentro de
                    # cada segmento, la funcionalidad que ya cubre por completo el modo
                    # "Mantener" de Lanzar / Recoger Objetos (mismo import + parenteo +
                    # offset + transiciones, ver apply_throw_item / HOLD mas abajo).
                    # El panel superior '3c Importacion de Objetos' (fuera de segmentos)
                    # y el property group st.object_imports siguen existiendo intactos.

                    # ── 3d: Lanzar / Recoger / Mantener Objetos ──────────────────────────
                    try:
                        th = seg.throws
                        box_th = box_cfg.box()

                        # Header con checkbox (se carga automaticamente desde JSON igual que los demas filtros)
                        row_th_hdr = box_th.row(align=True)
                        row_th_hdr.prop(th, "enabled",
                            text="Lanzar / Recoger / Mantener Objetos", icon="FORCE_WIND")

                        # La configuración ahora se edita en el panel global
                        # ubicado al nivel de Segmentos.
                        if False and th.enabled:
                            # ── Lista de items ────────────────────────────────
                            for _ti, _titem in enumerate(th.items):
                                box_ti = box_th.box()
                                box_ti.active = _titem.enabled

                                row_ti_hdr = box_ti.row(align=True)
                                # Toggle activo
                                _icon_en = "HIDE_OFF" if _titem.enabled else "HIDE_ON"
                                _op_tog = row_ti_hdr.operator(
                                    "alfst.throw_toggle_item", text="", icon=_icon_en)
                                _op_tog.seg_idx = i; _op_tog.item_idx = _ti
                                # Label
                                _mode_icon = {"THROW": "FORCE_WIND", "CATCH": "IMPORT",
                                              "HOLD": "PINNED"}.get(_titem.mode, "FORCE_WIND")
                                row_ti_hdr.label(
                                    text=f"  {_titem.label}  [{_titem.object_name}]"
                                         f"  {_titem.frame_start}→{_titem.frame_end}",
                                    icon=_mode_icon)
                                # Botones editar / limpiar / eliminar
                                # (importar + aplicar trayectoria lo hace CONCATENAR)
                                _op_ed = row_ti_hdr.operator(
                                    "alfst.throw_load_to_editor", text="", icon="GREASEPENCIL")
                                _op_ed.seg_idx = i; _op_ed.item_idx = _ti
                                _op_cl = row_ti_hdr.operator(
                                    "alfst.throw_clear_keyframes", text="", icon="TRASH")
                                _op_cl.seg_idx = i; _op_cl.item_idx = _ti
                                _op_rm = row_ti_hdr.operator(
                                    "alfst.throw_remove_item", text="", icon="X")
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
                                            "alfst.throw_wp_from_cursor", text="", icon="PIVOT_CURSOR")
                                        _op_wfc.seg_idx = i; _op_wfc.item_idx = _ti; _op_wfc.wp_idx = _wi
                                        _op_wrm = row_wp.operator(
                                            "alfst.throw_remove_waypoint", text="", icon="X")
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
                                "alfst.throw_browse_blend", text="Buscar .blend...", icon="FILEBROWSER")
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
                                "alfst.throw_detect_armature", text="", icon="VIEWZOOM")
                            _op_det.seg_idx = i
                            box_edit.prop(th, "edit_parent_bone", text="Bone")

                            # Grilla de bones
                            _ALFRED_BONES = [
                                "Hips_alfred","Spine_alfred","Spine1_alfred","Spine2_alfred",
                                "Neck_alfred","face_alfred","RightUpArm_alfred","Rightelbow_alfred",
                                "LeftUpArm_alfred","Leftelbow_alfred","RightUpLeg_alfred",
                                "Rightknee_alfred","LeftUpLeg_alfred","Leftknee_alfred",
                            ]
                            box_bones = box_edit.box()
                            box_bones.label(text="Bones de Alfred:", icon="BONE_DATA")
                            _tgrid = box_bones.grid_flow(row_major=True, columns=2, align=True)
                            for _bn in _ALFRED_BONES:
                                _op_tb = _tgrid.operator(
                                    "alfst.throw_pick_bone", text=_bn, emboss=True,
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

                            # ── Transiciones cartoon (aparicion/desaparicion) ─────────
                            # Disponible para los 3 modos (Lanzar/Recoger/Mantener). En
                            # THROW/CATCH solo sobrevive la parte de escala/rotacion/
                            # alpha (ver nota en apply_throw_item / AlfredThrowItem.
                            # transition_in en properties.py) -- se lo aclaramos al usuario.
                            box_trans_th = box_edit.box()
                            box_trans_th.label(text="Transiciones cartoon:", icon="ANIM")
                            if th.edit_mode != 'HOLD':
                                box_trans_th.label(
                                    text="En Lanzar/Recoger solo aplica escala/rotacion/alpha "
                                         "(la posicion la gobierna la trayectoria)",
                                    icon="INFO")

                            col_th_ti = box_trans_th.column(align=True)
                            col_th_ti.label(text="Aparicion (frame inicio):", icon="KEYFRAME")
                            col_th_ti.prop(th, "edit_transition_in", text="")
                            if th.edit_transition_in != 'NONE':
                                col_th_ti.prop(th, "edit_transition_in_duration",
                                                text="Duracion (frames)")

                            box_trans_th.separator(factor=0.3)

                            col_th_to = box_trans_th.column(align=True)
                            col_th_to.label(text="Desaparicion (frame fin):", icon="KEYFRAME_HLT")
                            col_th_to.prop(th, "edit_transition_out", text="")
                            if th.edit_transition_out != 'NONE':
                                col_th_to.prop(th, "edit_transition_out_duration",
                                                text="Duracion (frames)")

                            # Info: el CONCATENAR se encarga de importar y (si corresponde) aplicar
                            box_edit.separator(factor=0.3)
                            if th.edit_mode == 'HOLD':
                                box_edit.label(
                                    text="El CONCATENAR importa el objeto y lo aparenta "
                                         "(mantener, sin trayectoria)",
                                    icon="INFO")
                            else:
                                box_edit.label(
                                    text="El CONCATENAR importa el objeto y aplica la trayectoria",
                                    icon="INFO")

                            # Destino / trayectoria — NO aplica en modo Mantener (HOLD): el
                            # objeto queda aparentado y quieto donde lo deja el offset sobre
                            # el bone, exactamente igual que el sistema de Importacion de
                            # Objetos. Por eso este bloque completo (bone origen, coordenada
                            # destino, curva de easing, rotacion en vuelo y waypoints) solo
                            # tiene sentido para THROW/CATCH.
                            if th.edit_mode != 'HOLD':
                                box_edit.separator(factor=0.3)
                                box_edit.label(text="Referencia de trayectoria:", icon="FORCE_WIND")
                                box_edit.prop(th, "edit_target_bone", text="Bone origen")
                                _mode_lbl = "destino" if th.edit_mode == 'THROW' else "origen"
                                box_edit.label(
                                    text=f"Coordenada {_mode_lbl} (mundo):", icon="CURSOR")
                                row_ed_cur = box_edit.row()
                                _op_cur = row_ed_cur.operator(
                                    "alfst.throw_pick_dest_cursor",
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
                                        "alfst.throw_add_waypoint",
                                        text="+ Waypoint", icon="ADD")
                                    _op_wpa.seg_idx = i; _op_wpa.item_idx = th.active_idx; _op_wpa.from_cursor = False
                                    _op_wpc = row_ed_wp.operator(
                                        "alfst.throw_add_waypoint",
                                        text="Desde cursor", icon="PIVOT_CURSOR")
                                    _op_wpc.seg_idx = i; _op_wpc.item_idx = th.active_idx; _op_wpc.from_cursor = True

                            # Botones agregar / actualizar
                            box_edit.separator(factor=0.5)
                            row_ed_btns = box_edit.row(align=True)
                            row_ed_btns.scale_y = 1.3
                            _op_add = row_ed_btns.operator(
                                "alfst.throw_add_item",
                                text="+ Agregar lanzamiento", icon="ADD")
                            _op_add.seg_idx = i
                            if th.active_idx >= 0 and th.active_idx < len(th.items):
                                _op_upd = row_ed_btns.operator(
                                    "alfst.throw_update_item",
                                    text="Actualizar", icon="FILE_REFRESH")
                                _op_upd.seg_idx = i; _op_upd.item_idx = th.active_idx

                    except Exception as _e_throw:
                        box_cfg.label(text=f"[Lanzar/Recoger: {_e_throw}]", icon="ERROR")
                    # ── Secuencia de Ojos (Parpadeo + Expresiones propios de este
                    #    segmento) ──────────────────────────────────────────────
                    # ELIMINADO (Kebyn, 2026-08-03: "elimina el sistema de inicio,
                    # intermedio y final del sistema de ojos de los N° segmentos"):
                    # antes, aca dentro del box de CADA segmento se repetia,
                    # identico, todo el bloque "Frame de inicio" + "INICIO (Ojos)"
                    # + "N CAMBIOS DE OJOS (intermedios)" (con Setup de Shape Keys)
                    # + "FIN (Ojos)" + Resumen + CONCATENAR_2 + RESET. Esos
                    # controles NUNCA fueron datos por segmento -- son un sistema
                    # GLOBAL de una sola pasada sobre TODA la timeline (ver
                    # ALFST_OT_Concatenate2.execute: usa scene.alfst.eye_start_*/
                    # eye_slots/eye_end_* directamente, sin ningun indice de
                    # segmento). Mostrarlo repetido en cada segmento sugeria
                    # (incorrectamente) que cada uno tenia su propio Inicio/
                    # Intermedio/Fin independiente, cuando en realidad los N
                    # segmentos escribian y leian exactamente la misma
                    # configuracion global.
                    #
                    # Esa configuracion sigue existiendo y sigue siendo 100%
                    # funcional: ahora vive en un unico lugar, el panel
                    # "2b Secuencia de Ojos" (ya no se oculta al haber
                    # segmentos -- ver ALFST_PT_EyeSequence.poll). Lo que
                    # queda aca, dentro de cada segmento, es EXCLUSIVAMENTE lo
                    # que si es propio de este segmento: Parpadeo automatico
                    # (seg.blink_intervals) y Expresiones de ojos por
                    # intervalos.
                    eye_s = st.eye_expr
                    box_eye_root = box_cfg.box()
                    row_eye_hdr = box_eye_root.row()
                    row_eye_hdr.prop(eye_s, "enabled", text="Sistema de Ojos activo")
                    box_eye_root.active = eye_s.enabled
                    box_eye_root.label(
                        text="  Inicio / Intermedios / Fin: panel '2b Secuencia de Ojos' (global)",
                        icon="INFO",
                    )
                    box_eye_root.separator(factor=0.3)

                    # E) Parpadeo automatico
                    # AISLAMIENTO POR SEGMENTO: la lista de intervalos (bi) es la
                    # coleccion PROPIA de este segmento (seg.blink_intervals), no la
                    # global de scene.alfst. "blink_enabled" (el switch maestro que
                    # habilita el sistema de parpadeo en general) se mantiene global
                    # a proposito -- solo define SI hay parpadeo en la animacion;
                    # el CUANDO/CUANTO (los intervalos) es lo que ahora es propio de
                    # cada segmento. Los operadores CRUD reciben seg_idx=i para
                    # operar sobre seg.blink_intervals y no sobre el global.
                    box_eye_blink = box_eye_root.box()
                    row_blink_hdr = box_eye_blink.row(align=True)
                    row_blink_hdr.prop(eye_s, "blink_enabled", text="", icon="HIDE_OFF" if eye_s.blink_enabled else "HIDE_ON")
                    row_blink_hdr.label(text="Parpadeo automatico — Lista de intervalos (propios de este segmento)", icon="SEQUENCE")
                    if eye_s.blink_enabled:
                        row_bli = box_eye_blink.row()
                        row_bli.template_list(
                            "ALFST_UL_BlinkIntervals", "seg_blink",
                            seg, "blink_intervals",
                            seg, "blink_interval_idx",
                            rows=3,
                        )
                        col_bli = row_bli.column(align=True)
                        op_bli_add = col_bli.operator("alfst.blink_interval_add",       text="", icon="ADD")
                        op_bli_add.seg_idx = i
                        op_bli_rem = col_bli.operator("alfst.blink_interval_remove",    text="", icon="REMOVE")
                        op_bli_rem.seg_idx = i
                        op_bli_dup = col_bli.operator("alfst.blink_interval_duplicate", text="", icon="COPYDOWN")
                        op_bli_dup.seg_idx = i
                        col_bli.separator()
                        op_bu = col_bli.operator("alfst.blink_interval_move", text="", icon="TRIA_UP");  op_bu.direction = "UP"; op_bu.seg_idx = i
                        op_bd = col_bli.operator("alfst.blink_interval_move", text="", icon="TRIA_DOWN"); op_bd.direction = "DOWN"; op_bd.seg_idx = i
                        if 0 <= seg.blink_interval_idx < len(seg.blink_intervals):
                            bi = seg.blink_intervals[seg.blink_interval_idx]
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
                        elif not seg.blink_intervals:
                            box_eye_blink.label(text="  + Agrega un intervalo para definir cuando parpadea", icon="INFO")
                        total_blinks = sum(b.blink_count for b in seg.blink_intervals if b.enabled)
                        if seg.blink_intervals:
                            box_eye_blink.label(
                                text=f"  {len([b for b in seg.blink_intervals if b.enabled])} intervalos activos  |  {total_blinks} parpadeos totales",
                                icon="TIME",
                            )
                    else:
                        box_eye_blink.label(text="  Activar para insertar parpadeos automaticos por intervalos", icon="INFO")

                    # F) Filtro "Reir" -- oscilacion vertical sincronizada de
                    # ambos ojos (Kebyn, 2026-08-18). Mismo patron que E)
                    # Parpadeo automatico arriba: switch maestro global
                    # (eye_s.laugh_enabled) + lista de intervalos PROPIA de
                    # este segmento (seg.laugh_intervals).
                    box_eye_laugh = box_eye_root.box()
                    row_laugh_hdr = box_eye_laugh.row(align=True)
                    row_laugh_hdr.prop(eye_s, "laugh_enabled", text="", icon="HIDE_OFF" if eye_s.laugh_enabled else "HIDE_ON")
                    row_laugh_hdr.label(text="Reir — Lista de intervalos (propios de este segmento)", icon="MOD_SIMPLEDEFORM")
                    if eye_s.laugh_enabled:
                        row_lgi = box_eye_laugh.row()
                        row_lgi.template_list(
                            "ALFST_UL_LaughIntervals", "seg_laugh",
                            seg, "laugh_intervals",
                            seg, "laugh_interval_idx",
                            rows=3,
                        )
                        col_lgi = row_lgi.column(align=True)
                        op_lgi_add = col_lgi.operator("alfst.laugh_interval_add",       text="", icon="ADD")
                        op_lgi_add.seg_idx = i
                        op_lgi_rem = col_lgi.operator("alfst.laugh_interval_remove",    text="", icon="REMOVE")
                        op_lgi_rem.seg_idx = i
                        op_lgi_dup = col_lgi.operator("alfst.laugh_interval_duplicate", text="", icon="COPYDOWN")
                        op_lgi_dup.seg_idx = i
                        col_lgi.separator()
                        op_lu = col_lgi.operator("alfst.laugh_interval_move", text="", icon="TRIA_UP");   op_lu.direction = "UP";   op_lu.seg_idx = i
                        op_ld = col_lgi.operator("alfst.laugh_interval_move", text="", icon="TRIA_DOWN"); op_ld.direction = "DOWN"; op_ld.seg_idx = i
                        if 0 <= seg.laugh_interval_idx < len(seg.laugh_intervals):
                            li = seg.laugh_intervals[seg.laugh_interval_idx]
                            sub_li = box_eye_laugh.box()
                            row_li_hdr = sub_li.row(align=True)
                            row_li_hdr.prop(li, "enabled", text="", icon="HIDE_OFF" if li.enabled else "HIDE_ON")
                            row_li_hdr.prop(li, "label", text="")
                            col_li = sub_li.column(align=True)
                            row_rng_li = col_li.row(align=True)
                            row_rng_li.label(text="Rango:", icon="TIME")
                            row_rng_li.prop(li, "frame_start", text="Ini")
                            row_rng_li.prop(li, "frame_end",   text="Fin")
                            col_li.prop(li, "oscillation_count", text="N° oscilaciones")
                        elif not seg.laugh_intervals:
                            box_eye_laugh.label(text="  + Agrega un intervalo para definir cuando oscilan los ojos", icon="INFO")
                        if seg.laugh_intervals:
                            box_eye_laugh.label(
                                text=f"  {len([l for l in seg.laugh_intervals if l.enabled])} intervalos activos",
                                icon="TIME",
                            )
                    else:
                        box_eye_laugh.label(text="  Activar para oscilar ambos ojos (Z) por intervalos", icon="INFO")

                    # G) Filtro "Entendiendo" -- glance parabolico
                    # sincronizado de ambos ojos, Izquierda/Derecha (Kebyn,
                    # 2026-08-18). Mismo patron que F) Reir arriba: switch
                    # maestro global (eye_s.understand_enabled) + lista de
                    # intervalos PROPIA de este segmento
                    # (seg.understand_intervals).
                    box_eye_und = box_eye_root.box()
                    row_und_hdr = box_eye_und.row(align=True)
                    row_und_hdr.prop(eye_s, "understand_enabled", text="", icon="HIDE_OFF" if eye_s.understand_enabled else "HIDE_ON")
                    row_und_hdr.label(text="Entendiendo — Lista de intervalos (propios de este segmento)", icon="TRACKING_FORWARDS")
                    if eye_s.understand_enabled:
                        row_ugi = box_eye_und.row()
                        row_ugi.template_list(
                            "ALFST_UL_UnderstandIntervals", "seg_understand",
                            seg, "understand_intervals",
                            seg, "understand_interval_idx",
                            rows=3,
                        )
                        col_ugi = row_ugi.column(align=True)
                        op_ugi_add = col_ugi.operator("alfst.understand_interval_add",       text="", icon="ADD")
                        op_ugi_add.seg_idx = i
                        op_ugi_rem = col_ugi.operator("alfst.understand_interval_remove",    text="", icon="REMOVE")
                        op_ugi_rem.seg_idx = i
                        op_ugi_dup = col_ugi.operator("alfst.understand_interval_duplicate", text="", icon="COPYDOWN")
                        op_ugi_dup.seg_idx = i
                        col_ugi.separator()
                        op_uu = col_ugi.operator("alfst.understand_interval_move", text="", icon="TRIA_UP");   op_uu.direction = "UP";   op_uu.seg_idx = i
                        op_ud = col_ugi.operator("alfst.understand_interval_move", text="", icon="TRIA_DOWN"); op_ud.direction = "DOWN"; op_ud.seg_idx = i
                        if 0 <= seg.understand_interval_idx < len(seg.understand_intervals):
                            ui_ = seg.understand_intervals[seg.understand_interval_idx]
                            sub_ui = box_eye_und.box()
                            row_ui_hdr = sub_ui.row(align=True)
                            row_ui_hdr.prop(ui_, "enabled", text="", icon="HIDE_OFF" if ui_.enabled else "HIDE_ON")
                            row_ui_hdr.prop(ui_, "label", text="")
                            col_ui = sub_ui.column(align=True)
                            row_rng_ui = col_ui.row(align=True)
                            row_rng_ui.label(text="Rango:", icon="TIME")
                            row_rng_ui.prop(ui_, "frame_start", text="Ini")
                            row_rng_ui.prop(ui_, "frame_end",   text="Fin")
                            col_ui.prop(ui_, "direction", text="Direccion")
                        elif not seg.understand_intervals:
                            box_eye_und.label(text="  + Agrega un intervalo para definir cuando glancean los ojos", icon="INFO")
                        if seg.understand_intervals:
                            box_eye_und.label(
                                text=f"  {len([u for u in seg.understand_intervals if u.enabled])} intervalos activos",
                                icon="TIME",
                            )
                    else:
                        box_eye_und.label(text="  Activar para glancear ambos ojos (X/Z) por intervalos", icon="INFO")

                    # E2) Expresiones de ojos
                    box_ei = box_eye_root.box()
                    row_ei_hdr = box_ei.row(align=True)
                    row_ei_hdr.prop(eye_s, "expr_intervals_enabled", text="",
                                    icon="HIDE_OFF" if eye_s.expr_intervals_enabled else "HIDE_ON")
                    row_ei_hdr.label(text="Expresiones de ojos — Lista de intervalos", icon="SHAPEKEY_DATA")

                    # ── Setup de Shape Keys (Swap/Inv V/Inv H/Zona/Curva) ──────────
                    # AISLAMIENTO POR SEGMENTO (Kebyn + Claude, 2026-08-05:
                    # "el setup de shape keys de ojos de cada segmento debe ser
                    # completamente independiente entre segmentos, ya que cuando
                    # en un segmento elijo zona superior, este cambio esta
                    # afectando a todos los segmentos creados"). ANTES este
                    # bloque leia/escribia eye_s = st.eye_expr -- la MISMA
                    # instancia global usada por el panel "2b Secuencia de
                    # Ojos" -- asi que cambiar "Zona"/"Curva"/etc. en el box de
                    # un segmento cambiaba ese valor para TODOS los segmentos y
                    # tambien para el panel global. AHORA usa seg.eye_shapekey,
                    # una instancia PROPIA de AlfredEyeShapeKeySetup por
                    # segmento (ver properties.py) -- editar un segmento ya no
                    # afecta a los demas ni al panel global "2b Secuencia de
                    # Ojos" (que sigue usando eye_s para su propio sistema
                    # Inicio/Fin, que es global a proposito). Los shape keys
                    # geometricos de este segmento se generan con estos valores
                    # bajo nombres propios ("Feliz__seg<i>", etc. -- ver
                    # eye_system.build_expression_shape_keys) al Concatenar.
                    # ── MODO COMPARTIDO ELIMINADO (Kebyn, 2026-09-05: "cada
                    # setup de shape keys de ojos debe ser independiente
                    # para cada expresion... que no sea para todas las
                    # expresiones de la lista") ───────────────────────────
                    # ANTES este box mostraba un unico setup (Zona/Curva/
                    # Subdivisiones/Swap/Inv/Intensidades) compartido por
                    # TODAS las expresiones del segmento, y cada expresion
                    # solo obtenia su propio setup si se activaba a mano el
                    # checkbox "propio de esta expresion". AHORA cada
                    # expresion SIEMPRE tiene su propio setup independiente
                    # (ver ensure_expr_interval_shapekey_independent, que
                    # migra automaticamente los valores que cada expresion
                    # ya tenia efectivos, sin opcion de volver a heredar) --
                    # este box global ya no se dibuja aca, el setup se edita
                    # por expresion mas abajo, al seleccionar cada una en la
                    # lista.
                    ensure_eye_shapekey_migrated(seg, context.scene)
                    ensure_expr_interval_shapekey_independent(seg)

                    if eye_s.expr_intervals_enabled:
                        # AISLAMIENTO POR SEGMENTO (Kebyn + Claude, 2026-08-04):
                        # la lista de intervalos (ei) es la coleccion PROPIA de
                        # este segmento (seg.expr_intervals), no la global de
                        # scene.alfst -- mismo criterio que "E) Parpadeo
                        # automatico" arriba (seg.blink_intervals). Los
                        # operadores CRUD reciben seg_idx=i para operar sobre
                        # seg.expr_intervals y no sobre el global.
                        row_ei_lst = box_ei.row()
                        row_ei_lst.template_list(
                            "ALFST_UL_EyeExprIntervals", "seg_expr",
                            seg, "expr_intervals",
                            seg, "expr_interval_idx",
                            rows=3,
                        )
                        col_ei2 = row_ei_lst.column(align=True)
                        op_ei_add = col_ei2.operator("alfst.expr_interval_add",       text="", icon="ADD")
                        op_ei_add.seg_idx = i
                        op_ei_rem = col_ei2.operator("alfst.expr_interval_remove",    text="", icon="REMOVE")
                        op_ei_rem.seg_idx = i
                        op_ei_dup = col_ei2.operator("alfst.expr_interval_duplicate", text="", icon="COPYDOWN")
                        op_ei_dup.seg_idx = i
                        col_ei2.separator()
                        op_eu = col_ei2.operator("alfst.expr_interval_move", text="", icon="TRIA_UP");  op_eu.direction = "UP"; op_eu.seg_idx = i
                        op_ed = col_ei2.operator("alfst.expr_interval_move", text="", icon="TRIA_DOWN"); op_ed.direction = "DOWN"; op_ed.seg_idx = i
                        col_ei2.separator()
                        op_ei_edit = col_ei2.operator("alfst.edit_expr_interval", text="", icon="GREASEPENCIL")
                        op_ei_edit.seg_idx = i
                        if 0 <= seg.expr_interval_idx < len(seg.expr_intervals):
                            ei = seg.expr_intervals[seg.expr_interval_idx]
                            sub_ei = box_ei.box()
                            row_ei_top = sub_ei.row(align=True)
                            row_ei_top.prop(ei, "enabled", text="", icon="HIDE_OFF" if ei.enabled else "HIDE_ON")
                            row_ei_top.prop(ei, "label", text="")
                            col_ei3 = sub_ei.column(align=True)
                            row_frames = col_ei3.row(align=True)
                            row_frames.label(text="Frames:", icon="KEYFRAME")
                            row_frames.prop(ei, "duration", text="")
                            row_expr = col_ei3.row(align=True)
                            row_expr.label(text="Expresion:", icon="SHAPEKEY_DATA")
                            row_expr.prop(ei, "expression", text="")
                            row_expr.prop(ei, "expression_value", text="Intensidad")
                            row_itp_ei = col_ei3.row(align=True)
                            row_itp_ei.label(text="Interp entrada:", icon="IPO_BEZIER")
                            row_itp_ei.prop(ei, "interp_in",  text="")
                            row_itp_ei.label(text="Interp salida:")
                            row_itp_ei.prop(ei, "interp_out", text="")

                            # ── Setup de Shape Keys de ojos PROPIO de esta
                            # expresion (Kebyn, 2026-08-18, actualizado
                            # 2026-09-05: "cada expresion debera tener su
                            # propio setup... y que no sea para todas las
                            # expresiones de la lista") ───────────────────
                            # Ya NO es opcional: toda expresion tiene siempre
                            # su propio setup independiente (ei.own_shapekey),
                            # sin checkbox ni modo "heredar" -- eliminado el
                            # setup compartido a nivel de segmento. Editar
                            # "Enojo" aca nunca afecta a "Triste" ni a
                            # ninguna otra expresion de la lista.
                            box_sk_ei_own = sub_ei.box()
                            box_sk_ei_own.label(
                                text="Setup de Shape Keys de ojos (propio de esta expresion)",
                                icon="MESH_PLANE",
                            )
                            sk_ei = ei.own_shapekey
                            col_sk_ei_own = box_sk_ei_own.column(align=True)
                            col_sk_ei_own.prop(sk_ei, "subdivide_cuts", text="Subdivisiones previas")
                            row_sk_ei_own1 = col_sk_ei_own.row(align=True)
                            row_sk_ei_own1.prop(sk_ei, "swap_axes",         toggle=True)
                            row_sk_ei_own1.prop(sk_ei, "invert_vertical",   toggle=True, text="Inv V")
                            row_sk_ei_own1.prop(sk_ei, "invert_horizontal", toggle=True, text="Inv H")
                            col_sk_ei_own.prop(sk_ei, "affect_zone", text="Zona")
                            col_sk_ei_own.prop(sk_ei, "curve_mode",  text="Curva")
                            row_sk_ei_own2 = col_sk_ei_own.row(align=True)
                            row_sk_ei_own2.prop(sk_ei, "intensity_feliz",    text="Feliz")
                            row_sk_ei_own2.prop(sk_ei, "intensity_triste",   text="Triste")
                            row_sk_ei_own3 = col_sk_ei_own.row(align=True)
                            row_sk_ei_own3.prop(sk_ei, "intensity_enojado",  text="Enojo")
                            row_sk_ei_own3.prop(sk_ei, "intensity_sospecha", text="Sospecha")

                            row_edit_ei = sub_ei.row()
                            op_ei_edit2 = row_edit_ei.operator("alfst.edit_expr_interval", icon="GREASEPENCIL",
                                                  text="Editar posicion / rotacion / escala de cada ojo...")
                            op_ei_edit2.seg_idx = i
                        elif not seg.expr_intervals:
                            box_ei.label(text="  + Agrega un intervalo de expresion de ojos", icon="INFO")
                        active_ei_list = [e for e in seg.expr_intervals if e.enabled]
                        if seg.expr_intervals:
                            box_ei.label(text=f"  {len(active_ei_list)} intervalos activos en la timeline", icon="TIME")
                        box_ei.label(text="  Los intervalos pueden solaparse con el parpadeo", icon="INFO")

                        # BOTON CONCATENAR EXPRESIONES (Kebyn, 2026-09-06):
                        # a diferencia de "Concatenar segmentos" (que corre
                        # TODO el segmento), este boton solo reproduce la
                        # secuencia de expr_intervals de este segmento --
                        # limpia primero cualquier residuo de una corrida
                        # anterior antes de insertar los keyframes nuevos.
                        row_cat_ei = box_ei.row()
                        row_cat_ei.scale_y = 1.3
                        op_cat_ei = row_cat_ei.operator(
                            "alfst.concatenate_expr_intervals", icon="PLAY",
                            text="Concatenar expresiones")
                        op_cat_ei.seg_idx = i
                        box_ei.label(
                            text="  Solo reproduce la secuencia de expresiones — limpia residuos previos",
                            icon="INFO")
                    else:
                        box_ei.label(text="  Activar para definir emociones por intervalos de frames", icon="INFO")

                    # ELIMINADO junto con el bloque de arriba (Kebyn, 2026-08-03):
                    # el resumen de duracion Inicio+Cambios+Fin, el boton
                    # "CONCATENAR_2 (Ojos)" y "RESET Sistema de Ojos" pertenecen
                    # exclusivamente al sistema GLOBAL de una sola pasada -- ya
                    # no se dibujan aca. Siguen disponibles, sin cambios de
                    # comportamiento, en el panel "2b Secuencia de Ojos".

                else:
                    # Resumen compacto cuando esta colapsado
                    col_info = box_seg.column(align=True)
                    col_info.scale_y = 0.75
                    if seg.pose_mid_label or seg.pose_mid_file:
                        col_info.label(text=f"  Interm: {seg.pose_mid_label or seg.pose_mid_file}  fr{seg.frame_mid}", icon="DOT")
        else:
            box_list.label(text="  (sin segmentos — crea uno arriba)", icon="INFO")
