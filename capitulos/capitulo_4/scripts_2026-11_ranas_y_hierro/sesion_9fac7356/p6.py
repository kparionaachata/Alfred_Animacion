import bpy
s=next(s for s in bpy.context.scene.sequence_editor.strips_all if s.name.startswith("SND_pollos_desesp"))
result={"a":[a for a in dir(s) if not a.startswith("_") and any(k in a.lower() for k in ("pitch","speed","tone","modifier","retim"))]}
