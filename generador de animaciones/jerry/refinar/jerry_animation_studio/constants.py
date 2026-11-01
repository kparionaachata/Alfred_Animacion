# -*- coding: utf-8 -*-
"""
constants.py — Jerry Animation Studio v2.0
Rutas por defecto, listas de bones, tabla de interpolaciones.
Personaje: Jerry (perro cuadrupedo, Dog_001_rig)
"""

# RUTAS POR DEFECTO
DEFAULT_POSES_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\jerry\refinar\poses" + "\\"
)
DEFAULT_ANIM_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\jerry\refinar\animaciones"
)
DEFAULT_HISTORIA_JSON = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\Informacion_Animacion\jerry\historia_jerry.json"
)
DEFAULT_CONFIG_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\jerry\refinar\configuraciones"
)
# Carpeta "reglas" donde vive jerry_pose_library.json (libreria central de
# poses usada por el pipeline de generaciones: jerry_story_generator.py,
# jerry_filter.py, jerry_evolution_engine.py). El nombre_legible que cada
# pose trae en '_semantica' se lee de aqui para mostrarlo en el panel al
# seleccionar un slot (ver leer_nombre_legible en pose_utils.py).
DEFAULT_REGLAS_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\jerry\refinar\reglas"
)
DEFAULT_POSE_LIBRARY_PATH = DEFAULT_REGLAS_DIR + "\\jerry_pose_library.json"

# ─── SISTEMA DE INTERACCION ENTRE PERSONAJES ─────────────────
# Carpetas donde se guardan los scripts .py de animaciones de
# interaccion -- una por personaje, porque cada uno reproduce su PROPIA
# mitad de la interaccion (ej. Alfred da la mano / Jerry choca los
# cinco) cuando sus dos recorridos coinciden en la misma coordenada.
# Ver path_recorder.py: tipo_segmento == 'INTERACTUAR',
# _point_is_meeting_point(), _interaccion_anim_items().
DEFAULT_INTERACTION_DIR_ALFRED = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\archivos de interaccion\alfred"
)
DEFAULT_INTERACTION_DIR_JERRY = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\archivos de interaccion\jerry"
)
# Distancia maxima (unidades Blender) entre una coordenada del recorrido
# propio y una coordenada del recorrido del otro personaje para
# considerar que ambos "se juntan" en ese punto (circulo rojo del
# diagrama de referencia).
INTERACTION_MEETING_TOLERANCE = 1.05   # la coordenada minima es 1 m: bloque adyacente (1.0) cuenta, diagonal (1.41) no
# Carpeta donde el editor de pose en vivo ("Editar pose..." / "Guardar
# cambios") exporta un .json por cada guardado, con la pose de huesos +
# transform del Root ('jerry') capturados en vivo desde la escena.
DEFAULT_POSE_CHANGES_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\jerry\refinar\cambios"
)

# Nombres reales en el .blend — usados por el editor de pose en vivo para
# ubicar el Root (Empty) y el Armature sin depender de strings sueltos
# repetidos por todo el codigo.
ROOT_NAME = "jerry"
ARM_NAME  = "Dog_001_rig"

# ── BONES del armature principal (Dog_001_rig) ───────────────────────────────
BONES_LISTA = [
    "spine_1", "spine_2", "spine_3", "spine_4",
    "spine_5", "spine_6", "spine_7",
    "scull_1", "scull",
    "front_shoulder.R", "front_thigh.R", "front_shin.R", "front_foot.R",
    "front_shoulder.L", "front_thigh.L", "front_shin.L", "front_foot.L",
    "shoulder.R", "thigh.R", "shin.R", "foot.R",
    "shoulder.L", "thigh.L", "shin.L", "foot.L",
    # ── Cejas (sejas) ──
    "sejas_1_jerry", "sejas_2_jerry",
]

# Lista completa — todos los bones animables
BONES_LISTA_FULL = [
    "spine_1", "spine_2", "spine_3", "spine_4",
    "spine_5", "spine_6", "spine_7",
    "scull_1", "scull",
    "ear.R", "ear.L",
    "jaw_top", "jaw_bot",
    "sombrero",
    "tail_1", "tail_2", "tail_3",
    "front_shoulder.R", "front_thigh.R", "front_shin.R",
    "front_foot.R",     "front_toe.R",
    "front_shoulder.L", "front_thigh.L", "front_shin.L",
    "front_foot.L",     "front_toe.L",
    "shoulder.R", "thigh.R", "shin.R", "foot.R", "toe.R",
    "shoulder.L", "thigh.L", "shin.L", "foot.L", "toe.L",
    "no_bone_01", "no_bone_02", "no_bone_03", "no_bone_04",
    # ── Cejas (sejas) — bones animables ──
    "sejas_1_jerry", "sejas_2_jerry",
]

_BONE_DEFAULT = {"rot": (0.0, 0.0, 0.0), "loc": (0.0, 0.0, 0.0), "scale": (1.0, 1.0, 1.0)}

# ── ARMATURES secundarios — Jerry no tiene armatures secundarios ─────────────
SECONDARY_ARMATURES = []

# ── OJOS y PUPILAS de Jerry ──────────────────────────────────────────────────
EYE_MESH_NAMES   = ["ojo_izquierdo_jerry", "ojo_derecho_jerry"]
PUPIL_MESH_NAMES = ["pupila_izquierda_jerry", "pupila_derecha_jerry"]

# Pares esclerotica → pupila (orden coincide con EYE_MESH_NAMES)
EYE_PUPIL_PAIRS = [
    ("ojo_izquierdo_jerry",  "pupila_izquierda_jerry"),
    ("ojo_derecho_jerry",    "pupila_derecha_jerry"),
]

# Limite de desplazamiento de las pupilas dentro de la esclerotica (metros)
PUPIL_OFFSET_LIMIT = 0.025

# Transforms reales extraidos del outliner_data.json de Jerry
EYE_BASE_TRANSFORMS = {
    "ojo_izquierdo_jerry": {
        "loc": (-0.105732,  0.705210, 0.699791),
        "rot": (0.0, -1.570796, -1.570796),
        "sca": (1.0, 1.0, 1.0),
    },
    "ojo_derecho_jerry": {
        "loc": ( 0.105796,  0.704775, 0.700123),
        "rot": (0.0, -1.570796, -1.570796),
        "sca": (1.0, 1.0, 1.0),
    },
}

# ── CEJAS (SEJAS) de Jerry ───────────────────────────────────────────────────
SEJAS_BONE_NAMES = ["sejas_1_jerry", "sejas_2_jerry"]
SEJAS_MESH_NAMES = ["sejas_1_jerry", "sejas_2_jerry"]

# Transforms reales de las mallas de cejas
SEJAS_BASE_TRANSFORMS = {
    "sejas_1_jerry": {
        "loc": ( 0.104741,  0.711868, 0.794984),
        "rot": (-1.525217, -1.570796, 0.0),
        "sca": (1.0, 1.0, 1.0),
    },
    "sejas_2_jerry": {
        "loc": (-0.141106,  0.711868, 0.794984),
        "rot": (-1.525217, -1.570796, 0.0),
        "sca": (1.0, 1.0, 1.0),
    },
}

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

# ── TIPOS DE INTERPOLACION ───────────────────────────────────────────────────
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
    ("SQUASH_STRETCH",   "Squash and Stretch",    "Comprimir-estirar: arranque lento, explosion rapida"),
    ("STEPPED",          "Stepped (Sin interpol)","Sin interpolacion: pose directa"),
    ("HOLD_THEN_GO",     "Hold then Go",          "Mantiene el inicio, luego transicion rapida"),
    ("SLOW_IN_FAST_OUT", "Slow In / Fast Out",    "Precaucion al entrar, explosion al salir"),
    ("FAST_IN_SLOW_OUT", "Fast In / Slow Out",    "Impacto al entrar, reposo al terminar"),
    ("EASE_IN_BACK",     "Ease In Back",          "Retrocede ligeramente al arrancar"),
    ("EASE_OUT_BACK",    "Ease Out Back",         "Pasa el objetivo levemente antes de frenar"),
    ("EASE_IN_OUT_BCK",  "Ease In-Out Back",      "Anticipacion y overshoot combinados"),
]
