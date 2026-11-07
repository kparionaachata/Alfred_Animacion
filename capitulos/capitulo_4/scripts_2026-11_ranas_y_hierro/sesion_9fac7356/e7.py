import bpy
sc=bpy.context.scene; sc.frame_set(100); dg=bpy.context.evaluated_depsgraph_get()
al=bpy.data.objects["Armature"]; F=al.matrix_world@al.pose.bones["face_alfred"].matrix; fz=F.to_3x3().col[2].normalized()
r={}
for n in ("ojo_derecho_alfred","ojo_izquierdo_alfred"):
    e=bpy.data.objects[n].evaluated_get(dg); m=e.to_mesh(); c=sum((e.matrix_world@v.co for v in m.vertices), (e.matrix_world@m.vertices[0].co)*0)/len(m.vertices); e.to_mesh_clear()
    o=c+fz*1.0; hits=[]
    for _ in range(5):
        h=sc.ray_cast(dg,o,-fz)
        if not h[0]: break
        hits.append((h[4].name, round((h[1]-c).dot(fz),3))); o=h[1]-fz*0.0005
    r[n]=hits
result=r
