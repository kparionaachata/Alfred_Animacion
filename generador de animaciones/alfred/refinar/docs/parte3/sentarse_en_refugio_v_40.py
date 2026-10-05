"""Parte 3 - Alfred y Jerry se SIENTAN a descansar dentro del refugio (pedido de Kebyn). Se ejecuta DENTRO de Blender (exec) sobre base_parte_3.blend (f1 = estado del f2150 de la parte 2).
Layout (interior 2x2 del refugio, x -97..-95, y -110..-108; la antorcha esta en el centro (-96,-109)):
  Alfred: se gira al oeste, se agacha y se sienta con la espalda en el muro este (-95.3,-108.3) con las piernas estiradas hacia el oeste (muro norte a su derecha); respira, mira la antorcha, se le cierra la cabeza de sueno.
  Jerry : camina al rincon suroeste (-96.55,-109.45), se gira hacia la antorcha (NE) y se sienta como perro (grupa abajo, pecho arriba, patas traseras plegadas); respira, mueve la cola y la oreja, bosteza y apoya la cabeza.
Medidas en el rig: piernas de Alfred rectas (UpLeg X -90, rodilla 0) con Hips Y local -0.69 apoyan el cuerpo en el suelo (z 14.0); Jerry: spine_6 X +32, root z -0.15.
Idempotente: borra las acciones previas de Alfred/Jerry antes de keyframear. Rango de escena 1..N.
"""
import bpy, math
from mathutils import Euler, Matrix, Quaternion, Vector
D = math.radians
N = 650
STEP = 2
sc = bpy.context.scene


def ss(u):
    u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)


def wp_eval(wps, k):
    """waypoints [(frame, tuple)] -> valor con smoothstep entre ellos."""
    if k <= wps[0][0]: return wps[0][1]
    if k >= wps[-1][0]: return wps[-1][1]
    i = next(q for q in range(1, len(wps)) if wps[q][0] >= k); f0, f1 = wps[i - 1][0], wps[i][0]; u = ss((k - f0) / float(f1 - f0))
    return tuple(a + (b - a) * u for a, b in zip(wps[i - 1][1], wps[i][1]))


def clear(ob):
    if ob.animation_data:
        ob.animation_data.action = None
        for t in list(ob.animation_data.nla_tracks): ob.animation_data.nla_tracks.remove(t)


# ----------------------------------------------------------------------------------------------- ALFRED
# REFERENCIA del usuario: `codigos de animacion/alfred/sentado_cansado_alfred.py` (144 f): se sienta con las piernas ESTIRADAS al frente (UpLeg X +88: en este rig Alfred mira a +Y local, no a -Y),
# brazo derecho apoyado, izquierdo colgando, cabeza que cae cansada. Sus canales (rotaciones de todos los huesos + ubicacion de Hips y de los dos UpArm) se vuelcan tal cual en [REF0, REF0+143];
# antes se encadena desde la pose de pie con un fundido; despues se mantiene la ultima pose con los filtros organicos (respiracion, ruido, mirada a la antorcha, cabeza que cae y ojos que se cierran).
import json, os
REFJ = json.load(open(os.path.join(os.path.dirname(bpy.data.filepath) if False else r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\parte3", "ref_sentarse_cansado_alfred.json"), encoding="utf-8"))
A = next(o for o in bpy.data.objects if o.type == "ARMATURE" and "Hips_alfred" in o.pose.bones); O = A.parent; PA = A.pose.bones            # el rig de Alfred y su root cambian de nombre segun la herramienta (a / armature / Armature ; Object / alfred): se buscan por el hueso Hips_alfred            # el rig y su root se llaman a / Object o armature / alfred segun la herramienta de poses; PA = A.pose.bones
TOOLS = ("wooden_pickaxe", "wooden_axe", "stone_axe")
_bp = A.pose.bones["Spine1_alfred"]
for tn in TOOLS:                                                                    # una sola vez: la matriz de cada herramienta respecto al hueso Spine1 (queda guardada en la propiedad "rel_spine1"); se desparenta para animarla
    t_ = bpy.data.objects[tn]
    if t_.parent is not None:
        t_["rel_spine1"] = [v for row in ((A.matrix_world @ _bp.matrix).inverted() @ t_.matrix_world) for v in row]
        mw_ = t_.matrix_world.copy(); t_.parent = None; t_.matrix_world = mw_
    if t_.animation_data: t_.animation_data_clear()
    t_.rotation_mode = 'QUATERNION'
for ob in (O, A): clear(ob)
for b in PA: b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
TH = -4 * math.pi                                                                   # giro acumulado de la parte 2 (equivale a 0)
REF0 = 30                                                                           # frame de la escena donde empieza la referencia (antes 60: la aproximacion f1-29 dura la mitad)
SLOW = 0.16                                                                         # la referencia llega al suelo en su frame 95 -> x0.16 = 15 frames desde que empieza a sentarse (toda la animacion f1-45 = la mitad de los 90 f anteriores; pedido de Kebyn)
REFN = REFJ["frames"]; REFEND = int(REF0 + (REFN - 1) * SLOW); T0 = 150                      # REFEND = f105: termina de sentarse; T0 = f150 CONSERVA los frames de la mirada a la antorcha y del sueno (antes REFEND valia 150)
STAND = {b: (0.0, 0.0, 0.0) for b in REFJ["rot"]}; STAND["RightUpArm_alfred"] = STAND["LeftUpArm_alfred"] = (math.radians(90), 0.0, 0.0)
def root_at(k):
    """f1-59: UN solo movimiento de aproximacion al sitio: el cuerpo gira (+90 = mira al oeste) y se desplaza con la misma curva suave (arranca y llega con velocidad 0), con un pequeno rebase del giro que se asienta justo antes de f60."""
    u = ss((k - 3) / 23.0)
    yaw = 90.0 * u + 2.0 * math.sin(math.pi * min(max((k - 20) / 9.5, 0.0), 1.0)) ** 2
    x = -95.5 + 0.2 * u
    if k >= KN0: w = kn_w(k); x = x * (1 - w) + KN_X * w                                                  # al ponerse de rodillas se adelanta 30 cm (las espinillas no llegan al muro este)
    return (x, -108.5 - 0.09 * u, 14.0, yaw)    # Alfred mira a +Y local: yaw +90 => mira al oeste (piernas hacia el oeste). Y final -108.59 (antes -108.3): se sienta 0.29 m mas hacia su IZQUIERDA (sur) para que el brazo derecho no atraviese el muro norte (cara interior y=-108.0)


def ref_rot(b, t):
    """rotacion de la referencia en el instante t (frames de referencia, fraccionario): interpolacion lineal entre sus muestras."""
    t = min(max(t, 0.0), REFN - 1.0); i = int(t); j = min(i + 1, REFN - 1); u = t - i; a = REFJ["rot"][b][i]; c = REFJ["rot"][b][j]
    return [a[q] + (c[q] - a[q]) * u for q in range(3)]


def ref_loc(arr, t):
    t = min(max(t, 0.0), REFN - 1.0); i = int(t); j = min(i + 1, REFN - 1); u = t - i
    return [arr[i][q] + (arr[j][q] - arr[i][q]) * u for q in range(3)]


def breathe(k, a0, per, ph=0.0):
    return a0 * math.sin(2 * math.pi * k / per + ph)


def noise(k, seed, a):
    return a * (0.55 * math.sin(k * 0.071 + seed) + 0.3 * math.sin(k * 0.137 + seed * 2.3) + 0.15 * math.sin(k * 0.293 + seed * 3.7))


def blink_curve(k):
    for f0 in (14, 70, 112, 150, 158, 196, 236, 300, 352, 360, 392, 440, 478, 512, 545, 583, 621):
        d = k - f0
        if 0 <= d <= 6: return math.sin(math.pi * d / 6.0)
    return 0.0


# LANZAR LAS HERRAMIENTAS (pedido de Kebyn): mientras Jerry se acomoda, Alfred se inclina hacia delante, lleva la mano a la espalda, arranca el pico y las hachas que lleva clavadas y las lanza hacia delante (oeste)
# con Elastic In-Out en el tiron. v18 (correccion de Kebyn: "hace giros de 360 grados con los brazos"): el gesto de AGARRE es el calibrado del sistema Lanzar/Recoger/Mantener de alfred_animation_studio
# (`PRE_THROW_REACH_BACK_POSE`, brazo derecho hacia la espalda; el izquierdo es su espejo en X) con un ajuste de <= 60 grados para que la mano toque cada herramienta. Todas las transiciones del brazo se
# hacen con CUATERNIONES (camino mas corto: reposo -> espalda ~90 grados, espalda -> suelta ~165 grados, nunca vueltas completas) y los Euler se desenrollan frame a frame (compatibles con el anterior).
LEAN = (("Spine_alfred", 24.0), ("Spine1_alfred", 18.0), ("Spine2_alfred", 10.0))                      # inclinacion hacia delante mientras lanza (X positivo = adelante)
LEAN_UP, LEAN_TOP, LEAN_DOWN = 190, 204, 270
STUDIO_U, STUDIO_E, STUDIO_LOC = (28.5284, 198.1061, 62.0369), (-16.873, 18.6165, -107.9791), (0.006603, 0.096746, -0.086079)      # RightUpArm / Rightelbow del gesto "hacia la espalda" del estudio
THROWS = [("wooden_pickaxe", "Right", 206, (-19, 0, -42, 0)), ("wooden_axe", "Left", 224, (-2, 0, 57, -11)), ("stone_axe", "Right", 242, (-26, 0, -48, 0))]   # deltas del agarre (X, Y, Z del hombro y X del codo, grados) resueltos contra la cara trasera de cada herramienta
REL_Q = {"Right": ((0.13206, -0.67532, -0.68619, 0.23592), (0.63634, 0.77141, 0.0, 0.0)), "Left": ((0.13706, -0.65673, 0.63297, -0.38636), (0.63742, 0.77051, 0.0, 0.0))}   # (hombro, codo) al soltar: mano delante y arriba (cuaterniones w, x, y, z)
PILE = {"wooden_pickaxe": ((-96.64, -108.78), 8.0), "wooden_axe": ((-96.60, -108.76), 345.0), "stone_axe": ((-96.62, -108.77), 30.0)}   # montoncito delante de sus pies (oeste), entre la antorcha y el muro norte: es la parte del suelo que ve Camara_Conversacion
REACH_D, HOLD_D, SWING_D, BACK_D, FLY_D = 9, 2, 12, 12, 10
# MANOS EN LA NUCA (pedido de Kebyn): Alfred responde a Jerry ("Que borrio quieres?", voz f358) mientras se acomoda con las dos manos detras de la cabeza, apoyado contra el muro este. Sube los brazos f340-364 (camino mas corto en
# cuaternios, desde el reposo de cada frame), se acomoda f364-392 (cabeceo contra el muro que se amortigua) y mantiene las manos hasta el final. Poses resueltas numericamente en Blender (mano a 5-6 cm de la pared, x <= -95.04;
# codos a >= 0.33 m del eje del cuerpo, fuera y adelante; error de la mano 0.8 cm a 7 cm; el codo derecho a y <= -108.27 para que la malla no toque el muro norte): (cuat. hombro, cuat. codo) absolutos.
NUCA0, NUCA_D = 340, 24
NUCA_Q = {"Right": ((0.08303, -0.54445, -0.73441, 0.39665), (0.3166, 0.94856, 0.0, 0.0)), "Left": ((0.63915, -0.60283, -0.134, 0.4584), (0.40827, -0.91286, 0.0, 0.0))}


def nuca_layer(k, rot):
    """tronco y cabeza al apoyarse en el muro con las manos en la nuca (los brazos van en `arm_state`)."""
    w = ss((k - NUCA0) / float(NUCA_D))
    aco = math.exp(-max(0.0, k - (NUCA0 + NUCA_D)) / 11.0) * math.sin(2 * math.pi * max(0.0, k - (NUCA0 + NUCA_D)) / 15.0) * ss((k - NUCA0 - NUCA_D + 2) / 2.0)          # se acomoda: 2 vaivenes que se apagan
    rot["Spine2_alfred"][0] += D(-3.0 * w + 3.0 * aco); rot["Spine_alfred"][0] += D(-1.5 * w + 1.5 * aco); rot["Spine1_alfred"][0] += D(-1.0 * w)
    rot["Neck_alfred"][0] += D(-14.0 * ss((k - NUCA0 - 6) / 22.0) + 2.5 * aco)                              # la cabeza se echa atras contra las manos / el muro (quita la caida de sueno)
    rot["Neck_alfred"][1] += D(20.0 * ss((k - NUCA0 - 4) / 14.0) * (1 - ss((k - NUCA0 - 74) / 16.0)))        # mira a Jerry (a su izquierda) mientras le contesta
THROW_RANGE = (LEAN_UP - 4, THROWS[-1][2] + HOLD_D + SWING_D + FLY_D + 8)
# DESPEJAR EL SITIO (pedido de Kebyn): de pronto Alfred dice "Espera, tengo una idea." (audio `espera_tengo_una_idea.wav`, 36 f, voz desde CLR_V) y, mientras lo dice, empieza a barrer con la mano izquierda las herramientas que
# lanzo delante de el (stone_axe, wooden_axe, wooden_pickaxe) para despejar ese sitio: se inclina CLR_T grados sobre la cadera y da tres manotazos (f446-451, 459-464, 472-477) de la pila hacia donde duerme Jerry (sur). Cada
# herramienta sale disparada en el instante de su manotazo, sube por encima de Jerry, REBOTA EN EL MURO SUR y cae sobre su lomo, donde se queda (sube y baja con su respiracion). Poses (cuaterniones absolutos hombro / codo de la mano
# izquierda) resueltas numericamente en Blender: R = mano al norte de la pila (-96.40, -108.55, 14.33), S = mano al sur (-96.45, -109.19, 14.30), con la inclinacion CLR_T.
CLR_V = 430
# BRAZOS CAIDOS (correccion de Kebyn): desde f434 las manos dejan la nuca y los brazos pasan a la pose de la imagen de referencia (colgando a los lados, codos algo doblados hacia delante, manos junto a las caderas, sin tocar a Jerry
# ni el muro); desde ahi hacen el barrido, la espalda y la mesa. Resuelto con ik_brazos.py (error de la mano < 1 mm; muneca a z 14.1, codos fuera del torso): (cuat. hombro, cuat. codo) absolutos.
SIT_Q = {"Left": ((0.15481, 0.72657, -0.66836, -0.03777), (0.69446, -0.71953, 0.00000, 0.00000)), "Right": ((0.03304, 0.72474, 0.68737, 0.03441), (0.62592, -0.77989, 0.00000, 0.00000))}
SIT_T = 434, 440
CLR_SW = 0.55
CLR_T = 48.1; CLR_LEANW = (("Spine_alfred", 0.32), ("Spine1_alfred", 0.34), ("Spine2_alfred", 0.34))
CLR_Q = {"R": ((0.52357, -0.12749, -0.11319, 0.83475), (0.99882, -0.04848, 0.0, 0.0)), "S": ((0.78908, -0.32326, 0.18792, 0.48738), (0.99412, -0.10828, 0.0, 0.0))}
CLR_KEYS = [(434, "N"), (440, "SIT"), (444, "R"), (446, "R"), (451, "S"), (452, "S"), (457, "R"), (459, "R"), (464, "S"), (465, "S"), (470, "R"), (472, "R"), (477, "S"), (478, "S"), (494, "SIT"), (506, "SIT")]
CLR_LEAN = [(436, (0.0,)), (446, (1.0,)), (478, (1.0,)), (498, (0.0,))]
CLR_HIT = {"stone_axe": 450, "wooden_axe": 463, "wooden_pickaxe": 476}                                   # frame del manotazo que la lanza
CLR_WALL = {"stone_axe": -96.35, "wooden_axe": -96.05, "wooden_pickaxe": -95.75}                           # x donde choca con el muro sur
CLR_JERRY = {"stone_axe": (-96.30, -109.45, 70.0), "wooden_axe": (-96.00, -109.45, 20.0), "wooden_pickaxe": (-95.75, -109.45, 100.0)}      # (x, y, giro) donde cae sobre Jerry
CLR_T1, CLR_T2, CLR_WALL_Y, CLR_WALL_Z = 9, 8, -109.72, 15.0                                                 # frames hasta el muro, frames del muro a Jerry, centro de la herramienta al chocar
CLR_RANGE = (CLR_KEYS[0][0] - 4, max(CLR_HIT.values()) + CLR_T1 + CLR_T2 + 6)


def clr_lean(k):
    return wp_eval(CLR_LEAN, k)[0]


def clr_pose(k):
    """(cuat. hombro, cuat. codo) de la mano izquierda durante los manotazos; None fuera de ese tramo."""
    if k < CLR_KEYS[0][0] or k >= CLR_KEYS[-1][0]: return None
    Q = dict(CLR_Q); Q["N"] = NUCA_Q["Left"]; Q["SIT"] = SIT_Q["Left"]
    Q["S"] = tuple(_qpow(Quaternion(CLR_Q["R"][i]), Quaternion(CLR_Q["S"][i]), CLR_SW) for i in (0, 1))                   # el manotazo no llega al final de la pose S (solo CLR_SW de camino): la mano no se mete en el pelaje de Jerry
    for (f0, a), (f1, b) in zip(CLR_KEYS[:-1], CLR_KEYS[1:]):
        if f0 <= k < f1:
            x = (k - f0) / float(f1 - f0); u = (0.3 * ela(x) + 0.7 * ss(x)) if (a, b) == ("R", "S") else ss(x)       # el manotazo R -> S: Elastic In-Out mezclado al 30 %
            qa = [Quaternion(q) for q in Q[a]]; qb = [Quaternion(q) for q in Q[b]]
            return _qpow(qa[0], qb[0], u), _qpow(qa[1], qb[1], u)

# MESA DE CRAFTEO (pedido de Kebyn): despues de despejar el suelo Alfred se pone DE RODILLAS, saca de su espalda una mesa de crafteo (`bloques_dinamicos/mesa_de_crafteo_1.blend`, 1 m, origen en la base) y la coloca
# en el sitio que despejo (esquina noroeste de la sala: centro (-96.565, -108.5), cara oeste dentro del muro, cara este a 6 cm de la antorcha y a 11 cm del lomo de Jerry).
# Rodillas: muslos verticales (UpLeg X 0), espinillas planas hacia el este (knee X -90, la punta del pie queda a x -95.11, el muro este esta en -95.0) con el root en x -95.55; Hips Y local -0.40 apoya las rodillas en el suelo
# (13.988 medido contra las mallas de las piernas). Se pasa de sentado a de rodillas en KN0..KN1 (el suelo se corrige por frame con `KZ`: las piernas nunca lo atraviesan). Las poses de brazos (hombro / codo, cuaterniones
# absolutos) estan resueltas con `ik_brazos.py` (cinematica de matrices verificada contra la pose de Blender): REST = manos colgando junto a los muslos, BACK = manos detras de la espalda, HI / MID / LO = manos agarrando la cara
# este de la mesa a 3 alturas con el tronco inclinado 10 / 19 / 28 grados (los numeros de la tupla). Error de la mano <= 6 cm.
KN0, KN1 = 502, 516                                                                    # de rodillas: 14 frames (f502-516)
KN_LEG = (0.0, -90.0); KN_HIPY = -0.40; KN_X = -95.55
KN_LEAN = [(KN0, (0.0,)), (509, (26.0,)), (KN1, (0.0,)), (527, (0.0,)), (533, (10.0,)), (536, (19.0,)), (538, (28.0,)), (540, (28.0,)), (543, (20.0,)), (N, (20.0,))]
KN_NECK = [(KN0, (0.0,)), (524, (0.0,)), (533, (10.0,)), (536, (18.0,)), (541, (14.0,)), (548, (0.0,)), (N, (0.0,))]
MESA_PATH = r"C:\Users\user\Desktop\Alfred_Animacion\bloques_dinamicos\mesa_de_crafteo_1.blend"
MESA_Q = {
    "TOP": (20, ((0.50234, 0.27152, 0.46489, 0.67662), (0.52007, -0.85413, 0.00000, 0.00000)), ((0.49558, 0.44918, -0.50998, -0.54088), (0.38387, -0.92339, 0.00000, 0.00000))),
    "REST": (0, ((0.38337, 0.91465, 0.09878, 0.08172), (0.81042, -0.58585, 0.00000, 0.00000)), ((0.26404, 0.94593, -0.16503, -0.09086), (0.71122, -0.70296, 0.00000, 0.00000))),
    "BACK": (0, ((0.48296, 0.83652, 0.12941, -0.22414), (0.86603, -0.50000, 0.00000, 0.00000)), ((0.49240, 0.85287, -0.08682, 0.15038), (0.90631, -0.42262, 0.00000, 0.00000))),
    "HI": (10, ((0.32349, 0.38855, 0.66484, 0.54988), (0.35089, -0.93642, 0.00000, 0.00000)), ((0.26757, -0.71929, 0.32035, 0.55534), (0.21901, -0.97572, 0.00000, 0.00000))),
    "MID": (19, ((0.26803, 0.47115, 0.68365, 0.48868), (0.44520, -0.89543, 0.00000, 0.00000)), ((0.17966, 0.66804, -0.65736, -0.29888), (0.30065, -0.95374, 0.00000, 0.00000))),
    "LO": (28, ((0.36931, 0.38838, 0.65448, 0.53332), (0.66113, -0.75027, 0.00000, 0.00000)), ((0.30430, 0.63476, -0.57376, -0.41868), (0.54069, -0.84122, 0.00000, 0.00000))),
}
TBK = [(506, "SIT"), (513, "REST"), (524, "REST"), (527, "BACK"), (528, "BACK"), (533, "HI"), (534, "HI"), (536, "MID"), (538, "LO"), (539, "LO"), (543, "TOP"), (N, "TOP")]   # brazos caidos -> rectos f506-513 (7 f); espera f516-524 (8 f); mesa f524-540 (16 f)
MESA_T = {"aparece": 527, "mano": 533, "baja0": 534, "suelo": 538, "fin": 540}
MESA_P0 = Vector((-95.40, -108.59, 14.75)); MESA_PC = Vector((-95.70, -108.59, 15.55)); MESA_S = 0.9                                                                                                  # escala de la mesa: 0.9 m cabe en la esquina sin tocar el muro oeste (x -97.0), el norte (y -108.0) ni la antorcha
MESA_H = Vector((-96.53, -108.47, 14.55)); MESA_F = Vector((-96.53, -108.47, 13.9946))


def kn_w(k):
    return ss((k - KN0) / float(KN1 - KN0))


# POSES DE LOS BRAZOS DE LA MESA, SIN GIRO Z (orden de Kebyn: "no rotes en Z"): (X, Y, Z) en grados de LeftUpArm / RightUpArm y X del codo. Hombro con X 90 (brazo colgando) y el balanceo atras / adelante en Y
# (verificado con la cinematica del rig: con X 90, Y positivo en el izquierdo / negativo en el derecho lleva la mano hacia atras (+x); el signo contrario, hacia delante). BACK = brazos rectos hacia atras (munecas a x -95.14);
# HI / MID / LO / TOP = brazos rectos hacia delante con las manos encima de la tapa de la mesa mientras baja (la altura de las munecas sigue la tapa: z 15.49, 15.2, 14.94, 14.94; resueltas con ik_brazos / fk).
MESA_E = {"REST": ((90, 0, 0), 0, (90, 0, 0), 0), "BACK": ((90, 22, 0), 0, (90, -22, 0), 0), "HI": ((90, -128.5, 0), 0, (90, 128.0, 0), 0), "MID": ((90, -120.0, 0), 0, (90, 121.0, 0), 0),
          "LO": ((90, -114.5, 0), 0, (90, 117.0, 0), 0), "TOP": ((90, -106.0, 0), 0, (90, 108.5, 0), 0)}
_EU = {}


def _eu_key(side):
    """Euler XYZ (rad) del hombro y X del codo de cada pose (MESA_E; SIT sale de SIT_Q en la rama de menor torsion Z), con los angulos a la vuelta mas cercana a la pose anterior."""
    if side in _EU: return _EU[side]
    si = 0 if side == "Left" else 2; out = {}; e = Quaternion(SIT_Q[side][0]).to_euler('XYZ'); c = (e.x, e.y, e.z); c2 = (e.x + math.pi, math.pi - e.y, e.z + math.pi)
    cc = [[((a_ + math.pi) % (2 * math.pi)) - math.pi for a_ in q] for q in (c, c2)]; cc = min(cc, key=lambda q: 3 * abs(q[2]) + 0.1 * abs(q[0]))
    xe = 2 * math.atan2(Quaternion(SIT_Q[side][1]).x, Quaternion(SIT_Q[side][1]).w); out["SIT"] = (cc, xe)
    for nm, v in MESA_E.items(): out[nm] = ([math.radians(a_) for a_ in v[si]], math.radians(v[si + 1]))
    _EU[side] = out; return out


def tab_eul(side, k, lru):
    """([rx, ry, rz] del hombro, rx del codo, ubicacion): los angulos Euler de UpArm / elbow entre las poses MESA_Q, interpolados canal por canal (los keyframes quedan limpios; la espalda y el tiron al frente llevan Elastic In-Out al 30 %%)."""
    EU = _eu_key(side); locg = (STUDIO_LOC[0] * (-1 if side == "Left" else 1), STUDIO_LOC[1], STUDIO_LOC[2]); wl = ss((k - TBK[0][0]) / 10.0); lc = tuple(l * (1 - wl) + g * wl for l, g in zip(lru, locg))
    for (f0, a), (f1, b) in zip(TBK[:-1], TBK[1:]):
        if f0 <= k < f1:
            x = (k - f0) / float(f1 - f0); u = (0.3 * ela(x) + 0.7 * ss(x)) if (a, b) in (("REST", "BACK"), ("BACK", "HI")) else ss(x)
            A_, B_ = EU[a], EU[b]; return [A_[0][q] + (B_[0][q] - A_[0][q]) * u for q in range(3)], A_[1] + (B_[1] - A_[1]) * u, lc
    E_ = EU[TBK[-1][1]]; return list(E_[0]), E_[1], lc


def tab_arm(side, k, lru):
    e, x, lc = tab_eul(side, k, lru); return Euler(e, 'XYZ').to_quaternion(), Quaternion((math.cos(x / 2), math.sin(x / 2), 0.0, 0.0)), lc


def kn_layer(k, rot, loc):
    """sentado -> de rodillas: mezcla todos los huesos que no son los brazos hacia la pose de rodillas (piernas, tronco recto) y suma la inclinacion / la mirada de cada momento."""
    if k < KN0 - 1: return
    w = kn_w(k)
    for b in rot:
        if "UpArm" in b or "elbow" in b: continue
        t = (0.0, 0.0, 0.0)
        if b.endswith("UpLeg_alfred"): t = (D(KN_LEG[0]), 0.0, 0.0)
        elif b.endswith("knee_alfred"): t = (D(KN_LEG[1]), 0.0, 0.0)
        rot[b] = [rot[b][j] * (1 - w) + t[j] * w for j in range(3)]
    h = loc.get("Hips_alfred", [0.0, 0.0, 0.0]); loc["Hips_alfred"] = [h[0] * (1 - w), h[1] * (1 - w) + KN_HIPY * w, h[2] * (1 - w)]
    ln = wp_eval(KN_LEAN, k)[0]
    for b, wg in CLR_LEANW: rot[b][0] += D(ln * wg)
    rot["Neck_alfred"][0] += D(-0.15 * ln + wp_eval(KN_NECK, k)[0])


def mesa_pose(k):
    """(posicion del origen, euler, escala) de la mesa en el frame k."""
    T = MESA_T
    if k < T["aparece"]: return MESA_P0.copy(), (0.0, 0.0, 0.0), 0.001
    if k < T["mano"]:
        u = (k - T["aparece"]) / float(T["mano"] - T["aparece"]); e = ss(u); a = MESA_P0 * (1 - e) ** 2 + MESA_PC * 2 * e * (1 - e) + MESA_H * e * e
        return a, (0.0, D(70.0) * (1 - e), D(80.0) * (1 - e)), max(0.001, u ** 3 * MESA_S)
    if k < T["baja0"]: return MESA_H.copy(), (0.0, 0.0, 0.0), MESA_S
    if k < T["suelo"]:
        u = ss((k - T["baja0"]) / float(T["suelo"] - T["baja0"])); a = MESA_H.lerp(MESA_F, u); return a, (0.0, 0.0, 0.0), MESA_S
    d = k - T["suelo"]; sq = math.exp(-d / 2.0) * math.sin(math.pi * d / 3.0) * 0.04 if d < 8 else 0.0                                                         # al tocar el suelo se asienta (rebote corto)
    return MESA_F.copy(), (0.0, 0.0, 0.0), MESA_S * (1.0 - sq)


def ela(u):
    """Elastic In-Out (misma formula que el add-on y la parte 2)."""
    if u <= 0.0: return 0.0
    if u >= 1.0: return 1.0
    c5 = 2 * math.pi / 4.5
    if u < 0.5: return -(2 ** (20 * u - 10) * math.sin((20 * u - 11.125) * c5)) / 2
    return (2 ** (-20 * u + 10) * math.sin((20 * u - 11.125) * c5)) / 2 + 1


def lean_w(k):
    return ss((k - LEAN_UP) / float(LEAN_TOP - LEAN_UP)) * (1 - ss((k - LEAN_DOWN) / 12.0))


_SX = Matrix.Diagonal((-1, 1, 1))
_E = lambda *d: Euler([D(x) for x in d], 'XYZ').to_matrix()
ARM_TAB = {}


def _goal(side, p):
    """(cuaternion hombro, cuaternion codo) del agarre: gesto del estudio (+ espejo en X para el izquierdo) compuesto con el ajuste p."""
    ru, re = _E(*STUDIO_U), _E(*STUDIO_E)
    if side == "Left": ru, re = _SX @ ru @ _SX, _SX @ re @ _SX
    return (ru @ _E(p[0], p[1], p[2])).to_quaternion(), (re @ _E(p[3], 0, 0)).to_quaternion()


def _qpow(q0, q1, u):
    """q0 -> q1 por el camino mas corto, con u fuera de [0, 1] permitido (Elastic In-Out sobrepasa)."""
    d = q0.inverted() @ q1
    if d.w < 0: d = -d
    ax, an = d.to_axis_angle()
    return q0 @ Quaternion(ax, an * u) if an > 1e-9 else q0.copy()


def arm_state(side, k, qru, qre, lru):
    """(cuat. hombro, cuat. codo, ubicacion del hombro) del brazo `side` en el frame k durante los lanzamientos; None si no participa. qru / qre = el reposo en k."""
    locg = (STUDIO_LOC[0] * (-1 if side == "Left" else 1), STUDIO_LOC[1], STUDIO_LOC[2])
    if k >= TBK[0][0]: return tab_arm(side, k, lru)
    if side == "Right" and SIT_T[0] <= k < TBK[0][0]:
        u = ss((k - SIT_T[0]) / float(SIT_T[1] - SIT_T[0])); a_, b_ = (Quaternion(q) for q in NUCA_Q["Right"]); c_, d_ = (Quaternion(q) for q in SIT_Q["Right"]); return _qpow(a_, c_, u), _qpow(b_, d_, u), tuple(lru)
    if side == "Left" and k >= CLR_KEYS[0][0]:
        c_ = clr_pose(k)
        if c_ is not None: return c_[0], c_[1], tuple(lru)
    if k >= NUCA0:
        gu, ge = (Quaternion(q) for q in NUCA_Q[side]); u = ss((k - NUCA0) / float(NUCA_D)); return qru.slerp(gu, u), qre.slerp(ge, u), tuple(lru)
    for tool, sd, gf, p in THROWS:
        if sd != side: continue
        kr = gf + HOLD_D + SWING_D; gu, ge = _goal(sd, p); ru_, re_ = (Quaternion(q) for q in REL_Q[sd])
        if gf - REACH_D <= k < gf: u = ss((k - gf + REACH_D) / float(REACH_D)); w = u; return qru.slerp(gu, u), qre.slerp(ge, u), tuple(l * (1 - w) + g * w for l, g in zip(lru, locg))
        if gf <= k < gf + HOLD_D: return gu, ge, locg
        if gf + HOLD_D <= k < kr:
            x_ = (k - gf - HOLD_D) / float(SWING_D); u = 0.3 * ela(x_) + 0.7 * ss(x_); w = 1 - ss(x_)      # Elastic In-Out mezclado al 30 % con suave: el tiron de ~165 grados sigue elastico pero no salta de golpe
            return _qpow(gu, ru_, u), _qpow(ge, re_, u), tuple(l * (1 - w) + g * w for l, g in zip(lru, locg))
        if kr <= k < kr + BACK_D: u = ss((k - kr) / float(BACK_D)); return ru_.slerp(qru, u), re_.slerp(qre, u), tuple(lru)
    return None


def arm_table():
    """euler de los dos brazos para TODOS los frames, construidos en orden y cada uno compatible con el anterior (sin saltos de 360 grados al pasar del reposo a la pose y vuelta)."""
    if ARM_TAB: return
    kstart = min(gf for _, _, gf, _ in THROWS) - REACH_D; prev = {}
    for k in range(1, N + 1):
        rot, loc = alfred_at(k, throw=False)
        for side in ("Right", "Left"):
            ua, el = side + "UpArm_alfred", side + "elbow_alfred"; lru = tuple(loc.get(ua, (0.0, 0.0, 0.0)))
            if k < kstart: prev[ua], prev[el] = Euler(rot[ua], 'XYZ'), Euler(rot[el], 'XYZ'); continue
            if k >= TBK[0][0]:                                                                           # mesa: los Euler se escriben tal cual (sin pasar por cuaterniones)
                e_, x_, l_ = tab_eul(side, k, lru); prev[ua], prev[el] = Euler(e_, 'XYZ'), Euler((x_, 0.0, 0.0), 'XYZ'); ARM_TAB[(side, k)] = (list(e_), [x_, 0.0, 0.0], list(l_)); continue
            qru, qre = Euler(rot[ua], 'XYZ').to_quaternion(), Euler(rot[el], 'XYZ').to_quaternion(); st = arm_state(side, k, qru, qre, lru)
            if st is None: st = (qru, qre, lru)
            eu = st[0].to_euler('XYZ', prev[ua]); ee = st[1].to_euler('XYZ', prev[el]); prev[ua], prev[el] = eu, ee
            ARM_TAB[(side, k)] = (list(eu), list(ee), list(st[2]))


def throw_layer(k, rot, loc):
    w = lean_w(k)
    if w > 0:
        for b, a in LEAN: rot[b][0] += D(a * w)
    lc = clr_lean(k)
    if lc > 0:                                                                                      # se inclina sobre la cadera para llegar a la pila del suelo
        for b, wg in CLR_LEANW: rot[b][0] += D(CLR_T * wg * lc)
        rot["Neck_alfred"][0] += D(-0.15 * CLR_T * lc)
    arm_table()
    for side in ("Right", "Left"):
        t = ARM_TAB.get((side, k))
        if t is None: continue
        ua, el = side + "UpArm_alfred", side + "elbow_alfred"; rot[ua], rot[el] = list(t[0]), list(t[1])
        if ua in loc: loc[ua] = list(t[2])


def alfred_at(k, throw=True):
    """-> ({hueso: (rx, ry, rz) en RADIANES}, {hueso: ubicacion}) para el frame k."""
    rot = {}; loc = {}
    wf = ss((k - 1) / float(REF0 - 1))                                            # la pose de pie se acerca a la primera pose de la referencia con UNA curva lenta durante todo el tramo (f1-60), sin fundido corto
    for b in REFJ["rot"]:
        if k < REF0: r0 = STAND[b]; r1 = ref_rot(b, 0); rot[b] = [r0[j] + (r1[j] - r0[j]) * wf for j in range(3)]
        else: rot[b] = ref_rot(b, (k - REF0) / SLOW)
    for b, arr in REFJ["loc"].items():
        l1 = ref_loc(arr, (k - REF0) / SLOW); loc[b] = [l1[j] * wf for j in range(3)] if k < REF0 else l1
    rot["Neck_alfred"][0] *= 0.3                                                   # mira al FRENTE (la referencia baja la cabeza 16 grados: aqui solo ~5)
    if k < REF0:                                                                  # f1-59: UNA sola animacion hacia la posicion lista para sentarse: gira y da 4 pasitos de acomodo con contrapeso; llega quieto, con los pies juntos y la pose de pie de la referencia
        T = 23.0; v = min(max((k - 3) / T, 0.0), 1.0); W = math.sin(math.pi * v) ** 2                                  # envolvente de los pasos: 0 al empezar y al llegar
        ph = (k - 3) * 2 * math.pi / 11.5; sw = W * math.sin(ph)                                                      # 2 ciclos exactos en f3-26 -> los pasos terminan con las piernas en cero
        rot["RightUpLeg_alfred"][0] += D(15 * sw); rot["LeftUpLeg_alfred"][0] -= D(15 * sw)
        rot["Rightknee_alfred"][0] += D(-16 * W * 0.5 * (1 + math.sin(ph + 1.0))); rot["Leftknee_alfred"][0] += D(-16 * W * 0.5 * (1 - math.sin(ph + 1.0)))
        rot["RightUpArm_alfred"][0] += D(-7 * sw); rot["LeftUpArm_alfred"][0] += D(7 * sw)
        rot["Spine_alfred"][2] += D(-3 * sw); rot["Spine2_alfred"][2] += D(2 * sw); rot["Hips_alfred"][2] += D(2.2 * sw)
        rot["Neck_alfred"][1] += D(28 * math.sin(math.pi * min(max((k - 1) / 20.0, 0.0), 1.0)) ** 2)                      # la cabeza se adelanta al giro y vuelve al frente al terminarlo
        for b_, sd_, a_ in (("Spine_alfred", 1.0, 0.5), ("Spine2_alfred", 3.0, 0.6), ("Neck_alfred", 4.0, 0.8)): rot[b_][0] += D(noise(k, sd_, a_) * (1 - ss((k - 20) / 9.5)))       # ruido organico que se apaga al llegar (la referencia arranca desde cero)
    if k > REFEND:                                                                # reposo: la pose final de la referencia + filtros organicos
        t = k - REFEND; alive = ss(t / 10.0)
        for b, sd, a in (("Spine_alfred", 1.0, 0.8), ("Spine1_alfred", 2.0, 0.7), ("Spine2_alfred", 3.0, 0.9)): rot[b][0] += D(alive * noise(k, sd, a)); rot[b][2] += D(alive * noise(k, sd + 9, 0.6))
        rot["Neck_alfred"][0] += D(alive * noise(k, 4.0, 1.4)); rot["Neck_alfred"][2] += D(alive * noise(k, 6.0, 1.0))
        rot["Spine2_alfred"][0] += D(alive * breathe(k, 1.4, 96.0)); rot["Spine_alfred"][0] += D(alive * breathe(k, 0.8, 96.0, 0.5)); rot["Spine1_alfred"][0] += D(alive * breathe(k, 0.6, 96.0, 0.2))
        mira = wp_eval([(T0, (0.0,)), (T0 + 16, (0.0,)), (T0 + 34, (44.0,)), (T0 + 66, (46.0,)), (T0 + 84, (0.0,)), (N, (0.0,))], k)[0]                      # mira la antorcha (a su izquierda: Neck Y +)
        rot["Neck_alfred"][1] += D(mira); rot["Neck_alfred"][0] += D(-4 * ss((k - T0 - 20) / 12.0) * (1 - ss((k - T0 - 80) / 12.0)))
        cae = wp_eval([(T0, (0.0,)), (T0 + 100, (0.0,)), (T0 + 160, (14.0,)), (N, (14.0,))], k)[0]                                                    # se adormece: la cabeza cae mas
        rot["Neck_alfred"][0] += D(cae); rot["Neck_alfred"][2] += D(cae * 0.4)
        sig = math.exp(-((k - T0 - 44) / 7.0) ** 2); rot["Spine2_alfred"][0] += D(-3 * sig)                                                              # suspiro
        # brazo izquierdo (colgando): leve vaiven; el derecho (apoyado) casi quieto
        rot["LeftUpArm_alfred"][0] += D(alive * noise(k, 7.0, 1.2)); rot["Leftelbow_alfred"][0] += D(alive * noise(k, 10.0, 1.6))
    if k >= NUCA0 - 2: nuca_layer(k, rot)
    kn_layer(k, rot, loc)
    if throw: throw_layer(k, rot, loc)
    return rot, loc


def min_z(root):
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); z = 1e9
    for o in bpy.data.objects:
        p = o
        while p and p.name != root: p = p.parent
        if p and o.type == "MESH" and not o.hide_viewport:
            oe = o.evaluated_get(dg); me = oe.to_mesh(); mw = oe.matrix_world
            z = min(z, min((mw @ v.co).z for v in me.vertices)); oe.to_mesh_clear()
    return z


HY = {"v": 0.0}; KZ = {}


def apply_alfred(k, key=True):
    rot, loc = alfred_at(k)
    x, y, z, rz = root_at(k)
    O.location = (x, y, z); O.rotation_euler = (0, 0, TH + D(rz))
    for b, v in rot.items(): PA[b].rotation_euler = v
    for b, v in loc.items(): PA[b].location = v
    if k >= REF0: PA["Hips_alfred"].location = (loc["Hips_alfred"][0], loc["Hips_alfred"][1] + HYK[max(q for q in HYK if q <= k)] * (1 - kn_w(k)) + KZ.get(k, 0.0), loc["Hips_alfred"][2])
    if not key: return
    for b, v in rot.items(): PA[b].keyframe_insert("rotation_euler", frame=k)
    for b in loc: PA[b].keyframe_insert("location", frame=k)
    O.keyframe_insert("location", frame=k); O.keyframe_insert("rotation_euler", frame=k)


# ----------------------------------------------------------------------------------------------- JERRY
J = bpy.data.objects["jerry"]; RJ = bpy.data.objects["Dog_001_rig"]; PJ = RJ.pose.bones
for ob in (J, RJ): clear(ob)
for b in PJ: b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
TJ = -1.783                                                                       # giro del root de Jerry cuando mira al +X (f1)
FACE = {"S": D(-90), "NE": 0.68}
ROOT_J = [(1, (-96.5, -108.84, 14.0, 0.0)), (10, (-96.5, -108.84, 14.0, -1.571)), (34, (-96.55, -109.45, 14.0, -1.571)), (48, (-96.55, -109.45, 14.0, 0.68)), (66, (-96.55, -109.45, 13.85, 0.68)), (360, (-96.55, -109.45, 13.85, 0.68))]
SIT = ss  # alias


# POSE DE SENTADO DE JERRY elegida por el usuario en Blender (pose a mano en f62; rotaciones/ubicaciones de todos los huesos extraidas en `pose_jerry_sentado_usuario.json`)
SITJ = json.load(open("C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/parte3/pose_jerry_sentado_usuario.json", encoding="utf-8"))["bones"]
SITJ = {b: v for b, v in SITJ.items() if b in PJ and (any(abs(x) > 1e-3 for x in v["rot"]) or any(abs(x) > 1e-4 for x in v["loc"]))}

# AJUSTE DE CONTACTO (resuelto en Blender por busqueda de coordenadas): en la pose a mano la pata trasera izquierda quedaba ~6 cm bajo el suelo y el resto ~4-10 cm en el aire; con estos deltas en X
# (grados) las dos patas traseras, las dos delanteras y la grupa tocan el suelo a la vez (14.02) con el root a z 13.907. Medido: hindL 14.021, hindR 14.021, frontR 14.020, frontL 14.020, grupa 14.023, cola 14.032.
CONTACT = {"thigh.L": 9.75, "thigh.R": -6.0, "front_thigh.R": 14.625, "front_thigh.L": 12.75, "shoulder.L": 6.0}
for b_, dx_ in CONTACT.items():
    SITJ.setdefault(b_, {"rot": [0.0, 0.0, 0.0], "loc": [0.0, 0.0, 0.0]}); SITJ[b_]["rot"] = [SITJ[b_]["rot"][0] + math.radians(dx_), SITJ[b_]["rot"][1], SITJ[b_]["rot"][2]]


# DORMIR DE COSTADO (pedido de Kebyn, 2026-10-03): tras contestarle a Alfred (f114-158) Jerry se levanta (f160-182), bosteza de pie (f186-210), se acomoda (f196-238: gira 153 grados sobre las caderas, la cabeza pasa por el lado OESTE
# de la sala, lejos de los pies de Alfred, y la cola va enroscada) y se echa sobre su costado DERECHO (f250-284) a lo largo del muro SUR, cabeza al oeste, espalda al norte y patas al sur, como en la vista de planta de referencia
# (el dibujo "durmiendo de lado": cabeza ladeada hacia el vientre, patas delanteras adelantadas, traseras recogidas). El cuerpo rueda 90 grados sobre el eje largo local (Y) del root. Cierra los ojos al acomodarse (f268-292).
# RESPUESTA DE JERRY A ALFRED (pedido de Kebyn): ya echado de costado, tras oir a Alfred ("Ya pero, yo no tengo sueno", f206-265) voltea la cabeza para mirarlo (f272-292) y dice "Pero yo si, asi que apaga la antorcha y a dormir"
# (audios/jerry/pero_yo_si_apaga_la_antorcha.wav, 63 f, voz del f287 -> habla f292-344). Despues vuelve la cabeza (f352-374) y SOLO ENTONCES cierra los ojos y se duerme (antes se dormia al echarse).
# LOOKA = cabeza hacia la cabeza de Alfred, resuelta numericamente en Blender con la pose echada (angulo de error 0.2 grados): deltas en grados de (hueso, eje) para spine_2 X/Z, spine_1 X/Z, scull_1 X/Y/Z y scull X/Y/Z.
LOOK_UP0, LOOK_DN0 = 284, 358                                                      # el giro empieza cuando ya termino de echarse (f284); vuelve f358-386
LOOKA = [("spine_4", 0, -8.75), ("spine_4", 1, 35), ("spine_4", 2, -32.5), ("spine_3", 0, -33.75), ("spine_3", 1, -25), ("spine_3", 2, -42.5), ("spine_2", 0, -10), ("spine_2", 1, 60), ("spine_2", 2, -10),
         ("spine_1", 0, 20), ("spine_1", 1, 20), ("spine_1", 2, 17.5), ("scull_1", 2, -2.5)]       # v27: SIN ROTACION en el hueso `scull` (deformaba las mallas de ojos y cejas): todo el giro lo hacen spine_4..scull_1
# v26: el giro arranca en spine_4 (padre de los dos hombros delanteros): front_shoulder.L (la pata izquierda, arriba) gira CON el cuerpo (46 grados); el hombro derecho se contragira con la tabla PATA_R
# (rotacion + ubicacion calculadas en Blender frame a frame para que su pierna y su pie queden EXACTOS donde estaban: la pata derecha se queda en el suelo). Optimizado contra la malla: cabeza 17 puntos dentro (natural), 9 cm de holgura, error de angulo 0.5 grados.
ROLL_LOOK = 0.0                                                                    # grados que se levanta el cuerpo sobre su costado al mirar a Alfred
SLEEP_J0 = 384                                                                      # empieza a cerrar los ojos (cerrados del todo en SLEEP_J0 + 26)
TWITCH = (424, 432)                                                                 # la pata que tiembla al sonar
STAND0, STAND_D = 160, 22
TURN0, TURN_D = 196, 42
LIE0, LIE_D = 250, 34
LIE = {"spine_6": (0, 0, 0), "spine_5": (8, 0, 0), "spine_4": (-6, 0, 0), "spine_3": (8, 0, 0), "spine_2": (10, 0, 0), "spine_1": (10, 0, 0), "scull_1": (25, 0, 0), "scull": (15, 0, 0),
       "front_shoulder.R": (50, 0, 0), "front_thigh.R": (-30, 0, 0), "front_shin.R": (20, 0, 0), "front_foot.R": (25, 0, 0),
       "front_shoulder.L": (35, 0, 0), "front_thigh.L": (-20, 0, 0), "front_shin.L": (15, 0, 0), "front_foot.L": (20, 0, 0),
       "shoulder.R": (-35, 0, 0), "thigh.R": (55, 0, 0), "shin.R": (-60, 0, 0), "foot.R": (30, 0, 0),
       "shoulder.L": (-25, 0, 0), "thigh.L": (45, 0, 0), "shin.L": (-50, 0, 0), "foot.L": (25, 0, 0),
       "tail_1": (30, 0, 0), "tail_2": (25, 0, 0), "tail_3": (20, 0, 0)}
SIT_END = (-96.55, -109.45)                                                         # donde se sienta (rincon SO)
TURN_END = (-96.15, -109.52)                                                        # donde termina de girar
LIE_ROOT = (-96.15, -109.90)                                                        # root al echarse: patas al muro sur (y -110), espalda al norte (y ~ -109.3)
RZ_LIE = math.pi / 2 - TJ                                                           # yaw total +90 grados (cabeza al oeste)


def sit_w(k):
    """peso del sentado: se sienta f48-66, se levanta f160-182."""
    return ss((k - 48) / 18.0) * (1 - ss((k - STAND0) / float(STAND_D)))


PATA_R = {}                                                                         # {frame: [rx, ry, rz, lx, ly, lz]} del hueso front_shoulder.R: contragiro (grados / metros locales) para que su pierna no se mueva mientras gira el cuerpo
_ruta_pata = "C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/parte3/pata_delantera_R.json"
if os.path.exists(_ruta_pata):
    PATA_R = {int(k_): v_ for k_, v_ in json.load(open(_ruta_pata, encoding="utf-8")).items()}


def pata_delta(k):
    """tabla de la pata derecha interpolada en el frame k -> [rx, ry, rz, lx, ly, lz] (ceros fuera de la tabla)."""
    if not PATA_R: return [0.0] * 6
    ks = sorted(PATA_R)
    if k <= ks[0]: return list(PATA_R[ks[0]])
    if k >= ks[-1]: return list(PATA_R[ks[-1]])
    i = max(q for q in range(len(ks)) if ks[q] <= k); a = ks[i]; b = ks[i + 1]; u = (k - a) / float(b - a)
    return [PATA_R[a][j] + (PATA_R[b][j] - PATA_R[a][j]) * u for j in range(6)]


# REACCION DE JERRY A LO QUE LE CAE ENCIMA (pedido de Kebyn): cada herramienta que aterriza en su lomo (f466 / 479 / 492) le da un respingo (JR_HIT: lomo, orejas, pata y cola, con rebote que se apaga); tras la tercera
# abre un poco los ojos y se sacude: levanta el cuerpo f497-510 (rueda ~35 grados de su costado hacia arriba, levanta la cabeza, patea y tiembla) y lanza las herramientas, que salen disparadas del lomo (JR_REL) en un vuelo
# parabolico con giro y caen apiladas en el rincon sureste, junto al muro este (JR_PILE), libre de la mesa, de la antorcha y de Alfred. Despues vuelve a dormir.
JR_HIT = (466, 479, 492); JR_SHAKE = (497, 502, 510); JR_ROLL = 35.0
JR_REL = {"stone_axe": 503, "wooden_axe": 504, "wooden_pickaxe": 505}; JR_FLY = 12
JR_PILE = {"stone_axe": ((-95.26, -109.62), 80.0), "wooden_axe": ((-95.27, -109.58), 100.0), "wooden_pickaxe": ((-95.25, -109.64), 90.0)}


# LA PATA IZQUIERDA (la de arriba) BARRE LAS HERRAMIENTAS (pedido de Kebyn): front_shoulder.L (X, Z), front_thigh.L (X, Z) y front_shin.L (X), en grados SUMADOS a la postura de dormir. Poses resueltas en Blender contra la punta de la pata
# (front_toe.L): C = levanta la pata por encima del lomo (-96.40, -109.55, 14.90), A = la echa atras por el lado sur de las herramientas (-96.35, -109.78, 14.72), B = barrido hacia el norte a ras del lomo (-96.47, -109.37, 14.50).
JR_PAW = [(494, (0.0, 0.0, 0.0, 0.0, 0.0)), (498, (15.0, 77.9, -63.4, 21.0, 2.3)), (501, (-15.9, 49.7, -60.8, 26.1, 1.4)), (504, (-30.2, 0.8, 80.2, -16.1, 80.2)), (507, (-30.2, 0.8, 80.2, -16.1, 80.2)), (513, (0.0, 0.0, 0.0, 0.0, 0.0))]


def jr_hit(k):
    return sum(math.exp(-(k - h) / 4.0) * math.cos((k - h) * 0.9) for h in JR_HIT if k >= h)


def jr_shake(k):
    """(envolvente 0..1 del sacudon, temblor -1..1)."""
    a, b, c = JR_SHAKE; env = ss((k - a) / float(b - a)) * (1 - ss((k - b) / float(c - b))); return env, math.sin((k - a) * 1.7) * min(1.0, env * 3.0) * (1.0 if a <= k <= c else 0.0)


def la_body(k):
    return ss((k - LOOK_UP0) / 20.0) * (1 - ss((k - LOOK_DN0 - 6) / 22.0))


def root_j(k):
    """(x, y, z, rz, roll) del root de Jerry. f1-160: waypoints; f160-182 se levanta (z 13.85 -> 14.0); f196-238 gira sobre las caderas; f250-284 rueda 90 grados sobre su costado derecho y se pega al muro sur."""
    x, y, z, rz = wp_eval(ROOT_J, k); roll = 0.0
    if k > STAND0: z = 13.85 + 0.15 * ss((k - STAND0) / float(STAND_D))
    if k > TURN0:
        v = ss((k - TURN0) / float(TURN_D)); rz = 0.68 + (RZ_LIE - 0.68) * v
        x = SIT_END[0] + (TURN_END[0] - SIT_END[0]) * v; y = SIT_END[1] + (TURN_END[1] - SIT_END[1]) * v
    if k > LIE0:
        w = ss((k - LIE0) / float(LIE_D)); x = TURN_END[0] + (LIE_ROOT[0] - TURN_END[0]) * w; y = TURN_END[1] + (LIE_ROOT[1] - TURN_END[1]) * w; roll = (math.pi / 2) * w
    roll += math.radians(ROLL_LOOK) * la_body(k)
    env_, tre_ = jr_shake(k); roll += -math.radians(JR_ROLL) * env_ + math.radians(3.0) * tre_ + math.radians(1.5) * jr_hit(k)         # se sacude: rueda hacia arriba (Y menos = hacia vertical) y tiembla
    return x, y, z, rz, roll


def jloc_at(k):
    """ubicacion del hueso de la grupa (spine_6) en la pose de sentado: se aplica con el mismo peso `sit` (la grupa baja entre las patas traseras)."""
    sit = sit_w(k); l = SITJ.get("spine_6", {"loc": [0, 0, 0]})["loc"]
    return [x * sit for x in l]


def jerry_at(k):
    out = {b.name: [0.0, 0.0, 0.0] for b in PJ if b.name in (
        "spine_6", "spine_5", "spine_4", "spine_3", "spine_2", "spine_1", "scull_1", "jaw_bot", "tail_1", "tail_2", "tail_3", "ear.R", "ear.L",
        "thigh.R", "thigh.L", "shin.R", "shin.L", "foot.R", "foot.L", "toe.R", "toe.L", "front_shoulder.R", "front_shoulder.L", "front_thigh.R", "front_thigh.L",
        "front_shin.R", "front_shin.L", "front_foot.R", "front_foot.L", "front_toe.R", "front_toe.L") or b.name in SITJ}
    sit = sit_w(k)                                                                  # f48-66 se sienta, f160-182 se levanta
    lie = ss((k - LIE0) / float(LIE_D))                                             # f250-284 se echa de costado
    # caminata f10-34 (trote lento) y pasitos de giro f1-10 / f34-48
    wk = ss((k - 8) / 4.0) * (1 - ss((k - 34) / 4.0)); tn = (ss((k - 1) / 3.0) * (1 - ss((k - 10) / 3.0))) + (ss((k - 34) / 3.0) * (1 - ss((k - 48) / 3.0)))
    gc = ss((k - TURN0) / 4.0) * (1 - ss((k - TURN0 - TURN_D + 4) / 4.0)); gl = ss((k - LIE0 + 6) / 4.0) * (1 - ss((k - LIE0) / 4.0))            # pasitos al girar (f196-238) y al echarse
    amp = max(wk, 0.7 * tn, 0.8 * gc, 0.5 * gl)
    if amp > 0:
        ph = (k - 1) * 2 * math.pi / 7.0
        for s, o in (("R", 0.0), ("L", math.pi)):
            out[f"thigh.{s}"][0] += amp * 26 * math.sin(ph + o); out[f"shin.{s}"][0] += -amp * 22 * max(0.0, math.sin(ph + o + 0.8)); out[f"foot.{s}"][0] += amp * 10 * math.sin(ph + o + 0.5)
        for s, o in (("R", math.pi), ("L", 0.0)):
            out[f"front_thigh.{s}"][0] += amp * 24 * math.sin(ph + o); out[f"front_shin.{s}"][0] += -amp * 14 * max(0.0, math.sin(ph + o + 0.8))
        out["spine_6"][2] += amp * 3 * math.sin(ph); out["spine_3"][2] += -amp * 5 * math.sin(ph); out["scull_1"][2] += amp * 3 * math.sin(ph)
        out["tail_1"][2] += amp * 12 * math.sin(ph * 0.5)
    # sentado: la pose de Jerry elegida por el usuario (se mezcla con la de caminar segun `sit`, f48-66)
    for b_, v_ in SITJ.items():
        for j_ in range(3): out[b_][j_] = out[b_][j_] * (1 - sit) + math.degrees(v_["rot"][j_]) * sit
    tc = ss((k - 186) / 8.0) * (1 - ss((k - 242) / 8.0))                            # cola enroscada mientras gira (no toca el muro sur ni a Alfred)
    out["tail_1"][2] += -tc * 55; out["tail_2"][2] += -tc * 45; out["tail_3"][2] += -tc * 35; out["tail_1"][0] += tc * 20
    for b_, v_ in LIE.items():                                                      # postura de dormir de costado
        o_ = out.setdefault(b_, [0.0, 0.0, 0.0])
        for j_ in range(3): o_[j_] = o_[j_] * (1 - lie) + v_[j_] * lie
    # reposo (f70+): respiracion, cola perezosa, oreja, mira a Alfred, bosteza y duerme
    rest = ss((k - 70) / 12.0)
    out["spine_5"][0] += rest * breathe(k, 1.6, 80.0); out["spine_3"][0] += rest * breathe(k, 1.1, 80.0, 0.4)
    out["tail_1"][2] += rest * (10 * math.sin(k * 0.055) + 4 * math.sin(k * 0.13)); out["tail_2"][2] += rest * 8 * math.sin(k * 0.055 - 0.7); out["tail_3"][2] += rest * 8 * math.sin(k * 0.055 - 1.4)
    ear = math.exp(-((k - 125) / 4.0) ** 2) + math.exp(-((k - 330) / 4.0) ** 2); out["ear.R"][0] += 18 * ear; out["ear.L"][0] += -12 * ear
    look = wp_eval([(1, (0.0,)), (96, (0.0,)), (112, (-38.0,)), (160, (-38.0,)), (178, (0.0,)), (230, (0.0,)), (262, (0.0,))], k)[0]       # gira la cabeza hacia Alfred (Z de scull_1; el signo se midio con la pose sentada)
    out["scull_1"][2] += look * 0.9
    yawn = ss((k - 186) / 8.0) * (1 - ss((k - 210) / 8.0)); out["jaw_bot"][0] += -yawn * 28; out["scull_1"][0] += -yawn * 12
    la_b = la_body(k)                                                                # CUERPO: gira f272-292 y se deshace f358-380
    la_h = ss((k - LOOK_UP0 - 6) / 18.0) * (1 - ss((k - LOOK_DN0) / 18.0))           # CABEZA: va un poco detras al girar y se adelanta al volver (asi nunca se mete en el pecho: medido contra la malla)
    for b_, ax_, v_ in LOOKA:
        w_ = la_h if b_.startswith("scull") else la_b
        if w_ > 0: out[b_][ax_] += w_ * v_
    pd_ = pata_delta(k)
    for j_ in range(3): out["front_shoulder.R"][j_] += pd_[j_]                      # contragiro del hombro derecho (la pata se queda en el suelo)
    out["spine_5"][0] += lie * breathe(k, 1.8, 96.0, 0.3); out["spine_3"][0] += lie * breathe(k, 1.2, 96.0, 0.7)                                                       # respiracion lenta y profunda al dormir
    tw = math.exp(-((k - TWITCH[0]) / 3.0) ** 2) + 0.7 * math.exp(-((k - TWITCH[1]) / 3.0) ** 2); out["front_foot.R"][0] += lie * 9 * tw; out["foot.R"][0] += lie * 6 * tw; out["ear.L"][0] += lie * 8 * tw  # suena: tiembla una pata
    ht_ = jr_hit(k); env_, tre_ = jr_shake(k)
    out["spine_5"][0] += 5.0 * ht_; out["spine_3"][0] += 4.0 * ht_; out["ear.R"][0] += 16 * ht_; out["ear.L"][0] += -12 * ht_; out["front_foot.R"][0] += 8 * ht_; out["tail_1"][2] += 10 * ht_
    pw_ = wp_eval(JR_PAW, k)
    out["front_shoulder.L"][0] += pw_[0]; out["front_shoulder.L"][2] += pw_[1]; out["front_thigh.L"][0] += pw_[2]; out["front_thigh.L"][2] += pw_[3]; out["front_shin.L"][0] += pw_[4]
    out["scull_1"][0] += -16 * env_; out["thigh.R"][0] += 12 * env_ + 6 * tre_; out["front_thigh.R"][0] += -10 * env_; out["tail_1"][2] += 28 * tre_; out["tail_2"][2] += 22 * tre_; out["ear.R"][0] += 10 * abs(tre_)
    return out


def apply_jerry(k):
    for b, v in jerry_at(k).items():
        pb = PJ[b]; pb.rotation_euler = [D(x) for x in v]; pb.keyframe_insert("rotation_euler", frame=k)
    PJ["spine_6"].location = jloc_at(k); PJ["spine_6"].keyframe_insert("location", frame=k)
    PJ["front_shoulder.R"].location = pata_delta(k)[3:6]; PJ["front_shoulder.R"].keyframe_insert("location", frame=k)
    x, y, z, rz, roll = root_j(k)
    J.location = (x, y, z + DZS.get(k, 0.0)); J.rotation_euler = (0, roll, TJ + rz); J.keyframe_insert("location", frame=k); J.keyframe_insert("rotation_euler", frame=k)


frames = sorted(set(range(1, N + 1, STEP)) | set(range(1, REFEND + 6)) | set(range(STAND0 - 4, LIE0 + LIE_D + 12)) | set(range(THROW_RANGE[0], THROW_RANGE[1] + 1)) | set(range(NUCA0 - 4, NUCA0 + NUCA_D + 45)) | set(range(CLR_RANGE[0], CLR_RANGE[1] + 1)) | set(range(KN0 - 4, N + 1)) | set(range(JR_HIT[0] - 4, JR_HIT[0] + 40)))                # cada 2 f, y CADA frame mientras se sienta (30 f: con muestras cada 2 f se perderia el detalle)
if frames[-1] != N: frames.append(N)
# PASADA 1 (sin keyframes): correccion de altura de la cadera para tocar el suelo (z 13.99) al agacharse/sentarse. IMPORTANTE: se calcula ANTES de keyframear porque view_layer.update() con una accion ya creada
# re-evalua la animacion en el frame actual de la escena y pisaba el root con el valor del f1 (rotaciones bruscas de +-720 en f60-62 del empty).
HYK = {REF0: 0.0}
for k in frames:
    if REF0 <= k <= REF0 + int(90 * SLOW):
        rot, loc = alfred_at(k); x, y, z, rz = root_at(k)
        O.location = (x, y, z); O.rotation_euler = (0, 0, TH + D(rz))
        for b_, v_ in rot.items(): PA[b_].rotation_euler = v_
        for b_, v_ in loc.items(): PA[b_].location = v_
        HYK[k] = 13.99 - min_z(O.name)
# PASADA 1b (sin keyframes): Jerry NUNCA atraviesa el suelo. Por frame se mide su punto mas bajo (todas las mallas) y se corrige la altura del root para que quede a 14.015 (suelo 14.0 + 1.5 cm de margen);
# la correccion se suaviza con una media movil de +-3 frames. Corrige las patas enterradas al sentarse (y los 2 cm que se hundian al caminar).
DZK = {}
for k in frames:
    for b_, v_ in jerry_at(k).items(): PJ[b_].rotation_euler = [D(x_) for x_ in v_]
    PJ["spine_6"].location = jloc_at(k); PJ["front_shoulder.R"].location = pata_delta(k)[3:6]
    x, y, z, rz, roll = root_j(k); J.location = (x, y, z); J.rotation_euler = (0, roll, TJ + rz)
    DZK[k] = 14.015 - min_z("jerry")
DZS = {}
for i, k in enumerate(frames):
    w = [DZK[frames[q]] for q in range(max(0, i - 3), min(len(frames), i + 4))]; DZS[k] = max(sum(w) / len(w), DZK[k] - 0.012)                              # suave, pero nunca por debajo de 14.003
def pose_jerry(k):
    for b_, v_ in jerry_at(k).items(): PJ[b_].rotation_euler = [D(x_) for x_ in v_]
    PJ["spine_6"].location = jloc_at(k); PJ["front_shoulder.R"].location = pata_delta(k)[3:6]
    x, y, z, rz, roll = root_j(k); J.location = (x, y, z + DZS.get(k, 0.0)); J.rotation_euler = (0, roll, TJ + rz)


def _de_jerry(o):
    while o:
        if o.name == "jerry": return True
        o = o.parent
    return False


JMESH = {o.name for o in bpy.data.objects if o.type == "MESH" and _de_jerry(o)}


def lomo_jerry(x, y):
    """z de la superficie de Jerry bajo (x, y) (rayo hacia abajo contra sus mallas, en la pose actual); 14.45 si no toca."""
    o = Vector((x, y, 15.6)); dg = bpy.context.evaluated_depsgraph_get()
    for _ in range(6):
        ok, loc, _n, _i, ob, _m = sc.ray_cast(dg, o, (0, 0, -1), distance=2.0)
        if not ok: break
        if ob.name in JMESH: return loc.z
        o = loc + Vector((0, 0, -0.003))
    return 14.45


# PASADA 1d (sin keyframes): al ponerse de rodillas las piernas (mallas con peso en piernas / rodillas / pies) nunca atraviesan el suelo: se sube la cadera lo justo (media movil de +-2 frames)
import re
_LEGRE = re.compile(r"Leg|knee|no_bone_0[1256789]|no_bone_010")
_BODY = [o for o in bpy.data.objects if o.name.startswith("Mesh_") and o.name.endswith("_alfred")]
_VLEG = {o.name: [v.index for v in o.data.vertices if any(gr.group in [vg.index for vg in o.vertex_groups if _LEGRE.search(vg.name)] and gr.weight > 0.5 for gr in v.groups)] for o in _BODY}


def piernas_minz():
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); z = 1e9
    for o in _BODY:
        if not _VLEG[o.name]: continue
        oe = o.evaluated_get(dg); me = oe.to_mesh(); mw = oe.matrix_world; z = min(z, min((mw @ me.vertices[i].co).z for i in _VLEG[o.name])); oe.to_mesh_clear()
    return z


KZ0 = {}
for k in frames:
    if KN0 - 2 <= k <= KN1 + 12:
        apply_alfred(k, key=False); KZ0[k] = max(0.0, 13.99 - piernas_minz())
ks_ = sorted(KZ0)
for i, k in enumerate(ks_):
    w_ = [KZ0[ks_[q]] for q in range(max(0, i - 2), min(len(ks_), i + 3))]; KZ[k] = max(sum(w_) / len(w_), KZ0[k] - 0.01)
# PASADA 1c (sin keyframes): matrices del hueso Spine1 y de los antebrazos en cada frame -> herramientas: pegadas a la espalda, en la mano (de que la agarra hasta que la suelta), vuelo parabolico y montoncito en el suelo
MS = {}; MH = {}; MJ = {}
for k in frames:
    apply_alfred(k, key=False); pose_jerry(k); bpy.context.view_layer.update()
    MS[k] = A.matrix_world @ PA["Spine1_alfred"].matrix; MH[k] = {sd: A.matrix_world @ PA[sd + "elbow_alfred"].matrix for sd in ("Right", "Left")}; MJ[k] = RJ.matrix_world @ PJ["spine_3"].matrix
TK = {tn: {} for tn in TOOLS}; stack = 0.0; stack2 = 0.0; GRAV = 9.8; FPS = 24.0
for ti, (tn, sd, gf, G) in enumerate(THROWS):
    t_ = bpy.data.objects[tn]; rel_s = Matrix([t_["rel_spine1"][i:i + 4] for i in range(0, 16, 4)])
    sc_ = t_.matrix_world.to_scale() if t_.parent is None else Vector((1, 1, 1)); dims = [t_.dimensions[i] / max(abs(sc_[i]), 1e-6) for i in range(3)]
    cl = sum((Vector(c) for c in t_.bound_box), Vector()) / 8.0; thin = min(range(3), key=lambda i: dims[i]); lng = max(range(3), key=lambda i: dims[i]); third = 3 - thin - lng
    thick = dims[thin] * abs(sc_[thin]); kr = gf + HOLD_D + SWING_D; kl = kr + FLY_D
    (cx, cy), yaw = PILE[tn]; L = Vector((math.cos(D(yaw)), math.sin(D(yaw)), 0.0)); Zv = Vector((0, 0, 1.0)); Tv = Zv.cross(L)
    cols = [None, None, None]; cols[lng] = L; cols[thin] = Zv; cols[third] = Tv
    Rl = Matrix(((cols[0][0], cols[1][0], cols[2][0]), (cols[0][1], cols[1][1], cols[2][1]), (cols[0][2], cols[1][2], cols[2][2])))
    if Rl.determinant() < 0: cols[third] = -Tv; Rl = Matrix(((cols[0][0], cols[1][0], cols[2][0]), (cols[0][1], cols[1][1], cols[2][1]), (cols[0][2], cols[1][2], cols[2][2])))
    ql = Rl.to_quaternion(); cen_l = Vector((cx, cy, 14.0 + stack + thick / 2 + 0.004)); stack += thick
    S = Matrix.Diagonal((sc_[0], sc_[1], sc_[2])); off = lambda R: R @ (S @ cl)                               # centro del bbox en mundo = loc + R @ (S @ cl)
    Mg = MS[gf] @ rel_s; Hrel = MH[gf][sd].inverted() @ Mg                                                      # agarre: la herramienta pasa de la espalda a la mano SIN saltos (misma matriz en gf)
    Mr = MH[kr][sd] @ Hrel; cen_r = Vector(Mr @ cl); qr = Mr.to_quaternion()
    Tf = FLY_D / FPS; vz = (cen_l.z - cen_r.z + 0.5 * GRAV * Tf * Tf) / Tf
    # --- despejar: manotazo (CLR_HIT) -> vuelo por encima de Jerry -> rebote en el muro sur -> cae sobre su lomo -> viaja con el (hueso spine_3)
    hit = CLR_HIT[tn]; T1, T2 = CLR_T1, CLR_T2; cen_w = Vector((CLR_WALL[tn], CLR_WALL_Y, CLR_WALL_Z)); kL = hit + T1 + T2; xj, yj, yawj = CLR_JERRY[tn]
    pose_jerry(kL); bpy.context.view_layer.update(); zj = lomo_jerry(xj, yj); cen_j = Vector((xj, yj, zj + thick / 2 + 0.004))
    Lj = Vector((math.cos(D(yawj)), math.sin(D(yawj)), 0.0)); Tj = Zv.cross(Lj); colj = [None, None, None]; colj[lng] = Lj; colj[thin] = Zv; colj[third] = Tj
    Rj = Matrix(((colj[0][0], colj[1][0], colj[2][0]), (colj[0][1], colj[1][1], colj[2][1]), (colj[0][2], colj[1][2], colj[2][2])))
    if Rj.determinant() < 0: colj[third] = -Tj; Rj = Matrix(((colj[0][0], colj[1][0], colj[2][0]), (colj[0][1], colj[1][1], colj[2][1]), (colj[0][2], colj[1][2], colj[2][2])))
    qj = (Quaternion((1, 0, 0), D(7)) @ Rj.to_quaternion()); Rj = qj.to_matrix()                                    # cae un poco ladeada
    q1 = Quaternion((1, 0, 0), -1.5 * math.pi) @ ql; Tf1 = T1 / FPS; Tf2 = T2 / FPS
    vz1 = (cen_w.z - cen_l.z + 0.5 * GRAV * Tf1 * Tf1) / Tf1; vz2 = (cen_j.z - cen_w.z + 0.5 * GRAV * Tf2 * Tf2) / Tf2
    Mrest = Matrix.LocRotScale(cen_j - off(Rj), qj, sc_); Rel_j = MJ[kL].inverted() @ Mrest
    kR = JR_REL[tn]; MR = MJ[kR] @ Rel_j; cen_r = Vector(MR @ cl); qr_j = MR.to_quaternion(); (px, py), pyaw = JR_PILE[tn]; cen_p = Vector((px, py, 14.0 + stack2 + thick / 2 + 0.004)); stack2 += thick
    Lp = Vector((math.cos(D(pyaw)), math.sin(D(pyaw)), 0.0)); Tp = Zv.cross(Lp); colp = [None, None, None]; colp[lng] = Lp; colp[thin] = Zv; colp[third] = Tp
    Rp = Matrix(((colp[0][0], colp[1][0], colp[2][0]), (colp[0][1], colp[1][1], colp[2][1]), (colp[0][2], colp[1][2], colp[2][2])))
    if Rp.determinant() < 0: colp[third] = -Tp; Rp = Matrix(((colp[0][0], colp[1][0], colp[2][0]), (colp[0][1], colp[1][1], colp[2][1]), (colp[0][2], colp[1][2], colp[2][2])))
    qp = Rp.to_quaternion(); TfJ = JR_FLY / FPS; vzJ = (cen_p.z - cen_r.z + 0.5 * GRAV * TfJ * TfJ) / TfJ
    for k in frames:
        if k < gf: M = MS[k] @ rel_s; loc, q = M.to_translation(), M.to_quaternion()
        elif k < kr: M = MH[k][sd] @ Hrel; loc, q = M.to_translation(), M.to_quaternion()
        elif k < kl:
            u = (k - kr) / float(FLY_D); t = u * Tf; c = Vector((cen_r.x + (cen_l.x - cen_r.x) * u, cen_r.y + (cen_l.y - cen_r.y) * u, cen_r.z + vz * t - 0.5 * GRAV * t * t))
            q = Quaternion((0, 1, 0), 2 * math.pi * (1 - u) * (1 if ti % 2 == 0 else -1)) @ qr.slerp(ql, ss(u)); loc = c - off(q.to_matrix())
        elif k < hit: q = ql; loc = cen_l - off(Rl)
        elif k < hit + T1:
            u = (k - hit) / float(T1); t = u * Tf1; c = Vector((cen_l.x + (cen_w.x - cen_l.x) * u, cen_l.y + (cen_w.y - cen_l.y) * u, cen_l.z + vz1 * t - 0.5 * GRAV * t * t))
            q = Quaternion((1, 0, 0), -1.5 * math.pi * u) @ ql; loc = c - off(q.to_matrix())
        elif k < kL:
            u = (k - hit - T1) / float(T2); t = u * Tf2; c = Vector((cen_w.x + (cen_j.x - cen_w.x) * u, cen_w.y + (cen_j.y - cen_w.y) * u, cen_w.z + vz2 * t - 0.5 * GRAV * t * t))
            q = q1.slerp(qj, ss(u)); loc = c - off(q.to_matrix())
        elif k < kR:
            M = MJ[k] @ Rel_j; loc, q = M.to_translation(), M.to_quaternion()
        elif k < kR + JR_FLY:                                                                                       # Jerry se sacude y las lanza: vuelo parabolico con giro hasta el rincon sureste
            u = (k - kR) / float(JR_FLY); t = u * TfJ; c = Vector((cen_r.x + (cen_p.x - cen_r.x) * u, cen_r.y + (cen_p.y - cen_r.y) * u, cen_r.z + vzJ * t - 0.5 * GRAV * t * t))
            q = Quaternion((0, 0, 1), 3 * math.pi * (1 - ss(u)) * (1 if ti % 2 == 0 else -1)) @ qr_j.slerp(qp, ss(u)); loc = c - off(q.to_matrix())
        else: q = qp; loc = cen_p - off(Rp)
        TK[tn][k] = (loc, q, sc_)
for k in frames:
    apply_alfred(k); apply_jerry(k)
for tn in TOOLS:
    t_ = bpy.data.objects[tn]; prev = None
    for k in frames:
        loc, q, sc_ = TK[tn][k]
        if prev is not None and q.dot(prev) < 0: q = -q
        prev = q; t_.location = loc; t_.rotation_quaternion = q; t_.scale = sc_
        t_.keyframe_insert("location", frame=k); t_.keyframe_insert("rotation_quaternion", frame=k); t_.keyframe_insert("scale", frame=k)
# la MESA DE CRAFTEO: se importa una sola vez (objeto vacio `mesa_de_crafteo_1` + su malla) a la coleccion `mesa_crafteo` y se anima el vacio (ubicacion / rotacion / escala por frame)
MESA = bpy.data.objects.get("mesa_de_crafteo_1")
if MESA is None:
    with bpy.data.libraries.load(MESA_PATH, link=False) as (_src, _dst): _dst.objects = ["mesa_de_crafteo_1", "9ec2028a-8e9e-9a30-eae2-7cc72eda0077_1"]
    MESA = bpy.data.objects["mesa_de_crafteo_1"]
_col = bpy.data.collections.get("mesa_crafteo") or bpy.data.collections.new("mesa_crafteo")
if _col.name not in sc.collection.children: sc.collection.children.link(_col)
for _o in [MESA] + list(MESA.children):
    if _o.name not in _col.objects: _col.objects.link(_o)
    for _c in list(_o.users_collection):
        if _c != _col: _c.objects.unlink(_o)
if MESA.animation_data: MESA.animation_data_clear()
MESA.rotation_mode = 'XYZ'
for k in [1] + [f for f in frames if f >= MESA_T["aparece"] - 2]:
    pos, eu, esc = mesa_pose(k if k > 1 else 1)
    MESA.location = pos; MESA.rotation_euler = eu; MESA.scale = (esc, esc, esc)
    for _dp in ("location", "rotation_euler", "scale"): MESA.keyframe_insert(_dp, frame=k)
# Alfred: parpadeos naturales mientras esta despierto y cierra los ojos al dormirse (shape key "Closed" de los dos ojos)
SLEEP = [(1, (0.0,)), (T0 + 105, (0.0,)), (T0 + 118, (0.5,)), (T0 + 140, (0.3,)), (T0 + 170, (1.0,)), (NUCA0 + 6, (1.0,)), (NUCA0 + 16, (0.0,)), (NUCA0 + 80, (0.0,)), (N, (0.0,))]      # abre los ojos para contestar a Jerry (f346-356) y los vuelve a cerrar (f420-440)
for nm in ("ojo_izquierdo_alfred", "ojo_derecho_alfred"):
    ob = bpy.data.objects.get(nm)
    if ob and ob.data.shape_keys and "Closed" in ob.data.shape_keys.key_blocks:
        kb = ob.data.shape_keys.key_blocks["Closed"]; sk = ob.data.shape_keys
        if sk.animation_data: sk.animation_data.action = None
        for f in range(1, N + 1):
            v = max(blink_curve(f) * (1.0 if (f < T0 + 105 or f > 400) else 0.0), wp_eval(SLEEP, f)[0])
            if f % 2 == 1 or blink_curve(f) > 0 or f in (T0 + 105, T0 + 118, T0 + 140, T0 + 170): kb.value = v; kb.keyframe_insert("value", frame=f)
JSLEEP = [(1, (0.0,)), (SLEEP_J0, (0.0,)), (SLEEP_J0 + 26, (1.0,)), (JR_SHAKE[0] - 4, (1.0,)), (JR_SHAKE[0], (0.15,)), (JR_SHAKE[2], (0.15,)), (JR_SHAKE[2] + 8, (1.0,)), (N, (1.0,))]
for nm in ("ojo_izquierdo_jerry", "ojo_derecho_jerry", "pupila_izquierda_jerry", "pupila_derecha_jerry"):
    ob = bpy.data.objects.get(nm)
    if ob and ob.data.shape_keys and "Closed" in ob.data.shape_keys.key_blocks:
        kb = ob.data.shape_keys.key_blocks["Closed"]; sk = ob.data.shape_keys
        if sk.animation_data: sk.animation_data.action = None
        for f in range(1, N + 1):
            if f % 4 == 1 or SLEEP_J0 - 4 <= f <= SLEEP_J0 + 30 or JR_SHAKE[0] - 6 <= f <= JR_SHAKE[2] + 10: kb.value = wp_eval(JSLEEP, f)[0]; kb.keyframe_insert("value", frame=f)
sc.frame_start = 1; sc.frame_end = N; sc.frame_set(1)
print(f"Parte 3: sentarse en el refugio, {len(frames)} muestras, f1-f{N}")
