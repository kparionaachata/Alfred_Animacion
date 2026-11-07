import bpy
from mathutils import Vector
sc=bpy.context.scene; al=bpy.data.objects["Armature"]; pb=al.pose.bones; pala=bpy.data.objects["stone_shovel"]
A,B=Vector((-0.31,-0.44,0)),Vector((0.36,0.29,0))
PAL={"Rightelbow_alfred":(Vector((0.032,0.326,-0.008)),0.16),"Leftelbow_alfred":(Vector((-0.033,0.312,-0.005)),0.46)}
r={}
for f in range(1,113,3):
    sc.frame_set(f); M=pala.matrix_world
    e=[]
    for bn,(pl,t) in PAL.items():
        sh=al.matrix_world@pb[bn.replace("elbow","UpArm")].head
        obj=M@A.lerp(B,t); p=(al.matrix_world@pb[bn].matrix)@pl
        e.append((round((obj-p).length*100), round((obj-sh).length*100)))
    r[f]=e
result=r
