"""alfred_buscando_hierro.blend: Alfred, con la pala de piedra en la MANO DERECHA (skill herramienta-mano-derecha: Child Of
'Mano' a Rightelbow_alfred con loc/rot/escala fijas), se gira hacia el horno y empuja los 3 carbones del hueco del
combustible hacia adentro, uno por uno. Detalle por carbon: prepara (lleva la pala hacia atras), mete la pala rapido
hasta tocar el carbon, lo empuja (el cuerpo se inclina, el brazo izquierdo hace contrapeso, la cabeza mira al carbon) y
retira la pala. Fisica (skill inercia-accion-reaccion): el carbon empieza a moverse EN el frame del contacto, va con la
pala mientras lo empuja y al soltarlo sigue deslizando con su inercia y se frena por rozamiento; el carbon inclinado se
vuelca y queda plano. Brazo por IK temporal (constraint IK + objetivo empty) horneado a claves; la IK se quita despues.
Sonidos: golpe de la pala al tocar cada carbon y raspado al arrastrarlo."""
import bpy, math
from mathutils import Vector, Matrix, Quaternion, Euler
sc = bpy.context.scene
al = bpy.data.objects["Armature"]; root = bpy.data.objects["alfred"]; pb = al.pose.bones
pala = bpy.data.objects["stone_shovel"]
G = 9.81 / 24 ** 2
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
PUNTA = Vector((0.36, 0.29, 0.0))             # punto de la hoja de la pala (coords del sprite) que empuja
CARBONES = ["carbon_horno_1", "carbon_horno_2", "carbon_horno_3"]
PISO, FONDO = -9.938, -15.56                  # hueco del combustible: piso y pared del fondo (y)
EMPUJE = {"carbon_horno_1": 0.27, "carbon_horno_2": 0.27, "carbon_horno_3": 0.22}
BASES = [16, 42, 68]                          # frame de inicio de cada empuje
FIN = 108
PALA_LOC = (0.3021, 0.48578, -0.02626)
PALA_ROT = (-7.142, -21.913, 1.384)

# ---------- limpieza / estado base ----------
sc.frame_set(1)
for o in [al, root, pala] + [bpy.data.objects[c] for c in CARBONES]:
    ad = o.animation_data                        # quita acciones/NLA pero conserva los drivers
    if ad:
        ad.action = None
        for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
for c in [c for c in pala.constraints]: pala.constraints.remove(c)
for c in [c for c in pb["Rightelbow_alfred"].constraints if c.name == "_IK_pala"]: pb["Rightelbow_alfred"].constraints.remove(c)
for n in ("_ik_obj_pala",):
    if n in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[n])
inicio_carbon = {c: (bpy.data.objects[c].location.copy(), bpy.data.objects[c].rotation_euler.copy()) for c in CARBONES}
pose0 = {b.name: (b.rotation_euler.copy(), b.location.copy()) for b in pb}
for b in pb: b.rotation_mode = "XYZ"

# ---------- pala en la mano derecha (valores fijos de la skill) ----------
ch = pala.constraints.new("CHILD_OF"); ch.name = "Mano"; ch.target = al; ch.subtarget = "Rightelbow_alfred"
ch.inverse_matrix = Matrix.Identity(4); ch.influence = 1.0
pala.parent = None; pala.rotation_mode = "XYZ"
# agarre a dos manos: valores de la pala que dejo el usuario en Blender (sustituyen a los de la skill en esta animacion)
pala.location = PALA_LOC
pala.rotation_euler = [math.radians(d) for d in PALA_ROT]
pala.scale = (0.82, 0.82, 0.82)
pala.hide_viewport = pala.hide_render = False; pala.hide_set(False)
punta = lambda: pala.matrix_world @ PUNTA

# ---------- giro hacia el horno (f1-10) ----------
hueco = Vector((-76.47, -15.30, -9.85))
F = (al.matrix_world @ pb["face_alfred"].matrix).to_3x3().col[2]
yaw_cara = math.atan2(F.y, F.x); d0 = hueco - root.matrix_world.translation
yaw_obj = math.atan2(d0.y, d0.x)
giro = (yaw_obj - yaw_cara + math.pi) % (2 * math.pi) - math.pi
rz0 = root.rotation_euler.z; root.rotation_mode = "XYZ"
for f, k in ((1, 0.0), (4, 0.25), (7, 0.8), (10, 1.03), (12, 1.0)):
    root.rotation_euler.z = rz0 + giro * k; root.keyframe_insert("rotation_euler", index=2, frame=f)
root.rotation_euler.z = rz0 + giro
# pasito al girar: rodillas
for f, a in ((1, 0), (4, 10), (7, -6), (10, 4), (12, 0)):
    for b, s in (("RightUpLeg_alfred", 1), ("LeftUpLeg_alfred", -1)):
        e = pose0[b][0].copy(); e.x += math.radians(a * s); pb[b].rotation_euler = e; pb[b].keyframe_insert("rotation_euler", frame=f)

# ---------- ejes del cuerpo ya girado ----------
sc.frame_set(12)
fw = (hueco - al.matrix_world @ pb["Hips_alfred"].head); fw.z = 0; fw.normalize()
UP = Vector((0, 0, 1)); LAT = fw.cross(UP).normalized()
def delta_mundo(bn, axis, ang):
    p = (al.matrix_world @ pb[bn].matrix).to_quaternion() @ pb[bn].rotation_euler.to_quaternion().inverted()
    return (p.inverted() @ Quaternion(axis, ang) @ p).to_euler("XYZ")

# ---------- brazo derecho exacto a partir de la pala deseada ----------
A_S, B_S = Vector((-0.31, -0.44, 0.0)), Vector((0.36, 0.29, 0.0))      # mango y hoja en coords del sprite
Lfix = Matrix.LocRotScale(pala.location, Euler(pala.rotation_euler, "XYZ").to_quaternion(), pala.scale)
def matriz_pala(tip, baja):
    """pala con la punta en `tip`, el mango apuntando hacia el horno (fw) inclinado `baja` rad hacia abajo y la hoja
    casi horizontal (normal del sprite hacia arriba)"""
    eje = (fw * math.cos(baja) - UP * math.sin(baja)).normalized()
    n = eje.cross(LAT).normalized()
    if n.z < 0: n = -n
    pw = n.cross(eje)
    es = (B_S - A_S).normalized(); ns = Vector((0, 0, 1)); ps = ns.cross(es)
    Rw = Matrix((eje, pw, n)).transposed(); Rs = Matrix((es, ps, ns)).transposed()
    R = Rw @ Rs.inverted()
    S = Matrix.LocRotScale(Vector(), R.to_quaternion(), pala.scale)
    S.translation = tip - (S @ PUNTA)
    return S
def resolver(tip, baja=math.radians(10)):
    """coloca RightUpArm/Rightelbow para que la pala quede en matriz_pala(tip); mueve la cadera (adelante/atras y
    algo hacia abajo) si el brazo no llega. Devuelve rotaciones locales, desplazamiento de cadera y error (m)."""
    S = matriz_pala(tip, baja)
    Fm = S @ Lfix.inverted()                                   # antebrazo deseado (mundo)
    E = Fm.translation
    up_b = pb["RightUpArm_alfred"]; Lu = (al.matrix_world.to_3x3() @ (up_b.tail - up_b.head)).length
    H0 = al.matrix_world @ up_b.head
    # desplazamiento de la cadera a lo largo de fw (y un poco de bajada) para que |E-H| = Lu
    mejor = None
    for dz in (0.0, -0.03, -0.06, -0.09, -0.12):
        H1 = H0 + Vector((0, 0, dz)); d = E - H1
        bq = -2 * d.dot(fw); cq = d.dot(d) - Lu * Lu; disc = bq * bq - 4 * cq
        if disc >= 0:
            for r_ in ((-bq + math.sqrt(disc)) / 2, (-bq - math.sqrt(disc)) / 2):
                cand = (abs(r_) + abs(dz) * 2, r_, dz)
                if mejor is None or cand[0] < mejor[0]: mejor = cand
    if mejor is None: mejor = (0, 0.0, 0.0)
    _, dl, dz = mejor
    return S, Fm, E, dl, dz
def aplicar_brazo(f, Fm, E):
    up_b = pb["RightUpArm_alfred"]; fo = pb["Rightelbow_alfred"]
    bpy.context.view_layer.update()
    H = al.matrix_world @ up_b.head
    Mw = al.matrix_world @ up_b.matrix
    y_now = (Mw.to_3x3() @ Vector((0, 1, 0))).normalized()
    q = y_now.rotation_difference((E - H).normalized())
    nuevo = Matrix.LocRotScale(H, q @ Mw.to_quaternion(), Mw.to_scale())
    loc = al.convert_space(pose_bone=up_b, matrix=al.matrix_world.inverted() @ nuevo, from_space="POSE", to_space="LOCAL")
    up_b.rotation_euler = loc.to_euler("XYZ", up_b.rotation_euler); up_b.keyframe_insert("rotation_euler", frame=f)
    bpy.context.view_layer.update()
    Fp = al.matrix_world.inverted() @ Fm
    Fp = Matrix.LocRotScale((al.matrix_world.inverted() @ (al.matrix_world @ fo.head)), Fp.to_quaternion(), fo.matrix.to_scale())
    loc = al.convert_space(pose_bone=fo, matrix=Fp, from_space="POSE", to_space="LOCAL")
    fo.rotation_euler = loc.to_euler("XYZ", fo.rotation_euler); fo.keyframe_insert("rotation_euler", frame=f)
    bpy.context.view_layer.update()

def poner_cuerpo(f, inclinacion, brazo_izq, cadera=0.0, extra=Vector()):
    """inclina el torso hacia el horno, contrapeso del brazo izquierdo y empuje de cadera (claves en f)"""
    for bn, frac in (("Spine1_alfred", 0.55), ("Spine2_alfred", 0.45)):
        e0 = pose0[bn][0]; d = delta_mundo(bn, LAT, -inclinacion * frac)
        pb[bn].rotation_euler = (e0.x + d.x, e0.y + d.y, e0.z + d.z); pb[bn].keyframe_insert("rotation_euler", frame=f)
    l0 = pose0["Hips_alfred"][1]
    Mh = (al.matrix_world.to_3x3() @ pb["Hips_alfred"].bone.matrix_local.to_3x3()).inverted()
    pb["Hips_alfred"].location = l0 + Mh @ (fw * cadera + extra); pb["Hips_alfred"].keyframe_insert("location", frame=f)

claves = []        # (frame, objetivo_punta, inclinacion, brazo_izq, cadera)
listo = lambda: hueco + fw * -0.38 + Vector((0, 0, 0.10))           # pala lista, delante de la boca del horno
contacto = {}
for c, b0 in zip(CARBONES, BASES):
    o = bpy.data.objects[c]
    cpos = o.matrix_world.translation.copy()
    toque = Vector((cpos.x, cpos.y + 0.14, PISO + 0.035))             # borde del carbon que mira a Alfred
    contacto[c] = (b0 + 10, toque)
    claves += [(b0, listo(), math.radians(2), math.radians(-4), 0.0),
               (b0 + 6, toque + fw * -0.17 + Vector((0, 0, 0.04)), math.radians(-3), math.radians(6), -0.03),    # prepara
               (b0 + 10, toque, math.radians(9), math.radians(-10), 0.05),                                        # toca
               (b0 + 16, toque + fw * EMPUJE[c], math.radians(14), math.radians(-14), 0.08),                      # empuja
               (b0 + 18, toque + fw * (EMPUJE[c] + 0.01), math.radians(13), math.radians(-12), 0.07),
               (b0 + 24, listo(), math.radians(3), math.radians(-3), 0.01)]                                        # retira
claves = [(12, listo(), 0.0, 0.0, 0.0)] + claves + [(FIN - 10, listo(), 0.0, 0.0, 0.0)]
errores = []
for f, obj, inc, bi, cad in claves:
    sc.frame_set(f); poner_cuerpo(f, inc, bi, cad)
    bpy.context.view_layer.update()
    S, Fm, E, dl, dz = resolver(obj, math.radians(22) if (obj - listo()).length < 1e-6 else math.radians(10))
    poner_cuerpo(f, inc, bi, cad, extra=fw * dl + Vector((0, 0, dz)))
    bpy.context.view_layer.update()
    S, Fm, E, dl2, dz2 = resolver(obj, math.radians(22) if (obj - listo()).length < 1e-6 else math.radians(10))
    aplicar_brazo(f, Fm, E)
    errores.append((f, round((obj - punta()).length * 100, 1), round(dl * 100), round(dz * 100)))
# reposo al final: vuelve a bajar la pala
for bn in ("RightUpArm_alfred", "Rightelbow_alfred", "LeftUpArm_alfred", "Spine1_alfred", "Spine2_alfred"):
    pb[bn].rotation_euler = pose0[bn][0]; pb[bn].keyframe_insert("rotation_euler", frame=FIN)
pb["Hips_alfred"].location = pose0["Hips_alfred"][1]; pb["Hips_alfred"].keyframe_insert("location", frame=FIN)
# brazo derecho al inicio (antes del giro termina) = pose original
for bn in ("RightUpArm_alfred", "Rightelbow_alfred"):
    pb[bn].rotation_euler = pose0[bn][0]; pb[bn].keyframe_insert("rotation_euler", frame=1)
# el golpe hacia adentro es rapido y el empuje decelera
act = al.animation_data.action
for c in act.layers[0].strips[0].channelbags[0].fcurves:
    for k in c.keyframe_points: k.interpolation = "BEZIER"; k.handle_left_type = k.handle_right_type = "AUTO_CLAMPED"
    c.update()

# ---------- cabeza: mira el carbon que va a empujar ----------
def mirar(objetivo_f, f, w):
    for bn, frac, mx in (("Neck_alfred", 0.5, 40), ("face_alfred", 1.0, 45)):
        base = pb[bn].rotation_euler.copy(); R = base.to_matrix()
        P = pb[bn].matrix.to_3x3() @ R.inverted()
        cara = pb["face_alfred"]
        v = (pb[bn].matrix.to_3x3().inverted() @ cara.matrix.col[2].xyz.normalized()).normalized()
        t = (P.inverted() @ (al.matrix_world.inverted() @ objetivo_f - cara.head)).normalized()
        q = (R @ v).normalized().rotation_difference(t)
        e = (Quaternion(q.axis, min(q.angle * frac, math.radians(mx)) * w).to_matrix() @ R).to_euler("XYZ", base)
        pb[bn].rotation_euler = e; pb[bn].keyframe_insert("rotation_euler", frame=f)
        bpy.context.view_layer.update()
for f in range(8, FIN + 1, 2):
    sc.frame_set(f)
    act_c = next((c for c, b0 in zip(CARBONES, BASES) if f < b0 + 22), CARBONES[-1])
    w = ss((f - 8) / 6) * (1 - ss((f - (FIN - 12)) / 10))
    mirar(bpy.data.objects[act_c].matrix_world.translation + Vector((0, 0, 0.05)), f, w)

# ---------- carbones: empujados por la pala y deslizando con su inercia ----------
info = {}
for i, c in enumerate(CARBONES):
    o = bpy.data.objects[c]; l0, r0 = inicio_carbon[c]
    fc, toque = contacto[c]
    o.rotation_mode = "XYZ"
    o.location = l0; o.rotation_euler = r0
    o.keyframe_insert("location", frame=1); o.keyframe_insert("rotation_euler", frame=1)
    o.keyframe_insert("location", frame=fc - 1); o.keyframe_insert("rotation_euler", frame=fc - 1)
    sc.frame_set(fc); off = l0 - punta()
    yprev = l0.y; v = 0.0; empujando = True; y = l0.y; f = fc
    giro_z = (0.08 if i % 2 else -0.06); zs = l0.z + 0.006 * i      # alturas distintas: sin parpadeo entre carbones
    while f <= FIN:
        sc.frame_set(f)
        if empujando:
            ytip = punta().y + off.y
            if ytip < y - 1e-4: v = ytip - y; y = ytip         # la pala lo lleva (solo empuja hacia adentro)
            else: empujando = f < fc + 6
            if f >= fc + 7: empujando = False
        else:
            if abs(v) > 1e-4:
                y += v; dec = 0.55 * G                         # rozamiento carbon-piedra (mu ~0.55)
                v = min(0.0, v + dec) if v < 0 else max(0.0, v - dec)
        if y < FONDO + 0.2: y = FONDO + 0.2; v = 0.0            # tope: la pared del fondo
        t = f - fc
        rx = r0.x * (1 - ss(t / 4)) + (0.12 * math.sin(math.pi * min(1, t / 6)) if r0.x > 0.2 and t < 6 else 0)   # el inclinado se vuelca
        o.location = (l0.x + (y - l0.y) * 0.05, y, zs if r0.x > 0.2 and t >= 4 else (l0.z if t < 1 else zs))
        o.rotation_euler = (rx if r0.x > 0.2 else r0.x, r0.y, r0.z + giro_z * ss(t / 8))
        o.keyframe_insert("location", frame=f); o.keyframe_insert("rotation_euler", frame=f)
        if not empujando and abs(v) < 1e-4 and t > 10: break
        f += 1
    info[c] = {"contacto": fc, "entra_cm": round((l0.y - y) * 100, 1)}
    for cv in o.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        for k in cv.keyframe_points: k.interpolation = "LINEAR"

# ---------- sonidos ----------
S = r"C:\Users\user\Desktop\Alfred_Animacion\sonidos\vanilla\dig"
ed = sc.sequence_editor or sc.sequence_editor_create()
for s in [s for s in ed.strips_all if s.name.startswith("SND_pala_carbon")]: ed.strips.remove(s)
for i, c in enumerate(CARBONES):
    fc = contacto[c][0]
    a = ed.strips.new_sound("SND_pala_carbon_golpe_%d" % (i + 1), S + r"\stone%d.ogg" % (i + 1), 1, fc); a.volume = 0.55
    b = ed.strips.new_sound("SND_pala_carbon_raspa_%d" % (i + 1), S + r"\gravel%d.ogg" % (i + 1), 2, fc + 1); b.volume = 0.35
# ---------- comprobacion: pala nunca invertida y metida en el hueco ----------
chk = []
for f in range(1, FIN + 1, 4):
    sc.frame_set(f); M = pala.matrix_world
    d = (M @ Vector((0.17, 0.2, 0))) - (M @ Vector((-0.31, -0.44, 0)))
    chk.append((f, round(d.normalized().z, 2)))
result = {"giro_grados": round(math.degrees(giro), 1), "error_punta_cm": errores, "carbones": info, "pala_z_mango_cabeza": chk[::2]}
