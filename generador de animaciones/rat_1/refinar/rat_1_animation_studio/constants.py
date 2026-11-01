# -*- coding: utf-8 -*-
"""
constants.py — Rat 1 Animation Studio

Nombres reales de los objetos del personaje "rat_1", segun el escaneo
rat_1.json (Blender 4.5.8 LTS):

    rat_1     (EMPTY, root, PLAIN_AXES)
      body1_1   (ARMATURE, 22 bones, hijo de rat_1)
        Mesh_0_1  (MESH, 528 verts, hijo de body1_1)

A diferencia de Alfred (multiples accesorios: torch, herramientas, ojos
con shape keys, armature secundaria del arco, etc.), rat_1 es una
jerarquia minima de 3 objetos -- no hay accesorios que anexar todavia.
"""

ROOT_NAME  = "rat_1"      # EMPTY raiz que se desplaza por el recorrido
ARM_NAME   = "body1_1"    # Armature con los 22 bones
MESH_NAME  = "Mesh_0_1"   # Malla del cuerpo (528 verts)

# Lista completa de objetos que pertenecen al personaje -- usada por
# _load_character() en path_recorder.py para aparecer/renombrar/verificar
# visibilidad al importar desde el .blend de referencia.
ALL_OBJECTS = [ROOT_NAME, ARM_NAME, MESH_NAME]

# Bone raiz dentro del armature (equivalente a "Hips_alfred" en Alfred).
# Por ahora no se anima ningun bone (Paso 1/2 solo mueven el EMPTY raiz),
# pero se deja documentado aca para cuando se agregue la biomecanica de
# caminar/saltar_subir/saltar_bajar.
ROOT_BONE = "body1_1"

# =============================================================================
# PASO 3 -- SEGMENTOS / POSES / NLA / CONCATENAR
# (Port reducido desde alfred_animation_studio, pedido explicito de Kebyn:
# "solo el nucleo: crear segmentos, poses (keyframes), NLA y Concatenar".
# Sin sistema de ojos, sin Lanzar/Recoger objetos, sin Invisibilidad de
# Malla, sin filtros organicos -- rat_1 no tiene esos sistemas.)
# =============================================================================

# ─── RUTAS POR DEFECTO (Paso 3) ──────────────────────────────
DEFAULT_POSES_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\rat_1\refinar\poses"
)
DEFAULT_CONFIG_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\rat_1\refinar\configuraciones"
)

# ─── BONES POSABLES (Paso 3) ─────────────────────────────────
# Subconjunto de los 22 bones reales de body1_1 que el sistema de
# segmentos/poses puede animar. Se excluyen los bones faciales (ojos,
# orejas, hocico, nariz, bigotes) -- mismo criterio que Paso 1/2
# (ver PORT_NOTES.md: "Bones faciales... NO se animan").
BONES_LISTA = [
    'body1_1',      # raiz / hips
    'body2_1',      # columna
    'neck_1',
    'head_1',
    'leftArm_1',    'leftHand_1',
    'rightArm_1',   'rightHand_1',
    'leftThigh_1',  'leftFoot_1',
    'rightThigh_1', 'rightFoot_1',
    'tail1_1',      'tail2_1',
]
# Lista "FULL" (compatibilidad con el patron de Alfred, que agrega
# no_bone_XX de relleno para accesorios). rat_1 no tiene accesorios
# todavia, asi que FULL == BONES_LISTA por ahora.
BONES_LISTA_FULL = list(BONES_LISTA)

_BONE_DEFAULT = {"rot": (0.0, 0.0, 0.0), "loc": (0.0, 0.0, 0.0), "scale": (1.0, 1.0, 1.0)}

# ─── CALIFICACION DE POSES (heredado de pose_utils.py, no usado por el
# UI del Paso 3 de rat_1 todavia -- se deja para compatibilidad con
# pose_utils.py, que lo importa) ──────────────────────────────
RATING_STATUS_EXCELENTE  = "EXCELENTE"
RATING_STATUS_REGULAR    = "REGULAR"
RATING_STATUS_DESCARTADA = "DESCARTADA"
RATING_STATUS_NUEVA      = "NUEVA"

def calcular_estado_calificacion(promedio, cantidad):
    if cantidad <= 0:
        return RATING_STATUS_NUEVA
    if promedio >= 8.0:
        return RATING_STATUS_EXCELENTE
    if promedio >= 5.0:
        return RATING_STATUS_REGULAR
    return RATING_STATUS_DESCARTADA

DEFAULT_REGLAS_DIR = DEFAULT_CONFIG_DIR
DEFAULT_POSE_LIBRARY_PATH = DEFAULT_REGLAS_DIR + "\\pose_library.json"

# ─── TIPOS DE INTERPOLACION (identico a Alfred, generico) ────
INTERP_TYPE_ITEMS = [
    # BASICAS
    ("LINEAR",           "Linear",                "Velocidad constante, sin aceleracion"),
    ("SMOOTH",           "Smooth (Smoothstep)",   "Suave inicio y fin. Natural y fluido"),
    # EASE CLASICOS
    ("EASE_IN_QUAD",     "Ease In (Cuadratico)",  "Arranca lento, termina rapido"),
    ("EASE_OUT_QUAD",    "Ease Out (Cuadratico)", "Arranca rapido, frena suave"),
    ("EASE_IN_OUT_QUAD", "Ease In-Out Quad",      "Simetrico lento-rapido-lento"),
    ("EASE_IN_CUBIC",    "Ease In (Cubico)",      "Arranque muy lento, aceleracion pronunciada"),
    ("EASE_OUT_CUBIC",   "Ease Out (Cubico)",     "Frenada fuerte al final"),
    ("EASE_IN_OUT_CUB",  "Ease In-Out Cubico",    "Lento-rapido-lento cubico"),
    ("EASE_IN_QUART",    "Ease In (Quartico)",    "Arranque extremamente lento"),
    ("EASE_OUT_QUART",   "Ease Out (Quartico)",   "Impacto fuerte, parada casi instantanea"),
    ("EASE_IN_OUT_QRT",  "Ease In-Out Quartico",  "Zona media muy rapida"),
    ("EASE_IN_EXPO",     "Ease In (Exponencial)", "Aceleracion explosiva"),
    ("EASE_OUT_EXPO",    "Ease Out (Exponencial)","Explosion inicial con frenado suave"),
    ("EASE_IN_OUT_EXP",  "Ease In-Out Expo",      "Contraste extremo lento/rapido/lento"),
    ("EASE_IN_SINE",     "Ease In (Seno)",        "Arranque sinusoidal suave"),
    ("EASE_OUT_SINE",    "Ease Out (Seno)",       "Frenada sinusoidal. Muy organico"),
    ("EASE_IN_OUT_SIN",  "Ease In-Out Seno",      "Ideal para ciclos de caminar"),
    ("EASE_IN_CIRC",     "Ease In (Circular)",    "Arranque circular con aceleracion brusca"),
    ("EASE_OUT_CIRC",    "Ease Out (Circular)",   "Frenada circular suave"),
    ("EASE_IN_OUT_CIR",  "Ease In-Out Circular",  "Transicion circular simetrica"),
    # DINAMICAS Y FISICAS
    ("BOUNCE",           "Bounce",                "Rebote fisico al llegar al destino"),
    ("BOUNCE_IN",        "Bounce In",             "Rebotes antes de salir"),
    ("ELASTIC",          "Elastic Out",           "Resorte tenso: oscila y se asienta"),
    ("ELASTIC_IN",       "Elastic In",            "Tension de resorte al salir"),
    ("ELASTIC_IN_OUT",   "Elastic In-Out",        "Doble tension elastica"),
    ("SPRING",           "Spring (Resorte)",      "Resorte amortiguado fisico"),
    ("SPRING_HEAVY",     "Spring Pesado",         "Pocas oscilaciones, mayor amortiguacion"),
    ("SPRING_LIGHT",     "Spring Ligero",         "Muchas oscilaciones rapidas"),
    # PRINCIPIOS DISNEY
    ("ANTICIPATION",     "Anticipacion",          "Retroceso antes de avanzar"),
    ("ANTICIPATION_STR", "Anticipacion Fuerte",   "Anticipacion exagerada"),
    ("OVERSHOOT",        "Overshoot",             "Pasa el objetivo y regresa"),
    ("OVERSHOOT_STR",    "Overshoot Fuerte",      "Overshoot muy pronunciado"),
    ("FOLLOW_THROUGH",   "Follow Through",        "Sigue mas alla del objetivo y vuelve"),
    ("SQUASH_STRETCH",   "Squash and Stretch",    "Comprimir-estirar: arranque lento, explosion rapida"),
    # ESPECIALES
    ("STEPPED",          "Stepped (Sin interpol)","Sin interpolacion: pose directa"),
    ("HOLD_THEN_GO",     "Hold then Go",          "Mantiene el inicio, luego transicion rapida"),
    ("SLOW_IN_FAST_OUT", "Slow In / Fast Out",    "Precaucion al entrar, explosion al salir"),
    ("FAST_IN_SLOW_OUT", "Fast In / Slow Out",    "Impacto al entrar, reposo al terminar"),
    ("EASE_IN_BACK",     "Ease In Back",          "Retrocede ligeramente al arrancar"),
    ("EASE_OUT_BACK",    "Ease Out Back",         "Pasa el objetivo levemente antes de frenar"),
    ("EASE_IN_OUT_BCK",  "Ease In-Out Back",      "Anticipacion y overshoot combinados"),
]

# ─── BLOQUEADOR DE BONES (Paso 3) ─────────────────────────────
# Mapa bone_name -> nombre de atributo filter_* del segmento (Rat1AnimSegment).
# Si filter_* es True el bone esta BLOQUEADO (excluido de las poses del
# segmento; el recorrido base -- caminar/saltar -- sigue controlandolo).
BONE_FILTER_MAP = {
    'body1_1':      'filter_body1',
    'body2_1':      'filter_body2',
    'neck_1':       'filter_neck',
    'head_1':       'filter_head',
    'leftArm_1':    'filter_left_arm',
    'leftHand_1':   'filter_left_hand',
    'rightArm_1':   'filter_right_arm',
    'rightHand_1':  'filter_right_hand',
    'leftThigh_1':  'filter_left_thigh',
    'leftFoot_1':   'filter_left_foot',
    'rightThigh_1': 'filter_right_thigh',
    'rightFoot_1':  'filter_right_foot',
    'tail1_1':      'filter_tail1',
    'tail2_1':      'filter_tail2',
}
# Piernas bloqueadas por defecto (el recorrido base -- caminar/saltar --
# las controla), mismo criterio que Alfred con filter_right_leg/filter_left_leg.
BONE_FILTER_DEFAULT_TRUE = {
    'filter_left_thigh', 'filter_left_foot',
    'filter_right_thigh', 'filter_right_foot',
}
BONE_FILTER_ATTRS = list(BONE_FILTER_MAP.values())

# =============================================================================
# FILTROS ORGANICOS (Paso 3) -- port desde alfred_animation_studio
# (operators_anim.py: _apply_organic_filters). Mapeo de bones de Alfred
# (rig bipedo humano) a los bones equivalentes de rat_1 (rig cuadrupedo,
# ver rat_1.json / BONES_LISTA arriba). Kebyn pidio expresamente "solo
# Filtros Organicos" como primer subsistema a portar (2026-09-03) --
# Lanzar/Recoger/Mantener, Sistema de ojos y Oscilaciones de huesos
# quedan fuera de este paso.
#
#   Alfred (biped)                  rat_1 (cuadrupedo)      Justificacion
#   ----------------------------    -------------------     ------------------------------
#   Hips_alfred (raiz)           -> body1_1                 raiz del armature (level 0)
#   Spine_alfred, Spine1_alfred  -> body2_1                 rat_1 solo tiene 1 bone de
#                                                            columna (no hay Spine/Spine1
#                                                            separados)
#   Neck_alfred, face_alfred     -> neck_1, head_1           mismo rol (cuello + cabeza)
#   RightUpArm_alfred,           -> rightArm_1, leftArm_1    brazos delanteros
#   LeftUpArm_alfred
#   Rightelbow_alfred,           -> rightHand_1, leftHand_1  rat_1 no tiene bone de codo
#   Leftelbow_alfred                                        (leftArm_1/rightArm_1 van
#                                                            directo a la mano); el
#                                                            retardo de "codo" se aplica
#                                                            a la mano, que es el extremo
#                                                            equivalente en la cadena.
#   objeto raiz "alfred" (Empty) -> objeto raiz "rat_1"      Empty que se desplaza por
#                                                            el recorrido (ROOT_NAME)
# =============================================================================
ORGANIC_HIPS_BONE       = 'body1_1'                              # equiv. Hips_alfred
ORGANIC_SPINE_BONES     = ('body2_1',)                            # equiv. (Spine_alfred, Spine1_alfred)
ORGANIC_HEAD_BONES      = ('neck_1', 'head_1')                    # equiv. (Neck_alfred, face_alfred)
ORGANIC_SHOULDER_BONES  = (('rightArm_1', 0), ('leftArm_1', 17))  # equiv. (RightUpArm_alfred, LeftUpArm_alfred)
ORGANIC_SECONDARY_BONES = ('rightHand_1', 'leftHand_1')           # equiv. (Rightelbow_alfred, Leftelbow_alfred)
ORGANIC_ROOT_OBJECT     = ROOT_NAME                               # equiv. objeto "alfred"
