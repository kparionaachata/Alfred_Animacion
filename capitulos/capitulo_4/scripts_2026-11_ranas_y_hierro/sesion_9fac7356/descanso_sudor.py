"""f90-150: Alfred se endereza y descansa con la pala en la mano derecha (pasa a la mano con los valores de la skill
herramienta-mano-derecha) y con la mano izquierda se seca el sudor de la frente: sube la mano, la pasa por la frente de
izquierda a derecha, sacude la mano hacia abajo y la baja; respira hondo (pecho y hombros)."""
import bpy, math
from mathutils import Vector, Matrix, Quaternion, Euler
sc = bpy.context.scene
al = bpy.data.objects["Armature"]; pb = al.pose.bones; pala = bpy.data.objects["stone_shovel"]
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
F0, FIN = 90, 150
act = al.animation_data.action; cb = act.layers[0].strips[0].channelbag(al.animation_data.action_slot)
UP = Vector((0, 0, 1))
def valor_f1(bn):
    return Euler([cb.fcurves.find('pose.bones["%s"].rotation_euler' % bn, index=i).evaluate(1) if cb.fcurves.find('pose.bones["%s"].rotation_euler' % bn, index=i) else pb[bn].rotation_euler[i] for i in range(3)])
BASE = {bn: valor_f1(bn) for bn in ("RightUpArm_alfred", "Rightelbow_alfred", "LeftUpArm_alfred", "Leftelbow_alfred",
                                     "Spine1_alfred", "Spine2_alfred", "Neck_alfred", "face_alfred")}
def key(bn, e, f):
    ref = pb[bn].rotation_euler.copy(); pb[bn].rotation_euler = Euler(e).to_quaternion().to_euler("XYZ", ref)
    pb[bn].keyframe_insert("rotation_euler", frame=f)
sc.frame_set(F0)
pala_f90 = pala.matrix_world.copy()
# ---------- se endereza: torso, cabeza y brazo derecho a su pose de descanso ----------
for bn in ("Spine1_alfred", "Spine2_alfred", "Neck_alfred", "face_alfred", "RightUpArm_alfred", "Rightelbow_alfred", "LeftUpArm_alfred", "Leftelbow_alfred"):
    sc.frame_set(F0); key(bn, pb[bn].rotation_euler.copy(), F0)
    key(bn, BASE[bn], 104)
for bn in ("RightUpArm_alfred", "Rightelbow_alfred"): key(bn, BASE[bn], FIN)
# respiracion honda de descanso (pecho sube y baja, cabeza acompana)
for i, f in enumerate(range(104, FIN + 1, 8)):
    k = 1.0 if i % 2 else -0.4
    e = BASE["Spine2_alfred"].copy(); e.x -= math.radians(3.0) * k; key("Spine2_alfred", e, f)
    e = BASE["Spine1_alfred"].copy(); e.x -= math.radians(1.5) * k; key("Spine1_alfred", e, f)
# ---------- la pala pasa a la mano derecha (valores fijos de la skill) ----------
Lfix = Matrix.LocRotScale(Vector((0.21937, 0.32673, -0.001575)), Euler([math.radians(d) for d in (7.9831, 17.876, -56.916)]).to_quaternion(), Vector((0.82,) * 3))
pact = pala.animation_data.action; pcb = pact.layers[0].strips[0].channelbag(pala.animation_data.action_slot)
for fc in pcb.fcurves:
    for k in [k for k in fc.keyframe_points if k.co.x > F0][::-1]: fc.keyframe_points.remove(k)
for f in range(F0 + 1, FIN + 1):
    sc.frame_set(f)
    mano = al.matrix_world @ pb["Rightelbow_alfred"].matrix @ Lfix
    w = ss((f - F0) / 14.0)
    l = pala_f90.translation.lerp(mano.translation, w); q = pala_f90.to_quaternion().slerp(mano.to_quaternion(), w)
    pala.matrix_world = Matrix.LocRotScale(l, q, mano.to_scale())
    pala.keyframe_insert("location", frame=f); pala.keyframe_insert("rotation_euler", frame=f)
for fc in pcb.fcurves:
    if fc.data_path == "rotation_euler":
        prev = None
        for k in sorted(fc.keyframe_points, key=lambda k: k.co.x):
            if prev is not None:
                while k.co.y - prev > math.pi: k.co.y -= 2 * math.pi
                while k.co.y - prev < -math.pi: k.co.y += 2 * math.pi
            prev = k.co.y
        fc.update()
# ---------- mano izquierda: secarse el sudor (IK con polo en unas pocas claves) ----------
sc.frame_set(110)
cara = pb["face_alfred"]; Mc = al.matrix_world @ cara.matrix
adelante = Mc.to_3x3().col[2].normalized(); arriba = Mc.to_3x3().col[1].normalized()
der = adelante.cross(arriba).normalized()
if der.dot((al.matrix_world @ pb["RightUpArm_alfred"].head) - (al.matrix_world @ pb["LeftUpArm_alfred"].head)) < 0: der = -der
frente = Mc.translation + adelante * 0.30 + arriba * 0.16
PALMA = Vector((-0.033, 0.312, -0.005))
emp = bpy.data.objects.new("_ik_sudor", None); polo = bpy.data.objects.new("_polo_sudor", None)
sc.collection.objects.link(emp); sc.collection.objects.link(polo)
ik = pb["Leftelbow_alfred"].constraints.new("IK"); ik.name = "_IK_sudor"; ik.target = emp; ik.pole_target = polo; ik.chain_count = 2; ik.use_tail = True
CLAVES = [(110, frente - der * 0.16 + adelante * 0.02),      # mano en el lado izquierdo de la frente
          (113, frente - der * 0.12),
          (118, frente + der * 0.02 + arriba * 0.01),         # pasa por la frente
          (123, frente + der * 0.16 - arriba * 0.01),         # hasta el lado derecho
          (127, frente + der * 0.10 + adelante * 0.20 - arriba * 0.10),   # se aparta
          (130, frente - der * 0.05 + adelante * 0.30 - arriba * 0.45)]   # sacude la mano hacia abajo
palma = lambda: (al.matrix_world @ pb["Leftelbow_alfred"].matrix) @ PALMA
errs = {}
mejor_ang = None
for f, obj in CLAVES:
    sc.frame_set(f)
    h = al.matrix_world @ pb["LeftUpArm_alfred"].head
    polo.location = h - der * 0.5 - arriba * 0.25 - adelante * 0.05
    if mejor_ang is None:
        best = None
        for a_ in (0, 90, -90, 180):
            ik.pole_angle = math.radians(a_); emp.location = obj; bpy.context.view_layer.update()
            d = (al.matrix_world @ pb["Leftelbow_alfred"].head - polo.location).length
            if best is None or d < best[0]: best = (d, a_)
        mejor_ang = best[1]; ik.pole_angle = math.radians(mejor_ang)
    emp.location = obj + (al.matrix_world @ pb["Leftelbow_alfred"].tail - palma())
    er = 9; paso = 0.9
    for _ in range(14):
        bpy.context.view_layer.update(); e2 = (obj - palma()).length
        if e2 < 0.004: er = e2; break
        if e2 < er: er = e2; emp.location = emp.location + (obj - palma()) * paso
        else: paso *= 0.5; emp.location = emp.location - (obj - palma()) * paso
    bpy.context.view_layer.update()
    rots = {bn: al.convert_space(pose_bone=pb[bn], matrix=pb[bn].matrix, from_space="POSE", to_space="LOCAL").to_euler("XYZ", pb[bn].rotation_euler) for bn in ("LeftUpArm_alfred", "Leftelbow_alfred")}
    ik.mute = True
    for bn, r in rots.items(): pb[bn].rotation_euler = r; pb[bn].keyframe_insert("rotation_euler", frame=f)
    bpy.context.view_layer.update(); errs[f] = round((obj - palma()).length * 100, 1)
    ik.mute = False
pb["Leftelbow_alfred"].constraints.remove(ik); bpy.data.objects.remove(emp); bpy.data.objects.remove(polo)
for bn in ("LeftUpArm_alfred", "Leftelbow_alfred"): key(bn, BASE[bn], 140); key(bn, BASE[bn], FIN)
# cabeza: baja un poco al llevar la mano y se levanta al pasarla (alivio)
for f, inc in ((106, 0), (110, 6), (118, -4), (124, -6), (132, 2), (142, 0)):
    e = BASE["face_alfred"].copy(); e.x += math.radians(inc); key("face_alfred", e, f)
# claves suaves (BEZIER) en lo nuevo
for fc in cb.fcurves:
    for k in fc.keyframe_points:
        if k.co.x > F0: k.interpolation = "BEZIER"; k.handle_left_type = k.handle_right_type = "AUTO_CLAMPED"
    fc.update()
sc.frame_end = FIN; sc.frame_set(118)
result = {"error_mano_izq_cm": errs, "fin": FIN}
