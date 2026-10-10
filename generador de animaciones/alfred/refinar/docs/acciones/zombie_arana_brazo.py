# -*- coding: utf-8 -*-
"""ZOMBIE QUE ARAÑA CON UN BRAZO (esquema `alfred_accion_v1`, tipo `arana_brazo`), SIN ABRIR TU ESCENA: modifica las poses por frame de un portable (solo los huesos del brazo) desde `inicio` hasta `fin`.
Corre en Blender headless sobre la escena estatica de la parte (necesita el armature del personaje, solo para calcular la IK):
  blender -b base_parte_5_estatica.blend --python zombie_arana_brazo.py -- <accion.json> <configuracion_portable.json>
El portable debe cubrir `inicio..fin` (ver `caminar_a_pose.py --fin`). IK de 2 huesos: la mano sigue un zarpazo circular hacia `apunta_a`; se mezcla desde la pose de `inicio`. Actualiza los sha256 del manifiesto. Repetible."""
import hashlib
import json
import math
import os
import sys

import bpy
from mathutils import Euler, Matrix, Vector

acc_f, cfg_f = sys.argv[sys.argv.index("--") + 1:][:2]
A_ = json.load(open(acc_f, encoding="utf-8")); P = A_["parametros"]; T = A_["tiempos"]; C = json.load(open(cfg_f, encoding="utf-8")); D = C["portable"]["poses_directory"]; PERS = P["personaje"]
F0, FE, FIN = int(T["inicio"]), int(T["estira_frames"]), int(T["fin"]); BASE = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones"
AR = bpy.data.objects[PERS + "_Armature"]; RT = bpy.data.objects[PERS]; nU, nE = P["brazo"]["hombro"], P["brazo"]["codo"]; pU, pE = AR.pose.bones[nU], AR.pose.bones[nE]
base = json.load(open(os.path.join(BASE, P["pose_base"]), encoding="utf-8"))["poses"][0]; r = base["root"]
RT.location = (r["location"]["x"], r["location"]["y"], r["location"]["z"]); RT.rotation_euler = (0, 0, math.radians(r["rotation_euler_deg"]["z"]))
for n, b in base["bones"].items():
    pb = AR.pose.bones[n]; pb.rotation_mode = 'XYZ'; ls = b["local_space"]; pb.location = (ls["location"]["x"], ls["location"]["y"], ls["location"]["z"]); pb.rotation_euler = (ls["rotation_euler_rad"]["x"], ls["rotation_euler_rad"]["y"], ls["rotation_euler_rad"]["z"])
bpy.context.view_layer.update(); W = AR.matrix_world; E0 = {nU: tuple(pU.rotation_euler), nE: tuple(pE.rotation_euler)}
S = W @ pU.head; L1 = ((W @ pE.head) - S).length; L2 = ((W @ pE.tail) - (W @ pE.head)).length; mano0 = W @ pE.tail
aim = Vector(P["apunta_a"]["loc"]); dirn = (aim - S).normalized(); arriba = Vector((0, 0, 1)); lado = dirn.cross(arriba).normalized(); arriba = lado.cross(dirn).normalized()
polo = Vector(P["polo_codo"]); alc = float(P["alcance"]) * (L1 + L2); AR_ = P["arana"]; per = float(AR_["periodo_frames"]); rad = float(AR_["radio_m"]); av = float(AR_["avance_m"]); var = float(AR_["variacion"])


def arco(pb, destino):
    """gira el hueso (arco minimo) para que su eje head->tail apunte a `destino` (mundo), conservando la posicion de su cabeza."""
    Mw = AR.matrix_world @ pb.matrix; cur = (Mw.to_3x3() @ Vector((0, 1, 0))).normalized(); R_ = cur.rotation_difference(destino.normalized()).to_matrix()
    pb.matrix = AR.matrix_world.inverted() @ (Matrix.Translation(Mw.translation) @ (R_ @ Mw.to_3x3()).to_4x4()); bpy.context.view_layer.update()


def ik(mano):
    for n in (nU, nE): AR.pose.bones[n].rotation_euler = E0[n]
    bpy.context.view_layer.update(); v = mano - S; d = min(max(v.length, abs(L1 - L2) + 1e-3), L1 + L2 - 1e-3); u = v.normalized(); a = (d * d + L1 * L1 - L2 * L2) / (2 * d); h = math.sqrt(max(L1 * L1 - a * a, 0.0))
    pv = (polo - u * polo.dot(u)).normalized(); cod = S + u * a + pv * h
    arco(pU, cod - S); cabeza = AR.matrix_world @ pE.head; arco(pE, mano - cabeza)                          # el codo se calcula ya con el hombro girado
    return tuple(pU.rotation_euler), tuple(pE.rotation_euler)


def mano_en(f):
    t = f - (F0 + FE); th = 2 * math.pi * t / per; amp = rad * (1 + var * math.sin(0.73 * t + 1.0)); ext = alc + av * math.sin(th - 1.2)
    p = S + dirn * min(ext, alc + av) + (arriba * math.cos(th) + lado * math.sin(th)) * amp
    return p


def ss(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


prev = {nU: Euler(E0[nU], 'XYZ'), nE: Euler(E0[nE], 'XYZ')}; man = {m["frame"]: m for m in C["portable"]["pose_manifest"]}; maxdist = 0.0
for f in range(F0, FIN + 1):
    objetivo = mano_en(max(f, F0 + FE)) if f >= F0 + FE else None
    w = ss((f - F0) / float(FE)); eU, eE = ik(mano_en(f) if f >= F0 + FE else mano_en(F0 + FE)); res = {}
    for n, ei in ((nU, eU), (nE, eE)):
        e = Euler(tuple(E0[n][i] + (ei[i] - E0[n][i]) * w for i in range(3)), 'XYZ'); res[n] = e.copy()
    ruta = os.path.join(D, man[f]["archivo"]); fp = json.load(open(ruta, encoding="utf-8")); c = fp["poses"][0]
    for n, e in res.items():
        ls = c["bones"][n]["local_space"]; ls["rotation_euler_rad"] = dict(zip("xyz", [round(v, 6) for v in e])); ls["rotation_euler_deg"] = dict(zip("xyz", [round(math.degrees(v), 4) for v in e]))
        c["bones"][n]["raw_rotation_euler_deg"] = dict(ls["rotation_euler_deg"])
    json.dump(fp, open(ruta, "w", encoding="utf-8", newline="\n"), indent=2, ensure_ascii=False); man[f]["sha256"] = hashlib.sha256(open(ruta, "rb").read()).hexdigest()
    maxdist = max(maxdist, (mano_en(f) - S).length)
C["description"] = C.get("description", "") + " Desde f%d, el brazo derecho se estira hacia Alfred y da arañazos (hasta f%d)." % (F0, FIN); C["export_desc"] = C["description"]; C.setdefault("meta", {})["titulo"] = C["description"]
C.setdefault("anclas", {})["arana_desde"] = F0 + FE; C["anclas"]["fin"] = FIN
json.dump(C, open(cfg_f, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
print("ARANA: f%d-f%d | brazo %.3f+%.3f m, alcance %.3f, mano a maxima distancia %.3f del hombro" % (F0, FIN, L1, L2, alc, maxdist))
