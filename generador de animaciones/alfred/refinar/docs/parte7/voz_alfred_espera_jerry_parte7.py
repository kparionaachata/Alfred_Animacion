# -*- coding: utf-8 -*-
"""Parte 7: voz de Alfred "¡Espera, Jerry, espera, espera, espera!" (emocion: cansancio, de la app `estudio_audio_expresion`) mientras CORRE, antes de torcerse el tobillo (f182).
Audio `audios/alfred/alfred_espera_jerry.mp3` (1.824 s = 44 f, pico 0.622, -20.3 dB RMS; voz en los frames 3-38 del clip) y su animacion de ojos `alfred_espera_jerry.cara_original.py` (script de la app, NO se ejecuta: se leen sus constantes con `ast`).
Usa `acciones/voz_alfred_que_paso.py` (generico) con START = 135: la voz suena en f137-172 (tira `VozAlfred_espera_jerry_1_138`, canal 1, f136-174), Alfred aparece corriendo en f131 y se tuerce el tobillo en f182. VOL = 1.5 (pico 0.93 sin recortar).
Los sonidos de la animacion que se solapan con la voz bajan (ducking, ver `ducking_voces.py`). Despues hay que ejecutar `filtros_organicos_y_parpadeos_parte7.py` otra vez (el script de la voz limpia las claves de los ojos en f135-179 y el parpadeo al azar
de Alfred se salta f135-182). Se ejecuta DENTRO de Blender: exec(open(RUTA, encoding='utf-8').read())."""
g = {"__name__": "x", "START": 135, "TAG": "espera_jerry", "ARCHIVO": "alfred_espera_jerry", "VOL": 1.5}
exec(open(r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/voz_alfred_que_paso.py", encoding="utf-8").read(), g)
