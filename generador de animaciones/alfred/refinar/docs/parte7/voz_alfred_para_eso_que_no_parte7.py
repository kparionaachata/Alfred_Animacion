# -*- coding: utf-8 -*-
"""Parte 7: voz de Alfred "Pues para eso que no." (emocion: duda, de la app `estudio_audio_expresion`) a partir del frame 596 (reemplaza a "No, pues parece que no.").
Audio `audios/alfred/alfred_para_eso_que_no.mp3` (de `Downloads/Record (online-voice-recorder (mp3cut.net) (3).mp3`; 46 f, pico 0.494; voz en los frames 2-5 y 20-42 del clip) y su animacion de ojos `alfred_para_eso_que_no.cara_original.py` (script de la app, NO se ejecuta: se leen sus constantes con `ast`).
Usa `acciones/voz_alfred_que_paso.py` (generico) con START = 596, TAG = "para_eso_que_no", VOL = 1.88 (pico 0.93 sin recortar): tira `VozAlfred_para_eso_que_no_1_598` (f596-637, canal 1), voz en f598-634, ojos f596-641, un parpadeo propio en f618.
Para reemplazar una voz anterior hay que quitar primero su tira (`guion_id` `voz6_alfred_<TAG>`), su forma `Voz_<TAG>` y las claves de ojo (location/scale/rotation/Closed) de su rango. Se ejecuta DENTRO de Blender: exec(open(RUTA, encoding='utf-8').read())."""
g = {"__name__": "x", "START": 596, "TAG": "para_eso_que_no", "ARCHIVO": "alfred_para_eso_que_no", "VOL": 1.88}
exec(open(r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/voz_alfred_que_paso.py", encoding="utf-8").read(), g)
