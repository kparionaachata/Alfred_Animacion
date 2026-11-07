import bpy, math
sc=bpy.context.scene; rig=bpy.data.objects["Dog_001_rig"]; pbs=rig.pose.bones
T=[t for t in rig.animation_data.nla_tracks if t.name=="Jerry_mira_habla_arm"][0]; T.mute=True
r={}
for f in (100,120,136,150,170):
    sc.frame_set(f); M=rig.matrix_world
    fw=M@pbs["jaw_top"].tail-M@pbs["scull"].head
    jt=(M.to_3x3()@pbs["jaw_top"].matrix.to_3x3()).col[1]
    r[f]=dict(fw_pitch=round(math.degrees(math.atan2(fw.z,fw.xy.length)),1), jawtop_y_pitch=round(math.degrees(math.atan2(jt.z,jt.xy.length)),1))
T.mute=False
result=r
