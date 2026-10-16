# -*- coding: utf-8 -*-
"""Parte 11 (base_parte_11.blend): ALFRED SENTADO EN LA ORILLA SE SACA LAS FLECHAS y las TIRA AL MAR.
- Sentado (poses/sentado.json) en (-95.5, -69.5) sobre la piedra (z 8.0), mirando al mar (+x).
- Una por una: (1) antebrazo izquierdo (la saca con la mano derecha), (2) antebrazo derecho (con la izquierda), (3) pecho, (4) frente, (5) entrepierna.
  Para cada flecha: la agarra (el brazo herido se pone delante del cuerpo), la MUEVE DE UN LADO AL OTRO varias veces (gira sobre su punta clavada)
  con DOLOR en cada vaiven (se encoge, aprieta los ojos), la arranca de un tiron (dolor fuerte), la mira, y la LANZA AL MAR (vuela, gira y se hunde).
- Respiracion, mirada a la flecha / al mar; el dolor es corporal (se encoge).
- La CAMARA y las MALLAS DE LOS OJOS no se tocan (las maneja el usuario). Jerry no se toca.
- Pose sentada: poses/sentado.json con los valores del usuario en Hips (location y rotacion) y en las rodillas.
Repetible: rehace sus propias acciones (p11_*). Las flechas se desemparentan la primera vez (su desplazamiento respecto al hueso queda en `p11_off`)."""
import bpy, math, json, random
from mathutils import Vector, Matrix, Euler, Quaternion

sc = bpy.context.scene; vl = bpy.context.view_layer
X0, Y0 = -95.5, -69.5                                                     # donde se sienta (pedido del usuario)
FWD = Vector((1, 0, 0)); UP = Vector((0, 0, 1))                           # mira al mar (+x)
POSE = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\poses\sentado.json"
ss = lambda t: 0.0 if t <= 0 else (1.0 if t >= 1 else t * t * (3 - 2 * t))
rng = random.Random(11)

ARM = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'Hips_alfred' in o.pose.bones); AR = ARM.parent
PB = ARM.pose.bones; W = lambda: ARM.matrix_world
MESH_A = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("Mesh_") and o.name.endswith("_alfred")]
OJOS = [bpy.data.objects[n] for n in ("ojo_izquierdo_alfred", "ojo_derecho_alfred") if n in bpy.data.objects]
FORMAS = ("Cerrado", "Enojado", "Cansado", "Triste")

# ---------------- 0) limpiar lo propio (repetible) ----------------
def quitar_accion(idb):
    ad = getattr(idb, "animation_data", None)
    if ad and ad.action:
        a = ad.action; ad.action = None
        if a.users == 0: bpy.data.actions.remove(a)
for idb in [ARM, AR] + [bpy.data.objects.get(n) for n in ("flecha_alfred", "flecha_mano_der", "flecha_mano_izq", "flecha_entrepierna", "flecha_pecho")]:
    if idb: quitar_accion(idb)

# ---------------- 1) flechas: desplazamiento respecto a su hueso (se guarda la primera vez) ----------------
D_LOC = Vector((1, 1, 0)).normalized()                                     # eje de la flecha en su malla (hacia la punta)
FL = {}
for n in ("flecha_mano_izq", "flecha_mano_der", "flecha_pecho", "flecha_alfred", "flecha_entrepierna"):
    o = bpy.data.objects.get(n)
    if o is None: continue
    if "p11_off" not in o.keys():
        hb = o.parent_bone; Mb = W() @ PB[hb].matrix; off = Mb.inverted() @ o.matrix_world
        o["p11_hueso"] = hb; o["p11_off"] = [v for fila in off for v in fila]
    off = Matrix([o["p11_off"][i * 4:(i + 1) * 4] for i in range(4)])
    mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw; o.rotation_mode = 'QUATERNION'
    co = [v.co.copy() for v in o.data.vertices]
    punta = max(co, key=lambda c: c.dot(D_LOC)); cola = min(co, key=lambda c: c.dot(D_LOC))
    FL[n] = dict(obj=o, hueso=o["p11_hueso"], off=off, punta=punta, cola=cola, largo=(punta - cola).dot(D_LOC) * o.matrix_world.to_scale().x)

# ---------------- 2) pose sentada, mirando al mar, apoyada en la piedra ----------------
SENT = json.load(open(POSE, encoding="utf-8"))["poses"][0]["bones"]
BASE = {b.name: Euler((0, 0, 0)) for b in PB}; HIPS_LOC = Vector((0, 0, 0))
for n, b in SENT.items():
    if n in BASE:
        r_ = b["local_space"]["rotation_euler_rad"]; BASE[n] = Euler((r_["x"], r_["y"], r_["z"]))
        if n == "Hips_alfred": l_ = b["local_space"]["location"]; HIPS_LOC = Vector((l_["x"], l_["y"], l_["z"]))
# valores del usuario (desde el inicio de la animacion esta sentado asi)
d_ = math.radians
BASE["Hips_alfred"] = Euler((d_(-36.137), d_(-26.364), d_(3.1163))); HIPS_LOC = Vector((-0.14355, -0.64523, 0.34342))
BASE["Rightknee_alfred"] = Euler((d_(-41.616), d_(-14.717), d_(-25.909)))
BASE["Leftknee_alfred"] = Euler((d_(-46.992), d_(9.3128), d_(16.91)))
for pb in PB: pb.rotation_mode = 'XYZ'; pb.location = (0, 0, 0); pb.scale = (1, 1, 1)
PB["Hips_alfred"].location = HIPS_LOC


EJE_CAIDA = UP.cross(FWD).normalized()                                    # girar sobre el: la cabeza va hacia el mar y la cara hacia abajo


def rot_raiz(raiz):
    """raiz = (x, y, z, yaw[, caida, ladeo]): caida gira hacia el mar (boca abajo), ladeo rueda sobre la direccion del mar"""
    if len(raiz) <= 4: return Euler((0, 0, raiz[3]))
    lad = raiz[5] if len(raiz) > 5 else 0.0
    return (Matrix.Rotation(lad, 3, FWD) @ Matrix.Rotation(raiz[4], 3, EJE_CAIDA) @ Matrix.Rotation(raiz[3], 3, 'Z')).to_euler('XYZ')


def poner(p, raiz):
    AR.location = raiz[:3]; AR.rotation_mode = 'XYZ'; AR.rotation_euler = rot_raiz(raiz)
    for n, e in p.items(): PB[n].rotation_euler = e
    vl.update()


def verts_mundo(o):
    """vertices deformados (funciona tambien en modo Edicion, donde `evaluado.data` llega vacio)"""
    dg = bpy.context.evaluated_depsgraph_get(); e = o.evaluated_get(dg); m = e.to_mesh(); M = e.matrix_world
    out = [M @ v.co for v in m.vertices]; e.to_mesh_clear(); return out


def ojos_centro():
    pts = [p_ for o in OJOS for p_ in verts_mundo(o)]
    return sum(pts, Vector()) / max(len(pts), 1)


def frente_cara():
    """direccion hacia donde mira la cara (centro de la cabeza -> ojos), horizontal"""
    Mf = W() @ PB["face_alfred"].matrix; c = Mf @ Vector((0, PB["face_alfred"].bone.length * 0.5, 0))
    d = ojos_centro() - c; d.z = 0
    return d.normalized(), c


poner(BASE, (X0, Y0, 9.0, 0.0)); fw, _ = frente_cara()
YAW = math.atan2(FWD.y, FWD.x) - math.atan2(fw.y, fw.x)
poner(BASE, (X0, Y0, 9.0, YAW))
h = (W() @ PB["Hips_alfred"].head); RX, RY = X0 + (X0 - h.x), Y0 + (Y0 - h.y)


def es_ajeno(o):
    o = o.original
    return (o.type != 'MESH' or o.name.startswith(("flecha", "sombrero", "miga", "Short_Grass", "Tall_Grass", "Fern", "Poppy", "Dandelion", "Allium", "Azure", "Seagrass"))
            or o.name.endswith(("_alfred", "_jerry")) or (o.parent is not None and o.parent.type == 'ARMATURE'))
cache = {}
def piso_xy(x, y):
    k = (round(x * 4) / 4, round(y * 4) / 4)
    if k in cache: return cache[k]
    dg = bpy.context.evaluated_depsgraph_get(); p = Vector((k[0] + 0.0031, k[1] + 0.0027, 12.0)); z = 8.0       # +3 mm: nunca en la arista entre bloques
    for _ in range(14):
        ok, l, n, i, o, m = sc.ray_cast(dg, p, Vector((0, 0, -1)), distance=10)
        if not ok: break
        if es_ajeno(o): p = l - Vector((0, 0, 0.01)); continue
        z = l.z; break
    cache[k] = z; return z


poner(BASE, (RX, RY, 9.0, YAW)); dz = 1e9
for o in MESH_A:
    for w in verts_mundo(o): dz = min(dz, w.z - piso_xy(w.x, w.y))
assert dz < 1e8, "no se pudieron leer las mallas de Alfred"
RZ = 9.0 + 0.005 - dz; RAIZ = (RX, RY, RZ, YAW)
RAIZ = (-95.718, -69.583, 8.0, math.radians(-57.838)); YAW = RAIZ[3]          # valor del empty `alfred` dado por el usuario
poner(BASE, RAIZ)
print("ALFRED sentado: raiz (%.2f, %.2f, %.2f) yaw %.0f grados" % (RX, RY, RZ, math.degrees(YAW)))

# ---------------- 3) ejes locales (calibrados): inclinarse hacia delante y girar el torso ----------------
def eje_que_mueve(bone, punto_bone, direccion, ang=0.15):
    """indice y signo del eje local de `bone` que, al rotarlo, mueve `punto_bone` (head) en `direccion`"""
    mejor = None; base = PB[bone].rotation_euler.copy()
    p0 = W() @ PB[punto_bone].head
    for i in range(3):
        e = base.copy(); e[i] += ang; PB[bone].rotation_euler = e; vl.update()
        d = (W() @ PB[punto_bone].head - p0).dot(direccion)
        if mejor is None or abs(d) > abs(mejor[1]): mejor = (i, d)
    PB[bone].rotation_euler = base; vl.update()
    return mejor[0], (1.0 if mejor[1] > 0 else -1.0)
INCL = {b: eje_que_mueve(b, "Neck_alfred", FWD) for b in ("Spine1_alfred", "Spine2_alfred")}       # + = hacia delante
lado_der = ((W() @ PB["RightUpArm_alfred"].head) - (W() @ PB["LeftUpArm_alfred"].head)).normalized()
GIRO = eje_que_mueve("Spine1_alfred", "RightUpArm_alfred", -FWD)                                   # + = hombro derecho hacia atras
CAB = eje_que_mueve("Neck_alfred", "face_alfred", -UP)                                             # + = cabeza hacia abajo (asiente)

# ---------------- 3b) centro del PUNO (en el espacio del hueso del antebrazo): el hueso sigue ~30 cm mas alla de la mano ----------------
def centro_puno(lado):
    pb = PB[lado + "elbow_alfred"]; Mi = (W() @ pb.matrix).inverted(); pts = []
    for o in MESH_A:
        g = o.vertex_groups.get(pb.name)
        if not g: continue
        dg = bpy.context.evaluated_depsgraph_get(); e = o.evaluated_get(dg); m = e.to_mesh(); M = e.matrix_world
        for v in o.data.vertices:
            if any(gg.group == g.index and gg.weight > 0.5 for gg in v.groups): pts.append(Mi @ (M @ m.vertices[v.index].co))
        e.to_mesh_clear()
    ymax = max(p_.y for p_ in pts); fin = [p_ for p_ in pts if p_.y > ymax - 0.12]
    return sum(fin, Vector()) / len(fin)
MANO = {l: centro_puno(l) for l in ("Right", "Left")}
print("PUNO (espacio del antebrazo):", {l: tuple(round(x, 3) for x in v) for l, v in MANO.items()})

# ---------------- 4) cinematica analitica (sin actualizar la escena): brazos (IK de 2 huesos) y mirada ----------------
def M0(bname, Mpadre):
    b = PB[bname].bone; return Mpadre @ b.parent.matrix_local.inverted() @ b.matrix_local


def rot_en(M, pivote, q):
    return Matrix.Translation(pivote) @ q.to_matrix().to_4x4() @ Matrix.Translation(-pivote) @ M


def mezclar(e_base, Mb0, Mdes, w):
    qb = e_base.to_quaternion(); qi = (Mb0.inverted() @ Mdes).to_quaternion()
    if qb.dot(qi) < 0: qi.negate()
    q = qb.slerp(qi, w); return q.to_euler('XYZ', e_base), Mb0 @ q.to_matrix().to_4x4()


def ik(lado, objetivo_w, polo_w, Mp, eu_b, ee_b, w):
    """brazo `lado` ('Right'/'Left'): la mano (punta del antebrazo) a `objetivo_w`, el codo hacia `polo_w`. Devuelve eulers y matrices"""
    up, el = lado + "UpArm_alfred", lado + "elbow_alfred"; Wi = W().inverted()
    M0u = M0(up, Mp["Spine2_alfred"]); S = M0u.translation
    rest_u = PB[up].bone.matrix_local; E0 = M0u @ (rest_u.inverted() @ PB[el].bone.head_local)
    a = (E0 - S).length; b = MANO[lado].length; T = Wi @ objetivo_w; P = (Wi.to_3x3() @ polo_w).normalized()
    d = max(abs(a - b) + 1e-3, min(a + b - 1e-3, (T - S).length)); n = (T - S).normalized()
    ca = (a * a + d * d - b * b) / (2 * a * d); sa = math.sqrt(max(0.0, 1 - ca * ca))
    pp = P - n * P.dot(n); pp = pp.normalized() if pp.length > 1e-6 else n.orthogonal().normalized()
    E = S + n * a * ca + pp * a * sa
    Mu_ik = rot_en(M0u, S, (E0 - S).rotation_difference(E - S))
    eu, Mu = mezclar(eu_b, M0u, Mu_ik, w)
    M0e = Mu @ rest_u.inverted() @ PB[el].bone.matrix_local; He = M0e.translation; Te = M0e @ MANO[lado]
    Me_ik = rot_en(M0e, He, (Te - He).rotation_difference(T - He))
    ee, Me = mezclar(ee_b, M0e, Me_ik, w)
    return eu, ee, Mu, Me


# frente de la cara en el espacio del hueso face (con los ojos), para la mirada
poner(BASE, RAIZ); fw0, _ = frente_cara()
FRENTE_LOCAL = ((W() @ PB["face_alfred"].matrix).to_3x3().inverted() @ fw0).normalized()


def mirar(objetivo_w, w, Mp, en_b, ef_b, maximo=55):
    Wi = W().inverted(); M0n = M0("Neck_alfred", Mp["Spine2_alfred"]); Mn = M0n @ en_b.to_matrix().to_4x4()
    M0f = Mn @ PB["Neck_alfred"].bone.matrix_local.inverted() @ PB["face_alfred"].bone.matrix_local; Mf = M0f @ ef_b.to_matrix().to_4x4()
    centro = Mf @ Vector((0, PB["face_alfred"].bone.length * 0.5, 0)); d = (Wi @ objetivo_w - centro).normalized()
    f = (Mf.to_3x3() @ FRENTE_LOCAL).normalized(); q = f.rotation_difference(d)
    ang = min(q.angle, math.radians(maximo)) * w; q = Quaternion(q.axis, ang) if q.angle > 1e-5 else Quaternion()
    qn = Quaternion().slerp(q, 0.4); Mn2 = rot_en(Mn, Mn.translation, qn); en, Mn = mezclar(en_b, M0n, Mn2, 1.0)
    M0f = Mn @ PB["Neck_alfred"].bone.matrix_local.inverted() @ PB["face_alfred"].bone.matrix_local; Mf = M0f @ ef_b.to_matrix().to_4x4()
    f = (Mf.to_3x3() @ FRENTE_LOCAL).normalized(); q2 = f.rotation_difference(d)
    ang2 = min(q2.angle, math.radians(maximo)) * w * 0.85; q2 = Quaternion(q2.axis, ang2) if q2.angle > 1e-5 else Quaternion()
    Mf2 = rot_en(Mf, Mf.translation, q2); ef, Mf = mezclar(ef_b, M0f, Mf2, 1.0)
    return en, ef, Mn, Mf


# ---------------- 5) guion ----------------
# (flecha, mano que la saca, brazo que la presenta, vaivenes, inclinacion del torso)
GUION = [("flecha_mano_izq", "Right", "Left", 3, 0.10), ("flecha_mano_der", "Left", "Right", 3, 0.10), ("flecha_pecho", "Right", None, 4, 0.14),
         ("flecha_alfred", "Right", None, 3, 0.02), ("flecha_entrepierna", "Right", None, 2, 0.22)]
GUION = [g for g in GUION if g[0] in FL]
T_INI = 5; ALC, PER, EXT, MIRA, PREP, LANZ, SIG, VUELTA, PAUSA = 14, 12, 10, 8, 10, 5, 9, 12, 6
EV = []; t = T_INI
for n, mano, pres, nv, incl in GUION:
    e = dict(n=n, mano=mano, pres=pres, nv=nv, incl=incl, r0=t); e["m0"] = t + ALC; e["e0"] = e["m0"] + nv * PER; e["l0"] = e["e0"] + EXT
    e["t0"] = e["l0"] + MIRA; e["rel"] = e["t0"] + PREP + 3; e["fin"] = e["t0"] + PREP + LANZ + SIG + VUELTA
    e["amp"] = math.radians(rng.uniform(11, 16)); e["dist"] = rng.uniform(3.5, 5.0); e["lat"] = rng.uniform(-0.9, 0.9)
    EV.append(e); t = e["fin"] + PAUSA
FIN = t + 34
# ---- 5b) el PAN: cuando Jerry termina "anda ve por tu comida", Alfred responde (voz_alfred_ultimo_pan_parte11.py) mientras saca un pan
# de su espalda con la mano derecha, lo levanta delante de la cara y lo mira ORGULLOSO (pecho afuera); al final lo baja al regazo.
# La voz de Jerry empieza en e0(entrepierna)+5-31+1 y dura 99 frames -> termina en e0+73; Alfred responde 6 frames despues.
PAN0 = EV[-1]["e0"] + 79 if EV else FIN
# Justo cuando lo levanta entra volando la PALOMA (paloma_roba_pan_parte11.py): tiran del pan de un lado al otro, la paloma gana y se lo
# lleva volando; Alfred, sentado, la sigue con la mirada. Aqui se decide la trayectoria del PAN (la paloma la sigue con el pico).
# el audio de Alfred (voz_alfred_ultimo_pan) dura 101 frames: termina en PAN0+100; la paloma ENTRA 5 frames despues (pedido del usuario)
# y tarda 40 en llegar. Forcejeo con las DOS manos; al ganar la paloma, el tiron lo lanza AL MAR y queda FLOTANDO BOCA ABAJO.
PAN = dict(f0=PAN0, r0=PAN0 - 2, atras=PAN0 + 14, saca=PAN0 + 17, frente=PAN0 + 36, entra=PAN0 + 105, llega=PAN0 + 145, gana=PAN0 + 211)
PAN["cae"] = PAN["gana"] + 22                 # toca el agua
TIRON = 16                                   # frames de cada tiron (ida y vuelta)
FIN = max(FIN, PAN["cae"] + 50, sc.frame_end)            # flotando hasta el final de la escena
sc.frame_start = 1; sc.frame_end = max(FIN, sc.frame_end)          # no acorta la escena (el cerdo puede llegar mas lejos)
sc["p11_tiempos"] = {"T_INI": T_INI, "FIN": FIN, "pan_tiron": TIRON, **{e["n"] + "_" + k: e[k] for e in EV for k in ("r0", "m0", "e0", "rel", "fin")}, **{"pan_" + k: v for k, v in PAN.items()}}
DOLOR = []                                                                  # (frame, fuerza)
for e in EV:
    for k in range(e["nv"]):
        DOLOR.append((e["m0"] + k * PER + PER // 4, 0.45 + 0.1 * k)); DOLOR.append((e["m0"] + k * PER + 3 * PER // 4, 0.4 + 0.1 * k))
    DOLOR.append((e["e0"] + 6, 1.0))


def dolor(f):
    v = 0.0
    for fe, a in DOLOR:
        x = f - fe
        if -3 <= x < 0: v = max(v, a * (1 + x / 3.0))
        elif 0 <= x < 16: v = max(v, a * math.exp(-x / 5.0))
    return v


def env(f, a, b, ent=6, sal=6):
    """0 antes de a, sube en `ent` frames, 1 hasta b, baja en `sal` frames"""
    return ss((f - a) / float(ent)) * (1.0 - ss((f - b) / float(sal)))


# ---------------- 6) recorrido frame a frame ----------------
KH = []; KR = []
# pose FLOTANDO boca abajo, RELAJADA (no rigida): brazos medio abiertos hacia delante y caidos, codos y rodillas algo doblados, cabeza caida.
# Los ejes de cada hueso se MIDEN en la pose boca abajo (que eje lleva la mano/rodilla hacia donde se quiere).
P_FLOTA = Vector((RAIZ[0], RAIZ[1], 0.0)) + FWD * 2.4                      # lejos de la orilla: ahi el mar es mas hondo (fondo a z 6)
R_FL = (P_FLOTA.x, P_FLOTA.y, 0.0, RAIZ[3], math.pi / 2)
FLOTA = {n_: [0.0, 0.0, 0.0] for n_ in BASE}
# cadera al flotar: valores del usuario (Hips_alfred)
HIPS_FLOTA = Vector((0.06497, -0.004343, -0.084386)); FLOTA["Hips_alfred"] = [d_(-1.4824), d_(-37.266), d_(1.8205)]
PB["Hips_alfred"].location = HIPS_FLOTA


def _eje(hueso, punto, direccion, ang=0.2):
    """(indice, signo) del eje local de `hueso` que mueve `punto()` hacia `direccion` en la pose actual de FLOTA"""
    mejor = None
    for i in range(3):
        e = [v for v in FLOTA[hueso]]; poner({n_: Euler(v_) for n_, v_ in FLOTA.items()}, R_FL); p0 = punto()
        e[i] += ang; q = dict(FLOTA); q[hueso] = e; poner({n_: Euler(v_) for n_, v_ in q.items()}, R_FL)
        d = (punto() - p0).dot(direccion)
        if mejor is None or abs(d) > abs(mejor[1]): mejor = (i, d)
    poner({n_: Euler(v_) for n_, v_ in FLOTA.items()}, R_FL)
    return mejor[0], (1.0 if mejor[1] > 0 else -1.0)


def _mover(hueso, punto, direccion, ang):
    i, sg = _eje(hueso, punto, direccion); FLOTA[hueso][i] += sg * ang; return (i, sg)


EJES_FL = {}
for lado_, sl in (("Right", 1.0), ("Left", -1.0)):
    fuera = lado_der * sl
    codo = lambda l=lado_: W() @ PB[l + "elbow_alfred"].head
    mano = lambda l=lado_: W() @ PB[l + "elbow_alfred"].matrix @ MANO[l]
    EJES_FL[lado_ + "UpArm_alfred"] = _mover(lado_ + "UpArm_alfred", codo, FWD, 0.75)          # brazos hacia delante (hacia la cabeza)
    _mover(lado_ + "UpArm_alfred", codo, fuera, 0.35)                                          # y abiertos
    EJES_FL[lado_ + "elbow_alfred"] = _mover(lado_ + "elbow_alfred", mano, -UP, 0.45)          # antebrazos caidos (codo doblado)
    if lado_ + "UpLeg_alfred" in PB:
        rod = lambda l=lado_: W() @ PB[l + "knee_alfred"].head
        EJES_FL[lado_ + "UpLeg_alfred"] = _mover(lado_ + "UpLeg_alfred", rod, fuera, 0.16)      # piernas un poco abiertas
        pie = lambda l=lado_: W() @ PB[l + "knee_alfred"].tail
        EJES_FL[lado_ + "knee_alfred"] = _mover(lado_ + "knee_alfred", pie, -UP, 0.30)          # rodillas un poco dobladas, pies hacia abajo
EJES_FL["Neck_alfred"] = _mover("Neck_alfred", lambda: W() @ PB["face_alfred"].tail, -UP, 0.30)   # cabeza caida
EJES_FL["Spine1_alfred"] = _mover("Spine1_alfred", lambda: W() @ PB["Neck_alfred"].head, -UP, 0.10)  # espalda un poco curvada
FLOTA = {n_: tuple(v_) for n_, v_ in FLOTA.items()}
# altura: que FLOTE de verdad, con el torso a medias fuera del agua (el 45% mas alto del cuerpo queda sobre la superficie 7.89)
poner({n_: Euler(v_) for n_, v_ in FLOTA.items()}, R_FL)
_zs = sorted(w_.z for o_ in MESH_A for w_ in verts_mundo(o_))
P_FLOTA.z = 7.89 - _zs[int(len(_zs) * 0.55)]
PB["Hips_alfred"].location = HIPS_LOC; poner(BASE, RAIZ)
K = {pb.name: [] for pb in PB}; KO = {f_: [] for f_ in FORMAS}; KF = {n: [] for n in FL}; VIS = {n: [] for n in FL}; KPAN = []; VPAN = []
# el pan en la mano: plano del item de MCprep de canto hacia la cara, un poco por delante del puno
PAN_OFF = Matrix.Translation(Vector((0.0, 0.06, 0.0))) @ Euler((math.radians(90), 0, math.radians(90))).to_matrix().to_4x4()
mano_rel = {}; vuelo = {}; prev_q = {}
cerrado_parp = set()
for f0 in range(70, FIN, 1):
    if rng.random() < 1 / 70.0 and all(abs(f0 - x) > 30 for x in cerrado_parp): cerrado_parp.add(f0)
for F in range(1, FIN + 1):
    p = {n: e.copy() for n, e in BASE.items()}
    act = next((e for e in EV if e["r0"] - 4 <= F < e["fin"]), None); I = dolor(F)
    # torso: respiracion, inclinacion hacia la flecha, encogerse de dolor, giro al lanzar
    resp = math.sin(F / 24.0 * 2 * math.pi / (3.2 - 1.0 * min(1.0, I + (0.3 if act else 0)))) * 0.02
    inc = (act["incl"] * env(F, act["r0"], act["l0"], 12, 10) if act else 0.0) + 0.07 * I + resp
    gir = 0.0
    if act:
        tt = F - act["t0"]; sgn = 1.0 if act["mano"] == "Right" else -1.0
        gir = sgn * (0.35 * ss(tt / PREP) - 0.65 * ss((tt - PREP) / LANZ) + 0.3 * ss((tt - PREP - LANZ - SIG) / VUELTA)) if tt >= 0 else 0.0
        inc += 0.12 * (ss((tt - PREP) / LANZ) - ss((tt - PREP - LANZ - SIG) / VUELTA)) if tt >= 0 else 0.0
    for b_, frac in (("Spine1_alfred", 0.45), ("Spine2_alfred", 0.55)):
        i_, s_ = INCL[b_]; e_ = list(p[b_]); e_[i_] += s_ * inc * frac
        if b_ == "Spine1_alfred": e_[GIRO[0]] += GIRO[1] * gir
        p[b_] = Euler(e_)
    i_, s_ = CAB; e_ = list(p["Neck_alfred"]); e_[i_] += s_ * (0.05 * I + 0.25 * math.sin(F * 1.7) * 0.02 * I); p["Neck_alfred"] = Euler(e_)
    raiz_F = RAIZ; hips_F = HIPS_LOC.copy()
    if F >= PAN["gana"]:                                                    # LANZADO AL MAR por el tiron de la paloma
        k = max(0, F - PAN["gana"] - 3); AIRE = float(PAN["cae"] - PAN["gana"])          # la paloma arranca primero; 3 frames despues sale el
        u = min(1.0, k / AIRE); wc = ss(u); flota = max(0, F - PAN["cae"] - 3)
        for n_ in p:                                                        # de sentado a estirado
            fl = FLOTA.get(n_, (0.0, 0.0, 0.0))
            p[n_] = Euler([a_ * (1 - wc) + b_ * wc for a_, b_ in zip(p[n_], fl)])
        # en el aire agita brazos y piernas (manotea y patalea); al caer al agua quedan flojos y se mecen despacio
        agita = math.sin(math.pi * u) if k <= AIRE else 0.0
        flojo = 0.12 * min(1.0, flota / 20.0)
        if flota:                                                           # flotando: brazos, piernas y cabeza se mecen sueltos con el agua
            for b_, (i_, s_) in EJES_FL.items():
                fase_ = (sum(map(ord, b_)) % 100) / 100.0 * 2 * math.pi; am_ = 0.16 if "Arm" in b_ or "elbow" in b_ else (0.10 if "Leg" in b_ or "knee" in b_ else 0.06)
                e_ = list(p[b_]); e_[i_] += s_ * am_ * math.sin(flota / (34.0 + 9 * (sum(map(ord, b_)) % 5)) + fase_) * min(1.0, flota / 15.0); p[b_] = Euler(e_)
        for lado_, fase_ in (("Right", 0.0), ("Left", 2.1)):
            e_ = list(p[lado_ + "UpArm_alfred"]); e_[0] += 0.75 * agita * math.sin(k * 0.95 + fase_) + flojo * math.sin(flota / 19.0 + fase_); e_[2] += 0.45 * agita * math.sin(k * 0.7 + fase_ + 1.0); p[lado_ + "UpArm_alfred"] = Euler(e_)
            e_ = list(p[lado_ + "elbow_alfred"]); e_[0] += 0.5 * agita * math.sin(k * 1.2 + fase_); p[lado_ + "elbow_alfred"] = Euler(e_)
            for pierna_ in (lado_ + "UpLeg_alfred",):
                if pierna_ in p: e_ = list(p[pierna_]); e_[0] += 0.55 * agita * math.sin(k * 0.85 + fase_ + 0.5) + 0.6 * flojo * math.sin(flota / 23.0 + fase_); p[pierna_] = Euler(e_)
            if lado_ + "knee_alfred" in p: e_ = list(p[lado_ + "knee_alfred"]); e_[0] -= 0.45 * agita * abs(math.sin(k * 0.85 + fase_)); p[lado_ + "knee_alfred"] = Euler(e_)
        hips_F = HIPS_LOC.lerp(HIPS_FLOTA, wc)
        # trayectoria: sale disparado hacia el mar (no roza la orilla), sube, cae de panza; se HUNDE un poco y vuelve a FLOTAR en la superficie
        uh = 1 - (1 - u) ** 2
        pos = Vector(RAIZ[:3]).lerp(P_FLOTA, uh); pos.z = RAIZ[2] + (P_FLOTA.z - RAIZ[2]) * u * u + 0.55 * math.sin(math.pi * u) * (1 - u * 0.3)
        if flota:
            hunde = -0.16 * math.sin(math.pi * min(1.0, flota / 12.0)) if flota < 12 else 0.0                 # se hunde por el golpe y sale
            rebote = 0.05 * math.exp(-max(0, flota - 12) / 14.0) * math.sin(max(0, flota - 12) / 3.5) if flota >= 12 else 0.0
            pos = pos + UP * (hunde + rebote + 0.02 * math.sin(flota / 13.0) + 0.01 * math.sin(flota / 5.3)) + (FWD * 0.6 - lado_der * 0.25) * 0.0025 * flota   # se mece y la corriente lo arrastra
        caida = (math.pi / 2) * ss(min(1.0, u * 1.1)) + 0.18 * math.sin(math.pi * u) * (1 - u)                # gira un poco de mas y se asienta
        caida += 0.03 * math.sin(flota / 17.0) if flota else 0.0
        ladeo = 0.22 * math.sin(math.pi * u) * math.sin(k * 0.35) + (0.07 * math.sin(flota / 23.0) + 0.03 * math.sin(flota / 9.0) if flota else 0.0)
        raiz_F = (pos.x, pos.y, pos.z, RAIZ[3] + 0.04 * math.sin(flota / 31.0), caida, ladeo)
    PB["Hips_alfred"].location = hips_F; KH.append(hips_F.copy()); KR.append(raiz_F)
    poner(p, raiz_F)
    Mp = {pb.name: pb.matrix.copy() for pb in PB}
    # ---- flechas pegadas a su hueso (las que todavia estan clavadas) ----
    def pegada(n):
        d = FL[n]; return W() @ Mp[d["hueso"]] @ d["off"]
    mirar_a = None; w_mira = 0.0
    if act:
        n = act["n"]; d = FL[n]; o = d["obj"]
        # brazo que presenta la flecha (antebrazo herido delante del cuerpo)
        if act["pres"]:
            wp = env(F, act["r0"] - 4, act["l0"], 12, 10); lp = act["pres"]
            centro = W() @ Mp["Spine2_alfred"].to_translation()
            objp = centro + FWD * 0.42 - UP * 0.05 + (lado_der if lp == "Left" else -lado_der) * 0.05
            eu, ee, Mu, Me = ik(lp, objp, -UP + (-lado_der if lp == "Left" else lado_der) * 0.7, Mp, p[lp + "UpArm_alfred"], p[lp + "elbow_alfred"], wp)
            p[lp + "UpArm_alfred"], p[lp + "elbow_alfred"] = eu, ee; Mp[lp + "UpArm_alfred"], Mp[lp + "elbow_alfred"] = Mu, Me
        Mfl = pegada(n); eje = (Mfl.to_3x3() @ D_LOC).normalized(); punta = Mfl @ d["punta"]
        tm = F - act["m0"]; vaiven = 0.0; saque = 0.0
        if 0 <= tm < act["nv"] * PER:
            k = tm // PER; vaiven = act["amp"] * math.sin(2 * math.pi * tm / PER) * ss(tm / 4.0) * (1.0 - 0.15 * k)
            saque = 0.012 * (k + ss((tm % PER) / PER))
        elif tm >= act["nv"] * PER:
            saque = 0.012 * act["nv"]
        te = F - act["e0"]; saque += 0.17 * ss(te / EXT) if te >= 0 else 0.0
        lat = eje.cross(UP); lat = lat.normalized() if lat.length > 1e-3 else lado_der
        R = Matrix.Translation(punta) @ Quaternion(lat, vaiven).to_matrix().to_4x4() @ Quaternion(eje, 0.4 * vaiven).to_matrix().to_4x4() @ Matrix.Translation(-punta)
        Mfl = Matrix.Translation(-eje * saque) @ R @ Mfl
        eje_v = (Mfl.to_3x3() @ D_LOC).normalized(); agarre = (Mfl @ d["punta"]) - eje_v * min(0.42 * d["largo"], 0.32)
        mano = act["mano"]; S = W() @ Mp[mano + "UpArm_alfred"].to_translation(); lado = (lado_der if mano == "Right" else -lado_der)
        tl = F - act["t0"]
        if F < act["l0"]:
            objm = agarre; wm = ss((F - act["r0"]) / float(ALC)); mirar_a = agarre; w_mira = 0.9
        else:
            # mira la flecha, la prepara detras del hombro, la lanza y acompana el gesto
            Pm = S + FWD * 0.32 + UP * 0.05 + lado * 0.05                                  # delante, a la altura del hombro (la mira)
            Pw = S - FWD * 0.22 + UP * 0.48 + lado * 0.12                                  # preparada detras de la cabeza
            Pr = S + FWD * 0.48 + UP * 0.52                                                # suelta
            Pf = S + FWD * 0.62 + UP * 0.02 - lado * 0.10                                  # acompana
            P0 = mano_rel.setdefault(n + "_ext", agarre)
            if tl < 0: objm = P0.lerp(Pm, ss((F - act["l0"]) / float(MIRA)))
            elif tl < PREP: objm = Pm.lerp(Pw, ss(tl / float(PREP)))
            elif tl < PREP + LANZ: objm = Pw.lerp(Pr, ss((tl - PREP) / float(LANZ - 2))) if tl < PREP + LANZ - 2 else Pr.lerp(Pf, (tl - PREP - LANZ + 2) / 2.0 * 0.3)
            elif tl < PREP + LANZ + SIG: objm = Pr.lerp(Pf, 0.3 + 0.7 * ss((tl - PREP - LANZ) / float(SIG)))
            else: objm = Pf
            wm = 1.0 - ss((tl - PREP - LANZ - SIG) / float(VUELTA)) if tl >= PREP + LANZ + SIG else 1.0
            mirar_a = (P0 if tl < 0 else S + FWD * 4.0 + UP * 0.3); w_mira = 0.9 if tl < 0 else 0.7
        polo = -UP + lado * 0.8 - FWD * 0.2
        eu, ee, Mu, Me = ik(mano, objm, polo, Mp, p[mano + "UpArm_alfred"], p[mano + "elbow_alfred"], wm)
        p[mano + "UpArm_alfred"], p[mano + "elbow_alfred"] = eu, ee; Mp[mano + "UpArm_alfred"], Mp[mano + "elbow_alfred"] = Mu, Me
        Mmano = W() @ Me @ Matrix.Translation(MANO[mano])
        if F == act["e0"]: mano_rel[n] = Mmano.inverted() @ Mfl                      # al arrancarla la flecha ya va EN LA MANO (aunque el brazo no llegue al recorrido ideal)
        if act["e0"] <= F <= act["rel"] and n in mano_rel: Mfl = Mmano @ mano_rel[n]
        if F == act["rel"]: vuelo[n] = dict(M=Mfl.copy(), f=F)
        if F <= act["rel"]: act["_Mfl"] = Mfl
    else:
        mirar_a = (W() @ Mp["Spine2_alfred"].to_translation()) + FWD * 0.5 - UP * 0.6 if F < T_INI else (W() @ Mp["Spine2_alfred"].to_translation()) + FWD * 5 - UP * 0.2
        w_mira = 0.6
    # ---- el pan (despues de las flechas) ----
    Mpan = None
    if F >= PAN["r0"]:
        S = W() @ Mp["RightUpArm_alfred"].to_translation(); lado = lado_der
        Pa = S - FWD * 0.30 - UP * 0.32 + lado * 0.16                          # detras de la espalda
        Pf = S + FWD * 0.18 + UP * 0.62 - lado * 0.06                          # LEVANTADO AL AIRE delante, por encima de la cabeza (pedido del usuario)
        Pt = S + FWD * 0.54 + UP * 0.14 - lado * 0.10                          # forcejeo: lo baja a la altura de la cara (brazo doblado, puede tirar)
        Pr = S + FWD * 0.32 - UP * 0.32 - lado * 0.06                          # mano vacia en el regazo
        llevado = F >= PAN["gana"]
        if F < PAN["atras"]: objm = Pr.lerp(Pa, ss((F - PAN["r0"]) / float(PAN["atras"] - PAN["r0"]))); wm = ss((F - PAN["r0"]) / 6.0)
        elif F < PAN["saca"]: objm = Pa; wm = 1.0
        elif F < PAN["frente"]: objm = Pa.lerp(Pf, ss((F - PAN["saca"]) / float(PAN["frente"] - PAN["saca"]))); wm = 1.0
        elif F < PAN["llega"]: objm = Pf + UP * 0.015 * math.sin((F - PAN["frente"]) / 9.0); wm = 1.0       # lo sostiene en alto
        elif not llevado:                                                      # TIRA Y AFLOJA con la paloma, DE UN LADO HACIA EL OTRO
            k = F - PAN["llega"]; base = Pf.lerp(Pt, ss(k / 8.0)); amp = 0.08 + 0.08 * min(1.0, k / 40.0)
            objm = base + lado * amp * math.sin(2 * math.pi * k / TIRON) + FWD * 0.03 * math.sin(4 * math.pi * k / TIRON) + UP * 0.02 * math.sin(4 * math.pi * k / TIRON)
            wm = 1.0
        else:                                                                  # se lo arrebata: las manos se van tras el pan mientras cae
            k = F - PAN["gana"]; objm = Pt + FWD * (0.14 + 0.10 * ss(k / 5.0)); wm = 1.0 - ss(k / 10.0)
        polo = -UP + lado * 0.8 + (FWD * 0.4 if F < PAN["saca"] else -FWD * 0.2)
        eu, ee, Mu, Me = ik("Right", objm, polo, Mp, p["RightUpArm_alfred"], p["Rightelbow_alfred"], wm)
        p["RightUpArm_alfred"], p["Rightelbow_alfred"] = eu, ee; Mp["RightUpArm_alfred"], Mp["Rightelbow_alfred"] = Mu, Me
        Mmano = W() @ Me @ Matrix.Translation(MANO["Right"]) @ PAN_OFF
        # mano IZQUIERDA: en el forcejeo agarra el pan tambien (las dos manos para que no se lo quiten)
        wl = env(F, PAN["llega"] - 2, PAN["gana"], 8, 8)
        if wl > 0:
            objl = objm - lado * 0.13 + UP * 0.01
            eu, ee, Mu, Me2 = ik("Left", objl, -UP - lado * 0.8 - FWD * 0.2, Mp, p["LeftUpArm_alfred"], p["Leftelbow_alfred"], wl)
            p["LeftUpArm_alfred"], p["Leftelbow_alfred"] = eu, ee; Mp["LeftUpArm_alfred"], Mp["Leftelbow_alfred"] = Mu, Me2
            if not llevado and wl > 0.5:                                       # el pan entre las dos manos
                ml = W() @ Me2 @ MANO["Left"]; mr = W() @ Me @ MANO["Right"]
                Mmano = Matrix.Translation((ml + mr) / 2 - Mmano.translation) @ Mmano
        if not llevado: Mpan = Mmano; PAN_G = Mpan.copy()
        else:                                                                  # el pan va en el pico de la paloma, que escapa sobre el mar
            k = F - PAN["gana"]; D_ESC = (FWD * 0.70 + lado_der * -0.35 + UP * 0.75).normalized()
            dist = 0.19 * k - 0.19 * 6 * (1 - math.exp(-k / 6.0)) + 0.55 * ss(k / 4.0)   # tiron rapido al arrebatarlo y acelera hasta ~4.5 m/s
            Mpan = Matrix.Translation(D_ESC * dist + UP * 0.05 * math.sin(k / 3.0)) @ PAN_G
        orgullo = env(F, PAN["frente"] - 6, PAN["llega"], 10, 8)               # pecho afuera mientras lo luce
        lucha = env(F, PAN["llega"], PAN["gana"], 6, 4)                        # se inclina hacia la paloma al forcejear
        estira = env(F, PAN["gana"], PAN["gana"] + 6, 2, 16)                   # se va tras el pan
        resiste = env(F, PAN["gana"] - 10, PAN["gana"], 6, 2)                  # justo antes se echa atras resistiendo
        for b_, frac in (("Spine1_alfred", 0.45), ("Spine2_alfred", 0.55)):
            i_, s_ = INCL[b_]; e_ = list(p[b_]); e_[i_] += s_ * (-0.10 * orgullo + 0.06 * lucha - 0.12 * resiste + 0.07 * estira + (0.05 if llevado else 0.0)) * frac; p[b_] = Euler(e_)
        if F >= PAN["saca"] and F < PAN["gana"] + 10:
            mirar_a = Mpan.translation; w_mira = 0.95 * (1.0 - ss((F - PAN["gana"]) / 10.0))   # mira el pan; al caer, ya no
        elif F >= PAN["gana"] + 10: mirar_a = None
    KPAN.append(Mpan); VPAN.append(Mpan is not None and F >= PAN["saca"])
    # mirada
    if mirar_a is not None:
        en, ef, Mn, Mf = mirar(mirar_a, w_mira, Mp, p["Neck_alfred"], p["face_alfred"]); p["Neck_alfred"], p["face_alfred"] = en, ef; Mp["Neck_alfred"], Mp["face_alfred"] = Mn, Mf
    for n_, e_ in p.items(): K[n_].append(tuple(e_))
    # ---- flechas ----
    for n in FL:
        e = next(x for x in EV if x["n"] == n); vis = True
        if F < e["r0"] or (act is not e and F < e["l0"]): Mfl = pegada(n)
        elif act is e and F <= e["rel"]: Mfl = e["_Mfl"]
        else:
            v = vuelo.get(n)
            if v is None: Mfl = pegada(n)
            else:
                tv = (F - v["f"]) / 24.0; P0 = v["M"].translation
                Lp = P0 + FWD * e["dist"] + lado_der * e["lat"]; Lp.z = 7.85; Tf = 0.85
                vel = (Lp - P0) / Tf - Vector((0, 0, -9.8)) * 0.5 * Tf
                if tv <= Tf: pos = P0 + vel * tv + Vector((0, 0, -9.8)) * 0.5 * tv * tv; giro = tv * 2.3 * 2 * math.pi
                else: pos = Lp - UP * min(0.2, (tv - Tf) * 0.6); giro = Tf * 2.3 * 2 * math.pi; vis = tv < Tf + 0.3
                lat = (FWD.cross(UP)).normalized()
                Mfl = Matrix.Translation(pos) @ Quaternion(lat, -giro).to_matrix().to_4x4() @ Matrix.Translation(-P0) @ v["M"]
        KF[n].append(Mfl.copy()); VIS[n].append(vis)

# ---------------- 7) claves (directo a las curvas: rapido) ----------------
def accion(idb, nombre):
    ad = idb.animation_data_create(); quitar_accion(idb)
    a = bpy.data.actions.new(nombre); ad.action = a; return a


def curva(a, idb, ruta, i, valores, interp=1):
    fc = a.fcurve_ensure_for_datablock(idb, ruta, index=i); kp = fc.keyframe_points; kp.add(len(valores))
    co = []
    for k, v in enumerate(valores): co += [k + 1, float(v)]
    kp.foreach_set("co", co); kp.foreach_set("interpolation", [interp] * len(valores)); fc.update()


a = accion(ARM, "p11_alfred_saca_flechas")
for n_, L in K.items():
    for i in range(3): curva(a, ARM, 'pose.bones["%s"].rotation_euler' % n_, i, [e[i] for e in L])
for i in range(3): curva(a, ARM, 'pose.bones["Hips_alfred"].location', i, [h_[i] for h_ in KH])
a_r = accion(AR, "p11_alfred_raiz")                                         # la raiz se mueve solo al caer al mar
for i in range(3): curva(a_r, AR, "location", i, [r_[i] for r_ in KR])
_rots = [rot_raiz(r_) for r_ in KR]
for i in range(3): curva(a_r, AR, "rotation_euler", i, [e_[i] for e_ in _rots])
for n, L in KF.items():
    o = FL[n]["obj"]; a = accion(o, "p11_" + n); locs = []; rots = []; q_ant = None
    for M in L:
        l_, q, s_ = M.decompose()
        if q_ant is not None and q.dot(q_ant) < 0: q.negate()
        q_ant = q; locs.append(l_); rots.append(q)
    o.scale = L[0].to_scale()
    for i in range(3): curva(a, o, "location", i, [v[i] for v in locs])
    for i in range(4): curva(a, o, "rotation_quaternion", i, [q[i] for q in rots])
    curva(a, o, "hide_render", 0, [not v for v in VIS[n]], 0); curva(a, o, "hide_viewport", 0, [not v for v in VIS[n]], 0)
# el pan (item de MCprep): oculto hasta que lo saca de la espalda
pan = bpy.data.objects.get("pan_alfred")
if pan is None and hasattr(sc, "mcprep_props"):
    L_ = [i.name for i in sc.mcprep_props.item_list]
    if not L_: bpy.ops.mcprep.reload_items(); L_ = [i.name for i in sc.mcprep_props.item_list]
    antes = set(bpy.data.objects); sc.mcprep_props.item_list_index = L_.index("bread"); bpy.ops.mcprep.spawn_item()
    pan = [x for x in bpy.data.objects if x not in antes][0]; pan.name = "pan_alfred"; pan.parent = None
if pan is not None:
    lc = sum((v.co for v in pan.data.vertices), Vector()) / len(pan.data.vertices)
    if lc.length > 1e-4: pan.data.transform(Matrix.Translation(-lc))      # origen en el centro del pan
    quitar_accion(pan); pan.rotation_mode = 'QUATERNION'; a = accion(pan, "p11_pan_alfred")
    M_ok = [M for M in KPAN if M is not None]; M_ini = M_ok[0] if M_ok else Matrix()
    locs, rots, q_ant = [], [], None
    for M in KPAN:
        l_, q, _s = (M if M is not None else M_ini).decompose()
        if q_ant is not None and q.dot(q_ant) < 0: q.negate()
        q_ant = q; locs.append(l_); rots.append(q)
    pan.scale = (0.4, 0.4, 0.8)
    for i in range(3): curva(a, pan, "location", i, [v[i] for v in locs])
    for i in range(4): curva(a, pan, "rotation_quaternion", i, [q[i] for q in rots])
    VPAN = [v and (F_ + 1 < PAN["gana"] + 170) for F_, v in enumerate(VPAN)]                 # muy lejos ya no se ve
    curva(a, pan, "hide_render", 0, [not v for v in VPAN], 0); curva(a, pan, "hide_viewport", 0, [not v for v in VPAN], 0)
sc.frame_set(1)
print("PARTE 11: Alfred se saca %d flechas y las tira al mar: f1-%d (%s)" % (len(EV), FIN, ", ".join("%s f%d-%d" % (e["n"], e["r0"], e["fin"]) for e in EV)))
