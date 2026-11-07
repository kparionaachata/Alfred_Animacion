import bpy
sc=bpy.context.scene; al=bpy.data.objects["Armature"]; pb=al.pose.bones
names=[b.name for b in pb]
want=[n for n in names if any(k in n for k in ("Hips","Spine2","Neck","face","Head","LeftUpLeg","RightUpLeg","LeftLeg","RightLeg","LeftFoot","RightFoot","LeftArm","RightArm","LeftForeArm","RightForeArm","Rightelbow","Leftelbow","Rightknee","Leftknee"))]
r={"bones":names}
for f in (795,800,840):
    sc.frame_set(f)
    r[f]={n:[round(x,2) for x in (al.matrix_world@pb[n].head)] for n in want}
ch=bpy.data.objects["chicken_1"]
r["pollo"]={f:(sc.frame_set(f) or [round(x,2) for x in ch.matrix_world.translation]) for f in (700,740,760,780,800,837)}
result=r
