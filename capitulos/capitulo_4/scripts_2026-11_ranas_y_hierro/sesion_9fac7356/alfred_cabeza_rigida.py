"""Distorsion de la cabeza de Alfred al doblar el cuello: los vertices de la cabeza (face_alfred > 0.5) en Mesh_0_alfred y
en los ojos tambien pesaban en Neck_alfred / Spine2_alfred / no_bone_03 / no_bone_04 (huesos del rig activo 'Armature'),
asi que al girar el cuello el cubo se cizallaba. Se dejan rigidos: face_alfred = 1.0 y se quitan esos otros grupos en esos
vertices (los grupos de rigs viejos sin hueso en 'Armature' no deforman y no se tocan). Respaldo de los pesos en
alfred_cabeza_pesos_respaldo.json (para revertir: RESTAURAR = True)."""
import bpy, json, os
RESP = r"C:\Users\user\AppData\Local\Temp\claude\d0772e74e53e6fa2\9fac7356-8ced-4d1a-a12c-3247350383c7\scratchpad\alfred_cabeza_pesos_respaldo.json"
RESTAURAR = globals().get("RESTAURAR", False)
arm = bpy.data.objects["Armature"]
huesos = {b.name for b in arm.data.bones}
QUITAR = {"Neck_alfred", "Spine2_alfred", "Spine1_alfred", "Spine_alfred", "no_bone_03", "no_bone_04"} & huesos
MALLAS = ("Mesh_0_alfred", "ojo_derecho_alfred", "ojo_izquierdo_alfred")
if RESTAURAR:
    data = json.load(open(RESP))
    for n, verts in data.items():
        o = bpy.data.objects[n]
        for vi, ws in verts.items():
            for g in o.vertex_groups:
                if g.name in ws: g.add([int(vi)], ws[g.name], "REPLACE")
                else:
                    try: g.remove([int(vi)])
                    except RuntimeError: pass
    result = {"restaurado": list(data)}
else:
    resp = json.load(open(RESP)) if os.path.isfile(RESP) else {}
    cambios = {}
    for n in MALLAS:
        o = bpy.data.objects[n]; names = {g.index: g.name for g in o.vertex_groups}
        cara = o.vertex_groups["face_alfred"]; quitar = [o.vertex_groups[q] for q in QUITAR if q in o.vertex_groups]
        r = resp.setdefault(n, {}); c = 0
        for v in o.data.vertices:
            d = {names[g.group]: g.weight for g in v.groups}
            if d.get("face_alfred", 0) > 0.5:
                r.setdefault(str(v.index), d)                       # respaldo del peso original (solo la primera vez)
                cara.add([v.index], 1.0, "REPLACE")
                for g in quitar:
                    if g.name in d: g.remove([v.index])
                c += 1
        cambios[n] = c
    json.dump(resp, open(RESP, "w"))
    result = {"vertices_rigidos": cambios, "grupos_quitados": sorted(QUITAR)}
