# -*- coding: utf-8 -*-
"""Parte 8: despues de subir al escalon (salto hasta f2370), Alfred ROTA +90 grados en Z (de 180 a 270: mira a +x, a la pared), COLOCA UNA ANTORCHA EN LA PARED
(cara oeste del bloque `tunel_bloque_piedra_-131_-71_8`) adaptando `animacion_alfred (14).py` (colocar antorcha en el SUELO: el brazo derecho se estira, la antorcha aparece
en el frame en que la mano llega y el brazo vuelve; sin agacharse), despues rota -180 grados (de 270 a 90: mira a la cueva, -x) y se queda con las MANOS EN LA CINTURA
(`animacion_alfred (15).py`, pose `parado manos en la cintura.json`: solo rotaciones) mirando la cueva hasta FIN.
- La antorcha es una COPIA de `antorcha_1` (empty + luz, llama, palo y humo) inclinada 22.5 grados hacia afuera de la pared (como las de pared de Minecraft); visible desde que la mano llega.
- El brazo para alcanzar la pared se calcula midiendo la punta de la malla de la mano (`Mesh_2_alfred`) contra el punto de la antorcha.
Ejecutar DESPUES de `alfred_pica_y_sube_parte8.py`. Repetible (borra sus claves > T1 y rehace la antorcha)."""
import bpy, math, itertools
from mathutils import Vector, Euler, Matrix

T1 = globals().get('T1', 2372); FIN = globals().get('FIN', 2480); X_FINAL = globals().get('X_FINAL', -132.0)    # x donde se queda con las manos en la cintura (valor del usuario)
BASE_T = Vector((-131.0 - 0.06, -70.5, 8.18))                                            # base de la antorcha (pegada a la cara oeste del bloque de z8)
INCL = math.radians(22.5)
ss = lambda t: 0.0 if t <= 0 else 1.0 if t >= 1 else t * t * (3 - 2 * t)
sc = bpy.context.scene; vl = bpy.context.view_layer
ARM = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'Hips_alfred' in o.pose.bones); ROOT = ARM.parent
def fcs(o): return {(fc.data_path, fc.array_index): fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves}
FA, FR = fcs(ARM), fcs(ROOT)
huesos = sorted({dp.split('"')[1] for dp, i in FA if dp.startswith('pose.bones') and dp.endswith('rotation_euler')})
P0 = {n: [FA[('pose.bones["%s"].rotation_euler' % n, i)].evaluate(T1) for i in range(3)] for n in huesos}
L0 = (FR[('location', 0)].evaluate(T1), FR[('location', 1)].evaluate(T1), FR[('location', 2)].evaluate(T1)); RZ0 = FR[('rotation_euler', 2)].evaluate(T1)
RZ1 = RZ0 + math.radians(90); RZ2 = RZ1 - math.radians(180)
CINTURA = {'Hips_alfred': [0.047325, -0.000283, -0.000006], 'Spine_alfred': [0.0, 0.0, 0.0], 'Spine1_alfred': [-0.063225, 0.000414, -0.000023], 'Spine2_alfred': [0.0, 0.0, 0.0],
           'Neck_alfred': [-0.064246, 0.000337, -0.000012], 'face_alfred': [0.0, 0.0, 0.0], 'RightUpArm_alfred': [1.276101, 0.007172, 0.004379], 'Rightelbow_alfred': [0.801533, -0.061632, -0.025640],
           'LeftUpArm_alfred': [1.100634, 0.000133, -0.002057], 'Leftelbow_alfred': [1.285851, 0.068014, 0.650486], 'RightUpLeg_alfred': [-0.030967, 0.605239, -0.163466], 'Rightknee_alfred': [0.0, 0.0, 0.0],
           'LeftUpLeg_alfred': [0.005388, -0.342157, 0.195707], 'Leftknee_alfred': [0.0, 0.0, 0.0]}
near = lambda s, t: t + math.tau * round((s - t) / math.tau)

# ---------------- brazo hacia la pared: busqueda midiendo la punta de la mano ----------------
for o in (ROOT, ARM): o["_acc_tmp"] = o.animation_data.action.name
accR, accA = ROOT.animation_data.action, ARM.animation_data.action; ROOT.animation_data.action = None; ARM.animation_data.action = None
ROOT.location = L0; ROOT.rotation_euler = (0, 0, RZ1)
for n in huesos: ARM.pose.bones[n].rotation_mode = 'XYZ'; ARM.pose.bones[n].rotation_euler = P0[n]
vl.update(); dg = bpy.context.evaluated_depsgraph_get()
m2 = bpy.data.objects["Mesh_2_alfred"].evaluated_get(dg); sh = ARM.matrix_world @ ARM.pose.bones["RightUpArm_alfred"].head
tip = max((m2.matrix_world @ v.co for v in m2.data.vertices), key=lambda v: (v - sh).length)
off = (ARM.matrix_world @ ARM.pose.bones["Rightelbow_alfred"].matrix).inverted() @ tip
ua = ARM.pose.bones["RightUpArm_alfred"]; el = ARM.pose.bones["Rightelbow_alfred"]
OBJ = BASE_T + Vector((-0.06, 0, 0.02))                                                    # la mano sujeta la antorcha por la base
ua.rotation_euler = (1.570796, 0.0, 0.0); el.rotation_euler = (0.0, 0.0, 0.0)          # parte del brazo COLGANDO (pose neutra de los archivos del usuario): el giro minimo hacia la pared no retuerce el hombro
vl.update(); sh = ARM.matrix_world @ ua.head
# 1) codo: doblarlo (Z) lo justo para que la mano quede a la distancia hombro -> antorcha
def punta():
    vl.update(); return (ARM.matrix_world @ el.matrix) @ off
D = (OBJ - sh).length; mejor = None
for kz in range(0, 141, 2):
    el.rotation_euler = (0.0, 0.0, -math.radians(kz)); d_ = abs((punta() - sh).length - D)
    if mejor is None or d_ < mejor[0]: mejor = (d_, kz)
el.rotation_euler = (0.0, 0.0, -math.radians(mejor[1]))
# 2) brazo: girar el hueso del hombro (alrededor del hombro, en mundo) para que la mano APUNTE a la antorcha (2 pasadas)
for _ in range(3):
    t = punta(); q = (t - sh).rotation_difference(OBJ - sh)
    Mw = ARM.matrix_world @ ua.matrix; R = Matrix.Translation(sh) @ q.to_matrix().to_4x4() @ Matrix.Translation(-sh)
    ua.matrix = ARM.matrix_world.inverted() @ R @ Mw
vl.update(); err = (punta() - OBJ).length; best2 = (err, None)
ALCANCE = {"RightUpArm_alfred": list(ua.rotation_euler), "Rightelbow_alfred": list(el.rotation_euler)}
ROOT.animation_data.action = accR; ARM.animation_data.action = accA

# ---------------- linea de tiempo ----------------
G1 = (T1, T1 + 12); R_IDA = (G1[1] + 1, G1[1] + 14); APARECE = R_IDA[1]; R_VUELTA = (APARECE + 5, APARECE + 17); G2 = (R_VUELTA[1] + 2, R_VUELTA[1] + 20); C = (G2[0] + 6, G2[0] + 24)
def pose(f):
    p = {n: list(P0[n]) for n in huesos}
    w = ss((f - R_IDA[0]) / (R_IDA[1] - R_IDA[0])) * (1 - ss((f - R_VUELTA[0]) / (R_VUELTA[1] - R_VUELTA[0])))
    for n, v in ALCANCE.items():                                                           # ida y vuelta por SLERP (mezclar Euler eje por eje retuerce las articulaciones)
        qa = Euler(p[n], 'XYZ').to_quaternion(); qb = Euler(v, 'XYZ').to_quaternion()
        if qa.dot(qb) < 0: qb.negate()
        p[n] = list(qa.slerp(qb, w).to_euler('XYZ', Euler(p[n], 'XYZ')))
    if "Neck_alfred" in p: p["Neck_alfred"][0] += 0.15 * w                                       # mira la mano
    wc = ss((f - C[0]) / (C[1] - C[0]))
    for n, v in CINTURA.items():
        if n in p: p[n] = [p[n][i] + (near(p[n][i], v[i]) - p[n][i]) * wc for i in range(3)]
    return p
def rz(f):
    if f <= G1[1]: return RZ0 + (RZ1 - RZ0) * ss((f - G1[0]) / (G1[1] - G1[0]))
    return RZ1 + (RZ2 - RZ1) * ss((f - G2[0]) / (G2[1] - G2[0]))
def key(fc, f, v, interp='LINEAR'):
    k = fc.keyframe_points.insert(f, v); k.interpolation = interp
for fc in list(FA.values()) + list(FR.values()):
    for k in [k for k in fc.keyframe_points if k.co.x > T1 + 0.5][::-1]: fc.keyframe_points.remove(k)
for f in range(T1 + 1, FIN + 1):
    p = pose(f)
    for n in huesos:
        for i in range(3): key(FA[('pose.bones["%s"].rotation_euler' % n, i)], f, p[n][i])
    for i in range(3): key(FR[('location', i)], f, L0[i] if i else L0[0] + (X_FINAL - L0[0]) * ss((f - G2[0]) / (G2[1] - G2[0])))     # al girar hacia la cueva se aparta de la pared hasta X_FINAL
    key(FR[('rotation_euler', 2)], f, rz(f))
for d in (FA, FR):
    for fc in d.values(): fc.update()

# ---------------- antorcha de pared (copia de antorcha_1) ----------------
NOM = "antorcha_pared_parte8"
for o in [o for o in bpy.data.objects if o.name == NOM or (o.parent and o.parent.name == NOM)][::-1]: bpy.data.objects.remove(o, do_unlink=True)
src = bpy.data.objects["antorcha_1"]; col = src.users_collection[0]
emp = src.copy(); emp.name = NOM; col.objects.link(emp)
emp.matrix_world = Matrix.Translation(BASE_T) @ Euler((0, -INCL, 0), 'XYZ').to_matrix().to_4x4()       # la punta se inclina hacia -x (afuera de la pared)
objs = [emp]
for ch in src.children:
    c = ch.copy()
    if ch.type == 'LIGHT': c.data = ch.data.copy()
    col.objects.link(c); c.parent = emp; c.matrix_parent_inverse = ch.matrix_parent_inverse.copy(); objs.append(c)
for o in objs:
    if o.animation_data: o.animation_data_clear()
    for dp in ("hide_viewport", "hide_render"):
        setattr(o, dp, True); o.keyframe_insert(dp, frame=1); setattr(o, dp, False); o.keyframe_insert(dp, frame=APARECE)
        for fc in [c for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for c in cb.fcurves]:
            for k in fc.keyframe_points: k.interpolation = 'CONSTANT'
sc.frame_end = max(sc.frame_end, FIN)
print("Alfred: gira a 270 f%d-%d, brazo a la pared f%d-%d (error mano %.3f m), ANTORCHA en f%d, vuelve f%d-%d, gira a 90 (cueva) f%d-%d, manos en la cintura f%d-%d, hasta f%d" % (
    G1[0], G1[1], R_IDA[0], R_IDA[1], best2[0], APARECE, R_VUELTA[0], R_VUELTA[1], G2[0], G2[1], C[0], C[1], FIN))
