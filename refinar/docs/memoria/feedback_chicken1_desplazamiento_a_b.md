---
name: chicken1-desplazamiento-a-b
description: Skill chicken1-desplazamiento-a-b - mover a chicken_1 de A a B solo con las animaciones base capturadas del chicken_1_animation_studio
metadata:
  node_type: memory
  type: feedback
  originSessionId: 22c3d667-c653-48cb-ab35-244ae3a40749
  modified: 2026-10-30T08:45:13.164Z
---

El usuario (30 oct) pidio la skill de desplazamiento A→B para chicken_1 (`generador de animaciones/chicken_1/refinar/chicken_1_animation_studio`): sus animaciones base por defecto deben usarse siempre, para que la IA no invente caminar/saltar nuevos. Creada en `.claude/skills/chicken1-desplazamiento-a-b/` y `~/.claude/skills/`, zip en la raiz, linea en CLAUDE.md. Ver [[feedback_alfred_desplazamiento_a_b]], [[feedback_jerry_desplazamiento_a_b]], [[feedback_rat1_desplazamiento_a_b]].

**Why:** evitar animaciones inventadas; las del pollo son keyframes capturados (no procedurales).

**How to apply:** Z cruda con EPSILON 1e-3; caminar = 40 f por par de puntos (velocidad depende de la separacion, ~1 m entre puntos); subir 40 f, bajar 33 f, saltar de 3 puntos 33 f; estilos NORMAL/LENTO/RAPIDO/PERSEGUIDO (HERIDO/CORRER no existen). Firmas leidas del codigo, no probadas en Blender.

**Medido 30 oct (escena base_tarde con las ranas):** escala correcta del empty chicken_1 = 1.0 (el 0.7 de la pelicula era error, corregido el 30 oct); pasos de 1 bloque (ver [[reference_sistema_recorrido]]); chicken_1.json de estructura trae escala 0.1, no es la de la escena. Tras el golpe termino con rot (867,371,619) y hundido 0.54 m: al aterrizar rot X/Y en multiplo de 360 y base sobre el suelo. Medir antes de preguntar al usuario.
