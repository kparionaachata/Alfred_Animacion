# -*- coding: utf-8 -*-
"""
reproducir_ops.py -- Cerdo_1 Animation Studio: operador y panel "Reproducir guion" (fase 6 del plan). La logica esta en `reproducir_guion.py`.

  cerdo_1_st.guion_reproducir   aplica el guion 2.0 cargado en la escena: crea los objetos que falten, hornea a Cerdo_1, sincroniza las voces, anima objetos y mundo, coloca los sonidos y la camara.
                           Se puede elegir que pasos. Tarda ~2-3 minutos (evalua los frames de la escena). Si hay un guion en el disco (`configuraciones/guion_cerdo_1_parte3.json`), "Cargar guion" lo trae a la escena.
  cerdo_1_st.guion_cargar_archivo  carga un guion 2.0 desde un .json a la escena (sin tocar la animacion)
"""
import os

import bpy
from bpy.props import BoolProperty, StringProperty
from bpy.types import Operator, Panel

from . import audio_import as ai
from . import guion_v2 as gv
from . import reproducir_guion as rg

RUTA_GUION = os.path.join(ai.RAIZ, "generador de animaciones", "cerdo_1", "refinar", "configuraciones", "guion_cerdo_1_parte3.json")


class CERDO_1_ST_OT_GuionCargarArchivo(Operator):
    bl_idname = "cerdo_1_st.guion_cargar_archivo"
    bl_label = "Cargar guion (.json)"
    bl_description = "Carga un guion 2.0 desde un archivo a la escena (no cambia la animacion; usa 'Reproducir guion' despues)"
    bl_options = {"REGISTER"}
    filepath: StringProperty(name="Guion", subtype="FILE_PATH", default=RUTA_GUION)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=560)

    def execute(self, context):
        ruta = bpy.path.abspath(self.filepath)
        if not os.path.isfile(ruta): self.report({"ERROR"}, "No existe %s" % ruta); return {"CANCELLED"}
        try: g = gv.cargar(ruta)
        except Exception as e: self.report({"ERROR"}, "No se pudo leer el guion: %s" % e); return {"CANCELLED"}
        r = gv.validar(g, ai.RAIZ)
        if r["errores"]: self.report({"ERROR"}, "El guion tiene %d error(es): %s" % (len(r["errores"]), r["errores"][0])); return {"CANCELLED"}
        ai.guardar_en_escena(context.scene, g); m = g.get("meta") or {}
        self.report({"INFO"}, "Guion %r cargado (%d voces, %d sonidos, %d tramos de movimiento, %d avisos)" % (m.get("nombre"), len(g["audio"]), len(g["sonidos"]["manuales"]), len(g["movimiento"].get("tramos", [])), len(r["avisos"]))); return {"FINISHED"}


class CERDO_1_ST_OT_GuionReproducir(Operator):
    bl_idname = "cerdo_1_st.guion_reproducir"
    bl_label = "Reproducir guion"
    bl_description = "Aplica el guion 2.0 de la escena: objetos que falten, movimiento de Cerdo_1, voces, objetos y mundo, sonidos y camara. Tarda unos minutos (Blender queda ocupado)"
    bl_options = {"REGISTER", "UNDO"}
    preparar: BoolProperty(name="Preparar objetos", default=True)
    movimiento: BoolProperty(name="Movimiento de Cerdo_1", default=True)
    audio: BoolProperty(name="Voces (Voz Sync)", default=True)
    objetos: BoolProperty(name="Objetos y mundo", default=True)
    sonidos: BoolProperty(name="Sonidos", default=True)
    camara: BoolProperty(name="Camara", default=True)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=380)

    def execute(self, context):
        g = ai.guion_de_escena(context.scene)
        if g is None: self.report({"ERROR"}, "No hay un guion en la escena (usa 'Cargar guion')"); return {"CANCELLED"}
        r = gv.validar(g, ai.RAIZ)
        if r["errores"]: self.report({"ERROR"}, "El guion tiene errores: %s" % r["errores"][0]); return {"CANCELLED"}
        pasos = [p for p in rg.PASOS if getattr(self, p)]; inf = rg.reproducir(context, g, pasos)
        mal = [p for p, x in inf.items() if not x["ok"]]
        self.report({"WARNING"} if mal else {"INFO"}, "Guion reproducido: %s%s" % (", ".join("%s %.0f s" % (p, x["seg"]) for p, x in inf.items()), " | FALLARON: " + ", ".join(mal) + " (ver consola)" if mal else "")); return {"FINISHED"}


class CERDO_1_ST_PT_Reproducir(Panel):
    bl_label = "10  Reproducir guion completo"
    bl_idname = "CERDO_1_ST_PT_reproducir"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cerdo_1 Studio"
    bl_parent_id = "CERDO_1_ST_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        lay = self.layout; g = ai.guion_de_escena(context.scene); box = lay.box()
        if g is None: box.label(text="Sin guion 2.0 en la escena", icon="INFO")
        else:
            m = g.get("meta") or {}; trs = (g.get("movimiento") or {}).get("tramos") or []
            box.label(text="%s  (%s)" % (m.get("nombre", "?"), m.get("estado", "sin aprobar")), icon="TEXT")
            box.label(text="Movimiento: %d tramos migrados (resto: referencia)" % len(trs)); box.label(text="Voces %d | sonidos %d | camara %d | objetos %d" % (len(g.get("audio") or []), len((g.get("sonidos") or {}).get("manuales") or []), len(g.get("camara") or []), len(g.get("objetos") or [])))
        r = lay.row(align=True); r.operator("cerdo_1_st.guion_cargar_archivo", icon="FILE_FOLDER"); r.operator("cerdo_1_st.guion_reproducir", icon="PLAY")
