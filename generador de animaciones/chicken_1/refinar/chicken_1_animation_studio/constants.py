# -*- coding: utf-8 -*-
"""
constants.py — Chicken 1 Animation Studio v1.0
Rutas por defecto, listas de bones, tabla de interpolaciones.
Bones extraídos de chicken_1.json (bone_hierarchy, armature Armature_chicken_1, 34 bones, 28 animables).
"""

# ─── RUTAS POR DEFECTO ───────────────────────────────────────
DEFAULT_POSES_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\chicken_1\refinar\poses"
)
DEFAULT_ANIM_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\chicken_1\refinar\animaciones"
)
DEFAULT_HISTORIA_JSON = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\chicken_1\historia_chicken_1.json"
)
DEFAULT_CONFIG_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\chicken_1\refinar\configuraciones"
)

# ─── ARMATURE / ROOT ─────────────────────────────────────────
ARMATURE_NAME    = "Armature_chicken_1"
ROOT_OBJECT_NAME = "chicken_1"

# ─── BONES CHICKEN_1 ─────────────────────────────────────────
# 28 bones reales del armature (excluidos los _end_ y duplicados).
# Orden según bone_hierarchy del JSON outliner.
BONES_LISTA = [
    # Raíz y cadena central
    'Root_M_chicken_1',
    'Spine1_M_chicken_1',
    'Chest_M_chicken_1',
    'Neck_M_chicken_1',
    'Head_M_chicken_1',
    'Jaw_M_chicken_1',
    'Jaw_top_chicken_1',
    'Jaw_bot_chicken_1',
    # Ala derecha
    'Scapula_R_chicken_1',
    'Shoulder_R_chicken_1',
    'Elbow_R_chicken_1',
    # Ala izquierda
    'Scapula_L_chicken_1',
    'Shoulder_L_chicken_1',
    'Elbow_L_chicken_1',
    # Pata derecha
    'Hip_R_chicken_1',
    'Knee_R_chicken_1',
    'Ankle_R_chicken_1',
    # Pata izquierda
    'Hip_L_chicken_1',
    'Knee_L_chicken_1',
    'Ankle_L_chicken_1',
    # IK targets / helpers
    'Knee.Right_chicken_1',
    'Knee.Left_chicken_1',
    # Placeholders (no_bone_*)
    'no_bone_01_chicken_1',
    'no_bone_02_chicken_1',
    'no_bone_03_chicken_1',
    'no_bone_04_chicken_1',
    'no_bone_05_chicken_1',
    'no_bone_06_chicken_1',
]

# BONES_LISTA_FULL = igual (todos los 28 son el set completo)
BONES_LISTA_FULL = list(BONES_LISTA)

_BONE_DEFAULT = {"rot": (0.0, 0.0, 0.0), "loc": (0.0, 0.0, 0.0), "scale": (1.0, 1.0, 1.0)}

# ─── EXPRESIONES DE OJOS ─────────────────────────────────────
# chicken_1 no tiene mallas de ojo separadas; placeholders vacíos.
EYE_MESH_NAMES = []

EYE_BASE_TRANSFORMS = {}

EXPRESSION_PRESETS = [
    ("NEUTRAL",  "Neutral",   "Sin expresion"),
    ("FELIZ",    "Feliz",     "Curvas hacia arriba"),
    ("TRISTE",   "Triste",    "Curvas hacia abajo"),
    ("ENOJADO",  "Enojado",   "V invertida diagonal"),
    ("SOSPECHA", "Sospecha",  "Diagonal asimetrica"),
    ("CERRADO",  "Cerrado",   "Ojo completamente cerrado"),
    ("CANSADO",  "Cansado",   "Semicerrado, pesado"),
    ("SORPRESA", "Sorpresa",  "Apertura exagerada"),
]

# ─── TIPOS DE INTERPOLACION ──────────────────────────────────
INTERP_TYPE_ITEMS = [
    ("LINEAR",           "Linear",                "Velocidad constante, sin aceleracion"),
    ("SMOOTH",           "Smooth (Smoothstep)",   "Suave inicio y fin. Natural y fluido"),
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
    ("BOUNCE",           "Bounce",                "Rebote fisico al llegar al destino"),
    ("BOUNCE_IN",        "Bounce In",             "Rebotes antes de salir"),
    ("ELASTIC",          "Elastic Out",           "Resorte tenso: oscila y se asienta"),
    ("ELASTIC_IN",       "Elastic In",            "Tension de resorte al salir"),
    ("ELASTIC_IN_OUT",   "Elastic In-Out",        "Doble tension elastica"),
    ("SPRING",           "Spring (Resorte)",      "Resorte amortiguado fisico"),
    ("SPRING_HEAVY",     "Spring Pesado",         "Pocas oscilaciones, mayor amortiguacion"),
    ("SPRING_LIGHT",     "Spring Ligero",         "Muchas oscilaciones rapidas"),
    ("ANTICIPATION",     "Anticipacion",          "Retroceso antes de avanzar"),
    ("ANTICIPATION_STR", "Anticipacion Fuerte",   "Anticipacion exagerada"),
    ("OVERSHOOT",        "Overshoot",             "Pasa el objetivo y regresa"),
    ("OVERSHOOT_STR",    "Overshoot Fuerte",      "Overshoot muy pronunciado"),
    ("FOLLOW_THROUGH",   "Follow Through",        "Sigue mas alla del objetivo y vuelve"),
    ("SQUASH_STRETCH",   "Squash and Stretch",    "Comprimir-estirar"),
    ("STEPPED",          "Stepped (Sin interpol)","Sin interpolacion: pose directa"),
    ("HOLD_THEN_GO",     "Hold then Go",          "Mantiene el inicio, luego transicion rapida"),
    ("SLOW_IN_FAST_OUT", "Slow In / Fast Out",    "Precaucion al entrar, explosion al salir"),
    ("FAST_IN_SLOW_OUT", "Fast In / Slow Out",    "Impacto al entrar, reposo al terminar"),
    ("EASE_IN_BACK",     "Ease In Back",          "Retrocede ligeramente al arrancar"),
    ("EASE_OUT_BACK",    "Ease Out Back",         "Pasa el objetivo levemente antes de frenar"),
    ("EASE_IN_OUT_BCK",  "Ease In-Out Back",      "Anticipacion y overshoot combinados"),
]
