# -*- coding: utf-8 -*-
"""Cueva de bloques: los extremos (solo dan profundidad) pasan de bloques independientes a UNA superficie con textura por extremo.
La zona donde Alfred interactua (X_OESTE .. X_ESTE) se queda con bloques sueltos.

Cada superficie solo tiene las caras que dan al aire de la cueva (aire = relleno desde el pozo), con la textura y el UV de cada cara del bloque original.
Uso en Blender (llamadas cortas, una por una):
    exec(open(ruta).read())
    crear_superficies()      # crea cueva_superficie_oeste / _este (no borra nada)
    quitar_bloques(0)        # quita los bloques de esos extremos por tandas; repetir hasta que devuelva 0
"""
import bpy
from mathutils import Vector

X_OESTE, X_ESTE = -108, 10               # celdas con i < X_OESTE  /  i >= X_ESTE se vuelven superficie
SEMILLA_AIRE = (-46, -15, -1)            # una celda de aire (fondo del pozo)
TIPOS = ("stone", "andesite", "diorite")
COL, COL_SUP = "cueva_bloques", "cueva_superficies"
DIRS = {(1, 0, 0): "E", (-1, 0, 0): "W", (0, 1, 0): "N", (0, -1, 0): "S", (0, 0, 1): "U", (0, 0, -1): "D"}


def _celdas():
    celdas = {}
    for o in bpy.data.collections[COL].objects:
        p = o.name.split("_")
        if p[0] == "bloque" and p[1] in TIPOS:
            l = o.location
            celdas[(int(l.x // 1), int(l.y // 1), int(round(l.z)))] = (p[1], o)
    return celdas


def _aire(celdas):
    xs = [c[0] for c in celdas]; ys = [c[1] for c in celdas]; zs = [c[2] for c in celdas]
    lo = (min(xs), min(ys), min(zs)); hi = (max(xs), max(ys), max(zs) + 1)
    vistos = {SEMILLA_AIRE}
    pila = [SEMILLA_AIRE]
    while pila:
        x, y, z = pila.pop()
        for d in DIRS:
            n = (x + d[0], y + d[1], z + d[2])
            if n in vistos or n in celdas:
                continue
            if not all(lo[i] <= n[i] <= hi[i] for i in range(3)):
                continue
            vistos.add(n)
            pila.append(n)
    return vistos


def _caras_base(tipo):
    """para cada direccion: (vertices locales, uv, indice de material) del poligono del bloque base que mira hacia alli, con orden hacia afuera"""
    me = bpy.data.meshes[tipo]
    uv = me.uv_layers.active.data
    out = {}
    for d in DIRS:
        dv = Vector(d)
        mejor = None
        for p in me.polygons:
            c = p.center - Vector((0, 0, 0.5))
            sc = c.dot(dv)
            if mejor is None or sc > mejor[0]:
                mejor = (sc, p)
        p = mejor[1]
        idx = list(p.loop_indices)
        vs = [me.vertices[me.loops[l].vertex_index].co.copy() for l in idx]
        uvs = [tuple(uv[l].uv) for l in idx]
        n = (vs[1] - vs[0]).cross(vs[2] - vs[0])
        if n.dot(dv) < 0:
            vs.reverse(); uvs.reverse()
        out[d] = (vs, uvs, p.material_index)
    return out


def crear_superficies():
    celdas = _celdas()
    aire = _aire(celdas)
    base = {t: _caras_base(t) for t in TIPOS}
    mats = []
    for t in TIPOS:
        mats += list(bpy.data.meshes[t].materials)
    resumen = {}
    col = bpy.data.collections.get(COL_SUP) or bpy.data.collections.new(COL_SUP)
    if COL_SUP not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    for nombre, cond in (("oeste", lambda i: i < X_OESTE), ("este", lambda i: i >= X_ESTE)):
        verts, caras, uvs, mi = [], [], [], []
        for (i, j, k), (tipo, _) in celdas.items():
            if not cond(i):
                continue
            for d in DIRS:
                if (i + d[0], j + d[1], k + d[2]) in aire:
                    vs, uv, m = base[tipo][d]
                    n0 = len(verts)
                    verts += [(i + 0.5 + v.x, j + 0.5 + v.y, k + v.z) for v in vs]
                    caras.append(tuple(range(n0, n0 + len(vs))))
                    uvs += uv
                    mi.append(TIPOS.index(tipo) * 7 + m)
        nom = "cueva_superficie_" + nombre
        for viejo in (bpy.data.objects.get(nom),):
            if viejo:
                bpy.data.objects.remove(viejo, do_unlink=True)
        me = bpy.data.meshes.new(nom)
        me.from_pydata(verts, [], caras)
        me.update()
        capa = me.uv_layers.new(name="UVMap")
        capa.data.foreach_set("uv", [c for uv in uvs for c in uv])
        me.polygons.foreach_set("material_index", mi)
        for mt in mats:
            me.materials.append(mt)
        ob = bpy.data.objects.new(nom, me)
        col.objects.link(ob)
        resumen[nombre] = (len(caras), sum(1 for (i, j, k) in celdas if cond(i)))
    return resumen


def quitar_bloques(n=2000):
    """borra por tandas los objetos de los extremos (bloques y estalactitas / estalagmitas); n=0 solo cuenta. Devuelve cuantos quedan"""
    pend = []
    for o in bpy.data.collections[COL].objects:
        x = o.location.x
        if (x < X_OESTE or x >= X_ESTE) and not o.name.startswith(("escombro_", "bloque_techo")):
            pend.append(o)
    if n:
        bpy.data.batch_remove(pend[:n])
    return len(pend) - min(n, len(pend))
