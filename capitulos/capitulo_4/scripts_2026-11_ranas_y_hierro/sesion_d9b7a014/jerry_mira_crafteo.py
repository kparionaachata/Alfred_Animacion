"""Jerry mira a Alfred mientras craftea la pala (parada f259-387): giro del cuerpo (pista ADD de la raiz) + cabeza
apuntada a la cara de Alfred + filtros organicos del jerry_animation_studio (valores por omision, como en la parte 7),
todo en pistas NLA ADD que se pueden quitar sin tocar nada mas."""
import bpy, math
from mathutils import Quaternion

A, B, RAMPA = 239, 366, 8
sc = bpy.context.scene
j = bpy.data.objects["jerry"]; rig = bpy.data.objects["Dog_001_rig"]; alf = bpy.data.objects["Armature"]
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
peso = lambda f: ss((f - A) / RAMPA) * (1 - ss((f - (B - RAMPA)) / RAMPA))


def noise_at(frame, freq, seed, dim=0):
    v = math.sin(frame * freq * 1.3 + seed * 7.3 + dim * 3.7) + math.sin(frame * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5 + math.sin(frame * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25
    return v / 1.75


def quitar(obj, track, accion):
    for t in list(obj.animation_data.nla_tracks):
        if t.name == track: obj.animation_data.nla_tracks.remove(t)
    if accion in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[accion])


def pista(obj, track, act, blend="ADD"):
    slot = obj.animation_data.action_slot; obj.animation_data.action = None
    t = obj.animation_data.nla_tracks.new(); t.name = track
    s = t.strips.new(act.name, A, act); s.action_slot = slot
    s.blend_type = blend; s.extrapolation = "NOTHING"
    return t


def objetivo():
    return alf.matrix_world @ alf.pose.bones["face_alfred"].head


quitar(j, "Jerry_mira_crafteo_root", "jerry_mira_crafteo_root")
quitar(rig, "Jerry_mira_crafteo_arm", "jerry_mira_crafteo_arm")

# 1) raiz de la espera en (-6.5,-5.5): quieta, girando el cuerpo hacia Alfred
sc.frame_set(A - 1)
loc0 = j.matrix_world.translation.copy(); e0 = j.matrix_world.to_euler("XYZ")
r0, l0 = j.rotation_euler.copy(), j.location.copy()
ra = bpy.data.actions.new("jerry_mira_crafteo_root"); j.animation_data.action = ra
j.rotation_mode = "XYZ"
for f in range(A, B + 1):
    j.location = loc0; j.rotation_euler = e0
    j.keyframe_insert("location", frame=f); j.keyframe_insert("rotation_euler", frame=f)
pista(j, "Jerry_mira_crafteo_root", ra, "REPLACE")
yaw = {}
for f in range(A, B + 1):
    sc.frame_set(f)
    h = rig.matrix_world @ rig.pose.bones["scull"].head; n = rig.matrix_world @ rig.pose.bones["jaw_top"].tail
    p = j.matrix_world.translation.xy                     # el cuerpo gira sobre la raiz: la cabeza se desplaza con el giro
    r_, d_, T = (h.xy - p), (n - h).xy.normalized(), objetivo().xy - p
    mejor = (9.0, 0.0)
    for i in range(-360, 361):
        th = math.radians(i * 0.5); c_, s_ = math.cos(th), math.sin(th)
        rd = (c_ * d_.x - s_ * d_.y, s_ * d_.x + c_ * d_.y); rh = (c_ * r_.x - s_ * r_.y, s_ * r_.x + c_ * r_.y)
        tx, ty = T.x - rh[0], T.y - rh[1]
        err = abs(math.atan2(rd[0] * ty - rd[1] * tx, rd[0] * tx + rd[1] * ty))
        if err < mejor[0] - 1e-9 or (abs(err - mejor[0]) < 1e-9 and abs(th) < abs(mejor[1])): mejor = (err, th)
    yaw[f] = mejor[1]
fcz = next(fc for l in ra.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves if fc.data_path == "rotation_euler" and fc.array_index == 2)
for k in fcz.keyframe_points:
    f = round(k.co.x); k.co.y = e0.z + yaw[f] * peso(f); k.interpolation = "LINEAR"
fcz.update()
j.rotation_euler, j.location = r0, l0

# 2) mirada: spine_1 (cuello) levanta y gira la cabeza; scull solo corrige lo que falta
def apuntar(nombre, frac, max_grados, f):
    pb = rig.pose.bones[nombre]; base = pb.rotation_euler.copy(); R = base.to_matrix()
    P = pb.matrix.to_3x3() @ R.inverted()
    v = (pb.matrix.inverted() @ rig.pose.bones["jaw_top"].tail).normalized()
    t = (P.inverted() @ (rig.matrix_world.inverted() @ objetivo() - pb.head)).normalized()
    q = (R @ v).normalized().rotation_difference(t)
    e = (Quaternion(q.axis, min(q.angle * frac, math.radians(max_grados)) * peso(f)).to_matrix() @ R).to_euler("XYZ", base)
    return (e.x - base.x, e.y - base.y, e.z - base.z)


look_cuello = {}
for f in range(A, B + 1):
    sc.frame_set(f); look_cuello[f] = apuntar("spine_1", 0.85, 55, f)

ka = bpy.data.actions.new("jerry_mira_crafteo_arm"); rig.animation_data.action = ka
pbs = rig.pose.bones
keep = {b.name: (b.rotation_euler.copy(), b.scale.copy()) for b in pbs}
for b in ("scull", "spine_1", "front_shoulder.R", "front_shoulder.L", "ear.L", "ear.R", "tail_2"): pbs[b].rotation_mode = "XYZ"
for f in range(A, B + 1):
    w = peso(f)
    sp = [0.0, 0.0, 0.0]
    sp[0] = 0.05 * math.sin(f * 0.01 * 2 * math.pi); sp[2] = 0.05 * 0.4 * math.sin(f * 0.01 * 2 * math.pi + 1.2)   # respiracion
    for ax in range(3): sp[ax] += 0.008 * noise_at(f, 0.05, 42, ax)                                                   # micro-movimiento
    pbs["spine_1"].rotation_euler = [x * w + look_cuello[f][i] for i, x in enumerate(sp)]; pbs["spine_1"].keyframe_insert("rotation_euler", frame=f)
    pbs["spine_1"].scale = (0.0, 0.0, 0.005 * math.sin(f * 0.01 * 2 * math.pi) * w); pbs["spine_1"].keyframe_insert("scale", frame=f)
    for b, off in (("front_shoulder.R", 0), ("front_shoulder.L", 17)):
        pbs[b].rotation_euler = [0.006 * noise_at(f, 0.07, 123 + off, ax) * w for ax in range(3)]; pbs[b].keyframe_insert("rotation_euler", frame=f)
    for b, fase in (("ear.L", 0.0), ("ear.R", 1.57)):
        pbs[b].rotation_euler = (0.0, 0.0, 0.12 * math.sin(f * 0.06 * 2 * math.pi + fase) * w); pbs[b].keyframe_insert("rotation_euler", frame=f)
    pbs["tail_2"].rotation_euler = (0.0, 0.0, 0.524 * 0.35 * math.sin(f * 0.12 * 2 * math.pi) * w); pbs["tail_2"].keyframe_insert("rotation_euler", frame=f)
for fc in [fc for l in ka.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]:
    for k in fc.keyframe_points: k.interpolation = "LINEAR"
pista(rig, "Jerry_mira_crafteo_arm", ka)
for n, (r, s) in keep.items(): pbs[n].rotation_euler, pbs[n].scale = r, s

# correccion final con scull (con el cuello ya levantado)
look = {}
for f in range(A, B + 1):
    sc.frame_set(f); look[f] = apuntar("scull", 1.0, 30, f)
cb = ka.layers[0].strips[0].channelbags[0]
for ax in range(3):
    fc = cb.fcurves.find('pose.bones["scull"].rotation_euler', index=ax) or cb.fcurves.new('pose.bones["scull"].rotation_euler', index=ax)
    for f in range(A, B + 1):
        k = fc.keyframe_points.insert(f, look[f][ax], options={"FAST"}); k.interpolation = "LINEAR"
    fc.update()

# pasitos al girar y al volver
ed = sc.sequence_editor
plantilla = next(s for s in ed.strips_all if s.name.startswith("SND_paso_jerry_105"))
for f, ch in ((A + 1, 20), (A + 4, 21), (B - 7, 20), (B - 4, 21)):
    nm = "SND_paso_jerry_mira_%d" % f
    if nm in ed.strips_all: ed.strips.remove(ed.strips_all[nm])
    x = ed.strips.new_sound(nm, plantilla.sound.filepath, ch, f); x.volume = plantilla.volume * 0.8
result = {"giro_cuerpo_grados": [round(math.degrees(yaw[f])) for f in (A + 10, 300, 357)]}
