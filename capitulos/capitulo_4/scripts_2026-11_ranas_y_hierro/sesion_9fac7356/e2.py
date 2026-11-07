import bpy
sc=bpy.context.scene; sc.frame_set(850)
o=bpy.data.objects["ojo_derecho_alfred"]; sk=o.data.shape_keys; k=sk.key_blocks["Dolor"]
d=max((k.data[i].co-sk.key_blocks["Basis"].data[i].co).length for i in range(len(k.data)))
dg=bpy.context.evaluated_depsgraph_get(); e=o.evaluated_get(dg); m=e.to_mesh()
zs=[v.co.z for v in m.vertices]
r=dict(val=round(k.value,3), mute=k.mute, maxdiff=round(d,4), sk_action=sk.animation_data.action.name if sk.animation_data and sk.animation_data.action else None,
  slot=sk.animation_data.action_slot.name_display if sk.animation_data and sk.animation_data.action_slot else None, nverts_eval=len(m.vertices), nverts=len(o.data.vertices),
  mods=[(m_.type,m_.show_viewport, getattr(m_,'object',None) and m_.object.name) for m_ in o.modifiers], hide=o.hide_get(), hv=o.hide_viewport)
e.to_mesh_clear()
result=r
