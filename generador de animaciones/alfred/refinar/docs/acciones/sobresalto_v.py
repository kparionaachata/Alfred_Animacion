# -*- coding: utf-8 -*-
"""EJECUTOR GENERICO de la accion `sobresalto_v` (esquema `alfred_accion_v1`): el personaje voltea hacia un PUNTO del mundo (cuerpo + cabeza), se asusta y levanta los dos brazos en forma de V (con rebote ELASTIC_IN_OUT), se inclina hacia atras y retrocede un poco; se queda asi hasta `fin`.
Los angulos se calculan solos: la mirada actual se MIDE en el frame `inicio` (ojos respecto al cuello) y se lleva al punto `mirar_a`; los brazos se resuelven con la pose final del tronco para que la V quede simetrica respecto al cuerpo.
USO (dentro de Blender): ns = {"__name__": "accion", "ACCION_JSON": r"...\\accion.json"}; exec(open(r"...\\sobresalto_v.py", encoding="utf-8").read(), ns)
Repetible (la clave de partida del frame `inicio` conserva la pose de ese frame; quita las claves que sobren despues del `fin`). No guarda el .blend."""
import importlib.util
import json
import math
import os

import bpy
from mathutils import Matrix, Quaternion, Vector

REFINAR = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"; ADDON = os.path.join(REFINAR, "alfred_animation_studio")


def _cargar(n):
    sp = importlib.util.spec_from_file_location(n, os.path.join(ADDON, n + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


def elastico(x):                                                                                       # easeInOutElastic (ELASTIC_IN_OUT): rebasa los extremos y oscila
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    c = (2 * math.pi) / 4.5
    return -(2 ** (20 * x - 10) * math.sin((20 * x - 11.125) * c)) / 2 if x < 0.5 else (2 ** (-20 * x + 10) * math.sin((20 * x - 11.125) * c)) / 2 + 1


cu = _cargar("claves_util"); om = _cargar("objetos_mundo"); ss = om.ss
A_ = json.load(open(ACCION_JSON, encoding="utf-8")); P = A_["parametros"]; TT = A_["tiempos"]; sc = bpy.context.scene
AA = next(o for o in bpy.data.objects if o.type == "ARMATURE" and "Hips_alfred" in o.pose.bones); OO = AA.parent
F0, F1, F2, FIN = int(TT["inicio"]), int(TT["giro_hasta"]), int(TT["susto_hasta"]), int(TT["fin"]); FN = F0 + int(TT.get("cuello_frames", 10))
sc.frame_set(F0); bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
PESOS = (("Spine_alfred", .32), ("Spine1_alfred", .34), ("Spine2_alfred", .34)); BRAZOS = ("RightUpArm_alfred", "LeftUpArm_alfred")
ROT0 = {b.name: tuple(b.rotation_euler) for b in AA.pose.bones}; LOC0 = tuple(OO.location); RZ0 = OO.rotation_euler[2]
FR = P["frente"]; ALTURA_OJOS = float(FR.get("altura_ojos", 0.236)); K_PITCH = float(FR.get("cuello_x_por_grado_de_mirada", 0.84)); ADEL = float(FR.get("adelante_ojos", 0.267)); OFF = FR["cuello_sobre_root"]
SUSTO = P["susto"]; LEAN = float(SUSTO["inclinacion_atras_deg"]); RECULA = float(SUSTO["retrocede_m"]); ALFA = math.radians(float(SUSTO["v_angulo_deg"])); NECK_Y_REPOSO = float(P["cuello_y_reposo_deg"])
# --- mirada actual medida en F0 (ojos respecto a la cabeza del cuello; sesgo de ojos 3.8 grados en yaw, como en la calibracion)
def ojos():
    es = []
    for n in ("ojo_izquierdo_alfred", "ojo_derecho_alfred"):
        o = bpy.data.objects[n].evaluated_get(dg); me = o.to_mesh(); c = sum((o.matrix_world @ v.co for v in me.vertices), Vector()) / len(me.vertices); o.to_mesh_clear(); es.append(c)
    return (es[0] + es[1]) / 2
v = ojos() - (AA.matrix_world @ AA.pose.bones["Neck_alfred"].head); yaw_ahora = math.degrees(math.atan2(v.y, v.x)) + 3.8; pitch_ahora = math.degrees(math.atan2(v.z - ALTURA_OJOS, math.hypot(v.x, v.y)))
yaw_cuerpo0 = float(FR["mira_a_grados"]) + math.degrees(RZ0) - float(FR["rz_deg"]); cuello_y0 = math.degrees(ROT0["Neck_alfred"][1]) - NECK_Y_REPOSO
# --- hacia donde mirar: desde los ojos del personaje YA retrocedido (el retroceso cambia el angulo); se refina 8 veces
obj = Vector(P["mirar_a"]["loc"]); yaw_obj = yaw_ahora; pitch_obj = pitch_ahora
for _ in range(8):
    rec = Vector((-math.cos(math.radians(yaw_obj)), -math.sin(math.radians(yaw_obj)), 0)) * RECULA; cuello = Vector((LOC0[0] + rec.x + OFF[0], LOC0[1] + rec.y + OFF[1], LOC0[2] + OFF[2]))
    ph = math.radians(-pitch_obj); adel = ADEL * math.cos(ph) + ALTURA_OJOS * math.sin(ph); alto = ALTURA_OJOS * math.cos(ph) - ADEL * math.sin(ph)
    ojo = Vector((cuello.x + adel * math.cos(math.radians(yaw_obj)), cuello.y + adel * math.sin(math.radians(yaw_obj)), cuello.z + alto)); d = obj - ojo
    yaw_obj = math.degrees(math.atan2(d.y, d.x)); pitch_obj = math.degrees(math.atan2(d.z, math.hypot(d.x, d.y)))
d_cuerpo = (yaw_obj - yaw_cuerpo0 + 180.0) % 360.0 - 180.0                                                # el cuerpo queda de frente al punto; el cuello vuelve a su reposo
d_cuello_y = NECK_Y_REPOSO - math.degrees(ROT0["Neck_alfred"][1])                                       # deshace la torsion del cuello (la que dejo mirar a Jerry)
d_cuello_x = -(pitch_obj - pitch_ahora) / K_PITCH                                  # solo la mirada (la compensacion de la inclinacion se suma con el susto)
comp_x = LEAN / K_PITCH                                                                                 # el torso hacia atras sube la mirada LEAN grados: el cuello baja para seguir mirando
rz_fin = RZ0 + math.radians(d_cuerpo); dir_atras = (-math.cos(math.radians(yaw_obj)), -math.sin(math.radians(yaw_obj)))
# --- brazos en V: pose final del tronco puesta, direcciones de mundo (arriba +- lado) -> rotacion local de cada brazo (arco minimo desde la pose actual)
guardar = {}
def poner(pb, e): guardar.setdefault(pb.name, tuple(pb.rotation_euler)); pb.rotation_euler = e
for b, w in PESOS: poner(AA.pose.bones[b], (ROT0[b][0] - math.radians(LEAN * w), ROT0[b][1], ROT0[b][2]))
poner(AA.pose.bones["Neck_alfred"], (ROT0["Neck_alfred"][0], ROT0["Neck_alfred"][1] + math.radians(d_cuello_y), ROT0["Neck_alfred"][2]))
OO.rotation_euler[2] = rz_fin; bpy.context.view_layer.update()
lado = (AA.matrix_world @ AA.pose.bones["RightUpArm_alfred"].head) - (AA.matrix_world @ AA.pose.bones["LeftUpArm_alfred"].head); lado.z = 0; lado.normalize()
Q1 = {}
for nb, signo in (("RightUpArm_alfred", 1.0), ("LeftUpArm_alfred", -1.0)):
    pb = AA.pose.bones[nb]; Mw = AA.matrix_world @ pb.matrix; cur = (Mw.to_3x3() @ Vector((0, 1, 0))).normalized(); dest = (Vector((0, 0, math.cos(ALFA))) + lado * (signo * math.sin(ALFA))).normalized()
    R = cur.rotation_difference(dest).to_matrix(); M3 = R @ Mw.to_3x3(); Mn = Matrix.Translation(Mw.translation) @ M3.to_4x4()
    pb.matrix = AA.matrix_world.inverted() @ Mn; Q1[nb] = tuple(pb.rotation_euler); guardar.setdefault(nb, ROT0[nb])
for nm, e in guardar.items(): AA.pose.bones[nm].rotation_euler = e                                        # restituye lo que se toco
OO.rotation_euler[2] = RZ0; sc.frame_set(F0); bpy.context.view_layer.update()
from mathutils import Euler
def qeul(e): return Euler(e, 'XYZ').to_quaternion()
def arco(n, f):                                                                                         # rotacion a fraccion f (puede pasar de 1: rebote) por el arco entre la pose actual y la V
    a = qeul(ROT0[n]); b = qeul(Q1[n]); dq = a.inverted() @ b; ax, ang = dq.to_axis_angle()
    if ang > math.pi: ang -= 2 * math.pi
    return a @ Quaternion(ax, ang * f)
sc.frame_end = max(sc.frame_end, FIN)
for t in (AA.animation_data.nla_tracks if AA.animation_data else []):
    for s in t.strips:
        if t.name.startswith("Base") and s.frame_end < FIN: s.frame_end_ui = FIN
wa = cu.escritor_de(AA, 'pose.bones["Spine_alfred"].rotation_euler', 0, F0); wo = cu.escritor_de(OO, "location", 0, F0); prev = {n: Euler(ROT0[n], 'XYZ') for n in BRAZOS}
for k in range(F0, FIN + 1):
    uc = ss((k - F0) / float(F1 - F0)) if k < F1 else 1.0; un = ss((k - F0) / float(FN - F0)) if k < FN else 1.0
    e = elastico((k - F1) / float(F2 - F1)) if k > F1 else 0.0                                          # sobresalto: rebote elastico
    for b, w in PESOS: wa.poner('pose.bones["%s"].rotation_euler' % b, 0, k, ROT0[b][0] - math.radians(LEAN * w * e))
    wa.poner('pose.bones["Neck_alfred"].rotation_euler', 0, k, ROT0["Neck_alfred"][0] + math.radians(d_cuello_x * un + comp_x * e)); wa.poner('pose.bones["Neck_alfred"].rotation_euler', 1, k, ROT0["Neck_alfred"][1] + math.radians(d_cuello_y * un))
    for n in BRAZOS:
        eu = arco(n, e).to_euler('XYZ', prev[n]); prev[n] = eu
        for i in range(3): wa.poner('pose.bones["%s"].rotation_euler' % n, i, k, eu[i])
    wo.poner("location", 0, k, LOC0[0] + dir_atras[0] * RECULA * e); wo.poner("location", 1, k, LOC0[1] + dir_atras[1] * RECULA * e); wo.poner("location", 2, k, LOC0[2]); wo.poner("rotation_euler", 2, k, RZ0 + math.radians(d_cuerpo * uc))
for b, w in PESOS: wa.limpiar('pose.bones["%s"].rotation_euler' % b, 0, FIN + 1)
for i in range(2): wa.limpiar('pose.bones["Neck_alfred"].rotation_euler', i, FIN + 1)
for n in BRAZOS:
    for i in range(3): wa.limpiar('pose.bones["%s"].rotation_euler' % n, i, FIN + 1)
for i in range(3): wo.limpiar("location", i, FIN + 1)
wo.limpiar("rotation_euler", 2, FIN + 1); wa.cerrar(); wo.cerrar()
for ob in (AA, OO):
    if ob.animation_data: ob.animation_data.use_nla = False; ob.animation_data.use_nla = True
    ob.update_tag()
sc.frame_set(FIN); bpy.context.view_layer.update()
print("%s: f%d-f%d | giro cuerpo %.1f, cuello Y %.1f, X %.1f, mirada al punto yaw %.1f pitch %.1f | V %.0f grados, inclinacion atras %.0f, retrocede %.2f m" % (A_["id"], F0, FIN, d_cuerpo, d_cuello_y, d_cuello_x, yaw_obj, pitch_obj, math.degrees(ALFA), LEAN, RECULA))
