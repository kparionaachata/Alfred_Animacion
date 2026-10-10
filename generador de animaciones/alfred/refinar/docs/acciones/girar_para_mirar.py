# -*- coding: utf-8 -*-
"""EJECUTOR GENERICO de la accion `girar_para_mirar` (esquema `alfred_accion_v1`): el personaje se endereza, gira el cuerpo y la cabeza hacia un PUNTO del mundo (otro personaje, un objeto...) y se queda mirandolo (hablando, p. ej.).
Los angulos se calculan solos a partir de `mirar_a` (coordenadas de mundo) y de como esta orientado el personaje en el frame `inicio`: giro del cuerpo (repartido entre el root y el cuello), inclinacion de la cabeza hacia abajo o arriba.
USO (dentro de Blender): ns = {"__name__": "accion", "ACCION_JSON": r"...\\accion.json"}; exec(open(r"...\\girar_para_mirar.py", encoding="utf-8").read(), ns)
Repetible (la clave de partida del frame `inicio` conserva la pose de ese frame; quita las claves que sobren despues del `fin`). No guarda el .blend."""
import importlib.util
import json
import math
import os

import bpy
from mathutils import Vector

REFINAR = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"; ADDON = os.path.join(REFINAR, "alfred_animation_studio")


def _cargar(n):
    sp = importlib.util.spec_from_file_location(n, os.path.join(ADDON, n + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


cu = _cargar("claves_util"); om = _cargar("objetos_mundo"); ss = om.ss
A_ = json.load(open(ACCION_JSON, encoding="utf-8")); P = A_["parametros"]; TT = A_["tiempos"]; sc = bpy.context.scene
AA = next(o for o in bpy.data.objects if o.type == "ARMATURE" and "Hips_alfred" in o.pose.bones); OO = AA.parent
F0, F1, FIN = int(TT["inicio"]), int(TT["giro_hasta"]), int(TT["fin"]); sc.frame_set(F0); bpy.context.view_layer.update()
PESOS = (("Spine_alfred", .32), ("Spine1_alfred", .34), ("Spine2_alfred", .34)); ROT0 = {b.name: tuple(b.rotation_euler) for b in AA.pose.bones}; LOC0 = tuple(OO.location); RZ0 = OO.rotation_euler[2]
FR = P["frente"]; ALTURA_OJOS = float(FR.get("altura_ojos", 0.236)); K_PITCH = float(FR.get("cuello_x_por_grado_de_mirada", 0.84))
ENDEREZA = P["enderezar"]; ROOT_XY = P["cuerpo"].get("root_xy", [LOC0[0], LOC0[1]]); REPARTO = float(P["cuerpo"].get("reparto_giro_cuerpo", 0.76))
# --- hacia donde hay que mirar: desde los ojos del personaje YA enderezado y en su sitio final (cuello sobre el root + ojos adelantados), refinando el angulo 4 veces
OFF = FR["cuello_sobre_root"]; cuello = Vector((ROOT_XY[0] + OFF[0], ROOT_XY[1] + OFF[1], LOC0[2] + OFF[2])); obj = Vector(P["mirar_a"]["loc"]); ADEL = float(FR.get("adelante_ojos", 0.267)); yaw_obj = 0.0
pitch_obj = 0.0
for _ in range(8):                                                                                   # los ojos se adelantan y bajan cuando la cabeza se inclina: se refina el yaw y el pitch juntos
    ph = math.radians(-pitch_obj); adel = ADEL * math.cos(ph) + ALTURA_OJOS * math.sin(ph); alto = ALTURA_OJOS * math.cos(ph) - ADEL * math.sin(ph)
    ojo = Vector((cuello.x + adel * math.cos(math.radians(yaw_obj)), cuello.y + adel * math.sin(math.radians(yaw_obj)), cuello.z + alto)); d = obj - ojo
    yaw_obj = math.degrees(math.atan2(d.y, d.x)); pitch_obj = math.degrees(math.atan2(d.z, math.hypot(d.x, d.y)))
yaw_ahora = float(FR["mira_a_grados"]) + math.degrees(RZ0) - float(FR["rz_deg"])                                          # hacia donde mira el cuerpo en F0
dyaw = (yaw_obj - yaw_ahora + 180.0) % 360.0 - 180.0; d_cuerpo = dyaw * REPARTO
if "rz_final_deg" in P["cuerpo"]: d_cuerpo = float(P["cuerpo"]["rz_final_deg"]) - math.degrees(RZ0)                     # rotacion Z FINAL del root (absoluta) dada por el usuario: el cuerpo gira hasta ahi y el cuello lleva el resto
d_cuello_y = dyaw - d_cuerpo
d_cuello_x = -pitch_obj / K_PITCH - float(ENDEREZA["cuello_deg"])                                                         # cuello X positivo = mirar hacia abajo; y se quita la compensacion que dejo la inclinacion anterior
d_cuello_z = 0.0
if "cuello_final_deg" in P:                                                                                   # valores FINALES del hueso del cuello dados por el usuario (X, Y, Z en grados, absolutos): mandan sobre el calculo de la mirada
    CF = P["cuello_final_deg"]; d_cuello_x = float(CF[0]) - math.degrees(ROT0["Neck_alfred"][0]); d_cuello_y = float(CF[1]) - math.degrees(ROT0["Neck_alfred"][1]); d_cuello_z = float(CF[2]) - math.degrees(ROT0["Neck_alfred"][2])
sc.frame_end = max(sc.frame_end, FIN)
for t in (AA.animation_data.nla_tracks if AA.animation_data else []):
    for s in t.strips:
        if t.name.startswith("Base") and s.frame_end < FIN: s.frame_end_ui = FIN
wa = cu.escritor_de(AA, 'pose.bones["Spine_alfred"].rotation_euler', 0, F0); wo = cu.escritor_de(OO, "location", 0, F0)
CV = P.get("cuello_durante_voz")                                                                      # el cuello tiene un valor FIJO (X, Y, Z grados absolutos) mientras dura una voz; antes llega a el y despues va al valor final
if CV: NV = [math.radians(float(v)) for v in CV["deg"]]; NF = [ROT0["Neck_alfred"][i] + math.radians(d_) for i, d_ in enumerate((d_cuello_x, d_cuello_y, d_cuello_z))]; FA, FB = int(CV["desde"]), int(CV["hasta"])
for k in range(F0, FIN + 1):
    u = ss((k - F0) / float(F1 - F0)) if k < F1 else 1.0
    for b, w in PESOS: wa.poner('pose.bones["%s"].rotation_euler' % b, 0, k, ROT0[b][0] - math.radians(float(ENDEREZA["inclinacion_deg"]) * w * u))
    if CV:
        for i in range(3):
            if k <= FA: v_ = ROT0["Neck_alfred"][i] + (NV[i] - ROT0["Neck_alfred"][i]) * ss((k - F0) / float(max(1, FA - F0)))
            elif k <= FB: v_ = NV[i]
            else: v_ = NV[i] + (NF[i] - NV[i]) * ss((k - FB) / float(max(1, FIN - FB)))
            wa.poner('pose.bones["Neck_alfred"].rotation_euler', i, k, v_)
    else:
        wa.poner('pose.bones["Neck_alfred"].rotation_euler', 0, k, ROT0["Neck_alfred"][0] + math.radians(d_cuello_x * u)); wa.poner('pose.bones["Neck_alfred"].rotation_euler', 1, k, ROT0["Neck_alfred"][1] + math.radians(d_cuello_y * u))
        if d_cuello_z: wa.poner('pose.bones["Neck_alfred"].rotation_euler', 2, k, ROT0["Neck_alfred"][2] + math.radians(d_cuello_z * u))
    wo.poner("location", 0, k, LOC0[0] + (ROOT_XY[0] - LOC0[0]) * u); wo.poner("location", 1, k, LOC0[1] + (ROOT_XY[1] - LOC0[1]) * u); wo.poner("location", 2, k, LOC0[2]); wo.poner("rotation_euler", 2, k, RZ0 + math.radians(d_cuerpo * u))
for b, w in PESOS: wa.limpiar('pose.bones["%s"].rotation_euler' % b, 0, FIN + 1)
for i in range(3 if (d_cuello_z or CV) else 2): wa.limpiar('pose.bones["Neck_alfred"].rotation_euler', i, FIN + 1)
for i in range(3): wo.limpiar("location", i, FIN + 1)
wo.limpiar("rotation_euler", 2, FIN + 1); wa.cerrar(); wo.cerrar()
for ob in (AA, OO):
    if ob.animation_data: ob.animation_data.use_nla = False; ob.animation_data.use_nla = True
    ob.update_tag()
sc.frame_set(FIN); bpy.context.view_layer.update()
print("%s: f%d-f%d | giro total %.1f grados (cuerpo %.1f + cuello %.1f), cuello X %+.1f, direccion al punto: yaw %.1f pitch %.1f" % (A_["id"], F0, FIN, dyaw, d_cuerpo, d_cuello_y, d_cuello_x, yaw_obj, pitch_obj))
