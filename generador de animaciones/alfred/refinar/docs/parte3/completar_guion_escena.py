# -*- coding: utf-8 -*-
"""Completa las secciones `sonidos` y `camara` de `configuraciones/guion_alfred_parte3.json` con lo que hay en la escena (fase 5): los sonidos manuales de Alfred con sus tiempos RELATIVOS a las anclas y las claves de
la camara profesional (Camera.001 / Foco_Conversacion, f1-683). Los 3 movimientos de camara posteriores (f1062 y f1094) se conservan. SE EJECUTA EN BLENDER (exec). Repetible (deja .bak).
  exec(open(r"...\\completar_guion_escena.py", encoding="utf-8").read())"""
import importlib.util
import os

import bpy

REFINAR = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"
ADDON = os.path.join(REFINAR, "alfred_animation_studio"); GUION = os.path.join(REFINAR, "configuraciones", "guion_alfred_parte3.json")


def _cargar(n):
    sp = importlib.util.spec_from_file_location(n, os.path.join(ADDON, n + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


gv = _cargar("guion_v2"); cg = _cargar("camara_guion"); sg = _cargar("sonidos_guion")
d = gv.cargar(GUION); ctx = bpy.context

# ---------------------------------------------------------------------------- camara: claves de la camara profesional + los movimientos de antes (se conservan)
movs = [c for c in d["camara"] if c.get("tipo", "movimiento") == "movimiento"]
claves = [cg.capturar_claves(ctx, "Camera.001", "location", 1, 683, "cam_camara_location"), cg.capturar_claves(ctx, "Camera.001", "lens", 1, 683, "cam_camara_lente"),
          cg.capturar_claves(ctx, "Camera.001", "dof.aperture_fstop", 1, 683, "cam_camara_apertura"), cg.capturar_claves(ctx, "Foco_Conversacion", "location", 1, 683, "cam_foco_location")]
for c in claves: c["nota"] = "camara profesional de la parte 3 (camara_parte3.py): una clave por frame; captura de la escena"
d["camara"] = claves + movs

# ---------------------------------------------------------------------------- anclas de las escenas con sonidos (frames del script v76: lanzamientos, barrido, antorcha, mesa, tablones, slabs, Jerry)
d["anclas"].update({"lanza_pico": 214, "lanza_hacha_madera": 229, "lanza_hacha_piedra": 247, "barrido_1": 450, "barrido_2": 463, "barrido_3": 476, "antorcha_saca": 530, "antorcha_pone": 545, "mesa_suelo": 574,
                    "tablon_1": 712, "tablon_2": 730, "tablon_3": 755, "slabs_aparecen": 776, "slab_cogido": 791, "barrido_mesa": 819, "jerry_sacude": 838, "corta_inicio": 1016})
# ---------------------------------------------------------------------------- sonidos: manuales de Alfred, con tiempos relativos a las anclas
man = sg.capturar_sonidos(ctx); d["sonidos"]["manuales"] = man
d, n = gv.anclar(d, max_dist=40, secciones=("sonidos",))
r = gv.validar(d, os.path.dirname(os.path.dirname(os.path.dirname(REFINAR))))
for e in r["errores"]: print("ERROR ", e)
for a in r["avisos"]: print("aviso ", a)
if not r["errores"]:
    gv.guardar(d, GUION, sobrescribir=True)
    print("guion guardado | camara:", [(c["id"], len(c["claves"]) if "claves" in c else "mov") for c in d["camara"]], "| sonidos manuales:", len(man), "con ancla:", sum(isinstance(m["t"], str) for m in d["sonidos"]["manuales"]))
