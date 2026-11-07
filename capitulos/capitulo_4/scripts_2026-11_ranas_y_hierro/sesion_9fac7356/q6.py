import bpy, math
sc=bpy.context.scene; rig=bpy.data.objects["Dog_001_rig"]; pb=rig.pose.bones
r={}
for f in (90,104,110,114,120,136,150,160,164,170):
    sc.frame_set(f); M=rig.matrix_world
    s=pb["sombrero"]; up=(M@s.tail-M@s.head).normalized()
    r[f]=dict(up_z=round(up.z,2), roll=round(math.degrees(math.atan2(up.y,up.z)),0), rx=round(math.degrees(math.atan2(up.x,up.z)),0),
              scull=[round(math.degrees(x)) for x in pb["scull"].matrix_basis.to_euler()],
              sp1=[round(math.degrees(x)) for x in pb["spine_1"].matrix_basis.to_euler()])
a=[t for t in rig.animation_data.nla_tracks if t.name=="Jerry_para_habla_arm"][0].strips[0].action; r["accion"]=a.name
cb=a.layers[0].strips[0].channelbags[0]
r["curvas"]=sorted(set(c.data_path.split('"')[1] for c in cb.fcurves if '"' in c.data_path))
result=r
