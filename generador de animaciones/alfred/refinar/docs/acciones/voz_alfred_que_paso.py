# -*- coding: utf-8 -*-
"""Parte 6: voz + ojos de Alfred desde una animacion de la app `estudio_audio_expresion`. GENERICO: variables `START`, `TAG` (forma `Voz_<TAG>`), `ARCHIVO` (base de `audios/alfred/<ARCHIVO>.mp3` y `.cara_original.py`) y `VOL`.
Usos: f314 "¿Que paso?" (duda; valores por omision) y f512 "Ah, ya se su idea, al fin." (afirmacion; START=512, TAG="ya_se_su_idea", ARCHIVO="alfred_ya_se_su_idea", VOL=1.8).
Primer uso: f314+: Alfred (que acaba de levantarse) dice "¿Que paso?" (emocion: duda).
Audio `audios/alfred/alfred_que_paso.mp3` (1.8 s = 43 f; voz en los frames 4-22 y 26-40 del clip) y animacion de ojos `audios/alfred/alfred_que_paso.cara_original.py` (script de la app `estudio_audio_expresion`).
NO se ejecuta el script de la app (limpia con `animation_data_clear()` las claves de los ojos): sus constantes se leen con `ast` y se aplican igual que el original pero solo en f314-357, creando la forma `Voz_que_paso` (shape key `Audio_procedural` renombrada, con las coordenadas del script; las mallas de los ojos ya tienen la misma topologia, 1538 vertices) como las demas `Voz_*` de los ojos:
 shape key * emocion (8 fases), ubicacion/escala/rotacion de cada ojo con el acento del habla (squash y stretch), un parpadeo en el frame 23 del clip (f336). Los ojos de Alfred no tienen otras claves en la escena. Cambio respecto al script: el lado de cada ojo (`side`) se toma de su ubicacion LOCAL (x>0 = izquierdo) y no de la mundial (la escena esta en x -92, que invertia el signo).
Audio: tira `VozAlfred_que_paso_*` (voz +-2 f), volumen 2.6 (+8.3 dB; la grabacion cruda es baja: pico 0.36, -27.9 dB RMS; con 2.6 el pico queda en 0.93 sin recortar) y propiedad `duck_todos`: los sonidos de la animacion que se solapan bajan a la mitad (`ducking_voces.py`, DUCK 0.5).
Se ejecuta DENTRO de Blender con exec. Repetible. Nunca `raise SystemExit`. Variable opcional: START (314)."""
import bpy, ast, math, traceback

def canal_libre(ed, a, b):   # el VSE solo tiene 128 canales: busca uno sin tiras en [a, b] (new_sound desplaza la tira si el canal esta ocupado)
    for ch in range(1, 129):
        if not any(t.channel == ch and t.frame_final_start < b and a < t.frame_final_end for t in ed.strips_all): return ch
    raise RuntimeError('sin canal libre')
try:
    sc = bpy.context.scene; ed = sc.sequence_editor
    START = int(globals().get("START", 314)); VOL = float(globals().get("VOL", 2.6)); PAD = 2; TAG = globals().get("TAG", "que_paso")
    BASE_AUD = "C:/Users/user/Desktop/Alfred_Animacion/audios/alfred/" + globals().get("ARCHIVO", "alfred_que_paso"); SRC = BASE_AUD + ".cara_original.py"; MP3 = BASE_AUD + ".mp3"
    NOM = ("COORDINATES", "END_FRAME", "SHAPE_VALUE", "SCALE_X", "SCALE_Z", "VERTICAL", "ROTATION", "ATTACK_ROTATION", "LATERAL", "BLINK_CENTERS", "SPEECH_CURVE", "SPEECH_VERTICAL", "SPEECH_SCALE_X", "SPEECH_SCALE_Z", "phase_data")
    C = {}
    for nd in ast.parse(open(SRC, encoding="utf-8").read()).body:
        if isinstance(nd, ast.Assign) and len(nd.targets) == 1 and isinstance(nd.targets[0], ast.Name) and nd.targets[0].id in NOM: C[nd.targets[0].id] = ast.literal_eval(nd.value)
    END = C["END_FRAME"]; F = lambda k: START + k - 1; FIN = F(END); PH = C["phase_data"]; speech = {int(k): float(v) for k, v in C["SPEECH_CURVE"]}
    def emotion_weight(k):
        pos = (k - 1) / max(1, END - 1)
        for i in range(len(PH) - 1):
            lt, lv = PH[i]; rt, rv = PH[i + 1]
            if lt <= pos <= rt: return lv + (rv - lv) * ((pos - lt) / max(1e-6, rt - lt))
        return 0.0
    NAME = "Voz_" + TAG
    for ei, (nm, coords) in enumerate(C["COORDINATES"].items()):
        eye = bpy.data.objects[nm]
        if len(eye.data.vertices) != len(coords): raise RuntimeError("Topologia incompatible en " + nm)
        blocks = eye.data.shape_keys.key_blocks; old = blocks.get(NAME)
        if old: eye.shape_key_remove(old)
        shape = eye.shape_key_add(name=NAME, from_mix=False); shape.slider_min = -2.0; shape.slider_max = 2.0
        for v, co in enumerate(coords): shape.data[v].co = co
        # limpiar solo claves previas de ESTA forma y del rango (por si se repite)
        ad = eye.data.shape_keys.animation_data
        if ad and ad.action:
            for fc in ad.action.layers[0].strips[0].channelbags[0].fcurves:
                for i in range(len(fc.keyframe_points) - 1, -1, -1):
                    if F(1) <= fc.keyframe_points[i].co.x <= FIN + 1: fc.keyframe_points.remove(fc.keyframe_points[i])
        sc.frame_set(F(1)); bl = eye.location.copy(); bs = eye.scale.copy(); br = eye.rotation_euler.copy(); side = 1.0 if eye.location.x > 0 else -1.0; amt = 1.0 if ei == 0 else 0.86; prev = 0.0
        for k in range(1, END + 1):
            f = F(k); w = emotion_weight(k); lv = speech.get(k, 0.0); att = max(0.0, lv - prev); wave = math.sin(k * 1.34 + ei * 0.16); stretch = wave * lv
            shape.value = C["SHAPE_VALUE"] * w * amt; shape.keyframe_insert("value", frame=f)
            eye.location = bl.copy(); eye.location.x += side * C["LATERAL"] * w * (1.0 if ei == 0 else -0.55); eye.location.z += C["VERTICAL"] * w * (1.0 if k < END * 0.60 else 0.65); eye.location.z += C["SPEECH_VERTICAL"] * lv * wave * amt
            eye.scale = bs.copy(); eye.scale.x *= 1.0 + (C["SCALE_X"] - 1.0) * w * amt; eye.scale.z *= 1.0 + (C["SCALE_Z"] - 1.0) * w * amt
            eye.scale.x *= 1.0 + C["SPEECH_SCALE_X"] * lv - 0.040 * stretch; eye.scale.y *= 1.0 - 0.025 * lv; eye.scale.z *= 1.0 + C["SPEECH_SCALE_Z"] * lv + 0.065 * stretch + 0.025 * att
            eye.rotation_euler = br.copy(); eye.rotation_euler.y += side * C["ROTATION"] * w * amt; eye.rotation_euler.y += side * C["ATTACK_ROTATION"] * att * amt
            for ch in ("location", "scale", "rotation_euler"): eye.keyframe_insert(ch, frame=f)
            prev = lv
        shape.value = 0.0; shape.keyframe_insert("value", frame=FIN + 1)
        closed = blocks.get("Closed")
        if closed:
            for center in C["BLINK_CENTERS"]:
                for k, val in ((center - 2, 0.0), (center, 1.0), (center + 2, 0.0)): closed.value = val; closed.keyframe_insert("value", frame=F(k))
        for owner in (eye, eye.data.shape_keys):
            if owner.animation_data and owner.animation_data.action:
                for fc in owner.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
                    for kp in fc.keyframe_points:
                        if F(1) <= kp.co.x <= FIN + 1: kp.interpolation = 'BEZIER'
    # ---------- audio ----------
    for s_ in [s_ for s_ in ed.strips_all if str(s_.get("guion_id", "")).startswith("voz6_alfred_" + TAG)]: ed.strips.remove(s_)
    ks = sorted(k for k, v in speech.items() if v > 0.02); segs = []
    UMBRAL = float(globals().get("UMBRAL", 0.02))                                           # la curva de la app suaviza y casi nunca baja a 0 entre frases: para varias frases pasar VOZ=[(a, b), ...] (frames del audio con voz) o usar `voz_alfred_solo_audio.py` para las tiras
    for k in (globals().get("VOZ_FRASES") and [x for a_, b_ in VOZ_FRASES for x in range(a_, b_ + 1)] or ks):    # una tira por tramo de voz
        if segs and k - segs[-1][1] <= 6: segs[-1][1] = k
        else: segs.append([k, k])
    for i, (a, b) in enumerate(segs):
        s_ = ed.strips.new_sound(f"VozAlfred_{TAG}_{i + 1}_{F(a)}", MP3, canal_libre(ed, START, START + 400), START); n_tot = int(s_.frame_final_duration)
        s_.frame_offset_start = max(0, a - 1 - PAD); s_.frame_offset_end = max(0, n_tot - (b + PAD)); s_.volume = VOL; s_["vol_base"] = VOL; s_["duck_todos"] = True; s_["guion_id"] = f"voz6_alfred_{TAG}_{i + 1}"
        print(s_.name, "canal", s_.channel, "tira f", int(s_.frame_final_start), "-", int(s_.frame_final_end), "voz f", F(a), "-", F(b))
    exec(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\ducking_voces.py", encoding="utf-8").read(), {"__name__": "x", "DUCK": 0.5})
    sc.frame_end = max(sc.frame_end, FIN)
    eyeL = bpy.data.objects["ojo_izquierdo_alfred"]; res = {}
    for f in (F(1), F(8), F(20), F(23), F(30), F(44)):
        sc.frame_set(f); res[f] = {"forma": round(eyeL.data.shape_keys.key_blocks[NAME].value, 3), "scale": [round(x, 3) for x in eyeL.scale], "z": round(eyeL.location.z, 4), "Closed": round(eyeL.data.shape_keys.key_blocks["Closed"].value, 2)}
    sc.frame_set(120); print(res); print("LISTO")
except Exception:
    traceback.print_exc()
