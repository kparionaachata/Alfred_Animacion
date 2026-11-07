import bpy
al=bpy.data.objects["Armature"]; act=al.animation_data.action
cb=act.layers[0].strips[0].channelbag(al.animation_data.action_slot)
k103={}; todos=set()
for fc in cb.fcurves:
    fr=[round(k.co.x) for k in fc.keyframe_points]
    todos|=set(fr)
    if 103 in fr: k103.setdefault(fc.data_path.split('"')[1] if '"' in fc.data_path else fc.data_path,[]).append(fc.data_path.split('.')[-1]+str(fc.array_index))
r=bpy.data.objects["alfred"]
ra=r.animation_data.action if r.animation_data else None
result={"claves_en_103":k103,"frames_con_claves":sorted(todos)[-15:],"root_loc":[round(x,3) for x in r.location],"root_rot":[round(x,3) for x in r.rotation_euler]}
