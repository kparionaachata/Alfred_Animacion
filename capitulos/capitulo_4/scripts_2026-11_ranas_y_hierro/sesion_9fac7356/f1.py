import bpy
P=r"C:\Users\user\Desktop\Alfred_Animacion\objetos\vanilla\feather\feather.blend"
if "pluma_base" not in bpy.data.objects:
    with bpy.data.libraries.load(P) as (s,d): d.objects=[n for n in s.objects if n=="feather"]
    o=d.objects[0]; o.name="pluma_base"
    col=bpy.data.collections.get("plumas_pollos") or bpy.data.collections.new("plumas_pollos")
    if col.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(col)
    col.objects.link(o)
o=bpy.data.objects["pluma_base"]
result={"dim":list(o.dimensions),"mods":[(m.type,m.name) for m in o.modifiers],"bbox":[list(v) for v in o.bound_box][:2]}
