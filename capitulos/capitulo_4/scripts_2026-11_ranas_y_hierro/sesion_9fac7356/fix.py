import bpy
sc=bpy.context.scene
c=bpy.data.objects.get("_tmpcam")
cams=[o for o in sc.objects if o.type=="CAMERA" and o.name!="_tmpcam"]
if c: bpy.data.objects.remove(c)
for cd in [d for d in bpy.data.cameras if d.name.startswith("_tmpcam") and d.users==0]: bpy.data.cameras.remove(cd)
result={"camara":sc.camera.name if sc.camera else None,"otras":[o.name for o in cams],"res":(sc.render.resolution_x,sc.render.resolution_y,sc.render.resolution_percentage),"fp":sc.render.filepath}
