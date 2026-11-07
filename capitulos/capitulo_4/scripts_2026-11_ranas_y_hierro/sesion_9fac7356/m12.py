import bpy, math
from mathutils import Euler
r={}
for n,a,b in (("UpArm",(451.118,122.901,406.415),(352.397,148.413,233.462)),("elbow",(64.422,-21.81,-92.722),(34.027,1.626,-120.455))):
    qa=Euler([math.radians(x) for x in a]).to_quaternion(); qb=Euler([math.radians(x) for x in b]).to_quaternion()
    r[n]=round(math.degrees(qa.rotation_difference(qb).angle),1)
result=r
