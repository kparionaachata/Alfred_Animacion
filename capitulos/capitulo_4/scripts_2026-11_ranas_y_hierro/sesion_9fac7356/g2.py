import bpy
r={}
for n in ("Short_Grass","Tall_Grass"):
    o=bpy.data.objects[n]
    r[n]=dict(verts=len(o.data.vertices), polys=len(o.data.polygons), mods=[(m.type,m.name) for m in o.modifiers], users=o.data.users,
              loc=[round(x,2) for x in o.location], scale=list(o.scale), sk=bool(o.data.shape_keys), mats=[m.name for m in o.data.materials])
result=r
