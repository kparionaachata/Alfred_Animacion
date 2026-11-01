# -*- coding: utf-8 -*-
"""Parte 7: Jerry REGRESA corriendo por la misma ruta (`recorridos/jerry_parte7.json`, al reves: del punto 20 al punto 10) y llega en f310 a (-107.5, -86.5, 15.0) mirando a Alfred (que se soba el tobillo);
en f374 se da cuenta del creeper y se tira BOCA ABAJO tapandose la cabeza con las patas delanteras (pose `poses/boca abajo con las manos tapandose la cabeza.json`), con ELASTIC IN-OUT; se queda asi hasta el final.
- Requiere `jerry_recorrido_parte7.py` (la ida; Jerry en reposo en el punto 20 desde f151). Reutiliza de ese script el ciclo de correr (`pose_run`) y el salto (`pose_jump`, `jump_position`) sin ejecutar su construccion.
- Regreso: gira 180 grados en el sitio (6 f, rz 0 -> 180) y corre (7.2 f por bloque, como la ida) por la ruta invertida; los tramos que SUBEN (20->19, 19->18, 15->14) se saltan con `saltar_subir` (15 f) y el que baja
  (14->13) se corre con el z interpolado. Llega al punto 10 en T_LLEGA (304) y frena en 6 f (pose -> reposo) girando de rz 180 a la direccion de Alfred (el cuerpo mira a Alfred), en reposo hasta f373.
- f374-381: reaccion al creeper: de la pose de reposo a la pose del JSON (rotaciones por hueso y la bajada del hueso raiz `spine_6`) con ELASTIC IN-OUT (7 f, la funcion `ela` de los sustos), el z del root se sube lo justo para que ninguna
  malla atraviese el suelo; mantiene la pose hasta el final (sin mas claves).
Sin parpadeos, sonidos ni expresiones de la cara (no pedidos). Se ejecuta dentro de Blender: exec(open(RUTA, encoding='utf-8').read()). Idempotente (borra sus claves >= f152). Variables opcionales: T_LLEGA, T_REACC."""
import bpy, json, math
from mathutils import Vector, Euler, Quaternion

DOCS = 'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/jerry/refinar/'
T_LLEGA = int(globals().get('T_LLEGA', 304)); T_REACC = int(globals().get('T_REACC', 374)); DUR_REACC = 7; GIRO = 6
g = {'__name__': 'x'}                                                           # solo las definiciones de la ida (antes de "construccion")
exec(open(DOCS + 'docs/jerry_recorrido_parte7.py', encoding='utf-8').read().split('# ---------------- construccion')[0], g)
pose_run, pose_jump, jump_phase, jump_position = g['pose_run'], g['pose_jump'], g['jump_phase'], g['jump_position']
FPB, JUMP_FRAMES, TIMING, FRENADO, BOB, CL, nrm, ss, mul = g['FPB'], g['JUMP_FRAMES'], g['TIMING'], g['FRENADO'], g['BOB'], g['CL'], g['nrm'], g['ss'], g['mul']
root, arm, sc = g['root'], g['arm'], g['sc']
P = g['pts'][::-1][:11]; assert tuple(P[-1]) == (-107.5, -86.5, 15.0), P[-1]    # puntos 20 -> 10
NB = ['shoulder.L', 'shoulder.R', 'thigh.L', 'thigh.R', 'shin.L', 'shin.R', 'foot.L', 'foot.R', 'toe.L', 'toe.R', 'front_shoulder.L', 'front_shoulder.R', 'front_thigh.L', 'front_thigh.R',
      'front_shin.L', 'front_shin.R', 'front_foot.L', 'front_foot.R', 'front_toe.L', 'front_toe.R'] + ['spine_%d' % i for i in range(1, 8)] + ['tail_%d' % i for i in range(1, 4)] + \
     ['scull', 'scull_1', 'neck', 'jaw_top', 'ear.L', 'ear.R', 'sombrero']
NB = [n for n in NB if n in arm.pose.bones]
ZERO = (0.0, 0.0, 0.0)
def ela(t):                                                                      # ELASTIC in-out (como creeper_susto_y_huida.py)
    if t <= 0: return 0.0
    if t >= 1: return 1.0
    c5 = (2 * math.pi) / 4.5
    return -(2 ** (20 * t - 10) * math.sin((20 * t - 11.125) * c5)) / 2 if t < 0.5 else (2 ** (-20 * t + 10) * math.sin((20 * t - 11.125) * c5)) / 2 + 1
def qint(q0, q1, u):                                                             # interpolacion por eje-angulo que permite u fuera de [0,1] (el elastico se pasa de 1)
    d = q0.rotation_difference(q1); ax, an = d.to_axis_angle(); return q0 @ Quaternion(ax, an * u) if an > 1e-9 else q0.copy()
def curvas(o): return [fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]

# ---------- pose del JSON y direccion de Alfred ----------
JP = json.load(open(DOCS + 'poses/boca abajo con las manos tapandose la cabeza.json', encoding='utf-8'))['poses'][0]['bones']
TGT = {n: (tuple(JP[n]['local_space']['rotation_euler_rad'][c] for c in 'xyz') if n in JP and JP[n]['rotation_mode'] == 'XYZ' else ZERO) for n in NB}
LOCB = [n for n in JP if n in arm.pose.bones and any(abs(v) > 0.01 for v in JP[n]['local_space']['location'].values())]       # huesos con traslacion en la pose (el raiz baja el cuerpo)
LOCT = {n: tuple(JP[n]['local_space']['location'][c] for c in 'xyz') for n in LOCB}
nuevos = [n for n in JP if n not in NB and (any(abs(v) > 1e-3 for v in JP[n]['local_space']['rotation_euler_rad'].values()) and JP[n]['rotation_mode'] == 'XYZ')]
assert not nuevos, 'huesos de la pose fuera de NB: %s' % nuevos
sc.frame_set(T_LLEGA + FRENADO); bpy.context.view_layer.update()
AL = bpy.data.objects['alfred'].matrix_world.translation.copy()
rx, ry = root.rotation_euler.x, root.rotation_euler.y
RZ_ALFRED = -math.atan2(AL.x - P[-1][0], AL.y - P[-1][1])                       # rz con el que Jerry (que mira a +y en rz 0) mira a Alfred
RZ_ALFRED += 2 * math.pi * round((math.pi - RZ_ALFRED) / (2 * math.pi))          # cerca de 180 (llega mirando a -y: gira por el camino mas corto)

# ---------- tramos: los que suben se saltan, el resto se corre ----------
rises = [i for i in range(len(P) - 1) if P[i + 1][2] - P[i][2] >= 0.99]
def bounds_from(t0):
    b = []; t = t0; acc = 0.0
    for i in range(len(P)):
        b.append(t)
        if i == len(P) - 1: break
        if i in rises: t += JUMP_FRAMES - 1
        else:
            d = math.hypot(P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1]) * FPB; nt = round(acc + d); t += nt - round(acc); acc += d
    return b
S_RUN = T_LLEGA - bounds_from(0)[-1]; bounds = bounds_from(S_RUN)
JUMPS = [(bounds[j], bounds[j] + JUMP_FRAMES - 1, j) for j in rises]

REST = {n: ZERO for n in NB}
T_SIT0 = T_LLEGA + FRENADO; N_SIT = 12; N_MIRA = 4
T_MIRA = int(globals().get('T_MIRA', 374)); T_TIRA = T_MIRA + N_MIRA + 4                                           # f374 ve al creeper (gira 4 f), 4 f quieto mirandolo y se tira en f382
Dg = math.radians
SITD = {'shoulder.R': (30.7941, 17.2106, 12.1341), 'thigh.R': (-37.8749, -0.08667, -0.29331), 'shin.R': (-60.7645, 5.85033, -3.20637), 'toe.R': (32.7165, -3.13541, -3.85954),
        'shoulder.L': (36.6239, -7.29244, 7.40292), 'thigh.L': (-35.5687, 0.050003, 0.028891), 'shin.L': (-66.431, -2.51456, 10.2236), 'toe.L': (13.1202, 3.13541, -0.724126),
        'front_shoulder.R': (0.104614, 4.64061, -13.2978), 'front_thigh.R': (-3.19165, 0.713985, 6.77661), 'front_shin.R': (-20.4907, 0.349145, -0.494996), 'front_foot.R': (41.3328, -5.89264, -5.23815),
        'front_shoulder.L': (1.44402, 9.35442, 1.89138), 'front_thigh.L': (0.89341, -0.37494, -4.55577), 'front_shin.L': (-18.3209, -0.246426, -0.054384),
        'spine_1': (13.2537, 2.15474, 2.55871), 'spine_4': (6.06694, 0, 0), 'spine_5': (-32.2499, 0, 0), 'spine_6': (60.3763, -7.91597, -1.48891),
        'tail_1': (-54.5851, 10.5782, -10.7713), 'tail_2': (-40, 15, -8), 'tail_3': (-25, 12, -5), 'ear.L': (15, 5, 8), 'ear.R': (12, -5, -8), 'scull': (-25, 3, 8), 'jaw_top': (10, 0, 0)}   # SITTING_POSE de recorridos/jerry_sentado_slot53_fuente.py
SIT = {n: tuple(Dg(a) for a in SITD.get(n, (0, 0, 0))) for n in NB}
Z0 = P[-1][2]; PX, PY = P[-1][0], P[-1][1]
def poner(rot, loc, rz, z0=None):                                                 # pone la pose y devuelve (z de contacto con el suelo: la malla mas baja a z = Z0, z minimo)
    for n in NB: arm.pose.bones[n].rotation_euler = rot[n]
    for n in LOCB: arm.pose.bones[n].location = loc.get(n, ZERO)
    root.location = (PX, PY, Z0); root.rotation_euler = (rx, ry, rz); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); zm = 1e9
    for o in arm.children_recursive:
        if o.type == 'MESH':
            ev = o.evaluated_get(dg); mw = ev.matrix_world
            for v in ev.data.vertices: zm = min(zm, (mw @ v.co).z)
    return Z0 + (Z0 - zm)
def yaw_cabeza(rot, rz):                                                           # direccion (rz) a la que mira el hueso scull
    poner(rot, {}, rz); pb = arm.pose.bones['scull']; d = (arm.matrix_world @ pb.tail) - (arm.matrix_world @ pb.head); return -math.atan2(d.x, d.y)
wrap = lambda a: (a + math.pi) % (2 * math.pi) - math.pi
prev = {n: Euler(ZERO, 'XYZ') for n in NB}
def mezcla(A, B, u):                                                               # mezcla por cuaternion (eje-angulo; u puede salirse de [0,1] con el elastico)
    out = {}
    for n in NB:
        qa = Euler(A[n], 'XYZ').to_quaternion(); qb = Euler(B[n], 'XYZ').to_quaternion(); qb = qb if qa.dot(qb) >= 0 else -qb
        e = qint(qa, qb, u).to_euler('XYZ', prev[n]); prev[n] = e; out[n] = tuple(e)
    return out
# direcciones: sentado la CABEZA mira a Alfred (el cuerpo gira lo necesario); al ver al creeper la cabeza (columna alta + cuello + craneo) y la mitad del giro del cuerpo lo miran a el
B_A = RZ_ALFRED
RZ_SIT = B_A - yaw_cabeza(SIT, 0.0); RZ_SIT += 2 * math.pi * round((RZ_ALFRED - RZ_SIT) / (2 * math.pi))
sc.frame_set(T_TIRA - 1); bpy.context.view_layer.update(); CRP = bpy.data.objects['creeper_1'].matrix_world.translation.copy()
B_C = -math.atan2(CRP.x - PX, CRP.y - PY); DELTA = wrap(B_C - B_A); RZ_LOOK = RZ_SIT + 0.5 * DELTA
MIRA = lambda k: {n: ((SIT[n][0], SIT[n][1], SIT[n][2] + k * Dg({'scull': -30.0, 'spine_1': -16.0, 'spine_2': -16.0}[n])) if n in ('scull', 'spine_1', 'spine_2') else SIT[n]) for n in NB}
lo, hi = -1.5, 2.5
for _ in range(40):                                                                # k tal que la cabeza mire exactamente al creeper
    mid = (lo + hi) / 2; e = wrap(yaw_cabeza(MIRA(mid), RZ_LOOK) - B_C)
    if e > 0: hi = mid                                                             # (k > 0 = giro negativo de Z de estos huesos = sube el yaw)
    else: lo = mid
K_LOOK = (lo + hi) / 2; LOOK = MIRA(K_LOOK)
ERR_LOOK = wrap(yaw_cabeza(LOOK, RZ_LOOK) - B_C)
SEQ = []                                                                           # (f, pose, ubicacion de huesos, rz, z): TODO se calcula antes de insertar claves (con claves nuevas el update() reaplica la animacion)
RZ_LIE = math.radians(float(globals().get('RZ_LIE', 0.0)))                          # direccion del cuerpo tumbado: rz 0 (mirando a +y, de espaldas al creeper) deja >= 0.27 m a Alfred y al creeper (con otras direcciones el cuerpo toca al creeper)
def calc_estado(f, rot, loc, rz): SEQ.append((f, rot, loc, rz, poner(rot, loc, rz)))
for f in range(T_SIT0 + 1, T_SIT0 + N_SIT + 1):                                    # 1) se sienta mirando a Alfred (12 f, suave) y espera
    u = ss((f - T_SIT0) / float(N_SIT)); calc_estado(f, mezcla(REST, SIT, u), {}, RZ_ALFRED + (RZ_SIT - RZ_ALFRED) * u)
calc_estado(T_MIRA - 1, SIT, {}, RZ_SIT)
for f in range(T_MIRA, T_MIRA + N_MIRA + 1):                                       # 2) voltea a ver al creeper (4 f) y se queda mirandolo (4 f)
    u = ss((f - (T_MIRA - 1)) / float(N_MIRA)); calc_estado(f, mezcla(SIT, LOOK, u), {}, RZ_SIT + (RZ_LOOK - RZ_SIT) * u)
calc_estado(T_TIRA - 1, LOOK, {}, RZ_LOOK)
for f in range(T_TIRA, T_TIRA + DUR_REACC + 1):                                    # 3) se asusta y se tira boca abajo tapandose la cabeza (elastic in-out)
    w = ela((f - (T_TIRA - 1)) / float(DUR_REACC)); calc_estado(f, mezcla(LOOK, TGT, w), {n: tuple(LOCT[n][c] * w for c in range(3)) for n in LOCB}, RZ_LOOK + wrap(RZ_LIE - RZ_LOOK) * ss((f - (T_TIRA - 1)) / float(DUR_REACC)))
# 4) f525: cuando Alfred YA esta de pie (termina en f524), Jerry se quita las patas de la cabeza y la levanta (6 f), se sienta mirando al creeper (que esta inconsciente) y se para
T_SALE = int(globals().get('T_SALE', 525)); N_MANOS = 6; N_SIT2 = 12; H_SIT2 = 14; N_PARA = 10
sc.frame_set(T_SALE + 20); bpy.context.view_layer.update(); CR2 = bpy.data.objects['creeper_1'].matrix_world.translation.copy()      # el creeper tumbado boca arriba
B_C2 = -math.atan2(CR2.x - PX, CR2.y - PY)
RZ_SIT2 = B_C2 - yaw_cabeza(SIT, 0.0); RZ_SIT2 += 2 * math.pi * round((RZ_LIE - RZ_SIT2) / (2 * math.pi))                  # sentado, la CABEZA mira al creeper
B_C2W = B_C2 + 2 * math.pi * round((RZ_SIT2 - B_C2) / (2 * math.pi))                                                        # de pie, el cuerpo entero lo mira
MID = {n: (SIT[n] if (n.startswith('front_') or n in ('scull', 'scull_1')) else TGT[n]) for n in NB}                         # patas delanteras fuera de la cabeza y cabeza arriba, el cuerpo sigue tumbado
LOCL = {n: LOCT[n] for n in LOCB}
calc_estado(T_SALE - 1, TGT, LOCL, RZ_LIE)
for f in range(T_SALE, T_SALE + N_MANOS + 1):
    u = ss((f - (T_SALE - 1)) / float(N_MANOS)); calc_estado(f, mezcla(TGT, MID, u), LOCL, RZ_LIE)
T_S2 = T_SALE + N_MANOS
for f in range(T_S2 + 1, T_S2 + N_SIT2 + 1):                                       # se sienta mirando al creeper
    u = ss((f - T_S2) / float(N_SIT2)); calc_estado(f, mezcla(MID, SIT, u), {n: tuple(LOCT[n][c] * (1 - u) for c in range(3)) for n in LOCB}, RZ_LIE + (RZ_SIT2 - RZ_LIE) * u)
T_S3 = T_S2 + N_SIT2 + H_SIT2; calc_estado(T_S3, SIT, {}, RZ_SIT2)
for f in range(T_S3 + 1, T_S3 + N_PARA + 1):                                       # se para (pose de reposo) mirando al creeper
    u = ss((f - T_S3) / float(N_PARA)); calc_estado(f, mezcla(SIT, REST, u), {}, RZ_SIT2 + (B_C2W - RZ_SIT2) * u)
T_FIN_J = T_S3 + N_PARA

# ======================= desde aqui se insertan claves =======================
for a in [fc for o in (root, arm) for fc in curvas(o)]:                          # idempotente: borra las claves de este script (>= 152)
    for i in range(len(a.keyframe_points) - 1, -1, -1):
        if a.keyframe_points[i].co.x >= 152: a.keyframe_points.remove(a.keyframe_points[i])
def key_root(f, p, rz):
    root.location = p; root.rotation_euler = (rx, ry, rz); root.keyframe_insert('location', frame=f); root.keyframe_insert('rotation_euler', frame=f)
def key_pose(f, k):
    for n in NB:
        b = arm.pose.bones[n]; b.rotation_euler = k.get(n, ZERO); b.keyframe_insert('rotation_euler', frame=f, group=n)

# giro en el sitio (180 grados) y carrera
key_root(S_RUN - GIRO - 1, tuple(P[0]), 0.0); key_pose(S_RUN - GIRO - 1, REST)
for f in range(S_RUN - GIRO, S_RUN): key_root(f, tuple(P[0]), math.pi * ss((f - (S_RUN - GIRO - 1)) / float(GIRO))); key_pose(f, REST)
for f in range(S_RUN, T_LLEGA + 1):
    pf = f - S_RUN + 1; salto = next((j for j in JUMPS if j[0] <= f <= j[1]), None)
    if salto:
        ph = jump_phase(f - salto[0], TIMING); key_root(f, jump_position(P[salto[2]], P[salto[2] + 1], ph), math.pi); key_pose(f, pose_jump(ph)); continue
    i = next((j for j in range(len(P) - 1) if bounds[j] <= f < bounds[j + 1]), len(P) - 2)
    a, b = bounds[i], bounds[i + 1]; u = (f - a) / max(1, b - a); p = [P[i][c] + (P[i + 1][c] - P[i][c]) * u for c in range(3)]
    n = nrm(pf); bob = BOB * (0.5 - 0.5 * math.cos(2 * math.pi * n / CL * 2)); key_root(f, (p[0], p[1], p[2] + bob), math.pi)
    wr = 1.0
    for T0j, T1j, _ in JUMPS:
        if T1j < f <= T1j + 5: wr = min(wr, ss((f - T1j) / 5.0))                # tras el salto entra al correr
        if T0j - 3 <= f < T0j: wr = min(wr, 1.0 - ss((f - (T0j - 3) + 1) / 3.0))   # antes del salto sale del correr
    pr = pose_run(pf); k = {nn: mul(pr.get(nn, ZERO), wr) for nn in NB}
    if f <= S_RUN + 5: w = ss((f - (S_RUN - 1)) / 6.0); k = {nn: mul(k[nn], w) for nn in NB}
    key_pose(f, k)
# frenado y giro hacia Alfred
last = {n: tuple(arm.pose.bones[n].rotation_euler) for n in NB}
for j in range(1, FRENADO + 1):
    f = T_LLEGA + j; w = ss(j / float(FRENADO)); key_root(f, tuple(P[-1]), math.pi + (RZ_ALFRED - math.pi) * w); key_pose(f, {n: mul(last[n], 1.0 - w) for n in NB})
for n in LOCB:
    b = arm.pose.bones[n]; b.location = ZERO; b.keyframe_insert('location', frame=T_SIT0, group=n)
for (f, rot, loc, rz, z) in SEQ:                                                  # claves de sentarse / mirar / tirarse (la pose, el z de contacto y la ubicacion del hueso raiz ya calculados)
    key_root(f, (PX, PY, z), rz); key_pose(f, rot)
    for n in LOCB: arm.pose.bones[n].location = loc.get(n, ZERO); arm.pose.bones[n].keyframe_insert('location', frame=f, group=n)
for ob in (root, arm):
    for fc in curvas(ob):
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
for a in [a for a in bpy.data.actions if a.users == 0 and not a.use_fake_user]: bpy.data.actions.remove(a)
sc.frame_end = max(sc.frame_end, T_FIN_J)
sc.frame_set(T_LLEGA)
print("Jerry regresa: gira f%d-%d, corre f%d-%d (saltos %s), llega al punto 10 en f%d, frena hasta f%d; se sienta f%d-%d mirando a Alfred (rz cuerpo %.1f, cabeza hacia %.1f), ve al creeper f%d-%d (cabeza hacia %.1f, error %.2f grados, rz cuerpo %.1f), se tira boca abajo f%d-%d (elastico, cuerpo hacia rz %.0f) y se queda asi hasta f%d; en f%d se quita las patas, se sienta mirando al creeper (cabeza hacia %.1f) f%d-%d y se para f%d-%d (cuerpo hacia %.1f)" % (
    S_RUN - GIRO, S_RUN - 1, S_RUN, T_LLEGA, [(a, b) for a, b, _ in JUMPS], T_LLEGA, T_SIT0, T_SIT0 + 1, T_SIT0 + N_SIT, math.degrees(RZ_SIT), math.degrees(B_A), T_MIRA, T_MIRA + N_MIRA, math.degrees(B_C), math.degrees(ERR_LOOK), math.degrees(RZ_LOOK), T_TIRA, T_TIRA + DUR_REACC, math.degrees(RZ_LIE), T_SALE - 1, T_SALE, math.degrees(B_C2), T_S2 + 1, T_S2 + N_SIT2, T_S3 + 1, T_FIN_J, math.degrees(B_C2W)))
