"""Cada vez que Alfred habla con Jerry, lo sigue con la cabeza: pista NLA ADD 'Alfred_mira_jerry_voz' (reemplaza la de
348-421) sobre Spine2/Neck/face_alfred, en las ventanas de sus voces (VozSync_alfred_*, con margen y rampa). Cada hueso
corrige parte del angulo que falta (re-evaluando la escena) para que el frente de face_alfred apunte a la cabeza de
Jerry, que va caminando. Durante el crafteo (desde ~228) se apunta 0.9 m por encima de la cabeza de Jerry para que el
brazo no le tape la cara (como antes)."""
import bpy, math
from mathutils import Quaternion, Vector

sc = bpy.context.scene; ed = sc.sequence_editor
arm = bpy.data.objects["Armature"]; rig = bpy.data.objects["Dog_001_rig"]
PISTA = "Alfred_mira_jerry_voz"; RAMPA = 6; ANTES, DESPUES = 4, 4
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
voces = sorted((s.frame_final_start, s.frame_final_end) for s in ed.strips_all if s.name.startswith("VozSync_alfred"))
ventanas = []
for a, b in voces:
    a, b = a - ANTES, b + DESPUES
    if ventanas and a - ventanas[-1][1] < 2 * RAMPA + 4: ventanas[-1] = (ventanas[-1][0], b)   # voces seguidas: no suelta la mirada
    else: ventanas.append((a, b))
def peso(f):
    return max([ss((f - a) / RAMPA) * (1 - ss((f - (b - RAMPA)) / RAMPA)) for a, b in ventanas] + [0.0])
alto = lambda f: 0.9 * ss((f - 222) / 14.0)
HUESOS = (("Spine2_alfred", 0.35, 35), ("Neck_alfred", 0.55, 45), ("face_alfred", 1.0, 60))

for t in list(arm.animation_data.nla_tracks):
    if t.name == PISTA: arm.animation_data.nla_tracks.remove(t)
if PISTA.lower() in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[PISTA.lower()])
act = bpy.data.actions.new(PISTA.lower()); prev = arm.animation_data.action; arm.animation_data.action = act
keep = {n: arm.pose.bones[n].rotation_euler.copy() for n, _, _ in HUESOS}
F0, F1 = ventanas[0][0], ventanas[-1][1]
for n, _, _ in HUESOS:
    arm.pose.bones[n].rotation_euler = (0, 0, 0)
    for f in (F0, F1): arm.pose.bones[n].keyframe_insert("rotation_euler", frame=f)
slot = arm.animation_data.action_slot; arm.animation_data.action = prev
for n, r in keep.items(): arm.pose.bones[n].rotation_euler = r
tr = arm.animation_data.nla_tracks.new(); tr.name = PISTA
st = tr.strips.new(act.name, F0, act); st.action_slot = slot; st.blend_type = "ADD"; st.extrapolation = "NOTHING"
cb = act.layers[0].strips[0].channelbags[0]
frames = [f for a, b in ventanas for f in range(a, b + 1)]
for nombre, frac, maxg in HUESOS:
    d = {}
    for f in frames:
        sc.frame_set(f)
        pb = arm.pose.bones[nombre]; base = pb.rotation_euler.copy(); R = base.to_matrix()
        P = pb.matrix.to_3x3() @ R.inverted()
        cara = arm.pose.bones["face_alfred"]
        v = (pb.matrix.to_3x3().inverted() @ cara.matrix.col[2].xyz.normalized()).normalized()
        obj = arm.matrix_world.inverted() @ (rig.matrix_world @ rig.pose.bones["scull"].head + Vector((0, 0, alto(f))))
        t = (P.inverted() @ (obj - cara.head)).normalized()
        q = (R @ v).normalized().rotation_difference(t)
        e = (Quaternion(q.axis, min(q.angle * frac, math.radians(maxg)) * peso(f)).to_matrix() @ R).to_euler("XYZ", base)
        d[f] = (e.x - base.x, e.y - base.y, e.z - base.z)
    for ax in range(3):
        fc = cb.fcurves.find(f'pose.bones["{nombre}"].rotation_euler', index=ax)
        for a, b in ventanas:                       # ceros justo fuera de cada ventana
            for f in (a - 1, b + 1): fc.keyframe_points.insert(f, 0.0, options={"FAST"})
        for f in frames: fc.keyframe_points.insert(f, d[f][ax], options={"FAST"})
        for k in fc.keyframe_points: k.interpolation = "LINEAR"
        fc.update()
err = []
for a, b in ventanas:
    for f in range(a + RAMPA, b - RAMPA + 1, 12):
        sc.frame_set(f); cara = arm.pose.bones["face_alfred"]
        fw = arm.matrix_world.to_3x3() @ cara.matrix.col[2].xyz
        h = arm.matrix_world @ cara.head; j = rig.matrix_world @ rig.pose.bones["scull"].head + Vector((0, 0, alto(f)))
        err.append((f, round(math.degrees(fw.angle(j - h)))))
result = {"ventanas": ventanas, "error_mirada_grados": err}
