"""
alfred_eye_props.py
===================
PropertyGroups editables para la configuracion de ojos de Alfred
por slot. Permite editar INICIO / CAMBIOS INTERMEDIOS / FIN directamente
desde el panel de slots de capitulo_2 y guardar los cambios de vuelta
al .py del slot.
"""

import bpy
import json
import os
import importlib.util

from bpy.props import (
    StringProperty, IntProperty, FloatProperty, BoolProperty,
    EnumProperty, CollectionProperty, PointerProperty,
)
from bpy.types import PropertyGroup, Operator

# ── Enums ──────────────────────────────────────────────────────────────────

INTERP_ITEMS = [
    ("LINEAR",           "Linear",                ""),
    ("SMOOTH",           "Smooth (Smoothstep)",   ""),
    ("EASE_IN_QUAD",     "Ease In (Cuadratico)",  ""),
    ("EASE_OUT_QUAD",    "Ease Out (Cuadratico)", ""),
    ("EASE_IN_OUT_QUAD", "Ease In-Out Quad",      ""),
    ("EASE_IN_CUBIC",    "Ease In (Cubico)",      ""),
    ("EASE_OUT_CUBIC",   "Ease Out (Cubico)",     ""),
    ("EASE_IN_SINE",     "Ease In (Seno)",        ""),
    ("EASE_OUT_SINE",    "Ease Out (Seno)",       ""),
    ("EASE_IN_OUT_SIN",  "Ease In-Out Seno",      ""),
    ("BOUNCE",           "Bounce",                ""),
    ("BOUNCE_IN",        "Bounce In",             ""),
    ("ELASTIC",          "Elastic Out",           ""),
    ("ELASTIC_IN",       "Elastic In",            ""),
    ("ELASTIC_IN_OUT",   "Elastic In-Out",        ""),
    ("SPRING",           "Spring (Resorte)",      ""),
    ("OVERSHOOT",        "Overshoot",             ""),
    ("ANTICIPATION",     "Anticipacion",          ""),
    ("STEPPED",          "Stepped",               ""),
]

EXPRESSION_ITEMS = [
    ("NEUTRAL",  "Neutral",   ""),
    ("FELIZ",    "Feliz",     ""),
    ("TRISTE",   "Triste",    ""),
    ("ENOJADO",  "Enojado",   ""),
    ("SOSPECHA", "Sospecha",  ""),
    ("CERRADO",  "Cerrado",   ""),
    ("CANSADO",  "Cansado",   ""),
    ("SORPRESA", "Sorpresa",  ""),
]

BLINK_MODE_ITEMS = [
    ("FIXED", "Posicion fija", ""),
    ("BLINK", "Parpadeo",      ""),
]

AFFECT_ZONE_ITEMS = [
    ("SUPERIOR", "Superior", ""),
    ("INFERIOR", "Inferior", ""),
    ("COMPLETO", "Completo", ""),
]

CURVE_MODE_ITEMS = [
    ("CUADRATICA", "Cuadratica", ""),
    ("LINEAL",     "Lineal",     ""),
    ("CUBICA",     "Cubica",     ""),
]

# ── Estado de ojo (inicio / fin) ──────────────────────────────────────────

class AlfEyeStateProps(PropertyGroup):
    duration:           IntProperty(name="Duracion (frames)", default=2, min=1)
    interp_type:        EnumProperty(name="Interpolacion", items=INTERP_ITEMS, default="SMOOTH")
    blink_mode:         EnumProperty(name="Comportamiento", items=BLINK_MODE_ITEMS, default="FIXED")
    blink_count:        IntProperty(name="Num parpadeos", default=2, min=1)
    blink_duration:     IntProperty(name="Frames/parpadeo", default=4, min=1)
    active_expression:  EnumProperty(name="Expresion", items=EXPRESSION_ITEMS, default="NEUTRAL")
    expression_value:   FloatProperty(name="Valor", default=0.8, min=0.0, max=1.0, subtype='FACTOR')


# ── Slot intermedio ────────────────────────────────────────────────────────

class AlfEyeSlotProps(PropertyGroup):
    slot_label:         StringProperty(name="Etiqueta", default="expresion")
    duration:           IntProperty(name="Duracion (frames)", default=4, min=1)
    interp_type:        EnumProperty(name="Interpolacion", items=INTERP_ITEMS, default="ELASTIC_IN")
    active_expression:  EnumProperty(name="Expresion", items=EXPRESSION_ITEMS, default="ENOJADO")
    expression_value:   FloatProperty(name="Valor", default=0.8, min=0.0, max=1.0, subtype='FACTOR')


# ── Config global de shape keys ────────────────────────────────────────────

class AlfEyeGlobalProps(PropertyGroup):
    # Identificador "entity_name::slot_num" para saber a qué slot pertenece
    slot_key:           StringProperty(name="Clave", default="")

    loaded:             BoolProperty(name="Cargado", default=False)
    modified:           BoolProperty(name="Modificado", default=False)

    # Setup shape keys
    subdivide_cuts:     IntProperty(name="Subdivisiones previas", default=3, min=0, max=10)
    swap_axes:          BoolProperty(name="Swap H/V", default=False)
    invert_vertical:    BoolProperty(name="Inv V",    default=False)
    invert_horizontal:  BoolProperty(name="Inv H",    default=False)
    affect_zone:        EnumProperty(name="Zona",  items=AFFECT_ZONE_ITEMS, default="SUPERIOR")
    curve_mode:         EnumProperty(name="Curva", items=CURVE_MODE_ITEMS,  default="CUADRATICA")

    # Estado inicio / fin
    start: PointerProperty(type=AlfEyeStateProps)
    end:   PointerProperty(type=AlfEyeStateProps)

    # Slots intermedios
    slots:     CollectionProperty(type=AlfEyeSlotProps)
    slot_idx:  IntProperty(name="Slot activo", default=0)

    # Guarda todo el JSON original para no perder datos no expuestos
    raw_json:  StringProperty(name="JSON raw", default="")


# ── Helpers ────────────────────────────────────────────────────────────────

def _find_or_create_eye_config(context, slot_key):
    """Devuelve el AlfEyeGlobalProps para slot_key, creándolo si no existe."""
    col = context.scene.alfred_eye_configs
    for cfg in col:
        if cfg.slot_key == slot_key:
            return cfg
    new_cfg = col.add()
    new_cfg.slot_key = slot_key
    return new_cfg


def _get_eye_config(context, slot_key):
    """Devuelve el AlfEyeGlobalProps o None."""
    for cfg in context.scene.alfred_eye_configs:
        if cfg.slot_key == slot_key:
            return cfg
    return None


def _load_raw_from_file(filepath):
    """Carga EYE_SEQUENCE_DATA del .py del slot. Retorna (dict, msg)."""
    if not filepath or not os.path.isfile(filepath):
        return None, "Archivo no encontrado"
    try:
        spec = importlib.util.spec_from_file_location("_alf_eye_load_tmp", filepath)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        return None, f"Error importando: {e}"

    eye_seq = getattr(mod, "EYE_SEQUENCE_DATA", None)
    if not eye_seq or not isinstance(eye_seq, dict):
        return None, "Sin EYE_SEQUENCE_DATA"
    if not eye_seq.get("global", {}).get("enabled", False):
        return None, "Ojos deshabilitados en este slot"
    return eye_seq, "OK"


def _norm_enum(value, valid_values, default):
    """Normaliza un string al valor de enum correcto, insensible a mayúsculas."""
    if not value:
        return default
    upper = value.upper()
    for v in valid_values:
        if v.upper() == upper:
            return v
    return default


_VALID_AFFECT_ZONE  = [i[0] for i in AFFECT_ZONE_ITEMS]
_VALID_CURVE_MODE   = [i[0] for i in CURVE_MODE_ITEMS]
_VALID_BLINK_MODE   = [i[0] for i in BLINK_MODE_ITEMS]
_VALID_INTERP       = [i[0] for i in INTERP_ITEMS]
_VALID_EXPRESSION   = [i[0] for i in EXPRESSION_ITEMS]


def _norm_expr(val):
    return _norm_enum(val, _VALID_EXPRESSION, "NEUTRAL")


def _norm_interp(val):
    return _norm_enum(val, _VALID_INTERP, "SMOOTH")


def _file_has_eye_data(filepath):
    """Comprueba rapidamente si el .py tiene EYE_SEQUENCE_DATA habilitado. Sin escribir nada."""
    if not filepath or not os.path.isfile(filepath):
        return False
    try:
        spec = importlib.util.spec_from_file_location("_alf_eye_check_tmp", filepath)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        eye_seq = getattr(mod, "EYE_SEQUENCE_DATA", None)
        return (
            isinstance(eye_seq, dict)
            and eye_seq.get("global", {}).get("enabled", False)
        )
    except Exception:
        return False


def _populate_cfg_from_data(cfg, eye_data):
    """Rellena cfg con los datos de eye_data dict."""
    g = eye_data.get("global", {})
    s = eye_data.get("start",  {})
    e = eye_data.get("end",    {})
    slots = eye_data.get("slots", [])

    cfg.subdivide_cuts     = int(g.get("subdivide_cuts", 3))
    cfg.swap_axes          = bool(g.get("swap_axes", False))
    cfg.invert_vertical    = bool(g.get("invert_vertical", False))
    cfg.invert_horizontal  = bool(g.get("invert_horizontal", False))
    cfg.affect_zone        = _norm_enum(g.get("affect_zone", "SUPERIOR"), _VALID_AFFECT_ZONE, "SUPERIOR")
    cfg.curve_mode         = _norm_enum(g.get("curve_mode",  "CUADRATICA"), _VALID_CURVE_MODE, "CUADRATICA")

    def _fill_state(state_prop, d):
        state_prop.duration          = int(d.get("duration", 2))
        state_prop.interp_type       = _norm_interp(d.get("interp_type", "SMOOTH"))
        state_prop.blink_mode        = _norm_enum(d.get("blink_mode", "FIXED"), _VALID_BLINK_MODE, "FIXED")
        state_prop.blink_count       = int(d.get("blink_count", 2))
        state_prop.blink_duration    = int(d.get("blink_duration", 4))
        state_prop.active_expression = _norm_expr(d.get("active_expression", "NEUTRAL"))
        state_prop.expression_value  = float(d.get("expression_value", 0.8))

    _fill_state(cfg.start, s)
    _fill_state(cfg.end,   e)

    cfg.slots.clear()
    for sd in slots:
        ns = cfg.slots.add()
        ns.slot_label        = sd.get("slot_label", "expresion")
        ns.duration          = int(sd.get("duration", 4))
        ns.interp_type       = _norm_interp(sd.get("interp_type", "ELASTIC_IN"))
        ns.active_expression = _norm_expr(sd.get("active_expression", "NEUTRAL"))
        ns.expression_value  = float(sd.get("expression_value", 0.8))

    cfg.raw_json  = json.dumps(eye_data, ensure_ascii=False)
    cfg.loaded    = True
    cfg.modified  = False


def _cfg_to_data(cfg):
    """Convierte cfg props de vuelta a un dict EYE_SEQUENCE_DATA."""
    # Recuperar el dict original para preservar campos no expuestos
    try:
        raw = json.loads(cfg.raw_json) if cfg.raw_json else {}
    except Exception:
        raw = {}

    g_orig = raw.get("global", {})

    global_cfg = dict(g_orig)
    global_cfg.update({
        "enabled":         True,
        "subdivide_cuts":  cfg.subdivide_cuts,
        "swap_axes":       cfg.swap_axes,
        "invert_vertical": cfg.invert_vertical,
        "invert_horizontal": cfg.invert_horizontal,
        "affect_zone":     cfg.affect_zone,
        "curve_mode":      cfg.curve_mode,
    })

    def _state_dict(state_prop, orig_d):
        d = dict(orig_d)
        d.update({
            "duration":          state_prop.duration,
            "interp_type":       state_prop.interp_type,
            "blink_mode":        state_prop.blink_mode,
            "blink_count":       state_prop.blink_count,
            "blink_duration":    state_prop.blink_duration,
            "active_expression": state_prop.active_expression,
            "expression_value":  round(state_prop.expression_value, 3),
        })
        return d

    start_d = _state_dict(cfg.start, raw.get("start", {}))
    end_d   = _state_dict(cfg.end,   raw.get("end",   {}))

    orig_slots = raw.get("slots", [])
    slots_d = []
    for i, ns in enumerate(cfg.slots):
        orig = orig_slots[i] if i < len(orig_slots) else {}
        sd = dict(orig)
        sd.update({
            "slot_label":        ns.slot_label,
            "duration":          ns.duration,
            "interp_type":       ns.interp_type,
            "active_expression": ns.active_expression,
            "expression_value":  round(ns.expression_value, 3),
        })
        slots_d.append(sd)

    return {"global": global_cfg, "start": start_d, "slots": slots_d, "end": end_d}


def _patch_eye_sequence_in_file(filepath, eye_data):
    """Reemplaza EYE_SEQUENCE_DATA en el .py del slot."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    serialized = json.dumps(eye_data, indent=4, ensure_ascii=False)
    new_block = "\n".join([
        "# ============================================",
        "# SECUENCIA COMPLETA DE OJOS (panel 2b)",
        "# ============================================",
        "",
        "import json as _json_eye",
        f"EYE_SEQUENCE_DATA = _json_eye.loads({repr(serialized)})",
        "",
        "# ============================================",
        "# FIN DE SECUENCIA DE OJOS",
        "# ============================================",
    ])

    import re
    # Reemplazar bloque existente
    pattern = (
        r"# =+\s*\n# SECUENCIA COMPLETA DE OJOS.*?# FIN DE SECUENCIA DE OJOS\s*\n# =+\n?"
    )
    new_content, n = re.subn(pattern, new_block + "\n", content, flags=re.DOTALL)
    if n == 0:
        # Fallback: reemplazar solo la linea EYE_SEQUENCE_DATA =
        new_content = re.sub(
            r"EYE_SEQUENCE_DATA\s*=\s*_json_eye\.loads\([^\n]+\)",
            f"EYE_SEQUENCE_DATA = _json_eye.loads({repr(serialized)})",
            content,
        )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)


# ── Operadores ─────────────────────────────────────────────────────────────

class ALFEYECAP2_OT_LoadConfig(Operator):
    """Carga la configuracion de ojos del .py del slot en los props editables."""
    bl_idname  = "alfeyecap2.load_config"
    bl_label   = "Cargar config ojos"
    bl_options = {'REGISTER', 'UNDO'}

    slot_key: StringProperty(default="")
    filepath:  StringProperty(default="")

    def execute(self, context):
        eye_data, msg = _load_raw_from_file(self.filepath)
        if eye_data is None:
            self.report({'WARNING'}, msg)
            return {'CANCELLED'}

        cfg = _find_or_create_eye_config(context, self.slot_key)
        _populate_cfg_from_data(cfg, eye_data)
        self.report({'INFO'}, f"Config ojos cargada — {self.slot_key}")
        return {'FINISHED'}


class ALFEYECAP2_OT_SaveConfig(Operator):
    """Guarda los props editables de vuelta al .py del slot."""
    bl_idname  = "alfeyecap2.save_config"
    bl_label   = "Guardar cambios"
    bl_options = {'REGISTER', 'UNDO'}

    slot_key: StringProperty(default="")
    filepath:  StringProperty(default="")

    def execute(self, context):
        cfg = _get_eye_config(context, self.slot_key)
        if not cfg or not cfg.loaded:
            self.report({'WARNING'}, "No hay config cargada para guardar")
            return {'CANCELLED'}

        if not self.filepath or not os.path.isfile(self.filepath):
            self.report({'ERROR'}, "Archivo .py no encontrado")
            return {'CANCELLED'}

        eye_data = _cfg_to_data(cfg)
        try:
            _patch_eye_sequence_in_file(self.filepath, eye_data)
        except Exception as e:
            self.report({'ERROR'}, f"Error guardando: {e}")
            return {'CANCELLED'}

        cfg.modified = False
        # Actualizar raw_json
        cfg.raw_json = json.dumps(eye_data, ensure_ascii=False)
        self.report({'INFO'}, f"Config ojos guardada → {os.path.basename(self.filepath)}")
        return {'FINISHED'}


class ALFEYECAP2_OT_AddSlot(Operator):
    """Agrega un slot intermedio."""
    bl_idname  = "alfeyecap2.add_slot"
    bl_label   = "Agregar estado"
    bl_options = {'REGISTER', 'UNDO'}
    slot_key: StringProperty(default="")

    def execute(self, context):
        cfg = _get_eye_config(context, self.slot_key)
        if not cfg:
            return {'CANCELLED'}
        ns = cfg.slots.add()
        ns.slot_label = f"expresion"
        cfg.slot_idx  = len(cfg.slots) - 1
        cfg.modified  = True
        return {'FINISHED'}


class ALFEYECAP2_OT_RemoveSlot(Operator):
    """Elimina el slot intermedio activo."""
    bl_idname  = "alfeyecap2.remove_slot"
    bl_label   = "Eliminar estado"
    bl_options = {'REGISTER', 'UNDO'}
    slot_key: StringProperty(default="")

    def execute(self, context):
        cfg = _get_eye_config(context, self.slot_key)
        if not cfg or not cfg.slots:
            return {'CANCELLED'}
        idx = min(cfg.slot_idx, len(cfg.slots) - 1)
        cfg.slots.remove(idx)
        cfg.slot_idx  = max(0, idx - 1)
        cfg.modified  = True
        return {'FINISHED'}


class ALFEYECAP2_OT_MoveSlot(Operator):
    """Mueve un slot intermedio arriba o abajo."""
    bl_idname  = "alfeyecap2.move_slot"
    bl_label   = "Mover estado"
    bl_options = {'REGISTER', 'UNDO'}
    slot_key:  StringProperty(default="")
    direction: StringProperty(default="UP")

    def execute(self, context):
        cfg = _get_eye_config(context, self.slot_key)
        if not cfg or len(cfg.slots) < 2:
            return {'CANCELLED'}
        idx = cfg.slot_idx
        if self.direction == "UP" and idx > 0:
            cfg.slots.move(idx, idx - 1)
            cfg.slot_idx = idx - 1
        elif self.direction == "DOWN" and idx < len(cfg.slots) - 1:
            cfg.slots.move(idx, idx + 1)
            cfg.slot_idx = idx + 1
        cfg.modified = True
        return {'FINISHED'}


# ── UI de edicion inline ──────────────────────────────────────────────────

def draw_eye_editor(layout, cfg, slot_key, filepath):
    """
    Dibuja el panel de ojos editable (INICIO / CAMBIOS / FIN) con props reales.
    Llama a esta funcion desde ui_panels.py.
    """

    def _mark_modified(cfg):
        cfg.modified = True

    # ── INICIO (Ojos) ──────────────────────────────────────────────────────
    box_ini = layout.box()
    row_ini = box_ini.row()
    row_ini.label(text="INICIO  (Ojos)", icon='KEYFRAME')

    col_i = box_ini.column(align=True)
    row_d = col_i.row(align=True)
    row_d.label(text="Duracion:")
    row_d.prop(cfg.start, "duration", text="frames")

    row_ip = col_i.row(align=True)
    row_ip.label(text="Interpolacion salida:")
    row_ip.prop(cfg.start, "interp_type", text="")

    col_i.separator(factor=0.5)
    row_bm = col_i.row(align=True)
    row_bm.label(text="Comportamiento:")
    row_bm.prop(cfg.start, "blink_mode", expand=True)

    if cfg.start.blink_mode == 'BLINK':
        sub = col_i.column(align=True)
        sub.prop(cfg.start, "blink_count",    text="Numero parpadeos")
        sub.prop(cfg.start, "blink_duration", text="Frames/parpadeo")

    row_ex = col_i.row(align=True)
    row_ex.prop(cfg.start, "active_expression", text="Expresion")
    row_ex.prop(cfg.start, "expression_value",  text="Valor", slider=True)

    # ── N° CAMBIOS DE OJOS ─────────────────────────────────────────────────
    box_mid = layout.box()
    row_mid_hdr = box_mid.row()
    row_mid_hdr.label(text="N° CAMBIOS DE OJOS  (intermedios)", icon='NLA')

    # Setup shape keys
    sub_sk = box_mid.box()
    sub_sk.label(text="Setup de Shape Keys de ojos", icon='MESH_PLANE')
    col_sk = sub_sk.column(align=True)
    col_sk.prop(cfg, "subdivide_cuts", text="Subdivisiones previas")
    row_ax = col_sk.row(align=True)
    row_ax.prop(cfg, "swap_axes",         toggle=True)
    row_ax.prop(cfg, "invert_vertical",   toggle=True, text="Inv V")
    row_ax.prop(cfg, "invert_horizontal", toggle=True, text="Inv H")
    col_sk.prop(cfg, "affect_zone", text="Zona")
    col_sk.prop(cfg, "curve_mode",  text="Curva")

    # Botones add/remove/move
    row_btns = box_mid.row(align=True)
    op_add = row_btns.operator("alfeyecap2.add_slot",    text="+ Agregar", icon='ADD')
    op_add.slot_key = slot_key
    op_rem = row_btns.operator("alfeyecap2.remove_slot", text="Eliminar",  icon='REMOVE')
    op_rem.slot_key = slot_key

    if cfg.slots:
        # Lista de slots
        for idx, ns in enumerate(cfg.slots):
            ns_box = box_mid.box()
            ns_box.alert = (idx == cfg.slot_idx)

            # Header con nombre y botones up/down
            hrow = ns_box.row(align=True)
            hrow.prop(ns, "slot_label", text="")
            up_op = hrow.operator("alfeyecap2.move_slot", text="", icon='TRIA_UP')
            up_op.slot_key  = slot_key
            up_op.direction = "UP"
            dn_op = hrow.operator("alfeyecap2.move_slot", text="", icon='TRIA_DOWN')
            dn_op.slot_key  = slot_key
            dn_op.direction = "DOWN"

            col_ns = ns_box.column(align=True)
            row_nsd = col_ns.row(align=True)
            row_nsd.label(text="Frames:")
            row_nsd.prop(ns, "duration", text="")
            row_nsd.prop(ns, "interp_type", text="")

            row_nse = col_ns.row(align=True)
            row_nse.prop(ns, "active_expression", text="Expresion")
            row_nse.prop(ns, "expression_value",  text="Valor", slider=True)

        total_dur = sum(s.duration for s in cfg.slots)
        box_mid.label(
            text=f"  {len(cfg.slots)} estados  |  {total_dur} frames totales",
            icon='TIME',
        )
    else:
        box_mid.label(text="  Sin cambios: transicion directa inicio → fin", icon='INFO')

    # ── FIN (Ojos) ─────────────────────────────────────────────────────────
    box_fin = layout.box()
    box_fin.label(text="FIN  (Ojos)", icon='KEYFRAME_HLT')

    col_f = box_fin.column(align=True)
    row_fd = col_f.row(align=True)
    row_fd.label(text="Duracion:")
    row_fd.prop(cfg.end, "duration", text="frames")

    row_fi = col_f.row(align=True)
    row_fi.label(text="Interpolacion entrada:")
    row_fi.prop(cfg.end, "interp_type", text="")

    col_f.separator(factor=0.5)
    row_fbm = col_f.row(align=True)
    row_fbm.label(text="Comportamiento:")
    row_fbm.prop(cfg.end, "blink_mode", expand=True)

    if cfg.end.blink_mode == 'BLINK':
        sub = col_f.column(align=True)
        sub.prop(cfg.end, "blink_count",    text="Numero parpadeos")
        sub.prop(cfg.end, "blink_duration", text="Frames/parpadeo")

    row_fe = col_f.row(align=True)
    row_fe.prop(cfg.end, "active_expression", text="Expresion")
    row_fe.prop(cfg.end, "expression_value",  text="Valor", slider=True)

    # ── Boton Guardar ──────────────────────────────────────────────────────
    layout.separator(factor=0.5)
    save_row = layout.row()
    save_row.scale_y = 1.4
    if cfg.modified:
        save_row.alert = True
    save_op = save_row.operator(
        "alfeyecap2.save_config",
        text="💾  Guardar cambios de ojos" if not cfg.modified else "💾  Guardar cambios de ojos  ●",
        icon='FILE_TICK',
    )
    save_op.slot_key = slot_key
    save_op.filepath = filepath


# ── Registro ───────────────────────────────────────────────────────────────

_CLASSES = [
    AlfEyeStateProps,
    AlfEyeSlotProps,
    AlfEyeGlobalProps,
    ALFEYECAP2_OT_LoadConfig,
    ALFEYECAP2_OT_SaveConfig,
    ALFEYECAP2_OT_AddSlot,
    ALFEYECAP2_OT_RemoveSlot,
    ALFEYECAP2_OT_MoveSlot,
]


def register():
    for cls in _CLASSES:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"[alfred_eye_props] register {cls.__name__}: {e}")
    bpy.types.Scene.alfred_eye_configs = CollectionProperty(type=AlfEyeGlobalProps)


def unregister():
    if hasattr(bpy.types.Scene, 'alfred_eye_configs'):
        del bpy.types.Scene.alfred_eye_configs
    for cls in reversed(_CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
