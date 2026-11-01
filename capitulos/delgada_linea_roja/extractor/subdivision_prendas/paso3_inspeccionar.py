"""Paso 3 del flujo: muestra de que esta hecho un .blend, para escribir la configuracion del personaje. No guarda el .blend.

blender -b archivo.blend --factory-startup --python paso3_inspeccionar.py -- carpeta_salida
Sirve con el personaje entero y con una pieza suelta. Por cada malla imprime sus piezas conectadas (vertices, caras, posicion y UV)
y deja <malla>_uv.png: el dibujo de su textura ampliado, con las aristas de UV en verde y una rejilla cada 50 pixeles de textura en azul.
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np

SALIDA = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
os.makedirs(SALIDA, exist_ok=True)


def piezas(o):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    uvl = bm.loops.layers.uv.active
    vistos, filas = set(), []
    for v0 in bm.verts:
        if v0 in vistos:
            continue
        vistos.add(v0)
        pila, comp, caras = [v0], [], set()
        while pila:
            v = pila.pop()
            comp.append(v)
            caras.update(f.index for f in v.link_faces)
            for e in v.link_edges:
                w = e.other_vert(v)
                if w not in vistos:
                    vistos.add(w)
                    pila.append(w)
        p = np.array([v.co[:] for v in comp])
        uv = np.array([l[uvl].uv[:] for v in comp for l in v.link_loops] or [(0, 0)])
        filas.append((len(comp), len(caras), p.min(0).round(2).tolist(), p.max(0).round(2).tolist(), uv.min(0).round(2).tolist(), uv.max(0).round(2).tolist()))
    bm.free()
    return sorted(filas, key=lambda f: -f[1])


def dibujo(o):
    """Recorte de la textura con las UV encima. Devuelve la caja del recorte en pixeles de textura."""
    me = o.data
    tex = next((n.image for n in o.material_slots[0].material.node_tree.nodes
                if n.type == "TEX_IMAGE" and n.image and n.image.name.endswith("_difusa")), None)
    if tex is None:
        return None
    w, h = tex.size
    px = np.empty(w * h * 4, np.float32)
    tex.pixels.foreach_get(px)
    t = px.reshape(h, w, 4)[::-1][..., :3]
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers.active.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2) * (w, h)
    uv[:, 1] = h - uv[:, 1]
    x0, y0 = max(0, int(uv[:, 0].min()) - 4), max(0, int(uv[:, 1].min()) - 4)
    x1, y1 = min(w, int(uv[:, 0].max()) + 5), min(h, int(uv[:, 1].max()) + 5)
    e = max(1, 1000 // max(x1 - x0, y1 - y0))
    im = np.repeat(np.repeat(t[y0:y1, x0:x1], e, 0), e, 1)
    for x in range((x0 // 50 + 1) * 50, x1, 50):
        im[:, (x - x0) * e] = (.2, .5, 1)
    for y in range((y0 // 50 + 1) * 50, y1, 50):
        im[(y - y0) * e, :] = (.2, .5, 1)
    for p in me.polygons:
        q = (uv[list(p.loop_indices)] - (x0, y0)) * e
        for a, b in zip(q, np.roll(q, -1, axis=0)):
            n = int(max(abs(b - a))) + 1
            xs = np.clip(np.linspace(a[0], b[0], n).astype(int), 0, im.shape[1] - 1)
            ys = np.clip(np.linspace(a[1], b[1], n).astype(int), 0, im.shape[0] - 1)
            im[ys, xs] = (0, 1, 0)
    sal = bpy.data.images.new("_uv", im.shape[1], im.shape[0], alpha=False)
    sal.colorspace_settings.name = "Non-Color"
    rgba = np.ones((*im.shape[:2], 4), np.float32)
    rgba[..., :3] = im
    sal.pixels.foreach_set(rgba[::-1].ravel())
    sal.filepath_raw = os.path.join(SALIDA, o.name + "_uv.png")
    sal.file_format = "PNG"
    sal.save()
    bpy.data.images.remove(sal)
    return (x0, y0, x1, y1), e


for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    filas = piezas(o)
    mat = o.material_slots[0].material.name if o.material_slots and o.material_slots[0].material else None
    caja = dibujo(o) if mat and o.data.uv_layers else None
    print("MALLA", o.name, "material", mat, "caras", len(o.data.polygons), "piezas", len(filas), "recorte_textura_y_aumento", caja, flush=True)
    for f in filas[:40]:
        print("  verts", f[0], "caras", f[1], "xyz", f[2], f[3], "uv", f[4], f[5], flush=True)
    if len(filas) > 40:
        print("  ... y", len(filas) - 40, "piezas mas", flush=True)
print("FIN", flush=True)
