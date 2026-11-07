"""Bordes grises de la capucha de Alfred que aun se doblaban: vertices de Mesh_0_alfred DENTRO del cubo de la cabeza
(capucha / borde gris, mitad inferior de la cabeza) con face_alfred < 0.5 mezclado con Neck/Spine2/no_bone_03/04.
Se dejan rigidos a face_alfred (1.0) como el resto de la cabeza. Respaldo en alfred_cabeza_pesos_respaldo.json."""
import bpy, json, os
from mathutils import Vector
RESP = r"C:\Users\user\AppData\Local\Temp\claude\d0772e74e53e6fa2\9fac7356-8ced-4d1a-a12c-3247350383c7\scratchpad\alfred_cabeza_pesos_respaldo.json"
arm = bpy.data.objects["Armature"]; huesos = {b.name for b in arm.data.bones}
QUITAR = {"Neck_alfred", "Spine2_alfred", "Spine1_alfred", "Spine_alfred", "no_bone_03", "no_bone_04"} & huesos
o = bpy.data.objects["Mesh_0_alfred"]; nm = {g.index: g.name for g in o.vertex_groups}
pts = [o.matrix_world @ v.co for v in o.data.vertices if any(nm[g.group] == "face_alfred" and g.weight > 0.99 for g in v.groups)]
lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
resp = json.load(open(RESP)) if os.path.isfile(RESP) else {}
r = resp.setdefault(o.name, {})
cara = o.vertex_groups["face_alfred"]; quitar = [o.vertex_groups[q] for q in QUITAR if q in o.vertex_groups]
n = 0
for v in o.data.vertices:
    p = o.matrix_world @ v.co
    if all(lo[i] - 0.01 <= p[i] <= hi[i] + 0.01 for i in range(3)):
        d = {nm[g.group]: g.weight for g in v.groups}
        if d.get("face_alfred", 0) < 0.999 or any(q.name in d for q in quitar):
            r.setdefault(str(v.index), d)
            cara.add([v.index], 1.0, "REPLACE")
            for g in quitar:
                if g.name in d: g.remove([v.index])
            n += 1
json.dump(resp, open(RESP, "w"))
result = {"vertices_capucha_rigidos": n}
