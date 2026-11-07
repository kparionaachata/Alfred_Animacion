import bpy, math
from mathutils import Vector
sc=bpy.context.scene; al=bpy.data.objects["Armature"]; root=bpy.data.objects["alfred"]
t=[x for x in root.animation_data.nla_tracks if x.name=="Alfred_toca_suelo"]
for x in t: x.mute=True
mallas=[o for o in bpy.data.objects if o.type=="MESH" and o.name.startswith("Mesh_") and o.name.endswith("_alfred")]
fz=[x for x in al.animation_data.nla_tracks if x.name=="Alfred_forcejea_suelo"]
for x in fz: x.mute=True
r={}
for f in range(771,892,3):
    sc.frame_set(f); dg=bpy.context.evaluated_depsgraph_get()
    lo=None
    for o in mallas:
        e=o.evaluated_get(dg); m=e.to_mesh(); M=e.matrix_world
        for v in m.vertices:
            p=M@v.co
            if lo is None or p.z<lo.z: lo=p.copy()
        e.to_mesh_clear()
    r[f]=[round(lo.x,2),round(lo.y,2),round(lo.z,2)]
for x in fz: x.mute=False
result=r
