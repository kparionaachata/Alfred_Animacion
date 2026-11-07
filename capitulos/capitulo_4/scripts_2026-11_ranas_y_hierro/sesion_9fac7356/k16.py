import bpy
sc=bpy.context.scene
DIR=r"C:\Users\user\AppData\Local\Temp\claude\d0772e74e53e6fa2\9fac7356-8ced-4d1a-a12c-3247350383c7\scratchpad"
win=bpy.context.window_manager.windows[0]
area=max([a for a in win.screen.areas if a.type=="VIEW_3D"],key=lambda a:a.width*a.height)
reg=[r for r in area.regions if r.type=="WINDOW"][0]
fp=sc.render.filepath; cur=sc.frame_current; out=[]
for f in (100,110,118,123,130,145):
    sc.frame_set(f)
    with bpy.context.temp_override(window=win,area=area,region=reg):
        bpy.ops.render.opengl(view_context=True)
    p=DIR+"/vp3_%d.png"%f; bpy.data.images["Render Result"].save_render(p); out.append(p)
sc.render.filepath=fp; sc.frame_set(cur)
result={"out":len(out)}
