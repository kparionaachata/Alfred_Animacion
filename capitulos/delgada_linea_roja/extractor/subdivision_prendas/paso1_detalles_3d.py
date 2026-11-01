"""Convierte en mallas 3D independientes los detalles pintados en la textura de un personaje abierto en Blender.

Botones, cordones, ligas, hebillas... Cada detalle es un objeto en la coleccion detalles_3d, con la misma textura
y los mismos pesos que la ropa de debajo, asi que sigue al esqueleto. Se puede ejecutar varias veces: rehace la coleccion.
Uso (dentro de Blender):  exec(open(r"...\\detalles_3d.py", encoding="utf-8").read())
"""
import bmesh
import numpy as np

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform


def leer_imagen(nom):
    im = bpy.data.images[nom]
    w, h = im.size
    px = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(px)
    return px.reshape(h, w, 4)[::-1]  # fila 0 arriba


def crecer(m, n=1):
    m = m.copy()
    for _ in range(n):
        v = m.copy()
        v[1:] |= m[:-1]
        v[:-1] |= m[1:]
        v[:, 1:] |= m[:, :-1]
        v[:, :-1] |= m[:, 1:]
        m = v
    return m


def encoger(m, n=1):
    return ~crecer(~m, n)


def distancia(m, tope=12):
    """Pixeles hasta el borde del detalle (1 = borde)."""
    d = np.zeros(m.shape, np.int32)
    a = m.copy()
    for i in range(1, tope + 1):
        d[a] = i
        a = encoger(a)
        if not a.any():
            break
    return d


def componentes(m, minimo):
    """Listas de filas y columnas de cada zona conectada de la mascara."""
    vis = np.zeros(m.shape, bool)
    h, w = m.shape
    res = []
    for r0, c0 in zip(*np.nonzero(m)):
        if vis[r0, c0]:
            continue
        pila, zona = [(int(r0), int(c0))], []
        vis[r0, c0] = True
        while pila:
            r, c = pila.pop()
            zona.append((r, c))
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    a, b = r + dr, c + dc
                    if 0 <= a < h and 0 <= b < w and m[a, b] and not vis[a, b]:
                        vis[a, b] = True
                        pila.append((a, b))
        if len(zona) >= minimo:
            res.append(np.array(zona))
    return res


def mascaras(nombre):
    """Tipos de detalle de cada material: {tipo: (mascara, alto en metros, ancho del redondeo en pixeles, area minima)}."""
    d = leer_imagen(nombre + "_difusa")[..., :3]
    rug = leer_imagen(nombre + "_rugosidad")[..., 1]
    r, g, b = d[..., 0], d[..., 1], d[..., 2]
    lum = d.mean(axis=2)
    sat = (d.max(axis=2) - d.min(axis=2)) / np.maximum(d.max(axis=2), 1e-4)
    h, w = rug.shape
    fila, col = np.mgrid[0:h, 0:w]
    if nombre == "torsos":
        boton = crecer(rug < .6, 1)
        cordon = (rug < .97) & ~crecer(boton, 1)
        return {"boton": (boton, .007, 4, 6), "cordon": (cordon, .0035, 2, 10)}
    if nombre == "legs":
        tostado = (r > .3) & (g / np.maximum(r, 1e-4) > .72) & (b / np.maximum(r, 1e-4) < .62)
        liga = encoger(crecer(tostado & (fila > h * .6) & (fila < h * .73), 1), 1)
        hebilla = (rug < .6) & (fila > h * .88) & (col > w * .12) & (col < w * .26)
        return {"liga": (liga, .005, 2, 8), "hebilla": (crecer(hebilla, 1), .004, 2, 4)}
    if nombre == "hats":
        ribete = encoger(crecer(rug < .72, 1), 1) & (fila > h * .6)
        costura = (r > .25) & (b < r * .45) & (g < r * .75) & (col > w * .3) & (col < w * .53) & (fila < h * .45) & (lum < .45)
        return {"ribete": (ribete, .004, 2, 10), "costura": (costura, .0015, 1, 2)}
    return {}


def malla_detalle(nombre, zona, cobertura, P, alto, ancho, cuerpo, col, W, grupos, arm):
    """zona: pixeles del detalle. cobertura: {(fila, col): (tri, bari)} de esta isla de UV."""
    tris, uvs, vidx, nor = P
    h, w = cobertura["tri"].shape
    dentro = np.zeros((h, w), bool)
    dentro[zona[:, 0], zona[:, 1]] = True
    falda = crecer(dentro) & (cobertura["tri"] >= 0)  # anillo que se hunde en la ropa: sin rendijas por debajo
    if not falda.any():
        return None
    d = distancia(dentro)
    r0, c0 = np.nonzero(falda)
    ind = -np.ones((h, w), np.int64)
    ind[r0, c0] = np.arange(len(r0))
    tri = cobertura["tri"][r0, c0]
    bar = cobertura["bar"][r0, c0]
    v = vidx[tri]
    base = (P_pos[v] * bar[..., None]).sum(1)
    n = (nor[v] * bar[..., None]).sum(1)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    t = np.clip(d[r0, c0] / max(ancho, 1), 0, 1)
    perfil = np.sqrt(np.maximum(1 - (1 - t) ** 2, 0))
    uv = (uvs[tri] * bar[..., None]).sum(1)
    # bordes sin escalones de pixel: se suaviza la posicion sobre la superficie antes de levantar el relieve
    a = ind[:-1, :-1]
    q = np.stack([a, ind[:-1, 1:], ind[1:, 1:], ind[1:, :-1]], axis=1).reshape(-1, 4)
    q = q[(q >= 0).all(axis=1)]
    if not len(q):
        return None
    aristas = np.concatenate([q[:, [0, 1]], q[:, [1, 2]], q[:, [2, 3]], q[:, [3, 0]]])
    borde = d[r0, c0] <= 1
    for _ in range(3):
        suma, cuenta = np.zeros_like(base), np.zeros(len(base))
        for i, j in ((0, 1), (1, 0)):
            np.add.at(suma, aristas[:, i], base[aristas[:, j]])
            np.add.at(cuenta, aristas[:, i], 1)
        media = suma / np.maximum(cuenta, 1)[:, None]
        base = np.where((borde & (cuenta > 0))[:, None], base * .4 + media * .6, base)
    pos = base + n * (perfil * alto - .0012 * (d[r0, c0] == 0))[:, None]
    # caras apuntando hacia fuera
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(pos.tolist(), [], q[:, ::-1].tolist() if orientacion_invertida(pos, q, n) else q.tolist())
    me.update()
    capa = me.uv_layers.new(name="UVMap")
    bucles = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", bucles)
    capa.data.foreach_set("uv", uv[bucles].ravel())
    me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), bool))
    me.materials.append(cuerpo.material_slots[0].material)
    me.update()
    o = bpy.data.objects.new(nombre, me)
    col.objects.link(o)
    o.parent = arm
    mod = o.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    # mismos pesos que la ropa en ese punto; como mucho los 4 huesos de mas peso
    pes = (W[v] * bar[..., None]).sum(1)
    orden = np.argsort(pes, axis=1)[:, :-4]
    np.put_along_axis(pes, orden, 0, axis=1)
    pes /= np.maximum(pes.sum(1, keepdims=True), 1e-9)
    for g in np.nonzero((pes > 0).any(axis=0))[0]:
        vg = o.vertex_groups.new(name=grupos[g])
        for i in np.nonzero(pes[:, g] > 0)[0]:
            vg.add([int(i)], float(pes[i, g]), "REPLACE")
    return o


def orientacion_invertida(pos, q, n):
    a, b, c = pos[q[:, 0]], pos[q[:, 1]], pos[q[:, 2]]
    return np.sum(np.cross(b - a, c - a) * n[q[:, 0]]) < 0


def procesar(nombre, arm, raiz):
    global P_pos
    o = bpy.data.objects[nombre]
    me = o.data
    me.calc_loop_triangles()
    uvl = me.uv_layers.active.data
    n_uv = np.empty(len(uvl) * 2, np.float32)
    uvl.foreach_get("uv", n_uv)
    n_uv = n_uv.reshape(-1, 2)
    tl = np.empty(len(me.loop_triangles) * 3, np.int32)
    me.loop_triangles.foreach_get("loops", tl)
    tl = tl.reshape(-1, 3)
    tv = np.empty(len(me.loop_triangles) * 3, np.int32)
    me.loop_triangles.foreach_get("vertices", tv)
    tv = tv.reshape(-1, 3)
    tp = np.empty(len(me.loop_triangles), np.int32)
    me.loop_triangles.foreach_get("polygon_index", tp)
    P_pos = np.empty(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get("co", P_pos)
    P_pos = P_pos.reshape(-1, 3)
    nor = np.empty(len(me.vertices) * 3, np.float64)
    me.vertex_normals.foreach_get("vector", nor)
    nor = nor.reshape(-1, 3)
    grupos = [g.name for g in o.vertex_groups]
    W = np.zeros((len(me.vertices), len(grupos)))
    for v in me.vertices:
        for g in v.groups:
            W[v.index, g.group] = g.weight
    tipos = mascaras(nombre)
    if not tipos:
        return {}
    alguna = next(iter(tipos.values()))[0]
    h, w = alguna.shape
    todas = np.zeros((h, w), bool)
    for m, *_ in tipos.values():
        todas |= m
    todas = crecer(todas, 2)
    cuenta = {}
    col = bpy.data.collections.new("det_" + nombre)
    raiz.children.link(col)
    islas = trozos_3d(me)  # por trozo en 3D: los lados izquierdo y derecho comparten las mismas UV
    poli_isla = np.zeros(len(me.polygons), np.int32)
    for i, pol in enumerate(islas):
        poli_isla[pol] = i
    tri_isla = poli_isla[tp]
    uvs_tri = n_uv[tl]
    for isla in range(len(islas)):
        cob = {"tri": -np.ones((h, w), np.int64), "bar": np.zeros((h, w, 3))}
        for t in np.nonzero(tri_isla == isla)[0]:
            a, b, c = uvs_tri[t] * (w, h)
            # v crece hacia arriba y la fila hacia abajo
            A = np.array([a[0], h - a[1]]); B = np.array([b[0], h - b[1]]); C = np.array([c[0], h - c[1]])
            x0, x1 = int(max(min(A[0], B[0], C[0]) - 1, 0)), int(min(max(A[0], B[0], C[0]) + 1, w - 1))
            y0, y1 = int(max(min(A[1], B[1], C[1]) - 1, 0)), int(min(max(A[1], B[1], C[1]) + 1, h - 1))
            if x1 < x0 or y1 < y0:
                continue
            det = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])
            if abs(det) < 1e-9:
                continue
            yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
            sub = todas[y0:y1 + 1, x0:x1 + 1]
            if not sub.any():
                continue
            px, py = xx + .5, yy + .5
            l1 = ((B[1] - C[1]) * (px - C[0]) + (C[0] - B[0]) * (py - C[1])) / det
            l2 = ((C[1] - A[1]) * (px - C[0]) + (A[0] - C[0]) * (py - C[1])) / det
            l3 = 1 - l1 - l2
            ok = sub & (l1 >= -.02) & (l2 >= -.02) & (l3 >= -.02)
            cob["tri"][y0:y1 + 1, x0:x1 + 1][ok] = t
            cob["bar"][y0:y1 + 1, x0:x1 + 1][ok] = np.stack([l1[ok], l2[ok], l3[ok]], axis=1)
        cubierto = cob["tri"] >= 0
        if not cubierto.any():
            continue
        for tipo, (m, alto, ancho, minimo) in tipos.items():
            for zona in componentes(m & cubierto, minimo):
                k = cuenta.get(tipo, 0) + 1
                nom = "det_%s_%s_%03d" % (nombre, tipo, k)
                ob = malla_detalle(nom, zona, cob, (tv, uvs_tri, tv, nor), alto, ancho if tipo != "boton" else max(int(distancia_zona(zona)), 2), o, col, W, grupos, arm)
                if ob:
                    cuenta[tipo] = k
    return cuenta


def distancia_zona(zona):
    return (np.ptp(zona[:, 0]) + np.ptp(zona[:, 1]) + 2) / 4


def trozos_3d(me):
    """Listas de caras de cada trozo conectado de la malla."""
    par = list(range(len(me.vertices)))

    def raiz(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    for e in me.edges:
        par[raiz(e.vertices[0])] = raiz(e.vertices[1])
    res = {}
    for p in me.polygons:
        res.setdefault(raiz(p.vertices[0]), []).append(p.index)
    return list(res.values())


# ------------------------------------------------------------------ hombreras modeladas
class Superficie:
    """Pasa de un punto de la textura a su posicion, normal y pesos sobre un trozo de la malla."""

    def __init__(self, o, caras):
        me = o.data
        me.calc_loop_triangles()
        cs = set(caras)
        uv = me.uv_layers.active.data
        t = [lt for lt in me.loop_triangles if lt.polygon_index in cs]
        self.uvs = np.array([[uv[l].uv[:] for l in lt.loops] for lt in t], np.float64)
        self.v = np.array([lt.vertices[:] for lt in t])
        self.pos = np.array([v.co[:] for v in me.vertices], np.float64)
        self.nor = np.array([v.normal[:] for v in me.vertices], np.float64)
        self.grupos = [g.name for g in o.vertex_groups]
        self.W = np.zeros((len(me.vertices), len(self.grupos)))
        for v in me.vertices:
            for g in v.groups:
                self.W[v.index, g.group] = g.weight
        # las normales tienen que salir hacia fuera del brazo, que va a lo largo de X
        usados = np.unique(self.v)
        centro = self.pos[usados].mean(0)
        eje = self.pos[usados] - np.array([centro[0], .02, 1.52])
        eje[:, 0] = 0
        self.signo = -1.0 if np.sum(eje * self.nor[usados]) < 0 else 1.0

    def en(self, uv):
        """uv: (n, 2). Devuelve posicion, normal y pesos (n, grupos)."""
        a, b, c = self.uvs[:, 0], self.uvs[:, 1], self.uvs[:, 2]
        tri, bar = [], []
        for p in np.asarray(uv):
            e0, e1, e2 = b - a, c - a, p - a
            d = e0[:, 0] * e1[:, 1] - e1[:, 0] * e0[:, 1]
            d = np.where(np.abs(d) < 1e-12, 1e-12, d)
            l1 = (e2[:, 0] * e1[:, 1] - e1[:, 0] * e2[:, 1]) / d
            l2 = (e0[:, 0] * e2[:, 1] - e2[:, 0] * e0[:, 1]) / d
            l0 = 1 - l1 - l2
            k = int(np.argmax(np.minimum(np.minimum(l0, l1), l2)))
            x = np.maximum([l0[k], l1[k], l2[k]], 0)
            tri.append(k)
            bar.append(x / x.sum())
        tri, bar = np.array(tri), np.array(bar)
        v = self.v[tri]
        pos = (self.pos[v] * bar[..., None]).sum(1)
        n = (self.nor[v] * bar[..., None]).sum(1) * self.signo
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
        return pos, n, (self.W[v] * bar[..., None]).sum(1)


def crear_objeto(nombre, pos, caras, uv, pesos, grupos, material, col, arm):
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(np.asarray(pos).tolist(), [], caras)
    me.update()
    capa = me.uv_layers.new(name="UVMap")
    bucles = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", bucles)
    capa.data.foreach_set("uv", np.asarray(uv)[bucles].ravel())
    me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), bool))
    me.materials.append(material)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    o = bpy.data.objects.new(nombre, me)
    col.objects.link(o)
    o.parent = arm
    o.modifiers.new("Armature", "ARMATURE").object = arm
    pes = np.array(pesos)
    orden = np.argsort(pes, axis=1)[:, :-4]
    np.put_along_axis(pes, orden, 0, axis=1)
    pes /= np.maximum(pes.sum(1, keepdims=True), 1e-9)
    for g in np.nonzero((pes > 0).any(axis=0))[0]:
        vg = o.vertex_groups.new(name=grupos[g])
        for i in np.nonzero(pes[:, g] > 0)[0]:
            vg.add([int(i)], float(pes[i, g]), "REPLACE")
    return o


# corte de una cinta: ancho (-1 a 1) y alto (0 = ropa, 1 = cara superior), con el canto biselado
PERFIL = [(-1, -.3), (-1, .65), (-.8, 1), (-.3, 1), (.3, 1), (.8, 1), (1, .65), (1, -.3)]


def cinta(sup, uv_i, uv_d, grueso, nombre, material, col, arm):
    """Tira solida entre dos bordes de textura: un corte por cada par de puntos y tapas en los extremos."""
    m = len(uv_i)
    pi, ni, wi = sup.en(uv_i)
    pd, nd, wd = sup.en(uv_d)
    n = (ni + nd)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    pos, uv, pes = [], [], []
    for x, h in PERFIL:
        t = (x + 1) / 2
        pos.append(pi * (1 - t) + pd * t + n * (h * grueso))
        uv.append(uv_i * (1 - t) + uv_d * t)
        pes.append(wi * (1 - t) + wd * t)
    k = len(PERFIL)
    pos = np.stack(pos, 1).reshape(-1, 3)
    uv = np.stack(uv, 1).reshape(-1, 2)
    pes = np.stack(pes, 1).reshape(m * k, -1)
    caras = []
    for i in range(m - 1):
        for j in range(k):
            s = (j + 1) % k
            caras.append((i * k + j, i * k + s, (i + 1) * k + s, (i + 1) * k + j))
    caras.append(tuple(range(k)))
    caras.append(tuple((m - 1) * k + j for j in range(k)))
    return crear_objeto(nombre, pos, caras, uv, pes, sup.grupos, material, col, arm)


def suavizar(a, n=5):
    if len(a) < n:
        return a
    b = np.convolve(np.pad(a, n // 2, mode="edge"), np.ones(n) / n, mode="valid")
    return b


def hombreras(arm, raiz):
    o = bpy.data.objects["shoulders"]
    me = o.data
    mat = o.material_slots[0].material
    col = bpy.data.collections.new("det_shoulders")
    raiz.children.link(col)
    d = leer_imagen("shoulders_difusa")[..., :3]
    h, w = d.shape[:2]
    lum = d.mean(axis=2)
    sat = (d.max(axis=2) - d.min(axis=2)) / np.maximum(d.max(axis=2), 1e-4)
    barra = (sat < .3) & (lum > .35)
    barra[:, :int(w * .37)] = False  # la cinta larga se modela aparte; si se toca, une todas las barras en una
    uvp = lambda c, f: np.column_stack([(np.asarray(c, float) + .5) / w, 1 - (np.asarray(f, float) + .5) / h])
    uv = me.uv_layers.active.data
    trozos = {}
    for caras in trozos_3d(me):
        us = np.array([uv[l].uv[0] for c in caras for l in me.polygons[c].loop_indices])
        x = np.mean([me.vertices[v].co.x for c in caras for v in me.polygons[c].vertices])
        lado = "D" if x > 0 else "I"
        if us.min() < .3 and us.max() > .9:
            trozos.setdefault(("placa", lado), caras)
        elif us.max() < .2:
            trozos.setdefault(("fleco", lado), caras)
    cuenta = {}
    zonas = sorted(componentes(barra, 30), key=lambda z: z[:, 0].mean())
    for lado in "DI":
        sup = Superficie(o, trozos[("placa", lado)])
        # cinta larga, de arriba abajo
        filas = np.arange(4, h - 3, 6)
        cinta(sup, uvp(np.full(len(filas), 29.5), filas), uvp(np.full(len(filas), 45.5), filas), .007,
              f"det_hombrera_{lado}_cinta", mat, col, arm)
        for n, z in enumerate(zonas, 1):
            cols = np.arange(z[:, 1].min(), z[:, 1].max() + 1)
            cen = np.array([z[z[:, 1] == c, 0].mean() if (z[:, 1] == c).any() else np.nan for c in cols])
            med = np.array([np.ptp(z[z[:, 1] == c, 0]) / 2 + .5 if (z[:, 1] == c).any() else np.nan for c in cols])
            bien = ~np.isnan(cen)
            cen, med, cols = suavizar(cen[bien]), suavizar(np.maximum(med[bien], 3)), cols[bien]
            pasos = np.unique(np.r_[np.arange(0, len(cols), 4), len(cols) - 1])
            # empieza metida bajo la cinta larga
            cc = np.r_[38.0, cols[pasos]]
            ff, mm = np.r_[cen[0], cen[pasos]], np.r_[med[0], med[pasos]] + 1.0
            cinta(sup, uvp(cc, ff - mm), uvp(cc, ff + mm), .005, f"det_hombrera_{lado}_barra_{n}", mat, col, arm)
        # fleco: hebras sueltas de verdad, colgando de la cinta
        fle = Superficie(o, trozos[("fleco", lado)])
        rnd = np.random.RandomState(7 if lado == "D" else 11)
        pos, caras, uvs, pes = [], [], [], []
        secciones, lados = 7, 6
        for v0 in np.linspace(.03, .97, 46):
            u = np.linspace(.20, .045 + rnd.uniform(0, .02), secciones)
            v = v0 + rnd.uniform(-.004, .004) + np.linspace(0, 1, secciones) * rnd.uniform(-.012, .012)
            pts = np.column_stack([u, v])
            p, n, wg = fle.en(pts)
            p = p + n * (.0035 + np.linspace(0, .003, secciones) * rnd.uniform(.5, 1.5))[:, None]
            eje = np.gradient(p, axis=0)
            eje /= np.maximum(np.linalg.norm(eje, axis=1, keepdims=True), 1e-9)
            a = np.cross(eje, n)
            a /= np.maximum(np.linalg.norm(a, axis=1, keepdims=True), 1e-9)
            b = np.cross(a, eje)
            base = len(pos)
            for i in range(secciones):
                r = .0022 * (1 - .45 * i / (secciones - 1))
                for j in range(lados):
                    ang = 2 * np.pi * j / lados
                    pos.append(p[i] + (a[i] * np.cos(ang) + b[i] * np.sin(ang)) * r)
                    uvs.append(pts[i])
                    pes.append(wg[i])
            for i in range(secciones - 1):
                for j in range(lados):
                    s = (j + 1) % lados
                    caras.append((base + i * lados + j, base + i * lados + s, base + (i + 1) * lados + s, base + (i + 1) * lados + j))
            caras.append(tuple(base + (secciones - 1) * lados + j for j in range(lados)))
        crear_objeto(f"det_hombrera_{lado}_fleco", pos, caras, uvs, pes, fle.grupos, mat, col, arm)
        cuenta[lado] = len(zonas)
    return cuenta


def pesos_de_manga():
    """La hombrera se deforma igual que la manga de debajo: asi la manga no la atraviesa al levantar el brazo."""
    t = bpy.data.objects["torsos"]
    me = t.data
    me.calc_loop_triangles()
    co = [v.co.copy() for v in me.vertices]
    tris = [lt.vertices[:] for lt in me.loop_triangles]
    arbol = BVHTree.FromPolygons(co, tris)
    nombres = [g.name for g in t.vertex_groups]
    W = np.zeros((len(co), len(nombres)))
    for v in me.vertices:
        for g in v.groups:
            W[v.index, g.group] = g.weight
    objetivos = [bpy.data.objects["shoulders"]] + [o for o in bpy.data.objects if o.name.startswith("det_hombrera_")]
    for o in objetivos:
        pes = np.zeros((len(o.data.vertices), len(nombres)))
        for v in o.data.vertices:
            p, _, i, _ = arbol.find_nearest(v.co)
            a, b, c = tris[i]
            x = barycentric_transform(p, co[a], co[b], co[c], Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
            bar = np.maximum(np.array(x[:]), 0)
            pes[v.index] = W[a] * bar[0] + W[b] * bar[1] + W[c] * bar[2]
        orden = np.argsort(pes, axis=1)[:, :-4]
        np.put_along_axis(pes, orden, 0, axis=1)
        pes /= np.maximum(pes.sum(1, keepdims=True), 1e-9)
        o.vertex_groups.clear()
        for g in np.nonzero((pes > 0).any(axis=0))[0]:
            vg = o.vertex_groups.new(name=nombres[g])
            for i in np.nonzero(pes[:, g] > 0)[0]:
                vg.add([int(i)], float(pes[i, g]), "REPLACE")


def construir():
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    vieja = bpy.data.collections.get("detalles_3d")
    if vieja:
        for c in list(vieja.children) + [vieja]:
            for ob in list(c.objects):
                m = ob.data
                bpy.data.objects.remove(ob)
                bpy.data.meshes.remove(m)
            bpy.data.collections.remove(c)
    raiz = bpy.data.collections.new("detalles_3d")
    next(c for c in bpy.data.collections if c.name == arm.users_collection[0].name).children.link(raiz)
    res = {}
    for n in ("torsos", "legs", "hats"):
        res[n] = procesar(n, arm, raiz)
    res["hombreras"] = hombreras(arm, raiz)
    pesos_de_manga()
    return res


resultado_detalles = construir()
