import bpy, math
sc=bpy.context.scene; al=bpy.data.objects["Armature"]; pb=al.pose.bones
f=sc.frame_current
act=al.animation_data.action; cb=act.layers[0].strips[0].channelbag(al.animation_data.action_slot)
r={"frame":f}
for bn in ("RightUpArm_alfred","Rightelbow_alfred"):
    actual=[round(math.degrees(x),3) for x in pb[bn].rotation_euler]
    curva=[]
    for i in range(3):
        fc=cb.fcurves.find('pose.bones["%s"].rotation_euler'%bn,index=i)
        curva.append(round(math.degrees(fc.evaluate(f)),3))
    r[bn]={"actual":actual,"curva":curva}
result=r
