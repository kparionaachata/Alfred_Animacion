---
name: ai-api-and-chase-animation
description: State of the AI-assisted layer (ai_api.py) and the first AI-built animation (zombie chase -> water) in Alfred Animation Studio
metadata:
  node_type: memory
  type: project
  originSessionId: d2f4617a-366f-4f3f-a0af-d11850027bd4
  modified: 2026-09-29T09:50:17.735Z
---

From 2026-09-29 the user wants AI added to the Alfred workflow (previously deliberately manual) to speed up animation creation, WITHOUT replacing existing code. The AI's only write surface is the .json "guion" (config) plus pose .json files; Blender runs the existing engine.

- Added `refinar/alfred_animation_studio/ai_api.py` (additive, imported on demand; no changes to existing modules). Installed copy lives in `%APPDATA%\Blender Foundation\Blender\5.2\scripts\addons\alfred_animation_studio\` and must be re-copied after edits (or re-run the .bat).
- First AI-built animation: `refinar/configuraciones/mi_configuracion_ia_persecucion.json` (chase -> stop -> theatrical jump -> land face-down on stone -> roll into water -> waist-deep -> look up at cliff). Only Alfred; zombies out of scope. 27 `ia_*` poses in `refinar/poses/`. Scene backup in `capitulos/capitulo_4/respaldos_ia/`.
- Status: baked in the live scene but NOT approved by the user; they review visually in Blender.
- The file `GUIA_ANIMACION_ALFRED.md` is the living guide for other AIs; add an entry after each animation.

**Why:** the user wants faster creation while keeping the guion as the single source of truth.
**How to apply:** build on ai_api.py; keep changes additive; write to a NEW guion file instead of overwriting the user's; never mark an animation as approved without their confirmation; stop playback before capturing frames (concatenate_all starts it).

Gotchas found: Blender 5.2 loader drops PARADA on config import (enum_items empty; ai_api.guion_aplicar works around it, existing code not modified); importing a config auto-runs CONCATENAR_2 (eyes); pose `root` values are ABSOLUTE world transforms; segments start exactly on their first pose.
