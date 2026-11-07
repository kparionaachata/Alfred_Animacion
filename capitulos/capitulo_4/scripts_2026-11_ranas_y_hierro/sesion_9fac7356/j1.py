import bpy, math
sc=bpy.context.scene; j=bpy.data.objects["jerry"]; rig=bpy.data.objects["Dog_001_rig"]
r={}
for f in (500,600,700,760,800,840,900,960):
    sc.frame_set(f); r[f]=([round(x,2) for x in j.matrix_world.translation], round(math.degrees(j.matrix_world.to_euler().z)))
def tr(o): return [(t.name,t.mute,t.strips[0].blend_type if t.strips else None,[(s.frame_start,s.frame_end) for s in t.strips]) for t in o.animation_data.nla_tracks]
r["root_tracks"]=[x for x in tr(j) if any(e>600 for _,e in x[3])]
r["rig_tracks"]=[x for x in tr(rig) if any(e>600 for _,e in x[3])]
r["root_action"]=j.animation_data.action.name if j.animation_data.action else None
r["rig_action"]=rig.animation_data.action.name if rig.animation_data.action else None
result=r
