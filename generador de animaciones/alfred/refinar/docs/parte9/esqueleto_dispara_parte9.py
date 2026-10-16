# -*- coding: utf-8 -*-
"""Parte 9: el ESQUELETO (`estructura_lista/skeleton_1.blend`, coleccion `esqueleto_parte9`) parado ENCIMA del bloque `piso_piedra_-137_-71_-1` (root (-136.5, -70.5, 0)).
- Dispara las flechas de la escena con la animacion del estudio "disparar flechas" (Downloads/animacion de apuntar.py, slot 17: sube el arco f1-16, tensa f16-31,
  SUELTA en f39, baja f39-53; cuerda `Shooting_skeleton_1` X). Cada tiro empieza 38 f antes de que salga su flecha (`scene["p9_disparos"]`, lo escribe
  `alfred_pan_flechas_cae_parte9.py`): 3 tiros a ALFRED y el 4o a la piedra junto a JERRY. Mira primero a Alfred y gira hacia Jerry antes del 4o tiro.
  Como Alfred y Jerry estan ARRIBA, los brazos suben (X del hombro -pitch*0.9) y la cabeza mira arriba.
- f528-540 vuelve a apuntar a Jerry, lo mantiene 20 f (f540-560) sin soltar, en f560-566 gira 180 grados RAPIDO bajando el arco y desde f566 se va CORRIENDO
  (ciclo CORRER del estudio, Downloads/esqueleto corriendo.py: 2 m cada 11 f, inclinacion 0.12, rebote 0.06) por un camino libre del suelo de la cueva (BFS por las
  celdas del piso sin montones), alejandose de Alfred.
- Guarda `scene["p9_arco_S"]` (cuerda al soltar mirando a Alfred): el origen de las flechas. Repetible. Ejecutar con `bpy.app.timers.register`."""
import bpy, math
from mathutils import Vector, Euler

sc = bpy.context.scene; R = bpy.data.objects["skeleton_1"]; A = bpy.data.objects["skeleton.arma_1"]; BOW = bpy.data.objects["Bones:Bow_1"]
BW_ = bpy.data.objects["Bow_1"]; BW_.location = (-2.2831, -0.001601, 1.054); BW_.rotation_mode = "XYZ"; BW_.rotation_euler = (0.0, math.radians(90), math.radians(-90)); BW_.scale = (1, 1, 1)   # el arco en la mano (valores del usuario)
POS = Vector((-136.5, -70.5, 0.0)); FIN = 700
DISP = list(sc.get("p9_disparos", [152, 230, 316, 398]))                                   # frames en que SALE cada flecha (suelta)
ALF = Vector((-132.0, -70.3, 8.0)); JER = Vector(sc.get("p9_flecha_jerry_punto", (-131.9, -70.58, 10.53)))
OBJ = [ALF, ALF, ALF, JER]
T_SUSTO = 522; T_GIRA = 522 + 4 + 15; T_CORRE = T_GIRA + 6                           # f522 se ASUSTA (4 f), queda asi 15 f mirando a Jerry, gira 180 rapido (6 f) y corre
SUSTO = {"RightUpArm_skeleton_1": (0.0, 0.0, 0.25), "LeftUpArm_skeleton_1": (0.0, 0.0, -0.25), "Rightelbow_skeleton_1": (0.0, 0.0, 0.15), "Leftelbow_skeleton_1": (0.0, 0.0, -0.15),
         "RightUpLeg_skeleton_1": (0.0, 0.0, 0.35), "LeftUpLeg_skeleton_1": (0.0, 0.0, -0.35), "vertebra_1_skeleton_1": (-0.10, 0.0, 0.0)}   # brazos ABIERTOS a los lados, piernas en V invertida, se echa atras
ss = lambda t: 0.0 if t <= 0 else (1.0 if t >= 1 else t * t * (3 - 2 * t))
BONES = ["no_bone_1_skeleton_1", "vertebra_1_skeleton_1", "vertebra_3_skeleton_1", "vertebra_5_skeleton_1", "no_bone_2_skeleton_1", "Head_skeleton_1",
         "RightUpArm_skeleton_1", "Rightelbow_skeleton_1", "LeftUpArm_skeleton_1", "Leftelbow_skeleton_1", "RightUpLeg_skeleton_1", "Rightknee_skeleton_1", "LeftUpLeg_skeleton_1", "Leftknee_skeleton_1"]
PARADO = {b: (0.0, 0.0, 0.0) for b in BONES}; PARADO["RightUpArm_skeleton_1"] = (0.0, 0.0, -1.570796); PARADO["LeftUpArm_skeleton_1"] = (0.0, 0.0, 1.570796)
# slot 17 (relativo): 1 parado, 16 arriba, 31 tensado, 39 suelta, 53 parado
K17 = {1: {}, 16: {"RightUpArm_skeleton_1": (-1.570796, 0, -1.570796), "LeftUpArm_skeleton_1": (-1.363036, 0.614602, 1.570796), "Leftelbow_skeleton_1": (-0.120522, 0.189698, 0.841421)},
       31: {"RightUpArm_skeleton_1": (-1.570796, 0, -1.570796), "LeftUpArm_skeleton_1": (-1.363036, 0.614602, 1.570796), "Leftelbow_skeleton_1": (-0.078461, 0.218243, 1.088276)},
       39: {"RightUpArm_skeleton_1": (-1.570796, 0, -1.570796), "LeftUpArm_skeleton_1": (-1.363036, 0.614602, 1.570796), "Leftelbow_skeleton_1": (-0.120522, 0.189698, 0.841421)}, 53: {}}
CUERDA = {1: 0.0, 16: -0.013158, 31: 0.158308, 39: -0.013158, 53: 0.0}
def pose17(k):
    """pose del slot 17 en el frame relativo k (1..53), interpolada suave entre sus claves; peso de 'apuntar' (0 parado .. 1 arriba)"""
    ks = sorted(K17); k = max(1, min(53, k))
    for a, b in zip(ks, ks[1:]):
        if a <= k <= b:
            t = ss((k - a) / (b - a)); pa = dict(PARADO); pa.update(K17[a]); pb = dict(PARADO); pb.update(K17[b])
            p = {n: tuple(pa[n][i] + (pb[n][i] - pa[n][i]) * t for i in range(3)) for n in BONES}
            wa = 0.0 if a in (1, 53) else 1.0; wb = 0.0 if b in (1, 53) else 1.0
            return p, CUERDA[a] + (CUERDA[b] - CUERDA[a]) * t, wa + (wb - wa) * t
    return dict(PARADO), 0.0, 0.0
def yaw_a(p):                                                                              # el frente del esqueleto es +Y local: rz que lo encara a p
    d = p - POS; return math.atan2(-d.x, d.y)
def pitch_a(p):
    d = p - (POS + Vector((0, 0, 1.43)));  return math.atan2(d.z, Vector((d.x, d.y)).length)
def con_pitch(p, w, pit):
    q = dict(p)
    for n in ("RightUpArm_skeleton_1", "LeftUpArm_skeleton_1"): q[n] = (q[n][0] - pit * 0.9 * w, q[n][1], q[n][2])
    q["Head_skeleton_1"] = (q["Head_skeleton_1"][0] - pit * 0.6 * w, q["Head_skeleton_1"][1], q["Head_skeleton_1"][2]); return q

# ---------- linea de tiempo: pose, cuerda, rz ----------
TL = {}
# OBJETIVOS REALES: donde se clava cada flecha (las flechas de la escena en su frame de impacto); entre tiros el esqueleto SIGUE mirando/apuntando al siguiente
OBJ = []
for i_, nom in enumerate(("flecha_mano_der", "flecha_mano_izq", "flecha_entrepierna", "flecha_piedra_jerry")):
    o_ = bpy.data.objects.get(nom)
    if o_: sc.frame_set(DISP[i_] + 12); OBJ.append(o_.matrix_world.translation.copy())
    else: OBJ.append([ALF, ALF, ALF, JER][i_])
def objetivo(f):
    """el objetivo al que mira y apunta en el frame f: el del tiro en curso; tras soltar pasa suave (12 f) al siguiente"""
    if f <= DISP[0] + 6: return OBJ[0]
    for i_ in range(1, len(DISP)):
        a_ = DISP[i_ - 1] + 6; b_ = a_ + 12
        if f <= b_: return OBJ[i_ - 1].lerp(OBJ[i_], ss((f - a_) / 12.0))
        if f <= DISP[i_] + 6: return OBJ[i_]
    return OBJ[-1]
yaw_prev = [None]
def yaw_c(p):
    y = yaw_a(p)
    if yaw_prev[0] is not None:
        while y - yaw_prev[0] > math.pi: y -= 2 * math.pi
        while y - yaw_prev[0] < -math.pi: y += 2 * math.pi
    yaw_prev[0] = y; return y
F_SUBE = DISP[0] - 38                                                                       # sube el arco UNA vez y ya no lo baja: tensa/suelta cada tiro y sigue apuntando
for f in range(1, T_CORRE):
    obj = objetivo(f)
    if f < F_SUBE: p, cu, w = dict(PARADO), 0.0, 0.0
    elif f < F_SUBE + 15: p, cu, w = pose17(f - F_SUBE + 1)
    else:
        p, cu, w = pose17(16)
        for s_ in DISP:
            k = f - (s_ - 38) + 1
            if 16 <= k <= 39: p, cu, w = pose17(k)
    giro = 0.0; zb = 0.0
    def mezcla(pa, pb_, t): return {n: tuple(pa[n][i] + (pb_[n][i] - pa[n][i]) * t for i in range(3)) for n in BONES}
    PS = dict(PARADO); PS.update(SUSTO)
    if f >= T_SUSTO:
        obj = OBJ[-1] if f < T_GIRA else obj
        b = ss((f - T_SUSTO) / 4.0); p = mezcla(pose17(16)[0], PS, b); cu = 0.0; w = 1.0 - b; zb = -0.025 * b
        if f >= T_GIRA: b2 = ss((f - T_GIRA) / (T_CORRE - T_GIRA)); p = mezcla(PS, PARADO, b2); w = 0.0; giro = math.pi * b2; zb = -0.025 * (1 - b2)
    pit = pitch_a(obj); q = con_pitch(p, w, pit / 0.9)                                      # brazos: pitch COMPLETO hacia el objetivo
    if w < 1.0: q["Head_skeleton_1"] = (-pit * 0.6, 0.0, 0.0)                               # la cabeza mira al objetivo aunque el arco este abajo
    TL[f] = (q, cu, yaw_c(obj) + giro, POS + Vector((0, 0, zb)))

# ---------- camino de huida: BFS por el suelo libre de la cueva ----------
piso = bpy.data.collections["piso_cueva_parte9"]
llenas = {(math.floor(o.location.x), math.floor(o.location.y)) for o in piso.objects if o.name.startswith("piso_") and abs(o.location.z + 0.5) < 0.01}
ocup = set()
for cn in ("piso_cueva_parte9", "pared_cueva_parte9", "tapa_carbon_parte9"):
    c_ = bpy.data.collections.get(cn)
    if c_:
        for o in c_.objects:
            if o.location.z > 0 and o.location.z < 2.5: ocup.add((math.floor(o.location.x), math.floor(o.location.y)))
libre = {k for k in llenas if k not in ocup}
ini = (math.floor(POS.x), math.floor(POS.y)); prev = {ini: None}; cola = [ini]; dist = {ini: 0}
while cola:
    k = cola.pop(0)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        n_ = (k[0] + dx, k[1] + dy)
        if n_ in libre and n_ not in prev: prev[n_] = k; dist[n_] = dist[k] + 1; cola.append(n_)
VEL = 2.0 / 11.0; LMAX = int((FIN - T_CORRE) * VEL)
meta = max((k for k in dist if dist[k] <= LMAX), key=lambda k: (ini[0] - k[0]) * 1.0 + 0.3 * dist[k])   # lejos hacia -x (lejos de Alfred), sin pasar el largo posible
cam = []; k = meta
while k is not None: cam.append(Vector((k[0] + .5, k[1] + .5, 0.0))); k = prev[k]
cam.reverse(); cam[0] = POS.copy()
seg = [(cam[i], cam[i + 1]) for i in range(len(cam) - 1)]; largo = sum((b - a).length for a, b in seg)
def en_camino(s):
    for a, b in seg:
        l = (b - a).length
        if s <= l: return a.lerp(b, s / l), b - a
        s -= l
    a, b = seg[-1]; return b.copy(), b - a

# ---------- carrera (ciclo CORRER del estudio) ----------
RG = dict(leg_swing_x=math.radians(85), knee_flex=math.radians(72), arm_swing=math.radians(112), elbow_flex=math.radians(85), spine_bend=math.radians(0.18), neck_tilt=math.radians(0.9))
LEAN = 0.12; BOB = 0.06; CICLO = 10.0; AMP_B = 0.7
def knee(ph): return RG["knee_flex"] * max(0.0, math.sin((ph - 0.75) * 2 * math.pi))
def elbow(ph):
    m = RG["elbow_flex"]
    if ph < 0.3: return (-(math.cos(math.pi * ph / 0.3) - 1) / 2) * m * 0.85 + m * 0.15
    if ph < 0.7:
        t = (ph - 0.3) / 0.4; e = 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2; return m - e * m * 0.6
    t = (ph - 0.7) / 0.3; return m * 0.4 - (-(math.cos(math.pi * t) - 1) / 2) * m * 0.25
rz_huye = TL[T_CORRE - 1][2]
for f in range(T_CORRE, FIN + 1):
    s = (f - T_CORRE) * VEL; arranca = ss((f - T_CORRE) / 6.0)
    if s >= largo: p_, d_ = en_camino(largo); quieto = True
    else: p_, d_ = en_camino(s); quieto = False
    wc = ((f - T_CORRE) / CICLO) % 1.0; rc = (wc + 0.5) % 1.0; a = 0.0 if quieto else arranca
    sp = math.sin(wc * 2 * math.pi + math.pi / 6) * RG["spine_bend"] + LEAN * a; st = math.cos(wc * 2 * math.pi + math.pi / 3) * RG["spine_bend"] * 0.75
    p = dict(PARADO)
    for n in ("vertebra_1_skeleton_1", "vertebra_3_skeleton_1", "vertebra_5_skeleton_1"): p[n] = (sp, 0, st)
    p["no_bone_2_skeleton_1"] = (-sp * 0.25, 0, math.sin(wc * 2 * math.pi) * RG["neck_tilt"])
    p["LeftUpLeg_skeleton_1"] = (-RG["leg_swing_x"] * math.sin(wc * 2 * math.pi) * a, 0, 0); p["Leftknee_skeleton_1"] = (knee(wc) * a, 0, 0)
    p["RightUpLeg_skeleton_1"] = (-RG["leg_swing_x"] * math.sin(rc * 2 * math.pi) * a, 0, 0); p["Rightknee_skeleton_1"] = (knee(rc) * a, 0, 0)
    p["RightUpArm_skeleton_1"] = (-RG["arm_swing"] * math.sin(wc * 2 * math.pi) * AMP_B * a, 0, -1.570796); p["Rightelbow_skeleton_1"] = (elbow(wc) * AMP_B * a, 0, 0)
    p["LeftUpArm_skeleton_1"] = (-RG["arm_swing"] * math.sin(rc * 2 * math.pi) * AMP_B * a, 0, 1.570796); p["Leftelbow_skeleton_1"] = (-elbow(rc) * AMP_B * a, 0, 0)
    rz_c = math.atan2(-d_.x, d_.y)
    while rz_c - rz_huye > math.pi: rz_c -= 2 * math.pi
    while rz_c - rz_huye < -math.pi: rz_c += 2 * math.pi
    rz_huye = rz_huye + (rz_c - rz_huye) * 0.35                                                 # gira suave en las esquinas del camino
    TL[f] = (p, 0.0, rz_huye, p_ + Vector((0, 0, (BOB * (0.5 - 0.5 * math.cos(wc * 4 * math.pi)) - 0.20) * a)))   # -0.20: con las piernas abiertas de la carrera los pies no llegaban al suelo (min 0.24)

# ---------- escribir acciones (sin NLA) ----------
def accion(ob, nombre, canales):
    old = bpy.data.actions.get(nombre)
    if old: bpy.data.actions.remove(old)
    if ob.animation_data:
        for tr in list(ob.animation_data.nla_tracks): ob.animation_data.nla_tracks.remove(tr)
    ob.animation_data_create(); a = bpy.data.actions.new(nombre); ob.animation_data.action = a
    slot = a.slots.new(id_type='OBJECT', name=ob.name); ob.animation_data.action_slot = slot
    cb = a.layers.new("Capa").strips.new(type='KEYFRAME').channelbag(slot, ensure=True)
    for (dp, i), pts in canales.items():
        fc = cb.fcurves.new(dp, index=i); fc.keyframe_points.add(len(pts)); fc.keyframe_points.foreach_set("co", [v for p_ in pts for v in p_])
        for k_ in fc.keyframe_points: k_.interpolation = 'LINEAR'
        fc.update()
fs = sorted(TL)
for b in A.pose.bones: b.rotation_mode = 'XYZ'
canA = {}
for n in BONES:
    for i in range(3): canA[('pose.bones["%s"].rotation_euler' % n, i)] = [(f, TL[f][0][n][i]) for f in fs]
accion(A, "p9_esqueleto_arma", canA)
accion(BOW, "p9_esqueleto_arco", {('pose.bones["Shooting_skeleton_1"].location', 0): [(f, TL[f][1]) for f in fs]})
canR = {("location", i): [(f, TL[f][3][i]) for f in fs] for i in range(3)}; canR[("rotation_euler", 2)] = [(f, TL[f][2]) for f in fs]
canR[("rotation_euler", 0)] = [(1, 0.0)]; canR[("rotation_euler", 1)] = [(1, 0.0)]
accion(R, "p9_esqueleto_root", canR)
# ---------- APOYO EN EL SUELO durante la carrera: cada frame la malla minima a z 0 (las piernas abiertas del ciclo subian/hundian el cuerpo -0.20..+0.42) ----------
MS = [o for o in bpy.data.collections["esqueleto_parte9"].all_objects if o.type == 'MESH' and o.name != "Cube.001_1"]
fcz = next(c for c in R.animation_data.action.layers[0].strips[0].channelbags[0].fcurves if c.data_path == "location" and c.array_index == 2)
corr = {}
for f in range(T_CORRE, FIN + 1):
    sc.frame_set(f); dg_ = bpy.context.evaluated_depsgraph_get()
    corr[f] = min((o.evaluated_get(dg_).matrix_world @ v.co).z for o in MS for v in o.evaluated_get(dg_).data.vertices)
for kp in fcz.keyframe_points:
    f = int(round(kp.co[0]))
    if f in corr: kp.co[1] -= corr[f]
fcz.update()
bpy.data.objects["Cube.001_1"].hide_viewport = True; bpy.data.objects["Cube.001_1"].hide_render = True   # cubo suelto del .blend del esqueleto (lejos, en x 10.8)
# ---------- origen de las flechas: la cuerda al soltar, mirando a Alfred ----------
sc.frame_set(DISP[0]); bpy.context.view_layer.update()
sc["p9_arco_S"] = list(BOW.matrix_world @ BOW.pose.bones["Shooting_skeleton_1"].head)
print("ESQUELETO: tiros", DISP, "S", [round(v, 2) for v in sc["p9_arco_S"]], "huye", round(largo, 1), "m hasta", meta)
