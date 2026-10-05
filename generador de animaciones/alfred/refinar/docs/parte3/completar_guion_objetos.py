# -*- coding: utf-8 -*-
"""Completa la seccion `objetos` / `mundo` de `configuraciones/guion_alfred_parte3.json` con los datos que hacen falta para hornearlos con `objetos_mundo.py`: agarres relativos al hueso, sitio de la espalda,
estado inicial y eventos de la pala y el hacha, y los items de tierra / tablon (formulas y valores de `sentarse_en_refugio.py` v76). SE EJECUTA EN BLENDER (exec) con la escena de la parte 3 ya generada (lee matrices de
los huesos en frames concretos). Repetible: reemplaza las entradas con los mismos id y deja `.bak`.
  exec(open(r"...\\completar_guion_objetos.py", encoding="utf-8").read())"""
import importlib.util
import math
import os

import bpy
from mathutils import Matrix

REFINAR = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"
ADDON = os.path.join(REFINAR, "alfred_animation_studio")
GUION = os.path.join(REFINAR, "configuraciones", "guion_alfred_parte3.json")


def _cargar(nombre):
    sp = importlib.util.spec_from_file_location(nombre, os.path.join(ADDON, nombre + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


gv = _cargar("guion_v2"); om = _cargar("objetos_mundo")
ARM, MANO, ESP = "Armature", "Rightelbow_alfred", "Spine1_alfred"
d = gv.cargar(GUION)
sc = bpy.context.scene; f0 = sc.frame_current


def vivo(nombre, frame):
    sc.frame_set(frame); bpy.context.view_layer.update(); mw = bpy.data.objects[nombre].matrix_world
    return {"frame": frame, "loc": [round(c, 5) for c in mw.to_translation()], "quat": [round(c, 6) for c in mw.to_quaternion()], "escala": round(mw.to_scale().x, 4), "visible": True}


# ------------------------------------------------------------------------------------------------ agarres (valores de mundo -> relativos al hueso en el frame en que se dieron)
palo = om.agarre_desde_mundo(ARM, MANO, 625, (-96.317, -108.29, 15.372), (106.65, -45.118, -13.218))                     # sticks / pala recien hecha (ITEM_HOLD["stick_1"], f625)
cavar = om.agarre_desde_mundo(ARM, MANO, 887, (-95.774, -108.36, 14.64), (-131.02, 27.789, -72.813))                       # pala al cavar (Kebyn)
alto = [0.012658, -0.089666, 0.996158, 0.040519, -0.743668, 0.665821, 0.068626, 0.436685, -0.668638, -0.743973, -0.057042, -0.229646, 0.0, 0.0, 0.0, 1.0]   # hacha con el brazo en alto (Kebyn, f1023 con el arco de -45)
impacto = om.agarre_desde_mundo(ARM, MANO, 1038, (-95.195, -109.0, 14.757), (-98.702, -147.93, 7.6392))                    # hacha en el impacto (Kebyn)
rax = bpy.data.objects["wooden_axe"]["rel_spine1"]; esp_pala = om.mat16(Matrix([list(rax[i:i + 4]) for i in range(0, 16, 4)]) @ Matrix.Rotation(math.pi / 2, 4, 'X'))      # donde llevaba el hacha de madera, girada 90 en X
rha = bpy.data.objects["stone_axe"]["rel_spine1"]; esp_hacha = om.mat16(Matrix([list(rha[i:i + 4]) for i in range(0, 16, 4)]))                                          # su sitio al empezar la animacion

obj_pala = {"nombre": "stone_shovel", "blend": "objetos/vanilla/stone_shovel/stone_shovel.blend", "fuente_objeto": "stone_shovel", "armature": ARM, "hueso": MANO, "escala_mano": 0.7, "escala_espalda": 0.6,
            "inicial": {"loc": [-96.53, -108.47, 14.915], "rot": [0, 0, 0], "escala": 0.001, "visible": True},
            "agarres": {"palo": {"matriz": palo, "origen": "ITEM_HOLD stick_1 (mundo) en f625"}, "cavar": {"matriz": cavar, "origen": "valores de Kebyn (mundo) en f887"}},
            "espalda": {"hueso": ESP, "armature": ARM, "matriz": esp_pala, "origen": "rel_spine1 de wooden_axe x Rot X 90"},
            "eventos": [{"tipo": "aparece", "t": "pala_aparece", "en": {"loc": [-96.53, -108.47, 14.915], "rot": [0, 0, 0], "escala": 0.7}, "pop": {"curva": "elastica", "dur": 5}},
                        {"tipo": "toma", "t": "pala_toma", "hasta": "pala_toma+3", "agarre": "palo"}, {"tipo": "guarda", "t": "pala_guarda", "hasta": "pala_guarda+3"},
                        {"tipo": "toma", "t": "pala_sale", "hasta": "pala_sale+3", "agarre": "cavar"}, {"tipo": "guarda", "t": "pala_guardada", "hasta": "pala_guardada+3"}]}
obj_hacha = {"nombre": "stone_axe", "blend": "objetos/vanilla/stone_axe/stone_axe.blend", "fuente_objeto": "stone_axe", "armature": ARM, "hueso": MANO, "escala_mano": 0.7, "escala_espalda": 0.6, "inicial": vivo("stone_axe", 983),
             "agarres": {"mano": {"matriz": cavar, "origen": "el de la pala al cavar"}, "alto": {"matriz": alto, "origen": "valores de Kebyn: brazo en alto"}, "impacto": {"matriz": impacto, "origen": "valores de Kebyn: impacto, f1038"},
                         "corte": {"mezcla": {"a": "alto", "b": "impacto", "segun": {"hueso": MANO, "eje": 0, "de": -43.0, "a": 30.0}}}},
             "espalda": {"hueso": ESP, "armature": ARM, "matriz": esp_hacha, "origen": "rel_spine1 de stone_axe (su sitio al empezar la animacion)"},
             "eventos": [{"tipo": "toma", "t": "hacha_toma", "hasta": "hacha_toma+3", "agarre": "mano"}, {"tipo": "mantiene", "t": "corta_inicio", "agarre": "corte", "mezcla": 3},
                         {"tipo": "mantiene", "t": "corta_inicio+48", "agarre": "mano", "mezcla": 4}, {"tipo": "guarda", "t": "hacha_guardada", "hasta": "hacha_guardada+3"}]}
sc.frame_set(f0)
for o in (obj_pala, obj_hacha):
    d["objetos"] = [x for x in d["objetos"] if x.get("nombre") != o["nombre"]]; gv.agregar(d, "objetos", o, id="obj_" + ("pala" if "shovel" in o["nombre"] else "hacha"))

# ------------------------------------------------------------------------------------------------ mundo
pecho = {"armature": ARM, "hueso": ESP}
nuevos = {"mun_tierra": {"accion": "aparecer_item", "objeto": "tierra_item", "fuente_blend": "bloques_dinamicos/bloque_de_tierra.blend", "fuente_objeto": "dirt", "t": "cae_pozo", "en": [-95.85, -108.5, 13.55], "escala": 0.25, "sube": 0.9, "sube_dur": 8, "bob": 0.035, "bob_f": 0.45, "giro_vueltas_30f": 2,
                        "absorbe_en": "tierra_absorbida", "absorbe_dur": 7, "absorbido_por": pecho, "nota": "bloque de tierra: sale del pozo, flota, gira y es absorbido (como en Minecraft)"},
          "mun_tablon": {"accion": "aparecer_item", "objeto": "tablon_item", "t": "rompe_bloque", "en": [-94.5, -108.5, 14.6], "escala": 0.25, "sube": 0.3, "sube_dur": 8, "bob": 0.03, "bob_f": 0.45, "giro_vueltas_30f": 2,
                         "absorbe_en": "rompe_bloque+26", "absorbe_dur": 8, "absorbido_por": pecho, "copia_de": "refugio_bloque_03", "nota": "copia del bloque a escala 0.25: flota, gira y es absorbido"},
          "mun_tapa_pasto": {"accion": "crear_pozo", "objeto": "pozo_tierra", "tapa": "lid_cesped_cavar", "celda": [-95.5, -108.5, 14.0], "suelo": "a.001", "profundidad": 1.0, "t": "cae_pozo", "nota": "la tapa de pasto desaparece y queda el pozo (z 13..14); Alfred baja 1 en Z (f912-918)"},
          "mun_bloque_madera": {"accion": "ocultar", "objeto": "refugio_bloque_03", "t": "rompe_bloque"}}
d["mundo"] = [m for m in d["mundo"] if m.get("id") not in nuevos]
for i, m in nuevos.items(): gv.agregar(d, "mundo", m, id=i)

r = gv.validar(d, os.path.dirname(os.path.dirname(os.path.dirname(REFINAR))))
for e in r["errores"]: print("ERROR ", e)
for a in r["avisos"]: print("aviso ", a)
if not r["errores"]:
    gv.guardar(d, GUION, sobrescribir=True); print("guion guardado:", GUION, "| objetos", [o["nombre"] for o in d["objetos"]], "| mundo", [m["id"] for m in d["mundo"]])
