# -*- coding: utf-8 -*-
"""
path_recorder.py — Cerdo_1 Animation Studio
Sistema integrado de trazado de recorrido y generacion de slots.

FLUJO:
  1. El usuario selecciona faces en modo EDIT del mesh de escenario.
     Cada face seleccionada se agrega automaticamente como un punto del recorrido.
  2. El sistema detecta los segmentos: caminar / saltar_subir / saltar_bajar / parada.
  3. Con un solo boton "GENERAR SLOTS" se crean los scripts slot_NNN_*.py
     y opcionalmente se ejecutan directamente en Blender (InScene).

Sin sistema de tunel — solo coordenadas de faces (centros de poligono).
"""

import bpy
from . import jump_motion as _jump
import bmesh
import blf
import gpu
import json
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
from .blender_compat import get_fcurves
from .constants import (
    DEFAULT_INTERACTION_DIR_CERDO_1,
    DEFAULT_INTERACTION_DIR_JERRY,
    INTERACTION_MEETING_TOLERANCE,
)

# ── Variables globales de modulo ──────────────────────────────────────────────
_draw_handle    = None
_last_face_idx  = None


def _deferred_deselect_face(obj_name, face_index):
    """FIX (Kebyn, 2026-08-23 v3): deselecciona la cara recien registrada,
    pero diferido via bpy.app.timers en vez de hacerlo directo dentro de
    _cerdo_1_face_selection_handler(). Modificar la seleccion del bmesh
    (face.select + bmesh.update_edit_mesh()) DENTRO de un handler de
    depsgraph_update_post no es seguro: depsgraph_update_post es, en la
    practica, de solo lectura -- Blender esta en medio de evaluar el
    depsgraph cuando el handler corre, y una escritura ahi puede no
    aplicarse (o aplicarse y quedar pisada por el propio ciclo de
    evaluacion que sigue corriendo), que es exactamente lo que pasaba:
    la cara se veia visualmente igual de seleccionada despues del "fix"
    anterior, asi que el siguiente clic sobre ella seguia sin generar un
    cambio real de estado y el handler nunca se volvia a disparar. Este
    timer corre en el siguiente tick del event loop, YA AFUERA del
    depsgraph_update_post, que es el contexto seguro para tocar la malla.
    """
    obj = bpy.data.objects.get(obj_name)
    if obj is None or obj.type != "MESH" or obj.mode != "EDIT":
        return None
    bm = bmesh.from_edit_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    if 0 <= face_index < len(bm.faces):
        bm.faces[face_index].select = False
        bmesh.update_edit_mesh(obj.data)
    return None  # no repetir el timer

# =============================================================================
# PROPERTY GROUPS
# =============================================================================

from .woodcut_animation import is_woodcut, group_woodcut_points, WOODCUT_FRAMES

# =============================================================================
# SISTEMA DE INTERACCION ENTRE PERSONAJES (Cerdo_1 <-> Jerry)
# =============================================================================
# NUEVO (Kebyn): cuando el recorrido de Cerdo_1 y el recorrido de Jerry
# tienen una coordenada en comun (dentro de INTERACTION_MEETING_TOLERANCE,
# ver constants.py), ese punto se considera un "punto de encuentro" y
# habilita ahi la opcion 'Interactuar' en el dropdown de tipo_segmento
# (ver _tipo_segmento_items() mas abajo). El dropdown de que animacion
# reproducir (interaccion_anim_choice) lista los .py encontrados en
# DEFAULT_INTERACTION_DIR_CERDO_1 -- cada personaje reproduce su propia
# mitad de la interaccion desde su propia carpeta.
#
# Los caches _tipo_segmento_dynamic_cache / _interaccion_anim_cache
# existen porque bpy exige que la lista de tuplas devuelta por un
# items=funcion de EnumProperty se mantenga viva en memoria mientras el
# enum este dibujado (Blender no la copia) -- sin esto, las strings de
# los items pueden liberarse y corromper el dropdown. Se indexan por
# as_pointer() del propio CERDO_1PathPoint, que es estable mientras el
# punto exista en la coleccion.

_tipo_segmento_dynamic_cache = {}
_interaccion_anim_cache      = {}


def _other_character_path_coords(context):
    """Coordenadas (lista de tuplas x,y,z) del recorrido de Jerry, visto
    desde el addon de Cerdo_1. Devuelve [] si Jerry Animation Studio no
    esta instalado/registrado en esta escena o todavia no tiene puntos.
    """
    scene = getattr(context, "scene", None)
    if scene is None:
        return []
    other_pc = getattr(scene, "jerry_path", None)
    if other_pc is None:
        return []
    return [tuple(p.coords) for p in other_pc.path_points]


def _point_is_meeting_point(context, pt):
    """True si `pt` (un CERDO_1PathPoint) cae, dentro de
    INTERACTION_MEETING_TOLERANCE, sobre alguna coordenada del
    recorrido de Jerry -- ver circulo rojo del diagrama de referencia
    (dos recorridos que se cruzan en un mismo punto).
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
# un punto de encuentro real con Jerry -- por eso vive aparte, al final
# de esta lista, y no adentro de ella.
_TIPO_SEGMENTO_BASE_ITEMS = [
    ("CORTAR_MADERA_INFERIOR", "Cortar madera inferior", "Cuatro golpes al bloque inferior de enfrente; una sola coordenada", "MOD_BUILD", 10),
    ("CORTAR_MADERA_INTERMEDIO", "Cortar madera intermedio", "Cuatro golpes al bloque a media altura; una sola coordenada", "MOD_BUILD", 11),
    ("CORTAR_MADERA_SUPERIOR", "Cortar madera superior", "Cuatro golpes al bloque superior; una sola coordenada", "MOD_BUILD", 12),
    ("AUTO",   "Caminar", "Movimiento automatico: caminar o saltar segun la geometria", "ANIM_DATA", 0),
    ("SALTAR", "Saltar", "Saltar desde este punto hasta el siguiente; duracion automatica incluso a la misma altura", "IPO_QUAD", 50),
    ("PARADA", "Parada",  "El personaje se detiene en este punto antes de continuar",   "PAUSE",     1),
    # NUEVO (Kebyn, 2026-08-21): 'colocar_antorcha' abarca DOS
    # coordenadas REALES consecutivas del recorrido -- este punto
    # y el siguiente -- igual que 'saltar_subir'/'saltar_bajar'
    # (a diferencia de PARADA, que duplica el mismo punto). El
    # personaje camina hasta el siguiente punto, se agacha y
    # planta una antorcha ahi (ver generate_colocar_antorcha() en
    # generate_slots_cerdo_1.py); la antorcha en si se importa y
    # coloca via el Sistema de Lanzar/Recoger/Mantener Objetos
    # (seg.throws), fuente antorcha_1.blend.
    ("COLOCAR_ANTORCHA", "Colocar antorcha",
     "El personaje camina hasta el siguiente punto, se agacha y "
     "planta una antorcha en el suelo ahi. Abarca este punto y el "
     "siguiente (coordenadas reales, sin duplicar)",
     "OUTLINER_OB_LIGHT", 2),
    # NUEVO (Kebyn): "golpe_estomago_1" -- misma arquitectura que
    # "colocar_antorcha" (abarca este punto y el siguiente,
    # coordenadas reales, sin duplicar), pero en vez de plantar un
    # objeto reproduce una animacion completa importada de Mixamo
    # (14 huesos, 100 frames) con el personaje parado en este
    # punto. Ver generate_golpe_estomago_1() en
    # generate_slots_cerdo_1.py.
    ("GOLPE_ESTOMAGO_1", "Golpe estomago",
     "El personaje se detiene en este punto y realiza una "
     "animacion completa de golpe al estomago (Mixamo, 14 huesos). "
     "Abarca este punto y el siguiente (coordenadas reales, sin "
     "duplicar)",
     "ARMATURE_DATA", 3),
    # NUEVO (Kebyn, 2026-08-22): "colocar_mesa_de_crafteo" --
    # misma arquitectura que "colocar_antorcha" (abarca este
    # punto y el siguiente, coordenadas reales, sin duplicar): el
    # personaje camina hasta el siguiente punto, se agacha y
    # coloca una mesa de crafteo en el suelo ahi (ver
    # generate_colocar_mesa_crafteo() en generate_slots_cerdo_1.py);
    # la mesa en si se importa y coloca via el Sistema de Lanzar/
    # Recoger/Mantener Objetos (seg.throws), fuente
    # mesa_de_crafteo_1.blend.
    ("COLOCAR_MESA_CRAFTEO", "Colocar mesa de crafteo",
     "El personaje camina hasta el siguiente punto, se agacha y "
     "coloca una mesa de crafteo en el suelo ahi. Abarca este "
     "punto y el siguiente (coordenadas reales, sin duplicar)",
     "OUTLINER_OB_MESH", 4),
    # NUEVO (Kebyn): "levantarse_1" -- misma arquitectura que
    # "golpe_estomago_1" (abarca este punto y el siguiente,
    # coordenadas reales, sin duplicar): el personaje se detiene
    # en este punto y reproduce una animacion completa importada
    # de Mixamo (14 huesos, 107 frames) de levantarse del suelo.
    # Ver generate_levantarse_1() en generate_slots_cerdo_1.py.
    ("LEVANTARSE_1", "Levantarse",
     "El personaje se detiene en este punto y realiza una "
     "animacion completa de levantarse del suelo (Mixamo, 14 "
     "huesos). Abarca este punto y el siguiente (coordenadas "
     "reales, sin duplicar)",
     "ARMATURE_DATA", 5),
    # NUEVO (Kebyn): "levantarse_2" -- segunda variante de
    # "levantarse_1" (misma arquitectura, otro clip Mixamo, 14
    # huesos, 183 frames). Abarca este punto y el siguiente
    # (coordenadas reales, sin duplicar). Ver
    # generate_levantarse_2() en generate_slots_cerdo_1.py.
    ("LEVANTARSE_2", "Levantarse (variante 2)",
     "El personaje se detiene en este punto y realiza una "
     "segunda variante de la animacion completa de levantarse "
     "del suelo (Mixamo, 14 huesos). Abarca este punto y el "
     "siguiente (coordenadas reales, sin duplicar)",
     "ARMATURE_DATA", 6),
    # NUEVO (Kebyn): "arrodillarse_1" -- misma arquitectura que
    # "levantarse_1"/"levantarse_2"/"golpe_estomago_1" (abarca
    # este punto y el siguiente, coordenadas reales, sin
    # duplicar): el personaje se detiene en este punto y
    # reproduce una animacion completa importada de Mixamo (14
    # huesos, 49 frames) de arrodillarse. Ver
    # generate_arrodillarse_1() en generate_slots_cerdo_1.py.
    ("ARRODILLARSE_1", "Arrodillarse",
     "El personaje se detiene en este punto y realiza una "
     "animacion completa de arrodillarse (Mixamo, 14 huesos). "
     "Abarca este punto y el siguiente (coordenadas reales, sin "
     "duplicar)",
     "ARMATURE_DATA", 7),
    # NUEVO (Kebyn): "conversar_1" -- misma arquitectura que
    # "arrodillarse_1"/"levantarse_1"/"golpe_estomago_1" (abarca
    # este punto y el siguiente, coordenadas reales, sin
    # duplicar): el personaje se detiene en este punto y
    # reproduce una animacion completa importada de Mixamo (14
    # huesos, 95 frames) de conversar. Ver generate_conversar_1()
    # en generate_slots_cerdo_1.py.
    ("CONVERSAR_1", "Conversar",
     "El personaje se detiene en este punto y realiza una "
     "animacion completa de conversar (Mixamo, 14 huesos). "
     "Abarca este punto y el siguiente (coordenadas reales, sin "
     "duplicar)",
     "OUTLINER_OB_ARMATURE", 8),
    # NUEVO (Kebyn): "resbalarse_1" -- misma arquitectura que
    # "arrodillarse_1"/"levantarse_1"/"golpe_estomago_1" (abarca
    # este punto y el siguiente, coordenadas reales, sin
    # duplicar): el personaje se detiene en este punto y
    # reproduce una animacion completa importada de Mixamo (14
    # huesos, 51 frames) de resbalarse/caida. Ver
    # generate_resbalarse_1() en generate_slots_cerdo_1.py.
    ("RESBALARSE_1", "Resbalarse",
     "El personaje se detiene en este punto y realiza una "
     "animacion completa de resbalarse/caida (Mixamo, 14 "
     "huesos). Abarca este punto y el siguiente (coordenadas "
     "reales, sin duplicar)",
     "MOD_PHYSICS", 9),
    # NUEVO (Kebyn, pedido "crear pared NxN bloques"): misma
    # arquitectura que "colocar_mesa_de_crafteo"/"colocar_antorcha"
    # (abarca este punto y el siguiente, coordenadas reales, sin
    # duplicar): el personaje se queda parado en este punto y coloca,
    # uno por uno, una grilla de FILAS x COLUMNAS bloques de 1m3 frente
    # a el -- el archivo .blend del bloque (elegido por Kebyn en el
    # panel, campo "pared_bloque_blend_path") y el tamano de la grilla
    # ("pared_filas"/"pared_columnas") se configuran en este mismo
    # punto. Ver generate_crear_pared_nxn() en generate_slots_cerdo_1.py.
    ("CREAR_PARED_NXN", "Crear pared NxN bloques",
     "El personaje se detiene en este punto y coloca una grilla de "
     "FilasxColumnas bloques de 1m3 (elegidos por archivo .blend) "
     "frente a el, uno por uno. Abarca este punto y el siguiente "
     "(coordenadas reales, sin duplicar)",
     "MESH_GRID", 13),

]

# 'INTERACTUAR' se agrega SOLO cuando el punto es un punto de encuentro
# real con Jerry (ver _point_is_meeting_point() mas arriba) -- por eso
# tipo_segmento usa una funcion items= en vez de una lista estatica: la
# opcion literalmente desaparece del dropdown si el recorrido se edita
# despues y las coordenadas dejan de coincidir.
def _tipo_segmento_items(self, context):
    items = [it for it in _TIPO_SEGMENTO_BASE_ITEMS if it[0] in ("AUTO", "SALTAR", "PARADA")]   # cerdo: sin acciones de Alfred
    if _point_is_meeting_point(context, self):
        items.append((
            "INTERACTUAR", "Interactuar",
            "Solo disponible cuando este punto coincide con una coordenada "
            "del recorrido de Jerry (punto de encuentro). Reproduce, en "
            "este punto, la animacion .py elegida en 'Animacion de "
            "interaccion' (carpeta de interaccion de Cerdo_1)",
            "COMMUNITY", 20,
        ))
    # Mantener la lista viva en memoria (ver comentario mas arriba sobre
    # _tipo_segmento_dynamic_cache) mientras bpy la tenga dibujada.
    _tipo_segmento_dynamic_cache[self.as_pointer()] = items
    return _tipo_segmento_dynamic_cache[self.as_pointer()]


def _interaccion_anim_items(self, context):
    """Lista dinamica (dropdown) de animaciones .py encontradas en
    DEFAULT_INTERACTION_DIR_CERDO_1 -- cada archivo .py de esa carpeta es
    una animacion de interaccion que Cerdo_1 puede reproducir en un punto
    de encuentro. Se recorre la carpeta cada vez que el panel se
    redibuja, asi que un archivo nuevo aparece solo (sin boton
    'refrescar').
    """
    folder = DEFAULT_INTERACTION_DIR_CERDO_1
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
        print(f"cerdo_1_animation_studio: no se pudo leer '{folder}': {e}")
    if not items:
        items.append((
            "NONE", "(sin animaciones todavia)",
            f"No hay archivos .py en {folder} -- exporta las animaciones "
            f"de interaccion de Cerdo_1 ahi",
            "ERROR", 0,
        ))
    _interaccion_anim_cache[self.as_pointer()] = items
    return _interaccion_anim_cache[self.as_pointer()]


class CERDO_1PathPoint(PropertyGroup):
    coords:     FloatVectorProperty(name="Coords",     size=3, default=(0.0, 0.0, 0.0))
    texture:    StringProperty(name="Textura",         default="")
    face_index: StringProperty(name="Face Index",      default="")

    # NUEVO (pedido de Kebyn, 2026-08-02): tipo de segmento EDITABLE
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
        # FIX (2026-09-24): con items dinamicos (funcion), Blender NO usa
        # este entero como posicion en la lista -- lo matchea contra el
        # campo "number" (5to elemento) de cada tupla en
        # _TIPO_SEGMENTO_BASE_ITEMS. AUTO tiene number=0, pero
        # GOLPE_ESTOMAGO_1 tiene number=3 -- con default=3 cada punto
        # nuevo se inicializaba en "golpe_estomago_1" en vez de "caminar"
        # (AUTO). Corregido a 0 (el number real de AUTO).
        default=0,
    )
    parada_frames_punto: IntProperty(
        name="Frames parado aqui",
        description="Cantidad de frames que el personaje permanece detenido en este punto antes de seguir el recorrido",
        default=24, min=1, soft_max=99999,
    )

    # NUEVO (Kebyn, 2026-09-13): animacion .py IMPORTADA para este punto
    # de "Parada" -- tipicamente exportada por el conversor de Mixamo
    # (mismo formato que slot_001_parado_discutiendo_dba2c3.py: modulo
    # con un diccionario module-level KEYFRAME_DATA de bone -> {frame:
    # (rx, ry, rz)}). Si esta seteado, generate_parada()
    # (generate_slots_cerdo_1.py) reproduce esa animacion completa en
    # este punto de parada en vez de la pose estatica "parado" -- ver
    # CERDO_1PR_OT_ImportParadaAnim / CERDO_1PR_OT_ClearParadaAnim mas
    # abajo, y el boton "Importar animacion (.py)" en el panel (Paso 1,
    # solo visible cuando tipo_segmento == 'PARADA').
    parada_anim_file: StringProperty(
        name="Animacion importada (.py)",
        description=(
            "Script .py de animacion importada (ej. exportado por el "
            "conversor de Mixamo) que se reproduce durante esta parada "
            "en vez de la pose estatica por defecto. Vacio = "
            "comportamiento normal de 'Parada' (root inmovil, pose base)"
        ),
        default="",
        subtype='FILE_PATH',
    )

    # NUEVO (Kebyn, 2026-09-13): orientacion (heading, rotacion Z) GUARDADA
    # a mano para este punto de "Parada". El usuario rota el empty root
    # (ROOT_NAME = "cerdo_1") en el viewport -- boton "Rotar root (cerdo_1)"
    # (invoca bpy.ops.transform.rotate constreñido al eje Z) o directamente
    # con R, Z en el viewport -- y despues aprieta "Guardar orientacion".
    # Eso lee root_empty.rotation_euler.z ACTUAL (convertido a grados,
    # mismo formato que pc.root_rot_z) y lo graba aca. Mientras
    # parada_rot_saved este activo, ese valor reemplaza al heading
    # automatico (prev_rz / prev_rz_exp) desde este punto de parada en
    # adelante -- tanto en "Reproducir recorrido" (Paso 2, ver
    # CERDO_1PR_OT_PreviewPath) como en la generacion de segmentos reales
    # (Paso 3, ver el operador de exportacion/generar slots) -- y se
    # mantiene asi para el resto del recorrido hasta el proximo tramo con
    # desplazamiento real (caminar/salto) que recalcule un heading propio,
    # o hasta que el usuario vuelva a guardar/borrar la orientacion de
    # ESTE punto. Ver CERDO_1PR_OT_RotateParadaRoot / CERDO_1PR_OT_SaveParadaRot
    # / CERDO_1PR_OT_ClearParadaRot mas abajo.
    parada_rot_saved: BoolProperty(
        name="Orientacion guardada",
        description=(
            "Si esta activo, este punto de parada fuerza el heading "
            "(rotacion Z) del root 'cerdo_1' al valor guardado, en vez de "
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

    # NUEVO (Kebyn, "crear pared NxN bloques"): archivo .blend del
    # bloque de 1m3 a importar, elegido por Kebyn desde el explorador
    # de archivos (mismo patron que parada_anim_file de arriba). Solo
    # tiene efecto cuando tipo_segmento == 'CREAR_PARED_NXN' -- ver
    # generate_crear_pared_nxn() (generate_slots_cerdo_1.py) y el boton
    # correspondiente en el panel (Paso 1).
    pared_bloque_blend_path: StringProperty(
        name="Bloque .blend (1m3)",
        description=(
            "Archivo .blend del bloque de 1m3 a importar para armar la "
            "pared en este punto (ej. bloque_piedra.blend). Se importa "
            "una copia por cada celda de la grilla Filas x Columnas; "
            "las siguientes paredes del mismo recorrido numeran sus "
            "bloques solas (bloque_1, bloque_2...)"
        ),
        default="",
        subtype='FILE_PATH',
    )
    pared_filas: IntProperty(
        name="Filas (alto)",
        description="Cantidad de bloques de alto (filas, apiladas en Z) de la pared",
        default=2, min=1, soft_max=20,
    )
    pared_columnas: IntProperty(
        name="Columnas (ancho)",
        description="Cantidad de bloques de ancho (columnas, a los costados) de la pared",
        default=2, min=1, soft_max=20,
    )
    # NUEVO (Kebyn, "elegir cuantos frames dura toda la animacion de
    # crear pared"): duracion TOTAL en frames de la animacion completa
    # (los Filas x Columnas ciclos agachar/colocar, de principio a fin).
    # 0 = automatico (usa FRAMES_PER_BLOQUE_PARED_NXN frames fijos por
    # bloque, comportamiento de siempre) -- ver
    # resolve_pared_nxn_timing() (generate_slots_cerdo_1.py), que reparte
    # este total entre los bloques y reescala el ciclo si se especifica.
    pared_total_frames: IntProperty(
        name="Frames totales (0 = auto)",
        description=(
            "Duracion TOTAL en frames de toda la animacion de crear "
            "pared (los Filas x Columnas bloques, de principio a fin). "
            "0 = automatico: cada bloque usa su duracion fija de "
            "siempre. Si se especifica un valor, la duracion de cada "
            "bloque se acelera o alarga en partes iguales para que el "
            "total encaje (con un minimo por bloque para no perder la "
            "pose de agacharse/colocar)"
        ),
        default=0, min=0, soft_max=2000,
    )

    # NUEVO (Kebyn): dropdown de que animacion de interaccion reproducir
    # en este punto CUANDO tipo_segmento == 'INTERACTUAR' (solo
    # seleccionable en un punto de encuentro real con Jerry -- ver
    # _point_is_meeting_point() e _interaccion_anim_items() mas arriba).
    # Lista los .py encontrados en DEFAULT_INTERACTION_DIR_CERDO_1
    # (constants.py); Cerdo_1 reproduce su propia mitad de la interaccion
    # desde ahi, Jerry reproduce la suya desde su propia carpeta.
    interaccion_anim_choice: EnumProperty(
        name="Animacion de interaccion",
        description=(
            "Animacion .py (carpeta de interaccion de Cerdo_1) que se "
            "reproduce en este punto de encuentro con Jerry"
        ),
        items=_interaccion_anim_items,
    )


class CERDO_1ParadaFrames(PropertyGroup):
    """Duracion (en frames) de UNA parada individual del recorrido.

    NUEVO 2026-07-09 (pedido de Kebyn: 'ahun me salen 60 frames por cada
    parada'). Antes existia un unico IntProperty global
    `CERDO_1PathSettings.frames_parada` que se aplicaba identico a TODAS
    las paradas del recorrido, sin importar cuantas poses/tiempo real
    necesitaba cada una segun el pipeline Python
    (cerdo_1_story_generator.py calcula n_poses_por_parada * 20, que
    varia parada a parada). Esta coleccion permite un valor independiente
    por cada parada detectada en el recorrido (una entrada por cada
    segmento tipo 'parada' que retorna group_segments(), en el mismo
    orden en que aparecen los puntos duplicados en el Path Recorder).

    CORREGIDO (pedido de Kebyn): este valor ya NO se edita a mano desde
    el panel. Al cargar una configuracion (CERDO_1_ST_OT_LoadConfig) se
    recalcula como la SUMA de frames de las poses de accion que
    caen dentro de ese tramo especifico,
    leyendo unicamente lo que trae el configuracion.json (ver
    _calcular_frames_por_parada en config_ops.py). El campo sigue siendo
    un IntProperty (se necesita para guardarlo/serializarlo y para que
    generate_slots_cerdo_1.py lo use al generar los slots), pero el panel
    (panels.py) solo lo muestra con box.label(), nunca con prop().
    """
    frames: IntProperty(
        name="Frames",
        description=(
            "Frames que dura esta parada especifica (root inmovil). "
            "Calculado automaticamente como la suma de frames de las "
            "poses de la configuracion cargada que caen en este tramo — "
            "no se edita a mano desde el panel."
        ),
        default=60, min=1, soft_max=99999,
    )


class CERDO_1WalkStyleEntry(PropertyGroup):
    """Estilo de caminata (Normal/Lento/Herido/Rapido/Correr) de UN tramo
    'caminar' individual del recorrido.

    NUEVO (pedido de Kebyn, 2026-08-02): antes existia un unico
    EnumProperty global `CERDO_1PathSettings.walk_style` que se aplicaba
    identico a TODOS los tramos 'caminar' detectados en el recorrido, sin
    importar cuantos hubiera ni el contexto de cada uno (ej. el primer
    tramo podia necesitar 'Caminar Normal' y el tercero, despues de una
    parada, 'Caminar Herido'). Esta coleccion permite un estilo
    independiente por cada tramo 'caminar' detectado (una entrada por
    cada segmento tipo 'caminar' que retorna _group_segments(), en el
    mismo orden en que aparecen en el recorrido) — mismo patron que
    CERDO_1ParadaFrames para las paradas.
    """
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

    # NUEVO (pedido de Kebyn, 2026-08-04): "foto" del estilo que ya quedo
    # horneado en la duracion del segmento real del Paso 3 (via el boton
    # "Actualizar", ver CERDO_1SEG_OT_UpdateFromEstimacion). Comparando
    # `style` (lo que el usuario tiene elegido AHORA en el dropdown)
    # contra `applied_style` (lo que se aplico la ULTIMA vez) el operador
    # puede distinguir "el usuario cambio el estilo de este tramo, hay que
    # recalcular los frames" de "este tramo no cambio, no tocar su
    # duracion real" -- sin este campo no habia forma de saber por que
    # motivo se presiono Actualizar (frames por parada, o estilo de
    # caminata), y por eso los tramos 'caminar' nunca se recalculaban
    # (ver comentario largo en CERDO_1SEG_OT_UpdateFromEstimacion).
    # String vacio ("") = todavia sin "foto" (archivo viejo o tramo recien
    # creado): la primera vez que se presiona Actualizar solo se establece
    # la foto, sin recalcular nada (evita corromper duraciones reales que
    # ya traia un config cargado).
    applied_style: StringProperty(
        name="Estilo aplicado (interno)",
        description=(
            "Ultimo estilo de caminata horneado en la duracion real de "
            "este tramo. Uso interno -- no editar a mano."
        ),
        default="",
    )


class CERDO_1PathSettings(PropertyGroup):
    """Configuracion y estado del Path Recorder integrado."""

    recording_active: BoolProperty(
        name="Grabacion activa",
        description="Detecta automaticamente las faces seleccionadas",
        default=False,
    )
    # NUEVO (Kebyn, 2026-08-02): antes, la linea/puntos numerados del
    # recorrido SOLO se dibujaban en el viewport mientras recording_active
    # era True -- al presionar "Detener grabacion" el draw handler se
    # eliminaba por completo y el recorrido trazado se volvia invisible,
    # sin forma de revisarlo salvo volviendo a grabar. Este flag controla
    # una visualizacion PERSISTENTE e independiente de la grabacion (ver
    # boton "Visualizar recorrido" / CERDO_1PR_OT_TogglePathViz).
    show_path_viz: BoolProperty(
        name="Visualizar recorrido",
        description=(
            "Muestra la linea y los puntos numerados del recorrido "
            "trazado en el viewport, incluso sin estar grabando"
        ),
        default=False,
    )
    path_points: CollectionProperty(type=CERDO_1PathPoint)

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
        description="Frame final de la animacion (solo modo 1 coordenada)",
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
            "libre para superponer una action_pose). NO tiene techo — "
            "debe coincidir con self.frames_parada calculado en "
            "cerdo_1_story_generator.py (n_poses_por_parada * 20) del "
            "lado del pipeline Python, o el timing entre el config.json "
            "generado alli y lo que se reproduce aqui en Blender queda "
            "desincronizado. Ver generate_parada() en "
            "generate_slots_cerdo_1.py."
        ),
        default=60, min=1, soft_max=99999,
    )
    # NUEVO (Kebyn, transiciones entre tramos): suaviza el corte de pose
    # justo en el borde entre dos tramos consecutivos de TIPO DISTINTO
    # (ej. Caminar -> Parada, Parada -> Caminar, Caminar -> subir/bajar).
    # Cuando dos tramos consecutivos son del MISMO tipo (ej. dos
    # "Caminar" seguidos) el ciclo de marcha ya continua sin corte
    # visible, asi que ahi NUNCA se aplica -- ver
    # _suavizar_borde_segmentos() / el uso de "tipo_anterior != move_type"
    # en CERDO_1PR_OT_PreviewPath.execute().
    usar_transiciones: BoolProperty(
        name="Suavizar transiciones entre tramos distintos",
        description=(
            "Interpola la pose alrededor del corte entre dos tramos "
            "consecutivos cuando son de tipo distinto (Caminar/Parada/"
            "subir/bajar/etc.), en vez del cambio brusco de un frame al "
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
        type=CERDO_1ParadaFrames,
    )
    root_rot_x: FloatProperty(name="Rot X", default=0.0, precision=1)
    root_rot_y: FloatProperty(name="Rot Y", default=0.0, precision=1)
    root_rot_z: FloatProperty(name="Rot Z", default=-90.0, precision=1)

    # NUEVO (pedido de Kebyn, 2026-08-01): selector de "estilo de
    # caminata" — funciona como un multiplexor: la animacion base de
    # caminar tiene varias variantes segun el contexto de la historia
    # (normal / lenta / herido / rapida / correr).
    # ACTUALIZADO (pedido de Kebyn, 2026-08-02): cada tramo 'caminar'
    # detectado ahora elige su propio estilo de forma independiente (ver
    # walk_styles mas abajo, y sync_walk_styles()). Este EnumProperty ya
    # NO se aplica de forma global a todos los tramos -- se conserva solo
    # como valor por defecto para las entradas NUEVAS de walk_styles
    # cuando aparece un tramo 'caminar' recien detectado.
    walk_style: EnumProperty(
        name="Estilo de caminata (default)",
        description=(
            "Estilo por defecto para tramos 'caminar' nuevos que todavia "
            "no tienen su propia entrada en walk_styles"
        ),
        items=[
            ("NORMAL", "Caminar Normal", "Caminata estandar (por defecto)", "FORWARD", 0),
            ("LENTO", "Caminar Lento", "Caminata lenta / cautelosa", "TRIA_LEFT", 1),
            ("HERIDO", "Caminar Herido", "Caminata herida / cojeando", "ERROR", 2),
            ("RAPIDO", "Caminar Rapido", "Caminata rapida", "TRIA_RIGHT", 3),
            ("CORRER", "Correr", "Carrera / trote", "TRACKING_FORWARDS", 4),
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
        type=CERDO_1WalkStyleEntry,
    )

    output_dir: StringProperty(
        name="Carpeta salida",
        description="Carpeta donde se guardan los scripts slot_NNN_*.py generados",
        default=r"C:\Users\user\Desktop\Alfred_Animacion\animacion",
        subtype="DIR_PATH",
    )

    execute_inscene: BoolProperty(
        name="Ejecutar en escena",
        description="Ademas de guardar los archivos, ejecuta cada slot directamente en Blender",
        default=False,
    )

    status_msg:        StringProperty(default="")
    last_generated:    IntProperty(default=0)
    anim_frame_fin:    IntProperty(default=0)
    anim_total_frames: IntProperty(default=0)
    show_coords_list:  BoolProperty(name="Mostrar lista de coordenadas", default=True)

    blend_filepath: StringProperty(
        name="Archivo .blend del personaje",
        description="Ruta al archivo .blend que contiene el rig del personaje",
        default="",
        subtype="FILE_PATH",
    )


def sync_paradas_frames(pc):
    """Sincroniza pc.paradas_frames con la cantidad real de paradas del
    recorrido actual (pc.path_points), preservando los valores que ya
    hayan sido editados a mano.

    NUEVO 2026-07-09: antes de este fix no existia ninguna coleccion
    por-parada — solo el escalar global `pc.frames_parada`, por eso el
    panel siempre mostraba/usaba 60 frames para TODAS las paradas sin
    importar cuantas hubiera.

    IMPORTANTE — CORREGIDO 2026-07-09 v2: esta funcion escribe en datos
    de la escena (agrega/quita items de una CollectionProperty) y por
    lo tanto NUNCA debe llamarse desde un metodo draw() de panel; Blender
    prohibe escribir en ID-data durante el dibujado
    ("Writing to ID classes in this context is not allowed"). Debe
    invocarse solo desde operadores (execute()) o desde el handler de
    depsgraph_update_post, nunca desde UI_PT_Panel.draw().

    Se llama automaticamente desde: CERDO_1PR_OT_RemoveLast,
    CERDO_1PR_OT_ClearPath, el handler _cerdo_1_face_selection_handler
    (al agregar un punto nuevo), CERDO_1PR_OT_PreviewPath,
    CERDO_1PR_OT_ExportSlots, y CERDO_1_ST_OT_LoadConfig (al restaurar el
    recorrido desde un JSON). El panel solo LEE pc.paradas_frames y
    ofrece un boton manual (cerdo_1pr.sync_paradas_frames) para forzar
    la sincronizacion en cualquier caso borde.

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
    hayan sido elegidos a mano. Mismo patron que sync_paradas_frames()
    pero contando tramos 'caminar' en vez de 'parada'.

    IMPORTANTE: al igual que sync_paradas_frames(), escribe en datos de
    la escena (agrega/quita items de una CollectionProperty) y por lo
    tanto NUNCA debe llamarse desde un metodo draw() de panel -- solo
    desde operadores (execute()) o el handler de depsgraph_update_post.

    Se llama automaticamente desde los mismos puntos que
    sync_paradas_frames(): CERDO_1PR_OT_RemoveLast, CERDO_1PR_OT_ClearPath,
    el handler de seleccion de faces (al agregar un punto nuevo),
    CERDO_1PR_OT_PreviewPath, CERDO_1PR_OT_ExportSlots, y
    CERDO_1_ST_OT_LoadConfig (al restaurar el recorrido desde un JSON).

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
            # Tramo recien detectado: todavia no hay ningun segmento real
            # del Paso 3 cuya duracion dependa de este estilo, asi que se
            # marca de una la "foto" (ver applied_style arriba) para que
            # el primer "Actualizar" despues de dividir no dispare un
            # recalculo espurio.
            item.applied_style = item.style
    elif n_actual > n_caminar:
        for _ in range(n_actual - n_caminar):
            pc.walk_styles.remove(len(pc.walk_styles) - 1)

    return n_caminar


def sync_paradas_frames_from_segments(context):
    """Corrige el VALOR (no solo la cantidad) de cada entrada de
    pc.paradas_frames para que coincida con la duracion real que el
    segmento "parada" correspondiente tiene configurada en el Paso 3
    (cerdo_1_segs) -- la suma de las duraciones de sus action_poses.

    BUG (Kebyn, 2026-07-11): sync_paradas_frames() solo ajusta la
    CANTIDAD de entradas de pc.paradas_frames a la cantidad de paradas
    detectadas en el recorrido, pero nunca actualiza el VALOR de una
    entrada ya existente. Si el usuario recorta/ajusta las poses de un
    segmento "parada" en el Paso 3 (ej. de 247f originales a 110f reales
    tras asignar 4 poses), pc.paradas_frames sigue con el valor viejo
    (247), asi que la Capa 1 (generate_parada, via "Reproducir
    recorrido") sigue generando un bloque inmovil de 247 frames en vez
    de 110. El sobrante (137 frames) sigue siendo fisicamente parte de
    ESE mismo bloque/track de la Capa 1, asi que al reinyectar (Capa 2)
    las poses de los SIGUIENTES segmentos del Paso 3 (que en frames
    absolutos caen dentro de ese sobrante), terminan escribiendose en el
    mismo track -- se ve como si la animacion del segmento parada "se
    extendiera" mucho mas alla de su frame_end real.

    Empareja cada entrada de pc.paradas_frames (en el orden en que las
    detecta group_segments() sobre el recorrido actual) con el N-esimo
    segmento de cerdo_1_segs cuyo label contenga "parada" (insensible a
    mayusculas), ordenados por frame_start -- mismo orden en que se
    crean. Si ese segmento tiene action_poses con duracion > 0, se
    sobreescribe pc.paradas_frames[i].frames con esa suma. Si no hay
    segmentos "parada" en cerdo_1_segs (o no tienen poses aun), no se
    toca nada -- se conserva el valor existente (editado a mano o
    default).
    """
    pc = context.scene.cerdo_1_path
    segs_data = getattr(context.scene, "cerdo_1_segs", None)
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


# =============================================================================
# HANDLER — deteccion automatica de face seleccionada
# =============================================================================

@persistent
def _cerdo_1_face_selection_handler(scene):
    """Se ejecuta en depsgraph_update_post. Registra faces seleccionadas."""
    global _last_face_idx

    path_cfg = getattr(scene, "cerdo_1_path", None)
    if path_cfg is None or not path_cfg.recording_active:
        return

    obj = bpy.context.active_object
    if obj is None or obj.type != "MESH" or obj.mode != "EDIT":
        return

    bm = bmesh.from_edit_mesh(obj.data)
    selected = [f for f in bm.faces if f.select]
    if len(selected) != 1:
        # FIX (Kebyn, 2026-08-23): no hay exactamente 1 cara seleccionada
        # (se deselecciono, se marco mas de una, o ninguna) -- se resetea
        # la memoria de "ultima cara vista seleccionada". Antes esta rama
        # retornaba sin tocar _last_face_idx (que ademas nunca se leia en
        # ningun lado), asi que no habia forma de distinguir "la cara
        # sigue seleccionada de antes" de "se deselecciono y se volvio a
        # seleccionar" -- ver el chequeo de mas abajo.
        _last_face_idx = None
        return

    face = selected[0]
    face_id = str(face.index)

    # FIX (Kebyn, 2026-08-23): se compara contra _last_face_idx (ultima
    # cara REALMENTE VISTA seleccionada por este handler, se resetea a
    # None en cuanto deja de haber exactamente 1 cara seleccionada, ver
    # arriba) en vez de contra path_cfg.path_points[-1].face_index
    # (ultimo punto ya AGREGADO a la lista). Con la version anterior, si
    # el usuario deseleccionaba la cara (Alt+A / clic en vacio) y volvia
    # a seleccionar ESA MISMA cara sin haber agregado ningun otro punto
    # distinto en el medio, quedaba bloqueado PARA SIEMPRE -- el ultimo
    # punto de la lista seguia siendo esa misma cara, aunque en el
    # viewport hubo una deseleccion + reseleccion real (dos eventos
    # distintos, no ruido de depsgraph). Esto impedia marcar la misma
    # coordenada dos veces seguidas en la lista (por ejemplo, para cerrar
    # un recorrido en el mismo punto de inicio, o para repetir a mano una
    # coordenada). Ahora solo se descarta el registro cuando la cara
    # sigue siendo la MISMA seleccion ininterrumpida de antes (sin
    # deseleccion de por medio, que es el unico caso real de "ruido" de
    # depsgraph_update_post disparandose varias veces para un mismo
    # clic) -- revisitar una coordenada ya usada (ida y vuelta, guardias,
    # patrullas, o repetirla adrede) funciona en todos los casos.
    if _last_face_idx == face_id:
        return

    _last_face_idx = face_id
    center_local  = face.calc_center_median()
    center_global = obj.matrix_world @ center_local

    mat_name = "No Material"
    if obj.data.materials and face.material_index < len(obj.data.materials):
        mat = obj.data.materials[face.material_index]
        if mat:
            mat_name = mat.name

    pt            = path_cfg.path_points.add()
    pt.coords     = center_global
    pt.texture    = mat_name
    pt.face_index = face_id

    # FIX (Kebyn, 2026-08-23 v3): se agenda la deseleccion via
    # bpy.app.timers en vez de tocar el bmesh directo aca (ver
    # _deferred_deselect_face() mas arriba para el motivo -- escribir
    # sobre la malla dentro de este mismo handler de depsgraph no se
    # aplicaba de forma confiable). El proximo clic sobre esta misma
    # cara, incluso el clic inmediato siguiente, pasara entonces de
    # no-seleccionada a seleccionada -- un cambio de estado real que si
    # dispara un depsgraph_update_post nuevo -- permitiendo repetir la
    # coordenada las veces que se quiera, incluso dos veces seguidas.
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
    """Registra el draw handler del recorrido si todavia no esta activo.
    Usado tanto al iniciar grabacion como al activar la visualizacion
    persistente (CERDO_1PR_OT_TogglePathViz) -- ambos comparten el mismo
    handler global _draw_handle."""
    global _draw_handle
    if _draw_handle is None:
        _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_path_3d, (), "WINDOW", "POST_VIEW"
        )


def _maybe_remove_draw_handler(pc):
    """Elimina el draw handler SOLO si ni la grabacion ni la visualizacion
    persistente lo necesitan. Si cualquiera de las dos sigue activa, el
    handler se deja intacto (evita que detener grabacion oculte una
    visualizacion que el usuario dejo encendida a proposito, y viceversa)."""
    global _draw_handle
    if getattr(pc, "recording_active", False) or getattr(pc, "show_path_viz", False):
        return
    if _draw_handle is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
        except Exception:
            pass
        _draw_handle = None


def _draw_path_3d():
    scene = bpy.context.scene
    path_cfg = getattr(scene, "cerdo_1_path", None)
    if path_cfg is None or len(path_cfg.path_points) < 1:
        return

    points    = []
    col_pts   = []
    lines     = []
    col_lines = []

    for i, pt in enumerate(path_cfg.path_points):
        coord = Vector(pt.coords)
        points.append(coord)
        col_pts.append((0.3, 0.7, 1.0, 1.0))   # azul Cerdo_1
        if i > 0:
            prev = Vector(path_cfg.path_points[i - 1].coords)
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

    # NUEVO (Kebyn, 2026-08-02): numero de secuencia sobre cada punto,
    # pedido para poder identificar visualmente el orden del recorrido
    # sin tener que mirar la lista "Coordenadas seleccionadas" del panel.
    # blf.draw() trabaja en espacio de pantalla (2D), asi que cada
    # coordenada 3D se proyecta con location_3d_to_region_2d() -- si el
    # punto esta detras de la camara del viewport (o el area no tiene
    # region_data valida, ej. durante un render) esa funcion devuelve None
    # y el numero simplemente se omite para ese punto.
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
# DETECCION DE SEGMENTOS
# =============================================================================

def _smoothstep01(t):
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return t * t * (3.0 - 2.0 * t)


def _get_slot_nla_action(obj, slot_index, suffix):
    """Devuelve la Action "propia" que generate_*()/execute_animation()
    empujo a su pista NLA dedicada para este slot (ver bloque "EMPUJAR
    ACCIONES AL NLA" en generate_slots_cerdo_1.py -- cada segmento crea su
    PROPIA action y la pushea a una pista nueva 'Slot_NNN_arm'/'_root',
    dejando obj.animation_data.action en None). Por eso no alcanza con
    mirar obj.animation_data.action para leer la pose de un segmento ya
    procesado -- hay que ir a buscar la action a su pista NLA por nombre.
    `suffix` es "arm" o "root". Devuelve None si no se encuentra."""
    if obj is None or not getattr(obj, "animation_data", None):
        return None
    track = obj.animation_data.nla_tracks.get(f"Slot_{slot_index:03d}_{suffix}")
    if not track or not track.strips:
        return None
    return track.strips[0].action


def _suavizar_par_de_acciones(action_a, action_b, frame_a, frame_b, n_frames):
    """Suaviza el corte entre `action_a` (tramo anterior, termina en
    frame_a) y `action_b` (tramo siguiente, empieza en frame_b): para
    cada canal (data_path + indice) presente en AMBAS acciones, evalua
    el valor justo antes del corte y justo despues: si difieren,
    sobrescribe los ultimos `n_frames` de action_a y los primeros
    `n_frames` de action_b con una interpolacion smoothstep hacia el
    valor del otro lado, para que el corte entre las dos pistas NLA
    (que no se solapan y no tienen blend_in/out) ya casi no se note."""
    if not action_a or not action_b or n_frames <= 0:
        return
    fcs_a = {(fc.data_path, fc.array_index): fc for fc in get_fcurves(action_a, create=False)}
    fcs_b = {(fc.data_path, fc.array_index): fc for fc in get_fcurves(action_b, create=False)}

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


def _suavizar_borde_segmentos(arm_obj, root_empty, prev_slot_index, curr_slot_index,
                               frame_fin_anterior, frame_inicio_actual, n_frames):
    """Suaviza el corte entre el tramo del slot `prev_slot_index` y el
    tramo del slot `curr_slot_index`, para el armature y el root
    ("cerdo_1"). Solo debe llamarse cuando el TIPO de tramo cambio de uno
    al siguiente (ej. Caminar -> Parada) -- ver el llamado en
    CERDO_1PR_OT_PreviewPath.execute(). Entre dos tramos del mismo tipo
    (ej. dos "Caminar" seguidos) el movimiento ya es continuo y esto no
    se llama."""
    if n_frames <= 0 or frame_inicio_actual <= frame_fin_anterior:
        return
    arm_a  = _get_slot_nla_action(arm_obj, prev_slot_index, "arm")
    arm_b  = _get_slot_nla_action(arm_obj, curr_slot_index, "arm")
    root_a = _get_slot_nla_action(root_empty, prev_slot_index, "root")
    root_b = _get_slot_nla_action(root_empty, curr_slot_index, "root")
    jumps=[a for a in (arm_a,arm_b,root_a,root_b) if a and a.get('adaptive_jump')]
    if jumps:
        n=min([n_frames]+[a.get('jump_ground_blend',1) for a in jumps])
        _suavizar_par_de_acciones(arm_a,arm_b,frame_fin_anterior,frame_inicio_actual,n)
        return
    _suavizar_par_de_acciones(arm_a,  arm_b,  frame_fin_anterior, frame_inicio_actual, n_frames)
    _suavizar_par_de_acciones(root_a, root_b, frame_fin_anterior, frame_inicio_actual, n_frames)


def _detect_move(p0, p1):
    if getattr(p0,'tipo_segmento','AUTO') == 'SALTAR':
        z0,z1=round(p0.coords[2],2),round(p1.coords[2],2)
        return 'saltar_subir' if z1>z0 else 'saltar_bajar' if z1<z0 else 'saltar_horizontal'
    if is_woodcut(getattr(p0, "tipo_segmento", "AUTO")):
        return p0.tipo_segmento.lower()
    """NUEVO 2026-07-08 (paradas): si el punto es identico al anterior
    (misma x/y/z), se clasifica como "parada" — root inmovil, canvas
    libre para que CONCATENAR superponga la action_pose de este tramo.
    Replica el mismo criterio que `_detectar_movimiento_recorrido()` en
    el pipeline (cerdo_1_story_generator.py) y `detect_movement_type()`
    en generate_slots_cerdo_1.py — los 3 deben coincidir.

    FIX (Kebyn, 2026-08-19): "en las diagonales la lista de recorrido lo
    muestra como bajar, cuando lo unico que hace es ir en diagonal -- el
    personaje camina con normalidad, el error esta en como la interfaz lo
    detecta". Causa: pt.coords viene del raycast de seleccion de faces
    (world-space, ver CERDO_1_ST_OT_... mas arriba: `pt.coords = center_global`)
    y arrastra ruido de punto flotante de orden 1e-6/1e-5 (multiplicacion
    de matrices) -- en una diagonal (misma altura de bloque) ese ruido
    hacia que z1 sea, por ejemplo, 9.000001 en vez de exactamente
    9.000000, y la comparacion exacta `z1 > z0` / `z1 < z0` de mas abajo
    lo clasificaba como salto.

    FIX (Kebyn, 2026-08-23): 4 decimales resulto ser insuficiente -- se
    reporto el mismo sintoma ("repito la misma coordenada y la marca
    como bajar") entre dos faces cuya coordenada real difiere en menos
    de un centimetro (por debajo de 0.01, pero por encima de 0.0001),
    ruido geometrico real de la malla del escenario (no solo de punto
    flotante en la multiplicacion de matrices) que el redondeo a 4
    decimales no absorbia. Se baja la precision de comparacion a 2
    decimales -- la MISMA precision que ya se le muestra al usuario en
    el panel ("Coordenadas seleccionadas", ver panels.py:
    `round(pt.coords[...], 2)`), asi que lo que se ve en la lista
    siempre coincide con como se clasifica el tramo: si dos puntos se
    ven igual en la lista, SON iguales para la deteccion. Un salto real
    (altura de un bloque, tipicamente >= 0.1 en este escenario) sigue
    detectandose sin problema -- 2 decimales (0.01) sigue siendo un
    orden de magnitud mas chico que cualquier diferencia de altura real.
    FIX (Kebyn, 2026-08-23) v2: incluso con la comparacion a 2 decimales
    de arriba, marcar SIEMPRE una coordenada repetida como "parada" le
    quitaba al usuario la posibilidad de elegir el segmento (via el
    dropdown del panel, que solo se muestra editable cuando el tramo da
    "caminar" -- ver _detect_move_geom() mas abajo y panels.py). A
    pedido de Kebyn: una coordenada repetida en AUTO (sin marcar
    manualmente como PARADA) ahora resuelve como "caminar" -- el
    personaje camina hacia el mismo punto (distancia ~0, ver
    generate_caminar() en generate_slots_cerdo_1.py, que ya clampea
    dist_total a un minimo de 0.0001 para este caso: el resultado es
    caminar "en el lugar", sin desplazarse, en vez de tragarse el punto
    como si fuera un tramo distinto). "Parada" real sigue existiendo,
    pero ahora es EXCLUSIVAMENTE el resultado de marcar manualmente el
    punto como PARADA en el dropdown -- ya no es una consecuencia
    automatica de que dos coordenadas coincidan. Debe coincidir con el
    mismo cambio en detect_movement_type() (generate_slots_cerdo_1.py) y
    en _resolver_tipo_segmento_auto() (config_ops.py).
    """
    # NUEVO (Kebyn, 2026-08-21): override manual "colocar_antorcha" --
    # mismo patron que la salvaguarda de PARADA en
    # _expand_points_with_paradas(), pero sin duplicar punto: el tramo
    # p0->p1 se marca colocar_antorcha directamente, con prioridad sobre
    # la deteccion geometrica (funciona sea el tramo real caminar o
    # salto). Debe coincidir con el mismo override en
    # detect_movement_type() (generate_slots_cerdo_1.py).
    if getattr(p0, "tipo_segmento", "AUTO") == "COLOCAR_ANTORCHA":
        return "colocar_antorcha"
    # NUEVO (Kebyn): override manual "golpe_estomago_1" -- misma
    # arquitectura que "colocar_antorcha" (ver comentario de arriba),
    # sin duplicar punto. Debe coincidir con el mismo override en
    # detect_movement_type() (generate_slots_cerdo_1.py).
    if getattr(p0, "tipo_segmento", "AUTO") == "GOLPE_ESTOMAGO_1":
        return "golpe_estomago_1"
    # NUEVO (Kebyn, 2026-08-22): override manual "colocar_mesa_de_crafteo"
    # -- mismo patron que "colocar_antorcha"/"golpe_estomago_1" de arriba,
    # sin duplicar punto. Debe coincidir con el mismo override en
    # detect_movement_type() (generate_slots_cerdo_1.py).
    if getattr(p0, "tipo_segmento", "AUTO") == "COLOCAR_MESA_CRAFTEO":
        return "colocar_mesa_de_crafteo"
    # NUEVO (Kebyn, "crear pared NxN bloques"): override manual
    # "crear_pared_nxn" -- mismo patron que "colocar_mesa_de_crafteo"
    # de arriba, sin duplicar punto. Debe coincidir con el mismo
    # override en detect_movement_type() (generate_slots_cerdo_1.py).
    if getattr(p0, "tipo_segmento", "AUTO") == "CREAR_PARED_NXN":
        return "crear_pared_nxn"
    # NUEVO (Kebyn): override manual "levantarse_1" -- misma arquitectura
    # que "golpe_estomago_1" (ver arriba), sin duplicar punto. Debe
    # coincidir con el mismo override en detect_movement_type()
    # (generate_slots_cerdo_1.py).
    if getattr(p0, "tipo_segmento", "AUTO") == "LEVANTARSE_1":
        return "levantarse_1"
    # NUEVO (Kebyn): override manual "levantarse_2" -- misma arquitectura
    # que "levantarse_1" (ver arriba), sin duplicar punto. Debe coincidir
    # con el mismo override en detect_movement_type()
    # (generate_slots_cerdo_1.py).
    if getattr(p0, "tipo_segmento", "AUTO") == "LEVANTARSE_2":
        return "levantarse_2"
    # NUEVO (Kebyn): override manual "arrodillarse_1" -- misma
    # arquitectura que "levantarse_1"/"levantarse_2" (ver arriba), sin
    # duplicar punto. Debe coincidir con el mismo override en
    # detect_movement_type() (generate_slots_cerdo_1.py).
    if getattr(p0, "tipo_segmento", "AUTO") == "ARRODILLARSE_1":
        return "arrodillarse_1"
    # NUEVO (Kebyn): override manual "conversar_1" -- misma arquitectura
    # que "arrodillarse_1"/"levantarse_1"/"levantarse_2" (ver arriba),
    # sin duplicar punto. Debe coincidir con el mismo override en
    # detect_movement_type() (generate_slots_cerdo_1.py).
    if getattr(p0, "tipo_segmento", "AUTO") == "CONVERSAR_1":
        return "conversar_1"
    # NUEVO (Kebyn): override manual "resbalarse_1" -- misma arquitectura
    # que "arrodillarse_1"/"levantarse_1"/"levantarse_2" (ver arriba),
    # sin duplicar punto. Debe coincidir con el mismo override en
    # detect_movement_type() (generate_slots_cerdo_1.py).
    if getattr(p0, "tipo_segmento", "AUTO") == "RESBALARSE_1":
        return "resbalarse_1"

    x0, y0, z0 = p0.coords[0], p0.coords[1], p0.coords[2]
    x1, y1, z1 = p1.coords[0], p1.coords[1], p1.coords[2]
    x0, y0, z0 = round(x0, 2), round(y0, 2), round(z0, 2)
    x1, y1, z1 = round(x1, 2), round(y1, 2), round(z1, 2)
    if x0 == x1 and y0 == y1 and z0 == z1:
        # FIX (Kebyn, 2026-08-23 v2): "parada" solo si el punto esta
        # EXPLICITAMENTE marcado como PARADA (dropdown) -- ver docstring
        # de arriba. En AUTO, una coordenada repetida es "caminar" (en
        # el lugar, sin desplazarse), dejando el dropdown editable para
        # que el usuario elija a mano que hacer con esa repeticion.
        if getattr(p0, "tipo_segmento", "AUTO") == "PARADA":
            return "parada"
        return "caminar"
    if   z1 > z0: return "saltar_subir"
    elif z1 < z0: return "saltar_bajar"
    else:          return "caminar"


def _detect_move_geom(p0, p1):
    """NUEVO (Kebyn, 2026-08-21 v2): version de _detect_move() que NO aplica
    el override manual de tipo_segmento (COLOCAR_ANTORCHA) -- clasifica el
    tramo UNICAMENTE por geometria real (redondeada a 2 decimales, mismo
    criterio que _detect_move() -- ver FIX 2026-08-23 en su docstring).

    Se usa solo para decidir, en la lista "Coordenadas seleccionadas" del
    panel, si el dropdown Caminar/Parada/Colocar antorcha debe mostrarse
    editable en un punto -- independientemente de si ese punto YA tiene un
    override aplicado. Sin esto, _detect_move() (que SI mira tipo_segmento)
    devolvia 'colocar_antorcha' apenas el usuario elegia esa opcion, y el
    panel ocultaba el dropdown reemplazandolo por una etiqueta fija -- el
    usuario quedaba sin forma de volver a cambiarlo.

    FIX (Kebyn, 2026-08-23 v2): coordenadas identicas ahora SIEMPRE
    resuelven aca como "caminar" (nunca "parada"), sin importar
    tipo_segmento -- a diferencia de _detect_move() de arriba, esta
    funcion decide UNICAMENTE si el dropdown se muestra editable, y
    "caminar" es el unico valor que lo deja editable (ver panels.py:
    `if geom_move == "caminar": row_pt.prop(pt, "tipo_segmento", ...)`).
    Si devolviera "parada" para coordenadas repetidas, el usuario
    quedaria sin forma de elegir a mano que hacer con esa repeticion
    (Caminar en el lugar / Parada / Colocar antorcha / etc) -- justamente
    lo que pedia poder hacer."""
    x0, y0, z0 = p0.coords[0], p0.coords[1], p0.coords[2]
    x1, y1, z1 = p1.coords[0], p1.coords[1], p1.coords[2]
    x0, y0, z0 = round(x0, 2), round(y0, 2), round(z0, 2)
    x1, y1, z1 = round(x1, 2), round(y1, 2), round(z1, 2)
    if x0 == x1 and y0 == y1 and z0 == z1:
        return "caminar"
    if   z1 > z0: return "saltar_subir"
    elif z1 < z0: return "saltar_bajar"
    else:          return "caminar"


def _group_segments(path_points):
    return group_woodcut_points(path_points, _group_segments_legacy)

def _group_segments_legacy(path_points):
    """Agrupa los puntos en segmentos: caminar (multi-punto), saltar_subir/bajar
    (2 puntos), parada (2 puntos identicos — NUEVO 2026-07-08)."""
    pts = list(path_points)
    segments = []
    i = 0
    _ACCION_OVERRIDES = ("COLOCAR_ANTORCHA", "GOLPE_ESTOMAGO_1", "COLOCAR_MESA_CRAFTEO", "CREAR_PARED_NXN", "LEVANTARSE_1", "LEVANTARSE_2", "ARRODILLARSE_1", "CONVERSAR_1", "RESBALARSE_1")
    while i < len(pts) - 1:
        # FIX (Kebyn, 2026-08-23 tris, "se crea un caminar fantasma entre
        # Parada y Levantarse/etc"): pts[i] es el punto DUPLICADO que
        # _expand_points_with_paradas() inserta justo despues de una
        # "parada" (marcado con es_parada_dup=True, sin tipo_segmento
        # propio). Si el punto SIGUIENTE ya esta marcado manualmente con
        # uno de los overrides de accion puntual, ese punto va a
        # arrancar su propio segmento de accion en la proxima vuelta del
        # while de todos modos (el override se mira sobre el p0 de CADA
        # tramo). El tramo [duplicado_parada -> punto_marcado] no
        # necesita su propio segmento "caminar": el personaje esta fijo
        # en el lugar de la parada mientras arranca la accion siguiente
        # -- generar un "caminar" aca era exactamente el segmento
        # fantasma reportado. Se salta este punto sin emitir ningun
        # segmento. Debe coincidir con el mismo fix en group_segments()
        # (generate_slots_cerdo_1.py).
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
        elif move in ("colocar_antorcha", "golpe_estomago_1", "colocar_mesa_de_crafteo", "crear_pared_nxn", "levantarse_1", "levantarse_2", "arrodillarse_1", "conversar_1", "resbalarse_1"):
            # NUEVO (Kebyn): "golpe_estomago_1" y "colocar_mesa_de_crafteo"
            # comparten exactamente la misma arquitectura de
            # fusion-con-el-caminar-siguiente que "colocar_antorcha" (root
            # fijo en pts[i], ver generate_golpe_estomago_1()/
            # generate_colocar_mesa_crafteo() en generate_slots_cerdo_1.py).
            # "arrodillarse_1" idem (ver generate_arrodillarse_1()).
            # "conversar_1" idem (ver generate_conversar_1()). "resbalarse_1"
            # idem (ver generate_resbalarse_1()).
            segments.append({"type": move, "points": [pts[i], pts[i + 1]]})
            # FIX (Kebyn, teletransportacion post-antorcha): el root queda fijo
            # en pts[i] durante colocar_antorcha, asi que se necesita un tramo
            # "caminar" de alcance hasta pts[i+1] antes de que el recorrido
            # continue.
            #
            # FIX (Kebyn, 2026-08-21 quater, "piernas no abren bien en el 2do
            # ciclo"): antes ese tramo de alcance se agregaba como un segmento
            # "caminar" SEPARADO de 2 puntos, y el caminar real que le seguia
            # se agrupaba aparte en la siguiente vuelta del while -- DOS
            # segmentos "caminar" independientes. Cada segmento "caminar"
            # hornea su propio walk_cycle arrancando en fase 0 (aislado en su
            # propia pista NLA, ver AISLAMIENTO TOTAL DE SEGMENTOS en
            # operators_segments.py), y fase 0 no es una pose neutral -- es
            # mitad de zancada con una rodilla flexionada. Terminar un
            # segmento a mitad de zancada y arrancar el siguiente de golpe en
            # fase 0 producia el pop de piernas reportado. Fusionamos aca el
            # tramo de alcance con TODO el caminar real que le sigue en UN
            # SOLO segmento "caminar" continuo (mismo mecanismo de
            # agrupacion que la rama de arriba, arrancando en pts[i]) -- asi
            # walk_cycle es continuo de punta a punta, sin reinicio de fase
            # en el medio. Debe coincidir con el mismo cambio en
            # group_segments() (generate_slots_cerdo_1.py).
            #
            # FIX (Kebyn, "deberian haber solo 3 segmentos en vez de 4"):
            # si pts[i] y pts[i+1] son la MISMA coordenada (redondeada a 2
            # decimales -- misma tolerancia que _detect_move()), no hay
            # distancia real que recorrer -- se omite el tramo de alcance
            # "caminar" por completo (antes generaba un segmento caminar
            # en el lugar, distancia 0, ver dist_total clampeado a 0.0001
            # en generate_caminar()) y se avanza directo a pts[i+1] para
            # que el siguiente segmento (tipicamente una Parada) arranque
            # inmediatamente. Debe coincidir con el mismo cambio en
            # group_segments() (generate_slots_cerdo_1.py).
            _c0, _c1 = pts[i].coords, pts[i + 1].coords
            _same_coord = (round(_c0[0], 2) == round(_c1[0], 2)
                           and round(_c0[1], 2) == round(_c1[1], 2)
                           and round(_c0[2], 2) == round(_c1[2], 2))
            # FIX (Kebyn, 2026-08-23 cuater, "se crea un caminar fantasma
            # entre Levantarse/etc y la Parada que sigue"): mismo problema
            # que el fix de arriba pero al reves -- si pts[i+1] (el punto
            # de destino de la accion) esta marcado manualmente como
            # PARADA, el personaje se va a quedar quieto ahi de todos
            # modos apenas empiece esa parada; el tramo de "alcance"
            # caminando hasta ahi no aporta nada y es exactamente el
            # segmento fantasma reportado. Se trata igual que el caso de
            # coordenadas identicas de arriba. Debe coincidir con el
            # mismo cambio en group_segments() (generate_slots_cerdo_1.py).
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
                # FIX (Kebyn, bug "antorchas/paradas en secuencia se tragan",
                # 2026-08-21): antes era `i = j + 1`, que saltaba pts[j] por
                # completo -- ese es el punto donde termina este caminar
                # fusionado Y el punto donde debe empezar el siguiente segmento
                # especial (otra 'colocar_antorcha', o una 'parada' via su punto
                # duplicado de _expand_points_with_paradas()). Con `i = j + 1`
                # ese punto nunca volvia a evaluarse como inicio de segmento, asi
                # que su propio tramo (2da antorcha / pausa) jamas se generaba.
                # Mismo fix aplicado en group_segments() (generate_slots_cerdo_1.py)
                # -- deben coincidir.
                i = j
        else:
            segments.append({"type": move, "points": [pts[i], pts[i + 1]]})
            i += 1

    # NUEVO (Kebyn, "crear pared no debe pedir punto siguiente"): el while
    # de arriba nunca evalua el ULTIMO punto de la lista como p0 (condicion
    # `i < len(pts) - 1`), asi que si el usuario marca justo ese ultimo
    # punto como "Crear pared NxN bloques" no hay pts[i+1] real con el que
    # emparejarlo. En vez de bloquear la opcion (aviso "necesita un punto
    # siguiente"), se genera su propio segmento duplicando el punto
    # (pts[-1], pts[-1]) -- el mismo caso "degenerado" (points[0]==points[1])
    # que _compute_object_placement_target()/_compute_wall_grid_coords()
    # (generate_slots_cerdo_1.py) ya sabian manejar desde el principio: la
    # pared se planta OBJECT_PLACEMENT_FORWARD_STEP (1m) adelante del
    # personaje segun su orientacion actual (root_rot heredado del ultimo
    # tramo caminado), sin necesitar una coordenada real distinta. Debe
    # coincidir con el mismo cambio en _group_segments_legacy()
    # (generate_slots_cerdo_1.py).
    if pts and getattr(pts[-1], "tipo_segmento", "AUTO") == "CREAR_PARED_NXN":
        segments.append({"type": "crear_pared_nxn", "points": [pts[-1], pts[-1]]})

    return segments


class _StopPointStub:
    """Objeto liviano con la misma 'forma' que CERDO_1PathPoint (coords,
    texture, face_index) usado para representar el punto DUPLICADO que se
    inserta automaticamente detras de cada punto marcado como parada.
    No es una PropertyGroup real (no se guarda en la escena) -- solo existe
    en memoria mientras se arma el recorrido para preview/exportacion."""
    __slots__ = ("coords", "texture", "face_index", "es_parada_dup")

    def __init__(self, coords, texture, face_index):
        self.coords     = tuple(coords)
        self.texture    = texture
        self.face_index = face_index
        # MARCA (Kebyn, 2026-08-23 tris): identifica a este punto como el
        # duplicado auto-insertado de una "parada" -- ver el fix de
        # "caminar fantasma entre Parada y Levantarse" en _detect_move()
        # mas arriba en este archivo.
        self.es_parada_dup = True


def _expand_points_with_paradas(pts):
    """PASO OPCIONAL (pedido de Kebyn, 2026-08-02): en la lista "Coordenadas
    seleccionadas" del Paso 1, cada punto tiene un dropdown editable
    (pt.tipo_segmento) que por defecto esta en 'AUTO' (caminar/salto segun
    la geometria, comportamiento de siempre) pero que el usuario puede
    cambiar a 'PARADA'. Esta funcion recorre los puntos e inserta,
    inmediatamente despues de cada punto marcado como PARADA, un punto
    DUPLICADO (mismas coordenadas) -- reutilizando asi el mecanismo ya
    existente de deteccion de 'parada' (dos puntos consecutivos con
    coordenadas identicas, ver detect_movement_type() en
    generate_slots_cerdo_1.py y _detect_move() en este mismo archivo), sin
    que el usuario tenga que seleccionar la misma face dos veces (el
    handler de seleccion de faces ya lo impide por diseno).

    Si NINGUN punto esta en modo PARADA (todos en AUTO), la lista
    resultante es identica a la original -- el flujo de solo caminar no
    se ve afectado en absoluto.

    Retorna una tupla:
      (puntos_expandidos, frames_paradas_marcadas, anim_files_paradas_marcadas,
       rot_paradas_marcadas)
    donde frames_paradas_marcadas es la lista de pt.parada_frames_punto,
    anim_files_paradas_marcadas es la lista de pt.parada_anim_file (NUEVO,
    Kebyn 2026-09-13 -- animacion .py importada por punto de parada, o
    "" si el punto no tiene ninguna asociada), y rot_paradas_marcadas es
    la lista de tuplas (rot_saved: bool, rot_z_deg: float) -- orientacion
    GUARDADA a mano para ese punto de parada (ver
    CERDO_1PathPoint.parada_rot_saved / parada_rot_z y
    CERDO_1PR_OT_SaveParadaRot) -- las tres en el mismo orden en que
    apareceran los segmentos 'parada' que produzca luego
    group_segments()/_group_segments() sobre el resultado.
    """
    expanded = []
    frames_paradas_marcadas = []
    anim_files_paradas_marcadas = []
    rot_paradas_marcadas = []
    n = len(pts)
    for i, pt in enumerate(pts):
        expanded.append(pt)

        override_activo = getattr(pt, "tipo_segmento", "AUTO") == "PARADA"

        # SALVAGUARDA (Kebyn, 2026-08-02): las coordenadas de saltar_subir /
        # saltar_bajar NO se pueden alterar a parada -- solo los tramos que
        # geometricamente son "caminar" (Z constante). Si por cualquier
        # motivo (ej. se recorto/cambio un punto despues de marcarlo) el
        # tramo real hacia el siguiente punto resulta ser un salto, se
        # ignora el override aunque tipo_segmento siga en "PARADA".
        if override_activo and i < n - 1:
            real_move = _detect_move(pt, pts[i + 1])
            if real_move != "caminar":
                override_activo = False

        if override_activo:
            expanded.append(_StopPointStub(pt.coords, pt.texture, pt.face_index))
            frames_paradas_marcadas.append(max(1, int(pt.parada_frames_punto)))
            anim_files_paradas_marcadas.append(getattr(pt, "parada_anim_file", "") or "")
            rot_paradas_marcadas.append((
                bool(getattr(pt, "parada_rot_saved", False)),
                float(getattr(pt, "parada_rot_z", 0.0)),
            ))
    return expanded, frames_paradas_marcadas, anim_files_paradas_marcadas, rot_paradas_marcadas


def calcular_estimacion_slots(scene):
    """
    NUEVO 2026-08-02 (pedido de Kebyn): version reutilizable de la
    "Estimacion de slots" del Paso 2 (panels.py), pensada para poder
    guardarla tambien en el configuracion.json al exportar (ver
    CERDO_1_ST_OT_SaveConfig / _serialize_configuracion en config_ops.py),
    ademas de dibujarla en el panel. Antes esta logica vivia SOLO dentro
    de panels.draw() y se perdia apenas se cerraba Blender -- el
    configuracion.json exportado no traia rastro de ella.

    Recibe directamente la Scene (no el Context completo) para poder
    llamarse tanto desde panels.draw(context) (pasando context.scene)
    como desde _serialize_configuracion() en config_ops.py (pasando
    st.id_data o bpy.context.scene), sin depender de un bpy.types.Context
    real en ese segundo caso.

    Devuelve una tupla (slots, fuente):
      - fuente == "paso3_segmentos": ya existen segmentos reales en
        scene.cerdo_1_segs.segments (recorrido dividido en Paso 3, o
        config cargada) -- se listan ESOS directamente, con el mismo
        frame_start/frame_end/frame_end_auto que usa el panel. "tipo" se
        deriva del label ("NN_tipo[_intervalo_caminata_normal]", mismo
        formato que arma AutoSplitFromConfig en operators_segments.py y
        que ya interpreta cerdo_1_filter.py en el pipeline externo).
      - fuente == "estimacion_geometrica": todavia no hay segmentos
        reales -- fallback idéntico al que usaba panels.py: se agrupan
        pc.path_points (con las paradas ya expandidas) via
        _group_segments(), y se estima la duracion de cada tramo con las
        mismas constantes/formula que generate_caminar() en
        generate_slots_cerdo_1.py.
      - Si no hay nada que estimar (ni segmentos reales ni 2+
        path_points), devuelve ([], None).

    Cada slot es un dict serializable a JSON:
        {"slot": int, "tipo": str, "label": str, "frames_estimados": int}
    """
    real_segs = None
    try:
        real_segs = scene.cerdo_1_segs.segments
    except Exception:
        real_segs = None

    if real_segs:
        import re as _re_est
        slots = []
        for i, rseg in enumerate(real_segs):
            # FIX (aislar Paso 2 de Paso 3, 2026-08-04): esta es la
            # "Estimacion de segmentos" del PASO 2, asi que tiene que
            # mostrar lo que el Paso 2 configuro (frame_start_planned/
            # frame_end_planned, fijados una sola vez al dividir el
            # recorrido o al usar "Actualizar" en el Paso 2) y NO lo que
            # las poses del Paso 3 hayan dejado en frame_start/frame_end
            # -- esos siguen cambiando libremente para Concatenar/NLA,
            # pero ya no deben filtrarse hacia este panel. Fallback a los
            # campos en vivo solo para segmentos/config viejos que todavia
            # no tienen la foto seteada (frame_end_planned == 0).
            if rseg.frame_end_planned > rseg.frame_start_planned:
                fs = rseg.frame_start_planned
                fe = rseg.frame_end_planned
            else:
                fs = rseg.frame_start
                fe = rseg.frame_end if rseg.frame_end > fs else rseg.frame_end_auto
            dur = max(fe - fs + 1, 0)
            label = rseg.label or "Segmento"
            m = _re_est.match(r'^\d+_(.+)$', label)
            rest = m.group(1) if m else label
            tipo = rest[:-len("_intervalo_caminata_normal")] \
                if rest.endswith("_intervalo_caminata_normal") else rest
            slots.append({
                "slot": i + 1,
                "tipo": tipo,
                "label": label,
                "frames_estimados": dur,
            })
        return slots, "paso3_segmentos"

    slots = calcular_estimacion_geometrica(scene)
    if slots is None:
        return [], None
    return slots, "estimacion_geometrica"


def calcular_estimacion_geometrica(scene):
    """
    NUEVO (Kebyn, 2026-08-02): parte puramente geometrica de
    calcular_estimacion_slots(), separada para poder invocarla directo
    -- SIN pasar primero por el chequeo de "ya hay segmentos reales" --
    desde CERDO_1SEG_OT_AutoSplitFromConfig (boton "Dividir segmentos"
    del Paso 3), que necesita recalcular los tramos del recorrido
    aunque ya existan segmentos viejos (para poder reemplazarlos).

    Devuelve la misma lista de dicts que calcular_estimacion_slots()
    (fuente "estimacion_geometrica"), o None si no hay suficientes
    puntos de recorrido para estimar nada.
    """
    pc = getattr(scene, "cerdo_1_path", None)
    if pc is None or not pc.path_points or (len(pc.path_points) == 1 and not is_woodcut(pc.path_points[0].tipo_segmento)):
        return None

    from .generate_slots_cerdo_1 import WALK_STYLE_PARAMS as _WSP

    pts = list(pc.path_points)
    expanded_pts, frames_paradas_marcadas, _anim_files_marcadas_est, _rot_marcadas_est = _expand_points_with_paradas(pts)
    segs = _group_segments(expanded_pts)

    # FIX (Kebyn, "hay una parada del personaje ... antes de reproducir las
    # poses del segmento 16" -- hueco/freeze de ~20f justo antes del limite
    # entre el ultimo tramo 'caminar' y el siguiente segmento): esta
    # estimacion (usada tanto para el panel "Estimacion de segmentos" como
    # para los limites REALES que arma "Dividir segmentos" en el Paso 3,
    # via calcular_estimacion_geometrica() -> AutoSplitFromConfig) tenia
    # HALF_CYCLE = 12 fijo, sin relacion con el ciclo biomecanico real del
    # estilo de caminata. El generador REAL (generate_caminar(), en
    # generate_slots_cerdo_1.py) fue corregido el 2026-08-21 para usar
    # HALF_CYCLE = FRAMES_PER_BIO_CYCLE / 2 = (20.0 * cycle_mult) / 2 --
    # para el estilo 'NORMAL' (cycle_mult=1.0) eso da HALF_CYCLE=10, NO 12.
    # Esta funcion nunca se actualizo junto con ese fix, asi que redondeaba
    # cada tramo 'caminar' a un multiplo de 12 mientras el Capa 1 realmente
    # horneado (por "Reproducir recorrido") lo redondeaba a un multiplo de
    # 10 (u otro valor segun cycle_mult del estilo). La diferencia es de
    # solo unos pocos frames POR tramo, pero se ACUMULA en cada tramo
    # 'caminar' sucesivo del recorrido -- con varios tramos "Caminar Normal"
    # seguidos, el desfase total llega a ~20f, y el segmento donde se nota
    # es el ULTIMO tramo caminar antes del siguiente tipo de segmento: el
    # Capa 1 real termina antes de lo que el limite del segmento (armado
    # con el HALF_CYCLE viejo) asume, y el personaje queda congelado en la
    # ultima pose de caminata hasta que el limite "estimado" por fin llega.
    # Se deriva aca el mismo HALF_CYCLE por-estilo que usa generate_caminar(),
    # asi ambos calculos vuelven a coincidir frame a frame.
    HALF_CYCLE_BASE = 12  # fallback si no hay 'cycle_mult' en el estilo (no deberia pasar)

    slots = []
    parada_idx = 0
    caminar_idx = 0
    for i, seg in enumerate(segs):
        seg_type = seg["type"]
        seg_pts = seg["points"]
        if is_woodcut(seg_type):
            slots.append({"slot":i+1,"tipo":seg_type,"label":seg_type,"frames_estimados":WOODCUT_FRAMES})
        elif seg_type == "caminar":
            # ACTUALIZADO (Kebyn, 2026-08-02): antes se usaba pc.walk_style
            # (un unico estilo global aplicado a TODOS los tramos caminar).
            # Ahora cada tramo 'caminar' detectado tiene su propio estilo
            # independiente en pc.walk_styles[caminar_idx] (sincronizado por
            # sync_walk_styles(), mismo patron que paradas_frames/parada_idx).
            style_key = (pc.walk_styles[caminar_idx].style
                         if caminar_idx < len(pc.walk_styles) else pc.walk_style)
            style_est = _WSP.get(style_key, _WSP['NORMAL'])
            FRAMES_PER_UNIT = (60.0 / 4.8284) * style_est['speed_mult']  # ~12.43 base
            # Mismo HALF_CYCLE por-estilo que generate_caminar() (ver FIX arriba).
            _cycle_mult = style_est.get('cycle_mult', 1.0)
            HALF_CYCLE = (20.0 * _cycle_mult) / 2.0 if _cycle_mult else HALF_CYCLE_BASE
            dist = 0.0
            for j in range(len(seg_pts) - 1):
                dx = seg_pts[j + 1].coords[0] - seg_pts[j].coords[0]
                dy = seg_pts[j + 1].coords[1] - seg_pts[j].coords[1]
                dist += math.sqrt(dx * dx + dy * dy)
            dist = max(dist, 0.0001)
            raw_f = dist * FRAMES_PER_UNIT
            n_half = max(1, round(raw_f / HALF_CYCLE))
            total_f = round(n_half * HALF_CYCLE)
            slots.append({
                "slot": i + 1,
                "tipo": "caminar",
                "label": f"caminar {style_est['label']}",
                "frames_estimados": total_f,
                "caminar_idx": caminar_idx,
            })
            caminar_idx += 1
        elif seg_type in ('saltar_subir','saltar_bajar','saltar_horizontal'):
            slots.append({'slot': i+1, 'tipo': seg_type, 'label': seg_type,
                          'frames_estimados': _jump.jump_frame_count(tuple(seg_pts[0].coords),
                          tuple(seg_pts[-1].coords),seg_type.removeprefix('saltar_'),scene.render.fps/scene.render.fps_base)})
        elif seg_type == "colocar_antorcha":
            # NUEVO (Kebyn, 2026-08-21): 2 puntos reales -- seg_pts[1] es
            # la coordenada de suelo donde se planta la antorcha. Se
            # incluye aca (ademas de en el .py generado) para que
            # CERDO_1SEG_OT_AutoSplitFromConfig pueda auto-registrar el
            # Cerdo_1ThrowItem sin tener que re-parsear el .py exportado.
            from .generate_slots_cerdo_1 import TOTAL_FRAMES_COLOCAR_ANTORCHA as _TFCA
            _dest = seg_pts[1].coords
            slots.append({"slot": i + 1, "tipo": "colocar_antorcha",
                           "label": "colocar_antorcha",
                           "frames_estimados": _TFCA,
                           "torch_dest": {"x": round(_dest[0], 4),
                                          "y": round(_dest[1], 4),
                                          "z": round(_dest[2], 4)}})
        elif seg_type == "golpe_estomago_1":
            # NUEVO (Kebyn): misma arquitectura que "colocar_antorcha" de
            # arriba, pero sin destino de objeto -- solo reproduce la
            # animacion completa de Mixamo en seg_pts[0].
            from .generate_slots_cerdo_1 import TOTAL_FRAMES_GOLPE_ESTOMAGO_1 as _TFGE
            slots.append({"slot": i + 1, "tipo": "golpe_estomago_1",
                           "label": "golpe_estomago_1",
                           "frames_estimados": _TFGE})
        elif seg_type == "levantarse_1":
            # NUEVO (Kebyn): misma arquitectura que "golpe_estomago_1" de
            # arriba -- solo reproduce la animacion completa de Mixamo en
            # seg_pts[0], sin destino de objeto.
            from .generate_slots_cerdo_1 import TOTAL_FRAMES_LEVANTARSE_1 as _TFL1
            slots.append({"slot": i + 1, "tipo": "levantarse_1",
                           "label": "levantarse_1",
                           "frames_estimados": _TFL1})
        elif seg_type == "levantarse_2":
            # NUEVO (Kebyn): segunda variante de "levantarse_1" de arriba,
            # misma arquitectura -- solo reproduce la animacion completa
            # de Mixamo en seg_pts[0], sin destino de objeto.
            from .generate_slots_cerdo_1 import TOTAL_FRAMES_LEVANTARSE_2 as _TFL2
            slots.append({"slot": i + 1, "tipo": "levantarse_2",
                           "label": "levantarse_2",
                           "frames_estimados": _TFL2})
        elif seg_type == "arrodillarse_1":
            # NUEVO (Kebyn): misma arquitectura que "levantarse_1"/
            # "levantarse_2" de arriba -- solo reproduce la animacion
            # completa de Mixamo en seg_pts[0], sin destino de objeto.
            from .generate_slots_cerdo_1 import TOTAL_FRAMES_ARRODILLARSE_1 as _TFA1
            slots.append({"slot": i + 1, "tipo": "arrodillarse_1",
                           "label": "arrodillarse_1",
                           "frames_estimados": _TFA1})
        elif seg_type == "conversar_1":
            # NUEVO (Kebyn): misma arquitectura que "arrodillarse_1"/
            # "levantarse_1"/"levantarse_2" de arriba -- solo reproduce la
            # animacion completa de Mixamo en seg_pts[0], sin destino de
            # objeto.
            from .generate_slots_cerdo_1 import TOTAL_FRAMES_CONVERSAR_1 as _TFC1
            slots.append({"slot": i + 1, "tipo": "conversar_1",
                           "label": "conversar_1",
                           "frames_estimados": _TFC1})
        elif seg_type == "resbalarse_1":
            # NUEVO (Kebyn): misma arquitectura que "arrodillarse_1"/
            # "levantarse_1"/"levantarse_2" de arriba -- solo reproduce
            # la animacion completa de Mixamo en seg_pts[0], sin destino
            # de objeto.
            from .generate_slots_cerdo_1 import TOTAL_FRAMES_RESBALARSE_1 as _TFR1
            slots.append({"slot": i + 1, "tipo": "resbalarse_1",
                           "label": "resbalarse_1",
                           "frames_estimados": _TFR1})
        elif seg_type == "colocar_mesa_de_crafteo":
            # NUEVO (Kebyn, 2026-08-22): misma arquitectura que
            # "colocar_antorcha" de arriba -- seg_pts[1] es la coordenada
            # de suelo donde se coloca la mesa de crafteo.
            from .generate_slots_cerdo_1 import TOTAL_FRAMES_COLOCAR_MESA_CRAFTEO as _TFCM
            _dest_mesa = seg_pts[1].coords
            slots.append({"slot": i + 1, "tipo": "colocar_mesa_de_crafteo",
                           "label": "colocar_mesa_de_crafteo",
                           "frames_estimados": _TFCM,
                           "table_dest": {"x": round(_dest_mesa[0], 4),
                                          "y": round(_dest_mesa[1], 4),
                                          "z": round(_dest_mesa[2], 4)}})
        elif seg_type == "crear_pared_nxn":
            # NUEVO (Kebyn, "crear pared NxN bloques"): misma arquitectura
            # que "colocar_mesa_de_crafteo" de arriba, pero la cantidad de
            # frames depende de filas*columnas (un ciclo agachar/colocar
            # por bloque, ver FRAMES_PER_BLOQUE_PARED_NXN en
            # generate_slots_cerdo_1.py) -- no es una constante fija.
            from .generate_slots_cerdo_1 import (
                resolve_pared_nxn_timing as _rpnt,
                _compute_wall_grid_coords as _cwgc,
            )
            _filas = max(1, int(getattr(seg_pts[0], "pared_filas", 2)))
            _columnas = max(1, int(getattr(seg_pts[0], "pared_columnas", 2)))
            _blend_path = getattr(seg_pts[0], "pared_bloque_blend_path", "") or ""
            # NUEVO (Kebyn, "elegir cuantos frames dura toda la animacion
            # de crear pared"): 0 = automatico. resolve_pared_nxn_timing()
            # es la MISMA funcion que usa el generador real
            # (generate_crear_pared_nxn()), asi que esta estimacion
            # siempre coincide exacto con la animacion generada.
            _pared_total = int(getattr(seg_pts[0], "pared_total_frames", 0) or 0)
            _FPB, _MID_FPB, _total_real = _rpnt(_filas * _columnas, _pared_total)
            # NUEVO: grilla de coordenadas (mismo calculo que usara el
            # generador real, ver _compute_wall_grid_coords()) + el frame
            # de aparicion de cada celda (relativo al inicio del slot,
            # un ciclo completo de FRAMES_PER_BLOQUE_PARED_NXN por bloque,
            # en el mismo orden fila-por-fila) -- necesario para que
            # CERDO_1SEG_OT_AutoSplitFromConfig pueda auto-registrar un
            # Cerdo_1ThrowItem por bloque sin tener que regenerar el codigo
            # completo del slot.
            # NOTA: a diferencia del generador real (generate_crear_pared_nxn),
            # aca no tenemos el heading acumulado del recorrido (_cur_rot) --
            # mismo caso que "table_dest"/"torch_dest" arriba, que tampoco lo
            # usan. root_rot solo entra como FALLBACK dentro de
            # _compute_wall_grid_coords cuando seg_pts[0]==seg_pts[1] (caso
            # degenerado); en el caso normal el angulo sale de los propios
            # puntos via _compute_direction_angle(), asi que un default fijo
            # aca es seguro y no afecta la grilla real.
            # FIX (bug preexistente, "AttributeError: bpy_prop_array[key]
            # invalid key" al dividir segmentos): seg_pts[*].coords es un
            # FloatVectorProperty (se indexa [0]/[1]/[2], no ['x']/['y']/
            # ['z']), pero _compute_wall_grid_coords()/
            # _compute_object_placement_target() esperan dicts con esas
            # claves de string (mismo formato que "coordinates" en
            # key_points/points[0]['coordinates']) -- se convierte aca.
            _p0c = {'x': seg_pts[0].coords[0], 'y': seg_pts[0].coords[1], 'z': seg_pts[0].coords[2]}
            _p1c = {'x': seg_pts[1].coords[0], 'y': seg_pts[1].coords[1], 'z': seg_pts[1].coords[2]}
            _grid = _cwgc(_p0c, _p1c, (0, 0, -90), _filas, _columnas)
            _wall_blocks_est = [
                {"row": g["row"], "col": g["col"],
                 "x": round(g["x"], 4), "y": round(g["y"], 4), "z": round(g["z"], 4),
                 # FIX (mismo bug que generate_crear_pared_nxn() ya evita):
                 # el bloque debe aparecer cuando el cuerpo esta agachado
                 # colocandolo (mitad del ciclo de FPB frames), no al
                 # arranque del ciclo -- sino aparece "de golpe" con Cerdo_1
                 # todavia parado, 15 frames antes de que se agache.
                 "appear_frame_rel": idx * _FPB + _MID_FPB,
                 # NUEVO (fix "bloques en direcciones distintas"): heading
                 # de la pared en radianes (ver _compute_wall_grid_coords()),
                 # para que CERDO_1SEG_OT_AutoSplitFromConfig lo copie tal
                 # cual a Cerdo_1ThrowItem.rot_z -- todos los bloques de la
                 # grilla quedan orientados IGUAL entre si.
                 "rot_z": round(g.get("rot_z", 0.0), 6)}
                for idx, g in enumerate(_grid)
            ]
            slots.append({"slot": i + 1, "tipo": "crear_pared_nxn",
                           "label": "crear_pared_nxn",
                           "frames_estimados": _total_real,
                           "pared_filas": _filas,
                           "pared_columnas": _columnas,
                           "pared_bloque_blend_path": _blend_path,
                           "pared_total_frames": _pared_total,
                           "wall_blocks_est": _wall_blocks_est})
        else:  # parada
            # FIX (Kebyn, 2026-08-02): la fuente de verdad de "cuantos frames
            # dura esta parada" es pt.parada_frames_punto (editable por punto
            # en la lista del Paso 1, default 24 -- ver Image2), ya calculado
            # por _expand_points_with_paradas() como frames_paradas_marcadas
            # en el mismo orden que aparecen los tramos "parada". Antes se
            # usaba pc.paradas_frames (una coleccion plana a nivel de escena,
            # remanente de "paradas_frames" en el JSON) que no reflejaba
            # ediciones por punto y desincronizaba la duracion total real.
            if parada_idx < len(frames_paradas_marcadas):
                frames_parada_actual = frames_paradas_marcadas[parada_idx]
                slots.append({"slot": i + 1, "tipo": "parada",
                              "label": "parada",
                              "frames_estimados": frames_parada_actual})
            elif parada_idx < len(pc.paradas_frames):
                frames_parada_actual = pc.paradas_frames[parada_idx].frames
                slots.append({"slot": i + 1, "tipo": "parada",
                              "label": "parada",
                              "frames_estimados": frames_parada_actual})
            else:
                slots.append({"slot": i + 1, "tipo": "parada",
                              "label": "parada (sin sincronizar)",
                              "frames_estimados": pc.frames_parada})
            parada_idx += 1

    return slots


def _ajustar_por_cuerpo(key_points):
    """Bloques de 1 m3 con un personaje LARGO (ver CUERPO_FRENTE/CUERPO_ATRAS en jump_motion.py):
    - antes de SUBIR, el punto de despegue se corre hacia atras para que el hocico quede fuera del bloque;
    - al BAJAR, el punto de aterrizaje se corre hacia delante lo justo para que las ancas no queden sobre el bloque.
    Solo mueve x/y (la altura -- y por lo tanto la deteccion caminar/subir/bajar -- no cambia)."""
    fr, at, hol = _jump.CUERPO_FRENTE, _jump.CUERPO_ATRAS, _jump.HOLGURA
    for i in range(len(key_points) - 1):
        a = key_points[i]["coordinates"]; b = key_points[i + 1]["coordinates"]
        dx, dy = b["x"] - a["x"], b["y"] - a["y"]; d = math.hypot(dx, dy); dz = round(b["z"], 2) - round(a["z"], 2)
        if d < 1e-6 or dz == 0:
            continue
        ux, uy = dx / d, dy / d
        if dz > 0:
            atras = max(0.0, fr + hol - (d - 0.5))
            a["x"] = round(a["x"] - ux * atras, 4); a["y"] = round(a["y"] - uy * atras, 4)
        else:
            lejos = 0.5 + at + 0.16
            if d < lejos:
                b["x"] = round(a["x"] + ux * lejos, 4); b["y"] = round(a["y"] + uy * lejos, 4)
    return key_points


def _pt_to_dict(pt, idx):
    return {
        "index": idx + 1,
        "coordinates": {"x": round(pt.coords[0], 4),
                        "y": round(pt.coords[1], 4),
                        "z": round(pt.coords[2], 4)},
        "texture": pt.texture,
        "face_index": pt.face_index,
        # NUEVO (Kebyn, 2026-08-21): viaja el override de tipo_segmento
        # hasta gen.detect_movement_type()/gen.group_segments() para que
        # "colocar_antorcha" (y a futuro otros overrides de 2 puntos
        # reales) se reconozca ahi tambien -- los _StopPointStub del
        # mecanismo de PARADA no tienen este atributo, de ahi el
        # getattr() con fallback "AUTO".
        "tipo_segmento": getattr(pt, "tipo_segmento", "AUTO"),
    }


# =============================================================================
# OPERADORES
# =============================================================================

class CERDO_1PR_OT_ToggleRecording(Operator):
    bl_idname  = "cerdo_1pr.toggle_recording"
    bl_label   = "Toggle Recording"
    bl_description = "Inicia o detiene la grabacion de puntos del recorrido"
    bl_options = {"REGISTER"}

    def execute(self, context):
        pc = context.scene.cerdo_1_path
        pc.recording_active = not pc.recording_active

        if pc.recording_active:
            _ensure_draw_handler()
            self.report({"INFO"}, "Grabacion INICIADA — selecciona faces en modo EDIT")
        else:
            # CORREGIDO (Kebyn, 2026-08-02): antes esto eliminaba el draw
            # handler incondicionalmente, asi que el recorrido trazado
            # desaparecia del viewport apenas se presionaba "Detener
            # grabacion". Ahora _maybe_remove_draw_handler() solo lo quita
            # si el usuario tampoco dejo activada la visualizacion
            # persistente (pc.show_path_viz / boton "Visualizar recorrido").
            _maybe_remove_draw_handler(pc)
            self.report({"INFO"}, "Grabacion DETENIDA")

        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
        return {"FINISHED"}


class CERDO_1PR_OT_TogglePathViz(Operator):
    """NUEVO (Kebyn, 2026-08-02): boton independiente de la grabacion para
    mostrar/ocultar la linea y los puntos numerados del recorrido ya
    trazado. Antes, la unica forma de ver el recorrido en el viewport era
    tener la grabacion activa; al presionar "Detener grabacion" el trazado
    se volvia invisible. Con esto se puede revisar el recorrido en
    cualquier momento (por ejemplo despues de cargar una configuracion
    guardada) sin tener que re-entrar en modo grabacion."""
    bl_idname  = "cerdo_1pr.toggle_path_viz"
    bl_label   = "Visualizar recorrido"
    bl_description = (
        "Muestra u oculta la linea y los puntos numerados del recorrido "
        "trazado en el viewport, sin necesidad de estar grabando"
    )
    bl_options = {"REGISTER"}

    def execute(self, context):
        pc = context.scene.cerdo_1_path
        pc.show_path_viz = not pc.show_path_viz

        if pc.show_path_viz:
            _ensure_draw_handler()
        else:
            _maybe_remove_draw_handler(pc)

        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
        return {"FINISHED"}


class CERDO_1PR_OT_RemoveLast(Operator):
    bl_idname  = "cerdo_1pr.remove_last"
    bl_label   = "Eliminar ultimo punto"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        pc = context.scene.cerdo_1_path
        if len(pc.path_points) > 0:
            pc.path_points.remove(len(pc.path_points) - 1)
        sync_paradas_frames(pc)
        sync_walk_styles(pc)
        return {"FINISHED"}


class CERDO_1PR_OT_RemovePoint(Operator):
    """
    Elimina UNA coordenada puntual de la lista (boton 'X' por fila en el
    panel "Coordenadas seleccionadas", Paso 1), a diferencia de
    CERDO_1PR_OT_RemoveLast (que solo saca la ultima) y CERDO_1PR_OT_ClearPath
    (que vacia todo el recorrido). Reutiliza el mismo criterio de
    sincronizacion posterior (sync_paradas_frames + sync_walk_styles) que
    esos dos operadores, porque quitar cualquier punto intermedio puede
    correr los indices de 'Parada' y de los tramos 'caminar'.
    """
    bl_idname  = "cerdo_1pr.remove_point"
    bl_label   = "Eliminar coordenada"
    bl_description = "Quita esta coordenada de la lista del recorrido"
    bl_options = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty(default=0)

    def execute(self, context):
        pc = context.scene.cerdo_1_path
        if 0 <= self.index < len(pc.path_points):
            pc.path_points.remove(self.index)
        sync_paradas_frames(pc)
        sync_walk_styles(pc)
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
        return {"FINISHED"}


class CERDO_1PR_OT_ImportParadaAnim(Operator):
    """NUEVO (Kebyn, 2026-09-13): boton 'Importar animacion (.py)' que
    aparece en el panel junto al campo 'Frames' de un punto marcado como
    'Parada' (ver panels.py). Deja elegir un script .py de animacion
    importada (tipicamente exportado por el conversor de Mixamo, mismo
    formato que slot_001_parado_discutiendo_dba2c3.py) para que ese
    punto de parada reproduzca esa animacion completa en vez de la pose
    estatica 'parado' -- ver generate_parada()/anim_file_path en
    generate_slots_cerdo_1.py.

    Al elegir el archivo, se lee su duracion real (frame_count) y se
    sincroniza automaticamente pt.parada_frames_punto con ese valor --
    asi el campo 'Frames' del panel queda mostrando la duracion REAL del
    clip (la que realmente se va a reproducir al apretar "Reproducir
    recorrido"), sin que el usuario tenga que calcularla a mano. Mismo
    criterio que ya usan golpe_estomago_1/levantarse_1/conversar_1/etc.,
    cuya duracion tambien la fija el clip Mixamo, no un valor editable.
    """
    bl_idname    = "cerdo_1pr.import_parada_anim"
    bl_label     = "Importar animacion (.py)"
    bl_description = (
        "Selecciona un script .py de animacion (ej. exportado por el "
        "conversor de Mixamo) para reproducir en este punto de parada, "
        "en vez de la pose estatica por defecto"
    )
    bl_options   = {"REGISTER", "UNDO"}

    index:       bpy.props.IntProperty(default=-1)
    filepath:    StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.py", options={"HIDDEN"})

    def invoke(self, context, event):
        pc = context.scene.cerdo_1_path
        if 0 <= self.index < len(pc.path_points):
            existing = pc.path_points[self.index].parada_anim_file
            if existing:
                self.filepath = bpy.path.abspath(existing)
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        pc = context.scene.cerdo_1_path
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
            from .generate_slots_cerdo_1 import _load_keyframe_data_from_anim_file
            _kf, frame_count = _load_keyframe_data_from_anim_file(src)
        except Exception as e:
            print(f"cerdo_1pr.import_parada_anim: no se pudo leer duracion de '{src}': {e}")

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


class CERDO_1PR_OT_ClearParadaAnim(Operator):
    """Quita la animacion .py importada de un punto de 'Parada',
    volviendo al comportamiento por defecto (pose estatica 'parado')."""
    bl_idname    = "cerdo_1pr.clear_parada_anim"
    bl_label     = "Quitar animacion importada"
    bl_description = (
        "Quita la animacion .py importada de este punto de parada "
        "(vuelve a la pose estatica por defecto)"
    )
    bl_options   = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        pc = context.scene.cerdo_1_path
        if 0 <= self.index < len(pc.path_points):
            pc.path_points[self.index].parada_anim_file = ""
        return {"FINISHED"}


class CERDO_1PR_OT_OpenInteractionFolder(Operator):
    """Abre (y crea si no existe) la carpeta de animaciones de
    interaccion de Cerdo_1 (DEFAULT_INTERACTION_DIR_CERDO_1, constants.py).
    Ahi se guardan los .py que despues aparecen automaticamente en el
    dropdown 'Animacion de interaccion' de cualquier punto de encuentro
    con Jerry (ver _interaccion_anim_items() mas arriba).
    """
    bl_idname    = "cerdo_1pr.open_interaction_folder"
    bl_label     = "Abrir carpeta de interacciones (cerdo_1)"
    bl_description = (
        "Abre la carpeta donde van los .py de animaciones de "
        "interaccion de Cerdo_1 (se crea si todavia no existe)"
    )
    bl_options   = {"REGISTER"}

    def execute(self, context):
        import subprocess
        folder = DEFAULT_INTERACTION_DIR_CERDO_1
        try:
            os.makedirs(folder, exist_ok=True)
            subprocess.Popen(f'explorer "{folder}"')
            self.report({"INFO"}, f"Carpeta: {folder}")
        except Exception as e:
            self.report({"WARNING"}, f"No se pudo abrir: {e}")
        return {"FINISHED"}


class CERDO_1PR_OT_RotateParadaRoot(Operator):
    """NUEVO (Kebyn, 2026-09-13): boton 'Rotar root (cerdo_1)' en el panel
    de un punto marcado como 'Parada'. Selecciona y activa el empty root
    (ROOT_NAME = 'cerdo_1') y lanza el transform.rotate interactivo de
    Blender constreñido al eje Z (mismo comportamiento que presionar R,
    Z en el viewport) para que el usuario oriente al personaje a ojo.
    Una vez conforme con la orientacion, usar el boton 'Guardar
    orientacion' (CERDO_1PR_OT_SaveParadaRot) para grabarla en este punto.
    """
    bl_idname    = "cerdo_1pr.rotate_parada_root"
    bl_label     = "Rotar root (cerdo_1)"
    bl_description = (
        "Selecciona el empty root 'cerdo_1' y arranca una rotacion "
        "interactiva en el eje Z (como R, Z en el viewport). Mueve el "
        "mouse y hace click izquierdo para confirmar, luego usa 'Guardar "
        "orientacion' para grabar el resultado en este punto de parada"
    )
    bl_options   = {"REGISTER", "UNDO"}

    ROOT_NAME = "cerdo_1"

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


class CERDO_1PR_OT_SaveParadaRot(Operator):
    """NUEVO (Kebyn, 2026-09-13): boton 'Guardar orientacion' -- lee la
    rotacion Z ACTUAL del empty root 'cerdo_1' (la que haya quedado tras
    rotarlo a mano, ej. con CERDO_1PR_OT_RotateParadaRoot o R, Z directo
    en el viewport) y la graba en pt.parada_rot_z (convertida a grados,
    mismo formato que pc.root_rot_z), activando pt.parada_rot_saved.
    Ver comentario completo en CERDO_1PathPoint.parada_rot_saved sobre
    como se propaga este heading al resto del recorrido (Paso 2/3).
    """
    bl_idname    = "cerdo_1pr.save_parada_rot"
    bl_label     = "Guardar orientacion"
    bl_description = (
        "Graba la rotacion Z ACTUAL del root 'cerdo_1' como el heading de "
        "este punto de parada. Se mantendra para el resto del recorrido "
        "(pasos 2 y 3) hasta el proximo tramo con desplazamiento real, o "
        "hasta que se vuelva a editar"
    )
    bl_options   = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty(default=-1)
    ROOT_NAME = "cerdo_1"

    def execute(self, context):
        pc = context.scene.cerdo_1_path
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


class CERDO_1PR_OT_ClearParadaRot(Operator):
    """Quita la orientacion guardada de un punto de 'Parada', volviendo
    al heading automatico (ultimo tramo con desplazamiento real)."""
    bl_idname    = "cerdo_1pr.clear_parada_rot"
    bl_label     = "Quitar orientacion guardada"
    bl_description = (
        "Quita la orientacion guardada de este punto de parada (vuelve "
        "al heading automatico)"
    )
    bl_options   = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        pc = context.scene.cerdo_1_path
        if 0 <= self.index < len(pc.path_points):
            pc.path_points[self.index].parada_rot_saved = False
        return {"FINISHED"}


class CERDO_1PR_OT_ClearPath(Operator):
    bl_idname  = "cerdo_1pr.clear_path"
    bl_label   = "Limpiar recorrido"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        pc = context.scene.cerdo_1_path
        pc.path_points.clear()
        sync_paradas_frames(pc)
        sync_walk_styles(pc)
        return {"FINISHED"}


class CERDO_1PR_OT_SyncParadasFrames(Operator):
    """Ajusta pc.paradas_frames a la cantidad real de paradas del
    recorrido actual. NUEVO 2026-07-09: boton de respaldo manual — la
    sincronizacion ya ocurre automaticamente al agregar/quitar puntos,
    generar preview/exportar, o cargar un config.json, pero al escribir
    en datos de la escena esto NO puede hacerse desde draw() (Blender lo
    prohibe), asi que este boton cubre cualquier caso borde donde el
    recorrido haya cambiado por otra via."""
    bl_idname  = "cerdo_1pr.sync_paradas_frames"
    bl_label   = "Sincronizar frames por parada"
    bl_description = (
        "Ajusta la lista de frames por parada a la cantidad real de "
        "paradas detectadas en el recorrido actual, conservando los "
        "valores ya editados a mano"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        pc = context.scene.cerdo_1_path
        n = sync_paradas_frames(pc)
        n_walk = sync_walk_styles(pc)
        self.report({"INFO"}, f"Sincronizado: {n} parada(s) y {n_walk} tramo(s) de caminata detectado(s)")
        return {"FINISHED"}


class CERDO_1PR_OT_OpenBlendFile(Operator):
    bl_idname  = "cerdo_1pr.open_blend"
    bl_label   = "Seleccionar .blend"
    bl_options = {"REGISTER"}
    filepath: StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        context.scene.cerdo_1_path.blend_filepath = self.filepath
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


# =============================================================================
# PREVIEW PATH — Reproducir recorrido en viewport
# =============================================================================

# Version de la LOGICA de generacion del recorrido (no de los datos). Subir
# este numero cada vez que cambie como se interpretan los segmentos (ej. el
# fix 2026-07-11 que excluye las "paradas" del boton "Reproducir recorrido")
# para que compute_recorrido_fingerprint() invalide cualquier bake horneado
# con una version anterior de la logica, aunque los datos no hayan cambiado.
_FINGERPRINT_LOGIC_VERSION = 4

def compute_recorrido_fingerprint(context):
    """Genera una huella (hash) de todo lo que puede afectar el resultado de
    'Reproducir recorrido': los puntos del path, la rotacion del root, los
    frames de arranque y, si ya se ejecuto "Concatenar segmentos", las poses
    reinyectadas (Capa 2). Se usa para saber si el recorrido horneado en la
    timeline sigue siendo valido y asi evitar regenerar (proceso costoso)
    cuando nada cambio desde la ultima vez que se genero.

    Kebyn, 2026-07-11: agregado para que el boton "Reproducir recorrido" de
    cada segmento no tenga que regenerar el recorrido COMPLETO en cada click
    (eso era lento) cuando la animacion ya horneada sigue siendo valida.

    Kebyn, 2026-07-11 (2): se agrega _FINGERPRINT_LOGIC_VERSION a la huella.
    La huella anterior solo dependia de los DATOS (puntos, rotacion, frames),
    no del CODIGO que los interpreta — asi que un bake horneado con una
    version vieja de la logica (ej. antes de excluir las "paradas" del
    boton "Reproducir recorrido") se seguia reutilizando tal cual despues de
    actualizar el addon, porque los datos no habian cambiado. Subir esta
    constante cada vez que cambia la logica de generacion invalida
    cualquier bake previo y fuerza una regeneracion con el codigo actual.
    """
    import hashlib
    import json as _json
    pc = context.scene.cerdo_1_path
    parts = [("_fingerprint_logic_version", _FINGERPRINT_LOGIC_VERSION)]
    for pt in pc.path_points:
        parts.append((
            round(pt.coords[0], 4), round(pt.coords[1], 4), round(pt.coords[2], 4),
            pt.texture, pt.face_index,
        ))
    parts.append(("root_rot", pc.root_rot_x, pc.root_rot_y, pc.root_rot_z))
    parts.append(("frame_inicio", pc.frame_inicio, pc.slot_inicio))
    parts.append(("frames_parada", pc.frames_parada))
    parts.append(tuple((p.frames,) for p in pc.paradas_frames))

    cerdo_1_obj = bpy.data.objects.get("cerdo_1")
    if cerdo_1_obj:
        parts.append(("concat_arm",   cerdo_1_obj.get("_concat_arm_data", "")))
        parts.append(("concat_root",  cerdo_1_obj.get("_concat_root_data", "")))
        parts.append(("concat_start", cerdo_1_obj.get("_concat_frame_start", "")))
        parts.append(("concat_end",   cerdo_1_obj.get("_concat_frame_end", "")))

    raw = _json.dumps(parts, default=str, sort_keys=False)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


class CERDO_1PR_OT_PreviewPath(Operator):
    """Reproduce el recorrido de Cerdo_1 en el viewport con animacion base."""
    bl_idname  = "cerdo_1pr.preview_path"
    bl_label   = "Reproducir recorrido"
    bl_description = (
        "Genera la animacion base de Cerdo_1 (caminar/saltar) directamente "
        "en el viewport segun los puntos del recorrido"
    )
    bl_options = {"REGISTER"}

    ROOT_NAME = "cerdo_1"
    ARM_NAME  = "pig.arma_cerdo_1"

    # ── Carga lazy del modulo generate_slots_cerdo_1 ──────────────────────────
    @staticmethod
    def _get_gen():
        """Carga generate_slots_cerdo_1.py siempre fresco (sin cache) para garantizar coherencia."""
        import importlib.util as _ilu
        import sys as _sys
        # Siempre recargar — evita que una version cacheada desincronice preview vs exportacion
        _sys.modules.pop("gen_slots_cerdo_1_preview", None)
        addon_dir = os.path.dirname(os.path.abspath(__file__))
        gen_path  = os.path.join(addon_dir, "generate_slots_cerdo_1.py")
        spec = _ilu.spec_from_file_location("gen_slots_cerdo_1_preview", gen_path)
        mod  = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _sys.modules["gen_slots_cerdo_1_preview"] = mod
        return mod

    # ── Aplicar keyframes Mixamo reales: saltar_subir (18 frames) ────────────
    def _bones_saltar_subir(self, bones, frame, rf):
        """Aplica los keyframes Mixamo reales de KEYFRAMES_SALTAR_SUBIR al frame dado."""
        gen = self._get_gen()
        kf_data = gen.KEYFRAMES_SALTAR_SUBIR
        # rf es el offset relativo al inicio del slot (0-based)
        # Buscamos el frame de referencia mas cercano en los datos (0..17)
        rel = min(max(rf, 0), 17)
        for bone_name, frames_dict in kf_data.items():
            bone = bones.get(bone_name)
            if bone is None:
                continue
            # Interpolacion lineal entre el frame anterior y siguiente disponible
            keys = sorted(frames_dict.keys())
            # Encontrar los dos frames que encuadran rel
            lo = keys[0]; hi = keys[-1]
            for k in keys:
                if k <= rel:
                    lo = k
                if k >= rel:
                    hi = k
                    break
            if lo == hi:
                rot = frames_dict[lo]
            else:
                t = (rel - lo) / (hi - lo)
                r0 = frames_dict[lo]; r1 = frames_dict[hi]
                rot = (r0[0] + (r1[0]-r0[0])*t,
                       r0[1] + (r1[1]-r0[1])*t,
                       r0[2] + (r1[2]-r0[2])*t)
            bone.rotation_euler = rot
            self._kfb(bone, frame)

    # ── Aplicar keyframes Mixamo reales: saltar_bajar (35 frames) ────────────
    def _bones_saltar_bajar(self, bones, frame, rf):
        """Aplica los keyframes Mixamo reales de KEYFRAMES_SALTAR_BAJAR al frame dado."""
        gen = self._get_gen()
        kf_data = gen.KEYFRAMES_SALTAR_BAJAR
        rel = min(max(rf, 0), 34)
        for bone_name, frames_dict in kf_data.items():
            bone = bones.get(bone_name)
            if bone is None:
                continue
            keys = sorted(frames_dict.keys())
            lo = keys[0]; hi = keys[-1]
            for k in keys:
                if k <= rel:
                    lo = k
                if k >= rel:
                    hi = k
                    break
            if lo == hi:
                rot = frames_dict[lo]
            else:
                t = (rel - lo) / (hi - lo)
                r0 = frames_dict[lo]; r1 = frames_dict[hi]
                rot = (r0[0] + (r1[0]-r0[0])*t,
                       r0[1] + (r1[1]-r0[1])*t,
                       r0[2] + (r1[2]-r0[2])*t)
            bone.rotation_euler = rot
            self._kfb(bone, frame)

    # ── Caminar: biomecánica identica a generate_caminar ─────────────────────
    def _bones_caminar(self, bones, frame, rf, fpb):
        """Marcha de CUADRUPEDO del cerdo (identica a la de generate_caminar en generate_slots_cerdo_1.py, estilo NORMAL):
        pares diagonales FL+BR / FR+BL, eje X local de las patas = adelante/atras."""
        FRAMES_PER_BIO_CYCLE = 20.0
        total_slot = max(fpb, 1)
        walk_cycle = (rf / total_slot) * (total_slot / FRAMES_PER_BIO_CYCLE)
        _ph = walk_cycle * 2 * math.pi
        _sw = math.radians(50) * 0.6; _kf = math.radians(40) * 0.5
        _a = math.sin(_ph); _ka = -_kf * max(0.0, math.cos(_ph)); _kb = -_kf * max(0.0, -math.cos(_ph))
        rot = {
            'Leg:FL_cerdo_1': (_sw * _a, 0.0, 0.0), 'Leg:BR_cerdo_1': (_sw * _a, 0.0, 0.0),
            'Leg:FR_cerdo_1': (-_sw * _a, 0.0, 0.0), 'Leg:BL_cerdo_1': (-_sw * _a, 0.0, 0.0),
            'Leg:FL:Bend_cerdo_1': (_ka, 0.0, 0.0), 'Leg:BR:Bend_cerdo_1': (_ka, 0.0, 0.0),
            'Leg:FR:Bend_cerdo_1': (_kb, 0.0, 0.0), 'Leg:BL:Bend_cerdo_1': (_kb, 0.0, 0.0),
            'Body_cerdo_1': (math.sin(2 * _ph) * math.radians(1.5), math.sin(_ph) * math.radians(3), 0.0),
            'Body:Bend_cerdo_1': (-math.sin(2 * _ph) * math.radians(0.75), -math.sin(_ph) * math.radians(1.2), 0.0),
            'Head_cerdo_1': (math.sin(2 * _ph + 0.6) * math.radians(4), 0.0, math.sin(_ph) * math.radians(2)),
        }
        for name, r in rot.items():
            if name in bones:
                bones[name].rotation_euler = r
                self._kfb(bones[name], frame)

    # ── Posicion root: salto subir ───────────────────────────────────────────
    @staticmethod
    def _pos_saltar_subir(p0c, p1c, rf):
        """Parabola ascendente para Cerdo_1 (18 frames)."""
        ox, oy, oz = p0c[0], p0c[1], p0c[2]
        dx = p1c[0] - ox;  dy = p1c[1] - oy;  dz = p1c[2] - oz
        TOTAL = 18
        t = rf / max(TOTAL - 1, 1)
        t_s = t * t * (3 - 2 * t)   # smoothstep
        dist_xy = math.sqrt(dx * dx + dy * dy)
        H = max(abs(dz) * 0.6, dist_xy * 0.3, 0.3)
        arc = 4 * H * t_s * (1 - t_s)
        return (ox + t_s * dx, oy + t_s * dy, oz + t_s * dz + arc)

    # ── Posicion root: salto bajar ───────────────────────────────────────────
    @staticmethod
    def _pos_saltar_bajar(p0c, p1c, rf):
        """Caida para Cerdo_1 (35 frames)."""
        ox, oy, oz = p0c[0], p0c[1], p0c[2]
        dx = p1c[0] - ox;  dy = p1c[1] - oy;  dz = p1c[2] - oz
        TOTAL = 35
        t = rf / max(TOTAL - 1, 1)
        # Caida: ease-in horizontal, aceleracion gravitatoria en Z
        t_h = t * t * (3 - 2 * t)
        t_z = t * t  # ease-in para caida libre
        return (ox + t_h * dx, oy + t_h * dy, oz + t_z * dz)

    # ── Helpers ──────────────────────────────────────────────────────────────
    @staticmethod
    def _kf(obj, frame):
        obj.keyframe_insert(data_path="location",       frame=frame)
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)

    @staticmethod
    def _kfb(bone, frame):
        bone.keyframe_insert(data_path="rotation_euler", frame=frame)

    @staticmethod
    def _compute_direction_angle(dx, dy, fallback_deg):
        if dx == 0 and dy == 0:
            return fallback_deg
        ang_raw = math.degrees(math.atan2(dx, dy))
        ang_rounded = round(ang_raw / 90.0) * 90.0
        ang = ang_rounded if abs(ang_raw - ang_rounded) < 45 else ang_raw
        while ang >  180: ang -= 360
        while ang < -180: ang += 360
        if   ang ==  90: ang = -90
        elif ang == -90: ang =  90
        elif ang == 180: ang = -180
        return ang

    class _RotationSmoother:
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

    @staticmethod
    def _build_caminar_segments(pts):
        segs = []
        dists = []
        for i in range(len(pts) - 1):
            ax, ay = pts[i].coords[0],  pts[i].coords[1]
            bx, by = pts[i+1].coords[0], pts[i+1].coords[1]
            d = math.sqrt((bx-ax)**2 + (by-ay)**2)
            segs.append({"start": (ax, ay, pts[i].coords[2]),
                         "end":   (bx, by, pts[i+1].coords[2])})
            dists.append(max(d, 1e-6))
        return segs, dists

    @staticmethod
    def _alloc_frames(dists, total_frames):
        total_dist = sum(dists)
        if total_dist < 1e-9:
            per = [total_frames // len(dists)] * len(dists)
        else:
            per = [max(1, round(d / total_dist * total_frames)) for d in dists]
        diff = total_frames - sum(per)
        for i in range(abs(diff)):
            per[i % len(per)] += 1 if diff > 0 else -1
        cum = []
        acc = 0
        for p in per:
            acc += p
            cum.append(acc)
        return per, cum

    @staticmethod
    def _get_pos(segs, alloc, cum, path_frame):
        for i, c in enumerate(cum):
            if path_frame <= c:
                prev = cum[i-1] if i > 0 else 0
                local = path_frame - prev
                span  = alloc[i]
                t = local / max(span, 1)
                t_s = t * t * (3 - 2 * t)
                s, e = segs[i]["start"], segs[i]["end"]
                return Vector((
                    s[0] + t_s * (e[0] - s[0]),
                    s[1] + t_s * (e[1] - s[1]),
                    s[2] + t_s * (e[2] - s[2]),
                ))
        s, e = segs[-1]["start"], segs[-1]["end"]
        return Vector(e)

    # ── Carga de personaje desde .blend ──────────────────────────────────────
    # Lista completa de objetos del personaje Cerdo_1 según cerdo_1.json
    ALL_OBJECTS = (
        "cerdo_1",    # EMPTY
        "pig.arma_cerdo_1",    # ARMATURE
        "pig.Body_cerdo_1",    # MESH
        "pig.Head_cerdo_1",    # MESH
        "pig.Leg-BL_cerdo_1",    # MESH
        "pig.Leg-BR_cerdo_1",    # MESH
        "pig.Leg-FL_cerdo_1",    # MESH
        "pig.Leg-FR_cerdo_1",    # MESH
    )

    def _load_character(self, context, blend_path):
        """
        Carga (append) todos los objetos de Cerdo_1 desde blend_path.
        Robusto frente a objetos ya existentes, sufijos .001,
        contexto EDIT/POSE, y objetos desvinculados de colecciones.
        """
        print(f"  _load_character: iniciando — mode={context.mode!r}, blend={blend_path!r}")
        wanted = set(self.ALL_OBJECTS)

        # --- Asegurar OBJECT mode ---
        try:
            if context.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
        except Exception as e:
            print(f"  _load_character: advertencia modo: {e}")

        try:
            bpy.ops.object.select_all(action="DESELECT")
        except Exception:
            pass

        # --- PASO 1: cuáles ya existen en bpy.data ---
        already = {n for n in wanted if bpy.data.objects.get(n) is not None}
        need    = wanted - already

        # --- PASO 2: append solo los que faltan ---
        if need:
            try:
                with bpy.data.libraries.load(blend_path, link=False) as (src, dst):
                    available = [n for n in src.objects if n in need]
                    if not available:
                        # fallback: traer todo y filtrar después
                        available = src.objects[:]
                    dst.objects = available
            except Exception as e:
                self.report({"ERROR"}, f"Error al cargar .blend: {e}")
                return False

            # Renombrar objetos que Blender creó con sufijo .001
            for expected, expected_type in [
                ("cerdo_1", "EMPTY"),
                ("pig.arma_cerdo_1", "ARMATURE"),
                ("pig.Body_cerdo_1", "MESH"),
                ("pig.Head_cerdo_1", "MESH"),
                ("pig.Leg-BL_cerdo_1", "MESH"),
                ("pig.Leg-BR_cerdo_1", "MESH"),
                ("pig.Leg-FL_cerdo_1", "MESH"),
                ("pig.Leg-FR_cerdo_1", "MESH"),
            ]:
                if bpy.data.objects.get(expected) is None:
                    for candidate in bpy.data.objects:
                        if (candidate.name.startswith(expected + ".") and
                                candidate.type == expected_type):
                            candidate.name = expected
                            print(f"  _load_character: renombrado '{candidate.name}' → '{expected}'")
                            break

        # --- PASO 3: vincular TODOS a la colección raíz de la escena ---
        col = context.scene.collection
        scene_names = {o.name for o in context.view_layer.objects}

        for name in self.ALL_OBJECTS:
            obj = bpy.data.objects.get(name)
            if obj is None:
                continue
            if name not in scene_names:
                # Desvincular de colecciones huérfanas
                for other_col in list(bpy.data.collections):
                    if obj.name in [o.name for o in other_col.objects]:
                        try:
                            other_col.objects.unlink(obj)
                        except Exception:
                            pass
                try:
                    col.objects.link(obj)
                    print(f"  _load_character: vinculado '{name}' a escena")
                except RuntimeError:
                    pass  # ya estaba

        context.view_layer.update()

        # --- PASO 4: reparar jerarquía según cerdo_1.json ---
        root = bpy.data.objects.get("cerdo_1")
        arm  = bpy.data.objects.get("pig.arma_cerdo_1")

        # Armature → cerdo_1
        if root and arm and arm.parent != root:
            arm.parent = root
            arm.matrix_parent_inverse.identity()

        # Meshes _cerdo_1 → cerdo_1 (hijos directos del empty, según json)
        mesh_children_of_root = [
            "pig.Body_cerdo_1", "pig.Head_cerdo_1", "pig.Leg-BL_cerdo_1", "pig.Leg-BR_cerdo_1", "pig.Leg-FL_cerdo_1", "pig.Leg-FR_cerdo_1"
        ]
        for mname in mesh_children_of_root:
            obj = bpy.data.objects.get(mname)
            if obj and root and obj.parent != root:
                obj.parent = root
                obj.matrix_parent_inverse.identity()

        # Accesorios → Armature (hijos del armature, según json)
        for aname in ("wooden_axe", "wooden_pickaxe", "stone_axe"):
            obj = bpy.data.objects.get(aname)
            if obj and arm and obj.parent != arm:
                obj.parent = arm
                obj.matrix_parent_inverse.identity()

        # --- PASO 5: asegurar visibilidad de todos ---
        for name in self.ALL_OBJECTS:
            obj = bpy.data.objects.get(name)
            if obj:
                obj.hide_viewport = False
                obj.hide_render   = False

        root_ok = bpy.data.objects.get("cerdo_1") is not None
        print(f"  _load_character: {'OK' if root_ok else 'ERROR — cerdo_1 no encontrado'}")

        # ── Sincronizar armature_name en cerdo_1_st para que Paso 3 lo detecte ──
        arm_loaded = bpy.data.objects.get(self.ARM_NAME)
        if arm_loaded and arm_loaded.type == "ARMATURE":
            try:
                context.scene.cerdo_1_st.armature_name = arm_loaded.name
                print(f"  _load_character: cerdo_1_st.armature_name = '{arm_loaded.name}'")
            except Exception as e:
                print(f"  _load_character: no se pudo setear armature_name: {e}")

        return root_ok

    # ── Modo 1 coordenada: idle ───────────────────────────────────────────────
    def _execute_idle(self, context, pc, pt):
        root_empty = bpy.data.objects.get(self.ROOT_NAME)
        if root_empty is None or root_empty.type != "EMPTY":
            blend_path = bpy.path.abspath(pc.blend_filepath) if pc.blend_filepath else ""
            if not blend_path or not os.path.isfile(blend_path):
                try:
                    st = context.scene.cerdo_1_st
                    hp = bpy.path.abspath(st.historia_json) if hasattr(st, 'historia_json') else ""
                    if os.path.isfile(hp):
                        import json as _j
                        blend_path = _j.load(open(hp, "r", encoding="utf-8")).get(
                            "configuracion", {}).get("archivo_blend", "")
                        if blend_path: blend_path = bpy.path.abspath(blend_path)
                except Exception:
                    pass
            if not blend_path or not os.path.isfile(blend_path):
                self.report({"ERROR"}, f"No se encontro '{self.ROOT_NAME}'. Selecciona el .blend.")
                return {"CANCELLED"}
            if not self._load_character(context, blend_path):
                self.report({"ERROR"}, "No se pudo cargar el personaje.")
                return {"CANCELLED"}

        root_empty = bpy.data.objects.get(self.ROOT_NAME)
        arm_obj    = bpy.data.objects.get(self.ARM_NAME)
        if not arm_obj:
            self.report({"ERROR"}, f"No se encontro armature '{self.ARM_NAME}'.")
            return {"CANCELLED"}

        # Sincronizar armature_name en cerdo_1_st (por si el personaje ya estaba en escena)
        try:
            if not context.scene.cerdo_1_st.armature_name:
                context.scene.cerdo_1_st.armature_name = arm_obj.name
        except Exception:
            pass

        pb = arm_obj.pose.bones
        bone_names = [
            'Body_cerdo_1', 'Body:Bend_cerdo_1', 'Body:Bend_cerdo_1', 'Body:Bend_cerdo_1',
            'Head_cerdo_1', 'Head_cerdo_1',
            'Leg:FR_cerdo_1', 'Leg:FR:Bend_cerdo_1',
            'Leg:FL_cerdo_1',  'Leg:FL:Bend_cerdo_1',
            'Leg:BR_cerdo_1', 'Leg:BR:Bend_cerdo_1',
            'Leg:BL_cerdo_1',  'Leg:BL:Bend_cerdo_1',
        ]
        bones = {}
        for bn in bone_names:
            b = pb.get(bn)
            if b is not None:
                bones[bn] = b

        bpy.context.view_layer.objects.active = arm_obj
        if bpy.context.mode != "POSE":
            bpy.ops.object.mode_set(mode="POSE")
        for b in bones.values():
            b.rotation_mode = "XYZ"
        root_empty.rotation_mode = "XYZ"

        ROOT_ACT = "_cerdo_1_preview_root"
        ARM_ACT  = "_cerdo_1_preview_arm"
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

        pos_x, pos_y, pos_z = pt.coords[0], pt.coords[1], pt.coords[2]
        rot_z  = math.radians(pc.root_rot_z)
        rot_x  = math.radians(pc.root_rot_x)
        rot_y  = math.radians(pc.root_rot_y)

        start_frame = pc.frame_inicio
        end_frame   = max(pc.frame_fin_manual, start_frame + 1)
        fpb         = max(1, pc.frames_por_bloque) if pc.frames_por_bloque > 0 else 24

        for frame in range(start_frame, end_frame + 1):
            bpy.context.scene.frame_set(frame)
            root_empty.location       = (pos_x, pos_y, pos_z)
            root_empty.rotation_euler = (rot_x, rot_y, rot_z)
            self._kf(root_empty, frame)
            self._bones_caminar(bones, frame, 0, fpb)

        for act in (root_act, arm_act):
            for fc in get_fcurves(act):
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"

        context.scene.frame_start = start_frame
        context.scene.frame_end   = end_frame
        pc.anim_frame_fin         = end_frame
        context.scene.frame_set(start_frame)
        for _name in self.ALL_OBJECTS:
            _obj = bpy.data.objects.get(_name)
            if _obj:
                _obj.hide_viewport = False
                _obj.hide_render   = False
        bpy.ops.screen.animation_play()
        self.report({"INFO"}, f"Idle: frames {start_frame}→{end_frame}")
        return {"FINISHED"}

    # ── Execute principal ────────────────────────────────────────────────────
    def invoke(self, context, event):
        """Garantiza contexto OBJECT antes de ejecutar, sin importar el modo actual."""
        pc = context.scene.cerdo_1_path

        # 1. Detener grabacion si estaba activa (antes de cambiar modo)
        if pc.recording_active:
            pc.recording_active = False
            _maybe_remove_draw_handler(pc)
            for area in context.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()

        # 2. Salir de cualquier modo especial a OBJECT mode (hasta 3 intentos)
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

    def _cleanup_preview_torches(self, context):
        """NUEVO (Kebyn, pedido de Kebyn): borra las antorchas importadas por
        una corrida ANTERIOR de 'Reproducir recorrido', antes de generar la
        nueva -- sin esto, cada click de Play volveria a importar
        antorcha_1.blend y renombrarla con un sufijo nuevo (antorcha_2,
        antorcha_3...), acumulando copias en el Outliner en vez de
        reemplazar la anterior. La lista de nombres importados en la
        corrida previa se guarda como JSON en la custom property
        '_preview_torch_objects' del Empty 'cerdo_1' (ver el final de este
        mismo execute()).

        NUEVO (Kebyn, 2026-08-22): '_preview_torch_objects' es generico --
        tambien guarda los nombres de las mesas de crafteo (mesa_de_crafteo_1,
        mesa_de_crafteo_2...) importadas por "colocar_mesa_de_crafteo", asi
        que esta misma limpieza las borra a ellas tambien antes de la
        proxima corrida, sin necesitar una lista/propiedad separada."""
        root = bpy.data.objects.get(self.ROOT_NAME)
        if root is None:
            return
        raw = root.get("_preview_torch_objects")
        if not raw:
            return
        try:
            import json as _json_cleanup
            names = _json_cleanup.loads(raw)
        except Exception:
            names = []
        for name in names:
            obj = bpy.data.objects.get(name)
            if obj is None:
                continue
            for child in list(obj.children_recursive):
                _mesh = child.data if child.type == "MESH" else None
                bpy.data.objects.remove(child, do_unlink=True)
                if _mesh and _mesh.users == 0:
                    bpy.data.meshes.remove(_mesh, do_unlink=True)
            _mesh0 = obj.data if obj.type == "MESH" else None
            bpy.data.objects.remove(obj, do_unlink=True)
            if _mesh0 and _mesh0.users == 0:
                bpy.data.meshes.remove(_mesh0, do_unlink=True)
        # Limpiar colecciones de bloques dinamicos que hayan quedado vacias
        # (antorcha_N y, NUEVO Kebyn 2026-08-22, mesa_de_crafteo_N -- mismo
        # mecanismo de renombrado secuencial para ambos bloques dinamicos)
        for coll in list(bpy.data.collections):
            if (coll.name.startswith("antorcha") or coll.name.startswith("mesa_de_crafteo")) \
                    and len(coll.objects) == 0 and coll.users == 0:
                bpy.data.collections.remove(coll)
        try:
            del root["_preview_torch_objects"]
        except Exception:
            pass

    def execute(self, context):
        pc  = context.scene.cerdo_1_path
        pts = list(pc.path_points)

        if pc.recording_active:
            pc.recording_active = False
            _maybe_remove_draw_handler(pc)

        if len(pts) == 1 and not is_woodcut(pts[0].tipo_segmento):
            return self._execute_idle(context, pc, pts[0])
        if len(pts) < 1:
            self.report({"WARNING"}, "Agrega al menos 1 punto"); return {"CANCELLED"}

        self._cleanup_preview_torches(context)

        root_empty = bpy.data.objects.get(self.ROOT_NAME)
        if root_empty is None or root_empty.type != "EMPTY":
            blend_path = bpy.path.abspath(pc.blend_filepath) if pc.blend_filepath else ""
            if not blend_path or not os.path.isfile(blend_path):
                try:
                    st = context.scene.cerdo_1_st
                    hp = bpy.path.abspath(st.historia_json) if hasattr(st, 'historia_json') else ""
                    if os.path.isfile(hp):
                        import json as _j
                        blend_path = _j.load(open(hp, "r", encoding="utf-8")).get(
                            "configuracion", {}).get("archivo_blend", "")
                        if blend_path: blend_path = bpy.path.abspath(blend_path)
                except Exception: pass
            if not blend_path or not os.path.isfile(blend_path):
                self.report({"ERROR"}, f"No se encontro '{self.ROOT_NAME}'. Selecciona el .blend.")
                return {"CANCELLED"}
            if not self._load_character(context, blend_path):
                self.report({"ERROR"}, "No se pudo cargar el personaje."); return {"CANCELLED"}

        root_empty = bpy.data.objects.get(self.ROOT_NAME)
        arm_obj    = bpy.data.objects.get(self.ARM_NAME)
        if not arm_obj:
            self.report({"ERROR"}, f"No se encontro armature '{self.ARM_NAME}'."); return {"CANCELLED"}

        # Sincronizar armature_name en cerdo_1_st (por si el personaje ya estaba en escena)
        try:
            if not context.scene.cerdo_1_st.armature_name:
                context.scene.cerdo_1_st.armature_name = arm_obj.name
        except Exception:
            pass

        # Limpiar acciones y NLA tracks del preview anterior
        bpy.context.view_layer.objects.active = arm_obj
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        arm_obj.location       = (0.0, 0.0, 0.0)
        arm_obj.rotation_euler = (0.0, 0.0, 0.0)
        arm_obj.scale          = (1.0, 1.0, 1.0)
        root_empty.location       = (0.0, 0.0, 0.0)
        root_empty.rotation_euler = (0.0, 0.0, 0.0)

        for obj in (root_empty, arm_obj):
            if not obj.animation_data:
                obj.animation_data_create()
            # Eliminar todos los NLA tracks del preview anterior
            tracks_to_remove = list(obj.animation_data.nla_tracks)
            for t in tracks_to_remove:
                obj.animation_data.nla_tracks.remove(t)
            # Limpiar accion activa
            obj.animation_data.action = None

        # EYES_DATA se reproduce mediante acciones propias de cada malla y de
        # su datablock de shape keys. Retirar las pistas de slots anteriores
        # evita superponer previews al pulsar el boton varias veces.
        for eye_name in ("ojo_izquierdo_cerdo_1", "ojo_derecho_cerdo_1"):
            eye = bpy.data.objects.get(eye_name)
            if not eye:
                continue
            animated_ids = [eye]
            if getattr(eye.data, "shape_keys", None):
                animated_ids.append(eye.data.shape_keys)
            for animated_id in animated_ids:
                anim_data = animated_id.animation_data
                if not anim_data:
                    continue
                for track in list(anim_data.nla_tracks):
                    if track.name.startswith("Slot_") and "_eye_" in track.name:
                        anim_data.nla_tracks.remove(track)
                active = anim_data.action
                if active and active.name.startswith("slot_") and "_eye_" in active.name:
                    anim_data.action = None
            # Quitar residuos de visibilidad/expresion que una reproduccion
            # anterior pudiera haber dejado como valor base fuera de sus strips.
            eye.hide_viewport = False
            eye.hide_render = False
            if getattr(eye.data, "shape_keys", None):
                for key in eye.data.shape_keys.key_blocks:
                    key.value = 0.0

        from .woodcut_animation import clear_woodcut_preview
        clear_woodcut_preview(root_empty)
        root_rot_z_deg = pc.root_rot_z
        root_rot       = (pc.root_rot_x, pc.root_rot_y, pc.root_rot_z)

        # ── Generar y ejecutar los mismos slots que ExportSlots, en memoria ──
        # Esto garantiza que el preview es identico byte-a-byte a los .py exportados.
        gen = self._get_gen()
        from datetime import date as _date
        today = _date.today().isoformat()

        # PASO OPCIONAL (Kebyn, 2026-08-02): expande los puntos insertando un
        # duplicado detras de cada punto marcado como "parada" (pt.tipo_segmento == PARADA).
        # Si ningun punto esta marcado, expanded_pts == pts y el comportamiento
        # es identico al de siempre (solo caminar/saltos).
        expanded_pts, parada_frames_marcadas, anim_files_marcadas, rot_paradas_marcadas = _expand_points_with_paradas(pts)

        key_points = [
            {"index": i + 1,
             "coordinates": {"x": round(pt.coords[0], 4),
                             "y": round(pt.coords[1], 4),
                             "z": round(pt.coords[2], 4)},
             "texture":    pt.texture or "grass_block_top",
             "face_index": pt.face_index if pt.face_index else str(i + 1),
             # NUEVO (Kebyn, 2026-08-21): override "colocar_antorcha" —
             # ver detect_movement_type() en generate_slots_cerdo_1.py.
             "tipo_segmento": getattr(pt, "tipo_segmento", "AUTO"),
             # NUEVO (Kebyn, "crear pared NxN bloques"): viajan aca para
             # que generate_crear_pared_nxn() (generate_slots_cerdo_1.py)
             # los lea de points[0] igual que lee "coordinates"/
             # "tipo_segmento" -- ver ese generador.
             "pared_bloque_blend_path": getattr(pt, "pared_bloque_blend_path", ""),
             "pared_filas": getattr(pt, "pared_filas", 2),
             "pared_columnas": getattr(pt, "pared_columnas", 2),
             # NUEVO (Kebyn, "elegir cuantos frames dura toda la
             # animacion de crear pared"): 0 = automatico -- ver
             # resolve_pared_nxn_timing() (generate_slots_cerdo_1.py).
             "pared_total_frames": getattr(pt, "pared_total_frames", 0),
             # NUEVO (Kebyn, 2026-08-23 tris): marca el punto duplicado de
             # una parada -- ver fix de "caminar fantasma" en
             # detect_movement_type() (generate_slots_cerdo_1.py).
             "es_parada_dup": isinstance(pt, _StopPointStub)}
            for i, pt in enumerate(expanded_pts)
        ]
        key_points = _ajustar_por_cuerpo(key_points)   # bloques de 1 m3 con cuerpo largo

        gen_segments  = gen.group_segments(key_points)
        sync_paradas_frames(pc)
        sync_walk_styles(pc)
        sync_paradas_frames_from_segments(context)
        start_frame   = pc.frame_inicio
        current_frame = start_frame
        slot_index    = pc.slot_inicio
        parada_idx    = 0
        caminar_idx   = 0
        _preview_torch_names = []
        # FIX (Kebyn, 2026-07-13): antes root_rot quedaba fijo en pc.root_rot_z
        # (el valor estatico del panel, ej. -90) durante TODO el recorrido, para
        # los 4 tipos de segmento por igual. Un heading real solo se calculaba
        # DENTRO de generate_caminar (sus propios sub-tramos internos); saltos y
        # paradas nunca heredaban el heading del ultimo tramo real de caminata/
        # curva -- por eso el objeto "cerdo_1" se veia con la misma rotacion Z
        # estatica sin importar el tramo. prev_rz guarda el ultimo heading real
        # (grados) visto en un tramo con desplazamiento propio, y se pasa como
        # Z de root_rot a saltar_subir/saltar_bajar/parada en vez del estatico.
        prev_rz = root_rot[2]

        # NUEVO (Kebyn, transiciones entre tramos): guardan el tipo y el
        # frame final del tramo anterior para poder suavizar el corte
        # cuando el tipo CAMBIA de un tramo al siguiente -- ver el
        # llamado a _suavizar_borde_segmentos() mas abajo.
        _prev_move_type = None
        _prev_end_frame = None

        for gseg in gen_segments:
            move_type = gseg["type"]
            points    = gseg["points"]

            if len(points) >= 2:
                _p0 = points[0]["coordinates"]
                _p1 = points[-1]["coordinates"]
                _da = gen._compute_direction_angle(_p0, _p1)
            else:
                _da = None
            _cur_rot = (root_rot[0], root_rot[1], prev_rz)

            if is_woodcut(move_type):
                code, end_frame = gen.generate_cortar_madera(slot_index,current_frame,points,today,_cur_rot,move_type)
            elif move_type == 'saltar_horizontal':
                code,end_frame=gen.generate_saltar_horizontal(slot_index,current_frame,points,today,_cur_rot,
                    fps=context.scene.render.fps/context.scene.render.fps_base)
                fname=f"slot_{slot_index:03d}_cerdo_1_saltar_horizontal.py"
            elif move_type == "saltar_subir":
                code, end_frame = gen.generate_saltar_subir(
                    slot_index, current_frame, points, today, _cur_rot, fps=context.scene.render.fps/context.scene.render.fps_base)
            elif move_type == "saltar_bajar":
                code, end_frame = gen.generate_saltar_bajar(
                    slot_index, current_frame, points, today, _cur_rot, fps=context.scene.render.fps/context.scene.render.fps_base)
            elif move_type == "colocar_antorcha":
                # ACTUALIZADO (pedido de Kebyn): antes esta rama SOLO
                # generaba la pose (agacharse/plantar) y la importacion real
                # de la antorcha quedaba diferida al Paso 3 + CONCATENAR
                # (sistema de Lanzar/Recoger, seg.throws). Ahora la
                # importacion tambien ocurre ACA, en "Reproducir recorrido"
                # (Paso 2) -- ver el bloque "if move_type == 'colocar_antorcha'"
                # justo despues de ejecutar execute_animation() mas abajo.
                #
                # NUEVO (Kebyn, sincronizacion de extremidades): se le pasa
                # walk_style_next -- el MISMO estilo que va a usar el tramo
                # "caminar" que group_segments() inyecta automaticamente
                # justo despues de este (mismos 2 puntos, ver
                # gen.group_segments()) -- para que la cola de transicion
                # del final de colocar_antorcha (ver
                # generate_colocar_antorcha()/_build_colocar_antorcha_keyframes()
                # en generate_slots_cerdo_1.py) termine exactamente en la
                # pose que ese tramo caminar va a fijar en su primer frame.
                # caminar_idx todavia NO se incremento para ese tramo (eso
                # pasa en la rama "else" de mas abajo) asi que aca apunta al
                # indice correcto.
                _walk_style_next = (pc.walk_styles[caminar_idx].style
                                     if caminar_idx < len(pc.walk_styles) else pc.walk_style)
                code, end_frame = gen.generate_colocar_antorcha(
                    slot_index, current_frame, points, today, _cur_rot,
                    walk_style_next=_walk_style_next)
            elif move_type == "golpe_estomago_1":
                # NUEVO (Kebyn): misma arquitectura que "colocar_antorcha"
                # de arriba, pero sin importar ningun objeto -- ver
                # generate_golpe_estomago_1() (generate_slots_cerdo_1.py).
                code, end_frame = gen.generate_golpe_estomago_1(
                    slot_index, current_frame, points, today, _cur_rot)
            elif move_type == "levantarse_1":
                # NUEVO (Kebyn): misma arquitectura que "golpe_estomago_1"
                # de arriba -- ver generate_levantarse_1()
                # (generate_slots_cerdo_1.py).
                code, end_frame = gen.generate_levantarse_1(
                    slot_index, current_frame, points, today, _cur_rot)
            elif move_type == "levantarse_2":
                # NUEVO (Kebyn): segunda variante de "levantarse_1" de
                # arriba, misma arquitectura -- ver generate_levantarse_2()
                # (generate_slots_cerdo_1.py).
                code, end_frame = gen.generate_levantarse_2(
                    slot_index, current_frame, points, today, _cur_rot)
            elif move_type == "arrodillarse_1":
                # NUEVO (Kebyn): misma arquitectura que "levantarse_1"/
                # "levantarse_2" de arriba -- ver generate_arrodillarse_1()
                # (generate_slots_cerdo_1.py).
                code, end_frame = gen.generate_arrodillarse_1(
                    slot_index, current_frame, points, today, _cur_rot)
            elif move_type == "conversar_1":
                # NUEVO (Kebyn): misma arquitectura que "arrodillarse_1"/
                # "levantarse_1"/"levantarse_2" de arriba -- ver
                # generate_conversar_1() (generate_slots_cerdo_1.py).
                code, end_frame = gen.generate_conversar_1(
                    slot_index, current_frame, points, today, _cur_rot)
            elif move_type == "resbalarse_1":
                # NUEVO (Kebyn): misma arquitectura que "arrodillarse_1"/
                # "levantarse_1"/"levantarse_2" de arriba -- ver
                # generate_resbalarse_1() (generate_slots_cerdo_1.py).
                code, end_frame = gen.generate_resbalarse_1(
                    slot_index, current_frame, points, today, _cur_rot)
            elif move_type == "colocar_mesa_de_crafteo":
                # NUEVO (Kebyn, 2026-08-22): misma arquitectura EXACTA que
                # "colocar_antorcha" de arriba, ver
                # generate_colocar_mesa_crafteo() (generate_slots_cerdo_1.py)
                # -- misma sincronizacion de walk_style_next con el tramo
                # "caminar" fusionado que group_segments() inyecta justo
                # despues.
                _walk_style_next = (pc.walk_styles[caminar_idx].style
                                     if caminar_idx < len(pc.walk_styles) else pc.walk_style)
                code, end_frame = gen.generate_colocar_mesa_crafteo(
                    slot_index, current_frame, points, today, _cur_rot,
                    walk_style_next=_walk_style_next)
            elif move_type == "crear_pared_nxn":
                # NUEVO (Kebyn, "crear pared NxN bloques"): misma
                # arquitectura EXACTA que "colocar_mesa_de_crafteo" de
                # arriba, ver generate_crear_pared_nxn()
                # (generate_slots_cerdo_1.py).
                _walk_style_next = (pc.walk_styles[caminar_idx].style
                                     if caminar_idx < len(pc.walk_styles) else pc.walk_style)
                code, end_frame = gen.generate_crear_pared_nxn(
                    slot_index, current_frame, points, today, _cur_rot,
                    walk_style_next=_walk_style_next)
            elif move_type == "parada":
                # CORREGIDO (Kebyn, 2026-07-11 v2): saltar por completo la
                # generacion de este slot (sin ningun keyframe) dejaba el
                # rango de la parada sin ninguna accion/NLA que lo cubra.
                # Blender NO limpia los pose bones solo porque nada los este
                # animando ahi -- conservan el ULTIMO valor evaluado del
                # segmento anterior (caminar a medio paso), que se ve como
                # una animacion "solapada" bloqueando el canvas. Por eso SI
                # se debe generar el slot de parada (gen.generate_parada):
                # este resetea los bones a su pose de rest y deja el root
                # inmovil, dando un canvas realmente en blanco listo para que
                # el usuario inyecte sus propias poses -- eso es lo que
                # significa "no debe reproducirse nada" en la practica.
                if parada_idx < len(parada_frames_marcadas):
                    # Parada marcada por el usuario en el Paso 1.5 (opcional)
                    frames_esta_parada = parada_frames_marcadas[parada_idx]
                elif parada_idx < len(pc.paradas_frames):
                    frames_esta_parada = pc.paradas_frames[parada_idx].frames
                else:
                    frames_esta_parada = pc.frames_parada
                # NUEVO (Kebyn, 2026-09-13): animacion .py importada para
                # ESTE punto de parada especifico (si el usuario asocio
                # una via el boton "Importar animacion (.py)" del panel)
                # -- ver anim_files_marcadas / CERDO_1PR_OT_ImportParadaAnim.
                anim_file_esta_parada = (
                    anim_files_marcadas[parada_idx]
                    if parada_idx < len(anim_files_marcadas) else ""
                ) or None
                # NUEVO (Kebyn, 2026-09-13): orientacion guardada a mano
                # para ESTE punto de parada (ver
                # CERDO_1PathPoint.parada_rot_saved / CERDO_1PR_OT_SaveParadaRot).
                # Si esta activa, reemplaza el heading automatico (prev_rz)
                # tanto para ESTA parada como para el resto del recorrido
                # de aca en adelante -- hasta el proximo tramo con
                # desplazamiento real (que recalcula su propio heading), o
                # hasta que se vuelva a editar este punto.
                if parada_idx < len(rot_paradas_marcadas):
                    _rot_saved, _rot_deg = rot_paradas_marcadas[parada_idx]
                    if _rot_saved:
                        prev_rz = _rot_deg
                        _cur_rot = (root_rot[0], root_rot[1], prev_rz)
                code, end_frame = gen.generate_parada(
                    slot_index, current_frame, points, today, _cur_rot,
                    frames_parada=frames_esta_parada,
                    anim_file_path=anim_file_esta_parada)
                parada_idx += 1
            else:
                walk_style_actual = (pc.walk_styles[caminar_idx].style
                                      if caminar_idx < len(pc.walk_styles) else pc.walk_style)
                code, end_frame = gen.generate_caminar(
                    slot_index, current_frame, points, today, _cur_rot,
                    walk_style=walk_style_actual)
                caminar_idx += 1

            if code is not None:
                # Ejecutar el codigo del slot en memoria — identico al .py exportado
                import math as _math_mod
                import sys as _sys_mod
                # Inyectar bpy en sys.modules para que "import bpy" dentro del slot funcione
                _bpy_already = "bpy" in _sys_mod.modules
                if not _bpy_already:
                    _sys_mod.modules["bpy"] = bpy
                slot_ns = {
                    "__builtins__": __builtins__,
                    "bpy":  bpy,
                    "math": _math_mod,
                }
                try:
                    exec(compile(code, f"<slot_{slot_index:03d}_preview>", "exec"), slot_ns)
                except Exception as _exec_err:
                    print(f"[Cerdo_1 preview] ERROR compilando slot {slot_index}: {_exec_err}")
                    import traceback; traceback.print_exc()
                    self.report({"ERROR"}, f"Error en slot {slot_index}: {_exec_err}")
                    return {"CANCELLED"}

                if "execute_animation" in slot_ns:
                    try:
                        slot_ns["execute_animation"](None)
                    except Exception as _run_err:
                        print(f"[Cerdo_1 preview] ERROR ejecutando slot {slot_index}: {_run_err}")
                        import traceback; traceback.print_exc()
                        self.report({"ERROR"}, f"Error ejecutando slot {slot_index}: {_run_err}")
                        return {"CANCELLED"}
                else:
                    print(f"[Cerdo_1 preview] ADVERTENCIA: slot {slot_index} no tiene execute_animation")

                # NUEVO (pedido de Kebyn): a diferencia de saltar_subir/
                # saltar_bajar/caminar, el tramo "colocar_antorcha" tambien
                # importa y planta la antorcha ACA MISMO, en "Reproducir
                # recorrido" (Paso 2) -- ya no hace falta llegar al Paso 3
                # (Dividir segmentos) ni a CONCATENAR para verla. Usa el
                # mismo mecanismo de bloques dinamicos que ya usaba
                # CONCATENAR (import_bloque_dinamico_full(), renombrado
                # secuencial antorcha_1/antorcha_2/... con
                # remplazar_sufijo.py) leyendo TORCH_TARGET_COORDS/
                # TORCH_SOURCE que generate_colocar_antorcha() deja en el
                # slot ejecutado.
                if move_type == "colocar_antorcha":
                    try:
                        _torch_coords = slot_ns.get("TORCH_TARGET_COORDS")
                        _torch_source = slot_ns.get("TORCH_SOURCE")
                        # ACTUALIZADO (Kebyn, 2026-08-21): antes aparecia
                        # apenas empezaba el tramo (current_frame). Ahora
                        # debe quedar oculta hasta el frame EXACTO en que
                        # el cuerpo esta en la pose de
                        # inclinado_colocando_antorcha.json (ver
                        # TORCH_APPEAR_FRAME en generate_colocar_antorcha());
                        # fallback a current_frame solo si el slot no lo
                        # define (compatibilidad con slots viejos).
                        _torch_appear_frame = slot_ns.get("TORCH_APPEAR_FRAME", current_frame)
                        if _torch_coords and _torch_source:
                            from . import object_import_utils as _oiu_prev_path
                            _st_torch = context.scene.cerdo_1_st
                            _anchor = (bpy.path.abspath(_st_torch.anim_dir)
                                       if getattr(_st_torch, "anim_dir", None)
                                       else bpy.path.abspath("//"))
                            _bloques_dir = _oiu_prev_path.get_bloques_dinamicos_path_from_anchor(
                                _anchor, 4)
                            _blend_abs = os.path.join(
                                _bloques_dir, _torch_source.get("blend_filename", "antorcha_1.blend"))
                            _root_anchor, _mapa_renom = _oiu_prev_path.import_bloque_dinamico_full(
                                _blend_abs,
                                target_location=(_torch_coords["x"], _torch_coords["y"], _torch_coords["z"]),
                                base_name=_torch_source.get("object_name") or None,
                            )
                            if _root_anchor is None:
                                print(f"[Cerdo_1 preview] ADVERTENCIA: no se pudo importar "
                                      f"'{_torch_source.get('blend_filename')}' desde {_blend_abs}")
                                self.report({"WARNING"},
                                    f"No se pudo importar la antorcha (slot {slot_index}) -- "
                                    f"revisa que exista {_blend_abs}")
                            else:
                                _torch_objs = [_root_anchor] + list(_root_anchor.children_recursive)
                                for _tobj in _torch_objs:
                                    _oiu_prev_path.hide_until_frame(_tobj, appear_frame=_torch_appear_frame)
                                    _preview_torch_names.append(_tobj.name)
                    except Exception as _torch_err:
                        print(f"[Cerdo_1 preview] ERROR importando antorcha (slot {slot_index}): {_torch_err}")
                        import traceback; traceback.print_exc()
                        self.report({"WARNING"}, f"Error importando antorcha: {_torch_err}")

                # NUEVO (Kebyn, 2026-08-22): "colocar_mesa_de_crafteo"
                # importa y coloca la mesa de crafteo ACA MISMO, igual que
                # "colocar_antorcha" hace con la antorcha justo arriba --
                # mismo mecanismo de bloques dinamicos
                # (import_bloque_dinamico_full(), renombrado secuencial
                # mesa_de_crafteo_1/mesa_de_crafteo_2/... con
                # aplicar_sufijo_numerico_anticolision()), leyendo
                # TABLE_TARGET_COORDS/TABLE_SOURCE/TABLE_APPEAR_FRAME que
                # generate_colocar_mesa_crafteo() deja en el slot ejecutado.
                if move_type == "colocar_mesa_de_crafteo":
                    try:
                        _table_coords = slot_ns.get("TABLE_TARGET_COORDS")
                        _table_source = slot_ns.get("TABLE_SOURCE")
                        _table_appear_frame = slot_ns.get("TABLE_APPEAR_FRAME", current_frame)
                        if _table_coords and _table_source:
                            from . import object_import_utils as _oiu_prev_path
                            _st_table = context.scene.cerdo_1_st
                            _anchor = (bpy.path.abspath(_st_table.anim_dir)
                                       if getattr(_st_table, "anim_dir", None)
                                       else bpy.path.abspath("//"))
                            _bloques_dir = _oiu_prev_path.get_bloques_dinamicos_path_from_anchor(
                                _anchor, 4)
                            _blend_abs = os.path.join(
                                _bloques_dir, _table_source.get("blend_filename", "mesa_de_crafteo_1.blend"))
                            _root_anchor, _mapa_renom = _oiu_prev_path.import_bloque_dinamico_full(
                                _blend_abs,
                                target_location=(_table_coords["x"], _table_coords["y"], _table_coords["z"]),
                                base_name=_table_source.get("object_name") or None,
                            )
                            if _root_anchor is None:
                                print(f"[Cerdo_1 preview] ADVERTENCIA: no se pudo importar "
                                      f"'{_table_source.get('blend_filename')}' desde {_blend_abs}")
                                self.report({"WARNING"},
                                    f"No se pudo importar la mesa de crafteo (slot {slot_index}) -- "
                                    f"revisa que exista {_blend_abs}")
                            else:
                                _table_objs = [_root_anchor] + list(_root_anchor.children_recursive)
                                for _tobj in _table_objs:
                                    _oiu_prev_path.hide_until_frame(_tobj, appear_frame=_table_appear_frame)
                                    _preview_torch_names.append(_tobj.name)
                    except Exception as _table_err:
                        print(f"[Cerdo_1 preview] ERROR importando mesa de crafteo (slot {slot_index}): {_table_err}")
                        import traceback; traceback.print_exc()
                        self.report({"WARNING"}, f"Error importando mesa de crafteo: {_table_err}")

                # NUEVO (Kebyn, "crear pared NxN bloques"): importa y
                # coloca CADA bloque de la grilla ACA MISMO, igual que
                # "colocar_mesa_de_crafteo" hace con la mesa justo arriba
                # -- mismo mecanismo de bloques dinamicos
                # (import_bloque_dinamico_full()), leyendo
                # WALL_BLOCKS/WALL_BLOCK_SOURCE que
                # generate_crear_pared_nxn() deja en el slot ejecutado:
                # una entrada por celda de la grilla Filas x Columnas, con
                # su propia coordenada y su propio appear_frame (el frame
                # exacto en el que el cuerpo esta agachado colocando ESE
                # bloque puntual). A diferencia de la antorcha/mesa, la
                # fuente NO vive en bloques_dinamicos -- es la ruta .blend
                # que Kebyn eligio a mano en el punto (Paso 1, campo
                # "Bloque .blend (1m3)"), asi que se usa tal cual (solo
                # normalizada con bpy.path.abspath).
                if move_type == "crear_pared_nxn":
                    try:
                        _wall_blocks = slot_ns.get("WALL_BLOCKS") or []
                        _wall_source = slot_ns.get("WALL_BLOCK_SOURCE") or {}
                        _wall_blend_raw = _wall_source.get("blend_path", "")
                        _wall_blend_abs = bpy.path.abspath(_wall_blend_raw) if _wall_blend_raw else ""
                        if _wall_blend_abs and os.path.isfile(_wall_blend_abs):
                            from . import object_import_utils as _oiu_prev_wall
                            for _wb in _wall_blocks:
                                _wcoords = _wb.get("coords")
                                _wappear = _wb.get("appear_frame", current_frame)
                                if not _wcoords:
                                    continue
                                _root_anchor, _mapa_renom = _oiu_prev_wall.import_bloque_dinamico_full(
                                    _wall_blend_abs,
                                    target_location=(_wcoords["x"], _wcoords["y"], _wcoords["z"]),
                                    base_name=_wall_source.get("object_name") or None,
                                )
                                if _root_anchor is None:
                                    print(f"[Cerdo_1 preview] ADVERTENCIA: no se pudo importar "
                                          f"bloque de pared desde {_wall_blend_abs}")
                                    self.report({"WARNING"},
                                        f"No se pudo importar un bloque de pared (slot {slot_index}) -- "
                                        f"revisa que exista {_wall_blend_abs}")
                                    continue
                                # FIX (fix "bloques en direcciones distintas"):
                                # import_bloque_dinamico_full() solo mueve el
                                # ancla (offset de location) -- deja la
                                # rotacion tal cual viene del .blend fuente,
                                # asi que TODOS los bloques de la pared
                                # comparten el mismo heading calculado para
                                # la grilla (WALL_BLOCKS[].rot_z) en vez de
                                # quedar cada uno con lo que sea que tenga
                                # el .blend importado.
                                _root_anchor.rotation_euler = (
                                    _root_anchor.rotation_euler.x,
                                    _root_anchor.rotation_euler.y,
                                    _wb.get("rot_z", _root_anchor.rotation_euler.z))
                                _wall_objs = [_root_anchor] + list(_root_anchor.children_recursive)
                                for _wobj in _wall_objs:
                                    _oiu_prev_wall.hide_until_frame(_wobj, appear_frame=_wappear)
                                    _preview_torch_names.append(_wobj.name)
                        elif _wall_blocks:
                            self.report({"WARNING"},
                                f"'Crear pared NxN' (slot {slot_index}): no se eligio un archivo "
                                ".blend valido de bloque -- configuralo en el punto (Paso 1)")
                    except Exception as _wall_err:
                        print(f"[Cerdo_1 preview] ERROR importando pared NxN (slot {slot_index}): {_wall_err}")
                        import traceback; traceback.print_exc()
                        self.report({"WARNING"}, f"Error importando pared NxN: {_wall_err}")

            # NUEVO (Kebyn, transiciones entre tramos): solo tiene sentido
            # suavizar el corte cuando el tramo anterior existe Y su tipo
            # es DISTINTO al de este tramo (ej. Caminar -> Parada). Entre
            # dos tramos del MISMO tipo (ej. dos "Caminar" seguidos) el
            # movimiento ya es continuo -- aplicar esto ahi rompería el
            # ciclo de marcha en vez de arreglar algo.
            if (pc.usar_transiciones and code is not None
                    and _prev_move_type is not None
                    and _prev_move_type != move_type):
                _suavizar_borde_segmentos(
                    arm_obj, root_empty, slot_index - 1, slot_index,
                    _prev_end_frame, current_frame, pc.frames_transicion)

            if code is not None:
                _prev_move_type = move_type
                _prev_end_frame = end_frame

            if len(points) >= 2:
                _da_fin = gen._compute_direction_angle(points[-2]["coordinates"], points[-1]["coordinates"])
                if _da_fin is not None:
                    _da = _da_fin
            if _da is not None:
                prev_rz = _da
            current_frame = end_frame + 1
            slot_index   += 1

        total_end = current_frame - 1

        # Guardar la lista de antorchas importadas en esta corrida, para que
        # la PROXIMA vez que se presione "Reproducir recorrido"
        # _cleanup_preview_torches() pueda borrarlas antes de re-importar
        # (ver inicio de este mismo execute()).
        if root_empty is not None:
            if _preview_torch_names:
                import json as _json_torch
                root_empty["_preview_torch_objects"] = _json_torch.dumps(_preview_torch_names)
            elif "_preview_torch_objects" in root_empty:
                del root_empty["_preview_torch_objects"]

        # ── Reinyectar poses configuradas (de "Concatenar") sobre los slots base ──
        # Si existe la custom property "_concat_arm_data" en el objeto cerdo_1,
        # significa que el usuario ejecuto "Concatenar" antes de este segundo
        # "Reproducir recorrido". Reinyectamos los keyframes de poses directamente
        # en los fcurves de los NLA tracks Slot_NNN_arm que cubren ese rango.
        import json as _json

        _cerdo_1_root_obj = bpy.data.objects.get("cerdo_1")
        _concat_arm_raw  = (_cerdo_1_root_obj.get("_concat_arm_data")  if _cerdo_1_root_obj else None)
        _concat_root_raw = (_cerdo_1_root_obj.get("_concat_root_data") if _cerdo_1_root_obj else None)

        if _concat_arm_raw:
            try:
                _concat_arm_data  = _json.loads(_concat_arm_raw)
                _concat_root_data = _json.loads(_concat_root_raw) if _concat_root_raw else {}
                _cf_start = int(_cerdo_1_root_obj.get("_concat_frame_start", start_frame))
                _cf_end   = int(_cerdo_1_root_obj.get("_concat_frame_end",   total_end))

                def _reinject_into_nla(obj, data_dict, frame_start_c, frame_end_c,
                                       skip_dp=None):
                    """Reinyecta keyframes de poses en los fcurves de los NLA strips.
                    skip_dp: conjunto de data_path a ignorar (ej: {"location"} para el root).
                    """
                    if not obj.animation_data:
                        return
                    if skip_dp is None:
                        skip_dp = set()
                    for track in obj.animation_data.nla_tracks:
                        if not track.name.startswith("Slot_"):
                            continue
                        for strip in track.strips:
                            act = strip.action
                            if act is None:
                                continue
                            s_start = int(strip.frame_start)
                            s_end   = int(strip.frame_end)
                            overlap_s = max(s_start, frame_start_c)
                            overlap_e = min(s_end,   frame_end_c)
                            if overlap_s > overlap_e:
                                continue
                            for dp_key, frames_vals in data_dict.items():
                                bracket = dp_key.rfind("[")
                                dp      = dp_key[:bracket]
                                arr_idx = int(dp_key[bracket+1:-1])
                                # Saltar canales excluidos (ej: location del root)
                                if dp in skip_dp:
                                    continue
                                fc = get_fcurves(act).find(dp, index=arr_idx)
                                if fc is None:
                                    fc = get_fcurves(act).new(dp, index=arr_idx)
                                for frame_str, val in frames_vals.items():
                                    frame_i = int(frame_str)
                                    if overlap_s <= frame_i <= overlap_e:
                                        fc.keyframe_points.insert(frame_i, val,
                                            options={"FAST", "REPLACE"})
                                if fc.keyframe_points:
                                    fc.update()

                # Para el armature: reinyectar todos los canales (bones).
                _reinject_into_nla(arm_obj, _concat_arm_data, _cf_start, _cf_end)

                # Para el root (cerdo_1 empty): reinyectar SOLO rotation_euler.
                # La location viene del recorrido (slots Slot_NNN_root) y NO debe
                # ser sobreescrita por las poses configuradas (que tienen pos=0,0,0).
                _reinject_into_nla(root_empty, _concat_root_data, _cf_start, _cf_end,
                                   skip_dp={"location"})

            except Exception as _reinj_err:
                print(f"[Cerdo_1 preview] ADVERTENCIA reinyeccion poses: {_reinj_err}")
                import traceback; traceback.print_exc()

        # ── Post-proceso: filtros organicos y oscilaciones ────────────────────
        # Estrategia: usamos bpy.ops.nla.bake para obtener una accion con todos
        # los valores reales evaluados (NLA resuelto). Luego aplicamos los filtros
        # sobre esa accion baked y la dejamos como animacion final.
        try:
            from . import operators_anim as _ops_anim
            _st  = context.scene.cerdo_1_st
            _org = _st.organic

            # Los filtros organicos y oscilaciones solo se aplican cuando ya
            # existe una configuracion de segmento concatenada (_concat_arm_data).
            # En la primera reproduccion (sin CONCATENAR previo) no se aplican.
            _cerdo_1_root = bpy.data.objects.get("cerdo_1")
            _has_concat  = bool(_cerdo_1_root and _cerdo_1_root.get("_concat_arm_data"))

            _needs_organic = _org.enabled and _has_concat
            _needs_osc     = (_has_concat and
                              hasattr(_st, "bone_oscillations") and
                              _st.bone_oscillations.enabled and
                              bool(_st.bone_oscillations.items))

            if _needs_organic or _needs_osc:
                BAKED_ACT_NAME = "_cerdo_1_organic_baked"

                # Limpiar accion baked previa si existe
                _old = bpy.data.actions.get(BAKED_ACT_NAME)
                if _old:
                    bpy.data.actions.remove(_old, do_unlink=True)

                # Seleccionar el armature y ponerlo en modo POSE para el bake
                _prev_active = context.view_layer.objects.active
                _prev_mode   = arm_obj.mode if arm_obj.mode else "OBJECT"
                context.view_layer.objects.active = arm_obj
                arm_obj.select_set(True)
                if arm_obj.mode != "POSE":
                    bpy.ops.object.mode_set(mode="POSE")

                # bpy.ops.nla.bake: bake el NLA completo a una accion nueva
                # visual_keying=True garantiza que lee los valores evaluados
                # (no los canales crudos), incluyendo constraints y NLA.
                bpy.ops.nla.bake(
                    frame_start    = start_frame,
                    frame_end      = total_end,
                    step           = 1,
                    only_selected  = False,
                    visual_keying  = True,
                    clear_constraints = False,
                    clear_parents  = False,
                    use_current_action = False,
                    clean_curves   = True,
                    bake_types     = {"POSE"},
                )

                # La accion baked queda asignada como accion activa del armature
                baked_act = arm_obj.animation_data.action
                if baked_act:
                    baked_act.name = BAKED_ACT_NAME

                # Volver al modo objeto
                bpy.ops.object.mode_set(mode="OBJECT")
                context.view_layer.objects.active = _prev_active

                if baked_act:
                    # Mutear NLA para que la accion baked sea la unica fuente
                    for _tr in arm_obj.animation_data.nla_tracks:
                        _tr.mute = True

                    # Aplicar filtros organicos sobre la accion baked
                    if _needs_organic:
                        _ops_anim._apply_organic_filters(
                            context, arm_obj,
                            start_frame, total_end,
                            _org,
                        )
                    if _needs_osc:
                        _ops_anim._apply_bone_oscillations(
                            context, arm_obj,
                            _st.bone_oscillations,
                        )

                    print(f"[Cerdo_1] Filtros organicos OK — {len(get_fcurves(baked_act))} fcurves, "
                          f"frames {start_frame}→{total_end}")
                else:
                    print("[Cerdo_1] ADVERTENCIA: bake no produjo accion activa")

        except Exception as _org_err:
            print(f"[Cerdo_1 preview] ERROR filtros organicos: {_org_err}")
            import traceback; traceback.print_exc()

        from .woodcut_animation import regenerate_woodcut_props, bake_woodcut_base
        bake_woodcut_base(context.scene, start_frame, total_end)
        regenerate_woodcut_props(context.scene, start_frame, total_end)
        context.scene.frame_start = start_frame
        context.scene.frame_end   = total_end
        pc.anim_frame_fin         = total_end
        context.scene.frame_set(start_frame)
        for _name in self.ALL_OBJECTS:
            _obj = bpy.data.objects.get(_name)
            if _obj:
                _obj.hide_viewport = False
                _obj.hide_render   = False

        # ── Guardar huella + rango total generado, para que los botones de
        # "Reproducir recorrido" de cada segmento puedan saber si pueden
        # reusar esta bake sin tener que regenerar todo de nuevo.
        try:
            _root_for_fp = bpy.data.objects.get(self.ROOT_NAME)
            if _root_for_fp:
                _root_for_fp["_last_preview_fingerprint"] = compute_recorrido_fingerprint(context)
                _root_for_fp["_last_preview_start"] = start_frame
                _root_for_fp["_last_preview_end"]   = total_end
        except Exception:
            pass

        bpy.ops.screen.animation_play()

        self.report({"INFO"},
            f"Preview: {len(pts)} pts | {len(gen_segments)} segs | "
            f"{total_end - start_frame + 1} frames")
        return {"FINISHED"}


# =============================================================================
# RESET PREVIEW
# =============================================================================

class CERDO_1PR_OT_ResetPreview(Operator):
    bl_idname  = "cerdo_1pr.reset_preview"
    bl_label   = "Reset recorrido"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_cancel(restore_frame=True)
        for obj_name, act_name in (
            ("cerdo_1",    "_cerdo_1_preview_root"),
            ("pig.arma_cerdo_1",  "_cerdo_1_preview_arm"),
            ("pig.arma_cerdo_1",  "_cerdo_1_organic_baked"),
        ):
            obj = bpy.data.objects.get(obj_name)
            if obj and obj.animation_data:
                act = bpy.data.actions.get(act_name)
                if obj.animation_data.action == act:
                    obj.animation_data.action = None
                if act:
                    bpy.data.actions.remove(act, do_unlink=True)
                for track in obj.animation_data.nla_tracks:
                    track.mute = False   # reactivar por si los filtros organicos los mutearon
                    for strip in track.strips:
                        if strip.extrapolation == "NOTHING" and strip.name.startswith("Slot_"):
                            strip.extrapolation = "HOLD_FORWARD"
                # Limpiar accion baked de filtros organicos si existe
                _baked_act = bpy.data.actions.get("_cerdo_1_organic_baked")
                if _baked_act and obj.animation_data and obj.animation_data.action == _baked_act:
                    obj.animation_data.action = None
                if _baked_act:
                    bpy.data.actions.remove(_baked_act, do_unlink=True)
        root = bpy.data.objects.get("cerdo_1")
        if root:
            root.location = (0, 0, 0); root.rotation_euler = (0, 0, 0)
            # Limpiar custom properties de poses configuradas
            for _cprop in ("_concat_arm_data", "_concat_root_data",
                           "_concat_frame_start", "_concat_frame_end"):
                if _cprop in root:
                    del root[_cprop]
        self.report({"INFO"}, "Preview reseteada")
        return {"FINISHED"}


# =============================================================================
# SET ANIM RANGE
# =============================================================================

class CERDO_1PR_OT_SetAnimRange(Operator):
    bl_idname  = "cerdo_1pr.set_anim_range"
    bl_label   = "Fijar rango de animacion"
    bl_options = {"REGISTER", "UNDO"}

    frame_fin: bpy.props.IntProperty(
        name="Frame fin de animacion",
        default=1, min=1, soft_max=99999,
    )

    def invoke(self, context, event):
        pc = context.scene.cerdo_1_path
        self.frame_fin = pc.anim_frame_fin if pc.anim_frame_fin > 0 else context.scene.frame_end
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        pc = context.scene.cerdo_1_path
        if self.frame_fin <= pc.frame_inicio:
            self.report({"ERROR"}, f"Frame fin debe ser mayor que frame inicio")
            return {"CANCELLED"}
        pc.anim_frame_fin = self.frame_fin
        self.report({"INFO"}, f"Rango animacion: {pc.frame_inicio} → {self.frame_fin}")
        return {"FINISHED"}


# =============================================================================
# EXPORT SLOTS
# =============================================================================

class CERDO_1PR_OT_ExportSlots(bpy.types.Operator):
    """Exporta los scripts de slots del recorrido de Cerdo_1."""
    bl_idname  = "cerdo_1pr.export_slots"
    bl_label   = "Exportar recorrido (slots)"
    bl_description = (
        "Genera los scripts de slots del recorrido en la carpeta de salida. "
        "Equivalente a ejecutar generate_slots_cerdo_1.py"
    )
    bl_options = {"REGISTER"}

    def execute(self, context):
        import importlib.util as _ilu

        pc    = context.scene.cerdo_1_path
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
        gen_path  = os.path.join(addon_dir, "generate_slots_cerdo_1.py")
        if not os.path.exists(gen_path):
            self.report({"ERROR"},
                f"No se encontro generate_slots_cerdo_1.py en {gen_path}.")
            return {"CANCELLED"}

        spec = _ilu.spec_from_file_location("gen_slots_cerdo_1", gen_path)
        gen  = _ilu.module_from_spec(spec)
        spec.loader.exec_module(gen)

        today         = date.today().isoformat()
        root_rot      = (pc.root_rot_x, pc.root_rot_y, pc.root_rot_z)
        slot_index    = pc.slot_inicio
        current_frame = pc.frame_inicio

        # ── 1 COORDENADA: idle ───────────────────────────────────────────────
        if n_pts == 1 and not is_woodcut(pts[0].tipo_segmento):
            pt = pts[0]
            point = {
                "index": 0,
                "coordinates": {"x": pt.coords[0], "y": pt.coords[1], "z": pt.coords[2]},
                "texture": pt.texture or "grass_block_top",
                "face_index": pt.face_index if pt.face_index else "0",
            }
            total_frames_idle = max(1, pc.frame_fin_manual - pc.frame_inicio + 1)
            if hasattr(gen, 'generate_idle'):
                code, end_frame = gen.generate_idle(
                    slot_index, current_frame, point, today, root_rot,
                    total_frames=total_frames_idle
                )
            else:
                # Fallback: idle simple sin ciclo
                end_frame = current_frame + total_frames_idle - 1
                code = f"# slot_{slot_index:03d}_cerdo_1_idle.py\n# Generado {today}\n"
            fname = f"slot_{slot_index:03d}_cerdo_1_idle.py"
            with open(os.path.join(output_dir, fname), "w", encoding="utf-8") as f:
                f.write(code)
            pc.anim_frame_fin = end_frame
            self.report({"INFO"},
                f"Exportacion OK: 1 slot idle | frames {pc.frame_inicio}→{end_frame} | {output_dir}")
            return {"FINISHED"}

        # ── RECORRIDO (>1 coordenada) ─────────────────────────────────────────
        # PASO OPCIONAL (Kebyn, 2026-08-02): expande los puntos insertando un
        # duplicado detras de cada punto marcado como "parada" (pt.tipo_segmento == PARADA).
        # Si ningun punto esta marcado, expanded_pts == pts y la exportacion es
        # identica a la de siempre (solo caminar/saltos).
        expanded_pts, parada_frames_marcadas, anim_files_marcadas, rot_paradas_marcadas = _expand_points_with_paradas(pts)

        key_points = [
            {"index": i + 1,
             "coordinates": {"x": round(pt.coords[0], 4), "y": round(pt.coords[1], 4), "z": round(pt.coords[2], 4)},
             "texture": pt.texture or "grass_block_top",
             "face_index": pt.face_index if pt.face_index else str(i + 1),
             "tipo_segmento": getattr(pt, "tipo_segmento", "AUTO"),
             # NUEVO (Kebyn, 2026-08-23 tris): ver fix de "caminar
             # fantasma" en detect_movement_type() (generate_slots_cerdo_1.py).
             "es_parada_dup": isinstance(pt, _StopPointStub)}
            for i, pt in enumerate(expanded_pts)
        ]
        key_points = _ajustar_por_cuerpo(key_points)   # bloques de 1 m3 con cuerpo largo

        segments = gen.group_segments(key_points)
        sync_paradas_frames(pc)
        sync_walk_styles(pc)
        sync_paradas_frames_from_segments(context)

        prev_rz_exp = root_rot[2]
        parada_idx  = 0
        caminar_idx = 0
        for seg in segments:
            move_type = seg["type"]
            points    = seg["points"]

            if len(points) >= 2:
                _p0 = points[0]["coordinates"]
                _p1 = points[-1]["coordinates"]
                _da = gen._compute_direction_angle(_p0, _p1)
            else:
                _da = None

            _cur_rot = (root_rot[0], root_rot[1], prev_rz_exp)

            if is_woodcut(move_type):
                code, end_frame = gen.generate_cortar_madera(slot_index,current_frame,points,today,_cur_rot,move_type)
                fname = f"slot_{slot_index:03d}_cerdo_1_{move_type}.py"
            elif move_type == 'saltar_horizontal':
                code,end_frame=gen.generate_saltar_horizontal(slot_index,current_frame,points,today,_cur_rot,
                    fps=context.scene.render.fps/context.scene.render.fps_base)
                fname=f"slot_{slot_index:03d}_cerdo_1_saltar_horizontal.py"
            elif move_type == "saltar_subir":
                code, end_frame = gen.generate_saltar_subir(
                    slot_index, current_frame, points, today, _cur_rot, fps=context.scene.render.fps/context.scene.render.fps_base)
                fname = f"slot_{slot_index:03d}_cerdo_1_saltar_subir.py"
            elif move_type == "saltar_bajar":
                code, end_frame = gen.generate_saltar_bajar(
                    slot_index, current_frame, points, today, _cur_rot, fps=context.scene.render.fps/context.scene.render.fps_base)
                fname = f"slot_{slot_index:03d}_cerdo_1_saltar_bajar.py"
            elif move_type == "colocar_antorcha":
                # NUEVO (Kebyn, sincronizacion de extremidades): mismo
                # walk_style_next que en CERDO_1PR_OT_GenerateSlots -- ver
                # comentario detallado ahi. caminar_idx todavia NO se
                # incremento para el tramo caminar sintetico que sigue, asi
                # que apunta al indice correcto.
                _walk_style_next = (pc.walk_styles[caminar_idx].style
                                     if caminar_idx < len(pc.walk_styles) else pc.walk_style)
                code, end_frame = gen.generate_colocar_antorcha(
                    slot_index, current_frame, points, today, _cur_rot,
                    walk_style_next=_walk_style_next)
                fname = f"slot_{slot_index:03d}_cerdo_1_colocar_antorcha.py"
            elif move_type == "golpe_estomago_1":
                # NUEVO (Kebyn): misma arquitectura que "colocar_antorcha"
                # de arriba, ver generate_golpe_estomago_1()
                # (generate_slots_cerdo_1.py).
                code, end_frame = gen.generate_golpe_estomago_1(
                    slot_index, current_frame, points, today, _cur_rot)
                fname = f"slot_{slot_index:03d}_cerdo_1_golpe_estomago_1.py"
            elif move_type == "levantarse_1":
                # NUEVO (Kebyn): misma arquitectura que "golpe_estomago_1"
                # de arriba, ver generate_levantarse_1()
                # (generate_slots_cerdo_1.py).
                code, end_frame = gen.generate_levantarse_1(
                    slot_index, current_frame, points, today, _cur_rot)
                fname = f"slot_{slot_index:03d}_cerdo_1_levantarse_1.py"
            elif move_type == "levantarse_2":
                # NUEVO (Kebyn): segunda variante de "levantarse_1" de
                # arriba, misma arquitectura -- ver generate_levantarse_2()
                # (generate_slots_cerdo_1.py).
                code, end_frame = gen.generate_levantarse_2(
                    slot_index, current_frame, points, today, _cur_rot)
                fname = f"slot_{slot_index:03d}_cerdo_1_levantarse_2.py"
            elif move_type == "arrodillarse_1":
                # NUEVO (Kebyn): misma arquitectura que "levantarse_1"/
                # "levantarse_2" de arriba, ver generate_arrodillarse_1()
                # (generate_slots_cerdo_1.py).
                code, end_frame = gen.generate_arrodillarse_1(
                    slot_index, current_frame, points, today, _cur_rot)
                fname = f"slot_{slot_index:03d}_cerdo_1_arrodillarse_1.py"
            elif move_type == "conversar_1":
                # NUEVO (Kebyn): misma arquitectura que "arrodillarse_1"/
                # "levantarse_1"/"levantarse_2" de arriba, ver
                # generate_conversar_1() (generate_slots_cerdo_1.py).
                code, end_frame = gen.generate_conversar_1(
                    slot_index, current_frame, points, today, _cur_rot)
                fname = f"slot_{slot_index:03d}_cerdo_1_conversar_1.py"
            elif move_type == "resbalarse_1":
                # NUEVO (Kebyn): misma arquitectura que "arrodillarse_1"/
                # "levantarse_1"/"levantarse_2" de arriba, ver
                # generate_resbalarse_1() (generate_slots_cerdo_1.py).
                code, end_frame = gen.generate_resbalarse_1(
                    slot_index, current_frame, points, today, _cur_rot)
                fname = f"slot_{slot_index:03d}_cerdo_1_resbalarse_1.py"
            elif move_type == "colocar_mesa_de_crafteo":
                # NUEVO (Kebyn, 2026-08-22): mismo walk_style_next que en
                # CERDO_1PR_OT_ReproducirRecorrido -- ver comentario
                # detallado ahi. Misma arquitectura EXACTA que
                # "colocar_antorcha", ver generate_colocar_mesa_crafteo()
                # (generate_slots_cerdo_1.py).
                _walk_style_next = (pc.walk_styles[caminar_idx].style
                                     if caminar_idx < len(pc.walk_styles) else pc.walk_style)
                code, end_frame = gen.generate_colocar_mesa_crafteo(
                    slot_index, current_frame, points, today, _cur_rot,
                    walk_style_next=_walk_style_next)
                fname = f"slot_{slot_index:03d}_cerdo_1_colocar_mesa_de_crafteo.py"
            elif move_type == "crear_pared_nxn":
                # NUEVO (Kebyn): mismo walk_style_next que
                # "colocar_mesa_de_crafteo" de arriba -- misma
                # arquitectura EXACTA, ver generate_crear_pared_nxn()
                # (generate_slots_cerdo_1.py).
                _walk_style_next = (pc.walk_styles[caminar_idx].style
                                     if caminar_idx < len(pc.walk_styles) else pc.walk_style)
                code, end_frame = gen.generate_crear_pared_nxn(
                    slot_index, current_frame, points, today, _cur_rot,
                    walk_style_next=_walk_style_next)
                fname = f"slot_{slot_index:03d}_cerdo_1_crear_pared_nxn.py"
            elif move_type == "parada":
                if parada_idx < len(parada_frames_marcadas):
                    # Parada marcada por el usuario en el Paso 1.5 (opcional)
                    frames_esta_parada = parada_frames_marcadas[parada_idx]
                elif parada_idx < len(pc.paradas_frames):
                    frames_esta_parada = pc.paradas_frames[parada_idx].frames
                else:
                    frames_esta_parada = pc.frames_parada
                # NUEVO (Kebyn, 2026-09-13): ver comentario identico en
                # CERDO_1PR_OT_PreviewPath -- misma logica, animacion .py
                # importada por punto de parada (si existe).
                anim_file_esta_parada = (
                    anim_files_marcadas[parada_idx]
                    if parada_idx < len(anim_files_marcadas) else ""
                ) or None
                # NUEVO (Kebyn, 2026-09-13): ver comentario identico en
                # CERDO_1PR_OT_PreviewPath -- misma logica, orientacion
                # guardada a mano por punto de parada (si existe), que
                # reemplaza el heading automatico (prev_rz_exp) de aca en
                # adelante.
                if parada_idx < len(rot_paradas_marcadas):
                    _rot_saved, _rot_deg = rot_paradas_marcadas[parada_idx]
                    if _rot_saved:
                        prev_rz_exp = _rot_deg
                        _cur_rot = (root_rot[0], root_rot[1], prev_rz_exp)
                code, end_frame = gen.generate_parada(
                    slot_index, current_frame, points, today, _cur_rot,
                    frames_parada=frames_esta_parada,
                    anim_file_path=anim_file_esta_parada)
                fname = f"slot_{slot_index:03d}_cerdo_1_parada.py"
                parada_idx += 1
            else:
                walk_style_actual = (pc.walk_styles[caminar_idx].style
                                      if caminar_idx < len(pc.walk_styles) else pc.walk_style)
                code, end_frame = gen.generate_caminar(
                    slot_index, current_frame, points, today, _cur_rot,
                    walk_style=walk_style_actual)
                fname = f"slot_{slot_index:03d}_cerdo_1_caminar.py"
                caminar_idx += 1

            with open(os.path.join(output_dir, fname), "w", encoding="utf-8") as f:
                f.write(code)

            if len(points) >= 2:
                _da_fin = gen._compute_direction_angle(points[-2]["coordinates"], points[-1]["coordinates"])
                if _da_fin is not None:
                    _da = _da_fin
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


# =============================================================================
# GENERA SLOTS (directo en escena, sin archivo intermedio)
# =============================================================================

class CERDO_1PR_OT_GenerateSlots(Operator):
    """Genera y ejecuta slots directamente en la escena."""
    bl_idname  = "cerdo_1pr.generate_slots"
    bl_label   = "Generar slots (InScene)"
    bl_options = {"REGISTER"}

    def execute(self, context):
        self.report({"INFO"}, "Usa 'Exportar recorrido' para generar los archivos .py")
        return {"FINISHED"}


# =============================================================================
# REGISTRO
# =============================================================================

pr_classes = (
    CERDO_1PathPoint,
    CERDO_1ParadaFrames,
    CERDO_1WalkStyleEntry,
    CERDO_1PathSettings,
    CERDO_1PR_OT_ToggleRecording,
    CERDO_1PR_OT_TogglePathViz,
    CERDO_1PR_OT_RemoveLast,
    CERDO_1PR_OT_RemovePoint,
    CERDO_1PR_OT_ImportParadaAnim,
    CERDO_1PR_OT_ClearParadaAnim,
    CERDO_1PR_OT_OpenInteractionFolder,
    CERDO_1PR_OT_RotateParadaRoot,
    CERDO_1PR_OT_SaveParadaRot,
    CERDO_1PR_OT_ClearParadaRot,
    CERDO_1PR_OT_ClearPath,
    CERDO_1PR_OT_SyncParadasFrames,
    CERDO_1PR_OT_GenerateSlots,
    CERDO_1PR_OT_OpenBlendFile,
    CERDO_1PR_OT_PreviewPath,
    CERDO_1PR_OT_ResetPreview,
    CERDO_1PR_OT_SetAnimRange,
    CERDO_1PR_OT_ExportSlots,
)


def register_path_recorder():
    for cls in pr_classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
        bpy.utils.register_class(cls)
    bpy.types.Scene.cerdo_1_path = bpy.props.PointerProperty(type=CERDO_1PathSettings)
    if _cerdo_1_face_selection_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_cerdo_1_face_selection_handler)


def unregister_path_recorder():
    global _draw_handle
    if _draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
        _draw_handle = None
    if _cerdo_1_face_selection_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_cerdo_1_face_selection_handler)
    for cls in reversed(pr_classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
    if hasattr(bpy.types.Scene, "cerdo_1_path"):
        del bpy.types.Scene.cerdo_1_path
