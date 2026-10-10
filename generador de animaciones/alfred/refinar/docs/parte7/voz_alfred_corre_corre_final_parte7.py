# -*- coding: utf-8 -*-
"""Parte 7: voz de Alfred "¡Corre, corre, corre, corre, corre!" (emocion: sorpresa, de la app `estudio_audio_expresion`) a partir del frame 675 (cuando el creeper brilla y Alfred se asusta).
Audio `audios/alfred/alfred_corre_corre_final.mp3` (de `Downloads/Record (online-voice-recorder.com) (86).mp3`; 36 f, pico 0.752; voz continua en los frames 3-34 del clip) y su animacion de ojos `alfred_corre_corre_final.cara_original.py` (script de la app, NO se ejecuta: se leen sus constantes con `ast`).
Usa `acciones/voz_alfred_que_paso.py` (generico) con START = 675, TAG = "corre_final", VOL = 1.24 (pico 0.93 sin recortar): tira `VozAlfred_corre_final_1_679` (f677-710, canal 1), voz en f679-707, ojos f675-710, un parpadeo propio en f693.
Se ejecuta DENTRO de Blender: exec(open(RUTA, encoding='utf-8').read())."""
g = {"__name__": "x", "START": 675, "TAG": "corre_final", "ARCHIVO": "alfred_corre_corre_final", "VOL": 1.24}
exec(open(r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/voz_alfred_que_paso.py", encoding="utf-8").read(), g)
