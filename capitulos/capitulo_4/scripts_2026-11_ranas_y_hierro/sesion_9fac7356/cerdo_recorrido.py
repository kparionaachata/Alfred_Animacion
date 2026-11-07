"""cerdo_1 en el escenario de las ranas: recorrido.json (Desktop) con los generadores del cerdo_1_animation_studio
(caminar / saltar_subir / saltar_bajar segun la Z, group_segments del estudio)."""
import bpy, sys, importlib, json, math, datetime
sys.path.insert(0, r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\cerdo_1\refinar")
gs = importlib.import_module("cerdo_1_animation_studio.generate_slots_cerdo_1")
sc = bpy.context.scene; HOY = datetime.date.today().isoformat()
# 1) traer el cerdo
if "cerdo_1" not in bpy.data.objects:
    P = r"C:\Users\user\Desktop\Alfred_Animacion\estructura_lista\cerdo_1.blend"
    with bpy.data.libraries.load(P) as (src, dst): dst.objects = list(src.objects)
    col = bpy.data.collections.get("cerdo_relleno") or bpy.data.collections.new("cerdo_relleno")
    if col.name not in sc.collection.children: sc.collection.children.link(col)
    for o in dst.objects: col.objects.link(o)
root = bpy.data.objects["cerdo_1"]; arm = bpy.data.objects["pig.arma_cerdo_1"]
# 2) limpiar animacion previa del cerdo
for o in (root, arm):
    if not o.animation_data: o.animation_data_create()
    o.animation_data.action = None
    for t in list(o.animation_data.nla_tracks): o.animation_data.nla_tracks.remove(t)
for a in [a for a in bpy.data.actions if a.name.startswith("slot_") and "cerdo_1" in a.name]: bpy.data.actions.remove(a)
kp = json.load(open(r"C:\Users\user\AppData\Local\Temp\claude\d0772e74e53e6fa2\9fac7356-8ced-4d1a-a12c-3247350383c7\scratchpad\recorrido_cerdo_extendido.json"))["key_points"]
p0 = kp[0]["coordinates"]
root.location = (p0["x"], p0["y"], p0["z"]); root.rotation_euler = (0, 0, math.radians(135)); root.scale = (1, 1, 1)
# 3) plan: caminar LENTO con paradas para mirar alrededor en algunos puntos
PAUSAS = {4: 48, 12: 42, 18: 48, 28: 40}          # indice del punto en recorrido.json (0-based) -> frames de parada
RUTA = [tuple(c["coordinates"][k] for k in "xyz") for c in kp]
plan = []
for seg in gs.group_segments(kp):
    pts = [dict(c) for c in seg["points"]]
    if seg["type"] != "caminar": plan.append((seg["type"], pts)); continue
    cur = [pts[0]]
    for c in pts[1:]:
        cur.append(c); idx = RUTA.index(tuple(c["coordinates"][k] for k in "xyz"))
        if idx in PAUSAS:
            plan.append(("caminar", cur)); plan.append(("parada", [c, c], PAUSAS[idx])); cur = [c]
    if len(cur) > 1: plan.append(("caminar", cur))
f = 1; log = []; miradas = []
for i, paso in enumerate(plan, 1):
    t, P = paso[0], paso[1]
    sc.frame_set(max(1, f - 1)); rr = (0, 0, math.degrees(root.matrix_world.to_euler().z))
    if t == "caminar": res = gs.generate_caminar(i, f, P, HOY, rr, walk_style="LENTO")
    elif t == "saltar_subir": res = gs.generate_saltar_subir(i, f, P, HOY, rr)
    elif t == "saltar_bajar": res = gs.generate_saltar_bajar(i, f, P, HOY, rr)
    else:
        res = gs.generate_parada(i, f, P, HOY, rr, frames_parada=paso[2]); miradas.append((f, f + paso[2] - 1))
    code = res[0] if isinstance(res, tuple) else res
    g = {"__name__": "cerdo_slot"}
    exec(compile(code, "slot_%03d_%s" % (i, t), "exec"), g); g["execute_animation"](None)
    fin = g.get("END_FRAME", f); log.append((i, t, f, fin)); f = fin + 1
if bpy.context.object and bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
# 4) mirar alrededor en las paradas: giro de la cabeza (capa ADD sobre Head)
for t in list(arm.animation_data.nla_tracks):
    if t.name == "Cerdo_mirar_alrededor": arm.animation_data.nla_tracks.remove(t)
if "cerdo_mirar_alrededor" in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions["cerdo_mirar_alrededor"])
pb = arm.pose.bones["Head_cerdo_1"]; pb.rotation_mode = "XYZ"
M = (arm.matrix_world @ pb.bone.matrix_local).to_3x3()
ax = max(range(3), key=lambda k: abs(M.col[k].normalized().z)); sg = 1 if M.col[ax].z > 0 else -1
act = bpy.data.actions.new("cerdo_mirar_alrededor"); arm.animation_data.action = act
for a, b in miradas:
    n = b - a
    claves = [(0, 0, 0), (0.18, 1, 0.3), (0.38, 1, 0.3), (0.58, -1, -0.2), (0.80, -1, -0.2), (1.0, 0, 0)]  # (fase, giro, cabeceo)
    for ph, v, cab in claves:
        r = [0.0, 0.0, 0.0]; r[ax] = sg * math.radians(40) * v
        r[0 if ax != 0 else 1] += math.radians(8) * cab
        pb.rotation_euler = r; pb.keyframe_insert("rotation_euler", frame=a + round(n * ph))
slot_m = arm.animation_data.action_slot; arm.animation_data.action = None; pb.rotation_euler = (0, 0, 0)
tr = arm.animation_data.nla_tracks.new(); tr.name = "Cerdo_mirar_alrededor"
st = tr.strips.new(act.name, int(act.frame_range[0]), act); st.action_slot = slot_m
st.blend_type = "ADD"; st.extrapolation = "NOTHING"
# 5) comprobar llegada a cada punto
chk = []
for i, t, a, b in log:
    sc.frame_set(b); chk.append((t, b, [round(x, 2) for x in root.matrix_world.translation]))
result = {"slots": log, "fin": chk, "eje_cabeza": ax}
