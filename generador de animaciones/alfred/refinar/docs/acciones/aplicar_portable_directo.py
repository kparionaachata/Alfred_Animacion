# -*- coding: utf-8 -*-
"""APLICAR UN PORTABLE DIRECTO EN BLENDER, SIN ESTUDIO: para personajes cuyo estudio aun no tiene el flujo v2 (zombie_2..5). Lee `configuracion_portable_*.json` (+ las poses por frame de su carpeta) y deja claves por frame en el root y en los huesos del armature.
Dentro de Blender:  PORTABLES = [r"...\\configuracion_portable_zombie_2_rodea_refugio_f1_240.json", ...]; exec(open(r"...\\aplicar_portable_directo.py", encoding="utf-8").read(), {"__name__": "x", "PORTABLES": PORTABLES})
Sustituye la accion del root y del armature (accion nueva, sin NLA), muestra los objetos de la seccion `mundo` (mostrar) y no guarda el .blend. Repetible."""
import json
import math
import os

import bpy

res = []
for cfg in globals()["PORTABLES"]:
    C = json.load(open(cfg, encoding="utf-8")); d = C["portable"]["poses_directory"]; man = C["portable"]["pose_manifest"]; pers = C["meta"]["personaje"].lower(); root = bpy.data.objects[pers]
    arm = bpy.data.objects[C["armature_name"]]
    for o in (root, arm):
        if o.animation_data is None: o.animation_data_create()
        ad = o.animation_data; ad.action = None
        for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    for m in C.get("mundo") or []:
        t_m = m.get("t"); t_m = C.get("anclas", {}).get(t_m, 1) if isinstance(t_m, str) else (t_m or 1); t_m = int(t_m)
        for n in m["objetos"]:
            o = bpy.data.objects.get(n)
            if o is None: continue
            if o.animation_data and o.animation_data.action: o.animation_data.action = None
            if t_m > 1:                                                                   # aparece en t_m: oculto antes (claves de visibilidad), visible desde t_m
                for ocul, fr in ((True, 1), (True, t_m - 1), (False, t_m)):
                    o.hide_viewport = ocul; o.hide_render = ocul; o.keyframe_insert("hide_viewport", frame=fr); o.keyframe_insert("hide_render", frame=fr)
            else:
                o.hide_viewport = False; o.hide_render = False
                try: o.hide_set(False)
                except Exception: pass
    for pb in arm.pose.bones: pb.rotation_mode = 'XYZ'
    sc = bpy.context.scene; prev = sc.frame_current
    for fila in man:
        fr = fila["frame"]; p = json.load(open(os.path.join(d, fila["archivo"]), encoding="utf-8"))["poses"][0]; r = p["root"]
        root.location = (r["location"]["x"], r["location"]["y"], r["location"]["z"]); root.rotation_euler = tuple(math.radians(r["rotation_euler_deg"][k]) for k in "xyz")
        root.keyframe_insert("location", frame=fr); root.keyframe_insert("rotation_euler", frame=fr)
        for hn, hb in p["bones"].items():
            pb = arm.pose.bones.get(hn)
            if pb is None: continue
            ls = hb["local_space"]; pb.location = (ls["location"]["x"], ls["location"]["y"], ls["location"]["z"]); pb.rotation_euler = (ls["rotation_euler_rad"]["x"], ls["rotation_euler_rad"]["y"], ls["rotation_euler_rad"]["z"])
            pb.keyframe_insert("location", frame=fr, group=hn); pb.keyframe_insert("rotation_euler", frame=fr, group=hn)
    sc.frame_set(1); res.append((pers, len(man)))
print("PORTABLES aplicados:", res)
