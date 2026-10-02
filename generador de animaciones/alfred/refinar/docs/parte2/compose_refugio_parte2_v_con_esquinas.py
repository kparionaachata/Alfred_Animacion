"""Parte 2 - Alfred construye un REFUGIO de 4x4 bloques + techo tras descansar (pedido de Kebyn), con el principio de 'Crear pared NxN bloques':
Alfred queda fijo en un punto 1 m detras de cada celda y repite el ciclo agachar->colocar->parar (KEYFRAMES_COLOCAR_MESA_CRAFTEO, el mismo del add-on,
reescalado a FPB frames); el bloque aparece (oculto hasta ese frame) cuando el cuerpo esta agachado (frame MID del ciclo). Entre puntos camina por fuera del refugio.
Extiende los artefactos de la parte 2 (no los modifica): lee parte2_alfred_nada_y_sube / parte2_jerry_nada_y_sube (1600 f) y escribe
parte2_alfred_refugio / parte2_jerry_refugio (N2 f) + refugio_bloques.json (coordenada y frame de aparicion de cada bloque).
Ejecutar DESPUES de compose_parte2.py:  python alfred/refinar/docs/parte2/compose_refugio_parte2.py   (desde 'generador de animaciones')
"""
import ast, copy, json, math, os

BASE = "generador de animaciones" if os.path.isdir("generador de animaciones") else "."
N0 = 1600
FPB = 24                                     # frames por bloque (el ciclo base del add-on dura 30)
RAMP = 8
SPEED = 0.07                                 # m/f al caminar
TURN = 0.16                                  # rad/f maximo al girar caminando
D2R = math.pi / 180.0
INT_X = [-96.5, -95.5]                      # interior 2x2 (centros de celda): contiene el descanso de Alfred (-96.5,-109.5); el refugio completo es 4x4 (x -97.5..-94.5, y -110.5..-107.5)
INT_Y = [-109.5, -108.5]
JERRY0 = (-95.7, -107.5)                     # Jerry empieza en la celda norte del anillo, que queda como hueco hasta que entra
JERRY_FUERA = (-95.5, -105.5)                # sale a mirar construir desde fuera
JERRY_FIN = (-96.5, -108.5)                  # celda NW del interior: donde se queda al entrar
Z0 = 14.0
LAYERS = 4                                   # capas 0-2 = paredes (3 de alto), capa 3 = techo
JW = 80                                      # frames que Alfred espera mientras Jerry entra por el hueco
RELLENO = {(-97.5, -110.5): -1}              # esa celda del anillo esta 1 m mas baja (z=13): capa extra de relleno


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


def ciclo_colocar():
    """KEYFRAMES_COLOCAR_MESA_CRAFTEO (0..15 + vuelta smoothstep 16..29, igual que _build_colocar_mesa_crafteo_keyframes) leido sin importar el add-on."""
    src = open(os.path.join(BASE, "alfred/refinar/alfred_animation_studio/generate_slots_alfred.py"), encoding="utf-8").read()
    kf = None
    for nd in ast.parse(src).body:
        if isinstance(nd, ast.Assign) and getattr(nd.targets[0], "id", "") == "KEYFRAMES_COLOCAR_MESA_CRAFTEO": kf = ast.literal_eval(nd.value)
    out = {}
    for bone, fr in kf.items():
        seq = [fr[i] for i in range(16)]
        for j in range(1, 15):
            t = j / 14.0; tt = t * t * (3 - 2 * t); seq.append(tuple(fr[15][k] + (fr[0][k] - fr[15][k]) * tt for k in range(3)))
        out[bone] = seq
    return out


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
    for c, dirs in ((SW_, ("S", "W", "SW")), (NW_, ("N", "W", "NW")), (SE_, ("S", "E", "SE")), ("WAIT", ()), (NE_, ("E", "NE", "N"))):
        if c == "WAIT":
            P.append(("WAIT",)); continue
        for dn in dirs:
            dx, dy, rz = DIRS[dn]; dist = math.hypot(dx, dy); tc = (c[0] + dx, c[1] + dy)
            for ly in ([RELLENO[tc]] if tc in RELLENO else []) + list(range(LAYERS)):
                P.append((tc, ly, (c[0], c[1], rz), dist))
    for st, tg, rz in ((SE_, SW_, math.pi / 2), (SE_, NE_, 0.0), (SW_, SE_, -math.pi / 2), (SW_, NW_, 0.0)):    # techo del interior
        P.append((tg, 3, (st[0], st[1], rz), 1.0))
    return P


def main():
    A = load(art("parte2_alfred_nada_y_sube", "alfred")); J = load(art("parte2_jerry_nada_y_sube", "jerry")); TR = load(art("parte2_alfred_tramo_tierra", "alfred"))
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
    hold(40, rest)                                                                      # sigue descansando mientras Jerry termina de hablar
    for u in range(1, 31):                                                              # se incorpora
        w = ss(u / 30.0); push(mixrow(rest, stand, w), pos[0], pos[1], loc[2][0] + (Z0 - loc[2][0]) * w, cur["rz"])
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
            rem = total - s; vt = min(SPEED, math.sqrt(2 * 0.006 * rem) + 0.01); v += max(-0.006, min(0.004, vt - v)); v = max(0.012, v); s = min(total, s + v)
            q = next((i for i in range(1, len(cum)) if cum[i] >= s - 1e-9), len(cum) - 1); t = (s - cum[q - 1]) / max(cum[q] - cum[q - 1], 1e-9)
            pos[0] = pts[q - 1][0] + (pts[q][0] - pts[q - 1][0]) * t; pos[1] = pts[q - 1][1] + (pts[q][1] - pts[q - 1][1]) * t
            hd = math.atan2(-(pts[q][0] - pts[q - 1][0]), (pts[q][1] - pts[q - 1][1]))
            cur["rz"] += max(-TURN, min(TURN, norm(hd - cur["rz"])))
            cur["ph"] += 0.6 * v / SPEED
            push(mixrow(stand, row_at(RT, 130 + (cur["ph"] % 11.0)), ss(v / 0.05)), pos[0], pos[1], Z0, cur["rz"])

    def turn(rz_t, n=10):
        r0 = cur["rz"]; d = norm(rz_t - r0)
        if abs(d) < 0.02: return
        for u in range(1, n + 1): push(stand, pos[0], pos[1], Z0, r0 + d * ss(u / n))
        cur["rz"] = r0 + d

    def place(cell, ly, dist=1.0):
        k0 = 1601 + len(rows); mid = round(23 * 15 / 29.0)
        for q in range(FPB):
            f = q * 29.0 / (FPB - 1); i0 = min(28, int(f)); w = f - i0
            r = {b: (list(stand[b]) if b not in CY else [CY[b][i0][a] + (CY[b][i0 + 1][a] - CY[b][i0][a]) * w for a in range(3)]) for b in bones}
            push(r, pos[0], pos[1], Z0, cur["rz"])
        blocks.append({"x": cell[0], "y": cell[1], "z": Z0 + ly, "capa": ly, "frame": k0 + mid, "alcance": round(dist, 3)})

    estado = None; k_wait = None
    for it in plan():
        if it[0] == "WAIT":
            k_wait = len(rows); hold(JW, stand); continue
        cell, ly, (sx, sy, srz), dist = it
        if (sx, sy) != estado:
            walk([(pos[0], pos[1]), (sx, sy)]); estado = (sx, sy)
        turn(srz)
        place(cell, ly, dist)
    turn(0.0, 16); hold(60, stand)                                                      # sellado dentro: mira a Jerry (celda norte)
    n_add = len(rows); N2 = N0 + n_add
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

    # ---------------------------------------------------------------- Jerry: mira construir desde fuera, entra por el hueco norte cuando Alfred espera, y se queda dentro
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
    jz = val(jl[2], N0 - 1); jrz = val(jr[2], N0 - 1); jp = [JERRY0[0], JERRY0[1]]
    base = {b: [JB[b]["rotation_euler"][a][N0 - 1] for a in range(3)] for b in JB}; base["jaw_bot"][0] = 0.0
    segs = [("hold", 100), ("walk", [JERRY0, JERRY_FUERA]), ("hold_to", k_wait + 4), ("walk", [JERRY_FUERA, (JERRY_FUERA[0], -107.0), (JERRY_FUERA[0], -108.5), JERRY_FIN]), ("hold_to", n_add)]
    JT = []; JV = []

    def jwalk(pts, vmax=0.10):                                                          # posicion y velocidad por frame (mismo perfil que Alfred); el rumbo se calcula despues
        cum = [0.0]
        for a_, b_ in zip(pts, pts[1:]): cum.append(cum[-1] + math.dist(a_, b_))
        sd = 0.0; v = 0.0; tot = cum[-1]
        while tot - sd > 1e-3:
            rem = tot - sd; vt = min(vmax, math.sqrt(2 * 0.006 * rem) + 0.01); v += max(-0.006, min(0.006, vt - v)); v = max(0.012, v); sd = min(tot, sd + v)
            q = next((i for i in range(1, len(cum)) if cum[i] >= sd - 1e-9), len(cum) - 1); t = (sd - cum[q - 1]) / max(cum[q] - cum[q - 1], 1e-9)
            jp[0] = pts[q - 1][0] + (pts[q][0] - pts[q - 1][0]) * t; jp[1] = pts[q - 1][1] + (pts[q][1] - pts[q - 1][1]) * t
            JT.append((jp[0], jp[1])); JV.append(v)

    for kind, arg in segs:
        if kind == "hold":
            for _ in range(arg): JT.append((jp[0], jp[1])); JV.append(0.0)
        elif kind == "hold_to":
            while len(JT) < arg: JT.append((jp[0], jp[1])); JV.append(0.0)
        else:
            jwalk(arg)
    JT = JT[:n_add]; JV = JV[:n_add]
    # rumbo por frame: en marcha sigue la trayectoria; parado mira a Alfred con giro limitado y rapido
    rzs_j = []; r_ = jrz; ph_g = 0.0; cum_t = 0.0; rows_j = []
    for i in range(n_add):
        x_, y_ = JT[i]; sp = JV[i]; nx_, ny_ = JT[min(i + 1, n_add - 1)]; ax_, ay_ = locs[i][0], locs[i][1]
        if sp > 0.01 and math.dist((nx_, ny_), (x_, y_)) > 1e-4: tg = math.atan2(-(nx_ - x_), (ny_ - y_)); mx = 0.22
        else: tg = math.atan2(-(ax_ - x_), (ay_ - y_)); mx = 0.24
        e_ = norm(tg - r_); dr = max(-mx, min(mx, 0.4 * e_ if sp <= 0.01 else 0.5 * e_)); r_ += dr; cum_t += abs(dr) if sp <= 0.01 else 0.0; rzs_j.append(r_)
        err_a = norm(math.atan2(-(ax_ - x_), (ay_ - y_)) - r_); lead = max(-1.0, min(1.0, err_a * 1.6))
        row = {b: list(v_) for b, v_ in base.items()}

        def addr(bn, ax, rad):
            row[bn][ax] += rad

        row["scull_1"][2] -= 0.55 * lead; row["spine_6"][2] -= 0.22 * lead; row["spine_4"][2] -= 0.14 * lead; row["spine_2"][2] -= 0.08 * lead
        row["spine_6"][0] += 0.02 * math.sin(i * 0.05); row["tail_2"][2] += 0.12 * math.sin(i * 0.07)
        if sp > 0.004:                                                                  # trote diagonal (mismas formulas que compose_parte2, 'TROTE DE JERRY')
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
        wt = ss((abs(dr) - 0.01) / 0.05) if sp <= 0.01 else 0.0
        if wt > 0.001:                                                                  # giro en el sitio: pasitos de pivote (como el giro de la parte 2)
            ph = cum_t * 2 * math.pi / 1.1
            for sd, off in (("R", 0.0), ("L", math.pi)):
                fl = max(0.0, math.sin(ph + off + 0.5))
                addr(f"thigh.{sd}", 0, 0.55 * wt * math.sin(ph + off)); addr(f"shin.{sd}", 0, -0.5 * wt * fl); addr(f"foot.{sd}", 0, -0.15 * wt * fl)
                addr(f"front_thigh.{sd}", 0, -0.5 * wt * math.sin(ph + off)); addr(f"front_shin.{sd}", 0, -0.45 * wt * (0.5 + 0.5 * math.sin(ph + off + 0.5)))
                addr(f"front_foot.{sd}", 0, -0.25 * wt * fl); addr(f"front_toe.{sd}", 0, -0.15 * wt * fl)
        rows_j.append(row)
    for i in range(n_add):
        k = N0 + i; w0 = ss(i / 12.0)
        for b in JB:
            for a in range(3):
                old = JB[b]["rotation_euler"][a][N0 - 1]; JB[b]["rotation_euler"][a][k] = round(old + (rows_j[i][b][a] - old) * w0, 5)
        jl[0][k] = round(JT[i][0], 5); jl[1][k] = round(JT[i][1], 5); jl[2][k] = jz; jr[2][k] = round(rzs_j[i], 5)
    for i in range(N0 + 1, N2): jr[2][i] = jr[2][i - 1] + norm(jr[2][i] - jr[2][i - 1])
    i_in = next(i for i in range(k_wait, n_add) if math.dist(JT[i], JERRY_FIN) < 0.05)
    print("Jerry sale f%d, entra desde f%d y llega a %s en f%d (Alfred espera f%d-%d)" % (N0 + 100, N0 + k_wait + 4, [round(v, 2) for v in JT[i_in]], N0 + i_in, N0 + k_wait, N0 + k_wait + JW))
    carpeta = os.path.join(BASE, "jerry/refinar/animaciones_ia/parte2_jerry_refugio"); os.makedirs(carpeta, exist_ok=True)
    json.dump(oj, open(os.path.join(carpeta, "parte2_jerry_refugio.animacion.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump({"fuente": "bloque_de_roble.blend (objeto oak_planks, 1 m, origen en la base)", "refugio": "4x4 (interior 2x2) con muros de 3 + techo, sin puertas al terminar; Jerry entra por un hueco antes de cerrarlo", "N": N2, "bloques": blocks},
              open(os.path.join(BASE, "alfred/refinar/docs/parte2/refugio_bloques.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
