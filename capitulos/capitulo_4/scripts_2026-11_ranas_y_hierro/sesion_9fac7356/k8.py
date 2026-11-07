import bpy
import math
bpy.data.objects["carbon_horno_3"].rotation_euler.x=math.radians(30)
from mathutils import Vector
PISO=-9.938
bpy.data.objects["carbon_horno_3"].location.y=-15.16
r={}
for n in ("carbon_horno_1","carbon_horno_2","carbon_horno_3"):
    o=bpy.data.objects[n]; bpy.context.view_layer.update()
    zmin=min((o.matrix_world@Vector(v)).z for v in o.bound_box)
    o.location.z+= PISO-zmin+0.002
    bpy.context.view_layer.update(); bb=[o.matrix_world@Vector(v) for v in o.bound_box]
    r[n]={"zmin":round(min(v.z for v in bb),3),"zmax":round(max(v.z for v in bb),3),"sale_cm":round((max(v.y for v in bb)+14.992)*100,1)}
result=r
