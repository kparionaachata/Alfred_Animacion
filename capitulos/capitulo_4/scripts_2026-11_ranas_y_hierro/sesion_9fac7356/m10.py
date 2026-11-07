import bpy
from mathutils import Vector
sc=bpy.context.scene; al=bpy.data.objects["Armature"]; pb=al.pose.bones; pala=bpy.data.objects["stone_shovel"]
A,B=Vector((-0.31,-0.44,0)),Vector((0.36,0.29,0))
L={}
for bn in ("Rightelbow_alfred","Leftelbow_alfred"):
    up=pb[bn.replace("elbow","UpArm")]
    L[bn]=round(up.length*1,3)
r={"long_brazo":{k:v for k,v in L.items()},"long_antebrazo_palma":{"R":0.326,"L":0.312}}
for f in (17,20,24,28,36,40,44,95):
    sc.frame_set(f); M=pala.matrix_world; row=[]
    for bn,t in (("Rightelbow_alfred",0.08),("Leftelbow_alfred",0.45)):
        sh=al.matrix_world@pb[bn.replace("elbow","UpArm")].head
        row.append(round((M@A.lerp(B,t)-sh).length*100))
    r[f]=row
result=r
