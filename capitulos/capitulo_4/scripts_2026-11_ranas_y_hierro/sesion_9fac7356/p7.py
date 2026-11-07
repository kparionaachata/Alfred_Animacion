import bpy
ed=bpy.context.scene.sequence_editor
s=[x for x in ed.strips_all if x.name.startswith("SND_pollos_desesp")]
result={"n":len(s),"ok":all(x.sound and x.frame_final_end>x.frame_final_start for x in s),"ej":bpy.path.basename(s[0].sound.filepath)}
