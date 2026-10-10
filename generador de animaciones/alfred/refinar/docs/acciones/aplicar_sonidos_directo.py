# -*- coding: utf-8 -*-
"""APLICAR LOS SONIDOS DE UN PORTABLE COMO TIRAS DEL VSE, SIN ESTUDIO (zombie_1..5): lee `sonidos.manuales` de cada guion portable y crea / mueve las tiras `SND_<etiqueta>_<frame>` (propiedades mcsnd, mcsnd_ev y guion_id = id del sonido).
Dentro de Blender:  PORTABLES = [r"...\\configuracion_portable_zombie_2_rodea_refugio_f1_292.json", ...]; exec(open(r"...\\aplicar_sonidos_directo.py", encoding="utf-8").read(), {"__name__": "x", "PORTABLES": PORTABLES})
Repetible: si ya existe una tira con ese guion_id la mueve y le pone el volumen; quita las tiras de ese personaje que ya no estan en el guion. No toca las tiras de Alfred ni de otros personajes. No guarda el .blend."""
import json
import os

import bpy

RAIZ = r"C:\Users\user\Desktop\Alfred_Animacion"; sc = bpy.context.scene; ed = sc.sequence_editor or sc.sequence_editor_create(); strips = ed.strips_all if hasattr(ed, "strips_all") else ed.sequences_all; res = []
for cfg in globals()["PORTABLES"]:
    C = json.load(open(cfg, encoding="utf-8")); pers = C["meta"]["personaje"].lower(); man = (C.get("sonidos") or {}).get("manuales") or []; ids = {m["id"] for m in man}
    existentes = {s.get("guion_id"): s for s in strips if s.type == 'SOUND' and str(s.get("guion_id", "")).startswith("snd5_" + pers)}
    for gid, s in list(existentes.items()):
        if gid not in ids: ed.strips.remove(s)
    n = 0
    for m in man:
        ruta = os.path.normpath(os.path.join(RAIZ, "sonidos", "sounds", m["archivo"])); f = int(m["t"]); nombre = "SND_%s_%d" % (m["etiqueta"], f); s = existentes.get(m["id"])
        if s is None: s = ed.strips.new_sound(nombre, ruta, int(m.get("canal", 22)), f); n += 1
        else:
            s.name = nombre; s.frame_start = f
        s.volume = float(m.get("volumen", 1.0)); s["vol_base"] = s.volume; s.pan = float(m.get("pan", 0.0)); s["mcsnd"] = m.get("grupo", "objetos"); s["mcsnd_ev"] = m["etiqueta"]; s["guion_id"] = m["id"]
    res.append((pers, len(man), n))
exec(open(os.path.join(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones", "ducking_voces.py"), encoding="utf-8").read(), {"__name__": "x"})                       # las voces de los personajes mandan sobre los sonidos del juego
print("SONIDOS aplicados (personaje, total, nuevos):", res)
