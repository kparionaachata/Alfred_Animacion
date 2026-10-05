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
N = 1004
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
    x += TORCH_DX * (ss((k - 533) / 12.0) - ss((k - 548) / 12.0))                                              # se acerca al muro oeste para poner la antorcha y vuelve
    x += SCOOT_DX * ss((k - SCOOT0) / float(SCOOT_D))                                                          # avanza de rodillas 20 cm hacia la mesa para alcanzar las casillas lejanas de la rejilla
    sw = stand_w(k); y = -108.5 - 0.09 * u; x = x * (1 - sw) + STAND_X * sw; y = y * (1 - sw) + STAND_Y * sw
    return (x, y, 14.0 - 1.0 * ss((k - FALL0) / float(FALL_D)), yaw)    # Alfred mira a +Y local: yaw +90 => mira al oeste (piernas hacia el oeste). Y final -108.59 (antes -108.3): se sienta 0.29 m mas hacia su IZQUIERDA (sur) para que el brazo derecho no atraviese el muro norte (cara interior y=-108.0)


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


# FILTROS ORGANICOS Y PARPADEO DE alfred_animation_studio (pedido de Kebyn; valores de su segmento 0 en el estudio, `scene.alfred_segs.segments[0].organic`): respiracion (Spine / Spine1 X y Z), micro-movimiento de la cabeza
# (Neck / face, ruido procesal), micro-escala (Spine1 Z), movimiento secundario de los codos (retardo) y suavizado de curvas; parpadeo = la "cortina" de 9 frames (`BLINK_SEQUENCE_BASE`) con 1 parpadeo centrado por tramo.
ORG = dict(br_amp=0.020, br_speed=0.010, br_phase=1.97, hs_amp=0.023, hs_speed=0.079, hs_seed=693, micro_amp=0.010, sec_lag=3.9, sec_damp=0.51, sm_passes=3, sm_factor=0.63)
BLINK_BASE = {1: 0.0, 2: 0.25, 3: 0.5, 4: 0.75, 5: 1.0, 6: 1.0, 7: 0.75, 8: 0.5, 9: 0.25}
BLINK_SEGS = [(1, 59), (60, 105), (106, 205), (206, 265), (266, 357), (358, 429), (430, 501), (502, 559), (560, 640), (641, 712)]          # un parpadeo por tramo de la historia (centrado, como el estudio)


def org_noise(f, freq, seed, dim=0):
    v = math.sin(f * freq * 1.3 + seed * 7.3 + dim * 3.7) + math.sin(f * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5 + math.sin(f * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25
    return v / 1.75


def organico(k, rot):
    a = ORG["br_amp"]; ph = k * ORG["br_speed"] * 2 * math.pi + ORG["br_phase"]
    for b in ("Spine_alfred", "Spine1_alfred"): rot[b][0] += a * math.sin(ph); rot[b][2] += a * 0.4 * math.sin(ph + 1.2)
    for ax in range(3):
        d = ORG["hs_amp"] * org_noise(k, ORG["hs_speed"], ORG["hs_seed"], ax)
        for b in ("Neck_alfred", "face_alfred"):
            if b in rot: rot[b][ax] += d


def micro_scale(k):
    return 1.0 + ORG["micro_amp"] * math.sin(k * ORG["br_speed"] * 2 * math.pi + ORG["br_phase"])


def blink_cortina(f):
    for a_, b_ in BLINK_SEGS:
        bs = int((a_ + (b_ - a_ + 1) * 0.5) - 4.5); bs = max(a_, min(bs, b_ - 9))
        if bs <= f < bs + 9: return BLINK_BASE[f - bs + 1]
    return 0.0


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
SCOOT0, SCOOT_D, SCOOT_DX = 626, 8, -0.20
KN0, KN1 = 502, 516                                                                    # de rodillas: 14 frames (f502-516)
KN_LEG = (0.0, -90.0); KN_HIPY = -0.40; KN_X = -95.55
KN_LEAN = [(KN0, (0.0,)), (509, (26.0,)), (KN1, (0.0,)), (533, (0.0,)), (541, (20.0,)), (548, (20.0,)), (556, (0.0,)), (563, (0.0,)), (569, (10.0,)), (572, (19.0,)), (574, (28.0,)), (576, (28.0,)), (579, (20.0,)), (592, (20.0,)), (599, (0.0,)), (628, (0.0,)), (638, (30.0,)), (684, (30.0,)), (692, (0.0,)), (713, (0.0,)), (721, (28.0,)), (725, (28.0,)), (729, (0.0,)), (731, (0.0,)), (739, (28.0,)), (743, (28.0,)), (747, (0.0,)), (756, (0.0,)), (763, (28.0,)), (767, (28.0,)), (772, (0.0,)), (785, (0.0,)), (789, (28.0,)), (793, (28.0,)), (798, (0.0,)), (814, (0.0,)), (818, (28.0,)), (828, (28.0,)), (834, (0.0,)), (905, (0.0,)), (926, (18.0,)), (958, (18.0,)), (962, (24.0,)), (966, (24.0,)), (976, (18.0,)), (990, (0.0,)), (N, (0.0,))]
KN_NECK = [(KN0, (0.0,)), (533, (0.0,)), (541, (8.0,)), (548, (8.0,)), (556, (0.0,)), (560, (0.0,)), (569, (10.0,)), (572, (18.0,)), (577, (14.0,)), (584, (0.0,)), (628, (0.0,)), (638, (12.0,)), (684, (12.0,)), (692, (0.0,)), (N, (0.0,))]
MESA_PATH = r"C:\Users\user\Desktop\Alfred_Animacion\bloques_dinamicos\mesa_de_crafteo_1.blend"
MESA_Q = {
    "TOP": (20, ((0.50234, 0.27152, 0.46489, 0.67662), (0.52007, -0.85413, 0.00000, 0.00000)), ((0.49558, 0.44918, -0.50998, -0.54088), (0.38387, -0.92339, 0.00000, 0.00000))),
    "REST": (0, ((0.38337, 0.91465, 0.09878, 0.08172), (0.81042, -0.58585, 0.00000, 0.00000)), ((0.26404, 0.94593, -0.16503, -0.09086), (0.71122, -0.70296, 0.00000, 0.00000))),
    "BACK": (0, ((0.48296, 0.83652, 0.12941, -0.22414), (0.86603, -0.50000, 0.00000, 0.00000)), ((0.49240, 0.85287, -0.08682, 0.15038), (0.90631, -0.42262, 0.00000, 0.00000))),
    "HI": (10, ((0.32349, 0.38855, 0.66484, 0.54988), (0.35089, -0.93642, 0.00000, 0.00000)), ((0.26757, -0.71929, 0.32035, 0.55534), (0.21901, -0.97572, 0.00000, 0.00000))),
    "MID": (19, ((0.26803, 0.47115, 0.68365, 0.48868), (0.44520, -0.89543, 0.00000, 0.00000)), ((0.17966, 0.66804, -0.65736, -0.29888), (0.30065, -0.95374, 0.00000, 0.00000))),
    "LO": (28, ((0.36931, 0.38838, 0.65448, 0.53332), (0.66113, -0.75027, 0.00000, 0.00000)), ((0.30430, 0.63476, -0.57376, -0.41868), (0.54069, -0.84122, 0.00000, 0.00000))),
}
TBK = [(506, "SIT"), (513, "REST"), (560, "REST"), (563, "BACK"), (564, "BACK"), (569, "HI"), (570, "HI"), (572, "MID"), (574, "LO"), (575, "LO"), (579, "TOP"), (N, "TOP")]   # brazos caidos -> rectos f506-513 (7 f); espera f516-524 (8 f); mesa f524-540 (16 f)
MESA_T = {"aparece": 563, "mano": 569, "baja0": 570, "suelo": 574, "fin": 576}
MESA_P0 = Vector((-95.40, -108.59, 14.75)); MESA_PC = Vector((-95.70, -108.59, 15.55)); MESA_S = 0.9                                                                                                  # escala de la mesa: 0.9 m cabe en la esquina sin tocar el muro oeste (x -97.0), el norte (y -108.0) ni la antorcha
MESA_H = Vector((-96.53, -108.47, 14.55)); MESA_F = Vector((-96.53, -108.47, 13.9946))


def kn_w(k):
    return ss((k - KN0) / float(KN1 - KN0))


# POSES DE LOS BRAZOS DE LA MESA, SIN GIRO Z (orden de Kebyn: "no rotes en Z"): (X, Y, Z) en grados de LeftUpArm / RightUpArm y X del codo. Hombro con X 90 (brazo colgando) y el balanceo atras / adelante en Y
# (verificado con la cinematica del rig: con X 90, Y positivo en el izquierdo / negativo en el derecho lleva la mano hacia atras (+x); el signo contrario, hacia delante). BACK = brazos rectos hacia atras (munecas a x -95.14);
# HI / MID / LO / TOP = brazos rectos hacia delante con las manos encima de la tapa de la mesa mientras baja (la altura de las munecas sigue la tapa: z 15.49, 15.2, 14.94, 14.94; resueltas con ik_brazos / fk).
MESA_E = {"REST": ((90, 0, 0), 0, (90, 0, 0), 0), "BACK": ((78.088, -224.3, 0.27287), (20.216, 2.0649, 90.389), (266.17, -35.4, 190.21), (7.8244, -2.384, -111.53)), "HI": ((90, -128.5, 0), 0, (90, 128.0, 0), 0), "MID": ((90, -120.0, 0), 0, (90, 121.0, 0), 0),
          "LO": ((90, -114.5, 0), 0, (90, 117.0, 0), 0), "TOP": ((90, -106.0, 0), 0, (90, 108.5, 0), 0), "HOLD": ((90, -112.0, 0), 0, (90, 112.0, 0), 0), "TW": ((90, -112.0, 0), 0, (164.0, 108.1, 0), (-87.0, 0, 0)), "LT": ((195.2, -13.4, 0), (-118.8, 0, 0), (90, 112.0, 0), 0),
          "DU": ((76.9, 7.9, 118.8), (-94.7, 0, 0), (76.2, -6.5, -116.5), (-96.3, 0, 0)), "DD": ((66.3, 13.9, 126.9), (-32.4, 0, 0), (72.5, -13.6, -128.6), (-43.2, 0, 0)),
          "SW0": ((170.1, -122.0, 0), (-57.2, 0, 0), (90, 112.0, 0), 0), "SW1": ((157.9, -114.4, 0), (-107.0, 0, 0), (90, 112.0, 0), 0),
          "PLA": ((138.5, -43.7, 0), (-75.8, 105.1, 15.8), (90, 112.0, 0), 0), "PLKC": ((90, -112.0, 0), 0, (95.9, 66.0, 0), (-0.5, -11.3, -111.5)), "PLKB": ((90, -112.0, 0), 0, (144.2, 59.1, 0), (0.0, 3.9, -101.9)),
          "PLC": ((130.3, -126.1, 0), (0, 0, -0.9), (90, 112.0, 0), 0), "PS1": ((90, -112.0, 0), 0, (117.6, 86.5, 0), (-6.2, -2.5, -70.2)), "PS2": ((90, -112.0, 0), 0, (149.1, 60.0, 0), (-0.8, 11.0, -106.5))}
_EU = {}


def _eu_key(side):
    """Euler XYZ (rad) del hombro y X del codo de cada pose (MESA_E; SIT sale de SIT_Q en la rama de menor torsion Z), con los angulos a la vuelta mas cercana a la pose anterior."""
    if side in _EU: return _EU[side]
    si = 0 if side == "Left" else 2; out = {}; e = Quaternion(SIT_Q[side][0]).to_euler('XYZ'); c = (e.x, e.y, e.z); c2 = (e.x + math.pi, math.pi - e.y, e.z + math.pi)
    cc = [[((a_ + math.pi) % (2 * math.pi)) - math.pi for a_ in q] for q in (c, c2)]; cc = min(cc, key=lambda q: 3 * abs(q[2]) + 0.1 * abs(q[0]))
    xe = 2 * math.atan2(Quaternion(SIT_Q[side][1]).x, Quaternion(SIT_Q[side][1]).w); out["SIT"] = (cc, (xe, 0.0, 0.0))
    for nm, v in MESA_E.items(): ev_ = v[si + 1]; out[nm] = ([math.radians(a_) for a_ in v[si]], tuple(math.radians(a_) for a_ in (ev_ if isinstance(ev_, tuple) else (ev_, 0.0, 0.0))))
    if side == "Right":                                                                                              # orden de Kebyn: el brazo derecho tambien rota en +Y. En este rig (espejado) eso es la MISMA postura escrita como (X + 180, 180 - Y, Z + 180): X 270, Z 180 fijos y Y positivo
        out = {nm: (e_[0] if nm == "BACK" else [e_[0][0] + math.pi, math.pi - e_[0][1], e_[0][2] + math.pi], e_[1]) for nm, e_ in out.items()}            # la pose BACK ya viene escrita por Kebyn en esta rama (valores de su Blender)
    _EU[side] = out; return out


# TRAER OBJETOS (pedido de Kebyn): con la mesa ya puesta, Alfred lleva el brazo DERECHO a la espalda (BACK, f556-568), saca DOS STICKS (objetos/vanilla/stick/stick.blend) y los trae en la mano hasta delante, por encima de
# la mesa (HOLD, f571-583: brazo recto hacia delante, Z = 0 como el resto); luego hace lo mismo con el IZQUIERDO (f585-612) y trae un BLOQUE DE PIEDRA (bloques_dinamicos/cobblestone.blend). Los objetos aparecen en la mano
# al llegar a la espalda (escala 0 -> 1 en 3 frames, como sacados del inventario) y viajan pegados al antebrazo (hueso elbow, en la muneca).
TBK_X = {"Right": [(592, "TOP"), (598, "BACK"), (599, "BACK"), (607, "HOLD"), (643, "HOLD"), (651, "PS1"), (655, "PS1"), (659, "PS2"), (663, "PS2"), (669, "HOLD"), (677, "HOLD"), (682, "PS1"), (684, "PS1"), (693, "BACK"), (695, "BACK"), (704, "REST"), (724, "REST"), (730, "BACK"), (731, "BACK"), (739, "PLKC"), (743, "PLKC"), (749, "REST"), (755, "BACK"), (756, "BACK"), (763, "PLKB"), (767, "PLKB"), (773, "REST"), (781, "REST"), (789, "PLKC"), (792, "PLKC"), (800, "BACK"), (803, "BACK"), (812, "REST"), (906, "REST"), (912, "BACK"), (915, "BACK"), (923, "DU"), (930, "DU"), (934, "DD"), (937, "DD"), (944, "DU"), (948, "DD"), (951, "DD"), (958, "DU"), (962, "DD"), (966, "DD"), (976, "DU"), (N, "DU")],
         "Left": [(609, "TOP"), (615, "BACK"), (616, "BACK"), (624, "HOLD"), (630, "HOLD"), (639, "PLC"), (643, "PLC"), (653, "REST"), (706, "REST"), (712, "BACK"), (713, "BACK"), (721, "PLA"), (725, "PLA"), (733, "REST"), (808, "REST"), (816, "SW0"), (818, "SW0"), (824, "SW1"), (826, "SW1"), (834, "REST"), (906, "REST"), (918, "DU"), (930, "DU"), (934, "DD"), (937, "DD"), (944, "DU"), (948, "DD"), (951, "DD"), (958, "DU"), (962, "DD"), (966, "DD"), (976, "DU"), (N, "DU")]}
ITEM_SRC = {"stick": r"C:\Users\user\Desktop\Alfred_Animacion\objetos\vanilla\stick\stick.blend", "cobblestone": r"C:\Users\user\Desktop\Alfred_Animacion\bloques_dinamicos\cobblestone.blend"}
ITEM_S = {"stick": 0.6, "cobblestone": 0.35}                                                        # escala de cada objeto en la mano (el bloque de 1 m no cabe en un puno)
ITEMS = [("stick_1", "stick", "Right", 562, 0.0, 0.0), ("stick_2", "stick", "Right", 562, 0.0, 0.0), ("cobblestone", "cobblestone", "Left", 579, 0.0, 0.0)]
# TRANSFORMACION FINAL EN LA MANO (valores de Blender dados por Kebyn, mundo, en HOLD): (ubicacion del origen, rotacion Euler XYZ en grados). Cada objeto se pega al antebrazo con el desplazamiento que reproduce exactamente estos valores en el ultimo frame.
# PONER LOS MATERIALES EN LA MESA para craftear una PALA DE PIEDRA (receta: bloque de piedra arriba, un stick en medio y otro abajo, en la columna central de la rejilla 3x3 de la tapa). Visto desde Alfred (mira al oeste) la fila de
# arriba es la LEJANA (oeste). Casillas (centro de la columna y = -108.47; separacion 0.19 m): lejana x -96.72 (piedra), central x -96.53 (stick_1), cercana x -96.34 (stick_2). Alfred avanza 20 cm de rodillas (f614-622) y se inclina 30 grados;
# la izquierda deja la piedra (f629), la derecha los dos sticks (f641 y f649); al soltarlos caen 4 frames (~17 cm: las manos las sueltan sobre la rejilla) a la casilla y se reducen al tamano de la casilla (piedra 0.19, sticks 0.22). Poses PLC / PS1 / PS2 resueltas contra la posicion del objeto en la mano.
ITEM_PLACE = {"cobblestone": (641, (-96.72, -108.47, 14.90), (0.0, 0.0, 0.0), 0.19), "stick_1": (653, (-96.53, -108.47, 14.905), (0.0, 0.0, 20.0), 0.22), "stick_2": (661, (-96.34, -108.47, 14.905), (0.0, 0.0, -15.0), 0.22)}
ITEM_REF = 625
# CRAFTEO: tras dejar el ultimo stick (f625 + 4 de caida) los materiales desaparecen (f634-636, escala -> 0) y en f636-641 aparece encima de la mesa la PALA DE PIEDRA (objetos/vanilla/stone_shovel/stone_shovel.blend, plano de 0.81 m
# como los sticks) en el centro de la tapa, con Elastic In-Out en la escala (0 -> 0.6, rebasa y se asienta).
ITEM_VANISH = 670
SHOVEL_SRC = r"C:\Users\user\Desktop\Alfred_Animacion\objetos\vanilla\stone_shovel\stone_shovel.blend"; SHOVEL_AT = 672; SHOVEL_GRAB = 684; SHOVEL_MOUNT = 695; SHOVEL_POS = (-96.53, -108.47, 14.915); SHOVEL_S = 0.6                                                                                          # frame de referencia de ITEM_HOLD (ambos brazos en HOLD, antes de avanzar)
ITEM_HOLD = {"stick_1": ((-96.317, -108.29, 15.372), (106.65, -45.118, -13.218)), "stick_2": ((-96.326, -108.29, 15.346), (93.86, -24.347, -0.008386)), "cobblestone": ((-96.358, -109.11, 15.387), (-89.483, 110.68, 0.080644))}


# SEGUNDA ANTORCHA (pedido de Kebyn): ANTES de colocar la mesa, Alfred lleva la mano derecha a la espalda (f524-530), saca una antorcha nueva (copia de la del refugio, `antorcha_2`; aparece f530-533) y se acerca de rodillas 45 cm al muro
# oeste (f533-545) para ponerla en (-97, -108.5, 15.1) con rotacion Y 20 grados (f545; se asienta 3 frames); luego vuelve a su sitio (f548-560). Pose TW del brazo derecho resuelta con ik_brazos (X 164 / Y 108 / Z 0, codo -87).
TORCH_FINAL = ((-97.0, -108.5, 15.1), (0.0, 20.0, 0.0)); TORCH_PICK = 530; TORCH_PLACE = 545; TORCH_DX = -0.45
TBK_PRE_L = [(506, "SIT"), (513, "REST"), (524, "REST"), (531, "LT"), (552, "LT"), (559, "REST")]                    # mientras acerca la antorcha al muro, la mano izquierda descansa sobre el muslo (colgando chocaria con la antorcha central en (-96, -109))
TBK_PRE_R = [(506, "SIT"), (513, "REST"), (524, "REST"), (530, "BACK"), (533, "BACK"), (541, "TW"), (548, "TW"), (556, "REST")]


def tab_eul(side, k, lru):
    """([rx, ry, rz] del hombro, rx del codo, ubicacion): los angulos Euler de UpArm / elbow entre las poses MESA_Q, interpolados canal por canal (los keyframes quedan limpios; la espalda y el tiron al frente llevan Elastic In-Out al 30 %%)."""
    EU = _eu_key(side); locg = (STUDIO_LOC[0] * (-1 if side == "Left" else 1), STUDIO_LOC[1], STUDIO_LOC[2]); wl = ss((k - TBK[0][0]) / 10.0); lc = tuple(l * (1 - wl) + g * wl for l, g in zip(lru, locg))
    keys = ((TBK_PRE_R if side == "Right" else TBK_PRE_L) + TBK[2:-1]) + TBK_X[side]
    for (f0, a), (f1, b) in zip(keys[:-1], keys[1:]):
        if f0 <= k < f1:
            x = (k - f0) / float(f1 - f0); u = (0.3 * ela(x) + 0.7 * ss(x)) if (a, b) in (("REST", "BACK"), ("BACK", "HI"), ("TOP", "BACK"), ("BACK", "HOLD"), ("SW0", "SW1")) else ss(x)
            A_, B_ = EU[a], EU[b]; return [A_[0][q] + (B_[0][q] - A_[0][q]) * u for q in range(3)], [A_[1][q] + (B_[1][q] - A_[1][q]) * u for q in range(3)], lc
    E_ = EU[keys[-1][1]]; return list(E_[0]), list(E_[1]), lc


def tab_arm(side, k, lru):
    e, x, lc = tab_eul(side, k, lru); return Euler(e, 'XYZ').to_quaternion(), Euler(x, 'XYZ').to_quaternion(), lc


# CAVAR (pedido de Kebyn): Alfred se levanta (f893-905, vuelve a la pose de pie y se coloca en el centro-este de la casilla de suelo x -96..-95, y -109..-108), saca la pala de la espalda (BACK f912-915; la pala pasa de la espalda a la mano en
# 3 frames), la levanta y da 3 paladas al bloque de cesped de debajo (DU -> DD: f930-937, f944-951, f958-966). A la 3.a (f962) el bloque se rompe: la tapa de cesped (`lid_cesped_cavar`, el quad de a.001 en (-95.5, -108.5, 14.0)) se oculta y queda el
# pozo (`pozo_tierra`, caja de tierra abierta por arriba z 13..14); Alfred baja 1 en Z (f962-968) y sale el bloque de tierra (`tierra_item`): flota subiendo, gira y rebota suave con escala 0.25 hasta f988 y entonces es absorbido por Alfred (f988-995,
# vuela hacia su pecho encogiendose), como al cavar en el juego. Poses DU / DD (v2, corregidas): brazos naturales de cavar: el hombro cuelga (X ~75) y se tuerce en Z (+-120) para que el codo doble HACIA DELANTE, codos pegados bajo los hombros (z 15.04) y antebrazos hacia delante-dentro hasta las manos en la pala (U: z 15.05; D: z 14.5); torso 18 / 24 grados.
ASTAND0, ASTAND_D, STAND_X, STAND_Y = 893, 12, -95.4, -108.5
FALL0, FALL_D = 962, 6; SHOVEL_UNMOUNT = 915; DIRT_SPAWN = 962; DIRT_ABSORB = 988


def stand_w(k):
    return ss((k - ASTAND0) / float(ASTAND_D))


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
    sw = stand_w(k)                                                                                             # de pie: todos los huesos (menos los brazos) vuelven a cero
    if sw > 0:
        for b in rot:
            if "UpArm" in b or "elbow" in b: continue
            rot[b] = [v * (1 - sw) for v in rot[b]]
    h = loc.get("Hips_alfred", [0.0, 0.0, 0.0]); loc["Hips_alfred"] = [h[0] * (1 - w), (h[1] * (1 - w) + KN_HIPY * w) * (1 - sw), h[2] * (1 - w)]
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
                e_, x_, l_ = tab_eul(side, k, lru); prev[ua], prev[el] = Euler(e_, 'XYZ'), Euler(x_, 'XYZ'); ARM_TAB[(side, k)] = (list(e_), list(x_), list(l_)); continue
            qru, qre = Euler(rot[ua], 'XYZ').to_quaternion(), Euler(rot[el], 'XYZ').to_quaternion(); st = arm_state(side, k, qru, qre, lru)
            if st is None: st = (qru, qre, lru)
            eu = st[0].to_euler('XYZ', prev[ua]); ee = st[1].to_euler('XYZ', prev[el]); prev[ua], prev[el] = eu, ee
            ARM_TAB[(side, k)] = (list(eu), list(ee), list(st[2]))
    pin = set()                                                                                                       # frames de la pose BACK de Kebyn: los codos quedan EXACTOS ahi
    for lst in (TBK, TBK_PRE_R, TBK_PRE_L, TBK_X["Right"], TBK_X["Left"]):
        for (f0, a_), (f1, b_) in zip(lst[:-1], lst[1:]):
            if a_ == "BACK" and b_ == "BACK": pin |= set(range(f0, f1 + 1))
    lag = int(round(ORG["sec_lag"])); dmp = ORG["sec_damp"]; ks_ = [kk for kk in range(kstart, N + 1)]
    for side in ("Right", "Left"):
        for ax in range(3):
            vals = [ARM_TAB[(side, kk)][1][ax] for kk in ks_]; n_ = len(vals)
            for i, kk in enumerate(ks_):
                if kk in pin: continue
                dl = vals[max(0, i - lag)] * (1 - dmp) + vals[i] * dmp; ARM_TAB[(side, kk)][1][ax] = vals[i] * 0.7 + dl * 0.3                    # 70 % original + 30 % retrasado (estudio)


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
    organico(k, rot)
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


SMOOTH = {}


def alfred_final(k):
    """pose de Alfred en k: las curvas de TODOS los huesos menos los brazos se suavizan (sm_passes pasadas del filtro [0.25, 0.5, 0.25] mezclado al sm_factor, como `_gaussian_smooth` del estudio); los brazos conservan sus valores
    exactos (poses dadas por Kebyn)."""
    if not SMOOTH:
        raw = {kk: alfred_at(kk) for kk in range(1, N + 1)}; brazos = lambda b: "UpArm" in b or "elbow" in b
        for kk in raw: SMOOTH[kk] = ({b: list(v) for b, v in raw[kk][0].items()}, {b: list(v) for b, v in raw[kk][1].items()})
        for ci, bones in ((0, raw[1][0].keys()), (1, raw[1][1].keys())):
            for b in bones:
                if brazos(b): continue
                for ax in range(3):
                    vals = [raw[kk][ci].get(b, (0.0, 0.0, 0.0))[ax] for kk in range(1, N + 1)]
                    for _ in range(ORG["sm_passes"]):
                        out = vals[:]
                        for i in range(1, len(vals) - 1): out[i] = vals[i] * (1 - ORG["sm_factor"]) + (vals[i - 1] * 0.25 + vals[i] * 0.5 + vals[i + 1] * 0.25) * ORG["sm_factor"]
                        vals = out
                    for kk in range(1, N + 1):
                        if b in SMOOTH[kk][ci]: SMOOTH[kk][ci][b][ax] = vals[kk - 1]
    return SMOOTH[k]


def apply_alfred(k, key=True):
    rot, loc = alfred_final(k)
    x, y, z, rz = root_at(k)
    O.location = (x, y, z); O.rotation_euler = (0, 0, TH + D(rz))
    for b, v in rot.items(): PA[b].rotation_euler = v
    for b, v in loc.items(): PA[b].location = v
    if k >= REF0: PA["Hips_alfred"].location = (loc["Hips_alfred"][0], loc["Hips_alfred"][1] + HYK[max(q for q in HYK if q <= k)] * (1 - kn_w(k)) + KZ.get(k, 0.0), loc["Hips_alfred"][2])
    PA["Spine1_alfred"].scale = (1.0, 1.0, micro_scale(k))
    if not key: return
    PA["Spine1_alfred"].keyframe_insert("scale", frame=k)
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
    if k >= LOOK2_UP - 16: k = min(k - (LOOK2_UP - LOOK_UP0), 340)                                                  # segundo giro hacia Alfred: la misma tabla de contragiro de la pata derecha, desplazada y mantenida en su meseta
    ks = sorted(PATA_R)
    if k <= ks[0]: return list(PATA_R[ks[0]])
    if k >= ks[-1]: return list(PATA_R[ks[-1]])
    i = max(q for q in range(len(ks)) if ks[q] <= k); a = ks[i]; b = ks[i + 1]; u = (k - a) / float(b - a)
    return [PATA_R[a][j] + (PATA_R[b][j] - PATA_R[a][j]) * u for j in range(6)]


# REACCION DE JERRY A LO QUE LE CAE ENCIMA (pedido de Kebyn): cada herramienta que aterriza en su lomo (f466 / 479 / 492) le da un respingo (JR_HIT: lomo, orejas, pata y cola, con rebote que se apaga); tras la tercera
# abre un poco los ojos y se sacude: levanta el cuerpo f497-510 (rueda ~35 grados de su costado hacia arriba, levanta la cabeza, patea y tiembla) y lanza las herramientas, que salen disparadas del lomo (JR_REL) en un vuelo
# parabolico con giro y caen apiladas en el rincon sureste, junto al muro este (JR_PILE), libre de la mesa, de la antorcha y de Alfred. Despues vuelve a dormir.
JR_HIT = (466, 479, 492, 829, 832); JR_SHAKE = (497, 502, 510); JR_ROLL = 35.0
JR_REL = {"stone_axe": 503, "wooden_axe": 504, "wooden_pickaxe": 505}; JR_FLY = 12
JR_PILE = {"stone_axe": ((-95.26, -109.62), 80.0), "wooden_axe": ((-95.27, -109.58), 100.0), "wooden_pickaxe": ((-95.25, -109.64), 90.0)}


# LA PATA IZQUIERDA (la de arriba) BARRE LAS HERRAMIENTAS (pedido de Kebyn): front_shoulder.L (X, Z), front_thigh.L (X, Z) y front_shin.L (X), en grados SUMADOS a la postura de dormir. Poses resueltas en Blender contra la punta de la pata
# (front_toe.L): C = levanta la pata por encima del lomo (-96.40, -109.55, 14.90), A = la echa atras por el lado sur de las herramientas (-96.35, -109.78, 14.72), B = barrido hacia el norte a ras del lomo (-96.47, -109.37, 14.50).
JR_PAW = [(494, (0.0, 0.0, 0.0, 0.0, 0.0)), (498, (15.0, 77.9, -63.4, 21.0, 2.3)), (501, (-15.9, 49.7, -60.8, 26.1, 1.4)), (504, (-30.2, 0.8, 80.2, -16.1, 80.2)), (507, (-30.2, 0.8, 80.2, -16.1, 80.2)), (513, (0.0, 0.0, 0.0, 0.0, 0.0))]


# JERRY SE SACUDE LOS 5 SLABS CON LA PATA front_shoulder.L Y VUELVE A MIRAR A ALFRED (pedido de Kebyn): con los slabs ya sobre el lomo (f829-833) levanta la pata izquierda (f838), la echa atras (f841) y barre hacia el norte (f844-847),
# con el mismo gesto que uso para quitarse las herramientas (poses C / A / B); los slabs salen del lomo uno por frame (f844-848, vuelo de 8 frames con salto y giro) y quedan en fila en el suelo entre su lomo y la mesa (x -96.85 .. -96.17,
# y -109.015: franja libre de 19 cm, junto a la antorcha). Despues gira el cuerpo y la cabeza hacia Alfred como en f284-304 (mismo gesto LOOKA, f852-876), abre los ojos y se queda mirandolo.
JR_PAW2 = [(834, (0.0, 0.0, 0.0, 0.0, 0.0)), (838, (15.0, 77.9, -63.4, 21.0, 2.3)), (841, (-15.9, 49.7, -60.8, 26.1, 1.4)), (844, (-30.2, 0.8, 80.2, -16.1, 80.2)), (847, (-30.2, 0.8, 80.2, -16.1, 80.2)), (853, (0.0, 0.0, 0.0, 0.0, 0.0))]
JR_SHAKE2 = (838, 843, 850); LOOK2_UP = 852
SLAB_OFF = {1: 844, 2: 845, 3: 846, 4: 847, 5: 848}; SLAB_OFF_FLY = 8
SLAB_FLOOR = {1: (-96.85, -109.015, 0.0), 2: (-96.68, -109.015, 6.0), 3: (-96.51, -109.015, -5.0), 4: (-96.34, -109.015, 4.0), 5: (-96.17, -109.015, -7.0)}


def jr_hit(k):
    return sum(math.exp(-(k - h) / 4.0) * math.cos((k - h) * 0.9) for h in JR_HIT if k >= h)


def jr_shake(k):
    """(envolvente 0..1 del sacudon, temblor -1..1)."""
    a, b, c = JR_SHAKE; env = ss((k - a) / float(b - a)) * (1 - ss((k - b) / float(c - b))); tre = math.sin((k - a) * 1.7) * min(1.0, env * 3.0) * (1.0 if a <= k <= c else 0.0)
    a2, b2, c2 = JR_SHAKE2; env2 = ss((k - a2) / float(b2 - a2)) * (1 - ss((k - b2) / float(c2 - b2))); tre2 = math.sin((k - a2) * 1.7) * min(1.0, env2 * 3.0) * (1.0 if a2 <= k <= c2 else 0.0)
    return env + 0.6 * env2, tre + 0.6 * tre2


def la_body(k):
    return min(1.0, ss((k - LOOK_UP0) / 20.0) * (1 - ss((k - LOOK_DN0 - 6) / 22.0)) + ss((k - LOOK2_UP) / 20.0))


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
    la_h = min(1.0, ss((k - LOOK_UP0 - 6) / 18.0) * (1 - ss((k - LOOK_DN0) / 18.0)) + ss((k - LOOK2_UP - 6) / 18.0))           # CABEZA: va un poco detras al girar y se adelanta al volver (asi nunca se mete en el pecho: medido contra la malla)
    for b_, ax_, v_ in LOOKA:
        w_ = la_h if b_.startswith("scull") else la_b
        if w_ > 0: out[b_][ax_] += w_ * v_
    pd_ = pata_delta(k)
    for j_ in range(3): out["front_shoulder.R"][j_] += pd_[j_]                      # contragiro del hombro derecho (la pata se queda en el suelo)
    out["spine_5"][0] += lie * breathe(k, 1.8, 96.0, 0.3); out["spine_3"][0] += lie * breathe(k, 1.2, 96.0, 0.7)                                                       # respiracion lenta y profunda al dormir
    tw = math.exp(-((k - TWITCH[0]) / 3.0) ** 2) + 0.7 * math.exp(-((k - TWITCH[1]) / 3.0) ** 2); out["front_foot.R"][0] += lie * 9 * tw; out["foot.R"][0] += lie * 6 * tw; out["ear.L"][0] += lie * 8 * tw  # suena: tiembla una pata
    ht_ = jr_hit(k); env_, tre_ = jr_shake(k)
    out["spine_5"][0] += 5.0 * ht_; out["spine_3"][0] += 4.0 * ht_; out["ear.R"][0] += 16 * ht_; out["ear.L"][0] += -12 * ht_; out["front_foot.R"][0] += 8 * ht_; out["tail_1"][2] += 10 * ht_
    pw_ = [a_ + b_ for a_, b_ in zip(wp_eval(JR_PAW, k), wp_eval(JR_PAW2, k))]
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
# SLABS TIRADOS A JERRY (pedido de Kebyn): la mano izquierda barre la mesa de norte a sur (SW0 -> SW1, f816-826) y manda los 5 slabs restantes encima de Jerry (salen f819-822, vuelo de 10 frames con salto y giro, aterrizan sobre su lomo
# -altura medida con un rayo contra sus mallas- y viajan pegados a su hueso spine_3). El sexto slab se lo guarda la mano derecha (lo coge f791, lo lleva a la espalda f800-803 y se guarda: escala -> 0 f802-805).
SLAB_THROW = {1: (822, (-96.45, -109.40), 20.0), 2: (820, (-96.25, -109.50), 75.0), 3: (819, (-96.05, -109.45), 130.0), 4: (822, (-95.85, -109.50), 40.0), 5: (820, (-95.65, -109.50), 100.0)}; SLAB_FLY = 10; SLAB_REL = {}
for si_, (la_, (lx_, ly_), yw_) in SLAB_THROW.items():
    kL_ = la_ + SLAB_FLY; pose_jerry(kL_); bpy.context.view_layer.update(); zj_ = lomo_jerry(lx_, ly_)
    SLAB_REL[si_] = (zj_, MJ[kL_].inverted() @ (Matrix.Translation((lx_, ly_, zj_)) @ Matrix.Rotation(D(yw_), 4, 'Z')))
for k in frames:
    apply_alfred(k); apply_jerry(k)
for tn in TOOLS:
    t_ = bpy.data.objects[tn]; prev = None
    for k in frames:
        loc, q, sc_ = TK[tn][k]
        if prev is not None and q.dot(prev) < 0: q = -q
        prev = q; t_.location = loc; t_.rotation_quaternion = q; t_.scale = sc_
        t_.keyframe_insert("location", frame=k); t_.keyframe_insert("rotation_quaternion", frame=k); t_.keyframe_insert("scale", frame=k)
# OBJETOS EN LA MANO (sticks / bloque de piedra): se importan una sola vez a la coleccion `objetos_mano`; cada frame se pegan a la muneca (cola del hueso elbow) con la rotacion del antebrazo
ITEM_REL = {}
_colo = bpy.data.collections.get("objetos_mano") or bpy.data.collections.new("objetos_mano")
if _colo.name not in sc.collection.children: sc.collection.children.link(_colo)
for nm_, src_, sd_, pick_, ang_, dx_ in ITEMS:
    ob_ = bpy.data.objects.get(nm_)
    if ob_ is None:
        base_ = bpy.data.objects.get(src_)
        if base_ is None:
            with bpy.data.libraries.load(ITEM_SRC[src_], link=False) as (_s2, _d2): _d2.objects = [src_]
            base_ = bpy.data.objects[src_]
        if nm_ in (src_, "stick_1"):
            ob_ = base_; ob_.name = nm_
        else: ob_ = bpy.data.objects["stick_1"].copy() if src_ == "stick" else base_.copy(); ob_.name = nm_
    for c_ in list(ob_.users_collection): c_.objects.unlink(ob_)
    _colo.objects.link(ob_)
    if ob_.parent: ob_.parent = None
    if ob_.animation_data: ob_.animation_data_clear()
    ob_.rotation_mode = 'QUATERNION'; Lh_ = PA[sd_ + "elbow_alfred"].bone.length; cl_ = sum((Vector(c) for c in ob_.bound_box), Vector()) / 8.0; sci_ = ITEM_S[src_]
    Mt_ = Matrix.LocRotScale(Vector(ITEM_HOLD[nm_][0]), Euler([D(a_) for a_ in ITEM_HOLD[nm_][1]], 'XYZ').to_quaternion(), Vector((1, 1, 1))); Rr_ = MH[ITEM_REF][sd_].inverted() @ Mt_; prev_ = None; car_ = None
    for k in frames:
        Mi_ = MH[k][sd_] @ Rr_; qi_ = Mi_.to_quaternion(); pop_ = max(0.001, ss((k - pick_) / 3.0)) * sci_
        if prev_ is not None and qi_.dot(prev_) < 0: qi_ = -qi_
        pr_, ps_, pe_, pz_ = ITEM_PLACE[nm_]
        if k == pr_: car_ = (Mi_.translation.copy(), qi_.copy(), pop_)
        if k > pr_:                                                                                         # soltado: se asienta en la casilla (ubicacion, giro y tamano)
            uu_ = ss((k - pr_) / 4.0); qs_ = Euler([D(a_) for a_ in pe_], 'XYZ').to_quaternion(); qi_ = car_[1].slerp(qs_, uu_); pop_ = car_[2] + (pz_ - car_[2]) * uu_
            Mi_ = Matrix.Translation(car_[0].lerp(Vector(ps_), uu_)) @ qi_.to_matrix().to_4x4()
        if k > ITEM_VANISH: pop_ = max(0.001, pop_ * (1 - ss((k - ITEM_VANISH) / 2.0)))
        ITEM_REL[nm_] = Rr_
        prev_ = qi_; ob_.location = Mi_.translation; ob_.rotation_quaternion = qi_; ob_.scale = (pop_, pop_, pop_)
        for dp_ in ("location", "rotation_quaternion", "scale"): ob_.keyframe_insert(dp_, frame=k)
# LA SEGUNDA ANTORCHA: copia de la jerarquia `antorcha_1.001` (vacio + malla + llama + humo + luz) a la coleccion `antorcha_2`; la luz se enciende al sacarla
if bpy.data.objects.get("antorcha_2") is None:
    src_r = bpy.data.objects["antorcha_1.001"]; objs_ = [src_r] + list(src_r.children_recursive); mp_ = {}; col2_ = bpy.data.collections.new("antorcha_2"); sc.collection.children.link(col2_)
    for o_ in objs_:
        c_ = o_.copy()
        if o_.type == 'LIGHT': c_.data = o_.data.copy()
        c_.name = "antorcha_2" if o_ is src_r else o_.name + "_a2"; mp_[o_] = c_; col2_.objects.link(c_)
    for o_ in objs_:
        if o_.parent: mp_[o_].parent = mp_[o_.parent]; mp_[o_].matrix_parent_inverse = o_.matrix_parent_inverse.copy()
t2_ = bpy.data.objects["antorcha_2"]; t2_.rotation_mode = 'XYZ'
if t2_.animation_data: t2_.animation_data_clear()
Mtf_ = Matrix.LocRotScale(Vector(TORCH_FINAL[0]), Euler([D(a_) for a_ in TORCH_FINAL[1]], 'XYZ').to_quaternion(), Vector((1, 1, 1))); Rt_ = MH[TORCH_PLACE]["Right"].inverted() @ Mtf_; pq_ = None
for k in sorted(set([1] + [f for f in frames if f >= TORCH_PICK - 3])):
    pop_ = 0.001 if k < TORCH_PICK else max(0.001, ss((k - TORCH_PICK) / 3.0))
    Mh_ = MH[k]["Right"] @ Rt_; loc_, q_ = Mh_.translation, Mh_.to_quaternion()
    if k >= TORCH_PLACE: u_ = ss((k - TORCH_PLACE) / 3.0); loc_ = loc_.lerp(Mtf_.translation, u_); q_ = q_.slerp(Mtf_.to_quaternion(), u_)
    if k > TORCH_PLACE + 3: loc_, q_ = Mtf_.translation, Mtf_.to_quaternion()
    if pq_ is not None and q_.dot(pq_) < 0: q_ = -q_
    pq_ = q_; t2_.location = loc_; t2_.rotation_mode = 'QUATERNION'; t2_.rotation_quaternion = q_; t2_.scale = (pop_, pop_, pop_)
    for dp_ in ("location", "rotation_quaternion", "scale"): t2_.keyframe_insert(dp_, frame=k)
for o_ in t2_.children_recursive:                                                                           # la luz de la nueva antorcha solo existe desde que se saca
    if o_.type == 'LIGHT':
        if o_.data.animation_data: o_.data.animation_data_clear()
        e0_ = bpy.data.objects["torch1.light.002"].data.energy
        for f_, v_ in ((1, 0.0), (TORCH_PICK, 0.0), (TORCH_PICK + 3, e0_), (N, e0_)): o_.data.energy = v_; o_.data.keyframe_insert("energy", frame=f_)
# LA PALA DE PIEDRA (resultado del crafteo)
sh_ = bpy.data.objects.get("stone_shovel")
if sh_ is None:
    with bpy.data.libraries.load(SHOVEL_SRC, link=False) as (_s3, _d3): _d3.objects = ["stone_shovel"]
    sh_ = bpy.data.objects["stone_shovel"]
for c_ in list(sh_.users_collection): c_.objects.unlink(sh_)
_colo.objects.link(sh_)
if sh_.parent: sh_.parent = None
if sh_.animation_data: sh_.animation_data_clear()
sh_.rotation_mode = 'QUATERNION'; sh_.location = SHOVEL_POS; sh_.rotation_quaternion = (1, 0, 0, 0)
# LLEVARSELA A LA ESPALDA (pedido de Kebyn): con la mano derecha coge la pala de la mesa (f648, 3 frames de asentarse en el agarre de los sticks), la lleva a la espalda (BACK, f657-659) y se queda montada en la espalda en el lugar
# donde estaba su hacha de madera (la propiedad `rel_spine1` de `wooden_axe`, girada 90 grados en X: el plano de la pala va como la hoja plana del hacha), pegada al hueso Spine1 desde f659 (3 frames).
rax_ = bpy.data.objects["wooden_axe"]["rel_spine1"]; Relb_ = Matrix([rax_[i:i + 4] for i in range(0, 16, 4)]) @ Matrix.Rotation(math.pi / 2, 4, 'X'); prevq_ = None
for k in sorted(set([1] + [f for f in frames if f >= SHOVEL_AT - 3])):
    e_ = max(0.001, SHOVEL_S * ela((k - SHOVEL_AT) / 5.0)) if k > SHOVEL_AT else 0.001
    loc_, q_ = Vector(SHOVEL_POS), Quaternion((1, 0, 0, 0))
    if k >= SHOVEL_GRAB:
        Mh_ = MH[k]["Right"] @ ITEM_REL["stick_1"]; u_ = ss((k - SHOVEL_GRAB) / 3.0); loc_ = loc_.lerp(Mh_.translation, u_); q_ = q_.slerp(Mh_.to_quaternion(), u_)
    if k >= SHOVEL_MOUNT:
        Mh_ = MH[k]["Right"] @ ITEM_REL["stick_1"]; Mb_ = MS[k] @ Relb_; u_ = ss((k - SHOVEL_MOUNT) / 3.0); loc_ = Mh_.translation.lerp(Mb_.translation, u_); q_ = Mh_.to_quaternion().slerp(Mb_.to_quaternion(), u_)
    if k >= SHOVEL_UNMOUNT:
        Mh_ = MH[k]["Right"] @ ITEM_REL["stick_1"]; Mb_ = MS[k] @ Relb_; u_ = ss((k - SHOVEL_UNMOUNT) / 3.0); loc_ = Mb_.translation.lerp(Mh_.translation, u_); q_ = Mb_.to_quaternion().slerp(Mh_.to_quaternion(), u_)
    if prevq_ is not None and q_.dot(prevq_) < 0: q_ = -q_
    prevq_ = q_; sh_.location = loc_; sh_.rotation_quaternion = q_; sh_.scale = (e_, e_, e_)
    for dp_ in ("location", "rotation_quaternion", "scale"): sh_.keyframe_insert(dp_, frame=k)
# CRAFTEAR 6 SLABS (pedido de Kebyn, receta de la imagen: fila INFERIOR de la rejilla con 3 tablones de roble -> 6 slabs): Alfred saca de su espalda 3 `oak_planks` (bloque_de_tablones_de_roble.blend) y los pone en la fila de abajo
# (la mas cercana a el, x -96.34; columnas y -108.66 / -108.47 / -108.28). Izquierda: tablon 1 a la columna sur (BACK f712, suelta f723); derecha: tablon 2 a la columna norte (BACK f730, suelta f741) y tablon 3 a la central (BACK f755,
# suelta f765). Los tablones desaparecen (f772-774) y aparecen 6 `oak_planks_slab` (bloque_de_slab..., escala 0.19, 2 filas x 3 columnas sobre la tapa, uno por frame desde f776). Poses PLA / PLKC / PLKB resueltas contra la posicion del bloque en la mano.
BASE_SRC = r"C:\Users\user\Desktop\Alfred_Animacion\bloques_dinamicos"
PLANKS = [("plank_1", "Left", 712, 723, (-96.34, -108.66, 14.90)), ("plank_2", "Right", 730, 741, (-96.34, -108.28, 14.90)), ("plank_3", "Right", 755, 765, (-96.34, -108.47, 14.90))]
SLAB_POS = [(-96.60, -108.66), (-96.60, -108.47), (-96.60, -108.28), (-96.42, -108.66), (-96.42, -108.47), (-96.42, -108.28)]; PLANK_VANISH = 772; SLAB_AT = 776


def _cargar_obj(nombre, archivo, objeto):
    o_ = bpy.data.objects.get(nombre)
    if o_ is None:
        o_ = bpy.data.objects.get(objeto)
        if o_ is None or o_.users_scene or o_.name.startswith("oak_planks_refugio"):
            with bpy.data.libraries.load(os.path.join(BASE_SRC, archivo), link=False) as (_a, _b): _b.objects = [objeto]
            o_ = bpy.data.objects[objeto] if objeto in bpy.data.objects and not bpy.data.objects[objeto].users_scene else bpy.data.objects[objeto]
        else: pass
        if o_.name != nombre and not o_.users_scene: o_.name = nombre
    return o_


_colb = bpy.data.collections.get("crafteo_slabs") or bpy.data.collections.new("crafteo_slabs")
if _colb.name not in sc.collection.children: sc.collection.children.link(_colb)
RelLb_ = ITEM_REL["cobblestone"]; RelRb_ = MH[ITEM_REF]["Right"].inverted() @ Matrix.Translation(Vector((-96.317, -108.29, 15.372)))
plank0_ = bpy.data.objects.get("plank_1")
if plank0_ is None:
    plank0_ = bpy.data.objects.get("oak_planks")
    if plank0_ is None or plank0_.users_scene:
        with bpy.data.libraries.load(os.path.join(BASE_SRC, "bloque_de_tablones_de_roble.blend"), link=False) as (_a, _b): _b.objects = ["oak_planks"]
        plank0_ = bpy.data.objects["oak_planks"]
    plank0_.name = "plank_1"
slab0_ = bpy.data.objects.get("slab_1")
if slab0_ is None:
    slab0_ = bpy.data.objects.get("oak_planks_slab")
    if slab0_ is None or slab0_.users_scene:
        with bpy.data.libraries.load(os.path.join(BASE_SRC, "slab_de_tablones_de_roble.blend"), link=False) as (_a, _b): _b.objects = ["oak_planks_slab"]
        slab0_ = bpy.data.objects["oak_planks_slab"]
    slab0_.name = "slab_1"
for pl_, sd_, pick_, rel_, slot_ in PLANKS:
    ob_ = plank0_ if pl_ == "plank_1" else (bpy.data.objects.get(pl_) or plank0_.copy())
    ob_.name = pl_
    for c_ in list(ob_.users_collection): c_.objects.unlink(ob_)
    _colb.objects.link(ob_); ob_.parent = None
    if ob_.animation_data: ob_.animation_data_clear()
    ob_.rotation_mode = 'QUATERNION'; Rr_ = RelLb_ if sd_ == "Left" else RelRb_; car_ = None; prev_ = None
    for k in frames:
        Mi_ = MH[k][sd_] @ Rr_; qi_ = Mi_.to_quaternion(); pop_ = max(0.001, ss((k - pick_) / 3.0)) * 0.35
        if k == rel_: car_ = (Mi_.translation.copy(), qi_.copy(), pop_)
        if k > rel_:
            uu_ = ss((k - rel_) / 4.0); qi_ = car_[1].slerp(Quaternion((1, 0, 0, 0)), uu_); pop_ = car_[2] + (0.19 - car_[2]) * uu_; Mi_ = Matrix.Translation(car_[0].lerp(Vector(slot_), uu_)) @ qi_.to_matrix().to_4x4()
        if k > PLANK_VANISH: pop_ = max(0.001, pop_ * (1 - ss((k - PLANK_VANISH) / 2.0)))
        if prev_ is not None and qi_.dot(prev_) < 0: qi_ = -qi_
        prev_ = qi_; ob_.location = Mi_.translation; ob_.rotation_quaternion = qi_; ob_.scale = (pop_, pop_, pop_)
        for dp_ in ("location", "rotation_quaternion", "scale"): ob_.keyframe_insert(dp_, frame=k)
for i_ in range(6):
    nm_ = "slab_%d" % (i_ + 1); ob_ = slab0_ if i_ == 0 else (bpy.data.objects.get(nm_) or slab0_.copy()); ob_.name = nm_
    for c_ in list(ob_.users_collection): c_.objects.unlink(ob_)
    _colb.objects.link(ob_); ob_.parent = None
    if ob_.animation_data: ob_.animation_data_clear()
    ob_.rotation_mode = 'QUATERNION'; p0_ = Vector((SLAB_POS[i_][0], SLAB_POS[i_][1], 14.90)); prev_ = None
    for k in sorted(set([1] + [f for f in frames if f >= SLAB_AT - 3])):
        e_ = max(0.001, 0.19 * ela((k - SLAB_AT - i_) / 4.0)) if k > SLAB_AT + i_ else 0.001; loc_, q_ = p0_, Quaternion((1, 0, 0, 0))
        if i_ == 5 and k >= 791:                                                                        # el sexto: lo coge la mano derecha, lo lleva a la espalda y se lo guarda
            Mh_ = MH[k]["Right"] @ RelRb_; u_ = ss((k - 791) / 3.0); loc_ = p0_.lerp(Mh_.translation, u_); q_ = q_.slerp(Mh_.to_quaternion(), u_); e_ = e_ + (0.35 - e_) * u_
            if k > 802: e_ = max(0.001, e_ * (1 - ss((k - 802) / 3.0)))
        if i_ < 5:
            la_, (lx_, ly_), yw_ = SLAB_THROW[i_ + 1]; zj_, rel_l = SLAB_REL[i_ + 1]
            ro_ = SLAB_OFF[i_ + 1]; fx_, fy_, fyaw_ = SLAB_FLOOR[i_ + 1]
            if k >= ro_ + SLAB_OFF_FLY: loc_, q_ = Vector((fx_, fy_, 14.0)), Quaternion((0, 0, 1), D(fyaw_))
            elif k >= ro_:
                Mr_ = MJ[ro_] @ rel_l; u_ = (k - ro_) / float(SLAB_OFF_FLY); a0_ = Mr_.translation; loc_ = Vector((a0_.x + (fx_ - a0_.x) * u_, a0_.y + (fy_ - a0_.y) * u_, a0_.z + (14.0 - a0_.z) * u_ + 4 * 0.15 * u_ * (1 - u_)))
                q_ = Mr_.to_quaternion().slerp(Quaternion((0, 0, 1), D(fyaw_)), ss(u_))
            elif k >= la_ + SLAB_FLY: Mq_ = MJ[k] @ rel_l; loc_, q_ = Mq_.translation, Mq_.to_quaternion()
            elif k >= la_:
                u_ = (k - la_) / float(SLAB_FLY); loc_ = Vector((p0_.x + (lx_ - p0_.x) * u_, p0_.y + (ly_ - p0_.y) * u_, p0_.z + (zj_ - p0_.z) * u_ + 4 * 0.25 * u_ * (1 - u_)))
                q_ = Quaternion((0, 1, 0), 2 * math.pi * u_ * (1 if i_ % 2 == 0 else -1)) @ Quaternion((0, 0, 1), D(yw_) * ss(u_))
        if prev_ is not None and q_.dot(prev_) < 0: q_ = -q_
        prev_ = q_; ob_.location = loc_; ob_.rotation_quaternion = q_; ob_.scale = (e_, e_, e_)
        for dp_ in ("location", "rotation_quaternion", "scale"): ob_.keyframe_insert(dp_, frame=k)
# EL BLOQUE QUE SE CAVA: tapa de cesped + pozo + item de tierra
_colc = bpy.data.collections.get("cavar") or bpy.data.collections.new("cavar")
if _colc.name not in sc.collection.children: sc.collection.children.link(_colc)
lid_ = bpy.data.objects.get("lid_cesped_cavar")
if lid_ is None:                                                                                             # se saca de a.001 el unico quad de la cara superior de esa casilla (queda su copia exacta en `lid_cesped_cavar`)
    import bmesh
    a_ = bpy.data.objects["a.001"]; bm_ = bmesh.new(); bm_.from_mesh(a_.data); mwa_ = a_.matrix_world; uvl_ = bm_.loops.layers.uv.active
    fc_ = [f for f in bm_.faces if len(f.verts) == 4 and abs((mwa_ @ f.calc_center_median()).x + 95.5) < 0.01 and abs((mwa_ @ f.calc_center_median()).y + 108.5) < 0.01 and abs((mwa_ @ f.calc_center_median()).z - 14.0) < 0.01][0]
    me_ = bpy.data.meshes.new("lid_cesped_cavar"); vs_ = [mwa_ @ v.co for v in fc_.verts]; uv_ = [l[uvl_].uv.copy() for l in fc_.loops] if uvl_ else None
    me_.from_pydata([tuple(v) for v in vs_], [], [(0, 1, 2, 3)]); me_.update(); mi_ = fc_.material_index
    for mat_ in a_.data.materials: me_.materials.append(mat_)
    me_.polygons[0].material_index = mi_
    if uv_:
        uvm_ = me_.uv_layers.new(name="UVMap")
        for i_, l_ in enumerate(me_.loops): uvm_.data[l_.index].uv = uv_[i_]
    lid_ = bpy.data.objects.new("lid_cesped_cavar", me_); lid_["quad_original_de_a001"] = "eliminado de a.001 (casilla x -96..-95, y -109..-108, cara superior z 14)"
    bmesh.ops.delete(bm_, geom=[fc_], context='FACES'); bm_.to_mesh(a_.data); a_.data.update(); bm_.free()
for c_ in list(lid_.users_collection): c_.objects.unlink(lid_)
_colc.objects.link(lid_)
if lid_.animation_data: lid_.animation_data_clear()
for f_, v_ in ((1, False), (FALL0 - 1, False), (FALL0, True), (N, True)):
    lid_.hide_viewport = v_; lid_.hide_render = v_; lid_.keyframe_insert("hide_viewport", frame=f_); lid_.keyframe_insert("hide_render", frame=f_)
dref_ = bpy.data.objects.get("tierra_item")
if dref_ is None:
    dref_ = bpy.data.objects.get("dirt")
    if dref_ is None or dref_.users_scene:
        with bpy.data.libraries.load(os.path.join(BASE_SRC, "bloque_de_tierra.blend"), link=False) as (_a4, _b4): _b4.objects = ["dirt"]
        dref_ = bpy.data.objects["dirt"]
    dref_.name = "tierra_item"
pit_ = bpy.data.objects.get("pozo_tierra")
if pit_ is None:
    import bmesh
    me_ = dref_.data.copy(); me_.name = "pozo_tierra"; bm_ = bmesh.new(); bm_.from_mesh(me_)
    bmesh.ops.delete(bm_, geom=[f for f in bm_.faces if f.calc_center_median().z > 0.99], context='FACES'); bm_.to_mesh(me_); bm_.free()          # el pozo es la caja abierta por arriba
    pit_ = bpy.data.objects.new("pozo_tierra", me_)
for c_ in list(pit_.users_collection): c_.objects.unlink(pit_)
_colc.objects.link(pit_); pit_.location = (-95.5, -108.5, 13.0); pit_.rotation_euler = (0, 0, 0); pit_.scale = (1.0, 1.0, 1.0)
for c_ in list(dref_.users_collection): c_.objects.unlink(dref_)
_colc.objects.link(dref_)
dref_.parent = None
if dref_.animation_data: dref_.animation_data_clear()
dref_.rotation_mode = 'XYZ'
for k in sorted(set([1] + [f for f in frames if f >= DIRT_SPAWN - 3])):
    u_ = k - DIRT_SPAWN; vis_ = DIRT_SPAWN <= k < DIRT_ABSORB + 7
    base_ = Vector((-95.85, -108.5, 13.55 + 0.9 * ss(u_ / 8.0) + 0.035 * math.sin(max(0, u_ - 8) * 0.45))); sc_i = 0.25 * ss(u_ / 3.0)
    if k >= DIRT_ABSORB:
        a_ = ss((k - DIRT_ABSORB) / 7.0); tgt_ = MS[k].translation.copy(); base_ = base_.lerp(tgt_, a_); sc_i *= (1 - a_)
    dref_.location = (base_ - Vector((0.0, 0.0, sc_i * 0.5))) if vis_ else Vector((-95.85, -108.5, 13.5))
    dref_.rotation_euler = (0, 0, 4 * math.pi * max(0, u_) / 30.0); sc_i = max(0.001, sc_i) if vis_ else 0.001; dref_.scale = (sc_i, sc_i, sc_i)
    for dp_ in ("location", "rotation_euler", "scale"): dref_.keyframe_insert(dp_, frame=k)
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
            v = max(blink_cortina(f), wp_eval(SLEEP, f)[0])
            if f % 2 == 1 or blink_cortina(f) > 0 or f in (T0 + 105, T0 + 118, T0 + 140, T0 + 170): kb.value = v; kb.keyframe_insert("value", frame=f)
JSLEEP = [(1, (0.0,)), (SLEEP_J0, (0.0,)), (SLEEP_J0 + 26, (1.0,)), (JR_SHAKE[0] - 4, (1.0,)), (JR_SHAKE[0], (0.15,)), (JR_SHAKE[2], (0.15,)), (JR_SHAKE[2] + 8, (1.0,)), (JR_SHAKE2[0] - 4, (1.0,)), (JR_SHAKE2[0], (0.15,)), (JR_SHAKE2[2], (0.15,)), (JR_SHAKE2[2] + 6, (0.0,)), (N, (0.0,))]
for nm in ("ojo_izquierdo_jerry", "ojo_derecho_jerry", "pupila_izquierda_jerry", "pupila_derecha_jerry"):
    ob = bpy.data.objects.get(nm)
    if ob and ob.data.shape_keys and "Closed" in ob.data.shape_keys.key_blocks:
        kb = ob.data.shape_keys.key_blocks["Closed"]; sk = ob.data.shape_keys
        if sk.animation_data: sk.animation_data.action = None
        for f in range(1, N + 1):
            if f % 4 == 1 or SLEEP_J0 - 4 <= f <= SLEEP_J0 + 30 or JR_SHAKE[0] - 6 <= f <= JR_SHAKE[2] + 10 or JR_SHAKE2[0] - 6 <= f <= N: kb.value = wp_eval(JSLEEP, f)[0]; kb.keyframe_insert("value", frame=f)
sc.frame_start = 1; sc.frame_end = N; sc.frame_set(1)
print(f"Parte 3: sentarse en el refugio, {len(frames)} muestras, f1-f{N}")
