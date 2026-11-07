import bpy, math
sc=bpy.context.scene; sc.frame_set(1)
al=bpy.data.objects["Armature"]; pb=al.pose.bones
result={"f1":{b.name:[round(math.degrees(x),3) for x in b.rotation_euler]+[round(x,4) for x in b.location] for b in pb if b.name.endswith("_alfred")},
        "root_f1":[round(x,4) for x in bpy.data.objects["alfred"].rotation_euler]}
