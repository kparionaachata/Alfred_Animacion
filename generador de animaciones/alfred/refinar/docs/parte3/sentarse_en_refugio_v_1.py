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
# waypoints en GRADOS (X, Y, Z)
ALF = {
    "RightUpArm_alfred": [(1, (90, 0, 0)), (34, (90, 0, 0)), (44, (62, 0, -10)), (56, (50, 0, -22)), (72, (80, 0, -6)), (100, (80, 0, -6))],
    "LeftUpArm_alfred":  [(1, (90, 0, 0)), (34, (90, 0, 0)), (44, (62, 0, 10)), (56, (50, 0, 22)), (72, (80, 0, 6)), (100, (80, 0, 6))],
    "Rightelbow_alfred": [(1, Z3), (44, (-8, 0, 0)), (72, (-38, 0, 0)), (100, (-38, 0, 0))],
    "Leftelbow_alfred":  [(1, Z3), (44, (-8, 0, 0)), (72, (-38, 0, 0)), (100, (-38, 0, 0))],
    "RightUpLeg_alfred": [(1, Z3), (34, Z3), (46, (-58, 0, -2)), (56, (-64, 0, -3)), (72, (-90, 0, -6))],
    "LeftUpLeg_alfred":  [(1, Z3), (34, Z3), (46, (-58, 0, 2)), (56, (-64, 0, 3)), (72, (-90, 0, 6))],
    "Rightknee_alfred":  [(1, Z3), (34, Z3), (46, (96, 0, 0)), (56, (84, 0, 0)), (72, Z3)],
    "Leftknee_alfred":   [(1, Z3), (34, Z3), (46, (96, 0, 0)), (56, (84, 0, 0)), (72, Z3)],
    "Hips_alfred":       [(1, Z3), (360, Z3)],
    "Spine_alfred":      [(1, Z3), (30, (4, 0, 0)), (46, (14, 0, 0)), (60, (8, 0, 0)), (74, (-4, 0, 0)), (100, (-4, 0, 0))],
    "Spine2_alfred":     [(1, Z3), (30, (6, 0, 0)), (46, (10, 0, 0)), (60, (6, 0, 0)), (74, (-3, 0, 0)), (100, (-3, 0, 0))],
    "Neck_alfred":       [(1, Z3), (22, Z3), (34, (14, 0, 0)), (46, (10, 0, 0)), (60, (4, 0, 0)), (74, (-4, 0, 0)), (100, (-4, 0, 0)),
                          (112, (-2, 42, 6)), (130, (0, 46, 8)), (160, (4, 40, 4)), (182, (-2, 0, 0)), (215, (6, 0, 4)), (250, (16, 4, 8)), (290, (24, 6, 11)), (360, (24, 6, 11))],
}
HIPS_Y = [(1, 0.0), (34, 0.0), (46, -0.36), (56, -0.5), (72, -0.69)]                  # altura local de la cadera (1 unidad = 1 m)
ROOT_A = [(1, (-95.5, -108.5, 14.0, 0.0)), (22, (-95.3, -108.3, 14.0, -90.0)), (360, (-95.3, -108.3, 14.0, -90.0))]


def breathe(k, a0, per, ph=0.0):
    return a0 * math.sin(2 * math.pi * k / per + ph)


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
    rest = ss((k - 78) / 14.0)                                                           # sentado: respiracion lenta (≈4 s) + leve cabeceo + manos que se acomodan
    out["Spine2_alfred"][0] += rest * breathe(k, 1.4, 96.0); out["Spine_alfred"][0] += rest * breathe(k, 0.8, 96.0, 0.5)
    out["RightUpArm_alfred"][0] += rest * breathe(k, 1.0, 96.0, 0.4); out["LeftUpArm_alfred"][0] += rest * breathe(k, 1.0, 96.0, 0.4)
    # suspiro largo en f95 (hombros arriba y caen) y se frota la cara/ajusta postura en f140-165 con la mano derecha
    sig = math.exp(-((k - 98) / 7.0) ** 2); out["Spine2_alfred"][0] += -4 * sig; out["Neck_alfred"][0] += -3 * sig
    mano = ss((k - 196) / 10.0) * (1 - ss((k - 238) / 10.0))                              # se frota los ojos con la mano derecha (cansado)
    out["RightUpArm_alfred"][0] += mano * (-85); out["RightUpArm_alfred"][2] += mano * 40; out["Rightelbow_alfred"][0] += mano * (-70)
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
# Alfred: cierra los ojos al dormirse (shape key "Closed" de los dos ojos), f230-285
for nm in ("ojo_izquierdo_alfred", "ojo_derecho_alfred"):
    ob = bpy.data.objects.get(nm)
    if ob and ob.data.shape_keys and "Closed" in ob.data.shape_keys.key_blocks:
        kb = ob.data.shape_keys.key_blocks["Closed"]; sk = ob.data.shape_keys
        if sk.animation_data: sk.animation_data.action = None
        for f, v in ((1, 0.0), (225, 0.0), (240, 0.55), (262, 0.35), (285, 1.0), (360, 1.0)):
            kb.value = v; kb.keyframe_insert("value", frame=f)
sc.frame_start = 1; sc.frame_end = N; sc.frame_set(1)
print(f"Parte 3: sentarse en el refugio, {len(frames)} muestras, f1-f{N}")
