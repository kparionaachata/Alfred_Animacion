# -*- coding: utf-8 -*-
"""
tunel_jerry.py -- Jerry Animation Studio: TUNEL AUTOMATICO PARA UN PERSONAJE DE 1x1 m (Jerry). Das la coordenada de INICIO y la FINAL y Jerry pica su propio tunel.

QUE HACE (todo automatico, repetible con `quitar`):
  1. RUTA recta de celdas de 1 m; la z solo cambia de 1 m en 1 m (escalones con el SALTO de Jerry, `DogJumpCycle`). Corredor de `alto` = 1 bloque (Jerry mide ~0.8 m x 1.47 m),
     mas alto junto a un escalon. Se cava `columnas_extra` (1) columna MAS ALLA del final: el cuerpo de Jerry es largo y el hocico entraria en la roca.
  2. JERRY: al empezar baja la cabeza (spine_1 / spine_2 / spine_3), abre la boca (`jaw_bot`) y RECOGE con la boca un pico de piedra propio (`tunel_jerry_pico`, copia de `stone_pickaxe`);
     para PICAR levanta la cabeza y la baja de golpe (tierra 1 golpe, piedra 3); un bloque a la vez, de arriba abajo; camina con el ciclo del estudio (SniffingSearchCycle) y salta
     los escalones. NUNCA rota `scull` / `scull_1` (deforma el ojo izquierdo): la cabeza se mueve con `spine_2`. Se para `atras` m detras de cada columna (hocico a ~0.45 m de la cara).
  3. LLEGADA: las pausas entre bloques se reparten para que llegue a la coordenada FINAL exactamente en `frame_llegada` (2020 por omision).
  4. GEOMETRIA: la misma del tunel de Alfred (`alfred_animation_studio/tunel.py`): bloques enteros de `bloques_dinamicos`, piedra segun la profundidad, relleno del aire, items que
     caen y absorbe; con nombres propios (coleccion `tunel_jerry`, objetos `tunel_jerry_*`, acciones `tjerry_*`) para no tocar el tunel de Alfred. No pone bloques donde ya hay uno de
     otro tunel. CREAR PRIMERO EL TUNEL DE ALFRED y despues este.
"""
import json
import math
import os

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

COL = "tunel_jerry"; PREF = "tunel_jerry_"; ACC = "tjerry_"
DIRS = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
ss = lambda t: 0.0 if t <= 0 else (1.0 if t >= 1 else t * t * (3 - 2 * t))
PIEDRAS = {"Stone", "Andesite", "Coal_Ore", "Iron_Ore", "Copper_Ore", "Lapis_Lazuli_Ore", "Cobblestone", "Mossy_Cobblestone", "Diorite", "Granite", "Deepslate"}
_aqui = os.path.dirname(os.path.abspath(__file__))
BLOQUES_DIR = next((d for d in (os.path.normpath(os.path.join(_aqui, os.pardir, os.pardir, os.pardir, os.pardir, "bloques_dinamicos")),
                                r"C:\Users\user\Desktop\Alfred_Animacion\bloques_dinamicos") if os.path.isdir(d)), r"C:\Users\user\Desktop\Alfred_Animacion\bloques_dinamicos")


def _mixM(A, B, t):
    la, qa, sa = A.decompose(); lb, qb, sb = B.decompose()
    return Matrix.Translation(la.lerp(lb, t)) @ qa.slerp(qb, t).to_matrix().to_4x4() @ Matrix.Diagonal(tuple(sa.lerp(sb, t)) + (1,))


# ============================================================================================================================ mundo y ruta (del tunel de Alfred)
def celda_de(p): return (int(math.floor(p[0])), int(math.floor(p[1])), int(math.floor(round(p[2], 6))))


class Mundo:
    """consultas sobre el terreno (rayos) ANTES de editar las mallas"""
    def __init__(self, sc, ignorar):
        self.sc = sc; self.dg = bpy.context.evaluated_depsgraph_get(); self.ignorar = set(ignorar); self.cache = {}; self.cache_dir = {}
        self.stone = [o for o in bpy.data.objects if o.type == "MESH" and o.name in PIEDRAS]
    def solida(self, c):
        """celda roca (6 rayos: la primera superficie en cada direccion es una cara DE ESPALDA)"""
        if c in self.cache: return self.cache[c]
        p = Vector((c[0] + .5, c[1] + .5, c[2] + .5)); n = 0.0
        for d in DIRS:
            dv = Vector(d); ok, loc, nor, idx, ob, mat = self.sc.ray_cast(self.dg, p, dv, distance=40)
            if ok and nor.dot(dv) > 0: n += 1
            elif not ok: n += 0.3
        self.cache[c] = n >= 4; return self.cache[c]
    def solido_hacia(self, fc, d):
        """el vecino al otro lado de la cara compartida es roca? (rayo desde la cara: sin impacto o cara de frente = aire)"""
        k = (round(fc[0] * 2), round(fc[1] * 2), round(fc[2] * 2), d)
        if k not in self.cache_dir:
            dv = Vector(d); ok, loc, nor, idx, ob, mat = self.sc.ray_cast(self.dg, Vector(fc) + dv * 0.01, dv, distance=60)
            self.cache_dir[k] = bool(ok and nor.dot(dv) > 0)
        return self.cache_dir[k]
    def preparar_piedra(self, caja):
        """vertices (mundo) de las mallas de piedra dentro de `caja` = (xmin, xmax, ymin, ymax, zmin, zmax), para clasificar las celdas"""
        pts = []
        for o in self.stone:
            n = len(o.data.vertices)
            if n == 0: continue
            co = np.empty(n * 3); o.data.vertices.foreach_get("co", co); co = co.reshape(n, 3); M = np.array(o.matrix_world); w = co @ M[:3, :3].T + M[:3, 3]
            ok = (w[:, 0] >= caja[0]) & (w[:, 0] <= caja[1]) & (w[:, 1] >= caja[2]) & (w[:, 1] <= caja[3]) & (w[:, 2] >= caja[4]) & (w[:, 2] <= caja[5]); pts.append(w[ok])
        self.sv = np.concatenate(pts) if pts else np.zeros((0, 3))
    def piedra(self, c):
        if not hasattr(self, "sv") or len(self.sv) == 0: return False
        p = np.array([c[0] + .5, c[1] + .5, c[2] + .5]); return int((np.linalg.norm(self.sv - p, axis=1) < 0.9).sum()) >= 3


def hacer_tipo(cfg, mundo):
    """tipo de bloque de una celda: piedra real del mundo, o por PROFUNDIDAD (cuanto mas se baja mas piedra; abajo solo piedra)"""
    z_ini, z_fin = cfg.get("z_ini"), cfg.get("z_fin")
    def prof(c):
        if z_ini is None or z_fin is None or z_ini == z_fin: return cfg["pct_piedra"]
        return max(0.0, min(1.0, (z_ini - c[2]) / float(z_ini - z_fin)))
    def tipo(c):
        h = ((c[0] * 73856093) ^ (c[1] * 19349663) ^ (c[2] * 83492791) ^ (cfg["semilla"] * 2654435761)) & 0xFFFFFF
        return "piedra" if (mundo.piedra(c) or (h / float(0x1000000)) < prof(c) or prof(c) >= 0.999) else "tierra"
    return tipo


# ============================================================================================================================ ruta
def construir_ruta(ini, fin):
    """celdas 4-conectadas de `ini` a `fin` (x, y enteros) repartiendo los pasos de x e y; z de la raiz lineal. Devuelve (lista de celdas (cx, cy), z de la raiz por celda)."""
    ax, ay = int(math.floor(ini[0])), int(math.floor(ini[1])); bx, by = int(math.floor(fin[0])), int(math.floor(fin[1]))
    cel = [(ax, ay)]; x, y = ax, ay
    while (x, y) != (bx, by):
        rx, ry = bx - x, by - y
        if abs(rx) * 1.0 >= abs(ry) * 1.0 and rx != 0 and (ry == 0 or abs(rx) / max(1, abs(bx - ax)) >= abs(ry) / max(1, abs(by - ay))): x += 1 if rx > 0 else -1
        elif ry != 0: y += 1 if ry > 0 else -1
        else: x += 1 if rx > 0 else -1
        cel.append((x, y))
    n = len(cel) - 1
    zs = [int(round(ini[2] + (fin[2] - ini[2]) * (i / n if n else 0))) for i in range(n + 1)]       # la z solo cambia de 1 m en 1 m (con la animacion de saltar subir / bajar), nunca valores como 6.36
    return cel, zs



# ============================================================================================================================ geometria (del tunel de Alfred, nombres propios)
def _romper_claves(tC, base, previos=()):
    """romper un bloque (animacion_alfred (7), `refugio_bloque_06`): CADA golpe previo lo hace temblar ~1 cm y lo agrieta (escala .97 tras el 1.º, .94 tras el 2.º); en el golpe final se encoge en 3 f (.857 -> .533 -> .159) y desaparece"""
    off = [(0.002, 0.01, 0.005), (0.002, -0.006, -0.003), (-0.003, 0.003, -0.001), (0.0, 0.0, 0.0)]
    golpes = [h for h in previos] + [tC]; esc = [0.97, 0.94]
    loc = {ax: [(golpes[0] - 5, base[ax])] for ax in range(3)}
    sca = [(1, 1.0)]
    for n_, h in enumerate(golpes):
        ini = h - 3 if n_ == len(golpes) - 1 else h                                         # el golpe final tiembla 3 f ANTES de romperse; los previos desde el impacto
        for ax in range(3):
            loc[ax] += [(ini + k, base[ax] + off[k][ax]) for k in range(4)]
        if n_ < len(golpes) - 1: sca.append((h, 1.0 if n_ == 0 else esc[n_ - 1])); sca.append((h + 1, esc[min(n_, 1)]))
        else: sca += [(tC - 1, esc[min(len(previos), 2) - 1] if previos else 0.97), (tC, 0.857), (tC + 1, 0.533), (tC + 2, 0.159)]
    ex = {}
    for ax in range(3):
        ex[("location", ax)] = loc[ax] + [(tC + 3, base[ax])]; ex[("scale", ax)] = sca
    return ex


def _vis(o, t_on, t_off, extras=None):
    pts = [(1, 1.0 if t_on > 1 else 0.0)]
    if t_on > 1: pts.append((t_on, 0.0))
    if t_off < 10 ** 5: pts.append((t_off, 1.0))
    o.hide_viewport = pts[0][1] > 0.5; o.hide_render = pts[0][1] > 0.5
    if o.animation_data is None: o.animation_data_create()
    a = bpy.data.actions.new(ACC + "vis_" + o.name); slot = a.slots.new(id_type='OBJECT', name=o.name); cb = a.layers.new("Capa").strips.new(type='KEYFRAME').channelbag(slot, ensure=True)
    for dp in ("hide_viewport", "hide_render"):
        fc = cb.fcurves.new(dp, index=0); fc.keyframe_points.add(len(pts)); fc.keyframe_points.foreach_set("co", [v for p in pts for v in p])
        for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
        fc.update()
    for (dp, i), ps in (extras or {}).items():
        ps = sorted(set(ps)); fc = cb.fcurves.new(dp, index=i); fc.keyframe_points.add(len(ps)); fc.keyframe_points.foreach_set("co", [v for q in ps for v in q])
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
        fc.update()
    o.animation_data.action = a; o.animation_data.action_slot = slot


def _cuadrado(fc, n):
    ax = [i for i in range(3) if n[i] != 0][0]; o1, o2 = [i for i in range(3) if i != ax]; pts = []
    for s1, s2 in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        v = [fc[0], fc[1], fc[2]]; v[o1] += .5 * s1; v[o2] += .5 * s2; pts.append(Vector(v))
    if (pts[1] - pts[0]).cross(pts[2] - pts[1]).dot(Vector(n)) < 0: pts.reverse()
    return pts


BLOQUE_ARCHIVO = {"tierra": ("bloque_de_tierra.blend", "dirt"), "piedra": ("bloque_de_stone.blend", "stone")}


def malla_bloque(tipo, carpeta=None):
    """malla del BLOQUE ENTERO (cubo de 1 m con sus 6 caras / materiales) de `bloques_dinamicos/bloque_de_tierra.blend` o `bloque_de_stone.blend`; se importa una vez y se comparte"""
    nom = "tunel_bloque_" + tipo
    if nom in bpy.data.meshes: return bpy.data.meshes[nom]
    arch, obn = BLOQUE_ARCHIVO[tipo]; ruta = os.path.join(carpeta or BLOQUES_DIR, arch)
    if not os.path.exists(ruta): raise RuntimeError("No existe %s" % ruta)
    with bpy.data.libraries.load(ruta, link=False) as (src, dst):
        if obn not in src.objects: raise RuntimeError("%s no tiene el objeto %r" % (arch, obn))
        dst.objects = [obn]
    ob = dst.objects[0]; me = ob.data; me.name = nom; me.use_fake_user = True
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    c = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2))
    me.transform(Matrix.Translation(-c))                                                   # el cubo del archivo parte de la BASE (z 0..1): se centra para que el origen sea el CENTRO del bloque
    bpy.data.objects.remove(ob, do_unlink=True)
    return me


def geometria(sc, cfg, mundo, eventos, corr_celdas, llegadas, ruta, rellenos=()):
    """pone los BLOQUES del tunel (sin superficies sueltas): tapas de las celdas cavadas (copias de sus caras originales), bloques de tierra / piedra para lo que se descubre, el cascaron y borra del mundo
    las caras que sustituyen / se rompen"""
    T = {}; HITS = {}
    for f, cs, hs in eventos:
        for c in cs: T[tuple(c)] = f; HITS[tuple(c)] = list(hs)
    if not T: return {"tapas": 0, "bloques": 0, "objetos": 0}
    xs = [c[0] for c in T]; ys = [c[1] for c in T]; zs_ = [c[2] for c in T]
    BOX = (min(xs) - 1.6, max(xs) + 2.6, min(ys) - 1.6, max(ys) + 2.6, min(zs_) - 1.6, max(zs_) + 2.6)
    ign = set(mundo.ignorar); INDEX = {}; PCL = []; PNL = []; POL = []
    def indexar(o):
        me = o.data; n = len(me.polygons)
        if n == 0: return
        c = np.empty(n * 3); nr = np.empty(n * 3); me.polygons.foreach_get("center", c); me.polygons.foreach_get("normal", nr); c = c.reshape(n, 3); nr = nr.reshape(n, 3)
        M = np.array(o.matrix_world); cw = c @ M[:3, :3].T + M[:3, 3]; nw = nr @ M[:3, :3].T; nw /= np.maximum(np.linalg.norm(nw, axis=1, keepdims=True), 1e-9)
        ok = np.where((cw[:, 0] >= BOX[0]) & (cw[:, 0] <= BOX[1]) & (cw[:, 1] >= BOX[2]) & (cw[:, 1] <= BOX[3]) & (cw[:, 2] >= BOX[4]) & (cw[:, 2] <= BOX[5]))[0]
        for i in ok: INDEX.setdefault((int(round(cw[i, 0] * 2)), int(round(cw[i, 1] * 2)), int(round(cw[i, 2] * 2))), []).append((o, int(i), nw[i].copy()))
        PCL.append(cw[ok]); PNL.append(nw[ok]); POL.extend((o, int(i)) for i in ok)
    for o in bpy.data.objects:
        if o.type != "MESH" or o.name in ign or o.name.startswith(("tunel_", "techo_tierra")): continue
        if o.parent is not None and o.parent.type == "ARMATURE": continue                      # personajes y herramientas (mallas con rig): NUNCA se tocan
        if any(m.type == "ARMATURE" for m in o.modifiers) or len(o.vertex_groups) > 0: continue
        bb = [o.matrix_world @ Vector(v) for v in o.bound_box]
        if max(b.x for b in bb) < BOX[0] or min(b.x for b in bb) > BOX[1] or max(b.y for b in bb) < BOX[2] or min(b.y for b in bb) > BOX[3] or max(b.z for b in bb) < BOX[4] or min(b.z for b in bb) > BOX[5]: continue
        indexar(o)
    PC = np.concatenate(PCL) if PCL else np.zeros((0, 3)); PN = np.concatenate(PNL) if PNL else np.zeros((0, 3))
    def en_plano(cell, e, tol=0.02):
        """TODAS las caras del mundo (cualquier orientacion, tamano o centro) que tocan la cara `e` de la celda: en su mismo plano (+-`tol`) y con el centro dentro del cuadrado de esa cara"""
        a = [i for i in range(3) if e[i] != 0][0]; u, v = [i for i in range(3) if i != a]
        fc = (cell[0] + .5 + .5 * e[0], cell[1] + .5 + .5 * e[1], cell[2] + .5 + .5 * e[2])
        if not len(PC): return []
        m = (np.abs(PN[:, a]) > 0.9) & (np.abs(PC[:, a] - fc[a]) < tol) & (np.abs(PC[:, u] - fc[u]) < 0.5 + 1e-3) & (np.abs(PC[:, v] - fc[v]) < 0.5 + 1e-3)
        return [POL[j] for j in np.where(m)[0]]
    malla = {"tierra": malla_bloque("tierra", cfg.get("bloques_dir")), "piedra": malla_bloque("piedra", cfg.get("bloques_dir"))}
    tipo = cfg["_tipo"]
    def key(fc): return (int(round(fc[0] * 2)), int(round(fc[1] * 2)), int(round(fc[2] * 2)))
    def caras_de(cell, e):                                                                  # caras originales del mundo en el lado `e` de la celda (con normal hacia fuera)
        fc = (cell[0] + .5 + .5 * e[0], cell[1] + .5 + .5 * e[1], cell[2] + .5 + .5 * e[2])
        return [(o, i) for (o, i, nw) in INDEX.get(key(fc), []) if nw[0] * e[0] + nw[1] * e[1] + nw[2] * e[2] > 0.9]
    celda_de = {}
    cubiertas = {}                                                                          # t_off -> caras originales de celdas cavadas (se copian a `tapa` y se borran)
    reemplazo = []                                                                          # caras originales de bloques que pasan a ser un bloque entero (se copian ocultas para poder deshacer)
    BL = {}                                                                                 # celda -> [tipo, t_on, t_off]
    fin_ruta = ruta[-cfg["final_abierto"]:] if cfg["final_abierto"] else []; dir_final = (0, 0)
    if len(ruta) > 1: dir_final = (ruta[-1][0] - ruta[-2][0], ruta[-1][1] - ruta[-2][1])
    ult_celdas = {c for c in T if (c[0], c[1]) in set(fin_ruta)}
    zona_final = cfg.get("_zona_final", set())
    def bloque(cell, tp, t_on, t_off):
        if (cell[0], cell[1]) in zona_final: return                                          # tramo final: no se generan bloques
        if cell in cfg.get("_ajenas", ()): return                                              # ya hay un bloque de OTRO tunel (Alfred) en esa celda: no se solapa
        if cell in BL: BL[cell][1] = min(BL[cell][1], t_on); BL[cell][2] = max(BL[cell][2], t_off)
        else: BL[cell] = [tp, t_on, t_off]
    import random as _random
    rng_r = _random.Random(cfg["semilla"] + 1); relleno = set(map(tuple, rellenos))
    for C in sorted(relleno):                                                                 # celdas de aire del corredor: bloque entero desde el inicio hasta que Alfred lo pica
        if C in T: bloque(C, tipo(C), 1, T[C])
    for C, tC in T.items():
        if C in relleno: continue
        if any(caras_de(C, e) for e in DIRS): bloque(C, tipo(C), 1, tC)                       # bloque REAL del mundo que se pica: pasa a ser un BLOQUE ENTERO (sus caras expuestas se quitan), no una superficie suelta
        for d in DIRS:
            propias = caras_de(C, d); N = (C[0] + d[0], C[1] + d[1], C[2] + d[2])
            if propias:
                cubiertas.setdefault(tC, []).extend(propias)
                for (o_, i_) in propias: celda_de[(id(o_), i_)] = C
            elif C in ult_celdas and (d[0], d[1]) == dir_final: continue                    # fondo abierto hacia la cueva
            elif N in T:
                if T[N] < tC and not any(caras_de(C, e) for e in DIRS): bloque(C, tipo(C), T[N], tC)     # (si C ya tiene caras expuestas propias se omite: se solaparian con las suyas hasta el golpe)                                  # C queda al descubierto cuando se rompe N y se rompe despues
            else:
                fc = (C[0] + .5 + .5 * d[0], C[1] + .5 + .5 * d[1], C[2] + .5 + .5 * d[2])
                if mundo.solido_hacia(fc, d): bloque(N, tipo(N), 1, 10 ** 6)                  # vecino de roca: pasa a ser un bloque entero (visible desde el inicio, tapado por la roca hasta que se rompe C)
    borrando = {(id(o), i) for lst in cubiertas.values() for (o, i) in lst}                 # caras del mundo que se van a quitar (no cuentan como existentes)
    def ocupada(cell):                                                                      # la celda ya es un bloque del mundo? (tiene una cara expuesta propia hacia fuera en algun lado)
        return any((id(o), i) not in borrando for e in DIRS for (o, i) in caras_de(cell, e))
    # cascaron de bloques enteros donde el corredor no tiene piso / paredes / techo
    if cfg["cascaron"]:
        import random
        rng = random.Random(cfg["semilla"]); cset = set(corr_celdas); n_ent = cfg["entrada_sin_cascaron"]; idx_de = {(r[0], r[1]): i for i, r in enumerate(ruta)}
        for C in corr_celdas:
            i = idx_de.get((C[0], C[1]), 0)
            if i < n_ent: continue
            t_on = max(2, llegadas.get(max(0, i - cfg["adelanto"]), 2))
            for d in DIRS:
                N = (C[0] + d[0], C[1] + d[1], C[2] + d[2])
                if N in cset or N in BL or N in T: continue
                if i >= len(ruta) - cfg["final_abierto"] and (d[0], d[1]) == dir_final: continue
                fc = (C[0] + .5 + .5 * d[0], C[1] + .5 + .5 * d[1], C[2] + .5 + .5 * d[2])
                if mundo.solido_hacia(fc, d): continue                                      # ya es roca
                if ocupada(N): continue                                                     # ya hay un bloque del mundo ahi: no se pone otro encima
                bloque(N, tipo(N), t_on, 10 ** 6)
    # los bloques que sustituyen roca / terreno existente: sus caras originales expuestas se quitan (el bloque entero las reemplaza)
    for cell, (tp, t_on, t_off) in BL.items():
        if cell in T: continue
        for e in DIRS:
            for (o, i) in caras_de(cell, e): reemplazo.append((o, i))
    # las superficies del mundo que quedan PEGADAS a un bloque del tunel (caras del bloque vecino que miran a la celda del bloque) se eliminan para que no se solapen con las del bloque:
    #  - bloque permanente (cascaron, roca vecina): se borran definitivamente (copia oculta solo para `quitar`);
    #  - bloque que Alfred rompe (relleno de aire): se mueven a un objeto que APARECE cuando el bloque desaparece (asi la pared sigue ahi al romperlo)
    reaparecen = {}
    for cell, (tp, t_on, t_off) in BL.items():
        for e in DIRS:
            fc = (cell[0] + .5 + .5 * e[0], cell[1] + .5 + .5 * e[1], cell[2] + .5 + .5 * e[2])
            facs = [(o, i) for (o, i) in en_plano(cell, e) if (id(o), i) not in borrando]
            if not facs: continue
            if cell in T: reaparecen.setdefault(T[cell] + 3, []).extend(facs)
            else: reemplazo.extend(facs)
    col = bpy.data.collections.get(COL) or bpy.data.collections.new(COL)
    if col.name not in [c.name for c in sc.collection.children]: sc.collection.children.link(col)
    n_obj = 0; BORRAR = {}
    for cell, (tp, t_on, t_off) in sorted(BL.items(), key=lambda kv: (kv[1][1], kv[0])):
        ob = bpy.data.objects.new(PREF + "bloque_%s_%d_%d_%d" % (tp, cell[0], cell[1], cell[2]), malla[tp]); ob.location = (cell[0] + 0.5, cell[1] + 0.5, cell[2] + 0.5)
        col.objects.link(ob)
        if cell in T: _vis(ob, t_on, T[cell] + 3, _romper_claves(T[cell], ob.location, HITS.get(cell, ())))                       # celda cavada: tiembla y se rompe
        else: _vis(ob, t_on, t_off)
        n_obj += 1
    def copiar(lista, nombre, t_on, t_off, por_celda=False):
        por = {}
        for o, i in {(id(o), i): (o, i) for o, i in lista}.values(): por.setdefault((o, celda_de.get((id(o), i)) if por_celda else None), set()).add(i)
        for (o, cell), idx in por.items():
            origen = Vector((cell[0] + .5, cell[1] + .5, cell[2] + .5)) if cell else Vector((0.0, 0.0, 0.0))
            me = o.data; mw = o.matrix_world; uvd = me.uv_layers[0].data if me.uv_layers else None; bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
            for i in sorted(idx):
                p = me.polygons[i]
                try: f = bm.faces.new([bm.verts.new(mw @ me.vertices[vi].co - origen) for vi in p.vertices])
                except ValueError: continue
                f.material_index = p.material_index
                if uvd:
                    for l, li in zip(f.loops, p.loop_indices): l[uvl].uv = uvd[li].uv
            mc = bpy.data.meshes.new("tunel_tapa_m"); bm.to_mesh(mc); bm.free()
            for m in me.materials: mc.materials.append(m)
            ob = bpy.data.objects.new(PREF + "tapa_%s_%s" % (o.name, nombre), mc); ob["tunel_origen"] = o.name; ob["tunel_base"] = [origen.x, origen.y, origen.z]; ob.location = origen; col.objects.link(ob)
            if cell is not None and cell in T: _vis(ob, t_on, T[cell] + 3, _romper_claves(T[cell], origen, HITS.get(cell, ())))
            else: _vis(ob, t_on, t_off)
            BORRAR.setdefault(o, set()).update(idx)
    vistas = set(borrando)                                                                  # cada cara del mundo va a UNA sola copia (si no, `quitar` la devolveria dos veces)
    for k_ in sorted(reaparecen):
        reaparecen[k_] = [x for x in {(id(o_), i_): (o_, i_) for o_, i_ in reaparecen[k_]}.values() if (id(x[0]), x[1]) not in vistas]
        vistas.update((id(o_), i_) for o_, i_ in reaparecen[k_])
    reemplazo[:] = [x for x in {(id(o_), i_): (o_, i_) for o_, i_ in reemplazo}.values() if (id(x[0]), x[1]) not in vistas]
    cav = [x for lista in cubiertas.values() for x in lista]
    if cav: copiar(cav, "cavadas", 10 ** 6, 10 ** 7); n_obj += 1                                 # caras originales de las celdas cavadas: las reemplaza el bloque entero; se quitan del mundo (copia oculta solo para `quitar`)
    for t_ap, lista in sorted(reaparecen.items()): copiar(lista, "pared_%d" % t_ap, t_ap, 10 ** 6); n_obj += 1
    if reemplazo: copiar(reemplazo, "sustituidas", 10 ** 6, 10 ** 7); n_obj += 1                # caras del mundo que sustituye / tapa un bloque: se quitan (copia oculta solo para `quitar`)
    # lo que suelta cada bloque roto, COMO EN MINECRAFT: el mini bloque (escala .25) CAE al SUELO del tunel (rebota un poco y queda girando), y cuando Alfred esta a menos de 1.5 m lo ABSORBE:
    # vuela a su pecho encogiendose (animacion_alfred (8), `drop_tablon`) y desaparece
    pos_a = cfg.get("_pos_alfred"); piso = cfg.get("_piso")
    if pos_a is not None:
        for cell, tC in sorted(T.items(), key=lambda kv: kv[1]):
            tp = tipo(cell); ob = bpy.data.objects.new(PREF + "item_%d_%d_%d" % cell, malla[tp]); ob.scale = (0.25, 0.25, 0.25); col.objects.link(ob)
            h_ = ((cell[0] * 73856093) ^ (cell[1] * 19349663) ^ (cell[2] * 83492791)) & 0xFFFF
            cx_ = cell[0] + .5 + ((h_ & 0xFF) / 255.0 - 0.5) * 0.3; cy_ = cell[1] + .5 + (((h_ >> 8) & 0xFF) / 255.0 - 0.5) * 0.3
            z0 = cell[2] + .5; zf = (piso(cell) if piso else cell[2]) + 0.125; hh = max(0.0, z0 - zf); fall = max(4, int(round(5.5 * math.sqrt(max(hh, 0.3)))))
            land = tC + fall
            ex = {("location", 0): [], ("location", 1): [], ("location", 2): [], ("scale", 0): [], ("scale", 1): [], ("scale", 2): []}
            for k in sorted({0, max(1, fall // 3), max(2, 2 * fall // 3), fall}):               # caida (cuadratica) hasta el suelo del tunel
                z = z0 - (z0 - zf) * (k / float(fall)) ** 2
                for ax, v in enumerate((cx_, cy_, z)): ex[("location", ax)].append((tC + k, v))
            for k, dz in ((2, 0.1), (4, 0.0)):                                                  # rebote pequeno
                for ax, v in enumerate((cx_, cy_, zf + dz)): ex[("location", ax)].append((land + k, v))
            t_pick = land + 6
            for f_ in range(land + 6, land + 96):                                               # lo recoge cuando Alfred esta cerca
                pa = pos_a(f_)
                if math.hypot(pa[0] - cx_, pa[1] - cy_) < 1.5 and abs(pa[2] - (zf - 0.125)) < 1.5: t_pick = f_; break
            ax_, ay_, az_ = pos_a(t_pick + 6); az_ += cfg.get("alto_pecho", 1.1)
            for k in (2, 4, 6):                                                                  # vuela al pecho de Alfred encogiendose
                u = ss(k / 6.0)
                for ax, (v0, v1) in enumerate(((cx_, ax_), (cy_, ay_), (zf, az_))): ex[("location", ax)].append((t_pick + k, v0 + (v1 - v0) * u))
            for ax in range(3): ex[("scale", ax)] = [(tC, 0.25), (t_pick, 0.25), (t_pick + 2, 0.25 * (1 - ss(2 / 6.0))), (t_pick + 4, 0.25 * (1 - ss(4 / 6.0))), (t_pick + 6, 0.0)]
            ex[("rotation_euler", 2)] = [(tC, 0.0), (t_pick + 6, 2 * math.pi * (t_pick + 6 - tC) / 15.0)]
            _vis(ob, tC, t_pick + 7, ex); n_obj += 1
    borradas = 0
    for o, idx in BORRAR.items():
        me = o.data; b2 = bmesh.new(); b2.from_mesh(me); b2.faces.ensure_lookup_table()
        bmesh.ops.delete(b2, geom=[b2.faces[i] for i in sorted(idx)], context='FACES_ONLY'); b2.to_mesh(me); b2.free(); me.update(); borradas += len(idx)
    return {"tapas": sum(len(v) for v in cubiertas.values()), "bloques": len(BL), "objetos": n_obj, "borradas": borradas, "diag": {"cubiertas": sum(len(v) for v in cubiertas.values()), "reemplazo": len(reemplazo), "reaparecen": sum(len(v) for v in reaparecen.values()), "PC": int(len(PC)), "BL": len(BL)}, "_BL": dict(BL)}



def quitar(sc):
    """deshace el tunel: devuelve a las mallas originales las caras borradas, quita los objetos `tunel_*` y las acciones `tunel_*`"""
    col = bpy.data.collections.get(COL); n_rest = 0
    if col:
        for ob in list(col.objects):
            if ob.name.startswith(PREF + "tapa_") and ob.get("tunel_origen") in bpy.data.objects:
                src = bpy.data.objects[ob["tunel_origen"]]; inv = src.matrix_world.inverted(); me = src.data
                bm = bmesh.new(); bm.from_mesh(me); uvl = bm.loops.layers.uv.verify() if me.uv_layers else None; sm = ob.data
                uvd = sm.uv_layers[0].data if sm.uv_layers else None
                for p in sm.polygons:
                    try: f = bm.faces.new([bm.verts.new(inv @ (Matrix.Translation(Vector(ob.get("tunel_base", (0.0, 0.0, 0.0)))) @ sm.vertices[vi].co)) for vi in p.vertices])
                    except ValueError: continue
                    f.material_index = p.material_index
                    if uvl and uvd:
                        for l, li in zip(f.loops, p.loop_indices): l[uvl].uv = uvd[li].uv
                    n_rest += 1
                bm.to_mesh(me); bm.free(); me.update()
        for ob in list(col.objects):
            me = ob.data; bpy.data.objects.remove(ob, do_unlink=True)
            if me and me.users == 0: bpy.data.meshes.remove(me)
        bpy.data.collections.remove(col)
    for o in bpy.data.objects:                                                     # soltar las acciones `tunel_*` de Alfred, de las herramientas y de lo que sea
        if o.animation_data and o.animation_data.action and o.animation_data.action.name.startswith(ACC): o.animation_data.action = None
    for a in list(bpy.data.actions):
        if a.name.startswith(ACC) and a.users == 0: bpy.data.actions.remove(a)
    try:
        ROOT, ARM = rig_jerry()
        for o in (ROOT, ARM):
            if o.animation_data and o.animation_data.action and o.animation_data.action.name.startswith(ACC): o.animation_data.action = None
    except RuntimeError: pass
    for a in list(bpy.data.actions):
        if a.name.startswith(ACC) and a.users == 0: bpy.data.actions.remove(a)
    return n_rest




# ============================================================================================================================ JERRY: rig y huesos
def rig_jerry():
    arm = next((o for o in bpy.data.objects if o.type == "ARMATURE" and "scull_1" in o.pose.bones and "jaw_bot" in o.pose.bones), None)
    if arm is None: raise RuntimeError("No se encontro el armature de Jerry (con los huesos scull_1 / jaw_bot)")
    return arm.parent or arm, arm


NB_TODOS = ['shoulder.L', 'shoulder.R', 'thigh.L', 'thigh.R', 'shin.L', 'shin.R', 'foot.L', 'foot.R', 'toe.L', 'toe.R', 'front_shoulder.L', 'front_shoulder.R', 'front_thigh.L', 'front_thigh.R',
            'front_shin.L', 'front_shin.R', 'front_foot.L', 'front_foot.R', 'front_toe.L', 'front_toe.R'] + ['spine_%d' % i for i in range(1, 8)] + ['tail_%d' % i for i in range(1, 4)] + \
           ['scull', 'scull_1', 'jaw_top', 'jaw_bot', 'ear.L', 'ear.R', 'sombrero']
SIN_ROTAR = ('scull', 'scull_1')                                                    # NUNCA se rotan (`scull` deforma la malla sobre el ojo izquierdo): la cabeza se mueve con `spine_2` / `spine_1`
sw = lambda f, p, a, ph=0, off=0: a * math.sin(2 * math.pi * f / p + ph) + off
ease_in_out = lambda t: t * t * (3 - 2 * t); ease_out = lambda t: 1 - (1 - t) * (1 - t); ease_in = lambda t: t * t
mul = lambda v, m: tuple(x * m for x in v)


class Ciclo:
    """ciclo de caminar de Jerry (SniffingSearchCycle del estudio: `caminar_animacion_jerry.py`), con su ciclo `CL` y amplitudes `RM`"""
    def __init__(self, CL=25, RM=None):
        self.CL = CL; self.RM = RM or {'leg': 1.0, 'leg_front': 1.0, 'spine': 1.0, 'tail': 1.0, 'head': 1.0, 'ear': 1.0}; self.HALF = CL // 2
    def nrm(self, fr): return ((fr - 1) % self.CL) + 1
    def leg_slow(self, fr, rear, left):
        n = self.nrm(fr); ph = 0 if left else math.pi; amp = (0.4 if rear else 0.3) * (self.RM['leg'] if rear else self.RM['leg_front'])
        return (-sw(n, self.CL, amp, ph), -sw(n, self.CL, amp * 0.15, ph), -sw(n, self.CL, amp * 0.03, ph))
    def leg_bend(self, fr, rear, left):
        n = self.nrm(fr); ph = 0 if left else math.pi; bb = (0.3 if rear else 0.24) * (self.RM['leg'] if rear else self.RM['leg_front'])
        return (-abs(sw(n, self.CL, bb, ph, bb)), -sw(n, self.CL, 0.1, ph), -sw(n, self.CL, 0.04, ph))
    def foot_strike(self, fr, rear, left):
        n = self.nrm(fr); ph = 0 if left else math.pi; ax = (0.8 if rear else 0.6) * (self.RM['leg'] if rear else self.RM['leg_front'])
        return (-sw(n, self.CL, ax, ph, 0.4 if rear else -0.1), abs(sw(n, self.CL, 0.04, ph, 0.02)) * (1.0 if rear else 0.5), -sw(n, self.CL, 0.04 if rear else 0.06, ph, 0.02))
    def toe_curl(self, fr, rear, left):
        n = self.nrm(fr); ph = 0 if left else math.pi; amp = 0.5 * (self.RM['leg'] if rear else self.RM['leg_front'])
        return (abs(sw(n, self.CL, amp, ph, 0.4)), -sw(n, self.CL, 0.16, ph), -sw(n, self.CL, 0.08, ph, 0.04))
    def pose(self, fr):
        k = {}; H = self.HALF; CL = self.CL; RM = self.RM
        for s, left in (('L', True), ('R', False)):
            k['shoulder.' + s] = self.leg_slow(fr, True, left); k['shin.' + s] = self.leg_bend(fr, True, left); k['foot.' + s] = self.foot_strike(fr, True, left); k['toe.' + s] = self.toe_curl(fr, True, left)
            k['front_shoulder.' + s] = self.leg_slow(fr + H, False, left); k['front_shin.' + s] = self.leg_bend(fr + H, False, left)
            k['front_foot.' + s] = self.foot_strike(fr + H, False, left); k['front_toe.' + s] = self.toe_curl(fr + H, False, left)
        k['thigh.L'] = mul(self.leg_slow(fr, True, True), 0.01); k['thigh.R'] = mul(self.leg_slow(fr, True, False), -0.3)
        k['front_thigh.L'] = mul(self.leg_slow(fr + H, False, True), 0.6); k['front_thigh.R'] = mul(self.leg_slow(fr + H, False, False), 0.4)
        n = self.nrm(fr)
        for i in range(1, 8): k['spine_%d' % i] = (-sw(n, CL, 0.03 * RM['spine'], (i / 7) * math.pi, -0.08 * RM['spine']), 0, 0)
        for i in range(1, 4): k['tail_%d' % i] = (sw(n, CL, 0.4 * RM['tail'], 0, 0.2 * RM['tail']), sw(n, CL, 0.06 * RM['tail']), sw(n, CL, 0.16 * RM['tail']))
        k['spine_2'] = (k['spine_2'][0] + sw(n, CL, 0.03 * RM['head']), sw(n, CL, 0.05 * RM['head']), 0)        # el cabeceo de la caminata va a `spine_2` (no a `scull`)
        k['ear.L'] = (0, sw(n, CL, 0.2 * RM['ear']), sw(n, CL, 0.1 * RM['ear'])); k['ear.R'] = (0, sw(n + 6, CL, 0.2 * RM['ear']), sw(n + 6, CL, 0.1 * RM['ear']))
        return k


class DogJumpCycle:
    """salto de Jerry (`saltar_subir_animacion_jerry.py`, DogJumpCycle, 15 f)"""
    def __init__(self): self.impulse_frames = (1, 5); self.jump_frames = (6, 11); self.fall_frames = (12, 15)
    def get_phase_progress(self, frame):
        for (s, e), phase in [(self.impulse_frames, 'impulse'), (self.jump_frames, 'jump'), (self.fall_frames, 'fall')]:
            if s <= frame <= e: return phase, (frame - s) / max(1, e - s)
        return 'neutral', 0
    def _tri(self, frame, imp, jmp, fal):
        ph, pr = self.get_phase_progress(frame)
        return imp(pr) if ph == 'impulse' else jmp(pr) if ph == 'jump' else fal(pr) if ph == 'fall' else (0, 0, 0)
    def rear_thigh(self, f, L=True):
        s = 1 if L else -1
        return self._tri(f, lambda p: (-ease_in_out(p) * 0.20, sw(p * 6, 6, 0.03 * s), sw(p * 4, 4, 0.02)), lambda p: (-ease_out(p) * 0.25, sw(p * 12, 12, 0.015 * s), sw(p * 10, 10, 0.025)), lambda p: (-ease_in(p) * 0.15, sw(p * 8, 8, 0.01 * s), sw(p * 6, 6, -0.01)))
    def rear_shin(self, f, L=True):
        s = 1 if L else -1
        return self._tri(f, lambda p: (-ease_in_out(p) * 0.18, sw(p * 8, 8, 0.02 * s), sw(p * 6, 6, 0.015)), lambda p: (-ease_out(p) * 0.22, sw(p * 12, 12, 0.01 * s), sw(p * 8, 8, 0.02)), lambda p: (-ease_in(p) * 0.12, sw(p * 8, 8, 0.008 * s), sw(p * 4, 4, 0.01)))
    def rear_foot(self, f, L=True):
        s = 1 if L else -1
        return self._tri(f, lambda p: (-ease_in_out(p) * 0.15, sw(p * 12, 12, 0.03 * s), sw(p * 10, 10, 0.02)), lambda p: (-ease_out(p) * 0.18, sw(p * 25, 25, 0.02 * s), sw(p * 15, 15, 0.03)), lambda p: (-ease_in(p) * 0.1, sw(p * 15, 15, 0.01 * s), sw(p * 8, 8, 0.015)))
    def rear_toe(self, f, L=True):
        return self._tri(f, lambda p: (ease_in_out(p) * 0.12, 0, 0), lambda p: (ease_out(p) * 0.08, 0, 0), lambda p: (ease_in(p) * 0.05, 0, 0))
    def front_thigh(self, f, L=True):
        s = 1 if L else -1
        return self._tri(f, lambda p: (-ease_in_out(p) * 0.1, sw(p * 8, 8, 0.04 * s), sw(p * 6, 6, -0.02)), lambda p: (ease_out(p) * 0.35, sw(p * 15, 15, 0.03 * s), sw(p * 12, 12, 0.04)), lambda p: (-ease_in(p) * 0.3, sw(p * 10, 10, 0.02 * s), sw(p * 8, 8, 0.02)))
    def front_shin(self, f, L=True):
        s = 1 if L else -1
        return self._tri(f, lambda p: (-ease_in_out(p) * 0.15, sw(p * 10, 10, 0.03 * s), sw(p * 8, 8, -0.01)), lambda p: (-ease_out(p) * 0.25, sw(p * 20, 20, 0.02 * s), sw(p * 15, 15, 0.03)), lambda p: (-ease_in(p) * 0.18, sw(p * 12, 12, 0.015 * s), sw(p * 10, 10, 0.02)))
    def front_foot(self, f, L=True):
        s = 1 if L else -1
        return self._tri(f, lambda p: (-ease_in_out(p) * 0.12, sw(p * 12, 12, 0.02 * s), sw(p * 8, 8, -0.015)), lambda p: (-ease_out(p) * 0.2, sw(p * 18, 18, 0.015 * s), sw(p * 12, 12, 0.02)), lambda p: (-ease_in(p) * 0.15, sw(p * 10, 10, 0.01 * s), sw(p * 6, 6, 0.01)))
    def front_toe(self, f, L=True):
        return self._tri(f, lambda p: (ease_in_out(p) * 0.08, 0, 0), lambda p: (ease_out(p) * 0.1, 0, 0), lambda p: (ease_in(p) * 0.06, 0, 0))
    def spine_action(self, f, seg, tot=7):
        sf = seg / tot
        return self._tri(f, lambda p: (-ease_in_out(p) * 0.2 * sf, sw(p * 6, 6, 0.03 * sf), ease_in_out(p) * 0.08 * sf), lambda p: (ease_out(p) * 0.25 * sf, sw(p * 10, 10, 0.02 * sf), ease_out(p) * 0.12 * sf), lambda p: (-ease_in(p) * 0.15 * sf, sw(p * 8, 8, 0.015 * sf), ease_in(p) * 0.06 * sf))
    def ear_movement(self, f, L=True):
        d = -1 if L else 1
        return self._tri(f, lambda p: (ease_in_out(p) * 0.05 * d, sw(p * 15, 15, 0.02), sw(p * 12, 12, 0.015)), lambda p: (ease_out(p) * 0.06 * d, sw(p * 20, 20, 0.025), sw(p * 18, 18, 0.02)), lambda p: (-ease_in(p) * 0.04 * d, sw(p * 12, 12, 0.015), sw(p * 10, 10, 0.01)))
    def tail_movement(self, f, seg):
        sf = seg / 3
        return self._tri(f, lambda p: (-ease_in_out(p) * 0.15 * sf, sw(p * 25, 25, 0.06 * sf), sw(p * 20, 20, 0.04 * sf)), lambda p: (ease_out(p) * 0.25 * sf, sw(p * 40, 40, 0.1 * sf), sw(p * 35, 35, 0.08 * sf)), lambda p: (ease_in(p) * 0.15 * sf, sw(p * 25, 25, 0.05 * sf), sw(p * 20, 20, 0.03 * sf)))


def jump_phase(elapsed, timing=(2, 9, 3)):
    prep, flight, land = timing
    if elapsed <= prep: return 0.16 * elapsed / prep
    if elapsed <= prep + flight: return 0.16 + 0.64 * (elapsed - prep) / flight
    return min(1.0, 0.80 + 0.20 * (elapsed - prep - flight) / land)


def jump_position(p0, p1, t, arco=0.15):
    """parabola Bezier del salto de Jerry; `arco` = m sobre el piso mas alto (bajo, para no tocar el techo de un tunel de 1 m)"""
    t = min(max(t, 0.0), 1.0); u = min(max((t - 0.16) / 0.64, 0.0), 1.0); bias = 0.18
    control = (p0[0] + bias * (p1[0] - p0[0]), p0[1] + bias * (p1[1] - p0[1]), max(p0[2], p1[2]) + 2 * arco)
    q = [(1 - u) ** 2 * a + 2 * u * (1 - u) * c + u * u * b for a, b, c in zip(p0, p1, control)]
    if p1[2] < p0[2] - 0.5: q[2] = p0[2] + 4 * arco * u * (1 - u) - (p0[2] - p1[2]) * u ** 3       # BAJAR: avanza primero (las ancas libran el borde del escalon) y despues cae
    return tuple(q)


def pose_jump(phase):
    jump = DogJumpCycle(); lf = phase * 14 + 1; k = {}
    for s, L in (('L', True), ('R', False)):
        k['thigh.' + s] = jump.rear_thigh(lf, L); k['shin.' + s] = jump.rear_shin(lf, L); k['foot.' + s] = jump.rear_foot(lf, L); k['toe.' + s] = jump.rear_toe(lf, L)
        k['front_thigh.' + s] = jump.front_thigh(lf, L); k['front_shin.' + s] = jump.front_shin(lf, L); k['front_foot.' + s] = jump.front_foot(lf, L); k['front_toe.' + s] = jump.front_toe(lf, L); k['ear.' + s] = jump.ear_movement(lf, L)
    for i in range(1, 8): k['spine_%d' % i] = jump.spine_action(lf, i, 7)
    for i in range(1, 4): k['tail_%d' % i] = jump.tail_movement(lf, i)
    if phase >= 0.80:
        rec = ss((phase - 0.80) / 0.20)
        for b in list(k): k[b] = mul(k[b], 1.0 - rec)
    return k


# ============================================================================================================================ JERRY: poses del tunel (radianes, Euler XYZ; el resto de huesos en 0)
CARGA = {'spine_2': (0.06, 0, 0)}                                                                  # lleva el pico en la boca: cabeza apenas baja
RECOGE = {'spine_1': (0.45, 0, 0), 'spine_2': (0.45, 0, 0), 'spine_3': (0.30, 0, 0), 'jaw_bot': (-0.35, 0, 0), 'front_shin.L': (-0.15, 0, 0), 'front_shin.R': (-0.15, 0, 0)}
ALTO = {'spine_1': (-0.18, 0, 0), 'spine_2': (-0.38, 0, 0), 'spine_3': (-0.06, 0, 0), 'front_shoulder.L': (0.06, 0, 0), 'front_shoulder.R': (0.06, 0, 0), 'tail_1': (0.25, 0, 0)}      # levanta la cabeza (toma impulso)
IMPACTO = {'spine_1': (0.26, 0, 0), 'spine_2': (0.36, 0, 0), 'spine_3': (0.10, 0, 0), 'front_shin.L': (-0.12, 0, 0), 'front_shin.R': (-0.12, 0, 0), 'tail_1': (-0.1, 0, 0)}   # golpe: cabeza abajo / adelante
IMPACTO_BAJO = {'spine_1': (0.40, 0, 0), 'spine_2': (0.45, 0, 0), 'spine_3': (0.25, 0, 0), 'front_shin.L': (-0.2, 0, 0), 'front_shin.R': (-0.2, 0, 0), 'tail_1': (-0.1, 0, 0)}  # bloque por debajo del piso (escalon)


class LineaJ:
    """linea de tiempo de Jerry: por frame, pose (hueso -> Euler en radianes) y raiz (x, y, z, rz en grados)"""
    def __init__(self, cfg, nb):
        self.cfg = cfg; self.NB = nb; self.cic = Ciclo(cfg["ciclo"]); self.TL = {}; self.EVENTOS = []; self.LLEG = {}; self.cur = cfg["frame_ini"]; self.fase = 0
        self.Z = {n: (0.0, 0.0, 0.0) for n in nb}; self.ult = {"pose": dict(self.Z), "x": 0.0, "y": 0.0, "z": 0.0, "rz": 0.0}; self.agarre = None
    def comp(self, *capas):
        p = dict(self.Z)
        for c in capas:
            for n, v in c.items():
                if n in p and n not in SIN_ROTAR: p[n] = tuple(a + b for a, b in zip(p[n], v))
        return p
    def poner(self, pose, x, y, z, rz):
        self.TL[self.cur] = dict(pose=pose, x=x, y=y, z=z, rz=rz); self.ult.update(pose=pose, x=x, y=y, z=z, rz=rz); self.cur += 1
    def mezclar(self, p, q, t): return {n: tuple(a + (b - a) * t for a, b in zip(p[n], q[n])) for n in p}
    def hacia(self, pose, n, x, y, z, rz, curva=ss):
        p0 = self.ult["pose"]
        for i in range(n): self.poner(self.mezclar(p0, pose, curva((i + 1) / n)), x, y, z, rz)
    def reposo(self, n, x, y, z, rz):
        """quieto con el pico en la boca: respira, mueve la cola despacio y las orejas"""
        p0 = self.ult["pose"]
        for i in range(n):
            f = self.cur; ext = {'spine_4': (sw(f, 48, 0.015), 0, 0), 'tail_1': (sw(f, 22, 0.12, 0, 0.1), 0, sw(f, 22, 0.25)), 'tail_2': (0, 0, sw(f, 22, 0.2, 0.6)), 'tail_3': (0, 0, sw(f, 22, 0.15, 1.2)),
                                 'ear.L': (0, sw(f, 70, 0.08), 0), 'ear.R': (0, sw(f, 70, 0.08, 1.0), 0)}
            q = self.comp(CARGA, ext)
            self.poner(self.mezclar(p0, q, ss((i + 1) / 5.0)) if i < 5 else q, x, y, z, rz)
    def caminar(self, a, b, rz, fpb=None, paso=1):
        """camina de `a` a `b` a `fpb` frames por bloque; `paso` = 2 avanza el ciclo de caminar al doble de ritmo (caminar RAPIDO)"""
        d = math.hypot(b[0] - a[0], b[1] - a[1]); nf = max(3, int(round((fpb or self.cfg["frames_por_bloque"]) * d))); p0 = self.ult["pose"]; rz0 = self.ult["rz"]; dz = (rz - rz0 + 180.0) % 360.0 - 180.0
        for i in range(nf):
            u = (i + 1) / nf; amp = min(1.0, (i + 1) / (4.0 / paso), (nf - i) / (4.0 / paso) + 0.1); w = self.cic.pose(self.fase + paso * (i + 1))
            q = self.comp(CARGA, {n: mul(v, amp) for n, v in w.items()})
            if i < 3: q = self.mezclar(p0, q, ss((i + 1) / 4.0))
            self.poner(q, a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, a[2], rz0 + dz * ss(min(1.0, u * 2)))
        self.fase += paso * nf
    def saltar(self, a, b, rz):
        p0 = self.ult["pose"]; n = 15
        for i in range(n):
            ph = jump_phase(i + 1); pos = jump_position(a, b, ph, self.cfg["arco_salto"]); q = self.comp(CARGA, pose_jump(ph))
            if i < 3: q = self.mezclar(p0, q, ss((i + 1) / 4.0))
            self.poner(q, pos[0], pos[1], pos[2], rz)
    def picar(self, x, y, z, rz, bajo, ngol):
        """`ngol` golpes con el pico en la boca: levanta la cabeza (impulso) y la baja de golpe; devuelve los frames de impacto"""
        G = self.cfg["frames_golpe"]; sube = max(4, int(G * 0.5)); baja = 3; vuelve = G - sube - baja; golpes = []
        alto = self.comp(CARGA, ALTO); imp = self.comp(CARGA, IMPACTO_BAJO if bajo else IMPACTO); car = self.comp(CARGA)
        for g in range(ngol):
            self.hacia(alto, sube, x, y, z, rz)
            self.hacia(imp, baja, x, y, z, rz, curva=lambda t: t * t); golpes.append(self.cur - 1)                    # baja de golpe (acelerando): impacto en el ultimo frame
            self.hacia(car if g == ngol - 1 else self.mezclar(car, alto, 0.3), vuelve, x, y, z, rz)
        return golpes
    def recoger(self, x, y, z, rz):
        """baja la cabeza al pico del suelo (spine_1/2/3), abre la boca, la cierra (AGARRA) y levanta la cabeza con el pico"""
        abajo = self.comp(RECOGE); cerrada = self.comp(RECOGE, {'jaw_bot': (0.35, 0, 0)})
        self.hacia(abajo, 14, x, y, z, rz); self.hacia(cerrada, 4, x, y, z, rz); self.agarre = self.cur - 1
        self.reposo(4, x, y, z, rz); self.hacia(self.comp(CARGA), 12, x, y, z, rz)


def paradas_y_pisos(ruta, zs, atras):
    """P[k] = donde se para Jerry para picar la columna k (k >= 1): `atras` m detras del centro de la columna k-1 (el hocico queda a ~0.45 m de la cara del bloque);
    piso(x, y) = z de la columna de la ruta que contiene ese punto"""
    c = lambda i: (ruta[i][0] + 0.5, ruta[i][1] + 0.5)
    def dirk(k): return (ruta[k][0] - ruta[k - 1][0], ruta[k][1] - ruta[k - 1][1])
    P = [None] + [(c(k - 1)[0] - dirk(k)[0] * atras, c(k - 1)[1] - dirk(k)[1] * atras) for k in range(1, len(ruta))]
    col = {(r[0], r[1]): zs[i] for i, r in enumerate(ruta)}
    d0 = dirk(1)
    def piso(p):
        k = (int(math.floor(p[0])), int(math.floor(p[1])))
        if k in col: return col[k]
        return zs[0]
    return P, piso, d0


def animar_jerry(cfg, nb, ruta, zs, corredor, tipo, pausa_por_bloque, pausa_resto, n_fin):
    """ruta incluye la columna extra del final (el cuerpo de Jerry mide 1.47 m: se cava una columna mas para que el hocico no entre en la roca); n_fin = indice de la columna de la coordenada final"""
    L = LineaJ(cfg, nb); n = len(ruta) - 1
    rz_dir = lambda a, b: math.degrees(math.atan2(-(b[0] - a[0]), (b[1] - a[1])))
    P, piso, d0 = paradas_y_pisos(ruta, zs, cfg["atras"])
    rz = rz_dir(ruta[0], ruta[1]); x, y = P[1]; z = piso(P[1])
    L.ult.update(x=x, y=y, z=z, rz=rz)
    L.reposo(cfg["espera_ini"], x, y, z, rz)
    L.recoger(x, y, z, rz)
    trabajos = 0; total = sum(len(corredor[k]) for k in range(1, n + 1))
    for k in range(1, n + 1):
        L.LLEG[k - 1] = L.cur; rz = rz_dir(ruta[k - 1], ruta[k]); x, y = P[k]; z = piso(P[k])
        celdas = sorted(corredor[k], key=lambda c: -c[2])                                         # de arriba abajo (el de la altura de la cabeza primero)
        for c in celdas:
            ngol = 3 if tipo(c) == "piedra" else 1
            golpes = L.picar(x, y, z, rz, bajo=c[2] < z, ngol=ngol)
            L.EVENTOS.append((golpes[-1], [c], golpes[:-1]))
            extra = (pausa_por_bloque + (1 if trabajos < pausa_resto else 0)) if trabajos < total - 1 else 0; trabajos += 1     # tras el ULTIMO bloque no hay pausa: sale enseguida
            if extra > 0: L.reposo(extra, x, y, z, rz)
        a = (x, y, z)
        if k < n: bx, by = P[k + 1]
        else: bx, by = ruta[n_fin][0] + 0.5, ruta[n_fin][1] + 0.5                                  # ultimo: avanza hasta la COORDENADA FINAL
        bz = piso((bx, by)); b = (bx, by, bz)
        rzn = rz_dir(ruta[k], ruta[k + 1]) if k < n else rz
        if bz != z: L.saltar(a, b, rzn)                                                             # escalon de 1 m: salta (la z nunca toma valores intermedios fuera del salto)
        elif k == n: L.caminar(a, b, rzn, fpb=cfg["frames_por_bloque_final"], paso=2)                 # apenas termina de romper: camina RAPIDO a la coordenada final
        else: L.caminar(a, b, rzn)
    L.llegada = L.cur - 1
    L.reposo(cfg["espera_fin"], L.ult["x"], L.ult["y"], L.ult["z"], L.ult["rz"])
    L.n_trabajos = trabajos
    return L


def _accion_j(obj, nombre, canales, interp="LINEAR"):
    if obj.animation_data is None: obj.animation_data_create()
    ant = obj.animation_data.action; obj.animation_data.action = None
    if ant is not None and ant.users == 0 and ant.name.startswith(ACC): bpy.data.actions.remove(ant)
    a = bpy.data.actions.new(nombre); slot = a.slots.new(id_type='OBJECT', name=obj.name); cb = a.layers.new("Capa").strips.new(type='KEYFRAME').channelbag(slot, ensure=True)
    for (dp, i), pts in canales.items():
        fc = cb.fcurves.new(dp, index=i); fc.keyframe_points.add(len(pts)); fc.keyframe_points.foreach_set("co", [v for p in pts for v in p])
        for kp in fc.keyframe_points: kp.interpolation = interp
        fc.update()
    obj.animation_data.action = a; obj.animation_data.action_slot = slot
    return a


def pico_jerry(cfg):
    """copia propia del pico de piedra (`stone_pickaxe`, sin constraints) para la boca de Jerry, en la coleccion del tunel"""
    src = bpy.data.objects.get(cfg["pico"]) or bpy.data.objects.get("wooden_pickaxe")
    if src is None: raise RuntimeError("No existe el pico %r en la escena" % cfg["pico"])
    ob = src.copy(); ob.name = PREF + "pico"; ob.scale = (cfg["escala_pico"],) * 3                   # COPIA del pico de Alfred (con su Solidify: malla con profundidad)
    for c in list(ob.constraints): ob.constraints.remove(c)
    for m in list(ob.modifiers):
        if m.type == "ARMATURE": ob.modifiers.remove(m)
    if ob.animation_data: ob.animation_data_clear()
    for c in list(ob.users_collection): c.objects.unlink(ob)
    col = bpy.data.collections.get(COL) or bpy.data.collections.new(COL)
    if col.name not in [c.name for c in bpy.context.scene.collection.children]: bpy.context.scene.collection.children.link(col)
    col.objects.link(ob); return ob


def aplicar_jerry(L, cfg, ROOT, ARM, pico):
    """1) recorre la linea poniendo la pose a mano (sin claves) para medir el hueso de la cabeza y hornear el pico; 2) escribe las acciones de la raiz, del armature y del pico"""
    sc = bpy.context.scene; frames = sorted(L.TL); rx, ry = ROOT.rotation_euler.x, ROOT.rotation_euler.y; pb = ARM.pose.bones
    for o in (ROOT, ARM, pico):
        if o.animation_data and o.animation_data.action: o.animation_data.action = None
    for n in L.NB: pb[n].rotation_mode = 'XYZ'
    hb = cfg["hueso_cabeza"]; S = cfg["escala_pico"]
    def poner(f):
        d = L.TL[f]; ROOT.location = (d["x"], d["y"], d["z"]); ROOT.rotation_euler = (rx, ry, math.radians(d["rz"]))
        for n, v in d["pose"].items(): pb[n].rotation_euler = v
        bpy.context.view_layer.update()
    def boca():                                                                                    # punto de agarre: entre las puntas de las dos mandibulas
        mw = ARM.matrix_world; return (mw @ pb["jaw_top"].tail + mw @ pb["jaw_bot"].tail) * 0.5
    def M_hueso(): return ARM.matrix_world @ pb[hb].matrix
    def deseada(fwd, up, punto, retro):
        """mango (z local del pico) hacia `fwd`, cabeza en T (x local) hacia `up`; el extremo del mango (origen) `retro` m por detras de la boca"""
        z_ = fwd.normalized(); x_ = (up - z_ * up.dot(z_)).normalized(); y_ = z_.cross(x_)
        R = Matrix((x_, y_, z_)).transposed().to_4x4(); return Matrix.Translation(punto - z_ * retro) @ R @ Matrix.Diagonal((S, S, S, 1))
    # 2 frames de referencia: el agarre (pico en el suelo) y el primer frame con la cabeza ya arriba (pico en posicion de carga)
    g = L.agarre; poner(g); rzr = math.radians(L.TL[g]["rz"]); fwd = Vector((-math.sin(rzr), math.cos(rzr), 0.0)); up = Vector((0, 0, 1))
    b_ = boca(); suelo = Vector((b_.x, b_.y, L.TL[g]["z"] + 0.03))
    M_suelo = deseada(fwd, fwd.cross(up), suelo, 0.06)                                              # tumbado: mango hacia delante y la T de lado, sobre el piso
    off_suelo = M_hueso().inverted() @ M_suelo
    fc = g + 20; poner(fc); bc = boca(); Mh = M_hueso(); fwd_h = (Mh.to_3x3() @ Vector((0, 1, 0))).normalized()
    hz = Vector((fwd.x, fwd.y, -0.25)).normalized()                                                 # carga: mango hacia delante y un poco abajo, la T vertical
    off_carga = Mh.inverted() @ deseada(hz, up, bc, 0.06)
    gu = sc.get("jrrst_grip_pico")                                                                 # forma de LLEVAR el pico elegida por el usuario (relativa al hueso de la cabeza)
    if gu: off_carga = Matrix([list(gu[0:4]), list(gu[4:8]), list(gu[8:12]), list(gu[12:16])])
    canal = {("location", i): [] for i in range(3)}; canal.update({("rotation_euler", i): [] for i in range(3)}); prev = None
    for f in frames:
        poner(f)
        if f < g: M = M_suelo
        else:
            t = ss((f - g) / 16.0); M = M_hueso() @ _mixM(off_suelo, off_carga, t)
        l, q, s_ = M.decompose(); e = q.to_euler('XYZ', prev) if prev is not None else q.to_euler('XYZ'); prev = e
        for i in range(3): canal[("location", i)].append((f, l[i])); canal[("rotation_euler", i)].append((f, e[i]))
    pico.rotation_mode = 'XYZ'
    _accion_j(pico, ACC + "pico", canal)
    can_r = {("location", i): [(f, L.TL[f][k]) for f in frames] for i, k in enumerate("xyz")}
    can_r[("rotation_euler", 0)] = [(frames[0], rx)]; can_r[("rotation_euler", 1)] = [(frames[0], ry)]; can_r[("rotation_euler", 2)] = [(f, math.radians(L.TL[f]["rz"])) for f in frames]
    _accion_j(ROOT, ACC + "root", can_r)
    can_a = {}
    for n in L.NB:
        for i in range(3): can_a[('pose.bones["%s"].rotation_euler' % n, i)] = [(f, L.TL[f]["pose"][n][i]) for f in frames]
    _accion_j(ARM, ACC + "armature", can_a)


def colisiones_j(L, BL, T, solidas):
    """frames en que un punto del cuerpo de Jerry (hocico, pecho, patas, lomo; la punta del pico NO cuenta) queda dentro de roca sin picar o de un bloque del tunel visible"""
    malos = []
    for f in sorted(L.TL):
        d = L.TL[f]; r = math.radians(d["rz"]); fx, fy = -math.sin(r), math.cos(r)
        for av, h in ((0.66, 0.40), (0.30, 0.10), (-0.25, 0.10), (0.0, 0.70), (-0.6, 0.45)):
            c = (int(math.floor(d["x"] + fx * av)), int(math.floor(d["y"] + fy * av)), int(math.floor(d["z"] + h)))
            if c in T and f < T[c] and c in solidas: malos.append(f); break
            b = BL.get(c)
            if b and b[1] <= f < (T[c] + 3 if c in T else b[2]): malos.append(f); break
    return malos


# ============================================================================================================================ principal
CFG_DEFECTO = dict(frame_ini=1, frame_llegada=2020, alto=1, ciclo=25, frames_por_bloque=14, frames_por_bloque_final=7, frames_golpe=16, atras=0.64, arco_salto=0.15, espera_ini=10, espera_fin=14,
                   pico="stone_pickaxe", escala_pico=0.6, hueso_cabeza="scull", alto_pecho=0.45, columnas_extra=1, holgura_escalon=2,
                   final_sin_bloques=0, rellenar_aire=True, bloques_dir=None, cascaron=True, semilla=5, pct_piedra=0.5, final_abierto=0, entrada_sin_cascaron=1, adelanto=4,
                   ignorar=("Short_Grass", "Fern", "Large_Fern", "Birch_Leaves", "Oak_Leaves", "Spruce_Leaves", "Allium", "Dandelion", "Azure_Bluet", "Poppy",
                            "Seagrass", "Brown_Mushroom", "Glow_Lichen", "Stationary_Water"))


def celdas_ajenas():
    """celdas ocupadas por bloques de OTROS tuneles (p. ej. el de Alfred, coleccion `tunel`): ahi no se pone ningun bloque (se solaparian)"""
    out = set()
    for o in bpy.data.objects:
        if o.name.startswith("tunel_bloque_") and not o.name.startswith(PREF):
            p = o.matrix_world.translation if o.animation_data is None else Vector(o.location); out.add((int(math.floor(p[0])), int(math.floor(p[1])), int(math.floor(p[2]))))
    return out


def crear(context, inicio, final, **kw):
    """Crea el tunel de JERRY (personaje de 1x1 m) de `inicio` a `final` (z = piso): recoge el pico con la boca, pica cada bloque (tierra 1 golpe, piedra 3) y llega a la final en `frame_llegada`."""
    sc = context.scene; cfg = dict(CFG_DEFECTO); cfg.update(kw)
    if bpy.data.collections.get(COL): quitar(sc)
    ROOT, ARM = rig_jerry(); nb = [n for n in NB_TODOS if n in ARM.pose.bones]
    f_vuelta = sc.frame_current; sc.frame_set(max(sc.frame_end, cfg["frame_llegada"]))                 # el mundo se consulta con los bloques permanentes de otros tuneles ya visibles
    guard = tuple(ROOT.location); ROOT.location = (guard[0], guard[1], guard[2] + 500.0); bpy.context.view_layer.update()   # Jerry fuera del camino de los rayos
    try:
        mundo = Mundo(sc, cfg["ignorar"])
        ruta, zs = construir_ruta(inicio, final); n_fin = len(ruta) - 1
        if n_fin < 1: raise RuntimeError("El inicio y el final estan en la misma celda")
        dx, dy = ruta[-1][0] - ruta[-2][0], ruta[-1][1] - ruta[-2][1]
        for _ in range(int(cfg["columnas_extra"])): ruta.append((ruta[-1][0] + dx, ruta[-1][1] + dy)); zs.append(zs[-1])
        n = len(ruta) - 1
        cfg['z_ini'], cfg['z_fin'] = zs[0], zs[n_fin]; cfg["_tipo"] = tipo = hacer_tipo(cfg, mundo); cfg["_zona_final"] = set(); cfg["_ajenas"] = celdas_ajenas()
        xs_ = [r[0] for r in ruta]; ys_ = [r[1] for r in ruta]; mundo.preparar_piedra((min(xs_) - 3, max(xs_) + 4, min(ys_) - 3, max(ys_) + 4, min(zs) - 3, max(zs) + cfg['alto'] + 3))
        corredor = []; corr_celdas = []
        for i, (cx_, cy_) in enumerate(ruta):
            zf = int(math.floor(zs[i] + 0.001)); h_ = int(cfg["holgura_escalon"]); zmax = max(zs[j] for j in range(i - h_, i + h_ + 1) if 0 <= j <= n)      # junto a un escalon el corredor sube (el cuerpo de Jerry es largo: el hocico no toca el techo al saltar)
            celdas = [(cx_, cy_, z) for z in range(zf, int(math.floor(zmax + 0.001)) + cfg["alto"])]; corr_celdas += celdas
            corredor.append([c for c in celdas if i > 0 and (cfg["rellenar_aire"] or mundo.solida(c))])
        rellenos = [c for lst in corredor for c in lst if not mundo.solida(c)]
        # 1.a pasada sin pausas: cuanto dura; 2.a con pausas repartidas para LLEGAR a la coordenada final en `frame_llegada`
        L0 = animar_jerry(cfg, nb, ruta, zs, corredor, tipo, 0, 0, n_fin)
        sobra = cfg["frame_llegada"] - L0.llegada; nt = max(1, L0.n_trabajos - 1)
        L = animar_jerry(cfg, nb, ruta, zs, corredor, tipo, max(0, sobra) // nt, max(0, sobra) % nt, n_fin) if sobra > 0 else L0
        fmax = max(L.TL); piso_ = {(r_[0], r_[1]): zs[i_] for i_, r_ in enumerate(ruta)}
        cfg["_piso"] = lambda c: piso_.get((c[0], c[1]), c[2])
        cfg["_pos_alfred"] = lambda f: (L.TL[min(max(f, min(L.TL)), fmax)]["x"], L.TL[min(max(f, min(L.TL)), fmax)]["y"], L.TL[min(max(f, min(L.TL)), fmax)]["z"])
        ev = [(e[0], [tuple(c) for c in e[1]], list(e[2])) for e in L.EVENTOS]
        g = geometria(sc, cfg, mundo, ev, corr_celdas, dict(L.LLEG), ruta, rellenos)
    finally:
        ROOT.location = guard; bpy.context.view_layer.update()
    pico = pico_jerry(cfg)
    aplicar_jerry(L, cfg, ROOT, ARM, pico)
    fin = max(L.TL); sc.frame_end = max(sc.frame_end, fin)
    T = {tuple(c): f for f, cs, hs in ev for c in cs}
    malos = colisiones_j(L, g.get("_BL", {}), T, set(c for c in corr_celdas if mundo.solida(c)))
    g.pop("_BL", None)
    sc["jrrst_tunel_ultimo"] = json.dumps({"inicio": list(inicio), "final": list(final), "frame_ini": cfg["frame_ini"], "llegada": L.llegada, "frame_fin": fin, "golpes": sum(len(e[2]) + 1 for e in ev), "bloques_picados": len(ev)})
    sc.frame_set(f_vuelta)
    return {"llegada": L.llegada, "objetivo": cfg["frame_llegada"], "sin_pausas": L0.llegada, "frame_fin": fin, "bloques_picados": len(ev), "golpes": sum(len(e[2]) + 1 for e in ev),
            "agarre": L.agarre, "colisiones": {"frames": len(malos), "primeros": malos[:8]}, **g}


# ============================================================================================================================ capas ajenas al terreno
def _ocultar_ajenos():
    """oculta mientras se crea el tunel los objetos que NO son terreno real pero estan pegados a el (p. ej. `techo_tierra_bajo_pasto`: caras de tierra bajo el pasto,
    vistas desde dentro de la roca), para que no engañen a los rayos que deciden que celdas son roca"""
    ocu = [o for o in bpy.data.objects if o.name.startswith("techo_tierra") and not o.hide_viewport]
    for o in ocu: o.hide_viewport = True
    return ocu


_crear_base = crear


def crear(context, inicio, final, **kw):
    ocu = _ocultar_ajenos()
    try: return _crear_base(context, inicio, final, **kw)
    finally:
        for o in ocu: o.hide_viewport = False
