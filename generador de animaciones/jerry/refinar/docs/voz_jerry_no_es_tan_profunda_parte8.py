# -*- coding: utf-8 -*-
"""Parte 8: mientras mira la cueva (de lado a lado desde f2394), Jerry dice "No es tan profunda esta cueva." (emocion: curiosidad -> sospecha 0.62 / sorpresa 0.28 / feliz 0.1).
Audio `audios/jerry/jerry_no_es_tan_profunda.wav` (Record (99)_Jerry_..wav) y su animacion `jerry_no_es_tan_profunda.cara_original.py` (Downloads/animacion_jerry (11).py, 39 f; voz en los
frames 4-34 del clip; NO se ejecuta: se leen sus constantes con `ast`). Generico `voz_jerry_despierta.py` con START = 2420 (voz f2423-2453). La expresion se SUMA: no repetir sobre el
mismo rango. Despues `ducking_voces.py`. Ejecutar en Blender con exec."""
g = {"__name__": "x", "START": 2420, "TAG": "no_es_tan_profunda", "ARCHIVO": "jerry_no_es_tan_profunda", "VOL": 3.03}
exec(open(r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/jerry/refinar/docs/voz_jerry_despierta.py", encoding="utf-8").read(), g)
exec(open(r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/ducking_voces.py", encoding="utf-8").read(), {"__name__": "x"})
