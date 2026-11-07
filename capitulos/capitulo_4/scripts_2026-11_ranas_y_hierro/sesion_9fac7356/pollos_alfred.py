"""Los 3 pollos (chicken_1 que ya habia + chicken_2 y chicken_3 nuevos) corren hacia Alfred cuando cae (~795), se le tiran
encima con el salto de 3 puntos del estudio y lo picotean por el cuerpo buscando los insectos, hasta f960.
Todo con los generadores del chicken_1_animation_studio (caminar PERSEGUIDO = correr, saltar, picotear, parada)
+ capa ADD de mirar alrededor en las paradas. chicken_2/3 = copias de estructura_lista/chicken_1.blend; para generar sus
slots se intercambian temporalmente los nombres con los de chicken_1 (el codigo generado busca esos nombres)."""
import bpy, importlib, math, sys, datetime
sys.path.insert(0, r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\chicken_1\refinar")
gs = importlib.import_module("chicken_1_animation_studio.generate_slots")
sc = bpy.context.scene; HOY = datetime.date.today().isoformat()
FIN = int(bpy.app.driver_namespace.get("_FIN_ESCENA", 960))   # fin de la escena (lo fija la ultima animacion, p.ej. Jerry)
sc.frame_end = FIN
pt = lambda p, i=0: {"index": i, "coordinates": {"x": p[0], "y": p[1], "z": p[2]}, "texture": "grass_block_top", "face_index": ""}


def jerarquia(root):
    return [root] + list(root.children_recursive)


# --- traer chicken_2 y chicken_3 ---
col = bpy.data.collections.get("pollos_alfred") or bpy.data.collections.new("pollos_alfred")
if col.name not in sc.collection.children: sc.collection.children.link(col)
for n in ("chicken_2", "chicken_3"):
    if n in bpy.data.objects: continue
    with bpy.data.libraries.load(r"C:\Users\user\Desktop\Alfred_Animacion\estructura_lista\chicken_1.blend") as (src, dst):
        dst.objects = list(src.objects)
    for o in dst.objects: col.objects.link(o)
    for o in dst.objects:
        nm = o.name
        if "." in nm and nm.rsplit(".", 1)[1].isdigit(): nm = nm.rsplit(".", 1)[0]
        o.name = nm.replace("chicken_1", n)
ORIG = jerarquia(bpy.data.objects["chicken_1"])


def con_nombres(n, fn):
    """ejecuta fn con los objetos de chicken_n llamados como los de chicken_1"""
    if n == "chicken_1": return fn()
    cl = {o.name.replace(n, "chicken_1"): o for o in jerarquia(bpy.data.objects[n])}
    pares = [(o, cl[o.name]) for o in ORIG if o.name in cl]
    nombres = [o.name for o, c in pares]
    for o, c in pares: o.name = o.name + "__o"
    for (o, c), nm in zip(pares, nombres): c.name = nm
    try:
        return fn()
    finally:
        for (o, c), nm in zip(pares, nombres): c.name = nm.replace("chicken_1", n)
        for (o, c), nm in zip(pares, nombres): o.name = nm


def limpiar(n):
    root = bpy.data.objects[n]; arm = bpy.data.objects["Armature_" + n]
    for o in (root, arm):
        if not o.animation_data: o.animation_data_create()
        o.animation_data.action = None
        for t in list(o.animation_data.nla_tracks): o.animation_data.nla_tracks.remove(t)
    return root, arm


def mirar_alrededor(n, miradas):
    arm = bpy.data.objects["Armature_" + n]
    nombre = "pollo_mirar_alrededor" if n == "chicken_1" else "pollo_mirar_" + n
    if nombre in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[nombre])
    if not miradas: return
    act = bpy.data.actions.new(nombre); arm.animation_data.action = act
    for a, b in miradas:
        for bn, amp in (("Neck_M_chicken_1", 35), ("Head_M_chicken_1", 25)):
            pb = arm.pose.bones[bn]; pb.rotation_mode = "XYZ"
            M = (arm.matrix_world @ pb.bone.matrix_local).to_3x3()
            ax = max(range(3), key=lambda i: abs(M.col[i].normalized().z)); sg = 1 if M.col[ax].z > 0 else -1
            claves = [(0, 0), (4, 1), (12, 1), (16, -1), (26, -1), (30, 0.4), (36, 0.4), (40, 0)]
            k = 0
            while a + k <= b:
                for off, v in claves:
                    fr = a + k + off
                    if fr > b: break
                    r = [0.0, 0.0, 0.0]; r[ax] = sg * math.radians(amp) * v
                    pb.rotation_euler = r; pb.keyframe_insert("rotation_euler", frame=fr)
                k += 48
            pb.rotation_euler = (0, 0, 0); pb.keyframe_insert("rotation_euler", frame=b)
    sl = arm.animation_data.action_slot; arm.animation_data.action = None
    for bn in ("Neck_M_chicken_1", "Head_M_chicken_1"): arm.pose.bones[bn].rotation_euler = (0, 0, 0)
    tr = arm.animation_data.nla_tracks.new(); tr.name = "Pollo_mirar_alrededor"
    st = tr.strips.new(act.name, int(act.frame_range[0]), act); st.action_slot = sl
    st.blend_type = "ADD"; st.extrapolation = "NOTHING"


def ejecutar(n, plan, base_slot, rot0, p0):
    root, arm = limpiar(n)
    for a in [a for a in bpy.data.actions if a.name.startswith("slot_") and "chicken_1" in a.name
              and a.name[5:8].isdigit() and int(a.name[5:8]) // 100 == base_slot // 100]:
        bpy.data.actions.remove(a)
    root.location = p0; root.rotation_euler = (0, 0, math.radians(rot0)); root.scale = (1, 1, 1)
    f = 1; slot = base_slot; log = []; miradas = []
    for paso in plan:
        tipo, pts = paso[0], paso[1]
        sc.frame_set(max(1, f - 1)); rr = (0, 0, math.degrees(root.matrix_world.to_euler().z))
        P = [pt(p, i) for i, p in enumerate(pts)]
        if tipo == "caminar": res = gs.generate_caminar(slot, f, P, HOY, rr, walk_style=paso[2] if len(paso) > 2 else "RAPIDO")
        elif tipo == "saltar_bajar": res = gs.generate_saltar_bajar(slot, f, P, HOY, rr)
        elif tipo == "saltar_subir": res = gs.generate_saltar_subir(slot, f, P, HOY, rr)
        elif tipo == "saltar": res = gs.generate_saltar(slot, f, P, HOY, rr, altura_pico=paso[2])
        elif tipo == "picotear": res = gs.generate_picotear_1(slot, f, [P[0], P[0]], HOY, rr)
        elif tipo == "aletear": res = gs.generate_aletear_1(slot, f, [P[0], P[0]], HOY, rr)
        elif tipo == "mirar":
            nfr = paso[2]
            res = gs.generate_parada(slot, f, [P[0], P[0]], HOY, rr, frames_parada=nfr); miradas.append((f, f + nfr - 1))
        code = res[0] if isinstance(res, tuple) else res
        g = {"__name__": "pollo_slot"}

        def correr():
            exec(compile(code, "slot_%03d_%s" % (slot, tipo), "exec"), g)
            g["execute_animation"](None)
        con_nombres(n, correr)
        fin = g.get("END_FRAME", f); log.append((slot, tipo, f, fin)); f = fin + 1; slot += 1
    if bpy.context.object and bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
    mirar_alrededor(n, miradas)
    return log


def tramos(ruta, pausas, estilo="RAPIDO"):
    """caminar/saltar segun Z con group_segments; pausas = {indice: frames de mirar}"""
    kp = [pt(p, i) for i, p in enumerate(ruta)]; out = []
    for seg in gs.group_segments(kp):
        pts = [tuple(c["coordinates"][k] for k in "xyz") for c in seg["points"]]
        if seg["type"] == "caminar":
            cur = [pts[0]]
            for p in pts[1:]:
                cur.append(p); idx = ruta.index(p)
                if idx in pausas and p != pts[-1]:
                    out.append(("caminar", cur, estilo)); out.append(("mirar", [p], pausas[idx])); cur = [p]
            out.append(("caminar", cur, estilo))
            idx = ruta.index(pts[-1])
            if idx in pausas: out.append(("mirar", [pts[-1]], pausas[idx]))
        else:
            out.append((seg["type"], pts))
    return out


def relleno(p, desde, hasta, mirar_cada=2, larga=40):
    """quieto en p de `desde` a `hasta` (exacto): picotear (24 f) y mirar alrededor alternados"""
    plan = []; f = desde; i = 0
    while True:
        quedan = hasta - f + 1
        if quedan <= 0: break
        if i % (mirar_cada + 1) == mirar_cada and quedan >= larga + 8:
            plan.append(("mirar", [p], larga)); f += larga
        elif quedan >= 24 + 8:
            plan.append(("picotear", [p])); f += 24
        else:
            plan.append(("mirar", [p], quedan)); f += quedan
        i += 1
    return plan


def sobre_alfred(p, desde, fase=0):
    """sobre Alfred hasta FIN: picotea y aletea desesperado (aletear_1 del estudio, 64 f) con pausas cortas de mirar"""
    patron = ["picotear", "picotear", "picotear", "picotear", "picotear", "mirar"]   # pica sin parar; el aleteo va encima (capa ADD de alas)
    dur = {"picotear": 24, "aletear": 64, "mirar": 16}
    plan = []; f = desde; i = fase
    while True:
        quedan = FIN - f + 1
        if quedan <= 0: break
        t = patron[i % len(patron)]; i += 1
        if dur[t] + 8 > quedan:
            t = "picotear" if quedan >= 32 else None
        if t is None: plan.append(("mirar", [p], quedan)); break
        plan.append((t, [p], dur[t]) if t == "mirar" else (t, [p])); f += dur[t]
    return plan


def salto(a, b, h=0.9):
    m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, max(a[2], b[2]) + h)
    return ("saltar", [a, m, b], h)


def fin_de(log): return log[-1][3]


PECHO, CADERA, PIERNAS = (-19.45, -5.9, 11.63), (-19.4, -5.35, 11.66), (-19.35, -4.85, 11.67)
logs = {}

# ===== chicken_1: igual que antes hasta picotear en (-15.5,-12.5) (673-696); mira, corre y se tira al pecho =====
R1 = [(-8.5, 1.5, 14), (-9.5, 0.5, 14), (-10.5, 0.5, 13), (-11.5, -0.5, 13), (-12.5, -1.5, 13), (-13.5, -1.5, 12),
      (-14.5, -2.5, 12), (-15.5, -3.5, 12), (-16.5, -4.5, 12), (-17.5, -5.5, 12), (-18.5, -5.5, 11), (-19.5, -6.5, 11),
      (-20.5, -7.5, 11), (-21.5, -7.5, 11)]
R2 = [(-21.5, -7.5, 11), (-20.5, -8.5, 11), (-19.5, -8.5, 11), (-18.5, -9.5, 11), (-17.5, -10.5, 11), (-16.5, -11.5, 11), (-15.5, -12.5, 11)]
R3 = [(-15.5, -12.5, 11), (-16.5, -11.5, 11), (-17.5, -10.5, 11), (-18.5, -9.5, 11), (-18.5, -8.5, 11), (-18.5, -7.5, 11)]
plan1 = [("picotear", [R1[0]])] + tramos(R1, {4: 24}) + [("mirar", [R2[0]], 48), ("picotear", [R2[0]])] + tramos(R2, {}) + [("picotear", [R2[-1]])]
L = ejecutar("chicken_1", plan1, 1, 135, R1[0])
plan1 += [("mirar", [R2[-1]], max(8, 825 - fin_de(L)))] + [("caminar", R3, "PERSEGUIDO")]
L = ejecutar("chicken_1", plan1, 1, 135, R1[0])
plan1 += [salto(R3[-1], PECHO)]
L = ejecutar("chicken_1", plan1, 1, 135, R1[0])
plan1 += sobre_alfred(PECHO, fin_de(L) + 1, 0)
logs["chicken_1"] = ejecutar("chicken_1", plan1, 1, 135, R1[0])

# ===== chicken_2: picotea al oeste; corre desde 742 y se tira a la cadera =====
C2 = [(-25.5, -7.5, 11), (-24.5, -7.5, 11), (-23.5, -6.5, 11), (-22.5, -6.5, 11), (-21.5, -6.5, 11), (-20.5, -5.5, 11)]
plan2 = relleno(C2[0], 1, 831) + tramos(C2, {}, "PERSEGUIDO")
L = ejecutar("chicken_2", plan2, 201, 0, C2[0])
plan2 += [salto(C2[-1], CADERA)]
L = ejecutar("chicken_2", plan2, 201, 0, C2[0])
plan2 += sobre_alfred(CADERA, fin_de(L) + 1, 3)
logs["chicken_2"] = ejecutar("chicken_2", plan2, 201, 0, C2[0])

# ===== chicken_3: picotea al norte (z 12); corre desde 735, baja de un salto y se tira a las piernas =====
C3 = [(-18.5, 0.5, 12), (-18.5, -0.5, 12), (-18.5, -1.5, 12), (-18.5, -2.5, 12), (-18.5, -3.5, 12), (-18.5, -4.5, 11)]
plan3 = relleno(C3[0], 1, 824) + tramos(C3, {}, "PERSEGUIDO")
L = ejecutar("chicken_3", plan3, 301, 180, C3[0])
plan3 += [salto(C3[-1], PIERNAS, 0.8)]
L = ejecutar("chicken_3", plan3, 301, 180, C3[0])
plan3 += sobre_alfred(PIERNAS, fin_de(L) + 1, 1)
logs["chicken_3"] = ejecutar("chicken_3", plan3, 301, 180, C3[0])

bpy.app.driver_namespace["_pollos_alfred_logs"] = logs
result = {n: [x for x in L if x[3] >= 690] for n, L in logs.items()}
