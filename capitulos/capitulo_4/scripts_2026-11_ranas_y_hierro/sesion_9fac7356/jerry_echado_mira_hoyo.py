"""Jerry se echa (pose de la biblioteca de poses del jerry_animation_studio, por omision 'hechado_mirando_al_frente':
boca abajo, patas delanteras al frente, cabeza en alto) y mira el hoyo donde esta Alfred mientras espera; se levanta
justo antes de arrancar hacia Alfred (f790). Capas ADD (deltas = pose_echado - pose_base), para no tapar la voz/cara ni
los filtros organicos que estan en otras capas ADD. Giro del cuerpo hacia el hoyo en la raiz si hace falta."""
import bpy, json, math
from mathutils import Quaternion, Vector, Euler
sc = bpy.context.scene
POSE = globals().get("POSE", "hechado_mirando_al_frente.json")
RUTA = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\jerry\refinar\poses" + "\\" + POSE
A, A1 = 598, 614              # se echa
B0, B = 772, 789              # se levanta (f790 arranca el salto de bajada hacia Alfred)
j = bpy.data.objects["jerry"]; rig = bpy.data.objects["Dog_001_rig"]; pbs = rig.pose.bones
alf = bpy.data.objects["Armature"]
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
w = lambda f: ss((f - A) / (A1 - A)) * (1 - ss((f - B0) / (B - B0)))
for o, nm in ((rig, "Jerry_echado_arm"), (rig, "Jerry_echado_mira"), (j, "Jerry_echado_root")):
    for t in list(o.animation_data.nla_tracks):
        if t.name == nm: o.animation_data.nla_tracks.remove(t)
    if nm.lower() in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[nm.lower()])

pose = json.load(open(RUTA, encoding="utf-8"))["poses"][0]["bones"]
# pose base (sin capas ADD) en los extremos
adds = [t for t in rig.animation_data.nla_tracks if any(s.blend_type == "ADD" for s in t.strips) and not t.mute]
for t in adds: t.mute = True
base = {}
for f in (A, B):
    sc.frame_set(f)
    base[f] = {n: (pbs[n].rotation_euler.copy(), pbs[n].location.copy(), pbs[n].scale.copy()) for n in pose if n in pbs}
for t in adds: t.mute = False

def a_pista(obj, act, nombre, inicio):
    sl = obj.animation_data.action_slot; obj.animation_data.action = None
    tr = obj.animation_data.nla_tracks.new(); tr.name = nombre
    st = tr.strips.new(act.name, inicio, act); st.action_slot = sl; st.blend_type = "ADD"; st.extrapolation = "NOTHING"

keep = {n: (pbs[n].rotation_mode, pbs[n].rotation_euler.copy(), pbs[n].location.copy(), pbs[n].scale.copy()) for n in base[A]}
act = bpy.data.actions.new("jerry_echado_arm"); prev = rig.animation_data.action; rig.animation_data.action = act
for n in base[A]: pbs[n].rotation_mode = "XYZ"
for f in range(A - 1, B + 2):
    k = w(f); ref = base[A] if f < (A1 + B0) / 2 else base[B]
    for n, d in pose.items():
        if n not in pbs: continue
        ls = d["local_space"]; r0, l0, s0 = ref[n]
        er = ls["rotation_euler_rad"]; lo = ls["location"]; sc_ = ls["scale"]
        pbs[n].rotation_euler = [(er[a] - r0[i]) * k for i, a in enumerate("xyz")]
        pbs[n].location = [(lo[a] - l0[i]) * k for i, a in enumerate("xyz")]
        pbs[n].scale = [(sc_[a] - s0[i]) * k for i, a in enumerate("xyz")]
        for ch in ("rotation_euler", "location", "scale"): pbs[n].keyframe_insert(ch, frame=f)
for c in act.layers[0].strips[0].channelbags[0].fcurves:
    for kp in c.keyframe_points: kp.interpolation = "LINEAR"
a_pista(rig, act, "Jerry_echado_arm", A - 1)
rig.animation_data.action = prev
for n, (rm, r, l, s) in keep.items(): pbs[n].rotation_mode = rm; pbs[n].rotation_euler, pbs[n].location, pbs[n].scale = r, l, s

# objetivo: la cabeza de Alfred dentro del hoyo
cara = lambda: alf.matrix_world @ alf.pose.bones["face_alfred"].head
# giro del cuerpo hacia el hoyo (raiz, ADD sobre rotacion Z)
sc.frame_set(A1)
h = rig.matrix_world @ pbs["scull"].head; n_ = rig.matrix_world @ pbs["jaw_top"].tail
fw = (n_ - h).xy.normalized(); to = (cara() - j.matrix_world.translation).xy.normalized()
giro = math.atan2(fw.x * to.y - fw.y * to.x, fw.dot(to))
giro_cuerpo = giro * 0.7 if abs(giro) > math.radians(25) else 0.0      # el resto lo hace el cuello
ALZAR = globals().get("ALZAR", 0.10)       # la pose echada hunde ~10 cm el cuerpo en el suelo: se sube la raiz
if True:
    ra = bpy.data.actions.new("jerry_echado_root"); pr = j.animation_data.action; j.animation_data.action = ra
    r_keep = j.rotation_euler.copy(); l_keep = j.location.copy()
    for f in range(A - 1, B + 2):
        j.rotation_euler = (0, 0, giro_cuerpo * w(f)); j.keyframe_insert("rotation_euler", frame=f)
        j.location = (0, 0, ALZAR * w(f)); j.keyframe_insert("location", frame=f)
    for c in ra.layers[0].strips[0].channelbags[0].fcurves:
        for kp in c.keyframe_points: kp.interpolation = "LINEAR"
    a_pista(j, ra, "Jerry_echado_root", A - 1); j.animation_data.action = pr
    j.rotation_euler, j.location = r_keep, l_keep

# mirada al hoyo: spine_1 (cuello) + correccion de scull, como en las otras miradas de Jerry
OFF = math.radians(23)
def obj():
    hh = rig.matrix_world @ pbs["scull"].head; d = cara() - hh; L = d.length; hz = d.xy.length
    p = math.atan2(d.z, hz) - OFF; u = d.xy / hz
    return hh + L * Vector((u.x * math.cos(p), u.y * math.cos(p), math.sin(p)))
def apuntar(nombre, frac, mx, f):
    pb = pbs[nombre]; bse = pb.rotation_euler.copy(); R = bse.to_matrix()
    P_ = pb.matrix.to_3x3() @ R.inverted()
    v = (pb.matrix.inverted() @ pbs["jaw_top"].tail).normalized()
    t = (P_.inverted() @ (rig.matrix_world.inverted() @ obj() - pb.head)).normalized()
    q = (R @ v).normalized().rotation_difference(t)
    e = (Quaternion(q.axis, min(q.angle * frac, math.radians(mx)) * w(f)).to_matrix() @ R).to_euler("XYZ", bse)
    return (e.x - bse.x, e.y - bse.y, e.z - bse.z)
cu = {}
for f in range(A, B + 1): sc.frame_set(f); cu[f] = apuntar("spine_1", 0.85, 50, f)
la = bpy.data.actions.new("jerry_echado_mira"); rig.animation_data.action = la
k1 = pbs["spine_1"].rotation_euler.copy(); k2 = pbs["scull"].rotation_euler.copy()
for f in range(A, B + 1): pbs["spine_1"].rotation_euler = cu[f]; pbs["spine_1"].keyframe_insert("rotation_euler", frame=f)
a_pista(rig, la, "Jerry_echado_mira", A); rig.animation_data.action = prev
pbs["spine_1"].rotation_euler = k1
co = {}
for f in range(A, B + 1): sc.frame_set(f); co[f] = apuntar("scull", 1.0, 25, f)
cb = la.layers[0].strips[0].channelbags[0]
for i in range(3):
    fc = cb.fcurves.new('pose.bones["scull"].rotation_euler', index=i)
    for f in range(A, B + 1): fc.keyframe_points.insert(f, co[f][i], options={"FAST"})
    fc.update()
for c in cb.fcurves:
    for kp in c.keyframe_points: kp.interpolation = "LINEAR"
pbs["scull"].rotation_euler = k2
# comprobar: error de mirada y apoyo en el suelo
dg = bpy.context.evaluated_depsgraph_get(); malla = bpy.data.objects["Mesh_3_jerry"]
rep = {}
for f in (A1, 650, 700, 760):
    sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
    hh = rig.matrix_world @ pbs["scull"].head; fwd = rig.matrix_world @ pbs["jaw_top"].tail - hh
    e = malla.evaluated_get(dg); m = e.to_mesh(); zmin = min((e.matrix_world @ v.co).z for v in m.vertices); e.to_mesh_clear()
    rep[f] = dict(error_mirada=round(math.degrees(fwd.angle(obj() - hh)), 1), suelo_cm=round((zmin - 14.0) * 100, 1))
result = {"pose": POSE, "giro_cuerpo_grados": round(math.degrees(giro_cuerpo), 1), "control": rep}
