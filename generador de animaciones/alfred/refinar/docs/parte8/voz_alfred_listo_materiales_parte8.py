# -*- coding: utf-8 -*-
"""Parte 8: ya mirando la cueva con las manos en la cintura (pose desde f2441), Alfred dice "Ahora si, listo para buscar materiales." (emocion: afirmacion).
Audio `audios/alfred/alfred_mira_cueva.mp3` (Record (online-voice-recorder.com) (100).mp3, pico 0.421; voz en los frames 7-65 del clip, medido en el audio) y sus ojos
`alfred_mira_cueva.cara_original.py` (animacion_alfred (16).py, 69 f). Generico `acciones/voz_alfred_que_paso.py` con START = 2452: voz f2458-2516, despues de que Jerry
termina "No es tan profunda esta cueva" (f2453). VOL 2.21. Despues `ducking_voces.py`. Ejecutar en Blender con exec."""
A = r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/"
g = {"__name__": "x", "START": 2452, "TAG": "listo_materiales", "ARCHIVO": "alfred_mira_cueva", "VOL": 2.21, "VOZ_FRASES": [(7, 65)]}
exec(open(A + "voz_alfred_que_paso.py", encoding="utf-8").read(), g)
exec(open(A + "ducking_voces.py", encoding="utf-8").read(), {"__name__": "x"})
