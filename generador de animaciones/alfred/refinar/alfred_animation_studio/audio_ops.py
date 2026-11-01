# -*- coding: utf-8 -*-
"""
audio_ops.py -- Alfred Animation Studio: operadores y panel "Audio (voces del guion)" (fase 2 del plan). La logica esta en `audio_import.py`.

  alfst.audio_importar      importa un audio (+ `animacion_*.py` de la app opcional): copia, tiempos por palabra, cara; lo registra en el guion con su inicio (frame o ancla, OBLIGATORIO) y lo sincroniza
  alfst.audio_sincronizar   crea con Alfred Voz Sync las pistas de voz / emocion / cara de las voces del guion, cada una en su inicio (todas, o una por `audio_id`)
  alfst.audio_inicio        pone el inicio de una voz en el frame actual (o en `frame`) y la vuelve a sincronizar
  alfst.audio_quitar        quita una voz del guion y sus pistas de la escena (no borra archivos)
Las voces viven en la seccion `audio` del guion 2.0 (se guardan con "Guardar configuracion" del panel 5; al cargar un guion con audio se sincronizan solas).
"""
import re
import sys

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty
from bpy.types import Operator, Panel

from . import audio_import as ai
from . import guion_v2 as gv

_EMO_ITEMS = [("AUTO", "Automatica", "La que salga del script de la app / del analisis")] + [(e, e.capitalize(), "") for e in ai.EMOCIONES]


def _tiempo(txt):
    """'1064' -> 1064; 'rompe_bloque+2' -> 'rompe_bloque+2'; '' -> None."""
    t = (txt or "").strip()
    if not t: return None
    return int(t) if re.fullmatch(r"-?\d+", t) else t


def _guion(context, crear=True):
    g = ai.guion_de_escena(context.scene)
    if g is None and crear:
        g = gv.nuevo("guion_de_la_escena", frame_ini=context.scene.frame_start, frame_fin=context.scene.frame_end)
    return g


class ALFST_OT_AudioImportar(Operator):
    bl_idname = "alfst.audio_importar"
    bl_label = "Importar audio"
    bl_description = ("Copia el audio a audios/<personaje>/, saca los tiempos por palabra (Whisper) y la cara de la app, lo registra en el guion con su inicio y lo sincroniza con Voz Sync. "
                      "Tarda unos 30 s (analisis de voz): Blender queda ocupado mientras tanto")
    bl_options = {"REGISTER"}

    filepath: StringProperty(name="Audio", subtype="FILE_PATH")
    script_app: StringProperty(name="animacion_*.py de la app (opcional)", subtype="FILE_PATH", description="Script de la app estudio_audio_expresion: da la cara y la emocion exactas")
    personaje: EnumProperty(name="Personaje", items=[("ALFRED", "Alfred", ""), ("JERRY", "Jerry", "")], default="ALFRED")
    inicio: StringProperty(name="Inicio (frame o ancla)", default="", description="Frame de la escena en que empieza el audio, o una ancla del guion (ej. rompe_bloque+2). Obligatorio")
    nombre: StringProperty(name="Nombre del archivo", default="", description="Vacio = se saca del texto de la app o del nombre del archivo")
    texto: StringProperty(name="Texto (opcional)", default="", description="Corrige la transcripcion de Whisper")
    emocion: EnumProperty(name="Emocion", items=_EMO_ITEMS, default="AUTO")
    sincronizar: BoolProperty(name="Sincronizar al terminar", default=True)
    reanalizar: BoolProperty(name="Volver a analizar", default=False, description="Aunque ya exista su .emocion.json")

    def invoke(self, context, event):
        if not self.inicio: self.inicio = str(context.scene.frame_current)              # propuesta visible: el usuario la confirma en el dialogo (no se usa en silencio)
        return context.window_manager.invoke_props_dialog(self, width=560)

    def draw(self, context):
        c = self.layout.column(align=True)
        for k in ("filepath", "script_app", "personaje", "inicio", "nombre", "texto", "emocion", "sincronizar", "reanalizar"): c.prop(self, k)
        g = _guion(context, crear=False)
        if g and g.get("anclas"): c.label(text="Anclas: " + ", ".join(list(g["anclas"])[:8]) + ("..." if len(g["anclas"]) > 8 else ""), icon="INFO")

    def execute(self, context):
        ini = _tiempo(self.inicio)
        if ini is None: self.report({"ERROR"}, "Falta el inicio (un frame o una ancla)"); return {"CANCELLED"}
        g = _guion(context)
        if not isinstance(ini, int):
            try: gv.frame_de(ini, gv.resolver_anclas(g))
            except ValueError as e: self.report({"ERROR"}, "Inicio no valido: %s" % e); return {"CANCELLED"}
        try:
            r = ai.importar(bpy.path.abspath(self.filepath), self.personaje, ini, bpy.path.abspath(self.script_app) or None, self.texto or None, self.emocion, self.nombre or None, None, self.reanalizar)
        except (ValueError, FileNotFoundError) as e: self.report({"ERROR"}, str(e)); return {"CANCELLED"}
        for m in r["mensajes"]: print("[audio_import]", m)
        for a in r["avisos"]: self.report({"WARNING"}, a)
        entrada, reemp = ai.agregar_a_guion(g, r["entrada"]); ai.guardar_en_escena(context.scene, g)
        msg = "%s: %s en %s" % ("Actualizada" if reemp else "Agregada", entrada["id"], entrada["inicio"])
        if self.sincronizar:
            s = ai.aplicar_guion(context, g, ids=[entrada["id"]]); msg += " | " + s["mensaje"] + ("" if s["ok"] else " (ver consola)")
            for _i, ok, m in s["resultados"]: print("[audio_import]", m)
        self.report({"INFO"}, msg)
        return {"FINISHED"}


class ALFST_OT_AudioSincronizar(Operator):
    bl_idname = "alfst.audio_sincronizar"
    bl_label = "Sincronizar voces del guion"
    bl_description = "Crea con Voz Sync las pistas de voz, emocion y cara de las voces del guion, cada una en su inicio (no usa el frame actual)"
    bl_options = {"REGISTER"}
    audio_id: StringProperty(default="", options={"HIDDEN"})

    def execute(self, context):
        g = _guion(context, crear=False)
        if not g or not g.get("audio"): self.report({"WARNING"}, "El guion no tiene audio"); return {"CANCELLED"}
        r = ai.aplicar_guion(context, g, ids=[self.audio_id] if self.audio_id else None)
        for _i, ok, m in r["resultados"]: print("[audio_import]", m)
        self.report({"INFO"} if r["ok"] else {"WARNING"}, r["mensaje"] + ("" if r["ok"] else " (ver consola)"))
        return {"FINISHED"} if r["n"] else {"CANCELLED"}


class ALFST_OT_AudioInicio(Operator):
    bl_idname = "alfst.audio_inicio"
    bl_label = "Poner inicio"
    bl_description = "Pone el inicio de esta voz en el frame actual y la vuelve a sincronizar"
    bl_options = {"REGISTER"}
    audio_id: StringProperty(default="", options={"HIDDEN"})

    def execute(self, context):
        g = _guion(context, crear=False); e = next((x for x in (g or {}).get("audio", []) if x.get("id") == self.audio_id), None)
        if e is None: self.report({"ERROR"}, "No hay una voz con id %r" % self.audio_id); return {"CANCELLED"}
        e["inicio"] = int(context.scene.frame_current); ai.guardar_en_escena(context.scene, g)
        r = ai.aplicar_guion(context, g, ids=[self.audio_id]); self.report({"INFO"}, "%s -> f%d | %s" % (self.audio_id, e["inicio"], r["mensaje"]))
        return {"FINISHED"}


class ALFST_OT_AudioQuitar(Operator):
    bl_idname = "alfst.audio_quitar"
    bl_label = "Quitar voz"
    bl_description = "Quita la voz del guion y sus pistas de la escena (no borra los archivos de audio)"
    bl_options = {"REGISTER"}
    audio_id: StringProperty(default="", options={"HIDDEN"})

    def execute(self, context):
        g = _guion(context, crear=False)
        if not g: return {"CANCELLED"}
        clips = [c for c in ai.clips_del_guion(g) if c.id == self.audio_id]
        if clips: ai.quitar_voz(context, clips[0])
        g["audio"] = [x for x in g.get("audio", []) if x.get("id") != self.audio_id]; ai.guardar_en_escena(context.scene, g)
        self.report({"INFO"}, "Voz %s quitada" % self.audio_id)
        return {"FINISHED"}


class ALFST_PT_Audio(Panel):
    bl_label = "6  Audio (voces del guion)"
    bl_idname = "ALFST_PT_audio"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Alfred Studio"
    bl_parent_id = "ALFST_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        lay = self.layout
        if "alfred_voz_sync" not in sys.modules: lay.label(text="Alfred Voz Sync no esta activo (se cargara al sincronizar)", icon="ERROR")
        g = ai.guion_de_escena(context.scene); clips = []
        if g and g.get("audio"):
            try: clips = ai.clips_del_guion(g)
            except Exception as e: lay.label(text="Guion con error: %s" % e, icon="ERROR")
        box = lay.box()
        if not clips: box.label(text="Sin voces en el guion (importa un audio o carga un guion 2.0)", icon="INFO")
        for c in clips:
            f = box.row(align=True); f.label(text="f%d  %s %s" % (c.inicio, "A" if c.personaje == "ALFRED" else "J", (c.texto or c.nombre)[:34]), icon="SPEAKER")
            o = f.operator("alfst.audio_inicio", text="", icon="TIME"); o.audio_id = c.id
            o = f.operator("alfst.audio_sincronizar", text="", icon="FILE_REFRESH"); o.audio_id = c.id
            o = f.operator("alfst.audio_quitar", text="", icon="X"); o.audio_id = c.id
        r = lay.row(align=True); r.operator("alfst.audio_importar", text="Importar audio...", icon="IMPORT"); r.operator("alfst.audio_sincronizar", text="Sincronizar todo", icon="FILE_REFRESH")
        lay.label(text="Al cargar un guion o concatenar, las voces se sincronizan solas", icon="CHECKMARK")
