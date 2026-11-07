"""El frame 16 pasa a ser el frame 1: en cada curva se asegura una clave en 16 (con su valor), se borran las anteriores
y todo se corre -15 frames; tambien los sonidos y el fin de la escena."""
import bpy
sc = bpy.context.scene; D = 15; F = 16
ids = list(bpy.data.objects) + list(bpy.data.shape_keys)
n_curvas = 0; objs = set()
for idb in ids:
    ad = getattr(idb, "animation_data", None)
    if not ad or not ad.action: continue
    for l in ad.action.layers:
        for st in l.strips:
            for cb in st.channelbags:
                for fc in cb.fcurves:
                    if not len(fc.keyframe_points): continue
                    v = fc.evaluate(F)
                    if not any(abs(k.co.x - F) < 1e-3 for k in fc.keyframe_points):
                        k = fc.keyframe_points.insert(F, v); k.interpolation = "LINEAR"
                    for k in [k for k in fc.keyframe_points if k.co.x < F - 1e-3][::-1]: fc.keyframe_points.remove(k)
                    for k in fc.keyframe_points:
                        k.co.x -= D; k.handle_left.x -= D; k.handle_right.x -= D
                    fc.update(); n_curvas += 1; objs.add(idb.name)
ed = sc.sequence_editor; snd = 0
if ed:
    for s in sorted(ed.strips_all, key=lambda s: s.frame_final_start):
        s.frame_start -= D; snd += 1
for m in sc.timeline_markers: m.frame -= D
sc.frame_end = sc.frame_end - D; sc.frame_start = 1; sc.frame_set(1)
result = {"curvas": n_curvas, "objetos": len(objs), "sonidos_movidos": snd, "rango": (sc.frame_start, sc.frame_end)}
