"""Exporta personajes de Napoleon: Total War a .glb (Blender: File > Import > glTF 2.0).

Uso:  python -I exportar_personajes.py [prueba]
Salida: capitulos/delgada_linea_roja/personajes_napoleon/
"""
import io, json, os, re, struct, sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ntw_lib import Packs, leer_anim, leer_parte, matrices_mundo, posed_parte, cola_attach, quat_mat

SALIDA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "personajes_napoleon")
P = Packs()

# Colores de la mascara (R, G, B) tomados del cuadro de Gibb: en el juego los tine la faccion.
TINTE_HIGHLAND = ((168, 28, 22), (225, 195, 120), (60, 60, 62))
TINTE_HUSAR = ((96, 118, 138), (205, 190, 150), (45, 50, 62))
TINTE_COSACO = ((52, 62, 84), (170, 40, 35), (40, 40, 45))

UNIDADES = {
    "highlanders": [("britain_inf_line_british_highland_foot", TINTE_HIGHLAND),
                    ("britain_inf_elite_british_black_watch", TINTE_HIGHLAND)],
    "husares_rusos": [("russia_cav_light_russian_hussars", TINTE_HUSAR),
                      ("russia_cav_light_russian_lifeguard_hussars", TINTE_HUSAR),
                      ("russia_cav_light_russian_pavlograd_hussars", TINTE_HUSAR)],
    "cosacos_rusos": [("russia_cav_lancer_russian_cossack_cavalry", TINTE_COSACO)],
}
# Pose T de referencia del juego (tabla anim_reference_poses) y su equivalente del caballo: son la posicion neutral.
ANIM_HOMBRE = "animations/reference/tpose.anim"
ANIM_CABALLO = "animations/horse/horse_base.anim"
ES_ARMA = r"musket|rifle|carbine|sabre|sword|hanger|lance|pistol|flagpole|bayonet|ramrod|cutlass|rapier|talwar|boardingaxe|club|airrifle"
CATEGORIAS = ("hands", "heads", "belts", "hats", "legs", "plumes", "shoulders", "torsos")


# ------------------------------------------------------------------ texturas
def buscar_tex(base, suf):
    base = base.lower()
    for k in (f"{base}_{suf}.dds", f"{base}[01]_{suf}.dds"):
        if P.existe(k):
            return k
    return None


def abrir(k):
    return Image.open(io.BytesIO(P.leer(k))).convert("RGBA")


def difusa_tenida(base, tinte):
    k = buscar_tex(base, "diffuse")
    if not k:
        return None
    im = np.asarray(abrir(k)).astype(np.float32) / 255.0
    km = buscar_tex(base, "colour_mask")
    rgb = im[..., :3]
    if km and tinte:
        ma = abrir(km)
        if ma.size != (im.shape[1], im.shape[0]):
            ma = ma.resize((im.shape[1], im.shape[0]))
        ma = np.asarray(ma).astype(np.float32) / 255.0
        for i in range(3):
            c = np.array(tinte[i], dtype=np.float32) / 255.0
            rgb = rgb * (1 - ma[..., i:i + 1]) + rgb * c * ma[..., i:i + 1]
    out = np.dstack([np.clip(rgb, 0, 1), im[..., 3]])
    return Image.fromarray((out * 255).astype(np.uint8), "RGBA")


def normal_gltf(base):
    k = buscar_tex(base, "normal")
    if not k:
        return None
    # El juego guarda X en R e Y en A (pixel.rab en util.fx_fragment); Z se reconstruye.
    # R tiene solo 5 bits por el DXT5: se suaviza para que el escalonado no brille a puntos.
    im = abrir(k)
    r = np.asarray(im.getchannel("R").filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255.0
    al = np.asarray(im.getchannel("A").filter(ImageFilter.GaussianBlur(.6))).astype(np.float32) / 255.0
    x, y = r * 2 - 1, al * 2 - 1
    z = np.sqrt(np.clip(1 - x * x - y * y, 0, 1))
    out = np.dstack([x * .5 + .5, y * .5 + .5, z * .5 + .5])
    return Image.fromarray((out * 255).astype(np.uint8), "RGB")


def rugosidad_gltf(base):
    """Del mapa de brillo del juego: G es el nivel de especular (la tela casi no brilla). glTF lee la rugosidad en G."""
    k = buscar_tex(base, "gloss_map")
    if not k:
        return None
    g = np.asarray(abrir(k)).astype(np.float32)[..., 1] / 255.0
    rug = np.clip(1 - g * .75, .3, 1)
    cero = np.zeros_like(rug)
    return Image.fromarray((np.dstack([cero, rug, cero]) * 255).astype(np.uint8), "RGB")


def material_de(g, base, tinte, nombre, alfa=False):
    """Material completo de una textura del juego: difusa, normales y rugosidad."""
    dif, nor, rug = difusa_tenida(base, tinte), normal_gltf(base), rugosidad_gltf(base)
    if dif is not None and dif.size[0] > 2048:
        dif = dif.resize((2048, 2048))
    return g.material(nombre, g.imagen(png(dif), nombre + "_difusa") if dif else None,
                      g.imagen(png(nor), nombre + "_normal") if nor else None, alfa=alfa,
                      rugosa=g.imagen(png(rug), nombre + "_rugosidad") if rug else None)


def png(im):
    # lado potencia de dos: hay visores que no aceptan otra cosa
    lado = [2 ** round(np.log2(max(v, 1))) for v in im.size]
    if tuple(lado) != im.size:
        im = im.resize(lado)
    b = io.BytesIO()
    im.save(b, "PNG", optimize=False)
    return b.getvalue()


def guardar_originales(base):
    """Copia las texturas tal cual a PNG para poder retocarlas."""
    for suf in ("diffuse", "normal", "gloss_map", "colour_mask"):
        k = buscar_tex(base, suf)
        if not k:
            continue
        d = os.path.join(SALIDA, "texturas_originales", os.path.dirname(k).replace("variantmodels/", ""))
        os.makedirs(d, exist_ok=True)
        f = os.path.join(d, os.path.basename(k)[:-4] + ".png")
        if not os.path.exists(f):
            abrir(k).save(f)


# ------------------------------------------------------------------ glb
class Glb:
    def __init__(self):
        self.bin = bytearray()
        self.j = {"asset": {"version": "2.0", "generator": "extractor delgada_linea_roja"},
                  "scene": 0, "scenes": [{"nodes": []}], "nodes": [], "meshes": [], "skins": [],
                  "materials": [], "textures": [], "images": [], "samplers": [{"magFilter": 9729, "minFilter": 9987}],
                  "accessors": [], "bufferViews": []}

    def vista(self, datos, target=None):
        while len(self.bin) % 4:
            self.bin.append(0)
        v = {"buffer": 0, "byteOffset": len(self.bin), "byteLength": len(datos)}
        if target:
            v["target"] = target
        self.bin += datos
        self.j["bufferViews"].append(v)
        return len(self.j["bufferViews"]) - 1

    def acc(self, arr, tipo, comp, target=None, minmax=False):
        v = self.vista(arr.tobytes(), target)
        a = {"bufferView": v, "componentType": comp, "count": len(arr), "type": tipo}
        if minmax:
            a["min"] = arr.min(0).tolist()
            a["max"] = arr.max(0).tolist()
        self.j["accessors"].append(a)
        return len(self.j["accessors"]) - 1

    def imagen(self, datos, nombre):
        v = self.vista(datos)
        self.j["images"].append({"bufferView": v, "mimeType": "image/png", "name": nombre})
        self.j["textures"].append({"source": len(self.j["images"]) - 1, "sampler": 0})
        return len(self.j["textures"]) - 1

    def material(self, nombre, difusa, normal, alfa=False, rugosa=None):
        m = {"name": nombre, "doubleSided": True,
             "pbrMetallicRoughness": {"metallicFactor": 0.0, "roughnessFactor": 1.0 if rugosa is not None else 0.9}}
        if rugosa is not None:
            m["pbrMetallicRoughness"]["metallicRoughnessTexture"] = {"index": rugosa}
        if difusa is not None:
            m["pbrMetallicRoughness"]["baseColorTexture"] = {"index": difusa}
        if normal is not None:
            m["normalTexture"] = {"index": normal}
        if alfa:
            m["alphaMode"] = "MASK"
            m["alphaCutoff"] = 0.5
        self.j["materials"].append(m)
        return len(self.j["materials"]) - 1

    def guardar(self, path):
        for k in [k for k, v in self.j.items() if isinstance(v, list) and not v]:
            del self.j[k]
        while len(self.bin) % 4:
            self.bin.append(0)
        self.j["buffers"] = [{"byteLength": len(self.bin)}]
        js = json.dumps(self.j, separators=(",", ":")).encode()
        js += b" " * (-len(js) % 4)
        with open(path, "wb") as f:
            f.write(struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(js) + 8 + len(self.bin)))
            f.write(struct.pack("<I4s", len(js), b"JSON") + js)
            f.write(struct.pack("<I4s", len(self.bin), b"BIN\0") + bytes(self.bin))


def mat_quat(m):
    """Matriz de rotacion a cuaternion xyzw."""
    a = np.array([1 + m[0, 0] + m[1, 1] + m[2, 2], 1 + m[0, 0] - m[1, 1] - m[2, 2],
                  1 - m[0, 0] + m[1, 1] - m[2, 2], 1 - m[0, 0] - m[1, 1] + m[2, 2]])
    k = int(np.argmax(a))
    s = 2 * np.sqrt(max(a[k], 1e-12))
    if k == 0:
        q = [m[2, 1] - m[1, 2], m[0, 2] - m[2, 0], m[1, 0] - m[0, 1], s * s / 4]
    elif k == 1:
        q = [s * s / 4, m[0, 1] + m[1, 0], m[0, 2] + m[2, 0], m[2, 1] - m[1, 2]]
    elif k == 2:
        q = [m[0, 1] + m[1, 0], s * s / 4, m[1, 2] + m[2, 1], m[0, 2] - m[2, 0]]
    else:
        q = [m[0, 2] + m[2, 0], m[1, 2] + m[2, 1], s * s / 4, m[1, 0] - m[0, 1]]
    q = np.array(q) / s
    return q / np.linalg.norm(q)


def tangentes(pos, nor, uv, ind):
    """Tangentes por vertice para el mapa de normales; sin ellas cada visor calcula las suyas."""
    t = ind.reshape(-1, 3)
    e1, e2 = pos[t[:, 1]] - pos[t[:, 0]], pos[t[:, 2]] - pos[t[:, 0]]
    d1, d2 = uv[t[:, 1]] - uv[t[:, 0]], uv[t[:, 2]] - uv[t[:, 0]]
    det = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
    r = np.where(np.abs(det) > 1e-12, 1 / np.where(np.abs(det) > 1e-12, det, 1), 0)[:, None]
    td = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) * r
    bd = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) * r
    tan, bit = np.zeros_like(pos), np.zeros_like(pos)
    for k in range(3):
        np.add.at(tan, t[:, k], td)
        np.add.at(bit, t[:, k], bd)
    tan -= nor * np.sum(nor * tan, axis=1, keepdims=True)
    largo = np.linalg.norm(tan, axis=1)
    # vertices sin UV util: cualquier eje perpendicular a la normal
    malos = largo < 1e-9
    if malos.any():
        eje = np.where(np.abs(nor[malos, 0:1]) < .9, [[1.0, 0, 0]], [[0, 1.0, 0]])
        tan[malos] = np.cross(nor[malos], eje)
        largo = np.linalg.norm(tan, axis=1)
    tan /= np.maximum(largo, 1e-9)[:, None]
    w = np.where(np.sum(np.cross(nor, tan) * bit, axis=1) < 0, -1.0, 1.0)
    return np.column_stack([tan, w])


def atributos(g, pos, nor, uv, ind):
    """POSITION, NORMAL, TANGENT y TEXCOORD_0 con normales y tangentes unitarias."""
    pos, uv = np.asarray(pos, dtype=np.float64), np.asarray(uv, dtype=np.float64)
    nor = np.array(nor, dtype=np.float64)
    largo = np.linalg.norm(nor, axis=1)
    nor[largo < 1e-9] = (0, 0, 1)
    nor /= np.maximum(np.linalg.norm(nor, axis=1, keepdims=True), 1e-9)
    tan = tangentes(pos, nor, uv, np.asarray(ind))
    return {"POSITION": g.acc(pos.astype(np.float32), "VEC3", 5126, 34962, True),
            "NORMAL": g.acc(nor.astype(np.float32), "VEC3", 5126, 34962),
            "TANGENT": g.acc(tan.astype(np.float32), "VEC4", 5126, 34962),
            "TEXCOORD_0": g.acc(uv.astype(np.float32), "VEC2", 5126, 34962)}


def anadir_esqueleto(g, hs, W, nombre):
    """Crea los huesos; devuelve el indice de skin y deja los huesos en la escena."""
    base = len(g.j["nodes"])
    hijos = {i: [] for i in range(len(hs))}
    raices = []
    for i, (_, par) in enumerate(hs):
        (raices if par < 0 else hijos[par]).append(i)
    for i, (nom, par) in enumerate(hs):
        loc = W[i] if par < 0 else np.linalg.inv(W[par]) @ W[i]
        # traslacion y rotacion, no matriz: el visor 3D de Windows no aplica bien la matriz en los huesos
        n = {"name": nom, "translation": loc[:3, 3].tolist(), "rotation": mat_quat(loc[:3, :3]).tolist()}
        if hijos[i]:
            n["children"] = [base + h for h in hijos[i]]
        g.j["nodes"].append(n)
    ib = np.array([np.linalg.inv(m).T.flatten() for m in W], dtype=np.float32)
    g.j["skins"].append({"name": nombre, "joints": [base + i for i in range(len(hs))],
                         "inverseBindMatrices": g.acc(ib, "MAT4", 5126)})
    arm = len(g.j["nodes"])
    g.j["skins"][-1]["skeleton"] = arm
    g.j["nodes"].append({"name": nombre + "_armature", "children": [base + r for r in raices]})
    g.j["scenes"][0]["nodes"].append(arm)
    return len(g.j["skins"]) - 1


def primitiva(g, pos, nor, uv, huesos, pesos, ind, mat):
    huesos = np.array(huesos, dtype=np.uint8)
    pesos = np.array(pesos, dtype=np.float32)
    huesos[pesos <= 0] = 0  # sin peso, el indice de hueso tiene que ser 0
    pesos /= np.maximum(pesos.sum(axis=1, keepdims=True), 1e-9)
    ind = np.asarray(ind, dtype=np.uint32)
    pr = {"attributes": dict(atributos(g, pos, nor, uv, ind),
                             JOINTS_0=g.acc(huesos, "VEC4", 5121, 34962),
                             WEIGHTS_0=g.acc(pesos, "VEC4", 5126, 34962)),
          "indices": g.acc(ind, "SCALAR", 5125, 34963), "material": mat}
    return pr


def normales_de_caras(pos, ind):
    n = np.zeros_like(pos)
    t = ind.reshape(-1, 3)
    c = np.cross(pos[t[:, 1]] - pos[t[:, 0]], pos[t[:, 2]] - pos[t[:, 0]])
    for k in range(3):
        np.add.at(n, t[:, k], c)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)


# ------------------------------------------------------------------ equipo
_eq = {}


def tabla_equipo():
    if _eq:
        return _eq
    for arch, tex in (("mesh", "variantmodels/equipment/texture"), ("mesh2", "variantmodels/equipment/texture2")):
        b = P.leer(f"variantmodels/equipment/{arch}.variant_part_mesh")
        ng = struct.unpack_from("<I", b, 16)[0]
        p = 36
        for _ in range(ng):
            nom = b[p:p + 80].decode("utf-16le").split("\0")[0]
            hueso, nv, ni = struct.unpack_from("<iII", b, p + 80)
            q = p + 92
            a = np.frombuffer(b, dtype=np.float32, count=nv * 16, offset=q).reshape(nv, 16).astype(np.float64)
            ind = np.frombuffer(b, dtype=np.uint16, count=ni, offset=q + nv * 64).astype(np.uint32)
            _eq[nom.lower()] = {"pos": a[:, :3], "uv": a[:, 7:9], "ind": ind, "tex": tex, "hueso": hueso}
            p = q + nv * 64 + ni * 2
    return _eq


# ------------------------------------------------------------------ soldados
def esqueleto_hombre():
    _, hs, fr = leer_anim(P.leer(ANIM_HOMBRE))
    return hs, fr[0], matrices_mundo(hs, fr[0])


def base_textura(tex):
    return tex.lower()


def partes_variant(nombre_archivo):
    b = P.leer(nombre_archivo)
    ini = struct.unpack_from("<I", b, 16)[0]
    txt = [t.decode("utf-16le") for t in re.findall(rb"(?:[\x20-\x7e]\x00){3,}", b[ini:])]
    pares, vistos = [], set()
    for i in range(len(txt) - 1):
        if txt[i].lower().endswith("/mesh"):
            seg = txt[i].lower().split("/")
            cat = next((c for c in CATEGORIAS if c in seg), None)
            if cat in vistos:
                continue
            vistos.add(cat)
            pares.append((cat, txt[i].lower(), txt[i + 1].lower()))
    armas = [t.lower() for t in txt if re.search(r"musket|sabre|sword|lance|rifle", t.lower()) and t.lower().startswith("rigid_equip")]
    return pares, armas


def soldado(nombre, tinte, salida, arma_pref=None):
    hs, _, W = esqueleto_hombre()
    id_h = {n.lower(): i for i, (n, _) in enumerate(hs)}
    id_head = id_h["head"]
    g = Glb()
    skin = anadir_esqueleto(g, hs, W, "soldado")
    prims = []
    pares, _ = partes_variant(f"variantmodels/units/{nombre}.unit_variant")
    # el penacho cuelga del punto de union del sombrero
    union = None
    for cat, malla, tex in pares:
        if cat == "hats":
            bb = P.leer(malla + ".variant_part_mesh")
            f3, cola = cola_attach(bb)
            if f3:
                f = np.frombuffer(cola, dtype=np.float32, offset=32, count=16).reshape(4, 4).astype(np.float64)
                union = f
    for cat, malla, tex in pares:
        bb = P.leer(malla + ".variant_part_mesh")
        m = leer_parte(bb)
        guardar_originales(tex)
        mat = material_de(g, tex, tinte, cat, alfa=(cat == "plumes"))
        if m["rigido"]:
            local = m["pos"]
            if union is not None:
                local = (union[:3, :3] @ local[..., None])[..., 0] + union[:3, 3]
            pos = (W[id_head, :3, :3] @ local[..., None])[..., 0] + W[id_head, :3, 3]
            n = normales_de_caras(pos, m["ind"])
            hb = np.tile([id_head, 0, 0, 0], (len(pos), 1))
            pw = np.tile([1.0, 0, 0, 0], (len(pos), 1))
        else:
            pos, n = posed_parte(m, W)
            hb = np.zeros((len(pos), 4), dtype=np.uint8)
            hb[:, 0], hb[:, 1] = m["b1"], m["b2"]
            pw = np.zeros((len(pos), 4))
            pw[:, 0], pw[:, 1] = m["w1"], 1 - m["w1"]
        prims.append(primitiva(g, pos, n, m["uv"], hb, pw, m["ind"], mat))
    # las armas van aparte, en armas_napoleon/
    g.j["meshes"].append({"name": nombre, "primitives": prims})
    g.j["nodes"].append({"name": nombre, "mesh": 0, "skin": skin})
    g.j["scenes"][0]["nodes"].append(len(g.j["nodes"]) - 1)
    g.guardar(salida)


# ------------------------------------------------------------------ caballos
def leer_caballo(b):
    n = struct.unpack_from("<I", b, 8)[0]
    p = 12
    for _ in range(n):
        l = struct.unpack_from("<H", b, p)[0]
        p += 2 + 2 * l + 4
    # propiedades vectoriales
    nv4 = struct.unpack_from("<I", b, p)[0]
    p += 4
    for _ in range(nv4):
        l = struct.unpack_from("<H", b, p)[0]
        p += 2 + 2 * l + 16
    ng = struct.unpack_from("<I", b, p)[0]
    p += 4
    gr = []
    for _ in range(ng):
        l = struct.unpack_from("<H", b, p)[0]
        nom = b[p + 2:p + 2 + 2 * l].decode("utf-16le")
        p += 2 + 2 * l
        nv, ni = struct.unpack_from("<II", b, p)
        p += 8
        gr.append([nom, nv, ni])
    res = []
    for nom, nv, ni in gr:
        p += 4
        uv, hb, pw, off, nr = [], [], [], [], []
        for _ in range(nv):
            f = struct.unpack_from("<8f", b, p)
            c = struct.unpack_from("<I", b, p + 32)[0]
            p += 36
            inf = []
            for _ in range(c):
                bi = struct.unpack_from("<I", b, p)[0]
                v = struct.unpack_from("<7f", b, p + 4)
                inf.append((bi, np.array(v[:3]), np.array(v[3:6]), v[6]))
                p += 32
            p += 16
            uv.append(f[:2])
            off.append(inf)
        p += 4
        ind = np.frombuffer(b, dtype=np.uint32, count=ni, offset=p).copy()
        p += ni * 4
        res.append({"nombre": nom, "uv": np.array(uv), "inf": off, "ind": ind})
    return res


def caballo(nombre, salida):
    _, hs, fr = leer_anim(P.leer(ANIM_CABALLO))
    W = matrices_mundo(hs, fr[0])
    g = Glb()
    skin = anadir_esqueleto(g, hs, W, "caballo")
    base = "unitmodels/horse/textures/horse"
    guardar_originales(base)
    mat = material_de(g, base, None, "caballo", alfa=True)
    prims = []
    vistos = set()
    for gr in leer_caballo(P.leer(f"unitmodels/horse/{nombre}_lod1.variant_weighted_mesh")):
        # las variantes alternativas de cabeza y cabezada: solo la 01
        tipo = re.sub(r"\d+$", "", gr["nombre"].lower())
        if tipo in vistos:
            continue
        vistos.add(tipo)
        nv = len(gr["inf"])
        pos, nr = np.zeros((nv, 3)), np.zeros((nv, 3))
        hb = np.zeros((nv, 4), dtype=np.uint8)
        pw = np.zeros((nv, 4))
        for i, inf in enumerate(gr["inf"]):
            for k, (bi, of, n, w) in enumerate(inf[:4]):
                pos[i] += w * (W[bi, :3, :3] @ of + W[bi, :3, 3])
                nr[i] += w * (W[bi, :3, :3] @ n)
                hb[i, k], pw[i, k] = bi, w
        nr /= np.maximum(np.linalg.norm(nr, axis=1, keepdims=True), 1e-9)
        prims.append(primitiva(g, pos, nr, gr["uv"], hb, pw, gr["ind"], mat))
    g.j["meshes"].append({"name": nombre, "primitives": prims})
    g.j["nodes"].append({"name": nombre, "mesh": 0, "skin": skin})
    g.j["scenes"][0]["nodes"].append(len(g.j["nodes"]) - 1)
    g.guardar(salida)


def main(prueba=False):
    os.makedirs(SALIDA, exist_ok=True)
    hechos, fallos = [], []
    for carpeta, lista in UNIDADES.items():
        d = os.path.join(SALIDA, carpeta)
        os.makedirs(d, exist_ok=True)
        for unidad, tinte in lista:
            roles = sorted(os.path.basename(n)[len(unidad) + 1:-len(".unit_variant")]
                           for n in P.lista("variantmodels/units/" + unidad + ".", ".unit_variant"))
            for rol in roles:
                if prueba and (rol != "soldier" or not unidad.endswith(("highland_foot", "russian_hussars"))):
                    continue
                f = os.path.join(d, f"{unidad}.{rol}.glb")
                try:
                    soldado(f"{unidad}.{rol}", tinte, f)
                    hechos.append(f)
                    print("ok", os.path.basename(f), os.path.getsize(f) // 1024, "KB", flush=True)
                except Exception as e:
                    fallos.append((f, repr(e)))
                    print("FALLO", f, repr(e), flush=True)
    d = os.path.join(SALIDA, "caballos")
    os.makedirs(d, exist_ok=True)
    for letra in "abcdef":
        for tipo in ("hussar", "basic"):
            if prueba and (letra, tipo) != ("a", "hussar"):
                continue
            nom = f"horse_{letra}_{tipo}"
            f = os.path.join(d, nom + ".glb")
            try:
                caballo(nom, f)
                hechos.append(f)
                print("ok", nom, os.path.getsize(f) // 1024, "KB", flush=True)
            except Exception as e:
                fallos.append((f, repr(e)))
                print("FALLO", nom, repr(e), flush=True)
    print("HECHOS", len(hechos), "FALLOS", len(fallos))
    for x in fallos:
        print(x)


if __name__ == "__main__":
    main("prueba" in sys.argv)
