# -*- coding: utf-8 -*-
"""
tunel_jerry_ops.py -- Jerry Animation Studio: panel "Tunel (picar)". La logica esta en `tunel_jerry.py`.

  jrrst.tunel_crear      Jerry (1x1 m) recoge un pico de piedra con la boca y pica su tunel de la coordenada de INICIO a la FINAL; llega a la final en el "Frame de llegada"
  jrrst.tunel_quitar     lo deshace (devuelve las caras originales del mundo, quita los objetos `tunel_jerry_*` y las acciones `tjerry_*`)
  jrrst.tunel_cursor     copia la posicion del cursor 3D a inicio / final
Las coordenadas son de mundo (z = piso donde para Jerry). Crear primero el tunel de Alfred (si lo hay) y despues este: no pone bloques donde ya hay uno del tunel de Alfred.
"""
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup

from . import tunel_jerry as tn


class JerryTunelSettings(PropertyGroup):
    inicio: FloatVectorProperty(name="Inicio", size=3, default=(-110.5, -71.5, 12.0), precision=2, subtype='XYZ', description="Coordenada de inicio (z = piso)")
    final: FloatVectorProperty(name="Final", size=3, default=(-131.5, -71.5, 10.0), precision=2, subtype='XYZ', description="Coordenada final: Jerry llega aqui en el frame de llegada (z = piso)")
    frame_ini: IntProperty(name="Frame de inicio", default=1, min=1)
    frame_llegada: IntProperty(name="Frame de llegada", default=1900, min=2, description="Frame en que Jerry llega a la coordenada final (las pausas entre bloques se reparten para cumplirlo)")
    alto: IntProperty(name="Alto del tunel", default=1, min=1, max=3, description="Bloques de alto desde el piso (Jerry mide ~0.8 m)")
    columnas_extra: IntProperty(name="Columnas tras el final", default=1, min=0, max=3, description="Columnas que se cavan MAS ALLA de la final (el cuerpo de Jerry mide 1.47 m: el hocico no entra en la roca)")
    cascaron: BoolProperty(name="Rellenar piso / paredes / techo", default=True)
    pico: StringProperty(name="Pico", default="stone_pickaxe", description="Objeto del pico de piedra que se copia para la boca de Jerry")
    escala_pico: FloatProperty(name="Escala del pico", default=0.6, min=0.1, max=1.5)


def _cfg(s):
    return dict(frame_ini=s.frame_ini, frame_llegada=s.frame_llegada, alto=s.alto, columnas_extra=s.columnas_extra, cascaron=s.cascaron, pico=s.pico, escala_pico=s.escala_pico)


class JRRST_OT_TunelCrear(Operator):
    bl_idname = "jrrst.tunel_crear"
    bl_label = "Crear tunel"
    bl_description = "Jerry recoge el pico con la boca y pica un tunel recto de 1x1 m de la coordenada de inicio a la final. Repetible (rehace el tunel)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene.jrrst_tunel
        try: r = tn.crear(context, tuple(s.inicio), tuple(s.final), **_cfg(s))
        except Exception as e:
            self.report({"ERROR"}, "Tunel de Jerry: %s" % e); return {"CANCELLED"}
        self.report({"INFO"}, "Tunel de Jerry: llega en f%d (objetivo f%d), %d bloques, %d golpes, %d colisiones" % (r["llegada"], r["objetivo"], r["bloques_picados"], r["golpes"], r["colisiones"]["frames"]))
        return {"FINISHED"}


class JRRST_OT_TunelQuitar(Operator):
    bl_idname = "jrrst.tunel_quitar"
    bl_label = "Quitar tunel"
    bl_description = "Deshace el tunel de Jerry: devuelve las caras originales del mundo y quita los objetos `tunel_jerry_*` y las acciones `tjerry_*`"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        n = tn.quitar(context.scene); self.report({"INFO"}, "Tunel de Jerry quitado (%d caras devueltas al mundo)" % n); return {"FINISHED"}


class JRRST_OT_TunelCursor(Operator):
    bl_idname = "jrrst.tunel_cursor"
    bl_label = "Cursor 3D"
    bl_description = "Copia la posicion del cursor 3D a la coordenada de inicio o a la final"
    bl_options = {"REGISTER"}
    destino: EnumProperty(name="Destino", items=[("inicio", "Inicio", ""), ("final", "Final", "")], default="inicio")

    def execute(self, context):
        s = context.scene.jrrst_tunel; setattr(s, self.destino, tuple(context.scene.cursor.location)); return {"FINISHED"}


class JRRST_PT_Tunel(Panel):
    bl_label = "Tunel (picar)"
    bl_idname = "JRRST_PT_tunel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Jerry Studio"
    bl_parent_id = "JRRST_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        lay = self.layout; s = context.scene.jrrst_tunel
        b = lay.box(); b.label(text="Coordenadas (z = piso)", icon="CURVE_PATH")
        r = b.row(align=True); r.prop(s, "inicio", text="Inicio"); r.operator("jrrst.tunel_cursor", text="", icon="CURSOR").destino = "inicio"
        r = b.row(align=True); r.prop(s, "final", text="Final"); r.operator("jrrst.tunel_cursor", text="", icon="CURSOR").destino = "final"
        c = lay.column(align=True); c.prop(s, "frame_ini"); c.prop(s, "frame_llegada"); c.prop(s, "alto"); c.prop(s, "columnas_extra"); c.prop(s, "cascaron")
        c = lay.column(align=True); c.prop(s, "pico"); c.prop(s, "escala_pico")
        r = lay.row(align=True); r.scale_y = 1.3; r.operator("jrrst.tunel_crear", icon="MOD_BUILD"); r.operator("jrrst.tunel_quitar", icon="TRASH")
        u = context.scene.get("jrrst_tunel_ultimo")
        if u: lay.label(text="Ultimo: " + u[:70], icon="INFO")


clases = (JerryTunelSettings, JRRST_OT_TunelCrear, JRRST_OT_TunelQuitar, JRRST_OT_TunelCursor, JRRST_PT_Tunel)


def register_tunel_jerry():
    for c in clases:
        try: bpy.utils.unregister_class(c)
        except RuntimeError: pass
        bpy.utils.register_class(c)
    bpy.types.Scene.jrrst_tunel = PointerProperty(type=JerryTunelSettings)


def unregister_tunel_jerry():
    for c in reversed(clases):
        try: bpy.utils.unregister_class(c)
        except RuntimeError: pass
    if hasattr(bpy.types.Scene, "jrrst_tunel"): del bpy.types.Scene.jrrst_tunel
