import bpy
sc=bpy.context.scene
r={}
for n in ("ojo_izquierdo_jerry","pupila_izquierda_jerry"):
    o=bpy.data.objects[n]; kb=o.data.shape_keys.key_blocks
    c=kb.get("Closed"); b=kb["Basis"]
    diff=max((c.data[i].co-b.data[i].co).length for i in range(len(b.data))) if c else None
    vals={}
    for f in (710,712,714,716,718): sc.frame_set(f); vals[f]=round(c.value,2)
    r[n]=dict(keys=[(k.name,k.mute,round(k.value,2),k.relative_key.name) for k in kb], diff=round(diff,4), vals=vals,
              use_relative=o.data.shape_keys.use_relative, hide=(o.hide_viewport,o.hide_render,o.hide_get()),
              mods=[m.type for m in o.modifiers], nverts=len(o.data.vertices),
              drivers=[d.data_path for d in (o.data.shape_keys.animation_data.drivers if o.data.shape_keys.animation_data else [])])
result=r
