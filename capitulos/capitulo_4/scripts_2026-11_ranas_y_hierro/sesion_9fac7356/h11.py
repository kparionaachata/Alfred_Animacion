import bpy
r={}
for ob,tn in ((bpy.data.objects["alfred"],"Salir_root"),(bpy.data.objects["Armature"],"Salir_arm")):
    t=ob.animation_data.nla_tracks[tn]; s=t.strips[0]; a=s.action
    xs=[k.co.x for l in a.layers for st in l.strips for cb in st.channelbags for c in cb.fcurves for k in c.keyframe_points]
    r[tn]=dict(strip=(s.frame_start,s.frame_end,s.action_frame_start,s.action_frame_end), claves=(min(xs),max(xs)), n=len(xs))
result=r
