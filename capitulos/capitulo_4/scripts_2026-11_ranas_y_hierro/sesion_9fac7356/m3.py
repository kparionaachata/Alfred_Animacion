import bpy
from mathutils import Vector
from mathutils.geometry import intersect_point_line
al=bpy.data.objects["Armature"]; pb=al.pose.bones; p=bpy.data.objects["stone_shovel"]
M=p.matrix_world
mango=M@Vector((-0.31,-0.44,0)); cabeza=M@Vector((0.36,0.29,0))
def info(bn):
    h=al.matrix_world@pb[bn].tail; t=al.matrix_world@pb[bn].head
    # punto de la mano: 0.35 a lo largo del hueso desde la cabeza (malla del antebrazo acaba en y=0.37)
    Mb=al.matrix_world@pb[bn].matrix; mano=Mb@Vector((0.04,0.35,0))
    q,lam=intersect_point_line(mano,mango,cabeza)
    return {"mano":[round(x,3) for x in mano],"dist_al_mango_cm":round((mano-q).length*100,1),"pos_en_mango_0a1":round(lam,2)}
result={"izq":info("Leftelbow_alfred"),"der":info("Rightelbow_alfred"),"mango":[round(x,3) for x in mango],"cabeza":[round(x,3) for x in cabeza]}
