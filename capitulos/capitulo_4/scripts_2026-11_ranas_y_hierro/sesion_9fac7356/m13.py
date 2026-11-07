import bpy, math
sc=bpy.context.scene; al=bpy.data.objects["Armature"]; pb=al.pose.bones
r={}
for f in (36,62,88):
    sc.frame_set(f)
    r[f]={b:[round(math.degrees(x),1) for x in pb[b].rotation_euler] for b in ("Spine1_alfred","Spine2_alfred","RightUpArm_alfred","Rightelbow_alfred")}
result=r
