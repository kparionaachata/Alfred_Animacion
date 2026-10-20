# -*- coding: utf-8 -*-
"""Generador de cuevas de bloques (add-on de Blender).

Crea cuevas con BLOQUES INDEPENDIENTES (un objeto por bloque, con la malla compartida por tipo) usando los
bloques de la carpeta `bloques_dinamicos`. La entrada es un pozo vertical que baja desde una coordenada de la
superficie; la cueva es lo unico conectado a ese pozo (cerrada por todos los demas lados).

Tipos de cueva (basados en la generacion de cuevas de Minecraft 1.20.1, mundo "overworld"):
  TUNEL     tunel largo hacia los dos lados del pozo, con ramas que se curvan (suben o bajan) y relieve en el piso,
            techo y paredes (montículos, salientes, alcobas, pilares). Es el que se uso en el capitulo 4.
  QUESO     "cheese caves": grandes cavernas. Densidad = 4*capa^2 + clamp(0.27 + cheese) (+ cierre de bordes);
            el espacio con densidad baja es aire (cave_layer y cave_cheese de noise_settings/overworld.json).
  ESPAGUETI "spaghetti caves": tuneles delgados y largos: donde dos ruidos 3D son a la vez cercanos a 0.
  GUSANO    carver clasico (CaveCarver): sala esferica + tuneles que avanzan con rumbo/inclinacion que derivan,
            se ramifican a +-90 grados y excavan elipsoides de radio 1.5 + sin(pi*paso/largo)*grosor.
  MIXTA     queso + gusano + espagueti, con pilares (overworld/caves/pillars: columnas que se salvan).

Despues de excavar se hacen: pilares, solo-lo-conectado-al-pozo (relleno por inundacion), carcasa de bloques,
estalactitas/estalagmitas (piezas de goteo de la carpeta) y bultos en paredes, suelo y techo.

Uso: View3D > barra lateral (N) > pestana "Cuevas". Instalar este archivo como add-on (Preferences > Add-ons >
Install from Disk) o ejecutarlo con Alt+P desde el editor de texto de Blender.
"""
bl_info = {
    "name": "Generador de Cuevas de Bloques",
    "author": "Alfred Animacion",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Cuevas",
    "description": "Genera cuevas (tunel, queso, espagueti, gusano, mixta) con bloques independientes",
    "category": "Object",
}

import math
import os
import random
import time
from collections import deque

try:
    import bpy
    from bpy.props import (BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, IntProperty,
                           IntVectorProperty, PointerProperty, StringProperty)
    from bpy.types import Operator, Panel, PropertyGroup
except ImportError:          # el nucleo de generacion se puede probar fuera de Blender
    bpy = None

D6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
N4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def ss(t):
    return t * t * (3 - 2 * t)


# ============================================================================================================
#  RUIDO (valor con interpolacion suave; reproducible por semilla)
# ============================================================================================================
def _h(i, j, k, s):
    v = math.sin(i * 127.1 + j * 311.7 + k * 74.7 + s * 19.3) * 43758.5453
    return (v - math.floor(v)) * 2 - 1


def noise3(x, y, z, s):
    i, j, k = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - i, y - j, z - k
    ux, uy, uz = ss(fx), ss(fy), ss(fz)

    def l(a, b, t):
        return a + (b - a) * t
    c = [[[_h(i + a, j + b, k + cc, s) for cc in (0, 1)] for b in (0, 1)] for a in (0, 1)]
    return l(l(l(c[0][0][0], c[0][0][1], uz), l(c[0][1][0], c[0][1][1], uz), uy),
             l(l(c[1][0][0], c[1][0][1], uz), l(c[1][1][0], c[1][1][1], uz), uy), ux)


def fbm3(x, y, z, s, octavas=3):
    t, a, f, tot = 0.0, 1.0, 1.0, 0.0
    for q in range(octavas):
        t += a * noise3(x * f, y * f, z * f, s + 13 * q)
        tot += a
        a *= 0.5
        f *= 2
    return t / tot


def noise2(x, y, s):                       # 0..1
    return noise3(x, y, 0.37, s) * 0.5 + 0.5


def fbm2(x, y, s, octavas=3):              # 0..1
    return fbm3(x, y, 0.37, s, octavas) * 0.5 + 0.5


# ============================================================================================================
#  NUCLEO: EXCAVACION (conjuntos de celdas (i, j, k); la celda i cubre [i, i+1])
# ============================================================================================================
class Parametros:
    """Parametros planos (sin bpy) para poder probar el generador fuera de Blender."""
    def __init__(self, **kw):
        self.tipo = 'TUNEL'
        self.entrada = (-45.5, -14.5, 8.0)
        self.pozo = 10
        self.alto = 10
        self.ancho = 20
        self.largo_lado = 50
        self.curva_largo = 50
        self.curva_oeste_dz = -4
        self.curva_este_dz = 8
        self.curva_giro = 0.9
        self.techo_max = 5
        self.semilla = 1
        self.relieve = 1.0
        self.alcobas = 1.0
        self.pilares = 18
        self.estalactitas = 1.0
        self.estalagmitas = 1.0
        self.bultos = 1.0
        self.tam_caverna = (60, 50, 16)      # QUESO / ESPAGUETI / MIXTA: ancho (x), largo (y), alto (z)
        self.num_tuneles = 7                 # GUSANO / MIXTA
        self.largo_tunel = 60
        for k, v in kw.items():
            setattr(self, k, v)

    @property
    def celda_pozo(self):
        return (math.floor(self.entrada[0]), math.floor(self.entrada[1]))

    @property
    def k_superficie(self):                  # primer bloque por encima del suelo (el pozo llega hasta k_superficie - 1)
        return int(round(self.entrada[2]))

    @property
    def k_fondo_pozo(self):                  # celda mas baja del pozo (= hueco del techo de la cueva)
        return self.k_superficie - self.pozo


def _envolvente_tunel(p):
    """columnas (i, j) -> [piso, techo) del tunel recto + dos ramas curvas"""
    px, py = p.celda_pozo
    kb = p.k_fondo_pozo
    k_aire_top = kb - 1                      # ultima celda de aire del tunel (justo bajo el hueco del techo)
    piso0 = k_aire_top - p.alto + 1
    col = {}
    xa, xb = px - p.largo_lado, px + p.largo_lado
    ya = py - p.ancho // 2
    yb = ya + p.ancho - 1
    for i in range(xa, xb + 1):
        for j in range(ya, yb + 1):
            col[(i, j)] = [piso0, k_aire_top + 1]
    yc = (ya + yb + 1) / 2.0                  # y del centro del tunel

    def rama(x0, y0, yaw0, giro, delta, fase, techo_max):
        x, y = x0, y0
        n = max(1, int(p.curva_largo * 2))
        for q in range(n + 1):
            s = q * 0.5
            u = s / max(1.0, float(p.curva_largo))
            yaw = yaw0 + giro * u ** 1.3 + 0.10 * math.sin(s * 0.15 + fase)
            x += math.cos(yaw) * 0.5
            y += math.sin(yaw) * 0.5
            r = p.ancho / 2.0 + 1.5 * math.sin(s * 0.2 + fase)
            alto = p.alto + round(1.3 * math.sin(s * 0.17 + 2 * fase))
            zf = round(piso0 + delta * ss(min(1.0, u)) + 1.0 * math.sin(s * 0.1 + fase))
            if techo_max is not None:
                zf = min(zf, techo_max - alto)
            for i in range(math.floor(x - r), math.ceil(x + r) + 1):
                for j in range(math.floor(y - r), math.ceil(y + r) + 1):
                    if (i + 0.5 - x) ** 2 + (j + 0.5 - y) ** 2 <= r * r and not (xa <= i <= xb and ya <= j <= yb):
                        a = col.get((i, j))
                        if a is None:
                            col[(i, j)] = [zf, zf + alto]
                        else:
                            a[0] = min(a[0], zf)
                            a[1] = max(a[1], zf + alto)
    if p.curva_largo > 0:
        rama(float(xa), yc, math.pi, -p.curva_giro, p.curva_oeste_dz, 0.0, p.techo_max)
        rama(float(xb + 1), yc, 0.0, -p.curva_giro, p.curva_este_dz, 2.0, p.techo_max)
    return col


def _bfs_dist(E, maxd):
    din = {c: 0 for c in E if any((c[0] + d[0], c[1] + d[1]) not in E for d in N4)}
    q = deque(din)
    while q:
        c = q.popleft()
        for d in N4:
            n = (c[0] + d[0], c[1] + d[1])
            if n in E and n not in din:
                din[n] = din[c] + 1
                q.append(n)
    dout = {c: 0 for c in din if din[c] == 0}
    cerca = {c: c for c in dout}
    q = deque(dout)
    while q:
        c = q.popleft()
        for d in N4:
            n = (c[0] + d[0], c[1] + d[1])
            if n not in E and n not in dout and dout[c] < maxd:
                dout[n] = dout[c] + 1
                cerca[n] = cerca[c]
                q.append(n)
    return din, dout, cerca


def excavar_tunel(p):
    """TUNEL: envolvente + relieve (montículos, colgantes, domos, paredes con entrantes y alcobas) + pilares"""
    col = _envolvente_tunel(p)
    E = set(col)
    din, dout, cerca = _bfs_dist(E, 4)
    px, py = p.celda_pozo
    dp = lambda i, j: max(abs(i - px), abs(j - py))
    sem = p.semilla * 101
    rel = max(0.0, p.relieve)
    alc = max(0.0, p.alcobas)
    nuevas = {}
    items = list(col.items()) + [(c, col[cerca[c]]) for c in dout if c not in E]
    for c, (f0, c0) in items:
        i, j = c
        if c in E and din[c] <= 3 and dp(i, j) > 6 and fbm2(i / 6.0, j / 6.0, sem + 61) > 0.56 + 0.08 * din[c] + 0.2 * (1 - alc):
            continue
        if c not in E and not (alc > 0 and fbm2(i / 7.0, j / 7.0, sem + 67) > 0.48 + 0.09 * dout[c] + 0.25 * (1 - min(1.0, alc))):
            continue
        x, y = i + 0.5, j + 0.5
        cerca_pozo = dp(i, j) <= 5
        mont = 0 if cerca_pozo else (max(0.0, fbm2(x / 10.0, y / 10.0, sem + 41) - 0.30) * 11 + 2.4 * noise2(x / 2.8, y / 2.8, sem + 43)) * rel
        cuelg = 0 if dp(i, j) <= 2 else (max(0.0, fbm2(x / 9.0, y / 9.0, sem + 47) - 0.34) * 8.5 + 2.2 * noise2(x / 2.6, y / 2.6, sem + 49)) * rel
        domo = 0 if dp(i, j) <= 2 else round(3.0 * max(0.0, fbm2(x / 16.0, y / 16.0, sem + 53) - 0.56) * 3 * rel)
        piso = f0 + round(mont)
        techo = c0 - round(cuelg) + domo
        if p.techo_max is not None:
            techo = min(techo, p.techo_max)
        if techo - piso < 5:
            piso = min(piso, techo - 5)
            if piso < f0:
                piso = f0
                techo = f0 + 5
        nuevas[c] = (piso, techo)
    aire = {(i, j, k) for (i, j), (a, b) in nuevas.items() for k in range(a, b)}
    # pilares: columnas de 1-2 bloques que unen piso y techo (lejos del pozo y de los bordes)
    rng = random.Random(p.semilla + 12)
    cand = [c for c in nuevas if c in E and din.get(c, 0) >= 4 and dp(*c) > 9]
    for c in rng.sample(cand, min(len(cand), int(p.pilares))):
        a, b = nuevas[c]
        w = rng.choice([1, 1, 2])
        for dx in range(w):
            for dy in range(w):
                for k in range(a, b):
                    aire.discard((c[0] + dx, c[1] + dy, k))
    return aire


def _caja_caverna(p):
    px, py = p.celda_pozo
    w, l, h = p.tam_caverna
    kb = p.k_fondo_pozo
    k1 = kb - 1
    k0 = k1 - int(h) + 1
    return (px - int(w) // 2, px + int(w) // 2, py - int(l) // 2, py + int(l) // 2, k0, k1)


def _sala_bajo_pozo(p, aire, radio=6.0, alto_v=3.2):
    px, py = p.celda_pozo
    kb = p.k_fondo_pozo
    cz = kb - 1 - alto_v - 0.5
    _elipsoide(aire, px + 0.5, py + 0.5, cz, radio, alto_v, _caja_caverna(p))


def _elipsoide(aire, cx, cy, cz, rh, rv, caja):
    x0, x1, y0, y1, k0, k1 = caja
    for i in range(max(x0 + 1, math.floor(cx - rh)), min(x1 - 1, math.ceil(cx + rh)) + 1):
        for j in range(max(y0 + 1, math.floor(cy - rh)), min(y1 - 1, math.ceil(cy + rh)) + 1):
            for k in range(max(k0, math.floor(cz - rv)), min(k1, math.ceil(cz + rv)) + 1):
                if ((i + 0.5 - cx) / rh) ** 2 + ((j + 0.5 - cy) / rh) ** 2 + ((k + 0.5 - cz) / rv) ** 2 < 1:
                    aire.add((i, j, k))


def excavar_queso(p):
    """QUESO: densidad = 4*capa^2 + clamp(0.27 + cheese, -1, 1) + cierre de bordes; aire donde la densidad es baja"""
    x0, x1, y0, y1, k0, k1 = _caja_caverna(p)
    sem = p.semilla * 7
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    dens = {}
    for i in range(x0 + 1, x1):
        for j in range(y0 + 1, y1):
            for k in range(k0, k1 + 1):
                x, y, z = i + 0.5, j + 0.5, k + 0.5
                capa = fbm3(x / 26.0, z * 8 / 26.0, y / 26.0, sem + 3, 2)            # cave_layer: y_scale 8
                queso = fbm3(x / 20.0, z * 0.667 / 20.0, y / 20.0, sem + 7, 3)       # cave_cheese: y_scale 0.667
                rr = ((x - cx) / max(1.0, (x1 - x0) / 2 - 2)) ** 2 + ((y - cy) / max(1.0, (y1 - y0) / 2 - 2)) ** 2
                vv = ((k + 0.5 - (k0 + k1) / 2.0) / max(1.0, (k1 - k0) / 2.0 + 1)) ** 2
                dens[(i, j, k)] = 4 * capa * capa + max(-1.0, min(1.0, 0.27 + queso)) + 2.2 * rr ** 2 + 1.5 * vv ** 2
    vals = sorted(dens.values())
    T = vals[int(len(vals) * 0.40)]
    aire = {c for c, d in dens.items() if d < T}
    _sala_bajo_pozo(p, aire, 6.0, 3.2)
    return aire


def excavar_espagueti(p):
    """ESPAGUETI: tubos 3D = donde dos ruidos son a la vez cercanos a 0 (spaghetti_3d_1/2) + rugosidad"""
    x0, x1, y0, y1, k0, k1 = _caja_caverna(p)
    sem = p.semilla * 11
    aire = set()
    for i in range(x0 + 1, x1):
        for j in range(y0 + 1, y1):
            for k in range(k0, k1 + 1):
                x, y, z = i + 0.5, j + 0.5, k + 0.5
                a = fbm3(x / 16.0, z * 1.4 / 16.0, y / 16.0, sem + 5, 2)
                b = fbm3(x / 16.0, z * 1.4 / 16.0, y / 16.0, sem + 21, 2)
                grosor = 0.16 + 0.10 * (fbm3(x / 40.0, y / 40.0, z / 25.0, sem + 31, 1) * 0.5 + 0.5)
                rug = 0.05 * noise3(x / 3.0, y / 3.0, z / 3.0, sem + 9)
                if a * a + b * b < (grosor + rug) ** 2:
                    aire.add((i, j, k))
    _sala_bajo_pozo(p, aire, 5.0, 2.8)
    # tres tuneles finos que salen de la sala y se cruzan con la red (garantizan que el espagueti quede conectado al pozo)
    caja = _caja_caverna(p)
    px, py = p.celda_pozo
    z0 = p.k_fondo_pozo - 1 - 4.5
    for q in range(3):
        r = random.Random(p.semilla * 31 + q)
        _tunel_gusano(aire, px + 0.5, py + 0.5, z0 + r.uniform(-1.5, 1.5), 0.8, r.uniform(0, 2 * math.pi), (r.random() - 0.5) / 5, 0,
                      int(max(30, min(p.tam_caverna[0], p.tam_caverna[1]) * 0.7)), 0.5, r, caja)
    return aire


def _tunel_gusano(aire, cx, cy, cz, grosor, yaw, pitch, paso0, largo, yscale, r, caja):
    ramificado = False
    ya = pp = 0.0
    for paso in range(paso0, largo):
        rh = 1.5 + math.sin(math.pi * paso / largo) * grosor
        cp = math.cos(pitch)
        cx += math.cos(yaw) * cp
        cy += math.sin(yaw) * cp
        cz += math.sin(pitch)
        pitch *= 0.92 if r.random() < 1 / 6 else 0.7
        pitch += pp * 0.1
        yaw += ya * 0.1
        pp *= 0.9
        ya *= 0.75
        pp += (r.random() - r.random()) * r.random() * 2
        ya += (r.random() - r.random()) * r.random() * 4
        if not ramificado and paso == largo // 3 and grosor > 1:
            ramificado = True
            _tunel_gusano(aire, cx, cy, cz, r.random() * 0.5 + 0.5, yaw - math.pi / 2, pitch / 3, paso, largo, yscale, r, caja)
            _tunel_gusano(aire, cx, cy, cz, r.random() * 0.5 + 0.5, yaw + math.pi / 2, pitch / 3, paso, largo, yscale, r, caja)
            return
        if r.randrange(4) == 0:
            continue
        _elipsoide(aire, cx, cy, cz, rh, max(1.6, rh * yscale), caja)


def excavar_gusano(p):
    """GUSANO: CaveCarver (sala + tuneles que derivan y se ramifican)"""
    caja = _caja_caverna(p)
    aire = set()
    _sala_bajo_pozo(p, aire, 6.0, 3.2)
    px, py = p.celda_pozo
    kb = p.k_fondo_pozo
    z0 = kb - 1 - 4.5
    for q in range(int(p.num_tuneles)):
        r = random.Random(p.semilla * 100 + q)
        _tunel_gusano(aire, px + 0.5, py + 0.5, z0 + r.uniform(-2, 1), r.uniform(2.0, 4.2), r.uniform(0, 2 * math.pi),
                      (r.random() - 0.5) / 4, 0, int(p.largo_tunel * r.uniform(0.8, 1.2)), r.uniform(0.4, 0.7), r, caja)
    return aire


def excavar_mixta(p):
    aire = excavar_queso(p)
    aire |= excavar_gusano(p)
    aire |= excavar_espagueti(p)
    x0, x1, y0, y1, k0, k1 = _caja_caverna(p)
    # pilares con la formula real: (2*ruido - 1 - rareza) * (0.55 + 0.55*grosor)^3 >= 0.03
    sem = p.semilla * 13
    px, py = p.celda_pozo
    pv = {}
    for (i, j, k) in aire:
        x, y, z = i + 0.5, j + 0.5, k + 0.5
        rare = fbm3(x / 40.0, y / 40.0, 0, sem + 33, 1)
        gr = fbm3(x / 40.0, y / 40.0, 0, sem + 35, 1)
        pv[(i, j, k)] = (2 * fbm3(x / 6.0, y / 6.0, z * 0.3 / 6.0, sem + 31, 2) - 1 - rare) * (0.55 + 0.55 * gr) ** 3
    if pv:
        vs = sorted(pv.values())
        thr = max(0.03, vs[int(len(vs) * (1 - 0.04 * min(2.0, p.relieve)))])
        for c, v in pv.items():
            if v >= thr and max(abs(c[0] - px), abs(c[1] - py)) > 4:
                aire.discard(c)
    return aire


def conectar_con_pozo(p, aire):
    """deja solo el aire conectado con el pozo; devuelve (aire, pozo)"""
    px, py = p.celda_pozo
    kb = p.k_fondo_pozo
    kt = p.k_superficie - 1
    pozo = {(px, py, k) for k in range(kb, kt + 1)}
    inicio = (px, py, kb - 1)
    aire = set(aire)
    # el aterrizaje bajo el pozo debe llegar hasta el aire mas cercano de la cueva
    k = kb - 1
    while k > kb - 1 - 8 and (px, py, k) not in aire:
        aire.add((px, py, k))
        k -= 1
    aire.add(inicio)
    vis = {inicio}
    q = deque([inicio])
    while q:
        c = q.popleft()
        for d in D6:
            n = (c[0] + d[0], c[1] + d[1], c[2] + d[2])
            if n in aire and n not in vis and n[2] < kb:
                vis.add(n)
                q.append(n)
    return vis, pozo


def generar_aire(p):
    f = {'TUNEL': excavar_tunel, 'QUESO': excavar_queso, 'ESPAGUETI': excavar_espagueti, 'GUSANO': excavar_gusano,
         'MIXTA': excavar_mixta}[p.tipo]
    aire = f(p)
    # nada por encima del hueco del pozo (el techo de la cueva queda bajo el pozo)
    kb = p.k_fondo_pozo
    aire = {c for c in aire if c[2] < kb}
    return conectar_con_pozo(p, aire)


def carcasa(p, aire, pozo):
    """celdas solidas pegadas al aire (bloques completos de 1 bloque de grosor)"""
    total = aire | pozo
    sol = set()
    for (i, j, k) in total:
        for d in D6:
            c = (i + d[0], j + d[1], k + d[2])
            if c in total or c[2] >= p.k_superficie:
                continue
            sol.add(c)
    return sol


def planear_detalles(p, aire, sol):
    """estalactitas/estalagmitas/bultos: devuelve lista de (clase, pieza, celda); sin solapes"""
    rng = random.Random(p.semilla + 909)
    sem = p.semilla * 17
    px, py = p.celda_pozo
    lejos = lambda i, j: max(abs(i - px), abs(j - py)) > 6
    rica = lambda i, j, s: max(0.0, noise2(i / 9.0, j / 9.0, sem + s) - 0.38) * 2.0
    cols = {}
    for (i, j, k) in aire:
        cols.setdefault((i, j), []).append(k)
    cadena = {1: ["punta"], 2: ["base", "punta"], 3: ["base", "medio", "punta"], 4: ["base", "tronco", "medio", "punta"],
              5: ["base", "tronco", "medio", "medio", "punta"]}
    ocup = set()
    out = []
    libre = lambda c: c in aire and c not in ocup
    for (i, j), ks in cols.items():
        ks.sort()
        r = rica(i, j, 3)
        if p.estalactitas > 0 and (i, j, ks[-1] + 1) not in aire and lejos(i, j) and rng.random() < (0.04 + 0.16 * r) * p.estalactitas:
            L = rng.choice([1, 2, 2, 3, 3, 4, 5])
            cs = [(i, j, ks[-1] - q) for q in range(L)]
            if all(libre(c) for c in cs):
                for c, pz in zip(cs, cadena[L]):
                    out.append(("estalactita", pz, c))
                    ocup.add(c)
        if p.estalagmitas > 0 and (i, j, ks[0] - 1) not in aire and lejos(i, j) and rng.random() < (0.03 + 0.14 * rica(i, j, 9)) * p.estalagmitas:
            L = rng.choice([1, 2, 2, 3, 3, 4])
            cs = [(i, j, ks[0] + q) for q in range(L)]
            if all(libre(c) for c in cs):
                for c, pz in zip(cs, cadena[L]):
                    out.append(("estalagmita", pz, c))
                    ocup.add(c)
    if p.bultos > 0:
        for (i, j), ks in cols.items():
            if not lejos(i, j) or rng.random() >= (0.01 + 0.05 * rica(i, j, 17)) * p.bultos:
                continue
            k = rng.choice(ks)
            c = (i, j, k)
            if not libre(c) or not any((i + d[0], j + d[1], k) not in aire for d in D6[:4]):
                continue
            for _ in range(rng.choice([1, 1, 2, 3])):
                if libre(c):
                    out.append(("bulto", None, c))
                    ocup.add(c)
                d = rng.choice(D6[:4])
                c = (c[0] + d[0], c[1] + d[1], c[2] + d[2])
    return out


# ============================================================================================================
#  BLENDER
# ============================================================================================================
if bpy is not None:
    CARPETA_BLOQUES = r"C:\Users\user\Desktop\Alfred_Animacion\bloques_dinamicos"
    CARPETA_TEXTURAS = r"C:\Users\user\Desktop\Alfred_Animacion\ecenarios\mundo_0001\analizar\tex"
    # clave -> (archivo .blend de la carpeta, peso por defecto)
    PALETA = [
        ("stone", "bloque_de_stone", 56), ("andesita", "andesita", 28), ("diorita", "diorita", 16),
        ("granito", "granito", 0), ("cobblestone", "cobblestone", 0), ("toba", "toba", 0),
        ("pizarra_profunda", "pizarra_profunda", 0), ("piedra", "piedra", 0), ("grava", "grava", 0),
        ("obsidiana", "obsidiana", 0), ("mena_carbon", "mena_de_carbon", 0), ("mena_cobre", "mena_de_cobre", 0),
        ("mena_hierro", "mena_de_hierro", 0), ("espeleotema", "bloque_de_espeleotema", 0),
    ]
    PIEZAS_GOTEO = {
        "estalactita": {"base": "estalactita_base", "tronco": "estalactita_tronco", "medio": "estalactita_medio", "punta": "estalactita_punta"},
        "estalagmita": {"base": "estalagmita_base", "tronco": "estalagmita_tronco", "medio": "estalagmita_medio", "punta": "estalagmita_punta"},
    }

    def _peso(nombre):
        return "peso_" + nombre

    def _crear_propiedades_peso():
        anot = {}
        for clave, _f, w in PALETA:
            anot[_peso(clave)] = IntProperty(name=clave.replace("_", " "), default=w, min=0, max=100)
        return anot

    class CuevasProps(PropertyGroup):
        __annotations__ = dict(
            tipo=EnumProperty(name="Tipo", items=[
                ('TUNEL', "Tunel con ramas curvas", "Tunel largo hacia los dos lados con ramas que suben o bajan"),
                ('QUESO', "Queso (cavernas)", "Grandes cavernas de ruido 3D (cheese caves)"),
                ('ESPAGUETI', "Espagueti (tuneles finos)", "Tuneles delgados de ruido 3D"),
                ('GUSANO', "Gusano (carver clasico)", "Sala + tuneles que derivan y se ramifican"),
                ('MIXTA', "Mixta", "Queso + gusano + espagueti con pilares"),
            ], default='TUNEL'),
            entrada=FloatVectorProperty(name="Entrada (superficie)", size=3, default=(-45.5, -14.5, 8.0), subtype='TRANSLATION',
                                        description="Coordenada de la superficie donde empieza el pozo (z = cara superior del suelo)"),
            pozo=IntProperty(name="Profundidad del pozo", default=10, min=2, max=60),
            alto=IntProperty(name="Alto (tunel)", default=10, min=5, max=30),
            ancho=IntProperty(name="Ancho (tunel)", default=20, min=6, max=60),
            largo_lado=IntProperty(name="Largo por lado (tunel)", default=50, min=5, max=300),
            curva_largo=IntProperty(name="Largo de las curvas", default=50, min=0, max=200),
            curva_oeste_dz=IntProperty(name="Rama oeste: sube(+) / baja(-)", default=-4, min=-20, max=20),
            curva_este_dz=IntProperty(name="Rama este: sube(+) / baja(-)", default=8, min=-20, max=20),
            curva_giro=FloatProperty(name="Giro de las curvas (rad)", default=0.9, min=0.0, max=3.0),
            techo_max=IntProperty(name="Techo maximo (z)", default=5, min=-60, max=100, description="No excavar por encima de esta z (evita salir a la superficie)"),
            tam_caverna=IntVectorProperty(name="Caja (x, y, z)", size=3, default=(60, 50, 16), min=10, max=200),
            num_tuneles=IntProperty(name="Tuneles gusano", default=7, min=1, max=30),
            largo_tunel=IntProperty(name="Largo de cada tunel", default=60, min=10, max=250),
            semilla=IntProperty(name="Semilla", default=1, min=0, max=100000),
            relieve=FloatProperty(name="Relieve", default=1.0, min=0.0, max=2.0, description="Altura de montículos, colgantes y domos (tunel)"),
            alcobas=FloatProperty(name="Alcobas / entrantes", default=1.0, min=0.0, max=2.0),
            pilares=IntProperty(name="Pilares", default=18, min=0, max=200),
            estalactitas=FloatProperty(name="Estalactitas", default=1.0, min=0.0, max=3.0),
            estalagmitas=FloatProperty(name="Estalagmitas", default=1.0, min=0.0, max=3.0),
            bultos=FloatProperty(name="Bultos en paredes", default=1.0, min=0.0, max=3.0),
            coleccion=StringProperty(name="Coleccion", default="cueva_bloques"),
            coleccion_terreno=StringProperty(name="Coleccion del terreno", default="minecraft_world_ecenario_2",
                                             description="Se borran sus caras (planos) que quedan dentro de la cueva; vacio = no tocar"),
            carpeta_bloques=StringProperty(name="Carpeta de bloques", default=CARPETA_BLOQUES, subtype='DIR_PATH'),
            carpeta_texturas=StringProperty(name="Carpeta de texturas", default=CARPETA_TEXTURAS, subtype='DIR_PATH'),
            mostrar_paleta=BoolProperty(name="Paleta de bloques", default=False),
            ultimo_resumen=StringProperty(name="Resumen", default=""),
            luz_activa=BoolProperty(name="Crear luz de entrada", default=True,
                                    description="Una luz calida bajo el agujero que se dispersa por la cueva y deja los extremos a oscuras"),
            luz_sol_fuerza=FloatProperty(name="Sol de mediodia (fuerza)", default=5.0, min=0.0, max=100.0,
                                         description="Sol vertical que entra por el pozo (5 = igual que el sol de la escena)"),
            luz_potencia=FloatProperty(name="Foco de dispersion (W)", default=1200.0, min=1.0, max=1000000.0,
                                       description="Foco bajo el pozo: cae con el cuadrado de la distancia, menos potencia = extremos mas oscuros"),
            luz_cono=FloatProperty(name="Apertura del cono (grados)", default=150.0, min=30.0, max=180.0),
            luz_color=FloatVectorProperty(name="Color del foco", size=3, subtype='COLOR', default=(1.0, 0.95, 0.86), min=0.0, max=1.0),
        )
    CuevasProps.__annotations__.update(_crear_propiedades_peso())     # un peso por tipo de bloque de la paleta

    # ------------------------------------------------------------------------------------------------------
    def _reparar_texturas(carpeta):
        """vuelve a enlazar las imagenes cuyos archivos ya no existen (busca por nombre en `carpeta`)"""
        if not carpeta or not os.path.isdir(carpeta):
            return 0
        indice = {}
        for raiz, _d, archivos in os.walk(carpeta):
            for a in archivos:
                indice.setdefault(a.lower(), os.path.join(raiz, a))
        n = 0
        for im in bpy.data.images:
            if im.source != 'FILE' or not im.filepath:
                continue
            ruta = bpy.path.abspath(im.filepath)
            if os.path.exists(ruta):
                continue
            nuevo = indice.get(os.path.basename(ruta).lower())
            if nuevo:
                im.filepath = nuevo
                im.reload()
                n += 1
        return n

    def _malla_de_bloque(carpeta, archivo, coleccion_base, nombre):
        """malla del bloque (se anade el objeto del .blend a una coleccion oculta; se reutiliza si ya existe)"""
        o = bpy.data.objects.get(nombre)
        if o is not None:
            return o.data
        ruta = os.path.join(carpeta, archivo + ".blend")
        if not os.path.isfile(ruta):
            return None
        with bpy.data.libraries.load(ruta, link=False) as (df, dt):
            if not df.objects:
                return None
            dt.objects = [df.objects[0]]
        o = dt.objects[0]
        o.name = nombre
        coleccion_base.objects.link(o)
        o.location = (0, 0, 0)
        o.hide_viewport = True
        o.hide_render = True
        return o.data

    def _coleccion(nombre, hija_de=None):
        c = bpy.data.collections.get(nombre)
        if c is None:
            c = bpy.data.collections.new(nombre)
        padre = hija_de or bpy.context.scene.collection
        if c.name not in padre.children:
            try:
                padre.children.link(c)
            except RuntimeError:
                pass
        return c

    def _borrar_planos(coleccion, aire, extra_celdas, k_sup):
        """borra las caras (planos) del terreno pegadas al aire de la cueva; devuelve cuantas"""
        import numpy as np
        import bmesh
        celdas = set(aire) | set(extra_celdas)
        if not celdas or coleccion is None:
            return 0
        A = np.array(list(celdas))
        lo = A.min(axis=0) - 2
        hi = A.max(axis=0) + 3
        dim = hi - lo
        grid = np.zeros(dim, dtype=bool)
        grid[A[:, 0] - lo[0], A[:, 1] - lo[1], A[:, 2] - lo[2]] = True
        total = 0
        for o in [o for o in coleccion.all_objects if o.type == 'MESH']:
            me = o.data
            n = len(me.polygons)
            if n == 0:
                continue
            c = np.empty(n * 3, dtype=np.float32)
            me.polygons.foreach_get('center', c)
            c = c.reshape(-1, 3)
            W = np.array(o.matrix_world)
            cw = c @ W[:3, :3].T + W[:3, 3]
            ok = np.all((cw >= lo) & (cw <= hi), axis=1)
            if not ok.any():
                continue
            idx = np.nonzero(ok)[0]
            m = np.zeros(n, dtype=bool)
            for ox in (0, 1):
                for oy in (0, 1):
                    for oz in (0, 1):
                        f = np.floor(cw[idx]).astype(int) - np.array([ox, oy, oz]) - lo
                        v = np.all((f >= 0) & (f < dim), axis=1)
                        hit = np.zeros(len(idx), dtype=bool)
                        hit[v] = grid[f[v, 0], f[v, 1], f[v, 2]]
                        m[idx[hit]] = True
            k = int(m.sum())
            if k == 0:
                continue
            if me.users > 1:
                me = o.data = me.copy()
            bm = bmesh.new()
            bm.from_mesh(me)
            bm.faces.ensure_lookup_table()
            bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.nonzero(m)[0]], context='FACES')
            bm.to_mesh(me)
            bm.free()
            me.update()
            total += k
        return total

    def _parametros(props):
        return Parametros(
            tipo=props.tipo, entrada=tuple(props.entrada), pozo=props.pozo, alto=props.alto, ancho=props.ancho,
            largo_lado=props.largo_lado, curva_largo=props.curva_largo, curva_oeste_dz=props.curva_oeste_dz,
            curva_este_dz=props.curva_este_dz, curva_giro=props.curva_giro, techo_max=props.techo_max,
            semilla=props.semilla, relieve=props.relieve, alcobas=props.alcobas, pilares=props.pilares,
            estalactitas=props.estalactitas, estalagmitas=props.estalagmitas, bultos=props.bultos,
            tam_caverna=tuple(props.tam_caverna), num_tuneles=props.num_tuneles, largo_tunel=props.largo_tunel)

    def limpiar_coleccion(nombre):
        c = bpy.data.collections.get(nombre)
        if c is None:
            return 0
        objs = list(c.objects)
        bpy.data.batch_remove(ids=objs)
        return len(objs)

    def _crear_luz_entrada(props, p):
        """luz de entrada: un foco muy abierto justo bajo el hueco del pozo, mirando hacia abajo.
        Cae con el cuadrado de la distancia, asi que cerca del pozo ilumina y los extremos de la cueva quedan oscuros."""
        nombre = "luz_entrada_" + props.coleccion
        for o in [o for o in bpy.data.objects if o.name == nombre]:
            bpy.data.objects.remove(o)
        for l in [l for l in bpy.data.lights if l.name == nombre]:
            bpy.data.lights.remove(l)
        ld = bpy.data.lights.new(nombre, 'SPOT')
        ld.color = tuple(props.luz_color)
        ld.energy = props.luz_potencia
        ld.spot_size = math.radians(props.luz_cono)
        ld.spot_blend = 0.6
        ld.shadow_soft_size = 0.5
        ld.use_shadow = True
        ob = bpy.data.objects.new(nombre, ld)
        px, py = p.celda_pozo
        ob.location = (px + 0.5, py + 0.5, p.k_fondo_pozo - 0.4)
        bpy.context.scene.collection.objects.link(ob)
        cueva = bpy.data.collections.get(props.coleccion)
        # sol de mediodia: vertical (cae recto por el pozo) y solo sobre los bloques de la cueva (light linking)
        ns = "sol_mediodia_" + props.coleccion
        for o in [o for o in bpy.data.objects if o.name == ns]:
            bpy.data.objects.remove(o)
        for l in [l for l in bpy.data.lights if l.name == ns]:
            bpy.data.lights.remove(l)
        sd = bpy.data.lights.new(ns, 'SUN')
        sd.energy = props.luz_sol_fuerza
        sd.color = (1.0, 0.95, 0.86)                 # ~5700 K
        sd.angle = math.radians(0.53)                # tamano aparente real del sol
        sd.use_shadow = True
        sol = bpy.data.objects.new(ns, sd)
        sol.location = (px + 0.5, py + 0.5, p.k_superficie + 50.0)
        bpy.context.scene.collection.objects.link(sol)
        if cueva is not None:
            for lo in (sol, ob):
                try:
                    lo.light_linking.receiver_collection = cueva      # Blender 4.0+ (Cycles)
                except Exception:
                    pass
        return ob

    class CUEVAS_OT_generar(Operator):
        bl_idname = "cuevas.generar"
        bl_label = "Generar cueva"
        bl_description = "Genera la cueva con bloques independientes (reemplaza la anterior de la coleccion)"
        bl_options = {'REGISTER', 'UNDO'}

        def execute(self, context):
            props = context.scene.cuevas_props
            t0 = time.time()
            p = _parametros(props)
            aire, pozo = generar_aire(p)
            if len(aire) < 50:
                self.report({'ERROR'}, "La cueva quedo demasiado pequena (%d celdas de aire). Cambia la semilla o el tamano." % len(aire))
                return {'CANCELLED'}
            sol = carcasa(p, aire, pozo)
            detalles = planear_detalles(p, aire, sol)
            borradas = 0
            if props.coleccion_terreno:
                px, py = p.celda_pozo
                vecinos = {(px + dx, py + dy, p.k_superficie - 1) for dx, dy in N4}
                borradas = _borrar_planos(bpy.data.collections.get(props.coleccion_terreno), aire | pozo, vecinos, p.k_superficie)
            limpiar_coleccion(props.coleccion)
            col = _coleccion(props.coleccion)
            base_col = _coleccion(props.coleccion + "_base")
            base_col.hide_viewport = True
            base_col.hide_render = True
            # --- bloques base (paleta con pesos)
            mallas, pesos = {}, []
            for clave, archivo, _w in PALETA:
                w = getattr(props, _peso(clave))
                if w <= 0:
                    continue
                me = _malla_de_bloque(props.carpeta_bloques, archivo, base_col, clave + "_base")
                if me is None:
                    self.report({'WARNING'}, "No se encontro el bloque '%s' en la carpeta" % archivo)
                    continue
                mallas[clave] = me
                pesos.append((clave, w))
            if not pesos:
                self.report({'ERROR'}, "La paleta esta vacia")
                return {'CANCELLED'}
            claves = [c for c, _ in pesos]
            ws = [w for _, w in pesos]
            rng = random.Random(props.semilla + 33)
            n_b = 0
            for s in sorted(sol):
                t = rng.choices(claves, ws)[0]
                ob = bpy.data.objects.new("bloque_%s_%d_%d_%d" % (t, s[0], s[1], s[2]), mallas[t])
                ob.location = (s[0] + 0.5, s[1] + 0.5, s[2])
                col.objects.link(ob)
                n_b += 1
            # --- piezas de goteo y bultos
            goteo, n_e = {}, 0
            archivos = dict((a, b) for a, b, _w in PALETA)
            bulto_t = list(claves) + (["espeleotema"] if "espeleotema" not in claves else [])
            for clase, pieza, c in detalles:
                if clase == "bulto":
                    t = rng.choice(bulto_t)
                    me = mallas.get(t) or _malla_de_bloque(props.carpeta_bloques, archivos[t], base_col, t + "_base")
                    if me is None:
                        continue
                    nombre = "imperfeccion_%s_%d_%d_%d" % (t, c[0], c[1], c[2])
                    rz = 0.0
                else:
                    clave = (clase, pieza)
                    if clave not in goteo:
                        goteo[clave] = _malla_de_bloque(props.carpeta_bloques, PIEZAS_GOTEO[clase][pieza], base_col, "%s_%s_base" % (clase, pieza))
                    me = goteo[clave]
                    if me is None:
                        continue
                    nombre = "%s_%s_%d_%d_%d" % (clase, pieza, c[0], c[1], c[2])
                    rz = rng.choice([0.0, math.pi / 2, math.pi, 3 * math.pi / 2])
                ob = bpy.data.objects.new(nombre, me)
                ob.location = (c[0] + 0.5, c[1] + 0.5, c[2])
                ob.rotation_euler = (0.0, 0.0, rz)
                col.objects.link(ob)
                n_e += 1
            rep = _reparar_texturas(props.carpeta_texturas)
            if props.luz_activa:
                _crear_luz_entrada(props, p)
            alts = {}
            for (i, j, k) in aire:
                alts[(i, j)] = alts.get((i, j), 0) + 1
            props.ultimo_resumen = "%s: %d bloques + %d detalles, aire %d, alto medio %.1f, %d planos borrados, %d texturas reparadas, %.1f s" % (
                p.tipo, n_b, n_e, len(aire), sum(alts.values()) / max(1, len(alts)), borradas, rep, time.time() - t0)
            self.report({'INFO'}, props.ultimo_resumen)
            return {'FINISHED'}

    class CUEVAS_OT_borrar(Operator):
        bl_idname = "cuevas.borrar"
        bl_label = "Borrar cueva"
        bl_description = "Borra todos los bloques de la coleccion de la cueva"
        bl_options = {'REGISTER', 'UNDO'}

        def execute(self, context):
            n = limpiar_coleccion(context.scene.cuevas_props.coleccion)
            self.report({'INFO'}, "Bloques borrados: %d" % n)
            return {'FINISHED'}

    class CUEVAS_OT_cursor(Operator):
        bl_idname = "cuevas.usar_cursor"
        bl_label = "Entrada = cursor 3D"
        bl_description = "Usa la posicion del cursor 3D como entrada (superficie)"

        def execute(self, context):
            context.scene.cuevas_props.entrada = context.scene.cursor.location
            return {'FINISHED'}

    class CUEVAS_OT_comprobar(Operator):
        bl_idname = "cuevas.comprobar"
        bl_label = "Comprobar cierre y luz"
        bl_description = "Lanza rayos desde el interior: la cueva debe estar cerrada y el pozo abierto al cielo; avisa de luces dentro"
        bl_options = {'REGISTER'}

        def execute(self, context):
            import mathutils
            sc = context.scene
            props = sc.cuevas_props
            col = bpy.data.collections.get(props.coleccion)
            if col is None or not col.objects:
                self.report({'ERROR'}, "No hay cueva generada")
                return {'CANCELLED'}
            p = _parametros(props)
            aire, pozo = generar_aire(p)
            dg = context.evaluated_depsgraph_get()
            rng = random.Random(5)
            fugas = 0
            muestra = rng.sample(sorted(aire), min(40, len(aire)))
            dirs = [(math.cos(a), math.sin(a), 0.07 * ((q % 3) - 1)) for q, a in enumerate([q * math.pi / 4 + 0.11 for q in range(8)])] + [(0.01, 0.02, -1)]
            for (i, j, k) in muestra:
                o = mathutils.Vector((i + 0.37, j + 0.43, k + 0.51))
                for d in dirs:
                    hit, loc, n, idx, ob, m = sc.ray_cast(dg, o, mathutils.Vector(d).normalized(), distance=400)
                    if not hit or ob.name.split("_")[0] not in ("bloque", "imperfeccion", "estalactita", "estalagmita"):
                        fugas += 1          # el rayo salio sin chocar con un bloque de la cueva
                        break
            px, py = p.celda_pozo
            hit, loc, n, idx, ob, m = sc.ray_cast(dg, mathutils.Vector((px + 0.5, py + 0.5, p.k_fondo_pozo + 0.5)), mathutils.Vector((0, 0, 1)), distance=1000)
            abierto = not hit
            x = [c[0] for c in aire]; y = [c[1] for c in aire]; z = [c[2] for c in aire]
            dentro = []
            for l in sc.objects:
                if l.type == 'LIGHT':
                    q = l.matrix_world.translation
                    if min(x) <= q.x <= max(x) + 1 and min(y) <= q.y <= max(y) + 1 and min(z) <= q.z <= max(z) + 1:
                        dentro.append(l.name)
            msg = "puntos %d, fugas %d, pozo abierto al cielo: %s, luces dentro de la cueva: %s" % (len(muestra), fugas, "si" if abierto else "NO", dentro or "ninguna")
            self.report({'INFO'} if fugas == 0 and abierto and not dentro else {'WARNING'}, msg)
            props.ultimo_resumen = msg
            return {'FINISHED'}

    class CUEVAS_OT_luz(Operator):
        bl_idname = "cuevas.luz_entrada"
        bl_label = "Crear / actualizar luz de entrada"
        bl_description = "Crea (o actualiza) la luz que entra por el agujero y se dispersa por la cueva"
        bl_options = {'REGISTER', 'UNDO'}

        def execute(self, context):
            props = context.scene.cuevas_props
            ob = _crear_luz_entrada(props, _parametros(props))
            self.report({'INFO'}, "Luz '%s' en (%.1f, %.1f, %.1f)" % (ob.name, *ob.location))
            return {'FINISHED'}

    class CUEVAS_PT_panel(Panel):
        bl_label = "Generador de cuevas"
        bl_idname = "CUEVAS_PT_panel"
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_category = "Cuevas"

        def draw(self, context):
            l = self.layout
            pr = context.scene.cuevas_props
            l.prop(pr, "tipo", text="")
            b = l.box()
            b.label(text="Entrada y pozo", icon='TRIA_DOWN')
            b.prop(pr, "entrada", text="")
            b.operator("cuevas.usar_cursor", icon='PIVOT_CURSOR')
            b.prop(pr, "pozo")
            b = l.box()
            b.label(text="Forma", icon='MOD_BUILD')
            if pr.tipo == 'TUNEL':
                b.prop(pr, "alto"); b.prop(pr, "ancho"); b.prop(pr, "largo_lado")
                b.prop(pr, "curva_largo"); b.prop(pr, "curva_oeste_dz"); b.prop(pr, "curva_este_dz"); b.prop(pr, "curva_giro")
                b.prop(pr, "techo_max")
                b.prop(pr, "relieve"); b.prop(pr, "alcobas"); b.prop(pr, "pilares")
            else:
                b.prop(pr, "tam_caverna")
                if pr.tipo in ('GUSANO', 'MIXTA'):
                    b.prop(pr, "num_tuneles"); b.prop(pr, "largo_tunel")
                if pr.tipo == 'MIXTA':
                    b.prop(pr, "relieve")
            b = l.box()
            b.label(text="Detalles", icon='MOD_PARTICLES')
            b.prop(pr, "estalactitas"); b.prop(pr, "estalagmitas"); b.prop(pr, "bultos")
            b.prop(pr, "semilla")
            b = l.box()
            b.prop(pr, "mostrar_paleta", icon='TRIA_DOWN' if pr.mostrar_paleta else 'TRIA_RIGHT', emboss=False)
            if pr.mostrar_paleta:
                for clave, _f, _w in PALETA:
                    b.prop(pr, _peso(clave))
            b = l.box()
            b.label(text="Luz de entrada", icon='LIGHT_SPOT')
            b.prop(pr, "luz_activa")
            b.prop(pr, "luz_sol_fuerza")
            b.prop(pr, "luz_potencia"); b.prop(pr, "luz_cono"); b.prop(pr, "luz_color", text="")
            b.operator("cuevas.luz_entrada", icon='LIGHT')
            b = l.box()
            b.prop(pr, "coleccion"); b.prop(pr, "coleccion_terreno")
            b.prop(pr, "carpeta_bloques"); b.prop(pr, "carpeta_texturas")
            r = l.row(align=True)
            r.scale_y = 1.5
            r.operator("cuevas.generar", icon='MESH_CUBE')
            r.operator("cuevas.borrar", icon='TRASH')
            l.operator("cuevas.comprobar", icon='LIGHT')
            if pr.ultimo_resumen:
                for linea in [pr.ultimo_resumen[i:i + 44] for i in range(0, len(pr.ultimo_resumen), 44)]:
                    l.label(text=linea)

    CLASES = (CuevasProps, CUEVAS_OT_generar, CUEVAS_OT_borrar, CUEVAS_OT_cursor, CUEVAS_OT_comprobar, CUEVAS_OT_luz, CUEVAS_PT_panel)

    def register():
        for c in CLASES:
            bpy.utils.register_class(c)
        bpy.types.Scene.cuevas_props = PointerProperty(type=CuevasProps)

    def unregister():
        del bpy.types.Scene.cuevas_props
        for c in reversed(CLASES):
            bpy.utils.unregister_class(c)

    if __name__ == "__main__":
        register()
