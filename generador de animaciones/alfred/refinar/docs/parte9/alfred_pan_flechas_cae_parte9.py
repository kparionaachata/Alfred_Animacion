# -*- coding: utf-8 -*-
"""Parte 9 (base_parte_9.blend, empieza en f1 con Alfred en (-132, -70.309, 7) rz 90 mirando la cueva, manos en la cintura y una flecha clavada en la frente):
 1) con la flecha en la cabeza saca de la espalda un PAN (`objetos/vanilla/bread/bread.blend`) con su gesto de tomar algo de la espalda (Biblioteca del tunel: `toma`), lo lleva a la boca
    y COME como en el juego (pan delante de la boca, mano subiendo y bajando rapido 40 f, `entity.generic.eat` cada 5 f; el pan desaparece al final);
 2) SENALA hacia abajo con el brazo DERECHO estirado al esqueleto de la cueva (S) y lo acusa (vaiven) 30 f; le cae una FLECHA en la mano derecha (sale de S) y la mano va al pecho;
 3) hace lo mismo con la IZQUIERDA y le cae otra flecha en la mano izquierda;
 4) intenta mantenerse en pie (se tambalea) y le cae una flecha en la ENTREPIERNA: reaccion con `animacion_alfred_golpe_entrepierna.py` (Mixamo, 100 f, 14 huesos; copia en
    `acciones/`), se dobla y CAE del escalon BOCA ABAJO hasta (-133.5, -70.5, 0) con un rebote.
Las flechas (copias de `flecha_alfred`) y el pan se hornean por frame relativos al hueso donde estan (frente -> `Neck_alfred`, manos -> codos, entrepierna -> `Hips_alfred`).
Escribe las acciones `p9_alfred_root` / `p9_alfred_armature` (Alfred no tenia animacion en la base). Repetible (rehace todo). Ejecutar en Blender con exec."""
import bpy, math, ast, random, sys, importlib.util
from mathutils import Vector, Euler, Matrix, Quaternion
import alfred_animation_studio.tunel as tn

sc = bpy.context.scene; vl = bpy.context.view_layer
ARM = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'Hips_alfred' in o.pose.bones); ROOT = ARM.parent
S = Vector(sc["p9_arco_S"]) if "p9_arco_S" in sc else Vector((-139.5, -70.5, 1.5))           # origen de las flechas: la CUERDA del arco del esqueleto (esqueleto_dispara_parte9.py)
CAIDA = Vector((-134.2, -70.5, 1.0)); ALTO_TUMBADO = 0.25                                  # cae BOCA ARRIBA encima del bloque pared_piedra_-135_-71_0
ss = lambda t: 0.0 if t <= 0 else 1.0 if t >= 1 else t * t * (3 - 2 * t)
D = math.radians
for o in (ROOT, ARM):
    if o.animation_data and o.animation_data.action: o.animation_data.action = None
B = [b.name for b in ARM.pose.bones]
for n in B: ARM.pose.bones[n].rotation_mode = 'XYZ'
ARM.pose.bones["RightUpArm_alfred"].location = (0.0071, 0.0968, -0.0861); ARM.pose.bones["LeftUpArm_alfred"].location = (-0.0071, 0.0968, -0.0861)
for n_ in ("RightUpArm_alfred", "LeftUpArm_alfred"): ARM.pose.bones[n_].scale = (1.0, 1.0, 1.0)
if "p9_pose_base" not in sc:
    sc["p9_pose_base"] = {n: list(ARM.pose.bones[n].rotation_euler) for n in B}; sc["p9_root_base"] = list(ROOT.location) + list(ROOT.rotation_euler)
P0_ORIG = {n: Euler(sc["p9_pose_base"][n], 'XYZ') for n in B}; R0 = tuple(sc["p9_root_base"])
MIRA_ABAJO = 0.35                                                                            # desde el frame 1 Alfred MIRA HACIA ABAJO (cuello X +0.35, ~20 grados)
P0 = {n: Euler(v) for n, v in P0_ORIG.items()}; P0["Neck_alfred"] = Euler((P0["Neck_alfred"].x + MIRA_ABAJO, P0["Neck_alfred"].y, P0["Neck_alfred"].z))
FWD = Vector((-math.sin(R0[5]), math.cos(R0[5]), 0))

def mez(p, q, t):
    out = {}
    for n in p:
        a = p[n].to_quaternion(); b = q[n].to_quaternion()
        if a.dot(b) < 0: b.negate()
        out[n] = a.slerp(b, t).to_euler('XYZ', p[n])
    return out
TL = {}; cur = [2]; ult = {"p": dict(P0)}; TL[1] = (dict(P0), R0)
def poner(p, r=R0): TL[cur[0]] = (p, r); ult["p"] = p; cur[0] += 1
def hacia(p, n, curva=ss):
    p0 = ult["p"]
    for i in range(n): poner(mez(p0, p, curva((i + 1) / n)))
def mantener(n, extra=None):
    base = ult["p"]
    for i in range(n):
        q = {k: Euler(v) for k, v in base.items()}
        if extra: extra(q, i)
        poner(q); ult["p"] = base
    ult["p"] = q
def aplicar_pose(p, r):
    ROOT.location = r[:3]; ROOT.rotation_euler = r[3:]
    for n, e in p.items(): ARM.pose.bones[n].rotation_euler = e
    vl.update()

# ---------------- puntos del cuerpo (en la pose base) ----------------
aplicar_pose(P0, R0); dg = bpy.context.evaluated_depsgraph_get()
def verts(n): o = bpy.data.objects[n].evaluated_get(dg); return [o.matrix_world @ v.co for v in o.data.vertices]
cab = verts("Mesh_0_alfred"); tor = verts("Mesh_1_alfred"); pier = verts("Mesh_4_alfred") + verts("Mesh_5_alfred")
cc = sum(cab, Vector()) / len(cab); zc0, zc1 = min(v.z for v in cab), max(v.z for v in cab)
BOCA = cc + FWD * (max(v.dot(FWD) for v in cab) - cc.dot(FWD) + 0.04); BOCA.z = zc0 + 0.28 * (zc1 - zc0)
tc = sum(tor, Vector()) / len(tor); zt0, zt1 = min(v.z for v in tor), max(v.z for v in tor)
PECHO = tc + FWD * (max(v.dot(FWD) for v in tor) - tc.dot(FWD) + 0.10); PECHO.z = zt0 + 0.62 * (zt1 - zt0)
pc = sum(pier, Vector()) / len(pier); zp1 = max(v.z for v in pier)
ENTRE = pc + FWD * (max(v.dot(FWD) for v in pier) - pc.dot(FWD)); ENTRE.z = zp1 - 0.10; ENTRE.y = pc.y

# ---------------- brazos: apuntar la mano (codo doblado lo justo) ----------------
LADO = {"R": ("RightUpArm_alfred", "Rightelbow_alfred", "Mesh_2_alfred", -1), "L": ("LeftUpArm_alfred", "Leftelbow_alfred", "Mesh_3_alfred", 1)}
OFF = {}
for k_, (ua, el, me, sg) in LADO.items():
    aplicar_pose(P0, R0); dg = bpy.context.evaluated_depsgraph_get(); sh = ARM.matrix_world @ ARM.pose.bones[ua].head
    tip = max(verts(me), key=lambda v: (v - sh).length); OFF[k_] = (ARM.matrix_world @ ARM.pose.bones[el].matrix).inverted() @ tip
def punta(lado): return (ARM.matrix_world @ ARM.pose.bones[LADO[lado][1]].matrix) @ OFF[lado]
def apuntar(lado, base, objetivo=None, direccion=None):
    ua, el, me, sg = LADO[lado]; p = {k: Euler(v) for k, v in base.items()}; p[ua] = Euler((1.570796, 0, 0)); p[el] = Euler((0, 0, 0)); aplicar_pose(p, R0)
    pbu, pbe = ARM.pose.bones[ua], ARM.pose.bones[el]; sh = ARM.matrix_world @ pbu.head
    if objetivo is not None:
        Dd = (objetivo - sh).length; mejor = None
        for kz in range(0, 151, 3):
            pbe.rotation_euler = (0, 0, sg * D(kz)); vl.update(); d_ = abs((punta(lado) - sh).length - Dd)
            if mejor is None or d_ < mejor[0]: mejor = (d_, kz)
        pbe.rotation_euler = (0, 0, sg * D(mejor[1])); vl.update(); tgt = objetivo
    else: tgt = sh + direccion.normalized() * 2.0
    for _ in range(3):
        qd = (punta(lado) - sh).rotation_difference(tgt - sh); Mw = ARM.matrix_world @ pbu.matrix
        pbu.matrix = ARM.matrix_world.inverted() @ (Matrix.Translation(sh) @ qd.to_matrix().to_4x4() @ Matrix.Translation(-sh)) @ Mw; vl.update()
    p[ua] = Euler(pbu.rotation_euler); p[el] = Euler(pbe.rotation_euler); return p
def con(p, **cambios):
    q = {k: Euler(v) for k, v in p.items()}
    for n, (i, dv) in cambios.items(): e = list(q[n]); e[i] += dv; q[n] = Euler(e)
    return q

# ================= 1) PAN =================
bib = tn.Biblioteca(); EV = []
mantener(8)
t_toma = cur[0]
for i, pz in enumerate(bib.toma):
    p = {k: Euler(v) for k, v in P0.items()}
    for n in ("RightUpArm_alfred", "Rightelbow_alfred"): p[n] = Euler([D(x) for x in pz[n][0:3]])
    poner(mez(ult["p"], p, ss((i + 1) / 5.0)) if i < 4 else p)
T_AGARRA = t_toma + bib.toma_agarre; EV.append((T_AGARRA, 'item.armor.equip_generic', 'objetos', 0.5, 'alfred_saca_pan'))
# COMER COMO EN EL JUEGO: el pan queda delante de la boca y la mano sube y baja rapido (periodo 5 f) unos 40 f, con el sonido de comer repetido; al final el pan desaparece entero
COMER = 40; ARRIBA = BOCA + FWD * 0.10 + Vector((0, 0, -0.02)); ABAJO = ARRIBA + Vector((0, 0, -0.07))
p_arr = apuntar("R", P0, ARRIBA); p_aba = apuntar("R", P0, ABAJO)
hacia(p_arr, 9); MORDISCOS = []; t0c = cur[0]
for i in range(COMER):
    poner(mez(p_arr, p_aba, 0.5 - 0.5 * math.cos(2 * math.pi * i / 5.0)))
    if i % 5 == 0: EV.append((t0c + i, 'entity.generic.eat', 'objetos', 0.6, 'alfred_come'))
T_PAN_FIN = cur[0] - 1
hacia(P0, 10); mantener(10)

# ================= 2) senala con la DERECHA y flecha en la mano =================
def mirar_abajo(p): return con(p, Neck_alfred=(0, 0.45 - MIRA_ABAJO))                     # ya mira abajo desde el inicio: solo baja un poco mas
p = mirar_abajo(dict(ult["p"])); aplicar_pose(p, R0); sh = ARM.matrix_world @ ARM.pose.bones["RightUpArm_alfred"].head
p_sena_R = apuntar("R", p, direccion=S - sh)
hacia(p_sena_R, 10)
def acusa(lado):
    ua = LADO[lado][0]
    return lambda q, i: q.__setitem__(ua, Euler((q[ua].x, q[ua].y + D(5) * math.sin(i * 0.9), q[ua].z)))
T_VOZ = cur[0]; sc["p9_voz_inicio"] = T_VOZ                                              # con el brazo ya arriba dice "Oye, tu no te pases de pena." (voz hasta T_VOZ+32)
mantener(35, acusa("R")); H1 = cur[0]                                                     # la flecha le impacta JUSTO al terminar la frase
DER = Vector((FWD.y, -FWD.x, 0))                                                            # derecha de Alfred
def afuera(lado, base, sale=0.58, adelante=0.08):
    aplicar_pose(base, R0); sh_ = ARM.matrix_world @ ARM.pose.bones[LADO[lado][0]].head; v = DER if lado == "R" else -DER
    return apuntar(lado, base, sh_ + v * sale + FWD * adelante + Vector((0, 0, -0.12)))       # el impacto le ABRE el brazo hacia su lado
def reaccion(lado, tiron):
    """tiron hacia afuera (4 f) y despues el brazo CAE y queda SUELTO colgando, con un balanceo que se amortigua (no rigido)"""
    ua, el, me, sg = LADO[lado]
    hacia(tiron, 4, curva=lambda t: 1 - (1 - t) ** 3)
    cuelga = {k: Euler(v) for k, v in ult["p"].items()}; cuelga[ua] = Euler((1.570796, 0.0, 0.0)); cuelga[el] = Euler((0.0, 0.0, sg * 0.15))
    for i in range(28):
        q = mez(tiron, cuelga, ss((i + 1) / 8.0)); e = list(q[ua]); e[0] += 0.30 * math.exp(-i / 8.0) * math.sin(i * 2 * math.pi / 10.0); q[ua] = Euler(e)
        poner(q)
    ult["p"] = cuelga
reaccion("R", afuera("R", ult["p"]))
for k in range(cur[0] - H1):                                                                 # al recibir la flecha GIRA LA CABEZA RAPIDO a ver su brazo derecho y luego vuelve a mirar abajo
    w = ss(k / 5.0) if k < 5 else (1.0 if k < 18 else 1.0 - ss((k - 18) / 10.0))
    if w > 0: TL[H1 + k] = (con(TL[H1 + k][0], Neck_alfred=(1, -0.85 * w)), TL[H1 + k][1]); TL[H1 + k][0]["Neck_alfred"].x += 0.20 * w

# ================= 3) senala con la IZQUIERDA y flecha en la mano =================
p = mirar_abajo(dict(ult["p"])); aplicar_pose(p, R0); sh = ARM.matrix_world @ ARM.pose.bones["LeftUpArm_alfred"].head
p_sena_L = apuntar("L", p, direccion=S - sh)
hacia(p_sena_L, 10); T_VOZ2 = cur[0]; sc["p9_voz2_inicio"] = T_VOZ2                    # con el brazo izquierdo arriba dice "Ay, vas a ver cuando baje." (voz hasta T_VOZ2+33)
mantener(36, acusa("L")); H2 = cur[0]                                                      # segunda flecha justo al terminar la frase
reaccion("L", afuera("L", ult["p"], sale=0.0, adelante=-0.35))                              # a su izquierda esta la pared de piedra (y -71): tiron corto hacia afuera y hacia ATRAS
for k in range(cur[0] - H2):                                                                 # tambien mira RAPIDO su brazo izquierdo y vuelve a mirar abajo
    w = ss(k / 5.0) if k < 5 else (1.0 if k < 18 else 1.0 - ss((k - 18) / 10.0))
    if w > 0: TL[H2 + k] = (con(TL[H2 + k][0], Neck_alfred=(1, 0.85 * w)), TL[H2 + k][1]); TL[H2 + k][0]["Neck_alfred"].x += 0.20 * w

# ================= 4) se tambalea =================
def tambalea(q, i):
    for n, ax, a in (("Spine_alfred", 2, 0.10), ("Spine1_alfred", 0, 0.06), ("Hips_alfred", 2, 0.05)):
        e = list(q[n]); e[ax] += a * math.sin(i * 2 * math.pi / 14.0); q[n] = Euler(e)
T_VOZ3 = cur[0]; sc["p9_voz3_inicio"] = T_VOZ3                                            # ya mirando abajo otra vez dice "Ok, se acabo, cuando baje te voy a..." (voz hasta T_VOZ3+51)
mantener(54); H3 = cur[0]                                                                    # quieto; la flecha en la entrepierna llega JUSTO al terminar la frase

# ================= 5) flecha en la entrepierna, reaccion (Mixamo) y CAIDA =================
src = open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\animacion_alfred_golpe_entrepierna.py", encoding="utf-8").read()
KD = next(ast.literal_eval(n.value) for n in ast.parse(src).body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "KEYFRAME_DATA")
NREF = max(max(v) for v in KD.values()); base = ult["p"]
for k in range(1, NREF + 1):
    p = {kk: Euler(v) for kk, v in base.items()}
    for n, fr in KD.items():
        if n in p and k in fr: p[n] = Euler(fr[k])
    poner(mez(base, p, ss(k / 4.0)) if k < 4 else p)
T_FIN_REF = cur[0] - 1; mantener(30)
F_CAE = H3 + 14; DUR = 26; FIN_P9 = 700
INCLINA = 8                                                                                  # se inclina hacia delante sobre los pies y cae (gravedad) GIRANDO: aterriza BOCA ARRIBA sobre el bloque pared_piedra_-135_-71_0
F_SUELO = F_CAE + INCLINA + DUR; sc["p9_f_suelo"] = F_SUELO
TOPE = 1.0; HIPS_XY = Vector((-133.97, -70.5))                                                # cara superior del bloque (z 1); cadera sobre el bloque, cabeza y piernas fuera de sus bordes
YAW_F = R0[5] + math.pi                                                                      # tumbado con la cabeza hacia -x (hacia donde cae) y los pies hacia la pared
# ---- pose TUMBADO: referencia Mixamo "posicion boca arriba" (acciones/animacion_alfred_boca_arriba.py, frame 1) + lo que no se apoya CUELGA ----
src_ba = open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\animacion_alfred_boca_arriba.py", encoding="utf-8").read()
KBA = next(ast.literal_eval(n.value) for n in ast.parse(src_ba).body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "KEYFRAME_DATA")
LY = {k: Euler(v) for k, v in P0.items()}
for n, fr in KBA.items():
    if n in LY: LY[n] = Euler(fr[1])
LY = con(LY, Neck_alfred=(0, 0.35), RightUpLeg_alfred=(0, -0.80), LeftUpLeg_alfred=(0, -0.80), Rightknee_alfred=(0, -0.80), Leftknee_alfred=(0, -0.80))   # espalda y cabeza sobre la piedra (cadera en el borde +x); las PIERNAS cuelgan por ese borde
def raiz_fin(p):
    r = (HIPS_XY.x, HIPS_XY.y, 0.0, 0.0, 0.0, YAW_F); aplicar_pose(p, r); hp = ARM.matrix_world @ ARM.pose.bones["Hips_alfred"].head
    r = (r[0] + HIPS_XY.x - hp.x, r[1] + HIPS_XY.y - hp.y, 0.0, 0.0, 0.0, YAW_F); aplicar_pose(p, r); dg_ = bpy.context.evaluated_depsgraph_get()
    zt = min((o_.matrix_world @ v.co).z for n_ in ("Mesh_0_alfred", "Mesh_1_alfred") for o_ in [bpy.data.objects[n_].evaluated_get(dg_)] for v in o_.data.vertices
             if -135.0 < (o_.matrix_world @ v.co).x < -134.0 and -71.0 < (o_.matrix_world @ v.co).y < -70.0)                          # ESPALDA y CABEZA apoyadas en la piedra (lo que esta encima del bloque)
    return (r[0], r[1], TOPE + 0.005 - zt, 0.0, 0.0, YAW_F)
RF = raiz_fin(LY)
_R0 = R0; R0 = RF                                                                            # brazos colgando a los lados del bloque (apuntar usa R0)
aplicar_pose(LY, RF); shR = ARM.matrix_world @ ARM.pose.bones["RightUpArm_alfred"].head; shL = ARM.matrix_world @ ARM.pose.bones["LeftUpArm_alfred"].head
def fuera(sh):
    s_ = 1.0 if sh.y > HIPS_XY.y else -1.0
    return Vector((sh.x, sh.y + s_ * 0.30, TOPE - 0.55))                                       # los hombros quedan casi en el borde: los brazos CUELGAN por los lados del bloque
for lado_, sh_ in (("R", shR), ("L", shL)):                                                 # brazo ESTIRADO hacia el lado sobre la piedra (sale del borde) y el antebrazo CUELGA
    s_ = 1.0 if sh_.y > HIPS_XY.y else -1.0
    LY = apuntar(lado_, LY, direccion=Vector((0.0, s_, -0.15)))
    el_ = LADO[lado_][1]; mejor_ = None
    for kz in range(-120, 121, 6):
        q_ = {k: Euler(v) for k, v in LY.items()}; q_[el_] = Euler((0, 0, D(kz))); aplicar_pose(q_, RF)
        z_ = (ARM.matrix_world @ ARM.pose.bones[el_].tail).z; y_ = (ARM.matrix_world @ ARM.pose.bones[el_].tail).y
        sc_ = z_ + (5.0 if abs(y_ - HIPS_XY.y) < 0.62 else 0.0)                                # mano lo mas abajo posible pero FUERA del bloque
        if mejor_ is None or sc_ < mejor_[0]: mejor_ = (sc_, kz)
    LY[el_] = Euler((0, 0, D(mejor_[1])))
R0 = _R0
RF = raiz_fin(LY)
def raiz(f):
    if f < F_CAE: return R0
    if f < F_CAE + INCLINA: u = (f - F_CAE) / INCLINA; return (R0[0], R0[1], R0[2], -D(25) * u * u, 0.0, R0[5])
    u = min(1.0, (f - F_CAE - INCLINA) / DUR)
    x = R0[0] + (RF[0] - R0[0]) * u; y = R0[1] + (RF[1] - R0[1]) * u; z = R0[2] + (RF[2] - R0[2]) * u * u        # cae acelerando
    q0 = Euler((-D(25), 0.0, R0[5])).to_quaternion(); q1 = Euler((0.0, 0.0, YAW_F)).to_quaternion()
    if q0.dot(q1) < 0: q1.negate()
    e = q0.slerp(q1, ss(u)).to_euler('XYZ', Euler((-D(25), 0.0, R0[5]))); return (x, y, z, e.x, e.y, e.z)
p_ini = TL[F_CAE + INCLINA - 1][0]
for f in range(F_CAE + INCLINA, FIN_P9 + 1):                                                 # en el aire pasa a la pose tumbado (de espaldas); despues queda TUMBADO
    u = min(1.0, (f - F_CAE - INCLINA) / DUR); TL[f] = (mez(p_ini, LY, ss(u)), None)
# ---- ESPASMOS musculares sobre la piedra: sacudidas cortas al azar en brazos, piernas, columna y cuello + temblor fino ----
rng_e = random.Random(77); ESP = []; f_ = F_SUELO + 8
NOMS_E = ["RightUpArm_alfred", "LeftUpArm_alfred", "Rightelbow_alfred", "Leftelbow_alfred", "RightUpLeg_alfred", "LeftUpLeg_alfred", "Rightknee_alfred", "Leftknee_alfred", "Spine1_alfred", "Neck_alfred"]
while f_ < FIN_P9 - 6:
    ESP.append((f_, rng_e.uniform(0.5, 1.0), rng_e.sample(NOMS_E, 3), [rng_e.uniform(-1, 1) for _ in range(3)]))
    f_ += rng_e.randint(9, 26) if f_ < F_SUELO + 120 else rng_e.randint(18, 40)               # mas seguidos al principio, se van espaciando
AMP_E = {"RightUpArm_alfred": 0.22, "LeftUpArm_alfred": 0.22, "Rightelbow_alfred": 0.30, "Leftelbow_alfred": 0.30, "RightUpLeg_alfred": 0.12, "LeftUpLeg_alfred": 0.12,
         "Rightknee_alfred": 0.25, "Leftknee_alfred": 0.25, "Spine1_alfred": 0.06, "Neck_alfred": 0.10}
for f in range(F_SUELO + 1, FIN_P9 + 1):
    p = {k: Euler(v) for k, v in TL[f][0].items()}
    for (f0, a, huesos, sg) in ESP:
        k = f - f0
        if 0 <= k <= 6:
            w = a * (math.sin(k / 6.0 * math.pi) * math.exp(-k / 4.0) * 1.6) * (1 if k % 2 == 0 else 0.55)     # tiron con rebote seco
            for n, sgn in zip(huesos, sg): e = list(p[n]); e[0] += AMP_E[n] * w * sgn; e[2] += AMP_E[n] * 0.5 * w * sgn; p[n] = Euler(e)
    for n in ("Rightelbow_alfred", "Leftelbow_alfred", "Rightknee_alfred", "Leftknee_alfred"):                    # temblor fino constante
        e = list(p[n]); e[0] += 0.012 * math.sin(f * 2.3 + len(n)); p[n] = Euler(e)
    TL[f] = (p, None)
FIN = max(TL)
TL = {f: (TL[f][0], raiz(f) if f >= F_CAE else (TL[f][1] or R0)) for f in TL}
# FILTROS ORGANICOS de Alfred (paso 3 del estudio; valores de la parte 8: respiracion del usuario 0.020 / 0.010 / 0.00): se SUMAN a las poses ANTES de hornear flechas y pan
def noise_at(frame, freq, seed, dim=0):
    v = math.sin(frame * freq * 1.3 + seed * 7.3 + dim * 3.7); v += math.sin(frame * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5; v += math.sin(frame * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25
    return v / 1.75
AMP_R, VEL_R, FASE_R = 0.020, 0.010, 0.0
for f in TL:
    p = {k: Euler(v) for k, v in TL[f][0].items()}
    for n in ("Spine_alfred", "Spine1_alfred"):
        e = list(p[n]); e[0] += AMP_R * math.sin(f * VEL_R * 2 * math.pi + FASE_R); e[2] += AMP_R * 0.4 * math.sin(f * VEL_R * 2 * math.pi + FASE_R + 1.2); p[n] = Euler(e)
    for n in ("Neck_alfred", "face_alfred"):
        e = list(p[n])
        for ax in range(3): e[ax] += 0.023 * noise_at(f, 0.079, 693, ax)
        p[n] = Euler(e)
    TL[f] = (p, TL[f][1])
ESC_PECHO = {f: 0.010 * math.sin(f * VEL_R * 2 * math.pi + FASE_R) for f in TL}             # micro-escala Z de Spine1 (se escribe con las claves de Alfred)
MESHES = ("Mesh_0_alfred", "Mesh_1_alfred", "Mesh_2_alfred", "Mesh_3_alfred", "Mesh_4_alfred", "Mesh_5_alfred")
# el golpe contra el suelo: el mismo sonido del golpe del pico en la cabeza de la parte 8
EV += [(F_SUELO, 'entity.player.attack.strong', 'golpes', 0.9, 'alfred_cae_suelo'), (F_SUELO + 1, 'entity.player.hurt', 'voces', 0.85, 'alfred_quejido_caida')]

# ---------------- flechas y pan (horneados relativos al hueso) ----------------
fl0 = bpy.data.objects["flecha_alfred"]; D_loc = Vector((1, 1, 0)).normalized(); N_loc = Vector((0, 0, 1)); ESC = 0.45
punta_loc = max((v.co for v in fl0.data.vertices), key=lambda c: c.dot(D_loc))
def M_flecha(punta_w, dir_w):
    d = dir_w.normalized(); lado = d.cross(Vector((0, 0, 1)))
    if lado.length < 1e-6: lado = Vector((1, 0, 0))
    lado.normalize(); perp_loc = N_loc.cross(D_loc).normalized(); Rl = Matrix((D_loc, perp_loc, N_loc)).transposed(); up_w = lado.cross(d).normalized()
    R = (Matrix((d, up_w, lado)).transposed() @ Rl.inverted()).to_4x4(); M = R @ Matrix.Diagonal((ESC, ESC, ESC, 1))
    return Matrix.Translation(punta_w - (M @ punta_loc.to_4d()).to_3d()) @ M
def objeto(nombre, desde):
    o = bpy.data.objects.get(nombre)
    if o is None: o = desde.copy(); o.name = nombre; sc.collection.objects.link(o)
    for c in list(o.constraints): o.constraints.remove(c)
    if o.animation_data: o.animation_data_clear()
    o.parent = None; o.rotation_mode = 'QUATERNION'; return o
def hueso(n): return ARM.matrix_world @ ARM.pose.bones[n].matrix
CLAVES = {}
def clave(o, f, M, vis=True):
    CLAVES.setdefault(o.name, {})[f] = (M.copy(), vis)
fl_frente = objeto("flecha_alfred", fl0)
if "p9_flecha_frente_M" not in sc: sc["p9_flecha_frente_M"] = [v for r_ in fl_frente.matrix_world for v in r_]     # posicion ORIGINAL de la flecha de la frente (la primera vez); al repetir, su matrix_world es la del ultimo frame horneado
MF = Matrix([list(sc["p9_flecha_frente_M"][i * 4:i * 4 + 4]) for i in range(4)])
aplicar_pose(P0_ORIG, R0); OFF_FRENTE = hueso("Neck_alfred").inverted() @ MF                   # la flecha de la frente se fijo con la cabeza en la pose ORIGINAL de la base
FLECHAS = [("flecha_mano_der", H1, "R", "Rightelbow_alfred"), ("flecha_mano_izq", H2, "L", "Leftelbow_alfred"), ("flecha_entrepierna", H3, None, "Hips_alfred")]
VUELO = 12; info_fl = []
for nombre, H, lado, bn in FLECHAS:
    o = objeto(nombre, fl0); aplicar_pose(*TL[H])
    if lado:                                                                                # la flecha ATRAVIESA el centro de la mano (no la yema de los dedos): bien visible clavada
        dg = bpy.context.evaluated_depsgraph_get(); sh_ = ARM.matrix_world @ ARM.pose.bones[LADO[lado][0]].head
        vv = verts(LADO[lado][2]); dmax = max((v - sh_).length for v in vv); mano = [v for v in vv if (v - sh_).length > dmax - 0.20]
        tgt = sum(mano, Vector()) / len(mano); hondo = 0.16
    else: tgt = ENTRE.copy(); hondo = 0.06
    d = (tgt - S).normalized()
    if lado:                                                                                # la mano APUNTA al esqueleto: una flecha que llega por esa linea queda escondida dentro del brazo -> se clava ATRAVESANDO la mano de lado
        eje = (tgt - sh_).normalized(); dc = d - eje * d.dot(eje)
        if dc.length < 0.2: dc = (DER if lado == "R" else -DER) - eje * (DER if lado == "R" else -DER).dot(eje)
        d = (dc.normalized() * 0.85 + eje * 0.15).normalized(); hondo = 0.10
        if lado == "R":                                                                     # derecha: al colgar el brazo la cola quedaba en la cara interior (oculta); la cola SALE por delante y hacia afuera
            Mi = hueso(bn).to_3x3(); aplicar_pose(*TL[H + 28]); Mh = hueso(bn).to_3x3()             # se decide con el brazo YA COLGANDO (como se ve) y se lleva a la pose del impacto
            sh_h = ARM.matrix_world @ ARM.pose.bones[LADO[lado][0]].head; vh = verts(LADO[lado][2]); dmh = max((v - sh_h).length for v in vh)
            eje_h = (sum((v for v in vh if (v - sh_h).length > dmh - 0.20), Vector()) / len([v for v in vh if (v - sh_h).length > dmh - 0.20]) - sh_h).normalized()
            cola = FWD * 0.65 + DER * 0.6 + Vector((0, 0, 0.25)); cola = cola - eje_h * cola.dot(eje_h)
            d = (Mi @ (Mh.inverted() @ (-cola.normalized()))).normalized(); aplicar_pose(*TL[H])
    p_imp = tgt + d * hondo; M_imp = M_flecha(p_imp, d); OFFb = hueso(bn).inverted() @ M_imp
    p0 = S + d * 0.3
    for k in range(VUELO + 1):
        u = k / VUELO; p = p0.lerp(p_imp, u); p.z += 0.4 * 4 * u * (1 - u); clave(o, H - VUELO + k, M_flecha(p, d))
    clave(o, H - VUELO - 1, M_flecha(p0, d), False)
    info_fl.append((nombre, H, OFFb, bn, o))
    EV += [(H - VUELO, 'entity.skeleton.shoot', 'objetos', 0.5, 'alfred_flecha_disparo'), (H, 'entity.arrow.hit', 'golpes', 1.0, 'alfred_flecha_impacto'), (H + 1, 'entity.player.hurt', 'voces', 0.85, 'alfred_quejido_flecha')]
# ---- f410: una flecha se clava en la PIEDRA a la derecha de Jerry (+y), a la altura de su cabeza (Jerry reacciona en jerry_busca_materiales_parte9.py) ----
H_JERRY = 410; JR = bpy.data.objects["Dog_001_rig"]; cab_j = JR.matrix_world @ JR.pose.bones["scull"].head
dgj = bpy.context.evaluated_depsgraph_get(); pj = cab_j.copy()
for _ in range(10):
    ok_, hit_, nor_, i_, ob_, m_ = sc.ray_cast(dgj, pj, Vector((0, 1, 0)), distance=3)
    if ok_ and (ob_.original.name.endswith("_jerry") or ob_.original.name.startswith(("flecha", "sombrero")) or (ob_.original.parent and ob_.original.parent.name in ("jerry", "Dog_001_rig"))): pj = hit_ + Vector((0, 0.01, 0)); continue
    break
hit_j = hit_ if ok_ else cab_j + Vector((0, 0.6, 0))
d_j = (hit_j - S).normalized(); p_imp_j = hit_j + d_j * 0.10                                 # viene del ESQUELETO, igual que las otras flechas
o_j = objeto("flecha_piedra_jerry", fl0); p0_j = S + d_j * 0.3
for k in range(VUELO + 1):
    u = k / VUELO; pp = p0_j.lerp(p_imp_j, u); pp.z += 0.4 * 4 * u * (1 - u); clave(o_j, H_JERRY - VUELO + k, M_flecha(pp, d_j))
clave(o_j, H_JERRY - VUELO - 1, M_flecha(p0_j, d_j), False); clave(o_j, 700, M_flecha(p_imp_j, d_j))
EV += [(H_JERRY - VUELO, 'entity.skeleton.shoot', 'objetos', 0.4, 'jerry_flecha_disparo'), (H_JERRY, 'entity.arrow.hit', 'golpes', 1.0, 'jerry_flecha_piedra')]
sc["p9_flecha_jerry_punto"] = list(hit_j)
sc["p9_disparos"] = [H1 - VUELO, H2 - VUELO, H3 - VUELO, H_JERRY - VUELO]                # el esqueleto SUELTA cada flecha en estos frames
pan = bpy.data.objects.get("pan_alfred")
if pan is None:
    with bpy.data.libraries.load(r"C:\Users\user\Desktop\Alfred_Animacion\objetos\vanilla\bread\bread.blend", link=False) as (s_, d_): d_.objects = ["bread"]
    pan = d_.objects[0]; pan.name = "pan_alfred"; sc.collection.objects.link(pan)
pan = objeto("pan_alfred", pan)
aplicar_pose(*TL[T_AGARRA]); M_pan = Matrix.Translation(punta("R")) @ Matrix.Diagonal((0.4, 0.4, 0.4, 1)); OFF_PAN = hueso("Rightelbow_alfred").inverted() @ M_pan
for f in sorted(TL):
    aplicar_pose(*TL[f])
    clave(fl_frente, f, hueso("Neck_alfred") @ OFF_FRENTE)
    for nombre, H, OFFb, bn, o in info_fl:
        if f >= H: clave(o, f, hueso(bn) @ OFFb)
    if T_AGARRA <= f <= T_PAN_FIN + 1:
        esc = 1.0 - sum(1 for m_ in MORDISCOS if f > m_) / 3.0
        clave(pan, f, hueso("Rightelbow_alfred") @ OFF_PAN @ Matrix.Diagonal((max(esc, 0.001),) * 3 + (1,)), f <= T_PAN_FIN)
clave(pan, T_AGARRA - 1, M_pan, False)
for nombre, ks in CLAVES.items():
    o = bpy.data.objects[nombre]; a = bpy.data.actions.new("p9_" + nombre); slot = a.slots.new(id_type='OBJECT', name=o.name); cb = a.layers.new("Capa").strips.new(type='KEYFRAME').channelbag(slot, ensure=True)
    fs = sorted(ks); can = {}
    for f in fs:
        l, q, s_ = ks[f][0].decompose()
        for i in range(3): can.setdefault(("location", i), []).append((f, l[i])); can.setdefault(("scale", i), []).append((f, s_[i]))
        for i in range(4): can.setdefault(("rotation_quaternion", i), []).append((f, q[i]))
    vis = [(1, 0.0 if nombre == "flecha_alfred" else 1.0)] + [(f, 0.0 if ks[f][1] else 1.0) for f in fs]
    for (dp, i), pts in can.items():
        fc = cb.fcurves.new(dp, index=i); fc.keyframe_points.add(len(pts)); fc.keyframe_points.foreach_set("co", [v for p_ in pts for v in p_])
        for k_ in fc.keyframe_points: k_.interpolation = 'LINEAR'
        fc.update()
    for dp in ("hide_viewport", "hide_render"):
        pts = sorted(dict(vis).items()); fc = cb.fcurves.new(dp, index=0); fc.keyframe_points.add(len(pts)); fc.keyframe_points.foreach_set("co", [v for p_ in pts for v in p_])
        for k_ in fc.keyframe_points: k_.interpolation = 'CONSTANT'
        fc.update()
    o.animation_data_create(); o.animation_data.action = a; o.animation_data.action_slot = slot

# ---------------- acciones de Alfred ----------------
def accion(obj, nombre, canales):
    for a_ in [a_ for a_ in bpy.data.actions if a_.name == nombre]: bpy.data.actions.remove(a_)
    a = bpy.data.actions.new(nombre); slot = a.slots.new(id_type='OBJECT', name=obj.name); cb = a.layers.new("Capa").strips.new(type='KEYFRAME').channelbag(slot, ensure=True)
    for (dp, i), pts in canales.items():
        fc = cb.fcurves.new(dp, index=i); fc.keyframe_points.add(len(pts)); fc.keyframe_points.foreach_set("co", [v for p_ in pts for v in p_])
        for k_ in fc.keyframe_points: k_.interpolation = 'LINEAR'
        fc.update()
    obj.animation_data_create(); obj.animation_data.action = a; obj.animation_data.action_slot = slot
fs = sorted(TL); prev = {n: Euler(P0[n]) for n in B}; canA = {}
for f in fs:
    for n in B:
        e = Euler(TL[f][0][n]); e.make_compatible(prev[n]); prev[n] = e
        for i in range(3): canA.setdefault(('pose.bones["%s"].rotation_euler' % n, i), []).append((f, e[i]))
s1z = 1.0; canA[('pose.bones["Spine1_alfred"].scale', 2)] = [(f, s1z + ESC_PECHO[f]) for f in fs]
for n_ in ("RightUpArm_alfred", "LeftUpArm_alfred"):                                         # escala de los hombros FIJA a 1 (venian valores sueltos deformados que hinchaban la malla de los brazos)
    for i in range(3): canA[('pose.bones["%s"].scale' % n_, i)] = [(fs[0], 1.0)]
LOC_HOMBRO = {"LeftUpArm_alfred": (-0.0071, 0.0968, -0.0861), "RightUpArm_alfred": (0.0071, 0.0968, -0.0861)}   # hombros en su sitio (el derecho venia desplazado ~10 cm: el brazo se separaba del cuerpo)
for n_, v_ in LOC_HOMBRO.items():
    for i in range(3): canA[('pose.bones["%s"].location' % n_, i)] = [(fs[0], v_[i])]
canR = {("location", i): [(f, TL[f][1][i]) for f in fs] for i in range(3)}; canR.update({("rotation_euler", i): [(f, TL[f][1][3 + i]) for f in fs] for i in range(3)})
accion(ARM, "p9_alfred_armature", canA); accion(ROOT, "p9_alfred_root", canR)
sc.frame_end = max(sc.frame_end, FIN)
for o_ in (bpy.data.objects["ojo_izquierdo_alfred"], bpy.data.objects["ojo_derecho_alfred"]):          # OJOS ENTRECERRADOS desde que cae (parpadeos_parte9.py no pone parpadeos desde p9_f_suelo - 12)
    ck = o_.data.shape_keys.key_blocks["Closed"]
    for owner, filt in ((o_.data.shape_keys, lambda fc: "Closed" in fc.data_path), (o_, lambda fc: fc.data_path.startswith("hide"))):
        if owner.animation_data and owner.animation_data.action:
            for fc in [c for l in owner.animation_data.action.layers for st in l.strips for cb in st.channelbags for c in cb.fcurves if filt(c)]:
                for kk in range(len(fc.keyframe_points) - 1, -1, -1):
                    if fc.keyframe_points[kk].co.x >= F_SUELO - 3: fc.keyframe_points.remove(fc.keyframe_points[kk])
                fc.update()
    ck.value = 0.0; ck.keyframe_insert("value", frame=F_SUELO - 2); ck.value = 0.55; ck.keyframe_insert("value", frame=F_SUELO + 4)
    for (f0, a, huesos, sg) in ESP:                                                         # en cada espasmo aprieta un poco los ojos
        ck.value = 0.55; ck.keyframe_insert("value", frame=f0); ck.value = 0.55 + 0.3 * a; ck.keyframe_insert("value", frame=f0 + 2); ck.value = 0.55; ck.keyframe_insert("value", frame=f0 + 6)
    o_.hide_viewport = False; o_.hide_render = False
    for dp in ("hide_viewport", "hide_render"): o_.keyframe_insert(dp, frame=F_SUELO - 2)

# ---------------- sonidos ----------------
m = sys.modules.get("alfred_sonidos")
if m is None:
    sp = importlib.util.spec_from_file_location("alfred_sonidos", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py"); m = importlib.util.module_from_spec(sp); sys.modules["alfred_sonidos"] = m; sp.loader.exec_module(m)
if not hasattr(sc, 'mcsnd'):
    try: m.register()
    except Exception as e: print('registro alfred_sonidos:', e)
if not sc.mcsnd.items: bpy.ops.mcsnd.indexar()
p_ = sc.mcsnd; ed = sc.sequence_editor_create(); S_ = m._strips(ed); rng = random.Random(9)
for t in [t for t in S_ if t.name.startswith('SND_')]: S_.remove(t)
import os, aud, numpy as np
def sonido_grave(snd_, factor=0.7):
    src_ = bpy.path.abspath(snd_.filepath); base_ = os.path.splitext(os.path.basename(src_))[0]
    if base_.endswith("_grave70"): return snd_
    d_ = r"C:\Users\user\Desktop\Alfred_Animacion\audios\sonidos_graves"; os.makedirs(d_, exist_ok=True); out_ = os.path.join(d_, base_ + "_grave70.wav")
    if not os.path.exists(out_):
        a_ = aud.Sound(src_); rate_ = int(a_.specs[0]); x_ = a_.data().astype(np.float32); n_ = x_.shape[0]; xs_ = np.linspace(0, n_ - 1, int(n_ / factor))
        y_ = np.stack([np.interp(xs_, np.arange(n_), x_[:, c]) for c in range(x_.shape[1])], axis=1).astype(np.float32)
        aud.Sound.buffer(y_, rate_).write(out_, rate_, aud.CHANNELS_MONO if y_.shape[1] == 1 else aud.CHANNELS_STEREO, aud.FORMAT_S16, aud.CONTAINER_WAV, aud.CODEC_PCM)
    return bpy.data.sounds.load(out_, check_existing=True)
for f, ev, g, v, et in EV:
    r = m.rutas_de(p_, ev)
    if r:
        m.colocar(bpy.context, p_, r, int(f), g, et, v, 0, rng, False)
        if et == 'alfred_flecha_impacto':                                                    # mas GRAVE: las tiras no tienen tono -> version del .ogg estirada 1/0.7 (tono al 70 por ciento) en audios/sonidos_graves
            t_ = next((t for t in m._strips(ed) if t.name.startswith('SND_alfred_flecha_impacto_%d' % int(f))), None)
            pass                                                                           # (impacto: el mismo sonido de la parte 8, `entity.arrow.hit_player`, sin cambiar el tono)
sc.frame_set(1)
print("PARTE 9: agarra el pan f%d, mordiscos %s, pan acaba f%d; flecha mano der f%d, mano izq f%d, entrepierna f%d; cae f%d-%d a %s; fin f%d; %d sonidos" % (
    T_AGARRA, MORDISCOS, T_PAN_FIN, H1, H2, H3, F_CAE, F_SUELO, tuple(CAIDA), FIN, len(EV)))
