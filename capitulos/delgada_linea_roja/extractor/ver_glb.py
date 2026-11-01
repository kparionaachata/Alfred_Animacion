"""Prueba en Blender (segundo plano): importa .glb y genera una foto de frente, lado y espalda.

blender -b --factory-startup --python ver_glb.py -- salida.png archivo1.glb [archivo2.glb ...]
"""
import math, os, sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
salida, archivos = args[0], args[1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
info = []
x = 0.0
for f in archivos:
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=f)
    nuevos = set(bpy.data.objects) - antes
    mallas = [o for o in nuevos if o.type == "MESH"]
    arm = [o for o in nuevos if o.type == "ARMATURE"]
    dep = bpy.context.evaluated_depsgraph_get()
    mn, mx = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in mallas:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mn, mx = Vector(map(min, mn, w)), Vector(map(max, mx, w))
    tris = sum(len(o.data.polygons) for o in mallas)
    mats = sorted({m.name for o in mallas for m in o.data.materials if m})
    info.append(dict(archivo=os.path.basename(f), huesos=len(arm[0].data.bones) if arm else 0, caras=tris,
                     materiales=mats, min=[round(v, 2) for v in mn], max=[round(v, 2) for v in mx]))
    for o in nuevos:
        if o.parent is None:
            o.location.x += x
    x += (mx.x - mn.x) + 1.0
for i in info:
    print("GLB", i)

sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x, sc.render.resolution_y = 1500, 700
sc.render.filepath = salida
w = bpy.data.worlds.new("w")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (.55, .6, .65, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sc.world = w
for rot in ((55, 0, 30), (40, 0, 200)):
    s = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
    s.data.energy = 2.5
    s.rotation_euler = [math.radians(a) for a in rot]
    sc.collection.objects.link(s)
ancho = max(x - 1.0, 2.0)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 70
d = max(ancho, 3.2) * 2.4
cx = ancho / 2
cam.location = (cx + d * .35, -d, 1.1)
cam.rotation_euler = (Vector((cx, 0, 1.0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.ops.render.render(write_still=True)
print("FOTO", salida)
