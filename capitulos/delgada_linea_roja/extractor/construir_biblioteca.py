"""Crea biblioteca_personajes/: un .blend en pose neutral y una foto por personaje, una carpeta por arma y el .blend de equipo.

blender -b --factory-startup --python construir_biblioteca.py -- carpeta_temporal [nombre_personaje]
Con nombre_personaje solo construye ese (y no las armas). Lee el manifiesto de exportar_biblioteca.py.
"""
import json, math, os, sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
tmp = args[0]
solo = args[1] if len(args) > 1 else None
SALIDA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "biblioteca_personajes")
man = json.load(open(os.path.join(tmp, "manifiesto.json"), encoding="utf-8"))


def limpiar():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def importar(f):
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=f)
    nuevos = [o for o in bpy.data.objects if o not in antes]
    for o in [o for o in nuevos if o.type == "MESH" and o.name.startswith("Icosphere")]:
        nuevos.remove(o)
        bpy.data.objects.remove(o)
    for me in [m for m in bpy.data.meshes if m.users == 0]:
        bpy.data.meshes.remove(me)
    for c in [c for c in bpy.data.collections if c.name.startswith("glTF_not_exported")]:
        bpy.data.collections.remove(c)
    return nuevos


def coleccion(padre, nombre):
    c = bpy.data.collections.new(nombre)
    padre.children.link(c)
    return c


def mover(o, col):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    col.objects.link(o)


def foto(ruta, centro, dist, ancho=900, alto=700):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = ancho, alto
    sc.render.filepath = ruta
    w = bpy.data.worlds.new("fondo_foto")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (.6, .63, .67, 1)
    sc.world = w
    extras = []
    for rot in ((55, 0, 30), (40, 0, 200)):
        s = bpy.data.objects.new("sol_foto", bpy.data.lights.new("sol_foto", "SUN"))
        s.data.energy = 2.5
        s.rotation_euler = [math.radians(a) for a in rot]
        sc.collection.objects.link(s)
        extras.append(s)
    cam = bpy.data.objects.new("cam_foto", bpy.data.cameras.new("cam_foto"))
    sc.collection.objects.link(cam)
    extras.append(cam)
    sc.camera = cam
    cam.data.lens = 50
    cam.location = Vector(centro) + Vector((dist * .25, -dist, .3))
    cam.rotation_euler = (Vector(centro) - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.render.render(write_still=True)
    # la camara y las luces de la foto no quedan en el .blend
    datos = [o.data for o in extras]
    for o in extras:
        bpy.data.objects.remove(o)
    for d in datos:
        (bpy.data.lights if isinstance(d, bpy.types.Light) else bpy.data.cameras).remove(d)
    sc.camera = None
    sc.world = None
    bpy.data.worlds.remove(w)


def guardar(ruta):
    for im in bpy.data.images:
        if not im.packed_file and im.has_data and im.type == "IMAGE":
            im.pack()
    bpy.ops.wm.save_as_mainfile(filepath=ruta, compress=True, check_existing=False)


def personaje(p):
    limpiar()
    sc = bpy.context.scene
    sc.render.fps = 20
    nuevos = importar(p["glb"])
    arm = next(o for o in nuevos if o.type == "ARMATURE")
    arm.name = p["nombre"] + "_armature"
    raiz = coleccion(sc.collection, p["nombre"])
    cols = {}
    mover(arm, raiz)
    faltan = []
    por_nombre = {o.name: o for o in nuevos if o.type == "MESH"}
    for pieza in p["piezas"]:
        o = por_nombre.get(pieza["nodo"])
        if o is None:
            faltan.append(pieza["nodo"])
            continue
        c = cols.get(pieza["coleccion"]) or coleccion(raiz, pieza["coleccion"])
        cols[pieza["coleccion"]] = c
        mover(o, c)
        if pieza["coleccion"] in ("equipo", "instrumentos"):
            o.asset_mark()
    raiz.asset_mark()
    if "alternativas" in cols:
        vl = bpy.context.view_layer.layer_collection.children[raiz.name].children["alternativas"]
        vl.exclude = True
    d = os.path.join(SALIDA, p["grupo"], p["nombre"])
    os.makedirs(d, exist_ok=True)
    if p["tipo"] == "hombre":
        with open(os.path.join(d, "armas.json"), "w", encoding="utf-8") as f:
            json.dump(p["armas"], f, indent=1)
        foto(os.path.join(d, "vista.png"), (0, 0, 1.0), 6.0)
    else:
        foto(os.path.join(d, "vista.png"), (0, 0, 1.2), 7.5)
    guardar(os.path.join(d, p["nombre"] + ".blend"))
    print("BLEND", p["nombre"], len(p["piezas"]), "faltan", faltan, os.path.getsize(os.path.join(d, p["nombre"] + ".blend")) // 1024 // 1024, "MB", flush=True)


def arma(glb, pieza):
    """Un .blend por arma: la malla en su origen de empunadura y el hueso que le toca en la propiedad "hueso"."""
    limpiar()
    sc = bpy.context.scene
    nuevos = importar(glb)
    o = next(x for x in nuevos if x.name == pieza["nodo"])
    for x in nuevos:
        if x is not o:
            bpy.data.objects.remove(x)
    for me in [m for m in bpy.data.meshes if m.users == 0]:
        bpy.data.meshes.remove(me)
    raiz = coleccion(sc.collection, pieza["nodo"])
    mover(o, raiz)
    o["hueso"] = pieza["hueso"]
    o.asset_mark()
    d = os.path.join(SALIDA, "armas", pieza["nodo"])
    os.makedirs(d, exist_ok=True)
    bpy.context.view_layer.update()
    esq = [o.matrix_world @ Vector(c) for c in o.bound_box]
    centro = sum(esq, Vector()) / 8
    foto(os.path.join(d, "vista.png"), centro, max(max(o.dimensions) * 1.8, .6), 900, 450)
    guardar(os.path.join(d, pieza["nodo"] + ".blend"))
    print("BLEND arma", pieza["nodo"], pieza["hueso"], flush=True)


def equipo():
    limpiar()
    sc = bpy.context.scene
    raiz = coleccion(sc.collection, "equipo")
    cols = {}
    for e in man["equipo"]:
        nuevos = importar(e["glb"])
        por_nombre = {o.name: o for o in nuevos}
        for pieza in e["piezas"]:
            o = por_nombre[pieza["nodo"]]
            if pieza["coleccion"] == "armas":
                bpy.data.objects.remove(o)
                continue
            c = cols.get(pieza["coleccion"]) or coleccion(raiz, pieza["coleccion"])
            cols[pieza["coleccion"]] = c
            mover(o, c)
            o["hueso"] = pieza["hueso"]
            o.asset_mark()
    for me in [m for m in bpy.data.meshes if m.users == 0]:
        bpy.data.meshes.remove(me)
    for fila, (nombre, c) in enumerate(sorted(cols.items())):
        for i, o in enumerate(sorted(c.objects, key=lambda x: x.name)):
            o.location = (i * .6, fila * 2.0, 0)
    d = os.path.join(SALIDA, "equipo")
    os.makedirs(d, exist_ok=True)
    foto(os.path.join(d, "vista.png"), (5, 1, .8), 15, 1500, 800)
    guardar(os.path.join(d, "equipo.blend"))
    print("BLEND equipo", sum(len(c.objects) for c in cols.values()), flush=True)


if solo == "pendientes":
    # retoma una construccion cortada: solo armas sin .blend1 (no regeneradas) y equipo; los personajes no se tocan
    for e in man["equipo"]:
        for pieza in e["piezas"]:
            if pieza["coleccion"] == "armas" and not os.path.exists(os.path.join(SALIDA, "armas", pieza["nodo"], pieza["nodo"] + ".blend1")):
                arma(e["glb"], pieza)
    equipo()
else:
    for p in man["personajes"]:
        if not solo or p["nombre"] == solo:
            personaje(p)
    if not solo:
        for e in man["equipo"]:
            for pieza in e["piezas"]:
                if pieza["coleccion"] == "armas":
                    arma(e["glb"], pieza)
        equipo()
print("FIN", flush=True)
