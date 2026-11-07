# -*- coding: utf-8 -*-
"""
properties.py — Cerdo_1 Animation Studio v1.8
PropertyGroups: Cerdo_1EyeExpressionSettings, Cerdo_1OrganicFilters,
Cerdo_1PoseSlotItem, Cerdo_1StudioSettings.
Tambien: helpers load_historia_json, get_key_points, _enum_*
"""
import bpy, json, os
from bpy.props import (
    StringProperty, IntProperty, FloatProperty,
    BoolProperty, EnumProperty,
    CollectionProperty, PointerProperty,
)
from bpy.types import PropertyGroup
from .constants import (
    DEFAULT_POSES_DIR, DEFAULT_ANIM_DIR, DEFAULT_HISTORIA_JSON, DEFAULT_CONFIG_DIR,
    DEFAULT_REGLAS_DIR, EXPRESSION_PRESETS, INTERP_TYPE_ITEMS,
    UNDERSTAND_DIRECTION_ITEMS,
)
# Ruta por defecto de la libreria de ojos (definida en eye_library para evitar ciclo)
_DEFAULT_EYE_LIB_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\cerdo_1\refinar\ojos"
)

# =============================================================================
# FUNCIONES DE UTILIDAD PARA PROPIEDADES
# =============================================================================

def load_historia_json(filepath):
    """Carga el JSON de historia completo. Devuelve el dict o {} si falla."""
    path = bpy.path.abspath(filepath)
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Cerdo_1Studio] No se pudo leer historia_cerdo_1.json: {e}")
        return {}

def get_key_points(historia_data):
    """Devuelve la lista de key_points del JSON de historia."""
    return historia_data.get("recorrido", {}).get("key_points", [])

def _enum_key_points(self, context):
    """Genera enum con los key_points del historia_cerdo_1.json."""
    st = context.scene.cerdo_1_st
    historia = load_historia_json(st.historia_json)
    kps = get_key_points(historia)
    if not kps:
        return [("0", "-- sin key_points (verifica ruta JSON) --", "")]
    items = []
    for kp in kps:
        idx  = kp.get("index", 0)
        co   = kp.get("coordinates", {})
        tex  = kp.get("texture", "?")
        label = f"[{idx}]  x={co.get('x',0):.1f}  y={co.get('y',0):.1f}  z={co.get('z',0):.1f}  ({tex})"
        items.append((str(idx), label, ""))
    return items

# =============================================================================
# PROPIEDADES
# =============================================================================

# ── Propiedades de configuracion de expresion de ojos ──
class Cerdo_1EyeExpressionSettings(PropertyGroup):
    """Configuracion del sistema de expresiones para mallas de ojos"""

    enabled: BoolProperty(
        name="Activar expresiones de ojos",
        description="Habilita el sistema de shape keys de expresion en las mallas de ojos",
        default=False,
    )

    # Intensidades por expresion
    intensity_feliz: FloatProperty(
        name="Intensidad Feliz", default=0.18, min=0.0, max=0.8, precision=3,
        description="Fuerza de la curva feliz (arco hacia arriba)",
    )
    intensity_triste: FloatProperty(
        name="Intensidad Triste", default=0.18, min=0.0, max=0.8, precision=3,
        description="Fuerza de la curva triste (arco hacia abajo)",
    )
    intensity_enojado: FloatProperty(
        name="Intensidad Enojo", default=0.18, min=0.0, max=0.8, precision=3,
        description="Fuerza de la diagonal de enojo",
    )
    intensity_sospecha: FloatProperty(
        name="Intensidad Sospecha", default=0.18, min=0.0, max=0.8, precision=3,
        description="Fuerza de la diagonal de sospecha",
    )

    curve_mode: EnumProperty(
        name="Curva",
        items=[
            ("QUADRATIC", "Cuadratica", "Suave"),
            ("LINEAR",    "Lineal",     "Rampa directa"),
            ("CUBIC",     "Cubica",     "Pronunciada"),
        ],
        default="QUADRATIC",
    )
    affect_zone: EnumProperty(
        name="Zona",
        items=[
            ("UPPER", "Superior", "Solo parte superior"),
            ("LOWER", "Inferior", "Solo parte inferior"),
            ("BOTH",  "Ambas",    "Ojo completo"),
        ],
        default="UPPER",
    )
    swap_axes: BoolProperty(
        name="Swap H/V", default=False,
        description="Intercambiar ejes horizontal y vertical si las curvas van al reves",
    )
    invert_vertical: BoolProperty(name="Inv Vertical", default=False)
    invert_horizontal: BoolProperty(name="Inv Horizontal", default=False)

    subdivide_cuts: IntProperty(
        name="Subdivisiones", default=3, min=0, max=5,
        description="Subdivisiones adicionales si la malla tiene muy pocos vertices",
    )

    # Expresion activa para preview
    active_expression: EnumProperty(
        name="Expresion activa",
        items=EXPRESSION_PRESETS,
        default="NEUTRAL",
        description="Expresion que se aplica al presionar Aplicar Preview",
    )

    # Valor del shape key de expresion activa (0 = neutral, 1 = max)
    expression_value: FloatProperty(
        name="Valor expresion", default=1.0, min=0.0, max=1.0, precision=2,
        description="Fuerza de la expresion activa (0=neutral, 1=maximo)",
    )

    # ── Sistema de parpadeo automatico (multi-intervalo) ─────────────────────
    blink_enabled: BoolProperty(
        name="Parpadeos automaticos", default=False,
        description="Habilita el sistema de parpadeo automatico por intervalos (efecto cortina)",
    )
    # Campos legacy de un solo rango — conservados para compatibilidad
    # con builds anteriores; los nuevos intervalos van en blink_intervals.
    blink_count: IntProperty(
        name="Numero de parpadeos", default=2, min=1, max=40,
        description="[Legacy] Parpadeos del primer intervalo si no se usa la lista",
    )
    blink_duration: IntProperty(
        name="Frames por parpadeo", default=9, min=5, max=30,
        description="[Legacy] Duracion del primer intervalo",
    )
    blink_frame_start: IntProperty(
        name="Frame inicio parpadeo", default=1, min=0,
        description="[Legacy] Frame inicio del primer intervalo",
    )
    blink_frame_end: IntProperty(
        name="Frame fin parpadeo", default=60, min=1,
        description="[Legacy] Frame fin del primer intervalo",
    )
    # ── Indice activo de la lista de intervalos de parpadeo ──────────────────
    blink_interval_idx: IntProperty(default=0)

    # ── Sistema de expresiones multi-intervalo ────────────────────────────────
    expr_intervals_enabled: BoolProperty(
        name="Expresiones por intervalos", default=False,
        description="Usa intervalos independientes de emocion en lugar de la secuencia lineal",
    )
    expr_interval_idx: IntProperty(default=0)

    # ── Sistema de "Reir" multi-intervalo (Kebyn, 2026-08-18: "agrega un
    # nuevo filtro dentro de los segmentos, el cual sera reir... oscilar
    # las mallas de los dos ojos en simultaneo de arriba hacia abajo")
    # Mismo criterio que blink_enabled/expr_intervals_enabled: el switch
    # maestro vive aca (global), pero la lista de intervalos en si es
    # PROPIA de cada segmento (ver Cerdo_1AnimSegment.laugh_intervals) --
    # asi cada segmento puede tener su propia cantidad/rango/oscilaciones
    # de "Reir", igual que ya pasa con Parpadeo y Expresiones.
    laugh_enabled: BoolProperty(
        name="Reir (oscilacion de ojos)", default=False,
        description="Habilita el filtro 'Reir': oscila ambas mallas de ojo en Z, "
                     "de forma sincronizada, por intervalos",
    )
    laugh_interval_idx: IntProperty(default=0)

    # ── Sistema de "Entendiendo" multi-intervalo (Kebyn, 2026-08-18: junto
    # al filtro "Reir", agrega "Entendiendo Izquierda"/"Entendiendo
    # Derecha" -- mueve ambos ojos en simultaneo trazando una parabola
    # entre 3 posiciones de referencia, Izquierda con un sentido y Derecha
    # en el sentido opuesto/espejo). Mismo criterio que laugh_enabled de
    # arriba: el switch maestro vive aca (global), la lista de intervalos
    # es PROPIA de cada segmento (ver Cerdo_1AnimSegment.understand_intervals).
    understand_enabled: BoolProperty(
        name="Entendiendo (glance de ojos)", default=False,
        description="Habilita el filtro 'Entendiendo': mueve ambas mallas de ojo "
                     "en simultaneo trazando una parabola X/Z hacia la izquierda "
                     "o hacia la derecha, por intervalos",
    )
    understand_interval_idx: IntProperty(default=0)

    # ── LIBRERIA: propiedades de timeline por expresion ──────────────────────
    lib_frame_start: IntProperty(
        name="Frame inicio", default=1, min=0,
        description="Frame de la timeline donde empieza esta expresion de ojos",
    )
    lib_duration: IntProperty(
        name="Duracion (frames)", default=20, min=1, soft_max=99999,
        description="Cuantos frames dura esta expresion de ojos. Sin limite superior.",
    )
    lib_interp_type: EnumProperty(
        name="Transicion",
        description="Tipo de interpolacion al entrar a esta expresion",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )

    # ── TRANSFORMS EDITABLES de las mallas de ojos ───────────────────────────
    # Coordenadas base = posicion correcta de los ojos en el rostro de Cerdo_1.
    # Cualquier cambio en el panel es un DELTA relativo a estas posiciones.
    # ojo_derecho_cerdo_1  base: (-0.1053,  0.256331, 1.70043)
    # ojo_izquierdo_cerdo_1 base: ( 0.106646, 0.270456, 1.70082)

    # Ojo izquierdo
    eye_L_loc_x: FloatProperty(name="Loc X",   default=0.106646, precision=4, description="Posicion X ojo izquierdo (base: 0.106646)")
    eye_L_loc_y: FloatProperty(name="Loc Y",   default=0.270456, precision=4, description="Posicion Y ojo izquierdo (base: 0.270456)")
    eye_L_loc_z: FloatProperty(name="Loc Z",   default=1.70082,  precision=4, description="Posicion Z ojo izquierdo (base: 1.70082)")
    eye_L_rot_x: FloatProperty(name="Rot X",   default=0.0, subtype="ANGLE", description="Rotacion X ojo izquierdo (grados)")
    eye_L_rot_y: FloatProperty(name="Rot Y",   default=0.0, subtype="ANGLE", description="Rotacion Y ojo izquierdo (grados)")
    eye_L_rot_z: FloatProperty(name="Rot Z",   default=0.0, subtype="ANGLE", description="Rotacion Z ojo izquierdo (grados)")
    eye_L_sca_x: FloatProperty(name="Sca X",   default=1.555,    min=0.001, max=10.0, precision=3, description="Escala X ojo izquierdo")
    eye_L_sca_y: FloatProperty(name="Sca Y",   default=0.496018, min=0.001, max=10.0, precision=3, description="Escala Y ojo izquierdo")
    eye_L_sca_z: FloatProperty(name="Sca Z",   default=3.55,     min=0.001, max=10.0, precision=3, description="Escala Z ojo izquierdo")

    # Ojo derecho
    eye_R_loc_x: FloatProperty(name="Loc X",   default=-0.1053,   precision=4, description="Posicion X ojo derecho (base: -0.1053)")
    eye_R_loc_y: FloatProperty(name="Loc Y",   default=0.256331,  precision=4, description="Posicion Y ojo derecho (base: 0.256331)")
    eye_R_loc_z: FloatProperty(name="Loc Z",   default=1.70043,   precision=4, description="Posicion Z ojo derecho (base: 1.70043)")
    eye_R_rot_x: FloatProperty(name="Rot X",   default=0.0, subtype="ANGLE", description="Rotacion X ojo derecho (grados)")
    eye_R_rot_y: FloatProperty(name="Rot Y",   default=0.0, subtype="ANGLE", description="Rotacion Y ojo derecho (grados)")
    eye_R_rot_z: FloatProperty(name="Rot Z",   default=0.0, subtype="ANGLE", description="Rotacion Z ojo derecho (grados)")
    eye_R_sca_x: FloatProperty(name="Sca X",   default=1.555,    min=0.001, max=10.0, precision=3, description="Escala X ojo derecho")
    eye_R_sca_y: FloatProperty(name="Sca Y",   default=0.496018, min=0.001, max=10.0, precision=3, description="Escala Y ojo derecho")
    eye_R_sca_z: FloatProperty(name="Sca Z",   default=3.55,     min=0.001, max=10.0, precision=3, description="Escala Z ojo derecho")

    # ── Modo de edicion de geometria ─────────────────────────────────────────
    geo_edit_mode: EnumProperty(
        name="Forma de ojo",
        description="Tipo de geometria/forma que tendra el ojo",
        items=[
            ("NONE",     "Sin cambio",    "Mantiene la forma original de la malla"),
            ("ROUND",    "Redondo",       "Ojos redondeados (sorpresa, asombro)"),
            ("SQUINT",   "Entrecerrado",  "Aplana verticalmente el ojo (sospecha, cansancio)"),
            ("WIDE",     "Abierto ancho", "Expande horizontalmente el ojo"),
            ("FLAT",     "Plano/cerrado", "Aplana el ojo completamente (cerrado)"),
            ("CUSTOM",   "Personalizado", "Usa el valor de shape key activo como geometria"),
        ],
        default="NONE",
    )
    geo_intensity: FloatProperty(
        name="Intensidad forma",
        default=1.0, min=0.0, max=2.0, precision=2,
        description="Cuanto se aplica la forma de geometria seleccionada",
    )




class Cerdo_1BlinkInterval(PropertyGroup):
    """
    Un intervalo independiente de parpadeo automatico.
    El sistema de parpadeo puede tener N intervalos en la misma timeline,
    cada uno con su propio rango de frames, numero de parpadeos y duracion.
    """
    label: StringProperty(
        name="Etiqueta",
        default="Parpadeo",
        description="Nombre descriptivo del intervalo de parpadeo",
    )
    frame_start: IntProperty(
        name="Frame inicio",
        default=1, min=0,
        description="Frame a partir del cual inician los parpadeos de este intervalo",
    )
    frame_end: IntProperty(
        name="Frame fin",
        default=60, min=1,
        description="Frame hasta el cual se distribuyen los parpadeos de este intervalo",
    )
    blink_count: IntProperty(
        name="N° parpadeos",
        default=1, min=1, max=40,
        description="Cuantos parpadeos se distribuyen dentro del rango de este intervalo",
    )
    blink_duration: IntProperty(
        name="Frames/parpadeo",
        default=9, min=5, max=30,
        description="Frames que dura un ciclo completo de parpadeo (cierre + apertura)",
    )
    enabled: BoolProperty(
        name="Activo",
        default=True,
        description="Si esta desactivado, este intervalo se ignora al ejecutar CONCATENAR_2",
    )


class Cerdo_1LaughInterval(PropertyGroup):
    """
    Un intervalo independiente del filtro "Reir": ambas mallas de ojo
    (ojo_izquierdo_cerdo_1, ojo_derecho_cerdo_1) oscilan en Z de forma
    SINCRONIZADA -- EXCLUSIVAMENTE entre la posicion alta y la posicion
    baja (sin pasar por la base intermedia; ajustado a pedido de Kebyn,
    2026-08-18: "solo debe oscilar entre Z=1.73 y Z=1.66") -- N veces
    dentro del rango de frames de este intervalo. Mismo criterio de lista
    multi-intervalo que Cerdo_1BlinkInterval / Cerdo_1EyeExprInterval
    ("crear intervalos donde se escogera el frame de inicio y frame final
    de la oscilacion y numero de oscilaciones... al crearse varios
    intervalos estos se acomodaran en una lista").

    Los valores de Z (alta/baja) NO se editan por intervalo -- son
    constantes fijas calibradas sobre la geometria real de Cerdo_1 (ver
    constants.EYE_LAUGH_Z_HIGH/EYE_LAUGH_Z_LOW). Lo unico editable por
    intervalo es CUANDO (frame_start/frame_end) y CUANTAS veces oscila.
    """
    label: StringProperty(
        name="Etiqueta",
        default="Reir",
        description="Nombre descriptivo de este intervalo de oscilacion",
    )
    frame_start: IntProperty(
        name="Frame inicio",
        default=1, min=0,
        description="Frame en el que inicia la oscilacion de este intervalo",
    )
    frame_end: IntProperty(
        name="Frame fin",
        default=30, min=1,
        description="Frame en el que termina la oscilacion de este intervalo",
    )
    oscillation_count: IntProperty(
        name="N° oscilaciones",
        default=3, min=1, max=60,
        description="Cuantos ciclos completos (sube a la posicion alta, baja a la "
                     "posicion baja y vuelve a la base) se distribuyen dentro de "
                     "este rango de frames",
    )
    enabled: BoolProperty(
        name="Activo",
        default=True,
        description="Si esta desactivado, este intervalo se ignora al ejecutar CONCATENAR_2",
    )


class Cerdo_1UnderstandInterval(PropertyGroup):
    """
    Un intervalo independiente del filtro "Entendiendo": ambas mallas de
    ojo (ojo_izquierdo_cerdo_1, ojo_derecho_cerdo_1) se mueven EN SIMULTANEO
    trazando una parabola X/Z -- Base (frame_start) -> Apice (frame medio,
    Z mas alta) -> Destino (frame_end, Z de vuelta a la base, X mas
    desplazada que en el apice) -- exactamente la secuencia de 3
    posiciones capturadas en Blender (Kebyn, 2026-08-18). Mismo criterio
    de lista multi-intervalo que Cerdo_1LaughInterval.

    Los deltas de X/Z (apice/destino) NO se editan por intervalo -- son
    constantes fijas calibradas sobre la geometria real de Cerdo_1 (ver
    constants.EYE_UNDERSTAND_APEX_DX/DZ, EYE_UNDERSTAND_END_DX/DZ). Lo
    unico editable por intervalo es CUANDO (frame_start/frame_end) y
    hacia que lado (direction: Izquierda/Derecha, este ultimo es el
    espejo horizontal exacto del primero).
    """
    label: StringProperty(
        name="Etiqueta",
        default="Entendiendo",
        description="Nombre descriptivo de este intervalo de glance",
    )
    frame_start: IntProperty(
        name="Frame inicio",
        default=1, min=0,
        description="Frame en el que inicia el glance de este intervalo (posicion base)",
    )
    frame_end: IntProperty(
        name="Frame fin",
        default=30, min=1,
        description="Frame en el que termina el glance de este intervalo (posicion destino)",
    )
    direction: EnumProperty(
        name="Direccion",
        description="Hacia que lado glancean ambos ojos",
        items=UNDERSTAND_DIRECTION_ITEMS,
        default="IZQUIERDA",
    )
    enabled: BoolProperty(
        name="Activo",
        default=True,
        description="Si esta desactivado, este intervalo se ignora al ejecutar CONCATENAR_2",
    )


class Cerdo_1EyeExprInterval(PropertyGroup):
    """
    Un intervalo de expresion de ojos en la timeline.
    Cada intervalo define tres fases: Inicio (neutral) → Pico (expresion) → Fin (neutral),
    pero el usuario solo controla cuantos frames dura el intervalo completo -- el inicio
    se encadena automaticamente despues del intervalo anterior (mismo criterio que los
    "Slots de ojos"/Cerdo_1EyeSlotItem), y el pico se ubica a la mitad de la duracion.
    En una misma animacion pueden coexistir multiples intervalos con distintas emociones.
    """
    label: StringProperty(
        name="Etiqueta",
        default="Expresion",
        description="Nombre descriptivo de este intervalo de expresion",
    )
    duration: IntProperty(
        name="Frames",
        default=40, min=2, soft_max=99999,
        description="Cuantos frames dura esta expresion (entrada + pico + salida). "
                     "Se encadena automaticamente despues del intervalo anterior",
    )
    expression: EnumProperty(
        name="Expresion",
        items=EXPRESSION_PRESETS,
        default="NEUTRAL",
        description="Emocion que se expresa durante el pico de este intervalo",
    )
    # LIMITE (Kebyn, 2026-08-04: "por defecto pon que la maxima intensidad
    # de la expresion sera 0.06"): mismo criterio ya usado en
    # CERDO_1_ST_OT_EditEyeSlot.expression_value (default=max=0.05) -- el rango
    # completo 0..1 dejaba expresiones excesivamente exageradas en los ojos
    # de Cerdo_1. Se limita el maximo (y el valor por defecto de intervalos
    # nuevos) a 0.06.
    expression_value: FloatProperty(
        name="Intensidad",
        default=0.06, min=0.0, max=0.06, precision=3,
        description="Fuerza maxima de la expresion en el frame pico (0=neutral, 0.06=maximo)",
    )
    interp_in: EnumProperty(
        name="Interpolacion entrada",
        description="Interpolacion de la transicion neutral → expresion",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )
    interp_out: EnumProperty(
        name="Interpolacion salida",
        description="Interpolacion de la transicion expresion → neutral",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )
    enabled: BoolProperty(
        name="Activo",
        default=True,
        description="Si esta desactivado, este intervalo se ignora al ejecutar CONCATENAR_2",
    )

    # ── FRAME DE INICIO ABSOLUTO (Kebyn, 2026-09-06: "asi como el sistema
    # de poses de cada segmento tiene un sistema que identifica a partir de
    # que frame una pose se mostrara, necesito que lo agreges tambien al
    # sistema de ojos") — mismo esquema exacto que Cerdo_1SegmentPoseSlot.
    # frame_abs_start / manual_start (properties.py, seccion "PASO 3: SLOT
    # DE POSE"): por defecto (manual_start=False) el frame de inicio se
    # sigue encadenando automaticamente tras el intervalo anterior (cursor
    # de siempre); si el usuario fija manual_start=True, frame_abs_start se
    # usa tal cual (siempre que no invada al intervalo anterior -- ver
    # resolve_pose_start_frames en pose_utils.py, reutilizada tal cual para
    # expr_intervals). frame_abs_start se recalcula/escribe en cada
    # Concatenar para que el panel siempre muestre el valor real vigente.
    frame_abs_start: IntProperty(name="Frame inicio absoluto", default=0)
    manual_start: BoolProperty(
        name="Frame de inicio manual",
        default=False,
        description=(
            "Si esta activo, 'Frame inicio absoluto' se usa tal cual en vez "
            "de calcularse automaticamente tras la expresion anterior."
        ),
    )

    # ── TRANSFORMS EDITABLES por intervalo (Kebyn, 2026-08-04: "agrega el
    # boton editar expresion con el cual se podra editar la rotacion,
    # posicion, escala de cada ojo") ──────────────────────────────────────
    # Mismo esquema que Cerdo_1EyeSlotItem / Cerdo_1EyeExpressionSettings:
    # valores BASE = posicion correcta de los ojos en el rostro de Cerdo_1
    # (ver constants.EYE_BASE_TRANSFORMS). En el frame pico de este
    # intervalo se aplican estos valores; en frame_start/frame_end se
    # vuelve a la posicion base, igual que la intensidad de la expresion.
    eye_L_loc_x: FloatProperty(name="Loc X", default=0.106646, precision=4, description="Posicion X ojo izquierdo (base: 0.106646)")
    eye_L_loc_y: FloatProperty(name="Loc Y", default=0.270456, precision=4, description="Posicion Y ojo izquierdo (base: 0.270456)")
    eye_L_loc_z: FloatProperty(name="Loc Z", default=1.70082,  precision=4, description="Posicion Z ojo izquierdo (base: 1.70082)")
    eye_L_rot_x: FloatProperty(name="Rot X", default=0.0, subtype="ANGLE", description="Rotacion X ojo izquierdo")
    eye_L_rot_y: FloatProperty(name="Rot Y", default=0.0, subtype="ANGLE", description="Rotacion Y ojo izquierdo")
    eye_L_rot_z: FloatProperty(name="Rot Z", default=0.0, subtype="ANGLE", description="Rotacion Z ojo izquierdo")
    eye_L_sca_x: FloatProperty(name="Sca X", default=1.555,    min=0.001, max=10.0, precision=3, description="Escala X ojo izquierdo")
    eye_L_sca_y: FloatProperty(name="Sca Y", default=0.496018, min=0.001, max=10.0, precision=3, description="Escala Y ojo izquierdo")
    eye_L_sca_z: FloatProperty(name="Sca Z", default=3.55,     min=0.001, max=10.0, precision=3, description="Escala Z ojo izquierdo")

    eye_R_loc_x: FloatProperty(name="Loc X", default=-0.1053,   precision=4, description="Posicion X ojo derecho (base: -0.1053)")
    eye_R_loc_y: FloatProperty(name="Loc Y", default=0.256331,  precision=4, description="Posicion Y ojo derecho (base: 0.256331)")
    eye_R_loc_z: FloatProperty(name="Loc Z", default=1.70043,   precision=4, description="Posicion Z ojo derecho (base: 1.70043)")
    eye_R_rot_x: FloatProperty(name="Rot X", default=0.0, subtype="ANGLE", description="Rotacion X ojo derecho")
    eye_R_rot_y: FloatProperty(name="Rot Y", default=0.0, subtype="ANGLE", description="Rotacion Y ojo derecho")
    eye_R_rot_z: FloatProperty(name="Rot Z", default=0.0, subtype="ANGLE", description="Rotacion Z ojo derecho")
    eye_R_sca_x: FloatProperty(name="Sca X", default=1.555,    min=0.001, max=10.0, precision=3, description="Escala X ojo derecho")
    eye_R_sca_y: FloatProperty(name="Sca Y", default=0.496018, min=0.001, max=10.0, precision=3, description="Escala Y ojo derecho")
    eye_R_sca_z: FloatProperty(name="Sca Z", default=3.55,     min=0.001, max=10.0, precision=3, description="Escala Z ojo derecho")

    # ── Setup de Shape Keys de ojos PROPIO de esta expresion (Kebyn,
    # 2026-08-18: "todas las expresiones estan compartiendo el mismo setup
    # de shape keys de ojos... quiero que en una expresion sea Ambas, pero
    # la siguiente expresion sea solo Arriba... has que cada expresion
    # tenga su propia setup de shape keys de ojos") ─────────────────────
    # ANTES: dentro de un mismo segmento, TODAS las expresiones (seg.
    # expr_intervals) generaban su influencia sobre el MISMO juego de
    # shape keys geometricos -- el generado una sola vez por segmento con
    # seg.eye_shapekey (Zona/Curva/Subdivisiones/Swap/Inv/Intensidades).
    # Cambiar "Zona" no era posible por-expresion: afectaba a todas las
    # expresiones de ese segmento por igual.
    # AHORA: use_own_shapekey (abajo, default False = retrocompatible)
    # permite que ESTA expresion, en vez de heredar seg.eye_shapekey, use
    # su propia instancia independiente (own_shapekey, PointerProperty
    # asignado despues de definir Cerdo_1EyeShapeKeySetup mas abajo). El
    # consumidor (operators_anim.py / operators_segments.py) genera un
    # juego de shape keys con sufijo propio y unico para cada expresion
    # que active este flag (ver _ei_suffix = f"{seg_suffix}_ei{idx}"),
    # completamente independiente de las demas expresiones del segmento y
    # del juego compartido del segmento.
    use_own_shapekey: BoolProperty(
        name="Setup de Shape Keys de ojos (propio de esta expresion)",
        default=False,
        description="Si esta activo, ESTA expresion usa su propia configuracion de "
                     "Shape Keys (Subdivisiones/Swap/Inv/Zona/Curva/Intensidades), "
                     "independiente de las demas expresiones y del segmento. Si esta "
                     "desactivado (por defecto), hereda la configuracion del segmento "
                     "-- mismo comportamiento que antes de este flag",
    )


# ── AISLAMIENTO POR SEGMENTO -- Setup de Shape Keys de ojos (Kebyn +
# Claude, 2026-08-05) ────────────────────────────────────────────────────
# MISMO problema que ya se habia corregido para blink_intervals (2026-08-03)
# y expr_intervals (2026-08-04): el box "Setup de Shape Keys de ojos" que
# se dibuja dentro de CADA segmento (Subdivisiones previas, Swap H/V,
# Inv V, Inv H, Zona, Curva) seguia leyendo/escribiendo scene.cerdo_1_st.
# eye_expr -- una unica instancia GLOBAL compartida por todos los
# segmentos. Resultado: elegir "Zona: Superior" en un segmento cambiaba
# ese mismo valor para TODOS los segmentos, porque en realidad todos
# apuntaban al mismo dato. Esta PropertyGroup es la version aislada,
# una instancia PROPIA por Cerdo_1AnimSegment (ver eye_shapekey abajo).
class Cerdo_1EyeShapeKeySetup(PropertyGroup):
    """
    Configuracion de generacion geometrica de shape keys de ojos
    (Subdivisiones/Swap/Inv V/Inv H/Zona/Curva), propia de un segmento.
    Independiente de Cerdo_1EyeExpressionSettings.eye_expr (global, usada
    por INICIO/FIN -- panel "2b Secuencia de Ojos" -- que sigue siendo
    una sola pasada global sobre toda la timeline).
    """
    curve_mode: EnumProperty(
        name="Curva",
        items=[
            ("QUADRATIC", "Cuadratica", "Suave"),
            ("LINEAR",    "Lineal",     "Rampa directa"),
            ("CUBIC",     "Cubica",     "Pronunciada"),
        ],
        default="QUADRATIC",
    )
    affect_zone: EnumProperty(
        name="Zona",
        items=[
            ("UPPER", "Superior", "Solo parte superior"),
            ("LOWER", "Inferior", "Solo parte inferior"),
            ("BOTH",  "Ambas",    "Ojo completo"),
        ],
        default="UPPER",
    )
    swap_axes: BoolProperty(
        name="Swap H/V", default=False,
        description="Intercambiar ejes horizontal y vertical si las curvas van al reves",
    )
    invert_vertical: BoolProperty(name="Inv Vertical", default=False)
    invert_horizontal: BoolProperty(name="Inv Horizontal", default=False)
    subdivide_cuts: IntProperty(
        name="Subdivisiones", default=3, min=0, max=5,
        description="Subdivisiones adicionales si la malla tiene muy pocos vertices",
    )
    # Intensidades propias del segmento -- el bloque de shape keys de este
    # segmento se genera con sus propios valores, sin depender de
    # scene.cerdo_1_st.eye_expr.intensity_*.
    intensity_feliz: FloatProperty(
        name="Intensidad Feliz", default=0.18, min=0.0, max=0.8, precision=3,
    )
    intensity_triste: FloatProperty(
        name="Intensidad Triste", default=0.18, min=0.0, max=0.8, precision=3,
    )
    intensity_enojado: FloatProperty(
        name="Intensidad Enojo", default=0.18, min=0.0, max=0.8, precision=3,
    )
    intensity_sospecha: FloatProperty(
        name="Intensidad Sospecha", default=0.18, min=0.0, max=0.8, precision=3,
    )

    # ── Migracion desde el panel global (Kebyn + Claude, 2026-08-05) ──────
    # Al recien crearse esta PropertyGroup, cada segmento arranca con los
    # VALORES DE FABRICA de arriba (Inv V=False, Zona=Superior, etc.), no
    # con los valores que el usuario ya tenia calibrados en el panel global
    # "2b Secuencia de Ojos" (scene.cerdo_1_st.eye_expr) -- eso invertia
    # visualmente las expresiones (ej. "triste" se veia como "feliz") en
    # cuanto el aislamiento por segmento entro en vigor, porque cada
    # segmento paso a usar sus propios defaults en vez de la config ya
    # ajustada. Este flag evita que la migracion de "copiar los valores
    # actuales del panel global" se repita mas de una vez por segmento
    # (una vez que el usuario edita el segmento, sus cambios ya no deben
    # ser pisados).
    migrated_from_global: BoolProperty(default=False)


# Asignada aca (despues de la definicion de Cerdo_1EyeShapeKeySetup, y de
# Cerdo_1EyeExprInterval mas arriba) en vez de como anotacion dentro del
# cuerpo de la clase -- Cerdo_1EyeExprInterval se define ANTES que
# Cerdo_1EyeShapeKeySetup en este archivo, asi que un PointerProperty
# apuntando a ella no podia declararse ahi directamente.
#
# CORRECCION (Kebyn + Claude, 2026-08-20): el patron anterior
# `Cerdo_1EyeExprInterval.own_shapekey = PointerProperty(...)` asignaba un
# atributo de clase Python normal, PERO bpy.utils.register_class() SOLO
# busca propiedades RNA dentro de cls.__annotations__ -- no en atributos
# sueltos del __dict__ de la clase. El truco de "asignar despues de
# definir la clase" SI funciona para tipos ya registrados por Blender
# (bpy.types.Scene, bpy.types.Object, etc.) porque esos tienen un
# __setattr__ especial que registra la propiedad al vuelo en la RNA; NO
# funciona igual para un PropertyGroup propio que todavia no paso por
# register_class. Resultado: la propiedad nunca se registraba como RNA, y
# `ei.own_shapekey` devolvia el objeto _PropertyDeferred crudo (sin
# instanciar) en vez de una instancia de Cerdo_1EyeShapeKeySetup, causando
# AttributeError: '_PropertyDeferred' object has no attribute 'curve_mode'
# al guardar/leer configuracion. Fix: inyectar la propiedad directamente
# en __annotations__ (que es donde register_class() realmente la busca),
# en vez de como atributo de clase.
Cerdo_1EyeExprInterval.__annotations__["own_shapekey"] = PointerProperty(type=Cerdo_1EyeShapeKeySetup)


def ensure_eye_shapekey_migrated(seg, scene):
    """
    Si seg.eye_shapekey todavia no fue migrado desde el panel global (ver
    Cerdo_1EyeShapeKeySetup.migrated_from_global), copia ahi los valores
    ACTUALES de scene.cerdo_1_st.eye_expr -- asi el segmento arranca viendose
    igual que antes del aislamiento por segmento (2026-08-05), en vez de
    resetearse a los defaults de fabrica. Idempotente: no hace nada si ya
    se migro o si edita el segmento despues.
    """
    sk = getattr(seg, "eye_shapekey", None)
    if sk is None or sk.migrated_from_global:
        return
    st = getattr(scene, "cerdo_1_st", None)
    eye_s = getattr(st, "eye_expr", None) if st is not None else None
    if eye_s is not None:
        for a in ("curve_mode", "affect_zone", "swap_axes",
                  "invert_vertical", "invert_horizontal", "subdivide_cuts",
                  "intensity_feliz", "intensity_triste",
                  "intensity_enojado", "intensity_sospecha"):
            try:
                setattr(sk, a, getattr(eye_s, a))
            except Exception:
                pass
    try:
        sk.migrated_from_global = True
    except AttributeError:
        # Puede fallar si se llama desde un contexto restringido (p.ej.
        # dentro de un panel draw() mientras corre un operador largo como
        # "Concatenar", que fuerza redibujados de la UI). En ese caso no
        # pasa nada grave: los valores ya se copiaron arriba, y el flag
        # se terminara de persistir la proxima vez que esta funcion se
        # llame desde un contexto valido (p.ej. los operadores que ya la
        # invocan en operators_segments.py y operators_anim.py).
        pass


def ensure_expr_interval_shapekey_independent(seg):
    """
    ELIMINACION DEL MODO COMPARTIDO (Kebyn, 2026-09-05: "cada setup de
    shape keys de ojos debe ser independiente para cada expresion... que
    no sea para todas las expresiones de la lista"): antes, una expresion
    de seg.expr_intervals podia heredar seg.eye_shapekey (el setup UNICO
    compartido por TODO el segmento) si use_own_shapekey estaba en False
    -- el checkbox "Setup de Shape Keys de ojos (propio de esta expresion)"
    exigia activarlo a mano, expresion por expresion. Ahora TODA expresion
    usa siempre su propio setup independiente (ei.own_shapekey), sin
    opcion de heredar.

    Migra cada intervalo UNA sola vez (idempotente via el flag
    own_shapekey.migrated_from_global, reutilizado aca con el sentido "ya
    tiene su copia propia independiente"): copia los valores EFECTIVOS que
    tenia hasta ahora (los propios si ya usaba use_own_shapekey=True; si
    no, los de seg.eye_shapekey) para que el aspecto visual no cambie de
    golpe al activar esta migracion, y fuerza use_own_shapekey=True de
    forma permanente. Expresiones nuevas (own_shapekey recien creado, sin
    migrar) tambien quedan cubiertas: heredan como punto de partida los
    valores actuales de seg.eye_shapekey, pero ya en su propia copia
    independiente -- editarlas de ahi en mas no afecta a ninguna otra.
    """
    seg_sk = getattr(seg, "eye_shapekey", None)
    for ei in getattr(seg, "expr_intervals", []):
        own = getattr(ei, "own_shapekey", None)
        if own is None:
            continue
        if own.migrated_from_global:
            # Ya tiene su copia propia -- solo asegurar que quede forzado
            # a independiente (por si algun JSON viejo cargo use_own_shapekey=False).
            try:
                ei.use_own_shapekey = True
            except AttributeError:
                pass
            continue
        was_independent = getattr(ei, "use_own_shapekey", False)
        source = own if was_independent else seg_sk
        if source is not None:
            for a in ("curve_mode", "affect_zone", "swap_axes",
                      "invert_vertical", "invert_horizontal", "subdivide_cuts",
                      "intensity_feliz", "intensity_triste",
                      "intensity_enojado", "intensity_sospecha"):
                try:
                    setattr(own, a, getattr(source, a))
                except Exception:
                    pass
        try:
            own.migrated_from_global = True
        except AttributeError:
            # Mismo caso de contexto restringido documentado en
            # ensure_eye_shapekey_migrated -- no es grave, se reintenta la
            # proxima vez que se llame desde un contexto valido.
            pass
        try:
            ei.use_own_shapekey = True
        except AttributeError:
            # BUGFIX (Kebyn, 2026-09-05: "Writing to ID classes in this
            # context is not allowed" al dibujar el panel): panels.draw()
            # corre en un contexto restringido de Blender donde escribir
            # propiedades de datos de la escena esta prohibido. Igual que
            # el flag de arriba, no es grave -- los valores ya se
            # copiaron (o ya estaban) y esta bandera se termina de
            # persistir la proxima vez que la funcion se llame desde un
            # contexto valido (los operadores de concatenar, que ya la
            # invocan en operators_anim.py y operators_segments.py).
            pass


class Cerdo_1EyeLibEntry(PropertyGroup):
    """Entrada de la lista de expresiones de la libreria de ojos"""
    name:     StringProperty(name="Nombre")
    filepath: StringProperty(name="Ruta JSON")


# =============================================================================
# SLOT DE CONFIGURACION DE OJOS  (espejo de Cerdo_1PoseSlotItem para poses)
# =============================================================================

class Cerdo_1EyeSlotItem(PropertyGroup):
    """
    Un estado/configuracion de ojos intermedio dentro de la secuencia.
    Equivalente a Cerdo_1PoseSlotItem pero para los parametros de las mallas de ojos.
    """
    slot_label: StringProperty(
        name="Etiqueta",
        default="Estado ojos",
        description="Nombre descriptivo de este estado de ojos",
    )
    duration: IntProperty(
        name="Frames",
        default=20, min=1, soft_max=99999,
        description="Cuantos frames dura este estado de ojos. Sin limite superior.",
    )
    interp_type: EnumProperty(
        name="Transicion",
        description="Tipo de interpolacion desde el estado anterior a este",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )

    # ── Expresion de shape key ────────────────────────────────────────────────
    active_expression: EnumProperty(
        name="Expresion",
        items=EXPRESSION_PRESETS,
        default="NEUTRAL",
        description="Expresion de los ojos en este estado",
    )
    expression_value: FloatProperty(
        name="Valor expresion",
        default=0.05, min=0.0, max=0.05, precision=2,
        description="Intensidad de la expresion (0=neutral, 0.05=maximo)",
    )

    # ── Geometria / Forma ─────────────────────────────────────────────────────
    geo_edit_mode: EnumProperty(
        name="Forma de ojo",
        description="Tipo de geometria/forma que tendra el ojo en este estado",
        items=[
            ("NONE",   "Sin cambio",    "Mantiene la forma original de la malla"),
            ("ROUND",  "Redondo",       "Ojos redondeados (sorpresa, asombro)"),
            ("SQUINT", "Entrecerrado",  "Aplana verticalmente el ojo"),
            ("WIDE",   "Abierto ancho", "Expande horizontalmente el ojo"),
            ("FLAT",   "Plano/cerrado", "Aplana el ojo completamente"),
            ("CUSTOM", "Personalizado", "Usa el shape key activo como geometria"),
        ],
        default="NONE",
    )
    geo_intensity: FloatProperty(
        name="Intensidad forma",
        default=1.0, min=0.0, max=2.0, precision=2,
        description="Cuanto se aplica la forma geometrica seleccionada",
    )

    # ── Posicion (Location) ojo Izquierdo ─────────────────────────────────────
    eye_L_loc_x: FloatProperty(name="Loc X", default=0.106646, precision=4,
        description="Posicion X ojo izquierdo")
    eye_L_loc_y: FloatProperty(name="Loc Y", default=0.270456, precision=4,
        description="Posicion Y ojo izquierdo")
    eye_L_loc_z: FloatProperty(name="Loc Z", default=1.70082,  precision=4,
        description="Posicion Z ojo izquierdo")

    # ── Rotacion ojo Izquierdo ────────────────────────────────────────────────
    eye_L_rot_x: FloatProperty(name="Rot X", default=0.0, subtype="ANGLE",
        description="Rotacion X ojo izquierdo")
    eye_L_rot_y: FloatProperty(name="Rot Y", default=0.0, subtype="ANGLE",
        description="Rotacion Y ojo izquierdo")
    eye_L_rot_z: FloatProperty(name="Rot Z", default=0.0, subtype="ANGLE",
        description="Rotacion Z ojo izquierdo")

    # ── Escala ojo Izquierdo ──────────────────────────────────────────────────
    eye_L_sca_x: FloatProperty(name="Sca X", default=1.555,    min=0.001, max=10.0, precision=3,
        description="Escala X ojo izquierdo")
    eye_L_sca_y: FloatProperty(name="Sca Y", default=0.496018, min=0.001, max=10.0, precision=3,
        description="Escala Y ojo izquierdo")
    eye_L_sca_z: FloatProperty(name="Sca Z", default=3.55,     min=0.001, max=10.0, precision=3,
        description="Escala Z ojo izquierdo")

    # ── Posicion (Location) ojo Derecho ───────────────────────────────────────
    eye_R_loc_x: FloatProperty(name="Loc X", default=-0.1053,  precision=4,
        description="Posicion X ojo derecho")
    eye_R_loc_y: FloatProperty(name="Loc Y", default=0.256331, precision=4,
        description="Posicion Y ojo derecho")
    eye_R_loc_z: FloatProperty(name="Loc Z", default=1.70043,  precision=4,
        description="Posicion Z ojo derecho")

    # ── Rotacion ojo Derecho ──────────────────────────────────────────────────
    eye_R_rot_x: FloatProperty(name="Rot X", default=0.0, subtype="ANGLE",
        description="Rotacion X ojo derecho")
    eye_R_rot_y: FloatProperty(name="Rot Y", default=0.0, subtype="ANGLE",
        description="Rotacion Y ojo derecho")
    eye_R_rot_z: FloatProperty(name="Rot Z", default=0.0, subtype="ANGLE",
        description="Rotacion Z ojo derecho")

    # ── Escala ojo Derecho ────────────────────────────────────────────────────
    eye_R_sca_x: FloatProperty(name="Sca X", default=1.555,    min=0.001, max=10.0, precision=3,
        description="Escala X ojo derecho")
    eye_R_sca_y: FloatProperty(name="Sca Y", default=0.496018, min=0.001, max=10.0, precision=3,
        description="Escala Y ojo derecho")
    eye_R_sca_z: FloatProperty(name="Sca Z", default=3.55,     min=0.001, max=10.0, precision=3,
        description="Escala Z ojo derecho")


class Cerdo_1PoseSlotItem(PropertyGroup):
    pose_name:  StringProperty(name="Pose")
    pose_label: StringProperty(name="Etiqueta", default="")
    json_file:  StringProperty(name="JSON")
    pose_index: IntProperty(name="Indice en JSON", default=0)
    duration:   IntProperty(name="Frames", default=20, min=1, soft_max=99999)
    # Frame absoluto donde empieza esta pose. Ver Cerdo_1SegmentPoseSlot.manual_start
    # para la explicacion completa -- este campo es el espejo de ese mismo
    # sistema en la copia de trabajo que usa cerdo_1_st.concatenate.
    frame_abs_start: IntProperty(name="Frame inicio absoluto", default=0)
    manual_start: BoolProperty(
        name="Frame de inicio manual",
        default=False,
        description=(
            "Si esta activo, 'Frame inicio absoluto' se usa tal cual en vez "
            "de calcularse automaticamente tras la pose anterior."
        ),
    )
    entry_ratio: FloatProperty(name="Entrada %", default=0.3, min=0.0, max=1.0, precision=2)
    exit_ratio:  FloatProperty(name="Salida %",  default=0.3, min=0.0, max=1.0, precision=2)
    # Orientacion individual del Armature para esta pose (grados)
    rot_x: FloatProperty(name="Rot X", default=0.0, subtype="ANGLE",
        description="Rotacion X del Armature (root/Empty) en esta pose (grados)")
    rot_y: FloatProperty(name="Rot Y", default=0.0, subtype="ANGLE",
        description="Rotacion Y del Armature (root/Empty) en esta pose (grados)")
    rot_z: FloatProperty(name="Rot Z", default=0.0, subtype="ANGLE",
        description="Rotacion Z del Armature (root/Empty) en esta pose (grados)")
    # Posicion XYZ del root/Empty para esta pose
    pos_x: FloatProperty(name="Pos X", default=0.0,
        description="Posicion X del root (cerdo_1/Empty) en esta pose")
    pos_y: FloatProperty(name="Pos Y", default=0.0,
        description="Posicion Y del root (cerdo_1/Empty) en esta pose")
    pos_z: FloatProperty(name="Pos Z", default=0.0,
        description="Posicion Z del root (cerdo_1/Empty) en esta pose")
    # Tipo de interpolacion hacia esta pose de accion
    interp_type: EnumProperty(
        name="Interpolacion",
        description="Tipo de interpolacion profesional desde la pose anterior a esta",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )

class Cerdo_1OrganicFilters(PropertyGroup):
    """
    Filtros de movimiento organico que se aplican como post-proceso sobre los keyframes
    generados por CONCATENAR. Eliminan la rigidez robotica agregando micro-variaciones
    fisicamente plausibles sobre la rotacion, posicion y escala del armature y bones.
    """

    # ── Habilitadores generales ──
    enabled: BoolProperty(
        name="Activar filtros organicos",
        description="Aplica todos los filtros habilitados despues de CONCATENAR",
        default=False,
    )

    # ── FILTRO 1: Noise de respiracion ──
    breathing_enabled: BoolProperty(name="Respiracion", default=True,
        description="Agrega un ciclo suave de respiracion al torso (Spine/Spine1)")
    breathing_amplitude: FloatProperty(name="Amplitud", default=0.012, min=0.001, max=0.15, precision=3,
        description="Magnitud maxima del movimiento de respiracion en radianes")
    breathing_speed: FloatProperty(name="Velocidad", default=0.08, min=0.01, max=1.0, precision=3,
        description="Ciclos de respiracion por frame (0.08 = ~18 resp/min a 24fps)")
    breathing_phase: FloatProperty(name="Fase", default=0.0, min=0.0, max=6.28, precision=2,
        description="Offset de fase inicial del ciclo de respiracion (radianes)")

    # ── FILTRO 2: Micro-movimiento de cabeza (head sway) ──
    head_sway_enabled: BoolProperty(name="Micro-movimiento cabeza", default=True,
        description="Agrega oscilaciones organicas sutiles al cuello y cabeza (Neck/face)")
    head_sway_amplitude: FloatProperty(name="Amplitud", default=0.008, min=0.001, max=0.10, precision=3,
        description="Magnitud maxima del micro-movimiento de cabeza en radianes")
    head_sway_speed: FloatProperty(name="Velocidad", default=0.05, min=0.005, max=0.5, precision=3,
        description="Velocidad de oscilacion de la cabeza por frame")
    head_sway_seed: IntProperty(name="Semilla", default=42, min=0, max=9999,
        description="Semilla aleatoria para variacion del patron de cabeza")

    # ── FILTRO 3: Weight shift (desplazamiento del peso) ──
    weight_shift_enabled: BoolProperty(name="Desplazamiento de peso", default=False,
        description="Simula el desplazamiento del centro de masa de lado a lado (hips)")
    weight_shift_amplitude: FloatProperty(name="Amplitud", default=0.005, min=0.001, max=0.05, precision=3,
        description="Magnitud del desplazamiento lateral de cadera en unidades Blender")
    weight_shift_speed: FloatProperty(name="Velocidad", default=0.04, min=0.005, max=0.3, precision=3,
        description="Velocidad del ciclo de desplazamiento de peso")

    # ── FILTRO 4: Procedural noise sobre el ROOT (movimiento de camara/cuerpo) ──
    root_noise_enabled: BoolProperty(name="Noise en ROOT", default=False,
        description="Agrega ruido procesal sobre la posicion del root (cerdo_1/Empty)")
    root_noise_strength: FloatProperty(name="Intensidad", default=0.003, min=0.0001, max=0.05, precision=4,
        description="Intensidad maxima del ruido de posicion del root")
    root_noise_frequency: FloatProperty(name="Frecuencia", default=0.15, min=0.01, max=2.0, precision=3,
        description="Frecuencia del ruido (mayor = movimiento mas rapido)")
    root_noise_seed: IntProperty(name="Semilla", default=7, min=0, max=9999,
        description="Semilla para el ruido del root")

    # ── FILTRO 5: Secondary motion de extremidades ──
    secondary_motion_enabled: BoolProperty(name="Secondary motion brazos", default=False,
        description="Agrega retardo y oscilacion a los codos y antebrazos (follow-through)")
    secondary_motion_lag: FloatProperty(name="Retardo (frames)", default=3.0, min=0.5, max=15.0, precision=1,
        description="Frames de retardo que los extremos siguen al movimiento principal")
    secondary_motion_damping: FloatProperty(name="Amortiguacion", default=0.7, min=0.1, max=0.99, precision=2,
        description="Factor de amortiguacion del movimiento secundario (0=sin amortiguar, 1=rigido)")

    # ── FILTRO 6: Smooth de fcurves (suavizado de curvas generadas) ──
    smooth_curves_enabled: BoolProperty(name="Suavizar fcurves", default=True,
        description="Aplica suavizado gaussiano a todas las fcurves del armature post-generacion")
    smooth_passes: IntProperty(name="Pasadas de suavizado", default=2, min=1, max=10,
        description="Numero de pasadas del suavizado gaussiano (mas = mas suave, mas fluido)")
    smooth_factor: FloatProperty(name="Factor suavizado", default=0.5, min=0.1, max=0.9, precision=2,
        description="Fuerza del suavizado en cada pasada (0.1=leve, 0.9=muy suave)")

    # ── FILTRO 7: Micro-escala (squash and stretch organico) ──
    micro_scale_enabled: BoolProperty(name="Micro-escala organica", default=False,
        description="Agrega variacion minima de escala en el eje Z del Spine para simular presion/expansion")
    micro_scale_amplitude: FloatProperty(name="Amplitud", default=0.005, min=0.001, max=0.03, precision=3,
        description="Variacion maxima de escala organica")

    # ── FILTRO 8: Noise rotacional en hombros ──
    shoulder_noise_enabled: BoolProperty(name="Noise hombros", default=False,
        description="Agrega micro-rotaciones procesuales a los hombros para mayor naturalidad")
    shoulder_noise_amplitude: FloatProperty(name="Amplitud", default=0.006, min=0.001, max=0.08, precision=3,
        description="Magnitud del noise de hombros en radianes")
    shoulder_noise_speed: FloatProperty(name="Velocidad", default=0.07, min=0.01, max=0.5, precision=3,
        description="Velocidad del noise de hombros")
    shoulder_noise_seed: IntProperty(name="Semilla", default=123, min=0, max=9999,
        description="Semilla aleatoria para noise de hombros")


# =============================================================================
# FILTRO: IMPORTACION DE OBJETOS (armas, escudos, props)
# =============================================================================

def _oi_apply_transform_to_object(obj, loc_x, loc_y, loc_z, rot_x, rot_y, rot_z, scale_uniform):
    """
    Aplica posicion/rotacion/escala a un objeto ya importado en la escena,
    sin tocar parenteo ni visibilidad. Usado para previsualizar en tiempo
    real los cambios del panel de Importacion de Objetos.
    """
    try:
        obj.location = (loc_x, loc_y, loc_z)
        obj.rotation_euler = (rot_x, rot_y, rot_z)
        obj.scale = (scale_uniform, scale_uniform, scale_uniform)
    except Exception as e:
        print(f"[OBJ_IMPORTS] ⚠️ No se pudo previsualizar transform en '{obj.name}': {e}")


def _oi_item_update(self, context):
    """
    update= callback para los campos loc/rot/scale de un item ya agregado
    a la lista (Cerdo_1ObjectImportItem). Si el objeto ya fue importado
    (item.imported_object_name), se actualiza su transform en vivo.
    """
    obj = bpy.data.objects.get(self.imported_object_name)
    if obj is not None:
        _oi_apply_transform_to_object(
            obj, self.loc_x, self.loc_y, self.loc_z,
            self.rot_x, self.rot_y, self.rot_z, self.scale_uniform,
        )


def _oi_editor_update(self, context):
    """
    update= callback para los campos loc/rot/scale del editor
    (Cerdo_1ObjectImportsSettings.edit_*). Si hay un objeto importado en
    preview (edit_imported_object_name), se actualiza su transform en vivo
    para ver el resultado mientras se ajustan los valores.
    """
    obj = bpy.data.objects.get(self.edit_imported_object_name)
    if obj is not None:
        _oi_apply_transform_to_object(
            obj, self.edit_loc_x, self.edit_loc_y, self.edit_loc_z,
            self.edit_rot_x, self.edit_rot_y, self.edit_rot_z, self.edit_scale_uniform,
        )


class Cerdo_1ObjectImportItem(PropertyGroup):
    """
    Un intervalo de importacion de objeto para Cerdo_1.
    Importa un objeto .blend en el frame de inicio y lo oculta fuera del rango.
    """
    label: StringProperty(name="Etiqueta", default="Objeto",
        description="Nombre descriptivo de este objeto importado")
    object_folder: StringProperty(name="Carpeta", default="vanilla/shield",
        description="Ruta relativa dentro de objetos/ hasta la carpeta del objeto "
                     "(ej: vanilla/shield, jerry/espada). Se completa automaticamente "
                     "con 'Buscar .blend...'. Por compatibilidad, tambien acepta solo "
                     "el nombre de carpeta (ej: 'shield') asumiendo objetos/vanilla/.")
    blend_filename: StringProperty(name="Archivo .blend", default="shield.blend",
        description="Nombre del archivo .blend dentro de la carpeta del objeto")
    object_name: StringProperty(name="Nombre objeto", default="shield",
        description="Nombre exacto del objeto dentro del .blend a importar")
    frame_start: IntProperty(name="Frame inicio", default=1, min=0, soft_max=99999,
        description="Frame en el que el objeto aparece (se vuelve visible)")
    frame_end: IntProperty(name="Frame fin", default=60, min=1, soft_max=99999,
        description="Frame en el que el objeto se oculta")
    parent_armature: StringProperty(name="Armature", default="pig.arma_cerdo_1",
        description="Nombre del armature al que parentear el objeto. "
                     "Cerdo_1 tiene un unico armature en la escena llamado 'Armature'.")
    parent_bone: StringProperty(name="Bone de parenteo", default="Leg:FL:Bend_cerdo_1",
        description="Nombre del bone al que parentear el objeto (dejar vacio para parentear al armature)")
    loc_x: bpy.props.FloatProperty(name="Loc X", default=0.0, precision=4, update=_oi_item_update)
    loc_y: bpy.props.FloatProperty(name="Loc Y", default=0.0, precision=4, update=_oi_item_update)
    loc_z: bpy.props.FloatProperty(name="Loc Z", default=0.0, precision=4, update=_oi_item_update)
    rot_x: bpy.props.FloatProperty(name="Rot X", default=0.0, precision=2,
        subtype='ANGLE', unit='ROTATION', update=_oi_item_update,
        description="Rotacion en X (se muestra en grados, se almacena en radianes)")
    rot_y: bpy.props.FloatProperty(name="Rot Y", default=0.0, precision=2,
        subtype='ANGLE', unit='ROTATION', update=_oi_item_update,
        description="Rotacion en Y (se muestra en grados, se almacena en radianes)")
    rot_z: bpy.props.FloatProperty(name="Rot Z", default=0.0, precision=2,
        subtype='ANGLE', unit='ROTATION', update=_oi_item_update,
        description="Rotacion en Z (se muestra en grados, se almacena en radianes)")
    scale_uniform: bpy.props.FloatProperty(name="Escala", default=1.0, min=0.001, max=100.0, precision=3,
        update=_oi_item_update,
        description="Escala uniforme del objeto importado")
    levels_up: IntProperty(name="Niveles arriba", default=4, min=1, max=10,
        description="Niveles de directorio a subir desde el slot hasta la raiz del proyecto")
    enabled: BoolProperty(name="Activo", default=True,
        description="Activa o desactiva este objeto sin eliminarlo de la lista")
    imported_object_name: StringProperty(name="Objeto importado", default="",
        description="Nombre interno (bpy.data.objects) del objeto ya importado en la escena, "
                     "para evitar re-importar duplicados en cada CONCATENAR")
    segment_idx: IntProperty(name="Segmento", default=-1, min=-1, soft_max=999,
        description="Indice del segmento (cerdo_1_segs.segments) al que pertenece este objeto. "
                     "-1 = global (se ejecuta con el CONCATENAR de cualquier segmento)")
    # ── Transiciones de aparición / desaparición ────────────────────────────
    TRANSITION_IN_ITEMS = [
        ('NONE',        'Sin transición',       'El objeto aparece instantáneamente (hide_viewport keyframe)'),
        ('SCALE_POP',   'Pop / Rebote',         'Crece desde 0 con un overshoot elástico — clásico cartoon'),
        ('SCALE_BOUNCE','Bounce Drop',          'Cae escalando con rebote al aterrizar — entrada dinámica'),
        ('SCALE_SQUASH','Squash & Stretch',     'Se aplana y estira antes de asentarse — cartoon expresivo'),
        ('FADE_IN',     'Fade In (opacidad)',   'Aparece gradualmente aumentando la opacidad del material'),
        ('SLIDE_UP',    'Deslizar arriba',      'El objeto sube desde abajo hasta su posición final'),
        ('SLIDE_DOWN',  'Deslizar abajo',       'El objeto baja desde arriba hasta su posición final'),
        ('SPIN_IN',     'Spin + Pop',           'Rota 360° mientras crece — entrada llamativa'),
        ('IRIS_WIPE',   'Iris / Wipe',          'Crece desde punto central con ease-in exponencial — iris clásico'),
        ('SWING_IN',    'Swing In',             'Entra columpiándose con rotación amortiguada en Z'),
    ]
    TRANSITION_OUT_ITEMS = [
        ('NONE',         'Sin transición',      'El objeto desaparece instantáneamente'),
        ('SCALE_SHRINK', 'Encoger / Pop Out',   'Se reduce a 0 rápidamente con un squash previo — cartoon'),
        ('SCALE_BOUNCE', 'Bounce Out',          'Salta hacia arriba antes de encogerse y desaparecer'),
        ('FADE_OUT',     'Fade Out (opacidad)', 'Desaparece gradualmente reduciendo la opacidad del material'),
        ('SLIDE_UP',     'Deslizar arriba',     'El objeto sube y sale de cuadro por arriba'),
        ('SLIDE_DOWN',   'Deslizar abajo',      'El objeto baja y sale de cuadro por abajo'),
        ('SPIN_OUT',     'Spin + Shrink',       'Rota mientras se encoge hasta desaparecer'),
        ('SWING_OUT',    'Swing Out',           'Sale columpiándose con rotación en Z hacia afuera'),
        ('SQUASH_OUT',   'Squash Out',          'Se aplana en Y antes de desaparecer — cartoon expressivo'),
    ]
    transition_in: bpy.props.EnumProperty(
        name="Transición aparición",
        description="Efecto de entrada del objeto al frame de inicio",
        items=TRANSITION_IN_ITEMS,
        default='NONE',
    )
    transition_in_duration: IntProperty(
        name="Duración entrada (frames)",
        description="Número de frames que dura la transición de entrada",
        default=8, min=1, max=60,
    )
    transition_out: bpy.props.EnumProperty(
        name="Transición desaparición",
        description="Efecto de salida del objeto al frame fin",
        items=TRANSITION_OUT_ITEMS,
        default='NONE',
    )
    transition_out_duration: IntProperty(
        name="Duración salida (frames)",
        description="Número de frames que dura la transición de salida",
        default=8, min=1, max=60,
    )


# =============================================================================
# SISTEMA DE LANZAR / RECOGER OBJETOS
# =============================================================================

THROW_EASING_ITEMS = [
    ('LINEAR',   'Lineal',         'Velocidad constante sin aceleracion'),
    ('SMOOTH',   'Suave (ease)',   'Aceleracion y desaceleracion suave'),
    ('EASE_IN',  'Aceleracion',    'Empieza lento, termina rapido'),
    ('EASE_OUT', 'Desaceleracion', 'Empieza rapido, termina lento'),
    ('BOUNCE',   'Rebote',         'Rebota al llegar al punto'),
    ('ELASTIC',  'Elastico',       'Oscila antes de asentarse'),
    ('BACK',     'Overshoot',      'Se pasa del punto y vuelve'),
    ('PARABOLA', 'Parabola',       'Arco de proyectil con gravedad'),
]


def _th_editor_update(self, context):
    """
    update= callback para los campos loc/rot/scale del editor del sistema
    Lanzar/Recoger/Mantener (Cerdo_1ThrowsSettings.edit_*). Si hay un objeto
    importado en preview (edit_imported_object_name, via "Importar objeto"),
    se actualiza su transform en vivo para ver el resultado mientras se
    ajustan los valores -- igual que en el editor de Importacion de Objetos.
    """
    obj = bpy.data.objects.get(self.edit_imported_object_name)
    if obj is not None:
        _oi_apply_transform_to_object(
            obj, self.edit_loc_x, self.edit_loc_y, self.edit_loc_z,
            self.edit_rot_x, self.edit_rot_y, self.edit_rot_z, self.edit_scale_uniform,
        )


class Cerdo_1ThrowWaypoint(PropertyGroup):
    """Punto intermedio en la trayectoria. Coordenadas GLOBALES."""
    label:   StringProperty(name="Etiqueta", default="Punto")
    x:       FloatProperty(name="X", default=0.0, precision=4)
    y:       FloatProperty(name="Y", default=0.0, precision=4)
    z:       FloatProperty(name="Z", default=2.0, precision=4)
    easing:  EnumProperty(name="Easing", items=THROW_EASING_ITEMS, default='SMOOTH')
    enabled: BoolProperty(name="Activo", default=True)


class Cerdo_1ThrowItem(PropertyGroup):
    """
    Un lanzamiento/recogida de objeto. Un segmento puede tener varios.
    Equivalente a Cerdo_1ObjectImportItem para el sistema de lanzar/recoger.
    """
    label:   StringProperty(name="Etiqueta", default="Lanzamiento")
    enabled: BoolProperty(name="Activo", default=True)

    # BUGFIX (Kebyn + Claude, 2026-09-01 ter: "al borrar una configuracion
    # pasada donde se importo otro objeto, y elegir uno nuevo, se estan
    # acumulando los objetos importados anteriormente"): identificador
    # ESTABLE de este item, generado una sola vez al crearlo y persistido
    # en el JSON. Se usa para etiquetar (via custom property en el Object
    # de Blender) qué item de Lanzar/Recoger/Mantener "dueño" de cada
    # objeto importado, sin depender de object_name/label (que el usuario
    # puede cambiar libremente al elegir un objeto distinto) ni de la
    # posicion del item en la lista (que cambia al reordenar/eliminar
    # otros). Con este uid estable, run_throws_for_segments() puede barrer
    # y borrar de la escena cualquier objeto "huerfano" -- uno cuyo item
    # ya no existe (fue eliminado con el boton de basurero) -- en cada
    # "Concatenar segmentos", en vez de dejarlo acumulado para siempre.
    uid: StringProperty(name="UID interno", default="")
    # Segmento al que se aplica cuando la configuración se administra desde
    # el panel global de Lanzar/Recoger/Mantener.
    segment_idx: IntProperty(name="Segmento", default=0, min=0, soft_max=999)

    mode: EnumProperty(
        name="Modo",
        items=[
            ('THROW', 'Lanzar',  'El objeto sale del bone hacia la coordenada destino'),
            ('CATCH', 'Recoger', 'El objeto va desde la coordenada origen hacia el bone'),
            ('HOLD',  'Mantener', 'El objeto solo se importa y se aparenta al bone '
                                   'designado, sin trayectoria ni animacion propia'),
        ],
        default='THROW',
    )

    # Importacion propia
    blend_path:      StringProperty(name="Ruta .blend", default="", subtype="FILE_PATH")
    object_folder:   StringProperty(name="Carpeta", default="")
    blend_filename:  StringProperty(name="Archivo .blend", default="")
    object_name:     StringProperty(name="Nombre objeto", default="")
    levels_up:       IntProperty(name="Niveles arriba", default=4, min=1, max=10)
    imported_object_name: StringProperty(name="Objeto importado", default="")

    # Aparentamiento
    parent_armature: StringProperty(name="Armature", default="pig.arma_cerdo_1")
    parent_bone:     StringProperty(name="Bone", default="")

    # Offset sobre el bone
    loc_x: FloatProperty(name="X", default=0.0, precision=4)
    loc_y: FloatProperty(name="Y", default=0.0, precision=4)
    loc_z: FloatProperty(name="Z", default=0.0, precision=4)
    rot_x: FloatProperty(name="Rot X", default=0.0, precision=2,
                subtype='ANGLE', unit='ROTATION')
    rot_y: FloatProperty(name="Rot Y", default=0.0, precision=2,
                subtype='ANGLE', unit='ROTATION')
    rot_z: FloatProperty(name="Rot Z", default=0.0, precision=2,
                subtype='ANGLE', unit='ROTATION')
    scale_uniform: FloatProperty(name="Escala", default=1.0, min=0.001, max=100.0, precision=3)

    # Frames propios
    frame_start: IntProperty(name="Frame inicio", default=1, min=0, soft_max=99999)
    frame_end:   IntProperty(name="Frame fin",   default=30, min=1, soft_max=99999)

    # ── Gesto de brazo "hacia la espalda" (reach-back) ──────────────────────
    # Se aplica SIEMPRE para los 3 modos (ver apply_pre_throw_reach_back,
    # operators_anim.py). duration_in es la MITAD del gesto de entrada:
    # cuantos frames tarda el brazo en ir desde frame_start hasta la pose
    # "hacia la espalda" -- el objeto aparece justo ahi (frame_start +
    # duration_in), no cuando el brazo ya volvio a la normalidad. La
    # vuelta a la pose por defecto tarda lo mismo (duration_in de nuevo).
    # reach_back_enabled_out + duration_out agregan el mismo gesto en
    # espejo, terminando exacto en frame_end, para simular que el
    # personaje "guarda" el objeto antes de que desaparezca.
    reach_back_duration_in: IntProperty(
        name="Duración del gesto (frames)",
        description="Cuántos frames tarda el brazo en llegar a la pose "
                     "'hacia la espalda' desde Inicio -- el objeto aparece "
                     "justo ahí (Inicio + este valor). La vuelta a la pose "
                     "normal tarda lo mismo otra vez",
        default=16, min=2, soft_min=2, soft_max=120,
    )
    reach_back_enabled_out: BoolProperty(
        name="Repetir gesto (en espejo) antes de guardar",
        description="Aplica el mismo gesto de brazo, en espejo, terminando "
                     "exacto en Fin -- simula que el personaje guarda el objeto",
        default=True,
    )
    reach_back_duration_out: IntProperty(
        name="Duración gesto al guardar (frames)",
        description="Cuántos frames antes de Fin el brazo llega a la pose "
                     "'hacia la espalda' -- el objeto desaparece justo ahí "
                     "(Fin - este valor), no cuando el brazo ya volvió a la "
                     "normalidad. La vuelta a la normalidad tarda lo mismo "
                     "otra vez, terminando exacto en Fin",
        default=16, min=2, soft_min=2, soft_max=120,
    )

    # Trayectoria
    target_object:   StringProperty(name="Objeto activo", default="")
    target_armature: StringProperty(name="Armature (traj.)", default="pig.arma_cerdo_1")
    target_bone:     StringProperty(name="Bone origen (traj.)", default="")
    dest_x: FloatProperty(name="X", default=0.0, precision=4)
    dest_y: FloatProperty(name="Y", default=3.0, precision=4)
    dest_z: FloatProperty(name="Z", default=0.0, precision=4)
    easing_global: EnumProperty(name="Easing", items=THROW_EASING_ITEMS, default='SMOOTH')

    # Avanzado
    spin_during_flight: BoolProperty(name="Rotacion en vuelo", default=False)
    spin_turns: FloatProperty(name="Vueltas", default=1.0, min=0.0, max=20.0, precision=1)

    # Waypoints
    waypoints:     CollectionProperty(type=Cerdo_1ThrowWaypoint)
    waypoints_idx: IntProperty(default=0)

    # ── Transiciones cartoon de aparición / desaparición ──────────────────
    # Mismo sistema que Cerdo_1ObjectImportItem (reutiliza sus items de enum
    # para no duplicar la lista). Aplican en frame_start (aparición) y
    # frame_end (desaparición) para los 3 modos (THROW/CATCH/HOLD).
    # NOTA IMPORTANTE: en THROW/CATCH la parte de `location` de la transición
    # (si la tuviera, ej. SLIDE_UP/SLIDE_DOWN/SCALE_BOUNCE) se descarta
    # automáticamente — apply_throw_item() limpia cualquier keyframe de
    # `location` en su rango antes de trazar la trayectoria real, así que
    # solo sobrevive la parte de escala/rotación/alpha de la transición. En
    # HOLD se aplica completa (incluida la parte de location), igual que en
    # Importación de Objetos, porque ahí no hay trayectoria que proteger.
    transition_in: bpy.props.EnumProperty(
        name="Transición aparición",
        description="Efecto de entrada del objeto al frame de inicio",
        items=Cerdo_1ObjectImportItem.TRANSITION_IN_ITEMS,
        default='NONE',
    )
    transition_in_duration: IntProperty(
        name="Duración entrada (frames)",
        description="Número de frames que dura la transición de entrada",
        default=8, min=1, max=60,
    )
    transition_out: bpy.props.EnumProperty(
        name="Transición desaparición",
        description="Efecto de salida del objeto al frame fin",
        items=Cerdo_1ObjectImportItem.TRANSITION_OUT_ITEMS,
        default='NONE',
    )
    transition_out_duration: IntProperty(
        name="Duración salida (frames)",
        description="Número de frames que dura la transición de salida",
        default=8, min=1, max=60,
    )

    # UI state
    show_waypoints: BoolProperty(name="Mostrar waypoints", default=True)
    show_advanced:  BoolProperty(name="Mostrar avanzado",  default=False)


# =============================================================================
# SISTEMA DE INVISIBILIDAD DE MALLA
# =============================================================================
# Se ubica DEBAJO del sistema de Lanzar / Recoger / Mantener Objetos, tanto en
# el codigo (aca, a continuacion de Cerdo_1ThrowsSettings) como en el panel
# (panels.py dibuja su box justo despues del de Lanzar/Recoger/Mantener).
# Permite elegir CUALQUIER malla del escenario (no necesariamente importada
# por Cerdo_1: cualquier Object tipo MESH de la escena) y un intervalo de
# frames propio durante el cual esa malla se vuelve invisible (hide_viewport
# + hide_render), volviendo a ser visible automaticamente al terminar el
# intervalo. No requiere trayectoria, aparentamiento a bone ni importacion:
# solo toggles de visibilidad con keyframes, igual que set_visibility_keyframes
# en object_import_utils.py.

class Cerdo_1HideMeshItem(PropertyGroup):
    """
    Un intervalo de invisibilidad para una malla del escenario. Un segmento
    puede tener varios. Equivalente (simplificado) a Cerdo_1ThrowItem, pero
    sin importacion/trayectoria: solo oculta y vuelve a mostrar la malla
    elegida en el rango de frames indicado.
    """
    label:   StringProperty(name="Etiqueta", default="Invisibilidad")
    enabled: BoolProperty(name="Activo", default=True)

    # uid estable (mismo criterio que Cerdo_1ThrowItem.uid) para poder
    # identificar este item de forma independiente de su posicion en la
    # lista o del nombre que el usuario le haya puesto.
    uid: StringProperty(name="UID interno", default="")
    # Segmento al que se aplica cuando la configuracion se administra desde
    # el panel global de Invisibilidad de Malla (mismo criterio que
    # Cerdo_1ThrowItem.segment_idx).
    segment_idx: IntProperty(name="Segmento", default=0, min=0, soft_max=999)

    # Cualquier malla del escenario -- se guarda el nombre del Object y se
    # resuelve via bpy.data.objects.get() al momento de aplicar.
    mesh_object: StringProperty(
        name="Malla",
        description="Objeto (malla) del escenario que se hara invisible durante el intervalo",
        default="",
    )

    # Intervalo propio durante el cual la malla permanece invisible. Fuera
    # de [frame_start, frame_end] la malla es visible.
    frame_start: IntProperty(name="Frame inicio", default=1, min=0, soft_max=99999)
    frame_end:   IntProperty(name="Frame fin",   default=30, min=1, soft_max=99999)


class Cerdo_1HideMeshSettings(PropertyGroup):
    """
    Coleccion de Cerdo_1HideMeshItem para un segmento.
    Equivalente a Cerdo_1ThrowsSettings, para el sistema de Invisibilidad de
    Malla. Se almacena en Cerdo_1AnimSegment.hide_mesh.
    """
    enabled: BoolProperty(name="Activar Invisibilidad de Malla", default=False)
    items:   CollectionProperty(type=Cerdo_1HideMeshItem)
    active_idx: IntProperty(default=0)

    # ── Campos edit_* para el editor de nuevo item ────────────────────────
    edit_label:       StringProperty(name="Etiqueta", default="Invisibilidad")
    edit_mesh_object: StringProperty(name="Malla", default="")
    edit_frame_start: IntProperty(name="Frame inicio", default=1, min=0, soft_max=99999)
    edit_frame_end:   IntProperty(name="Frame fin", default=30, min=1, soft_max=99999)


class Cerdo_1ThrowsSettings(PropertyGroup):
    """
    Coleccion de Cerdo_1ThrowItem para un segmento.
    Equivalente a Cerdo_1ObjectImportsSettings.
    Se almacena en Cerdo_1AnimSegment.throws.
    """
    enabled: BoolProperty(name="Activar Lanzar/Recoger", default=False)
    items:   CollectionProperty(type=Cerdo_1ThrowItem)
    active_idx: IntProperty(default=0)

    # ── Campos edit_* para el editor de nuevo item ────────────────────────
    edit_label:          StringProperty(name="Etiqueta", default="Lanzamiento")
    edit_mode: EnumProperty(
        name="Modo",
        items=[
            ('THROW', 'Lanzar',  'El objeto sale del bone hacia el destino'),
            ('CATCH', 'Recoger', 'El objeto va desde el origen hacia el bone'),
            ('HOLD',  'Mantener', 'El objeto solo se importa y se aparenta al bone '
                                   'designado, sin trayectoria ni animacion propia'),
        ],
        default='THROW',
    )
    edit_blend_path:      StringProperty(name="Ruta .blend", default="", subtype="FILE_PATH")
    edit_object_folder:   StringProperty(name="Carpeta", default="")
    edit_blend_filename:  StringProperty(name="Archivo .blend", default="")
    edit_object_name:     StringProperty(name="Nombre objeto", default="")
    edit_levels_up:       IntProperty(name="Niveles arriba", default=4, min=1, max=10)
    edit_imported_object_name: StringProperty(default="")
    edit_parent_armature: StringProperty(name="Armature", default="pig.arma_cerdo_1")
    edit_parent_bone:     StringProperty(name="Bone", default="")
    edit_loc_x: FloatProperty(name="X", default=0.0, precision=4, update=_th_editor_update)
    edit_loc_y: FloatProperty(name="Y", default=0.0, precision=4, update=_th_editor_update)
    edit_loc_z: FloatProperty(name="Z", default=0.0, precision=4, update=_th_editor_update)
    edit_rot_x: FloatProperty(name="Rot X", default=0.0, precision=2,
                    subtype='ANGLE', unit='ROTATION', update=_th_editor_update)
    edit_rot_y: FloatProperty(name="Rot Y", default=0.0, precision=2,
                    subtype='ANGLE', unit='ROTATION', update=_th_editor_update)
    edit_rot_z: FloatProperty(name="Rot Z", default=0.0, precision=2,
                    subtype='ANGLE', unit='ROTATION', update=_th_editor_update)
    edit_scale_uniform:   FloatProperty(name="Escala", default=1.0, min=0.001, max=100.0, precision=3,
                    update=_th_editor_update)
    edit_frame_start:     IntProperty(name="Frame inicio", default=1, min=0, soft_max=99999)
    edit_frame_end:       IntProperty(name="Frame fin", default=30, min=1, soft_max=99999)
    edit_reach_back_duration_in: IntProperty(
        name="Duración del gesto (frames)", default=16, min=2, soft_min=2, soft_max=120,
        description="Cuántos frames tarda el brazo en llegar a la pose "
                     "'hacia la espalda' desde Inicio -- el objeto aparece "
                     "justo ahí (Inicio + este valor). La vuelta a la pose "
                     "normal tarda lo mismo otra vez",
    )
    edit_reach_back_enabled_out: BoolProperty(
        name="Repetir gesto (en espejo) antes de guardar", default=True,
        description="Aplica el mismo gesto de brazo, en espejo, terminando "
                     "exacto en Fin -- simula que el personaje guarda el objeto",
    )
    edit_reach_back_duration_out: IntProperty(
        name="Duración gesto al guardar (frames)", default=16, min=2, soft_min=2, soft_max=120,
        description="Cuántos frames antes de Fin el brazo llega a la pose "
                     "'hacia la espalda' -- el objeto desaparece justo ahí "
                     "(Fin - este valor), no cuando el brazo ya volvió a la "
                     "normalidad. La vuelta a la normalidad tarda lo mismo "
                     "otra vez, terminando exacto en Fin",
    )
    edit_target_armature: StringProperty(name="Armature (traj.)", default="pig.arma_cerdo_1")
    edit_target_bone:     StringProperty(name="Bone origen (traj.)", default="")
    edit_dest_x: FloatProperty(name="X", default=0.0, precision=4)
    edit_dest_y: FloatProperty(name="Y", default=3.0, precision=4)
    edit_dest_z: FloatProperty(name="Z", default=0.0, precision=4)
    edit_easing_global: EnumProperty(name="Easing", items=THROW_EASING_ITEMS, default='SMOOTH')
    edit_spin_during_flight: BoolProperty(name="Rotacion en vuelo", default=False)
    edit_spin_turns: FloatProperty(name="Vueltas", default=1.0, min=0.0, max=20.0, precision=1)
    edit_transition_in: bpy.props.EnumProperty(
        name="Transición aparición",
        items=Cerdo_1ObjectImportItem.TRANSITION_IN_ITEMS,
        default='NONE',
    )
    edit_transition_in_duration: IntProperty(
        name="Duración entrada (frames)", default=8, min=1, max=60,
    )
    edit_transition_out: bpy.props.EnumProperty(
        name="Transición desaparición",
        items=Cerdo_1ObjectImportItem.TRANSITION_OUT_ITEMS,
        default='NONE',
    )
    edit_transition_out_duration: IntProperty(
        name="Duración salida (frames)", default=8, min=1, max=60,
    )


class Cerdo_1ObjectImportsSettings(PropertyGroup):
    """Configuracion global del sistema de importacion de objetos de Cerdo_1."""
    enabled: BoolProperty(
        name="Activar importacion de objetos",
        description=(
            "Habilita el sistema de importacion de objetos. "
            "Se generan al presionar EXPORTAR (incluidos en el .py exportado)."
        ),
        default=False,
    )
    items: CollectionProperty(type=Cerdo_1ObjectImportItem)
    active_idx: IntProperty(default=0)

    # ── Editor de nuevo objeto ──────────────────────────────────────────────
    edit_label:          StringProperty(name="Etiqueta", default="Mi objeto")
    edit_object_folder:  StringProperty(name="Carpeta", default="vanilla/shield")
    edit_blend_filename: StringProperty(name="Archivo .blend", default="shield.blend")
    edit_object_name:    StringProperty(name="Nombre objeto", default="shield")
    edit_frame_start:    IntProperty(name="Frame inicio", default=1, min=0, soft_max=99999)
    edit_frame_end:      IntProperty(name="Frame fin",   default=60, min=1, soft_max=99999)
    edit_parent_armature: StringProperty(name="Armature", default="pig.arma_cerdo_1",
        description="Nombre del armature al que parentear el objeto. "
                     "Cerdo_1 tiene un unico armature en la escena llamado 'Armature'.")
    edit_parent_bone:    StringProperty(name="Bone de parenteo", default="Leg:FL:Bend_cerdo_1")
    edit_loc_x: bpy.props.FloatProperty(name="Loc X", default=0.0, precision=4, update=_oi_editor_update)
    edit_loc_y: bpy.props.FloatProperty(name="Loc Y", default=0.0, precision=4, update=_oi_editor_update)
    edit_loc_z: bpy.props.FloatProperty(name="Loc Z", default=0.0, precision=4, update=_oi_editor_update)
    edit_rot_x: bpy.props.FloatProperty(name="Rot X", default=0.0, precision=2,
        subtype='ANGLE', unit='ROTATION', update=_oi_editor_update,
        description="Rotacion en X (se muestra en grados, se almacena en radianes)")
    edit_rot_y: bpy.props.FloatProperty(name="Rot Y", default=0.0, precision=2,
        subtype='ANGLE', unit='ROTATION', update=_oi_editor_update,
        description="Rotacion en Y (se muestra en grados, se almacena en radianes)")
    edit_rot_z: bpy.props.FloatProperty(name="Rot Z", default=0.0, precision=2,
        subtype='ANGLE', unit='ROTATION', update=_oi_editor_update,
        description="Rotacion en Z (se muestra en grados, se almacena en radianes)")
    edit_scale_uniform: bpy.props.FloatProperty(name="Escala", default=1.0, min=0.001, max=100.0, precision=3,
        update=_oi_editor_update)
    edit_levels_up: IntProperty(name="Niveles arriba", default=4, min=1, max=10)
    edit_imported_object_name: StringProperty(name="Objeto importado (preview)", default="",
        description="Nombre interno del objeto importado con 'Importar .blend al Outliner', "
                     "para reutilizarlo al agregar/actualizar el item de la lista")
    edit_segment_idx: IntProperty(name="Segmento", default=-1, min=-1, soft_max=999,
        description="Indice del segmento al que pertenece este objeto. "
                     "-1 = global (se ejecuta con el CONCATENAR de cualquier segmento)")
    # ── Transiciones ────────────────────────────────────────────────────────
    edit_transition_in: bpy.props.EnumProperty(
        name="Transición aparición",
        description="Efecto de entrada del objeto al frame de inicio",
        items=Cerdo_1ObjectImportItem.TRANSITION_IN_ITEMS,
        default='NONE',
    )
    edit_transition_in_duration: IntProperty(
        name="Duración entrada (frames)",
        default=8, min=1, max=60,
    )
    edit_transition_out: bpy.props.EnumProperty(
        name="Transición desaparición",
        description="Efecto de salida del objeto al frame fin",
        items=Cerdo_1ObjectImportItem.TRANSITION_OUT_ITEMS,
        default='NONE',
    )
    edit_transition_out_duration: IntProperty(
        name="Duración salida (frames)",
        default=8, min=1, max=60,
    )


class Cerdo_1BoneOscillationItem(PropertyGroup):
    """
    Un item de oscilacion sinusoidal para un bone especifico del armature de Cerdo_1.
    Permite animar cabeceos, balanceos de brazos, rodillas, etc.
    """
    label: StringProperty(name="Etiqueta", default="Oscilacion",
        description="Nombre descriptivo de esta oscilacion")
    bone_name: EnumProperty(
        name="Bone",
        description="Bone del armature de Cerdo_1 a oscilar",
        items=[
            ("Body_cerdo_1",       "Body_cerdo_1 (Caderas)",        ""),
            ("Body:Bend_cerdo_1",      "Body:Bend_cerdo_1 (Columna)",       ""),
            ("Body:Bend_cerdo_1",     "Body:Bend_cerdo_1 (Columna 1)",    ""),
            ("Body:Bend_cerdo_1",     "Body:Bend_cerdo_1 (Columna 2)",    ""),
            ("Head_cerdo_1",       "Head_cerdo_1 (Cuello)",         ""),
            ("Head_cerdo_1",       "Head_cerdo_1 (Cara)",           ""),
            ("Leg:FR_cerdo_1", "Leg:FR_cerdo_1 (Brazo D)",  ""),
            ("Leg:FR:Bend_cerdo_1", "Leg:FR:Bend_cerdo_1 (Codo D)",   ""),
            ("Leg:FL_cerdo_1",  "Leg:FL_cerdo_1 (Brazo I)",   ""),
            ("Leg:FL:Bend_cerdo_1",  "Leg:FL:Bend_cerdo_1 (Codo I)",    ""),
            ("Leg:BR_cerdo_1", "Leg:BR_cerdo_1 (Pierna D)", ""),
            ("Leg:BR:Bend_cerdo_1",  "Leg:BR:Bend_cerdo_1 (Rodilla D)", ""),
            ("Leg:BL_cerdo_1",  "Leg:BL_cerdo_1 (Pierna I)",  ""),
            ("Leg:BL:Bend_cerdo_1",   "Leg:BL:Bend_cerdo_1 (Rodilla I)",  ""),
        ],
        default="Body_cerdo_1",
    )
    frame_start: IntProperty(name="Frame inicio", default=1, min=0, soft_max=99999)
    frame_end:   IntProperty(name="Frame fin",   default=60, min=1, soft_max=99999)
    axis_x: BoolProperty(name="X", default=False,
        description="Aplicar oscilacion en eje X")
    axis_y: BoolProperty(name="Y", default=False,
        description="Aplicar oscilacion en eje Y")
    axis_z: BoolProperty(name="Z", default=True,
        description="Aplicar oscilacion en eje Z")
    amplitude: FloatProperty(name="Amplitud (grad)",
        default=30.0, min=0.1, max=360.0, precision=1,
        description="Amplitud de la oscilacion en grados (+/- desde el centro)")
    angle_offset: FloatProperty(name="Offset base (grad)",
        default=0.0, min=-360.0, max=360.0, precision=1, subtype="ANGLE",
        description="Desplazamiento angular base antes de oscilar")
    num_cycles: IntProperty(name="Numero de ciclos",
        default=4, min=1, max=999,
        description="Numero de ciclos completos en el rango de frames")
    phase: FloatProperty(name="Fase (rad)",
        default=0.0, min=0.0, max=6.2832, precision=3,
        description="Offset de fase inicial en radianes")
    wave_type: EnumProperty(name="Transicion",
        items=[
            # ── Clásicas ──────────────────────────────────────────────────────
            ("SINE",          "Sinusoidal",          "Oscilacion suave y ciclica — la base organica"),
            ("TRIANGLE",      "Lineal (triangulo)",  "Oscilacion lineal de punta a punta, bordes angulosos"),
            ("SQUARE",        "Snap (cuadrada)",     "Salto brusco entre los dos extremos"),
            ("NOISE",         "Noise aleatorio",     "Variacion aleatoria usando Perlin noise"),
            # ── Orgánicas suaves ─────────────────────────────────────────────
            ("SINE_EASE",     "Sine suavizado",      "Seno con ease-in/out: arranques y frenadas mas suaves"),
            ("ELASTIC",       "Elastico",            "Rebote elastico al final de cada ciclo — ideal para ropa y pelo"),
            ("BOUNCE",        "Rebote (bounce)",     "Decae como una pelota rebotando — impactos y pasos"),
            ("BREATHE",       "Respiracion",         "Patron lento expansivo como la respiracion — torso, hombros"),
            ("HEARTBEAT",     "Latido",              "Doble pulso rapido seguido de pausa — pecho, garganta"),
            # ── Ruido controlado ─────────────────────────────────────────────
            ("NOISE_DRIFT",   "Noise + deriva",      "Noise organico con deriva lenta — micro-movimientos naturales"),
            ("NOISE_LAYERED", "Noise multicapa",     "Tres frecuencias de noise superpuestas — temblor realista"),
            # ── Asimétricas / gestuales ───────────────────────────────────────
            ("SAW_SMOOTH",    "Sierra suavizada",    "Subida lenta y caida brusca — movimientos de barrido"),
            ("SAW_REVERSE",   "Sierra inversa",      "Subida rapida y caida lenta — reacciones y resortes"),
            ("PENDULUM",      "Pendulo",             "Aceleracion en el centro y frenada en los extremos — cabeza y tronco"),
            ("QUIVER",        "Temblor (quiver)",    "Oscilacion alta frecuencia de pequeña amplitud — miedo, frio, tension"),
        ], default="SINE")
    fade_in:  IntProperty(name="Fade in (frames)",  default=6, min=0, max=120,
        description="Frames de transicion suave al inicio")
    fade_out: IntProperty(name="Fade out (frames)", default=6, min=0, max=120,
        description="Frames de transicion suave al final")
    noise_seed: IntProperty(name="Semilla noise", default=42, min=0, max=9999,
        description="Semilla aleatoria para el noise organico")
    enabled: BoolProperty(name="Activo", default=True,
        description="Activa o desactiva esta oscilacion sin eliminarla")


class Cerdo_1BoneOscillationsSettings(PropertyGroup):
    """Configuracion global del sistema de oscilaciones de bones de Cerdo_1."""
    enabled: BoolProperty(
        name="Activar oscilaciones de bones",
        description=(
            "Habilita el sistema de oscilaciones personalizadas. "
            "Se aplican como post-proceso al presionar CONCATENAR."
        ),
        default=False,
    )
    items:      CollectionProperty(type=Cerdo_1BoneOscillationItem)
    active_idx: IntProperty(default=0)

    # ── Editor de nueva oscilacion ─────────────────────────────────────────
    edit_label:       StringProperty(name="Etiqueta", default="Mi oscilacion")
    edit_bone_name: EnumProperty(
        name="Bone",
        description="Bone del armature de Cerdo_1 a oscilar",
        items=[
            ("Body_cerdo_1",       "Body_cerdo_1 (Caderas)",        ""),
            ("Body:Bend_cerdo_1",      "Body:Bend_cerdo_1 (Columna)",       ""),
            ("Body:Bend_cerdo_1",     "Body:Bend_cerdo_1 (Columna 1)",    ""),
            ("Body:Bend_cerdo_1",     "Body:Bend_cerdo_1 (Columna 2)",    ""),
            ("Head_cerdo_1",       "Head_cerdo_1 (Cuello)",         ""),
            ("Head_cerdo_1",       "Head_cerdo_1 (Cara)",           ""),
            ("Leg:FR_cerdo_1", "Leg:FR_cerdo_1 (Brazo D)",  ""),
            ("Leg:FR:Bend_cerdo_1", "Leg:FR:Bend_cerdo_1 (Codo D)",   ""),
            ("Leg:FL_cerdo_1",  "Leg:FL_cerdo_1 (Brazo I)",   ""),
            ("Leg:FL:Bend_cerdo_1",  "Leg:FL:Bend_cerdo_1 (Codo I)",    ""),
            ("Leg:BR_cerdo_1", "Leg:BR_cerdo_1 (Pierna D)", ""),
            ("Leg:BR:Bend_cerdo_1",  "Leg:BR:Bend_cerdo_1 (Rodilla D)", ""),
            ("Leg:BL_cerdo_1",  "Leg:BL_cerdo_1 (Pierna I)",  ""),
            ("Leg:BL:Bend_cerdo_1",   "Leg:BL:Bend_cerdo_1 (Rodilla I)",  ""),
        ],
        default="Body_cerdo_1",
    )
    edit_frame_start: IntProperty(name="Frame inicio", default=1, min=0, soft_max=99999)
    edit_frame_end:   IntProperty(name="Frame fin",   default=60, min=1, soft_max=99999)
    edit_axis_x:      BoolProperty(name="X", default=False)
    edit_axis_y:      BoolProperty(name="Y", default=False)
    edit_axis_z:      BoolProperty(name="Z", default=True)
    edit_amplitude:   FloatProperty(name="Amplitud (grad)",
        default=30.0, min=0.1, max=360.0, precision=1)
    edit_angle_offset: FloatProperty(name="Offset (grad)",
        default=0.0, min=-360.0, max=360.0, precision=1, subtype="ANGLE")
    edit_num_cycles:  IntProperty(name="Numero de ciclos", default=4, min=1, max=999)
    edit_phase:       FloatProperty(name="Fase (rad)", default=0.0, min=0.0, max=6.2832, precision=3)
    edit_wave_type:   EnumProperty(name="Transicion",
        items=[
            # ── Clásicas ──────────────────────────────────────────────────────
            ("SINE",          "Sinusoidal",          "Oscilacion suave y ciclica — la base organica"),
            ("TRIANGLE",      "Lineal (triangulo)",  "Oscilacion lineal de punta a punta, bordes angulosos"),
            ("SQUARE",        "Snap (cuadrada)",     "Salto brusco entre los dos extremos"),
            ("NOISE",         "Noise aleatorio",     "Variacion aleatoria usando Perlin noise"),
            # ── Orgánicas suaves ─────────────────────────────────────────────
            ("SINE_EASE",     "Sine suavizado",      "Seno con ease-in/out: arranques y frenadas mas suaves"),
            ("ELASTIC",       "Elastico",            "Rebote elastico al final de cada ciclo — ideal para ropa y pelo"),
            ("BOUNCE",        "Rebote (bounce)",     "Decae como una pelota rebotando — impactos y pasos"),
            ("BREATHE",       "Respiracion",         "Patron lento expansivo como la respiracion — torso, hombros"),
            ("HEARTBEAT",     "Latido",              "Doble pulso rapido seguido de pausa — pecho, garganta"),
            # ── Ruido controlado ─────────────────────────────────────────────
            ("NOISE_DRIFT",   "Noise + deriva",      "Noise organico con deriva lenta — micro-movimientos naturales"),
            ("NOISE_LAYERED", "Noise multicapa",     "Tres frecuencias de noise superpuestas — temblor realista"),
            # ── Asimétricas / gestuales ───────────────────────────────────────
            ("SAW_SMOOTH",    "Sierra suavizada",    "Subida lenta y caida brusca — movimientos de barrido"),
            ("SAW_REVERSE",   "Sierra inversa",      "Subida rapida y caida lenta — reacciones y resortes"),
            ("PENDULUM",      "Pendulo",             "Aceleracion en el centro y frenada en los extremos — cabeza y tronco"),
            ("QUIVER",        "Temblor (quiver)",    "Oscilacion alta frecuencia de pequeña amplitud — miedo, frio, tension"),
        ], default="SINE")
    edit_fade_in:    IntProperty(name="Fade in",  default=6, min=0, max=120)
    edit_fade_out:   IntProperty(name="Fade out", default=6, min=0, max=120)
    edit_noise_seed: IntProperty(name="Semilla noise", default=42, min=0, max=9999)


class Cerdo_1StudioSettings(PropertyGroup):

    poses_dir: StringProperty(
        name="Poses",
        default=DEFAULT_POSES_DIR,
        subtype="DIR_PATH",
    )
    anim_dir: StringProperty(
        name="Animaciones",
        default=DEFAULT_ANIM_DIR,
        subtype="DIR_PATH",
    )
    # Carpeta donde vive pose_library.json (libreria central usada por el
    # pipeline de generaciones). Las calificaciones 1-10 que se guardan desde
    # esta interfaz se reflejan ahi para que el generador de IA las use.
    reglas_dir: StringProperty(
        name="Reglas (pose_library)",
        default=DEFAULT_REGLAS_DIR,
        subtype="DIR_PATH",
        description="Carpeta 'reglas' donde se guarda pose_library.json con las calificaciones",
    )
    # ── Ruta al JSON de historia (key_points + orientacion) ──
    historia_json: StringProperty(
        name="historia_cerdo_1.json",
        default=DEFAULT_HISTORIA_JSON,
        subtype="FILE_PATH",
        description="Ruta al archivo historia_cerdo_1.json con key_points y orientacion_inicial",
    )

    armature_name: StringProperty(name="Armature", default="")



    action_poses:    CollectionProperty(type=Cerdo_1PoseSlotItem)
    action_pose_idx: IntProperty(default=0)

    # Filtros de movimiento organico (post-proceso)
    organic: PointerProperty(type=Cerdo_1OrganicFilters)

    # Importacion de objetos (armas, escudos, props)
    object_imports: PointerProperty(type=Cerdo_1ObjectImportsSettings)

    # Sistema de expresiones de mallas de ojos (configuracion global / preview)
    eye_expr: PointerProperty(type=Cerdo_1EyeExpressionSettings)

    # ═══════════════════════════════════════════════════════════════════════
    # SISTEMA DE SECUENCIA DE OJOS  (espejo del sistema de poses)
    # ═══════════════════════════════════════════════════════════════════════

    # ── FRAME DE INICIO GLOBAL DE LA SECUENCIA DE OJOS ───────────────────
    eye_global_start_frame: IntProperty(
        name="Frame inicio  (ojos)",
        default=1, min=0, soft_max=99999,
        description=(
            "Frame a partir del cual CONCATENAR_2 insertara los keyframes "
            "de la secuencia de ojos. Sin limite superior. Independiente del frame de inicio del armature"
        ),
    )

    # ── TOGGLES DE SISTEMAS DE OJOS ──────────────────────────────────────
    eye_changes_enabled: BoolProperty(
        name="N° Cambios de Ojos",
        description=(
            "Activa el sistema de cambios intermedios de ojos (Inicio / N cambios / Fin). "
            "Desactivar si se usa solo el Parpadeo automatico para evitar conflictos"
        ),
        default=True,
    )
    # Nota: el toggle del Parpadeo automatico (cortina) vive en eye_expr.blink_enabled

    # ── ESTADO INICIAL DE OJOS ────────────────────────────────────────────
    eye_start_label: StringProperty(
        name="Etiqueta inicio ojos",
        default="Ojos inicio",
        description="Nombre descriptivo del estado inicial de los ojos",
    )
    eye_start_duration: IntProperty(
        name="Frames estado inicio ojos",
        default=10, min=1, soft_max=99999,
        description="Cuantos frames se mantiene el estado inicial de ojos. Sin limite superior.",
    )
    eye_start_interp: EnumProperty(
        name="Interpolacion salida INICIO ojos",
        description="Tipo de interpolacion de salida desde el estado inicial de ojos",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )
    eye_start_blink_mode: EnumProperty(
        name="Modo inicio ojos",
        description="Comportamiento de los ojos durante el estado inicial",
        items=[
            ("FIXED",  "Posicion fija",  "Los ojos permanecen en la posicion base sin parpadear"),
            ("BLINK",  "Parpadeo",       "Los ojos parpadean con normalidad durante el estado inicial"),
        ],
        default="FIXED",
    )
    eye_start_blink_count: IntProperty(
        name="Parpadeos en inicio", default=2, min=1, max=10,
        description="Numero de parpadeos durante el estado inicial",
    )
    eye_start_blink_duration: IntProperty(
        name="Frames por parpadeo inicio", default=9, min=5, max=30,
        description="Duracion de cada parpadeo en el estado inicial",
    )
    # Expresion
    eye_start_expression: EnumProperty(
        name="Expresion inicio",
        items=EXPRESSION_PRESETS,
        default="NEUTRAL",
        description="Expresion del estado inicial de los ojos",
    )
    eye_start_expr_value: FloatProperty(
        name="Valor expresion inicio",
        default=1.0, min=0.0, max=1.0, precision=2,
    )
    # Geometria
    eye_start_geo_mode: EnumProperty(
        name="Forma inicio",
        items=[
            ("NONE",   "Sin cambio",    "Mantiene la forma original"),
            ("ROUND",  "Redondo",       "Ojos redondeados"),
            ("SQUINT", "Entrecerrado",  "Aplana verticalmente"),
            ("WIDE",   "Abierto ancho", "Expande horizontalmente"),
            ("FLAT",   "Plano/cerrado", "Aplana completamente"),
            ("CUSTOM", "Personalizado", "Usa el shape key activo"),
        ],
        default="NONE",
    )
    eye_start_geo_intensity: FloatProperty(
        name="Intensidad forma inicio",
        default=1.0, min=0.0, max=2.0, precision=2,
    )
    # Transforms ojo izquierdo
    eye_start_L_loc_x: FloatProperty(name="Loc X", default=0.106646, precision=4)
    eye_start_L_loc_y: FloatProperty(name="Loc Y", default=0.270456, precision=4)
    eye_start_L_loc_z: FloatProperty(name="Loc Z", default=1.70082,  precision=4)
    eye_start_L_rot_x: FloatProperty(name="Rot X", default=0.0, subtype="ANGLE")
    eye_start_L_rot_y: FloatProperty(name="Rot Y", default=0.0, subtype="ANGLE")
    eye_start_L_rot_z: FloatProperty(name="Rot Z", default=0.0, subtype="ANGLE")
    eye_start_L_sca_x: FloatProperty(name="Sca X", default=1.555, min=0.001, max=10.0, precision=3)
    eye_start_L_sca_y: FloatProperty(name="Sca Y", default=0.496018, min=0.001, max=10.0, precision=3)
    eye_start_L_sca_z: FloatProperty(name="Sca Z", default=3.55, min=0.001, max=10.0, precision=3)
    # Transforms ojo derecho
    eye_start_R_loc_x: FloatProperty(name="Loc X", default=-0.1053,  precision=4)
    eye_start_R_loc_y: FloatProperty(name="Loc Y", default=0.256331, precision=4)
    eye_start_R_loc_z: FloatProperty(name="Loc Z", default=1.70043,  precision=4)
    eye_start_R_rot_x: FloatProperty(name="Rot X", default=0.0, subtype="ANGLE")
    eye_start_R_rot_y: FloatProperty(name="Rot Y", default=0.0, subtype="ANGLE")
    eye_start_R_rot_z: FloatProperty(name="Rot Z", default=0.0, subtype="ANGLE")
    eye_start_R_sca_x: FloatProperty(name="Sca X", default=1.555, min=0.001, max=10.0, precision=3)
    eye_start_R_sca_y: FloatProperty(name="Sca Y", default=0.496018, min=0.001, max=10.0, precision=3)
    eye_start_R_sca_z: FloatProperty(name="Sca Z", default=3.55, min=0.001, max=10.0, precision=3)

    # ── CAMBIOS INTERMEDIOS DE OJOS ───────────────────────────────────────
    eye_slots:     CollectionProperty(type=Cerdo_1EyeSlotItem)
    eye_slot_idx:  IntProperty(default=0)

    # ── Intervalos de parpadeo automatico (multi-intervalo) ───────────────────
    blink_intervals:     CollectionProperty(type=Cerdo_1BlinkInterval)
    blink_interval_idx:  IntProperty(default=0)

    # ── Intervalos de expresiones de ojos (multi-intervalo) ───────────────────
    expr_intervals:     CollectionProperty(type=Cerdo_1EyeExprInterval)
    expr_interval_idx:  IntProperty(default=0)

    # ── ESTADO FINAL DE OJOS ──────────────────────────────────────────────
    eye_end_label: StringProperty(
        name="Etiqueta fin ojos",
        default="Ojos fin",
        description="Nombre descriptivo del estado final de los ojos",
    )
    eye_end_duration: IntProperty(
        name="Frames estado fin ojos",
        default=10, min=1, soft_max=99999,
        description="Cuantos frames se mantiene el estado final de ojos. Sin limite superior.",
    )
    eye_end_interp: EnumProperty(
        name="Interpolacion entrada FIN ojos",
        description="Tipo de interpolacion de entrada hacia el estado final de ojos",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )
    eye_end_blink_mode: EnumProperty(
        name="Modo fin ojos",
        description="Comportamiento de los ojos durante el estado final",
        items=[
            ("FIXED",  "Posicion fija",  "Los ojos permanecen en la posicion base sin parpadear"),
            ("BLINK",  "Parpadeo",       "Los ojos parpadean con normalidad durante el estado final"),
        ],
        default="FIXED",
    )
    eye_end_blink_count: IntProperty(
        name="Parpadeos en fin", default=2, min=1, max=10,
        description="Numero de parpadeos durante el estado final",
    )
    eye_end_blink_duration: IntProperty(
        name="Frames por parpadeo fin", default=9, min=5, max=30,
        description="Duracion de cada parpadeo en el estado final",
    )
    # Expresion
    eye_end_expression: EnumProperty(
        name="Expresion fin",
        items=EXPRESSION_PRESETS,
        default="NEUTRAL",
        description="Expresion del estado final de los ojos",
    )
    eye_end_expr_value: FloatProperty(
        name="Valor expresion fin",
        default=1.0, min=0.0, max=1.0, precision=2,
    )
    # Geometria
    eye_end_geo_mode: EnumProperty(
        name="Forma fin",
        items=[
            ("NONE",   "Sin cambio",    "Mantiene la forma original"),
            ("ROUND",  "Redondo",       "Ojos redondeados"),
            ("SQUINT", "Entrecerrado",  "Aplana verticalmente"),
            ("WIDE",   "Abierto ancho", "Expande horizontalmente"),
            ("FLAT",   "Plano/cerrado", "Aplana completamente"),
            ("CUSTOM", "Personalizado", "Usa el shape key activo"),
        ],
        default="NONE",
    )
    eye_end_geo_intensity: FloatProperty(
        name="Intensidad forma fin",
        default=1.0, min=0.0, max=2.0, precision=2,
    )
    # Transforms ojo izquierdo
    eye_end_L_loc_x: FloatProperty(name="Loc X", default=0.106646, precision=4)
    eye_end_L_loc_y: FloatProperty(name="Loc Y", default=0.270456, precision=4)
    eye_end_L_loc_z: FloatProperty(name="Loc Z", default=1.70082,  precision=4)
    eye_end_L_rot_x: FloatProperty(name="Rot X", default=0.0, subtype="ANGLE")
    eye_end_L_rot_y: FloatProperty(name="Rot Y", default=0.0, subtype="ANGLE")
    eye_end_L_rot_z: FloatProperty(name="Rot Z", default=0.0, subtype="ANGLE")
    eye_end_L_sca_x: FloatProperty(name="Sca X", default=1.555, min=0.001, max=10.0, precision=3)
    eye_end_L_sca_y: FloatProperty(name="Sca Y", default=0.496018, min=0.001, max=10.0, precision=3)
    eye_end_L_sca_z: FloatProperty(name="Sca Z", default=3.55, min=0.001, max=10.0, precision=3)
    # Transforms ojo derecho
    eye_end_R_loc_x: FloatProperty(name="Loc X", default=-0.1053,  precision=4)
    eye_end_R_loc_y: FloatProperty(name="Loc Y", default=0.256331, precision=4)
    eye_end_R_loc_z: FloatProperty(name="Loc Z", default=1.70043,  precision=4)
    eye_end_R_rot_x: FloatProperty(name="Rot X", default=0.0, subtype="ANGLE")
    eye_end_R_rot_y: FloatProperty(name="Rot Y", default=0.0, subtype="ANGLE")
    eye_end_R_rot_z: FloatProperty(name="Rot Z", default=0.0, subtype="ANGLE")
    eye_end_R_sca_x: FloatProperty(name="Sca X", default=1.555, min=0.001, max=10.0, precision=3)
    eye_end_R_sca_y: FloatProperty(name="Sca Y", default=0.496018, min=0.001, max=10.0, precision=3)
    eye_end_R_sca_z: FloatProperty(name="Sca Z", default=3.55, min=0.001, max=10.0, precision=3)

    start_frame: IntProperty(
        name="Frame inicio",
        description="Frame de la timeline donde comienza la animacion. Sin limite superior: puede ser 1, 500, 1250, 12000, etc.",
        default=1, min=1, soft_max=99999,
    )
    fps: IntProperty(
        name="FPS",
        description="Fotogramas por segundo",
        default=24, min=1, max=120,
    )
    entry_ratio: FloatProperty(
        name="Blend entrada",
        description="Porcion inicial de blend suave (0.05 a 0.49)",
        default=0.30, min=0.05, max=0.49, step=1, precision=2,
    )
    exit_ratio: FloatProperty(
        name="Blend salida",
        description="Porcion final de blend suave (0.05 a 0.49)",
        default=0.30, min=0.05, max=0.49, step=1, precision=2,
    )

    # ── Exportacion formato slot ──
    export_slot_number: IntProperty(
        name="Numero de slot",
        description="Numero del slot (ej: 2 -> slot_002_tipo.py)",
        default=1, min=1, max=999,
    )
    export_name: StringProperty(name="Nombre", default="cerdo_1_nueva_animacion")
    export_type: StringProperty(name="Tipo",   default="custom")
    export_desc: StringProperty(name="Desc",   default="Animacion generada con Cerdo_1 Studio")

    export_scope: EnumProperty(
        name="Alcance de exportacion",
        description=(
            "Que parte de la animacion se exporta al .py:\n"
            "  Segmento activo  — solo el segmento seleccionado en Paso 3\n"
            "  Segmentos marcados — todos los segmentos con 'Exportar' activado\n"
            "  Animacion completa — toda la timeline generada (comportamiento previo)"
        ),
        items=[
            ("FULL",     "Animacion completa",    "Exporta todos los frames generados (frame_inicio → frame_fin)",  "RENDER_ANIMATION", 0),
            ("ACTIVE",   "Segmento activo",        "Exporta solo el segmento activo en el Paso 3",                  "SOLO_ON",          1),
            ("SELECTED", "Segmentos marcados",     "Exporta los segmentos que tienen activada la opcion 'Exportar'","CHECKMARK",        2),
        ],
        default="FULL",
    )

    # ── NUEVO: key_point seleccionado para la accion ──
    selected_key_point: IntProperty(
        name="Index key_point",
        description="Index del punto clave del recorrido donde se realiza la accion (de historia_cerdo_1.json)",
        default=1, min=1,
    )
    # Informacion visual del key_point elegido (solo lectura, actualizado al cargar)
    key_point_info: StringProperty(default="-- carga el JSON primero --")

    # ── NUEVO: key_point para posicion inicial del ROOT ──
    root_pos_key_point: EnumProperty(
        name="KeyPoint para Root",
        description="Coordenada del recorrido para la posicion inicial del ROOT (Body_cerdo_1)",
        items=_enum_key_points,
    )

    extract_label:       StringProperty(name="Nombre nueva pose", default="")
    extract_frame:       IntProperty(name="Frame", default=1, min=0, max=99999)
    extract_use_current: BoolProperty(name="Frame actual", default=True)

    # ── Extraer pose rapida (Paso 3, dentro de cada segmento) ─────────────
    # Version simplificada de "Extraer Nueva Pose" (extract_label/_frame/
    # _use_current arriba): detecta el armature de Cerdo_1 automaticamente
    # (sin selector), nombra la pose sola segun que huesos se movieron, y
    # guarda el .json con un solo click. El archivo/indice/etiqueta que
    # acaba de generar "Guardar" quedan aca en espera de que el usuario
    # presione "Importar" (que los agrega a seg.action_poses del segmento
    # correspondiente) y luego se limpian para el siguiente ciclo.
    quickpose_pending_file:  StringProperty(default="")
    quickpose_pending_index: IntProperty(default=0)
    quickpose_pending_label: StringProperty(default="")

    # ── Sistema de oscilaciones de bones personalizadas ──────────────────────
    bone_oscillations: PointerProperty(type=Cerdo_1BoneOscillationsSettings)

    last_export_path: StringProperty(default="")
    anim_generated:   BoolProperty(default=False)
    total_frames_gen: IntProperty(default=0)
    end_frame_gen:    IntProperty(default=0)
    status_msg:       StringProperty(default="")

    # ── Configuracion: guardar/cargar sesion de trabajo ──
    config_dir: StringProperty(
        name="Carpeta Configuraciones",
        default=DEFAULT_CONFIG_DIR,
        subtype="DIR_PATH",
        description="Carpeta donde se guardan/cargan las configuraciones de trabajo (.json)",
    )
    config_name: StringProperty(
        name="Nombre configuracion",
        default="mi_configuracion",
        description="Nombre del archivo de configuracion a guardar (sin extension)",
    )

    # ── Libreria de expresiones de ojos ──────────────────────────────────────
    eye_lib_dir: StringProperty(
        name="Libreria de ojos",
        default=_DEFAULT_EYE_LIB_DIR,
        subtype="DIR_PATH",
        description="Carpeta con los JSON de expresiones de ojos",
    )
    eye_lib_entries:  CollectionProperty(type=Cerdo_1EyeLibEntry)
    eye_lib_idx:      IntProperty(default=0)
    eye_lib_save_name: StringProperty(
        name="Nombre", default="",
        description="Nombre de la expresion a guardar en la libreria",
    )
    eye_lib_save_desc: StringProperty(
        name="Descripcion", default="",
        description="Descripcion opcional de la expresion",
    )
    eye_config_name: StringProperty(
        name="Nombre config ojos",
        default="ojos_config",
        description="Nombre del archivo de configuracion de ojos a guardar",
    )



# =============================================================================
# PASO 3: SLOT DE POSE DENTRO DE UN SEGMENTO
# =============================================================================

# =============================================================================
# PASO 3 — SISTEMA DE POSES FLEXIBLE (Kebyn, 2026-07-10)
# =============================================================================

def _on_pose_slot_duration_update(self, context):
    """
    Callback de 'update' del campo 'duration' de Cerdo_1SegmentPoseSlot.
    Cuando se edita el numero de frames de una pose directamente en la lista
    (sin pasar por los operadores Agregar/Editar), este callback busca el
    Cerdo_1AnimSegment dueño de este slot y reajusta automaticamente su
    frame_end (y frame_end_auto en modo 1 coordenada) para que el intervalo
    del segmento quede siempre igual a la suma de duraciones de sus poses.

    CASCADA (Kebyn, 2026-07-10): si ese frame_end cambia, desplaza (mismo
    delta) todos los DEMAS segmentos cuyo frame_start sea posterior al de
    este segmento, para que la secuencia completa (anteriores y
    posteriores) se mantenga contigua y no se desfase. Cada segmento
    desplazado conserva su propia duracion, solo cambia su posicion en la
    timeline.

    Se identifica el segmento dueño comparando punteros RNA (as_pointer())
    porque un PropertyGroup anidado no guarda referencia directa a su padre.

    FIX (Kebyn, 2026-08-04): igual que en _calc_seg_frames /
    _sync_seg_interval (operators_segments.py), si el segmento ya tiene un
    rango fijo del Paso 2/3 (frame_end_planned > frame_start_planned) y no
    esta en modo 1 coordenada, ese rango NO se toca aca -- las poses viven
    DENTRO de el, no lo redefinen. Solo se sigue recalculando frame_end
    desde la suma de duraciones para segmentos en modo 1 coordenada o sin
    foto del Paso 2 (compatibilidad con proyectos viejos).
    """
    segs_data = getattr(context.scene, "cerdo_1_segs", None)
    if segs_data is None:
        return
    _self_ptr = self.as_pointer()
    for seg in segs_data.segments:
        for slot in seg.action_poses:
            if slot.as_pointer() == _self_ptr:
                if not seg.action_poses:
                    return
                if (not seg.single_coord_mode) and seg.frame_end_planned > seg.frame_start_planned:
                    # Rango fijo del Paso 2/3: las poses no lo redefinen.
                    return
                old_end = seg.frame_end
                total = sum(ap.duration for ap in seg.action_poses)
                total = max(total, 1)
                new_end = seg.frame_start + total - 1
                delta = new_end - old_end
                seg.frame_end = new_end
                if seg.single_coord_mode:
                    seg.frame_end_auto = new_end

                if delta != 0:
                    _seg_ptr = seg.as_pointer()
                    for other in segs_data.segments:
                        if other.as_pointer() == _seg_ptr:
                            continue
                        if other.frame_start > seg.frame_start:
                            other.frame_start += delta
                            other.frame_end   += delta
                            if other.single_coord_mode:
                                other.frame_end_auto += delta
                return


class Cerdo_1SegmentPoseSlot(PropertyGroup):
    """Un slot de pose dentro de un Cerdo_1AnimSegment."""
    json_file:   StringProperty(default="", description="Archivo .json de la pose")
    pose_index:  IntProperty(default=0, description="Indice del registro dentro del .json")
    pose_label:  StringProperty(default="")
    pose_name:   StringProperty(default="", description="Nombre descriptivo de la pose")
    duration:    IntProperty(name="Frames", default=24, min=1, max=9999,
                              update=_on_pose_slot_duration_update)
    entry_ratio: FloatProperty(name="Entrada %", default=0.3, min=0.0, max=1.0, precision=2)
    exit_ratio:  FloatProperty(name="Salida %",  default=0.3, min=0.0, max=1.0, precision=2)
    interp_type: EnumProperty(name="Interpolacion", items=INTERP_TYPE_ITEMS, default="SMOOTH")
    rot_x: FloatProperty(name="Rot X", default=0.0, precision=4)
    rot_y: FloatProperty(name="Rot Y", default=0.0, precision=4)
    rot_z: FloatProperty(name="Rot Z", default=0.0, precision=4)
    pos_x: FloatProperty(name="Pos X", default=0.0, precision=4)
    pos_y: FloatProperty(name="Pos Y", default=0.0, precision=4)
    pos_z: FloatProperty(name="Pos Z", default=0.0, precision=4)
    # Frame absoluto donde empieza esta pose. Si manual_start=False, este
    # valor se RECALCULA automaticamente al CONCATENAR (comportamiento de
    # siempre: apilado secuencial tras la pose anterior). Si manual_start=
    # True, el usuario fijo este valor a mano y CONCATENAR lo respeta tal
    # cual (siempre que no invada a la pose anterior), dejando un hueco
    # (interpolado, sin corte) entre el fin de la pose previa y el inicio
    # de esta.
    frame_abs_start: IntProperty(name="Frame inicio absoluto", default=0)
    manual_start: BoolProperty(
        name="Frame de inicio manual",
        default=False,
        description=(
            "Si esta activo, 'Frame inicio absoluto' se usa tal cual en vez "
            "de calcularse automaticamente tras la pose anterior. Permite "
            "elegir en que frame (dentro del rango del segmento) debe "
            "empezar esta pose."
        ),
    )

    # ── CALIFICACION (1-10) ──────────────────────────────────
    # El usuario describe que pidio y que tan bien esta pose representa
    # ese pedido. 10 = coincide exactamente con lo solicitado.
    rating_query: StringProperty(
        name="Que se pidio",
        default="",
        description="Texto/historia o movimiento especifico que se pidio para esta pose",
    )
    rating_score: IntProperty(
        name="Calificacion (1-10)",
        default=10, min=1, max=10,
        description="10 = la pose representa exactamente lo que se pidio",
    )
    rating_comment: StringProperty(
        name="Comentario",
        default="",
        description="Detalle opcional de por que se califico asi (ej: que le falto o que sobro)",
    )
    # Cache de solo-lectura (se actualiza al guardar) para mostrar en la lista
    # sin tener que reabrir el archivo de la pose en cada redibujado.
    rating_avg_cache:    FloatProperty(default=0.0)
    rating_count_cache:  IntProperty(default=0)
    rating_status_cache: StringProperty(default="NUEVA")


# =============================================================================
# PASO 3: SEGMENTO DE ANIMACION
# =============================================================================

class Cerdo_1BoneBlockInterval(PropertyGroup):
    """
    Un intervalo de frames durante el cual un bone especifico del Bloqueador
    de bones queda excluido de las poses del segmento.
    Un mismo bone puede tener multiples intervalos independientes
    (ej: bloqueado en 60-100, luego otra vez en 500-630, etc).
    """
    frame_start: IntProperty(
        name="Inicio", default=1, min=0,
        description="Frame (absoluto) desde el cual este bone queda bloqueado",
    )
    frame_end: IntProperty(
        name="Fin", default=10, min=0,
        description="Frame (absoluto) hasta el cual este bone queda bloqueado",
    )
    enabled: BoolProperty(
        name="Activo", default=True,
        description="Si esta desactivado, este intervalo se ignora al aplicar el segmento",
    )


class Cerdo_1BoneBlockEntry(PropertyGroup):
    """
    Contenedor de intervalos de bloqueo para UN bone dentro de un segmento.
    'bone_key' corresponde al nombre del atributo filter_* del bone
    (ej: 'filter_right_leg') para poder ubicarlo facilmente.
    """
    bone_key:  StringProperty(name="Bone", default="")
    intervals: CollectionProperty(type=Cerdo_1BoneBlockInterval)
    intervals_idx: IntProperty(default=0)


class Cerdo_1AnimSegment(PropertyGroup):
    """
    Un segmento dentro de la animacion generada por Pasos 1+2.
    Contiene su propio intervalo de frames y configuracion completa de poses.
    """
    label: StringProperty(name="Etiqueta", default="Segmento")

    frame_start: IntProperty(name="Frame inicio", default=1, min=1, soft_max=99999)
    frame_end:   IntProperty(name="Frame fin",    default=48, min=2, soft_max=99999)

    # FIX (aislar Paso 2 de Paso 3, 2026-08-04): "foto" del frame_start/
    # frame_end tal como quedaron definidos por el Paso 2 (division del
    # recorrido en AutoSplitFromConfig, "Actualizar" por frames-por-parada,
    # o carga de un configuracion.json). frame_start/frame_end de arriba
    # SIGUEN siendo mutables -- las poses del Paso 3 (_sync_seg_interval,
    # _on_pose_slot_duration_update) los recalculan y los desplazan en
    # cascada, porque eso es lo que necesitan Concatenar/NLA/Reproducir
    # para reflejar la duracion real de las poses ya cargadas.
    #
    # Pero calcular_estimacion_slots() (path_recorder.py) -- la fuente del
    # panel "Estimacion de segmentos" del PASO 2 -- antes leia esos mismos
    # campos mutables, asi que agregar/editar/quitar una pose en el Paso 3
    # hacia que el numero de frames mostrado en el Paso 2 cambiara solo,
    # aunque nada de la configuracion del Paso 2 se hubiera tocado.
    #
    # Con esta foto, el Paso 2 siempre muestra lo que el Paso 2 configuro
    # -- nunca lo que el Paso 3 hizo despues -- y el Paso 3 sigue
    # funcionando exactamente igual que antes con frame_start/frame_end.
    # 0 = "no seteado" (compatibilidad con segmentos/config viejos): en
    # ese caso se cae de vuelta a frame_start/frame_end en vivo.
    frame_start_planned: IntProperty(name="Frame inicio (Paso 2, fijo)", default=0, min=0, soft_max=99999)
    frame_end_planned:   IntProperty(name="Frame fin (Paso 2, fijo)",    default=0, min=0, soft_max=99999)

    # Slots de accion intermedios
    action_poses:     CollectionProperty(type=Cerdo_1SegmentPoseSlot)
    action_poses_idx: IntProperty(default=0)

    fps:         IntProperty(name="FPS", default=24, min=1, max=120)
    entry_ratio: FloatProperty(name="Blend entrada", default=0.30, min=0.05, max=0.49,
                               step=1, precision=2)
    exit_ratio:  FloatProperty(name="Blend salida",  default=0.30, min=0.05, max=0.49,
                               step=1, precision=2)

    export_slot_number: IntProperty(name="Numero de slot", default=1, min=1, max=999)
    export_type:        StringProperty(name="Tipo de animacion", default="idle")
    export_desc:        StringProperty(name="Descripcion", default="")
    export_selected:    BoolProperty(name="Exportar este segmento", default=False)
    seg_action_name:    StringProperty(name="Action del segmento", default="")

    frame_mid:     IntProperty(name="Frame intermedio", default=0, min=0, soft_max=99999)
    pose_mid_file: StringProperty(name="Pose intermedia", default="")
    pose_mid_label: StringProperty(default="")
    interp_type:   EnumProperty(name="Interpolacion", items=INTERP_TYPE_ITEMS, default="SMOOTH")
    interp_mid_to_end: EnumProperty(name="Interp. mid->fin", items=INTERP_TYPE_ITEMS, default="SMOOTH")

    blend_in_frames:  IntProperty(name="Blend entrada (frames)", default=8, min=0, max=120)
    blend_out_frames: IntProperty(name="Blend salida (frames)",  default=8, min=0, max=120)

    # Bones afectados (grupos)
    affect_body:      BoolProperty(name="Cuerpo",      default=True)
    affect_left_arm:  BoolProperty(name="Brazo Izq.",  default=True)
    affect_right_arm: BoolProperty(name="Brazo Der.",  default=True)
    affect_left_leg:  BoolProperty(name="Pierna Izq.", default=True)
    affect_right_leg: BoolProperty(name="Pierna Der.", default=True)
    affect_root:      BoolProperty(name="Root", default=False)
    affect_shield:    BoolProperty(name="Accesorio 1", default=False)
    affect_spear:     BoolProperty(name="Accesorio 2", default=False)

    blend_strength: FloatProperty(name="Fuerza de mezcla", default=1.0, min=0.0, max=1.0, precision=2)

    # ── Bloqueador de bones (Paso 3) ──────────────────────────────────────────
    # Los bones marcados NO reciben keyframes de configuracion en CONCATENAR.
    # Por defecto las piernas estan bloqueadas (el recorrido base las controla).
    # El bloqueador esta siempre desplegado en el panel (no requiere expandir).
    # Esta propiedad se conserva solo por compatibilidad con configuraciones
    # guardadas anteriormente; ya no controla el despliegue ni el bloqueo.
    filter_show:     BoolProperty(name="Bloqueador de bones", default=True, description="Legado: el bloqueador de bones ahora esta siempre activo y desplegado")

    # Root / caderas
    filter_main_bone: BoolProperty(name="Armature",      default=False)
    filter_hips:      BoolProperty(name="Body_cerdo_1",   default=False)

    # Columna
    filter_body:      BoolProperty(name="Body:Bend_cerdo_1",  default=False)
    filter_spine:     BoolProperty(name="Body:Bend_cerdo_1",  default=False)
    filter_spine1:    BoolProperty(name="Body:Bend_cerdo_1", default=False)
    filter_spine2:    BoolProperty(name="Body:Bend_cerdo_1", default=False)

    # Cabeza / cuello
    filter_neck:      BoolProperty(name="Head_cerdo_1",   default=False)
    filter_face:      BoolProperty(name="Head_cerdo_1",   default=False)

    # Brazos
    filter_right_arm:   BoolProperty(name="Leg:FR_cerdo_1",  default=False)
    filter_right_elbow: BoolProperty(name="Leg:FR:Bend_cerdo_1",  default=False)
    filter_left_arm:    BoolProperty(name="Leg:FL_cerdo_1",   default=False)
    filter_left_elbow:  BoolProperty(name="Leg:FL:Bend_cerdo_1",   default=False)

    # Piernas (filtradas por defecto — el recorrido base las controla)
    filter_right_leg:   BoolProperty(name="Leg:BR_cerdo_1", default=True)
    filter_right_knee:  BoolProperty(name="Leg:BR:Bend_cerdo_1",  default=True)
    filter_left_leg:    BoolProperty(name="Leg:BL_cerdo_1",  default=True)
    filter_left_knee:   BoolProperty(name="Leg:BL:Bend_cerdo_1",   default=True)

    # Accesorios / no_bone
    filter_no_bone_01: BoolProperty(name="no_bone_01", default=False)
    filter_no_bone_02: BoolProperty(name="no_bone_02", default=False)
    filter_no_bone_03: BoolProperty(name="no_bone_03", default=False)
    filter_no_bone_04: BoolProperty(name="no_bone_04", default=False)
    filter_no_bone_05: BoolProperty(name="no_bone_05", default=False)
    filter_no_bone_06: BoolProperty(name="no_bone_06", default=False)
    filter_no_bone_07: BoolProperty(name="no_bone_07", default=False)
    filter_no_bone_08: BoolProperty(name="no_bone_08", default=False)

    # Intervalos de bloqueo por bone (bloqueo total independiente del checkbox
    # de arriba). Un mismo bone puede tener N intervalos de frames distintos.
    bone_blocks: CollectionProperty(type=Cerdo_1BoneBlockEntry)

    enabled: BoolProperty(name="Activo", default=True)
    show_config: BoolProperty(name="Mostrar configuracion", default=True)
    single_coord_mode: BoolProperty(name="Modo 1 coordenada", default=False)
    frame_end_auto: IntProperty(name="Frame fin (calculado)", default=0, min=0, soft_max=99999)

    # ── Filtro: Lanzar / Recoger Objetos ─────────────────────────────────
    throws: PointerProperty(type=Cerdo_1ThrowsSettings)

    # ── Filtro: Invisibilidad de Malla (debajo de Lanzar/Recoger/Mantener) ─
    hide_mesh: PointerProperty(type=Cerdo_1HideMeshSettings)

    # ── AISLAMIENTO POR SEGMENTO (Kebyn + Claude, 2026-08-03) ────────────
    # ANTES: los Filtros organicos y el Parpadeo automatico que se veian
    # dentro del box de CADA segmento en el panel (Paso 3) en realidad
    # apuntaban a scene.cerdo_1_st.organic / scene.cerdo_1_st.blink_intervals -- una
    # UNICA instancia global compartida por todos los segmentos. El panel
    # dibujaba una copia visual por segmento, pero las tres (o las N que
    # hubiera) escribian y leian el mismo dato: al editar un valor en
    # cualquier segmento, ese valor quedaba "puesto" para todos, y al
    # CONCATENAR (CERDO_1SEG_OT_ConcatenateAll / CERDO_1_ST_OT_Concatenate) cada
    # segmento se procesaba con exactamente los mismos filtros organicos y
    # los mismos intervalos de parpadeo, sin importar cual se hubiera
    # tocado por ultimo.
    #
    # AHORA: cada Cerdo_1AnimSegment tiene su PROPIA instancia de
    # Cerdo_1OrganicFilters y su PROPIA coleccion de Cerdo_1BlinkInterval.
    # Son completamente independientes entre segmentos -- editar uno no
    # afecta a los demas, y CONCATENAR usa exclusivamente los valores del
    # segmento que esta procesando en cada paso del loop.
    organic: PointerProperty(type=Cerdo_1OrganicFilters)
    blink_intervals: CollectionProperty(type=Cerdo_1BlinkInterval)
    blink_interval_idx: IntProperty(default=0)

    # ── AISLAMIENTO POR SEGMENTO -- Expresiones de ojos (Kebyn + Claude,
    # 2026-08-04) ──────────────────────────────────────────────────────
    # MISMO problema que blink_intervals arriba, pero para el panel E2)
    # "Expresiones de ojos" del box de cada segmento (Paso 3): el panel ya
    # se dibujaba una vez POR segmento, pero seguia leyendo/escribiendo
    # scene.cerdo_1_st.expr_intervals -- una unica coleccion global compartida.
    # Resultado: agregar o quitar una expresion en el box de un segmento la
    # agregaba/quitaba para TODOS los segmentos, porque en realidad todos
    # apuntaban al mismo dato. Se agrega aca la coleccion PROPIA de cada
    # segmento, exactamente igual que blink_intervals.
    expr_intervals: CollectionProperty(type=Cerdo_1EyeExprInterval)
    expr_interval_idx: IntProperty(default=0)

    # ── Filtro "Reir" -- oscilacion vertical sincronizada de ambos ojos
    # (Kebyn, 2026-08-18) ────────────────────────────────────────────────
    # Mismo criterio de aislamiento por segmento que blink_intervals /
    # expr_intervals arriba: cada Cerdo_1AnimSegment tiene su PROPIA
    # coleccion de Cerdo_1LaughInterval, independiente de los demas
    # segmentos. El switch maestro (laugh_enabled) vive en
    # scene.cerdo_1_st.eye_expr, igual que blink_enabled/expr_intervals_enabled.
    laugh_intervals: CollectionProperty(type=Cerdo_1LaughInterval)
    laugh_interval_idx: IntProperty(default=0)

    # ── Filtro "Entendiendo" -- parabola de ambos ojos, Izquierda/Derecha
    # (Kebyn, 2026-08-18) ────────────────────────────────────────────────
    # Mismo criterio de aislamiento por segmento que laugh_intervals
    # arriba: cada Cerdo_1AnimSegment tiene su PROPIA coleccion de
    # Cerdo_1UnderstandInterval, independiente de los demas segmentos. El
    # switch maestro (understand_enabled) vive en scene.cerdo_1_st.eye_expr,
    # igual que laugh_enabled.
    understand_intervals: CollectionProperty(type=Cerdo_1UnderstandInterval)
    understand_interval_idx: IntProperty(default=0)

    # ── AISLAMIENTO POR SEGMENTO -- Setup de Shape Keys de ojos (Kebyn +
    # Claude, 2026-08-05) ────────────────────────────────────────────────
    # Ver Cerdo_1EyeShapeKeySetup arriba. Cada segmento genera su PROPIO
    # juego de shape keys de expresion (nombres con sufijo "__seg<indice>",
    # ver eye_system.build_expression_shape_keys) usando esta config, en
    # vez de compartir los shape keys "Feliz"/"Triste"/etc. globales.
    eye_shapekey: PointerProperty(type=Cerdo_1EyeShapeKeySetup)


# =============================================================================
# PASO 3: CONFIGURACION GLOBAL DE SEGMENTOS
# =============================================================================

class Cerdo_1AnimSegmentsSettings(PropertyGroup):
    """
    Coleccion de Cerdo_1AnimSegment y estado global del sistema de refinado (Paso 3).
    Se almacena en bpy.types.Scene.cerdo_1_segs.
    """
    segments:      CollectionProperty(type=Cerdo_1AnimSegment)
    active_index:  IntProperty(default=0)
    # El sistema de objetos vive al nivel de Segmentos. Este índice selecciona
    # qué segmento recibe la configuración editada en el panel global.
    throws_segment_index: IntProperty(name="Segmento de objetos", default=0, min=0, soft_max=999)
    armature_name: StringProperty(name="Armature", default="pig.arma_cerdo_1")
    segs_applied:  BoolProperty(name="Segmentos aplicados", default=False)
    status_msg:    StringProperty(name="Estado", default="")
    poses_dir:     StringProperty(
        name="Carpeta de poses",
        default=r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\cerdo_1\refinar\poses",
        subtype="DIR_PATH",
    )

    # ── Propiedades de edicion para el formulario "Crear segmento" (Paso 3) ──
    edit_label: StringProperty(
        name="Nombre del segmento",
        default="Segmento",
        description="Nombre descriptivo del nuevo segmento",
    )
    edit_frame_start: IntProperty(
        name="Frame inicio",
        default=1, min=1, soft_max=99999,
        description="Frame donde comienza el segmento",
    )
    edit_frame_end: IntProperty(
        name="Frame fin",
        default=48, min=2, soft_max=99999,
        description="Frame donde termina el segmento",
    )

    # ── Propiedades del modulador / pose intermedia (Legacy modulator) ──
    edit_use_mid: BoolProperty(
        name="Usar pose intermedia",
        default=False,
        description="Activar una pose intermedia entre inicio y fin del segmento",
    )
    edit_frame_mid: IntProperty(
        name="Frame intermedio",
        default=0, min=0, soft_max=99999,
        description="Frame donde se aplica la pose intermedia",
    )
    edit_pose_mid_file: StringProperty(
        name="Archivo pose intermedia",
        default="",
        description="Ruta al JSON de la pose intermedia",
    )
    edit_pose_mid_label: StringProperty(
        name="Etiqueta pose intermedia",
        default="",
        description="Etiqueta de la pose intermedia dentro del archivo JSON",
    )
    edit_interp: EnumProperty(
        name="Interpolacion inicio->fin",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
        description="Tipo de interpolacion para el segmento completo",
    )
    edit_interp_mid: EnumProperty(
        name="Interpolacion mid->fin",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
        description="Tipo de interpolacion desde la pose intermedia hasta el fin",
    )
    edit_start_frames: IntProperty(
        name="Blend entrada (frames)",
        default=8, min=0, max=120,
        description="Frames de blend al inicio del segmento",
    )
    edit_end_frames: IntProperty(
        name="Blend salida (frames)",
        default=8, min=0, max=120,
        description="Frames de blend al final del segmento",
    )
