# -*- coding: utf-8 -*-
"""
voz_rapida.py -- Jerry Animation Studio: VOZ RAPIDA de Jerry (audio + animacion de cara de la app) en UNA llamada, sin Whisper ni Voz Sync.

    aplicar(context, audio, inicio, script=None, tag=None, modo="normal", vol=None, efecto="ninguno")

  1. copia el audio a `audios/jerry/<tag>.wav` (si no es .wav lo convierte con ffmpeg) y, si hay, el `animacion_jerry (N).py` a `<tag>.cara_original.py`;
     `efecto` = "boca_ocupada" (suave, voz ahogada) | "boca_ocupada_fuerte" | "ninguno" | "sin_efecto" (voz limpia aun en modo boca_ocupada / boca_cerrada_cara): filtro ffmpeg sobre el audio;
  2. VOLUMEN automatico (si `vol` es None): sube el pico a -1 dBFS (maximo x3);
  3. FOTO de las claves de la cara de Jerry en el rango (mandibula, hocico, cabeza, cejas, ojos y pupilas): si la voz `tag` ya se aplico antes, primero se
     RESTAURA esa foto (asi se puede repetir sin duplicar el efecto, que los scripts de voz SUMAN);
  4. segun `modo`:
       "normal"       -> `docs/voz_jerry_despierta.py` (cara de la app: mandibula por silaba, hocico, cabeza, cejas, ojos/pupilas; necesita `script`)
       "solo_audio"   -> `docs/voz_jerry_solo_audio.py` (mandibula con la envolvente del audio; sin script)
       "boca_ocupada" -> sin abrir la boca: tiembla la mandibula +-4 grados y cabecea `spine_2` con la envolvente (para cuando muerde algo);
       "boca_cerrada_cara" -> cejas, ojos y cabeza de la app, pero la mandibula y el hocico NO se abren (solo tiemblan, como "boca_ocupada");
  5. tira `VozJerry_<tag>_*` con `duck_todos` y `ducking_voces.py`.
Registro en `scene["jerry_voces_rapidas"]` (tag -> inicio, modo, archivo). `quitar(context, tag)` restaura la foto y borra sus tiras.
"""
import bpy, os, json, math, shutil, subprocess, wave

RAIZ = r"C:\Users\user\Desktop\Alfred_Animacion"
AUD = os.path.join(RAIZ, "audios", "jerry")
DOCS = os.path.join(RAIZ, "generador de animaciones", "jerry", "refinar", "docs")
DUCK = os.path.join(RAIZ, "generador de animaciones", "alfred", "refinar", "docs", "acciones", "ducking_voces.py")
EFECTOS = {"boca_ocupada_claro": "highpass=f=120,equalizer=f=450:t=q:w=1.4:g=1,equalizer=f=2800:t=q:w=1.2:g=3,acompressor=threshold=-32dB:ratio=3:attack=3:release=80,volume=3dB,alimiter=limit=0.9",   # casi sin filtrar: las palabras se entienden (sube lo debil)
           "boca_ocupada": "highpass=f=150,lowpass=f=3800,equalizer=f=450:t=q:w=1.4:g=1,equalizer=f=3200:t=q:w=1:g=-3,acompressor=threshold=-24dB:ratio=2:attack=5:release=60,volume=4dB,alimiter=limit=0.9",
           "boca_ocupada_fuerte": "highpass=f=170,lowpass=f=2400,equalizer=f=450:t=q:w=1.4:g=2,equalizer=f=3200:t=q:w=1:g=-6,acompressor=threshold=-24dB:ratio=2.5:attack=5:release=60,volume=5dB,alimiter=limit=0.9"}
HUESOS_CARA = ("jaw_bot", "jaw_top", "scull", "scull_1", "sejas_1_jerry", "sejas_2_jerry", "spine_2")
OJOS = ("ojo_izquierdo_jerry", "ojo_derecho_jerry", "pupila_izquierda_jerry", "pupila_derecha_jerry")


def rig():
    return next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "scull_1" in o.pose.bones and "jaw_bot" in o.pose.bones)


def _slug(t):
    import re
    return re.sub(r"[^a-z0-9_]+", "_", t.lower()).strip("_")[:40] or "voz"


def _ffmpeg(args):
    try: subprocess.run(["ffmpeg", "-hide_banner", "-y"] + args, check=True, capture_output=True, timeout=120); return True
    except Exception as e: print("[voz_rapida] ffmpeg:", e); return False


def preparar_audio(audio, tag, efecto="ninguno"):
    """-> ruta del .wav final en audios/jerry (el original se guarda como <tag>_original.wav)"""
    os.makedirs(AUD, exist_ok=True); dest = os.path.join(AUD, tag + ".wav"); orig = os.path.join(AUD, tag + "_original.wav")
    if audio.lower().endswith(".wav"): shutil.copyfile(audio, orig)
    elif not _ffmpeg(["-i", audio, "-ac", "1", "-ar", "44100", orig]): raise RuntimeError("no se pudo convertir %s a .wav (falta ffmpeg)" % audio)
    if efecto in EFECTOS:
        if not _ffmpeg(["-i", orig, "-af", EFECTOS[efecto], "-ar", "44100", "-ac", "1", dest]): shutil.copyfile(orig, dest)
    else: shutil.copyfile(orig, dest)
    return dest


def envolvente(wav):
    import numpy as np
    w = wave.open(wav); sr = w.getframerate(); nc = w.getnchannels(); sw = w.getsampwidth()
    raw = w.readframes(w.getnframes()); dt = {1: np.int8, 2: np.int16, 4: np.int32}[sw]
    d = np.frombuffer(raw, dtype=dt).astype(float).reshape(-1, nc).mean(1); fl = sr / 24.0
    rms = np.array([np.sqrt((d[int(i * fl):int((i + 1) * fl)] ** 2).mean()) for i in range(max(1, int(len(d) / fl)))])
    pico = float(np.abs(d).max()) / float(2 ** (8 * sw - 1))
    return (rms / max(rms.max(), 1e-9)).tolist(), pico


def vol_auto(pico):
    if pico <= 0: return 1.0
    return max(0.5, min(3.0, 10 ** ((-1.0 - 20 * math.log10(pico)) / 20.0)))


# ---------------- foto / restauracion de las claves de la cara ----------------
def _owners():
    A = rig(); out = [("rig", A)]
    for n in OJOS:
        o = bpy.data.objects.get(n)
        if o: out.append(("obj:" + n, o));
        if o and o.data.shape_keys: out.append(("sk:" + n, o.data.shape_keys))
    return out


def _fcurvas(idb, filtro=None):
    ad = getattr(idb, "animation_data", None)
    if not ad or not ad.action: return []
    out = [c for l in ad.action.layers for s in l.strips for b in s.channelbags for c in b.fcurves]
    return [c for c in out if filtro is None or filtro(c.data_path)]


def _filtro(clave):
    if clave == "rig": return lambda dp: any(('"%s"' % h) in dp for h in HUESOS_CARA)
    return None


def foto(a, b):
    """claves de la cara en [a, b] -> dict serializable"""
    d = {}
    for clave, idb in _owners():
        for c in _fcurvas(idb, _filtro(clave)):
            d["%s|%s|%d" % (clave, c.data_path, c.array_index)] = [[kp.co.x, kp.co.y] for kp in c.keyframe_points if a <= kp.co.x <= b]
    return {"a": a, "b": b, "curvas": d}


def restaurar(f_, solo=None):
    a, b = f_["a"], f_["b"]; own = dict(_owners())
    for clave, idb in own.items():
        for c in _fcurvas(idb, _filtro(clave)):
            k = "%s|%s|%d" % (clave, c.data_path, c.array_index)
            if solo and not any(('"%s"' % h) in c.data_path for h in solo): continue
            for i in range(len(c.keyframe_points) - 1, -1, -1):
                if a <= c.keyframe_points[i].co.x <= b: c.keyframe_points.remove(c.keyframe_points[i])
            pts = f_["curvas"].get(k, [])
            if pts:
                n0 = len(c.keyframe_points); c.keyframe_points.add(len(pts))
                for j, (x, y) in enumerate(pts): c.keyframe_points[n0 + j].co = (x, y); c.keyframe_points[n0 + j].interpolation = 'LINEAR'
            c.update()


def _registro(sc):
    try: return json.loads(sc.get("jerry_voces_rapidas", "{}"))
    except Exception: return {}


def _quitar_tiras(sc, tag):
    ed = sc.sequence_editor
    if not ed: return 0
    ts = [t for t in ed.strips_all if t.name.startswith("VozJerry_" + tag) or str(t.get("guion_id", "")).startswith("voz6_jerry_" + tag)]
    for t in ts: (t.parent_meta().strips if t.parent_meta() else ed.strips).remove(t)
    return len(ts)


def quitar(context, tag):
    sc = context.scene; R = _registro(sc); r = R.pop(tag, None)
    if r and r.get("foto"): restaurar(r["foto"])
    n = _quitar_tiras(sc, tag); sc["jerry_voces_rapidas"] = json.dumps(R)
    return n


# ---------------- modo boca ocupada ----------------
def _boca_ocupada(sc, wav, tag, inicio, vol, env, tira=True):
    ed = sc.sequence_editor_create()
    ch = next(c for c in range(1, 129) if not any(t.channel == c and t.frame_final_start < inicio + len(env) and inicio < t.frame_final_end for t in ed.strips_all))
    if tira: s_ = ed.strips.new_sound("VozJerry_%s_1_%d" % (tag, inicio), wav, ch, inicio); s_.volume = vol; s_["vol_base"] = vol; s_["duck_todos"] = True
    A = rig(); fcs = {(c.data_path, c.array_index): c for c in _fcurvas(A)}
    CANAL = [('pose.bones["jaw_bot"].rotation_euler', 0, lambda k, e: -math.radians(4.0) * e * (0.5 + 0.5 * math.sin(k * 1.7))),
             ('pose.bones["spine_2"].rotation_euler', 0, lambda k, e: 0.035 * e * math.sin(k * 0.9)),
             ('pose.bones["spine_2"].rotation_euler', 2, lambda k, e: 0.025 * e * math.sin(k * 0.6 + 1.0))]
    for dp, ix, fn in CANAL:
        fc = fcs.get((dp, ix))
        if fc is None:                                                                   # sin claves: se crean sobre el valor actual
            pb = A.pose.bones[dp.split('"')[1]]
            for k in range(len(env)): pb.keyframe_insert("rotation_euler", index=ix, frame=inicio + k)
            fc = {(c.data_path, c.array_index): c for c in _fcurvas(A)}[(dp, ix)]
        for k, e in enumerate(env):
            f = inicio + k; kp = next((p for p in fc.keyframe_points if abs(p.co.x - f) < 0.5), None)
            if kp is None: fc.keyframe_points.insert(f, fc.evaluate(f)); kp = next(p for p in fc.keyframe_points if abs(p.co.x - f) < 0.5)
            kp.co.y += fn(k, e)
        fc.update()


# ---------------- aplicar ----------------
def aplicar(context, audio, inicio, script=None, tag=None, modo="normal", vol=None, efecto="ninguno"):
    sc = context.scene; tag = _slug(tag or os.path.splitext(os.path.basename(audio))[0]); inicio = int(inicio)
    if modo == "normal" and not script: modo = "solo_audio"
    R = _registro(sc)
    if tag in R: quitar(context, tag); R = _registro(sc)                                    # repetir = restaurar la cara y volver a poner
    wav = preparar_audio(audio, tag, "boca_ocupada" if modo in ("boca_ocupada", "boca_cerrada_cara") and efecto == "ninguno" else efecto)
    env, pico = envolvente(wav); V = float(vol) if vol else vol_auto(pico)
    nfr = len(env); f_ = foto(inicio - 3, inicio + nfr + 3)
    if script: shutil.copyfile(script, os.path.join(AUD, tag + ".cara_original.py"))
    if modo == "normal":
        exec(open(os.path.join(DOCS, "voz_jerry_despierta.py"), encoding="utf-8").read(), {"__name__": "x", "START": inicio, "TAG": tag, "ARCHIVO": tag, "VOL": V})
    elif modo == "solo_audio":
        con = [i for i, e in enumerate(env) if e > 0.08]; A_, B_ = (con[0] + 1, con[-1] + 1) if con else (1, nfr)
        exec(open(os.path.join(DOCS, "voz_jerry_solo_audio.py"), encoding="utf-8").read(), {"__name__": "x", "START": inicio, "TAG": tag, "ARCHIVO": tag, "VOL": V, "VOZ": (A_, B_)})
    elif modo == "boca_cerrada_cara":                                                       # cejas y ojos de la app, pero la BOCA CERRADA (solo tiembla)
        exec(open(os.path.join(DOCS, "voz_jerry_despierta.py"), encoding="utf-8").read(), {"__name__": "x", "START": inicio, "TAG": tag, "ARCHIVO": tag, "VOL": V})
        restaurar(f_, solo=("jaw_bot", "jaw_top")); _boca_ocupada(sc, wav, tag, inicio, V, env, tira=False)
    else:
        _boca_ocupada(sc, wav, tag, inicio, V, env)
    if os.path.isfile(DUCK): exec(open(DUCK, encoding="utf-8").read(), {"__name__": "x", "DUCK": 0.5})
    R[tag] = {"inicio": inicio, "modo": modo, "archivo": wav, "vol": round(V, 3), "frames": nfr, "foto": f_}
    sc["jerry_voces_rapidas"] = json.dumps(R)
    return {"tag": tag, "modo": modo, "inicio": inicio, "fin": inicio + nfr - 1, "vol": round(V, 2), "pico_db": round(20 * math.log10(max(pico, 1e-9)), 1)}
