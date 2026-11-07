import bpy
sc=bpy.context.scene; sc.frame_set(850)
o=bpy.data.objects["ojo_derecho_alfred"]; dg=bpy.context.evaluated_depsgraph_get()
def bbox():
    dg=bpy.context.evaluated_depsgraph_get(); e=o.evaluated_get(dg); m=e.to_mesh(); pts=[e.matrix_world@v.co for v in m.vertices]; e.to_mesh_clear()
    return [round(min(p[i] for p in pts),3) for i in range(3)]+[round(max(p[i] for p in pts),3) for i in range(3)]
k=o.data.shape_keys.key_blocks["Dolor"]
a=bbox()
sk=o.data.shape_keys; act=sk.animation_data.action; sk.animation_data.action=None
k.value=0.0; bpy.context.view_layer.update(); b=bbox()
k.value=1.0; bpy.context.view_layer.update(); c=bbox()
sk.animation_data.action=act
result={"anim":a,"v0":b,"v1":c}
