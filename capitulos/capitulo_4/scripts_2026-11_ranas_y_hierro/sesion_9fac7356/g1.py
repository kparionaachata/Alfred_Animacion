import bpy
from mathutils import Vector
sc=bpy.context.scene
al=bpy.data.objects["Armature"]
pts=[]
for f in range(770,991,10):
    sc.frame_set(f); pts.append((f,[round(x,2) for x in (al.matrix_world@al.pose.bones["Hips_alfred"].head)]))
# objetos de pasto cerca del recorrido
cerca={}
P=[Vector(p) for _,p in pts]
for o in bpy.data.objects:
    n=o.name.lower()
    if o.type in ("MESH","CURVES") and any(k in n for k in ("grass","pasto","fern","plant","flower","hierba","tall")):
        d=min((o.matrix_world.translation-p).length for p in P)
        if d<3: cerca[o.name]=(round(d,2),o.type,len(o.data.vertices) if o.type=="MESH" else None, [round(x,1) for x in o.matrix_world.translation], o.data.users)
tipos={}
for o in bpy.data.objects:
    if o.type=="MESH" and ("grass" in o.name.lower() or "pasto" in o.name.lower()):
        k=o.name.split(".")[0]; tipos[k]=tipos.get(k,0)+1
result={"hips":pts,"pasto_cerca":dict(list(cerca.items())[:30]),"n_cerca":len(cerca),"tipos_pasto":dict(list(tipos.items())[:20])}
