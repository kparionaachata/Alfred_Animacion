import bpy
sc=bpy.context.scene; al=bpy.data.objects["Armature"]; pb=al.pose.bones
r={}
eye=bpy.data.objects["ojo_derecho_alfred"].data.shape_keys.key_blocks
for f in (600,610,640,680,700,706,720,760,780,800,885,900,960,990):
    sc.frame_set(f); r[f]=(round((al.matrix_world@pb["face_alfred"].head).z,2), round(eye["Closed"].value,2), round(eye["Dolor"].value,2))
ed=sc.sequence_editor
r["snd"]=sorted([(s.frame_final_start,s.name) for s in ed.strips_all if s.type=="SOUND" and 600<=s.frame_final_start<=800 and not s.name.startswith(("SND_cerdo","SND_pollo"))])[:20]
result=r
