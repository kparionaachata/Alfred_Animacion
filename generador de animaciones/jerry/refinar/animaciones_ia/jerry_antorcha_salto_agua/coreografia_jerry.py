import bpy, math, pickle, os
from mathutils import Vector
P = globals().get("PARAMS", {})
BIAS = P.get("bias", 38.0)          # grados que la cabeza base mira por debajo del objetivo
TURN = P.get("turn", 6.5)           # grados/frame de giro del cuerpo hacia Alfred
YAWK = P.get("yawk", 1.0)
JAW = P.get("jaw", 44.0)          # apertura maxima de la mandibula al hablar (grados)
sc = bpy.context.scene
arm = bpy.data.objects["Dog_001_rig"]; root = bpy.data.objects["jerry"]
scr = r"C:\Users\user\AppData\Local\Temp\claude\C--Users-user-Desktop-Alfred-Animacion\d930d14a-d5ee-4666-8fac-0136f635075d\scratchpad"
D = pickle.load(open(os.path.join(scr, "jerry_base.pkl"), "rb"))
base, rootS, H, A = D["base"], D["root"], D["H"], D["A"]
N = 561
rad = math.radians
def ss(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)
def ramp(f, a, b): return ss((f - a) / (b - a)) if b > a else (1.0 if f >= a else 0.0)
def bump(f, a, pk, b): return ramp(f, a, pk) * (1 - ramp(f, pk, b))
def hold(f, a, a2, b2, b): return ramp(f, a, a2) * (1 - ramp(f, b2, b))
delta = {b: {f: [0.0, 0.0, 0.0] for f in range(1, N + 1)} for b in base}
def add(b, f, x=0.0, y=0.0, z=0.0):
    d = delta[b][f]; d[0] += rad(x); d[1] += rad(y); d[2] += rad(z)
def env_org(f):
    if f <= 38: return 0.35
    if f <= 74: return 0.3
    if f <= 126: return 0.25
    return 0.25 + 0.75 * ramp(f, 126, 150)
# --- salto: impulso y fluidez de patas ---
for f in range(74, 142):
    ant = bump(f, 75, 81, 85); push = bump(f, 83, 87, 92); fly = hold(f, 88, 94, 116, 124); brace = bump(f, 114, 124, 130); land = bump(f, 124, 129, 140)
    for s in ("spine_4", "spine_5"): add(s, f, x=9 * ant - 8 * push - 5 * fly + 11 * land)
    add("spine_3", f, x=5 * ant - 4 * push - 6 * fly + 6 * land)
    for lg in ("thigh.L", "thigh.R"): add(lg, f, x=18 * ant - 30 * push - 22 * fly + 12 * brace + 16 * land)
    for fs in ("front_shoulder.L", "front_shoulder.R"): add(fs, f, x=-8 * ant + 30 * push + 36 * fly + 22 * brace - 6 * land)
    for ft in ("front_thigh.L", "front_thigh.R"): add(ft, f, x=16 * fly + 10 * brace)
    for i, t in enumerate(("tail_1", "tail_2", "tail_3")): add(t, f, x=(-10 - 4 * i) * (push + fly) + 6 * land)
    add("scull_1", f, x=-8 * fly + 6 * land)
# --- flotar: nado suave de patas ---
for f in range(132, N + 1):
    e = ramp(f, 128, 148) * (1 + 1.2 * bump(f, 128, 140, 168)); ph = 2 * math.pi * f / 36.0
    add("front_shoulder.L", f, x=10 * e * math.sin(ph)); add("thigh.R", f, x=8 * e * math.sin(ph)); add("thigh.L", f, x=-8 * e * math.sin(ph))
    if not (258 <= f <= 350): add("front_shoulder.R", f, x=-10 * e * math.sin(ph))
# --- cuerpo gira hacia Alfred y la cabeza lo sigue ---
rz = {f: rootS[f][1][2] for f in range(1, N + 1)}
def angdiff(a, b): return (a - b + math.pi) % (2 * math.pi) - math.pi
prev = rz[133]
for f in range(134, N + 1):
    v = Vector(A[f]) - Vector(rootS[f][0])
    des = math.atan2(-v.x, v.y)
    step = max(-rad(TURN), min(rad(TURN), angdiff(des, prev)))
    prev = prev + step * ramp(f, 134, 142)
    rz[f] = prev
for f in range(134, N + 1):
    v = Vector(A[f]) - Vector(H[f]); vh = math.hypot(v.x, v.y)
    fwd = Vector((-math.sin(rz[f]), math.cos(rz[f]), 0)); left = Vector((-fwd.y, fwd.x, 0))
    yaw = max(-rad(70), min(rad(70), math.atan2(v.dot(left), v.dot(fwd))))
    elev = math.degrees(math.atan2(v.z, vh)) + BIAS
    w = ramp(f, 134, 146) * (1 - 0.7 * bump(f, 262, 276, 340))
    add("scull_1", f, x=-elev * 0.6 * w, y=math.degrees(yaw) * 0.55 * YAWK * w)
    add("scull", f, x=-elev * 0.2 * w)
    add("spine_1", f, x=-elev * 0.2 * w, y=math.degrees(yaw) * 0.2 * YAWK * w)
    add("spine_2", f, y=math.degrees(yaw) * 0.25 * YAWK * w)
# --- alentar a Alfred ---
for (a, b) in ((160, 170), (174, 184), (188, 198)):
    for f in range(a, b + 1):
        pulse = math.sin(math.pi * (f - a) / (b - a)); add("jaw_bot", f, x=-JAW * pulse); add("scull_1", f, x=-7 * pulse)
for f in range(160, 204):
    g = bump(f, 160, 170, 180) + bump(f, 180, 190, 200); add("front_shoulder.L", f, x=42 * g); add("front_thigh.L", f, x=22 * g)
for f in range(212, 251): add("jaw_bot", f, x=-JAW * 0.6 * hold(f, 212, 222, 244, 251))
for f in range(134, N + 1):
    e = (1.0 if f < 262 else 0.25 + 0.45 * ramp(f, 352, 400)) * ramp(f, 134, 146)
    for i, t in enumerate(("tail_1", "tail_2", "tail_3")):
        add(t, f, z=math.degrees([0.40, 0.29, 0.19][i]) * e * math.sin(2 * math.pi * f * 0.125 - i * 0.55))

# --- Jerry le habla a Alfred tras verlo flotar (frames 416-478) ---
for (a, b, amp) in ((416, 432, JAW * 0.86), (438, 458, JAW), (464, 478, JAW * 0.93)):
    sil = (b - a) / 4.6
    for f in range(a, b + 1):
        u = (f - a) / (b - a)
        env = min(1.0, u / 0.12, (1 - u) / 0.15)
        s_ = max(0.0, math.sin(2 * math.pi * sil * u))
        add("jaw_bot", f, x=-amp * env * s_)
        add("scull_1", f, x=-3.5 * env * s_ - 7 * bump(f, a, (a + b) / 2, b))
        add("ear.L", f, x=6 * env); add("ear.R", f, x=6 * env)
# --- decepcion: pata derecha al rostro ---
FACE = {"front_shoulder.R": (26, -7.5, 8.6), "front_thigh.R": (-3.1, 5.5, 7.5), "front_shin.R": (108.4, 20.1, 10.9), "front_foot.R": (35.8, 12.1, 3.6)}
for f in range(256, 360):
    k = ramp(f, 256, 274) * (1 - ramp(f, 336, 354))
    for b, (x, y, z) in FACE.items(): add(b, f, x=x * k, y=y * k, z=z * k)
    shake = k * math.sin(2 * math.pi * (f - 274) / 22.0) * ramp(f, 274, 284)
    add("scull_1", f, x=12 * k, y=16 * shake); add("spine_2", f, y=6 * shake)
    add("ear.L", f, x=-10 * k); add("ear.R", f, x=-10 * k)
# --- filtros organicos ---
for f in range(1, N + 1):
    e = env_org(f); br = math.sin((f - 1) * 0.0125 * 2 * math.pi * 2.0)
    add("spine_5", f, x=0.65 * br * e, z=0.25 * math.sin(f * 0.031) * e)
    add("spine_4", f, x=0.85 * math.sin((f - 1) * 0.0125 * 2 * math.pi * 2.0 - 0.3) * e, z=0.25 * math.sin(f * 0.027 + 1.0) * e)
    add("spine_6", f, z=0.45 * math.sin(f * 0.023 + 0.6) * e)
    add("scull_1", f, y=1.5 * math.sin(f * 0.070 + 0.4) * e, x=0.8 * math.sin(f * 0.052) * e)
    add("ear.L", f, z=3.0 * math.sin(f * 0.21 + 0.3) * e); add("ear.R", f, z=3.0 * math.sin(f * 0.19 + 2.0) * e)
for f in range(1, N + 1):
    for b in base:
        d = delta[b][f]
        if f > 1 and f < 74 and not any(abs(v) > 1e-9 for v in d): continue
        pb = arm.pose.bones[b]; v0 = base[b][f]
        pb.rotation_euler = (v0[0] + d[0], v0[1] + d[1], v0[2] + d[2]); pb.keyframe_insert(data_path="rotation_euler", frame=f)
for f in range(127, N + 1):
    loc, rot = rootS[f]
    t = f - 127
    w = 2 * math.pi / 34.0
    A_, B_ = 0.229, (-0.06 + 0.229 / 14.0) / w
    ent = math.exp(-t / 14.0) * (A_ * math.cos(w * t) + B_ * math.sin(w * t))      # zambullida y rebote amortiguado
    flot = (0.04 * math.sin(2 * math.pi * f / 64.0) + 0.015 * math.sin(2 * math.pi * f / 27.0)) * ramp(f, 150, 175)
    z = 7.66 + ent + flot
    rx = 0.09 * math.exp(-t / 16.0) * math.sin(w * t + 0.6) + 0.05 * math.sin(2 * math.pi * f / 70.0) * ramp(f, 150, 175)
    ry = 0.035 * math.sin(2 * math.pi * f / 45.0) * ramp(f, 150, 175)
    root.location = (loc[0], loc[1], z)
    root.rotation_euler = (rx, ry, rz[f])
    root.keyframe_insert("location", frame=f); root.keyframe_insert("rotation_euler", frame=f)

# --- expresiones por las cejas (sejas_1_jerry / sejas_2_jerry) ---
EMO = {
 "enojado": {"sejas_1_jerry": ((0.018057, 0.032724, 0.466682), (0.00746, -0.011135, 0.000709)), "sejas_2_jerry": ((0.059813, -0.027015, -0.463214), (0.020687, -0.018262, 0.005866))},
 "triste": {"sejas_1_jerry": ((0.002696, -0.051839, -0.649442), (0.008732, -0.027737, 0.001994)), "sejas_2_jerry": ((-0.046540, 0.063158, 0.554100), (0.020013, -0.031002, 0.003717))},
 "sorprendido": {"sejas_1_jerry": ((0.001155, -0.049993, -0.613817), (0.019916, -0.009849, -0.000639)), "sejas_2_jerry": ((-0.047893, 0.064076, 0.570414), (0.010334, -0.010014, 0.000792))},
 "levanta_la_ceja_derecha": {"sejas_1_jerry": ((-0.001606, -0.008090, -0.098054), (0.019472, -0.003857, -0.000569)), "sejas_2_jerry": ((-0.020113, 0.020089, 0.198146), (0.00855, -0.031592, 0.002454))},
 "levanta_la_ceja_izquierda": {"sejas_1_jerry": ((-0.002724, -0.014304, -0.180244), (0.016415, -0.030631, 0.001622)), "sejas_2_jerry": ((-0.020113, 0.020089, 0.198146), (0.01384, 0.000266, 0.000305))},
}
BASEB = {"sejas_1_jerry": (0.006569, 0.000489, -0.000191), "sejas_2_jerry": (0.013395, -0.000836, 0.003522)}
E = {"e": "enojado", "t": "triste", "s": "sorprendido", "d": "levanta_la_ceja_derecha", "i": "levanta_la_ceja_izquierda"}
LINEA = [
 (1, {}), (20, {"e": .25}), (46, {"e": .5}), (56, {"e": .9}), (66, {"e": .3}), (82, {"s": .4}), (100, {"s": .65}), (120, {"s": .8}), (127, {"s": 1.0}), (140, {"s": .7}),
 (150, {"d": .8}), (162, {"s": .5}), (166, {"i": .8}), (174, {"s": .6}), (180, {"d": .9}), (188, {"s": .5}), (194, {"i": .8}), (204, {"s": .6}),
 (225, {"s": .85}), (245, {"s": 1.0}), (252, {"s": 1.0}), (262, {"t": .6, "s": .3}), (280, {"t": 1.0}), (330, {"t": 1.0}), (356, {"t": .6}),
 (380, {"t": .4, "i": .4}), (412, {"i": .5, "t": .2}), (416, {"e": .45}), (420, {"e": .45, "d": .7}), (426, {"e": .5}), (440, {"e": .5, "d": .8}),
 (450, {"e": .55}), (466, {"e": .5, "i": .7}), (474, {"e": .6}), (486, {"e": .3}), (505, {"s": .4, "t": .2}), (525, {"s": .7}), (561, {"s": .6}),
]
def pesos(f):
    for i in range(len(LINEA) - 1):
        (fa, wa), (fb, wb) = LINEA[i], LINEA[i + 1]
        if fa <= f <= fb:
            t = ss((f - fa) / (fb - fa)) if fb > fa else 1.0
            return {k: wa.get(k, 0.0) + (wb.get(k, 0.0) - wa.get(k, 0.0)) * t for k in set(wa) | set(wb)}
    return dict(LINEA[-1][1])
for f in range(1, N + 1):
    w = pesos(f)
    for br in ("sejas_1_jerry", "sejas_2_jerry"):
        rot = [0.0, 0.0, 0.0]; loc = list(BASEB[br])
        for k, wv in w.items():
            er, el = EMO[E[k]][br]
            for a in range(3):
                rot[a] += wv * er[a]
                loc[a] += wv * (el[a] - BASEB[br][a])
        pb = arm.pose.bones[br]; pb.rotation_mode = "XYZ"
        pb.rotation_euler = rot; pb.location = loc
        pb.keyframe_insert("rotation_euler", frame=f); pb.keyframe_insert("location", frame=f)
alf = bpy.data.objects["Armature"]
res = []
for f in range(140, 561, 20):
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get(); ae = arm.evaluated_get(dg); aa = alf.evaluated_get(dg); mw = ae.matrix_world
    pb = ae.pose.bones["scull"]
    gaze = (mw @ pb.tail) - (mw @ pb.head)
    tgt = (aa.matrix_world @ aa.pose.bones["Neck_alfred"].head) - (mw @ pb.head)
    yaw = math.degrees(Vector((gaze.x, gaze.y, 0)).normalized().angle(Vector((tgt.x, tgt.y, 0)).normalized()))
    pit = math.degrees(math.atan2(gaze.z, math.hypot(gaze.x, gaze.y))) - math.degrees(math.atan2(tgt.z, math.hypot(tgt.x, tgt.y)))
    res.append((f, round(yaw), round(pit)))
sc.frame_set(1)
RESULT_COREO = res
