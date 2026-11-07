import bpy
# quita las claves de cara/ojos de la version en f513 (513-541) antes de rehacerla en 625
n=0
for name in ("ojo_izquierdo_jerry","ojo_derecho_jerry","pupila_izquierda_jerry","pupila_derecha_jerry"):
    o=bpy.data.objects[name]
    for idb in (o, o.data.shape_keys):
        ad=getattr(idb,"animation_data",None)
        if not ad or not ad.action: continue
        cb=ad.action.layers[0].strips[0].channelbag(ad.action_slot)
        if not cb: continue
        for c in cb.fcurves:
            ks=[k for k in c.keyframe_points if 513<=k.co.x<=541]
            for k in ks[::-1]: c.keyframe_points.remove(k); n+=1
            c.update()
result={"claves_quitadas":n}
