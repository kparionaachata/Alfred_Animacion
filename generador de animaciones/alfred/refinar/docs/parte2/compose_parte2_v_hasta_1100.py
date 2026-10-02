"""PARTE 2 (Alfred y Jerry), v2 segun la descripcion del usuario. Solo Python estandar, sin Blender.

Historia: siguen nadando al este hasta Alfred (-84.5,-120.32) / Jerry (-82.5,-119.44). Jerry es el primero en ver que no hay tierra en esa
direccion; giran a discutirlo y se quedan mucho tiempo alli; los zombies se acercan; ambos miran atras, ven a los zombies cerca y nadan
frenéticamente hacia la costa (norte, y=-104.5), suben la escalera oriental (x -83.5 -> -89.5, z 8..14) y siguen por la meseta.

Uso (desde 'generador de animaciones'):   python alfred/refinar/docs/parte2/compose_parte2.py [alfred|jerry|todos]
Entradas: nado de la parte 1 (ciclos exactos: 24 f Alfred, 16 f Jerry), `parado*.json` (pose de pie) y el tramo de tierra
(`parte2_*_tramo_tierra`, motor base del add-on). Salida: <pers>/refinar/animaciones_ia/parte2_<pers>_nada_y_sube/.
"""
import copy, json, math, os, sys

BASE = "generador de animaciones" if os.path.isdir("generador de animaciones") else "."
N = 1100
D2R = math.pi / 180.0


def ss(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def pulse(k, a, b, fa=8.0, fb=8.0):
    return ss((k - a) / fa) * (1 - ss((k - b) / fb))


def ela(t):
    """Elastic In-Out (misma curva que `interpolation.py` del add-on, ELASTIC_IN_OUT): transiciones EXPRESIVAS (sustos, risas, golpes)."""
    if t <= 0: return 0.0
    if t >= 1: return 1.0
    c5 = (2 * math.pi) / 4.5
    if t < 0.5: return -(2 ** (20 * t - 10) * math.sin((20 * t - 11.125) * c5)) / 2
    return (2 ** (-20 * t + 10) * math.sin((20 * t - 11.125) * c5)) / 2 + 1


def epulse(k, a, b, fa=14.0, fb=14.0):
    return ela((k - a) / fa) * (1 - ela((k - b) / fb))


def ld(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def val(ch, i):
    return ch[i] if isinstance(ch, list) else ch


def mix(a, b, w):
    return [x + (y - x) * w for x, y in zip(a, b)]


def mixrow(A, B, w):
    if w <= 0: return A
    if w >= 1: return B
    return {b: {p: mix(A[b][p], B[b][p], w) for p in A[b]} for b in A}


def norm(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class Art:
    def __init__(self, path):
        self.d = ld(path); self.f0 = self.d["frame_inicio"]; self.f1 = self.d["frame_fin"]; self.bones = list(self.d["armature"]["bones"])

    def idx(self, f):
        return max(0, min(self.f1 - self.f0, int(round(f)) - self.f0))

    def bone(self, name, prop, f):
        return [val(a, self.idx(f)) for a in self.d["armature"]["bones"][name][prop]]

    def root(self, prop, f):
        return [val(a, self.idx(f)) for a in self.d["root"]["canales"][prop]]

    def row(self, f):
        f0 = math.floor(f); w = f - f0
        return {b: {p: (mix(self.bone(b, p, f0), self.bone(b, p, f0 + 1), w) if w > 1e-9 else self.bone(b, p, f0)) for p in ("rotation_euler", "location", "scale")} for b in self.bones}


def stand_pose(path, bones, fallback):
    ps = ld(path)["poses"][0]["bones"]; out = {}
    for b in bones:
        if b not in ps:
            out[b] = copy.deepcopy(fallback[b]); continue
        ls = ps[b]["local_space"]
        out[b] = {"rotation_euler": [ls["rotation_euler_rad"][a] for a in "xyz"], "location": [ls["location"][a] for a in "xyz"], "scale": [ls["scale"][a] for a in "xyz"]}
    return out


CFG = {
    "alfred": {
        "swim": "alfred/refinar/animaciones_ia/alfred_nada_hacia_piedras/alfred_nada_hacia_piedras.animacion.json", "period": 24,
        "tramo": "alfred/refinar/animaciones_ia/parte2_alfred_tramo_tierra/parte2_alfred_tramo_tierra.animacion.json",
        "stand": "alfred/refinar/poses/parado_neutral.json", "carpeta": "alfred/refinar/animaciones_ia", "nombre": "parte2_alfred_nada_y_sube",
        "speed": 0.058, "stop": (-84.5, -120.32), "decel": 30, "stand_z": 7.0,
        "stand_a": 305, "stand_d": 40, "k_back": 482, "k_north": 518, "k_swim": 540, "fast_rate": 1.7, "fast_speed": 0.105, "fast_ramp": 18,
    },
    "jerry": {
        "swim": "jerry/refinar/animaciones_ia/jerry_nada_hacia_piedras/jerry_nada_hacia_piedras.animacion.json", "period": 16,
        "tramo": "jerry/refinar/animaciones_ia/parte2_jerry_tramo_tierra/parte2_jerry_tramo_tierra.animacion.json",
        "stand": "jerry/refinar/poses/parado.json", "carpeta": "jerry/refinar/animaciones_ia", "nombre": "parte2_jerry_nada_y_sube",
        "speed": 0.062, "stop": (-82.5, -119.44), "decel": 25,
        "stand_a": 240, "stand_d": 35, "k_back": 482, "k_north": 518, "k_swim": 540, "fast_rate": 1.5, "fast_speed": 0.13, "fast_ramp": 15,
    },
}
# postura de descanso de Alfred (grados); ajustable por la variable de entorno REST_P (JSON) para calibrar midiendo en Blender
REST_P = {"hips": 26, "spine": 14, "spine1": 11, "spine2": 11, "neck": 22, "leg": 26, "knee": -4, "arm_x": 105, "arm_y": 45, "root_dz": 0.09}   # calibrado midiendo en Blender (torso ~56 grados, manos a ~0.25 m de la rodilla, pies a ~0.14 m del root y en el suelo)
REST_P.update(json.loads(os.environ.get("REST_P", "{}")))
V_LEFT_EXTRA = 30          # el brazo izquierdo del rig cuelga mas bajo (hombro asimetrico): 30 grados mas de abduccion para que la V quede simetrica en apertura
P0 = (-82.5, -104.5, 7.0)
REST = {"alfred": (-93.5, -108.5), "jerry": (-95.0, -107.6)}       # donde suben y paran (Alfred: coordenada dada por el usuario; Jerry a ~1.7 m de el)
SLIP_INFO = {}                                   # lo rellena build('alfred'): kS, t1, t2, starts de cada vuelta
SLIP = os.environ.get("SLIP", "1") == "1"        # Alfred resbala a la altura Z=13 de la escalera, rueda por los escalones y flota boca abajo (sustituye al descanso)
STAIR_FOOT = (-82.5, -104.5)
FACE = {"alfred": math.atan2(-(REST["jerry"][0] - REST["alfred"][0]), (REST["jerry"][1] - REST["alfred"][1])),   # Alfred mira a Jerry
        "jerry": (math.atan2(-(STAIR_FOOT[0] - REST["jerry"][0]), (STAIR_FOOT[1] - REST["jerry"][1])) if SLIP else math.atan2(-(REST["alfred"][0] - REST["jerry"][0]), (REST["alfred"][1] - REST["jerry"][1])))}    # Jerry mira a Alfred (o hacia la escalera/agua si Alfred cae)

ALF_STOP = (-84.5, -120.32)
RZ_NORTH = 0.0                                                             # rumbo norte (la escalera esta al norte, por el agua de x=-82.5)
WAY = {"alfred": [(-82.5, -117.5)], "jerry": []}                            # Alfred sale en diagonal al carril x=-82.5 (la orilla en x=-84 es tierra)


def build(name):
    c = CFG[name]
    SW = Art(os.path.join(BASE, c["swim"])); TR = Art(os.path.join(BASE, c["tramo"])); bones = SW.bones
    per = c["period"]; t_last = SW.f1; t0c = t_last - per + 1
    cyc = [SW.row(t0c + i) for i in range(per)]
    ph0 = per - 1                                                        # k=1 == ultimo frame de la parte 1

    def cyc_row(phase):
        p = phase % per; i = int(math.floor(p)); w = p - i
        return mixrow(cyc[i], cyc[(i + 1) % per], w)

    def swim_row(k, rate=1.0, base_k=1, ph_base=None):
        return cyc_row((ph0 if ph_base is None else ph_base) + rate * (k - base_k))

    x0, y0, z0 = SW.root("location", t_last); rz0 = norm(SW.root("rotation_euler", t_last)[2])
    v = c["speed"]; Dm = c["decel"]; sx, sy = c["stop"]
    d_const = (sx - x0) - v * Dm / 2.0; k_c = 1 + d_const / v; k_stop = k_c + Dm

    def swim_x(k):
        if k <= k_c: return x0 + v * (k - 1)
        u = min(k - k_c, Dm); return x0 + d_const + v * u - v * u * u / (2.0 * Dm)

    kb, kn, ks = c["k_back"], c["k_north"], c["k_swim"]
    poly = [(sx, sy)] + WAY[name] + [(P0[0], P0[1])]
    cum = [0.0]
    for a_, b_ in zip(poly, poly[1:]): cum.append(cum[-1] + math.dist(a_, b_))
    dN = cum[-1]; vf = c["fast_speed"]; R = c["fast_ramp"]
    kT = int(round(ks + R / 2.0 + dN / vf))                              # llegada al pie de la escalera

    def poly_at(s_):
        s_ = min(max(s_, 0.0), dN - 1e-9)
        q = next(i for i in range(1, len(cum)) if cum[i] >= s_); t = (s_ - cum[q - 1]) / max(cum[q] - cum[q - 1], 1e-9)
        return (poly[q - 1][0] + (poly[q][0] - poly[q - 1][0]) * t, poly[q - 1][1] + (poly[q][1] - poly[q - 1][1]) * t)
    leg1 = math.atan2(-(poly[1][0] - sx), (poly[1][1] - sy)) if len(poly) > 2 else 0.0
    k_w = ks + R / 2.0 + (cum[1] / vf if len(poly) > 2 else 0.0)
    STAND = stand_pose(os.path.join(BASE, c["stand"]), bones, SW.row(SW.f1)) if c["stand"] else None

    # ------------------------------------------------ poses "en el sitio" (no nadan hacia delante)
    def alfred_stand(k):
        r = copy.deepcopy(STAND)

        def e(b, a, d): r[b]["rotation_euler"][a] += d
        g1 = pulse(k, 352, 392) + pulse(k, 412, 446)                       # discute: manos abiertas
        yaw = (22 + 14 * math.sin((k - 352) * 0.20)) * D2R * pulse(k, 345, 480, 12, 12)   # cabeza hacia Jerry / niega
        e("Neck_alfred", 1, yaw); e("Spine2_alfred", 1, yaw * 0.3); e("Neck_alfred", 0, 6 * D2R * g1); e("Spine_alfred", 0, 7 * D2R * g1)
        for b, s in (("RightUpArm_alfred", 1), ("LeftUpArm_alfred", -1)):
            e(b, 0, -50 * D2R * g1); e(b, 1, s * (35 + 10 * math.sin((k - 352) * 0.35)) * D2R * g1)
        e("Rightelbow_alfred", 2, -55 * D2R * g1); e("Leftelbow_alfred", 2, 55 * D2R * g1)
        back = pulse(k, kb - 4, kb + 8, 8, 8); fright = epulse(k, kb + 8, kn + 8, 14, 16)     # gira el torso/cuello hacia atras SOLO mientras el cuerpo gira (f478-498); al susto el cuerpo ya mira a los zombies
        e("Neck_alfred", 1, 55 * D2R * back); e("Spine2_alfred", 1, 45 * D2R * back); e("Spine1_alfred", 1, 30 * D2R * back)
        # SUSTO: brazos en V (arriba y hacia afuera, codos estirados, temblor leve) y ojos muy abiertos
        tremble = 1.0 + 0.06 * math.sin(k * 1.7)
        for b, s in (("RightUpArm_alfred", 1), ("LeftUpArm_alfred", -1)):
            e(b, 0, -(140 if s > 0 else 140 + V_LEFT_EXTRA) * D2R * fright * tremble); e(b, 1, s * 8 * D2R * fright)
        for b, sg in (("Rightelbow_alfred", -1), ("Leftelbow_alfred", 1)):                # codos estirados (casi 0) en la V
            r[b]["rotation_euler"][2] = r[b]["rotation_euler"][2] * (1 - fright) + sg * 6 * D2R * fright
        e("Hips_alfred", 0, -9 * D2R * fright); e("Neck_alfred", 0, 8 * D2R * fright)
        zero = pulse(k, kb + 6, kn + 12, 4, 8)                                    # en el susto (f~496-530) Neck/Spine1/Spine2 con rotacion Y = 0: el cuerpo ya mira a los zombies
        for b_ in ("Neck_alfred", "Spine1_alfred", "Spine2_alfred"): r[b_]["rotation_euler"][1] *= (1 - zero)
        return r

    def jerry_tread(k):
        r = copy.deepcopy(swim_row(k, 0.55, base_k=c["stand_a"], ph_base=ph0 + (c["stand_a"] - 1)))   # chapoteo tranquilo en el sitio

        def e(b, a, d): r[b]["rotation_euler"][a] += d
        e("scull_1", 2, pulse(k, 278, 300, 8, 8) * (30 * math.sin((k - 278) * 0.35)) * D2R)          # Jerry es el primero en mirar alrededor
        for kk in (352, 380, 414, 442):                                                              # ladra a Alfred
            bark = pulse(k, kk, kk + 9, 3, 4); e("jaw_bot", 0, -0.5 * bark); e("scull_1", 0, -0.12 * bark)
        e("scull_1", 2, 0.10 * math.sin((k - 300) * 0.30) * pulse(k, 300, 480, 12, 12))
        fright = epulse(k, kb + 8, kn + 8, 14, 16); e("jaw_bot", 0, -0.35 * fright); e("scull_1", 0, 0.18 * fright)
        return r

    # ------------------------------------------------ SALTOS DE SUBIDA DE JERRY (7 escalones seguidos, sin parones) -- reemplaza la carrera/pausa del motor base
    # Cada salto (15 f): agacharse (cuartos traseros y pecho se comprimen, pies casi fijos) -> impulso (cuerpo se levanta, patas traseras empujan hacia atras,
    # patas delanteras suben) -> vuelo en parabola (delanteras al frente, traseras recogidas, boca entreabierta, orejas y cola al aire) -> aterrizaje que amortigua
    # con las delanteras y encadena con el siguiente agachado. Cada salto es algo distinto (altura del vuelo, amplitud, cola).
    JC_N = 105; JC_T = 15
    JK = [  # (u, {hueso: grados X})   cuarto trasero = thigh/shin/foot; delantero = front_*
        (0.00, {"thigh": 12, "shin": -12, "front_thigh": 8, "front_shin": -8, "front_shoulder": 0, "spine_6": -4, "spine_4": 3, "spine_2": 2, "scull_1": -4, "tail_1": 8, "ear": 6, "jaw": 0.0}),
        (0.20, {"thigh": 28, "shin": -28, "front_thigh": 18, "front_shin": -18, "front_shoulder": -6, "spine_6": -9, "spine_4": 7, "spine_2": 5, "scull_1": -10, "tail_1": 14, "ear": 10, "jaw": 0.0}),
        (0.36, {"thigh": -32, "shin": -14, "front_thigh": -8, "front_shin": 6, "front_shoulder": 34, "spine_6": 20, "spine_4": -9, "spine_2": -5, "scull_1": -6, "tail_1": -26, "ear": -18, "jaw": -0.10}),
        (0.58, {"thigh": -24, "shin": -34, "front_thigh": -22, "front_shin": -10, "front_shoulder": 26, "spine_6": 12, "spine_4": -4, "spine_2": -2, "scull_1": 2, "tail_1": -16, "ear": -26, "jaw": -0.22}),
        (0.80, {"thigh": 10, "shin": -12, "front_thigh": 12, "front_shin": -22, "front_shoulder": -10, "spine_6": -14, "spine_4": 9, "spine_2": 6, "scull_1": 8, "tail_1": 10, "ear": 4, "jaw": -0.04}),
        (1.00, {"thigh": 12, "shin": -12, "front_thigh": 8, "front_shin": -8, "front_shoulder": 0, "spine_6": -4, "spine_4": 3, "spine_2": 2, "scull_1": -4, "tail_1": 8, "ear": 6, "jaw": 0.0}),
    ]
    JVAR = [(1.00, 0.40, 1.0), (0.92, 0.46, 0.8), (1.08, 0.38, 1.1), (0.96, 0.50, 0.9), (1.05, 0.36, 1.0), (0.90, 0.48, 1.2), (1.10, 0.42, 0.85)]   # (amplitud, altura extra del vuelo m, meneo de cola)

    def jc_idx(j): return min(6, (j - 1) // JC_T), ((j - 1) % JC_T) / float(JC_T)

    def jc_x(j):
        i, u = jc_idx(j); xa, xb = -82.5 - i, -83.5 - i
        e = 0.05 * ss(u / 0.2) if u < 0.2 else (0.05 + 0.90 * ss((u - 0.2) / 0.6) if u < 0.8 else 0.95 + 0.05 * ss((u - 0.8) / 0.2))
        return xa + (xb - xa) * e

    def jc_z(j):
        i, u = jc_idx(j); za, zb = 7.0 + i, 8.0 + i; hop = JVAR[i][1]
        if u <= 0.28: return za + 0.07                                                   # +0.07: al agacharse los pies se hundian hasta 7 cm mas que en reposo
        if u >= 0.80: return zb + 0.07
        sv = (u - 0.28) / 0.52
        return za + (zb - za) * ss(sv) + hop * 4 * sv * (1 - sv) + 0.07 * (1 - math.sin(math.pi * sv))

    def jc_pose(j):
        i, u = jc_idx(j); amp = JVAR[i][0]; tw = JVAR[i][2]
        for (u0, k0), (u1, k1) in zip(JK, JK[1:]):
            if u0 <= u <= u1:
                w = ss((u - u0) / (u1 - u0)); v = {kk: k0[kk] + (k1[kk] - k0[kk]) * w for kk in k0}; break
        r = copy.deepcopy(TR.row(1))

        def add(b, a, d): r[b]["rotation_euler"][a] += d

        for sd in ("R", "L"):
            ph = 0.0 if sd == "R" else 0.35                                                  # las dos patas no se mueven exactamente a la vez
            add(f"thigh.{sd}", 0, amp * v["thigh"] * D2R * (1 + (0.08 if sd == "L" else 0)))
            add(f"shin.{sd}", 0, amp * v["shin"] * D2R); add(f"foot.{sd}", 0, 0.5 * amp * v["shin"] * D2R * -1)
            add(f"front_thigh.{sd}", 0, amp * v["front_thigh"] * D2R); add(f"front_shin.{sd}", 0, amp * v["front_shin"] * D2R)
            add(f"front_shoulder.{sd}", 0, amp * v["front_shoulder"] * D2R * (1 - 0.15 * ph))
            add(f"ear.{sd}", 0, v["ear"] * D2R * (1 + 0.3 * math.sin(j * 0.9 + ph * 6)))
        add("spine_6", 0, amp * v["spine_6"] * D2R); add("spine_4", 0, amp * v["spine_4"] * D2R); add("spine_2", 0, amp * v["spine_2"] * D2R)
        add("spine_1", 0, 0.5 * amp * v["spine_2"] * D2R); add("scull_1", 0, v["scull_1"] * D2R)
        for tb, f_ in (("tail_1", 1.0), ("tail_2", 0.8), ("tail_3", 0.6)):
            add(tb, 0, f_ * v["tail_1"] * D2R); add(tb, 2, f_ * tw * 0.35 * math.sin(j * 0.55 + (0.6 if tb != "tail_1" else 0)))      # meneo lateral de la cola
        add("jaw_bot", 0, v["jaw"])
        return r

    ktr = TR.f1
    jmax = ktr                                                           # ultimo frame del tramo de tierra que se usa
    if name == "jerry" and SLIP:                                         # Jerry se detiene al ver resbalar a Alfred (kS + 6) y mira desde arriba
        if "kS" not in SLIP_INFO: build("alfred")
        jmax = ktr                                                        # sube y solo avanza hasta (-90.8,-105.2): 1.3 m pasado el borde; alli espera a Alfred
    kBack = SLIP_INFO["kS"] + 2 if (name == "jerry" and SLIP) else kT + jmax - 1   # al resbalar Alfred, Jerry gira en seco (kS+2) y vuelve al borde de la subida
    kEnd = kT + ktr - 1                                                   # fin del tramo de tierra
    EDGE_J = (-89.7, -104.3, 14.0)                                        # borde superior de la escalera (primer escalon a z=14), ligeramente al norte de la linea por donde rueda Alfred (y=-104.8)
    if name == "jerry" and SLIP:
        P0j = TR.root("location", jmax); dj = math.hypot(EDGE_J[0] - P0j[0], EDGE_J[1] - P0j[1]); Dj = int(dj / 0.17) + 8
        kArr = kBack + Dj; kE = kArr                                      # llegada al borde (z se mantiene en 14)
        rz_end = norm(TR.root("rotation_euler", ktr)[2]); fz_w = math.atan2(-(-86.0 - P0j[0]), (-104.8 - P0j[1]))   # mientras espera mira hacia la escalera (por donde sube Alfred)
        rz_j0 = fz_w; hd_j = math.atan2(-(EDGE_J[0] - P0j[0]), (EDGE_J[1] - P0j[1]))
        fz_j = math.atan2(-(-86.0 - EDGE_J[0]), (-104.8 - EDGE_J[1]))     # una vez en el borde mira hacia donde rueda Alfred
    else:
        kE = kT + jmax - 1                                                # llegada al punto de descanso
    BR = []; acc_ = 0.0
    for k_ in range(1, N + 1):                                            # fase de respiracion: periodo 24 f al llegar -> 40 f al calmarse
        acc_ += 2 * math.pi / (24.0 + 16.0 * ss((k_ - kE) / 150.0)); BR.append(acc_)

    def land_rest(k):
        """Alfred descansa (inclinado, manos en las rodillas, jadeando) y luego escucha de pie cansado; Jerry le habla del refugio."""
        r = copy.deepcopy(STAND)

        def e(b, a, d): r[b]["rotation_euler"][a] += d
        if name == "alfred":
            # RESPIRAR TRAS CORRER MUCHO: se dobla por la cintura con las manos en las rodillas (brazos rectos empujando), rodillas algo flexionadas,
            # cabeza colgando, jadeo rapido al principio (periodo ~24 f, amplitud grande) que se va calmando; despues una inhalacion profunda y se incorpora.
            bent = ss((k - (kE - 6)) / 20.0) * (1 - ss((k - (kE + 128)) / 40.0)); upr = ss((k - (kE + 128)) / 40.0)
            calm = ss((k - kE) / 130.0); amp = 1.0 - 0.55 * calm; br = math.sin(BR[k - 1]); br2 = math.sin(BR[k - 1] * 2 + 0.7)

            def tgt(b, a, deg, w): r[b]["rotation_euler"][a] = r[b]["rotation_euler"][a] * (1 - w) + deg * D2R * w
            tgt("Hips_alfred", 0, REST_P["hips"] + 2.2 * br * amp, bent); tgt("Spine_alfred", 0, REST_P["spine"] + 3.2 * br * amp, bent); tgt("Spine1_alfred", 0, REST_P["spine1"] + 2.6 * br * amp, bent)
            tgt("Spine2_alfred", 0, REST_P["spine2"] + 3.4 * br * amp, bent); tgt("Neck_alfred", 0, REST_P["neck"] - 5 * br * amp + 2 * br2 * amp, bent); tgt("Neck_alfred", 1, 6 * math.sin(k * 0.021), bent)
            for sd in ("Right", "Left"):
                tgt(f"{sd}UpLeg_alfred", 0, REST_P["leg"], bent); tgt(f"{sd}knee_alfred", 0, REST_P["knee"] - 2.5 * br * amp, bent)
            for sd, sg in (("Right", 1), ("Left", -1)):
                tgt(f"{sd}UpArm_alfred", 0, REST_P["arm_x"] + 3.0 * br * amp, bent); tgt(f"{sd}UpArm_alfred", 1, sg * (REST_P["arm_y"] + 2.0 * br * amp), bent)       # brazos rectos hasta la rodilla; los hombros suben y bajan con cada respiracion
            tgt("Rightelbow_alfred", 2, 0, bent); tgt("Leftelbow_alfred", 2, 0, bent)
            tgt("Hips_alfred", 2, 1.6 * math.sin(k * 0.05), bent)                                                                           # leve balanceo por el cansancio
            # inhalacion profunda al incorporarse (f+120..f+160): cabeza atras, pecho abierto, brazos algo separados
            deep = pulse(k, kE + 118, kE + 165, 14, 22)
            e("Neck_alfred", 0, -14 * D2R * deep); e("Spine_alfred", 0, -6 * D2R * deep); e("Spine2_alfred", 0, -5 * D2R * deep)
            for b_, sg in (("RightUpArm_alfred", 1), ("LeftUpArm_alfred", -1)): e(b_, 0, -14 * D2R * deep); e(b_, 1, sg * 8 * D2R * deep)
            # de pie cansado, escuchando a Jerry: cabeza a Jerry, asiente, mira alrededor un momento
            e("Spine_alfred", 0, (6 + 1.2 * br) * D2R * upr); e("Neck_alfred", 0, (4 + 6 * max(0.0, math.sin((k - kE) * 0.085))) * D2R * upr)
            e("Neck_alfred", 1, (10 * math.sin((k - kE) * 0.05)) * D2R * upr); e("Hips_alfred", 0, 3 * D2R * upr)
            look = pulse(k, kE + 205, kE + 235, 10, 12); e("Neck_alfred", 1, 40 * D2R * look); e("Neck_alfred", 0, -6 * D2R * look)
        else:
            w = ss((k - (kE - 10)) / 20.0)
            if SLIP:                                                                                                     # ve caer a Alfred desde arriba: se sobresalta con cada golpe y luego se tapa la cara decepcionado
                hits = [SLIP_INFO["t1"]] + SLIP_INFO["starts"][1:]                                                    # cada aterrizaje (golpe) de Alfred: caida de bruces + 6 escalones
                t_end = SLIP_INFO["t2"]
                look = ss((k - (kE - 6)) / 10.0)                                                                       # cabeza erguida mirando hacia la escalera
                e("scull_1", 0, -0.10 * look); e("scull_1", 2, 0.0)
                for i_, th_ in enumerate(hits):                                                                        # sobresalto en cada golpe (elastico): cabeza se echa atras y baja, la mandibula se abre mas con los golpes fuertes
                    f_ = epulse(k, th_ - 1, th_ + 10, 3, 7)
                    big = 0.55 + 0.45 * ((i_ % 3) / 2.0)
                    e("scull_1", 0, 0.20 * f_ * big); e("scull_1", 2, (0.10 if i_ % 2 else -0.10) * f_)
                    e("jaw_bot", 0, -0.30 * f_ * big)
                    for tb in ("tail_1", "tail_2", "tail_3"): e(tb, 2, 0.18 * math.sin(k * 0.7) * f_)
                # tras el ultimo golpe: se tapa la cara con la pata derecha y mueve la cabeza a derecha e izquierda (decepcionado)
                cov = epulse(k, t_end + 8, t_end + 28, 12, 12) * (1 - ss((k - (N - 8)) / 8.0)) if False else ela((k - (t_end + 8)) / 18.0)
                cov = max(0.0, min(1.0, cov))
                def tg(b_, a_, deg): r[b_]["rotation_euler"][a_] = r[b_]["rotation_euler"][a_] * (1 - cov) + deg * D2R * cov
                tg("front_shoulder.R", 0, 30); tg("front_shoulder.R", 2, 20); tg("front_thigh.R", 0, 0); tg("front_shin.R", 0, 60); tg("front_foot.R", 0, 40)         # pata derecha sobre la cara (medido: dedo a 5 cm del centro de la cara)
                sh_ = max(0.0, ss((k - (t_end + 30)) / 14.0))
                e("scull_1", 2, 0.62 * math.sin((k - (t_end + 30)) * 0.21) * sh_)                                       # niega con la cabeza: derecha-izquierda (~35 grados)
                e("scull_1", 0, 0.16 * cov)                                                                              # cabeza algo baja
                e("jaw_bot", 0, -0.05 * cov * (0.5 + 0.5 * math.sin((k - t_end) * 0.15)))                               # suspira
                return r
            talk = pulse(k, kE + 55, kE + 250, 10, 12)
            e("scull_1", 2, (12 * math.sin((k - kE) * 0.06) + 22 * pulse(k, kE + 40, kE + 60, 6, 6)) * D2R * w)          # primero espera mirando al cabo de la escalera, luego a Alfred
            for kk in range(kE + 60, kE + 250, 34):                                                                        # habla en rafagas: mandibula + cabeceo
                bur = pulse(k, kk, kk + 22, 4, 5); ph = (k - kk) * 0.9
                e("jaw_bot", 0, -0.42 * bur * (0.55 + 0.45 * math.sin(ph))); e("scull_1", 0, -0.10 * bur * math.sin(ph * 0.5))
            gest = pulse(k, kE + 150, kE + 215, 10, 10); e("scull_1", 2, 0.55 * math.sin((k - kE - 150) * 0.11) * gest)  # mira a los lados (donde levantar el refugio)
            for tb, ax, amp in (("tail_1", 2, 0.22), ("tail_2", 2, 0.30), ("tail_3", 2, 0.38)):
                e(tb, ax, amp * math.sin(k * 0.24) * talk)                                                                # mueve la cola mientras habla
        return r

    # ------------------------------------------------ RESBALON, UNA VUELTA LATERAL POR CADA ESCALON (todas distintas), LUEGO FLOTAR (solo Alfred)
    # Alfred resbala subiendo (mira al oeste), cae de bruces y, TUMBADO PARALELO AL SUELO (Hips X=90, cara abajo), rueda de lado cuesta abajo (este): UNA vuelta
    # completa (Hips Z -360) por cada metro de altura que baja (z 13->7, 6 escalones). Cada caida es distinta: duracion, rebote, perfil de giro, desvio
    # lateral, guinada del cuerpo, caida en el borde y posicion de brazos/piernas cambian en cada escalon.
    SL = {}
    if name == "alfred" and SLIP:
        jj_s = next(i for i in range(1, ktr + 1) if TR.root("location", i)[0] <= -88.5)
        kS = kT + jj_s - 1; t1 = kS + 16
        x_s, y_s, z_s = TR.root("location", jj_s)
        # un escalon = una vuelta; (duracion f, rebote m, inicio de la caida u, sesgo del giro, desvio y m, guinada deg, fase, amp brazos, amp piernas, giro de cuello, impacto deg)
        STEPS = [(12, 0.22, 0.52, 0.35, +0.10, 7, 0.0, 70, 18, 14, 5), (19, 0.46, 0.58, -0.30, -0.18, 12, 1.9, 55, 26, 22, 9), (14, 0.30, 0.50, 0.55, +0.22, 5, 3.6, 80, 20, 10, 6),
                 (17, 0.40, 0.62, -0.10, -0.08, 14, 0.8, 62, 30, 25, 8), (15, 0.27, 0.55, 0.20, +0.15, 9, 2.7, 75, 16, 16, 7), (21, 0.50, 0.60, -0.45, -0.24, 11, 4.4, 58, 28, 20, 10)]
        starts = [t1]
        for st_ in STEPS: starts.append(starts[-1] + st_[0])
        t2 = starts[-1]; SLIP_INFO.update({"kS": kS, "t1": t1, "t2": t2, "starts": list(starts)}); SL = {"kS": kS, "t1": t1, "t2": t2, "x0": x_s + 0.5, "y": y_s, "z0": z_s}
        zt = lambda n: 13.0 - n if n <= 5 else 7.0
        LAND = [SL["x0"]] + [-88.9 + i for i in range(1, 7)]                                    # x donde aterriza en cada escalon (el 6 es el agua, x=-82.9)
        Y_ROLL = -104.8                                                                         # coordenada Y del root durante las vueltas (pedido del usuario): evita que las mallas de los pies se solapen con el suelo

        def step_of(k):
            for i in range(len(STEPS)):
                if starts[i] <= k < starts[i + 1]: return i, (k - starts[i]) / float(STEPS[i][0])
            return len(STEPS) - 1, 1.0

        def roll_th(k):                                                                       # grados: -360 por escalon, con perfil distinto en cada uno
            if k < t1: return 0.0
            if k >= t2: return -360.0 * len(STEPS)
            i, u = step_of(k); bsk = STEPS[i][3]
            return -360.0 * (i + u + bsk * math.sin(2 * math.pi * u) / (2 * math.pi))

        def hips_x(k):
            sv = k - kS
            if k < t1:
                if sv < 6: return -22.0 * ela(sv / 6.0)                                       # el pie delantero patina sobre la piedra mojada: el torso se va hacia atras (elastico)
                return -22.0 + 112.0 * ss((sv - 6) / 10.0)                                     # intenta recuperarse y cae de bruces sobre el escalon (tumbado)
            if k < t2:
                i, u = step_of(k); imp = STEPS[i][10]
                return 90.0 + imp * math.sin(2 * math.pi * u * 2) * math.exp(-u * 3.0)         # sacudida al aterrizar cada escalon
            u = k - t2; return 90.0 + 4 * math.sin(0.1 * u) * math.exp(-u / 45.0)

        def slip_root(k):
            if k < t1:
                sv = (k - kS) / 16.0
                sag = 0.20 * ss((k - kS) / 6.0) * (1 - ss((k - (kS + 6)) / 6.0))                # la pierna de apoyo cede: la cadera baja
                return [x_s + 0.5 * ss(sv), SL["y"] + (Y_ROLL - SL["y"]) * ss((k - (kS + 6)) / 10.0), z_s - sag - 0.42 * ss((k - (kS + 6)) / 10.0)], 90 * D2R + 90 * D2R * ss((k - (kS + 6)) / 10.0)
            if k < t2:
                i, u = step_of(k); hop, ud, ydr, yaw, ph0_ = STEPS[i][1], STEPS[i][2], STEPS[i][4], STEPS[i][5], STEPS[i][6]
                xa, xb = LAND[i], LAND[i + 1]; ex_ = u + STEPS[i][3] * 0.25 * math.sin(2 * math.pi * u) / (2 * math.pi)
                x = xa + (xb - xa) * ex_
                zb = zt(i) - (1.0 if i < 5 else 1.0) * (((u - ud) / (1.0 - ud)) ** 2 if u > ud else 0.0)
                bounce = hop * math.sin(math.pi * min(1.0, u / 0.45)) if u < 0.45 else 0.0
                y = Y_ROLL + 0.3 * ydr * math.sin(math.pi * u)
                return [x, y, zb + bounce - 0.42], (180 + yaw * math.sin(2 * math.pi * u + ph0_)) * D2R
            u = k - t2
            x = LAND[6] + 0.9 * (1 - math.exp(-u / 40.0)); z = 6.907 - 0.25 * pulse(k, t2, t2 + 14, 3, 12) + 0.035 * math.sin(0.12 * u) * ss(u / 20.0)    # entra al agua y flota (eje de la cadera 0.11 m bajo la superficie 7.89)
            return [x, Y_ROLL + 0.05 * math.sin(0.05 * u), z], 180 * D2R

        def slip_row(k):
            r = copy.deepcopy(STAND)

            def setb(b, a, deg): r[b]["rotation_euler"][a] = deg * D2R
            sv = k - kS; setb("Hips_alfred", 0, hips_x(k))
            if k < t1:                                                                         # RESBALON en contexto: sube mojado y agotado, huyendo; mira atras a los zombies y no ve el escalon
                aw = ela(sv / 8.0) * (1 - ela((sv - 7) / 7.0))                                 # susto: brazos en V (elastico)
                reach = ss((sv - 6) / 4.0) * (1 - ss((sv - 12) / 4.0))                         # estira las manos para agarrarse del escalon
                slide = ela(sv / 5.0) * (1 - ss((sv - 9) / 5.0))                               # el pie delantero patina hacia delante sobre la piedra mojada
                for sd, sg in (("Right", 1), ("Left", -1)):
                    setb(f"{sd}UpArm_alfred", 0, 90 - 150 * aw * (1 - reach) - 45 * reach); setb(f"{sd}UpArm_alfred", 1, sg * (10 * aw + 40 * reach))
                    setb(f"{sd}elbow_alfred", 2, sg * -(8 + 14 * reach))
                setb("LeftUpLeg_alfred", 0, 58 * slide); setb("Leftknee_alfred", 0, -4 * slide)             # pierna que patina: casi recta y adelantada
                setb("RightUpLeg_alfred", 0, -22 * slide); setb("Rightknee_alfred", 0, -75 * slide)         # pierna de apoyo: la rodilla cede
                gl_ = pulse(k, kS - 16, kS + 3, 6, 4)                                          # aun mira hacia atras (a los zombies) cuando pierde el pie, luego vuelve la cabeza
                setb("Neck_alfred", 1, 55 * gl_); setb("Spine2_alfred", 1, 18 * gl_)
                setb("Neck_alfred", 0, -10 * aw + 30 * ss((sv - 9) / 7.0))
                return r
            if k < t2:
                i, u = step_of(k); _, _, _, _, _, _, ph0_, aamp, lamp, nturn, _ = STEPS[i]
                th = roll_th(k); setb("Hips_alfred", 2, th); ph_ = math.radians(th) + ph0_
                for sd, sg, off in (("Right", 1, 0.0), ("Left", -1, 1.9)):
                    setb(f"{sd}UpArm_alfred", 0, 90 - 0.5 * aamp - 0.5 * aamp * math.sin(ph_ + off)); setb(f"{sd}UpArm_alfred", 1, sg * (18 + 0.45 * aamp * math.sin(ph_ * 0.5 + off + 1)))
                    setb(f"{sd}elbow_alfred", 2, sg * -(20 + 0.5 * aamp * (0.5 + 0.5 * math.sin(ph_ + off + 0.7))))
                    setb(f"{sd}UpLeg_alfred", 0, lamp * math.sin(ph_ + off + 0.5)); setb(f"{sd}knee_alfred", 0, -(18 + lamp * (0.5 + 0.5 * math.sin(ph_ + off + 2.0))))
                setb("Neck_alfred", 0, 14 + 8 * math.sin(ph_)); setb("Neck_alfred", 1, nturn * math.sin(ph_ * 0.5 + 0.3)); setb("Spine_alfred", 0, 6 * math.sin(ph_ + 1.0))
            else:                                                                              # flotando boca abajo: cuerpo laxo, brazos y piernas colgando, cabeza caida, leve vaiven
                u = k - t2; sw = math.sin(0.12 * u); setb("Hips_alfred", 2, -360.0 * len(STEPS))
                for sd, sg in (("Right", 1), ("Left", -1)):
                    setb(f"{sd}UpArm_alfred", 0, 55 + 5 * sw); setb(f"{sd}UpArm_alfred", 1, sg * (30 + 4 * math.sin(0.1 * u + 1)))
                    setb(f"{sd}elbow_alfred", 2, sg * -(18 + 6 * sw)); setb(f"{sd}UpLeg_alfred", 0, 8 + 3 * math.sin(0.1 * u + (0 if sd == "Right" else 2.0))); setb(f"{sd}knee_alfred", 0, -10)
                setb("Neck_alfred", 0, 28 + 3 * sw); setb("Neck_alfred", 1, 0)
            return r

    def wait_row(k):
        r = copy.deepcopy(STAND)

        def e(b, a, d): r[b]["rotation_euler"][a] += d
        u = k - kEnd
        e("scull_1", 2, (0.12 * math.sin(u * 0.09) + 0.10 * pulse(k, kEnd + 12, kEnd + 34, 6, 6)) if name == "jerry" else 0.0)       # mira hacia la escalera, con algun vistazo extra
        e("scull_1", 0, 0.10 * pulse(k, kEnd + 6, kEnd + 40, 8, 8))                                                                    # asoma la cabeza para ver mejor
        e("jaw_bot", 0, -0.06 * (0.5 + 0.5 * math.sin(u * 0.45)))                                                                      # jadea
        for tb, ax, amp in (("tail_1", 2, 0.16), ("tail_2", 2, 0.22), ("tail_3", 2, 0.28)): e(tb, ax, amp * math.sin(k * 0.3))        # cola contenta/ansiosa
        return r

    inplace = alfred_stand if name == "alfred" else jerry_tread
    rows = {b: {p: [None] * N for p in ("rotation_euler", "location", "scale")} for b in bones}
    rloc = [None] * N; rrot = [None] * N
    # rumbo (desenrollado): Alfred gira a la izquierda para mirar atras; Jerry a la derecha para encarar a Alfred
    if name == "alfred":
        rz_seq = [(0, rz0), (kb - 4, rz0), (kb + 14, 90 * D2R), (kn, 90 * D2R), (ks + 6, leg1), (k_w, leg1), (k_w + 16, RZ_NORTH)]
    else:
        rz_alf = math.atan2(-(ALF_STOP[0] - sx), (ALF_STOP[1] - sy))
        rz_seq = [(0, rz0), (284, rz0), (306, rz_alf - 2 * math.pi), (kn, rz_alf - 2 * math.pi), (ks + 6, RZ_NORTH - 2 * math.pi)]

    def rz_at(k):
        if k <= rz_seq[0][0]: return rz_seq[0][1]
        for (ta, ra), (tb, rb) in zip(rz_seq, rz_seq[1:]):
            if ta <= k <= tb: return ra + (rb - ra) * ss((k - ta) / float(max(tb - ta, 1)))
        return rz_seq[-1][1]

    for k in range(1, N + 1):
        j = k - kT + 1                                                   # frame del tramo de tierra
        # ---------- huesos
        b = swim_row(k)
        b = mixrow(b, inplace(k), ss((k - c["stand_a"]) / float(c["stand_d"])))
        fa = 22.0 if name == "alfred" else 14.0
        b = mixrow(b, swim_row(k, c["fast_rate"], base_k=ks, ph_base=0.0), ss((k - (ks - (fa if name == "alfred" else 12))) / fa))
        if j >= 1:
            rowj = TR.row(min(j, jmax))
            if name == "jerry" and 1 <= j <= JC_N: rowj = jc_pose(j)
            elif name == "jerry" and JC_N < j <= JC_N + 8: rowj = mixrow(jc_pose(JC_N), TR.row(min(j, jmax)), ss((j - JC_N) / 8.0))     # al terminar los saltos pasa suave al trote final
            if name == "jerry" and SLIP and kEnd < k <= kBack:                                              # espera a Alfred en el borde, mirando la subida: respira agitado, mira hacia abajo y mueve la cola
                rowj = mixrow(TR.row(ktr), wait_row(k), ss((k - kEnd) / 8.0))
            if name == "jerry" and SLIP and k > kBack:                                                       # corre de vuelta al borde (ciclo de carrera de 12 f a ritmo x1.5)
                rowj = TR.row(130 + (((k - kBack) * 1.5) % 12.0))
                if k - kBack < 4: rowj = mixrow(TR.row(jmax), rowj, ss((k - kBack) / 4.0))
            b = mixrow(b, rowj, ss((j + 8) / 12.0))
            if name == "jerry" and SLIP:
                if k > kE - 6: b = mixrow(b, land_rest(k), ss((k - (kE - 6)) / 8.0))
            elif k > kE - 25 and not (name == "alfred" and SLIP): b = mixrow(b, land_rest(k), ss((k - (kE - 22)) / 22.0))
        if SL and SL["kS"] - 16 <= k < SL["kS"] + 4:                                                   # sube corriendo y gira la cabeza hacia los zombies (sur): no mira donde pisa
            gl_ = pulse(k, SL["kS"] - 16, SL["kS"] + 3, 6, 4); b = copy.deepcopy(b)
            b["Neck_alfred"]["rotation_euler"][1] += 55 * D2R * gl_; b["Spine2_alfred"]["rotation_euler"][1] += 18 * D2R * gl_
        if SL and k >= SL["kS"]: b = mixrow(b, slip_row(k), ss((k - SL["kS"]) / 3.0))
        for bn in bones:
            for p in ("rotation_euler", "location", "scale"):
                rows[bn][p][k - 1] = b[bn][p]
        # ---------- raiz
        if j >= 1:
            jj = min(j, jmax)
            loc = TR.root("location", jj); rot = TR.root("rotation_euler", jj); rz = norm(rot[2])
            if name == "jerry" and 1 <= j <= JC_N: loc = [jc_x(j), loc[1], jc_z(j)]
            if name == "jerry" and SLIP and kEnd < k <= kBack: rz = rz_end + norm(fz_w - rz_end) * ss((k - (kEnd + 3)) / 10.0)          # se gira hacia la escalera mientras espera
            if name == "jerry" and SLIP and k > kBack:                                                       # vuelta al borde: lineal con arranque/frenada suaves, siempre a z=14
                uj = min(1.0, (k - kBack) / float(Dj)); ej = ss(uj)
                loc = [P0j[0] + (EDGE_J[0] - P0j[0]) * ej, P0j[1] + (EDGE_J[1] - P0j[1]) * ej, 14.0]
                rz = rz_j0 + norm(hd_j - rz_j0) * ss((k - kBack) / 6.0)
                rz = rz + norm(fz_j - rz) * ss((k - (kArr - 8)) / 8.0)
            if j <= 12: rz = RZ_NORTH + (90 * D2R - RZ_NORTH) * ss((j - 1) / 11.0)                 # de cara a la costa -> rumbo oeste de la escalera
            if name == "alfred" and not SLIP: loc = [loc[0], loc[1], loc[2] + REST_P["root_dz"] * ss((k - (kE - 6)) / 20.0) * (1 - ss((k - (kE + 128)) / 40.0))]      # piernas casi rectas y pies bajo la cadera: al inclinarse el pie baja 0.2 m, se sube el root
            wl = ss((jj - (ktr - 30)) / 30.0) if not SLIP else 0.0; loc = [loc[0] + (REST[name][0] - loc[0]) * wl, loc[1] + (REST[name][1] - loc[1]) * wl, loc[2]]   # termina EXACTO en el punto de descanso
            fz = FACE[name]
            if name == "jerry" and SLIP: fz = rz                                                           # el rumbo ya lo da la vuelta al borde
            wf = ss((k - (kE - 10)) / 32.0) if not (name == "alfred" and SLIP) else 0.0; rz = rz + norm(fz - rz) * wf                                                                 # al parar se encaran
            rot = [rot[0], rot[1], rz + (-2 * math.pi if name == "jerry" else 0.0)]
            if SL and k >= SL["kS"]:
                loc_s, rz_s = slip_root(k); a_ = ss((k - SL["kS"]) / 3.0); loc = [loc[i] + (loc_s[i] - loc[i]) * a_ for i in range(3)]; rot = [0.0, 0.0, rot[2] + norm(rz_s - rot[2]) * a_]
        else:
            if k <= ks:
                x = swim_x(k); y = y0 + (sy - y0) * ss((k - 30.0) / (k_c + Dm - 30.0)) if k <= k_c + Dm else sy
            else:
                u = k - ks; s_ = min(dN, vf * u * u / (2.0 * R) if u < R else vf * (u - R / 2.0))
                x, y = poly_at(s_)
            if name == "alfred":
                z = z0 + (c["stand_z"] - z0) * ss((k - c["stand_a"]) / float(c["stand_d"])) if k <= ks else c["stand_z"] + (z0 - c["stand_z"]) * ss((k - ks) / 22.0)
            else:
                z = z0 + 0.03 * math.sin(k * 0.22) * ss((k - c["stand_a"]) / 30.0) * (1 - ss((k - ks) / 10.0))
            loc = [x, y, z]; rot = [0.0, 0.0, rz_at(k)]
        rloc[k - 1] = loc; rrot[k - 1] = rot
    for i in range(1, N):                                                # rumbo continuo (sin saltos de 360)
        rrot[i][2] = rrot[i - 1][2] + norm(rrot[i][2] - rrot[i - 1][2])
    # ---------- ojos: ultimos valores de la parte 1; ensanchados en el susto (Alfred); al empezar el tramo, los del tramo
    ojos = copy.deepcopy(TR.d["ojos"])

    def serie(tr_v, sw_v):
        a = val(sw_v, SW.idx(t_last))
        return [round(a + (val(tr_v, TR.idx(max(1, k - kT + 1))) - a) * ss((k - (kT - 20)) / 20.0), 5) for k in range(1, N + 1)]

    for on, o in ojos.items():
        so = SW.d["ojos"].get(on)
        if so is None: continue
        for key, chans in o["canales"].items():
            o["canales"][key] = [serie(chans[a], so["canales"][key][a]) for a in range(3)]
            if key == "scale" and name == "alfred":
                fr = [epulse(k, kb + 8, kn + 8, 14, 16) for k in range(1, N + 1)]
                o["canales"][key][0] = [round(v_ * (1 + 0.35 * f_), 5) for v_, f_ in zip(o["canales"][key][0], fr)]
                o["canales"][key][2] = [round(v_ * (1 + 0.30 * f_), 5) for v_, f_ in zip(o["canales"][key][2], fr)]
        for grp in ("visibilidad", "shape_keys"):
            for key, v_ in o[grp].items():
                o[grp][key] = serie(v_, so[grp].get(key, v_))
        if name == "alfred" and SLIP and "scale" in o["canales"]:        # ojos muy abiertos al resbalar (elastico)
            wi = [epulse(k_, SL["kS"] - 8, SL["kS"] + 16, 8, 8) for k_ in range(1, N + 1)]
            o["canales"]["scale"][0] = [round(v_ * (1 + 0.35 * w_), 5) for v_, w_ in zip(o["canales"]["scale"][0], wi)]
            o["canales"]["scale"][2] = [round(v_ * (1 + 0.30 * w_), 5) for v_, w_ in zip(o["canales"]["scale"][2], wi)]
        if name == "alfred" and SLIP:                                   # ojos cerrados al caer rodando y mientras flota
            if "Closed" in o["shape_keys"]:
                o["shape_keys"]["Closed"] = [round(max(c_, ss((k_ - (SL["t1"] + 2)) / 6.0)), 5) for k_, c_ in zip(range(1, N + 1), o["shape_keys"]["Closed"])]
        if name == "alfred" and not SLIP:                                # ojos cansados mientras recupera el aliento: parpados caidos y un cierre corto al exhalar
            wtired = [ss((k - (kE - 6)) / 25.0) * (1 - ss((k - (kE + 200)) / 60.0)) for k in range(1, N + 1)]
            if "Cansado" in o["shape_keys"]: o["shape_keys"]["Cansado"] = [round(0.8 * w_, 5) for w_ in wtired]
            if "Closed" in o["shape_keys"]:
                o["shape_keys"]["Closed"] = [round(min(1.0, c_ + 0.35 * max(0.0, math.sin(BR[i] + 2.2)) * wtired[i] * (1 - ss((i + 1 - (kE + 128)) / 30.0))), 5) for i, c_ in enumerate(o["shape_keys"]["Closed"])]
            if "scale" in o["canales"]:
                o["canales"]["scale"][2] = [round(v_ * (1 - 0.18 * w_), 5) for v_, w_ in zip(o["canales"]["scale"][2], wtired)]
        if name == "alfred":                                             # ojos ABIERTOS durante el susto: sin parpadeo (Closed=0, mallas visibles)
            wopen = [pulse(k, kb - 2, kn + 24, 6, 8) for k in range(1, N + 1)]
            for grp, key in (("shape_keys", "Closed"), ("visibilidad", "hide_viewport"), ("visibilidad", "hide_render")):
                if key in o[grp]:
                    o[grp][key] = [round(v_ * (1 - w_), 5) for v_, w_ in zip(o[grp][key], wopen)]
    out = copy.deepcopy(TR.d)
    out["nombre"] = c["nombre"]; out["frame_inicio"] = 1; out["frame_fin"] = N
    out["root"]["canales"]["location"] = [[round(l[a], 5) for l in rloc] for a in range(3)]
    out["root"]["canales"]["rotation_euler"] = [[round(r[a], 5) for r in rrot] for a in range(3)]
    for bn in bones:
        for p in ("rotation_euler", "location", "scale"):
            out["armature"]["bones"][bn][p] = [[round(rows[bn][p][k][a], 5) for k in range(N)] for a in range(3)]
    out["ojos"] = ojos
    if "brillo_ojos" in SW.d and "brillo_ojos" not in out: out["brillo_ojos"] = SW.d["brillo_ojos"]
    carpeta = os.path.join(BASE, c["carpeta"], c["nombre"]); os.makedirs(carpeta, exist_ok=True)
    with open(os.path.join(carpeta, c["nombre"] + ".animacion.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    def jump(seq): return max(abs(seq[i + 1] - seq[i]) for i in range(len(seq) - 1))
    mxb = max((jump(out["armature"]["bones"][b]["rotation_euler"][a]), b, a) for b in bones for a in range(3))
    mxr = max(jump(out["root"]["canales"]["location"][a]) for a in range(3))
    rzs = out["root"]["canales"]["rotation_euler"][2]
    print(f"{name}: N={N}, para en k={round(k_c + Dm)}, miran atras k~{kb}, nado frenetico k={ks}, pie de escalera k={kT}, salto max hueso {mxb[0]:.2f} rad ({mxb[1]}.{mxb[2]}), paso max root {mxr:.2f} m/f, giro rz {math.degrees(rzs[0]):.0f}->{math.degrees(rzs[-1]):.0f}")
    print("  root k=1", [round(rloc[0][a], 2) for a in range(3)], "parada", [round(rloc[int(k_c + Dm)][a], 2) for a in range(3)], "k=ks+60", [round(rloc[ks + 60][a], 2) for a in range(3)], "fin", [round(rloc[-1][a], 2) for a in range(3)])
    return kT


if __name__ == "__main__":
    who = sys.argv[1] if len(sys.argv) > 1 else "todos"
    for n in (["alfred", "jerry"] if who == "todos" else [who]):
        build(n)
