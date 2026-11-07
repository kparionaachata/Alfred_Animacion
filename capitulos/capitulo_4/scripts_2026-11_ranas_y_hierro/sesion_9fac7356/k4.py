import bpy, math
from mathutils import Vector
o=bpy.context.view_layer.objects.active
sel=[x.name for x in bpy.context.selected_objects]
c=bpy.data.objects["coal_6"]
bb=[o.matrix_world@Vector(v) for v in o.bound_box]
cb=[Vector(v) for v in c.bound_box]
result={"activo":o.name if o else None,"sel":sel,"loc":[round(x,3) for x in o.matrix_world.translation],"rot":[round(math.degrees(x),1) for x in o.matrix_world.to_euler()],"dim":[round(x,3) for x in o.dimensions],
 "bbmin":[round(min(v[i] for v in bb),3) for i in range(3)],"bbmax":[round(max(v[i] for v in bb),3) for i in range(3)],"mats":[m.name for m in o.data.materials] if o.type=="MESH" else None,
 "coal":{"dim":[round(x,3) for x in c.dimensions],"scale":list(c.scale),"rot":[round(math.degrees(x),1) for x in c.rotation_euler],"data":c.data.name,"mods":[m.type for m in c.modifiers],"localbb":[[round(x,3) for x in cb[0]],[round(x,3) for x in cb[6]]]},
 "anim":bool(o.animation_data), "ncaras":len(o.data.polygons) if o.type=="MESH" else None}
