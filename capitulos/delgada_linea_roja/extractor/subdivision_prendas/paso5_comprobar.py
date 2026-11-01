"""Paso 5 del flujo: comprueba todos los .blend generados. No guarda nada.

blender -b --factory-startup --python paso5_comprobar.py -- carpeta_prendas
Cada archivo debe tener esqueleto, pesos, material y texturas empaquetadas. Cada grupo de hijos debe sumar el area de su padre
y, con todos los huesos girados 12 grados, quedar sobre su superficie. Imprime TOTAL ... MAL n: n debe ser 0.
"""
import math
import os
import sys

import bpy
from mathutils import Quaternion
from mathutils.bvhtree import BVHTree

BASE = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
TOL_AREA = .001  # fraccion
TOL_POSE = .005  # metros


def blend_de(d):
    r = os.path.join(d, os.path.basename(d) + ".blend")
    return r if os.path.exists(r) else None


def medir(r):
    bpy.ops.wm.open_mainfile(filepath=r)
    arm = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    mallas = [o for o in bpy.data.objects if o.type == "MESH"]
    malos = [o.name for o in mallas if not o.data.polygons or not o.vertex_groups or not o.material_slots or o.material_slots[0].material is None
             or not [m for m in o.modifiers if m.type == "ARMATURE" and m.object in arm]
             or not any(v.groups for v in o.data.vertices)]
    sin = [i.name for i in bpy.data.images if not i.packed_file and i.has_data and i.size[0] > 0]
    area = sum(p.area for o in mallas for p in o.data.polygons)
    for b in arm[0].pose.bones if arm else ():
        b.rotation_mode = "QUATERNION"
        b.rotation_quaternion = Quaternion((1, 0, 0), math.radians(12))
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    vs, ps = [], []
    for o in mallas:
        me = o.evaluated_get(dg).to_mesh()
        k = len(vs)
        # solo los vertices con cara: el relieve del paso 1 deja algunos sueltos, que estan fuera de toda superficie
        usados = sorted({i for p in me.polygons for i in p.vertices})
        nuevo = {i: k + n for n, i in enumerate(usados)}
        vs += [(o.matrix_world @ me.vertices[i].co).copy() for i in usados]
        ps += [[nuevo[i] for i in p.vertices] for p in me.polygons]
        o.evaluated_get(dg).to_mesh_clear()
    return {"area": area, "caras": len(ps), "malos": malos, "sin": sin, "vs": vs, "ps": ps, "arm": len(arm)}


total = mal = largo = 0
cache = {}
for raiz, dirs, files in os.walk(BASE):
    dirs.sort()
    r = blend_de(raiz)
    if not r:
        continue
    m = medir(r)
    total += 1
    largo = max(largo, len(r))
    if m["malos"] or m["sin"] or m["arm"] != 1:
        mal += 1
        print("MAL archivo", os.path.relpath(r, BASE), "arm", m["arm"], "malos", m["malos"], "sin_empaquetar", m["sin"], flush=True)
    hijos = [blend_de(os.path.join(raiz, "detalles", h)) for h in sorted(os.listdir(os.path.join(raiz, "detalles")))] if "detalles" in dirs else []
    hijos = [h for h in hijos if h]
    if not hijos:
        continue
    arbol = BVHTree.FromPolygons(m["vs"], m["ps"])
    suma, peor, nombres = 0, 0, []
    for h in hijos:
        c = medir(h)
        suma += c["area"]
        nombres.append(os.path.basename(h)[:-6])
        if c["vs"]:
            peor = max(peor, max(arbol.find_nearest(q)[3] for q in c["vs"]))
    bien = abs(suma - m["area"]) <= TOL_AREA * m["area"] and peor <= TOL_POSE
    mal += not bien
    print("OK " if bien else "MAL", os.path.relpath(raiz, BASE), "hijos", len(hijos), "area", round(m["area"], 5), "suma", round(suma, 5), "desvio_pose_mm", round(peor * 1000, 2), flush=True)
print("TOTAL archivos", total, "ruta_mas_larga", largo, "MAL", mal, flush=True)
