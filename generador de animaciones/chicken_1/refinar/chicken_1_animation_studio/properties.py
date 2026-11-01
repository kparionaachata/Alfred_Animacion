# -*- coding: utf-8 -*-
"""
properties.py — Chicken 1 Animation Studio v1.8
PropertyGroups: Chicken1EyeExpressionSettings, Chicken1OrganicFilters,
Chicken1PoseSlotItem, Chicken1StudioSettings.
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
    EXPRESSION_PRESETS, INTERP_TYPE_ITEMS,
)
# Ruta por defecto de la libreria de ojos (definida en eye_library para evitar ciclo)
_DEFAULT_EYE_LIB_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\alfred\refinar\ojos"
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
        print(f"[AlfredStudio] No se pudo leer historia_chicken_1.json: {e}")
        return {}

def get_key_points(historia_data):
    """Devuelve la lista de key_points del JSON de historia."""
    return historia_data.get("recorrido", {}).get("key_points", [])

def _enum_key_points(self, context):
    """Genera enum con los key_points del historia_chicken_1.json."""
    st = context.scene.ch1st
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
class Chicken1EyeExpressionSettings(PropertyGroup):
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
    # Coordenadas base = posicion correcta de los ojos en el rostro de Alfred.
    # Cualquier cambio en el panel es un DELTA relativo a estas posiciones.
    # ojo_derecho_chicken_1  base: (-0.1053,  0.256331, 1.70043)
    # ojo_izquierdo_chicken_1 base: ( 0.106646, 0.270456, 1.70082)

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




class Chicken1BlinkInterval(PropertyGroup):
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
        default=2, min=1, max=40,
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


class Chicken1EyeExprInterval(PropertyGroup):
    """
    Un intervalo de expresion de ojos en la timeline.
    Cada intervalo define tres fases: Inicio (neutral) → N° Cambio (expresion) → Fin (neutral).
    En una misma animacion pueden coexistir multiples intervalos con distintas emociones.
    """
    label: StringProperty(
        name="Etiqueta",
        default="Expresion",
        description="Nombre descriptivo de este intervalo de expresion",
    )
    frame_start: IntProperty(
        name="Frame inicio",
        default=1, min=0,
        description="Frame donde comienza la fase de entrada (neutral → expresion)",
    )
    frame_peak: IntProperty(
        name="Frame pico",
        default=20, min=0,
        description="Frame donde se alcanza la expresion maxima (N° cambio de ojos)",
    )
    frame_end: IntProperty(
        name="Frame fin",
        default=40, min=1,
        description="Frame donde termina la expresion (regreso a neutral)",
    )
    expression: EnumProperty(
        name="Expresion",
        items=EXPRESSION_PRESETS,
        default="NEUTRAL",
        description="Emocion que se expresa durante el pico de este intervalo",
    )
    expression_value: FloatProperty(
        name="Intensidad",
        default=1.0, min=0.0, max=1.0, precision=2,
        description="Fuerza maxima de la expresion en el frame pico (0=neutral, 1=maximo)",
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


class Chicken1EyeLibEntry(PropertyGroup):
    """Entrada de la lista de expresiones de la libreria de ojos"""
    name:     StringProperty(name="Nombre")
    filepath: StringProperty(name="Ruta JSON")


# =============================================================================
# SLOT DE CONFIGURACION DE OJOS  (espejo de Chicken1PoseSlotItem para poses)
# =============================================================================

class Chicken1EyeSlotItem(PropertyGroup):
    """
    Un estado/configuracion de ojos intermedio dentro de la secuencia.
    Equivalente a Chicken1PoseSlotItem pero para los parametros de las mallas de ojos.
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


class Chicken1PoseSlotItem(PropertyGroup):
    pose_name:  StringProperty(name="Pose")
    pose_label: StringProperty(name="Etiqueta", default="")
    json_file:  StringProperty(name="JSON")
    pose_index: IntProperty(name="Indice en JSON", default=0)
    duration:   IntProperty(name="Frames", default=20, min=1, soft_max=99999)
    # Frame absoluto donde empieza esta pose. Ver Chicken1SegmentPoseSlot.manual_start
    # para la explicacion completa -- este campo es el espejo de ese mismo
    # sistema en la copia de trabajo que usa ch1st.concatenate.
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
        description="Posicion X del root (alfred/Empty) en esta pose")
    pos_y: FloatProperty(name="Pos Y", default=0.0,
        description="Posicion Y del root (alfred/Empty) en esta pose")
    pos_z: FloatProperty(name="Pos Z", default=0.0,
        description="Posicion Z del root (alfred/Empty) en esta pose")
    # Tipo de interpolacion hacia esta pose de accion
    interp_type: EnumProperty(
        name="Interpolacion",
        description="Tipo de interpolacion profesional desde la pose anterior a esta",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )

class Chicken1OrganicFilters(PropertyGroup):
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

    # ── FILTRO 1: Noise de respiracion (pecho/torso del pollo) ──
    breathing_enabled: BoolProperty(name="Respiracion", default=True,
        description="Agrega un ciclo suave de respiracion al pecho/torso del pollo (Spine1/Chest)")
    breathing_amplitude: FloatProperty(name="Amplitud", default=0.012, min=0.001, max=0.15, precision=3,
        description="Magnitud maxima del movimiento de respiracion en radianes")
    breathing_speed: FloatProperty(name="Velocidad", default=0.08, min=0.01, max=1.0, precision=3,
        description="Ciclos de respiracion por frame (0.08 = ~18 resp/min a 24fps)")
    breathing_phase: FloatProperty(name="Fase", default=0.0, min=0.0, max=6.28, precision=2,
        description="Offset de fase inicial del ciclo de respiracion (radianes)")

    # ── FILTRO 2: Aleteo de alas (wing flap) — filtro estrella del pollo ──
    flap_enabled: BoolProperty(name="Aleteo de alas", default=True,
        description="Agrega un ciclo ritmico de aleteo a las alas del pollo (Scapula/Shoulder/Elbow L y R)")
    flap_amplitude: FloatProperty(name="Amplitud", default=0.455, min=0.01, max=1.5, precision=3,
        description="Apertura maxima del aleteo en radianes (recorrido arriba/abajo del ala)")
    flap_speed: FloatProperty(name="Velocidad", default=0.18, min=0.01, max=1.5, precision=3,
        description="Aleteos por frame (mayor = aleteo mas rapido)")
    flap_openness: FloatProperty(name="Apertura base", default=0.05, min=-0.5, max=0.8, precision=3,
        description="Levanta el punto medio del aleteo: alas mas abiertas/separadas del cuerpo (radianes)")
    flap_asymmetry: FloatProperty(name="Asimetria L/R", default=0.15, min=0.0, max=1.57, precision=3,
        description="Desfase de fase entre ala izquierda y derecha para un aleteo mas natural (radianes)")

    # ── FILTRO 3: Micro-movimiento de cabeza / cabeceo del pollo (head bob) ──
    head_sway_enabled: BoolProperty(name="Cabeceo / picoteo", default=True,
        description="Agrega el cabeceo y micro-movimientos tipicos del pollo (Neck/Head/Jaw)")
    head_sway_amplitude: FloatProperty(name="Amplitud", default=0.008, min=0.001, max=0.10, precision=3,
        description="Magnitud maxima del cabeceo del pollo en radianes")
    head_sway_speed: FloatProperty(name="Velocidad", default=0.05, min=0.005, max=0.5, precision=3,
        description="Velocidad de oscilacion de la cabeza por frame")
    head_sway_seed: IntProperty(name="Semilla", default=42, min=0, max=9999,
        description="Semilla aleatoria para variacion del patron de cabeza")

    # ── FILTRO 4: Balanceo de peso (patas del pollo) ──
    weight_shift_enabled: BoolProperty(name="Balanceo de peso", default=False,
        description="Simula el balanceo del peso de una pata a otra al pararse/caminar (Root/patas)")
    weight_shift_amplitude: FloatProperty(name="Amplitud", default=0.005, min=0.001, max=0.05, precision=3,
        description="Magnitud del balanceo lateral del cuerpo en unidades Blender")
    weight_shift_speed: FloatProperty(name="Velocidad", default=0.04, min=0.005, max=0.3, precision=3,
        description="Velocidad del ciclo de balanceo de peso")

    # ── FILTRO 5: Procedural noise sobre el ROOT (movimiento del cuerpo entero) ──
    root_noise_enabled: BoolProperty(name="Noise en ROOT", default=False,
        description="Agrega ruido procesal sobre la posicion del root del pollo (chicken_1/Empty)")
    root_noise_strength: FloatProperty(name="Intensidad", default=0.003, min=0.0001, max=0.05, precision=4,
        description="Intensidad maxima del ruido de posicion del root")
    root_noise_frequency: FloatProperty(name="Frecuencia", default=0.15, min=0.01, max=2.0, precision=3,
        description="Frecuencia del ruido (mayor = movimiento mas rapido)")
    root_noise_seed: IntProperty(name="Semilla", default=7, min=0, max=9999,
        description="Semilla para el ruido del root")

    # ── FILTRO 6: Secondary motion de las puntas de las alas (follow-through) ──
    secondary_motion_enabled: BoolProperty(name="Follow-through de alas", default=False,
        description="Agrega retardo y oscilacion a las puntas de las alas (Elbow L/R) tras el aleteo")
    secondary_motion_lag: FloatProperty(name="Retardo (frames)", default=3.0, min=0.5, max=15.0, precision=1,
        description="Frames de retardo con que la punta del ala sigue al movimiento principal")
    secondary_motion_damping: FloatProperty(name="Amortiguacion", default=0.7, min=0.1, max=0.99, precision=2,
        description="Factor de amortiguacion del movimiento secundario (0=sin amortiguar, 1=rigido)")

    # ── FILTRO 6: Smooth de fcurves (suavizado de curvas generadas) ──
    smooth_curves_enabled: BoolProperty(name="Suavizar fcurves", default=True,
        description="Aplica suavizado gaussiano a todas las fcurves del armature post-generacion")
    smooth_passes: IntProperty(name="Pasadas de suavizado", default=2, min=1, max=10,
        description="Numero de pasadas del suavizado gaussiano (mas = mas suave, mas fluido)")
    smooth_factor: FloatProperty(name="Factor suavizado", default=0.5, min=0.1, max=0.9, precision=2,
        description="Fuerza del suavizado en cada pasada (0.1=leve, 0.9=muy suave)")

    # ── FILTRO 7: Micro-escala (squash & stretch del pecho al respirar) ──
    micro_scale_enabled: BoolProperty(name="Micro-escala pecho", default=False,
        description="Agrega variacion minima de escala en el pecho del pollo (Chest) para simular la inflacion/desinflacion al respirar")
    micro_scale_amplitude: FloatProperty(name="Amplitud", default=0.005, min=0.001, max=0.03, precision=3,
        description="Variacion maxima de escala organica del pecho")

    # ── FILTRO 8: Noise rotacional en las alas (plumas/temblor de alas) ──
    shoulder_noise_enabled: BoolProperty(name="Noise de alas", default=False,
        description="Agrega micro-rotaciones procesuales a la base de las alas (Scapula L/R) para simular el temblor de las plumas")
    shoulder_noise_amplitude: FloatProperty(name="Amplitud", default=0.006, min=0.001, max=0.08, precision=3,
        description="Magnitud del noise de alas en radianes")
    shoulder_noise_speed: FloatProperty(name="Velocidad", default=0.07, min=0.01, max=0.5, precision=3,
        description="Velocidad del noise de alas")
    shoulder_noise_seed: IntProperty(name="Semilla", default=123, min=0, max=9999,
        description="Semilla aleatoria para noise de alas")


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
    a la lista (Chicken1ObjectImportItem). Si el objeto ya fue importado
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
    (Chicken1ObjectImportsSettings.edit_*). Si hay un objeto importado en
    preview (edit_imported_object_name), se actualiza su transform en vivo
    para ver el resultado mientras se ajustan los valores.
    """
    obj = bpy.data.objects.get(self.edit_imported_object_name)
    if obj is not None:
        _oi_apply_transform_to_object(
            obj, self.edit_loc_x, self.edit_loc_y, self.edit_loc_z,
            self.edit_rot_x, self.edit_rot_y, self.edit_rot_z, self.edit_scale_uniform,
        )


class Chicken1ObjectImportItem(PropertyGroup):
    """
    Un intervalo de importacion de objeto para Alfred.
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
    parent_armature: StringProperty(name="Armature", default="Armature",
        description="Nombre del armature al que parentear el objeto. "
                     "Alfred tiene un unico armature en la escena llamado 'Armature'.")
    parent_bone: StringProperty(name="Bone de parenteo", default="Elbow_L_chicken_1",
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
        description="Indice del segmento (ch1_segs.segments) al que pertenece este objeto. "
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


class Chicken1ThrowWaypoint(PropertyGroup):
    """Punto intermedio en la trayectoria. Coordenadas GLOBALES."""
    label:   StringProperty(name="Etiqueta", default="Punto")
    x:       FloatProperty(name="X", default=0.0, precision=4)
    y:       FloatProperty(name="Y", default=0.0, precision=4)
    z:       FloatProperty(name="Z", default=2.0, precision=4)
    easing:  EnumProperty(name="Easing", items=THROW_EASING_ITEMS, default='SMOOTH')
    enabled: BoolProperty(name="Activo", default=True)


class Chicken1ThrowItem(PropertyGroup):
    """
    Un lanzamiento/recogida de objeto. Un segmento puede tener varios.
    Equivalente a Chicken1ObjectImportItem para el sistema de lanzar/recoger.
    """
    label:   StringProperty(name="Etiqueta", default="Lanzamiento")
    enabled: BoolProperty(name="Activo", default=True)

    mode: EnumProperty(
        name="Modo",
        items=[
            ('THROW', 'Lanzar',  'El objeto sale del bone hacia la coordenada destino'),
            ('CATCH', 'Recoger', 'El objeto va desde la coordenada origen hacia el bone'),
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
    parent_armature: StringProperty(name="Armature", default="Armature")
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

    # Trayectoria
    target_object:   StringProperty(name="Objeto activo", default="")
    target_armature: StringProperty(name="Armature (traj.)", default="Armature")
    target_bone:     StringProperty(name="Bone origen (traj.)", default="")
    dest_x: FloatProperty(name="X", default=0.0, precision=4)
    dest_y: FloatProperty(name="Y", default=3.0, precision=4)
    dest_z: FloatProperty(name="Z", default=0.0, precision=4)
    easing_global: EnumProperty(name="Easing", items=THROW_EASING_ITEMS, default='SMOOTH')

    # Avanzado
    spin_during_flight: BoolProperty(name="Rotacion en vuelo", default=False)
    spin_turns: FloatProperty(name="Vueltas", default=1.0, min=0.0, max=20.0, precision=1)

    # Waypoints
    waypoints:     CollectionProperty(type=Chicken1ThrowWaypoint)
    waypoints_idx: IntProperty(default=0)

    # UI state
    show_waypoints: BoolProperty(name="Mostrar waypoints", default=True)
    show_advanced:  BoolProperty(name="Mostrar avanzado",  default=False)


class Chicken1ThrowsSettings(PropertyGroup):
    """
    Coleccion de Chicken1ThrowItem para un segmento.
    Equivalente a Chicken1ObjectImportsSettings.
    Se almacena en Chicken1AnimSegment.throws.
    """
    enabled: BoolProperty(name="Activar Lanzar/Recoger", default=False)
    items:   CollectionProperty(type=Chicken1ThrowItem)
    active_idx: IntProperty(default=0)

    # ── Campos edit_* para el editor de nuevo item ────────────────────────
    edit_label:          StringProperty(name="Etiqueta", default="Lanzamiento")
    edit_mode: EnumProperty(
        name="Modo",
        items=[
            ('THROW', 'Lanzar',  'El objeto sale del bone hacia el destino'),
            ('CATCH', 'Recoger', 'El objeto va desde el origen hacia el bone'),
        ],
        default='THROW',
    )
    edit_blend_path:      StringProperty(name="Ruta .blend", default="", subtype="FILE_PATH")
    edit_object_folder:   StringProperty(name="Carpeta", default="")
    edit_blend_filename:  StringProperty(name="Archivo .blend", default="")
    edit_object_name:     StringProperty(name="Nombre objeto", default="")
    edit_levels_up:       IntProperty(name="Niveles arriba", default=4, min=1, max=10)
    edit_imported_object_name: StringProperty(default="")
    edit_parent_armature: StringProperty(name="Armature", default="Armature")
    edit_parent_bone:     StringProperty(name="Bone", default="")
    edit_loc_x: FloatProperty(name="X", default=0.0, precision=4)
    edit_loc_y: FloatProperty(name="Y", default=0.0, precision=4)
    edit_loc_z: FloatProperty(name="Z", default=0.0, precision=4)
    edit_rot_x: FloatProperty(name="Rot X", default=0.0, precision=2,
                    subtype='ANGLE', unit='ROTATION')
    edit_rot_y: FloatProperty(name="Rot Y", default=0.0, precision=2,
                    subtype='ANGLE', unit='ROTATION')
    edit_rot_z: FloatProperty(name="Rot Z", default=0.0, precision=2,
                    subtype='ANGLE', unit='ROTATION')
    edit_scale_uniform:   FloatProperty(name="Escala", default=1.0, min=0.001, max=100.0, precision=3)
    edit_frame_start:     IntProperty(name="Frame inicio", default=1, min=0, soft_max=99999)
    edit_frame_end:       IntProperty(name="Frame fin", default=30, min=1, soft_max=99999)
    edit_target_armature: StringProperty(name="Armature (traj.)", default="Armature")
    edit_target_bone:     StringProperty(name="Bone origen (traj.)", default="")
    edit_dest_x: FloatProperty(name="X", default=0.0, precision=4)
    edit_dest_y: FloatProperty(name="Y", default=3.0, precision=4)
    edit_dest_z: FloatProperty(name="Z", default=0.0, precision=4)
    edit_easing_global: EnumProperty(name="Easing", items=THROW_EASING_ITEMS, default='SMOOTH')
    edit_spin_during_flight: BoolProperty(name="Rotacion en vuelo", default=False)
    edit_spin_turns: FloatProperty(name="Vueltas", default=1.0, min=0.0, max=20.0, precision=1)


class Chicken1ObjectImportsSettings(PropertyGroup):
    """Configuracion global del sistema de importacion de objetos de Alfred."""
    enabled: BoolProperty(
        name="Activar importacion de objetos",
        description=(
            "Habilita el sistema de importacion de objetos. "
            "Se generan al presionar EXPORTAR (incluidos en el .py exportado)."
        ),
        default=False,
    )
    items: CollectionProperty(type=Chicken1ObjectImportItem)
    active_idx: IntProperty(default=0)

    # ── Editor de nuevo objeto ──────────────────────────────────────────────
    edit_label:          StringProperty(name="Etiqueta", default="Mi objeto")
    edit_object_folder:  StringProperty(name="Carpeta", default="vanilla/shield")
    edit_blend_filename: StringProperty(name="Archivo .blend", default="shield.blend")
    edit_object_name:    StringProperty(name="Nombre objeto", default="shield")
    edit_frame_start:    IntProperty(name="Frame inicio", default=1, min=0, soft_max=99999)
    edit_frame_end:      IntProperty(name="Frame fin",   default=60, min=1, soft_max=99999)
    edit_parent_armature: StringProperty(name="Armature", default="Armature",
        description="Nombre del armature al que parentear el objeto. "
                     "Alfred tiene un unico armature en la escena llamado 'Armature'.")
    edit_parent_bone:    StringProperty(name="Bone de parenteo", default="Elbow_L_chicken_1")
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
        items=Chicken1ObjectImportItem.TRANSITION_IN_ITEMS,
        default='NONE',
    )
    edit_transition_in_duration: IntProperty(
        name="Duración entrada (frames)",
        default=8, min=1, max=60,
    )
    edit_transition_out: bpy.props.EnumProperty(
        name="Transición desaparición",
        description="Efecto de salida del objeto al frame fin",
        items=Chicken1ObjectImportItem.TRANSITION_OUT_ITEMS,
        default='NONE',
    )
    edit_transition_out_duration: IntProperty(
        name="Duración salida (frames)",
        default=8, min=1, max=60,
    )


class Chicken1BoneOscillationItem(PropertyGroup):
    """
    Un item de oscilacion sinusoidal para un bone especifico del armature de Alfred.
    Permite animar cabeceos, balanceos de brazos, rodillas, etc.
    """
    label: StringProperty(name="Etiqueta", default="Oscilacion",
        description="Nombre descriptivo de esta oscilacion")
    bone_name: EnumProperty(
        name="Bone",
        description="Bone del armature de Alfred a oscilar",
        items=[
            ("Root_M_chicken_1",       "Root_M_chicken_1 (Caderas)",        ""),
            ("Spine1_M_chicken_1",      "Spine1_M_chicken_1 (Columna)",       ""),
            ("Chest_M_chicken_1",     "Chest_M_chicken_1 (Columna 1)",    ""),
            ("Neck_M_chicken_1",     "Neck_M_chicken_1 (Columna 2)",    ""),
            ("Head_M_chicken_1",       "Head_M_chicken_1 (Cuello)",         ""),
            ("Jaw_M_chicken_1",       "Jaw_M_chicken_1 (Cara)",           ""),
            ("Scapula_R_chicken_1", "Scapula_R_chicken_1 (Brazo D)",  ""),
            ("Elbow_R_chicken_1", "Elbow_R_chicken_1 (Codo D)",   ""),
            ("Scapula_L_chicken_1",  "Scapula_L_chicken_1 (Brazo I)",   ""),
            ("Elbow_L_chicken_1",  "Elbow_L_chicken_1 (Codo I)",    ""),
            ("Hip_R_chicken_1", "Hip_R_chicken_1 (Pierna D)", ""),
            ("Knee_R_chicken_1",  "Knee_R_chicken_1 (Rodilla D)", ""),
            ("Hip_L_chicken_1",  "Hip_L_chicken_1 (Pierna I)",  ""),
            ("Knee_L_chicken_1",   "Knee_L_chicken_1 (Rodilla I)",  ""),
        ],
        default="Root_M_chicken_1",
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


class Chicken1BoneOscillationsSettings(PropertyGroup):
    """Configuracion global del sistema de oscilaciones de bones de Alfred."""
    enabled: BoolProperty(
        name="Activar oscilaciones de bones",
        description=(
            "Habilita el sistema de oscilaciones personalizadas. "
            "Se aplican como post-proceso al presionar CONCATENAR."
        ),
        default=False,
    )
    items:      CollectionProperty(type=Chicken1BoneOscillationItem)
    active_idx: IntProperty(default=0)

    # ── Editor de nueva oscilacion ─────────────────────────────────────────
    edit_label:       StringProperty(name="Etiqueta", default="Mi oscilacion")
    edit_bone_name: EnumProperty(
        name="Bone",
        description="Bone del armature de Alfred a oscilar",
        items=[
            ("Root_M_chicken_1",       "Root_M_chicken_1 (Caderas)",        ""),
            ("Spine1_M_chicken_1",      "Spine1_M_chicken_1 (Columna)",       ""),
            ("Chest_M_chicken_1",     "Chest_M_chicken_1 (Columna 1)",    ""),
            ("Neck_M_chicken_1",     "Neck_M_chicken_1 (Columna 2)",    ""),
            ("Head_M_chicken_1",       "Head_M_chicken_1 (Cuello)",         ""),
            ("Jaw_M_chicken_1",       "Jaw_M_chicken_1 (Cara)",           ""),
            ("Scapula_R_chicken_1", "Scapula_R_chicken_1 (Brazo D)",  ""),
            ("Elbow_R_chicken_1", "Elbow_R_chicken_1 (Codo D)",   ""),
            ("Scapula_L_chicken_1",  "Scapula_L_chicken_1 (Brazo I)",   ""),
            ("Elbow_L_chicken_1",  "Elbow_L_chicken_1 (Codo I)",    ""),
            ("Hip_R_chicken_1", "Hip_R_chicken_1 (Pierna D)", ""),
            ("Knee_R_chicken_1",  "Knee_R_chicken_1 (Rodilla D)", ""),
            ("Hip_L_chicken_1",  "Hip_L_chicken_1 (Pierna I)",  ""),
            ("Knee_L_chicken_1",   "Knee_L_chicken_1 (Rodilla I)",  ""),
        ],
        default="Root_M_chicken_1",
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


class Chicken1StudioSettings(PropertyGroup):

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
    # ── Ruta al JSON de historia (key_points + orientacion) ──
    historia_json: StringProperty(
        name="historia_chicken_1.json",
        default=DEFAULT_HISTORIA_JSON,
        subtype="FILE_PATH",
        description="Ruta al archivo historia_chicken_1.json con key_points y orientacion_inicial",
    )

    armature_name: StringProperty(name="Armature", default="")



    action_poses:    CollectionProperty(type=Chicken1PoseSlotItem)
    action_pose_idx: IntProperty(default=0)

    # Filtros de movimiento organico (post-proceso)
    organic: PointerProperty(type=Chicken1OrganicFilters)

    # Importacion de objetos (armas, escudos, props)
    object_imports: PointerProperty(type=Chicken1ObjectImportsSettings)

    # Sistema de expresiones de mallas de ojos (configuracion global / preview)
    eye_expr: PointerProperty(type=Chicken1EyeExpressionSettings)

    # ═══════════════════════════════════════════════════════════════════════
    # SISTEMA DE SECUENCIA DE OJOS  (espejo del sistema de poses)
    # ═════════════════════════════════════════════════════�����═════════════════

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
        default="BLINK",
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
    eye_slots:     CollectionProperty(type=Chicken1EyeSlotItem)
    eye_slot_idx:  IntProperty(default=0)

    # ── Intervalos de parpadeo automatico (multi-intervalo) ───────────────────
    blink_intervals:     CollectionProperty(type=Chicken1BlinkInterval)
    blink_interval_idx:  IntProperty(default=0)

    # ── Intervalos de expresiones de ojos (multi-intervalo) ───────────────────
    expr_intervals:     CollectionProperty(type=Chicken1EyeExprInterval)
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
        default="BLINK",
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
    export_name: StringProperty(name="Nombre", default="alfred_nueva_animacion")
    export_type: StringProperty(name="Tipo",   default="custom")
    export_desc: StringProperty(name="Desc",   default="Animacion generada con Chicken1 Studio")

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
        description="Index del punto clave del recorrido donde se realiza la accion (de historia_chicken_1.json)",
        default=1, min=1,
    )
    # Informacion visual del key_point elegido (solo lectura, actualizado al cargar)
    key_point_info: StringProperty(default="-- carga el JSON primero --")

    # ── NUEVO: key_point para posicion inicial del ROOT ──
    root_pos_key_point: EnumProperty(
        name="KeyPoint para Root",
        description="Coordenada del recorrido para la posicion inicial del ROOT (Root_M_chicken_1)",
        items=_enum_key_points,
    )

    extract_label:       StringProperty(name="Nombre nueva pose", default="")
    extract_frame:       IntProperty(name="Frame", default=1, min=0, max=99999)
    extract_use_current: BoolProperty(name="Frame actual", default=True)

    # ── Extraer pose rapida (Paso 3, dentro de cada segmento) ─────────────
    # Version simplificada de "Extraer Nueva Pose" (extract_label/_frame/
    # _use_current arriba): detecta el armature de chicken_1 automaticamente
    # (sin selector), nombra la pose sola segun que huesos se movieron, y
    # guarda el .json con un solo click. El archivo/indice/etiqueta que
    # acaba de generar "Guardar" quedan aca en espera de que el usuario
    # presione "Importar" (que los agrega a seg.action_poses del segmento
    # correspondiente) y luego se limpian para el siguiente ciclo.
    quickpose_pending_file:  StringProperty(default="")
    quickpose_pending_index: IntProperty(default=0)
    quickpose_pending_label: StringProperty(default="")

    # ── Sistema de oscilaciones de bones personalizadas ──────────────────────
    bone_oscillations: PointerProperty(type=Chicken1BoneOscillationsSettings)

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
    eye_lib_entries:  CollectionProperty(type=Chicken1EyeLibEntry)
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

class Chicken1SegmentPoseSlot(PropertyGroup):
    """Un slot de pose dentro de un Chicken1AnimSegment."""
    json_file:   StringProperty(default="", description="Archivo .json de la pose")
    pose_label:  StringProperty(default="")
    pose_name:   StringProperty(default="", description="Nombre descriptivo de la pose")
    # Indice de esta pose DENTRO del archivo json_file (una biblioteca puede
    # contener varias poses). Sin este campo, CH1SEG_OT_AddActionPoseSeg no
    # puede guardar cual pose eligio el usuario en el dropdown "Paso 2 --
    # Elige la pose de accion", y la reproduccion cae siempre en la pose [0]
    # del archivo (bug: "las poses no se reproducen").
    pose_index:  IntProperty(name="Indice en JSON", default=0)
    duration:    IntProperty(name="Frames", default=24, min=1, max=9999)
    entry_ratio: FloatProperty(name="Entrada %", default=0.3, min=0.0, max=1.0, precision=2)
    exit_ratio:  FloatProperty(name="Salida %",  default=0.3, min=0.0, max=1.0, precision=2)
    interp_type: EnumProperty(name="Interpolacion", items=INTERP_TYPE_ITEMS, default="SMOOTH")
    rot_x: FloatProperty(name="Rot X", default=0.0)
    rot_y: FloatProperty(name="Rot Y", default=0.0)
    rot_z: FloatProperty(name="Rot Z", default=0.0)
    pos_x: FloatProperty(name="Pos X", default=0.0)
    pos_y: FloatProperty(name="Pos Y", default=0.0)
    pos_z: FloatProperty(name="Pos Z", default=0.0)
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


# =============================================================================
# PASO 3: SEGMENTO DE ANIMACION
# =============================================================================

class Chicken1AnimSegment(PropertyGroup):
    """
    Un segmento dentro de la animacion generada por Pasos 1+2.
    Contiene su propio intervalo de frames y configuracion completa de poses.
    """
    label: StringProperty(name="Etiqueta", default="Segmento")

    frame_start: IntProperty(name="Frame inicio", default=1, min=1, soft_max=99999)
    frame_end:   IntProperty(name="Frame fin",    default=48, min=2, soft_max=99999)



    # Slots de accion intermedios
    action_poses:     CollectionProperty(type=Chicken1SegmentPoseSlot)
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

    # ── Filtros de bones (Paso 3) ─────────────────────────────────────────────
    # Los bones marcados NO reciben keyframes de configuracion en CONCATENAR.
    # Por defecto las piernas estan filtradas (el recorrido base las controla).
    filter_show:     BoolProperty(name="Filtrar bones", default=False, description="Activar para excluir bones especificos de las poses del segmento")

    # Root / caderas
    filter_main_bone: BoolProperty(
        name="chicken_1 (Root)",
        default=False,
        description=(
            "Excluye el Empty raiz 'chicken_1' (posicion y rotacion global del "
            "personaje). NO es el objeto Armature_chicken_1 ni ninguno de sus "
            "bones -- esos se filtran individualmente mas abajo (Root_M_chicken_1, "
            "Spine1_M_chicken_1, etc.)."
        ),
    )
    filter_hips:      BoolProperty(name="Root_M_chicken_1",   default=False)

    # Columna
    filter_body:      BoolProperty(name="Spine1_M_chicken_1",  default=False)
    filter_spine:     BoolProperty(name="Spine1_M_chicken_1",  default=False)
    filter_spine1:    BoolProperty(name="Chest_M_chicken_1", default=False)
    filter_spine2:    BoolProperty(name="Neck_M_chicken_1", default=False)

    # Cabeza / cuello
    filter_neck:      BoolProperty(name="Head_M_chicken_1",   default=False)
    filter_face:      BoolProperty(name="Jaw_M_chicken_1",   default=False)
    filter_jaw_top:   BoolProperty(name="Jaw_top_chicken_1", default=False)
    filter_jaw_bot:   BoolProperty(name="Jaw_bot_chicken_1", default=False)

    # Brazos
    filter_right_arm:      BoolProperty(name="Scapula_R_chicken_1",  default=False)
    filter_right_shoulder: BoolProperty(name="Shoulder_R_chicken_1", default=False)
    filter_right_elbow:    BoolProperty(name="Elbow_R_chicken_1",  default=False)
    filter_left_arm:       BoolProperty(name="Scapula_L_chicken_1",   default=False)
    filter_left_shoulder:  BoolProperty(name="Shoulder_L_chicken_1",  default=False)
    filter_left_elbow:     BoolProperty(name="Elbow_L_chicken_1",   default=False)

    # Piernas (filtradas por defecto — el recorrido base las controla)
    filter_right_leg:   BoolProperty(name="Hip_R_chicken_1", default=True)
    filter_right_knee:  BoolProperty(name="Knee_R_chicken_1",  default=True)
    filter_right_ankle: BoolProperty(name="Ankle_R_chicken_1", default=True)
    filter_left_leg:    BoolProperty(name="Hip_L_chicken_1",  default=True)
    filter_left_knee:   BoolProperty(name="Knee_L_chicken_1",   default=True)
    filter_left_ankle:  BoolProperty(name="Ankle_L_chicken_1",  default=True)

    # Poles de rodilla (bones sueltos level 0, no jerarquia del brazo/pierna)
    filter_knee_pole_r: BoolProperty(name="Knee.Right_chicken_1", default=False)
    filter_knee_pole_l: BoolProperty(name="Knee.Left_chicken_1",  default=False)

    # Accesorios / no_bone
    filter_no_bone_01: BoolProperty(name="no_bone_01_chicken_1", default=False)
    filter_no_bone_02: BoolProperty(name="no_bone_02_chicken_1", default=False)
    filter_no_bone_03: BoolProperty(name="no_bone_03_chicken_1", default=False)
    filter_no_bone_04: BoolProperty(name="no_bone_04_chicken_1", default=False)
    filter_no_bone_05: BoolProperty(name="no_bone_05_chicken_1", default=False)
    filter_no_bone_06: BoolProperty(name="no_bone_06_chicken_1", default=False)
    filter_no_bone_07: BoolProperty(name="no_bone_07", default=False)
    filter_no_bone_08: BoolProperty(name="no_bone_08", default=False)

    enabled: BoolProperty(name="Activo", default=True)
    show_config: BoolProperty(name="Mostrar configuracion", default=True)
    single_coord_mode: BoolProperty(name="Modo 1 coordenada", default=False)
    frame_end_auto: IntProperty(name="Frame fin (calculado)", default=0, min=0, soft_max=99999)

    # ── Filtro: Lanzar / Recoger Objetos ─────────────────────────────────
    throws: PointerProperty(type=Chicken1ThrowsSettings)


# =============================================================================
# PASO 3: CONFIGURACION GLOBAL DE SEGMENTOS
# =============================================================================

class Chicken1AnimSegmentsSettings(PropertyGroup):
    """
    Coleccion de Chicken1AnimSegment y estado global del sistema de refinado (Paso 3).
    Se almacena en bpy.types.Scene.ch1_segs.
    """
    segments:      CollectionProperty(type=Chicken1AnimSegment)
    active_index:  IntProperty(default=0)
    armature_name: StringProperty(name="Armature", default="Armature_chicken_1")
    poses_dir:     StringProperty(
        # FIX: quedaba apuntando a la carpeta de "alfred" (resto de la
        # plantilla) en vez de "chicken_1". No se usa como fuente principal
        # (CH1SEG_OT_Apply resuelve la carpeta real desde ch1st.poses_dir,
        # la unica editable en el panel "Carpetas"): este default solo
        # queda como fallback de compatibilidad con .blend antiguos.
        name="Carpeta de poses",
        default=DEFAULT_POSES_DIR,
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
