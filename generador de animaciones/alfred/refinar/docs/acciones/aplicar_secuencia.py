# -*- coding: utf-8 -*-
"""APLICAR LA SECUENCIA EN BLENDER CON UNA SOLA EJECUCION: une los guiones portables de `secuencia_parte5.json` (en orden) en una configuracion, la carga en el Alfred Studio, concatena y aplica la camara.
Dentro de Blender (escena de la parte abierta):   exec(open(r"...\\aplicar_secuencia.py", encoding="utf-8").read(), {"__name__": "x"})
Variables opcionales en el dict: CONCATENAR=False (solo camara: segundos, util tras `ajustar.py camara`), ULTIMO_SOLO=True.
Para agregar una animacion nueva a la secuencia basta anadir su archivo a `secuencia_parte5.json`. No guarda el .blend."""
import copy
import json
import os
import sys

import bpy

REF = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"; G = os.path.join(REF, "configuraciones", "guiones")
if REF not in sys.path: sys.path.insert(0, REF)
if not hasattr(bpy.ops, "alfst") or not hasattr(bpy.ops.alfst, "load_config"):
    import alfred_animation_studio as _al; _al.register()
_conc = globals().get("CONCATENAR", True)
S = json.load(open(os.path.join(REF, "docs", "acciones", "secuencia_parte5.json"), encoding="utf-8")); gs = [json.load(open(os.path.join(G, f), encoding="utf-8")) for f in S["guiones"]]
for g_ in gs:                                                                                       # objetos de los assets portables (el stick, la antorcha...): se importan si no estan en la escena
    oa = g_["portable"].get("object_asset") or {}; nombres = list(oa.get("library_objects") or []) + list(oa.get("children") or [])
    if nombres and any(bpy.data.objects.get(n) is None for n in nombres) and os.path.exists(oa.get("path", "")):
        with bpy.data.libraries.load(oa["path"], link=False) as (src, dst): dst.objects = [n for n in src.objects if n in nombres and bpy.data.objects.get(n) is None]
        for o_ in dst.objects: bpy.context.scene.collection.objects.link(o_)
        print("asset importado:", [o_.name for o_ in dst.objects])
C = copy.deepcopy(gs[0]); C["alfred_segs"] = []; C["action_poses"] = []; fin = 0; cam = {}
for i, g in enumerate(gs):
    sg = copy.deepcopy(g["alfred_segs"][0]); skip = 0 if i == 0 else 1; poses = sg["action_poses"][skip:]; a, b = (g["portable"]["frame_range"][0] + skip), g["portable"]["frame_range"][1]
    sg.update({"action_poses": poses, "frame_start": a, "frame_end": b, "frame_start_planned": a, "frame_end_planned": b, "label": "%02d_%s" % (i + 1, g["alfred_segs"][0]["label"][3:]), "seg_action_name": "alfredseg_%02d_%s" % (i + 1, g["alfred_segs"][0]["label"][3:])})
    C["alfred_segs"].append(sg); C["action_poses"] += g["action_poses"][skip:]; fin = max(fin, b)
    for e in g.get("camara") or []:                                                      # camara: claves de cada canal se unen por frame; los movimientos se conservan
        if e["tipo"] == "claves":
            k = (e["objeto"], e["canal"]); m = cam.setdefault(k, dict(e, claves=[]))
            filas = {r[0]: r for r in m["claves"]}; filas.update({r[0]: r for r in e["claves"]}); m["claves"] = [filas[x] for x in sorted(filas)]
        else: cam[("mov", e["objeto"], e["desde"])] = e
C["paso1_path"]["frame_fin_manual"] = fin; C["meta"] = dict(C.get("meta") or {}, frame_ini=1, frame_fin=fin); C["camara"] = list(cam.values()); C["description"] = "Secuencia: " + " + ".join(S["guiones"]); C["mundo"] = [m for g in gs for m in g.get("mundo") or []]
C["objetos"] = [o for g in gs for o in g.get("objetos") or []]; C["sonidos"] = {"modo": "manual", "techo_voces": True, "manuales": [m for g in gs for m in (g.get("sonidos") or {}).get("manuales") or []]}; C["audio"] = [a for g in gs for a in g.get("audio") or []]
cfg = os.path.join(os.environ.get("TEMP", "."), "secuencia_parte5_combinada.json"); json.dump(C, open(cfg, "w", encoding="utf-8"))
sc = bpy.context.scene; r1 = bpy.ops.alfst.load_config(filepath=cfg)
if _conc: bpy.ops.alfredseg.concatenate_all()
try:
    if bpy.context.screen.is_animation_playing: bpy.ops.screen.animation_cancel(restore_frame=False)
except Exception: pass
rc = bpy.ops.alfst.cam_aplicar(); sc.frame_set(1)
print("SECUENCIA aplicada: %d guiones, f1-%d%s, camara aplicada" % (len(gs), fin, "" if _conc else " (sin concatenar)"))
for e_ in C["audio"]:                                                                              # voces con `cuello_fijo`: la pista de la armature de Voz Sync (cabeza + torso) se silencia (el cuello queda con los valores del guion)
    if e_.get("cuello_fijo"):
        nom_ = os.path.splitext(os.path.basename(e_["archivo"]))[0]; A_ = next((o for o in bpy.data.objects if o.type == "ARMATURE" and "Hips_alfred" in o.pose.bones), None)
        for t_ in (A_.animation_data.nla_tracks if A_ and A_.animation_data else []):
            if t_.name.startswith("VozSync_") and nom_ in t_.name:
                t_.mute = True                                                                       # (la influencia de la tira solo vale si esta animada: se silencia la pista de la armature; los ojos van en sus propias pistas)
        ini_ = int(e_["inicio"]) if isinstance(e_["inicio"], (int, float)) else None                              # las colas de las voces anteriores se apagan (influencia 1 -> 0) justo antes de esta voz
        for t2_ in (A_.animation_data.nla_tracks if A_ and A_.animation_data and ini_ else []):
            if t2_.name.startswith("VozSync_") and nom_ not in t2_.name:
                for s2_ in t2_.strips:
                    if s2_.frame_start < ini_ < s2_.frame_end: s2_.use_animated_influence = True; s2_.influence = 1.0; s2_.keyframe_insert("influence", frame=ini_ - 8); s2_.influence = 0.0; s2_.keyframe_insert("influence", frame=ini_)
exec(open(os.path.join(REF, "docs", "acciones", "aplicar_sonidos_alfred.py"), encoding="utf-8").read(), {"__name__": "x"})                       # sonidos de Alfred (volumen del guion) + ducking de las voces                       # las voces de los personajes mandan sobre los sonidos del juego
