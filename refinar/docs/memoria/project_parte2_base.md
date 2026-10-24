---
name: parte-2-base-frame-860
description: "base_parte_2.blend = end state (frame 860) of part 1 baked as static frame 1, to start part 2; how it was made and what stays behind"
metadata:
  node_type: memory
  type: project
  originSessionId: 375700f1-eee8-4888-9621-032f2838ad39
  modified: 2026-09-30T08:16:09.259Z
---

2026-09-30: user needed part 2 of the animation to start from the pose/positions of frame 860 of part 1 (part 1 already saved in another .blend, e.g. `capitulo_4/base_ruta_M.blend`). Made `capitulos/capitulo_4/base_parte_2.blend` (save-as; `base.blend` untouched on disk): evaluated frame 860, removed ALL actions/NLA tracks (56 IDs: objects, shape keys, materials, cameras, lights) and wrote the 860 values as static (2155 channels). Verified frame 1 == frame 860 positions and bone sums; nothing animated remains. Scene range still 1-860.

**Why:** user starts part 2 from where part 1 ended (Alfred/Jerry swimming east, zombies 1-5 in the channel).
**How to apply:** in part 2, animate from these static poses; the add-on data (alfredpr path, alfredseg segments, jerry/zombie paths, `IA_*` artifacts) still describe part 1 — do not re-run old artifacts; record new paths from the current positions. Method is reusable: capture fcurve values at frame N via `id.path_resolve`, clear animation_data, re-set values.
Related: [[zombies-chase-animation]], [[two-flows-manual-and-ai]]

Update 2026-09-30 (same day): Part 2 first draft built in the open (unsaved) session of base_parte_2.blend, 540 frames: artifacts `parte2_alfred_nada_y_sube`, `parte2_jerry_nada_y_sube` (composed by `alfred/refinar/docs/parte2/compose_parte2.py` from part-1 swim cycles + base-motor land route), `parte2_zombie_N_sigue` (compose_zombies_parte2.py). Route per user's red arrow: keep swimming east, stop, look around, turn to the coast, climb the 1-wide stone stair at x=-91.5 (z 8..14) to the plateau z=14. Enable `jerry_animation_studio` (was not registered) for jerrypr; never zombie_2..5 add-ons. Camera for part 2 and stair-specific zombie climb not done.
