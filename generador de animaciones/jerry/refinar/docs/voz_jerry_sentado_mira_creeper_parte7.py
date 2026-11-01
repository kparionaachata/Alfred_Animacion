# -*- coding: utf-8 -*-
"""Parte 7: voz de Jerry "¿Qué pasó? ¿no exploto?" (emocion: duda, de la app `estudio_audio_expresion`) a partir del frame 526: se quita las patas de la cabeza, se sienta mirando al creeper y se para (f525-567).
Audio `audios/jerry/jerry_sentado_mira_creeper.wav` (2.2 s = 53 f, pico 0.705, -25.3 dB RMS; voz en los frames 4-11 y 40-51 del clip) y su animacion `jerry_sentado_mira_creeper.cara_original.py` (script de la app, NO se ejecuta: se leen sus constantes con `ast`; Sospecha 0.72 + Triste 0.28).
Usa `voz_jerry_despierta.py` (generico): START = 526, TAG = "sentado_mira_creeper", VOL = 1.32 (pico 0.93 sin recortar): dos tiras `VozJerry_sentado_mira_creeper_1_529` (f527-540) y `_2_565` (f563-579) y la cara (ojos, pupilas, cejas, mandibula, hocico) f526-578.
La expresion se SUMA a lo que Jerry ya anima y NO se debe repetir sobre el mismo rango (ni correr antes `voz_jerry_solo_audio.py` en este rango: duplica la mandibula). Se ejecuta DENTRO de Blender: exec(open(RUTA, encoding='utf-8').read())."""
g = {"__name__": "x", "START": 526, "TAG": "sentado_mira_creeper", "ARCHIVO": "jerry_sentado_mira_creeper", "VOL": 1.32}
exec(open(r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/jerry/refinar/docs/voz_jerry_despierta.py", encoding="utf-8").read(), g)
