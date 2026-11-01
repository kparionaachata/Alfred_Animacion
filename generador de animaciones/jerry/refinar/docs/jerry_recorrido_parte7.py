# -*- coding: utf-8 -*-
"""Parte 7: Jerry recorre `recorridos/jerry_parte7.json` CORRIENDO y salta el bloque con la animacion `saltar_subir`.
- Correr = el ciclo de caminar de Jerry (`recorridos/caminar_animacion_jerry.py`, SniffingSearchCycle) con los parametros de CORRER del estudio de Jerry:
  ciclo 12 f (25*0.5), RANGE_MULT leg 1.7 / spine 1.6 / tail 1.5 / head 0.6 / ear 0.7, rebote vertical 0.05 m, 14.4 f por bloque (32 * 0.45).
- Salto = `recorridos/saltar_subir_animacion_jerry.py` (DogJumpCycle, TIMING (2, 9, 3), 15 f, parabola Bezier) en el tramo del punto con z mas alta (+1).
- Los tramos que bajan (z -1) se corren con el z interpolado. Empieza en el frame S colocando a Jerry en el punto 1 mirando a +y (rz 0) y termina frenando (pose -> 0 en 6 f).
Sin parpadeos, filtros organicos ni sonidos (no pedidos). Se ejecuta dentro de Blender:  exec(open(RUTA, encoding='utf-8').read())  [S = 1 por defecto: definir S antes para cambiarlo]"""
import bpy, json, math
from mathutils import Vector

S = globals().get('S', 1)                                                    # frame en que Jerry esta en el punto 1
RUTA_JSON = r'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/jerry/refinar/docs/recorridos/jerry_parte7.json'
FPB = 7.2                                                                    # frames por bloque al correr (CORRER del estudio = 14.4; aqui el doble de rapido)
CL = max(4, round(25 * 0.5)); RM = {'leg': 1.3, 'leg_front': 1.3, 'spine': 1.0, 'tail': 1.5, 'head': 0.6, 'ear': 0.7}; BOB = 0.05   # amplitud de la caminata del usuario: patas 1.3 (delanteras = traseras, alternan); con 1.7 y columna 1.6 las delanteras se esconden en el torso
TIMING = (2, 9, 3); JUMP_FRAMES = sum(TIMING) + 1                           # 15
FRENADO = 6
HALF = CL // 2                                                               # desfase de las patas delanteras: medio ciclo (en la caminata original 12 de 25); con ciclo 12, +12 las ponia en fase con las traseras del mismo lado

sc = bpy.context.scene
root = bpy.data.objects['jerry']; arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.parent == root)
pts = [(k['coordinates']['x'], k['coordinates']['y'], k['coordinates']['z']) for k in json.load(open(RUTA_JSON))['key_points']]

sw = lambda f, p, a, ph=0, off=0: a * math.sin(2 * math.pi * f / p + ph) + off
ss = lambda x: 0.0 if x <= 0 else 1.0 if x >= 1 else x * x * (3 - 2 * x)
ease_in_out = lambda t: t * t * (3 - 2 * t); ease_out = lambda t: 1 - (1 - t) * (1 - t); ease_in = lambda t: t * t
mul = lambda v, m: tuple(x * m for x in v)


# ---------------- ciclo de caminar -> correr (copia de SniffingSearchCycle con RANGE_MULT de CORRER) ----------------
def nrm(fr): return ((fr - 1) % CL) + 1
def leg_slow(fr, rear, left):
    n = nrm(fr); ph = 0 if left else math.pi; amp = (0.4 if rear else 0.3) * (RM['leg'] if rear else RM['leg_front'])
    return (-sw(n, CL, amp, ph), -sw(n, CL, amp * 0.15, ph), -sw(n, CL, amp * 0.03, ph))
def leg_bend(fr, rear, left):
    n = nrm(fr); ph = 0 if left else math.pi; bb = (0.3 if rear else 0.24) * (RM['leg'] if rear else RM['leg_front'])
    return (-abs(sw(n, CL, bb, ph, bb)), -sw(n, CL, 0.1, ph), -sw(n, CL, 0.04, ph))
def foot_strike(fr, rear, left):
    n = nrm(fr); ph = 0 if left else math.pi; ax = (0.8 if rear else 0.6) * (RM['leg'] if rear else RM['leg_front'])
    return (-sw(n, CL, ax, ph, 0.4 if rear else -0.1), abs(sw(n, CL, 0.04, ph, 0.02)) * (1.0 if rear else 0.5), -sw(n, CL, 0.04 if rear else 0.06, ph, 0.02))
def toe_curl(fr, rear, left):
    n = nrm(fr); ph = 0 if left else math.pi; amp = 0.5 * (RM['leg'] if rear else RM['leg_front'])
    return (abs(sw(n, CL, amp, ph, 0.4)), -sw(n, CL, 0.16, ph), -sw(n, CL, 0.08, ph, 0.04))
def tail_wag(fr):
    n = nrm(fr); t = RM['tail']; return (sw(n, CL, 0.4 * t, 0, 0.2 * t), sw(n, CL, 0.06 * t), sw(n, CL, 0.16 * t))
def ear_tw(fr):
    n = nrm(fr); return (0, sw(n, CL, 0.2 * RM['ear']), sw(n, CL, 0.1 * RM['ear']))
def pose_run(fr):
    k = {}
    for s, left in (('L', True), ('R', False)):
        k['shoulder.' + s] = leg_slow(fr, True, left); k['shin.' + s] = leg_bend(fr, True, left); k['foot.' + s] = foot_strike(fr, True, left); k['toe.' + s] = toe_curl(fr, True, left)
        k['front_shoulder.' + s] = leg_slow(fr + HALF, False, left); k['front_shin.' + s] = leg_bend(fr + HALF, False, left)
        k['front_foot.' + s] = foot_strike(fr + HALF, False, left); k['front_toe.' + s] = toe_curl(fr + HALF, False, left)
    k['thigh.L'] = mul(leg_slow(fr, True, True), 0.01); k['thigh.R'] = mul(leg_slow(fr, True, False), -0.3)
    k['front_thigh.L'] = mul(leg_slow(fr + HALF, False, True), 0.6); k['front_thigh.R'] = mul(leg_slow(fr + HALF, False, False), 0.4)
    for i in range(1, 8): k['spine_%d' % i] = (-sw(nrm(fr), CL, 0.03 * RM['spine'], (i / 7) * math.pi, -0.08 * RM['spine']), 0, 0)
    for i in range(1, 4): k['tail_%d' % i] = tail_wag(fr)
    n = nrm(fr); sn = (sw(n, CL, 0.03 * RM['head']), 0, 0); lk = (0, sw(n, CL, 0.05 * RM['head']), 0); tl = (0, 0, sw(n, CL, 0.016 * RM['head']))
    k['scull'] = (sn[0] + tl[0] * 0.3, lk[1], tl[2]); k['jaw_top'] = (0.224, 0, 0); k['ear.L'] = ear_tw(fr); k['ear.R'] = ear_tw(fr + 6); k['sombrero'] = (0, 0, 0)
    return k


# ---------------- salto (copia de DogJumpCycle y _bones_saltar_subir de saltar_subir_animacion_jerry.py) ----------------
class DogJumpCycle:
    def __init__(self): self.impulse_frames = (1, 5); self.jump_frames = (6, 11); self.fall_frames = (12, 15)
    def get_phase_progress(self, frame):
        for (s, e), phase in [(self.impulse_frames, 'impulse'), (self.jump_frames, 'jump'), (self.fall_frames, 'fall')]:
            if s <= frame <= e: return phase, (frame - s) / max(1, e - s)
        return 'neutral', 0
    def _tri(self, frame, imp, jmp, fal):
        ph, pr = self.get_phase_progress(frame)
        return imp(pr) if ph == 'impulse' else jmp(pr) if ph == 'jump' else fal(pr) if ph == 'fall' else (0, 0, 0)
    def rear_thigh(self, f, L=True):
        s = 1 if L else -1
        return self._tri(f, lambda p: (-ease_in_out(p) * 0.20, sw(p * 6, 6, 0.03 * s), sw(p * 4, 4, 0.02)), lambda p: (-ease_out(p) * 0.25, sw(p * 12, 12, 0.015 * s), sw(p * 10, 10, 0.025)), lambda p: (-ease_in(p) * 0.15, sw(p * 8, 8, 0.01 * s), sw(p * 6, 6, -0.01)))
    def rear_shin(self, f, L=True):
        s = 1 if L else -1
        return self._tri(f, lambda p: (-ease_in_out(p) * 0.18, sw(p * 8, 8, 0.02 * s), sw(p * 6, 6, 0.015)), lambda p: (-ease_out(p) * 0.22, sw(p * 12, 12, 0.01 * s), sw(p * 8, 8, 0.02)), lambda p: (-ease_in(p) * 0.12, sw(p * 8, 8, 0.008 * s), sw(p * 4, 4, 0.01)))
    def rear_foot(self, f, L=True):
        s = 1 if L else -1
        return self._tri(f, lambda p: (-ease_in_out(p) * 0.15, sw(p * 12, 12, 0.03 * s), sw(p * 10, 10, 0.02)), lambda p: (-ease_out(p) * 0.18, sw(p * 25, 25, 0.02 * s), sw(p * 15, 15, 0.03)), lambda p: (-ease_in(p) * 0.1, sw(p * 15, 15, 0.01 * s), sw(p * 8, 8, 0.015)))
    def rear_toe(self, f, L=True):
        return self._tri(f, lambda p: (ease_in_out(p) * 0.12, 0, 0), lambda p: (ease_out(p) * 0.08, 0, 0), lambda p: (ease_in(p) * 0.05, 0, 0))
    def front_thigh(self, f, L=True):
        s = 1 if L else -1
        return self._tri(f, lambda p: (-ease_in_out(p) * 0.1, sw(p * 8, 8, 0.04 * s), sw(p * 6, 6, -0.02)), lambda p: (ease_out(p) * 0.35, sw(p * 15, 15, 0.03 * s), sw(p * 12, 12, 0.04)), lambda p: (-ease_in(p) * 0.3, sw(p * 10, 10, 0.02 * s), sw(p * 8, 8, 0.02)))
    def front_shin(self, f, L=True):
        s = 1 if L else -1
        return self._tri(f, lambda p: (-ease_in_out(p) * 0.15, sw(p * 10, 10, 0.03 * s), sw(p * 8, 8, -0.01)), lambda p: (-ease_out(p) * 0.25, sw(p * 20, 20, 0.02 * s), sw(p * 15, 15, 0.03)), lambda p: (-ease_in(p) * 0.18, sw(p * 12, 12, 0.015 * s), sw(p * 10, 10, 0.02)))
    def front_foot(self, f, L=True):
        s = 1 if L else -1
        return self._tri(f, lambda p: (-ease_in_out(p) * 0.12, sw(p * 12, 12, 0.02 * s), sw(p * 8, 8, -0.015)), lambda p: (-ease_out(p) * 0.2, sw(p * 18, 18, 0.015 * s), sw(p * 12, 12, 0.02)), lambda p: (-ease_in(p) * 0.15, sw(p * 10, 10, 0.01 * s), sw(p * 6, 6, 0.01)))
    def front_toe(self, f, L=True):
        return self._tri(f, lambda p: (ease_in_out(p) * 0.08, 0, 0), lambda p: (ease_out(p) * 0.1, 0, 0), lambda p: (ease_in(p) * 0.06, 0, 0))
    def spine_action(self, f, seg, tot=7):
        sf = seg / tot
        return self._tri(f, lambda p: (-ease_in_out(p) * 0.2 * sf, sw(p * 6, 6, 0.03 * sf), ease_in_out(p) * 0.08 * sf), lambda p: (ease_out(p) * 0.25 * sf, sw(p * 10, 10, 0.02 * sf), ease_out(p) * 0.12 * sf), lambda p: (-ease_in(p) * 0.15 * sf, sw(p * 8, 8, 0.015 * sf), ease_in(p) * 0.06 * sf))
    def head_movement(self, f):
        return self._tri(f, lambda p: (-ease_in_out(p) * 0.06, sw(p * 8, 8, 0.03), sw(p * 6, 6, 0.02)), lambda p: (ease_out(p) * 0.08, sw(p * 12, 12, 0.04), sw(p * 10, 10, 0.03)), lambda p: (-ease_in(p) * 0.05, sw(p * 8, 8, 0.02), sw(p * 6, 6, 0.015)))
    def jaw_movement(self, f):
        return self._tri(f, lambda p: (ease_in_out(p) * 0.03, 0, 0), lambda p: (ease_out(p) * 0.04, 0, 0), lambda p: (ease_in(p) * 0.02, 0, 0))
    def ear_movement(self, f, L=True):
        d = -1 if L else 1
        return self._tri(f, lambda p: (ease_in_out(p) * 0.05 * d, sw(p * 15, 15, 0.02), sw(p * 12, 12, 0.015)), lambda p: (ease_out(p) * 0.06 * d, sw(p * 20, 20, 0.025), sw(p * 18, 18, 0.02)), lambda p: (-ease_in(p) * 0.04 * d, sw(p * 12, 12, 0.015), sw(p * 10, 10, 0.01)))
    def neck_movement(self, f):
        return self._tri(f, lambda p: (-ease_in_out(p) * 0.04, sw(p * 8, 8, 0.02), 0), lambda p: (ease_out(p) * 0.05, sw(p * 12, 12, 0.03), 0), lambda p: (-ease_in(p) * 0.03, sw(p * 8, 8, 0.02), 0))
    def tail_movement(self, f, seg):
        sf = seg / 3
        return self._tri(f, lambda p: (-ease_in_out(p) * 0.15 * sf, sw(p * 25, 25, 0.06 * sf), sw(p * 20, 20, 0.04 * sf)), lambda p: (ease_out(p) * 0.25 * sf, sw(p * 40, 40, 0.1 * sf), sw(p * 35, 35, 0.08 * sf)), lambda p: (ease_in(p) * 0.15 * sf, sw(p * 25, 25, 0.05 * sf), sw(p * 20, 20, 0.03 * sf)))


def jump_smooth(t): t = min(max(t, 0.0), 1.0); return t * t * (3.0 - 2.0 * t)
def jump_phase(elapsed, timing):
    prep, flight, land = timing
    if elapsed <= prep: return 0.16 * elapsed / prep
    if elapsed <= prep + flight: return 0.16 + 0.64 * (elapsed - prep) / flight
    return min(1.0, 0.80 + 0.20 * (elapsed - prep - flight) / land)
def jump_position(p0, p1, t, kind='subir'):
    t = min(max(t, 0.0), 1.0); u = min(max((t - 0.16) / 0.64, 0.0), 1.0)
    distance = math.hypot(p1[0] - p0[0], p1[1] - p0[1]); height = abs(p1[2] - p0[2]); bias = 0.18
    control_z = max(p0[2], p1[2]) + max(0.8, 1.4 * height, 0.45 * distance)
    control = (p0[0] + bias * (p1[0] - p0[0]), p0[1] + bias * (p1[1] - p0[1]), control_z)
    return tuple((1 - u) ** 2 * a + 2 * u * (1 - u) * c + u * u * b for a, b, c in zip(p0, p1, control))
def pose_jump(phase):
    jump = DogJumpCycle(); lf = phase * 14 + 1; k = {}
    for s, L in (('L', True), ('R', False)):
        k['thigh.' + s] = jump.rear_thigh(lf, L); k['shin.' + s] = jump.rear_shin(lf, L); k['foot.' + s] = jump.rear_foot(lf, L); k['toe.' + s] = jump.rear_toe(lf, L)
        k['front_thigh.' + s] = jump.front_thigh(lf, L); k['front_shin.' + s] = jump.front_shin(lf, L); k['front_foot.' + s] = jump.front_foot(lf, L); k['front_toe.' + s] = jump.front_toe(lf, L); k['ear.' + s] = jump.ear_movement(lf, L)
    for i in range(1, 8): k['spine_%d' % i] = jump.spine_action(lf, i, 7)
    for i in range(1, 4): k['tail_%d' % i] = jump.tail_movement(lf, i)
    k['neck'] = jump.neck_movement(lf); k['scull'] = jump.head_movement(lf); k['scull_1'] = mul(jump.head_movement(lf), 0.5); k['jaw_top'] = jump.jaw_movement(lf)
    if phase >= 0.80:
        rec = jump_smooth((phase - 0.80) / 0.20)
        for b in list(k): k[b] = mul(k[b], 1.0 - rec)
    return k


# ---------------- construccion ----------------
NB = ['shoulder.L', 'shoulder.R', 'thigh.L', 'thigh.R', 'shin.L', 'shin.R', 'foot.L', 'foot.R', 'toe.L', 'toe.R', 'front_shoulder.L', 'front_shoulder.R', 'front_thigh.L', 'front_thigh.R',
      'front_shin.L', 'front_shin.R', 'front_foot.L', 'front_foot.R', 'front_toe.L', 'front_toe.R'] + ['spine_%d' % i for i in range(1, 8)] + ['tail_%d' % i for i in range(1, 4)] + \
     ['scull', 'scull_1', 'neck', 'jaw_top', 'ear.L', 'ear.R', 'sombrero']
faltan = [n for n in NB if n not in arm.pose.bones]
assert set(faltan) <= {'neck', 'scull_1'}, 'faltan huesos: %s' % faltan                 # neck/scull_1 son opcionales (el salto original los usa solo "if in bones")
NB = [n for n in NB if n in arm.pose.bones]; print('huesos omitidos (no existen en este rig):', faltan)
BASE = {n: (0.0, 0.0, 0.0) for n in NB}                                       # sale desde la pose de reposo (el escenario base no trae una pose de Jerry que conservar)
for b in arm.pose.bones: b.rotation_mode = 'XYZ'
if arm.animation_data and arm.animation_data.action: arm.animation_data.action = None
if root.animation_data and root.animation_data.action: root.animation_data.action = None

# tramos: el de mayor subida es el salto; el resto, correr (cada uno FPB frames, con redondeo acumulado)
sub = max(range(len(pts) - 1), key=lambda i: pts[i + 1][2] - pts[i][2]); assert pts[sub + 1][2] - pts[sub][2] >= 0.99, 'no hay tramo de subida'
bounds = []; t = S; run_acc = 0.0                                               # bounds[i] = frame de llegada al punto i (inicio del tramo i)
for i in range(len(pts)):
    bounds.append(t)
    if i == len(pts) - 1: break
    if i == sub: t += JUMP_FRAMES - 1
    else:
        d = math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) * FPB; nt = round((run_acc + d)); t += nt - round(run_acc); run_acc += d
E = bounds[-1]; Tj0 = bounds[sub]; Tj1 = Tj0 + JUMP_FRAMES - 1
rx, ry = root.rotation_euler.x, root.rotation_euler.y
def key_root(f, p, rz=0.0):
    root.location = p; root.rotation_euler = (rx, ry, rz); root.keyframe_insert('location', frame=f); root.keyframe_insert('rotation_euler', frame=f)
def key_pose(f, k):
    for n, v in k.items():
        if n not in NB: continue
        b = arm.pose.bones[n]; b.rotation_euler = v; b.keyframe_insert('rotation_euler', frame=f, group=n)

for f in range(S, E + 1):
    pf = f - S + 1
    if Tj0 <= f <= Tj1:
        ph = jump_phase(f - Tj0, TIMING); key_root(f, jump_position(pts[sub], pts[sub + 1], ph)); key_pose(f, pose_jump(ph)); continue
    i = next((j for j in range(len(pts) - 1) if bounds[j] <= f < bounds[j + 1]), len(pts) - 2)   # tramo de correr que contiene f (el del salto ya se resolvio arriba)
    a, b = bounds[i], bounds[i + 1]; u = (f - a) / max(1, b - a); p = [pts[i][c] + (pts[i + 1][c] - pts[i][c]) * u for c in range(3)]
    n = nrm(pf); bob = BOB * (0.5 - 0.5 * math.cos(2 * math.pi * n / CL * 2)); key_root(f, (p[0], p[1], p[2] + bob))
    wr = 1.0
    if f > Tj1 - 0 and f <= Tj1 + 5: wr = ss((f - Tj1) / 5.0)                    # tras el salto (pose 0) entra al correr
    if Tj0 - 3 <= f < Tj0: wr = min(wr, 1.0 - ss((f - (Tj0 - 3) + 1) / 3.0))     # antes del salto sale del correr hacia la pose del salto
    pr = pose_run(pf); k = {nn: mul(pr.get(nn, (0, 0, 0)), wr) for nn in NB}
    if f <= S + 5:
        w = ss((f - (S - 1)) / 6.0); k = {nn: tuple(BASE[nn][c] * (1 - w) + k[nn][c] * w for c in range(3)) for nn in NB}
    key_pose(f, k)
# anclas previas y frenado final
key_root(S - 1, pts[0]) if S > 1 else None
if S > 1:
    for n in NB: b = arm.pose.bones[n]; b.rotation_euler = BASE[n]; b.keyframe_insert('rotation_euler', frame=S - 1, group=n)
last = {n: tuple(arm.pose.bones[n].rotation_euler) for n in NB}; pend = Vector(pts[-1])        # al frenar se apoya en el suelo (sin el rebote)
for j in range(1, FRENADO + 1):
    f = E + j; w = ss(j / FRENADO); key_root(f, tuple(pend))
    for n in NB: b = arm.pose.bones[n]; b.rotation_euler = tuple(last[n][c] * (1 - w) for c in range(3)); b.keyframe_insert('rotation_euler', frame=f, group=n)

def curvas(action): return [fc for l in action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]
for ob in (root, arm):
    for fc in curvas(ob.animation_data.action):
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
for a in [a for a in bpy.data.actions if a.users == 0 and not a.use_fake_user]: bpy.data.actions.remove(a)   # restos de ejecuciones anteriores
sc.frame_end = max(sc.frame_end, E + FRENADO)
sc.frame_set(S)
print('Jerry: S', S, '| tramos', len(pts) - 1, '| salto en tramo', sub + 1, '->', sub + 2, 'frames', Tj0, '-', Tj1, '| llega al punto', len(pts), 'en f', E, '| frenado hasta f', E + FRENADO)
