"""Parpadeos de Jerry invisibles: (1) la forma 'Closed' de los ojos aplastaba el GROSOR del ojo (Z local, 1 cm) en vez
del alto: el ojo tiene el alto en X local (X local = vertical del mundo). Se rehace cerrando hacia abajo en X (como la
pupila, que cierra hacia abajo en su Z local). (2) las pupilas casi no tenian claves de 'Closed': se copian las
del ojo de su lado para que cierren junto con el."""
import bpy
sc = bpy.context.scene
PARES = (("ojo_izquierdo_jerry", "pupila_izquierda_jerry"), ("ojo_derecho_jerry", "pupila_derecha_jerry"))

def fcurve_closed(o):
    sk = o.data.shape_keys
    for c in sk.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        if c.data_path == 'key_blocks["Closed"].value': return c

res = {}
for ojo_n, pup_n in PARES:
    ojo, pup = bpy.data.objects[ojo_n], bpy.data.objects[pup_n]
    kb = ojo.data.shape_keys.key_blocks
    M = ojo.matrix_world.to_3x3()
    ax = max(range(3), key=lambda i: abs(M.col[i].normalized().z))          # eje local vertical del ojo
    sg = 1 if M.col[ax].z > 0 else -1
    base = [v.co.copy() for v in kb["Basis"].data]
    abajo = min(c[ax] for c in base) if sg > 0 else max(c[ax] for c in base)
    for i, c in enumerate(base):
        n = c.copy(); n[ax] = abajo; kb["Closed"].data[i].co = n
    fo = fcurve_closed(ojo); fp = fcurve_closed(pup)
    for k in list(fp.keyframe_points)[::-1]: fp.keyframe_points.remove(k)
    for k in fo.keyframe_points:
        p = fp.keyframe_points.insert(k.co.x, k.co.y, options={"FAST"}); p.interpolation = k.interpolation
    fp.update()
    res[ojo_n] = {"eje_vertical": ax, "claves_copiadas_a_pupila": len(fo.keyframe_points)}
result = res
