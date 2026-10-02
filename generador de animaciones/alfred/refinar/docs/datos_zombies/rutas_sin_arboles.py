"""Reemplaza la aproximacion (xy del root) de zombie_N por una ruta A* que evita troncos/hojas.
El avance en el tiempo se conserva: u(f) = arco_viejo(f)/arco_viejo(G), con G = fall_frame-40 (llegada al borde).
Uso: python rutas_sin_arboles.py 3 4 5   (parte de <nombre>.antes_arboles.json; escribe el .animacion.json)"""
import heapq, json, math, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PUNTOS = json.load(open(os.path.join(HERE, "arboles_puntos.json")))
BLK = {(round(x * 2), round(y * 2)) for x, y in PUNTOS}
FALL = {3: 650, 4: 673, 5: 708}
# Punto de caida en el BORDE del alcantilado (tope z=13 hasta y=-116.9; bloque de tierra al sur): cada zombie se para ahi y se deja caer.
EDGE = {3: (-112.0, -116.7), 4: (-115.6, -116.7), 5: (-113.4, -116.7)}
import sys as _s; _s.path.insert(0, HERE)
from derivar_zombie import CONFIG, frame_tau, walk_weight, smoothstep
def libre(c): return c not in BLK
def astar(s, g):
    op = [(0, s)]; cost = {s: 0}; par = {}
    while op:
        _, c = heapq.heappop(op)
        if c == g: break
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if not (dx or dy): continue
                n = (c[0] + dx, c[1] + dy)
                if not libre(n) or not (-250 <= n[0] <= -205 and -240 <= n[1] <= -180): continue
                nc = cost[c] + math.hypot(dx, dy)
                if nc < cost.get(n, 1e9):
                    cost[n] = nc; par[n] = c; heapq.heappush(op, (nc + math.hypot(g[0] - n[0], g[1] - n[1]), n))
    path = [g]
    while path[-1] != s: path.append(par[path[-1]])
    return [(a / 2, b / 2) for a, b in path[::-1]]
def libre_cerca(c):
    if libre(c): return c
    for r in range(1, 6):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if libre((c[0] + dx, c[1] + dy)): return (c[0] + dx, c[1] + dy)
def suavizar(pts, it=3):
    for _ in range(it):
        q = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            q += [(.75 * a[0] + .25 * b[0], .75 * a[1] + .25 * b[1]), (.25 * a[0] + .75 * b[0], .25 * a[1] + .75 * b[1])]
        pts = q + [pts[-1]]
    return pts
def run(n):
    p = f"zombie_{n}/refinar/animaciones_ia/zombie_{n}_camina_acantilado/zombie_{n}_camina_acantilado.animacion.json"
    ant = p.replace(".animacion.json", ".antes_arboles.json")
    if not os.path.exists(ant): shutil.copy(p, ant)
    d = json.load(open(ant, encoding="utf-8")); loc = d["root"]["canales"]["location"]; N = d["frame_fin"]
    X, Y = list(loc[0]), list(loc[1]); cfgz = CONFIG[n]
    FF = 553 + cfgz["delay"]; LF = FF + 30                       # inicio de la caida y aterrizaje
    Lx, Ly = X[LF - 1], Y[LF - 1]                                 # aterrizaje ya calculado
    G = next(f for f in range(1, N) if walk_weight(frame_tau(f, cfgz["delay"], cfgz["approach_speed"])) < 0.03 and f > 300)  # deja de caminar
    s = [0.0]
    for i in range(1, N): s.append(s[-1] + math.hypot(X[i] - X[i - 1], Y[i] - Y[i - 1]))
    st = libre_cerca((round(X[0] * 2), round(Y[0] * 2))); gl = libre_cerca((round(EDGE[n][0] * 2), round(Y[G] * 2 * 0 + EDGE[n][1] * 2)))
    ruta = suavizar([(X[0], Y[0])] + astar(st, gl)[1:-1] + [EDGE[n]])
    acc = [0.0]
    for a, b in zip(ruta, ruta[1:]): acc.append(acc[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    def en(u):
        t = u * acc[-1]; k = 0
        while k < len(acc) - 2 and acc[k + 1] < t: k += 1
        w = (t - acc[k]) / max(acc[k + 1] - acc[k], 1e-9); a, b = ruta[k], ruta[k + 1]
        return a[0] + (b[0] - a[0]) * w, a[1] + (b[1] - a[1]) * w
    for i in range(G + 1):
        u = s[i] / s[G] if s[G] > 0 else 1.0
        X[i], Y[i] = [round(v, 5) for v in en(min(1.0, u))]
    ex_, ey_ = EDGE[n]
    zz = loc[2]; FZ = next(f for f in range(300, N) if zz[f - 1] < 12.6)   # el cuerpo empieza a caer
    F0 = FZ - 22                                                            # sale del borde ANTES de perder altura (si no atraviesa el bloque)
    for i in range(G + 1, F0 - 1):                                          # parado en el borde
        X[i], Y[i] = round(ex_, 5), round(ey_, 5)
    zt, zb = max(zz[:LF]), zz[LF - 1]; mprev = 0.0                            # la salida horizontal va por delante de la caida vertical:
    for i in range(F0 - 1, LF):                                             # bloque de tierra (z13 hasta y=-116.9) y saliente de piedra (z8 hasta y=-118.3)
        q = max(0.0, min(1.0, (zt - zz[i]) / max(zt - zb, 1e-6)))
        mprev = max(mprev, q ** 0.55); m = 1.0 if i + 1 >= LF else mprev
        X[i] = round(ex_ + (Lx - ex_) * m, 5); Y[i] = round(ey_ + (Ly - ey_) * m, 5)
    loc[0], loc[1] = X, Y
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    md = min(min(math.hypot(X[i] - a / 2, Y[i] - b / 2) for a, b in BLK) for i in range(G + 1) if Y[i] > -118.5)
    paso = max(math.hypot(X[i + 1] - X[i], Y[i + 1] - Y[i]) for i in range(N - 1))
    print(f"zombie_{n}: ruta {len(ruta)} pts, arco viejo {s[G]:.1f} m -> nuevo {acc[-1]:.1f} m, dist minima a celda marcada {md:.2f} m, paso max {paso:.2f} m/f, borde ({ex_:.1f},{ey_:.1f}) llegada f{G}, caida f{FF}")
for n in map(int, sys.argv[1:]): run(n)
