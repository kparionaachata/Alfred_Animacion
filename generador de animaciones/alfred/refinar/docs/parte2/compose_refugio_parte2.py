"""Parte 2 - Alfred construye un REFUGIO de 4x4 bloques + techo tras descansar (pedido de Kebyn), con el principio de 'Crear pared NxN bloques':
Alfred queda fijo en un punto 1 m detras de cada celda y repite el ciclo agachar->colocar->parar (KEYFRAMES_COLOCAR_MESA_CRAFTEO, el mismo del add-on,
reescalado a FPB frames); el bloque aparece (oculto hasta ese frame) cuando el cuerpo esta agachado (frame MID del ciclo). Entre puntos camina por fuera del refugio.
Extiende los artefactos de la parte 2 (no los modifica): lee parte2_alfred_nada_y_sube / parte2_jerry_nada_y_sube (1600 f) y escribe
parte2_alfred_refugio / parte2_jerry_refugio (N2 f) + refugio_bloques.json (coordenada y frame de aparicion de cada bloque).
Ejecutar DESPUES de compose_parte2.py:  python alfred/refinar/docs/parte2/compose_refugio_parte2.py   (desde 'generador de animaciones')
"""
import ast, copy, json, math, os

BASE = "generador de animaciones" if os.path.isdir("generador de animaciones") else "."
N_FULL = 1600                               # largo de los artefactos base
K_REST0 = 1357                               # Alfred llega al punto de descanso (se inclina)
REST_FULL = 251                              # descanso original: f1357 -> f1608 (empezaba a levantarse)
N_TOTAL = 2150                               # duracion total (igual en compose_zombies_parte2.py)
HERE = os.path.join(BASE, "alfred/refinar/docs/parte2")
K_ARR = 1349                                 # f en que Alfred llega al punto de descanso: justo ahi coloca la antorcha (sistema 'Colocar antorcha')
TORCH_INS = 42                               # 6 f para ponerse de pie + ciclo colocar antorcha (30 f, antorcha aparece en el f15 del ciclo) + 6 f para volver al descanso
TORCH_XY = (-96.0, -109.0)                   # centro del interior 2x2: a 0.5 m de todos los recorridos de Alfred y Jerry dentro del refugio
N0 = K_REST0 + TORCH_INS + REST_FULL // 4               # descanso reducido otra vez a la MITAD (251 -> 125 -> ~62 f): se levanta en f1419 (los artefactos base se cortan ahi)
FPB = 12                                     # frames por bloque: rapido (el ciclo base del add-on dura 30; minimo del add-on 6)
RAMP = 8
SPEED = 0.14                                 # m/f al caminar (rapido)
TURN = 0.3
D2R = math.pi / 180.0
INT_X = [-96.5, -95.5]                      # interior 2x2 (centros de celda): contiene el descanso de Alfred (-96.5,-109.5); el refugio completo es 4x4 (x -97.5..-94.5, y -110.5..-107.5)
INT_Y = [-109.5, -108.5]
JERRY0 = (-95.7, -107.5)                     # Jerry empieza en la celda norte del anillo, que queda como hueco hasta que entra
JERRY_FUERA = (-95.5, -105.5)                # sale a mirar construir desde fuera
JERRY_FIN = (-96.5, -108.5)                  # celda NW del interior: donde se queda al entrar
Z0 = 14.0
LAYERS = 3                                   # altura total 3: capas 0-1 = paredes (2 de alto), capa 2 = techo
FL = 14                                      # frames del salto de Jerry contra un zombie
WIND = 8                                     # anticipacion (agacharse y apuntar) antes del salto
REC = 18                                     # recuperacion tras el golpe (aterriza, amortigua, sacude la cabeza)
JW = 36                                      # frames que Alfred espera mientras Jerry entra por el hueco
RELLENO = {}                                   # sin esquinas: la celda baja (-97.5,-110.5) era una esquina y ya no se construye


def ss(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def norm(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def val(c, i):
    return c[i] if isinstance(c, list) else c


def load(path):
    return json.load(open(path, encoding="utf-8"))


def art(nombre, carpeta):
    return os.path.join(BASE, carpeta, "refinar/animaciones_ia", nombre, nombre + ".animacion.json")


def rows_of(D):
    return {b: [[val(pr["rotation_euler"][a], i) for a in range(3)] for i in range(D["frame_fin"])] for b, pr in D["armature"]["bones"].items()}


def row_at(R, f):                            # fila interpolada (f 1-based, float)
    n = len(next(iter(R.values()))); f = max(1.0, min(n, f)); i0 = int(math.floor(f)) - 1; i1 = min(n - 1, i0 + 1); w = f - math.floor(f)
    return {b: [R[b][i0][a] + (R[b][i1][a] - R[b][i0][a]) * w for a in range(3)] for b in R}


def mixrow(A, B, w):
    return {b: [A[b][a] + (B[b][a] - A[b][a]) * w for a in range(3)] for b in A}


def ciclo_colocar(nombre="KEYFRAMES_COLOCAR_MESA_CRAFTEO"):
    """KEYFRAMES_COLOCAR_MESA_CRAFTEO (0..15 + vuelta smoothstep 16..29, igual que _build_colocar_mesa_crafteo_keyframes) leido sin importar el add-on."""
    src = open(os.path.join(BASE, "alfred/refinar/alfred_animation_studio/generate_slots_alfred.py"), encoding="utf-8").read()
    kf = None
    for nd in ast.parse(src).body:
        if isinstance(nd, ast.Assign) and getattr(nd.targets[0], "id", "") == nombre: kf = ast.literal_eval(nd.value)
    out = {}
    for bone, fr in kf.items():
        seq = [fr[i] for i in range(16)]
        for j in range(1, 15):
            t = j / 14.0; tt = t * t * (3 - 2 * t); seq.append(tuple(fr[15][k] + (fr[0][k] - fr[15][k]) * tt for k in range(3)))
        out[bone] = seq
    return out


def trunc(o, n_old, n_new):
    """recorta a n_new frames toda lista numerica de n_old elementos (canales por frame)."""
    if isinstance(o, list):
        if len(o) == n_old and all(isinstance(v, (int, float)) for v in o): del o[n_new:]
        else:
            for v in o: trunc(v, n_old, n_new)
    elif isinstance(o, dict):
        for v in o.values(): trunc(v, n_old, n_new)


def ins(o, n_old, at, n_ins):
    """inserta n_ins frames (copia del frame anterior) en la posicion `at` de toda lista numerica de n_old elementos (canales por frame)."""
    if isinstance(o, list):
        if len(o) == n_old and all(isinstance(v, (int, float)) for v in o): o[at:at] = [o[at - 1]] * n_ins
        else:
            for v in o: ins(v, n_old, at, n_ins)
    elif isinstance(o, dict):
        for v in o.values(): ins(v, n_old, at, n_ins)


def ext(o, n_old, n_add):
    """alarga con el ultimo valor toda lista numerica de n_old elementos (canales por frame)."""
    if isinstance(o, list):
        if len(o) == n_old and all(isinstance(v, (int, float)) for v in o): o.extend([o[-1]] * n_add)
        else:
            for v in o: ext(v, n_old, n_add)
    elif isinstance(o, dict):
        for v in o.values(): ext(v, n_old, n_add)


# ----------------------------------------------------------------------------------------------- plan de bloques
# Alfred construye DESDE DENTRO: recorre las 12 celdas del borde del interior (sentido antihorario, empezando donde descansaba) y desde cada una coloca los bloques del
# anillo exterior que tiene delante (a 1 m; a sqrt(2) en las diagonales de las esquinas). Segunda vuelta: techo del interior. Sin puertas: termina sellado dentro.
DIRS = {"N": (0, 1, 0.0), "W": (-1, 0, math.pi / 2), "S": (0, -1, math.pi), "E": (1, 0, -math.pi / 2),
        "NW": (-1, 1, math.pi / 4), "SW": (-1, -1, 3 * math.pi / 4), "SE": (1, -1, -3 * math.pi / 4), "NE": (1, 1, -math.pi / 4)}
SW_, NW_, SE_, NE_ = (INT_X[0], INT_Y[0]), (INT_X[0], INT_Y[1]), (INT_X[1], INT_Y[0]), (INT_X[1], INT_Y[1])


def plan():
    """Alfred construye DESDE DENTRO (interior 2x2): desde cada celda coloca los 3 bloques del anillo que tiene delante (2 de frente a 1 m + la diagonal a sqrt(2)), 4 capas (3 de muro + techo).
    Deja el hueco del norte (celda NE->N) para el final: Jerry entra por ahi mientras Alfred espera; luego Alfred lo cierra y pone el techo del interior. Sin puertas al terminar."""
    P = []
    for c, dirs in ((SE_, ("E",)), (NE_, ("E",)), (NW_, ("N", "W")), (SW_, ("S", "W")), (SE_, ("S",))):     # primero los muros que miran a los zombies (este y norte)
        for dn in dirs:
            dx, dy, rz = DIRS[dn]; dist = math.hypot(dx, dy); tc = (c[0] + dx, c[1] + dy)
            for ly in ([RELLENO[tc]] if tc in RELLENO else []) + list(range(LAYERS)):
                P.append((tc, ly, (c[0], c[1], rz), dist))
    for st, tg, rz in ((SE_, SW_, math.pi / 2), (SE_, NE_, 0.0), (SW_, SE_, -math.pi / 2), (SW_, NW_, 0.0)):    # techo del interior
        P.append((tg, LAYERS - 1, (st[0], st[1], rz), 1.0))
    P.append(("WAITJ",))                                                                # el hueco norte se cierra al final: Jerry sale a empujar zombies y vuelve a entrar
    for ly in range(LAYERS):
        P.append(((NE_[0], NE_[1] + 1.0), ly, (NE_[0], NE_[1], 0.0), 1.0))
    return P


EX0, EX1, EY0, EY1 = -99.0, -92.3, -111.9, -105.8     # corredor de Jerry alrededor de los muros (1.3-1.7 m por fuera: los zombies que atacan el muro ocupan los 0.7 m pegados a el)


def _perim_t(q):
    w, h = EX1 - EX0, EY1 - EY0
    if abs(q[1] - EY0) < 1e-6: return q[0] - EX0
    if abs(q[0] - EX1) < 1e-6: return w + (q[1] - EY0)
    if abs(q[1] - EY1) < 1e-6: return w + h + (EX1 - q[0])
    return 2 * w + h + (EY1 - q[1])


def _to_perim(p):
    x = min(max(p[0], EX0), EX1); y = min(max(p[1], EY0), EY1)
    if EX0 < x < EX1 and EY0 < y < EY1:
        d = [(x - EX0, (EX0, y)), (EX1 - x, (EX1, y)), (y - EY0, (x, EY0)), (EY1 - y, (x, EY1))]; return min(d)[1]
    return (x, y)


def _crosses(a, b):
    for i in range(1, 40):
        x = a[0] + (b[0] - a[0]) * i / 40.0; y = a[1] + (b[1] - a[1]) * i / 40.0
        if -98.35 < x < -93.65 and -111.35 < y < -106.65: return True                  # solo cuenta cruzar el refugio (+0.35 m); el corredor ancho se usa para rodearlo
    return False


def jroute(a, b):
    """camino de Jerry de a a b por fuera del refugio (recto si no lo cruza; si no, rodeando por el lado mas corto)."""
    if not _crosses(a, b): return [a, b]
    qa, qb = _to_perim(a), _to_perim(b); per = 2 * ((EX1 - EX0) + (EY1 - EY0)); ta, tb = _perim_t(qa), _perim_t(qb)
    corners = [(EX0, EY0), (EX1, EY0), (EX1, EY1), (EX0, EY1)]; ct = [0.0, EX1 - EX0, (EX1 - EX0) + (EY1 - EY0), 2 * (EX1 - EX0) + (EY1 - EY0)]
    ccw = (tb - ta) % per; pts = [a, qa]
    if ccw <= per / 2:
        for k in range(4):
            if 1e-6 < (ct[k] - ta) % per < ccw - 1e-6: pts.append(corners[k])
        pts.sort(key=lambda p: 0) if False else None
        mid = [c for c in pts[2:]]; mid.sort(key=lambda c: (ct[corners.index(c)] - ta) % per); pts = [a, qa] + mid
    else:
        cw = per - ccw; mid = [corners[k] for k in range(4) if 1e-6 < (ta - ct[k]) % per < cw - 1e-6]; mid.sort(key=lambda c: (ta - ct[corners.index(c)]) % per); pts = [a, qa] + mid
    return pts + [qb, b]


def jsim(pts, vmax=0.17):
    """frames de una carrera de Jerry por pts: lista de (x, y, v) (arranque/frenada suaves)."""
    cum = [0.0]
    for a_, b_ in zip(pts, pts[1:]): cum.append(cum[-1] + math.dist(a_, b_))
    out = []; sd = 0.0; v = 0.0; tot = cum[-1]
    while tot - sd > 1e-3:
        rem = tot - sd; vt = min(vmax, math.sqrt(2 * 0.015 * rem) + 0.01); v += max(-0.015, min(0.015, vt - v)); v = max(0.012, v); sd = min(tot, sd + v)
        q = next((i for i in range(1, len(cum)) if cum[i] >= sd - 1e-9), len(cum) - 1); t = (sd - cum[q - 1]) / max(cum[q] - cum[q - 1], 1e-9)
        out.append((pts[q - 1][0] + (pts[q][0] - pts[q - 1][0]) * t, pts[q - 1][1] + (pts[q][1] - pts[q - 1][1]) * t, v))
    return out


def _perim_pt(t):
    w, h = EX1 - EX0, EY1 - EY0; per = 2 * (w + h); t %= per
    if t <= w: return (EX0 + t, EY0)
    if t <= w + h: return (EX1, EY0 + (t - w))
    if t <= 2 * w + h: return (EX1 - (t - w - h), EY1)
    return (EX0, EY1 - (t - 2 * w - h))


def jsim_fit(pts, nframes):
    """como jsim pero ajustando la velocidad para que dure ~nframes (Jerry no se queda parado esperando: camina mas lento hasta llegar a tiempo)."""
    lo, hi = 0.012, 0.35
    for _ in range(30):
        mid = (lo + hi) / 2; n = len(jsim(pts, mid))
        if n > nframes: lo = mid
        else: hi = mid
    sim = jsim(pts, hi)
    while len(sim) < nframes and sim: sim.append((sim[-1][0], sim[-1][1], sim[-1][2] * 0.5))
    return sim[:nframes] if len(sim) > nframes else sim


def jerry_schedule(n_add):
    """Jerry VIGILA SIEMPRE y en movimiento: patrulla el corredor exterior (ida y vuelta) mientras llegan los zombies; por cada zombie que entra al anillo (empujes_zombies.json)
    corre por el muro, se coloca delante, SALTA y lo empuja de frente en el frame del golpe; tras empujar sigue patrullando hacia el siguiente. Despues del ultimo vuelve a entrar por el hueco
    norte. Devuelve posiciones, velocidades, etiquetas de salto por frame e i_in (indice en que ya esta dentro)."""
    EV = sorted(json.load(open(os.path.join(HERE, "empujes_zombies.json"), encoding="utf-8"))["eventos"].values(), key=lambda e: e["frame_golpe"])
    JT, JV, TAG = [], [], []; jp = [JERRY0[0], JERRY0[1]]; warn = []

    def app(sim):
        for x, y, v in sim: JT.append((x, y)); JV.append(v); TAG.append(None)
        if sim: jp[0], jp[1] = sim[-1][0], sim[-1][1]

    def patrol_leg(direction, vmax=0.09):
        """un tramo de patrulla de ~2.5 m por el corredor exterior (ida y vuelta alternando el sentido)."""
        ta = _perim_t(_to_perim(tuple(jp))); q = _perim_pt(ta + direction * 2.5)
        app(jsim(jroute(tuple(jp), q), vmax))

    app(jsim([tuple(jp), JERRY_FUERA]))
    dirn = 1
    for ei, e in enumerate(EV):
        ih = e["frame_golpe"] - N0 - 1; n = e["n"]; t = e["t"]
        Phit = (e["pos"][0] - n[0] * 0.9, e["pos"][1] - n[1] * 0.9)
        perp = (-n[1], n[0]); cand = [(Phit[0] + perp[0] * 2.0 * sg_, Phit[1] + perp[1] * 2.0 * sg_) for sg_ in (1, -1)]                   # espera 2 m ANTES por el corredor del muro (perpendicular a la normal) y salta de lado contra el zombie
        def _dbb(q): return math.hypot(max(-98.0 - q[0], 0, q[0] + 94.0), max(-111.0 - q[1], 0, q[1] + 107.0))
        ok_ = [q for q in cand if _dbb(q) >= 0.45] or cand; Pt = min(ok_, key=lambda q: math.dist(q, tuple(jp)))
        i_wind = ih - FL - WIND + 1
        for _ in range(40):                                                                # mientras sobre tiempo: patrulla (nunca se queda quieto)
            dur = len(jsim(jroute(tuple(jp), Pt)))
            if i_wind - len(JT) - dur < 35: break
            patrol_leg(dirn); dirn = -dirn
        sim = jsim_fit(jroute(tuple(jp), Pt), max(1, i_wind - len(JT)))                      # el ultimo tramo se ajusta para llegar justo a tiempo, sin esperar
        if len(sim) > i_wind - len(JT): warn.append((ei, len(sim) - (i_wind - len(JT))))
        app(sim); jp[0], jp[1] = Pt
        for q in range(WIND): JT.append(Pt); JV.append(0.0); TAG.append(("wind", (q + 1) / float(WIND), ei))
        for q in range(FL):
            u = (q + 1) / float(FL); JT.append((Pt[0] + (Phit[0] - Pt[0]) * u, Pt[1] + (Phit[1] - Pt[1]) * u)); JV.append(0.0); TAG.append(("fly", u, ei))
        jp[0], jp[1] = Phit
        for q in range(REC): JT.append(Phit); JV.append(0.0); TAG.append(("rec", (q + 1) / float(REC), ei))
    app(jsim(jroute(tuple(jp), (JERRY_FUERA[0], -106.35)))); app(jsim([tuple(jp), (JERRY_FUERA[0], -107.5), (JERRY_FUERA[0], -108.5), JERRY_FIN]))
    i_in = len(JT) - 1
    return EV, JT, JV, TAG, i_in, warn


def jerry_avoid(JT, TAG, ZP, EV, dmin=1.0):
    """Jerry nunca se pega a un zombie (salvo en sus saltos): empuja su posicion hacia fuera de los zombies a menos de dmin m (suavizado) y fuera de los muros."""
    n = len(JT); offs = [[0.0, 0.0] for _ in range(n)]
    for i in range(n):
        if TAG[i] is not None: continue
        x, y = JT[i]
        for zn, Lz in ZP.items():
            zx, zy = Lz[N0 + i] if N0 + i < len(Lz) else Lz[-1]; d = math.hypot(x - zx, y - zy)
            if 1e-6 < d < dmin: offs[i][0] += (x - zx) / d * (dmin - d); offs[i][1] += (y - zy) / d * (dmin - d)
            if 1e-6 < d < dmin:                                                                       # si esta pegado al muro (corredor), se aparta TAMBIEN hacia fuera del refugio
                cx_, cy_ = min(max(x, -98.0), -94.0), min(max(y, -111.0), -107.0); ox_, oy_ = x - cx_, y - cy_; do_ = math.hypot(ox_, oy_)
                if 1e-6 < do_ < 1.4: offs[i][0] += ox_ / do_ * (dmin - d) * 1.5; offs[i][1] += oy_ / do_ * (dmin - d) * 1.5
    sm = []
    for i in range(n):
        lo, hi = max(0, i - 6), min(n, i + 7); sm.append((sum(o[0] for o in offs[lo:hi]) / (hi - lo) * 1.6, sum(o[1] for o in offs[lo:hi]) / (hi - lo) * 1.6))
    out = []
    for i, (x, y) in enumerate(JT):
        if TAG[i] is not None or (max(0.0, -98.45 - x, x + 93.55) == 0 and max(0.0, -111.45 - y, y + 106.55) == 0 and False): out.append((x, y)); continue
        nx, ny = x + sm[i][0], y + sm[i][1]
        dx_, dy_ = max(-98.0 - nx, 0, nx + 94.0), max(-111.0 - ny, 0, ny + 107.0)                  # fuera del bloque del refugio (0.45 m)
        if -98.0 < nx < -94.0 and -111.0 < ny < -107.0: nx, ny = x, y
        out.append((nx, ny))
    return out


def jerry_inside(JT, JV, TAG, i_in, i_alf_done, n_add):
    """ya dentro: sigue en movimiento. Hasta que Alfred termina de cerrar, paseo corto en su celda (NW); despues patrulla NW<->SW."""
    del JT[i_in + 1:], JV[i_in + 1:], TAG[i_in + 1:]; jp = [JERRY_FIN[0], JERRY_FIN[1]]
    def go(sim):
        for x, y, v in sim: JT.append((x, y)); JV.append(v); TAG.append(None)
        if sim: jp[0], jp[1] = sim[-1][0], sim[-1][1]
    a1, a2 = (JERRY_FIN[0] - 0.05, JERRY_FIN[1] - 0.05), (JERRY_FIN[0] - 0.32, JERRY_FIN[1] + 0.12)
    s_ = 0
    while len(JT) < min(i_alf_done, n_add):
        go(jsim([tuple(jp), a2 if s_ % 2 == 0 else a1], 0.035)); s_ += 1
    b1, b2 = (JERRY_FIN[0], JERRY_FIN[1] - 0.05), (JERRY_FIN[0], JERRY_FIN[1] - 0.85)
    s_ = 0
    while len(JT) < n_add:
        go(jsim([tuple(jp), b2 if s_ % 2 == 0 else b1], 0.05)); s_ += 1
    del JT[n_add:], JV[n_add:], TAG[n_add:]


def main():
    A = load(art("parte2_alfred_nada_y_sube", "alfred")); J = load(art("parte2_jerry_nada_y_sube", "jerry")); TR = load(art("parte2_alfred_tramo_tierra", "alfred"))
    for D_ in (A, J): ins(D_, N_FULL, K_ARR, TORCH_INS); D_["frame_fin"] = N_FULL + TORCH_INS                  # hueco de TORCH_INS f al llegar Alfred al descanso (Jerry espera; su charla y el descanso se corren)
    for D_ in (A, J): trunc(D_, N_FULL + TORCH_INS, N0); D_["frame_fin"] = N0                                  # el descanso termina antes: se descartan los frames sobrantes (Jerry deja de hablar donde corte)
    # ---------------- Alfred coloca la antorcha al llegar (ciclo `KEYFRAMES_COLOCAR_ANTORCHA` del add-on, 30 f, agachado en el f15 = aparece la antorcha) y despues empieza a descansar
    CT = ciclo_colocar("KEYFRAMES_COLOCAR_ANTORCHA"); BA = A["armature"]["bones"]; at = K_ARR
    row_at_ = lambda i: {b: [val(BA[b]["rotation_euler"][a_], i) for a_ in range(3)] for b in BA}
    pre_r, post_r = row_at_(at - 1), row_at_(at + TORCH_INS); LA = A["root"]["canales"]["location"]; RZA = A["root"]["canales"]["rotation_euler"][2]
    tz_pre, tz_post = LA[2][at - 1], LA[2][at + TORCH_INS]; rz_pre, rz_post = RZA[at - 1], RZA[at + TORCH_INS]
    rz_t = math.atan2(-(TORCH_XY[0] - LA[0][at - 1]), (TORCH_XY[1] - LA[1][at - 1])); rz_t = rz_pre + norm(rz_t - rz_pre)                    # mira hacia donde queda la antorcha
    for t in range(TORCH_INS):
        if t < 6: w_ = ss((t + 1) / 6.0); tgt = {b: (list(CT[b][0]) if b in CT else pre_r[b]) for b in BA}; rw = mixrow(pre_r, tgt, w_); zz = tz_pre + (Z0 - tz_pre) * w_; rr = rz_pre + (rz_t - rz_pre) * w_
        elif t < 36: rw = {b: (list(CT[b][t - 6]) if b in CT else pre_r[b]) for b in BA}; zz = Z0; rr = rz_t
        else:
            w_ = ss((t - 35) / 6.0); src = {b: (list(CT[b][29]) if b in CT else pre_r[b]) for b in BA}; rw = mixrow(src, post_r, w_); zz = Z0 + (tz_post - Z0) * w_; rr = rz_t + (rz_post - rz_t) * w_
        for b in BA:
            for a_ in range(3): BA[b]["rotation_euler"][a_][at + t] = round(rw[b][a_], 5)
        LA[2][at + t] = round(zz, 5); RZA[at + t] = round(rr, 5)
    json.dump({"fuente": "bloques_dinamicos/antorcha_1.blend (sistema Colocar antorcha del add-on)", "frame_aparece": at + 6 + 15 + 1, "pos": [TORCH_XY[0], TORCH_XY[1], Z0], "alfred_en": [LA[0][at - 1], LA[1][at - 1]]},
              open(os.path.join(HERE, "antorcha_parte2.json"), "w", encoding="utf-8"), indent=1)
    RA = rows_of(A); RT = rows_of(TR); CY = ciclo_colocar(); bones = list(RA)
    rest = {b: list(RA[b][N0 - 1]) for b in bones}
    stand = copy.deepcopy(rest)
    for b, seq in CY.items():
        if b in stand: stand[b] = list(seq[0])
    loc = [[val(A["root"]["canales"]["location"][a], N0 - 1)] for a in range(3)]
    pos = [loc[0][0], loc[1][0]]; rz = val(A["root"]["canales"]["rotation_euler"][2], N0 - 1); rzs = []; locs = []; rows = []
    blocks = []

    def push(row, x, y, z, r):
        rows.append(row); locs.append((x, y, z)); rzs.append(r)

    cur = {"row": rest, "z": loc[2][0], "rz": rz, "ph": 0.0}
    hold = lambda n, row: [push(row, pos[0], pos[1], cur["z"], cur["rz"]) for _ in range(n)]
    hold(0, rest)
    for u in range(1, 13):                                                              # se incorpora
        w = ss(u / 12.0); push(mixrow(rest, stand, w), pos[0], pos[1], loc[2][0] + (Z0 - loc[2][0]) * w, cur["rz"])
    cur["row"] = stand; cur["z"] = Z0

    def walk(path):
        pts = [path[0]]
        for p in path[1:]:
            if math.dist(p, pts[-1]) > 1e-6: pts.append(p)
        if len(pts) < 2: return
        cum = [0.0]
        for a, b in zip(pts, pts[1:]): cum.append(cum[-1] + math.dist(a, b))
        s = 0.0; v = 0.0; total = cum[-1]
        while total - s > 1e-3:
            rem = total - s; vt = min(SPEED, math.sqrt(2 * 0.015 * rem) + 0.01); v += max(-0.015, min(0.012, vt - v)); v = max(0.012, v); s = min(total, s + v)
            q = next((i for i in range(1, len(cum)) if cum[i] >= s - 1e-9), len(cum) - 1); t = (s - cum[q - 1]) / max(cum[q] - cum[q - 1], 1e-9)
            pos[0] = pts[q - 1][0] + (pts[q][0] - pts[q - 1][0]) * t; pos[1] = pts[q - 1][1] + (pts[q][1] - pts[q - 1][1]) * t
            hd = math.atan2(-(pts[q][0] - pts[q - 1][0]), (pts[q][1] - pts[q - 1][1]))
            cur["rz"] += max(-TURN, min(TURN, norm(hd - cur["rz"])))
            cur["ph"] += 0.9 * v / SPEED
            push(mixrow(stand, row_at(RT, 130 + (cur["ph"] % 11.0)), ss(v / 0.05)), pos[0], pos[1], Z0, cur["rz"])

    def turn(rz_t, n=5):
        r0 = cur["rz"]; d = norm(rz_t - r0)
        if abs(d) < 0.02: return
        for u in range(1, n + 1): push(stand, pos[0], pos[1], Z0, r0 + d * ss(u / n))
        cur["rz"] = r0 + d

    def place(cell, ly, dist=1.0):
        k0 = N0 + 1 + len(rows); mid = round((FPB - 1) * 15 / 29.0)
        for q in range(FPB):
            f = q * 29.0 / (FPB - 1); i0 = min(28, int(f)); w = f - i0
            r = {b: (list(stand[b]) if b not in CY else [CY[b][i0][a] + (CY[b][i0 + 1][a] - CY[b][i0][a]) * w for a in range(3)]) for b in bones}
            push(r, pos[0], pos[1], Z0, cur["rz"])
        blocks.append({"x": cell[0], "y": cell[1], "z": Z0 + ly, "capa": ly, "frame": k0 + mid, "alcance": round(dist, 3)})

    n_add = N_TOTAL - N0; EV, JT, JV, TAG, i_in, jwarn = jerry_schedule(n_add)
    ZP0 = {}
    for n_ in (1, 2, 3, 4, 5):
        Lz0 = load(art(f"parte2_zombie_{n_}_sigue", f"zombie_{n_}"))["root"]["canales"]["location"]; ZP0[n_] = list(zip(Lz0[0], Lz0[1]))
    JT = jerry_avoid(JT, TAG, ZP0, EV)
    estado = None
    for it in plan():
        if it[0] == "WAITJ":
            hold(max(0, i_in + 10 - len(rows)), stand); continue                       # el hueco se cierra cuando Jerry ya esta dentro
        cell, ly, (sx, sy, srz), dist = it
        if (sx, sy) != estado:
            here_ = (round(pos[0], 2), round(pos[1], 2))
            if {here_, (round(sx, 2), round(sy, 2))} == {tuple(map(lambda v_: round(v_, 2), SW_)), tuple(map(lambda v_: round(v_, 2), NE_))}: walk([(pos[0], pos[1]), SE_, (sx, sy)])     # la diagonal pasa por la antorcha: rodea por SE
            else: walk([(pos[0], pos[1]), (sx, sy)])
            estado = (sx, sy)
        turn(srz)
        place(cell, ly, dist)
    turn(0.0, 8); hold(max(0, n_add - len(rows)), stand)                               # sellado dentro: mira a Jerry
    assert len(rows) == n_add, (len(rows), n_add)
    N2 = N0 + n_add
    jerry_inside(JT, JV, TAG, i_in, blocks[-1]["frame"] - N0 - 1 + 8, n_add)
    print(f"bloques {len(blocks)}  frames extra {n_add}  N2 {N2}  ultimo bloque en f{blocks[-1]['frame']}")

    # ---------------------------------------------------------------- Alfred
    out = copy.deepcopy(A); out["nombre"] = "parte2_alfred_refugio"; out["frame_fin"] = N2
    ext(out["ojos"], N0, n_add); ext(out["armature"], N0, n_add)
    for b in bones:
        ch = out["armature"]["bones"][b]["rotation_euler"]
        for a in range(3):
            if not isinstance(ch[a], list): ch[a] = [ch[a]] * N0
            ch[a][N0:] = [round(r[b][a], 5) for r in rows]
    for p in ("location", "scale"):
        for b in bones:
            ch = out["armature"]["bones"][b][p]
            for a in range(3):
                if isinstance(ch[a], list) and len(ch[a]) == N0: ch[a][N0:] = [ch[a][N0 - 1]] * n_add
    for key, arr in (("location", locs), ("rotation_euler", None)):
        pass
    L = out["root"]["canales"]["location"]; R = out["root"]["canales"]["rotation_euler"]
    for a in range(3): L[a][N0:] = [round(l[a], 5) for l in locs]
    R[2][N0:] = [round(v, 5) for v in rzs]
    for a in (0, 1):
        if not isinstance(R[a], list): R[a] = [R[a]] * N2
        elif len(R[a]) == N0: R[a].extend([R[a][-1]] * n_add)
    for i in range(1, N2): R[2][i] = R[2][i - 1] + norm(R[2][i] - R[2][i - 1])
    carpeta = os.path.join(BASE, "alfred/refinar/animaciones_ia/parte2_alfred_refugio"); os.makedirs(carpeta, exist_ok=True)
    json.dump(out, open(os.path.join(carpeta, "parte2_alfred_refugio.animacion.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    # ---------------------------------------------------------------- Jerry: vigila fuera, SALTA y EMPUJA a cada zombie que se acerca demasiado (frame del golpe = empujes_zombies.json) y vuelve a entrar por el hueco
    oj = copy.deepcopy(J); oj["nombre"] = "parte2_jerry_refugio"; oj["frame_fin"] = N2
    ext(oj["ojos"], N0, n_add); ext(oj["armature"], N0, n_add); ext(oj["root"], N0, n_add)
    JB = oj["armature"]["bones"]
    for b in JB:
        for a in range(3):
            c_ = JB[b]["rotation_euler"][a]
            if isinstance(c_, list) and len(c_) != N2: JB[b]["rotation_euler"][a] = c_ + [c_[-1]] * (N2 - len(c_))
    jl = oj["root"]["canales"]["location"]; jr = oj["root"]["canales"]["rotation_euler"]
    for a in range(3):
        if not isinstance(jl[a], list): jl[a] = [jl[a]] * N2
    if not isinstance(jr[2], list): jr[2] = [jr[2]] * N2
    jz = val(jl[2], N0 - 1); jrz = val(jr[2], N0 - 1)
    base = {b: [JB[b]["rotation_euler"][a][N0 - 1] for a in range(3)] for b in JB}; base["jaw_bot"][0] = 0.0
    ev_i = [(e["frame_golpe"] - N0 - 1, e) for e in EV]
    ZPOS = {}
    for n_ in (1, 2, 3, 4, 5):
        Lz = load(art(f"parte2_zombie_{n_}_sigue", f"zombie_{n_}"))["root"]["canales"]["location"]; ZPOS[n_] = list(zip(Lz[0], Lz[1]))
    rzs_j = []; r_ = jrz; ph_g = 0.0; cum_t = 0.0; rows_j = []; dzs = []; offs = []
    for i in range(n_add):
        x_, y_ = JT[i]; sp = JV[i]; tag = TAG[i]; nx_, ny_ = JT[min(i + 1, n_add - 1)]; ax_, ay_ = locs[i][0], locs[i][1]
        look = min(((ZPOS[n][N0 + i][0], ZPOS[n][N0 + i][1]) for n in ZPOS), key=lambda q: math.dist(q, (x_, y_)))                  # siempre vigilante: cabeza y cuerpo hacia el zombie mas cercano (posicion real)
        dr = 0.0; dz = 0.0
        row = {b: list(v_) for b, v_ in base.items()}

        def addr(bn, ax, rad):
            row[bn][ax] += rad

        ox = oy = 0.0
        if tag:
            kind, u, ei = tag; e_ = EV[ei]; zp = ZPOS[e_["z"]][N0 + i]
            aim = math.atan2(-(zp[0] - x_), (zp[1] - y_))                                  # SIEMPRE apuntando al zombie (posicion real en este frame): cuerpo y cabeza hacia el
            if kind == "wind": mxr = 0.30
            elif kind == "fly": mxr = 0.40
            else: mxr = 0.30 * (1 - ss((u - 0.55) / 0.3))
            dr = max(-mxr, min(mxr, norm(aim - r_))); r_ = r_ + dr
            fx, fy = -math.sin(r_), math.cos(r_)                                           # hacia delante del perro

            def add2(bn, a2, rad):
                row[bn][a2] += rad

            def both(f_, ax_, rad):                                                         # mismo valor en ambos lados
                for sd_ in ("R", "L"): add2(f"{f_}.{sd_}", ax_, rad)

            def ear(c):                                                                     # orejas pegadas hacia atras y aleteando
                for sd_, ph_ in (("R", 0.0), ("L", 0.7)): add2(f"ear.{sd_}", 0, 0.18 * c + 0.08 * c * math.sin(i * 0.9 + ph_))

            if kind == "wind":                                                              # ANTICIPACION: cuarto trasero se encoge, peso atras, pecho y cabeza bajan mirando al zombie, cola baja, un pequeno temblor antes de saltar
                c = ss(u) ; tr = 0.015 * math.sin(i * 1.7) * c
                both("thigh", 0, 0.75 * c); both("shin", 0, -0.85 * c); both("foot", 0, -0.30 * c); both("toe", 0, -0.15 * c)
                both("front_thigh", 0, 0.18 * c); both("front_shin", 0, -0.22 * c); both("front_shoulder", 0, -0.08 * c)
                add2("spine_6", 0, -0.14 * c); add2("spine_4", 0, 0.06 * c); add2("scull_1", 0, 0.26 * c); add2("tail_1", 0, 0.12 * c); add2("tail_2", 2, 0.25 * math.sin(i * 0.8) * c)
                ear(c); dz = -0.20 * c + tr; ox, oy = -fx * 0.16 * c, -fy * 0.16 * c
            elif kind == "fly":                                                             # SALTO: las patas traseras empujan primero (onda de extension de atras a delante), el pecho sube, las delanteras alcanzan al zombie y golpean en el contacto
                g = (u ** 0.82) * 0.88; dz = -0.20 * (1 - ss(min(1.0, u / 0.18))) + 4 * 1.05 * g * (1 - g)
                extn = ss(u / 0.30); reach_ = ss((u - 0.18) / 0.72); thr = ss((u - 0.72) / 0.28); lag = lambda d_: ss((u - d_) / 0.35)
                both("thigh", 0, 0.75 * (1 - extn) - 0.95 * extn); both("shin", 0, -0.85 * (1 - extn) - 0.10 * extn); both("foot", 0, -0.30 * (1 - extn) + 0.12 * extn); both("toe", 0, -0.15 * (1 - extn) + 0.1 * extn)
                both("front_thigh", 0, 0.18 * (1 - reach_) - (1.10 + 0.30 * thr) * reach_); both("front_shoulder", 0, -0.08 * (1 - reach_) + (0.55 + 0.45 * thr) * reach_)
                both("front_shin", 0, -0.22 * (1 - reach_) - 0.12 * reach_); both("front_foot", 0, -0.12 * reach_); both("front_toe", 0, -0.1 * reach_)
                add2("spine_1", 0, -0.12 * lag(0.0)); add2("spine_2", 0, -0.10 * lag(0.08)); add2("spine_4", 0, -0.14 * lag(0.16) + 0.10 * thr); add2("spine_6", 0, -0.14 * (1 - lag(0.0)) + 0.30 * lag(0.24) - 0.10 * thr)
                add2("scull_1", 0, 0.26 * (1 - extn) + 0.20 * reach_ + 0.12 * thr); row["jaw_bot"][0] = -math.radians(25) * ss((u - 0.35) / 0.4)
                add2("tail_1", 0, 0.12 * (1 - extn) - 0.55 * lag(0.05)); add2("tail_2", 0, -0.35 * lag(0.12)); add2("tail_3", 0, -0.25 * lag(0.2) + 0.12 * math.sin(i * 1.1)); add2("tail_2", 2, 0.4 * math.sin(i * 0.9))
                ear(1.0); ox, oy = -fx * 0.16 * (1 - ss(u / 0.22)), -fy * 0.16 * (1 - ss(u / 0.22))                      # el peso atras de la anticipacion se suelta al lanzarse
            else:                                                                           # RECUPERACION: el golpe lo empuja hacia atras, aterriza amortiguando con las delanteras, se sacude (cabeza y cola) y vuelve a la postura de trote
                k_ = 1.0 - ss(u); land = math.sin(math.pi * min(1.0, u / 0.40)); fall = (1.0 - min(1.0, u / 0.30)) ** 2
                dz = 4 * 1.05 * (0.88 * 0.88) * (1 - 0.88) * 0 + 0.44 * fall - 0.12 * land * (1 - ss((u - 0.4) / 0.4))
                ox, oy = -fx * 0.20 * ss(u / 0.28) * (1 - ss((u - 0.28) / 0.6)), -fy * 0.20 * ss(u / 0.28) * (1 - ss((u - 0.28) / 0.6))
                both("thigh", 0, (-0.95 * (1 - ss(u / 0.35)) + 0.45 * land) * 1.0); both("shin", 0, -0.45 * land - 0.10 * (1 - ss(u / 0.35))); both("foot", 0, 0.12 * (1 - ss(u / 0.35)) - 0.15 * land)
                both("front_thigh", 0, -1.40 * k_ * (1 - land * 0.4)); both("front_shoulder", 0, 1.00 * k_); both("front_shin", 0, -0.12 * k_ - 0.35 * land); both("front_foot", 0, -0.12 * k_)
                add2("spine_6", 0, -0.22 * land + 0.2 * k_); add2("spine_4", 0, 0.10 * k_ + 0.08 * land); add2("scull_1", 0, 0.32 * k_ + 0.1 * land)
                add2("scull_1", 2, 0.45 * math.sin(u * 15) * (1 - u) * ss(u / 0.25)); row["jaw_bot"][0] = -math.radians(25) * k_
                add2("tail_1", 0, -0.5 * k_); add2("tail_2", 2, 0.55 * math.sin(u * 13) * (1 - 0.6 * u)); add2("tail_3", 2, 0.7 * math.sin(u * 13 - 0.8) * (1 - 0.6 * u)); ear(k_)
        else:
            if sp > 0.01 and math.dist((nx_, ny_), (x_, y_)) > 1e-4: tg = math.atan2(-(nx_ - x_), (ny_ - y_)); mx = 0.22
            else: tg = math.atan2(-(look[0] - x_), (look[1] - y_)); mx = 0.24
            e_ = norm(tg - r_); dr = max(-mx, min(mx, 0.4 * e_ if sp <= 0.01 else 0.5 * e_)); r_ += dr
        cum_t += abs(dr) if (sp <= 0.01 and not tag) else 0.0; rzs_j.append(r_)
        err_a = norm(math.atan2(-(look[0] - x_), (look[1] - y_)) - r_); lead = max(-1.0, min(1.0, err_a * 1.6))
        row["scull_1"][2] -= 0.55 * lead; row["spine_6"][2] -= 0.22 * lead; row["spine_4"][2] -= 0.14 * lead; row["spine_2"][2] -= 0.08 * lead
        row["spine_6"][0] += 0.02 * math.sin(i * 0.05); row["tail_2"][2] += 0.12 * math.sin(i * 0.07)
        if sp > 0.004 and not tag:                                                      # trote diagonal (mismas formulas que compose_parte2, TROTE DE JERRY)
            ph_g += 2 * math.pi * sp / 1.9; w = ss((sp - 0.004) / 0.03); a = min(1.3, 0.65 + sp / 0.1); ph = ph_g

            def addj(bn, ax, deg):
                row[bn][ax] += deg * D2R * w

            for sd, off in (("R", 0.0), ("L", math.pi)):
                addj(f"thigh.{sd}", 0, 38 * a * math.sin(ph + off)); addj(f"shin.{sd}", 0, -34 * a * max(0.0, math.sin(ph + off + 0.5))); addj(f"foot.{sd}", 0, -10 * a * max(0.0, math.sin(ph + off + 0.5)))
                addj(f"front_thigh.{sd}", 0, -36 * a * math.sin(ph + off)); addj(f"front_shin.{sd}", 0, -32 * a * (0.5 + 0.5 * math.sin(ph + off + 0.5)))
                addj(f"front_shoulder.{sd}", 0, 16 * a * math.sin(ph + off + 0.6)); addj(f"front_foot.{sd}", 0, -18 * a * max(0.0, math.sin(ph + off + 0.5)))
                addj(f"front_toe.{sd}", 0, -12 * a * max(0.0, math.sin(ph + off + 0.8))); addj(f"toe.{sd}", 0, -10 * a * max(0.0, math.sin(ph + off + 0.8)))
            addj("spine_6", 0, 3 * a * math.sin(2 * ph + 0.4)); addj("spine_4", 0, -2.5 * a * math.sin(2 * ph + 0.4)); addj("scull_1", 0, 2.5 * a * math.sin(2 * ph + 1.2))
            addj("tail_1", 2, 10 * a * math.sin(ph)); addj("tail_2", 2, 12 * a * math.sin(ph - 0.5)); addj("tail_3", 2, 14 * a * math.sin(ph - 1.0))
        wt = ss((abs(dr) - 0.01) / 0.05) if (sp <= 0.01 and not tag) else 0.0
        if wt > 0.001:                                                                  # giro en el sitio: pasitos de pivote (como el giro de la parte 2)
            ph = cum_t * 2 * math.pi / 1.1
            for sd, off in (("R", 0.0), ("L", math.pi)):
                fl = max(0.0, math.sin(ph + off + 0.5))
                addr(f"thigh.{sd}", 0, 0.55 * wt * math.sin(ph + off)); addr(f"shin.{sd}", 0, -0.5 * wt * fl); addr(f"foot.{sd}", 0, -0.15 * wt * fl)
                addr(f"front_thigh.{sd}", 0, -0.5 * wt * math.sin(ph + off)); addr(f"front_shin.{sd}", 0, -0.45 * wt * (0.5 + 0.5 * math.sin(ph + off + 0.5)))
                addr(f"front_foot.{sd}", 0, -0.25 * wt * fl); addr(f"front_toe.{sd}", 0, -0.15 * wt * fl)
        rows_j.append(row); dzs.append(dz); offs.append((ox, oy))
    for i in range(n_add):
        k = N0 + i; w0 = ss(i / 8.0)
        for b in JB:
            for a in range(3):
                old = JB[b]["rotation_euler"][a][N0 - 1]; JB[b]["rotation_euler"][a][k] = round(old + (rows_j[i][b][a] - old) * w0, 5)
        jl[0][k] = round(JT[i][0] + offs[i][0], 5); jl[1][k] = round(JT[i][1] + offs[i][1], 5); jl[2][k] = round(jz + dzs[i], 5); jr[2][k] = round(rzs_j[i], 5)
    for i in range(N0 + 1, N2): jr[2][i] = jr[2][i - 1] + norm(jr[2][i] - jr[2][i - 1])
    print("Jerry: golpes en f%s; entra al refugio en f%d; avisos de tiempo: %s" % ([e["frame_golpe"] for e in EV], N0 + 1 + i_in, jwarn))
    carpeta = os.path.join(BASE, "jerry/refinar/animaciones_ia/parte2_jerry_refugio"); os.makedirs(carpeta, exist_ok=True)
    json.dump(oj, open(os.path.join(carpeta, "parte2_jerry_refugio.animacion.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump({"fuente": "bloque_de_tablones_de_roble.blend (objeto oak_planks, 1 m, origen en la base)", "refugio": "4x4 (interior 2x2) con muros de 3 + techo, sin puertas al terminar; Jerry entra por un hueco antes de cerrarlo", "N": N2, "bloques": blocks},
              open(os.path.join(BASE, "alfred/refinar/docs/parte2/refugio_bloques.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
