import bpy
sc=bpy.context.scene
p=bpy.data.objects["stone_shovel"]; al=bpy.data.objects["Armature"]
dest=next(c for c in al.users_collection if c.name in [x.name for x in sc.collection.children_recursive] or c==sc.collection)
for c in list(p.users_collection): c.objects.unlink(p)
dest.objects.link(p)
result={"coleccion":dest.name,"en_escena":p.name in sc.objects}
