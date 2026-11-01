# -*- coding: utf-8 -*-
"""Parte 8: Jerry le responde a Alfred "Excusas y excusas" (emocion: enojo 0.88 / sospecha 0.12) justo despues de la frase de Alfred (f2156-2210), de pie mirandolo.
Audio `audios/jerry/jerry_excusas.wav` (Record (online-voice-recorder.com) (96)_Jerry_..wav) y su animacion `jerry_excusas.cara_original.py` (Downloads/animacion_jerry (9).py, 31 f;
voz en los frames 3-26 del clip; NO se ejecuta: se leen sus constantes con `ast`). Generico `voz_jerry_despierta.py` con START = 2230 (voz desde f2232, 22 f despues de la frase de Alfred). La expresion se SUMA:
no repetir sobre el mismo rango. Despues `ducking_voces.py`. Ejecutar en Blender con exec."""
g = {"__name__": "x", "START": 2230, "TAG": "excusas", "ARCHIVO": "jerry_excusas", "VOL": 2.01}
exec(open(r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/jerry/refinar/docs/voz_jerry_despierta.py", encoding="utf-8").read(), g)
exec(open(r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/ducking_voces.py", encoding="utf-8").read(), {"__name__": "x"})
