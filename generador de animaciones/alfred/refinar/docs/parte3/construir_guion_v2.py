# -*- coding: utf-8 -*-
"""Construye `refinar/configuraciones/guion_alfred_parte3.json`: el guion 2.0 de Alfred (parte 3) con las secciones que YA se pueden escribir con datos exactos de hoy
(meta, anclas, capas del corte y del asomarse, exactos del impacto, objetos con los valores dados por Kebyn, mundo, audio con su cara, sonidos manuales, camara).
Las secciones de movimiento del resto de la animacion (capas / poses de los tramos S01-S12) se llenan en las fases siguientes del plan (docs/PLAN_PARTE3_AL_FLUJO.md).
Uso:  python construir_guion_v2.py [--sobrescribir]      (no pisa un guion existente sin --sobrescribir; deja .bak)"""
import importlib.util
import json
import os
import sys

RAIZ = r"C:\Users\user\Desktop\Alfred_Animacion"
REFINAR = os.path.join(RAIZ, "generador de animaciones", "alfred", "refinar")
spec = importlib.util.spec_from_file_location("guion_v2", os.path.join(REFINAR, "alfred_animation_studio", "guion_v2.py")); g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
SALIDA = os.path.join(REFINAR, "configuraciones", "guion_alfred_parte3.json")

d = g.nuevo("alfred_parte3", "ALFRED", 24, 1, 1160, "Alfred, parte 3 (refugio): sentarse, herramientas, mesa de crafteo, cavar, cortar madera, asomarse. Guion 2.0 (version inicial: audio, camara, exactos, objetos, mundo, sonidos y las capas del corte).")
d["meta"].update({"fuente": "docs/parte3/sentarse_en_refugio.py (v76)", "blend": "capitulos/capitulo_4/base_parte_3.blend", "notas": "Las poses y capas de los tramos S01-S12 todavia viven en sentarse_en_refugio.py (plan: docs/PLAN_PARTE3_AL_FLUJO.md)."})

# ---------------------------------------------------------------- anclas (frames confirmados en el script / la escena)
AN = {"inicio": 1, "voz_sentado": 50, "voz_pico": 206, "voz_zombie": 358, "voz_idea": 430, "arrodilla": 502, "mesa_aparece": 563, "voz_a_ver": 632, "pala_aparece": 672, "pala_toma": 684, "pala_guarda": 695,
      "voz_solo_uno": 664, "levanta": 843, "pala_sale": 865, "cae_pozo": 912, "tierra_absorbida": 938, "gira_1": 946, "pala_guardada": 956, "hacha_toma": 984, "gira_2": 996, "corta_inicio": 1016,
      "golpe_1": 1026, "golpe_2": 1038, "golpe_3": 1050, "rompe_bloque": 1062, "hacha_guardada": "rompe_bloque+8", "voz_afuera": "rompe_bloque+2", "camara_1": "rompe_bloque", "camara_2": 1094,
      "asoma": 1096, "fin": 1160}
d["anclas"] = AN; an = g.resolver_anclas(d)


def rel(t):
    """frame absoluto -> atajo relativo a la ancla mas cercana (los tiempos de las capas cuelgan de los golpes y del asomarse)."""
    cand = [(abs(t - v), k, v) for k, v in an.items() if k in ("corta_inicio", "golpe_1", "golpe_2", "golpe_3", "rompe_bloque", "asoma", "camara_2")]
    _, k, v = min(cand); return k if t == v else "%s%+d" % (k, t - v)


def curva(canal, pts, interp="smooth", nota=""):
    e = {"canal": canal, "puntos": [[rel(t), v] for t, v in pts], "interp": interp}
    if nota: e["nota"] = nota
    return e


# ---------------------------------------------------------------- capas (tramo del corte de madera y asomarse; valores del script v76)
G1, G2, G3, G4 = 1026, 1038, 1050, 1062
lean = [(1016, 0), (1020, -22.5), (1024, -22.5), (G1, 22), (1028, 22), (1033, -22.5), (1036, -22.5), (G2, 22), (1040, 22), (1045, -22.5), (1048, -22.5), (G3, 22), (1052, 22), (1057, -22.5), (1060, -22.5), (G4, 22),
        (1064, 22), (1070, 0), (1096, 0), (1106, 12), (1140, 12), (1148, 0)]
neck_x = [(1016, 0), (1020, -13.5), (1024, -13.5), (G1, 0), (1033, -13.5), (1036, -13.5), (G2, 0), (1045, -13.5), (1048, -13.5), (G3, 0), (1057, -13.5), (1060, -13.5), (G4, 0), (1070, 0)]
look_y = [(1098, 0), (1108, 45), (1113, 45), (1124, -45), (1129, -45), (1140, 0)]
g.agregar(d, "capas", curva("inclinacion", lean, nota="cortar madera: torso atras (-22.5) antes de cada golpe y adelante (+22) en el impacto; se asoma (+12) f1096-1148"), id="cap_inclinacion_corte")
g.agregar(d, "capas", curva("cuello_x", neck_x, nota="cabeza echada atras en cada preparacion del golpe"), id="cap_cuello_x_corte")
g.agregar(d, "capas", curva("cuello_y", look_y, nota="se asoma a mirar: +45 izquierda, -45 derecha, al frente"), id="cap_mirada_asoma")

# ---------------------------------------------------------------- exactos (valores dados por Kebyn)
g.agregar(d, "exactos", {"frames": ["golpe_1", "golpe_2", "golpe_3", "rompe_bloque"], "ventana": 3, "tol": 0.0, "nota": "IMPACTO hacha-bloque (capturas de Blender de Kebyn, 2026-10-04): ningun filtro puede tocar estos valores en esos frames",
                             "huesos": {"Rightelbow_alfred": [30.0, 44.0, -52.0], "RightUpArm_alfred": [170.25, 182.12, 106.45], "Hips_alfred": [-0.16987, -20.884, 0.23731], "Spine_alfred": [-5.134, 0.0, -0.45724],
                                        "Spine1_alfred": [-2.2951, -35.957, -8.9858]},
                             "objetos": {"stone_axe": {"loc": [-95.195, -109.0, 14.757], "rot": [-98.702, -147.93, 7.6392], "scale": 0.7}}}, id="exa_impacto_hacha")
g.agregar(d, "exactos", {"frames": ["hacha_guardada", "hacha_guardada+3"], "ventana": 0, "tol": 0.0, "nota": "pose BACK de Kebyn (mano derecha a la espalda) al guardar el hacha; la misma pose se usa en los demas tramos BACK (antorcha, sticks, pala)",
                         "huesos": {"LeftUpArm_alfred": [78.088, -224.3, 0.27287], "Leftelbow_alfred": [20.216, 2.0649, 90.389], "RightUpArm_alfred": [266.17, -35.4, 190.21], "Rightelbow_alfred": [7.8244, -2.384, -111.53]}},
         id="exa_pose_espalda")

# ---------------------------------------------------------------- objetos (agarres de mundo dados por Kebyn; los eventos son los de hoy)
g.agregar(d, "objetos", {"nombre": "stone_shovel", "blend": "objetos/vanilla/stone_shovel/stone_shovel.blend", "hueso": "Rightelbow_alfred", "escala_mano": 0.7, "escala_espalda": 0.6,
                         "agarres_mundo": {"cavar": {"loc": [-95.774, -108.36, 14.64], "rot": [-131.02, 27.789, -72.813], "scale": 0.7, "pose_ref": "f887"}},
                         "eventos": [{"tipo": "aparece", "t": "pala_aparece"}, {"tipo": "toma", "t": "pala_toma", "hasta": "pala_toma+3"}, {"tipo": "guarda", "t": "pala_guarda", "hasta": "pala_guarda+3"},
                                     {"tipo": "toma", "t": "pala_sale", "hasta": "pala_sale+3"}, {"tipo": "guarda", "t": "pala_guardada", "hasta": "pala_guardada+3"}]}, id="obj_pala")
g.agregar(d, "objetos", {"nombre": "stone_axe", "blend": "objetos/vanilla/stone_axe/stone_axe.blend", "hueso": "Rightelbow_alfred", "escala_mano": 0.7, "escala_espalda": 0.6,
                         "agarres_mundo": {"brazo_en_alto": {"loc": [-96.057, -108.73, 14.727], "quat_wxyz": [-0.667, 0.489, -0.388, -0.407], "scale": 0.7, "pose_ref": "f1023 con el arco de -45"},
                                           "impacto": {"loc": [-95.195, -109.0, 14.757], "rot": [-98.702, -147.93, 7.6392], "scale": 0.7, "pose_ref": "f1038"}},
                         "espalda": {"origen": "rel_spine1 del objeto stone_axe en base_parte_3.blend (su sitio al empezar la animacion)"},
                         "eventos": [{"tipo": "toma", "t": "hacha_toma", "hasta": "hacha_toma+3"}, {"tipo": "mantiene", "t": "hacha_toma+3", "hasta": "hacha_guardada"}, {"tipo": "guarda", "t": "hacha_guardada", "hasta": "hacha_guardada+3"}]},
         id="obj_hacha")

# ---------------------------------------------------------------- mundo
g.agregar(d, "mundo", {"accion": "ocultar", "objeto": "lid_cesped_cavar", "t": "cae_pozo", "nota": "la tapa de pasto desaparece y queda el pozo (pozo_tierra, z 13..14); Alfred baja 1 en Z (f912-918)"}, id="mun_tapa_pasto")
g.agregar(d, "mundo", {"accion": "aparecer_item", "objeto": "tierra_item", "t": "cae_pozo", "hasta": "tierra_absorbida", "absorbido_por": "Alfred", "nota": "bloque de tierra: flota, gira, escala 0.25; absorbido f938-945"}, id="mun_tierra")
g.agregar(d, "mundo", {"accion": "ocultar", "objeto": "refugio_bloque_03", "t": "rompe_bloque"}, id="mun_bloque_madera")
g.agregar(d, "mundo", {"accion": "aparecer_item", "objeto": "tablon_item", "t": "rompe_bloque", "hasta": "rompe_bloque+34", "absorbido_por": "Alfred", "nota": "copia del bloque a escala 0.25: flota, gira; absorbido desde rompe_bloque+26"}, id="mun_tablon")

# ---------------------------------------------------------------- audio (voces de Alfred; la cara viene de <audio>.cara.json)
VOCES = [("fdfdfdfff.mp3", "voz_sentado"), ("ya_pero_no_tengo_sueno.mp3", "voz_pico"), ("que_borrio_quieres.wav", "voz_zombie"), ("espera_tengo_una_idea.wav", "voz_idea"), ("a_ver_como_eres_tu.wav", 632),
         ("voy_a_necesitar_solo_uno.wav", "voz_solo_uno"), ("que_estara_pasando_afuera.wav", "voz_afuera")]
for arch, ini in VOCES:
    base = os.path.splitext(arch)[0]; rc = "audios/alfred/%s.cara.json" % base; re_ = "audios/alfred/%s.emocion.json" % base
    with open(os.path.join(RAIZ, rc), encoding="utf-8") as f: cara = json.load(f)
    with open(os.path.join(RAIZ, re_), encoding="utf-8") as f: emo = json.load(f)
    g.agregar(d, "audio", {"personaje": "ALFRED", "archivo": "audios/alfred/" + arch, "inicio": ini, "emocion": cara.get("emocion"), "texto": emo.get("texto"), "cara": rc, "emocion_json": re_,
                           "duracion_f": int(round(cara.get("duracion_s", 0) * 24))}, id="aud_" + base)

# ---------------------------------------------------------------- sonidos: modo auto + los manuales de Alfred (los automaticos -pasos, silbidos, impactos- los vuelve a generar el modo auto)
with open(os.path.join(REFINAR, "docs", "parte3", "datos_guion", "sonidos_escena.json"), encoding="utf-8") as f: esc = json.load(f)
d["sonidos"] = {"modo": "auto", "techo_voces": True, "manuales": []}
for s in esc:
    et = s["etiqueta"]
    if s["auto"] or et.startswith(("wolf_step", "zombie_", "jerry_", "grass_fall_cuerpo_Dog")): continue
    g.agregar(d, "sonidos", {"etiqueta": et, "grupo": s["grupo"], "archivo": s["archivo"], "t": s["t"], "volumen": s["volumen"], "canal": s["canal"]}, id="snd_%s_%d" % (et, s["t"]))

# ---------------------------------------------------------------- camara
g.agregar(d, "camara", {"objeto": "Camera.001", "desde": "camara_1", "hasta": "camara_1+12", "destino": [-95.646, -109.17, 14.847], "interp": "smooth", "nota": "apenas rompe el bloque"}, id="cam_acercamiento")
g.agregar(d, "camara", {"objeto": "Foco_Conversacion", "desde": "camara_1", "hasta": "camara_1+12", "destino": [-94.315, -108.59, 14.902], "interp": "smooth"}, id="cam_foco")
g.agregar(d, "camara", {"objeto": "Camera.001", "desde": "camara_2", "hasta": "camara_2+12", "destino": [-91.623, -107.82, 14.847], "interp": "smooth", "nota": "mientras Alfred se asoma"}, id="cam_exterior")

r = g.validar(d, RAIZ)
for e in r["errores"]: print("ERROR ", e)
for a in r["avisos"]: print("aviso ", a)
if r["errores"]: sys.exit("el guion tiene errores")
g.guardar(d, SALIDA, sobrescribir="--sobrescribir" in sys.argv)
print("escrito", SALIDA, "| capas %d, exactos %d, objetos %d, mundo %d, audio %d, sonidos manuales %d, camara %d, anclas %d" % (len(d["capas"]), len(d["exactos"]), len(d["objetos"]), len(d["mundo"]), len(d["audio"]), len(d["sonidos"]["manuales"]), len(d["camara"]), len(d["anclas"])))
