import bpy
sc=bpy.context.scene
o=bpy.data.objects["Short_Grass"]
at=o.data.attributes["aplasta_t"].data
idx=[i for i,a in enumerate(at) if a.value<1e5][:8]
r={}
for f in (770,900):
    sc.frame_set(f); dg=bpy.context.evaluated_depsgraph_get(); e=o.evaluated_get(dg); m=e.to_mesh()
    r[f]=[[round(x,3) for x in (o.matrix_world@m.vertices[i].co)] for i in idx[:4]]; e.to_mesh_clear()
result=r
