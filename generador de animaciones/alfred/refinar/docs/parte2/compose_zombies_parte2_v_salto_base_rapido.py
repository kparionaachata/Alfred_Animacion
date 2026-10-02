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
N = 1600
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


KFJ = _kf_salto(); JF = 12; JLEAD = 0.45            # 12 frames de salto; despega 0.45 m antes del borde y cae 0.45 m despues
SUBE_Y = {1: -104.6, 2: -106.2, 3: -103.3, 5: -107.2, 4: -105.4}                     # carril propio de cada zombie en la escalera (ya no suben en fila india)
FIN_P = {1: (-96.0, -103.4), 2: (-95.2, -105.6), 3: (-96.8, -104.6), 5: (-94.6, -107.4), 4: (-95.8, -106.4)}
GAP = 1.4


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


def main():
    data = {n: load(n) for n in ZOM}
    routes = {}
    for n, (v, lane) in ZOM.items():
        D = data[n]; i = D["frame_fin"] - 1
        st = (val(D["root"]["canales"]["location"][0], i), val(D["root"]["canales"]["location"][1], i))
        # canal hasta el punto de espera y luego en diagonal por el agua al pie de la escalera
        sy = SUBE_Y[n]; fe = FIN_P[n]
        pts = resample([st, (-97.0, lane), (HOLD_X, lane), (-84.0, -119.6), (-82.5, -117.5), (-82.5, sy), (-83.5, sy), (-89.5, sy), (-91.5, sy), fe])   # por el agua, sin cruzar la orilla de x=-84
        cum = [0.0]
        for a, b in zip(pts, pts[1:]): cum.append(cum[-1] + math.dist(a, b))
        s_hold = next(c for p_, c in zip(pts, cum) if p_[0] >= HOLD_X - 1e-6 and abs(p_[1] - lane) < 0.06)
        routes[n] = (pts, cum, s_hold)
    S = {n: [0.0] * N for n in ZOM}; V = {n: [0.0] * N for n in ZOM}; v0 = {}
    for n in ZOM:
        D = data[n]; i = D["frame_fin"] - 1; L = D["root"]["canales"]["location"]
        v0[n] = math.hypot(val(L[0], i) - val(L[0], i - 5), val(L[1], i) - val(L[1], i - 5)) / 5.0
    for k in range(1, N):
        for n in ORDEN:
            v_t = ZOM[n][0]
            v = v_t                                              # velocidad CONSTANTE desde el primer frame hasta el ultimo (sin aceleraciones)
            s = S[n][k - 1] + v
            V[n][k] = s - S[n][k - 1]; S[n][k] = s
    for n in ZOM:
        D = data[n]; pts, cum, s_hold = routes[n]; bones = list(D["armature"]["bones"]); start = last_row(D)
        Lr = D["root"]["canales"]["location"]; Rr = D["root"]["canales"]["rotation_euler"]
        rz_prev = val(Rr[2], D["frame_fin"] - 1); z0 = val(Lr[2], D["frame_fin"] - 1)

        def pos_at(s):
            s = min(s, cum[-1] - 1e-6)
            j = max(1, next((q for q in range(1, len(cum)) if cum[q] >= s), len(cum) - 1)); t = (s - cum[j - 1]) / max(cum[j] - cum[j - 1], 1e-9)
            return (pts[j - 1][0] + (pts[j][0] - pts[j - 1][0]) * t, pts[j - 1][1] + (pts[j][1] - pts[j - 1][1]) * t)

        # --- escalones: cada subida de bloque (>0.3 m) se hace con la animacion base saltar_subir (12 f) entre coordenadas p0 (antes del borde) y p1 (sobre el bloque)
        edges = []
        for i_ in range(len(pts) - 1):
            h0_, h1_ = min(height(*pts[i_]), 14.0), min(height(pts[i_ + 1][0], pts[i_ + 1][1]), 14.0)
            if h1_ - h0_ > 0.3 and h0_ >= 6.9: edges.append((cum[i_] - JLEAD, h0_, h1_))
        S[n] = [0.0] * N; V[n] = [0.0] * N; jw = [0] * N; jz = [None] * N; ej = list(edges); kk = 1
        while kk < N:
            if ej and S[n][kk - 1] >= ej[0][0] and kk + JF < N:
                sj, h0_, h1_ = ej.pop(0); sj = S[n][kk - 1]; L_ = 2 * JLEAD
                for q in range(JF):                                                          # frame q del salto: horizontal ease-in, vertical ease-out (como el slot base)
                    t = (q + 1) / JF; S[n][kk + q] = sj + L_ * t * t; V[n][kk + q] = S[n][kk + q] - S[n][kk + q - 1]
                    jw[kk + q] = q + 1; jz[kk + q] = h0_ + (h1_ - h0_) * (1 - (1 - t) * (1 - t))
                kk += JF
            else:
                S[n][kk] = S[n][kk - 1] + ZOM[n][0]; V[n][kk] = ZOM[n][0]; kk += 1
        xs, ys = [], []
        for k in range(N):
            x, y = pos_at(S[n][k]); xs.append(x); ys.append(y)
        hs = [min(height(xs[k], ys[k]), 14.0) if jz[k] is None else jz[k] for k in range(N)]
        for k in range(N):                                                                  # tras el salto aterriza exacto en el bloque; entre saltos sigue el terreno
            if jz[k] is None and k > 0 and jw[k - 1] == JF: hs[k] = min(height(xs[k], ys[k]), 14.0)
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
        zs = [zs[k] + (z0 - zs[0]) * (1 - ss(k / 30.0)) for k in range(N)]
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
                        q_ = jw[k] - 1 if jw[k] else (JF - 1 if k > 0 and jw[k - 1] == JF else 0); jr = KFJ[kb_][q_]
                        wj = 1.0 if jw[k] else 0.5; r_ = [r_[a] + (jr[a] - r_[a]) * wj for a in range(3)]
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


if __name__ == "__main__":
    main()
