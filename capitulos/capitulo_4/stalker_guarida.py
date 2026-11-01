# -*- coding: utf-8 -*-
"""alfred_cueva_5B.blend: la guarida de the_stalker_1 (alrededor de donde esta al comenzar, f1-546, y de los primeros metros de su camino): herramientas de Minecraft tiradas en el suelo
(espadas, hachas, picos, palas, arco, palo; modelos voxel hechos pixel a pixel con las texturas de item del paquete kebyn) y extremidades de otras victimas (brazos, piernas, cabezas,
torsos con la herida abierta, de varios jugadores distintos) con charcos de sangre.
Todo en la coleccion `guarida_stalker`, un solo material con color por vertice (atributo `Col`). Zombie convertido en "jugador": ver imagen jugador_victima.png (material Skin.018).
Uso en Blender: exec(open(ruta, encoding="utf8").read()); construir_guarida()     (repetible)
"""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler

ITEMS = "C:/Users/user/Desktop/Alfred_Animacion/kebyn proyecto  1.20.1_analysis/kebyn proyecto  1.20.1/assets/minecraft/textures/item/"
HERRAMIENTAS = ["iron_sword", "diamond_sword", "stone_sword", "wooden_sword", "iron_axe", "diamond_axe", "golden_axe", "iron_pickaxe", "diamond_pickaxe", "golden_pickaxe",
                "iron_shovel", "stone_shovel", "bow", "stick", "netherite_sword", "wooden_axe"]
# (piel, camiseta, pantalon, pelo): una por victima
VICTIMAS = [((0.91, 0.71, 0.55), (0.20, 0.45, 0.80), (0.20, 0.20, 0.55), (0.25, 0.15, 0.08)),
            ((0.80, 0.56, 0.40), (0.25, 0.65, 0.30), (0.30, 0.25, 0.20), (0.10, 0.08, 0.06)),
            ((0.95, 0.80, 0.65), (0.90, 0.75, 0.15), (0.25, 0.28, 0.35), (0.55, 0.40, 0.10)),
            ((0.60, 0.42, 0.30), (0.55, 0.20, 0.60), (0.15, 0.15, 0.18), (0.05, 0.05, 0.05)),
            ((0.88, 0.66, 0.50), (0.85, 0.85, 0.85), (0.35, 0.22, 0.12), (0.45, 0.25, 0.10))]
SANGRE = (0.30, 0.01, 0.01)
CENTRO = Vector((42.45, -53.16, 6.02))


def _lin(c):
    return (c[0] ** 2.2, c[1] ** 2.2, c[2] ** 2.2, 1.0)


def _caja(bm, lay, centro, tam, color, rot=None):
    m = Matrix.Translation(centro) @ (rot.to_matrix().to_4x4() if rot else Matrix.Identity(4))
    n = len(bm.verts)
    res = bmesh.ops.create_cube(bm, size=1.0, matrix=m @ Matrix.Diagonal((tam[0], tam[1], tam[2], 1.0)))
    for f in {f for v in res["verts"] for f in v.link_faces}:
        for lp in f.loops:
            lp[lay] = _lin(color)


def _material():
    m = bpy.data.materials.get("guarida_vertex")
    if m is None:
        m = bpy.data.materials.new("guarida_vertex")
        m.use_nodes = True
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        at = nt.nodes.new("ShaderNodeAttribute")
        at.attribute_name = "Col"
        mx = nt.nodes.new("ShaderNodeMix")                 # todo muy oscuro alrededor de la criatura: el color por vertice se multiplica por 0.22
        mx.data_type = 'RGBA'
        mx.blend_type = 'MULTIPLY'
        mx.inputs["Factor"].default_value = 1.0
        mx.inputs["B"].default_value = (0.22, 0.22, 0.22, 1.0)
        nt.links.new(at.outputs["Color"], mx.inputs["A"])
        nt.links.new(mx.outputs["Result"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 1.0
    return m


def _objeto(nombre, bm, loc, rot, col, mat):
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(nombre, me)
    ob.location = loc
    ob.rotation_euler = rot
    col.objects.link(ob)
    return ob


def _bm():
    bm = bmesh.new()
    lay = bm.loops.layers.color.new("Col")
    return bm, lay


def _suelo(x, y):
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    pos = Vector((x, y, 20))
    for _ in range(8):
        r = sc.ray_cast(dg, pos, Vector((0, 0, -1)), distance=40)
        if not r[0]:
            return None
        if r[4].name.startswith("caverna_"):
            return r[1].z
        pos = r[1] - Vector((0, 0, 0.01))


def _herramienta(nombre, col, mat, loc, yaw):
    img = bpy.data.images.load(ITEMS + nombre + ".png", check_existing=True)
    W, H = img.size
    px = list(img.pixels)
    bm, lay = _bm()
    p, g = 0.05, 0.05
    for y in range(H):
        for x in range(W):
            i = (y * W + x) * 4
            if px[i + 3] > 0.5:
                _caja(bm, lay, Vector(((x - W / 2) * p, (y - H / 2) * p, 0)), (p, p, g), tuple(v ** (1 / 2.2) for v in px[i:i + 3]))
    ob = _objeto("guarida_" + nombre, bm, loc, Euler((0, 0, yaw)), col, mat)
    return ob


def _brazo(bm, lay, v):
    piel, cam, pan, pelo = v
    _caja(bm, lay, Vector((0, 0, 0.19)), (0.25, 0.25, 0.37), cam)
    _caja(bm, lay, Vector((0, 0, -0.19)), (0.25, 0.25, 0.38), piel)
    _caja(bm, lay, Vector((0, 0, 0.385)), (0.20, 0.20, 0.02), SANGRE)           # herida


def _pierna(bm, lay, v):
    piel, cam, pan, pelo = v
    _caja(bm, lay, Vector((0, 0, 0.1)), (0.25, 0.25, 0.55), pan)
    _caja(bm, lay, Vector((0, 0.02, -0.25)), (0.26, 0.27, 0.18), (0.35, 0.35, 0.38))
    _caja(bm, lay, Vector((0, 0, 0.385)), (0.20, 0.20, 0.02), SANGRE)


def _cabeza(bm, lay, v):
    piel, cam, pan, pelo = v
    _caja(bm, lay, Vector((0, 0, 0)), (0.5, 0.5, 0.5), piel)
    _caja(bm, lay, Vector((0, -0.03, 0.2)), (0.52, 0.56, 0.12), pelo)
    _caja(bm, lay, Vector((0, -0.27, 0.0)), (0.52, 0.06, 0.52), pelo) if False else None
    _caja(bm, lay, Vector((-0.12, 0.255, 0.03)), (0.1, 0.02, 0.07), (1, 1, 1))
    _caja(bm, lay, Vector((0.12, 0.255, 0.03)), (0.1, 0.02, 0.07), (1, 1, 1))
    _caja(bm, lay, Vector((-0.10, 0.265, 0.03)), (0.05, 0.02, 0.07), (0.15, 0.2, 0.55))
    _caja(bm, lay, Vector((0.10, 0.265, 0.03)), (0.05, 0.02, 0.07), (0.15, 0.2, 0.55))
    _caja(bm, lay, Vector((0, 0.255, -0.14)), (0.14, 0.02, 0.04), (0.5, 0.25, 0.22))
    _caja(bm, lay, Vector((0, 0, -0.26)), (0.34, 0.34, 0.03), SANGRE)


def _torso(bm, lay, v):
    piel, cam, pan, pelo = v
    _caja(bm, lay, Vector((0, 0, 0)), (0.5, 0.25, 0.75), cam)
    _caja(bm, lay, Vector((0, 0, 0.385)), (0.40, 0.18, 0.02), SANGRE)
    _caja(bm, lay, Vector((0, 0, -0.385)), (0.40, 0.18, 0.02), SANGRE)


def _charco(bm, lay, rnd):
    for _ in range(rnd.randint(4, 7)):
        _caja(bm, lay, Vector((rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), 0)), (rnd.uniform(0.4, 1.0), rnd.uniform(0.4, 1.0), 0.015), SANGRE)


def construir_guarida(semilla=11):
    sc = bpy.context.scene
    col = bpy.data.collections.get("guarida_stalker")
    if col is None:
        col = bpy.data.collections.new("guarida_stalker")
        sc.collection.children.link(col)
    for o in list(col.objects):
        me = o.data
        bpy.data.objects.remove(o)
        if me and me.users == 0:
            bpy.data.meshes.remove(me)
    mat = _material()
    rnd = random.Random(semilla)
    yaw0 = bpy.data.objects["the_stalker_1"].matrix_world.to_euler().z
    D = Vector((-math.sin(yaw0), math.cos(yaw0), 0))

    def punto(rmin, rmax):
        for _ in range(60):
            a = rnd.uniform(0, 2 * math.pi)
            d = rnd.uniform(rmin, rmax)
            p = CENTRO + Vector((math.cos(a) * d, math.sin(a) * d, 0))
            # lejos del cuerpo del Stalker; el camino hacia delante queda mas despejado
            rel = p - CENTRO
            if rel.dot(D) > 0 and abs(rel.cross(D).z) < 1.3 and rel.dot(D) < 18:
                continue
            z = _suelo(p.x, p.y)
            if z is not None and abs(z - CENTRO.z) < 1.2:
                return Vector((p.x, p.y, z))
        return None
    n = {"herramientas": 0, "extremidades": 0, "charcos": 0}
    for nombre in HERRAMIENTAS:
        p = punto(2.2, 9.5)
        if p is None:
            continue
        ob = _herramienta(nombre, col, mat, p + Vector((0, 0, 0.03)), rnd.uniform(0, 2 * math.pi))
        ob.rotation_euler = Euler((0, 0, rnd.uniform(0, 2 * math.pi)))
        n["herramientas"] += 1
    piezas = [("brazo", _brazo)] * 8 + [("pierna", _pierna)] * 6 + [("cabeza", _cabeza)] * 4 + [("torso", _torso)] * 4
    rnd.shuffle(piezas)
    for i, (nom, fn) in enumerate(piezas):
        p = punto(1.8, 9.0)
        if p is None:
            continue
        bm, lay = _bm()
        fn(bm, lay, VICTIMAS[i % len(VICTIMAS)])
        alto = {"brazo": 0.13, "pierna": 0.13, "cabeza": 0.27, "torso": 0.13}[nom]
        # tumbada: eje largo horizontal (rotacion X de 90) + giro libre
        rot = Euler((math.pi / 2 if nom != "cabeza" else rnd.uniform(0, math.pi), rnd.uniform(-0.2, 0.2), rnd.uniform(0, 2 * math.pi)))
        ob = _objeto("guarida_%s_%02d" % (nom, i), bm, p + Vector((0, 0, alto + 0.02)), rot, col, mat)
        n["extremidades"] += 1
        # charco debajo
        if rnd.random() < 0.7:
            bm2, lay2 = _bm()
            _charco(bm2, lay2, rnd)
            _objeto("guarida_charco_%02d" % i, bm2, p + Vector((0, 0, 0.005)), Euler((0, 0, rnd.uniform(0, 3))), col, mat)
            n["charcos"] += 1
    return n
