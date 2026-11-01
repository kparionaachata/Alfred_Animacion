"""Paso 10 del flujo: convierte en geometria lo que el juego solo tenia pintado (galones, botones, lazos, hebillas) y quita las esquirlas.

blender -b montado.blend --factory-startup --python paso10_relieve_3d.py -- personajes/config.py original.blend salida.blend
La lista RELIEVE de la configuracion dice que mallas del juego se rehacen y que zonas de su textura se levantan. La malla se suelda y se subdivide:
sin aristas de carton. Cada texel marcado es un vertice sobre esa malla, empujado por su normal, con los mismos pesos. Lo pintado se borra de la tela.
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

ARGS = sys.argv[sys.argv.index("--") + 1:]
ORIGINAL = os.path.abspath(ARGS[1])
DESTINO = os.path.abspath(ARGS[2])
if os.path.normcase(DESTINO) in (os.path.normcase(ORIGINAL), os.path.normcase(bpy.data.filepath)):
    raise RuntimeError("La salida debe ser un archivo nuevo")
_f = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "paso8_cine_lote.py"), encoding="utf-8").read()
# solo las funciones del paso 8, sin su bucle
sys.argv = sys.argv[:sys.argv.index("--") + 1] + [ARGS[0]]
__file__ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paso8_cine_lote.py")
exec(compile(_f[:_f.index("hojas = []")], "paso8", "exec"))
bpy.context.preferences.filepaths.save_version = 0

RECETAS.update({
    "cordon": {"loseta": "sarga", "m": .022, "dibujo": .7, "sheen": .3, "roce": .9, "barro": .8, "relieve": 1.0, "oscurecer": .9, "saturacion": .7},
    "peltre": {"loseta": "metal", "m": .02, "dibujo": .25, "rug": .34, "metal": 1.0, "barro": .5, "mancha": .3, "roce": 0.0, "sangre": .2, "oscurecer": .85, "relieve": .15},
})


def desenfoque(a, s):
    if s <= 0:
        return a
    h, w = a.shape
    fy, fx = np.fft.fftfreq(h)[:, None], np.fft.rfftfreq(w)[None, :]
    return np.fft.irfft2(np.fft.rfft2(a) * np.exp(-2 * (np.pi * s) ** 2 * (fx ** 2 + fy ** 2)), s=a.shape).astype(np.float32)


def leer(im):
    """Pixeles RGBA con la fila 0 arriba, como se ve la textura."""
    w, h = im.size
    p = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(p)
    return p.reshape(h, w, 4)[::-1].copy()


def escribir(im, p):
    im.pixels.foreach_set(p[::-1].ravel())
    im.update()
    im.pack()


def ampliar(a, f):
    a = np.repeat(np.repeat(a, f, axis=0), f, axis=1)
    return desenfoque(a, f * .55) if a.ndim == 2 else np.dstack([desenfoque(a[..., i], f * .55) for i in range(a.shape[2])])


def imagen_de(textura, suf):
    """La imagen que usan los materiales de cine: puede haber otras con el mismo nombre y otro numero."""
    for m in bpy.data.materials:
        if m.name.startswith(textura + "_cine") and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image and n.image.name.startswith(textura + suf):
                    return n.image
    raise KeyError(textura + suf)


def rellenar(p, m):
    """Borra lo marcado: los colores de alrededor lo cubren, de lejos a cerca para no dejar halo."""
    libre = (1 - np.clip(desenfoque(m, 1.2) * 3, 0, 1))[..., None]
    sal = p.copy()
    for s in (40, 16, 7, 3):
        pes = desenfoque(libre[..., 0], s)[..., None]
        col = np.dstack([desenfoque(p[..., i] * libre[..., 0], s) for i in range(p.shape[2])]) / np.maximum(pes, 1e-4)
        sal = np.where(pes > .03, col, sal)
    return p * libre + sal * (1 - libre)


DESVIOS = [Vector(v) for v in ((0, 0, 0), (.4, 0, 0), (-.4, 0, 0), (0, .4, 0), (0, -.4, 0), (0, 0, .4), (0, 0, -.4))]


class Soporte:
    """Malla del juego lista para colocar puntos por UV: islas sin mezclar lados espejados, normales lisas y pesos por triangulo."""

    def __init__(self, o, arbol, caras=None):
        me = o.data
        self.nombres = [g.name for g in o.vertex_groups]
        n = len(me.vertices)
        self.co = np.empty(n * 3, np.float32)
        me.vertices.foreach_get("co", self.co)
        self.co = self.co.reshape(-1, 3)
        uv = np.empty(len(me.loops) * 2, np.float32)
        me.uv_layers.active.data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        self.W = np.zeros((n, len(self.nombres)), np.float32)
        for v in me.vertices:
            for g in v.groups:
                self.W[v.index, g.group] = g.weight
        cn = np.empty(len(me.loops) * 3, np.float32)
        me.corner_normals.foreach_get("vector", cn)
        cn = cn.reshape(-1, 3)
        tris = [t for t in me.loop_triangles if caras is None or caras(me, t, uv)] if me.calc_loop_triangles() is None else []
        self.tv = np.array([t.vertices[:] for t in tris], np.int32)
        tl = np.array([t.loops[:] for t in tris], np.int32)
        self.tuv = uv[tl]
        # normal por vertice de posicion: las costuras del juego no se abren al empujar
        llave = {}
        ids = np.array([llave.setdefault(tuple(np.round(c, 4)), len(llave)) for c in self.co.tolist()], np.int32)
        a, b, c = self.co[self.tv[:, 0]], self.co[self.tv[:, 1]], self.co[self.tv[:, 2]]
        nt = np.cross(b - a, c - a)
        # las normales guardadas tambien apuntan adentro en algunas zonas: decide el lado por el que se sale del personaje
        guia = cn[tl].mean(axis=1)
        signos = np.where((nt * guia).sum(axis=1) < 0, -1.0, 1.0)
        centros = (a + b + c) / 3
        unit = nt / np.maximum(np.linalg.norm(nt, axis=1, keepdims=True), 1e-12)
        for i in range(len(tris) if arbol else 0):
            n = Vector((unit[i] * signos[i]).tolist())
            ce = Vector(centros[i].tolist())
            fuera = sum(arbol.ray_cast(ce + (n + d).normalized() * .004, (n + d).normalized(), 2.0)[0] is None for d in DESVIOS)
            dentro = sum(arbol.ray_cast(ce - (n + d).normalized() * .004, -(n + d).normalized(), 2.0)[0] is None for d in DESVIOS)
            if dentro > fuera:
                signos[i] = -signos[i]
        nt = nt * signos[:, None]
        suma = np.zeros((len(llave), 3), np.float32)
        for k in range(3):
            np.add.at(suma, ids[self.tv[:, k]], nt)
        self.nv = (suma / np.maximum(np.linalg.norm(suma, axis=1, keepdims=True), 1e-9))[ids]
        self.signo = np.sign(np.cross(self.tuv[:, 1] - self.tuv[:, 0], self.tuv[:, 2] - self.tuv[:, 0]))
        # islas: triangulos con arista comun, misma UV y mismo sentido
        padre = list(range(len(tris)))

        def raiz(i):
            while padre[i] != i:
                padre[i] = padre[padre[i]]
                i = padre[i]
            return i

        aristas = {}
        for i in range(len(tris)):
            for x, y in ((0, 1), (1, 2), (2, 0)):
                ka = tuple(sorted((tuple(np.round(self.tuv[i, x], 4).tolist()), tuple(np.round(self.tuv[i, y], 4).tolist()))))
                j = aristas.setdefault((ka, self.signo[i]), i)
                padre[raiz(i)] = raiz(j)
        self.isla = np.array([raiz(i) for i in range(len(tris))], np.int32)


def objeto_relieve(nombre, p, caras, pes, sop, arm, material):
    """Objeto con la malla, los pesos del soporte y los atributos que usa el material de cine."""
    # sin vertices sueltos: los puntos de margen que no forman cara
    usados = np.unique(np.array(caras, np.int64).ravel())
    nuevo = np.full(len(p), -1, np.int64)
    nuevo[usados] = np.arange(len(usados))
    caras = [tuple(nuevo[list(c)].tolist()) for c in caras]
    p, pes = p[usados], pes[usados]
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(p.tolist(), [], caras)
    me.update()
    me.shade_smooth()
    me.uv_layers.new(name="UVMap")
    me.materials.append(material)
    me.attributes.new("cine_vis", "FLOAT", "FACE").data.foreach_set("value", np.ones(len(caras), np.float32))
    me.attributes.new("cine_p", "FLOAT_VECTOR", "POINT").data.foreach_set("vector", p.astype(np.float32).ravel())
    o = bpy.data.objects.new(nombre, me)
    o.parent = arm
    o.modifiers.new("Armature", "ARMATURE").object = arm
    o.cycles.shadow_terminator_offset = .2
    for j, g in enumerate(sop.nombres):
        vg = o.vertex_groups.new(name=g)
        for i in np.nonzero(pes[:, j] > .004)[0].tolist():
            vg.add([i], float(pes[i, j]), "REPLACE")
    return o


def levantar(sop, alto, f, tam, nombre, arm, material, base=0.0, hundir=.0006, respeta_borde=False):
    """Malla sobre el soporte: un vertice por texel donde alto > 0, empujado por la normal. El borde se hunde para que no quede abierto."""
    h, w = alto.shape
    H, W = h, w
    if respeta_borde:
        # sobre el borde de la malla los texeles hacen escalera: el relieve baja antes de llegar a el
        cubre = np.zeros(alto.shape, np.float32)
        for q in sop.tuv * (W, H):
            q = np.c_[q[:, 0] - .5, H - q[:, 1] - .5]
            x0, x1 = int(max(np.floor(q[:, 0].min()), 0)), int(min(np.ceil(q[:, 0].max()), W - 1))
            y0, y1 = int(max(np.floor(q[:, 1].min()), 0)), int(min(np.ceil(q[:, 1].max()), H - 1))
            d = (q[1, 1] - q[2, 1]) * (q[0, 0] - q[2, 0]) + (q[2, 0] - q[1, 0]) * (q[0, 1] - q[2, 1])
            if x1 < x0 or y1 < y0 or abs(d) < 1e-9:
                continue
            ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
            b0 = ((q[1, 1] - q[2, 1]) * (xs - q[2, 0]) + (q[2, 0] - q[1, 0]) * (ys - q[2, 1])) / d
            b1 = ((q[2, 1] - q[0, 1]) * (xs - q[2, 0]) + (q[0, 0] - q[2, 0]) * (ys - q[2, 1])) / d
            cubre[y0:y1 + 1, x0:x1 + 1][(b0 >= 0) & (b1 >= 0) & (b0 + b1 <= 1)] = 1
        c = np.clip(desenfoque(cubre, f * 1.6) * 2.2 - 1.2, 0, 1)
        alto = alto * np.sin(c * np.pi / 2) ** .7
    puntos = {}
    pos, nor, pes, alt = [], [], [], []
    activo = alto > 1e-5
    # un texel de margen: el borde debe llegar a cero y meterse en la tela
    margen = desenfoque(activo.astype(np.float32), 1.0) > .02
    # donde la textura esta muy estirada en una cara el relieve saldria como un escalon: esas caras no lo llevan
    l3 = np.stack([np.linalg.norm(sop.co[sop.tv[:, (k + 1) % 3]] - sop.co[sop.tv[:, k]], axis=1) for k in range(3)], axis=1)
    l2 = np.stack([np.linalg.norm(sop.tuv[:, (k + 1) % 3] - sop.tuv[:, k], axis=1) for k in range(3)], axis=1)
    escala = l3 / np.maximum(l2, 1e-9)
    estirada = escala.max(axis=1) / np.maximum(escala.min(axis=1), 1e-9) > 3.5
    print(f"ESTIRADAS {nombre}: {int(estirada.sum())} de {len(estirada)}", flush=True)
    for i in range(len(sop.tv)):
        if estirada[i]:
            continue
        q = sop.tuv[i] * (W, H)
        q = np.c_[q[:, 0] - .5, H - q[:, 1] - .5]
        x0, x1 = int(max(np.floor(q[:, 0].min()), 0)), int(min(np.ceil(q[:, 0].max()), W - 1))
        y0, y1 = int(max(np.floor(q[:, 1].min()), 0)), int(min(np.ceil(q[:, 1].max()), H - 1))
        if x1 < x0 or y1 < y0 or not margen[y0:y1 + 1, x0:x1 + 1].any():
            continue
        ys, xs = np.nonzero(margen[y0:y1 + 1, x0:x1 + 1])
        xs, ys = xs + x0, ys + y0
        d = (q[1, 1] - q[2, 1]) * (q[0, 0] - q[2, 0]) + (q[2, 0] - q[1, 0]) * (q[0, 1] - q[2, 1])
        if abs(d) < 1e-9:
            continue
        b0 = ((q[1, 1] - q[2, 1]) * (xs - q[2, 0]) + (q[2, 0] - q[1, 0]) * (ys - q[2, 1])) / d
        b1 = ((q[2, 1] - q[0, 1]) * (xs - q[2, 0]) + (q[0, 0] - q[2, 0]) * (ys - q[2, 1])) / d
        b = np.c_[b0, b1, 1 - b0 - b1]
        dentro = (b > -1e-3).all(axis=1)
        vs = sop.tv[i]
        p3 = b @ sop.co[vs]
        n3 = b @ sop.nv[vs]
        # superficie curva sobre las caras planas (teselado de Phong): las cintas no salen a franjas
        cur = np.zeros_like(p3)
        for k in range(3):
            cur += b[:, k, None] * (p3 - ((p3 - sop.co[vs[k]]) * sop.nv[vs[k]]).sum(axis=1, keepdims=True) * sop.nv[vs[k]])
        p3 = p3 * .3 + cur * .7
        w3 = b @ sop.W[vs]
        isla = int(sop.isla[i])
        for k in np.nonzero(dentro)[0]:
            ll = (isla, int(xs[k]), int(ys[k]))
            if ll in puntos:
                continue
            puntos[ll] = len(pos)
            pos.append(p3[k])
            nor.append(n3[k])
            pes.append(w3[k])
            alt.append(alto[ys[k], xs[k]])
    if not pos:
        print("VACIO", nombre, flush=True)
        return None
    pos, nor, pes, alt = np.array(pos), np.array(nor), np.array(pes), np.array(alt)
    nor /= np.maximum(np.linalg.norm(nor, axis=1, keepdims=True), 1e-9)
    p = pos + nor * np.where(alt > 1e-5, alt + base, -hundir)[:, None]
    caras = []
    for (isla, x, y), a in puntos.items():
        b, c, d = puntos.get((isla, x + 1, y)), puntos.get((isla, x + 1, y + 1)), puntos.get((isla, x, y + 1))
        if b is None or c is None or d is None or max(alt[[a, b, c, d]]) <= 1e-5:
            continue
        cara = [a, b, c, d]
        n = np.cross(p[b] - p[a], p[d] - p[a])
        caras.append(cara if n.dot(nor[a]) > 0 else cara[::-1])
    print(f"RELIEVE {nombre}: {len(p)} vertices, {len(caras)} caras", flush=True)
    return objeto_relieve(nombre, p, caras, pes, sop, arm, material)


def lazo_3d(sop, centro_px, tam, nombre, arm, material, separa=.0045):
    """Lazo de cinta anudado de verdad, uno por cada sitio del cuerpo donde cae ese punto de la textura: nudo, dos gazas y dos caidas."""
    W, H = tam[1], tam[0]
    objetivo = np.array((centro_px[0] / W, 1 - centro_px[1] / H), np.float32)
    sitios = {}
    for i in range(len(sop.tv)):
        q = sop.tuv[i]
        d = (q[1, 1] - q[2, 1]) * (q[0, 0] - q[2, 0]) + (q[2, 0] - q[1, 0]) * (q[0, 1] - q[2, 1])
        if abs(d) < 1e-12:
            continue
        b0 = ((q[1, 1] - q[2, 1]) * (objetivo[0] - q[2, 0]) + (q[2, 0] - q[1, 0]) * (objetivo[1] - q[2, 1])) / d
        b1 = ((q[2, 1] - q[0, 1]) * (objetivo[0] - q[2, 0]) + (q[0, 0] - q[2, 0]) * (objetivo[1] - q[2, 1])) / d
        b = np.array((b0, b1, 1 - b0 - b1), np.float32)
        if (b > -1e-3).all():
            vs = sop.tv[i]
            sitios.setdefault(int(np.sign(sop.co[vs].mean(axis=0)[0])), (b @ sop.co[vs], b @ sop.nv[vs], b @ sop.W[vs]))
    pos, caras = [], []

    def banda(fun, nu, nv):
        """Tira de cinta: fun(s, t) da el punto en coordenadas locales (derecha, arriba, afuera)."""
        k = len(pos)
        for i in range(nu + 1):
            for j in range(nv + 1):
                pos.append(fun(i / nu, j / nv * 2 - 1))
        for i in range(nu):
            for j in range(nv):
                a = k + i * (nv + 1) + j
                caras.append((a, a + nv + 1, a + nv + 2, a + 1))

    def gaza(lado, alza):
        ax = np.array((lado * math.cos(alza), math.sin(alza)))
        pe = np.array((-ax[1], ax[0]))
        largo, ancho = .034, .0085

        def f(s, t):
            # ida por delante y vuelta por detras, con la cinta fruncida junto al nudo
            ida = s < .5
            u = s * 2 if ida else (1 - s) * 2
            ga = ancho * (.28 + .72 * math.sin(min(u * 1.25, 1) * math.pi / 2) ** .8)
            alto = math.sin(u * math.pi) ** .6 * (.0075 if ida else .0012) + .003 * u
            pliegue = (1 - u) ** 2 * .0016 * math.cos(t * 7) + .0009 * (1 - t * t)
            xy = ax * largo * u + pe * t * ga
            return (xy[0], xy[1], alto + pliegue)
        banda(f, 32, 8)

    def caida(lado, abre):
        ax = np.array((lado * math.sin(abre), -math.cos(abre)))
        pe = np.array((-ax[1], ax[0]))

        def f(s, t):
            ga = .0028 + .0062 * min(s * 3, 1) ** .7
            # punta en cola de golondrina
            largo = .05 * s * (1 - .16 * s ** 8 * (1 - abs(t)))
            xy = ax * largo + pe * t * ga
            return (xy[0], xy[1], .002 + .0022 * math.sin(s * 7 + lado) + .0015 * (1 - s) ** 2 * math.cos(t * 6))
        banda(f, 28, 8)

    def nudo():
        def f(s, t):
            a = (s - .5) * math.pi
            b = (t + 1) * math.pi
            return (.0072 * math.cos(a) * math.cos(b) * (1 + .1 * math.cos(b * 5)), .0085 * math.cos(a) * math.sin(b), .0085 + .0058 * math.sin(a))
        banda(f, 14, 24)

    gaza(1, math.radians(14))
    gaza(-1, math.radians(10))
    caida(1, math.radians(24))
    caida(-1, math.radians(18))
    nudo()
    malla_p, malla_c, malla_w = [], [], []
    for centro, nor, peso in sitios.values():
        nor = nor / max(np.linalg.norm(nor), 1e-9)
        der = np.cross(np.array((0, 0, 1.0)), nor)
        der /= max(np.linalg.norm(der), 1e-9)
        arr = np.cross(nor, der)
        k = len(malla_p)
        malla_p += [centro + der * a + arr * b + nor * (c + separa) for a, b, c in pos]
        malla_c += [tuple(x + k for x in c) for c in caras]
        malla_w += [peso] * len(pos)
    print(f"LAZO {nombre}: {len(sitios)} sitios, {len(malla_p)} vertices", flush=True)
    o = objeto_relieve(nombre, np.array(malla_p, np.float32), malla_c, np.array(malla_w, np.float32), sop, arm, material)
    g = o.modifiers.new("Grosor", "SOLIDIFY")
    g.thickness, g.offset = .0011, 0
    return o


def afuera(bm, arbol):
    """Caras coherentes y cada trozo conectado hacia fuera del personaje."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if arbol is None:
        return
    vistas = set()
    for f0 in bm.faces:
        if f0.index in vistas:
            continue
        pila, trozo = [f0], []
        vistas.add(f0.index)
        while pila:
            f = pila.pop()
            trozo.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in vistas:
                        vistas.add(g.index)
                        pila.append(g)
        fuera = dentro = 0
        for f in trozo[::max(len(trozo) // 40, 1)]:
            c, n = f.calc_center_median(), f.normal
            fuera += sum(arbol.ray_cast(c + (n + d).normalized() * .006, (n + d).normalized(), 2.0)[0] is None for d in DESVIOS)
            dentro += sum(arbol.ray_cast(c - (n + d).normalized() * .006, -(n + d).normalized(), 2.0)[0] is None for d in DESVIOS)
        if dentro > fuera:
            bmesh.ops.reverse_faces(bm, faces=trozo)


def suavizar(o, arbol, zona=None, slots=None, niveles=2):
    """Suelda las costuras de la malla, junta triangulos y subdivide. zona(u, v, z) reparte las caras por material; None la quita."""
    me = o.data
    bm = bmesh.new()
    bm.from_mesh(me)
    if zona:
        uvl = bm.loops.layers.uv.active
        fuera = []
        for f in bm.faces:
            z = zona([l[uvl].uv[0] for l in f.loops], [l[uvl].uv[1] for l in f.loops], [v.co.z for v in f.verts])
            if z in slots:
                f.material_index = slots[z]
            else:
                fuera.append(f)
        bmesh.ops.delete(bm, geom=fuera, context="FACES")
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=.0002)
    bmesh.ops.join_triangles(bm, faces=bm.faces, angle_face_threshold=math.radians(45), angle_shape_threshold=math.radians(60), cmp_uvs=True, cmp_materials=True)
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    afuera(bm, arbol)
    # las esquinas muy cerradas (cuello, suelas, puno) no se derriten del todo
    pliegue = bm.edges.layers.float.get("crease_edge") or bm.edges.layers.float.new("crease_edge")
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(70):
            e[pliegue] = .65
    bm.to_mesh(me)
    bm.free()
    if "custom_normal" in me.attributes:
        me.attributes.remove(me.attributes["custom_normal"])
    me.shade_smooth()
    guardadas = [m for m in o.modifiers]
    for m in guardadas:
        o.modifiers.remove(m)
    if o.name not in bpy.context.view_layer.objects:
        bpy.context.scene.collection.objects.link(o)
        temporal = True
    else:
        temporal = False
    sub = o.modifiers.new("Suave", "SUBSURF")
    sub.levels, sub.render_levels = niveles, niveles
    with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o]):
        bpy.ops.object.modifier_apply(modifier=sub.name)
    if temporal:
        bpy.context.scene.collection.objects.unlink(o)
    me = o.data
    me.shade_smooth()
    o.modifiers.new("Armature", "ARMATURE").object = arm
    o.cycles.shadow_terminator_offset = .05


def nueva_imagen(nombre, p, datos):
    h, w = p.shape[:2]
    im = bpy.data.images.new(nombre, w, h, alpha=True)
    if datos:
        im.colorspace_settings.name = "Non-Color"
    escribir(im, p)
    return im


def color_plano(nombre, rgb):
    for suf, c in (("_difusa", (*rgb, 1)), ("_normal", (.5, .5, 1, 1))):
        im = bpy.data.images.new(nombre + suf, 4, 4)
        im.pixels.foreach_set(np.tile(np.array(c, np.float32), 16))
        if suf == "_normal":
            im.colorspace_settings.name = "Non-Color"
        im.pack()


def caja(forma, x0, y0, x1, y1):
    """Cajas en pixeles de la textura original."""
    y, x = np.mgrid[0:forma[0], 0:forma[1]].astype(np.float32)
    return (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)


arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
col_rel = bpy.data.collections.new("relieve_3d")
next(c for c in bpy.data.collections if arm.name in c.objects).children.link(col_rel)
for g, v in RECETAS_NUEVAS.items():
    RECETAS.setdefault(g, {}).update(v)
arbol = arbol_personaje()

quitadas = 0
for o in [o for o in bpy.data.objects if o.type == "MESH" and (o.name in QUITAR_NOMBRES or any(t in o.get("cine_ruta", "") for t in QUITAR))]:
    bpy.data.objects.remove(o)
    quitadas += 1
print("QUITADAS", quitadas, flush=True)

for ruta, textura, receta in REHACER:
    # recetas cambiadas en la configuracion: el material se genera otra vez
    for suf in ("_difusa", "_normal"):
        im = imagen_de(textura, suf)
        if im.name != textura + suf:
            otra = bpy.data.images.get(textura + suf)
            if otra:
                otra.name = textura + suf + "_viejo"
            im.name = textura + suf
    mat = material_cine(textura, receta, bpy.data.images["cine_" + RECETAS[receta]["loseta"]])
    for o in bpy.data.objects:
        if ruta in o.get("cine_ruta", ""):
            o.data.materials[0] = mat

with bpy.data.libraries.load(ORIGINAL) as (ori, des):
    nombres = [g["malla"] for g in RELIEVE]
    des.objects = list(nombres)
mallas = dict(zip(nombres, des.objects))
materiales = {}
for g in RELIEVE:
    o = mallas[g["malla"]]
    piel = o.data.materials[0]
    with bpy.data.libraries.load(ORIGINAL) as (ori, des):
        des.images = [g["textura"] + "_difusa", g["textura"] + "_normal"]
    im_d, im_n = des.images
    dif, nor = leer(im_d), leer(im_n)
    g["_dif"] = dif
    borrar = np.zeros(dif.shape[:2], np.float32)
    contacto = borrar.copy()
    for pieza in g["piezas"]:
        m = pieza["mascara"](dif[..., 0], dif[..., 1], dif[..., 2], caja)
        pieza["_m"] = m
        borrar = np.maximum(borrar, m.astype(np.float32))
        if not pieza.get("lazo"):
            contacto = np.maximum(contacto, m.astype(np.float32))
    # sombra de contacto: el relieve oscurece la tela que tiene al lado
    sombra = np.clip(desenfoque(contacto, 1.0) * 1.4, 0, 1)[..., None]
    limpio = rellenar(dif, borrar)
    limpio[..., :3] *= 1 - .3 * sombra * (1 - contacto[..., None])
    limpio[..., 3] = dif[..., 3]
    F = g["escala"]
    alta = ampliar(limpio, F)
    if g.get("pintar"):
        alta = g["pintar"](alta, F, desenfoque)
    plano = np.array((.5, .5, 1, 1), np.float32)
    t = np.clip(desenfoque(borrar, 1.5) * 2.5, 0, 1)[..., None]
    nn = rellenar(nor, borrar) * (1 - t) + plano * t
    base = g["textura"] + "_hd"
    nueva_imagen(base + "_difusa", np.clip(alta, 0, 1), False)
    nueva_imagen(base + "_normal", nn, True)
    # materiales por zona; None deja el del juego
    me = o.data
    me.materials.clear()
    slots = {}
    for k, (zona_n, receta) in enumerate(g["slots"].items()):
        slots[zona_n] = k
        if receta is None:
            me.materials.append(piel)
        elif isinstance(receta, tuple):
            # material de un solo color, sin depender de la textura del juego
            rec, plano_n, color = receta
            if plano_n + "_difusa" not in bpy.data.images:
                color_plano(plano_n, color)
            me.materials.append(material_cine(plano_n, rec, bpy.data.images["cine_" + RECETAS[rec]["loseta"]]))
        else:
            me.materials.append(material_cine(base, receta, bpy.data.images["cine_" + RECETAS[receta]["loseta"]]))
    suavizar(o, arbol, g["zona"], slots)
    if g.get("forma"):
        g["forma"](o)
    o.name = "suave_" + g["malla"]
    o.parent = arm
    o["cine_ruta"] = "suave/" + g["malla"]
    col_rel.objects.link(o)
    print("SUAVE", o.name, len(o.data.polygons), "caras", flush=True)

for o in [o for o in bpy.data.objects if o.type == "MESH" and (o.name in SUAVES_NOMBRES or any(t in o.get("cine_ruta", "") for t in SUAVES_RUTAS))]:
    suavizar(o, arbol)
    if any(t in o.get("cine_ruta", "") for t in GROSOR):
        sol = o.modifiers.new("Grosor", "SOLIDIFY")
        sol.thickness, sol.offset, sol.use_rim = GROSOR_M, 1, True
print("SUAVES_PIEZAS listas", flush=True)

# el desgaste se mide con la forma nueva
arbol = arbol_personaje()
for g in RELIEVE:
    o = bpy.data.objects["suave_" + g["malla"]]
    visibilidad(o, arbol)
    sop = Soporte(o, None)
    for pieza in g["piezas"]:
        Fp = pieza["f"]
        alto = pieza["alto"](pieza["_m"], Fp, g["_dif"], ampliar, desenfoque) if pieza["alto"] else None
        color_plano(pieza["nombre"], pieza["color"])
        mat = material_cine(pieza["nombre"], pieza["receta"], bpy.data.images["cine_" + RECETAS[pieza["receta"]]["loseta"]])
        if pieza.get("lazo"):
            r = lazo_3d(sop, pieza["lazo"], pieza["_m"].shape, pieza["nombre"], arm, mat)
        else:
            r = levantar(sop, alto, Fp, pieza["_m"].shape, pieza["nombre"], arm, mat, base=pieza.get("base", 0.0), respeta_borde=pieza.get("respeta_borde", False))
        if r and pieza.get("recorte"):
            # sobrantes medidos a mano: la funcion recibe la posicion y dice si se quita
            bm = bmesh.new()
            bm.from_mesh(r.data)
            fuera = [v for v in bm.verts if pieza["recorte"](v.co)]
            bmesh.ops.delete(bm, geom=fuera, context="VERTS")
            bm.to_mesh(r.data)
            bm.free()
            print("RECORTE", pieza["nombre"], len(fuera), "vertices", flush=True)
        if r:
            col_rel.objects.link(r)
    if g.get("grosor"):
        sol = o.modifiers.new("Grosor", "SOLIDIFY")
        sol.thickness, sol.offset, sol.use_rim = g["grosor"], -1, True
    if g.get("extra"):
        g["extra"](o)

for fn in FINAL:
    fn()

for x in [x for x in bpy.data.objects if x.type == "ARMATURE" and x is not arm]:
    d = x.data
    bpy.data.objects.remove(x)
    bpy.data.armatures.remove(d)
bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=DESTINO, compress=True, check_existing=False)
print(f"TOTAL objetos={len(bpy.data.objects)} {os.path.getsize(DESTINO) // 1024 // 1024}MB", flush=True)
print("FIN", flush=True)
