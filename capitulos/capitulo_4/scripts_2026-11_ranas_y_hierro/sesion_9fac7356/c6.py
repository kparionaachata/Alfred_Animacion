import bpy
from mathutils import Vector
sc=bpy.context.scene; sc.frame_set(600); dg=bpy.context.evaluated_depsgraph_get()
skip=set()
for c in ("cerdo_relleno","pollo_relleno"):
    if c in bpy.data.collections: skip|={o.name for o in bpy.data.collections[c].all_objects}
rows=[]
for y in range(4,-15,-1):
    row=[]
    for x in range(-26,-5):
        o=Vector((x+0.5,y+0.5,30)); v="  ."
        for _ in range(8):
            h=sc.ray_cast(dg,o,Vector((0,0,-1)))
            if not h[0]: break
            if h[4].name in skip or h[2].z<0.5: o=h[1]-Vector((0,0,0.001)); continue
            v="%3d"%round(h[1].z) if abs(h[1].z-round(h[1].z))<0.02 else "  ~"; 
            if h[4].name.split(".")[0] not in ("Grass_Block","Stone","Dirt","Gravel","Coarse_Dirt","Andesite","Cobblestone","Podzol"): v=v[:-1]+"*" if v.strip()!="~" else "  ~"
            break
        row.append(v)
    rows.append("y%5.1f "%(y+0.5)+"".join(row))
result={"x":"       "+"".join("%3d"%(x) for x in range(-26,-5)),"map":rows}
