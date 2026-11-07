import bpy
sc=bpy.context.scene; al=bpy.data.objects["Armature"]; pb=al.pose.bones
hz={}; fz={}
for f in range(380,720):
    sc.frame_set(f); hz[f]=(al.matrix_world@pb["Hips_alfred"].head).z; fz[f]=(al.matrix_world@pb["face_alfred"].head).z
def tramo(d,lim):
    fr=[f for f in sorted(d) if d[f]<lim]
    return (fr[0],fr[-1],len(fr)) if fr else None
result={"cadera_bajo_suelo":tramo(hz,13.0),"cabeza_bajo_suelo":tramo(fz,13.0),
        "muestras":{f:(round(hz[f],2),round(fz[f],2)) for f in range(380,720,10)}}
