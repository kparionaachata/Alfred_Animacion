import bpy
p=bpy.data.objects["alfred"]
result={"root":[(t.name,t.mute,[(s.name,s.frame_start,s.frame_end,s.action_frame_start,s.action_frame_end,s.blend_type,s.extrapolation) for s in t.strips]) for t in p.animation_data.nla_tracks]}
