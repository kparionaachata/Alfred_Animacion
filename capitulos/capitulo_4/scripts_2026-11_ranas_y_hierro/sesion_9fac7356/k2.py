import bpy
r=[]
for o in bpy.data.objects:
    if "coal" in o.name.lower():
        r.append((o.name,o.type,[round(x,2) for x in o.matrix_world.translation],round(o.scale.x,2),o.hide_viewport,o.hide_render,o.visible_get(),o.parent.name if o.parent else None,[c.name for c in o.users_collection]))
result={"r":r}
