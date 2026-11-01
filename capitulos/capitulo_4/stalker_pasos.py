# -*- coding: utf-8 -*-
"""alfred_cueva_5B.blend: pasos de the_stalker_1 mientras camina hacia el pico (stalker_camina_pico.py, f546-780).
El pie izquierdo (zancada larga) pisa fuerte con step/stone1-6 y el derecho (corto, arrastrado) con step/stone1-6 mas flojo (camina sobre piedra), en el frame en que cada muslo llega al maximo de su
balanceo hacia delante. El volumen baja con la distancia a la camara (que orbita de 2 a 7 m). Tiras de sonido con mcsnd_origen = "stalker_pasos".
Requiere haber ejecutado antes stalker_camina_pico.py (usa _fase, F0, F_END).
Uso: exec(stalker_parte_zombie.py); exec(stalker_camina_pico.py); exec(este); pasos()
"""
import bpy, math, random

BASE = "C:/Users/user/Desktop/Alfred_Animacion/sonidos/sounds/step/"
ORIGEN = "stalker_pasos"


def pasos(canal0=130):
    sc = bpy.context.scene
    ed = sc.sequence_editor or sc.sequence_editor_create()
    for s in list(ed.strips_all):
        if s.get("mcsnd_origen") == ORIGEN:
            ed.strips.remove(s)
    st, cam = bpy.data.objects["the_stalker_1"], sc.camera
    rnd = random.Random(9)
    eventos = []
    for fr in range(F0 + 1, F_END + 1):
        a, b = _fase(fr - 1), _fase(fr)
        ka0, ka1 = math.floor((a - math.pi / 2) / (2 * math.pi)), math.floor((b - math.pi / 2) / (2 * math.pi))
        if ka1 > ka0:                                   # izquierda: seno de la fase llega al maximo
            eventos.append((fr, "L"))
        kb0, kb1 = math.floor((a + 2.5 - math.pi / 2) / (2 * math.pi)), math.floor((b + 2.5 - math.pi / 2) / (2 * math.pi))
        if kb1 > kb0:                                   # derecha (desfasada 2.5 rad)
            eventos.append((fr, "R"))
    n = 0
    for fr, lado in eventos:
        sc.frame_set(fr)
        d = (cam.matrix_world.translation - st.matrix_world.translation).length
        atenua = min(1.0, 4.0 / max(d, 4.0)) ** 0.7
        if lado == "L":
            arch, vol = "stone%d.ogg" % rnd.randint(1, 6), 0.9
        else:
            arch, vol = "stone%d.ogg" % rnd.randint(1, 6), 0.5
        s = ed.strips.new_sound("SND_paso_%s_%d" % (lado, fr), BASE + arch, canal0, fr)
        c = canal0
        while any(o is not s and o.channel == c and o.frame_final_start < s.frame_final_end and o.frame_final_end > s.frame_final_start for o in ed.strips_all):
            c += 1
        s.channel = c
        s.volume = vol * atenua
        s["mcsnd_origen"] = ORIGEN
        n += 1
    sc.frame_set(F0)
    return n
