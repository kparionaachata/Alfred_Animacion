# -*- coding: utf-8 -*-
"""Parte 10: VOZ de Jerry desde f130 mientras jala a Alfred con la ropa en la boca: suena AHOGADA ("con la boca ocupada").
Audio: Downloads/Record (online-voice-recorder.com) - 2026-10-12T105618.027_Jerry_..wav -> `audios/jerry/jerry_boca_ocupada_original.wav` (2.5 s = 60 f).
Efecto (ffmpeg, version 3 SUAVE) -> `audios/jerry/jerry_boca_ocupada.wav`: paso alto 150 Hz + paso bajo 3800 Hz, +1 dB en 450 Hz (resonancia de
boca cerrada), -3 dB en 3.2 kHz, compresor 2:1 y +4 dB.
Tira `VozJerry_boca_ocupada_1_130` (frame 1 del clip = f130, volumen VOL, `duck_todos`). Sincronia SIN abrir la boca (esta mordiendo): la mandibula SOLO tiembla
+-4 grados y la cabeza da cabeceos cortos con la ENVOLVENTE del audio, SUMADO a las claves que ya tiene Jerry. Repetible (guarda los deltas en la escena y los resta)."""
import bpy, wave, math
import numpy as np
sc = bpy.context.scene; START = 130; VOL = 2.0; TAG = "boca_ocupada"
WAV = r"C:\Users\user\Desktop\Alfred_Animacion\audios\jerry\jerry_boca_ocupada.wav"
JA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'scull_1' in o.pose.bones)
# ---- envolvente por frame ----
w = wave.open(WAV); sr = w.getframerate(); d = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float); fl = sr / 24.0
rms = np.array([np.sqrt((d[int(i * fl):int((i + 1) * fl)] ** 2).mean()) for i in range(int(len(d) / fl))]); env = np.clip(rms / rms.max(), 0, 1)
# ---- tira de audio ----
ed = sc.sequence_editor_create()
for t in [t for t in ed.strips_all if t.name.startswith("VozJerry_" + TAG)]: ed.strips.remove(t)
ch = next(c for c in range(1, 129) if not any(t.channel == c and t.frame_final_start < START + len(env) and START < t.frame_final_end for t in ed.strips_all))
s_ = ed.strips.new_sound("VozJerry_%s_1_%d" % (TAG, START), WAV, ch, START); s_.volume = VOL; s_["duck_todos"] = True
# ---- sincronia: temblor de mandibula y cabeceos (deltas sumados, repetible) ----
fcs = {(c.data_path, c.array_index): c for l in JA.animation_data.action.layers for st in l.strips for b in st.channelbags for c in b.fcurves}
prev = sc.get("p10_voz_jerry_deltas", {})
for key, vals in prev.items():                                                              # quitar los deltas de una ejecucion anterior
    dp, ix = key.rsplit("|", 1); fc = fcs.get((dp, int(ix)))
    if fc:
        for kp in fc.keyframe_points:
            k = str(int(round(kp.co.x)))
            if k in vals: kp.co.y -= vals[k]
        fc.update()
nuevos = {}
CANAL = [('pose.bones["jaw_bot"].rotation_euler', 0, lambda k, e: -math.radians(4.0) * e * (0.5 + 0.5 * math.sin(k * 1.7))),          # tiembla la mandibula (no se abre)
         ('pose.bones["spine_2"].rotation_euler', 0, lambda k, e: 0.035 * e * math.sin(k * 0.9)),                                     # cabeceo corto al hablar
         ('pose.bones["spine_2"].rotation_euler', 2, lambda k, e: 0.025 * e * math.sin(k * 0.6 + 1.0))]
for dp, ix, fn in CANAL:
    fc = fcs.get((dp, ix))
    if fc is None: continue
    vals = {}
    for kp in fc.keyframe_points:
        k = int(round(kp.co.x)) - START
        if 0 <= k < len(env): dv = fn(k, float(env[k])); kp.co.y += dv; vals[str(int(round(kp.co.x)))] = dv
    fc.update(); nuevos["%s|%d" % (dp, ix)] = vals
sc["p10_voz_jerry_deltas"] = nuevos
print("VOZ JERRY boca ocupada: f%d-%d, canal %d, %d canales sincronizados" % (START, START + len(env) - 1, ch, len(nuevos)))
