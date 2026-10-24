---
name: two-flows-manual-and-ai
description: "User's rule that the manual flow and the AI flow must stay separate and parallel; AI output goes to animaciones_ia/, never bottlenecked by the guion"
metadata:
  node_type: memory
  type: feedback
  originSessionId: d2f4617a-366f-4f3f-a0af-d11850027bd4
  modified: 2026-09-29T10:38:39.701Z
---

There are TWO independent flows: MANUAL (user, panels, guion .json in `configuraciones/`, editable recipe) and IA (AI, result saved in `refinar/animaciones_ia/<nombre>/` as .animacion.json + standalone .py + manifest.json via `ai_export.exportar`). Other AIs will get animation tasks like this too and run in parallel.

**Why:** the user said the guion .json is for the manual flow; if it is a bottleneck for the AI, the AI needs its own output that stores the whole animation as data + code. It must be clear there are two flows.
**How to apply:** for animation tasks use the IA flow; never overwrite the user's guiones or another AI's folder; unique `<nombre>` per task (tracks `IA_<nombre>__*`); shared `poses/` is append-only with `ia_<nombre>_` prefix; do not modify existing add-on code unless the user says so (the user did authorize the PARADA loader fix); document in `GUIA_ANIMACION_ALFRED.md` and `FLUJOS_MANUAL_E_IA.md`. All Alfred documentation lives in ONE folder, `refinar/docs/` (user's instruction 2026-09-29): put new docs/guides there, not loose in `refinar/`.
Related: [[ai-api-and-chase-animation]]
