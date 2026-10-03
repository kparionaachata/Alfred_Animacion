"""Parte 2 - SEGUNDA RUTA DE CAMARA cinematografica, enfocada en ALFRED (pedido de Kebyn). Solo calcula keyframes; no renderiza.
Misma tecnica que `compose_camara_parte2.py` (balizas de toma interpoladas con Catmull-Rom, sin sobreimpulsos, suavizadas; reutiliza sus funciones), pero:
 - el punto de mira es Alfred (peso de Jerry 0-0.2, solo sube en los momentos de Jerry: antorcha, f1900+),
 - planos mas cerrados y focales largas (35-50 mm) en los gestos y emociones de Alfred (discusion, sospecha, idea, despertar, cansancio, construccion),
 - la distancia solo exige que quepa Alfred (y Jerry parcialmente segun su peso),
 - tomas bajas/contrapicadas en las escaleras y el travelling inicial, y empujes lentos (dolly-in) en los primeros planos.
Escribe `camara_alfred_parte2.json` (muestras cada STEP frames). `importar_camara_alfred.py` (exec en Blender) crea `Camara_Alfred` + `Cam_Foco_Alfred` SIN tocar la camara anterior.
Uso (desde 'generador de animaciones'):  python alfred/refinar/docs/parte2/compose_camara_alfred_parte2.py
"""
import json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose_camara_parte2 import val, interp, smooth, STEP, SENSOR, BASE, HERE

# (frame, azimut deg [0 = camara al este de los sujetos, -90 = al sur, 180 = al oeste], elevacion deg, distancia base m, focal mm, peso de Jerry en el punto de mira, altura extra del punto de mira m)
BALIZAS = [
    (1, -90, 5, 6.5, 32, 0.10, 0.3),         # f1-274 nada hacia el este: travelling bajo desde el sur, que va pasando al frente
    (100, -70, 6, 5.5, 35, 0.10, 0.4),
    (200, -35, 8, 5.0, 35, 0.10, 0.4),
    (272, -50, 8, 4.5, 40, 0.10, 0.6),
    (310, -75, 8, 3.6, 45, 0.05, 0.8),       # f275-475 discusion: primer plano de Alfred con empuje lento (preocupacion, sospecha, idea)
    (350, -100, 10, 3.2, 50, 0.05, 0.9),
    (400, -72, 8, 2.9, 50, 0.05, 0.9),
    (440, -35, 8, 3.2, 45, 0.05, 0.9),
    (476, 5, 6, 4.0, 35, 0.20, 0.8),         # f476-540 mira atras y ve a los zombies: la camara pasa al este para verle la cara y el miedo
    (500, 15, 10, 5.5, 28, 0.15, 1.0),
    (535, 30, 16, 8.0, 24, 0.20, 0.8),
    (560, -90, 12, 7.0, 28, 0.10, 0.5),      # f540-706 nada frenetico al norte: camara detras
    (690, -80, 10, 8.0, 26, 0.10, 0.5),
    (706, -20, 5, 6.5, 28, 0.10, 0.8),       # f706-810 sube la escalera: contrapicado desde el este (el sur es bosque que tapa)
    (790, -10, 5, 8.0, 26, 0.10, 1.0),
    (815, 5, 9, 10.0, 24, 0.10, 0.8),        # f810-1000 resbala, rueda y flota: plano amplio sobre el agua
    (900, 10, 12, 11.0, 24, 0.10, 0.8),
    (1000, 10, 14, 9.0, 28, 0.10, 0.3),
    (1070, 0, 12, 6.0, 35, 0.15, 0.0),       # f1000-1100 despierta (tos, parpados pesados) y ve a los zombies: se acerca
    (1100, -10, 9, 7.0, 28, 0.15, 0.5),      # f1100-1227 vuelve a subir
    (1227, -20, 10, 6.0, 30, 0.10, 1.0),
    (1300, -170, 8, 5.0, 35, 0.10, 0.9),     # f1227-1349 camina agotado: la camara pasa delante para verle la cara
    (1349, -200, 8, 4.5, 40, 0.10, 0.9),
    (1371, -215, 12, 3.5, 40, 0.30, 0.5),    # f1349-1391 se coloca la antorcha: primer plano
    (1420, -230, 8, 3.5, 45, 0.10, 0.9),     # descanso y charla
    (1470, -250, 35, 6.0, 28, 0.10, 1.2),    # f1461-1860 construye el refugio: desde arriba (el interior sigue abierto) con orbita lenta
    (1560, -300, 42, 7.5, 26, 0.10, 1.2),
    (1700, -380, 45, 8.5, 24, 0.10, 1.2),
    (1860, -460, 38, 9.0, 24, 0.10, 1.0),
    (1900, -480, 22, 8.0, 24, 0.60, 0.8),    # f1860+: el techo cubre a Alfred; baja y sigue a Jerry y a los zombies que atacan los muros
    (2000, -540, 16, 9.0, 24, 0.70, 0.8),
    (2093, -600, 18, 11.0, 24, 0.50, 1.0),   # f2005+: el refugio queda sellado (ver SELLADO)
    (2150, -660, 28, 13.0, 24, 0.50, 1.0),
]


def main():
    A = json.load(open(os.path.join(BASE, "alfred/refinar/animaciones_ia/parte2_alfred_refugio/parte2_alfred_refugio.animacion.json"), encoding="utf-8"))["root"]["canales"]["location"]
    J = json.load(open(os.path.join(BASE, "jerry/refinar/animaciones_ia/parte2_jerry_refugio/parte2_jerry_refugio.animacion.json"), encoding="utf-8"))["root"]["canales"]["location"]
    N = len(A[0]); fr = [b[0] for b in BALIZAS]; cols = list(zip(*BALIZAS))
    ks = list(range(1, N + 1, STEP))
    if ks[-1] != N: ks.append(N)
    az = [interp(fr, cols[1], k) for k in ks]; el = [interp(fr, cols[2], k) for k in ks]; dist = [interp(fr, cols[3], k) for k in ks]; lens = [interp(fr, cols[4], k) for k in ks]
    wj = [min(1.0, max(0.0, interp(fr, cols[5], k))) for k in ks]; dz = [interp(fr, cols[6], k) for k in ks]
    tx, ty, tz, seps = [], [], [], []
    for q, k in enumerate(ks):
        a = (val(A[0], k - 1), val(A[1], k - 1), val(A[2], k - 1) + 0.9); j = (val(J[0], k - 1), val(J[1], k - 1), val(J[2], k - 1) + 0.4)
        tx.append(a[0] + (j[0] - a[0]) * wj[q]); ty.append(a[1] + (j[1] - a[1]) * wj[q]); tz.append(a[2] + (j[2] - a[2]) * wj[q] + dz[q] - 0.5); seps.append(math.dist(a, j) * wj[q])
    SELLADO = (-96.0, -109.0, 15.6)                                           # centro del refugio; desde ~f2005 los dos estan dentro y se muestra el refugio con los zombies que lo atacan
    for q, k in enumerate(ks):
        w_ = min(1.0, max(0.0, (k - 2005) / 40.0)); w_ = w_ * w_ * (3 - 2 * w_)
        tx[q] += (SELLADO[0] - tx[q]) * w_; ty[q] += (SELLADO[1] - ty[q]) * w_; tz[q] += (SELLADO[2] - tz[q]) * w_; seps[q] *= (1 - 0.7 * w_)
    W = 3
    tx, ty, tz, seps = smooth(tx, W), smooth(ty, W), smooth(tz, W), smooth(seps, W)
    cam = []; meta = []
    for q, k in enumerate(ks):
        fov = 2 * math.atan(SENSOR / 2.0 / lens[q]); need = (seps[q] * 1.5 + 1.4) / (2 * math.tan(fov / 2))                  # cabe Alfred (y Jerry segun su peso)
        d = max(dist[q], need); a_ = math.radians(az[q]); e_ = math.radians(el[q])
        cam.append((tx[q] + d * math.cos(e_) * math.cos(a_), ty[q] + d * math.cos(e_) * math.sin(a_), tz[q] + d * math.sin(e_))); meta.append((round(d, 2), round(seps[q], 2)))
    cx, cy, cz = smooth([c[0] for c in cam], 2), smooth([c[1] for c in cam], 2), smooth([c[2] for c in cam], 2)
    out = {"N": N, "paso": STEP, "muestras": [{"f": k, "cam": [round(cx[q], 3), round(cy[q], 3), round(cz[q], 3)], "mira": [round(tx[q], 3), round(ty[q], 3), round(tz[q], 3)], "focal": round(lens[q], 2), "dist": meta[q][0], "sep": meta[q][1]} for q, k in enumerate(ks)]}
    json.dump(out, open(os.path.join(HERE, "camara_alfred_parte2.json"), "w", encoding="utf-8"), separators=(",", ":"))
    print(f"camara Alfred: {len(ks)} muestras (cada {STEP} f) de f1 a f{N}; distancia {min(m[0] for m in meta)}-{max(m[0] for m in meta)} m")


if __name__ == "__main__":
    main()
