import bpy
_sh=bpy.context.scene.display.shading; _ct=_sh.color_type; _sh.color_type="TEXTURE"
FRAMES=[1,22,26,32,52,84]
DIR=r"C:\Users\user\AppData\Local\Temp\claude\d0772e74e53e6fa2\9fac7356-8ced-4d1a-a12c-3247350383c7\scratchpad"
import bpy, math
from mathutils import Vector
sc=bpy.context.scene
rig=bpy.data.objects["Armature"]
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
    h=Vector((-76.5,-15.0,-9.8))
    cam.location=Vector((-77.25,-14.35,-9.3)); cam.rotation_euler=(h-cam.location).to_track_quat('-Z','Y').to_euler()
    cd.lens=24
    with bpy.context.temp_override(window=win,area=area,region=reg):
        bpy.ops.render.opengl(view_context=False)
    p=DIR+"/pc4_%d.png"%f; bpy.data.images["Render Result"].save_render(p); out.append(p)
sc.camera=oc; bpy.data.objects.remove(cam); bpy.data.cameras.remove(cd)
sc.render.resolution_x,sc.render.resolution_y,sc.render.resolution_percentage,sc.render.filepath=r0
result={"out":out}
_sh.color_type=_ct
