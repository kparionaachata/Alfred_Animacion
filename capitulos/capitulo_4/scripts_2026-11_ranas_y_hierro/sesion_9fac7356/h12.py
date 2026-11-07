import bpy
sc=bpy.context.scene
r={}
for ob,tn in ((bpy.data.objects["alfred"],"Salir_root"),(bpy.data.objects["Armature"],"Salir_arm")):
    s=ob.animation_data.nla_tracks[tn].strips[0]
    s.frame_end_ui=716
    s.action_frame_end=716
    if s.frame_end!=716: s.frame_end=716
    r[tn]=(s.frame_start,s.frame_end,s.action_frame_start,s.action_frame_end,round(s.scale,3))
al=bpy.data.objects["Armature"]; ins=bpy.data.objects["ant_1"]
for f in range(706,790,8):
    sc.frame_set(f); r[f]=(round((al.matrix_world@al.pose.bones["face_alfred"].head).z,2), round(ins.matrix_world.translation.z,2))
result=r
