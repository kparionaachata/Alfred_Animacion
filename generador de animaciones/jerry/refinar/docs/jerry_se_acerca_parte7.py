# -*- coding: utf-8 -*-
"""Parte 7: despues de pararse (f567) Jerry se acerca al creeper tumbado e inconsciente con CURIOSIDAD y PRECAUCION (huella del creeper: x -108.82..-108.18, y -90.06..-88.05) hasta (-107.45, -88.75), a su lado este.
- Camina con el ciclo de CAMINAR de Jerry (`recorridos/caminar_animacion_jerry.py`, SniffingSearchCycle, 25 f por ciclo, amplitud x0.85) a 20 f por bloque y la cabeza gacha olfateando.
- Guion: camina 1.3 m -> PAUSA 'olfatea' (cabeza baja que cabecea, 14 f) -> camina 0.95 m seguidos (sin retroceder)
  -> llega, gira hacia el creeper (rz 90) y 'husmea': cabeza baja que cabecea hacia delante, cola moviendose lenta (40 f) y se queda asi.
Parte de la pose de reposo de f567 (la ultima de `jerry_regresa_y_se_cubre_parte7.py`) y borra sus claves >= f568. Se ejecuta dentro de Blender: exec(open(RUTA, encoding='utf-8').read()). Sin sonidos (no pedidos)."""
import bpy, math
from mathutils import Vector

DOCS = 'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/jerry/refinar/'
T_STAND = 567; T0 = int(globals().get('T_ACERCA_J', 568))
g = {'__name__': 'x'}
exec(open(DOCS + 'docs/jerry_recorrido_parte7.py', encoding='utf-8').read().split('# ---------------- construccion')[0], g)
g['CL'] = 25; g['HALF'] = 12; g['RM'] = {'leg': 0.85, 'leg_front': 0.85, 'spine': 0.85, 'tail': 0.6, 'head': 0.3, 'ear': 0.7}      # caminar de Jerry (25 f) mas suave: patas 0.85, cabeza casi quieta (la pone el gesto)
pose_run, ss, mul, BOB = g['pose_run'], g['ss'], g['mul'], 0.025
root, arm, sc = g['root'], g['arm'], g['sc']
NB = [n for n in ['shoulder.L', 'shoulder.R', 'thigh.L', 'thigh.R', 'shin.L', 'shin.R', 'foot.L', 'foot.R', 'toe.L', 'toe.R', 'front_shoulder.L', 'front_shoulder.R', 'front_thigh.L', 'front_thigh.R',
      'front_shin.L', 'front_shin.R', 'front_foot.L', 'front_foot.R', 'front_toe.L', 'front_toe.R'] + ['spine_%d' % i for i in range(1, 8)] + ['tail_%d' % i for i in range(1, 4)] +
      ['scull', 'scull_1', 'neck', 'jaw_top', 'ear.L', 'ear.R', 'sombrero'] if n in arm.pose.bones]
ZERO = (0.0, 0.0, 0.0)
def curvas(o): return [fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]

# ---------- pose de partida y camino ----------
sc.frame_set(T_STAND); bpy.context.view_layer.update()
P0 = Vector(root.location); RZ0 = root.rotation_euler.z; rx, ry = root.rotation_euler.x, root.rotation_euler.y
PF = Vector((-107.45, -88.75, P0.z)); LTOT = (PF - P0).length; DIR = (PF - P0).normalized(); RZ_PATH = -math.atan2(DIR.x, DIR.y); RZ_PATH += 2 * math.pi * round((RZ0 - RZ_PATH) / (2 * math.pi))
LOOK = Vector((-108.5, -89.7, 15.5))                                                                              # cara del creeper tumbado: Jerry SIEMPRE mira hacia ahi mientras se acerca (el cuerpo gira con la posicion)
def mira_a(p, prev):                                                                                               # rz con el que Jerry (mira a +y con rz 0) mira al creeper desde p, continuo con el valor anterior
    rz = -math.atan2(LOOK.x - p.x, LOOK.y - p.y); return rz + 2 * math.pi * round((prev - rz) / (2 * math.pi))
FPB = 20.0                                                                                                        # frames por bloque al caminar hacia delante
SEGS = [('anda', 1.3), ('pausa', 14, 'olfatea'), ('anda', 0.95), ('pausa', 40, 'husmea')]
NET = sum(s[1] for s in SEGS if s[0] == 'anda') - sum(s[1] for s in SEGS if s[0] == 'atras'); assert abs(NET - LTOT) < 0.2, (NET, LTOT)   # los metros del guion suman el camino

def gesto(kind, w, tt):                                                                                           # gestos aditivos de la cabeza, el cuello y la cola
    d = {n: [0.0, 0.0, 0.0] for n in NB}
    if kind == 'andando':                                                                                         # cabeza gacha olfateando mientras anda
        d['scull'][0] = 0.30 * w; d['spine_1'][0] = 0.08 * w
    elif kind == 'olfatea':
        d['scull'][0] = (0.42 + 0.07 * math.sin(2 * math.pi * tt / 7.0)) * w; d['spine_1'][0] = 0.12 * w; d['scull'][1] = 0.15 * w * math.sin(2 * math.pi * tt / 14.0)
    elif kind == 'alerta':                                                                                        # cabeza arriba, mira a los lados
        d['scull'][0] = -0.28 * w; d['scull'][1] = 0.45 * w * math.sin(2 * math.pi * tt / 6.0); d['spine_1'][0] = -0.05 * w
    elif kind == 'husmea':
        d['scull'][0] = (0.45 + 0.10 * math.sin(2 * math.pi * tt / 8.0)) * w; d['spine_1'][0] = 0.14 * w; d['spine_2'][0] = 0.06 * w
        for i in (1, 2, 3): d['tail_%d' % i][2] = 0.30 * w * math.sin(2 * math.pi * tt / 16.0 + i * 0.4)
    return d

frames = []; fr = 0.0; dist = 0.0
for sg in SEGS:
    if sg[0] == 'anda':
        for k in range(int(round(sg[1] * FPB))): fr += 1; dist += 1.0 / FPB; frames.append(dict(fr=fr, dist=dist, kind='andando', w=1.0, tt=k, move=1))
    elif sg[0] == 'atras':
        n = 8
        for k in range(n): fr -= 1.4; dist -= sg[1] / n; frames.append(dict(fr=fr, dist=dist, kind='andando', w=1.0, tt=k, move=-1))
    else:
        dur, kind = sg[1], sg[2]
        for k in range(dur): frames.append(dict(fr=fr, dist=dist, kind=kind, w=ss((k + 1) / 5.0) * (ss((dur - k) / 5.0) if kind != 'husmea' else 1.0), tt=k, move=0))
DIST_END = frames[-1]['dist']
# ---------- claves ----------
for fc in curvas(root) + curvas(arm):
    for i in range(len(fc.keyframe_points) - 1, -1, -1):
        if fc.keyframe_points[i].co.x >= T0: fc.keyframe_points.remove(fc.keyframe_points[i])
def key_root(f, p, rz):
    root.location = p; root.rotation_euler = (rx, ry, rz); root.keyframe_insert('location', frame=f); root.keyframe_insert('rotation_euler', frame=f)
def key_pose(f, k):
    for n in NB:
        b = arm.pose.bones[n]; b.rotation_euler = k.get(n, ZERO); b.keyframe_insert('rotation_euler', frame=f, group=n)
prev_rz = RZ0; BLEND = 5; wm = []; w_ = 0.0                                                                                       # peso del ciclo de caminar: rampa de 5 f al arrancar y al parar (en pausa se funde a la pose de reposo)
for f_ in frames: w_ += max(-1.0 / BLEND, min(1.0 / BLEND, (1.0 if f_['move'] != 0 else 0.0) - w_)); wm.append(w_)
for i, f_ in enumerate(frames):
    t = T0 + i; d = max(0.0, f_['dist']); p = P0 + DIR * d
    rz = mira_a(p, prev_rz); rz = prev_rz + max(-0.05, min(0.05, rz - prev_rz)); prev_rz = rz                      # el giro hacia el creeper tiene como maximo 0.05 rad (2.9 grados) por frame
    wmov = ss(wm[i]); pr = pose_run(f_['fr']); base = {n: mul(pr.get(n, ZERO), wmov) for n in NB}
    gg = gesto(f_['kind'], f_['w'] if f_['kind'] != 'andando' else min(1.0, ss((i + 1) / 8.0)), f_['tt'])
    vals = {n: tuple(base[n][c] + gg[n][c] for c in range(3)) for n in NB}
    bob = BOB * (0.5 - 0.5 * math.cos(2 * math.pi * (f_['fr'] % 12.5) / 12.5 * 2)) * wmov
    key_root(t, (p.x, p.y, P0.z + bob), rz); key_pose(t, vals)
T_FIN = T0 + len(frames) - 1
for fc in curvas(root) + curvas(arm):
    for kp in fc.keyframe_points:
        if kp.co.x >= T_STAND: kp.interpolation = 'LINEAR'
sc.frame_end = max(sc.frame_end, T_FIN)
sc.frame_set(T_STAND)
print("Jerry se acerca: f%d-%d | camino %.2f m, pausas %s | llega a (%.2f, %.2f) y mira al creeper (rz final %.0f)" % (T0, T_FIN, LTOT, [(s[2], s[1]) for s in SEGS if s[0] == 'pausa'], PF.x, PF.y, math.degrees(prev_rz)))
