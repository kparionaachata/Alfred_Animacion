# -*- coding: utf-8 -*-
"""Parte 8: Alfred le responde a Jerry "Ahi si, todo yo, ¿no?" (emocion: enojo) tras "Mejor anda colocando rapido la antorcha..." (voz de Jerry hasta f2339).
Audio `audios/alfred/alfred_responde_antorcha.mp3` (Record (online-voice-recorder.com) (98).mp3) y sus ojos `alfred_responde_antorcha.cara_original.py` (animacion_alfred (13).py, 28 f;
voz en los frames 4-25 del clip segun el audio: la curva de la app acaba en el 20 y cortaba el "¿no?"). Generico `acciones/voz_alfred_que_paso.py` con START = 2347: voz f2350-2371 (12 f despues de Jerry). Despues `ducking_voces.py`. Ejecutar en Blender con exec."""
A = r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/"
g = {"__name__": "x", "START": 2347, "TAG": "responde_antorcha", "ARCHIVO": "alfred_responde_antorcha", "VOL": 1.9, "VOZ_FRASES": [(4, 25)]}
exec(open(A + "voz_alfred_que_paso.py", encoding="utf-8").read(), g)
exec(open(A + "ducking_voces.py", encoding="utf-8").read(), {"__name__": "x"})
