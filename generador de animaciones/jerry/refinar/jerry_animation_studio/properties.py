# -*- coding: utf-8 -*-
"""
properties.py — Jerry Animation Studio v2.0
PropertyGroups: JerryOrganicFilters, JerryPoseSlotItem, JerryStudioSettings,
                JerryAnimSegment, JerryAnimSegmentsSettings.

NUEVO EN v2.0:
  JerryAnimSegment        — un segmento de refinado: intervalo de frames dentro
                           de la animacion generada por Pasos 1+2, con pose
                           inicio / intermedio / final propias.
  JerryAnimSegmentsSettings — coleccion de segmentos + estado global del Paso 3.

El Paso 3 opera SOBRE la animacion ya existente en la timeline (generada por
path_recorder). Cada segmento define un rango [frame_start, frame_end] y
tres poses opcionales (.json) que se interpolan dentro de ese rango,
sobreescribiendo / modulando los fcurves de los bones seleccionados.
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
    DEFAULT_POSE_CHANGES_DIR, DEFAULT_REGLAS_DIR,
    EXPRESSION_PRESETS, INTERP_TYPE_ITEMS,
)

# Ruta por defecto de la libreria de ojos
_DEFAULT_EYE_LIB_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\Informacion_Animacion\jerry\ojos"
)

# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def load_historia_json(filepath):
    path = bpy.path.abspath(filepath)
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[JRRSTStudio] No se pudo leer historia JSON: {e}")
        return {}

def get_key_points(historia_data):
    return historia_data.get("recorrido", {}).get("key_points", [])

def _enum_key_points(self, context):
    st = context.scene.jerryst
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
# FILTROS ORGANICOS
# =============================================================================

class JerryEyeExpressionSettings(PropertyGroup):
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

    # ── Selector de sistema activo ───────────────────────────────────────────
    # NOTA (Kebyn + Claude, 2026-08-24): SISTEMA_2 (parpadeo cortina
    # sincronizado) y AMBOS fueron eliminados de la UI y del enum -- ya existe
    # un sistema de parpadeo propio POR SEGMENTO ("Parpadeo automatico (por
    # segmento)", ver seg.eye_blink_intervals en JerryAnimSegment) que cubre
    # ese mismo caso de uso de forma mas flexible. Se deja el enum con un solo
    # valor (en vez de convertir a BoolProperty) para no romper el resto del
    # codigo, que sigue leyendo `active_eye_system` en varios operadores.
    active_eye_system: EnumProperty(
        name="Sistema activo",
        description="Secuencia Inicio / N Cambios / Fin  (CONCATENAR_2)",
        items=[
            ("SISTEMA_1", "Sistema 1 — Secuencia",  "Secuencia Inicio / N Cambios / Fin  (CONCATENAR_2)",          "NLA",              0),
        ],
        default="SISTEMA_1",
    )

    # ── Compatibilidad: propiedades derivadas del selector ───────────────────
    # El resto del codigo (operadores, panel) puede seguir leyendo estos bool.
    # Se calculan como propiedades de solo lectura basadas en active_eye_system.
    # NOTA: en Blender los PropertyGroup no permiten @property de Python puro,
    # por lo que los operadores leen active_eye_system directamente.
    eye_seq_enabled: BoolProperty(
        name="Sistema 1 activo",
        default=True,
        description="(Interno) Activa el sistema Inicio / N Cambios / Fin — controlado por el selector de sistema",
    )
    blink_only_enabled: BoolProperty(
        name="Sistema 2 activo",
        default=False,
        description="(Interno) Activa el parpadeo sincronizado — controlado por el selector de sistema",
    )

    # Parpadeo integrado (sistema cortina)
    blink_enabled: BoolProperty(
        name="Parpadeos automaticos", default=False,
        description="Inserta parpadeos de efecto cortina independientemente de la secuencia de expresiones",
    )
    blink_count: IntProperty(
        name="Numero de parpadeos", default=2, min=1, max=20,
        description="Cuantos parpadeos se distribuyen a lo largo del rango de frames",
    )
    blink_duration: IntProperty(
        name="Frames por parpadeo", default=9, min=5, max=30,
        description="Frames que dura un ciclo de parpadeo completo (cierre + apertura)",
    )
    blink_frame_start: IntProperty(
        name="Frame inicio parpadeo", default=1, min=0,
        description="Frame a partir del cual se insertan los parpadeos",
    )
    blink_frame_end: IntProperty(
        name="Frame fin parpadeo", default=60, min=1,
        description="Frame hasta el cual se distribuyen los parpadeos",
    )

    # ── Pupilas — posicion base y desplazamiento de mirada ──
    pupil_enabled: BoolProperty(
        name="Pupilas activas", default=True,
        description="Activa el desplazamiento de las pupilas dentro de la esclerotica",
    )

    # Posicion base pupila izquierda (pupila_izquierda_jerry)
    pupil_L_base_x: FloatProperty(name="Base X izq", default=0.093955,  precision=6)
    pupil_L_base_y: FloatProperty(name="Base Y izq", default=0.703723,  precision=6)
    pupil_L_base_z: FloatProperty(name="Base Z izq", default=0.687998,  precision=6)
    pupil_L_base_rot_z: FloatProperty(name="Rot Z izq", default=3.141593, subtype="ANGLE", precision=6,
        description="Rotacion Z base pupila izquierda (pi rad = 180 grados)")

    # Posicion base pupila derecha (pupila_derecha_jerry)
    pupil_R_base_x: FloatProperty(name="Base X der", default=-0.093451, precision=6)
    pupil_R_base_y: FloatProperty(name="Base Y der", default=0.703504,  precision=6)
    pupil_R_base_z: FloatProperty(name="Base Z der", default=0.688877,  precision=6)
    pupil_R_base_rot_z: FloatProperty(name="Rot Z der", default=0.0,    subtype="ANGLE", precision=6,
        description="Rotacion Z base pupila derecha (0 rad = 0 grados)")

    # Offsets de mirada (desplazamiento sobre la base)
    pupil_L_offset_x: FloatProperty(
        name="Offset X izq", default=0.0, min=-0.025, max=0.025, precision=4,
        description="Desplazamiento horizontal pupila izquierda (limite ±0.025 m)",
    )
    pupil_L_offset_z: FloatProperty(
        name="Offset Z izq", default=0.0, min=-0.025, max=0.025, precision=4,
        description="Desplazamiento vertical pupila izquierda (limite ±0.025 m)",
    )
    pupil_R_offset_x: FloatProperty(
        name="Offset X der", default=0.0, min=-0.025, max=0.025, precision=4,
        description="Desplazamiento horizontal pupila derecha (limite ±0.025 m)",
    )
    pupil_R_offset_z: FloatProperty(
        name="Offset Z der", default=0.0, min=-0.025, max=0.025, precision=4,
        description="Desplazamiento vertical pupila derecha (limite ±0.025 m)",
    )
    # Mirada conjunta
    pupil_link: BoolProperty(
        name="Mirada enlazada", default=True,
        description="Mueve ambas pupilas al mismo tiempo con los mismos offsets",
    )

    # ── LIBRERIA: propiedades de timeline por expresion ──────────────────────
    lib_frame_start: IntProperty(
        name="Frame inicio", default=1, min=0,
        description="Frame de la timeline donde empieza esta expresion de ojos",
    )
    lib_duration: IntProperty(
        name="Duracion (frames)", default=20, min=1, max=500,
        description="Cuantos frames dura esta expresion de ojos",
    )
    lib_interp_type: EnumProperty(
        name="Transicion",
        description="Tipo de interpolacion al entrar a esta expresion",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )

    # ── TRANSFORMS EDITABLES de las mallas de ojos ───────────────────────────
    # Coordenadas base = posicion correcta de los ojos en el rostro de Jerry.
    # Cualquier cambio en el panel es un DELTA relativo a estas posiciones.
    # ojo_derecho_jerry  base: (0.094537,  -0.712021, 1.70043)
    # ojo_izquierdo_jerry base: ( -0.093451, -0.710586, 1.70082)

    # Ojo izquierdo
    eye_L_loc_x: FloatProperty(name="Loc X",   default=-0.105732, precision=4, description="Posicion X ojo izquierdo (base: -0.105732)")
    eye_L_loc_y: FloatProperty(name="Loc Y",   default=0.705210,  precision=4, description="Posicion Y ojo izquierdo (base: 0.705210)")
    eye_L_loc_z: FloatProperty(name="Loc Z",   default=0.699791,  precision=4, description="Posicion Z ojo izquierdo (base: 0.699791)")
    eye_L_rot_x: FloatProperty(name="Rot X",   default=0.0,       subtype="ANGLE", description="Rotacion X ojo izquierdo (base: 0 grados)")
    eye_L_rot_y: FloatProperty(name="Rot Y",   default=-1.570796, subtype="ANGLE", description="Rotacion Y ojo izquierdo (base: -90 grados)")
    eye_L_rot_z: FloatProperty(name="Rot Z",   default=-1.570796, subtype="ANGLE", description="Rotacion Z ojo izquierdo (base: -90 grados)")
    eye_L_sca_x: FloatProperty(name="Sca X",   default=1.0,      min=0.001, max=10.0, precision=3, description="Escala X ojo izquierdo")
    eye_L_sca_y: FloatProperty(name="Sca Y",   default=1.0,      min=0.001, max=10.0, precision=3, description="Escala Y ojo izquierdo")
    eye_L_sca_z: FloatProperty(name="Sca Z",   default=1.0,      min=0.001, max=10.0, precision=3, description="Escala Z ojo izquierdo")

    # Ojo derecho
    eye_R_loc_x: FloatProperty(name="Loc X",   default=0.105796,   precision=4, description="Posicion X ojo derecho (base: 0.105796)")
    eye_R_loc_y: FloatProperty(name="Loc Y",   default=0.704775,   precision=4, description="Posicion Y ojo derecho (base: 0.704775)")
    eye_R_loc_z: FloatProperty(name="Loc Z",   default=0.700123,   precision=4, description="Posicion Z ojo derecho (base: 0.700123)")
    eye_R_rot_x: FloatProperty(name="Rot X",   default=0.0,       subtype="ANGLE", description="Rotacion X ojo derecho (base: 0 grados)")
    eye_R_rot_y: FloatProperty(name="Rot Y",   default=-1.570796, subtype="ANGLE", description="Rotacion Y ojo derecho (base: -90 grados)")
    eye_R_rot_z: FloatProperty(name="Rot Z",   default=-1.570796, subtype="ANGLE", description="Rotacion Z ojo derecho (base: -90 grados)")
    eye_R_sca_x: FloatProperty(name="Sca X",   default=1.0,      min=0.001, max=10.0, precision=3, description="Escala X ojo derecho")
    eye_R_sca_y: FloatProperty(name="Sca Y",   default=1.0,      min=0.001, max=10.0, precision=3, description="Escala Y ojo derecho")
    eye_R_sca_z: FloatProperty(name="Sca Z",   default=1.0,      min=0.001, max=10.0, precision=3, description="Escala Z ojo derecho")

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




class JerryEyeLibEntry(PropertyGroup):
    """Entrada de la lista de expresiones de la libreria de ojos"""
    name:     StringProperty(name="Nombre")
    filepath: StringProperty(name="Ruta JSON")


# NOTA (Kebyn, 2026-08-27): JerryEyeSlotItem ("estado de ojos" intermedio
# de la Secuencia de Ojos por-segmento) eliminado por no usarse -- ver
# panels.py / operators_base.py para el resto del sistema retirado.




class JerryPoseSlotItem(PropertyGroup):
    pose_name:  StringProperty(name="Pose")
    json_file:  StringProperty(name="JSON")
    pose_index: IntProperty(name="Indice en JSON", default=0)
    duration:   IntProperty(name="Frames", default=20, min=1, soft_max=300)
    # Orientacion individual del Dog_001_rig para esta pose (grados)
    rot_x: FloatProperty(name="Rot X", default=0.0, subtype="ANGLE",
        description="Rotacion X del Dog_001_rig (root/Empty) en esta pose (grados)")
    rot_y: FloatProperty(name="Rot Y", default=0.0, subtype="ANGLE",
        description="Rotacion Y del Dog_001_rig (root/Empty) en esta pose (grados)")
    rot_z: FloatProperty(name="Rot Z", default=0.0, subtype="ANGLE",
        description="Rotacion Z del Dog_001_rig (root/Empty) en esta pose (grados)")
    # Posicion XYZ del root/Empty para esta pose
    pos_x: FloatProperty(name="Pos X", default=0.0,
        description="Posicion X del root (jerry/Empty) en esta pose")
    pos_y: FloatProperty(name="Pos Y", default=0.0,
        description="Posicion Y del root (jerry/Empty) en esta pose")
    pos_z: FloatProperty(name="Pos Z", default=0.0,
        description="Posicion Z del root (jerry/Empty) en esta pose")
    # Tipo de interpolacion hacia esta pose de accion
    interp_type: EnumProperty(
        name="Interpolacion",
        description="Tipo de interpolacion profesional desde la pose anterior a esta",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )


# =============================================================================
# INTERVALOS DE OSCILACION: OREJAS y MANDIBULA (deben ir ANTES de JerryOrganicFilters)
# =============================================================================

class JerryEarOscItem(PropertyGroup):
    """Un intervalo de oscilacion de orejas con sus parametros."""
    label:       StringProperty(name="Etiqueta", default="Orejas")
    frame_start: IntProperty(name="Inicio", default=1, min=0, soft_max=99999)
    frame_end:   IntProperty(name="Fin",    default=80, min=1, soft_max=99999)
    amplitude:   FloatProperty(name="Amplitud (rad)", default=0.12, min=0.01, max=1.0, precision=3)
    speed:       FloatProperty(name="Velocidad", default=0.06, min=0.005, max=2.0, precision=3)
    phase_l:     FloatProperty(name="Fase ear.L", default=0.0, min=0.0, max=6.28, precision=2)
    phase_r:     FloatProperty(name="Fase ear.R", default=1.57, min=0.0, max=6.28, precision=2)
    axis:        EnumProperty(name="Eje", default="Z",
        items=[("X","X",""),("Y","Y",""),("Z","Z","")])
    enabled:     BoolProperty(name="Activo", default=True)


class JerryJawOscItem(PropertyGroup):
    """Un intervalo de oscilacion de mandibula con sus parametros."""
    label:       StringProperty(name="Etiqueta", default="Mandibula")
    frame_start: IntProperty(name="Inicio", default=1, min=0, soft_max=99999)
    frame_end:   IntProperty(name="Fin",    default=60, min=1, soft_max=99999)
    amplitude:   FloatProperty(name="Apertura (grad)", default=30.0, min=0.0, max=30.0, precision=1,
        description="Apertura maxima de la mandibula: 0° cerrada, 30° abierta al maximo")
    cycles:      IntProperty(name="Ciclos", default=4, min=1, max=200,
        description="Numero de ciclos completos de oscilacion en el rango de frames")
    phase:       FloatProperty(name="Fase", default=0.0, min=0.0, max=6.28, precision=2)
    # NOTA: el eje de oscilacion ya NO es configurable desde la UI. jaw_bot solo
    # sube/baja rotando su eje X local (invariante ante la orientacion del
    # personaje, ver jaw_bot en operators_anim.py). El campo `axis` se conserva
    # unicamente para poder leer configs JSON antiguos sin romperlos; no se usa
    # en el calculo.
    axis:        EnumProperty(name="Ejes", default="X",
        items=[("X","X","Rotacion en X"),("Y","Y","Rotacion en Y"),("Z","Z","Rotacion en Z")])
    transition:  EnumProperty(name="Transicion", default="SINE",
        items=[
            ("SINE",     "Sinusoidal",   "Movimiento suave y ciclico"),
            ("TRIANGLE", "Triangular",   "Apertura/cierre lineal"),
            ("NOISE",    "Noise (habla)","Variacion aleatoria natural para voz"),
        ])
    noise_seed:  IntProperty(name="Semilla noise", default=55, min=0, max=9999)
    enabled:     BoolProperty(name="Activo", default=True)



class JerryEmotionItem(PropertyGroup):
    """Un intervalo de emocion de cejas con sus parametros."""
    label:          StringProperty(name="Etiqueta", default="Emocion")
    frame_start:    IntProperty(name="Inicio", default=1, min=0, soft_max=99999)
    frame_end:      IntProperty(name="Fin",    default=60, min=1, soft_max=99999)
    transition_in:  IntProperty(name="Entrada (frames)", default=8, min=1, max=500,
        description="Frames de transicion base→emocion antes del frame inicio")
    transition_out: IntProperty(name="Salida (frames)", default=8, min=1, max=500,
        description="Frames de transicion emocion→base despues del frame fin")
    interp_type:    EnumProperty(name="Transicion", default="EASE_IN_OUT_SIN",
        items=INTERP_TYPE_ITEMS,
        description="Curva de interpolacion para entrada y salida de la emocion")
    emotion:        EnumProperty(name="Emocion", default="enojado",
        items=[
            ("enojado",                "Enojado",                "Cejas bajas fruncidas"),
            ("triste",                 "Triste",                 "Cejas inclinadas al centro"),
            ("sorprendido",            "Sorprendido",            "Cejas levantadas arqueadas"),
            ("levanta_la_ceja_derecha","Levanta ceja derecha",   "Solo ceja derecha levantada"),
            ("levanta_la_ceja_izquierda","Levanta ceja izquierda","Solo ceja izquierda levantada"),
        ])
    enabled:        BoolProperty(name="Activo", default=True)

class JerryOrganicFilters(PropertyGroup):
    """
    Filtros de movimiento organico post-proceso sobre los keyframes de CONCATENAR.
    """

    enabled: BoolProperty(
        name="Activar filtros organicos",
        description="Aplica todos los filtros habilitados despues de CONCATENAR",
        default=False,
    )

    breathing_enabled: BoolProperty(name="Respiracion", default=True,
        description="Agrega un ciclo suave de respiracion al torso")
    breathing_amplitude: FloatProperty(name="Amplitud", default=0.012, min=0.001, max=0.15, precision=3)
    breathing_speed: FloatProperty(name="Velocidad", default=0.08, min=0.01, max=1.0, precision=3)
    breathing_phase: FloatProperty(name="Fase", default=0.0, min=0.0, max=6.28, precision=2)

    head_sway_enabled: BoolProperty(name="Micro-movimiento cabeza", default=True)
    head_sway_amplitude: FloatProperty(name="Amplitud", default=0.008, min=0.001, max=0.10, precision=3)
    head_sway_speed: FloatProperty(name="Velocidad", default=0.05, min=0.005, max=0.5, precision=3)
    head_sway_seed: IntProperty(name="Semilla", default=42, min=0, max=9999)

    weight_shift_enabled: BoolProperty(name="Desplazamiento de peso", default=False)
    weight_shift_amplitude: FloatProperty(name="Amplitud", default=0.005, min=0.001, max=0.05, precision=3)
    weight_shift_speed: FloatProperty(name="Velocidad", default=0.04, min=0.005, max=0.3, precision=3)

    root_noise_enabled: BoolProperty(name="Noise en ROOT", default=False)
    root_noise_strength: FloatProperty(name="Intensidad", default=0.003, min=0.0001, max=0.05, precision=4)
    root_noise_frequency: FloatProperty(name="Frecuencia", default=0.15, min=0.01, max=2.0, precision=3)
    root_noise_seed: IntProperty(name="Semilla", default=7, min=0, max=9999)

    secondary_motion_enabled: BoolProperty(name="Secondary motion brazos", default=False)
    secondary_motion_lag: FloatProperty(name="Retardo (frames)", default=3.0, min=0.5, max=15.0, precision=1)
    secondary_motion_damping: FloatProperty(name="Amortiguacion", default=0.7, min=0.1, max=0.99, precision=2)

    smooth_curves_enabled: BoolProperty(name="Suavizar fcurves", default=True)
    smooth_passes: IntProperty(name="Pasadas de suavizado", default=2, min=1, max=10)
    smooth_factor: FloatProperty(name="Factor suavizado", default=0.5, min=0.1, max=0.9, precision=2)

    micro_scale_enabled: BoolProperty(name="Micro-escala organica", default=False)
    micro_scale_amplitude: FloatProperty(name="Amplitud", default=0.005, min=0.001, max=0.03, precision=3)

    shoulder_noise_enabled: BoolProperty(name="Noise hombros", default=False)
    shoulder_noise_amplitude: FloatProperty(name="Amplitud", default=0.006, min=0.001, max=0.08, precision=3)
    shoulder_noise_speed: FloatProperty(name="Velocidad", default=0.07, min=0.01, max=0.5, precision=3)
    shoulder_noise_seed: IntProperty(name="Semilla", default=123, min=0, max=9999)

    tail_wag_enabled: BoolProperty(name="Oscilacion cola", default=True)
    tail_wag_amplitude: FloatProperty(name="Amplitud (rad)", default=0.524, min=0.017, max=0.524, precision=3)
    tail_wag_speed: FloatProperty(name="Velocidad", default=0.12, min=0.01, max=1.0, precision=3)
    tail_wag_phase: FloatProperty(name="Fase", default=0.0, min=0.0, max=6.28, precision=2)
    tail_wag_lag: FloatProperty(name="Retardo entre bones", default=0.35, min=0.0, max=1.0, precision=2)

    # ── Orejas ────────────────────────────────────────────────────────────────
    ear_osc_enabled: BoolProperty(name="Oscilacion orejas", default=False,
        description="Agrega oscilacion organica a ear.L y ear.R en los intervalos definidos")
    ear_items:        CollectionProperty(type=JerryEarOscItem)
    ear_active_idx:   IntProperty(default=0)
    # Formulario de edicion
    ear_edit_label:       StringProperty(name="Etiqueta", default="Orejas")
    ear_edit_frame_start: IntProperty(name="Inicio", default=1, min=0, soft_max=99999,
        description="Frame ABSOLUTO de la escena/Blender (el mismo numero que ves en la linea de tiempo), no relativo al segmento")
    ear_edit_frame_end:   IntProperty(name="Fin",    default=80, min=1, soft_max=99999,
        description="Frame ABSOLUTO de la escena/Blender (el mismo numero que ves en la linea de tiempo), no relativo al segmento")
    ear_edit_amplitude:   FloatProperty(name="Amplitud (rad)", default=0.12, min=0.01, max=1.0, precision=3)
    ear_edit_speed:       FloatProperty(name="Velocidad", default=0.06, min=0.005, max=2.0, precision=3)
    ear_edit_phase_l:     FloatProperty(name="Fase ear.L", default=0.0, min=0.0, max=6.28, precision=2)
    ear_edit_phase_r:     FloatProperty(name="Fase ear.R", default=1.57, min=0.0, max=6.28, precision=2)
    ear_edit_axis:        EnumProperty(name="Eje", default="Z",
        items=[("X","X","Rotacion en X"),("Y","Y","Rotacion en Y"),("Z","Z","Rotacion en Z")])
    ear_edit_mode:        EnumProperty(name="Modo", default="ADD",
        items=[("ADD","Agregar",""),("EDIT","Editar","")])
    ear_edit_source_idx:  IntProperty(default=-1)

    # ── Mandibula ─────────────────────────────────────────────────────────────
    jaw_osc_enabled: BoolProperty(name="Oscilacion mandibula", default=False,
        description="Agrega oscilacion organica a jaw_bot para simular habla en los intervalos definidos")
    jaw_items:        CollectionProperty(type=JerryJawOscItem)
    jaw_active_idx:   IntProperty(default=0)
    # Formulario de edicion
    jaw_edit_label:       StringProperty(name="Etiqueta", default="Mandibula")
    jaw_edit_frame_start: IntProperty(name="Inicio", default=1, min=0, soft_max=99999,
        description="Frame ABSOLUTO de la escena/Blender (el mismo numero que ves en la linea de tiempo), no relativo al segmento")
    jaw_edit_frame_end:   IntProperty(name="Fin",    default=60, min=1, soft_max=99999,
        description="Frame ABSOLUTO de la escena/Blender (el mismo numero que ves en la linea de tiempo), no relativo al segmento")
    jaw_edit_amplitude:   FloatProperty(name="Apertura (grad)", default=30.0, min=0.0, max=30.0, precision=1,
        description="Apertura maxima de la mandibula: 0° cerrada, 30° abierta al maximo")
    jaw_edit_cycles:      IntProperty(name="Ciclos", default=4, min=1, max=200,
        description="Numero de ciclos completos de oscilacion en el rango de frames")
    jaw_edit_phase:       FloatProperty(name="Fase", default=0.0, min=0.0, max=6.28, precision=2)
    jaw_edit_transition:  EnumProperty(name="Transicion", default="SINE",
        items=[
            ("SINE",     "Sinusoidal",   "Movimiento suave y ciclico"),
            ("TRIANGLE", "Triangular",   "Apertura/cierre lineal"),
            ("NOISE",    "Noise (habla)","Variacion aleatoria natural para voz"),
        ])
    jaw_edit_noise_seed:  IntProperty(name="Semilla noise", default=55, min=0, max=9999)
    jaw_edit_mode:        EnumProperty(name="Modo", default="ADD",
        items=[("ADD","Agregar",""),("EDIT","Editar","")])
    jaw_edit_source_idx:  IntProperty(default=-1)

    # ── Emociones (sejas_1_jerry / sejas_2_jerry) ────────────────────────────────────────
    emotion_enabled: BoolProperty(name="Filtro de emociones", default=False,
        description="Aplica variaciones de pose en las cejas de Jerry en los intervalos definidos")
    emotion_items:        CollectionProperty(type=JerryEmotionItem)
    emotion_active_idx:   IntProperty(default=0)
    # Formulario de edicion
    emotion_edit_label:            StringProperty(name="Etiqueta", default="Emocion")
    emotion_edit_frame_start:      IntProperty(name="Inicio", default=1, min=0, soft_max=99999,
        description="Frame ABSOLUTO de la escena/Blender (el mismo numero que ves en la linea de tiempo), no relativo al segmento")
    emotion_edit_frame_end:        IntProperty(name="Fin",    default=60, min=1, soft_max=99999,
        description="Frame ABSOLUTO de la escena/Blender (el mismo numero que ves en la linea de tiempo), no relativo al segmento")
    emotion_edit_transition_in:    IntProperty(name="Entrada (frames)", default=8, min=1, max=500)
    emotion_edit_transition_out:   IntProperty(name="Salida (frames)",  default=8, min=1, max=500)
    emotion_edit_interp_type:      EnumProperty(name="Transicion", default="EASE_IN_OUT_SIN",
        items=INTERP_TYPE_ITEMS)
    emotion_edit_emotion:          EnumProperty(name="Emocion", default="enojado",
        items=[
            ("enojado",                "Enojado",                "Cejas bajas fruncidas hacia adentro"),
            ("triste",                 "Triste",                 "Cejas inclinadas hacia arriba al centro"),
            ("sorprendido",            "Sorprendido",            "Cejas levantadas y arqueadas"),
            ("levanta_la_ceja_derecha","Levanta ceja derecha",   "Solo la ceja derecha levantada"),
            ("levanta_la_ceja_izquierda","Levanta ceja izquierda","Solo la ceja izquierda levantada"),
        ])
    emotion_edit_mode:             EnumProperty(name="Modo", default="ADD",
        items=[("ADD","Agregar",""),("EDIT","Editar","")])
    emotion_edit_source_idx:       IntProperty(default=-1)


# =============================================================================
# BONE OSCILLATIONS
# =============================================================================

class JerryBoneOscillationItem(PropertyGroup):
    label: StringProperty(name="Etiqueta", default="Oscilacion")
    bone_name: StringProperty(name="Bone", default="")
    frame_start: IntProperty(name="Frame inicio", default=1, min=0, soft_max=99999)
    frame_end:   IntProperty(name="Frame fin",   default=60, min=1, soft_max=99999)
    axis_x: BoolProperty(name="X", default=False)
    axis_y: BoolProperty(name="Y", default=False)
    axis_z: BoolProperty(name="Z", default=True)
    amplitude: FloatProperty(name="Amplitud (grad)", default=30.0, min=0.1, max=360.0, precision=1)
    angle_offset: FloatProperty(name="Offset base (grad)", default=0.0, min=-360.0, max=360.0, precision=1, subtype="ANGLE")
    num_cycles: IntProperty(name="Numero de ciclos", default=4, min=1, max=999)
    phase: FloatProperty(name="Fase (rad)", default=0.0, min=0.0, max=6.2832, precision=3)
    wave_type: EnumProperty(name="Transicion",
        items=[
            ("SINE",          "Sinusoidal",          "Oscilacion suave y ciclica"),
            ("TRIANGLE",      "Lineal (triangulo)",  "Oscilacion lineal de punta a punta"),
            ("SQUARE",        "Snap (cuadrada)",     "Salto brusco entre los dos extremos"),
            ("NOISE",         "Noise aleatorio",     "Variacion aleatoria"),
            ("SINE_EASE",     "Sine suavizado",      "Seno con ease-in/out"),
            ("ELASTIC",       "Elastico",            "Rebote elastico al final de cada ciclo"),
            ("BOUNCE",        "Rebote (bounce)",     "Decae como una pelota rebotando"),
            ("BREATHE",       "Respiracion",         "Patron lento expansivo"),
            ("HEARTBEAT",     "Latido",              "Doble pulso rapido seguido de pausa"),
            ("NOISE_DRIFT",   "Noise + deriva",      "Noise organico con deriva lenta"),
            ("NOISE_LAYERED", "Noise multicapa",     "Tres frecuencias de noise superpuestas"),
        ],
        default="SINE",
    )
    noise_seed: IntProperty(name="Semilla noise", default=42, min=0, max=99999)
    fade_in:    IntProperty(name="Fade in (fr)",  default=0,  min=0, max=9999,
                    description="Frames de entrada suave (0 = sin fade)")
    fade_out:   IntProperty(name="Fade out (fr)", default=0,  min=0, max=9999,
                    description="Frames de salida suave (0 = sin fade)")
    enabled: BoolProperty(name="Activo", default=True)


class JerryBoneOscillationsSettings(PropertyGroup):
    enabled: BoolProperty(
        name="Activar oscilaciones de bones",
        description="Habilita o deshabilita todas las oscilaciones de bones al ejecutar CONCATENAR",
        default=True,
    )
    items: CollectionProperty(type=JerryBoneOscillationItem)
    active_idx: IntProperty(default=0)

    # ── Modo de formulario: ADD = nueva oscilacion, EDIT = editar existente ──
    edit_mode: EnumProperty(
        name="Modo edicion",
        items=[("ADD", "Agregar", ""), ("EDIT", "Editar", "")],
        default="ADD",
    )
    edit_source_idx: IntProperty(name="Indice item editado", default=-1)

    # ── Formulario de edicion para nueva oscilacion ───────────────────────────
    edit_label:       StringProperty(name="Etiqueta",    default="Oscilacion")
    edit_bone_name:   StringProperty(name="Bone",        default="")
    edit_frame_start: IntProperty(name="Frame inicio",   default=1,    min=0,   soft_max=99999)
    edit_frame_end:   IntProperty(name="Frame fin",      default=60,   min=1,   soft_max=99999)
    edit_axis_x:      BoolProperty(name="X",             default=False)
    edit_axis_y:      BoolProperty(name="Y",             default=False)
    edit_axis_z:      BoolProperty(name="Z",             default=True)
    edit_amplitude:   FloatProperty(name="Amplitud (grad)",      default=30.0, min=0.1, max=360.0, precision=1)
    edit_angle_offset: FloatProperty(name="Offset base (grad)",  default=0.0,  min=-360.0, max=360.0, precision=1)
    edit_num_cycles:  IntProperty(name="Numero de ciclos",       default=4,    min=1, max=999)
    edit_phase:       FloatProperty(name="Fase (rad)",           default=0.0,  min=0.0, max=6.2832, precision=3)
    edit_wave_type:   EnumProperty(name="Transicion",
        items=[
            ("SINE",          "Sinusoidal",         "Oscilacion suave y ciclica"),
            ("TRIANGLE",      "Lineal (triangulo)", "Oscilacion lineal de punta a punta"),
            ("SQUARE",        "Snap (cuadrada)",    "Salto brusco entre los dos extremos"),
            ("NOISE",         "Noise aleatorio",    "Variacion aleatoria"),
            ("SINE_EASE",     "Sine suavizado",     "Seno con ease-in/out"),
            ("ELASTIC",       "Elastico",           "Rebote elastico al final de cada ciclo"),
            ("BOUNCE",        "Rebote (bounce)",    "Decae como una pelota rebotando"),
            ("BREATHE",       "Respiracion",        "Patron lento expansivo"),
            ("HEARTBEAT",     "Latido",             "Doble pulso rapido seguido de pausa"),
            ("NOISE_DRIFT",   "Noise + deriva",     "Noise organico con deriva lenta"),
            ("NOISE_LAYERED", "Noise multicapa",    "Tres frecuencias de noise superpuestas"),
        ],
        default="SINE",
    )
    edit_noise_seed:  IntProperty(name="Semilla noise", default=42, min=0, max=99999)
    edit_fade_in:     IntProperty(name="Fade in (fr)",  default=0,  min=0, soft_max=200)
    edit_fade_out:    IntProperty(name="Fade out (fr)", default=0,  min=0, soft_max=200)


# =============================================================================
# POSE SLOT ITEM (Paso 3 — legacy, mantenido para compatibilidad)
# =============================================================================

class JerryPoseSlotItem(PropertyGroup):
    json_file:   StringProperty(default="")
    pose_label:  StringProperty(default="")
    pose_name:   StringProperty(default="")
    pose_idx:    IntProperty(default=0)
    pose_index:  IntProperty(default=0)
    duration:    IntProperty(name="Frames", default=24, min=1, max=9999)
    entry_ratio: FloatProperty(name="Entrada %", default=0.3, min=0.0, max=1.0, precision=2)
    exit_ratio:  FloatProperty(name="Salida %",  default=0.3, min=0.0, max=1.0, precision=2)
    interp_type: EnumProperty(
        name="Interpolacion",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )
    rot_x: FloatProperty(name="Rot X (grados)", default=0.0)
    rot_y: FloatProperty(name="Rot Y (grados)", default=0.0)
    rot_z: FloatProperty(name="Rot Z (grados)", default=0.0)
    pos_x: FloatProperty(name="Pos X", default=0.0)
    pos_y: FloatProperty(name="Pos Y", default=0.0)
    pos_z: FloatProperty(name="Pos Z", default=0.0)
    # Frame absoluto donde empieza esta pose. Ver JerrySegmentPoseSlot.manual_start
    # para la explicacion completa -- este campo es el espejo de ese mismo
    # sistema en la copia de trabajo que usa jerryst.concatenate.
    # PORTADO desde alfred_animation_studio (Kebyn, 2026-08-06).
    frame_abs_start: IntProperty(name="Frame inicio absoluto", default=0)
    manual_start: BoolProperty(
        name="Frame de inicio manual",
        default=False,
        description=(
            "Si esta activo, 'Frame inicio absoluto' se usa tal cual en vez "
            "de calcularse automaticamente tras la pose anterior."
        ),
    )


# =============================================================================
# SLOT DE POSE DENTRO DE UN SEGMENTO (equivalente a action_poses del JSON)
# =============================================================================

class JerrySegmentPoseSlot(PropertyGroup):
    """Un slot de pose dentro de un JerryAnimSegment (equivale a action_poses del JSON)."""
    json_file:   StringProperty(default="", description="Archivo .json de la pose")
    pose_label:  StringProperty(default="")
    pose_name:   StringProperty(default="", description="Nombre descriptivo de la pose")
    duration:    IntProperty(name="Frames", default=24, min=1, max=9999,
                             description="Duracion de este slot en frames")
    entry_ratio: FloatProperty(name="Entrada %", default=0.3, min=0.0, max=1.0, precision=2,
                               description="Fraccion de blend de entrada")
    exit_ratio:  FloatProperty(name="Salida %",  default=0.3, min=0.0, max=1.0, precision=2,
                               description="Fraccion de blend de salida")
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
    # PORTADO desde alfred_animation_studio (Kebyn, 2026-08-06): ver
    # AlfredSegmentPoseSlot en alfred_animation_studio/properties.py.
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
# SISTEMA DE LANZAR / RECOGER OBJETOS (moved here so JerryAnimSegment can reference it)
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


class JerryThrowWaypoint(PropertyGroup):
    """Punto intermedio en la trayectoria. Coordenadas GLOBALES."""
    label:   StringProperty(name="Etiqueta", default="Punto")
    x:       FloatProperty(name="X", default=0.0, precision=4)
    y:       FloatProperty(name="Y", default=0.0, precision=4)
    z:       FloatProperty(name="Z", default=2.0, precision=4)
    easing:  EnumProperty(name="Easing", items=THROW_EASING_ITEMS, default='SMOOTH')
    enabled: BoolProperty(name="Activo", default=True)


class JerryThrowItem(PropertyGroup):
    """
    Un lanzamiento/recogida de objeto. Un segmento puede tener varios.
    Equivalente a JerryObjectImportItem para el sistema de lanzar/recoger.
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
    parent_armature: StringProperty(name="Armature", default="Dog_001_rig")
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
    target_armature: StringProperty(name="Armature (traj.)", default="Dog_001_rig")
    target_bone:     StringProperty(name="Bone origen (traj.)", default="")
    dest_x: FloatProperty(name="X", default=0.0, precision=4)
    dest_y: FloatProperty(name="Y", default=3.0, precision=4)
    dest_z: FloatProperty(name="Z", default=0.0, precision=4)
    easing_global: EnumProperty(name="Easing", items=THROW_EASING_ITEMS, default='SMOOTH')

    # Avanzado
    spin_during_flight: BoolProperty(name="Rotacion en vuelo", default=False)
    spin_turns: FloatProperty(name="Vueltas", default=1.0, min=0.0, max=20.0, precision=1)

    # Waypoints
    waypoints:     CollectionProperty(type=JerryThrowWaypoint)
    waypoints_idx: IntProperty(default=0)

    # UI state
    show_waypoints: BoolProperty(name="Mostrar waypoints", default=True)
    show_advanced:  BoolProperty(name="Mostrar avanzado",  default=False)


class JerryThrowsSettings(PropertyGroup):
    """
    Coleccion de JerryThrowItem para un segmento.
    Equivalente a JerryObjectImportsSettings.
    Se almacena en JerryAnimSegment.throws.
    """
    enabled: BoolProperty(name="Activar Lanzar/Recoger", default=False)
    items:   CollectionProperty(type=JerryThrowItem)
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
    edit_parent_armature: StringProperty(name="Armature", default="Dog_001_rig")
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
    edit_target_armature: StringProperty(name="Armature (traj.)", default="Dog_001_rig")
    edit_target_bone:     StringProperty(name="Bone origen (traj.)", default="")
    edit_dest_x: FloatProperty(name="X", default=0.0, precision=4)
    edit_dest_y: FloatProperty(name="Y", default=3.0, precision=4)
    edit_dest_z: FloatProperty(name="Z", default=0.0, precision=4)
    edit_easing_global: EnumProperty(name="Easing", items=THROW_EASING_ITEMS, default='SMOOTH')
    edit_spin_during_flight: BoolProperty(name="Rotacion en vuelo", default=False)
    edit_spin_turns: FloatProperty(name="Vueltas", default=1.0, min=0.0, max=20.0, precision=1)


# =============================================================================
# NUEVO: SEGMENTO DE ANIMACION (Paso 3)
# =============================================================================

# PORTADO desde alfred_animation_studio (Kebyn, 2026-08-05): un intervalo de
# parpadeo automatico propio de UN segmento. Antes Jerry solo tenia parpadeo
# GLOBAL (scene.jerryst.eye_expr.blink_* — un unico rango para toda la
# timeline, ver operators_anim.py _build_blink_sequence_data), sin forma de
# tener "un parpadeo por segmento" como pidio Kebyn. Misma estructura que
# ALFREDBlinkInterval en alfred_animation_studio/properties.py.
class JerryBlinkInterval(PropertyGroup):
    """Un intervalo de parpadeo automatico dentro de UN segmento del Paso 3."""
    label:          StringProperty(name="Etiqueta", default="Parpadeo")
    frame_start:    IntProperty(name="Inicio", default=1, min=0, soft_max=99999)
    frame_end:      IntProperty(name="Fin",    default=60, min=1, soft_max=99999)
    blink_count:    IntProperty(name="N. parpadeos", default=1, min=1, max=20)
    blink_duration: IntProperty(name="Frames/parpadeo", default=9, min=6, max=30)
    enabled:        BoolProperty(name="Activo", default=True)


class JerryBoneBlockInterval(PropertyGroup):
    """
    PORTADO desde alfred_animation_studio (AlfredBoneBlockInterval, Kebyn,
    2026-08-08): un intervalo de frames durante el cual un bone especifico
    del Filtro de bones queda excluido de las poses del segmento, ADEMAS
    del checkbox simple (que bloquea el bone en TODO el segmento). Un mismo
    bone puede tener multiples intervalos independientes (ej: bloqueado en
    60-100, luego otra vez en 500-630).
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


class JerryBoneBlockEntry(PropertyGroup):
    """
    PORTADO desde alfred_animation_studio (AlfredBoneBlockEntry, Kebyn,
    2026-08-08): contenedor de intervalos de bloqueo para UN bone dentro de
    un segmento. 'bone_key' corresponde al nombre del atributo filter_* del
    bone (ej: 'filter_right_arm') para poder ubicarlo facilmente.
    """
    bone_key:  StringProperty(name="Bone", default="")
    intervals: CollectionProperty(type=JerryBoneBlockInterval)
    intervals_idx: IntProperty(default=0)


class JerryAnimSegment(PropertyGroup):
    """
    Un segmento dentro de la animacion generada por Pasos 1+2.

    Contiene su propio intervalo de frames [frame_start, frame_end] y su
    configuracion completa de poses (inicio, fin, slots intermedios), igual
    al JSON exportado por el sistema anterior.  Cada segmento es autocontenido:
    se puede guardar/cargar/aplicar de forma independiente.
    """

    # ── Identificacion ────────────────────────────────────────────────────────
    label: StringProperty(
        name="Etiqueta",
        default="Segmento",
        description="Nombre descriptivo del segmento para identificarlo en la lista",
    )

    # ── Rango de frames dentro de la animacion de recorrido ──────────────────
    frame_start: IntProperty(
        name="Frame inicio",
        default=1, min=1, soft_max=99999,
        description="Frame absoluto de Blender donde comienza este segmento",
    )
    frame_end: IntProperty(
        name="Frame fin",
        default=48, min=2, soft_max=99999,
        description="Frame absoluto de Blender donde termina este segmento",
    )

    # ── Configuracion de poses (espejo del JSON exportado) ────────────────────
    # NOTA (Kebyn, 2026-08-06): el sistema de "Pose INICIO" / "Pose FIN" por
    # segmento (bookend cargado desde un JSON aparte) se elimino por ser logica
    # de versiones antiguas -- ver refactor equivalente ya aplicado en Alfred
    # (pose_inicio/pose_fin -> action_poses). Ahora el primer y ultimo item de
    # `action_poses` cumplen ese rol directamente (ver JRRST_OT_Concatenate).

    # Slots de accion intermedios (action_poses del JSON)
    action_poses:     CollectionProperty(type=JerrySegmentPoseSlot,
                          description="Secuencia de poses intermedias del segmento")
    action_poses_idx: IntProperty(default=0)

    # Parametros globales de la animacion del segmento
    fps:         IntProperty(name="FPS", default=24, min=1, max=120)
    entry_ratio: FloatProperty(name="Blend entrada", default=0.30, min=0.05, max=0.49,
                               step=1, precision=2)
    exit_ratio:  FloatProperty(name="Blend salida",  default=0.30, min=0.05, max=0.49,
                               step=1, precision=2)

    # Exportacion del segmento
    export_slot_number: IntProperty(name="Numero de slot", default=1, min=1, max=999)
    export_type:        StringProperty(name="Tipo de animacion", default="idle")
    export_desc:        StringProperty(name="Descripcion", default="")
    # Marca este segmento para exportacion en modo "Segmentos seleccionados"
    export_selected:    BoolProperty(
        name="Exportar este segmento",
        description="Incluir este segmento al exportar en modo 'Segmentos seleccionados'",
        default=False,
    )
    # Nombre de la action dedicada creada al crear el segmento en modo recorrido
    seg_action_name:    StringProperty(name="Action del segmento", default="")

    # ── Pose INTERMEDIA legacy (para compatibilidad con el modulador de recorrido) ──
    frame_mid: IntProperty(
        name="Frame intermedio",
        default=0, min=0, soft_max=99999,
        description="Frame absoluto donde se aplica la pose intermedia (0 = sin intermedio)",
    )
    pose_mid_file:  StringProperty(name="Pose intermedia", default="")
    pose_mid_label: StringProperty(default="")
    interp_type: EnumProperty(
        name="Interpolacion",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
        description="Curva de interpolacion entre la pose inicio y la pose fin",
    )
    interp_mid_to_end: EnumProperty(
        name="Interp. mid→fin",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )

    # ── Blend con la animacion subyacente de recorrido ────────────────────────
    blend_in_frames: IntProperty(
        name="Blend entrada (frames)",
        default=8, min=0, max=120,
        description="Frames de transicion desde la animacion de recorrido hasta la pose inicio",
    )
    blend_out_frames: IntProperty(
        name="Blend salida (frames)",
        default=8, min=0, max=120,
        description="Frames de transicion desde la pose fin de vuelta a la animacion de recorrido",
    )

    # ── Bones afectados ───────────────────────────────────────────────────────
    affect_body:      BoolProperty(name="Cuerpo",       default=True)
    affect_left_arm:  BoolProperty(name="Brazo Izq.",   default=True)
    affect_right_arm: BoolProperty(name="Brazo Der.",   default=True)
    affect_left_leg:  BoolProperty(name="Pierna Izq.",  default=True)
    affect_right_leg: BoolProperty(name="Pierna Der.",  default=True)
    affect_root:      BoolProperty(name="Root (main)",  default=False,
        description="Modular tambien el bone root. Normalmente False porque el recorrido lo controla.")
    affect_shield:    BoolProperty(name="Escudo",       default=False)
    affect_spear:     BoolProperty(name="Lanza",        default=False)

    # ── Intensidad de mezcla ─────────────────────────────────────────────────
    blend_strength: FloatProperty(
        name="Fuerza de mezcla",
        default=1.0, min=0.0, max=1.0, precision=2,
        description="1.0 = la pose reemplaza los fcurves de recorrido. 0.0 = no hace nada.",
    )

    # ── Filtro de bones (se excluyen del bake de CONCATENAR) ─────────────────
    # Los bones marcados aqui NO reciben keyframes de configuracion en CONCATENAR.
    # Su animacion proviene exclusivamente del recorrido base (Reproducir recorrido).
    # Por defecto las patas estan filtradas (comportamiento original).
    filter_show:          BoolProperty(name="Filtrar bones", default=False,
        description="Despliega la seleccion manual de bones a filtrar antes de CONCATENAR")
    filter_main_bone:     BoolProperty(name="Dog_001_rig",    default=True,
        description="Filtrar el bone root principal")
    filter_body:          BoolProperty(name="spine_1",    default=False,
        description="Filtrar el cuerpo")
    filter_left_arm:      BoolProperty(name="front_shoulder.L",  default=True,
        description="Filtrar brazo izquierdo")
    filter_right_arm:     BoolProperty(name="front_shoulder.R", default=True,
        description="Filtrar brazo derecho")
    filter_right_leg:     BoolProperty(name="shoulder.R", default=True,
        description="Filtrar pierna derecha (recorrido base la controla)")
    filter_left_leg:      BoolProperty(name="shoulder.L",  default=True,
        description="Filtrar pierna izquierda (recorrido base la controla)")
    filter_shield:        BoolProperty(name="tail_1",  default=False,
        description="Filtrar el escudo")
    filter_spear:         BoolProperty(name="tail_2",   default=False,
        description="Filtrar la lanza")
    filter_tail_3:        BoolProperty(name="tail_3",   default=False,
        description="Filtrar tail_3")

    # Columna vertebral adicional
    filter_spine_2:       BoolProperty(name="spine_2",  default=False,
        description="Filtrar spine_2")
    filter_spine_3:       BoolProperty(name="spine_3",  default=False,
        description="Filtrar spine_3")
    filter_spine_4:       BoolProperty(name="spine_4",  default=False,
        description="Filtrar spine_4")
    filter_spine_5:       BoolProperty(name="spine_5",  default=False,
        description="Filtrar spine_5")
    filter_spine_6:       BoolProperty(name="spine_6",  default=False,
        description="Filtrar spine_6")
    filter_spine_7:       BoolProperty(name="spine_7",  default=False,
        description="Filtrar spine_7")

    # Patas delanteras
    filter_front_thigh_l: BoolProperty(name="front_thigh.L",  default=True,
        description="Filtrar muslo delantero izquierdo")
    filter_front_thigh_r: BoolProperty(name="front_thigh.R",  default=True,
        description="Filtrar muslo delantero derecho")
    filter_front_shin_l:  BoolProperty(name="front_shin.L",   default=True,
        description="Filtrar tibia delantera izquierda")
    filter_front_shin_r:  BoolProperty(name="front_shin.R",   default=True,
        description="Filtrar tibia delantera derecha")
    filter_front_foot_l:  BoolProperty(name="front_foot.L",   default=True,
        description="Filtrar pata delantera izquierda")
    filter_front_foot_r:  BoolProperty(name="front_foot.R",   default=True,
        description="Filtrar pata delantera derecha")
    filter_front_toe_l:   BoolProperty(name="front_toe.L",    default=True,
        description="Filtrar dedo delantero izquierdo")
    filter_front_toe_r:   BoolProperty(name="front_toe.R",    default=True,
        description="Filtrar dedo delantero derecho")

    # Patas traseras
    filter_thigh_l:       BoolProperty(name="thigh.L",  default=True,
        description="Filtrar muslo trasero izquierdo")
    filter_thigh_r:       BoolProperty(name="thigh.R",  default=True,
        description="Filtrar muslo trasero derecho")
    filter_shin_l:        BoolProperty(name="shin.L",   default=True,
        description="Filtrar tibia trasera izquierda")
    filter_shin_r:        BoolProperty(name="shin.R",   default=True,
        description="Filtrar tibia trasera derecha")
    filter_foot_l:        BoolProperty(name="foot.L",   default=True,
        description="Filtrar pata trasera izquierda")
    filter_foot_r:        BoolProperty(name="foot.R",   default=True,
        description="Filtrar pata trasera derecha")
    filter_toe_l:         BoolProperty(name="toe.L",    default=True,
        description="Filtrar dedo trasero izquierdo")
    filter_toe_r:         BoolProperty(name="toe.R",    default=True,
        description="Filtrar dedo trasero derecho")

    # Cabeza
    filter_jaw_bot:       BoolProperty(name="jaw_bot",  default=False,
        description="Filtrar mandibula inferior")
    filter_jaw_top:       BoolProperty(name="jaw_top",  default=False,
        description="Filtrar mandibula superior")
    filter_scull:         BoolProperty(name="scull",    default=False,
        description="Filtrar craneo")
    filter_scull_1:       BoolProperty(name="scull_1",  default=False,
        description="Filtrar craneo secundario")
    filter_ear_l:         BoolProperty(name="ear.L",    default=False,
        description="Filtrar oreja izquierda")
    filter_ear_r:         BoolProperty(name="ear.R",    default=False,
        description="Filtrar oreja derecha")
    filter_sombrero:      BoolProperty(name="sombrero", default=False,
        description="Filtrar sombrero")

    # Cejas / ojos
    filter_sejas_1:       BoolProperty(name="sejas_1_jerry", default=False,
        description="Filtrar cejas 1")
    filter_sejas_2:       BoolProperty(name="sejas_2_jerry", default=False,
        description="Filtrar cejas 2")

    # Bones auxiliares (no_bone)
    filter_no_bone_01:    BoolProperty(name="no_bone_01", default=False,
        description="Filtrar no_bone_01")
    filter_no_bone_02:    BoolProperty(name="no_bone_02", default=False,
        description="Filtrar no_bone_02")
    filter_no_bone_03:    BoolProperty(name="no_bone_03", default=False,
        description="Filtrar no_bone_03")
    filter_no_bone_04:    BoolProperty(name="no_bone_04", default=False,
        description="Filtrar no_bone_04")

    # Intervalos de bloqueo por bone (bloqueo parcial, independiente del
    # checkbox filter_* de arriba, que bloquea TODO el segmento). PORTADO
    # desde alfred_animation_studio (Kebyn, 2026-08-08): un mismo bone puede
    # tener N intervalos de frames distintos ("dividir en partes" el
    # bloqueo). Ver JerryBoneBlockEntry/JerryBoneBlockInterval arriba y
    # _get_bone_block_entry / _bone_blocked_in_intervals en
    # operators_segments.py.
    bone_blocks: CollectionProperty(type=JerryBoneBlockEntry)

    # ── Enabled ───────────────────────────────────────────────────────────────
    enabled: BoolProperty(
        name="Activo",
        default=True,
        description="Desmarcar para ignorar este segmento al aplicar",
    )

    # ── UI: mostrar/ocultar configuracion del segmento ───────────────────────
    show_config: BoolProperty(
        name="Mostrar configuracion",
        default=True,
        description="Despliega la configuracion de poses de este segmento",
    )

    # ── Modo 1 coordenada (frame_end calculado automaticamente) ───────────────
    single_coord_mode: BoolProperty(
        name="Modo 1 coordenada",
        default=False,
        description=(
            "El segmento fue creado con una sola coordenada de recorrido. "
            "frame_end se calcula automaticamente a partir de la suma de duraciones "
            "de las poses (inicio + action_poses + fin) mas los filtros organicos."
        ),
    )
    frame_end_auto: IntProperty(
        name="Frame fin (calculado)",
        default=0, min=0, soft_max=99999,
        description=(
            "Frame fin calculado automaticamente tras CONCATENAR. "
            "Solo valido cuando single_coord_mode = True."
        ),
    )

    # ── Lanzar / Recoger objetos (por segmento) ─────────────────────────────
    throws: PointerProperty(type=JerryThrowsSettings)

    # ── Parpadeo automatico (propio de este segmento) ─────────────────────────
    # PORTADO desde alfred_animation_studio (Kebyn, 2026-08-05): ver
    # JerryBlinkInterval arriba. Se auto-puebla con UN intervalo por defecto
    # al crear el segmento (ver _aplicar_defaults_organicos_jerry en
    # operators_segments.py) y se aplica en JRRSTSEG_OT_Apply.
    blink_intervals:     CollectionProperty(type=JerryBlinkInterval)
    blink_interval_idx:  IntProperty(default=0)

    # ── AISLAMIENTO POR SEGMENTO -- Filtros organicos (Kebyn + Claude,
    # 2026-08-06) ──────────────────────────────────────────────────────────
    # ANTES: los Filtros organicos (respiracion, sway de cabeza, cola,
    # oscilacion de orejas/mandibula, emociones de cejas, etc.) que se veian
    # dentro del box de CADA segmento en el panel (Paso 3) en realidad
    # apuntaban a scene.jerryst.organic -- UNA UNICA instancia global
    # compartida por todos los segmentos. El panel dibujaba una copia visual
    # por segmento, pero todas escribian y leian el mismo dato: editar un
    # filtro (o agregar/editar/quitar un intervalo de orejas, mandibula o
    # emocion) en cualquier segmento lo aplicaba a TODOS los demas al
    # concatenar -- el mismo bug que ya se habia corregido en
    # alfred_animation_studio el 2026-08-03 (ver AlfredAnimSegment.organic).
    #
    # AHORA: cada JerryAnimSegment tiene su PROPIA instancia de
    # JerryOrganicFilters -- incluye automaticamente ear_items/jaw_items/
    # emotion_items y sus formularios de edicion, porque esas colecciones ya
    # viven DENTRO de JerryOrganicFilters. Son completamente independientes
    # entre segmentos -- editar uno no afecta a los demas, y CONCATENAR usa
    # exclusivamente los valores del segmento que esta procesando en cada
    # paso del loop. scene.jerryst.organic se conserva solo como fallback
    # (paneles fuera de un segmento / compatibilidad).
    organic: PointerProperty(type=JerryOrganicFilters)


# =============================================================================
# NUEVO: CONFIGURACION GLOBAL DEL PASO 3
# =============================================================================

class JerryAnimSegmentsSettings(PropertyGroup):
    """
    Coleccion de JerryAnimSegment y estado global del sistema de refinado (Paso 3).

    Se almacena en bpy.types.Scene.jerry_segs y es independiente de jerryst
    para no interferir con la logica de Pasos 1 y 2.
    """

    # ── Lista de segmentos ────────────────────────────────────────────────────
    segments: CollectionProperty(type=JerryAnimSegment)
    active_index: IntProperty(default=0)

    # ── Armature sobre el que opera ───────────────────────────────────────────
    armature_name: StringProperty(
        name="Armature",
        default="Dog_001_rig",
        description="Armature principal del personaje (debe coincidir con el de Pasos 1+2)",
    )

    # ── Carpeta de poses (.json) ──────────────────────────────────────────────
    poses_dir: StringProperty(
        name="Carpeta de poses",
        default=DEFAULT_POSES_DIR,
        subtype="DIR_PATH",
        description="Carpeta donde estan los archivos .json de poses",
    )

    # ── Accion de origen (la generada por path_recorder) ─────────────────────
    source_action_name: StringProperty(
        name="Accion origen",
        default="",
        description="Nombre de la accion NLA generada por el Paso 2 (dejar vacia para autodetectar)",
    )

    # NOTA (Kebyn, 2026-08-27): sistema de "Secuencia de Ojos" por-segmento
    # (eye_expr, eye_global_start_frame, eye_start_*, eye_slots, eye_end_*)
    # eliminado por no usarse -- ver panels.py / operators_base.py para el
    # resto retirado junto con el. jerryst.eye_expr (sistema de expresiones
    # a nivel de personaje, en eye_system.py / eye_library.py) no se toco.


    start_frame: IntProperty(
        name="Frame inicio",
        description="Frame de la timeline donde comienza la animacion",
        default=1, min=1,
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

    # ── Libreria de ojos ─────────────────────────────────────────────────────
    eye_lib_dir: StringProperty(
        name="Libreria de ojos",
        default=_DEFAULT_EYE_LIB_DIR,
        subtype="DIR_PATH",
        description="Carpeta con los JSON de expresiones de ojos",
    )
    eye_lib_entries:  CollectionProperty(type=JerryEyeLibEntry)
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

    # ── Exportacion ──────────────────────────────────────────────────────────
    export_slot_number: IntProperty(name="Numero de slot", default=1, min=1, max=999)
    export_type:        StringProperty(name="Tipo", default="refinado")
    export_desc:        StringProperty(name="Descripcion", default="")
    anim_dir:           StringProperty(
        name="Carpeta exportacion",
        default=DEFAULT_ANIM_DIR,
        subtype="DIR_PATH",
    )

    # ── Estado ────────────────────────────────────────────────────────────────
    status_msg:     StringProperty(default="")
    segs_applied:   BoolProperty(default=False)

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
    edit_frame_mid: IntProperty(
        name="Frame intermedio",
        default=0, min=0, soft_max=99999,
        description="Frame donde se aplica la pose intermedia (0 = sin intermedio)",
    )
    edit_use_mid: BoolProperty(
        name="Usar pose intermedia",
        default=False,
        description="Activar para definir una pose intermedia",
    )
    # Pose inicio
    edit_pose_start_file:  StringProperty(name="Archivo pose inicio",  default="")
    edit_pose_start_label: StringProperty(name="Pose inicio",          default="")
    edit_start_frames: IntProperty(
        name="Frames inicio",
        default=10, min=1, soft_max=200,
        description="Duracion de la transicion de entrada",
    )
    edit_interp: EnumProperty(
        name="Interpolacion inicio",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )
    # Pose intermedia
    edit_pose_mid_file:  StringProperty(name="Archivo pose intermedia", default="")
    edit_pose_mid_label: StringProperty(name="Pose intermedia",         default="")
    edit_interp_mid: EnumProperty(
        name="Interpolacion intermedia",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )
    # Pose fin
    edit_pose_end_file:  StringProperty(name="Archivo pose fin",  default="")
    edit_pose_end_label: StringProperty(name="Pose fin",          default="")
    edit_end_frames: IntProperty(
        name="Frames fin",
        default=10, min=1, soft_max=200,
        description="Duracion de la transicion de salida",
    )
    edit_interp_end: EnumProperty(
        name="Interpolacion fin",
        items=INTERP_TYPE_ITEMS,
        default="SMOOTH",
    )

    # ── Nombre para guardar/cargar config de esta seccion ────────────────────
    config_name: StringProperty(
        name="Nombre config Paso 3",
        default="segs_config",
        description="Nombre del archivo .json de configuracion del Paso 3",
    )
    config_dir: StringProperty(
        name="Carpeta config",
        default=DEFAULT_CONFIG_DIR,
        subtype="DIR_PATH",
    )


# =============================================================================
# FILTRO: IMPORTACION DE OBJETOS (props, accesorios)
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
    a la lista (JerryObjectImportItem). Si el objeto ya fue importado
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
    (JerryObjectImportsSettings.edit_*). Si hay un objeto importado en
    preview (edit_imported_object_name), se actualiza su transform en vivo
    para ver el resultado mientras se ajustan los valores.
    """
    obj = bpy.data.objects.get(self.edit_imported_object_name)
    if obj is not None:
        _oi_apply_transform_to_object(
            obj, self.edit_loc_x, self.edit_loc_y, self.edit_loc_z,
            self.edit_rot_x, self.edit_rot_y, self.edit_rot_z, self.edit_scale_uniform,
        )


class JerryObjectImportItem(PropertyGroup):
    """
    Un intervalo de importacion de objeto para Jerry.
    Importa un objeto .blend en el frame de inicio y lo oculta fuera del rango.
    """
    label: StringProperty(name="Etiqueta", default="Objeto",
        description="Nombre descriptivo de este objeto importado")
    object_folder: StringProperty(name="Carpeta", default="vanilla/shield",
        description="Ruta relativa dentro de objetos/ hasta la carpeta del objeto "
                     "(ej: vanilla/shield, jerry/hueso). Se completa automaticamente "
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
    parent_armature: StringProperty(name="Armature", default="Dog_001_rig",
        description="Nombre del armature al que parentear el objeto. "
                     "Jerry tiene un unico armature en la escena llamado 'Dog_001_rig'.")
    parent_bone: StringProperty(name="Bone de parenteo", default="jaw_top",
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
        description="Indice del segmento (jerry_segs.segments) al que pertenece este objeto. "
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
        default=8, min=1, max=60,
    )


# (JerryThrowWaypoint, JerryThrowItem, JerryThrowsSettings moved above JerryAnimSegment)


class JerryObjectImportsSettings(PropertyGroup):
    """Configuracion global del sistema de importacion de objetos de Jerry."""
    enabled: BoolProperty(
        name="Activar importacion de objetos",
        description=(
            "Habilita el sistema de importacion de objetos. "
            "Se generan al presionar EXPORTAR (incluidos en el .py exportado)."
        ),
        default=False,
    )
    items: CollectionProperty(type=JerryObjectImportItem)
    active_idx: IntProperty(default=0)

    # ── Editor de nuevo objeto ──────────────────────────────────────────────
    edit_label:          StringProperty(name="Etiqueta", default="Mi objeto")
    edit_object_folder:  StringProperty(name="Carpeta", default="vanilla/shield")
    edit_blend_filename: StringProperty(name="Archivo .blend", default="shield.blend")
    edit_object_name:    StringProperty(name="Nombre objeto", default="shield")
    edit_frame_start:    IntProperty(name="Frame inicio", default=1, min=0, soft_max=99999)
    edit_frame_end:      IntProperty(name="Frame fin",   default=60, min=1, soft_max=99999)
    edit_parent_armature: StringProperty(name="Armature", default="Dog_001_rig",
        description="Nombre del armature al que parentear el objeto. "
                     "Jerry tiene un unico armature en la escena llamado 'Dog_001_rig'.")
    edit_parent_bone:    StringProperty(name="Bone de parenteo", default="jaw_top")
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
        items=JerryObjectImportItem.TRANSITION_IN_ITEMS,
        default='NONE',
    )
    edit_transition_in_duration: IntProperty(
        name="Duración entrada (frames)",
        default=8, min=1, max=60,
    )
    edit_transition_out: bpy.props.EnumProperty(
        name="Transición desaparición",
        description="Efecto de salida del objeto al frame fin",
        items=JerryObjectImportItem.TRANSITION_OUT_ITEMS,
        default='NONE',
    )
    edit_transition_out_duration: IntProperty(
        name="Duración salida (frames)",
        default=8, min=1, max=60,
    )


# =============================================================================
# SETTINGS PRINCIPAL (Pasos 1 y 2 — sin cambios salvo adicion de historia_json)
# =============================================================================

class JerryStudioSettings(PropertyGroup):

    # ── Carpetas y rutas ─────────────────────────────────────────────────────
    poses_dir: StringProperty(name="Poses", default=DEFAULT_POSES_DIR, subtype="DIR_PATH")
    anim_dir:  StringProperty(name="Animaciones", default=DEFAULT_ANIM_DIR, subtype="DIR_PATH")
    config_dir: StringProperty(name="Configuraciones", default=DEFAULT_CONFIG_DIR, subtype="DIR_PATH")
    # Carpeta donde vive jerry_pose_library.json (libreria central usada por
    # el pipeline de generaciones). El nombre_legible ('_semantica') de cada
    # pose se lee de aqui para mostrarlo en el panel al seleccionar un slot.
    reglas_dir: StringProperty(
        name="Reglas (pose_library)",
        default=DEFAULT_REGLAS_DIR,
        subtype="DIR_PATH",
        description="Carpeta 'reglas' donde esta jerry_pose_library.json",
    )
    pose_changes_dir: StringProperty(
        name="Cambios de pose",
        description="Carpeta donde 'Guardar cambios' exporta un .json por "
                    "cada guardado del editor de pose en vivo (huesos + "
                    "Root 'jerry'), sin tocar la libreria de poses original",
        default=DEFAULT_POSE_CHANGES_DIR, subtype="DIR_PATH",
    )
    historia_json: StringProperty(
        name="historia_jerry.json",
        default=DEFAULT_HISTORIA_JSON,
        subtype="FILE_PATH",
        description="Ruta al JSON de historia con key_points y orientacion_inicial",
    )

    # ── Armature principal ───────────────────────────────────────────────────
    armature_name: StringProperty(name="Armature principal", default="Dog_001_rig")

    # ── Importacion de objetos (props, accesorios) ─────────────────────────
    object_imports: PointerProperty(type=JerryObjectImportsSettings)

    # ── Pose inicio ─────────────────────────────────────────────────────────
    pose_start_file:     StringProperty(default="")
    pose_start_name:     StringProperty(default="")
    pose_start_idx:      IntProperty(default=0)
    pose_start_rot_x:    FloatProperty(name="Rot X inicio", default=0.0)
    pose_start_rot_y:    FloatProperty(name="Rot Y inicio", default=0.0)
    pose_start_rot_z:    FloatProperty(name="Rot Z inicio", default=0.0)
    pose_start_pos_x:    FloatProperty(name="Pos X inicio", default=0.0)
    pose_start_pos_y:    FloatProperty(name="Pos Y inicio", default=0.0)
    pose_start_pos_z:    FloatProperty(name="Pos Z inicio", default=0.0)
    pose_start_duration: IntProperty(name="Frames pose inicio", default=10, min=1, soft_max=300)
    pose_start_interp:   EnumProperty(
        name="Interpolacion salida INICIO", items=INTERP_TYPE_ITEMS, default="SMOOTH")

    # ── Pose fin ─────────────────────────────────────────────────────────────
    pose_end_file:     StringProperty(default="")
    pose_end_name:     StringProperty(default="")
    pose_end_idx:      IntProperty(default=0)
    pose_end_rot_x:    FloatProperty(name="Rot X fin", default=0.0)
    pose_end_rot_y:    FloatProperty(name="Rot Y fin", default=0.0)
    pose_end_rot_z:    FloatProperty(name="Rot Z fin", default=0.0)
    pose_end_pos_x:    FloatProperty(name="Pos X fin", default=0.0)
    pose_end_pos_y:    FloatProperty(name="Pos Y fin", default=0.0)
    pose_end_pos_z:    FloatProperty(name="Pos Z fin", default=0.0)
    pose_end_duration: IntProperty(name="Frames pose fin", default=10, min=1, soft_max=300)
    pose_end_interp:   EnumProperty(
        name="Interpolacion entrada FIN", items=INTERP_TYPE_ITEMS, default="SMOOTH")

    # ── Slots de accion ─────────────────────────────────────────────────────
    action_poses:     CollectionProperty(type=JerryPoseSlotItem)
    action_poses_idx:  IntProperty(default=0)
    action_pose_idx:   IntProperty(default=0)

    # ── FPS y frames ─────────────────────────────────────────────────────────
    fps:         IntProperty(name="FPS", default=24, min=1, max=120)
    start_frame: IntProperty(name="Frame inicio", default=1, min=1)

    # ── Ratios de entrada / salida (globales) ─────────────────────────────────
    entry_ratio: FloatProperty(
        name="Blend entrada",
        default=0.30, min=0.05, max=0.49, step=1, precision=2,
    )
    exit_ratio: FloatProperty(
        name="Blend salida",
        default=0.30, min=0.05, max=0.49, step=1, precision=2,
    )

    # ── Filtros organicos ─────────────────────────────────────────────────────
    organic: PointerProperty(type=JerryOrganicFilters)

    # ── Trayectoria / key point ──────────────────────────────────────────────
    root_pos_key_point: EnumProperty(
        name="Key Point destino",
        description="Punto de la historia al que se dirige el personaje en este slot",
        items=_enum_key_points,
    )
    key_point_info: StringProperty(default="")

    # ── Sistema de ojos ───────────────────────────────────────────────────────
    eye_expr: PointerProperty(type=JerryEyeExpressionSettings)

    # ── Sistema de oscilaciones de bones personalizadas ──────────────────────
    bone_oscillations: PointerProperty(type=JerryBoneOscillationsSettings)

    # ── Estado de la animacion generada ─────────────────────────────────────
    anim_generated:   BoolProperty(default=False)
    total_frames_gen: IntProperty(default=0)
    end_frame_gen:    IntProperty(default=0)
    status_msg:       StringProperty(default="")

    # ── Exportacion ─────────────────────────────────────────────────────────
    export_slot_number: IntProperty(name="Numero de slot", default=1, min=1, max=999)
    export_type:        StringProperty(name="Tipo", default="idle")
    export_desc:        StringProperty(name="Descripcion", default="")
    last_export_path:   StringProperty(default="")

    # Modo de exportacion: segmento activo, segmentos seleccionados, o animacion completa
    export_mode: EnumProperty(
        name="Modo de exportacion",
        description="Que parte de la animacion exportar",
        items=[
            ("ACTIVE",   "Segmento activo",        "Exporta solo el segmento activo (comportamiento anterior)", "KEYFRAME",     0),
            ("SELECTED", "Segmentos seleccionados", "Exporta los segmentos marcados en la lista",                "RESTRICT_SELECT_OFF", 1),
            ("ALL",      "Todos los segmentos",     "Exporta cada segmento como un .py separado",               "NLA",          2),
            ("FULL",     "Animacion completa",       "Exporta la timeline completa (inicio → fin) como un solo .py", "RENDER_ANIMATION", 3),
        ],
        default="ACTIVE",
    )

    # ── Extraccion de pose ───────────────────────────────────────────────────
    extract_label:       StringProperty(name="Nombre nueva pose", default="")
    extract_frame:       IntProperty(name="Frame", default=1, min=0, max=99999)
    extract_use_current: BoolProperty(name="Frame actual", default=True)

    # ── Extraer pose rapida (Paso 3, dentro de cada segmento) ─────────────
    # PORTADO desde alfred_animation_studio (Kebyn, 2026-09-04). Version
    # simplificada de "Extraer Nueva Pose" (extract_label/_frame/_use_current
    # arriba): detecta el armature de Jerry automaticamente (sin selector),
    # nombra la pose sola segun que huesos se movieron, y guarda el .json
    # con un solo click. El archivo/indice/etiqueta que acaba de generar
    # "Guardar" quedan aca en espera de que el usuario presione "Importar"
    # (que los agrega a seg.action_poses del segmento correspondiente) y
    # luego se limpian para el siguiente ciclo.
    quickpose_pending_file:  StringProperty(default="")
    quickpose_pending_index: IntProperty(default=0)
    quickpose_pending_label: StringProperty(default="")

    # ── Configuracion de sesion ──────────────────────────────────────────────
    config_name: StringProperty(
        name="Nombre configuracion",
        default="mi_configuracion",
        description="Nombre del archivo de configuracion a guardar (sin extension)",
    )
