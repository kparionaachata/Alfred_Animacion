import bpy, math
sc=bpy.context.scene
r={}
for n in ("chicken_1","chicken_2","chicken_3"):
    o=bpy.data.objects[n]; ms=[c for c in o.children_recursive if c.type=="MESH"]
    r[n]={}
    for f in (1,700,800,805,826,842,870,960):
        sc.frame_set(f); dg=bpy.context.evaluated_depsgraph_get()
        zmin=min((c.evaluated_get(dg).matrix_world@v.co).z for c in ms for v in c.evaluated_get(dg).to_mesh().vertices)
        e=o.matrix_world.to_euler()
        r[n][f]=([round(x,2) for x in o.matrix_world.translation], round(zmin-o.matrix_world.translation.z,3), [round(math.degrees(x)) for x in e])
result=r
