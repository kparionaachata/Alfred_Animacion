# -*- coding: utf-8 -*-
"""
constants.py — Alfred Animation Studio v1.8
Rutas por defecto, listas de bones, tabla de interpolaciones.
"""

# ─── RUTAS POR DEFECTO ───────────────────────────────────────
DEFAULT_POSES_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\alfred\refinar\poses"
)
DEFAULT_ANIM_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\alfred\refinar\animaciones"
)
DEFAULT_HISTORIA_JSON = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\alfred\historia_alfred.json"
)
DEFAULT_CONFIG_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\alfred\refinar\configuraciones"
)
# Carpeta "reglas" donde vive pose_library.json (libreria central de poses
# usada por el pipeline de generaciones: alfred_story_generator.py,
# alfred_filter.py, alfred_evolution_engine.py). Las calificaciones que se
# guardan desde la interfaz del addon se reflejan tambien aqui.
DEFAULT_REGLAS_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\alfred\refinar\reglas"
)
DEFAULT_POSE_LIBRARY_PATH = DEFAULT_REGLAS_DIR + "\\pose_library.json"

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

# ─── CALIFICACION DE POSES (1-10) ────────────────────────────
# 10 = la pose representa EXACTAMENTE lo que se pidio en el texto/historia.
# Umbrales para clasificar el estado de una pose segun el promedio de sus
# calificaciones acumuladas:
RATING_STATUS_EXCELENTE  = "EXCELENTE"   # promedio >= 8
RATING_STATUS_REGULAR    = "REGULAR"     # promedio >= 5 y < 8
RATING_STATUS_DESCARTADA = "DESCARTADA"  # promedio < 5
RATING_STATUS_NUEVA      = "NUEVA"       # sin calificaciones todavia

def calcular_estado_calificacion(promedio, cantidad):
    if cantidad <= 0:
        return RATING_STATUS_NUEVA
    if promedio >= 8.0:
        return RATING_STATUS_EXCELENTE
    if promedio >= 5.0:
        return RATING_STATUS_REGULAR
    return RATING_STATUS_DESCARTADA

# ─── BONES ───────────────────────────────────────────────────
BONES_LISTA = [
    'Hips_alfred',      'Spine_alfred',    'Spine1_alfred',  'Spine2_alfred',
    'Neck_alfred',      'face_alfred',
    'RightUpArm_alfred','Rightelbow_alfred',
    'LeftUpArm_alfred', 'Leftelbow_alfred',
    'RightUpLeg_alfred','Rightknee_alfred',
    'LeftUpLeg_alfred', 'Leftknee_alfred',
]
BONES_LISTA_FULL = [
    'Hips_alfred', 'Spine_alfred', 'Spine1_alfred', 'Spine2_alfred',
    'Neck_alfred', 'face_alfred',
    'RightUpArm_alfred', 'Rightelbow_alfred',
    'LeftUpArm_alfred',  'Leftelbow_alfred',
    'RightUpLeg_alfred', 'Rightknee_alfred',
    'LeftUpLeg_alfred',  'Leftknee_alfred',
    'no_bone_01', 'no_bone_02', 'no_bone_03', 'no_bone_04',
    'no_bone_05', 'no_bone_06', 'no_bone_07', 'no_bone_08',
]
_BONE_DEFAULT = {"rot": (0.0, 0.0, 0.0), "loc": (0.0, 0.0, 0.0), "scale": (1.0, 1.0, 1.0)}

# ─── EXPRESIONES DE OJOS ─────────────────────────────────────
EYE_MESH_NAMES    = ['ojo_izquierdo_alfred', 'ojo_derecho_alfred']

# Transforms reales de los ojos en el .blend de Alfred
# (loc, rot_euler, scale) — extraídos del outliner_data.json
EYE_BASE_TRANSFORMS = {
    "ojo_izquierdo_alfred": {
        "loc": ( 0.106646,  0.270456, 1.700815),
        "rot": (0.0, 0.0, 0.0),
        "sca": (1.555, 0.496018, 3.55),
    },
    "ojo_derecho_alfred": {
        "loc": (-0.1053,    0.256331, 1.700426),
        "rot": (0.0, 0.0, 0.0),
        "sca": (1.555, 0.496018, 3.55),
    },
}

# ─── FILTRO "REIR" (oscilacion vertical sincronizada de ambos ojos) ──────
# Kebyn, 2026-08-18: valores tomados de referencia directa en Blender --
# posicion base = EYE_BASE_TRANSFORMS de arriba (Z: 1.700815 / 1.700426);
# posicion alta = Z 1.73 en AMBAS mallas; posicion baja = Z 1.66 en AMBAS
# mallas. La oscilacion sube desde la base hasta la posicion alta, baja
# hasta la posicion baja, y vuelve a la base -- eso es UN ciclo completo
# ("de arriba hacia abajo"). Solo cambia Z; X/Y se mantienen en su valor
# base (EYE_BASE_TRANSFORMS) durante toda la oscilacion.
EYE_LAUGH_Z_HIGH = 1.73
EYE_LAUGH_Z_LOW  = 1.66

# ─── FILTRO "ENTENDIENDO" (parabola de ambos ojos, Izquierda/Derecha) ────
# Kebyn, 2026-08-18: valores tomados de captura directa en Blender de un
# gesto de "entendiendo" hacia la izquierda -- 3 posiciones en la
# secuencia: Base (Imagen 1, igual a EYE_BASE_TRANSFORMS), Apice (Imagen
# 2 -- Z mas alta, X levemente desplazada) y Destino final (Imagen 3 --
# Z de vuelta al nivel de la base, X mas desplazada que en el apice).
# Ambos ojos se mueven EN SIMULTANEO trazando una parabola X/Z entre las
# 3 posiciones. Los valores de abajo son DELTAS (respecto a la base de
# cada malla en EYE_BASE_TRANSFORMS), no posiciones absolutas.
#
# "Entendiendo Izquierda" usa estos deltas de X tal como fueron
# capturados (ambos ojos se desplazan hacia -X). "Entendiendo Derecha"
# es el espejo horizontal exacto -- mismos deltas de Z, deltas de X con
# el signo invertido -- para el gesto equivalente hacia el lado opuesto.
EYE_UNDERSTAND_APEX_DX = {
    "ojo_izquierdo_alfred": 0.07 - 0.106646,     # -0.036646
    "ojo_derecho_alfred":  -0.13 - (-0.1053),    # -0.024700
}
EYE_UNDERSTAND_APEX_DZ = {
    "ojo_izquierdo_alfred": 1.74 - 1.700815,     #  0.039185
    "ojo_derecho_alfred":   1.74 - 1.700426,     #  0.039574
}
EYE_UNDERSTAND_END_DX = {
    "ojo_izquierdo_alfred": 0.04 - 0.106646,     # -0.066646
    "ojo_derecho_alfred":  -0.16 - (-0.1053),    # -0.054700
}
EYE_UNDERSTAND_END_DZ = {
    "ojo_izquierdo_alfred": 0.0,
    "ojo_derecho_alfred":   0.0,
}

UNDERSTAND_DIRECTION_ITEMS = [
    ("IZQUIERDA", "Izquierda", "Ambos ojos glancean hacia la izquierda (deltas capturados tal cual)"),
    ("DERECHA",   "Derecha",   "Ambos ojos glancean hacia la derecha (espejo horizontal de Izquierda)"),
]

# ─── EXPRESIONES "SUENO" (Kebyn, 2026-09-27) ─────────────────────────────
# Sueno 1: "donde tiene los ojos cerrados las mallas de los ojos
# desaparecen" -- reusa el shape key compartido "Closed" (el mismo del
# parpadeo) llevado a 1.0 (cerrado total) + hide_viewport/hide_render en
# True mientras dura el tramo "sostenido" del intervalo. SUENO_1_HOLD_RATIO
# es la fraccion central del intervalo que se mantiene cerrado+invisible;
# el resto (repartido en entrada y salida) es la transicion cerrando/
# abriendo el parpado antes de ocultar la malla y despues de mostrarla.
SUENO_1_HOLD_RATIO = 0.5

# Sueno 2: "intenta abrir oscilantemente la malla del ojo derecho, despues
# del ojo izquierdo; al final se quedan ambas mallas a medias,
# semiabiertas". Ambas mallas arrancan cerradas (Closed=1.0). Durante la
# primera mitad del intervalo solo la malla derecha oscila intentando
# abrir (mientras la izquierda se mantiene cerrada); durante la segunda
# mitad, lo mismo pero con la malla izquierda. Al llegar a frame_end,
# ambas mallas quedan fijas en SUENO_2_END_CLOSED (0.5 = a medio camino
# entre abierto y cerrado, "semiabiertas").
SUENO_2_OSCILLATION_COUNT = 3      # intentos de apertura por cada ojo
SUENO_2_OSCILLATION_LOW   = 0.35   # valor de "Closed" en el punto mas abierto de cada intento
SUENO_2_END_CLOSED        = 0.5    # valor final compartido ("a medias semiabiertas")

EXPRESSION_PRESETS = [
    ("NEUTRAL",  "Neutral",   "Sin expresion"),
    ("FELIZ",    "Feliz",     "Curvas hacia arriba"),
    ("TRISTE",   "Triste",    "Curvas hacia abajo"),
    ("ENOJADO",  "Enojado",   "V invertida diagonal"),
    ("SOSPECHA", "Sospecha",  "Diagonal asimetrica"),
    ("CERRADO",  "Cerrado",   "Ojo completamente cerrado"),
    ("CANSADO",  "Cansado",   "Semicerrado, pesado"),
    ("SORPRESA", "Sorpresa",  "Apertura exagerada"),
    ("SUENO_1", "Sueño 1", "Ambos ojos cerrados e invisibles durante el intervalo"),
    ("SUENO_2", "Sueño 2", "Apertura oscilante: derecho, izquierdo; termina al 50%"),
]

# ─── TIPOS DE INTERPOLACION ──────────────────────────────────
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
