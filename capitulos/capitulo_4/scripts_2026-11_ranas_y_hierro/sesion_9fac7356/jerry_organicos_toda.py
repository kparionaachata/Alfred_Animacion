"""Filtros organicos del jerry_animation_studio (valores por omision) en TODA la animacion de Jerry (f1-fin), como pista
NLA ADD 'Jerry_organicos' encima de todo: respiracion (spine_1 rot + escala Z), micro-movimiento (ruido), hombros
delanteros, orejas y cola. En f239-366 ya los tiene 'Jerry_mira_crafteo_arm': ahi el peso es el complemento de esa
rampa para no sumarlos dos veces. No suaviza fcurves (no toca claves existentes)."""
import bpy, math
sc = bpy.context.scene
rig = bpy.data.objects["Dog_001_rig"]; pbs = rig.pose.bones; ad = rig.animation_data
F0, F1 = 1, sc.frame_end
A, B, RAMPA = 239, 366, 8                       # ventana de Jerry_mira_crafteo_arm (ya con filtros)
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
peso = lambda f: 1.0 - ss((f - A) / RAMPA) * (1 - ss((f - (B - RAMPA)) / RAMPA))


def noise_at(frame, freq, seed, dim=0):
    v = (math.sin(frame * freq * 1.3 + seed * 7.3 + dim * 3.7) + math.sin(frame * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5
         + math.sin(frame * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25)
    return v / 1.75


for t in list(ad.nla_tracks):
    if t.name == "Jerry_organicos": ad.nla_tracks.remove(t)
if "jerry_organicos" in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions["jerry_organicos"])
HUESOS = ("spine_1", "front_shoulder.R", "front_shoulder.L", "ear.L", "ear.R", "tail_2")
keep = {b: (pbs[b].rotation_mode, pbs[b].rotation_euler.copy(), pbs[b].scale.copy()) for b in HUESOS}
prev = ad.action; act = bpy.data.actions.new("jerry_organicos"); ad.action = act
for b in HUESOS: pbs[b].rotation_mode = "XYZ"
for f in range(F0, F1 + 1):
    w = peso(f)
    sp = [0.05 * math.sin(f * 0.01 * 2 * math.pi), 0.0, 0.05 * 0.4 * math.sin(f * 0.01 * 2 * math.pi + 1.2)]   # respiracion
    for ax in range(3): sp[ax] += 0.008 * noise_at(f, 0.05, 42, ax)                                          # micro-movimiento
    pbs["spine_1"].rotation_euler = [x * w for x in sp]; pbs["spine_1"].keyframe_insert("rotation_euler", frame=f)
    pbs["spine_1"].scale = (0.0, 0.0, 0.005 * math.sin(f * 0.01 * 2 * math.pi) * w); pbs["spine_1"].keyframe_insert("scale", frame=f)
    for b, off in (("front_shoulder.R", 0), ("front_shoulder.L", 17)):
        pbs[b].rotation_euler = [0.006 * noise_at(f, 0.07, 123 + off, ax) * w for ax in range(3)]; pbs[b].keyframe_insert("rotation_euler", frame=f)
    for b, fase in (("ear.L", 0.0), ("ear.R", 1.57)):
        pbs[b].rotation_euler = (0.0, 0.0, 0.12 * math.sin(f * 0.06 * 2 * math.pi + fase) * w); pbs[b].keyframe_insert("rotation_euler", frame=f)
    pbs["tail_2"].rotation_euler = (0.0, 0.0, 0.524 * 0.35 * math.sin(f * 0.12 * 2 * math.pi) * w); pbs["tail_2"].keyframe_insert("rotation_euler", frame=f)
for c in act.layers[0].strips[0].channelbags[0].fcurves:
    for k in c.keyframe_points: k.interpolation = "LINEAR"
sl = ad.action_slot; ad.action = prev
for b, (rm, r, s) in keep.items(): pbs[b].rotation_mode = rm; pbs[b].rotation_euler = r; pbs[b].scale = s
tr = ad.nla_tracks.new(); tr.name = "Jerry_organicos"
st = tr.strips.new(act.name, F0, act); st.action_slot = sl; st.blend_type = "ADD"; st.extrapolation = "NOTHING"
result = {"rango": (F0, F1), "huesos": HUESOS, "pista": tr.name}
