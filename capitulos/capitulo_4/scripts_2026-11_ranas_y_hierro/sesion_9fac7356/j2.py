import bpy
j=bpy.data.objects["jerry"]; rig=bpy.data.objects["Dog_001_rig"]
result={"root":[t.name for t in j.animation_data.nla_tracks],"rig":[t.name for t in rig.animation_data.nla_tracks]}
