"""Paso 6 del flujo: busca que archivos finales aun tienen varias piezas conectadas, para anadirlas a CON_TROZOS. No guarda nada.

blender -b --factory-startup --python paso6_auditar.py -- carpeta_prendas
Muchos trozos diminutos (mayores de pocas caras) son esquirlas de relieve, no detalles: no conviene separarlos.
"""
import os
import sys

import bmesh
import bpy

BASE = os.path.abspath(sys.argv[sys.argv.index("--") + 1])


def piezas(o):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    vistos, tam = set(), []
    for v0 in bm.verts:
        if v0 in vistos:
            continue
        vistos.add(v0)
        pila, caras = [v0], set()
        while pila:
            v = pila.pop()
            caras.update(f.index for f in v.link_faces)
            for e in v.link_edges:
                w = e.other_vert(v)
                if w not in vistos:
                    vistos.add(w)
                    pila.append(w)
        tam.append(len(caras))
    bm.free()
    return sorted(tam, reverse=True)


for raiz, dirs, files in os.walk(BASE):
    dirs.sort()
    bl = [f for f in files if f.endswith(".blend")]
    if not bl or "detalles" in dirs:
        continue
    bpy.ops.wm.open_mainfile(filepath=os.path.join(raiz, bl[0]))
    for o in bpy.data.objects:
        if o.type == "MESH":
            t = piezas(o)
            if len(t) > 1:
                print("VARIAS", os.path.relpath(raiz, BASE).replace(os.sep, "/"), "caras", sum(t), "piezas", len(t), "mayores", t[:6], flush=True)
print("FIN", flush=True)
