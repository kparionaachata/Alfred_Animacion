---
name: parte-5-base-frame-1236
description: "base_parte_5.blend = end state (f1236) of part 4 baked static as frame 1; how it was made, what was removed"
metadata:
  type: project
---

2026-10-07: `capitulos/capitulo_4/base_parte_5.blend` = frame 1236 of part 4 (Alfred just placed the torch, back in rest posture) as static frame 1, no animation. Built headless by `alfred/refinar/docs/parte5/crear_base_parte_5.py` from base_parte_4.blend (re-running the torch action via `docs/acciones/colocar_objeto.py`, because the live session's torch animation was unsaved). Same method as [[parte-2-base-frame-860]]: capture channel values at the frame, clear actions/NLA, write static values. Also removed all 151 VSE sound strips (belong to parts 1-4) and scene key `alfred_guion_v2`. Verified 310 objects / 250 bones identical to f1236. Scene range still 1-1236; 88 `ALFSEG_*` bank actions remain unassigned.

**Why:** the user starts part 5 from where the torch placement ended.
**How to apply:** animate part 5 from these static poses; new animations are delivered as portable guion JSONs per character (see [[parte-3-despejar-y-mesa]] notes / guides) and loaded into the scene. base_parte_4.blend on disk was NOT saved with the torch animation (it only exists as the guion `configuracion_portable_antorcha_3_f1160_1236.json` + `docs/acciones/colocar_objeto_exterior`).

Update 2026-10-07 (later): the user saved the live scene over `base_parte_5.blend` (04:57), so that file now holds the torch+lean animation (NLA); the clean static base is `capitulos/capitulo_4/base_parte_5_estatica.blend` (copy of base_parte_5.blend1, 03:29). Use the _estatica copy for headless portable exports/tests. Part-5 animations so far (portables in alfred/refinar/configuraciones/guiones): torch from f1 (f1-61), lean-to-look-outside (f61-112) with camera moving (-95.521,-108.955,14.847) -> (-95.985,-109.22,14.957) at f88-112; Alfred organic filters (reglas_alfred baseline) on by default in exportar_portable.py.
