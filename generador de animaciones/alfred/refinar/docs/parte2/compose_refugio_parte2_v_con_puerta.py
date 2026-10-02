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
FOOT_X = [-93.5, -92.5, -91.5, -90.5]        # centros de celda del refugio (4x4)
FOOT_Y = [-108.5, -107.5, -106.5, -105.5]
Z0 = 14.0
LAYERS = 4                                   # capas 0-2 = paredes (3 de alto), capa 3 = techo
DOOR = (-92.5, -108.5)                       # hueco de la puerta (capas 0 y 1) en el muro sur


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


# ----------------------------------------------------------------------------------------------- plan de bloques y estaciones
def estacion(cx, cy):
    """(x, y, rz) donde se para Alfred para colocar la celda (cx, cy): 1 m por fuera del muro, de frente a el (adelante = (-sin rz, cos rz))."""
    if cy == FOOT_Y[0]: return cx, cy - 1.0, 0.0
    if cx == FOOT_X[-1]: return cx + 1.0, cy, math.pi / 2
    if cy == FOOT_Y[-1]: return cx, cy + 1.0, math.pi
    return cx - 1.0, cy, -math.pi / 2


def plan():
    P = []                                                        # (celda, capa, estacion)
    cols = ([(x, FOOT_Y[0]) for x in FOOT_X] + [(FOOT_X[-1], y) for y in FOOT_Y[1:3]] + [(x, FOOT_Y[-1]) for x in reversed(FOOT_X)] + [(FOOT_X[0], y) for y in (FOOT_Y[2], FOOT_Y[1])])
    for cx, cy in cols:
        for ly in range(LAYERS):
            if (cx, cy) == DOOR and ly < 2: continue
            P.append(((cx, cy), ly, estacion(cx, cy)))
    # techo interior (2x2) desde dentro; la puerta es el hueco del muro sur
    P += [((-91.5, -107.5), 3, (-92.5, -107.5, -math.pi / 2)), ((-91.5, -106.5), 3, (-92.5, -106.5, -math.pi / 2)),
          ((-92.5, -106.5), 3, (-91.5, -106.5, math.pi / 2)), ((-92.5, -107.5), 3, (-92.5, -108.5, 0.0))]
    return P


RING = [(-94.5, -109.5), (-89.5, -109.5), (-89.5, -104.5), (-94.5, -104.5)]          # anillo por fuera del refugio, sentido antihorario


def ring_t(p):
    d = 0.0
    for a, b in zip(RING, RING[1:] + RING[:1]):
        L = math.dist(a, b)
        if abs((p[0] - a[0]) * (b[1] - a[1]) - (p[1] - a[1]) * (b[0] - a[0])) < 1e-6 and min(a[0], b[0]) - 1e-6 <= p[0] <= max(a[0], b[0]) + 1e-6 and min(a[1], b[1]) - 1e-6 <= p[1] <= max(a[1], b[1]) + 1e-6:
            return d + math.dist(a, p)
        d += L
    return None


def ring_pt(t):
    per = sum(math.dist(a, b) for a, b in zip(RING, RING[1:] + RING[:1])); t %= per
    for a, b in zip(RING, RING[1:] + RING[:1]):
        L = math.dist(a, b)
        if t <= L: return (a[0] + (b[0] - a[0]) * t / L, a[1] + (b[1] - a[1]) * t / L)
        t -= L


def ring_path(a, b):
    ta, tb = ring_t(a), ring_t(b); per = sum(math.dist(p, q) for p, q in zip(RING, RING[1:] + RING[:1]))
    if tb < ta - 1e-6: tb += per
    pts = [a]; corners = [(sum(math.dist(RING[j], RING[(j + 1) % 4]) for j in range(i)), RING[i]) for i in range(4)]
    for off in (0.0, per):
        for tc, c in corners:
            if ta + 1e-6 < tc + off < tb - 1e-6: pts.append(c)
    return pts + [b]


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

    def place(cell, ly):
        k0 = 1601 + len(rows); mid = round(23 * 15 / 29.0)
        for q in range(FPB):
            f = q * 29.0 / (FPB - 1); i0 = min(28, int(f)); w = f - i0
            r = {b: (list(stand[b]) if b not in CY else [CY[b][i0][a] + (CY[b][i0 + 1][a] - CY[b][i0][a]) * w for a in range(3)]) for b in bones}
            push(r, pos[0], pos[1], Z0, cur["rz"])
        blocks.append({"x": cell[0], "y": cell[1], "z": Z0 + ly, "capa": ly, "frame": k0 + mid})

    estado = None
    for cell, ly, (sx, sy, srz) in plan():
        if (sx, sy) != estado:
            here = (pos[0], pos[1])
            if estado is None: path = [here, (-94.5, -109.5), (sx, sy)] if ring_t((sx, sy)) is not None else [here, (sx, sy)]
            elif ring_t(here) is not None and ring_t((sx, sy)) is not None: path = ring_path(here, (sx, sy))
            elif ring_t(here) is None and ring_t((sx, sy)) is None: path = [here, (sx, sy)]
            elif ring_t(here) is None:                                                   # sale del interior por la puerta
                path = [here, (-92.5, -107.5), (-92.5, -109.5)]
                if ring_t((sx, sy)) is not None and (sx, sy) != (-92.5, -109.5): path = path[:-1] + ring_path((-92.5, -109.5), (sx, sy))
            else:                                                                        # entra al interior por la puerta
                path = ring_path(here, (-92.5, -109.5)) + [(-92.5, -108.5), (sx, sy)]
            walk(path); estado = (sx, sy)
        turn(srz)
        place(cell, ly)
    walk([(pos[0], pos[1]), (-92.5, -107.5), (-92.0, -107.0)]) if pos[1] < -108 else None   # termina dentro del refugio
    turn(math.pi / 2, 16); hold(60, stand)
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

    # ---------------------------------------------------------------- Jerry: se queda, calla (mandibula cerrada) y mira a Alfred mientras construye
    oj = copy.deepcopy(J); oj["nombre"] = "parte2_jerry_refugio"; oj["frame_fin"] = N2
    ext(oj["ojos"], N0, n_add); ext(oj["armature"], N0, n_add); ext(oj["root"], N0, n_add)
    jl = oj["root"]["canales"]["location"]; jr = oj["root"]["canales"]["rotation_euler"]
    jx, jy = val(jl[0], N0 - 1), val(jl[1], N0 - 1); jrz = val(jr[2], N0 - 1)
    for a in range(3):
        if not isinstance(jl[a], list): jl[a] = [jl[a]] * N2
    if not isinstance(jr[2], list): jr[2] = [jr[2]] * N2
    JB = oj["armature"]["bones"]
    for b in JB:
        for a in range(3):
            if isinstance(JB[b]["rotation_euler"][a], list) and len(JB[b]["rotation_euler"][a]) != N2: JB[b]["rotation_euler"][a] = JB[b]["rotation_euler"][a] + [JB[b]["rotation_euler"][a][-1]] * (N2 - len(JB[b]["rotation_euler"][a]))
    for i in range(n_add):
        k = N0 + i; w = ss(i / 12.0); br = math.sin(i * 0.05)
        ax, ay = locs[i][0], locs[i][1]; err = norm(math.atan2(-(ax - jx), (ay - jy)) - jrz); head = max(-0.9, min(0.9, err)) * 0.8
        j0 = JB["jaw_bot"]["rotation_euler"][0]; j0[k] = j0[N0 - 1] * (1 - w)
        z0 = JB["scull_1"]["rotation_euler"][2]; z0[k] = z0[N0 - 1] + (-head - z0[N0 - 1]) * w
        s6 = JB["spine_6"]["rotation_euler"][0]; s6[k] = s6[N0 - 1] + 0.02 * br
    carpeta = os.path.join(BASE, "jerry/refinar/animaciones_ia/parte2_jerry_refugio"); os.makedirs(carpeta, exist_ok=True)
    json.dump(oj, open(os.path.join(carpeta, "parte2_jerry_refugio.animacion.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump({"fuente": "bloque_de_roble.blend (objeto oak_planks, 1 m, origen en la base)", "refugio": "4x4 + techo, 3 de alto, puerta en muro sur", "N": N2, "bloques": blocks},
              open(os.path.join(BASE, "alfred/refinar/docs/parte2/refugio_bloques.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
