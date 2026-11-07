import bpy
from collections import Counter
o=bpy.data.objects["horno"]; M=o.matrix_world; N=M.to_3x3()
mi=[i for i,m in enumerate(o.data.materials) if "front" in m.name]
c=Counter(); ys=[]
for p in o.data.polygons:
    n=(N@p.normal).normalized(); ce=M@p.center
    key=(p.material_index, tuple(round(x) for x in n))
    c[key]+=1
    if p.material_index in mi: ys.append((tuple(round(x,2) for x in n), round(ce.x,3),round(ce.y,3),round(ce.z,3)))
# caras front: rangos
import collections
g=collections.defaultdict(list)
for n,x,y,z in ys: g[n].append((x,y,z))
res={str(k):(len(v),[min(a[i] for a in v) for i in range(3)],[max(a[i] for a in v) for i in range(3)]) for k,v in g.items()}
result={"conteo":{str(k):v for k,v in c.items()},"front":res}
