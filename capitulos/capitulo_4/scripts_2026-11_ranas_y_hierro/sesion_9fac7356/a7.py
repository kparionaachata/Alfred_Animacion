import bpy
from mathutils import Vector
al=bpy.data.objects["Armature"]; hb={b.name for b in al.data.bones}
m0=bpy.data.objects["Mesh_0_alfred"]; nm0={g.index:g.name for g in m0.vertex_groups}
pts=[m0.matrix_world@v.co for v in m0.data.vertices if any(nm0[g.group]=="face_alfred" and g.weight>0.99 for g in v.groups)]
lo=Vector([min(p[i] for p in pts) for i in range(3)]); hi=Vector([max(p[i] for p in pts) for i in range(3)])
r={}
for n in ("Mesh_0_alfred","Mesh_1_alfred"):
    o=bpy.data.objects[n]; nm={g.index:g.name for g in o.vertex_groups}
    zs=[]
    for v in o.data.vertices:
        p=o.matrix_world@v.co
        if all(lo[i]-0.01<=p[i]<=hi[i]+0.01 for i in range(2)) and lo.z-0.01<=p.z<=hi.z+0.01:
            d={nm[g.group]:g.weight for g in v.groups if nm[g.group] in hb}
            if d.get("face_alfred",0)<0.999: zs.append(round(p.z-lo.z,2))
    from collections import Counter
    r[n]=sorted(Counter(zs).items())[:25]
result=r
