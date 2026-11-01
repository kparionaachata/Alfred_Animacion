# -*- coding: utf-8 -*-
"""Parte 8: mientras mira la cueva, Jerry TIRA el pico de piedra hacia su derecha con un latigazo de cabeza; vuela girando y GOLPEA la cabeza de Alfred en IMPACTO (2030);
ACCION-REACCION: el pico rebota (velocidad reflejada, giro invertido) y cae al piso; la cabeza de Alfred se sacude por el golpe y vuelve con rebote elastico.
- Ejecutar DESPUES de `jerry_se_sienta_mira_cueva_parte8.py` (que rehace las claves de Jerry y del pico > 1900). Las claves de Alfred se guardan la primera vez
  (`scene["alfred_golpe_base"]`) y se reaplican desde ahi: repetible.
- Animacion de LANZAR: carga (SUELTA-16..-5: cabeza abajo / izquierda, tronco torcido, cola al otro lado), lanzamiento (SUELTA-5..+2: cabeza arriba / derecha, patas delanteras
  arriba, orejas atras, boca abierta) y vuelta (+2..+16). SUELTA a mitad del latigazo. El pico vuela en PARABOLA (x / y lineales, apice 0.8 m sobre la salida) girando 2.5 vueltas.
- Reaccion de Alfred (tunel_alfred_armature): `Neck_alfred` X +0.40 (la cabeza se va hacia delante / abajo) y Z +0.30 (hacia el lado del golpe) en 2 f, `Spine2_alfred` X +0.12,
  vuelta ELASTIC en 16 f."""
import bpy, math
from mathutils import Vector, Quaternion

SUELTA = globals().get('SUELTA', 2010); IMPACTO = globals().get('IMPACTO', 2030); FIN = globals().get('FIN', 2070)
ss = lambda t: 0.0 if t <= 0 else 1.0 if t >= 1 else t * t * (3 - 2 * t)
def ela_out(t):                                                                     # Elastic Out (rebote al volver)
    if t <= 0: return 0.0
    if t >= 1: return 1.0
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi) / 3) + 1

sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'scull_1' in o.pose.bones); pk = bpy.data.objects['tunel_jerry_pico']
armA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'Hips_alfred' in o.pose.bones)
def fcs(o): return {(fc.data_path, fc.array_index): fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves}
FA, FP, FAL = fcs(arm), fcs(pk), fcs(armA)
def key(fc, f, v):
    k = fc.keyframe_points.insert(f, v); k.interpolation = 'LINEAR'
def bake_pose_pico(f, M, prev):
    l, q, s = M.decompose(); e = q.to_euler('XYZ', prev) if prev is not None else q.to_euler('XYZ')
    for i in range(3): key(FP[('location', i)], f, l[i]); key(FP[('rotation_euler', i)], f, e[i])
    return e

# ---------------- 1) Jerry: ANIMACION DE LANZAR (carga -> lanzamiento -> seguimiento), con cuerpo, cabeza, patas, cola y orejas ----------------
sc.frame_set(SUELTA - 20); OFF = (arm.matrix_world @ arm.pose.bones['scull'].matrix).inverted() @ pk.matrix_world     # forma de llevar el pico (antes de tocar nada)
# (hueso, eje, CARGA, LANZA)  [Z de spine: + = a la DERECHA de Jerry]: CARGA = cabeza algo arriba / a la izquierda, tronco torcido; LANZA = cabeza ABAJO / a la derecha (sale el pico), patas delanteras arriba
GESTO = [('spine_2', 0, -0.20, 0.30), ('spine_2', 2, -0.50, 0.65), ('spine_1', 0, -0.10, 0.15), ('spine_1', 2, -0.20, 0.30),
         ('spine_4', 2, -0.15, 0.22), ('spine_5', 0, -0.05, 0.08), ('front_shoulder.L', 0, 0.05, -0.18), ('front_shoulder.R', 0, 0.05, -0.18),
         ('tail_1', 2, 0.40, -0.55), ('tail_2', 2, 0.25, -0.40), ('ear.L', 0, 0.0, -0.25), ('ear.R', 0, 0.0, -0.25), ('jaw_bot', 0, 0.0, -0.40)]
C0, C1, L1, V1 = SUELTA - 16, SUELTA - 5, SUELTA + 2, SUELTA + 16        # carga C0->C1, lanzamiento C1->L1 (suelta en SUELTA, a mitad del latigazo), vuelta L1->V1
def gesto(f, carga, lanza):
    if f <= C0 or f >= V1: return 0.0
    if f <= C1: return carga * ss((f - C0) / (C1 - C0))
    if f <= L1: u = (f - C1) / (L1 - C1); return carga + (lanza - carga) * (u * u * (3 - 2 * u))
    return lanza * (1 - ss((f - L1) / (V1 - L1)))
R = range(C0, V1 + 1)
for b, i, ca, la in GESTO:
    fc = FA.get(('pose.bones["%s"].rotation_euler' % b, i))
    if fc is None: continue
    bs = {f: fc.evaluate(f) for f in R}
    for f in R: key(fc, f, bs[f] + gesto(f, ca, la) * (1.0 if b != 'jaw_bot' else (1.0 if f >= SUELTA - 2 else 0.0)))
    fc.update()

# ---------------- 2) pico: en la boca hasta SUELTA (re-horneado) y vuelo en PARABOLA hasta la cabeza de Alfred ----------------
for fc in FP.values():
    for k in [k for k in fc.keyframe_points if k.co.x > C0 - 0.5][::-1]: fc.keyframe_points.remove(k)
prev = None; M = {}
for f in range(C0, SUELTA + 1):
    sc.frame_set(f); M[f] = arm.matrix_world @ arm.pose.bones['scull'].matrix @ OFF; prev = bake_pose_pico(f, M[f], prev)
p0 = M[SUELTA].to_translation(); q0 = M[SUELTA].to_quaternion(); v0 = p0 - M[SUELTA - 1].to_translation()
sc.frame_set(IMPACTO); dg = bpy.context.evaluated_depsgraph_get(); cab = bpy.data.objects['Mesh_0_alfred'].evaluated_get(dg)
vs = [cab.matrix_world @ v.co for v in cab.data.vertices]; p1 = sum(vs, Vector()) / len(vs); p1.z = max(v.z for v in vs) + 0.05
N = IMPACTO - SUELTA; APICE = max(p0.z, p1.z) + 0.8
# parabola: x / y lineales (velocidad horizontal constante), z cuadratica que pasa por p0, el APICE y p1
c = 4 * (APICE - (p0.z + p1.z) / 2)                                                 # z(u) = p0 + (p1-p0) u + c u (1-u): maximo ~ APICE a mitad del vuelo
def parab(u): return Vector((p0.x + (p1.x - p0.x) * u, p0.y + (p1.y - p0.y) * u, p0.z + (p1.z - p0.z) * u + c * u * (1 - u)))
def herm(u): return parab(u)
hz = Vector((p1.x - p0.x, p1.y - p0.y, 0)).normalized(); eje = hz.cross(Vector((0, 0, 1))).normalized(); vueltas = 2.5
from mathutils import Matrix
def Mq(p, q): return Matrix.Translation(p) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((*pk.scale, 1))
for k in range(1, N + 1):
    u = k / N; prev = bake_pose_pico(SUELTA + k, Mq(parab(u), Quaternion(eje, -2 * math.pi * vueltas * u) @ q0), prev)
qi = Quaternion(eje, -2 * math.pi * vueltas) @ q0

# ---------------- 3) REBOTE del pico en la cabeza: velocidad reflejada (amortiguada), giro invertido, gravedad, rebotito en el piso ----------------
piso = bpy.data.objects['alfred'].matrix_world.translation.z + 0.03
vin = herm(1.0) - herm(1.0 - 1.0 / N)
v = Vector((-0.30 * vin.x, -0.30 * vin.y, 0.55 * abs(vin.z) + 0.06)); g = 0.028; p = p1.copy(); f = IMPACTO; giro_r = 0.0; rebotes = 0
cx = math.floor(p1.x) + 0.5; cy = math.floor(p1.y) + 0.5                              # se queda dentro del pasillo de Alfred
while f < FIN and rebotes < 2:
    f += 1; v.z -= g; p = p + v; p.x = min(max(p.x, cx - 0.4), cx + 0.4); p.y = min(max(p.y, cy - 0.32), cy + 0.32)
    giro_r += 0.32 * (1 if rebotes == 0 else 0.4)
    if p.z <= piso:
        p.z = piso; rebotes += 1; v = Vector((v.x * 0.4, v.y * 0.4, abs(v.z) * 0.25))
    prev = bake_pose_pico(f, Mq(p, Quaternion(eje, giro_r) @ qi), prev)
qt = Quaternion(Vector((0, 0, 1)), math.atan2(hz.y, hz.x)) @ Quaternion(Vector((1, 0, 0)), math.pi / 2)
qa = Quaternion(eje, giro_r) @ qi
for k in range(1, 7):                                                                   # se acomoda tumbado en el piso
    prev = bake_pose_pico(f + k, Mq(p, qa.slerp(qt, ss(k / 6.0))), prev)
for ff in range(f + 10, FIN + 1, 6): prev = bake_pose_pico(ff, Mq(p, qt), prev)
for fc in FP.values(): fc.update()
cae = f

# ---------------- 4) REACCION de Alfred: la cabeza se sacude por el golpe y vuelve con rebote ----------------
BONES = [('Neck_alfred', 0, 0.40), ('Neck_alfred', 2, 0.30), ('Spine2_alfred', 0, 0.12), ('Spine1_alfred', 0, 0.05)]
RA = range(IMPACTO - 1, IMPACTO + 20)
base = sc.get("alfred_golpe_base")
if base is None:
    base = {"%s|%d" % (b, i): [FAL[('pose.bones["%s"].rotation_euler' % b, i)].evaluate(f) for f in RA] for b, i, _ in BONES}; sc["alfred_golpe_base"] = base
for b, i, amp in BONES:
    fc = FAL[('pose.bones["%s"].rotation_euler' % b, i)]; bs = list(base["%s|%d" % (b, i)])
    for j, f in enumerate(RA):
        if f <= IMPACTO: w = 0.0
        elif f <= IMPACTO + 2: w = (f - IMPACTO) / 2.0                                    # golpe: 2 f
        else: w = 1.0 - ela_out((f - IMPACTO - 2) / 16.0)                                  # vuelve con rebote elastico
        key(fc, f, bs[j] + amp * w)
    fc.update()
sc.frame_set(IMPACTO)
print('Jerry suelta el pico en f%d (vel. boca %.3f m/f, %.2f vueltas); golpe en f%d en %s; cae al piso en f%d' % (SUELTA, v0.length, vueltas, IMPACTO, tuple(round(x, 2) for x in p1), cae))
