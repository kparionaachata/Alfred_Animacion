# -*- coding: utf-8 -*-
"""
sonidos_guion.py -- Cerdo_1 Animation Studio: SONIDOS del guion 2.0 (fase 5 del plan `docs/PLAN_PARTE3_AL_FLUJO.md`).

Seccion `sonidos`:  {modo: auto | manual | off, techo_voces, manuales: [{id, etiqueta, grupo, archivo, t, volumen, canal, pan}]}
  manuales   los sonidos que se colocan A MANO (impactos, herramientas, mesa, recogidas...): `archivo` es relativo a `sonidos/sounds/` (biblioteca de Minecraft), `t` un frame o una ancla ("hachazo_1+0"),
             `volumen` el que quedo tras el techo de las voces (se escribe tal cual: aqui NO se vuelve a aplicar el techo)
  modo auto  los pasos, silbidos e impactos que detecta `cerdo_1_sonidos` (`mcsnd.sonorizar`) se vuelven a generar con ese operador (`aplicar_sonidos(auto=True)`), no se guardan uno a uno
Cada tira queda como `SND_<etiqueta>_<frame>` con las propiedades `mcsnd` (grupo), `mcsnd_ev` (etiqueta) y `guion_id`. `aplicar_sonidos` es repetible y MUEVE las tiras que ya existen (las del guion por `guion_id`; las colocadas a mano
antes de existir el guion, por su etiqueta, que se adoptan): al mover una ancla o insertar tiempo basta con volver a aplicar. Las tiras que el guion ya no menciona (y que son suyas) se quitan.
"""
import os
import re

import bpy

try:
    from . import guion_v2 as gv
except Exception:
    import importlib.util as _ilu
    _sp = _ilu.spec_from_file_location("guion_v2", os.path.join(os.path.dirname(os.path.abspath(__file__)), "guion_v2.py")); gv = _ilu.module_from_spec(_sp); _sp.loader.exec_module(gv)

RAIZ = os.environ.get("CERDO_1_RAIZ", r"C:\Users\user\Desktop\Alfred_Animacion")
PREFIJO = "SND_"
AJENOS = ("wolf_step", "zombie_", "jerry_", "grass_fall_cuerpo_Dog")                 # sonidos de otros personajes: no son del guion de Cerdo_1 (los trae su script / su guion)


def ruta_sonido(archivo):
    return os.path.normpath(os.path.join(RAIZ, "sonidos", "sounds", archivo))


def _strips(ed):
    return ed.strips_all if hasattr(ed, "strips_all") else ed.sequences_all


def plan_sonidos(data):
    """lista de sonidos manuales con el frame ya resuelto: [{id, etiqueta, grupo, archivo, frame, volumen, canal, pan}]."""
    d = gv.desplegar(gv.migrar(data)); out = []
    for m in (d.get("sonidos") or {}).get("manuales") or []:
        out.append({"id": m.get("id"), "etiqueta": m["etiqueta"], "grupo": m.get("grupo", "objetos"), "archivo": m["archivo"], "frame": int(m["t"]), "volumen": float(m.get("volumen", 1.0)), "canal": int(m.get("canal", 22)),
                    "pan": float(m.get("pan", 0.0))})
    return sorted(out, key=lambda x: (x["frame"], x["etiqueta"]))


def _suyas(ed):
    return [s for s in _strips(ed) if s.type == 'SOUND' and s.name.startswith(PREFIJO)]


def aplicar_sonidos(context, data, auto=False):
    """crea / mueve / quita las tiras de los sonidos manuales del guion. -> {"creados", "movidos", "iguales", "quitados", "adoptados"}"""
    sc = context.scene; ed = sc.sequence_editor or sc.sequence_editor_create(); plan = plan_sonidos(data); r = {"creados": 0, "movidos": 0, "iguales": 0, "quitados": 0, "adoptados": 0}
    por_id = {s.get("guion_id"): s for s in _suyas(ed) if s.get("guion_id")}; libres = [s for s in _suyas(ed) if not s.get("guion_id") and not s.get("mcsnd_auto")]; usados = set()
    for m in plan:
        s = por_id.get(m["id"])
        if s is None:                                                                  # adoptar una tira puesta a mano con la misma etiqueta (SND_<etiqueta>_<frame>)
            pat = re.compile(r"^%s%s_-?\d+$" % (PREFIJO, re.escape(m["etiqueta"])))
            s = next((x for x in libres if pat.match(x.name) and x.name not in usados), None)
            if s is not None: r["adoptados"] += 1
        nombre = "%s%s_%d" % (PREFIJO, m["etiqueta"], m["frame"]); ruta = ruta_sonido(m["archivo"])
        if s is None:
            s = ed.strips.new_sound(nombre, ruta, m["canal"], m["frame"]); r["creados"] += 1
        else:
            cambio = int(s.frame_start) != m["frame"] or s.name != nombre or s.channel != m["canal"] or abs(s.volume - m["volumen"]) > 1e-4 or os.path.normpath(bpy.path.abspath(s.sound.filepath)) != ruta
            if cambio: r["movidos"] += 1
            else: r["iguales"] += 1
            if os.path.normpath(bpy.path.abspath(s.sound.filepath)) != ruta:
                ed.strips.remove(s); s = ed.strips.new_sound(nombre, ruta, m["canal"], m["frame"])
            else:
                s.frame_start = m["frame"]; s.name = nombre
                if s.channel != m["canal"]: s.channel = m["canal"]
        s.volume = m["volumen"]; s["vol_base"] = float(m["volumen"]); s.pan = m["pan"]; s["mcsnd"] = m["grupo"]; s["mcsnd_ev"] = m["etiqueta"]; s["guion_id"] = m["id"]; usados.add(s.name)
    ids = {m["id"] for m in plan}
    for gid, s in por_id.items():
        if gid not in ids and not str(s.get("mcsnd_ev", "")).startswith(AJENOS): ed.strips.remove(s); r["quitados"] += 1                 # los sonidos de otros personajes (zombie_*, jerry_*) no se quitan aunque no esten en este guion
    if auto and hasattr(bpy.ops, "mcsnd"):
        try: bpy.ops.mcsnd.sonorizar(modo="NUEVO")
        except Exception as e: print("[sonidos_guion] sonorizar:", e)
    return r


def capturar_sonidos(context, incluir_auto=False):
    """sonidos manuales de la escena -> entradas del guion (sin los de otros personajes: lobo, zombies, Jerry)."""
    ed = context.scene.sequence_editor; out = []
    for s in sorted(_suyas(ed), key=lambda x: (x.frame_start, x.name)):
        et = s.get("mcsnd_ev") or re.sub(r"_-?\d+$", "", s.name[len(PREFIJO):])
        if (s.get("mcsnd_auto") and not incluir_auto) or et.startswith(AJENOS): continue
        ruta = os.path.normpath(bpy.path.abspath(s.sound.filepath)); base = os.path.join(RAIZ, "sonidos", "sounds") + os.sep
        out.append({"id": s.get("guion_id") or "snd_%s_%d" % (et, int(s.frame_start)), "etiqueta": et, "grupo": s.get("mcsnd", "objetos"), "archivo": ruta[len(base):].replace("\\", "/") if ruta.startswith(base) else ruta,
                    "t": int(s.frame_start), "volumen": round(s.volume, 4), "canal": s.channel, "pan": round(s.pan, 2)})
    return out
