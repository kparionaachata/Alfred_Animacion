# -*- coding: utf-8 -*-
"""Parte 9: TAPA con piedra la parte de la cueva que sigue mas alla del suelo rellenado (`piso_cueva_parte9.py`): la geoda de amatista y la continuacion hacia x -165 / -185.
En cada celda del BORDE de la zona rellenada donde la cueva continua (celda vecina con fondo a z 0 que no se relleno) se levanta una COLUMNA de bloques `bloque_de_stone`
desde z 0 hasta el techo (mientras la celda sea aire, maximo ALTO_MAX). Coleccion `pared_cueva_parte9` (copias enlazadas de la malla `piso_bloque_piedra`).
Ejecutar DESPUES de `piso_cueva_parte9.py`, con `bpy.app.timers.register`. Repetible (`QUITAR = True` la quita)."""
import bpy, math
import numpy as np
from mathutils import Vector

QUITAR = bool(globals().get('QUITAR', False)); COLN = "pared_cueva_parte9"; ALTO_MAX = 16; MARGEN = 3
sc = bpy.context.scene
col = bpy.data.collections.get(COLN)
if col:
    for o in list(col.objects): bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(col)
if QUITAR:
    print("pared de la cueva quitada")
else:
    piso = bpy.data.collections["piso_cueva_parte9"]
    llenas = {(math.floor(o.location.x), math.floor(o.location.y)) for o in piso.objects if o.name.startswith("piso_") and abs(o.location.z + 0.5) < 0.01}
    xs = [k[0] for k in llenas]; ys = [k[1] for k in llenas]; caja = (min(xs) - MARGEN, max(xs) + MARGEN, min(ys) - MARGEN, max(ys) + MARGEN)
    fondo = set()                                                                            # celdas con cara de fondo a z 0 (cueva que continua) en todas las mallas del mundo
    for o_ in bpy.data.objects:
        if o_.type != 'MESH' or o_.name.startswith(("piso_", "tunel_", "techo_", "flecha", "pan_", "pared_")) or o_.name.endswith(("_alfred", "_jerry")) or o_.parent is not None: continue
        if any(m_.type == 'ARMATURE' for m_ in o_.modifiers) or len(o_.data.polygons) == 0: continue
        bb = [o_.matrix_world @ Vector(v) for v in o_.bound_box]
        if min(v.z for v in bb) > 0.01 or max(v.x for v in bb) < caja[0] or min(v.x for v in bb) > caja[1] or max(v.y for v in bb) < caja[2] or min(v.y for v in bb) > caja[3]: continue
        me_ = o_.data; n_ = len(me_.polygons); c_ = np.empty(n_ * 3); me_.polygons.foreach_get("center", c_); c_ = c_.reshape(n_, 3); W_ = np.array(o_.matrix_world); cw_ = c_ @ W_[:3, :3].T + W_[:3, 3]
        for i in np.where((np.abs(cw_[:, 2]) < 0.01) & (cw_[:, 0] > caja[0]) & (cw_[:, 0] < caja[1]) & (cw_[:, 1] > caja[2]) & (cw_[:, 1] < caja[3]))[0]: fondo.add((math.floor(cw_[i, 0]), math.floor(cw_[i, 1])))
    dg = bpy.context.evaluated_depsgraph_get()
    OCU = {o.name for o in bpy.data.objects if o.type == 'MESH' and (o.name.endswith('_alfred') or o.name.startswith(('flecha', 'pan_alfred', 'tunel_jerry_pico', 'stone_pickaxe', 'piso_', 'pared_')))}
    def aire(x, y, z):
        p = Vector((x + .5, y + .5, z + .3))
        for _ in range(8):
            ok, loc, nor, i, o, m_ = sc.ray_cast(dg, p, Vector((0, 0, 1)), distance=40)
            if not ok: return True
            if o.original.name in OCU: p = loc + Vector((0, 0, 0.01)); continue
            return loc.z > z + 1.0 - 0.01
        return False
    borde = set()
    for (x, y) in llenas:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            k = (x + dx, y + dy)
            if k not in llenas and k in fondo and aire(k[0], k[1], 0): borde.add(k)
    # ---------- IRREGULAR: muro de borde + 3 filas escalonadas hacia dentro (alturas por ruido), con vetas de cobre / carbon ----------
    import random
    rng = random.Random(33); MALLAS = {"piedra": bpy.data.meshes["piso_bloque_piedra"], "cobre": bpy.data.meshes["piso_bloque_cobre"], "carbon": bpy.data.meshes["piso_bloque_carbon"]}
    CAE = (-133.5, -70.5); ESQ = (-139.5, -70.5)
    def tipo(x, y, z):
        u = (((x * 73856093) ^ (y * 19349663) ^ (z * 83492791) ^ 77) & 0xFFFF) / 65535.0
        return "cobre" if u < 0.05 else ("carbon" if u < 0.065 else "piedra")
    def ruido(x, y): return 0.5 + 0.5 * (math.sin(x * 0.7 + 1.3) * math.cos(y * 0.6 + 0.4) * 0.6 + 0.4 * math.sin(x * 1.7 - y * 1.1 + 2.0))
    ocupado = {}                                                                             # altura ya ocupada por los montones del suelo
    for o in piso.objects:
        if o.name.startswith("piso_") and o.location.z > 0: k = (math.floor(o.location.x), math.floor(o.location.y)); ocupado[k] = max(ocupado.get(k, 0), math.floor(o.location.z) + 1)
    techo = {}
    def alto_libre(x, y, z0):
        z = z0
        while z < ALTO_MAX and aire(x, y, z): z += 1
        return z
    col = bpy.data.collections.new(COLN); sc.collection.children.link(col); n = 0
    def poner(x, y, z):
        global n
        t = tipo(x, y, z); ob = bpy.data.objects.new("pared_%s_%d_%d_%d" % (t, x, y, z), MALLAS[t]); ob.location = (x + .5, y + .5, z + .5); col.objects.link(ob)
    cuenta = 0
    for (x, y) in sorted(borde):                                                             # muro exterior (tapa la cueva que sigue), con el remate superior irregular
        top = alto_libre(x, y, 0)
        for z in range(0, top): poner(x, y, z); cuenta += 1
    # filas hacia dentro: distancia al borde por vecinos
    dist = {k: 0 for k in borde}; frente = list(borde)
    for d in (1, 2, 3, 4, 5):
        nuevo = []
        for (x, y) in frente:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                k = (x + dx, y + dy)
                if k in llenas and k not in dist: dist[k] = d; nuevo.append(k)
        frente = nuevo
    for k, d in dist.items():
        if d == 0: continue
        x, y = k
        if math.hypot(x + .5 - CAE[0], y + .5 - CAE[1]) < 4.0 or math.hypot(x + .5 - ESQ[0], y + .5 - ESQ[1]) < 2.5: continue
        r = ruido(x, y) + rng.uniform(-0.2, 0.2)
        prob = {1: 0.85, 2: 0.6, 3: 0.4, 4: 0.25, 5: 0.12}[d]
        if r < 1.0 - prob: continue
        z0 = ocupado.get(k, 0); top = alto_libre(x, y, z0)
        frac = {1: rng.uniform(0.4, 1.0), 2: rng.uniform(0.2, 0.75), 3: rng.uniform(0.1, 0.45), 4: rng.uniform(0.05, 0.3), 5: rng.uniform(0.0, 0.18)}[d]
        h = max(1, int(round((top - z0) * frac)))
        for z in range(z0, min(top, z0 + h)): poner(x, y, z); cuenta += 1
    n = cuenta
    print("PARED CUEVA: %d columnas en el borde + filas irregulares; %d bloques" % (len(borde), n))
