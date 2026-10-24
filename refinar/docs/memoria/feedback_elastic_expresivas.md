---
name: elastic-in-out-expressive-transitions
description: "User rule: expressive transitions (scares, laughs, hits...) must use ELASTIC IN-OUT interpolation"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 375700f1-eee8-4888-9621-032f2838ad39
  modified: 2026-10-01T03:18:39.670Z
---

For expressive transitions in the animations (sustos/scares, risas/laughs, golpes/hits and similar reactions) use **Elastic In-Out** easing (Blender's "Elastic In-Out"; the add-on's `ELASTIC_IN_OUT` in `interpolation.py`), not smoothstep/linear. Said by the user on 2026-09-30 with a screenshot of Blender's interpolation menu.

**Why:** gives the snappy overshoot/oscillation that reads as a reaction instead of a smooth blend.
**How to apply:** pose transitions in manual segments: `interp_type="ELASTIC_IN_OUT"` for the pose you arrive at. In AI-composed JSON (compose scripts): use `ela()/epulse()` from `alfred/refinar/docs/parte2/compose_parte2.py` (same formula) for the onset/offset of the reaction; keep plain smoothstep for calm moves (walking, breathing, rest). Do not use it where a bone must land exactly at 0 (it overshoots). Already applied to Alfred's and Jerry's fright in part 2 (frames ~490-526).
Related: [[parte-2-base-frame-860]]

**Update 2026-10-03:** the user repeated the rule (same menu screenshot) for "los movimientos de Alfred": applied in the Alfred Voz Sync add-on (v1.4, `elastico_alfred`) to Alfred's nods, emotion entry/exit/cross-fades and facial phases; calm sways/breathing stay smooth; Jerry unchanged.
