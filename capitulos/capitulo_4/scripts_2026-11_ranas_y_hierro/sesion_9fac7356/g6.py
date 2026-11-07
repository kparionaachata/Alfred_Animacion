import bpy
from mathutils import Vector
r={}
for o in bpy.data.objects:
    if o.type!="MESH" or not o.visible_get(): continue
    bb=[o.matrix_world@Vector(c) for c in o.bound_box]
    if max(v.x for v in bb)<-20.5 or min(v.x for v in bb)>-12 or max(v.y for v in bb)<-7.5 or min(v.y for v in bb)>-3.5: continue
    mats=[m.name if m else None for m in o.data.materials]
    gm={i for i,m in enumerate(mats) if m and any(k in m.lower() for k in ("grass","fern","flower","plant","dandelion","poppy","bush"))}
    if not gm: continue
    c=0
    for p in o.data.polygons:
        if p.material_index in gm:
            ce=o.matrix_world@p.center
            if -20.5<=ce.x<=-12 and -7.5<=ce.y<=-3.5: c+=1
    if c: r[o.name]=(c,[mats[i] for i in gm],len(o.data.vertices),[m.type for m in o.modifiers])
result=r
