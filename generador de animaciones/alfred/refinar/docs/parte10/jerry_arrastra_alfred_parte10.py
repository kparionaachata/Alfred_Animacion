# -*- coding: utf-8 -*-
"""Parte 10 (base_parte_10.blend, escena viva): JERRY SACA A ALFRED DEL TUNEL ARRASTRANDOLO con los dientes desde la cabeza.
- Limpia la escena: quita las animaciones de la parte 7 (personajes, creeper, pollo, camara, ojos) y sus tiras de sonido; oculta el creeper y el pollo.
- Alfred: INCONSCIENTE, boca arriba (pose de la referencia Mixamo `acciones/animacion_alfred_boca_arriba.py`), la cabeza hacia la salida (+x), ojos cerrados,
  con las 4 FLECHAS de la parte 9 clavadas (frente, mano derecha, mano izquierda, entrepierna: objetos de `base_parte_9.blend` emparentados a su hueso con el
  mismo desplazamiento que en el ultimo frame de la parte 9, `flechas_offsets_parte9.json`).
- Jerry: a la altura de la cabeza de Alfred dentro del tunel de Alfred (x -114), mirando hacia el; baja la cabeza y lo MUERDE (f1-20), y lo saca a TIRONES
  caminando hacia atras (ciclo de caminar del estudio de Jerry al reves): en cada tiron retrocede `PASO` m y Alfred lo sigue con 2 f de retraso, con la cabeza
  y los hombros levantados por el tiron y los brazos y piernas sueltos que se sacuden. Afuera (cabeza de Alfred en x -104) lo suelta, levanta la cabeza y jadea.
- El suelo se lee con rayos (tunel y ladera); el cuerpo de Alfred se apoya en el suelo frame a frame. Ejecutar con `bpy.app.timers.register`."""
import bpy, math, json, ast, random
from mathutils import Vector, Matrix, Euler

sc = bpy.context.scene; vl = bpy.context.view_layer
D9 = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\base_parte_9.blend"
DOC = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs"
ARM = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'Hips_alfred' in o.pose.bones); AR = ARM.parent
JA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'scull_1' in o.pose.bones and 'jaw_bot' in o.pose.bones); JR = JA.parent
Y = -69.5; X_CAB0 = -110.1; X_CAB1 = -104.0; PASO = 0.35; TIRON = 14; T_MUERDE = 10; T_SUELTA = 30   # empieza donde estaban en el f160 de la version anterior (cabeza de Alfred en x -110.1), ya mordiendo
ss = lambda t: 0.0 if t <= 0 else (1.0 if t >= 1 else t * t * (3 - 2 * t))

# ---------------- 1) limpiar la parte 7 ----------------
for k_ in ("p10_voz_jerry_deltas", "p10_organicos"):
    if k_ in sc: del sc[k_]                         # las claves se rehacen: la voz (voz_jerry_boca_ocupada_parte10.py) se vuelve a sumar despues
YA_LIMPIA = "p10_tiempos" in sc                    # la parte 7 ya se limpio en una corrida anterior: al REPETIR solo se quita lo que anima esta cadena
if not YA_LIMPIA:                                   # primera vez: fuera TODO lo de la parte 7 (personajes, creeper, pollo, camara, ojos) y sus sonidos
    ids = [o for o in bpy.data.objects if o.type != 'CAMERA'] + list(bpy.data.shape_keys) + [m.node_tree for m in bpy.data.materials if m.node_tree] + list(bpy.data.materials)   # la CAMARA nunca: la maneja el usuario
else:                                               # al repetir: la camara, los focos, el oceano, la musica... que se animen a mano DESPUES se conservan
    propios = {AR, ARM, JR, JA} | set(AR.children_recursive) | set(JR.children_recursive)
    propios |= {o for o in bpy.data.objects if o.name.startswith(("flecha_", "sombrero_jerry")) or o.name.endswith(("_alfred", "_jerry"))}
    mats = {s.material for o in propios for s in o.material_slots if s.material}
    ids = list(propios) + [k for k in bpy.data.shape_keys if k.user in propios or getattr(k.user, "name", "").endswith(("_alfred", "_jerry"))] + list(mats) + [m.node_tree for m in mats if m.node_tree]
for idb in ids:
    ad = getattr(idb, "animation_data", None)
    if ad:
        for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
        ad.action = None
for a in [a for a in bpy.data.actions if a.users == 0 and not a.use_fake_user]: bpy.data.actions.remove(a)
if sc.sequence_editor:
    for s in [s for s in sc.sequence_editor.strips_all if not YA_LIMPIA or s.name.startswith(("SND_p10_", "VozJerry_", "VozAlfred_"))]:
        try: (s.parent_meta().strips if s.parent_meta() else sc.sequence_editor.strips).remove(s)
        except Exception: pass
for raiz in ("creeper_1", "chicken_1"):
    r = bpy.data.objects.get(raiz)
    if r:
        for o in [r] + list(r.children_recursive): o.hide_viewport = True; o.hide_render = True
for n in ("stone_axe", "stone_shovel"):
    o = bpy.data.objects.get(n)
    if o:
        for c in o.constraints: c.influence = 1.0 if c.name == "Espalda" else 0.0
for o in [ARM] + [m for m in AR.children_recursive if m.type == 'MESH'] + [JA] + [m for m in JR.children_recursive if m.type == 'MESH']:
    o.hide_viewport = False; o.hide_render = False
for A in (ARM, JA):
    for b in A.pose.bones: b.rotation_mode = 'XYZ'; b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0); b.scale = (1, 1, 1)

# ---------------- 2) suelo (rayos hacia abajo dentro del tunel y en la ladera) ----------------
dg = bpy.context.evaluated_depsgraph_get()
def es_ajeno(o):
    o = o.original; return o.type != 'MESH' or o.name.startswith(("flecha", "sombrero", "miga", "Short_Grass", "Tall_Grass", "Fern", "Poppy", "Dandelion", "Allium", "Azure")) or (o.parent is not None and o.parent.type in ('ARMATURE', 'EMPTY') and o.parent.name in ("armature", "alfred", "a.002", "jerry")) or o.name.endswith(("_alfred", "_jerry"))
cache = {}
def piso(x):
    k = round(x * 4) / 4
    if k in cache: return cache[k]
    zest = 9.0 + min(0.0, (k + 106.5)) * (3.0 / 25.0); p = Vector((k + 0.0031, Y, zest + 1.2)); z = None   # +3 mm: el rayo nunca cae justo en la arista entre bloques (ahi a veces atraviesa el suelo)
    for _ in range(12):
        ok, l, n, i, o, m = sc.ray_cast(dg, p, Vector((0, 0, -1)), distance=6)
        if not ok: break
        if es_ajeno(o): p = l - Vector((0, 0, 0.01)); continue
        z = l.z; break
    cache[k] = z if z is not None else zest; return cache[k]
def piso_suave(x): return sum(piso(x + d) for d in (-0.3, 0.0, 0.3)) / 3.0                  # los escalones del tunel se pasan suave

# ---------------- 3) Alfred: pose tumbado e inconsciente ----------------
src = open(DOC + r"\acciones\animacion_alfred_boca_arriba.py", encoding="utf-8").read()
KBA = next(ast.literal_eval(n.value) for n in ast.parse(src).body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "KEYFRAME_DATA")
LY = {b.name: Euler((0, 0, 0)) for b in ARM.pose.bones}
for n, fr in KBA.items():
    if n in LY: LY[n] = Euler(fr[1])
def aplicar(A, R, p, r):
    R.location = r[:3]; R.rotation_euler = r[3:]
    for n, e in p.items(): A.pose.bones[n].rotation_euler = e
    vl.update()
mejor = None
for k in range(4):                                                                          # rumbo con la CABEZA hacia la salida (+x)
    yaw = k * math.pi / 2; aplicar(ARM, AR, LY, (X_CAB0, Y, 9, 0, 0, yaw))
    d = (ARM.matrix_world @ ARM.pose.bones["face_alfred"].tail).x - (ARM.matrix_world @ ARM.pose.bones["Hips_alfred"].head).x
    if mejor is None or d > mejor[0]: mejor = (d, yaw)
YAW_A = mejor[1]
MESH_A = [o for o in AR.children_recursive if o.type == 'MESH' and o.name.startswith("Mesh_")]
# ---- BRAZOS en el suelo: estirados junto al cuerpo (codos SIN doblar), apuntando hacia los pies y un poco abiertos ----
def brazos_al_suelo(p):
    q = {k: Euler(v) for k, v in p.items()}; r0 = (X_CAB0, Y, 9.0, 0.0, 0.0, YAW_A); aplicar(ARM, AR, q, r0)
    W = ARM.matrix_world; hp = W @ ARM.pose.bones["Hips_alfred"].head; cab = W @ ARM.pose.bones["Neck_alfred"].head
    pies = (hp - cab); pies.z = 0; pies.normalize()
    for ua, el in (("RightUpArm_alfred", "Rightelbow_alfred"), ("LeftUpArm_alfred", "Leftelbow_alfred")):
        q[el] = Euler((0.0, 0.0, 0.0)); aplicar(ARM, AR, q, r0)
        pbu = ARM.pose.bones[ua]; sh = W @ pbu.head; lat = (sh - cab); lat = lat - pies * lat.dot(pies); lat.z = 0
        lat = lat.normalized() if lat.length > 1e-4 else Vector((0, 0, 0))
        tgt = pies + lat * 0.22 + Vector((0, 0, -0.10))                                     # hacia los pies, algo abierto y pegado al suelo
        for _ in range(3):
            v = (W @ ARM.pose.bones[el].tail) - sh; qd = v.rotation_difference(tgt); Mw = W @ pbu.matrix
            pbu.matrix = W.inverted() @ (Matrix.Translation(sh) @ qd.to_matrix().to_4x4() @ Matrix.Translation(-sh)) @ Mw; vl.update()
        q[ua] = Euler(pbu.rotation_euler)
    return q
LY = brazos_al_suelo(LY)
def raiz_alfred(p, x_cabeza):
    r = (x_cabeza, Y, 0.0, 0.0, 0.0, YAW_A); aplicar(ARM, AR, p, r); c = ARM.matrix_world @ ARM.pose.bones["face_alfred"].tail
    r = (r[0] + x_cabeza - c.x, r[1] + Y + 0.07 - (ARM.matrix_world @ ARM.pose.bones["Hips_alfred"].head).y, 0.0, 0.0, 0.0, YAW_A)   # +0.07: el cuerpo (con los brazos) queda centrado en el tunel de 1 m; aplicar(ARM, AR, p, r)
    dgx = bpy.context.evaluated_depsgraph_get(); dz = 1e9
    for o in MESH_A:
        e = o.evaluated_get(dgx); M = e.matrix_world; vs = e.data.vertices
        for i in range(0, len(vs), 7): w = M @ vs[i].co; dz = min(dz, w.z - piso(w.x))
    return (r[0], r[1], 0.005 - dz, 0.0, 0.0, YAW_A)

# ---------------- 4) Jerry: rumbo, mordida, desplazamiento de la boca ----------------
import sys
p_ = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\jerry\refinar"
if p_ not in sys.path: sys.path.insert(0, p_)
import jerry_animation_studio.tunel_jerry as tj
CIC = tj.Ciclo(25)
def pose_jerry(fase, muerde, tiron, jadeo=0.0):
    k = {n: Euler(v) for n, v in CIC.pose(fase).items() if n in JA.pose.bones}
    e = list(k.get("spine_2", Euler())); e[0] += 0.55 * muerde - 0.18 * tiron; k["spine_2"] = Euler(e)      # cabeza ABAJO a la cabeza de Alfred; el tiron la echa atras
    e = list(k.get("spine_1", Euler())); e[0] += 0.12 * muerde - 0.06 * tiron; k["spine_1"] = Euler(e)
    k["jaw_bot"] = Euler((-math.radians(22) * jadeo, 0, 0))
    return k
mejor = None
for kk in range(4):                                                                         # Jerry MIRA a Alfred (hacia -x)
    yaw = kk * math.pi / 2; aplicar(JA, JR, pose_jerry(1, 1, 0), (-110, Y, 9, 0, 0, yaw))
    d = (JA.matrix_world @ JA.pose.bones["jaw_top"].tail).x - (JA.matrix_world @ JA.pose.bones["scull"].head).x
    if mejor is None or d < mejor[0]: mejor = (d, yaw)
YAW_J = mejor[1]
def raiz_jerry(p, x_boca):
    r = (x_boca, Y, 0.0, 0.0, 0.0, YAW_J); aplicar(JA, JR, p, r); b = JA.matrix_world @ JA.pose.bones["jaw_top"].tail
    x = r[0] + x_boca - b.x; return (x, Y, piso_suave(x - 0.0), 0.0, 0.0, YAW_J)

# ---------------- 5) linea de tiempo ----------------
N = 16; T_PARA = T_MUERDE + N * TIRON                                                     # deja de jalar en el f234 (10 + 16 x 14)
FIN = T_MUERDE + N * TIRON + T_SUELTA + 30
rng = random.Random(8); TA = {}; TJ = {}
def cab_alfred(f):
    """x de la cabeza de Alfred en el frame f (sigue al tiron con 2 f de retraso)"""
    k = f - T_MUERDE - 2
    if k <= 0: return X_CAB0
    i, r = divmod(k, TIRON); i = min(i, N)
    if i >= N: return X_CAB0 + N * PASO
    return X_CAB0 + (i + ss(min(1.0, r / 9.0))) * PASO
def boca_jerry(f):
    k = f - T_MUERDE
    if k <= 0: return X_CAB0 + 0.06
    i, r = divmod(k, TIRON)
    if i >= N: return X_CAB0 + N * PASO + 0.06
    return X_CAB0 + (i + ss(min(1.0, r / 9.0))) * PASO + 0.06
fase = 1.0; prev_x = boca_jerry(1); sac = {}
for f in range(1, FIN + 1):
    xb = boca_jerry(f); fase -= (xb - prev_x) / PASO * (CIC.CL / 2.0); prev_x = xb            # camina HACIA ATRAS: el ciclo va al reves y avanza con el desplazamiento
    k = f - T_MUERDE; tiron = 0.0
    if 0 <= k < N * TIRON: r = k % TIRON; tiron = math.sin(min(1.0, r / 8.0) * math.pi) if r < 8 else 0.0
    muerde = 1.0 if f < T_MUERDE + N * TIRON + 4 else 1.0 - ss((f - (T_MUERDE + N * TIRON + 4)) / 10.0)          # ya lo tiene agarrado desde el f1
    jadeo = 0.0
    if f <= T_MUERDE + N * TIRON + 4: jadeo = 0.75 + 0.08 * tiron                              # MANDIBULA ABIERTA mordiendo la ropa (la capucha) de Alfred
    elif f > T_MUERDE + N * TIRON + 4: jadeo = 0.5 + 0.35 * math.sin((f - T_MUERDE - N * TIRON) * 0.9)   # lo suelta y jadea
    # Alfred: tumbado, la cabeza/hombros se levantan con el tiron, brazos y piernas sueltos
    pa = {n: Euler(e) for n, e in LY.items()}
    ka = k - 2; t_a = math.sin(min(1.0, (ka % TIRON) / 8.0) * math.pi) if 0 <= ka < N * TIRON and (ka % TIRON) < 8 else 0.0
    rebote = math.exp(-((ka % TIRON) - 8) / 3.0) * math.sin(((ka % TIRON) - 8) * 1.6) if 0 <= ka < N * TIRON and (ka % TIRON) >= 8 else 0.0
    for n, ax, a in (("Neck_alfred", 0, -0.10), ("Spine2_alfred", 0, -0.05), ("Spine1_alfred", 0, -0.03)):
        e = list(pa[n]); e[ax] += a * t_a; pa[n] = Euler(e)
    for n, a in (("RightUpArm_alfred", 0.10), ("LeftUpArm_alfred", 0.10), ("Rightelbow_alfred", 0.08), ("Leftelbow_alfred", 0.08), ("RightUpLeg_alfred", 0.05), ("LeftUpLeg_alfred", 0.05), ("Rightknee_alfred", 0.07), ("Leftknee_alfred", 0.07)):
        e = list(pa[n]); e[0] += a * (rebote + 0.3 * t_a) * (1 if "Right" in n else 0.8); pa[n] = Euler(e)
    TA[f] = (pa, raiz_alfred(pa, cab_alfred(f)))
    # Jerry: el punto ENTRE SUS MANDIBULAS va a la capucha de Alfred (vertice mas adelantado de la malla de la cabeza, a media altura), un poco hacia dentro
    aplicar(ARM, AR, *TA[f]); dgx = bpy.context.evaluated_depsgraph_get(); e0 = bpy.data.objects["Mesh_0_alfred"].evaluated_get(dgx)
    vh = [e0.matrix_world @ v.co for v in e0.data.vertices]; xm = max(v.x for v in vh); fr_ = [v for v in vh if v.x > xm - 0.12]
    G = Vector((xm - 0.05, sum(v.y for v in fr_) / len(fr_), sum(v.z for v in fr_) / len(fr_)))
    mejor = None
    for md in (0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4):                                           # cuanto baja la cabeza para que la boca quede a la altura de la capucha
        if f > T_MUERDE + N * TIRON + 4: md = muerde
        pj = pose_jerry(fase, md, tiron, jadeo); aplicar(JA, JR, pj, (xb, Y, piso_suave(xb), 0, 0, YAW_J))
        M = (JA.matrix_world @ JA.pose.bones["jaw_top"].tail + JA.matrix_world @ JA.pose.bones["jaw_bot"].tail) / 2
        err = abs(M.z - G.z)
        if mejor is None or err < mejor[0]: mejor = (err, pj, M)
        if f > T_MUERDE + N * TIRON + 4: break
    pj, M = mejor[1], mejor[2]; xj = xb + (G.x - M.x) if f <= T_MUERDE + N * TIRON + 4 else TJ[f - 1][1][0]
    TJ[f] = (pj, (xj, Y, piso_suave(xj), 0.0, 0.0, YAW_J))


# ---------------- 5b) tras soltarlo: CUATRO CACHETADAS (derecha, izquierda, derecha, izquierda) en LE-VAN-TA-TE, Alfred reacciona, mueve la cabeza y se LEVANTA ----------------
VOZ_LEV = T_PARA + 12                                                                        # voz de Jerry "Ya, ahora LE-VAN-TA-TE" (clip frame 1 en este frame)
SILABAS = [39, 55, 71, 86]                                                                  # inicio de LE, VAN, TA, TE en el clip (SPEECH_CURVE de animacion_jerry (1).py)
LADOS = ["R", "L", "R", "L"]; CONTACTO = {"R": 3, "L": 3}                                   # pata de cada golpe y frames del arranque al contacto
CACH = [VOZ_LEV + k - 1 - CONTACTO[l] for k, l in zip(SILABAS, LADOS)]                      # cada golpe TOCA la cara en su silaba
T_SUELTA_FIN = T_PARA + 14; T_MUEVE = CACH[-1] + 20; T_LEV = T_MUEVE + 38
sc["p10_tiempos"] = {"T_PARA": T_PARA, "VOZ_LEV": VOZ_LEV, "CACH": CACH, "CONTACTOS": [c + CONTACTO[l] for c, l in zip(CACH, LADOS)], "T_MUEVE": T_MUEVE, "T_LEV": T_LEV}
src_lev = open(DOC + r"\acciones\animacion_alfred_levantarse_boca_arriba.py", encoding="utf-8").read()
KLEV = next(ast.literal_eval(n.value) for n in ast.parse(src_lev).body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "KEYFRAME_DATA")
NLEV = max(max(v) for v in KLEV.values()); FIN = T_LEV + NLEV + 24
def mez(p, q, t):
    out = {}
    for n in p:
        a = p[n].to_quaternion(); c = q[n].to_quaternion()
        if a.dot(c) < 0: c.negate()
        out[n] = a.slerp(c, t).to_euler('XYZ', p[n])
    return out
ela = lambda t: math.exp(-t / 5.0) * math.cos(t * 0.9)                                     # sacudida amortiguada
def raiz_apoyo(p, x, y):
    """raiz con el punto mas bajo de Alfred apoyado en el suelo (sirve tumbado, sentado y de pie)"""
    r = (x, y, 0.0, 0.0, 0.0, YAW_A); aplicar(ARM, AR, p, r); dgx = bpy.context.evaluated_depsgraph_get(); dz = 1e9
    for o in MESH_A:
        e = o.evaluated_get(dgx); M = e.matrix_world; vs = e.data.vertices
        for i in range(0, len(vs), 7): w = M @ vs[i].co; dz = min(dz, w.z - piso(w.x))
    return (x, y, 0.005 - dz, 0.0, 0.0, YAW_A)
# --- Jerry NO se mueve de su sitio (su empty queda donde dejo de jalar) y le da dos cachetadas en la CARA: la 1.a con la pata DERECHA hacia la derecha (+y),
#     la 2.a con la pata IZQUIERDA hacia la izquierda (-y); se inclina hacia delante para alcanzar sin tocar a Alfred con el cuerpo ---
import numpy as np
TJLOC = {}
pj0, rj0 = TJ[T_PARA]; pa0, ra0 = TA[T_PARA]; aplicar(ARM, AR, pa0, ra0)
dgx = bpy.context.evaluated_depsgraph_get()
AV = np.array([tuple(o.evaluated_get(dgx).matrix_world @ v.co) for o in MESH_A for v in o.evaluated_get(dgx).data.vertices][::3])
e0 = bpy.data.objects["Mesh_0_alfred"].evaluated_get(dgx); vh = [e0.matrix_world @ v.co for v in e0.data.vertices]
zt = max(v.z for v in vh); xm_ = max(v.x for v in vh); sup = [v for v in vh if v.z > zt - 0.05 and v.x > xm_ - 0.22]      # la parte de la cara MAS CERCANA a Jerry (lado de la coronilla)
CARA = Vector((sum(v.x for v in sup) / len(sup), sum(v.y for v in sup) / len(sup), zt + 0.02))          # la cara (arriba de la cabeza: Alfred esta boca arriba)
MESH_J = [o for o in JR.children_recursive if o.type == 'MESH' and not o.hide_viewport]
def verts_jerry(excluir):
    dg_ = bpy.context.evaluated_depsgraph_get(); W = JA.matrix_world; segs = [(W @ JA.pose.bones[b].head, W @ JA.pose.bones[b].tail) for b in excluir if b in JA.pose.bones]
    out = []
    for o in MESH_J:
        e = o.evaluated_get(dg_); M = e.matrix_world; vs = e.data.vertices
        for k in range(0, len(vs), 2):
            w = M @ vs[k].co; cerca = False
            for a_, b_ in segs:
                ab = b_ - a_; t = max(0.0, min(1.0, (w - a_).dot(ab) / max(1e-9, ab.dot(ab))))
                if (w - (a_ + ab * t)).length < 0.13: cerca = True; break
            if not cerca: out.append(tuple(w))
    return np.array(out)
PATAS = {s_: tuple("front_%s.%s" % (b, s_) for b in ("shoulder", "thigh", "shin", "foot", "toe")) for s_ in ("R", "L")}
def holgura(av=AV, excluir=PATAS["R"] + PATAS["L"]):
    jv = verts_jerry(excluir)
    if len(jv) == 0 or len(av) == 0: return 9.0
    lo = av.min(0) - 0.3; hi = av.max(0) + 0.3; jv = jv[np.all((jv > lo) & (jv < hi), axis=1)]
    if len(jv) == 0: return 9.0
    return float(np.sqrt(((jv[:, None, :] - av[None, :, :]) ** 2).sum(2)).min())
def con_pata(p, lado, sx, sz, sh, incl=0.0):
    q = {k: Euler(v) for k, v in p.items()}
    for n, d in (("front_shoulder." + lado, (sx, 0.0, sz)), ("front_shin." + lado, (sh, 0.0, 0.0))):
        e = list(q.get(n, Euler())); e[0] += d[0]; e[2] += d[2]; q[n] = Euler(e)
    for n, a in (("spine_1", 0.5), ("spine_4", 0.5)):                                      # se INCLINA hacia delante (el pecho baja hacia Alfred)
        if n in q or n in JA.pose.bones: e = list(q.get(n, Euler())); e[0] += incl * a; q[n] = Euler(e)
    return q
ATRAS = 0.0                                                                                  # SIN levantar la cabeza: el cuerpo se echa ATRAS con el hueso raiz `spine_6` (el empty no se mueve)
B6 = JA.pose.bones["spine_6"]
def loc_atras(d):
    """ubicacion local de `spine_6` que lleva el cuerpo d metros hacia +x (lejos de Alfred) en el mundo"""
    R = (JA.matrix_world @ B6.bone.matrix_local).to_3x3().normalized(); return R.inverted() @ Vector((d, 0.0, 0.0))
RETRO = 0.0
for RETRO in [0.04 * k for k in range(16)]:
    B6.location = loc_atras(RETRO); aplicar(JA, JR, pose_jerry(1.0, 0.0, 0.0, 0.0), rj0)
    if holgura() >= 0.05: break
base_j = pose_jerry(1.0, 0.0, 0.0, 0.0); RJ = rj0
print("CUERPO ATRAS: %.2f m" % RETRO)
GOLPES = {}
for lado, hacia in (("R", 1.0), ("L", -1.0)):
    tgt = CARA + Vector((0.0, -hacia * 0.10, 0.0))                                         # toca la cara del lado contrario y la empuja hacia `hacia`
    mejor = None
    for incl in (0.0, 0.15, 0.3):
        for sx in range(-20, 131, 10):
            for sz in range(-80, 81, 10):
                for sh in (0, 20, 40, 60):
                    aplicar(JA, JR, con_pata(base_j, lado, math.radians(sx), math.radians(sz), math.radians(sh), incl), RJ)
                    d_ = ((JA.matrix_world @ JA.pose.bones["front_foot." + lado].tail) - tgt).length
                    if mejor is None or d_ < mejor[0]: mejor = (d_, incl, sx, sz, sh)
    G = (math.radians(mejor[2]), math.radians(mejor[3]), math.radians(mejor[4]))
    def punta_y(dz):
        aplicar(JA, JR, con_pata(base_j, lado, G[0], G[1] + dz, G[2], mejor[1]), RJ); return (JA.matrix_world @ JA.pose.bones["front_foot." + lado].tail).y
    sg = 1.0 if punta_y(0.5) > punta_y(-0.5) else -1.0                                      # signo de Z del hombro que mueve la pata hacia +y
    ARMA = (G[0] + math.radians(15), G[1] - sg * hacia * math.radians(45), G[2])           # armada del lado CONTRARIO al golpe
    SIG = (G[0], G[1] + sg * hacia * math.radians(25), G[2])                               # barre la cara hacia `hacia`
    aplicar(JA, JR, con_pata(base_j, lado, G[0], G[1], G[2], mejor[1]), RJ); hol = holgura(excluir=PATAS[lado])
    GOLPES[lado] = (G, ARMA, SIG, mejor[1])
    print("CACHETADA %s: pata a %.2f m de la cara (incl %.2f, hombro X %d Z %d, espinilla %d); holgura del resto del cuerpo %.2f" % ((lado,) + tuple(mejor) + (hol,)))
def cab_y(dz):
    q = {k: Euler(v) for k, v in pa0.items()}; e = list(q["Neck_alfred"]); e[2] += dz; q["Neck_alfred"] = Euler(e); aplicar(ARM, AR, q, ra0)
    return (ARM.matrix_world @ ARM.pose.bones["face_alfred"].tail).y
SGA = 1.0 if cab_y(0.3) > cab_y(-0.3) else -1.0                                             # signo de Z del cuello que gira la cara hacia +y
DIR_CACH = [1.0 if l == "R" else -1.0 for l in LADOS]                                    # derecha -> la cara a +y, izquierda -> a -y
def pesos_pata(f):
    """golpes activos en el frame f (las dos patas pueden moverse a la vez si los golpes estan seguidos): [(lado, fase, peso)]"""
    out = []
    for c, lado in zip(CACH, LADOS):
        t = f - c
        if -7 <= t < -3: out.append((lado, "alza", ss((t + 7) / 4.0)))
        elif -3 <= t < 0: out.append((lado, "golpe", ((t + 3) / 3.0) ** 2))
        elif 0 <= t < 3: out.append((lado, "sigue", ss(t / 3.0)))
        elif 3 <= t < 9: out.append((lado, "vuelve", 1.0 - ss((t - 3) / 6.0)))
    return out
for f in range(T_PARA + 1, FIN + 1):
    # ---- Jerry (quieto en su sitio) ----
    m = 1.0 - ss((f - T_PARA) / 10.0)
    jad = 0.75 * m                                                                       # suelta la capucha y CIERRA la boca (no habla ni jadea)
    pj = pose_jerry(1.0, 0.55 * m, 0.0, jad); TJLOC[f] = tuple(loc_atras(RETRO * ss((f - T_PARA - 2) / 10.0)))   # suelta y se echa ATRAS con el cuerpo (cabeza normal)
    for lado, fase_, w in pesos_pata(f):
        G, ARMA, SIG, incl = GOLPES[lado]
        if fase_ == "alza": v = tuple(ARMA[i] * w for i in range(3)); ic = incl * w
        elif fase_ == "golpe": v = tuple(ARMA[i] + (G[i] - ARMA[i]) * w for i in range(3)); ic = incl
        elif fase_ == "sigue": v = tuple(G[i] + (SIG[i] - G[i]) * w for i in range(3)); ic = incl
        else: v = tuple(SIG[i] * w for i in range(3)); ic = incl * w
        pj = con_pata(pj, lado, v[0], v[1], v[2], ic)
    xx, yy = rj0[0], rj0[1]
    TJ[f] = (pj, (xx, yy, piso_suave(xx), 0.0, 0.0, YAW_J))
    # ---- Alfred ----
    if f < T_LEV:
        pa = {n: Euler(e) for n, e in LY.items()}; nz = 0.0; nx = 0.0
        for i_, c in enumerate(CACH):
            t = f - c
            t0_ = CONTACTO[LADOS[i_]]                                                          # la cara se va en el CONTACTO de cada pata
            if t >= t0_: nz += SGA * DIR_CACH[i_] * 0.50 * ela(t - t0_)                              # con el contacto la CARA se va hacia donde la empuja la pata (1.a +y, 2.a -y)
        if f >= T_MUEVE:                                                                    # vuelve en si: mueve la cabeza a los lados y la levanta un poco
            u = (f - T_MUEVE) / float(T_LEV - T_MUEVE); nz += 0.30 * math.sin((f - T_MUEVE) * 0.22) * math.sin(min(1.0, u) * math.pi); nx -= 0.12 * ss(u * 1.5)
        for n, k_ in (("Neck_alfred", 1.0), ("face_alfred", 0.5)):
            e = list(pa[n]); e[2] += nz * k_; e[0] += nx * k_; pa[n] = Euler(e)
        TA[f] = (pa, raiz_apoyo(pa, ra0[0], ra0[1]))
    else:                                                                                   # SE LEVANTA (referencia Mixamo `animacion_alfred_levantarse_boca_arriba.py`)
        k = min(NLEV, f - T_LEV + 1); pr = {n: Euler(e) for n, e in LY.items()}
        for n, fr in KLEV.items():
            if n in pr and k in fr: pr[n] = Euler(fr[k])
        prev_p = TA[T_LEV - 1][0]; pa = mez(prev_p, pr, ss(k / 8.0)) if k < 8 else pr
        TA[f] = (pa, raiz_apoyo(pa, ra0[0], ra0[1]))
OJOS = {T_MUEVE: 0.92, T_MUEVE + 10: 0.6, T_MUEVE + 14: 0.85, T_MUEVE + 24: 0.4, T_LEV: 0.35, T_LEV + 40: 0.1, FIN: 0.0}   # abre los ojos poco a poco (aturdido)


# ---------------- 5c) NO se quiere levantar: DUERME DE COSTADO; se MEDIO LEVANTA (poses/sentado.json); una FLECHA desde el tunel le da en el PECHO y cae boca arriba;
#                  Jerry lo ARRASTRA a la IZQUIERDA (fuera de la entrada del tunel), lo deja y se quita el SOMBRERO para pegarle con el ----------------
T0 = CACH[-1] + 14
T_ROLL0, T_ROLL1 = T0 + 6, T0 + 24                                                          # se gira de costado
T_SIENTA0 = CACH[-1] + CONTACTO[LADOS[-1]] + 30; T_SENTADO = T_SIENTA0 + 60                     # 30 f en el suelo tras la ultima cachetada; se levanta como recien despertado (60 f)
T_FLECHA = T_SENTADO + 8; VUELO_F = 10                                                      # la flecha le da en el pecho
T_CAE1 = T_FLECHA + 8                                                                       # cae otra vez boca arriba
T_MUERDE2 = T_FLECHA + 22; T_ARR0 = T_MUERDE2 + 12; N2 = 8; PASO2 = 0.33; T_ARR1 = T_ARR0 + N2 * TIRON
T_SUELTA2 = T_ARR1 + 10; T_SOMB0 = T_SUELTA2 + 6; T_SOMB_AG = T_SOMB0 + 10; T_SOMB1 = T_SOMB_AG + 8
GOLPES_S = [T_SOMB1 + 10 + 14 * k for k in range(3)]                                         # 3 golpes con el sombrero
T_PONE = GOLPES_S[-1] + 22                                                                 # se vuelve a PONER el sombrero
T_REAC = GOLPES_S[-1] + 8; T_LEV2 = T_REAC + 20                                            # tras el sombrero REACCIONA y se LEVANTA hasta quedar de pie
FIN = T_LEV2 + NLEV + 30
T_MUEVE, T_LEV = T_SIENTA0, T_SENTADO                                                       # ojos asimetricos mientras se levanta
sc["p10_tiempos"] = dict(sc["p10_tiempos"], T_MUEVE=T_MUEVE, T_LEV=T_LEV, T_ROLL0=T_ROLL0, T_SIENTA0=T_SIENTA0, T_SENTADO=T_SENTADO, T_FLECHA=T_FLECHA, T_CAE1=T_CAE1,
                         T_MUERDE2=T_MUERDE2, T_ARR0=T_ARR0, T_ARR1=T_ARR1, N2=N2, T_SOMB_AG=T_SOMB_AG, GOLPES_S=GOLPES_S, T_REAC=T_REAC, T_LEV2=T_LEV2, T_PONE=T_PONE, FIN=FIN)
from mathutils import Quaternion
def con(p, **cambios):
    q = {k: Euler(v) for k, v in p.items()}
    for n, (i, dv) in cambios.items(): e = list(q[n]); e[i] += dv; q[n] = Euler(e)
    return q
def piso_xy(x, y):
    k = (round(x * 4) / 4, round(y * 4) / 4)
    if k in cache: return cache[k]
    p = Vector((k[0] + 0.0031, k[1] + 0.0027, 11.0)); z = None                                    # fuera de la arista entre bloques (ahi el rayo a veces atraviesa el suelo)
    for _ in range(14):
        ok, l, n, i, o, m = sc.ray_cast(dg, p, Vector((0, 0, -1)), distance=8)
        if not ok: break
        if es_ajeno(o): p = l - Vector((0, 0, 0.01)); continue
        z = l.z; break
    cache[k] = z if z is not None else piso(k[0]); return cache[k]
def rot_alfred(yaw, roll=0.0):
    q = Euler((0, 0, yaw)).to_quaternion(); qr = Quaternion(Vector((math.cos(yaw - YAW_A), math.sin(yaw - YAW_A), 0)), roll)   # roll alrededor del eje LARGO del cuerpo (la cabeza va hacia +x con YAW_A)
    return (qr @ q).to_euler('XYZ')
def apoyar(p, x, y, e):
    """raiz de Alfred con el punto mas bajo en el suelo (rayos en x, y) para la rotacion e"""
    r = (x, y, 0.0, e.x, e.y, e.z); aplicar(ARM, AR, p, r); dgx = bpy.context.evaluated_depsgraph_get(); dz = 1e9
    for o in MESH_A:
        ev = o.evaluated_get(dgx); M = ev.matrix_world; vs = ev.data.vertices
        for i in range(0, len(vs), 9): w = M @ vs[i].co; dz = min(dz, w.z - piso_xy(w.x, w.y))
    return (x, y, 0.005 - dz, e.x, e.y, e.z)
# poses de Alfred
def pose_json(ruta):
    """rotaciones (rad) de los huesos de una pose guardada del estudio (`poses/*.json`) sobre LY"""
    P_ = json.load(open(ruta, encoding="utf-8"))["poses"][0]; out = {n: Euler(e) for n, e in LY.items()}
    for n, b in P_["bones"].items():
        if n in out: r_ = b["local_space"]["rotation_euler_rad"]; out[n] = Euler((r_["x"], r_["y"], r_["z"]))
    return out
COSTADO = pose_json(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\poses\durmiendo de costado.json")   # pose del usuario (raiz con roll 80)
SENT = json.load(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\poses\sentado.json", encoding="utf-8"))["poses"][0]
SENTADO = {n: Euler(e) for n, e in LY.items()}
for n, b in SENT["bones"].items():
    if n in SENTADO: r_ = b["local_space"]["rotation_euler_rad"]; SENTADO[n] = Euler((r_["x"], r_["y"], r_["z"]))
ROLL = math.radians(80.0)
APOYO = mez(LY, SENTADO, 0.45); APOYO = con(APOYO, Neck_alfred=(0, 0.25), face_alfred=(0, 0.1))           # medio camino, apoyado en los codos, cabeza colgando
SENTADO_GROG = con(SENTADO, Neck_alfred=(0, 0.35), Spine2_alfred=(0, 0.08))                                # sentado pero con la cabeza pesada
x_a, y_a = ra0[0], ra0[1]
aplicar(ARM, AR, TA[T0][0], TA[T0][1]); C_CAD = (ARM.matrix_world @ ARM.pose.bones["Hips_alfred"].head).xy.copy()   # la CADERA no se desplaza: gira sobre si mismo
def apoyar_fijo(p, e):
    """como `apoyar`, pero corrige x, y para que la cadera quede donde estaba (el giro de costado no lo traslada)"""
    r = (x_a, y_a, 0.0, e.x, e.y, e.z); aplicar(ARM, AR, p, r); h = (ARM.matrix_world @ ARM.pose.bones["Hips_alfred"].head).xy
    return apoyar(p, x_a + C_CAD.x - h.x, y_a + C_CAD.y - h.y, e)
GRUPOS = [(("Neck_alfred", "face_alfred"), 0), (("Spine_alfred", "Spine1_alfred", "Spine2_alfred", "Hips_alfred"), 3),
          (("RightUpArm_alfred", "Rightelbow_alfred", "LeftUpArm_alfred", "Leftelbow_alfred"), 6), (("RightUpLeg_alfred", "LeftUpLeg_alfred", "Rightknee_alfred", "Leftknee_alfred"), 9)]
def mez_escalonado(pa_, pb_, f, f0, dur):
    """la cabeza se mueve primero, luego el torso, los brazos y al final las piernas (accion superpuesta)"""
    out = {}; t_ = {}
    for nombres, d in GRUPOS:
        for n in nombres: t_[n] = ss((f - f0 - d) / float(dur))
    for n in pa_:
        u = t_.get(n, ss((f - f0) / float(dur + 6))); a_ = pa_[n].to_quaternion(); b_ = pb_[n].to_quaternion()
        if a_.dot(b_) < 0: b_.negate()
        out[n] = a_.slerp(b_, u).to_euler('XYZ', pa_[n])
    return out
for f in range(T0 + 1, T_CAE1 + 1):
    pa_prev = TA[T0][0]
    if f <= T_SIENTA0:                                                                      # SIN dormir de costado (a pedido): sigue boca arriba, respira lento
        pa = {n: Euler(v) for n, v in LY.items()}; e = rot_alfred(YAW_A); t = f - T0
        for n, ax, a_ in (("Spine1_alfred", 0, 0.025), ("Spine2_alfred", 0, 0.015)):
            v_ = list(pa[n]); v_[ax] += a_ * math.sin(t * 2 * math.pi / 60.0); pa[n] = Euler(v_)
    elif f <= T_SENTADO:                                                                    # SE LEVANTA COMO RECIEN DESPERTADO (60 f): se despereza, se apoya en los codos, pausa y se sienta pesado
        k = f - T_SIENTA0
        if k <= 10:                                                                         # 1) se despereza: gira la cabeza, estira un brazo, mueve las piernas
            u = math.sin(k / 10.0 * math.pi); pa = con(LY, Neck_alfred=(2, 0.18 * u), RightUpArm_alfred=(0, 0.35 * u), Rightelbow_alfred=(2, -0.3 * u), LeftUpLeg_alfred=(0, -0.15 * u))
        elif k <= 26:                                                                       # 2) se apoya en los CODOS (torso a medias), cabeza caida
            pa = mez_escalonado(LY, APOYO, f, T_SIENTA0 + 10, 12)
        elif k <= 36:                                                                       # 3) pausa aturdido: respira hondo y la cabeza cuelga
            pa = {n: Euler(v) for n, v in APOYO.items()}; u = (k - 26) / 10.0
            for n, ax, a_ in (("Spine1_alfred", 0, 0.04 * math.sin(u * math.pi)), ("Neck_alfred", 2, 0.12 * math.sin(u * 2 * math.pi))): v_ = list(pa[n]); v_[ax] += a_; pa[n] = Euler(v_)
        elif k <= 52:                                                                       # 4) termina de sentarse, pesado
            pa = mez_escalonado(APOYO, SENTADO_GROG, f, T_SIENTA0 + 36, 12)
        else:                                                                               # 5) levanta la cabeza
            pa = mez(SENTADO_GROG, SENTADO, ss((k - 52) / 8.0))
        e = rot_alfred(YAW_A)
    elif f < T_FLECHA:
        pa = {n: Euler(v) for n, v in SENTADO.items()}; e = rot_alfred(YAW_A)
    else:                                                                                   # FLECHA en el pecho: cae de espaldas (acelerando) y rebota un poco
        u = min(1.0, (f - T_FLECHA) / float(T_CAE1 - T_FLECHA)); pa = mez(SENTADO, LY, u * u); e = rot_alfred(YAW_A)
    TA[f] = (pa, apoyar_fijo(pa, e))
# ---- Jerry durante el sueno y el medio levantarse: quieto en su sitio, mira; respingo con la flecha ----
for f in range(T0 + 1, T_MUERDE2):
    t = f - T_FLECHA; susto = (0.25 * math.exp(-t / 4.0) * math.sin(t * 1.3)) if t >= 0 else 0.0
    pj = pose_jerry(1.0, 0.0, 0.0, 0.0); e = list(pj.get("spine_2", Euler())); e[2] += 0.35 * ss(t / 4.0) * (1 - ss((t - 12) / 8.0)) if t >= 0 else 0.0; e[0] -= susto; pj["spine_2"] = Euler(e)   # mira hacia el tunel
    TJ[f] = (pj, TJ[T0][1]); TJLOC[f] = TJLOC.get(T0, (0.0, 0.0, 0.0))
for f in range(T_CAE1 + 1, T_MUERDE2): TA[f] = ({n: Euler(v) for n, v in LY.items()}, TA[T_CAE1][1])   # queda tumbado (inconsciente otra vez)
# ---- arrastre a la IZQUIERDA (-y): la cabeza de Alfred va delante; los dos giran 90 grados en los 3 primeros tirones ----
aplicar(ARM, AR, LY, TA[T_CAE1][1]); C0 = ARM.matrix_world @ ARM.pose.bones["face_alfred"].tail
DIRF = Vector((0.0, -1.0, 0.0))
def cabeza_en(f):
    k = f - T_ARR0
    if k <= 0: return C0.copy(), 0.0
    i, r = divmod(k, TIRON); i = min(i, N2)
    s_ = (i + (ss(min(1.0, r / 9.0)) if i < N2 else 0.0)) * PASO2
    giro = ss(min(1.0, s_ / (3 * PASO2)))
    return C0 + Vector((0.25 * giro, 0, 0)) + DIRF * s_, giro
def raiz_alfred_yaw(p, cab, yaw):
    e = rot_alfred(yaw); r = (cab.x, cab.y, 0.0, e.x, e.y, e.z); aplicar(ARM, AR, p, r); c = ARM.matrix_world @ ARM.pose.bones["face_alfred"].tail
    return apoyar(p, r[0] + cab.x - c.x, r[1] + cab.y - c.y, e)
def raiz_jerry_yaw(p, G, yaw):
    r = (G.x, G.y, 0.0, 0.0, 0.0, yaw); aplicar(JA, JR, p, r)
    M = (JA.matrix_world @ JA.pose.bones["jaw_top"].tail + JA.matrix_world @ JA.pose.bones["jaw_bot"].tail) / 2
    x, y = r[0] + G.x - M.x, r[1] + G.y - M.y; return (x, y, piso_xy(x, y), 0.0, 0.0, yaw)
fase2 = 1.0; prev_c = C0.copy(); MD2 = [None]; SEP2 = 0.15                                        # la boca un poco FUERA de la capucha: la cabeza de Jerry no se mete en la de Alfred
for f in range(T_MUERDE2, T_SUELTA2 + 1):
    cab, giro = cabeza_en(f); yaw_a = YAW_A - math.pi / 2 * giro; yaw_j = YAW_J - math.pi / 2 * giro
    k = f - T_ARR0; tiron = math.sin(min(1.0, (k % TIRON) / 8.0) * math.pi) if 0 <= k < N2 * TIRON and (k % TIRON) < 8 else 0.0
    muerde = ss((f - T_MUERDE2) / 10.0) * (1 - ss((f - T_ARR1) / 10.0))
    # Alfred arrastrado (cabeza y hombros se levantan con el tiron)
    pa = {n: Euler(v) for n, v in LY.items()}
    for n, a in (("Neck_alfred", -0.10), ("Spine2_alfred", -0.05)):
        e = list(pa[n]); e[0] += a * tiron; pa[n] = Euler(e)
    TA[f] = (pa, raiz_alfred_yaw(pa, cab, yaw_a))
    # Jerry: baja a morder la capucha y camina hacia atras
    aplicar(ARM, AR, *TA[f]); dgx = bpy.context.evaluated_depsgraph_get(); e0 = bpy.data.objects["Mesh_0_alfred"].evaluated_get(dgx)
    vh = [e0.matrix_world @ v.co for v in e0.data.vertices]; hd = Vector((math.cos(yaw_a - YAW_A), math.sin(yaw_a - YAW_A), 0))   # direccion de la cabeza
    pm = max(v.dot(hd) for v in vh); fr_ = [v for v in vh if v.dot(hd) > pm - 0.12]
    Gc = sum(fr_, Vector()) / len(fr_); Gc = Gc + hd * (pm - Gc.dot(hd) - 0.05)
    fase2 -= (cab - prev_c).length / PASO2 * (CIC.CL / 2.0); prev_c = cab.copy()
    if muerde > 0.05:                                                                       # como en el 1.er arrastre: la cabeza baja SOLO lo justo para que la boca quede a la altura de la capucha
        mejor_ = None
        for md in (0.1, 0.25, 0.4, 0.55, 0.7, 0.85, 1.0):
            pj_ = pose_jerry(fase2, md * muerde, tiron, 0.75 * muerde); rj_ = raiz_jerry_yaw(pj_, Gc + hd * SEP2, yaw_j); aplicar(JA, JR, pj_, rj_)
            Mb = (JA.matrix_world @ JA.pose.bones["jaw_top"].tail + JA.matrix_world @ JA.pose.bones["jaw_bot"].tail) / 2
            if mejor_ is None or abs(Mb.z - Gc.z) < mejor_[0]: mejor_ = (abs(Mb.z - Gc.z), pj_, rj_, md)
        pj, rj = mejor_[1], mejor_[2]
        md_b = mejor_[3]; md_s = md_b if MD2[0] is None else MD2[0] + max(-0.06, min(0.06, md_b - MD2[0]))   # la cabeza no salta: cambia como mucho 0.06 por frame
        if abs(md_s - md_b) > 1e-6: pj = pose_jerry(fase2, md_s * muerde, tiron, 0.75 * muerde); rj = raiz_jerry_yaw(pj, Gc + hd * SEP2, yaw_j)
        MD2[0] = md_s
    else:
        pj = pose_jerry(fase2, 0.0, tiron, 0.0); rj = TJ[f - 1][1]
    if muerde <= 0.05 and f < T_ARR0: rj = TJ[T0][1]
    TJ[f] = (pj, rj); TJLOC[f] = tuple(Vector(TJLOC.get(T0, (0, 0, 0))) * (1 - ss((f - T_MUERDE2) / 8.0)))
# ---- se quita el SOMBRERO con la pata izquierda y le pega con el 3 veces ----
yaw_fin = YAW_J - math.pi / 2; rjF = TJ[T_SUELTA2][1]; paF = TA[T_SUELTA2]
aplicar(ARM, AR, *paF); _cab = ARM.matrix_world @ ARM.pose.bones["face_alfred"].tail; _atras = Vector((rjF[0] - _cab.x, rjF[1] - _cab.y, 0)).normalized()
rj0F = rjF; rjF = (-104.50, -73.128, 9.00, 0.0, 0.0, math.radians(-8.8992))                         # se queda FIJO en esta coordenada (pedido del usuario), apartado de Alfred
PATA_SOMB = {"front_shoulder.L": (100.0, 30.0, 30.0), "front_thigh.L": (0.0, 0.0, 0.0), "front_shin.L": (90.0, 0.0, 0.0), "front_foot.L": (20.0, 0.0, 0.0)}   # pata al sombrero (parte 9)
def con_somb(p, w):
    q = {k: Euler(v) for k, v in p.items()}
    for n, d in PATA_SOMB.items():
        e = list(q.get(n, Euler())); q[n] = Euler([e[i] + math.radians(d[i]) * w for i in range(3)])
    return q
# pose del golpe con el sombrero: la pata IZQUIERDA (con el sombrero) baja sobre la cara de Alfred
aplicar(ARM, AR, *paF); dgx = bpy.context.evaluated_depsgraph_get(); e0 = bpy.data.objects["Mesh_0_alfred"].evaluated_get(dgx); vh = [e0.matrix_world @ v.co for v in e0.data.vertices]
CARA2 = Vector((sum(v.x for v in vh) / len(vh), sum(v.y for v in vh) / len(vh), max(v.z for v in vh) + 0.08))
base2 = pose_jerry(1.0, 0.0, 0.0, 0.0); mejor = None
for sx in range(-20, 141, 10):
    for sz in range(-60, 61, 15):
        for sh in (0, 20, 40, 60):
            aplicar(JA, JR, con_pata(base2, "L", math.radians(sx), math.radians(sz), math.radians(sh)), rjF)
            d_ = ((JA.matrix_world @ JA.pose.bones["front_foot.L"].tail) - CARA2).length
            if mejor is None or d_ < mejor[0]: mejor = (d_, sx, sz, sh)
GS = (math.radians(mejor[1]), math.radians(mejor[2]), math.radians(mejor[3])); ALZA_S = (GS[0] + math.radians(55), GS[1], GS[2] - math.radians(20))
print("SOMBRERO: golpe con la pata a %.2f m de la cara (hombro X %d Z %d, espinilla %d)" % mejor)
for f in range(T_SUELTA2 + 1, FIN + 1):
    pj = pose_jerry(1.0, 0.0, 0.0, 0.0)
    if f <= T_SOMB1:                                                                        # la pata sube al sombrero, lo agarra y lo baja
        w = ss((f - T_SOMB0) / float(T_SOMB_AG - T_SOMB0)) if f <= T_SOMB_AG else 1.0 - ss((f - T_SOMB_AG) / float(T_SOMB1 - T_SOMB_AG)) * 0.6
        pj = con_somb(pj, w)
    else:
        pj = con_somb(pj, 0.4 * (1 - ss((f - T_SOMB1) / 6.0)))
        if f >= T_PONE - 12: pj = con_somb(pj, ss((f - T_PONE + 12) / 12.0) if f <= T_PONE else 1.0 - ss((f - T_PONE) / 9.0))   # sube la pata y se PONE el sombrero
        for g in GOLPES_S:
            t = f - g
            if -8 <= t < -2: w = ss((t + 8) / 6.0); pj = con_pata(pj, "L", *(ALZA_S[i] * w for i in range(3)))
            elif -2 <= t < 2: w = ss((t + 2) / 2.0); pj = con_pata(pj, "L", *(ALZA_S[i] + (GS[i] - ALZA_S[i]) * w for i in range(3)))
            elif 2 <= t < 9: w = 1.0 - ss((t - 2) / 7.0); pj = con_pata(pj, "L", *(GS[i] * w for i in range(3)))
    w_ap = ss((f - T_SUELTA2) / 8.0)                                                        # retrocede en 8 f al soltarlo
    rjf_ = tuple(rj0F[i] + (rjF[i] - rj0F[i]) * w_ap for i in range(6))
    TJ[f] = (pj, rjf_); TJLOC[f] = (0.0, 0.0, 0.0)
    pa = {n: Euler(v) for n, v in LY.items()}; nz = 0.0
    for i_, g in enumerate(GOLPES_S):                                                       # cada golpe le sacude la cabeza
        t = f - g
        if t >= 0: nz += (0.3 if i_ % 2 == 0 else -0.3) * ela(t)
    if f >= T_REAC and f < T_LEV2:                                                          # REACCIONA: levanta la cabeza, la sacude y mueve los brazos
        u = (f - T_REAC) / float(T_LEV2 - T_REAC); nz += 0.25 * math.sin(u * 3 * math.pi);
        for n, ax, a_ in (("Neck_alfred", 0, 0.30 * ss(u * 2)), ("Spine2_alfred", 0, 0.08 * ss(u * 2)), ("RightUpArm_alfred", 0, 0.15 * math.sin(u * math.pi))):
            v_ = list(pa[n]); v_[ax] += a_; pa[n] = Euler(v_)
    e = list(pa["Neck_alfred"]); e[2] += nz; pa["Neck_alfred"] = Euler(e)
    if f >= T_LEV2:                                                                         # SE LEVANTA hasta quedar de pie (referencia Mixamo levantarse_boca_arriba)
        k = min(NLEV, f - T_LEV2 + 1); pr = {n: Euler(v) for n, v in LY.items()}
        for n, fr in KLEV.items():
            if n in pr and k in fr: pr[n] = Euler(fr[k])
        pa = mez(TA[T_LEV2 - 1][0], pr, ss(k / 8.0)) if k < 8 else pr
        TA[f] = (pa, apoyar(pa, paF[1][0], paF[1][1], Euler(paF[1][3:])))
    else:
        TA[f] = (pa, paF[1])

# ---------------- 6) claves ----------------
def accion(A, R, TL, nombre):
    for ob in (A, R):
        ob.animation_data_create(); old = bpy.data.actions.get(nombre + ("_arm" if ob is A else "_raiz"))
        if old: bpy.data.actions.remove(old)
        ob.animation_data.action = bpy.data.actions.new(nombre + ("_arm" if ob is A else "_raiz"))
    prev = {}
    for f in sorted(TL):
        p, r = TL[f]; R.location = r[:3]; R.rotation_euler = r[3:]; R.keyframe_insert("location", frame=f); R.keyframe_insert("rotation_euler", frame=f)
        for n, e in p.items():
            e = Euler(e)
            if n in prev: e.make_compatible(prev[n])
            prev[n] = e; A.pose.bones[n].rotation_euler = e; A.pose.bones[n].keyframe_insert("rotation_euler", frame=f, group=n)
    for ob in (A, R):
        for c in [c for l in ob.animation_data.action.layers for s in l.strips for b in s.channelbags for c in b.fcurves]:
            for kp in c.keyframe_points: kp.interpolation = 'LINEAR'
accion(ARM, AR, TA, "p10_alfred_arrastrado"); accion(JA, JR, TJ, "p10_jerry_arrastra")
B6 = JA.pose.bones["spine_6"]
for f in sorted(TJ):                                                                        # el cuerpo de Jerry atras con `spine_6` (0 mientras jala)
    B6.location = TJLOC.get(f, (0.0, 0.0, 0.0)); B6.keyframe_insert("location", frame=f, group="spine_6")


# ---------------- 7b) la FLECHA del tunel al pecho y el SOMBRERO en la pata de Jerry ----------------
fl_m = bpy.data.objects["flecha_alfred"].data; D_loc = Vector((1, 1, 0)).normalized(); N_loc = Vector((0, 0, 1)); ESC = 0.45
punta_loc = max((v.co for v in fl_m.vertices), key=lambda c: c.dot(D_loc))
def M_flecha(punta_w, dir_w):
    d = dir_w.normalized(); lado = d.cross(Vector((0, 0, 1)))
    if lado.length < 1e-6: lado = Vector((1, 0, 0))
    lado.normalize(); perp_loc = N_loc.cross(D_loc).normalized(); Rl = Matrix((D_loc, perp_loc, N_loc)).transposed(); up_w = lado.cross(d).normalized()
    R = (Matrix((d, up_w, lado)).transposed() @ Rl.inverted()).to_4x4(); M = R @ Matrix.Diagonal((ESC, ESC, ESC, 1))
    return Matrix.Translation(punta_w - (M @ punta_loc.to_4d()).to_3d()) @ M
def obj(nombre, me):
    o = bpy.data.objects.get(nombre)
    if o is None: o = bpy.data.objects.new(nombre, me); sc.collection.objects.link(o)
    o.animation_data_clear(); o.parent = None; o.rotation_mode = 'QUATERNION'
    if not any(m_.type == 'SOLIDIFY' for m_ in o.modifiers):                              # GROSOR como en objetos/vanilla/arrow/arrow.blend (sin esto la flecha es un plano)
        m_ = o.modifiers.new("Solidify", 'SOLIDIFY'); m_.thickness = 0.1; m_.offset = 0.0; m_.use_rim = True; m_.use_even_offset = False
    return o
def visible(o, tramos):
    """tramos = [(frame, visible)]"""
    for f, v in tramos:
        o.hide_viewport = not v; o.hide_render = not v
        for dp in ("hide_viewport", "hide_render"): o.keyframe_insert(dp, frame=f)
    for c in [c for l in o.animation_data.action.layers for st in l.strips for b in st.channelbags for c in b.fcurves if c.data_path.startswith("hide")]:
        for kp in c.keyframe_points: kp.interpolation = 'CONSTANT'
sc.frame_set(T_FLECHA); vl.update(); dgx = bpy.context.evaluated_depsgraph_get()
e1 = bpy.data.objects["Mesh_1_alfred"].evaluated_get(dgx); vt = [e1.matrix_world @ v.co for v in e1.data.vertices]
pech = ARM.matrix_world @ ARM.pose.bones["Spine2_alfred"].head
cand = [v for v in vt if abs(v.z - pech.z) < 0.12 and abs(v.y - pech.y) < 0.15] or vt
sup = min(cand, key=lambda v: v.x)                                                          # el PECHO mira al tunel (-x)
d_f = Vector((1.0, 0.0, -0.04)).normalized(); P_IMP = sup + d_f * 0.08; P0 = P_IMP - d_f * 7.0
fv = obj("flecha_pecho_vuelo", fl_m)
for k in range(VUELO_F + 1):
    u = k / VUELO_F; pp = P0.lerp(P_IMP, u); pp.z += 0.15 * 4 * u * (1 - u); M = M_flecha(pp, d_f)
    fv.matrix_world = M
    for dp in ("location", "rotation_quaternion", "scale"): fv.keyframe_insert(dp, frame=T_FLECHA - VUELO_F + k)
visible(fv, [(1, False), (T_FLECHA - VUELO_F, True), (T_FLECHA, False)])
fp = obj("flecha_pecho", fl_m); sc.frame_set(T_FLECHA); vl.update()
fp.parent = ARM; fp.parent_type = 'BONE'; fp.parent_bone = "Spine2_alfred"; vl.update(); fp.matrix_world = M_flecha(P_IMP, d_f)
visible(fp, [(1, False), (T_FLECHA, True)])
# sombrero: el original (con piel) se oculta al agarrarlo; una copia rigida sigue a la pata izquierda
SOM = bpy.data.objects["sombrero_jerry"]; LIB = bpy.data.objects.get("sombrero_jerry_libre")
sc.frame_set(T_SOMB_AG); vl.update(); dgx = bpy.context.evaluated_depsgraph_get()
me_h = bpy.data.meshes.new_from_object(SOM.evaluated_get(dgx)); me_h.transform(SOM.matrix_world); me_h.name = "sombrero_jerry_libre_p10"
if LIB is None: LIB = bpy.data.objects.new("sombrero_jerry_libre", me_h); sc.collection.objects.link(LIB)
else: LIB.data = me_h
LIB = obj("sombrero_jerry_libre", me_h); LIB.matrix_world = Matrix.Identity(4)
def BWJ(n): return JA.matrix_world @ JA.pose.bones[n].matrix
P_AG = BWJ("front_foot.L").copy()
S_AG = BWJ("sombrero").copy(); C_SOMB = sum((v.co for v in me_h.vertices), Vector()) / len(me_h.vertices)
for f in range(T_SOMB_AG, T_PONE + 1):                                                       # en la pata; los ultimos 6 f se ACOMODA en la cabeza
    sc.frame_set(f); vl.update(); Mp = BWJ("front_foot.L") @ P_AG.inverted(); Mh = BWJ("sombrero") @ S_AG.inverted()
    t_ = ss((f - (T_PONE - 6)) / 6.0)
    if t_ > 0:
        qp = Mp.to_quaternion(); qh = Mh.to_quaternion()                                      # se interpola el CENTRO del sombrero (no la traslacion: la malla esta en coordenadas de mundo)
        if qp.dot(qh) < 0: qh.negate()
        cp = Mp @ C_SOMB; ch_ = Mh @ C_SOMB
        Mp = Matrix.Translation(cp.lerp(ch_, t_)) @ qp.slerp(qh, t_).to_matrix().to_4x4() @ Matrix.Translation(-C_SOMB)
    LIB.matrix_world = Mp
    for dp in ("location", "rotation_quaternion", "scale"): LIB.keyframe_insert(dp, frame=f)
visible(LIB, [(1, False), (T_SOMB_AG, True), (T_PONE, False)])
SOM.animation_data_create()
for dp in ("hide_viewport", "hide_render"):
    setattr(SOM, dp, False); SOM.keyframe_insert(dp, frame=1); SOM.keyframe_insert(dp, frame=T_SOMB_AG - 1); setattr(SOM, dp, True); SOM.keyframe_insert(dp, frame=T_SOMB_AG)
    SOM.keyframe_insert(dp, frame=T_PONE - 1); setattr(SOM, dp, False); SOM.keyframe_insert(dp, frame=T_PONE)        # de nuevo en la cabeza
for c in [c for l in SOM.animation_data.action.layers for st in l.strips for b in st.channelbags for c in b.fcurves if c.data_path.startswith("hide")]:
    for kp in c.keyframe_points: kp.interpolation = 'CONSTANT'

print("FLECHA al pecho en f%d (de x %.1f), sombrero agarrado en f%d, golpes con el sombrero %s" % (T_FLECHA, P0.x, T_SOMB_AG, GOLPES_S))

# ---------------- 7) flechas de la parte 9 (emparentadas al hueso) y ojos cerrados ----------------
OFF = json.load(open(DOC + r"\parte10\flechas_offsets_parte9.json", encoding="utf-8"))
faltan = [n for n in OFF if n not in bpy.data.objects]
if faltan:
    with bpy.data.libraries.load(D9, link=False) as (s_, d_): d_.objects = faltan
    for o in d_.objects:
        if o is not None: sc.collection.objects.link(o)
sc.frame_set(1); vl.update()
for n, rec in OFF.items():
    o = bpy.data.objects[n]; o.animation_data_clear()
    for c in list(o.constraints): o.constraints.remove(c)
    o.hide_viewport = False; o.hide_render = False
    Mb = ARM.matrix_world @ ARM.pose.bones[rec["hueso"]].matrix; Mw = Mb @ Matrix(rec["off"])
    o.parent = ARM; o.parent_type = 'BONE'; o.parent_bone = rec["hueso"]; vl.update(); o.matrix_world = Mw
for n in ("ojo_izquierdo_alfred", "ojo_derecho_alfred"):
    o = bpy.data.objects.get(n)
    if o and o.data.shape_keys and "Closed" in o.data.shape_keys.key_blocks:
        ck = o.data.shape_keys.key_blocks["Closed"]; o.hide_viewport = False; o.hide_render = False
        ad = o.data.shape_keys.animation_data
        if ad and ad.action: ad.action = None
        ck.value = 0.92; ck.keyframe_insert("value", frame=1)
        for f_, v_ in sorted(OJOS.items()): ck.value = v_; ck.keyframe_insert("value", frame=f_)
sc.frame_start = 1; sc.frame_end = FIN; sc.frame_set(1)
print("ARRASTRE: %d tirones de %.2f m, f1-%d; yaw Alfred %.0f, Jerry %.0f" % (N, PASO, FIN, math.degrees(YAW_A), math.degrees(YAW_J)))
