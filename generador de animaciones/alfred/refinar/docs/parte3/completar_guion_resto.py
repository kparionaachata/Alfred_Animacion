# -*- coding: utf-8 -*-
"""Ultimo paso de la migracion de OBJETOS (parte 3 de Alfred): agrega al guion TODO lo que faltaba: el barrido de las herramientas sobre Jerry y su lanzamiento al rincon (S05), la segunda antorcha y su luz (S06),
la mesa de crafteo, los sticks y el bloque de piedra (S07), los 3 tablones y los 6 slabs, con el barrido de los slabs sobre Jerry y su caida al suelo (S08, S09), y quita el `coloca` (puente) del hacha de piedra.
Datos: los TIEMPOS y las formulas son los de `sentarse_en_refugio.py`; las posiciones que dependian de medir a Jerry (donde queda cada herramienta / slab sobre su lomo y en el suelo) se LEEN de la escena guardada
(`base_parte_3.blend`, el resultado del generador) y quedan escritas en el guion como numeros. Los agarres se calculan contra los huesos de la escena en el frame de referencia (f625 / f545).
SE EJECUTA EN BLENDER con `base_parte_3.blend`:  blender --background base_parte_3.blend --python completar_guion_resto.py     (repetible: reemplaza las entradas con el mismo nombre; deja .bak)."""
import importlib.util
import math
import os
import shutil

import bpy

REFINAR = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"; ADDON = os.path.join(REFINAR, "alfred_animation_studio"); GUION = os.path.join(REFINAR, "configuraciones", "guion_alfred_parte3.json")


def _cargar(n):
    sp = importlib.util.spec_from_file_location(n, os.path.join(ADDON, n + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


gv = _cargar("guion_v2"); om = _cargar("objetos_mundo"); d = gv.cargar(GUION); sc = bpy.context.scene
ARM = "Armature"; JERRY = "Dog_001_rig"; MANO = {"Right": "Rightelbow_alfred", "Left": "Leftelbow_alfred"}; REF_ITEMS = 625; N = int(d["meta"].get("frame_fin") or 1160)
sc.frame_set(1); bpy.context.view_layer.update()


def vivo(nombre, frame):
    sc.frame_set(frame); bpy.context.view_layer.update(); mw = bpy.data.objects[nombre].matrix_world
    return {"loc": [round(c, 5) for c in mw.to_translation()], "quat": [round(c, 6) for c in mw.to_quaternion().normalized()], "escala": round(mw.to_scale().x, 4)}


def poner_ancla(nombre, valor): d["anclas"][nombre] = valor


# ------------------------------------------------------------------------------------------------------------------------------------------- anclas nuevas
for n, v in {"suelta_1": 503, "suelta_2": 504, "suelta_3": 505, "items_sale": 562, "piedra_sale": 579, "piedra_suelta": 641, "stick_1_suelta": 653, "stick_2_suelta": 661, "items_desaparecen": 670,
             "tablon_1_suelta": 723, "tablon_2_suelta": 741, "tablon_3_suelta": 765, "tablones_desaparecen": 772, "slab_guarda": 802, "mesa_mano": 569, "mesa_baja": 570}.items(): poner_ancla(n, v)

nuevos = []                                                                                  # (nombre, entrada)


def objeto(nombre, **kw):
    e = {"nombre": nombre, "armature": ARM, "hueso": MANO["Right"], "escala_mano": 1.0, "agarres": {}, "eventos": []}; e.update(kw); nuevos.append(e); return e


# ------------------------------------------------------------------------------------------------------------------------------------------- 1. herramientas: barrido sobre Jerry y vuelo al rincon
BARRIDO = {"stone_axe": ("barrido_1", 450, -96.35, "suelta_1", 503, +1), "wooden_axe": ("barrido_2", 463, -96.05, "suelta_2", 504, -1), "wooden_pickaxe": ("barrido_3", 476, -95.75, "suelta_3", 505, +1)}
T1, T2, WALL_Y, WALL_Z, JR_FLY = 9, 8, -109.72, 15.0, 12
for e in d["objetos"]:
    if e["nombre"] not in BARRIDO: continue
    anc, hit, wx, anc_r, kr, sgn = BARRIDO[e["nombre"]]; n = e["nombre"]
    e["eventos"] = [ev for ev in e["eventos"] if ev["tipo"] != "coloca" and not ev.get("nota", "").startswith("barrido")]
    antes = vivo(n, hit - 1); kL = hit + T1 + T2; reposo = vivo(n, kL); fin = vivo(n, kr + JR_FLY + 3)
    i_lanza = max(i for i, ev in enumerate(e["eventos"]) if ev["tipo"] == "lanza") + 1 if any(ev["tipo"] == "lanza" for ev in e["eventos"]) else 0
    e["eventos"][i_lanza:i_lanza] = [
        {"tipo": "lanza", "t": anc, "vuelo": T1, "a": {"centro": [wx, WALL_Y, WALL_Z], "quat": antes["quat"], "escala": antes["escala"]}, "giro": {"eje": [1, 0, 0], "de": 0.0, "a": -270.0},
         "nota": "barrido: el manotazo de Jerry la lanza contra el muro sur (vuela hasta el con una vuelta y media)"},
        {"tipo": "cae_sobre", "t": "%s+%d" % (anc, T1), "vuelo": T2, "sobre": {"armature": JERRY, "hueso": "spine_3", "reposo": {"loc": reposo["loc"], "quat": reposo["quat"], "escala": reposo["escala"]}},
         "nota": "barrido: rebota en el muro y cae sobre el lomo de Jerry; viaja pegada a su hueso spine_3"},
        {"tipo": "lanza", "t": anc_r, "vuelo": JR_FLY, "a": {"loc": fin["loc"], "quat": fin["quat"], "escala": fin["escala"]}, "giro": {"eje": [0, 0, 1], "de": 540.0 * sgn, "a": 0.0, "curva": "suave"},
         "nota": "barrido: Jerry se sacude y la lanza al rincon sureste (vuelo parabolico con giro en Z)"}]
# ------------------------------------------------------------------------------------------------------------------------------------------- 2. objetos en la mano: sticks / piedra / tablones
ITEMS = [("stick_1", "Right", "items_sale", "stick", "stick.blend", 0.6, [-96.317, -108.29, 15.372], [106.65, -45.118, -13.218], "stick_1_suelta", [-96.53, -108.47, 14.905], [0, 0, 20.0], 0.22, None),
         ("stick_2", "Right", "items_sale", "stick", None, 0.6, [-96.326, -108.29, 15.346], [93.86, -24.347, -0.008386], "stick_2_suelta", [-96.34, -108.47, 14.905], [0, 0, -15.0], 0.22, "stick_1"),
         ("cobblestone", "Left", "piedra_sale", "cobblestone", "cobblestone.blend", 0.35, [-96.358, -109.11, 15.387], [-89.483, 110.68, 0.080644], "piedra_suelta", [-96.72, -108.47, 14.90], [0, 0, 0], 0.19, None)]
FUENTES = {"stick": "objetos/vanilla/stick/stick.blend", "cobblestone": "bloques_dinamicos/cobblestone.blend"}
for nombre, lado, anc_pick, src, _x, esc_mano, loc, rot, anc_rel, slot, rot_f, esc_f, copia in ITEMS:
    e = objeto(nombre, hueso=MANO[lado], escala_mano=esc_mano, coleccion="objetos_mano", inicial={"loc": vivo(nombre, 1)["loc"], "escala": 0.001, "visible": True})
    if copia: e["copia_de"] = copia
    else: e["blend"] = FUENTES[src]; e["fuente_objeto"] = src
    e["agarres"]["mano"] = {"matriz": om.agarre_desde_mundo(ARM, MANO[lado], REF_ITEMS, loc, rot), "origen": "valores de Kebyn (mundo) en f%d" % REF_ITEMS}
    e["eventos"] = [{"tipo": "en_mano", "t": anc_pick, "agarre": "mano", "pop": {"dur": 3, "escala": esc_mano}, "nota": "sale en la mano (escala 0 -> %s en 3 f) y viaja pegado al antebrazo" % esc_mano},
                    {"tipo": "asienta", "t": anc_rel, "dur": 4, "en": {"loc": slot, "rot": rot_f, "escala": esc_f}, "nota": "lo suelta sobre la casilla de la rejilla: cae 4 f y se reduce al tamano de la casilla"},
                    {"tipo": "encoge", "t": "items_desaparecen", "dur": 2, "nota": "craftea: los materiales desaparecen"}]
# tablones (agarre de la mano izquierda = el de la piedra; derecha = traslacion pura en f625)
AG_R = om.agarre_desde_mundo(ARM, MANO["Right"], REF_ITEMS, [-96.317, -108.29, 15.372], [0, 0, 0])
AG_L = [x for x in nuevos if x["nombre"] == "cobblestone"][0]["agarres"]["mano"]["matriz"]
PLANKS = [("plank_1", "Left", "tablon_1", "tablon_1_suelta", [-96.34, -108.66, 14.90]), ("plank_2", "Right", "tablon_2", "tablon_2_suelta", [-96.34, -108.28, 14.90]), ("plank_3", "Right", "tablon_3", "tablon_3_suelta", [-96.34, -108.47, 14.90])]
for nombre, lado, anc_pick, anc_rel, slot in PLANKS:
    e = objeto(nombre, hueso=MANO[lado], escala_mano=0.35, coleccion="crafteo_slabs", inicial={"loc": vivo(nombre, 1)["loc"], "escala": 0.001, "visible": True})
    if nombre == "plank_1": e["blend"] = "bloques_dinamicos/bloque_de_tablones_de_roble.blend"; e["fuente_objeto"] = "oak_planks"
    else: e["copia_de"] = "plank_1"
    e["agarres"]["mano"] = {"matriz": AG_L if lado == "Left" else AG_R, "origen": "el de la piedra (izquierda) / traslacion pura de la derecha en f%d" % REF_ITEMS}
    e["eventos"] = [{"tipo": "en_mano", "t": anc_pick, "agarre": "mano", "pop": {"dur": 3, "escala": 0.35}, "nota": "lo saca de la espalda"},
                    {"tipo": "asienta", "t": anc_rel, "dur": 4, "en": {"loc": slot, "rot": [0, 0, 0], "escala": 0.19}, "nota": "lo suelta en la fila inferior de la rejilla"},
                    {"tipo": "encoge", "t": "tablones_desaparecen", "dur": 2, "nota": "craftea: los tablones desaparecen"}]
# ------------------------------------------------------------------------------------------------------------------------------------------- 3. slabs
SLAB_POS = [(-96.60, -108.66), (-96.60, -108.47), (-96.60, -108.28), (-96.42, -108.66), (-96.42, -108.47), (-96.42, -108.28)]
SLAB_THROW = {1: (822, (-96.45, -109.40), 20.0), 2: (820, (-96.25, -109.50), 75.0), 3: (819, (-96.05, -109.45), 130.0), 4: (822, (-95.85, -109.50), 40.0), 5: (820, (-95.65, -109.50), 100.0)}
SLAB_OFF = {1: 844, 2: 845, 3: 846, 4: 847, 5: 848}; SLAB_FLOOR = {1: (-96.85, -109.015, 0.0), 2: (-96.68, -109.015, 6.0), 3: (-96.51, -109.015, -5.0), 4: (-96.34, -109.015, 4.0), 5: (-96.17, -109.015, -7.0)}
SLAB_FLY, SLAB_OFF_FLY = 10, 8
for i in range(6):
    nombre = "slab_%d" % (i + 1); p0 = [SLAB_POS[i][0], SLAB_POS[i][1], 14.90]
    e = objeto(nombre, hueso=MANO["Right"], escala_mano=0.35 if i == 5 else 0.19, coleccion="crafteo_slabs", inicial={"loc": p0, "escala": 0.001, "visible": True})
    if i == 0: e["blend"] = "bloques_dinamicos/slab_de_tablones_de_roble.blend"; e["fuente_objeto"] = "oak_planks_slab"
    else: e["copia_de"] = "slab_1"
    ev = [{"tipo": "aparece", "t": "slabs_aparecen+%d" % i, "en": {"loc": p0, "rot": [0, 0, 0], "escala": 0.19}, "pop": {"curva": "elastica", "dur": 4}, "nota": "craftea: aparece sobre la tapa de la mesa (Elastic In-Out)"}]
    if i < 5:
        la, (lx, ly), yw = SLAB_THROW[i + 1]; zj = vivo(nombre, la + SLAB_FLY)["loc"][2]; fx, fy, fyaw = SLAB_FLOOR[i + 1]
        ev += [{"tipo": "cae_sobre", "t": la, "vuelo": SLAB_FLY, "arco": {"altura": 0.25, "ref": "origen"}, "giro": {"eje": [0, 1, 0], "de": 0.0, "a": 360.0 * (1 if i % 2 == 0 else -1)},
                "sobre": {"armature": JERRY, "hueso": "spine_3", "reposo": {"loc": [lx, ly, zj], "rot": [0, 0, yw], "escala": 0.19}}, "nota": "la mano izquierda lo barre sobre Jerry: salta, gira y cae sobre su lomo (altura medida en la escena)"},
               {"tipo": "lanza", "t": SLAB_OFF[i + 1], "vuelo": SLAB_OFF_FLY, "arco": {"altura": 0.15, "ref": "origen"}, "a": {"loc": [fx, fy, 14.0], "rot": [0, 0, fyaw], "escala": 0.19},
                "nota": "Jerry se sacude: sale del lomo con un salto y queda en fila en el suelo"}]
    else:
        e["agarres"]["mano"] = {"matriz": AG_R, "origen": "traslacion pura de la derecha en f%d" % REF_ITEMS}
        ev += [{"tipo": "toma", "t": "slab_cogido", "hasta": "slab_cogido+3", "agarre": "mano", "nota": "el sexto lo coge la mano derecha"}, {"tipo": "encoge", "t": "slab_guarda", "dur": 3, "nota": "lo lleva a la espalda y se lo guarda"}]
    e["eventos"] = ev
# ------------------------------------------------------------------------------------------------------------------------------------------- 4. antorcha 2 y mesa
TORCH_FINAL = ([-97.0, -108.5, 15.1], [0.0, 20.0, 0.0])
e = objeto("antorcha_2", hueso=MANO["Right"], escala_mano=1.0, coleccion="antorcha_2", copia_jerarquia_de="antorcha_1.001", inicial={"loc": vivo("antorcha_2", 1)["loc"], "escala": 0.001, "visible": True})
e["agarres"]["mano"] = {"matriz": om.agarre_desde_mundo(ARM, MANO["Right"], 545, TORCH_FINAL[0], TORCH_FINAL[1]), "origen": "su sitio final en el muro oeste, relativo a la mano en f545"}
e["eventos"] = [{"tipo": "en_mano", "t": "antorcha_saca", "agarre": "mano", "pop": {"dur": 3, "escala": 1.0}, "nota": "la saca de la espalda (copia de la antorcha del refugio)"},
                {"tipo": "asienta", "t": "antorcha_pone", "dur": 3, "vivo": True, "en": {"loc": TORCH_FINAL[0], "rot": TORCH_FINAL[1], "escala": 1.0}, "nota": "se asienta en el muro oeste (-97, -108.5, 15.1), giro Y 20"}]
e0 = bpy.data.objects["torch1.light.002"].data.energy
d["mundo"] = [m for m in d["mundo"] if m.get("id") != "mun_luz_antorcha2"]
d["mundo"].append({"id": "mun_luz_antorcha2", "accion": "luz", "t": 1, "objeto": "antorcha_2", "energia": round(e0, 4), "claves": [[1, 0.0], ["antorcha_saca", 0.0], ["antorcha_saca+3", 1.0], [N, 1.0]], "nota": "la luz de la antorcha nueva solo existe desde que se saca"})
P0, PC, H, F = [-95.40, -108.59, 14.75], [-95.70, -108.59, 15.55], [-96.53, -108.47, 14.55], [-96.53, -108.47, 13.9946]
e = objeto("mesa_de_crafteo_1", hueso=MANO["Right"], escala_mano=0.9, coleccion="mesa_crafteo", blend="bloques_dinamicos/mesa_de_crafteo_1.blend", fuente_objeto="mesa_de_crafteo_1", fuente_extra=["9ec2028a-8e9e-9a30-eae2-7cc72eda0077_1"],
           inicial={"loc": P0, "rot": [0, 0, 0], "escala": 0.001, "visible": True})
e["eventos"] = [{"tipo": "bezier", "t": "mesa_aparece", "hasta": "mesa_mano", "puntos": [P0, PC, H], "rot0": [0, 70.0, 80.0], "escala": 0.9, "nota": "sale de la nada, vuela en curva y llega a las manos de Alfred (escala 0 -> 0.9)"},
                {"tipo": "asienta", "t": "mesa_baja", "dur": 4, "en": {"loc": F, "rot": [0, 0, 0], "escala": 0.9}, "squash": {"desde": 0, "amp": 0.04, "tau": 2.0, "periodo": 3.0, "dur": 8}, "nota": "baja al suelo y se asienta con un rebote corto"}]
# ------------------------------------------------------------------------------------------------------------------------------------------- guardar
nombres = {e["nombre"] for e in nuevos}
d["objetos"] = [e for e in d["objetos"] if e["nombre"] not in nombres]
for e in nuevos: gv.agregar(d, "objetos", e, id="obj_" + e["nombre"])
mig = d["meta"].setdefault("migracion", {})
mig["objetos_en_el_guion"] = [e["nombre"] for e in d["objetos"]] + ["tierra_item", "tablon_item"]
mig["objetos_pendientes"] = []
mig.pop("objetos_pendientes_nota", None)
shutil.copyfile(GUION, GUION + ".bak")
r = gv.validar(d, os.path.dirname(os.path.dirname(os.path.dirname(REFINAR))))
for x in r["errores"]: print("ERROR ", x)
for x in r["avisos"]: print("aviso ", x)
if not r["errores"]:
    gv.guardar(d, GUION, sobrescribir=True); print("guion guardado: objetos =", [e["nombre"] for e in d["objetos"]])
