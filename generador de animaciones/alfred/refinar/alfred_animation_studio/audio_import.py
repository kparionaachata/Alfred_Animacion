# -*- coding: utf-8 -*-
"""
audio_import.py -- Alfred Animation Studio: AUDIO del guion (fase 2 del plan `docs/PLAN_PARTE3_AL_FLUJO.md`).

Que hace
  1. IMPORTAR un audio a un personaje: lo copia a `audios/<personaje>/` (sin pisar nada: mismo contenido = se reutiliza, otro contenido = nombre nuevo), saca el tiempo de cada palabra y la emocion
     (Whisper, `alfred_voz_sync/herramientas/analizar_audio.py`), la cara de la app `estudio_audio_expresion` (`importar_script_alfred.py` / `importar_script_jerry.py` con su `animacion_*.py`) y lo registra
     en la seccion `audio` del guion 2.0 con su INICIO (un frame o una ancla). El inicio es OBLIGATORIO: nunca se toma "el frame actual" por omision (era la causa de un error real: Voz Sync toma el
     frame actual al refrescar la lista y dejaba todas las voces en el mismo frame).
  2. SINCRONIZAR: crea las pistas de voz / emocion / cara de TODAS las voces del guion con Alfred Voz Sync (`sincronizar_clip`), cada una en el inicio que dice el guion (anclas ya resueltas), sin pasar por la
     lista del add-on ni por el frame actual.
  3. Se vuelve a sincronizar solo cuando hace falta: al CARGAR un guion (`post_cargar`) y al terminar CONCATENAR segmentos (`post_concatenar`), porque concatenar / previsualizar el recorrido borran todas las
     pistas NLA del personaje (tambien las de voz). Se desactiva con `bpy.context.scene["alfred_audio_auto"] = False`.

Las funciones de arriba (sin bpy) se prueban fuera de Blender (`refinar/pruebas/test_audio_import.py`); las de Blender importan bpy al usarse.
"""
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import types
import unicodedata
import wave

try:
    from . import guion_v2 as gv
except Exception:                                                                      # fuera del paquete (pruebas / exec por ruta)
    import importlib.util as _ilu
    _sp = _ilu.spec_from_file_location("guion_v2", os.path.join(os.path.dirname(os.path.abspath(__file__)), "guion_v2.py")); gv = _ilu.module_from_spec(_sp); _sp.loader.exec_module(gv)

RAIZ = os.environ.get("ALFRED_RAIZ", r"C:\Users\user\Desktop\Alfred_Animacion")
PYTHON_ESTUDIO = os.path.join(RAIZ, "voz_a_voz", "Applio", "env", "Scripts", "python.exe")                         # Python con librosa / torch / transformers (el de la app)
HERRAMIENTAS = os.path.join(RAIZ, "capitulos", "capitulo_4", "alfred_voz_sync", "herramientas")
EXT = (".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac", ".opus", ".wma")
PERSONAJES = {"ALFRED": {"carpeta": "alfred", "importador": "importar_script_alfred.py"}, "JERRY": {"carpeta": "jerry", "importador": "importar_script_jerry.py"}}
EMOCIONES = ("NEUTRO", "ENOJO", "ALEGRIA", "TRISTEZA", "SUENO", "MIEDO", "SORPRESA", "DUDA")
_A_APP = {"NEUTRO": "neutral", "ENOJO": "enojo", "ALEGRIA": "alegria", "TRISTEZA": "tristeza", "SUENO": "cansancio", "MIEDO": "miedo", "SORPRESA": "sorpresa", "DUDA": "duda"}


# ------------------------------------------------------------------------------------------------------------------------------------------- nombres y archivos
def slug(texto, max_palabras=6):
    s = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii").lower()
    p = [w for w in re.split(r"[^0-9a-z]+", s) if w][:max_palabras]
    return "_".join(p) or "audio"


def leer_transcript(script):
    """TRANSCRIPT del `animacion_*.py` de la app (se lee con ast, sin ejecutarlo; acepta UTF-8 o ANSI)."""
    with open(script, "rb") as f: raw = f.read()
    try: src = raw.decode("utf-8")
    except UnicodeDecodeError: src = raw.decode("cp1252", errors="replace")
    for n in ast.parse(src).body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and getattr(n.targets[0], "id", "") == "TRANSCRIPT": return str(ast.literal_eval(n.value))
    return None


def _sha1(ruta):
    h = hashlib.sha1()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def carpeta_personaje(personaje, carpeta_audios=None):
    return os.path.join(carpeta_audios or os.path.join(RAIZ, "audios"), PERSONAJES[personaje]["carpeta"])


def copiar_audio(origen, personaje, nombre, carpeta_audios=None):
    """copia `origen` a audios/<personaje>/<nombre><ext>. -> (ruta destino, creado). Mismo contenido: reutiliza; contenido distinto con el mismo nombre: <nombre>_2, _3..."""
    destino = carpeta_personaje(personaje, carpeta_audios); ext = os.path.splitext(origen)[1].lower()
    if ext not in EXT: raise ValueError("formato de audio no admitido: %s" % ext)
    if os.path.normcase(os.path.abspath(os.path.dirname(origen))) == os.path.normcase(os.path.abspath(destino)): return os.path.abspath(origen), False
    os.makedirs(destino, exist_ok=True); n = 1; sha = _sha1(origen)
    while True:
        cand = os.path.join(destino, nombre + ("" if n == 1 else "_%d" % n) + ext)
        if not os.path.exists(cand): shutil.copyfile(origen, cand); return cand, True
        if _sha1(cand) == sha: return cand, False
        n += 1


def rel_raiz(ruta, raiz=None):
    return os.path.relpath(ruta, raiz or RAIZ).replace("\\", "/")


def duracion_wav(ruta):
    try:
        with wave.open(ruta, "rb") as w: return w.getnframes() / float(w.getframerate())
    except Exception: return None


# ------------------------------------------------------------------------------------------------------------------------------------------- herramientas (subprocesos con el Python de la app)
def _ejecutar(cmd, timeout):
    try: r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as e: return False, "no se pudo ejecutar: %s" % e
    out = [l for l in r.stdout.splitlines() if l.strip()]
    if r.returncode: return False, "fallo: " + ((r.stderr.strip().splitlines() or out or ["sin salida"])[-1])
    return True, " | ".join(l for l in out if l.startswith(("emocion:", "cara:", "Alfred:", "Jerry:"))) or " | ".join(out[-2:])


def analizar(audio, texto=None, emocion=None, python=None, timeout=900):
    """tiempos por palabra + emocion (+ cara estimada) -> `<audio>.emocion.json` / `.cara.json` (analizar_audio.py)."""
    py = python or PYTHON_ESTUDIO; script = os.path.join(HERRAMIENTAS, "analizar_audio.py")
    if not (os.path.isfile(py) and os.path.isfile(script)): return False, "falta el Python de la herramienta o analizar_audio.py (%s)" % py
    cmd = [py, script, audio] + (["--emocion", _A_APP.get(emocion, emocion)] if emocion and emocion != "AUTO" else []) + (["--texto", texto] if texto else [])
    return _ejecutar(cmd, timeout)


def importar_script_app(audio, script, personaje="ALFRED", python=None, timeout=300):
    """cara y emocion de la app (`animacion_<personaje>.py`) -> `<audio>.cara.json` / `.emocion.json` (importar_script_*.py)."""
    py = python or PYTHON_ESTUDIO; imp = os.path.join(HERRAMIENTAS, PERSONAJES[personaje]["importador"])
    if not (os.path.isfile(py) and os.path.isfile(imp)): return False, "falta el Python de la herramienta o %s" % PERSONAJES[personaje]["importador"]
    return _ejecutar([py, imp, audio, script], timeout)


def _json(ruta):
    try:
        with open(ruta, encoding="utf-8") as f: return json.load(f)
    except Exception: return None


def entrada_guion(audio, inicio, personaje="ALFRED", id=None, raiz=None):
    """entrada de la seccion `audio` del guion para un audio ya importado (lee su `.cara.json` / `.emocion.json`)."""
    base = os.path.splitext(audio)[0]; cara = _json(base + ".cara.json"); emo = _json(base + ".emocion.json") or {}
    dur = (cara or {}).get("duracion_s") or emo.get("duracion_s") or duracion_wav(audio)
    e = {"personaje": personaje, "archivo": rel_raiz(audio, raiz), "inicio": inicio, "emocion": (cara or {}).get("emocion") or emo.get("emocion"), "texto": emo.get("texto")}
    if cara is not None: e["cara"] = rel_raiz(base + ".cara.json", raiz)
    if emo: e["emocion_json"] = rel_raiz(base + ".emocion.json", raiz)
    if dur: e["duracion_f"] = int(round(dur * 24))
    if id: e["id"] = id
    return e


def importar(origen, personaje="ALFRED", inicio=None, script_app=None, texto=None, emocion=None, nombre=None, carpeta_audios=None, reanalizar=False, python=None):
    """importa un audio: copia + analisis + cara. -> {"ok", "audio" (ruta), "entrada" (para el guion), "mensajes", "avisos"}. `inicio` es OBLIGATORIO (frame o ancla)."""
    if personaje not in PERSONAJES: raise ValueError("personaje desconocido: %r" % personaje)
    if inicio is None or not gv.es_tiempo(inicio): raise ValueError("`inicio` obligatorio: un frame o una ancla (no se usa el frame actual por omision)")
    if not os.path.isfile(origen): raise FileNotFoundError(origen)
    if script_app and not os.path.isfile(script_app): raise FileNotFoundError(script_app)
    msgs, avisos = [], []
    if not nombre:
        stem = os.path.splitext(os.path.basename(origen))[0]; tr = texto or (leer_transcript(script_app) if script_app else None)
        nombre = slug(tr) if (tr and stem.lower() in ("audio_original", "audio", "grabacion", "record")) else slug(stem, 12)
    audio, creado = copiar_audio(origen, personaje, slug(nombre, 12), carpeta_audios); msgs.append("%s: %s" % ("copiado" if creado else "ya estaba (mismo contenido)", rel_raiz(audio)))
    base = os.path.splitext(audio)[0]; txt = texto or (leer_transcript(script_app) if script_app else None)
    if reanalizar or not os.path.isfile(base + ".emocion.json"):
        ok, m = analizar(audio, txt, emocion if emocion != "AUTO" else None, python); (msgs if ok else avisos).append(("analisis: " if ok else "analisis NO hecho: ") + m)
    if script_app:
        ok, m = importar_script_app(audio, script_app, personaje, python); (msgs if ok else avisos).append(("cara de la app: " if ok else "cara de la app NO importada: ") + m)
    if not os.path.isfile(base + ".emocion.json"): avisos.append("sin `.emocion.json`: Voz Sync estimara la emocion por el audio")
    e = entrada_guion(audio, inicio, personaje)
    if script_app and e.get("emocion") == "NEUTRO" and txt: avisos.append("la emocion de la app quedo en NEUTRO (si el script trae una emocion que Voz Sync no conoce, agregarla a MAPA de importar_script_*.py)")
    return {"ok": os.path.isfile(audio), "audio": audio, "entrada": e, "mensajes": msgs, "avisos": avisos}


def agregar_a_guion(data, entrada):
    """agrega (o ACTUALIZA, si ya hay una entrada del mismo personaje y archivo) una voz en `data["audio"]`. -> (entrada, reemplazada)."""
    for x in data.setdefault("audio", []):
        if x.get("archivo") == entrada["archivo"] and x.get("personaje") == entrada["personaje"]:
            x.update({k: v for k, v in entrada.items() if k != "id"}); return x, True
    return gv.agregar(data, "audio", entrada, id="aud_" + os.path.splitext(os.path.basename(entrada["archivo"]))[0]), False


def clips_del_guion(data, raiz=None, personaje=None):
    """voces del guion con el inicio ya en frames absolutos (anclas resueltas), como los clips que espera Voz Sync (`nombre`, `ruta`, `inicio`). Ordenadas por inicio."""
    d = gv.desplegar(gv.migrar(data)); out = []
    for a in d.get("audio") or []:
        if personaje and a.get("personaje", "ALFRED") != personaje: continue
        out.append(types.SimpleNamespace(id=a.get("id"), personaje=a.get("personaje", "ALFRED"), nombre=os.path.basename(a["archivo"]), ruta=os.path.normpath(os.path.join(raiz or RAIZ, a["archivo"])), inicio=int(a["inicio"]),
                                         emocion=a.get("emocion"), texto=a.get("texto")))
    return sorted(out, key=lambda c: (c.inicio, c.id or ""))


# ------------------------------------------------------------------------------------------------------------------------------------------- Blender
def voz_sync():
    """modulo de Alfred Voz Sync (lo registra si Blender lo descargo); None si no existe."""
    m = sys.modules.get("alfred_voz_sync")
    if m is None:
        try:
            ruta = os.path.join(RAIZ, "capitulos", "capitulo_4")
            if ruta not in sys.path: sys.path.insert(0, ruta)
            import alfred_voz_sync as m
            m.register()
        except Exception as e:
            print("[audio_import] Voz Sync no disponible:", e); return None
    return m if hasattr(m, "sincronizar_clip") else None


def guion_de_escena(escena):
    """guion 2.0 recordado en la escena (cargado desde un .json o creado al importar audios); None si no hay."""
    ex = gv.recordado(escena); return gv.migrar(ex) if ex else None


def guardar_en_escena(escena, data):
    gv.recordar(data, escena)


def aplicar_guion(context, data=None, ids=None, raiz=None):
    """sincroniza con Voz Sync las voces del guion (todas, o solo las de `ids`), cada una en su inicio. -> {"ok", "n", "resultados": [(id, ok, mensaje)], "mensaje"}."""
    sc = context.scene; data = data or guion_de_escena(sc)
    if not data or not data.get("audio"): return {"ok": True, "n": 0, "resultados": [], "mensaje": "el guion no tiene audio"}
    vz = voz_sync()
    if vz is None: return {"ok": False, "n": 0, "resultados": [], "mensaje": "Alfred Voz Sync no esta instalado / activo"}
    p = sc.voz_sync; pers0 = p.personaje; frame0 = sc.frame_current; res = []
    try:
        for pers in PERSONAJES:
            clips = [c for c in clips_del_guion(data, raiz, pers) if ids is None or c.id in ids]
            if not clips: continue
            if p.personaje != pers: p.personaje = pers
            for c in clips:
                ok, msg = vz.sincronizar_clip(context, c); res.append((c.id, ok, msg))
    finally:
        if p.personaje != pers0: p.personaje = pers0
        sc.frame_set(frame0)
    bien = sum(1 for _, ok, _m in res if ok)
    return {"ok": bien == len(res), "n": bien, "resultados": res, "mensaje": "%d/%d voces sincronizadas" % (bien, len(res))}


def quitar_voz(context, clip):
    """quita de la escena las pistas / claves / audio del VSE de una voz (no toca archivos ni el guion)."""
    vz = voz_sync(); sc = context.scene
    if vz is None: return False
    p = sc.voz_sync; pers0 = p.personaje
    try:
        p.personaje = clip.personaje; rig = vz.buscar_rig(p); nombre = vz.nombre_pista(clip.personaje, clip)
        if rig is not None: vz.quitar_pista(p, rig, nombre)
        vz.quitar_claves_cara(p, ("Voz_" + vz.nombre_seguro(clip.nombre))[:56]); vz.quitar_audio_vse(sc, nombre)
    finally:
        if p.personaje != pers0: p.personaje = pers0
    return True


def _auto(context):
    return bool(context.scene.get("alfred_audio_auto", True))


def post_cargar(context):
    """al CARGAR un guion en el panel: sincroniza sus voces (si trae audio, Voz Sync existe y el automatico no esta apagado). Nunca lanza."""
    try:
        if _auto(context) and (guion_de_escena(context.scene) or {}).get("audio"):
            r = aplicar_guion(context); print("[audio_import] al cargar el guion:", r["mensaje"]); return r
    except Exception as e: print("[audio_import] post_cargar:", e)


def post_concatenar(context):
    """al terminar CONCATENAR: concatenar borra todas las pistas NLA del personaje (tambien las de voz): se vuelven a crear. Nunca lanza."""
    return post_cargar(context)
