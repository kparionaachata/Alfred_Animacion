# -*- coding: utf-8 -*-
"""
eye_library.py — Cerdo_1 Animation Studio v1.9
Libreria de expresiones de ojos: guardar, cargar, importar y aplicar
configuraciones JSON desde C:\\...\\refinar\\ojos

Cada JSON guarda:
  - Nombre y descripcion de la expresion
  - Expresion activa + valor
  - Posicion/escala/rotacion de las mallas de ojos
  - Deformacion de geometria (shape key target o modo libre)
  - Frame inicio, duracion y tipo de interpolacion
"""

import bpy, json, os, math
from bpy.types import Operator
from bpy.props import StringProperty, IntProperty, FloatProperty, EnumProperty
from .constants import EYE_MESH_NAMES, INTERP_TYPE_ITEMS, EYE_BASE_TRANSFORMS


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_EYE_LIB_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\cerdo_1\refinar\ojos"
)

def _get_eye_objects(context):
    """Devuelve lista de objetos de ojos existentes en la escena."""
    found = []
    for name in EYE_MESH_NAMES:
        obj = context.scene.objects.get(name)
        if obj and obj.type == "MESH":
            found.append(obj)
    return found

def _snapshot_eye_transforms(context):
    """Captura posicion, rotacion y escala de las mallas de ojos."""
    data = {}
    for obj in _get_eye_objects(context):
        data[obj.name] = {
            "location": list(obj.location),
            "rotation_euler": [math.degrees(a) for a in obj.rotation_euler],
            "scale": list(obj.scale),
        }
    return data

def _snapshot_shape_keys(context):
    """Captura todos los valores de shape keys de los ojos."""
    data = {}
    for obj in _get_eye_objects(context):
        if obj.data.shape_keys:
            kbs = {}
            for kb in obj.data.shape_keys.key_blocks:
                if kb.name != "Basis":
                    kbs[kb.name] = round(kb.value, 4)
            data[obj.name] = kbs
    return data

def _apply_eye_transforms(context, transforms_data):
    """Restaura posicion, rotacion y escala a los objetos de ojos."""
    for obj_name, td in transforms_data.items():
        obj = context.scene.objects.get(obj_name)
        if not obj:
            continue
        obj.location = td["location"]
        obj.rotation_euler = [math.radians(a) for a in td["rotation_euler"]]
        obj.scale = td["scale"]

def _apply_shape_keys(context, sk_data):
    """Restaura valores de shape keys a los objetos de ojos."""
    for obj_name, kbs in sk_data.items():
        obj = context.scene.objects.get(obj_name)
        if not obj or not obj.data.shape_keys:
            continue
        for kb_name, val in kbs.items():
            kb = obj.data.shape_keys.key_blocks.get(kb_name)
            if kb:
                kb.value = val

def _lib_dir(context):
    return bpy.path.abspath(context.scene.cerdo_1_st.eye_lib_dir) or DEFAULT_EYE_LIB_DIR

def _scan_library(lib_dir):
    """Devuelve lista de (nombre_sin_ext, filepath) de JSONs en la carpeta."""
    items = []
    if os.path.isdir(lib_dir):
        for fname in sorted(os.listdir(lib_dir)):
            if fname.lower().endswith(".json"):
                name = os.path.splitext(fname)[0]
                items.append((name, os.path.join(lib_dir, fname)))
    return items


# ─────────────────────────────────────────────────────────────────────────────
# OPERADOR: GUARDAR expresion en libreria
# ─────────────────────────────────────────────────────────────────────────────

class CERDO_1_ST_OT_SaveEyeExpression(Operator):
    bl_idname      = "cerdo_1_st.save_eye_expression"
    bl_label       = "Guardar expresion en libreria"
    bl_description = "Guarda el estado actual de los ojos (transforms + shape keys) como JSON en la carpeta de libreria"

    def execute(self, context):
        st     = context.scene.cerdo_1_st
        eye_s  = st.eye_expr
        lib_dir = _lib_dir(context)

        name = st.eye_lib_save_name.strip()
        if not name:
            self.report({"ERROR"}, "Escribe un nombre antes de guardar")
            return {"CANCELLED"}

        os.makedirs(lib_dir, exist_ok=True)

        _FORBIDDEN = set('/\\:*?"<>|')
        safe = "".join(c if c not in _FORBIDDEN else "_" for c in name)
        filepath = os.path.join(lib_dir, f"{safe}.json")

        payload = {
            "name":             name,
            "description":      st.eye_lib_save_desc,
            # ── Timeline ──
            "frame_start":      eye_s.lib_frame_start,
            "duration":         eye_s.lib_duration,
            "interp_type":      eye_s.lib_interp_type,
            # ── Expresion activa (shape key) ──
            "active_expression": eye_s.active_expression,
            "expression_value":  round(eye_s.expression_value, 4),
            # ── Transforms actuales de los objetos de ojos ──
            "transforms":       _snapshot_eye_transforms(context),
            # ── Shape keys actuales ──
            "shape_keys":       _snapshot_shape_keys(context),
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.report({"ERROR"}, f"No se pudo guardar: {e}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Guardado: {os.path.basename(filepath)}")
        # Refrescar lista de libreria
        bpy.ops.cerdo_1_st.refresh_eye_library()
        return {"FINISHED"}


# ─────────────────────────────────────────────────────────────────────────────
# OPERADOR: REFRESCAR lista de libreria
# ─────────────────────────────────────────────────────────────────────────────

class CERDO_1_ST_OT_RefreshEyeLibrary(Operator):
    bl_idname      = "cerdo_1_st.refresh_eye_library"
    bl_label       = "Actualizar libreria de ojos"
    bl_description = "Recarga la lista de expresiones JSON de la carpeta de libreria"

    def execute(self, context):
        st      = context.scene.cerdo_1_st
        lib_dir = _lib_dir(context)
        items   = _scan_library(lib_dir)

        st.eye_lib_entries.clear()
        for name, fpath in items:
            entry = st.eye_lib_entries.add()
            entry.name     = name
            entry.filepath = fpath

        self.report({"INFO"}, f"{len(items)} expresiones encontradas en libreria")
        return {"FINISHED"}


# ─────────────────────────────────────────────────────────────────────────────
# OPERADOR: CARGAR expresion de libreria (aplica al viewport)
# ─────────────────────────────────────────────────────────────────────────────

class CERDO_1_ST_OT_LoadEyeExpression(Operator):
    bl_idname      = "cerdo_1_st.load_eye_expression"
    bl_label       = "Cargar expresion"
    bl_description = "Aplica la expresion seleccionada: restaura transforms y shape keys en los ojos"

    def execute(self, context):
        st      = context.scene.cerdo_1_st
        eye_s   = st.eye_expr
        idx     = st.eye_lib_idx

        if not st.eye_lib_entries or idx >= len(st.eye_lib_entries):
            self.report({"ERROR"}, "Selecciona una expresion de la lista")
            return {"CANCELLED"}

        entry = st.eye_lib_entries[idx]
        try:
            with open(entry.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.report({"ERROR"}, f"No se pudo leer {entry.filepath}: {e}")
            return {"CANCELLED"}

        # Restaurar propiedades de timeline
        eye_s.lib_frame_start = data.get("frame_start", 1)
        eye_s.lib_duration    = data.get("duration",    20)
        eye_s.lib_interp_type = data.get("interp_type", "SMOOTH")

        # Restaurar expresion activa
        expr = data.get("active_expression", "NEUTRAL")
        val  = data.get("expression_value",  1.0)
        try:
            eye_s.active_expression = expr
        except Exception:
            pass
        eye_s.expression_value = val

        # Restaurar transforms de las mallas
        transforms = data.get("transforms", {})
        if transforms:
            _apply_eye_transforms(context, transforms)

        # Restaurar shape keys
        sk = data.get("shape_keys", {})
        if sk:
            _apply_shape_keys(context, sk)

        self.report({"INFO"}, f"Expresion '{data.get('name', entry.name)}' aplicada")
        return {"FINISHED"}


# ─────────────────────────────────────────────────────────────────────────────
# OPERADOR: IMPORTAR JSON externo (file browser)
# ─────────────────────────────────────────────────────────────────────────────

class CERDO_1_ST_OT_ImportEyeExpression(Operator):
    bl_idname      = "cerdo_1_st.import_eye_expression"
    bl_label       = "Importar expresion .json"
    bl_description = "Selecciona un archivo .json externo y lo carga como expresion de ojos"

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        lib_dir = _lib_dir(context)
        if os.path.isdir(lib_dir):
            self.filepath = lib_dir + os.sep
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        if not self.filepath or not os.path.isfile(self.filepath):
            self.report({"ERROR"}, "Archivo no encontrado")
            return {"CANCELLED"}
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.report({"ERROR"}, f"No se pudo leer: {e}")
            return {"CANCELLED"}

        st    = context.scene.cerdo_1_st
        eye_s = st.eye_expr

        eye_s.lib_frame_start = data.get("frame_start", 1)
        eye_s.lib_duration    = data.get("duration",    20)
        eye_s.lib_interp_type = data.get("interp_type", "SMOOTH")

        expr = data.get("active_expression", "NEUTRAL")
        val  = data.get("expression_value", 1.0)
        try:
            eye_s.active_expression = expr
        except Exception:
            pass
        eye_s.expression_value = val

        transforms = data.get("transforms", {})
        if transforms:
            _apply_eye_transforms(context, transforms)

        sk = data.get("shape_keys", {})
        if sk:
            _apply_shape_keys(context, sk)

        self.report({"INFO"}, f"Importado: {os.path.basename(self.filepath)}")
        return {"FINISHED"}


# ─────────────────────────────────────────────────────────────────────────────
# OPERADOR: INSERTAR KEYFRAME con datos de libreria
# ─────────────────────────────────────────────────────────────────────────────

class CERDO_1_ST_OT_KeyframeEyeExpression(Operator):
    bl_idname      = "cerdo_1_st.keyframe_eye_expression"
    bl_label       = "Insertar keyframe de ojos"
    bl_description = (
        "Inserta keyframes de transforms y shape keys de los ojos "
        "en el frame indicado (lib_frame_start)"
    )

    def execute(self, context):
        st    = context.scene.cerdo_1_st
        eye_s = st.eye_expr
        frame = eye_s.lib_frame_start

        inserted = 0
        for obj in _get_eye_objects(context):
            obj.keyframe_insert("location",        frame=frame)
            obj.keyframe_insert("rotation_euler",  frame=frame)
            obj.keyframe_insert("scale",           frame=frame)
            inserted += 1
            if obj.data.shape_keys:
                for kb in obj.data.shape_keys.key_blocks:
                    if kb.name != "Basis":
                        kb.keyframe_insert("value", frame=frame)

        context.scene.frame_set(frame)
        self.report({"INFO"}, f"Keyframes insertados en frame {frame} ({inserted} objetos)")
        return {"FINISHED"}


# ─────────────────────────────────────────────────────────────────────────────
# OPERADOR: ABRIR CARPETA de libreria
# ─────────────────────────────────────────────────────────────────────────────

class CERDO_1_ST_OT_OpenEyeLibFolder(Operator):
    bl_idname      = "cerdo_1_st.open_eye_lib_folder"
    bl_label       = "Abrir carpeta de libreria de ojos"
    bl_description = "Abre la carpeta de la libreria de expresiones en el explorador"

    def execute(self, context):
        import subprocess
        lib_dir = _lib_dir(context)
        os.makedirs(lib_dir, exist_ok=True)
        try:
            subprocess.Popen(f'explorer "{lib_dir}"')
        except Exception as e:
            self.report({"WARNING"}, f"No se pudo abrir: {e}")
        return {"FINISHED"}


# ─────────────────────────────────────────────────────────────────────────────
# OPERADOR: RESET TRANSFORMS de ojos al origen
# ─────────────────────────────────────────────────────────────────────────────

class CERDO_1_ST_OT_ResetEyeTransforms(Operator):
    bl_idname      = "cerdo_1_st.reset_eye_transforms"
    bl_label       = "Reset transforms de ojos"
    bl_description = "Restaura posicion de los ojos a su posicion base en el rostro de Cerdo_1 y escala/rotacion a neutro"

    # Coordenadas base de los ojos en el rostro de Cerdo_1
    _BASE = EYE_BASE_TRANSFORMS

    def execute(self, context):
        eye_s = context.scene.cerdo_1_st.eye_expr
        # Restaurar propiedades del panel
        eye_s.eye_L_loc_x, eye_s.eye_L_loc_y, eye_s.eye_L_loc_z = self._BASE["ojo_izquierdo_cerdo_1"]["loc"]
        eye_s.eye_L_rot_x = eye_s.eye_L_rot_y = eye_s.eye_L_rot_z = 0.0
        eye_s.eye_L_sca_x = eye_s.eye_L_sca_y = eye_s.eye_L_sca_z = 1.0

        eye_s.eye_R_loc_x, eye_s.eye_R_loc_y, eye_s.eye_R_loc_z = self._BASE["ojo_derecho_cerdo_1"]["loc"]
        eye_s.eye_R_rot_x = eye_s.eye_R_rot_y = eye_s.eye_R_rot_z = 0.0
        eye_s.eye_R_sca_x = eye_s.eye_R_sca_y = eye_s.eye_R_sca_z = 1.0

        # Aplicar a los objetos en la escena
        for obj_name, td in self._BASE.items():
            obj = context.scene.objects.get(obj_name)
            if not obj:
                continue
            obj.location       = td["loc"]
            obj.rotation_euler = td["rot"]
            obj.scale          = td["sca"]

        self.report({"INFO"}, "Ojos restaurados a posicion base de Cerdo_1")
        return {"FINISHED"}


# ─────────────────────────────────────────────────────────────────────────────
# OPERADOR: APLICAR TRANSFORMS DESDE PROPIEDADES DEL PANEL
# ─────────────────────────────────────────────────────────────────────────────

class CERDO_1_ST_OT_ApplyEyeTransforms(Operator):
    bl_idname      = "cerdo_1_st.apply_eye_transforms"
    bl_label       = "Aplicar transforms de ojos"
    bl_description = "Aplica los valores de posicion, rotacion y escala del panel a los objetos de ojos en la escena"

    def execute(self, context):
        eye_s = context.scene.cerdo_1_st.eye_expr

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

        applied = 0
        for obj_name, td in mapping.items():
            obj = context.scene.objects.get(obj_name)
            if not obj:
                continue
            obj.location       = td["loc"]
            obj.rotation_euler = td["rot"]   # ya en radianes (subtype=ANGLE)
            obj.scale          = td["sca"]
            applied += 1

        self.report({"INFO"}, f"Transforms aplicados a {applied} objetos")
        return {"FINISHED"}


# ─────────────────────────────────────────────────────────────────────────────
# OPERADOR: APLICAR GEOMETRIA / FORMA AL SHAPE KEY
# ─────────────────────────────────────────────────────────────────────────────

class CERDO_1_ST_OT_ApplyEyeGeometry(Operator):
    bl_idname      = "cerdo_1_st.apply_eye_geometry"
    bl_label       = "Aplicar forma de geometria"
    bl_description = (
        "Deforma la geometria de los ojos segun el modo seleccionado "
        "(Redondo, Plano, Squint, Ancho) creando/actualizando un shape key 'geo_form'"
    )

    def execute(self, context):
        eye_s = context.scene.cerdo_1_st.eye_expr
        mode  = eye_s.geo_edit_mode
        intensity = eye_s.geo_intensity

        if mode == "NONE":
            self.report({"INFO"}, "Modo 'Sin cambio': no se modifica la geometria")
            return {"FINISHED"}

        objs = _get_eye_objects(context)
        if not objs:
            self.report({"ERROR"}, "No se encontraron las mallas de ojos en la escena")
            return {"CANCELLED"}

        modified = 0
        for obj in objs:
            mesh = obj.data

            # Asegurar shape key Basis
            if not mesh.shape_keys:
                obj.shape_key_add(name="Basis", from_mix=False)

            # Crear o recuperar shape key de forma
            sk_name = f"geo_{mode.lower()}"
            sk = mesh.shape_keys.key_blocks.get(sk_name)
            if not sk:
                sk = obj.shape_key_add(name=sk_name, from_mix=False)

            basis = mesh.shape_keys.key_blocks["Basis"]

            # Calcular deformacion segun el modo
            for i, vert in enumerate(basis.data):
                co = vert.co.copy()
                x, y, z = co.x, co.y, co.z

                if mode == "ROUND":
                    # Expandir uniformemente en X e Y (circulo)
                    dist_xy = math.sqrt(x * x + y * y) + 1e-6
                    factor  = 1.0 + intensity * 0.4
                    co.x    = x * factor
                    co.y    = y * factor

                elif mode == "SQUINT":
                    # Aplanar verticalmente (Z o Y segun orientacion)
                    co.z = z * max(0.05, 1.0 - intensity * 0.7)

                elif mode == "WIDE":
                    # Expandir horizontalmente
                    co.x = x * (1.0 + intensity * 0.5)

                elif mode == "FLAT":
                    # Aplanar completamente (cerrar)
                    co.z = z * max(0.0, 1.0 - intensity)

                elif mode == "CUSTOM":
                    # Mantiene la forma basis; el usuario la edita manualmente
                    pass

                sk.data[i].co = co

            sk.value = min(1.0, intensity)
            modified += 1

        self.report({"INFO"}, f"Forma '{mode}' aplicada a {modified} objetos (shape key '{sk_name}')")
        return {"FINISHED"}


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRO
# ─────────────────────────────────────────────────────────────────────────────

classes = (
    CERDO_1_ST_OT_SaveEyeExpression,
    CERDO_1_ST_OT_RefreshEyeLibrary,
    CERDO_1_ST_OT_LoadEyeExpression,
    CERDO_1_ST_OT_ImportEyeExpression,
    CERDO_1_ST_OT_KeyframeEyeExpression,
    CERDO_1_ST_OT_OpenEyeLibFolder,
    CERDO_1_ST_OT_ResetEyeTransforms,
    CERDO_1_ST_OT_ApplyEyeTransforms,
    CERDO_1_ST_OT_ApplyEyeGeometry,
)
