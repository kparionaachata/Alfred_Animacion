# -*- coding: utf-8 -*-
"""
pose_utils.py — Alfred Animation Studio v1.8
Funciones de carga de poses JSON, interpolacion de bones y utilidades de carpetas.
"""
import bpy, json, os, math, subprocess, sys, datetime
from mathutils import Euler, Quaternion, Vector
from .constants import (
    BONES_LISTA, _BONE_DEFAULT, DEFAULT_REGLAS_DIR, DEFAULT_POSE_LIBRARY_PATH,
    calcular_estado_calificacion,
)
from .interpolation import apply_interp

# Cache de lecturas de JSON por ruta -> (mtime, data_parseada). Usado por
# _leer_json() para evitar releer/parsear archivos grandes (pose_library.json,
# poses individuales) en cada redraw del panel de Blender. Ver _leer_json().
_JSON_READ_CACHE = {}

# FIX (Kebyn, 2026-08-26: "el personaje con sus poses se desplaza a 0,0,0
# sin respetar la coordenada asignada"). Ver get_root_transform_from_record()
# mas abajo. Este set evita repetir el mismo aviso de consola por cada
# frame horneado de una misma pose (se avisa 1 sola vez por pose+sesion).
_WARNED_MISSING_ROOT_POSES = set()

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
    action_poses (AlfredPoseSlotItem o AlfredSegmentPoseSlot, ambos con
    .duration / .manual_start / .frame_abs_start).

    Generica: tambien se reutiliza tal cual (Kebyn, 2026-09-06) para
    encadenar AlfredEyeExprInterval (sistema de expresiones de ojos), que
    tiene el mismo trio de atributos .duration/.manual_start/
    .frame_abs_start -- ver operators_anim.py y operators_segments.py,
    seccion "Expresiones de ojos por intervalos".

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
    st = context.scene.alfst
    files = list_json_files(st.poses_dir)
    if not files:
        return [("NONE", "-- sin archivos JSON --", "")]
    return [(str(i), f, f) for i, f in enumerate(files)]

def _json_file_from_index(self, context):
    """Convierte el identifier numerico del EnumProperty al nombre real del archivo."""
    st = context.scene.alfst
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
    st  = context.scene.alfst
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
    Extrae la rotacion XYZ (en grados) del bone raiz 'Armature' o 'Hips_alfred'
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
    grados) del Root (Empty 'alfred') guardadas dentro del pose record, bajo la
    clave "root" escrita por ALFREDSEG_OT_SaveEditedPose.

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
    # BUGFIX (Kebyn, 2026-08-26, bis: "el root aparece con rotaciones,
    # cuando nunca se debe rotar el root"). ANTES: si la pose no tenia
    # "root", esta funcion llamaba a get_root_rotation_from_record(record),
    # que lee la rotacion CRUDA del bone Hips_alfred (la cadera, ya rotada
    # como parte normal de la pose) y la aplicaba, ademas, como rotacion
    # propia del Empty raiz "alfred". Eso duplicaba la rotacion (la cadera
    # ya gira como bone dentro del armature) y dejaba al root con angulos
    # sin sentido (ej. X=175°, Y=-100°, Z=-175° vistos en Transform), pese
    # a que el Empty raiz NUNCA deberia rotar por si solo salvo que se haya
    # guardado explicitamente asi via "Guardar cambios en la pose".
    #
    # AHORA: si no hay "root" guardado, la rotacion del Empty se mantiene
    # SIEMPRE en (0.0, 0.0, 0.0) -- get_root_rotation_from_record() ya no
    # se usa como fuente de la rotacion del root. La orientacion/"hacia
    # donde mira" de la pose la sigue aportando el propio bone Hips_alfred
    # (u otros bones), que se hornea normalmente en su propio fcurve; el
    # root solo debe rotar cuando el usuario lo haya posicionado y guardado
    # a proposito (ej. para seguir la tangente de un recorrido curvo).
    rx, ry, rz = (0.0, 0.0, 0.0)

    # BUGFIX (Kebyn, 2026-08-26: "el personaje con sus poses se desplaza a
    # 0,0,0 sin respetar la coordenada asignada"). ANTES: si la pose no
    # tenia la clave "root" (nunca se guardo con "Guardar cambios en la
    # pose" -- tipico en poses viejas de la libreria general, usadas tal
    # cual en segmentos de 1 coordenada), esta funcion devolvia posicion
    # (0.0, 0.0, 0.0) EN SILENCIO. Eso pisaba, al concatenar, cualquier
    # coordenada donde el usuario hubiera colocado realmente al personaje
    # -- el sintoma tipico era "el personaje se teletransporta al origen
    # sin ninguna advertencia".
    #
    # AHORA: en vez de forzar el origen, se usa como fallback la posicion
    # ACTUAL del Empty "alfred" en la escena (la misma que el usuario ya
    # dejo ubicada a mano antes de concatenar) -- esto es lo mas parecido
    # a "respetar la coordenada asignada" sin tener el dato guardado en el
    # .json. Ademas se avisa por consola (una sola vez por pose+sesion)
    # para que el problema de fondo (falta guardar la pose con el Root ya
    # bien ubicado) no vuelva a pasar desapercibido. Si no existe el Empty
    # "alfred" en la escena, se mantiene (0,0,0) como ultimo recurso.
    root_empty = bpy.data.objects.get("alfred")
    if root_empty is not None:
        _fallback_pos = (
            root_empty.location.x, root_empty.location.y, root_empty.location.z,
        )
    else:
        _fallback_pos = (0.0, 0.0, 0.0)

    _pose_key = (
        record.get("label")
        or record.get("edited_timestamp")
        or record.get("timestamp")
        or id(record)
    )
    if _pose_key not in _WARNED_MISSING_ROOT_POSES:
        _WARNED_MISSING_ROOT_POSES.add(_pose_key)
        print(
            "[Alfred Animation Studio] AVISO: la pose "
            f"'{record.get('label', '?')}' no tiene guardada su posicion/"
            "rotacion de Root (nunca se uso 'Guardar cambios en la pose'). "
            f"Se usa como fallback: posicion actual del Empty 'alfred' "
            f"{_fallback_pos} y rotacion (0,0,0) -- el root ya NO hereda la "
            "rotacion del bone Hips_alfred. Para fijar esto de forma "
            "permanente: selecciona esta pose en el segmento, ubica/rota el "
            "Empty 'alfred' como corresponda y presiona 'Guardar cambios "
            "en la pose'."
        )

    return (_fallback_pos[0], _fallback_pos[1], _fallback_pos[2], rx, ry, rz)


_enum_json_cache = {"folder": "", "mtime": 0.0, "items": []}


def _enum_json_files(self, context):
    """Genera items para EnumProperty de archivos JSON de poses."""
    import os as _os
    st     = getattr(context.scene, "alfst", None)
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
    st = getattr(context.scene, "alfst", None)
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
    st  = getattr(context.scene, "alfst", None)
    jf  = _json_file_from_index(self, context)
    if not jf:
        return [("0", "-- elige JSON primero --", "")]
    poses_dir = st.poses_dir if st else ""
    fp    = os.path.join(bpy.path.abspath(poses_dir), jf) if poses_dir else ""
    poses = load_json_poses(fp) if fp else []
    if not poses:
        return [("0", "-- JSON vacio --", "")]
    return [(str(i), p.get("label", f"pose_{i}"), "") for i, p in enumerate(poses)]

# =============================================================================
# CALIFICACION DE POSES (1-10)
# =============================================================================
# Cada vez que el usuario califica una pose desde la interfaz, se guarda:
#   1) En el propio archivo .json de la pose, dentro de poses[pose_idx]:
#        user_score_history: [{query, score, comment, timestamp}, ...]
#        user_score_avg, user_score_count, user_score_status
#   2) En pose_library.json (carpeta "reglas"), bajo la clave "calificaciones",
#      un resumen liviano por archivo para que el resto del pipeline
#      (alfred_story_generator.py, alfred_filter.py, alfred_evolution_engine.py)
#      pueda consultar la calidad de una pose sin abrir cada JSON individual.

def _leer_json(fp):
    """Lee un JSON con cache por mtime del archivo.

    SIN esto, leer_nombre_legible() (llamada desde panels.py en cada
    redraw, una vez por cada segmento con la configuracion expandida)
    releia y re-parseaba pose_library.json completo desde disco decenas
    de veces por segundo — ese archivo crece con cada generacion
    evolutiva y termina pesando varios MB, lo que causaba el lag severo
    al navegar entre segmentos. Con el cache, si el archivo no cambio en
    disco (mismo mtime) se devuelve el dict ya parseado, sin tocar disco.
    El cache se invalida solo cuando el archivo se vuelve a escribir
    (ej: guardar_calificacion_pose), porque cambia su mtime.
    """
    try:
        mtime = os.path.getmtime(fp)
    except Exception:
        return None
    cached = _JSON_READ_CACHE.get(fp)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    _JSON_READ_CACHE[fp] = (mtime, data)
    return data

def _escribir_json(fp, data):
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    # Invalida el cache de lectura: el archivo recien escrito tiene un
    # mtime nuevo, pero por si el filesystem tiene resolucion de tiempo
    # baja (algunos SO redondean a 1-2s) forzamos la invalidacion aqui
    # tambien para no arriesgar servir una version vieja desde el cache.
    _JSON_READ_CACHE.pop(fp, None)

def reglas_dir_path(context):
    """Carpeta 'reglas' configurable desde la escena; si no existe el campo,
    usa la ruta por defecto definida en constants.py."""
    st = getattr(context.scene, "alfst", None)
    val = getattr(st, "reglas_dir", "") if st else ""
    return bpy.path.abspath(val) if val else DEFAULT_REGLAS_DIR

def pose_library_path(context):
    folder = reglas_dir_path(context)
    return os.path.join(folder, "pose_library.json")



def leer_nombre_legible(context, json_file):
    """
    Lee el campo _semantica.nombre_legible de pose_library.json para la pose
    indicada por json_file (ej: "auto_alfred_config_xxx_123.json").

    Retorna el nombre legible como string, o None si no existe.
    Este nombre se usa para:
      - Mostrar en la UI qué pose se está reproduciendo
      - Auto-rellenar el campo 'Que se pidio' antes de calificar
    """
    lib_fp = pose_library_path(context)
    lib_doc = _leer_json(lib_fp)
    if lib_doc is None:
        return None
    poses_data = lib_doc.get("poses_data", {})
    pose_data  = poses_data.get(json_file, {})
    semantica  = pose_data.get("_semantica", {})
    return semantica.get("nombre_legible", None)


def guardar_calificacion_pose(context, json_file, pose_idx, query, score, comment=""):
    """
    Guarda una calificacion (1-10) para la pose `json_file` (indice `pose_idx`
    dentro del archivo, normalmente 0) tanto en su propio .json como en
    pose_library.json. Devuelve (ok, mensaje, promedio, cantidad, estado).
    """
    st = getattr(context.scene, "alfst", None)
    poses_dir = bpy.path.abspath(st.poses_dir) if st else ""
    fp_pose = os.path.join(poses_dir, json_file) if poses_dir else ""

    if not fp_pose or not os.path.isfile(fp_pose):
        return False, f"No se encontro el archivo de pose: {json_file}", 0.0, 0, "NUEVA"

    doc = _leer_json(fp_pose)
    if doc is None:
        return False, f"No se pudo leer el JSON de la pose: {json_file}", 0.0, 0, "NUEVA"

    poses = doc.get("poses", [])
    if not (0 <= pose_idx < len(poses)):
        return False, "Indice de pose invalido dentro del archivo.", 0.0, 0, "NUEVA"

    record = poses[pose_idx]
    # Guardar solo la calificacion mas reciente — una sola entrada por pose.
    # No acumular historial: si el usuario recalifica, la nueva reemplaza la anterior.
    nueva_entrada = {
        "query":     query,
        "score":     int(score),
        "comment":   comment,
        "timestamp": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
    }
    record["user_score_history"] = [nueva_entrada]

    cantidad = 1
    promedio = float(int(score))
    estado   = calcular_estado_calificacion(promedio, cantidad)

    record["user_score_avg"]    = promedio
    record["user_score_count"]  = cantidad
    record["user_score_status"] = estado

    doc["poses"][pose_idx] = record
    _escribir_json(fp_pose, doc)

    # ── Reflejar en pose_library.json ──
    lib_fp = pose_library_path(context)
    lib_doc = _leer_json(lib_fp)
    if lib_doc is None:
        lib_doc = {"_descripcion": "Libreria central de poses Alfred",
                   "version": 1, "calificaciones": {}}
    if "calificaciones" not in lib_doc:
        lib_doc["calificaciones"] = {}

    lib_doc["calificaciones"][json_file] = {
        "avg":                  promedio,
        "count":                cantidad,
        "status":               estado,
        "ultima_query":         query,
        "ultimo_comentario":    comment,
        "ultima_actualizacion": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
    }

    # ── Escribir también dentro de poses_data para que el generador
    #    y cualquier otra IA lo vea junto a la semántica de la pose ──
    if "poses_data" not in lib_doc:
        lib_doc["poses_data"] = {}
    if json_file not in lib_doc["poses_data"]:
        lib_doc["poses_data"][json_file] = {}

    lib_doc["poses_data"][json_file]["_calificacion_usuario"] = {
        "score":        int(score),
        "status":       estado,
        "query":        query,
        "comentario":   comment,
        "timestamp":    datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
        "nota":         (
            "Calificacion manual del animador (1-10). "
            "10 = la pose describe exactamente lo que se pidio. "
            "El generador prefiere poses con score >= 6. "
            "Poses con score <= 3 son candidatas a descarte."
        ),
    }

    try:
        os.makedirs(os.path.dirname(lib_fp), exist_ok=True)
        _escribir_json(lib_fp, lib_doc)
        lib_ok = True
    except Exception as e:
        lib_ok = False
        return True, (f"Calificacion guardada en la pose, pero NO se pudo "
                       f"escribir pose_library.json ({e})"), promedio, cantidad, estado

    return True, "Calificacion guardada en la pose y en pose_library.json.", promedio, cantidad, estado

def leer_calificacion_actual(context, json_file, pose_idx=0):
    """Lectura rapida (solo para mostrar en la UI) del estado de calificacion
    actual de una pose, sin modificar nada."""
    st = getattr(context.scene, "alfst", None)
    poses_dir = bpy.path.abspath(st.poses_dir) if st else ""
    fp_pose = os.path.join(poses_dir, json_file) if poses_dir and json_file else ""
    if not fp_pose or not os.path.isfile(fp_pose):
        return None
    doc = _leer_json(fp_pose)
    if doc is None:
        return None
    poses = doc.get("poses", [])
    if not (0 <= pose_idx < len(poses)):
        return None
    record = poses[pose_idx]
    return {
        "avg":    record.get("user_score_avg", 0.0),
        "count":  record.get("user_score_count", 0),
        "status": record.get("user_score_status", "NUEVA"),
        "history": record.get("user_score_history", []),
    }
