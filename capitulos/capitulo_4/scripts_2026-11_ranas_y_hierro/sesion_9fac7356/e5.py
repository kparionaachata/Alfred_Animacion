import bpy, collections
sc=bpy.context.scene; sc.frame_set(850)
o=bpy.data.objects["ojo_derecho_alfred"]; kb=o.data.shape_keys.key_blocks
def perfil(src):
    b=collections.defaultdict(list)
    for co in src: b[round(co.x/0.009)].append(co.z)
    return [(k,round(max(v),4),round(min(v),4)) for k,v in sorted(b.items())]
r={"dolor_shape":perfil([d.co for d in kb["Dolor"].data]), "basis":perfil([d.co for d in kb["Basis"].data])}
dg=bpy.context.evaluated_depsgraph_get(); e=o.evaluated_get(dg)
m=e.to_mesh(); r["eval_local"]=perfil([v.co for v in m.vertices]); e.to_mesh_clear()
r["use_relative"]=o.data.shape_keys.use_relative; r["show_only"]=o.show_only_shape_key; r["active"]=o.active_shape_key_index
r["mods_dg"]=[(m_.name,m_.type,getattr(m_,'object',None) and m_.object.name, m_.show_render) for m_ in o.modifiers]
result=r
