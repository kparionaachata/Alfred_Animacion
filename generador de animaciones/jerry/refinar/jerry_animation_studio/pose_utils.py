# -*- coding: utf-8 -*-
"""
pose_utils.py — Jerry Animation Studio v1.0
Funciones de carga de poses JSON, interpolacion de bones y utilidades de carpetas.
"""
import bpy, json, os, math, subprocess, sys
from mathutils import Euler, Quaternion, Vector
from .constants import BONES_LISTA, BONES_LISTA_FULL, _BONE_DEFAULT
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

def get_root_rotation_from_record(record):
    """
    Extrae la rotacion XYZ (en grados) del bone raiz 'Dog_001_rig'
    desde un pose record. Devuelve (rx, ry, rz) en grados, o (0, 0, 0) si
    no se puede leer.
    Usado para auto-rellenar Rot X/Y/Z al elegir una pose en los dialogos.
    """
    if not record:
        return (0.0, 0.0, 0.0)
    bones = record.get("bones", {})
    root  = bones.get("Dog_001_rig", {})
    # Intentar raw_rotation_euler_deg primero (siempre presente)
    raw_e = root.get("raw_rotation_euler_deg")
    if raw_e and raw_e.get("y") is not None:
        return (raw_e.get("x", 0.0), raw_e.get("y", 0.0), raw_e.get("z", 0.0))
    # Fallback: local_space
    local_sp = root.get("local_space", {})
    re = local_sp.get("rotation_euler_deg", {})
    if re and re.get("y") is not None:
        return (re.get("x", 0.0), re.get("y", 0.0), re.get("z", 0.0))
    return (0.0, 0.0, 0.0)

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
    for bone_name in BONES_LISTA_FULL:
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
        for bone in BONES_LISTA_FULL:
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
    action_poses (JerryPoseSlotItem o JerrySegmentPoseSlot, ambos con
    .duration / .manual_start / .frame_abs_start).

    PORTADO desde alfred_animation_studio (Kebyn, 2026-08-06): mismo sistema
    de "Elegir frame de inicio" del Paso 3, ver ALFREDSEG_OT_EditActionPoseSeg
    en alfred_animation_studio/operators_segments.py.

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

# ── Cache global para _enum_json_files ──────────────────────────────────────
# Blender cachea los EnumProperty de operadores y no los re-evalua aunque la
# carpeta haya cambiado en disco. Solución: cache propio invalidado por mtime
# de la carpeta o por llamada explícita a invalidate_enum_cache().
_enum_json_cache = {
    "items":  [],   # lista de tuplas (identifier, label, description)
    "folder": "",   # carpeta escaneada
    "mtime":  0.0,  # os.stat(folder).st_mtime al momento del escaneo
}

def invalidate_enum_cache():
    """Fuerza re-escaneo en la siguiente llamada a _enum_json_files.
    Llamar desde JRRST_OT_RefreshPoses y JRRST_OT_ExtractPose."""
    _enum_json_cache["mtime"]  = 0.0
    _enum_json_cache["folder"] = ""
    _enum_json_cache["items"]  = []


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

    Usa cache propio invalidado por mtime de carpeta para que archivos recién
    guardados (ej: captura de pose) aparezcan sin necesidad de reabrir Blender.
    """
    st     = context.scene.jerryst
    folder = bpy.path.abspath(st.poses_dir)

    # Obtener mtime actual de la carpeta (0 si no existe)
    try:
        current_mtime = os.stat(folder).st_mtime if os.path.isdir(folder) else 0.0
    except OSError:
        current_mtime = 0.0

    cache = _enum_json_cache
    # Reescanear si cambió la carpeta, el mtime, o el cache fue invalidado
    if cache["folder"] != folder or cache["mtime"] != current_mtime or not cache["items"]:
        files = list_json_files(st.poses_dir)
        cache["items"]  = ([(str(i), f, f) for i, f in enumerate(files)]
                           if files else [("NONE", "-- sin archivos JSON --", "")])
        cache["folder"] = folder
        cache["mtime"]  = current_mtime

    return cache["items"]

def _json_file_from_index(self, context):
    """Convierte el identifier numerico del EnumProperty al nombre real del archivo."""
    st = context.scene.jerryst
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
    st  = context.scene.jerryst
    jf  = _json_file_from_index(self, context)
    if not jf:
        return [("0", "-- elige JSON primero --", "")]
    fp    = os.path.join(bpy.path.abspath(st.poses_dir), jf)
    poses = load_json_poses(fp)
    if not poses:
        return [("0", "-- JSON vacio --", "")]
    return [(str(i), p.get("label", f"pose_{i}"), "") for i, p in enumerate(poses)]

# =============================================================================
# EDITOR DE POSE EN VIVO — "Editar pose..." / "Guardar cambios"
# =============================================================================
# Sistema que reemplaza los antiguos dialogos con campos numericos manuales
# (rot_x/rot_y/rot_z/pos_x/pos_y/pos_z escritos a mano) por edicion en vivo:
#   1. "Editar pose..." entra a Pose Mode sobre el armature, para ajustar los
#      huesos con las herramientas nativas de Blender (panel N).
#   2. Para el Root, el usuario selecciona el Empty ('jerry') y lo ajusta con
#      el panel nativo Properties > Object > Transform (NO un campo custom).
#   3. "Guardar cambios" lee el estado ACTUAL de la escena (huesos en pose +
#      transform del Empty) y lo exporta a un .json dentro de la carpeta de
#      cambios, sin tocar el JSON original de la libreria de poses.

import random
import string
import time


def get_root_transform_from_record(record, root_name="jerry", arm_name="Dog_001_rig"):
    """
    Devuelve el transform del Root de una pose ya guardada, para mostrarlo
    como solo-lectura en el panel. Busca primero la entrada keyed por
    root_name (el Empty, formato nuevo del editor en vivo) y, si no esta,
    cae a arm_name (formato viejo/otros exportadores) — carga INCONDICIONAL,
    sin asumir que un formato esta siempre presente.

    Devuelve {"pos": (x,y,z), "rot_deg": (rx,ry,rz)}; (0,0,0)/(0,0,0) si no
    hay datos.
    """
    zero = {"pos": (0.0, 0.0, 0.0), "rot_deg": (0.0, 0.0, 0.0)}
    if not record:
        return zero
    bones_data = record.get("bones", {})
    entry = bones_data.get(root_name) or bones_data.get(arm_name)
    if not entry:
        return zero

    local_sp = entry.get("local_space") or {}

    loc = local_sp.get("location") or entry.get("raw_location") or {}
    pos = (loc.get("x", 0.0), loc.get("y", 0.0), loc.get("z", 0.0))

    rot_deg = (local_sp.get("rotation_euler_deg")
               or entry.get("raw_rotation_euler_deg") or {})
    rot = (rot_deg.get("x", 0.0), rot_deg.get("y", 0.0), rot_deg.get("z", 0.0))

    return {"pos": pos, "rot_deg": rot}


def capture_live_bone_pose(armature, bone_names=None):
    """
    Lee la pose ACTUAL (en vivo, desde Pose Mode) de cada hueso de
    'bone_names' (por defecto BONES_LISTA_FULL) que exista en el armature.
    Devuelve {bone_name: {"loc":(x,y,z), "rot_deg":(rx,ry,rz), "scale":(x,y,z)}}
    Los huesos que no existen en este rig se omiten (no se inventan datos).
    """
    if bone_names is None:
        bone_names = BONES_LISTA_FULL
    out = {}
    for bname in bone_names:
        pb = armature.pose.bones.get(bname)
        if pb is None:
            continue
        if pb.rotation_mode == 'QUATERNION':
            e = pb.rotation_quaternion.to_euler('XYZ')
        elif pb.rotation_mode == 'AXIS_ANGLE':
            e = pb.matrix_basis.to_euler('XYZ')
        else:
            e = pb.rotation_euler
        out[bname] = {
            "loc": (pb.location.x, pb.location.y, pb.location.z),
            "rot_deg": (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z)),
            "scale": (pb.scale.x, pb.scale.y, pb.scale.z),
        }
    return out


def capture_live_root_transform(root_obj):
    """
    Lee el transform ACTUAL del objeto Root (Empty), tal cual esta en
    Properties > Object > Transform en este momento de la escena.
    Devuelve {"pos": (x,y,z), "rot_deg": (rx,ry,rz)}.
    """
    loc = root_obj.location
    rot = root_obj.rotation_euler
    return {
        "pos": (loc.x, loc.y, loc.z),
        "rot_deg": (math.degrees(rot.x), math.degrees(rot.y), math.degrees(rot.z)),
    }


def _bone_capture_to_record_entry(data):
    """Convierte la salida de capture_live_* al formato de 'bones' del JSON."""
    rx, ry, rz = data["rot_deg"]
    x, y, z = data["pos"] if "pos" in data else data["loc"]
    entry = {
        "rotation_mode": "XYZ",
        "raw_rotation_euler_deg": {"x": rx, "y": ry, "z": rz},
        "raw_location": {"x": x, "y": y, "z": z},
        "raw_scale": {"x": 1.0, "y": 1.0, "z": 1.0},
        "local_space": {
            "rotation_euler_deg": {"x": rx, "y": ry, "z": rz},
            "location": {"x": x, "y": y, "z": z},
            "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
        },
    }
    if "scale" in data:
        sx, sy, sz = data["scale"]
        entry["raw_scale"] = {"x": sx, "y": sy, "z": sz}
        entry["local_space"]["scale"] = {"x": sx, "y": sy, "z": sz}
    return entry


def build_pose_record(pose_name, bone_data, root_transform, root_name="jerry"):
    """
    Arma un pose record completo (mismo formato que lee pose_record_to_full_dict
    / get_root_transform_from_record) a partir de lo capturado en vivo:
    bone_data de capture_live_bone_pose() + root_transform de
    capture_live_root_transform().
    """
    bones = {}
    for bname, data in bone_data.items():
        bones[bname] = _bone_capture_to_record_entry(data)
    bones[root_name] = _bone_capture_to_record_entry(root_transform)
    return {"label": pose_name, "bones": bones}


def export_pose_changes(pose_changes_dir, pose_name, bone_data, root_transform,
                        base_filename=None, root_name="jerry"):
    """
    Exporta un .json con la pose actual (huesos + Root) a la carpeta de
    cambios (DEFAULT_POSE_CHANGES_DIR por defecto, configurable en el panel).
    NO modifica el JSON original de la libreria de poses — genera un archivo
    nuevo, pensado para revisar/fusionar despues.

    Devuelve la ruta completa del archivo escrito.
    """
    folder = bpy.path.abspath(pose_changes_dir)
    os.makedirs(folder, exist_ok=True)

    record = build_pose_record(pose_name, bone_data, root_transform, root_name)

    safe_name = "".join(c if (c.isalnum() or c in "_-") else "_"
                        for c in (pose_name or "pose"))[:40] or "pose"
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    filename = base_filename or f"auto_jerry_{safe_name}_{suffix}.json"
    if not filename.lower().endswith(".json"):
        filename += ".json"

    filepath = os.path.join(folder, filename)

    # Si el archivo ya existe (mismo base_filename, guardados sucesivos sobre
    # el mismo slot), se agrega/actualiza el record dentro de 'poses' en vez
    # de pisar todo el archivo, para no perder guardados previos del mismo slot.
    poses = load_json_poses(filepath) if os.path.isfile(filepath) else []
    poses.append(record)
    payload = {"poses": poses, "ultimo_guardado": time.strftime("%Y-%m-%d %H:%M:%S")}

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return filepath


# =============================================================================
# LECTURA DE jerry_pose_library.json — nombre_legible ('_semantica')
# =============================================================================
# Puerto directo de la funcionalidad equivalente en Alfred Animation Studio
# (alfred_studio_v2/pose_utils.py: reglas_dir_path / pose_library_path /
# leer_nombre_legible). No existia en Jerry Animation Studio: por eso el
# panel de slots mostraba el bloque "Root (jerry) de esta pose" pero nunca
# la descripcion semantica de la pose seleccionada.

def _leer_json(fp):
    try:
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def reglas_dir_path(context):
    """Carpeta 'reglas' configurable desde la escena; si no existe el campo,
    usa la ruta por defecto definida en constants.py."""
    from .constants import DEFAULT_REGLAS_DIR
    st = getattr(context.scene, "jerryst", None)
    val = getattr(st, "reglas_dir", "") if st else ""
    return bpy.path.abspath(val) if val else DEFAULT_REGLAS_DIR


def pose_library_path(context):
    folder = reglas_dir_path(context)
    return os.path.join(folder, "jerry_pose_library.json")


def leer_nombre_legible(context, json_file):
    """
    Lee el campo _semantica.nombre_legible de jerry_pose_library.json para
    la pose indicada por json_file (ej: "auto_jerry_config_xxx_123.json").

    Retorna el nombre legible como string, o None si no existe.
    Este nombre se usa para mostrar en la UI que movimiento representa la
    pose seleccionada (equivalente exacto al bloque de Alfred).
    """
    lib_fp = pose_library_path(context)
    lib_doc = _leer_json(lib_fp)
    if lib_doc is None:
        return None
    poses_data = lib_doc.get("poses_data", {})
    pose_data  = poses_data.get(json_file, {})
    semantica  = pose_data.get("_semantica", {})
    return semantica.get("nombre_legible", None)
