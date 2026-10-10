# -*- coding: utf-8 -*-
"""Parte 8 (version final): Alfred cava/pica un tunel RECTO desde la coordenada inicial (-106.5, -69.5, 9.0) hasta la final (-131.5, -69.5, 6.0) (fila de celdas y -70, x -107 -> -132, la raiz baja en linea recta de z 9 a 6).
Sustituye al recorrido anterior (curvas, etapas 1 y 2): se parte de `base_parte_8.blend` recien cargado. Usa las mismas animaciones (palada de `pala_pozo` para tierra; ciclo del hacha con el PICO para piedra) y las funciones de `tunel_alfred_parte8.py`.
Cada paso: cava las celdas SOLIDAS del corredor (3 de alto desde el piso, rejilla `tunel3_rejilla.json`) en grupos de 2 por golpe y avanza 1 bloque; donde la cueva es aire solo camina. Una herramienta por paso (pico si hay piedra, si no la que lleva).
Orden: recargar la base -> `exec(este)` -> `tunel_geometria_parte8.py` (usa `tunel_eventos.json`). Jerry no se anima. Se ejecuta DENTRO de Blender con exec."""
import bpy, json, math
R_ = "C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/parte8/"
g = globals(); exec(open(R_ + "tunel_alfred_parte8.py", encoding="utf-8").read(), g)       # funciones y poses (no toca la escena)

X0, X1 = -107, -132; YC = -70
INI = (-106.5, -69.5, 9.0); FINAL = (-131.5, -69.5, 6.0)
def raiz_z(xc): return 9.0 - 3.0 * (-106.5 - xc) / 25.0

def construir_recto():
    G = json.load(open(R_ + "tunel3_rejilla.json", encoding="utf-8")); sol = lambda c: G.get("%d,%d,%d" % c, 1)
    TL.clear(); EVENTOS.clear(); ACC.clear(); cur[0] = 1; ult.update(pose=REPOSO, x=INI[0], y=INI[1], rz=90.0, z=INI[2])
    quedarse(14, REPOSO, INI[0], INI[1], 90.0)
    herr = None; ultimo = None; LLEG = {}
    def a_pie(xq, nf=9, pose=REPOSO):
        xa = xq + 0.5; xb = xq - 0.5; za, zb = raiz_z(xa), raiz_z(xb); p0_ = ult["pose"]
        for i in range(nf):
            u = (i + 1) / nf; amp = min(1.0, (i + 1) / 3.0, (nf - i) / 3.0 + 0.15); base = mezcla(p0_, pose, ss(min(1.0, (i + 1) / 4.0)))
            poner(piernas(base, i / 12.0 * 2 * math.pi, amp), xa + (xb - xa) * u, INI[1], 90.0, z=za + (zb - za) * u)
    for xq in range(X0, X1, -1):                                              # xq = celda donde esta parado (de -107 a -131); la celda de delante es xq-1
        LLEG[xq] = cur[0]; xn = xq - 1; xa = xq + 0.5; za = raiz_z(xa); zf = int(math.floor(raiz_z(xn + 0.5) + 0.001))
        nuevos = [(xn, YC, z) for z in range(zf, zf + 3) if sol((xn, YC, z))]
        if nuevos:
            th = "pico" if any(es_piedra_celda(c) for c in nuevos) else (herr or "pala")
            for i in range(0, len(nuevos), 2):
                grp = nuevos[i:i + 2]
                if herr != th:
                    if herr is not None: guardar(herr, xa, INI[1], 90.0)
                    tomar(th, xa, INI[1], 90.0); herr = th; ultimo = None
                    if th == "pico": secuencia([mezcla(LISTO, HA[1022], ss((j + 1) / 7.0)) for j in range(7)], xa, INI[1], 90.0, mezcla_in=0)
                n, imp = (14, 6) if herr == "pala" else (12, 4); ciclo = pala_ciclo if herr == "pala" else pico_ciclo
                t_ini = cur[0]; secuencia([ciclo(8 + j) for j in range(n)], xa, INI[1], 90.0, mezcla_in=(0 if ultimo == (herr, xq) else 5)); ultimo = (herr, xq)
                EVENTOS.append((t_ini + imp, grp))
        a_pie(xq, pose=(LISTO if herr == "pala" else (HA[1022] if herr == "pico" else REPOSO))); ultimo = None
    xa = X1 + 0.5
    if herr is not None: guardar(herr, xa, INI[1], 90.0)
    quedarse(24, REPOSO, xa, INI[1], 90.0)
    json.dump({str(k): v for k, v in LLEG.items()}, open(R_ + 'tunel_llegadas.json', 'w'))
    return cur[0] - 1
