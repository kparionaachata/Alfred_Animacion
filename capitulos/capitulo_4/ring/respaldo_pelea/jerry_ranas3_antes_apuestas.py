# -*- coding: utf-8 -*-
"""base_ranas_3: Jerry llega al cuadrilatero por Desktop/jerry_A.json (desde el frame 1), se levanta en dos patas
apoyando las delanteras en la valla (como los demas cuadrupedos del publico), mira la pelea sin entender y se
gira a preguntarle al cerdo de al lado (cerdo_ring) que esta pasando. Reemplaza la animacion anterior de Jerry
(dormir/sombrero) y quita sus tiras de sonido y voz viejas (SND_jerry_*, VozJerry_*).
Usa las utilidades de jerry_despierta.py (poses, ciclo de caminar del estudio, claves).
Uso (exec en Blender): iniciar()  -> pasada de suelo por timer -> escribe.  Estado: driver_namespace["jerry_ranas3"]
"""
import bpy, json, math
import numpy as np
from mathutils import Vector

DIR = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/"
RUTA = "C:/Users/user/Desktop/jerry_A.json"
ARM, ROOT = "Dog_001_rig", "jerry"
FPB = 12.43
J = {}
exec(compile(open(DIR + "jerry_despierta.py", encoding="utf8").read(), "jerry_despierta.py", "exec"), J)
P, add, mix, ss, ramp = J["P"], J["add"], J["mix"], J["ss"], J["ramp"]
D = math.radians

# ---------------------------------------------------------------- lugar en la valla
XY_VALLA = Vector((-36.25, -15.28))
ESPERA = Vector((-36.25, -15.70))           # en cuatro patas, el hocico queda a ~0.15 m de la valla
RECORTE = 0.3                                # la ruta termina un poco antes (el hocico atravesaba la barra)          # patas delanteras sobre la barra superior (y -14.5, z ~9.99)
CERDO = Vector((-37.45, -14.65, 10.3))
RING = Vector((-37.5, -12.0, 10.0))
GAN_YAW = 1.0                                # de pie, el giro horizontal de la cabeza es el eje Y local (medido ~1:1)
TH = 60.0                                    # inclinacion del cuerpo (spine_6 X)
UP = P({"spine_6": (TH, 0, 0), "shoulder.L": (-TH, 0, 0), "shoulder.R": (-TH, 0, 0),
        "thigh.L": (8, 0, 0), "thigh.R": (8, 0, 0), "shin.L": (-6, 0, 0), "shin.R": (-6, 0, 0),
        "front_shoulder.L": (0, 0, 15), "front_shoulder.R": (0, 0, -15),          # patas delanteras en V sobre la barra
        "front_thigh.L": (-10, 0, 0), "front_thigh.R": (-10, 0, 0), "front_shin.L": (10, 0, 0), "front_shin.R": (10, 0, 0),
        "spine_1": (24, 0, 0), "scull_1": (22, 0, 0), "tail_1": (-75, 0, 0), "tail_2": (-25, 0, 0), "tail_3": (-10, 0, 0)})

# ---------------------------------------------------------------- tiempos
F_TURN = (44, 56)            # llega y se pone de frente a la valla
F_UP = (58, 66)              # se levanta en dos patas
F_ASOMBRO = (80, 112)          # ladea la cabeza: no entiende
F_CERDO = (118, 130, 255, 268)   # gira la cabeza al cerdo, le pregunta, vuelve a la pelea
F_OTRA = (288, 300, 318, 330)    # vuelve a mirar al cerdo un momento
BLINKS = [40, 96, 138, 250, 306, 383]


def asombro_k(f):
    return ramp(f, F_ASOMBRO[0], F_ASOMBRO[0] + 5) * (1 - ramp(f, F_ASOMBRO[1] - 8, F_ASOMBRO[1]))


# cejas de sorpresa (delta pose - base de `animacion_jerry (10).py`, emocion sorpresa)
CEJAS = {"sejas_1_jerry": ((0.001155, -0.049993, -0.613817), (0.013347, -0.010338, -0.000448)),
         "sejas_2_jerry": ((-0.047893, 0.064076, 0.570414), (-0.003061, -0.009178, -0.00273))}


def cara_asombro():
    """cejas arriba, ojos mas abiertos y pupilas mas chicas mientras se asombra (F_ASOMBRO)"""
    arm = bpy.data.objects[ARM]; a = arm.animation_data.action
    fr = range(F_ASOMBRO[0] - 2, F_ASOMBRO[1] + 3)
    for b, (dr, dl) in CEJAS.items():
        for path, d in (('pose.bones["%s"].rotation_euler' % b, dr), ('pose.bones["%s"].location' % b, dl)):
            for i in range(3):
                fc = a.fcurve_ensure_for_datablock(arm, path, index=i)
                vals = [(f, fc.evaluate(f) + d[i] * asombro_k(f)) for f in fr]
                for f, v in vals: fc.keyframe_points.insert(f, v, options={'FAST'}).interpolation = 'LINEAR'
                fc.update()
    for n, sx, sz, dz in (("ojo_izquierdo_jerry", 0.16, 0.14, 0.0025), ("ojo_derecho_jerry", 0.16, 0.14, 0.0018),
                          ("pupila_izquierda_jerry", -0.2, -0.2, 0.0012), ("pupila_derecha_jerry", -0.2, -0.2, 0.0012)):
        o = bpy.data.objects[n]; s0, l0 = o.scale.copy(), o.location.copy()
        sc_k, lo_k = [], []
        for f in [1] + list(fr) + [bpy.context.scene.frame_end]:
            k = asombro_k(f)
            sc_k.append((f, (s0.x * (1 + sx * k), s0.y, s0.z * (1 + sz * k)))); lo_k.append((f, (l0.x, l0.y, l0.z + dz * k)))
        J["claves"](o, "jerry_ranas3_asombro_" + n, {"scale": sc_k, "location": lo_k})


def cabeza(yaw_deg, pitch_deg=0.0):
    """giro de cabeza (yaw + = a la izquierda) repartido en spine_1 y scull_1 (eje Y local con el cuerpo levantado)"""
    yaw_deg *= GAN_YAW
    return P({"spine_1": (pitch_deg * 0.5, 0.5 * yaw_deg, 0), "scull_1": (pitch_deg * 0.5, 0.5 * yaw_deg, 0),
              "ear.L": (-8, 0, 0), "ear.R": (-8, 0, 0)})


def ruta():
    kp = json.load(open(RUTA, encoding="utf8"))["key_points"]
    pts = [Vector((p["coordinates"]["x"], p["coordinates"]["y"])) for p in kp]
    for _ in range(3):
        q = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]): q += [a.lerp(b, 0.25), a.lerp(b, 0.75)]
        q.append(pts[-1]); pts = q
    acum = [0.0]
    for a, b in zip(pts[:-1], pts[1:]): acum.append(acum[-1] + (b - a).length)
    return pts, acum


def plan(F_END):
    walk_ns = J["_cargar"]("slot_004_jerry_caminar.py", "slot4")
    cyc = walk_ns["SniffingSearchCycle"](cycle_length=25, total_frames=9999)
    pts, acum = ruta(); Lr = acum[-1] - RECORTE
    pts = [J["en_ruta"](pts, acum, Lr * i / 40.0) for i in range(41)] + [ESPERA]     # la caminata termina en el punto de espera
    acum = [0.0]
    for a, b in zip(pts[:-1], pts[1:]): acum.append(acum[-1] + (b - a).length)
    L = acum[-1]; F_LLEGA = F_UP[0] - 6; nw = F_LLEGA - 1                          # llega caminando justo antes de levantarse
    vel = np.array([min(1.0, ss(i / 8.0) + 0.15, ss((nw - i) / 10.0) + 0.05) for i in range(nw + 1)])
    s_acc = np.concatenate([[0], np.cumsum(vel[1:])]); s_acc *= L / s_acc[-1]
    fin_ruta = J["en_ruta"](pts, acum, L)
    frames = {}; h = 90.0
    yaw_cerdo = None
    for f in range(1, F_END + 1):
        br = math.sin(2 * math.pi * f / 70.0)
        breath = P({"spine_4": (0.8 * br, 0, 0), "spine_5": (0.5 * br, 0, 0)})
        if f <= F_LLEGA:
            i = f - 1; s = float(s_acc[i]); xy = J["en_ruta"](pts, acum, s)
            tg = J["en_ruta"](pts, acum, s + 0.4) - J["en_ruta"](pts, acum, max(0.0, s - 0.05))
            tgt = math.degrees(math.atan2(-tg.x, tg.y)) if tg.length > 1e-4 else h
            tgt *= 1 - ramp(f, F_LLEGA - 22, F_LLEGA - 6)                       # al final gira de frente a la valla (en diagonal chocaba con el cerdo)
            h += max(-6.0, min(6.0, (((tgt - h + 180) % 360) - 180) * 0.3))
            wp = J["walk_pose"](cyc, f)
            pose = mix({}, wp, ramp(f, 1, 7))
        elif f < F_UP[0]:                                                         # frena: patas a la pose de pie, sin avanzar
            xy = ESPERA.copy()
            if f == F_LLEGA + 1: h0 = h
            h = h0 * (1 - ramp(f, F_LLEGA, F_UP[0] - 1))
            pose = mix(J["walk_pose"](cyc, F_LLEGA), {}, ramp(f, F_LLEGA, F_UP[0] - 1))
        else:
            xy = ESPERA.lerp(XY_VALLA, ramp(f, F_UP[0] + 3, F_UP[1] + 2)); h = 0.0             # primero sube las patas, luego avanza
            # direccion al cerdo y al ring desde la cabeza (aprox.)
            hpos = Vector((xy.x, xy.y + 0.15, 10.45))
            d = CERDO - hpos; yaw_c = math.degrees(math.atan2(-d.x, d.y))
            d2 = RING - hpos; yaw_r = math.degrees(math.atan2(-d2.x, d2.y))
            base = mix({}, UP, ramp(f, F_UP[0], F_UP[1]))
            mirar = cabeza(yaw_r, -6)
            k_c = ramp(f, F_CERDO[0], F_CERDO[1]) - ramp(f, F_CERDO[2], F_CERDO[3]) + ramp(f, F_OTRA[0], F_OTRA[1]) - ramp(f, F_OTRA[2], F_OTRA[3])
            look = mix(mirar, cabeza(yaw_c * 0.9, 4), k_c)
            pose = add(base, look, ramp(f, F_UP[0] + 6, F_UP[1] + 6))
            k_as = asombro_k(f)                                                  # se asombra: cabeza atras, orejas arriba
            pose = add(pose, P({"scull_1": (-9, 0, 0), "spine_1": (-4, 0, 0), "ear.L": (-14, 0, 0), "ear.R": (-14, 0, 0), "jaw_bot": (-10, 0, 0)}), k_as)
            # mientras pregunta: la cabeza acompana (leve asentir), orejas arriba
            if F_CERDO[1] <= f < F_CERDO[2]:
                pose = add(pose, P({"scull_1": (3 * math.sin(2 * math.pi * (f - F_CERDO[1]) / 18.0), 0, 0), "ear.L": (-10, 0, 0), "ear.R": (-10, 0, 0)}))
            wag = 16 * ramp(f, F_UP[1], F_UP[1] + 10) * math.sin(2 * math.pi * f / 11.0)
            pose = add(pose, P({"tail_2": (0, 0, wag), "tail_3": (0, 0, wag * 0.8)}))
            pose = add(pose, breath)
        frames[f] = dict(pose=pose, xy=Vector(xy), hd=h, G=9.0)
    return dict(frames=frames, F_END=F_END, F_LLEGA=F_LLEGA, L=L)


def iniciar():
    sc = bpy.context.scene
    st = {"estado": "plan", "error": None}
    bpy.app.driver_namespace["jerry_ranas3"] = st
    try:
        arm, root = bpy.data.objects[ARM], bpy.data.objects[ROOT]
        st["plan"] = plan(sc.frame_end)
        for o in (arm, root):
            if o.animation_data and o.animation_data.action: o.animation_data.action.use_fake_user = True
        arm.animation_data.action = None; root.animation_data.action = None
        st["f"] = 1; st["estado"] = "suelo"
    except Exception:
        import traceback; st["error"] = traceback.format_exc(); st["estado"] = "error"; return st
    bpy.app.timers.register(_tick, first_interval=0.05)
    return st


def _tick():
    st = bpy.app.driver_namespace["jerry_ranas3"]
    try:
        if st["estado"] == "suelo":
            for _ in range(40):
                if st["f"] > st["plan"]["F_END"]: st["estado"] = "escribir"; break
                J["medir"](st, st["f"]); st["f"] += 1
            return 0.01
        if st["estado"] == "escribir":
            escribir(st); st["estado"] = "listo"; return None
    except Exception:
        import traceback; st["error"] = traceback.format_exc(); st["estado"] = "error"
    return None


def escribir(st):
    sc = bpy.context.scene; pl = st["plan"]; FR = pl["frames"]; F_END = pl["F_END"]
    arm, root = bpy.data.objects[ARM], bpy.data.objects[ROOT]
    z = {f: FR[f]["G"] - FR[f]["minrel"] for f in range(1, F_END + 1)}
    can = {}
    for pb in arm.pose.bones:
        b = pb.name
        can['pose.bones["%s"].rotation_euler' % b] = J["suavizar_euler"]([(f, FR[f]["pose"].get(b, (0, 0, 0))) for f in range(1, F_END + 1)])
        can['pose.bones["%s"].scale' % b] = [(1, (1, 1, 1))]
        can['pose.bones["%s"].location' % b] = [(1, (0, 0, 0))]
    J["claves"](arm, "jerry_ranas3", can)
    J["claves"](root, "jerry_ranas3_root", {"location": [(f, (FR[f]["xy"].x, FR[f]["xy"].y, z[f])) for f in range(1, F_END + 1)],
                                            "rotation_euler": [(f, (0.0, 0.0, D(FR[f]["hd"]))) for f in range(1, F_END + 1)]})
    # ojos abiertos + parpadeos
    SEQ = [0, .25, .5, .75, 1, 1, .75, .5, .25]
    cerr = []
    for f in range(1, F_END + 1):
        c = 0.0
        for b0 in BLINKS:
            if b0 <= f < b0 + 9: c = SEQ[f - b0]
        cerr.append((f, (c,)))
    for n in J["OJOS"]:
        o = bpy.data.objects[n]
        J["claves"](o.data.shape_keys, "jerry_ranas3_ojos_" + n, {'key_blocks["Closed"].value': cerr})
        if o.animation_data and o.animation_data.action:                      # gestos de las voces viejas (escala/posicion de ojos)
            a = o.animation_data.action; o.animation_data.action = None
            if a.users == 0: bpy.data.actions.remove(a)
    # sombrero puesto, el suelto oculto
    hat, lib = bpy.data.objects[J["HAT"]], bpy.data.objects.get(J["LIBRE"])
    J["claves"](hat, "jerry_ranas3_sombrero", {"hide_viewport": [(1, (0.0,))], "hide_render": [(1, (0.0,))]}, constantes=("hide_viewport", "hide_render"))
    if lib: J["claves"](lib, "jerry_ranas3_sombrero_libre", {"hide_viewport": [(1, (1.0,))], "hide_render": [(1, (1.0,))]}, constantes=("hide_viewport", "hide_render"))
    # sonidos y voces viejas de Jerry
    ed = sc.sequence_editor; quit = [s for s in ed.strips_all if s.name.startswith(("SND_jerry_", "VozJerry_"))]
    nq = len(quit)
    for s in quit: ed.strips.remove(s)
    # filtros organicos viejos: su json ya no aplica a esta animacion
    import os
    dj = DIR + "organicos_jerry_delta.json"
    if os.path.exists(dj): os.remove(dj)
    cara_asombro()
    st["resumen"] = dict(F_LLEGA=pl["F_LLEGA"], largo=round(pl["L"], 2), z_pie=round(z[F_UP[1] + 10], 3), tiras_quitadas=nq)
    sc.frame_set(sc.frame_current)
