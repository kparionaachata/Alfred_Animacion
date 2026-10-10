# -*- coding: utf-8 -*-
"""ALFRED SE AGARRA EL PECHO (como un ataque al corazon), SIN ABRIR TU ESCENA: portable individual que PARTE de la pose de un archivo (la pose final del susto) y la anima durante `inicio..fin`.
Corre en Blender headless sobre la escena estatica (necesita el rig de Alfred solo para la IK de los brazos):
  blender -b base_parte_5_estatica.blend --python agarrarse_pecho.py -- <accion.json>
Que hace: las dos manos suben al pecho (IK de `docs/parte3/ik_brazos.py`, la derecha cruzada sobre el lado izquierdo del esternon), el torso se encorva hacia delante (`encorva_deg`, y poco a poco `encorva_extra_deg` mas), la cabeza cae (`cabeza_cae_deg`) y desde `tiembla_desde` todo el cuerpo tiembla (tremor de `tremor_hz`).
El resto de la pose (piernas, root) queda como en el archivo. Organico apagado. Escribe `configuracion_portable_<nombre>_f<a>_<b>.json` + una pose por frame."""
import json
import math
import os
import sys

import bpy
from mathutils import Euler, Quaternion, Vector

AQUI = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones"; sys.path.insert(0, AQUI)
import pose_estatica as pe
exec(open(os.path.join(AQUI, "..", "parte3", "ik_brazos.py"), encoding="utf-8").read(), globals())                     # fk, mundo, resolver, AA, OO

A_ = json.load(open(sys.argv[sys.argv.index("--") + 1], encoding="utf-8")); P = A_["parametros"]; T = A_["tiempos"]; F0, FIN = int(T["inicio"]), int(T["fin"]); PF = P["pose_inicio"]; E = P["pecho"]
base = json.load(open(PF, encoding="utf-8"))["poses"][0]; rt = base["root"]; RZ = rt["rotation_euler_deg"]["z"]; ROOT = (rt["location"]["x"], rt["location"]["y"], rt["location"]["z"])
rot0 = {n: (b["local_space"]["rotation_euler_rad"]["x"], b["local_space"]["rotation_euler_rad"]["y"], b["local_space"]["rotation_euler_rad"]["z"]) for n, b in base["bones"].items()}; loc0 = {n: (b["local_space"]["location"]["x"], b["local_space"]["location"]["y"], b["local_space"]["location"]["z"]) for n, b in base["bones"].items()}
SP = (("Spine_alfred", .32), ("Spine1_alfred", .34), ("Spine2_alfred", .34)); ss = lambda x: max(0.0, min(1.0, x)) ** 2 * (3 - 2 * max(0.0, min(1.0, x)))
LEAN_FIN = float(E["encorva_deg"]) + float(E["encorva_extra_deg"]); CAE = float(E["cabeza_cae_deg"])
# --- IK de las dos manos con el torso ya encorvado (pose final del agarre)
rot_f = {k: list(v) for k, v in rot0.items()}
for b, w in SP: rot_f[b][0] += math.radians(LEAN_FIN * w)
M = fk(rot_f, loc0); Mw = mundo(ROOT, math.radians(RZ)); sp2 = Mw @ M["Spine2_alfred"].translation; th = math.radians(RZ + 450.0); fwd = Vector((math.cos(th), math.sin(th), 0)); izq = Vector((-math.sin(th), math.cos(th), 0)); arriba = Vector((0, 0, 1))
res = {}
for lado, off in (("Right", E["mano_derecha"]), ("Left", E["mano_izquierda"])):
    up, el = lado + "UpArm_alfred", lado + "elbow_alfred"; tgt = sp2 + fwd * off[0] + izq * off[1] + arriba * off[2]; sg = -1.0 if lado == "Left" else 1.0
    hint = tgt - izq * (0.22 * (1 if lado == "Right" else -1)) + Vector((0, 0, -0.15))
    q0 = Euler(rot0[up], 'XYZ').to_quaternion(); q, qe, err, codo = resolver(lado, M["Spine2_alfred"], Mw, tgt, codo_hint=hint, inicio=(q0, rot0[el][0]), iters=7000, semilla=5)
    res[lado] = (q0, q, rot0[el][0], 2 * math.atan2(qe.x, qe.w)); print("IK %s: error de muneca %.3f m, mano %s" % (lado, err, [round(c, 3) for c in tgt]))
# --- portable (estructura + config) y poses por frame
nombre = "alfred_se_agarra_el_pecho"; ruta, n = pe.crear("alfred", PF, F0, FIN - F0 + 1, nombre, aparicion=False); C = json.load(open(ruta, encoding="utf-8")); D = C["poses_dir"]; man = []
ts = lambda f: 2 * math.pi * f
for f in range(F0, FIN + 1):
    t = f - F0; u1 = ss(t / float(E["sube_frames"])); u2 = ss(t / float(E["encorva_frames"])); lean = float(E["encorva_deg"]) * u2 + float(E["encorva_extra_deg"]) * ss((t - E["encorva_frames"]) / float(FIN - F0 - E["encorva_frames"]))
    a = ss((f - int(E["tiembla_desde"])) / 6.0) if f >= int(E["tiembla_desde"]) else 0.0; hz = float(E["tremor_hz"]) / 24.0
    fp = json.load(open(os.path.join(D, "%s_f%d.json" % (nombre, f)), encoding="utf-8")); c = fp["poses"][0]; bo = c["bones"]; eul = {k: list(v) for k, v in rot0.items()}
    for b, w in SP: eul[b][0] += math.radians(lean * w)
    eul["Neck_alfred"][0] += math.radians(CAE * u2)
    eul["Spine1_alfred"][0] += math.radians(1.3 * a) * math.sin(ts(f * hz) + 0.4); eul["Spine2_alfred"][2] += math.radians(0.9 * a) * math.sin(ts(f * hz * 0.83)); eul["Neck_alfred"][2] += math.radians(1.1 * a) * math.sin(ts(f * hz * 1.21) + 1.0)
    for lado in ("Right", "Left"):
        q0, q1, x0, x1 = res[lado]; qq = q0.slerp(q1 if q0.dot(q1) >= 0 else -q1, u1); e = qq.to_euler('XYZ', Euler(rot0[lado + "UpArm_alfred"], 'XYZ')); eul[lado + "UpArm_alfred"] = [e.x, e.y, e.z]; eul[lado + "elbow_alfred"] = [x0 + (x1 - x0) * u1, 0.0, 0.0]
        eul[lado + "UpArm_alfred"][0] += math.radians(0.8 * a) * math.sin(ts(f * hz * 0.9) + (0.0 if lado == "Right" else 2.0))
    for hn, hb in bo.items():
        ls = hb["local_space"]; r = eul[hn]; ls["rotation_euler_rad"] = {"x": round(r[0], 6), "y": round(r[1], 6), "z": round(r[2], 6)}; ls["rotation_euler_deg"] = {k: round(math.degrees(r[i]), 4) for i, k in enumerate("xyz")}
        hb["raw_rotation_euler_deg"] = dict(ls["rotation_euler_deg"])
    import hashlib
    p = os.path.join(D, "%s_f%d.json" % (nombre, f)); json.dump(fp, open(p, "w", encoding="utf-8", newline="\n"), indent=2, ensure_ascii=False); man.append({"frame": f, "archivo": os.path.basename(p), "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest()})
C["portable"]["pose_manifest"] = man; C["description"] = A_["descripcion"]; C["export_desc"] = C["description"]; C["meta"]["titulo"] = A_["titulo"]; C["meta"]["notas"] = "Parte de la pose de %s (pose final del susto) y la anima: manos al pecho, torso encorvado, cabeza caida y temblor desde f%d." % (os.path.basename(PF), int(E["tiembla_desde"]))
C["anclas"] = {"inicio_pose": F0, "manos_al_pecho": F0 + int(E["sube_frames"]), "encorvado": F0 + int(E["encorva_frames"]), "tiembla_desde": int(E["tiembla_desde"]), "fin": FIN}
json.dump(C, open(ruta, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2); print("PECHO: portable escrito (%d frames): %s" % (n, ruta))
