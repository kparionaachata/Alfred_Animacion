# -*- coding: utf-8 -*-
"""Parte 9: TAPA el carbon visible con piedra, colocando bloques `piso_bloque_piedra` ENCIMA de cada bloque de carbon (suelo y muro) sin regenerar nada.
Para dar mas irregularidad, a veces el monton sube 1-2 bloques mas. Solo en celdas libres (sin bloque y con aire). Coleccion `tapa_carbon_parte9`; repetible (`QUITAR = True`).
Ejecutar DESPUES de `piso_cueva_parte9.py` y `pared_cueva_parte9.py`."""
import bpy, math, random
from mathutils import Vector

QUITAR = bool(globals().get('QUITAR', False)); COLN = "tapa_carbon_parte9"; SEMILLA = 5; P_EXTRA = 0.45
CAE = (-133.5, -70.5); ESQ = (-139.5, -70.5)
sc = bpy.context.scene
col = bpy.data.collections.get(COLN)
if col:
    for o in list(col.objects): bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(col)
if QUITAR:
    print("tapa del carbon quitada")
else:
    bloques = [o for c in ("piso_cueva_parte9", "pared_cueva_parte9") if c in bpy.data.collections for o in bpy.data.collections[c].objects if o.name.startswith(("piso_", "pared_")) and not o.name.startswith("piso_cueva_caras")]
    celda = lambda o: (math.floor(o.location.x), math.floor(o.location.y), math.floor(o.location.z))
    ocup = {celda(o) for o in bloques}
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
    rng = random.Random(SEMILLA); me = bpy.data.meshes["piso_bloque_piedra"]
    col = bpy.data.collections.new(COLN); sc.collection.children.link(col); n = 0
    for o in sorted((o for o in bloques if "_carbon_" in o.name), key=lambda o: o.name):
        x, y, z = celda(o)
        if math.hypot(x + .5 - CAE[0], y + .5 - CAE[1]) < 2.6 or math.hypot(x + .5 - ESQ[0], y + .5 - ESQ[1]) < 1.6: continue
        alto = 1 + (rng.random() < P_EXTRA) + (rng.random() < P_EXTRA * 0.4)
        for zz in range(z + 1, z + 1 + alto):
            if (x, y, zz) in ocup or not aire(x, y, zz): break
            ob = bpy.data.objects.new("tapa_piedra_%d_%d_%d" % (x, y, zz), me); ob.location = (x + .5, y + .5, zz + .5); col.objects.link(ob); ocup.add((x, y, zz)); n += 1
    print("TAPA CARBON: %d bloques de piedra encima del carbon" % n)
