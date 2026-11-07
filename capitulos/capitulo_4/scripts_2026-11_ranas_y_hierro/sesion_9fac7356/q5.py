import bpy, math
sc=bpy.context.scene; rig=bpy.data.objects["Dog_001_rig"]
al=[o for o in bpy.data.objects if o.type=="ARMATURE" and "face_alfred" in o.pose.bones][0]
r={"alfred":al.name}
def pit(v): return round(math.degrees(math.atan2(v.z,(v.x**2+v.y**2)**.5)),1)
def yaw(v): return round(math.degrees(math.atan2(v.y,v.x)),1)
for f in range(100,176,6):
    sc.frame_set(f)
    M=rig.matrix_world; pb=rig.pose.bones
    a=M@pb["scull"].head; b=M@pb["jaw_top"].tail; fw=b-a
    t=al.matrix_world@al.pose.bones["face_alfred"].head; d=t-a
    r[f]=dict(fw=(yaw(fw),pit(fw)),obj=(yaw(d),pit(d)))
r["tracks"]=[(t.name,t.mute,[(s.name,s.frame_start,s.frame_end,s.blend_type) for s in t.strips]) for t in rig.animation_data.nla_tracks if any(s.frame_start<176 and s.frame_end>100 for s in t.strips)]
result=r
