import bpy
ed=bpy.context.scene.sequence_editor
result={"v":sorted([(s.frame_final_start,s.frame_final_end,s.name,s.channel,bpy.path.basename(s.sound.filepath)) for s in ed.strips_all if s.type=="SOUND" and ("alfred" in s.sound.filepath.lower() and "voces" in s.sound.filepath.lower() or s.name.startswith("Voz"))])}
