# -*- coding: utf-8 -*-
"""Sonidos de la animacion de Jerry (jerry_despierta.py) en base_ranas_2.

Ronquidos (fox/sleep) mientras duerme, bostezo al estirarse, el sombrero que cae y rebota, olfateos,
la mordida al recogerlo, el lanzamiento y el sombrero al caerle en la cabeza, gemido curioso y ladrido
al ver la pelea, y PASOS en cada apoyo medido de las patas (pasto o grava segun la ruta).
Tiras `SND_jerry_*` con `mic_emisor` = "jerry". Repetible: borra las tiras SND_jerry_ anteriores.
Uso (exec en Blender): medir_contactos() por timer -> construir()
"""
import bpy, json, math
from mathutils import Vector

SND = "C:/Users/user/Desktop/Alfred_Animacion/sonidos/sounds/"
RUTA = "C:/Users/user/Desktop/jerry_recorrido.json"
ARM = "Dog_001_rig"
TOES = ["toe.L", "toe.R", "front_toe.L", "front_toe.R"]
TRAMOS_PASOS = [(176, 197), (280, 310), (360, 510)]          # levantarse/bajar, giro y caminata
VOL_PASO = 0.30

EVENTOS = [  # (frame, archivo, volumen, nombre)
    (100, "random/breath.ogg", 0.40, "bostezo"),
    (112, "step/cloth1.ogg", 0.30, "sombrero_resbala"),
    (124, "step/cloth2.ogg", 0.55, "sombrero_cae"),
    (129, "step/cloth3.ogg", 0.25, "sombrero_rebota"),
    (150, "mob/fox/sniff1.ogg", 0.40, "olfatea"),
    (170, "step/cloth4.ogg", 0.30, "se_levanta"),
    (202, "step/cloth1.ogg", 0.40, "impulso_salto"),
    (218, "step/grass1.ogg", 0.60, "aterriza"),
    (229, "mob/fox/sniff2.ogg", 0.40, "olfatea_sombrero"),
    (239, "mob/fox/bite1.ogg", 0.45, "muerde_sombrero"),
    (259, "entity/player/attack/sweep1.ogg", 0.30, "lanza_sombrero"),
    (268, "item/armor/equip_leather1.ogg", 0.60, "sombrero_puesto"),
    (316, "mob/fox/sniff3.ogg", 0.35, "olfatea_aire"),
    (512, "mob/fox/sniff4.ogg", 0.30, "olfatea_final"),
]
RONQUIDOS = (4, 92, ["mob/fox/sleep1.ogg", "mob/fox/sleep2.ogg", "mob/fox/sleep3.ogg", "mob/fox/sleep4.ogg", "mob/fox/sleep5.ogg"], 0.45)


def medir_contactos():
    """posiciones de las puntas de las 4 patas por frame (frame_set por timer) -> driver_namespace['contactos_jerry']"""
    fr = sorted({f for a, b in TRAMOS_PASOS for f in range(a - 1, b + 2)})
    st = {"cola": fr, "i": 0, "d": {}, "listo": False}
    bpy.app.driver_namespace["contactos_jerry"] = st

    def tick():
        sc = bpy.context.scene; arm = bpy.data.objects[ARM]
        for _ in range(40):
            if st["i"] >= len(st["cola"]):
                sc.frame_set(1); st["listo"] = True; return None
            f = st["cola"][st["i"]]; sc.frame_set(f); mw = arm.matrix_world
            st["d"][f] = [tuple(mw @ arm.pose.bones[b].tail) for b in TOES]; st["i"] += 1
        return 0.01
    bpy.app.timers.register(tick, first_interval=0.05)
    return st


def contactos(d):
    """apoyos: minimo local de la altura de cada pata, despues de haberla levantado >= 2.5 cm"""
    out = []
    for a, b in TRAMOS_PASOS:
        for k in range(4):
            alto = None
            for f in range(a, b + 1):
                if f - 1 not in d or f + 1 not in d: continue
                z0, z, z1 = d[f - 1][k][2], d[f][k][2], d[f + 1][k][2]
                alto = z if alto is None else max(alto, z)
                if z <= z0 and z < z1 and alto - z >= 0.025:
                    out.append((f, k, Vector(d[f][k]))); alto = z
    return sorted(out)


def textura(p, kp):
    if p.x > -8.0: return "grass"
    q = min(kp, key=lambda c: (c["coordinates"]["x"] - p.x) ** 2 + (c["coordinates"]["y"] - p.y) ** 2)
    return "gravel" if q["texture"] == "gravel" else "grass"


def construir():
    sc = bpy.context.scene; ed = sc.sequence_editor
    for s in [s for s in ed.strips_all if s.name.startswith("SND_jerry_")]: ed.strips.remove(s)
    ocupado = {}
    for s in ed.strips_all: ocupado.setdefault(s.channel, []).append((s.frame_final_start, s.frame_final_end))

    def poner(nombre, ruta, frame, vol):
        import aud
        a_ = aud.Sound(SND + ruta); dur = max(1, int(math.ceil(a_.length / a_.specs[0] * sc.render.fps))) + 1
        for ch in range(1, 129):
            if all(frame + dur <= a or frame >= b for a, b in ocupado.get(ch, [])):
                s = ed.strips.new_sound(name="SND_jerry_" + nombre, filepath=SND + ruta, channel=ch, frame_start=frame)
                s.volume = vol; s["mic_emisor"] = "jerry"
                ocupado.setdefault(ch, []).append((s.frame_final_start, s.frame_final_end)); return s
        raise RuntimeError("sin canal libre")

    n = 0
    f, (a, b, files, vol) = RONQUIDOS[0], RONQUIDOS
    i = 0
    while f < b:
        s = poner("ronquido_%d" % i, files[i % len(files)], f, vol); f = s.frame_final_end + 8; i += 1; n += 1
    for fr, ruta, vol, nombre in EVENTOS:
        poner(nombre, ruta, fr, vol); n += 1
    kp = json.load(open(RUTA, encoding="utf8"))["key_points"]
    st = bpy.app.driver_namespace["contactos_jerry"]
    pasos = contactos(st["d"]); cuenta = {"grass": 0, "gravel": 0}
    for j, (f, k, p) in enumerate(pasos):
        t = textura(p, kp); num = (j % 4) + 1 if t == "gravel" else (j % 6) + 1
        v = VOL_PASO * (0.75 if k >= 2 else 1.0)                               # delanteras algo mas suaves
        poner("paso_%s_%d" % (t, j), "step/%s%d.ogg" % (t, num), f, v); cuenta[t] += 1; n += 1
    return {"tiras": n, "pasos": len(pasos), "por_suelo": cuenta, "ronquidos": i}
