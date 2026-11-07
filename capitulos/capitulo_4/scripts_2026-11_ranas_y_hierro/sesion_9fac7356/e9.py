import bpy
sc=bpy.context.scene; sc.frame_set(850); dg=bpy.context.evaluated_depsgraph_get()
al=bpy.data.objects["Armature"]; h=al.matrix_world@al.pose.bones["face_alfred"].head
r=[]
for o in bpy.data.objects:
    if o.type!="MESH" or not o.visible_get(): continue
    d=(o.matrix_world.translation-h).length
    if d<1.0: r.append((o.name, round(d,2), o.data.name, o.data.users))
result={"cerca":sorted(r,key=lambda x:x[1])}
