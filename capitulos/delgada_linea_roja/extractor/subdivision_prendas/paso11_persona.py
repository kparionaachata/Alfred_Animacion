"""Paso 11 del flujo: subdivide la persona como la ropa, un .blend y una foto por detalle. No guarda el archivo de entrada.

blender -b montado.blend --factory-startup --python paso11_persona.py -- carpeta_salida
Piel de la cabeza por zonas (frente, parpados, nariz, mejillas, boca, menton, orejas, cuero cabelludo, cuello), manos, ojos y cada tipo de pelo.
Las zonas de piel guardan las normales de la cabeza entera, asi no se ven costuras al juntarlas.
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

SALIDA = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
bpy.context.preferences.filepaths.save_version = 0
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
cabeza = bpy.data.objects["heads"]
OJO_X, OJO_Z = cabeza["ojo_x"], cabeza["ojo_z"]


def zona_de(p):
    """Zona de una cara por su centro; en pares, D es x positiva, como en las prendas."""
    x, y, z = p
    ax, lado = abs(x), "D" if x > 0 else "I"
    if z < 1.688 or (y > .03 and z < 1.77):
        return "cuello"
    if z > 1.866 or (y > -.02 and z > 1.82) or y > .03:
        return "cuero_cabelludo"
    if ax > .07 and y > -.035 and 1.765 < z < 1.85:
        return "oreja_" + lado
    if z > 1.836:
        return "frente"
    if abs(ax - OJO_X) < .024 and abs(z - OJO_Z) < .0175:
        return "parpados_" + lado
    if ax < .021 and 1.757 < z < 1.836:
        return "nariz"
    if ax < .031 and 1.73 <= z <= 1.757:
        return "boca"
    if ax < .046 and z < 1.73:
        return "menton"
    return "mejilla_" + lado


def piezas_piel():
    """Copia de la cabeza por cada zona, con sus normales guardadas."""
    me = cabeza.data
    me.calc_loop_triangles()
    n_es = np.empty(len(me.loops) * 3, np.float32)
    me.corner_normals.foreach_get("vector", n_es)
    n_es = n_es.reshape(-1, 3)
    zonas = [zona_de(p.center) for p in me.polygons]
    salida = {}
    for nombre in sorted(set(zonas)):
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        guarda = {}
        for f in bm.faces:
            if zonas[f.index] == nombre:
                for l in f.loops:
                    guarda[(f.index, l.vert.index)] = None
        for p in me.polygons:
            if zonas[p.index] == nombre:
                for li in p.loop_indices:
                    guarda[(p.index, me.loops[li].vertex_index)] = n_es[li].tolist()
        # en el mismo orden que quedaran: se guardan por posicion
        por_pos = {}
        for (fi, vi), nr in guarda.items():
            por_pos[(fi, tuple(round(c, 6) for c in me.vertices[vi].co))] = nr
        restantes = [f.index for f in bm.faces if zonas[f.index] == nombre]
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if zonas[f.index] != nombre], context="FACES")
        malla = bpy.data.meshes.new("persona_" + nombre)
        bm.to_mesh(malla)
        bm.free()
        lista = []
        for p, fi in zip(malla.polygons, restantes):
            for li in p.loop_indices:
                lista.append(por_pos[(fi, tuple(round(c, 6) for c in malla.vertices[malla.loops[li].vertex_index].co))])
        malla.normals_split_custom_set(lista)
        malla.materials.append(me.materials[0])
        o = bpy.data.objects.new("persona_" + nombre, malla)
        for g in cabeza.vertex_groups:
            if g.name not in o.vertex_groups:
                o.vertex_groups.new(name=g.name)
        o.parent = arm
        o.modifiers.new("Armature", "ARMATURE").object = arm
        salida[nombre] = [o]
    return salida


def separar_manos():
    h = bpy.data.objects["hands"]
    salida = {}
    for lado, signo in (("D", 1), ("I", -1)):
        malla = h.data.copy()
        bm = bmesh.new()
        bm.from_mesh(malla)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().x * signo < 0], context="FACES")
        bm.to_mesh(malla)
        bm.free()
        o = bpy.data.objects.new("persona_mano_" + lado, malla)
        o.parent = arm
        o.modifiers.new("Armature", "ARMATURE").object = arm
        salida["mano_" + lado] = [o]
    return salida


def foto(ruta, objs):
    sc = bpy.context.scene
    r, cy = sc.render, sc.cycles
    r.engine = "CYCLES"
    cy.device, cy.samples, cy.use_denoising = "GPU", 24, True
    r.resolution_x, r.resolution_y = 640, 500
    r.film_transparent = False
    r.image_settings.file_format = "PNG"
    sc.view_settings.view_transform, sc.view_settings.look = "AgX", "None"
    r.filepath = ruta
    bpy.context.view_layer.update()
    esq = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    bajo = Vector(min(p[i] for p in esq) for i in range(3))
    alto = Vector(max(p[i] for p in esq) for i in range(3))
    centro, med = (bajo + alto) / 2, alto - bajo
    dist = max(med.z * 2.4, max(med.x, med.y) * 1.9, .05)
    cam = sc.camera
    cam.location = centro + Vector((dist * .3, -dist, dist * .08))
    cam.rotation_euler = (centro - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.render.render(write_still=True)


try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == "OPTIX" and "T400" not in d.name
except Exception as e:
    print("AVISO: sin OPTIX", e, flush=True)

detalles = {}
detalles.update(piezas_piel())
detalles.update(separar_manos())
ojos = bpy.data.objects["rostro_ojos"]
detalles["ojos"] = [ojos]
for o in bpy.data.objects:
    if o.name.startswith("rostro_") and o is not ojos:
        detalles[o.name.replace("rostro_", "")] = [o]

sc = bpy.context.scene
for o in list(bpy.data.objects):
    o.hide_render = o is not arm
w = bpy.data.worlds.new("_f")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (.6, .6, .58, 1)
sc.world = w
sol = bpy.data.objects.new("_sol", bpy.data.lights.new("_sol", "SUN"))
sol.data.energy, sol.data.angle = 3.2, math.radians(6)
sol.rotation_euler = (math.radians(58), 0, math.radians(-28))
sc.collection.objects.link(sol)
cam = bpy.data.objects.new("_cam", bpy.data.cameras.new("_cam"))
cam.data.lens, cam.data.clip_start = 60, .005
sc.collection.objects.link(cam)
sc.camera = cam

os.makedirs(SALIDA, exist_ok=True)
for nombre, objs in sorted(detalles.items()):
    d = os.path.join(SALIDA, nombre)
    os.makedirs(d, exist_ok=True)
    escena = bpy.data.scenes.new(nombre)
    for o in objs + [arm]:
        if o.name not in sc.collection.objects and o.name not in {x.name for c in o.users_collection for x in c.objects}:
            sc.collection.objects.link(o)
        escena.collection.objects.link(o)
    for o in objs:
        o.hide_render = False
    foto(os.path.join(d, "vista.png"), objs)
    for o in objs:
        o.hide_render = True
    arm.hide_render = False
    ruta = os.path.join(d, nombre + ".blend")
    bpy.data.libraries.write(ruta, {escena}, compress=True, path_remap="ABSOLUTE")
    print(f"PIEZA {nombre} {sum(len(o.data.polygons) for o in objs)} caras {os.path.getsize(ruta) // 1024}KB", flush=True)
    bpy.data.scenes.remove(escena)
print("TOTAL", len(detalles), flush=True)
print("FIN", flush=True)
