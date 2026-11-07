"""Picotazos de los 3 pollos sobre Alfred: reaccion de Alfred en el frame exacto de cada picotazo y de cada aterrizaje
(perfil elastico de inercia-accion-reaccion, capa ADD 'Alfred_picoteado') + sonidos (aleteo al tirarse, golpe al caer
sobre el, golpecitos de picotazo, cacareos)."""
import bpy, math
sc = bpy.context.scene; ed = sc.sequence_editor
logs = bpy.app.driver_namespace["_pollos_alfred_logs"]
al = bpy.data.objects["Armature"]; apb = al.pose.bones
S = r"C:\Users\user\Desktop\Alfred_Animacion\sonidos"
HUESO = {"chicken_1": "Spine2_alfred", "chicken_2": "Hips_alfred", "chicken_3": "RightUpLeg_alfred"}

# --- frames de impacto: minimo local de altura de la cabeza en cada picoteo sobre Alfred ---
impactos = []   # (frame, pollo, fuerza)
saltos = {}
for n, L in logs.items():
    arm = bpy.data.objects["Armature_" + n]; hb = arm.pose.bones["Head_M_chicken_1"]
    sobre = False
    for slot, tipo, a, b in L:
        if tipo == "saltar":
            saltos[n] = (a, b); impactos.append((b, n, 1.0)); sobre = True; continue
        if sobre and tipo == "picotear":
            zs = []
            for f in range(a, b + 1):
                sc.frame_set(f); zs.append((arm.matrix_world @ hb.tail).z)
            for i in range(1, len(zs) - 1):
                if zs[i] <= zs[i - 1] and zs[i] < zs[i + 1] and zs[i] < max(zs) - 0.05:
                    impactos.append((a + i, n, 0.35))

# --- reaccion de Alfred (ADD) ---
for t in list(al.animation_data.nla_tracks):
    if t.name == "Alfred_picoteado": al.animation_data.nla_tracks.remove(t)
if "alfred_picoteado" in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions["alfred_picoteado"])
PERFIL = [(0, 0.45), (2, 1.0), (5, -0.18), (8, 0.06), (11, 0.0)]
curvas = {}
for f0, n, fu in impactos:
    bn = HUESO[n]; amp = math.radians(6.0) * fu
    for off, w in PERFIL:
        d = curvas.setdefault(bn, {})
        d[f0 + off] = d.get(f0 + off, 0.0) + amp * w
    d[f0 - 1] = d.get(f0 - 1, 0.0)
keep = {b: apb[b].rotation_mode for b in curvas}
act = bpy.data.actions.new("alfred_picoteado"); prev = al.animation_data.action; al.animation_data.action = act
for bn, d in curvas.items():
    pb = apb[bn]; dp = 'rotation_quaternion' if pb.rotation_mode == 'QUATERNION' else 'rotation_euler'
    for f in sorted(d):
        if dp == 'rotation_euler':
            pb.rotation_euler = (d[f], 0, 0); pb.keyframe_insert(dp, frame=f, index=0)
        else:
            pb.rotation_quaternion = (1, 0, 0, 0)
            from mathutils import Quaternion
            q = Quaternion((1, 0, 0), d[f]); q.w -= 1.0     # ADD: delta respecto a identidad
            pb.rotation_quaternion = q; pb.keyframe_insert(dp, frame=f)
sl = al.animation_data.action_slot; al.animation_data.action = prev
tr = al.animation_data.nla_tracks.new(); tr.name = "Alfred_picoteado"
st = tr.strips.new(act.name, int(act.frame_range[0]), act); st.action_slot = sl; st.blend_type = "ADD"; st.extrapolation = "NOTHING"

# --- sonidos ---
for s in [s for s in ed.strips_all if s.name.startswith("SND_pollos_alfred")]: ed.strips.remove(s)
for s in [s for s in ed.strips_all if s.name.startswith("SND_pollo_cacarea") and s.frame_final_start >= 697]: ed.strips.remove(s)
def libre(f, n=20, ch0=41):
    for ch in range(ch0, 128):
        if not any(s.channel == ch and s.frame_final_start < f + n and s.frame_final_end > f for s in ed.strips_all): return ch
def poner(nm, ruta, f, vol):
    x = ed.strips.new_sound(nm, ruta, libre(f), f); x.volume = vol; x["vol_base"] = vol; return x
k = 0
for n, (a, b) in saltos.items():
    poner("SND_pollos_alfred_aleteo_%s" % n, S + r"\THE UNDEAD REVAMPED\wing-flap-1-6434.ogg", a + 8, 0.5)
    poner("SND_pollos_alfred_cae_%s" % n, S + r"\vanilla\step\cloth%d.ogg" % (k % 4 + 1), b, 0.5); k += 1
for n, vs in bpy.app.driver_namespace.get("_pollos_aleteos", {}).items():   # aleteo desesperado encima del picoteo
    for a, b in vs:
            for j, off in enumerate((2, 22, 42)):
                poner("SND_pollos_alfred_aletea_%s_%d" % (n, a + off), S + r"\THE UNDEAD REVAMPED\wing-flap-1-6434.ogg", a + off, 0.4 - 0.05 * j)
for i, (f, n, fu) in enumerate(sorted(impactos)):
    if fu < 1: poner("SND_pollos_alfred_pico_%s_%d" % (n, f), S + r"\vanilla\step\cloth%d.ogg" % (i % 4 + 1), f, 0.18)
cac = [700, 738, 745, 760, 790, 830, 852, 880, 905, 925, 945]
for i, f in enumerate(cac): poner("SND_pollos_alfred_cacarea_%d" % f, S + r"\vanilla\mob\chicken\say%d.ogg" % (i % 3 + 1), f, 0.5)
DUCK = 0.56
exec(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\ducking_voces.py", encoding="utf-8").read(), {"__name__": "x", "DUCK": DUCK})
result = {"impactos": len(impactos), "picotazos": len([i for i in impactos if i[2] < 1]), "saltos": saltos,
          "huesos": {b: keep[b] for b in keep}, "sonidos": len([s for s in ed.strips_all if s.name.startswith("SND_pollos_alfred")])}
