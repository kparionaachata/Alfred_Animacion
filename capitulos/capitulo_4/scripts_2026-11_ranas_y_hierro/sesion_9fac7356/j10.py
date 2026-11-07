import bpy
sc=bpy.context.scene; sc.frame_set(100)
r={}
for n in ("ojo_izquierdo_jerry","pupila_izquierda_jerry"):
    o=bpy.data.objects[n]; M=o.matrix_world.to_3x3()
    kb=o.data.shape_keys.key_blocks
    b=[v.co for v in kb["Basis"].data]; c=[v.co for v in kb["Closed"].data]
    r[n]=dict(colz=[round(M.col[i].normalized().z,2) for i in range(3)],
       basis_min=[round(min(v[i] for v in b),4) for i in range(3)], basis_max=[round(max(v[i] for v in b),4) for i in range(3)],
       closed_min=[round(min(v[i] for v in c),4) for i in range(3)], closed_max=[round(max(v[i] for v in c),4) for i in range(3)])
result=r
