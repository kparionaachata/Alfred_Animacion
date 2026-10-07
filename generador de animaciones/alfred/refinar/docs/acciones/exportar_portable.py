# -*- coding: utf-8 -*-
"""EXPORTADOR de acciones PORTABLES (formato `alfred_portable_clip_v1`, el que carga y concatena el flujo Alfred Animation Studio en cualquier otro .blend).
Para un rango de frames de la escena abierta escribe:
  poses/<nombre>_f<f0>_<f1>/<nombre>_f<k>.json     una pose por frame (22 huesos + root), con sha256 en el manifiesto
  objetos_portables/<nombre>_portable.blend         los objetos de la accion con sus animaciones (si hay)
  configuraciones/configuracion_portable_<nombre>_f<f0>_<f1>.json     la configuracion (segmento, anclas, objetos, mundo, sonidos, camara, audio, portable)
Se usa justo despues de ejecutar una accion (`colocar_objeto.py`) o de animar algo a mano, en el mismo Blender:
    ex = {"__name__": "exp", "SPEC": {...}}; exec(open(r"...\\exportar_portable.py", encoding="utf-8").read(), ex)
SPEC (claves): nombre, f0, f1, titulo, descripcion, label (nombre del segmento), objetos_asset [objetos de la escena a guardar con sus hijos], anclas {}, objetos [cfg de guion v2], mundo [], sonidos {modo, manuales},
exactos [], audio [], camara [], plantilla (ruta de un portable existente: de ahi salen los campos fijos del flujo), fuente_guion (ruta del .json de la accion o del guion), pasos (lista de textos para `reproduction_order`).
No guarda el .blend de la escena."""
import copy
import hashlib
import json
import math
import os
import time

import bpy

REFINAR = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"; S = SPEC
AA = next(o for o in bpy.data.objects if o.type == "ARMATURE" and "Hips_alfred" in o.pose.bones); OO = AA.parent; sc = bpy.context.scene
nombre = S["nombre"]; f0 = int(S["f0"]); f1 = int(S["f1"]); n = f1 - f0 + 1; carpeta = "%s_f%d_%d" % (nombre, f0, f1)
dir_poses = os.path.join(REFINAR, "poses", carpeta); dir_obj = os.path.join(REFINAR, "objetos_portables"); dir_cfg = os.path.join(REFINAR, "configuraciones")
for d_ in (dir_poses, dir_obj, dir_cfg): os.makedirs(d_, exist_ok=True)
R = lambda v, n_=6: round(float(v), n_)
xyz = lambda v, n_=6: {"x": R(v[0], n_), "y": R(v[1], n_), "z": R(v[2], n_)}
ts = time.strftime("%Y-%m-%dT%H:%M:%S") + ".000000"; blend = os.path.basename(bpy.data.filepath) or "sin_guardar.blend"
f_actual = sc.frame_current; manifiesto = []; raices = {}


def pose_json(k):
    sc.frame_set(k); bpy.context.view_layer.update(); bones = {}
    for b in AA.pose.bones:
        e = b.rotation_euler; q = b.rotation_quaternion; rl = xyz(b.location); rs = xyz(b.scale)
        bones[b.name] = {"parent": b.parent.name if b.parent else None, "connected": bool(b.bone.use_connect),
                         "local_space": {"location": rl, "rotation_euler_rad": xyz(e), "rotation_euler_deg": xyz([math.degrees(a) for a in e], 4), "rotation_quaternion": {"w": R(q.w), "x": R(q.x), "y": R(q.y), "z": R(q.z)}, "scale": rs},
                         "rotation_mode": b.rotation_mode, "raw_rotation_euler_deg": xyz([math.degrees(a) for a in e], 4), "raw_rotation_quaternion": None, "raw_location": rl, "raw_scale": rs}
    root = {"location": xyz(OO.location), "rotation_euler_deg": xyz([math.degrees(a) for a in OO.rotation_euler], 4), "scale": xyz(OO.scale)}; raices[k] = root
    return {"poses": [{"label": "%s_f%d" % (nombre, k), "frame": k, "armature": AA.name, "character": OO.name, "timestamp": ts, "blender_version": bpy.app.version_string, "file": blend, "bone_count": len(bones), "root": root, "bones": bones}]}


for k in range(f0, f1 + 1):
    arch = "%s_f%d.json" % (nombre, k); ruta = os.path.join(dir_poses, arch); txt = json.dumps(pose_json(k), indent=2, ensure_ascii=False)
    with open(ruta, "w", encoding="utf-8", newline="\n") as fh: fh.write(txt)
    manifiesto.append({"frame": k, "archivo": arch, "sha256": hashlib.sha256(open(ruta, "rb").read()).hexdigest()})
sc.frame_set(f_actual)

# --- asset de objetos
asset = None
if S.get("objetos_asset"):
    objs = set()
    for nm in S["objetos_asset"]:
        o = bpy.data.objects[nm]; objs.add(o); objs |= set(o.children_recursive)
    ruta_a = os.path.join(dir_obj, "%s_portable.blend" % nombre)
    bpy.data.libraries.write(ruta_a, objs, fake_user=True)
    asset = {"path": ruta_a, "sha256": hashlib.sha256(open(ruta_a, "rb").read()).hexdigest(), "root_object": S["objetos_asset"][0], "children": sorted(o.name for o in objs if o.name not in S["objetos_asset"]), "library_objects": sorted(o.name for o in objs)}

# --- configuracion
T = json.load(open(S["plantilla"], encoding="utf-8")); C = copy.deepcopy(T); label = S.get("label", "01_" + nombre); r0 = raices[f0]
rot_z = r0["rotation_euler_deg"]["z"]; ap_pos = lambda k: {"rot_x": raices[k]["rotation_euler_deg"]["x"], "rot_y": raices[k]["rotation_euler_deg"]["y"], "rot_z": raices[k]["rotation_euler_deg"]["z"], "pos_x": raices[k]["location"]["x"], "pos_y": raices[k]["location"]["y"], "pos_z": raices[k]["location"]["z"]}
C["timestamp"] = ts; C["description"] = S["descripcion"]; C["poses_dir"] = dir_poses; C["start_frame"] = f0
p1 = C["paso1_path"]; p1.update({"frame_inicio": f0, "frame_fin_manual": f1, "frames_parada": n, "paradas_frames": [n], "root_rot_z": rot_z}); p1["path_points"] = [{"coords": [r0["location"]["x"], r0["location"]["y"], r0["location"]["z"]], "texture": "", "face_index": "-1", "tipo_segmento": "parada", "tipo_segmento_raw": "PARADA", "parada_frames_punto": n}]
C["estimacion_slots"] = {"fuente": "extraccion_exacta_blender", "slots": [{"slot": 1, "tipo": "parada", "label": label, "frames_estimados": n}]}
base_ap = lambda k, i: dict({"pose_name": "%s_f%d" % (nombre, k), "json_file": os.path.join(dir_poses, "%s_f%d.json" % (nombre, k)), "duration": 1}, **ap_pos(k), interp_type="LINEAR")
C["action_poses"] = [dict(base_ap(k, i), pose_index=0) for i, k in enumerate(range(f0, f1 + 1))]
seg = C["alfred_segs"][0]; seg.update({"label": label, "frame_start": f0, "frame_end": f1, "frame_start_planned": f0, "frame_end_planned": f1, "seg_action_name": "alfredseg_" + label, "export_desc": S["titulo"]})
seg["action_poses"] = [dict(base_ap(k, i), pose_label="Frame %d" % k, entry_ratio=0.3, exit_ratio=0.3, manual_start=True, frame_abs_start=k) for i, k in enumerate(range(f0, f1 + 1))]
C["export_name"] = "alfred_" + nombre; C["export_desc"] = S["titulo"]
C["meta"] = {"nombre": nombre + "_portable", "titulo": S["titulo"], "personaje": "ALFRED", "fps": sc.render.fps, "frame_ini": f0, "frame_fin": f1, "fuente": [blend] + ([os.path.basename(S["fuente_guion"])] if S.get("fuente_guion") else []),
             "estado": "extraido_sin_aprobacion_nueva", "notas": S.get("notas", "Las poses se guardan una por frame (carpeta poses/%s) y se concatenan al cargar." % carpeta)}
C["anclas"] = S.get("anclas", {}); C["capas"] = S.get("capas", []); C["exactos"] = S.get("exactos", []); C["objetos"] = S.get("objetos", []); C["mundo"] = S.get("mundo", [])
C["audio"] = S.get("audio", []); C["sonidos"] = S.get("sonidos", {"modo": "manual", "techo_voces": True, "manuales": []}); C["camara"] = S.get("camara", []); C["movimiento"] = {}
C["portable"] = {"schema": "alfred_portable_clip_v1", "source_blend": bpy.data.filepath, "source_guion": S.get("fuente_guion", "embedded"), "frame_range": [f0, f1], "pose_count": n, "poses_directory": dir_poses, "pose_manifest": manifiesto,
                 "required_target_objects": [OO.name, AA.name], "required_bone": "Rightelbow_alfred", "reproduction_order": S.get("pasos", ["Cargar esta configuracion en Alfred Animation Studio.", "Concatenar el segmento %s para hornear las poses." % label])}
if asset: C["portable"]["object_asset"] = asset
C["portable"].pop("torch_asset", None)
ruta_c = os.path.join(dir_cfg, "configuracion_portable_%s_f%d_%d.json" % (nombre, f0, f1)) if not S.get("salida") else S["salida"]
with open(ruta_c, "w", encoding="utf-8", newline="\n") as fh: json.dump(C, fh, ensure_ascii=False, indent=2)
print("portable escrito:", ruta_c, "| poses:", n, "| asset:", bool(asset))
