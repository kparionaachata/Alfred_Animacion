---
name: project-stalker-tunel
description: The Stalker (the_stalker_1) tunnel crawl in alfred_cueva_5.blend: script, grip schedule, constraints
metadata:
  type: project
---

`capitulos/capitulo_4/stalker_tunel_gatear.py` (`aplicar()`) rewrites the 14 body bones + empty Y path (frames 1-261): crouched, long arms grabbing walls (f1-80), left arm floor (80-145), right arm ceiling (145-210), asymmetric legs/periods, lower jaw `neck_front_1` follows the head, face light `stalker_luz_cara` linked only to `stalker_receptores`. Backups: actions `*.respaldo_caminar`. Speed changed to ~1.4 m/s from frame 1 (was 3 m/s from 85).

**Why:** user wants face/teeth/chest visible, 1x3 creature in a 1x2 tunnel, non-symmetric limbs. **How to apply:** re-run `aplicar(False)` after parameter edits; arm reach 2.1 m, min fold 0.78; legs go out of reach ~20 frames each; ceiling grab forearm crosses face in frontal view.
