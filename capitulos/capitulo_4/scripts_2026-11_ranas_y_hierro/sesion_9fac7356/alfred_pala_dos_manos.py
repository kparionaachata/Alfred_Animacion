"""alfred_buscando_hierro.blend - Alfred empuja con la pala (dos manos) los 3 carbones al fondo del horno, uno por uno.
Rehecho desde cero:
  * Alfred estaba a 0.5 m del horno y la pala mide 0.8 m: el mango le atravesaba el cuerpo. Ahora se gira hacia el
    horno y da un PASO ATRAS (dos pasos cortos) antes de empezar.
  * La pala se anima en el mundo (Child Of 'Mano' en influencia 0 mientras la usa con las dos manos): mango
    apuntando al hueco, inclinado hacia abajo, hoja casi plana; la punta llega exacta a cada carbon.
  * Las DOS manos agarran el mango: derecha cerca del extremo, izquierda a mitad (IK con polo, horneada por frame).
  * Piernas y cadera en su pose natural (sin estirarlas); el torso se inclina al empujar; la cabeza mira el carbon.
  * Carbones (inercia-accion-reaccion): se mueven en el frame en que la hoja los toca, van con la pala, al soltarlos
    deslizan y se frenan por rozamiento; el inclinado se vuelca."""
import bpy, math
from mathutils import Vector, Matrix, Quaternion, Euler
from mathutils.geometry import intersect_point_line
sc = bpy.context.scene
al = bpy.data.objects["Armature"]; root = bpy.data.objects["alfred"]; pb = al.pose.bones
pala = bpy.data.objects["stone_shovel"]
G = 9.81 / 24 ** 2
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
A_S, B_S = Vector((-0.31, -0.44, 0.0)), Vector((0.36, 0.29, 0.0))     # extremo del mango / punta de la hoja (sprite)
ESCALA = 0.82
CARBONES = ["carbon_horno_1", "carbon_horno_2", "carbon_horno_3"]
PISO, FONDO = -9.938, -15.56
EMPUJE = {"carbon_horno_1": 0.27, "carbon_horno_2": 0.27, "carbon_horno_3": 0.22}
BASES = [20, 46, 72]; FIN = 112
ATRAS = 0.45                                      # paso atras para que quepa la pala
PALMA = {"Rightelbow_alfred": Vector((0.032, 0.326, -0.008)), "Leftelbow_alfred": Vector((-0.033, 0.312, -0.005))}
T_MANO = {"Rightelbow_alfred": 0.16, "Leftelbow_alfred": 0.46}        # donde agarra cada mano (0 extremo, 1 punta)

# ---------- estado base (frame 1) y limpieza ----------
sc.frame_set(1)
BASE = {b.name: (b.rotation_euler.copy(), b.location.copy()) for b in pb}
carbon0 = {}
for c in CARBONES:
    o = bpy.data.objects[c]; carbon0[c] = (o.location.copy(), o.rotation_euler.copy())
pala_f1 = pala.matrix_world.copy()
root_loc0, root_rot0 = root.location.copy(), root.rotation_euler.copy()
for o in [al, root, pala] + [bpy.data.objects[c] for c in CARBONES]:
    ad = o.animation_data
    if ad:
        ad.action = None
        for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
for b in pb:
    b.rotation_mode = "XYZ"; b.rotation_euler, b.location = BASE[b.name]
for c, (l, r) in carbon0.items():
    o = bpy.data.objects[c]; o.location, o.rotation_euler = l, r
root.location, root.rotation_euler = root_loc0, root_rot0
for bn in ("Rightelbow_alfred", "Leftelbow_alfred", "Rightknee_alfred", "Leftknee_alfred"):
    for cn in [c for c in pb[bn].constraints if c.name.startswith("_IK")]: pb[bn].constraints.remove(cn)
for n in [o.name for o in bpy.data.objects if o.name.startswith(("_ik_", "_polo_"))]: bpy.data.objects.remove(bpy.data.objects[n])
mano = pala.constraints.get("Mano")
bpy.context.view_layer.update()

# ---------- giro hacia el horno + paso atras (f1-16) ----------
hueco = Vector((-76.47, -15.30, -9.85))
F = (al.matrix_world @ pb["face_alfred"].matrix).to_3x3().col[2]
d0 = hueco - root.matrix_world.translation
giro = (math.atan2(d0.y, d0.x) - math.atan2(F.y, F.x) + math.pi) % (2 * math.pi) - math.pi
fw = d0.copy(); fw.z = 0; fw.normalize()
UP = Vector((0, 0, 1))
root.rotation_mode = "XYZ"
for f, k in ((1, 0.0), (4, 0.3), (8, 0.85), (11, 1.03), (14, 1.0)):
    root.rotation_euler.z = root_rot0.z + giro * k; root.keyframe_insert("rotation_euler", index=2, frame=f)
for f, k in ((1, 0.0), (5, 0.1), (8, 0.55), (11, 0.6), (14, 1.0), (16, 1.0)):
    root.location = root_loc0 - fw * ATRAS * k; root.keyframe_insert("location", frame=f)
root.rotation_euler.z = root_rot0.z + giro; root.location = root_loc0 - fw * ATRAS
bpy.context.view_layer.update()
RIGHT = (al.matrix_world @ pb["RightUpArm_alfred"].head) - (al.matrix_world @ pb["LeftUpArm_alfred"].head); RIGHT.z = 0; RIGHT.normalize()
def delta_mundo(bn, axis, ang):
    p = (al.matrix_world @ pb[bn].matrix).to_quaternion() @ pb[bn].rotation_euler.to_quaternion().inverted()
    return (p.inverted() @ Quaternion(axis, ang) @ p).to_euler("XYZ")
# dos pasos cortos hacia atras: se levanta un muslo y luego el otro (rodilla doblada al levantar)
for f, (ra, rk, la, lk) in ((1, (0, 0, 0, 0)), (4, (-18, 25, 0, 0)), (7, (0, 0, 0, 0)), (9, (0, 0, -18, 25)), (12, (0, 0, 0, 0)), (16, (0, 0, 0, 0))):
    for bn, a in (("RightUpLeg_alfred", ra), ("Rightknee_alfred", rk), ("LeftUpLeg_alfred", la), ("Leftknee_alfred", lk)):
        d = delta_mundo(bn, RIGHT, math.radians(a)); e0 = BASE[bn][0]
        pb[bn].rotation_euler = (e0.x + d.x, e0.y + d.y, e0.z + d.z); pb[bn].keyframe_insert("rotation_euler", frame=f)

# ---------- la pala en el mundo ----------
Lsh = (B_S - A_S).length * ESCALA
def matriz_pala(tip, baja):
    cad = al.matrix_world @ pb["Hips_alfred"].head
    ancla = cad + RIGHT * 0.20 + fw * 0.30 + UP * 0.12        # el mango sale del lado derecho de la cadera
    eje = tip - ancla; eje.z = 0; eje.normalize()
    eje = (eje * math.cos(baja) - UP * math.sin(baja)).normalized()
    side = eje.cross(UP).normalized()
    n = side.cross(eje).normalized()                           # normal de la hoja hacia arriba (hoja casi plana)
    es = (B_S - A_S).normalized(); ns = Vector((0, 0, 1)); ps = ns.cross(es)
    pw = n.cross(eje)
    R = Matrix((eje, pw, n)).transposed() @ Matrix((es, ps, ns)).transposed().inverted()
    S = Matrix.LocRotScale(Vector(), R.to_quaternion(), Vector((ESCALA,) * 3))
    S.translation = tip - (S @ B_S)
    return S
sc.frame_set(16)
poses = []          # (frame, tip, baja, inclinacion_torso)
contacto = {}
for c, b0 in zip(CARBONES, BASES):
    o = bpy.data.objects[c]; cp = o.matrix_world.translation
    toque = Vector((cp.x, cp.y, PISO + 0.03)) - fw * 0.19   # borde del carbon que mira a Alfred
    contacto[c] = (b0 + 10, toque)
    poses += [(b0, toque - fw * 0.10 + UP * 0.05, math.radians(16), 4),
              (b0 + 6, toque - fw * 0.07 + UP * 0.02, math.radians(14), 2),
              (b0 + 10, toque, math.radians(12), 20),
              (b0 + 16, toque + fw * EMPUJE[c], math.radians(11), 42),
              (b0 + 18, toque + fw * (EMPUJE[c] + 0.01), math.radians(11), 40),
              (b0 + 24, toque - fw * 0.10 + UP * 0.05, math.radians(16), 4)]
fin_pose = (FIN - 8, contacto[CARBONES[-1]][1] - fw * 0.42 + UP * 0.16, math.radians(28), 0)
poses.append(fin_pose)
# del frame 1 al 16 la pala va con el cuerpo (como la tenia en la mano) y luego pasa a la pose de trabajo
if mano: mano.influence = 0.0
pala.rotation_mode = "XYZ"
# al principio y al final la lleva con las dos manos delante del cuerpo, inclinada (pose "lista" mas recogida)
sc.frame_set(16)
listo0 = poses[0][1] + UP * 0.04 - fw * 0.03
rel = root.matrix_world.inverted() @ matriz_pala(listo0, math.radians(30))
for f in range(1, 15):
    sc.frame_set(f); pala.matrix_world = root.matrix_world @ rel
    pala.keyframe_insert("location", frame=f); pala.keyframe_insert("rotation_euler", frame=f)
sc.frame_set(16)
for f, tip, baja, inc in poses:
    sc.frame_set(f); pala.matrix_world = matriz_pala(tip, baja)
    pala.keyframe_insert("location", frame=f); pala.keyframe_insert("rotation_euler", frame=f)
sc.frame_set(FIN); pala.matrix_world = root.matrix_world @ rel
pala.keyframe_insert("location", frame=FIN); pala.keyframe_insert("rotation_euler", frame=FIN)
pala.scale = (ESCALA,) * 3
# euler continuo
for c in pala.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
    if c.data_path == "rotation_euler":
        prev = None
        for k in c.keyframe_points:
            if prev is not None:
                while k.co.y - prev > math.pi: k.co.y -= 2 * math.pi
                while k.co.y - prev < -math.pi: k.co.y += 2 * math.pi
            prev = k.co.y
    for k in c.keyframe_points: k.interpolation = "BEZIER"; k.handle_left_type = k.handle_right_type = "AUTO_CLAMPED"
    c.update()

# ---------- torso: se inclina al empujar ----------
for f, tip, baja, inc in [(16, None, 0, 0)] + poses + [(FIN, None, 0, 0)]:
    sc.frame_set(f)
    for bn, frac in (("Spine1_alfred", 0.55), ("Spine2_alfred", 0.45)):
        e0 = BASE[bn][0]; d = delta_mundo(bn, RIGHT, -math.radians(inc) * frac)
        pb[bn].rotation_euler = (e0.x + d.x, e0.y + d.y, e0.z + d.z); pb[bn].keyframe_insert("rotation_euler", frame=f)

# ---------- manos en el mango: IK con polo, horneada frame a frame ----------
def palma(bn): return (al.matrix_world @ pb[bn].matrix) @ PALMA[bn]
iks = {}
for bn, lado in (("Rightelbow_alfred", 1), ("Leftelbow_alfred", -1)):
    e = bpy.data.objects.new("_ik_" + bn, None); p = bpy.data.objects.new("_polo_" + bn, None)
    sc.collection.objects.link(e); sc.collection.objects.link(p)
    c = pb[bn].constraints.new("IK"); c.name = "_IK_mano"; c.target = e; c.pole_target = p; c.chain_count = 2; c.use_tail = True
    iks[bn] = (c, e, p, lado)
def colocar_polos():
    for bn, (c, e, p, lado) in iks.items():
        hombro = al.matrix_world @ pb[bn.replace("elbow", "UpArm")].head
        p.location = hombro + RIGHT * 0.65 * lado - UP * 0.28 - fw * 0.08      # codos bien abiertos hacia fuera
# angulo de polo: el que deja el codo mas cerca del polo
sc.frame_set(BASES[0] + 10); colocar_polos()
for bn, (c, e, p, lado) in iks.items():
    M = pala.matrix_world; e.location = M @ A_S.lerp(B_S, T_MANO[bn])
    mejor = None
    for ang in (0, 90, -90, 180):
        c.pole_angle = math.radians(ang); bpy.context.view_layer.update()
        codo = al.matrix_world @ pb[bn].head
        d = (codo - p.location).length
        if mejor is None or d < mejor[0]: mejor = (d, ang)
    c.pole_angle = math.radians(mejor[1])
# punto de agarre por frame: las manos se deslizan por el mango para quedar a una distancia comoda del hombro
BANDA = {"Rightelbow_alfred": (0.02, 0.34, 0.40), "Leftelbow_alfred": (0.32, 0.68, 0.56)}   # t min, t max, distancia ideal (m)
for c, e, p, lado in iks.values(): c.mute = True
t_f = {bn: {} for bn in iks}
for f in range(1, FIN + 1):
    sc.frame_set(f); M = pala.matrix_world
    for bn in iks:
        hombro = al.matrix_world @ pb[bn.replace("elbow", "UpArm")].head
        tmin, tmax, ideal = BANDA[bn]
        t_f[bn][f] = min((tmin + (tmax - tmin) * k / 40 for k in range(41)),
                         key=lambda t: abs((M @ A_S.lerp(B_S, t) - hombro).length - ideal) + 0.05 * abs(t - T_MANO[bn]))
for bn in iks:                                   # suavizado (no tiembla el agarre)
    for _ in range(3):
        sm = {f: sum(t_f[bn][g] for g in range(max(1, f - 3), min(FIN, f + 3) + 1)) / (min(FIN, f + 3) - max(1, f - 3) + 1) for f in t_f[bn]}
        t_f[bn] = sm
SEP_T = 0.30                                     # manos separadas en el mango (~34 cm): no se solapan
for f in t_f["Leftelbow_alfred"]:
    tr, tl = t_f["Rightelbow_alfred"][f], t_f["Leftelbow_alfred"][f]
    if tl - tr < SEP_T:
        mid = (tl + tr) / 2; t_f["Rightelbow_alfred"][f] = max(0.02, mid - SEP_T / 2); t_f["Leftelbow_alfred"][f] = t_f["Rightelbow_alfred"][f] + SEP_T
for c, e, p, lado in iks.values(): c.mute = False
err = {}; prev_emp = {}; prev_obj = {}
for f in range(1, FIN + 1):
    sc.frame_set(f); colocar_polos()
    M = pala.matrix_world
    for bn, (c, e, p, lado) in iks.items():
        obj = M @ A_S.lerp(B_S, t_f[bn][f])
        cands = [obj + (al.matrix_world @ pb[bn].tail - palma(bn))]
        if bn in prev_emp: cands.append(prev_emp[bn] + (obj - prev_obj[bn]))      # coherencia con el frame anterior
        best = None
        for c0 in cands:
            e.location = c0; bpy.context.view_layer.update(); er = (obj - palma(bn)).length
            if best is None or er < best[0]: best = (er, c0.copy())
        e.location = best[1]; er = best[0]; paso = 0.9
        for _ in range(14):
            if er < 0.004: break
            dlt = obj - palma(bn); prueba = e.location + dlt * paso
            old_loc = e.location.copy(); e.location = prueba; bpy.context.view_layer.update()
            er2 = (obj - palma(bn)).length
            if er2 < er: er = er2
            else: e.location = old_loc; paso *= 0.5; bpy.context.view_layer.update()
        prev_emp[bn] = e.location.copy(); prev_obj[bn] = obj.copy()
    bpy.context.view_layer.update()
    rots = {}
    for bn in iks:
        for b in (bn.replace("elbow", "UpArm"), bn):
            rots[b] = al.convert_space(pose_bone=pb[b], matrix=pb[b].matrix, from_space="POSE", to_space="LOCAL").to_euler("XYZ", pb[b].rotation_euler)
    for c, e, p, lado in iks.values(): c.mute = True
    for b, r in rots.items(): pb[b].rotation_euler = r; pb[b].keyframe_insert("rotation_euler", frame=f)
    bpy.context.view_layer.update()
    err[f] = tuple(round((M @ A_S.lerp(B_S, t_f[bn][f]) - palma(bn)).length * 100, 1) for bn in iks)
    for c, e, p, lado in iks.values(): c.mute = False
for bn, (c, e, p, lado) in iks.items():
    pb[bn].constraints.remove(c); bpy.data.objects.remove(e); bpy.data.objects.remove(p)
act = al.animation_data.action
for c in act.layers[0].strips[0].channelbags[0].fcurves:
    if "UpArm" in c.data_path or "elbow" in c.data_path:
        for k in c.keyframe_points: k.interpolation = "LINEAR"

# ---------- cabeza: mira el carbon de turno ----------
def mirar(objetivo, f, w):
    for bn, frac, mx in (("Neck_alfred", 0.5, 35), ("face_alfred", 1.0, 40)):
        base = pb[bn].rotation_euler.copy(); R = base.to_matrix()
        P = pb[bn].matrix.to_3x3() @ R.inverted(); cara = pb["face_alfred"]
        v = (pb[bn].matrix.to_3x3().inverted() @ cara.matrix.col[2].xyz.normalized()).normalized()
        t = (P.inverted() @ (al.matrix_world.inverted() @ objetivo - cara.head)).normalized()
        q = (R @ v).normalized().rotation_difference(t)
        e = (Quaternion(q.axis, min(q.angle * frac, math.radians(mx)) * w).to_matrix() @ R).to_euler("XYZ", base)
        pb[bn].rotation_euler = e; pb[bn].keyframe_insert("rotation_euler", frame=f); bpy.context.view_layer.update()
for f in range(10, FIN + 1, 2):
    sc.frame_set(f)
    cc = next((c for c, b0 in zip(CARBONES, BASES) if f < b0 + 22), CARBONES[-1])
    w = ss((f - 10) / 6) * (1 - ss((f - (FIN - 12)) / 10))
    mirar(bpy.data.objects[cc].matrix_world.translation + UP * 0.05, f, w)

# ---------- carbones: los mueve la hoja (contacto real) y deslizan con su inercia ----------
info = {}
for i, c in enumerate(CARBONES):
    o = bpy.data.objects[c]; l0, r0 = carbon0[c]
    o.rotation_mode = "XYZ"; o.location, o.rotation_euler = l0, r0
    o.keyframe_insert("location", frame=1); o.keyframe_insert("rotation_euler", frame=1)
    borde = l0.dot(fw) - 0.19
    s = 0.0; v = 0.0; tocado = None; zs = l0.z + 0.006 * i; giro_z = 0.08 if i % 2 else -0.06
    for f in range(BASES[i], FIN + 1):
        sc.frame_set(f); tip = pala.matrix_world @ B_S
        avance_tip = tip.dot(fw) - borde                         # cuanto ha entrado la hoja pasado el borde del carbon
        lateral = ((tip - l0) - fw * (tip - l0).dot(fw)); lateral.z = 0; lateral = lateral.length
        if tocado is None and avance_tip >= 0 and lateral < 0.22 and f <= BASES[i] + 18:
            tocado = f
        if tocado is None: continue
        if avance_tip > s + 1e-4 and f <= BASES[i] + 18: v = avance_tip - s; s = avance_tip    # la hoja lo empuja
        else:
            if v > 1e-4: s += v; v = max(0.0, v - 0.55 * G)                                    # desliza y frena
        if (l0 + fw * s).y < FONDO + 0.2:                       # tope: pared del fondo del horno
            s = (FONDO + 0.2 - l0.y) / fw.y; v = 0.0
        t = f - tocado
        rx = r0.x * (1 - ss(t / 4)) if r0.x > 0.2 else r0.x
        o.location = l0 + fw * s; o.location.z = zs if t >= 1 else l0.z
        o.rotation_euler = (rx, r0.y, r0.z + giro_z * ss(t / 8))
        o.keyframe_insert("location", frame=f); o.keyframe_insert("rotation_euler", frame=f)
        if v < 1e-4 and f > BASES[i] + 20: break
    if tocado:
        o.location, o.rotation_euler = l0, r0
        o.keyframe_insert("location", frame=tocado - 1); o.keyframe_insert("rotation_euler", frame=tocado - 1)
    for cv in o.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        for k in cv.keyframe_points: k.interpolation = "LINEAR"
    info[c] = {"toca_en": tocado, "entra_cm": round(s * 100, 1)}

# ---------- sonidos ----------
S = r"C:\Users\user\Desktop\Alfred_Animacion\sonidos\vanilla\dig"
ed = sc.sequence_editor or sc.sequence_editor_create()
for s_ in [s_ for s_ in ed.strips_all if s_.name.startswith("SND_pala_carbon")]: ed.strips.remove(s_)
for i, c in enumerate(CARBONES):
    fc = info[c]["toca_en"]
    if not fc: continue
    a = ed.strips.new_sound("SND_pala_carbon_golpe_%d" % (i + 1), S + r"\stone%d.ogg" % (i + 1), 1, fc); a.volume = 0.55
    b = ed.strips.new_sound("SND_pala_carbon_raspa_%d" % (i + 1), S + r"\gravel%d.ogg" % (i + 1), 2, fc + 1); b.volume = 0.35

# ---------- comprobaciones ----------
holgura = {}
for f in range(1, FIN + 1, 3):
    sc.frame_set(f); M = pala.matrix_world; a, b = M @ A_S, M @ B_S
    puntos = [al.matrix_world @ pb[n].head for n in ("Hips_alfred", "Spine1_alfred", "Spine2_alfred", "Neck_alfred")]
    dmin = 9
    for pnt in puntos:
        q, l = intersect_point_line(pnt, a, b); l = max(0, min(1, l)); q = a.lerp(b, l)
        dmin = min(dmin, (pnt - q).length)
    holgura[f] = round(dmin * 100)
sep = {}
for f in range(1, FIN + 1, 3):
    sc.frame_set(f)
    a1, b1 = al.matrix_world @ pb["Rightelbow_alfred"].head, palma("Rightelbow_alfred")
    a2, b2 = al.matrix_world @ pb["Leftelbow_alfred"].head, palma("Leftelbow_alfred")
    dmin = min((a1.lerp(b1, i / 6) - a2.lerp(b2, j / 6)).length for i in range(7) for j in range(7))
    sep[f] = round(dmin * 100)
result = {"separacion_antebrazos_min_cm": min(sep.values()), "sep_muestras": dict(list(sep.items())[::5]), "agarre_t": {bn[:4]: (round(min(t_f[bn].values()), 2), round(max(t_f[bn].values()), 2)) for bn in t_f}, "errores_mano_por_frame_cm(der,izq)": {f: e for f, e in err.items() if max(e) > 2}, "giro": round(math.degrees(giro), 1), "manos_error_max_cm": max(max(e) for e in err.values()), "carbones": info,
          "distancia_mango_columna_min_cm": min(holgura.values()), "muestras_holgura": dict(list(holgura.items())[::4])}
