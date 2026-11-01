# -*- coding: utf-8 -*-
"""
panels.py — Jerry Animation Studio v1.0
Paneles UI: Setup, Secuencia de poses, Filtros organicos, Exportar, Configuracion.
Sin panel de ojos (jerry no tiene mallas de ojos ni pupilas).
"""
import bpy, os
from bpy.types import Panel, UIList
from .properties import load_historia_json, get_key_points
from .operators_segments import _calc_seg_frames


def _draw_parada_anim_row_jerry(layout, pt, idx):
    """NUEVO (Kebyn, 2026-09-14, portado de Alfred): fila auxiliar bajo
    cada punto marcado como 'Parada' que deja importar/quitar un script
    .py de animacion para ese punto -- ver
    JRRSTPathPoint.parada_anim_file (path_recorder.py) y
    JRRSTPR_OT_ImportParadaAnim / JRRSTPR_OT_ClearParadaAnim.
    """
    row_anim = layout.row(align=True)
    row_anim.separator(factor=2.2)
    if pt.parada_anim_file:
        row_anim.label(text=os.path.basename(pt.parada_anim_file), icon="FILE_MOVIE")
        op_clear = row_anim.operator(
            "jerrypr.clear_parada_anim", text="", icon="X", emboss=False)
        op_clear.index = idx
    else:
        op_imp = row_anim.operator(
            "jerrypr.import_parada_anim",
            text="Importar animacion (.py)", icon="FILEBROWSER")
        op_imp.index = idx


def _draw_parada_rot_row_jerry(layout, pt, idx):
    """NUEVO (Kebyn, 2026-09-14, portado de Alfred): fila auxiliar bajo
    cada punto marcado como 'Parada' que deja rotar el empty root
    ('jerry') a mano y guardar esa orientacion para este punto -- ver
    JRRSTPathPoint.parada_rot_saved/parada_rot_z y
    JRRSTPR_OT_RotateParadaRoot / JRRSTPR_OT_SaveParadaRot /
    JRRSTPR_OT_ClearParadaRot (path_recorder.py). Mientras la
    orientacion este guardada, se usa como heading desde este punto de
    parada en adelante hasta el proximo tramo con desplazamiento real o
    hasta que se vuelva a editar.
    """
    row_rot = layout.row(align=True)
    row_rot.separator(factor=2.2)
    op_rot = row_rot.operator(
        "jerrypr.rotate_parada_root", text="Rotar root (jerry)", icon="ORIENTATION_GIMBAL")
    if pt.parada_rot_saved:
        row_rot.label(text=f"Orientacion: {pt.parada_rot_z:.1f}°", icon="CHECKMARK")
        op_clear_rot = row_rot.operator(
            "jerrypr.clear_parada_rot", text="", icon="X", emboss=False)
        op_clear_rot.index = idx
    else:
        op_save_rot = row_rot.operator(
            "jerrypr.save_parada_rot", text="Guardar orientacion", icon="FILE_TICK")
        op_save_rot.index = idx


def _draw_interaccion_row_jerry(layout, pt, idx):
    """NUEVO (Kebyn, portado de Alfred): fila auxiliar que aparece bajo
    un punto marcado como 'Interactuar' -- solo puede estar marcado asi
    si el punto es un punto de encuentro real con el recorrido de
    Alfred (ver _point_is_meeting_point()/_tipo_segmento_items() en
    path_recorder.py). Deja elegir, de un dropdown, cual de los .py de
    DEFAULT_INTERACTION_DIR_JERRY reproducir aqui.
    """
    row = layout.row(align=True)
    row.separator(factor=2.2)
    row.label(text="Interactuar con:", icon="COMMUNITY")
    row.prop(pt, "interaccion_anim_choice", text="")
    row.operator(
        "jerrypr.open_interaction_folder", text="", icon="FILEBROWSER")
    if pt.interaccion_anim_choice == "NONE":
        row_warn = layout.row(align=True)
        row_warn.separator(factor=2.2)
        row_warn.label(
            text="Todavia no hay animaciones .py en la carpeta de interaccion",
            icon="ERROR")


# =============================================================================
# UILIST — POSES
# =============================================================================

class JRRST_UL_ActionPoses(UIList):
    bl_idname = "JRRST_UL_ActionPoses"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        _label = item.pose_name or item.pose_label or item.json_file or '-- vacia --'
        row.label(text=f"[{index+1}] {_label}", icon="POSE_HLT")
        sub = row.row()
        sub.alignment = "RIGHT"
        # Frame de inicio manual, si el usuario lo fijo (portado de Alfred)
        if getattr(item, "manual_start", False):
            sub.label(text=f"@f{item.frame_abs_start}", icon="KEYFRAME_HLT")
        sub.label(text=f"{item.duration}f")

# =============================================================================
# PANEL PRINCIPAL (contenedor)
# =============================================================================

class JRRST_PT_Main(Panel):
    bl_label       = "Jerry Studio"
    bl_idname      = "JRRST_PT_main"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Jerry Studio"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Jerry Animation Studio", icon="ARMATURE_DATA")

# =============================================================================
# 1. PANEL SETUP
# =============================================================================

class JRRST_PT_Setup(Panel):
    bl_label       = "1  Setup"
    bl_idname      = "JRRST_PT_setup"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Jerry Studio"
    bl_parent_id   = "JRRST_PT_main"
    bl_order       = 1

    @classmethod
    def poll(cls, context):
        # Setup ahora vive dentro de cada segmento en el Paso 3.
        return False

    def draw(self, context):
        layout = self.layout
        st     = context.scene.jerryst

        box = layout.box()
        box.label(text="Armature principal", icon="ARMATURE_DATA")
        row = box.row(align=True)
        row.prop(st, "armature_name", text="")
        row.operator("jerryst.set_armature", text="", icon="EYEDROPPER")

        box2 = layout.box()
        box2.label(text="Carpetas", icon="FILE_FOLDER")
        col = box2.column(align=True)
        col.prop(st, "poses_dir",  text="Poses")
        col.prop(st, "anim_dir",   text="Animaciones")
        col.prop(st, "config_dir", text="Configuraciones")
        col.prop(st, "pose_changes_dir", text="Cambios de pose")
        row2 = box2.row(align=True)
        row2.operator("jerryst.open_poses_folder", text="Poses", icon="FILE_FOLDER")
        row2.operator("jerryst.open_anim_folder",  text="Anims", icon="FILE_FOLDER")
        row2.operator("jerryst.refresh_poses",     text="",      icon="FILE_REFRESH")

        layout.operator("jerryst.reset", text="Reset todo", icon="LOOP_BACK")

# =============================================================================
# 3. PANEL FILTROS ORGANICOS
# =============================================================================

class JRRST_PT_OrganicFilters(Panel):
    bl_label       = "2b  Filtros organicos"
    bl_idname      = "JRRST_PT_organicfilters"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Jerry Studio"
    bl_parent_id   = "JRRST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}
    bl_order       = 3

    @classmethod
    def poll(cls, context):
        # Este panel global ya no se usa — la UI vive dentro de cada segmento.
        return False

    def draw(self, context):
        layout = self.layout
        st     = context.scene.jerryst
        og     = st.organic

        layout.prop(og, "enabled", text="Activar filtros organicos")
        if not og.enabled:
            return

        # ── Filtro 1: Respiracion ─────────────────────────────────────────
        box_b = layout.box()
        row_b = box_b.row()
        row_b.prop(og, "breathing_enabled", text="Respiracion  (spine_4 / spine_5)")
        if og.breathing_enabled:
            col = box_b.column(align=True)
            col.prop(og, "breathing_amplitude", text="Amplitud")
            col.prop(og, "breathing_speed",     text="Velocidad")
            col.prop(og, "breathing_phase",     text="Fase")

        # ── Filtro 2: Micro-movimiento cabeza ─────────────────────────────
        box_h = layout.box()
        box_h.prop(og, "head_sway_enabled", text="Micro-movimiento cabeza  (scull_1, scull)")
        if og.head_sway_enabled:
            col = box_h.column(align=True)
            col.prop(og, "head_sway_amplitude", text="Amplitud")
            col.prop(og, "head_sway_speed",     text="Velocidad")
            col.prop(og, "head_sway_seed",      text="Semilla")

        # ── Filtro 3: Desplazamiento de peso ──────────────────────────────
        box_w = layout.box()
        box_w.prop(og, "weight_shift_enabled", text="Desplazamiento de peso  (spine_6)")
        if og.weight_shift_enabled:
            col = box_w.column(align=True)
            col.prop(og, "weight_shift_amplitude", text="Amplitud")
            col.prop(og, "weight_shift_speed",     text="Velocidad")

        # ── Filtro 4: Noise en ROOT ───────────────────────────────────────
        box_r = layout.box()
        box_r.prop(og, "root_noise_enabled", text="Noise en ROOT  (jerry Empty)")
        if og.root_noise_enabled:
            col = box_r.column(align=True)
            col.prop(og, "root_noise_strength",  text="Intensidad")
            col.prop(og, "root_noise_frequency", text="Frecuencia")
            col.prop(og, "root_noise_seed",      text="Semilla")

        # ── Filtro 5: Secondary motion brazos ─────────────────────────────
        box_sec = layout.box()
        box_sec.prop(og, "secondary_motion_enabled", text="Secondary motion brazos  (front_thigh)")
        if og.secondary_motion_enabled:
            col = box_sec.column(align=True)
            col.prop(og, "secondary_motion_lag",     text="Retardo (frames)")
            col.prop(og, "secondary_motion_damping", text="Amortiguacion")

        # ── Filtro 6: Suavizado de fcurves ────────────────────────────────
        box_sm = layout.box()
        box_sm.prop(og, "smooth_curves_enabled", text="Suavizar fcurves")
        if og.smooth_curves_enabled:
            col = box_sm.column(align=True)
            col.prop(og, "smooth_passes", text="Pasadas")
            col.prop(og, "smooth_factor", text="Factor", slider=True)

        # ── Filtro 7: Micro-escala organica ───────────────────────────────
        box_ms = layout.box()
        box_ms.prop(og, "micro_scale_enabled", text="Micro-escala organica  (spine_4 Z)")
        if og.micro_scale_enabled:
            box_ms.prop(og, "micro_scale_amplitude", text="Amplitud")

        # ── Filtro 8: Noise en hombros ────────────────────────────────────
        box_sh = layout.box()
        box_sh.prop(og, "shoulder_noise_enabled", text="Noise hombros  (front_shoulder.R/L)")
        if og.shoulder_noise_enabled:
            col = box_sh.column(align=True)
            col.prop(og, "shoulder_noise_amplitude", text="Amplitud")
            col.prop(og, "shoulder_noise_speed",     text="Velocidad")
            col.prop(og, "shoulder_noise_seed",      text="Semilla")

        # ── Filtro 9: Oscilacion de cola ──────────────────────────────────
        box_t = layout.box()
        box_t.prop(og, "tail_wag_enabled", text="Oscilacion cola  (tail_1 / tail_2 / tail_3)")
        if og.tail_wag_enabled:
            col = box_t.column(align=True)
            col.prop(og, "tail_wag_amplitude", text="Amplitud (rad)")
            col.prop(og, "tail_wag_speed",     text="Velocidad")
            col.prop(og, "tail_wag_phase",     text="Fase")
            col.prop(og, "tail_wag_lag",       text="Retardo entre bones", slider=True)

        # ── Filtro 10: Oscilacion de orejas ──────────────────────────────────
        box_ear = layout.box()
        box_ear.prop(og, "ear_osc_enabled", text="Oscilacion orejas  (ear.L / ear.R)")
        if og.ear_osc_enabled:
            _draw_ear_osc_list(box_ear, og)

        # ── Filtro 11: Oscilacion de mandibula ────────────────────────────────
        box_jaw = layout.box()
        box_jaw.prop(og, "jaw_osc_enabled", text="Oscilacion mandibula  (jaw_bot)")
        if og.jaw_osc_enabled:
            _draw_jaw_osc_list(box_jaw, og)

        # ── Filtro 12: Emociones de cejas ─────────────────────────────────────
        box_em = layout.box()
        box_em.prop(og, "emotion_enabled", text="Emociones  (sejas_1_jerry / sejas_2_jerry)")
        if og.emotion_enabled:
            _draw_emotion_list(box_em, og)

# =============================================================================
# HELPERS: UI de intervalos de orejas y mandibula
# =============================================================================

def _draw_bone_block_row(layout, seg, seg_idx, filter_attr):
    """
    PORTADO desde alfred_animation_studio (_draw_bone_block_row, Kebyn,
    2026-08-08). Dibuja la fila de bloqueo de UN bone dentro del Filtro de
    bones:
      - Checkbox de bloqueo total (bloquea el bone en todo el segmento).
      - Boton [+] para agregar un intervalo de frames de bloqueo especifico.
      - Lista de los intervalos ya creados para ese bone (Inicio / Fin / activo / eliminar).
    Un mismo bone puede tener varios intervalos independientes
    (ej: bloqueado 60→100, luego otra vez 500→630).
    """
    row = layout.row(align=True)
    row.prop(seg, filter_attr, icon="BONE_DATA")
    op_add = row.operator("jerryseg.add_bone_interval", text="", icon="ADD")
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
            op_rm = row_iv.operator("jerryseg.remove_bone_interval", text="", icon="X")
            op_rm.item_idx     = seg_idx
            op_rm.bone_key     = filter_attr
            op_rm.interval_idx = iv_idx


def _draw_ear_osc_list(layout, og, seg_idx=-1):
    """Dibuja la lista de intervalos de orejas y su formulario de edicion.

    `seg_idx` (Kebyn + Claude, 2026-08-06 -- aislamiento por segmento): se
    propaga a cada operador para que opere sobre el `organic` PROPIO del
    segmento cuyo box se esta dibujando (ver _resolve_seg_organic en
    operators_anim.py), en vez de siempre sobre scene.jerryst.organic."""
    # Lista
    box_list = layout.box()
    box_list.label(text="Intervalos:", icon="NLA")
    if og.ear_items:
        for i, item in enumerate(og.ear_items):
            row = box_list.row(align=True)
            icon_en = "HIDE_OFF" if item.enabled else "HIDE_ON"
            op_en = row.operator("jerryst.ear_osc_toggle", text="", icon=icon_en)
            op_en.item_idx = i
            op_en.seg_idx  = seg_idx
            is_editing = (og.ear_edit_mode == "EDIT" and og.ear_edit_source_idx == i)
            row.label(
                text=f"  {item.label}  fr {item.frame_start}\u2192{item.frame_end}  \xb1{item.amplitude:.3f}rad  [{item.axis}]",
                icon="GREASEPENCIL" if is_editing else "BLANK1",
            )
            op_edit = row.operator("jerryst.ear_osc_load", text="", icon="GREASEPENCIL")
            op_edit.item_idx = i
            op_edit.seg_idx  = seg_idx
            op_del = row.operator("jerryst.ear_osc_remove", text="", icon="X")
            op_del.item_idx = i
            op_del.seg_idx  = seg_idx
    else:
        box_list.label(text="  (sin intervalos)", icon="INFO")

    # Formulario
    box_edit = layout.box()
    is_edit = (og.ear_edit_mode == "EDIT" and 0 <= og.ear_edit_source_idx < len(og.ear_items))
    if is_edit:
        row_t = box_edit.row(align=True)
        row_t.label(text=f"Editando: {og.ear_items[og.ear_edit_source_idx].label}", icon="GREASEPENCIL")
        op_cancel = row_t.operator("jerryst.ear_osc_cancel", text="", icon="X")
        op_cancel.seg_idx = seg_idx
    else:
        box_edit.label(text="Nuevo intervalo:", icon="ADD")

    col = box_edit.column(align=True)
    col.prop(og, "ear_edit_label",       text="Etiqueta")
    row_f = col.row(align=True)
    row_f.prop(og, "ear_edit_frame_start", text="Inicio")
    row_f.prop(og, "ear_edit_frame_end",   text="Fin")
    col.prop(og, "ear_edit_axis",          text="Eje")
    col.prop(og, "ear_edit_amplitude",     text="Amplitud (rad)")
    col.prop(og, "ear_edit_speed",         text="Velocidad")
    row_ph = col.row(align=True)
    row_ph.prop(og, "ear_edit_phase_l",    text="Fase L")
    row_ph.prop(og, "ear_edit_phase_r",    text="Fase R")

    row_btn = box_edit.row()
    row_btn.scale_y = 1.4
    if is_edit:
        op_save = row_btn.operator("jerryst.ear_osc_save", text="\u2714 Guardar cambios", icon="CHECKMARK")
        op_save.seg_idx = seg_idx
    else:
        op_add = row_btn.operator("jerryst.ear_osc_add", text="+ Agregar intervalo", icon="CHECKMARK")
        op_add.seg_idx = seg_idx


def _draw_jaw_osc_list(layout, og, seg_idx=-1):
    """Dibuja la lista de intervalos de mandibula y su formulario de edicion.
    Ver `seg_idx` en _draw_ear_osc_list (mismo patron de aislamiento)."""
    # Lista
    box_list = layout.box()
    box_list.label(text="Intervalos:", icon="NLA")
    if og.jaw_items:
        for i, item in enumerate(og.jaw_items):
            row = box_list.row(align=True)
            icon_en = "HIDE_OFF" if item.enabled else "HIDE_ON"
            op_en = row.operator("jerryst.jaw_osc_toggle", text="", icon=icon_en)
            op_en.item_idx = i
            op_en.seg_idx  = seg_idx
            is_editing = (og.jaw_edit_mode == "EDIT" and og.jaw_edit_source_idx == i)
            row.label(
                text=f"  {item.label}  fr {item.frame_start}\u2192{item.frame_end}  \xb1{item.amplitude:.1f}\xb0  [{item.axis}]",
                icon="GREASEPENCIL" if is_editing else "BLANK1",
            )
            op_edit = row.operator("jerryst.jaw_osc_load", text="", icon="GREASEPENCIL")
            op_edit.item_idx = i
            op_edit.seg_idx  = seg_idx
            op_del = row.operator("jerryst.jaw_osc_remove", text="", icon="X")
            op_del.item_idx = i
            op_del.seg_idx  = seg_idx
    else:
        box_list.label(text="  (sin intervalos)", icon="INFO")

    # Formulario
    box_edit = layout.box()
    is_edit = (og.jaw_edit_mode == "EDIT" and 0 <= og.jaw_edit_source_idx < len(og.jaw_items))
    if is_edit:
        row_t = box_edit.row(align=True)
        row_t.label(text=f"Editando: {og.jaw_items[og.jaw_edit_source_idx].label}", icon="GREASEPENCIL")
        op_cancel = row_t.operator("jerryst.jaw_osc_cancel", text="", icon="X")
        op_cancel.seg_idx = seg_idx
    else:
        box_edit.label(text="Nuevo intervalo:", icon="ADD")

    col = box_edit.column(align=True)
    col.prop(og, "jaw_edit_label", text="Etiqueta")

    # Inicio / Fin en una sola fila
    row_f = col.row(align=True)
    row_f.prop(og, "jaw_edit_frame_start", text="Inicio")
    row_f.prop(og, "jaw_edit_frame_end",   text="Fin")

    col.prop(og, "jaw_edit_amplitude", text="Apertura (grad)")
    col.prop(og, "jaw_edit_cycles",    text="Ciclos")
    col.prop(og, "jaw_edit_transition", text="Transicion")
    if og.jaw_edit_transition == "NOISE":
        col.prop(og, "jaw_edit_noise_seed", text="Semilla noise")

    row_btn = box_edit.row()
    row_btn.scale_y = 1.4
    if is_edit:
        op_save = row_btn.operator("jerryst.jaw_osc_save", text="\u2714 Guardar cambios", icon="CHECKMARK")
        op_save.seg_idx = seg_idx
    else:
        op_add = row_btn.operator("jerryst.jaw_osc_add", text="+ Agregar oscilacion", icon="CHECKMARK")
        op_add.seg_idx = seg_idx


def _draw_emotion_list(layout, og, seg_idx=-1):
    """Dibuja la lista de intervalos de emocion de cejas y su formulario de
    edicion. Ver `seg_idx` en _draw_ear_osc_list (mismo patron de aislamiento)."""
    _EMOTION_LABELS = {
        "enojado":                "Enojado",
        "triste":                 "Triste",
        "sorprendido":            "Sorprendido",
        "levanta_la_ceja_derecha":"Ceja der.",
        "levanta_la_ceja_izquierda":"Ceja izq.",
    }

    # Lista
    box_list = layout.box()
    box_list.label(text="Intervalos:", icon="NLA")
    if og.emotion_items:
        for i, item in enumerate(og.emotion_items):
            row = box_list.row(align=True)
            icon_en = "HIDE_OFF" if item.enabled else "HIDE_ON"
            op_en = row.operator("jerryst.emotion_toggle", text="", icon=icon_en)
            op_en.item_idx = i
            op_en.seg_idx  = seg_idx
            is_editing = (og.emotion_edit_mode == "EDIT" and og.emotion_edit_source_idx == i)
            em_label = _EMOTION_LABELS.get(item.emotion, item.emotion)
            row.label(
                text=f"  {item.label}  fr {item.frame_start}→{item.frame_end}  {em_label}",
                icon="GREASEPENCIL" if is_editing else "BLANK1",
            )
            op_edit = row.operator("jerryst.emotion_load", text="", icon="GREASEPENCIL")
            op_edit.item_idx = i
            op_edit.seg_idx  = seg_idx
            op_del = row.operator("jerryst.emotion_remove", text="", icon="X")
            op_del.item_idx = i
            op_del.seg_idx  = seg_idx
    else:
        box_list.label(text="  (sin intervalos)", icon="INFO")

    # Formulario
    box_edit = layout.box()
    is_edit = (og.emotion_edit_mode == "EDIT" and 0 <= og.emotion_edit_source_idx < len(og.emotion_items))
    if is_edit:
        row_t = box_edit.row(align=True)
        row_t.label(text=f"Editando: {og.emotion_items[og.emotion_edit_source_idx].label}", icon="GREASEPENCIL")
        op_cancel = row_t.operator("jerryst.emotion_cancel", text="", icon="X")
        op_cancel.seg_idx = seg_idx
    else:
        box_edit.label(text="Nueva emocion:", icon="ADD")

    col = box_edit.column(align=True)
    col.prop(og, "emotion_edit_label",         text="Etiqueta")
    col.prop(og, "emotion_edit_emotion",       text="Emocion")
    col.separator()
    row_f = col.row(align=True)
    row_f.prop(og, "emotion_edit_frame_start", text="Inicio")
    row_f.prop(og, "emotion_edit_frame_end",   text="Fin")
    row_t = col.row(align=True)
    row_t.prop(og, "emotion_edit_transition_in",  text="Entrada")
    row_t.prop(og, "emotion_edit_transition_out", text="Salida")
    col.prop(og, "emotion_edit_interp_type",   text="Transicion")

    row_btn = box_edit.row()
    row_btn.scale_y = 1.4
    if is_edit:
        op_save = row_btn.operator("jerryst.emotion_save", text="✔ Guardar cambios", icon="CHECKMARK")
        op_save.seg_idx = seg_idx
    else:
        op_add = row_btn.operator("jerryst.emotion_add", text="+ Agregar emocion", icon="CHECKMARK")
        op_add.seg_idx = seg_idx


# =============================================================================
# HELPER: leer bones del JSON de historia (jerry)
# =============================================================================

def _get_bones_from_historia(context):
    """
    Extrae la lista de bones del personaje usando multiples fuentes en orden de prioridad:
      1. Armature activo en la escena de Blender (mas fiable, siempre actualizado)
      2. JSON estilo jerry.json  -> collections.scene_collection.objects[*].bone_hierarchy
      3. JSON estilo historia_jerry_*.json -> rig_info.categorias_animacion.completo
      4. JSON estilo historia -> aplanar bones_principales
    Devuelve lista de strings o [] si falla.
    """
    import bpy, json, os

    # ── Fuente 1: leer directamente del armature en escena ──────────────────
    try:
        st = context.scene.jerryst
        arm_name = getattr(st, "armature_name", "Dog_001_rig")
        arm_obj = bpy.data.objects.get(arm_name)
        if arm_obj and arm_obj.type == "ARMATURE" and arm_obj.data.bones:
            return sorted([b.name for b in arm_obj.data.bones])
    except Exception as e:
        print(f"[JRRSTStudio] bones_from_armature error: {e}")

    # ── Fuente 2 y 3: leer desde el JSON configurado ────────────────────────
    try:
        st = context.scene.jerryst
        filepath = bpy.path.abspath(st.historia_json)
        if not filepath or not os.path.isfile(filepath):
            return []
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Fuente 2: formato jerry.json -> bone_hierarchy recursivo
        def _extract_from_hierarchy(bone_list, out=None):
            if out is None:
                out = []
            for bone in bone_list:
                name = bone.get("name")
                if name and name not in out:
                    out.append(name)
                children = bone.get("children", [])
                if children:
                    _extract_from_hierarchy(children, out)
            return out

        collections = data.get("collections", {})
        scene_col = collections.get("scene_collection", {})
        objects = scene_col.get("objects", [])
        all_bones_hier = []
        for obj in objects:
            hier = obj.get("bone_hierarchy")
            if hier and isinstance(hier, list):
                _extract_from_hierarchy(hier, all_bones_hier)
        if all_bones_hier:
            return sorted(all_bones_hier)

        # Fuente 3: formato historia_jerry_*.json -> rig_info.categorias_animacion.completo
        rig = data.get("rig_info", {})
        completo = rig.get("categorias_animacion", {}).get("completo", [])
        if completo and isinstance(completo, list):
            return [b for b in completo if isinstance(b, str)]

        # Fuente 4: aplanar bones_principales
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
        print(f"[JRRSTStudio] _get_bones_from_historia error: {e}")
        return []


# =============================================================================
# 3b. PANEL: OSCILACIONES DE BONES (jerry)
# =============================================================================

class JRRST_PT_BoneOscillations(Panel):
    bl_label       = "3b  Oscilaciones de Bones"
    bl_idname      = "JRRST_PT_bone_osc"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Jerry Studio"
    bl_parent_id   = "JRRST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}
    bl_order       = 4

    @classmethod
    def poll(cls, context):
        # Este panel global ya no se usa — la UI vive dentro de cada segmento.
        return False

    def draw_header(self, context):
        osc = context.scene.jerryst.bone_oscillations
        self.layout.prop(osc, "enabled", text="")

    def draw(self, context):
        layout = self.layout
        st  = context.scene.jerryst
        osc = st.bone_oscillations

        layout.active = osc.enabled

        # LISTA DE OSCILACIONES EXISTENTES
        box_list = layout.box()
        box_list.label(text="Lista de oscilaciones:", icon="NLA")

        if osc.items:
            for i, item in enumerate(osc.items):
                is_selected = (i == osc.active_idx)
                row_item = box_list.row(align=True)

                icon_sel = "RADIOBUT_ON" if is_selected else "RADIOBUT_OFF"
                op_sel = row_item.operator("jerryst.bone_osc_toggle_item", text="", icon=icon_sel, emboss=False)
                op_sel.item_idx = i

                icon_en = "HIDE_OFF" if item.enabled else "HIDE_ON"
                op_en = row_item.operator("jerryst.bone_osc_toggle_item", text="", icon=icon_en)
                op_en.item_idx = i

                wave_icon = {"SINE": "MOD_WAVE", "TRIANGLE": "GRAPH",
                             "SQUARE": "SNAP_INCREMENT", "NOISE": "MOD_NOISE"}.get(item.wave_type, "MOD_WAVE")
                axes_str = "".join(a for a, b in [("X", item.axis_x), ("Y", item.axis_y), ("Z", item.axis_z)] if b) or "?"
                label_text = (
                    f"  {item.label or item.bone_name}  [{item.bone_name}]  "
                    f"{axes_str}  \xb1{item.amplitude:.0f}\xb0  {item.frame_start}\u2192{item.frame_end}"
                )
                is_editing = (osc.edit_mode == "EDIT" and osc.edit_source_idx == i)
                row_item.label(text=label_text[:56], icon="GREASEPENCIL" if is_editing else wave_icon)

                op_edit = row_item.operator("jerryst.bone_osc_load_to_edit", text="", icon="GREASEPENCIL")
                op_edit.item_idx = i
                op_dup = row_item.operator("jerryst.bone_osc_duplicate_item", text="", icon="DUPLICATE")
                op_dup.item_idx = i
                op_del = row_item.operator("jerryst.bone_osc_remove_item", text="", icon="X")
                op_del.item_idx = i

            if len(osc.items) > 1:
                row_move = box_list.row(align=True)
                op_up = row_move.operator("jerryst.bone_osc_move_item", text="Subir",  icon="TRIA_UP")
                op_up.direction = "UP"
                op_dn = row_move.operator("jerryst.bone_osc_move_item", text="Bajar",  icon="TRIA_DOWN")
                op_dn.direction = "DOWN"
        else:
            box_list.label(text="  (sin oscilaciones -- agrega una abajo)", icon="INFO")

        layout.separator()

        # EDITOR DE OSCILACION (agregar o editar)
        box_edit = layout.box()
        is_edit_mode = (osc.edit_mode == "EDIT" and 0 <= osc.edit_source_idx < len(osc.items))
        if is_edit_mode:
            row_title = box_edit.row(align=True)
            row_title.label(text=f"Editando: {osc.items[osc.edit_source_idx].label}", icon="GREASEPENCIL")
            row_title.operator("jerryst.bone_osc_cancel_edit", text="", icon="X")
        else:
            box_edit.label(text="Nueva oscilacion:", icon="ADD")

        col = box_edit.column(align=True)
        col.prop(osc, "edit_label",     text="Etiqueta")
        col.prop(osc, "edit_bone_name", text="Bone")

        # BONES DETECTADOS: armature en escena > jerry.json > historia_jerry_*.json
        bones_json = _get_bones_from_historia(context)
        box_bones = box_edit.box()

        if bones_json:
            # Detectar fuente para mostrar en etiqueta
            try:
                import bpy as _bpy, os as _os
                arm_name = getattr(st, "armature_name", "Dog_001_rig")
                arm_obj = _bpy.data.objects.get(arm_name)
                if arm_obj and arm_obj.type == "ARMATURE" and arm_obj.data.bones:
                    src_label = f"Bones de {arm_name} (armature en escena):"
                else:
                    json_name = _os.path.basename(_bpy.path.abspath(st.historia_json))
                    src_label = f"Bones del personaje  ({json_name}):"
            except Exception:
                src_label = "Bones del personaje:"
            row_bh = box_bones.row()
            row_bh.label(text=src_label, icon="BONE_DATA")
            grid = box_bones.grid_flow(row_major=True, columns=3, align=True)
            for bone_name in bones_json:
                op_b = grid.operator("jerryst.bone_osc_pick_bone", text=bone_name, emboss=True)
                op_b.bone_name = bone_name
        else:
            box_bones.label(text="  Sin bones detectados", icon="ERROR")
            box_bones.label(text="  Abre el archivo jerry.json en Configuracion, o verifica el armature", icon="INFO")
            box_bones.label(text="  (tambien puedes escribir el nombre manualmente arriba)", icon="INFO")

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
        if osc.edit_wave_type in ("NOISE", "NOISE_DRIFT", "NOISE_LAYERED"):
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
        if is_edit_mode:
            row_add.operator("jerryst.bone_osc_save_edit", text="✔ Guardar cambios", icon="CHECKMARK")
        else:
            op_add = row_add.operator("jerryst.bone_osc_add_item", text="+ Agregar oscilacion", icon="CHECKMARK")
            op_add.quick_bone = ""

        layout.separator()
        layout.label(text="Las oscilaciones se aplican al presionar CONCATENAR (arriba)", icon="INFO")


# =============================================================================
# 4. PANEL EXPORTAR
# =============================================================================

class JRRST_PT_Export(Panel):
    bl_label       = "3  Exportar / Importar"
    bl_idname      = "JRRST_PT_export"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Jerry Studio"
    bl_parent_id   = "JRRST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}
    bl_order       = 7

    def draw(self, context):
        layout = self.layout
        st     = context.scene.jerryst
        segs   = context.scene.jerry_segments if hasattr(context.scene, "jerry_segments") else None
        pc     = context.scene.jerry_path     if hasattr(context.scene, "jerry_path")     else None

        # ── Identificacion del archivo ────────────────────────────────────────
        box = layout.box()
        box.label(text="Exportar slot_NNN_tipo.py", icon="EXPORT")
        col = box.column(align=True)
        col.prop(st, "export_slot_number", text="Numero de slot")
        col.prop(st, "export_type",        text="Tipo  (ej: patrullar)")
        col.prop(st, "export_desc",        text="Descripcion")

        sn = f"{st.export_slot_number:03d}"
        tp = st.export_type.strip() or "custom"
        filename_preview = f"slot_{sn}_{tp}.py"
        box_fname = box.box()
        box_fname.label(text=f"Archivo:  {filename_preview}", icon="FILE_SCRIPT")

        # ── Modo de exportacion ───────────────────────────────────────────────
        box_mode = layout.box()
        box_mode.label(text="Que exportar", icon="SETTINGS")
        col_m = box_mode.column(align=True)
        col_m.prop(st, "export_mode", text="")

        # Informacion contextual segun el modo
        mode = st.export_mode
        if segs and segs.segments:
            n_segs   = len(segs.segments)
            n_active = 1 if n_segs > 0 else 0
            n_sel    = sum(1 for s in segs.segments if getattr(s, "export_selected", False))

            if mode == "ACTIVE":
                if n_segs > 0:
                    idx     = max(0, min(segs.active_index, n_segs - 1))
                    seg_act = segs.segments[idx]
                    col_m.label(text=f"  Segmento: [{idx+1}] {seg_act.label}", icon="KEYFRAME")
                    col_m.label(text=f"  Frames: {seg_act.frame_start} → {seg_act.frame_end}", icon="TIME")
                else:
                    col_m.label(text="  Sin segmentos", icon="ERROR")

            elif mode == "SELECTED":
                if n_sel == 0:
                    col_m.label(text="  Ninguno marcado — marca con  ✓  abajo", icon="ERROR")
                else:
                    col_m.label(text=f"  {n_sel} segmento(s) seleccionado(s)", icon="CHECKMARK")
                # Lista de segmentos con checkbox
                box_list = box_mode.box()
                for i, seg in enumerate(segs.segments):
                    row_s = box_list.row(align=True)
                    row_s.prop(seg, "export_selected", text="")
                    lbl = f"[{i+1}] {seg.label}  ({seg.frame_start}→{seg.frame_end})"
                    row_s.label(text=lbl, icon="KEYFRAME_HLT" if seg.export_selected else "KEYFRAME")

            elif mode == "ALL":
                col_m.label(text=f"  Se exportaran {n_segs} archivos .py", icon="NLA")
                col_m.label(text=f"  Numeracion: slots {st.export_slot_number} … {st.export_slot_number + n_segs - 1}", icon="INFO")

            elif mode == "FULL":
                fps_val = st.fps if st.fps > 0 else 24
                f_ini   = st.start_frame
                f_fin   = st.end_frame_gen
                dur_s   = round((f_fin - f_ini + 1) / fps_val, 3) if f_fin >= f_ini else 0
                col_m.label(text=f"  Frames: {f_ini} → {f_fin}  ({dur_s}s)", icon="RENDER_ANIMATION")
                col_m.label(text="  Un solo archivo con toda la timeline", icon="INFO")
        else:
            col_m.label(text="  Sin segmentos creados aun", icon="INFO")

        # ── Coordenadas del recorrido ─────────────────────────────────────────
        box_coords = layout.box()
        box_coords.label(text="Coordenadas del recorrido", icon="TRACKER")

        if pc is not None:
            pts    = list(pc.path_points)
            n_pts  = len(pts)
            if n_pts == 0:
                box_coords.label(text="  Sin recorrido definido", icon="ERROR")
            elif n_pts == 1:
                pt = pts[0]
                col_c = box_coords.column(align=True)
                col_c.label(text="  Modo: 1 coordenada (posicion fija)", icon="PINNED")
                col_c.label(
                    text=f"  X={pt.coords[0]:.3f}  Y={pt.coords[1]:.3f}  Z={pt.coords[2]:.3f}",
                    icon="OBJECT_ORIGIN"
                )
                if pt.texture:
                    col_c.label(text=f"  Textura: {pt.texture}", icon="TEXTURE")
            else:
                col_c = box_coords.column(align=True)
                col_c.label(text=f"  Modo: recorrido ({n_pts} puntos)", icon="CURVE_PATH")
                for i, pt in enumerate(pts):
                    col_c.label(
                        text=f"  [{i}] X={pt.coords[0]:.2f}  Y={pt.coords[1]:.2f}  Z={pt.coords[2]:.2f}"
                             + (f"  tex:{pt.texture}" if pt.texture else ""),
                        icon="LAYER_ACTIVE"
                    )
        else:
            box_coords.label(text="  Path recorder no disponible", icon="QUESTION")

        # ── Frames de la animacion ────────────────────────────────────────────
        box_frames = layout.box()
        box_frames.label(text="Frames de la animacion", icon="TIME")
        col_f = box_frames.column(align=True)
        if st.anim_generated and st.total_frames_gen > 0:
            fps_val = st.fps if st.fps > 0 else 24
            dur_s   = round(st.total_frames_gen / fps_val, 3)
            col_f.label(text=f"  Inicio: frame {st.start_frame}", icon="KEYFRAME")
            col_f.label(text=f"  Fin:    frame {st.end_frame_gen}", icon="KEYFRAME_HLT")
            col_f.label(text=f"  Total:  {st.total_frames_gen} frames  ({dur_s}s @ {fps_val}fps)", icon="NLA")
        else:
            col_f.label(text="  Sin animacion generada", icon="ERROR")

        # ── Armatures ────────────────────────────────────────────────────────
        box_arm = layout.box()
        box_arm.label(text="Armatures del personaje", icon="ARMATURE_DATA")
        arm_main = context.scene.objects.get(st.armature_name)
        if arm_main and arm_main.type == "ARMATURE":
            box_arm.label(text=f"  Principal: {st.armature_name}  ({len(arm_main.pose.bones)} bones)", icon="BONE_DATA")
        else:
            box_arm.label(text=f"  {st.armature_name} no encontrado", icon="ERROR")
        for sec_name in ["tail_1", "tail_2"]:
            sec_obj = context.scene.objects.get(sec_name)
            if sec_obj:
                box_arm.label(text=f"  {sec_name}  ({len(sec_obj.pose.bones)} bone)", icon="BONE_DATA")
            else:
                box_arm.label(text=f"  {sec_name}: no encontrado", icon="QUESTION")

        # ── Carpeta de destino ────────────────────────────────────────────────
        box_dir = layout.box()
        box_dir.label(text="Carpeta de destino", icon="FILEBROWSER")
        box_dir.prop(st, "anim_dir", text="")
        if st.anim_dir:
            box_dir.label(
                text=f"  .../{os.path.basename(bpy.path.abspath(st.anim_dir))}/{filename_preview}",
                icon="FILE_FOLDER"
            )

        layout.separator(factor=0.5)

        # ── Boton exportar ────────────────────────────────────────────────────
        box_btn = layout.box()
        row_btn = box_btn.row()
        row_btn.scale_y = 2.0
        can_export = st.anim_generated
        # En modo SELECTED exigir al menos 1 marcado
        if mode == "SELECTED" and segs:
            n_sel = sum(1 for s in segs.segments if getattr(s, "export_selected", False))
            can_export = can_export and (n_sel > 0)
        row_btn.enabled = can_export
        row_btn.operator(
            "jerryst.export_animation",
            text=f"EXPORTAR  {filename_preview}",
            icon="FILE_SCRIPT"
        )
        if not st.anim_generated:
            box_btn.label(text="  Genera la animacion primero", icon="ERROR")
        elif mode == "SELECTED" and segs:
            n_sel = sum(1 for s in segs.segments if getattr(s, "export_selected", False))
            if n_sel == 0:
                box_btn.label(text="  Marca al menos un segmento para exportar", icon="ERROR")

        # ── Boton exportar MODO 1 COORDENADA ─────────────────────────────────
        # Solo visible cuando el path recorder tiene exactamente 1 punto.
        if pc is not None and len(list(pc.path_points)) == 1:
            box_1c = layout.box()
            box_1c.label(text="Exportar — 1 coordenada (parado / idle)", icon="PINNED")
            box_1c.label(
                text="  Captura bones con NLA activos: incluye rotaciones,",
                icon="INFO")
            box_1c.label(
                text="  filtros y efectos organicos del segmento.",
                icon="BLANK1")
            row_1c = box_1c.row()
            row_1c.scale_y = 1.8
            row_1c.enabled = st.anim_generated
            row_1c.operator(
                "jerryst.export_animation_single_coord",
                text=f"EXPORTAR  {filename_preview}  [1 coord]",
                icon="PINNED"
            )
            if not st.anim_generated:
                box_1c.label(text="  Genera la animacion primero", icon="ERROR")
        if st.last_export_path:
            box_btn.label(text=f"  OK: {os.path.basename(st.last_export_path)}", icon="CHECKMARK")

        layout.separator()

        # ── Importar ──────────────────────────────────────────────────────────
        box_imp = layout.box()
        box_imp.label(text="Importar animacion .py", icon="IMPORT")
        row_imp = box_imp.row()
        row_imp.scale_y = 1.4
        row_imp.operator("jerryst.import_animation", text="Seleccionar .py...", icon="FILE_FOLDER")

# =============================================================================
# 5. PANEL CONFIG SESSION
# =============================================================================

class JRRST_PT_ConfigSession(Panel):
    bl_label       = "4  Configuracion de sesion"
    bl_idname      = "JRRST_PT_configsession"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Jerry Studio"
    bl_parent_id   = "JRRST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}
    bl_order       = 8

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout
        st     = context.scene.jerryst

        box = layout.box()
        box.label(text="Guardar / Cargar configuracion", icon="FILE")
        box.prop(st, "config_dir",  text="Carpeta")
        box.prop(st, "config_name", text="Nombre")

        # Vista previa del archivo que se guardara
        raw = st.config_name.strip() or "config_jerry"
        while raw.lower().endswith(".json"):
            raw = raw[:-5]
        box.label(text=f"  Archivo: {raw}.json", icon="FILE_SCRIPT")

        row = box.row(align=True)
        row.scale_y = 1.3
        row.operator("jerryst.save_config",        text="Guardar", icon="FILE_TICK")
        row.operator("jerryst.load_config",        text="Cargar",  icon="FILEBROWSER")
        row.operator("jerryst.open_config_folder", text="",        icon="FILE_FOLDER")

# =============================================================================
# 6. PANEL EXTRACT POSE
# =============================================================================

class JRRST_PT_Extract(Panel):
    bl_label       = "5  Extraer pose"
    bl_idname      = "JRRST_PT_extract"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Jerry Studio"
    bl_parent_id   = "JRRST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}
    bl_order       = 6

    def draw(self, context):
        layout = self.layout
        st     = context.scene.jerryst

        box = layout.box()
        box.label(text="Extrae la pose actual del armature", icon="POSE_HLT")

        # ── Nombre de la pose (OBLIGATORIO para que el operador funcione) ──
        col = box.column(align=True)
        col.prop(st, "extract_label", text="Nombre de la pose")

        # ── Frame a extraer ───────────────────────────────────────────────
        row_f = box.row(align=True)
        row_f.prop(st, "extract_use_current", text="Frame actual", toggle=True)
        sub = row_f.row(align=True)
        sub.enabled = not st.extract_use_current
        sub.prop(st, "extract_frame", text="Frame")

        # ── Carpeta destino ───────────────────────────────────────────────
        box.prop(st, "poses_dir", text="Carpeta destino")

        # ── Aviso si falta el nombre ──────────────────────────────────────
        if not st.extract_label.strip():
            box.label(text="  Escribe un nombre para la pose", icon="ERROR")

        # ── Boton de exportar (deshabilitado si no hay nombre) ────────────
        row_btn = box.row()
        row_btn.scale_y = 1.5
        row_btn.enabled = bool(st.extract_label.strip())
        row_btn.operator("jerryst.extract_pose", text="Extraer y guardar pose", icon="EXPORT")

# =============================================================================
# 0. PANEL PATH RECORDER — Trazado de recorrido + Generacion de slots
# =============================================================================

class JRRST_PT_PathRecorder(Panel):
    bl_label       = "0  Recorrido y Slots"
    bl_idname      = "JRRST_PT_pathrecorder"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Jerry Studio"
    bl_parent_id   = "JRRST_PT_main"
    bl_order       = 0

    def draw(self, context):
        layout = self.layout
        pc     = context.scene.jerry_path

        # ── PASO 1: Grabar recorrido ──────────────────────────────────────
        box1 = layout.box()
        row_title = box1.row()
        row_title.label(text="PASO 1 — Trazar recorrido", icon="TRACKING")

        # Selector del archivo .blend del personaje
        box_blend = box1.box()
        box_blend.label(text="Personaje (.blend):", icon="ARMATURE_DATA")
        row_blend = box_blend.row(align=True)
        row_blend.prop(pc, "blend_filepath", text="")
        row_blend.operator("jerrypr.open_blend_file", text="", icon="FILE_FOLDER")
        if pc.blend_filepath:
            import os as _os
            blend_name = _os.path.basename(bpy.path.abspath(pc.blend_filepath))
            box_blend.label(text=f"  {blend_name}", icon="CHECKMARK" if blend_name.endswith(".blend") else "ERROR")

        box1.separator(factor=0.3)

        n_pts = len(pc.path_points)

        if pc.recording_active:
            row_rec = box1.row()
            row_rec.alert = True
            row_rec.label(text="● GRABANDO — selecciona faces en EDIT MODE", icon="REC")
            box1.operator("jerrypr.toggle_recording", text="Detener grabacion", icon="PAUSE")
        else:
            box1.operator("jerrypr.toggle_recording",
                          text="Iniciar grabacion de recorrido", icon="REC")

        row_count = box1.row()
        row_count.label(text=f"Puntos registrados: {n_pts}", icon="SNAP_FACE")

        # Lista de coordenadas seleccionadas (EDITABLE) — dropdown Caminar/Parada
        # portado de Alfred (2026-08-06): la lista ahora se dibuja COMPLETA
        # (con encabezado colegible/colapsable, pc.show_coords_list), igual
        # que en alfred_animation_studio. Antes solo se mostraban los
        # ultimos 5 puntos (englobando/resumiendo el resto), lo que impedia
        # elegir cualquier coordenada especifica de todo el recorrido como
        # 'Parada'. Cada punto tiene un tipo_segmento editable que por
        # defecto es AUTO (caminar/salto segun geometria) y que se puede
        # cambiar a PARADA para forzar un tramo de root inmovil.
        if n_pts > 0:
            from .path_recorder import _detect_move

            box_lista = box1.box()
            header_row = box_lista.row(align=True)
            header_row.prop(
                pc, "show_coords_list",
                icon="TRIA_DOWN" if pc.show_coords_list else "TRIA_RIGHT",
                text=f"Coordenadas seleccionadas  ({n_pts})",
                emboss=False,
            )

            if pc.show_coords_list:
                n_marcadas = sum(1 for pt in pc.path_points if pt.tipo_segmento == "PARADA")
                n_observar = sum(1 for pt in pc.path_points if pt.tipo_segmento == "OBSERVAR")
                info_row = box_lista.row()
                if n_marcadas == 0 and n_observar == 0:
                    info_row.label(
                        text="Todos en 'Caminar': el recorrido sera solo caminata/saltos",
                        icon="INFO",
                    )
                else:
                    if n_marcadas:
                        info_row.label(
                            text=f"{n_marcadas} punto(s) marcado(s) como 'Parada'",
                            icon="PAUSE",
                        )
                    if n_observar:
                        info_row = box_lista.row()
                        info_row.label(
                            text=f"{n_observar} punto(s) marcado(s) como 'Observar'",
                            icon="HIDE_OFF",
                        )

                pts_list = list(pc.path_points)
                col_pts = box_lista.column(align=False)
                for i, pt in enumerate(pts_list):
                    row_pt = col_pts.row(align=True)
                    row_pt.label(text=f"#{i+1}", icon="LAYER_USED")
                    row_pt.label(text=f"({pt.coords[0]:.2f}, {pt.coords[1]:.2f}, {pt.coords[2]:.2f})")

                    # NUEVO (Kebyn, portado de Alfred): badge "punto de
                    # encuentro" -- se muestra en CUALQUIER punto cuya
                    # coordenada coincida con una del recorrido de
                    # Alfred, independientemente del tipo_segmento
                    # actual, para que el usuario vea donde puede
                    # activar 'Interactuar' (ver _point_is_meeting_point()
                    # en path_recorder.py).
                    from .path_recorder import _point_is_meeting_point
                    if _point_is_meeting_point(context, pt):
                        row_pt.label(text="", icon="LINKED")

                    # El dropdown Caminar/Parada SOLO se muestra editable en tramos
                    # donde la geometria real (Z entre este punto y el siguiente)
                    # da "caminar" -- las coordenadas de saltar_subir/saltar_bajar
                    # no se pueden alterar, se muestran fijas sin dropdown.
                    if i < len(pts_list) - 1:
                        real_move = _detect_move(pt, pts_list[i + 1])
                        if real_move in ("caminar", "saltar_horizontal") or pt.tipo_segmento == "SALTAR":
                            row_pt.prop(pt, "tipo_segmento", text="")
                            if pt.tipo_segmento == 'SALTAR':
                                col_pts.label(text=f"Salto: punto {i+1} a {i+2}", icon='IPO_QUAD')
                            if pt.tipo_segmento == "PARADA":
                                row_pt.prop(pt, "parada_frames_punto", text="Frames")
                                _draw_parada_anim_row_jerry(col_pts, pt, i)
                                _draw_parada_rot_row_jerry(col_pts, pt, i)
                            elif pt.tipo_segmento == "OBSERVAR":
                                # Observar: mismos Frames y orientacion que Parada,
                                # sin animacion .py importada (ver observar_motion.py)
                                row_pt.prop(pt, "parada_frames_punto", text="Frames")
                                _draw_parada_rot_row_jerry(col_pts, pt, i)
                            elif pt.tipo_segmento == "INTERACTUAR":
                                _draw_interaccion_row_jerry(col_pts, pt, i)
                        elif real_move == "saltar_subir":
                            row_pt.label(text="subir", icon="TRIA_UP")
                        else:
                            row_pt.label(text="bajar", icon="TRIA_DOWN")
                    else:
                        # Ultimo punto: destino final, sin tramo de salto asociado
                        # -- se puede marcar como parada igual.
                        row_pt.prop(pt, "tipo_segmento", text="")
                        if pt.tipo_segmento == "PARADA":
                            row_pt.prop(pt, "parada_frames_punto", text="Frames")
                            _draw_parada_anim_row_jerry(col_pts, pt, i)
                            _draw_parada_rot_row_jerry(col_pts, pt, i)
                        elif pt.tipo_segmento == "OBSERVAR":
                            row_pt.prop(pt, "parada_frames_punto", text="Frames")
                            _draw_parada_rot_row_jerry(col_pts, pt, i)
                        elif pt.tipo_segmento == "INTERACTUAR":
                            _draw_interaccion_row_jerry(col_pts, pt, i)
                        row_pt.label(text="(final)", icon="KEYFRAME")

                    if pt.texture:
                        col_pts.label(text=f"     Textura: {pt.texture}", icon="TEXTURE")

                    col_pts.separator(factor=0.3)

            # Deteccion de segmentos rapida (incluye paradas marcadas)
            from .path_recorder import _expand_points_with_paradas, _group_segments as _grp_seg_quick
            expanded_quick, _, _, _ = _expand_points_with_paradas(pts_list)
            segs_quick = _grp_seg_quick(expanded_quick)
            segs_info = []
            _label_map = {"caminar": "→ caminar", "saltar_subir": "↑ saltar_subir",
                          "saltar_bajar": "↓ saltar_bajar", "parada": "⏸ parada"}
            for _s in segs_quick:
                seg_type = _label_map.get(_s["type"], _s["type"])
                # Observar es una parada cuyo punto real esta marcado 'OBSERVAR'
                if (_s["type"] == "parada"
                        and getattr(_s["points"][0], "tipo_segmento", "AUTO") == "OBSERVAR"):
                    seg_type = "● observar"
                if segs_info and segs_info[-1][0] == seg_type:
                    segs_info[-1] = (seg_type, segs_info[-1][1] + 1)
                else:
                    segs_info.append((seg_type, 1))

            if segs_info:
                box1.separator(factor=0.5)
                box1.label(text="Segmentos detectados:", icon="LINENUMBERS_ON")
                col_seg = box1.column(align=True)
                col_seg.scale_y = 0.8
                for seg_type, count in segs_info:
                    col_seg.label(text=f"    {seg_type}  ×{count}")

        row_btns = box1.row(align=True)
        row_btns.operator("jerrypr.remove_last", text="Quitar ultimo", icon="REMOVE")
        row_btns.operator("jerrypr.clear_path",  text="Limpiar todo",  icon="TRASH")

        layout.separator(factor=0.8)

        # ── PASO 2: Configurar generacion de slots ────────────────────────
        box2 = layout.box()
        box2.label(text="PASO 2 — Configuracion de slots", icon="SETTINGS")

        if n_pts == 0:
            box2.label(text="  Traza el recorrido primero", icon="ERROR")
        else:
            col_cfg = box2.column(align=True)
            col_cfg.prop(pc, "slot_inicio",         text="Primer slot #")
            col_cfg.prop(pc, "frame_inicio",         text="Frame inicial")

            # ── Modo 1 coordenada: sin recorrido, el usuario define frame final ──
            if n_pts == 1:
                col_cfg.separator(factor=0.5)
                box_1pt = box2.box()
                box_1pt.label(text="Modo: 1 coordenada (parado)", icon="PINNED")
                box_1pt.label(text="  Define el intervalo de frames manualmente:", icon="INFO")
                box_1pt.prop(pc, "frame_fin_manual", text="Frame final")
                _dur_manual = max(1, pc.frame_fin_manual - pc.frame_inicio + 1)
                _dur_s = round(_dur_manual / 24, 2)
                box_1pt.label(text=f"  Duracion: {_dur_manual} frames  ({_dur_s}s @ 24fps)", icon="TIME")
            else:
                col_cfg.prop(pc, "frames_por_bloque", text="Frames/bloque (caminar)")
                col_cfg.prop(pc, "frames_parada", text="Frames por parada (default)")

                # NUEVO (portado de Alfred, transiciones entre tramos,
                # Kebyn 2026-09-14): solo tiene sentido ofrecer esto si
                # el recorrido tiene AL MENOS dos tipos de tramo
                # distintos consecutivos -- con un recorrido 100%
                # "Caminar" no hay ningun corte que suavizar.
                from .path_recorder import _detect_move as _detect_move_ui
                _tipos_tramos_ui = []
                _pts_para_tipos_ui = list(pc.path_points)
                for _i in range(len(_pts_para_tipos_ui) - 1):
                    _tipos_tramos_ui.append(
                        _detect_move_ui(_pts_para_tipos_ui[_i], _pts_para_tipos_ui[_i + 1]))
                _hay_tramos_distintos_ui = any(
                    _tipos_tramos_ui[_i] != _tipos_tramos_ui[_i + 1]
                    for _i in range(len(_tipos_tramos_ui) - 1)
                )
                if _hay_tramos_distintos_ui:
                    box_trans_jrr = col_cfg.box()
                    row_trans_jrr = box_trans_jrr.row()
                    row_trans_jrr.prop(pc, "usar_transiciones", icon="IPO_EASE_IN_OUT")
                    if pc.usar_transiciones:
                        row_trans_jrr.prop(pc, "frames_transicion", text="Frames")

            box2.separator(factor=0.5)
            box2.label(text="Orientacion inicial del root (grados):")
            row_rot = box2.row(align=True)
            row_rot.prop(pc, "root_rot_x", text="X")
            row_rot.prop(pc, "root_rot_y", text="Y")
            row_rot.prop(pc, "root_rot_z", text="Z")

            box2.separator(factor=0.5)
            box2.label(text="Salida:", icon="FILE_FOLDER")
            box2.prop(pc, "output_dir", text="")

            # Estimacion de frames + duracion total
            # ACTUALIZADO (portado de Alfred, 2026-08-05): usa
            # _expand_points_with_paradas() + _group_segments() (misma logica
            # que GENERAR SLOTS / Exportar) en vez del calculo geometrico
            # manual anterior, para que la estimacion refleje las paradas
            # marcadas en la lista de arriba.
            if n_pts > 1:
                from .path_recorder import _expand_points_with_paradas as _exp_pp
                from .path_recorder import _group_segments as _grp_seg
                from .path_recorder import sync_paradas_frames as _sync_pf

                pts_list = list(pc.path_points)
                expanded_est, frames_paradas_est, _anim_files_est, _rot_est = _exp_pp(pts_list)
                segs_est = _grp_seg(expanded_est)

                n_paradas_actual = sum(1 for s in segs_est if s["type"] == "parada")
                if len(pc.paradas_frames) != n_paradas_actual:
                    row_sync = box2.row()
                    row_sync.alert = True
                    row_sync.operator(
                        "jerrypr.sync_paradas_frames",
                        text=f"Sincronizar frames por parada ({n_paradas_actual} detectada(s))",
                        icon="FILE_REFRESH",
                    )

                box2.separator(factor=0.5)
                col_est = box2.column(align=True)
                col_est.scale_y = 0.8
                col_est.label(text="Estimacion de slots:", icon="INFO")
                total_frames_est = 0
                parada_idx_est = 0
                caminar_idx_est = 0
                from .generate_slots_jerry import (
                    WALK_STYLE_PARAMS as _WSP_ui,
                    SALTAR_SUBIR_FRAMES as _SSF_ui,
                    SALTAR_BAJAR_FRAMES as _SBF_ui,
                )
                for seg_idx, seg in enumerate(segs_est, start=1):
                    slot_n = pc.slot_inicio + seg_idx - 1
                    if seg['type'] in ('saltar_subir','saltar_bajar','saltar_horizontal'):
                        from .jump_motion import jump_frame_count
                        jump_frames=jump_frame_count(tuple(seg['points'][0].coords),tuple(seg['points'][-1].coords),
                            seg['type'].removeprefix('saltar_'),context.scene.render.fps/context.scene.render.fps_base)
                        col_est.label(text=f"  Slot {slot_n}: {seg['type']} ({jump_frames} f)")
                        total_frames_est+=jump_frames
                    elif seg["type"] == "parada":
                        if parada_idx_est < len(frames_paradas_est):
                            f_parada = frames_paradas_est[parada_idx_est]
                        elif parada_idx_est < len(pc.paradas_frames):
                            f_parada = pc.paradas_frames[parada_idx_est].frames
                        else:
                            f_parada = pc.frames_parada
                        _lbl_parada = (
                            "observar"
                            if getattr(seg["points"][0], "tipo_segmento", "AUTO") == "OBSERVAR"
                            else "parada")
                        col_est.label(text=f"  Slot {slot_n}: {_lbl_parada} (~{f_parada} f)")
                        total_frames_est += f_parada
                        parada_idx_est += 1
                    else:  # caminar
                        # NUEVO (portado de Alfred, Kebyn 2026-08-05): cada
                        # tramo 'caminar' elige su propio ESTILO DE CAMINATA
                        # (Normal/Lento/Herido/Rapido/Correr) con un dropdown
                        # inline, que ademas escala la duracion estimada del
                        # slot (speed_mult del estilo).
                        import math as _m
                        seg_pts = seg["points"]
                        d = sum(
                            _m.sqrt(
                                (seg_pts[k+1].coords[0]-seg_pts[k].coords[0])**2 +
                                (seg_pts[k+1].coords[1]-seg_pts[k].coords[1])**2
                            ) for k in range(len(seg_pts) - 1)
                        )
                        _walk_style_ui = (pc.walk_styles[caminar_idx_est].style
                                           if caminar_idx_est < len(pc.walk_styles) else pc.walk_style)
                        _style_ui = _WSP_ui.get(_walk_style_ui, _WSP_ui['NORMAL'])
                        est_f = max(24, round(d * pc.frames_por_bloque * _style_ui['speed_mult']))
                        row_caminar = col_est.row(align=True)
                        row_caminar.label(text=f"  Slot {slot_n}: caminar (~{est_f} f, {len(seg_pts)-1} seg)")
                        if caminar_idx_est < len(pc.walk_styles):
                            row_caminar.prop(pc.walk_styles[caminar_idx_est], "style", text="")
                        total_frames_est += est_f
                        caminar_idx_est += 1

                # Boton de sincronizacion de estilos de caminata, solo si la
                # coleccion pc.walk_styles quedo desactualizada respecto de
                # la cantidad real de tramos 'caminar' detectados arriba.
                if caminar_idx_est != len(pc.walk_styles):
                    row_sync_ws = box2.row()
                    row_sync_ws.alert = True
                    row_sync_ws.operator(
                        "jerrypr.sync_paradas_frames",
                        text=f"Sincronizar estilos de caminata ({caminar_idx_est} tramo(s) detectado(s))",
                        icon="FILE_REFRESH",
                    )


                # Resumen de duracion total
                fps_val = 24  # FPS de referencia
                dur_s = round(total_frames_est / fps_val, 2)
                frame_fin = pc.frame_inicio + total_frames_est - 1
                box2.separator(factor=0.3)
                box_dur = box2.box()
                col_dur = box_dur.column(align=True)
                col_dur.scale_y = 0.9
                col_dur.label(text=f"  Duracion total del recorrido:", icon="TIME")
                col_dur.label(text=f"  {total_frames_est} frames  ({dur_s}s @ {fps_val}fps)", icon="NLA")
                col_dur.label(text=f"  Frame inicio: {pc.frame_inicio}  →  frame fin: {frame_fin}", icon="KEYFRAME")

            # Boton maestro: Reproducir recorrido
            # 1 coordenada: habilitar si frame_fin_manual > frame_inicio (para importar idle)
            # 2+ coordenadas: habilitar si frames_por_bloque > 0
            if n_pts == 1:
                paso2_listo = pc.frame_fin_manual > pc.frame_inicio
            else:
                paso2_listo = n_pts >= 2 and pc.frames_por_bloque > 0
            box2.separator(factor=0.5)
            row_play = box2.row()
            row_play.scale_y = 1.8
            row_play.enabled = paso2_listo
            if n_pts == 1:
                row_play.operator("jerrypr.preview_path",
                                  text="▶  Importar personaje (idle)",
                                  icon="PLAY")
            else:
                row_play.operator("jerrypr.preview_path",
                                  text="▶  Reproducir recorrido",
                                  icon="PLAY")
            if not paso2_listo and n_pts == 0:
                box2.label(text="  Completa el Paso 2 para reproducir", icon="INFO")

            # ── Exportar slot idle (opcional) — solo en modo 1 coordenada ────
            if n_pts == 1:
                box_exp1 = box2.box()
                box_exp1.label(text="Exportar slot idle (opcional):", icon="EXPORT")
                box_exp1.label(text="  Solo si deseas que el personaje quede parado sin poses avanzadas", icon="INFO")
                row_exp1 = box_exp1.row()
                row_exp1.scale_y = 1.4
                row_exp1.enabled = bool(pc.output_dir)
                row_exp1.operator("jerrypr.export_slots",
                                  text="Exportar slot parado (idle)",
                                  icon="SCRIPT")
                if not pc.output_dir:
                    box_exp1.label(text="  Define la carpeta de salida primero", icon="ERROR")
                # Rama "NO solo parado → continuar al Paso 3"
                box_exp1.separator(factor=0.3)
                box_exp1.label(
                    text="  ¿Quieres poses avanzadas? → Configura el PASO 3 abajo",
                    icon="TRIA_DOWN"
                )

            # ── Boton Exportar recorrido (slots) — opcional ───────────────
            if n_pts >= 2:
                box_exp = box2.box()
                box_exp.label(text="Exportar slots (opcional):", icon="EXPORT")
                box_exp.label(text="  Solo si deseas la animacion base sin poses avanzadas", icon="INFO")
                box_exp.label(text="  Genera .py de caminar/saltar por segmento", icon="INFO")
                row_exp = box_exp.row()
                row_exp.scale_y = 1.4
                row_exp.enabled = bool(pc.output_dir)
                row_exp.operator("jerrypr.export_slots",
                                 text="Exportar recorrido",
                                 icon="SCRIPT")
                if not pc.output_dir:
                    box_exp.label(text="  Define la carpeta de salida primero", icon="ERROR")
                # Rama "NO solo base → continuar al Paso 3"
                box_exp.separator(factor=0.3)
                box_exp.label(
                    text="  ¿Quieres poses avanzadas? → Configura el PASO 3 abajo",
                    icon="TRIA_DOWN"
                )

            # Boton Reset
            box2.separator(factor=0.3)
            row_rst = box2.row()
            row_rst.scale_y = 1.2
            row_rst.operator("jerrypr.reset_preview",
                             text="Reset recorrido",
                             icon="LOOP_BACK")

            # Boton Fijar rango — util cuando la animacion ya existe
            row_range = box2.row()
            row_range.scale_y = 1.1
            _anim_fin_actual = getattr(pc, "anim_frame_fin", 0)
            _range_label = (f"Rango fijado: {pc.frame_inicio}→{_anim_fin_actual}"
                            if _anim_fin_actual > 0
                            else "Fijar rango de animacion")
            row_range.operator("jerrypr.set_anim_range",
                               text=_range_label,
                               icon="PREVIEW_RANGE")

            layout.separator(factor=0.8)

            # ── PASO 3: Crear segmento ────────────────────────────────────
            segs = context.scene.jerry_segs

            # Detectar modo una sola vez aqui (n_pts ya calculado arriba en el panel)
            _modo_1coord = n_pts <= 1

            # ── Cabecera PASO 3 ───────────────────────────────────────────────
            box3 = layout.box()
            row_title3 = box3.row()
            row_title3.alert = True
            row_title3.label(text="PASO 3 — Crear segmento", icon="KEYFRAME")

            if _modo_1coord:
                # ══ MODO 1 COORDENADA ════════════════════════════════════════
                # El frame inicio proviene DIRECTAMENTE del Paso 1 (pc.frame_inicio).
                # No se pide frame fin: la duracion la determina la suma de poses.
                # ─────────────────────────────────────────────────────────────

                _fs_1c = pc.frame_inicio   # frame inicio tomado del Paso 1

                # Info compacta: frame inicio heredado del Paso 1
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
                    text="(suma de frames de las N poses/Acciones del segmento)",
                    icon="INFO"
                )

                box3.separator(factor=0.3)
                # Nombre del segmento
                box3.prop(segs, "edit_label", text="Nombre")

                # Boton CREAR SEGMENTO (sin validacion de frame fin)
                layout.separator(factor=0.5)
                row_crear = layout.row()
                row_crear.scale_y = 2.2
                row_crear.alert   = True
                row_crear.operator("jerryseg.add", text="+ CREAR SEGMENTO", icon="ADD")

            else:
                # ══ MODO RECORRIDO (2+ coordenadas) ══════════════════════════
                # Leer rango calculado por el Paso 2
                try:
                    _anim_f_inicio = pc.frame_inicio
                    _total_est     = getattr(pc, "anim_total_frames", 0)
                    _anim_f_fin    = getattr(pc, "anim_frame_fin", _anim_f_inicio + 1)
                    if _total_est == 0 and n_pts > 1:
                        import math as _math
                        _pts = list(pc.path_points)
                        _i = 0
                        while _i < len(_pts) - 1:
                            # FIX (portado de Alfred, Kebyn, 2026-08-19):
                            # redondeo a 4 decimales antes de comparar --
                            # mismo motivo que el fix de _detect_move() en
                            # path_recorder.py (ruido de punto flotante del
                            # raycast hacia que una diagonal de Z constante
                            # se contara como salto en esta estimacion).
                            _z0 = round(_pts[_i].coords[2], 4); _z1 = round(_pts[_i+1].coords[2], 4)
                            if _z1 > _z0:
                                _total_est += 48; _i += 1
                            elif _z1 < _z0:
                                _total_est += 42; _i += 1
                            else:
                                _j = _i + 1
                                while _j < len(_pts)-1 and round(_pts[_j].coords[2], 4) == round(_pts[_j+1].coords[2], 4):
                                    _j += 1
                                _d = sum(
                                    _math.sqrt(
                                        (_pts[_k+1].coords[0]-_pts[_k].coords[0])**2 +
                                        (_pts[_k+1].coords[1]-_pts[_k].coords[1])**2
                                    ) for _k in range(_i, _j)
                                )
                                _total_est += max(24, round(_d * pc.frames_por_bloque))
                                _i = _j
                        _anim_f_fin = (_anim_f_inicio + _total_est - 1
                                       if _total_est > 0 else _anim_f_inicio + 1)
                except Exception:
                    _anim_f_inicio = getattr(pc, "frame_inicio", 1)
                    _anim_f_fin    = _anim_f_inicio + 1
                    _total_est     = 0

                try:
                    _occupied = sorted(
                        [(s.frame_start, s.frame_end) for s in segs.segments if s.enabled],
                        key=lambda x: x[0]
                    )
                except Exception:
                    _occupied = []

                # Rango + ocupados + libres
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
                    "jerryseg.autosplit_from_config",
                    text="Dividir segmentos",
                    icon="MOD_ARRAY",
                )
                box3.label(
                    text="  Crea un segmento por cada tramo (caminar/salto/parada) detectado",
                    icon="INFO",
                )

                box3.separator(factor=0.3)
                # Nombre del segmento
                box3.prop(segs, "edit_label", text="Nombre")

                # Intervalo inicio → fin
                box_fr = box3.box()
                col_fr = box_fr.column(align=True)
                box_fr.label(text="Intervalo del segmento:", icon="KEYFRAME")

                _fs_edit = segs.edit_frame_start
                _fe_edit = segs.edit_frame_end
                _fs_ok   = False
                _fe_ok   = False
                _overlap = False

                if _total_est == 0:
                    col_fr.label(text="  Agrega al menos 2 puntos al recorrido", icon="INFO")
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

                # Boton CREAR SEGMENTO (modo recorrido)
                layout.separator(factor=0.5)
                _puede_crear = _fs_ok and _fe_ok and not _overlap and _total_est > 0
                row_crear = layout.row()
                row_crear.scale_y = 2.2
                row_crear.alert   = True
                row_crear.enabled = _puede_crear
                row_crear.operator("jerryseg.add", text="+ CREAR SEGMENTO", icon="ADD")
                if not _puede_crear and _total_est > 0:
                    layout.label(text="  Corrige los frames antes de crear", icon="ERROR")

            # ── Concatenar segmentos: ejecuta CONCATENAR de CADA segmento activo,
            #    respetando el rango de frames propio de cada uno, y reproduce
            #    todas las secuencias encadenadas de principio a fin ─────────
            layout.separator(factor=0.5)
            _n_enabled = sum(1 for s in segs.segments if s.enabled)
            row_concat = layout.row()
            row_concat.scale_y = 1.8
            row_concat.enabled = _n_enabled > 0
            row_concat.operator(
                "jerryseg.concatenate_all",
                text=f"▶ Concatenar segmentos ({_n_enabled})",
                icon="SEQUENCE",
            )
            if _n_enabled == 0:
                layout.label(text="  Activa al menos un segmento para concatenar", icon="INFO")

            # ── Lista acumulada de segmentos (ambos modos) ─────────────────────
            layout.separator(factor=0.5)
            box_list = layout.box()
            box_list.label(text="Segmentos creados:", icon="NLA")

            if segs.segments:
                for i, seg in enumerate(segs.segments):
                    box_seg = box_list.box()

                    # ── Cabecera: toggle enable + label + toggle config ────────
                    row_seg_hdr = box_seg.row(align=True)
                    icon_en = "HIDE_OFF" if seg.enabled else "HIDE_ON"
                    op_en = row_seg_hdr.operator("jerryseg.toggle_enabled", text="", icon=icon_en, emboss=False)
                    op_en.item_idx = i

                    # Calcular duracion en tiempo real desde las poses del segmento
                    _seg_total_fr, _seg_f_end = _calc_seg_frames(seg)

                    if seg.single_coord_mode:
                        # Mostrar duracion calculada desde poses (actualiza en tiempo real)
                        _fe_txt  = str(_seg_f_end)
                        _dur_txt = f"{_seg_total_fr}f"
                        row_seg_hdr.label(
                            text=(f"[{i+1}] {seg.label or 'Segmento'}  |  "
                                  f"inicio:{seg.frame_start}  fin:{_fe_txt}  [{_dur_txt}]"),
                            icon="PINNED"
                        )
                    else:
                        _dur_i = seg.frame_end - seg.frame_start
                        row_seg_hdr.label(
                            text=(f"[{i+1}] {seg.label or 'Segmento'}  |  "
                                  f"{seg.frame_start}→{seg.frame_end}  ({_dur_i}f)"),
                            icon="KEYFRAME"
                        )

                    # Botón de configuración (chevron)
                    _cfg_icon = "TRIA_DOWN" if seg.show_config else "TRIA_RIGHT"
                    op_cfg = row_seg_hdr.operator("jerryseg.toggle_config", text="", icon=_cfg_icon, emboss=False)
                    op_cfg.item_idx = i

                    # ── Controles: editar frames + duplicar + eliminar ────────
                    row_play = box_seg.row(align=True)
                    row_play.scale_y = 1.3

                    # Campos editables de rango de frames
                    row_play.prop(seg, "frame_start", text="Ini")
                    row_play.prop(seg, "frame_end",   text="Fin")

                    row_play.separator()
                    op_dup = row_play.operator("jerryseg.duplicate", text="", icon="DUPLICATE")
                    op_dup.item_idx = i
                    op_del = row_play.operator("jerryseg.remove",    text="", icon="X")
                    op_del.item_idx = i

                    # ── Barra de duracion calculada en tiempo real ────────────
                    _fps = getattr(context.scene.jerryst, "fps", 0) or context.scene.render.fps
                    _dur_s = round(_seg_total_fr / _fps, 2) if _fps > 0 else 0
                    _n_slots = len(seg.action_poses)
                    _dur_row = box_seg.row()
                    _dur_row.enabled = False   # solo lectura, visual
                    # NOTA (Kebyn, 2026-08-06): seg.pose_start_duration/
                    # pose_end_duration ya no existen -- el primer y ultimo
                    # item de action_poses son ahora las anclas de inicio/fin
                    # y su duracion ya esta incluida en la suma de _n_slots.
                    if _n_slots:
                        _dur_parts = (
                            f"{_n_slots} pose{'s' if _n_slots != 1 else ''}"
                            f"  =  {_seg_total_fr}f  ({_dur_s}s)"
                        )
                    else:
                        _dur_parts = "Sin poses configuradas"
                    _dur_row.label(text=_dur_parts, icon="TIME")

                    # ── CONFIGURACION EXPANDIDA (Imagen 2) ───────────────────
                    if seg.show_config:
                        box_cfg = box_seg.box()

                        # ── Titulo de seccion ─────────────────────────────────
                        row_cfg_title = box_cfg.row()
                        row_cfg_title.alert = False
                        row_cfg_title.label(
                            text=f"Configuracion del segmento [{i+1}]: {seg.label}",
                            icon="SETTINGS"
                        )

                        # ── Setup: Armature + Carpetas ────────────────────────
                        st = context.scene.jerryst
                        box_setup = box_cfg.box()
                        box_setup.label(text="Armature principal", icon="ARMATURE_DATA")
                        row_arm = box_setup.row(align=True)
                        row_arm.prop(st, "armature_name", text="")
                        row_arm.operator("jerryst.set_armature", text="", icon="EYEDROPPER")

                        box_dirs = box_cfg.box()
                        box_dirs.label(text="Carpetas", icon="FILE_FOLDER")
                        col_dirs = box_dirs.column(align=True)
                        col_dirs.prop(st, "poses_dir",  text="Poses")
                        col_dirs.prop(st, "anim_dir",   text="Animaciones")
                        col_dirs.prop(st, "config_dir", text="Configuraciones")
                        row_dirs = box_dirs.row(align=True)
                        row_dirs.operator("jerryst.open_poses_folder", text="Poses", icon="FILE_FOLDER")
                        row_dirs.operator("jerryst.open_anim_folder",  text="Anims", icon="FILE_FOLDER")
                        row_dirs.operator("jerryst.refresh_poses",     text="",      icon="FILE_REFRESH")
                        box_cfg.operator("jerryst.reset", text="Reset todo", icon="LOOP_BACK")

                        # ── CONCATENAR (dentro del segmento) ──────────────────
                        # ── Filtrar bones ─────────────────────────────────────
                        # Bones marcados aqui son excluidos del bake de CONCATENAR.
                        # Su animacion viene del recorrido base (Reproducir recorrido).
                        box_filt = box_cfg.box()
                        row_filt_hdr = box_filt.row()
                        row_filt_hdr.prop(
                            seg, "filter_show",
                            text="Filtrar bones",
                            icon="FILTER",
                            emboss=True,
                        )
                        if seg.filter_show:
                            box_filt.label(
                                text="Bones marcados NO reciben keyframes de configuracion:",
                                icon="INFO"
                            )
                            # ── Dog_001_rig (root) ──────────────────────────
                            col_f = box_filt.column(align=False)
                            col_f.label(text="Dog_001_rig", icon="ARMATURE_DATA")
                            col_main = box_filt.column(align=True)
                            _draw_bone_block_row(col_main, seg, i, "filter_main_bone")
                            # ── Columna vertebral ───────────────────────────
                            col_f.separator()
                            col_f.label(text="Columna vertebral", icon="ARMATURE_DATA")
                            col_sp = box_filt.column(align=True)
                            _draw_bone_block_row(col_sp, seg, i, "filter_body")
                            _draw_bone_block_row(col_sp, seg, i, "filter_spine_2")
                            _draw_bone_block_row(col_sp, seg, i, "filter_spine_3")
                            _draw_bone_block_row(col_sp, seg, i, "filter_spine_4")
                            _draw_bone_block_row(col_sp, seg, i, "filter_spine_5")
                            _draw_bone_block_row(col_sp, seg, i, "filter_spine_6")
                            _draw_bone_block_row(col_sp, seg, i, "filter_spine_7")
                            # ── Patas delanteras ────────────────────────────
                            col_f.separator()
                            col_f.label(text="Patas delanteras", icon="ARMATURE_DATA")
                            col_fa = box_filt.column(align=True)
                            _draw_bone_block_row(col_fa, seg, i, "filter_left_arm")
                            _draw_bone_block_row(col_fa, seg, i, "filter_right_arm")
                            _draw_bone_block_row(col_fa, seg, i, "filter_front_thigh_l")
                            _draw_bone_block_row(col_fa, seg, i, "filter_front_thigh_r")
                            _draw_bone_block_row(col_fa, seg, i, "filter_front_shin_l")
                            _draw_bone_block_row(col_fa, seg, i, "filter_front_shin_r")
                            _draw_bone_block_row(col_fa, seg, i, "filter_front_foot_l")
                            _draw_bone_block_row(col_fa, seg, i, "filter_front_foot_r")
                            _draw_bone_block_row(col_fa, seg, i, "filter_front_toe_l")
                            _draw_bone_block_row(col_fa, seg, i, "filter_front_toe_r")
                            # ── Patas traseras ──────────────────────────────
                            col_f.separator()
                            col_f.label(text="Patas traseras", icon="ARMATURE_DATA")
                            col_rl = box_filt.column(align=True)
                            _draw_bone_block_row(col_rl, seg, i, "filter_left_leg")
                            _draw_bone_block_row(col_rl, seg, i, "filter_right_leg")
                            _draw_bone_block_row(col_rl, seg, i, "filter_thigh_l")
                            _draw_bone_block_row(col_rl, seg, i, "filter_thigh_r")
                            _draw_bone_block_row(col_rl, seg, i, "filter_shin_l")
                            _draw_bone_block_row(col_rl, seg, i, "filter_shin_r")
                            _draw_bone_block_row(col_rl, seg, i, "filter_foot_l")
                            _draw_bone_block_row(col_rl, seg, i, "filter_foot_r")
                            _draw_bone_block_row(col_rl, seg, i, "filter_toe_l")
                            _draw_bone_block_row(col_rl, seg, i, "filter_toe_r")
                            # ── Cola ────────────────────────────────────────
                            col_f.separator()
                            col_f.label(text="Cola", icon="ARMATURE_DATA")
                            col_tl = box_filt.column(align=True)
                            _draw_bone_block_row(col_tl, seg, i, "filter_shield")
                            _draw_bone_block_row(col_tl, seg, i, "filter_spear")
                            _draw_bone_block_row(col_tl, seg, i, "filter_tail_3")
                            # ── Cabeza ──────────────────────────────────────
                            col_f.separator()
                            col_f.label(text="Cabeza", icon="ARMATURE_DATA")
                            col_hd = box_filt.column(align=True)
                            _draw_bone_block_row(col_hd, seg, i, "filter_scull")
                            _draw_bone_block_row(col_hd, seg, i, "filter_scull_1")
                            _draw_bone_block_row(col_hd, seg, i, "filter_jaw_bot")
                            _draw_bone_block_row(col_hd, seg, i, "filter_jaw_top")
                            _draw_bone_block_row(col_hd, seg, i, "filter_ear_l")
                            _draw_bone_block_row(col_hd, seg, i, "filter_ear_r")
                            _draw_bone_block_row(col_hd, seg, i, "filter_sombrero")
                            _draw_bone_block_row(col_hd, seg, i, "filter_sejas_1")
                            _draw_bone_block_row(col_hd, seg, i, "filter_sejas_2")
                            # ── Bones auxiliares ────────────────────────────
                            col_f.separator()
                            col_f.label(text="Bones auxiliares", icon="ARMATURE_DATA")
                            col_nb = box_filt.column(align=True)
                            _draw_bone_block_row(col_nb, seg, i, "filter_no_bone_01")
                            _draw_bone_block_row(col_nb, seg, i, "filter_no_bone_02")
                            _draw_bone_block_row(col_nb, seg, i, "filter_no_bone_03")
                            _draw_bone_block_row(col_nb, seg, i, "filter_no_bone_04")
                            # ── Resumen de bones filtrados ──────────────────
                            _filtered = [
                                n for prop, n in [
                                    ("filter_main_bone",    "Dog_001_rig"),
                                    ("filter_body",         "spine_1"),
                                    ("filter_spine_2",      "spine_2"),
                                    ("filter_spine_3",      "spine_3"),
                                    ("filter_spine_4",      "spine_4"),
                                    ("filter_spine_5",      "spine_5"),
                                    ("filter_spine_6",      "spine_6"),
                                    ("filter_spine_7",      "spine_7"),
                                    ("filter_left_arm",     "front_shoulder.L"),
                                    ("filter_right_arm",    "front_shoulder.R"),
                                    ("filter_front_thigh_l","front_thigh.L"),
                                    ("filter_front_thigh_r","front_thigh.R"),
                                    ("filter_front_shin_l", "front_shin.L"),
                                    ("filter_front_shin_r", "front_shin.R"),
                                    ("filter_front_foot_l", "front_foot.L"),
                                    ("filter_front_foot_r", "front_foot.R"),
                                    ("filter_front_toe_l",  "front_toe.L"),
                                    ("filter_front_toe_r",  "front_toe.R"),
                                    ("filter_left_leg",     "shoulder.L"),
                                    ("filter_right_leg",    "shoulder.R"),
                                    ("filter_thigh_l",      "thigh.L"),
                                    ("filter_thigh_r",      "thigh.R"),
                                    ("filter_shin_l",       "shin.L"),
                                    ("filter_shin_r",       "shin.R"),
                                    ("filter_foot_l",       "foot.L"),
                                    ("filter_foot_r",       "foot.R"),
                                    ("filter_toe_l",        "toe.L"),
                                    ("filter_toe_r",        "toe.R"),
                                    ("filter_shield",       "tail_1"),
                                    ("filter_spear",        "tail_2"),
                                    ("filter_tail_3",       "tail_3"),
                                    ("filter_scull",        "scull"),
                                    ("filter_scull_1",      "scull_1"),
                                    ("filter_jaw_bot",      "jaw_bot"),
                                    ("filter_jaw_top",      "jaw_top"),
                                    ("filter_ear_l",        "ear.L"),
                                    ("filter_ear_r",        "ear.R"),
                                    ("filter_sombrero",     "sombrero"),
                                    ("filter_sejas_1",      "sejas_1_jerry"),
                                    ("filter_sejas_2",      "sejas_2_jerry"),
                                    ("filter_no_bone_01",   "no_bone_01"),
                                    ("filter_no_bone_02",   "no_bone_02"),
                                    ("filter_no_bone_03",   "no_bone_03"),
                                    ("filter_no_bone_04",   "no_bone_04"),
                                ]
                                if getattr(seg, prop, False)
                            ]
                            if _filtered:
                                box_filt.label(
                                    text=f"Filtrados ({len(_filtered)}): " + ", ".join(_filtered),
                                    icon="CHECKMARK"
                                )
                            else:
                                box_filt.label(text="Ningun bone filtrado", icon="BLANK1")

                        # ── CONCATENAR ────────────────────────────────────────
                        box_conc_seg = box_cfg.box()
                        _seg_label = (
                            f"Segmento activo: {seg.label}  "
                            f"[{seg.frame_start}→"
                            f"{'?' if seg.single_coord_mode and seg.frame_end_auto <= seg.frame_start else seg.frame_end}]"
                        )
                        box_conc_seg.label(text=_seg_label, icon="SEQUENCE")
                        row_conc_seg = box_conc_seg.row()
                        row_conc_seg.scale_y = 2.0
                        _conc_text = "CONCATENAR" if n_pts <= 1 else "CONCATENAR  (inyectar poses → bones configurados)"
                        op_conc_seg = row_conc_seg.operator(
                            "jerryst.concatenate", text=_conc_text, icon="PLAY"
                        )
                        # FIX (Kebyn, 2026-08-12): pasar explicitamente el
                        # indice de ESTE segmento (i), en vez de depender de
                        # segs.active_index -- ver nota en JRRST_OT_Concatenate.
                        op_conc_seg.item_idx = i
                        if n_pts >= 2:
                            box_conc_seg.label(
                                text="Inyecta las poses configuradas sobre el desplazamiento del recorrido",
                                icon="INFO"
                            )
                            box_conc_seg.label(
                                text="Luego presiona REPRODUCIR para agregar caminar/saltar a los bones restantes",
                                icon="INFO"
                            )
                        else:
                            box_conc_seg.label(
                                text="Genera la animacion de poses dentro del segmento activo",
                                icon="INFO"
                            )

                        # ── Acciones (slots) ──────────────────────────────────
                        box_ac = box_cfg.box()
                        box_ac.label(text="Acciones (slots)", icon="NLA")
                        row_ac = box_ac.row()
                        row_ac.template_list(
                            "JRRST_UL_ActionPoses", f"seg_{i}",
                            seg, "action_poses",
                            seg, "action_poses_idx",
                            rows=4,
                        )
                        col_ac = row_ac.column(align=True)
                        op_add = col_ac.operator("jerryseg.add_action_pose_seg",    text="", icon="ADD")
                        op_add.item_idx = i
                        op_rem = col_ac.operator("jerryseg.remove_action_pose_seg", text="", icon="REMOVE")
                        op_rem.item_idx = i
                        col_ac.separator()
                        op_up = col_ac.operator("jerryseg.move_action_pose_seg",   text="", icon="TRIA_UP")
                        op_up.item_idx = i; op_up.direction = "UP"
                        op_dn = col_ac.operator("jerryseg.move_action_pose_seg",   text="", icon="TRIA_DOWN")
                        op_dn.item_idx = i; op_dn.direction = "DOWN"
                        col_ac.separator()
                        op_ed = col_ac.operator("jerryseg.edit_action_pose_seg",   text="", icon="GREASEPENCIL")
                        op_ed.item_idx = i
                        op_cp = col_ac.operator("jerryseg.duplicate_action_pose_seg", text="", icon="DUPLICATE")
                        op_cp.item_idx = i
                        if seg.action_poses:
                            slot = (seg.action_poses[seg.action_poses_idx]
                                    if seg.action_poses_idx < len(seg.action_poses) else None)
                            if slot:
                                box_slot = box_ac.box()
                                col_slot = box_slot.column(align=True)
                                col_slot.label(text=f"Slot activo: {slot.pose_name or slot.json_file or '-- vacio --'}")
                                if getattr(slot, "manual_start", False):
                                    col_slot.label(
                                        text=f"Frame de inicio manual: {slot.frame_abs_start}",
                                        icon="KEYFRAME_HLT",
                                    )
                                col_slot.prop(slot, "duration",     text="Frames")
                                col_slot.prop(slot, "interp_type",  text="Interpolacion")

                                # ── Editor de pose en vivo ──────────────────
                                row_edit = box_slot.row(align=True)
                                row_edit.operator("jerryst.enter_pose_edit_live",
                                                  text="Editar pose...", icon="POSE_HLT")
                                op_save = row_edit.operator("jerryst.save_pose_changes_live",
                                                            text="Guardar cambios", icon="FILE_TICK")
                                op_save.item_idx = i

                                # ── NOMBRE LEGIBLE desde jerry_pose_library.json ────
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
                                            box_slot.label(text=f"↳ {_nombre_leg}", icon="INFO")
                                        else:
                                            _partes = _nombre_leg.split(", ")
                                            _linea  = ""
                                            for _p in _partes:
                                                if len(_linea) + len(_p) + 2 <= _MAX:
                                                    _linea = _linea + (", " if _linea else "") + _p
                                                else:
                                                    box_slot.label(text=f"↳ {_linea}", icon="INFO")
                                                    _linea = _p
                                            if _linea:
                                                box_slot.label(text=f"  {_linea}", icon="BLANK1")
                                    except Exception:
                                        box_slot.label(text=f"↳ {str(_nombre_leg)[:60]}", icon="INFO")
                                # NOTA: NO mutar slot.rating_query aqui — mutar RNA en draw()
                                # hace que Blender aborte silenciosamente el resto del panel.

                        # ── EXTRAER POSE RAPIDA (bones del armature Jerry) ──────
                        # PORTADO desde alfred_animation_studio (Kebyn, 2026-09-04):
                        # debajo del sistema de agregar poses (mismo criterio que
                        # "Extraccion de pose" del Paso 1, pero automatico: detecta
                        # el armature/bones de Jerry solo, nombra la pose segun los
                        # huesos que se movieron, y con "Importar" la agrega directo
                        # a esta lista).
                        box_qp = box_ac.box()
                        row_qp_hdr = box_qp.row(align=True)
                        row_qp_hdr.label(text="Extraer pose rapida (bones actuales)", icon="BONE_DATA")
                        row_qp_btn = box_qp.row(align=True)
                        row_qp_btn.scale_y = 1.3
                        row_qp_btn.operator(
                            "jerryseg.quickpose_extract",
                            text="  Guardar pose (bones actuales)", icon="PINNED"
                        )
                        _st_qp = context.scene.jerryst
                        row_qp_imp = box_qp.row(align=True)
                        row_qp_imp.scale_y = 1.3
                        op_qp_imp = row_qp_imp.operator(
                            "jerryseg.quickpose_import",
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

                        # ── Parpadeo automatico (propio de este segmento) ───────
                        # PORTADO desde alfred_animation_studio (Kebyn, 2026-08-05):
                        # "un parpadeo por segmento". A diferencia de Alfred no se
                        # uso un template_list con UIList propia -- con 1-2
                        # intervalos tipicos por segmento alcanza con dibujar cada
                        # uno en su propia fila; menos codigo que mantener a
                        # cambio de una lista sin drag-to-reorder.
                        box_bl = box_cfg.box()
                        row_bl_hdr = box_bl.row()
                        row_bl_hdr.label(text="Parpadeo automatico (por segmento)", icon="HIDE_OFF")
                        op_bl_add = row_bl_hdr.operator("jerryseg.blink_interval_add_seg",
                                                        text="", icon="ADD")
                        op_bl_add.item_idx = i
                        if not seg.blink_intervals:
                            box_bl.label(text="  Sin parpadeo configurado en este segmento", icon="INFO")
                        for _bi_idx, _bi in enumerate(seg.blink_intervals):
                            box_bi = box_bl.box()
                            row_bi = box_bi.row(align=True)
                            row_bi.prop(_bi, "enabled", text="", icon="HIDE_OFF" if _bi.enabled else "HIDE_ON")
                            row_bi.prop(_bi, "label", text="")
                            op_bl_rem = row_bi.operator("jerryseg.blink_interval_remove_seg",
                                                        text="", icon="X")
                            op_bl_rem.item_idx = i
                            op_bl_rem.bi_idx   = _bi_idx
                            if _bi.enabled:
                                row_rng = box_bi.row(align=True)
                                row_rng.prop(_bi, "frame_start", text="Ini")
                                row_rng.prop(_bi, "frame_end",   text="Fin")
                                row_cnt = box_bi.row(align=True)
                                row_cnt.prop(_bi, "blink_count",    text="N. parpadeos")
                                row_cnt.prop(_bi, "blink_duration", text="Frames/parpadeo")

                        # ── Filtros Organicos ──────────────────────────────────
                        # AISLAMIENTO POR SEGMENTO (Kebyn + Claude, 2026-08-06):
                        # og apunta a la instancia PROPIA de este segmento
                        # (seg.organic), no a scene.jerryst.organic (global).
                        # Cada segmento guarda y reproduce sus propios valores
                        # -- ver JerryAnimSegment.organic en properties.py.
                        box_og = box_cfg.box()
                        og = seg.organic
                        row_og_hdr = box_og.row()
                        row_og_hdr.prop(og, "enabled", text="Filtros organicos")
                        if og.enabled:
                            # Respiracion
                            box_b = box_og.box()
                            box_b.prop(og, "breathing_enabled", text="Respiracion  (spine_4 / spine_5)")
                            if og.breathing_enabled:
                                col_b = box_b.column(align=True)
                                col_b.prop(og, "breathing_amplitude", text="Amplitud")
                                col_b.prop(og, "breathing_speed",     text="Velocidad")
                                col_b.prop(og, "breathing_phase",     text="Fase")
                            # Micro-movimiento cabeza
                            box_h = box_og.box()
                            box_h.prop(og, "head_sway_enabled", text="Micro-movimiento cabeza  (scull_1, scull)")
                            if og.head_sway_enabled:
                                col_h = box_h.column(align=True)
                                col_h.prop(og, "head_sway_amplitude", text="Amplitud")
                                col_h.prop(og, "head_sway_speed",     text="Velocidad")
                                col_h.prop(og, "head_sway_seed",      text="Semilla")
                            # Desplazamiento de peso
                            box_w = box_og.box()
                            box_w.prop(og, "weight_shift_enabled", text="Desplazamiento de peso  (spine_6)")
                            if og.weight_shift_enabled:
                                col_w = box_w.column(align=True)
                                col_w.prop(og, "weight_shift_amplitude", text="Amplitud")
                                col_w.prop(og, "weight_shift_speed",     text="Velocidad")
                            # Noise en ROOT
                            box_r = box_og.box()
                            box_r.prop(og, "root_noise_enabled", text="Noise en ROOT  (jerry Empty)")
                            if og.root_noise_enabled:
                                col_r = box_r.column(align=True)
                                col_r.prop(og, "root_noise_strength",  text="Intensidad")
                                col_r.prop(og, "root_noise_frequency", text="Frecuencia")
                                col_r.prop(og, "root_noise_seed",      text="Semilla")
                            # Secondary motion brazos
                            box_sec = box_og.box()
                            box_sec.prop(og, "secondary_motion_enabled", text="Secondary motion brazos  (front_thigh)")
                            if og.secondary_motion_enabled:
                                col_sec = box_sec.column(align=True)
                                col_sec.prop(og, "secondary_motion_lag",     text="Retardo (frames)")
                                col_sec.prop(og, "secondary_motion_damping", text="Amortiguacion")
                            # Suavizado de fcurves
                            box_sm = box_og.box()
                            box_sm.prop(og, "smooth_curves_enabled", text="Suavizar fcurves")
                            if og.smooth_curves_enabled:
                                col_sm = box_sm.column(align=True)
                                col_sm.prop(og, "smooth_passes", text="Pasadas")
                                col_sm.prop(og, "smooth_factor", text="Factor", slider=True)
                            # Cola
                            box_t = box_og.box()
                            box_t.prop(og, "tail_wag_enabled", text="Oscilacion cola  (tail_1 / tail_2 / tail_3)")
                            if og.tail_wag_enabled:
                                col_t = box_t.column(align=True)
                                col_t.prop(og, "tail_wag_amplitude", text="Amplitud (rad)")
                                col_t.prop(og, "tail_wag_speed",     text="Velocidad")
                                col_t.prop(og, "tail_wag_phase",     text="Fase")
                                col_t.prop(og, "tail_wag_lag",       text="Retardo entre bones", slider=True)

                        # ── Oscilacion de orejas ───────────────────────────────
                        box_ear = box_cfg.box()
                        box_ear.prop(og, "ear_osc_enabled", text="Oscilacion orejas  (ear.L / ear.R)")
                        if og.ear_osc_enabled:
                            _draw_ear_osc_list(box_ear, og, i)

                        # ── Oscilacion de mandibula ────────────────────────────
                        box_jaw = box_cfg.box()
                        box_jaw.prop(og, "jaw_osc_enabled", text="Oscilacion mandibula  (jaw_bot)")
                        if og.jaw_osc_enabled:
                            _draw_jaw_osc_list(box_jaw, og, i)

                        # ── Emociones de cejas ─────────────────────────────────
                        box_em = box_cfg.box()
                        box_em.prop(og, "emotion_enabled", text="Emociones  (sejas_1_jerry / sejas_2_jerry)")
                        if og.emotion_enabled:
                            _draw_emotion_list(box_em, og, i)

                        # ── Oscilaciones de Bones ──────────────────────────────
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
                                    _op_en = _row.operator("jerryst.bone_osc_toggle_item", text="", icon=_icon_en)
                                    _op_en.item_idx = _oi
                                    _axes = "".join(a for a, b in [("X", _oitem.axis_x),("Y", _oitem.axis_y),("Z", _oitem.axis_z)] if b) or "?"
                                    _is_editing = (osc.edit_mode == "EDIT" and osc.edit_source_idx == _oi)
                                    _row.label(text=f"  {_oitem.label or _oitem.bone_name}  [{_axes}]  \xb1{_oitem.amplitude:.0f}\xb0",
                                               icon="GREASEPENCIL" if _is_editing else "BLANK1")
                                    _op_edit = _row.operator("jerryst.bone_osc_load_to_edit", text="", icon="GREASEPENCIL")
                                    _op_edit.item_idx = _oi
                                    _op_del = _row.operator("jerryst.bone_osc_remove_item", text="", icon="X")
                                    _op_del.item_idx = _oi
                            else:
                                box_osc_list.label(text="  (sin oscilaciones)", icon="INFO")
                            # Editor nueva / editar oscilacion
                            box_osc_edit = box_osc.box()
                            _is_edit_mode = (osc.edit_mode == "EDIT" and 0 <= osc.edit_source_idx < len(osc.items))
                            if _is_edit_mode:
                                _row_t = box_osc_edit.row(align=True)
                                _row_t.label(text=f"Editando: {osc.items[osc.edit_source_idx].label}", icon="GREASEPENCIL")
                                _row_t.operator("jerryst.bone_osc_cancel_edit", text="", icon="X")
                            else:
                                box_osc_edit.label(text="Nueva oscilacion:", icon="ADD")
                            col_oe = box_osc_edit.column(align=True)
                            col_oe.prop(osc, "edit_label",     text="Etiqueta")
                            col_oe.prop(osc, "edit_bone_name", text="Bone")

                            # ── Grid de bones del personaje ───────────────
                            _bones_list = _get_bones_from_historia(context)
                            box_osc_bones = box_osc_edit.box()
                            if _bones_list:
                                try:
                                    import bpy as _bpy2
                                    _arm_name = getattr(st, "armature_name", "Dog_001_rig")
                                    _arm_obj  = _bpy2.data.objects.get(_arm_name)
                                    if _arm_obj and _arm_obj.type == "ARMATURE" and _arm_obj.data.bones:
                                        _src = f"Bones de {_arm_name}:"
                                    else:
                                        _src = "Bones del personaje:"
                                except Exception:
                                    _src = "Bones del personaje:"
                                box_osc_bones.label(text=_src, icon="BONE_DATA")
                                _grid = box_osc_bones.grid_flow(row_major=True, columns=3, align=True)
                                for _bname in _bones_list:
                                    _op_b = _grid.operator("jerryst.bone_osc_pick_bone", text=_bname, emboss=True)
                                    _op_b.bone_name = _bname
                            else:
                                box_osc_bones.label(text="  Sin bones — verifica el armature o configura el JSON", icon="ERROR")

                            row_of = box_osc_edit.row(align=True)
                            row_of.prop(osc, "edit_frame_start", text="Inicio")
                            row_of.prop(osc, "edit_frame_end",   text="Fin")
                            row_oa = box_osc_edit.row(align=True)
                            row_oa.label(text="Ejes:")
                            row_oa.prop(osc, "edit_axis_x", toggle=True)
                            row_oa.prop(osc, "edit_axis_y", toggle=True)
                            row_oa.prop(osc, "edit_axis_z", toggle=True)
                            col_oamp = box_osc_edit.column(align=True)
                            col_oamp.prop(osc, "edit_amplitude",    text="Amplitud (grad)")
                            col_oamp.prop(osc, "edit_num_cycles",   text="Ciclos")
                            col_oamp.prop(osc, "edit_wave_type",    text="Transicion")
                            row_oadd = box_osc_edit.row()
                            row_oadd.scale_y = 1.4
                            if _is_edit_mode:
                                row_oadd.operator("jerryst.bone_osc_save_edit", text="\u2714 Guardar cambios", icon="CHECKMARK")
                            else:
                                _op_oadd = row_oadd.operator("jerryst.bone_osc_add_item", text="+ Agregar oscilacion", icon="CHECKMARK")
                                _op_oadd.quick_bone = ""
                            box_osc.label(text="Las oscilaciones se aplican al CONCATENAR", icon="INFO")

                        # ── Importacion de Objetos (por segmento) ────────────────────────
                        try:
                            oi = context.scene.jerryst.object_imports
                            box_obj = box_cfg.box()
                            row_obj_hdr = box_obj.row(align=True)
                            row_obj_hdr.prop(oi, "enabled",
                                text="Importacion de Objetos (props, accesorios)", icon="IMPORT")

                            if oi.enabled:
                                # Lista de items de este segmento
                                seg_items = [item for item in oi.items
                                             if item.segment_idx == i or item.segment_idx == -1]
                                if seg_items:
                                    box_obj_list = box_obj.box()
                                    box_obj_list.label(text="Objetos de este segmento:", icon="OBJECT_DATA")
                                    for _gi, _gitem in enumerate(oi.items):
                                        if _gitem.segment_idx != i and _gitem.segment_idx != -1:
                                            continue
                                        row_gi = box_obj_list.row(align=True)
                                        _icon_gen = "HIDE_OFF" if _gitem.enabled else "HIDE_ON"
                                        _op_gen = row_gi.operator("jrst.obj_import_toggle_item",
                                                                   text="", icon=_icon_gen)
                                        _op_gen.item_idx = _gi
                                        row_gi.label(
                                            text=f"  {_gitem.label}  [{_gitem.object_name}]"
                                                 f"  {_gitem.frame_start}→{_gitem.frame_end}",
                                            icon="IMPORT")
                                        _op_gen_ed = row_gi.operator("jrst.obj_import_load_to_editor",
                                                                     text="", icon="GREASEPENCIL")
                                        _op_gen_ed.item_idx = _gi
                                        _op_gen_rm = row_gi.operator("jrst.obj_import_remove_item",
                                                                     text="", icon="X")
                                        _op_gen_rm.item_idx = _gi
                                else:
                                    box_obj.label(text="  (sin objetos para este segmento)", icon="INFO")

                                # Mini-editor para agregar nuevo objeto a este segmento
                                box_obj_edit = box_obj.box()
                                box_obj_edit.label(text="Nuevo objeto para este segmento:", icon="ADD")
                                row_obj_br = box_obj_edit.row(align=True)
                                row_obj_br.scale_y = 1.2
                                row_obj_br.operator("jrst.obj_import_browse_blend",
                                                    text="Buscar .blend...", icon="FILEBROWSER")
                                col_obj = box_obj_edit.column(align=True)
                                col_obj.prop(oi, "edit_object_folder",  text="Carpeta")
                                col_obj.prop(oi, "edit_blend_filename", text="Archivo .blend")
                                col_obj.prop(oi, "edit_object_name",    text="Nombre objeto")
                                row_of = box_obj_edit.row(align=True)
                                row_of.prop(oi, "edit_frame_start", text="Inicio")
                                row_of.prop(oi, "edit_frame_end",   text="Fin")
                                col_op = box_obj_edit.column(align=True)
                                col_op.label(text="Parenteo:", icon="BONE_DATA")
                                row_oa = col_op.row(align=True)
                                row_oa.prop(oi, "edit_parent_armature", text="Armature")
                                row_oa.operator("jrst.obj_import_detect_armature", text="", icon="VIEWZOOM")
                                col_op.prop(oi, "edit_parent_bone", text="Bone")
                                # Transiciones
                                if hasattr(oi, "edit_transition_in"):
                                    box_tr2 = box_obj_edit.box()
                                    box_tr2.label(text="Transiciones cartoon:", icon="ANIM")
                                    col_tin2 = box_tr2.column(align=True)
                                    col_tin2.label(text="Aparicion (frame inicio):", icon="KEYFRAME")
                                    row_tin2 = col_tin2.row(align=True)
                                    row_tin2.scale_y = 1.1
                                    row_tin2.prop(oi, "edit_transition_in", text="")
                                    if getattr(oi, "edit_transition_in", "NONE") != "NONE":
                                        col_tin2.prop(oi, "edit_transition_in_duration",
                                                      text="Duracion entrada (frames)")
                                    col_tout2 = box_tr2.column(align=True)
                                    col_tout2.label(text="Desaparicion (frame fin):", icon="KEYFRAME_HLT")
                                    row_tout2 = col_tout2.row(align=True)
                                    row_tout2.scale_y = 1.1
                                    row_tout2.prop(oi, "edit_transition_out", text="")
                                    if getattr(oi, "edit_transition_out", "NONE") != "NONE":
                                        col_tout2.prop(oi, "edit_transition_out_duration",
                                                       text="Duracion salida (frames)")
                                # Fijar segment_idx a este segmento
                                box_obj_edit.label(
                                    text=f"  Se asignara al segmento {i} (este segmento)",
                                    icon="INFO")
                                row_oadd2 = box_obj_edit.row()
                                row_oadd2.scale_y = 1.4
                                _op_oadd2 = row_oadd2.operator(
                                    "jrst.obj_import_add_item",
                                    text="+ Agregar objeto a este segmento", icon="CHECKMARK")
                                box_obj.label(text="Los objetos se incluyen en el .py al EXPORTAR",
                                              icon="INFO")
                        except Exception as _e_obj:
                            box_cfg.label(text=f"[Importacion de Objetos: {_e_obj}]", icon="ERROR")

                        # ── Lanzar / Recoger Objetos ──────────────────────────────────────
                        try:
                            th = seg.throws
                            box_th = box_cfg.box()

                            row_th_hdr = box_th.row(align=True)
                            row_th_hdr.prop(th, "enabled",
                                text="Lanzar / Recoger Objetos", icon="FORCE_WIND")

                            if th.enabled:
                                # ── Lista de items ────────────────────────────
                                for _ti, _titem in enumerate(th.items):
                                    box_ti = box_th.box()
                                    box_ti.active = _titem.enabled

                                    row_ti_hdr = box_ti.row(align=True)
                                    _icon_en = "HIDE_OFF" if _titem.enabled else "HIDE_ON"
                                    _op_tog = row_ti_hdr.operator(
                                        "jrst.throw_toggle_item", text="", icon=_icon_en)
                                    _op_tog.seg_idx = i; _op_tog.item_idx = _ti
                                    _mode_icon = "FORCE_WIND" if _titem.mode == 'THROW' else "IMPORT"
                                    row_ti_hdr.label(
                                        text=f"  {_titem.label}  [{_titem.object_name}]"
                                             f"  {_titem.frame_start}→{_titem.frame_end}",
                                        icon=_mode_icon)
                                    _op_ed = row_ti_hdr.operator(
                                        "jrst.throw_load_to_editor", text="", icon="GREASEPENCIL")
                                    _op_ed.seg_idx = i; _op_ed.item_idx = _ti
                                    _op_cl = row_ti_hdr.operator(
                                        "jrst.throw_clear_keyframes", text="", icon="TRASH")
                                    _op_cl.seg_idx = i; _op_cl.item_idx = _ti
                                    _op_rm = row_ti_hdr.operator(
                                        "jrst.throw_remove_item", text="", icon="X")
                                    _op_rm.seg_idx = i; _op_rm.item_idx = _ti

                                    if _titem.enabled and _titem.imported_object_name:
                                        box_ti.label(
                                            text=f"En escena: '{_titem.imported_object_name}'",
                                            icon="CHECKMARK")

                                    if _titem.enabled and _titem.waypoints:
                                        box_ti_wp = box_ti.box()
                                        box_ti_wp.label(
                                            text=f"Waypoints ({len(_titem.waypoints)}):",
                                            icon="IPO_BEZIER")
                                        for _wi, _wp in enumerate(_titem.waypoints):
                                            row_wp = box_ti_wp.row(align=True)
                                            row_wp.prop(_wp, "enabled", text="")
                                            row_wp.label(
                                                text=f"{_wp.label}  ({_wp.x:.2f},{_wp.y:.2f},{_wp.z:.2f})")
                                            row_wp.prop(_wp, "easing", text="")
                                            _op_wfc = row_wp.operator(
                                                "jrst.throw_wp_from_cursor", text="", icon="PIVOT_CURSOR")
                                            _op_wfc.seg_idx = i; _op_wfc.item_idx = _ti; _op_wfc.wp_idx = _wi
                                            _op_wrm = row_wp.operator(
                                                "jrst.throw_remove_waypoint", text="", icon="X")
                                            _op_wrm.seg_idx = i; _op_wrm.item_idx = _ti; _op_wrm.wp_idx = _wi

                                # ── Editor de nuevo / editar item ─────────────
                                box_edit = box_th.box()
                                box_edit.label(text="Nuevo lanzamiento / editar:", icon="ADD")

                                row_ed_mode = box_edit.row(align=True)
                                row_ed_mode.scale_y = 1.1
                                row_ed_mode.prop(th, "edit_mode", expand=True)

                                box_edit.prop(th, "edit_label", text="Etiqueta")

                                row_ed_br = box_edit.row(align=True)
                                row_ed_br.scale_y = 1.2
                                _op_br = row_ed_br.operator(
                                    "jrst.throw_browse_blend", text="Buscar .blend...", icon="FILEBROWSER")
                                _op_br.seg_idx = i
                                col_ed = box_edit.column(align=True)
                                col_ed.prop(th, "edit_object_name",   text="Nombre objeto")
                                col_ed.prop(th, "edit_object_folder",  text="Carpeta")
                                col_ed.prop(th, "edit_blend_filename", text="Archivo .blend")
                                col_ed.prop(th, "edit_levels_up",      text="Niveles arriba")

                                box_edit.separator(factor=0.3)
                                row_ed_f = box_edit.row(align=True)
                                row_ed_f.prop(th, "edit_frame_start", text="Inicio")
                                row_ed_f.prop(th, "edit_frame_end",   text="Fin")

                                box_edit.separator(factor=0.3)
                                box_edit.label(text="Aparentamiento:", icon="BONE_DATA")
                                row_ed_arm = box_edit.row(align=True)
                                row_ed_arm.prop(th, "edit_parent_armature", text="Armature")
                                _op_det = row_ed_arm.operator(
                                    "jrst.throw_detect_armature", text="", icon="VIEWZOOM")
                                _op_det.seg_idx = i
                                box_edit.prop(th, "edit_parent_bone", text="Bone")

                                # Grilla de bones de Jerry (cuadrupedo)
                                _JERRY_BONES = [
                                    "neck", "scull", "scull_1", "jaw_top",
                                    "ear.L", "ear.R",
                                    "spine_1", "spine_2", "spine_3", "spine_4",
                                    "spine_5", "spine_6", "spine_7",
                                    "tail_1", "tail_2", "tail_3",
                                    "shoulder.L", "shoulder.R",
                                    "front_thigh.L", "front_thigh.R",
                                    "front_shin.L", "front_shin.R",
                                    "front_foot.L", "front_foot.R",
                                    "front_toe.L", "front_toe.R",
                                    "thigh.L", "thigh.R",
                                    "shin.L", "shin.R",
                                    "foot.L", "foot.R",
                                    "toe.L", "toe.R",
                                ]
                                box_bones = box_edit.box()
                                box_bones.label(text="Bones de Jerry:", icon="BONE_DATA")
                                _tgrid = box_bones.grid_flow(row_major=True, columns=2, align=True)
                                for _bn in _JERRY_BONES:
                                    _op_tb = _tgrid.operator(
                                        "jrst.throw_pick_bone", text=_bn, emboss=True,
                                        depress=(th.edit_parent_bone == _bn))
                                    _op_tb.seg_idx = i; _op_tb.bone_name = _bn

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

                                box_edit.separator(factor=0.3)
                                box_edit.label(
                                    text="El CONCATENAR importa el objeto y aplica la trayectoria",
                                    icon="INFO")

                                box_edit.separator(factor=0.3)
                                box_edit.label(text="Referencia de trayectoria:", icon="FORCE_WIND")
                                box_edit.prop(th, "edit_target_bone", text="Bone origen")
                                _mode_lbl = "destino" if th.edit_mode == 'THROW' else "origen"
                                box_edit.label(
                                    text=f"Coordenada {_mode_lbl} (mundo):", icon="CURSOR")
                                row_ed_cur = box_edit.row()
                                _op_cur = row_ed_cur.operator(
                                    "jrst.throw_pick_dest_cursor",
                                    text="Tomar del cursor 3D", icon="PIVOT_CURSOR")
                                _op_cur.seg_idx = i
                                row_ed_xyz = box_edit.row(align=True)
                                row_ed_xyz.prop(th, "edit_dest_x", text="X")
                                row_ed_xyz.prop(th, "edit_dest_y", text="Y")
                                row_ed_xyz.prop(th, "edit_dest_z", text="Z")
                                box_edit.prop(th, "edit_easing_global", text="Curva general")

                                row_ed_spin = box_edit.row(align=True)
                                row_ed_spin.prop(th, "edit_spin_during_flight", text="Rotacion en vuelo")
                                if th.edit_spin_during_flight:
                                    row_ed_spin.prop(th, "edit_spin_turns", text="vueltas")

                                box_edit.separator(factor=0.3)
                                if th.active_idx >= 0 and th.active_idx < len(th.items):
                                    row_ed_wp = box_edit.row(align=True)
                                    _op_wpa = row_ed_wp.operator(
                                        "jrst.throw_add_waypoint",
                                        text="+ Waypoint", icon="ADD")
                                    _op_wpa.seg_idx = i
                                    _op_wpa.item_idx = th.active_idx
                                    _op_wpa.from_cursor = False
                                    _op_wpc = row_ed_wp.operator(
                                        "jrst.throw_add_waypoint",
                                        text="Desde cursor", icon="PIVOT_CURSOR")
                                    _op_wpc.seg_idx = i
                                    _op_wpc.item_idx = th.active_idx
                                    _op_wpc.from_cursor = True

                                box_edit.separator(factor=0.5)
                                row_ed_btns = box_edit.row(align=True)
                                row_ed_btns.scale_y = 1.3
                                _op_add = row_ed_btns.operator(
                                    "jrst.throw_add_item",
                                    text="+ Agregar lanzamiento", icon="ADD")
                                _op_add.seg_idx = i
                                if th.active_idx >= 0 and th.active_idx < len(th.items):
                                    _op_upd = row_ed_btns.operator(
                                        "jrst.throw_update_item",
                                        text="Actualizar", icon="FILE_REFRESH")
                                    _op_upd.seg_idx = i; _op_upd.item_idx = th.active_idx

                        except Exception as _e_throw:
                            box_cfg.label(text=f"[Lanzar/Recoger: {_e_throw}]", icon="ERROR")

                        # NOTA (Kebyn, 2026-08-27): el panel "Secuencia de Ojos"
                        # (Sistema 1 / CONCATENAR_2) por-segmento se elimino por
                        # no usarse -- ver operators_base.py para el detalle de
                        # los operadores retirados junto con el.

                    else:
                        # Resumen compacto cuando está colapsado
                        # NOTA (Kebyn, 2026-08-06): seg.pose_start_name/file y
                        # seg.pose_end_name/file ya no existen -- el primer y
                        # ultimo item de action_poses son ahora las anclas de
                        # inicio/fin.
                        col_info = box_seg.column(align=True)
                        col_info.scale_y = 0.75
                        _ap_summary = list(seg.action_poses)
                        if _ap_summary:
                            _ap_s = _ap_summary[0]
                            col_info.label(text=f"  Inicio: {_ap_s.pose_name or _ap_s.json_file}", icon="KEYFRAME")
                        if seg.pose_mid_label or seg.pose_mid_file:
                            col_info.label(text=f"  Interm: {seg.pose_mid_label or seg.pose_mid_file}  fr{seg.frame_mid}", icon="DOT")
                        if _ap_summary:
                            _ap_e = _ap_summary[-1]
                            col_info.label(text=f"  Fin:    {_ap_e.pose_name or _ap_e.json_file}", icon="KEYFRAME_HLT")
            else:
                box_list.label(text="  (sin segmentos — crea uno arriba)", icon="INFO")




# =============================================================================
# JRRST_UL_EyeSlots / _draw_eye_state_transforms / _draw_eye_sistema1 /
# _draw_eye_sistema2 / _draw_eye_sequence_content ELIMINADOS (Kebyn,
# 2026-08-27): panel "Secuencia de Ojos" por-segmento sin uso -- ver nota
# equivalente en operators_base.py.
# =============================================================================



# =============================================================================
# PANEL: OSCILACIONES DE BONES PERSONALIZADAS
# =============================================================================

def _get_bones_from_historia(context):
    """
    Extrae la lista de bones del personaje usando multiples fuentes en orden de prioridad:
      1. Armature activo en la escena de Blender (mas fiable, siempre actualizado)
      2. JSON estilo jerry.json  -> collections.scene_collection.objects[*].bone_hierarchy
      3. JSON estilo historia_jerry_*.json -> rig_info.categorias_animacion.completo
      4. JSON estilo historia -> aplanar bones_principales
    Devuelve lista de strings o [] si falla.
    """
    import bpy, json, os

    # ── Fuente 1: leer directamente del armature en escena ──────────────────
    try:
        st = context.scene.jerryst
        arm_name = getattr(st, "armature_name", "Dog_001_rig")
        arm_obj = bpy.data.objects.get(arm_name)
        if arm_obj and arm_obj.type == "ARMATURE" and arm_obj.data.bones:
            return sorted([b.name for b in arm_obj.data.bones])
    except Exception as e:
        print(f"[JerryStudio] bones_from_armature error: {e}")

    # ── Fuente 2 y 3: leer desde el JSON configurado ────────────────────────
    try:
        st = context.scene.jerryst
        filepath = bpy.path.abspath(st.historia_json)
        if not filepath or not os.path.isfile(filepath):
            return []
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Fuente 2: formato jerry.json -> bone_hierarchy recursivo
        def _extract_from_hierarchy(bone_list, out=None):
            if out is None:
                out = []
            for bone in bone_list:
                name = bone.get("name")
                if name and name not in out:
                    out.append(name)
                children = bone.get("children", [])
                if children:
                    _extract_from_hierarchy(children, out)
            return out

        collections = data.get("collections", {})
        scene_col = collections.get("scene_collection", {})
        objects = scene_col.get("objects", [])
        all_bones_hier = []
        for obj in objects:
            hier = obj.get("bone_hierarchy")
            if hier and isinstance(hier, list):
                _extract_from_hierarchy(hier, all_bones_hier)
        if all_bones_hier:
            return sorted(all_bones_hier)

        # Fuente 3: formato historia_jerry_*.json -> rig_info.categorias_animacion.completo
        rig = data.get("rig_info", {})
        completo = rig.get("categorias_animacion", {}).get("completo", [])
        if completo and isinstance(completo, list):
            return [b for b in completo if isinstance(b, str)]

        # Fuente 4: aplanar bones_principales
        bp = rig.get("bones_principales", {})
        bones = []
        def _flatten(obj):
            if isinstance(obj, list):
                for item in obj:
                    _flatten(item)
            elif isinstance(obj, dict):
                for v in obj.values():
                    _flatten(v)
            elif isinstance(obj, str):
                if obj not in bones:
                    bones.append(obj)
        _flatten(bp)
        return bones

    except Exception as e:
        print(f"[JerryStudio] _get_bones_from_historia error: {e}")
        return []


# =============================================================================
# PANEL GLOBAL: IMPORTACION DE OBJETOS (props, accesorios)
# =============================================================================

class JRRST_PT_ObjectImports(Panel):
    bl_label       = "3c  Importacion de Objetos"
    bl_idname      = "JRRST_PT_object_imports"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Jerry Studio"
    bl_parent_id   = "JRRST_PT_main"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        # Solo mostrar este panel global si NO hay segmentos activos
        # (en modo segmentos, los objetos se gestionan inline por segmento)
        segs = getattr(context.scene, "jerry_segs", None)
        if segs is not None and len(segs.segments) > 0:
            return False
        return True

    def draw_header(self, context):
        oi = context.scene.jerryst.object_imports
        self.layout.prop(oi, "enabled", text="")

    def draw(self, context):
        layout = self.layout
        st = context.scene.jerryst
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
                op_sel = row_item.operator("jrst.obj_import_toggle_item", text="", icon=icon_sel, emboss=False)
                op_sel.item_idx = i

                icon_en = "HIDE_OFF" if item.enabled else "HIDE_ON"
                op_en = row_item.operator("jrst.obj_import_toggle_item", text="", icon=icon_en)
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

                op_edit = row_item.operator("jrst.obj_import_load_to_editor", text="", icon="GREASEPENCIL")
                op_edit.item_idx = i
                op_dup = row_item.operator("jrst.obj_import_duplicate_item", text="", icon="DUPLICATE")
                op_dup.item_idx = i
                op_del = row_item.operator("jrst.obj_import_remove_item", text="", icon="X")
                op_del.item_idx = i

            if len(oi.items) > 1:
                row_move = box_list.row(align=True)
                op_up = row_move.operator("jrst.obj_import_move_item", text="Subir",  icon="TRIA_UP")
                op_up.direction = "UP"
                op_dn = row_move.operator("jrst.obj_import_move_item", text="Bajar",  icon="TRIA_DOWN")
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
        row_browse.operator("jrst.obj_import_browse_blend", text="Buscar .blend...", icon="FILEBROWSER")

        col.prop(oi, "edit_object_folder",  text="Carpeta")
        col.prop(oi, "edit_blend_filename", text="Archivo .blend")
        col.prop(oi, "edit_object_name",    text="Nombre objeto")

        row_preview = box_edit.row(align=True)
        row_preview.scale_y = 1.2
        row_preview.operator("jrst.obj_import_preview_now", text="Importar .blend al Outliner", icon="IMPORT")

        box_edit.separator()

        row_frames = box_edit.row(align=True)
        row_frames.prop(oi, "edit_frame_start", text="Inicio")
        row_frames.prop(oi, "edit_frame_end",   text="Fin")

        box_edit.separator()

        col_par = box_edit.column(align=True)
        col_par.label(text="Parenteo:", icon="BONE_DATA")
        row_arm = col_par.row(align=True)
        row_arm.prop(oi, "edit_parent_armature", text="Armature")
        row_arm.operator("jrst.obj_import_detect_armature", text="", icon="VIEWZOOM")
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

        box_edit.separator()

        # ── Transiciones ─────────────────────────────────────────────────
        box_trans = box_edit.box()
        box_trans.label(text="Transiciones cartoon:", icon="ANIM")

        col_ti = box_trans.column(align=True)
        col_ti.label(text="Aparicion (frame inicio):", icon="KEYFRAME")
        row_ti = col_ti.row(align=True)
        row_ti.scale_y = 1.15
        if hasattr(oi, "edit_transition_in"):
            row_ti.prop(oi, "edit_transition_in", text="")
            t_in_val = getattr(oi, "edit_transition_in", "NONE")
            if t_in_val and t_in_val != 'NONE':
                col_ti.prop(oi, "edit_transition_in_duration", text="Duracion (frames)")
        else:
            row_ti.label(text="(recarga el addon)", icon="ERROR")

        box_trans.separator(factor=0.3)

        col_to = box_trans.column(align=True)
        col_to.label(text="Desaparicion (frame fin):", icon="KEYFRAME_HLT")
        row_to = col_to.row(align=True)
        row_to.scale_y = 1.15
        if hasattr(oi, "edit_transition_out"):
            row_to.prop(oi, "edit_transition_out", text="")
            t_out_val = getattr(oi, "edit_transition_out", "NONE")
            if t_out_val and t_out_val != 'NONE':
                col_to.prop(oi, "edit_transition_out_duration", text="Duracion (frames)")
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
            row_btns.operator("jrst.obj_import_update_item", text="Actualizar", icon="CHECKMARK")
            row_btns.operator("jrst.obj_import_add_item",    text="+ Agregar nuevo", icon="ADD")
        else:
            row_btns.active_default = True
            row_btns.operator("jrst.obj_import_add_item", text="+ Agregar objeto", icon="CHECKMARK")

        layout.separator()
        layout.label(text="Los objetos se incluyen en el .py al EXPORTAR", icon="INFO")
