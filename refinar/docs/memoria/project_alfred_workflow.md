---
name: alfred-manual-workflow
description: "How the user actually works with Alfred Animation Studio (manual, AI-independent pipeline; JSON = saved per-character config/script)"
metadata:
  node_type: memory
  type: project
  originSessionId: d2f4617a-366f-4f3f-a0af-d11850027bd4
  modified: 2026-09-29T05:14:25.102Z
---

The user deliberately avoids depending on AI for the animation itself. Their pipeline:
1. Import Minecraft scenery with Mineways -> OBJ, split into surface objects.
2. Manually record the character path face-by-face/coordinate-by-coordinate with the path recorder (Steps 1-2).
3. Load the character. The ONLY AI-generated pieces are 4 base animations: caminar, parado, saltar_subir (1 block up), saltar_bajar (1 block down). With these, the path plays as a simple animation.
4. Step 3 (Segments): path is split into segments (walk/jump/stop). Each segment gets its own config: organic filters, blinks, emotions, pose sequences injected onto the base animation, and bone filters/locks (e.g. walking segment: leg bones locked so injected poses don't alter the base walk cycle but affect the rest of the body). "Concatenar segmentos" bakes it all.
5. The .json config is saved incrementally as progress and re-imported later; it is the per-character "script/guion" (recipe), not baked keyframes.

Reuse structure: the scenery (Mineways OBJ split into surfaces) is imported/split ONCE and serves many animations; the 4 base animations are created ONCE per character and reused across all animations. Only steps 2 (route), 4 (segments/config) and 5 (.json) repeat per animation, so each .json holds just that animation's decisions (route, poses, filters), not the scenery or base animations.

**Why:** manual control and no AI dependence for everything except the 3-4 base animations.
**How to apply:** treat generate_slots_alfred.py base movements as the AI-made part; suggestions should preserve manual control, per-segment config, and bone-lock filtering. Don't propose replacing manual steps with AI generation.
