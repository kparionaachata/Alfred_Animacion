# -*- coding: utf-8 -*-
"""Parte 10: VOZ de Alfred mientras intenta levantarse (Record (online-voice-recorder.com) (64).mp3 -> `audios/alfred/alfred_despertar.wav`, 2.2 s = 53 f).
Tira `VozAlfred_despertar_1_<inicio>` desde 2 f despues de que empieza a levantarse (`p10_tiempos` T_SIENTA0), volumen VOL, `duck_todos`.
La ENVOLVENTE del audio queda en `scene["p10_voz_alfred"]` y `filtros_y_parpadeos_parte10.py` la usa para mover los OJOS ASIMETRICOS al ritmo de la voz
(en cada golpe de voz aprieta los ojos: el derecho mas que el izquierdo). Ejecutar antes de `filtros_y_parpadeos_parte10.py`. Repetible."""
import bpy, wave
import numpy as np
sc = bpy.context.scene; VOL = 2.0; TAG = "despertar"
WAV = r"C:\Users\user\Desktop\Alfred_Animacion\audios\alfred\alfred_despertar.wav"
INICIO = int(sc["p10_tiempos"]["T_SIENTA0"]) + 2
w = wave.open(WAV); sr = w.getframerate(); d = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float); fl = sr / 24.0
rms = np.array([np.sqrt((d[int(i * fl):int((i + 1) * fl)] ** 2).mean()) for i in range(int(len(d) / fl))]); env = np.clip(rms / rms.max(), 0, 1)
ed = sc.sequence_editor_create()
for t in [t for t in ed.strips_all if t.name.startswith("VozAlfred_" + TAG)]: ed.strips.remove(t)
ch = next(c for c in range(1, 129) if not any(t.channel == c and t.frame_final_start < INICIO + len(env) and INICIO < t.frame_final_end for t in ed.strips_all))
s_ = ed.strips.new_sound("VozAlfred_%s_1_%d" % (TAG, INICIO), WAV, ch, INICIO); s_.volume = VOL; s_["vol_base"] = VOL; s_["duck_todos"] = True
sc["p10_voz_alfred"] = {"inicio": INICIO, "env": [round(float(v), 3) for v in env]}
print("VOZ ALFRED despertar: f%d-%d (canal %d)" % (INICIO, INICIO + len(env) - 1, ch))
