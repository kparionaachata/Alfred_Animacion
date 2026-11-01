"""Comprueba en Blender (segundo plano) que cada .glb importa, tiene texturas y que el esqueleto deforma la malla.

blender -b --factory-startup --python comprobar_glb.py -- carpeta_personajes foto_caballo.png
"""
import glob, math, os, sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
raiz, foto = args[0], args[1]
archivos = sorted(glob.glob(os.path.join(raiz, "*", "*.glb")))
malos = 0


def limpiar():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def puntos(o):
    dep = bpy.context.evaluated_depsgraph_get()
    e = o.evaluated_get(dep)
    me = e.to_mesh()
    r = [e.matrix_world @ v.co for v in me.vertices]
    e.to_mesh_clear()
    return r


for f in archivos:
    limpiar()
    bpy.ops.import_scene.gltf(filepath=f)
    # el importador crea una esfera auxiliar (Icosphere) para los huesos: se ignora
    mallas = sorted((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: -len(o.data.vertices))
    arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    sin_tex = [m.name for o in mallas for m in o.data.materials if m and not any(n.type == "TEX_IMAGE" and n.image for n in m.node_tree.nodes)]
    p0 = puntos(mallas[0])
    alto = max(p.z for p in p0) - min(p.z for p in p0)
    # dobla un hueso y mide cuanto se mueve la malla
    h = "Head" if "Head" in arm.pose.bones else arm.pose.bones[len(arm.pose.bones) // 2].name
    b = arm.pose.bones[h]
    b.rotation_mode = "XYZ"
    b.rotation_euler = (0.8, 0, 0)
    bpy.context.view_layer.update()
    p1 = puntos(mallas[0])
    mov = max((a - c).length for a, c in zip(p0, p1))
    ok = alto > 1.2 and mov > 0.02 and not sin_tex and len(p0) > 500
    malos += 0 if ok else 1
    print("GLB", "ok " if ok else "MAL", os.path.basename(f), "alto %.2f" % alto, "verts", len(p0), "huesos", len(arm.data.bones), "mov %.2f" % mov, "sin_tex", sin_tex)
print("TOTAL", len(archivos), "MAL", malos)

# foto de lado de un jinete sobre el caballo no se monta: solo el caballo de lado y el husar
limpiar()
sc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=os.path.join(raiz, "caballos", "horse_a_hussar.glb"))
for o in bpy.data.objects:
    if o.parent is None:
        o.location.y += 0
bpy.ops.import_scene.gltf(filepath=os.path.join(raiz, "husares_rusos", "russia_cav_light_russian_hussars.soldier.glb"))
for o in bpy.data.objects:
    if o.parent is None and "hussars" in o.name or (o.parent is None and o.name.startswith("soldado")):
        o.location.x += 2.0
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x, sc.render.resolution_y = 1100, 700
sc.render.filepath = foto
w = bpy.data.worlds.new("w")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (.55, .6, .65, 1)
sc.world = w
s = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
s.data.energy = 3
s.rotation_euler = (math.radians(50), 0, math.radians(40))
sc.collection.objects.link(s)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 50
cam.location = (9.0, 0.5, 1.4)
cam.rotation_euler = (Vector((1.0, 0, 1.1)) - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.ops.render.render(write_still=True)
print("FOTO", foto)
