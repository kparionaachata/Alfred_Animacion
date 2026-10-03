"""Parte 3 - Alfred y Jerry se SIENTAN a descansar dentro del refugio (pedido de Kebyn). Se ejecuta DENTRO de Blender (exec) sobre base_parte_3.blend (f1 = estado del f2150 de la parte 2).
Layout (interior 2x2 del refugio, x -97..-95, y -110..-108; la antorcha esta en el centro (-96,-109)):
  Alfred: se gira al oeste, se agacha y se sienta con la espalda en el muro este (-95.3,-108.3) con las piernas estiradas hacia el oeste (muro norte a su derecha); respira, mira la antorcha, se le cierra la cabeza de sueno.
  Jerry : camina al rincon suroeste (-96.55,-109.45), se gira hacia la antorcha (NE) y se sienta como perro (grupa abajo, pecho arriba, patas traseras plegadas); respira, mueve la cola y la oreja, bosteza y apoya la cabeza.
Medidas en el rig: piernas de Alfred rectas (UpLeg X -90, rodilla 0) con Hips Y local -0.69 apoyan el cuerpo en el suelo (z 14.0); Jerry: spine_6 X +32, root z -0.15.
Idempotente: borra las acciones previas de Alfred/Jerry antes de keyframear. Rango de escena 1..N.
"""
import bpy, math
D = math.radians
N = 480
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
A = bpy.data.objects["a"]; O = bpy.data.objects["Object"]; PA = A.pose.bones
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
    return (-95.5 + 0.2 * u, -108.5 - 0.09 * u, 14.0, yaw)    # Alfred mira a +Y local: yaw +90 => mira al oeste (piernas hacia el oeste). Y final -108.59 (antes -108.3): se sienta 0.29 m mas hacia su IZQUIERDA (sur) para que el brazo derecho no atraviese el muro norte (cara interior y=-108.0)


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
    for f0 in (14, 70, 112, 150, 158, 196, 236, 300, 352, 360, 392):
        d = k - f0
        if 0 <= d <= 6: return math.sin(math.pi * d / 6.0)
    return 0.0


def alfred_at(k):
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
        mira = wp_eval([(T0, (0.0,)), (T0 + 16, (0.0,)), (T0 + 34, (44.0,)), (T0 + 66, (46.0,)), (T0 + 84, (0.0,)), (480, (0.0,))], k)[0]                      # mira la antorcha (a su izquierda: Neck Y +)
        rot["Neck_alfred"][1] += D(mira); rot["Neck_alfred"][0] += D(-4 * ss((k - T0 - 20) / 12.0) * (1 - ss((k - T0 - 80) / 12.0)))
        cae = wp_eval([(T0, (0.0,)), (T0 + 100, (0.0,)), (T0 + 160, (14.0,)), (480, (14.0,))], k)[0]                                                    # se adormece: la cabeza cae mas
        rot["Neck_alfred"][0] += D(cae); rot["Neck_alfred"][2] += D(cae * 0.4)
        sig = math.exp(-((k - T0 - 44) / 7.0) ** 2); rot["Spine2_alfred"][0] += D(-3 * sig)                                                              # suspiro
        # brazo izquierdo (colgando): leve vaiven; el derecho (apoyado) casi quieto
        rot["LeftUpArm_alfred"][0] += D(alive * noise(k, 7.0, 1.2)); rot["Leftelbow_alfred"][0] += D(alive * noise(k, 10.0, 1.6))
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


HY = {"v": 0.0}


def apply_alfred(k):
    rot, loc = alfred_at(k)
    x, y, z, rz = root_at(k)
    O.location = (x, y, z); O.rotation_euler = (0, 0, TH + D(rz))
    for b, v in rot.items(): PA[b].rotation_euler = v
    for b, v in loc.items(): PA[b].location = v
    if k >= REF0: PA["Hips_alfred"].location = (loc["Hips_alfred"][0], loc["Hips_alfred"][1] + HYK[max(q for q in HYK if q <= k)], loc["Hips_alfred"][2])
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


def root_j(k):
    """(x, y, z, rz, roll) del root de Jerry. f1-160: waypoints; f160-182 se levanta (z 13.85 -> 14.0); f196-238 gira sobre las caderas; f250-284 rueda 90 grados sobre su costado derecho y se pega al muro sur."""
    x, y, z, rz = wp_eval(ROOT_J, k); roll = 0.0
    if k > STAND0: z = 13.85 + 0.15 * ss((k - STAND0) / float(STAND_D))
    if k > TURN0:
        v = ss((k - TURN0) / float(TURN_D)); rz = 0.68 + (RZ_LIE - 0.68) * v
        x = SIT_END[0] + (TURN_END[0] - SIT_END[0]) * v; y = SIT_END[1] + (TURN_END[1] - SIT_END[1]) * v
    if k > LIE0:
        w = ss((k - LIE0) / float(LIE_D)); x = TURN_END[0] + (LIE_ROOT[0] - TURN_END[0]) * w; y = TURN_END[1] + (LIE_ROOT[1] - TURN_END[1]) * w; roll = (math.pi / 2) * w
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
    out["spine_5"][0] += lie * breathe(k, 1.8, 96.0, 0.3); out["spine_3"][0] += lie * breathe(k, 1.2, 96.0, 0.7)                                                       # respiracion lenta y profunda al dormir
    tw = math.exp(-((k - 384) / 3.0) ** 2) + 0.7 * math.exp(-((k - 392) / 3.0) ** 2); out["front_foot.R"][0] += lie * 9 * tw; out["foot.R"][0] += lie * 6 * tw; out["ear.L"][0] += lie * 8 * tw  # suena: tiembla una pata
    return out


def apply_jerry(k):
    for b, v in jerry_at(k).items():
        pb = PJ[b]; pb.rotation_euler = [D(x) for x in v]; pb.keyframe_insert("rotation_euler", frame=k)
    PJ["spine_6"].location = jloc_at(k); PJ["spine_6"].keyframe_insert("location", frame=k)
    x, y, z, rz, roll = root_j(k)
    J.location = (x, y, z + DZS.get(k, 0.0)); J.rotation_euler = (0, roll, TJ + rz); J.keyframe_insert("location", frame=k); J.keyframe_insert("rotation_euler", frame=k)


frames = sorted(set(range(1, N + 1, STEP)) | set(range(1, REFEND + 6)) | set(range(STAND0 - 4, LIE0 + LIE_D + 12)))                # cada 2 f, y CADA frame mientras se sienta (30 f: con muestras cada 2 f se perderia el detalle)
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
        HYK[k] = 13.99 - min_z("Object")
# PASADA 1b (sin keyframes): Jerry NUNCA atraviesa el suelo. Por frame se mide su punto mas bajo (todas las mallas) y se corrige la altura del root para que quede a 14.015 (suelo 14.0 + 1.5 cm de margen);
# la correccion se suaviza con una media movil de +-3 frames. Corrige las patas enterradas al sentarse (y los 2 cm que se hundian al caminar).
DZK = {}
for k in frames:
    for b_, v_ in jerry_at(k).items(): PJ[b_].rotation_euler = [D(x_) for x_ in v_]
    PJ["spine_6"].location = jloc_at(k)
    x, y, z, rz, roll = root_j(k); J.location = (x, y, z); J.rotation_euler = (0, roll, TJ + rz)
    DZK[k] = 14.015 - min_z("jerry")
DZS = {}
for i, k in enumerate(frames):
    w = [DZK[frames[q]] for q in range(max(0, i - 3), min(len(frames), i + 4))]; DZS[k] = max(sum(w) / len(w), DZK[k] - 0.012)                              # suave, pero nunca por debajo de 14.003
for k in frames:
    apply_alfred(k); apply_jerry(k)
# Alfred: parpadeos naturales mientras esta despierto y cierra los ojos al dormirse (shape key "Closed" de los dos ojos)
SLEEP = [(1, (0.0,)), (T0 + 105, (0.0,)), (T0 + 118, (0.5,)), (T0 + 140, (0.3,)), (T0 + 170, (1.0,)), (480, (1.0,))]
for nm in ("ojo_izquierdo_alfred", "ojo_derecho_alfred"):
    ob = bpy.data.objects.get(nm)
    if ob and ob.data.shape_keys and "Closed" in ob.data.shape_keys.key_blocks:
        kb = ob.data.shape_keys.key_blocks["Closed"]; sk = ob.data.shape_keys
        if sk.animation_data: sk.animation_data.action = None
        for f in range(1, N + 1):
            v = max(blink_curve(f) * (1.0 if f < T0 + 105 else 0.0), wp_eval(SLEEP, f)[0])
            if f % 2 == 1 or blink_curve(f) > 0 or f in (T0 + 105, T0 + 118, T0 + 140, T0 + 170): kb.value = v; kb.keyframe_insert("value", frame=f)
JSLEEP = [(1, (0.0,)), (LIE0 + 18, (0.0,)), (LIE0 + 44, (1.0,)), (N, (1.0,))]
for nm in ("ojo_izquierdo_jerry", "ojo_derecho_jerry", "pupila_izquierda_jerry", "pupila_derecha_jerry"):
    ob = bpy.data.objects.get(nm)
    if ob and ob.data.shape_keys and "Closed" in ob.data.shape_keys.key_blocks:
        kb = ob.data.shape_keys.key_blocks["Closed"]; sk = ob.data.shape_keys
        if sk.animation_data: sk.animation_data.action = None
        for f in range(1, N + 1):
            if f % 4 == 1 or LIE0 + 14 <= f <= LIE0 + 48: kb.value = wp_eval(JSLEEP, f)[0]; kb.keyframe_insert("value", frame=f)
sc.frame_start = 1; sc.frame_end = N; sc.frame_set(1)
print(f"Parte 3: sentarse en el refugio, {len(frames)} muestras, f1-f{N}")
