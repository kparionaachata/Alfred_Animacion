# -*- coding: utf-8 -*-
"""
Jerry despierta (capitulo 4, base_ranas_2.blend).

Duerme en el bloque de seta (ojos cerrados, respira) -> se estira y se le cae el sombrero ->
abre los ojos, se levanta, baja del bloque, recoge el sombrero con la boca y se lo lanza a la
cabeza -> se da la vuelta para volver a subir, ve la pelea del cuadrilatero al fondo -> camina
media ruta de Desktop/jerry_recorrido.json (puntos 1-9) y la camara lo sigue.

Uso (exec en Blender):  iniciar()   # prepara, pasada de suelo por timer y escribe las claves
Estado: bpy.app.driver_namespace["jerry_despierta"]
Las acciones anteriores (jerry_durmiendo, jerryAction) se conservan con fake user.
"""
import bpy, json, math
import numpy as np
from mathutils import Vector, Matrix, Euler, Quaternion

BASE = "C:/Users/user/Desktop/Alfred_Animacion/"
ANIM = BASE + "generador de animaciones/jerry/refinar/animaciones/"
RUTA = "C:/Users/user/Desktop/jerry_recorrido.json"
N_RUTA = 9                                   # mitad del recorrido (17 puntos)
FPB = 12.43                                  # frames por bloque caminando
RECORTE = 0.8                                # se detiene 0.8 m antes del punto 9 (el guardian 17 pasa por ahi)
CAM_SUBE = 1.3                               # la camara sube al seguirlo (el bloque de seta lo tapaba)
ARM, ROOT, HAT, LIBRE = "Dog_001_rig", "jerry", "sombrero_jerry", "sombrero_jerry_libre"
CAM, FOCO = "Camera.001", "Foco_Camara"
OJOS = ["ojo_izquierdo_jerry", "ojo_derecho_jerry", "pupila_izquierda_jerry", "pupila_derecha_jerry"]
RING = Vector((-37.5, -12.0))
D = math.radians

# ---------------------------------------------------------------- tiempos
F_STR = (92, 108, 122, 138)                  # estiron: sube, pico, mantiene, suelta
F_HAT0, F_HAT_HIT, F_HAT_REST = 112, 124, 146
F_EYES = (140, 147)
F_LOOK = (148, 160)
F_UP = (168, 194)
F_JUMP = 198                                 # 24 f (estudio saltar_bajar)
F_PICK = (224, 236, 239, 250)                # baja cabeza, boca abierta, muerde, levanta
F_TOSS = (252, 258, 262, 268)                # prepara, lanza (suelta en 262), cae en la cabeza
F_TURN = (282, 306)
F_SEE = (312, 316, 320, 326)                 # mira arriba, vistazo, vuelve, fija en el ring
F_GO = 364
BLINKS = [155, 213, 244, 300, 323, 395, 455]

J_BED = Vector((-7.5, -23.289)); H_BED = -80.0; Z_BED = 10.035
J_TOP = Vector((-7.45, -23.40)); H_TOP = -90.0
J_LAND = Vector((-5.55, -23.40))
HAT_HIT = Vector((-6.55, -23.55))


def P(d):
    return {b: tuple(D(v) for v in vals) for b, vals in d.items()}


STRETCH = P({"front_shoulder.L": (38, 0, 0), "front_shoulder.R": (34, 0, 0), "shoulder.L": (-30, 0, 0), "shoulder.R": (-26, 0, 0),
             "spine_4": (-6, 0, 0), "spine_5": (-4, 0, 0), "spine_1": (-10, 0, 0), "scull_1": (-18, 0, 0),
             "jaw_bot": (-28, 0, 0), "jaw_top": (10, 0, 0), "tail_1": (-15, 0, 0), "tail_2": (-10, 0, 0),
             "ear.L": (0, 0, -15), "ear.R": (0, 0, 15), "toe.L": (-20, 0, 0), "toe.R": (-20, 0, 0)})
LOOK_HAT = P({"scull_1": (-12, 0, 0), "spine_1": (-8, 0, 0), "ear.L": (-8, 0, 0), "ear.R": (-8, 0, 0)})
STAND_DOWN = P({"spine_1": (18, 0, 0), "scull_1": (14, 0, 0), "ear.L": (-10, 0, 0), "ear.R": (-10, 0, 0)})
PICK_OPEN = P({"spine_2": (12, 0, 0), "spine_1": (30, 0, 0), "scull_1": (28, 0, 0), "spine_4": (6, 0, 0),
               "front_shoulder.L": (-8, 0, 0), "front_shoulder.R": (-8, 0, 0), "jaw_bot": (-24, 0, 0), "jaw_top": (6, 0, 0)})
PICK_BITE = dict(PICK_OPEN); PICK_BITE.update(P({"jaw_bot": (-7, 0, 0), "jaw_top": (0, 0, 0)}))
HOLD = P({"spine_1": (-6, 0, 0), "scull_1": (-4, 0, 0), "jaw_bot": (-7, 0, 0)})
TOSS_PREP = P({"spine_1": (22, 0, 0), "scull_1": (18, 0, 0), "jaw_bot": (-7, 0, 0), "spine_4": (4, 0, 0)})
TOSS_UP = P({"spine_1": (-22, 0, 0), "scull_1": (-25, 0, 0), "jaw_bot": (-22, 0, 0), "jaw_top": (6, 0, 0)})
CATCH = P({"spine_1": (5, 0, 0), "scull_1": (6, 0, 0)})
CLIMB = P({"scull_1": (-14, 0, 0), "spine_1": (-6, 0, 0), "spine_4": (4, 0, 0), "shoulder.L": (6, 0, 0), "shoulder.R": (6, 0, 0)})


# pose del usuario cuando Jerry se da cuenta de la pelea (frame 357)
NOTA = P({"spine_6": (5.8963, -21.732, -30.037), "scull_1": (-2.8118, 4.9413, -7.4797)})
CAMARA = False                               # False: no rehace la camara ni el foco (la camara inicial la fijo el usuario)


def SEE(yaw, k=1.0):
    """mira al ring: yaw = rumbo del ring - rumbo del cuerpo (grados). Z local (hacia abajo) = -yaw."""
    return P({"spine_1": (-8 * k, 0, -0.5 * yaw * k), "scull_1": (-6 * k, 0, -0.5 * yaw * k),
              "ear.L": (-14 * k, 0, 0), "ear.R": (-14 * k, 0, 0)})


# ---------------------------------------------------------------- utilidades de pose
def add(a, b, k=1.0):
    r = dict(a)
    for n, v in b.items():
        base = r.get(n, (0, 0, 0)); r[n] = tuple(base[i] + k * v[i] for i in range(3))
    return r


def mix(a, b, t):
    if t <= 0: return dict(a)
    if t >= 1: return dict(b)
    r = {}
    for n in set(a) | set(b):
        if n.startswith("L:"):
            va, vb = a.get(n, (0, 0, 0)), b.get(n, (0, 0, 0)); r[n] = tuple(va[i] + (vb[i] - va[i]) * t for i in range(3))
        else:
            qa = Euler(a.get(n, (0, 0, 0))).to_quaternion(); qb = Euler(b.get(n, (0, 0, 0))).to_quaternion()
            r[n] = tuple(qa.slerp(qb, t).to_euler('XYZ'))
    return r


def ss(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


def ramp(f, a, b):
    return ss((f - a) / max(1e-6, b - a))


def ring_heading(p):
    d = RING - Vector(p[:2]); return math.degrees(math.atan2(-d.x, d.y))


# ---------------------------------------------------------------- ciclos del estudio de Jerry
def _cargar(fichero, nombre):
    ns = {"__name__": nombre}
    exec(compile(open(ANIM + fichero, encoding="utf8").read(), fichero, "exec"), ns)
    return ns


def walk_pose(cyc, n, amp=1.0):
    kf = {}
    for side, il in (("L", True), ("R", False)):
        kf["shoulder." + side] = cyc.leg_slow_walk(n, True, il)
        kf["shin." + side] = cyc.leg_bend(n, True, il)
        kf["foot." + side] = cyc.foot_strike(n, True, il)
        kf["toe." + side] = cyc.toe_curl(n, True, il)
        kf["front_shoulder." + side] = cyc.leg_slow_walk(n + 12, False, il)
        kf["front_shin." + side] = cyc.leg_bend(n + 12, False, il)
        kf["front_foot." + side] = cyc.foot_strike(n + 12, False, il)
        kf["front_toe." + side] = cyc.toe_curl(n + 12, False, il)
    kf["thigh.L"] = tuple(x * 0.01 for x in cyc.leg_slow_walk(n, True, True))
    kf["thigh.R"] = tuple(x * -0.3 for x in cyc.leg_slow_walk(n, True, False))
    kf["front_thigh.L"] = tuple(x * 0.6 for x in cyc.leg_slow_walk(n + 12, False, True))
    kf["front_thigh.R"] = tuple(x * 0.4 for x in cyc.leg_slow_walk(n + 12, False, False))
    for i in range(1, 8): kf["spine_%d" % i] = cyc.spine_undulation(n, i, 7)
    for i in range(1, 4): kf["tail_%d" % i] = cyc.tail_wag_alert(n)
    sn, lk, tl = cyc.sniff_down(n), cyc.look_around(n), cyc.head_tilt(n)
    kf["scull"] = (sn[0] + tl[0] * 0.3, lk[1], tl[2])
    kf["ear.L"] = cyc.ear_twitch(n); kf["ear.R"] = cyc.ear_twitch(n + 6)
    return {b: tuple(v * amp for v in r) for b, r in kf.items()}


def jump_pose(jkf, n):
    return {b: tuple(fr[n]) for b, fr in jkf.items() if b not in ("jaw_top", "sombrero")}


# ---------------------------------------------------------------- ruta
def ruta():
    kp = json.load(open(RUTA, encoding="utf8"))["key_points"][:N_RUTA]
    pts = [J_LAND, Vector((-6.3, -22.6)), Vector((-7.5, -22.45))] + [Vector((p["coordinates"]["x"], p["coordinates"]["y"])) for p in kp[1:]]
    for _ in range(3):                                                     # Chaikin conservando extremos
        q = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]): q += [a.lerp(b, 0.25), a.lerp(b, 0.75)]
        q.append(pts[-1]); pts = q
    acum = [0.0]
    for a, b in zip(pts[:-1], pts[1:]): acum.append(acum[-1] + (b - a).length)
    return pts, acum


def en_ruta(pts, acum, s):
    s = max(0.0, min(acum[-1], s))
    for i in range(1, len(acum)):
        if acum[i] >= s:
            t = (s - acum[i - 1]) / max(1e-9, acum[i] - acum[i - 1]); return pts[i - 1].lerp(pts[i], t)
    return pts[-1].copy()


# ---------------------------------------------------------------- plan por frame
def plan():
    arm = bpy.data.objects[ARM]
    from bpy_extras.anim_utils import action_get_channelbag_for_slot
    act = bpy.data.actions["jerry_durmiendo"]
    cb = action_get_channelbag_for_slot(act, act.slots[0])
    sleep = {}
    for fc in cb.fcurves:
        b = fc.data_path.split('"')[1]; v = fc.evaluate(1)
        if fc.data_path.endswith("rotation_euler"):
            t = list(sleep.get(b, (0, 0, 0))); t[fc.array_index] = v; sleep[b] = tuple(t)
        elif fc.data_path.endswith("location"):
            t = list(sleep.get("L:" + b, (0, 0, 0))); t[fc.array_index] = v; sleep["L:" + b] = tuple(t)
    walk_ns = _cargar("slot_004_jerry_caminar.py", "slot4"); jump_ns = _cargar("slot_003_jerry_saltar_bajar.py", "slot3")
    cyc = walk_ns["SniffingSearchCycle"](cycle_length=25, total_frames=9999)
    jkf = jump_ns["generate_keyframes"](24)
    pts, acum = ruta(); L = acum[-1] - RECORTE; n_walk = int(round(L * FPB)); F_END_WALK = F_GO + n_walk
    F_END = F_END_WALK + 30
    # avance con arranque y frenado suaves
    vel = np.ones(n_walk + 1)
    for i in range(n_walk + 1):
        vel[i] = min(1.0, ss(i / 12.0) + 0.05, ss((n_walk - i) / 14.0) + 0.05)
    s_acc = np.concatenate([[0], np.cumsum(vel[1:])]); s_acc *= L / s_acc[-1]

    stand = {}
    frames = {}
    head = H_BED; heads = {}
    h_walk = None
    for f in range(1, F_END + 1):
        br = math.sin(2 * math.pi * f / 64.0)
        breath = P({"spine_4": (2.2 * br, 0, 0), "spine_5": (1.3 * br, 0, 0), "spine_3": (0.8 * br, 0, 0)})
        breath_st = P({"spine_4": (0.8 * br, 0, 0), "spine_5": (0.5 * br, 0, 0)})
        wag = lambda k, per=14: P({"tail_1": (-18 * k, 0, 18 * k * math.sin(2 * math.pi * f / per)), "tail_2": (0, 0, 14 * k * math.sin(2 * math.pi * f / per - 0.6)),
                                   "tail_3": (0, 0, 10 * k * math.sin(2 * math.pi * f / per - 1.2))})
        xy, hd, G = J_BED.copy(), H_BED, 10.0
        if f < F_STR[0]:
            pose = add(sleep, breath)
            if 38 <= f <= 46: pose = add(pose, P({"ear.L": (0, 0, 10 * math.sin(math.pi * (f - 38) / 8))}))
        elif f < F_STR[3] + 1:
            k = ramp(f, F_STR[0], F_STR[1]) if f < F_STR[2] else 1 - ramp(f, F_STR[2], F_STR[3])
            if F_STR[1] <= f < F_STR[2]: k += 0.06 * math.sin(2 * math.pi * f / 5.0)
            pose = add(add(sleep, breath, 0.4), STRETCH, k)
        elif f < F_UP[0]:
            pose = add(add(sleep, breath, 0.6), LOOK_HAT, ramp(f, F_LOOK[0], F_LOOK[1]))
        elif f < F_UP[1]:
            t = ramp(f, F_UP[0], F_UP[1])
            pose = mix(add(sleep, LOOK_HAT), STAND_DOWN, t)
            xy = J_BED.lerp(J_TOP, t); hd = H_BED + (H_TOP - H_BED) * t
        elif f < F_JUMP:
            pose = add(STAND_DOWN, breath_st); xy, hd = J_TOP.copy(), H_TOP
        elif f < F_JUMP + 24:
            n = f - F_JUMP + 1
            jp = jump_pose(jkf, n)
            pose = mix(STAND_DOWN, jp, ramp(n, 1, 4)) if n <= 4 else jp
            if n >= 21: pose = mix(jp, {b: tuple(v * 0.5 for v in r) for b, r in STAND_DOWN.items()}, ramp(n, 21, 24))
            s = min(1.0, max(0.0, (n - 7) / 14.0)) if 7 <= n <= 21 else (1.0 if n > 21 else 0.0)
            xy = J_TOP.lerp(J_LAND, s); hd = H_TOP; G = 10.0 + (9.0 - 10.0) * s
        else:
            xy, hd, G = J_LAND.copy(), H_TOP, 9.0
            half_down = {b: tuple(v * 0.5 for v in r) for b, r in STAND_DOWN.items()}
            if f < F_PICK[0]:
                pose = half_down
            elif f < F_PICK[2]:
                pose = mix(half_down, PICK_OPEN, ramp(f, F_PICK[0], F_PICK[1]))
                if f >= F_PICK[1]: pose = mix(PICK_OPEN, PICK_BITE, ramp(f, F_PICK[1], F_PICK[2]))
            elif f < F_TOSS[0]:
                pose = add(mix(PICK_BITE, HOLD, ramp(f, F_PICK[2], F_PICK[3])), wag(0.6, 10), ramp(f, F_PICK[3], F_TOSS[0]))
            elif f < F_TOSS[3]:
                if f < F_TOSS[1]: pose = mix(HOLD, TOSS_PREP, ramp(f, F_TOSS[0], F_TOSS[1]))
                elif f < F_TOSS[2]: pose = mix(TOSS_PREP, TOSS_UP, ramp(f, F_TOSS[1], F_TOSS[2]))
                else: pose = mix(TOSS_UP, CATCH, ramp(f, F_TOSS[2], F_TOSS[3]))
            elif f < F_TURN[0]:
                t = ramp(f, F_TOSS[3], F_TOSS[3] + 8)
                shake = P({"scull_1": (0, 10 * math.sin(2 * math.pi * (f - F_TOSS[3]) / 6.0) * (1 - ramp(f, F_TOSS[3] + 2, F_TOSS[3] + 12)), 0)})
                pose = add(add(mix(CATCH, {}, t), shake), wag(1.0, 9))
                pose = add(pose, breath_st)
            elif f < F_TURN[1]:
                t = ramp(f, F_TURN[0], F_TURN[1])
                k = min(ramp(f, F_TURN[0], F_TURN[0] + 4), 1 - ramp(f, F_TURN[1] - 4, F_TURN[1]))
                pose = mix({}, walk_pose(cyc, f - F_TURN[0] + 1, 0.7), k)
                hd = H_TOP - 180.0 * t
            else:
                hd = H_TOP - 180.0                                         # -270 = mira al oeste (al bloque)
                yaw_full = ((ring_heading(xy) - hd + 180) % 360) - 180
                if f < F_SEE[1]:
                    pose = mix({}, CLIMB, ramp(f, F_TURN[1], F_SEE[0] + 2))
                elif f < F_SEE[2]:
                    pose = mix(CLIMB, add(CLIMB, SEE(yaw_full * 0.35, 0.5)), ramp(f, F_SEE[1], F_SEE[1] + 2) - ramp(f, F_SEE[1] + 3, F_SEE[2]))
                elif f < F_GO:
                    # el cuerpo gira un poco hacia el ring mientras mira
                    hd = H_TOP - 180.0 + 12.0 * ramp(f, 334, 352)
                    yaw = ((ring_heading(xy) - hd + 180) % 360) - 180
                    see = SEE(yaw); see.update(NOTA)                                # valores del usuario al darse cuenta
                    pose = mix(CLIMB, see, ramp(f, F_SEE[2], F_SEE[3]))
                    pose = add(pose, wag(ramp(f, 344, 350), 10))
                    pose = add(pose, breath_st)
                    if f >= F_GO - 6: pose = mix(pose, walk_pose(cyc, 1), ramp(f, F_GO - 6, F_GO))
                else:
                    i = min(f - F_GO, n_walk)
                    p = en_ruta(pts, acum, float(s_acc[i])); xy = p
                    tang = en_ruta(pts, acum, float(s_acc[i]) + 0.45) - en_ruta(pts, acum, max(0.0, float(s_acc[i]) - 0.05))
                    target = math.degrees(math.atan2(-tang.x, tang.y)) if tang.length > 1e-4 else h_walk
                    if h_walk is None: h_walk = H_TOP - 180.0 + 12.0
                    dif = ((target - h_walk + 180) % 360) - 180
                    h_walk += max(-4.0, min(4.0, dif * 0.22)); hd = h_walk
                    wp = walk_pose(cyc, f - F_GO + 1)
                    if f <= F_END_WALK:
                        pose = wp
                        if f > F_END_WALK - 10: pose = mix(wp, {}, ramp(f, F_END_WALK - 10, F_END_WALK))
                    else:
                        yaw = ((ring_heading(xy) - hd + 180) % 360) - 180
                        pose = add(mix({}, SEE(yaw, 0.8), ramp(f, F_END_WALK, F_END_WALK + 10)), breath_st)
        frames[f] = dict(pose=pose, xy=Vector(xy), hd=hd, G=G)
    return dict(frames=frames, F_END=F_END, F_END_WALK=F_END_WALK, n_walk=n_walk, L=L)


# ---------------------------------------------------------------- pasada de suelo (timer)
def aplicar_pose(arm, root, fr, z=0.0):
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = fr["pose"].get(pb.name, (0, 0, 0))
        pb.location = fr["pose"].get("L:" + pb.name, (0, 0, 0))
        pb.scale = (1, 1, 1)
    root.location = (fr["xy"].x, fr["xy"].y, z); root.rotation_euler = (0, 0, D(fr["hd"]))


def medir(st, f):
    arm, root = bpy.data.objects[ARM], bpy.data.objects[ROOT]
    fr = st["plan"]["frames"][f]; aplicar_pose(arm, root, fr)
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    o = bpy.data.objects["Mesh_3_jerry"].evaluated_get(dg); me = o.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    M = np.array(o.matrix_world); w = co @ M[:3, :3].T + M[:3, 3]; o.to_mesh_clear()
    mw = arm.matrix_world; pb = arm.pose.bones
    fr["minrel"] = float(w[:, 2].min())
    fr["hat"] = bpy.data.objects[HAT].matrix_world.copy()
    fr["jaw"] = mw @ pb["jaw_bot"].matrix
    fr["tip"] = mw @ pb["jaw_top"].tail
    fr["head"] = mw @ pb["scull"].head


def iniciar():
    st = {"estado": "plan", "error": None}
    bpy.app.driver_namespace["jerry_despierta"] = st
    try:
        arm, root = bpy.data.objects[ARM], bpy.data.objects[ROOT]
        st["plan"] = plan()
        st["prev"] = (arm.animation_data.action, root.animation_data.action)
        for a in st["prev"]: a.use_fake_user = True
        arm.animation_data.action = None; root.animation_data.action = None
        st["f"] = 1; st["estado"] = "suelo"
    except Exception as e:
        import traceback; st["error"] = traceback.format_exc(); st["estado"] = "error"; return st
    bpy.app.timers.register(_tick, first_interval=0.05)
    return st


def _restaurar(st):
    arm, root = bpy.data.objects[ARM], bpy.data.objects[ROOT]
    if "prev" in st:
        arm.animation_data.action, root.animation_data.action = st["prev"]


def _tick():
    st = bpy.app.driver_namespace["jerry_despierta"]
    try:
        F_END = st["plan"]["F_END"]
        if st["estado"] == "suelo":
            for _ in range(40):
                if st["f"] > F_END:
                    st["estado"] = "escribir"; break
                medir(st, st["f"]); st["f"] += 1
            return 0.01
        if st["estado"] == "escribir":
            escribir(st); st["estado"] = "listo"; return None
    except Exception:
        import traceback; st["error"] = traceback.format_exc(); st["estado"] = "error"; _restaurar(st)
    return None


# ---------------------------------------------------------------- escritura de claves
def claves(idblock, nombre, canales, constantes=()):
    idblock.animation_data_create()
    viejo = bpy.data.actions.get(nombre)
    if viejo: bpy.data.actions.remove(viejo)
    act = bpy.data.actions.new(nombre); idblock.animation_data.action = act
    for path, cl in canales.items():
        for i in range(len(cl[0][1])):
            fc = act.fcurve_ensure_for_datablock(idblock, path, index=i); fc.keyframe_points.add(len(cl))
            fc.keyframe_points.foreach_set("co", [x for f, v in cl for x in (f, v[i])])
            if path in constantes:
                for k in fc.keyframe_points: k.interpolation = 'CONSTANT'
            fc.update()
    return act


def suavizar_euler(lista):
    out, prev = [], None
    for f, e in lista:
        q = Euler(e).to_quaternion()
        e2 = q.to_euler('XYZ', prev) if prev is not None else Euler(e)
        out.append((f, tuple(e2))); prev = e2
    return out


def escribir(st):
    pl = st["plan"]; FR = pl["frames"]; F_END = pl["F_END"]
    arm, root = bpy.data.objects[ARM], bpy.data.objects[ROOT]
    # ---- altura del root
    z = {}
    for f in range(1, F_END + 1):
        fr = FR[f]; zc = fr["G"] - fr["minrel"]
        if f < F_UP[0]: z[f] = Z_BED                                       # altura dada por el usuario (cuelga del borde)
        elif f < F_UP[1]: z[f] = Z_BED + (zc - Z_BED) * ramp(f, F_UP[0], F_UP[1])
        else: z[f] = zc
    for n in range(7, 22):                                                 # arco del salto
        s = (n - 7) / 14.0; z[F_JUMP + n - 1] += 4 * 0.38 * s * (1 - s)
    # ---- armature
    bones = [pb.name for pb in arm.pose.bones]
    can = {}
    for b in bones:
        can['pose.bones["%s"].rotation_euler' % b] = suavizar_euler([(f, FR[f]["pose"].get(b, (0, 0, 0))) for f in range(1, F_END + 1)])
        can['pose.bones["%s"].scale' % b] = [(1, (1, 1, 1))]
        if b == "spine_6":
            can['pose.bones["%s"].location' % b] = [(f, FR[f]["pose"].get("L:spine_6", (0, 0, 0))) for f in range(1, F_END + 1)]
        else:
            can['pose.bones["%s"].location' % b] = [(1, (0, 0, 0))]
    claves(arm, "jerry_despierta", can)
    # ---- root
    hd = [(f, (0.0, 0.0, D(FR[f]["hd"]))) for f in range(1, F_END + 1)]
    claves(root, "jerry_despierta_root", {"location": [(f, (FR[f]["xy"].x, FR[f]["xy"].y, z[f])) for f in range(1, F_END + 1)],
                                          "rotation_euler": hd})
    dz = lambda f: Matrix.Translation((0, 0, z[f]))
    # ---- ojos (forma Closed en ojos y pupilas)
    for n in OJOS:
        o = bpy.data.objects[n]
        if not o.data.shape_keys: o.shape_key_add(name="Basis", from_mix=False)
        if "Closed" not in o.data.shape_keys.key_blocks:
            k = o.shape_key_add(name="Closed", from_mix=False); mz = min(v.co.z for v in o.data.vertices)
            for i, v in enumerate(o.data.vertices): k.data[i].co = (v.co.x, v.co.y, mz)
    SEQ = [0, .25, .5, .75, 1, 1, .75, .5, .25]
    cerr = []
    for f in range(1, F_END + 1):
        c = 1.0 if f < F_EYES[0] else 1 - ramp(f, F_EYES[0], F_EYES[1])
        for b0 in BLINKS:
            if b0 <= f < b0 + 9: c = max(c, SEQ[f - b0])
        cerr.append((f, (c,)))
    for n in OJOS:
        claves(bpy.data.objects[n].data.shape_keys, "jerry_despierta_ojos_" + n, {'key_blocks["Closed"].value': cerr})
    # ---- sombrero: puesto (hueso) / libre (mundo)
    hat = bpy.data.objects[HAT]
    lib = bpy.data.objects.get(LIBRE)
    if lib is None:
        lib = bpy.data.objects.new(LIBRE, hat.data)
        for c in hat.users_collection: c.objects.link(lib)
    lib.rotation_mode = 'QUATERNION'; lib.parent = None
    M0 = dz(F_HAT0) @ FR[F_HAT0]["hat"]
    loc0, q0, sc0 = M0.decompose()
    yaw_end = D(-35)
    q_up = Euler((0, 0, yaw_end)).to_quaternion()
    HZ = 9.0 + 0.104 * sc0.z / 0.91                                        # el ala apoya en el suelo
    tip = FR[F_PICK[2]]["tip"] + Vector((0, 0, z[F_PICK[2]]))
    fwd = Vector((-math.sin(D(H_TOP)), math.cos(D(H_TOP)), 0))
    H = Vector((tip.x + fwd.x * 0.10, tip.y + fwd.y * 0.10, HZ))
    st["H"] = tuple(H); st["tip_z"] = tip.z
    hit = Vector((HAT_HIT.x, HAT_HIT.y, HZ))
    M_H = Matrix.LocRotScale(H, q_up, sc0)
    mats = {}
    T = (F_HAT_HIT - F_HAT0) / 24.0; g = 9.8
    vz = ((hit.z - loc0.z) + 0.5 * g * T * T) / T
    for f in range(F_HAT0, F_HAT_HIT + 1):
        t = (f - F_HAT0) / 24.0; u = (f - F_HAT0) / (F_HAT_HIT - F_HAT0)
        p = loc0.lerp(hit, u); p.z = loc0.z + vz * t - 0.5 * g * t * t
        q = q0.slerp(Euler((0, 0, yaw_end + D(70))).to_quaternion(), ss(u)) @ Quaternion((1, 0, 0), 2 * math.pi * ss(u))
        mats[f] = Matrix.LocRotScale(p, q, sc0)
    for f in range(F_HAT_HIT + 1, F_PICK[2] + 1):
        u = ramp(f, F_HAT_HIT, F_HAT_REST); e = 1 - (1 - min(1, (f - F_HAT_HIT) / (F_HAT_REST - F_HAT_HIT))) ** 2
        p = hit.lerp(H, e); dec = max(0.0, 1 - (f - F_HAT_HIT) / 14.0)
        p.z = HZ + 0.07 * dec * abs(math.sin(math.pi * (f - F_HAT_HIT) / 5.0))
        yaw = yaw_end + D(70) * (1 - e)
        tilt = D(14) * dec * dec
        q = Euler((0, 0, yaw)).to_quaternion() @ Quaternion(Vector((math.cos(f * 0.9), math.sin(f * 0.9), 0)), tilt)
        mats[f] = Matrix.LocRotScale(p, q, sc0)
    J0 = dz(F_PICK[2]) @ FR[F_PICK[2]]["jaw"]; off = J0.inverted() @ mats[F_PICK[2]]
    for f in range(F_PICK[2] + 1, F_TOSS[2] + 1):
        mats[f] = dz(f) @ FR[f]["jaw"] @ off
    Mr = mats[F_TOSS[2]]; lr, qr, _ = Mr.decompose()
    Mh = dz(F_TOSS[3]) @ FR[F_TOSS[3]]["hat"]; lh, qh, sh = Mh.decompose()
    for f in range(F_TOSS[2] + 1, F_TOSS[3] + 1):
        u = (f - F_TOSS[2]) / (F_TOSS[3] - F_TOSS[2])
        p = lr.lerp(lh, u); p.z += 0.45 * 4 * u * (1 - u)
        q = qr.slerp(qh, ss(u)) @ Quaternion((0, 0, 1), 2 * math.pi * ss(u))
        mats[f] = Matrix.LocRotScale(p, q, sh)
    loc_k, rot_k, sc_k, qprev = [], [], [], None
    for f in sorted(mats):
        l, q, s = mats[f].decompose()
        if qprev is not None and q.dot(qprev) < 0: q = -q
        qprev = q; loc_k.append((f, tuple(l))); rot_k.append((f, tuple(q))); sc_k.append((f, tuple(s)))
    vis_lib = [(1, (1.0,)), (F_HAT0, (0.0,)), (F_TOSS[3] + 1, (1.0,))]
    vis_hat = [(1, (0.0,)), (F_HAT0, (1.0,)), (F_TOSS[3] + 1, (0.0,))]
    claves(lib, "jerry_despierta_sombrero_libre", {"location": loc_k, "rotation_quaternion": rot_k, "scale": sc_k,
                                                   "hide_viewport": vis_lib, "hide_render": vis_lib}, constantes=("hide_viewport", "hide_render"))
    claves(hat, "jerry_despierta_sombrero", {"hide_viewport": vis_hat, "hide_render": vis_hat}, constantes=("hide_viewport", "hide_render"))
    # ---- camara: sigue a Jerry desde que empieza a caminar
    if not CAMARA:
        st["resumen"] = dict(F_END=F_END, z_inicio=round(z[1], 3), H=[round(v, 3) for v in H]); bpy.context.scene.frame_set(bpy.context.scene.frame_current); return
    cam, foco = bpy.data.objects[CAM], bpy.data.objects[FOCO]
    c0, fo0 = cam.location.copy(), foco.location.copy()
    jpos = lambda f: Vector((FR[f]["xy"].x, FR[f]["xy"].y, z[f]))
    off = c0 - jpos(F_GO)
    ck, fk = [(F_GO - 1, tuple(c0))], [(F_GO - 1, tuple(fo0))]
    cp, fp = c0.copy(), fo0.copy()
    for f in range(F_GO, F_END + 1):
        tgt = jpos(f) + off + Vector((0, 0, CAM_SUBE * ramp(f, F_GO, F_GO + 30)))
        cp = cp.lerp(tgt, 0.12); ck.append((f, tuple(cp)))
        hfr = FR[f]["head"] + Vector((0, 0, z[f]))
        fwd = Vector((-math.sin(D(FR[f]["hd"])), math.cos(D(FR[f]["hd"])), 0))
        ft = (jpos(f) + hfr) * 0.5 + fwd * 0.6
        k = ramp(f, F_GO, F_GO + 30)
        fp = fp.lerp(fo0.lerp(ft, k), 0.15 if k < 1 else 0.2); fk.append((f, tuple(fp)))
    claves(cam, "camara_sigue_a_jerry", {"location": ck})
    claves(foco, "foco_sigue_a_jerry", {"location": fk})
    sc = bpy.context.scene
    st["resumen"] = dict(F_END=F_END, F_GO=F_GO, F_END_WALK=pl["F_END_WALK"], largo=round(pl["L"], 2),
                         z_inicio=round(z[1], 3), z_suelo=round(z[F_PICK[0]], 3), H=[round(v, 3) for v in H], tip_z=round(tip.z, 3),
                         cam_fin=[round(v, 2) for v in ck[-1][1]])
    sc.frame_set(sc.frame_current)
