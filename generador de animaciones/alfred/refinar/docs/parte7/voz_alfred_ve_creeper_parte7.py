# -*- coding: utf-8 -*-
"""Parte 7: voz de Alfred "Ah, el creeper." (emocion: sorpresa, de la app `estudio_audio_expresion`) JUSTO DESPUES de levantar la cabeza y ver al creeper (la cabeza sube en f384-387 y los brazos se abren en f386-393).
Audio `audios/alfred/alfred_ve_creeper.mp3` (1.2 s = 29 f, pico 0.601, -20.4 dB RMS; voz en los frames 2-26 del clip) y su animacion de ojos `alfred_ve_creeper.cara_original.py` (script de la app, NO se ejecuta: se leen sus constantes con `ast`).
Usa `acciones/voz_alfred_que_paso.py` (generico) con START = 386: la voz suena en f388-410 (tira `VozAlfred_ah_el_creeper_1_388`, canal 1), en pleno susto (arrancan los aleteos en f394); VOL = 1.55 (pico 0.93 sin recortar).
Se ejecuta DENTRO de Blender: exec(open(RUTA, encoding='utf-8').read())."""
g = {"__name__": "x", "START": 386, "TAG": "ah_el_creeper", "ARCHIVO": "alfred_ve_creeper", "VOL": 1.55}
exec(open(r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/voz_alfred_que_paso.py", encoding="utf-8").read(), g)
