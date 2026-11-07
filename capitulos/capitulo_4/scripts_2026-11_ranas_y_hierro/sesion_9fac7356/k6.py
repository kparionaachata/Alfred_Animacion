import bpy
from collections import defaultdict
o=bpy.data.objects["horno"]; M=o.matrix_world; N=M.to_3x3()
pis=defaultdict(list); fondo=defaultdict(list)
for p in o.data.polygons:
    n=(N@p.normal).normalized(); ce=M@p.center
    vs=[M@o.data.vertices[i].co for i in p.vertices]
    if n.z>0.9 and ce.y<-15.03: pis[round(ce.z,3)].append((round(min(v.x for v in vs),3),round(max(v.x for v in vs),3),round(min(v.y for v in vs),3),round(max(v.y for v in vs),3)))
    if n.y>0.9 and ce.y<-15.03: fondo[round(ce.y,3)].append((round(min(v.x for v in vs),3),round(max(v.x for v in vs),3),round(min(v.z for v in vs),3),round(max(v.z for v in vs),3)))
def resum(d):
    return {k:(len(v),[min(a[0] for a in v),max(a[1] for a in v),min(a[2] for a in v),max(a[3] for a in v)]) for k,v in sorted(d.items())}
result={"pisos_hueco_z":resum(pis),"fondos_hueco_y":resum(fondo)}
