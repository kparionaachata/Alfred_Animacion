"""Alfred tirado en el suelo (f798-fin) forcejeando con los pollos encima + los pollos rebotando en su cuerpo.
1) Alfred: capa NLA ADD 'Alfred_forcejea_suelo': se revuelca (giro sobre el eje largo del cuerpo), da sacudidas bruscas
   de cadera hacia arriba (corcoveos), patalea alternando piernas, manotea con los dos brazos para espantarlos y sacude
   la cabeza. Rapido e irregular (nada lento). Las rotaciones se definen en ejes del MUNDO (eje largo / lateral del
   cuerpo tirado) y se pasan al espacio de cada hueso.
2) Pollos: capa ADD 'Pollo_sobre_alfred' en su raiz: siguen el punto del cuerpo donde estan parados (se mueven con el) y,
   con fisica real (g = 9.81/24^2 m/f2), salen despedidos cuando el cuerpo frena su subida mas rapido que la gravedad,
   vuelan en parabola y caen de nuevo sobre el con un rebotito (restitucion 0.3).
Despues hay que re-hornear los insectos pegados (insectos_quedan.py) y las plumas (plumas_pollos.py)."""
import bpy, math
from mathutils import Vector, Matrix, Quaternion
sc = bpy.context.scene
al = bpy.data.objects["Armature"]; apb = al.pose.bones
FIN = sc.frame_end; A = 888; RAMPA = 6
G = 9.81 / 24 ** 2
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
env = lambda f: ss((f - A) / RAMPA)
PISTA = "Alfred_forcejea_suelo"

# --- limpiar corrida anterior (antes de medir la pose base) ---
for t in list(al.animation_data.nla_tracks):
    if t.name == PISTA: al.animation_data.nla_tracks.remove(t)
if PISTA.lower() in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[PISTA.lower()])
for n in ("chicken_1", "chicken_2", "chicken_3"):
    o = bpy.data.objects[n]
    for t in list(o.animation_data.nla_tracks):
        if t.name == "Pollo_sobre_alfred": o.animation_data.nla_tracks.remove(t)
    nm = "pollo_sobre_alfred_" + n
    if nm in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[nm])

# --- ejes del cuerpo tirado (f800) ---
sc.frame_set(890)
W = lambda b: al.matrix_world @ apb[b].head
L = (W("Neck_alfred") - W("Hips_alfred")); L.z = 0; L.normalize()      # eje largo (hacia la cabeza)
U = Vector((0, 0, 1)); S = L.cross(U).normalized()                       # lateral
P = {b.name: (al.matrix_world @ b.matrix).to_quaternion() @ b.rotation_euler.to_quaternion().inverted() for b in apb}
REST = {b.name: (al.matrix_world.to_3x3() @ b.bone.matrix_local.to_3x3()) for b in apb}

def delta_euler(bn, axis, ang):
    """rotacion de `ang` rad alrededor del eje de MUNDO `axis`, expresada como delta euler local del hueso"""
    p = P[bn]; q = p.inverted() @ Quaternion(axis, ang) @ p
    return q.to_euler("XYZ")

# --- curvas (rad / m) ---
CORCOVEOS = [(896, 0.12), (909, 0.09), (921, 0.14), (934, 0.10), (947, 0.15), (960, 0.10), (973, 0.13), (985, 0.09)]
def corcoveo(f):
    """sacudida de cadera hacia arriba: sube en 3 f, baja en 6 f con un pequeno rebote"""
    z = 0.0
    for f0, h in CORCOVEOS:
        t = f - f0
        if 0 <= t <= 3: z += h * ss(t / 3)
        elif 3 < t <= 9: z += h * (1 - ss((t - 3) / 6))
        elif 9 < t <= 14: z += -0.15 * h * math.sin(math.pi * (t - 9) / 5)
    return z
def rodar(f):
    r = math.radians(9) * math.sin(2 * math.pi * f / 27) + math.radians(4) * math.sin(2 * math.pi * f / 11 + 1.0)
    for i, (f0, h) in enumerate(CORCOVEOS):
        t = f - f0
        if 0 <= t <= 12: r += (1 if i % 2 else -1) * math.radians(10) * math.sin(math.pi * t / 12)
    return r
CURVAS = {
    "Hips_alfred":       lambda f: [(L, rodar(f))],
    "Spine2_alfred":     lambda f: [(L, -0.5 * rodar(f) + math.radians(6) * math.sin(2 * math.pi * f / 13))],
    "face_alfred":       lambda f: [(L, math.radians(16) * math.sin(2 * math.pi * f / 15 + 0.5)), (S, math.radians(8) * math.sin(2 * math.pi * f / 9))],
    "RightUpArm_alfred": lambda f: [(S, math.radians(38) * math.sin(2 * math.pi * f / 11)), (L, math.radians(20) * math.sin(2 * math.pi * f / 7 + 0.7))],
    "LeftUpArm_alfred":  lambda f: [(S, math.radians(38) * math.sin(2 * math.pi * f / 12 + 2.1)), (L, math.radians(20) * math.sin(2 * math.pi * f / 8 + 1.9))],
    "Rightelbow_alfred": lambda f: [(S, math.radians(30) * max(0.0, math.sin(2 * math.pi * f / 11 + 0.8)))],
    "Leftelbow_alfred":  lambda f: [(S, math.radians(30) * max(0.0, math.sin(2 * math.pi * f / 12 + 2.9)))],
    "RightUpLeg_alfred": lambda f: [(S, math.radians(16) * math.sin(2 * math.pi * f / 12))],
    "LeftUpLeg_alfred":  lambda f: [(S, math.radians(16) * math.sin(2 * math.pi * f / 12 + math.pi))],
    "Rightknee_alfred":  lambda f: [(S, math.radians(20) * max(0.0, math.sin(2 * math.pi * f / 12 + 0.6)))],
    "Leftknee_alfred":   lambda f: [(S, math.radians(20) * max(0.0, math.sin(2 * math.pi * f / 12 + math.pi + 0.6)))],
}
act = bpy.data.actions.new(PISTA.lower()); prev = al.animation_data.action; al.animation_data.action = act
keep = {b: (apb[b].rotation_mode, apb[b].rotation_euler.copy(), apb[b].location.copy()) for b in CURVAS}
for b in CURVAS: apb[b].rotation_mode = "XYZ"
Mh = REST["Hips_alfred"].inverted()
for f in range(A - 1, FIN + 1):
    w = env(f)
    for bn, fn in CURVAS.items():
        q = Quaternion()
        for axis, ang in fn(f): q = Quaternion(axis, ang * w) @ q
        p = P[bn]; e = (p.inverted() @ q @ p).to_euler("XYZ")
        apb[bn].rotation_euler = e; apb[bn].keyframe_insert("rotation_euler", frame=f)
    apb["Hips_alfred"].location = Mh @ (U * corcoveo(f) * w); apb["Hips_alfred"].keyframe_insert("location", frame=f)
for c in act.layers[0].strips[0].channelbags[0].fcurves:
    for k in c.keyframe_points: k.interpolation = "LINEAR"
sl = al.animation_data.action_slot; al.animation_data.action = prev
for b, (rm, r, l) in keep.items(): apb[b].rotation_mode = rm; apb[b].rotation_euler = r; apb[b].location = l
tr = al.animation_data.nla_tracks.new(); tr.name = PISTA
st = tr.strips.new(act.name, A - 1, act); st.action_slot = sl; st.blend_type = "ADD"; st.extrapolation = "NOTHING"

# --- pollos: siguen el cuerpo y rebotan ---
logs = bpy.app.driver_namespace["_pollos_alfred_logs"]
HUESOS = ["Spine2_alfred", "Spine1_alfred", "Hips_alfred", "RightUpLeg_alfred", "LeftUpLeg_alfred"]   # muslos, no rodillas (patalean demasiado)
bm = lambda b: al.matrix_world @ apb[b].matrix
info = {}
for n, Lg in logs.items():
    land = next(b for s_, t, a, b in Lg if t == "saltar")
    sc.frame_set(land); o = bpy.data.objects[n]; p0 = o.matrix_world.translation.copy()
    hb = min(HUESOS, key=lambda b: (bm(b).translation - p0).length)
    info[n] = dict(land=land, p0=p0, hb=hb, off=bm(hb).inverted() @ p0)
sup = {n: {} for n in info}
for f in range(min(i["land"] for i in info.values()), FIN + 1):
    sc.frame_set(f)
    for n, i in info.items():
        if f >= i["land"]: sup[n][f] = bm(i["hb"]) @ i["off"]
res = {}
for n, i in info.items():
    o = bpy.data.objects[n]; frs = sorted(sup[n]); base = sup[n][frs[0]]
    z = base.z; vz = 0.0; en_aire = False; vs_prev = 0.0; saltos = []
    dl = {}
    for k_, f in enumerate(frs):
        s = sup[n][f]; vs = (s.z - sup[n][frs[k_ - 1]].z) if k_ else 0.0
        if not en_aire:
            if vs_prev - vs > G and vs_prev > 0.004:       # el cuerpo frena su subida mas rapido que g: sale despedido
                en_aire = True; vz = vs_prev; saltos.append(f)
            else: z = s.z
        if en_aire:
            vz -= G; z += vz
            if z <= s.z:
                z = s.z
                if -vz > 0.02: vz = -vz * 0.3                 # rebotito al caer
                else: en_aire = False; vz = 0.0
        vs_prev = vs
        dl[f] = Vector((s.x - base.x, s.y - base.y, z - base.z))
    act = bpy.data.actions.new("pollo_sobre_alfred_" + n); prev = o.animation_data.action; o.animation_data.action = act
    l0 = o.location.copy()
    o.location = (0, 0, 0); o.keyframe_insert("location", frame=frs[0] - 1)
    for f, d in dl.items(): o.location = d; o.keyframe_insert("location", frame=f)
    for c in act.layers[0].strips[0].channelbags[0].fcurves:
        for k in c.keyframe_points: k.interpolation = "LINEAR"
    sl = o.animation_data.action_slot; o.animation_data.action = prev; o.location = l0
    tr = o.animation_data.nla_tracks.new(); tr.name = "Pollo_sobre_alfred"
    st = tr.strips.new(act.name, frs[0] - 1, act); st.action_slot = sl; st.blend_type = "ADD"; st.extrapolation = "NOTHING"
    res[n] = {"hueso": i["hb"], "despegues": saltos, "altura_max_cm": round(max(d.z - (sup[n][f].z - base.z) for f, d in dl.items()) * 100, 1)}
bpy.app.driver_namespace["_pollos_despegues"] = {n: r["despegues"] for n, r in res.items()}
result = res
