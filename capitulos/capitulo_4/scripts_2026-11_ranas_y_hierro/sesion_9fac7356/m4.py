import bpy
from mathutils import Vector
from mathutils.geometry import intersect_point_line
al=bpy.data.objects["Armature"]; pb=al.pose.bones; p=bpy.data.objects["stone_shovel"]
M=p.matrix_world; a=M@Vector((-0.31,-0.44,0)); b=M@Vector((0.36,0.29,0))
r={}
for bn in ("Leftelbow_alfred","Rightelbow_alfred"):
    Mb=al.matrix_world@pb[bn].matrix
    for y in (0.2,0.3,0.35,0.4,0.5):
        for x in (-0.04,0,0.04):
            m=Mb@Vector((x,y,0)); q,l=intersect_point_line(m,a,b)
            r[f"{bn[:4]} y{y} x{x}"]=(round((m-q).length*100,1),round(l,2))
# longitud hueso
r["len"]={bn:round(pb[bn].length,3) for bn in ("Leftelbow_alfred","Rightelbow_alfred")}
result=r
