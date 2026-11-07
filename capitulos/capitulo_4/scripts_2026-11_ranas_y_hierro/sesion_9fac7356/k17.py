import bpy
from mathutils import Vector
sc=bpy.context.scene; dg=bpy.context.evaluated_depsgraph_get()
obj=Vector((-76.5,-15.0,-9.8))
res=[]
for c in [(-75.6,-13.9,-9.4),(-75.4,-14.3,-9.5),(-76.0,-13.6,-9.2),(-75.8,-14.8,-9.6),(-75.3,-15.0,-9.5)]:
    c=Vector(c); d=obj-c
    h=sc.ray_cast(dg,c,d.normalized(),distance=d.length)
    res.append((tuple(c), h[0], h[4].name if h[0] else None, round((h[1]-c).length,2) if h[0] else None, round(d.length,2)))
result={"r":res}
