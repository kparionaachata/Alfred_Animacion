# -*- coding: utf-8 -*-
"""
objetos_ops.py -- Jerry Animation Studio: operadores y panel "Objetos y mundo" (fase 3 del plan). La logica esta en `objetos_mundo.py`.

  jerryst.obj_capturar_agarre   guarda en el guion el AGARRE de un objeto: su posicion actual (frame actual) respecto al hueso de la mano (se coloca el objeto a mano y se captura)
  jerryst.obj_capturar_espalda  guarda su SITIO EN LA ESPALDA (su posicion actual respecto a Spine1)
  jerryst.obj_aplicar           calcula los eventos de objetos / mundo del guion, los compara con la escena y (si se pide) los hornea como keyframes; los cambios de visibilidad del mundo tambien
Los objetos y el mundo viven en las secciones `objetos` / `mundo` del guion 2.0 (se guardan con "Guardar configuracion" del panel 5).
"""
import bpy
from bpy.props import BoolProperty, StringProperty
from bpy.types import Operator, Panel

from . import audio_import as ai
from . import guion_v2 as gv
from . import objetos_mundo as om


def _guion(context):
    g = ai.guion_de_escena(context.scene)
    return g if g is not None else gv.nuevo("guion_de_la_escena", frame_ini=context.scene.frame_start, frame_fin=context.scene.frame_end)


def _entrada(g, nombre):
    e = next((o for o in g["objetos"] if o.get("nombre") == nombre), None)
    if e is None: e = gv.agregar(g, "objetos", {"nombre": nombre, "armature": "Dog_001_rig", "hueso": "front_foot.R", "agarres": {}, "eventos": []}, id="obj_" + nombre)
    return e


class JRRST_OT_ObjCapturarAgarre(Operator):
    bl_idname = "jerryst.obj_capturar_agarre"
    bl_label = "Capturar agarre"
    bl_description = "Guarda en el guion el agarre del objeto: su posicion actual (en el frame actual) respecto al hueso de la mano"
    bl_options = {"REGISTER"}
    objeto: StringProperty(name="Objeto", default="", description="Vacio = el objeto activo")
    agarre: StringProperty(name="Nombre del agarre", default="mano")
    armature: StringProperty(name="Armature", default="Dog_001_rig")
    hueso: StringProperty(name="Hueso de la mano", default="front_foot.R")

    def invoke(self, context, event):
        if not self.objeto and context.active_object: self.objeto = context.active_object.name
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        ob = bpy.data.objects.get(self.objeto)
        if ob is None: self.report({"ERROR"}, "No existe el objeto %r" % self.objeto); return {"CANCELLED"}
        g = _guion(context); e = _entrada(g, ob.name); e["armature"] = self.armature; e["hueso"] = self.hueso
        e.setdefault("agarres", {})[self.agarre] = {"matriz": om.capturar_agarre(ob, self.armature, self.hueso), "origen": "capturado en f%d" % context.scene.frame_current}
        ai.guardar_en_escena(context.scene, g); self.report({"INFO"}, "Agarre %r de %s guardado (f%d)" % (self.agarre, ob.name, context.scene.frame_current)); return {"FINISHED"}


class JRRST_OT_ObjCapturarEspalda(Operator):
    bl_idname = "jerryst.obj_capturar_espalda"
    bl_label = "Capturar espalda"
    bl_description = "Guarda en el guion el sitio del objeto en la espalda: su posicion actual (en el frame actual) respecto a Spine1"
    bl_options = {"REGISTER"}
    objeto: StringProperty(name="Objeto", default="", description="Vacio = el objeto activo")
    armature: StringProperty(name="Armature", default="Dog_001_rig")
    hueso: StringProperty(name="Hueso", default="spine_3")

    def invoke(self, context, event):
        if not self.objeto and context.active_object: self.objeto = context.active_object.name
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        ob = bpy.data.objects.get(self.objeto)
        if ob is None: self.report({"ERROR"}, "No existe el objeto %r" % self.objeto); return {"CANCELLED"}
        g = _guion(context); e = _entrada(g, ob.name); esp = om.capturar_espalda(ob, self.hueso, self.armature, context.scene.frame_current); esp["armature"] = self.armature; esp["origen"] = "capturado en f%d" % context.scene.frame_current
        e["espalda"] = esp; ai.guardar_en_escena(context.scene, g); self.report({"INFO"}, "Espalda de %s guardada (f%d)" % (ob.name, context.scene.frame_current)); return {"FINISHED"}


class JRRST_OT_ObjAplicar(Operator):
    bl_idname = "jerryst.obj_aplicar"
    bl_label = "Aplicar objetos y mundo"
    bl_description = "Calcula los eventos de objetos y mundo del guion, los compara con la escena y los hornea como keyframes. Tarda ~40 s (evalua los frames de la escena)"
    bl_options = {"REGISTER"}
    solo_comparar: BoolProperty(name="Solo comparar (no cambiar la escena)", default=True)
    objeto: StringProperty(name="Solo este objeto (vacio = todos)", default="")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=420)

    def execute(self, context):
        g = ai.guion_de_escena(context.scene)
        if not g or not (g.get("objetos") or g.get("mundo")): self.report({"WARNING"}, "El guion no tiene objetos ni mundo"); return {"CANCELLED"}
        solo = [self.objeto] if self.objeto else None
        res = om.calcular(context, g, objetos=solo); cmp = om.comparar(res)
        for n, c in cmp.items(): print("[objetos_mundo]", n, c)
        txt = " | ".join("%s %s%.1f cm" % (n, "OK " if c["ok"] else "", c["loc_cm"]) for n, c in cmp.items())
        if not self.solo_comparar:
            n = om.aplicar(context, res); vis = om.aplicar_mundo_visibilidad(context, g); self.report({"INFO"}, "Horneados %d objetos, visibilidad de %s | %s" % (n, vis, txt))
        else: self.report({"INFO"}, "Comparacion con la escena (sin cambiar nada): " + txt)
        return {"FINISHED"}


class JRRST_PT_Objetos(Panel):
    bl_label = "7  Objetos y mundo (guion)"
    bl_idname = "JRRST_PT_objetos"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Jerry Studio"
    bl_parent_id = "JRRST_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        lay = self.layout; g = ai.guion_de_escena(context.scene); box = lay.box()
        objs = (g or {}).get("objetos") or []; mun = (g or {}).get("mundo") or []
        if not objs and not mun: box.label(text="Sin objetos ni mundo en el guion", icon="INFO")
        for o in objs: box.label(text="%s: %d eventos, %d agarres%s" % (o.get("nombre"), len(o.get("eventos") or []), len(o.get("agarres") or {}), ", espalda" if o.get("espalda") else ""), icon="OBJECT_DATA")
        if mun: box.label(text="Mundo: " + ", ".join(m.get("accion", "?") + ":" + str(m.get("objeto", "")) for m in mun)[:70], icon="WORLD")
        r = lay.row(align=True); r.operator("jerryst.obj_capturar_agarre", icon="HAND"); r.operator("jerryst.obj_capturar_espalda", icon="ARMATURE_DATA")
        lay.operator("jerryst.obj_aplicar", icon="PLAY")
