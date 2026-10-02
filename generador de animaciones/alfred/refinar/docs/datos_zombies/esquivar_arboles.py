"""Empuja el root de un artefacto zombie fuera de las celdas con arbol (grilla del terreno) con fundido suave.
Uso: python esquivar_arboles.py 3 4 5      (edita el .animacion.json de cada zombie; hace copia .antes_arboles.json)
Celdas de arbol (bloqueadas, Spruce_Leaves/Log a altura del cuerpo), de la grilla medida por raycast: ver BLOQ."""
import json, math, shutil, sys
import os
PUNTOS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "arboles_puntos.json")))  # puntos (paso 0.5) a <0.6 m de un tronco/hojas, medidos por raycast horizontal
_BLOQ_ANTIGUO = [(-122,-102),(-122,-101),(-122,-100),(-121,-116),(-120,-118),(-120,-115),(-119,-116),(-119,-115),(-119,-114),
        (-118,-117),(-118,-116),(-118,-115),(-118,-106),(-115,-95),(-114,-96),(-114,-94),(-113,-95),(-121,-118)]
CLEAR, WIN, LAST = 0.5, 18, 600
def nearest(x, y):
    best = None
    for qx, qy in PUNTOS:
        d = math.hypot(x - qx, y - qy)
        if best is None or d < best[0]: best = (d, qx, qy, qx, qy)
    return best
def run(n):
    p = f"zombie_{n}/refinar/animaciones_ia/zombie_{n}_camina_acantilado/zombie_{n}_camina_acantilado.animacion.json"
    ant = p.replace(".animacion.json", ".antes_arboles.json")
    if not os.path.exists(ant): shutil.copy(p, ant)
    else: shutil.copy(ant, p)   # siempre parte de la version previa a esquivar
    d = json.load(open(p, encoding="utf-8")); loc = d["root"]["canales"]["location"]; N = d["frame_fin"]
    X = list(loc[0]); Y = list(loc[1]); cx = [0.0] * N; cy = [0.0] * N
    for _ in range(6):
        for i in range(LAST):
            x, y = X[i] + cx[i], Y[i] + cy[i]
            if y < -118.5: continue
            dd, qx, qy, ccx, ccy = nearest(x, y)
            if dd < CLEAR:
                if dd < 1e-6: vx, vy = x - ccx, y - ccy
                else: vx, vy = x - qx, y - qy
                m = math.hypot(vx, vy) or 1.0
                push = CLEAR - dd + (0.5 if dd < 1e-6 else 0)
                cx[i] += vx / m * push; cy[i] += vy / m * push
        nx, ny = [0.0] * N, [0.0] * N
        for i in range(N):
            a, b = max(0, i - WIN), min(N, i + WIN + 1)
            # solo suaviza dentro del tramo corregido; el fundido en los bordes evita saltos
            nx[i] = sum(cx[a:b]) / (b - a); ny[i] = sum(cy[a:b]) / (b - a)
        cx = [max(nx[i], cx[i]) if abs(cx[i]) > abs(nx[i]) and cx[i] * nx[i] > 0 else nx[i] if abs(nx[i]) >= abs(cx[i]) else cx[i] for i in range(N)]
        cy = [max(ny[i], cy[i]) if abs(cy[i]) > abs(ny[i]) and cy[i] * ny[i] > 0 else ny[i] if abs(ny[i]) >= abs(cy[i]) else cy[i] for i in range(N)]
    for i in range(N):
        X[i] = round(X[i] + cx[i], 5); Y[i] = round(Y[i] + cy[i], 5)
    loc[0], loc[1] = X, Y
    mn = min(nearest(X[i], Y[i])[0] for i in range(LAST) if Y[i] > -118.5)
    salto = max(math.hypot(X[i+1]-X[i], Y[i+1]-Y[i]) for i in range(LAST))
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"zombie_{n}: distancia minima a arbol {mn:.2f} m, paso max {salto:.2f} m/f, correccion max {max(math.hypot(a,b) for a,b in zip(cx,cy)):.2f} m")
for n in map(int, sys.argv[1:]): run(n)
