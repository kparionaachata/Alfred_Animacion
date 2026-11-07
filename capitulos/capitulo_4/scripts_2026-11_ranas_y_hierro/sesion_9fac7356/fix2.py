import bpy
sc=bpy.context.scene
sc.camera=bpy.data.objects["Cam_prev"]
for n in [o.name for o in bpy.data.objects if o.name.startswith("_tmpcam")]: bpy.data.objects.remove(bpy.data.objects[n])
for d in [d for d in bpy.data.cameras if d.name.startswith("_tmpcam")]: bpy.data.cameras.remove(d)
sc.render.resolution_x=sc.render.resolution_y=360; sc.render.resolution_percentage=100
sc.render.filepath=r"C:\Users\user\AppData\Local\Temp\prevmono\m_54_15.png"
result={"cam":sc.camera.name,"tmp":[o.name for o in bpy.data.objects if o.name.startswith("_tmp")]}
