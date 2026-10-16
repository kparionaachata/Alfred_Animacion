# -*- coding: utf-8 -*-
"""Parte 11: VOZ de Alfred mientras se saca las flechas: "¿Como paso esto? Oh... Oh... Oh..." + su expresion de ojos.
Audio: audios/alfred/alfred_como_paso_esto.mp3; ojos: alfred_como_paso_esto.cara_original.py (archivo del usuario, NO se ejecuta:
se leen sus datos -coordenadas del shape key, curva de habla, emocion- y se aplican con el tiempo de la escena).
SINCRONIA: el audio se CORTA en 4 trozos (medidos por volumen, a 24 fps): la pregunta al empezar y cada "Oh" en el momento en que
Alfred arranca CADA flecha (las 5: p11_tiempos *_e0), junto al sonido de arrancarla (los 3 "Oh" grabados se reparten).
Ojos: shape key 'Voz_como_paso_esto' + escala/rotacion/posicion como en el archivo del usuario; el habla de cada trozo usa la curva de
SU parte del audio. Repetible. Despues aplica el MICROFONO de camara (ultimo paso)."""
import bpy, ast, math, os, sys, importlib.util
import aud

AUDIO = r"C:\Users\user\Desktop\Alfred_Animacion\audios\alfred\alfred_como_paso_esto.mp3"
CARA = r"C:\Users\user\Desktop\Alfred_Animacion\audios\alfred\alfred_como_paso_esto.cara_original.py"
CORTES = os.path.join(os.path.dirname(AUDIO), "cortes_como_paso_esto")
PREF = "VOZ_p11_alfred_como_paso_esto"; CANAL = 30; SHAPE = "Voz_como_paso_esto"
# (inicio, fin, frame del audio que cae en el ancla) en frames del audio a 24 fps; medido: voz en 3-29, Oh en 46, 69, 94
TROZOS = [("pregunta", 0, 37, 0), ("oh1", 40, 64, 46), ("oh2", 64, 88, 69), ("oh3", 88, 103, 94)]
INICIO_PREGUNTA = 6                     # la pregunta mientras mira las flechas, antes de la primera
# un "Oh" por CADA flecha que se saca (pedido del usuario); los 3 "Oh" grabados se reparten para que no suenen iguales seguidos
FLECHAS_OH = (("flecha_mano_izq", "oh2"), ("flecha_mano_der", "oh3"), ("flecha_pecho", "oh1"), ("flecha_alfred", "oh2"), ("flecha_entrepierna", "oh3"))
RETRASO_OH = 5                          # el "Oh" sale 5 frames despues de que la flecha se suelta del cuerpo


def _datos_cara():
    d = {}
    for n in ast.parse(open(CARA, encoding="utf-8").read()).body:
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id.isupper():
            try: d[n.targets[0].id] = ast.literal_eval(n.value)
            except Exception: pass
    return d


def _microfono():
    sc = bpy.context.scene
    if not hasattr(sc, "microfono"):
        sp = importlib.util.spec_from_file_location("microfono_camara", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\microfono_camara\__init__.py")
        m = importlib.util.module_from_spec(sp); sys.modules["microfono_camara"] = m; sp.loader.exec_module(m); m.register()
    bpy.ops.microfono.analizar(); bpy.ops.microfono.aplicar()


def construir():
    sc = bpy.context.scene; TT = sc["p11_tiempos"]; fps = sc.render.fps; C = _datos_cara()
    # 1. cortar el audio
    os.makedirs(CORTES, exist_ok=True); snd = aud.Sound(AUDIO); rate = int(snd.specs[0])
    trozo = {}
    for nom, a0, a1, a_ancla in TROZOS:
        wav = os.path.join(CORTES, nom + ".wav"); trozo[nom] = (wav, a0, a1, a_ancla)
        snd.limit(a0 / fps, a1 / fps).write(wav, rate, aud.CHANNELS_MONO, aud.FORMAT_S16, aud.CONTAINER_WAV, aud.CODEC_PCM)
    usos = [("pregunta", "pregunta", INICIO_PREGUNTA)] + [(fl.replace("flecha_", "oh_"), oh, int(TT[fl + "_e0"]) + RETRASO_OH) for fl, oh in FLECHAS_OH]
    plan = []                                                    # (nombre, wav, frame_escena_inicio, a0, a1)
    for nom, t, f_ancla in usos:
        wav, a0, a1, a_ancla = trozo[t]; plan.append((nom, wav, f_ancla - (a_ancla - a0), a0, a1))
    # 2. tiras de voz (Alfred es el emisor para el microfono)
    ed = sc.sequence_editor_create(); S_ = ed.strips if hasattr(ed, "strips") else ed.sequences
    for s in [s for s in S_ if s.name.startswith(PREF)]: S_.remove(s)
    raiz = next(o.name for o in sc.objects if o.parent is None and o.type == 'EMPTY' and o.name.lower() == "alfred")
    for nom, wav, f0, a0, a1 in plan:
        s = S_.new_sound(PREF + "_" + nom, wav, CANAL, f0); s["mic_emisor"] = raiz
    # 3. ojos: archivo del usuario con el tiempo de la escena
    habla = {int(f): float(v) for f, v in C["SPEECH_CURVE"]}
    fases = ((0.00, 0.00), (0.12, 0.00), (0.28, 0.70), (0.42, 1.08), (0.57, 0.92), (0.72, 1.02), (0.86, 0.48), (1.00, 0.00))
    T0 = plan[0][2] - 2; T1 = plan[-1][2] + (plan[-1][4] - plan[-1][3]) + 4

    def peso(t):
        u = (t - T0) / (T1 - T0)
        for (a, va), (b, vb) in zip(fases, fases[1:]):
            if a <= u <= b: return va + (vb - va) * (u - a) / max(1e-6, b - a)
        return 0.0

    def nivel(t):
        for nom, wav, f0, a0, a1 in plan:
            if f0 <= t < f0 + (a1 - a0): return habla.get(a0 + (t - f0) + 1, 0.0)   # la curva del usuario empieza en el frame 1
        return 0.0

    gap = (plan[1][2] + (plan[1][4] - plan[1][3]) + plan[2][2]) // 2                   # parpadeo entre el 1er y 2o "Oh" (como en el audio)
    for i, (nombre, coords) in enumerate(C["COORDINATES"].items()):
        ojo = bpy.data.objects[nombre]
        if len(ojo.data.vertices) != len(coords): raise RuntimeError("topologia distinta en " + nombre)
        kb = ojo.data.shape_keys.key_blocks
        if kb.get(SHAPE): ojo.shape_key_remove(kb[SHAPE])
        sk = ojo.shape_key_add(name=SHAPE, from_mix=False); sk.slider_min = -2.0; sk.slider_max = 2.0
        sk.data.foreach_set("co", [c for v in coords for c in v])
        for ad in (ojo.animation_data, ojo.data.shape_keys.animation_data):            # solo esta voz anima los ojos en la parte 11
            if ad and ad.action: bpy.data.actions.remove(ad.action)
        if ojo.animation_data: ojo.animation_data_clear()
        if ojo.data.shape_keys.animation_data: ojo.data.shape_keys.animation_data_clear()
        bl, bs, br = ojo.location.copy(), ojo.scale.copy(), ojo.rotation_euler.copy()
        lado = 1.0 if ojo.matrix_world.translation.x > 0 else -1.0; amt = 1.0 if i == 0 else 0.86; prev = 0.0
        for t in range(T0, T1 + 1):
            w = peso(t); lv = nivel(t); ataque = max(0.0, lv - prev); ola = math.sin(t * 1.34 + i * 0.16); estira = ola * lv
            sk.value = C["SHAPE_VALUE"] * w * amt; sk.keyframe_insert("value", frame=t)
            ojo.location = bl.copy(); ojo.location.x += lado * C["LATERAL"] * w * (1.0 if i == 0 else -0.55)
            ojo.location.z += C["VERTICAL"] * w * (1.0 if t < T0 + (T1 - T0) * 0.60 else 0.65) + C["SPEECH_VERTICAL"] * lv * ola * amt
            ojo.scale = bs.copy()
            ojo.scale.x *= (1.0 + (C["SCALE_X"] - 1.0) * w * amt) * (1.0 + C["SPEECH_SCALE_X"] * lv - 0.040 * estira)
            ojo.scale.y *= 1.0 - 0.025 * lv
            ojo.scale.z *= (1.0 + (C["SCALE_Z"] - 1.0) * w * amt) * (1.0 + C["SPEECH_SCALE_Z"] * lv + 0.065 * estira + 0.025 * ataque)
            ojo.rotation_euler = br.copy(); ojo.rotation_euler.y += lado * (C["ROTATION"] * w + C["ATTACK_ROTATION"] * ataque) * amt
            for p in ("location", "scale", "rotation_euler"): ojo.keyframe_insert(p, frame=t)
            prev = lv
        ojo.location, ojo.scale, ojo.rotation_euler = bl, bs, br
        cl = kb.get("Closed")
        if cl:
            for f, v in ((T0, 0.0), (gap - 2, 0.0), (gap, 1.0), (gap + 2, 0.0), (T1, 0.0)):
                cl.value = v; cl.keyframe_insert("value", frame=f)
    sc["p11_voz_como_paso"] = {n: f0 for n, w_, f0, a0, a1 in plan}
    _microfono()
    print("VOZ ALFRED 'como paso esto':", dict(sc["p11_voz_como_paso"]), "ojos", T0, "-", T1)
    return dict(sc["p11_voz_como_paso"])


if __name__ in ("__main__", "x"):
    construir()
