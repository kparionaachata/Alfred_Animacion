# -*- coding: utf-8 -*-
"""
config_ops.py — Rat 1 Animation Studio

Guardar / cargar el recorrido grabado (Paso 1+2) a/desde un JSON, siguiendo
la convencion de nombres "escenario_*" del pipeline (escenario_registro.json).

_serialize_path()/_deserialize_path() tambien las reutiliza
RAT1SEG_OT_SaveConfig/LoadConfig (operators_segments.py, Paso 3): la
configuracion completa que expone el panel "Guardar / Importar
Configuracion" junta Paso 1+2 (estas funciones) + Paso 3 (segmentos,
poses, bloqueador de bones -- ver _SEG_SCALAR_ATTRS en
operators_segments.py) en un unico .json, para que UNA sola accion
restaure la sesion de trabajo completa (mismo criterio que
ALFST_OT_SaveConfig/LoadConfig en alfred_animation_studio).
"""

import bpy
import json
import os
from bpy.types import Operator
from bpy.props import StringProperty


def _serialize_path(pc):
    return {
        "personaje": "rat_1",
        "puntos": [
            {
                "coords": list(pt.coords),
                "texture": pt.texture,
                "face_index": pt.face_index,
                "tipo_segmento": pt.tipo_segmento,
                "parada_frames_punto": pt.parada_frames_punto,
            }
            for pt in pc.path_points
        ],
        "slot_inicio": pc.slot_inicio,
        "frame_inicio": pc.frame_inicio,
        "frame_fin_manual": pc.frame_fin_manual,
        "frames_por_unidad": pc.frames_por_unidad,
        "frames_parada": pc.frames_parada,
        "root_rot": [pc.root_rot_x, pc.root_rot_y, pc.root_rot_z],
        "walk_styles": [{"style": w.style} for w in pc.walk_styles],
        "output_dir": pc.output_dir,
        "blend_filepath": pc.blend_filepath,
    }


def _deserialize_path(pc, data):
    """Restaura en 'pc' (scene.rat1_path) los datos de Paso 1+2 producidos
    por _serialize_path(). Comparte logica con RAT1ST_OT_LoadConfig.execute()
    y con RAT1SEG_OT_LoadConfig (operators_segments.py, Paso 3), para que
    ambos puntos de entrada (recorrido solo, o configuracion completa
    Paso 1-3) restauren el recorrido exactamente igual."""
    pc.path_points.clear()
    for p in data.get("puntos", []):
        pt = pc.path_points.add()
        pt.coords = p.get("coords", (0.0, 0.0, 0.0))
        pt.texture = p.get("texture", "")
        pt.face_index = p.get("face_index", "")
        pt.tipo_segmento = p.get("tipo_segmento", "AUTO")
        pt.parada_frames_punto = p.get("parada_frames_punto", 24)

    pc.slot_inicio        = data.get("slot_inicio", pc.slot_inicio)
    pc.frame_inicio       = data.get("frame_inicio", pc.frame_inicio)
    pc.frame_fin_manual   = data.get("frame_fin_manual", pc.frame_fin_manual)
    pc.frames_por_unidad  = data.get("frames_por_unidad", pc.frames_por_unidad)
    pc.frames_parada      = data.get("frames_parada", pc.frames_parada)
    rr = data.get("root_rot", [pc.root_rot_x, pc.root_rot_y, pc.root_rot_z])
    pc.root_rot_x, pc.root_rot_y, pc.root_rot_z = rr
    pc.output_dir         = data.get("output_dir", pc.output_dir)
    pc.blend_filepath     = data.get("blend_filepath", pc.blend_filepath)

    from .path_recorder import sync_paradas_frames, sync_walk_styles
    sync_paradas_frames(pc)
    sync_walk_styles(pc)
    for i, w in enumerate(data.get("walk_styles", [])):
        if i < len(pc.walk_styles):
            pc.walk_styles[i].style = w.get("style", "NORMAL")

    return len(pc.path_points)


class RAT1ST_OT_SaveConfig(Operator):
    """Guarda el recorrido grabado en escenario_registro.json."""
    bl_idname  = "rat1st.save_config"
    bl_label   = "Guardar recorrido (escenario_registro.json)"
    bl_options = {"REGISTER"}

    filepath: StringProperty(subtype="FILE_PATH", default="escenario_registro.json")

    def execute(self, context):
        pc = context.scene.rat1_path
        data = _serialize_path(pc)
        path = bpy.path.abspath(self.filepath)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.report({"INFO"}, f"Recorrido guardado en {path}")
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class RAT1ST_OT_LoadConfig(Operator):
    """Carga un recorrido previamente guardado con RAT1ST_OT_SaveConfig."""
    bl_idname  = "rat1st.load_config"
    bl_label   = "Cargar recorrido (escenario_registro.json)"
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        path = bpy.path.abspath(self.filepath)
        if not os.path.isfile(path):
            self.report({"ERROR"}, f"No se encontro {path}")
            return {"CANCELLED"}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        pc = context.scene.rat1_path
        n_pts = _deserialize_path(pc, data)

        self.report({"INFO"}, f"Recorrido cargado desde {path} ({n_pts} puntos)")
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
