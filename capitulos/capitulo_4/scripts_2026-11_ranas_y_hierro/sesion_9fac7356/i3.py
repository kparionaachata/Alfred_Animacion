import bpy
sc=bpy.context.scene; al=bpy.data.objects["Armature"]; pb=al.pose.bones
ins=[o for o in bpy.data.collections["insectos_alfred"].all_objects if o.type=="EMPTY"]
r={}
for f in range(600,841,10):
    sc.frame_set(f); h=al.matrix_world@pb["Hips_alfred"].head
    d=[round((o.matrix_world.translation-h).length,1) for o in ins]
    hd=al.matrix_world@pb["face_alfred"].head
    r[f]=dict(hips=[round(x,2) for x in h], cara_z=round(hd.z,2), dist=d)
r["textos_scene"]=[t.name for t in bpy.data.texts][-15:]
r["markers"]=[(m.name,m.frame) for m in sc.timeline_markers]
result=r
