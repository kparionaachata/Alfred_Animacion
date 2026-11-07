import bpy
from collections import Counter
al=bpy.data.objects["Armature"]; pb=al.pose.bones
r={}
for o in bpy.data.objects:
    if o.type!="MESH" or not any(m.type=="ARMATURE" and m.object==al for m in o.modifiers): continue
    names={g.index:g.name for g in o.vertex_groups}
    c=Counter()
    for v in o.data.vertices:
        ws=tuple(sorted((names[g.group],round(g.weight,2)) for g in v.groups if g.weight>0.01 and names[g.group] in ("Neck_alfred","face_alfred","Spine2_alfred")))
        if ws: c[ws]+=1
    if c: r[o.name]=[(list(k),n) for k,n in c.most_common(8)]
result=r
