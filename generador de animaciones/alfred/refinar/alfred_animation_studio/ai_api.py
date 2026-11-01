# -*- coding: utf-8 -*-
"""
ai_api.py -- API para que una IA arme animaciones de Alfred.

DOS FLUJOS (ver refinar/docs/FLUJOS_MANUAL_E_IA.md):
  MANUAL  paneles del add-on + guion .json (configuraciones/): receta editable del usuario.
  IA      la IA crea poses/segmentos con este modulo y guarda el RESULTADO COMPLETO en
          animaciones_ia/<nombre>/ con ai_export (.animacion.json + .py autonomo + manifest).
          El guion es opcional para la IA: nunca debe ser cuello de botella.

Este modulo NO registra clases ni cambia el comportamiento del add-on: se importa a demanda.
Las funciones de guion (guion_*, seg_*) son el PUENTE: permiten a la IA usar el motor manual
escribiendo un guion NUEVO (nunca sobrescribir el del usuario).

    from alfred_animation_studio import ai_api
"""
import bpy
import copy
import json
import math
import os
from datetime import datetime

from .constants import BONES_LISTA, INTERP_TYPE_ITEMS
from . import config_ops

INTERPS_VALIDOS = {it[0] for it in INTERP_TYPE_ITEMS}

_ROOT = "alfred"
_ARM = "Armature"

# bone -> flag filter_* del segmento (True = bone bloqueado en todo el segmento)
BONE_A_FILTRO = {
    "Hips_alfred": "filter_hips", "Spine_alfred": "filter_spine",
    "Spine1_alfred": "filter_spine1", "Spine2_alfred": "filter_spine2",
    "Neck_alfred": "filter_neck", "face_alfred": "filter_face",
    "RightUpArm_alfred": "filter_right_arm", "Rightelbow_alfred": "filter_right_elbow",
    "LeftUpArm_alfred": "filter_left_arm", "Leftelbow_alfred": "filter_left_elbow",
    "RightUpLeg_alfred": "filter_right_leg", "Rightknee_alfred": "filter_right_knee",
    "LeftUpLeg_alfred": "filter_left_leg", "Leftknee_alfred": "filter_left_knee",
    "Armature": "filter_main_bone",
}

# Rangos heuristicos (radianes, eje local) para detectar poses imposibles.
# Solo aplican a poses "normales": se pueden pasar rangos propios a chequear_frames().
RANGOS_ANATOMICOS = {
    "Rightelbow_alfred": {"z": (-2.8, 0.3)},
    "Leftelbow_alfred": {"z": (-0.3, 2.8)},
    "Rightknee_alfred": {"x": (-0.4, 2.6)},
    "Leftknee_alfred": {"x": (-0.4, 2.6)},
}


def _scene():
    return bpy.context.scene


def _st():
    return _scene().alfst


def _poses_dir():
    return bpy.path.abspath(_st().poses_dir)


# =============================================================================
# ESTADO
# =============================================================================

def estado():
    """Resumen compacto de la escena para que la IA decida sin abrir la UI."""
    sc = _scene()
    out = {
        "frame_actual": sc.frame_current,
        "rango": [sc.frame_start, sc.frame_end],
        "fps": sc.render.fps,
    }
    root = bpy.data.objects.get(_ROOT)
    if root:
        out["root"] = {
            "loc": [round(v, 3) for v in root.location],
            "rot_deg": [round(math.degrees(v), 1) for v in root.rotation_euler],
            "nla": [
                {"pista": t.name, "tiras": [(s.name, int(s.frame_start), int(s.frame_end)) for s in t.strips]}
                for t in (root.animation_data.nla_tracks if root.animation_data else [])
            ],
        }
    if hasattr(sc, "alfred_path"):
        pc = sc.alfred_path
        out["recorrido"] = {
            "puntos": [
                {"i": i, "coords": [round(c, 2) for c in p.coords], "tipo": p.tipo_segmento, "textura": p.texture}
                for i, p in enumerate(pc.path_points)
            ],
            "walk_styles": [w.style for w in pc.walk_styles],
            "frames_por_bloque": pc.frames_por_bloque,
            "frames_parada": pc.frames_parada,
            "paradas_frames": [p.frames for p in pc.paradas_frames],
        }
    if hasattr(sc, "alfred_segs"):
        out["segmentos"] = [
            {
                "i": i, "label": s.label, "frames": [s.frame_start, s.frame_end],
                "poses": [(p.json_file, p.duration, p.interp_type) for p in s.action_poses],
                "bloqueados": [a for a in BONE_A_FILTRO.values() if getattr(s, a, False)],
            }
            for i, s in enumerate(sc.alfred_segs.segments)
        ]
    return out


# =============================================================================
# GUION (.json de configuracion)
# =============================================================================

def guion_desde_escena():
    return config_ops._serialize_configuracion(_st())


def guion_leer(ruta):
    with open(bpy.path.abspath(ruta), "r", encoding="utf-8") as f:
        return json.load(f)


def guion_escribir(data, ruta):
    ruta = bpy.path.abspath(ruta)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    data = dict(data)
    data["timestamp"] = datetime.now().isoformat()
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return ruta


def guion_aplicar(data):
    """
    Carga un guion (dict) en la escena con el mismo codigo que 'Importar Configuracion'.

    El cargador original perdia las PARADA en Blender 5.2 (validaba tipo_segmento contra
    bl_rna...enum_items, vacio en este enum dinamico). Ya esta corregido en config_ops.py; aqui se
    reasigna igual desde tipo_segmento_raw por si el add-on instalado aun es la copia vieja, y se
    resincronizan paradas_frames / walk_styles.

    FLUJO MANUAL: el guion es la receta editable del usuario. Una IA puede usar estas funciones
    (flujo puente) o saltarse el guion y guardar su resultado con ai_export (FLUJO IA).
    """
    config_ops._aplicar_configuracion(_st(), data)
    from . import path_recorder
    pc = _scene().alfred_path
    p1 = data.get("paso1_path", {})
    for pt, d in zip(pc.path_points, p1.get("path_points", [])):
        raw = d.get("tipo_segmento_raw", "AUTO")
        if raw != "AUTO" and pt.tipo_segmento != raw:
            try:
                pt.tipo_segmento = raw
            except TypeError:
                pass
        if "parada_frames_punto" in d:
            pt.parada_frames_punto = d["parada_frames_punto"]
    path_recorder.sync_paradas_frames(pc)
    path_recorder.sync_walk_styles(pc)
    for i, w in enumerate(p1.get("walk_styles", [])):
        if i < len(pc.walk_styles):
            pc.walk_styles[i].style = w["style"]
    for i, f in enumerate(p1.get("paradas_frames", [])):
        if i < len(pc.paradas_frames):
            pc.paradas_frames[i].frames = int(f)
    return estado()


def guion_aplicar_segmentos(data):
    """Carga solo los segmentos del Paso 3 del guion (sin re-disparar ojos/recorrido)."""
    config_ops._aplicar_alfred_segs(_st(), data.get("alfred_segs", []))
    return estado()


def ojos_fijar(shape, tramos, ojos=("ojo_izquierdo_alfred", "ojo_derecho_alfred")):
    """
    Retoque de una shape key de los ojos DESPUES de concatenar (se pierde al volver a concatenar).
    tramos: [(frame_ini, frame_fin, valor_ini, valor_fin)], interpolacion lineal, sobre los keyframes
    ya horneados. Sirve para corregir rampas: el sistema de ojos solo pone claves en los intervalos que
    usan la shape key, y entre dos usos distantes la interpola (ej. 'Closed' se cerraba poco a poco
    durante un salto entero).
    """
    from .blender_compat import get_fcurves
    n = 0
    for nombre in ojos:
        o = bpy.data.objects[nombre]
        ad = o.data.shape_keys.animation_data
        for fc in get_fcurves(ad):
            if fc.data_path != f'key_blocks["{shape}"].value':
                continue
            for a, b, v0, v1 in tramos:
                for fr, val in ((a, v0), (b, v1)):
                    if any(abs(k.co.x - fr) < 0.01 for k in fc.keyframe_points):
                        continue
                    fc.keyframe_points.add(1)
                    kp = fc.keyframe_points[len(fc.keyframe_points) - 1]
                    kp.co = (fr, val)
                    kp.handle_left = (fr - 1, val)
                    kp.handle_right = (fr + 1, val)
                    n += 1
            fc.update()
            for kp in fc.keyframe_points:
                f = kp.co.x
                for a, b, v0, v1 in tramos:
                    if a < f < b:
                        kp.co.y = v0 + (v1 - v0) * (f - a) / (b - a)
                        n += 1
            for kp in fc.keyframe_points:
                if any(a <= kp.co.x <= b for a, b, _, _ in tramos):
                    kp.interpolation = "LINEAR"
                    kp.handle_left.y = kp.handle_right.y = kp.co.y
            fc.update()
    return n


def concatenar(**kw):
    """Ejecuta 'Concatenar segmentos' (alfredseg.concatenate_all) y devuelve el resultado + estado NLA."""
    r = bpy.ops.alfredseg.concatenate_all(**kw)
    return {"operador": str(r), "estado": estado()}


def validar_guion(data):
    """Devuelve lista de problemas (vacia = ok). No modifica nada."""
    problemas = []
    pdir = bpy.path.abspath(data.get("poses_dir") or _st().poses_dir)
    for si, seg in enumerate(data.get("alfred_segs", [])):
        f0, f1 = seg.get("frame_start", 0), seg.get("frame_end", 0)
        for pi, p in enumerate(seg.get("action_poses", [])):
            jf = p.get("json_file", "")
            if not os.path.isfile(os.path.join(pdir, jf)):
                problemas.append(f"seg {si} pose {pi}: no existe {jf}")
            if p.get("interp_type") not in INTERPS_VALIDOS:
                problemas.append(f"seg {si} pose {pi}: interp_type invalido {p.get('interp_type')}")
            if p.get("duration", 0) < 1:
                problemas.append(f"seg {si} pose {pi}: duration < 1")
            if p.get("manual_start"):
                fa = p.get("frame_abs_start", 0)
                if fa < f0 or fa > f1:
                    problemas.append(f"seg {si} pose {pi}: frame_abs_start {fa} fuera de {f0}-{f1}")
        for bb in seg.get("bone_blocks", []):
            if bb.get("bone_key") not in BONE_A_FILTRO.values():
                problemas.append(f"seg {si}: bone_key desconocido {bb.get('bone_key')}")
    return problemas


# ---- edicion de guion (sobre el dict, sin tocar Blender) ---------------------

def guion_recorrido(data, tipos=None, walk_styles=None, frames_por_bloque=None, quitar_desde=None):
    """
    tipos: {indice_punto: 'PARADA'|'AUTO'|...} (enum de tipo_segmento).
    walk_styles: lista de estilos ('NORMAL','LENTO','HERIDO','RAPIDO','CORRER'), uno por tramo caminar.
    quitar_desde: elimina los puntos con indice >= quitar_desde.
    """
    d = data["paso1_path"]
    if quitar_desde is not None:
        d["path_points"] = d["path_points"][:quitar_desde]
    for i, t in (tipos or {}).items():
        d["path_points"][i]["tipo_segmento_raw"] = t
        d["path_points"][i]["tipo_segmento"] = t.lower()
    if walk_styles is not None:
        d["walk_styles"] = [{"style": s, "applied_style": s} for s in walk_styles]
        d["walk_style"] = walk_styles[0] if walk_styles else "NORMAL"
    if frames_por_bloque is not None:
        d["frames_por_bloque"] = frames_por_bloque
    return data


def pose_item(json_file, duration, interp="SMOOTH", pos=(0, 0, 0), rot=(0, 0, 0),
              entry=0.3, exit=0.3, inicio=None, label=None):
    """Una pose de segmento. pos/rot: root absoluto (mundo, grados) -- ver crear_pose()."""
    return {
        "json_file": json_file, "pose_label": label or json_file[:-5], "pose_name": label or json_file[:-5],
        "duration": int(duration), "entry_ratio": entry, "exit_ratio": exit, "interp_type": interp,
        "rot_x": rot[0], "rot_y": rot[1], "rot_z": rot[2],
        "pos_x": pos[0], "pos_y": pos[1], "pos_z": pos[2],
        "manual_start": inicio is not None, "frame_abs_start": int(inicio or 0),
    }


def seg_poner_poses(data, seg_idx, items):
    data["alfred_segs"][seg_idx]["action_poses"] = list(items)
    return data


def seg_bordes(data, seg_idx, entrada=0, salida=0, minimo=4):
    """
    Suaviza las uniones de un segmento. El motor arranca cada segmento EXACTAMENTE en su primera pose y
    termina en la ultima (salto seco contra la base del tramo vecino). Con esto se deja un hueco de
    `entrada` frames al inicio y `salida` al final donde manda la animacion base (Capa 1): las poses
    entran y salen mezclandose desde/hacia la base en vez de aparecer de golpe.
    No usar `salida` si lo que sigue es otro segmento con poses continuas (ej. caida -> rodar).
    """
    seg = data["alfred_segs"][seg_idx]
    ps = seg["action_poses"]
    if entrada > 0:
        ps[0]["duration"] = max(minimo, ps[0]["duration"] - entrada)
        ps[0]["manual_start"] = True
        ps[0]["frame_abs_start"] = seg["frame_start"] + entrada
    if salida > 0:
        ps[-1]["duration"] = max(minimo, ps[-1]["duration"] - salida)
    return data


def seg_bloquear(data, seg_idx, huesos=(), intervalos=None):
    """
    huesos: bloqueo total (todo el segmento). 'Armature' bloquea el root (no lo mueven las poses).
    intervalos: {hueso: [(f0, f1), ...]} bloqueo solo en esos frames.
    """
    seg = data["alfred_segs"][seg_idx]
    for h in huesos:
        seg[BONE_A_FILTRO[h]] = True
    if intervalos:
        bb = seg.setdefault("bone_blocks", [])
        for h, ivs in intervalos.items():
            key = BONE_A_FILTRO[h]
            entry = next((e for e in bb if e["bone_key"] == key), None)
            if entry is None:
                entry = {"bone_key": key, "intervals": []}
                bb.append(entry)
            for a, b in ivs:
                entry["intervals"].append({"frame_start": int(a), "frame_end": int(b), "enabled": True})
    return data


# =============================================================================
# POSES
# =============================================================================

def listar_poses(filtro=""):
    filtro = filtro.lower()
    return [f for f in sorted(os.listdir(_poses_dir())) if f.endswith(".json") and filtro in f.lower()]


def _record_hueso(rot_deg, loc, scale):
    return {
        "parent": None, "connected": False,
        "local_space": {
            "location": {"x": loc[0], "y": loc[1], "z": loc[2]},
            "rotation_euler_rad": {"x": math.radians(rot_deg[0]), "y": math.radians(rot_deg[1]), "z": math.radians(rot_deg[2])},
            "rotation_euler_deg": {"x": rot_deg[0], "y": rot_deg[1], "z": rot_deg[2]},
            "rotation_quaternion": {"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0},
            "scale": {"x": scale[0], "y": scale[1], "z": scale[2]},
        },
        "rotation_mode": "XYZ",
        "raw_rotation_euler_deg": {"x": rot_deg[0], "y": rot_deg[1], "z": rot_deg[2]},
        "raw_rotation_quaternion": None,
        "raw_location": {"x": loc[0], "y": loc[1], "z": loc[2]},
        "raw_scale": {"x": scale[0], "y": scale[1], "z": scale[2]},
    }


def _bones_de_pose(json_file):
    """{bone: (rot_deg, loc, scale)} de la ultima version de una pose existente."""
    with open(os.path.join(_poses_dir(), json_file), "r", encoding="utf-8") as f:
        rec = json.load(f)["poses"][-1]
    out = {}
    for b, d in rec["bones"].items():
        ls = d.get("local_space") or {}
        r = (ls.get("rotation_euler_deg") or d.get("raw_rotation_euler_deg") or {"x": 0, "y": 0, "z": 0})
        l = (ls.get("location") or d.get("raw_location") or {"x": 0, "y": 0, "z": 0})
        s = (ls.get("scale") or d.get("raw_scale") or {"x": 1, "y": 1, "z": 1})
        out[b] = ((r["x"], r["y"], r["z"]), (l["x"], l["y"], l["z"]), (s["x"], s["y"], s["z"]))
    return out


def crear_pose(nombre, huesos, base="parado_neutral.json", root_pos=None, root_rot_deg=None,
               notas="", sobrescribir=True):
    """
    Crea una pose en la libreria (formato ALFST_OT_ExtractPose + clave "root").
    huesos: {bone: {"rot": (x,y,z) grados, "loc": (x,y,z), "scale": (x,y,z)}} -- solo lo que cambia;
            el resto se copia de `base`.
    root_pos / root_rot_deg: transformacion ABSOLUTA (mundo) del Empty 'alfred' que guardara la pose.
    Devuelve el nombre del archivo.
    """
    partida = _bones_de_pose(base) if base else {}
    bones = {}
    for b in BONES_LISTA:
        r, l, s = partida.get(b, ((0, 0, 0), (0, 0, 0), (1, 1, 1)))
        o = huesos.get(b, {})
        bones[b] = _record_hueso(o.get("rot", r), o.get("loc", l), o.get("scale", s))
    rec = {
        "label": nombre, "frame": 1, "armature": _ARM, "character": _ROOT,
        "timestamp": datetime.now().isoformat(), "blender_version": bpy.app.version_string,
        "file": os.path.basename(bpy.data.filepath) or "unsaved",
        "bone_count": len(bones), "bones": bones, "origen": "ia", "notas": notas,
        "root": {
            "location": {"x": (root_pos or (0, 0, 0))[0], "y": (root_pos or (0, 0, 0))[1], "z": (root_pos or (0, 0, 0))[2]},
            "rotation_euler_deg": {"x": (root_rot_deg or (0, 0, 0))[0], "y": (root_rot_deg or (0, 0, 0))[1], "z": (root_rot_deg or (0, 0, 0))[2]},
        },
    }
    fname = "".join(c if c not in '/\\:*?"<>|' else "_" for c in nombre).strip().replace(" ", "_") + ".json"
    ruta = os.path.join(_poses_dir(), fname)
    if os.path.isfile(ruta) and not sobrescribir:
        raise FileExistsError(ruta)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump({"poses": [rec]}, f, indent=2, ensure_ascii=False)
    return fname


def ver_pose(json_file, frame=None, con_root=True):
    """Aplica una pose de la libreria a la escena SIN keyframes (para revisarla)."""
    if frame is not None:
        _scene().frame_set(frame)
    with open(os.path.join(_poses_dir(), json_file), "r", encoding="utf-8") as f:
        rec = json.load(f)["poses"][-1]
    arm = bpy.data.objects[_ARM]
    for b, d in rec["bones"].items():
        pb = arm.pose.bones.get(b)
        if pb is None:
            continue
        ls = d.get("local_space") or {}
        r = ls.get("rotation_euler_deg") or d.get("raw_rotation_euler_deg") or {"x": 0, "y": 0, "z": 0}
        l = ls.get("location") or d.get("raw_location") or {"x": 0, "y": 0, "z": 0}
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (math.radians(r["x"]), math.radians(r["y"]), math.radians(r["z"]))
        pb.location = (l["x"], l["y"], l["z"])
    if con_root and rec.get("root"):
        root = bpy.data.objects[_ROOT]
        rl, rr = rec["root"]["location"], rec["root"]["rotation_euler_deg"]
        root.location = (rl["x"], rl["y"], rl["z"])
        root.rotation_euler = (math.radians(rr["x"]), math.radians(rr["y"]), math.radians(rr["z"]))
    bpy.context.view_layer.update()
    return {"pose": json_file, "root_loc": list(bpy.data.objects[_ROOT].location)}


def _aplicar_huesos(huesos, base="parado_neutral.json"):
    """Pone huesos en la armature (sin keyframes): base + cambios {bone: {'rot','loc'}}."""
    partida = _bones_de_pose(base) if base else {}
    arm = bpy.data.objects[_ARM]
    for b in BONES_LISTA:
        pb = arm.pose.bones.get(b)
        if pb is None:
            continue
        r, l, s = partida.get(b, ((0, 0, 0), (0, 0, 0), (1, 1, 1)))
        o = huesos.get(b, {})
        r, l = o.get("rot", r), o.get("loc", l)
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (math.radians(r[0]), math.radians(r[1]), math.radians(r[2]))
        pb.location = l
        pb.scale = o.get("scale", s)


def _mallas_alfred():
    root = bpy.data.objects[_ROOT]
    return [o for o in bpy.data.objects if o.parent == root and o.type == "MESH"]


def cuerpo_min_z(huesos, root_rot_deg=(0, 0, 180), base="parado_neutral.json"):
    """
    Z minima del cuerpo (mallas deformadas) con el root en el origen XY y z=0, para la pose
    y orientacion dadas. Sirve para apoyar el cuerpo: root_z = suelo_z - cuerpo_min_z(...).
    """
    root = bpy.data.objects[_ROOT]
    _aplicar_huesos(huesos, base)
    root.location = (0, 0, 0)
    root.rotation_euler = tuple(math.radians(v) for v in root_rot_deg)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    zs = []
    for o in _mallas_alfred():
        oe = o.evaluated_get(dg)
        zs.extend((oe.matrix_world @ __import__("mathutils").Vector(c)).z for c in oe.bound_box)
    return min(zs)


def offset_cadera(huesos, root_rot_deg=(0, 0, 180), base="parado_neutral.json"):
    """Vector (mundo) de la cadera respecto al root con la pose dada: root = cadera_objetivo - esto."""
    root = bpy.data.objects[_ROOT]
    _aplicar_huesos(huesos, base)
    root.location = (0, 0, 0)
    root.rotation_euler = tuple(math.radians(v) for v in root_rot_deg)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ae = bpy.data.objects[_ARM].evaluated_get(dg)
    return ae.matrix_world @ ae.pose.bones["Hips_alfred"].head


def root_por_suelo(huesos, rz, xy, suelo_z, base="parado_neutral.json"):
    """Posicion absoluta del root para que el punto mas bajo del cuerpo toque suelo_z."""
    return (xy[0], xy[1], round(suelo_z - cuerpo_min_z(huesos, (0, 0, rz), base), 4))


def root_por_cadera(huesos, rz, cadera, base="parado_neutral.json"):
    """Posicion absoluta del root para que la cadera quede en `cadera` (x, y, z mundo)."""
    off = offset_cadera(huesos, (0, 0, rz), base)
    return (round(cadera[0] - off.x, 4), round(cadera[1] - off.y, 4), round(cadera[2] - off.z, 4))


def pose_huesos(hips=(0, 0, 0), spine=(0, 0, 0), s1=(0, 0, 0), s2=(0, 0, 0), neck=(0, 0, 0),
                ra=(0, 0, -47), la=(0, 0, 19), rl=(0, 0, 0), ll=(0, 0, 0), rk=12, lk=0):
    """
    Constructor de huesos en terminos de movimiento (grados), listo para crear_pose().
    ra / la = (abduccion lateral, avance hacia adelante, flexion de codo)
    rl / ll = (adelante, giro, abduccion); rk / lk = flexion de rodilla (positivo = flexiona).
    hips/spine/s1/s2/neck = (X, Y, Z) locales: X inclina adelante, Y gira a la izquierda, Z inclina a la derecha.
    """
    R = lambda x=0, y=0, z=0: {"rot": (x, y, z)}
    return {
        "Hips_alfred": R(*hips), "Spine_alfred": R(*spine), "Spine1_alfred": R(*s1), "Spine2_alfred": R(*s2),
        "Neck_alfred": R(*neck),
        "RightUpArm_alfred": {"rot": (90 - ra[0], ra[1], 0)}, "Rightelbow_alfred": {"rot": (0, 0, ra[2])},
        "LeftUpArm_alfred": {"rot": (90 - la[0], -la[1], 0)}, "Leftelbow_alfred": {"rot": (0, 0, la[2])},
        "RightUpLeg_alfred": {"rot": (rl[0], rl[1], -rl[2])}, "Rightknee_alfred": {"rot": (-rk, 0, 0)},
        "LeftUpLeg_alfred": {"rot": (ll[0], ll[1], ll[2])}, "Leftknee_alfred": {"rot": (-lk, 0, 0)},
    }


def encuadrar(objetivo, dist=6.0, azim=145.0, elev=10.0, local=True):
    """Mueve la vista 3D (y la aisla en vista local con Alfred si local=True) para una captura."""
    from mathutils import Euler, Vector
    area = next(a for a in bpy.context.screen.areas if a.type == "VIEW_3D")
    region = next(r for r in area.regions if r.type == "WINDOW")
    sp = area.spaces[0]
    if local and not sp.local_view:
        root = bpy.data.objects[_ROOT]
        vl = bpy.context.view_layer
        for o in vl.objects:
            o.select_set(False)
        for o in [root, bpy.data.objects[_ARM]] + [o for o in bpy.data.objects if o.parent == root]:
            if o.name in vl.objects:
                o.select_set(True)
        with bpy.context.temp_override(area=area, region=region):
            bpy.ops.view3d.localview()
    r3d = sp.region_3d
    r3d.view_perspective = "PERSP"
    r3d.view_location = Vector(objetivo)
    r3d.view_distance = dist
    r3d.view_rotation = Euler((math.radians(90 - elev), 0, math.radians(azim)), "XYZ").to_quaternion()
    for a in bpy.context.screen.areas:
        a.tag_redraw()


# =============================================================================
# VERIFICACION NUMERICA
# =============================================================================

def medir(frames, huesos=("Hips_alfred", "Neck_alfred", "face_alfred", "LeftUpLeg_alfred", "RightUpLeg_alfred")):
    """Posicion mundial del root y de huesos clave en frames dados (no deja la escena cambiada)."""
    sc = _scene()
    f0 = sc.frame_current
    out = {}
    for f in frames:
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        root = bpy.data.objects[_ROOT].evaluated_get(dg)
        arm = bpy.data.objects[_ARM].evaluated_get(dg)
        mw = arm.matrix_world
        out[f] = {
            "root": [round(v, 2) for v in root.matrix_world.translation],
            "rot_deg": [round(math.degrees(v), 0) for v in root.rotation_euler],
            **{h: [round(v, 2) for v in (mw @ arm.pose.bones[h].head)] for h in huesos if h in arm.pose.bones},
        }
    sc.frame_set(f0)
    return out


def chequear_frames(frames, rangos=None):
    """Rotaciones fuera de rango anatomico en frames dados. Aproximacion, no reemplaza mirar."""
    rangos = rangos or RANGOS_ANATOMICOS
    sc = _scene()
    f0 = sc.frame_current
    arm = bpy.data.objects[_ARM]
    malos = []
    for f in frames:
        sc.frame_set(f)
        for b, ejes in rangos.items():
            pb = arm.pose.bones.get(b)
            if pb is None:
                continue
            rot = {"x": pb.rotation_euler.x, "y": pb.rotation_euler.y, "z": pb.rotation_euler.z}
            for e, (lo, hi) in ejes.items():
                if rot[e] < lo or rot[e] > hi:
                    malos.append({"frame": f, "hueso": b, "eje": e, "valor": round(rot[e], 2), "rango": (lo, hi)})
    sc.frame_set(f0)
    return {"ok": not malos, "fuera_de_rango": malos}
