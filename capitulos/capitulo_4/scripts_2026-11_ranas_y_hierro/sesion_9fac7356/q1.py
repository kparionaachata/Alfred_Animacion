import bpy
sc=bpy.context.scene; sc.frame_set(136)
rig=bpy.data.objects["Dog_001_rig"]
r={}
for o in bpy.data.objects:
    if "jerry" in o.name.lower() and o.type=="MESH":
        r[o.name]=dict(parent=o.parent.name if o.parent else None, ptype=o.parent_type, pbone=o.parent_bone,
            cons=[(c.type,getattr(c,'subtarget','')) for c in o.constraints], loc=[round(x,3) for x in o.matrix_world.translation],
            anim=bool(o.animation_data and (o.animation_data.action or o.animation_data.nla_tracks)))
sc_=rig.pose.bones["scull"]
r["_scull_head"]=[round(x,3) for x in (rig.matrix_world@sc_.head)]
r["_jerry_mesh"]=[o.name for o in bpy.data.objects if o.parent==rig][:20]
result=r
