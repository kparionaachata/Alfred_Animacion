import bpy
sc=bpy.context.scene; al=bpy.data.objects["Armature"]; pb=al.pose.bones
r={}
for f in range(500,700,6):
    sc.frame_set(f); r[f]=[round(x,2) for x in (al.matrix_world@pb["face_alfred"].head)]
ed=sc.sequence_editor
r["sonidos_500_700"]=sorted([(s.frame_final_start,s.frame_final_end,s.name) for s in ed.strips_all if s.type=="SOUND" and 500<=s.frame_final_start<=700 and not s.name.startswith(("SND_cerdo","SND_pollo"))])[:40]
result=r
