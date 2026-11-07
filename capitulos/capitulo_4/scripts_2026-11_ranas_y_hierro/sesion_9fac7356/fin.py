import bpy
sc=bpy.context.scene
ed=sc.sequence_editor
fuera=[s.name for s in ed.strips_all if s.frame_final_start>sc.frame_end]
result={"end":sc.frame_end,"strips_despues_del_fin":len(fuera)}
