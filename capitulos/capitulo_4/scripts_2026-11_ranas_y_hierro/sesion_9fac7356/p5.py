import bpy
from mathutils import Vector
sc=bpy.context.scene; sc.frame_set(880); al=bpy.data.objects["Armature"]
h=(al.matrix_world@al.pose.bones["Hips_alfred"].head)
r={}
for n in ["fireant_1","centipede_1","pillbug_1","honeyant_1","whipspider_1","ant_1"]:
    p=bpy.data.objects[n].matrix_world.translation; r[n]=[round(p.x,2),round(p.y,2),round(p.z,2)]
r["hips"]=[round(x,2) for x in h]
result=r
