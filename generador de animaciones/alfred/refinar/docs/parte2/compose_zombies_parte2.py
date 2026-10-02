"""Parte 2 de los zombies 1-5 (v2): siguen a Alfred y Jerry por el canal (vadeando por el lecho, z 7) y se van acercando mientras los dos
discuten parados en (-84.5,-120.3); hacia el frame 540 (Alfred y Jerry ya los vieron y huyen) aceleran y cortan en diagonal hacia el
pie de la escalera oriental (-82.5,-104.5) para subirla en fila detras de ellos. Solo Python estandar.
Uso (desde 'generador de animaciones'):  python alfred/refinar/docs/parte2/compose_zombies_parte2.py
Entradas: artefactos de la parte 1 (ultimo frame = estado inicial), `estilos_zombie2.json` (caminata NORMAL), `grilla_p2.json` (alturas).
Salida: zombie_N/refinar/animaciones_ia/parte2_zombie_N_sigue/*.animacion.json  (N=1600 frames, igual que Alfred/Jerry).
"""
import ast, copy, json, math, os

BASE = "generador de animaciones" if os.path.isdir("generador de animaciones") else "."
HERE = os.path.join(BASE, "alfred/refinar/docs/parte2")
N = 2150                                    # duracion de la parte 2 con el refugio (igual en compose_refugio_parte2.py); orden: compose_zombies -> compose_refugio
GRID = json.load(open(os.path.join(HERE, "grilla_p2.json")))
STY = json.load(open(os.path.join(BASE, "alfred/refinar/docs/datos_zombies/estilos_zombie2.json")))["NORMAL"]


def ss(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def val(ch, i):
    return ch[i] if isinstance(ch, list) else ch


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def height(x, y):
    g = GRID.get(f"{math.floor(x)},{math.floor(y)}")
    if g is None or g[0] is None: return 7.0
    if g[1] is not None and g[0] < g[1]: return 7.0            # agua: caminan sobre el lecho (los huecos del lecho no se siguen)
    return g[0]


P0 = (-82.5, -104.5)
STAIRS = [(-83.5, -104.5), (-84.5, -104.5), (-85.5, -104.5), (-86.5, -104.5), (-87.5, -104.5), (-88.5, -104.5), (-89.5, -104.5), (-91.5, -104.5), (-93.5, -103.8), (-96.0, -103.0)]
HOLD_X = -90.0            # hasta donde llega el primero mientras Alfred y Jerry discuten
# (velocidad de vadeo m/frame antes de cazar, carril y)
ZOM = {1: (0.033, -120.2), 2: (0.032, -119.6), 3: (0.031, -120.9), 5: (0.030, -119.9), 4: (0.029, -121.4)}   # velocidad CONSTANTE de cada zombie durante toda la parte 2
ORDEN = [1, 2, 3, 5, 4]


def _kf_salto():
    """KEYFRAMES_SALTAR_SUBIR (animacion base del zombie, 12 frames) leidos del generador de slots sin importarlo."""
    src = open(os.path.join(BASE, "zombie_1/refinar/zombie_1_animation_studio/generate_slots_zombie_1.py"), encoding="utf-8").read()
    for nd in ast.parse(src).body:
        if isinstance(nd, ast.Assign) and getattr(nd.targets[0], "id", "") == "KEYFRAMES_SALTAR_SUBIR": return ast.literal_eval(nd.value)


KFJ = _kf_salto(); JF = 20; JLEAD = 0.45; LAND = 2.2            # el salto base (12 f) se estira a 20 f; en el agua cada uno va a su velocidad constante y al salir a tierra ACELERAN (x2.2); despega 0.45 m antes del borde y cae 0.45 m despues
SUBE_Y = {1: (-103.6, -105.8), 2: (-107.0, -107.0), 3: (-105.2, -108.2), 5: (-106.2, -109.0), 4: (-104.0, -109.0)}   # (y al pie, y arriba): cada uno sube en DIAGONAL distinta (se cruzan, ya no van en fila ni en paralelo)
# Los zombies NUNCA se detienen: tras salir del agua (aceleran x2.2) suben la escalera con el salto base y llegan al refugio (que ocupa x -98..-94, y -111..-107); al llegar siguen caminando
# en un anillo alrededor de los muros (sentido antihorario) hasta el ultimo frame. Para que lleguen mientras Alfred construye (f1452-f1919) NO se paran: dan un rodeo mas largo por el agua (zigzag
# `w` calculado por biseccion para que cada uno llegue al anillo en su frame ENTRY_F).
ENTRY_F = {1: 1570, 2: 1640, 3: 1700, 5: 1750, 4: 1912}
RING = {1: 1.4, 3: 1.4, 4: 1.4, 2: 1.85, 5: 1.85}                    # distancia del anillo a los muros (dos anillos para que no se pisen)
ENTRY_Y = {1: -105.8, 2: -107.0, 3: -108.2, 5: -109.4, 4: -110.6}  # donde cada uno entra al anillo (lado este)
ZIGX = {1: -81.5, 2: -82.5, 3: -82.5, 5: -82.5, 4: -82.5}                      # columna base del zigzag (z5 mas al este para no cruzarse con z4)
ZIGN = {1: 4, 2: 4, 3: 4, 5: 8, 4: 8}                              # cruces del zigzag por el agua (distintos por zombie para que no se pisen)
GAP = 1.4
# --- EMPUJON DE JERRY: cuando un zombie entra al anillo (se acerca demasiado al refugio) Jerry salta y lo empuja de frente: cae boca arriba (Hips X -90), queda tendido y se levanta
KH_AFTER = {1: 12, 2: 12, 3: 12, 5: 12, 4: 12}   # el empujon llega estos frames despues de entrar al anillo; todos se empujan en el lado ESTE (hacia el este hay meseta firme) en alturas distintas, de norte a sur en orden de llegada
# CADA zombie cae distinto (medido en Blender que NO atraviesa el suelo: piernas/rodillas solo SUBEN (UpLeg X+, knee X+), splay por UpLeg Z, brazos por X/Y, cuello Y):
#   fall = frames de la caida, bnc = amplitud del rebote, nb = rebotes, lie = frames tendido, rise = frames al levantarse, knock = m lanzado, yaw = giro de la direccion de caida respecto al empujon (rad),
#   arm = (amplitud X, amplitud Y, frecuencia, fase) del manoteo, legup = (UpLeg X der, izq), splay = (UpLeg Z der, izq), knee = (rodilla der, izq) (X+ sube la pantorrilla), neck = giro del cuello Y, wig = pataleo de piernas
FALLV = {
    1: dict(fall=14, bnc=0.05, nb=1, lie=40, rise=30, knock=1.20, yaw=0.0, arm=(0.12, 0.18, 0.17, 0.0), legup=(0.0, 0.0), splay=(0.0, 0.0), knee=(0.0, 0.0), neck=0.0, wig=0.0),
    2: dict(fall=18, bnc=0.08, nb=2, lie=46, rise=34, knock=1.50, yaw=-0.5, arm=(0.35, 0.40, 0.25, 1.0), legup=(0.5, 0.1), splay=(0.0, 0.2), knee=(0.6, 0.1), neck=0.5, wig=0.0),
    3: dict(fall=11, bnc=0.03, nb=1, lie=36, rise=26, knock=0.95, yaw=0.45, arm=(0.05, 0.06, 0.10, 2.0), legup=(0.0, 0.0), splay=(-0.45, 0.45), knee=(0.3, 0.3), neck=-0.4, wig=0.0),
    5: dict(fall=16, bnc=0.06, nb=3, lie=34, rise=28, knock=1.35, yaw=-0.3, arm=(0.30, 0.30, 0.22, 3.0), legup=(0.0, 0.7), splay=(-0.3, 0.0), knee=(0.0, 0.8), neck=0.3, wig=0.0),
    4: dict(fall=13, bnc=0.07, nb=1, lie=42, rise=36, knock=1.10, yaw=-0.25, arm=(0.25, 0.25, 0.30, 4.0), legup=(0.35, 0.35), splay=(0.0, 0.0), knee=(0.45, 0.45), neck=-0.6, wig=0.25),
}
# altura del punto mas bajo del cuerpo sobre el root (medido en Blender, malla evaluada, pose de caida: todos los huesos a 0 salvo Hips X=-90*lam y Neck X=-0.3*lam), lam = 0..1 en pasos de 0.1
LIE_TAB = [0.0, -0.012, -0.002, 0.03, 0.082, 0.154, 0.243, 0.347, 0.465, 0.592, 0.467]


def lie_dz(lam):
    x = max(0.0, min(1.0, lam)) * 10; i = min(9, int(x)); w = x - i; return -max(0.0, LIE_TAB[i] + (LIE_TAB[i + 1] - LIE_TAB[i]) * w)    # baja el root justo lo necesario para que nada atraviese el suelo
SHELTER = (-98.0, -94.0, -111.0, -107.0)     # x0, x1, y0, y1 del refugio


def knock_dir(x, y):
    x0, x1, y0, y1 = SHELTER; cx, cy = min(max(x, x0), x1), min(max(y, y0), y1); dx, dy = x - cx, y - cy; L = math.hypot(dx, dy) or 1.0
    return dx / L, dy / L


def idx_map(k, kh, FREEZE):
    """indice (float) del perfil base que corresponde al frame k: frena 10 f antes del golpe, queda congelado FREEZE f y sigue."""
    if k < kh - 10: return float(k)
    if k < kh: u = (k - (kh - 10)) / 10.0; return (kh - 10) + 10 * (u - u * u / 2)
    if k < kh + FREEZE: return float(kh - 5)
    return float(k - FREEZE + (kh - 5) - kh)                                  # tras congelarse sigue desde donde se quedo


def resample(pts, ds=0.1):
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a, b); n = max(1, int(L / ds))
        for i in range(1, n + 1):
            out.append((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n))
    return out


def load(n):
    return json.load(open(os.path.join(BASE, f"zombie_{n}/refinar/animaciones_ia/zombie_{n}_camina_acantilado/zombie_{n}_camina_acantilado.animacion.json"), encoding="utf-8"))


def last_row(D):
    i = D["frame_fin"] - 1
    return {b: {p: [val(a, i) for a in pr[p]] for p in pr} for b, pr in D["armature"]["bones"].items()}


def gait_row(zn, bones, phase):
    idx = 20 + (phase % 20.0); i0 = int(math.floor(idx)); w = idx - i0; out = {}
    for b in bones:
        key = b.replace(f"_zombie_{zn}", "_zombie_2") if f"_zombie_{zn}" in b else b
        if key in STY:
            r0 = STY[key][i0]; r1 = STY[key][i0 + 1]; out[b] = [r0[a] + (r1[a] - r0[a]) * w for a in range(3)]
    return out


# Los zombies que ya no pueden entrar (los empuja Jerry) rodean el refugio hasta un muro distinto y lo ATACAN sin parar (golpean con las manos / saltan a trepar y resbalan), de cara a la pared
# y a ~0.8 m del plano del muro (z1, el del muro sur, a 0.86 porque al saltar se inclina hacia el muro) (el brazo mide 0.76 m: las manos tocan la pared al golpear). (x, y), rz de frente al muro (adelante = (-sin rz, cos rz))
SPOT = {1: ((-96.0, -111.86), 0.0), 2: ((-98.8, -109.0), -math.pi / 2), 3: ((-96.5, -106.2), math.pi), 5: ((-93.2, -108.5), math.pi / 2), 4: ((-93.2, -109.6), math.pi / 2)}
WAYS = {1: [(-93.3, -107.5), (-93.3, -111.3)], 2: [(-93.0, -105.9), (-99.4, -105.9), (-99.5, -108.0)], 3: [(-93.0, -105.9)], 5: [], 4: []}      # rutas distintas por la meseta, por fuera del refugio (evitan el hueco (-96,-105))
# (kind, frames): 'hit' = puñetazos alternos (periodo 26 f), 'climb' = agacharse, saltar contra el muro, agarrarse, resbalar y recuperar (70 f); el patron se repite
ATK = {1: [("climb", 70), ("hit", 52), ("climb", 70)], 2: [("hit", 52), ("hit", 52), ("climb", 70)], 3: [("hit", 78), ("climb", 70)], 5: [("climb", 70), ("climb", 70), ("hit", 52)], 4: [("hit", 52), ("climb", 70), ("hit", 26)]}


def ring_route(n, y0):
    """entrada (lado este) + rodeo hasta el muro que le toca."""
    d = RING[n]; return [(-94 + d, y0)] + WAYS[n] + [SPOT[n][0]]


def atk_pose(n, k, ka):
    """(ajustes aditivos por hueso en rad, dz de la raiz, (u, peso) del salto base o None) del ataque al muro en el frame k, tras llegar en ka."""
    if k < ka: return {}, 0.0, None
    pat = ATK[n]; tot = sum(l for _, l in pat); t = (k - ka) % tot; kind = None; tl = 0
    for kd, l in pat:
        if t < l: kind = kd; tl = t; break
        t -= l
    add = {}; dz = 0.0; jmp = None
    if kind == "hit":
        P = 26.0; lean = 0.0
        for side, off in (("Right", 0.0), ("Left", 13.0)):
            p = ((tl - off) % P) / P
            r = ss(p / 0.5) if p < 0.5 else (1 - ss((p - 0.5) / 0.1) if p < 0.6 else 0.0)
            imp = ss((p - 0.5) / 0.04) * (1 - ss((p - 0.6) / 0.15)) if 0.5 <= p < 0.75 else 0.0
            add[side + "UpArm"] = [-0.95 * r + 0.30 * imp, 0.0, 0.0]; lean = max(lean, imp)
        add["Hips"] = [0.18 * lean, 0.0, 0.06 * math.sin(tl * 0.25)]; add["Spine"] = [0.12 * lean, 0.0, 0.0]; add["Neck"] = [0.20 * lean + 0.08 * math.sin(tl * 0.3), 0.0, 0.0]
        add["RightUpLeg"] = [0.08 * math.sin(tl * 0.5), 0.0, 0.0]; add["LeftUpLeg"] = [-0.08 * math.sin(tl * 0.5), 0.0, 0.0]
    else:
        c = ss(tl / 10.0) * (1 - ss((tl - 10) / 3.0)); au = ss((tl - 12) / 6.0) * (1 - ss((tl - 44) / 10.0)); cl = ss((tl - 24) / 3.0) * (1 - ss((tl - 38) / 4.0))
        add["Hips"] = [0.18 * c + 0.12 * au, 0.0, 0.0]; add["Neck"] = [0.0, 0.0, 0.35 * math.sin(tl * 0.6) * ss((tl - 38) / 4.0) * (1 - ss((tl - 56) / 10.0))]
        for side in ("Right", "Left"):
            add[side + "UpArm"] = [0.2 * c - 1.15 * au, 0.0, 0.0]; add[side + "knee"] = [-0.6 * c, 0.0, 0.0]
        add["RightUpLeg"] = [0.5 * c + 0.5 * math.sin(tl * 0.9) * cl, 0.0, 0.0]; add["LeftUpLeg"] = [0.5 * c + 0.5 * math.sin(tl * 0.9 + math.pi) * cl, 0.0, 0.0]
        if 10 <= tl < 24: dz = 0.55 * ss((tl - 10) / 13.0)
        elif 24 <= tl < 38: dz = 0.55 * (1 - ss((tl - 24) / 14.0))
        jw_ = ss(min(1.0, (tl - 8) / 4.0)) * (1 - ss((tl - 23) / 4.0))
        if jw_ > 0.001: jmp = (min(1.0, max(0.0, (tl - 10) / 13.0)), jw_)
    return add, dz, jmp


def make_route(n, st, lane, w):
    sy, sy2 = SUBE_Y[n]; ring = ring_route(n, ENTRY_Y[n])
    ZIG = ZIGN[n]; zig = [(ZIGX[n] + (w if i % 2 else 0.0), -117.5 + (sy + 117.5) * i / ZIG) for i in range(ZIG + 1)]
    pts = resample([st, (-97.0, lane), (HOLD_X, lane), (-84.0, -119.6)] + zig + [(-83.5, sy), (-89.5, sy2), (-91.5, sy2)] + ring)
    cum = [0.0]
    for a_, b_ in zip(pts, pts[1:]): cum.append(cum[-1] + math.dist(a_, b_))
    return pts, cum, ring[0]


def profile(n, pts, cum):
    """S (distancia recorrida por frame), V, ventanas de salto (jw) y alturas de salto (jz). Velocidad constante en el agua, x LAND en tierra; sin pausas."""
    def pos_s(s_):
        s_ = min(max(s_, 0.0), cum[-1] - 1e-6); j_ = max(1, next((q for q in range(1, len(cum)) if cum[q] >= s_), len(cum) - 1)); t_ = (s_ - cum[j_ - 1]) / max(cum[j_] - cum[j_ - 1], 1e-9)
        return pts[j_ - 1][0] + (pts[j_][0] - pts[j_ - 1][0]) * t_, pts[j_ - 1][1] + (pts[j_][1] - pts[j_ - 1][1]) * t_

    edges = []
    for i_ in range(len(pts) - 1):
        h0_, h1_ = min(height(*pts[i_]), 14.0), min(height(pts[i_ + 1][0], pts[i_ + 1][1]), 14.0)
        if h1_ - h0_ > 0.3 and h0_ >= 6.9: edges.append(cum[i_] - JLEAD)
    s_land = next(c for p_, c in zip(pts, cum) if min(height(p_[0], p_[1]), 14.0) > 7.6)
    S = [0.0] * N; V = [0.0] * N; jw = [0] * N; jz = [None] * N; ej = list(edges); kk = 1
    while kk < N:
        if ej and S[kk - 1] >= ej[0] and kk + JF < N:
            ej.pop(0); sj = S[kk - 1]; L_ = 2 * JLEAD
            h0_ = min(height(*pos_s(sj)), 14.0); h1_ = min(height(*pos_s(sj + L_)), 14.0)          # alturas reales bajo el despegue y el aterrizaje
            if h1_ - h0_ < 0.3 or h0_ < 6.9: continue
            for q in range(JF):                                                                    # horizontal ease-in, vertical ease-out (como el slot base)
                t = (q + 1) / JF; S[kk + q] = sj + L_ * t * t; V[kk + q] = S[kk + q] - S[kk + q - 1]
                jw[kk + q] = q + 1; jz[kk + q] = h0_ + (h1_ - h0_) * (1 - (1 - t) * (1 - t))
            kk += JF
        else:
            vv_ = ZOM[n][0] * (LAND if S[kk - 1] >= s_land else 1.0); S[kk] = S[kk - 1] + vv_; V[kk] = vv_; kk += 1
    for kk in range(1, N):
        S[kk] = min(S[kk], cum[-1]); V[kk] = S[kk] - S[kk - 1]
    return S, V, jw, jz


def entry_frame(S, cum_entry):
    return next((k for k in range(N) if S[k] >= cum_entry), N)


def main():
    data = {n: load(n) for n in ZOM}
    PROF = {}
    for n, (v, lane) in ZOM.items():
        D = data[n]; i = D["frame_fin"] - 1
        st = (val(D["root"]["canales"]["location"][0], i), val(D["root"]["canales"]["location"][1], i))
        lo, hi = 0.0, 7.0
        for _ in range(16):                                                                         # biseccion de la amplitud del zigzag: llega al anillo en ENTRY_F[n]
            w = (lo + hi) / 2; pts, cum, e0 = make_route(n, st, lane, w); cum_e = cum[min(range(len(pts)), key=lambda j: math.dist(pts[j], e0))]
            S, V, jw, jz = profile(n, pts, cum)
            if entry_frame(S, cum_e) < ENTRY_F[n]: lo = w
            else: hi = w
        PROF[n] = (pts, cum, S, V, jw, jz, w, entry_frame(S, cum_e))
        print(f"zombie_{n}: zigzag w={w:.2f} m, llega al anillo en f{PROF[n][7]} (objetivo f{ENTRY_F[n]})")
    S = {n: PROF[n][2] for n in ZOM}; V = {n: PROF[n][3] for n in ZOM}; EVT = {}
    for n in ZOM:
        D = data[n]; pts, cum = PROF[n][0], PROF[n][1]; jw, jz = PROF[n][4], PROF[n][5]; bones = list(D["armature"]["bones"]); start = last_row(D)
        Lr = D["root"]["canales"]["location"]; Rr = D["root"]["canales"]["rotation_euler"]
        rz_prev = val(Rr[2], D["frame_fin"] - 1); z0 = val(Lr[2], D["frame_fin"] - 1)
        # --- empujon de Jerry: perfil de avance remapeado (frena, queda congelado mientras cae/yace/se levanta, sigue)
        Sb, jwb, jzb = S[n], jw, jz; ke = PROF[n][7]; kh = ke + KH_AFTER[n]; kb = kh - 5

        def interp(arr, f_):
            i0 = int(math.floor(f_)); w_ = f_ - i0; a_ = arr[min(i0, N - 1)]; return a_ + (arr[min(i0 + 1, N - 1)] - a_) * w_

        fv = FALLV[n]; FALL_F = fv["fall"]; FREEZE = FALL_F + 8 + fv["lie"] + fv["rise"]; RISE_F = fv["rise"]; BOUNCE_F = 8 * fv["nb"] if False else 8
        idxs = [idx_map(k, kh, FREEZE) for k in range(N)]
        Sn = [interp(Sb, f_) for f_ in idxs]; Vn = [0.0] + [Sn[k] - Sn[k - 1] for k in range(1, N)]
        jw = [0 if kh <= k < kh + FREEZE else jwb[min(N - 1, int(round(f_)))] for k, f_ in enumerate(idxs)]
        jz = [jzb[min(N - 1, int(round(f_)))] if jw[k] else None for k, f_ in enumerate(idxs)]
        S[n] = Sn; V[n] = Vn; ka = next((k for k in range(N) if Sn[k] >= cum[-1] - 0.02), N - 1)                  # llega a su muro

        def pos_at(s):
            s = min(s, cum[-1] - 1e-6)
            j = max(1, next((q for q in range(1, len(cum)) if cum[q] >= s), len(cum) - 1)); t = (s - cum[j - 1]) / max(cum[j] - cum[j - 1], 1e-9)
            return (pts[j - 1][0] + (pts[j][0] - pts[j - 1][0]) * t, pts[j - 1][1] + (pts[j][1] - pts[j - 1][1]) * t)

        xs, ys = [], []
        for k in range(N):
            x, y = pos_at(S[n][k]); xs.append(x); ys.append(y)
        px, py = pos_at(Sb[kb]); nx_, ny_ = knock_dir(px, py); qx, qy = pos_at(Sb[kb + 2]); rx_, ry_ = pos_at(Sb[kb - 2]); tl_ = math.hypot(qx - rx_, qy - ry_) or 1.0
        cy_, sy_ = math.cos(fv["yaw"]), math.sin(fv["yaw"]); kx_, ky_ = nx_ * cy_ - ny_ * sy_, nx_ * sy_ + ny_ * cy_                    # direccion en la que cae (la del empujon girada fv["yaw"])
        EVT[n] = {"z": n, "llegada": ka + 1, "frame_golpe": kh + 1, "frame_libre": kh + FREEZE + 1, "cae": [round(kx_, 4), round(ky_, 4)], "pos": [round(px, 3), round(py, 3)], "n": [round(nx_, 4), round(ny_, 4)], "t": [round((qx - rx_) / tl_, 4), round((qy - ry_) / tl_, 4)], "anillo": RING[n]}
        lam = [0.0] * N; ek = [0.0] * N
        for k in range(N):                                                                  # lam: 0 de pie, 1 tendido boca arriba (Hips X -90 * lam)
            if k < kh: continue
            if k < kh + FALL_F: t_ = (k - kh) / float(FALL_F); lam[k] = ss(t_); ek[k] = 1 - (1 - t_) * (1 - t_)
            elif k < kh + FALL_F + BOUNCE_F: u_ = (k - (kh + FALL_F)) / float(BOUNCE_F); lam[k] = 1.0 - fv["bnc"] * abs(math.sin(u_ * fv["nb"] * math.pi * 2 / 2.0 * 2)) * (1 - u_); ek[k] = 1.0     # rebote solo hacia arriba (si pasara de 90 grados las piernas se hundirian)
            elif k < kh + FREEZE - RISE_F: lam[k] = 1.0 - 0.012 * (0.5 + 0.5 * math.sin(k * 0.2)); ek[k] = 1.0
            elif k < kh + FREEZE: lam[k] = 1.0 - ss((k - (kh + FREEZE - RISE_F)) / float(RISE_F)); ek[k] = 1.0
            else: ek[k] = 1.0 - ss((k - (kh + FREEZE)) / 40.0)                             # al levantarse vuelve caminando a su ruta
        for k in range(N): xs[k] += kx_ * fv["knock"] * ek[k]; ys[k] += ky_ * fv["knock"] * ek[k]
        hs = [min(height(xs[k], ys[k]), 14.0) if jz[k] is None else jz[k] for k in range(N)]
        for k in range(1, N):                                                               # bajar un desnivel (anillo) lleva ~11 f, no cae de golpe
            if jz[k] is None and hs[k] < hs[k - 1] - 0.09: hs[k] = hs[k - 1] - 0.09
            if jz[k] is None and hs[k] > hs[k - 1] + 0.25: hs[k] = hs[k - 1] + 0.25               # subidas bruscas sin salto (bultos estrechos del terreno): maximo 0.25 m/f
        ph_b = {1: 0.0, 2: 1.3, 3: 2.6, 5: 3.9, 4: 5.2}[n]                                    # fase de flotacion distinta por zombie
        wat = [1.0 - ss((h - 7.3) / 1.2) for h in hs]                                         # 1 en el agua, 0 en tierra/escalera
        zs = []
        for k in range(N):
            bob = 0.055 * math.sin(k * 2 * math.pi / 52.0 + ph_b) + 0.02 * math.sin(k * 2 * math.pi / 19.0 + 2 * ph_b)
            zs.append(max(hs[k], 7.0 + (0.22 + bob) * wat[k]) if wat[k] > 0 else hs[k])       # flotan: cadera un poco sobre la superficie y suben/bajan con el oleaje
        rz = [rz_prev]; last_h = rz_prev
        for k in range(1, N):
            a, b = max(0, k - 5), min(N - 1, k + 5); vx, vy = xs[b] - xs[a], ys[b] - ys[a]
            if math.hypot(vx, vy) > 0.02: last_h = math.atan2(-vx, vy)
            rz.append(rz[-1] + max(-0.05, min(0.05, wrap(last_h - rz[-1]))))
        ATKS = [atk_pose(n, k, ka) for k in range(N)]
        zs = [zs[k] + (z0 - zs[0]) * (1 - ss(k / 30.0)) + lie_dz(lam[k]) + ATKS[k][1] * ss((k - ka) / 10.0) for k in range(N)]
        face = math.atan2(nx_, -ny_); face_f = math.atan2(kx_, -ky_)                          # primero se gira a mirar a Jerry; al caer rota hasta quedar cayendo en la direccion propia de este zombie
        for k in range(N):
            wf = ss((k - (kh - 12)) / 10.0) * (1 - ss((k - (kh + FREEZE - 6)) / 16.0)); fa = face + wrap(face_f - face) * ss((k - kh) / float(FALL_F))
            rz[k] = rz[k] + wrap(fa - rz[k]) * wf
        for k in range(1, N): rz[k] = rz[k - 1] + wrap(rz[k] - rz[k - 1])
        for k in range(N):                                                                  # al llegar al muro se pone de frente a el
            wsp = ss((k - (ka - 16)) / 16.0)
            if wsp > 0: rz[k] = rz[k] + wrap(SPOT[n][1] - rz[k]) * wsp
        for k in range(1, N): rz[k] = rz[k - 1] + wrap(rz[k] - rz[k - 1])
        rows = {b: [None] * N for b in bones}; ph = 0.0
        for k in range(N):
            ph += V[n][k] / 0.085
            gw = ss(k / 12.0) * min(1.0, V[n][k] / 0.004); g = gait_row(n, bones, ph)
            if jw[k]: gw = 0.0                                                              # en el salto manda la animacion base
            w_ = wat[k]; t_ = k * 2 * math.pi / 52.0 + ph_b; t2 = k * 2 * math.pi / 34.0 + ph_b * 1.7
            for b in bones:
                base = start[b]["rotation_euler"]
                r_ = [base[a] + (g[b][a] - base[a]) * gw for a in range(3)] if b in g else list(base)
                short = b.replace(f"_zombie_{n}", "")
                if w_ > 0.01:                                                                   # en el agua: cabeceo/balanceo del oleaje y brazos/pierna que chapotean
                    if short == "Hips": r_[0] += 0.07 * math.sin(t_) * w_; r_[2] += 0.06 * math.sin(t_ * 0.8 + 1.0) * w_
                    elif short in ("Spine", "Spine1"): r_[0] += 0.05 * math.sin(t_ + 0.6) * w_; r_[2] += 0.04 * math.sin(t2) * w_
                    elif short == "Neck": r_[0] += 0.05 * math.sin(t_ + 1.4) * w_; r_[2] += 0.07 * math.sin(t2 + 0.5) * w_
                    elif short == "RightUpArm": r_[0] += 0.16 * math.sin(t2) * w_; r_[1] += 0.12 * math.sin(t2 + 0.9) * w_
                    elif short == "LeftUpArm": r_[0] += 0.16 * math.sin(t2 + 2.1) * w_; r_[1] -= 0.12 * math.sin(t2 + 3.0) * w_
                    elif short in ("Rightelbow", "Leftelbow"): r_[2] += (0.16 if short == "Leftelbow" else -0.16) * (0.5 + 0.5 * math.sin(t2 + 1.2)) * w_
                    elif short in ("RightUpLeg", "LeftUpLeg"): r_[0] += 0.10 * math.sin(t_ * 1.6 + (0 if short[0] == "R" else math.pi)) * w_
                if jw[k] or (k + 1 < N and jw[k + 1]) or (k > 0 and jw[k - 1] == JF):         # salto base: 12 keyframes de huesos, entrando y saliendo en 1 frame de mezcla
                    kb_ = b.replace(f"_zombie_{n}", "_zombie_1")
                    if kb_ in KFJ:
                        q_ = jw[k] - 1 if jw[k] else (JF - 1 if k > 0 and jw[k - 1] == JF else 0); fi = q_ * 11.0 / (JF - 1); i0 = min(10, int(fi)); fw = fi - i0       # 12 keyframes base estirados a JF frames
                        jr = [KFJ[kb_][i0][a] + (KFJ[kb_][i0 + 1][a] - KFJ[kb_][i0][a]) * fw for a in range(3)]
                        wj = 1.0 if jw[k] else 0.5; r_ = [r_[a] + (jr[a] - r_[a]) * wj for a in range(3)]
                if lam[k] != 0.0:                                                               # tendido boca arriba: cuerpo a la pose de reposo del rig + la variante propia de este zombie
                    lk = lam[k]; lw = ss(min(1.0, lk * 2.5)); r_ = [v_ * (1 - lw) for v_ in r_]; ax_, ay_, fr_, ph0 = fv["arm"]; wg = fv["wig"] * math.sin(k * 0.45) * lw
                    if short == "Hips": r_[0] += math.radians(-90) * lk
                    elif short == "Neck": r_[0] += -0.12 * lk; r_[1] += 0.6 * fv["neck"] * lw
                    elif short == "RightUpArm": r_[1] += ay_ * math.sin(k * fr_ + ph0) * lw; r_[0] += ax_ * math.sin(k * fr_ * 0.8 + ph0) * lw
                    elif short == "LeftUpArm": r_[1] -= ay_ * math.sin(k * fr_ + ph0 + 2.0) * lw; r_[0] += ax_ * math.sin(k * fr_ * 0.8 + ph0 + 2.0) * lw
                    elif short == "RightUpLeg": r_[0] += (fv["legup"][0] + wg) * lw; r_[2] += fv["splay"][0] * lw
                    elif short == "LeftUpLeg": r_[0] += (fv["legup"][1] - wg) * lw; r_[2] += fv["splay"][1] * lw
                    elif short == "Rightknee": r_[0] += fv["knee"][0] * lw
                    elif short == "Leftknee": r_[0] += fv["knee"][1] * lw
                if k >= ka:                                                                     # ataque al muro: puñetazos / intento de trepar (salto base + brazos arriba + patalear)
                    add_, dzk_, jmp_ = ATKS[k]; wa_ = ss((k - ka) / 10.0)
                    if jmp_ is not None:
                        kb2_ = b.replace(f"_zombie_{n}", "_zombie_1")
                        if kb2_ in KFJ:
                            fi = jmp_[0] * 11.0; i0 = min(10, int(fi)); fw = fi - i0; jr2 = [KFJ[kb2_][i0][a] + (KFJ[kb2_][i0 + 1][a] - KFJ[kb2_][i0][a]) * fw for a in range(3)]
                            wj2 = jmp_[1] * wa_; r_ = [r_[a] + (jr2[a] - r_[a]) * wj2 for a in range(3)]
                    if short in add_: r_ = [r_[a] + add_[short][a] * wa_ for a in range(3)]
                rows[b][k] = r_
        out = copy.deepcopy(D)
        out["nombre"] = f"parte2_zombie_{n}_sigue"; out["frame_inicio"] = 1; out["frame_fin"] = N
        out["root"]["canales"]["location"] = [[round(v, 5) for v in xs], [round(v, 5) for v in ys], [round(v, 5) for v in zs]]
        out["root"]["canales"]["rotation_euler"] = [[0.0] * N, [0.0] * N, [round(v, 5) for v in rz]]
        for b in bones:
            pr = out["armature"]["bones"][b]
            pr["rotation_euler"] = [[round(rows[b][k][a], 5) for k in range(N)] for a in range(3)]
            for p in ("location", "scale"): pr[p] = [val(c, D["frame_fin"] - 1) for c in pr[p]]
        for on, o in out["ojos"].items():
            for key, ch in list(o["canales"].items()): o["canales"][key] = [val(c, D["frame_fin"] - 1) for c in ch]
            for grp in ("visibilidad", "shape_keys"):
                for key, c in list(o[grp].items()): o[grp][key] = val(c, D["frame_fin"] - 1)
        carpeta = os.path.join(BASE, f"zombie_{n}/refinar/animaciones_ia/parte2_zombie_{n}_sigue"); os.makedirs(carpeta, exist_ok=True)
        with open(os.path.join(carpeta, f"parte2_zombie_{n}_sigue.animacion.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
        mxr = max(math.dist((xs[k], ys[k], zs[k]), (xs[k + 1], ys[k + 1], zs[k + 1])) for k in range(N - 1))
        print(f"zombie_{n}: k=480 ({xs[480]:.1f},{ys[480]:.1f})  k=540 ({xs[540]:.1f},{ys[540]:.1f})  k=700 ({xs[700]:.1f},{ys[700]:.1f},{zs[700]:.1f})  fin ({xs[-1]:.1f},{ys[-1]:.1f},{zs[-1]:.1f})  paso max {mxr:.3f}")
    json.dump({"N": N, "eventos": {str(n): EVT[n] for n in EVT}}, open(os.path.join(HERE, "empujes_zombies.json"), "w", encoding="utf-8"), indent=1)
    print("empujes:", {n: (EVT[n]["frame_golpe"], EVT[n]["pos"], EVT[n]["n"]) for n in EVT})


if __name__ == "__main__":
    main()
