import bpy, math
from mathutils import Euler
base=bpy.data.objects["coal_6"]
# hueco del combustible (abajo del horno): piso z -9.938, x -76.81..-76.13, fondo y -15.60, frente y -14.99
COLOCA=[("carbon_horno_1",(-76.62,-15.06,-9.925),(math.radians(4),math.radians(-3),math.radians(12))),
        ("carbon_horno_2",(-76.33,-15.10,-9.915),(math.radians(-8),math.radians(5),math.radians(-28))),
        ("carbon_horno_3",(-76.47,-15.24,-9.80),(math.radians(62),math.radians(0),math.radians(8)))]
hechos=[]
for n,loc,rot in COLOCA:
    o=bpy.data.objects.get(n)
    if o is None:
        o=base.copy(); o.name=n
        for c in base.users_collection: c.objects.link(o)
    o.animation_data_clear()
    o.hide_viewport=o.hide_render=False; o.hide_set(False)
    o.location=loc; o.rotation_mode="XYZ"; o.rotation_euler=rot; o.scale=(0.5,0.5,0.5)
    hechos.append(n)
bpy.context.view_layer.update()
from mathutils import Vector
r={}
for n in hechos:
    o=bpy.data.objects[n]; bb=[o.matrix_world@Vector(v) for v in o.bound_box]
    r[n]={"ymax_fuera_cm":round((max(v.y for v in bb)+14.992)*100,1),"zmin":round(min(v.z for v in bb),3),"zmax":round(max(v.z for v in bb),3)}
result=r
