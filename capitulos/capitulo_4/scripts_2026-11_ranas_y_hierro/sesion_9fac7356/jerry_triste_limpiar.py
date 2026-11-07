import bpy
n=0
for e in ("ojo_izquierdo_jerry","ojo_derecho_jerry"):
    sk=bpy.data.objects[e].data.shape_keys
    for c in sk.animation_data.action.layers[0].strips[0].channelbag(sk.animation_data.action_slot).fcurves:
        if c.data_path=='key_blocks["Triste"].value':
            for k in [k for k in c.keyframe_points if k.co.x>610][::-1]: c.keyframe_points.remove(k); n+=1
            c.update()
result={"claves_triste_borradas":n}
