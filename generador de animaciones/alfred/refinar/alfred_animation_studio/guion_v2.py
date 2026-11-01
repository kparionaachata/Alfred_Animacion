# -*- coding: utf-8 -*-
"""
guion_v2.py -- Alfred Animation Studio: GUION `version` 2.0 (superset del guion actual).

El guion es la receta editable de TODA la animacion de un personaje (flujo MANUAL, refinar/configuraciones/*.json). La version 2.0 NO cambia ni quita nada de lo
que ya guarda el add-on (`paso1_path`, `alfred_segs`, `organic`, `eye_sequence`, `object_imports`, `segments_throw`, ...): solo agrega secciones OPCIONALES. Un guion
viejo (1.x) se lee igual (`migrar` le agrega las secciones vacias) y un guion 2.0 cargado en el panel conserva sus secciones nuevas al volver a guardarse
(`recordar` / `fusionar_en`, enganchados en `config_ops`).

Este modulo es Python puro (sin bpy ni imports relativos): se prueba fuera de Blender (`refinar/pruebas/test_guion_v2.py`) y lo usan las herramientas nuevas
(audio, objetos, sonidos, camara) para leer su seccion ya con los tiempos resueltos (`desplegar`).

SECCIONES NUEVAS (todas opcionales)
  meta      {nombre, personaje, fps, frame_ini, frame_fin, fuente, estado, notas}          datos del guion
  anclas    {nombre: tiempo}                      puntos de referencia ("rompe_bloque": 1062); lo demas puede colgar de ellos
  capas     [{id, canal, puntos: [[tiempo, valor]...], interp}]   curvas de movimiento (inclinacion del torso, mirada, giros, "de pie")
  exactos   [{id, frames: [tiempo...], huesos: {hueso: [x, y, z] grados}, objetos: {nombre: {loc, rot, scale}}, ventana, tol, nota}]
                                                  valores dados por el usuario que ningun filtro puede tocar en esos frames
  objetos   [{id, nombre, blend, hueso, agarre, espalda, escala_mano, escala_espalda, eventos: [{tipo, t, hasta, ...}]}]
  mundo     [{id, accion, objeto, t, hasta, ...}]  cambios del escenario (ocultar un bloque, crear el pozo, item que sale del bloque)
  audio     [{id, personaje, archivo, inicio, emocion, texto, cara, emocion_json, duracion_f}]   voces
  sonidos   {modo: auto|manual|off, techo_voces, manuales: [{id, etiqueta, grupo, archivo, t, volumen, pan, canal}]}
  camara    [{id, objeto, desde, hasta, destino: [x, y, z], interp}]       movimientos de camara / foco

TIEMPO: un frame absoluto (int / float), o un frame relativo a una ancla: {"ancla": "rompe_bloque", "delta": 8} o el atajo "rompe_bloque+8" / "rompe_bloque-3" / "rompe_bloque".
Las anclas pueden colgar de otras anclas (sin ciclos). Asi, insertar frames en la linea de tiempo solo obliga a mover las anclas absolutas (`mover_tiempo`).
"""
import copy
import json
import os
import re
import tempfile
import time

VERSION = "2.0"
SECCIONES = ("meta", "anclas", "capas", "exactos", "objetos", "mundo", "audio", "sonidos", "camara", "movimiento")


def _vacio():
    return {"meta": {}, "anclas": {}, "capas": [], "exactos": [], "objetos": [], "mundo": [], "audio": [],
            "sonidos": {"modo": "auto", "techo_voces": True, "manuales": []}, "camara": [], "movimiento": {}}


HUESOS = ("Hips_alfred", "Spine_alfred", "Spine1_alfred", "Spine2_alfred", "Neck_alfred", "face_alfred", "RightUpArm_alfred", "Rightelbow_alfred", "LeftUpArm_alfred",
          "Leftelbow_alfred", "RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred")
CANALES_CAPA = {"inclinacion": "grados hacia delante repartidos en Spine / Spine1 / Spine2 (0.32 / 0.34 / 0.34)", "cuello_x": "Neck X (grados)", "cuello_y": "Neck Y (grados; + = izquierda)",
                "giro_yaw": "giro del root sobre si mismo (grados, acumulado)", "de_pie": "0 = como estaba, 1 = de pie (peso)", "root_dx": "desplazamiento X del root (m)",
                "root_dy": "desplazamiento Y del root (m)", "root_dz": "desplazamiento Z del root (m)"}
EVENTOS_OBJETO = ("aparece", "coloca", "toma", "guarda", "mantiene", "lanza", "recoge", "rebota", "cae_sobre", "absorbe", "oculta", "muestra", "en_mano", "asienta", "encoge", "bezier")
ACCIONES_MUNDO = ("ocultar", "mostrar", "crear_pozo", "aparecer_item", "mover", "luz")
MODOS_SONIDO = ("auto", "manual", "off")
TIPOS_TRAMO = ("sentado_cansado", "cuerpo")
INTERP = ("linear", "smooth", "elastic", "ease_in", "ease_out", "constant")


# ------------------------------------------------------------------------------------------------------------------------------------------- tiempo
_RE_ANCLA = re.compile(r"^\s*([A-Za-z_][\w\-\.]*?)\s*(?:([+-])\s*(\d+(?:\.\d+)?))?\s*$")


def _es_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _partes(t):
    """tiempo -> (ancla o None, delta o valor absoluto). Lanza ValueError si no es un tiempo valido."""
    if _es_num(t): return None, float(t)
    if isinstance(t, dict) and "ancla" in t: return str(t["ancla"]), float(t.get("delta", 0))
    if isinstance(t, str):
        m = _RE_ANCLA.match(t)
        if m: return m.group(1), (0.0 if m.group(2) is None else (1 if m.group(2) == "+" else -1) * float(m.group(3)))
    raise ValueError("tiempo no valido: %r" % (t,))


def es_tiempo(t):
    try: _partes(t); return True
    except ValueError: return False


def resolver_anclas(data):
    """{ancla: frame (int)}. Las anclas pueden colgar de otras; ValueError si hay un ciclo o una ancla que no existe."""
    crudo = (data.get("anclas") or {}); res = {}; en_curso = []

    def res_(n):
        if n in res: return res[n]
        if n not in crudo: raise ValueError("ancla inexistente: %r" % n)
        if n in en_curso: raise ValueError("ciclo de anclas: " + " -> ".join(en_curso + [n]))
        en_curso.append(n); a, v = _partes(crudo[n]); val = v if a is None else res_(a) + v; en_curso.pop(); res[n] = val; return val
    for n in crudo: res_(n)
    return {n: int(round(v)) for n, v in res.items()}


def frame_de(t, anclas):
    """tiempo -> frame absoluto (int). `anclas` = resultado de `resolver_anclas`."""
    a, v = _partes(t)
    if a is None: return int(round(v))
    if a not in anclas: raise ValueError("ancla inexistente: %r" % a)
    return int(round(anclas[a] + v))


# Donde hay tiempos dentro de cada seccion: (seccion, ruta). Se usa para validar, resolver (`desplegar`) y desplazar (`mover_tiempo`).
def _tiempos(data):
    """-> lista de (contenedor, clave) de cada campo de tiempo del guion v2 (mas los frames absolutos de `alfred_segs`)."""
    out = []
    an = data.get("anclas")
    if isinstance(an, dict): out += [(an, k) for k in an]
    for c in data.get("capas") or []:
        for p in c.get("puntos") or []:
            if isinstance(p, list) and p: out.append((p, 0))
    for e in data.get("exactos") or []:
        fr = e.get("frames")
        if isinstance(fr, list): out += [(fr, i) for i in range(len(fr))]
    for o in data.get("objetos") or []:
        for ev in o.get("eventos") or []:
            out += [(ev, k) for k in ("t", "hasta") if k in ev]
    for m in data.get("mundo") or []:
        out += [(m, k) for k in ("t", "hasta", "absorbe_en") if k in m]
        out += [(c, 0) for c in m.get("claves") or [] if isinstance(c, list) and c]
    for a in data.get("audio") or []:
        if "inicio" in a: out.append((a, "inicio"))
    s = data.get("sonidos")
    if isinstance(s, dict):
        for m in s.get("manuales") or []:
            if "t" in m: out.append((m, "t"))
    for c in data.get("camara") or []:
        out += [(c, k) for k in ("desde", "hasta") if k in c]
        out += [(row, 0) for row in c.get("claves") or [] if isinstance(row, list) and row]
    mv = data.get("movimiento")
    if isinstance(mv, dict):
        for t in mv.get("tramos") or []:
            out += [(t, k) for k in ("inicio", "fin") if k in t]

            def rec(x):                                                                  # los parametros cuyo nombre empieza por `t_` son tiempos (frames o anclas), a cualquier profundidad
                if isinstance(x, dict):
                    for k in list(x):
                        if k.startswith("t_") and es_tiempo(x[k]): out.append((x, k))
                        elif k.startswith("tt_") and isinstance(x[k], list): out.extend((row, 0) for row in x[k] if isinstance(row, list) and row and es_tiempo(row[0]))        # tabla de filas [tiempo, ...]
                        else: rec(x[k])
                elif isinstance(x, list):
                    for y in x: rec(y)
            rec(t.get("params"))
    return out


def desplegar(data):
    """copia del guion con TODOS los tiempos como frames absolutos (int) y las anclas resueltas: es lo que leen las herramientas que ejecutan el guion."""
    d = copy.deepcopy(data); an = resolver_anclas(d)
    for cont, k in _tiempos(d): cont[k] = frame_de(cont[k], an)
    d["anclas"] = an
    return d


def mover_tiempo(data, desde, delta):
    """inserta (`delta` > 0) o quita (`delta` < 0) frames a partir de `desde`: los tiempos ABSOLUTOS >= desde se desplazan (los relativos a una ancla viajan con ella) y tambien
    `frame_start` / `frame_end` de `alfred_segs`. Si se quitan frames, lo que caia dentro del tramo quitado se queda en `desde`. Devuelve una copia."""
    d = copy.deepcopy(data)

    def mv(v):
        if v < desde: return v
        return max(desde, v + delta) if delta < 0 else v + delta
    for cont, k in _tiempos(d):
        t = cont[k]
        if _es_num(t): cont[k] = type(t)(mv(t)) if isinstance(t, int) else mv(t)
    for s in d.get("alfred_segs") or []:
        for k in ("frame_start", "frame_end", "frame_start_planned", "frame_end_planned"):
            if _es_num(s.get(k)): s[k] = type(s[k])(mv(s[k]))
    m = d.get("meta")
    if isinstance(m, dict) and _es_num(m.get("frame_fin")): m["frame_fin"] = type(m["frame_fin"])(mv(m["frame_fin"]))
    return d


# ------------------------------------------------------------------------------------------------------------------------------------------- migrar / cargar / guardar
def migrar(data):
    """guion (cualquier version) -> guion 2.0: agrega las secciones que falten (vacias) y marca `version`. Idempotente; no quita ni cambia ninguna clave existente. Copia."""
    d = copy.deepcopy(data)
    if d.get("version") != VERSION:
        d.setdefault("migrado_de", d.get("version", "?")); d["version"] = VERSION
    for k, v in _vacio().items():
        if k not in d: d[k] = v
    return d


def nuevo(nombre, personaje="ALFRED", fps=24, frame_ini=1, frame_fin=1, descripcion=""):
    d = migrar({"description": descripcion, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")})
    d["meta"] = {"nombre": nombre, "personaje": personaje, "fps": fps, "frame_ini": frame_ini, "frame_fin": frame_fin, "estado": "sin aprobar"}
    return d


def cargar(ruta):
    with open(ruta, "r", encoding="utf-8") as f: return migrar(json.load(f))


def guardar(data, ruta, sobrescribir=False, respaldo=True):
    """escribe el guion (escritura atomica). NUNCA pisa un archivo existente salvo `sobrescribir=True` (y entonces deja `<archivo>.bak`)."""
    if os.path.exists(ruta):
        if not sobrescribir: raise FileExistsError("ya existe (usar sobrescribir=True): " + ruta)
        if respaldo:
            with open(ruta, "rb") as a, open(ruta + ".bak", "wb") as b: b.write(a.read())
    carpeta = os.path.dirname(os.path.abspath(ruta)); os.makedirs(carpeta, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=carpeta, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, ruta)
    finally:
        if os.path.exists(tmp): os.remove(tmp)
    return ruta


def agregar(data, seccion, entrada, id=None):
    """agrega `entrada` a una seccion de lista (capas, exactos, objetos, mundo, audio, camara o sonidos.manuales) con un `id` unico. Devuelve la entrada."""
    if seccion == "sonidos": lista = data.setdefault("sonidos", _vacio()["sonidos"]).setdefault("manuales", []); pref = "snd"
    elif seccion in ("capas", "exactos", "objetos", "mundo", "audio", "camara"): lista = data.setdefault(seccion, []); pref = seccion[:3]
    else: raise ValueError("seccion de lista desconocida: %r" % seccion)
    usados = {x.get("id") for x in lista}; n = len(lista) + 1; nid = id or "%s_%02d" % (pref, n)
    while nid in usados: n += 1; nid = "%s_%02d" % (pref, n)
    entrada = dict(entrada); entrada["id"] = nid; lista.append(entrada); return entrada


def anclar(data, max_dist=40, secciones=("sonidos",)):
    """reescribe los tiempos ABSOLUTOS de `sonidos.manuales` (y de `camara` movimientos si se pide) como "ancla+/-N" respecto a la ancla mas cercana (si esta a <= max_dist frames): asi, al mover una ancla (o insertar
    tiempo con `mover_tiempo`) los sonidos viajan con su escena. Devuelve (copia, cuantos)."""
    d = copy.deepcopy(data); an = resolver_anclas(d); n = 0
    if not an: return d, 0

    def rel(t):
        if not _es_num(t): return t
        k, v = min(((abs(t - v), k) for k, v in an.items()), key=lambda x: (x[0], x[1])); a = an[v]
        return t if k > max_dist else (v if round(t) == a else "%s%+d" % (v, int(round(t)) - a))
    if "sonidos" in secciones:
        for m in (d.get("sonidos") or {}).get("manuales") or []:
            if "t" in m and _es_num(m["t"]): m["t"] = rel(m["t"]); n += 1
    if "camara" in secciones:
        for c in d.get("camara") or []:
            for k in ("desde", "hasta"):
                if k in c and _es_num(c[k]): c[k] = rel(c[k]); n += 1
    return d, n


# ------------------------------------------------------------------------------------------------------------------------------------------- validar
def validar(data, raiz=None):
    """-> {"errores": [...], "avisos": [...]}. `raiz` = carpeta del proyecto (para comprobar que existen los audios, .cara.json y sonidos)."""
    E, A = [], []
    if data.get("version") not in ("2.0",) and not str(data.get("version", "")).startswith("1."): A.append("version desconocida: %r" % data.get("version"))
    an = None
    try: an = resolver_anclas(data)
    except ValueError as e: E.append("anclas: %s" % e)
    meta = data.get("meta") or {}; ini, fin = meta.get("frame_ini"), meta.get("frame_fin")

    def fr(t, donde):
        if an is None: return None
        try: v = frame_de(t, an)
        except ValueError as e: E.append("%s: %s" % (donde, e)); return None
        if _es_num(ini) and _es_num(fin) and not (ini <= v <= fin): A.append("%s: frame %d fuera del rango del guion (%s-%s)" % (donde, v, ini, fin))
        return v

    def ids(lista, nombre):
        vistos = set()
        for x in lista:
            i = x.get("id")
            if i is None: A.append("%s: entrada sin id" % nombre)
            elif i in vistos: E.append("%s: id repetido %r" % (nombre, i))
            vistos.add(i)
    for k in (data.get("anclas") or {}):
        if not es_tiempo(data["anclas"][k]): E.append("anclas.%s: tiempo no valido %r" % (k, data["anclas"][k]))
    ids(data.get("capas") or [], "capas")
    for c in data.get("capas") or []:
        w = "capas[%s]" % c.get("id")
        if c.get("canal") not in CANALES_CAPA: A.append("%s: canal desconocido %r (conocidos: %s)" % (w, c.get("canal"), ", ".join(CANALES_CAPA)))
        if c.get("interp", "smooth") not in INTERP: A.append("%s: interp desconocida %r" % (w, c.get("interp")))
        pts = c.get("puntos") or []
        if len(pts) < 2: E.append("%s: hacen falta al menos 2 puntos" % w)
        fs = [fr(p[0], w) for p in pts if isinstance(p, list) and len(p) == 2]
        if len(fs) != len(pts): E.append("%s: cada punto debe ser [tiempo, valor]" % w)
        elif None not in fs and fs != sorted(fs): E.append("%s: los puntos no estan en orden de tiempo" % w)
    ids(data.get("exactos") or [], "exactos")
    for e in data.get("exactos") or []:
        w = "exactos[%s]" % e.get("id")
        if not e.get("frames"): E.append("%s: sin frames" % w)
        for t in e.get("frames") or []: fr(t, w)
        for h, v in (e.get("huesos") or {}).items():
            if h not in HUESOS: A.append("%s: hueso desconocido %r" % (w, h))
            if not (isinstance(v, list) and len(v) == 3 and all(_es_num(x) for x in v)): E.append("%s: %s debe ser [x, y, z]" % (w, h))
        if not (e.get("huesos") or e.get("objetos")): A.append("%s: no fija ni huesos ni objetos" % w)
    ids(data.get("objetos") or [], "objetos")
    for o in data.get("objetos") or []:
        w = "objetos[%s]" % o.get("id")
        if not o.get("nombre"): E.append("%s: falta `nombre`" % w)
        prev = None
        for ev in o.get("eventos") or []:
            if ev.get("tipo") not in EVENTOS_OBJETO: E.append("%s: evento desconocido %r" % (w, ev.get("tipo"))); continue
            if "t" not in ev: E.append("%s: evento %s sin `t`" % (w, ev["tipo"])); continue
            t = fr(ev["t"], w + "." + ev["tipo"]); h = fr(ev["hasta"], w + "." + ev["tipo"]) if "hasta" in ev else None
            tp = ev["tipo"]; ag = o.get("agarres") or {}
            if tp in ("toma", "mantiene") and ev.get("agarre") not in ag: E.append("%s: %s usa el agarre %r que no esta en `agarres` (%s)" % (w, tp, ev.get("agarre"), ", ".join(ag) or "ninguno"))
            if tp == "guarda" and not o.get("espalda"): E.append("%s: guarda sin `espalda` (captura el sitio de la espalda)" % w)
            if tp in ("toma", "guarda") and "hasta" not in ev: E.append("%s: %s necesita `hasta`" % (w, tp))
            if tp in ("lanza", "rebota") and not (ev.get("a") and ev.get("vuelo")): E.append("%s: %s necesita `a` y `vuelo`" % (w, tp))
            if tp == "cae_sobre" and not (ev.get("vuelo") and (ev.get("sobre") or {}).get("reposo") and (ev.get("sobre") or {}).get("hueso")): E.append("%s: cae_sobre necesita `vuelo` y `sobre` {hueso, reposo}" % w)
            if tp == "absorbe" and not (ev.get("hasta") is not None and ev.get("hacia")): E.append("%s: absorbe necesita `hasta` y `hacia`" % w)
            if tp == "asienta" and not ev.get("en"): E.append("%s: asienta necesita `en` {loc, rot|quat, escala}" % w)
            if tp == "en_mano" and ev.get("agarre") not in ag: E.append("%s: en_mano usa el agarre %r que no esta en `agarres`" % (w, ev.get("agarre")))
            if tp == "bezier" and not (len(ev.get("puntos") or []) == 3 and h is not None): E.append("%s: bezier necesita `puntos` [P0, PC, H] y `hasta`" % w)
            if tp == "coloca" and not ev.get("en"): E.append("%s: coloca necesita `en` {loc, rot|quat, escala}" % w)
            if tp == "aparece" and not ev.get("en"): A.append("%s: aparece sin `en` (se usara el estado inicial)" % w)
            if t is not None and h is not None and h < t: E.append("%s: %s termina (%d) antes de empezar (%d)" % (w, ev["tipo"], h, t))
            if t is not None and prev is not None and t < prev: A.append("%s: eventos fuera de orden (%s en f%d)" % (w, ev["tipo"], t))
            prev = t if t is not None else prev
        if ev_tipos_con_hueso(o) and not o.get("hueso"): A.append("%s: hay eventos que usan la mano pero falta `hueso`" % w)
    ids(data.get("mundo") or [], "mundo")
    for m in data.get("mundo") or []:
        w = "mundo[%s]" % m.get("id")
        if m.get("accion") not in ACCIONES_MUNDO: E.append("%s: accion desconocida %r" % (w, m.get("accion")))
        if "t" not in m: E.append("%s: sin `t`" % w)
        else: fr(m["t"], w)
        if "absorbe_en" in m: fr(m["absorbe_en"], w + ".absorbe_en")
        if m.get("accion") == "aparecer_item" and not (m.get("objeto") and m.get("en") and "absorbe_en" in m and m.get("absorbido_por")): E.append("%s: aparecer_item necesita `objeto`, `en`, `absorbe_en` y `absorbido_por`" % w)
        if m.get("accion") == "luz" and not (m.get("objeto") and m.get("claves") and "energia" in m): E.append("%s: luz necesita `objeto`, `energia` y `claves` [[t, factor]]" % w)
        if m.get("accion") == "crear_pozo" and not m.get("tapa"): E.append("%s: crear_pozo necesita `tapa`" % w)
    ids(data.get("audio") or [], "audio")
    prev = []
    for a in data.get("audio") or []:
        w = "audio[%s]" % a.get("id")
        if not a.get("archivo"): E.append("%s: falta `archivo`" % w)
        elif raiz and not os.path.isfile(os.path.join(raiz, a["archivo"])): E.append("%s: no existe %s" % (w, a["archivo"]))
        if raiz and a.get("cara") and not os.path.isfile(os.path.join(raiz, a["cara"])): E.append("%s: no existe %s" % (w, a["cara"]))
        if "inicio" not in a: E.append("%s: falta `inicio`" % w); continue
        t = fr(a["inicio"], w); d = a.get("duracion_f")
        if t is not None and _es_num(d):
            for (p_id, p_pers, p0, p1) in prev:
                if p_pers == a.get("personaje") and t < p1 and p0 < t + d: A.append("%s se solapa con %s (mismo personaje)" % (w, p_id))
            prev.append((a.get("id"), a.get("personaje"), t, t + d))
    s = data.get("sonidos") or {}
    if s.get("modo", "auto") not in MODOS_SONIDO: E.append("sonidos: modo desconocido %r" % s.get("modo"))
    ids(s.get("manuales") or [], "sonidos.manuales")
    for m in s.get("manuales") or []:
        w = "sonidos.manuales[%s]" % m.get("id")
        if not (m.get("archivo") or m.get("evento")): E.append("%s: falta `archivo` o `evento`" % w)
        if "t" not in m: E.append("%s: sin `t`" % w)
        else: fr(m["t"], w)
        if raiz and m.get("archivo") and not os.path.isfile(os.path.join(raiz, "sonidos", "sounds", m["archivo"])): A.append("%s: no existe sonidos/sounds/%s" % (w, m["archivo"]))
    mv = data.get("movimiento") or {}; trs = mv.get("tramos") or []
    ids(trs, "movimiento.tramos"); prev_f = None
    for t in sorted([x for x in trs if es_tiempo(x.get("inicio")) and es_tiempo(x.get("fin"))], key=lambda x: fr(x["inicio"], "tramo") or 0):
        w = "movimiento.tramos[%s]" % t.get("id"); a_, b_ = fr(t["inicio"], w), fr(t["fin"], w)
        if a_ is not None and b_ is not None:
            if b_ < a_: E.append("%s: `fin` (%d) antes de `inicio` (%d)" % (w, b_, a_))
            if prev_f is not None and a_ <= prev_f: E.append("%s se solapa con el tramo anterior (hasta f%d)" % (w, prev_f))
            prev_f = b_
    for t in trs:
        w = "movimiento.tramos[%s]" % t.get("id")
        if t.get("tipo") not in TIPOS_TRAMO: E.append("%s: tipo desconocido %r (conocidos: %s)" % (w, t.get("tipo"), ", ".join(TIPOS_TRAMO)))
        if t.get("usa") and t["usa"] not in {x.get("id") for x in trs}: E.append("%s: `usa` apunta a un tramo que no existe (%r)" % (w, t["usa"]))
        if not t.get("usa") and not t.get("params"): E.append("%s: sin `params` ni `usa`" % w)
        if "inicio" not in t or "fin" not in t: E.append("%s: faltan `inicio` / `fin`" % w)
    if trs and raiz and mv.get("referencia_numerica") and not os.path.isfile(os.path.join(raiz, "generador de animaciones", "alfred", "refinar", mv["referencia_numerica"])): E.append("movimiento: no existe la referencia numerica %s" % mv["referencia_numerica"])
    if trs and not mv.get("organico"): A.append("movimiento: sin `organico` (los filtros del estudio): el motor no podra generar")
    ids(data.get("camara") or [], "camara")
    for c in data.get("camara") or []:
        w = "camara[%s]" % c.get("id")
        if not c.get("objeto"): E.append("%s: falta `objeto`" % w)
        if c.get("tipo") == "claves":
            n = {"location": 3}.get(c.get("canal"), 1); rows = c.get("claves") or []
            if not c.get("canal"): E.append("%s: falta `canal` (location, lens, dof.aperture_fstop...)" % w)
            if not rows: E.append("%s: sin `claves`" % w)
            if any(not (isinstance(x, list) and len(x) == n + 1 and all(_es_num(v) for v in x[1:])) for x in rows): E.append("%s: cada clave debe ser [tiempo%s]" % (w, ", x, y, z" if n == 3 else ", valor"))
            else:
                fs = [fr(x[0], w) for x in rows]
                if None not in fs and fs != sorted(fs): E.append("%s: las claves no estan en orden de tiempo" % w)
            continue
        d = c.get("destino")
        if not (isinstance(d, list) and len(d) == 3 and all(_es_num(x) for x in d)): E.append("%s: `destino` debe ser [x, y, z]" % w)
        a, b = (fr(c[k], w) if k in c else None for k in ("desde", "hasta"))
        if "desde" not in c or "hasta" not in c: E.append("%s: faltan `desde` / `hasta`" % w)
        elif a is not None and b is not None and b < a: E.append("%s: `hasta` (%d) antes de `desde` (%d)" % (w, b, a))
        if c.get("interp", "smooth") not in INTERP: A.append("%s: interp desconocida %r" % (w, c.get("interp")))
    return {"errores": E, "avisos": A}


def ev_tipos_con_hueso(o):
    return any(ev.get("tipo") in ("toma", "guarda", "mantiene", "lanza", "recoge") for ev in (o.get("eventos") or []))


# ------------------------------------------------------------------------------------------------------------------------------------------- enganche con config_ops (guardar / cargar desde los paneles)
_EXTRAS = {"datos": {}}
_CLAVE_ESCENA = "alfred_guion_v2"


def extras_de(data):
    """solo las secciones v2 que NO estan vacias (lo que el panel no sabe guardar)."""
    v = _vacio(); return {k: copy.deepcopy(data[k]) for k in SECCIONES if k in data and data[k] != v[k]}


def recordar(data, escena=None):
    """al CARGAR un guion en el panel: recuerda sus secciones v2 para que no se pierdan al guardar de nuevo. Un guion 1.x vacia el recuerdo."""
    ex = extras_de(data); _EXTRAS["datos"] = ex
    if escena is not None:
        try: escena[_CLAVE_ESCENA] = json.dumps(ex, ensure_ascii=False)
        except Exception: pass
    return ex


def recordado(escena=None):
    if escena is not None:
        try:
            s = escena.get(_CLAVE_ESCENA)
            if s: return json.loads(s)
        except Exception: pass
    return _EXTRAS["datos"]


def fusionar_en(cfg, extras):
    """al GUARDAR desde el panel: agrega las secciones v2 recordadas al diccionario que escribe el add-on (y marca la version 2.0 si habia alguna)."""
    if extras:
        cfg.update(copy.deepcopy(extras)); cfg["version"] = VERSION
    return cfg


# ------------------------------------------------------------------------------------------------------------------------------------------- linea de comandos
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3 or sys.argv[1] not in ("validar", "migrar", "desplegar"):
        sys.exit("uso: python guion_v2.py validar <guion.json> [raiz_proyecto] | migrar <entrada.json> <salida.json> | desplegar <guion.json> <salida.json>")
    g = cargar(sys.argv[2])
    if sys.argv[1] == "validar":
        r = validar(g, sys.argv[3] if len(sys.argv) > 3 else None)
        for e in r["errores"]: print("ERROR ", e)
        for a in r["avisos"]: print("aviso ", a)
        print("%d error(es), %d aviso(s)" % (len(r["errores"]), len(r["avisos"]))); sys.exit(1 if r["errores"] else 0)
    out = sys.argv[4] if len(sys.argv) > 4 else sys.argv[3]
    guardar(migrar(g) if sys.argv[1] == "migrar" else desplegar(g), out); print("escrito", out)
