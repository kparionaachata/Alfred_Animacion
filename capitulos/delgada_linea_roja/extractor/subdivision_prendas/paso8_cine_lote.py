"""Paso 8 del flujo: aplica textura de cine y desgaste de batalla a todos los detalles finales de un personaje. No toca prendas/.

blender -b personaje.blend --factory-startup --python paso8_cine_lote.py -- personajes/config.py [carpeta_salida] [texto1,texto2]
Salida por defecto: <carpeta del personaje>/prendas_cine, con la misma estructura. Los textos filtran por ruta, para probar pocas piezas.
La receta de cada pieza sale de CINE en la configuracion. El desgaste solo va en lo que se ve desde fuera con el personaje completo,
y se reparte por la altura real del cuerpo: el barro de una pieza continua en la de al lado.
"""
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ARGS = sys.argv[sys.argv.index("--") + 1:]
AQUI = os.path.dirname(os.path.abspath(__file__))
ORIGEN = bpy.data.filepath
ENTRADA = os.path.join(os.path.dirname(ORIGEN), "prendas")
SALIDA = os.path.abspath(ARGS[1]) if len(ARGS) > 1 and ARGS[1] else os.path.join(os.path.dirname(ORIGEN), "prendas_cine")
FILTRO = [t for t in ARGS[2].split(",") if t] if len(ARGS) > 2 else []
LIMITE_RUTA = 255

bpy.context.preferences.filepaths.save_version = 0
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == "OPTIX" and "T400" not in d.name
except Exception as e:
    print("AVISO: sin OPTIX", e, flush=True)

exec(compile(open(ARGS[0], encoding="utf-8").read(), ARGS[0], "exec"))
CINE_LOTE = True
exec(compile(open(os.path.join(AQUI, "paso7_textura_cine.py"), encoding="utf-8").read(), "paso7", "exec"))

# loseta: tipo, tamano en metros, fuerza del dibujo y del relieve. Colores lineales, valores 0-1.
BASE = {"oscurecer": .86, "saturacion": .8, "barro": 1.0, "hollin": .8, "mancha": .7, "roce": .8, "sangre": .5, "rotos": 0.0,
        "metal": 0.0, "rug": .85, "sheen": 0.0, "falloff": False, "pale": (.05, .043, .03), "relieve": .5, "esc_barro": 30, "normal": .5, "espec": .3}
RECETAS = {
    "sarga": {"loseta": "sarga", "m": .03, "dibujo": .55, "sheen": .5, "falloff": True, "rotos": .5},
    "pano": {"loseta": "pano", "m": .05, "dibujo": .4, "sheen": .6, "falloff": True, "rotos": .4, "relieve": .25},
    "tartan": {"loseta": "sarga", "m": .045, "dibujo": .45, "sheen": .45, "falloff": True, "rotos": .4},
    "galon": {"loseta": "sarga", "m": .012, "dibujo": .4, "sheen": .35, "falloff": True, "rotos": .2, "pale": (.02, .018, .014), "oscurecer": .72},
    "ante": {"loseta": "pano", "m": .03, "dibujo": .25, "rug": .78, "roce": 1.0, "oscurecer": .7, "relieve": .15},
    "cuero": {"loseta": "cuero", "m": .05, "dibujo": .3, "rug": .42, "roce": 1.0, "relieve": .35, "pale": (.04, .032, .024), "saturacion": .9},
    "metal": {"loseta": "metal", "m": .02, "dibujo": .2, "rug": .38, "metal": 1.0, "barro": .6, "mancha": .4, "roce": 0.0, "sangre": .3, "oscurecer": .72, "relieve": .1},
    "pluma": {"loseta": "pluma", "m": .03, "dibujo": .5, "sheen": .3, "barro": .25, "mancha": .4, "roce": .3, "sangre": .15, "relieve": .3},
}


def losetas():
    """Cada loseta en una imagen periodica: R = claridad, G = altura, B = rugosidad. 1024 pixeles."""
    rng = np.random.default_rng(11)
    n = 1024
    forma = (n, n)

    def rd(sx, sy):
        return ruido(forma, sx, sy, rng)

    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    salida = {}
    # sarga 2/2 con hilos irregulares y pelusa
    k = 112
    fu = x / n * k + rd(25, 12) * .14
    fv = y / n * k + rd(25, 12) * .14
    j, i = np.floor(fu).astype(int), np.floor(fv).astype(int)
    a, b = fu - j, fv - i
    urd = ((i + j) % 4) < 2
    ta, tb = rng.normal(0, 1, k + 2), rng.normal(0, 1, k + 2)
    arriba = np.where(urd, np.sin(np.pi * b) ** .55 * (.55 + .45 * np.sin(np.pi * a)) * (1 + .12 * ta[i % (k + 2)]),
                      np.sin(np.pi * a) ** .55 * (.55 + .45 * np.sin(np.pi * b)) * (1 + .12 * tb[j % (k + 2)]))
    fibra = np.where(urd, rd(30, .7), rd(.7, 30))
    salida["sarga"] = np.dstack((.5 + .28 * (np.clip(arriba, 0, 1) - .6) + .08 * fibra, np.clip(.62 * arriba + .1 * fibra, 0, 1), .5 + .1 * fibra))
    # pano abatanado: fieltro sin hilos visibles
    p1 = rd(1.5, 1.5) * .6 + rd(5, 5) * .4 + rd(20, 3) * .2
    salida["pano"] = np.dstack((.5 + .13 * p1, np.clip(.5 + .17 * p1, 0, 1), .5 + .08 * p1))
    # cuero: grano y arrugas
    g = np.abs(rd(6, 6)) * .7 + np.abs(rd(22, 5)) * .5 + rd(1.5, 1.5) * .12
    salida["cuero"] = np.dstack((.56 - .14 * np.clip(g, 0, 2), np.clip(.8 - .34 * g, 0, 1), .45 + .22 * np.clip(g, 0, 2)))
    # metal: rayas y picado
    r = rd(90, .8) * .6 + rd(.8, 60) * .3 + np.clip(rd(3, 3) - 1.6, 0, 1)
    salida["metal"] = np.dstack((.5 + .1 * r, np.clip(.5 + .09 * r, 0, 1), .5 + .16 * r))
    # barbas de pluma
    b1 = rd(1.1, 60) * .7 + rd(4, 90) * .4
    salida["pluma"] = np.dstack((.5 + .22 * b1, np.clip(.5 + .24 * b1, 0, 1), .55 + .08 * b1))
    return {t: np.clip(v, 0, 1).astype(np.float32) for t, v in salida.items()}


def receta_de(rel):
    for texto, nombre in CINE:
        if texto in rel:
            return nombre
    return None


def arbol_personaje():
    """Malla completa en pose T, sin lo que no lleva puesto: mide lo que se ve desde fuera."""
    vs, ps = [], []
    for o in bpy.data.objects:
        if o.type != "MESH" or o.name.startswith("euro_flask0") and not o.name.endswith("1") or o.name.startswith("nap_"):
            continue
        k = len(vs)
        vs += [(o.matrix_world @ v.co).copy() for v in o.data.vertices]
        ps += [[i + k for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(vs, ps)


# direcciones repartidas por la esfera; se usan las del lado de fuera de cada cara
_n = 40
_i = np.arange(_n) + .5
_z = 1 - 2 * _i / _n
_f = np.pi * (1 + 5 ** .5) * _i
RAYOS = [Vector(v) for v in np.c_[np.sqrt(1 - _z ** 2) * np.cos(_f), np.sqrt(1 - _z ** 2) * np.sin(_f), _z].tolist()]


def visibilidad(o, arbol):
    """Atributo de cara cine_vis: 1 si la cara se ve desde fuera, 0 si queda tapada por otra pieza o contra el cuerpo."""
    me = o.data
    vis = np.zeros(len(me.polygons), np.float32)
    pasos = RAYOS if len(me.polygons) < 1500 else RAYOS[::4]
    for f in me.polygons:
        c = o.matrix_world @ f.center
        n = (o.matrix_world.to_3x3() @ f.normal).normalized()
        total = libres = 0
        for r in pasos:
            d = n.dot(r)
            if d <= .05:
                continue
            total += 1
            # el origen se separa de la cara para no chocar con ella ni con lo que esta pegado
            if arbol.ray_cast(c + n * .0035 + r * .001, r, 2.0)[0] is None:
                libres += 1
        vis[f.index] = 1.0 if total and libres / total >= .1 else 0.0
    if "cine_vis" in me.attributes:
        me.attributes.remove(me.attributes["cine_vis"])
    me.attributes.new("cine_vis", "FLOAT", "FACE").data.foreach_set("value", vis)
    p = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", p)
    p = (np.c_[p.reshape(-1, 3), np.ones(len(me.vertices))] @ np.array(o.matrix_world, np.float32).T)[:, :3]
    if "cine_p" in me.attributes:
        me.attributes.remove(me.attributes["cine_p"])
    me.attributes.new("cine_p", "FLOAT_VECTOR", "POINT").data.foreach_set("vector", p.astype(np.float32).ravel())
    return float(vis.mean()) if len(vis) else 0.0


def limpiar_normales(me):
    """Las caras del corte por dibujo dan manchas con sus normales guardadas: se calculan otra vez."""
    if not any(len(p.vertices) > 4 for p in me.polygons):
        return
    if "custom_normal" in me.attributes:
        me.attributes.remove(me.attributes["custom_normal"])
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(70))


def material_cine(nombre_base, rec, imagen_loseta):
    r = {**BASE, **RECETAS[rec]}
    m = bpy.data.materials.new(f"{nombre_base}_cine_{rec}")
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    p = next(n for n in N if n.type == "BSDF_PRINCIPLED")

    def nodo(t, **prop):
        n = N.new(t)
        for k, v in prop.items():
            setattr(n, k, v)
        return n

    def poner(sock, v):
        if isinstance(v, (int, float, tuple, list)):
            sock.default_value = v
        else:
            L.new(v, sock)

    def mate(op, a, b=None, clamp=False):
        n = nodo("ShaderNodeMath", operation=op, use_clamp=clamp)
        poner(n.inputs[0], a)
        if b is not None:
            poner(n.inputs[1], b)
        return n.outputs[0]

    def rango(v, a, b, c=0.0, d=1.0):
        n = nodo("ShaderNodeMapRange", clamp=True, interpolation_type="SMOOTHSTEP")
        poner(n.inputs[0], v)
        n.inputs[1].default_value, n.inputs[2].default_value, n.inputs[3].default_value, n.inputs[4].default_value = a, b, c, d
        return n.outputs[0]

    def mezcla(f, a, b, tipo="MIX"):
        n = nodo("ShaderNodeMix", data_type="RGBA", blend_type=tipo, clamp_result=True)
        poner(n.inputs[0], f)
        poner(n.inputs[6], a)
        poner(n.inputs[7], tuple(b) + (1,) if isinstance(b, tuple) else b)
        return n.outputs[2]

    pos = nodo("ShaderNodeAttribute", attribute_name="cine_p").outputs["Vector"]
    vis = nodo("ShaderNodeAttribute", attribute_name="cine_vis").outputs["Fac"]

    def ruid(esc, det=3.0):
        n = nodo("ShaderNodeTexNoise")
        L.new(pos, n.inputs["Vector"])
        n.inputs["Scale"].default_value, n.inputs["Detail"].default_value = esc, det
        return n.outputs["Fac"]

    uv = nodo("ShaderNodeUVMap", uv_map="UVMap").outputs[0]

    def juego(suf, datos=True):
        n = nodo("ShaderNodeTexImage", interpolation="Cubic")
        n.image = bpy.data.images[nombre_base + suf]
        L.new(uv, n.inputs[0])
        return n

    mp = nodo("ShaderNodeMapping")
    L.new(pos, mp.inputs["Vector"])
    mp.inputs["Scale"].default_value = (1 / r["m"],) * 3
    tl = nodo("ShaderNodeTexImage", projection="BOX", projection_blend=.25)
    tl.image = imagen_loseta
    L.new(mp.outputs[0], tl.inputs[0])
    sp = nodo("ShaderNodeSeparateColor")
    L.new(tl.outputs[0], sp.inputs[0])
    claro, alto, rug_t = sp.outputs[0], sp.outputs[1], sp.outputs[2]

    # color del juego con su dibujo, hilo o grano encima
    hs = nodo("ShaderNodeHueSaturation")
    hs.inputs["Saturation"].default_value = r["saturacion"]
    hs.inputs["Value"].default_value = r["oscurecer"]
    L.new(vis, hs.inputs["Fac"])
    L.new(juego("_difusa").outputs[0], hs.inputs["Color"])
    fac = mate("ADD", 1.0, mate("MULTIPLY", mate("SUBTRACT", claro, .5), 2 * r["dibujo"]))
    esc = nodo("ShaderNodeVectorMath", operation="SCALE")
    L.new(hs.outputs[0], esc.inputs[0])
    L.new(fac, esc.inputs["Scale"])
    color = esc.outputs[0]

    # mascaras de desgaste por altura real y ruido; todas a 0 en lo que no se ve
    z = nodo("ShaderNodeSeparateXYZ")
    L.new(pos, z.inputs[0])
    zv = z.outputs[2]
    subida = rango(zv, .62, .02, 0, 1)
    v_ = lambda x, k=1.0: mate("MULTIPLY", mate("MULTIPLY", x, vis), k, True)
    roce = v_(rango(mate("ADD", ruid(28, 4), mate("MULTIPLY", alto, .12)), .52, .68), r["roce"])
    mancha = v_(rango(ruid(9, 4), .5, .62), r["mancha"])
    cerco = v_(rango(mate("ABSOLUTE", mate("SUBTRACT", ruid(9, 4), .5)), .03, 0.0), r["mancha"] * .5)
    hollin = v_(mate("MULTIPLY", rango(ruid(14, 5), .54, .66), mate("ADD", .7, mate("MULTIPLY", ruid(600, 1), .5))), r["hollin"])
    costra = rango(mate("ADD", mate("MULTIPLY", subida, .8), mate("MULTIPLY", mate("SUBTRACT", ruid(r["esc_barro"], 6), .5), 1.4)), .5, .68)
    salp = mate("MULTIPLY", rango(ruid(320, 1), .73, .76), mate("ADD", rango(ruid(10, 2), .45, .6), mate("MULTIPLY", subida, .6)), True)
    barro = v_(mate("MAXIMUM", costra, salp), r["barro"])
    gota = v_(mate("MULTIPLY", rango(ruid(380, 1), .75, .78), rango(ruid(6, 2), .62, .68)), r["sangre"])

    color = mezcla(mate("MULTIPLY", roce, mate("MULTIPLY", rango(alto, .35, .7), .9)), color, r["pale"], "ADD")
    color = mezcla(mate("MULTIPLY", mancha, .5), color, (.32, .3, .27), "MULTIPLY")
    color = mezcla(cerco, color, (.03, .027, .02), "ADD")
    color = mezcla(mate("MULTIPLY", hollin, .75), color, (.012, .012, .012))
    tierra = mezcla(rango(ruid(280, 3), .35, .65), (.062, .047, .031, 1), (.115, .09, .06))
    color = mezcla(mate("MULTIPLY", barro, .92), color, tierra)
    color = mezcla(mate("MULTIPLY", gota, .9), color, (.03, .006, .004))
    L.new(color, p.inputs["Base Color"])
    L.new(color, p.inputs["Sheen Tint"])  # con el blanco por defecto la tela se ve gris

    # rugosidad y metal: el barro y el hollin matan el brillo; el roce pule
    rug = mate("ADD", r["rug"], mate("MULTIPLY", mate("SUBTRACT", rug_t, .5), .5))
    rug = mate("SUBTRACT", rug, mate("MULTIPLY", roce, .18))
    rug = mate("ADD", rug, mate("MULTIPLY", mate("MAXIMUM", barro, hollin), .5), True)
    L.new(rug, p.inputs["Roughness"])
    p.inputs["Metallic"].default_value = 0
    if r["metal"]:
        L.new(mate("MULTIPLY", mate("SUBTRACT", 1, mate("MAXIMUM", barro, hollin)), r["metal"], True), p.inputs["Metallic"])
    p.inputs["Sheen Weight"].default_value = r["sheen"]
    p.inputs["Sheen Roughness"].default_value = .45
    p.inputs["Specular IOR Level"].default_value = r["espec"] if not r["metal"] else .5

    # relieve: pliegues del juego, hilo y costra de barro
    nm = nodo("ShaderNodeNormalMap", uv_map="UVMap")
    L.new(juego("_normal").outputs[0], nm.inputs["Color"])
    nm.inputs["Strength"].default_value = r["normal"]
    bp = nodo("ShaderNodeBump")
    bp.inputs["Distance"].default_value = .0012
    bp.inputs["Strength"].default_value = r["relieve"]
    L.new(mate("ADD", alto, mate("MULTIPLY", barro, mate("ADD", .6, mate("MULTIPLY", ruid(500, 2), .5)))), bp.inputs["Height"])
    L.new(nm.outputs[0], bp.inputs["Normal"])
    if r["falloff"]:
        if "Poliigon_Fabric_Falloff" not in bpy.data.node_groups:
            with bpy.data.libraries.load(POLIIGON) as (ori, des):
                des.node_groups = ["Poliigon_Fabric_Falloff"]
        g = nodo("ShaderNodeGroup")
        g.node_tree = bpy.data.node_groups["Poliigon_Fabric_Falloff"]
        # poco: con el valor del grupo el rojo de la casaca se lava a gris
        g.inputs["Falloff"].default_value = .12
        L.new(p.inputs["Base Color"].links[0].from_socket, g.inputs["Base Color"])
        L.new(rug, g.inputs["Roughness"])
        L.new(bp.outputs[0], g.inputs["Normal"])
        L.new(g.outputs["Base Color"], p.inputs["Base Color"])
        L.new(g.outputs["Roughness"], p.inputs["Roughness"])
        L.new(g.outputs["Normal"], p.inputs["Normal"])
    else:
        L.new(bp.outputs[0], p.inputs["Normal"])
    # el recorte del juego (barbas de pluma) se conserva; los rotos solo restan
    alfa = juego("_difusa").outputs["Alpha"]
    if r["rotos"]:
        roto = mate("MULTIPLY", rango(mate("ADD", ruid(70, 3), mate("MULTIPLY", roce, .08)), .77, .79), r["rotos"] * 2, True)
        alfa = mate("MULTIPLY", alfa, mate("SUBTRACT", 1, mate("MULTIPLY", roto, vis), True))
    L.new(alfa, p.inputs["Alpha"])
    return m


def foto_cine(ruta, objs):
    sc = bpy.context.scene
    r, cy = sc.render, sc.cycles
    r.engine = "CYCLES"
    cy.device, cy.samples, cy.use_denoising = "GPU", 24, True
    r.resolution_x, r.resolution_y = 640, 500
    r.film_transparent = False
    r.image_settings.file_format = "PNG"
    sc.view_settings.view_transform, sc.view_settings.look = "AgX", "None"
    r.filepath = ruta
    w = bpy.data.worlds.new("_f")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (.3, .34, .4, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = .7
    sc.world = w
    extras = []
    for nom, ener, rot, col in (("_sol", 3.2, (58, 0, -35), (1, .93, .82)), ("_con", 1.4, (70, 0, 150), (.75, .85, 1))):
        s = bpy.data.objects.new(nom, bpy.data.lights.new(nom, "SUN"))
        s.data.energy, s.data.color, s.data.angle = ener, col, math.radians(6)
        s.rotation_euler = [math.radians(a) for a in rot]
        sc.collection.objects.link(s)
        extras.append(s)
    bpy.context.view_layer.update()
    esq = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    bajo = Vector(min(p[i] for p in esq) for i in range(3))
    alto = Vector(max(p[i] for p in esq) for i in range(3))
    centro, med = (bajo + alto) / 2, alto - bajo
    dist = max(med.z * 2.25, max(med.x, med.y) * 1.75, .08)
    cam = bpy.data.objects.new("_cam", bpy.data.cameras.new("_cam"))
    sc.collection.objects.link(cam)
    extras.append(cam)
    sc.camera = cam
    cam.data.lens, cam.data.clip_start = 50, .001
    cam.location = centro + Vector((dist * .25, -dist, dist * .08))
    cam.rotation_euler = (centro - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.render.render(write_still=True)
    datos = [o.data for o in extras]
    for o in extras:
        bpy.data.objects.remove(o)
    for d in datos:
        (bpy.data.cameras if isinstance(d, bpy.types.Camera) else bpy.data.lights).remove(d)
    sc.camera, sc.world = None, None
    bpy.data.worlds.remove(w)
    r.engine = "BLENDER_EEVEE"


def tratar(rel, rec, arbol, imgs_loseta):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(ENTRADA, *rel.split("/")))
    mallas = [o for o in bpy.data.objects if o.type == "MESH"]
    for o in mallas:
        # en mallas de pocas caras, Cycles dibuja sombras en punta sin este ajuste
        o.cycles.shadow_terminator_offset = .3
        o.cycles.shadow_terminator_geometry_offset = .6
    if rec == "anillo":
        info = texturizar({**CINTA_MEDIA, "objeto": mallas[0].name})
        vis = 1.0
    else:
        im = imagen("cine_" + RECETAS[rec]["loseta"], imgs_loseta[RECETAS[rec]["loseta"]], True)
        hechos, vis_t = {}, []
        for o in mallas:
            limpiar_normales(o.data)
            vis_t.append(visibilidad(o, arbol))
            base = o.data.materials[0].name
            hechos.setdefault(base, material_cine(base, rec, im))
            o.data.materials[0] = hechos[base]
        vis = float(np.mean(vis_t))
    salida = os.path.join(SALIDA, *rel.split("/"))
    if len(salida) >= LIMITE_RUTA:
        raise RuntimeError(f"Ruta de {len(salida)} caracteres: usa una carpeta de salida mas corta. {salida}")
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    foto_cine(os.path.join(os.path.dirname(salida), "vista.png"), mallas)
    for x in [i for i in bpy.data.images if i.name == "Render Result"]:
        bpy.data.images.remove(x)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    for i in bpy.data.images:
        if not i.packed_file and i.has_data:
            i.pack()
    bpy.ops.wm.save_as_mainfile(filepath=salida, compress=True, check_existing=False)
    return vis, os.path.getsize(salida)


hojas = []
for raiz, dirs, files in os.walk(ENTRADA):
    dirs.sort()
    nombre = os.path.basename(raiz) + ".blend"
    if nombre in files and "detalles" not in dirs:
        hojas.append(os.path.relpath(os.path.join(raiz, nombre), ENTRADA).replace(os.sep, "/"))
if FILTRO:
    hojas = [h for h in hojas if any(t in h for t in FILTRO)]
arbol = arbol_personaje()
imgs = losetas()
t0 = time.time()
total_bytes = sin_receta = 0
for n, rel in enumerate(hojas, 1):
    rec = receta_de(rel)
    if rec is None:
        sin_receta += 1
        print("SIN_RECETA", rel, flush=True)
        continue
    t = time.time()
    vis, b = tratar(rel, rec, arbol, imgs)
    total_bytes += b
    print(f"CINE {n}/{len(hojas)} {rel} receta={rec} visible={vis:.0%} {b // 1024 // 1024}MB {time.time() - t:.1f}s", flush=True)
print(f"TOTAL hojas={len(hojas)} sin_receta={sin_receta} {total_bytes // 1024 // 1024}MB {time.time() - t0:.0f}s", flush=True)
print("FIN", flush=True)
