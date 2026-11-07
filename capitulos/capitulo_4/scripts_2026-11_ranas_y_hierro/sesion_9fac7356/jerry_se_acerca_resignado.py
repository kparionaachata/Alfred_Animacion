"""Jerry, mientras los pollos picotean a Alfred: recorrido_1.json (Desktop) con el jerry_animation_studio (saltar bajar +
caminar NORMAL), se sienta (biblioteca: se_sienta_zombies_subiendo_jerry, 13 f) y queda sentado mirando a Alfred
(spine_1 + correccion de scull apuntados a la cara de Alfred) y mueve la cabeza de izquierda a derecha, resignado
(cabeza un poco gacha, ojos tristes). Todo en pistas NLA nuevas encima de lo existente (nada se borra)."""
import ast, bpy, datetime, importlib, json, math, sys
from mathutils import Matrix, Vector, Euler, Quaternion
sys.path.insert(0, r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\jerry\refinar")
gs = importlib.import_module("jerry_animation_studio.generate_slots_jerry")
sc = bpy.context.scene; HOY = datetime.date.today().isoformat()
j = bpy.data.objects["jerry"]; rig = bpy.data.objects["Dog_001_rig"]; alf = bpy.data.objects["Armature"]; pbs = rig.pose.bones
INICIO = 790
PREFIJO = ("Slot_06", "Jerry_sienta_resignado")
# limpiar lo de una corrida anterior
for o in (j, rig):
    for t in list(o.animation_data.nla_tracks):
        if t.name.startswith(PREFIJO): o.animation_data.nla_tracks.remove(t)
for a in [a for a in bpy.data.actions if a.name.startswith(("slot_06", "jerry_sienta_resignado"))]: bpy.data.actions.remove(a)

# ---- 1) recorrido con el estudio ----
kp = json.load(open(r"C:\Users\user\Desktop\recorrido_1.json"))["key_points"]
f = INICIO; slot = 61; log = []
for seg in gs.group_segments(kp):
    sc.frame_set(f - 1); prz = math.degrees(j.matrix_world.to_euler().z); rr = (0, 0, prz)
    P = [dict(c) for c in seg["points"]]
    t = seg["type"]
    if t == "caminar": res = gs.generate_caminar(slot, f, P, HOY, prz, rr, walk_style="RAPIDO", frames_por_bloque=21)   # +50% de velocidad (32/1.5 f por bloque)
    elif t == "saltar_bajar": res = gs.generate_saltar_bajar(slot, f, P, HOY, prz, rr)
    elif t == "saltar_subir": res = gs.generate_saltar_subir(slot, f, P, HOY, prz, rr)
    code = res[0] if isinstance(res, tuple) else res
    g = {"__name__": "jerry_slot"}
    exec(compile(code, "slot_%03d_%s" % (slot, t), "exec"), g); g["execute_animation"](None)
    fin = g.get("END_FRAME", res[1] if isinstance(res, tuple) else f)
    log.append((slot, t, f, fin)); f = fin + 1; slot += 1
if bpy.context.object and bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
F_SIENTA = f

# ---- 2) se sienta (biblioteca), como pistas REPLACE encima, sostenidas hasta el final ----
src = open(r"C:\Users\user\Desktop\Alfred_Animacion\codigos de animacion\jerry\se_sienta_zombies_subiendo_jerry.py", encoding="utf-8").read()
PL = next(ast.literal_eval(n.value) for n in ast.parse(src).body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "PAYLOAD")
N = PL["info"]["frames"]
sc.frame_set(F_SIENTA - 1)
mat = lambda l, e: Matrix.LocRotScale(Vector(l), Euler(e, "XYZ").to_quaternion(), Vector((1, 1, 1)))
T = j.matrix_world.copy() @ mat(PL["root"]["location"][0], PL["root"]["rotation_euler"][0]).inverted()

def a_pista(obj, act, nombre, blend, inicio, hold=False):
    sl = obj.animation_data.action_slot; obj.animation_data.action = None
    tr = obj.animation_data.nla_tracks.new(); tr.name = nombre
    st = tr.strips.new(act.name, inicio, act); st.action_slot = sl; st.blend_type = blend
    st.extrapolation = "HOLD_FORWARD" if hold else "NOTHING"
    return st

keep = {b.name: (b.rotation_mode, b.rotation_euler.copy(), b.location.copy(), b.scale.copy()) for b in pbs}
act = bpy.data.actions.new("jerry_sienta_resignado_arm"); rig.animation_data.action = act
for b in pbs: b.rotation_mode = "XYZ"
for name, chans in PL["constantes"].items():
    for ch, v in chans.items(): setattr(pbs[name], ch, v); pbs[name].keyframe_insert(ch, frame=F_SIENTA)
for name, chans in PL["bones"].items():
    for ch, vals in chans.items():
        for i, v in enumerate(vals): setattr(pbs[name], ch, v); pbs[name].keyframe_insert(ch, frame=F_SIENTA + i)
a_pista(rig, act, "Jerry_sienta_resignado_arm", "REPLACE", F_SIENTA, hold=True)
for n, (rm, r, l, s) in keep.items(): pb = pbs[n]; pb.rotation_euler, pb.location, pb.scale = r, l, s
ra = bpy.data.actions.new("jerry_sienta_resignado_root"); j.animation_data.action = ra; j.rotation_mode = "XYZ"
prev = j.rotation_euler.copy()
for i in range(N):
    M = T @ mat(PL["root"]["location"][i], PL["root"]["rotation_euler"][i]); l, q, _ = M.decompose()
    e = q.to_euler("XYZ", prev); prev = e
    j.location = l; j.rotation_euler = e
    j.keyframe_insert("location", frame=F_SIENTA + i); j.keyframe_insert("rotation_euler", frame=F_SIENTA + i)
a_pista(j, ra, "Jerry_sienta_resignado_root", "REPLACE", F_SIENTA, hold=True)
for a_ in (act, ra):
    for c in a_.layers[0].strips[0].channelbags[0].fcurves:
        for k in c.keyframe_points: k.interpolation = "LINEAR"
F_SENTADO = F_SIENTA + N            # ya sentado

# ---- 3) mira a Alfred y mueve la cabeza de izquierda a derecha (resignacion) ----
A = F_SENTADO; RAMPA = 6
F_NIEGA = A + 10; CICLOS = 3; PER = 15; F_FIN_NIEGA = F_NIEGA + CICLOS * PER
B = 990                             # fin de la animacion
sc.frame_end = B
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
peso = lambda f: ss((f - A) / RAMPA)
def niega(fr):
    if fr < F_NIEGA or fr > F_FIN_NIEGA: return 0.0
    t = (fr - F_NIEGA) / PER
    env = ss(t / 0.5) * ss((CICLOS - t) / 0.7)            # entra y sale suave
    return math.radians(24) * env * math.sin(2 * math.pi * t)
OFF = math.radians(23)               # el vector scull->jaw_top.tail va ~23 grados por debajo del hocico
cara = lambda: alf.matrix_world @ alf.pose.bones["face_alfred"].head
def obj(f):
    h = rig.matrix_world @ pbs["scull"].head; d = cara() - h; L = d.length; hz = d.xy.length
    p = math.atan2(d.z, hz) - OFF - math.radians(8)      # un poco gacha: resignado
    yaw = math.atan2(d.y, d.x) + niega(f)                 # "no" con la cabeza: izquierda-derecha sobre el eje vertical
    return h + L * Vector((math.cos(yaw) * math.cos(p), math.sin(yaw) * math.cos(p), math.sin(p)))
def apuntar(nombre, frac, mx, f):
    pb = pbs[nombre]; base = pb.rotation_euler.copy(); R = base.to_matrix()
    P_ = pb.matrix.to_3x3() @ R.inverted()
    v = (pb.matrix.inverted() @ pbs["jaw_top"].tail).normalized()
    t = (P_.inverted() @ (rig.matrix_world.inverted() @ obj(f) - pb.head)).normalized()
    q = (R @ v).normalized().rotation_difference(t)
    e = (Quaternion(q.axis, min(q.angle * frac, math.radians(mx)) * peso(f)).to_matrix() @ R).to_euler("XYZ", base)
    return (e.x - base.x, e.y - base.y, e.z - base.z)
cuello = {}
for fr in range(A, B + 1): sc.frame_set(fr); cuello[fr] = apuntar("spine_1", 0.85, 55, fr)
la = bpy.data.actions.new("jerry_sienta_resignado_mira"); rig.animation_data.action = la
keep = {b: pbs[b].rotation_euler.copy() for b in ("spine_1", "scull")}
for fr in range(A, B + 1):
    pbs["spine_1"].rotation_euler = cuello[fr]; pbs["spine_1"].keyframe_insert("rotation_euler", frame=fr)
a_pista(rig, la, "Jerry_sienta_resignado_mira", "ADD", A, hold=True)
for b, r in keep.items(): pbs[b].rotation_euler = r
corr = {}
for fr in range(A, B + 1): sc.frame_set(fr); corr[fr] = apuntar("scull", 1.0, 30, fr)
cb = la.layers[0].strips[0].channelbags[0]
for i in range(3):
    fc = cb.fcurves.new('pose.bones["scull"].rotation_euler', index=i)
    for fr in range(A, B + 1):
        fc.keyframe_points.insert(fr, corr[fr][i], options={"FAST"})
    fc.update()
for c in cb.fcurves:
    for k in c.keyframe_points: k.interpolation = "LINEAR"
# ojos tristes mientras niega
for eye in ("ojo_izquierdo_jerry", "ojo_derecho_jerry"):
    kb = bpy.data.objects[eye].data.shape_keys.key_blocks.get("Triste")
    if not kb: continue
    for fr, v in ((F_NIEGA - 6, 0.0), (F_NIEGA + 4, 0.6), (F_FIN_NIEGA + 10, 0.6), (B, 0.45)):
        kb.value = v; kb.keyframe_insert("value", frame=fr)
    kb.value = 0.0
# ---- 4) pasos de Jerry en el recorrido (plantilla de pasos ya usada en la escena) ----
ed = sc.sequence_editor
for s in [s for s in ed.strips_all if s.name.startswith("SND_paso_jerry_resig")]: ed.strips.remove(s)
plant = next(s for s in ed.strips_all if s.name.startswith("SND_paso_jerry_105"))
pasos = []
for slot_, t, a_, b_ in log:
    if t != "caminar": continue
    alto = {}
    for fr in range(a_, b_ + 1):
        sc.frame_set(fr)
        for pie in ("front_toe.L", "front_toe.R", "toe.L", "toe.R"):
            z = (rig.matrix_world @ pbs[pie].head).z - j.matrix_world.translation.z
            st = alto.setdefault(pie, [None, False])
            if st[0] is not None and z > st[0] + 0.02: st[1] = True
            if st[1] and st[0] is not None and z <= st[0] + 0.004: pasos.append(fr); st[1] = False
            st[0] = z if st[0] is None else min(st[0], z) if not st[1] else st[0]
pasos = sorted(set(pasos)); dep = []
for p in pasos:
    if not dep or p - dep[-1] > 3: dep.append(p)
def libre(fr, n=12, ch0=20):
    for ch in range(ch0, 128):
        if not any(s.channel == ch and s.frame_final_start < fr + n and s.frame_final_end > fr for s in ed.strips_all): return ch
for p in dep:
    x = ed.strips.new_sound("SND_paso_jerry_resig_%d" % p, plant.sound.filepath, libre(p), p); x.volume = plant.volume
aterr = [b_ for s_, t, a_, b_ in log if t.startswith("saltar")]
for p in aterr:
    x = ed.strips.new_sound("SND_paso_jerry_resig_at_%d" % p, plant.sound.filepath, libre(p), p); x.volume = min(1.0, plant.volume * 1.6)
bpy.app.driver_namespace["_FIN_ESCENA"] = sc.frame_end
sc.frame_set(B)
result = {"slots": log, "se_sienta": (F_SIENTA, F_SENTADO - 1), "mira": A, "niega": (F_NIEGA, F_FIN_NIEGA), "fin": B,
          "pos_final": [round(v, 2) for v in j.matrix_world.translation], "pasos": len(dep)}
