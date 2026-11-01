---
name: alfred-desplazamiento-a-b
description: Alfred de A a B: Z igual=caminar, Z+=saltar subir, Z-=saltar bajar, siempre con las animaciones del alfred_animation_studio; skill creada
metadata:
  type: feedback
---

El usuario (30 oct) pidio que SIEMPRE que se desplace a Alfred de A a B se usen las animaciones preestablecidas del estudio (`generador de animaciones/alfred/refinar/alfred_animation_studio`): caminar (dz=0), saltar_subir (dz>0), saltar_bajar (dz<0). Skill `alfred-desplazamiento-a-b` en el proyecto, en ~/.claude/skills y como zip en la raiz del proyecto.

**Why:** consistencia con su sistema 1 de recorrido.

**How to apply:** clasificar cada tramo por round(z,2); no inventar caminatas/saltos. Defectos fisicos conocidos del estudio (ver skill) se corrigen solo si el usuario lo pide. Relacionado: [[inercia-accion-reaccion]].
