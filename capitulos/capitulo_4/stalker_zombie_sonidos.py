# -*- coding: utf-8 -*-
"""alfred_cueva_5B.blend: sonidos de la escena en que the_stalker_1 levanta al zombie y lo parte en dos (ver stalker_parte_zombie.py, frames 428-545).
Tiras de sonido del editor de secuencias (canales 100-109), etiqueta mcsnd_origen = "stalker_zombie". Repetible: borra las suyas antes de crear.
Uso en Blender: exec(open(ruta, encoding="utf8").read()); sonorizar()
"""
import bpy

BASE = "C:/Users/user/Desktop/Alfred_Animacion/sonidos/sounds/"
MAN = "C:/Users/user/Desktop/Alfred_Animacion/sonidos/The Man From The Fog/"      # sonidos propios de the_stalker_1
ORIGEN = "stalker_zombie"
# (frame, archivo, volumen, canal): el zombie NO emite voz (solo suena al romperse), el Stalker suena a la mitad de volumen, crujido al partirlo y caida de las mitades
SONIDOS = [
    (470, "@look-version-1.ogg", 0.45, 103),
    (487, "mob/zombie/woodbreak.ogg", 0.5, 104),
    (489, "damage/hit2.ogg", 0.5, 105),
    (491, "random/break.ogg", 0.45, 106),
    (493, "@jumpscare.ogg", 0.056, 103),
    (498, "@screams-version-2.ogg", 0.15, 103),
    (506, "@short_whisper_1.ogg", 0.25, 103),
    (495, "damage/hit3.ogg", 0.4, 107),
    (505, "damage/fallbig.ogg", 0.9, 104),
    (509, "damage/fallsmall.ogg", 0.9, 105),
    (514, "damage/hit1.ogg", 0.6, 106),
]


def sonorizar():
    sc = bpy.context.scene
    ed = sc.sequence_editor or sc.sequence_editor_create()
    for s in list(ed.strips_all):
        if s.get("mcsnd_origen") == ORIGEN:
            ed.strips.remove(s)
    n = 0
    for fr, arch, vol, canal in SONIDOS:
        s = ed.strips.new_sound("SND_%s_%d" % (arch.split("/")[-1][:-4], fr), (MAN + arch[1:] if arch.startswith("@") else BASE + arch), 100 + n, fr)
        c = 100
        while any(o is not s and o.channel == c and o.frame_final_start < s.frame_final_end and o.frame_final_end > s.frame_final_start for o in ed.strips_all):
            c += 1
        s.channel = c
        s.volume = vol
        s["mcsnd_origen"] = ORIGEN
        n += 1
    return n
