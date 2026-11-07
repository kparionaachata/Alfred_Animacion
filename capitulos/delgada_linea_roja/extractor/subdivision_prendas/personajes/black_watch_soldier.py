"""Configuracion de paso4_subdividir.py para britain_inf_elite_british_black_watch.soldier.

Las zonas estan medidas sobre SU textura y SUS UV (paso3_inspeccionar.py): otro personaje necesita las suyas.
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree


def zona_legs(u, v, z):
    if max(z) > .6 or min(v) >= .375:
        # la piel de la pierna ocupa esta franja de la textura; lo demas de esta altura es el kilt
        return "piel" if min(v) >= .375 and max(v) <= .665 and max(u) < .6 else "kilt"
    if min(v) >= .225:
        return "medias"
    return "polainas" if max(v) > .155 else "zapatos"


def zona_torsos(u, v, z):
    return "corbatin" if min(u) >= .595 and max(v) <= .22 else "casaca"


# prenda: (mallas enteras, (malla a cortar, zona), prefijos de los detalles 3D)
PRENDAS = {
    "casaca": ((), ("torsos", zona_torsos), ("det_torsos_",)),
    "corbatin": ((), ("torsos", zona_torsos), ()),
    "kilt": ((), ("legs", zona_legs), ()),
    "medias": ((), ("legs", zona_legs), ("det_legs_liga_",)),
    "polainas": ((), ("legs", zona_legs), ()),
    "zapatos": ((), ("legs", zona_legs), ("det_legs_hebilla_",)),
    "gorro": (("hats", "plumes"), None, ("det_hats_",)),
    "correajes": (("belts",), None, ()),
    "hombreras": (("shoulders",), None, ("det_hombrera_",)),
}


def zona_casaca(u0, u1, v0, v1, y1, z1):
    if u0 >= .59:
        return "mangas" if v0 >= .55 else "cuello" if v1 <= .345 else "punos"
    return "faldones" if z1 <= 1.16 else "cuerpo"


def zona_gorro(u0, u1, v0, v1, y1, z1):
    if u0 >= .76:
        return "franja"
    if u0 < .2:
        return "cuerpo"
    return "visera" if y1 < -.05 else "interior"


def zona_kilt(u0, u1, v0, v1, y1, z1):
    return "forro" if u0 >= .65 and z1 > 1 else "tela"


def zona_zapatos(u0, u1, v0, v1, y1, z1):
    return "suelas" if z1 < .02 else "zapato"


# detalle: (malla a cortar, zona) o texto que aparece en el nombre de sus objetos. Corbatin, polainas y correajes son de una sola pieza.
DETALLES = {
    "casaca": {"cuerpo": ("casaca", zona_casaca), "faldones": ("casaca", zona_casaca), "mangas": ("casaca", zona_casaca), "punos": ("casaca", zona_casaca),
               "cuello": ("casaca", zona_casaca), "botones": "_boton_", "cordones": "_cordon_"},
    "kilt": {"tela": ("kilt", zona_kilt), "forro": ("kilt", zona_kilt)},
    "medias": {"media": "medias", "ligas": "_liga_"},
    "zapatos": {"zapato": ("zapatos", zona_zapatos), "suelas": ("zapatos", zona_zapatos), "hebillas": "_hebilla_"},
    "gorro": {"cuerpo": ("hats", zona_gorro), "franja": ("hats", zona_gorro), "visera": ("hats", zona_gorro), "interior": ("hats", zona_gorro),
              "plumas": "plumes", "ribete": "_ribete_"},
    "hombreras": {"ala": "shoulders", "barras": "_barra_", "cinta": "_cinta", "flecos": "_fleco"},
}


# mallas limpias con piezas conectadas sueltas. Botones, cordones, ligas, hebillas y ribete no: sus trozos son esquirlas del relieve
CON_TROZOS = ("corbatin", "correajes", "polainas", "casaca/detalles/cuello", "casaca/detalles/cuerpo", "casaca/detalles/faldones", "casaca/detalles/mangas",
              "casaca/detalles/punos", "gorro/detalles/franja", "gorro/detalles/plumas", "gorro/detalles/visera", "hombreras/detalles/ala",
              "hombreras/detalles/flecos/detalles/D_fleco", "hombreras/detalles/flecos/detalles/I_fleco", "kilt/detalles/forro", "kilt/detalles/tela",
              "medias/detalles/media", "zapatos/detalles/suelas", "zapatos/detalles/zapato")


def zonas_puno(x, y, r, g, b, lum):
    def caja(x0, y0, x1, y1):
        return (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
    claro = (r - b) < .12
    z = [("banda", caja(300, 312, 520, 340)), ("galon", caja(300, 250, 520, 263))]
    for n, (x0, x1) in enumerate(((372, 393), (394, 414), (415, 435), (436, 454)), 1):
        z.append((f"presilla_{n}", caja(x0, 259, x1, 293) & claro))
    return z, "tela"


def zonas_ala(x, y, r, g, b, lum):
    def caja(x0, y0, x1, y1):
        return (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
    claro = (r - g) < .25
    z = [("cinta", caja(0, 0, 45, 256) & claro)]
    filas = ((39, 56), (66, 82), (95, 111), (123, 140), (150, 167), (179, 196), (206, 222))
    for n, (y0, y1) in enumerate(filas, 1):
        z.append((f"barra_{n}", caja(46, y0, 128, y1) & claro))
    return z, "base_roja"


def zonas_media(x, y, r, g, b, lum):
    def caja(x0, y0, x1, y1):
        return (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
    lazo = caja(143, 329, 198, 371) & (((g - b) > .1) | (lum < .18)) & ((y >= 339) | ((x >= 155) & (x <= 185)))
    return [("lazo", lazo), ("banda", caja(0, 327, 511, 339)), ("franja_superior", caja(0, 300, 511, 326)), ("borde_azul", caja(0, 379, 511, 410))], "cuadros"


def zonas_zapato(x, y, r, g, b, lum):
    hebilla = (x >= 70) & (x <= 124) & (y >= 466) & (y <= 479) & ((r - b) > .15)
    return [("hebilla", hebilla), ("borde_azul", ((b - r) > .02) & (lum > .06))], "cuero"


# piezas de una sola malla con detalles solo pintados: se cortan siguiendo el dibujo de la textura
PINTADAS = {
    "casaca/detalles/punos/detalles/punos_D_01": zonas_puno, "casaca/detalles/punos/detalles/punos_I_01": zonas_puno,
    "hombreras/detalles/ala/detalles/ala_D_01": zonas_ala, "hombreras/detalles/ala/detalles/ala_I_01": zonas_ala,
    "medias/detalles/media/detalles/media_D_01": zonas_media, "medias/detalles/media/detalles/media_I_01": zonas_media,
    "zapatos/detalles/zapato/detalles/zapato_D_01": zonas_zapato, "zapatos/detalles/zapato/detalles/zapato_I_01": zonas_zapato,
}


# receta de paso8_cine_lote.py para cada detalle: el primer texto que aparece en su ruta decide. anillo = cinta rehecha de paso7.
CINE = [
    ("medias/detalles/media/detalles/media_I_01/detalles/banda/", "anillo"),
    ("medias/detalles/media/detalles/media_D_01/detalles/banda/", "anillo"),
    ("hebilla", "metal"), ("boton", "metal"), ("presilla", "galon"), ("galon", "galon"), ("cordon", "galon"), ("barra", "galon"),
    ("ribete", "galon"), ("/cinta", "galon"), ("fleco", "galon"), ("correajes", "ante"), ("corbatin", "cuero"),
    ("zapato", "cuero"), ("suelas", "cuero"), ("visera", "cuero"), ("gorro/detalles/interior", "cuero"),
    ("gorro/detalles/plumas", "pluma"), ("gorro/detalles/cuerpo", "pluma"), ("gorro/detalles/franja", "sarga"),
    ("kilt", "tartan"), ("medias", "sarga"), ("polainas", "sarga"),
    ("casaca", "pano"), ("hombreras", "pano"),
]


# paso10_relieve_3d.py: lo que se quita, lo que se suaviza y lo que se levanta de la textura. Medidas en pixeles de la textura, alturas en metros.
QUITAR = ("casaca/", "corbatin/", "kilt/", "medias/", "polainas/", "zapatos/", "gorro/", "hombreras/")
QUITAR_NOMBRES = ("legs", "euro_flask01", "euro_flask02", "euro_flask03")
SUAVES_RUTAS = ("correajes/",)
SUAVES_NOMBRES = ("hands", "heads")

BOTONES = [(24, y, 5.2) for y in (81, 111, 141, 170, 199, 229, 261, 292, 318)] + [(276, 326, 5), (206, 395, 5), (203.5, 463, 5), (247, 463, 5)] \
    + [(x, 264, 3.6) for x in (383, 404, 425, 445)]


def discos(forma, f=1):
    y, x = np.mgrid[0:forma[0] * f, 0:forma[1] * f].astype(np.float32)
    r = np.full((forma[0] * f, forma[1] * f), 9.0, np.float32)
    for cx, cy, ra in BOTONES:
        r = np.minimum(r, np.hypot((x + .5) / f - cx - .5, (y + .5) / f - cy - .5) / ra)
    return r


def en_uve(x, y):
    """El rojo entre los dos faldones: lo que queda por encima de su borde."""
    return (y < np.interp(x, (11, 65, 120, 165, 222), (339, 334, 352, 380, 472))) & (x < 305 - (y - 336) * .566)


def campo_galon(r, g, b, f):
    # senal continua, no mascara de 0 y 1: el contorno sale liso al subir de resolucion
    c = np.clip((g - .5) / .22, 0, 1) * np.clip((.2 - (r - b)) / .08, 0, 1)
    y, x = np.mgrid[0:r.shape[0], 0:r.shape[1]].astype(np.float32)
    def caja_(x0, y0, x1, y1):
        return (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
    zonas = caja_(10, 65, 65, 336) | caja_(257, 311, 308, 342) | caja_(309, 253, 512, 263) | caja_(372, 257, 456, 293) | caja_(311, 334, 512, 395)
    zonas |= caja_(160, 352, 241, 452) & en_uve(x, y)
    c = c * zonas
    return c


def m_galon(r, g, b, caja):
    return (campo_galon(r, g, b, 1) > .45) & (discos(r.shape) > 1.05)


def a_galon(m, f, dif, ampliar, desenfoque):
    c = ampliar(campo_galon(dif[..., 0], dif[..., 1], dif[..., 2], f), f)
    c = desenfoque(c, f * 1.1)
    # la orilla sube desde cero: sin escalon en el contorno. Lomo redondeado, como un cordon de lana
    d = np.clip((c - .4) / .28, 0, 1)
    return .0034 * np.sin(d * np.pi / 2) ** .8 * (discos(m.shape, f) > 1.02)


def m_boton(r, g, b, caja):
    return discos(r.shape) <= 1.05


def a_boton(m, f, dif, ampliar, desenfoque):
    d = discos(m.shape, f)
    # cupula baja con cerco y orilla redondeada: boton de peltre cosido
    orilla = np.clip((1 - d) / .14, 0, 1) ** .6
    return (.0028 + .0022 * np.sqrt(np.clip(1 - d ** 2, 0, 1)) + .0006 * np.exp(-((d - .78) / .07) ** 2)) * orilla * (d < 1) + .001 * orilla


def redondo(m, f, desenfoque, ampliar, h, s=1.0):
    d = np.clip(desenfoque((ampliar(m.astype(np.float32), f) > .5).astype(np.float32), f * s) * 2 - 1, 0, 1)
    return h * np.sin(d * np.pi / 2) ** .7


def m_faldon(r, g, b, caja):
    # el pano blanco vuelto de los faldones; la linea oscura pintada queda como una costura hundida
    y, x = np.mgrid[0:r.shape[0], 0:r.shape[1]].astype(np.float32)
    claro = desenfoque((((r - b) < .22) & (g > .42)).astype(np.float32), .6) > .5
    return claro & ~en_uve(x, y) & (y >= 333) & (y <= 480) & (x <= 306) & (discos(r.shape) > 1.05)


def a_faldon(m, f, dif, ampliar, desenfoque):
    # contorno liso: la mascara se difumina antes de cortarla
    M = (desenfoque(ampliar(m.astype(np.float32), f), f * 1.2) > .5).astype(np.float32)
    d = np.clip(desenfoque(M, f * 1.0) * 2 - 1, 0, 1)
    # lomo en la orilla, donde la tela da la vuelta
    orilla = np.clip((1 - desenfoque(M, f * 3.5)) * 2.4, 0, 1) * (M > .5)
    return (.0024 + .0017 * orilla) * np.sin(d * np.pi / 2) ** .7


def m_banda_puno(r, g, b, caja):
    return caja(r.shape, 315, 312, 505, 332)


def a_banda_puno(m, f, dif, ampliar, desenfoque):
    return redondo(m, f, desenfoque, ampliar, .0022)


def _rayas(t, paso, tramos):
    u = (t % paso) / paso
    sal = np.zeros(t.shape + (3,), np.float32)
    ini = 0.0
    for fin, col in tramos:
        sal[(u >= ini) & (u < fin)] = col
        ini = fin
    return sal


def pintar_legs(p, f, desenfoque):
    """Cuadros de las medias y tartan a alta resolucion; el juego solo los tenia borrosos."""
    y, x = np.mgrid[0:p.shape[0], 0:p.shape[1]].astype(np.float32)
    x, y = (x + .5) / f, (y + .5) / f
    # medias a dados rojos y blancos, como en el cuadro. En la textura, 1 px mide 1.17 mm a lo ancho y 2.8 mm a lo alto
    mx, my = x * 1.17, y * 2.8
    a, b = (mx + my) / 34, (mx - my) / 34
    da, db = a - np.floor(a), b - np.floor(b)
    par = (np.floor(a) + np.floor(b)) % 2
    borde = np.minimum(np.minimum(da, 1 - da), np.minimum(db, 1 - db))
    col = np.where(par[..., None] > .5, np.array((.56, .11, .09), np.float32), np.array((.76, .72, .63), np.float32))
    linea = np.clip((.035 - borde) / .015, 0, 1)[..., None]
    col = col * (1 - .55 * linea) + np.array((.2, .05, .05), np.float32) * .55 * linea
    media = (y >= 296) & (y <= 381) & (x <= 300)
    sal = p.copy()
    sal[media, :3] = col[media]
    # tartan Black Watch: azul, verde y lineas negras; los pliegues del juego quedan como sombra
    azul, verde, negro = (.062, .08, .15), (.055, .125, .09), (.018, .018, .02)
    sett = ((.28, azul), (.34, negro), (.4, azul), (.46, negro), (.72, verde), (.78, negro), (.84, azul), (.9, negro), (1.01, azul))
    t = (_rayas(x, 44, sett) + _rayas(y, 44, sett)) / 2
    kilt = ((x <= 317) & (y <= 157)) | ((x >= 272) & (x <= 372) & (y >= 378))
    lum = desenfoque(p[..., :3].mean(axis=2), 5 * f)
    luz = np.clip(lum / max(float(lum[kilt].mean()), 1e-3), .6, 1.2)
    # lana tejida a mano y meses de campana: hilos desiguales, tinte comido a parches, grasa y tierra
    rng = np.random.default_rng(7)
    hilos_x = rng.normal(0, 1, int(p.shape[1] / 2) + 2)[(x * f / 2).astype(int)]
    hilos_y = rng.normal(0, 1, int(p.shape[0] / 2) + 2)[(y * f / 2).astype(int)]
    forma = p.shape[:2]

    def parches(sg):
        n = desenfoque(rng.normal(0, 1, forma).astype(np.float32), sg * f)
        return n / max(float(n.std()), 1e-6)

    t = t * (1 + .055 * (hilos_x + hilos_y))[..., None]
    gris = t.mean(axis=2, keepdims=True)
    sol = np.clip(.5 + .45 * parches(38) + .2 * parches(11), 0, 1)[..., None]
    t = t * (1 - .5 * sol) + (gris * np.array((1.3, 1.18, .95), np.float32) + .012) * .5 * sol
    grasa = np.clip(.55 + .4 * parches(16) + .22 * parches(4), 0, 1)[..., None]
    t = t * (1 - .42 * grasa)
    tierra = np.clip(parches(9) * .5 + parches(2.5) * .25 - .35, 0, 1)[..., None]
    t = t * (1 - .55 * tierra) + np.array((.075, .06, .042), np.float32) * .55 * tierra
    sal[kilt, :3] = np.clip(t * luz[..., None] * 1.9, 0, 1)[kilt]
    return sal


def plisar_kilt(o):
    """Tablas de verdad: cuchillas por detras y a los lados, delantal casi liso. Salen de la cintura y se abren hacia el bajo."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    aristas = {e for f in bm.faces if f.material_index == 0 for e in f.edges}
    bmesh.ops.subdivide_edges(bm, edges=list(aristas), cuts=3, use_grid_fill=True)
    vs = {v for f in bm.faces if f.material_index == 0 for v in f.verts}
    arriba = max(v.co.z for v in vs)
    cy = sum(v.co.y for v in vs) / len(vs)
    for v in vs:
        x, y = v.co.x, v.co.y - cy
        fi = math.atan2(x, -y)
        # 0 en el frente del cuerpo; el delantal llega a unos 65 grados
        tablas = np.clip((abs(fi) - math.radians(62)) / math.radians(25), 0, 1)
        baja = np.clip((arriba - v.co.z - .26) / .16, 0, 1)
        t = (fi * 44 / (2 * math.pi)) % 1
        # sube despacio y cae de golpe: el perfil de una tabla planchada
        sierra = t / .82 - .5 if t < .82 else (1 - t) / .18 - .5
        d = .013 * sierra * tablas * baja * (.65 + .35 * baja)
        d += .0028 * math.sin(fi * 5 + 1) * baja * (1 - tablas)
        # la parte alta se mete bajo la casaca para no atravesar sus faldones
        d -= .02 * (1 - baja)
        r = max(math.hypot(x, y), 1e-6)
        v.co.x += x / r * d
        v.co.y += y / r * d
    bm.to_mesh(o.data)
    bm.free()
    o.data.shade_smooth()


def crear_polainas(o):
    """Polainas de lona blanca sobre el zapato: una capa propia con grosor, corte limpio arriba y sobre el empeine, arrugas en el tobillo y botones por fuera."""
    me = o.data.copy()
    pol = bpy.data.objects.new("polaina_lona", me)
    col_rel.objects.link(pol)
    bm = bmesh.new()
    bm.from_mesh(me)
    # medias, polainas y zapatos: las tres zonas que puede tapar
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index not in (1, 2, 3)], context="FACES")
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=3, use_grid_fill=True)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=(0, 0, .285), plane_no=(0, 0, 1), clear_outer=True)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    # como en el cuadro tapa casi todo el zapato: del talon (y .105, z .012) a junto a la puntera (y -.16, z .04)
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=(0, .105, .012), plane_no=(0, .106, 1), clear_inner=True)
    bm.normal_update()
    for v in bm.verts:
        ang = math.atan2(v.co.y - .04, abs(v.co.x) - .115)
        # lona arrugada: fuelle en el tobillo, pliegues sobre el empeine y otros mas suaves por la pierna
        arruga = .0026 * math.sin(v.co.z * 170 + 2.2 * math.sin(ang * 2)) * math.exp(-((v.co.z - .125) / .05) ** 2)
        arruga += .002 * math.sin(v.co.z * 240 + v.co.y * 90 + 1.5 * math.sin(ang * 3)) * math.exp(-((v.co.z - .05) / .03) ** 2)
        arruga += .0011 * math.sin(v.co.z * 75 + ang * 3 + 1.2 * math.sin(v.co.z * 31))
        v.co += v.normal * (.0014 + arruga)
    for f in bm.faces:
        f.material_index = 0
    arbol_pol = BVHTree.FromBMesh(bm)
    bm.to_mesh(me)
    bm.free()
    me.materials.clear()
    color_plano("lona_polaina", (.86, .84, .78))
    me.materials.append(material_cine("lona_polaina", "lona", bpy.data.images["cine_sarga"]))
    me.shade_smooth()
    pol.parent = arm
    pol["cine_ruta"] = "suave/polaina_lona"
    pol.modifiers.new("Armature", "ARMATURE").object = arm
    g = pol.modifiers.new("Grosor", "SOLIDIFY")
    g.thickness, g.offset, g.use_rim = .0028, 1, True
    pol.cycles.shadow_terminator_offset = .05
    visibilidad(pol, arbol)
    # botones en el lado de fuera de cada pierna
    sop = Soporte(pol, None)
    arbolkd = KDTree(len(sop.co))
    for i, c in enumerate(sop.co.tolist()):
        arbolkd.insert(c, i)
    arbolkd.balance()
    pos, caras, pesos = [], [], []
    for lado in (1, -1):
        for z in (.078, .118, .158, .198, .238, .272):
            cerca = sop.co[(np.abs(sop.co[:, 2] - z) < .012) & (sop.co[:, 0] * lado > 0)]
            hit = arbol_pol.ray_cast(Vector((lado * .4, float(cerca[:, 1].mean()) + .012, z)), Vector((-lado, 0, 0)), 1.0)
            if hit[0] is None:
                continue
            c, n = hit[0], hit[1]
            if n.x * lado < 0:
                n = -n
            t = n.cross(Vector((0, 0, 1))).normalized()
            u = n.cross(t)
            peso = sop.W[arbolkd.find(c)[1]]
            k = len(pos)
            aros = ((.0058, .0024), (.0058, .0042), (.0048, .0052), (.003, .0058), (.0001, .006))
            for r_, h_ in aros:
                for i in range(14):
                    a = i / 14 * 2 * math.pi
                    pos.append(c + t * (r_ * math.cos(a)) + u * (r_ * math.sin(a)) + n * h_)
                    pesos.append(peso)
            for j in range(len(aros) - 1):
                for i in range(14):
                    a0, a1 = k + j * 14 + i, k + j * 14 + (i + 1) % 14
                    caras.append((a0, a1, a1 + 14, a0 + 14))
    color_plano("boton_polaina", (.09, .08, .07))
    mat = material_cine("boton_polaina", "cuero", bpy.data.images["cine_cuero"])
    col_rel.objects.link(objeto_relieve("polaina_botones", np.array([list(x) for x in pos], np.float32), caras, np.array(pesos, np.float32), sop, arm, mat))
    print("POLAINAS", len(me.vertices), "vertices,", len(pos) // 70, "botones", flush=True)


def malla_cabeza(nombre, p, caras, mat, uv=None, hueso="Head"):
    """Objeto rigido sobre el hueso de la cabeza, con los atributos del material de cine."""
    me = bpy.data.meshes.new(nombre)
    me.from_pydata([tuple(x) for x in np.asarray(p, np.float64).tolist()], [], caras)
    me.update()
    me.shade_smooth()
    capa = me.uv_layers.new(name="UVMap")
    if uv is not None:
        # uv por vertice
        i = np.fromiter((l.vertex_index for l in me.loops), np.int64, len(me.loops))
        capa.data.foreach_set("uv", np.asarray(uv, np.float32)[i].ravel())
    me.materials.append(mat)
    me.attributes.new("cine_vis", "FLOAT", "FACE").data.foreach_set("value", np.ones(len(caras), np.float32))
    me.attributes.new("cine_p", "FLOAT_VECTOR", "POINT").data.foreach_set("vector", np.asarray(p, np.float32).ravel())
    o = bpy.data.objects.new(nombre, me)
    o.parent = arm
    o["cine_ruta"] = "suave/" + nombre
    o.modifiers.new("Armature", "ARMATURE").object = arm
    o.vertex_groups.new(name=hueso).add(list(range(len(me.vertices))), 1.0, "REPLACE")
    col_rel.objects.link(o)
    return o


def material_pluma(nombre, im, color, polvo):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    b = next(n for n in N if n.type == "BSDF_PRINCIPLED")
    t = N.new("ShaderNodeTexImage")
    t.image = im
    uv = N.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    L.new(uv.outputs[0], t.inputs[0])
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(uv.outputs[0], sep.inputs[0])
    # la raiz de cada pluma queda en sombra: da fondo a la masa
    fondo = N.new("ShaderNodeMapRange")
    L.new(sep.outputs[0], fondo.inputs[0])
    fondo.inputs[3].default_value, fondo.inputs[4].default_value = .35, 1.0
    att = N.new("ShaderNodeAttribute")
    att.attribute_name = "cine_p"
    ru = N.new("ShaderNodeTexNoise")
    L.new(att.outputs["Vector"], ru.inputs["Vector"])
    ru.inputs["Scale"].default_value = 22
    ma = N.new("ShaderNodeMapRange")
    L.new(ru.outputs["Fac"], ma.inputs[0])
    ma.inputs[1].default_value, ma.inputs[2].default_value = .5, .68
    ma.inputs[4].default_value = 1.0
    mz = N.new("ShaderNodeMix")
    mz.data_type = "RGBA"
    L.new(ma.outputs[0], mz.inputs[0])
    mz.inputs[6].default_value = (*color, 1)
    mz.inputs[7].default_value = (*polvo, 1)
    a = N.new("ShaderNodeVectorMath")
    a.operation = "SCALE"
    L.new(mz.outputs[2], a.inputs[0])
    L.new(fondo.outputs[0], a.inputs["Scale"])
    L.new(a.outputs[0], b.inputs["Base Color"])
    L.new(t.outputs["Alpha"], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = .62
    b.inputs["Specular IOR Level"].default_value = .25
    b.inputs["Sheen Weight"].default_value = .6
    b.inputs["Sheen Roughness"].default_value = .4
    L.new(a.outputs[0], b.inputs["Sheen Tint"])
    return m


def pelo(rng, raiz, nor, n_seg=4, sube=False, caida=.55, largos=(.04, .085), anchos=(.0022, .0042), tope=True, suelto=1.0, factor=None, rizado=0.0):
    """Pelos en cinta afilada, generados de golpe. raiz y nor: una fila por pelo."""
    n = len(raiz)
    t = rng.uniform(0, 2 * np.pi, n)
    z = raiz[:, 2]
    mech = np.sin(t * 2 + z * 40) + np.sin(raiz[:, 0] * 55 + raiz[:, 1] * 37)
    baja = np.array((0, 0, 1.0 if sube else -1.0), np.float32)
    lado = np.cross(nor, baja)
    lado /= np.maximum(np.linalg.norm(lado, axis=1, keepdims=True), 1e-6)
    d = nor * .8 + baja * caida + lado * ((mech * .3 + rng.normal(0, .3, n)) * suelto)[:, None] + rng.normal(0, .12 * suelto, (n, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    largo = rng.uniform(*largos, n)
    if factor is not None:
        largo = largo * factor
    # en el borde bajo el pelo acaba sobre la banda
    if tope and not sube:
        largo = np.minimum(largo, np.maximum(z - (1.85 - .1 * raiz[:, 1] + .05), 0) * 1.1 + .018)
    ancho = rng.uniform(*anchos, n)
    w = np.cross(d, nor)
    w /= np.maximum(np.linalg.norm(w, axis=1, keepdims=True), 1e-6)
    filas, q = [], raiz.copy()
    rizo = rng.normal(0, .16 * suelto, (n, 3))
    if rizado:
        # mismo giro para las hebras vecinas: forma rizos en vez de pelo liso
        fase = raiz * 150
        rizo = rizo + rizado * np.c_[np.sin(fase[:, 2] + fase[:, 1] * .7), np.sin(fase[:, 0] + fase[:, 2] * .6), np.sin(fase[:, 1] - fase[:, 0])]
    for i in range(n_seg + 1):
        f = 1 - i / n_seg
        filas.append(q - w * (ancho * f * .5)[:, None])
        filas.append(q + w * (ancho * f * .5)[:, None])
        d = d + baja * .16 + rizo
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        q = q + d * (largo / n_seg)[:, None]
    pos = np.stack(filas, axis=1).reshape(-1, 3)
    uv = np.tile(np.array([(i / n_seg, j) for i in range(n_seg + 1) for j in (0, 1)], np.float32), (n, 1))
    k = (n_seg + 1) * 2
    base = np.arange(n)[:, None, None] * k
    m = np.array([(2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1) for i in range(n_seg)])[None]
    caras = (base + m).reshape(-1, 4)
    return pos, caras.tolist(), uv


def crear_bonete():
    """Bonete de los Highlanders: banda a dados del cuadro de Gibb, masa alta de pelo negro con una caida al lado y plumero blanco, como en las fotos de la epoca."""
    rng = np.random.default_rng(21)
    cx, cy, rx, ry = 0.0, -.012, .09, .113

    def base_z(x, y):
        return 1.85 - .1 * y

    # banda a dados: ceñida a la frente, con su reborde
    h = 512
    fil, col_ = 3, 36
    y, x = np.mgrid[0:h, 0:h * 8].astype(np.float32)
    cx_, cy_ = np.floor(x / (h * 8) * col_), np.floor(y / h * fil)
    blanco, rojo, verde = np.array((.74, .71, .63), np.float32), np.array((.6, .1, .09), np.float32), np.array((.08, .2, .12), np.float32)
    par = (cx_ % 2).astype(bool)
    centro = (cy_ == 1)[..., None]
    pp = np.where(par[..., None], rojo, np.where(centro, rojo, blanco))
    pp = np.where(centro & par[..., None], verde, pp)
    img = np.ones((h, h * 8, 4), np.float32)
    img[..., :3] = pp * (.93 + .07 * rng.normal(0, 1, (h, h * 8, 1)).astype(np.float32))
    nueva_imagen("banda_dados_difusa", img, False)
    nueva_imagen("banda_dados_normal", np.ones((4, 4, 4), np.float32) * np.array((.5, .5, 1, 1), np.float32), True)
    mat_b = material_cine("banda_dados", "dados", bpy.data.images["cine_sarga"])
    M, K = 128, 10
    pos, caras, uvs = [], [], []
    for j in range(K + 1):
        s = j / K
        for i in range(M + 1):
            t = i / M * 2 * math.pi
            bulto = .004 * math.sin(s * math.pi) ** .6
            xx = cx + (rx + bulto) * math.cos(t)
            yy = cy + (ry + bulto) * math.sin(t)
            pos.append((xx, yy, base_z(xx, yy) + .058 * s))
            uvs.append((i / M, s))
    for j in range(K):
        for i in range(M):
            a = j * (M + 1) + i
            caras.append((a, a + 1, a + M + 2, a + M + 1))
    malla_cabeza("bonete_banda", pos, caras, mat_b, uvs)

    # fondo negro bajo las plumas: alto, ancho arriba, un poco caido hacia atras
    nb = bpy.data.images.new("bonete_negro", 4, 4)
    mat_f = bpy.data.materials.new("bonete_fondo")
    mat_f.use_nodes = True
    bs = next(n for n in mat_f.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bs.inputs["Base Color"].default_value = (.008, .008, .009, 1)
    bs.inputs["Roughness"].default_value = 1.0
    A, B = 96, 36

    def domo(a, b):
        """a: vuelta completa, b: 0 banda - 1 cima."""
        t = a * 2 * math.pi
        h_ = b * .32
        cierre = max(1 - b ** 3, 0) ** .5
        perf = math.sin(min(b * 1.4, 1) * math.pi * .5) ** .7
        ondas = 1 + .05 * math.sin(t * 3 + b * 5) + .035 * math.sin(t * 5 - b * 8)
        xx = cx - .012 * b + (rx * .96 + .058 * perf) * cierre * math.cos(t) * ondas
        yy = cy + .05 * b * b + (ry * .96 + .045 * perf) * cierre * math.sin(t) * ondas
        return np.array((xx, yy, base_z(cx, cy + ry * .96 * math.sin(t)) + .05 + h_))
    pos = [domo(i / A, j / B) for j in range(B + 1) for i in range(A + 1)]
    caras = [(j * (A + 1) + i, j * (A + 1) + i + 1, (j + 1) * (A + 1) + i + 1, (j + 1) * (A + 1) + i) for j in range(B) for i in range(A)]
    malla_cabeza("bonete_fondo", pos, caras, mat_f)

    # pelo sobre el fondo y sobre la caida del lado derecho del soldado, como en las fotos
    G = np.array([domo(i / 240, j / 90) for j in range(1, 91) for i in range(240)], np.float32)
    malla = G.reshape(90, 240, 3)
    du = np.roll(malla, -1, axis=1) - malla
    dv = np.gradient(malla, axis=0)
    area = np.linalg.norm(np.cross(du, dv), axis=2)
    nn = np.cross(du, dv)
    fuera = malla - np.array((cx, cy, 2.0), np.float32)
    nn *= np.where((nn * fuera).sum(axis=2, keepdims=True) < 0, -1, 1)
    nn /= np.maximum(np.linalg.norm(nn, axis=2, keepdims=True), 1e-9)
    prob = (area / area.sum()).ravel()
    elige = rng.choice(prob.size, 48000, p=prob)
    r1, n1 = malla.reshape(-1, 3)[elige], nn.reshape(-1, 3)[elige]
    u_, v_ = rng.uniform(0, 2 * np.pi, 16000), np.arccos(rng.uniform(-1, 1, 16000))
    uni = np.c_[np.sin(v_) * np.cos(u_), np.sin(v_) * np.sin(u_), np.cos(v_)].astype(np.float32)
    rad = np.array((.074, .082, .17), np.float32)
    cen = np.array((-.098, .05, 1.97), np.float32)
    r2, n2 = cen + uni * rad, uni / rad
    n2 /= np.linalg.norm(n2, axis=1, keepdims=True)
    # sin tapar la cara
    libre = ~((r2[:, 1] < -.02) & (r2[:, 2] < 1.9))
    p, c, uv = pelo(rng, np.r_[r1, r2[libre]], np.r_[n1, n2[libre]])
    blanco_im = nueva_imagen("pelo_opaco", np.ones((4, 4, 4), np.float32), False)
    mat_p = material_pluma("bonete_pelo_negro", blanco_im, (.009, .009, .01), (.045, .04, .036))
    mat_p.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = .4
    malla_cabeza("bonete_pelo", p, c, mat_p, uv)
    print("PELO", len(p) // 10, "pelos,", len(c), "caras", flush=True)
    # fondo de la caida
    A2, B2 = 32, 20
    pos = [cen + rad * .86 * np.array((math.sin(j / B2 * math.pi) * math.cos(i / A2 * 2 * math.pi), math.sin(j / B2 * math.pi) * math.sin(i / A2 * 2 * math.pi), math.cos(j / B2 * math.pi))) for j in range(B2 + 1) for i in range(A2 + 1)]
    caras = [(j * (A2 + 1) + i, j * (A2 + 1) + i + 1, (j + 1) * (A2 + 1) + i + 1, (j + 1) * (A2 + 1) + i) for j in range(B2) for i in range(A2)]
    malla_cabeza("bonete_caida", pos, caras, mat_f)

    # plumero blanco: hebras finas alrededor de un eje que sube por el costado y asoma sobre la cima
    n = 14000
    t_ = rng.uniform(0, 1, n) ** .8
    eje = np.array([domo(.075, .3 + .6 * x) + np.array((.06 - .025 * x, .03, .1 * x)) for x in np.linspace(0, 1, 60)], np.float32)
    q_ = eje[(t_ * 59).astype(int)]
    az = rng.uniform(0, 2 * np.pi, n)
    # plano como una pluma grande: mas ancho hacia atras que hacia los lados
    nor_ = np.c_[np.cos(az) * .55, np.sin(az), rng.uniform(.1, .9, n)].astype(np.float32)
    nor_ /= np.linalg.norm(nor_, axis=1, keepdims=True)
    ab = (.006 + .02 * np.sin(np.clip(t_, 0, 1) * np.pi) ** .6)[:, None]
    p, c, uv = pelo(rng, q_ + nor_ * ab * rng.uniform(0, 1, (n, 1)), nor_, sube=True)
    malla_cabeza("bonete_plumero", p, c, material_pluma("bonete_plumero_blanco", blanco_im, (.74, .72, .66), (.34, .31, .26)), uv)
    bpy.context.scene.cycles.transparent_max_bounces = 48
    print("BONETE listo", flush=True)


def crear_sporran():
    """Sporran de gala del cuadro: bolsa de pelo oscuro colgada de la cintura sobre el delantal del kilt, con seis borlas claras."""
    rng = np.random.default_rng(31)
    arriba, abajo = 1.075, .7

    def ante(x, z):
        # primer punto del cuerpo visto de frente
        h = arbol.ray_cast(Vector((x, -.6, z)), Vector((0, 1, 0)), 1.2)
        return h[0].y if h[0] else -.12

    def ancho(s_):
        ancho_ = .082 + .038 * s_
        return ancho_ * max(1 - max((s_ - .82) / .18, 0) ** 2.4, 0) ** .5

    def perfil(x, z):
        # el cuerpo por detras queda liso aunque el kilt tenga pliegues: se toma lo mas saliente de la zona
        return min(ante(x + dx, max(z, .68)) for dx in (-.03, 0, .03))

    NU, NV = 24, 40
    pos = []
    for j in range(NV + 1):
        s_ = j / NV
        z = arriba + (abajo - arriba) * s_
        w = max(ancho(s_), .002)
        for i in range(NU + 1):
            t = i / NU * 2 - 1
            x = t * w
            bulto = .017 * (1 - t * t) ** .5 * math.sin(min(s_ * 1.15 + .12, 1) * math.pi) ** .5
            pos.append((x, perfil(x, z) - .005 - bulto, z))
    pos = np.array(pos, np.float32)
    caras = [(j * (NU + 1) + i, j * (NU + 1) + i + 1, (j + 1) * (NU + 1) + i + 1, (j + 1) * (NU + 1) + i) for j in range(NV) for i in range(NU)]
    fondo = bpy.data.materials["bonete_fondo"]
    malla_cabeza("sporran_bolsa", pos, caras, fondo, hueso="Hips")

    # pelo por toda la bolsa, cayendo
    malla = pos.reshape(NV + 1, NU + 1, 3)
    du, dv = np.gradient(malla, axis=1), np.gradient(malla, axis=0)
    nn = np.cross(du, dv)
    nn *= np.where(nn[..., 1:2] > 0, -1, 1)
    area = np.linalg.norm(nn, axis=2)
    nn /= np.maximum(area[..., None], 1e-9)
    elige = rng.choice(area.size, 16000, p=(area / area.sum()).ravel())
    r_ = malla.reshape(-1, 3)[elige] + rng.normal(0, .002, (16000, 3)).astype(np.float32)
    n_ = nn.reshape(-1, 3)[elige]
    p, c, uv = pelo(rng, r_, n_, caida=2.4, largos=(.035, .065), anchos=(.0014, .0028), tope=False, suelto=.45)
    im = bpy.data.images["pelo_opaco"]
    malla_cabeza("sporran_pelo", p, c, material_pluma("sporran_pelo_oscuro", im, (.014, .014, .016), (.045, .042, .04)), uv, hueso="Hips")

    # borlas: remate oscuro y un manojo de hebras claras
    sitios = ((-.054, 1.0), (.054, 1.0), (-.064, .89), (.064, .89), (-.04, .785), (.04, .785))
    cap_p, cap_c, raices, normales = [], [], [], []
    for x, z in sitios:
        cen = np.array((x, float(perfil(x, z)) - .042, z), np.float32)
        k = len(cap_p)
        aros = ((.002, .022), (.0065, .018), (.0095, .01), (.0105, .002), (.0098, -.005), (.0085, -.009))
        for r0, dz in aros:
            for i in range(14):
                a = i / 14 * 2 * math.pi
                cap_p.append(cen + np.array((r0 * math.cos(a), r0 * math.sin(a), dz), np.float32))
        for j in range(len(aros) - 1):
            for i in range(14):
                cap_c.append((k + j * 14 + i, k + j * 14 + (i + 1) % 14, k + (j + 1) * 14 + (i + 1) % 14, k + (j + 1) * 14 + i))
        az = rng.uniform(0, 2 * np.pi, 1300)
        rr = rng.uniform(0, 1, 1300) ** .5 * .0085
        raices.append(np.c_[np.cos(az) * rr, np.sin(az) * rr, np.full(1300, -.007)] + cen)
        normales.append(np.c_[np.cos(az), np.sin(az), np.zeros(1300)])
    malla_cabeza("sporran_remates", cap_p, cap_c, fondo, hueso="Hips")
    p, c, uv = pelo(rng, np.vstack(raices).astype(np.float32), np.vstack(normales).astype(np.float32), caida=4.5, largos=(.08, .112), anchos=(.0016, .0028), tope=False, suelto=.22)
    malla_cabeza("sporran_borlas", p, c, material_pluma("sporran_borla_clara", im, (.74, .71, .62), (.36, .33, .27)), uv, hueso="Hips")

    # boca de cuero y correas que suben bajo la casaca
    cuero = next(m for m in bpy.data.materials if m.name.startswith("zapato_negro_cine_cuero"))
    pos, caras = [], []
    for i in range(33):
        t = i / 32 * 2 - 1
        x = t * .088
        z = arriba + .004 + .012 * (1 - t * t)
        yf = float(perfil(x, arriba)) - .012
        for j in range(8):
            a = j / 8 * 2 * math.pi
            pos.append((x, yf + .007 * math.cos(a), z + .01 * math.sin(a)))
    for i in range(32):
        for j in range(8):
            caras.append((i * 8 + j, i * 8 + (j + 1) % 8, (i + 1) * 8 + (j + 1) % 8, (i + 1) * 8 + j))
    malla_cabeza("sporran_cuero", pos, caras, cuero, hueso="Hips")

    # colgador: dos correas blancas en V, de las esquinas de la bolsa a la cintura, por debajo del borde de la casaca
    color_plano("colgador", (.78, .75, .67))
    mat_c = material_cine("colgador", "ante", bpy.data.images["cine_pano"])
    pos, caras = [], []
    N, M = 22, 8
    for lado in (1, -1):
        k = len(pos)
        for i in range(N + 1):
            f = i / N
            x = lado * (.09 + .078 * f ** 1.25)
            z = arriba + .012 + .043 * f ** .85
            # sobre el kilt y, en el ultimo tramo, hacia dentro para acabar bajo la casaca
            yy = ante(x, min(z, 1.085)) - .0045 + .018 * max((f - .78) / .22, 0) ** 2
            fx = lado * .078 * 1.25 * max(f, .001) ** .25
            fz = .043 * .85 * max(f, .001) ** -.15
            tn = math.hypot(fx, fz)
            ax, az = -fz / tn, fx / tn
            for j in range(M):
                a = j / M * 2 * math.pi
                pos.append((x + ax * .0075 * math.cos(a), yy + .0022 * math.sin(a), z + az * .0075 * math.cos(a)))
        for i in range(N):
            for j in range(M):
                caras.append((k + i * M + j, k + i * M + (j + 1) % M, k + (i + 1) * M + (j + 1) % M, k + (i + 1) * M + j))
    malla_cabeza("sporran_colgador", pos, caras, mat_c, hueso="Hips")
    # anillas de laton que unen cada correa a la bolsa
    color_plano("anilla_laton", (.62, .5, .22))
    mat_a = material_cine("anilla_laton", "peltre", bpy.data.images["cine_metal"])
    pos, caras = [], []
    for lado in (1, -1):
        k = len(pos)
        cx_, cz_ = lado * .09, arriba + .012
        cy_ = float(perfil(cx_, arriba)) - .012
        for i in range(24):
            a = i / 24 * 2 * math.pi
            for j in range(8):
                b_ = j / 8 * 2 * math.pi
                r0 = .0095 + .0022 * math.cos(b_)
                pos.append((cx_ + r0 * math.cos(a), cy_ + .0022 * math.sin(b_), cz_ + r0 * math.sin(a)))
        for i in range(24):
            for j in range(8):
                caras.append((k + i * 8 + j, k + i * 8 + (j + 1) % 8, k + (i + 1) % 24 * 8 + (j + 1) % 8, k + (i + 1) % 24 * 8 + j))
    malla_cabeza("sporran_anillas", pos, caras, mat_a, hueso="Hips")
    print("SPORRAN listo", flush=True)


def crear_doblez_media():
    """La media vuelta hacia abajo sobre si misma, con su borde redondo y su grosor, y la borla roja que asoma debajo, por fuera de cada pierna."""
    rng = np.random.default_rng(41)
    legs = bpy.data.objects["suave_legs"]
    medias = next(i for i, m in enumerate(legs.data.materials) if "cuadros" in m.name)
    piel = next(i for i, m in enumerate(legs.data.materials) if m.name.startswith("legs"))
    arriba_d, abajo_d = .492, .405
    me = legs.data.copy()
    o = bpy.data.objects.new("media_doblez", me)
    col_rel.objects.link(o)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index not in (medias, piel)], context="FACES")
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=2, use_grid_fill=True)
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-5, plane_co=(0, 0, arriba_d), plane_no=(0, 0, 1), clear_outer=True)
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-5, plane_co=(0, 0, abajo_d), plane_no=(0, 0, 1), clear_inner=True)
    bm.normal_update()
    for v in bm.verts:
        f = (arriba_d - v.co.z) / (arriba_d - abajo_d)
        a = math.atan2(v.co.y - .03, abs(v.co.x) - .115)
        # arriba cierra contra la pierna en curva; abajo queda holgada y con el borde caido a tramos
        hueco = .0065 * math.sin(min(f * 3.2, 1) * math.pi / 2) ** .6 + .0022 * f
        arruga = .0011 * math.sin(a * 9 + f * 3) * f
        v.co += v.normal * (hueco + arruga)
        v.co.z -= .005 * f ** 3 * (1 + math.sin(a * 3 + 1))
    for f in bm.faces:
        f.material_index = 0
    bm.to_mesh(me)
    bm.free()
    mat_m = legs.data.materials[medias]
    me.materials.clear()
    me.materials.append(mat_m)
    me.shade_smooth()
    o.parent = arm
    o["cine_ruta"] = "suave/media_doblez"
    o.modifiers.new("Armature", "ARMATURE").object = arm
    g = o.modifiers.new("Grosor", "SOLIDIFY")
    g.thickness, g.offset, g.use_rim = .003, 1, True
    o.cycles.shadow_terminator_offset = .05
    visibilidad(o, arbol)

    # borla roja: nudo pequeno y un manojo largo de hebras, que llega casi hasta la polaina
    color_plano("borla_roja", (.5, .09, .08))
    mat_nudo = material_cine("borla_roja", "cordon", bpy.data.images["cine_sarga"])
    mat_hebra = material_pluma("borla_roja_hebras", bpy.data.images["pelo_opaco"], (.42, .05, .045), (.2, .035, .03))
    arbol_l = BVHTree.FromObject(legs, bpy.context.evaluated_depsgraph_get())
    co = np.empty(len(legs.data.vertices) * 3, np.float32)
    legs.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    for lado in (1, -1):
        hit = arbol_l.ray_cast(Vector((lado * .5, .025, abajo_d + .006)), Vector((-lado, 0, 0)), 1.0)
        c0 = np.array(hit[0], np.float32) + np.array((lado * .016, 0, 0), np.float32)
        # sigue al hueso de la espinilla mas cercano
        cerca = int(np.argmin(((co - c0) ** 2).sum(axis=1)))
        grupos = sorted(legs.data.vertices[cerca].groups, key=lambda x: -x.weight)
        hueso = legs.vertex_groups[grupos[0].group].name
        pos, caras = [], []
        aros = ((.001, .012), (.0055, .0095), (.0078, .004), (.0085, -.002), (.0075, -.007), (.0088, -.01))
        for r0, dz in aros:
            for i in range(14):
                a = i / 14 * 2 * math.pi
                pos.append(c0 + np.array((r0 * math.cos(a), r0 * math.sin(a), dz), np.float32))
        for j in range(len(aros) - 1):
            for i in range(14):
                caras.append((j * 14 + i, j * 14 + (i + 1) % 14, (j + 1) * 14 + (i + 1) % 14, (j + 1) * 14 + i))
        malla_cabeza(f"borla_nudo_{'D' if lado > 0 else 'I'}", pos, caras, mat_nudo, hueso=hueso)
        n = 2600
        az = rng.uniform(0, 2 * np.pi, n)
        rr = rng.uniform(0, 1, n) ** .5 * .0085
        raices = np.c_[np.cos(az) * rr, np.sin(az) * rr, np.full(n, -.008)].astype(np.float32) + c0
        nors = np.c_[np.cos(az), np.sin(az), np.zeros(n)].astype(np.float32)
        p, c, uv = pelo(rng, raices, nors, caida=5.0, largos=(.095, .125), anchos=(.0016, .0028), tope=False, suelto=.2)
        malla_cabeza(f"borla_hebras_{'D' if lado > 0 else 'I'}", p, c, mat_hebra, uv, hueso=hueso)
        print("BORLA", lado, hueso, [round(float(x), 3) for x in c0], flush=True)


def crear_bandas():
    """Banda blanca del hombro izquierdo con su insignia de laton, y faja roja de otra tela y con pliegues en la otra diagonal, como en el cuadro."""
    # cada banda venia con dos capas casi iguales: una sola, que el grosor lo da el modificador
    for n in ("correajes_D_02", "correajes_D_04", "correajes_I_02", "correajes_I_04"):
        bpy.data.objects.remove(bpy.data.objects[n])
    color_plano("banda_blanca_tela", (.84, .82, .75))
    mat_b = material_cine("banda_blanca_tela", "banda_blanca", bpy.data.images["cine_pano"])
    color_plano("faja_roja_tela", (.43, .05, .06))
    mat_r = material_cine("faja_roja_tela", "faja", bpy.data.images["cine_sarga"])
    # las dos bandas se ajustan a la casaca: sin puntas sueltas en la cadera, y la blanca pasa por encima de la faja
    torso = BVHTree.FromObject(bpy.data.objects["suave_torsos"], bpy.context.evaluated_depsgraph_get())

    def ajustar(v, alto_):
        h = torso.find_nearest(v.co)
        if h[0] is not None:
            nor = h[1] if h[1].dot(h[0] - Vector((0, h[0].y * .2, h[0].z))) > 0 else -h[1]
            v.co = h[0] + nor * alto_

    for n in ("correajes_I_01", "correajes_I_03"):
        o = bpy.data.objects[n]
        o.data.materials[0] = mat_b
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=3, use_grid_fill=True)
        for v in bm.verts:
            cruce = np.clip((.11 - abs(v.co.x)) / .05, 0, 1)
            ajustar(v, .0065 + .0065 * cruce)
        bm.to_mesh(o.data)
        bm.free()
        o.data.shade_smooth()
    for n in ("correajes_D_01", "correajes_D_03"):
        o = bpy.data.objects[n]
        o.data.materials[0] = mat_r
        o.modifiers["Grosor"].thickness = .002
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=7, use_grid_fill=True)
        for v in bm.verts:
            ajustar(v, .0052)
        bm.normal_update()
        alto = max(bm.verts, key=lambda v: v.co.z).co.copy()
        bajo = min(bm.verts, key=lambda v: v.co.z).co.copy()
        eje = (alto - bajo).normalized()
        # una sola direccion para toda la pieza: los pliegues corren rectos a lo largo de la faja
        media = sum((v.normal for v in bm.verts), Vector()).normalized()
        cruz = eje.cross(media).normalized()
        for v in bm.verts:
            u = (v.co - bajo).dot(cruz)
            t = (v.co - bajo).dot(eje)
            onda = math.sin(u * 2 * math.pi / .032 + .7 * math.sin(t * 5)) + .25 * math.sin(u * 2 * math.pi / .013 + 1.2 * math.sin(t * 3))
            v.co += v.normal * (.0013 + .0021 * onda)
        bm.to_mesh(o.data)
        bm.free()
        o.data.shade_smooth()
    # insignia sobre la banda blanca, donde se cruza con la faja
    blanca = bpy.data.objects["correajes_I_01"]
    arbol_b = BVHTree.FromPolygons([v.co.copy() for v in blanca.data.vertices], [list(p.vertices) for p in blanca.data.polygons])
    zs = [z for z in np.arange(1.3, 1.7, .004) if arbol_b.ray_cast(Vector((0, -.8, float(z))), Vector((0, 1, 0)))[0] is not None]
    zc = float(np.mean(zs))
    hit = arbol_b.ray_cast(Vector((0, -.8, zc)), Vector((0, 1, 0)))
    c0, n0 = np.array(hit[0], np.float32), np.array(hit[1], np.float32)
    if n0[1] > 0:
        n0 = -n0
    der = np.cross(np.array((0, 0, 1.0), np.float32), n0)
    der /= np.linalg.norm(der)
    arr = np.cross(n0, der)
    A, R = 128, 40
    rx, rz = .026, .033
    pos, caras = [], []
    for j in range(R + 1):
        r_ = j / R
        for i in range(A):
            t = i / A * 2 * math.pi
            # cerco, campo hundido, estrella de ocho puntas y boton central
            cerco = .0009 * math.exp(-((r_ - .9) / .055) ** 2)
            estrella = .0014 * np.clip((.74 * (.5 + .5 * abs(math.cos(4 * t))) ** 2.2 + .12 - r_) / .05, 0, 1)
            boton = .0012 * np.clip((.2 - r_) / .05, 0, 1) ** .6
            h = .0012 + cerco + estrella + boton
            h *= np.clip((1 - r_) / .05, 0, 1) ** .5
            pos.append(c0 + der * (r_ * rx * math.cos(t)) + arr * (r_ * rz * math.sin(t)) + n0 * (.0038 + h))
    for j in range(R):
        for i in range(A):
            caras.append((j * A + i, j * A + (i + 1) % A, (j + 1) * A + (i + 1) % A, (j + 1) * A + i))
    grupos = sorted(blanca.data.vertices[blanca.data.polygons[hit[2]].vertices[0]].groups, key=lambda x: -x.weight)
    hueso = blanca.vertex_groups[grupos[0].group].name
    color_plano("insignia_laton", (.66, .52, .22))
    mat_i = material_cine("insignia_laton", "peltre", bpy.data.images["cine_metal"])
    malla_cabeza("banda_insignia", np.array(pos, np.float32), caras, mat_i, hueso=hueso)
    print("BANDAS insignia en", c0.round(3).tolist(), "hueso", hueso, flush=True)


def crear_hombros():
    """Hombros del cuadro: rollo blanco acolchado sobre la costura del hombro, tirilla con dos cordones hasta el cuello y vivo blanco que baja por la sisa."""
    torso = bpy.data.objects["suave_torsos"]
    me = torso.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    bvh = BVHTree.FromPolygons([tuple(x) for x in co.tolist()], [list(f.vertices) for f in me.polygons])
    sop = Soporte(torso, None)
    kd = KDTree(len(co))
    for i, c in enumerate(co.tolist()):
        kd.insert(c, i)
    kd.balance()
    xs = .262
    color_plano("hombro_blanco", (.8, .78, .71))
    mat_w = material_cine("hombro_blanco", "banda_blanca", bpy.data.images["cine_pano"])
    color_plano("hombro_cordon", (.86, .84, .77))
    mat_c = material_cine("hombro_cordon", "cordon", bpy.data.images["cine_sarga"])

    def seccion(lado):
        sel = co[(co[:, 0] * lado > xs - .012) & (co[:, 0] * lado < xs + .012)]
        return Vector((lado * xs, float((sel[:, 1].min() + sel[:, 1].max()) / 2), float((sel[:, 2].min() + sel[:, 2].max()) / 2)))

    def en_sisa(lado, fi, centro):
        # fi = 0 arriba del hombro; negativo hacia el frente
        d = Vector((0, math.sin(fi), math.cos(fi)))
        h = bvh.ray_cast(centro + d * .4, -d, .5)
        return (h[0], d) if h[0] is not None else (None, d)

    def tubo(camino, medio_a, medio_b, N=12):
        """Tubo eliptico por una lista de (punto, direccion hacia fuera, a lo ancho); el ancho puede variar con la posicion."""
        p, c = [], []
        for i, (q, fuera, ancho_v) in enumerate(camino):
            f = i / (len(camino) - 1)
            remate = max(min(f, 1 - f) / .1, 0)
            k = min(remate, 1) ** .5
            for j in range(N):
                a = j / N * 2 * math.pi
                p.append(q + ancho_v * (medio_a * k * math.cos(a)) + fuera * (medio_b * k * (math.sin(a) + 1)))
        for i in range(len(camino) - 1):
            for j in range(N):
                c.append((i * N + j, i * N + (j + 1) % N, (i + 1) * N + (j + 1) % N, (i + 1) * N + j))
        return p, c

    def guarda(nombre, partes, mat):
        pos, caras = [], []
        for p, c in partes:
            k = len(pos)
            pos += [tuple(x) for x in p]
            caras += [tuple(i + k for i in f) for f in c]
        pes = np.array([sop.W[kd.find(x)[1]] for x in pos], np.float32)
        col_rel.objects.link(objeto_relieve(nombre, np.array(pos, np.float32), caras, pes, sop, arm, mat))
        print("HOMBRO", nombre, len(pos), "vertices", flush=True)

    rollos, cordones = [], []
    for lado in (1, -1):
        centro = seccion(lado)
        ancho_x = Vector((1, 0, 0))
        # rollo: de delante a detras por encima de la costura
        camino = []
        for i in range(49):
            fi = math.radians(-96 + 192 * i / 48)
            q, d = en_sisa(lado, fi, centro)
            if q is not None:
                camino.append((q + d * .001, d, ancho_x))
        rollos.append(tubo(camino, .022, .0075))
        # vivo de la sisa: sigue bajando desde cada punta del rollo
        for ini, fin in ((-84, -146), (84, 146)):
            camino = []
            for i in range(25):
                fi = math.radians(ini + (fin - ini) * i / 24)
                q, d = en_sisa(lado, fi, centro + Vector((-lado * .012, 0, 0)))
                if q is not None:
                    camino.append((q, d, ancho_x))
            cordones.append(tubo(camino, .0028, .0016, 8))
        # tirilla: dos cordones del cuello al rollo, por lo alto del hombro
        for ds in (-.021, .021):
            camino = []
            for i in range(31):
                x = lado * (.082 + (xs - .082 - .016) * i / 30)
                y = centro.y + ds
                h = bvh.ray_cast(Vector((x, y, 2.2)), Vector((0, 0, -1)), 1.2)
                if h[0] is not None:
                    n = h[1] if h[1].z > 0 else -h[1]
                    camino.append((h[0], n, Vector((0, 1, 0))))
            cordones.append(tubo(camino, .0034, .002, 8))
        print("SISA", lado, [round(x, 3) for x in centro], flush=True)
    guarda("hombro_rollo", rollos, mat_w)
    guarda("hombro_cordones", cordones, mat_c)


def _campana(x, z, x0, z0, sx, sz):
    return np.exp(-((x - x0) / sx) ** 2 - ((z - z0) / sz) ** 2)


def _tramo(x, z, a, b, ancho):
    """Cercania a un segmento (x, z), para surcos."""
    a, b = np.array(a), np.array(b)
    d = b - a
    t = np.clip(((x - a[0]) * d[0] + (z - a[1]) * d[1]) / d.dot(d), 0, 1)
    return np.exp(-(np.hypot(x - a[0] - t * d[0], z - a[1] - t * d[1]) / ancho) ** 2)


def _a_lineal(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)


OJO = (.034, 1.815)


def _almendra(ax, z):
    """Distancia normalizada al borde del ojo: 1 en el borde. ax es la x en valor absoluto."""
    dx = ax - OJO[0]
    dz = z - OJO[1] + .05 * dx
    alto = np.where(dz > 0, .0037, .0033)
    return np.sqrt((dx / .0138) ** 2 + (dz / alto) ** 2)


def material_piel(nombre, surcos):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    b = next(n for n in N if n.type == "BSDF_PRINCIPLED")
    att = N.new("ShaderNodeAttribute")
    att.attribute_name = "cine_p"
    col = N.new("ShaderNodeAttribute")
    col.attribute_name = "piel"
    # manchas muy finas y poros: la piel no es de un solo tono
    finas = N.new("ShaderNodeTexNoise")
    L.new(att.outputs["Vector"], finas.inputs["Vector"])
    finas.inputs["Scale"].default_value, finas.inputs["Detail"].default_value = 420, 6
    tono = N.new("ShaderNodeMapRange")
    L.new(finas.outputs["Fac"], tono.inputs[0])
    tono.inputs[1].default_value, tono.inputs[2].default_value = .3, .7
    tono.inputs[3].default_value, tono.inputs[4].default_value = .86, 1.1
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(att.outputs["Vector"], sep.inputs[0])
    cu = N.new("ShaderNodeMath")
    cu.operation = "MULTIPLY_ADD"
    L.new(sep.outputs["X"], cu.inputs[0])
    cu.inputs[1].default_value, cu.inputs[2].default_value = 5.0, .5
    cv = N.new("ShaderNodeMath")
    cv.operation = "MULTIPLY_ADD"
    L.new(sep.outputs["Z"], cv.inputs[0])
    cv.inputs[1].default_value, cv.inputs[2].default_value = 4.0, -6.64
    jn = N.new("ShaderNodeCombineXYZ")
    L.new(cu.outputs[0], jn.inputs["X"])
    L.new(cv.outputs[0], jn.inputs["Y"])
    tx = N.new("ShaderNodeTexImage")
    tx.image = surcos
    tx.extension = "EXTEND"
    L.new(jn.outputs[0], tx.inputs[0])
    spl = N.new("ShaderNodeSeparateColor")
    L.new(tx.outputs[0], spl.inputs[0])
    oscuro = N.new("ShaderNodeMath")
    oscuro.operation = "MULTIPLY"
    L.new(tono.outputs[0], oscuro.inputs[0])
    L.new(spl.outputs[1], oscuro.inputs[1])
    esc = N.new("ShaderNodeVectorMath")
    esc.operation = "SCALE"
    L.new(col.outputs["Color"], esc.inputs[0])
    L.new(oscuro.outputs[0], esc.inputs["Scale"])
    L.new(esc.outputs[0], b.inputs["Base Color"])
    b.inputs["Subsurface Weight"].default_value = .2
    b.inputs["Subsurface Radius"].default_value = (1.0, .35, .18)
    b.inputs["Subsurface Scale"].default_value = .005
    b.inputs["Specular IOR Level"].default_value = .42
    rug = N.new("ShaderNodeMapRange")
    L.new(finas.outputs["Fac"], rug.inputs[0])
    rug.inputs[1].default_value, rug.inputs[2].default_value = .3, .7
    rug.inputs[3].default_value, rug.inputs[4].default_value = .44, .66
    L.new(rug.outputs[0], b.inputs["Roughness"])
    poro = N.new("ShaderNodeTexNoise")
    L.new(att.outputs["Vector"], poro.inputs["Vector"])
    poro.inputs["Scale"].default_value, poro.inputs["Detail"].default_value = 2600, 3
    arr = N.new("ShaderNodeTexNoise")
    L.new(att.outputs["Vector"], arr.inputs["Vector"])
    arr.inputs["Scale"].default_value, arr.inputs["Detail"].default_value = 140, 5
    suma = N.new("ShaderNodeMath")
    suma.operation = "ADD"
    pz = N.new("ShaderNodeMath")
    pz.operation = "SUBTRACT"
    L.new(poro.outputs["Fac"], pz.inputs[0])
    gr = N.new("ShaderNodeMath")
    gr.operation = "MULTIPLY"
    L.new(spl.outputs[0], gr.inputs[0])
    # los surcos ya son geometria: el bump solo afila el fondo del pliegue
    gr.inputs[1].default_value = .6
    L.new(gr.outputs[0], pz.inputs[1])
    L.new(pz.outputs[0], suma.inputs[0])
    mu = N.new("ShaderNodeMath")
    mu.operation = "MULTIPLY"
    L.new(arr.outputs["Fac"], mu.inputs[0])
    mu.inputs[1].default_value = 1.6
    L.new(mu.outputs[0], suma.inputs[1])
    bp = N.new("ShaderNodeBump")
    bp.inputs["Distance"].default_value = .0009
    bp.inputs["Strength"].default_value = .75
    L.new(suma.outputs[0], bp.inputs["Height"])
    L.new(bp.outputs[0], b.inputs["Normal"])
    return m


def imagen_ojo(rng):
    n = 1024
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    dx, dy = (x - n / 2 + .5) / (n / 2), (y - n / 2 + .5) / (n / 2)
    r = np.hypot(dx, dy)
    a = np.arctan2(dy, dx)
    p = np.ones((n, n, 4), np.float32)
    # esclerotica con venillas hacia el borde
    ven = desenfoque(rng.normal(0, 1, (n, n)).astype(np.float32), 3)
    ven = np.abs(ven / ven.std())
    # hacia los lagrimales y las comisuras: mas venas y un tono rosado; un blanco puro delata el 3D
    esquina = np.clip((np.abs(dx) - .3) / .5, 0, 1) * np.clip((r - .25) / .3, 0, 1)
    venas = np.clip((.12 - ven) / .12, 0, 1) * np.clip((r - .2) / .3, 0, 1) * (.35 + .5 * esquina)
    base = np.array((.6, .55, .5), np.float32)[None, None] * np.ones((n, n, 1), np.float32)
    base = base * (1 - .55 * esquina[..., None] ** 1.5) + np.array((.58, .36, .32), np.float32) * .55 * esquina[..., None] ** 1.5
    # junto al iris la esclerotica se oscurece un poco (anillo limbal difuso)
    base *= (1 - .18 * np.clip((.24 - r) / .07, 0, 1))[..., None]
    base = base * (1 - venas[..., None]) + np.array((.55, .2, .16), np.float32) * venas[..., None]
    # iris azul grisaceo, con fibras radiales
    fib = desenfoque(rng.normal(0, 1, (n, n)).astype(np.float32), 1.2)
    fib = .5 + .5 * np.sin(a * 90 + fib * 9) * .5 + .25 * np.sin(a * 37 + r * 22)
    ir = np.array((.15, .21, .25), np.float32)[None, None] * (.5 + .75 * fib)[..., None]
    ir = ir + np.array((.2, .13, .04), np.float32) * np.clip((.085 - r) / .03, 0, 1)[..., None] * .5
    ir *= (1 - .8 * np.clip((r - .135) / .03, 0, 1))[..., None]
    filo = np.clip((.168 - r) / .008, 0, 1)[..., None]
    p[..., :3] = base * (1 - filo) + ir * filo
    pupila = np.clip((.058 - r) / .006, 0, 1)[..., None]
    p[..., :3] = p[..., :3] * (1 - pupila) + .004 * pupila
    return nueva_imagen("ojo_iris", np.clip(p, 0, 1), False)


def imagen_surcos(rng):
    """Arrugas vistas de frente, de x -.1 a .1 y z 1.66 a 1.91, un decimo de mm por pixel. R = hondura, G = oscurecido por la suciedad."""
    h, w = 2500, 2000
    fz = np.linspace(1.91, 1.66, h, dtype=np.float32)[:, None]
    fx = np.linspace(-.1, .1, w, dtype=np.float32)[None, :]
    surco = np.zeros((h, w), np.float32)

    def linea(puntos, ancho, fuerza):
        puntos = np.array(puntos, np.float32)
        for lado in (1, -1):
            for a, b in zip(puntos, puntos[1:]):
                a2, b2 = a * (lado, 1), b * (lado, 1)
                # irregular en cada lado de la cara
                a2 = a2 + rng.normal(0, .00035, 2)
                b2 = b2 + rng.normal(0, .00035, 2)
                d = b2 - a2
                t = np.clip(((fx - a2[0]) * d[0] + (fz - a2[1]) * d[1]) / d.dot(d), 0, 1)
                dist = np.hypot(fx - a2[0] - t * d[0], fz - a2[1] - t * d[1])
                surco[:] = np.maximum(surco, fuerza * np.exp(-(dist / ancho) ** 2))

    def onda(z0, x0, x1, amp, k, ancho, fuerza):
        xs = np.linspace(x0, x1, 14)
        linea([(q, z0 + amp * math.sin(q * k)) for q in xs], ancho, fuerza)

    # frente
    for z0, f in ((1.8445, .45), (1.8515, .6), (1.8585, .45)):
        onda(z0, .004, .058, .0016, 70, .00055, f)
    # entrecejo
    linea([(.0052, 1.8275), (.0068, 1.8345), (.0085, 1.8405)], .0007, 1.0)
    linea([(.0115, 1.8295), (.0135, 1.836)], .0005, .55)
    # patas de gallo
    for fin in ((.0625, 1.8215), (.0645, 1.8145), (.0625, 1.808)):
        linea([(.052, 1.8135), fin], .0007, .45)
    # bajo el ojo y sobre el pomulo
    linea([(.017, 1.8045), (.03, 1.7985), (.045, 1.7995), (.056, 1.804)], .0007, .95)
    linea([(.022, 1.798), (.036, 1.7925), (.052, 1.795)], .0006, .6)
    # parpado superior, junto al pliegue
    linea([(.021, 1.8215), (.034, 1.8245), (.05, 1.8205)], .00055, .7)
    # nasolabial, comisuras y mejilla enjuta
    linea([(.0195, 1.7735), (.027, 1.757), (.036, 1.737)], .0011, 1.0)
    linea([(.0275, 1.7445), (.031, 1.7345)], .0007, .8)
    linea([(.05, 1.79), (.054, 1.77), (.056, 1.75)], .0007, .55)
    # nariz
    linea([(.0, 1.8165), (.008, 1.8145)], .0005, .6)
    # los surcos se abren al difuminarlos; encima, un grano fino sin formar lineas
    surco = desenfoque(surco, 5) * 1.5
    # relieve de verdad (en metros): el surco se hunde y la piel de los lados abulta, como un pliegue
    global RELIEVE_ARRUGAS
    lin = np.clip(surco, 0, 1)
    RELIEVE_ARRUGAS = -.0008 * lin + .0012 * (desenfoque(lin, 14) - lin)
    grano = desenfoque(rng.normal(0, 1, (h, w)).astype(np.float32), 3)
    surco = np.clip(surco, 0, 1) + .05 * grano / grano.std()
    p = np.ones((h, w, 4), np.float32)
    p[..., 0] = surco
    # la suciedad: tierra en los surcos y parches de polvo
    polvo = desenfoque(rng.normal(0, 1, (h, w)).astype(np.float32), 60)
    polvo /= polvo.std()
    p[..., 1] = (1 - .1 * np.clip(surco, 0, 1)) * (.93 + .07 * np.tanh(polvo))
    p[..., 2] = 0
    return nueva_imagen("rostro_surcos", p, True)


def _muestra_frente(mapa, x, z):
    """Lee un mapa de imagen_surcos (x -.1 a .1, z 1.91 a 1.66) en puntos de la cara, con interpolacion bilineal."""
    h, w = mapa.shape
    c = np.clip((x + .1) / .2 * (w - 1), 0, w - 1.001)
    r = np.clip((1.91 - z) / .25 * (h - 1), 0, h - 1.001)
    c0, r0 = c.astype(np.int64), r.astype(np.int64)
    fc, fr = c - c0, r - r0
    return (mapa[r0, c0] * (1 - fc) * (1 - fr) + mapa[r0, c0 + 1] * fc * (1 - fr)
            + mapa[r0 + 1, c0] * (1 - fc) * fr + mapa[r0 + 1, c0 + 1] * fc * fr)


def relieve_arrugas(o):
    """Las arrugas en alto relieve: subdivide la piel donde hay surcos (de 1.5 mm a unos 0.4 mm entre vertices) y la desplaza por la normal."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.normal_update()

    def peso(v):
        # solo la cara vista de frente: el mapa se proyecta de frente y saldria tambien en la nuca
        return min(max((-.01 - v.co.y) / .02, 0), 1) * min(max((-v.normal.y - .1) / .3, 0), 1)

    def alto(v):
        return float(_muestra_frente(RELIEVE_ARRUGAS, np.array([v.co.x]), np.array([v.co.z]))[0]) * peso(v)

    marcados = {v for v in bm.verts if peso(v) > 0 and abs(alto(v)) > 2e-5}
    aristas = [e for e in bm.edges if e.verts[0] in marcados or e.verts[1] in marcados]
    bmesh.ops.subdivide_edges(bm, edges=aristas, cuts=3, use_grid_fill=True)
    bm.normal_update()
    vs = list(bm.verts)
    co = np.array([v.co[:] for v in vs], np.float64)
    nor = np.array([v.normal[:] for v in vs], np.float64)
    w = np.clip((-.01 - co[:, 1]) / .02, 0, 1) * np.clip((-nor[:, 1] - .1) / .3, 0, 1)
    d = _muestra_frente(RELIEVE_ARRUGAS, co[:, 0], co[:, 2]) * w
    for v, n_, d_ in zip(vs, nor, d):
        if d_:
            v.co += Vector(n_ * d_)
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    print("ARRUGAS", len(aristas), "aristas subdivididas", len(o.data.vertices), "vertices", round(float(d.min()) * 1000, 2), round(float(d.max()) * 1000, 2), "mm", flush=True)


def cabeza_mpfb():
    """Malla base de MakeHuman/MPFB con deformaciones de hombre mayor y enjuto. Devuelve vertices en metros aproximados de este personaje (ejes de Blender)."""
    import gzip
    d = os.path.join(AQUI, "mpfb_datos")
    vs, caras_b, grupos_v, g = [], [], {}, None
    for l in open(os.path.join(d, "base.obj")):
        if l.startswith("v "):
            vs.append([float(q) for q in l.split()[1:4]])
        elif l.startswith("g "):
            g = l.split()[1]
        elif l.startswith("f "):
            ids = [int(q.split("/")[0]) - 1 for q in l.split()[1:]]
            grupos_v.setdefault(g, set()).update(ids)
            if g == "body":
                caras_b.append(ids)
    vs = np.array(vs, np.float64)
    pesos = {"caucasian-male-old": 1.0, "universal-male-old-averagemuscle-minweight": .5, "universal-male-old-maxmuscle-minweight": .3, "universal-male-old-averagemuscle-averageweight": .2,
             "head-age-incr": .9, "head-fat-decr": .6, "head-rectangular": .35,
             "l-cheek-bones-incr": .6, "r-cheek-bones-incr": .6, "l-cheek-volume-decr": .7, "r-cheek-volume-decr": .7, "l-cheek-inner-decr": .4, "r-cheek-inner-decr": .4,
             "l-eye-bag-incr": .55, "r-eye-bag-incr": .55, "l-eye-height2-incr": .75, "r-eye-height2-incr": .75, "l-eye-eyefold-up": .45, "r-eye-eyefold-up": .45,
             "nose-hump-incr": .25, "nose-point-width-incr": .3, "nose-flaring-incr": .25, "forehead-temple-decr": .5, "forehead-nubian-incr": .25,
             "eyebrows-trans-forward": .5, "eyebrows-trans-down": .4, "mouth-laugh-lines-in": .6, "mouth-angles-down": .3, "chin-prominent-incr": .2}
    for nombre, w_ in pesos.items():
        with gzip.open(os.path.join(d, nombre + ".target.gz"), "rt") as f:
            for l in f:
                q = l.split()
                if len(q) == 4 and q[0].isdigit():
                    vs[int(q[0])] += w_ * np.array([float(t) for t in q[1:]])
    # OBJ: Y arriba y mira a +Z. Aqui Z arriba y mira a -Y
    co = np.c_[vs[:, 0], -vs[:, 2], vs[:, 1]]
    ojos = [sorted(grupos_v["helper-l-eye"]), sorted(grupos_v["helper-r-eye"])]
    tiras = sorted(set().union(*(grupos_v[f"helper-{l}-eyelashes-{k}"] for l in "lr" for k in (1, 2))))
    return co, caras_b, ojos, co[sorted(grupos_v["helper-upper-teeth"])], tiras


def crear_rostro():
    """Cara modelada: se subdivide la cabeza del juego, se esculpen los rasgos, se abren los ojos y se cubre de pelo de verdad."""
    global OJO
    rng = np.random.default_rng(51)
    o = bpy.data.objects["heads"]
    # pesos del juego por cercania: mandibula, cabeza y cuello
    viejo = np.empty(len(o.data.vertices) * 3, np.float32)
    o.data.vertices.foreach_get("co", viejo)
    viejo = viejo.reshape(-1, 3)
    kd_v = KDTree(len(viejo))
    for i, c_ in enumerate(viejo.tolist()):
        kd_v.insert(c_, i)
    kd_v.balance()
    grupos_v = [{o.vertex_groups[g.group].name: g.weight for g in v.groups} for v in o.data.vertices]
    arbol0 = BVHTree.FromPolygons([tuple(c) for c in viejo.tolist()], [list(f.vertices) for f in o.data.polygons])
    ysup = arbol0.ray_cast(Vector((OJO[0], -1, OJO[1])), Vector((0, 1, 0)), 2.0)[0].y

    co, caras_h, ojo_v, dientes, tiras_p = cabeza_mpfb()
    # escala por la altura de la cara: del ojo al menton, como la cabeza del juego
    izq, der = co[ojo_v[0]], co[ojo_v[1]]
    ci, cd = izq.mean(axis=0), der.mean(axis=0)
    ojo_z, ojo_y = float((ci[2] + cd[2]) / 2), float((ci[1] + cd[1]) / 2)
    cerca_m = co[(np.abs(co[:, 0]) < .12) & (co[:, 2] < ojo_z) & (co[:, 2] > ojo_z - 1.7) & (co[:, 1] < ojo_y + .25)]
    menton_z = float(cerca_m[:, 2].min())
    esc = .117 / (ojo_z - menton_z)
    OJO = (float(abs(ci[0] - cd[0])) * esc / 2, OJO[1])
    R = .0119
    co = co * esc
    dt = dientes * esc
    ojo_z, menton_z, ojo_y = ojo_z * esc, menton_z * esc, ojo_y * esc
    yc = ysup + R - .0016
    co = co - np.array((0, ojo_y - yc, 0))
    # el globo asoma un poco mas que su ayudante de MPFB
    yc -= .0005
    boca_z = float(dt[:, 2].min())
    print("MPFB alturas", round(ojo_z, 3), round(boca_z, 3), round(menton_z, 3), "esc", round(esc, 4), "ojo_x", round(OJO[0], 4), "ancho", round(float(np.abs(co[:, 0][(co[:, 2] > ojo_z - .05) & (co[:, 2] < ojo_z + .1)]).max()), 3), flush=True)
    # deformacion vertical minima: ojos, boca y menton caen donde los espera lo demas
    fuente = [menton_z - 1, menton_z, boca_z, ojo_z, ojo_z + 1]
    destino = [1.698 - 1, 1.698, 1.7455, OJO[1], OJO[1] + 1]
    co[:, 2] = np.interp(co[:, 2], fuente, destino)
    # MPFB trae tiras de pestanas: su lado cercano al ojo marca el borde del parpado
    borde_p = co[tiras_p].astype(np.float32)
    # solo la cabeza y parte del cuello, que queda dentro del cuello de la casaca
    # abajo solo el cuello: los hombros de MPFB saldrian por fuera de la casaca
    def _sirve(f):
        q = co[list(f)]
        return q[:, 2].min() > 1.668 and np.abs(q[:, 0]).max() < .12 and (q[:, 2].min() > 1.725 or np.abs(q[:, 0]).max() < .062)
    usa = [f for f in caras_h if _sirve(f)]
    ids = sorted({i for f in usa for i in f})
    nuevo = {v: k for k, v in enumerate(ids)}
    me = bpy.data.meshes.new("heads_mpfb")
    me.from_pydata(co[ids].tolist(), [], [tuple(nuevo[i] for i in f) for f in usa])
    me.update()
    me.uv_layers.new(name="UVMap")
    o.modifiers.clear()
    o.data = me
    nombres = sorted({k for g in grupos_v for k in g})
    while o.vertex_groups:
        o.vertex_groups.remove(o.vertex_groups[0])
    grupos = {k: o.vertex_groups.new(name=k) for k in nombres}
    for i, c_ in enumerate(co[ids].tolist()):
        for k, w_ in grupos_v[kd_v.find(c_)[1]].items():
            grupos[k].add([i], w_, "REPLACE")
    suavizar(o, None, niveles=2)
    me = o.data
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3).astype(np.float64)
    # solo por encima del cuello de la casaca; mas abajo atravesaria la tela
    baja_c = np.clip((1.765 - co[:, 2]) / .04, 0, 1) * np.clip((co[:, 2] - 1.71) / .02, 0, 1) * np.clip((co[:, 1] + .02) / .03, 0, 1)
    largo_c = np.maximum(np.hypot(co[:, 0], co[:, 1] + .01), 1e-6)
    co[:, 0] += co[:, 0] / largo_c * .009 * baja_c
    co[:, 1] += (co[:, 1] + .01) / largo_c * .009 * baja_c
    me.vertices.foreach_set("co", co.astype(np.float32).ravel())
    me.update()
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    ax = np.abs(x)
    e = _almendra(ax, z)
    linea = 1.7455 - 1.6 * np.clip(ax - .012, 0, 1) ** 2 * 10
    co2 = co
    me.shade_smooth()

    # color por zonas, sobre la forma nueva; se guarda por vertice
    piel = _a_lineal(np.array((.7, .52, .41)))[None] * np.ones((n, 3), np.float32)

    def tinte(fuerza, col, solo_cara=True):
        nonlocal piel
        # los rasgos se miden de frente: sin esto saldrian tambien detras de la cabeza
        f = (np.clip(fuerza, 0, 1) * (np.clip((-.01 - y) / .02, 0, 1) if solo_cara else 1))[:, None]
        piel = piel * (1 - f) + _a_lineal(np.array(col))[None] * f

    def ru(esc):
        q = np.sin(x * esc + 1.3) * np.sin(z * esc * 1.13 + .7) * np.sin(y * esc * .9 + 2.1)
        return q + .5 * np.sin(x * esc * 2.3 + z * esc * 1.9)

    tinte(.4 * _campana(ax, z, .05, 1.79, .03, .03), (.66, .38, .3))      # mejillas curtidas
    tinte(.4 * _campana(ax, z, .0, 1.782, .018, .018), (.62, .34, .27))      # nariz
    tinte(.35 * np.clip((z - 1.83) / .03, 0, 1) * np.clip((1.87 - z) / .03, 0, 1), (.74, .46, .36))   # frente quemada por el sol
    tinte(.28 * np.clip(ru(90) * .5 + .35, 0, 1), (.5, .36, .27))             # sol y polvo a parches
    tinte(.3 * _campana(ax, z, OJO[0], OJO[1] - .0085, .015, .0045), (.42, .29, .26))
    tinte(.3 * _campana(ax, z, OJO[0], OJO[1] + .008, .016, .004), (.42, .3, .25))  # ojera
    labio = np.clip(_campana(ax, z, .0, 1.7515, .021, .0032) + _campana(ax, z, .0, 1.739, .0185, .0042), 0, 1)
    tinte(.82 * labio, (.62, .32, .29))
    tinte(.95 * np.exp(-((z - linea) / .0009) ** 2) * (ax < .0255), (.22, .1, .09))
    tinte(.95 * _campana(ax, z, .0065, 1.7675, .0032, .002), (.1, .05, .04))  # orificios
    tinte(.85 * np.clip((y - .01) / .03, 0, 1) * (z > 1.69), (.2, .12, .07), False)    # cuero cabelludo bajo el pelo
    me.color_attributes.new("piel", "FLOAT_COLOR", "POINT").data.foreach_set("color", np.c_[piel, np.ones(n)].astype(np.float32).ravel())
    if "cine_p" in me.attributes:
        me.attributes.remove(me.attributes["cine_p"])
    me.attributes.new("cine_p", "FLOAT_VECTOR", "POINT").data.foreach_set("vector", co2.astype(np.float32).ravel())
    me.materials.clear()
    me.materials.append(material_piel("piel_rostro", imagen_surcos(rng)))
    relieve_arrugas(o)

    # globos oculares con cornea
    A, B = 48, 32
    pos, caras, uvs = [], [], []
    k = 0
    for lado in (1, -1):
        for j in range(B + 1):
            t = j / B * math.pi
            for i in range(A):
                f = i / A * 2 * math.pi
                # la cornea abulta poco delante del iris
                rr = R + .0007 * max(math.cos(min(t / .55, 1) * math.pi / 2), 0) ** 1.5
                pos.append((lado * OJO[0] + rr * math.sin(t) * math.cos(f), yc - rr * math.cos(t), OJO[1] + rr * math.sin(t) * math.sin(f)))
                uvs.append((.5 + .5 * t / math.pi * math.cos(f), .5 + .5 * t / math.pi * math.sin(f)))
        for j in range(B):
            for i in range(A):
                caras.append((k + j * A + i, k + j * A + (i + 1) % A, k + (j + 1) * A + (i + 1) % A, k + (j + 1) * A + i))
        k += (B + 1) * A
    im = imagen_ojo(rng)
    mo = bpy.data.materials.new("ojo")
    mo.use_nodes = True
    nb = next(q for q in mo.node_tree.nodes if q.type == "BSDF_PRINCIPLED")
    tx = mo.node_tree.nodes.new("ShaderNodeTexImage")
    tx.image = im
    # el parpado y las pestanas dejan en sombra la parte alta del globo
    ao = mo.node_tree.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = .007
    mo.node_tree.links.new(tx.outputs[0], ao.inputs["Color"])
    mo.node_tree.links.new(ao.outputs["Color"], nb.inputs["Base Color"])
    nb.inputs["Subsurface Weight"].default_value = .25
    nb.inputs["Subsurface Radius"].default_value = (1.0, .45, .3)
    nb.inputs["Subsurface Scale"].default_value = .002
    nb.inputs["Roughness"].default_value = .06
    nb.inputs["Specular IOR Level"].default_value = .6
    nb.inputs["Coat Weight"].default_value = .9
    nb.inputs["Coat Roughness"].default_value = .02
    malla_cabeza("rostro_ojos", pos, caras, mo, uvs, hueso="Eyes")

    # pelo: cada hebra toma los pesos de su raiz
    sop = Soporte(o, None)
    nv = np.empty(len(me.vertices) * 3, np.float32)
    me.vertex_normals.foreach_get("vector", nv)
    nv = nv.reshape(-1, 3)
    cf = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", cf)
    cf = cf.reshape(-1, 3)

    area_v = np.zeros(len(me.vertices), np.float64)
    for f_ in me.polygons:
        for v_ in f_.vertices:
            area_v[v_] += f_.area / len(f_.vertices)

    def raices(mascara, cuantas):
        idx = np.nonzero(mascara)[0]
        el = rng.choice(idx, cuantas, p=area_v[idx] / area_v[idx].sum())
        # el salto se ajusta al tamano de la cara, para no dejar huecos entre vertices separados
        salto = np.sqrt(area_v[el])[:, None] * .6
        return el, (cf[el] + rng.normal(0, 1, (cuantas, 3)) * salto).astype(np.float32), nv[el]

    def hebras(nombre, el, raiz, nor, col, polvo, **kw):
        p, c, uv = pelo(rng, raiz.astype(np.float32), nor.astype(np.float32), tope=False, **kw)
        pes = np.repeat(sop.W[el], len(p) // len(el), axis=0)
        col_rel.objects.link(objeto_relieve(nombre, np.array(p, np.float32), c, pes, sop, arm, material_pluma(nombre + "_mat", bpy.data.images["pelo_opaco"], col, polvo)))
        # la uv da la sombra de la raiz
        o_ = bpy.data.objects[nombre]
        i_ = np.fromiter((l.vertex_index for l in o_.data.loops), np.int64, len(o_.data.loops))
        o_.data.uv_layers["UVMap"].data.foreach_set("uv", np.asarray(uv, np.float32)[i_].ravel())
        print("PELO", nombre, len(el), flush=True)

    X, Y, Z = cf[:, 0], cf[:, 1], cf[:, 2]
    AX = np.abs(X)
    rojo, rubio = (.19, .075, .036), (.42, .19, .09)
    # barba: bajo la linea que va de la patilla a la comisura, sin tapar los labios
    alto_b = 1.754 + .7 * np.clip(AX - .032, 0, 1)
    boca = (AX < .0265) & (Z > 1.7325) & (Z < 1.7555)
    barba = (Z < alto_b + .012) & (Y < -.002) & ~boca & (Z > 1.684)
    # cuanto mas cerca del borde, menos probable y mas corta
    borde = np.clip((alto_b + .012 - Z) / .028, 0, 1)
    barba &= rng.uniform(0, 1, len(Z)) < borde ** .8 + .03
    el, r_, n_ = raices(barba, 62000)
    n_ = n_ * .9 + np.array((0, -.3, -.25), np.float32)
    hebras("rostro_barba", el, r_, n_, rojo, rubio, n_seg=6, caida=1.3, largos=(.04, .085), anchos=(.0007, .0015), suelto=.7, rizado=.26, factor=(.25 + .75 * borde[el]).astype(np.float32))
    # vello corto en el borde de la barba y sobre la mejilla
    vello = (np.abs(Z - alto_b - .004) < .017) & (Y < -.002) & ~boca & (AX > .012)
    el, r_, n_ = raices(vello, 14000)
    hebras("rostro_vello", el, r_, n_ + np.array((0, -.2, -.5), np.float32), rojo, rubio, n_seg=3, caida=1.0, largos=(.004, .016), anchos=(.0004, .0009), suelto=.7)
    # patillas que suben hasta el pelo
    pat = (AX > .064) & (Y < -.006) & (Y > -.05) & (Z >= alto_b - .012) & (Z < 1.838)
    el, r_, n_ = raices(pat, 9000)
    hebras("rostro_patillas", el, r_, n_, (.09, .045, .025), (.3, .14, .07), caida=1.3, largos=(.012, .026), anchos=(.0007, .0013), suelto=.65)
    # bigote: del surco del labio hacia los lados, cayendo sobre la boca
    big = (AX < .034) & (Z > 1.7505) & (Z < 1.764) & (Y < -.09)
    el, r_, n_ = raices(big, 7000)
    n_ = np.c_[r_[:, 0] / .03, np.full(len(r_), -.5), np.full(len(r_), -.5)]
    hebras("rostro_bigote", el, r_, n_, (.15, .07, .035), (.4, .2, .095), caida=.7, largos=(.024, .05), anchos=(.0011, .002), suelto=.45, rizado=.12)
    # cejas: hebras cortas tumbadas hacia fuera
    arco = 1.8285 + .0085 * np.clip((AX - .012) / .03, 0, 1) - .55 * np.clip(AX - .05, 0, 1)
    ceja = (rng.uniform(0, 1, len(Z)) < np.clip((.0052 - np.abs(Z - arco)) / .0026, 0, 1)) & (AX > .009) & (AX < .06) & (Y < -.07)
    el, r_, n_ = raices(ceja, 3400)
    n_ = np.c_[np.sign(r_[:, 0]) * .8, np.full(len(r_), -.3), np.full(len(r_), .62)]
    hebras("rostro_cejas", el, r_, n_, (.09, .05, .03), (.3, .16, .07), n_seg=3, caida=.05, largos=(.007, .017), anchos=(.0005, .001), suelto=.65)
    # pelo corto de la nuca y los lados, lo que asoma bajo el bonete
    nuca = ((Y > .03) & (Z > 1.712) | (Y > -.03) & (Z > 1.838) & (AX > .05) | (Y > -.012) & (Z > 1.725) & (Z < 1.772)) & (Z < 1.885)
    el, r_, n_ = raices(nuca, 30000)
    hebras("rostro_pelo", el, r_, n_, (.045, .028, .018), (.075, .045, .028), caida=1.6, largos=(.016, .032), anchos=(.0009, .0016), suelto=.55)
    # pestanas en el borde real del parpado: donde, mirando de frente, la piel deja de tapar el globo
    # (las tiras de MPFB quedan unos 6 mm por delante del ojo y las pestanas flotaban)
    arbol_c = BVHTree.FromPolygons(cf.tolist(), [list(f_.vertices) for f_ in me.polygons])
    frente = Vector((0, 1, 0))
    borde = {True: [], False: []}
    for lado in (1, -1):
        for dx in np.linspace(-.0128, .0128, 90):
            x = lado * OJO[0] + dx
            visto = []
            for z in np.arange(OJO[1] - .0125, OJO[1] + .0125, .0002):
                q = R * R - dx * dx - (z - OJO[1]) ** 2
                if q <= 0:
                    continue
                piel_y = arbol_c.ray_cast(Vector((x, -1, z)), frente, 2.0)[0]
                if piel_y is None or piel_y.y > yc - math.sqrt(q) - 1e-5:
                    visto.append(z)
            if len(visto) < 3:
                continue
            for arr, z in ((True, max(visto) + .0003), (False, min(visto) - .0003)):
                p_ = arbol_c.ray_cast(Vector((x, -1, z)), frente, 2.0)[0]
                if p_ is not None:
                    borde[arr].append((p_.x, p_.y, p_.z))
    kd = KDTree(len(cf))
    for i, c_ in enumerate(cf.tolist()):
        kd.insert(c_, i)
    kd.balance()
    # arriba una fila densa que sale hacia delante y se curva hacia arriba; abajo menos, cortas y caidas
    for nombre, arr, cuantas, largos, anchos in (("rostro_pestanas", True, 210, (.0045, .0095), (.00015, .0003)), ("rostro_pestanas_bajo", False, 80, (.0022, .0045), (.00014, .00026))):
        fila = np.array(borde[arr], np.float32)
        r_ = []
        for lado in (1, -1):
            f_ = fila[np.sign(fila[:, 0]) == lado]
            f_ = f_[np.argsort(f_[:, 0])]
            # del lagrimal (x0) a la comisura (x1); el lagrimal no lleva pestanas: se empieza un poco hacia fuera
            x0, x1 = (f_[0, 0], f_[-1, 0]) if lado > 0 else (f_[-1, 0], f_[0, 0])
            x_ = x0 + (.12 + .88 * rng.uniform(0, 1, cuantas // 2) ** .8) * (x1 - x0)
            r_.append(np.c_[x_, np.interp(x_, f_[:, 0], f_[:, 1]) + .0002, np.interp(x_, f_[:, 0], f_[:, 2])])
        r_ = np.concatenate(r_).astype(np.float32)
        # -1 en el lagrimal, +1 en la comisura: las de fuera son mas largas y se abren hacia la sien
        fuera = np.clip(np.sign(r_[:, 0]) * (np.abs(r_[:, 0]) - OJO[0]) / .012, -1, 1)
        # en abanico: las del lagrimal hacia la nariz, las de fuera hacia la sien; arriba casi de frente, la curva la da el peso hacia arriba
        n_ = np.c_[np.sign(r_[:, 0]) * .55 * fuera + rng.normal(0, .12, len(r_)), np.full(len(r_), -1.0), (.08 if arr else -.35) + rng.normal(0, .1, len(r_))].astype(np.float32)
        n_ /= np.linalg.norm(n_, axis=1, keepdims=True)
        el = np.array([kd.find(v.tolist())[1] for v in r_], np.int64)
        hebras(nombre, el, r_, n_, (.025, .016, .011), (.05, .028, .018), n_seg=5, sube=arr, caida=.0, largos=largos, anchos=anchos,
               suelto=.3, factor=(.5 + .5 * np.sin(np.pi * (fuera * .45 + .55)) ** .5).astype(np.float32))
        print("PESTANAS", nombre, len(fila), "puntos de borde", flush=True)
    # manos: misma piel, mas curtida y sucia
    h = bpy.data.objects["hands"]
    mh = h.data
    hc = np.empty(len(mh.vertices) * 3, np.float32)
    mh.vertices.foreach_get("co", hc)
    hc = hc.reshape(-1, 3)
    nudos = np.sin(hc[:, 0] * 260) * np.sin(hc[:, 1] * 310 + 1) * np.sin(hc[:, 2] * 280 + 2)
    col_h = _a_lineal(np.array((.62, .44, .33)))[None] * (.8 + .2 * np.clip(nudos + .4, 0, 1))[:, None]
    mh.color_attributes.new("piel", "FLOAT_COLOR", "POINT").data.foreach_set("color", np.c_[col_h, np.ones(len(hc))].astype(np.float32).ravel())
    if "cine_p" in mh.attributes:
        mh.attributes.remove(mh.attributes["cine_p"])
    mh.attributes.new("cine_p", "FLOAT_VECTOR", "POINT").data.foreach_set("vector", hc.ravel())
    plano = np.ones((4, 4, 4), np.float32)
    plano[..., 0], plano[..., 2] = 0, 0
    mh.materials.clear()
    mh.materials.append(material_piel("piel_manos", nueva_imagen("manos_surcos", plano, True)))
    o["ojo_x"], o["ojo_z"] = OJO
    print("ROSTRO", len(me.vertices), "vertices", flush=True)


FINAL = (crear_bonete, crear_sporran, crear_doblez_media, crear_bandas, crear_hombros, crear_rostro)


# recetas para los materiales rehechos
RECETAS_NUEVAS = {
    "cuero": {"barro": .2, "roce": .5, "m": .07, "esc_barro": 7},
    "peltre": {"rug": .5},
    "ante": {"dibujo": .12, "m": .05, "relieve": .08},
    "pano": {"rotos": .1},
    "pano_claro": {"loseta": "pano", "m": .05, "dibujo": .4, "sheen": .35, "oscurecer": .95, "saturacion": .8, "roce": .8, "relieve": .35, "espec": .12},
    "tartan": {"m": .11, "oscurecer": 1.0, "saturacion": .95, "dibujo": 1.0, "barro": .8, "hollin": .75, "mancha": .65, "roce": .55, "rotos": .1, "esc_barro": 12,
               # lana mate: sin el grupo de tela, que baja la rugosidad, y casi sin reflejo
               "falloff": False, "rug": 1.0, "espec": .08, "sheen": .22, "normal": .12, "relieve": 1.0},
    "banda_blanca": {"loseta": "pano", "m": .05, "dibujo": .1, "rug": .78, "roce": .8, "oscurecer": 1.0, "saturacion": .85, "mancha": .55, "hollin": .55, "barro": .3, "sangre": .3, "relieve": .08, "normal": .0},
    "faja": {"loseta": "sarga", "m": .022, "dibujo": .6, "sheen": .45, "espec": .2, "rug": .8, "oscurecer": 1.0, "saturacion": 1.0, "mancha": .5, "hollin": .5, "roce": .45, "barro": .2, "sangre": .3, "relieve": .6, "normal": .0},
    "cuadros": {"loseta": "sarga", "m": .024, "dibujo": .75, "sheen": .2, "oscurecer": 1.0, "saturacion": .85, "mancha": .8, "hollin": .75, "roce": .7, "barro": 1.0, "sangre": .5, "esc_barro": 12, "relieve": .9},
    "dados": {"loseta": "sarga", "m": .03, "dibujo": .6, "sheen": .2, "espec": .12, "oscurecer": 1.0, "saturacion": .95, "mancha": .55, "hollin": .55, "roce": .5, "barro": 0.0, "sangre": .15, "relieve": .7, "normal": .0},
    "lona": {"loseta": "sarga", "m": .03, "dibujo": .55, "sheen": .12, "espec": .12, "oscurecer": 1.0, "saturacion": .9, "mancha": .3, "hollin": .22, "roce": .5, "barro": .32, "sangre": .3, "esc_barro": 24, "relieve": .7, "normal": .1},
    "polaina": {"loseta": "pano", "m": .05, "dibujo": .45, "sheen": .3, "oscurecer": 1.0, "saturacion": .9, "mancha": .55, "hollin": .55, "roce": .7, "barro": .85, "esc_barro": 12, "relieve": .35},
}
GROSOR = ("correajes/",)
GROSOR_M = .003
REHACER = ()

RELIEVE = [
    {"malla": "torsos", "textura": "torsos", "escala": 2, "zona": zona_torsos, "slots": {"casaca": "pano", "corbatin": "cuero"}, "piezas": [
        {"nombre": "relieve_galon", "mascara": m_galon, "alto": a_galon, "f": 3, "receta": "cordon", "color": (.74, .71, .62)},
        {"nombre": "relieve_faldon", "respeta_borde": True, "mascara": m_faldon, "alto": a_faldon, "f": 2, "receta": "pano_claro", "color": (.78, .76, .71)},
        {"nombre": "relieve_banda_puno", "mascara": m_banda_puno, "alto": a_banda_puno, "f": 2, "receta": "pano_claro", "color": (.42, .42, .42)},
        {"nombre": "relieve_boton", "mascara": m_boton, "alto": a_boton, "f": 4, "receta": "peltre", "color": (.62, .6, .54)},
    ]},
    {"malla": "legs", "textura": "legs", "escala": 4, "pintar": pintar_legs, "forma": plisar_kilt, "extra": crear_polainas, "zona": zona_legs,
     "slots": {"kilt": "tartan", "medias": "cuadros", "polainas": ("cuero", "zapato_negro", (.055, .05, .05)), "zapatos": ("cuero", "zapato_negro", (.055, .05, .05)), "piel": None}, "piezas": [
    ]},
]
