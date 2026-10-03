"""Parte 2 - SEGUNDA RUTA DE CAMARA cinematografica, enfocada en las EXPRESIONES de ALFRED (pedido de Kebyn). Solo calcula keyframes; no renderiza.
Misma tecnica que `compose_camara_parte2.py` (balizas de toma interpoladas con Catmull-Rom, sin sobreimpulsos, suavizadas; reutiliza sus funciones), pero:
 - el punto de mira es Alfred (peso de Jerry 0-0.2; sube en la antorcha y tras f1900, cuando Alfred queda bajo el techo),
 - en los momentos de expresion (columna `cara` = 1) la camara se coloca DELANTE de su cara: azimut relativo a hacia donde mira Alfred (`az_rel`, 0 = de frente, +-30 = 3/4),
   a 2.2-3.2 m con 45-60 mm y apuntando a la altura de los ojos (root + 1.7 m); el rumbo de Alfred se suaviza para que la camara no gire de golpe,
 - tomas amplias (cara = 0) con azimut absoluto, como la ruta anterior; la distancia solo exige que quepa Alfred (y Jerry segun su peso).
Escribe `camara_alfred_parte2.json` (muestras cada STEP frames). `importar_camara_alfred.py` (exec en Blender) crea `Camara_Alfred` + `Cam_Foco_Alfred` SIN tocar la camara anterior,
elige posiciones libres de arboles de forma continua en el tiempo (Viterbi) y limita la velocidad de giro de la mirada.
Uso (desde 'generador de animaciones'):  python alfred/refinar/docs/parte2/compose_camara_alfred_parte2.py
"""
import json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose_camara_parte2 import val, interp, smooth, STEP, SENSOR, BASE, HERE

# (frame, azimut absoluto deg [0 = camara al este, -90 = al sur, 180 = al oeste], elevacion deg, distancia base m, focal mm, peso de Jerry, altura extra del punto de mira m,
#  cara 0..1 [1 = camara delante de la cara de Alfred], az_rel deg respecto a hacia donde mira Alfred [0 = de frente])
BALIZAS = [
    (1, -90, 5, 6.0, 32, 0.10, 0.5, 0.0, 0),          # f1-274 nada hacia el este: travelling bajo desde el sur
    (110, -70, 6, 5.0, 35, 0.10, 0.8, 0.0, 0),
    (170, -50, 6, 3.4, 40, 0.05, 1.2, 0.8, 35),       # nadando: 3/4 delantero
    (235, -50, 7, 3.6, 40, 0.05, 1.1, 0.6, 35),
    (280, -60, 7, 3.0, 45, 0.05, 1.25, 1.0, 30),      # f275-475 discusion: cara de Alfred
    (333, -90, 6, 2.4, 55, 0.0, 1.3, 1.0, 25),        # preocupado
    (376, -80, 6, 2.2, 60, 0.0, 1.3, 1.0, -25),       # sospecha (empuje lento)
    (436, -60, 6, 2.2, 60, 0.0, 1.3, 1.0, 20),        # idea
    (458, -30, 6, 2.6, 55, 0.0, 1.3, 1.0, 20),        # decidido
    (495, 10, 8, 2.8, 50, 0.10, 1.3, 1.0, 20),        # f476-540 mira atras y ve a los zombies: miedo
    (525, 25, 12, 5.5, 32, 0.20, 1.0, 0.3, 0),
    (565, -90, 12, 7.0, 28, 0.10, 0.6, 0.0, 0),       # f540-706 nada frenetico al norte: plano amplio desde detras
    (600, -88, 10, 4.2, 40, 0.05, 1.0, 0.6, 25),      # panico
    (690, -80, 10, 8.0, 26, 0.10, 0.5, 0.0, 0),
    (706, -20, 5, 6.5, 28, 0.10, 0.8, 0.0, 0),        # f706-810 sube la escalera: contrapicado
    (760, -15, 6, 3.4, 45, 0.05, 1.2, 0.7, 30),       # urgencia
    (815, 5, 9, 9.0, 24, 0.10, 0.6, 0.0, 0),          # f810-1000 resbala, rueda y flota: plano amplio
    (900, 10, 12, 10.0, 24, 0.10, 0.6, 0.0, 0),
    (985, 10, 12, 7.0, 30, 0.10, 0.3, 0.3, 20),
    (1010, 0, 10, 3.2, 50, 0.05, 1.0, 1.0, 20),       # despierta con parpados pesados
    (1045, 0, 10, 2.6, 55, 0.05, 1.2, 1.0, 20),       # tos
    (1075, -5, 9, 3.0, 50, 0.10, 1.2, 1.0, 25),       # ve a los zombies
    (1110, -10, 9, 7.0, 28, 0.15, 0.6, 0.0, 0),       # f1100-1227 vuelve a subir
    (1227, -20, 10, 6.0, 30, 0.10, 0.8, 0.0, 0),
    (1300, -170, 8, 3.0, 45, 0.05, 1.2, 1.0, 20),     # f1227-1349 camina agotado: cara
    (1349, -200, 8, 3.2, 45, 0.05, 1.2, 0.8, 30),
    (1371, -215, 12, 3.0, 40, 0.30, 1.0, 0.6, 30),    # f1349-1391 se coloca la antorcha
    (1420, -230, 8, 2.6, 50, 0.05, 1.25, 1.0, 25),    # descanso y charla
    (1470, -250, 35, 6.0, 28, 0.10, 1.2, 0.0, 0),     # f1461-1860 construye el refugio: desde arriba (el interior sigue abierto)
    (1540, -300, 28, 3.6, 40, 0.05, 1.2, 0.9, 30),    # concentrado
    (1600, -330, 40, 7.0, 26, 0.10, 1.2, 0.0, 0),
    (1700, -380, 45, 8.5, 24, 0.10, 1.2, 0.0, 0),
    (1860, -460, 38, 9.0, 24, 0.10, 1.0, 0.0, 0),
    (1900, -480, 22, 8.0, 24, 0.60, 0.8, 0.0, 0),     # f1860+: el techo cubre a Alfred; baja y sigue a Jerry y a los zombies
    (2000, -540, 16, 9.0, 24, 0.70, 0.8, 0.0, 0),
    (2093, -600, 18, 11.0, 24, 0.50, 1.0, 0.0, 0),    # f2005+: el refugio queda sellado (ver SELLADO)
    (2150, -660, 28, 13.0, 24, 0.50, 1.0, 0.0, 0),
]


def smooth_ang(arr, w):
    """suaviza una serie de angulos (rad) mediante vectores unitarios."""
    cs, ss = smooth([math.cos(a) for a in arr], w), smooth([math.sin(a) for a in arr], w)
    return [math.atan2(s, c) for c, s in zip(cs, ss)]


def main():
    A = json.load(open(os.path.join(BASE, "alfred/refinar/animaciones_ia/parte2_alfred_refugio/parte2_alfred_refugio.animacion.json"), encoding="utf-8"))["root"]["canales"]
    J = json.load(open(os.path.join(BASE, "jerry/refinar/animaciones_ia/parte2_jerry_refugio/parte2_jerry_refugio.animacion.json"), encoding="utf-8"))["root"]["canales"]["location"]
    AL, AR = A["location"], A["rotation_euler"]
    N = len(AL[0]); fr = [b[0] for b in BALIZAS]; cols = list(zip(*BALIZAS))
    ks = list(range(1, N + 1, STEP))
    if ks[-1] != N: ks.append(N)
    az = [interp(fr, cols[1], k) for k in ks]; el = [interp(fr, cols[2], k) for k in ks]; dist = [interp(fr, cols[3], k) for k in ks]; lens = [interp(fr, cols[4], k) for k in ks]
    wj = [min(1.0, max(0.0, interp(fr, cols[5], k))) for k in ks]; dz = [interp(fr, cols[6], k) for k in ks]
    cara = [min(1.0, max(0.0, interp(fr, cols[7], k))) for k in ks]; azr = [interp(fr, cols[8], k) for k in ks]
    # rumbo de Alfred (hacia donde mira) suavizado ~ +-24 frames para que la camara no gire de golpe con sus giros rapidos
    head = smooth_ang([math.atan2(math.cos(val(AR[2], k - 1)), -math.sin(val(AR[2], k - 1))) for k in ks], 6)
    az_f = []
    for q in range(len(ks)):                                                    # azimut final: mezcla (por vectores) del absoluto y del relativo a la cara
        ab = math.radians(az[q]); re = head[q] + math.radians(azr[q]); c_ = cara[q]
        x = (1 - c_) * math.cos(ab) + c_ * math.cos(re); y = (1 - c_) * math.sin(ab) + c_ * math.sin(re); az_f.append(math.atan2(y, x))
    tx, ty, tz, seps = [], [], [], []
    for q, k in enumerate(ks):
        a = (val(AL[0], k - 1), val(AL[1], k - 1), val(AL[2], k - 1) + 0.9); j = (val(J[0], k - 1), val(J[1], k - 1), val(J[2], k - 1) + 0.4)
        tx.append(a[0] + (j[0] - a[0]) * wj[q]); ty.append(a[1] + (j[1] - a[1]) * wj[q]); tz.append(a[2] + (j[2] - a[2]) * wj[q] + dz[q] - 0.5); seps.append(math.dist(a, j) * wj[q])
    SELLADO = (-96.0, -109.0, 15.6)                                           # centro del refugio; desde ~f2005 los dos estan dentro y se muestra el refugio con los zombies que lo atacan
    for q, k in enumerate(ks):
        w_ = min(1.0, max(0.0, (k - 2005) / 40.0)); w_ = w_ * w_ * (3 - 2 * w_)
        tx[q] += (SELLADO[0] - tx[q]) * w_; ty[q] += (SELLADO[1] - ty[q]) * w_; tz[q] += (SELLADO[2] - tz[q]) * w_; seps[q] *= (1 - 0.7 * w_)
    W = 3
    tx, ty, tz, seps = smooth(tx, W), smooth(ty, W), smooth(tz, W), smooth(seps, W)
    cam = []; meta = []
    for q, k in enumerate(ks):
        fov = 2 * math.atan(SENSOR / 2.0 / lens[q]); need = (seps[q] * 1.5 + 1.4 - 0.5 * cara[q]) / (2 * math.tan(fov / 2))                  # cabe Alfred (y Jerry segun su peso)
        d = max(dist[q], need); e_ = math.radians(el[q])
        cam.append((tx[q] + d * math.cos(e_) * math.cos(az_f[q]), ty[q] + d * math.cos(e_) * math.sin(az_f[q]), tz[q] + d * math.sin(e_))); meta.append((round(d, 2), round(seps[q], 2)))
    cx, cy, cz = smooth([c[0] for c in cam], 2), smooth([c[1] for c in cam], 2), smooth([c[2] for c in cam], 2)
    out = {"N": N, "paso": STEP, "muestras": [{"f": k, "cam": [round(cx[q], 3), round(cy[q], 3), round(cz[q], 3)], "mira": [round(tx[q], 3), round(ty[q], 3), round(tz[q], 3)], "focal": round(lens[q], 2), "dist": meta[q][0], "sep": meta[q][1], "cara": round(cara[q], 2)} for q, k in enumerate(ks)]}
    json.dump(out, open(os.path.join(HERE, "camara_alfred_parte2.json"), "w", encoding="utf-8"), separators=(",", ":"))
    print(f"camara Alfred: {len(ks)} muestras (cada {STEP} f) de f1 a f{N}; distancia {min(m[0] for m in meta)}-{max(m[0] for m in meta)} m; {sum(1 for c_ in cara if c_ > 0.5)} muestras con cara > 0.5")


if __name__ == "__main__":
    main()
