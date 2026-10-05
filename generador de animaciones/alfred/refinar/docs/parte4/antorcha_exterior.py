# -*- coding: utf-8 -*-
"""PARTE 4 (base_parte_4.blend), tramo 1: Alfred, al ver su refugio rodeado de zombies, se saca una antorcha de la espalda con el brazo DERECHO y la coloca en (-94.5, -107.5, 14).
Continua DESPUES del f1160 (lo animado no se toca). Alfred esta en el pozo (z 13); la coordenada esta fuera del refugio, en el suelo, pasada la abertura del bloque cortado: se inclina hacia la abertura
(giro +50, inclinacion 30 grados en Spine / Spine1 / Spine2, root a (-95.15, -108.25)) y el brazo derecho llega con cinematica inversa (`parte3/ik_brazos.py`, error < 3 cm).
SE EJECUTA EN BLENDER (exec) con base_parte_4.blend abierta. Repetible: reescribe las claves de f1161 en adelante."""
import math
import importlib.util
import os

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

REFINAR = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"; ADDON = os.path.join(REFINAR, "alfred_animation_studio")
exec(open(os.path.join(REFINAR, "docs", "parte3", "ik_brazos.py"), encoding="utf-8").read(), globals())          # fk, mundo, cabeza_cola, resolver, AA (armature), OO (root)


def _cargar(n):
    sp = importlib.util.spec_from_file_location(n, os.path.join(ADDON, n + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


cu = _cargar("claves_util"); om = _cargar("objetos_mundo"); gv = _cargar("guion_v2")
sc = bpy.context.scene; F0 = 1160; sc.frame_set(F0); bpy.context.view_layer.update()
ROT0 = {b.name: tuple(b.rotation_euler) for b in AA.pose.bones}; LOC0 = {b.name: tuple(b.location) for b in AA.pose.bones}; ROOT0 = (tuple(OO.location), OO.rotation_euler[2])
TARGET = Vector((-94.5, -107.5, 14.25))                         # muneca: la antorcha (origen en su base) queda en (-94.5, -107.5, 14.0)
SUELO = Vector((-94.5, -107.5, 14.0))
T = {"espalda": 1172, "alcance": 1190, "suelta": 1192, "quieto": 1198, "vuelve": 1216, "fin": 1236}
DYAW, LEAN, ROOT2 = 50.0, 30.0, (-95.15, -108.25)
ss = om.ss


def pose_M(root, dyaw, lean, z=13.0):
    rot = {k: list(v) for k, v in ROT0.items()}
    for b, w in (("Spine_alfred", .32), ("Spine1_alfred", .34), ("Spine2_alfred", .34)): rot[b][0] += math.radians(lean * w)
    return fk(rot, LOC0), mundo((root[0], root[1], z), ROOT0[1] + math.radians(dyaw))


# --- brazo derecho: tres posturas (reposo = la del f1160, espalda, alcance)
q_rest = Euler(ROT0["RightUpArm_alfred"], 'XYZ').to_quaternion(); x_rest = ROT0["Rightelbow_alfred"][0]
M0, Mw0 = pose_M(ROOT0[0][:2], 0, 0)
back_pt = M0["Spine1_alfred"].translation; back_w = Mw0 @ back_pt
BACK = Vector((back_w.x - 0.27, back_w.y - 0.12, back_w.z + 0.06))                              # sitio de la antorcha en la espalda (detras del omoplato derecho)
q_back, qe_back, e_back, codo_back = resolver("Right", M0["Spine2_alfred"], Mw0, BACK, codo_hint=BACK + Vector((-0.05, -0.2, -0.2)), inicio=(q_rest, x_rest), iters=5000, semilla=3)
M2, Mw2 = pose_M(ROOT2, DYAW, LEAN)
q_reach, qe_reach, e_reach, codo_reach = resolver("Right", M2["Spine2_alfred"], Mw2, TARGET, inicio=(q_back, 2 * math.atan2(qe_back.x, qe_back.w)), iters=6000, semilla=2)
x_back = 2 * math.atan2(qe_back.x, qe_back.w); x_reach = 2 * math.atan2(qe_reach.x, qe_reach.w)
print("errores de la muneca (m): espalda %.3f, alcance %.3f" % (e_back, e_reach))


def mezcla(a, b, u):
    return a.slerp(b if a.dot(b) >= 0 else -b, u)


def estado(k):
    """-> (lean, dyaw, root_xy, q hombro, x codo) en el frame k."""
    if k <= T["espalda"]: u = ss((k - F0) / (T["espalda"] - F0)); return 0.0, 0.0, 0.0, mezcla(q_rest, q_back, u), x_rest + (x_back - x_rest) * u
    if k <= T["alcance"]:
        u = ss((k - T["espalda"]) / (T["alcance"] - T["espalda"])); return LEAN * u, DYAW * u, u, mezcla(q_back, q_reach, u), x_back + (x_reach - x_back) * u
    if k <= T["quieto"]: return LEAN, DYAW, 1.0, q_reach, x_reach
    if k <= T["vuelve"]:
        u = ss((k - T["quieto"]) / (T["vuelve"] - T["quieto"])); return LEAN * (1 - u), DYAW * (1 - u), 1 - u, mezcla(q_reach, q_rest, u), x_reach + (x_rest - x_reach) * u
    return 0.0, 0.0, 0.0, q_rest, x_rest


# --- extender el rango y la tira base del NLA
sc.frame_end = T["fin"]
for t in AA.animation_data.nla_tracks:
    for s in t.strips:
        if t.name.startswith("Base") and s.frame_end < T["fin"]: s.frame_end_ui = T["fin"]
# --- claves
wa = cu.escritor_de(AA, 'pose.bones["Spine_alfred"].rotation_euler', 0, F0 + 1); wo = cu.escritor_de(OO, "location", 0, F0 + 1)
prev = Euler(ROT0["RightUpArm_alfred"], 'XYZ')
for k in range(F0 + 1, T["fin"] + 1):
    lean, dyaw, ur, q, x = estado(k)
    for b, w in (("Spine_alfred", .32), ("Spine1_alfred", .34), ("Spine2_alfred", .34)): wa.poner('pose.bones["%s"].rotation_euler' % b, 0, k, ROT0[b][0] + math.radians(lean * w))
    e = q.to_euler('XYZ', prev); prev = e
    for i in range(3): wa.poner('pose.bones["RightUpArm_alfred"].rotation_euler', i, k, e[i])
    wa.poner('pose.bones["Rightelbow_alfred"].rotation_euler', 0, k, x)
    for i in range(2): wo.poner("location", i, k, ROOT0[0][i] + (ROOT2[i] - ROOT0[0][i]) * ur)
    wo.poner("location", 2, k, ROOT0[0][2]); wo.poner("rotation_euler", 2, k, ROOT0[1] + math.radians(dyaw))
wa.cerrar(); wo.cerrar()
for ob in (AA, OO):
    if ob.animation_data: ob.animation_data.use_nla = False; ob.animation_data.use_nla = True
    ob.update_tag()
sc.frame_set(T["alcance"]); bpy.context.view_layer.update()
mw = AA.matrix_world @ AA.pose.bones["Rightelbow_alfred"].tail
print("muneca real en f%d: %s (objetivo %s, error %.1f cm)" % (T["alcance"], [round(c, 3) for c in mw], list(TARGET), (mw - TARGET).length * 100))

# --- la antorcha 3: copia de la antorcha 2 (vacio + malla + llama + humo + luz), sale de la espalda y se asienta en el suelo
if bpy.data.objects.get("antorcha_3") is None:
    raiz = bpy.data.objects["antorcha_2"]; objs = [raiz] + list(raiz.children_recursive); mp = {}; col = bpy.data.collections.new("antorcha_3"); sc.collection.children.link(col)
    for x in objs:
        c = x.copy()
        if x.type == 'LIGHT': c.data = x.data.copy()
        c.name = "antorcha_3" if x is raiz else x.name.replace("_a2", "") + "_a3"; mp[x] = c; col.objects.link(c)
        if c.animation_data: c.animation_data_clear()
        if x.type == 'LIGHT' and c.data.animation_data: c.data.animation_data_clear()
    for x in objs:
        if x.parent: mp[x].parent = mp[x.parent]; mp[x].matrix_parent_inverse = x.matrix_parent_inverse.copy()
    mp[raiz].location = SUELO; mp[raiz].rotation_mode = 'QUATERNION'; mp[raiz].rotation_quaternion = (1, 0, 0, 0)
agarre = om.agarre_desde_mundo("Armature", "Rightelbow_alfred", T["alcance"], list(SUELO), [0, 0, 0])
e0 = bpy.data.objects["torch1.light.002"].data.energy
cfg = {"id": "obj_antorcha_3", "nombre": "antorcha_3", "armature": "Armature", "hueso": "Rightelbow_alfred", "escala_mano": 1.0, "coleccion": "antorcha_3", "copia_jerarquia_de": "antorcha_2",
       "inicial": {"loc": [-95.9, -108.6, 14.2], "escala": 0.001, "visible": True}, "agarres": {"mano": {"matriz": agarre, "origen": "su sitio final en el suelo (-94.5, -107.5, 14), relativo a la mano en f%d" % T["alcance"]}},
       "eventos": [{"tipo": "en_mano", "t": T["espalda"], "agarre": "mano", "pop": {"dur": 3, "escala": 1.0}, "nota": "la saca de la espalda con el brazo derecho"},
                   {"tipo": "asienta", "t": T["suelta"], "dur": 3, "vivo": True, "en": {"loc": list(SUELO), "rot": [0, 0, 0], "escala": 1.0}, "nota": "la coloca en el suelo fuera del refugio, (-94.5, -107.5, 14), derecha"}]}
mun = {"id": "mun_luz_antorcha3", "accion": "luz", "t": 1, "objeto": "antorcha_3", "energia": round(e0, 4), "claves": [[1, 0.0], [T["espalda"], 0.0], [T["espalda"] + 3, 1.0], [T["fin"], 1.0]], "nota": "la luz solo existe desde que se saca"}
guion = {"version": "2.0", "meta": {"titulo": "Parte 4 - Alfred coloca una antorcha fuera del refugio", "frame_fin": T["fin"], "base": "base_parte_4.blend"}, "anclas": {"espalda": T["espalda"], "alcance": T["alcance"], "fin": T["fin"]}, "objetos": [cfg], "mundo": [mun]}
g = gv.migrar(guion)
res = om.calcular(bpy.context, g, frames=list(range(1, 3)) + list(range(F0 - 2, T["fin"] + 1)))
om.aplicar(bpy.context, res); om.aplicar_mundo_luces(bpy.context, g)
ob = bpy.data.objects["antorcha_3"]; sc.frame_set(T["fin"]); bpy.context.view_layer.update()
print("antorcha_3 en f%d: %s escala %.2f" % (T["fin"], [round(c, 3) for c in ob.matrix_world.translation], ob.matrix_world.to_scale().x))
sc.frame_set(F0)
import json
os.makedirs(os.path.join(REFINAR, "configuraciones"), exist_ok=True)
with open(os.path.join(REFINAR, "configuraciones", "guion_alfred_parte4.json"), "w", encoding="utf-8", newline="\n") as f: json.dump(guion, f, ensure_ascii=False, indent=1)
