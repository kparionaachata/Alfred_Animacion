"""Parte 2 - CAMARA CINEMATOGRAFICA continua (una sola toma, sin cortes) enfocada en Alfred y Jerry de f1 a N (pedido de Kebyn). SOLO keyframes de la camara; no se renderiza nada.
Calcula, a partir de las posiciones reales de Alfred y Jerry en los artefactos (parte2_alfred_refugio / parte2_jerry_refugio), una trayectoria suave con "tomas" definidas por balizas
(frame, azimut, elevacion, distancia, focal, peso de Jerry en el encuadre, altura) y la escribe en `camara_parte2.json` (muestras cada STEP frames). La distancia se amplia sola para que
los DOS personajes quepan siempre en el encuadre segun la focal. `importar_camara.py` (se ejecuta en Blender) inserta los keyframes en `Camara_Cinematica` (su TRACK_TO apunta a `Cam_Foco`)
y `Cam_Foco` y ajusta con raycast las muestras donde algo tapa la vista o la camara queda dentro del terreno/arboles/bloques.
Uso (desde 'generador de animaciones'):  python alfred/refinar/docs/parte2/compose_camara_parte2.py
"""
import json, math, os

BASE = "generador de animaciones" if os.path.isdir("generador de animaciones") else "."
HERE = os.path.join(BASE, "alfred/refinar/docs/parte2")
STEP = 4
SENSOR = 36.0

# (frame, azimut deg [0 = camara al este de los sujetos, -90 = al sur, 180 = al oeste], elevacion deg, distancia base m, focal mm, peso de Jerry en el punto de mira (0 = Alfred, 1 = Jerry), altura extra del punto de mira m)
BALIZAS = [
    (1, -90, 6, 9, 28, 0.5, 0.2),          # f1-274 nadan hacia el este: travelling bajo desde el sur, que va pasando al frente
    (100, -75, 8, 8, 28, 0.5, 0.3),
    (200, -30, 10, 7, 26, 0.5, 0.3),
    (272, -45, 9, 6, 28, 0.5, 0.5),
    (310, -70, 10, 5.5, 32, 0.5, 0.8),     # f275-475 discuten la ruta: plano medio de los dos y orbita lenta con empuje en los gestos
    (350, -95, 12, 5, 35, 0.5, 0.9),
    (400, -70, 10, 4.2, 40, 0.5, 0.9),
    (440, -35, 10, 4.5, 35, 0.5, 0.8),
    (476, 5, 8, 5.5, 28, 0.5, 0.8),        # f476-540 miran atras y ven a los zombies: la camara pasa al este para ver sus caras y a los zombies detras
    (500, 15, 12, 7, 24, 0.5, 1.0),
    (535, 30, 20, 10, 24, 0.5, 0.8),
    (560, -90, 14, 9, 26, 0.5, 0.5),       # f540-706 nadan frenetico al norte: camara detras
    (690, -80, 12, 10, 26, 0.5, 0.5),
    (706, -20, 6, 9, 24, 0.5, 0.8),        # f706-810 suben la escalera: contrapicado desde el este (el sur es bosque que tapa)
    (790, -10, 6, 11, 24, 0.5, 1.0),
    (815, 5, 10, 13, 24, 0.5, 0.8),        # f810-1000 resbala, rueda y flota; Jerry mira desde arriba (camara sobre el agua, al este)
    (900, 10, 14, 15, 24, 0.5, 0.8),
    (1000, 10, 18, 15, 24, 0.5, 0.8),
    (1070, 0, 16, 13, 26, 0.5, 0.8),       # f1000-1100 despierta y ve a los zombies
    (1100, -10, 10, 11, 24, 0.5, 1.0),     # f1100-1227 vuelve a subir
    (1227, -20, 12, 9, 26, 0.5, 1.0),
    (1300, -170, 10, 7, 28, 0.5, 0.9),     # f1227-1349 camina agotado y Jerry corre a su lado: la camara pasa delante para verles las caras
    (1349, -200, 10, 6, 30, 0.5, 0.9),
    (1371, -215, 14, 3.5, 40, 0.5, 0.5),   # f1349-1391 coloca la antorcha: primer plano
    (1420, -230, 10, 4.5, 32, 0.5, 0.9),   # descanso y charla de Jerry
    (1470, -250, 40, 7, 28, 0.5, 1.2),     # f1461-1860 construyen el refugio: desde arriba (el interior sigue abierto) con orbita lenta; Jerry patrulla y empuja zombies fuera
    (1560, -300, 50, 9, 24, 0.5, 1.2),
    (1700, -380, 52, 10, 24, 0.5, 1.2),
    (1860, -460, 45, 10, 24, 0.5, 1.0),
    (1900, -480, 25, 8, 24, 0.8, 0.8),     # f1860+: el techo cubre a Alfred; la camara baja y sigue a Jerry y a los zombies que atacan los muros
    (2000, -540, 18, 9, 24, 0.9, 0.8),
    (2093, -600, 20, 11, 24, 0.5, 1.0),    # f2005+: Jerry tambien entra y el refugio queda sellado: el punto de mira pasa al refugio (ver SELLADO) y la camara orbita viendo a los zombies golpear los muros
    (2150, -660, 30, 13, 24, 0.5, 1.0),
]


def val(c, i):
    return c[i] if isinstance(c, list) else c


def cr(p0, p1, p2, p3, t):                                           # Catmull-Rom
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)


def interp(frames, vals, k):
    n = len(frames)
    if k <= frames[0]: return vals[0]
    if k >= frames[-1]: return vals[-1]
    i = next(q for q in range(1, n) if frames[q] >= k) - 1; t = (k - frames[i]) / float(frames[i + 1] - frames[i])
    p0 = vals[max(0, i - 1)]; p1 = vals[i]; p2 = vals[i + 1]; p3 = vals[min(n - 1, i + 2)]
    out = cr(p0, p1, p2, p3, t)
    return min(max(out, min(p1, p2) - 0.15 * abs(p2 - p1)), max(p1, p2) + 0.15 * abs(p2 - p1))     # sin sobreimpulsos


def smooth(arr, w):
    n = len(arr); out = []
    for i in range(n):
        lo, hi = max(0, i - w), min(n, i + w + 1); out.append(sum(arr[lo:hi]) / (hi - lo))
    return out


def main():
    A = json.load(open(os.path.join(BASE, "alfred/refinar/animaciones_ia/parte2_alfred_refugio/parte2_alfred_refugio.animacion.json"), encoding="utf-8"))["root"]["canales"]["location"]
    J = json.load(open(os.path.join(BASE, "jerry/refinar/animaciones_ia/parte2_jerry_refugio/parte2_jerry_refugio.animacion.json"), encoding="utf-8"))["root"]["canales"]["location"]
    N = len(A[0]); fr = [b[0] for b in BALIZAS]; cols = list(zip(*BALIZAS))
    ks = list(range(1, N + 1, STEP))
    if ks[-1] != N: ks.append(N)
    az = [interp(fr, cols[1], k) for k in ks]; el = [interp(fr, cols[2], k) for k in ks]; dist = [interp(fr, cols[3], k) for k in ks]; lens = [interp(fr, cols[4], k) for k in ks]
    wj = [interp(fr, cols[5], k) for k in ks]; dz = [interp(fr, cols[6], k) for k in ks]
    tx, ty, tz, seps = [], [], [], []
    for q, k in enumerate(ks):
        a = (val(A[0], k - 1), val(A[1], k - 1), val(A[2], k - 1) + 0.9); j = (val(J[0], k - 1), val(J[1], k - 1), val(J[2], k - 1) + 0.4)
        tx.append(a[0] + (j[0] - a[0]) * wj[q]); ty.append(a[1] + (j[1] - a[1]) * wj[q]); tz.append(a[2] + (j[2] - a[2]) * wj[q] + dz[q] - 0.5); seps.append(math.dist(a, j))
    SELLADO = (-96.0, -109.0, 15.6)                                           # centro del refugio; desde ~f2005 los dos estan dentro y se muestra el refugio con los zombies que lo atacan
    for q, k in enumerate(ks):
        w_ = min(1.0, max(0.0, (k - 2005) / 40.0)); w_ = w_ * w_ * (3 - 2 * w_)
        tx[q] += (SELLADO[0] - tx[q]) * w_; ty[q] += (SELLADO[1] - ty[q]) * w_; tz[q] += (SELLADO[2] - tz[q]) * w_; seps[q] *= (1 - 0.7 * w_)
    W = 3                                                                   # suavizado del punto de mira y de la separacion (el perro y Alfred se mueven a saltos)
    tx, ty, tz, seps = smooth(tx, W), smooth(ty, W), smooth(tz, W), smooth(seps, W)
    cam = []; meta = []
    for q, k in enumerate(ks):
        fov = 2 * math.atan(SENSOR / 2.0 / lens[q]); need = (seps[q] * 1.5 + 1.2) / (2 * math.tan(fov / 2))                      # los dos personajes caben con margen
        d = max(dist[q], need); a_ = math.radians(az[q]); e_ = math.radians(el[q])
        cam.append((tx[q] + d * math.cos(e_) * math.cos(a_), ty[q] + d * math.cos(e_) * math.sin(a_), tz[q] + d * math.sin(e_))); meta.append((round(d, 2), round(seps[q], 2)))
    cx, cy, cz = smooth([c[0] for c in cam], 2), smooth([c[1] for c in cam], 2), smooth([c[2] for c in cam], 2)
    out = {"N": N, "paso": STEP, "muestras": [{"f": k, "cam": [round(cx[q], 3), round(cy[q], 3), round(cz[q], 3)], "mira": [round(tx[q], 3), round(ty[q], 3), round(tz[q], 3)], "focal": round(lens[q], 2), "dist": meta[q][0], "sep": meta[q][1]} for q, k in enumerate(ks)]}
    json.dump(out, open(os.path.join(HERE, "camara_parte2.json"), "w", encoding="utf-8"), separators=(",", ":"))
    print(f"camara: {len(ks)} muestras (cada {STEP} f) de f1 a f{N}; distancia {min(m[0] for m in meta)}-{max(m[0] for m in meta)} m; separacion Alfred-Jerry max {max(m[1] for m in meta)} m")


if __name__ == "__main__":
    main()
