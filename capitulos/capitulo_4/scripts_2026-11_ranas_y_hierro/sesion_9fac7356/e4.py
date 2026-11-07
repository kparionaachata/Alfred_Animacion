import bpy
sc=bpy.context.scene
o=bpy.data.objects["ojo_derecho_alfred"]
r={}
for f in (100,200,417,418,500,850):
    sc.frame_set(f); r[f]=(o.hide_viewport,o.hide_render,o.visible_get())
ad=o.animation_data
fc=[c for c in ad.action.layers[0].strips[0].channelbag(ad.action_slot).fcurves if c.data_path=="hide_viewport"][0]
r["ultimas_claves_hide"]=[(k.co.x,k.co.y) for k in fc.keyframe_points][-4:]
result=r
