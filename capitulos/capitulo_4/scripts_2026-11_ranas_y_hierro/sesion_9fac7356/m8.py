import bpy, math
from mathutils import Vector
sc=bpy.context.scene; sc.frame_set(1)
al=bpy.data.objects["Armature"]; pb=al.pose.bones; root=bpy.data.objects["alfred"]
r={}
for bn,mesh in (("Rightelbow_alfred","Mesh_2_alfred"),("Leftelbow_alfred","Mesh_3_alfred")):
    o=bpy.data.objects[mesh]; g=o.vertex_groups.get(bn); dg=bpy.context.evaluated_depsgraph_get(); e=o.evaluated_get(dg); me=e.to_mesh()
    Mi=(al.matrix_world@pb[bn].matrix).inverted(); ys=[]
    for v,ve in zip(o.data.vertices, me.vertices):
        w=next((x.weight for x in v.groups if x.group==g.index),0) if g else 0
        if w>0.5: ys.append(Mi@(e.matrix_world@ve.co))
    e.to_mesh_clear()
    ymax=max(p.y for p in ys); fin=[p for p in ys if p.y>ymax-0.12]
    c=sum(fin,Vector())/len(fin)
    r[bn]={"n":len(ys),"ymax":round(ymax,3),"centro_mano":[round(x,3) for x in c]}
# espacio detras de Alfred (para el paso atras)
dg=bpy.context.evaluated_depsgraph_get()
F=(al.matrix_world@pb["face_alfred"].matrix).to_3x3().col[2]
p0=root.matrix_world.translation
hueco=Vector((-76.47,-15.3,-9.85)); fw=(hueco-p0); fw.z=0; fw.normalize()
for back in (0.3,0.5,0.7):
    q=p0-fw*back+Vector((0,0,2.0)); h=sc.ray_cast(dg,q,Vector((0,0,-1)))
    r["suelo_atras_%.1f"%back]=(round(h[1].z,3),h[4].name) if h[0] else None
    # obstaculo a la altura del pecho
    s=p0-fw*back+Vector((0,0,1.0)); hh=sc.ray_cast(dg,p0+Vector((0,0,1.0)),(s-(p0+Vector((0,0,1.0)))).normalized(),distance=back+0.3)
    r["obst_%.1f"%back]=hh[4].name if hh[0] else None
r["fw"]=[round(x,3) for x in fw]; r["root"]=[round(x,3) for x in p0]
result=r
