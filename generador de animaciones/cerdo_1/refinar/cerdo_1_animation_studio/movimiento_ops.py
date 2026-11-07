# -*- coding: utf-8 -*-
"""
movimiento_ops.py -- Cerdo_1 Animation Studio: operadores y panel "Movimiento (tramos)" (fase 4 del plan). La logica esta en `motor_cerdo_1.py`.

  cerdo_1_st.mov_comparar   genera el movimiento de un tramo desde el guion y lo compara con la referencia numerica y con lo que evalua Blender (no cambia la escena)
  cerdo_1_st.mov_hornear    escribe en el rig de Cerdo_1 las claves de ese tramo (en la accion donde ya estan las del generador; no toca ningun otro frame)
  cerdo_1_st.mov_aprobar    marca el tramo como "aprobado" en el guion (solo cuando el usuario lo confirma: una animacion es una primera version hasta que el usuario la aprueba)
Los tramos viven en `movimiento.tramos` del guion 2.0 (se guardan con "Guardar configuracion" del panel 5).
"""
import time

import bpy
from bpy.props import BoolProperty, StringProperty
from bpy.types import Operator, Panel

from . import audio_import as ai
from . import guion_v2 as gv
from . import motor_cerdo_1 as ma


def _guion(context):
    g = ai.guion_de_escena(context.scene)
    return g if g is not None and (g.get("movimiento") or {}).get("tramos") else None


def _tramo(g, tid):
    return next((t for t in g["movimiento"]["tramos"] if t["id"] == tid), None)


class CERDO_1_ST_OT_MovComparar(Operator):
    bl_idname = "cerdo_1_st.mov_comparar"
    bl_label = "Comparar tramo"
    bl_description = "Genera el tramo desde el guion y lo compara con la referencia numerica y con lo que evalua Blender (sin voces). No cambia la escena"
    bl_options = {"REGISTER"}
    tramo: StringProperty(default="", options={"HIDDEN"})

    def execute(self, context):
        g = _guion(context)
        if not g: self.report({"WARNING"}, "El guion no tiene tramos de movimiento"); return {"CANCELLED"}
        d = gv.desplegar(g); trs = [t for t in ma.tramos_de(d) if not self.tramo or t["id"] == self.tramo]
        res = ma.generar(g); ref = ma.cargar_referencia(g["movimiento"]["referencia_numerica"]); msgs = []
        for t in trs:
            c = ma.comparar(res, ref, (t["inicio"], t["fin"])); b = ma.verificar_en_blender(context, res, range(t["inicio"], t["fin"] + 1))
            msgs.append("%s f%d-%d: vs referencia rot %.5f grados, root %.2g m | vs Blender rot %.5f grados" % (t["id"], t["inicio"], t["fin"], c["final_rot_deg"], c["root_m"], b["rot_deg"]))
        for m in msgs: print("[movimiento]", m)
        self.report({"INFO"}, " || ".join(msgs)); return {"FINISHED"}


class CERDO_1_ST_OT_MovHornear(Operator):
    bl_idname = "cerdo_1_st.mov_hornear"
    bl_label = "Hornear tramo"
    bl_description = "Escribe en el rig de Cerdo_1 las claves del tramo (en la accion donde ya estan las del generador; no toca ningun otro frame ni crea una accion que tape el NLA)"
    bl_options = {"REGISTER", "UNDO"}
    tramo: StringProperty(default="", options={"HIDDEN"})

    def execute(self, context):
        g = _guion(context)
        if not g: self.report({"WARNING"}, "El guion no tiene tramos de movimiento"); return {"CANCELLED"}
        d = gv.desplegar(g); trs = [t for t in ma.tramos_de(d) if not self.tramo or t["id"] == self.tramo]; res = ma.generar(g); t0 = time.time(); n = 0
        for t in trs: n += ma.hornear(context, res, range(t["inicio"], t["fin"] + 1))
        b = [ma.verificar_en_blender(context, res, range(t["inicio"], t["fin"] + 1))["rot_deg"] for t in trs]
        self.report({"INFO"}, "Horneados %d frames (%s) en %.1f s | Blender evalua lo mismo que el motor: dif max %.5f grados" % (n, ", ".join(t["id"] for t in trs), time.time() - t0, max(b))); return {"FINISHED"}


class CERDO_1_ST_OT_MovAprobar(Operator):
    bl_idname = "cerdo_1_st.mov_aprobar"
    bl_label = "Marcar aprobado"
    bl_description = "Marca el tramo como aprobado en el guion (hazlo solo cuando lo hayas revisado)"
    bl_options = {"REGISTER"}
    tramo: StringProperty(default="", options={"HIDDEN"})
    aprobado: BoolProperty(default=True, options={"HIDDEN"})

    def execute(self, context):
        g = _guion(context); t = _tramo(g, self.tramo) if g else None
        if t is None: return {"CANCELLED"}
        t["estado"] = "aprobado" if self.aprobado else "sin aprobar"; ai.guardar_en_escena(context.scene, g); self.report({"INFO"}, "%s: %s" % (t["id"], t["estado"])); return {"FINISHED"}


class CERDO_1_ST_PT_Movimiento(Panel):
    bl_label = "8  Movimiento (tramos)"
    bl_idname = "CERDO_1_ST_PT_movimiento"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cerdo_1 Studio"
    bl_parent_id = "CERDO_1_ST_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        lay = self.layout; g = _guion(context); box = lay.box()
        if not g: box.label(text="Sin tramos de movimiento en el guion", icon="INFO"); return
        try: an = gv.resolver_anclas(g)
        except ValueError as e: box.label(text=str(e), icon="ERROR"); return
        for t in g["movimiento"]["tramos"]:
            r = box.row(align=True); apr = t.get("estado") == "aprobado"
            r.label(text="%s  f%d-%d  %s" % (t["id"], gv.frame_de(t["inicio"], an), gv.frame_de(t["fin"], an), "aprobado" if apr else "sin aprobar"), icon="CHECKMARK" if apr else "DOT")
            o = r.operator("cerdo_1_st.mov_comparar", text="", icon="VIEWZOOM"); o.tramo = t["id"]
            o = r.operator("cerdo_1_st.mov_hornear", text="", icon="PLAY"); o.tramo = t["id"]
            o = r.operator("cerdo_1_st.mov_aprobar", text="", icon="CHECKBOX_HLT" if not apr else "CHECKBOX_DEHLT"); o.tramo = t["id"]; o.aprobado = not apr
        lay.label(text="Los frames sin tramo siguen saliendo de la referencia", icon="INFO")
