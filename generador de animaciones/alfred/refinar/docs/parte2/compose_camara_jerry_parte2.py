"""Parte 2 - TERCERA RUTA DE CAMARA: enfocada en los EMPUJONES de Jerry a los zombies mientras Alfred construye el refugio (pedido de Kebyn). Solo calcula keyframes; no renderiza.
Cubre f1461-2060 (construccion del refugio, patrulla de Jerry y los 5 empujones de `empujes_zombies.json`: zombies 1, 2, 3, 5 y 4, frames de golpe 1583, 1653, 1713, 1763, 1924).
 - Punto de mira: Jerry (patrulla) -> punto medio Jerry-zombie durante cada empujon (sube desde golpe-45, baja hasta libre+25); en la patrulla se desplaza un 30 % hacia el refugio para que se vea a Alfred construyendo.
 - Camara: tomas de 3/4 por el EXTERIOR (lado este, que es agua/abierto; el sur es bosque) respecto a la normal del muro en cada empujon, para ver el salto, el golpe y la caida del zombie con el refugio detras;
   entre empujones, plano general abierto desde el este. En el golpe (+-20 f) la focal sube a 40 mm y la camara se acerca; la distancia siempre deja caber a Jerry y al zombie.
 - Giros: azimut y elevacion limitados a 0.30 grados/frame (mismo limitador que la ruta de Alfred); camara = punto de mira + desfase.
Escribe `camara_jerry_parte2.json`; `importar_camara_jerry.py` (Blender) crea `Camara_Jerry` + `Cam_Foco_Jerry` (sin tocar las otras camaras ni la camara activa) y elige posiciones libres de arboles con Viterbi.
Uso (desde 'generador de animaciones'):  python alfred/refinar/docs/parte2/compose_camara_jerry_parte2.py
"""
import json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose_camara_parte2 import val, interp, smooth, STEP, SENSOR, BASE, HERE
from compose_camara_alfred_parte2 import unwrap, limitar_giro

F0, F1 = 1461, 2060
SELLADO = (-96.0, -109.0, 15.6)                                                  # centro del refugio (Alfred construye dentro)
BASE_AZ, BASE_EL, BASE_D, BASE_LENS = 10.0, 16.0, 8.5, 28.0                      # plano general desde el este entre empujones
EV_EL, EV_D, EV_LENS = 12.0, 5.5, 32.0                                           # durante un empujon
GOLPE_LENS, GOLPE_D = 40.0, 4.2                                                  # +-20 frames del golpe


def ss(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def main():
    J = json.load(open(os.path.join(BASE, "jerry/refinar/animaciones_ia/parte2_jerry_refugio/parte2_jerry_refugio.animacion.json"), encoding="utf-8"))["root"]["canales"]["location"]
    EV = sorted(json.load(open(os.path.join(HERE, "empujes_zombies.json"), encoding="utf-8"))["eventos"].values(), key=lambda e: e["frame_golpe"])
    Z = {n: json.load(open(os.path.join(BASE, f"zombie_{n}/refinar/animaciones_ia/parte2_zombie_{n}_sigue/parte2_zombie_{n}_sigue.animacion.json"), encoding="utf-8"))["root"]["canales"]["location"] for n in range(1, 6)}
    for e in EV:                                                                  # azimut de la camara en cada empujon: normal exterior del muro girada 35 grados hacia el lado mas cercano al este
        an = math.degrees(math.atan2(e["n"][1], e["n"][0])); e["az"] = min((an + 35, an - 35), key=lambda a: abs(a - 10.0))
    ks = list(range(F0, F1 + 1, STEP))
    if ks[-1] != F1: ks.append(F1)
    N = len(J[0]); tx, ty, tz, seps, w_ev, w_gol, azv, azw = [], [], [], [], [], [], [], []
    for k in ks:
        j = (val(J[0], k - 1), val(J[1], k - 1), val(J[2], k - 1) + 0.5)
        best = None
        for e in EV:                                                              # empujon activo (el de mayor peso)
            w = ss((k - (e["frame_golpe"] - 45)) / 35.0) * (1.0 - ss((k - (e["frame_libre"] - 5)) / 30.0))
            if best is None or w > best[0]: best = (w, e)
        w, e = best; zn = e["z"]; zp = (val(Z[zn][0], k - 1), val(Z[zn][1], k - 1), val(Z[zn][2], k - 1) + 1.0)
        mid = tuple(0.5 * (j[i] + zp[i]) for i in range(3))
        main_ = tuple(j[i] + (mid[i] - j[i]) * w for i in range(3))
        ws = 0.3 * (1.0 - w)                                                       # en la patrulla el punto de mira se desplaza hacia el refugio (se ve a Alfred construir)
        tx.append(main_[0] + (SELLADO[0] - main_[0]) * ws); ty.append(main_[1] + (SELLADO[1] - main_[1]) * ws); tz.append(main_[2] + 0.3 + (SELLADO[2] - main_[2]) * ws)
        seps.append(math.dist(j, zp) * w); w_ev.append(w)
        g = 1.0 - ss((abs(k - e["frame_golpe"]) - 10) / 12.0); w_gol.append(g * w)
        azv.append(math.radians(e["az"]))
    W = 3
    tx, ty, tz, seps = smooth(tx, W), smooth(ty, W), smooth(tz, W), smooth(seps, W)
    az_f = []
    for q in range(len(ks)):                                                      # azimut: mezcla (vectores) del general (este) y el del empujon activo
        w = w_ev[q]; ab = math.radians(BASE_AZ); re = azv[q]
        x = (1 - w) * math.cos(ab) + w * math.cos(re); y = (1 - w) * math.sin(ab) + w * math.sin(re); az_f.append(math.atan2(y, x))
    el = [math.radians(BASE_EL + (EV_EL - BASE_EL) * w) for w in w_ev]
    LIM = math.radians(0.30) * STEP
    az_f = limitar_giro(unwrap(az_f), LIM); el = limitar_giro(el, LIM)
    lens = [BASE_LENS + (EV_LENS - BASE_LENS) * w_ev[q] + (GOLPE_LENS - EV_LENS) * w_gol[q] for q in range(len(ks))]
    dist = [BASE_D + (EV_D - BASE_D) * w_ev[q] + (GOLPE_D - EV_D) * w_gol[q] for q in range(len(ks))]
    lens = smooth(lens, 1)
    cam, meta = [], []
    for q in range(len(ks)):
        fov = 2 * math.atan(SENSOR / 2.0 / lens[q]); need = (seps[q] * 1.4 + 1.8) / (2 * math.tan(fov / 2))                  # caben Jerry y el zombie
        d = max(dist[q], need)
        cam.append((tx[q] + d * math.cos(el[q]) * math.cos(az_f[q]), ty[q] + d * math.cos(el[q]) * math.sin(az_f[q]), tz[q] + d * math.sin(el[q]))); meta.append((round(d, 2), round(seps[q], 2)))
    out = {"N": N, "paso": STEP, "muestras": [{"f": k, "cam": [round(cam[q][0], 3), round(cam[q][1], 3), round(cam[q][2], 3)], "mira": [round(tx[q], 3), round(ty[q], 3), round(tz[q], 3)], "focal": round(lens[q], 2), "dist": meta[q][0], "sep": meta[q][1]} for q, k in enumerate(ks)]}
    json.dump(out, open(os.path.join(HERE, "camara_jerry_parte2.json"), "w", encoding="utf-8"), separators=(",", ":"))
    print(f"camara Jerry: {len(ks)} muestras (cada {STEP} f) de f{F0} a f{F1}; distancia {min(m[0] for m in meta)}-{max(m[0] for m in meta)} m; azimut de empujon: " + ", ".join(f"z{e['z']}@f{e['frame_golpe']}:{e['az']:.0f}" for e in EV))


if __name__ == "__main__":
    main()
