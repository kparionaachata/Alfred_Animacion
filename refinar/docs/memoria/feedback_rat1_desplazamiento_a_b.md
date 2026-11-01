---
name: rat1-desplazamiento-a-b
description: Skill rat1-desplazamiento-a-b - mover a rat_1 de A a B siempre con caminar/saltar subir/saltar bajar del rat_1_animation_studio segun dz
metadata:
  type: feedback
---

El usuario (30 oct) pidio la misma skill de desplazamiento A→B para rat_1 (`generador de animaciones/rat_1/refinar/rat_1_animation_studio`). Creada en `.claude/skills/rat1-desplazamiento-a-b/` y `~/.claude/skills/`, zip en la raiz y linea en CLAUDE.md. Ver [[feedback_alfred_desplazamiento_a_b]] y [[feedback_jerry_desplazamiento_a_b]].

**Why:** evitar caminatas/saltos inventados.

**How to apply:** Z a 2 decimales; saltos de duracion fija (18 subir / 20 bajar); sin saltar_horizontal; rig `rat_1` + `body1_1`. Quirk: speed_mult del generador esta invertido respecto a la estimacion de path_recorder. Firmas leidas del codigo, no probadas en Blender.

**Medido 30 oct (escena base_tarde con las ranas):** escala del empty rat_1 = 0.6 en la pelicula (base 1.0, sin confirmar) (malla 0.44x2.05x0.45 sin escalar); pasos de 1 bloque (ver [[reference_sistema_recorrido]]); `rat_1/refinar/estructura/` es copia de Alfred, no sirve de referencia. Tras el golpe termino con rot (884,379,632) y hundida 0.5 m: al aterrizar rot X/Y en multiplo de 360 y base sobre el suelo. Medir antes de preguntar al usuario.
