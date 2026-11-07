import bpy
sc=bpy.context.scene
r={}
for n in ("ojo_izquierdo_jerry","ojo_derecho_jerry"):
    o=bpy.data.objects[n]; k=o.data.shape_keys
    fc=None
    for c in (k.animation_data.action.layers[0].strips[0].channelbags[0].fcurves if k.animation_data and k.animation_data.action else []):
        if c.data_path=='key_blocks["Closed"].value': fc=c
    picos=[]; cerrado=False
    for f in range(sc.frame_start, sc.frame_end+1):
        v=fc.evaluate(f) if fc else 0
        if v>0.5 and not cerrado: picos.append(f); cerrado=True
        elif v<0.2: cerrado=False
    r[n]=picos
result=r
