"""Parte 3 - Alfred y Jerry se SIENTAN a descansar dentro del refugio (pedido de Kebyn). Se ejecuta DENTRO de Blender (exec) sobre base_parte_3.blend (f1 = estado del f2150 de la parte 2).
Layout (interior 2x2 del refugio, x -97..-95, y -110..-108; la antorcha esta en el centro (-96,-109)):
  Alfred: se gira al oeste, se agacha y se sienta con la espalda en el muro este (-95.3,-108.3) con las piernas estiradas hacia el oeste (muro norte a su derecha); respira, mira la antorcha, se le cierra la cabeza de sueno.
  Jerry : camina al rincon suroeste (-96.55,-109.45), se gira hacia la antorcha (NE) y se sienta como perro (grupa abajo, pecho arriba, patas traseras plegadas); respira, mueve la cola y la oreja, bosteza y apoya la cabeza.
Medidas en el rig: piernas de Alfred rectas (UpLeg X -90, rodilla 0) con Hips Y local -0.69 apoyan el cuerpo en el suelo (z 14.0); Jerry: spine_6 X +32, root z -0.15.
Idempotente: borra las acciones previas de Alfred/Jerry antes de keyframear. Rango de escena 1..N.
"""
import bpy, math
D = math.radians
N = 360
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
A = bpy.data.objects["a"]; O = bpy.data.objects["Object"]; PA = A.pose.bones
for ob in (O, A): clear(ob)
for b in PA: b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
Z3 = (0, 0, 0)
TH = -4 * math.pi                                                                   # giro acumulado de la parte 2 (equivale a 0)
# Medido en Blender (brazo derecho, Alfred mirando al oeste): UpArm X = elevacion (90 = cuelga, 0 = lateral), Z +90 = hacia ADELANTE (Z -90 = hacia atras); el izquierdo es el espejo (Z negativo = adelante).
# Pose de reposo sentado: manos apoyadas en el suelo a los lados de las piernas: UpArm (62, +-78), codo X -28.
def arm(side, x, az, ex, ez=0.0):
    s = 1 if side == "Right" else -1
    return (x, 0, s * az), (ex, 0, ez)


ALF = {}
for side in ("Right", "Left"):
    s = 1 if side == "Right" else -1
    ua = [(1, (90, 0, 0)), (34, (90, 0, 0)), (40, (104, 0, -s * 8)), (48, (66, 0, s * 70)), (58, (60, 0, s * 80)), (70, (62, 0, s * 78)), (84, (62, 0, s * 78)), (100, (62, 0, s * 78))]
    el = [(1, Z3), (34, Z3), (40, (-4, 0, 0)), (48, (-22, 0, 0)), (58, (-26, 0, 0)), (70, (-28, 0, 0)), (100, (-28, 0, 0))]
    ALF[f"{side}UpArm_alfred"] = ua; ALF[f"{side}elbow_alfred"] = el
    # las piernas se estiran una despues de otra (derecha primero), con los pies abiertos hacia afuera
    ALF[f"{side}UpLeg_alfred"] = [(1, Z3), (34, Z3), (40, (-22, 0, s * 1)), (50, (-58, 0, s * 3)), (58, (-62, 0, s * 4)), (62 if side == "Right" else 66, (-66, 0, s * 4)), (72 if side == "Right" else 76, (-90, 0, s * 10)), (100, (-90, 0, s * 10))]
    ALF[f"{side}knee_alfred"] = [(1, Z3), (34, Z3), (40, (38, 0, 0)), (50, (98, 0, 0)), (58, (88, 0, 0)), (62 if side == "Right" else 66, (82, 0, 0)), (72 if side == "Right" else 76, (6, 0, 0)), (100, (6, 0, 0))]
ALF.update({
    "Hips_alfred":   [(1, Z3), (360, Z3)],
    "Spine_alfred":  [(1, Z3), (24, (2, 0, 0)), (34, (6, 0, 0)), (44, (16, 0, 0)), (56, (12, 0, 0)), (72, (3, 0, 0)), (84, (-2, 0, 0)), (110, (-4, 0, 0))],
    "Spine1_alfred": [(1, Z3), (34, (2, 0, 0)), (44, (6, 0, 0)), (60, (4, 0, 0)), (84, (0, 0, 0)), (110, (-1, 0, 0))],
    "Spine2_alfred": [(1, Z3), (34, (4, 0, 0)), (44, (10, 0, 0)), (60, (7, 0, 0)), (84, (0, 0, 0)), (110, (-2, 0, 0))],
    "Neck_alfred":   [(1, Z3), (22, Z3), (34, (12, 0, 0)), (46, (16, 0, 0)), (60, (8, 0, 0)), (76, (4, 0, 0)), (100, (2, 0, 0)),
                      (112, (2, 42, 6)), (130, (4, 46, 8)), (160, (6, 40, 4)), (182, (4, 0, 0)), (215, (10, 0, 4)), (250, (20, 4, 8)), (290, (28, 6, 11)), (360, (28, 6, 11))],
})
HIPS_Y = [(1, 0.0), (34, 0.0), (46, -0.36), (56, -0.5), (72, -0.69)]                  # base: la correccion por contacto con el suelo se calcula en apply_alfred
ROOT_A = [(1, (-95.5, -108.5, 14.0, 0.0)), (22, (-95.3, -108.3, 14.0, -90.0)), (360, (-95.3, -108.3, 14.0, -90.0))]


def breathe(k, a0, per, ph=0.0):
    return a0 * math.sin(2 * math.pi * k / per + ph)


def noise(k, seed, a):
    """ruido organico suave: tres senos con periodos no multiplos (nunca se repite de forma evidente)."""
    return a * (0.55 * math.sin(k * 0.071 + seed) + 0.3 * math.sin(k * 0.137 + seed * 2.3) + 0.15 * math.sin(k * 0.293 + seed * 3.7))


def base_spine(k):
    return sum(wp_eval(ALF[b], k)[0] for b in ("Spine_alfred", "Spine1_alfred", "Spine2_alfred"))


def blink_curve(k):
    """parpadeos naturales cada 3-5 s mientras esta despierto (f1-225); 6 f de duracion, a veces doble."""
    for f0 in (14, 70, 112, 150, 158, 196):
        d = k - f0
        if 0 <= d <= 6: return math.sin(math.pi * d / 6.0)
    return 0.0


def alfred_at(k):
    out = {}
    for b, w in ALF.items(): out[b] = list(wp_eval(w, k))
    # pasitos mientras gira (f1-f22): piernas alternas
    wst = ss((k - 1) / 4.0) * (1 - ss((k - 18) / 5.0))
    if wst > 0:
        ph = (k - 1) * 2 * math.pi / 10.0
        out["RightUpLeg_alfred"][0] += wst * 24 * math.sin(ph); out["LeftUpLeg_alfred"][0] -= wst * 24 * math.sin(ph)
        out["Rightknee_alfred"][0] += wst * 22 * max(0.0, math.sin(ph + 0.9)); out["Leftknee_alfred"][0] += wst * 22 * max(0.0, -math.sin(ph + 0.9))
        out["RightUpArm_alfred"][0] += -wst * 10 * math.sin(ph); out["LeftUpArm_alfred"][0] += wst * 10 * math.sin(ph)
    # ---- filtros organicos ----
    alive = 0.35 + 0.65 * ss((k - 72) / 16.0)                                            # ruido suave siempre presente (mas al descansar)
    for b, sd, a in (("Spine_alfred", 1.0, 0.8), ("Spine1_alfred", 2.0, 0.7), ("Spine2_alfred", 3.0, 0.9)): out[b][0] += alive * noise(k, sd, a); out[b][2] += alive * noise(k, sd + 9, 0.6)
    out["Neck_alfred"][0] += alive * noise(k, 4.0, 1.4); out["Neck_alfred"][1] += alive * noise(k, 5.0, 1.8); out["Neck_alfred"][2] += alive * noise(k, 6.0, 1.0)
    for side, sd in (("Right", 7.0), ("Left", 8.0)):
        out[f"{side}UpArm_alfred"][0] += alive * noise(k, sd, 1.4); out[f"{side}elbow_alfred"][0] += alive * noise(k, sd + 3, 1.6)
    # solapamiento (follow-through): la cabeza llega con retraso al movimiento del torso; los codos con retraso a los hombros
    out["Neck_alfred"][0] += -0.55 * (base_spine(k) - base_spine(k - 5))
    for side in ("Right", "Left"):
        a0 = wp_eval(ALF[f"{side}UpArm_alfred"], k - 4)[0]; a1 = wp_eval(ALF[f"{side}UpArm_alfred"], k)[0]; out[f"{side}elbow_alfred"][0] += 0.5 * (a1 - a0)
    # respiracion (≈4 s) + suspiro + cadera que cambia el peso
    rest = ss((k - 76) / 14.0)
    out["Spine2_alfred"][0] += rest * breathe(k, 1.4, 96.0); out["Spine_alfred"][0] += rest * breathe(k, 0.8, 96.0, 0.5); out["Spine1_alfred"][0] += rest * breathe(k, 0.6, 96.0, 0.2)
    out["RightUpArm_alfred"][0] += rest * breathe(k, 1.0, 96.0, 0.4); out["LeftUpArm_alfred"][0] += rest * breathe(k, 1.0, 96.0, 0.4)
    sig = math.exp(-((k - 98) / 7.0) ** 2); out["Spine2_alfred"][0] += -4 * sig; out["Neck_alfred"][0] += -3 * sig
    shift = ss((k - 130) / 10.0) * (1 - ss((k - 150) / 10.0))                              # f130-150 se acomoda: una rodilla sube un poco y la cadera se gira
    out["Hips_alfred"][2] += 2.5 * shift; out["Leftknee_alfred"][0] += 14 * shift; out["LeftUpLeg_alfred"][0] += 7 * shift; out["Spine_alfred"][2] += -2.0 * shift
    mano = ss((k - 196) / 10.0) * (1 - ss((k - 238) / 10.0))                              # se frota los ojos con la mano derecha (cansado)
    out["RightUpArm_alfred"][0] += mano * (-85); out["RightUpArm_alfred"][2] += mano * 0; out["Rightelbow_alfred"][0] += mano * (-70)
    out["Rightelbow_alfred"][0] += mano * 5 * math.sin(k * 0.55)
    hy = wp_eval([(a, (b,)) for a, b in HIPS_Y], k)[0]
    return out, hy


def min_z(root):
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); z = 1e9
    for o in bpy.data.objects:
        p = o
        while p and p.name != root: p = p.parent
        if p and o.type == "MESH" and not o.hide_viewport:
            oe = o.evaluated_get(dg); me = oe.to_mesh(); mw = oe.matrix_world
            z = min(z, min((mw @ v.co).z for v in me.vertices)); oe.to_mesh_clear()
    return z


HY_ADJ = {"v": 0.0}                                                                 # correccion de altura (solo agacharse/sentarse): la parte mas baja del cuerpo queda EXACTO en el suelo (z 13.99)


def apply_alfred(k):
    out, hy = alfred_at(k)
    if k >= 34:
        for b, v in out.items(): PA[b].rotation_euler = [D(x) for x in v]
        PA["Hips_alfred"].location = (0, hy, 0); x, y, z, rz = wp_eval(ROOT_A, k); O.location = (x, y, z); O.rotation_euler = (0, 0, TH + D(rz))
        if k <= 80: HY_ADJ["v"] = 13.99 - min_z("Object")
        hy += HY_ADJ["v"]
        hy += -0.035 * math.exp(-max(0, k - 70) / 4.0) * math.cos(max(0, k - 70) * 0.9) * (1 if k >= 70 else 0)             # impacto/asiento: rebote amortiguado al tocar el suelo
    for b, v in out.items():
        pb = PA[b]; pb.rotation_euler = [D(x) for x in v]; pb.keyframe_insert("rotation_euler", frame=k)
    PA["Hips_alfred"].location = (0, hy, 0); PA["Hips_alfred"].keyframe_insert("location", frame=k)
    x, y, z, rz = wp_eval(ROOT_A, k)
    O.location = (x, y, z); O.rotation_euler = (0, 0, TH + D(rz)); O.keyframe_insert("location", frame=k); O.keyframe_insert("rotation_euler", frame=k)


# ----------------------------------------------------------------------------------------------- JERRY
J = bpy.data.objects["jerry"]; RJ = bpy.data.objects["Dog_001_rig"]; PJ = RJ.pose.bones
for ob in (J, RJ): clear(ob)
for b in PJ: b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
TJ = -1.783                                                                       # giro del root de Jerry cuando mira al +X (f1)
FACE = {"S": D(-90), "NE": 0.68}
ROOT_J = [(1, (-96.5, -108.84, 14.0, 0.0)), (10, (-96.5, -108.84, 14.0, -1.571)), (34, (-96.55, -109.45, 14.0, -1.571)), (48, (-96.55, -109.45, 14.0, 0.68)), (66, (-96.55, -109.45, 13.85, 0.68)), (360, (-96.55, -109.45, 13.85, 0.68))]
SIT = ss  # alias


def jerry_at(k):
    out = {b.name: [0.0, 0.0, 0.0] for b in PJ if b.name in (
        "spine_6", "spine_5", "spine_4", "spine_3", "spine_2", "spine_1", "scull_1", "jaw_bot", "tail_1", "tail_2", "tail_3", "ear.R", "ear.L",
        "thigh.R", "thigh.L", "shin.R", "shin.L", "foot.R", "foot.L", "toe.R", "toe.L", "front_shoulder.R", "front_shoulder.L", "front_thigh.R", "front_thigh.L",
        "front_shin.R", "front_shin.L", "front_foot.R", "front_foot.L", "front_toe.R", "front_toe.L")}
    sit = ss((k - 48) / 18.0)                                                       # f48-66 se sienta
    # caminata f10-34 (trote lento) y pasitos de giro f1-10 / f34-48
    wk = ss((k - 8) / 4.0) * (1 - ss((k - 34) / 4.0)); tn = (ss((k - 1) / 3.0) * (1 - ss((k - 10) / 3.0))) + (ss((k - 34) / 3.0) * (1 - ss((k - 48) / 3.0)))
    amp = max(wk, 0.7 * tn)
    if amp > 0:
        ph = (k - 1) * 2 * math.pi / 7.0
        for s, o in (("R", 0.0), ("L", math.pi)):
            out[f"thigh.{s}"][0] += amp * 26 * math.sin(ph + o); out[f"shin.{s}"][0] += -amp * 22 * max(0.0, math.sin(ph + o + 0.8)); out[f"foot.{s}"][0] += amp * 10 * math.sin(ph + o + 0.5)
        for s, o in (("R", math.pi), ("L", 0.0)):
            out[f"front_thigh.{s}"][0] += amp * 24 * math.sin(ph + o); out[f"front_shin.{s}"][0] += -amp * 14 * max(0.0, math.sin(ph + o + 0.8))
        out["spine_6"][2] += amp * 3 * math.sin(ph); out["spine_3"][2] += -amp * 5 * math.sin(ph); out["scull_1"][2] += amp * 3 * math.sin(ph)
        out["tail_1"][2] += amp * 12 * math.sin(ph * 0.5)
    # sentado
    out["spine_6"][0] += sit * 32; out["spine_5"][0] += -sit * 6; out["scull_1"][0] += -sit * 14
    for s in "RL":
        out[f"thigh.{s}"][0] += sit * 70; out[f"shin.{s}"][0] += -sit * 120; out[f"foot.{s}"][0] += sit * 50
    # reposo (f70+): respiracion, cola perezosa, oreja, mira a Alfred, bosteza y apoya la cabeza
    rest = ss((k - 70) / 12.0)
    out["spine_5"][0] += rest * breathe(k, 1.6, 80.0); out["spine_3"][0] += rest * breathe(k, 1.1, 80.0, 0.4)
    out["tail_1"][2] += rest * (10 * math.sin(k * 0.055) + 4 * math.sin(k * 0.13)); out["tail_2"][2] += rest * 8 * math.sin(k * 0.055 - 0.7); out["tail_3"][2] += rest * 8 * math.sin(k * 0.055 - 1.4)
    ear = math.exp(-((k - 125) / 4.0) ** 2) + math.exp(-((k - 240) / 4.0) ** 2); out["ear.R"][0] += 18 * ear; out["ear.L"][0] += -12 * ear
    look = wp_eval([(1, (0.0,)), (96, (0.0,)), (112, (-38.0,)), (160, (-38.0,)), (178, (0.0,)), (230, (0.0,)), (262, (0.0,))], k)[0]       # gira la cabeza hacia Alfred (Z de scull_1; el signo se midio con la pose sentada)
    out["scull_1"][2] += look * 0.9
    yawn = ss((k - 186) / 8.0) * (1 - ss((k - 210) / 8.0)); out["jaw_bot"][0] += -yawn * 28; out["scull_1"][0] += -yawn * 12
    drop = ss((k - 232) / 28.0); out["scull_1"][0] += drop * 26; out["spine_4"][0] += drop * 8; out["spine_5"][0] += drop * 5          # se adormece: baja la cabeza al pecho/patas
    return out


def apply_jerry(k):
    for b, v in jerry_at(k).items():
        pb = PJ[b]; pb.rotation_euler = [D(x) for x in v]; pb.keyframe_insert("rotation_euler", frame=k)
    x, y, z, rz = wp_eval(ROOT_J, k)
    J.location = (x, y, z); J.rotation_euler = (0, 0, TJ + rz); J.keyframe_insert("location", frame=k); J.keyframe_insert("rotation_euler", frame=k)


frames = list(range(1, N + 1, STEP))
if frames[-1] != N: frames.append(N)
for k in frames:
    apply_alfred(k); apply_jerry(k)
# Alfred: parpadeos naturales mientras esta despierto y cierra los ojos al dormirse (shape key "Closed" de los dos ojos)
SLEEP = [(1, (0.0,)), (225, (0.0,)), (240, (0.55,)), (262, (0.35,)), (285, (1.0,)), (360, (1.0,))]
for nm in ("ojo_izquierdo_alfred", "ojo_derecho_alfred"):
    ob = bpy.data.objects.get(nm)
    if ob and ob.data.shape_keys and "Closed" in ob.data.shape_keys.key_blocks:
        kb = ob.data.shape_keys.key_blocks["Closed"]; sk = ob.data.shape_keys
        if sk.animation_data: sk.animation_data.action = None
        for f in range(1, N + 1):
            v = max(blink_curve(f) * (1.0 if f < 225 else 0.0), wp_eval(SLEEP, f)[0])
            if f % 2 == 1 or blink_curve(f) > 0 or f in (225, 240, 262, 285): kb.value = v; kb.keyframe_insert("value", frame=f)
sc.frame_start = 1; sc.frame_end = N; sc.frame_set(1)
print(f"Parte 3: sentarse en el refugio, {len(frames)} muestras, f1-f{N}")
