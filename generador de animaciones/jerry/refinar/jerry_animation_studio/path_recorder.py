
from .blender_compat import get_fcurves as _get_action_fcurves, new_fcurve as _new_fcurve

# -*- coding: utf-8 -*-
"""
path_recorder.py — Jerry Animation Studio
Sistema integrado de trazado de recorrido y generacion de slots.

FLUJO:
  1. El usuario selecciona faces en modo EDIT del mesh de escenario.
     Cada face seleccionada se agrega automaticamente como un punto del recorrido.
  2. El sistema detecta los segmentos: caminar / saltar_subir / saltar_bajar.
  3. Con un solo boton "GENERAR SLOTS" se crean los scripts slot_NNN_*.py
     y opcionalmente se ejecutan directamente en Blender (InScene).

Sin sistema de tunel — solo coordenadas de faces (centros de poligono).
"""

import bpy
from . import jump_motion as _jump
from . import observar_motion as _observar
import bmesh
import gpu
import json
import math
import os
from datetime import date
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from bpy.props import (
    CollectionProperty, StringProperty, FloatVectorProperty,
    BoolProperty, FloatProperty, IntProperty, EnumProperty,
)
from bpy.types import PropertyGroup, Operator
from bpy.app.handlers import persistent
from .constants import (
    DEFAULT_INTERACTION_DIR_ALFRED,
    DEFAULT_INTERACTION_DIR_JERRY,
    INTERACTION_MEETING_TOLERANCE,
)

# ── Variables globales de modulo ──────────────────────────────────────────────
_draw_handle    = None
_last_face_idx  = None

# =============================================================================
# PROPERTY GROUPS
# =============================================================================

# =============================================================================
# SISTEMA DE INTERACCION ENTRE PERSONAJES (Jerry <-> Alfred)
# =============================================================================
# NUEVO (Kebyn, portado de Alfred): cuando el recorrido de Jerry y el
# recorrido de Alfred tienen una coordenada en comun (dentro de
# INTERACTION_MEETING_TOLERANCE, ver constants.py), ese punto se
# considera un "punto de encuentro" y habilita ahi la opcion
# 'Interactuar' en el dropdown de tipo_segmento (ver
# _tipo_segmento_items() mas abajo). El dropdown de que animacion
# reproducir (interaccion_anim_choice) lista los .py encontrados en
# DEFAULT_INTERACTION_DIR_JERRY -- cada personaje reproduce su propia
# mitad de la interaccion desde su propia carpeta.
#
# Los caches de abajo existen porque bpy exige que la lista de tuplas
# devuelta por un items=funcion de EnumProperty se mantenga viva en
# memoria mientras el enum este dibujado (Blender no la copia) -- se
# indexan por as_pointer() del propio JRRSTPathPoint, estable mientras
# el punto exista en la coleccion. Ver path_recorder.py de Alfred para
# la version original de este sistema.

_tipo_segmento_dynamic_cache = {}
_interaccion_anim_cache      = {}


def _other_character_path_coords(context):
    """Coordenadas (lista de tuplas x,y,z) del recorrido de Alfred,
    visto desde el addon de Jerry. Devuelve [] si Alfred Animation
    Studio no esta instalado/registrado en esta escena o todavia no
    tiene puntos.
    """
    scene = getattr(context, "scene", None)
    if scene is None:
        return []
    other_pc = getattr(scene, "alfred_path", None)
    if other_pc is None:
        return []
    return [tuple(p.coords) for p in other_pc.path_points]


def _point_is_meeting_point(context, pt):
    """True si `pt` (un JRRSTPathPoint) cae, dentro de
    INTERACTION_MEETING_TOLERANCE, sobre alguna coordenada del
    recorrido de Alfred.
    """
    try:
        px, py, pz = pt.coords[0], pt.coords[1], pt.coords[2]
    except Exception:
        return False
    others = _other_character_path_coords(context)
    if not others:
        return False
    tol2 = INTERACTION_MEETING_TOLERANCE * INTERACTION_MEETING_TOLERANCE
    for ox, oy, oz in others:
        dx, dy, dz = px - ox, py - oy, pz - oz
        if (dx * dx + dy * dy + dz * dz) <= tol2:
            return True
    return False


# Items base de tipo_segmento (todo lo que YA existia). 'INTERACTUAR' se
# agrega dinamicamente en _tipo_segmento_items() SOLO cuando el punto es
# un punto de encuentro real con Alfred.
_TIPO_SEGMENTO_BASE_ITEMS = [
    ("AUTO",   "Caminar", "Movimiento automatico: caminar o saltar segun la geometria", "ANIM_DATA", 0),
    ("SALTAR", "Saltar", "Saltar desde este punto hasta el siguiente; duracion automatica incluso a la misma altura", "IPO_QUAD", 50),
    ("PARADA", "Parada",  "El personaje se detiene en este punto antes de continuar",   "PAUSE",     1),
    # NUEVO (Kebyn, 2026-09-24): 'Observar' -- Jerry se sienta en alerta y
    # gira la cabeza de derecha a izquierda (pose sentado_mirar_frente.json,
    # ver observar_motion.py). Es una variante de Parada: root inmovil, mismos
    # 'Frames' y misma orientacion guardada ('Rotar root'), pero sin
    # animacion .py importada.
    ("OBSERVAR", "Observar", "Jerry se sienta en alerta y gira la cabeza de derecha a izquierda antes de continuar", "HIDE_OFF", 60),
]

# Valor por defecto de JRRSTPathPoint.parada_frames_punto (ver mas abajo).
_PARADA_FRAMES_PUNTO_DEFAULT = 24


def _tipo_segmento_update(self, context):
    """Al elegir 'Observar' en un punto que todavia tiene los frames por
    defecto de una parada (24), sube a la duracion tipica de Observar:
    con 24 frames apenas alcanza para sentarse y pararse, sin girar la
    cabeza. Si el usuario ya cambio los frames, no se toca."""
    if (self.tipo_segmento == "OBSERVAR"
            and self.parada_frames_punto == _PARADA_FRAMES_PUNTO_DEFAULT):
        self.parada_frames_punto = _observar.FRAMES_OBSERVAR_DEFAULT


def _tipo_segmento_items(self, context):
    items = list(_TIPO_SEGMENTO_BASE_ITEMS)
    if _point_is_meeting_point(context, self):
        items.append((
            "INTERACTUAR", "Interactuar",
            "Solo disponible cuando este punto coincide con una coordenada "
            "del recorrido de Alfred (punto de encuentro). Reproduce, en "
            "este punto, la animacion .py elegida en 'Animacion de "
            "interaccion' (carpeta de interaccion de Jerry)",
            "COMMUNITY", 20,
        ))
    _tipo_segmento_dynamic_cache[self.as_pointer()] = items
    return _tipo_segmento_dynamic_cache[self.as_pointer()]


def _interaccion_anim_items(self, context):
    """Lista dinamica (dropdown) de animaciones .py encontradas en
    DEFAULT_INTERACTION_DIR_JERRY -- cada archivo .py de esa carpeta es
    una animacion de interaccion que Jerry puede reproducir en un punto
    de encuentro.
    """
    folder = DEFAULT_INTERACTION_DIR_JERRY
    items = []
    try:
        os.makedirs(folder, exist_ok=True)
        for fname in sorted(os.listdir(folder)):
            if fname.lower().endswith(".py") and not fname.startswith("_"):
                stem = fname[:-3]
                label = stem.replace("_", " ").strip().title() or stem
                items.append((
                    stem, label,
                    f"Reproduce '{fname}' en este punto de encuentro",
                    "ARMATURE_DATA", len(items),
                ))
    except Exception as e:
        print(f"jerry_animation_studio: no se pudo leer '{folder}': {e}")
    if not items:
        items.append((
            "NONE", "(sin animaciones todavia)",
            f"No hay archivos .py en {folder} -- exporta las animaciones "
            f"de interaccion de Jerry ahi",
            "ERROR", 0,
        ))
    _interaccion_anim_cache[self.as_pointer()] = items
    return _interaccion_anim_cache[self.as_pointer()]


class JRRSTPathPoint(PropertyGroup):
    coords:     FloatVectorProperty(name="Coords",     size=3, default=(0.0, 0.0, 0.0))
    texture:    StringProperty(name="Textura",         default="")
    face_index: StringProperty(name="Face Index",      default="")

    # NUEVO (portado de Alfred, 2026-08-05): tipo de segmento EDITABLE
    # directamente en la lista "Coordenadas seleccionadas" del Paso 1 —
    # reemplaza la etiqueta fija "caminar" por un dropdown que permite
    # cambiarlo a "parada" (u otros tipos a futuro) sin tocar el
    # recorrido grabado. AUTO = comportamiento de siempre (caminar o
    # salto segun la geometria real entre este punto y el siguiente).
    # Si TODOS los puntos quedan en AUTO, el recorrido es identico al de
    # antes -- ver _expand_points_with_paradas().
    tipo_segmento: EnumProperty(
        name="Tipo",
        description=(
            "Tipo de movimiento hacia el siguiente punto del recorrido. "
            "'Auto' detecta caminar/subir/bajar segun la geometria real "
            "(comportamiento de siempre). 'Parada' fuerza que el personaje "
            "llegue aqui y se quede detenido antes de continuar."
        ),
        items=_tipo_segmento_items,
        default=0,
        update=_tipo_segmento_update,
    )
    parada_frames_punto: IntProperty(
        name="Frames parado aqui",
        description="Cantidad de frames que el personaje permanece detenido en este punto antes de seguir el recorrido",
        default=_PARADA_FRAMES_PUNTO_DEFAULT, min=1, soft_max=99999,
    )

    # NUEVO (portado de Alfred, Kebyn 2026-09-14): animacion .py
    # IMPORTADA para un punto marcado como 'Parada' -- si se asigna, este
    # punto reproduce esa animacion completa en vez del reset a
    # IDLE_POSE de siempre. Ver ALFREDPathPoint.parada_anim_file
    # (path_recorder.py de Alfred) y generate_parada()/anim_file_path en
    # generate_slots_jerry.py.
    parada_anim_file: StringProperty(
        name="Animacion importada (.py)",
        description=(
            "Script .py de animacion importada que se reproduce durante "
            "esta parada en vez de la pose estatica por defecto. Vacio = "
            "comportamiento normal de 'Parada' (root inmovil, IDLE_POSE)"
        ),
        default="",
        subtype='FILE_PATH',
    )

    # NUEVO (portado de Alfred, Kebyn 2026-09-14): orientacion (heading,
    # rotacion Z) GUARDADA a mano para este punto de "Parada". El usuario
    # rota el empty root ("jerry", ROOT_NAME) en el viewport -- boton
    # "Rotar root (jerry)" (invoca bpy.ops.transform.rotate constreñido
    # al eje Z) o directamente con R, Z en el viewport -- y despues
    # aprieta "Guardar orientacion". Eso lee root_empty.rotation_euler.z
    # ACTUAL (convertido a grados, mismo formato que pc.root_rot_z) y lo
    # graba aca. Mientras parada_rot_saved este activo, ese valor
    # reemplaza al heading automatico desde este punto de parada en
    # adelante -- tanto en "Reproducir recorrido" (JRRSTPR_OT_PreviewPath)
    # como en la generacion de segmentos reales (JRRSTPR_OT_ExportSlots)
    # -- y se mantiene asi para el resto del recorrido hasta el proximo
    # tramo con desplazamiento real que recalcule un heading propio, o
    # hasta que el usuario vuelva a guardar/borrar la orientacion de ESTE
    # punto. Ver JRRSTPR_OT_RotateParadaRoot / JRRSTPR_OT_SaveParadaRot /
    # JRRSTPR_OT_ClearParadaRot mas abajo.
    parada_rot_saved: BoolProperty(
        name="Orientacion guardada",
        description=(
            "Si esta activo, este punto de parada fuerza el heading "
            "(rotacion Z) del root 'jerry' al valor guardado, en vez de "
            "usar el heading automatico. Se mantiene para el resto del "
            "recorrido hasta el proximo tramo con desplazamiento real, o "
            "hasta que se vuelva a editar"
        ),
        default=False,
    )
    parada_rot_z: FloatProperty(
        name="Rotacion Z guardada (grados)",
        description="Heading (rotacion Z, en grados) guardado para este punto de parada",
        default=0.0, precision=1,
    )

    # NUEVO (Kebyn, portado de Alfred): dropdown de que animacion de
    # interaccion reproducir en este punto CUANDO tipo_segmento ==
    # 'INTERACTUAR' (solo seleccionable en un punto de encuentro real
    # con Alfred -- ver _point_is_meeting_point() e
    # _interaccion_anim_items() mas arriba). Lista los .py encontrados
    # en DEFAULT_INTERACTION_DIR_JERRY (constants.py).
    interaccion_anim_choice: EnumProperty(
        name="Animacion de interaccion",
        description=(
            "Animacion .py (carpeta de interaccion de Jerry) que se "
            "reproduce en este punto de encuentro con Alfred"
        ),
        items=_interaccion_anim_items,
    )


class JRRSTParadaFrames(PropertyGroup):
    """Duracion (en frames) de UNA parada individual del recorrido.

    Portado de ALFREDParadaFrames (alfred_animation_studio, 2026-08-05).
    Permite un valor independiente por cada parada detectada en el
    recorrido (una entrada por cada segmento tipo 'parada' que retorna
    _group_segments(), en el mismo orden en que aparecen los puntos
    duplicados en el Path Recorder).
    """
    frames: IntProperty(
        name="Frames",
        description=(
            "Frames que dura esta parada especifica (root inmovil). "
            "Se sincroniza automaticamente con la cantidad real de "
            "paradas detectadas en el recorrido."
        ),
        default=60, min=1, soft_max=99999,
    )


class JRRSTWalkStyleEntry(PropertyGroup):
    """Estilo de caminata (Normal/Lento/Herido/Rapido/Correr) de UN tramo
    'caminar' individual del recorrido.

    NUEVO (portado de Alfred, 2026-08-05 -- pedido de Kebyn): cada tramo
    'caminar' detectado en el recorrido elige su propio estilo de forma
    independiente, en vez de un unico valor global aplicado a todos los
    tramos por igual. Mismo patron que JRRSTParadaFrames para las
    paradas -- una entrada por cada segmento tipo 'caminar' que retorna
    _group_segments(), en el mismo orden en que aparecen en el recorrido.
    """
    style: EnumProperty(
        name="Estilo de caminata",
        description="Variante de la animacion de caminar para este tramo especifico",
        items=[
            ("NORMAL", "Caminar Normal", "Caminata estandar (por defecto)", "FORWARD", 0),
            ("LENTO", "Caminar Lento", "Caminata lenta / cautelosa (olfateando)", "TRIA_LEFT", 1),
            ("HERIDO", "Caminar Herido", "Caminata herida / cojeando (pata trasera debil)", "ERROR", 2),
            ("RAPIDO", "Caminar Rapido", "Caminata rapida / trote corto", "TRIA_RIGHT", 3),
            ("CORRER", "Correr", "Carrera / trote largo", "TRACKING_FORWARDS", 4),
            ("CORRER_2", "Correr 2", "Carrera mas rapida (+50% velocidad y amplitud sobre Correr)", "TRACKING_FORWARDS", 5),
        ],
        default="NORMAL",
    )

    # "Foto" del estilo horneado en la duracion/keyframes real de este
    # tramo la ultima vez que se genero/actualizo (misma logica que
    # ALFREDWalkStyleEntry.applied_style en Alfred). Uso interno.
    applied_style: StringProperty(
        name="Estilo aplicado (interno)",
        description=(
            "Ultimo estilo de caminata horneado en este tramo. Uso "
            "interno -- no editar a mano."
        ),
        default="",
    )


class JRRSTPathSettings(PropertyGroup):
    """Configuracion y estado del Path Recorder integrado."""

    # ── Estado de grabacion ───────────────────────────────────────────────────
    recording_active: BoolProperty(
        name="Grabacion activa",
        description="Detecta automaticamente las faces seleccionadas",
        default=False,
    )
    path_points: CollectionProperty(type=JRRSTPathPoint)

    # ── Configuracion de slots ────────────────────────────────────────────────
    slot_inicio: IntProperty(
        name="Primer slot",
        description="Numero del primer slot a generar",
        default=1, min=1, max=999,
    )
    frame_inicio: IntProperty(
        name="Frame inicial",
        description="Frame de Blender donde empieza la secuencia",
        default=1, min=0,
    )
    frame_fin_manual: IntProperty(
        name="Frame final",
        description="Frame final de la animacion (solo modo 1 coordenada, sin recorrido)",
        default=100, min=2, soft_max=99999,
    )
    frames_por_bloque: IntProperty(
        name="Frames/bloque (caminar)",
        description="Frames por unidad de distancia para la animacion de caminar",
        default=26, min=6, max=120,
    )
    frames_parada: IntProperty(
        name="Frames por parada",
        description=(
            "Frames que dura cada tramo 'parada' (root inmovil, canvas "
            "libre para superponer una pose de segmento). Valor por "
            "defecto usado para paradas nuevas -- ver paradas_frames "
            "para el valor individual de cada una."
        ),
        default=60, min=1, soft_max=99999,
    )
    paradas_frames: CollectionProperty(
        name="Frames por parada (individual)",
        description=(
            "Duracion en frames de cada parada del recorrido, en el "
            "mismo orden en que aparecen en el Path Recorder. Se "
            "sincroniza automaticamente con la cantidad real de "
            "paradas detectadas; los valores nuevos parten de "
            "frames_parada, y los que ya se hayan editado a mano se "
            "conservan aunque cambie el numero total de paradas."
        ),
        type=JRRSTParadaFrames,
    )

    # NUEVO (portado de Alfred, transiciones entre tramos, Kebyn
    # 2026-09-14): suaviza el corte de pose justo en el borde entre dos
    # tramos consecutivos de TIPO DISTINTO (ej. Caminar -> Parada,
    # Parada -> Caminar, Caminar -> subir/bajar). Cuando dos tramos
    # consecutivos son del MISMO tipo (ej. dos "Caminar" seguidos) el
    # ciclo de marcha ya continua sin corte visible, asi que ahi NUNCA
    # se aplica -- ver _suavizar_borde_segmentos_jerry() / el uso de
    # "_prev_move_type != seg['type']" en JRRSTPR_OT_PreviewPath.execute().
    # A diferencia de Alfred (una Action nueva por tramo empujada a su
    # propia pista NLA 'Slot_NNN_arm/root'), el preview de Jerry escribe
    # TODOS los tramos como keyframes dentro de DOS Actions unicas y
    # continuas para todo el recorrido -- el mecanismo de suavizado es
    # el mismo (smoothstep canal por canal alrededor del corte), solo
    # que ambos "lados" del corte viven en la misma Action.
    usar_transiciones: BoolProperty(
        name="Suavizar transiciones entre tramos distintos",
        description=(
            "Interpola la pose alrededor del corte entre dos tramos "
            "consecutivos cuando son de tipo distinto (Caminar/Parada/"
            "subir/bajar), en vez del cambio brusco de un frame al "
            "otro. No hace nada entre dos tramos del mismo tipo -- ahi "
            "el movimiento ya es continuo"
        ),
        default=True,
    )
    frames_transicion: IntProperty(
        name="Frames de transicion",
        description=(
            "Cantidad de frames a cada lado del corte que se re-"
            "interpolan suavemente entre la pose final del tramo "
            "anterior y la inicial del siguiente"
        ),
        default=6, min=1, max=40,
    )

    # NUEVO (portado de Alfred, 2026-08-05): selector de "estilo de
    # caminata" — funciona como multiplexor, igual que en Alfred: la
    # animacion base de caminar (SniffingSearchCycle) tiene varias
    # variantes segun el contexto de la historia (normal / lenta /
    # herido / rapida / correr). Cada tramo 'caminar' detectado elige su
    # propio estilo de forma independiente (ver walk_styles abajo y
    # sync_walk_styles()); walk_style solo sirve de valor por defecto
    # para las entradas NUEVAS de walk_styles cuando aparece un tramo
    # 'caminar' recien detectado.
    walk_style: EnumProperty(
        name="Estilo de caminata (default)",
        description=(
            "Estilo por defecto para tramos 'caminar' nuevos que todavia "
            "no tienen su propia entrada en walk_styles"
        ),
        items=[
            ("NORMAL", "Caminar Normal", "Caminata estandar (por defecto)", "FORWARD", 0),
            ("LENTO", "Caminar Lento", "Caminata lenta / cautelosa (olfateando)", "TRIA_LEFT", 1),
            ("HERIDO", "Caminar Herido", "Caminata herida / cojeando (pata trasera debil)", "ERROR", 2),
            ("RAPIDO", "Caminar Rapido", "Caminata rapida / trote corto", "TRIA_RIGHT", 3),
            ("CORRER", "Correr", "Carrera / trote largo", "TRACKING_FORWARDS", 4),
            ("CORRER_2", "Correr 2", "Carrera mas rapida (+50% velocidad y amplitud sobre Correr)", "TRACKING_FORWARDS", 5),
        ],
        default="NORMAL",
    )
    walk_styles: CollectionProperty(
        name="Estilo de caminata (por tramo)",
        description=(
            "Estilo de caminata de cada tramo 'caminar' individual del "
            "recorrido, en el mismo orden en que aparecen. Se sincroniza "
            "automaticamente con la cantidad real de tramos 'caminar' "
            "detectados; los valores nuevos parten de walk_style, y los "
            "que ya se hayan elegido a mano se conservan aunque cambie el "
            "numero total de tramos."
        ),
        type=JRRSTWalkStyleEntry,
    )

    root_rot_x: FloatProperty(name="Rot X", default=0.0, precision=1,
        description="Rotacion inicial del root en grados (eje X)")
    root_rot_y: FloatProperty(name="Rot Y", default=0.0, precision=1,
        description="Rotacion inicial del root en grados (eje Y)")
    root_rot_z: FloatProperty(name="Rot Z", default=-90.0, precision=1,
        description="Rotacion inicial del root en grados (eje Z)")

    # ── Destino de los slots generados ───────────────────────────────────────
    output_dir: StringProperty(
        name="Carpeta salida",
        description="Carpeta donde se guardan los scripts slot_NNN_*.py generados",
        default=r"C:\Users\user\Desktop\Alfred_Animacion\animacion",
        subtype="DIR_PATH",
    )

    # ── Ejecucion directa en escena ───────────────────────────────────────────
    execute_inscene: BoolProperty(
        name="Ejecutar en escena",
        description="Ademas de guardar los archivos, ejecuta cada slot directamente en Blender",
        default=False,
    )

    # ── Estado / feedback ─────────────────────────────────────────────────────
    status_msg:     StringProperty(default="")
    last_generated: IntProperty(default=0)   # cantidad de slots generados
    anim_frame_fin:    IntProperty(default=0)   # frame final calculado del recorrido
    anim_total_frames: IntProperty(default=0)   # total frames calculados del recorrido

    # ── Archivo .blend del personaje ──────────────────────────────────────────
    blend_filepath: StringProperty(
        name="Archivo .blend del personaje",
        description="Ruta al archivo .blend que contiene el rig del personaje",
        default="",
        subtype="FILE_PATH",
    )

    # NUEVO (portado de Alfred, 2026-08-06): controla si la lista completa
    # de "Coordenadas seleccionadas" del Paso 1 esta expandida o colapsada.
    # Antes, el panel de Jerry solo mostraba los ultimos 5 puntos
    # (englobando/resumiendo el resto), lo que impedia elegir cualquier
    # coordenada especifica como 'Parada'. Con esta propiedad se dibuja la
    # lista COMPLETA (igual que en Alfred), con su propio dropdown
    # Caminar/Parada por punto -- ver panels.py, JRRST_PT_PathRecorder.
    show_coords_list: BoolProperty(
        name="Mostrar lista de coordenadas",
        description="Expande o colapsa la lista completa de coordenadas registradas",
        default=True,
    )

# =============================================================================
# HANDLER — deteccion automatica de face seleccionada
# =============================================================================

@persistent
def _jerry_face_selection_handler(scene):
    """Se ejecuta en depsgraph_update_post. Registra faces seleccionadas."""
    global _last_face_idx

    path_cfg = getattr(scene, "jerry_path", None)
    if path_cfg is None or not path_cfg.recording_active:
        return

    obj = bpy.context.active_object
    if obj is None or obj.type != "MESH" or obj.mode != "EDIT":
        return

    bm = bmesh.from_edit_mesh(obj.data)
    selected = [f for f in bm.faces if f.select]
    if len(selected) != 1:
        return

    face = selected[0]
    face_id = str(face.index)

    # Evita registrar el mismo punto varias veces mientras esa cara sigue
    # seleccionada (este handler se dispara en cada depsgraph_update_post,
    # no solo al hacer clic). Comparamos SOLO contra el ultimo punto
    # agregado -- no contra todo el historial -- para permitir que el
    # recorrido vuelva a pasar por una coordenada ya visitada antes
    # (ida y vuelta, guardias, patrullas por el mismo camino).
    if path_cfg.path_points and path_cfg.path_points[-1].face_index == face_id:
        return

    _last_face_idx = face.index
    center_local  = face.calc_center_median()
    center_global = obj.matrix_world @ center_local

    mat_name = "No Material"
    if obj.data.materials and face.material_index < len(obj.data.materials):
        mat = obj.data.materials[face.material_index]
        if mat:
            mat_name = mat.name

    pt          = path_cfg.path_points.add()
    pt.coords   = center_global
    pt.texture  = mat_name
    pt.face_index = face_id

    sync_paradas_frames(path_cfg)
    sync_walk_styles(path_cfg)

    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            area.tag_redraw()

# =============================================================================
# DIBUJO 3D — visualizacion del recorrido en el viewport
# =============================================================================

def _draw_path_3d():
    scene = bpy.context.scene
    path_cfg = getattr(scene, "jerry_path", None)
    if path_cfg is None or len(path_cfg.path_points) < 1:
        return

    points      = []
    col_pts     = []
    lines       = []
    col_lines   = []

    for i, pt in enumerate(path_cfg.path_points):
        coord = Vector(pt.coords)
        points.append(coord)
        col_pts.append((0.2, 1.0, 0.3, 1.0))
        if i > 0:
            prev = Vector(path_cfg.path_points[i - 1].coords)
            lines += [prev, coord]
            col_lines += [(1.0, 1.0, 0.0, 1.0), (1.0, 1.0, 0.0, 1.0)]

    gpu.state.blend_set("ALPHA")
    gpu.state.depth_test_set("LESS_EQUAL")
    gpu.state.line_width_set(4.0)
    gpu.state.point_size_set(10.0)

    shader = gpu.shader.from_builtin("SMOOTH_COLOR")
    if lines:
        batch_for_shader(shader, "LINES",   {"pos": lines,   "color": col_lines}).draw(shader)
    if points:
        batch_for_shader(shader, "POINTS",  {"pos": points,  "color": col_pts}).draw(shader)

    gpu.state.line_width_set(1.0)
    gpu.state.point_size_set(1.0)

# =============================================================================
# TRANSICIONES ENTRE TRAMOS (portado de Alfred, Kebyn 2026-09-14)
# =============================================================================

def _smoothstep01(t):
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return t * t * (3.0 - 2.0 * t)


def _suavizar_par_de_acciones(action_a, action_b, frame_a, frame_b, n_frames):
    """Suaviza el corte entre `action_a` (tramo anterior, termina en
    frame_a) y `action_b` (tramo siguiente, empieza en frame_b): para
    cada canal (data_path + indice) presente en AMBAS acciones, evalua
    el valor justo antes del corte y justo despues: si difieren,
    sobrescribe los ultimos `n_frames` de action_a y los primeros
    `n_frames` de action_b con una interpolacion smoothstep hacia el
    valor del otro lado. Idéntico al de alfred_animation_studio --
    `action_a` y `action_b` pueden ser la MISMA Action (ver
    _suavizar_borde_segmentos_jerry() mas abajo): en ese caso simplemente
    reescribe dos ventanas de frames distintas dentro de la misma
    fcurve, a cada lado del corte."""
    if not action_a or not action_b or n_frames <= 0:
        return
    fcs_a = {(fc.data_path, fc.array_index): fc for fc in _get_action_fcurves(action_a, create=False)}
    fcs_b = {(fc.data_path, fc.array_index): fc for fc in _get_action_fcurves(action_b, create=False)}

    for key, fc_a in fcs_a.items():
        fc_b = fcs_b.get(key)
        if fc_b is None:
            continue
        try:
            valor_a = fc_a.evaluate(frame_a)
            valor_b = fc_b.evaluate(frame_b)
        except Exception:
            continue
        if abs(valor_a - valor_b) < 1e-5:
            continue

        # Cola de salida (dentro de action_a, terminando justo en frame_a)
        f_ini_a = frame_a - n_frames
        for f in range(f_ini_a, frame_a + 1):
            t = (f - f_ini_a) / max(1, n_frames)
            valor = valor_a + (valor_b - valor_a) * _smoothstep01(t) * 0.5
            fc_a.keyframe_points.insert(f, valor, options={'FAST'})
        fc_a.update()

        # Cola de entrada (dentro de action_b, empezando justo en frame_b)
        f_fin_b = frame_b + n_frames
        for f in range(frame_b, f_fin_b + 1):
            t = (f - frame_b) / max(1, n_frames)
            valor = (valor_a + (valor_b - valor_a) * 0.5) + (valor_b - (valor_a + (valor_b - valor_a) * 0.5)) * _smoothstep01(t)
            fc_b.keyframe_points.insert(f, valor, options={'FAST'})
        fc_b.update()


def _suavizar_borde_segmentos_jerry(arm_act, root_act, frame_fin_anterior,
                                     frame_inicio_actual, n_frames):
    """Suaviza el corte entre el tramo anterior y el tramo actual del
    recorrido, para el armature ('Dog_001_rig') y el root ('jerry').
    Solo debe llamarse cuando el TIPO de tramo cambio de uno al
    siguiente (ej. Caminar -> Parada) -- ver el llamado en
    JRRSTPR_OT_PreviewPath.execute(). Entre dos tramos del mismo tipo
    (ej. dos "Caminar" seguidos) el movimiento ya es continuo y esto no
    se llama.

    DIFERENCIA CON ALFRED: en alfred_animation_studio cada tramo genera
    su PROPIA Action y la empuja a su propia pista NLA
    ('Slot_NNN_arm'/'Slot_NNN_root'), asi que el corte esta entre DOS
    Actions distintas (una por pista NLA, ver _get_slot_nla_action() en
    ese addon). El preview de Jerry (JRRSTPR_OT_PreviewPath) NO arma una
    Action nueva por tramo -- escribe TODOS los tramos como keyframes
    dentro de DOS Actions unicas y continuas para todo el recorrido
    ('_jerry_preview_arm'/'_jerry_preview_root', ver ARM_ACT/ROOT_ACT en
    execute()). Por eso aca no hace falta buscar la Action de "cada
    lado" por pista NLA -- ambos lados del corte viven en la MISMA
    Action, y _suavizar_par_de_acciones() ya soporta ese caso (evalua el
    valor del canal en frame_fin_anterior vs frame_inicio_actual DENTRO
    de la misma fcurve y, si difieren, reescribe una ventana de frames a
    cada lado del corte)."""
    if n_frames <= 0 or frame_inicio_actual <= frame_fin_anterior:
        return
    _suavizar_par_de_acciones(arm_act, arm_act, frame_fin_anterior, frame_inicio_actual, n_frames)
    _suavizar_par_de_acciones(root_act, root_act, frame_fin_anterior, frame_inicio_actual, n_frames)


# =============================================================================
# DETECCION DE SEGMENTOS
# =============================================================================

def _detect_move(p0, p1):
    if getattr(p0,'tipo_segmento','AUTO') == 'SALTAR':
        z0,z1=round(p0.coords[2],2),round(p1.coords[2],2)
        return 'saltar_subir' if z1>z0 else 'saltar_bajar' if z1<z0 else 'saltar_horizontal'
    """NUEVO (portado de Alfred, 2026-08-05): si el punto es identico al
    anterior (misma x/y/z), se clasifica como "parada" — root inmovil,
    canvas libre para superponer una pose de segmento en este tramo.
    Debe coincidir con detect_movement_type() en generate_slots_jerry.py.

    FIX (portado de Alfred, Kebyn, 2026-08-19): "en las diagonales la
    lista de recorrido lo muestra como bajar, cuando lo unico que hace es
    ir en diagonal -- el personaje camina con normalidad, el error esta
    en como la interfaz lo detecta". Causa: pt.coords viene del raycast
    de seleccion de faces (world-space) y arrastra ruido de punto
    flotante de orden 1e-6/1e-5 (multiplicacion de matrices) -- en una
    diagonal (misma altura de bloque) ese ruido hacia que z1 fuera, por
    ejemplo, 9.000001 en vez de exactamente 9.000000, y la comparacion
    exacta `z1 > z0` / `z1 < z0` de mas abajo lo clasificaba como salto.
    La generacion real de la animacion nunca mostraba el bug porque
    exporta las coordenadas redondeadas a 4 decimales antes de usarlas --
    ese redondeo diluye el ruido. Aca se aplica el mismo redondeo a 4
    decimales ANTES de comparar, para que la lista de la interfaz
    coincida exactamente con lo que realmente se genera. Un salto real
    (altura de un bloque, >= 0.1) sigue detectandose sin problema -- 4
    decimales solo absorbe el ruido de punto flotante, no diferencias de
    altura reales.
    """
    x0, y0, z0 = p0.coords[0], p0.coords[1], p0.coords[2]
    x1, y1, z1 = p1.coords[0], p1.coords[1], p1.coords[2]
    x0, y0, z0 = round(x0, 4), round(y0, 4), round(z0, 4)
    x1, y1, z1 = round(x1, 4), round(y1, 4), round(z1, 4)
    if x0 == x1 and y0 == y1 and z0 == z1:
        return "parada"
    if   z1 > z0: return "saltar_subir"
    elif z1 < z0: return "saltar_bajar"
    else:          return "caminar"

def _group_segments(path_points):
    """Agrupa los puntos en segmentos: caminar (multi-punto), saltar_subir/bajar
    (2 puntos), parada (2 puntos identicos — NUEVO, portado de Alfred)."""
    pts = list(path_points)
    segments = []
    i = 0
    while i < len(pts) - 1:
        move = _detect_move(pts[i], pts[i + 1])
        if move == "caminar":
            group = [pts[i]]
            while i < len(pts) - 1 and _detect_move(pts[i], pts[i + 1]) == "caminar":
                group.append(pts[i + 1])
                i += 1
            segments.append({"type": "caminar", "points": group})
        else:
            segments.append({"type": move, "points": [pts[i], pts[i + 1]]})
            i += 1
    return segments


class _StopPointStub:
    """Objeto liviano con la misma 'forma' que JRRSTPathPoint (coords,
    texture, face_index) usado para representar el punto DUPLICADO que se
    inserta automaticamente detras de cada punto marcado como parada.
    No es una PropertyGroup real (no se guarda en la escena) -- solo existe
    en memoria mientras se arma el recorrido para preview/exportacion.
    Portado de Alfred (_StopPointStub), 2026-08-05."""
    __slots__ = ("coords", "texture", "face_index")

    def __init__(self, coords, texture, face_index):
        self.coords     = tuple(coords)
        self.texture    = texture
        self.face_index = face_index


def _expand_points_with_paradas(pts):
    """Portado de Alfred (_expand_points_with_paradas), 2026-08-05: en la
    lista "Coordenadas seleccionadas" del Paso 1, cada punto tiene un
    dropdown editable (pt.tipo_segmento) que por defecto esta en 'AUTO'
    (caminar/salto segun la geometria, comportamiento de siempre) pero
    que el usuario puede cambiar a 'PARADA'. Esta funcion recorre los
    puntos e inserta, inmediatamente despues de cada punto marcado como
    PARADA, un punto DUPLICADO (mismas coordenadas) -- reutilizando asi
    el mecanismo ya existente de deteccion de 'parada' (dos puntos
    consecutivos con coordenadas identicas, ver _detect_move() en este
    mismo archivo y detect_movement_type() en generate_slots_jerry.py),
    sin que el usuario tenga que seleccionar la misma face dos veces (el
    handler de seleccion de faces ya lo impide por diseno).

    Si NINGUN punto esta en modo PARADA (todos en AUTO), la lista
    resultante es identica a la original -- el flujo de solo caminar no
    se ve afectado en absoluto.

    Retorna una tupla:
      (puntos_expandidos, frames_paradas_marcadas, anim_files_paradas_marcadas,
       rot_paradas_marcadas)
    donde frames_paradas_marcadas es la lista de pt.parada_frames_punto,
    anim_files_paradas_marcadas es la lista de pt.parada_anim_file (NUEVO,
    Kebyn 2026-09-14, portado de Alfred -- animacion .py importada por
    punto de parada, o "" si el punto no tiene ninguna asociada), y
    rot_paradas_marcadas es la lista de tuplas (rot_saved: bool,
    rot_z_deg: float) -- orientacion GUARDADA a mano para ese punto de
    parada (NUEVO, Kebyn 2026-09-14, portado de Alfred -- ver
    JRRSTPathPoint.parada_rot_saved / parada_rot_z y
    JRRSTPR_OT_SaveParadaRot) -- las tres en el mismo orden en que
    apareceran los segmentos 'parada' que produzca luego
    _group_segments() sobre el resultado.
    """
    expanded = []
    frames_paradas_marcadas = []
    anim_files_paradas_marcadas = []
    rot_paradas_marcadas = []
    n = len(pts)
    for i, pt in enumerate(pts):
        expanded.append(pt)

        # NUEVO (Kebyn, 2026-09-24): 'OBSERVAR' se expande igual que
        # 'PARADA' (punto duplicado, root inmovil, mismos Frames y misma
        # orientacion guardada); lo que cambia es la animacion del cuerpo,
        # que decide el consumidor mirando el tipo_segmento del punto real
        # (p0 del segmento 'parada') -- ver 'observar' en Preview / Generar /
        # Exportar.
        override_activo = getattr(pt, "tipo_segmento", "AUTO") in ("PARADA", "OBSERVAR")

        # SALVAGUARDA: las coordenadas de saltar_subir / saltar_bajar NO se
        # pueden alterar a parada -- solo los tramos que geometricamente
        # son "caminar" (Z constante). Si por cualquier motivo (ej. se
        # recorto/cambio un punto despues de marcarlo) el tramo real hacia
        # el siguiente punto resulta ser un salto, se ignora el override
        # aunque tipo_segmento siga en "PARADA".
        if override_activo and i < n - 1:
            real_move = _detect_move(pt, pts[i + 1])
            if real_move != "caminar":
                override_activo = False

        if override_activo:
            expanded.append(_StopPointStub(pt.coords, pt.texture, pt.face_index))
            frames_paradas_marcadas.append(max(1, int(pt.parada_frames_punto)))
            # Observar no usa animacion .py importada: se ignora aunque el
            # punto tenga una asociada de cuando era 'Parada'.
            anim_files_paradas_marcadas.append(
                "" if getattr(pt, "tipo_segmento", "AUTO") == "OBSERVAR"
                else (getattr(pt, "parada_anim_file", "") or ""))
            rot_paradas_marcadas.append((
                bool(getattr(pt, "parada_rot_saved", False)),
                float(getattr(pt, "parada_rot_z", 0.0)),
            ))
    return expanded, frames_paradas_marcadas, anim_files_paradas_marcadas, rot_paradas_marcadas


def calcular_estimacion_geometrica(scene):
    """
    NUEVO (portado de Alfred, ALFREDPathRecorder.calcular_estimacion_geometrica,
    2026-08-06): version reutilizable de la "Estimacion de slots" que ya se
    dibuja inline en JRRST_PT_PathRecorder.draw() (Paso 2), separada en una
    funcion propia para poder invocarla tambien desde
    JRRSTSEG_OT_AutoSplitFromConfig (boton "Dividir segmentos" del Paso 3),
    que necesita la misma lista de tramos sin depender de que el panel se
    haya dibujado antes.

    Usa exactamente la misma formula que ya vive en el panel (frames_por_bloque
    * speed_mult del estilo de caminata, min. 24 frames por tramo caminar;
    SALTAR_SUBIR_FRAMES/SALTAR_BAJAR_FRAMES de generate_slots_jerry.py para
    saltar_subir/saltar_bajar; pc.frames_parada o el frame marcado a mano
    para parada) -- NO la formula de Alfred (FRAMES_PER_UNIT/HALF_CYCLE),
    que es propia del rig bipedo.
    CORREGIDO (Kebyn, 2026-08-24): antes tenia 48/42 hardcodeados en vez de
    importar las mismas constantes que usan los generadores reales
    (generate_saltar_subir/generate_saltar_bajar), causando que "Dividir
    segmentos" (Paso 3) creara segmentos mas largos de lo que la animacion
    real ocupa.

    Devuelve una lista de dicts:
        {"slot": int, "tipo": str, "frames_estimados": int}
    o [] si no hay suficientes puntos de recorrido para estimar nada.
    """
    pc = getattr(scene, "jerry_path", None)
    if pc is None or len(pc.path_points) <= 1:
        return []

    from .generate_slots_jerry import (
        WALK_STYLE_PARAMS as _WSP,
        SALTAR_SUBIR_FRAMES as _SSF,
        SALTAR_BAJAR_FRAMES as _SBF,
    )

    pts = list(pc.path_points)
    expanded_pts, frames_paradas_marcadas, _anim_files_est, _rot_est = _expand_points_with_paradas(pts)
    segs = _group_segments(expanded_pts)

    slots = []
    parada_idx  = 0
    caminar_idx = 0
    for i, seg in enumerate(segs, start=1):
        seg_type = seg["type"]
        slot_n   = pc.slot_inicio + i - 1
        if seg_type in ('saltar_subir','saltar_bajar','saltar_horizontal'):
            slots.append({'slot':slot_n,'tipo':seg_type,'frames_estimados':
                _jump.jump_frame_count(tuple(seg['points'][0].coords),tuple(seg['points'][-1].coords),
                    seg_type.removeprefix('saltar_'),scene.render.fps/scene.render.fps_base)})
        elif seg_type == "parada":
            if parada_idx < len(frames_paradas_marcadas):
                f_parada = frames_paradas_marcadas[parada_idx]
            elif parada_idx < len(pc.paradas_frames):
                f_parada = pc.paradas_frames[parada_idx].frames
            else:
                f_parada = pc.frames_parada
            slots.append({"slot": slot_n, "tipo": seg_type, "frames_estimados": f_parada})
            parada_idx += 1
        else:  # caminar
            seg_pts = seg["points"]
            d = sum(
                math.sqrt(
                    (seg_pts[k + 1].coords[0] - seg_pts[k].coords[0]) ** 2 +
                    (seg_pts[k + 1].coords[1] - seg_pts[k].coords[1]) ** 2
                ) for k in range(len(seg_pts) - 1)
            )
            walk_style = (pc.walk_styles[caminar_idx].style
                          if caminar_idx < len(pc.walk_styles) else pc.walk_style)
            style = _WSP.get(walk_style, _WSP['NORMAL'])
            est_f = max(24, round(d * pc.frames_por_bloque * style['speed_mult']))
            slots.append({"slot": slot_n, "tipo": seg_type, "frames_estimados": est_f})
            caminar_idx += 1

    return slots


def sync_paradas_frames(pc):
    """Sincroniza pc.paradas_frames con la cantidad real de paradas del
    recorrido actual (pc.path_points), preservando los valores que ya
    hayan sido editados a mano. Portado de Alfred
    (sync_paradas_frames), 2026-08-05.

    IMPORTANTE: esta funcion escribe en datos de la escena (agrega/quita
    items de una CollectionProperty) y por lo tanto NUNCA debe llamarse
    desde un metodo draw() de panel; Blender prohibe escribir en ID-data
    durante el dibujado. Debe invocarse solo desde operadores (execute())
    o desde el handler de depsgraph_update_post.

    Se llama automaticamente desde: JRRSTPR_OT_RemoveLast,
    JRRSTPR_OT_ClearPath, el handler _jerry_face_selection_handler (al
    agregar un punto nuevo), JRRSTPR_OT_PreviewPath y
    JRRSTPR_OT_ExportSlots. El panel solo LEE pc.paradas_frames y ofrece
    un boton manual (jerrypr.sync_paradas_frames) para forzar la
    sincronizacion en cualquier caso borde.

    Retorna la cantidad de paradas detectadas (int).
    """
    try:
        if len(pc.path_points) >= 2:
            expanded, _, _, _ = _expand_points_with_paradas(pc.path_points)
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
    """Sincroniza pc.walk_styles con la cantidad real de tramos 'caminar'
    del recorrido actual (pc.path_points), preservando los estilos que ya
    hayan sido elegidos a mano. Portado de Alfred (sync_walk_styles),
    2026-08-05 -- mismo patron que sync_paradas_frames() pero contando
    tramos 'caminar' en vez de 'parada'.

    IMPORTANTE: al igual que sync_paradas_frames(), escribe en datos de
    la escena (agrega/quita items de una CollectionProperty) y por lo
    tanto NUNCA debe llamarse desde un metodo draw() de panel -- solo
    desde operadores (execute()) o el handler de depsgraph_update_post.

    Se llama automaticamente desde los mismos puntos que
    sync_paradas_frames(): JRRSTPR_OT_RemoveLast, JRRSTPR_OT_ClearPath,
    el handler de seleccion de faces (al agregar un punto nuevo),
    JRRSTPR_OT_PreviewPath, JRRSTPR_OT_GenerateSlots y
    JRRSTPR_OT_ExportSlots.

    Retorna la cantidad de tramos 'caminar' detectados (int).
    """
    try:
        if len(pc.path_points) >= 2:
            expanded, _, _, _ = _expand_points_with_paradas(pc.path_points)
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
            # Tramo recien detectado: todavia no hay ningun keyframe real
            # que dependa de este estilo, asi que se marca de una la
            # "foto" para que el primer recalculo no dispare un cambio
            # espurio (mismo motivo que en Alfred).
            item.applied_style = item.style
    elif n_actual > n_caminar:
        for _ in range(n_actual - n_caminar):
            pc.walk_styles.remove(len(pc.walk_styles) - 1)

    return n_caminar


def sync_paradas_frames_from_segments(context):
    """Corrige el VALOR (no solo la cantidad) de cada entrada de
    pc.paradas_frames para que coincida con la duracion real que el
    segmento "parada" correspondiente tiene configurado en el Paso 3
    (scene.jerry_segs) -- la suma de las duraciones de sus action_poses
    (JerrySegmentPoseSlot.duration). Portado de Alfred
    (sync_paradas_frames_from_segments), adaptado a scene.jerry_segs /
    JerrySegmentPoseSlot.duration, 2026-08-05.

    Empareja cada entrada de pc.paradas_frames (en el orden en que las
    detecta _group_segments() sobre el recorrido actual) con el N-esimo
    segmento de jerry_segs cuyo label contenga "parada" (insensible a
    mayusculas), ordenados por frame_start -- mismo orden en que se
    crean. Si ese segmento tiene action_poses con duracion > 0, se
    sobreescribe pc.paradas_frames[i].frames con esa suma. Si no hay
    segmentos "parada" en jerry_segs (o no tienen poses aun), no se toca
    nada -- se conserva el valor existente (editado a mano o default).
    """
    pc = context.scene.jerry_path
    segs_data = getattr(context.scene, "jerry_segs", None)
    if segs_data is None or not len(pc.paradas_frames):
        return

    paradas_segs = sorted(
        (s for s in segs_data.segments if "parada" in (s.label or "").lower()),
        key=lambda s: s.frame_start,
    )

    for i, seg in enumerate(paradas_segs):
        if i >= len(pc.paradas_frames):
            break
        total = sum(int(getattr(p, "duration", 0)) for p in seg.action_poses)
        if total > 0:
            pc.paradas_frames[i].frames = total


def _pt_to_dict(pt, idx):
    return {
        "index": idx + 1,
        "tipo_segmento": getattr(pt,"tipo_segmento","AUTO"),
        "coordinates": {"x": round(pt.coords[0], 4),
                        "y": round(pt.coords[1], 4),
                        "z": round(pt.coords[2], 4)},
        "texture": pt.texture,
        "face_index": pt.face_index,
    }

# =============================================================================
# CODIGO COMUN — incrustado en cada slot generado
# =============================================================================

_HELPERS = '''
def _lerp(a, b, t):
    return a + (b - a) * t

def _clamp(t, lo=0.0, hi=1.0):
    return max(lo, min(hi, t))

def _smoothstep(t):
    t = _clamp(t)
    return t * t * (3 - 2 * t)

def _ease_out(t, exp=2):
    t = _clamp(t)
    return 1 - (1 - t) ** exp

def _ease_in(t, exp=2):
    t = _clamp(t)
    return t ** exp

def _phase_t(rf, start, end):
    if end == start:
        return 1.0
    return _clamp((rf - start) / (end - start))

def _micro(rf, freq=1.0, amp=1.0):
    return math.sin(rf * freq * 0.45 + 1.3) * amp
'''

_ROTATION_SMOOTHER = '''
class RotationSmoother:
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
        if abs(angle_diff) < 2:
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
        while a >  180: a -= 360
        while a < -180: a += 360
        return a

    def _diff(self, target, current):
        d = target - current
        while d >  180: d -= 360
        while d < -180: d += 360
        return d

    def _smoothstep(self, x):
        if x <= 0: return 0.0
        if x >= 1: return 1.0
        return x * x * (3.0 - 2.0 * x)
'''

_NLA_SETUP = '''
def _find_jerry_objects():
    root_empty    = bpy.data.objects.get('jerry')
    main_armature = bpy.data.objects.get('Dog_001_rig')
    if not root_empty or root_empty.type != 'EMPTY':
        print('ERROR: No se encontro EMPTY jerry'); return None, None
    if not main_armature or main_armature.type != 'ARMATURE':
        print('ERROR: No se encontro ARMATURE Dog_001_rig'); return None, None
    return root_empty, main_armature

def _get_pose_bones(main_armature):
    pb = main_armature.pose.bones
    bones = {
        'root':      pb.get('spine_6'),          # bone raiz del rig Jerry
        'body':      pb.get('spine_1'),
        'left_arm':  pb.get('front_shoulder.L'),
        'right_arm': pb.get('front_shoulder.R'),
        'left_leg':  pb.get('shoulder.L'),
        'right_leg': pb.get('shoulder.R'),
    }
    for name, bone in bones.items():
        if not bone:
            print(f'ERROR: bone {name} no encontrado'); return None
    return bones

def _setup_armature(main_armature, bones):
    bpy.context.view_layer.objects.active = main_armature
    if bpy.context.mode != 'POSE':
        bpy.ops.object.mode_set(mode='POSE')
    for bone in bones.values():
        bone.rotation_mode = 'XYZ'

def _create_dedicated_actions(root_empty, main_armature, slot_index, move_type):
    arm_action_name  = f'slot_{slot_index:03d}_jerry_{move_type}_arm'
    root_action_name = f'slot_{slot_index:03d}_jerry_{move_type}_root'
    if not main_armature.animation_data:
        main_armature.animation_data_create()
    existing = bpy.data.actions.get(arm_action_name)
    if existing: bpy.data.actions.remove(existing)
    arm_action = bpy.data.actions.new(name=arm_action_name)
    if not root_empty.animation_data:
        root_empty.animation_data_create()
    existing = bpy.data.actions.get(root_action_name)
    if existing: bpy.data.actions.remove(existing)
    root_action = bpy.data.actions.new(name=root_action_name)
    root_empty.animation_data.action = root_action
    return arm_action, root_action

def _push_actions_to_nla(root_empty, main_armature, arm_action, root_action,
                          slot_index, move_type, start_frame, end_frame):
    if main_armature.animation_data and main_armature.animation_data.action:
        for fc in _get_action_fcurves(arm_action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'
    if root_empty.animation_data and root_empty.animation_data.action:
        for fc in _get_action_fcurves(root_action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'
    _arm_track_name  = f'Slot_{slot_index:03d}_{move_type}_arm'
    _root_track_name = f'Slot_{slot_index:03d}_{move_type}_root'
    main_armature.animation_data.action = None
    _tracks_to_remove = [t for t in main_armature.animation_data.nla_tracks if t.name == _arm_track_name]
    for _t in _tracks_to_remove:
        main_armature.animation_data.nla_tracks.remove(_t)
    _arm_track = main_armature.animation_data.nla_tracks.new()
    _arm_track.name = _arm_track_name
    _arm_strip = _arm_track.strips.new(arm_action.name, start_frame, arm_action)
    _arm_strip.frame_end      = end_frame
    _arm_strip.extrapolation  = 'NOTHING'
    _arm_strip.use_auto_blend = False
    _arm_strip.blend_in       = 0
    _arm_strip.blend_out      = 0
    root_empty.animation_data.action = None
    _tracks_to_remove = [t for t in root_empty.animation_data.nla_tracks if t.name == _root_track_name]
    for _t in _tracks_to_remove:
        root_empty.animation_data.nla_tracks.remove(_t)
    _root_track = root_empty.animation_data.nla_tracks.new()
    _root_track.name = _root_track_name
    _root_strip = _root_track.strips.new(root_action.name, start_frame, root_action)
    _root_strip.frame_end      = end_frame
    _root_strip.extrapolation  = 'HOLD_FORWARD'
    _root_strip.use_auto_blend = False
    _root_strip.blend_in       = 0
    _root_strip.blend_out      = 0
'''

# =============================================================================
# BLOQUES DE CODIGO COMUN (embebidos en cada slot generado)
# =============================================================================

COMMON_MATH = '''
def sin_wave(frame, period, amplitude, phase=0, offset=0):
    return amplitude * math.sin(2 * math.pi * frame / period + phase) + offset

def cos_wave(frame, period, amplitude, phase=0, offset=0):
    return amplitude * math.cos(2 * math.pi * frame / period + phase) + offset

def lerp(start, end, t):
    return start + (end - start) * t

def ease_in_out(t):
    return t * t * (3 - 2 * t)

def ease_out(t):
    return 1 - (1 - t) * (1 - t)

def ease_in(t):
    return t * t
'''

DIRECTION_HELPERS = '''
def _compute_direction_angle(p0, p1):
    dx = p1['x'] - p0['x']
    dy = p1['y'] - p0['y']
    if dx == 0 and dy == 0:
        return None
    ang_raw = math.degrees(math.atan2(dx, dy))
    ang_rounded = round(ang_raw / 90.0) * 90.0
    ang = ang_rounded if abs(ang_raw - ang_rounded) < 45 else -ang_raw
    while ang >  180: ang -= 360
    while ang < -180: ang += 360
    if   ang ==  90: ang = -90
    elif ang == -90: ang =  90
    elif ang == 180: ang = -180
    return ang

def _smoothstep_val(x):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    return x * x * (3.0 - 2.0 * x)

def _angle_diff_shortest(target, current):
    d = target - current
    while d >  180: d -= 360
    while d < -180: d += 360
    return d
'''

BLINK_SYSTEM_BLOCK = '''
# ============================================================
# SISTEMA DE PARPADEO
# ============================================================

BLINK_SEQUENCE = {
    1: {"closed": 0.0,  "hide": False},
    2: {"closed": 0.25, "hide": False},
    3: {"closed": 0.5,  "hide": False},
    4: {"closed": 0.75, "hide": False},
    5: {"closed": 1.0,  "hide": True},
    6: {"closed": 1.0,  "hide": True},
    7: {"closed": 0.75, "hide": False},
    8: {"closed": 0.5,  "hide": False},
    9: {"closed": 0.25, "hide": False},
}

EYE_NAMES = ["ojo_izquierdo_jerry", "ojo_derecho_jerry"]


def _create_curtain_effect(eye_obj, shape_key):
    """Deforma la shape key bajando todos los vertices al minimo Z (efecto parpado)."""
    mesh    = eye_obj.data
    min_z   = min(v.co.z for v in mesh.vertices)
    for i, vert in enumerate(mesh.vertices):
        new_co     = vert.co.copy()
        new_co.z   = min_z
        shape_key.data[i].co = new_co


def setup_blink_shape_keys():
    """Crea Basis + Closed en los ojos si no existen. Seguro llamar multiples veces."""
    import bpy
    for obj_name in EYE_NAMES:
        eye_obj = bpy.data.objects.get(obj_name)
        if not eye_obj or eye_obj.type != "MESH":
            print(f"   setup_blink: WARNING \'{obj_name}\' no encontrado o no es MESH")
            continue
        if not eye_obj.data.shape_keys:
            eye_obj.shape_key_add(name="Basis", from_mix=False)
            print(f"   setup_blink: Basis creado en \'{obj_name}\'")
        existing = [sk.name for sk in eye_obj.data.shape_keys.key_blocks]
        if "Closed" not in existing:
            closed_key = eye_obj.shape_key_add(name="Closed", from_mix=False)
            _create_curtain_effect(eye_obj, closed_key)
            print(f"   setup_blink: Shape key \'Closed\' creada en \'{obj_name}\'")
        else:
            print(f"   setup_blink: \'Closed\' ya existe en \'{obj_name}\' -- OK")
'''

ROTATION_SMOOTHER_CLASS = '''
class RotationSmoother:
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
        if abs(angle_diff) < 2:
            self.previous_rotation = target_rotation
            self.transition_start_frame = None
            return target_rotation
        if self.transition_start_frame is None:
            self.transition_start_frame = current_frame
            self.transition_start_rotation = self.previous_rotation
            self.target_rotation = target_rotation
        elapsed  = current_frame - self.transition_start_frame
        progress = min(elapsed / self.smoothing_frames, 1.0)
        eased    = self._smoothstep(progress)
        smoothed = self.transition_start_rotation + self._diff(self.target_rotation, self.transition_start_rotation) * eased
        if progress >= 1.0:
            self.previous_rotation = target_rotation
            self.transition_start_frame = None
            return target_rotation
        return smoothed

    def _normalize(self, a):
        while a >  180: a -= 360
        while a < -180: a += 360
        return a

    def _diff(self, target, current):
        d = target - current
        while d >  180: d -= 360
        while d < -180: d += 360
        return d

    def _smoothstep(self, x):
        if x <= 0: return 0.0
        if x >= 1: return 1.0
        return x * x * (3.0 - 2.0 * x)
'''

# =============================================================================
# GENERADORES DE CODIGO DE SLOT
# =============================================================================

def _fmt_traj(points_dicts):
    lines = ["EMBEDDED_TRAJECTORY_POINTS = ["]
    for p in points_dicts:
        c = p["coordinates"]
        lines.append(
            f'    {{"index": {p["index"]}, '
            f'"coordinates": {{"x": {c["x"]}, "y": {c["y"]}, "z": {c["z"]}}}, '
            f'"texture": "{p.get("texture","")}"}},'
        )
    lines.append("]")
    return "\n".join(lines)

def _compute_direction_angle(p0c, p1c):
    dx = p1c["x"] - p0c["x"]
    dy = p1c["y"] - p0c["y"]
    if dx == 0 and dy == 0:
        return None
    ang_raw     = math.degrees(math.atan2(dx, dy))
    ang_rounded = round(ang_raw / 90.0) * 90.0
    ang = ang_rounded if abs(ang_raw - ang_rounded) < 45 else -ang_raw
    while ang >  180: ang -= 360
    while ang < -180: ang += 360
    if   ang ==  90: ang = -90
    elif ang == -90: ang =  90
    return ang


def _gen_saltar_subir(slot_index, start_frame, pts_dicts, root_rot, today):
    points = pts_dicts
    prev_rz = root_rot[2]
    total_frames = 15
    end_frame = start_frame + total_frames - 1
    p0 = points[0]['coordinates']
    p1 = points[1]['coordinates']
    traj = _fmt_traj(points)
    rx, ry, rz = root_rot

    # Posicion del parpadeo: 1 parpadeo al 50% del slot
    blink_start_val = start_frame + int(total_frames * 0.50)

    code = f'''# -*- coding: utf-8 -*-
"""
slot_{slot_index:03d}_saltar_subir.py
Jerry (perro) - Slot {slot_index}
GENERADO AUTOMATICAMENTE - {today}
Tipo: saltar_subir  |  Frames: {start_frame}-{end_frame}  ({total_frames} frames)
Trayectoria: punto {points[0]['index']} -> punto {points[1]['index']}
"""

import bpy
import math

SLOT_INDEX   = {slot_index}
START_FRAME  = {start_frame}
END_FRAME    = {end_frame}
TOTAL_FRAMES = {total_frames}

{traj}

ANIMATION_INFO = {{
    'name': 'slot_{slot_index:03d}_jerry_saltar_subir',
    'frame_count': {total_frames},
    'fps': 24,
    'duration_seconds': {total_frames/24:.3f},
    'entity': 'Jerry',
    'slot': {slot_index},
    'movement_type': 'saltar_subir',
}}
{COMMON_MATH}
{DIRECTION_HELPERS}
{BLINK_SYSTEM_BLOCK}

# --- Orientacion por trayectoria p0->p1 con suavizado ---
_p0c = {{'x': {p0['x']}, 'y': {p0['y']}, 'z': {p0['z']}}}
_p1c = {{'x': {p1['x']}, 'y': {p1['y']}, 'z': {p1['z']}}}
_dir_angle = _compute_direction_angle(_p0c, _p1c)
_base_rz   = {prev_rz}

def _build_rotation_data():
    data = {{}}
    target_rz = _dir_angle if _dir_angle is not None else _base_rz
    prev_rot   = _base_rz
    trans_start = None
    trans_start_rot = None
    smoothing = 6
    for frame in range({start_frame}, {end_frame + 1}):
        diff = _angle_diff_shortest(target_rz, prev_rot)
        if abs(diff) < 0.1:
            smoothed = target_rz; trans_start = None
        else:
            if trans_start is None:
                trans_start = frame; trans_start_rot = prev_rot
            elapsed  = frame - trans_start
            progress = min(elapsed / smoothing, 1.0)
            eased    = _smoothstep_val(progress)
            smoothed = trans_start_rot + _angle_diff_shortest(target_rz, trans_start_rot) * eased
            if progress >= 1.0:
                prev_rot = target_rz; trans_start = None
        data[frame] = (math.radians({rx}), math.radians({ry}), math.radians(smoothed))
    return data

ROOT_ROTATION_DATA = _build_rotation_data()

# ============================================================
# CLASE DE SALTO
# ============================================================

class DogJumpCycle:
    """Animacion de salto para perro - 15 frames"""
    def __init__(self, total_frames=15):
        self.total_frames = total_frames
        self.impulse_frames = (1, 5)
        self.jump_frames    = (6, 11)
        self.fall_frames    = (12, 15)

    def get_phase_progress(self, frame):
        for (s, e), phase in [(self.impulse_frames,'impulse'),(self.jump_frames,'jump'),(self.fall_frames,'fall')]:
            if s <= frame <= e:
                return phase, (frame - s) / max(1, e - s)
        return 'neutral', 0

    def rear_thigh(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        s = 1 if is_left else -1
        if ph == 'impulse':
            c = ease_in_out(pr)*0.20; return (-c, sin_wave(pr*6,6,0.03*s,0,0), sin_wave(pr*4,4,0.02,0,0))
        elif ph == 'jump':
            e = ease_out(pr)*0.25;   return (-e, sin_wave(pr*12,12,0.015*s,0,0), sin_wave(pr*10,10,0.025,0,0))
        elif ph == 'fall':
            t = ease_in(pr)*0.15;    return (-t, sin_wave(pr*8,8,0.01*s,0,0), sin_wave(pr*6,6,-0.01,0,0))
        return (0,0,0)

    def rear_shin(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        s = 1 if is_left else -1
        if ph == 'impulse': return (-ease_in_out(pr)*0.18, sin_wave(pr*8,8,0.02*s,0,0), sin_wave(pr*6,6,0.015,0,0))
        elif ph == 'jump':  return (-ease_out(pr)*0.22,    sin_wave(pr*12,12,0.01*s,0,0), sin_wave(pr*8,8,0.02,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.12,     sin_wave(pr*8,8,0.008*s,0,0), sin_wave(pr*4,4,0.01,0,0))
        return (0,0,0)

    def rear_foot(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        s = 1 if is_left else -1
        if ph == 'impulse': return (-ease_in_out(pr)*0.15, sin_wave(pr*12,12,0.03*s,0,0), sin_wave(pr*10,10,0.02,0,0))
        elif ph == 'jump':  return (-ease_out(pr)*0.18,    sin_wave(pr*25,25,0.02*s,0,0), sin_wave(pr*15,15,0.03,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.1,      sin_wave(pr*15,15,0.01*s,0,0), sin_wave(pr*8,8,0.015,0,0))
        return (0,0,0)

    def rear_toe(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': return (ease_in_out(pr)*0.12, 0, 0)
        elif ph == 'jump':  return (ease_out(pr)*0.08,    0, 0)
        elif ph == 'fall':  return (ease_in(pr)*0.05,     0, 0)
        return (0,0,0)

    def front_thigh(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        s = 1 if is_left else -1
        if ph == 'impulse': return (-ease_in_out(pr)*0.1,  sin_wave(pr*8,8,0.04*s,0,0), sin_wave(pr*6,6,-0.02,0,0))
        elif ph == 'jump':  return ( ease_out(pr)*0.35,    sin_wave(pr*15,15,0.03*s,0,0), sin_wave(pr*12,12,0.04,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.3,      sin_wave(pr*10,10,0.02*s,0,0), sin_wave(pr*8,8,0.02,0,0))
        return (0,0,0)

    def front_shin(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        s = 1 if is_left else -1
        if ph == 'impulse': return (-ease_in_out(pr)*0.15, sin_wave(pr*10,10,0.03*s,0,0), sin_wave(pr*8,8,-0.01,0,0))
        elif ph == 'jump':  return (-ease_out(pr)*0.25,    sin_wave(pr*20,20,0.02*s,0,0), sin_wave(pr*15,15,0.03,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.18,     sin_wave(pr*12,12,0.015*s,0,0), sin_wave(pr*10,10,0.02,0,0))
        return (0,0,0)

    def front_foot(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        s = 1 if is_left else -1
        if ph == 'impulse': return (-ease_in_out(pr)*0.12, sin_wave(pr*12,12,0.02*s,0,0), sin_wave(pr*8,8,-0.015,0,0))
        elif ph == 'jump':  return (-ease_out(pr)*0.2,     sin_wave(pr*18,18,0.015*s,0,0), sin_wave(pr*12,12,0.02,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.15,     sin_wave(pr*10,10,0.01*s,0,0), sin_wave(pr*6,6,0.01,0,0))
        return (0,0,0)

    def front_toe(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': return (ease_in_out(pr)*0.08, 0, 0)
        elif ph == 'jump':  return (ease_out(pr)*0.1,     0, 0)
        elif ph == 'fall':  return (ease_in(pr)*0.06,     0, 0)
        return (0,0,0)

    def spine_action(self, frame, segment, total_segments=7):
        ph, pr = self.get_phase_progress(frame)
        sf = segment / total_segments
        if ph == 'impulse': return (-ease_in_out(pr)*0.2*sf, sin_wave(pr*6,6,0.03*sf,0,0), ease_in_out(pr)*0.08*sf)
        elif ph == 'jump':  return ( ease_out(pr)*0.25*sf,   sin_wave(pr*10,10,0.02*sf,0,0), ease_out(pr)*0.12*sf)
        elif ph == 'fall':  return (-ease_in(pr)*0.15*sf,    sin_wave(pr*8,8,0.015*sf,0,0), ease_in(pr)*0.06*sf)
        return (0,0,0)

    def head_movement(self, frame):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': return (-ease_in_out(pr)*0.06, sin_wave(pr*8,8,0.03,0,0), sin_wave(pr*6,6,0.02,0,0))
        elif ph == 'jump':  return ( ease_out(pr)*0.08,    sin_wave(pr*12,12,0.04,0,0), sin_wave(pr*10,10,0.03,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.05,     sin_wave(pr*8,8,0.02,0,0), sin_wave(pr*6,6,0.015,0,0))
        return (0,0,0)

    def jaw_movement(self, frame):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': return (ease_in_out(pr)*0.03, 0, 0)
        elif ph == 'jump':  return (ease_out(pr)*0.04,    0, 0)
        elif ph == 'fall':  return (ease_in(pr)*0.02,     0, 0)
        return (0,0,0)

    def ear_movement(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        d = -1 if is_left else 1
        if ph == 'impulse': return (ease_in_out(pr)*0.05*d, sin_wave(pr*15,15,0.02,0,0), sin_wave(pr*12,12,0.015,0,0))
        elif ph == 'jump':  return (ease_out(pr)*0.06*d,    sin_wave(pr*20,20,0.025,0,0), sin_wave(pr*18,18,0.02,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.04*d,    sin_wave(pr*12,12,0.015,0,0), sin_wave(pr*10,10,0.01,0,0))
        return (0,0,0)

    def neck_movement(self, frame):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': return (-ease_in_out(pr)*0.04, sin_wave(pr*8,8,0.02,0,0), 0)
        elif ph == 'jump':  return ( ease_out(pr)*0.05,    sin_wave(pr*12,12,0.03,0,0), 0)
        elif ph == 'fall':  return (-ease_in(pr)*0.03,     sin_wave(pr*8,8,0.02,0,0), 0)
        return (0,0,0)

    def tail_movement(self, frame, segment):
        ph, pr = self.get_phase_progress(frame)
        sf = segment / 3
        if ph == 'impulse': return (-ease_in_out(pr)*0.15*sf, sin_wave(pr*25,25,0.06*sf,0,0), sin_wave(pr*20,20,0.04*sf,0,0))
        elif ph == 'jump':  return ( ease_out(pr)*0.25*sf,    sin_wave(pr*40,40,0.1*sf,0,0), sin_wave(pr*35,35,0.08*sf,0,0))
        elif ph == 'fall':  return ( ease_in(pr)*0.15*sf,     sin_wave(pr*25,25,0.05*sf,0,0), sin_wave(pr*20,20,0.03*sf,0,0))
        return (0,0,0)


def generate_jump_keyframes():
    jump = DogJumpCycle(total_frames={total_frames})
    kf = {{}}
    for frame in range({start_frame}, {end_frame + 1}):
        lf = frame - {start_frame} + 1
        kf.setdefault('thigh.L', {{}})[frame]        = jump.rear_thigh(lf, True)
        kf.setdefault('thigh.R', {{}})[frame]        = jump.rear_thigh(lf, False)
        kf.setdefault('shin.L', {{}})[frame]         = jump.rear_shin(lf, True)
        kf.setdefault('shin.R', {{}})[frame]         = jump.rear_shin(lf, False)
        kf.setdefault('foot.L', {{}})[frame]         = jump.rear_foot(lf, True)
        kf.setdefault('foot.R', {{}})[frame]         = jump.rear_foot(lf, False)
        kf.setdefault('toe.L', {{}})[frame]          = jump.rear_toe(lf, True)
        kf.setdefault('toe.R', {{}})[frame]          = jump.rear_toe(lf, False)
        kf.setdefault('front_thigh.L', {{}})[frame]  = jump.front_thigh(lf, True)
        kf.setdefault('front_thigh.R', {{}})[frame]  = jump.front_thigh(lf, False)
        kf.setdefault('front_shin.L', {{}})[frame]   = jump.front_shin(lf, True)
        kf.setdefault('front_shin.R', {{}})[frame]   = jump.front_shin(lf, False)
        kf.setdefault('front_foot.L', {{}})[frame]   = jump.front_foot(lf, True)
        kf.setdefault('front_foot.R', {{}})[frame]   = jump.front_foot(lf, False)
        kf.setdefault('front_toe.L', {{}})[frame]    = jump.front_toe(lf, True)
        kf.setdefault('front_toe.R', {{}})[frame]    = jump.front_toe(lf, False)
        for i in range(1, 8):
            kf.setdefault(f'spine_{{i}}', {{}})[frame] = jump.spine_action(lf, i, 7)
        kf.setdefault('neck', {{}})[frame]   = jump.neck_movement(lf)
        kf.setdefault('scull', {{}})[frame]  = jump.head_movement(lf)
        kf.setdefault('scull_1', {{}})[frame]= jump.head_movement(lf)
        kf.setdefault('jaw_top', {{}})[frame]= jump.jaw_movement(lf)
        kf.setdefault('ear.L', {{}})[frame]  = jump.ear_movement(lf, True)
        kf.setdefault('ear.R', {{}})[frame]  = jump.ear_movement(lf, False)
        for i in range(1, 4):
            kf.setdefault(f'tail_{{i}}', {{}})[frame] = jump.tail_movement(lf, i)
    return kf


def execute_animation(player_parts, start_frame=START_FRAME, end_frame=END_FRAME):
    start_frame = START_FRAME
    end_frame   = END_FRAME

    # --- Root jerry ---
    root = next((o for o in bpy.data.objects if o.name.lower() == 'jerry'), None)
    if not root:
        root = next((o for o in bpy.data.objects if 'jerry' in o.name.lower() and o.type in ('EMPTY','ARMATURE')), None)
    if not root:
        print("ERROR: No se encontro el empty 'jerry'"); return False

    # --- Armature (hijo del root jerry) ---
    armature = next((o for o in bpy.data.objects if o.type == 'ARMATURE' and o.parent == root), None)
    if not armature:
        armature = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
    if not armature:
        print("ERROR: No se encontro el Armature"); return False

    # ============================================
    # SETUP DE ACCIONES NLA
    # ============================================
    _arm_action_name  = f'slot_{{{slot_index}:03d}}_jerry_saltar_subir_arm'
    _root_action_name = f'slot_{{{slot_index}:03d}}_jerry_saltar_subir_root'

    if not armature.animation_data:
        armature.animation_data_create()
    _arm_existing = bpy.data.actions.get(_arm_action_name)
    if _arm_existing:
        bpy.data.actions.remove(_arm_existing)
    _arm_action = bpy.data.actions.new(name=_arm_action_name)
    armature.animation_data.action = _arm_action

    if not root.animation_data:
        root.animation_data_create()
    _root_existing = bpy.data.actions.get(_root_action_name)
    if _root_existing:
        bpy.data.actions.remove(_root_existing)
    _root_action = bpy.data.actions.new(name=_root_action_name)
    root.animation_data.action = _root_action

    bpy.context.view_layer.objects.active = armature
    if armature.mode != 'POSE':
        bpy.ops.object.mode_set(mode='POSE')
    for bone in armature.pose.bones:
        bone.rotation_mode = 'XYZ'

    # --- Keyframes de salto ---
    jump_kf = generate_jump_keyframes()
    bones_applied = 0
    for bone_name, fd in jump_kf.items():
        bone = armature.pose.bones.get(bone_name)
        if not bone: continue
        bone.rotation_mode = 'XYZ'
        for frame, val in fd.items():
            if isinstance(val, dict):
                if 'rotation' in val:
                    bone.rotation_euler = val['rotation']
                    bone.keyframe_insert(data_path="rotation_euler", frame=frame)
                if 'location' in val:
                    bone.location = val['location']
                    bone.keyframe_insert(data_path="location", frame=frame)
            else:
                bone.rotation_euler = val
                bone.keyframe_insert(data_path="rotation_euler", frame=frame)
        bones_applied += 1

    # --- Parabolica + rotacion root ---
    p_start = EMBEDDED_TRAJECTORY_POINTS[0]['coordinates']
    p_end   = EMBEDDED_TRAJECTORY_POINTS[1]['coordinates']

    for t in range(start_frame, end_frame + 1):
        lf = t - start_frame + 1
        f  = (lf - 1) / max(1, TOTAL_FRAMES - 1)
        x  = p_start['x'] + (p_end['x'] - p_start['x']) * f
        y  = p_start['y'] + (p_end['y'] - p_start['y']) * f
        z  = p_start['z'] + (p_end['z'] - p_start['z']) * f + 4.0 * 0.75 * f * (1 - f)
        rot = ROOT_ROTATION_DATA.get(t, (0, 0, math.radians({rz})))
        bpy.context.scene.frame_set(t)
        root.location = (x, y, z)
        root.rotation_euler = rot
        root.keyframe_insert(data_path="location", frame=t)
        root.keyframe_insert(data_path="rotation_euler", frame=t)

    # --- Sistema de parpadeo ---
    blink_start = {blink_start_val}
    setup_blink_shape_keys()
    for t in range(start_frame, end_frame + 1):
        blink_applied = False
        if blink_start <= t < blink_start + 9:
            blink_applied = True
            offset     = t - blink_start + 1
            frame_data = BLINK_SEQUENCE.get(offset, {{"closed": 0.0, "hide": False}})
            progress   = frame_data["closed"]
            hide_eye   = frame_data["hide"]
            for eye_name in EYE_NAMES:
                eye = bpy.data.objects.get(eye_name)
                if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                    ck = eye.data.shape_keys.key_blocks.get("Closed")
                    if ck:
                        ck.value = progress
                        ck.keyframe_insert(data_path='value', frame=t)
                        eye.hide_viewport = hide_eye
                        eye.hide_render   = hide_eye
                        eye.keyframe_insert(data_path="hide_viewport", frame=t)
                        eye.keyframe_insert(data_path="hide_render",   frame=t)
        if not blink_applied:
            for eye_name in EYE_NAMES:
                eye = bpy.data.objects.get(eye_name)
                if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                    ck = eye.data.shape_keys.key_blocks.get("Closed")
                    if ck:
                        ck.value = 0.0
                        ck.keyframe_insert(data_path='value', frame=t)
                        eye.hide_viewport = False
                        eye.hide_render   = False
                        eye.keyframe_insert(data_path="hide_viewport", frame=t)
                        eye.keyframe_insert(data_path="hide_render",   frame=t)

    print(f"Slot {{SLOT_INDEX}} saltar_subir completado: {{bones_applied}} bones, {{TOTAL_FRAMES}} frames")

    # ============================================
    # EMPUJAR ACCIONES AL NLA
    # ============================================
    if armature.animation_data and armature.animation_data.action:
        _arm_done  = armature.animation_data.action
        armature.animation_data.action = None
        _arm_track = armature.animation_data.nla_tracks.new()
        _arm_track.name = f'Slot_{{{slot_index}:03d}}_arm'
        _arm_strip = _arm_track.strips.new(_arm_done.name, start_frame, _arm_done)
        _arm_strip.frame_end      = end_frame
        _arm_strip.extrapolation  = 'NOTHING'
        _arm_strip.use_auto_blend = False
        _arm_strip.blend_in       = 0
        _arm_strip.blend_out      = 0

    if root.animation_data and root.animation_data.action:
        _root_done  = root.animation_data.action
        root.animation_data.action = None
        _root_track = root.animation_data.nla_tracks.new()
        _root_track.name = f'Slot_{{{slot_index}:03d}}_root'
        _root_strip = _root_track.strips.new(_root_done.name, start_frame, _root_done)
        _root_strip.frame_end      = end_frame
        _root_strip.extrapolation  = 'HOLD_FORWARD'
        _root_strip.use_auto_blend = False
        _root_strip.blend_in       = 0
        _root_strip.blend_out      = 0

    return True


if __name__ == "__main__":
    execute_animation({{}}, START_FRAME, END_FRAME)
'''
    return code, end_frame


# ============================================================
# GENERADOR: SALTAR BAJAR  (24 frames, QuadrupedWalkPlainCycle)
# ============================================================

def _gen_saltar_bajar(slot_index, start_frame, pts_dicts, root_rot, today):
    points = pts_dicts
    prev_rz = root_rot[2]
    total_frames = 24
    end_frame = start_frame + total_frames - 1
    # Para slots de ensamblaje, las coordenadas serán ajustadas por ensamblar_secuencia.py
    # Usamos coordenadas dummy que serán reemplazadas
    p0 = points[0]['coordinates'] if len(points) > 0 else {'x': 0, 'y': 0, 'z': 0}
    p1 = points[1]['coordinates'] if len(points) > 1 else {'x': 0, 'y': 0, 'z': 0}
    traj = _fmt_traj(points)
    rx, ry, rz = root_rot

    # Posicion del parpadeo: 1 parpadeo al 50% del slot
    blink_start_val = start_frame + int(total_frames * 0.50)

    code = f'''# -*- coding: utf-8 -*-
"""
slot_{slot_index:03d}_saltar_bajar.py
Jerry (perro) - Slot {slot_index}
GENERADO AUTOMATICAMENTE - {today}
Tipo: saltar_bajar  |  Frames: {start_frame}-{end_frame}  ({total_frames} frames)
Trayectoria: punto {points[0]['index']} -> punto {points[1]['index']}
"""

import bpy
import math

SLOT_INDEX   = {slot_index}
START_FRAME  = {start_frame}
END_FRAME    = {end_frame}
TOTAL_FRAMES = {total_frames}

{traj}

ANIMATION_INFO = {{
    'name': 'slot_{slot_index:03d}_jerry_saltar_bajar',
    'frame_count': {total_frames},
    'fps': 24,
    'duration_seconds': {total_frames/24:.3f},
    'entity': 'Jerry',
    'slot': {slot_index},
    'movement_type': 'saltar_bajar',
}}
{COMMON_MATH}
{DIRECTION_HELPERS}
{BLINK_SYSTEM_BLOCK}

# --- Orientacion por trayectoria p0->p1 ---
_p0c = {{'x': {p0['x']}, 'y': {p0['y']}, 'z': {p0['z']}}}
_p1c = {{'x': {p1['x']}, 'y': {p1['y']}, 'z': {p1['z']}}}
_dir_angle = _compute_direction_angle(_p0c, _p1c)
_base_rz   = {prev_rz}

def _build_rotation_data():
    data = {{}}
    target_rz = _dir_angle if _dir_angle is not None else _base_rz
    prev_rot = _base_rz; trans_start = None; trans_start_rot = None; smoothing = 8
    for frame in range({start_frame}, {end_frame + 1}):
        diff = _angle_diff_shortest(target_rz, prev_rot)
        if abs(diff) < 0.1:
            smoothed = target_rz; trans_start = None
        else:
            if trans_start is None: trans_start = frame; trans_start_rot = prev_rot
            elapsed  = frame - trans_start
            progress = min(elapsed / smoothing, 1.0)
            eased    = _smoothstep_val(progress)
            smoothed = trans_start_rot + _angle_diff_shortest(target_rz, trans_start_rot) * eased
            if progress >= 1.0: prev_rot = target_rz; trans_start = None
        data[frame] = (math.radians({rx}), math.radians({ry}), math.radians(smoothed))
    return data

ROOT_ROTATION_DATA = _build_rotation_data()

# ============================================================
# CLASE DE SALTO DESCENDENTE
# ============================================================

class QuadrupedWalkPlainCycle:
    def __init__(self, total_frames={total_frames}):
        self.total_frames = total_frames
        self.impulse_frames  = (1, 6)
        self.jump_frames     = (7, 14)
        self.fall_frames     = (15, 21)
        self.recovery_frames = (22, total_frames)

    def get_phase_progress(self, frame):
        for (s, e), ph in [(self.impulse_frames,'impulse'),(self.jump_frames,'jump'),
                           (self.fall_frames,'fall'),(self.recovery_frames,'recovery')]:
            if s <= frame <= e:
                return ph, (frame - s) / max(1, e - s)
        return 'neutral', 0

    def get_leg_rotation(self, frame, is_rear=False, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse':
            a = ease_in_out(pr)*(0.2 if is_rear else 0.15); return (-a, sin_wave(pr*15,15,0.01,0,0), sin_wave(pr*10,10,0.005,0,0))
        elif ph == 'jump':
            e = 0.15 if is_rear else 0.08; return (-e, sin_wave(pr*20,20,0.02,0,0), 0)
        elif ph == 'fall':
            if pr < 0.1: return (0, sin_wave(pr*12,12,0.01,0,0), sin_wave(pr*10,10,0.005,0,0))
            ap = (pr-0.1)/0.9; r = ease_out(ap)*(0.35 if is_rear else 0.2); b = 0.4 if is_rear else 0.25
            return (-b+r, sin_wave(pr*12,12,0.01,0,0), sin_wave(pr*10,10,0.005,0,0))
        return (0,0,0)

    def spine_jump_down(self, frame, segment, total_segments=7):
        ph, pr = self.get_phase_progress(frame)
        sf = segment / total_segments
        if ph == 'impulse': return (ease_in_out(pr)*0.1*sf, 0, 0)
        elif ph == 'jump':  return (-ease_out(pr)*0.25*sf, 0, 0)
        elif ph == 'fall':  x = -0.25*sf + ease_out(pr)*0.3*sf; return (x, 0, 0)
        return (0,0,0)

    def tail_jump_down(self, frame, segment):
        ph, pr = self.get_phase_progress(frame)
        sf = segment / 3
        if ph == 'impulse': return (ease_in_out(pr)*0.1*sf, sin_wave(pr*20,20,0.015,segment*3.14/6,0), sin_wave(frame,30,0.008,segment*3.14/8,0))
        elif ph == 'jump':  return (-ease_out(pr)*0.25*sf,  sin_wave(pr*25,25,0.025,segment*3.14/4,0), sin_wave(frame,30,0.008,segment*3.14/8,0))
        elif ph == 'fall':  x = -0.25*sf + ease_out(pr)*0.25*sf; return (x, sin_wave(pr*15,15,0.015,segment*3.14/3,0), sin_wave(frame,30,0.008,segment*3.14/8,0))
        return (0,0,sin_wave(frame,30,0.008,segment*3.14/8,0))

    def head_jump_down(self, frame):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': return (ease_in_out(pr)*0.02, sin_wave(pr*12,12,0.005,0,0), 0)
        elif ph == 'jump':  return (-ease_out(pr)*0.04,   sin_wave(pr*18,18,0.008,0,0), 0)
        elif ph == 'fall':  return (-0.04+ease_out(pr)*0.04, sin_wave(pr*10,10,0.005,0,0), 0)
        return (0,0,0)

    def ear_jump_down(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': a = ease_in_out(pr)*0.02; return (a if is_left else -a, sin_wave(pr*15,15,0.005,0,0), sin_wave(frame,25,0.003,0,0))
        elif ph == 'jump':  b = ease_out(pr)*0.03;    return (-b if is_left else b, sin_wave(pr*20,20,0.008,0.78,0), sin_wave(frame,25,0.003,0,0))
        elif ph == 'fall':  c = (-0.03+ease_out(pr)*0.03) if is_left else (0.03-ease_out(pr)*0.03); return (c, sin_wave(pr*12,12,0.005,0,0), sin_wave(frame,25,0.003,0,0))
        return (0,0,sin_wave(frame,25,0.003,0,0))

    def sombrero_jump_down(self, frame):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': return (ease_in_out(pr)*0.015, sin_wave(frame,20,0.004,0,0), sin_wave(frame,25,0.006,0.52,0))
        elif ph == 'jump':  return (-ease_out(pr)*0.04,    sin_wave(frame,20,0.004,0,0), sin_wave(frame,25,0.006,0.52,0))
        elif ph == 'fall':  return (-0.04+ease_out(pr)*0.04, sin_wave(frame,20,0.004,0,0), sin_wave(frame,25,0.006,0.52,0))
        return (0, sin_wave(frame,20,0.004,0,0), sin_wave(frame,25,0.006,0.52,0))

    def body_translation(self, frame):
        ph, pr = self.get_phase_progress(frame)
        p0 = EMBEDDED_TRAJECTORY_POINTS[0]['coordinates']
        p1 = EMBEDDED_TRAJECTORY_POINTS[1]['coordinates']
        if ph == 'impulse':   return (p0['x'], p0['y'], p0['z'])
        elif ph == 'jump':    return (p0['x']+(p1['x']-p0['x'])*pr, p0['y']+(p1['y']-p0['y'])*pr, p0['z']+(p1['z']-p0['z'])*pr)
        else:                 return (p1['x'], p1['y'], p1['z'])


def generate_keyframes(total_frames={total_frames}):
    cyc = QuadrupedWalkPlainCycle(total_frames=total_frames)
    kf  = {{}}
    for frame in range(1, total_frames + 1):
        ph, _ = cyc.get_phase_progress(frame)
        for side, is_l in [('L', True), ('R', False)]:
            kf.setdefault(f'shoulder.{{side}}', {{}})[frame] = tuple(x*(0.2 if ph=='impulse' else (-x if ph=='fall' else 1)*1) for x in cyc.get_leg_rotation(frame, True, is_l)) if ph in ('impulse',) else (tuple(-x for x in cyc.get_leg_rotation(frame, True, is_l)) if ph == 'fall' else cyc.get_leg_rotation(frame, True, is_l))
            kf.setdefault(f'thigh.{{side}}', {{}})[frame]    = tuple(x*0.5 for x in cyc.get_leg_rotation(frame, True, is_l))
            kf.setdefault(f'shin.{{side}}', {{}})[frame]     = cyc.get_leg_rotation(frame, True, is_l)
            kf.setdefault(f'foot.{{side}}', {{}})[frame]     = tuple(x*0.8 for x in cyc.get_leg_rotation(frame, True, is_l))
            kf.setdefault(f'toe.{{side}}', {{}})[frame]      = tuple(x*0.6 for x in cyc.get_leg_rotation(frame, True, is_l))
            fs = tuple(-x for x in cyc.get_leg_rotation(frame, False, is_l)) if ph == 'fall' else cyc.get_leg_rotation(frame, False, is_l)
            kf.setdefault(f'front_shoulder.{{side}}', {{}})[frame] = fs
            kf.setdefault(f'front_thigh.{{side}}', {{}})[frame]    = tuple(x*0.4 for x in cyc.get_leg_rotation(frame, False, is_l))
            kf.setdefault(f'front_shin.{{side}}', {{}})[frame]     = cyc.get_leg_rotation(frame, False, is_l)
            kf.setdefault(f'front_foot.{{side}}', {{}})[frame]     = tuple(x*0.7 for x in cyc.get_leg_rotation(frame, False, is_l))
            kf.setdefault(f'front_toe.{{side}}', {{}})[frame]      = tuple(x*0.5 for x in cyc.get_leg_rotation(frame, False, is_l))
        for i in range(1, 8):
            kf.setdefault(f'spine_{{i}}', {{}})[frame] = cyc.spine_jump_down(frame, i, 7)
        for i in range(1, 4):
            kf.setdefault(f'tail_{{i}}', {{}})[frame] = cyc.tail_jump_down(frame, i)
        kf.setdefault('scull', {{}})[frame]   = cyc.head_jump_down(frame)
        kf.setdefault('scull_1', {{}})[frame] = tuple(x*0.5 for x in cyc.head_jump_down(frame))
        kf.setdefault('jaw_top', {{}})[frame] = (0,0,0)
        kf.setdefault('ear.L', {{}})[frame]   = cyc.ear_jump_down(frame, True)
        kf.setdefault('ear.R', {{}})[frame]   = cyc.ear_jump_down(frame, False)
        kf.setdefault('sombrero', {{}})[frame]= cyc.sombrero_jump_down(frame)
    return kf


def execute_animation(player_parts, start_frame=START_FRAME, end_frame=END_FRAME):
    start_frame = START_FRAME; end_frame = END_FRAME

    root = next((o for o in bpy.data.objects if o.name.lower() == 'jerry'), None)
    if not root:
        root = next((o for o in bpy.data.objects if 'jerry' in o.name.lower() and o.type in ('EMPTY','ARMATURE')), None)
    if not root:
        print("ERROR: No se encontro el empty 'jerry'"); return False

    armature = next((o for o in bpy.data.objects if o.type == 'ARMATURE' and o.parent == root), None)
    if not armature:
        armature = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
    if not armature:
        print("ERROR: No se encontro el Armature"); return False

    # ============================================
    # SETUP DE ACCIONES NLA
    # ============================================
    _arm_action_name  = f'slot_{{{slot_index}:03d}}_jerry_saltar_bajar_arm'
    _root_action_name = f'slot_{{{slot_index}:03d}}_jerry_saltar_bajar_root'

    if not armature.animation_data:
        armature.animation_data_create()
    _arm_existing = bpy.data.actions.get(_arm_action_name)
    if _arm_existing:
        bpy.data.actions.remove(_arm_existing)
    _arm_action = bpy.data.actions.new(name=_arm_action_name)
    armature.animation_data.action = _arm_action

    if not root.animation_data:
        root.animation_data_create()
    _root_existing = bpy.data.actions.get(_root_action_name)
    if _root_existing:
        bpy.data.actions.remove(_root_existing)
    _root_action = bpy.data.actions.new(name=_root_action_name)
    root.animation_data.action = _root_action

    bpy.context.view_layer.objects.active = armature
    if armature.mode != 'POSE': bpy.ops.object.mode_set(mode='POSE')
    for bone in armature.pose.bones: bone.rotation_mode = 'XYZ'

    kf_data = generate_keyframes(TOTAL_FRAMES)
    bones_applied = 0
    cyc = QuadrupedWalkPlainCycle(total_frames=TOTAL_FRAMES)
    for bone_name, fd in kf_data.items():
        bone = armature.pose.bones.get(bone_name)
        if not bone: continue
        bone.rotation_mode = 'XYZ'
        for frame, val in fd.items():
            adj = START_FRAME + (frame - 1)
            bone.rotation_euler = val
            bone.keyframe_insert(data_path="rotation_euler", frame=adj)
        bones_applied += 1

    for frame in range(1, TOTAL_FRAMES + 1):
        adj = START_FRAME + (frame - 1)
        pos = cyc.body_translation(frame)
        rot = ROOT_ROTATION_DATA.get(adj, (0, 0, math.radians({rz})))
        bpy.context.scene.frame_set(adj)
        root.location = pos
        root.rotation_euler = rot
        root.keyframe_insert(data_path="location", frame=adj)
        root.keyframe_insert(data_path="rotation_euler", frame=adj)

    # --- Sistema de parpadeo ---
    blink_start = {blink_start_val}
    setup_blink_shape_keys()
    for t in range(start_frame, end_frame + 1):
        blink_applied = False
        if blink_start <= t < blink_start + 9:
            blink_applied = True
            offset     = t - blink_start + 1
            frame_data = BLINK_SEQUENCE.get(offset, {{"closed": 0.0, "hide": False}})
            progress   = frame_data["closed"]
            hide_eye   = frame_data["hide"]
            for eye_name in EYE_NAMES:
                eye = bpy.data.objects.get(eye_name)
                if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                    ck = eye.data.shape_keys.key_blocks.get("Closed")
                    if ck:
                        ck.value = progress
                        ck.keyframe_insert(data_path='value', frame=t)
                        eye.hide_viewport = hide_eye
                        eye.hide_render   = hide_eye
                        eye.keyframe_insert(data_path="hide_viewport", frame=t)
                        eye.keyframe_insert(data_path="hide_render",   frame=t)
        if not blink_applied:
            for eye_name in EYE_NAMES:
                eye = bpy.data.objects.get(eye_name)
                if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                    ck = eye.data.shape_keys.key_blocks.get("Closed")
                    if ck:
                        ck.value = 0.0
                        ck.keyframe_insert(data_path='value', frame=t)
                        eye.hide_viewport = False
                        eye.hide_render   = False
                        eye.keyframe_insert(data_path="hide_viewport", frame=t)
                        eye.keyframe_insert(data_path="hide_render",   frame=t)

    print(f"Slot {{SLOT_INDEX}} saltar_bajar completado: {{bones_applied}} bones, {{TOTAL_FRAMES}} frames")

    # ============================================
    # EMPUJAR ACCIONES AL NLA
    # ============================================
    if armature.animation_data and armature.animation_data.action:
        _arm_done  = armature.animation_data.action
        armature.animation_data.action = None
        _arm_track = armature.animation_data.nla_tracks.new()
        _arm_track.name = f'Slot_{{{slot_index}:03d}}_arm'
        _arm_strip = _arm_track.strips.new(_arm_done.name, start_frame, _arm_done)
        _arm_strip.frame_end      = end_frame
        _arm_strip.extrapolation  = 'NOTHING'
        _arm_strip.use_auto_blend = False
        _arm_strip.blend_in       = 0
        _arm_strip.blend_out      = 0

    if root.animation_data and root.animation_data.action:
        _root_done  = root.animation_data.action
        root.animation_data.action = None
        _root_track = root.animation_data.nla_tracks.new()
        _root_track.name = f'Slot_{{{slot_index}:03d}}_root'
        _root_strip = _root_track.strips.new(_root_done.name, start_frame, _root_done)
        _root_strip.frame_end      = end_frame
        _root_strip.extrapolation  = 'HOLD_FORWARD'
        _root_strip.use_auto_blend = False
        _root_strip.blend_in       = 0
        _root_strip.blend_out      = 0

    return True


if __name__ == "__main__":
    execute_animation({{}}, START_FRAME, END_FRAME)
'''
    return code, end_frame


# ============================================================
# GENERADOR: PARADA  (root inmovil, canvas limpio para poses de segmento)
# ============================================================
#
# Portado de Alfred (generate_parada / _gen_parada), 2026-08-05: el root
# se detiene por completo en una coordenada elegida por el usuario (dropdown
# "Tipo" en la lista del Paso 1, ver JRRSTPathPoint.tipo_segmento), para
# dejar un hueco donde tenga sentido animar una accion puntual via el
# sistema de poses del Paso 3, en vez de forzarla sobre una caminata en
# curso.
#
# A diferencia de saltar_subir/saltar_bajar/caminar, una parada NO anima
# ningun ciclo de bones -- fuerza todos los bones de IDLE_POSE_PARADA
# (misma pose de rest "parado" que usa generate_idle() en
# generate_slots_jerry.py, ver parado.json / Dog_001_rig) durante todo el
# rango, para que el canvas quede limpio y el sistema de poses (Paso 3)
# tenga donde superponer su propia animacion sin heredar la ultima pose
# congelada del segmento anterior.
FRAMES_PARADA_DEFAULT = 60

IDLE_POSE_PARADA = {
    "spine_6":          (1.0,      0.0,       0.0,       0.0     ),
    "shoulder.R":       (1.0,      0.0,       0.0,       0.0     ),
    "thigh.R":          (0.998338,-0.025782,  0.042195,  0.029608),
    "shin.R":           (0.994427, 0.015862,  0.082995, -0.063043),
    "foot.R":           (0.996655, 0.081519, -0.005796, -0.000377),
    "toe.R":            (0.999005,-0.040315,  0.017105,  0.008429),
    "spine_7":          (1.0,      0.0,       0.0,       0.0     ),
    "tail_1":           (1.0,      0.0,       0.0,       0.0     ),
    "tail_2":           (1.0,      0.0,       0.0,       0.0     ),
    "tail_3":           (1.0,      0.0,       0.0,       0.0     ),
    "spine_5":          (1.0,      0.0,       0.0,       0.0     ),
    "spine_4":          (1.0,      0.0,       0.0,       0.0     ),
    "spine_3":          (1.0,      0.0,       0.0,       0.0     ),
    "spine_2":          (1.0,      0.0,       0.0,       0.0     ),
    "spine_1":          (1.0,      0.0,       0.0,       0.0     ),
    "scull_1":          (1.0,      0.0,       0.0,       0.0     ),
    "scull":            (0.999945, 0.010519,  0.0,       0.0     ),
    "ear.R":            (1.0,      0.0,       0.0,       0.0     ),
    "ear.L":            (0.999945, 0.002396,  0.009347,  0.004159),
    "jaw_top":          (0.999955,-0.009430,  0.0,       0.0     ),
    "jaw_bot":          (1.0,      0.0,       0.0,       0.0     ),
    "sombrero":         (1.0,      0.0,       0.0,       0.0     ),
    "front_shoulder.R": (1.0,      0.0,       0.0,       0.0     ),
    "front_thigh.R":    (0.999326, 0.000806, -0.019173,  0.031282),
    "front_shin.R":     (0.999651,-0.026395, -0.001057, -0.000234),
    "front_foot.R":     (0.997441, 0.045186,  0.018651, -0.052181),
    "front_toe.R":      (1.0,      0.0,       0.0,       0.0     ),
    "front_shoulder.L": (1.0,      0.0,       0.0,       0.0     ),
    "front_thigh.L":    (0.999276, 0.006675,  0.019077, -0.032223),
    "front_shin.L":     (0.989825,-0.018532,  0.141046, -0.003009),
    "front_foot.L":     (0.999560, 0.022467, -0.018879, -0.004336),
    "front_toe.L":      (0.990863, 0.003916, -0.008821,  0.134525),
    "shoulder.L":       (1.0,      0.0,       0.0,       0.0     ),
    "thigh.L":          (1.0,      0.0,       0.0,       0.0     ),
    "shin.L":           (0.998899,-0.039855,  0.001751,  0.024680),
    "foot.L":           (1.0,      0.0,       0.0,       0.0     ),
    "toe.L":            (0.967064, 0.102424, -0.212854,  0.094812),
}


def _gen_parada(slot_index, start_frame, pts_dicts, root_rot, today, frames_parada=None):
    """Genera un slot de 'parada': root inmovil `frames_parada` frames, con
    los bones forzados a la pose de rest "parado" (IDLE_POSE_PARADA) --
    canvas limpio para la pose que superponga el Paso 3.

    `frames_parada`: sin limite -- cualquier entero >= 1. Si no se pasa
    (None), usa FRAMES_PARADA_DEFAULT como fallback.

    `pts_dicts` debe ser una lista de 2 puntos IDENTICOS (misma x/y/z) --
    exactamente lo que produce _group_segments() cuando _detect_move()
    devuelve "parada".
    """
    points = pts_dicts
    # FIX (Kebyn, 2026-09-24): el script generado llamaba a
    # `_get_action_fcurves(action)` sin definir ni la funcion ni `action`
    # (NameError apenas se ejecutaba el slot). Se pega el bloque autonomo
    # de generate_slots_jerry.FCURVES_COMPAT_BLOCK y se usan las Actions
    # reales del armature / root -- ver {FCURVES_COMPAT_BLOCK} en la plantilla.
    from .generate_slots_jerry import FCURVES_COMPAT_BLOCK
    total_frames = frames_parada if frames_parada is not None else FRAMES_PARADA_DEFAULT
    end_frame = start_frame + total_frames - 1
    p0 = points[0]['coordinates'] if len(points) > 0 else {'x': 0, 'y': 0, 'z': 0}
    p1 = points[1]['coordinates'] if len(points) > 1 else p0
    traj = _fmt_traj(points)
    rx, ry, rz = root_rot

    # Posicion del parpadeo: 1 parpadeo al 50% del slot
    blink_start_val = start_frame + int(total_frames * 0.50)

    code = f'''# -*- coding: utf-8 -*-
"""
slot_{slot_index:03d}_jerry_parada.py
Jerry (perro) - Slot {slot_index}
GENERADO AUTOMATICAMENTE - {today}
Tipo: parada  |  Frames: {start_frame}-{end_frame}  ({total_frames} frames)

NOTA: este slot mantiene el root inmovil y fuerza todos los bones
animables a la postura base "parado" (Dog_001_rig, IDLE_POSE) durante
todo el rango -- canvas limpio para que el Paso 3 superponga su pose,
sin heredar la ultima pose congelada del segmento anterior.
"""

import bpy
import math
from mathutils import Quaternion

SLOT_INDEX   = {slot_index}
START_FRAME  = {start_frame}
END_FRAME    = {end_frame}
TOTAL_FRAMES = {total_frames}

{traj}

ANIMATION_INFO = {{
    'name': 'slot_{slot_index:03d}_jerry_parada',
    'frame_count': {total_frames},
    'fps': 24,
    'duration_seconds': {total_frames/24:.3f},
    'entity': 'Jerry',
    'slot': {slot_index},
    'movement_type': 'parada',
    'animation_type': 'stop_hold_reset',
}}
{COMMON_MATH}
{FCURVES_COMPAT_BLOCK}
{BLINK_SYSTEM_BLOCK}

ROOT_LOCATION_DATA = {{
    {start_frame}: ({p0['x']}, {p0['y']}, {p0['z']}),
    {end_frame}:   ({p1['x']}, {p1['y']}, {p1['z']}),
}}
ROOT_ROTATION_X = {rx}
ROOT_ROTATION_Y = {ry}
ROOT_ROTATION_Z = {rz}   # sin trayecto (parada) -> orientacion base, fija
ROOT_ROTATION_DATA = {{
    {start_frame}: (math.radians({rx}), math.radians({ry}), math.radians({rz})),
    {end_frame}:   (math.radians({rx}), math.radians({ry}), math.radians({rz})),
}}

IDLE_POSE = {IDLE_POSE_PARADA!r}


def execute_animation(player_parts, start_frame=START_FRAME, end_frame=END_FRAME):
    start_frame = START_FRAME; end_frame = END_FRAME

    root = next((o for o in bpy.data.objects if o.name.lower() == 'jerry'), None)
    if not root:
        root = next((o for o in bpy.data.objects if 'jerry' in o.name.lower() and o.type in ('EMPTY','ARMATURE')), None)
    if not root:
        print("ERROR: No se encontro el empty 'jerry'"); return False

    armature = next((o for o in bpy.data.objects if o.type == 'ARMATURE' and o.parent == root), None)
    if not armature:
        armature = bpy.data.objects.get("Dog_001_rig")
    if not armature:
        armature = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
    if not armature:
        print("ERROR: No se encontro el Armature"); return False

    # ============================================
    # SETUP DE ACCIONES NLA -- BONES A LA POSE "PARADO" (canvas limpio)
    # ============================================
    _arm_action_name  = f'slot_{{SLOT_INDEX:03d}}_jerry_parada_arm'
    _root_action_name = f'slot_{{SLOT_INDEX:03d}}_jerry_parada_root'

    if not armature.animation_data:
        armature.animation_data_create()
    _arm_existing = bpy.data.actions.get(_arm_action_name)
    if _arm_existing:
        bpy.data.actions.remove(_arm_existing)
    _arm_action = bpy.data.actions.new(name=_arm_action_name)
    armature.animation_data.action = _arm_action

    bpy.context.view_layer.objects.active = armature
    if armature.mode != 'POSE': bpy.ops.object.mode_set(mode='POSE')

    bones_applied = 0
    for bname, (qw, qx, qy, qz) in IDLE_POSE.items():
        b = armature.pose.bones.get(bname)
        if b is None:
            continue
        b.rotation_mode = 'XYZ'
        b.rotation_euler = Quaternion((qw, qx, qy, qz)).to_euler('XYZ')
        b.keyframe_insert(data_path='rotation_euler', frame=START_FRAME)
        b.keyframe_insert(data_path='rotation_euler', frame=END_FRAME)
        bones_applied += 1

    if armature.animation_data.action:
        for fcurve in _get_action_fcurves(armature.animation_data.action):
            for kp in fcurve.keyframe_points:
                kp.interpolation = 'CONSTANT'   # hold en la pose "parado", sin transicion

    print(f"   {{bones_applied}} bones puestos en postura 'parado' para canvas limpio")

    # ============================================
    # SETUP DE ACCION NLA -- SOLO ROOT
    # ============================================
    if not root.animation_data:
        root.animation_data_create()
    _root_existing = bpy.data.actions.get(_root_action_name)
    if _root_existing:
        bpy.data.actions.remove(_root_existing)
    _root_action = bpy.data.actions.new(name=_root_action_name)
    root.animation_data.action = _root_action

    for frame, rotation in ROOT_ROTATION_DATA.items():
        root.rotation_euler = rotation
        root.keyframe_insert(data_path="rotation_euler", frame=frame)
    for frame, location in ROOT_LOCATION_DATA.items():
        root.location = location
        root.keyframe_insert(data_path="location", frame=frame)

    if root.animation_data.action:
        for fcurve in _get_action_fcurves(root.animation_data.action):
            for kp in fcurve.keyframe_points:
                kp.interpolation = 'CONSTANT'   # es un hold, no una transicion

    print("PARADA APLICADA -- root inmovil, bones en postura 'parado'")
    print(f"  Frames: {{start_frame}}-{{end_frame}}")

    # --- Sistema de parpadeo ---
    blink_start = {blink_start_val}
    setup_blink_shape_keys()
    for t in range(start_frame, end_frame + 1):
        blink_applied = False
        if blink_start <= t < blink_start + 9:
            blink_applied = True
            offset     = t - blink_start + 1
            frame_data = BLINK_SEQUENCE.get(offset, {{"closed": 0.0, "hide": False}})
            progress   = frame_data["closed"]
            hide_eye   = frame_data["hide"]
            for eye_name in EYE_NAMES:
                eye = bpy.data.objects.get(eye_name)
                if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                    ck = eye.data.shape_keys.key_blocks.get("Closed")
                    if ck:
                        ck.value = progress
                        ck.keyframe_insert(data_path='value', frame=t)
                        eye.hide_viewport = hide_eye
                        eye.hide_render   = hide_eye
                        eye.keyframe_insert(data_path="hide_viewport", frame=t)
                        eye.keyframe_insert(data_path="hide_render",   frame=t)
        if not blink_applied:
            for eye_name in EYE_NAMES:
                eye = bpy.data.objects.get(eye_name)
                if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                    ck = eye.data.shape_keys.key_blocks.get("Closed")
                    if ck:
                        ck.value = 0.0
                        ck.keyframe_insert(data_path='value', frame=t)
                        eye.hide_viewport = False
                        eye.hide_render   = False
                        eye.keyframe_insert(data_path="hide_viewport", frame=t)
                        eye.keyframe_insert(data_path="hide_render",   frame=t)

    # ============================================
    # EMPUJAR ACCIONES AL NLA
    # ============================================
    if armature.animation_data and armature.animation_data.action:
        _arm_done  = armature.animation_data.action
        armature.animation_data.action = None
        _arm_track = armature.animation_data.nla_tracks.new()
        _arm_track.name = f'Slot_{{SLOT_INDEX:03d}}_parada_arm'
        _arm_strip = _arm_track.strips.new(_arm_done.name, start_frame, _arm_done)
        _arm_strip.frame_end      = end_frame
        _arm_strip.extrapolation  = 'NOTHING'
        _arm_strip.use_auto_blend = False
        _arm_strip.blend_in       = 0
        _arm_strip.blend_out      = 0

    if root.animation_data and root.animation_data.action:
        _root_done  = root.animation_data.action
        root.animation_data.action = None
        _root_track = root.animation_data.nla_tracks.new()
        _root_track.name = f'Slot_{{SLOT_INDEX:03d}}_parada_root'
        _root_strip = _root_track.strips.new(_root_done.name, start_frame, _root_done)
        _root_strip.frame_end      = end_frame
        _root_strip.extrapolation  = 'HOLD_FORWARD'
        _root_strip.use_auto_blend = False
        _root_strip.blend_in       = 0
        _root_strip.blend_out      = 0

    return True


if __name__ == "__main__":
    execute_animation({{}}, START_FRAME, END_FRAME)
'''
    return code, end_frame


# ============================================================
# GENERADOR: CAMINAR  (140 frames, SniffingSearchCycle)
# ============================================================

def _gen_caminar(slot_index, start_frame, pts_dicts, root_rot, today, frames_por_bloque=32,
                  walk_style='NORMAL'):
    from .generate_slots_jerry import WALK_STYLE_PARAMS as _WSP
    style = _WSP.get(walk_style, _WSP['NORMAL'])
    _rm = style['range_mult']
    points = pts_dicts
    prev_rz = root_rot[2]
    # Calcular total_frames basado en distancia (como el original), ahora
    # escalado por el speed_mult del estilo elegido (portado de Alfred,
    # 2026-08-05 -- ver WALK_STYLE_PARAMS en generate_slots_jerry.py).
    dist_total = 0.0
    for i in range(len(points) - 1):
        c0 = points[i]["coordinates"]; c1 = points[i + 1]["coordinates"]
        dx = c1["x"] - c0["x"]; dy = c1["y"] - c0["y"]; dz = c1["z"] - c0["z"]
        dist_total += math.sqrt(dx*dx + dy*dy + dz*dz)
    fpb_efectivo = frames_por_bloque * style['speed_mult']
    total_frames = max(24, round(dist_total * fpb_efectivo))
    end_frame = start_frame + total_frames - 1
    n_pts = len(points)
    traj = _fmt_traj(points)
    idx_start = points[0]['index']
    idx_end = points[-1]['index']
    rx, ry, rz = root_rot

    code = f'''# -*- coding: utf-8 -*-
"""
slot_{slot_index:03d}_caminar.py
Jerry (perro) - Slot {slot_index}
GENERADO AUTOMATICAMENTE - {today}
Tipo: caminar  |  Frames: {start_frame}-{end_frame}  ({total_frames} frames)
Trayectoria: punto {idx_start} -> punto {idx_end}  ({n_pts} puntos)
"""

import bpy
import math

SLOT_INDEX   = {slot_index}
START_FRAME  = {start_frame}
END_FRAME    = {end_frame}
TOTAL_FRAMES = {total_frames}

ROOT_ROTATION_X = {rx}
ROOT_ROTATION_Y = {ry}
ROOT_ROTATION_Z = {prev_rz}

{traj}

ANIMATION_INFO = {{
    'name': 'slot_{slot_index:03d}_jerry_caminar',
    'frame_count': {total_frames},
    'fps': 24,
    'duration_seconds': {total_frames/24:.3f},
    'entity': 'Jerry',
    'slot': {slot_index},
    'movement_type': 'caminar',
    'walk_style': '{walk_style}',
}}

# ============================================================
# ESTILO DE CAMINATA (multiplexor) — Kebyn, 2026-08-05
# ============================================================
WALK_STYLE      = "{walk_style}"                # NORMAL/LENTO/HERIDO/RAPIDO/CORRER/CORRER_2
CYCLE_LENGTH    = {max(4, round(25 * style['cycle_mult']))}                  # frames por ciclo de zancada (base 25)
RANGE_MULT      = {{'leg': {_rm['leg']:.4f}, 'spine': {_rm['spine']:.4f}, 'tail': {_rm['tail']:.4f}, 'head': {_rm['head']:.4f}, 'ear': {_rm['ear']:.4f}}}
VERTICAL_BOB    = {style['vertical_bob']}                # metros, rebote vertical extra del root
ASYM_REAR_LEG   = {style['asym_rear_leg']}              # 0.0-1.0, debilita pata trasera derecha (cojera, solo HERIDO)
{COMMON_MATH}
{DIRECTION_HELPERS}
{BLINK_SYSTEM_BLOCK}

# ============================================================
# SISTEMA DE SUAVIZADO DE ROTACION
# ============================================================
{ROTATION_SMOOTHER_CLASS}

def _compute_direction_angle_local(p0, p1):
    dx = p1[0]-p0[0]; dy = p1[1]-p0[1]
    if dx == 0 and dy == 0: return None
    ang_raw = math.degrees(math.atan2(dx, dy))
    ang_rounded = round(ang_raw/90.0)*90.0
    ang = ang_rounded if abs(ang_raw-ang_rounded) < 45 else -ang_raw
    while ang >  180: ang -= 360
    while ang < -180: ang += 360
    if   ang ==  90: ang = -90
    elif ang == -90: ang =  90
    if ang == 180: ang = -180
    return ang

def _get_segment_angle_for_frame(segments, frames_per_seg, cum_frames, frame):
    prev = 0
    for j, cf in enumerate(cum_frames):
        if frame <= cf:
            ang = _compute_direction_angle_local(segments[j]['start'], segments[j]['end'])
            return ang if ang is not None else ROOT_ROTATION_Z
        prev = cf
    ang = _compute_direction_angle_local(segments[-1]['start'], segments[-1]['end'])
    return ang if ang is not None else ROOT_ROTATION_Z

_rotation_smoother = RotationSmoother(smoothing_frames=12)

# ============================================================
# CICLO DE CAMINATA CUADRUPEDO (SniffingSearchCycle)
# ============================================================

class SniffingSearchCycle:
    # NUEVO (portado de Alfred, Kebyn 2026-08-05): range_mult/asym_rear
    # aplican el estilo de caminata elegido (RANGE_MULT/ASYM_REAR_LEG
    # arriba) sobre la MISMA formula base -- no se duplica el ciclo por
    # estilo, solo se escala su amplitud.
    def __init__(self, cycle_length=25, total_frames=100, range_mult=None, asym_rear=0.0):
        self.cycle_length  = cycle_length
        self.total_frames  = total_frames
        self.rm   = range_mult or {{'leg': 1.0, 'spine': 1.0, 'tail': 1.0, 'head': 1.0, 'ear': 1.0}}
        self.asym = asym_rear  # 0.0-1.0, debilita la pata trasera derecha (cojera)

    def normalize_frame(self, frame):
        return ((frame - 1) % self.cycle_length) + 1

    def sniff_down(self, frame):
        n = self.normalize_frame(frame)
        return (sin_wave(n, self.cycle_length, 0.03 * self.rm['head'], 0, 0), 0, 0)

    def look_around(self, frame):
        n = self.normalize_frame(frame)
        return (0, sin_wave(n, self.cycle_length, 0.05 * self.rm['head'], 0, 0), 0)

    def head_tilt(self, frame):
        n = self.normalize_frame(frame)
        return (0, 0, sin_wave(n, self.cycle_length, 0.016 * self.rm['head'], 0, 0))

    def ear_twitch(self, frame):
        n = self.normalize_frame(frame)
        return (0, sin_wave(n, self.cycle_length, 0.2 * self.rm['ear'], 0, 0), sin_wave(n, self.cycle_length, 0.1 * self.rm['ear'], 0, 0))

    def tail_wag_alert(self, frame):
        n = self.normalize_frame(frame)
        t = self.rm['tail']
        return (sin_wave(n, self.cycle_length, 0.4*t, 0, 0.2*t), sin_wave(n, self.cycle_length, 0.06*t, 0, 0), sin_wave(n, self.cycle_length, 0.16*t, 0, 0))

    def leg_slow_walk(self, frame, is_rear=False, is_left=True):
        n = self.normalize_frame(frame)
        phase = 0 if is_left else math.pi
        amp   = (0.4 if is_rear else 0.3) * self.rm['leg']
        if is_rear and not is_left:
            amp *= (1.0 - self.asym)
        return (-sin_wave(n, self.cycle_length, amp, phase, 0),
                -sin_wave(n, self.cycle_length, amp*0.15, phase, 0),
                -sin_wave(n, self.cycle_length, amp*0.03, phase, 0))

    def leg_bend(self, frame, is_rear=False, is_left=True):
        n = self.normalize_frame(frame)
        phase = 0 if is_left else math.pi
        bb    = (0.3 if is_rear else 0.24) * self.rm['leg']
        if is_rear and not is_left:
            bb *= (1.0 - self.asym)
        return (-abs(sin_wave(n, self.cycle_length, bb, phase, bb)),
                -sin_wave(n, self.cycle_length, 0.1, phase, 0),
                -sin_wave(n, self.cycle_length, 0.04, phase, 0))

    def foot_strike(self, frame, is_rear=False, is_left=True):
        n = self.normalize_frame(frame)
        phase = 0 if is_left else math.pi
        amp_x = (0.8 if is_rear else 0.6) * self.rm['leg']
        if is_rear and not is_left:
            amp_x *= (1.0 - self.asym)
        x = -sin_wave(n, self.cycle_length, amp_x, phase, 0.4 if is_rear else -0.1)
        y = abs(sin_wave(n, self.cycle_length, 0.04, phase, 0.02)) * (1.0 if is_rear else 0.5)
        z = -sin_wave(n, self.cycle_length, 0.04 if is_rear else 0.06, phase, 0.02)
        return (x, y, z)

    def toe_curl(self, frame, is_rear=False, is_left=True):
        n = self.normalize_frame(frame)
        phase = 0 if is_left else math.pi
        amp = 0.5 * self.rm['leg']
        if is_rear and not is_left:
            amp *= (1.0 - self.asym)
        return (abs(sin_wave(n, self.cycle_length, amp, phase, 0.4)),
                -sin_wave(n, self.cycle_length, 0.16, phase, 0),
                -sin_wave(n, self.cycle_length, 0.08, phase, 0.04))

    def spine_undulation(self, frame, segment, total_segments=7):
        n = self.normalize_frame(frame)
        ph = (segment / total_segments) * math.pi
        return (-sin_wave(n, self.cycle_length, 0.03 * self.rm['spine'], ph, -0.08 * self.rm['spine']), 0, 0)

    def vertical_bob(self, frame):
        n = self.normalize_frame(frame)
        bob = VERTICAL_BOB * (0.5 - 0.5 * math.cos(2 * math.pi * n / self.cycle_length * 2))
        if self.asym > 0.0:
            bob += max(0.0, math.sin(2 * math.pi * n / self.cycle_length)) * VERTICAL_BOB * self.asym
        return bob


def generate_keyframes(total_frames=140):
    cl    = min(CYCLE_LENGTH, max(4, total_frames))
    cycle = SniffingSearchCycle(cycle_length=cl, total_frames=total_frames,
                                 range_mult=RANGE_MULT, asym_rear=ASYM_REAR_LEG)
    kf    = {{}}
    for frame in range(1, total_frames + 1):
        kf.setdefault('shoulder.L', {{}})[frame] = cycle.leg_slow_walk(frame, True, True)
        kf.setdefault('shoulder.R', {{}})[frame] = cycle.leg_slow_walk(frame, True, False)
        kf.setdefault('thigh.L', {{}})[frame]    = tuple(x*0.01  for x in cycle.leg_slow_walk(frame, True, True))
        kf.setdefault('thigh.R', {{}})[frame]    = tuple(x*-0.3  for x in cycle.leg_slow_walk(frame, True, False))
        kf.setdefault('shin.L', {{}})[frame]     = cycle.leg_bend(frame, True, True)
        kf.setdefault('shin.R', {{}})[frame]     = cycle.leg_bend(frame, True, False)
        kf.setdefault('foot.L', {{}})[frame]     = cycle.foot_strike(frame, True, True)
        kf.setdefault('foot.R', {{}})[frame]     = cycle.foot_strike(frame, True, False)
        kf.setdefault('toe.L', {{}})[frame]      = cycle.toe_curl(frame, True, True)
        kf.setdefault('toe.R', {{}})[frame]      = cycle.toe_curl(frame, True, False)
        kf.setdefault('front_shoulder.L', {{}})[frame] = cycle.leg_slow_walk(frame+12, False, True)
        kf.setdefault('front_shoulder.R', {{}})[frame] = cycle.leg_slow_walk(frame+12, False, False)
        kf.setdefault('front_thigh.L', {{}})[frame]    = tuple(x*0.6 for x in cycle.leg_slow_walk(frame+12, False, True))
        kf.setdefault('front_thigh.R', {{}})[frame]    = tuple(x*0.4 for x in cycle.leg_slow_walk(frame+12, False, False))
        kf.setdefault('front_shin.L', {{}})[frame]     = cycle.leg_bend(frame+12, False, True)
        kf.setdefault('front_shin.R', {{}})[frame]     = cycle.leg_bend(frame+12, False, False)
        kf.setdefault('front_foot.L', {{}})[frame]     = cycle.foot_strike(frame+12, False, True)
        kf.setdefault('front_foot.R', {{}})[frame]     = cycle.foot_strike(frame+12, False, False)
        kf.setdefault('front_toe.L', {{}})[frame]      = cycle.toe_curl(frame+12, False, True)
        kf.setdefault('front_toe.R', {{}})[frame]      = cycle.toe_curl(frame+12, False, False)
        for i in range(1, 8):
            kf.setdefault(f'spine_{{i}}', {{}})[frame] = cycle.spine_undulation(frame, i, 7)
        for i in range(1, 4):
            kf.setdefault(f'tail_{{i}}', {{}})[frame] = cycle.tail_wag_alert(frame)
        sniff = cycle.sniff_down(frame); look = cycle.look_around(frame); tilt = cycle.head_tilt(frame)
        kf.setdefault('scull', {{}})[frame]   = (sniff[0]+tilt[0]*0.3, look[1], tilt[2])
        kf.setdefault('jaw_top', {{}})[frame] = (0.224, 0, 0)
        kf.setdefault('ear.L', {{}})[frame]   = cycle.ear_twitch(frame)
        kf.setdefault('ear.R', {{}})[frame]   = cycle.ear_twitch(frame+6)
        kf.setdefault('sombrero', {{}})[frame]= (0, 0, 0)
    return kf


def _load_segments():
    pts  = EMBEDDED_TRAJECTORY_POINTS
    segs = []
    for i in range(len(pts)-1):
        s = pts[i]['coordinates']; e = pts[i+1]['coordinates']
        segs.append({{'start':[s['x'],s['y'],s['z']], 'end':[e['x'],e['y'],e['z']], 'texture': pts[i].get('texture','grass_block_top')}})
    return segs

def _compute_frames_allocation(segments, total_frames):
    dists = []
    for seg in segments:
        s,e = seg['start'],seg['end']
        dx,dy,dz = e[0]-s[0],e[1]-s[1],e[2]-s[2]
        dists.append(max(0.0001, math.sqrt(dx*dx+dy*dy+dz*dz)))
    total_dist = sum(dists) or 1.0
    bf = [max(1,int(round(total_frames*(d/total_dist)))) for d in dists]
    diff = total_frames - sum(bf); i = 0
    while diff != 0:
        if diff > 0: bf[i%len(bf)] += 1; diff -= 1
        else:
            if bf[i%len(bf)] > 1: bf[i%len(bf)] -= 1; diff += 1
        i += 1
    cum = []; acc = 0
    for f in bf: acc += f; cum.append(acc)
    return bf, cum

def _get_position_for_frame(segments, frames_per_seg, cum_frames, frame):
    prev = 0
    for j, cf in enumerate(cum_frames):
        if frame <= cf:
            s,e = segments[j]['start'],segments[j]['end']
            steps = max(1, frames_per_seg[j]); local = frame - prev
            f = max(0.0, min(1.0, local/steps))
            return (s[0]+(e[0]-s[0])*f, s[1]+(e[1]-s[1])*f, s[2]+(e[2]-s[2])*f)
        prev = cf
    return tuple(segments[-1]['end'])


def execute_animation(player_parts, start_frame=START_FRAME, end_frame=END_FRAME):
    start_frame = START_FRAME; end_frame = END_FRAME

    root = next((o for o in bpy.data.objects if o.name.lower() == 'jerry'), None)
    if not root:
        root = next((o for o in bpy.data.objects if 'jerry' in o.name.lower() and o.type in ('EMPTY','ARMATURE')), None)
    if not root:
        print("ERROR: No se encontro el empty 'jerry'"); return False

    armature = next((o for o in bpy.data.objects if o.type == 'ARMATURE' and o.parent == root), None)
    if not armature:
        armature = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
    if not armature:
        print("ERROR: No se encontro el Armature"); return False

    # ============================================
    # SETUP DE ACCIONES NLA
    # ============================================
    _arm_action_name  = f'slot_{{{slot_index}:03d}}_jerry_caminar_arm'
    _root_action_name = f'slot_{{{slot_index}:03d}}_jerry_caminar_root'

    if not armature.animation_data:
        armature.animation_data_create()
    _arm_existing = bpy.data.actions.get(_arm_action_name)
    if _arm_existing:
        bpy.data.actions.remove(_arm_existing)
    _arm_action = bpy.data.actions.new(name=_arm_action_name)
    armature.animation_data.action = _arm_action

    if not root.animation_data:
        root.animation_data_create()
    _root_existing = bpy.data.actions.get(_root_action_name)
    if _root_existing:
        bpy.data.actions.remove(_root_existing)
    _root_action = bpy.data.actions.new(name=_root_action_name)
    root.animation_data.action = _root_action

    bpy.context.view_layer.objects.active = armature
    if armature.mode != 'POSE': bpy.ops.object.mode_set(mode='POSE')
    for bone in armature.pose.bones: bone.rotation_mode = 'XYZ'

    kf_data = generate_keyframes(TOTAL_FRAMES)
    bones_applied = 0
    for bone_name, fd in kf_data.items():
        bone = armature.pose.bones.get(bone_name)
        if not bone: continue
        bone.rotation_mode = 'XYZ'
        for frame, rot in fd.items():
            adj = START_FRAME + (frame - 1)
            bone.rotation_euler = rot
            bone.keyframe_insert(data_path="rotation_euler", frame=adj)
        bones_applied += 1

    segments = _load_segments()
    frames_per_seg, cum_global = _compute_frames_allocation(segments, TOTAL_FRAMES)

    # Parpadeos al 25% y 75% del slot
    slot_duration = end_frame - start_frame + 1
    blink_starts  = [start_frame + int(slot_duration * 0.25), start_frame + int(slot_duration * 0.75)]

    setup_blink_shape_keys()

    # Ciclo auxiliar SOLO para el rebote vertical del root (VERTICAL_BOB)
    _bob_cycle = SniffingSearchCycle(cycle_length=min(CYCLE_LENGTH, max(4, TOTAL_FRAMES)),
                                      total_frames=TOTAL_FRAMES, asym_rear=ASYM_REAR_LEG)

    for t in range(start_frame, end_frame + 1):
        path_frame  = t - start_frame + 1
        pos         = _get_position_for_frame(segments, frames_per_seg, cum_global, min(path_frame, TOTAL_FRAMES))
        seg_ang     = _get_segment_angle_for_frame(segments, frames_per_seg, cum_global, path_frame)
        smoothed_ang= _rotation_smoother.smooth_rotation(seg_ang, t)

        bpy.context.scene.frame_set(t)
        if VERTICAL_BOB > 0.0:
            _bob = _bob_cycle.vertical_bob(min(path_frame, TOTAL_FRAMES))
            pos = (pos[0], pos[1], pos[2] + _bob)
        root.location       = pos
        root.rotation_euler = (math.radians(ROOT_ROTATION_X), math.radians(ROOT_ROTATION_Y), math.radians(smoothed_ang))
        root.keyframe_insert(data_path="location",       frame=t)
        root.keyframe_insert(data_path="rotation_euler", frame=t)

        blink_applied = False
        for blink_start in blink_starts:
            if blink_start <= t < blink_start + 9:
                blink_applied = True
                offset     = t - blink_start + 1
                frame_data = BLINK_SEQUENCE.get(offset, {{"closed": 0.0, "hide": False}})
                progress   = frame_data["closed"]
                hide_eye   = frame_data["hide"]
                for eye_name in EYE_NAMES:
                    eye = bpy.data.objects.get(eye_name)
                    if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                        ck = eye.data.shape_keys.key_blocks.get("Closed")
                        if ck:
                            ck.value = progress
                            ck.keyframe_insert(data_path='value', frame=t)
                            eye.hide_viewport = hide_eye
                            eye.hide_render   = hide_eye
                            eye.keyframe_insert(data_path="hide_viewport", frame=t)
                            eye.keyframe_insert(data_path="hide_render",   frame=t)
                break
        if not blink_applied:
            for eye_name in EYE_NAMES:
                eye = bpy.data.objects.get(eye_name)
                if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                    ck = eye.data.shape_keys.key_blocks.get("Closed")
                    if ck:
                        ck.value = 0.0
                        ck.keyframe_insert(data_path='value', frame=t)
                        eye.hide_viewport = False
                        eye.hide_render   = False
                        eye.keyframe_insert(data_path="hide_viewport", frame=t)
                        eye.keyframe_insert(data_path="hide_render",   frame=t)

    print(f"Slot {{SLOT_INDEX}} caminar completado: {{bones_applied}} bones, {{TOTAL_FRAMES}} frames")

    # ============================================
    # EMPUJAR ACCIONES AL NLA
    # ============================================
    if armature.animation_data and armature.animation_data.action:
        _arm_done  = armature.animation_data.action
        armature.animation_data.action = None
        _arm_track = armature.animation_data.nla_tracks.new()
        _arm_track.name = f'Slot_{{{slot_index}:03d}}_arm'
        _arm_strip = _arm_track.strips.new(_arm_done.name, start_frame, _arm_done)
        _arm_strip.frame_end      = end_frame
        _arm_strip.extrapolation  = 'NOTHING'
        _arm_strip.use_auto_blend = False
        _arm_strip.blend_in       = 0
        _arm_strip.blend_out      = 0

    if root.animation_data and root.animation_data.action:
        _root_done  = root.animation_data.action
        root.animation_data.action = None
        _root_track = root.animation_data.nla_tracks.new()
        _root_track.name = f'Slot_{{{slot_index}:03d}}_root'
        _root_strip = _root_track.strips.new(_root_done.name, start_frame, _root_done)
        _root_strip.frame_end      = end_frame
        _root_strip.extrapolation  = 'HOLD_FORWARD'
        _root_strip.use_auto_blend = False
        _root_strip.blend_in       = 0
        _root_strip.blend_out      = 0

    return True


if __name__ == "__main__":
    execute_animation({{}}, START_FRAME, END_FRAME)
'''
    return code, end_frame



# ─────────────────────────────────────────────────────────────────────────────
# Helpers matemáticos para clases de ciclo (alias sin prefijo)
# ─────────────────────────────────────────────────────────────────────────────
def sin_wave(frame, period, amplitude, phase=0, offset=0):
    return amplitude * math.sin(2 * math.pi * frame / period + phase) + offset

def cos_wave(frame, period, amplitude, phase=0, offset=0):
    return amplitude * math.cos(2 * math.pi * frame / period + phase) + offset

def lerp(start, end, t):
    return start + (end - start) * t

def ease_in_out(t):
    return t * t * (3 - 2 * t)

def ease_out(t):
    return 1 - (1 - t) * (1 - t)

def ease_in(t):
    return t * t


# =============================================================================
# CLASES DE CICLO — definidas al nivel de módulo para preview en tiempo real
# =============================================================================

class DogJumpCycle:
    """Animacion de salto para perro - 15 frames"""
    def __init__(self, total_frames=15):
        self.total_frames = total_frames
        self.impulse_frames = (1, 5)
        self.jump_frames    = (6, 11)
        self.fall_frames    = (12, 15)

    def get_phase_progress(self, frame):
        for (s, e), phase in [(self.impulse_frames,'impulse'),(self.jump_frames,'jump'),(self.fall_frames,'fall')]:
            if s <= frame <= e:
                return phase, (frame - s) / max(1, e - s)
        return 'neutral', 0

    def rear_thigh(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        s = 1 if is_left else -1
        if ph == 'impulse': c = ease_in_out(pr)*0.20; return (-c, sin_wave(pr*6,6,0.03*s,0,0), sin_wave(pr*4,4,0.02,0,0))
        elif ph == 'jump':  e = ease_out(pr)*0.25;   return (-e, sin_wave(pr*12,12,0.015*s,0,0), sin_wave(pr*10,10,0.025,0,0))
        elif ph == 'fall':  t = ease_in(pr)*0.15;    return (-t, sin_wave(pr*8,8,0.01*s,0,0), sin_wave(pr*6,6,-0.01,0,0))
        return (0,0,0)

    def rear_shin(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        s = 1 if is_left else -1
        if ph == 'impulse': return (-ease_in_out(pr)*0.18, sin_wave(pr*8,8,0.02*s,0,0), sin_wave(pr*6,6,0.015,0,0))
        elif ph == 'jump':  return (-ease_out(pr)*0.22,    sin_wave(pr*12,12,0.01*s,0,0), sin_wave(pr*8,8,0.02,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.12,     sin_wave(pr*8,8,0.008*s,0,0), sin_wave(pr*4,4,0.01,0,0))
        return (0,0,0)

    def rear_foot(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        s = 1 if is_left else -1
        if ph == 'impulse': return (-ease_in_out(pr)*0.15, sin_wave(pr*12,12,0.03*s,0,0), sin_wave(pr*10,10,0.02,0,0))
        elif ph == 'jump':  return (-ease_out(pr)*0.18,    sin_wave(pr*25,25,0.02*s,0,0), sin_wave(pr*15,15,0.03,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.1,      sin_wave(pr*15,15,0.01*s,0,0), sin_wave(pr*8,8,0.015,0,0))
        return (0,0,0)

    def rear_toe(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': return (ease_in_out(pr)*0.12, 0, 0)
        elif ph == 'jump':  return (ease_out(pr)*0.08,    0, 0)
        elif ph == 'fall':  return (ease_in(pr)*0.05,     0, 0)
        return (0,0,0)

    def front_thigh(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        s = 1 if is_left else -1
        if ph == 'impulse': return (-ease_in_out(pr)*0.1,  sin_wave(pr*8,8,0.04*s,0,0), sin_wave(pr*6,6,-0.02,0,0))
        elif ph == 'jump':  return ( ease_out(pr)*0.35,    sin_wave(pr*15,15,0.03*s,0,0), sin_wave(pr*12,12,0.04,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.3,      sin_wave(pr*10,10,0.02*s,0,0), sin_wave(pr*8,8,0.02,0,0))
        return (0,0,0)

    def front_shin(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        s = 1 if is_left else -1
        if ph == 'impulse': return (-ease_in_out(pr)*0.15, sin_wave(pr*10,10,0.03*s,0,0), sin_wave(pr*8,8,-0.01,0,0))
        elif ph == 'jump':  return (-ease_out(pr)*0.25,    sin_wave(pr*20,20,0.02*s,0,0), sin_wave(pr*15,15,0.03,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.18,     sin_wave(pr*12,12,0.015*s,0,0), sin_wave(pr*10,10,0.02,0,0))
        return (0,0,0)

    def front_foot(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        s = 1 if is_left else -1
        if ph == 'impulse': return (-ease_in_out(pr)*0.12, sin_wave(pr*12,12,0.02*s,0,0), sin_wave(pr*8,8,-0.015,0,0))
        elif ph == 'jump':  return (-ease_out(pr)*0.2,     sin_wave(pr*18,18,0.015*s,0,0), sin_wave(pr*12,12,0.02,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.15,     sin_wave(pr*10,10,0.01*s,0,0), sin_wave(pr*6,6,0.01,0,0))
        return (0,0,0)

    def front_toe(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': return (ease_in_out(pr)*0.08, 0, 0)
        elif ph == 'jump':  return (ease_out(pr)*0.1,     0, 0)
        elif ph == 'fall':  return (ease_in(pr)*0.06,     0, 0)
        return (0,0,0)

    def spine_action(self, frame, segment, total_segments=7):
        ph, pr = self.get_phase_progress(frame)
        sf = segment / total_segments
        if ph == 'impulse': return (-ease_in_out(pr)*0.2*sf, sin_wave(pr*6,6,0.03*sf,0,0), ease_in_out(pr)*0.08*sf)
        elif ph == 'jump':  return ( ease_out(pr)*0.25*sf,   sin_wave(pr*10,10,0.02*sf,0,0), ease_out(pr)*0.12*sf)
        elif ph == 'fall':  return (-ease_in(pr)*0.15*sf,    sin_wave(pr*8,8,0.015*sf,0,0), ease_in(pr)*0.06*sf)
        return (0,0,0)

    def head_movement(self, frame):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': return (-ease_in_out(pr)*0.06, sin_wave(pr*8,8,0.03,0,0), sin_wave(pr*6,6,0.02,0,0))
        elif ph == 'jump':  return ( ease_out(pr)*0.08,    sin_wave(pr*12,12,0.04,0,0), sin_wave(pr*10,10,0.03,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.05,     sin_wave(pr*8,8,0.02,0,0), sin_wave(pr*6,6,0.015,0,0))
        return (0,0,0)

    def jaw_movement(self, frame):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': return (ease_in_out(pr)*0.03, 0, 0)
        elif ph == 'jump':  return (ease_out(pr)*0.04,    0, 0)
        elif ph == 'fall':  return (ease_in(pr)*0.02,     0, 0)
        return (0,0,0)

    def ear_movement(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        d = -1 if is_left else 1
        if ph == 'impulse': return (ease_in_out(pr)*0.05*d, sin_wave(pr*15,15,0.02,0,0), sin_wave(pr*12,12,0.015,0,0))
        elif ph == 'jump':  return (ease_out(pr)*0.06*d,    sin_wave(pr*20,20,0.025,0,0), sin_wave(pr*18,18,0.02,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.04*d,    sin_wave(pr*12,12,0.015,0,0), sin_wave(pr*10,10,0.01,0,0))
        return (0,0,0)

    def neck_movement(self, frame):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': return (-ease_in_out(pr)*0.04, sin_wave(pr*8,8,0.02,0,0), 0)
        elif ph == 'jump':  return ( ease_out(pr)*0.05,    sin_wave(pr*12,12,0.03,0,0), 0)
        elif ph == 'fall':  return (-ease_in(pr)*0.03,     sin_wave(pr*8,8,0.02,0,0), 0)
        return (0,0,0)

    def tail_movement(self, frame, segment):
        ph, pr = self.get_phase_progress(frame)
        sf = segment / 3
        if ph == 'impulse': return (-ease_in_out(pr)*0.15*sf, sin_wave(pr*25,25,0.06*sf,0,0), sin_wave(pr*20,20,0.04*sf,0,0))
        elif ph == 'jump':  return ( ease_out(pr)*0.25*sf,    sin_wave(pr*40,40,0.1*sf,0,0), sin_wave(pr*35,35,0.08*sf,0,0))
        elif ph == 'fall':  return ( ease_in(pr)*0.15*sf,     sin_wave(pr*25,25,0.05*sf,0,0), sin_wave(pr*20,20,0.03*sf,0,0))
        return (0,0,0)


class QuadrupedWalkPlainCycle:
    def __init__(self, total_frames=24):
        self.total_frames    = total_frames
        self.impulse_frames  = (1, 6)
        self.jump_frames     = (7, 14)
        self.fall_frames     = (15, 21)
        self.recovery_frames = (22, total_frames)

    def get_phase_progress(self, frame):
        for (s, e), ph in [(self.impulse_frames,'impulse'),(self.jump_frames,'jump'),
                           (self.fall_frames,'fall'),(self.recovery_frames,'recovery')]:
            if s <= frame <= e:
                return ph, (frame - s) / max(1, e - s)
        return 'neutral', 0

    def get_leg_rotation(self, frame, is_rear=False, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse':
            a = ease_in_out(pr)*(0.2 if is_rear else 0.15)
            return (-a, sin_wave(pr*15,15,0.01,0,0), sin_wave(pr*10,10,0.005,0,0))
        elif ph == 'jump':
            e = 0.15 if is_rear else 0.08
            return (-e, sin_wave(pr*20,20,0.02,0,0), 0)
        elif ph == 'fall':
            if pr < 0.1: return (0, sin_wave(pr*12,12,0.01,0,0), sin_wave(pr*10,10,0.005,0,0))
            ap = (pr-0.1)/0.9; r = ease_out(ap)*(0.35 if is_rear else 0.2); b = 0.4 if is_rear else 0.25
            return (-b+r, sin_wave(pr*12,12,0.01,0,0), sin_wave(pr*10,10,0.005,0,0))
        return (0,0,0)

    def spine_jump_down(self, frame, segment, total_segments=7):
        ph, pr = self.get_phase_progress(frame)
        sf = segment / total_segments
        if ph == 'impulse': return (ease_in_out(pr)*0.1*sf, 0, 0)
        elif ph == 'jump':  return (-ease_out(pr)*0.25*sf, 0, 0)
        elif ph == 'fall':  x = -0.25*sf + ease_out(pr)*0.3*sf; return (x, 0, 0)
        return (0,0,0)

    def tail_jump_down(self, frame, segment):
        ph, pr = self.get_phase_progress(frame)
        sf = segment / 3
        if ph == 'impulse': return (ease_in_out(pr)*0.1*sf, sin_wave(pr*20,20,0.015,segment*3.14/6,0), sin_wave(frame,30,0.008,segment*3.14/8,0))
        elif ph == 'jump':  return (-ease_out(pr)*0.25*sf,  sin_wave(pr*25,25,0.025,segment*3.14/4,0), sin_wave(frame,30,0.008,segment*3.14/8,0))
        elif ph == 'fall':  x = -0.25*sf + ease_out(pr)*0.25*sf; return (x, sin_wave(pr*15,15,0.015,segment*3.14/3,0), sin_wave(frame,30,0.008,segment*3.14/8,0))
        return (0,0,sin_wave(frame,30,0.008,segment*3.14/8,0))

    def head_jump_down(self, frame):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': return (ease_in_out(pr)*0.02, sin_wave(pr*12,12,0.005,0,0), 0)
        elif ph == 'jump':  return (-ease_out(pr)*0.04,   sin_wave(pr*18,18,0.008,0,0), 0)
        elif ph == 'fall':  return (-0.04+ease_out(pr)*0.04, sin_wave(pr*10,10,0.005,0,0), 0)
        return (0,0,0)

    def ear_jump_down(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': a = ease_in_out(pr)*0.02; return (a if is_left else -a, sin_wave(pr*15,15,0.005,0,0), sin_wave(frame,25,0.003,0,0))
        elif ph == 'jump':  b = ease_out(pr)*0.03;    return (-b if is_left else b, sin_wave(pr*20,20,0.008,0.78,0), sin_wave(frame,25,0.003,0,0))
        elif ph == 'fall':  c = (-0.03+ease_out(pr)*0.03) if is_left else (0.03-ease_out(pr)*0.03); return (c, sin_wave(pr*12,12,0.005,0,0), sin_wave(frame,25,0.003,0,0))
        return (0,0,sin_wave(frame,25,0.003,0,0))


# NOTA (fix 2026-08-06): esta es la definicion REAL de SniffingSearchCycle
# usada por el preview en vivo (_bones_caminar en el operador de "Reproducir
# recorrido" mas abajo, y por generate_keyframes() para los slots
# exportados via bake). Hay TAMBIEN un bloque de texto identico a esta
# clase mas arriba (~linea 2063), pero ese esta dentro de un f-string
# (variable `code = f'''...'''`, ver linea ~1983-2377): es solo la
# PLANTILLA que se escribe al archivo slot_NNN_jerry_caminar_arm.py al
# exportar, no codigo ejecutable de este addon. Antes existia aqui una
# version vieja de esta clase SIN los parametros range_mult/asym_rear
# (necesarios para el selector de "Estilo de caminata" por tramo:
# Normal/Lento/Herido/Rapido/Correr) -- se reemplazo por la version
# completa, igual en logica a la plantilla de arriba pero con las llaves
# de diccionario sin escapar (aqui SI es codigo real, no texto de un
# f-string).
class SniffingSearchCycle:
    def __init__(self, cycle_length=25, total_frames=100, range_mult=None, asym_rear=0.0):
        self.cycle_length  = cycle_length
        self.total_frames  = total_frames
        self.rm   = range_mult or {'leg': 1.0, 'spine': 1.0, 'tail': 1.0, 'head': 1.0, 'ear': 1.0}
        self.asym = asym_rear  # 0.0-1.0, debilita la pata trasera derecha (cojera)

    def normalize_frame(self, frame):
        return ((frame - 1) % self.cycle_length) + 1

    def sniff_down(self, frame):
        n = self.normalize_frame(frame)
        return (sin_wave(n, self.cycle_length, 0.03 * self.rm['head'], 0, 0), 0, 0)

    def look_around(self, frame):
        n = self.normalize_frame(frame)
        return (0, sin_wave(n, self.cycle_length, 0.05 * self.rm['head'], 0, 0), 0)

    def head_tilt(self, frame):
        n = self.normalize_frame(frame)
        return (0, 0, sin_wave(n, self.cycle_length, 0.016 * self.rm['head'], 0, 0))

    def ear_twitch(self, frame):
        n = self.normalize_frame(frame)
        return (0, sin_wave(n, self.cycle_length, 0.2 * self.rm['ear'], 0, 0), sin_wave(n, self.cycle_length, 0.1 * self.rm['ear'], 0, 0))

    def tail_wag_alert(self, frame):
        n = self.normalize_frame(frame)
        t = self.rm['tail']
        return (sin_wave(n, self.cycle_length, 0.4*t, 0, 0.2*t), sin_wave(n, self.cycle_length, 0.06*t, 0, 0), sin_wave(n, self.cycle_length, 0.16*t, 0, 0))

    def leg_slow_walk(self, frame, is_rear=False, is_left=True):
        n = self.normalize_frame(frame)
        phase = 0 if is_left else math.pi
        amp   = (0.4 if is_rear else 0.3) * self.rm['leg']
        if is_rear and not is_left:
            amp *= (1.0 - self.asym)
        return (-sin_wave(n, self.cycle_length, amp, phase, 0),
                -sin_wave(n, self.cycle_length, amp*0.15, phase, 0),
                -sin_wave(n, self.cycle_length, amp*0.03, phase, 0))

    def leg_bend(self, frame, is_rear=False, is_left=True):
        n = self.normalize_frame(frame)
        phase = 0 if is_left else math.pi
        bb    = (0.3 if is_rear else 0.24) * self.rm['leg']
        if is_rear and not is_left:
            bb *= (1.0 - self.asym)
        return (-abs(sin_wave(n, self.cycle_length, bb, phase, bb)),
                -sin_wave(n, self.cycle_length, 0.1, phase, 0),
                -sin_wave(n, self.cycle_length, 0.04, phase, 0))

    def foot_strike(self, frame, is_rear=False, is_left=True):
        n = self.normalize_frame(frame)
        phase = 0 if is_left else math.pi
        amp_x = (0.8 if is_rear else 0.6) * self.rm['leg']
        if is_rear and not is_left:
            amp_x *= (1.0 - self.asym)
        x = -sin_wave(n, self.cycle_length, amp_x, phase, 0.4 if is_rear else -0.1)
        y = abs(sin_wave(n, self.cycle_length, 0.04, phase, 0.02)) * (1.0 if is_rear else 0.5)
        z = -sin_wave(n, self.cycle_length, 0.04 if is_rear else 0.06, phase, 0.02)
        return (x, y, z)

    def toe_curl(self, frame, is_rear=False, is_left=True):
        n = self.normalize_frame(frame)
        phase = 0 if is_left else math.pi
        amp = 0.5 * self.rm['leg']
        if is_rear and not is_left:
            amp *= (1.0 - self.asym)
        return (abs(sin_wave(n, self.cycle_length, amp, phase, 0.4)),
                -sin_wave(n, self.cycle_length, 0.16, phase, 0),
                -sin_wave(n, self.cycle_length, 0.08, phase, 0.04))

    def spine_undulation(self, frame, segment, total_segments=7):
        n = self.normalize_frame(frame)
        ph = (segment / total_segments) * math.pi
        return (-sin_wave(n, self.cycle_length, 0.03 * self.rm['spine'], ph, -0.08 * self.rm['spine']), 0, 0)

    def vertical_bob(self, frame):
        n = self.normalize_frame(frame)
        bob = 0.02 * (0.5 - 0.5 * math.cos(2 * math.pi * n / self.cycle_length * 2))
        if self.asym > 0.0:
            bob += max(0.0, math.sin(2 * math.pi * n / self.cycle_length)) * 0.02 * self.asym
        return bob


# =============================================================================
# OPERADORES NUEVOS: Abrir .blend, Previsualizar recorrido, Ejecutar preview
# =============================================================================

class JRRSTPR_OT_ToggleRecording(Operator):
    bl_idname  = "jerrypr.toggle_recording"
    bl_label   = "Iniciar/Detener grabacion"
    bl_description = "Activa/desactiva la deteccion automatica de faces seleccionadas como recorrido"

    def execute(self, context):
        global _draw_handle
        path_cfg = context.scene.jerry_path
        path_cfg.recording_active = not path_cfg.recording_active

        if path_cfg.recording_active:
            if _draw_handle is None:
                _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
                    _draw_path_3d, (), "WINDOW", "POST_VIEW")
            self.report({"INFO"}, "Grabacion INICIADA — selecciona faces en modo EDIT")
        else:
            if _draw_handle is not None:
                bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
                _draw_handle = None
            self.report({"INFO"}, "Grabacion DETENIDA")

        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
        return {"FINISHED"}


class JRRSTPR_OT_RemoveLast(Operator):
    bl_idname  = "jerrypr.remove_last"
    bl_label   = "Quitar ultimo punto"
    bl_description = "Elimina el ultimo punto del recorrido"

    def execute(self, context):
        pts = context.scene.jerry_path.path_points
        if pts:
            pts.remove(len(pts) - 1)
            sync_paradas_frames(context.scene.jerry_path)
            sync_walk_styles(context.scene.jerry_path)
            for area in context.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()
            self.report({"INFO"}, "Ultimo punto eliminado")
        else:
            self.report({"WARNING"}, "No hay puntos")
        return {"FINISHED"}


class JRRSTPR_OT_ImportParadaAnim(Operator):
    """NUEVO (Kebyn, 2026-09-14, portado de Alfred): boton 'Importar
    animacion (.py)' que aparece en el panel junto al campo 'Frames' de
    un punto marcado como 'Parada' (ver panels.py). Deja elegir un
    script .py de animacion importada (modulo con un diccionario
    KEYFRAME_DATA de bone -> {frame: (rx, ry, rz)}) para que ese punto
    de parada reproduzca esa animacion completa en vez de la pose
    estatica IDLE_POSE -- ver generate_parada()/anim_file_path en
    generate_slots_jerry.py.

    Al elegir el archivo, se lee su duracion real (frame_count) y se
    sincroniza automaticamente pt.parada_frames_punto con ese valor.
    """
    bl_idname    = "jerrypr.import_parada_anim"
    bl_label     = "Importar animacion (.py)"
    bl_description = (
        "Selecciona un script .py de animacion para reproducir en este "
        "punto de parada, en vez de la pose estatica por defecto"
    )
    bl_options   = {"REGISTER", "UNDO"}

    index:       bpy.props.IntProperty(default=-1)
    filepath:    StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.py", options={"HIDDEN"})

    def invoke(self, context, event):
        pc = context.scene.jerry_path
        if 0 <= self.index < len(pc.path_points):
            existing = pc.path_points[self.index].parada_anim_file
            if existing:
                self.filepath = bpy.path.abspath(existing)
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        pc = context.scene.jerry_path
        if not (0 <= self.index < len(pc.path_points)):
            self.report({"ERROR"}, "Punto de recorrido invalido")
            return {"CANCELLED"}

        src = bpy.path.abspath(self.filepath)
        if not os.path.isfile(src) or not src.lower().endswith(".py"):
            self.report({"ERROR"}, f"Archivo .py no valido: {src}")
            return {"CANCELLED"}

        pt = pc.path_points[self.index]
        pt.parada_anim_file = src

        frame_count = None
        try:
            from .generate_slots_jerry import _load_keyframe_data_from_anim_file
            _kf, frame_count = _load_keyframe_data_from_anim_file(src)
        except Exception as e:
            print(f"jerrypr.import_parada_anim: no se pudo leer duracion de '{src}': {e}")

        if frame_count:
            pt.parada_frames_punto = frame_count
            self.report(
                {"INFO"},
                f"Animacion importada: {os.path.basename(src)} ({frame_count} frames)"
            )
        else:
            self.report(
                {"WARNING"},
                f"Animacion asociada, pero no se pudo leer su KEYFRAME_DATA: "
                f"{os.path.basename(src)} (se usara el valor actual de 'Frames')"
            )
        return {"FINISHED"}


class JRRSTPR_OT_ClearParadaAnim(Operator):
    """Quita la animacion .py importada de un punto de 'Parada',
    volviendo al comportamiento por defecto (pose estatica IDLE_POSE)."""
    bl_idname    = "jerrypr.clear_parada_anim"
    bl_label     = "Quitar animacion importada"
    bl_description = (
        "Quita la animacion .py importada de este punto de parada "
        "(vuelve a la pose estatica por defecto)"
    )
    bl_options   = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        pc = context.scene.jerry_path
        if 0 <= self.index < len(pc.path_points):
            pc.path_points[self.index].parada_anim_file = ""
        return {"FINISHED"}


class JRRSTPR_OT_OpenInteractionFolder(Operator):
    """Abre (y crea si no existe) la carpeta de animaciones de
    interaccion de Jerry (DEFAULT_INTERACTION_DIR_JERRY, constants.py).
    Ahi se guardan los .py que despues aparecen automaticamente en el
    dropdown 'Animacion de interaccion' de cualquier punto de encuentro
    con Alfred (ver _interaccion_anim_items() mas arriba).
    """
    bl_idname    = "jerrypr.open_interaction_folder"
    bl_label     = "Abrir carpeta de interacciones (jerry)"
    bl_description = (
        "Abre la carpeta donde van los .py de animaciones de "
        "interaccion de Jerry (se crea si todavia no existe)"
    )
    bl_options   = {"REGISTER"}

    def execute(self, context):
        import subprocess
        folder = DEFAULT_INTERACTION_DIR_JERRY
        try:
            os.makedirs(folder, exist_ok=True)
            subprocess.Popen(f'explorer "{folder}"')
            self.report({"INFO"}, f"Carpeta: {folder}")
        except Exception as e:
            self.report({"WARNING"}, f"No se pudo abrir: {e}")
        return {"FINISHED"}


class JRRSTPR_OT_RotateParadaRoot(Operator):
    """NUEVO (portado de Alfred, Kebyn 2026-09-14): boton 'Rotar root
    (jerry)' en el panel de un punto marcado como 'Parada'. Selecciona y
    activa el empty root (ROOT_NAME = 'jerry') y lanza el
    transform.rotate interactivo de Blender constreñido al eje Z (mismo
    comportamiento que presionar R, Z en el viewport) para que el
    usuario oriente al personaje a ojo. Una vez conforme con la
    orientacion, usar el boton 'Guardar orientacion'
    (JRRSTPR_OT_SaveParadaRot) para grabarla en este punto de parada.
    """
    bl_idname    = "jerrypr.rotate_parada_root"
    bl_label     = "Rotar root (jerry)"
    bl_description = (
        "Selecciona el empty root 'jerry' y arranca una rotacion "
        "interactiva en el eje Z (como R, Z en el viewport). Mueve el "
        "mouse y hace click izquierdo para confirmar, luego usa 'Guardar "
        "orientacion' para grabar el resultado en este punto de parada"
    )
    bl_options   = {"REGISTER", "UNDO"}

    ROOT_NAME = "jerry"

    def execute(self, context):
        root_empty = bpy.data.objects.get(self.ROOT_NAME)
        if root_empty is None or root_empty.type != "EMPTY":
            self.report({"ERROR"}, f"No se encontro el empty root '{self.ROOT_NAME}'")
            return {"CANCELLED"}

        for obj in context.selected_objects:
            obj.select_set(False)
        root_empty.select_set(True)
        context.view_layer.objects.active = root_empty

        return bpy.ops.transform.rotate(
            "INVOKE_DEFAULT",
            orient_axis="Z",
            constraint_axis=(False, False, True),
        )


class JRRSTPR_OT_SaveParadaRot(Operator):
    """NUEVO (portado de Alfred, Kebyn 2026-09-14): boton 'Guardar
    orientacion' -- lee la rotacion Z ACTUAL del empty root 'jerry' (la
    que haya quedado tras rotarlo a mano, ej. con
    JRRSTPR_OT_RotateParadaRoot o R, Z directo en el viewport) y la graba
    en pt.parada_rot_z (convertida a grados, mismo formato que
    pc.root_rot_z), activando pt.parada_rot_saved. Ver comentario
    completo en JRRSTPathPoint.parada_rot_saved sobre como se propaga
    este heading al resto del recorrido (Preview/Export).
    """
    bl_idname    = "jerrypr.save_parada_rot"
    bl_label     = "Guardar orientacion"
    bl_description = (
        "Graba la rotacion Z ACTUAL del root 'jerry' como el heading de "
        "este punto de parada. Se mantendra para el resto del recorrido "
        "hasta el proximo tramo con desplazamiento real, o hasta que se "
        "vuelva a editar"
    )
    bl_options   = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty(default=-1)
    ROOT_NAME = "jerry"

    def execute(self, context):
        pc = context.scene.jerry_path
        if not (0 <= self.index < len(pc.path_points)):
            self.report({"ERROR"}, "Punto de recorrido invalido")
            return {"CANCELLED"}

        root_empty = bpy.data.objects.get(self.ROOT_NAME)
        if root_empty is None or root_empty.type != "EMPTY":
            self.report({"ERROR"}, f"No se encontro el empty root '{self.ROOT_NAME}'")
            return {"CANCELLED"}

        pt = pc.path_points[self.index]
        rot_deg = math.degrees(root_empty.rotation_euler.z)
        pt.parada_rot_z = rot_deg
        pt.parada_rot_saved = True
        self.report({"INFO"}, f"Orientacion guardada: {rot_deg:.1f}°")
        return {"FINISHED"}


class JRRSTPR_OT_ClearParadaRot(Operator):
    """Quita la orientacion guardada de un punto de 'Parada', volviendo
    al heading automatico (ultimo tramo con desplazamiento real)."""
    bl_idname    = "jerrypr.clear_parada_rot"
    bl_label     = "Quitar orientacion guardada"
    bl_description = (
        "Quita la orientacion guardada de este punto de parada (vuelve "
        "al heading automatico)"
    )
    bl_options   = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        pc = context.scene.jerry_path
        if 0 <= self.index < len(pc.path_points):
            pc.path_points[self.index].parada_rot_saved = False
        return {"FINISHED"}


class JRRSTPR_OT_ClearPath(Operator):
    bl_idname  = "jerrypr.clear_path"
    bl_label   = "Limpiar recorrido"
    bl_description = "Elimina todos los puntos del recorrido"

    def execute(self, context):
        global _last_face_idx
        context.scene.jerry_path.path_points.clear()
        _last_face_idx = None
        sync_paradas_frames(context.scene.jerry_path)
        sync_walk_styles(context.scene.jerry_path)
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
        self.report({"INFO"}, "Recorrido limpiado")
        return {"FINISHED"}


class JRRSTPR_OT_SyncParadasFrames(Operator):
    """Ajusta pc.paradas_frames a la cantidad real de paradas del
    recorrido actual. Portado de ALFREDPR_OT_SyncParadasFrames,
    2026-08-05."""
    bl_idname  = "jerrypr.sync_paradas_frames"
    bl_label   = "Sincronizar frames por parada"
    bl_description = (
        "Ajusta la lista de frames por parada y de estilos de caminata a "
        "la cantidad real de paradas/tramos detectados en el recorrido "
        "actual, conservando los valores ya editados a mano"
    )

    def execute(self, context):
        pc = context.scene.jerry_path
        n = sync_paradas_frames(pc)
        n_walk = sync_walk_styles(pc)
        self.report({"INFO"}, f"Sincronizado: {n} parada(s) y {n_walk} tramo(s) de caminata detectado(s)")
        return {"FINISHED"}


class JRRSTPR_OT_GenerateSlots(Operator):
    bl_idname  = "jerrypr.generate_slots"
    bl_label   = "GENERAR SLOTS"
    bl_description = "Genera scripts slot_NNN_*.py y opcionalmente los ejecuta en escena"

    def execute(self, context):
        path_cfg = context.scene.jerry_path
        pts = list(path_cfg.path_points)

        if len(pts) < 1:
            self.report({"ERROR"}, "No hay puntos en el recorrido")
            return {"CANCELLED"}

        # Si solo hay 1 punto: slot estatico (idle en esa coordenada)
        if len(pts) == 1:
            self.report({"INFO"}, "1 solo punto: la animacion se realizara en esa coordenada (sin desplazamiento)")

        # Convertir a dicts
        pts_dicts = [_pt_to_dict(pt, i) for i, pt in enumerate(pts)]
        if len(pts) > 1:
            expanded_pts, frames_paradas_marcadas, _anim_files_gs, _rot_gs = _expand_points_with_paradas(pts)
            segments = _group_segments(expanded_pts)
        else:
            expanded_pts, frames_paradas_marcadas, _anim_files_gs, _rot_gs = pts, [], [], []
            segments = []
        today     = date.today().isoformat()
        root_rot  = (path_cfg.root_rot_x, path_cfg.root_rot_y, path_cfg.root_rot_z)
        fpb       = path_cfg.frames_por_bloque

        sync_paradas_frames(path_cfg)
        sync_paradas_frames_from_segments(context)
        sync_walk_styles(path_cfg)
        parada_idx = 0
        caminar_idx = 0

        # Carpeta de salida
        out_dir = bpy.path.abspath(path_cfg.output_dir) if path_cfg.output_dir else ""
        if out_dir and not os.path.isdir(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
            except Exception as e:
                self.report({"ERROR"}, f"No se pudo crear carpeta: {e}")
                return {"CANCELLED"}

        slot_index    = path_cfg.slot_inicio
        current_frame = path_cfg.frame_inicio
        generated     = []

        # Caso especial: un solo punto → caminar 0 distancia (solo idle en esa coord)
        if len(pts) == 1:
            segments = [{"type": "caminar", "points": [pts[0], pts[0]]}]

        prev_rz = root_rot[2]
        for seg in segments:
            move_type = seg["type"]
            seg_pts   = [_pt_to_dict(p, i) for i, p in enumerate(seg["points"])]

            # Calcular dir_angle para actualizar prev_rz al final
            # seg["points"] son bpy PropertyGroup con .coords[]
            _pts_raw = seg["points"]
            if len(_pts_raw) >= 2:
                _p0r = _pts_raw[0]; _p1r = _pts_raw[-1]
                _p0c = {"x": _p0r.coords[0], "y": _p0r.coords[1], "z": _p0r.coords[2]}
                _p1c = {"x": _p1r.coords[0], "y": _p1r.coords[1], "z": _p1r.coords[2]}
                _dir_angle = _compute_direction_angle(_p0c, _p1c)
            else:
                _dir_angle = None

            _cur_root_rot = (root_rot[0], root_rot[1], prev_rz)
            if move_type in ('saltar_subir','saltar_bajar','saltar_horizontal'):
                code,end_frame=_jump.generate_jump(slot_index,current_frame,seg_pts,_cur_root_rot,
                    move_type.removeprefix('saltar_'),context.scene.render.fps/context.scene.render.fps_base)
                fname=f"slot_{slot_index:03d}_jerry_{move_type}.py"
            elif move_type == "parada":
                if parada_idx < len(frames_paradas_marcadas):
                    frames_esta_parada = frames_paradas_marcadas[parada_idx]
                elif parada_idx < len(path_cfg.paradas_frames):
                    frames_esta_parada = path_cfg.paradas_frames[parada_idx].frames
                else:
                    frames_esta_parada = path_cfg.frames_parada
                if getattr(seg["points"][0], "tipo_segmento", "AUTO") == "OBSERVAR":
                    # NUEVO (Kebyn, 2026-09-24): Observar -- ver
                    # generate_parada(observar=True) en generate_slots_jerry.py
                    from .generate_slots_jerry import generate_parada as _gs_gen_parada
                    code, end_frame = _gs_gen_parada(slot_index, current_frame, seg_pts, today,
                                                     _cur_root_rot, frames_parada=frames_esta_parada,
                                                     observar=True)
                    fname = f"slot_{slot_index:03d}_jerry_observar.py"
                else:
                    code, end_frame = _gen_parada(slot_index, current_frame, seg_pts, _cur_root_rot, today,
                                                   frames_parada=frames_esta_parada)
                    fname = f"slot_{slot_index:03d}_jerry_parada.py"
                parada_idx += 1
            else:
                walk_style_actual = (path_cfg.walk_styles[caminar_idx].style
                                      if caminar_idx < len(path_cfg.walk_styles) else path_cfg.walk_style)
                code, end_frame = _gen_caminar(slot_index, current_frame, seg_pts, _cur_root_rot, today, fpb,
                                                walk_style=walk_style_actual)
                fname = f"slot_{slot_index:03d}_jerry_caminar.py"
                caminar_idx += 1

            if _dir_angle is not None:
                prev_rz = _dir_angle

            # Guardar archivo si se especifico carpeta
            if out_dir:
                fpath = os.path.join(out_dir, fname)
                try:
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(code)
                except Exception as e:
                    self.report({"WARNING"}, f"Error guardando {fname}: {e}")

            # Ejecutar en escena si esta habilitado
            if path_cfg.execute_inscene:
                try:
                    exec(compile(code, fname, "exec"), {"__name__": "__main__"})
                except Exception as e:
                    self.report({"WARNING"}, f"Error ejecutando {fname}: {e}")

            frames_used = end_frame - current_frame + 1
            generated.append({
                "slot": slot_index, "type": move_type, "file": fname,
                "start_frame": current_frame, "end_frame": end_frame, "frames": frames_used,
            })
            current_frame = end_frame + 1
            slot_index   += 1

        path_cfg.last_generated = len(generated)
        total_frames = current_frame - path_cfg.frame_inicio
        path_cfg.status_msg = (
            f"OK: {len(generated)} slots | {total_frames} frames | "
            f"frame {path_cfg.frame_inicio}–{current_frame - 1}"
        )

        # Guardar resumen JSON
        if out_dir:
            summary = {
                "personaje": "jerry",
                "start_slot": path_cfg.slot_inicio, "start_frame": path_cfg.frame_inicio,
                "end_slot": slot_index - 1, "end_frame": current_frame - 1,
                "root_rotation": {"x": root_rot[0], "y": root_rot[1], "z": root_rot[2]},
                "frames_por_bloque": fpb,
                "total_slots": len(generated), "total_frames": total_frames,
                "slots": generated,
            }
            try:
                with open(os.path.join(out_dir, "_resumen_slots_jerry.json"),
                          "w", encoding="utf-8") as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

        self.report({"INFO"}, path_cfg.status_msg)
        return {"FINISHED"}




# =============================================================================
# OPERADORES NUEVOS: Abrir .blend, Previsualizar recorrido, Ejecutar preview
# =============================================================================

class JRRSTPR_OT_OpenBlendFile(Operator):
    """Abre un explorador de archivos para seleccionar el .blend del personaje."""
    bl_idname  = "jerrypr.open_blend_file"
    bl_label   = "Seleccionar .blend del personaje"
    bl_options = {"REGISTER", "UNDO"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        pc = context.scene.jerry_path
        if self.filepath:
            pc.blend_filepath = self.filepath
        return {"FINISHED"}

    def invoke(self, context, event):
        pc = context.scene.jerry_path
        self.filepath = bpy.path.abspath(pc.blend_filepath) if pc.blend_filepath else ""
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class JRRSTPR_OT_PreviewPath(Operator):
    """Carga personaje completo, anima root + bones (caminar/saltar) y lanza playback."""
    bl_idname  = "jerrypr.preview_path"
    bl_label   = "Reproducir recorrido"
    bl_options = {"REGISTER", "UNDO"}

    ROOT_NAME   = "jerry"
    ARM_NAME    = "Dog_001_rig"
    ALL_OBJECTS = ("jerry", "Dog_001_rig",
                   "Mesh_3_jerry",
                   "sombrero_jerry",
                   "pupila_derecha_jerry", "pupila_izquierda_jerry",
                   "ojo_izquierdo_jerry", "ojo_derecho_jerry",
                   "sejas_1_jerry", "sejas_2_jerry")

    # ── utilidades matematicas (identicas al generador oficial) ──────────────
    @staticmethod
    def _lerp(a, b, t):     return a + (b - a) * t
    @staticmethod
    def _clamp(t):          return max(0.0, min(1.0, t))
    @staticmethod
    def _smoothstep(t):
        t = max(0.0, min(1.0, t)); return t*t*(3-2*t)
    @staticmethod
    def _ease_in(t, e=2):   t = max(0.0, min(1.0, t)); return t**e
    @staticmethod
    def _ease_out(t, e=2):  t = max(0.0, min(1.0, t)); return 1-(1-t)**e
    @staticmethod
    def _phase_t(rf, s, e):
        return max(0.0, min(1.0, (rf-s)/(e-s))) if e != s else 1.0
    @staticmethod
    def _micro(rf, freq=1.0, amp=1.0):
        return math.sin(rf * freq * 0.45 + 1.3) * amp

    # ── calculo de angulo IDENTICO a _compute_direction_angle / _get_segment_angle ──
    @staticmethod
    def _compute_direction_angle(dx, dy, fallback_deg):
        """Replica exacta de _compute_direction_angle del generador oficial.
        Devuelve angulo en GRADOS con snapping a 90 y correccion de signo."""
        if abs(dx) < 0.0001 and abs(dy) < 0.0001:
            return fallback_deg
        ang_raw     = math.degrees(math.atan2(dx, dy))
        ang_rounded = round(ang_raw / 90.0) * 90.0
        ang = ang_rounded if abs(ang_raw - ang_rounded) < 45 else -ang_raw
        while ang >  180: ang -= 360
        while ang < -180: ang += 360
        if   ang ==  90: ang = -90
        elif ang == -90: ang =  90
        return ang

    # ── RotationSmoother identico al generador oficial ───────────────────────
    class _RotationSmoother:
        def __init__(self, smoothing_frames=12):
            self.smoothing_frames          = smoothing_frames
            self.previous_rotation         = None
            self.transition_start_frame    = None
            self.transition_start_rotation = None
            self.target_rotation           = None

        def smooth_rotation(self, target_rotation, current_frame):
            target_rotation = self._normalize(target_rotation)
            if self.previous_rotation is None:
                self.previous_rotation = target_rotation
                return target_rotation
            angle_diff = self._diff(target_rotation, self.previous_rotation)
            if abs(angle_diff) < 2:
                self.previous_rotation = target_rotation
                self.transition_start_frame = None
                return target_rotation
            if self.transition_start_frame is None:
                self.transition_start_frame    = current_frame
                self.transition_start_rotation = self.previous_rotation
                self.target_rotation           = target_rotation
            elapsed  = current_frame - self.transition_start_frame
            progress = min(elapsed / self.smoothing_frames, 1.0)
            eased    = self._ss(progress)
            smoothed = self.transition_start_rotation + self._diff(
                self.target_rotation, self.transition_start_rotation) * eased
            if progress >= 1.0:
                self.previous_rotation      = target_rotation
                self.transition_start_frame = None
                return target_rotation
            return smoothed

        def _normalize(self, a):
            while a >  180: a -= 360
            while a < -180: a += 360
            return a
        def _diff(self, target, current):
            d = target - current
            while d >  180: d -= 360
            while d < -180: d += 360
            return d
        def _ss(self, x):
            if x <= 0: return 0.0
            if x >= 1: return 1.0
            return x * x * (3.0 - 2.0 * x)

    # ── carga del personaje ──────────────────────────────────────────────────
    def _load_character(self, context, blend_path):
        """
        Carga (append) los objetos de Jerry desde blend_path a la escena actual.
        Robusto frente a:
          - Objetos ya existentes en bpy.data (segunda llamada) → los reutiliza.
          - Objetos importados con sufijo .001 → los renombra.
          - Contexto proveniente de EDIT mode → fuerza OBJECT mode antes del append.
          - Objetos no vinculados a ninguna coleccion → los vincula a la raiz.
        """
        print(f"  _load_character: iniciando — context.mode={context.mode!r}, blend={blend_path!r}")
        wanted = set(self.ALL_OBJECTS)

        # --- Asegurar OBJECT mode antes del append ---
        try:
            if context.mode != "OBJECT":
                # En POSE mode necesitamos el objeto activo correcto
                arm = bpy.data.objects.get(self.ARM_NAME)
                if arm:
                    try:
                        bpy.context.view_layer.objects.active = arm
                    except Exception:
                        pass
                bpy.ops.object.mode_set(mode="OBJECT")
        except Exception as _me:
            print(f"  _load_character: advertencia al cambiar modo: {_me}")

        # --- Deseleccionar todo para evitar contaminacion de contexto ---
        try:
            bpy.ops.object.select_all(action="DESELECT")
        except Exception:
            pass

        # --- PASO 1: Detectar cuales objetos ya existen en bpy.data ---
        already_in_data = {n for n in wanted if bpy.data.objects.get(n) is not None}
        need_append     = wanted - already_in_data

        # --- PASO 2: Append solo los que faltan ---
        if need_append:
            try:
                with bpy.data.libraries.load(blend_path, link=False) as (src, dst):
                    available = [n for n in src.objects if n in need_append]
                    dst.objects = available
            except Exception as e:
                self.report({"ERROR"}, f"Error al cargar .blend: {e}"); return False

            if not available and not already_in_data:
                self.report({"ERROR"},
                    f"El .blend no contiene ninguno de los objetos esperados: {sorted(wanted)}")
                return False

            # Tras el append, Blender puede haberlos creado con sufijo .001
            # si habia datos residuales. Renombrar antes de vincular.
            for expected_name, expected_type in [
                (self.ROOT_NAME, "EMPTY"),
                (self.ARM_NAME,  "ARMATURE"),
                ("Mesh_3_jerry",         "MESH"),
                ("sombrero_jerry",       "MESH"),
                ("pupila_derecha_jerry", "MESH"),
                ("pupila_izquierda_jerry","MESH"),
                ("ojo_izquierdo_jerry",  "MESH"),
                ("ojo_derecho_jerry",    "MESH"),
                ("sejas_1_jerry",        "MESH"),
                ("sejas_2_jerry",        "MESH"),
            ]:
                if bpy.data.objects.get(expected_name) is None:
                    for candidate in bpy.data.objects:
                        if (candidate.name.startswith(expected_name + ".") and
                                candidate.type == expected_type):
                            candidate.name = expected_name
                            print(f"  _load_character: renombrado '{candidate.name}' -> '{expected_name}'")
                            break

        # --- PASO 3: Vincular TODOS los objetos de Jerry a la coleccion raiz ---
        # Esto cubre tanto los recien appendeados como los ya existentes que
        # pudieron haber quedado desvinculados (ej: Undo, cambio de escena).
        col = context.scene.collection
        scene_obj_names = {o.name for o in context.view_layer.objects}

        for name in wanted:
            obj = bpy.data.objects.get(name)
            if obj is None:
                continue
            # Vincular a la coleccion raiz de la escena si no esta en ningun layer
            if name not in scene_obj_names:
                # Primero intentar desvincular de otras colecciones huerfanas
                for other_col in list(bpy.data.collections):
                    if name in [o.name for o in other_col.objects]:
                        try:
                            other_col.objects.unlink(obj)
                        except Exception:
                            pass
                try:
                    col.objects.link(obj)
                    print(f"  _load_character: vinculado '{name}' a escena")
                except RuntimeError:
                    pass  # ya estaba en col

        # --- PASO 4: Actualizar view layer ---
        context.view_layer.update()

        # --- PASO 5: Reparar jerarquia ---
        root = bpy.data.objects.get(self.ROOT_NAME)
        arm  = bpy.data.objects.get(self.ARM_NAME)
        if root and arm and arm.parent is None:
            arm.parent = root
            arm.matrix_parent_inverse.identity()
            print(f"  _load_character: jerarquia reparada arm->root")
        for mn in ("Mesh_3_jerry", "sombrero_jerry",
                   "pupila_derecha_jerry", "pupila_izquierda_jerry",
                   "ojo_izquierdo_jerry",  "ojo_derecho_jerry",
                   "sejas_1_jerry",        "sejas_2_jerry"):
            mo = bpy.data.objects.get(mn)
            if mo and mo.parent is None and arm:
                mo.parent = arm

        root_final = bpy.data.objects.get(self.ROOT_NAME)
        if root_final is None:
            print(f"  _load_character: ERROR — 'jerry' no encontrado tras el append")
            print(f"  _load_character: objetos en bpy.data con 'jerry': "
                  f"{[o.name for o in bpy.data.objects if 'jerry' in o.name.lower()]}")
        else:
            print(f"  _load_character: OK — personaje listo en escena")
        return root_final is not None

    # ── helpers de geometria de trayectoria ──────────────────────────────────
    @staticmethod
    def _build_caminar_segments(pts):
        """Construye lista de segmentos {start, end} y distancias a partir de JRRSTPathPoints."""
        segs  = []
        dists = []
        for i in range(len(pts) - 1):
            s = (pts[i].coords[0],   pts[i].coords[1],   pts[i].coords[2])
            e = (pts[i+1].coords[0], pts[i+1].coords[1], pts[i+1].coords[2])
            dx, dy, dz = e[0]-s[0], e[1]-s[1], e[2]-s[2]
            d = max(0.0001, math.sqrt(dx*dx + dy*dy + dz*dz))
            segs.append({'start': s, 'end': e})
            dists.append(d)
        if not segs:
            segs  = [{'start': (0,0,0), 'end': (0,0,0)}]
            dists = [0.0001]
        return segs, dists

    @staticmethod
    def _alloc_frames(dists, total_frames):
        """Distribuye total_frames entre segmentos proporcional a distancia."""
        total_dist = sum(dists) or 1.0
        alloc = [max(1, int(round(total_frames * (d / total_dist)))) for d in dists]
        diff = total_frames - sum(alloc)
        i = 0
        while diff != 0:
            if diff > 0:
                alloc[i % len(alloc)] += 1; diff -= 1
            else:
                if alloc[i % len(alloc)] > 1:
                    alloc[i % len(alloc)] -= 1; diff += 1
            i += 1
        cum = []
        acc = 0
        for f in alloc:
            acc += f; cum.append(acc)
        return alloc, cum

    @staticmethod
    def _get_pos(segs, alloc, cum, path_frame):
        """Interpola posicion en path_frame (1-based) sobre los segmentos."""
        prev = 0
        for j, cf in enumerate(cum):
            if path_frame <= cf:
                s, e = segs[j]['start'], segs[j]['end']
                steps = max(1, alloc[j])
                local = path_frame - prev
                t = max(0.0, min(1.0, local / steps))
                return (s[0]+(e[0]-s[0])*t, s[1]+(e[1]-s[1])*t, s[2]+(e[2]-s[2])*t)
            prev = cf
        last = segs[-1]['end']
        return (last[0], last[1], last[2])

    # ── keyframe helpers ─────────────────────────────────────────────────────
    @staticmethod
    def _kf(obj, frame):
        obj.keyframe_insert(data_path="location",       frame=frame)
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
    @staticmethod
    def _kfb(bone, frame):
        bone.keyframe_insert(data_path="rotation_euler", frame=frame)

    # ── BONES caminar — usa SniffingSearchCycle (identico al slot generado) ──
    def _bones_parada(self, bones, frame):
        """Fuerza todos los bones del cuadrupedo a la pose de rest 'parado'
        (IDLE_POSE_PARADA) -- canvas limpio para el Paso 3, igual que
        _gen_parada()/generate_parada() para los slots exportados."""
        from mathutils import Quaternion as _Quat
        for bname, (qw, qx, qy, qz) in IDLE_POSE_PARADA.items():
            b = bones.get(bname)
            if b is None:
                continue
            b.rotation_euler = _Quat((qw, qx, qy, qz)).to_euler('XYZ')
            self._kfb(b, frame)

    def _bones_caminar(self, bones, frame, rf, fpb, walk_style='NORMAL'):
        """Anima todos los bones del cuadrupedo en caminar usando
        SniffingSearchCycle, escalada por el estilo de caminata elegido
        (portado de Alfred, Kebyn 2026-08-05 -- ver WALK_STYLE_PARAMS en
        generate_slots_jerry.py)."""
        from .generate_slots_jerry import WALK_STYLE_PARAMS as _WSP
        style = _WSP.get(walk_style, _WSP['NORMAL'])
        cycle_len = min(max(4, round(25 * style['cycle_mult'])), max(1, fpb))
        cycle = SniffingSearchCycle(cycle_length=cycle_len, total_frames=fpb,
                                     range_mult=style['range_mult'], asym_rear=style['asym_rear_leg'])
        local = rf + 1  # SniffingSearchCycle usa frames 1-based

        def sin_w(f, period, amp, phase=0, offset=0):
            return amp * math.sin(2 * math.pi * f / period + phase) + offset
        def cos_w(f, period, amp, phase=0, offset=0):
            return amp * math.cos(2 * math.pi * f / period + phase) + offset

        # Patas traseras
        for side, is_l in (('L', True), ('R', False)):
            for key, rot in (
                (f'shoulder.{side}', cycle.leg_slow_walk(local, True, is_l)),
                (f'thigh.{side}',    tuple(x * (0.01 if is_l else -0.3) for x in cycle.leg_slow_walk(local, True, is_l))),
                (f'shin.{side}',     cycle.leg_bend(local, True, is_l)),
                (f'foot.{side}',     cycle.foot_strike(local, True, is_l)),
                (f'toe.{side}',      cycle.toe_curl(local, True, is_l)),
            ):
                if key in bones:
                    bones[key].rotation_euler = rot
                    self._kfb(bones[key], frame)
            # Patas delanteras (desfase +12 frames como en el slot)
            lf2 = local + 12
            for key, rot in (
                (f'front_thigh.{side}', tuple(x * (0.6 if is_l else 0.4) for x in cycle.leg_slow_walk(lf2, False, is_l))),
                (f'front_shin.{side}',  cycle.leg_bend(lf2, False, is_l)),
                (f'front_foot.{side}',  cycle.foot_strike(lf2, False, is_l)),
                (f'front_toe.{side}',   cycle.toe_curl(lf2, False, is_l)),
            ):
                if key in bones:
                    bones[key].rotation_euler = rot
                    self._kfb(bones[key], frame)

        # Columna
        for i in range(1, 8):
            key = f'spine_{i}'
            if key in bones:
                bones[key].rotation_euler = cycle.spine_undulation(local, i, 7)
                self._kfb(bones[key], frame)

        # Cola
        for i in range(1, 4):
            key = f'tail_{i}'
            if key in bones:
                bones[key].rotation_euler = cycle.tail_wag_alert(local)
                self._kfb(bones[key], frame)

        # Cabeza / oidos
        sniff = cycle.sniff_down(local)
        look  = cycle.look_around(local)
        tilt  = cycle.head_tilt(local)
        if 'scull' in bones:
            bones['scull'].rotation_euler = (sniff[0] + tilt[0] * 0.3, look[1], tilt[2])
            self._kfb(bones['scull'], frame)
        if 'scull_1' in bones:
            bones['scull_1'].rotation_euler = (sniff[0] * 0.5, look[1] * 0.5, tilt[2] * 0.5)
            self._kfb(bones['scull_1'], frame)
        if 'neck' in bones:
            bones['neck'].rotation_euler = (sniff[0] * 0.3, 0, 0)
            self._kfb(bones['neck'], frame)
        if 'jaw_top' in bones:
            bones['jaw_top'].rotation_euler = (0.224, 0, 0)
            self._kfb(bones['jaw_top'], frame)
        if 'ear.L' in bones:
            bones['ear.L'].rotation_euler = cycle.ear_twitch(local)
            self._kfb(bones['ear.L'], frame)
        if 'ear.R' in bones:
            bones['ear.R'].rotation_euler = cycle.ear_twitch(local + 6)
            self._kfb(bones['ear.R'], frame)

    # ── BONES saltar_subir — usa DogJumpCycle (identico al slot generado) ───
    def _bones_saltar_subir(self, bones, frame, rf):
        """Anima todos los bones del cuadrupedo en salto ascendente usando DogJumpCycle."""
        jump = DogJumpCycle(total_frames=15)
        lf = rf + 1  # local frame 1-based

        for side, is_l in (('L', True), ('R', False)):
            for key, rot in (
                (f'thigh.{side}',        jump.rear_thigh(lf, is_l)),
                (f'shin.{side}',         jump.rear_shin(lf, is_l)),
                (f'foot.{side}',         jump.rear_foot(lf, is_l)),
                (f'toe.{side}',          jump.rear_toe(lf, is_l)),
                (f'front_thigh.{side}',  jump.front_thigh(lf, is_l)),
                (f'front_shin.{side}',   jump.front_shin(lf, is_l)),
                (f'front_foot.{side}',   jump.front_foot(lf, is_l)),
                (f'front_toe.{side}',    jump.front_toe(lf, is_l)),
                (f'ear.{side}',          jump.ear_movement(lf, is_l)),
            ):
                if key in bones:
                    bones[key].rotation_euler = rot
                    self._kfb(bones[key], frame)

        for i in range(1, 8):
            key = f'spine_{i}'
            if key in bones:
                bones[key].rotation_euler = jump.spine_action(lf, i, 7)
                self._kfb(bones[key], frame)

        for i in range(1, 4):
            key = f'tail_{i}'
            if key in bones:
                bones[key].rotation_euler = jump.tail_movement(lf, i)
                self._kfb(bones[key], frame)

        if 'neck' in bones:
            bones['neck'].rotation_euler = jump.neck_movement(lf)
            self._kfb(bones['neck'], frame)
        if 'scull' in bones:
            bones['scull'].rotation_euler = jump.head_movement(lf)
            self._kfb(bones['scull'], frame)
        if 'scull_1' in bones:
            h = jump.head_movement(lf)
            bones['scull_1'].rotation_euler = tuple(x * 0.5 for x in h)
            self._kfb(bones['scull_1'], frame)
        if 'jaw_top' in bones:
            bones['jaw_top'].rotation_euler = jump.jaw_movement(lf)
            self._kfb(bones['jaw_top'], frame)

    # ── BONES saltar_bajar — usa QuadrupedWalkPlainCycle (identico al slot) ─
    def _bones_saltar_bajar(self, bones, frame, rf):
        """Anima todos los bones del cuadrupedo en salto descendente usando QuadrupedWalkPlainCycle."""
        cyc = QuadrupedWalkPlainCycle(total_frames=24)
        lf = rf + 1  # local frame 1-based
        ph, _ = cyc.get_phase_progress(lf)

        for side, is_l in (('L', True), ('R', False)):
            rear_rot  = cyc.get_leg_rotation(lf, True,  is_l)
            front_rot = cyc.get_leg_rotation(lf, False, is_l)
            front_fall = tuple(-x for x in front_rot) if ph == 'fall' else front_rot

            mapping = [
                (f'shoulder.{side}',      (tuple(x * (0.2 if ph == 'impulse' else 1) for x in rear_rot)
                                           if ph != 'fall' else tuple(-x for x in rear_rot))),
                (f'thigh.{side}',         tuple(x * 0.5 for x in rear_rot)),
                (f'shin.{side}',          rear_rot),
                (f'foot.{side}',          tuple(x * 0.8 for x in rear_rot)),
                (f'toe.{side}',           tuple(x * 0.6 for x in rear_rot)),
                (f'front_thigh.{side}',   tuple(x * 0.4 for x in front_rot)),
                (f'front_shin.{side}',    front_rot),
                (f'front_foot.{side}',    tuple(x * 0.7 for x in front_rot)),
                (f'front_toe.{side}',     tuple(x * 0.5 for x in front_rot)),
                (f'ear.{side}',           cyc.ear_jump_down(lf, is_l)),
            ]
            for key, rot in mapping:
                if key in bones:
                    bones[key].rotation_euler = rot
                    self._kfb(bones[key], frame)

        for i in range(1, 8):
            key = f'spine_{i}'
            if key in bones:
                bones[key].rotation_euler = cyc.spine_jump_down(lf, i, 7)
                self._kfb(bones[key], frame)

        for i in range(1, 4):
            key = f'tail_{i}'
            if key in bones:
                bones[key].rotation_euler = cyc.tail_jump_down(lf, i)
                self._kfb(bones[key], frame)

        if 'scull' in bones:
            bones['scull'].rotation_euler = cyc.head_jump_down(lf)
            self._kfb(bones['scull'], frame)
        if 'scull_1' in bones:
            h = cyc.head_jump_down(lf)
            bones['scull_1'].rotation_euler = tuple(x * 0.5 for x in h)
            self._kfb(bones['scull_1'], frame)
        if 'jaw_top' in bones:
            bones['jaw_top'].rotation_euler = (0, 0, 0)
            self._kfb(bones['jaw_top'], frame)
        if 'neck' in bones:
            bones['neck'].rotation_euler = (0, 0, 0)
            self._kfb(bones['neck'], frame)

    # ── posicion empty: salto subir (identico a _empty_position_subir) ───────
    @staticmethod
    def _pos_saltar_subir(p0c, p1c, rf):
        """
        Parabola suave para salto ascendente (15 frames).
        - Avance horizontal: ease-in-out sobre t
        - Arco vertical: parabola 4*H*t*(1-t) con ease-in en la primera mitad
          y ease-out en la segunda — elimina los escalones roboticos de fases.
        - H adaptativo: dz del destino mas un arco adicional proporcional a la distancia XY.
        """
        ox, oy, oz = p0c[0], p0c[1], p0c[2]
        dx = p1c[0] - ox;  dy = p1c[1] - oy;  dz = p1c[2] - oz
        TOTAL = 15
        # t normalizado 0→1 con suavizado quintico (sin discontinuidades)
        raw = max(0.0, min(1.0, rf / max(1, TOTAL - 1)))
        # Smoothstep doble (C2) para avance horizontal
        t = raw * raw * raw * (raw * (raw * 6 - 15) + 10)
        # Arco: parabola clasica + componente ease que suaviza los extremos
        # Altura maxima de la parabola = z_destino + 0.3m
        # arc(t) va de 0 en t=0, sube hasta +0.3 en el pico, vuelve a 0 en t=1
        # (ya que oz+dz es z_destino, el arco final es 0 y el offset lo da dz)
        # Formula: arc = extra * 4 * t * (1-t), donde extra = 0.3m sobre destino
        EXTRA = 0.3  # metros sobre z_destino
        arc = EXTRA * 4.0 * raw * (1.0 - raw)
        # Suavizar arranque y aterrizaje (evita pop en frame 0 y frame final)
        if raw < 0.15:
            blend = raw / 0.15
            arc *= blend * blend * (3 - 2 * blend)
        elif raw > 0.85:
            blend = (1.0 - raw) / 0.15
            arc *= blend * blend * (3 - 2 * blend)
        return (ox + t*dx, oy + t*dy, oz + t*dz + arc)

    # ── posicion empty: salto bajar (parábola suave descendente) ─────────────
    @staticmethod
    def _pos_saltar_bajar(p0c, p1c, rf):
        """
        Parabola suave para salto descendente (24 frames).
        - Igual filosofia que _pos_saltar_subir pero con asimetria:
          la caida se acelera mas rapido (bias hacia el final) para sentirse
          como gravedad real. Se agrega un mini-bounce al aterrizar.
        """
        ox, oy, oz = p0c[0], p0c[1], p0c[2]
        dx = p1c[0] - ox;  dy = p1c[1] - oy;  dz = p1c[2] - oz
        TOTAL = 24
        raw = max(0.0, min(1.0, rf / max(1, TOTAL - 1)))
        # Avance horizontal: smoothstep quintico
        t = raw * raw * raw * (raw * (raw * 6 - 15) + 10)
        # Arco asimetrico: sube suave, cae con aceleracion (ease-in en la bajada)
        dist_xy = math.sqrt(dx*dx + dy*dy)
        # dz es negativo (baja), H es la altura del arco sobre la linea recta
        H = abs(dz) * 0.5 + max(0.3, dist_xy * 0.15)
        # Parabola sesgada: pico antes del centro (raw=0.35) para sentir gravedad
        peak = 0.35
        if raw <= peak:
            u = raw / peak              # 0→1 hasta el pico
            arc = H * math.sin(u * math.pi * 0.5)   # sube suave (ease-out)
        else:
            u = (raw - peak) / (1.0 - peak)          # 0→1 desde el pico al final
            arc = H * math.cos(u * math.pi * 0.5)   # cae con ease-in
        # Mini bounce al aterrizar (ultimos 15% del trayecto)
        if raw > 0.85:
            bounce_t = (raw - 0.85) / 0.15           # 0→1
            bounce = math.sin(bounce_t * math.pi) * 0.08 * (1.0 - bounce_t)
            arc += bounce
        return (ox + t*dx, oy + t*dy, oz + t*dz + arc)

    # ── execute ──────────────────────────────────────────────────────────────
    # ── MODO 1 COORDENADA: importar personaje en posicion idle ─────────────
    def _execute_idle(self, context, pc, pt):
        """Importa el personaje en el outliner y lo posiciona en la unica coordenada
        con animacion idle (posicion parado) durante el rango frame_inicio→frame_fin_manual."""

        # El invoke() ya garantizo OBJECT mode antes de llegar aqui.
        # 1. Localizar o cargar personaje
        root_empty = bpy.data.objects.get(self.ROOT_NAME)
        if root_empty is None or root_empty.type != "EMPTY":
            blend_path = bpy.path.abspath(pc.blend_filepath) if pc.blend_filepath else ""
            if not blend_path or not os.path.isfile(blend_path):
                try:
                    st = context.scene.jerryst
                    hp = bpy.path.abspath(st.historia_json)
                    if os.path.isfile(hp):
                        import json as _j
                        blend_path = _j.load(open(hp, "r", encoding="utf-8")).get(
                            "configuracion", {}).get("archivo_blend", "")
                        if blend_path:
                            blend_path = bpy.path.abspath(blend_path)
                except Exception:
                    pass
            if not blend_path or not os.path.isfile(blend_path):
                self.report({"ERROR"},
                    f"No se encontro {self.ROOT_NAME!r}. Selecciona el .blend en Paso 1.")
                return {"CANCELLED"}
            if not self._load_character(context, blend_path):
                self.report({"ERROR"}, "No se pudo cargar el personaje.")
                return {"CANCELLED"}

        root_empty = bpy.data.objects.get(self.ROOT_NAME)
        arm_obj    = bpy.data.objects.get(self.ARM_NAME)
        if not arm_obj:
            self.report({"ERROR"}, f"No se encontro armature {self.ARM_NAME!r}.")
            return {"CANCELLED"}

        # 2. Pose bones
        pb = arm_obj.pose.bones
        # Bones completos del rig cuadrupedo de Jerry
        # FIX (Claude, 2026-09-14): faltaban 'jaw_bot', 'sejas_1_jerry' y
        # 'sejas_2_jerry' en esta lista -- por eso una animacion .py
        # importada en una Parada (KEYFRAME_DATA con esos 3 bones) se
        # aplicaba en el archivo EXPORTADO (generate_parada() no usa esta
        # lista, itera KEYFRAME_DATA directo) pero se perdia en "Reproducir
        # recorrido" y, en cascada, en "Concatenar segmentos" (que regenera
        # Capa 1 llamando a este mismo preview antes de capturar
        # _capture_base_bones). constants.BONES_LISTA_FULL ya tenia los 3
        # bones -- ver bug "single source of truth" documentado para este
        # proyecto.
        # FIX 2 (Claude, 2026-09-14): mismo bug, mismo sintoma -- tambien
        # faltaban 'front_shoulder.L' y 'front_shoulder.R'. Un .py importado
        # en una Parada que trae KEYFRAME_DATA['front_shoulder.L'] pasaba
        # por bones.get('front_shoulder.L') -> None -> se descartaba en
        # silencio (ver bloque "elif seg['type'] == 'parada'" mas abajo:
        # `b = bones.get(bone_name); if b is None: continue`). El hombro
        # delantero quedaba inmovil en preview/concatenado aunque el slot
        # exportado si tuviera el movimiento.
        bone_names = [
            'shoulder.L', 'shoulder.R',
            'thigh.L', 'thigh.R',
            'shin.L', 'shin.R',
            'foot.L', 'foot.R',
            'toe.L', 'toe.R',
            'front_shoulder.L', 'front_shoulder.R',
            'front_thigh.L', 'front_thigh.R',
            'front_shin.L', 'front_shin.R',
            'front_foot.L', 'front_foot.R',
            'front_toe.L', 'front_toe.R',
            'spine_1', 'spine_2', 'spine_3', 'spine_4', 'spine_5', 'spine_6', 'spine_7',
            'tail_1', 'tail_2', 'tail_3',
            'scull', 'scull_1', 'neck', 'jaw_top', 'jaw_bot',
            'ear.L', 'ear.R',
            'sejas_1_jerry', 'sejas_2_jerry',
        ]
        bones = {}
        for bn in bone_names:
            b = pb.get(bn)
            if b is not None:
                bones[bn] = b
        if not bones:
            self.report({"ERROR"}, "No se encontraron bones del rig de Jerry")
            return {"CANCELLED"}

        bpy.context.view_layer.objects.active = arm_obj
        if bpy.context.mode != "POSE":
            bpy.ops.object.mode_set(mode="POSE")
        for b in bones.values():
            b.rotation_mode = "XYZ"
        root_empty.rotation_mode = "XYZ"

        # 3. Actions limpias
        ROOT_ACT = "_jerry_preview_root"
        ARM_ACT  = "_jerry_preview_arm"
        for obj, aname in ((root_empty, ROOT_ACT), (arm_obj, ARM_ACT)):
            if not obj.animation_data:
                obj.animation_data_create()
            for track in obj.animation_data.nla_tracks:
                track.mute = True
            old_act = bpy.data.actions.get(aname)
            if old_act:
                bpy.data.actions.remove(old_act, do_unlink=True)
        root_act = bpy.data.actions.new(ROOT_ACT)
        arm_act  = bpy.data.actions.new(ARM_ACT)
        root_empty.animation_data.action = root_act
        arm_obj.animation_data.action    = arm_act

        # 4. Posicion y orientacion fijas en la coordenada unica
        pos_x, pos_y, pos_z = pt.coords[0], pt.coords[1], pt.coords[2]
        rot_z = math.radians(pc.root_rot_z)
        rot_x = math.radians(pc.root_rot_x)
        rot_y = math.radians(pc.root_rot_y)

        start_frame = pc.frame_inicio
        end_frame   = max(pc.frame_fin_manual, start_frame + 1)
        fpb         = max(1, pc.frames_por_bloque) if pc.frames_por_bloque > 0 else 24

        # 5. Insertar keyframes idle en todo el rango
        for frame in range(start_frame, end_frame + 1):  # PERF: ver comentario en JRRSTPR_OT_PreviewPath.execute() (loop "caminar")
            root_empty.location       = (pos_x, pos_y, pos_z)
            root_empty.rotation_euler = (rot_x, rot_y, rot_z)
            self._kf(root_empty, frame)
            # Bones idle: posicion neutral (sin ciclo de caminar)
            rf = frame - start_frame
            self._bones_caminar(bones, frame, 0, fpb)   # rf=0 → pose neutral

        # Suavizar fcurves
        for act in (root_act, arm_act):
            for fc in _get_action_fcurves(act):
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"

        # 6. Configurar timeline y visibilidad
        context.scene.frame_start = start_frame
        context.scene.frame_end   = end_frame
        pc.anim_frame_fin         = end_frame
        context.scene.frame_set(start_frame)

        root_empty.hide_viewport = False
        root_empty.hide_render   = False
        arm_obj.hide_viewport    = False
        arm_obj.hide_render      = False

        total_frames = end_frame - start_frame + 1
        dur_s = round(total_frames / 24, 2)
        self.report({"INFO"},
            f"Personaje importado en outliner | idle en ({pos_x:.2f}, {pos_y:.2f}, {pos_z:.2f}) "
            f"| frames {start_frame}→{end_frame} ({total_frames} fr, {dur_s}s)")
        return {"FINISHED"}

    def invoke(self, context, event):
        """Garantiza contexto OBJECT antes de ejecutar, sin importar el modo actual."""
        global _draw_handle
        pc = context.scene.jerry_path

        # 1. Detener grabacion si estaba activa (antes de cambiar modo)
        if pc.recording_active:
            pc.recording_active = False
            if _draw_handle is not None:
                try:
                    bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
                except Exception:
                    pass
                _draw_handle = None
            for area in context.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()

        # 2. Salir de cualquier modo especial a OBJECT mode
        # Intentamos hasta 3 veces con diferentes estrategias para cubrir
        # EDIT, POSE, SCULPT, etc.
        for _attempt in range(3):
            if context.mode == "OBJECT":
                break
            view3d_area = next((a for a in context.screen.areas if a.type == "VIEW_3D"), None)
            try:
                if context.mode in ("EDIT_MESH", "EDIT_CURVE", "EDIT_ARMATURE"):
                    if view3d_area:
                        region = next((r for r in view3d_area.regions if r.type == "WINDOW"), None)
                        if region:
                            with context.temp_override(area=view3d_area, region=region):
                                bpy.ops.object.editmode_toggle()
                    else:
                        bpy.ops.object.editmode_toggle()
                elif context.mode == "POSE":
                    # En POSE mode, asegurarse de que el objeto activo sea el armature
                    arm = bpy.data.objects.get(self.ARM_NAME)
                    if arm and view3d_area:
                        region = next((r for r in view3d_area.regions if r.type == "WINDOW"), None)
                        if region:
                            with context.temp_override(area=view3d_area, region=region,
                                                       active_object=arm, object=arm):
                                bpy.ops.object.mode_set(mode="OBJECT")
                    else:
                        bpy.ops.object.mode_set(mode="OBJECT")
                else:
                    bpy.ops.object.mode_set(mode="OBJECT")
            except Exception:
                try:
                    bpy.ops.object.mode_set(mode="OBJECT")
                except Exception:
                    pass

        return self.execute(context)

    def execute(self, context):
        pc  = context.scene.jerry_path
        pts = list(pc.path_points)

        # ── Detener grabacion si quedó activa (seguridad) ────────────────────
        if pc.recording_active:
            pc.recording_active = False
            global _draw_handle
            if _draw_handle is not None:
                try:
                    bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
                except Exception:
                    pass
                _draw_handle = None

        # ── CASO ESPECIAL: 1 sola coordenada → importar personaje en posicion idle ──
        if len(pts) == 1:
            return self._execute_idle(context, pc, pts[0])

        if len(pts) < 1:
            self.report({"WARNING"}, "Agrega al menos 1 punto"); return {"CANCELLED"}

        # 1. Localizar o cargar personaje completo
        root_empty = bpy.data.objects.get(self.ROOT_NAME)
        if root_empty is None or root_empty.type != "EMPTY":
            blend_path = bpy.path.abspath(pc.blend_filepath) if pc.blend_filepath else ""
            if not blend_path or not os.path.isfile(blend_path):
                try:
                    st = context.scene.jerryst
                    hp = bpy.path.abspath(st.historia_json)
                    if os.path.isfile(hp):
                        import json as _j
                        blend_path = _j.load(open(hp,"r",encoding="utf-8")).get(
                            "configuracion",{}).get("archivo_blend","")
                        if blend_path: blend_path = bpy.path.abspath(blend_path)
                except Exception: pass
            if not blend_path or not os.path.isfile(blend_path):
                self.report({"ERROR"}, f"No se encontro {self.ROOT_NAME!r}. Selecciona el .blend en Paso 1.")
                return {"CANCELLED"}
            if not self._load_character(context, blend_path):
                self.report({"ERROR"}, "No se pudo cargar el personaje."); return {"CANCELLED"}

        root_empty = bpy.data.objects.get(self.ROOT_NAME)
        arm_obj    = bpy.data.objects.get(self.ARM_NAME)
        if not arm_obj:
            self.report({"ERROR"}, f"No se encontro armature {self.ARM_NAME!r}."); return {"CANCELLED"}

        # 2. Pose bones
        pb = arm_obj.pose.bones
        # Bones completos del rig cuadrupedo de Jerry
        # FIX (Claude, 2026-09-14): mismo fix que en la otra copia de esta
        # lista mas arriba en este archivo -- faltaban 'jaw_bot',
        # 'sejas_1_jerry' y 'sejas_2_jerry'.
        bone_names_rec = [
            'shoulder.L', 'shoulder.R',
            'thigh.L', 'thigh.R',
            'shin.L', 'shin.R',
            'foot.L', 'foot.R',
            'toe.L', 'toe.R',
            'front_shoulder.L', 'front_shoulder.R',
            'front_thigh.L', 'front_thigh.R',
            'front_shin.L', 'front_shin.R',
            'front_foot.L', 'front_foot.R',
            'front_toe.L', 'front_toe.R',
            'spine_1', 'spine_2', 'spine_3', 'spine_4', 'spine_5', 'spine_6', 'spine_7',
            'tail_1', 'tail_2', 'tail_3',
            'scull', 'scull_1', 'neck', 'jaw_top', 'jaw_bot',
            'ear.L', 'ear.R',
            'sejas_1_jerry', 'sejas_2_jerry',
        ]
        bones = {}
        for bn in bone_names_rec:
            b = pb.get(bn)
            if b is not None:
                bones[bn] = b
        if not bones:
            self.report({"ERROR"}, "No se encontraron bones del rig de Jerry"); return {"CANCELLED"}

        bpy.context.view_layer.objects.active = arm_obj
        if bpy.context.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')
        for b in bones.values():
            b.rotation_mode = 'XYZ'
        root_empty.rotation_mode = 'XYZ'

        # 3. Actions limpias — mutear NLA para evitar FCurve errors
        ROOT_ACT = "_jerry_preview_root"
        ARM_ACT  = "_jerry_preview_arm"

        # FIX desincronizacion root/armature:
        # CONCATENAR en modo recorrido deja la seg_action como action directa
        # del armature (sin push al NLA). Si Reproducir recorrido se llama
        # despues de CONCATENAR, la action activa del armature NO es
        # _jerry_preview_arm sino la seg_action — y el bucle de abajo no la
        # elimina correctamente, dejando transformaciones acumuladas.
        # Solucion: desasignar cualquier action directa que no sea la preview
        # ni una Slot_* (es decir, las seg_action de CONCATENAR) sin borrarla,
        # y resetear la transformacion local del armature a cero para que el
        # root empty sea el unico portador de posicion.
        if arm_obj.animation_data and arm_obj.animation_data.action:
            _cur_arm_act = arm_obj.animation_data.action
            if _cur_arm_act.name not in (ARM_ACT,) and not _cur_arm_act.name.startswith("Slot_"):
                # Es una seg_action de CONCATENAR — desasignar sin borrar
                arm_obj.animation_data.action = None
        # Resetear transformacion local del armature: en modo recorrido el
        # armature es hijo del root empty y su posicion local debe ser (0,0,0).
        # Si CONCATENAR o cualquier operacion anterior movio el armature en
        # espacio local, se produce el offset visible en la imagen.
        arm_obj.location       = (0.0, 0.0, 0.0)
        arm_obj.rotation_euler = (0.0, 0.0, 0.0)
        arm_obj.scale          = (1.0, 1.0, 1.0)

        for obj, aname in ((root_empty, ROOT_ACT), (arm_obj, ARM_ACT)):
            if not obj.animation_data:
                obj.animation_data_create()
            for track in obj.animation_data.nla_tracks:
                track.mute = True
                # Cambiar extrapolation a NOTHING para que los tracks no
                # proyecten su valor fuera de su rango (evita el bug de
                # posicion duplicada cuando frame_inicio > 1 y hay tracks
                # con HOLD_FORWARD del Paso 3 activos).
                for strip in track.strips:
                    strip.extrapolation = "NOTHING"
            old = bpy.data.actions.get(aname)
            if old: bpy.data.actions.remove(old, do_unlink=True)
        root_act = bpy.data.actions.new(ROOT_ACT)
        arm_act  = bpy.data.actions.new(ARM_ACT)
        root_empty.animation_data.action = root_act
        arm_obj.animation_data.action    = arm_act

        # Forzar root a origen antes de escribir keyframes para que no
        # arrastre ninguna transformacion residual de animaciones anteriores.
        root_empty.location       = (0.0, 0.0, 0.0)
        root_empty.rotation_euler = (0.0, 0.0, 0.0)

        # 4. Calcular segmentos
        fpb = pc.frames_por_bloque
        root_rot_z_deg = pc.root_rot_z   # en grados, igual que el generador

        # NUEVO (portado de Alfred, 2026-08-05): expandir las paradas marcadas
        # en el Paso 1 (pt.tipo_segmento == "PARADA") ANTES de calcular los
        # segmentos, insertando el punto duplicado que activa la deteccion de
        # "parada" mas abajo (dx==dy==dz==0).
        expanded_pts, frames_paradas_marcadas, anim_files_marcadas, rot_marcadas = _expand_points_with_paradas(pts)
        sync_paradas_frames(pc)
        sync_paradas_frames_from_segments(context)
        sync_walk_styles(pc)
        parada_idx = 0
        caminar_idx = 0
        pts = expanded_pts

        from .generate_slots_jerry import WALK_STYLE_PARAMS as _WSP_prev

        segments = []
        i = 0
        while i < len(pts)-1:
            p0=pts[i]; p1=pts[i+1]
            dx=p1.coords[0]-p0.coords[0]
            dy=p1.coords[1]-p0.coords[1]
            dz=p1.coords[2]-p0.coords[2]
            if _detect_move(p0,p1) == "parada":
                if parada_idx < len(frames_paradas_marcadas):
                    pframes = frames_paradas_marcadas[parada_idx]
                elif parada_idx < len(pc.paradas_frames):
                    pframes = pc.paradas_frames[parada_idx].frames
                else:
                    pframes = pc.frames_parada
                anim_file_esta_parada = (
                    anim_files_marcadas[parada_idx]
                    if parada_idx < len(anim_files_marcadas) else ""
                ) or None
                # NUEVO (portado de Alfred, Kebyn 2026-09-14): orientacion
                # guardada a mano para ESTE punto de parada (ver
                # JRRSTPathPoint.parada_rot_saved / JRRSTPR_OT_SaveParadaRot).
                rot_override_esta_parada = (
                    rot_marcadas[parada_idx] if parada_idx < len(rot_marcadas)
                    else (False, 0.0)
                )
                segments.append({"type":"parada","p0":p0,"p1":p1,"frames":pframes,
                                  "anim_file":anim_file_esta_parada,
                                  "rot_override":rot_override_esta_parada,
                                  "observar":getattr(p0, "tipo_segmento", "AUTO") == "OBSERVAR"})
                parada_idx += 1
                i+=1
            elif _detect_move(p0,p1).startswith('saltar_'):
                kind=_detect_move(p0,p1).removeprefix('saltar_')
                frames=_jump.jump_frame_count(tuple(p0.coords),tuple(p1.coords),kind,
                                               context.scene.render.fps/context.scene.render.fps_base)
                segments.append({'type':kind,'p0':p0,'p1':p1,'frames':frames})
                i+=1
            else:
                j=i
                while j<len(pts)-1 and _detect_move(pts[j],pts[j+1]) == 'caminar':
                    j+=1
                dist=sum(math.sqrt(
                    (pts[k+1].coords[0]-pts[k].coords[0])**2+
                    (pts[k+1].coords[1]-pts[k].coords[1])**2)
                    for k in range(i,j))
                # NUEVO (portado de Alfred, Kebyn 2026-08-05): cada tramo
                # 'caminar' usa su propio estilo (pc.walk_styles[caminar_idx]),
                # que escala tanto los frames (speed_mult) como la amplitud
                # de los bones (_bones_caminar mas abajo).
                walk_style_actual = (pc.walk_styles[caminar_idx].style
                                      if caminar_idx < len(pc.walk_styles) else pc.walk_style)
                _style_prev = _WSP_prev.get(walk_style_actual, _WSP_prev['NORMAL'])
                fpb_efectivo = fpb * _style_prev['speed_mult']
                frames=max(round(fpb_efectivo), round(dist*fpb_efectivo))
                segments.append({"type":"caminar","p0":pts[i],"p1":pts[j],
                                  "frames":frames,"all_pts":pts[i:j+1],
                                  "walk_style":walk_style_actual})
                caminar_idx += 1
                i=j

        # 5. Insertar keyframes
        start_frame   = pc.frame_inicio
        current_frame = start_frame
        prev_dir_deg  = root_rot_z_deg   # angulo inicial en grados

        # NUEVO (portado de Alfred, transiciones entre tramos, Kebyn
        # 2026-09-14): guardan el tipo y el frame final del tramo
        # anterior para poder suavizar el corte cuando el tipo CAMBIA de
        # un tramo al siguiente -- ver el llamado a
        # _suavizar_borde_segmentos_jerry() al final del loop.
        _prev_move_type = None
        _prev_end_frame = None

        for seg in segments:
            _seg_start_frame = current_frame
            p0=seg["p0"]; p1=seg["p1"]; sf=seg["frames"]

            if seg["type"] == "caminar":
                all_pts = seg["all_pts"]
                segs_geo, dists_geo = self._build_caminar_segments(all_pts)
                fps_alloc, cum_alloc = self._alloc_frames(dists_geo, sf)
                # RotationSmoother por segmento de caminar (igual que el generador)
                rot_smoother = self._RotationSmoother(smoothing_frames=12)

                # PERF (Kebyn/Claude, 2026-08-24): antes se hacia
                # bpy.context.scene.frame_set(frame) en cada iteracion. Esto
                # NO hace falta: pos/rotacion se calculan aca con matematica
                # pura (self._get_pos, _compute_direction_angle, el
                # RotationSmoother) y self._kf()/keyframe_insert() ya recibe
                # el frame de forma explicita, sin depender de donde este el
                # playhead. frame_set() fuerza una evaluacion COMPLETA del
                # depsgraph (constraints, modifiers, drivers de todo el
                # personaje) en cada uno de los frames del recorrido -- para
                # un recorrido de 500 frames eso es 500 evaluaciones
                # completas por nada, y es la causa real de la lentitud al
                # "Concatenar segmentos" (que llama a este generador antes de
                # inyectar las poses del Paso 3).
                for f_off in range(sf):
                    frame = current_frame + f_off
                    pf = f_off + 1   # path_frame: 1-based como en el generador
                    pos = self._get_pos(segs_geo, fps_alloc, cum_alloc, min(pf, sf))

                    # Angulo de segmento con _compute_direction_angle identico al generador
                    prev_idx=0
                    seg_ang_deg = prev_dir_deg
                    for j,cf in enumerate(cum_alloc):
                        if pf <= cf:
                            s=segs_geo[j]['start']; e=segs_geo[j]['end']
                            seg_ang_deg = self._compute_direction_angle(
                                e[0]-s[0], e[1]-s[1], prev_dir_deg)
                            break
                        prev_idx=cf

                    smoothed_deg = rot_smoother.smooth_rotation(seg_ang_deg, frame)

                    root_empty.location       = pos
                    root_empty.rotation_euler = (math.radians(pc.root_rot_x),
                                                 math.radians(pc.root_rot_y),
                                                 math.radians(smoothed_deg))
                    self._kf(root_empty, frame)
                    self._bones_caminar(bones, frame, f_off, fpb, walk_style=seg.get("walk_style", "NORMAL"))

                prev_dir_deg = seg_ang_deg if sf > 0 else prev_dir_deg

            elif seg["type"] == "parada":
                # NUEVO (portado de Alfred, 2026-08-05): root inmovil en p0
                # (== p1, son el mismo punto duplicado). Si este punto tiene
                # una animacion .py importada asociada (seg["anim_file"], ver
                # parada_anim_file en JRRSTPathPoint), reproduce ESA
                # animacion en vez de forzar la pose estatica IDLE_POSE_PARADA.
                #
                # BUGFIX (2026-09-14, "al apretar reproducir recorrido, el
                # personaje se queda parado sin reproducir la animacion
                # .py"): antes este bloque descartaba por completo el
                # archivo importado (se leia como "_anim_files_marcadas",
                # con guion bajo = variable intencionalmente ignorada, ver
                # mas arriba en este mismo execute()) y SIEMPRE llamaba a
                # self._bones_parada() (pose fija IDLE_POSE_PARADA en cada
                # frame -- el "canvas limpio" del Paso 3) sin importar si el
                # punto tenia un .py adjunto. La Exportacion real
                # (JRRSTPR_OT_ExportSlots -> generate_parada() en
                # generate_slots_jerry.py) SI leia y aplicaba ese archivo --
                # por eso Exportar funcionaba pero el boton "Reproducir
                # recorrido" (este operador) se veia congelado durante la
                # parada, con la curva plana en el Dope Sheet.
                p0c = (p0.coords[0], p0.coords[1], p0.coords[2])
                anim_kf_data = None
                if seg.get("anim_file") and not seg.get("observar"):
                    try:
                        from .generate_slots_jerry import _load_keyframe_data_from_anim_file
                        anim_kf_data, _frame_count = _load_keyframe_data_from_anim_file(seg["anim_file"])
                    except Exception as e:
                        print(f"jerrypr.preview_path: no se pudo leer la animacion "
                              f"importada '{seg['anim_file']}': {e}")
                        anim_kf_data = None

                # NUEVO (portado de Alfred, Kebyn 2026-09-14): si el
                # usuario guardo una orientacion a mano para este punto de
                # parada (rotar el empty "jerry" y apretar "Guardar
                # orientacion"), ese heading reemplaza a prev_dir_deg tanto
                # para ESTA parada como para el resto del recorrido de aca
                # en adelante -- ver JRRSTPathPoint.parada_rot_saved.
                _rot_saved, _rot_deg = seg.get("rot_override", (False, 0.0))
                if _rot_saved:
                    prev_dir_deg = _rot_deg

                for f_off in range(sf):  # PERF: ver comentario en el loop "caminar" arriba
                    frame = current_frame + f_off
                    root_empty.location       = p0c
                    root_empty.rotation_euler = (math.radians(pc.root_rot_x),
                                                 math.radians(pc.root_rot_y),
                                                 math.radians(prev_dir_deg))
                    self._kf(root_empty, frame)
                    if not anim_kf_data and not seg.get("observar"):
                        self._bones_parada(bones, frame)
                if seg.get("observar"):
                    # NUEVO (Kebyn, 2026-09-24): Observar -- se sienta, gira
                    # la cabeza de derecha a izquierda y se para (ver
                    # observar_motion.py). Keyframes esparcidos; el paso
                    # 'Suavizar fcurves' de mas abajo los pasa a BEZIER.
                    _rot_kf, _loc_kf = _observar.build_observar_keyframes(sf, IDLE_POSE_PARADA)
                    for bone_name, bone_kf in _rot_kf.items():
                        b = bones.get(bone_name)
                        if b is None:
                            continue
                        b.rotation_mode = 'XYZ'
                        for f_off, rot in bone_kf.items():
                            b.rotation_euler = rot
                            self._kfb(b, current_frame + f_off)
                    for bone_name, bone_kf in _loc_kf.items():
                        b = bones.get(bone_name)
                        if b is None:
                            continue
                        for f_off, loc in bone_kf.items():
                            b.location = loc
                            b.keyframe_insert(data_path="location", frame=current_frame + f_off)
                if anim_kf_data:
                    # A diferencia de _bones_parada (un keyframe en CADA
                    # frame), la animacion importada solo trae keyframes en
                    # los frames que el .py original definio -- igual que
                    # _build_parada_anim_importada_block_jerry() del lado de
                    # Exportacion, para no aplanar la curva original.
                    for bone_name, bone_kf in anim_kf_data.items():
                        b = bones.get(bone_name)
                        if b is None:
                            continue
                        b.rotation_mode = 'XYZ'
                        for f_off, rot in bone_kf.items():
                            if f_off >= sf:
                                continue
                            b.rotation_euler = rot
                            self._kfb(b, current_frame + f_off)
                # prev_dir_deg solo cambia si el usuario guardo una
                # orientacion a mano para este punto (rot_override arriba);
                # de lo contrario la parada no reorienta al personaje

            else:  # salto subir / bajar
                p0c = (p0.coords[0], p0.coords[1], p0.coords[2])
                p1c = (p1.coords[0], p1.coords[1], p1.coords[2])
                # Angulo fijo para el salto: _compute_direction_angle del p0->p1
                dir_deg = self._compute_direction_angle(
                    p1.coords[0]-p0.coords[0],
                    p1.coords[1]-p0.coords[1],
                    prev_dir_deg)

                timing=_jump.jump_timing(p0c,p1c,seg['type'],context.scene.render.fps/context.scene.render.fps_base)
                rot=(pc.root_rot_x,pc.root_rot_y,prev_dir_deg)
                for f_off in range(sf):
                    frame=current_frame+f_off
                    phase=_jump.jump_phase(f_off,timing)
                    _jump.key_root(root_empty,frame,p0c,p1c,phase,seg['type'],rot)
                    _jump.key_pose(bones,frame,phase,seg['type'])

                prev_dir_deg = dir_deg

            # NUEVO (portado de Alfred, transiciones entre tramos): solo
            # tiene sentido suavizar el corte cuando el tramo anterior
            # existe Y su tipo es DISTINTO al de este tramo (ej. Caminar
            # -> Parada). Entre dos tramos del MISMO tipo (ej. dos
            # "Caminar" seguidos) el movimiento ya es continuo -- aplicar
            # esto ahi rompería el ciclo de marcha en vez de arreglar algo.
            if (pc.usar_transiciones and _prev_move_type is not None
                    and _prev_move_type != seg["type"]
                    and _prev_move_type not in ('subir','bajar','horizontal')
                    and seg['type'] not in ('subir','bajar','horizontal')):
                _suavizar_borde_segmentos_jerry(
                    arm_act, root_act, _prev_end_frame, _seg_start_frame,
                    pc.frames_transicion)

            _prev_move_type = seg["type"]
            _prev_end_frame = _seg_start_frame + sf - 1

            current_frame += sf

        # Keyframe final
        last=pts[-1]
        bpy.context.scene.frame_set(current_frame-1)
        root_empty.location=(last.coords[0],last.coords[1],last.coords[2])
        root_empty.rotation_euler=(0.0,0.0,math.radians(prev_dir_deg))
        self._kf(root_empty, current_frame-1)

        # Suavizar fcurves del recorrido base
        for act in (root_act, arm_act):
            for fc in _get_action_fcurves(act):
                for kp in fc.keyframe_points:
                    kp.interpolation="BEZIER"; kp.easing="AUTO"

        jump_cursor=start_frame
        jump_ranges=[]
        for item in segments:
            if item['type'] in ('subir','bajar','horizontal'):
                jump_ranges.append((jump_cursor,jump_cursor+item['frames']-1))
            jump_cursor+=item['frames']
        for act in (root_act,arm_act):
            for fc in _get_action_fcurves(act):
                for kp in fc.keyframe_points:
                    if any(a<=kp.co.x<=b for a,b in jump_ranges): kp.interpolation='LINEAR'

        # ── Overlay de configuracion (Capa 2) ─────────────────────────────────
        # Si existe configuracion del Paso 3 (CONCATENAR ya fue ejecutado),
        # los bones configurados en cada segmento activo deben prevalecer sobre
        # la animacion base del recorrido en su rango de frames.
        # Overlay Paso 3: copiar poses concatenadas (bones NO filtrados) desde
        # cada seg_action hacia arm_act, sobreescribiendo el ciclo base solo
        # en los bones y frames donde el usuario configuro poses.
        # Los bones FILTRADOS en el segmento NO se tocan aqui: sus keyframes
        # vienen del ciclo base generado arriba (caminar/saltar/etc.).
        segs_paso3 = getattr(context.scene, "jerry_segs", None)
        if segs_paso3 and len(segs_paso3.segments) > 0:
            try:
                from .operators_segments import _BONE_FILTER_MAP, _bone_is_filtered
            except Exception:
                _BONE_FILTER_MAP = {}
                _bone_is_filtered = lambda seg, bn: False
            from .constants import BONES_LISTA_FULL as _ALL_BONES
            for seg in segs_paso3.segments:
                if not seg.enabled:
                    continue
                seg_action = bpy.data.actions.get(seg.seg_action_name) if seg.seg_action_name else None
                if seg_action is None:
                    continue
                f_seg_start = seg.frame_start
                f_seg_end   = seg.frame_end if seg.frame_end > seg.frame_start else seg.frame_end_auto
                if f_seg_end <= f_seg_start:
                    continue
                # Bones que recibieron poses = los NO filtrados por el usuario
                pose_bones = [bn for bn in _ALL_BONES if not _bone_is_filtered(seg, bn)]
                if not pose_bones:
                    continue
                # Copiar fcurves de poses: seg_action → arm_act
                for bone_name in pose_bones:
                    for dp in (
                        f'pose.bones["{bone_name}"].rotation_euler',
                        f'pose.bones["{bone_name}"].location',
                        f'pose.bones["{bone_name}"].scale',
                    ):
                        for axis_i in range(3):
                            src_fc = _get_action_fcurves(seg_action).find(dp, index=axis_i)
                            if src_fc is None:
                                continue
                            dst_fc = _get_action_fcurves(arm_act).find(dp, index=axis_i)
                            if dst_fc is None:
                                dst_fc = _new_fcurve(_get_action_fcurves(arm_act), dp, index=axis_i,
                                                      action_group=bone_name)
                            for kp in src_fc.keyframe_points:
                                frame_val = kp.co.x
                                if f_seg_start <= frame_val <= f_seg_end:
                                    existing = next(
                                        (dkp for dkp in dst_fc.keyframe_points
                                         if abs(dkp.co.x - frame_val) < 0.5), None)
                                    if existing:
                                        existing.co.y         = kp.co.y
                                        existing.interpolation = kp.interpolation
                                        existing.easing        = kp.easing
                                    else:
                                        new_kp = dst_fc.keyframe_points.insert(
                                            frame=frame_val, value=kp.co.y,
                                            options={"FAST"})
                                        new_kp.interpolation = kp.interpolation
                                        new_kp.easing        = kp.easing
                            dst_fc.update()

        # 6. Timeline y playback
        total_end = current_frame-1
        context.scene.frame_start = start_frame
        context.scene.frame_end   = total_end
        # ── Registrar rango para que Paso 3 pueda validar segmentos ──────────
        pc.anim_frame_fin = total_end
        context.scene.frame_set(start_frame)
        root_empty.hide_viewport=False; root_empty.hide_render=False
        arm_obj.hide_viewport=False;    arm_obj.hide_render=False
        bpy.ops.screen.animation_play()

        self.report({"INFO"},
            f"Preview: {len(pts)} pts | {len(segments)} segs | "
            f"{total_end-start_frame+1} frames")
        return {"FINISHED"}


class JRRSTPR_OT_ResetPreview(Operator):
    """Elimina las actions de preview y resetea posicion del personaje."""
    bl_idname  = "jerrypr.reset_preview"
    bl_label   = "Reset recorrido"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_cancel(restore_frame=True)
        for obj_name, act_name in (
            ("jerry",      "_jerry_preview_root"),
            ("Dog_001_rig", "_jerry_preview_arm"),
        ):
            obj = bpy.data.objects.get(obj_name)
            if obj and obj.animation_data:
                act = bpy.data.actions.get(act_name)
                if obj.animation_data.action == act:
                    obj.animation_data.action = None
                if act:
                    bpy.data.actions.remove(act, do_unlink=True)
                for track in obj.animation_data.nla_tracks:
                    track.mute = False
                    # Restaurar extrapolation HOLD_FORWARD a los tracks
                    # root del Paso 3 (que la preview cambio a NOTHING).
                    for strip in track.strips:
                        if strip.extrapolation == "NOTHING" and strip.name.startswith("Slot_"):
                            strip.extrapolation = "HOLD_FORWARD"
        root = bpy.data.objects.get("jerry")
        if root:
            root.location=(0,0,0); root.rotation_euler=(0,0,0)
        self.report({"INFO"}, "Preview reseteada")
        return {"FINISHED"}

# =============================================================================
# REGISTRO
# =============================================================================

class JRRSTPR_OT_SetAnimRange(Operator):
    """Establece manualmente el rango de animacion del Paso 2.
    Util cuando la animacion ya existe y anim_frame_fin no fue guardado."""
    bl_idname  = "jerrypr.set_anim_range"
    bl_label   = "Fijar rango de animacion"
    bl_description = (
        "Registra el rango [frame_inicio, frame_fin] de la animacion existente "
        "para que el Paso 3 pueda validar y crear segmentos correctamente"
    )
    bl_options = {"REGISTER", "UNDO"}

    frame_fin: bpy.props.IntProperty(
        name="Frame fin de animacion",
        description="Ultimo frame de la animacion de recorrido generada",
        default=1,
        min=1,
        soft_max=99999,
    )

    def invoke(self, context, event):
        pc = context.scene.jerry_path
        # Pre-rellenar con el valor actual o con frame_end de la escena
        self.frame_fin = pc.anim_frame_fin if pc.anim_frame_fin > 0 else context.scene.frame_end
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        pc = context.scene.jerry_path
        if self.frame_fin <= pc.frame_inicio:
            self.report({"ERROR"}, f"Frame fin ({self.frame_fin}) debe ser mayor que frame inicio ({pc.frame_inicio})")
            return {"CANCELLED"}
        pc.anim_frame_fin = self.frame_fin
        self.report({"INFO"}, f"Rango animacion: {pc.frame_inicio} → {self.frame_fin}  ({self.frame_fin - pc.frame_inicio + 1} frames)")
        return {"FINISHED"}



class JRRSTPR_OT_ExportSlots(bpy.types.Operator):
    """Exporta los scripts de slots del recorrido (caminar/saltar_subir/saltar_bajar)."""
    bl_idname  = "jerrypr.export_slots"
    bl_label   = "Exportar recorrido (slots)"
    bl_description = (
        "Genera los scripts de slots del recorrido en la carpeta de salida. "
        "Equivalente a ejecutar generate_slots_jerry.py"
    )
    bl_options = {"REGISTER"}

    def execute(self, context):
        import os, importlib.util as _ilu
        from datetime import date

        pc  = context.scene.jerry_path
        pts = list(pc.path_points)
        n_pts = len(pts)

        # 1 coordenada Y 0 coordenadas no son validas para recorrido,
        # pero 1 coordenada SI es valida para exportar idle
        if n_pts == 0:
            self.report({"ERROR"}, "Agrega al menos 1 punto de recorrido antes de exportar")
            return {"CANCELLED"}

        output_dir = bpy.path.abspath(pc.output_dir) if pc.output_dir else ""
        if not output_dir:
            self.report({"ERROR"}, "Define la carpeta de salida en el Paso 2 antes de exportar")
            return {"CANCELLED"}

        os.makedirs(output_dir, exist_ok=True)

        addon_dir = os.path.dirname(os.path.abspath(__file__))
        gen_path  = os.path.join(addon_dir, "generate_slots_jerry.py")
        if not os.path.exists(gen_path):
            self.report({"ERROR"},
                f"No se encontro generate_slots_jerry.py en {gen_path}. "
                "Copia el archivo al directorio del addon.")
            return {"CANCELLED"}

        spec = _ilu.spec_from_file_location(__package__ + ".generate_slots_jerry", gen_path)
        gen  = _ilu.module_from_spec(spec)
        spec.loader.exec_module(gen)

        today         = date.today().isoformat()
        root_rot      = (pc.root_rot_x, pc.root_rot_y, pc.root_rot_z)
        slot_index    = pc.slot_inicio
        current_frame = pc.frame_inicio

        # ── CASO 1 COORDENADA: generar slot idle (personaje parado) ──────────
        if n_pts == 1:
            pt = pts[0]
            point = {
                "index": 0,
                "coordinates": {"x": pt.coords[0], "y": pt.coords[1], "z": pt.coords[2]},
                "texture": pt.texture or "grass_block_top",
            }
            # Duracion: desde frame_inicio hasta frame_fin_manual
            total_frames_idle = max(1, pc.frame_fin_manual - pc.frame_inicio + 1)
            code, end_frame = gen.generate_idle(
                slot_index, current_frame, point, today, root_rot,
                total_frames=total_frames_idle
            )
            fname = f"slot_{slot_index:03d}_jerry_idle.py"
            with open(os.path.join(output_dir, fname), "w", encoding="utf-8") as f:
                f.write(code)
            pc.anim_frame_fin = end_frame
            self.report({"INFO"},
                f"Exportacion OK: 1 slot idle | "
                f"frames {pc.frame_inicio}→{end_frame} ({total_frames_idle} fr) | {output_dir}")
            return {"FINISHED"}

        # ── CASO RECORRIDO (>1 coordenada): generar slots caminar/saltar/parada
        # NUEVO (portado de Alfred, 2026-08-05): expandir primero las paradas
        # marcadas en el Paso 1 (pt.tipo_segmento == "PARADA") sobre los
        # PropertyGroup originales -- _expand_points_with_paradas necesita
        # los atributos tipo_segmento/parada_frames_punto, que los dicts de
        # key_points no tienen.
        expanded_pts, frames_paradas_marcadas, anim_files_paradas_marcadas, rot_paradas_marcadas = _expand_points_with_paradas(pts)
        key_points = [
            {"index": i,
             "coordinates": {"x": pt.coords[0], "y": pt.coords[1], "z": pt.coords[2]},
             "texture": (pt.texture or "grass_block_top"), "tipo_segmento": getattr(pt,"tipo_segmento","AUTO")}
            for i, pt in enumerate(expanded_pts)
        ]

        segments = gen.group_segments(key_points)

        sync_paradas_frames(pc)
        sync_paradas_frames_from_segments(context)
        sync_walk_styles(pc)
        parada_idx  = 0
        caminar_idx = 0

        prev_rz_exp = root_rot[2]
        for seg in segments:
            move_type = seg["type"]
            points    = seg["points"]

            # Calcular dir_angle para actualizar prev_rz al final
            if len(points) >= 2:
                _p0 = points[0]["coordinates"]
                _p1 = points[-1]["coordinates"]
                _da = gen._compute_direction_angle(_p0, _p1)
            else:
                _da = None

            _cur_rot = (root_rot[0], root_rot[1], prev_rz_exp)
            if move_type == 'saltar_horizontal':
                code,end_frame=gen.generate_saltar_horizontal(slot_index,current_frame,points,today,prev_rz_exp,_cur_rot,
                    fps=context.scene.render.fps/context.scene.render.fps_base)
                fname=f"slot_{slot_index:03d}_jerry_saltar_horizontal.py"
            elif move_type == "saltar_subir":
                code, end_frame = gen.generate_saltar_subir(slot_index, current_frame, points, today, prev_rz_exp, _cur_rot, fps=context.scene.render.fps/context.scene.render.fps_base)
                fname = f"slot_{slot_index:03d}_jerry_saltar_subir.py"
            elif move_type == "saltar_bajar":
                code, end_frame = gen.generate_saltar_bajar(slot_index, current_frame, points, today, prev_rz_exp, _cur_rot, fps=context.scene.render.fps/context.scene.render.fps_base)
                fname = f"slot_{slot_index:03d}_jerry_saltar_bajar.py"
            elif move_type == "parada":
                if parada_idx < len(frames_paradas_marcadas):
                    frames_esta_parada = frames_paradas_marcadas[parada_idx]
                elif parada_idx < len(pc.paradas_frames):
                    frames_esta_parada = pc.paradas_frames[parada_idx].frames
                else:
                    frames_esta_parada = pc.frames_parada
                anim_file_esta_parada = (
                    anim_files_paradas_marcadas[parada_idx]
                    if parada_idx < len(anim_files_paradas_marcadas) else ""
                ) or None
                # NUEVO (portado de Alfred, Kebyn 2026-09-14): orientacion
                # guardada a mano para ESTE punto de parada (ver
                # JRRSTPathPoint.parada_rot_saved / JRRSTPR_OT_SaveParadaRot).
                # Si esta activa, reemplaza el heading automatico
                # (prev_rz_exp) tanto para ESTA parada como para el resto
                # del recorrido de aca en adelante -- hasta el proximo
                # tramo con desplazamiento real (que recalcula su propio
                # heading), o hasta que se vuelva a editar este punto.
                if parada_idx < len(rot_paradas_marcadas):
                    _rot_saved, _rot_deg = rot_paradas_marcadas[parada_idx]
                    if _rot_saved:
                        prev_rz_exp = _rot_deg
                        _cur_rot = (root_rot[0], root_rot[1], prev_rz_exp)
                _es_observar = points[0].get("tipo_segmento", "AUTO") == "OBSERVAR"
                code, end_frame = gen.generate_parada(
                    slot_index, current_frame, points, today, _cur_rot,
                    frames_parada=frames_esta_parada,
                    anim_file_path=anim_file_esta_parada,
                    observar=_es_observar)
                fname = (f"slot_{slot_index:03d}_jerry_observar.py" if _es_observar
                         else f"slot_{slot_index:03d}_jerry_parada.py")
                parada_idx += 1
            else:
                walk_style_actual = (pc.walk_styles[caminar_idx].style
                                      if caminar_idx < len(pc.walk_styles) else pc.walk_style)
                code, end_frame = gen.generate_caminar(
                    slot_index, current_frame, points, today, prev_rz_exp, _cur_rot,
                    walk_style=walk_style_actual, frames_por_bloque=pc.frames_por_bloque)
                fname = f"slot_{slot_index:03d}_jerry_caminar.py"
                caminar_idx += 1
            with open(os.path.join(output_dir, fname), "w", encoding="utf-8") as f:
                f.write(code)
            if _da is not None:
                prev_rz_exp = _da
            current_frame = end_frame + 1
            slot_index   += 1

        pc.anim_frame_fin = current_frame - 1
        total_frames = current_frame - pc.frame_inicio
        self.report({"INFO"},
            f"Exportacion OK: {slot_index - pc.slot_inicio} slots | "
            f"frames {pc.frame_inicio}→{current_frame-1} ({total_frames} fr) | {output_dir}")
        return {"FINISHED"}

pr_classes = (
    JRRSTPathPoint,
    JRRSTParadaFrames,
    JRRSTWalkStyleEntry,
    JRRSTPathSettings,
    JRRSTPR_OT_ToggleRecording,
    JRRSTPR_OT_RemoveLast,
    JRRSTPR_OT_ClearPath,
    JRRSTPR_OT_ImportParadaAnim,
    JRRSTPR_OT_ClearParadaAnim,
    JRRSTPR_OT_OpenInteractionFolder,
    JRRSTPR_OT_RotateParadaRoot,
    JRRSTPR_OT_SaveParadaRot,
    JRRSTPR_OT_ClearParadaRot,
    JRRSTPR_OT_GenerateSlots,
    JRRSTPR_OT_OpenBlendFile,
    JRRSTPR_OT_PreviewPath,
    JRRSTPR_OT_ResetPreview,
    JRRSTPR_OT_SetAnimRange,
    JRRSTPR_OT_ExportSlots,
    JRRSTPR_OT_SyncParadasFrames,
)


def register_path_recorder():
    for cls in pr_classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.jerry_path = bpy.props.PointerProperty(type=JRRSTPathSettings)
    if _jerry_face_selection_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_jerry_face_selection_handler)


def unregister_path_recorder():
    global _draw_handle
    if _draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
        _draw_handle = None
    if _jerry_face_selection_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_jerry_face_selection_handler)
    for cls in reversed(pr_classes):
        bpy.utils.unregister_class(cls)
    if hasattr(bpy.types.Scene, "jerry_path"):
        del bpy.types.Scene.jerry_path
