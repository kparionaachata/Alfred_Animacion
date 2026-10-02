"""Orienta el root (rotation_euler Z) de un zombie hacia donde avanza (evita caminar de lado tras mover x,y).
Convencion del rig: delante = (-sin rz, cos rz)  ->  rz = atan2(-vx, vy). Solo actua donde hay avance (>0.02 m/f), con fundido y suavizado.
Uso: python orientar_al_avanzar.py 1 2 3 4 5   (respalda `<nombre>.antes_rumbo.json`, parte siempre de ese respaldo)"""
import json, math, os, shutil, sys
def wrap(a): return (a + math.pi) % (2 * math.pi) - math.pi
def box(v, w):
    n = len(v); out = []
    for i in range(n):
        a, b = max(0, i - w), min(n, i + w + 1); out.append(sum(v[a:b]) / (b - a))
    return out
def run(n):
    p = f"zombie_{n}/refinar/animaciones_ia/zombie_{n}_camina_acantilado/zombie_{n}_camina_acantilado.animacion.json"
    ant = p.replace(".animacion.json", ".antes_rumbo.json")
    if not os.path.exists(ant): shutil.copy(p, ant)
    d = json.load(open(ant, encoding="utf-8")); c = d["root"]["canales"]; N = d["frame_fin"]
    L = [list(a) if isinstance(a, list) else [a] * N for a in c["location"]]
    R = list(c["rotation_euler"][2]) if isinstance(c["rotation_euler"][2], list) else [c["rotation_euler"][2]] * N
    K = 4; spd = []; tgt = []
    for i in range(N):
        a, b = max(0, i - K), min(N - 1, i + K)
        vx = (L[0][b] - L[0][a]) / (b - a); vy = (L[1][b] - L[1][a]) / (b - a)
        spd.append(math.hypot(vx, vy)); tgt.append(math.atan2(-vx, vy) if math.hypot(vx, vy) > 0.02 else None)
    # rellenar huecos manteniendo el ultimo rumbo valido (y el primero hacia atras)
    last = next((t for t in tgt if t is not None), R[0])
    for i in range(N):
        if tgt[i] is None: tgt[i] = last
        else: last = tgt[i]
    un = [tgt[0]]
    for i in range(1, N): un.append(un[-1] + wrap(tgt[i] - un[-1]))
    un = box(box(un, 8), 8)
    w = box([min(1.0, max(0.0, (s - 0.006) / 0.012)) for s in spd], 4)
    new = [round(R[i] + wrap(un[i] - R[i]) * w[i], 5) for i in range(N)]
    # limite de velocidad de giro (rad/frame), sin dar saltos al cambiar de rumbo
    for i in range(1, N): new[i] = round(new[i - 1] + max(-0.09, min(0.09, wrap(new[i] - new[i - 1]))) if abs(wrap(new[i] - new[i - 1])) > 0.09 else new[i], 5)
    # continuidad: desenrollar respecto al valor anterior para no dar vueltas
    for i in range(1, N): new[i] = round(new[i - 1] + wrap(new[i] - new[i - 1]), 5)
    c["rotation_euler"][2] = new
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    paso = max(abs(new[i + 1] - new[i]) for i in range(N - 1))
    mal = sum(1 for i in range(1, N - 1) if spd[i] > 0.03 and abs(wrap(new[i] - math.atan2(-(L[0][min(N-1,i+K)]-L[0][max(0,i-K)]), L[1][min(N-1,i+K)]-L[1][max(0,i-K)]))) > 0.35)
    print(f"zombie_{n}: giro max {math.degrees(paso):.1f} grados/frame, frames de lado restantes {mal}")
for n in map(int, sys.argv[1:]): run(n)
