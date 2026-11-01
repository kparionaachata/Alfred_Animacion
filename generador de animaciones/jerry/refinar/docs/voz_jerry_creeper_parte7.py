# -*- coding: utf-8 -*-
"""Parte 7: voz de Jerry "¡Creeper!" (emocion: sorpresa, de la app `estudio_audio_expresion`) en el instante en que se TIRA AL SUELO y se tapa la cabeza (el brinco elastico hacia la pose boca abajo empieza en f382).
Audio `audios/jerry/jerry_creeper.wav` (0.52 s = 13 f, pico 0.575, -20.7 dB RMS; voz en los frames 4-11 del clip) y su animacion `jerry_creeper.cara_original.py` (script de la app, NO se ejecuta: se leen sus constantes con `ast`; la expresion dura 24 f).
Usa `voz_jerry_despierta.py` (generico): START = 379, TAG = "creeper", VOL = 1.62 (pico 0.93 sin recortar): la voz suena en f382-389 (tira `VozJerry_creeper_1_382`, canal 2, visible f380-391), justo cuando empieza a tirarse, y la cara (sorpresa) dura f379-402.
La expresion se SUMA a lo que Jerry ya anima y NO se debe repetir sobre el mismo rango. Se ejecuta DENTRO de Blender: exec(open(RUTA, encoding='utf-8').read())."""
g = {"__name__": "x", "START": 379, "TAG": "creeper", "ARCHIVO": "jerry_creeper", "VOL": 1.62}
exec(open(r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/jerry/refinar/docs/voz_jerry_despierta.py", encoding="utf-8").read(), g)
