import bpy, math, sys
sys.path.insert(0, r"C:\Users\user\AppData\Local\Temp\claude\d0772e74e53e6fa2\9fac7356-8ced-4d1a-a12c-3247350383c7\scratchpad")
import importlib, ref_pose; importlib.reload(ref_pose)
from mathutils import Vector
sc=bpy.context.scene; al=bpy.data.objects["Armature"]; pb=al.pose.bones; root=bpy.data.objects["alfred"]; pala=bpy.data.objects["stone_shovel"]
DIR=r"C:\Users\user\AppData\Local\Temp\claude\d0772e74e53e6fa2\9fac7356-8ced-4d1a-a12c-3247350383c7\scratchpad"
acts={o:o.animation_data.action for o in (al,root) if o.animation_data}
for o in acts: o.animation_data.action=None
ref_pose.poner_ref(pb, root); pala.location=ref_pose.PALA_LOC; pala.rotation_euler=[math.radians(x) for x in ref_pose.PALA_ROT]
bpy.context.view_layer.update()
sh=sc.display.shading; ct=sh.color_type; sh.color_type="TEXTURE"
cd=bpy.data.cameras.new("_tc"); cam=bpy.data.objects.new("_tc",cd); sc.collection.objects.link(cam); oc=sc.camera; sc.camera=cam
r0=(sc.render.resolution_x,sc.render.resolution_y,sc.render.resolution_percentage)
sc.render.resolution_x=sc.render.resolution_y=500; sc.render.resolution_percentage=100
win=bpy.context.window_manager.windows[0]
area=max([a for a in win.screen.areas if a.type=="VIEW_3D"],key=lambda a:a.width*a.height); reg=[x for x in area.regions if x.type=="WINDOW"][0]
h=al.matrix_world@pb["Spine2_alfred"].head
out=[]
for i,off in enumerate([Vector((-0.9,0.35,0.1)),Vector((0.75,0.2,0.15)),Vector((0.0,1.0,0.35))]):
    cam.location=h+off; cam.rotation_euler=(h+Vector((0,-0.2,-0.2))-cam.location).to_track_quat('-Z','Y').to_euler(); cd.lens=22
    with bpy.context.temp_override(window=win,area=area,region=reg): bpy.ops.render.opengl(view_context=False)
    p=DIR+"/ref_%d.png"%i; bpy.data.images["Render Result"].save_render(p); out.append(p)
sc.camera=oc; bpy.data.objects.remove(cam); bpy.data.cameras.remove(cd); sh.color_type=ct
sc.render.resolution_x,sc.render.resolution_y,sc.render.resolution_percentage=r0
for o,a in acts.items(): o.animation_data.action=a
sc.frame_set(sc.frame_current)
result={"ok":out}
