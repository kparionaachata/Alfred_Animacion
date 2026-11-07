"""Pose de empuje del brazo derecho indicada por el usuario (la dejo puesta en f39, sin clave): RightUpArm y Rightelbow
toman esos valores en el empuje de los 3 carbones. En cada empuje la pala sigue a la mano derecha con el agarre de esa
pose (pala/antebrazo en f39), con fundido de 4 frames a la entrada y a la salida; el torso gira un poco para apuntar a
cada carbon; luego se re-hornea la mano izquierda sobre el mango y se vuelven a simular los carbones y sus sonidos."""
import bpy, math
from mathutils import Vector, Matrix, Quaternion, Euler
from mathutils.geometry import intersect_point_line
sc = bpy.context.scene
al = bpy.data.objects["Armature"]; pb = al.pose.bones; root = bpy.data.objects["alfred"]; pala = bpy.data.objects["stone_shovel"]
G_ = 9.81 / 24 ** 2
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
A_S, B_S = Vector((-0.31, -0.44, 0.0)), Vector((0.36, 0.29, 0.0))
CARBONES = ["carbon_horno_1", "carbon_horno_2", "carbon_horno_3"]
BASES = [20, 46, 72]; FIN = 112; PISO, FONDO = -9.938, -15.56
PALMA = {"Rightelbow_alfred": Vector((0.032, 0.326, -0.008)), "Leftelbow_alfred": Vector((-0.033, 0.312, -0.005))}
act = al.animation_data.action; cb = act.layers[0].strips[0].channelbag(al.animation_data.action_slot)
pact = pala.animation_data.action; pcb = pact.layers[0].strips[0].channelbag(pala.animation_data.action_slot)
fc_ = lambda bn, i: cb.fcurves.find('pose.bones["%s"].rotation_euler' % bn, index=i)
UP = Vector((0, 0, 1))

# ---------- 1) pose del usuario (valores actuales, sin cambiar de frame) y agarre ----------
F_REF = 39
U = {"RightUpArm_alfred": Euler([math.radians(v) for v in (451.118, 122.901, 406.415)]),
     "Rightelbow_alfred": Euler([math.radians(v) for v in (64.422, -21.81, -92.722)])}      # valores del usuario (f39)
sc.frame_set(F_REF)
for bn, e in U.items(): pb[bn].rotation_euler = e
bpy.context.view_layer.update()
agarre = (al.matrix_world @ pb["Rightelbow_alfred"].matrix).inverted() @ pala.matrix_world
fw = (Vector((-76.47, -15.30, -9.85)) - root.matrix_world.translation); fw.z = 0; fw.normalize()
RIGHT = (al.matrix_world @ pb["RightUpArm_alfred"].head) - (al.matrix_world @ pb["LeftUpArm_alfred"].head); RIGHT.z = 0; RIGHT.normalize()

# ---------- 2) muestrear la trayectoria planeada de la pala ----------
plan = {}
for f in range(1, FIN + 1):
    sc.frame_set(f); plan[f] = pala.matrix_world.copy()

def quitar_claves(fcs, a, b):
    for fc in fcs:
        for k in [k for k in fc.keyframe_points if a < k.co.x < b][::-1]: fc.keyframe_points.remove(k)
        fc.update()
def poner_euler(bn, e, f):
    ref = pb[bn].rotation_euler.copy()
    pb[bn].rotation_euler = e.to_quaternion().to_euler("XYZ", ref); pb[bn].keyframe_insert("rotation_euler", frame=f)
def delta_mundo(bn, axis, ang):
    p = (al.matrix_world @ pb[bn].matrix).to_quaternion() @ pb[bn].rotation_euler.to_quaternion().inverted()
    return (p.inverted() @ Quaternion(axis, ang) @ p).to_euler("XYZ")

# ---------- 3) por carbon: brazo derecho a la pose del usuario + giro del torso para apuntar ----------
ventanas = []; giros = {}; alturas = {}; cabeceos = {}
for c, b0 in zip(CARBONES, BASES):
    cf, pf, hf, rf = b0 + 10, b0 + 16, b0 + 18, b0 + 24
    ventanas.append((c, cf, pf, hf, rf))
    arm_f = [fc_(bn, i) for bn in U for i in range(3)]
    quitar_claves(arm_f, cf, rf)
    for f in (pf - 1, pf, hf):
        sc.frame_set(f)
        for bn, e in U.items(): poner_euler(bn, e, f)
    # apuntar: giro del torso (Spine1/Spine2) alrededor de la vertical, buscado grado a grado (sin pasarse)
    cpos = bpy.data.objects[c].matrix_world.translation.copy()
    sc.frame_set(pf)
    base_sp = {f: {bn: (sc.frame_set(f), pb[bn].rotation_euler.copy())[1] for bn in ("Spine1_alfred", "Spine2_alfred")} for f in (pf - 1, pf, hf)}
    def aplicar(f, ang, cab, insertar):
        sc.frame_set(f)
        for bn in ("Spine1_alfred", "Spine2_alfred"): pb[bn].rotation_euler = base_sp[f][bn]
        bpy.context.view_layer.update()
        for bn in ("Spine1_alfred", "Spine2_alfred"):
            q = Quaternion(UP, ang * 0.5) @ Quaternion(RIGHT, cab * 0.5)
            p_ = (al.matrix_world @ pb[bn].matrix).to_quaternion() @ pb[bn].rotation_euler.to_quaternion().inverted()
            d = (p_.inverted() @ q @ p_).to_euler("XYZ"); e = base_sp[f][bn]
            pb[bn].rotation_euler = (e.x + d.x, e.y + d.y, e.z + d.z)
            if insertar: pb[bn].keyframe_insert("rotation_euler", frame=f)
        bpy.context.view_layer.update()
    def coste(ang, cab):
        aplicar(pf, ang, cab, False)
        tip = (al.matrix_world @ pb["Rightelbow_alfred"].matrix @ agarre) @ B_S
        return abs((tip - cpos).dot(RIGHT)) + abs(tip.z - (PISO + 0.03)) * 1.5 + 2.0 * max(0.0, (tip - cpos).dot(-fw) - 0.05)
    mejor = min(((math.radians(a), math.radians(c_)) for a in range(-25, 26, 2) for c_ in range(-4, 24, 2)), key=lambda x: coste(*x))
    ang, cab = mejor
    for a2 in (-1, 0, 1):
        for c2 in (-1, 0, 1):
            cand = (ang + math.radians(a2), cab + math.radians(c2))
            if coste(*cand) < coste(ang, cab): ang, cab = cand
    for f in (pf - 1, pf, hf): aplicar(f, ang, cab, True)
    sc.frame_set(pf); tipz = ((al.matrix_world @ pb["Rightelbow_alfred"].matrix @ agarre) @ B_S).z
    alturas[c] = round((tipz - PISO) * 100, 1); cabeceos[c] = round(math.degrees(cab))
    giros[c] = round(math.degrees(ang))

# ---------- 4) la pala sigue a la mano en cada empuje (con fundidos) ----------
pala_fc = [c for c in pcb.fcurves if c.data_path in ("location", "rotation_euler")]
for c, cf, pf, hf, rf in ventanas:
    quitar_claves(pala_fc, cf - 1, rf + 1)
for c, cf, pf, hf, rf in ventanas:
    for f in range(cf, rf + 1):
        sc.frame_set(f)
        mano = al.matrix_world @ pb["Rightelbow_alfred"].matrix @ agarre
        w = ss((f - cf) / 4.0) * (1 - ss((f - hf) / float(rf - hf)))
        P = plan[f]
        l = P.translation.lerp(mano.translation, w)
        q = P.to_quaternion().slerp(mano.to_quaternion(), w)
        pala.matrix_world = Matrix.LocRotScale(l, q, P.to_scale())
        pala.keyframe_insert("location", frame=f); pala.keyframe_insert("rotation_euler", frame=f)
for fcu in pcb.fcurves:
    if fcu.data_path == "rotation_euler":
        prev = None
        for k in sorted(fcu.keyframe_points, key=lambda k: k.co.x):
            if prev is not None:
                while k.co.y - prev > math.pi: k.co.y -= 2 * math.pi
                while k.co.y - prev < -math.pi: k.co.y += 2 * math.pi
            prev = k.co.y
        fcu.update()

# ---------- 5) mano izquierda en el mango (IK con polo, horneada; separada de la derecha) ----------
for i in range(3):
    f_ = fc_("LeftUpArm_alfred", i); g_ = fc_("Leftelbow_alfred", i)
    if f_: cb.fcurves.remove(f_)
    if g_: cb.fcurves.remove(g_)
emp = bpy.data.objects.new("_ik_izq", None); polo = bpy.data.objects.new("_polo_izq", None)
sc.collection.objects.link(emp); sc.collection.objects.link(polo)
ik = pb["Leftelbow_alfred"].constraints.new("IK"); ik.name = "_IK_izq"; ik.target = emp; ik.pole_target = polo; ik.chain_count = 2; ik.use_tail = True
palma = lambda bn: (al.matrix_world @ pb[bn].matrix) @ PALMA[bn]
def poner_polo():
    h = al.matrix_world @ pb["LeftUpArm_alfred"].head; polo.location = h - RIGHT * 0.65 - UP * 0.28 - fw * 0.08
sc.frame_set(BASES[0] + 10); poner_polo()
M = pala.matrix_world; emp.location = M @ A_S.lerp(B_S, 0.5)
mejor = None
for a_ in (0, 90, -90, 180):
    ik.pole_angle = math.radians(a_); bpy.context.view_layer.update()
    d = (al.matrix_world @ pb["Leftelbow_alfred"].head - polo.location).length
    if mejor is None or d < mejor[0]: mejor = (d, a_)
ik.pole_angle = math.radians(mejor[1])
ik.mute = True
tl = {}
for f in range(1, FIN + 1):
    sc.frame_set(f); M = pala.matrix_world; a, b = M @ A_S, M @ B_S
    q, t_r = intersect_point_line(palma("Rightelbow_alfred"), a, b)
    h = al.matrix_world @ pb["LeftUpArm_alfred"].head
    cands = [0.30 + 0.38 * k / 38 for k in range(39)]
    t = min(cands, key=lambda t: abs((a.lerp(b, t) - h).length - 0.56) + (5.0 if t < t_r + 0.30 else 0) + 0.05 * abs(t - 0.5))
    tl[f] = t
for _ in range(3):
    tl = {f: sum(tl[g] for g in range(max(1, f - 3), min(FIN, f + 3) + 1)) / (min(FIN, f + 3) - max(1, f - 3) + 1) for f in tl}
ik.mute = False
err = {}; prev = None
for f in range(1, FIN + 1):
    sc.frame_set(f); poner_polo(); M = pala.matrix_world
    obj = M @ A_S.lerp(B_S, tl[f])
    cands = [obj + (al.matrix_world @ pb["Leftelbow_alfred"].tail - palma("Leftelbow_alfred"))] + ([prev[0] + (obj - prev[1])] if prev else [])
    best = None
    for c0 in cands:
        emp.location = c0; bpy.context.view_layer.update(); e_ = (obj - palma("Leftelbow_alfred")).length
        if best is None or e_ < best[0]: best = (e_, c0.copy())
    emp.location = best[1]; e_ = best[0]; paso = 0.9
    for _ in range(14):
        if e_ < 0.004: break
        old = emp.location.copy(); emp.location = old + (obj - palma("Leftelbow_alfred")) * paso; bpy.context.view_layer.update()
        e2 = (obj - palma("Leftelbow_alfred")).length
        if e2 < e_: e_ = e2
        else: emp.location = old; paso *= 0.5; bpy.context.view_layer.update()
    prev = (emp.location.copy(), obj.copy())
    rots = {bn: al.convert_space(pose_bone=pb[bn], matrix=pb[bn].matrix, from_space="POSE", to_space="LOCAL").to_euler("XYZ", pb[bn].rotation_euler) for bn in ("LeftUpArm_alfred", "Leftelbow_alfred")}
    ik.mute = True
    for bn, r in rots.items(): pb[bn].rotation_euler = r; pb[bn].keyframe_insert("rotation_euler", frame=f)
    bpy.context.view_layer.update(); err[f] = round((obj - palma("Leftelbow_alfred")).length * 100, 1)
    ik.mute = False
pb["Leftelbow_alfred"].constraints.remove(ik); bpy.data.objects.remove(emp); bpy.data.objects.remove(polo)

# ---------- 6) carbones: re-simulados con la nueva trayectoria de la hoja ----------
sc.frame_set(1)
info = {}
for i, c in enumerate(CARBONES):
    o = bpy.data.objects[c]
    ad = o.animation_data; a0 = ad.action
    cbc = a0.layers[0].strips[0].channelbag(ad.action_slot)
    l0 = Vector([cbc.fcurves.find("location", index=k).evaluate(1) for k in range(3)])
    r0 = Euler([cbc.fcurves.find("rotation_euler", index=k).evaluate(1) for k in range(3)])
    ad.action = None; bpy.data.actions.remove(a0)
    o.location, o.rotation_euler = l0, r0
    o.keyframe_insert("location", frame=1); o.keyframe_insert("rotation_euler", frame=1)
    borde = l0.dot(fw) - 0.19; s = 0.0; v = 0.0; tocado = None; zs = l0.z + 0.006 * i; gz = 0.08 if i % 2 else -0.06
    for f in range(BASES[i], FIN + 1):
        sc.frame_set(f); tip = pala.matrix_world @ B_S
        av = tip.dot(fw) - borde
        lat = (tip - l0) - fw * (tip - l0).dot(fw); lat.z = 0
        if tocado is None and av >= 0 and lat.length < 0.24 and f <= BASES[i] + 18: tocado = f
        if tocado is None: continue
        if av > s + 1e-4 and f <= BASES[i] + 18: v = av - s; s = av
        elif v > 1e-4: s += v; v = max(0.0, v - 0.55 * G_)
        if (l0 + fw * s).y < FONDO + 0.2: s = (FONDO + 0.2 - l0.y) / fw.y; v = 0.0
        t = f - tocado
        o.location = l0 + fw * s; o.location.z = zs if t >= 1 else l0.z
        o.rotation_euler = ((r0.x * (1 - ss(t / 4))) if r0.x > 0.2 else r0.x, r0.y, r0.z + gz * ss(t / 8))
        o.keyframe_insert("location", frame=f); o.keyframe_insert("rotation_euler", frame=f)
        if v < 1e-4 and f > BASES[i] + 20: break
    if tocado:
        o.location, o.rotation_euler = l0, r0
        o.keyframe_insert("location", frame=tocado - 1); o.keyframe_insert("rotation_euler", frame=tocado - 1)
    for cv in o.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        for k in cv.keyframe_points: k.interpolation = "LINEAR"
    info[c] = {"toca_en": tocado, "entra_cm": round(s * 100, 1)}
# sonidos en los nuevos contactos
S = r"C:\Users\user\Desktop\Alfred_Animacion\sonidos\vanilla\dig"
ed = sc.sequence_editor
for s_ in [s_ for s_ in ed.strips_all if s_.name.startswith("SND_pala_carbon")]: ed.strips.remove(s_)
for i, c in enumerate(CARBONES):
    fc0 = info[c]["toca_en"]
    if fc0:
        a = ed.strips.new_sound("SND_pala_carbon_golpe_%d" % (i + 1), S + r"\stone%d.ogg" % (i + 1), 1, fc0); a.volume = 0.55
        b = ed.strips.new_sound("SND_pala_carbon_raspa_%d" % (i + 1), S + r"\gravel%d.ogg" % (i + 1), 2, fc0 + 1); b.volume = 0.35
# comprobaciones
chk = {}
for c, cf, pf, hf, rf in ventanas:
    sc.frame_set(pf)
    chk[c] = {"brazo_igual_al_usuario": all((pb[bn].rotation_euler.to_quaternion().rotation_difference(U[bn].to_quaternion()).angle) < 0.01 for bn in U),
              "punta": [round(x, 3) for x in pala.matrix_world @ B_S]}
sc.frame_set(F_REF)
result = {"giro_torso_grados": giros, "enderezo_torso_grados": cabeceos, "punta_sobre_piso_cm": alturas, "carbones": info, "empuje": chk, "mano_izq_error_max_cm": max(err.values()), "mano_izq_malos": {f: e for f, e in err.items() if e > 3}}
