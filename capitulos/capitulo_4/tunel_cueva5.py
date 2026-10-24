# -*- coding: utf-8 -*-
"""alfred_cueva_5.blend: tunel de 1x2 picado como en Minecraft desde (-98.5, -26.5, -11.0) hacia -Y (la derecha de la vista):
escalera que baja 7 bloques (primero 1 abajo por bloque, luego cada 2 y cada 3, como la curva del dibujo) y despues todo recto.
Las celdas del tunel se vacian (se borran los bloques que hubiera) y se ponen paredes, techo y suelo de piedra alrededor
(la cueva es un cascaron de bloques: fuera de el no hay bloques). En los tramos que bajan el hueco es de 3 de alto para poder pasar.
Uso: exec(open(ruta, encoding="utf8").read()); construir()      (repetible: borra lo que creo antes, prefijo de etiqueta `tunel5`)
"""
import bpy, re, random

X = -99                                   # columna x de las celdas (el bloque -99 va de -99 a -98)
Y0, Z0 = -27, -11                         # celda de inicio (suelo en z -11)
BAJADAS = [1, 1, 1, 1, 2, 2, 3]           # bloques de avance por cada bloque que baja (7 en total)
RECTO = 58                                # bloques del tramo recto final
COL = "cueva_bloques"
DIORITA = 10                              # bloques de diorita sueltos en las paredes
ANTORCHA = "antorcha_cueva4_1"               # modelo (empty con luz, llama, palo y humo); se copian como antorchas de pared
CADA = (5, 9)                             # cada cuantos bloques de tunel hay una antorcha (al azar)
VETAS = {"coal_ore": (4, 2, 5), "copper_ore": (2, 2, 4)}   # mineral: (vetas, bloques min, max) pocas, como en el juego


def celdas_tunel():
    """[(y, z_suelo, alto)] desde el inicio hacia -Y"""
    cols = [(Y0, Z0, 2)]; y, z = Y0, Z0
    for paso in BAJADAS:
        for i in range(paso):
            y -= 1
            if i == 0: z -= 1
            cols.append((y, z, 3 if i == 0 else 2))                   # donde baja, 3 de alto para que quepa la cabeza
    for _ in range(RECTO):
        y -= 1; cols.append((y, z, 2))
    cols[-1] = (y, z, 3); y -= 1; cols.append((y, z, 3))                 # al final, un hueco de 1x3 para un personaje
    return cols


def construir(semilla=5):
    O = bpy.data.objects; col = bpy.data.collections[COL]; rnd = random.Random(semilla)
    for o in [o for o in O if o.get("tunel5")]: bpy.data.objects.remove(o, do_unlink=True)
    bloques = {}
    for o in O:
        m = re.match(r"bloque_(.+?)_(-?\d+)_(-?\d+)_(-?\d+)$", o.name)
        if m: bloques[(int(m[2]), int(m[3]), int(m[4]))] = o
    aire = set()
    for y, z, h in celdas_tunel():
        for k in range(h): aire.add((X, y, z + k))
    # picar: quitar los bloques que ocupan el tunel (se ocultan, para poder deshacer)
    picados = []
    for c in aire:
        o = bloques.get(c)
        if o and not o.hide_get():
            o.hide_set(True); o.hide_render = True; o["tunel5_picado"] = True; picados.append(o.name)
    # paredes, techo y suelo donde no hay bloque (no del lado de la cueva: y >= Y0)
    plantilla = {t: next(o for o in O if o.name.startswith("bloque_%s_" % t)) for t in ("stone", "andesite", "diorite")}
    nuevos = 0
    for (x, y, z) in aire:
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            c = (x + d[0], y + d[1], z + d[2])
            if c in aire or c[1] >= Y0: continue                     # la columna de inicio ya esta dentro de la cueva
            o = bloques.get(c)
            if o and not o.hide_get(): continue
            t = "stone" if rnd.random() < 0.8 else "andesite"                      # sin diorita
            b = plantilla[t].copy(); b.name = "bloque_%s_%d_%d_%d" % (t, *c); b.location = (c[0] + 0.5, c[1] + 0.5, c[2])
            b.hide_render = False; b["tunel5"] = True; col.objects.link(b); b.hide_set(False); bloques[c] = b; nuevos += 1
    for b in rnd.sample([o for o in O if o.get("tunel5")], DIORITA):          # unas pocas de diorita
        x, y, z = (int(v) for v in b.name.split("_")[-3:])
        b.data = plantilla["diorite"].data; b.name = "bloque_diorite_%d_%d_%d" % (x, y, z)
    # vetas de carbon y cobre: pequenos grupos de bloques vecinos en las paredes
    libres = {tuple(int(v) for v in o.name.split("_")[-3:]): o for o in O if o.get("tunel5") and "_stone_" in o.name or (o.get("tunel5") and "_andesite_" in o.name)}
    vetas = {}
    for mineral, (n, a_, b_) in VETAS.items():
        base = next(o for o in O if o.name.startswith("bloque_%s_" % mineral) and not o.get("tunel5"))
        for _ in range(n):
            c = rnd.choice(sorted(libres)); grupo = [c]
            while len(grupo) < rnd.randint(a_, b_):
                vec = [(g[0] + d[0], g[1] + d[1], g[2] + d[2]) for g in grupo for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
                vec = [v for v in vec if v in libres and v not in grupo]
                if not vec: break
                grupo.append(rnd.choice(vec))
            for g in grupo:
                b = libres.pop(g); b.data = base.data; b.name = "bloque_%s_%d_%d_%d" % (mineral, *g)
            vetas.setdefault(mineral, []).append(len(grupo))
    antorchas = _antorchas(rnd)
    return {"celdas_aire": len(aire), "picados": picados, "bloques_nuevos": nuevos, "fin": celdas_tunel()[-1], "vetas": vetas, "antorchas": antorchas}


def _puntas(e):
    """(punto mas bajo, punto mas alto) del palo de la antorcha en el mundo"""
    bpy.context.view_layer.update(); m = next(c for c in e.children if "main" in c.name)
    ps = [m.matrix_world @ v.co for v in m.data.vertices]
    return min(ps, key=lambda p: p.z), max(ps, key=lambda p: p.z)


def _pegar(e, lado):
    """inclina la antorcha con la punta hacia afuera de la pared y entierra la base 4 cm en la pared"""
    import math
    for sg in (1, -1):
        e.rotation_euler = (0.0, sg * math.radians(22.5), 0.0); lo, hi = _puntas(e)
        if (hi.x - lo.x) * lado < 0: break                                  # la punta se aleja de la pared
    pared = X + 0.5 + lado * 0.5
    e.location.x += (pared + lado * 0.04) - lo.x


def _antorchas(rnd):
    """antorchas de pared como en Minecraft: pegadas a la pared a la altura de la cabeza, inclinadas 22.5 grados hacia afuera"""
    import math
    O = bpy.data.objects; mod = O[ANTORCHA]; cols = mod.users_collection; puestas = []
    tunel = celdas_tunel()[2:]; i = rnd.randint(*CADA) // 2
    while i < len(tunel):
        y, z, h = tunel[i]; lado = rnd.choice((1, -1))                    # +1: pared de +X, -1: pared de -X
        e = mod.copy(); e.name = "antorcha_tunel5_%d" % (len(puestas) + 1); e["tunel5"] = True
        for c in cols: c.objects.link(e)
        e.location = (X + 0.5 + lado * 0.53, y + 0.5, z + 1.18)   # la base entra en la pared; e.rotation_euler = (0.0, lado * math.radians(22.5), 0.0)   # la punta hacia afuera
        for ch in mod.children:
            n = ch.copy(); n["tunel5"] = True
            if ch.data and ch.type == 'LIGHT': n.data = ch.data.copy()
            for c in ch.users_collection: c.objects.link(n)
            n.parent = e; n.matrix_parent_inverse = ch.matrix_parent_inverse.copy()
        _pegar(e, lado)
        if h == 3 and i >= len(tunel) - 2:                                   # el hueco final de 1x3 queda sin antorcha
            for ch in list(e.children): bpy.data.objects.remove(ch, do_unlink=True)
            bpy.data.objects.remove(e, do_unlink=True); i += rnd.randint(*CADA); continue
        puestas.append((y, z + 1, "+X" if lado > 0 else "-X")); i += rnd.randint(*CADA)
    return puestas
