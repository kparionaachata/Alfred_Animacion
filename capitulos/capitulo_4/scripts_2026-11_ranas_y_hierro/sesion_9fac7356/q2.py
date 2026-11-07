import bpy
from mathutils import Vector
sc=bpy.context.scene; rig=bpy.data.objects["Dog_001_rig"]
def cen(o):
    dg=bpy.context.evaluated_depsgraph_get(); e=o.evaluated_get(dg); m=e.to_mesh()
    c=sum((e.matrix_world@v.co for v in m.vertices),Vector())/len(m.vertices); e.to_mesh_clear(); return c
r={}
eye=bpy.data.objects["ojo_derecho_jerry"]
r["mods"]=[(m.type,getattr(m,'object',None) and m.object.name) for m in eye.modifiers]
r["vgroups"]=[g.name for g in eye.vertex_groups]
for f in (100,110,120,136,150,170):
    sc.frame_set(f)
    M=(rig.matrix_world@rig.pose.bones["scull"].matrix).inverted()
    r[f]=[round(x,3) for x in (M@cen(eye))]
result=r
