import bpy
sc=bpy.context.scene; al=bpy.data.objects["Armature"]; pb=al.pose.bones
ins=bpy.data.objects["ant_1"]
r={}
for f in range(700,800,6):
    sc.frame_set(f); r[f]=(round((al.matrix_world@pb["face_alfred"].head).z,2),[round(x,2) for x in ins.matrix_world.translation])
r["alfred_tracks"]=[(t.name,t.mute,[(s.name,s.frame_start,s.frame_end,s.action_frame_start,s.action_frame_end,round(s.scale,3),s.repeat) for s in t.strips]) for t in al.animation_data.nla_tracks]
r["alfred_action"]=al.animation_data.action.name if al.animation_data.action else None
p=al.parent
r["parent"]=p.name if p else None
if p and p.animation_data: r["parent_anim"]=(p.animation_data.action.name if p.animation_data.action else None,[t.name for t in p.animation_data.nla_tracks])
result=r
