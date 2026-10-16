# -*- coding: utf-8 -*-
"""Parte 8: voz de Alfred "¡Hey! ¿Qué pasó?" (emocion: enojo, de la app `estudio_audio_expresion`) mientras se soba la cabeza tras el golpe del pico de Jerry (f2030).
Audio `audios/alfred/alfred_hey_que_paso.mp3` (Downloads/Record (online-voice-recorder.com) (87).mp3: 1.22 s = 30 f, pico 0.336, -23.9 dB RMS; voz en los frames 4-11 y 16-26 del clip)
y su animacion de ojos `alfred_hey_que_paso.cara_original.py` (Downloads/animacion_alfred (10).py; NO se ejecuta: se leen sus constantes con `ast`).
Usa `acciones/voz_alfred_que_paso.py` (generico) con START = 2057: voz desde f2060 (f2060-2067 y f2072-2082), ojos f2057-2086. VOL = 2.77 (pico 0.93 sin recortar).
Despues `acciones/ducking_voces.py` (baja los sonidos que se solapan y reaplica la distancia a la camara). Ejecutar en Blender: exec(open(RUTA, encoding='utf-8').read())."""
A = r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/"
g = {"__name__": "x", "START": 2057, "TAG": "hey_que_paso", "ARCHIVO": "alfred_hey_que_paso", "VOL": 2.77, "VOZ_FRASES": [(4, 11), (16, 26)]}
exec(open(A + "voz_alfred_que_paso.py", encoding="utf-8").read(), g)
exec(open(A + "ducking_voces.py", encoding="utf-8").read(), {"__name__": "x"})
