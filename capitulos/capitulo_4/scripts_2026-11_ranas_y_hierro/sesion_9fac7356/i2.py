import bpy
sc=bpy.context.scene
c=bpy.data.collections["insectos_alfred"]
def rng(o):
    ad=o.animation_data; r=[]
    if ad and ad.action: r.append(("act",tuple(ad.action.frame_range)))
    if ad: r+= [(t.name,s.frame_start,s.frame_end) for t in ad.nla_tracks for s in t.strips]
    return r
res={"objs":[(o.name,o.type,o.parent.name if o.parent else None,o.parent_bone,[(k.type,getattr(k,'subtarget','')) for k in o.constraints],rng(o),o.hide_render, o.hide_viewport) for o in c.all_objects][:60],
 "children":[x.name for x in c.children], "n":len(c.all_objects)}
vis={}
for f in (1,300,522,600,700,800,840):
    sc.frame_set(f)
    vis[f]=[(o.name,[round(v,1) for v in o.matrix_world.translation]) for o in c.all_objects if o.type in("EMPTY","ARMATURE") and o.parent is None][:12]
res["pos"]=vis
result=res
