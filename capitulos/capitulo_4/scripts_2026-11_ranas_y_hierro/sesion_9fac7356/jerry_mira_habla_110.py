"""Jerry mira a Alfred al hablar (f110-164): quita el giro de scull de la pista de voz (dejaba la cabeza torcida bajo el
sombrero) y apunta con spine_1 (cuello) + correccion pequena de scull, en una pista ADD propia."""
import ast, bpy, math
from mathutils import Quaternion, Vector
A, B, RAMPA = 110, 164, 5
sc = bpy.context.scene; rig = bpy.data.objects["Dog_001_rig"]; alf = bpy.data.objects["Armature"]; pbs = rig.pose.bones
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
peso = lambda f: ss((f - A) / RAMPA) * (1 - ss((f - (B - RAMPA)) / RAMPA))
# 1) scull de la voz = solo el habla
c = {}
for n in ast.parse(open(r"C:\Users\user\Downloads\sadasdsadsad.py", encoding="utf-8").read()).body:
    if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in ("SPEECH_CURVE", "END_FRAME"):
        c[n.targets[0].id] = ast.literal_eval(n.value)
sp = {int(f): float(l) for f, l in c["SPEECH_CURVE"]}
va = bpy.data.actions["jerry_voz_subida_rostro_arm"]
cbv = va.layers[0].strips[0].channelbags[0]
for ax in range(3):
    fc = cbv.fcurves.find('pose.bones["scull"].rotation_euler', index=ax)
    for k in fc.keyframe_points:
        f = round(k.co.x)
        if A <= f <= B:
            lf = f - A + 1; l = sp.get(lf, 0.0) if lf <= c["END_FRAME"] else 0.0
            k.co.y = (math.radians(1.15) * l, math.radians(0.55) * l * math.sin(lf * 0.19), 0.0)[ax]
            k.handle_left.y = k.handle_right.y = k.co.y
    fc.update()
# 2) mirada nueva
for t in list(rig.animation_data.nla_tracks):
    if t.name == "Jerry_mira_habla_arm": rig.animation_data.nla_tracks.remove(t)
if "jerry_mira_habla_arm" in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions["jerry_mira_habla_arm"])
OFF = math.radians(23)   # el vector scull->jaw_top.tail va ~23 grados por debajo de la direccion real del hocico
cara = lambda: alf.matrix_world @ alf.pose.bones["face_alfred"].head
def obj():
    h = rig.matrix_world @ pbs["scull"].head; d = cara() - h; L = d.length; hz = d.xy.length
    p = math.atan2(d.z, hz) - OFF; u = d.xy / hz
    return h + L * Vector((u.x * math.cos(p), u.y * math.cos(p), math.sin(p)))
def apuntar(nombre, frac, mx, f):
    pb = pbs[nombre]; base = pb.rotation_euler.copy(); R = base.to_matrix()
    P = pb.matrix.to_3x3() @ R.inverted()
    v = (pb.matrix.inverted() @ pbs["jaw_top"].tail).normalized()
    t = (P.inverted() @ (rig.matrix_world.inverted() @ obj() - pb.head)).normalized()
    q = (R @ v).normalized().rotation_difference(t)
    e = (Quaternion(q.axis, min(q.angle * frac, math.radians(mx)) * peso(f)).to_matrix() @ R).to_euler("XYZ", base)
    return (e.x - base.x, e.y - base.y, e.z - base.z)
for b in ("spine_1", "scull"): pbs[b].rotation_mode = "XYZ"
cuello = {}
for f in range(A, B + 1): sc.frame_set(f); cuello[f] = apuntar("spine_1", 0.85, 55, f)
keep = {b.name: b.rotation_euler.copy() for b in pbs}
ka = bpy.data.actions.new("jerry_mira_habla_arm"); rig.animation_data.action = ka
for f in range(A, B + 1):
    pbs["spine_1"].rotation_euler = cuello[f]; pbs["spine_1"].keyframe_insert("rotation_euler", frame=f)
slot = rig.animation_data.action_slot; rig.animation_data.action = None
for n, r in keep.items(): pbs[n].rotation_euler = r
tr = rig.animation_data.nla_tracks.new(); tr.name = "Jerry_mira_habla_arm"
st = tr.strips.new(ka.name, A, ka); st.action_slot = slot; st.blend_type = "ADD"; st.extrapolation = "NOTHING"
cra = {}
for f in range(A, B + 1): sc.frame_set(f); cra[f] = apuntar("scull", 1.0, 30, f)
cb = ka.layers[0].strips[0].channelbags[0]
for ax in range(3):
    fc = cb.fcurves.new('pose.bones["scull"].rotation_euler', index=ax)
    for f in range(A, B + 1): fc.keyframe_points.insert(f, cra[f][ax], options={"FAST"})
    fc.update()
for fc in cb.fcurves:
    for k in fc.keyframe_points: k.interpolation = "LINEAR"
# comprobar
import math as m
out = {}
for f in (104, 112, 120, 136, 150, 160, 168):
    sc.frame_set(f); M = rig.matrix_world
    a = M @ pbs["scull"].head; fw = M @ pbs["jaw_top"].tail - a; d = obj() - a
    dd = cara() - a
    out[f] = dict(err=round(m.degrees(fw.angle(d)), 1), pitch_hocico=round(m.degrees(m.atan2(fw.z, fw.xy.length)) + 23, 1), pitch_alfred=round(m.degrees(m.atan2(dd.z, dd.xy.length)), 1), scull=[round(m.degrees(x)) for x in pbs["scull"].matrix_basis.to_euler()],
                  sp1=[round(m.degrees(x)) for x in pbs["spine_1"].matrix_basis.to_euler()])
result = out
