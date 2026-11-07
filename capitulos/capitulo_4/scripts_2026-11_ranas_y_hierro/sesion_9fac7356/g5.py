import bpy
from mathutils import Vector
r={}
for n in ("Short_Grass","Tall_Grass"):
    o=bpy.data.objects[n]; me=o.data; c=0; ej=[]
    for p in me.polygons:
        ce=o.matrix_world@p.center
        if -20.5<=ce.x<=-12 and -7.5<=ce.y<=-3.5:
            c+=1
            if len(ej)<6: ej.append([round(x,2) for x in ce])
    r[n]=(c,ej)
# huella range
result=r
