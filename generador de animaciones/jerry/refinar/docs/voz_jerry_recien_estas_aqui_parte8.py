# -*- coding: utf-8 -*-
"""Parte 8: voz de Jerry "¿Que, recien estas aqui?" (emocion: enojo 0.88 / sospecha 0.12, de la app `estudio_audio_expresion`) cuando ya se paro y mira a Alfred.
Audio `audios/jerry/jerry_recien_estas_aqui.wav` (Downloads/Record (online-voice-recorder.com) (93)_Jerry_..wav, pico 0.419) y su animacion `jerry_recien_estas_aqui.cara_original.py`
(Downloads/animacion_jerry (8).py, 41 f; voz en los frames 5-13, 19-27, 29-32 y 34-38 del clip; NO se ejecuta: se leen sus constantes con `ast`).
Usa `voz_jerry_despierta.py` (generico) con START = 2100 (frame 1 del clip): voz desde f2104. VOL = 2.22 (pico 0.93 sin recortar). La expresion se SUMA: no repetir sobre el mismo rango.
Despues `ducking_voces.py` (Alfred) para el ducking y la distancia a la camara. Ejecutar en Blender: exec(open(RUTA, encoding='utf-8').read())."""
g = {"__name__": "x", "START": 2100, "TAG": "recien_estas_aqui", "ARCHIVO": "jerry_recien_estas_aqui", "VOL": 2.22}
exec(open(r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/jerry/refinar/docs/voz_jerry_despierta.py", encoding="utf-8").read(), g)
exec(open(r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/ducking_voces.py", encoding="utf-8").read(), {"__name__": "x"})
