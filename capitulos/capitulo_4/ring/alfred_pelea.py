# -*- coding: utf-8 -*-
"""RING DE LUCHA: la PELEA de Alfred dividida en FASES, con combos rapidos estilo anime (boxeo, patadas y MMA).
Fases (marcadores en la linea de tiempo):
  1 ESTUDIO            se rodean alrededor de la antorcha, guardia de boxeo (clip Mixamo), sin entrar
  2 PRIMER INTERCAMBIO  primeras entradas: jab-directo-patada baja, teep, doble jab-directo
  3 PRESION MMA         amago de derribo + superman punch, patada alta, rodillazo + directo
  4 CLIMAX              rafaga anime: jab, directo, gancho, uppercut, patada alta, patada giratoria; rodilla voladora
  5 REINICIO            se separan y vuelven a rodearse
Ritmo anime: anticipacion corta, golpe en 2-3 frames con salida explosiva, 2-3 frames congelados en el impacto, recuperacion.
Cada combo: Alfred entra en 4 frames (dash), encadena golpes y sale hacia atras. Base: el clip de boxeo + pasos plantados.
El guardian se acerca en las fases 2-4 (dejan de estar en lados opuestos, asi Alfred no atraviesa la antorcha) y mira
siempre a Alfred. Todo en espacio mundo con IK de 2 tramos. No toca camara ni ojos. Repetible."""
import bpy, math, random
from mathutils import Vector

L = {"__name__": "luch"}
exec(open("C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/luchadores_rodean.py", encoding="utf-8").read(), L)
ik2, apuntar, rotar_mundo = L["ik2"], L["apuntar"], L["rotar_mundo"]
ss, ejes, punto, yaw_hacia, desenrollar = L["ss"], L["ejes"], L["punto"], L["yaw_hacia"], L["desenrollar"]
claves, limpiar, suela, poner_clip, secuencia_clips = L["claves"], L["limpiar"], L["suela"], L["poner_clip"], L["secuencia_clips"]
FIN, UP = L["FIN"], L["UP"]
sc = bpy.context.scene; vl = bpy.context.view_layer

FASES = [("Fase 1: Estudio", 1), ("Fase 2: Primer intercambio", 160), ("Fase 3: Presion MMA", 330),
         ("Fase 4: Climax", 500), ("Fase 5: Reinicio", 650)]

# blanco en el guardian (alto 0.75 m): altura sobre su raiz; contacto a RADIO_RIVAL de su centro
BLANCO = {"cabeza": 0.60, "menton": 0.50, "cuerpo": 0.36, "piernas": 0.10}
RADIO_RIVAL = 0.22

# t = (anticipacion, golpe, impacto congelado, recuperacion) en frames
MOV = {
    "jab":              dict(m="LA", b="cabeza", t=(2, 2, 2, 3), giro=-15, dist=1.00, agacha=0.10),
    "directo":          dict(m="RA", b="cabeza", t=(3, 2, 3, 4), giro=40, dist=1.00, agacha=0.12),
    "gancho":           dict(m="LA", b="cabeza", t=(3, 3, 2, 4), giro=-45, dist=0.98, agacha=0.12, tipo="gancho"),
    "uppercut":         dict(m="RA", b="menton", t=(3, 2, 3, 4), giro=30, dist=0.93, agacha=0.20, tipo="uppercut"),
    "patada_baja":      dict(m="RL", b="piernas", t=(3, 3, 2, 5), giro=50, dist=0.95, tipo="circular"),
    "teep":             dict(m="LL", b="cuerpo", t=(4, 2, 3, 5), giro=0, dist=1.17, tipo="frontal"),
    "patada_alta":      dict(m="RL", b="cabeza", t=(4, 3, 3, 6), giro=70, dist=1.10, inclina=25, tipo="circular"),
    "rodillazo":        dict(m="RK", b="cuerpo", t=(3, 2, 3, 4), giro=20, dist=0.74),
    "superman":         dict(m="RA", b="cabeza", t=(6, 3, 2, 6), giro=45, dist=0.86, salto=0.35, aire=True),
    "finta_derribo":    dict(m=None, t=(3, 4, 3, 5), dist=1.25, agacha=0.38),
    "giratoria":        dict(m="RL", b="cuerpo", t=(6, 2, 3, 7), giro=0, dist=1.12, gira=True, tipo="atras"),
    "rodilla_voladora": dict(m="RK", b="cabeza", t=(6, 3, 3, 8), giro=15, dist=1.00, salto=0.50, aire=True),
}
COMBOS = [(175, ["jab", "directo", "patada_baja"]), (255, ["teep"]), (290, ["jab", "jab", "directo"]),
          (345, ["finta_derribo", "superman"]), (410, ["patada_alta"]), (455, ["rodillazo", "directo"]),
          (510, ["jab", "directo", "gancho", "uppercut", "patada_alta", "giratoria"]), (590, ["rodilla_voladora"])]
ENTRA = 4; SALE = 8
VARIANTE = L["VARIANTE"]
if VARIANTE == "ranas3":                     # base_ranas_3: en la fase 4 Alfred empieza a perder (el guardian esquiva sus golpes)
    FASES = FASES[:3] + [("Fase 4: Alfred pierde", 500), ("Fase 5: Derribo", 638)]
    COMBOS = COMBOS[:6] + [(500, ["jab", "directo", "gancho"]), (580, ["patada_alta"])]


def snap(u): u = min(1.0, max(0.0, u)); return 1 - (1 - u) ** 4          # salida explosiva (anime)


def total(n): return sum(MOV[n]["t"])


def programa():
    """golpes [(inicio, nombre)] y rangos [(e0, e1, x0, x1)] de cada combo"""
    golpes = []; rangos = []
    for f0, lista in COMBOS:
        t = f0 + ENTRA; ult = {}; fin = t
        for n in lista:
            A, S, H, R = MOV[n]["t"]; lim = MOV[n]["m"]
            st = max(t, ult.get(lim, 0)); golpes.append((st, n))
            ult[lim] = st + A + S + H + R; t = st + A + S + H; fin = max(fin, st + A + S + H + R)
        x0 = fin - MOV[lista[-1]]["t"][3] // 2
        rangos.append((f0, f0 + ENTRA, x0, x0 + SALE))
    return golpes, rangos


def envolvente(n, st, f):
    """(fase, u, w, g): w = peso del golpe sobre la pose base, g = avance del miembro de la carga al impacto"""
    A, S, H, R = MOV[n]["t"]; t = f - st
    if t < 0 or t >= A + S + H + R: return None
    if t < A: u = t / A; return ("A", u, ss(u), 0.0)
    if t < A + S: u = (t - A) / S; return ("S", u, 1.0, snap(u + 1.0 / S))
    if t < A + S + H: return ("H", (t - A - S) / H, 1.0, 1.0)
    u = (t - A - S - H) / R; return ("R", u, 1 - ss(u), 1 - 0.5 * ss(u))


def phi(f):
    """separacion angular de los dos en el circulo: opuestos al estudiar; 110 grados al pelear (la antorcha queda a un lado)"""
    sep = 10 ** 6 if VARIANTE == "ranas3" else 655                     # ranas3: no se separan (Alfred pierde y lo derriban)
    e = ss((f - 125) / 30.0) * (1 - ss((f - sep) / 30.0))
    return math.pi - (math.pi - math.radians(110)) * e


# ------------------------------------------------------------------ guardian: saltos por el circulo (antes que Alfred)
def saltos_guardian(th):
    rng = random.Random(9)
    destino = {f: punto(th[f] + phi(min(f, FIN)), f) for f in range(1, FIN + 12)}
    pos, alto, aire = {}, {}, {}; f0 = 1
    while f0 <= FIN:
        n = rng.randint(9, 12); a = destino[f0]; b = destino[min(f0 + n, FIN + 11)]; d = (b - a).length
        h = 0.02 + 0.06 * min(1.0, d / 0.08)
        for f in range(f0, f0 + n):
            u = (f - f0 - 2) / (n - 4.0)
            pos[f] = a.lerp(b, ss(u)); alto[f] = h * math.sin(math.pi * min(1.0, max(0.0, u))); aire[f] = (0 < u < 1, (b - a))
        f0 += n
    return pos, alto, aire


def pose_guardian(gpos, galto, gaire, apos):
    r = bpy.data.objects["guard_ribbit_1"]; arm = bpy.data.objects["main_guard_ribbit_1"]; P = arm.pose.bones
    limpiar(r); limpiar(arm)
    huesos = ["body_guard_ribbit_1", "left_arm_guard_ribbit_1", "right_arm_guard_ribbit_1", "right_leg_guard_ribbit_1", "left_leg_guard_ribbit_1"]
    for h in huesos: P[h].rotation_mode = 'XYZ'; P[h].rotation_euler = (0, 0, 0)
    am = L["amagos"](11, 90); jab = L["jab"]
    ys = desenrollar([yaw_hacia(gpos[f], apos[f]) for f in range(1, FIN + 1)])
    canal = {"location": [], "rotation_euler": []}; cb = {h: [] for h in huesos}
    for f in range(1, FIN + 1):
        yaw = ys[f - 1]; fw, rt = ejes(yaw)
        r.location = (gpos[f].x, gpos[f].y, 9.0 + galto[f]); r.rotation_euler = (0, 0, yaw)
        for h in huesos: P[h].rotation_euler = (0, 0, 0)
        vl.update()
        rotar_mundo(arm, "body_guard_ribbit_1", rt, -math.radians(12))
        for s, brazo, lado in (("left", 0, -1), ("right", 1, 1)):
            b = "%s_arm_guard_ribbit_1" % s; hom = arm.matrix_world @ P[b].head; j = jab(f, am, brazo)
            T = hom + fw * (0.22 + 0.12 * j) + UP * (0.03 + 0.04 * j + 0.02 * math.sin(2 * math.pi * f / 14 + brazo)) + rt * (-lado) * (0.05 - 0.03 * j)
            apuntar(arm, b, lambda b=b: arm.matrix_world @ P[b].tail, T)
        en_aire, mov = gaire[f]
        if en_aire and mov.length > 1e-4 and galto[f] > 0.01:
            m = mov.normalized(); eje = UP.cross(m)
            for s in ("right", "left"): rotar_mundo(arm, "%s_leg_guard_ribbit_1" % s, eje, math.radians(25) * galto[f] / 0.08)
        canal["location"].append((f, tuple(r.location))); canal["rotation_euler"].append((f, tuple(r.rotation_euler)))
        for h in huesos: cb[h].append((f, tuple(P[h].rotation_euler)))
    claves(r, "guard_ribbit_1_rodea_ring", canal)
    claves(arm, "guard_ribbit_1_guardia_ring", {'pose.bones["%s"].rotation_euler' % h: v for h, v in cb.items()})


# ------------------------------------------------------------------ ALFRED
def mezclar(pb, base, ik, w):
    pb.rotation_euler = base.to_quaternion().slerp(ik.to_quaternion(), w).to_euler('XYZ', ik)


def alfred_pelea(th, gpos, galto, defensa=None):
    """defensa (opcional, por frame): off (Vector, desplaza la raiz), agacha (m), glide (pies deslizan),
    bajo (peso del bloqueo bajo: antebrazos cruzados delante del vientre), esquiva (peso, lado +1/-1)"""
    D0 = {"off": Vector((0, 0, 0)), "agacha": 0.0, "glide": False, "bajo": 0.0, "esquiva": (0.0, 1), "impacto": 0.0, "flexion": 0.0}
    dfs = lambda f: (defensa or {}).get(f, D0)
    r = bpy.data.objects["alfred"]; arm = bpy.data.objects["Armature"]; P = arm.pose.bones; W = lambda: arm.matrix_world
    limpiar(r); limpiar(arm)
    clips, seq = secuencia_clips()
    huesos = sorted({h for c in clips for h in c["huesos"] if h in P} | {"RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred"})
    for b in P: b.rotation_mode = 'XYZ'; b.rotation_euler = (0, 0, 0)
    z0 = 9.018
    # postura del clip: bajada de cadera y separacion de los pies (como en alfred_clip)
    r.location = (L["C"].x + 2, L["C"].y, z0); r.rotation_euler = (0, 0, math.pi / 2); vl.update()
    fw0, rt0 = ejes(math.pi / 2); base = Vector(r.location); baja = {}; pie_loc = {"Right": [], "Left": []}; pie_z = {}
    for s in pie_loc: pie_z[s] = (W() @ P[s + "knee_alfred"].tail).z - suela(r)
    for ci, cl in enumerate(clips):
        for fc in cl["frames"]:
            poner_clip(P, cl, fc); vl.update(); baja[(ci, fc)] = suela(r) - 9.0
            for s in pie_loc:
                t = W() @ P[s + "knee_alfred"].tail - base; pie_loc[s].append((t.dot(rt0), t.dot(fw0)))
    OFF = {s: (sum(a for a, b in v) / len(v), sum(b for a, b in v) / len(v)) for s, v in pie_loc.items()}

    golpes, rangos = programa()
    activos = {f: [(st, n, envolvente(n, st, f)) for st, n in golpes if envolvente(n, st, f)] for f in range(1, FIN + 1)}

    def en_combo(f): return next(((e0, e1, x0, x1) for e0, e1, x0, x1 in rangos if e0 <= f <= x1), None)

    def c_de(f):
        g = en_combo(f)
        if not g: return 0.0
        e0, e1, x0, x1 = g
        if f <= e1: return snap((f - e0) / float(e1 - e0))
        if f < x0: return 1.0
        return 1 - ss((f - x0) / float(x1 - x0))

    # distancia de ataque (del golpe en curso), suavizada
    dr_raw = {}
    for f in range(1, FIN + 1):
        g = en_combo(f); d = 1.0
        if g:
            cand = [(st, n) for st, n in golpes if g[0] <= st <= g[3]]
            ya = [x for x in cand if x[0] <= f + 2]
            d = MOV[(ya[-1] if ya else cand[0])[1]]["dist"]
        dr_raw[f] = d
    dr = {f: sum(dr_raw[min(FIN, max(1, k))] for k in range(f - 2, f + 3)) / 5.0 for f in range(1, FIN + 1)}

    # raiz: circulo -> punto de ataque frente al guardian; mira al guardian (+ giro de la patada giratoria)
    pos = {}; yb = []; spin = {}; agacha = {}; salto = {}
    for f in range(1, FIN + 1):
        G = gpos[f]; pc = punto(th[f], f); d = G - pc; d.z = 0; d.normalize()
        emp = 0.0; sp = 0.0; ag = 0.0; sa = 0.0
        for st, n, (fa, u, w, g) in activos[f]:
            m = MOV[n]
            if fa == "S": emp = max(emp, 0.07)                                    # el peso del cuerpo va al golpe
            ag = max(ag, m.get("agacha", 0.0) * w)
            if m.get("salto"):
                A, S, H, R = m["t"]; tt = (f - st) / float(A + S + H + 2); sa = max(sa, m["salto"] * math.sin(math.pi * min(1.0, tt)))
            if m.get("gira"):
                sp = {"A": -math.pi * ss(u), "S": -math.pi, "H": -math.pi, "R": -math.pi - math.pi * ss(u)}[fa]
        pa = G - d * (dr[f] - emp); p = pc.lerp(pa, c_de(f)) + dfs(f)["off"]; p.z = 0
        pos[f] = p; spin[f] = sp; agacha[f] = max(ag, dfs(f)["agacha"]) + 0.05 * dfs(f).get("impacto", 0.0) + 0.08 * dfs(f).get("flexion", 0.0); salto[f] = sa
        yb.append(yaw_hacia(p, G))
    yb = desenrollar(yb); yaw = desenrollar([yb[f - 1] + spin[f] for f in range(1, FIN + 1)])
    yaw = {f: yaw[f - 1] for f in range(1, FIN + 1)}

    # pies: fuera de los combos pasos plantados; dentro, se deslizan con la guardia (dash anime)
    DUR = 6; UMBRAL = 0.09; ALTO = 0.07

    def deseado(s, f):
        f = min(FIN, f); fw, rt = ejes(yaw[f]); q = pos[f] + rt * OFF[s][0] + fw * OFF[s][1]; q.z = 0; return q

    plant = {s: deseado(s, 1) for s in OFF}; paso = {s: None for s in OFF}; pies = {s: {} for s in OFF}
    for f in range(1, FIN + 1):
        if en_combo(f) or dfs(f)["glide"]:
            for s in OFF:
                q = deseado(s, f); q.z = 9.0 + pie_z[s]; pies[s][f] = q; plant[s] = deseado(s, f); paso[s] = None
            continue
        for s in OFF:
            if paso[s] and f >= paso[s][1]: plant[s] = paso[s][3]; paso[s] = None
        if not any(paso.values()):
            err = {s: (deseado(s, f + DUR) - plant[s]).length for s in OFF}; s = max(err, key=err.get)
            if err[s] > UMBRAL: paso[s] = (f, f + DUR, plant[s].copy(), deseado(s, f + DUR))
        for s in OFF:
            if paso[s]:
                f0, f1, a, b = paso[s]; u = (f - f0) / (f1 - f0); p = a.lerp(b, ss(u)); lift = ALTO * math.sin(math.pi * u)
            else: p = plant[s].copy(); lift = 0.0
            p.z = 9.0 + pie_z[s] + lift; pies[s][f] = p

    LADO = {"Right": 1, "Left": -1}; MIEMBRO = {"LA": ("Left", "Arm"), "RA": ("Right", "Arm"), "LL": ("Left", "Leg"), "RL": ("Right", "Leg"), "RK": ("Right", "Knee")}
    canal = {"location": [], "rotation_euler": []}; cb = {h: [] for h in huesos}; prev = {}
    informe = {}; err_suela = 0.0
    for f in range(1, FIN + 1):
        cl, fc = seq[f]; ci = clips.index(cl); G = gpos[f]
        r.location = (pos[f].x, pos[f].y, z0 - baja[(ci, fc)] - agacha[f] + salto[f]); r.rotation_euler = (0, 0, yaw[f])
        poner_clip(P, cl, fc); vl.update()
        fw, rt = ejes(yaw[f]); dG = G - Vector(r.location); dG.z = 0; dG.normalize(); rtG = dG.cross(UP)
        # torso
        for st, n, (fa, u, w, g) in activos[f]:
            m = MOV[n]
            if m.get("giro"): rotar_mundo(arm, "Spine1_alfred", UP, math.radians(m["giro"]) * w)
            if m.get("inclina"): rotar_mundo(arm, "Spine1_alfred", dG, -math.radians(m["inclina"]) * w)     # se echa al lado contrario de la pierna (derecha)
            if n == "finta_derribo": rotar_mundo(arm, "Spine1_alfred", rtG, -math.radians(28) * w)    # baja el nivel: torso adelante
        we, lado_e = dfs(f)["esquiva"]
        if we > 0.01:                                                          # esquiva: el torso se va hacia el lado y atras
            rotar_mundo(arm, "Spine1_alfred", dG, lado_e * math.radians(22) * we)      # (+ sobre dG = hacia rtG)
            rotar_mundo(arm, "Spine1_alfred", rtG, math.radians(12) * we)            # (+ sobre rtG = hacia atras)
        imp = dfs(f).get("impacto", 0.0); flex = dfs(f).get("flexion", 0.0)
        if imp > 0.01:                                                         # golpe atajado: el torso y la cabeza ceden hacia atras
            rotar_mundo(arm, "Spine1_alfred", rtG, math.radians(10) * imp)
            rotar_mundo(arm, "Neck_alfred", rtG, math.radians(12) * imp)
        if flex > 0.01:                                                        # golpe al vientre: se dobla, la cabeza sigue atras
            rotar_mundo(arm, "Spine_alfred", rtG, -math.radians(12) * flex)
            rotar_mundo(arm, "Spine1_alfred", rtG, -math.radians(28) * flex)
            rotar_mundo(arm, "Neck_alfred", rtG, math.radians(10) * flex)
        vl.update()
        wb = dfs(f)["bajo"]
        if wb > 0.01:                                                          # bloqueo bajo: antebrazos cruzados delante del vientre
            for s in ("Left", "Right"):
                lado = 1 if s == "Right" else -1
                T = Vector((r.location.x, r.location.y, 9.0)) + UP * (0.62 - 0.04 * flex) + dG * (0.55 - 0.10 * imp - 0.15 * flex) + rtG * (-lado) * 0.06
                b0 = (P[s + "UpArm_alfred"].rotation_euler.copy(), P[s + "elbow_alfred"].rotation_euler.copy())
                ik2(arm, s + "UpArm_alfred", s + "elbow_alfred", T, -UP + rtG * lado * 0.9)
                mezclar(P[s + "UpArm_alfred"], b0[0], P[s + "UpArm_alfred"].rotation_euler.copy(), wb)
                mezclar(P[s + "elbow_alfred"], b0[1], P[s + "elbow_alfred"].rotation_euler.copy(), wb); vl.update()
        polos = {s: (W() @ P[s + "knee_alfred"].head) - (W() @ P[s + "UpLeg_alfred"].head) for s in OFF}
        # piernas de apoyo primero (pies plantados o deslizando)
        for s in OFF: ik2(arm, s + "UpLeg_alfred", s + "knee_alfred", pies[s][f], polos[s])
        ocupadas = {}; en_aire = False
        for st, n, (fa, u, w, g) in activos[f]:
            m = MOV[n]; lim = m["m"]; en_aire = en_aire or bool(m.get("aire") and salto[f] > 0.02)
            blanco = Vector((G.x, G.y, 9.0 + galto[f] + BLANCO.get(m.get("b"), 0.36))) - dG * RADIO_RIVAL
            if lim is None:                                                    # amago de derribo: brazos adelante y abajo
                for s in ("Left", "Right"):
                    sh = W() @ P[s + "UpArm_alfred"].head; T = sh + dG * 0.55 - UP * 0.35 + rtG * (-LADO[s]) * 0.08
                    b0 = (P[s + "UpArm_alfred"].rotation_euler.copy(), P[s + "elbow_alfred"].rotation_euler.copy())
                    ik2(arm, s + "UpArm_alfred", s + "elbow_alfred", T, -UP + rtG * LADO[s])
                    mezclar(P[s + "UpArm_alfred"], b0[0], P[s + "UpArm_alfred"].rotation_euler.copy(), w)
                    mezclar(P[s + "elbow_alfred"], b0[1], P[s + "elbow_alfred"].rotation_euler.copy(), w); vl.update()
                continue
            s, parte = MIEMBRO[lim]; lado = LADO[s]
            if parte == "Arm":
                sh = W() @ P[s + "UpArm_alfred"].head; tipo = m.get("tipo")
                if tipo == "gancho":
                    carga = sh + rtG * lado * 0.45 + dG * 0.15; polo = rtG * lado + UP * 0.4
                elif tipo == "uppercut":
                    carga = sh - UP * 0.5 + dG * 0.2; blanco = blanco - dG * 0.05; polo = -UP + dG * 0.4
                else:
                    carga = sh + dG * 0.22 + UP * 0.05; polo = -UP + rtG * lado * 0.6
                T = carga.lerp(blanco, g)
                if tipo == "gancho": T += rtG * lado * 0.25 * math.sin(math.pi * g)
                b0 = (P[s + "UpArm_alfred"].rotation_euler.copy(), P[s + "elbow_alfred"].rotation_euler.copy())
                e = ik2(arm, s + "UpArm_alfred", s + "elbow_alfred", T, polo)
                if fa == "H": informe[n] = max(informe.get(n, 0.0), round(e, 3))
                mezclar(P[s + "UpArm_alfred"], b0[0], P[s + "UpArm_alfred"].rotation_euler.copy(), w)
                mezclar(P[s + "elbow_alfred"], b0[1], P[s + "elbow_alfred"].rotation_euler.copy(), w); vl.update()
            else:
                hip = W() @ P[s + "UpLeg_alfred"].head; ocupadas[s] = max(ocupadas.get(s, 0.0), w)
                b0 = (P[s + "UpLeg_alfred"].rotation_euler.copy(), P[s + "knee_alfred"].rotation_euler.copy())
                if parte == "Knee":                                            # rodillazo: muslo al blanco, pierna recogida atras
                    carga = hip + dG * 0.15 - UP * 0.25
                    K = carga.lerp(blanco, g)
                    apuntar(arm, s + "UpLeg_alfred", lambda s=s: W() @ P[s + "knee_alfred"].head, K)
                    k = W() @ P[s + "knee_alfred"].head
                    apuntar(arm, s + "knee_alfred", lambda s=s: W() @ P[s + "knee_alfred"].tail, k - UP * 0.5 - dG * 0.35)
                    if fa == "H": informe[n] = round(((W() @ P[s + "knee_alfred"].head) - hip).normalized().dot((blanco - hip).normalized()), 3)
                else:
                    tipo = m.get("tipo")
                    if tipo == "circular":
                        carga = hip + rtG * lado * 0.35 + UP * 0.1 + dG * 0.1; polo = UP * 0.6 + rtG * lado
                        T = carga.lerp(blanco, g) + rtG * lado * 0.3 * math.sin(math.pi * g)
                    elif tipo == "atras":
                        carga = hip + dG * 0.1 - UP * 0.3; polo = UP; T = carga.lerp(blanco, g)
                    else:
                        carga = hip + dG * 0.3 - UP * 0.35; polo = UP + dG * 0.3; T = carga.lerp(blanco, g)
                    e = ik2(arm, s + "UpLeg_alfred", s + "knee_alfred", T, polo)
                    if fa == "H": informe[n] = max(informe.get(n, 0.0), round(e, 3))
                mezclar(P[s + "UpLeg_alfred"], b0[0], P[s + "UpLeg_alfred"].rotation_euler.copy(), w)
                mezclar(P[s + "knee_alfred"], b0[1], P[s + "knee_alfred"].rotation_euler.copy(), w); vl.update()
            # en los saltos la otra pierna va recogida (superman: la de atras estirada)
            if m.get("aire"):
                otra = "Left" if s == "Right" else "Right"
                if n == "superman": otra, T2, pol2 = "Right", (W() @ P["RightUpLeg_alfred"].head) - dG * 0.6 - UP * 0.6, UP
                else: T2, pol2 = (W() @ P[otra + "UpLeg_alfred"].head) - UP * 0.5 - dG * 0.4, dG
                b0 = (P[otra + "UpLeg_alfred"].rotation_euler.copy(), P[otra + "knee_alfred"].rotation_euler.copy())
                ik2(arm, otra + "UpLeg_alfred", otra + "knee_alfred", T2, pol2)
                ws = min(1.0, salto[f] / 0.08)
                mezclar(P[otra + "UpLeg_alfred"], b0[0], P[otra + "UpLeg_alfred"].rotation_euler.copy(), ws)
                mezclar(P[otra + "knee_alfred"], b0[1], P[otra + "knee_alfred"].rotation_euler.copy(), ws); vl.update()
                ocupadas[otra] = max(ocupadas.get(otra, 0.0), ws)
        # suelo: las piernas de apoyo pisan justo el pasto; en el aire nada atraviesa el suelo
        apoyo = [s for s in OFF if ocupadas.get(s, 0.0) < 0.05]
        if apoyo and not en_aire:
            sube = 0.0; previo = None
            for _it in range(8):
                z = suela(r); dz = 9.0 - z
                if abs(dz) < 0.0015: break
                gan = 1.0
                if previo and abs(sube - previo[0]) > 1e-5: gan = min(1.5, max(0.25, (z - previo[1]) / (sube - previo[0])))
                previo = (sube, z); sube += dz / gan
                for s in apoyo: ik2(arm, s + "UpLeg_alfred", s + "knee_alfred", pies[s][f] + UP * sube, polos[s])
        # la pierna que vuelve de un golpe (o va en el aire) tampoco atraviesa el pasto: se levanta lo que falte
        for _it in range(4):
            z = suela(r)
            if z > 9.0 - 0.0015: break
            for s, w_ in ocupadas.items():
                if w_ < 0.05: continue
                hip = W() @ P[s + "UpLeg_alfred"].head; kn = W() @ P[s + "knee_alfred"].head
                ik2(arm, s + "UpLeg_alfred", s + "knee_alfred", (W() @ P[s + "knee_alfred"].tail) + UP * (9.0 - z + 0.003), kn - hip)
        z = suela(r)
        if z < 9.0 - 0.0015: r.location.z += 9.0 - z; vl.update()
        err_suela = max(err_suela, max(0.0, 9.0 - suela(r)))
        canal["location"].append((f, tuple(r.location))); canal["rotation_euler"].append((f, tuple(r.rotation_euler)))
        for h in huesos:
            e = P[h].rotation_euler.to_quaternion().to_euler('XYZ', prev[h]) if h in prev else P[h].rotation_euler.copy()
            prev[h] = e; cb[h].append((f, tuple(e)))
    claves(r, "alfred_rodea_ring", canal)
    claves(arm, "alfred_guardia_ring", {'pose.bones["%s"].rotation_euler' % h: v for h, v in cb.items()})
    apos = {f: Vector(c[1]) for f, c in zip(range(1, FIN + 1), canal["location"])}
    return dict(golpes=len(golpes), combos=len(rangos), hundido_max=round(err_suela, 4), error_impacto=informe), apos


def marcadores():
    tm = sc.timeline_markers
    for m in [m for m in tm if m.name.startswith("Fase ")]: tm.remove(m)
    for n, f in FASES: tm.new(n, frame=f)


def construir():
    th = L["angulos"](); gpos, galto, gaire = saltos_guardian(th)
    out, apos = alfred_pelea(th, gpos, galto)
    pose_guardian(gpos, galto, gaire, apos)
    marcadores(); sc.frame_set(1)
    return out
