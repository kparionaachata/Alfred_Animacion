# -*- coding: utf-8 -*-
"""alfred_cueva_5C.blend: ruta caminable de the_stalker_1 hasta el pico (alfred_pico_piedra) sin atravesar la caverna.
A* sobre una rejilla (CELDA m): cada paso se acepta si el suelo (rayo hacia abajo sobre objetos caverna_*) no es lava, sube/baja poco (SUBE/BAJA), hay altura libre (ALTO)
y los rayos horizontales a la altura de las piernas y del pecho (con radio RADIO) no chocan con la caverna. Se puede reanudar (LIMITE s por llamada).
Uso: exec(...); r = buscar_ruta()   -> {'listo': bool, ...}; al terminar guarda la ruta en ruta_stalker_pico.json
"""
import bpy, math, heapq, time, json
from mathutils import Vector

JSON = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ruta_stalker_pico.json"
CELDA = 0.75
SUBE, BAJA = 1.1, 3.0
ALTO = 2.0
RADIO = 0.3
ANCHO = 0.9            # holgura lateral para brazos y manos colgando (la criatura es ancha): rayos a cada lado a 0.45/0.9/1.4 m sobre el suelo
LIMITE = 40.0
PICO = (2.4, 78.4)
INICIO = (41.75, -28.35)
NS = bpy.app.driver_namespace


def _bvh(dg):
    """BVH propio (mundo) de las mallas caverna_*; el agua/lava aparte para no pisarla"""
    from mathutils.bvhtree import BVHTree
    if "ruta_bvh" in NS:
        return NS["ruta_bvh"]
    res = []
    for lava in (False, True):
        vs, ps = [], []
        for o in bpy.data.objects:
            if o.type != 'MESH' or not o.name.startswith("caverna_") or (("lava" in o.name) != lava) or o.name.startswith("caverna_luz"):
                continue
            oe = o.evaluated_get(dg)
            me = oe.to_mesh()
            n0 = len(vs)
            vs += [oe.matrix_world @ v.co for v in me.vertices]
            ps += [tuple(n0 + i for i in p.vertices) for p in me.polygons]
            oe.to_mesh_clear()
        res.append(BVHTree.FromPolygons(vs, ps) if ps else None)
    NS["ruta_bvh"] = res
    return res


def _golpe(sc, dg, o, d, dist):
    """primer choque con la caverna (sin lava) o con la lava: (punto, es_lava) o None"""
    b, bl = _bvh(dg)
    r = b.ray_cast(Vector(o), d, dist) if b else (None,)
    rl = bl.ray_cast(Vector(o), d, dist) if bl else (None,)
    if r[0] is None and rl[0] is None:
        return None
    if r[0] is None or (rl[0] is not None and rl[3] < r[3]):
        return (rl[0], True)
    return (r[0], False)


def _suelo(sc, dg, x, y, zref):
    r = _golpe(sc, dg, (x, y, zref + SUBE + 0.2), Vector((0, 0, -1)), SUBE + 0.2 + BAJA)
    if not r or r[1]:
        return None
    return r[0].z


def _libre(sc, dg, a, b):
    """paso de a=(x,y,z) a b=(x,y,z) sin chocar: altura libre en b y rayos horizontales con holgura lateral"""
    r = _golpe(sc, dg, (b[0], b[1], b[2] + 0.05), Vector((0, 0, 1)), ALTO)
    if r and not r[1]:
        return False
    v = Vector((b[0] - a[0], b[1] - a[1], 0))
    L = v.length
    d = v / L
    lat = Vector((-d.y, d.x, 0))
    zz = max(a[2], b[2])
    for h in (0.45, 1.1, 1.8):
        for off in (0.0, RADIO, -RADIO):
            o = (a[0] + lat.x * off, a[1] + lat.y * off, zz + h)
            r = _golpe(sc, dg, o, d, L + RADIO)
            if r and not r[1]:
                return False
    for h in (0.45, 0.9, 1.4):
        for sg in (1, -1):
            r = _golpe(sc, dg, (b[0], b[1], b[2] + h), lat * sg, ANCHO)
            if r and not r[1]:
                return False
    return True


def buscar_ruta():
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    z0 = bpy.data.objects["the_stalker_1"].matrix_world.translation.z
    if "ruta_estado" not in NS:
        k0 = (0, 0)
        NS["ruta_estado"] = {"g": {k0: 0.0}, "z": {k0: z0}, "padre": {}, "abierta": [(0.0, k0)], "cerrada": set(), "n": 0}
    E = NS["ruta_estado"]
    k_obj = (round((PICO[0] - INICIO[0]) / CELDA), round((PICO[1] - INICIO[1]) / CELDA))

    def pos(k):
        return (INICIO[0] + k[0] * CELDA, INICIO[1] + k[1] * CELDA)

    def h(k):
        return CELDA * math.hypot(k[0] - k_obj[0], k[1] - k_obj[1])
    t0 = time.time()
    vec = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    fin = None
    while E["abierta"] and time.time() - t0 < LIMITE:
        f, k = heapq.heappop(E["abierta"])
        if k in E["cerrada"]:
            continue
        E["cerrada"].add(k)
        E["n"] += 1
        if math.hypot(k[0] - k_obj[0], k[1] - k_obj[1]) <= 2:
            fin = k
            break
        a = pos(k) + (E["z"][k],)
        for dx, dy in vec:
            nk = (k[0] + dx, k[1] + dy)
            if nk in E["cerrada"]:
                continue
            px, py = pos(nk)
            z = _suelo(sc, dg, px, py, a[2])
            if z is None or z - a[2] > SUBE or a[2] - z > BAJA:
                continue
            if not _libre(sc, dg, a, (px, py, z)):
                continue
            c = E["g"][k] + CELDA * math.hypot(dx, dy) * (1.0 + 0.6 * abs(z - a[2]))
            if c < E["g"].get(nk, 1e18):
                E["g"][nk], E["z"][nk], E["padre"][nk] = c, z, k
                heapq.heappush(E["abierta"], (c + 1.4 * h(nk), nk))
    if fin is None:
        return {"listo": False, "expandidos": E["n"], "abierta": len(E["abierta"]), "mejor_h": round(min((h(k) for k in E["cerrada"]), default=0), 1)}
    ruta, k = [], fin
    while True:
        x, y = pos(k)
        ruta.append((x, y, E["z"][k]))
        if k not in E["padre"]:
            break
        k = E["padre"][k]
    ruta.reverse()
    json.dump(ruta, open(JSON, "w"))
    del NS["ruta_estado"]
    L = sum(math.dist(ruta[i][:2], ruta[i + 1][:2]) for i in range(len(ruta) - 1))
    return {"listo": True, "puntos": len(ruta), "longitud_m": round(L, 1), "expandidos": E["n"]}
