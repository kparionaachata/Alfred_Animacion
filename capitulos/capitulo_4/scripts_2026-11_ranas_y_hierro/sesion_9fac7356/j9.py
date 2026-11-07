import bpy
r={}
for n in ("ojo_izquierdo_jerry","pupila_izquierda_jerry","ojo_derecho_jerry","pupila_derecha_jerry"):
    o=bpy.data.objects[n]; kb=o.data.shape_keys.key_blocks
    def ext(k):
        cs=[v.co for v in kb[k].data]
        return [round(max(c[i] for c in cs)-min(c[i] for c in cs),4) for i in range(3)]
    r[n]={"basis":ext("Basis"),"closed":ext("Closed")}
    sk=o.data.shape_keys
    r[n]["fcurves"]=[c.data_path for c in sk.animation_data.action.layers[0].strips[0].channelbags[0].fcurves] if sk.animation_data and sk.animation_data.action else None
result=r
