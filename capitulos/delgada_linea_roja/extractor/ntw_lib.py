"""Lectura de datos de Napoleon: Total War: .pack, .anim y mallas de unidades.

Solo lee la carpeta del juego; nunca escribe en ella.
"""
import glob, io, json, os, struct

import numpy as np
from PIL import Image

DATA = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\delgada_linea_roja\Nueva carpeta\data"
# Los parches pisan a los packs base.
ORDEN = ["data", "rigidmodels", "variantmodels", "variantmodels2", "patch", "patch2", "patch3", "patch4", "patch5", "patch6", "patch7"]


def _indice_pack(path):
    with open(path, "rb") as f:
        f.read(4)
        _, _, tamrep, nfiles, tamidx = struct.unpack("<5I", f.read(20))
        f.read(tamrep)
        idx = f.read(tamidx)
        off = f.tell()
    res, p = {}, 0
    for _ in range(nfiles):
        tam = struct.unpack_from("<I", idx, p)[0]
        p += 4
        fin = idx.index(b"\0", p)
        res[idx[p:fin].decode("latin1").replace("\\", "/").lower()] = (path, off, tam)
        p = fin + 1
        off += tam
    return res


class Packs:
    def __init__(self):
        self.t = {}
        for n in ORDEN:
            self.t.update(_indice_pack(os.path.join(DATA, n + ".pack")))

    def leer(self, nom):
        path, off, tam = self.t[nom.lower().replace("\\", "/")]
        with open(path, "rb") as f:
            f.seek(off)
            return f.read(tam)

    def existe(self, nom):
        return nom.lower().replace("\\", "/") in self.t

    def lista(self, ini="", fin=""):
        return [n for n in self.t if n.startswith(ini) and n.endswith(fin)]


# ---------------------------------------------------------------- animaciones
def leer_anim(b):
    """Devuelve (fps, huesos[(nombre, padre)], frames: array frames*huesos*(pos3+quat4 xyzw))."""
    fps, _, nb = struct.unpack_from("<ffI", b, 0)
    p, hs = 12, []
    for _ in range(nb):
        n = struct.unpack_from("<H", b, p)[0]
        p += 2
        nom = b[p:p + 2 * n].decode("utf-16le")
        p += 2 * n
        hs.append((nom, struct.unpack_from("<i", b, p)[0]))
        p += 4
    nf = struct.unpack_from("<I", b, p)[0]
    p += 4
    resto = (len(b) - p) // 4
    por = resto // max(nf * nb, 1)  # 7 floats en hombres, 10 en caballos (la cola es basura 0.001)
    a = np.frombuffer(b, dtype=np.float32, count=nf * nb * por, offset=p).reshape(nf, nb, por)
    return fps, hs, a[:, :, :7].astype(np.float64)


def quat_mat(q):
    x, y, z, w = q / np.linalg.norm(q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def matrices_mundo(hs, pose):
    """Local TRS -> matrices de mundo (4x4). El padre siempre va antes que el hijo."""
    n = len(hs)
    w = np.zeros((n, 4, 4))
    for i, (_, par) in enumerate(hs):
        m = np.eye(4)
        m[:3, :3] = quat_mat(pose[i, 3:7])
        m[:3, 3] = pose[i, :3]
        w[i] = m if par < 0 else w[par] @ m
    return w


# ---------------------------------------------------------------- mallas de partes
def _n8(a):
    return a.astype(np.float64) / 127.5 - 1.0


def leer_parte(b):
    """Malla variant_part_mesh, solo LOD 0. Devuelve dict con los datos crudos de vertice."""
    magic, _, f2, f3, ng, tv, ti = struct.unpack_from("<4sIIIIII", b, 0)
    assert magic == b"VMPF"
    nv, ni = struct.unpack_from("<II", b, 36)
    p = 44
    if f2 == 1:
        v = np.frombuffer(b, dtype=np.uint8, count=nv * 40, offset=p).reshape(nv, 40)
        h = np.frombuffer(b, dtype=np.float16, count=nv * 20, offset=p).reshape(nv, 20).astype(np.float64)
        ind = np.frombuffer(b, dtype=np.uint16, count=ni, offset=p + nv * 40).astype(np.uint32)
        return {
            "rigido": False,
            "off1": h[:, 0:3], "off2": h[:, 4:7], "uv": h[:, [3, 7]],
            "n1": _n8(v[:, 24:27]), "n2": _n8(v[:, 28:31]),
            "b1": v[:, 27].astype(int), "b2": v[:, 31].astype(int),
            "w1": v[:, 35].astype(np.float64) / 255.0,
            "ind": ind,
        }
    if f2 == 0:
        a = np.frombuffer(b, dtype=np.float32, count=nv * 16, offset=p).reshape(nv, 16).astype(np.float64)
        ind = np.frombuffer(b, dtype=np.uint16, count=ni, offset=p + nv * 64).astype(np.uint32)
        return {"rigido": True, "pos": a[:, :3], "uv": a[:, 7:9], "ind": ind}
    raise ValueError("malla no soportada f2=%d" % f2)


def cola_attach(b):
    """Tras los grupos, f3=1 anade un bloque de 100 bytes (punto de union del penacho)."""
    f2, f3, ng = struct.unpack_from("<III", b, 8)
    st = {1: 40, 0: 64}[f2]
    p = 36
    for _ in range(ng):
        nv, ni = struct.unpack_from("<II", b, p)
        p += 8 + nv * st + ni * 2
    return f3, b[p:p + 100] if f3 else b""


def posed_parte(m, W):
    """Posicion y normal de cada vertice con las matrices de mundo W."""
    if m["rigido"]:
        return m["pos"], None
    p1 = (W[m["b1"], :3, :3] @ m["off1"][..., None])[..., 0] + W[m["b1"], :3, 3]
    p2 = (W[m["b2"], :3, :3] @ m["off2"][..., None])[..., 0] + W[m["b2"], :3, 3]
    n1 = (W[m["b1"], :3, :3] @ m["n1"][..., None])[..., 0]
    n2 = (W[m["b2"], :3, :3] @ m["n2"][..., None])[..., 0]
    w = m["w1"][:, None]
    pos = p1 * w + p2 * (1 - w)
    nor = n1 * w + n2 * (1 - w)
    nor /= np.maximum(np.linalg.norm(nor, axis=1, keepdims=True), 1e-9)
    return pos, nor


# ---------------------------------------------------------------- unit_variant
def leer_variant(b):
    """Devuelve {categoria: [(malla, textura), ...]}; ignora el equipo rigido."""
    magic, _, ncat, _, ini = struct.unpack_from("<4sIIII", b, 0)
    assert magic == b"VRNT"
    cats = []
    p = 20
    tam_cat = (ini - 20) // ncat
    for i in range(ncat):
        reg = b[p + i * tam_cat:p + (i + 1) * tam_cat]
        nom = reg[:512].decode("utf-16le").split("\0")[0]
        cats.append((nom, struct.unpack("<II", reg[512:520])))
    return cats, ini


# ---------------------------------------------------------------- texturas
def dds_a_png(raw):
    im = Image.open(io.BytesIO(raw))
    im.load()
    return im
