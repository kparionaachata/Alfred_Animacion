# -*- coding: utf-8 -*-
"""
tunel_ops.py -- Alfred Animation Studio: panel "10  Tunel (cavar)". La logica esta en `tunel.py`.

  alfst.tunel_crear      crea el tunel y la animacion de Alfred de la coordenada de INICIO a la FINAL (pala en tierra, pico en piedra, caras / paredes / piso / techo automaticos)
  alfst.tunel_quitar     lo deshace (devuelve las caras originales del mundo, quita objetos y acciones `tunel_*`)
  alfst.tunel_cursor     copia la posicion del cursor 3D a inicio / final
Las coordenadas son de mundo (z = piso donde para Alfred). Escribe las anclas `tunel_inicio` / `tunel_fin` en el guion de la escena (si hay uno).
"""
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup

from . import tunel as tn


class AlfredTunelSettings(PropertyGroup):
    inicio: FloatVectorProperty(name="Inicio", size=3, default=(0.0, 0.0, 0.0), precision=2, subtype='XYZ', description="Coordenada de inicio (donde para Alfred; z = piso)")
    final: FloatVectorProperty(name="Final", size=3, default=(0.0, 0.0, 0.0), precision=2, subtype='XYZ', description="Coordenada final (donde termina de cavar; z = piso)")
    frame_ini: IntProperty(name="Frame de inicio", default=1, min=1)
    alto: IntProperty(name="Alto del tunel", default=3, min=2, max=6, description="Bloques de alto desde el piso (Alfred mide ~2.1)")
    cascaron: BoolProperty(name="Rellenar piso / paredes / techo", default=True, description="Pone bloques de tierra y piedra donde la cueva no tiene superficie")
    pct_piedra: FloatProperty(name="% piedra en paredes", default=0.5, min=0.0, max=1.0)
    final_abierto: IntProperty(name="Celdas finales abiertas", default=2, min=0, max=6, description="Las ultimas celdas no llevan tapon hacia delante (el tunel desemboca en la cueva)")
    final_sin_bloques: IntProperty(name="Celdas finales sin bloques nuevos", default=0, min=0, max=30, description="Al llegar al final del recorrido no se generan mas bloques: Alfred solo rompe los que tiene delante")
    pala: StringProperty(name="Pala", default="stone_shovel")
    pico: StringProperty(name="Pico", default="stone_pickaxe")


def _cfg(s):
    return dict(frame_ini=s.frame_ini, alto=s.alto, cascaron=s.cascaron, pct_piedra=s.pct_piedra, final_abierto=s.final_abierto, final_sin_bloques=s.final_sin_bloques, pala=s.pala, pico=s.pico)


class ALFST_OT_TunelCrear(Operator):
    bl_idname = "alfst.tunel_crear"
    bl_label = "Crear tunel"
    bl_description = "Alfred cava / pica un tunel recto de la coordenada de inicio a la final: animacion (pala / pico), caras, paredes, piso y techo. Repetible (rehace el tunel)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene.alfst_tunel
        try: r = tn.crear(context, tuple(s.inicio), tuple(s.final), **_cfg(s))
        except Exception as e:
            self.report({"ERROR"}, "Tunel: %s" % e); return {"CANCELLED"}
        self.report({"INFO"}, "Tunel f%d-f%d: %d golpes, %d celdas cavadas, %d objetos" % (s.frame_ini, r["frame_fin"], r["golpes"], r["celdas_cavadas"], r["objetos"]))
        return {"FINISHED"}


class ALFST_OT_TunelQuitar(Operator):
    bl_idname = "alfst.tunel_quitar"
    bl_label = "Quitar tunel"
    bl_description = "Deshace el tunel: devuelve las caras originales del mundo y quita los objetos y las acciones `tunel_*`"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        n = tn.quitar(context.scene); self.report({"INFO"}, "Tunel quitado (%d caras devueltas al mundo)" % n); return {"FINISHED"}


class ALFST_OT_TunelCursor(Operator):
    bl_idname = "alfst.tunel_cursor"
    bl_label = "Cursor 3D"
    bl_description = "Copia la posicion del cursor 3D a la coordenada de inicio o a la final"
    bl_options = {"REGISTER"}
    destino: EnumProperty(name="Destino", items=[("inicio", "Inicio", ""), ("final", "Final", "")], default="inicio")

    def execute(self, context):
        s = context.scene.alfst_tunel; setattr(s, self.destino, tuple(context.scene.cursor.location)); return {"FINISHED"}


class ALFST_PT_Tunel(Panel):
    bl_label = "10  Tunel (cavar)"
    bl_idname = "ALFST_PT_tunel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Alfred Studio"
    bl_parent_id = "ALFST_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        lay = self.layout; s = context.scene.alfst_tunel
        b = lay.box(); b.label(text="Coordenadas (z = piso)", icon="CURVE_PATH")
        r = b.row(align=True); r.prop(s, "inicio", text="Inicio"); r.operator("alfst.tunel_cursor", text="", icon="CURSOR").destino = "inicio"
        r = b.row(align=True); r.prop(s, "final", text="Final"); r.operator("alfst.tunel_cursor", text="", icon="CURSOR").destino = "final"
        c = lay.column(align=True); c.prop(s, "frame_ini"); c.prop(s, "alto"); c.prop(s, "cascaron"); c.prop(s, "pct_piedra", slider=True); c.prop(s, "final_abierto"); c.prop(s, "final_sin_bloques")
        c = lay.column(align=True); c.prop(s, "pala"); c.prop(s, "pico")
        r = lay.row(align=True); r.scale_y = 1.3; r.operator("alfst.tunel_crear", icon="MOD_BUILD"); r.operator("alfst.tunel_quitar", icon="TRASH")
        u = context.scene.get("alfst_tunel_ultimo")
        if u: lay.label(text="Ultimo: " + u[:70], icon="INFO")


clases = (AlfredTunelSettings, ALFST_OT_TunelCrear, ALFST_OT_TunelQuitar, ALFST_OT_TunelCursor, ALFST_PT_Tunel)


def register_tunel():
    for c in clases:
        try: bpy.utils.unregister_class(c)
        except RuntimeError: pass
        bpy.utils.register_class(c)
    bpy.types.Scene.alfst_tunel = PointerProperty(type=AlfredTunelSettings)


def unregister_tunel():
    for c in reversed(clases):
        try: bpy.utils.unregister_class(c)
        except RuntimeError: pass
    if hasattr(bpy.types.Scene, "alfst_tunel"): del bpy.types.Scene.alfst_tunel
