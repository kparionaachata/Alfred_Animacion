# -*- coding: utf-8 -*-
"""
voz_rapida_ops.py -- Jerry Animation Studio: panel "Voz rapida de Jerry". La logica esta en `voz_rapida.py`.
  jrrst.voz_rapida_aplicar   audio (+ animacion_jerry (N).py de la app) en el frame de inicio: copia, volumen automatico, efecto, cara y ducking (repetible)
  jrrst.voz_rapida_quitar    quita una voz rapida (restaura las claves de la cara y borra sus tiras)
"""
import bpy, json
from bpy.props import EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty, BoolProperty
from bpy.types import Operator, Panel, PropertyGroup
from . import voz_rapida as vr


class JerryVozRapidaSettings(PropertyGroup):
    audio: StringProperty(name="Audio", subtype='FILE_PATH', description=".wav o .mp3 de la voz de Jerry")
    script: StringProperty(name="Cara (app)", subtype='FILE_PATH', description="animacion_jerry (N).py de la app estudio_audio_expresion (opcional)")
    inicio: IntProperty(name="Frame de inicio", default=1, min=1)
    tag: StringProperty(name="Nombre", default="", description="nombre corto de la voz (vacio = el del archivo)")
    modo: EnumProperty(name="Modo", items=[("normal", "Normal (cara de la app)", "Mandibula, hocico, cabeza, cejas y ojos del script de la app"),
                                           ("solo_audio", "Solo audio", "Mandibula con la envolvente del audio"),
                                           ("boca_ocupada", "Boca ocupada", "No abre la boca: tiembla la mandibula y cabecea (voz ahogada)"),
                                           ("boca_cerrada_cara", "Boca cerrada + cara", "Cejas y ojos de la app con la boca cerrada")], default="normal")
    efecto: EnumProperty(name="Efecto", items=[("ninguno", "Ninguno", ""), ("boca_ocupada", "Boca ocupada (suave)", ""), ("boca_ocupada_fuerte", "Boca ocupada (fuerte)", "")], default="ninguno")
    auto_vol: BoolProperty(name="Volumen automatico", default=True)
    vol: FloatProperty(name="Volumen", default=2.0, min=0.0, max=5.0)
    quitar_tag: StringProperty(name="Voz a quitar", default="")


class JRRST_OT_VozRapidaAplicar(Operator):
    bl_idname = "jrrst.voz_rapida_aplicar"; bl_label = "Poner voz"; bl_options = {"REGISTER", "UNDO"}
    bl_description = "Pone la voz de Jerry en el frame de inicio con su animacion de cara (repetible)"
    def execute(self, context):
        s = context.scene.jrrst_voz
        if not s.audio: self.report({"ERROR"}, "Falta el audio"); return {"CANCELLED"}
        try: r = vr.aplicar(context, bpy.path.abspath(s.audio), s.inicio, bpy.path.abspath(s.script) if s.script else None, s.tag or None, s.modo, None if s.auto_vol else s.vol, s.efecto)
        except Exception as e: self.report({"ERROR"}, "Voz: %s" % e); return {"CANCELLED"}
        self.report({"INFO"}, "Voz '%s' (%s) f%d-%d, volumen %.2f" % (r["tag"], r["modo"], r["inicio"], r["fin"], r["vol"])); return {"FINISHED"}


class JRRST_OT_VozRapidaQuitar(Operator):
    bl_idname = "jrrst.voz_rapida_quitar"; bl_label = "Quitar voz"; bl_options = {"REGISTER", "UNDO"}
    def execute(self, context):
        t = context.scene.jrrst_voz.quitar_tag; n = vr.quitar(context, t); self.report({"INFO"}, "Voz '%s' quitada (%d tiras)" % (t, n)); return {"FINISHED"}


class JRRST_PT_VozRapida(Panel):
    bl_label = "Voz rapida de Jerry"; bl_idname = "JRRST_PT_voz_rapida"; bl_space_type = "VIEW_3D"; bl_region_type = "UI"; bl_category = "Jerry Studio"; bl_parent_id = "JRRST_PT_main"; bl_options = {"DEFAULT_CLOSED"}
    def draw(self, context):
        s = context.scene.jrrst_voz; l = self.layout; c = l.column(align=True)
        for p in ("audio", "script", "inicio", "tag", "modo", "efecto", "auto_vol"): c.prop(s, p)
        if not s.auto_vol: c.prop(s, "vol")
        r = l.row(); r.scale_y = 1.3; r.operator("jrrst.voz_rapida_aplicar", icon="SPEAKER")
        try: R = json.loads(context.scene.get("jerry_voces_rapidas", "{}"))
        except Exception: R = {}
        if R:
            b = l.box(); b.label(text="Voces puestas:")
            for t, v in R.items(): b.label(text="%s  f%d  %s  vol %.2f" % (t, v["inicio"], v["modo"], v["vol"]))
            r = l.row(align=True); r.prop(s, "quitar_tag", text=""); r.operator("jrrst.voz_rapida_quitar", icon="TRASH")


clases = (JerryVozRapidaSettings, JRRST_OT_VozRapidaAplicar, JRRST_OT_VozRapidaQuitar, JRRST_PT_VozRapida)


def register_voz_rapida():
    for c in clases:
        try: bpy.utils.unregister_class(c)
        except RuntimeError: pass
        bpy.utils.register_class(c)
    bpy.types.Scene.jrrst_voz = PointerProperty(type=JerryVozRapidaSettings)


def unregister_voz_rapida():
    for c in reversed(clases):
        try: bpy.utils.unregister_class(c)
        except RuntimeError: pass
    if hasattr(bpy.types.Scene, "jrrst_voz"): del bpy.types.Scene.jrrst_voz
