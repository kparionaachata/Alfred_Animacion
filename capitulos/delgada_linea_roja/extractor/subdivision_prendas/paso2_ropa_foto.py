"""Materiales fotorrealistas para el personaje abierto en Blender: el dibujo del juego con tela y cuero fotografiados encima.

Fotos CC0 de materiales/ambientcg (Fabric031 y Leather037), empaquetadas en el .blend. Cada mascara decide donde va tela y
donde cuero; piel, plumas, botones y metal quedan como estan. Se puede ejecutar varias veces.
Uso (dentro de Blender):  exec(open(r"...\\ropa_foto.py", encoding="utf-8").read())
"""
import os

import numpy as np

import bpy

RAIZ = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\delgada_linea_roja\materiales\ambientcg"
# repeticiones de la foto en u y v: una baldosa mide unos 20 cm en todas las piezas
REPETIR = {"torsos": (5, 5), "legs": (4.5, 4), "shoulders": (1.5, 1.05), "hats": (1.5, 3), "belts": (.35, 8)}


def imagen(carpeta, mapa, datos=True):
    ruta = os.path.join(RAIZ, carpeta, f"{carpeta}_2K-JPG_{mapa}.jpg")
    im = bpy.data.images.load(ruta, check_existing=True)
    im.colorspace_settings.name = "Non-Color" if datos else "sRGB"
    if not im.packed_file:
        im.pack()
    return im


def leer(nom):
    im = bpy.data.images[nom]
    w, h = im.size
    px = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(px)
    return px.reshape(h, w, 4)[::-1]


def mascara(nombre):
    """Imagen con R = cuanta tela y G = cuanto cuero. Se decide con el brillo y la zona de la textura del juego."""
    d = leer(nombre + "_difusa")[..., :3]
    rug = leer(nombre + "_rugosidad")[..., 1]
    h, w = rug.shape
    fila, col = np.mgrid[0:h, 0:w]
    fy, cx = fila / h, col / w
    lum = d.mean(axis=2)
    tela = np.where(rug < .6, 0.0, np.where(rug < .97, .55, 1.0))  # metal fuera, cordon a media fuerza
    cuero = np.zeros_like(tela)
    if nombre == "legs":
        tela[(fy > .31) & (fy < .62) & (cx < .62)] = 0  # piel de la pierna
        sat = (d.max(axis=2) - d.min(axis=2)) / np.maximum(d.max(axis=2), 1e-4)
        zap = (fy > .84) & (cx < .56) & (lum < .2) & (sat < .3)
        tela[zap] = 0
        cuero[zap] = 1
    elif nombre == "hats":
        tela[cx < .755] = 0  # plumas: solo la franja cuadriculada es tela
        vis = ((rug < .9) & (fy < .5) & (cx > .25) & (cx < .6)) | ((fy > .7) & (rug < .9) & (cx < .755))
        cuero[vis] = 1
    elif nombre == "shoulders":
        tela = np.where(rug < .6, 0.0, 1.0)
    elif nombre == "belts":
        tela[:] = .45  # cinta de ante blanqueado: tejido apenas visible
    nom = "tela_mascara_" + nombre
    if nom in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[nom])
    im = bpy.data.images.new(nom, w, h, alpha=False, float_buffer=False)
    im.colorspace_settings.name = "Non-Color"
    p = np.ones((h, w, 4), np.float32)
    p[..., 0], p[..., 1], p[..., 2] = tela, cuero, 0
    im.pixels.foreach_set(p[::-1].ravel())
    im.update()
    im.pack()
    return im


def media_foto(im):
    w, h = im.size
    px = np.empty(w * h * im.channels, np.float32)
    im.pixels.foreach_get(px)
    # los pixeles estan en sRGB y el nodo devuelve valores lineales: la media tiene que ser lineal o todo se oscurece
    c = px.reshape(h, w, im.channels)[..., :3]
    return float(np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4).mean())


def construir(nombre):
    m = bpy.data.materials[nombre]
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    for n in [n for n in N if n.name.startswith("tela_")]:
        N.remove(n)
    p = next(n for n in N if n.type == "BSDF_PRINCIPLED")
    dif = next(n for n in N if n.type == "TEX_IMAGE" and n.image.name.endswith("_difusa"))
    nor = next(n for n in N if n.type == "TEX_IMAGE" and n.image.name.endswith("_normal"))
    sep = next(n for n in N if n.type == "SEPARATE_COLOR")
    nm = next(n for n in N if n.type == "NORMAL_MAP")
    dif.interpolation = nor.interpolation = "Cubic"  # sin bloques de pixel de la textura pequena

    cuenta = [0]

    def nodo(tipo):
        n = N.new(tipo)
        cuenta[0] += 1
        n.name = f"tela_{cuenta[0]:02d}"
        n.location = (-1800 + (cuenta[0] % 8) * 180, -700 - (cuenta[0] // 8) * 260)
        return n

    def mate(op, a, b=None):
        n = nodo("ShaderNodeMath")
        n.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                L.new(v, n.inputs[i])
        return n.outputs[0]

    def vec(op, a, b=None):
        n = nodo("ShaderNodeVectorMath")
        n.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (tuple, list)):
                n.inputs[i].default_value = v
            else:
                L.new(v, n.inputs[i])
        return n.outputs[0]

    def mezcla(f, a, b):
        n = nodo("ShaderNodeMix")
        n.data_type = "FLOAT"
        L.new(f, n.inputs[0])
        for i, v in ((2, a), (3, b)):
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                L.new(v, n.inputs[i])
        return n.outputs[0]

    def textura(im, uv):
        n = nodo("ShaderNodeTexImage")
        n.image = im
        L.new(uv, n.inputs[0])
        return n

    uv0 = nodo("ShaderNodeTexCoord").outputs["UV"]
    rep = nodo("ShaderNodeMapping")
    L.new(uv0, rep.inputs["Vector"])
    su, sv = REPETIR[nombre]
    rep.inputs["Scale"].default_value = (su, sv, 1)
    uv = rep.outputs[0]
    # la misma foto, girada y a otra escala, rompe la repeticion de la baldosa
    rep2 = nodo("ShaderNodeMapping")
    L.new(uv0, rep2.inputs["Vector"])
    rep2.inputs["Scale"].default_value = (su * .37, sv * .37, 1)
    rep2.inputs["Rotation"].default_value = (0, 0, .6)

    mk = textura(mascara(nombre), uv0)
    sm = nodo("ShaderNodeSeparateColor")
    L.new(mk.outputs["Color"], sm.inputs[0])
    R, G = sm.outputs["Red"], sm.outputs["Green"]

    fc = imagen("Fabric031", "Color", datos=False)
    fn = imagen("Fabric031", "NormalGL")
    fr = imagen("Fabric031", "Roughness")
    cn = imagen("Leather037", "NormalGL")
    cr = imagen("Leather037", "Roughness")
    media = media_foto(fc)

    # color: las fibras e irregularidades de la foto modulan el dibujo del juego, sin cambiar su color de fondo
    fg = nodo("ShaderNodeRGBToBW")
    L.new(textura(fc, uv).outputs["Color"], fg.inputs[0])
    gran = nodo("ShaderNodeRGBToBW")
    L.new(textura(fc, rep2.outputs[0]).outputs["Color"], gran.inputs[0])
    fibra = mate("SUBTRACT", mate("DIVIDE", fg.outputs[0], media), 1.0)
    mancha = mate("SUBTRACT", mate("DIVIDE", gran.outputs[0], media), 1.0)
    var = mate("ADD", mate("MULTIPLY", fibra, .55), mate("MULTIPLY", mancha, .35))
    fac = mate("ADD", 1.0, mate("MULTIPLY", var, R))
    # el juego satura mucho: tintes de lana mas apagados, como un tinte natural
    hs = nodo("ShaderNodeHueSaturation")
    hs.inputs["Saturation"].default_value, hs.inputs["Value"].default_value = .94, .97
    L.new(R, hs.inputs["Fac"])
    L.new(dif.outputs["Color"], hs.inputs["Color"])
    color = vec("SCALE", hs.outputs[0])
    L.new(fac, color.node.inputs["Scale"])
    L.new(color, p.inputs["Base Color"])

    # normales: pliegues del juego + tejido o cuero fotografiado, mezclados en espacio tangente
    base_n = vec("SUBTRACT", vec_escalar(N, L, nor.outputs["Color"], 2.0, nodo), (1, 1, 1))
    det_t = vec("SUBTRACT", vec_escalar(N, L, textura(fn, uv).outputs["Color"], 2.0, nodo), (1, 1, 1))
    det_c = vec("SUBTRACT", vec_escalar(N, L, textura(cn, uv).outputs["Color"], 2.0, nodo), (1, 1, 1))
    def plano(v, f):
        s = nodo("ShaderNodeSeparateXYZ")
        L.new(v, s.inputs[0])
        c = nodo("ShaderNodeCombineXYZ")
        L.new(mate("MULTIPLY", s.outputs[0], f), c.inputs[0])
        L.new(mate("MULTIPLY", s.outputs[1], f), c.inputs[1])
        return c.outputs[0]
    suma = vec("ADD", vec("ADD", base_n, plano(det_t, mate("MULTIPLY", R, .9))), plano(det_c, mate("MULTIPLY", G, .8)))
    unit = vec("NORMALIZE", suma)
    col_n = vec("ADD", vec_escalar(N, L, unit, .5, nodo), (.5, .5, .5))
    L.new(col_n, nm.inputs["Color"])
    nm.inputs["Strength"].default_value = 1.15

    # respuesta a la luz: lana mate con brillo de borde; cuero algo pulido; el resto, como el juego
    tr = mate("ADD", .72, mate("MULTIPLY", textura(fr, uv).outputs["Color"], .28))
    tc = mate("ADD", .28, mate("MULTIPLY", textura(cr, uv).outputs["Color"], .35))
    rug = mezcla(G, mezcla(R, sep.outputs["Green"], tr), tc)
    L.new(rug, p.inputs["Roughness"])
    L.new(mate("MULTIPLY", R, .3), p.inputs["Sheen Weight"])
    p.inputs["Sheen Roughness"].default_value = .5
    L.new(hs.outputs[0], p.inputs["Sheen Tint"])
    L.new(mezcla(R, mezcla(G, .5, .45), .2), p.inputs["Specular IOR Level"])
    return nombre


def vec_escalar(N, L, v, k, nodo):
    n = nodo("ShaderNodeVectorMath")
    n.operation = "SCALE"
    L.new(v, n.inputs[0])
    n.inputs["Scale"].default_value = k
    return n.outputs[0]


resultado_ropa = [construir(n) for n in REPETIR]
