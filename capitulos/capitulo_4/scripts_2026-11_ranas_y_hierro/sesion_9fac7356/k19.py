import bpy, math
from mathutils import Vector
sc=bpy.context.scene; sc.frame_set(30); dg=bpy.context.evaluated_depsgraph_get()
obj=Vector((-76.5,-15.0,-9.85))
p=bpy.data.objects["stone_shovel"]; M=p.matrix_world
res=[]
for c in [(-75.9,-14.5,-8.9),(-77.2,-14.4,-9.3),(-77.3,-14.9,-9.5),(-75.5,-14.6,-9.2),(-76.5,-14.3,-8.8),(-77.0,-14.2,-9.0)]:
    c=Vector(c); d=obj-c; h=sc.ray_cast(dg,c,d.normalized(),distance=d.length-0.15)
    res.append((tuple(round(x,2) for x in c), h[4].name if h[0] else "libre"))
result={"cams":res,"pala_mundo":[round(x,3) for x in M.translation],"punta":[round(x,3) for x in M@Vector((0.36,0.29,0))],"mango":[round(x,3) for x in M@Vector((-0.31,-0.44,0))]}
