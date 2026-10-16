# -*- coding: utf-8 -*-
"""RING DE LUCHA (base_ranas_1.blend): los dos LUCHADORES se rodean alrededor de la antorcha, en guardia.
- Alfred y guard_ribbit_1 quedan en lados opuestos del circulo (radio RADIO alrededor de la antorcha) y giran juntos:
  casi siempre en un sentido, a veces se frenan y vuelven un poco (tanteo). Siempre se miran de frente.
- ALFRED: agachado (rodillas dobladas, torso un poco adelante), puños arriba delante de la cara, pasos laterales con
  los pies PLANTADOS en el suelo (IK de 2 tramos con planificador de pasos: un pie se queda quieto mientras el otro da el paso).
  De vez en cuando amaga un golpe (jab) con un brazo.
- GUARD_RIBBIT_1: como es una rana, se desplaza a SALTITOS (avanza en el aire, quieto en el suelo), cuerpo inclinado
  y brazos al frente; tambien amaga.
- No toca la camara ni las mallas de los ojos. Repetible: rehace sus acciones (alfred_rodea_ring, ...)."""
import bpy, math, random
from mathutils import Vector, Matrix, Quaternion

g = {"__name__": "ring_mod"}
exec(open("C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/espectadores_ring.py", encoding="utf-8").read(), g)
apuntar, rotar_mundo, ik2, HIJO_PATA = g["apuntar"], g["rotar_mundo"], g["ik2"], g["HIJO_PATA"]
sc = bpy.context.scene; vl = bpy.context.view_layer

C = Vector((-37.5, -12.0, 9.0))          # antorcha_ring
FIN = 745
RADIO = 1.25                              # radio del circulo (deja libres las herramientas tiradas en las esquinas)
OMEGA = 0.35                              # rad/s de giro tipico
UP = Vector((0, 0, 1))

HIJO_PATA.update({"RightUpLeg_alfred": "Rightknee_alfred", "LeftUpLeg_alfred": "Leftknee_alfred",
                  "RightUpArm_alfred": "Rightelbow_alfred", "LeftUpArm_alfred": "Leftelbow_alfred"})


def ss(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)


def ejes(yaw):
    f = Vector((-math.sin(yaw), math.cos(yaw), 0)); r = Vector((math.cos(yaw), math.sin(yaw), 0)); return f, r


# ------------------------------------------------------------------ recorrido del circulo
def angulos():
    """angulo de Alfred alrededor de la antorcha por frame (el guardian va en el lado opuesto)"""
    th = [0.0] * (FIN + 30); t = 0.0
    for f in range(2, FIN + 30):
        arranque = ss((f - 20) / 40.0)                                         # primero se acercan, luego empiezan a girar
        w = OMEGA * (0.5 + 0.7 * math.sin(2 * math.pi * f / 300 + 0.3)) * arranque
        t += w / 24.0; th[f] = t
    return th


def radio(f): return 2.0 + (RADIO - 2.0) * ss((f - 1) / 36.0) + 0.06 * math.sin(2 * math.pi * f / 170)


def punto(th, f): return C + Vector((math.cos(th), math.sin(th), 0)) * radio(f)


def yaw_hacia(a, b): d = b - a; return math.atan2(-d.x, d.y)


def desenrollar(ys):
    out = [ys[0]]
    for y in ys[1:]:
        while y - out[-1] > math.pi: y -= 2 * math.pi
        while y - out[-1] < -math.pi: y += 2 * math.pi
        out.append(y)
    return out


def amagos(seed, inicio):
    """frames donde empieza un jab y con que brazo"""
    rng = random.Random(seed); out = []; f = inicio
    while f < FIN - 20: out.append((f, rng.choice((0, 1)))); f += rng.randint(55, 95)
    return out


def jab(f, lista, brazo):
    """0..1: cuanto esta estirado ese brazo (sale rapido, vuelve mas lento)"""
    v = 0.0
    for f0, b in lista:
        if b != brazo: continue
        u = f - f0
        if 0 <= u < 4: v = max(v, ss(u / 4))
        elif 4 <= u < 12: v = max(v, 1 - ss((u - 4) / 8))
    return v


# ------------------------------------------------------------------ claves densas
def claves(obj, nombre, canales):
    """canales: {data_path: [(f, valores...)]}"""
    obj.animation_data_create()
    viejo = bpy.data.actions.get(nombre)
    if viejo: bpy.data.actions.remove(viejo)
    act = bpy.data.actions.new(nombre); obj.animation_data.action = act
    for path, cl in canales.items():
        for i in range(len(cl[0][1])):
            fc = act.fcurve_ensure_for_datablock(obj, path, index=i); fc.keyframe_points.add(len(cl))
            fc.keyframe_points.foreach_set("co", [c for f, v in cl for c in (f, v[i])])
            for k in fc.keyframe_points: k.interpolation = 'LINEAR'
            fc.update()
    return act


def limpiar(obj):
    if obj.animation_data and obj.animation_data.action: obj.animation_data.action = None


# ------------------------------------------------------------------ ALFRED
def suela(r):
    """z mas baja de la malla de Alfred (sin ojos)"""
    dg = bpy.context.evaluated_depsgraph_get(); z = 1e9
    for x in r.children:
        if x.type == 'MESH' and x.name.startswith("Mesh_"):
            e = x.evaluated_get(dg); M = x.matrix_world
            z = min(z, min((M @ v.co).z for v in e.data.vertices))
    return z


def alfred(th):
    r = bpy.data.objects["alfred"]; arm = bpy.data.objects["Armature"]; P = arm.pose.bones
    limpiar(r); limpiar(arm)
    huesos = ["Spine1_alfred", "face_alfred", "RightUpArm_alfred", "Rightelbow_alfred", "LeftUpArm_alfred", "Leftelbow_alfred",
              "RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred"]
    for h in huesos: P[h].rotation_mode = 'XYZ'; P[h].rotation_euler = (0, 0, 0)
    z0 = 9.018
    r.location = (-35.5, -12, z0); r.rotation_euler = (0, 0, math.pi / 2); vl.update()
    pie_z = {s: (arm.matrix_world @ P["%sknee_alfred" % s].tail).z - 9.0 for s in ("Right", "Left")}   # la punta del hueso vs el suelo
    # raiz por frame: mira al guardian (que va en el lado opuesto)
    pos = {}; ys = []
    for f in range(1, FIN + 1):
        p = punto(th[f], f); q = punto(th[f] + math.pi, f); pos[f] = p; ys.append(yaw_hacia(p, q))
    ys = desenrollar(ys); yaw = {f: ys[f - 1] for f in range(1, FIN + 1)}
    # planificador de pasos: cada pie quieto hasta que se aleja de donde deberia estar; entonces da un paso de DUR frames
    OFF = {"Right": (0.19, -0.09), "Left": (-0.19, 0.09)}       # (lateral, adelante): guardia con el pie izquierdo adelante
    DUR = 6; UMBRAL = 0.09; ALTO = 0.07

    def deseado(s, f):
        f = min(FIN, f); fw, rt = ejes(yaw[f]); return pos[f] + rt * OFF[s][0] + fw * OFF[s][1]

    plant = {s: deseado(s, 1) for s in OFF}; paso = {s: None for s in OFF}; pies = {s: {} for s in OFF}
    for f in range(1, FIN + 1):
        for s in OFF:
            if paso[s] and f >= paso[s][1]: plant[s] = paso[s][3]; paso[s] = None
        if not any(paso.values()):
            err = {s: (deseado(s, f + DUR) - plant[s]).length for s in OFF}
            s = max(err, key=err.get)
            if err[s] > UMBRAL: paso[s] = (f, f + DUR, plant[s].copy(), deseado(s, f + DUR))
        for s in OFF:
            if paso[s]:
                f0, f1, a, b = paso[s]; u = (f - f0) / (f1 - f0)
                p = a.lerp(b, ss(u)); p.z = 9.0 + pie_z[s] + ALTO * math.sin(math.pi * u)
            else:
                p = plant[s].copy(); p.z = 9.0 + pie_z[s]
            pies[s][f] = p
    am = amagos(5, 60)
    canal = {"location": [], "rotation_euler": []}; cb = {h: [] for h in huesos}; err_max = 0.0
    for f in range(1, FIN + 1):
        fw, rt = ejes(yaw[f])
        rebote = 0.012 * math.sin(2 * math.pi * f / 16)
        r.location = (pos[f].x, pos[f].y, z0 - 0.07 + rebote); r.rotation_euler = (0, 0, yaw[f])
        for h in ("Spine1_alfred", "face_alfred"): P[h].rotation_euler = (0, 0, 0)
        vl.update()
        rotar_mundo(arm, "Spine1_alfred", rt, -math.radians(10))            # torso un poco adelante
        rotar_mundo(arm, "face_alfred", rt, math.radians(8))                # la cara sigue mirando al rival
        # puños en guardia delante de la cara; jab = brazo casi estirado hacia el rival
        for s, brazo, lado, adel, arriba in (("Left", 0, -1, 0.62, 0.10), ("Right", 1, 1, 0.48, 0.16)):
            hom = arm.matrix_world @ P["%sUpArm_alfred" % s].head; j = jab(f, am, brazo)
            T = hom + fw * (adel + (0.98 - adel) * j) + UP * (arriba - 0.06 * j + 0.03 * math.sin(2 * math.pi * f / 16 + brazo))
            T += rt * (-lado) * (0.15 - 0.1 * j)
            ik2(arm, "%sUpArm_alfred" % s, "%selbow_alfred" % s, T, -UP + rt * lado * 0.7 - fw * 0.2)
        sube = 0.0
        for _it in range(3):                                                # la suela (no el hueso) queda justo sobre el pasto
            for s in ("Right", "Left"):
                lado = 1 if s == "Right" else -1
                T = pies[s][f] + UP * sube
                e = ik2(arm, "%sUpLeg_alfred" % s, "%sknee_alfred" % s, T, fw + rt * lado * 0.25)
            dz = 9.0 - suela(r)
            if abs(dz) < 0.002: break
            sube += dz
        err_max = max(err_max, abs(9.0 - suela(r)))
        canal["location"].append((f, tuple(r.location))); canal["rotation_euler"].append((f, tuple(r.rotation_euler)))
        for h in huesos: cb[h].append((f, tuple(P[h].rotation_euler)))
    claves(r, "alfred_rodea_ring", canal)
    claves(arm, "alfred_guardia_ring", {'pose.bones["%s"].rotation_euler' % h: v for h, v in cb.items()})
    return dict(suela_err_max=round(err_max, 4), amagos=len(am))


# ------------------------------------------------------------------ GUARD_RIBBIT_1 (a saltitos)
def guardian(th):
    r = bpy.data.objects["guard_ribbit_1"]; arm = bpy.data.objects["main_guard_ribbit_1"]; P = arm.pose.bones
    limpiar(r); limpiar(arm)
    huesos = ["body_guard_ribbit_1", "left_arm_guard_ribbit_1", "right_arm_guard_ribbit_1", "right_leg_guard_ribbit_1", "left_leg_guard_ribbit_1"]
    for h in huesos: P[h].rotation_mode = 'XYZ'; P[h].rotation_euler = (0, 0, 0)
    rng = random.Random(9)
    # saltos: en cada salto se queda quieto al principio y al final y avanza en el aire
    destino = {f: punto(th[f] + math.pi, f) for f in range(1, FIN + 12)}
    pos = {}; alto = {}; aire = {}
    f0 = 1
    while f0 <= FIN:
        n = rng.randint(9, 12); a = destino[f0]; b = destino[min(f0 + n, FIN + 11)]; d = (b - a).length
        h = 0.02 + 0.06 * min(1.0, d / 0.08)
        for f in range(f0, f0 + n):
            u = (f - f0 - 2) / (n - 4.0)
            pos[f] = a.lerp(b, ss(u)); alto[f] = h * math.sin(math.pi * min(1.0, max(0.0, u))); aire[f] = (0 < u < 1, (b - a))
        f0 += n
    am = amagos(11, 90)
    canal = {"location": [], "rotation_euler": []}; cb = {h: [] for h in huesos}; ys = []
    for f in range(1, FIN + 1): ys.append(yaw_hacia(pos[f], punto(th[f], f)))     # mira a Alfred donde esta
    ys = desenrollar(ys)
    for f in range(1, FIN + 1):
        yaw = ys[f - 1]; fw, rt = ejes(yaw)
        r.location = (pos[f].x, pos[f].y, 9.0 + alto[f]); r.rotation_euler = (0, 0, yaw)
        for h in huesos: P[h].rotation_euler = (0, 0, 0)
        vl.update()
        rotar_mundo(arm, "body_guard_ribbit_1", rt, -math.radians(12))
        for s, brazo, lado in (("left", 0, -1), ("right", 1, 1)):
            b = "%s_arm_guard_ribbit_1" % s; hom = arm.matrix_world @ P[b].head; j = jab(f, am, brazo)
            T = hom + fw * (0.22 + 0.12 * j) + UP * (0.03 + 0.04 * j + 0.02 * math.sin(2 * math.pi * f / 14 + brazo)) + rt * (-lado) * (0.05 - 0.03 * j)
            apuntar(arm, b, lambda b=b: arm.matrix_world @ P[b].tail, T)
        en_aire, mov = aire[f]
        if en_aire and mov.length > 1e-4 and alto[f] > 0.01:              # en el aire las patas se recogen hacia atras del salto
            m = mov.normalized(); eje = UP.cross(m)
            for s in ("right", "left"): rotar_mundo(arm, "%s_leg_guard_ribbit_1" % s, eje, math.radians(25) * alto[f] / 0.08)
        canal["location"].append((f, tuple(r.location))); canal["rotation_euler"].append((f, tuple(r.rotation_euler)))
        for h in huesos: cb[h].append((f, tuple(P[h].rotation_euler)))
    claves(r, "guard_ribbit_1_rodea_ring", canal)
    claves(arm, "guard_ribbit_1_guardia_ring", {'pose.bones["%s"].rotation_euler' % h: v for h, v in cb.items()})
    return dict(saltos=len([1 for f in range(2, FIN + 1) if alto[f] > 0.005 and alto[f - 1] <= 0.005]))


def construir():
    th = angulos(); out = {"vueltas": round(th[FIN] / (2 * math.pi), 2)}
    out["alfred"] = alfred(th); out["guardian"] = guardian(th)
    sc.frame_set(1)
    return out



# ------------------------------------------------------------------ ALFRED CON CLIPS (Mixamo): torso y brazos del clip, pies plantados
CLIPS_DIR = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/clips_alfred"
CLIPS = ["boxeo_mixamo.py"]                      # se encadenan en bucle; agregar mas archivos aqui
PIERNAS = ["RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred"]


def leer_clip(ruta):
    """KEYFRAME_DATA del archivo leido con ast (no se ejecuta: el archivo cambia de modo y pone claves por su cuenta)"""
    import ast
    arbol = ast.parse(open(ruta, encoding="utf-8").read())
    for n in arbol.body:
        if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "KEYFRAME_DATA" for t in n.targets):
            d = ast.literal_eval(n.value); fs = sorted(next(iter(d.values())).keys())
            return {"huesos": d, "frames": fs}
    raise ValueError("sin KEYFRAME_DATA: " + ruta)


def secuencia_clips():
    """frame de la escena -> (clip, frame del clip), clips encadenados en bucle (el ultimo frame = el primero, se salta)"""
    clips = [leer_clip(CLIPS_DIR + "/" + c) for c in CLIPS]; out = {}; i = 0; k = 0
    for f in range(1, FIN + 1):
        cl = clips[i]; fs = cl["frames"]; ciclo = fs[:-1] if len(fs) > 2 else fs
        out[f] = (cl, ciclo[k]); k += 1
        if k >= len(ciclo): k = 0; i = (i + 1) % len(clips)
    return clips, out


def poner_clip(P, clip, fc):
    for h, d in clip["huesos"].items():
        if h in P: P[h].rotation_mode = 'XYZ'; P[h].rotation_euler = d[fc]


def alfred_clip(th):
    r = bpy.data.objects["alfred"]; arm = bpy.data.objects["Armature"]; P = arm.pose.bones
    limpiar(r); limpiar(arm)
    clips, seq = secuencia_clips()
    huesos = sorted({h for c in clips for h in c["huesos"] if h in P} | set(PIERNAS))
    for b in P: b.rotation_mode = 'XYZ'; b.rotation_euler = (0, 0, 0)
    z0 = 9.018
    # 1) postura de cada frame de cada clip: cuanto baja la cadera (el clip dobla rodillas sin bajarla) y donde caen los pies
    r.location = (C.x + 2, C.y, z0); r.rotation_euler = (0, 0, math.pi / 2); vl.update()
    fw0, rt0 = ejes(math.pi / 2); base = Vector(r.location); baja = {}; pie_loc = {"Right": [], "Left": []}
    pie_z = {}
    for b in P: b.rotation_euler = (0, 0, 0)
    vl.update()
    for s in ("Right", "Left"): pie_z[s] = (arm.matrix_world @ P[s + "knee_alfred"].tail).z - suela(r)
    for ci, cl in enumerate(clips):
        for fc in cl["frames"]:
            poner_clip(P, cl, fc); vl.update(); baja[(ci, fc)] = suela(r) - 9.0
            for s in pie_loc:
                t = arm.matrix_world @ P[s + "knee_alfred"].tail - base; pie_loc[s].append((t.dot(rt0), t.dot(fw0)))
    OFF = {s: (sum(a for a, b in v) / len(v), sum(b for a, b in v) / len(v)) for s, v in pie_loc.items()}
    # 2) raiz: el mismo recorrido del circulo, mirando al guardian
    pos = {}; ys = []
    for f in range(1, FIN + 1):
        p = punto(th[f], f); q = punto(th[f] + math.pi, f); pos[f] = p; ys.append(yaw_hacia(p, q))
    ys = desenrollar(ys); yaw = {f: ys[f - 1] for f in range(1, FIN + 1)}
    # 3) pasos: pies plantados con la separacion promedio del clip
    DUR = 6; UMBRAL = 0.09; ALTO = 0.07

    def deseado(s, f):
        f = min(FIN, f); fw, rt = ejes(yaw[f]); return pos[f] + rt * OFF[s][0] + fw * OFF[s][1]

    plant = {s: deseado(s, 1) for s in OFF}; paso = {s: None for s in OFF}; pies = {s: {} for s in OFF}
    for f in range(1, FIN + 1):
        for s in OFF:
            if paso[s] and f >= paso[s][1]: plant[s] = paso[s][3]; paso[s] = None
        if not any(paso.values()):
            err = {s: (deseado(s, f + DUR) - plant[s]).length for s in OFF}
            s = max(err, key=err.get)
            if err[s] > UMBRAL: paso[s] = (f, f + DUR, plant[s].copy(), deseado(s, f + DUR))
        for s in OFF:
            if paso[s]:
                f0, f1, a, b = paso[s]; u = (f - f0) / (f1 - f0); p = a.lerp(b, ss(u)); lift = ALTO * math.sin(math.pi * u)
            else:
                p = plant[s].copy(); lift = 0.0
            p.z = 9.0 + pie_z[s] + lift; pies[s][f] = p
    # 4) cada frame: pose del clip + cadera bajada lo que el clip dobla + piernas por IK a los pies plantados (rodilla hacia donde la pone el clip)
    canal = {"location": [], "rotation_euler": []}; cb = {h: [] for h in huesos}; err_max = 0.0
    for f in range(1, FIN + 1):
        cl, fc = seq[f]; ci = clips.index(cl)
        fw, rt = ejes(yaw[f])
        r.location = (pos[f].x, pos[f].y, z0 - baja[(ci, fc)]); r.rotation_euler = (0, 0, yaw[f])
        poner_clip(P, cl, fc); vl.update()
        polo = {s: (arm.matrix_world @ P[s + "knee_alfred"].head) - (arm.matrix_world @ P[s + "UpLeg_alfred"].head) for s in OFF}
        sube = 0.0; previo = None                                           # secante: la suela sube menos que el pie (el pie se ladea)
        for _it in range(8):
            for s in ("Right", "Left"):
                ik2(arm, s + "UpLeg_alfred", s + "knee_alfred", pies[s][f] + UP * sube, polo[s])
            z = suela(r); dz = 9.0 - z
            if abs(dz) < 0.0015: break
            ganancia = 1.0
            if previo and abs(sube - previo[0]) > 1e-5: ganancia = min(1.5, max(0.25, (z - previo[1]) / (sube - previo[0])))
            previo = (sube, z); sube += dz / ganancia
        err_max = max(err_max, abs(9.0 - suela(r)))
        canal["location"].append((f, tuple(r.location))); canal["rotation_euler"].append((f, tuple(r.rotation_euler)))
        for h in huesos: cb[h].append((f, tuple(P[h].rotation_euler)))
    claves(r, "alfred_rodea_ring", canal)
    act = claves(arm, "alfred_guardia_ring", {'pose.bones["%s"].rotation_euler' % h: v for h, v in cb.items()})
    return dict(clips=CLIPS, suela_err_max=round(err_max, 4), separacion_pies={s: [round(x, 3) for x in v] for s, v in OFF.items()},
                bajada_cadera=[round(min(baja.values()), 3), round(max(baja.values()), 3)])


def construir_alfred_clips():
    th = angulos(); out = alfred_clip(th); sc.frame_set(1); return out
