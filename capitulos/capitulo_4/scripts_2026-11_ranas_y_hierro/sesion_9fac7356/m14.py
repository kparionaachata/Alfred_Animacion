import bpy, math
sc=bpy.context.scene; al=bpy.data.objects["Armature"]; pb=al.pose.bones
act=al.animation_data.action; cb=act.layers[0].strips[0].channelbag(al.animation_data.action_slot)
f=sc.frame_current; r={"frame":f}
for bn in ("RightUpArm_alfred","Rightelbow_alfred","Spine1_alfred"):
    cur=[round(math.degrees(x),4) for x in pb[bn].rotation_euler]
    cv=[round(math.degrees(cb.fcurves.find('pose.bones["%s"].rotation_euler'%bn,index=i).evaluate(f)),4) for i in range(3)]
    r[bn]={"actual":cur,"curva":cv,"cambiado":any(abs(a-b)>0.01 for a,b in zip(cur,cv))}
result=r
