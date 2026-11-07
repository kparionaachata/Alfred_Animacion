import bpy
sc=bpy.context.scene; sc.frame_set(100); dg=bpy.context.evaluated_depsgraph_get()
al=bpy.data.objects["Armature"]; F=al.matrix_world@al.pose.bones["face_alfred"].matrix; fz=F.to_3x3().col[2].normalized()
o0=bpy.data.objects["Mesh_0_alfred"]
r={}
for n in ("ojo_derecho_alfred",):
    e=bpy.data.objects[n].evaluated_get(dg); m=e.to_mesh(); c=sum((e.matrix_world@v.co for v in m.vertices), (e.matrix_world@m.vertices[0].co)*0)/len(m.vertices); e.to_mesh_clear()
    o=c+fz*1.0; hits=[]
    for _ in range(4):
        h=sc.ray_cast(dg,o,-fz)
        if not h[0]: break
        ob=h[4]; fi=h[3]
        info=(ob.name, round((h[1]-c).dot(fz),3), fi)
        if ob.name=="Mesh_0_alfred":
            ev=ob.evaluated_get(dg); me=ev.data
            poly=me.polygons[fi]; mat=ob.material_slots[poly.material_index].material
            info+= (mat.name if mat else None, getattr(mat,'blend_method',None))
            uvl=me.uv_layers.active.data
            uv=[tuple(round(x,3) for x in uvl[li].uv) for li in poly.loop_indices]
            info+=(uv[0],)
            img=next((nd.image for nd in mat.node_tree.nodes if nd.type=="TEX_IMAGE" and nd.image), None) if mat and mat.use_nodes else None
            if img:
                W,H=img.size; u=sum(x[0] for x in uv)/len(uv); v=sum(x[1] for x in uv)/len(uv)
                px=img.pixels; i=(int(v*H)%H*W+int(u*W)%W)*4
                info+=(img.name, [round(px[i+k],2) for k in range(4)])
        hits.append(info); o=h[1]-fz*0.0005
    r[n]=hits
result=r
