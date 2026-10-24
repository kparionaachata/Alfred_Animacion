---
name: zombies-chase-animation
description: "Zombies 1-5 chase (behind Jerry, arriving at the cliff); zombie_1 and zombie_2 done via AI flow, what remains and how"
metadata:
  node_type: memory
  type: project
  originSessionId: 375700f1-eee8-4888-9621-032f2838ad39
---

2026-09-29: user asked to animate zombie_1..zombie_5 (add-ons `zombie_N_animation_studio`, prefix `zombie_Npr`, `scene.zombie_N_path`, root `zombie_N`, armature `zombie_N_Armature`) chasing Jerry, arriving at Alfred's cliff late.

Done (unapproved): zombie_1 -> `zombie_1/refinar/animaciones_ia/zombie_1_camina_acantilado/` (1-860, walk, stop at ledge, fall like wet rag, rise, follow Alfred). zombie_2 -> `zombie_2/refinar/animaciones_ia/zombie_2_camina_acantilado/`, derived from zombie_1's artifact with own A* route (~1 m offset) and small gait variations; its 18 objects were appended from `estructura_lista/zombie_2.blend`. zombies 3-5 not done.

**Why:** story beat, Alfred sees zombies approaching the cliff.
**How to apply:** for zombie_3..5 repeat the zombie_2 recipe (derive from zombie_1 json, rename bones `_zombie_1`->`_zombie_N` except `Neck_zombie_1.001`, append blend objects, `ai_export.importar(..., personaje=ai_export.zombie(n))`). NEVER enable `zombie_N_animation_studio` add-ons: they are incompletely renamed copies that still register `ZMB1ST_*`/`scene.zmb1st` and break zombie_1 (recover by disable/enable zombie_1). Raycast must skip leaves/rain/logs.
Related: [[ai-api-and-chase-animation]], [[jerry-torch-jump-animation]]
