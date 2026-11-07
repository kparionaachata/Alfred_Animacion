import bpy
sc=bpy.context.scene; sc.frame_set(30)
p=bpy.data.objects["stone_shovel"]; al=bpy.data.objects["Armature"]
c=p.constraints["Mano"]
result={"mw":[round(x,3) for x in p.matrix_world.translation],"scale_w":[round(x,3) for x in p.matrix_world.to_scale()],"cols":[x.name for x in p.users_collection],
 "en_escena":p.name in sc.objects, "visible":p.visible_get(), "con":(c.target.name if c.target else None,c.subtarget,c.influence,c.is_valid,c.mute, c.use_location_x, c.set_inverse_pending if hasattr(c,'set_inverse_pending') else None),
 "loc":list(p.location),"parent":p.parent.name if p.parent else None,"codo":[round(x,3) for x in al.matrix_world@al.pose.bones["Rightelbow_alfred"].head],
 "inv":[list(r) for r in c.inverse_matrix]}
