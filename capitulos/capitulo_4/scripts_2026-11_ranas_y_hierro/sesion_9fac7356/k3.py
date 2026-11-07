import bpy
N=["coal_1","coal_2","coal_3","coal_4","coal_5","coal_suelto_-83_-11_-10","coal_suelto_-83_-12_-10"]
hechos=[]
for n in N:
    o=bpy.data.objects.get(n)
    if o: bpy.data.objects.remove(o, do_unlink=True); hechos.append(n)
result={"borrados":hechos,"quedan_coal_visibles":[o.name for o in bpy.data.objects if o.name.startswith("coal") and o.visible_get()]}
