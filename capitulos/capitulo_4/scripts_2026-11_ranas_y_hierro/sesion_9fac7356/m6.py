import bpy, math, sys
sys.path.insert(0, r"C:\Users\user\AppData\Local\Temp\claude\d0772e74e53e6fa2\9fac7356-8ced-4d1a-a12c-3247350383c7\scratchpad")
import importlib, ref_pose; importlib.reload(ref_pose)
from mathutils import Vector
from mathutils.geometry import intersect_point_line
sc=bpy.context.scene; al=bpy.data.objects["Armature"]; pb=al.pose.bones; root=bpy.data.objects["alfred"]; pala=bpy.data.objects["stone_shovel"]
# apagar animacion temporalmente
acts={o:o.animation_data.action for o in (al,root) if o.animation_data}
for o in acts: o.animation_data.action=None
ref_pose.poner_ref(pb, root); pala.location=ref_pose.PALA_LOC; pala.rotation_euler=[math.radians(x) for x in ref_pose.PALA_ROT]
bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get()
M=pala.matrix_world; A=M@Vector((-0.31,-0.44,0)); B=M@Vector((0.36,0.29,0))
r={"punta":[round(x,3) for x in B],"mango":[round(x,3) for x in A]}
# extremo real de cada mano: vertices de la malla del brazo mas lejanos a lo largo del antebrazo
for bn in ("Leftelbow_alfred","Rightelbow_alfred"):
    Mb=al.matrix_world@pb[bn].matrix; Mi=Mb.inverted()
    best=None
    for o in [x for x in bpy.data.objects if x.type=="MESH" and x.name.startswith("Mesh_") and x.name.endswith("_alfred")]:
        e=o.evaluated_get(dg); me=e.to_mesh()
        for v in me.vertices:
            pw=e.matrix_world@v.co; pl=Mi@pw
            if abs(pl.x)<0.2 and abs(pl.z)<0.2 and 0<pl.y<0.8 and (best is None or pl.y>best[0].y): best=(pl,pw,o.name)
        e.to_mesh_clear()
    pl,pw,nm=best
    q,l=intersect_point_line(pw,A,B)
    r[bn]={"malla":nm,"extremo_local":[round(x,3) for x in pl],"dist_mango_cm":round((pw-q).length*100,1),"t":round(l,2)}
for o,a in acts.items(): o.animation_data.action=a
sc.frame_set(sc.frame_current)
result=r
