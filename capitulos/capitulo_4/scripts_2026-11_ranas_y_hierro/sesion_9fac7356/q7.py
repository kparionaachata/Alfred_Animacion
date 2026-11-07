import bpy, math
sc=bpy.context.scene; rig=bpy.data.objects["Dog_001_rig"]; pb=rig.pose.bones
T={t.name:t for t in rig.animation_data.nla_tracks}
def ev(f): sc.frame_set(f); return [round(math.degrees(x)) for x in pb["scull"].matrix_basis.to_euler()]
r={"con":{f:ev(f) for f in (114,136,160)}}
T["Jerry_voz_subida"].mute=True
r["sin_voz"]={f:ev(f) for f in (114,136,160)}
T["Jerry_voz_subida"].mute=False
st=T["Jerry_para_habla_arm"].strips[0]
r["strip"]=(st.name,st.action.name,st.action_frame_start,st.action_frame_end,st.extrapolation)
r["look"]={k:[round(math.degrees(x)) for x in v] for k,v in list(bpy.app.driver_namespace.get("_jerry_look110",{}).items())[::10]}
result=r
