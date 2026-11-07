import bpy
from mathutils import Vector
from collections import Counter
al=bpy.data.objects["Armature"]; hb={b.name for b in al.data.bones}
m0=bpy.data.objects["Mesh_0_alfred"]; nm0={g.index:g.name for g in m0.vertex_groups}
pts=[m0.matrix_world@v.co for v in m0.data.vertices if any(nm0[g.group]=="face_alfred" and g.weight>0.99 for g in v.groups)]
lo=Vector([min(p[i] for p in pts) for i in range(3)]); hi=Vector([max(p[i] for p in pts) for i in range(3)])
r={"lo":[round(x,3) for x in lo],"hi":[round(x,3) for x in hi]}
E=0.03
for o in bpy.data.objects:
    if o.type!="MESH" or not any(m.type=="ARMATURE" and m.object==al for m in o.modifiers): continue
    nm={g.index:g.name for g in o.vertex_groups}; c=Counter(); n=0
    for v in o.data.vertices:
        p=o.matrix_world@v.co
        if all(lo[i]-E<=p[i]<=hi[i]+E for i in range(3)):
            d={nm[g.group]:round(g.weight,2) for g in v.groups if nm[g.group] in hb and g.weight>0.01}
            if d.get("face_alfred",0)<0.999 or len(d)>1:
                n+=1; c[tuple(sorted(d))]+=1
    if n: r[o.name]=(n,[(list(k),x) for k,x in c.most_common(6)])
result=r
