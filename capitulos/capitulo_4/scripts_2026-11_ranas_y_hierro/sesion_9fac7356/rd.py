import bpy
s=bpy.context.scene
print("RES", s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage, repr(s.render.filepath), s.camera.name if s.camera else None)
