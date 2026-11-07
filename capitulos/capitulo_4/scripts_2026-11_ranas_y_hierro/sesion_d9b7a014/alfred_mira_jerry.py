"""Alfred mira a Jerry mientras habla (A-B): pista NLA ADD sobre Spine2/Neck/face_alfred. Cada hueso corrige una
parte del angulo que falta (en orden, re-evaluando la escena) para que el eje Z de face_alfred (su frente) apunte
a la cabeza de Jerry; limites por hueso para no romper el cuello. Se suma encima del crafteo y de la caminata."""
import bpy, math
from mathutils import Quaternion, Vector

A = globals().get("A", 348); B = globals().get("B", 421); RAMPA = 8
ALTO = globals().get("ALTO", 0.0)          # metros por encima de la cabeza de Jerry: levanta la mirada de Alfred
PISTA = "Alfred_mira_jerry_voz"
sc = bpy.context.scene
arm = bpy.data.objects["Armature"]; rig = bpy.data.objects["Dog_001_rig"]
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
peso = lambda f: ss((f - A) / RAMPA) * (1 - ss((f - (B - RAMPA)) / RAMPA))
HUESOS = (("Spine2_alfred", 0.35, 35), ("Neck_alfred", 0.55, 45), ("face_alfred", 1.0, 60))

for t in list(arm.animation_data.nla_tracks):
    if t.name == PISTA: arm.animation_data.nla_tracks.remove(t)
if PISTA.lower() in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[PISTA.lower()])
act = bpy.data.actions.new(PISTA.lower())
arm.animation_data.action = act
keep = {n: arm.pose.bones[n].rotation_euler.copy() for n, _, _ in HUESOS}
for n, _, _ in HUESOS:
    arm.pose.bones[n].rotation_euler = (0, 0, 0)
    for f in (A, B): arm.pose.bones[n].keyframe_insert("rotation_euler", frame=f)
slot = arm.animation_data.action_slot; arm.animation_data.action = None
for n, r in keep.items(): arm.pose.bones[n].rotation_euler = r
tr = arm.animation_data.nla_tracks.new(); tr.name = PISTA
st = tr.strips.new(act.name, A, act); st.action_slot = slot; st.blend_type = "ADD"; st.extrapolation = "NOTHING"
cb = act.layers[0].strips[0].channelbags[0]

rep = {}
for nombre, frac, maxg in HUESOS:
    d = {}
    for f in range(A, B + 1):
        sc.frame_set(f)
        pb = arm.pose.bones[nombre]; base = pb.rotation_euler.copy(); R = base.to_matrix()
        P = pb.matrix.to_3x3() @ R.inverted()
        cara = arm.pose.bones["face_alfred"]
        fwd_arm = cara.matrix.col[2].xyz.normalized()                       # frente de Alfred (eje Z de face_alfred)
        v = (pb.matrix.to_3x3().inverted() @ fwd_arm).normalized()
        obj = arm.matrix_world.inverted() @ (rig.matrix_world @ rig.pose.bones["scull"].head + Vector((0, 0, ALTO)))
        t = (P.inverted() @ (obj - cara.head)).normalized()
        q = (R @ v).normalized().rotation_difference(t)
        e = (Quaternion(q.axis, min(q.angle * frac, math.radians(maxg)) * peso(f)).to_matrix() @ R).to_euler("XYZ", base)
        d[f] = (e.x - base.x, e.y - base.y, e.z - base.z)
    for ax in range(3):
        fc = cb.fcurves.find(f'pose.bones["{nombre}"].rotation_euler', index=ax)
        for f in range(A, B + 1):
            k = fc.keyframe_points.insert(f, d[f][ax], options={"FAST"}); k.interpolation = "LINEAR"
        fc.update()
    rep[nombre] = round(max(math.degrees(math.sqrt(sum(x * x for x in v))) for v in d.values()))

err = []
for f in range(A, B + 1, 8):
    sc.frame_set(f)
    cara = arm.pose.bones["face_alfred"]
    fw = (arm.matrix_world.to_3x3() @ cara.matrix.col[2].xyz)
    h = arm.matrix_world @ cara.head; j = rig.matrix_world @ rig.pose.bones["scull"].head
    err.append((f, round(math.degrees(fw.angle(j - h)))))
result = {"max_grados_por_hueso": rep, "error_mirada": err}
