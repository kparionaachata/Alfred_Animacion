# -*- coding: utf-8 -*-
"""Parte 7: voz de Jerry "Corre, corre, corre, corre, corre, corre, corre, corre, corre." (emocion: cansancio, de la app `estudio_audio_expresion`) mientras CORRE por la ruta, a partir del frame 30 (el frame 1 del clip = f30).
Audio `audios/jerry/jerry_corre_corre.wav` (2.184 s = 53 f, pico 0.523, -21.2 dB RMS; voz en los frames 5-51 del clip) y su animacion `jerry_corre_corre.cara_original.py` (script de la app `estudio_audio_expresion`, NO se ejecuta: se leen sus constantes con `ast`).
Usa `voz_jerry_despierta.py` (generico): START = 30, TAG = "corre_corre", VOL = 1.78 (pico 0.93 sin recortar). La voz suena en f34-80 (tira `VozJerry_corre_corre_1_34`, canal 2, visible f32-82). La expresion se SUMA a lo que Jerry ya anima (mandibula `jaw_bot`
hasta -25 grados con la voz, hocico, cabeza, cejas, ojos Cansado/Cerrado) y NO se debe repetir sobre el mismo rango. Despues hay que volver a ejecutar `alfred/refinar/docs/parte7/filtros_organicos_y_parpadeos_parte7.py` (el parpadeo al azar de Jerry se salta f16-97).
Se ejecuta DENTRO de Blender: exec(open(RUTA, encoding='utf-8').read())."""
g = {"__name__": "x", "START": 30, "TAG": "corre_corre", "ARCHIVO": "jerry_corre_corre", "VOL": 1.78}
exec(open(r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/jerry/refinar/docs/voz_jerry_despierta.py", encoding="utf-8").read(), g)
