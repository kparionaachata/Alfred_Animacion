# -*- coding: utf-8 -*-
"""
pose_utils.py — Chicken 1 Animation Studio v1.8
Funciones de carga de poses JSON, interpolacion de bones y utilidades de carpetas.
"""
import bpy, json, os, math, subprocess, sys
from mathutils import Euler, Quaternion, Vector
from .constants import BONES_LISTA, _BONE_DEFAULT
from .interpolation import apply_interp

# =============================================================================
# UTILIDADES
# =============================================================================

def list_json_files(poses_dir):
    folder = bpy.path.abspath(poses_dir)
    if not folder or not os.path.isdir(folder):
        return []
    return sorted(f for f in os.listdir(folder) if f.endswith(".json"))

def load_json_poses(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f).get("poses", [])
    except Exception:
        return []

def get_pose_record(poses_dir, json_file, pose_idx):
    fp = os.path.join(bpy.path.abspath(poses_dir), json_file)
    poses = load_json_poses(fp)
    if 0 <= pose_idx < len(poses):
        return poses[pose_idx]
    return None

def get_orientacion_inicial(historia_data):
    """Devuelve (rx, ry, rz) en radianes desde orientacion_inicial del JSON."""
    ori = historia_data.get("configuracion", {}).get("orientacion_inicial", {})
    return (
        math.radians(ori.get("rotacion_x", 0.0)),
        math.radians(ori.get("rotacion_y", 0.0)),
        math.radians(ori.get("rotacion_z", 0.0)),
    )

def pose_record_to_full_dict(record):
    """
    Lee datos de huesos del registro JSON y devuelve:
        {bone_name: {"rot": (rx,ry,rz), "loc": (lx,ly,lz), "scale": (sx,sy,sz)}}

    Compatible con DOS formatos de exportacion:

    FORMATO A — exportador antiguo / señalar.json (campos en raiz del hueso):
        {
          "rotation_mode": "XYZ",
          "raw_rotation_euler_deg": {"x":0, "y":0, "z":0},   <- puede ser null si modo QUATERNION
          "raw_rotation_quaternion": {"w":1,"x":0,"y":0,"z":0},
          "raw_location": {"x":0,"y":0,"z":0},
          "raw_scale":    {"x":1,"y":1,"z":1}
        }

    FORMATO B — exportador nuevo / arrodillarse.json (con local_space):
        {
          "local_space": {
            "rotation_euler_deg": {"x":0,"y":0,"z":0},
            "rotation_quaternion": {"w":1,"x":0,"y":0,"z":0},
            "location": {"x":0,"y":0,"z":0},
            "scale":    {"x":1,"y":1,"z":1}
          },
          "rotation_mode": "XYZ",
          "raw_rotation_euler_deg": {"x":0,"y":0,"z":0},   <- tambien presente como fallback
          "raw_location": {"x":0,"y":0,"z":0},
          "raw_scale":    {"x":1,"y":1,"z":1}
        }
    """
    out = {}
    bones_data = record.get("bones", {})
    for bone_name in BONES_LISTA:
        bdata = bones_data.get(bone_name)
        if bdata is None:
            out[bone_name] = dict(_BONE_DEFAULT)
            continue

        rot_mode   = bdata.get("rotation_mode", "XYZ")
        local_sp   = bdata.get("local_space")   # presente solo en Formato B

        # ── ROTACION ──
        # Prioridad: local_space > raw_rotation_* en raiz
        rot = None
        if rot_mode == "QUATERNION":
            # Intentar quaternion desde local_space (Formato B)
            if local_sp:
                rq = local_sp.get("rotation_quaternion") or {}
                if rq and rq.get("w") is not None:
                    q = Quaternion((rq.get("w",1.0), rq.get("x",0.0),
                                    rq.get("y",0.0), rq.get("z",0.0)))
                    e = q.to_euler("XYZ")
                    rot = (e.x, e.y, e.z)
            # Fallback: raw_rotation_quaternion en raiz (ambos formatos)
            if rot is None:
                raw_q = bdata.get("raw_rotation_quaternion") or {}
                if raw_q and raw_q.get("w") is not None:
                    q = Quaternion((raw_q.get("w",1.0), raw_q.get("x",0.0),
                                    raw_q.get("y",0.0), raw_q.get("z",0.0)))
                    e = q.to_euler("XYZ")
                    rot = (e.x, e.y, e.z)
        else:
            # Euler XYZ — intentar local_space primero (Formato B)
            if local_sp:
                re = local_sp.get("rotation_euler_deg") or {}
                if re and re.get("x") is not None:
                    rot = (math.radians(re.get("x",0.0)),
                           math.radians(re.get("y",0.0)),
                           math.radians(re.get("z",0.0)))
            # Fallback: raw_rotation_euler_deg en raiz (ambos formatos)
            if rot is None:
                raw_e = bdata.get("raw_rotation_euler_deg") or {}
                rot = (math.radians(raw_e.get("x",0.0)),
                       math.radians(raw_e.get("y",0.0)),
                       math.radians(raw_e.get("z",0.0)))

        if rot is None:
            rot = (0.0, 0.0, 0.0)

        # ── UBICACION ──
        loc = None
        if local_sp:
            lc = local_sp.get("location") or {}
            if lc and lc.get("x") is not None:
                loc = (lc.get("x",0.0), lc.get("y",0.0), lc.get("z",0.0))
        if loc is None:
            raw_loc = bdata.get("raw_location") or {}
            loc = (raw_loc.get("x",0.0), raw_loc.get("y",0.0), raw_loc.get("z",0.0))

        # ── ESCALA ──
        scale = None
        if local_sp:
            sc = local_sp.get("scale") or {}
            if sc and sc.get("x") is not None:
                scale = (sc.get("x",1.0), sc.get("y",1.0), sc.get("z",1.0))
        if scale is None:
            raw_sc = bdata.get("raw_scale") or {}
            scale = (raw_sc.get("x",1.0), raw_sc.get("y",1.0), raw_sc.get("z",1.0))

        out[bone_name] = {"rot": rot, "loc": loc, "scale": scale}
    return out

def _lerp(a, b, t):
    return (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t, a[2]+(b[2]-a[2])*t)

def _smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

def _interpolate_bone_segment(frame, total_frames, s, a, e, er, xr, interp_type="SMOOTH"):
    """Interpola un componente de 3 floats para un bone en un segmento."""
    if total_frames <= 1:
        return a
    if frame <= 1:
        return s
    if frame >= total_frames:
        return e
    entry_end  = max(2, int(total_frames * er))
    exit_start = min(total_frames - 1, int(total_frames * (1.0 - xr)))
    if frame <= entry_end:
        t = apply_interp((frame - 1) / max(entry_end - 1, 1), interp_type)
        return _lerp(s, a, t)
    elif frame >= exit_start:
        t = apply_interp((frame - exit_start) / max(total_frames - exit_start, 1), interp_type)
        return _lerp(a, e, t)
    return a

def build_segment_frames(d_s, d_a, d_e, n_frames, er, xr, interp_type="SMOOTH"):
    """Construye lista de frames para un segmento interpolando rot/loc/scale."""
    frames = []
    for local_f in range(1, n_frames + 1):
        fd = {}
        for bone in BONES_LISTA:
            s = d_s.get(bone, _BONE_DEFAULT)
            a = d_a.get(bone, s)
            e = d_e.get(bone, s)
            fd[bone] = {
                "rot":   _interpolate_bone_segment(local_f, n_frames, s["rot"],   a["rot"],   e["rot"],   er, xr, interp_type),
                "loc":   _interpolate_bone_segment(local_f, n_frames, s["loc"],   a["loc"],   e["loc"],   er, xr, interp_type),
                "scale": _interpolate_bone_segment(local_f, n_frames, s["scale"], a["scale"], e["scale"], er, xr, interp_type),
            }
        frames.append(fd)
    return frames

def resolve_pose_start_frames(action_items, start_frame):
    """
    Resuelve el frame absoluto de inicio de cada pose de una lista de
    action_poses (Chicken1PoseSlotItem o Chicken1SegmentPoseSlot, ambos con
    .duration / .manual_start / .frame_abs_start).

    Comportamiento por pose:
      - manual_start == False (default): se apila automaticamente justo
        despues del final de la pose anterior (comportamiento de siempre).
      - manual_start == True: se usa item.frame_abs_start tal cual, SIEMPRE
        que no invada a la pose anterior (frame_abs_start >= cursor actual).
        Si invade, se ignora el valor manual y se cae al apilado automatico
        (evita que dos poses se superpongan). Un frame manual mayor al
        automatico simplemente deja un hueco -- ese hueco se interpola
        suavemente entre el fin de la pose anterior y el inicio de esta,
        no requiere ningun tratamiento especial en el resto del pipeline.

    Devuelve: lista de ints, un frame_abs_start resuelto por cada item de
    `action_items`, en el mismo orden. No modifica los items.
    """
    resolved = []
    cursor = start_frame
    for item in action_items:
        manual = getattr(item, "manual_start", False)
        manual_val = getattr(item, "frame_abs_start", 0)
        if manual and manual_val >= cursor:
            fs = manual_val
        else:
            fs = cursor
        resolved.append(fs)
        cursor = fs + max(1, int(item.duration))
    return resolved


def open_folder(path):
    import subprocess, sys
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print(f"No se pudo abrir carpeta: {e}")

# =============================================================================
# ENUM CALLBACKS
# =============================================================================

def _enum_json_files(self, context):
    """
    Genera items para EnumProperty de archivos JSON.

    IMPORTANTE: Blender exige que el identifier (primer elemento de la tupla)
    sea ASCII puro. Si se usa el nombre del archivo directamente como identifier,
    archivos con caracteres no-ASCII (ñ, tildes, etc.) son ignorados o corrompen
    el widget. Solucion: usar indice numerico como identifier, nombre como label.

    Formato: (identifier, label, description)
      identifier = str(indice)  <- siempre ASCII, nunca falla
      label      = nombre_archivo.json  <- se muestra en el desplegable
    """
    st = context.scene.ch1st
    files = list_json_files(st.poses_dir)
    if not files:
        return [("NONE", "-- sin archivos JSON --", "")]
    return [(str(i), f, f) for i, f in enumerate(files)]

def _json_file_from_index(self, context):
    """Convierte el identifier numerico del EnumProperty al nombre real del archivo."""
    st = context.scene.ch1st
    idx_str = getattr(self, "json_file", "NONE")
    if idx_str == "NONE":
        return ""
    try:
        idx   = int(idx_str)
        files = list_json_files(st.poses_dir)
        return files[idx] if 0 <= idx < len(files) else ""
    except (ValueError, TypeError):
        # Compatibilidad: si ya es un nombre de archivo (valores guardados antiguos)
        return idx_str

def _enum_poses_from_self_json(self, context):
    st  = context.scene.ch1st
    jf  = _json_file_from_index(self, context)
    if not jf:
        return [("0", "-- elige JSON primero --", "")]
    fp    = os.path.join(bpy.path.abspath(st.poses_dir), jf)
    poses = load_json_poses(fp)
    if not poses:
        return [("0", "-- JSON vacio --", "")]
    return [(str(i), p.get("label", f"pose_{i}"), "") for i, p in enumerate(poses)]

# =============================================================================


def get_root_rotation_from_record(record):
    """
    Extrae la rotacion XYZ (en grados) del bone raiz 'Armature' o 'Root_M_chicken_1'
    desde un pose record. Devuelve (rx, ry, rz) en grados, o (0, 0, 0) si no se puede leer.
    """
    if not record:
        return (0.0, 0.0, 0.0)
    bones = record.get("bones", {})
    # Intentar con el root de Alfred (Hips_alfred o Armature)
    for root_key in ("Hips_alfred", "Armature", "Dog_001_rig"):
        root = bones.get(root_key, {})
        if root:
            raw_e = root.get("raw_rotation_euler_deg")
            if raw_e and raw_e.get("y") is not None:
                return (raw_e.get("x", 0.0), raw_e.get("y", 0.0), raw_e.get("z", 0.0))
            local_sp = root.get("local_space", {})
            re = local_sp.get("rotation_euler_deg", {})
            if re and re.get("y") is not None:
                return (re.get("x", 0.0), re.get("y", 0.0), re.get("z", 0.0))
    return (0.0, 0.0, 0.0)


def get_root_transform_from_record(record):
    """
    Extrae la Posicion (pos_x, pos_y, pos_z) y Rotacion (rot_x, rot_y, rot_z, en
    grados) del Root (Empty 'chicken_1') guardadas dentro del pose record, bajo la
    clave "root" escrita por CH1SEG_OT_SaveEditedPose.

    Devuelve (pos_x, pos_y, pos_z, rot_x, rot_y, rot_z). Si el record no tiene
    "root" (pose vieja, nunca editada con el flujo de Empty), cae de vuelta a
    posicion (0,0,0) y a get_root_rotation_from_record() para la rotacion, para
    mantener compatibilidad con poses ya existentes.
    """
    if not record:
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    root = record.get("root")
    if root:
        loc = root.get("location", {}) or {}
        rot = root.get("rotation_euler_deg", {}) or {}
        if loc or rot:
            return (
                loc.get("x", 0.0), loc.get("y", 0.0), loc.get("z", 0.0),
                rot.get("x", 0.0), rot.get("y", 0.0), rot.get("z", 0.0),
            )
    rx, ry, rz = get_root_rotation_from_record(record)
    return (0.0, 0.0, 0.0, rx, ry, rz)


_enum_json_cache = {"folder": "", "mtime": 0.0, "items": []}


def _enum_json_files(self, context):
    """Genera items para EnumProperty de archivos JSON de poses."""
    import os as _os
    st     = getattr(context.scene, "ch1st", None)
    folder = bpy.path.abspath(st.poses_dir) if st else ""

    try:
        current_mtime = _os.stat(folder).st_mtime if _os.path.isdir(folder) else 0.0
    except OSError:
        current_mtime = 0.0

    cache = _enum_json_cache
    if cache["folder"] != folder or cache["mtime"] != current_mtime or not cache["items"]:
        files = list_json_files(folder) if folder else []
        cache["items"]  = ([(str(i), f, f) for i, f in enumerate(files)]
                           if files else [("NONE", "-- sin archivos JSON --", "")])
        cache["folder"] = folder
        cache["mtime"]  = current_mtime

    return cache["items"]


def _json_file_from_index(self, context):
    """Convierte el identifier numerico del EnumProperty al nombre real del archivo."""
    st = getattr(context.scene, "ch1st", None)
    idx_str = getattr(self, "json_file", "NONE")
    if idx_str == "NONE":
        return ""
    try:
        idx   = int(idx_str)
        poses_dir = st.poses_dir if st else ""
        files = list_json_files(poses_dir) if poses_dir else []
        return files[idx] if 0 <= idx < len(files) else ""
    except (ValueError, TypeError):
        return idx_str


def _enum_poses_from_self_json(self, context):
    st  = getattr(context.scene, "ch1st", None)
    jf  = _json_file_from_index(self, context)
    if not jf:
        return [("0", "-- elige JSON primero --", "")]
    poses_dir = st.poses_dir if st else ""
    fp    = os.path.join(bpy.path.abspath(poses_dir), jf) if poses_dir else ""
    poses = load_json_poses(fp) if fp else []
    if not poses:
        return [("0", "-- JSON vacio --", "")]
    return [(str(i), p.get("label", f"pose_{i}"), "") for i, p in enumerate(poses)]
