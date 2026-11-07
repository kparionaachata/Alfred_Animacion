"""Jerry sigue con la mirada a Alfred desde que sale del agujero (f~714) mientras sigue echado, se levanta y camina hacia
el, hasta que empieza la mirada de 'sentado resignado' (f925). Capa ADD 'Jerry_sigue_alfred' (spine_1 + correccion de
scull), calculada SOBRE lo que ya hay (echado, caminata), con rampas suaves."""
import bpy, math
from mathutils import Quaternion, Vector
sc = bpy.context.scene
rig = bpy.data.objects["Dog_001_rig"]; pbs = rig.pose.bones; alf = bpy.data.objects["Armature"]
A, B, RAMPA = 712, 930, 8
NOMBRE = "Jerry_sigue_alfred"
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
w = lambda f: ss((f - A) / RAMPA) * (1 - ss((f - (B - RAMPA)) / RAMPA))
for t in list(rig.animation_data.nla_tracks):
    if t.name == NOMBRE: rig.animation_data.nla_tracks.remove(t)
if NOMBRE.lower() in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[NOMBRE.lower()])
OFF = math.radians(23)          # scull->jaw_top.tail va ~23 grados por debajo del hocico
cara = lambda: alf.matrix_world @ alf.pose.bones["face_alfred"].head
def obj():
    h = rig.matrix_world @ pbs["scull"].head; d = cara() - h; L = d.length; hz = max(1e-4, d.xy.length)
    p = math.atan2(d.z, hz) - OFF; u = d.xy / hz
    return h + L * Vector((u.x * math.cos(p), u.y * math.cos(p), math.sin(p)))
def apuntar(nombre, frac, mx, f):
    pb = pbs[nombre]; base = pb.rotation_euler.copy(); R = base.to_matrix()
    P = pb.matrix.to_3x3() @ R.inverted()
    v = (pb.matrix.inverted() @ pbs["jaw_top"].tail).normalized()
    t = (P.inverted() @ (rig.matrix_world.inverted() @ obj() - pb.head)).normalized()
    q = (R @ v).normalized().rotation_difference(t)
    e = (Quaternion(q.axis, min(q.angle * frac, math.radians(mx)) * w(f)).to_matrix() @ R).to_euler("XYZ", base)
    return (e.x - base.x, e.y - base.y, e.z - base.z)
for b in ("spine_1", "scull"): pbs[b].rotation_mode = "XYZ"
cu = {}
for f in range(A, B + 1): sc.frame_set(f); cu[f] = apuntar("spine_1", 0.85, 55, f)
keep = {b: pbs[b].rotation_euler.copy() for b in ("spine_1", "scull")}
act = bpy.data.actions.new(NOMBRE.lower()); prev = rig.animation_data.action; rig.animation_data.action = act
for f in range(A, B + 1): pbs["spine_1"].rotation_euler = cu[f]; pbs["spine_1"].keyframe_insert("rotation_euler", frame=f)
sl = rig.animation_data.action_slot; rig.animation_data.action = prev
for b, r in keep.items(): pbs[b].rotation_euler = r
tr = rig.animation_data.nla_tracks.new(); tr.name = NOMBRE
st = tr.strips.new(act.name, A, act); st.action_slot = sl; st.blend_type = "ADD"; st.extrapolation = "NOTHING"
co = {}
for f in range(A, B + 1): sc.frame_set(f); co[f] = apuntar("scull", 1.0, 30, f)
cb = act.layers[0].strips[0].channelbags[0]
for i in range(3):
    fc = cb.fcurves.new('pose.bones["scull"].rotation_euler', index=i)
    for f in range(A, B + 1): fc.keyframe_points.insert(f, co[f][i], options={"FAST"})
    fc.update()
for c in cb.fcurves:
    for k in c.keyframe_points: k.interpolation = "LINEAR"
err = []
for f in range(A + RAMPA, B - RAMPA + 1, 16):
    sc.frame_set(f); h = rig.matrix_world @ pbs["scull"].head; fw = rig.matrix_world @ pbs["jaw_top"].tail - h
    err.append((f, round(math.degrees(fw.angle(obj() - h)), 1)))
result = {"rango": (A, B), "error_mirada_grados": err}
