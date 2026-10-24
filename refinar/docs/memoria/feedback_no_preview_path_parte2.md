---
name: no-preview-path-in-part2-scene
description: In base_parte_2.blend never run alfredpr/jerrypr preview_path or ai_api.guion_aplicar: they re-import and rename the characters
metadata:
  type: feedback
---

Running `bpy.ops.alfredpr.preview_path()`, `bpy.ops.jerrypr.preview_path()` or `ai_api.guion_aplicar(...)` in the part-2 scene (`capitulos/capitulo_4/base_parte_2.blend`) re-imports the character from its `.blend` when it cannot find the objects by their original names, duplicating and renaming objects (Alfred root `alfred`->`Object`, armature `Armature`->`a`; once the Dog rig became `alfred` with `alfred.001/.002`, `Object.001`). The session had to be backed up and `base_parte_2.blend` reloaded (2026-10-01).

**Why:** the add-ons assume the original object names; the scene was edited so they no longer match.
**How to apply:** build animations as artifacts (`compose_parte2.py`, `ai_export`) and import with `root_name="Object", armature_name="a"` for Alfred; if a new climbing/walk route is needed, extend it in the compose scripts (polyline + cycle rows from `parte2_*_tramo_tierra`) instead of regenerating with `preview_path`. Back up before touching add-on operators.
Related: [[parte-2-base-frame-860]]
