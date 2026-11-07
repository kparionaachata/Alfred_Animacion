import bpy
sc=bpy.context.scene; sc.frame_set(100)
r={}
for n in ("ojo_derecho_alfred","ojo_izquierdo_alfred"):
    o=bpy.data.objects[n]; sk=o.data.shape_keys
    kb=sk.key_blocks if sk else []
    b=[v.co for v in (kb["Basis"].data if sk else o.data.vertices)]
    M=o.matrix_world.to_3x3()
    fcs=[]
    if sk and sk.animation_data and sk.animation_data.action:
        for c in sk.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
            ks=[k.co.x for k in c.keyframe_points]
            fcs.append((c.data_path, len(ks), min(ks), max(ks)))
    r[n]=dict(keys=[(k.name,round(k.value,2)) for k in kb], ext=[round(max(c[i] for c in b)-min(c[i] for c in b),4) for i in range(3)],
       mn=[round(min(c[i] for c in b),4) for i in range(3)], mx=[round(max(c[i] for c in b),4) for i in range(3)],
       colz=[round(M.col[i].normalized().z,2) for i in range(3)], world=[round(x,3) for x in o.matrix_world.translation],
       nla=[t.name for t in sk.animation_data.nla_tracks] if sk and sk.animation_data else None, fcs=fcs,
       loc_anim=bool(o.animation_data and o.animation_data.action))
result=r
