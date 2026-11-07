import bpy
sc=bpy.context.scene; rig=bpy.data.objects["Dog_001_rig"]; pb=rig.pose.bones
r={}
for f in (50,300,600,850):
    sc.frame_set(f); r[f]=[round(x,3) for x in pb["spine_1"].scale]+[round(pb["tail_2"].rotation_euler.z,3)]
result=r
