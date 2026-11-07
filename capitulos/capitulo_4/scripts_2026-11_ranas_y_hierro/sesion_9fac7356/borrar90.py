import bpy
sc=bpy.context.scene
n=0; objs=set()
for o in list(bpy.data.objects)+list(bpy.data.shape_keys):
    ad=getattr(o,"animation_data",None)
    if not ad or not ad.action: continue
    a=ad.action
    for l in a.layers:
        for st in l.strips:
            for cb in st.channelbags:
                for fc in cb.fcurves:
                    ks=[k for k in fc.keyframe_points if k.co.x>90.5]
                    for k in ks[::-1]: fc.keyframe_points.remove(k); n+=1
                    if ks: objs.add(o.name); fc.update()
sc.frame_set(90)
result={"claves_borradas":n,"objetos":sorted(objs)}
