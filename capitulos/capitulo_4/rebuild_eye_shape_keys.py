# -*- coding: utf-8 -*-
"""
rebuild_eye_shape_keys.py
─────────────────────────────────────────────────────────────────────────────
Script de utilidad — Alfred Animation Studio
Reconstruye los Shape Keys de expresion de ojos leyendo la configuracion
directamente desde los archivos .py de slot ya exportados.

USO:
  Pegar en el Text Editor de Blender y ejecutar con "Run Script",
  o cargarlo desde el menu "Scripts" del addon.

El panel aparece en: Vista 3D → N-panel → pestaña "Alfred"
─────────────────────────────────────────────────────────────────────────────
"""

import bpy
import os
import json
import importlib.util
from bpy.props import StringProperty, BoolProperty, CollectionProperty, IntProperty
from bpy.types import PropertyGroup, Operator, Panel, UIList


# ─────────────────────────────────────────────────────────────────────────────
# LOGICA DE RECONSTRUCCION
# ─────────────────────────────────────────────────────────────────────────────

EYE_NAMES = ("ojo_izquierdo_alfred", "ojo_derecho_alfred")


def _apply_curve(factor, cm):
    if cm == "QUADRATIC": return factor ** 2
    if cm == "CUBIC":     return factor ** 3
    return factor


def _compute_vertex(orig_co, h_axis, v_axis, bounds, expr, cfg, mirror_h=False):
    cx = bounds["cx"]; cy = bounds["cy"]; cz = bounds["cz"]
    rx = bounds["rx"]; ry = bounds["ry"]; rz = bounds["rz"]
    h_val = getattr(orig_co, h_axis)
    v_val = getattr(orig_co, v_axis)
    cv = {"x": cx, "y": cy, "z": cz}[v_axis]
    rv = {"x": rx, "y": ry, "z": rz}[v_axis]
    ch = {"x": cx, "y": cy, "z": cz}[h_axis]
    rh = {"x": rx, "y": ry, "z": rz}[h_axis]
    v_mult = -1 if cfg["invert_vertical"]   else 1
    h_mult = -1 if cfg["invert_horizontal"] else 1
    v_factor = (v_val - cv) / (rv / 2) if rv > 0 else 0
    h_factor = (h_val - ch) / (rh / 2) if rh > 0 else 0
    if mirror_h:
        h_factor = -h_factor
    zone = cfg["affect_zone"]
    if zone == "UPPER":
        if v_factor <= 0: return orig_co.copy()
        v_fn = v_factor
    elif zone == "LOWER":
        if v_factor >= 0: return orig_co.copy()
        v_fn = -v_factor
    else:
        v_fn = abs(v_factor)
    offset = 0.0
    cm = cfg["curve_mode"]
    if expr in ("feliz", "triste"):
        curve  = _apply_curve(abs(h_factor), cm)
        intens = cfg["intensity_feliz"] if expr == "feliz" else cfg["intensity_triste"]
        sign   = 1 if expr == "feliz" else -1
        offset = sign * intens * curve * v_fn * v_mult
    elif expr in ("sospecha", "enojado"):
        min_h  = ch - rh / 2
        h_norm = (h_val - min_h) / rh if rh > 0 else 0.5
        if mirror_h: h_norm = 1.0 - h_norm
        if expr == "sospecha":
            intens = cfg["intensity_sospecha"]
            offset = (intens * h_norm - intens / 2) * v_fn * v_mult * h_mult
        else:
            intens = cfg["intensity_enojado"]
            offset = (-intens * h_norm + intens / 2) * v_fn * v_mult * h_mult
    elif expr == "cerrado":
        offset = -(v_val - cv) * 0.85
    elif expr == "cansado":
        offset = -(v_val - cv) * 0.4 * v_fn
    elif expr == "sorpresa":
        offset = (v_val - cv) * 0.15 * v_fn
    new_co = orig_co.copy()
    setattr(new_co, v_axis, v_val + offset)
    return new_co


def rebuild_shape_keys_for_eye(eye_obj, cfg, base_verts, is_right):
    """
    Restaura geometria y reconstruye todos los shape keys para un objeto ojo.
    Devuelve (ok: bool, msg: str).
    """
    if not eye_obj or eye_obj.type != "MESH":
        return False, f"Objeto '{eye_obj.name if eye_obj else '?'}' no es una malla"

    # ── Restaurar geometria base desde base_verts ─────────────────────────
    if base_verts:
        if len(base_verts) != len(eye_obj.data.vertices):
            # Reconstruir malla desde cero con la subdivision correcta
            if eye_obj.data.shape_keys:
                eye_obj.shape_key_clear()
            bpy.context.view_layer.objects.active = eye_obj
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.mesh.dissolve_limited()
            cuts = cfg.get("subdivide_cuts", 3)
            for _ in range(cuts):
                bpy.ops.mesh.subdivide(number_cuts=1)
            bpy.ops.object.mode_set(mode="OBJECT")

        if len(base_verts) == len(eye_obj.data.vertices):
            if eye_obj.data.shape_keys:
                eye_obj.shape_key_clear()
            for i, co in enumerate(base_verts):
                eye_obj.data.vertices[i].co.x = co[0]
                eye_obj.data.vertices[i].co.y = co[1]
                eye_obj.data.vertices[i].co.z = co[2]
            eye_obj.data.update()
    else:
        # Sin datos base: subdivir solo si la malla es primitiva (<=12 verts)
        cuts = cfg.get("subdivide_cuts", 3)
        if cuts > 0 and len(eye_obj.data.vertices) <= 12:
            if eye_obj.data.shape_keys:
                eye_obj.shape_key_clear()
            bpy.context.view_layer.objects.active = eye_obj
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            for _ in range(cuts):
                bpy.ops.mesh.subdivide(number_cuts=1)
            bpy.ops.object.mode_set(mode="OBJECT")
        elif eye_obj.data.shape_keys:
            eye_obj.shape_key_clear()

    # ── Construir shape keys ──────────────────────────────────────────────
    eye_obj.shape_key_add(name="Basis", from_mix=False)
    mesh = eye_obj.data
    orig = [v.co.copy() for v in mesh.vertices]

    xs = [v.co.x for v in mesh.vertices]
    ys = [v.co.y for v in mesh.vertices]
    zs = [v.co.z for v in mesh.vertices]
    bounds = {
        "cx": (max(xs)+min(xs))/2, "cy": (max(ys)+min(ys))/2, "cz": (max(zs)+min(zs))/2,
        "rx": max(xs)-min(xs),     "ry": max(ys)-min(ys),     "rz": max(zs)-min(zs),
    }

    side  = "R" if is_right else "L"
    h_key = f"eye_{side}_h_axis"
    v_key = f"eye_{side}_v_axis"
    h_axis = cfg.get(h_key, "x")
    v_axis = cfg.get(v_key, "z")
    if cfg.get("swap_axes", False):
        h_axis, v_axis = v_axis, h_axis

    for expr in ("feliz", "triste", "enojado", "sospecha", "cerrado", "cansado", "sorpresa"):
        sk = eye_obj.shape_key_add(name=expr.capitalize(), from_mix=False)
        sk.value = 0.0
        sk.slider_min = -2.0
        sk.slider_max = 2.0
        for i, o in enumerate(orig):
            sk.data[i].co = _compute_vertex(o, h_axis, v_axis, bounds, expr, cfg, mirror_h=is_right)

    sk_cl = eye_obj.shape_key_add(name="Closed", from_mix=False)
    sk_cl.value = 0.0
    min_v = min(getattr(v.co, v_axis) for v in mesh.vertices)
    for i, v in enumerate(mesh.vertices):
        nc = v.co.copy()
        setattr(nc, v_axis, min_v)
        sk_cl.data[i].co = nc

    return True, (
        f"{eye_obj.name}: h={h_axis} v={v_axis} "
        f"verts={len(orig)} zone={cfg.get('affect_zone','?')} "
        f"invV={cfg.get('invert_vertical','?')} swap={cfg.get('swap_axes','?')}"
    )


def load_cfg_from_py(filepath):
    """
    Carga EYE_SEQUENCE_DATA y EYE_BASE_MESH_DATA desde un .py de slot.
    Devuelve (cfg, base_verts_L, base_verts_R) o (None, None, None) si falla.
    """
    try:
        spec = importlib.util.spec_from_file_location("_alfred_slot_tmp", filepath)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        return None, None, None, f"Error importando .py: {e}"

    eye_seq  = getattr(mod, "EYE_SEQUENCE_DATA",  None)
    eye_base = getattr(mod, "EYE_BASE_MESH_DATA", None)

    if not eye_seq or not isinstance(eye_seq, dict):
        return None, None, None, "No contiene EYE_SEQUENCE_DATA"

    global_cfg = eye_seq.get("global", {})
    if not global_cfg.get("enabled", False):
        return None, None, None, "EYE_SEQUENCE_DATA.enabled = False"

    cfg = {
        "curve_mode":        global_cfg.get("curve_mode",        "QUADRATIC"),
        "affect_zone":       global_cfg.get("affect_zone",       "UPPER"),
        "invert_vertical":   global_cfg.get("invert_vertical",   True),
        "invert_horizontal": global_cfg.get("invert_horizontal", False),
        "swap_axes":         global_cfg.get("swap_axes",         False),
        "subdivide_cuts":    global_cfg.get("subdivide_cuts",    3),
        "intensity_feliz":   global_cfg.get("intensity_feliz",   0.18),
        "intensity_triste":  global_cfg.get("intensity_triste",  0.18),
        "intensity_enojado": global_cfg.get("intensity_enojado", 0.18),
        "intensity_sospecha":global_cfg.get("intensity_sospecha",0.18),
        "eye_L_h_axis":      global_cfg.get("eye_L_h_axis",      "x"),
        "eye_L_v_axis":      global_cfg.get("eye_L_v_axis",      "z"),
        "eye_R_h_axis":      global_cfg.get("eye_R_h_axis",      "x"),
        "eye_R_v_axis":      global_cfg.get("eye_R_v_axis",      "z"),
    }

    bv_L = bv_R = None
    if eye_base and isinstance(eye_base, dict):
        bv_L = eye_base.get("eye_L")
        bv_R = eye_base.get("eye_R")

    return cfg, bv_L, bv_R, "OK"


# ─────────────────────────────────────────────────────────────────────────────
# PROPERTIES
# ─────────────────────────────────────────────────────────────────────────────

class ALFRED_SlotItem(PropertyGroup):
    """Un slot .py detectado en el directorio de animaciones."""
    name:      StringProperty()
    filepath:  StringProperty()
    selected:  BoolProperty(name="", default=True)
    status:    StringProperty(default="")     # "", "OK", "ERROR", "SKIP"
    status_msg: StringProperty(default="")


class ALFRED_EyeRebuildProps(PropertyGroup):
    anim_dir:    StringProperty(
        name="Directorio .py",
        description="Carpeta con los archivos slot_NNN_tipo.py de alfred",
        subtype="DIR_PATH",
        default="",
    )
    slots:       CollectionProperty(type=ALFRED_SlotItem)
    active_slot: IntProperty(default=0)
    last_log:    StringProperty(default="")


# ─────────────────────────────────────────────────────────────────────────────
# OPERADORES
# ─────────────────────────────────────────────────────────────────────────────

class ALFRED_OT_ScanSlots(Operator):
    bl_idname  = "alfred_eye.scan_slots"
    bl_label   = "Detectar slots"
    bl_description = "Busca archivos slot_NNN_tipo.py en el directorio indicado"

    def execute(self, context):
        props    = context.scene.alfred_eye_rebuild
        anim_dir = bpy.path.abspath(props.anim_dir)

        props.slots.clear()

        if not anim_dir or not os.path.isdir(anim_dir):
            self.report({"ERROR"}, f"Directorio no valido: {anim_dir}")
            return {"CANCELLED"}

        found = 0
        for fname in sorted(os.listdir(anim_dir)):
            if not fname.endswith(".py"):
                continue
            if not (fname.startswith("slot_") or "alfred" in fname.lower()):
                continue
            item = props.slots.add()
            item.name     = fname
            item.filepath = os.path.join(anim_dir, fname)
            item.selected = True
            item.status   = ""
            found += 1

        if found == 0:
            self.report({"WARNING"}, "No se encontraron archivos slot_*.py en ese directorio")
        else:
            self.report({"INFO"}, f"{found} slot(s) detectado(s)")

        return {"FINISHED"}


class ALFRED_OT_SelectAll(Operator):
    bl_idname  = "alfred_eye.select_all"
    bl_label   = "Todos"
    bl_description = "Seleccionar todos los slots"
    def execute(self, context):
        for item in context.scene.alfred_eye_rebuild.slots:
            item.selected = True
        return {"FINISHED"}


class ALFRED_OT_SelectNone(Operator):
    bl_idname  = "alfred_eye.select_none"
    bl_label   = "Ninguno"
    bl_description = "Deseleccionar todos los slots"
    def execute(self, context):
        for item in context.scene.alfred_eye_rebuild.slots:
            item.selected = False
        return {"FINISHED"}


class ALFRED_OT_RebuildShapeKeys(Operator):
    bl_idname   = "alfred_eye.rebuild_shape_keys"
    bl_label    = "Crear / Recrear Shape Keys"
    bl_description = (
        "Reconstruye los Shape Keys de expresion de ojos para los slots seleccionados, "
        "leyendo la configuracion exacta desde cada archivo .py"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props    = context.scene.alfred_eye_rebuild
        selected = [item for item in props.slots if item.selected]

        if not selected:
            self.report({"WARNING"}, "No hay slots seleccionados")
            return {"CANCELLED"}

        # Verificar que existen los objetos de ojo
        eye_L = bpy.data.objects.get("ojo_izquierdo_alfred")
        eye_R = bpy.data.objects.get("ojo_derecho_alfred")
        if not eye_L or not eye_R:
            self.report({"ERROR"},
                "No se encontraron 'ojo_izquierdo_alfred' y/o 'ojo_derecho_alfred' en la escena")
            return {"CANCELLED"}

        ok_count  = 0
        err_count = 0
        skip_count = 0
        log_lines = []

        for item in selected:
            item.status = ""
            item.status_msg = ""

            cfg, bv_L, bv_R, msg = load_cfg_from_py(item.filepath)

            if cfg is None:
                item.status     = "SKIP"
                item.status_msg = msg
                skip_count += 1
                log_lines.append(f"  SKIP  {item.name}: {msg}")
                continue

            errors = []
            ok_L, msg_L = rebuild_shape_keys_for_eye(eye_L, cfg, bv_L, is_right=False)
            if not ok_L:
                errors.append(f"ojo_izq: {msg_L}")
            else:
                log_lines.append(f"  OK    {item.name} | {msg_L}")

            ok_R, msg_R = rebuild_shape_keys_for_eye(eye_R, cfg, bv_R, is_right=True)
            if not ok_R:
                errors.append(f"ojo_der: {msg_R}")
            else:
                log_lines.append(f"        {msg_R}")

            if errors:
                item.status     = "ERROR"
                item.status_msg = " / ".join(errors)
                err_count += 1
                log_lines.append(f"  ERR   {item.name}: {item.status_msg}")
            else:
                item.status     = "OK"
                item.status_msg = msg_L
                ok_count += 1

        summary = f"Shape Keys reconstruidos: {ok_count} OK  |  {skip_count} sin ojos  |  {err_count} error(es)"
        props.last_log = "\n".join(log_lines)
        self.report({"INFO"} if err_count == 0 else {"WARNING"}, summary)
        return {"FINISHED"}


# ─────────────────────────────────────────────────────────────────────────────
# UI LIST
# ─────────────────────────────────────────────────────────────────────────────

STATUS_ICONS = {"OK": "CHECKMARK", "ERROR": "ERROR", "SKIP": "REMOVE", "": "FILE_SCRIPT"}

class ALFRED_UL_SlotList(bpy.types.UIList):
    bl_idname = "ALFRED_UL_slot_list"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        row.prop(item, "selected", text="")
        ic = STATUS_ICONS.get(item.status, "FILE_SCRIPT")
        row.label(text=item.name, icon=ic)
        if item.status == "OK":
            row.label(text="OK", icon="CHECKMARK")
        elif item.status == "ERROR":
            row.label(text="Error", icon="ERROR")
        elif item.status == "SKIP":
            row.label(text="Sin ojos", icon="REMOVE")


# ─────────────────────────────────────────────────────────────────────────────
# PANEL
# ─────────────────────────────────────────────────────────────────────────────

class ALFRED_PT_EyeRebuild(Panel):
    bl_label       = "Crear / Recrear Shape Keys de Ojos"
    bl_idname      = "ALFRED_PT_eye_rebuild"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Alfred"

    def draw(self, context):
        layout = context.layout
        props  = context.scene.alfred_eye_rebuild

        # ── Directorio ────────────────────────────────────────────────────
        box = layout.box()
        box.label(text="1 — Directorio de slots .py", icon="FILE_FOLDER")
        box.prop(props, "anim_dir", text="")

        # Detectar desde el addon si no hay ruta
        try:
            st = context.scene.alfst
            if not props.anim_dir and st.anim_dir:
                box.operator("alfred_eye.use_addon_dir",
                             text="Usar directorio del addon", icon="LINKED")
        except Exception:
            pass

        box.operator("alfred_eye.scan_slots",
                     text="Detectar slots", icon="FILE_REFRESH")

        if not props.slots:
            layout.label(text="(ningún slot detectado)", icon="INFO")
            return

        # ── Lista de slots ────────────────────────────────────────────────
        box2 = layout.box()
        box2.label(text=f"2 — Slots detectados ({len(props.slots)})", icon="SEQUENCE")

        row_sel = box2.row(align=True)
        row_sel.operator("alfred_eye.select_all",  text="Todos",   icon="CHECKBOX_HLT")
        row_sel.operator("alfred_eye.select_none", text="Ninguno", icon="CHECKBOX_DEHLT")

        box2.template_list(
            "ALFRED_UL_slot_list", "",
            props, "slots",
            props, "active_slot",
            rows=min(len(props.slots), 8),
        )

        # Detalle del slot activo
        if 0 <= props.active_slot < len(props.slots):
            active = props.slots[props.active_slot]
            if active.status_msg:
                sub = box2.box()
                sub.scale_y = 0.75
                for line in active.status_msg[:200].split(" / "):
                    sub.label(text=line, icon="DOT")

        # ── Objetos de ojo en escena ──────────────────────────────────────
        box3 = layout.box()
        box3.label(text="3 — Objetos de ojo en escena", icon="HIDE_OFF")
        for name in ("ojo_izquierdo_alfred", "ojo_derecho_alfred"):
            obj = bpy.data.objects.get(name)
            row = box3.row()
            if obj:
                sk_count = len(obj.data.shape_keys.key_blocks) if obj.data.shape_keys else 0
                row.label(text=f"{name}  ({sk_count} shape keys)", icon="CHECKMARK")
            else:
                row.label(text=f"{name}  (no encontrado)", icon="ERROR")

        # ── Boton principal ───────────────────────────────────────────────
        layout.separator()
        n_sel = sum(1 for s in props.slots if s.selected)
        op_row = layout.row()
        op_row.scale_y = 1.6
        op_row.operator(
            "alfred_eye.rebuild_shape_keys",
            text=f"Crear / Recrear Shape Keys  ({n_sel} slot{'s' if n_sel != 1 else ''})",
            icon="SCULPTMODE_HLT",
        )

        # ── Log ───────────────────────────────────────────────────────────
        if props.last_log:
            box_log = layout.box()
            box_log.label(text="Resultado:", icon="INFO")
            col = box_log.column(align=True)
            col.scale_y = 0.70
            for line in props.last_log.splitlines()[:30]:
                col.label(text=line)


# Operador auxiliar: copiar ruta del addon
class ALFRED_OT_UseAddonDir(Operator):
    bl_idname  = "alfred_eye.use_addon_dir"
    bl_label   = "Usar directorio del addon"
    bl_description = "Copia la ruta de animaciones configurada en Alfred Animation Studio"

    def execute(self, context):
        try:
            context.scene.alfred_eye_rebuild.anim_dir = context.scene.alfst.anim_dir
            self.report({"INFO"}, "Ruta copiada desde el addon")
        except Exception as e:
            self.report({"ERROR"}, f"No se pudo leer alfst.anim_dir: {e}")
        return {"FINISHED"}


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRO
# ─────────────────────────────────────────────────────────────────────────────

_CLASSES = [
    ALFRED_SlotItem,
    ALFRED_EyeRebuildProps,
    ALFRED_UL_SlotList,
    ALFRED_OT_ScanSlots,
    ALFRED_OT_SelectAll,
    ALFRED_OT_SelectNone,
    ALFRED_OT_RebuildShapeKeys,
    ALFRED_OT_UseAddonDir,
    ALFRED_PT_EyeRebuild,
]


def register():
    for cls in _CLASSES:
        try:
            bpy.utils.register_class(cls)
        except Exception:
            bpy.utils.unregister_class(cls)
            bpy.utils.register_class(cls)
    bpy.types.Scene.alfred_eye_rebuild = bpy.props.PointerProperty(type=ALFRED_EyeRebuildProps)
    print("[alfred_eye_rebuild] registrado")


def unregister():
    for cls in reversed(_CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
    if hasattr(bpy.types.Scene, "alfred_eye_rebuild"):
        del bpy.types.Scene.alfred_eye_rebuild
    print("[alfred_eye_rebuild] desregistrado")


# Cuando se ejecuta directamente desde el Text Editor
if __name__ == "__main__":
    register()
