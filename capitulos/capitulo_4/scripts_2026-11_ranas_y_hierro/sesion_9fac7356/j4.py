import bpy, math
sc=bpy.context.scene; rig=bpy.data.objects["Dog_001_rig"]; pb=rig.pose.bones; alf=bpy.data.objects["Armature"]
r={}
for f in range(1078,1132,4):
    sc.frame_set(f); M=rig.matrix_world
    a=M@pb["scull"].head; fw=M@pb["jaw_top"].tail-a
    up=(M@pb["sombrero"].tail-M@pb["sombrero"].head).normalized()
    d=alf.matrix_world@alf.pose.bones["face_alfred"].head-a
    r[f]=dict(yaw=round(math.degrees(math.atan2(fw.y,fw.x)),1), pitch=round(math.degrees(math.atan2(fw.z,fw.xy.length))+23,1), tilt=round(math.degrees(math.asin(max(-1,min(1,up.cross(fw.normalized()).z)))),1) if False else round(math.degrees(math.acos(max(-1,min(1,up.z)))),1), alf_yaw=round(math.degrees(math.atan2(d.y,d.x)),1))
result=r
