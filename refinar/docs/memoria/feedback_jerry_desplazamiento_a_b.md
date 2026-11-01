---
name: jerry-desplazamiento-a-b
description: Skill jerry-desplazamiento-a-b - mover a Jerry de A a B siempre con caminar/saltar subir/saltar bajar del jerry_animation_studio segun dz
metadata:
  node_type: memory
  type: feedback
  originSessionId: 22c3d667-c653-48cb-ab35-244ae3a40749
  modified: 2026-10-30T06:34:46.673Z
---

El usuario (30 oct) pidio una skill para que Jerry, al desplazarse de A a B, use siempre las animaciones preestablecidas del `generador de animaciones/jerry/refinar/jerry_animation_studio` segun Z (igual=caminar, positivo=saltar subir, negativo=saltar bajar). Creada en `.claude/skills/jerry-desplazamiento-a-b/` y `~/.claude/skills/`, con zip en la raiz del proyecto y linea en CLAUDE.md.

**Why:** evitar que se inventen caminatas/saltos; mismo criterio que [[feedback_alfred_desplazamiento_a_b]].

**How to apply:** tolerancia de Z 4 decimales (Alfred 2); rig cuadrupedo `jerry`/`Dog_001_rig`. Las firmas de generate_* se leyeron del codigo, no se probaron en Blender.
