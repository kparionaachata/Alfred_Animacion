import bpy
from mathutils import Vector
sc=bpy.context.scene; dg=bpy.context.evaluated_depsgraph_get()
ms=[bpy.data.objects[n] for n in ("pig.Leg-FR_cerdo_1","pig.Leg-FL_cerdo_1","pig.Leg-BR_cerdo_1","pig.Leg-BL_cerdo_1")]
body=bpy.data.objects["pig.Body_cerdo_1"]
skip={o.name for o in bpy.data.collections["cerdo_relleno"].objects}
out={}
for f in (1,30,60,90,100,108,150,218,236,253,270,293,320,356):
    sc.frame_set(f); dg=bpy.context.evaluated_depsgraph_get()
    zmin=9e9; low=None
    for o in ms:
        e=o.evaluated_get(dg); m=e.to_mesh()
        for v in m.vertices:
            w=e.matrix_world@v.co
            if w.z<zmin: zmin=w.z; low=w.copy()
        e.to_mesh_clear()
    hit=sc.ray_cast(dg, Vector((low.x,low.y,low.z+3)), Vector((0,0,-1)))
    # ignore pig itself
    o=low+Vector((0,0,3)); g=None
    for _ in range(5):
        h=sc.ray_cast(dg,o,Vector((0,0,-1)))
        if not h[0]: break
        if h[4].name in skip: o=h[1]-Vector((0,0,0.001)); continue
        g=h[1].z; break
    out[f]=(round(zmin,3), round(g,3) if g is not None else None)
result=out
