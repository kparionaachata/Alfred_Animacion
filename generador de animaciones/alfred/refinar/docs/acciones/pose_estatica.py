# -*- coding: utf-8 -*-
"""POSE ESTATICA CON APARICION, SIN BLENDER (segundos): crea el guion portable de un personaje que APARECE en un frame, en la posicion y con la pose de un archivo de pose (el que extrae `Extractor_de_datos/pose_extractor_independent.py`), y se queda quieto.
  python pose_estatica.py <personaje> <pose.json> --desde 193 --duracion 48 [--nombre zombie_1_aparece] [--sin-aparicion]
    personaje   carpeta del personaje en `generador de animaciones` (zombie_1, jerry, zombie_baby_1 ...)
    pose.json   archivo de pose (de `poses/`): da la pose de los huesos y el root (posicion y rotacion Z)
    desde       frame en que aparece (primer frame visible); antes de ese frame el personaje esta oculto
    duracion    frames que se queda en esa pose (el guion cubre desde .. desde+duracion-1)
Escribe `<personaje>/refinar/configuraciones/guiones/configuracion_portable_<nombre>_f<a>_<b>.json` + una pose por frame en `<personaje>/refinar/poses/<nombre>_f<a>_<b>/`. Filtros organicos TODOS apagados (la pose queda exacta).
Se carga con el estudio del personaje (Cargar configuracion + Concatenar); la aparicion (mostrar/ocultar de todos sus objetos) la aplica el estudio al concatenar."""
import argparse
import copy
import hashlib
import json
import os
import re
import time

RAIZ = r"C:\Users\user\Desktop\Alfred_Animacion"; BASE = os.path.join(RAIZ, "generador de animaciones")
PLANTILLA = os.path.join(BASE, "alfred", "refinar", "configuraciones", "guiones", "configuracion_portable_alfred_se_inclina_para_mirar_afuera_f61_112.json")


def objetos_del_personaje(personaje):
    """nombres de todos los objetos del personaje: el root y todos sus descendientes (`estructura_lista/<personaje>.json`, relaciones padre-hijo)."""
    f = os.path.join(RAIZ, "estructura_lista", personaje + ".json")
    if os.path.exists(f): d = json.load(open(f, encoding="utf-8"))
    else:                                                                                                                  # zombie_2..5 no tienen estructura propia: es la de zombie_1 con el nombre cambiado
        d = json.loads(open(os.path.join(RAIZ, "estructura_lista", "zombie_1.json"), encoding="utf-8").read().replace("zombie_1", personaje))
    hijos = {}
    for r in d["relationships"]["parent_child"]: hijos.setdefault(r["parent"], []).append(r["child"])
    out = [personaje]; i = 0
    while i < len(out): out += [h for h in hijos.get(out[i], []) if h not in out]; i += 1
    return out


def crear(personaje, pose, desde, duracion, nombre=None, aparicion=True, objetos_ocultar=None):
    ref = os.path.join(BASE, personaje, "refinar"); d_pose = json.load(open(pose, encoding="utf-8"))["poses"][0]; nombre = nombre or personaje + "_aparece"; a = int(desde); b = a + int(duracion) - 1
    carpeta = "%s_f%d_%d" % (nombre, a, b); dir_poses = os.path.join(ref, "poses", carpeta); os.makedirs(dir_poses, exist_ok=True); dir_cfg = os.path.join(ref, "configuraciones", "guiones"); os.makedirs(dir_cfg, exist_ok=True)
    root = d_pose["root"]; arm = d_pose["armature"]; ts = time.strftime("%Y-%m-%dT%H:%M:%S") + ".000000"; manifiesto = []; aps = []
    ap = lambda k: {"pose_name": "%s_f%d" % (nombre, k), "json_file": os.path.join(dir_poses, "%s_f%d.json" % (nombre, k)), "duration": 1, "rot_x": root["rotation_euler_deg"]["x"], "rot_y": root["rotation_euler_deg"]["y"], "rot_z": root["rotation_euler_deg"]["z"],
                    "pos_x": root["location"]["x"], "pos_y": root["location"]["y"], "pos_z": root["location"]["z"], "interp_type": "LINEAR"}
    for k in range(a, b + 1):
        c = copy.deepcopy(d_pose); c.update({"label": "%s_f%d" % (nombre, k), "frame": k, "timestamp": ts}); ruta = os.path.join(dir_poses, "%s_f%d.json" % (nombre, k))
        with open(ruta, "w", encoding="utf-8", newline="\n") as f: json.dump({"poses": [c]}, f, indent=2, ensure_ascii=False)
        manifiesto.append({"frame": k, "archivo": os.path.basename(ruta), "sha256": hashlib.sha256(open(ruta, "rb").read()).hexdigest()}); aps.append(ap(k))
    C = json.load(open(PLANTILLA, encoding="utf-8")); seg = C.pop("alfred_segs")[0]; label = "01_" + nombre; clave = personaje + "_segs"
    seg.update({"label": label, "frame_start": a, "frame_end": b, "frame_start_planned": a, "frame_end_planned": b, "seg_action_name": "%sseg_%s" % (personaje, label), "export_desc": "%s aparece en f%d" % (personaje, a)})
    seg["action_poses"] = [dict(ap(k), pose_label="Frame %d" % k, entry_ratio=0.3, exit_ratio=0.3, manual_start=True, frame_abs_start=k) for k in range(a, b + 1)]
    seg["organic"] = {k: (False if k.endswith("_enabled") else v) for k, v in seg["organic"].items()}; seg["organic"]["enabled"] = True                      # sin filtros organicos: pose exacta
    for k in ("arm_stiffness_enabled", "arm_spasm_enabled", "tail_wag_enabled", "ear_osc_enabled", "jaw_osc_enabled", "emotion_enabled"): seg["organic"][k] = False
    C[clave] = [seg]; C["action_poses"] = aps; C["armature_name"] = arm; C["poses_dir"] = dir_poses; C["start_frame"] = a; C["description"] = "%s aparece en f%d con la pose de %s y se queda quieto %d frames." % (personaje, a, os.path.basename(pose), duracion)
    C["paso1_path"].update({"frame_inicio": a, "frame_fin_manual": b, "frames_parada": b - a + 1, "paradas_frames": [b - a + 1], "root_rot_z": root["rotation_euler_deg"]["z"],
                            "path_points": [{"coords": [root["location"]["x"], root["location"]["y"], root["location"]["z"]], "texture": "", "face_index": "-1", "tipo_segmento": "parada", "tipo_segmento_raw": "PARADA", "parada_frames_punto": b - a + 1}]})
    C["paso1_path"]["blend_filepath"] = os.path.join(RAIZ, "estructura_lista", personaje + ".blend"); C["estimacion_slots"] = {"fuente": "extraccion_exacta_blender", "slots": [{"slot": 1, "tipo": "parada", "label": label, "frames_estimados": b - a + 1}]}
    C["export_name"] = nombre; C["export_desc"] = C["description"]
    C["meta"] = {"nombre": nombre + "_portable", "titulo": C["description"], "personaje": personaje.upper(), "fps": 24, "frame_ini": a, "frame_fin": b, "fuente": [os.path.basename(pose)], "estado": "extraido_sin_aprobacion_nueva",
                 "notas": "Pose estatica (una pose repetida por frame en poses/%s). Aparece en f%d: antes esta oculto." % (carpeta, a)}
    C["anclas"] = {"aparece": a, "fin": b}; C["capas"] = []; C["exactos"] = []; C["objetos"] = []; C["audio"] = []; C["camara"] = []; C["movimiento"] = {}; C["sonidos"] = {"modo": "manual", "techo_voces": True, "manuales": []}
    objs = objetos_ocultar or objetos_del_personaje(personaje)                                                           # TODOS los objetos del personaje (ocultar solo el root no oculta a sus hijos)
    C["mundo"] = [{"id": "aparece_" + personaje, "accion": "mostrar", "objetos": objs, "t": "aparece", "nota": "el personaje aparece (antes esta oculto)"}] if aparicion else []
    C["portable"] = {"schema": "alfred_portable_clip_v1", "source_blend": "", "source_guion": "pose_estatica.py", "frame_range": [a, b], "pose_count": b - a + 1, "poses_directory": dir_poses, "pose_manifest": manifiesto, "required_target_objects": [personaje, arm], "required_bone": "Hips_" + personaje,
                     "reproduction_order": ["Cargar esta configuracion en el estudio de %s." % personaje, "Concatenar el segmento %s para hornear la pose." % label, "El estudio muestra al personaje en f%d (estaba oculto antes)." % a]}
    ruta = os.path.join(dir_cfg, "configuracion_portable_%s_f%d_%d.json" % (nombre, a, b))
    with open(ruta, "w", encoding="utf-8", newline="\n") as f: json.dump(C, f, ensure_ascii=False, indent=2)
    return ruta, b - a + 1


if __name__ == "__main__":
    ap_ = argparse.ArgumentParser(description=__doc__.split("\n")[0]); ap_.add_argument("personaje"); ap_.add_argument("pose"); ap_.add_argument("--desde", type=int, required=True); ap_.add_argument("--duracion", type=int, default=48); ap_.add_argument("--nombre"); ap_.add_argument("--sin-aparicion", action="store_true")
    p = ap_.parse_args(); r, n = crear(p.personaje, p.pose, p.desde, p.duracion, p.nombre, not p.sin_aparicion); print("guion escrito (%d frames): %s" % (n, r))
