# -*- coding: utf-8 -*-
"""
escena_ops.py -- Jerry Animation Studio: operadores y panel "Sonidos y camara (guion)" (fase 5 del plan). La logica esta en `sonidos_guion.py` y `camara_guion.py`.

  jerryst.snd_capturar    guarda en el guion los sonidos manuales de Alfred que hay en la escena (con sus tiempos relativos a las anclas cercanas)
  jerryst.snd_aplicar     crea / mueve / quita las tiras de sonido del guion (al mover una ancla o insertar tiempo, basta con volver a aplicar); opcionalmente pasa tambien el detector automatico (pasos, impactos)
  jerryst.cam_aplicar     escribe las claves y movimientos de camara del guion
  jerryst.cam_capturar    agrega al guion un movimiento de camara / foco hacia la posicion ACTUAL del objeto (colocalo a mano, elige desde / hasta y captura)
Las secciones `sonidos` y `camara` se guardan con "Guardar configuracion" del panel 5 (`guion_v2` las conserva).
"""
import re

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Operator, Panel

from . import audio_import as ai
from . import camara_guion as cg
from . import guion_v2 as gv
from . import sonidos_guion as sg


def _guion(context, crear=True):
    g = ai.guion_de_escena(context.scene)
    if g is None and crear: g = gv.nuevo("guion_de_la_escena", frame_ini=context.scene.frame_start, frame_fin=context.scene.frame_end)
    return g


def _tiempo(txt):
    t = (txt or "").strip()
    return None if not t else (int(t) if re.fullmatch(r"-?\d+", t) else t)


class JRRST_OT_SndCapturar(Operator):
    bl_idname = "jerryst.snd_capturar"
    bl_label = "Capturar sonidos"
    bl_description = "Guarda en el guion los sonidos manuales de Alfred que hay en la escena (sin los de otros personajes ni los automaticos), con tiempos relativos a las anclas cercanas"
    bl_options = {"REGISTER"}
    anclar: BoolProperty(name="Tiempos relativos a las anclas", default=True)

    def execute(self, context):
        if not context.scene.sequence_editor: self.report({"WARNING"}, "La escena no tiene editor de secuencias"); return {"CANCELLED"}
        g = _guion(context); g["sonidos"]["manuales"] = sg.capturar_sonidos(context); n = 0
        if self.anclar and g.get("anclas"): g, n = gv.anclar(g, 40, ("sonidos",))
        ai.guardar_en_escena(context.scene, g); self.report({"INFO"}, "%d sonidos guardados en el guion (%d con ancla)" % (len(g["sonidos"]["manuales"]), n)); return {"FINISHED"}


class JRRST_OT_SndAplicar(Operator):
    bl_idname = "jerryst.snd_aplicar"
    bl_label = "Aplicar sonidos"
    bl_description = "Crea, mueve y quita las tiras de sonido del guion segun sus anclas. Repetible"
    bl_options = {"REGISTER", "UNDO"}
    auto: BoolProperty(name="Tambien el detector automatico (pasos, impactos)", default=False, description="Llama a Sonidos MC (`mcsnd.sonorizar`, ~35 s)")

    def execute(self, context):
        g = _guion(context, crear=False)
        if not g or not (g.get("sonidos") or {}).get("manuales"): self.report({"WARNING"}, "El guion no tiene sonidos"); return {"CANCELLED"}
        r = sg.aplicar_sonidos(context, g, self.auto); self.report({"INFO"}, "Sonidos: %(creados)d creados, %(movidos)d movidos, %(iguales)d iguales, %(quitados)d quitados, %(adoptados)d adoptados" % r); return {"FINISHED"}


class JRRST_OT_CamAplicar(Operator):
    bl_idname = "jerryst.cam_aplicar"
    bl_label = "Aplicar camara"
    bl_description = "Escribe en la escena las claves y movimientos de camara del guion (sustituye a camara_final_parte3.py). Repetible"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        g = _guion(context, crear=False)
        if not g or not g.get("camara"): self.report({"WARNING"}, "El guion no tiene camara"); return {"CANCELLED"}
        try: r = cg.aplicar_camara(context, g)
        except (KeyError, ValueError, RuntimeError) as e: self.report({"ERROR"}, str(e)); return {"CANCELLED"}
        self.report({"INFO"}, "Camara: %d canales de claves, %d movimientos (%s)" % (r["claves"], r["movimientos"], ", ".join(r["objetos"]))); return {"FINISHED"}


class JRRST_OT_CamCapturar(Operator):
    bl_idname = "jerryst.cam_capturar"
    bl_label = "Capturar movimiento de camara"
    bl_description = "Agrega al guion un movimiento hacia la posicion ACTUAL del objeto: desde `desde` hasta `hasta` (frames o anclas). Coloca la camara / el foco a mano antes"
    bl_options = {"REGISTER"}
    objeto: StringProperty(name="Objeto", default="Camera.001")
    desde: StringProperty(name="Desde (frame o ancla)", default="")
    hasta: StringProperty(name="Hasta (frame o ancla)", default="")
    interp: EnumProperty(name="Interpolacion", items=[("smooth", "Suave", ""), ("linear", "Lineal", ""), ("constant", "Corte", "")], default="smooth")

    def invoke(self, context, event):
        if not self.desde: self.desde = str(context.scene.frame_current)
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        d, h = _tiempo(self.desde), _tiempo(self.hasta)
        if d is None or h is None: self.report({"ERROR"}, "Faltan `desde` y `hasta`"); return {"CANCELLED"}
        if self.objeto not in bpy.data.objects: self.report({"ERROR"}, "No existe %r" % self.objeto); return {"CANCELLED"}
        g = _guion(context); e = cg.capturar_movimiento(context, self.objeto, d, h, interp=self.interp); gv.agregar(g, "camara", e, id="cam_%s_%d" % (self.objeto, len(g["camara"]) + 1))
        r = gv.validar(g)["errores"]
        if r: g["camara"].pop(); self.report({"ERROR"}, r[0]); return {"CANCELLED"}
        ai.guardar_en_escena(context.scene, g); self.report({"INFO"}, "Movimiento de %s agregado al guion (%s -> %s)" % (self.objeto, d, h)); return {"FINISHED"}


class JRRST_PT_EscenaGuion(Panel):
    bl_label = "9  Sonidos y camara (guion)"
    bl_idname = "JRRST_PT_escena_guion"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Jerry Studio"
    bl_parent_id = "JRRST_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        lay = self.layout; g = ai.guion_de_escena(context.scene); box = lay.box()
        man = ((g or {}).get("sonidos") or {}).get("manuales") or []; cam = (g or {}).get("camara") or []
        box.label(text="Sonidos manuales: %d (modo %s)" % (len(man), ((g or {}).get("sonidos") or {}).get("modo", "auto")), icon="SPEAKER")
        box.label(text="Camara: %d claves de canal, %d movimientos" % (sum(1 for c in cam if c.get("tipo") == "claves"), sum(1 for c in cam if c.get("tipo", "movimiento") == "movimiento")), icon="CAMERA_DATA")
        r = lay.row(align=True); r.operator("jerryst.snd_capturar", icon="IMPORT"); r.operator("jerryst.snd_aplicar", icon="FILE_REFRESH")
        r = lay.row(align=True); r.operator("jerryst.cam_capturar", icon="IMPORT"); r.operator("jerryst.cam_aplicar", icon="FILE_REFRESH")
