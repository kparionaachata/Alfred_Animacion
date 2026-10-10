# -*- coding: utf-8 -*-
"""Parte 7: voz de Alfred "¡Ah la p... madre, mi tobillo, mi tobillo, mi tobillo! ¡Ah, mi tobillo!" (emocion: tristeza, de la app `estudio_audio_expresion`) JUSTO DESPUES de caer de cara al suelo (aterriza en f186).
Audio `audios/alfred/alfred_quejido_caida.mp3` (4.8 s = 116 f, pico 0.79, -22.3 dB RMS; voz en los frames 6-109 del clip) y su animacion de ojos `alfred_quejido_caida.cara_original.py` (script de la app, NO se ejecuta: se leen sus constantes con `ast`).
Usa `acciones/voz_alfred_que_paso.py` (generico) con START = 182: la voz suena en f187-290 (tira `VozAlfred_quejido_caida_1_187`, canal 1, f185-293), o sea desde el frame siguiente al aterrizaje, durante los rebotes, el giro y el sobarse. VOL = 1.18 (pico 0.93 sin recortar).
Despues hay que ejecutar `filtros_organicos_y_parpadeos_parte7.py` otra vez (el script de la voz limpia las claves de los ojos en f182-298; el parpadeo al azar de Alfred se salta f135-300). Se ejecuta DENTRO de Blender: exec(open(RUTA, encoding='utf-8').read())."""
g = {"__name__": "x", "START": 182, "TAG": "quejido_caida", "ARCHIVO": "alfred_quejido_caida", "VOL": 1.18}
exec(open(r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/voz_alfred_que_paso.py", encoding="utf-8").read(), g)
