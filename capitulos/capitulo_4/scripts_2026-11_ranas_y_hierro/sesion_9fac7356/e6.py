import bpy
from mathutils import Vector
sc=bpy.context.scene
al=bpy.data.objects["Armature"]
r={}
for f in (100,170,250,380,500):
    sc.frame_set(f); dg=bpy.context.evaluated_depsgraph_get()
    F=(al.matrix_world@al.pose.bones["face_alfred"].matrix); fz=F.to_3x3().col[2].normalized(); c=F.translation
    def prof(n):
        e=bpy.data.objects[n].evaluated_get(dg); m=e.to_mesh(); ds=[(e.matrix_world@v.co-c).dot(fz) for v in m.vertices]; e.to_mesh_clear(); return round(min(ds),3),round(max(ds),3)
    r[f]={n:prof(n) for n in ("Mesh_0_alfred","ojo_derecho_alfred")}
result=r
