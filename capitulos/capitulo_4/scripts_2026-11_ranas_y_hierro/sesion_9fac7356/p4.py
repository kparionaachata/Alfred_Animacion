import bpy
sc=bpy.context.scene; al=bpy.data.objects["Armature"]; pb=al.pose.bones
r={}
for f in (840,880,950):
    sc.frame_set(f); r[f]=[round(x,2) for x in (al.matrix_world@pb["Hips_alfred"].head)]+[round(x,2) for x in (al.matrix_world@pb["face_alfred"].head)]
r["end"]=sc.frame_end
result=r
