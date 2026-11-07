import bpy
from mathutils import Vector
sc=bpy.context.scene; sc.frame_set(830); dg=bpy.context.evaluated_depsgraph_get()
al=bpy.data.objects["Armature"]
mallas={o.name for o in bpy.data.objects if o.type=="MESH" and (o.parent==al or any(m.type=="ARMATURE" and m.object==al for m in o.modifiers))}
out={}
for x in (-19.7,-19.55,-19.4,-19.25,-19.1):
  for y in (-6.2,-5.95,-5.8,-5.5,-5.3,-5.05,-4.8,-4.6):
    o=Vector((x,y,15)); z=None; nm=None
    for _ in range(10):
        h=sc.ray_cast(dg,o,Vector((0,0,-1)))
        if not h[0]: break
        if h[4].name in mallas: z=round(h[1].z,2); nm=h[4].name; break
        if h[2].z>0.5 and h[1].z<11.05: break
        o=h[1]-Vector((0,0,0.001))
    out["%.2f,%.2f"%(x,y)]=(z,nm)
result={"mallas":sorted(mallas),"sup":out}
