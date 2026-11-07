import bpy
from collections import Counter
r={}
for n in ("Mesh_0_alfred","ojo_derecho_alfred","ojo_izquierdo_alfred"):
    o=bpy.data.objects[n]; names={g.index:g.name for g in o.vertex_groups}
    otros=Counter(); tot=len(o.data.vertices); cab=0; sumas=[]
    for v in o.data.vertices:
        d={names[g.group]:g.weight for g in v.groups if g.weight>0.001}
        if d.get("face_alfred",0)>0.5:
            cab+=1; sumas.append(sum(d.values()))
            for k in d:
                if k!="face_alfred": otros[k]+=1
    r[n]=dict(total=tot,cabeza=cab,otros=dict(otros),suma_min=round(min(sumas),3) if sumas else None,suma_max=round(max(sumas),3) if sumas else None,
              mods=[(m.type,m.name,getattr(m,'object',None) and m.object.name, getattr(m,'vertex_group','')) for m in o.modifiers])
result=r
