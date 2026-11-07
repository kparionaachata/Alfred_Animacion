import bpy
sc=bpy.context.scene
k=("insect","insecto","bicho","bug","mosca","fly","grillo","hormiga","ant_","beetle","escarabajo","luciern","firefly","mosquito","particle","part")
r=[(o.name,o.type,o.users_collection[0].name if o.users_collection else None) for o in bpy.data.objects if any(x in o.name.lower() for x in k)]
ps=[(o.name,[m.name for m in o.modifiers if m.type=="PARTICLE_SYSTEM"]) for o in bpy.data.objects if any(m.type=="PARTICLE_SYSTEM" for m in o.modifiers)]
al=bpy.data.objects["Armature"]
pos={}
for f in (1,200,400,522,600,700,840):
    sc.frame_set(f); pos[f]=[round(x,2) for x in (al.matrix_world@al.pose.bones["Hips_alfred"].head)] if "Hips_alfred" in al.pose.bones else None
cols=[c.name for c in bpy.data.collections]
result={"insectos":r,"particulas":ps,"alfred_hips":pos,"cols":cols}
