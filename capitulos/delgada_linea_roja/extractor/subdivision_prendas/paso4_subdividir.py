"""Paso 4 del flujo: subdivide un personaje en prendas, detalles y piezas, con un .blend y una foto por cada una. El original no se guarda.

blender -b personaje.blend --factory-startup --python paso4_subdividir.py -- personajes/config.py [carpeta_salida] [etapas]
Etapas (coma): prendas,detalles,piezas,trozos,pintadas; por defecto todas, en ese orden, porque cada una lee lo que dejo la anterior.
Salida por defecto: <carpeta del personaje>/prendas. La configuracion de cada personaje dice como se reparte; ver LEEME.md.
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

ARGS = sys.argv[sys.argv.index("--") + 1:]
bpy.context.preferences.filepaths.save_version = 0  # regenerar no deja copias .blend1
ORIGEN = bpy.data.filepath
SALIDA = os.path.abspath(ARGS[1]) if len(ARGS) > 1 and ARGS[1] else os.path.join(os.path.dirname(ORIGEN), "prendas")
ETAPAS = ARGS[2].split(",") if len(ARGS) > 2 else ["prendas", "detalles", "piezas", "trozos", "pintadas"]
LIMITE_RUTA = 255  # Windows no abre mas de 260, y Blender guarda antes en <ruta>@

exec(compile(open(ARGS[0], encoding="utf-8").read(), ARGS[0], "exec"))


def cortar(o, zona, prenda):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    uvl = bm.loops.layers.uv.active
    fuera = [f for f in bm.faces if zona([l[uvl].uv[0] for l in f.loops], [l[uvl].uv[1] for l in f.loops], [v.co.z for v in f.verts]) != prenda]
    bmesh.ops.delete(bm, geom=fuera, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context="EDGES")
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    o.name = o.data.name = prenda


def foto(ruta, objs):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 900, 700
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
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
    bpy.context.view_layer.update()
    esq = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    bajo = Vector(min(p[i] for p in esq) for i in range(3))
    alto = Vector(max(p[i] for p in esq) for i in range(3))
    centro, med = (bajo + alto) / 2, alto - bajo
    dist = max(med.z * 2.25, max(med.x, med.y) * 1.75, .08)
    cam = bpy.data.objects.new("cam_foto", bpy.data.cameras.new("cam_foto"))
    sc.collection.objects.link(cam)
    extras.append(cam)
    sc.camera = cam
    cam.data.lens = 50
    cam.data.clip_start = .001
    cam.location = centro + Vector((dist * .25, -dist, dist * .08))
    cam.rotation_euler = (centro - cam.location).to_track_quat("-Z", "Y").to_euler()
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


def separar(prenda):
    enteras, corte, prefijos = PRENDAS[prenda]
    bpy.ops.wm.open_mainfile(filepath=ORIGEN)
    sc = bpy.context.scene
    sc.world = None
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    if corte:
        if corte[0] not in bpy.data.objects:
            print("AVISO: no existe la malla", corte[0], "para", prenda, flush=True)
            return
        cortar(bpy.data.objects[corte[0]], corte[1], prenda)
    quedan = [o for o in bpy.data.objects if o.type == "MESH" and (o.name == prenda or o.name in enteras or o.name.startswith(prefijos or ("\0",)))]
    for o in [o for o in bpy.data.objects if o.type == "MESH" and o not in quedan]:
        bpy.data.objects.remove(o)
    guardar(prenda, arm, quedan, os.path.join(SALIDA, prenda))


def guardar(nombre, arm, quedan, d, archivo=None):
    sc = bpy.context.scene
    ruta = os.path.join(d, (archivo or nombre) + ".blend")
    if len(ruta) >= LIMITE_RUTA:
        raise RuntimeError(f"Ruta de {len(ruta)} caracteres, Windows no la abriria: usa una carpeta_salida mas corta o nombres mas cortos. {ruta}")
    quedan = [o for o in quedan if o.data.polygons]
    if not quedan:
        print("AVISO: sin caras, no se guarda", ruta, flush=True)
        return
    raiz = bpy.data.collections.new(nombre)
    sc.collection.children.link(raiz)
    for o in [arm] + quedan:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        raiz.objects.link(o)
    for c in [c for c in bpy.data.collections if c is not raiz]:
        bpy.data.collections.remove(c)
    raiz.asset_mark()
    os.makedirs(d, exist_ok=True)
    foto(os.path.join(d, "vista.png"), quedan)
    for im in [i for i in bpy.data.images if i.name == "Render Result"]:
        bpy.data.images.remove(im)
    for o in [o for o in bpy.data.objects if o.type == "MESH" and o not in quedan]:
        bpy.data.objects.remove(o)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    bpy.ops.wm.save_as_mainfile(filepath=ruta, compress=True, check_existing=False)
    print("GUARDADO", os.path.relpath(ruta, SALIDA), len(quedan), "mallas", sum(len(o.data.polygons) for o in quedan), "caras", os.path.getsize(ruta) // 1024 // 1024, "MB", flush=True)


def cortar_piezas(o, zona, detalle):
    """Cada pieza conectada de la malla va entera a una zona, segun donde cae en la textura y en el cuerpo."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    uvl = bm.loops.layers.uv.active
    vistos, fuera = set(), []
    for v0 in bm.verts:
        if v0 in vistos:
            continue
        vistos.add(v0)
        pila, comp = [v0], []
        while pila:
            v = pila.pop()
            comp.append(v)
            for e in v.link_edges:
                w = e.other_vert(v)
                if w not in vistos:
                    vistos.add(w)
                    pila.append(w)
        uv = [l[uvl].uv for v in comp for l in v.link_loops]
        if zona(min(c[0] for c in uv), max(c[0] for c in uv), min(c[1] for c in uv), max(c[1] for c in uv),
                max(v.co.y for v in comp), max(v.co.z for v in comp)) != detalle:
            fuera += comp
    bmesh.ops.delete(bm, geom=fuera, context="VERTS")
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    o.name = o.data.name = detalle


def detallar(prenda, detalle, regla):
    d = os.path.join(SALIDA, prenda)
    if not os.path.exists(os.path.join(d, prenda + ".blend")):
        return
    bpy.ops.wm.open_mainfile(filepath=os.path.join(d, prenda + ".blend"))
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    if isinstance(regla, tuple):
        cortar_piezas(bpy.data.objects[regla[0]], regla[1], detalle)
        quedan = [bpy.data.objects[detalle]]
    else:
        quedan = [o for o in bpy.data.objects if o.type == "MESH" and regla in o.name]
    for o in [o for o in bpy.data.objects if o.type == "MESH" and o not in quedan]:
        bpy.data.objects.remove(o)
    guardar(detalle, arm, quedan, os.path.join(d, "detalles", detalle))


def piezas(prenda, detalle):
    """Si el detalle tiene varios objetos sueltos, cada uno va a <detalle>/detalles/<pieza>/<pieza>.blend."""
    d = os.path.join(SALIDA, prenda, "detalles", detalle)
    ruta = os.path.join(d, detalle + ".blend")
    bpy.ops.wm.open_mainfile(filepath=ruta)
    nombres = [o.name for o in bpy.data.objects if o.type == "MESH"]
    if len(nombres) < 2:
        return
    for nom in nombres:
        bpy.ops.wm.open_mainfile(filepath=ruta)
        arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
        o = bpy.data.objects[nom]
        for x in [x for x in bpy.data.objects if x.type == "MESH" and x is not o]:
            bpy.data.objects.remove(x)
        pieza = nom.split("_", 2)[2] if nom.startswith("det_") else nom  # det_torsos_boton_001 -> boton_001
        guardar(pieza, arm, [o], os.path.join(d, "detalles", pieza))


def grupos_de(o, base):
    """{nombre de pieza: indices de vertices}. D es x > 0, como en las hombreras; lo de menos de 3 caras va junto en remates."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    vistos, filas, resto = set(), [], []
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
        if len(caras) < 3:
            resto += [v.index for v in comp]
        else:
            c = sum((v.co for v in comp), Vector()) / len(comp)
            filas.append((c.x, c.y, c.z, [v.index for v in comp]))
    bm.free()
    grupos, cuenta = {}, {}
    con_lado = base[:2] in ("D_", "I_")
    for x, y, z, idx in sorted(filas, key=lambda f: (f[0] <= 0, -round(f[2], 3), f[1])):
        lado = "" if con_lado else ("D_" if x > 0 else "I_")
        cuenta[lado] = cuenta.get(lado, 0) + 1
        grupos[f"{base}_{lado}{cuenta[lado]:02d}"] = idx
    if resto:
        grupos[base + "_remates"] = resto
    return grupos


def trozos(rel):
    d = os.path.join(SALIDA, *rel.split("/"))
    base = os.path.basename(d)
    ruta = os.path.join(d, base + ".blend")
    if not os.path.exists(ruta):
        print("AVISO: no existe", rel, flush=True)
        return
    bpy.ops.wm.open_mainfile(filepath=ruta)
    nom = next(o.name for o in bpy.data.objects if o.type == "MESH")
    grupos = grupos_de(bpy.data.objects[nom], base)
    if len(grupos) < 2:
        return
    for pieza, idx in grupos.items():
        bpy.ops.wm.open_mainfile(filepath=ruta)
        arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
        o = bpy.data.objects[nom]
        dentro = set(idx)
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in dentro], context="VERTS")
        bm.to_mesh(o.data)
        bm.free()
        o.data.update()
        o.name = o.data.name = pieza
        guardar(pieza, arm, [o], os.path.join(d, "detalles", pieza))


def campos(mat, zonas):
    """Lista de (nombre, campo 0-1) de cada zona, con la textura de arriba abajo; el ultimo nombre es lo que sobra."""
    im = bpy.data.images[mat + "_difusa"]
    w, h = im.size
    px = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(px)
    t = px.reshape(h, w, 4)[::-1]
    y, x = np.mgrid[0:h, 0:w]
    r, g, b = t[..., 0], t[..., 1], t[..., 2]
    z, resto = zonas(x, y, r, g, b, t[..., :3].mean(axis=2))
    salida = []
    for nom, m in z:
        f = m.astype(np.float32)
        # un pixel de suavizado: el corte sigue el contorno y no la escalera de pixeles
        for eje in (0, 1):
            f = (np.roll(f, 1, eje) + f + np.roll(f, -1, eje)) / 3
        salida.append((nom, f))
    return salida, resto


def muestrear(f, uv):
    h, w = f.shape
    x = np.clip(uv[..., 0] * w - .5, 0, w - 1.001)
    y = np.clip((1 - uv[..., 1]) * h - .5, 0, h - 1.001)
    x0, y0 = x.astype(int), y.astype(int)
    a, c = x - x0, y - y0
    return (f[y0, x0] * (1 - a) + f[y0, x0 + 1] * a) * (1 - c) + (f[y0 + 1, x0] * (1 - a) + f[y0 + 1, x0 + 1] * a) * c


def rejilla(n):
    """Triangulos pequenos de un triangulo partido en n por lado, en baricentricas: (m, 3, 3)."""
    ij = {}
    pts = []
    for i in range(n + 1):
        for j in range(n + 1 - i):
            ij[(i, j)] = len(pts)
            pts.append((i / n, j / n, (n - i - j) / n))
    tris = []
    for i in range(n):
        for j in range(n - i):
            tris.append((ij[(i, j)], ij[(i + 1, j)], ij[(i, j + 1)]))
            if i + j < n - 1:
                tris.append((ij[(i + 1, j)], ij[(i + 1, j + 1)], ij[(i, j + 1)]))
    return np.array(pts, np.float32)[np.array(tris)]


def recortar(ids, bar, val):
    """Parte los triangulos por val = 0 y devuelve (ids, bar) de dentro (val > 0) y de fuera."""
    dentro_v = val > 0
    n = dentro_v.sum(axis=1)
    di, db, fi, fb = [ids[n == 3]], [bar[n == 3]], [ids[n == 0]], [bar[n == 0]]
    extra = {True: ([], []), False: ([], [])}
    for t in np.nonzero((n > 0) & (n < 3))[0]:
        pol = {True: [], False: []}
        for a in range(3):
            c = (a + 1) % 3
            pol[bool(dentro_v[t, a])].append(bar[t, a])
            if dentro_v[t, a] != dentro_v[t, c]:
                s = val[t, a] / (val[t, a] - val[t, c])
                q = bar[t, a] + (bar[t, c] - bar[t, a]) * s
                pol[True].append(q)
                pol[False].append(q)
        for lado, puntos in pol.items():
            for k in range(1, len(puntos) - 1):
                extra[lado][0].append(ids[t])
                extra[lado][1].append((puntos[0], puntos[k], puntos[k + 1]))
    for lado, (li, lb), (si, sb) in ((True, (di, db), extra[True]), (False, (fi, fb), extra[False])):
        if si:
            li.append(np.array(si))
            lb.append(np.array(sb, np.float32))
    return np.concatenate(di), np.concatenate(db), np.concatenate(fi), np.concatenate(fb)


def malla_cortada(o, nombre, ids, bar, tri_v, tri_l, pos, uv, nor, pesos):
    """Malla nueva con los triangulos recortados; vertices unidos por posicion y uv, caras planas disueltas."""
    v3 = tri_v[ids]
    p = bar @ pos[v3]
    l3 = tri_l[ids]
    t = bar @ uv[l3]
    nn = bar @ nor[l3]
    w = bar @ pesos[v3]
    llave = np.round(p.reshape(-1, 3), 5)
    unicos, inv = np.unique(llave, axis=0, return_inverse=True)
    inv = inv.reshape(-1)
    caras = inv.reshape(-1, 3)
    bien = (caras[:, 0] != caras[:, 1]) & (caras[:, 1] != caras[:, 2]) & (caras[:, 0] != caras[:, 2])
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(unicos.tolist(), [], caras[bien].tolist())
    me.materials.append(o.data.materials[0])
    capa = me.uv_layers.new(name=o.data.uv_layers.active.name)
    capa.data.foreach_set("uv", t[bien].reshape(-1))
    # pesos y normales por vertice (la media de sus esquinas)
    pv = np.zeros((len(unicos), pesos.shape[1]), np.float32)
    nv = np.zeros((len(unicos), 3), np.float32)
    np.add.at(pv, inv, w.reshape(-1, pesos.shape[1]))
    np.add.at(nv, inv, nn.reshape(-1, 3))
    pv /= np.maximum(np.bincount(inv, minlength=len(unicos))[:, None], 1)
    viejo = o.data
    # los nombres de los grupos viven en la malla: hay que crearlos otra vez, en el mismo orden
    grupos = [g.name for g in o.vertex_groups]
    o.data = me
    for nom in grupos:
        g = o.vertex_groups.new(name=nom)
        col = pv[:, g.index]
        for i in np.nonzero(col > .001)[0]:
            g.add([int(i)], float(col[i]), "REPLACE")
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.dissolve_limit(bm, angle_limit=.002, use_dissolve_boundaries=False, verts=bm.verts[:], edges=bm.edges[:], delimit={"UV"})
    bm.to_mesh(me)
    bm.free()
    llaves = {tuple(c): i for i, c in enumerate(np.rint(unicos * 1e5).astype(np.int64).tolist())}
    largo = np.maximum(np.linalg.norm(nv, axis=1, keepdims=True), 1e-6)
    nv = nv / largo
    me.normals_split_custom_set([nv[llaves[tuple(int(round(x * 1e5)) for x in me.vertices[lo.vertex_index].co)]].tolist() for lo in me.loops])
    bpy.data.meshes.remove(viejo)
    o.name = me.name = nombre


def datos_malla(o):
    me = o.data
    me.calc_loop_triangles()
    nv = len(me.vertices)
    pos = np.empty(nv * 3, np.float32)
    me.vertices.foreach_get("co", pos)
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers.active.data.foreach_get("uv", uv)
    nor = np.empty(len(me.loops) * 3, np.float32)
    me.corner_normals.foreach_get("vector", nor)
    tri_v = np.empty(len(me.loop_triangles) * 3, np.int32)
    me.loop_triangles.foreach_get("vertices", tri_v)
    tri_l = np.empty(len(me.loop_triangles) * 3, np.int32)
    me.loop_triangles.foreach_get("loops", tri_l)
    pesos = np.zeros((nv, len(o.vertex_groups)), np.float32)
    for v in me.vertices:
        for g in v.groups:
            pesos[v.index, g.group] = g.weight
    return pos.reshape(-1, 3), uv.reshape(-1, 2), nor.reshape(-1, 3), tri_v.reshape(-1, 3), tri_l.reshape(-1, 3), pesos


def cortes(o, zonas):
    """{nombre de zona: (ids de triangulo, baricentricas)} de la malla, partida a menos de 2 pixeles de textura."""
    pos, uv, nor, tri_v, tri_l, pesos = datos_malla(o)
    fs, resto = campos(o.material_slots[0].material.name, zonas)
    h, w = fs[0][1].shape
    aux_i, aux_b = [], []
    for t, ls in enumerate(tri_l):
        q = uv[ls] * (w, h)
        lado = max(np.linalg.norm(q[0] - q[1]), np.linalg.norm(q[1] - q[2]), np.linalg.norm(q[2] - q[0]))
        g = rejilla(max(1, int(math.ceil(lado / 2))))
        aux_i.append(np.full(len(g), t))
        aux_b.append(g)
    ids, bar = np.concatenate(aux_i), np.concatenate(aux_b)
    trozos_z = {}
    for nom, f in fs:
        di, db, ids, bar = recortar(ids, bar, muestrear(f, bar @ uv[tri_l[ids]]) - .5)
        if len(di):
            trozos_z[nom] = (di, db)
    if len(ids):
        trozos_z[resto] = (ids, bar)
    return trozos_z, (pos, uv, nor, tri_v, tri_l, pesos)


def pintadas(rel, zonas):
    d = os.path.join(SALIDA, *rel.split("/"))
    base = os.path.basename(d)
    ruta = os.path.join(d, base + ".blend")
    if not os.path.exists(ruta):
        print("AVISO: no existe", rel, flush=True)
        return
    bpy.ops.wm.open_mainfile(filepath=ruta)
    o = next(x for x in bpy.data.objects if x.type == "MESH")
    nom_o = o.name
    z, datos = cortes(o, zonas)
    pos, uv, nor, tri_v, tri_l, pesos = datos
    for nom, (ids, bar) in z.items():
        bpy.ops.wm.open_mainfile(filepath=ruta)
        arm = next(x for x in bpy.data.objects if x.type == "ARMATURE")
        o = bpy.data.objects[nom_o]
        pieza = f"{base}_{nom}"
        malla_cortada(o, pieza, ids, bar, tri_v, tri_l, pos, uv, nor, pesos)
        # carpeta y archivo con el nombre corto: con el completo se pasa del limite de ruta de Windows
        guardar(pieza, arm, [o], os.path.join(d, "detalles", nom), nom)


if "prendas" in ETAPAS:
    for p in PRENDAS:
        separar(p)
if "detalles" in ETAPAS:
    for p, detalles in DETALLES.items():
        for det, regla in detalles.items():
            detallar(p, det, regla)
if "piezas" in ETAPAS:
    for p, detalles in DETALLES.items():
        for det in detalles:
            if os.path.exists(os.path.join(SALIDA, p, "detalles", det, det + ".blend")):
                piezas(p, det)
if "trozos" in ETAPAS:
    for rel in CON_TROZOS:
        trozos(rel)
if "pintadas" in ETAPAS:
    for rel, zonas in PINTADAS.items():
        pintadas(rel, zonas)
print("FIN", flush=True)
