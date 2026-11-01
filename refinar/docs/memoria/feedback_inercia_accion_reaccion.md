---
name: inercia-accion-reaccion
description: Toda animacion debe cumplir inercia, accion-reaccion y gravedad real; skill inercia-accion-reaccion instalada
metadata:
  type: feedback
---

El usuario (30 oct) reprocho que olvidaba inercia y accion-reaccion en objetos lanzados a Alfred. Skill `inercia-accion-reaccion` creada en el proyecto (.claude/skills) y en la carpeta global de usuario (~/.claude/skills).

**Why:** los objetos caian rectos y Alfred reaccionaba tarde y con poses estaticas.

**How to apply:** en cualquier animacion con objetos que se lanzan/golpean/caen: gravedad real, inercia tras el choque, reaccion en el frame exacto del impacto proporcional a masa x velocidad, con rebote elastico. Usar bonobos_madera_fisica.py (vuelo) y reaccion() de bonobos_madera_alfred.py. Ver [[project_video_bonobos_tala]].
