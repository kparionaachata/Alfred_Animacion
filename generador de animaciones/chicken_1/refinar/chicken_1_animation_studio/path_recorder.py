# -*- coding: utf-8 -*-
"""
path_recorder.py — Alfred Animation Studio
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
from .fcurve_compat import get_fcurves, ensure_fcurves

# ── Variables globales de modulo ──────────────────────────────────────────────
_draw_handle    = None
_last_face_idx  = None


def _deferred_deselect_face(obj_name, face_index):
    """PORTADO de alfred_animation_studio (Kebyn, 2026-08-23 v3): deselecciona
    la cara recien registrada, pero diferido via bpy.app.timers en vez de
    hacerlo directo dentro de _chicken_1_face_selection_handler(). Modificar
    la seleccion del bmesh (face.select + bmesh.update_edit_mesh()) DENTRO de
    un handler de depsgraph_update_post no es seguro: depsgraph_update_post
    es, en la practica, de solo lectura -- Blender esta en medio de evaluar
    el depsgraph cuando el handler corre, y una escritura ahi puede no
    aplicarse (o aplicarse y quedar pisada por el propio ciclo de evaluacion
    que sigue corriendo). Este timer corre en el siguiente tick del event
    loop, YA AFUERA del depsgraph_update_post, que es el contexto seguro
    para tocar la malla.
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

class CH1PathPoint(PropertyGroup):
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
        items=[
            ("AUTO",   "Caminar", "Movimiento automatico: caminar o saltar segun la geometria", "ANIM_DATA", 0),
            ("PARADA", "Parada",  "El personaje se detiene en este punto antes de continuar",   "PAUSE",     1),
            # NUEVO (pedido de Kebyn, 2026-09-02): salto explicito de 3 puntos
            # consecutivos (despegue=este punto, pico=siguiente, aterrizaje=el
            # de despues) -- a diferencia de "saltar_subir"/"saltar_bajar"
            # (automaticos, detectados por diferencia de Z entre 2 puntos), este
            # lo marca el usuario a mano y usa 3 coordenadas ya existentes en el
            # recorrido, no una geometria auto-detectada.
            ("SALTAR", "Saltar",  "El personaje salta desde aqui: usa este punto y los DOS "
                                  "siguientes como despegue / pico / aterrizaje",
             "FORCE_TURBULENCE", 2),
            # NUEVAS (pedido de Kebyn, 2026-09-04): acciones de campo -- 1 sola
            # coordenada, mismo mecanismo de duplicado de punto que PARADA,
            # pero con una pose de accion real en vez de forzar rest (ver
            # ACCIONES_PUNTUALES_CAMPO / generate_<accion>() en generate_slots.py).
            ("PICOTEAR",   "Picotear",   "El personaje picotea el suelo en este punto",            "KEYTYPE_KEYFRAME_VEC", 3),
            ("ACICALARSE", "Acicalarse", "El personaje se acicala el ala en este punto",            "KEYTYPE_KEYFRAME_VEC", 4),
            ("ALETEAR",    "Aletear",    "El personaje aletea en el lugar en este punto",           "KEYTYPE_KEYFRAME_VEC", 5),
            ("RASCAR",     "Rascar",     "El personaje rasca el suelo con una pata en este punto",  "KEYTYPE_KEYFRAME_VEC", 6),
        ],
        default="AUTO",
    )
    parada_frames_punto: IntProperty(
        name="Frames parado aqui",
        description="Cantidad de frames que el personaje permanece detenido en este punto antes de seguir el recorrido",
        default=24, min=1, soft_max=99999,
    )


class CH1ParadaFrames(PropertyGroup):
    """Duracion (en frames) de UNA parada individual del recorrido.

    NUEVO 2026-07-09 (pedido de Kebyn: 'ahun me salen 60 frames por cada
    parada'). Antes existia un unico IntProperty global
    `CH1PathSettings.frames_parada` que se aplicaba identico a TODAS
    las paradas del recorrido, sin importar cuantas poses/tiempo real
    necesitaba cada una segun el pipeline Python
    (alfred_story_generator.py calcula n_poses_por_parada * 20, que
    varia parada a parada). Esta coleccion permite un valor independiente
    por cada parada detectada en el recorrido (una entrada por cada
    segmento tipo 'parada' que retorna group_segments(), en el mismo
    orden en que aparecen los puntos duplicados en el Path Recorder).

    CORREGIDO (pedido de Kebyn): este valor ya NO se edita a mano desde
    el panel. Al cargar una configuracion (CH1ST_OT_LoadConfig) se
    recalcula como la SUMA de frames de las poses de accion que
    caen dentro de ese tramo especifico,
    leyendo unicamente lo que trae el configuracion.json (ver
    _calcular_frames_por_parada en config_ops.py). El campo sigue siendo
    un IntProperty (se necesita para guardarlo/serializarlo y para que
    generate_slots.py lo use al generar los slots), pero el panel
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


class CH1WalkStyleEntry(PropertyGroup):
    """Estilo de caminata (Normal/Lento/Herido/Rapido/Correr/Perseguido) de
    UN tramo 'caminar' individual del recorrido.

    NUEVO (pedido de Kebyn, 2026-08-02): antes existia un unico
    EnumProperty global `CH1PathSettings.walk_style` que se aplicaba
    identico a TODOS los tramos 'caminar' detectados en el recorrido, sin
    importar cuantos hubiera ni el contexto de cada uno (ej. el primer
    tramo podia necesitar 'Caminar Normal' y el tercero, despues de una
    parada, 'Caminar Herido'). Esta coleccion permite un estilo
    independiente por cada tramo 'caminar' detectado (una entrada por
    cada segmento tipo 'caminar' que retorna _group_segments(), en el
    mismo orden en que aparecen en el recorrido) — mismo patron que
    CH1ParadaFrames para las paradas.
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
            ("PERSEGUIDO", "Correr (perseguido)",
             "Carrera de panico: aletea, mueve la cabeza y mira hacia atras mientras huye",
             "TRACKING_BACKWARDS", 5),
        ],
        default="NORMAL",
    )

    # NUEVO (pedido de Kebyn, 2026-08-04): "foto" del estilo que ya quedo
    # horneado en la duracion del segmento real del Paso 3 (via el boton
    # "Actualizar", ver CH1SEG_OT_UpdateFromEstimacion). Comparando
    # `style` (lo que el usuario tiene elegido AHORA en el dropdown)
    # contra `applied_style` (lo que se aplico la ULTIMA vez) el operador
    # puede distinguir "el usuario cambio el estilo de este tramo, hay que
    # recalcular los frames" de "este tramo no cambio, no tocar su
    # duracion real" -- sin este campo no habia forma de saber por que
    # motivo se presiono Actualizar (frames por parada, o estilo de
    # caminata), y por eso los tramos 'caminar' nunca se recalculaban
    # (ver comentario largo en CH1SEG_OT_UpdateFromEstimacion).
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


class CH1PathSettings(PropertyGroup):
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
    # boton "Visualizar recorrido" / CH1PR_OT_TogglePathViz).
    show_path_viz: BoolProperty(
        name="Visualizar recorrido",
        description=(
            "Muestra la linea y los puntos numerados del recorrido "
            "trazado en el viewport, incluso sin estar grabando"
        ),
        default=False,
    )
    path_points: CollectionProperty(type=CH1PathPoint)

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
            "alfred_story_generator.py (n_poses_por_parada * 20) del "
            "lado del pipeline Python, o el timing entre el config.json "
            "generado alli y lo que se reproduce aqui en Blender queda "
            "desincronizado. Ver generate_parada() en "
            "generate_slots.py."
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
        type=CH1ParadaFrames,
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
            ("PERSEGUIDO", "Correr (perseguido)",
             "Carrera de panico: aletea, mueve la cabeza y mira hacia atras mientras huye",
             "TRACKING_BACKWARDS", 5),
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
        type=CH1WalkStyleEntry,
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

    Se llama automaticamente desde: CH1PR_OT_RemoveLast,
    CH1PR_OT_ClearPath, el handler _chicken_1_face_selection_handler
    (al agregar un punto nuevo), CH1PR_OT_PreviewPath,
    CH1PR_OT_ExportSlots, y CH1ST_OT_LoadConfig (al restaurar el
    recorrido desde un JSON). El panel solo LEE pc.paradas_frames y
    ofrece un boton manual (ch1pr.sync_paradas_frames) para forzar
    la sincronizacion en cualquier caso borde.

    Retorna la cantidad de paradas detectadas (int).
    """
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
    """Sincroniza pc.walk_styles con la cantidad real de tramos 'caminar'
    del recorrido actual (pc.path_points), preservando los estilos que ya
    hayan sido elegidos a mano. Mismo patron que sync_paradas_frames()
    pero contando tramos 'caminar' en vez de 'parada'.

    IMPORTANTE: al igual que sync_paradas_frames(), escribe en datos de
    la escena (agrega/quita items de una CollectionProperty) y por lo
    tanto NUNCA debe llamarse desde un metodo draw() de panel -- solo
    desde operadores (execute()) o el handler de depsgraph_update_post.

    Se llama automaticamente desde los mismos puntos que
    sync_paradas_frames(): CH1PR_OT_RemoveLast, CH1PR_OT_ClearPath,
    el handler de seleccion de faces (al agregar un punto nuevo),
    CH1PR_OT_PreviewPath, CH1PR_OT_ExportSlots, y
    CH1ST_OT_LoadConfig (al restaurar el recorrido desde un JSON).

    Retorna la cantidad de tramos 'caminar' detectados (int).
    """
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
    (ch1_segs) -- la suma de las duraciones de sus action_poses.

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
    segmento de ch1_segs cuyo label contenga "parada" (insensible a
    mayusculas), ordenados por frame_start -- mismo orden en que se
    crean. Si ese segmento tiene action_poses con duracion > 0, se
    sobreescribe pc.paradas_frames[i].frames con esa suma. Si no hay
    segmentos "parada" en ch1_segs (o no tienen poses aun), no se
    toca nada -- se conserva el valor existente (editado a mano o
    default).
    """
    pc = context.scene.ch1_path
    segs_data = getattr(context.scene, "ch1_segs", None)
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
def _chicken_1_face_selection_handler(scene):
    """Se ejecuta en depsgraph_update_post. Registra faces seleccionadas.

    ACTUALIZADO (Kebyn, 2026-09-02): portado de alfred_animation_studio --
    el sistema anterior bloqueaba PARA SIEMPRE volver a marcar una
    coordenada ya usada (recorria toda path_cfg.path_points buscando un
    face_index igual y, si lo encontraba, descartaba el clic sin importar
    cuanto tiempo hubiera pasado ni cuantas deselecciones/reselecciones
    reales hubiera de por medio -- impedia, por ejemplo, cerrar un
    recorrido volviendo al punto de inicio, o repetir a mano una
    coordenada para una patrulla/ida y vuelta). Ahora se compara contra
    _last_face_idx (la ultima cara REALMENTE VISTA seleccionada por este
    handler, se resetea a None en cuanto deja de haber exactamente 1 cara
    seleccionada) en vez de contra el historial completo de puntos ya
    agregados -- solo se descarta el registro cuando la cara sigue siendo
    la MISMA seleccion ininterrumpida de antes (el unico caso real de
    ruido de depsgraph_update_post disparandose varias veces para un
    mismo clic). Ademas, la cara se deselecciona automaticamente despues
    de agregarse (via _deferred_deselect_face(), diferido con
    bpy.app.timers porque escribir sobre la malla DENTRO de este handler
    no es seguro), asi que el siguiente clic sobre esa misma cara --
    incluso inmediato -- dispara un cambio de estado real y se registra
    de nuevo. Revisitar una coordenada ya usada funciona ahora en todos
    los casos.
    """
    global _last_face_idx

    path_cfg = getattr(scene, "ch1_path", None)
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

    mat_name = "No Material"
    if obj.data.materials and face.material_index < len(obj.data.materials):
        mat = obj.data.materials[face.material_index]
        if mat:
            mat_name = mat.name

    pt            = path_cfg.path_points.add()
    pt.coords     = center_global
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
    """Registra el draw handler del recorrido si todavia no esta activo.
    Usado tanto al iniciar grabacion como al activar la visualizacion
    persistente (CH1PR_OT_TogglePathViz) -- ambos comparten el mismo
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
    path_cfg = getattr(scene, "ch1_path", None)
    if path_cfg is None or len(path_cfg.path_points) < 1:
        return

    points    = []
    col_pts   = []
    lines     = []
    col_lines = []

    for i, pt in enumerate(path_cfg.path_points):
        coord = Vector(pt.coords)
        points.append(coord)
        col_pts.append((0.3, 0.7, 1.0, 1.0))   # azul Alfred
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


# BUGFIX (Kebyn, 2026-09-02): pt.coords se calcula en record_path_point()
# como face.calc_center_median() @ obj.matrix_world -- esa operacion de
# bmesh/matriz introduce ruido de punto flotante (tipicamente 1e-6 a
# 1e-4). En un tramo diagonal (cambia X y Y a la vez) los dos puntos caen
# en faces distintas del terreno; aunque el panel redondea a 2 decimales
# y ambos muestran el mismo Z visible, el valor crudo puede diferir en
# ese ruido y disparaba "saltar_subir"/"saltar_bajar" en terreno
# perfectamente plano. EPSILON_Z absorbe ese ruido sin afectar saltos
# reales (que cambian ~1.0 unidad de Z, un bloque).
EPSILON_Z = 1e-3


def _detect_move(p0, p1):
    """NUEVO 2026-07-08 (paradas): si el punto es identico al anterior
    (misma x/y/z), se clasifica como "parada" — root inmovil, canvas
    libre para que CONCATENAR superponga la action_pose de este tramo.
    Replica el mismo criterio que `_detectar_movimiento_recorrido()` en
    el pipeline (alfred_story_generator.py) y `detect_movement_type()`
    en generate_slots.py — los 3 deben coincidir.
    """
    x0, y0, z0 = p0.coords[0], p0.coords[1], p0.coords[2]
    x1, y1, z1 = p1.coords[0], p1.coords[1], p1.coords[2]
    if x0 == x1 and y0 == y1 and z0 == z1:
        return "parada"
    dz = z1 - z0
    if   dz > EPSILON_Z:  return "saltar_subir"
    elif dz < -EPSILON_Z: return "saltar_bajar"
    else:                  return "caminar"


def _group_segments(path_points):
    """Agrupa los puntos en segmentos: caminar (multi-punto), saltar_subir/bajar
    (2 puntos), parada (2 puntos identicos — NUEVO 2026-07-08), saltar (3 puntos
    consecutivos marcados a mano — NUEVO 2026-09-02, ver tipo_segmento=SALTAR)."""
    pts = list(path_points)
    segments = []
    i = 0
    while i < len(pts) - 1:
        # NUEVO (Kebyn, 2026-09-02): salto explicito de 3 puntos. Si el punto
        # actual esta marcado SALTAR y quedan al menos 2 puntos mas adelante,
        # se consume este punto + los DOS siguientes como un unico segmento
        # "saltar" (despegue/pico/aterrizaje) y se avanza 2 posiciones. Si no
        # alcanzan los puntos (marcado cerca del final del recorrido), se
        # ignora el marcador y cae al comportamiento AUTO normal.
        if getattr(pts[i], "tipo_segmento", "AUTO") == "SALTAR" and i < len(pts) - 2:
            segments.append({"type": "saltar", "points": [pts[i], pts[i + 1], pts[i + 2]]})
            i += 2
            continue

        # NUEVO (Kebyn, 2026-09-04): acciones de campo (picotear/acicalarse/
        # aletear/rascar) -- 1 sola coordenada, mismo mecanismo de duplicado
        # de punto que PARADA (ver _expand_points_with_paradas()), pero con
        # tipo_marcado propio para que la estimacion del panel las cuente
        # aparte en vez de como 'parada' generica.
        _tipo_actual = getattr(pts[i], "tipo_segmento", "AUTO")
        if _tipo_actual in ("PICOTEAR", "ACICALARSE", "ALETEAR", "RASCAR"):
            segments.append({"type": _tipo_actual.lower(), "points": [pts[i], pts[i + 1]]})
            i += 1
            continue

        move = _detect_move(pts[i], pts[i + 1])
        if move == "caminar":
            group = [pts[i]]
            # BUGFIX (Kebyn, 2026-09-02): el corte por SALTAR tiene que
            # detenerse ACA tambien, no solo al entrar al while de arriba --
            # este while interno solo miraba la geometria (Z), asi que en un
            # recorrido totalmente plano se tragaba de largo el punto
            # marcado SALTAR dentro del mismo tramo "caminar" (nunca le daba
            # una vuelta al while externo para detectarlo). Se corta la
            # racha de caminata apenas el punto actual esta marcado SALTAR,
            # dejando que la proxima vuelta del while externo arme el
            # segmento de salto desde ahi.
            while (i < len(pts) - 1
                   and _detect_move(pts[i], pts[i + 1]) == "caminar"
                   and getattr(pts[i], "tipo_segmento", "AUTO") != "SALTAR"):
                group.append(pts[i + 1])
                i += 1
            segments.append({"type": "caminar", "points": group})
        else:
            segments.append({"type": move, "points": [pts[i], pts[i + 1]]})
            i += 1
    return segments


class _StopPointStub:
    """Objeto liviano con la misma 'forma' que CH1PathPoint (coords,
    texture, face_index) usado para representar el punto DUPLICADO que se
    inserta automaticamente detras de cada punto marcado como parada.
    No es una PropertyGroup real (no se guarda en la escena) -- solo existe
    en memoria mientras se arma el recorrido para preview/exportacion."""
    __slots__ = ("coords", "texture", "face_index")

    def __init__(self, coords, texture, face_index):
        self.coords     = tuple(coords)
        self.texture    = texture
        self.face_index = face_index


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
    generate_slots.py y _detect_move() en este mismo archivo), sin
    que el usuario tenga que seleccionar la misma face dos veces (el
    handler de seleccion de faces ya lo impide por diseno).

    Si NINGUN punto esta en modo PARADA (todos en AUTO), la lista
    resultante es identica a la original -- el flujo de solo caminar no
    se ve afectado en absoluto.

    Retorna una tupla:
      (puntos_expandidos, frames_paradas_marcadas)
    donde frames_paradas_marcadas es la lista de pt.parada_frames_punto,
    en el mismo orden en que apareceran los segmentos 'parada' que
    produzca luego group_segments()/_group_segments() sobre el resultado.
    """
    expanded = []
    frames_paradas_marcadas = []
    n = len(pts)
    for i, pt in enumerate(pts):
        expanded.append(pt)

        _tipo_pt = getattr(pt, "tipo_segmento", "AUTO")
        override_activo_parada = _tipo_pt == "PARADA"
        # NUEVO (Kebyn, 2026-09-04): las 4 acciones de campo usan el MISMO
        # mecanismo de duplicado de punto que PARADA (se necesitan 2 puntos
        # identicos para que group_segments()/_group_segments() arme un
        # segmento de 1 sola coordenada), pero con duracion FIJA (ver
        # FRAMES_PICOTEAR/ACICALARSE/ALETEAR/RASCAR en generate_slots.py) --
        # por eso NO se agregan a frames_paradas_marcadas (esa lista es
        # exclusiva de PARADA; ver parada_idx en los bucles de preview/
        # export mas abajo, que solo avanza para move_type == "parada").
        override_activo_accion = _tipo_pt in ("PICOTEAR", "ACICALARSE", "ALETEAR", "RASCAR")
        override_activo = override_activo_parada or override_activo_accion

        # SALVAGUARDA (Kebyn, 2026-08-02): las coordenadas de saltar_subir /
        # saltar_bajar NO se pueden alterar a parada/accion de campo -- solo
        # los tramos que geometricamente son "caminar" (Z constante). Si por
        # cualquier motivo (ej. se recorto/cambio un punto despues de
        # marcarlo) el tramo real hacia el siguiente punto resulta ser un
        # salto, se ignora el override aunque tipo_segmento siga marcado.
        if override_activo and i < n - 1:
            real_move = _detect_move(pt, pts[i + 1])
            if real_move != "caminar":
                override_activo = False

        if override_activo:
            expanded.append(_StopPointStub(pt.coords, pt.texture, pt.face_index))
            if override_activo_parada:
                frames_paradas_marcadas.append(max(1, int(pt.parada_frames_punto)))
    return expanded, frames_paradas_marcadas


def calcular_estimacion_slots(scene):
    """
    NUEVO 2026-08-02 (pedido de Kebyn): version reutilizable de la
    "Estimacion de slots" del Paso 2 (panels.py), pensada para poder
    guardarla tambien en el configuracion.json al exportar (ver
    CH1ST_OT_SaveConfig / _serialize_configuracion en config_ops.py),
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
        scene.ch1_segs.segments (recorrido dividido en Paso 3, o
        config cargada) -- se listan ESOS directamente, con el mismo
        frame_start/frame_end/frame_end_auto que usa el panel. "tipo" se
        deriva del label ("NN_tipo[_intervalo_caminata_normal]", mismo
        formato que arma AutoSplitFromConfig en operators_segments.py y
        que ya interpreta alfred_filter.py en el pipeline externo).
      - fuente == "estimacion_geometrica": todavia no hay segmentos
        reales -- fallback idéntico al que usaba panels.py: se agrupan
        pc.path_points (con las paradas ya expandidas) via
        _group_segments(), y se estima la duracion de cada tramo con las
        mismas constantes/formula que generate_caminar() en
        generate_slots.py.
      - Si no hay nada que estimar (ni segmentos reales ni 2+
        path_points), devuelve ([], None).

    Cada slot es un dict serializable a JSON:
        {"slot": int, "tipo": str, "label": str, "frames_estimados": int}
    """
    real_segs = None
    try:
        real_segs = scene.ch1_segs.segments
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
            # NOTA (port a chicken_1, 2026-08-10): a diferencia de Alfred,
            # Chicken1AnimSegment NO tiene frame_start_planned/
            # frame_end_planned (esa "foto" del Paso 2 nunca se porto a este
            # addon -- ver el propio comentario de CH1SEG_OT_UpdateFromEstimacion
            # en operators_segments.py). Usar directamente esos atributos
            # rompia con AttributeError apenas existia algun segmento real
            # (ej. recien creados por "Dividir segmentos"). Se usa siempre el
            # rango en vivo del segmento (frame_start/frame_end/frame_end_auto).
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
    desde CH1SEG_OT_AutoSplitFromConfig (boton "Dividir segmentos"
    del Paso 3), que necesita recalcular los tramos del recorrido
    aunque ya existan segmentos viejos (para poder reemplazarlos).

    Devuelve la misma lista de dicts que calcular_estimacion_slots()
    (fuente "estimacion_geometrica"), o None si no hay suficientes
    puntos de recorrido para estimar nada.
    """
    pc = getattr(scene, "ch1_path", None)
    if pc is None or len(pc.path_points) <= 1:
        return None

    # NOTA (port a chicken_1): a diferencia de Alfred (motor biomecanico
    # que estira/comprime el ciclo segun distancia y velocidad del estilo
    # elegido -- WALK_STYLE_PARAMS/speed_mult), chicken_1 solo tiene UN
    # ciclo de caminata REALMENTE capturado (KEYFRAMES_CAMINAR_CYCLE, ver
    # generate_slots.py). Caminar Lento y Caminar Rapido reutilizan ese
    # mismo ciclo pero retimed (mas o menos frames por ciclo -- ver
    # _get_walk_cycle() en generate_slots.py); Caminar Normal no cambia.
    # generate_caminar() repite el ciclo elegido una vez por cada par de
    # puntos consecutivos del tramo, sin importar la distancia real entre
    # ellos. La estimacion de aqui replica esa misma formula por estilo
    # para que el numero mostrado en el panel coincida con lo que
    # "Exportar recorrido" realmente genera. Perseguido SI tiene su propio
    # largo de ciclo (mas rapido que Rapido, ver
    # FRAMES_CAMINAR_CICLO_PERSEGUIDO / _apply_perseguido_overlay() en
    # generate_slots.py -- aleteo panico + mirada atras encimados sobre el
    # ciclo retimed, no una captura nueva). Caminar Herido y Correr (trote
    # liso) todavia no tienen ciclo propio (necesitan una captura de
    # referencia distinta) y por ahora se estiman igual que Normal.
    try:
        from .generate_slots import (
            FRAMES_CAMINAR_CICLO_NORMAL     as _CICLO_NORMAL,
            FRAMES_CAMINAR_CICLO_LENTO      as _CICLO_LENTO,
            FRAMES_CAMINAR_CICLO_RAPIDO     as _CICLO_RAPIDO,
            FRAMES_CAMINAR_CICLO_PERSEGUIDO as _CICLO_PERSEGUIDO,
            FRAMES_SALTAR                   as _FRAMES_SALTAR,
        )
    except ImportError:
        _CICLO_NORMAL, _CICLO_LENTO, _CICLO_RAPIDO, _CICLO_PERSEGUIDO = 41, 55, 29, 23
        _FRAMES_SALTAR = 65

    _CICLO_POR_ESTILO = {
        "NORMAL":     _CICLO_NORMAL,
        "LENTO":      _CICLO_LENTO,
        "RAPIDO":     _CICLO_RAPIDO,
        "PERSEGUIDO": _CICLO_PERSEGUIDO,
        # sin ciclo propio todavia -- se estiman como Normal
        "HERIDO": _CICLO_NORMAL,
        "CORRER": _CICLO_NORMAL,
    }

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
            # Cada tramo 'caminar' detectado tiene su propio estilo
            # independiente en pc.walk_styles[caminar_idx] (sincronizado por
            # sync_walk_styles()). Se muestra en la etiqueta como referencia
            # para una futura captura por estilo -- no afecta la duracion.
            style_key = (pc.walk_styles[caminar_idx].style
                         if caminar_idx < len(pc.walk_styles) else "NORMAL")
            n_repeats = max(1, len(seg_pts) - 1)
            _ciclo_estilo = _CICLO_POR_ESTILO.get(style_key, _CICLO_NORMAL)
            total_f = n_repeats * (_ciclo_estilo - 1) + 1
            slots.append({
                "slot": i + 1,
                "tipo": "caminar",
                "label": f"caminar ({style_key.title()})",
                "frames_estimados": total_f,
                "caminar_idx": caminar_idx,
            })
            caminar_idx += 1
        elif seg_type == "saltar_subir":
            slots.append({"slot": i + 1, "tipo": "saltar_subir",
                           "label": "saltar_subir", "frames_estimados": 25})
        elif seg_type == "saltar_bajar":
            slots.append({"slot": i + 1, "tipo": "saltar_bajar",
                           "label": "saltar_bajar", "frames_estimados": 35})
        elif seg_type == "saltar":
            slots.append({"slot": i + 1, "tipo": "saltar",
                           "label": "saltar", "frames_estimados": _FRAMES_SALTAR})
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


def _pt_to_dict(pt, idx):
    return {
        "index": idx + 1,
        "coordinates": {"x": round(pt.coords[0], 4),
                        "y": round(pt.coords[1], 4),
                        "z": round(pt.coords[2], 4)},
        "texture": pt.texture,
        "face_index": pt.face_index,
    }


# =============================================================================
# OPERADORES
# =============================================================================

class CH1PR_OT_ToggleRecording(Operator):
    bl_idname  = "ch1pr.toggle_recording"
    bl_label   = "Toggle Recording"
    bl_description = "Inicia o detiene la grabacion de puntos del recorrido"
    bl_options = {"REGISTER"}

    def execute(self, context):
        pc = context.scene.ch1_path
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


class CH1PR_OT_TogglePathViz(Operator):
    """NUEVO (Kebyn, 2026-08-02): boton independiente de la grabacion para
    mostrar/ocultar la linea y los puntos numerados del recorrido ya
    trazado. Antes, la unica forma de ver el recorrido en el viewport era
    tener la grabacion activa; al presionar "Detener grabacion" el trazado
    se volvia invisible. Con esto se puede revisar el recorrido en
    cualquier momento (por ejemplo despues de cargar una configuracion
    guardada) sin tener que re-entrar en modo grabacion."""
    bl_idname  = "ch1pr.toggle_path_viz"
    bl_label   = "Visualizar recorrido"
    bl_description = (
        "Muestra u oculta la linea y los puntos numerados del recorrido "
        "trazado en el viewport, sin necesidad de estar grabando"
    )
    bl_options = {"REGISTER"}

    def execute(self, context):
        pc = context.scene.ch1_path
        pc.show_path_viz = not pc.show_path_viz

        if pc.show_path_viz:
            _ensure_draw_handler()
        else:
            _maybe_remove_draw_handler(pc)

        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
        return {"FINISHED"}


class CH1PR_OT_RemoveLast(Operator):
    bl_idname  = "ch1pr.remove_last"
    bl_label   = "Eliminar ultimo punto"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        pc = context.scene.ch1_path
        if len(pc.path_points) > 0:
            pc.path_points.remove(len(pc.path_points) - 1)
        sync_paradas_frames(pc)
        sync_walk_styles(pc)
        return {"FINISHED"}


class CH1PR_OT_ClearPath(Operator):
    bl_idname  = "ch1pr.clear_path"
    bl_label   = "Limpiar recorrido"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        pc = context.scene.ch1_path
        pc.path_points.clear()
        sync_paradas_frames(pc)
        sync_walk_styles(pc)
        return {"FINISHED"}


class CH1PR_OT_SyncParadasFrames(Operator):
    """Ajusta pc.paradas_frames a la cantidad real de paradas del
    recorrido actual. NUEVO 2026-07-09: boton de respaldo manual — la
    sincronizacion ya ocurre automaticamente al agregar/quitar puntos,
    generar preview/exportar, o cargar un config.json, pero al escribir
    en datos de la escena esto NO puede hacerse desde draw() (Blender lo
    prohibe), asi que este boton cubre cualquier caso borde donde el
    recorrido haya cambiado por otra via."""
    bl_idname  = "ch1pr.sync_paradas_frames"
    bl_label   = "Sincronizar frames por parada"
    bl_description = (
        "Ajusta la lista de frames por parada a la cantidad real de "
        "paradas detectadas en el recorrido actual, conservando los "
        "valores ya editados a mano"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        pc = context.scene.ch1_path
        n = sync_paradas_frames(pc)
        n_walk = sync_walk_styles(pc)
        self.report({"INFO"}, f"Sincronizado: {n} parada(s) y {n_walk} tramo(s) de caminata detectado(s)")
        return {"FINISHED"}


class CH1PR_OT_OpenBlendFile(Operator):
    bl_idname  = "ch1pr.open_blend"
    bl_label   = "Seleccionar .blend"
    bl_options = {"REGISTER"}
    filepath: StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        context.scene.ch1_path.blend_filepath = self.filepath
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
    pc = context.scene.ch1_path
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

    chicken_1_obj = bpy.data.objects.get("chicken_1")
    if chicken_1_obj:
        parts.append(("concat_arm",   chicken_1_obj.get("_concat_arm_data", "")))
        parts.append(("concat_root",  chicken_1_obj.get("_concat_root_data", "")))
        parts.append(("concat_start", chicken_1_obj.get("_concat_frame_start", "")))
        parts.append(("concat_end",   chicken_1_obj.get("_concat_frame_end", "")))

    raw = _json.dumps(parts, default=str, sort_keys=False)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


class CH1PR_OT_PreviewPath(Operator):
    """Reproduce el recorrido de Alfred en el viewport con animacion base."""
    bl_idname  = "ch1pr.preview_path"
    bl_label   = "Reproducir recorrido"
    bl_description = (
        "Genera la animacion base de Alfred (caminar/saltar) directamente "
        "en el viewport segun los puntos del recorrido"
    )
    bl_options = {"REGISTER"}

    ROOT_NAME = "chicken_1"
    ARM_NAME  = "Armature_chicken_1"

    # ── Carga lazy del modulo generate_slots ──────────────────────────
    @staticmethod
    def _get_gen():
        """Carga generate_slots.py siempre fresco (sin cache) para garantizar coherencia."""
        import importlib.util as _ilu
        import sys as _sys
        # Siempre recargar — evita que una version cacheada desincronice preview vs exportacion
        _sys.modules.pop("gen_slots_chicken_1_preview", None)
        addon_dir = os.path.dirname(os.path.abspath(__file__))
        gen_path  = os.path.join(addon_dir, "generate_slots.py")
        spec = _ilu.spec_from_file_location("gen_slots_chicken_1_preview", gen_path)
        mod  = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _sys.modules["gen_slots_chicken_1_preview"] = mod
        return mod

    # ── Aplicar keyframes Mixamo reales: saltar_subir (25 frames) ────────────
    def _bones_saltar_subir(self, bones, frame, rf):
        """Aplica los keyframes Mixamo reales de KEYFRAMES_SALTAR_SUBIR al frame dado."""
        gen = self._get_gen()
        kf_data = gen.KEYFRAMES_SALTAR_SUBIR
        # rf es el offset relativo al inicio del slot (0-based)
        # Buscamos el frame de referencia mas cercano en los datos (0..24)
        rel = min(max(rf, 0), 24)
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
        """Biomecánica de caminar identica a la de generate_caminar en generate_slots.py."""
        # Parametros identicos a ANIMATION_CONFIG en generate_caminar
        arm_base_x      = math.radians(90)
        arm_swing_y_max = math.radians(70)
        elbow_flex_max  = math.radians(50)
        leg_swing_x_max = math.radians(50)
        leg_sway_z_max  = math.radians(3)
        knee_flex_max   = math.radians(40)
        spine_bend_max  = math.radians(0.1)
        neck_tilt_max   = math.radians(1.5)
        head_stab       = 0.25
        FRAMES_PER_BIO_CYCLE = 20.0

        # Ciclo normalizado (igual logica que generate_caminar: walk_cycles proporcional)
        total_slot = max(fpb, 1)
        walk_cycles = total_slot / FRAMES_PER_BIO_CYCLE
        walk_cycle  = (rf / total_slot) * walk_cycles  # fraccion de ciclo en [0, walk_cycles]

        def ease_in_out_sine(t):
            return -(math.cos(math.pi * t) - 1) / 2

        def ease_in_out_cubic(t):
            if t < 0.5:
                return 4 * t * t * t
            return 1 - pow(-2 * t + 2, 3) / 2

        def calc_leg_swing(phase):
            return leg_swing_x_max * math.sin(phase * 2 * math.pi)

        def calc_arm_swing(phase):
            if phase < 0.5:
                return ease_in_out_sine(phase / 0.5) * arm_swing_y_max * 2 - arm_swing_y_max
            else:
                return arm_swing_y_max - ease_in_out_sine((phase - 0.5) / 0.5) * arm_swing_y_max * 2

        def calc_elbow_flex(phase):
            if phase < 0.3:
                return ease_in_out_sine(phase / 0.3) * elbow_flex_max * 0.85 + elbow_flex_max * 0.15
            elif phase < 0.7:
                return elbow_flex_max - ease_in_out_cubic((phase - 0.3) / 0.4) * elbow_flex_max * 0.6
            else:
                return elbow_flex_max * 0.4 - ease_in_out_sine((phase - 0.7) / 0.3) * elbow_flex_max * 0.25

        # Hips: forzado a (0,0,0) — identico a generate_caminar
        if 'Hips_alfred' in bones:
            bones['Hips_alfred'].rotation_euler = (0.0, 0.0, 0.0)
            self._kfb(bones['Hips_alfred'], frame)

        # Columna
        spine_forward = math.sin(walk_cycle * 2 * math.pi + math.pi/6) * spine_bend_max
        spine_tilt    = math.cos(walk_cycle * 2 * math.pi + math.pi/3) * spine_bend_max * 0.75
        for key in ('Spine_alfred', 'Spine1_alfred', 'Spine2_alfred'):
            if key in bones:
                bones[key].rotation_euler = (spine_forward, 0.0, spine_tilt)
                self._kfb(bones[key], frame)

        # Cuello
        neck_forward = -spine_forward * head_stab
        neck_tilt    = math.sin(walk_cycle * 2 * math.pi) * neck_tilt_max
        neck_side    = math.cos(walk_cycle * 2 * math.pi + math.pi/4) * neck_tilt_max * 0.5
        if 'Neck_alfred' in bones:
            bones['Neck_alfred'].rotation_euler = (neck_forward, neck_side, neck_tilt)
            self._kfb(bones['Neck_alfred'], frame)
        if 'face_alfred' in bones:
            bones['face_alfred'].rotation_euler = (0.0, 0.0, 0.0)
            self._kfb(bones['face_alfred'], frame)

        # Piernas
        left_leg_swing = calc_leg_swing(walk_cycle % 1.0)
        if 'LeftUpLeg_alfred' in bones:
            bones['LeftUpLeg_alfred'].rotation_euler = (left_leg_swing, 0.0, 0.0)
            self._kfb(bones['LeftUpLeg_alfred'], frame)
        right_leg_swing = calc_leg_swing((walk_cycle + 0.5) % 1.0)
        if 'RightUpLeg_alfred' in bones:
            bones['RightUpLeg_alfred'].rotation_euler = (right_leg_swing, 0.0, 0.0)
            self._kfb(bones['RightUpLeg_alfred'], frame)

        # Rodillas
        if 'Leftknee_alfred' in bones:
            bones['Leftknee_alfred'].rotation_euler = (min(0, left_leg_swing) * 0.8, 0.0, 0.0)
            self._kfb(bones['Leftknee_alfred'], frame)
        if 'Rightknee_alfred' in bones:
            bones['Rightknee_alfred'].rotation_euler = (min(0, right_leg_swing) * 0.8, 0.0, 0.0)
            self._kfb(bones['Rightknee_alfred'], frame)

        # Brazo derecho
        right_arm_phase = (walk_cycle + 0.25) % 1.0
        if 'RightUpArm_alfred' in bones:
            bones['RightUpArm_alfred'].rotation_euler = (arm_base_x, calc_arm_swing(right_arm_phase), 0.0)
            self._kfb(bones['RightUpArm_alfred'], frame)
        if 'Rightelbow_alfred' in bones:
            bones['Rightelbow_alfred'].rotation_euler = (0.0, 0.0, -calc_elbow_flex(right_arm_phase))
            self._kfb(bones['Rightelbow_alfred'], frame)

        # Brazo izquierdo
        left_arm_phase = (walk_cycle + 0.75) % 1.0
        if 'LeftUpArm_alfred' in bones:
            bones['LeftUpArm_alfred'].rotation_euler = (arm_base_x, -calc_arm_swing(left_arm_phase), 0.0)
            self._kfb(bones['LeftUpArm_alfred'], frame)
        if 'Leftelbow_alfred' in bones:
            bones['Leftelbow_alfred'].rotation_euler = (0.0, 0.0, calc_elbow_flex(left_arm_phase))
            self._kfb(bones['Leftelbow_alfred'], frame)

    # ── Posicion root: salto subir ───────────────────────────────────────────
    @staticmethod
    def _pos_saltar_subir(p0c, p1c, rf):
        """Parabola ascendente para Alfred (25 frames)."""
        ox, oy, oz = p0c[0], p0c[1], p0c[2]
        dx = p1c[0] - ox;  dy = p1c[1] - oy;  dz = p1c[2] - oz
        TOTAL = 25
        t = rf / max(TOTAL - 1, 1)
        t_s = t * t * (3 - 2 * t)   # smoothstep
        dist_xy = math.sqrt(dx * dx + dy * dy)
        H = max(abs(dz) * 0.6, dist_xy * 0.3, 0.3)
        arc = 4 * H * t_s * (1 - t_s)
        return (ox + t_s * dx, oy + t_s * dy, oz + t_s * dz + arc)

    # ── Posicion root: salto bajar ───────────────────────────────────────────
    @staticmethod
    def _pos_saltar_bajar(p0c, p1c, rf):
        """Caida para Alfred (35 frames)."""
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
    # Lista completa de objetos del personaje chicken_1 según chicken_1.json
    # (root Empty "chicken_1" → Armature_chicken_1 → mallas, todas
    # parentadas directamente al Armature, no al Empty raiz)
    ALL_OBJECTS = (
        "chicken_1",              # EMPTY — root
        "Armature_chicken_1",     # ARMATURE
        "WingR_chicken_1",        # MESH
        "WingL_chicken_1",
        "LegL_chicken_1",
        "LegL.001_chicken_1",
        "Head_chicken_1",
        "Head2_chicken_1",
        "Eyes_chicken_1",
        "Body_chicken_1",
        "BeakTop_chicken_1",
        "BeakBottom_chicken_1",
    )

    def _load_character(self, context, blend_path):
        """
        Carga (append) todos los objetos de chicken_1 desde blend_path.
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
                ("chicken_1",           "EMPTY"),
                ("Armature_chicken_1",  "ARMATURE"),
                ("WingR_chicken_1",     "MESH"),
                ("WingL_chicken_1",     "MESH"),
                ("LegL_chicken_1",      "MESH"),
                ("LegL.001_chicken_1",  "MESH"),
                ("Head_chicken_1",      "MESH"),
                ("Head2_chicken_1",     "MESH"),
                ("Eyes_chicken_1",      "MESH"),
                ("Body_chicken_1",      "MESH"),
                ("BeakTop_chicken_1",   "MESH"),
                ("BeakBottom_chicken_1","MESH"),
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

        # --- PASO 4: reparar jerarquía según chicken_1.json ---
        # IMPORTANTE: se usa keep-transform al reparentar (en vez de
        # matrix_parent_inverse.identity()) para respetar la rotacion y
        # escala reales del root/armature tal como vienen en el .blend,
        # sin que la reparentacion las altere.
        def _reparent_keep_transform(obj, new_parent):
            if obj is None or new_parent is None:
                return
            old_world = obj.matrix_world.copy()
            obj.parent = new_parent
            try:
                obj.matrix_parent_inverse = (
                    new_parent.matrix_world.inverted() @ old_world @ obj.matrix_basis.inverted()
                )
            except Exception:
                obj.matrix_parent_inverse = new_parent.matrix_world.inverted()

        root = bpy.data.objects.get("chicken_1")
        arm  = bpy.data.objects.get("Armature_chicken_1")

        # Armature → chicken_1
        if root and arm and arm.parent != root:
            _reparent_keep_transform(arm, root)

        # Mallas → Armature_chicken_1 (hijos directos del armature, según json;
        # a diferencia de Alfred, en chicken_1 las mallas NO cuelgan del Empty raiz)
        mesh_children_of_armature = [
            "WingR_chicken_1", "WingL_chicken_1",
            "LegL_chicken_1", "LegL.001_chicken_1",
            "Head_chicken_1", "Head2_chicken_1", "Eyes_chicken_1",
            "Body_chicken_1", "BeakTop_chicken_1", "BeakBottom_chicken_1",
        ]
        for mname in mesh_children_of_armature:
            obj = bpy.data.objects.get(mname)
            if obj and arm and obj.parent != arm:
                _reparent_keep_transform(obj, arm)

        # --- PASO 5: asegurar visibilidad de todos ---
        for name in self.ALL_OBJECTS:
            obj = bpy.data.objects.get(name)
            if obj:
                obj.hide_viewport = False
                obj.hide_render   = False

        # --- PASO 4b: forzar transform identidad en el root "chicken_1" ---
        # El root SIEMPRE debe quedar en location=(0,0,0), rotation=(0,0,0),
        # scale=(1,1,1) al cargar el personaje -- es el estado real que tiene
        # chicken_1.blend al abrirlo directo. Si "chicken_1" ya existia en
        # bpy.data (sesion previa, ApplyKeyPointToRoot, etc.) su transform
        # puede haber quedado con valores de una operacion anterior (ej.
        # un keypoint del recorrido, o un scale residual); se reafirma aca
        # para que "trazar el recorrido" no herede estado sucio de la sesion.
        root_reset = bpy.data.objects.get("chicken_1")
        if root_reset is not None:
            if root_reset.animation_data and root_reset.animation_data.action:
                _old_root_act = root_reset.animation_data.action
                root_reset.animation_data.action = None
                bpy.data.actions.remove(_old_root_act)
            root_reset.location       = (0.0, 0.0, 0.0)
            root_reset.rotation_euler = (0.0, 0.0, 0.0)
            root_reset.scale          = (1.0, 1.0, 1.0)

        root_ok = bpy.data.objects.get("chicken_1") is not None
        print(f"  _load_character: {'OK' if root_ok else 'ERROR — chicken_1 no encontrado'}")

        # ── Sincronizar armature_name en ch1st para que Paso 3 lo detecte ──
        arm_loaded = bpy.data.objects.get(self.ARM_NAME)
        if arm_loaded and arm_loaded.type == "ARMATURE":
            try:
                context.scene.ch1st.armature_name = arm_loaded.name
                print(f"  _load_character: ch1st.armature_name = '{arm_loaded.name}'")
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
                    st = context.scene.ch1st
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

        # Sincronizar armature_name en ch1st (por si el personaje ya estaba en escena)
        try:
            if not context.scene.ch1st.armature_name:
                context.scene.ch1st.armature_name = arm_obj.name
        except Exception:
            pass

        pb = arm_obj.pose.bones
        bone_names = [
            'Hips_alfred', 'Spine_alfred', 'Spine1_alfred', 'Spine2_alfred',
            'Neck_alfred', 'face_alfred',
            'RightUpArm_alfred', 'Rightelbow_alfred',
            'LeftUpArm_alfred',  'Leftelbow_alfred',
            'RightUpLeg_alfred', 'Rightknee_alfred',
            'LeftUpLeg_alfred',  'Leftknee_alfred',
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

        ROOT_ACT = "_chicken_1_preview_root"
        ARM_ACT  = "_chicken_1_preview_arm"
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
        pc = context.scene.ch1_path

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

    def execute(self, context):
        pc  = context.scene.ch1_path
        pts = list(pc.path_points)

        if pc.recording_active:
            pc.recording_active = False
            _maybe_remove_draw_handler(pc)

        if len(pts) == 1:
            return self._execute_idle(context, pc, pts[0])
        if len(pts) < 1:
            self.report({"WARNING"}, "Agrega al menos 1 punto"); return {"CANCELLED"}

        root_empty = bpy.data.objects.get(self.ROOT_NAME)
        if root_empty is None or root_empty.type != "EMPTY":
            blend_path = bpy.path.abspath(pc.blend_filepath) if pc.blend_filepath else ""
            if not blend_path or not os.path.isfile(blend_path):
                try:
                    st = context.scene.ch1st
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

        # Sincronizar armature_name en ch1st (por si el personaje ya estaba en escena)
        try:
            if not context.scene.ch1st.armature_name:
                context.scene.ch1st.armature_name = arm_obj.name
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
        expanded_pts, parada_frames_marcadas = _expand_points_with_paradas(pts)

        key_points = [
            {"index": i + 1,
             "coordinates": {"x": round(pt.coords[0], 4),
                             "y": round(pt.coords[1], 4),
                             "z": round(pt.coords[2], 4)},
             "texture":    pt.texture or "grass_block_top",
             "face_index": pt.face_index if pt.face_index else str(i + 1),
             # NUEVO (Kebyn, 2026-09-02): marcador de tipo_segmento propagado
             # al dict para que gen.group_segments() detecte "saltar" (3
             # puntos) igual que _group_segments() lo hace sobre los
             # CH1PathPoint originales.
             "tipo_marcado": getattr(pt, "tipo_segmento", "AUTO")}
            for i, pt in enumerate(expanded_pts)
        ]

        gen_segments  = gen.group_segments(key_points)
        sync_paradas_frames(pc)
        sync_walk_styles(pc)
        sync_paradas_frames_from_segments(context)
        start_frame   = pc.frame_inicio
        current_frame = start_frame
        slot_index    = pc.slot_inicio
        parada_idx    = 0
        caminar_idx   = 0
        # FIX (Kebyn, 2026-07-13): antes root_rot quedaba fijo en pc.root_rot_z
        # (el valor estatico del panel, ej. -90) durante TODO el recorrido, para
        # los 4 tipos de segmento por igual. Un heading real solo se calculaba
        # DENTRO de generate_caminar (sus propios sub-tramos internos); saltos y
        # paradas nunca heredaban el heading del ultimo tramo real de caminata/
        # curva -- por eso el objeto "chicken_1" se veia con la misma rotacion Z
        # estatica sin importar el tramo. prev_rz guarda el ultimo heading real
        # (grados) visto en un tramo con desplazamiento propio, y se pasa como
        # Z de root_rot a saltar_subir/saltar_bajar/parada en vez del estatico.
        prev_rz = root_rot[2]

        for gseg in gen_segments:
            move_type = gseg["type"]
            points    = gseg["points"]

            if len(points) >= 2:
                # BUGFIX (Kebyn, 2026-09-03): antes esto usaba SIEMPRE
                # points[0] -> points[-1] (primer punto -> ultimo punto del
                # segmento completo) para calcular el heading a heredar por
                # el SIGUIENTE segmento. Para "caminar" con varios puntos
                # intermedios (recorrido no recto), esa direccion promedio
                # de punta a punta NO es la misma que la direccion del
                # ULTIMO tramo real (la que generate_caminar() usa de hecho
                # para el ultimo _SEGMENT_DIRECTIONS, y con la que termina
                # visualmente el personaje). Ese desfase es lo que producia
                # el flip de rotacion (ej. -45 -> 45) justo al entrar a un
                # salto: el salto heredaba un heading calculado sobre el
                # tramo completo de caminata, no el heading real con el que
                # el personaje quedo mirando al terminar de caminar.
                # Para saltar_subir/saltar_bajar/saltar/parada esto no
                # cambia nada (su propio target interno YA es
                # points[0]->points[-1] sobre todo el segmento), pero para
                # "caminar" ahora se usan los DOS ULTIMOS puntos del
                # segmento (el tramo final real).
                if move_type == "caminar":
                    _p0 = points[-2]["coordinates"]
                    _p1 = points[-1]["coordinates"]
                else:
                    _p0 = points[0]["coordinates"]
                    _p1 = points[-1]["coordinates"]
                _da = gen._compute_direction_angle(_p0, _p1)
            else:
                _da = None
            _cur_rot = (root_rot[0], root_rot[1], prev_rz)

            if move_type == "saltar_subir":
                code, end_frame = gen.generate_saltar_subir(
                    slot_index, current_frame, points, today, _cur_rot)
            elif move_type == "saltar_bajar":
                code, end_frame = gen.generate_saltar_bajar(
                    slot_index, current_frame, points, today, _cur_rot)
            elif move_type == "saltar":
                # NUEVO (Kebyn, 2026-09-02): salto explicito de 3 puntos
                # (marcado a mano por el usuario, ver tipo_segmento=SALTAR).
                code, end_frame = gen.generate_saltar(
                    slot_index, current_frame, points, today, _cur_rot)
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
                code, end_frame = gen.generate_parada(
                    slot_index, current_frame, points, today, _cur_rot,
                    frames_parada=frames_esta_parada)
                parada_idx += 1
            elif move_type == "picotear":
                # NUEVO (Kebyn, 2026-09-04): accion de campo, 1 coordenada.
                code, end_frame = gen.generate_picotear_1(
                    slot_index, current_frame, points, today, _cur_rot)
            elif move_type == "acicalarse":
                code, end_frame = gen.generate_acicalarse_1(
                    slot_index, current_frame, points, today, _cur_rot)
            elif move_type == "aletear":
                code, end_frame = gen.generate_aletear_1(
                    slot_index, current_frame, points, today, _cur_rot)
            elif move_type == "rascar":
                code, end_frame = gen.generate_rascar_1(
                    slot_index, current_frame, points, today, _cur_rot)
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
                    print(f"[Alfred preview] ERROR compilando slot {slot_index}: {_exec_err}")
                    import traceback; traceback.print_exc()
                    self.report({"ERROR"}, f"Error en slot {slot_index}: {_exec_err}")
                    return {"CANCELLED"}

                if "execute_animation" in slot_ns:
                    try:
                        slot_ns["execute_animation"](None)
                    except Exception as _run_err:
                        print(f"[Alfred preview] ERROR ejecutando slot {slot_index}: {_run_err}")
                        import traceback; traceback.print_exc()
                        self.report({"ERROR"}, f"Error ejecutando slot {slot_index}: {_run_err}")
                        return {"CANCELLED"}
                else:
                    print(f"[Alfred preview] ADVERTENCIA: slot {slot_index} no tiene execute_animation")

            if _da is not None:
                prev_rz = _da
            current_frame = end_frame + 1
            slot_index   += 1

        total_end = current_frame - 1

        # ── Reinyectar poses configuradas (de "Concatenar") sobre los slots base ──
        # Si existe la custom property "_concat_arm_data" en el objeto chicken_1,
        # significa que el usuario ejecuto "Concatenar" antes de este segundo
        # "Reproducir recorrido". Reinyectamos los keyframes de poses directamente
        # en los fcurves de los NLA tracks Slot_NNN_arm que cubren ese rango.
        import json as _json

        _chicken_1_root_obj = bpy.data.objects.get("chicken_1")
        _concat_arm_raw  = (_chicken_1_root_obj.get("_concat_arm_data")  if _chicken_1_root_obj else None)
        _concat_root_raw = (_chicken_1_root_obj.get("_concat_root_data") if _chicken_1_root_obj else None)

        if _concat_arm_raw:
            try:
                _concat_arm_data  = _json.loads(_concat_arm_raw)
                _concat_root_data = _json.loads(_concat_root_raw) if _concat_root_raw else {}
                _cf_start = int(_chicken_1_root_obj.get("_concat_frame_start", start_frame))
                _cf_end   = int(_chicken_1_root_obj.get("_concat_frame_end",   total_end))

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
                                    fc = ensure_fcurves(act).new(dp, index=arr_idx)
                                for frame_str, val in frames_vals.items():
                                    frame_i = int(frame_str)
                                    if overlap_s <= frame_i <= overlap_e:
                                        fc.keyframe_points.insert(frame_i, val,
                                            options={"FAST", "REPLACE"})
                                if fc.keyframe_points:
                                    fc.update()

                # Para el armature: reinyectar todos los canales (bones).
                _reinject_into_nla(arm_obj, _concat_arm_data, _cf_start, _cf_end)

                # Para el root (chicken_1 empty): reinyectar SOLO rotation_euler.
                # La location viene del recorrido (slots Slot_NNN_root) y NO debe
                # ser sobreescrita por las poses configuradas (que tienen pos=0,0,0).
                _reinject_into_nla(root_empty, _concat_root_data, _cf_start, _cf_end,
                                   skip_dp={"location"})

            except Exception as _reinj_err:
                print(f"[Alfred preview] ADVERTENCIA reinyeccion poses: {_reinj_err}")
                import traceback; traceback.print_exc()

        # ── Post-proceso: filtros organicos y oscilaciones ────────────────────
        # Estrategia: usamos bpy.ops.nla.bake para obtener una accion con todos
        # los valores reales evaluados (NLA resuelto). Luego aplicamos los filtros
        # sobre esa accion baked y la dejamos como animacion final.
        try:
            from . import operators_anim as _ops_anim
            _st  = context.scene.ch1st
            _org = _st.organic

            # Los filtros organicos y oscilaciones solo se aplican cuando ya
            # existe una configuracion de segmento concatenada (_concat_arm_data).
            # En la primera reproduccion (sin CONCATENAR previo) no se aplican.
            _chicken_1_root = bpy.data.objects.get("chicken_1")
            _has_concat  = bool(_chicken_1_root and _chicken_1_root.get("_concat_arm_data"))

            _needs_organic = _org.enabled and _has_concat
            _needs_osc     = (_has_concat and
                              hasattr(_st, "bone_oscillations") and
                              _st.bone_oscillations.enabled and
                              bool(_st.bone_oscillations.items))

            if _needs_organic or _needs_osc:
                BAKED_ACT_NAME = "_chicken_1_organic_baked"

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

                    print(f"[Alfred] Filtros organicos OK — {len(get_fcurves(baked_act))} fcurves, "
                          f"frames {start_frame}→{total_end}")
                else:
                    print("[Alfred] ADVERTENCIA: bake no produjo accion activa")

        except Exception as _org_err:
            print(f"[Alfred preview] ERROR filtros organicos: {_org_err}")
            import traceback; traceback.print_exc()

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

class CH1PR_OT_ResetPreview(Operator):
    bl_idname  = "ch1pr.reset_preview"
    bl_label   = "Reset recorrido"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_cancel(restore_frame=True)
        for obj_name, act_name in (
            ("chicken_1", "_chicken_1_preview_root"),
            ("Armature_chicken_1", "_chicken_1_preview_arm"),
            ("Armature_chicken_1", "_chicken_1_organic_baked"),
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
                _baked_act = bpy.data.actions.get("_chicken_1_organic_baked")
                if _baked_act and obj.animation_data and obj.animation_data.action == _baked_act:
                    obj.animation_data.action = None
                if _baked_act:
                    bpy.data.actions.remove(_baked_act, do_unlink=True)
        root = bpy.data.objects.get("chicken_1")
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

class CH1PR_OT_SetAnimRange(Operator):
    bl_idname  = "ch1pr.set_anim_range"
    bl_label   = "Fijar rango de animacion"
    bl_options = {"REGISTER", "UNDO"}

    frame_fin: bpy.props.IntProperty(
        name="Frame fin de animacion",
        default=1, min=1, soft_max=99999,
    )

    def invoke(self, context, event):
        pc = context.scene.ch1_path
        self.frame_fin = pc.anim_frame_fin if pc.anim_frame_fin > 0 else context.scene.frame_end
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        pc = context.scene.ch1_path
        if self.frame_fin <= pc.frame_inicio:
            self.report({"ERROR"}, f"Frame fin debe ser mayor que frame inicio")
            return {"CANCELLED"}
        pc.anim_frame_fin = self.frame_fin
        self.report({"INFO"}, f"Rango animacion: {pc.frame_inicio} → {self.frame_fin}")
        return {"FINISHED"}


# =============================================================================
# EXPORT SLOTS
# =============================================================================

class CH1PR_OT_ExportSlots(bpy.types.Operator):
    """Exporta los scripts de slots del recorrido de Alfred."""
    bl_idname  = "ch1pr.export_slots"
    bl_label   = "Exportar recorrido (slots)"
    bl_description = (
        "Genera los scripts de slots del recorrido en la carpeta de salida. "
        "Equivalente a ejecutar generate_slots.py"
    )
    bl_options = {"REGISTER"}

    def execute(self, context):
        import importlib.util as _ilu

        pc    = context.scene.ch1_path
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
        gen_path  = os.path.join(addon_dir, "generate_slots.py")
        if not os.path.exists(gen_path):
            self.report({"ERROR"},
                f"No se encontro generate_slots.py en {gen_path}.")
            return {"CANCELLED"}

        spec = _ilu.spec_from_file_location("gen_slots_alfred", gen_path)
        gen  = _ilu.module_from_spec(spec)
        spec.loader.exec_module(gen)

        today         = date.today().isoformat()
        root_rot      = (pc.root_rot_x, pc.root_rot_y, pc.root_rot_z)
        slot_index    = pc.slot_inicio
        current_frame = pc.frame_inicio

        # ── 1 COORDENADA: idle ───────────────────────────────────────────────
        if n_pts == 1:
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
                code = f"# slot_{slot_index:03d}_chicken_1_idle.py\n# Generado {today}\n"
            fname = f"slot_{slot_index:03d}_chicken_1_idle.py"
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
        expanded_pts, parada_frames_marcadas = _expand_points_with_paradas(pts)

        key_points = [
            {"index": i + 1,
             "coordinates": {"x": round(pt.coords[0], 4), "y": round(pt.coords[1], 4), "z": round(pt.coords[2], 4)},
             "texture": pt.texture or "grass_block_top",
             "face_index": pt.face_index if pt.face_index else str(i + 1),
             "tipo_marcado": getattr(pt, "tipo_segmento", "AUTO")}
            for i, pt in enumerate(expanded_pts)
        ]

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
                # BUGFIX (Kebyn, 2026-09-03): ver comentario identico en el
                # bloque de preview (CH1ST_OT_PlayRoute) mas arriba en este
                # archivo -- mismo desfase de heading al heredar rotacion
                # hacia el siguiente segmento, corregido igual aqui para que
                # preview y export queden consistentes.
                if move_type == "caminar":
                    _p0 = points[-2]["coordinates"]
                    _p1 = points[-1]["coordinates"]
                else:
                    _p0 = points[0]["coordinates"]
                    _p1 = points[-1]["coordinates"]
                _da = gen._compute_direction_angle(_p0, _p1)
            else:
                _da = None

            _cur_rot = (root_rot[0], root_rot[1], prev_rz_exp)

            if move_type == "saltar_subir":
                code, end_frame = gen.generate_saltar_subir(
                    slot_index, current_frame, points, today, _cur_rot)
                fname = f"slot_{slot_index:03d}_chicken_1_saltar_subir.py"
            elif move_type == "saltar_bajar":
                code, end_frame = gen.generate_saltar_bajar(
                    slot_index, current_frame, points, today, _cur_rot)
                fname = f"slot_{slot_index:03d}_chicken_1_saltar_bajar.py"
            elif move_type == "saltar":
                code, end_frame = gen.generate_saltar(
                    slot_index, current_frame, points, today, _cur_rot)
                fname = f"slot_{slot_index:03d}_chicken_1_saltar.py"
            elif move_type == "parada":
                if parada_idx < len(parada_frames_marcadas):
                    # Parada marcada por el usuario en el Paso 1.5 (opcional)
                    frames_esta_parada = parada_frames_marcadas[parada_idx]
                elif parada_idx < len(pc.paradas_frames):
                    frames_esta_parada = pc.paradas_frames[parada_idx].frames
                else:
                    frames_esta_parada = pc.frames_parada
                code, end_frame = gen.generate_parada(
                    slot_index, current_frame, points, today, _cur_rot,
                    frames_parada=frames_esta_parada)
                fname = f"slot_{slot_index:03d}_chicken_1_parada.py"
                parada_idx += 1
            elif move_type == "picotear":
                code, end_frame = gen.generate_picotear_1(
                    slot_index, current_frame, points, today, _cur_rot)
                fname = f"slot_{slot_index:03d}_chicken_1_picotear.py"
            elif move_type == "acicalarse":
                code, end_frame = gen.generate_acicalarse_1(
                    slot_index, current_frame, points, today, _cur_rot)
                fname = f"slot_{slot_index:03d}_chicken_1_acicalarse.py"
            elif move_type == "aletear":
                code, end_frame = gen.generate_aletear_1(
                    slot_index, current_frame, points, today, _cur_rot)
                fname = f"slot_{slot_index:03d}_chicken_1_aletear.py"
            elif move_type == "rascar":
                code, end_frame = gen.generate_rascar_1(
                    slot_index, current_frame, points, today, _cur_rot)
                fname = f"slot_{slot_index:03d}_chicken_1_rascar.py"
            else:
                walk_style_actual = (pc.walk_styles[caminar_idx].style
                                      if caminar_idx < len(pc.walk_styles) else pc.walk_style)
                code, end_frame = gen.generate_caminar(
                    slot_index, current_frame, points, today, _cur_rot,
                    walk_style=walk_style_actual)
                fname = f"slot_{slot_index:03d}_chicken_1_caminar.py"
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


# =============================================================================
# GENERA SLOTS (directo en escena, sin archivo intermedio)
# =============================================================================

class CH1PR_OT_GenerateSlots(Operator):
    """Genera y ejecuta slots directamente en la escena."""
    bl_idname  = "ch1pr.generate_slots"
    bl_label   = "Generar slots (InScene)"
    bl_options = {"REGISTER"}

    def execute(self, context):
        self.report({"INFO"}, "Usa 'Exportar recorrido' para generar los archivos .py")
        return {"FINISHED"}


# =============================================================================
# REGISTRO
# =============================================================================

pr_classes = (
    CH1PathPoint,
    CH1ParadaFrames,
    CH1WalkStyleEntry,
    CH1PathSettings,
    CH1PR_OT_ToggleRecording,
    CH1PR_OT_TogglePathViz,
    CH1PR_OT_RemoveLast,
    CH1PR_OT_ClearPath,
    CH1PR_OT_SyncParadasFrames,
    CH1PR_OT_GenerateSlots,
    CH1PR_OT_OpenBlendFile,
    CH1PR_OT_PreviewPath,
    CH1PR_OT_ResetPreview,
    CH1PR_OT_SetAnimRange,
    CH1PR_OT_ExportSlots,
)


def register_path_recorder_ch1():
    for cls in pr_classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
        bpy.utils.register_class(cls)
    bpy.types.Scene.ch1_path = bpy.props.PointerProperty(type=CH1PathSettings)
    if _chicken_1_face_selection_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_chicken_1_face_selection_handler)


def unregister_path_recorder_ch1():
    global _draw_handle
    if _draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
        _draw_handle = None
    if _chicken_1_face_selection_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_chicken_1_face_selection_handler)
    for cls in reversed(pr_classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
    if hasattr(bpy.types.Scene, "ch1_path"):
        del bpy.types.Scene.ch1_path