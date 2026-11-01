# -*- coding: utf-8 -*-
"""Parte 8: 20 f despues de "Excusas y excusas" (voz hasta f2255), Jerry le dice a Alfred "Mejor anda colocando rapido la antorcha, antes que aparezcan los zombies."
(emocion: disgusto -> sospecha 0.55 / enojo 0.35 / triste 0.1). Audio `audios/jerry/jerry_coloca_antorcha.wav` (Record (97)_Jerry_..wav) y su animacion
`jerry_coloca_antorcha.cara_original.py` (Downloads/animacion_jerry (10).py, 72 f; voz en los frames 5-68 del clip; NO se ejecuta: se leen sus constantes con `ast`).
Generico `voz_jerry_despierta.py` con START = 2271 (voz desde f2275). La expresion se SUMA: no repetir sobre el mismo rango. Despues `ducking_voces.py`. Ejecutar en Blender con exec."""
g = {"__name__": "x", "START": 2271, "TAG": "coloca_antorcha", "ARCHIVO": "jerry_coloca_antorcha", "VOL": 1.96}
exec(open(r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/jerry/refinar/docs/voz_jerry_despierta.py", encoding="utf-8").read(), g)
exec(open(r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/ducking_voces.py", encoding="utf-8").read(), {"__name__": "x"})
