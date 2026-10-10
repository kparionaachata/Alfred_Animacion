# -*- coding: utf-8 -*-
"""EJECUTOR GENERICO de la accion `inclinarse_para_mirar` (esquema `alfred_accion_v1`): el personaje inclina el torso hacia delante (desde la cintura, repartido en Spine / Spine1 / Spine2), adelanta el cuerpo y levanta la cabeza
(el cuello compensa la inclinacion) para mirar algo que pasa delante de el (p. ej. por una ventana). Los numeros de la escena estan en el JSON de la accion; este script no tiene ninguno.
USO (dentro de Blender, con la escena abierta):
    ns = {"__name__": "accion", "ACCION_JSON": r"...\accion.json"}; exec(open(r"...\inclinarse_para_mirar.py", encoding="utf-8").read(), ns)
Repetible: la clave de partida (frame `inicio`) conserva la pose de ese frame, asi que volver a ejecutarlo sobre la misma escena da lo mismo. No guarda el .blend."""
import importlib.util
import json
import math
import os

import bpy

REFINAR = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"; ADDON = os.path.join(REFINAR, "alfred_animation_studio")


def _cargar(n):
    sp = importlib.util.spec_from_file_location(n, os.path.join(ADDON, n + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


cu = _cargar("claves_util"); om = _cargar("objetos_mundo"); ss = om.ss
A_ = json.load(open(ACCION_JSON, encoding="utf-8")); P = A_["parametros"]; TT = A_["tiempos"]; sc = bpy.context.scene
AA = next(o for o in bpy.data.objects if o.type == "ARMATURE" and "Hips_alfred" in o.pose.bones); OO = AA.parent
F0, F1, FIN = int(TT["inicio"]), int(TT["inclinado"]), int(TT["fin"]); sc.frame_set(F0); bpy.context.view_layer.update()
CU = P["cuerpo"]; LEAN = float(CU["inclinacion_deg"]); DX, DY = (float(v) for v in CU.get("avance_root_xy", [0, 0])); NECK = float(P["cuello"]["compensacion_deg"]); NECK_Y = float(P["cuello"].get("giro_deg", 0.0))
PESOS = (("Spine_alfred", .32), ("Spine1_alfred", .34), ("Spine2_alfred", .34))
ROT0 = {b.name: tuple(b.rotation_euler) for b in AA.pose.bones}; LOC0 = tuple(OO.location)
sc.frame_end = max(sc.frame_end, FIN)
for t in (AA.animation_data.nla_tracks if AA.animation_data else []):
    for s in t.strips:
        if t.name.startswith("Base") and s.frame_end < FIN: s.frame_end_ui = FIN
wa = cu.escritor_de(AA, 'pose.bones["Spine_alfred"].rotation_euler', 0, F0); wo = cu.escritor_de(OO, "location", 0, F0)
for k in range(F0, FIN + 1):
    u = ss((k - F0) / float(F1 - F0)) if k < F1 else 1.0
    for b, w in PESOS: wa.poner('pose.bones["%s"].rotation_euler' % b, 0, k, ROT0[b][0] + math.radians(LEAN * w * u))
    wa.poner('pose.bones["Neck_alfred"].rotation_euler', 0, k, ROT0["Neck_alfred"][0] + math.radians(NECK * u)); wa.poner('pose.bones["Neck_alfred"].rotation_euler', 1, k, ROT0["Neck_alfred"][1] + math.radians(NECK_Y * u))
    wo.poner("location", 0, k, LOC0[0] + DX * u); wo.poner("location", 1, k, LOC0[1] + DY * u); wo.poner("location", 2, k, LOC0[2])
for b, w in PESOS: wa.limpiar('pose.bones["%s"].rotation_euler' % b, 0, FIN + 1)                 # si antes duraba mas, se quitan las claves que sobran despues del fin
for i in range(2): wa.limpiar('pose.bones["Neck_alfred"].rotation_euler', i, FIN + 1)
for i in range(3): wo.limpiar("location", i, FIN + 1)
wa.cerrar(); wo.cerrar()
for ob in (AA, OO):
    if ob.animation_data: ob.animation_data.use_nla = False; ob.animation_data.use_nla = True
    ob.update_tag()
sc.frame_set(FIN); bpy.context.view_layer.update()
print("%s: f%d-f%d | inclinacion %.0f grados, avance (%.2f, %.2f) m, cuello %+.0f grados" % (A_["id"], F0, FIN, LEAN, DX, DY, NECK))
