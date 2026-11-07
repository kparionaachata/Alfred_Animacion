import bpy
from mathutils import Vector
sc=bpy.context.scene; sc.frame_set(1); dg=bpy.context.evaluated_depsgraph_get()
out={}
def hits(x,y):
    o=Vector((x,y,25)); r=[]
    for _ in range(6):
        h=sc.ray_cast(dg,o,Vector((0,0,-1)))
        if not h[0]: break
        r.append((round(h[1].z,2),h[4].name,round(h[2].z,2))); o=h[1]-Vector((0,0,0.001))
    return r
for p in [(-14.5,-0.5),(-15.5,-1.5),(-13.5,1.5),(-8.5,1.5)]: out[str(p)]=hits(*p)
result=out
