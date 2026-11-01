# -*- coding: utf-8 -*-
"""
path_recorder.py — Rat 1 Animation Studio
Sistema integrado de trazado de recorrido (Paso 1) y disparo de
generacion de slots (Paso 2), portado desde alfred_animation_studio.

ALCANCE DE ESTE PORT (pedido explicito de Kebyn): SOLO el sistema de
recorrido -- grabar puntos por seleccion de faces, detectar tramos
caminar / saltar_subir / saltar_bajar / parada, previsualizar el
recorrido en el viewport y exportar los slots. Las 8 animaciones de
accion puntual de Alfred (colocar_antorcha, golpe_estomago_1,
levantarse_1/2, arrodillarse_1, conversar_1, resbalarse_1,
colocar_mesa_de_crafteo) NO se portaron -- tipo_segmento solo admite
AUTO / PARADA. Tampoco se porto el Paso 3 (segmentos/poses), el sistema
de ojos, filtros organicos, oscilaciones de bones, ni importacion de
objetos -- eso pertenece a addons que ya tienen personaje completo.

BIOMECANICA (Kebyn, 2026-09-03): "Reproducir recorrido" (RAT1PR_OT_PreviewPath)
ya anima los 22 bones del armature "body1_1" (cuadrupedo: trote diagonal en
caminar, secuencia de poses clave agazapamiento/despegue/vuelo/aterrizaje en
los saltos) -- las mismas formulas que generate_slots_rat_1.py, duplicadas
aca en metodos estaticos de RAT1PR_OT_PreviewPath (mismo patron que usa
Alfred entre su operador de preview y su generador de slots: dos lugares que
DEBEN coincidir si se ajusta alguna amplitud o formula).

Sin sistema de tunel — solo coordenadas de faces (centros de poligono),
igual que en Alfred.
"""

import bpy
import bmesh
import blf
import gpu
import math
import os
from datetime import date
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from bpy_extras import view3d_utils
from bpy.props import (
    CollectionProperty, StringProperty, FloatVectorProperty,
    BoolProperty, FloatProperty, IntProperty, EnumProperty,
)
from bpy.types import PropertyGroup, Operator
from bpy.app.handlers import persistent

from .constants import ROOT_NAME, ARM_NAME, MESH_NAME, ALL_OBJECTS

# ── Variables globales de modulo ──────────────────────────────────────────────
_draw_handle    = None
_last_face_idx  = None


def _deferred_deselect_face(obj_name, face_index):
    """Ver docstring identico en alfred_animation_studio/path_recorder.py:
    deselecciona la cara recien registrada de forma diferida (via
    bpy.app.timers), porque modificar el bmesh dentro del handler de
    depsgraph_update_post no es seguro."""
    obj = bpy.data.objects.get(obj_name)
    if obj is None or obj.type != "MESH" or obj.mode != "EDIT":
        return None
    bm = bmesh.from_edit_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    if 0 <= face_index < len(bm.faces):
        bm.faces[face_index].select = False
        bmesh.update_edit_mesh(obj.data)
    return None


# =============================================================================
# PROPERTY GROUPS
# =============================================================================

class RAT1PathPoint(PropertyGroup):
    coords:     FloatVectorProperty(name="Coords",     size=3, default=(0.0, 0.0, 0.0))
    # FIX (z-fighting recorrido, 2026-09-04): normal de la face en el momento
    # del click, en espacio mundo. Se usa para separar la linea/puntos del
    # recorrido de la superficie del mesh a lo largo de la normal real (ver
    # _offset_along_normal), en vez de hacerlo hacia la camara. Default
    # (0,0,0) = recorrido grabado con una version anterior del addon, sin
    # normal guardada; en ese caso el dibujo cae de vuelta al offset viejo
    # hacia camara (ver _offset_along_normal).
    normal:     FloatVectorProperty(name="Normal",     size=3, default=(0.0, 0.0, 0.0))
    texture:    StringProperty(name="Textura",         default="")
    face_index: StringProperty(name="Face Index",      default="")

    # AMPLIADO (Kebyn, 2026-09-03): 4 acciones puntuales propias de rata,
    # agregadas siguiendo el mismo principio que las acciones puntuales de
    # Alfred (ver alfred_animation_studio/docs/GUIA_NUEVOS_SEGMENTOS_ESPECIALES.md,
    # sub-patron B: "Animacion pura", sin objeto). Deben coincidir siempre
    # con los overrides de _detect_move() (mas abajo) y de
    # detect_movement_type() en generate_slots_rat_1.py.
    tipo_segmento: EnumProperty(
        name="Tipo",
        description=(
            "Tipo de movimiento/accion hacia el siguiente punto del recorrido. "
            "'Auto' detecta caminar/subir/bajar segun la geometria real. "
            "'Parada' fuerza que el personaje llegue aqui y se quede "
            "detenido antes de continuar. Las demas son acciones puntuales de "
            "rata (animacion corporal pura, sin objeto): abarcan este punto y "
            "el siguiente (coordenadas reales, sin duplicar)."
        ),
        items=[
            ("AUTO",   "Caminar", "Movimiento automatico: caminar o saltar segun la geometria", "ANIM_DATA", 0),
            ("PARADA", "Parada",  "El personaje se detiene en este punto antes de continuar",   "PAUSE",     1),
            ("PARARSE_DOS_PATAS", "Pararse en 2 patas",
             "La rata se yergue sobre las patas traseras para vigilar/olfatear el entorno",
             "ARMATURE_DATA", 2),
            ("OLFATEAR", "Olfatear",
             "La rata olfatea el entorno con movimientos rapidos de cabeza",
             "ARMATURE_DATA", 3),
            ("ESCARBAR", "Escarbar",
             "La rata escarba el suelo con las patas delanteras",
             "ARMATURE_DATA", 4),
            ("ROER", "Roer / morder",
             "La rata roe o muerde algo sosteniendolo con las patas delanteras",
             "ARMATURE_DATA", 5),
        ],
        default="AUTO",
    )
    parada_frames_punto: IntProperty(
        name="Frames parado aqui",
        description="Cantidad de frames que el personaje permanece detenido en este punto antes de seguir el recorrido",
        default=24, min=1, soft_max=99999,
    )


class RAT1ParadaFrames(PropertyGroup):
    """Duracion (en frames) de UNA parada individual del recorrido.
    Mismo patron que ALFREDParadaFrames en Alfred."""
    frames: IntProperty(
        name="Frames",
        description="Frames que dura esta parada especifica (root inmovil)",
        default=60, min=1, soft_max=99999,
    )


class RAT1WalkStyleEntry(PropertyGroup):
    """Estilo de caminata de UN tramo 'caminar' individual del recorrido.
    Se conserva como scaffolding para cuando exista la biomecanica real
    de caminar -- por ahora solo afecta la VELOCIDAD del placeholder
    root-only (ver WALK_STYLE_PARAMS en generate_slots_rat_1.py)."""
    style: EnumProperty(
        name="Estilo de caminata",
        description="Variante de la animacion de caminar para este tramo especifico",
        items=[
            ("NORMAL", "Caminar Normal", "Caminata estandar (por defecto)", "FORWARD", 0),
            ("LENTO", "Caminar Lento", "Caminata lenta / cautelosa", "TRIA_LEFT", 1),
            ("HERIDO", "Caminar Herido", "Caminata herida / cojeando", "ERROR", 2),
            ("RAPIDO", "Caminar Rapido", "Caminata rapida", "TRIA_RIGHT", 3),
            ("CORRER", "Correr", "Carrera / trote", "TRACKING_FORWARDS", 4),
        ],
        default="NORMAL",
    )
    applied_style: StringProperty(default="")


class RAT1PathSettings(PropertyGroup):
    """Configuracion y estado del Path Recorder integrado."""

    recording_active: BoolProperty(
        name="Grabacion activa",
        description="Detecta automaticamente las faces seleccionadas",
        default=False,
    )
    show_path_viz: BoolProperty(
        name="Visualizar recorrido",
        description="Muestra la linea y los puntos numerados del recorrido trazado en el viewport, incluso sin estar grabando",
        default=False,
    )
    path_points: CollectionProperty(type=RAT1PathPoint)

    slot_inicio: IntProperty(name="Primer slot", default=1, min=1, max=999)
    frame_inicio: IntProperty(name="Frame inicial", default=1, min=0)
    frame_fin_manual: IntProperty(name="Frame final", description="Frame final de la animacion (solo modo 1 coordenada)", default=100, min=2, soft_max=99999)

    frames_por_unidad: FloatProperty(
        name="Frames/unidad (caminar, placeholder)",
        description="Frames por unidad de distancia del placeholder root-only de 'caminar' (sin biomecanica todavia)",
        default=24.0, min=2.0, max=200.0,
    )
    frames_parada: IntProperty(
        name="Frames por parada (default)",
        default=60, min=1, soft_max=99999,
    )
    paradas_frames: CollectionProperty(type=RAT1ParadaFrames)

    root_rot_x: FloatProperty(name="Rot X", default=0.0, precision=1)
    root_rot_y: FloatProperty(name="Rot Y", default=0.0, precision=1)
    root_rot_z: FloatProperty(name="Rot Z", default=-90.0, precision=1)

    walk_style: EnumProperty(
        name="Estilo de caminata (default)",
        items=[
            ("NORMAL", "Caminar Normal", "Caminata estandar (por defecto)", "FORWARD", 0),
            ("LENTO", "Caminar Lento", "Caminata lenta / cautelosa", "TRIA_LEFT", 1),
            ("HERIDO", "Caminar Herido", "Caminata herida / cojeando", "ERROR", 2),
            ("RAPIDO", "Caminar Rapido", "Caminata rapida", "TRIA_RIGHT", 3),
            ("CORRER", "Correr", "Carrera / trote", "TRACKING_FORWARDS", 4),
        ],
        default="NORMAL",
    )
    walk_styles: CollectionProperty(type=RAT1WalkStyleEntry)

    output_dir: StringProperty(
        name="Carpeta salida",
        description="Carpeta donde se guardan los scripts slot_NNN_*.py generados",
        default=r"C:\Users\user\Desktop\Rat_1_Animacion\animacion",
        subtype="DIR_PATH",
    )

    status_msg:        StringProperty(default="")
    anim_frame_fin:    IntProperty(default=0)
    show_coords_list:  BoolProperty(name="Mostrar lista de coordenadas", default=True)

    blend_filepath: StringProperty(
        name="Archivo .blend del personaje",
        description="Ruta al archivo .blend que contiene el rig de rat_1",
        default="",
        subtype="FILE_PATH",
    )


def sync_paradas_frames(pc):
    """Sincroniza pc.paradas_frames con la cantidad real de paradas
    detectadas. Mismo patron que sync_paradas_frames() en Alfred."""
    try:
        if len(pc.path_points) >= 2:
            expanded, _ = _expand_points_with_paradas(pc.path_points)
            segments = _group_segments(expanded)
        else:
            segments = []
    except Exception:
        segments = []

    n_paradas = sum(1 for s in segments if s.get("type") == "parada")
    n_actual  = len(pc.paradas_frames)

    if n_actual < n_paradas:
        for _ in range(n_paradas - n_actual):
            item = pc.paradas_frames.add()
            item.frames = pc.frames_parada
    elif n_actual > n_paradas:
        for _ in range(n_actual - n_paradas):
            pc.paradas_frames.remove(len(pc.paradas_frames) - 1)
    return n_paradas


def sync_walk_styles(pc):
    """Sincroniza pc.walk_styles con la cantidad real de tramos 'caminar'.
    Mismo patron que sync_walk_styles() en Alfred."""
    try:
        if len(pc.path_points) >= 2:
            expanded, _ = _expand_points_with_paradas(pc.path_points)
            segments = _group_segments(expanded)
        else:
            segments = []
    except Exception:
        segments = []

    n_caminar = sum(1 for s in segments if s.get("type") == "caminar")
    n_actual  = len(pc.walk_styles)

    if n_actual < n_caminar:
        for _ in range(n_caminar - n_actual):
            item = pc.walk_styles.add()
            item.style = pc.walk_style
            item.applied_style = item.style
    elif n_actual > n_caminar:
        for _ in range(n_actual - n_caminar):
            pc.walk_styles.remove(len(pc.walk_styles) - 1)
    return n_caminar


# =============================================================================
# HANDLER — deteccion automatica de face seleccionada
# =============================================================================

@persistent
def _rat1_face_selection_handler(scene):
    """Se ejecuta en depsgraph_update_post. Registra faces seleccionadas.
    Identico en logica a _alfred_face_selection_handler()."""
    global _last_face_idx

    path_cfg = getattr(scene, "rat1_path", None)
    if path_cfg is None or not path_cfg.recording_active:
        return

    obj = bpy.context.active_object
    if obj is None or obj.type != "MESH" or obj.mode != "EDIT":
        return

    bm = bmesh.from_edit_mesh(obj.data)
    selected = [f for f in bm.faces if f.select]
    if len(selected) != 1:
        _last_face_idx = None
        return

    face = selected[0]
    face_id = str(face.index)

    if _last_face_idx == face_id:
        return

    _last_face_idx = face_id
    center_local  = face.calc_center_median()
    center_global = obj.matrix_world @ center_local
    # FIX (z-fighting recorrido, 2026-09-04): normal real de la face,
    # transformada a espacio mundo, para poder despegar el dibujo del
    # recorrido de la superficie a lo largo de esta normal (ver
    # _offset_along_normal) en vez de hacia la camara.
    normal_global = (obj.matrix_world.to_3x3() @ face.normal).normalized()

    mat_name = "No Material"
    if obj.data.materials and face.material_index < len(obj.data.materials):
        mat = obj.data.materials[face.material_index]
        if mat:
            mat_name = mat.name

    pt            = path_cfg.path_points.add()
    pt.coords     = center_global
    pt.normal     = normal_global
    pt.texture    = mat_name
    pt.face_index = face_id

    bpy.app.timers.register(
        lambda _n=obj.name, _i=face.index: _deferred_deselect_face(_n, _i),
        first_interval=0.0,
    )

    sync_paradas_frames(path_cfg)
    sync_walk_styles(path_cfg)

    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            area.tag_redraw()


# =============================================================================
# DIBUJO 3D — visualizacion del recorrido en el viewport
# =============================================================================

def _ensure_draw_handler():
    global _draw_handle
    if _draw_handle is None:
        _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_path_3d, (), "WINDOW", "POST_VIEW"
        )


def _maybe_remove_draw_handler(pc):
    global _draw_handle
    if getattr(pc, "recording_active", False) or getattr(pc, "show_path_viz", False):
        return
    if _draw_handle is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
        except Exception:
            pass
        _draw_handle = None


def _offset_along_normal(coord, normal, rv3d):
    """Despega `coord` de la superficie del mesh una fraccion minima de la
    distancia a camara, a lo largo de la NORMAL REAL de la face (no hacia la
    camara). Los puntos del recorrido son el centro de la face donde se
    clickeo (ver _rat1_face_selection_handler): quedan pegados a la
    superficie del mesh, coplanares con el, y con depth_test_set('LESS_EQUAL')
    un empate de profundidad SIEMPRE lo gana el overlay (se dibuja despues
    del pase opaco) -- por eso el recorrido nunca se veia tapado por el mesh
    (z-fighting estructural, no intermitente).

    FIX (2026-09-04): la version anterior empujaba hacia la camara en vez de
    a lo largo de la normal. Eso tiene dos problemas: (1) en angulos rasantes
    la separacion en profundidad-de-pantalla que produce se reduce casi a
    cero, o sea el z-fighting seguia ahi en muchos angulos; y (2) al mover el
    punto HACIA la camara, un punto que en la realidad esta apenas detras de
    una colina/loma (y deberia quedar tapado por ella) se corria lo
    suficiente como para terminar delante de esa colina en el z-buffer --
    exactamente el sintoma reportado: "las lineas del recorrido siempre
    quedan expuestas", incluso donde el terreno si deberia taparlas. Separar
    a lo largo de la normal real es independiente del angulo de camara y no
    le resta profundidad real a los oclusores autenticos (colinas, paredes),
    asi que la linea se sigue tapando correctamente cuando corresponde.

    Si el punto viene de un recorrido grabado con una version vieja del addon
    (sin normal guardada, normal == (0,0,0)) se cae de vuelta al offset hacia
    camara de antes, para no romper recorridos ya grabados."""
    if rv3d is None:
        return coord
    try:
        cam_loc = rv3d.view_matrix.inverted().translation
    except Exception:
        return coord
    to_cam = cam_loc - coord
    dist = to_cam.length
    if dist < 1e-6:
        return coord
    offset = min(max(dist * 0.001, 0.0005), 0.05)

    if normal is not None and normal.length > 1e-6:
        direction = normal.normalized()
        # Si por algun motivo la normal mira "para adentro" del lado
        # opuesto a la camara, igual la usamos tal cual: el objetivo es
        # despegar de la superficie real, no acercarse a la camara.
        return coord + direction * offset

    # Fallback: recorrido viejo sin normal guardada.
    return coord + (to_cam / dist) * offset


def _draw_path_3d():
    scene = bpy.context.scene
    path_cfg = getattr(scene, "rat1_path", None)
    if path_cfg is None or len(path_cfg.path_points) < 1:
        return

    rv3d = bpy.context.region_data

    points    = []
    col_pts   = []
    lines     = []
    col_lines = []

    for i, pt in enumerate(path_cfg.path_points):
        coord = _offset_along_normal(Vector(pt.coords), Vector(pt.normal), rv3d)
        points.append(coord)
        col_pts.append((0.85, 0.55, 0.25, 1.0))  # marron rata
        if i > 0:
            prev_pt = path_cfg.path_points[i - 1]
            prev = _offset_along_normal(Vector(prev_pt.coords), Vector(prev_pt.normal), rv3d)
            lines    += [prev, coord]
            col_lines += [(1.0, 0.9, 0.0, 1.0), (1.0, 0.9, 0.0, 1.0)]

    gpu.state.blend_set("ALPHA")
    gpu.state.depth_test_set("LESS_EQUAL")
    gpu.state.line_width_set(4.0)
    gpu.state.point_size_set(10.0)

    shader = gpu.shader.from_builtin("SMOOTH_COLOR")
    if lines:
        batch_for_shader(shader, "LINES",  {"pos": lines,  "color": col_lines}).draw(shader)
    if points:
        batch_for_shader(shader, "POINTS", {"pos": points, "color": col_pts}).draw(shader)

    gpu.state.line_width_set(1.0)
    gpu.state.point_size_set(1.0)

    region   = bpy.context.region
    rv3d     = bpy.context.region_data
    if region is not None and rv3d is not None:
        gpu.state.depth_test_set("NONE")
        font_id = 0
        blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
        blf.size(font_id, 16)
        for i, pt in enumerate(path_cfg.path_points):
            coord_3d = Vector(pt.coords)
            coord_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, coord_3d)
            if coord_2d is None:
                continue
            blf.position(font_id, coord_2d.x + 8, coord_2d.y + 8, 0)
            blf.draw(font_id, str(i + 1))
        gpu.state.depth_test_set("LESS_EQUAL")


# =============================================================================
# DETECCION DE SEGMENTOS (solo AUTO / PARADA)
# =============================================================================

def _detect_move(p0, p1):
    """Debe coincidir siempre con detect_movement_type() en
    generate_slots_rat_1.py. AMPLIADO (Kebyn, 2026-09-03): 4 acciones
    puntuales de rata (pararse_dos_patas, olfatear, escarbar, roer),
    agregadas con el mismo criterio que los overrides de accion puntual
    de Alfred (_detect_move() en alfred_animation_studio/path_recorder.py):
    el override SIEMPRE se evalua ANTES de la comparacion de coordenadas,
    asi la accion funciona sin importar si points[0]/points[1] coinciden
    o no."""
    tipo = getattr(p0, "tipo_segmento", "AUTO")
    if tipo == "PARARSE_DOS_PATAS":
        return "pararse_dos_patas"
    if tipo == "OLFATEAR":
        return "olfatear"
    if tipo == "ESCARBAR":
        return "escarbar"
    if tipo == "ROER":
        return "roer"

    x0, y0, z0 = p0.coords[0], p0.coords[1], p0.coords[2]
    x1, y1, z1 = p1.coords[0], p1.coords[1], p1.coords[2]
    x0, y0, z0 = round(x0, 2), round(y0, 2), round(z0, 2)
    x1, y1, z1 = round(x1, 2), round(y1, 2), round(z1, 2)
    if x0 == x1 and y0 == y1 and z0 == z1:
        if tipo == "PARADA":
            return "parada"
        return "caminar"
    if   z1 > z0: return "saltar_subir"
    elif z1 < z0: return "saltar_bajar"
    else:          return "caminar"


def _detect_move_geom(p0, p1):
    """Version SOLO geometrica (ignora el override PARADA) -- usada por el
    panel para decidir si el dropdown de un punto debe mostrarse editable."""
    x0, y0, z0 = p0.coords[0], p0.coords[1], p0.coords[2]
    x1, y1, z1 = p1.coords[0], p1.coords[1], p1.coords[2]
    x0, y0, z0 = round(x0, 2), round(y0, 2), round(z0, 2)
    x1, y1, z1 = round(x1, 2), round(y1, 2), round(z1, 2)
    if x0 == x1 and y0 == y1 and z0 == z1:
        return "caminar"
    if   z1 > z0: return "saltar_subir"
    elif z1 < z0: return "saltar_bajar"
    else:          return "caminar"


# ============================================================
# SISTEMA DE ORIENTACION DEL PREVIEW -- PORTADO de
# alfred_animation_studio/generate_slots_alfred.py (2026-09-03).
#
# Debe coincidir con el sistema embebido en generate_slots_rat_1.py
# (_compute_direction_angle_local / RotationSmoother dentro de
# _SHARED_HELPERS) -- mismo patron de "dos lugares que deben coincidir"
# documentado en el docstring del modulo. Antes, el bucle de "caminar"
# en RAT1PR_OT_PreviewPath.execute() calculaba el rumbo de cada
# sub-tramo con atan2 crudo (sin snap cardinal/diagonal) y lo aplicaba
# de golpe (sin transicion), asi que un giro en diagonal se veia como
# un salto instantaneo de orientacion en vez de un giro progresivo, y
# saltar_subir/saltar_bajar mantenian una orientacion fija durante todo
# el salto en vez de girar hacia el rumbo real del salto.
# ============================================================

def _snap_direction_angle(dx, dy, fallback_deg):
    """Angulo cardinal/diagonal (grados) para el vector (dx, dy), o
    fallback_deg si no hay desplazamiento horizontal. Mismo criterio de
    snap que _compute_direction_angle_local() en generate_slots_rat_1.py
    / generate_slots_alfred.py."""
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return fallback_deg
    ang_raw = math.degrees(math.atan2(dx, dy))
    ang_rounded = round(ang_raw / 90.0) * 90.0
    ang = ang_rounded if abs(ang_raw - ang_rounded) < 45 else -ang_raw
    while ang > 180: ang -= 360
    while ang < -180: ang += 360
    if ang == 90: ang = -90
    elif ang == -90: ang = 90
    elif ang == 180: ang = -180
    return ang


class _RotationSmoother:
    """Suaviza cambios de orientacion con curva S (smoothstep). Identico
    al RotationSmoother embebido en generate_slots_rat_1.py (caminar)."""
    def __init__(self, smoothing_frames=12):
        self.smoothing_frames = smoothing_frames
        self.previous_rotation = None
        self.transition_start_frame = None
        self.transition_start_rotation = None
        self.target_rotation = None

    def smooth_rotation(self, target_rotation, current_frame):
        target_rotation = self._normalize(target_rotation)
        if self.previous_rotation is None:
            self.previous_rotation = target_rotation
            return target_rotation
        angle_diff = self._diff(target_rotation, self.previous_rotation)
        if abs(angle_diff) < 5:
            self.previous_rotation = target_rotation
            self.transition_start_frame = None
            return target_rotation
        if self.transition_start_frame is None:
            self.transition_start_frame = current_frame
            self.transition_start_rotation = self.previous_rotation
            self.target_rotation = target_rotation
        elapsed = current_frame - self.transition_start_frame
        progress = min(elapsed / self.smoothing_frames, 1.0)
        eased = self._smoothstep(progress)
        smoothed = self.transition_start_rotation + self._diff(
            self.target_rotation, self.transition_start_rotation) * eased
        if progress >= 1.0:
            self.previous_rotation = target_rotation
            self.transition_start_frame = None
            return target_rotation
        return smoothed

    def _normalize(self, a):
        while a > 180: a -= 360
        while a < -180: a += 360
        return a

    def _diff(self, target, current):
        d = target - current
        while d > 180: d -= 360
        while d < -180: d += 360
        return d

    def _smoothstep(self, x):
        if x <= 0: return 0.0
        if x >= 1: return 1.0
        return x * x * (3.0 - 2.0 * x)


def _group_segments(path_points):
    """Agrupa los puntos en segmentos: caminar (multi-punto),
    saltar_subir/bajar (2 puntos), parada (2 puntos identicos).

    FIX (Kebyn, 2026-09-04, "salto de coordenada tras accion puntual"):
    las 4 acciones puntuales de rata (pararse_dos_patas/olfatear/
    escarbar/roer) dejan el root FIJO en pts[i] durante todo el slot
    (ver PORT_NOTES.md v0.3/v0.5, generate_pararse_dos_patas()/etc en
    generate_slots_rat_1.py) -- nunca caminan hasta pts[i+1]. Antes esas
    4 acciones caian en la rama generica de abajo (segmento de 2 puntos
    sin fusion), asi que si el tramo "caminar" siguiente del recorrido
    arrancaba en pts[i+1], la rata aparecia de golpe ahi (nunca se la
    vio caminar el tramo pts[i]->pts[i+1], porque quedo fija en pts[i]
    durante la accion). Mismo mecanismo que colocar_antorcha/
    golpe_estomago_1 en Alfred (ver group_segments() en
    alfred_animation_studio/generate_slots_alfred.py): se fusiona el
    tramo de alcance pts[i]->pts[i+1] con TODO el caminar real que le
    sigue, en un solo segmento "caminar" continuo -- asi el recorrido no
    tiene saltos de coordenada Y el walk_cycle no reinicia de fase a
    mitad de camino. Debe coincidir con group_segments() en
    generate_slots_rat_1.py."""
    pts = list(path_points)
    segments = []
    i = 0
    _ACCION_OVERRIDES = ("PARARSE_DOS_PATAS", "OLFATEAR", "ESCARBAR", "ROER")
    while i < len(pts) - 1:
        # FIX (mismo criterio que Alfred, "caminar fantasma entre Parada
        # y accion siguiente"): pts[i] es el punto duplicado que
        # _expand_points_with_paradas() inserta justo despues de una
        # "parada". Si el punto siguiente ya esta marcado con una accion
        # puntual, ese punto arrancara su propio segmento en la proxima
        # vuelta del while de todos modos -- no hace falta generar un
        # "caminar" fantasma entre medio (el personaje ya esta fijo en
        # el lugar de la parada).
        if (getattr(pts[i], "es_parada_dup", False)
                and getattr(pts[i], "tipo_segmento", "AUTO") not in _ACCION_OVERRIDES
                and getattr(pts[i + 1], "tipo_segmento", "AUTO") in _ACCION_OVERRIDES):
            i += 1
            continue

        move = _detect_move(pts[i], pts[i + 1])
        if move == "caminar":
            group = [pts[i]]
            while i < len(pts) - 1 and _detect_move(pts[i], pts[i + 1]) == "caminar":
                group.append(pts[i + 1])
                i += 1
            segments.append({"type": "caminar", "points": group})
        elif move in ("pararse_dos_patas", "olfatear", "escarbar", "roer"):
            segments.append({"type": move, "points": [pts[i], pts[i + 1]]})
            # Si pts[i]/pts[i+1] son la misma coordenada, no hay
            # distancia real que recorrer -- se omite el tramo de
            # alcance "caminar" (mismo criterio que colocar_antorcha en
            # Alfred, evita un walk cycle completo en el lugar).
            _c0, _c1 = pts[i].coords, pts[i + 1].coords
            _same_coord = (round(_c0[0], 2) == round(_c1[0], 2)
                           and round(_c0[1], 2) == round(_c1[1], 2)
                           and round(_c0[2], 2) == round(_c1[2], 2))
            # Si pts[i+1] (destino de la accion) esta marcado como
            # PARADA, el personaje se va a quedar quieto ahi de todos
            # modos apenas empiece esa parada -- el tramo de alcance no
            # aporta nada, se omite igual que el caso de arriba.
            _dest_es_parada = getattr(pts[i + 1], "tipo_segmento", "AUTO") == "PARADA"
            if _same_coord or _dest_es_parada:
                i = i + 1
            else:
                group = [pts[i], pts[i + 1]]
                j = i + 1
                while j < len(pts) - 1 and _detect_move(pts[j], pts[j + 1]) == "caminar":
                    group.append(pts[j + 1])
                    j += 1
                segments.append({"type": "caminar", "points": group})
                i = j
        else:
            segments.append({"type": move, "points": [pts[i], pts[i + 1]]})
            i += 1
    return segments


class _StopPointStub:
    """Punto DUPLICADO en memoria para representar una 'parada'. Igual a
    _StopPointStub en Alfred."""
    __slots__ = ("coords", "texture", "face_index", "es_parada_dup")

    def __init__(self, coords, texture, face_index):
        self.coords     = tuple(coords)
        self.texture    = texture
        self.face_index = face_index
        self.es_parada_dup = True


def _expand_points_with_paradas(pts):
    """Inserta un punto duplicado despues de cada punto marcado PARADA.
    Identico en logica a _expand_points_with_paradas() (Alfred), sin los
    overrides de accion puntual."""
    expanded = []
    frames_paradas_marcadas = []
    n = len(pts)
    for i, pt in enumerate(pts):
        expanded.append(pt)
        override_activo = getattr(pt, "tipo_segmento", "AUTO") == "PARADA"
        if override_activo and i < n - 1:
            real_move = _detect_move(pt, pts[i + 1])
            if real_move != "caminar":
                override_activo = False
        if override_activo:
            expanded.append(_StopPointStub(pt.coords, pt.texture, pt.face_index))
            frames_paradas_marcadas.append(max(1, int(pt.parada_frames_punto)))
    return expanded, frames_paradas_marcadas


def calcular_estimacion_geometrica(scene):
    """Estimacion de frames por tramo (placeholder root-only, sin
    HALF_CYCLE biomecanico porque todavia no hay ciclo de piernas real).
    Devuelve una lista de dicts (mismo formato que en Alfred) o None."""
    pc = getattr(scene, "rat1_path", None)
    if pc is None or len(pc.path_points) <= 1:
        return None

    from .generate_slots_rat_1 import (
        WALK_STYLE_PARAMS as _WSP, FRAMES_PER_UNIT_BASE, SALTAR_SUBIR_FRAMES, SALTAR_BAJAR_FRAMES,
        TOTAL_FRAMES_PARARSE_DOS_PATAS, TOTAL_FRAMES_OLFATEAR,
        TOTAL_FRAMES_ESCARBAR, TOTAL_FRAMES_ROER,
    )

    pts = list(pc.path_points)
    expanded_pts, frames_paradas_marcadas = _expand_points_with_paradas(pts)
    segs = _group_segments(expanded_pts)

    slots = []
    parada_idx = 0
    caminar_idx = 0
    for i, seg in enumerate(segs):
        seg_type = seg["type"]
        seg_pts = seg["points"]
        if seg_type == "caminar":
            style_key = (pc.walk_styles[caminar_idx].style
                         if caminar_idx < len(pc.walk_styles) else pc.walk_style)
            style_est = _WSP.get(style_key, _WSP["NORMAL"])
            dist = 0.0
            for j in range(len(seg_pts) - 1):
                dx = seg_pts[j + 1].coords[0] - seg_pts[j].coords[0]
                dy = seg_pts[j + 1].coords[1] - seg_pts[j].coords[1]
                dist += math.sqrt(dx * dx + dy * dy)
            dist = max(dist, 0.0001)
            frames = dist * FRAMES_PER_UNIT_BASE / max(style_est["speed_mult"], 0.01)
            total_f = max(2, round(frames))
            slots.append({
                "slot": i + 1, "tipo": "caminar",
                "label": f"caminar {style_est['label']} (placeholder)",
                "frames_estimados": total_f, "caminar_idx": caminar_idx,
            })
            caminar_idx += 1
        elif seg_type == "saltar_subir":
            slots.append({"slot": i + 1, "tipo": "saltar_subir",
                           "label": "saltar_subir (placeholder)", "frames_estimados": SALTAR_SUBIR_FRAMES})
        elif seg_type == "saltar_bajar":
            slots.append({"slot": i + 1, "tipo": "saltar_bajar",
                           "label": "saltar_bajar (placeholder)", "frames_estimados": SALTAR_BAJAR_FRAMES})
        elif seg_type == "pararse_dos_patas":
            slots.append({"slot": i + 1, "tipo": "pararse_dos_patas",
                           "label": "pararse en 2 patas", "frames_estimados": TOTAL_FRAMES_PARARSE_DOS_PATAS})
        elif seg_type == "olfatear":
            slots.append({"slot": i + 1, "tipo": "olfatear",
                           "label": "olfatear", "frames_estimados": TOTAL_FRAMES_OLFATEAR})
        elif seg_type == "escarbar":
            slots.append({"slot": i + 1, "tipo": "escarbar",
                           "label": "escarbar", "frames_estimados": TOTAL_FRAMES_ESCARBAR})
        elif seg_type == "roer":
            slots.append({"slot": i + 1, "tipo": "roer",
                           "label": "roer / morder", "frames_estimados": TOTAL_FRAMES_ROER})
        else:  # parada
            if parada_idx < len(frames_paradas_marcadas):
                frames_parada_actual = frames_paradas_marcadas[parada_idx]
            elif parada_idx < len(pc.paradas_frames):
                frames_parada_actual = pc.paradas_frames[parada_idx].frames
            else:
                frames_parada_actual = pc.frames_parada
            slots.append({"slot": i + 1, "tipo": "parada",
                           "label": "parada", "frames_estimados": frames_parada_actual})
            parada_idx += 1

    return slots


# =============================================================================
# OPERADORES — Paso 1 (grabacion)
# =============================================================================

class RAT1PR_OT_ToggleRecording(Operator):
    bl_idname  = "rat1pr.toggle_recording"
    bl_label   = "Toggle Recording"
    bl_description = "Inicia o detiene la grabacion de puntos del recorrido"
    bl_options = {"REGISTER"}

    def execute(self, context):
        pc = context.scene.rat1_path
        pc.recording_active = not pc.recording_active
        if pc.recording_active:
            _ensure_draw_handler()
            self.report({"INFO"}, "Grabacion INICIADA — selecciona faces en modo EDIT")
        else:
            _maybe_remove_draw_handler(pc)
            self.report({"INFO"}, "Grabacion DETENIDA")
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
        return {"FINISHED"}


class RAT1PR_OT_TogglePathViz(Operator):
    bl_idname  = "rat1pr.toggle_path_viz"
    bl_label   = "Visualizar recorrido"
    bl_description = "Muestra u oculta la linea y los puntos numerados del recorrido trazado en el viewport, sin necesidad de estar grabando"
    bl_options = {"REGISTER"}

    def execute(self, context):
        pc = context.scene.rat1_path
        pc.show_path_viz = not pc.show_path_viz
        if pc.show_path_viz:
            _ensure_draw_handler()
        else:
            _maybe_remove_draw_handler(pc)
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
        return {"FINISHED"}


class RAT1PR_OT_RemoveLast(Operator):
    bl_idname  = "rat1pr.remove_last"
    bl_label   = "Eliminar ultimo punto"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        pc = context.scene.rat1_path
        if len(pc.path_points) > 0:
            pc.path_points.remove(len(pc.path_points) - 1)
        sync_paradas_frames(pc)
        sync_walk_styles(pc)
        return {"FINISHED"}


class RAT1PR_OT_RemovePoint(Operator):
    bl_idname  = "rat1pr.remove_point"
    bl_label   = "Eliminar coordenada"
    bl_description = "Quita esta coordenada de la lista del recorrido"
    bl_options = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty(default=0)

    def execute(self, context):
        pc = context.scene.rat1_path
        if 0 <= self.index < len(pc.path_points):
            pc.path_points.remove(self.index)
        sync_paradas_frames(pc)
        sync_walk_styles(pc)
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
        return {"FINISHED"}


class RAT1PR_OT_ClearPath(Operator):
    bl_idname  = "rat1pr.clear_path"
    bl_label   = "Limpiar recorrido"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        pc = context.scene.rat1_path
        pc.path_points.clear()
        sync_paradas_frames(pc)
        sync_walk_styles(pc)
        return {"FINISHED"}


class RAT1PR_OT_SyncParadasFrames(Operator):
    bl_idname  = "rat1pr.sync_paradas_frames"
    bl_label   = "Sincronizar frames por parada"
    bl_description = "Ajusta la lista de frames por parada y estilos de caminata a lo detectado en el recorrido actual"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        pc = context.scene.rat1_path
        n = sync_paradas_frames(pc)
        n_walk = sync_walk_styles(pc)
        self.report({"INFO"}, f"Sincronizado: {n} parada(s) y {n_walk} tramo(s) de caminata detectado(s)")
        return {"FINISHED"}


class RAT1PR_OT_OpenBlendFile(Operator):
    bl_idname  = "rat1pr.open_blend"
    bl_label   = "Seleccionar .blend"
    bl_options = {"REGISTER"}
    filepath: StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        context.scene.rat1_path.blend_filepath = self.filepath
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


# =============================================================================
# CARGA DE PERSONAJE (simplificada: rat_1 solo tiene 3 objetos)
# =============================================================================

def _load_character(context, blend_path):
    """Aparece rat_1/body1_1/Mesh_0_1 desde blend_path si no estan ya en
    la escena. Mucho mas simple que _load_character() en Alfred (que
    maneja ~15 objetos, armature secundaria del arco, herramientas,
    etc.) porque rat_1 todavia no tiene accesorios."""
    missing = [n for n in ALL_OBJECTS if bpy.data.objects.get(n) is None]
    if missing:
        if not blend_path or not os.path.isfile(blend_path):
            return False
        try:
            with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
                data_to.objects = [n for n in ALL_OBJECTS if n in data_from.objects]
        except Exception as e:
            print(f"  _load_character: error al abrir '{blend_path}': {e}")
            return False
        for obj in data_to.objects:
            if obj is not None and obj.name not in context.scene.objects:
                context.scene.collection.objects.link(obj)

    root = bpy.data.objects.get(ROOT_NAME)
    arm  = bpy.data.objects.get(ARM_NAME)
    mesh = bpy.data.objects.get(MESH_NAME)

    if arm and root and arm.parent != root:
        arm.parent = root
        arm.matrix_parent_inverse.identity()
    if mesh and arm and mesh.parent != arm:
        mesh.parent = arm
        mesh.matrix_parent_inverse.identity()

    for name in ALL_OBJECTS:
        obj = bpy.data.objects.get(name)
        if obj:
            obj.hide_viewport = False
            obj.hide_render   = False

    if arm:
        try:
            context.scene.rat1st.armature_name = arm.name
        except Exception as e:
            print(f"  _load_character: no se pudo setear armature_name: {e}")

    root_ok = bpy.data.objects.get(ROOT_NAME) is not None
    print(f"  _load_character: {'OK' if root_ok else 'ERROR — rat_1 no encontrado'}")
    return root_ok


# =============================================================================
# PREVIEW PATH — Reproducir recorrido en viewport (PLACEHOLDER root-only)
# =============================================================================

class RAT1PR_OT_PreviewPath(Operator):
    """Reproduce el recorrido de rat_1 en el viewport, incluyendo la
    biomecanica cuadrupeda de los 22 bones (trote diagonal en caminar,
    poses clave de agazapamiento/despegue/vuelo/aterrizaje en los
    saltos). Las formulas deben coincidir con generate_slots_rat_1.py
    (mismo patron que Alfred entre su preview y su exportador de slots).
    """
    bl_idname  = "rat1pr.preview_path"
    bl_label   = "Reproducir recorrido"
    bl_description = "Anima rat_1 (EMPTY raiz + 22 bones del armature) a lo largo del recorrido grabado"
    bl_options = {"REGISTER"}

    # ── Amplitudes biomecanicas (radianes) -- deben coincidir con
    # BIO_CAMINAR en generate_slots_rat_1.py ──────────────────────────
    FRONT_LEG_SWING = math.radians(30)
    HIND_LEG_SWING  = math.radians(48)
    FRONT_PAW_FLEX  = math.radians(30)
    HIND_PAW_FLEX   = math.radians(42)
    SPINE_BOUNCE    = math.radians(7.0)
    SPINE_LATERAL   = math.radians(4.0)
    NECK_COUNTER    = 0.45
    HEAD_COUNTER    = 0.60
    TAIL1_LATERAL   = math.radians(9.0)
    TAIL2_LATERAL   = math.radians(15.0)
    TAIL_VERTICAL   = math.radians(7.0)
    TAIL_LAG        = 0.15
    TAIL2_WHIP_MULT = 1.6

    def _kfb(self, obj, frame):
        obj.keyframe_insert(data_path="location", frame=frame)
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)

    def _kf_bone(self, pbones, name, rot_xyz, frame):
        pb = pbones.get(name) if pbones else None
        if pb is None:
            return
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = rot_xyz
        pb.keyframe_insert(data_path="rotation_euler", frame=frame)

    @staticmethod
    def _ease_in_out_sine(t):
        return -(math.cos(math.pi * t) - 1) / 2

    @classmethod
    def _keyed(cls, t, keys):
        if t <= keys[0][0]:
            return keys[0][1]
        if t >= keys[-1][0]:
            return keys[-1][1]
        for i in range(len(keys) - 1):
            t0, v0 = keys[i]
            t1, v1 = keys[i + 1]
            if t0 <= t <= t1:
                span = max(t1 - t0, 1e-6)
                return v0 + (v1 - v0) * cls._ease_in_out_sine((t - t0) / span)
        return keys[-1][1]

    @classmethod
    def _env(cls, t, in_frac=0.15, out_frac=0.15):
        """Envolvente de entrada/salida suave (evita 'pop' al inicio/fin
        de una pose sostenida). Debe coincidir con _env() embebido via
        _SHARED_HELPERS en generate_slots_rat_1.py."""
        if in_frac > 0 and t < in_frac:
            return cls._ease_in_out_sine(t / in_frac)
        if out_frac > 0 and t > 1.0 - out_frac:
            return cls._ease_in_out_sine((1.0 - t) / out_frac)
        return 1.0

    @staticmethod
    def _calc_leg_swing(phase, amp):
        return amp * math.sin(phase * 2 * math.pi)

    @staticmethod
    def _calc_paw_flex(phase, amp):
        return amp * max(0.0, math.sin((phase - 0.75) * 2 * math.pi))

    def _bones_caminar(self, pbones, frame, walk_cycle):
        """Trote diagonal: RF+LH en fase, LF+RH en fase+0.5. Debe
        coincidir con execute_animation() en generate_caminar()."""
        phase_a = walk_cycle % 1.0
        phase_b = (walk_cycle + 0.5) % 1.0

        rf_swing = self._calc_leg_swing(phase_a, self.FRONT_LEG_SWING)
        lf_swing = self._calc_leg_swing(phase_b, self.FRONT_LEG_SWING)
        lh_swing = self._calc_leg_swing(phase_a, self.HIND_LEG_SWING)
        rh_swing = self._calc_leg_swing(phase_b, self.HIND_LEG_SWING)

        self._kf_bone(pbones, "rightArm_1",   (rf_swing, 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftArm_1",    (lf_swing, 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftThigh_1",  (lh_swing, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightThigh_1", (rh_swing, 0.0, 0.0), frame)

        self._kf_bone(pbones, "rightHand_1", (self._calc_paw_flex(phase_a, self.FRONT_PAW_FLEX), 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftHand_1",  (self._calc_paw_flex(phase_b, self.FRONT_PAW_FLEX), 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftFoot_1",  (self._calc_paw_flex(phase_a, self.HIND_PAW_FLEX), 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightFoot_1", (self._calc_paw_flex(phase_b, self.HIND_PAW_FLEX), 0.0, 0.0), frame)

        spine_x = -self.SPINE_BOUNCE * math.cos(walk_cycle * 4 * math.pi)
        spine_z = self.SPINE_LATERAL * math.sin(walk_cycle * 2 * math.pi)
        self._kf_bone(pbones, "body2_1", (spine_x, 0.0, spine_z), frame)
        self._kf_bone(pbones, "body1_1", (0.0, 0.0, 0.0), frame)
        self._kf_bone(pbones, "neck_1", (-spine_x * self.NECK_COUNTER, 0.0, -spine_z * 0.3), frame)
        self._kf_bone(pbones, "head_1", (-spine_x * self.NECK_COUNTER * self.HEAD_COUNTER, 0.0, 0.0), frame)

        tail_cycle = walk_cycle - self.TAIL_LAG
        tail_z = -self.TAIL1_LATERAL * math.sin(tail_cycle * 2 * math.pi)
        tail2_z = -self.TAIL2_LATERAL * math.sin(tail_cycle * 2 * math.pi)
        tail_x = self.TAIL_VERTICAL * math.cos(tail_cycle * 4 * math.pi)
        self._kf_bone(pbones, "tail1_1", (tail_x, 0.0, tail_z), frame)
        self._kf_bone(pbones, "tail2_1", (tail_x * 1.3, 0.0, tail2_z), frame)

    # ── Poses clave (radianes) de los saltos -- deben coincidir con
    # generate_saltar_subir()/generate_saltar_bajar() ────────────────
    _KEYS_SUBIR_HIND_SWING  = [(0.0, 0.0), (0.28, math.radians(35)),  (0.62, math.radians(-55)), (0.85, math.radians(25)), (1.0, math.radians(-8))]
    _KEYS_SUBIR_HIND_PAW    = [(0.0, 0.0), (0.28, math.radians(45)),  (0.62, math.radians(-10)), (0.85, math.radians(35)), (1.0, math.radians(10))]
    _KEYS_SUBIR_FRONT_SWING = [(0.0, 0.0), (0.28, math.radians(15)),  (0.62, math.radians(-20)), (0.85, math.radians(30)), (1.0, math.radians(50))]
    _KEYS_SUBIR_FRONT_PAW   = [(0.0, 0.0), (0.28, math.radians(30)),  (0.62, math.radians(10)),  (0.85, math.radians(-15)), (1.0, math.radians(-30))]
    _KEYS_SUBIR_SPINE_X     = [(0.0, 0.0), (0.28, math.radians(-8)),  (0.62, math.radians(10)),  (0.85, math.radians(-5)), (1.0, math.radians(6))]
    _KEYS_SUBIR_TAIL_X      = [(0.0, 0.0), (0.28, math.radians(-10)), (0.62, math.radians(28)),  (0.85, math.radians(5)), (1.0, math.radians(-5))]

    _KEYS_BAJAR_FRONT_SWING = [(0.0, 0.0), (0.5, math.radians(45)),  (0.75, math.radians(30)), (0.9, math.radians(5)),   (1.0, 0.0)]
    _KEYS_BAJAR_FRONT_PAW   = [(0.0, 0.0), (0.5, math.radians(-20)), (0.75, math.radians(35)), (0.9, math.radians(50)),  (1.0, math.radians(10))]
    _KEYS_BAJAR_HIND_SWING  = [(0.0, 0.0), (0.5, math.radians(-35)), (0.75, math.radians(-15)),(0.9, math.radians(30)),  (1.0, math.radians(5))]
    _KEYS_BAJAR_HIND_PAW    = [(0.0, 0.0), (0.5, math.radians(-10)), (0.75, math.radians(15)), (0.9, math.radians(48)),  (1.0, math.radians(12))]
    _KEYS_BAJAR_SPINE_X     = [(0.0, 0.0), (0.5, math.radians(8)),   (0.75, math.radians(-4)), (0.9, math.radians(-14)), (1.0, math.radians(-3))]
    _KEYS_BAJAR_TAIL_X      = [(0.0, 0.0), (0.5, math.radians(20)),  (0.75, math.radians(-8)), (0.9, math.radians(-22)), (1.0, math.radians(-4))]

    def _bones_salto(self, pbones, frame, t, subir):
        """Agazapamiento/despegue/vuelo/aterrizaje (subir) o
        caida/impacto/absorcion/asentamiento (bajar). Debe coincidir con
        execute_animation() en generate_saltar_subir()/generate_saltar_bajar()."""
        if subir:
            hind_swing  = self._keyed(t, self._KEYS_SUBIR_HIND_SWING)
            front_swing = self._keyed(t, self._KEYS_SUBIR_FRONT_SWING)
            hind_paw    = self._keyed(t, self._KEYS_SUBIR_HIND_PAW)
            front_paw   = self._keyed(t, self._KEYS_SUBIR_FRONT_PAW)
            spine_x     = self._keyed(t, self._KEYS_SUBIR_SPINE_X)
            tail_x      = self._keyed(t, self._KEYS_SUBIR_TAIL_X)
        else:
            hind_swing  = self._keyed(t, self._KEYS_BAJAR_HIND_SWING)
            front_swing = self._keyed(t, self._KEYS_BAJAR_FRONT_SWING)
            hind_paw    = self._keyed(t, self._KEYS_BAJAR_HIND_PAW)
            front_paw   = self._keyed(t, self._KEYS_BAJAR_FRONT_PAW)
            spine_x     = self._keyed(t, self._KEYS_BAJAR_SPINE_X)
            tail_x      = self._keyed(t, self._KEYS_BAJAR_TAIL_X)

        self._kf_bone(pbones, "leftThigh_1",  (hind_swing, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightThigh_1", (hind_swing, 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftFoot_1",   (hind_paw, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightFoot_1",  (hind_paw, 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftArm_1",    (front_swing, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightArm_1",   (front_swing, 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftHand_1",   (front_paw, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightHand_1",  (front_paw, 0.0, 0.0), frame)

        self._kf_bone(pbones, "body2_1", (spine_x, 0.0, 0.0), frame)
        self._kf_bone(pbones, "body1_1", (0.0, 0.0, 0.0), frame)
        self._kf_bone(pbones, "neck_1", (-spine_x * self.NECK_COUNTER, 0.0, 0.0), frame)
        self._kf_bone(pbones, "head_1", (-spine_x * self.NECK_COUNTER * self.HEAD_COUNTER, 0.0, 0.0), frame)

        self._kf_bone(pbones, "tail1_1", (tail_x, 0.0, 0.0), frame)
        self._kf_bone(pbones, "tail2_1", (tail_x * self.TAIL2_WHIP_MULT, 0.0, 0.0), frame)

    # ── Acciones puntuales de rata (Kebyn, 2026-09-03/04) -- 100% procedural,
    # sin mocap, mismo criterio que caminar/saltos. Deben coincidir con
    # execute_animation() en generate_pararse_dos_patas()/generate_olfatear()/
    # generate_escarbar()/generate_roer() de generate_slots_rat_1.py.
    # NOTA: signos/amplitudes son punto de partida razonable, igual que el
    # resto de la biomecanica de este port -- pendiente de validar en
    # Blender real (ver PORT_NOTES.md).
    #
    # FIX (Kebyn, 2026-09-04): en la version original, body2_1 con signo
    # negativo (-70 grados) hundia a la rata en el suelo en vez de
    # levantarla -- la convencion real del rig es la INVERSA a la
    # supuesta: X POSITIVO en body2_1 = columna se yergue/levanta,
    # X NEGATIVO = columna se inclina hacia el suelo. Se invirtio el
    # signo de columna/cuello/cabeza de pararse_dos_patas (las 3 unicas
    # poses cuyo problema era "levantarse"; olfatear/escarbar/roer usan
    # el signo negativo para AGACHARSE, que con esta misma convencion ya
    # apunta en la direccion correcta -- no se tocaron).
    _KEYS_PARARSE_SPINE = [(0.0, 0.0), (0.30, math.radians(70)),  (0.55, math.radians(70)),  (0.85, math.radians(70)),  (1.0, 0.0)]
    _KEYS_PARARSE_NECK  = [(0.0, 0.0), (0.30, math.radians(-20)), (0.55, math.radians(-20)), (0.85, math.radians(-20)), (1.0, 0.0)]
    _KEYS_PARARSE_HEAD  = [(0.0, 0.0), (0.30, math.radians(-12)), (0.55, math.radians(-12)), (0.85, math.radians(-12)), (1.0, 0.0)]
    _KEYS_PARARSE_ARM   = [(0.0, 0.0), (0.30, math.radians(90)),  (0.55, math.radians(90)),  (0.85, math.radians(90)),  (1.0, 0.0)]
    _KEYS_PARARSE_HAND  = [(0.0, 0.0), (0.30, math.radians(-35)), (0.55, math.radians(-35)), (0.85, math.radians(-35)), (1.0, 0.0)]
    _KEYS_PARARSE_THIGH = [(0.0, 0.0), (0.30, math.radians(-12)), (0.55, math.radians(-12)), (0.85, math.radians(-12)), (1.0, 0.0)]
    _KEYS_PARARSE_FOOT  = [(0.0, 0.0), (0.30, math.radians(8)),   (0.55, math.radians(8)),   (0.85, math.radians(8)),   (1.0, 0.0)]
    _KEYS_PARARSE_TAIL1 = [(0.0, 0.0), (0.30, math.radians(18)),  (0.55, math.radians(18)),  (0.85, math.radians(18)),  (1.0, 0.0)]
    _KEYS_PARARSE_TAIL2 = [(0.0, 0.0), (0.30, math.radians(26)),  (0.55, math.radians(26)),  (0.85, math.radians(26)),  (1.0, 0.0)]
    # Bones faciales (Kebyn, 2026-09-04): orejas erguidas/alerta y
    # bigotes en abanico hacia adelante mientras esta parada vigilando,
    # con la misma envolvente subir/hold/bajar que el resto de la pose.
    _KEYS_PARARSE_EAR      = [(0.0, 0.0), (0.30, math.radians(25)), (0.55, math.radians(25)), (0.85, math.radians(25)), (1.0, 0.0)]
    _KEYS_PARARSE_WHISKER  = [(0.0, 0.0), (0.30, math.radians(15)), (0.55, math.radians(15)), (0.85, math.radians(15)), (1.0, 0.0)]
    PARARSE_NOSE_AMP    = math.radians(10)
    PARARSE_NOSE_CYCLES = 6

    def _bones_pararse_dos_patas(self, pbones, frame, t):
        """Se yergue sobre las patas traseras: columna se endereza,
        patas delanteras se pliegan contra el pecho, cola apoya atras
        como contrapeso, luego vuelve a 4 patas. Orejas erguidas y
        bigotes en abanico (postura de alerta/vigilancia), nariz
        olfatea el aire mientras esta arriba."""
        self._kf_bone(pbones, "body2_1", (self._keyed(t, self._KEYS_PARARSE_SPINE), 0.0, 0.0), frame)
        self._kf_bone(pbones, "body1_1", (0.0, 0.0, 0.0), frame)
        self._kf_bone(pbones, "neck_1", (self._keyed(t, self._KEYS_PARARSE_NECK), 0.0, 0.0), frame)
        self._kf_bone(pbones, "head_1", (self._keyed(t, self._KEYS_PARARSE_HEAD), 0.0, 0.0), frame)
        arm_x = self._keyed(t, self._KEYS_PARARSE_ARM)
        hand_x = self._keyed(t, self._KEYS_PARARSE_HAND)
        self._kf_bone(pbones, "leftArm_1", (arm_x, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightArm_1", (arm_x, 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftHand_1", (hand_x, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightHand_1", (hand_x, 0.0, 0.0), frame)
        thigh_x = self._keyed(t, self._KEYS_PARARSE_THIGH)
        foot_x = self._keyed(t, self._KEYS_PARARSE_FOOT)
        self._kf_bone(pbones, "leftThigh_1", (thigh_x, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightThigh_1", (thigh_x, 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftFoot_1", (foot_x, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightFoot_1", (foot_x, 0.0, 0.0), frame)
        self._kf_bone(pbones, "tail1_1", (self._keyed(t, self._KEYS_PARARSE_TAIL1), 0.0, 0.0), frame)
        self._kf_bone(pbones, "tail2_1", (self._keyed(t, self._KEYS_PARARSE_TAIL2), 0.0, 0.0), frame)
        ear_x = self._keyed(t, self._KEYS_PARARSE_EAR)
        whisker_x = self._keyed(t, self._KEYS_PARARSE_WHISKER)
        self._kf_bone(pbones, "leftEar_1", (ear_x, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightEar_1", (ear_x, 0.0, 0.0), frame)
        self._kf_bone(pbones, "wisker1_1", (whisker_x, 0.0, 0.0), frame)
        self._kf_bone(pbones, "wisker2_1", (whisker_x, 0.0, 0.0), frame)
        _hold_env = self._keyed(t, [(0.0, 0.0), (0.30, 1.0), (0.85, 1.0), (1.0, 0.0)])
        nose_x = self.PARARSE_NOSE_AMP * max(0.0, math.sin(t * self.PARARSE_NOSE_CYCLES * 2 * math.pi)) * _hold_env
        self._kf_bone(pbones, "nose_1", (nose_x, 0.0, 0.0), frame)

    OLFATEAR_CYCLES = 4
    OLFATEAR_HEAD_AMP = math.radians(22)
    OLFATEAR_NECK_AMP = math.radians(14)
    OLFATEAR_CROUCH = math.radians(-10)
    OLFATEAR_ARM_CROUCH = math.radians(-8)
    OLFATEAR_TAIL_SWAY = math.radians(6)
    OLFATEAR_EAR_AMP = math.radians(15)
    OLFATEAR_NOSE_AMP = math.radians(18)
    OLFATEAR_WHISKER_AMP = math.radians(20)

    def _bones_olfatear(self, pbones, frame, t):
        """Olfatea: agachado leve y constante (envolvente), con
        rapidos 'dips' de cabeza/cuello siguiendo un ritmo de olfateo
        (mitad positiva de un seno, no un vaiven simetrico), y la cola
        con un balanceo lento independiente. Nariz y bigotes tiemblan
        al DOBLE de frecuencia que la cabeza (el detalle real del
        olfateo), orejas atentas hacia adelante."""
        env = self._env(t)
        raw = math.sin(t * self.OLFATEAR_CYCLES * 2 * math.pi)
        dip = max(0.0, raw) ** 0.6
        raw2 = math.sin(t * self.OLFATEAR_CYCLES * 4 * math.pi)
        dip2 = max(0.0, raw2) ** 0.5
        self._kf_bone(pbones, "body2_1", (self.OLFATEAR_CROUCH * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "body1_1", (0.0, 0.0, 0.0), frame)
        self._kf_bone(pbones, "neck_1", (-self.OLFATEAR_NECK_AMP * dip * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "head_1", (-self.OLFATEAR_HEAD_AMP * dip * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftArm_1", (self.OLFATEAR_ARM_CROUCH * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightArm_1", (self.OLFATEAR_ARM_CROUCH * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftHand_1", (0.0, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightHand_1", (0.0, 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftThigh_1", (0.0, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightThigh_1", (0.0, 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftFoot_1", (0.0, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightFoot_1", (0.0, 0.0, 0.0), frame)
        tail_z = self.OLFATEAR_TAIL_SWAY * math.sin(t * 2 * math.pi) * env
        self._kf_bone(pbones, "tail1_1", (0.0, 0.0, tail_z), frame)
        self._kf_bone(pbones, "tail2_1", (0.0, 0.0, tail_z * 1.3), frame)
        self._kf_bone(pbones, "leftEar_1", (self.OLFATEAR_EAR_AMP * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightEar_1", (self.OLFATEAR_EAR_AMP * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "nose_1", (self.OLFATEAR_NOSE_AMP * dip2 * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "wisker1_1", (self.OLFATEAR_WHISKER_AMP * dip2 * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "wisker2_1", (self.OLFATEAR_WHISKER_AMP * dip2 * env, 0.0, 0.0), frame)

    ESCARBAR_CYCLES = 4
    ESCARBAR_CROUCH = math.radians(-25)
    ESCARBAR_HEAD_DOWN = math.radians(15)
    ESCARBAR_NECK_DOWN = math.radians(10)
    ESCARBAR_ARM_SWING = math.radians(40)
    ESCARBAR_HAND_FLEX = math.radians(30)
    ESCARBAR_THIGH_BRACE = math.radians(-6)
    ESCARBAR_FOOT_BRACE = math.radians(4)
    ESCARBAR_TAIL_SWAY = math.radians(5)
    ESCARBAR_EAR_AMP = math.radians(-15)
    ESCARBAR_SNOUT_AMP = math.radians(12)
    ESCARBAR_NOSE_AMP = math.radians(14)
    ESCARBAR_WHISKER_AMP = math.radians(16)

    def _bones_escarbar(self, pbones, frame, t):
        """Escarba el suelo con las patas delanteras, alternadas (fuera
        de fase), agachada mirando hacia abajo, patas traseras
        plantadas con leve contra-apoyo. Orejas hacia atras
        (concentracion), hocico/nariz/bigotes tiemblan por el polvo,
        sincronizados con el ciclo de escarbado."""
        env = self._env(t)
        phase_a = (t * self.ESCARBAR_CYCLES) % 1.0
        phase_b = (t * self.ESCARBAR_CYCLES + 0.5) % 1.0
        arm_r = self.ESCARBAR_ARM_SWING * math.sin(phase_a * 2 * math.pi) * env
        arm_l = self.ESCARBAR_ARM_SWING * math.sin(phase_b * 2 * math.pi) * env
        hand_r = self.ESCARBAR_HAND_FLEX * max(0.0, math.sin((phase_a - 0.75) * 2 * math.pi)) * env
        hand_l = self.ESCARBAR_HAND_FLEX * max(0.0, math.sin((phase_b - 0.75) * 2 * math.pi)) * env
        self._kf_bone(pbones, "body2_1", (self.ESCARBAR_CROUCH * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "body1_1", (0.0, 0.0, 0.0), frame)
        self._kf_bone(pbones, "neck_1", (self.ESCARBAR_NECK_DOWN * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "head_1", (self.ESCARBAR_HEAD_DOWN * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightArm_1", (arm_r, 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftArm_1", (arm_l, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightHand_1", (hand_r, 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftHand_1", (hand_l, 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftThigh_1", (self.ESCARBAR_THIGH_BRACE * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightThigh_1", (self.ESCARBAR_THIGH_BRACE * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftFoot_1", (self.ESCARBAR_FOOT_BRACE * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightFoot_1", (self.ESCARBAR_FOOT_BRACE * env, 0.0, 0.0), frame)
        tail_z = self.ESCARBAR_TAIL_SWAY * math.sin(phase_a * 2 * math.pi) * env
        self._kf_bone(pbones, "tail1_1", (0.0, 0.0, tail_z), frame)
        self._kf_bone(pbones, "tail2_1", (0.0, 0.0, tail_z * 1.2), frame)
        self._kf_bone(pbones, "leftEar_1", (self.ESCARBAR_EAR_AMP * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightEar_1", (self.ESCARBAR_EAR_AMP * env, 0.0, 0.0), frame)
        dust = max(0.0, math.sin(phase_a * 2 * math.pi)) ** 0.5
        self._kf_bone(pbones, "snout_1", (self.ESCARBAR_SNOUT_AMP * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "nose_1", (self.ESCARBAR_NOSE_AMP * dust * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "wisker1_1", (self.ESCARBAR_WHISKER_AMP * dust * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "wisker2_1", (self.ESCARBAR_WHISKER_AMP * dust * env, 0.0, 0.0), frame)

    ROER_CYCLES = 8
    ROER_SPINE_SIT = math.radians(-35)
    ROER_THIGH_SIT = math.radians(-20)
    ROER_FOOT_SIT = math.radians(14)
    ROER_ARM_HOLD = math.radians(85)
    ROER_HAND_HOLD = math.radians(-45)
    ROER_HEAD_CHEW_AMP = math.radians(8)
    ROER_NECK_CHEW_AMP = math.radians(4)
    ROER_TAIL_SETTLE = math.radians(6)
    ROER_EAR_AMP = math.radians(12)
    ROER_NOSE_AMP = math.radians(16)
    ROER_WHISKER_AMP = math.radians(18)

    def _bones_roer(self, pbones, frame, t):
        """Se sienta sobre las ancas y sostiene algo con ambas patas
        delanteras cerca del hocico, con un rapido cabeceo de
        masticado. Nariz y bigotes tiemblan exactamente al ritmo del
        masticado, orejas atentas hacia adelante."""
        env = self._env(t)
        chew = math.sin(t * self.ROER_CYCLES * 2 * math.pi)
        self._kf_bone(pbones, "body2_1", (self.ROER_SPINE_SIT * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "body1_1", (0.0, 0.0, 0.0), frame)
        self._kf_bone(pbones, "neck_1", (self.ROER_NECK_CHEW_AMP * chew * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "head_1", (self.ROER_HEAD_CHEW_AMP * chew * env, 0.0, 0.0), frame)
        arm_x = self.ROER_ARM_HOLD * env
        hand_x = self.ROER_HAND_HOLD * env
        self._kf_bone(pbones, "leftArm_1", (arm_x, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightArm_1", (arm_x, 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftHand_1", (hand_x, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightHand_1", (hand_x, 0.0, 0.0), frame)
        thigh_x = self.ROER_THIGH_SIT * env
        foot_x = self.ROER_FOOT_SIT * env
        self._kf_bone(pbones, "leftThigh_1", (thigh_x, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightThigh_1", (thigh_x, 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftFoot_1", (foot_x, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightFoot_1", (foot_x, 0.0, 0.0), frame)
        tail_x = self.ROER_TAIL_SETTLE * env
        self._kf_bone(pbones, "tail1_1", (tail_x, 0.0, 0.0), frame)
        self._kf_bone(pbones, "tail2_1", (tail_x * 1.2, 0.0, 0.0), frame)
        self._kf_bone(pbones, "leftEar_1", (self.ROER_EAR_AMP * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "rightEar_1", (self.ROER_EAR_AMP * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "nose_1", (self.ROER_NOSE_AMP * chew * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "wisker1_1", (self.ROER_WHISKER_AMP * chew * env, 0.0, 0.0), frame)
        self._kf_bone(pbones, "wisker2_1", (self.ROER_WHISKER_AMP * chew * env, 0.0, 0.0), frame)

    @staticmethod
    def _pos_saltar_subir(p0, p1, t):
        dx = p1.x - p0.x; dy = p1.y - p0.y; dz = p1.z - p0.z
        t_s = t * t * (3 - 2 * t)
        dist_xy = math.sqrt(dx * dx + dy * dy)
        H = max(abs(dz) * 0.6, dist_xy * 0.35, 0.25)
        arc = 4 * H * t_s * (1 - t_s)
        return Vector((p0.x + t_s * dx, p0.y + t_s * dy, p0.z + t_s * dz + arc))

    @staticmethod
    def _pos_saltar_bajar(p0, p1, t):
        """Parabola de proyectil (igual criterio que _pos_saltar_subir):
        arco hacia afuera al salir del borde, no caida recta pegada a la
        cara vertical del bloque -- ver calc_root_position() en
        generate_saltar_bajar() de generate_slots_rat_1.py (mismo fix,
        2026-09-03, pedido con referencia grafica)."""
        dx = p1.x - p0.x; dy = p1.y - p0.y; dz = p1.z - p0.z
        t_s = t * t * (3 - 2 * t)
        dist_xy = math.sqrt(dx * dx + dy * dy)
        H = max(abs(dz) * 0.3, dist_xy * 0.3, 0.2)
        arc = 4 * H * t_s * (1 - t_s)
        return Vector((p0.x + t_s * dx, p0.y + t_s * dy, p0.z + t_s * dz + arc))

    def execute(self, context):
        from .generate_slots_rat_1 import (
            WALK_STYLE_PARAMS, FRAMES_PER_UNIT_BASE, FRAMES_PER_BIO_CYCLE_BASE,
            SALTAR_SUBIR_FRAMES, SALTAR_BAJAR_FRAMES, PARADA_FRAMES_DEFAULT,
            TOTAL_FRAMES_PARARSE_DOS_PATAS, TOTAL_FRAMES_OLFATEAR,
            TOTAL_FRAMES_ESCARBAR, TOTAL_FRAMES_ROER,
        )

        pc = context.scene.rat1_path
        pts = list(pc.path_points)
        if len(pts) == 0:
            self.report({"ERROR"}, "Graba al menos 1 punto de recorrido")
            return {"CANCELLED"}

        root = bpy.data.objects.get(ROOT_NAME)
        if root is None:
            blend_path = bpy.path.abspath(pc.blend_filepath) if pc.blend_filepath else ""
            if not blend_path or not os.path.isfile(blend_path):
                self.report({"ERROR"}, f"No se encontro '{ROOT_NAME}' en la escena. Selecciona el .blend en el Paso 1.")
                return {"CANCELLED"}
            if not _load_character(context, blend_path):
                self.report({"ERROR"}, "No se pudo cargar el personaje rat_1.")
                return {"CANCELLED"}
            root = bpy.data.objects.get(ROOT_NAME)

        # Limpiar animacion previa del root y del armature
        if root.animation_data:
            root.animation_data_clear()
        root.rotation_mode = "XYZ"

        arm = bpy.data.objects.get(ARM_NAME)
        pbones = None
        if arm is not None:
            if arm.animation_data:
                arm.animation_data_clear()
            pbones = arm.pose.bones

        root_rot = (pc.root_rot_x, pc.root_rot_y, pc.root_rot_z)

        # ── Modo 1 coordenada: idle ──────────────────────────────────────
        if len(pts) == 1:
            pt = pts[0]
            frame_a = pc.frame_inicio
            frame_b = max(frame_a + 1, pc.frame_fin_manual)
            context.scene.frame_set(frame_a)
            root.location = Vector(pt.coords)
            root.rotation_euler = (math.radians(root_rot[0]), math.radians(root_rot[1]), math.radians(root_rot[2]))
            self._kfb(root, frame_a)
            context.scene.frame_set(frame_b)
            root.location = Vector(pt.coords)
            root.rotation_euler = (math.radians(root_rot[0]), math.radians(root_rot[1]), math.radians(root_rot[2]))
            self._kfb(root, frame_b)
            pc.anim_frame_fin = frame_b
            context.scene.frame_start = frame_a
            context.scene.frame_end   = frame_b
            self.report({"INFO"}, f"Preview OK (idle): frames {frame_a}→{frame_b}")
            return {"FINISHED"}

        # ── Modo recorrido (>1 coordenada) ───────────────────────────────
        expanded_pts, frames_paradas_marcadas = _expand_points_with_paradas(pts)
        segs = _group_segments(expanded_pts)
        sync_paradas_frames(pc)
        sync_walk_styles(pc)

        frame = pc.frame_inicio
        prev_rot_z = math.radians(root_rot[2])
        parada_idx = 0
        caminar_idx = 0

        # Punto de partida
        context.scene.frame_set(frame)
        root.location = Vector(segs[0]["points"][0].coords)
        root.rotation_euler = (math.radians(root_rot[0]), math.radians(root_rot[1]), prev_rot_z)
        self._kfb(root, frame)

        for seg in segs:
            seg_type = seg["type"]
            seg_pts  = seg["points"]
            p_start  = Vector(seg_pts[0].coords)
            p_end    = Vector(seg_pts[-1].coords)

            dx = p_end.x - p_start.x
            dy = p_end.y - p_start.y
            # PORTADO (Kebyn, 2026-09-03): antes rot_z se calculaba con
            # atan2 crudo (angulo "sucio" en diagonales). Ahora se snapea
            # a cardinal/diagonal -- mismo criterio que
            # _compute_direction_angle_local() en generate_slots_rat_1.py
            # / generate_slots_alfred.py -- para que el heading heredado
            # entre tramos (prev_rot_z) sea siempre un valor limpio.
            rot_z_deg = _snap_direction_angle(dx, dy, math.degrees(prev_rot_z))
            rot_z = math.radians(rot_z_deg)

            if seg_type == "caminar":
                style_key = (pc.walk_styles[caminar_idx].style
                             if caminar_idx < len(pc.walk_styles) else pc.walk_style)
                style = WALK_STYLE_PARAMS.get(style_key, WALK_STYLE_PARAMS["NORMAL"])

                # Puntos reales del tramo (>=2, puede tener varios si el
                # recorrido tiene varias coordenadas 'caminar' seguidas)
                seg_coords = [Vector(p.coords) for p in seg_pts]

                frames_per_unit = FRAMES_PER_UNIT_BASE * style["speed_mult"]
                frames_per_bio_cycle = FRAMES_PER_BIO_CYCLE_BASE * style["cycle_mult"]
                half_cycle = frames_per_bio_cycle / 2.0

                dist_total = sum((seg_coords[i + 1] - seg_coords[i]).length
                                 for i in range(len(seg_coords) - 1))
                dist_total = max(dist_total, 0.0001)
                raw_frames = dist_total * frames_per_unit
                n_half = max(1, round(raw_frames / half_cycle))
                n_frames = max(2, round(n_half * half_cycle))
                walk_cycles = n_frames / frames_per_bio_cycle
                frame_end = frame + n_frames - 1

                # PORTADO (Kebyn, 2026-09-03): suavizador de orientacion
                # fresco por tramo 'caminar' -- mismo criterio que el
                # RotationSmoother(smoothing_frames=12) que usa
                # generate_caminar() en generate_slots_rat_1.py / Alfred.
                # Sin esto, el giro entre dos sub-puntos con angulos
                # distintos (ej. tramo recto -> diagonal) se aplicaba de
                # golpe en vez de progresivamente.
                _smoother = _RotationSmoother(smoothing_frames=12)
                _last_walk_rz = rot_z  # fallback si n_frames==0 (no deberia pasar)

                for rf in range(n_frames):
                    f = frame + rf
                    s = rf / max(n_frames - 1, 1)
                    # Posicion sobre la polilinea del tramo, proporcional
                    # a la distancia recorrida (velocidad constante dentro del
                    # tramo -- simplificacion razonable frente al reparto por
                    # sub-segmento que usa Alfred).
                    target = s * dist_total
                    acc = 0.0
                    pos = seg_coords[-1]
                    seg_ang_deg = rot_z_deg
                    for i in range(len(seg_coords) - 1):
                        L = (seg_coords[i + 1] - seg_coords[i]).length
                        if target <= acc + L or i == len(seg_coords) - 2:
                            lt = 0.0 if L < 1e-9 else max(0.0, min(1.0, (target - acc) / L))
                            pos = seg_coords[i].lerp(seg_coords[i + 1], lt)
                            ddx = seg_coords[i + 1].x - seg_coords[i].x
                            ddy = seg_coords[i + 1].y - seg_coords[i].y
                            seg_ang_deg = _snap_direction_angle(ddx, ddy, rot_z_deg)
                            break
                        acc += L

                    smoothed_deg = _smoother.smooth_rotation(seg_ang_deg, rf)
                    rz_local = math.radians(smoothed_deg)
                    _last_walk_rz = rz_local

                    context.scene.frame_set(f)
                    root.location = pos
                    root.rotation_euler = (math.radians(root_rot[0]), math.radians(root_rot[1]), rz_local)
                    self._kfb(root, f)

                    walk_cycle = s * walk_cycles
                    self._bones_caminar(pbones, f, walk_cycle)

                # FIX (2026-09-03): el heading que se hereda hacia el tramo
                # siguiente (prev_rot_z, asignado mas abajo desde `rot_z`)
                # NO debe ser el rumbo "global" del grupo caminar completo
                # (rot_z_deg, calculado de punta a punta del grupo) sino el
                # rumbo REAL con el que quedo mirando la rata en su ULTIMO
                # frame (_last_walk_rz, ya suavizado). Si el recorrido de
                # caminar tiene varios sub-tramos con giros (ej. un pasillo
                # en zigzag antes de un salto_bajar), el rumbo global
                # punta-a-punta puede ser muy distinto del rumbo del ultimo
                # tramo -- eso hacia que el salto siguiente arrancara su
                # curva-S de rotacion desde un heading "fantasma" y el
                # personaje giraba casi 360 grados (dando la vuelta larga)
                # para llegar al rumbo correcto antes de saltar.
                rot_z = _last_walk_rz

                caminar_idx += 1

            elif seg_type in ("saltar_subir", "saltar_bajar"):
                subir = (seg_type == "saltar_subir")
                n_frames = SALTAR_SUBIR_FRAMES if subir else SALTAR_BAJAR_FRAMES
                frame_end = frame + n_frames - 1

                # PORTADO (Kebyn, 2026-09-03): antes el salto mantenia
                # rot_z fijo durante todos sus frames. Ahora gira en
                # curva S desde el heading heredado (prev_rot_z, en
                # grados) hacia el rumbo real y snapeado del salto
                # (rot_z_deg) en los primeros frames -- mismo criterio
                # que _build_rotation_data() en generate_slots_alfred.py
                # (smoothing = 8 frames, portado a generate_saltar_subir/
                # generate_saltar_bajar en generate_slots_rat_1.py).
                _base_deg = math.degrees(prev_rot_z)
                _rot_smoothing_frames = min(8, max(1, n_frames - 1))

                for rf in range(n_frames):
                    f = frame + rf
                    t = rf / max(n_frames - 1, 1)
                    pos = (self._pos_saltar_subir(p_start, p_end, t) if subir
                           else self._pos_saltar_bajar(p_start, p_end, t))

                    if abs(rot_z_deg - _base_deg) < 0.1:
                        smoothed_deg = rot_z_deg
                    else:
                        progress = min(rf / _rot_smoothing_frames, 1.0)
                        eased = progress * progress * (3.0 - 2.0 * progress)
                        diff = rot_z_deg - _base_deg
                        while diff > 180: diff -= 360
                        while diff < -180: diff += 360
                        smoothed_deg = _base_deg + diff * eased
                    rz_jump = math.radians(smoothed_deg)

                    context.scene.frame_set(f)
                    root.location = pos
                    root.rotation_euler = (math.radians(root_rot[0]), math.radians(root_rot[1]), rz_jump)
                    self._kfb(root, f)
                    self._bones_salto(pbones, f, t, subir)

            elif seg_type in ("pararse_dos_patas", "olfatear", "escarbar", "roer"):
                # Acciones puntuales de rata (Kebyn, 2026-09-03): mismo
                # principio que golpe_estomago_1 en Alfred -- root FIJO en
                # p_start durante todo el slot (el desplazamiento real, si
                # lo hay, lo hace el tramo 'caminar' que sigue), rotando
                # hacia p_end con la misma curva-S de orientacion que usan
                # los saltos.
                _ACTION_FRAMES = {
                    "pararse_dos_patas": TOTAL_FRAMES_PARARSE_DOS_PATAS,
                    "olfatear": TOTAL_FRAMES_OLFATEAR,
                    "escarbar": TOTAL_FRAMES_ESCARBAR,
                    "roer": TOTAL_FRAMES_ROER,
                }
                _ACTION_BONES = {
                    "pararse_dos_patas": self._bones_pararse_dos_patas,
                    "olfatear": self._bones_olfatear,
                    "escarbar": self._bones_escarbar,
                    "roer": self._bones_roer,
                }
                n_frames = _ACTION_FRAMES[seg_type]
                frame_end = frame + n_frames - 1
                _bones_fn = _ACTION_BONES[seg_type]

                _base_deg = math.degrees(prev_rot_z)
                # Kebyn (2026-09-04): es un raton en estado de alerta --
                # smoothing mas corto (5 en vez de 8) para que gire hacia
                # la nueva orientacion mas rapido, reflejo de roedor.
                _rot_smoothing_frames = min(5, max(1, n_frames - 1))

                for rf in range(n_frames):
                    f = frame + rf
                    t = rf / max(n_frames - 1, 1)

                    if abs(rot_z_deg - _base_deg) < 0.1:
                        smoothed_deg = rot_z_deg
                    else:
                        progress = min(rf / _rot_smoothing_frames, 1.0)
                        eased = progress * progress * (3.0 - 2.0 * progress)
                        diff = rot_z_deg - _base_deg
                        while diff > 180: diff -= 360
                        while diff < -180: diff += 360
                        smoothed_deg = _base_deg + diff * eased
                    rz_action = math.radians(smoothed_deg)

                    context.scene.frame_set(f)
                    root.location = p_start
                    root.rotation_euler = (math.radians(root_rot[0]), math.radians(root_rot[1]), rz_action)
                    self._kfb(root, f)
                    _bones_fn(pbones, f, t)

            else:  # parada
                if parada_idx < len(frames_paradas_marcadas):
                    n_frames = frames_paradas_marcadas[parada_idx]
                elif parada_idx < len(pc.paradas_frames):
                    n_frames = pc.paradas_frames[parada_idx].frames
                else:
                    n_frames = pc.frames_parada or PARADA_FRAMES_DEFAULT
                frame_end = frame + max(1, n_frames) - 1
                context.scene.frame_set(frame_end)
                root.location = p_start
                root.rotation_euler = (math.radians(root_rot[0]), math.radians(root_rot[1]), prev_rot_z)
                self._kfb(root, frame_end)
                parada_idx += 1

            prev_rot_z = rot_z
            frame = frame_end + 1

        pc.anim_frame_fin = frame - 1
        context.scene.frame_start = pc.frame_inicio
        context.scene.frame_end   = pc.anim_frame_fin
        context.scene.frame_set(pc.frame_inicio)

        total_f = pc.anim_frame_fin - pc.frame_inicio + 1
        self.report({"INFO"}, f"Preview OK: {len(segs)} tramo(s) | frames {pc.frame_inicio}→{pc.anim_frame_fin} ({total_f} f) — biomecanica cuadrupeda de rat_1")
        return {"FINISHED"}


class RAT1PR_OT_ResetPreview(Operator):
    bl_idname  = "rat1pr.reset_preview"
    bl_label   = "Reset recorrido"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_cancel(restore_frame=True)
        root = bpy.data.objects.get(ROOT_NAME)
        if root:
            if root.animation_data:
                root.animation_data_clear()
            root.location = (0, 0, 0)
            root.rotation_euler = (0, 0, 0)
        self.report({"INFO"}, "Preview reseteada")
        return {"FINISHED"}


class RAT1PR_OT_SetAnimRange(Operator):
    bl_idname  = "rat1pr.set_anim_range"
    bl_label   = "Fijar rango de animacion"
    bl_options = {"REGISTER", "UNDO"}

    frame_fin: bpy.props.IntProperty(name="Frame fin de animacion", default=1, min=1, soft_max=99999)

    def invoke(self, context, event):
        pc = context.scene.rat1_path
        self.frame_fin = pc.anim_frame_fin if pc.anim_frame_fin > 0 else context.scene.frame_end
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        pc = context.scene.rat1_path
        if self.frame_fin <= pc.frame_inicio:
            self.report({"ERROR"}, "Frame fin debe ser mayor que frame inicio")
            return {"CANCELLED"}
        pc.anim_frame_fin = self.frame_fin
        self.report({"INFO"}, f"Rango animacion: {pc.frame_inicio} → {self.frame_fin}")
        return {"FINISHED"}


# =============================================================================
# EXPORT SLOTS (Paso 2) — escribe slot_NNN_rat_1_*.py placeholders a disco
# =============================================================================

class RAT1PR_OT_ExportSlots(bpy.types.Operator):
    """Exporta los scripts de slots del recorrido de rat_1 (Paso 2)."""
    bl_idname  = "rat1pr.export_slots"
    bl_label   = "Exportar recorrido (slots)"
    bl_description = "Genera los scripts slot_NNN_rat_1_*.py en la carpeta de salida (con biomecanica cuadrupeda real)"
    bl_options = {"REGISTER"}

    def execute(self, context):
        import importlib.util as _ilu

        pc    = context.scene.rat1_path
        pts   = list(pc.path_points)
        n_pts = len(pts)

        if n_pts == 0:
            self.report({"ERROR"}, "Agrega al menos 1 punto de recorrido antes de exportar")
            return {"CANCELLED"}

        output_dir = bpy.path.abspath(pc.output_dir) if pc.output_dir else ""
        if not output_dir:
            self.report({"ERROR"}, "Define la carpeta de salida antes de exportar")
            return {"CANCELLED"}
        os.makedirs(output_dir, exist_ok=True)

        addon_dir = os.path.dirname(os.path.abspath(__file__))
        gen_path  = os.path.join(addon_dir, "generate_slots_rat_1.py")
        if not os.path.exists(gen_path):
            self.report({"ERROR"}, f"No se encontro generate_slots_rat_1.py en {gen_path}.")
            return {"CANCELLED"}

        spec = _ilu.spec_from_file_location("gen_slots_rat_1", gen_path)
        gen  = _ilu.module_from_spec(spec)
        spec.loader.exec_module(gen)

        today         = date.today().isoformat()
        root_rot      = (pc.root_rot_x, pc.root_rot_y, pc.root_rot_z)
        slot_index    = pc.slot_inicio
        current_frame = pc.frame_inicio

        if n_pts == 1:
            pt = pts[0]
            point = {
                "index": 0,
                "coordinates": {"x": pt.coords[0], "y": pt.coords[1], "z": pt.coords[2]},
                "texture": pt.texture or "", "face_index": pt.face_index or "0",
            }
            total_frames_idle = max(1, pc.frame_fin_manual - pc.frame_inicio + 1)
            code, end_frame = gen.generate_idle(slot_index, current_frame, point, today, root_rot, total_frames=total_frames_idle)
            fname = f"slot_{slot_index:03d}_rat_1_idle.py"
            with open(os.path.join(output_dir, fname), "w", encoding="utf-8") as f:
                f.write(code)
            pc.anim_frame_fin = end_frame
            self.report({"INFO"}, f"Exportacion OK: 1 slot idle | frames {pc.frame_inicio}→{end_frame} | {output_dir}")
            return {"FINISHED"}

        expanded_pts, parada_frames_marcadas = _expand_points_with_paradas(pts)
        key_points = [
            {"index": i + 1,
             "coordinates": {"x": round(pt.coords[0], 4), "y": round(pt.coords[1], 4), "z": round(pt.coords[2], 4)},
             "texture": pt.texture or "", "face_index": pt.face_index if pt.face_index else str(i + 1),
             "tipo_segmento": getattr(pt, "tipo_segmento", "AUTO"),
             # FIX (Kebyn, 2026-09-04): faltaba esta clave -- sin ella
             # group_segments() (generate_slots_rat_1.py) nunca podia
             # detectar los puntos duplicados de "parada" para su fix
             # de "caminar fantasma entre Parada y accion siguiente".
             # Debe coincidir con _StopPointStub (arriba en este archivo).
             "es_parada_dup": isinstance(pt, _StopPointStub)}
            for i, pt in enumerate(expanded_pts)
        ]

        segments = gen.group_segments(key_points)
        sync_paradas_frames(pc)
        sync_walk_styles(pc)

        prev_rz_exp = root_rot[2]
        parada_idx  = 0
        caminar_idx = 0
        for seg in segments:
            move_type = seg["type"]
            points    = seg["points"]
            _cur_rot = (root_rot[0], root_rot[1], prev_rz_exp)

            if move_type == "saltar_subir":
                code, end_frame = gen.generate_saltar_subir(slot_index, current_frame, points, today, _cur_rot)
                fname = f"slot_{slot_index:03d}_rat_1_saltar_subir.py"
            elif move_type == "saltar_bajar":
                code, end_frame = gen.generate_saltar_bajar(slot_index, current_frame, points, today, _cur_rot)
                fname = f"slot_{slot_index:03d}_rat_1_saltar_bajar.py"
            elif move_type == "pararse_dos_patas":
                code, end_frame = gen.generate_pararse_dos_patas(slot_index, current_frame, points, today, _cur_rot)
                fname = f"slot_{slot_index:03d}_rat_1_pararse_dos_patas.py"
            elif move_type == "olfatear":
                code, end_frame = gen.generate_olfatear(slot_index, current_frame, points, today, _cur_rot)
                fname = f"slot_{slot_index:03d}_rat_1_olfatear.py"
            elif move_type == "escarbar":
                code, end_frame = gen.generate_escarbar(slot_index, current_frame, points, today, _cur_rot)
                fname = f"slot_{slot_index:03d}_rat_1_escarbar.py"
            elif move_type == "roer":
                code, end_frame = gen.generate_roer(slot_index, current_frame, points, today, _cur_rot)
                fname = f"slot_{slot_index:03d}_rat_1_roer.py"
            elif move_type == "parada":
                if parada_idx < len(parada_frames_marcadas):
                    frames_esta_parada = parada_frames_marcadas[parada_idx]
                elif parada_idx < len(pc.paradas_frames):
                    frames_esta_parada = pc.paradas_frames[parada_idx].frames
                else:
                    frames_esta_parada = pc.frames_parada
                code, end_frame = gen.generate_parada(slot_index, current_frame, points, today, _cur_rot, frames_parada=frames_esta_parada)
                fname = f"slot_{slot_index:03d}_rat_1_parada.py"
                parada_idx += 1
            else:
                walk_style_actual = (pc.walk_styles[caminar_idx].style
                                      if caminar_idx < len(pc.walk_styles) else pc.walk_style)
                code, end_frame = gen.generate_caminar(slot_index, current_frame, points, today, _cur_rot, walk_style=walk_style_actual)
                fname = f"slot_{slot_index:03d}_rat_1_caminar.py"
                caminar_idx += 1

            with open(os.path.join(output_dir, fname), "w", encoding="utf-8") as f:
                f.write(code)

            if len(points) >= 2:
                # FIX (2026-09-03): usar el ULTIMO sub-tramo (points[-2] ->
                # points[-1]), no el vector global del grupo completo
                # (points[0] -> points[-1]). Para saltos/parada (siempre 2
                # puntos) es identico a antes -- solo cambia para un grupo
                # 'caminar' con varios sub-tramos (ej. pasillo en zigzag),
                # donde el rumbo real con el que termina la rata es el del
                # ULTIMO tramo, no la diagonal de punta a punta del grupo.
                # Mismo bug/fix que el preview (RAT1PR_OT_PreviewPath, mas
                # arriba): sin esto, el heading heredado por el siguiente
                # segmento (saltar_subir/saltar_bajar/parada) podia quedar
                # muy alejado del heading visual real, y el salto giraba
                # casi 360 grados (la vuelta larga) para corregirlo.
                _da = gen._compute_direction_angle(points[-2], points[-1])
                if _da is not None:
                    prev_rz_exp = math.degrees(_da)
            current_frame = end_frame + 1
            slot_index   += 1

        pc.anim_frame_fin = current_frame - 1
        total_frames = current_frame - pc.frame_inicio
        self.report({"INFO"}, f"Exportacion OK: {slot_index - pc.slot_inicio} slots | frames {pc.frame_inicio}→{current_frame-1} ({total_frames} fr) | {output_dir}")
        return {"FINISHED"}


class RAT1PR_OT_GenerateSlots(Operator):
    """Placeholder de compatibilidad (equivalente a ALFREDPR_OT_GenerateSlots)."""
    bl_idname  = "rat1pr.generate_slots"
    bl_label   = "Generar slots (InScene)"
    bl_options = {"REGISTER"}

    def execute(self, context):
        self.report({"INFO"}, "Usa 'Exportar recorrido' para generar los archivos .py")
        return {"FINISHED"}


# =============================================================================
# REGISTRO
# =============================================================================

pr_classes = (
    RAT1PathPoint,
    RAT1ParadaFrames,
    RAT1WalkStyleEntry,
    RAT1PathSettings,
    RAT1PR_OT_ToggleRecording,
    RAT1PR_OT_TogglePathViz,
    RAT1PR_OT_RemoveLast,
    RAT1PR_OT_RemovePoint,
    RAT1PR_OT_ClearPath,
    RAT1PR_OT_SyncParadasFrames,
    RAT1PR_OT_GenerateSlots,
    RAT1PR_OT_OpenBlendFile,
    RAT1PR_OT_PreviewPath,
    RAT1PR_OT_ResetPreview,
    RAT1PR_OT_SetAnimRange,
    RAT1PR_OT_ExportSlots,
)


def register_path_recorder():
    for cls in pr_classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
        bpy.utils.register_class(cls)
    bpy.types.Scene.rat1_path = bpy.props.PointerProperty(type=RAT1PathSettings)
    if _rat1_face_selection_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_rat1_face_selection_handler)


def unregister_path_recorder():
    global _draw_handle
    if _draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
        _draw_handle = None
    if _rat1_face_selection_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_rat1_face_selection_handler)
    for cls in reversed(pr_classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
    if hasattr(bpy.types.Scene, "rat1_path"):
        del bpy.types.Scene.rat1_path
