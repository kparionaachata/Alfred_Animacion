# -*- coding: utf-8 -*-
"""Parte 7: voz de Jerry "Y ahora, que miralo descansando." (emocion: enojo, de la app `estudio_audio_expresion`) a partir del frame 274 (el frame 1 del clip = f274), cuando termina de volver corriendo y se sienta mirando a Alfred.
Audio `audios/jerry/jerry_y_ahora_descansando.wav` (4.02 s = 97 f, pico 0.487, -25.9 dB RMS; voz en los frames 2-11, 37-43 y 67-94 del clip) y su animacion `jerry_y_ahora_descansando.cara_original.py` (script de la app, NO se ejecuta: se leen sus constantes con `ast`).
Usa `voz_jerry_despierta.py` (generico): START = 274, TAG = "y_ahora", VOL = 1.91 (pico 0.93 sin recortar). Tres tiras (una por tramo de voz): `VozJerry_y_ahora_1_276` f274-288, `_2_309` f307-319 y `_3_340` f338-370. La expresion se SUMA a lo que Jerry ya anima y NO se debe repetir sobre el mismo rango.
Se ejecuta DENTRO de Blender: exec(open(RUTA, encoding='utf-8').read())."""
g = {"__name__": "x", "START": 274, "TAG": "y_ahora", "ARCHIVO": "jerry_y_ahora_descansando", "VOL": 1.91}
exec(open(r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/jerry/refinar/docs/voz_jerry_despierta.py", encoding="utf-8").read(), g)
