import bpy
sc=bpy.context.scene; sc.frame_set(136)
win=bpy.context.window_manager.windows[0]
area=max([a for a in win.screen.areas if a.type=="VIEW_3D"],key=lambda a:a.width*a.height)
reg=[r for r in area.regions if r.type=="WINDOW"][0]
old=sc.render.filepath
sc.render.filepath=r"C:\Users\user\AppData\Local\Temp\claude\d0772e74e53e6fa2\9fac7356-8ced-4d1a-a12c-3247350383c7\scratchpad\v136.png"
with bpy.context.temp_override(window=win,area=area,region=reg):
    bpy.ops.render.opengl(view_context=True)
    bpy.data.images["Render Result"].save_render(sc.render.filepath)
sc.render.filepath=old
result={"ok":1}
