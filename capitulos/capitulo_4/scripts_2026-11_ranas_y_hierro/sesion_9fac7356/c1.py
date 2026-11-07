import bpy
P=r"C:\Users\user\Desktop\Alfred_Animacion\estructura_lista\cerdo_1.blend"
with bpy.data.libraries.load(P) as (src,_):
    objs=list(src.objects); cols=list(src.collections)
result={"archivo":bpy.data.filepath,"objs":objs,"cols":cols,"ya":[o.name for o in bpy.data.objects if "cerdo" in o.name.lower()]}
