import bpy, math
P=r"C:\Users\user\Desktop\Alfred_Animacion\objetos\vanilla\stone_shovel\stone_shovel.blend"
if "stone_shovel" not in bpy.data.objects:
    with bpy.data.libraries.load(P) as (s,d): d.objects=list(s.objects)
    col=bpy.data.objects["stone_axe"].users_collection[0]
    for o in d.objects: col.objects.link(o)
o=bpy.data.objects["stone_shovel"]
ax=bpy.data.objects["stone_axe"]
vs=[v.co for v in o.data.vertices]
# extremos del sprite en el plano XY local
import itertools
ext={"min":[round(min(v[i] for v in vs),3) for i in range(3)],"max":[round(max(v[i] for v in vs),3) for i in range(3)]}
# punto mas lejano en direccion (1,1) y (-1,-1)
pmax=max(vs,key=lambda v:v.x+v.y); pmin=min(vs,key=lambda v:v.x+v.y)
result={"objs":[x.name for x in bpy.data.objects if "shovel" in x.name],"ext":ext,"extremo_+":[round(x,3) for x in pmax],"extremo_-":[round(x,3) for x in pmin],
 "mods":[m.type for m in o.modifiers],"axe_constraints":[(c.name,c.type,getattr(c,'subtarget','')) for c in ax.constraints],"axe_ext":[round(x,3) for x in ax.dimensions], "shovel_dim":[round(x,3) for x in o.dimensions],"scale":list(o.scale)}
