"""Paso 7 del flujo: textura de cine para un detalle suelto, abierto en Blender. Teje la tela hilo a hilo a su tamano real.

Uso (dentro de Blender):  exec(open(r"...\\paso7_textura_cine.py", encoding="utf-8").read())
Genera color, normal y rugosidad, los empaqueta en el .blend, crea el material y anade una UV a escala y grosor real.
Se puede ejecutar varias veces. El UVMap, el material del juego y los pesos no cambian; el archivo no se guarda.
"""
import bmesh
import bpy
import numpy as np
from mathutils.kdtree import KDTree

POLIIGON = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\delgada_linea_roja\poliigon-addon-blender\poliigon-addon-blender\files\poliigon_material_template_update.blend"
# colores lineales: color del juego medido en su textura y su variacion; medidas en metros
CINTA_MEDIA = {"objeto": "media_I_01_banda", "grosor": .0018, "px_mm": 16, "paso_hilo": (.00036, .00032),
               "color": (.135, .094, .038), "semilla": 3}


def ruido(forma, sx, sy, rng):
    """Ruido periodico de media 0 y desviacion 1, con detalle de sx por sy pixeles."""
    f = np.fft.rfft2(rng.standard_normal(forma))
    ky = np.fft.fftfreq(forma[0])[:, None]
    kx = np.fft.rfftfreq(forma[1])[None, :]
    r = np.fft.irfft2(f * np.exp(-2 * np.pi ** 2 * ((kx * sx) ** 2 + (ky * sy) ** 2)), s=forma)
    return (r - r.mean()) / max(r.std(), 1e-9)


def tejer(c):
    """Sarga 2/2 de lana. Filas = alto de la cinta (y sube), columnas = largo. Devuelve altura en mm, color lineal, rugosidad."""
    rng = np.random.default_rng(c["semilla"])
    h = int(round(c["alto"] * 1000 * c["px_mm"]))
    w = int(round(c["largo"] * 1000 * c["px_mm"]))
    forma = (h, w)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    n_u = int(round(c["largo"] / c["paso_hilo"][0] / 4)) * 4
    n_v = int(round(c["alto"] / c["paso_hilo"][1]))
    amp = c["paso_hilo"][1] * 1000 * .42  # altura del hilo en mm
    mm = c["px_mm"]

    def rd(lx, ly):  # ruido con detalle dado en milimetros
        return ruido(forma, lx * mm, ly * mm, rng)

    # los hilos no son rectos: ondulan un poco, como en un tejido a mano
    du = rd(7, 3) * .16 + rd(1, 1) * .05
    dv = rd(9, 2.5) * .14 + rd(1, 1) * .05
    fu = x / w * n_u + du
    fv = y / h * n_v + dv
    j, i = np.floor(fu).astype(np.int32), np.floor(fv).astype(np.int32)
    a, b = fu - j, fv - i
    urdimbre = ((i + j) % 4) < 2  # hilo a lo largo por encima
    prof_v, prof_u = np.sin(np.pi * b), np.sin(np.pi * a)
    # grosor y tono propios de cada hilo; algun hilo mas grueso (lana hilada irregular)
    tv = rng.normal(0, 1, n_v + 2)
    tu = rng.normal(0, 1, n_u + 2)
    gv, gu = 1 + .12 * tv, 1 + .12 * tu
    hilo_v = np.clip(i, 0, n_v + 1)
    hilo_u = j % (n_u + 2)
    hebra_u = rd(5, .09)  # fibras a lo largo del hilo
    hebra_v = rd(.09, 5)
    arriba = np.where(urdimbre, prof_v ** .55 * (.55 + .45 * prof_u) * gv[hilo_v], prof_u ** .55 * (.55 + .45 * prof_v) * gu[hilo_u])
    fibra = np.where(urdimbre, hebra_u, hebra_v)
    altura = amp * arriba + .28 * amp * fibra + .1 * amp * rd(.25, .25)

    # orillo: dos cordones mas gruesos en cada borde
    alto_mm = y / h * c["alto"] * 1000
    borde = np.minimum(alto_mm, c["alto"] * 1000 - alto_mm)
    orillo = np.clip(1 - borde / 1.8, 0, 1)
    altura += .5 * amp * orillo * np.abs(np.sin(np.pi * borde / .9))
    # arrugas suaves de una cinta atada, a lo ancho
    pliegue = rd(14, 7) * .35 + rd(45, 16) * .65
    altura += .1 * pliegue

    # color: hebras de dos tonos, tinte natural irregular, roce claro y suciedad, todo sin manchas duras
    base = np.array(c["color"], np.float32)
    tono = np.where(urdimbre, 1 + .1 * tv[hilo_v], .86 + .1 * tu[hilo_u])
    tinte = np.exp(.09 * rd(14, 9) + .07 * rd(60, 25))
    hueco = .62 + .38 * np.clip(arriba, 0, 1) ** .8  # sombra real entre hilos
    v = tono * tinte * hueco * (1 + .16 * fibra)
    color = base[None, None] * v[..., None]
    # el tinte agrisa donde la lana esta gastada
    gris = np.clip(.5 + .5 * rd(22, 12), 0, 1)[..., None]
    color = color * (1 - .22 * gris) + (color.mean(axis=2, keepdims=True) * np.array((1.04, 1, .88), np.float32)) * .22 * gris
    roce = np.clip(rd(16, 6) * .3 + orillo * .55 + pliegue * .25 - .2, 0, 1) * np.clip(arriba, 0, 1) ** 2
    color += roce[..., None] * np.array((.07, .058, .038), np.float32)
    # --- meses de campana: nada sale limpio del sastre ---
    # tinte comido por el sol y la lluvia, a parches
    sol = np.clip(.5 + .7 * rd(30, 14), 0, 1)[..., None]
    color = color * (1 - .4 * sol) + color.mean(axis=2, keepdims=True) * np.array((1.12, 1.02, .8), np.float32) * .4 * sol
    color *= .86
    # zonas rozadas: el hilo se aplana y palidece
    gast = np.clip(rd(18, 6) * .5 + orillo * .55 + pliegue * .3 - .2, 0, 1)
    altura -= amp * .55 * gast * np.clip(arriba, 0, 1)
    color += gast[..., None] * np.clip(arriba, 0, 1)[..., None] * np.array((.05, .043, .03), np.float32)
    # sudor y grasa desde arriba, con cerco de sal donde se seco
    g = rd(45, 16) * .5 + (y / h) ** 2 * .75 + rd(6, 4) * .06
    mancha = np.clip((g - .38) / .22, 0, 1)
    cerco = np.exp(-((g - .38) / .03) ** 2) * np.clip(rd(25, 25) + .8, 0, 1)
    color *= 1 - .5 * mancha[..., None]
    color += cerco[..., None] * np.array((.038, .034, .026), np.float32)
    # hollin de la polvora, en tiznones y polvo fino
    hollin = np.clip(rd(20, 9) * .7 - .55, 0, 1) * np.clip(.65 + .35 * rd(.5, .5), 0, 1)
    color = color * (1 - .68 * hollin[..., None]) + .012 * .68 * hollin[..., None]
    # barro de Crimea: costra seca desde abajo y salpicaduras, tapa el tejido y tiene relieve
    salpica = np.clip((rd(.75, .75) - 2.0) * 2.5, 0, 1) * np.clip(rd(55, 28) + .7, 0, 1) * (.35 + .65 * (1 - y / h))
    barro = np.clip((rd(30, 5) * .3 + (1 - y / h) ** 1.7 * 1.05 + rd(2.5, 2.5) * .13 - .47) * 2.4, 0, 1)
    barro = np.maximum(barro, salpica)
    tierra = np.array((.092, .071, .047), np.float32)[None, None] * np.exp(.28 * rd(.4, .4) + .2 * rd(6, 6))[..., None]
    color = color * (1 - .9 * barro[..., None]) + tierra * .9 * barro[..., None]
    altura += barro * (.32 + .1 * rd(.3, .3) + .12 * rd(2, 2))
    # sangre seca: pocas gotas, casi negras
    gotas = np.clip((rd(.7, .7) - 2.15) * 3, 0, 1) * np.clip((rd(40, 30) - .9) * 3, 0, 1)
    color = color * (1 - .88 * gotas[..., None]) + np.array((.03, .006, .004), np.float32) * .88 * gotas[..., None]

    rug = np.clip(.88 + .05 * fibra - .3 * gast * np.clip(arriba, 0, 1) - .3 * mancha * .7 + .08 * barro - .25 * gotas, .4, 1)

    # orillo deshilachado: se pierde la urdimbre y queda el fleco de la trama; rotos sueltos por el roce
    corte = np.maximum(rd(14, 1) * .5 + rd(3, .6) * .3 + .3, 0)
    corte += np.clip(rd(40, 1) - 1.4, 0, 1) * 2.2  # mordiscos de la tela enganchada
    largo_hilo = rng.exponential(.7, n_u + 2)[hilo_u]  # cada hilo de la trama asoma lo suyo
    fleco = borde < corte + 1.5
    alfa = np.where(fleco, (prof_u > .5) & (borde > corte - largo_hilo), True)
    # pocos rotos pequenos, deshilachados, donde mas roza
    agujero = (rd(.8, .55) + rd(.15, .15) * .35 + gast * 1.1) > 4.1
    alfa = np.where(agujero, False, alfa)
    return altura.astype(np.float32), np.clip(color, 0, 1).astype(np.float32), rug.astype(np.float32), alfa.astype(np.float32)


def normal_de(altura, px_mm, fuerza=1.0):
    dx = (np.roll(altura, -1, 1) - np.roll(altura, 1, 1)) * px_mm / 2 * fuerza
    dy = (np.roll(altura, -1, 0) - np.roll(altura, 1, 0)) * px_mm / 2 * fuerza
    n = np.dstack((-dx, -dy, np.ones_like(dx)))
    return n / np.linalg.norm(n, axis=2, keepdims=True) * .5 + .5


def a_srgb(c):
    return np.where(c <= .0031308, c * 12.92, 1.055 * np.maximum(c, 1e-6) ** (1 / 2.4) - .055)


def imagen(nombre, rgb, datos, alfa=None):
    if nombre in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[nombre])
    h, w = rgb.shape[:2]
    im = bpy.data.images.new(nombre, w, h, alpha=alfa is not None)
    im.colorspace_settings.name = "Non-Color" if datos else "sRGB"
    p = np.ones((h, w, 4), np.float32)
    p[..., :3] = rgb if rgb.ndim == 3 else rgb[..., None]
    if alfa is not None:
        p[..., 3] = alfa
    im.pixels.foreach_set(p.ravel())  # pixels va de abajo arriba, igual que las filas del tejido
    im.update()
    im.pack()
    return im


def malla_limpia(o, segmentos=128, filas=6):
    """Rehace la cinta como anillo de cuadrados, con la misma forma y pesos: las caras del corte por dibujo dan fallos de sombreado.

    Cierra el hueco del lazo y suaviza un poco las esquinas. Devuelve largo y alto en metros.
    """
    me = o.data
    if me.get("anillo_cine"):
        return me["largo"], me["alto"]
    p = np.empty(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get("co", p)
    p = p.reshape(-1, 3)
    centro = p.mean(0)
    eje = np.linalg.svd(p - centro, full_matrices=False)[2][2]
    eje = eje if eje[2] > 0 else -eje  # el eje del anillo es la direccion de menor extension
    a = np.cross(eje, (1, 0, 0))
    a /= np.linalg.norm(a)
    b = np.cross(eje, a)
    q = p - centro
    alto = q @ eje
    x, y = q @ a, q @ b
    ang = np.arctan2(y, x)
    rad = np.hypot(x, y)
    pend = np.polyfit(alto, rad, 1)[0]  # la cinta se estrecha un poco, como la pierna
    rad0 = rad - pend * alto
    # contorno por sectores, con los sectores sin datos interpolados y un suavizado corto de las esquinas
    n = 720
    sector = ((ang + np.pi) / (2 * np.pi) * n).astype(int) % n
    perfil = np.full(n, np.nan)
    for i in range(n):
        if (sector == i).any():
            perfil[i] = np.median(rad0[sector == i])
    bien = np.nonzero(~np.isnan(perfil))[0]
    perfil = np.interp(np.arange(n), bien, perfil[bien], period=n)
    perfil = np.real(np.fft.ifft(np.fft.fft(perfil) * np.exp(-.5 * (np.fft.fftfreq(n) * n * .035) ** 2)))
    th = -np.pi + 2 * np.pi * np.arange(segmentos) / segmentos
    ra = np.interp(th, -np.pi + 2 * np.pi * (np.arange(n) + .5) / n, perfil, period=2 * np.pi)
    t0, t1 = alto.min(), alto.max()
    alturas = np.linspace(t0, t1, filas)
    verts = []
    for t in alturas:
        r = ra + pend * t
        verts.append(centro + a[None] * (r * np.cos(th))[:, None] + b[None] * (r * np.sin(th))[:, None] + eje[None] * t)
    verts = np.concatenate(verts)
    # pesos por los 4 vertices antiguos mas cercanos
    arbol = KDTree(len(p))
    for i, c in enumerate(p):
        arbol.insert(c, i)
    arbol.balance()
    pesos_v = np.zeros((len(p), len(o.vertex_groups)), np.float32)
    for v in me.vertices:
        for g in v.groups:
            pesos_v[v.index, g.group] = g.weight
    pesos = np.zeros((len(verts), pesos_v.shape[1]), np.float32)
    for i, c in enumerate(verts):
        cerca = arbol.find_n(c, 4)
        w = np.array([1 / (d + 1e-4) for _, _, d in cerca])
        pesos[i] = (pesos_v[[k for _, k, _ in cerca]] * (w / w.sum())[:, None]).sum(0)
    caras, uv = [], []
    for j in range(filas - 1):
        for i in range(segmentos):
            i2 = (i + 1) % segmentos
            caras.append((j * segmentos + i, j * segmentos + i2, (j + 1) * segmentos + i2, (j + 1) * segmentos + i))
            u0, u1 = i / segmentos, (i + 1) / segmentos
            v0, v1 = j / (filas - 1), (j + 1) / (filas - 1)
            uv += [u0, v0, u1, v0, u1, v1, u0, v1]
    largo = float(np.hypot(*np.diff(np.c_[ra * np.cos(th), ra * np.sin(th)], axis=0, append=[[ra[0] * np.cos(th[0]), ra[0] * np.sin(th[0])]]).T).sum())
    nuevo = bpy.data.meshes.new(me.name)
    nuevo.from_pydata(verts.tolist(), [], caras)
    nuevo.materials.append(me.materials[0])
    nuevo.uv_layers.new(name="UV_cine").data.foreach_set("uv", uv)
    nuevo.shade_smooth()
    nombres = [g.name for g in o.vertex_groups]
    o.data = nuevo
    for nom in nombres:
        g = o.vertex_groups.new(name=nom)
        for i in np.nonzero(pesos[:, g.index] > .001)[0]:
            g.add([int(i)], float(pesos[i, g.index]), "REPLACE")
    nuevo["anillo_cine"] = 1
    nuevo["largo"], nuevo["alto"] = largo, float(t1 - t0)
    return largo, float(t1 - t0)


def aflojar(o, semilla):
    """Cinta cedida por el uso: ondula y se hunde un poco, una sola vez."""
    me = o.data
    if me.get("aflojada"):
        return
    rng = np.random.default_rng(semilla)
    n = len(me.vertices)
    p = np.empty(n * 3, np.float64)
    me.vertices.foreach_get("co", p)
    p = p.reshape(-1, 3)
    c = p.mean(0)
    ang = np.arctan2(p[:, 1] - c[1], p[:, 0] - c[0])
    alt = p[:, 2] - c[2]
    onda = sum(rng.normal(0, 1) * np.sin(k * ang + rng.uniform(0, 6.3) + alt * rng.normal(0, 40)) / k ** .7 for k in (3, 5, 8, 13, 21))
    radial = (p - c) * (1, 1, 0)
    radial /= np.maximum(np.linalg.norm(radial, axis=1, keepdims=True), 1e-6)
    p += radial * (onda * .0006)[:, None]
    p[:, 2] += sum(rng.normal(0, 1) * np.sin(k * ang + rng.uniform(0, 6.3)) for k in (2, 3, 7)) * .0009
    me.vertices.foreach_set("co", p.ravel())
    me.update()
    me["aflojada"] = 1


def material(c, imgs, nombre_uv):
    nom = c["objeto"] + "_cine"
    if nom in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials[nom])
    m = bpy.data.materials.new(nom)
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    p = next(n for n in N if n.type == "BSDF_PRINCIPLED")
    uv = N.new("ShaderNodeUVMap")
    uv.uv_map = nombre_uv
    col = N.new("ShaderNodeTexImage")
    nor = N.new("ShaderNodeTexImage")
    rug = N.new("ShaderNodeTexImage")
    for t, im in ((col, imgs[0]), (nor, imgs[1]), (rug, imgs[2])):
        t.image = im
        t.interpolation = "Cubic"
        L.new(uv.outputs[0], t.inputs[0])
    nm = N.new("ShaderNodeNormalMap")
    nm.uv_map = nombre_uv
    nm.inputs["Strength"].default_value = .6
    L.new(nor.outputs[0], nm.inputs["Color"])
    L.new(nm.outputs[0], p.inputs["Normal"])
    L.new(col.outputs[0], p.inputs["Base Color"])
    L.new(col.outputs["Alpha"], p.inputs["Alpha"])
    L.new(rug.outputs[0], p.inputs["Roughness"])
    # lana: casi sin reflejo directo, pelusa que aclara los bordes y la luz entra un poco en la fibra
    p.inputs["Specular IOR Level"].default_value = .28
    p.inputs["Sheen Weight"].default_value = .55
    p.inputs["Sheen Roughness"].default_value = .45
    L.new(col.outputs[0], p.inputs["Sheen Tint"])
    p.inputs["Subsurface Weight"].default_value = .12
    p.inputs["Subsurface Radius"].default_value = (.9, .55, .3)
    p.inputs["Subsurface Scale"].default_value = .0012
    for i, n in enumerate((uv, col, nor, rug, nm)):
        n.location = (-900 + (i > 0) * 300 + (i == 4) * 300, 300 - i * 280)
    # brillo de tela segun el angulo, con el grupo del add-on Poliigon (GPL), sin instalarlo
    if "Poliigon_Fabric_Falloff" not in bpy.data.node_groups:
        with bpy.data.libraries.load(POLIIGON) as (ori, des):
            des.node_groups = ["Poliigon_Fabric_Falloff"]
    g = N.new("ShaderNodeGroup")
    g.node_tree = bpy.data.node_groups["Poliigon_Fabric_Falloff"]
    g.name = "tela_falloff"
    g.location = (-250, 200)
    L.new(col.outputs[0], g.inputs["Base Color"])
    L.new(rug.outputs[0], g.inputs["Roughness"])
    L.new(nm.outputs[0], g.inputs["Normal"])
    L.new(g.outputs["Base Color"], p.inputs["Base Color"])
    L.new(g.outputs["Roughness"], p.inputs["Roughness"])
    L.new(g.outputs["Normal"], p.inputs["Normal"])
    return m


def interior(c, im, nombre_uv):
    nom = c["objeto"] + "_interior"
    if nom in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials[nom])
    m = bpy.data.materials.new(nom)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    p = next(n for n in N if n.type == "BSDF_PRINCIPLED")
    uv = N.new("ShaderNodeUVMap")
    uv.uv_map = nombre_uv
    t = N.new("ShaderNodeTexImage")
    t.image = im
    L.new(uv.outputs[0], t.inputs[0])
    L.new(t.outputs["Alpha"], p.inputs["Alpha"])
    p.inputs["Base Color"].default_value = (*[v * .35 for v in c["color"]], 1)
    p.inputs["Roughness"].default_value = .95
    return m


def texturizar(c):
    o = bpy.data.objects[c["objeto"]]
    c = dict(c)
    c["largo"], c["alto"] = malla_limpia(o)
    me = o.data
    aflojar(o, c["semilla"])
    altura, color, rug, alfa = tejer(c)
    n = c["objeto"]
    imgs = (imagen(n + "_color", a_srgb(color), False, alfa), imagen(n + "_normal", normal_de(altura, c["px_mm"]), True), imagen(n + "_rugosidad", rug, True))
    m = material(c, imgs, "UV_cine")
    # el desgaste solo va en la cara visible; la que toca la media lleva un material liso que comparte el recorte
    me.materials.clear()
    me.materials.append(m)
    me.materials.append(interior(c, imgs[0], "UV_cine"))
    mod = o.modifiers.get("grosor_cine") or o.modifiers.new("grosor_cine", "SOLIDIFY")
    mod.thickness = c["grosor"]
    mod.use_rim = False  # con el borde cerrado no se veria el deshilachado
    mod.material_offset = 1  # la capa nueva queda por dentro y usa el material liso
    mod.offset = 1  # hacia fuera, sin hundirse en la media
    mod.use_quality_normals = True
    return {"textura": imgs[0].size[:], "largo_m": round(c["largo"], 3), "alto_m": round(c["alto"], 3)}


if "CINE_LOTE" not in globals():
    resultado_cine = texturizar(CINTA_MEDIA)
