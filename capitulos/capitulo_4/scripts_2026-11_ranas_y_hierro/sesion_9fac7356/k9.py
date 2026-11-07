import bpy, math
from mathutils import Vector
sc=bpy.context.scene
arms=[o.name for o in bpy.data.objects if o.type=="ARMATURE"]
al=bpy.data.objects.get("Armature")
r={"armatures":arms[:20]}
if al:
    r["alfred_root"]=al.parent.name if al.parent else None
    pr=al.parent
    r["root_loc"]=[round(x,3) for x in (pr.matrix_world.translation if pr else al.matrix_world.translation)]
    r["root_rotz"]=round(math.degrees((pr or al).matrix_world.to_euler().z),1)
    r["hips"]=[round(x,3) for x in (al.matrix_world@al.pose.bones["Hips_alfred"].head)]
    r["mano"]=[round(x,3) for x in (al.matrix_world@al.pose.bones["Rightelbow_alfred"].tail)]
    r["bones"]=[b.name for b in al.pose.bones]
herr=[(o.name,o.type,[round(x,2) for x in o.matrix_world.translation],[ (c.type,getattr(c,'subtarget',''),round(c.influence,2)) for c in o.constraints], o.visible_get()) for o in bpy.data.objects if any(k in o.name.lower() for k in ("shovel","pala","axe","pickaxe","sword","espada","hacha","pico"))]
r["herramientas"]=herr
r["frames"]=(sc.frame_start,sc.frame_end,sc.frame_current)
result=r
