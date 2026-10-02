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
N = 1600
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
REST = {"alfred": (-96.5, -109.5), "jerry": (-95.7, -107.5)}       # donde suben y paran (Alfred: coordenada dada por el usuario; Jerry a ~1.7 m de el)
SLIP_INFO = {}                                   # lo rellena build('alfred'): kS, t1, t2, starts de cada vuelta
SLIP = os.environ.get("SLIP", "1") == "1"        # Alfred resbala a la altura Z=13 de la escalera, rueda por los escalones y flota boca abajo (sustituye al descanso)
STAIR_FOOT = (-82.5, -104.5)
WALK_A = [(-91.0, -105.8), (-93.0, -107.6), (-95.0, -108.8), (-96.5, -109.5)]   # tras subir, Alfred cruza la meseta (cansado) hasta (-96.5,-109.5), donde descansa
KW, KC, JJ_END = 1000, 1100, 128       # Alfred: f1000 empieza a levantarse; f1100 empieza a subir otra vez (tramo base jj 1..128); llega arriba hacia el 1227
FACE = {"alfred": math.atan2(-(REST["jerry"][0] - REST["alfred"][0]), (REST["jerry"][1] - REST["alfred"][1])),   # Alfred mira a Jerry
        "jerry": (math.atan2(-(STAIR_FOOT[0] - REST["jerry"][0]), (STAIR_FOOT[1] - REST["jerry"][1])) if SLIP else math.atan2(-(REST["alfred"][0] - REST["jerry"][0]), (REST["alfred"][1] - REST["jerry"][1])))}    # Jerry mira a Alfred (o hacia la escalera/agua si Alfred cae)

ALF_STOP = (-84.5, -120.32)
RZ_NORTH = 0.0                                                             # rumbo norte (la escalera esta al norte, por el agua de x=-82.5)
WAY = {"alfred": [(-82.5, -117.5)], "jerry": []}                            # Alfred sale en diagonal al carril x=-82.5 (la orilla en x=-84 es tierra)


def build(name):
    c = CFG[name]
    SW = Art(os.path.join(BASE, c["swim"])); TR = Art(os.path.join(BASE, c["tramo"])); bones = SW.bones
    if name == "jerry": TR.d["armature"]["bones"]["front_shoulder.R"]["rotation_euler"] = [0.0, 0.0, 0.0]      # el motor base deja la pata delantera derecha fija (X30, Z20): hombro neutro como el izquierdo
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
        (0.36, {"thigh": -32, "shin": -14, "front_thigh": -8, "front_shin": -6, "front_shoulder": 34, "spine_6": 20, "spine_4": -9, "spine_2": -5, "scull_1": -6, "tail_1": -26, "ear": -18, "jaw": -0.10}),
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
            add(f"shin.{sd}", 0, amp * v["shin"] * D2R); add(f"foot.{sd}", 0, 0.5 * amp * v["shin"] * D2R)
            add(f"front_thigh.{sd}", 0, amp * v["front_thigh"] * D2R); add(f"front_shin.{sd}", 0, amp * v["front_shin"] * D2R)
            add(f"front_foot.{sd}", 0, 0.6 * amp * v["front_shin"] * D2R); add(f"front_toe.{sd}", 0, 0.3 * amp * v["front_shin"] * D2R - 0.2 * amp * v["front_shoulder"] * D2R)   # pie y dedo delanteros acompanan el salto (se flexionan al agacharse/aterrizar y se estiran en el vuelo)
            add(f"toe.{sd}", 0, 0.3 * amp * v["shin"] * D2R)
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
        if "kTop" not in SLIP_INFO: build("alfred")
        KJ2 = SLIP_INFO["kTop"] - 34; KEA = SLIP_INFO["kE_A"]                          # cuando Alfred llega arriba, Jerry corre a donde Alfred va a descansar y le habla
        dj2 = math.hypot(REST["jerry"][0] - EDGE_J[0], REST["jerry"][1] - EDGE_J[1]); Dj2 = int(dj2 / 0.15) + 8; kArr2 = KJ2 + Dj2
        RZ_HOLD_J = [None]; ALF_XY = json.load(open(os.path.join(BASE, CFG["alfred"]["carpeta"], CFG["alfred"]["nombre"], CFG["alfred"]["nombre"] + ".animacion.json"), encoding="utf-8"))["root"]["canales"]["location"]
        hd_j2 = math.atan2(-(REST["jerry"][0] - EDGE_J[0]), (REST["jerry"][1] - EDGE_J[1])); fz_j2 = math.atan2(-(REST["alfred"][0] - REST["jerry"][0]), (REST["alfred"][1] - REST["jerry"][1]))
    else:
        if name == "alfred" and SLIP:
            P_top = TR.root("location", JJ_END); pol_a = [(P_top[0], P_top[1])] + WALK_A
            cum_a = [0.0]
            for a_, b_ in zip(pol_a, pol_a[1:]): cum_a.append(cum_a[-1] + math.dist(a_, b_))
            kTop = KC + JJ_END - 1; Dw = int(cum_a[-1] / 0.07) + 1; kE = kTop + Dw                          # llega arriba en kTop y camina Dw frames a 0.07 m/f
            SLIP_INFO.update({"kTop": kTop, "kE_A": kE})
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
            kET = KEA if SLIP else kE
            w = 1.0 if SLIP else ss((k - (kE - 10)) / 20.0)
            if SLIP and k < KJ2:                                                                                                     # ve caer a Alfred desde arriba: se sobresalta con cada golpe y luego se tapa la cara decepcionado
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
                cov = ela((k - (t_end + 8)) / 18.0) * (1 - ela((k - (KW + 62)) / 10.0))          # se destapa la cara cuando Alfred se levanta y se asusta
                cov = max(0.0, min(1.0, cov))
                def tg(b_, a_, deg): r[b_]["rotation_euler"][a_] = r[b_]["rotation_euler"][a_] * (1 - cov) + deg * D2R * cov
                tg("front_shoulder.R", 0, 30); tg("front_shoulder.R", 2, 20); tg("front_thigh.R", 0, 0); tg("front_shin.R", 0, 60); tg("front_foot.R", 0, 40)         # pata derecha sobre la cara (medido: dedo a 5 cm del centro de la cara)
                sh_ = max(0.0, ss((k - (t_end + 30)) / 14.0)) * (1 - ss((k - (KW + 56)) / 6.0))
                e("scull_1", 2, 0.62 * math.sin((k - (t_end + 30)) * 0.21) * sh_)                                       # niega con la cabeza: derecha-izquierda (~35 grados)
                e("scull_1", 0, 0.16 * cov)                                                                              # cabeza algo baja
                e("jaw_bot", 0, -0.05 * cov * (0.5 + 0.5 * math.sin((k - t_end) * 0.15)))                               # suspira
                alert = ss((k - (KW + 62)) / 8.0)                                                                       # Alfred se levanto y vuelve a subir: Jerry NO ladra ni habla, solo lo mira subir
                if "alf_xyz" not in SLIP_INFO:
                    Dj_ = json.load(open(os.path.join(BASE, CFG["alfred"]["carpeta"], CFG["alfred"]["nombre"], CFG["alfred"]["nombre"] + ".animacion.json"), encoding="utf-8"))["root"]["canales"]["location"]
                    SLIP_INFO["alf_xyz"] = Dj_
                axyz = SLIP_INFO["alf_xyz"]; kk_ = min(len(axyz[0]), k) - 1
                dxy = math.hypot(axyz[0][kk_] - EDGE_J[0], axyz[1][kk_] - EDGE_J[1]); dzz = EDGE_J[2] + 0.5 - axyz[2][kk_]
                look_dn = math.atan2(dzz, max(dxy, 1.0)) * 0.9                                                        # cabeza hacia abajo siguiendo a Alfred (X+ = abajo): mira mas hacia abajo cuanto mas lejos y bajo esta
                e("scull_1", 0, look_dn * alert * (1 - ss((k - (KJ2 - 2)) / 6.0)))
                for tb, ax, amp in (("tail_1", 2, 0.10), ("tail_2", 2, 0.14), ("tail_3", 2, 0.18)): e(tb, ax, amp * math.sin(k * 0.2) * alert)     # cola quieta, balanceo leve de nerviosismo
                return r
            # Alfred se pone a descansar (kET) y Jerry le habla DE INMEDIATO del refugio: mandibula jaw_bot X hasta -25 grados en cada silaba (ritmo ~7 f), en 3 rafagas durante el descanso (~62 f)
            talk = pulse(k, kET + 2, kET + 62, 4, 4)
            e("scull_1", 2, 8 * math.sin((k - kET) * 0.12) * D2R * talk)                                                     # ya mira a Alfred (el giro lo hace el root): leve vaiven al hablar
            for kk in (kET + 2, kET + 22, kET + 42):
                bur = pulse(k, kk, kk + 18, 3, 4); ph = (k - kk) * 0.9
                e("jaw_bot", 0, -math.radians(25) * bur * (0.5 + 0.5 * math.sin(ph))); e("scull_1", 0, -0.10 * bur * math.sin(ph * 0.5))
            gest = pulse(k, kET + 30, kET + 56, 6, 6); e("scull_1", 2, 0.45 * math.sin((k - kET - 30) * 0.2) * gest)        # mira a los lados (donde levantar el refugio)
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
            if k >= KC: return climb_root(k)[0], climb_root(k)[1]
            if k >= KW: return wake_root(k)
            u = k - t2
            x = LAND[6] + 0.9 * (1 - math.exp(-u / 40.0)); z = 6.907 - 0.25 * pulse(k, t2, t2 + 14, 3, 12) + 0.035 * math.sin(0.12 * u) * ss(u / 20.0)    # entra al agua y flota (eje de la cadera 0.11 m bajo la superficie 7.89)
            return [x, Y_ROLL + 0.05 * math.sin(0.05 * u), z], 180 * D2R


        # ---------------- f1000+: se levanta, ve a los zombies, se asusta (V + ojos grandes, elastico), se gira a la escalera y vuelve a subir (tramo base)
        KSC = KW + 70                                                                      # f1070: reconoce a los zombies

        def wake_pose(k):
            u = k - KW; r = copy.deepcopy(STAND)

            def setb(b, a, deg): r[b]["rotation_euler"][a] = deg * D2R

            def addb(b, a, deg): r[b]["rotation_euler"][a] += deg * D2R
            rise = ss(u / 32.0)
            setb("Hips_alfred", 0, 90.0 * (1 - rise)); setb("Hips_alfred", 2, -2160.0 if u < 34 else 0.0)        # -2160 = 6 vueltas = misma orientacion que 0: sin giro visible al cambiar
            tread = ss((u - 6) / 20.0)                                                      # nada en el sitio (patea y bracea) una vez de pie
            for sd, sg, off in (("Right", 1, 0.0), ("Left", -1, 2.1)):
                setb(f"{sd}UpArm_alfred", 0, 55 + (28 + 14 * math.sin(0.42 * u + off)) * tread); setb(f"{sd}UpArm_alfred", 1, sg * (30 + 8 * math.cos(0.42 * u + off)))
                setb(f"{sd}elbow_alfred", 2, sg * -(18 + 14 * tread * (0.5 + 0.5 * math.sin(0.42 * u + off + 1))))
                setb(f"{sd}UpLeg_alfred", 0, 8 + 20 * tread * math.sin(0.45 * u + off)); setb(f"{sd}knee_alfred", 0, -(12 + 26 * tread * (0.5 + 0.5 * math.sin(0.45 * u + off + 2))))
            setb("Neck_alfred", 0, 28 * (1 - rise))                                         # la cabeza cuelga y se levanta al enderezarse
            for uc in (38, 48):                                                              # tose y escupe agua: cabeza y pecho se encogen
                c_ = epulse(k, KW + uc - 1, KW + uc + 7, 3, 6); addb("Neck_alfred", 0, 22 * c_); addb("Spine_alfred", 0, 12 * c_); addb("Spine1_alfred", 0, 8 * c_)
            srch = pulse(k, KW + 52, KW + 80, 8, 8); setb("Neck_alfred", 1, 48 * math.sin((u - 52) * 0.17) * srch)                # mira a los lados desorientado
            sc_ = epulse(k, KSC, KSC + 28, 10, 14)                                          # SUSTO al ver a los zombies: brazos en V, hacia atras, ojos enormes
            for sd, sg in (("Right", 1), ("Left", -1)):
                setb(f"{sd}UpArm_alfred", 0, (r[f"{sd}UpArm_alfred"]["rotation_euler"][0] / D2R) * (1 - sc_) + (-50 if sd == "Right" else -80) * sc_)
                setb(f"{sd}UpArm_alfred", 1, (r[f"{sd}UpArm_alfred"]["rotation_euler"][1] / D2R) * (1 - sc_) + sg * 8 * sc_)
                setb(f"{sd}elbow_alfred", 2, (r[f"{sd}elbow_alfred"]["rotation_euler"][2] / D2R) * (1 - sc_) + sg * 6 * sc_)
            addb("Hips_alfred", 0, -10 * sc_); addb("Neck_alfred", 0, -8 * sc_)
            return r

        def wake_root(k):
            u = k - KW
            xw0 = -83.0 + 0.9 * (1 - math.exp(-(KW - t2) / 40.0)); yw0 = Y_ROLL + 0.05 * math.sin(0.05 * (KW - t2))
            tz = 6.907 + (6.55 - 6.907) * ss(u / 32.0) + 0.03 * math.sin(0.15 * u) * ss(u / 40.0)                        # de pie nadando: cadera justo bajo la superficie
            tz = tz + (7.0 - tz) * ss((u - 84.0) / 16.0)                                                                  # y se sube al fondo del arranque de la escalera
            tg_ = ss((u - 84.0) / 16.0)
            x = xw0 + (-82.5 - xw0) * tg_; y = yw0 + (-104.5 - yw0) * tg_
            rz = 180 * D2R + (90 * D2R - 180 * D2R) * ss((u - 80.0) / 18.0)                                               # se gira de cara a los zombies a cara a la escalera
            return [x, y, tz], rz

        def climb_root(k):
            if k <= kTop:
                jj = max(1, min(JJ_END, k - KC + 1)); loc = TR.root("location", jj); rot = TR.root("rotation_euler", jj)
                return loc, norm(rot[2])
            u = min(1.0, (k - kTop) / float(Dw)); e_ = ss(u) * 0.3 + u * 0.7                                  # camina sin prisa, arranca y frena suave
            sdist = e_ * cum_a[-1]; q = next((i for i in range(1, len(cum_a)) if cum_a[i] >= sdist), len(cum_a) - 1)
            t = (sdist - cum_a[q - 1]) / max(cum_a[q] - cum_a[q - 1], 1e-9)
            x = pol_a[q - 1][0] + (pol_a[q][0] - pol_a[q - 1][0]) * t; y = pol_a[q - 1][1] + (pol_a[q][1] - pol_a[q - 1][1]) * t
            hd = math.atan2(-(pol_a[q][0] - pol_a[q - 1][0]), (pol_a[q][1] - pol_a[q - 1][1]))
            rz = hd + norm(FACE["alfred"] - hd) * ss((k - (kE - 22)) / 22.0)                                      # al llegar se encara con Jerry
            return [x, y, 14.0 + REST_P["root_dz"] * ss((k - (kE - 6)) / 20.0)], rz

        def climb_row(k):
            jj = max(1, min(JJ_END, k - KC + 1)); r = TR.row(jj)
            if k > kTop:                                                                                         # paso cansado: ciclo de carrera de 11 f a ritmo 0.6
                r = mixrow(r, TR.row(130 + (((k - kTop) * 0.6) % 11.0)), ss((k - kTop) / 6.0))
            return r

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
            elif k >= KW:                                                                      # levantarse / asustarse / volver a subir
                r = wake_pose(k)
                if k >= KC - 6: r = mixrow(r, climb_row(k), ss((k - (KC - 6)) / 8.0))
                if k > kE - 14: r = mixrow(r, land_rest(k), ss((k - (kE - 14)) / 14.0))                 # arriba, agotado: se dobla con las manos en las rodillas y jadea
                return r
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
        e("jaw_bot", 0, 0.0)                                                                                                            # callado: solo mira subir a Alfred
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
            elif name == "jerry" and JC_N < j <= JC_N + 8: rowj = mixrow(jc_pose(JC_N), STAND, ss((j - JC_N) / 8.0))     # al terminar los saltos pasa suave a la pose neutra (las patas delanteras del tramo base no se mueven)
            if name == "jerry" and SLIP and j > JC_N + 8: rowj = copy.deepcopy(STAND)
            if name == "jerry" and SLIP and kEnd < k <= kBack:                                              # espera a Alfred en el borde, mirando la subida: respira agitado, mira hacia abajo y mueve la cola
                rowj = mixrow(STAND, wait_row(k), ss((k - kEnd) / 8.0))
            if name == "jerry" and SLIP and k > kBack:                                                       # corre de vuelta al borde (ciclo de carrera de 12 f a ritmo x1.5)
                rowj = copy.deepcopy(STAND)                                                                    # base NEUTRA (parado): las filas de carrera del tramo base ya no existen (tramo de 122 f) y la ultima quedaba congelada a media zancada
                if k - kBack < 4: rowj = mixrow(TR.row(jmax), rowj, ss((k - kBack) / 4.0))
            b = mixrow(b, rowj, ss((j + 8) / 12.0))
            if name == "jerry" and SLIP:
                if kE - 6 < k <= KJ2: b = mixrow(b, land_rest(k), ss((k - (kE - 6)) / 8.0))
                elif k > kArr2 - 4: b = mixrow(b, land_rest(k), ss((k - (kArr2 - 4)) / 8.0))
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
            if name == "jerry" and SLIP and k > KJ2:                                                         # segunda carrera: del borde a junto de Alfred
                uj = min(1.0, (k - KJ2) / float(Dj2)); ej = ss(uj)
                loc = [EDGE_J[0] + (REST["jerry"][0] - EDGE_J[0]) * ej, EDGE_J[1] + (REST["jerry"][1] - EDGE_J[1]) * ej, 14.0]
                rz = fz_j + norm(hd_j2 - fz_j) * ss((k - KJ2) / 6.0); rz = rz + norm(fz_j2 - rz) * ss((k - (kArr2 - 8)) / 8.0)
                if k > kArr2:                                                                                     # ya en su sitio: se gira a VER VENIR a Alfred (sigue su posicion real con giro limitado) y solo le habla cuando llega
                    if RZ_HOLD_J[0] is None: RZ_HOLD_J[0] = rz
                    tgt = math.atan2(-(ALF_XY[0][k - 1] - loc[0]), (ALF_XY[1][k - 1] - loc[1]))
                    RZ_HOLD_J[0] = RZ_HOLD_J[0] + max(-0.24, min(0.24, 0.4 * norm(tgt - RZ_HOLD_J[0]))); rz = RZ_HOLD_J[0]
            elif name == "jerry" and SLIP and k > kBack:                                                     # vuelta al borde: lineal con arranque/frenada suaves, siempre a z=14
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
    # ------------------------------------------------ NADO DE JERRY: tibia, pie y dedo delanteros acoplados al muslo (el ciclo de la parte 1 solo movia hombro y muslo: la pata parecia un palo)
    if name == "jerry":
        for k in range(1, min(kT, N) + 1):
            for sd in ("R", "L"):
                th = rows[f"front_thigh.{sd}"]["rotation_euler"][k - 1][0]; fl = max(0.0, -th)                      # muslo hacia delante (X negativo) -> la pata se recoge
                for bn, g in ((f"front_shin.{sd}", -2.4), (f"front_foot.{sd}", -1.2), (f"front_toe.{sd}", -0.8)):
                    rows[bn]["rotation_euler"][k - 1] = list(rows[bn]["rotation_euler"][k - 1]); rows[bn]["rotation_euler"][k - 1][0] += g * fl
    # ------------------------------------------------ TROTE DE JERRY (segunda pasada): cuando se desplaza (>0.02 m/f) tras el tramo de subida, patas, columna, cabeza, cola y orejas
    # siguen un trote diagonal; la fase avanza con la distancia recorrida (zancada de 1.5 m), asi que arranca, acelera y frena con el movimiento real.
    if name == "jerry" and SLIP:
        ph_g = 0.0; spds = []
        for k in range(1, N + 1):
            sp = math.dist(rloc[k - 1], rloc[k - 2]) if k > 1 else 0.0
            spds.append(sp)
        for k in range(1, N + 1):
            sp = sum(spds[max(0, k - 3):k]) / len(spds[max(0, k - 3):k]); ph_g += 2 * math.pi * sp / 1.9
            if k <= kT + JC_N - 1: continue                                              # los 7 saltos de subida ya tienen su propia animacion
            w = ss((sp - 0.004) / 0.03)
            if w <= 0.001: continue
            a = min(1.3, 0.65 + sp / 0.1); ph = ph_g

            def addj(bn, ax, deg):
                rows[bn]["rotation_euler"][k - 1][ax] += deg * D2R * w if isinstance(rows[bn]["rotation_euler"][k - 1], list) else 0.0

            for bn in bones:
                rows[bn]["rotation_euler"][k - 1] = list(rows[bn]["rotation_euler"][k - 1])                         # copia propia (las filas pueden compartir objetos entre frames)
            for sd, off in (("R", 0.0), ("L", math.pi)):                                   # diagonal: trasera D con delantera I
                addj(f"thigh.{sd}", 0, 38 * a * math.sin(ph + off)); addj(f"shin.{sd}", 0, -34 * a * max(0.0, math.sin(ph + off + 0.5))); addj(f"foot.{sd}", 0, -10 * a * max(0.0, math.sin(ph + off + 0.5)))      # trasera: al adelantarse la pata la tibia y el pie se pliegan HACIA ATRAS (X negativo)      # en el vuelo (pata adelantandose) la tibia y el pie se recogen y la punta sube
                fo = off + math.pi                                                         # la delantera del mismo lado va en contrafase
                addj(f"front_thigh.{sd}", 0, -36 * a * math.sin(ph + off)); addj(f"front_shin.{sd}", 0, -32 * a * (0.5 + 0.5 * math.sin(ph + off + 0.5)))
                addj(f"front_shoulder.{sd}", 0, 16 * a * math.sin(ph + off + 0.6)); addj(f"front_foot.{sd}", 0, -18 * a * max(0.0, math.sin(ph + off + 0.5))); addj(f"front_toe.{sd}", 0, -12 * a * max(0.0, math.sin(ph + off + 0.8))); addj(f"toe.{sd}", 0, -10 * a * max(0.0, math.sin(ph + off + 0.8)))      # delantera: pie y dedo hacia atras (X negativo; la tibia ya pliega atras con X positivo); addj(f"ear.{sd}", 0, 5 * a * math.sin(2 * ph + 2.0 + off))
            addj("spine_6", 0, 3 * a * math.sin(2 * ph + 0.4)); addj("spine_4", 0, -2.5 * a * math.sin(2 * ph + 0.4)); addj("scull_1", 0, 2.5 * a * math.sin(2 * ph + 1.2))
            addj("tail_1", 0, -8); addj("tail_1", 2, 10 * a * math.sin(ph)); addj("tail_2", 2, 12 * a * math.sin(ph - 0.5)); addj("tail_3", 2, 14 * a * math.sin(ph - 1.0))
    # ------------------------------------------------ GIRO DE JERRY hacia Alfred (rapido y animado): la cabeza se adelanta, el torso se tuerce, las patas dan pasitos de pivote y la cola acompana
    if name == "jerry" and SLIP:
        cum_t = 0.0
        for k in range(kArr2 + 1, N + 1):
            wv = norm(rrot[k - 1][2] - rrot[k - 2][2]); cum_t += abs(wv)
            tgt = math.atan2(-(ALF_XY[0][k - 1] - rloc[k - 1][0]), (ALF_XY[1][k - 1] - rloc[k - 1][1])); err = norm(tgt - rrot[k - 1][2])
            wt = ss((abs(wv) - 0.01) / 0.05)                                            # 0 si solo sigue con calma, 1 en un giro franco
            for bn in bones: rows[bn]["rotation_euler"][k - 1] = list(rows[bn]["rotation_euler"][k - 1])

            def addr(bn, ax, rad):
                rows[bn]["rotation_euler"][k - 1][ax] += rad

            lead = max(-1.0, min(1.0, err * 1.6))                                       # cabeza por delante del cuerpo: gira primero (Z derecha +, el giro a la izquierda es rz +)
            addr("scull_1", 2, -0.55 * lead); addr("spine_6", 2, -0.22 * lead); addr("spine_4", 2, -0.14 * lead); addr("spine_2", 2, -0.08 * lead)
            addr("scull_1", 0, 0.05 * wt); addr("tail_1", 2, -0.5 * wv * 4); addr("tail_2", 2, -0.7 * wv * 4); addr("tail_3", 2, -0.9 * wv * 4)     # la cola se va hacia el lado contrario del giro
            if wt > 0.001:
                ph = cum_t * 2 * math.pi / 1.1
                for sd, off in (("R", 0.0), ("L", math.pi)):                              # pasitos en el sitio, diagonales
                    fl = max(0.0, math.sin(ph + off + 0.5))
                    addr(f"thigh.{sd}", 0, 0.55 * wt * math.sin(ph + off)); addr(f"shin.{sd}", 0, -0.5 * wt * fl); addr(f"foot.{sd}", 0, -0.15 * wt * fl)
                    addr(f"front_thigh.{sd}", 0, -0.5 * wt * math.sin(ph + off)); addr(f"front_shin.{sd}", 0, -0.45 * wt * (0.5 + 0.5 * math.sin(ph + off + 0.5)))
                    addr(f"front_foot.{sd}", 0, -0.25 * wt * fl); addr(f"front_toe.{sd}", 0, -0.15 * wt * fl)
                addr("spine_6", 0, 0.04 * wt); addr("spine_4", 0, -0.03 * wt)
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
        if name == "alfred" and SLIP and "scale" in o["canales"]:        # ojos muy abiertos al resbalar y al ver a los zombies (elastico)
            wi = [epulse(k_, SL["kS"] - 8, SL["kS"] + 16, 8, 8) + epulse(k_, KW + 66, KW + 100, 10, 14) for k_ in range(1, N + 1)]
            o["canales"]["scale"][0] = [round(v_ * (1 + 0.35 * w_), 5) for v_, w_ in zip(o["canales"]["scale"][0], wi)]
            o["canales"]["scale"][2] = [round(v_ * (1 + 0.30 * w_), 5) for v_, w_ in zip(o["canales"]["scale"][2], wi)]
        if name == "alfred" and SLIP:                                   # ojos cerrados al caer rodando y mientras flota
            if "Closed" in o["shape_keys"]:
                o["shape_keys"]["Closed"] = [round((max(c_, ss((k_ - (SL["t1"] + 2)) / 6.0)) if k_ < KW else max(ss((k_ - (SL["t1"] + 2)) / 6.0) * (1 - ss((k_ - (KW + 4)) / 10.0)), min(1.0, sum(pulse(k_, b0, b0 + 5, 2, 2) for b0 in (1052, 1135, 1188, 1252))))), 5) for k_, c_ in zip(range(1, N + 1), o["shape_keys"]["Closed"])]      # cerrados al caer/flotar; abiertos al levantarse (con algun parpadeo)
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
