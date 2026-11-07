"""Pollo de relleno (chicken_1): recorre #1 (-8.5,1.5,14) -> #2 (-21.5,-7.5,11) -> #3 (-10.5,-14.5,11) en pasos de
1 bloque (ruta A* sobre el terreno medido), con los generadores del chicken_1_animation_studio: caminar RAPIDO,
saltar_bajar, picotear y parada (+ mirar alrededor como capa ADD de cuello/cabeza)."""
import bpy, importlib, math, sys, datetime
from mathutils import Vector

sys.path.insert(0, r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\chicken_1\refinar")
gs = importlib.import_module("chicken_1_animation_studio.generate_slots")
sc = bpy.context.scene
root = bpy.data.objects["chicken_1"]; arm = bpy.data.objects["Armature_chicken_1"]
HOY = datetime.date.today().isoformat()

R1 = [(-8.5, 1.5, 14), (-9.5, 0.5, 14), (-10.5, 0.5, 13), (-11.5, -0.5, 13), (-12.5, -1.5, 13), (-13.5, -1.5, 12),
      (-14.5, -2.5, 12), (-15.5, -3.5, 12), (-16.5, -4.5, 12), (-17.5, -5.5, 12), (-18.5, -5.5, 11), (-19.5, -6.5, 11),
      (-20.5, -7.5, 11), (-21.5, -7.5, 11)]
R2 = [(-21.5, -7.5, 11), (-20.5, -8.5, 11), (-19.5, -8.5, 11), (-18.5, -9.5, 11), (-17.5, -10.5, 11), (-16.5, -11.5, 11),
      (-15.5, -12.5, 11), (-14.5, -12.5, 11), (-13.5, -13.5, 11), (-12.5, -13.5, 11), (-11.5, -13.5, 11), (-10.5, -14.5, 11)]
pt = lambda p, i=0: {"index": i, "coordinates": {"x": p[0], "y": p[1], "z": p[2]}}

# limpiar lo anterior del pollo
for o in (root, arm):
    if not o.animation_data: o.animation_data_create()
    o.animation_data.action = None
    for t in list(o.animation_data.nla_tracks): o.animation_data.nla_tracks.remove(t)
for a in [a for a in bpy.data.actions if a.name.startswith("slot_") and "chicken_1" in a.name or a.name == "pollo_mirar_alrededor"]:
    bpy.data.actions.remove(a)
root.location = R1[0]; root.rotation_euler = (0, 0, math.radians(135)); root.scale = (1, 1, 1)

# plan: (tipo, puntos)
plan = [("picotear", [R1[0]])]
def tramos(ruta, pausas):
    """parte la ruta en caminar/saltar_bajar con group_segments del estudio; `pausas` = {indice_de_punto: accion}"""
    kp = [pt(p, i) for i, p in enumerate(ruta)]
    out = []
    for seg in gs.group_segments(kp):
        pts = [tuple(c["coordinates"][k] for k in "xyz") for c in seg["points"]]
        if seg["type"] == "caminar":
            cur = [pts[0]]
            for p in pts[1:]:
                cur.append(p)
                idx = ruta.index(p)
                if idx in pausas and p != pts[-1]:
                    out.append(("caminar", cur)); out.append((pausas[idx], [p])); cur = [p]
            out.append(("caminar", cur))
            idx = ruta.index(pts[-1])
            if idx in pausas: out.append((pausas[idx], [pts[-1]]))
        else:
            out.append((seg["type"], pts))
    return out
plan += tramos(R1, {4: "mirar"})
plan += [("mirar", [R2[0]], 48), ("picotear", [R2[0]])]
plan += tramos(R2, {6: "picotear"})

f = 1; slot = 1; log = []; miradas = []
for paso in plan:
    tipo, pts = paso[0], paso[1]
    sc.frame_set(max(1, f - 1)); rz = math.degrees(root.matrix_world.to_euler().z)
    rr = (0, 0, rz)
    P = [pt(p, i) for i, p in enumerate(pts)]
    if tipo == "caminar":
        res = gs.generate_caminar(slot, f, P, HOY, rr, walk_style="RAPIDO")
    elif tipo == "saltar_bajar":
        res = gs.generate_saltar_bajar(slot, f, P, HOY, rr)
    elif tipo == "picotear":
        res = gs.generate_picotear_1(slot, f, [P[0], P[0]], HOY, rr)
    elif tipo == "mirar":
        n = (paso[2] if len(paso) > 2 else 24) or (sc.frame_end - f + 1)
        res = gs.generate_parada(slot, f, [P[0], P[0]], HOY, rr, frames_parada=n)
        miradas.append((f, f + n - 1))
    code = res[0] if isinstance(res, tuple) else res
    g = {"__name__": "pollo_slot"}
    exec(compile(code, "slot_%03d_%s" % (slot, tipo), "exec"), g)
    g["execute_animation"](None)
    fin = g.get("END_FRAME", f)
    log.append((slot, tipo, f, fin))
    f = fin + 1; slot += 1
if bpy.context.object and bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")

# mirar alrededor: giro del cuello/cabeza a un lado y al otro sobre la parada (capa ADD)
def eje_vertical(bn):
    pb = arm.pose.bones[bn]; M = (arm.matrix_world @ pb.bone.matrix_local).to_3x3()
    return max(range(3), key=lambda i: abs(M.col[i].normalized().z)), (1 if M.col[max(range(3), key=lambda i: abs(M.col[i].normalized().z))].z > 0 else -1)
act = bpy.data.actions.new("pollo_mirar_alrededor"); arm.animation_data.action = act
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
for a, b in miradas:
    for bn, amp in (("Neck_M_chicken_1", 35), ("Head_M_chicken_1", 25)):
        ax, sg = eje_vertical(bn); pb = arm.pose.bones[bn]; pb.rotation_mode = "XYZ"
        # giros rapidos de pollo: mirar izq, pausa, der, pausa, centro (24 f por vuelta)
        claves = [(0, 0), (4, 1), (12, 1), (16, -1), (26, -1), (30, 0.4), (36, 0.4), (40, 0)]
        k = 0
        while a + k <= b:
            for off, v in claves:
                fr = a + k + off
                if fr > b: break
                r = [0.0, 0.0, 0.0]; r[ax] = sg * math.radians(amp) * v; pb.rotation_euler = r
                pb.keyframe_insert("rotation_euler", frame=fr)
            k += 48
        r = [0.0, 0.0, 0.0]; pb.rotation_euler = r; pb.keyframe_insert("rotation_euler", frame=b)
slot_m = arm.animation_data.action_slot; arm.animation_data.action = None
for bn in ("Neck_M_chicken_1", "Head_M_chicken_1"): arm.pose.bones[bn].rotation_euler = (0, 0, 0)
tr = arm.animation_data.nla_tracks.new(); tr.name = "Pollo_mirar_alrededor"
st = tr.strips.new(act.name, int(act.frame_range[0]), act); st.action_slot = slot_m
st.blend_type = "ADD"; st.extrapolation = "NOTHING"
result = {"slots": log, "miradas": miradas}
