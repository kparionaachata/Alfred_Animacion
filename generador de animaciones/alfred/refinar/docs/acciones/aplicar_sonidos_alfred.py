# -*- coding: utf-8 -*-
"""APLICAR SOLO LOS SONIDOS DE ALFRED (segundos): une los `sonidos.manuales` de los portables de `secuencia_parte5.json` y los pone como tiras `SND_<etiqueta>_<frame>` con el modulo `sonidos_guion` del Alfred Studio (mueve/crea/quita las suyas; no toca las de zombies ni las voces).
Dentro de Blender:  exec(open(r"...\aplicar_sonidos_alfred.py", encoding="utf-8").read(), {"__name__": "x"})  (luego corre el ducking). No concatena ni toca poses."""
import json
import os
import sys

import bpy

REF = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"; G = os.path.join(REF, "configuraciones", "guiones")
S = json.load(open(os.path.join(REF, "docs", "acciones", "secuencia_parte5.json"), encoding="utf-8")); man = []
def frame_de(t, anclas):
    """un frame o una ancla de ese guion: 'nombre', 'nombre+N', 'nombre-N'."""
    if isinstance(t, (int, float)): return int(t)
    base, off = t, 0
    for sg_ in ("+", "-"):
        if sg_ in t[1:]: base, o = t.rsplit(sg_, 1); off = int(o) * (1 if sg_ == "+" else -1); break
    return int(anclas[base]) + off


for f in S["guiones"]:
    C_ = json.load(open(os.path.join(G, f), encoding="utf-8")); an = C_.get("anclas") or {}
    man += [dict(m, t=frame_de(m["t"], an)) for m in (C_.get("sonidos") or {}).get("manuales") or []]
sg = sys.modules["alfred_animation_studio.sonidos_guion"]
r = sg.aplicar_sonidos(bpy.context, {"version": "2.0", "sonidos": {"modo": "manual", "techo_voces": False, "manuales": man}})
ed_ = bpy.context.scene.sequence_editor; por_id_ = {x.get("guion_id"): x for x in ed_.strips_all if x.type == 'SOUND'}
for m in man:                                                                                    # el volumen base de cada tira = el del guion (el ducking parte de ahi; si la tira tenia claves de volumen, el ducking las rehace)
    x = por_id_.get(m.get("id"))
    if x is not None: x["vol_base"] = float(m["volumen"]); x.volume = float(m["volumen"])
print("SONIDOS DE ALFRED:", len(man), "en la secuencia ->", r)
exec(open(os.path.join(REF, "docs", "acciones", "ducking_voces.py"), encoding="utf-8").read(), {"__name__": "x"})
