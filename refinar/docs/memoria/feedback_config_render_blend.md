---
name: feedback-config-render-blend
description: "Every .blend I create must use the user's render config - Cycles GPU OptiX (RTX 3050), DLSS Render Balanced, Upscale Quality, viewport 20 samples, DLSS denoise"
metadata:
  node_type: memory
  type: feedback
  originSessionId: a0ef4841-1971-466b-a45e-be1a82655bea
  modified: 2026-11-02T14:48:04.474Z
---

Every .blend I make or save must use this render setup (the user asked on 2026-11-02, with a screenshot):
- Engine Cycles, Device GPU Compute. OptiX with only the RTX 3050 is set in the user preferences; the T400 and the CPU are off.
- DLSS Render add-on (Armin5D, `bl_ext.user_default.dlss_render`): `scene.dlss_render.quality='BALANCED'`, `cycles.preview_denoising_upscale_quality='QUALITY'`.
- Viewport: `preview_samples=20`, `preview_adaptive_min_samples=0`, `preview_adaptive_threshold=0.1`, `use_preview_denoising=True`, `preview_denoiser='DLSS'`.
- Display backend is Vulkan, which is a preference and is not stored in the .blend.

**Why:** the user's machine renders through DLSS on the RTX 3050.

**How to apply:** run headless WITHOUT `--factory-startup`, so the DLSS add-on and its property load. Call `config_render.aplicar()` from `capitulos/delgada_linea_roja/terreno/blender/config_render.py`, or run that file with `-P` to save. Quick preview renders made with Eevee for checking are fine, as long as the saved file keeps this config.
