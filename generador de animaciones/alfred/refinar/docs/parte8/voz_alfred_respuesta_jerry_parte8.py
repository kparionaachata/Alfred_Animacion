# -*- coding: utf-8 -*-
"""Parte 8: Alfred le responde a Jerry "¿Sera porque yo tengo que picar dos bloques y tu solo uno?" (emocion: disgusto) ya girado hacia el (f2155).
Audio `audios/alfred/alfred_respuesta_jerry.mp3` (Record (online-voice-recorder.com) (94).mp3, 68 f, pico 0.688; voz en los frames 9-63 del clip) y su animacion de ojos
`alfred_respuesta_jerry.cara_original.py` (animacion_alfred (11).py; NO se ejecuta: se leen sus constantes con `ast`).
Generico `acciones/voz_alfred_que_paso.py` con START = 2148: voz f2156-2210 (una tira), en cuanto termina de girar hacia Jerry (f2155), sobandose la cabeza. VOL = 1.35 (pico 0.93). Despues `ducking_voces.py`. Ejecutar en Blender con exec."""
A = r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/"
g = {"__name__": "x", "START": 2148, "TAG": "respuesta_jerry", "ARCHIVO": "alfred_respuesta_jerry", "VOL": 1.35, "VOZ_FRASES": [(9, 63)]}
exec(open(A + "voz_alfred_que_paso.py", encoding="utf-8").read(), g)
exec(open(A + "ducking_voces.py", encoding="utf-8").read(), {"__name__": "x"})
