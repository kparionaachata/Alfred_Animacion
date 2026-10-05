# -*- coding: utf-8 -*-
"""S03 (objetos): agrega al guion las 3 herramientas que Alfred lanza (pico de madera, hacha de madera, hacha de piedra): estan en su espalda desde f1, la mano las coge en su frame (`de_espalda_en`: sin salto), las lanza
(vuelo de 10 f con giro) y quedan en el montoncito delante de el. Datos: matriz `rel_spine1` de cada herramienta (su sitio en la espalda) y su reposo en el montoncito (leidos de la escena). Para el hacha de piedra se
conservan los eventos de f984 en adelante y se agrega un `coloca` (puente) en f980 con su estado de ese momento, hasta que el tramo S05 (barrido sobre Jerry) se migre.
SE EJECUTA EN BLENDER (exec) con la escena de la parte 3 ya generada. Repetible (deja .bak)."""
import importlib.util
import os

import bpy
from mathutils import Matrix

REFINAR = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"; ADDON = os.path.join(REFINAR, "alfred_animation_studio"); GUION = os.path.join(REFINAR, "configuraciones", "guion_alfred_parte3.json")


def _cargar(n):
    sp = importlib.util.spec_from_file_location(n, os.path.join(ADDON, n + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


gv = _cargar("guion_v2"); om = _cargar("objetos_mundo"); d = gv.cargar(GUION); sc = bpy.context.scene; f0 = sc.frame_current
TIEMPOS = {"alcanza": 9, "sostiene": 2, "lanza": 12, "vuelve": 12}; FLY_D = 10
TOOLS = [("wooden_pickaxe", "Right", 206, 1), ("wooden_axe", "Left", 224, -1), ("stone_axe", "Right", 242, 1)]               # (objeto, mano, frame en que la coge, sentido del giro)


def estado(nombre, frame):
    sc.frame_set(frame); bpy.context.view_layer.update(); mw = bpy.data.objects[nombre].matrix_world
    return {"loc": [round(c, 5) for c in mw.to_translation()], "quat": [round(c, 6) for c in mw.to_quaternion().normalized()], "escala": round(mw.to_scale().x, 4)}


for nombre, lado, gf, sgn in TOOLS:
    ob = bpy.data.objects[nombre]; rel = ob["rel_spine1"]; kr = gf + TIEMPOS["sostiene"] + TIEMPOS["lanza"]; reposo = estado(nombre, kr + FLY_D + 2); ini = estado(nombre, 1)
    nuevos = [{"tipo": "guarda", "t": 1, "hasta": 2, "escala": ini["escala"], "nota": "en la espalda desde el principio"}, {"tipo": "toma", "t": gf, "hasta": gf, "agarre": "lanzar", "nota": "la mano la coge tal como esta en la espalda"},
              {"tipo": "lanza", "t": kr, "vuelo": FLY_D, "a": reposo, "giro": {"eje": [0, 1, 0], "de": 360.0 * sgn, "a": 0.0}, "nota": "vuelo parabolico con giro hasta el montoncito delante de sus pies"}]
    e = next((o for o in d["objetos"] if o["nombre"] == nombre), None)
    if e is None:
        e = gv.agregar(d, "objetos", {"nombre": nombre, "blend": None, "armature": "Armature", "hueso": lado + "elbow_alfred", "escala_mano": ini["escala"], "escala_espalda": ini["escala"], "agarres": {}, "eventos": []}, id="obj_" + nombre)
        e.pop("blend")
    e["espalda"] = {"hueso": "Spine1_alfred", "armature": "Armature", "matriz": om.mat16(Matrix([list(rel[i:i + 4]) for i in range(0, 16, 4)])), "origen": "propiedad rel_spine1 de %s (su sitio en la espalda al empezar)" % nombre}
    e.setdefault("agarres", {})["lanzar"] = {"de_espalda_en": gf, "origen": "la mano coge la herramienta tal como esta en la espalda en f%d (sin salto)" % gf}
    antes = [ev for ev in e.get("eventos", []) if ev["tipo"] not in ("coloca",) and not (isinstance(ev["t"], int) and ev["t"] < 900 and ev["tipo"] in ("guarda", "toma", "lanza")) and not (ev.get("agarre") == "lanzar")]
    e["inicial"] = {"loc": ini["loc"], "quat": ini["quat"], "escala": ini["escala"], "visible": True}
    if nombre == "stone_axe":                                                                    # puente hasta que el tramo S05 (barrido sobre Jerry) se migre
        puente = {"tipo": "coloca", "t": 980, "en": estado(nombre, 983), "nota": "PUENTE: su estado real en f983 (el tramo S05 todavia no esta migrado)"}; nuevos.append(puente)
    e["eventos"] = nuevos + antes
sc.frame_set(f0)
r = gv.validar(d, os.path.dirname(os.path.dirname(os.path.dirname(REFINAR))))
for x in r["errores"]: print("ERROR ", x)
if not r["errores"]:
    gv.guardar(d, GUION, sobrescribir=True); print("guion guardado:", {o["nombre"]: [(ev["tipo"], ev["t"]) for ev in o["eventos"]] for o in d["objetos"] if o["nombre"].startswith(("wooden", "stone_axe"))})
