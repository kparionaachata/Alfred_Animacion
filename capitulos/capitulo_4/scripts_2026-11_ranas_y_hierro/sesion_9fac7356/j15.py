FRAMES=[640]
DIR=r"C:\Users\user\AppData\Local\Temp\claude\d0772e74e53e6fa2\9fac7356-8ced-4d1a-a12c-3247350383c7\scratchpad"
import bpy, math
from mathutils import Vector
sc=bpy.context.scene
rig=bpy.data.objects["Dog_001_rig"]
cd=bpy.data.cameras.new("_tmpcam"); cam=bpy.data.objects.new("_tmpcam",cd); sc.collection.objects.link(cam)
oc=sc.camera; sc.camera=cam
r0=(sc.render.resolution_x,sc.render.resolution_y,sc.render.resolution_percentage,sc.render.filepath)
sc.render.resolution_x=sc.render.resolution_y=500; sc.render.resolution_percentage=100
win=bpy.context.window_manager.windows[0]
area=max([a for a in win.screen.areas if a.type=="VIEW_3D"],key=lambda a:a.width*a.height)
reg=[r for r in area.regions if r.type=="WINDOW"][0]
out=[]
for f in FRAMES:
    sc.frame_set(f)
    h=rig.matrix_world@rig.pose.bones["scull"].head
    cam.location=h+Vector((-2.0,-1.6,0.7)); cam.rotation_euler=(h-cam.location).to_track_quat('-Z','Y').to_euler()
    cd.lens=45
    with bpy.context.temp_override(window=win,area=area,region=reg):
        bpy.ops.render.opengl(view_context=False)
    p=DIR+"/ech3_%d.png"%f; bpy.data.images["Render Result"].save_render(p); out.append(p)
sc.camera=oc; bpy.data.objects.remove(cam); bpy.data.cameras.remove(cd)
sc.render.resolution_x,sc.render.resolution_y,sc.render.resolution_percentage,sc.render.filepath=r0
result={"out":out}
