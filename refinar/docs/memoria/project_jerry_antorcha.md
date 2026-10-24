---
name: jerry-torch-jump-animation
description: Jerry (dog) chase animation built via the AI flow on the same scene as Alfred; where things live and gotchas
metadata:
  node_type: memory
  type: project
  originSessionId: d930d14a-d5ee-4666-8fac-0136f635075d
  modified: 2026-09-29T12:05:21.226Z
---

2026-09-29: built Jerry's part of the chase (runs ahead of Alfred with a torch parented to jaw_bot, throws it to his left/+x at y=-115.5, jumps into the water at x=-112.5). Output: `generador de animaciones/jerry/refinar/animaciones_ia/jerry_antorcha_salto_agua/`; route JSON in `jerry/refinar/configuraciones/jerry_ia_ruta_antorcha_salto.json`. Unapproved. Torch source is `bloques_dinamicos/antorcha_1.blend` (user pointed to it).

**Why:** same story as Alfred's chase; Jerry jumps first.
**How to apply:** Jerry uses the ported toolkit (`jerrypr.*`, `scene.jerry_path`, `Dog_001_rig`, root Empty `jerry`, 43 bones, head yaw = scull_1 Z (corrected 2026-10-01; pitch X, roll Y), jaw opens with jaw_bot X negative). `jerrypr.preview_path` overwrites scene.jerry_path and the scene frame range: snapshot/restore the user's manual Jerry path first. `ai_export` takes `personaje=JERRY` (+ `extras`). In the scene Dog_001_rig has scale 1.0 while jerry.blend has 1.3 (baked object transform handles it). Stop playback before screenshots; `get_screenshot_of_area_as_image` works only when the Blender window is at its current size.
Related: [[ai-api-and-chase-animation]], [[two-flows-manual-and-ai]]
