"""Jerry se detiene en f110, gira hacia Alfred (110-118), habla (110-155), vuelve a girar (156-164) y sigue
su caminata (accion 110-204 -> 164-258). La parada 205-387 pasa a 259-387. Pasos y mira_pozo desplazados."""
import bpy, math

T0, T1, T2, T3 = 110, 118, 156, 164
D = T3 - T0
sc = bpy.context.scene
j = bpy.data.objects["jerry"]; rig = bpy.data.objects["Dog_001_rig"]; alf = bpy.data.objects["Armature"]
jt, rt = j.animation_data.nla_tracks, rig.animation_data.nla_tracks


def smooth(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def partir(track):
    s = track.strips[0]
    act = s.action
    s.action_frame_end = T0                  # recalcula el final de la tira (98-110)
    s.extrapolation = "HOLD_FORWARD"
    b = track.strips.new(s.name + "_B", T3, act)
    b.action_slot = s.action_slot
    b.action_frame_start = T0                # 164-258
    b.extrapolation = "HOLD_FORWARD" if track.name.endswith("_root") else "NOTHING"
    return s, b


# 1) caminata partida
partir(jt["Slot_014_root"]); partir(rt["Slot_014_arm"])
for tr in (jt["Slot_015_parada_root"], rt["Slot_015_parada_arm"]):
    s = tr.strips[0]
    s.action_frame_end = 387 - D             # misma accion, tira mas corta
    s.frame_start_ui = 205 + D               # mover la tira entera: 259-387

# 2) raiz de la parada-giro
sc.frame_set(T0)
loc0 = j.matrix_world.translation.copy(); e0 = j.matrix_world.to_euler("XYZ")
rz0 = e0.z
for t in list(jt):
    if t.name == "Jerry_para_habla_root": jt.remove(t)
for t in list(rt):
    if t.name == "Jerry_para_habla_arm": rt.remove(t)
for n in ("jerry_para_habla_root", "jerry_para_habla_arm"):
    if n in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[n])


def objetivo(f):
    sc.frame_set(f)
    h = alf.matrix_world @ alf.pose.bones["face_alfred"].head
    d = h - loc0
    rz = math.atan2(d.y, d.x) - math.pi / 2         # frente de Jerry = rz + 90
    while rz - rz0 > math.pi: rz -= 2 * math.pi
    while rz - rz0 < -math.pi: rz += 2 * math.pi
    return rz


rzs = {f: objetivo(f) for f in range(T0, T3 + 1)}
ra = bpy.data.actions.new("jerry_para_habla_root")
j.animation_data.action = ra
for f in range(T0, T3 + 1):
    if f <= T1: w = smooth((f - T0) / (T1 - T0))
    elif f >= T2: w = 1 - smooth((f - T2) / (T3 - T2))
    else: w = 1.0
    j.location = loc0
    j.rotation_euler = (e0.x, e0.y, rz0 + (rzs[f] - rz0) * w)
    j.keyframe_insert("location", frame=f); j.keyframe_insert("rotation_euler", frame=f)
slot = j.animation_data.action_slot; j.animation_data.action = None
tr = jt.new(); tr.name = "Jerry_para_habla_root"
s = tr.strips.new("jerry_para_habla_root", T0, ra); s.action_slot = slot
s.extrapolation = "NOTHING"

# 3) pose de parada durante el giro/habla (idle de la parada 205+)
pa = rt["Slot_015_parada_arm"].strips[0].action
tr = rt.new(); tr.name = "Jerry_para_habla_arm"
s = tr.strips.new("jerry_para_habla_arm", T0, pa)
s.action_slot = rt["Slot_015_parada_arm"].strips[0].action_slot
s.action_frame_start = 205; s.action_frame_end = 205 + D
s.extrapolation = "NOTHING"; s.blend_in = 3; s.blend_out = 3

# 4) mira_pozo empieza cuando Jerry ya esta parado
pz = rt["Jerry_mira_pozo"].strips[0]
for l in pz.action.layers:
    for st in l.strips:
        for cb in st.channelbags:
            for fc in cb.fcurves:
                for k in fc.keyframe_points:
                    if round(k.co.x) == 213: k.co.x += D; k.handle_left.x += D; k.handle_right.x += D
                    elif round(k.co.x) == 220: k.co.x += D; k.handle_left.x += D; k.handle_right.x += D
                fc.update()
rt["Jerry_busca_habla"].mute = True

# 5) pasos de Jerry: los de la caminata despues de f110 se desplazan; pasitos al girar
ed = sc.sequence_editor
mov = [s for s in ed.strips_all if s.name.startswith("SND_paso_jerry_") and T0 <= s.frame_final_start <= 213]
for s in sorted(mov, key=lambda s: -s.frame_start):
    s.frame_start += D
plantilla = next(s for s in ed.strips_all if s.name.startswith("SND_paso_jerry_105"))
for f, ch in ((112, 20), (115, 21), (158, 20), (161, 21)):
    n = "SND_paso_jerry_giro_%d" % f
    if n in ed.strips_all: ed.strips.remove(ed.strips_all[n])
    x = ed.strips.new_sound(n, plantilla.sound.filepath, ch, f)
    x.volume = plantilla.volume * 0.8
result = {"movidos": len(mov), "rz0": math.degrees(rz0), "rz_obj": [round(math.degrees(rzs[f])) for f in (T1, 135, T2)]}
