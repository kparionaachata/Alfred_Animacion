"""Paso 9 del flujo: monta los detalles de prendas_cine sobre el esqueleto del personaje, en un archivo nuevo. El original no se guarda.

blender -b personaje.blend --factory-startup --python paso9_montar_cine.py -- personajes/config.py salida.blend
Quita las mallas repartidas en PRENDAS y deja lo demas: manos, cabeza, equipo y la piel de las mallas cortadas.
Las texturas y materiales repetidos se juntan: cada detalle trae su copia y el archivo pasaria de 700 MB.
"""
import hashlib
import os
import re
import sys

import bmesh
import bpy
import numpy as np

ARGS = sys.argv[sys.argv.index("--") + 1:]
ORIGEN = bpy.data.filepath
SALIDA = os.path.abspath(ARGS[1])
CARPETA = os.path.join(os.path.dirname(ORIGEN), "prendas_cine")
if os.path.normcase(SALIDA) == os.path.normcase(ORIGEN):
    raise RuntimeError("La salida no puede ser el personaje original")
bpy.context.preferences.filepaths.save_version = 0
exec(compile(open(ARGS[0], encoding="utf-8").read(), ARGS[0], "exec"))


def area(objs):
    return sum(f.area for o in objs for f in o.data.polygons)


def tomar_mallas():
    """Quita lo que ya esta en prendas_cine. Devuelve el area quitada; de una malla con zonas se queda lo que ninguna prenda usa."""
    enteras, cortadas, prefijos = set(), {}, []
    for prenda, (mallas, corte, pref) in PRENDAS.items():
        enteras.update(mallas)
        if corte:
            cortadas.setdefault(corte[0], (corte[1], set()))[1].add(prenda)
        prefijos += pref
    quitada = 0.0
    for nombre, (zona, prendas) in cortadas.items():
        o = bpy.data.objects[nombre]
        antes = area([o])
        bm = bmesh.new()
        bm.from_mesh(o.data)
        uvl = bm.loops.layers.uv.active
        fuera = [f for f in bm.faces if zona([l[uvl].uv[0] for l in f.loops], [l[uvl].uv[1] for l in f.loops], [v.co.z for v in f.verts]) in prendas]
        bmesh.ops.delete(bm, geom=fuera, context="FACES")
        bm.to_mesh(o.data)
        bm.free()
        o.data.update()
        if not o.data.polygons:
            enteras.add(nombre)
        quitada += antes - area([o])
        print("CORTADA", nombre, "quedan", len(o.data.polygons), "caras", flush=True)
    for o in [o for o in bpy.data.objects if o.type == "MESH" and (o.name in enteras or o.name.startswith(tuple(prefijos)))]:
        quitada += area([o])
        bpy.data.objects.remove(o)
    return quitada


def huella(im):
    w, h = im.size
    p = np.empty(w * h * im.channels, np.float32)
    im.pixels.foreach_get(p)
    return (w, h, hashlib.md5(p.tobytes()).hexdigest())


def raiz_de(nombre):
    return re.sub(r"\.\d{3}$", "", nombre)


def firma(m):
    return (len(m.node_tree.nodes), len(m.node_tree.links))


imagenes, materiales = {}, {}
for im in bpy.data.images:
    if im.has_data and im.size[0]:
        imagenes[(raiz_de(im.name), huella(im))] = im
TAMANOS = {}


def juntar(nuevas_img, nuevos_mat, nuevos_grp):
    for im in nuevas_img:
        llave = (raiz_de(im.name), huella(im))
        prima = imagenes.setdefault(llave, im)
        if prima is not im:
            im.user_remap(prima)
            bpy.data.images.remove(im)
    for g in nuevos_grp:
        prima = bpy.data.node_groups.get(raiz_de(g.name))
        if prima is not None and prima is not g:
            g.user_remap(prima)
            bpy.data.node_groups.remove(g)
    for m in nuevos_mat:
        llave = (raiz_de(m.name), firma(m))
        prima = materiales.setdefault(llave, m)
        if prima is not m:
            m.user_remap(prima)
            bpy.data.materials.remove(m)


arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
quitada = tomar_mallas()
coleccion = next(c for c in bpy.data.collections if arm.name in c.objects)
hojas = []
for raiz, dirs, files in os.walk(CARPETA):
    dirs.sort()
    nombre = os.path.basename(raiz) + ".blend"
    if nombre in files and "detalles" not in dirs:
        hojas.append(os.path.relpath(os.path.join(raiz, nombre), CARPETA).replace(os.sep, "/"))
puesta = 0.0
por_prenda = {}
for n, rel in enumerate(hojas, 1):
    img0, mat0, grp0, arm0 = set(bpy.data.images), set(bpy.data.materials), set(bpy.data.node_groups), set(bpy.data.armatures)
    with bpy.data.libraries.load(os.path.join(CARPETA, *rel.split("/"))) as (ori, des):
        des.objects = list(ori.objects)
    prenda = rel.split("/")[0]
    col = por_prenda.get(prenda)
    if col is None:
        col = por_prenda[prenda] = bpy.data.collections.new("cine_" + prenda)
        coleccion.children.link(col)
    otros = []
    for o in des.objects:
        if o.type != "MESH":
            otros.append(o)
            continue
        col.objects.link(o)
        o.parent = arm
        o.matrix_parent_inverse.identity()
        o["cine_ruta"] = rel
        for m in o.modifiers:
            if m.type == "ARMATURE":
                m.object = arm
        puesta += area([o])
    for o in otros:
        bpy.data.objects.remove(o)
    for a in set(bpy.data.armatures) - arm0:
        bpy.data.armatures.remove(a)
    juntar(set(bpy.data.images) - img0, set(bpy.data.materials) - mat0, set(bpy.data.node_groups) - grp0)
    if n % 50 == 0:
        print("MONTADAS", n, "de", len(hojas), flush=True)
# colecciones de los detalles 3D originales, ya vacias
for c in [c for c in bpy.data.collections if c.name.startswith("det_")] + [c for c in bpy.data.collections if c.name == "detalles_3d"]:
    if not c.objects and not c.children:
        bpy.data.collections.remove(c)
bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
for i in bpy.data.images:
    if not i.packed_file and i.has_data and i.source == "GENERATED":
        i.pack()
bpy.ops.wm.save_as_mainfile(filepath=SALIDA, compress=True, check_existing=False)
print(f"AREA quitada={quitada:.3f} puesta={puesta:.3f} ({puesta / quitada:.1%})", flush=True)
print(f"TOTAL piezas={len(hojas)} objetos={len(bpy.data.objects)} materiales={len(bpy.data.materials)} imagenes={len(bpy.data.images)} {os.path.getsize(SALIDA) // 1024 // 1024}MB", flush=True)
print("FIN", flush=True)
