# -*- coding: utf-8 -*-
"""Partes COMUNES (sin bpy) de la automatizacion de cadenas: configuracion, huellas de los pasos, estado guardado, respaldos y decision de
DESDE QUE PASO hay que reconstruir. Lo usan `cadena_runner.py` (dentro de Blender), `lanzador.py` (fuera) y `panel_cadena.py` (el panel)."""
import os, json, hashlib, shutil, time, glob

AUTO = os.path.dirname(os.path.abspath(__file__))                     # .../capitulo_4/automatizacion
CAPITULO = os.path.dirname(AUTO)                                      # .../capitulo_4
CAMPOS_ARCHIVO = ("archivo", "audio", "script")                       # campos de un paso que son archivos: su CONTENIDO entra en la huella del paso


def nombre_base(blend):
    return os.path.splitext(os.path.basename(blend))[0]


def ruta_config(blend):
    return os.path.join(AUTO, "cadenas", nombre_base(blend) + ".json")


def _expandir(x, var):
    if isinstance(x, str):
        for _ in range(4):                                            # las variables pueden usar otras variables
            for k, v in var.items(): x = x.replace("{" + k + "}", str(v))
        return x
    if isinstance(x, list): return [_expandir(v, var) for v in x]
    if isinstance(x, dict): return {k: _expandir(v, var) for k, v in x.items()}
    return x


def cargar_config(ruta):
    with open(ruta, encoding="utf-8") as f: cfg = json.load(f)
    var = dict(cfg.get("variables", {})); var.setdefault("CAPITULO", CAPITULO); var.setdefault("AUTO", AUTO)
    cfg = {k: (v if k == "variables" else _expandir(v, var)) for k, v in cfg.items()}
    for i, p in enumerate(cfg.get("pasos", [])): p.setdefault("id", "paso_%d" % i)
    cfg["_ruta"] = os.path.abspath(ruta)
    return cfg


def _md5_archivo(ruta):
    if not os.path.isfile(ruta): return "FALTA:" + ruta
    h = hashlib.md5()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def archivos_del_paso(p):
    out = [p[c] for c in CAMPOS_ARCHIVO if isinstance(p.get(c), str) and p[c]]
    return out + list(p.get("depende_de", []))


def huellas_pasos(cfg):
    """huella ENCADENADA de cada paso: su definicion + el contenido de sus archivos + la huella del paso anterior.
    Si cambia un paso, cambian el y todos los siguientes."""
    ant = "inicio"; out = []
    for p in cfg.get("pasos", []):
        h = hashlib.md5(ant.encode())
        h.update(json.dumps({k: v for k, v in p.items() if k != "checkpoint"}, sort_keys=True).encode())
        for a in archivos_del_paso(p): h.update(_md5_archivo(a).encode())
        ant = h.hexdigest(); out.append(ant)
    return out


def dir_estado(blend):
    d = os.path.join(AUTO, "estado", nombre_base(blend)); os.makedirs(d, exist_ok=True); return d


def leer_estado(blend):
    try:
        with open(os.path.join(dir_estado(blend), "estado.json"), encoding="utf-8") as f: return json.load(f)
    except Exception: return {}


def guardar_estado(blend, est):
    p = os.path.join(dir_estado(blend), "estado.json"); tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(est, f, indent=1, ensure_ascii=False)
    os.replace(tmp, p)


def firma_archivo(ruta):
    try: st = os.stat(ruta); return [int(st.st_mtime), st.st_size]
    except OSError: return None


def checkpoint_valido(est, hs, j):
    """el checkpoint guardado DESPUES del paso j sirve si ese paso (y los anteriores) no cambiaron y el archivo existe"""
    ps = est.get("pasos", [])
    if j < 0 or j >= len(ps) or j >= len(hs): return None
    e = ps[j]; cp = e.get("checkpoint")
    return cp if (e.get("huella") == hs[j] and cp and os.path.isfile(cp)) else None


def decidir(est, hs, escena_igual, desde="auto"):
    """-> (k, checkpoint): ejecutar los pasos k.. ; si checkpoint no es None, abrirlo antes (estado despues del paso k-1).
    k == len(hs) => la cadena ya esta al dia (no hay nada que reconstruir).
    `escena_igual`: la escena no se toco a mano desde la ultima reconstruccion (si se toco, todo desde el principio)."""
    n = len(hs)
    if desde == "completo" or not escena_igual: return 0, None
    if desde == "auto":
        ps = est.get("pasos", []); k = 0
        while k < n and k < len(ps) and ps[k].get("huella") == hs[k]: k += 1
    else:
        k = int(desde)
    if k >= n: return n, None
    for j in range(k - 1, -1, -1):                                    # el checkpoint mas cercano ANTES de k
        cp = checkpoint_valido(est, hs, j)
        if cp: return j + 1, cp
    return 0, None


def indice_paso(cfg, x):
    """'3' o 'jerry_rio' -> indice del paso"""
    if str(x).isdigit(): return int(x)
    for i, p in enumerate(cfg.get("pasos", [])):
        if p["id"] == x: return i
    raise ValueError("no hay paso %r en la cadena" % x)


def respaldar(blend, n_max=4):
    """copia el .blend a capitulo_4/respaldos_auto/<nombre>_<fecha>.blend y deja solo los `n_max` mas nuevos de ese archivo"""
    if not os.path.isfile(blend): return None
    d = os.path.join(os.path.dirname(os.path.abspath(blend)), "respaldos_auto"); os.makedirs(d, exist_ok=True)
    nb = nombre_base(blend); dst = os.path.join(d, "%s_%s.blend" % (nb, time.strftime("%Y%m%d_%H%M%S")))
    shutil.copy2(blend, dst)
    viejos = sorted(glob.glob(os.path.join(d, nb + "_????????_??????.blend")))
    for v in viejos[:-n_max] if n_max > 0 else []:
        try: os.remove(v)
        except OSError: pass
    return dst


def ruta_informe(blend):
    d = os.path.join(AUTO, "informes"); os.makedirs(d, exist_ok=True)
    return os.path.join(d, nombre_base(blend) + "_ultimo.txt")
