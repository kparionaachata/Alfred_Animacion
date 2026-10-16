# -*- coding: utf-8 -*-
"""Parte 10: ENTRADAS NATURALES de los tuneles de Alfred y de Jerry (base_parte_10.blend).
El sistema de tunel puso bloques de tierra / piedra (`tunel_bloque_*`, `tunel_jerry_bloque_*`) que en la ladera SOBRESALEN del pasto alrededor de las entradas.
  1) nivel natural del terreno de cada columna = mediana de la altura del suelo de las 8 columnas vecinas (rayo hacia abajo que ignora el tunel, la vegetacion y los personajes);
  2) se BORRAN los bloques del tunel de las entradas cuya base queda a la altura del terreno o por encima (los que sobresalen);
  3) AGUJERO NATURAL: en esas columnas, si la celda justo bajo el nivel del terreno queda vacia y sin superficie del mundo (se veian las caras grises que el tunel quito),
     se pone un bloque de PASTO al ras del terreno; las celdas CAVADAS del tunel (por donde pasan Alfred y Jerry) se dejan abiertas: la entrada queda como un agujero.
Uso en segundo plano:  blender -b base_parte_10.blend --python entradas_naturales_parte10.py -- [guardar]   (sin 'guardar' solo informa)."""
import bpy, sys, math, statistics
from mathutils import Vector

GUARDAR = 'guardar' in sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else False
sc = bpy.context.scene; vl = bpy.context.view_layer; vl.update(); dg = bpy.context.evaluated_depsgraph_get()
IGN = ('tunel', 'techo', 'Short_Grass', 'Tall_Grass', 'Oak_Leaves', 'Birch_Leaves', 'Spruce_Leaves', 'Poppy', 'Dandelion', 'Fern', 'Large_Fern', 'Sweet_Berry', 'Sugar_Cane',
       'Vines', 'Torch', 'antorcha', 'flecha', 'pan_', 'miga', 'esqueleto', 'skeleton', 'sombrero', 'Oak_Log', 'Birch_Log', 'Spruce_Log')
# entradas: (prefijo, inicio, rango de x hacia dentro, celdas cavadas (y, z0, z1))
ENTRADAS = [("tunel_bloque", (-106.5, -69.5, 9.0), 12, (-70, 9, 11)), ("tunel_jerry_bloque", (-110.5, -71.5, 12.0), 12, (-72, 12, 12))]

def ignorar(o):
    o = o.original; return o.name.startswith(IGN) or o.type != 'MESH' or o.name.endswith(('_alfred', '_jerry')) or (o.parent is not None and o.parent.type == 'ARMATURE')

cache = {}
def suelo(x, y):
    if (x, y) in cache: return cache[(x, y)]
    p = Vector((x + .5, y + .5, 60.0)); z = None
    for _ in range(60):
        ok, l, n, i, o, m = sc.ray_cast(dg, p, Vector((0, 0, -1)), distance=200)
        if not ok: break
        if ignorar(o): p = l - Vector((0, 0, 0.01)); continue
        z = l.z; break
    cache[(x, y)] = z; return z

def superficie_mundo(x, y, zt):
    """hay una cara del MUNDO (no tunel) a la altura zt en la columna"""
    p = Vector((x + .5, y + .5, zt + 0.4))
    for _ in range(20):
        ok, l, n, i, o, m = sc.ray_cast(dg, p, Vector((0, 0, -1)), distance=0.8)
        if not ok: return False
        if ignorar(o): p = l - Vector((0, 0, 0.01)); continue
        return True
    return False

def al_cielo(x, y, z):
    """la cara de arriba del bloque (x, y, z) se ve desde el cielo (solo la vegetacion no tapa)"""
    p = Vector((x + .5, y + .5, z + 1.02))
    for _ in range(30):
        ok, l, n, i, o, m = sc.ray_cast(dg, p, Vector((0, 0, 1)), distance=80)
        if not ok: return True
        if ignorar(o) and not o.original.name.startswith('tunel'): p = l + Vector((0, 0, 0.01)); continue
        return False
    return True

borrar = []; rellenar = []; pasto = []
me_tierra = bpy.data.meshes.get("tunel_bloque_tierra") or next(o.data for o in bpy.data.objects if o.name.startswith("tunel_bloque_tierra"))
me_pasto = bpy.data.meshes.get("entrada_bloque_pasto")                                         # bloque de PASTO (los materiales del pasto del mundo) para que el relleno se vea natural
if me_pasto is None:
    me_pasto = me_tierra.copy(); me_pasto.name = "entrada_bloque_pasto"
    CAMBIO = {"dirt_up": "grass_block_top", "dirt_down": "dirt", "dirt_north": "grass_block_side", "dirt_east": "grass_block_side", "dirt_south": "grass_block_side", "dirt_west": "grass_block_side"}
    for i_, m_ in enumerate(me_pasto.materials):
        base = m_.name.split(".")[0] if m_ else ""
        if base in CAMBIO and CAMBIO[base] in bpy.data.materials: me_pasto.materials[i_] = bpy.data.materials[CAMBIO[base]]
for pref, ini, largo, (yc, z0c, z1c) in ENTRADAS:
    x_ini = math.floor(ini[0]); cav = {(x, yc, z) for x in range(x_ini - largo - 1, x_ini + 2) for z in range(z0c, z1c + 1)}
    blq = [o for o in bpy.data.objects if o.name.startswith(pref) and o.type == 'MESH' and x_ini - largo <= math.floor(o.matrix_world.translation.x) <= x_ini + 1]
    ocup = {(math.floor(o.matrix_world.translation.x), math.floor(o.matrix_world.translation.y), math.floor(o.matrix_world.translation.z)): o for o in blq}
    for (x, y, z), o in sorted(ocup.items()):
        zs = [suelo(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)]
        zs = [v for v in zs if v is not None and v > 3]
        if not zs: continue
        G = round(statistics.median(zs))
        if z >= G: borrar.append((o.name, G, (x, y)))                                       # SOBRESALE del terreno: se borra
        elif al_cielo(x, y, z) and "tierra" in o.name: pasto.append(o.name)                    # al ras o en un hueco y se ve desde el cielo: su cara de arriba pasa a PASTO
    cols = {}
    for n, G, (x, y) in borrar:
        if n.startswith(pref): cols[(x, y)] = G
    for (x, y), G in cols.items():
        c = (x, y, G - 1)
        if c in cav: continue
        quedan = c in ocup and all(b[0] != ocup[c].name for b in borrar)
        if not quedan and not superficie_mundo(x, y, G): rellenar.append(c)
print("ENTRADAS: borrar %d bloques %s" % (len(borrar), [b[0] for b in borrar]))
print("ENTRADAS: rellenar %d celdas %s" % (len(rellenar), rellenar))
print("ENTRADAS: a pasto %d bloques %s" % (len(pasto), pasto))
if GUARDAR:
    for n, G, _ in borrar:
        o = bpy.data.objects.get(n)
        if o: bpy.data.objects.remove(o, do_unlink=True)
    col = bpy.data.collections.get("entradas_relleno_parte10") or bpy.data.collections.new("entradas_relleno_parte10")
    if col.name not in sc.collection.children: sc.collection.children.link(col)
    for n in pasto:
        o = bpy.data.objects.get(n)
        if o: o.data = me_pasto; o.name = n.replace('_tierra_', '_pasto_')
    for (x, y, z) in rellenar:
        ob = bpy.data.objects.new("entrada_pasto_%d_%d_%d" % (x, y, z), me_pasto); ob.location = (x + .5, y + .5, z + .5); col.objects.link(ob)
    sc.frame_start = 1; sc.frame_end = 250; sc.frame_set(1)                                  # la parte 10 empieza en el frame 1
    bpy.ops.wm.save_mainfile()
    print("GUARDADO", bpy.data.filepath)
