# -*- coding: utf-8 -*-
"""Parte 7: el creeper (tumbado) da una convulsion y empieza a brillar (f668); Jerry se asusta y SALE CORRIENDO por `jerry_2.json` (de (-107.5, -88.5) a (-107.5, -80.5), hacia +y, saltando el bloque del punto 7).
- f671-678 SUSTO: da un brinco en el sitio (la pose del salto `saltar_subir`, con ELASTIC IN-OUT en la entrada, z +0.20 m) y gira hacia el norte (rz 0).
- f679-: CORRE (el ciclo CORRER de `jerry_recorrido_parte7.py`: 12 f por ciclo, 7.2 f por bloque): la pose del brinco se funde al ciclo y la velocidad sube de 0 a la normal en 5 f; va primero al punto 1 y sigue la ruta; el tramo que SUBE (punto 6 -> 7, z 15 -> 16) lo salta con `saltar_subir` (15 f) y el que baja lo corre con el z interpolado.
- Al llegar al ultimo punto frena en 6 f (pose a reposo) y se queda asi.
Parte de la pose de f670 y borra sus claves >= f671. Reutiliza de `jerry_recorrido_parte7.py` solo las definiciones (`pose_run`, `pose_jump`, `jump_phase`, `jump_position`). Se ejecuta dentro de Blender: exec(open(RUTA, encoding='utf-8').read()). Variable opcional: T_HUYE_J (671). Sin sonidos (no pedidos)."""
import bpy, json, math
from mathutils import Vector

DOCS = 'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/jerry/refinar/'
T_R = int(globals().get('T_HUYE_J', 671)); RUTA = r'C:/Users/user/Desktop/jerry_2.json'
g = {'__name__': 'x'}
exec(open(DOCS + 'docs/jerry_recorrido_parte7.py', encoding='utf-8').read().split('# ---------------- construccion')[0], g)
pose_run, pose_jump, jump_phase, jump_position = g['pose_run'], g['pose_jump'], g['jump_phase'], g['jump_position']
FPB, JUMP_FRAMES, TIMING, BOB, CL, nrm, ss, mul = g['FPB'], g['JUMP_FRAMES'], g['TIMING'], g['BOB'], g['CL'], g['nrm'], g['ss'], g['mul']
root, arm, sc = g['root'], g['arm'], g['sc']
NB = [n for n in ['shoulder.L', 'shoulder.R', 'thigh.L', 'thigh.R', 'shin.L', 'shin.R', 'foot.L', 'foot.R', 'toe.L', 'toe.R', 'front_shoulder.L', 'front_shoulder.R', 'front_thigh.L', 'front_thigh.R',
      'front_shin.L', 'front_shin.R', 'front_foot.L', 'front_foot.R', 'front_toe.L', 'front_toe.R'] + ['spine_%d' % i for i in range(1, 8)] + ['tail_%d' % i for i in range(1, 4)] +
      ['scull', 'scull_1', 'neck', 'jaw_top', 'ear.L', 'ear.R', 'sombrero'] if n in arm.pose.bones]
ZERO = (0.0, 0.0, 0.0)
def ela(t):                                                                      # ELASTIC in-out (como creeper_susto_y_huida.py)
    if t <= 0: return 0.0
    if t >= 1: return 1.0
    c5 = (2 * math.pi) / 4.5
    return -(2 ** (20 * t - 10) * math.sin((20 * t - 11.125) * c5)) / 2 if t < 0.5 else (2 ** (-20 * t + 10) * math.sin((20 * t - 11.125) * c5)) / 2 + 1
def curvas(o): return [fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]

# ---------- pose de partida (antes de tocar las claves) y ruta ----------
sc.frame_set(T_R - 1); bpy.context.view_layer.update()
BASE = {n: tuple(arm.pose.bones[n].rotation_euler) for n in NB}; P0 = Vector(root.location); RZ0 = root.rotation_euler.z; rx, ry = root.rotation_euler.x, root.rotation_euler.y
RUTA_PTS = [Vector((k['coordinates']['x'], k['coordinates']['y'], k['coordinates']['z'])) for k in json.load(open(RUTA))['key_points']]
P = [Vector((P0.x, P0.y, P0.z))] + RUTA_PTS                                    # primero al punto 1, luego la ruta del json
rises = [i for i in range(len(P) - 1) if P[i + 1][2] - P[i][2] >= 0.99]
def rumbo_seg(i): v = P[min(i, len(P) - 2) + 1] - P[min(i, len(P) - 2)]; return -math.atan2(v.x, v.y)
RZ_N = rumbo_seg(len(P) - 2); RZ_N += 2 * math.pi * round((RZ0 - RZ_N) / (2 * math.pi))                      # hacia donde corre (norte: rz ~0)
N_H = 8; T_RUN0 = T_R + N_H; RAMP = 5
def bounds_from(t0):
    b = []; t = t0; acc = 0.0
    for i in range(len(P)):
        b.append(t)
        if i == len(P) - 1: break
        if i in rises: t += JUMP_FRAMES - 1
        else:
            d = math.hypot(P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1]) * FPB; nt = round(acc + d); t += nt - round(acc); acc += d
    return b
bounds = bounds_from(T_RUN0); E = bounds[-1]; JUMPS = [(bounds[j], bounds[j] + JUMP_FRAMES - 1, j) for j in rises]
# ---------- claves ----------
for fc in curvas(root) + curvas(arm):
    for i in range(len(fc.keyframe_points) - 1, -1, -1):
        if fc.keyframe_points[i].co.x >= T_R: fc.keyframe_points.remove(fc.keyframe_points[i])
def key_root(f, p, rz):
    root.location = p; root.rotation_euler = (rx, ry, rz); root.keyframe_insert('location', frame=f); root.keyframe_insert('rotation_euler', frame=f)
def key_pose(f, k):
    for n in NB:
        b = arm.pose.bones[n]; b.rotation_euler = k.get(n, ZERO); b.keyframe_insert('rotation_euler', frame=f, group=n)
key_root(T_R - 1, tuple(P0), RZ0); key_pose(T_R - 1, BASE)
# 1) susto: brinco en el sitio con la pose del salto, girando hacia el norte
for k in range(1, N_H + 1):
    u = k / float(N_H); jp = pose_jump(0.8 * u); wj = ela(min(1.0, k / 4.0))
    vals = {n: tuple(BASE[n][c] * (1 - wj) + jp.get(n, ZERO)[c] * wj for c in range(3)) for n in NB}
    key_root(T_R + k - 1, (P0.x, P0.y, P0.z + 0.20 * math.sin(math.pi * u)), RZ0 + (RZ_N - RZ0) * ss((k - 1) / 7.0)); key_pose(T_R + k - 1, vals)
HOP_END = {n: tuple(vals[n]) for n in NB}
# 2) corre la ruta (los tramos que suben se saltan)
prev_rz = RZ_N; last = HOP_END
for f in range(T_RUN0, E + 1):
    k = f - T_RUN0; wr = ss((k + 1) / float(RAMP)); pf = k + 1
    salto = next((j for j in JUMPS if j[0] <= f <= j[1]), None)
    if salto:
        ph = jump_phase(f - salto[0], TIMING); p = jump_position(P[salto[2]], P[salto[2] + 1], ph); pj = pose_jump(ph); vals = {n: tuple(pj.get(n, ZERO)) for n in NB}
        key_root(f, tuple(p), prev_rz); key_pose(f, vals); last = vals; continue
    i = next((j for j in range(len(P) - 1) if bounds[j] <= f < bounds[j + 1]), len(P) - 2)
    a, b = bounds[i], bounds[i + 1]; u = (f - a) / max(1, b - a); p = [P[i][c] + (P[i + 1][c] - P[i][c]) * u for c in range(3)]
    tgt = rumbo_seg(i); tgt += 2 * math.pi * round((prev_rz - tgt) / (2 * math.pi)); prev_rz = prev_rz + max(-0.3, min(0.3, tgt - prev_rz))
    n_ = nrm(pf); bob = BOB * (0.5 - 0.5 * math.cos(2 * math.pi * n_ / g['CL'] * 2))
    wrun = 1.0
    for T0j, T1j, _ in JUMPS:
        if T1j < f <= T1j + 5: wrun = min(wrun, ss((f - T1j) / 5.0))              # tras el salto entra al correr
        if T0j - 3 <= f < T0j: wrun = min(wrun, 1.0 - ss((f - (T0j - 3) + 1) / 3.0))   # antes del salto sale del correr
    pr = pose_run(pf); run = {n: mul(pr.get(n, ZERO), wrun) for n in NB}
    vals = {n: tuple(HOP_END[n][c] * (1 - wr) + run[n][c] * wr for c in range(3)) for n in NB} if k < RAMP else run
    key_root(f, (p[0], p[1], p[2] + bob * wr), prev_rz); key_pose(f, vals); last = vals
# 3) frena y se queda
pend = tuple(P[-1])
for j in range(1, 7):
    w = ss(j / 6.0); key_root(E + j, pend, prev_rz); key_pose(E + j, {n: mul(last[n], 1.0 - w) for n in NB})
for fc in curvas(root) + curvas(arm):
    for kp in fc.keyframe_points:
        if kp.co.x >= T_R - 1: kp.interpolation = 'LINEAR'
sc.frame_end = max(sc.frame_end, E + 6)
sc.frame_set(T_R - 1)
print("Jerry huye: brinco f%d-%d, corre f%d-%d por %d puntos (de (%.2f, %.2f) a (%.2f, %.2f)), salta en f%s, llega en f%d y frena hasta f%d" % (T_R, T_R + N_H - 1, T_RUN0, E, len(RUTA_PTS), P0.x, P0.y, RUTA_PTS[-1].x, RUTA_PTS[-1].y, [(a, b) for a, b, _ in JUMPS], E, E + 6))
