import bpy
sc=bpy.context.scene; sc.frame_set(850)
o=bpy.data.objects["ojo_derecho_alfred"]; dg=bpy.context.evaluated_depsgraph_get(); e=o.evaluated_get(dg); m=e.to_mesh()
# perfil en coordenadas de la malla evaluada relativas a la cara: proyectar en ejes de face_alfred
al=bpy.data.objects["Armature"]; F=(al.matrix_world@al.pose.bones["face_alfred"].matrix).to_3x3()
W=e.matrix_world
pts=[W@v.co for v in m.vertices]
c=sum(pts,pts[0]*0)/len(pts)
ax=[F.col[i].normalized() for i in range(3)]
loc=[[round((p-c).dot(a),3) for a in ax] for p in pts]
# top edge sampled: for bins along each axis
import collections
r={}
for hi,vi in ((0,1),(1,0),(0,2),(2,0),(1,2),(2,1)):
    b=collections.defaultdict(list)
    for q in loc: b[round(q[hi]/0.02)].append(q[vi])
    r["%d_%d"%(hi,vi)]=[(k,max(v),min(v)) for k,v in sorted(b.items())]
e.to_mesh_clear()
result={"scale":[round(x,2) for x in o.matrix_world.to_scale()],"perfiles":r}
