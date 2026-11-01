# -*- coding: utf-8 -*-
"""
reproducir_guion.py -- Alfred Animation Studio: REPRODUCE un guion 2.0 completo en una escena (fase 6 del plan `docs/PLAN_PARTE3_AL_FLUJO.md`).

Un solo paso, en este orden (cada uno repetible; cada uno se puede pedir por separado):
  preparar    crea los objetos que el guion necesita y que la escena no tiene (pala, items de tierra / tablon, tapa de pasto y pozo)     -> preparar_escena.py
  movimiento  genera y hornea a Alfred de f1 a f(fin): tramos migrados del motor + frames aun no migrados de la referencia numerica   -> motor_alfred.py
  audio       sincroniza las voces con Alfred Voz Sync, cada una en su inicio (DESPUES del movimiento: Voz Sync pasa la accion al NLA)  -> audio_import.py
  objetos     herramientas / items / bloques del mundo (siguen la pose FINAL, voces incluidas)                                           -> objetos_mundo.py
  sonidos     las tiras de sonido manuales                                                                                           -> sonidos_guion.py
  camara      claves y movimientos de camara y foco                                                                                  -> camara_guion.py
Lo que el guion NO cubre todavia (tramos S03-S14 de Alfred como datos propios, Jerry, zombies, objetos fuera de pala / hacha / items) sigue viniendo de la referencia numerica o del script generador.
"""
import time

import bpy

try:
    from . import audio_import as ai, camara_guion as cg, guion_v2 as gv, motor_alfred as ma, objetos_mundo as om, preparar_escena as pe, sonidos_guion as sg
except Exception:                                                                      # exec por ruta (pruebas)
    import importlib.util as _ilu
    import os as _os

    def _cargar(n):
        sp = _ilu.spec_from_file_location(n, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), n + ".py")); m = _ilu.module_from_spec(sp); sp.loader.exec_module(m); return m
    gv = _cargar("guion_v2"); ma = _cargar("motor_alfred"); om = _cargar("objetos_mundo"); sg = _cargar("sonidos_guion"); cg = _cargar("camara_guion"); ai = _cargar("audio_import"); pe = _cargar("preparar_escena")

PASOS = ("preparar", "movimiento", "audio", "objetos", "sonidos", "camara")


def reproducir(context, guion, pasos=PASOS, log=print):
    """-> {paso: {"ok": bool, "seg": float, "detalle": ...}}. Un paso que falla no impide los siguientes (queda en el informe)."""
    g = gv.migrar(guion); N = int((g.get("meta") or {}).get("frame_fin") or context.scene.frame_end); inf = {}
    ai.guardar_en_escena(context.scene, g)                                              # las herramientas del panel leen el guion de la escena
    f0 = context.scene.frame_current

    def paso(nombre, fn):
        if nombre not in pasos: return
        t0 = time.time()
        try: det = fn(); ok = True if not isinstance(det, dict) or det.get("ok", True) is not False else False
        except Exception as e: det = "%s: %s" % (type(e).__name__, e); ok = False
        inf[nombre] = {"ok": ok, "seg": round(time.time() - t0, 1), "detalle": det}; log("[reproducir] %-10s %s (%.1f s) %s" % (nombre, "OK " if ok else "FALLO", time.time() - t0, str(det)[:160]))

    def mov():
        res = ma.generar(g); n = ma.hornear(context, res, range(1, res["N"] + 1)); return {"frames": n, "migrados": len(res["migrados"]), "tramos": [t["id"] for t in res["tramos"]]}

    def obj():
        r = om.calcular(context, g); n = om.aplicar(context, r); vis = om.aplicar_mundo_visibilidad(context, g); return {"objetos_animados": n, "visibilidad": vis}

    paso("preparar", lambda: pe.preparar(context, g))
    paso("movimiento", mov)
    paso("audio", lambda: (lambda r: {"ok": r["ok"], "voces": r["n"], "mensaje": r["mensaje"]})(ai.aplicar_guion(context, g)))
    paso("objetos", obj)
    paso("sonidos", lambda: sg.aplicar_sonidos(context, g))
    paso("camara", lambda: cg.aplicar_camara(context, g))
    context.scene.frame_set(f0)
    return inf
