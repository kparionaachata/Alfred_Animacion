# -*- coding: utf-8 -*-
"""Parte 7: a partir de T0 (f384) Alfred (sentado, girado 180 grados, tras sobarse el tobillo) levanta la cabeza, ve que de frente se acerca el creeper y entra en PANICO FRENETICO: abre los brazos RECTOS a los lados y los agita desesperado de arriba hacia abajo (vista frontal) y
busca con la cabeza a toda velocidad de izquierda a derecha. TODOS los movimientos rapidos usan ELASTIC IN-OUT (la funcion `ela` de los sustos de la parte 6, `creeper_susto_y_huida.py`).
- Parte de la pose que Alfred tiene en T0-1 (la ultima de `alfred_corre_tobillo_parte7.py`, quieta de f295 a f347) y NO toca nada anterior a T0. Variable `T0` (384); el panico dura hasta FIN_SUSTO (419).
- T0..T0+3 (f384-387): levanta la cabeza de golpe (cuello X 34 -> -6 grados) y endereza el torso, elastico (3 f).
- T0+2..T0+9 (f386-393): abre los brazos hacia los lados (IK de `docs/parte3/ik_brazos.py`, muñecas a ~0.8 m a cada lado a la altura del hombro) con elastico en 7 f, y el torso se echa hacia atras (elastico).
- T0+10..FIN: ALETEO desesperado de los brazos (de la altura del hombro a ~0.5 m por encima, ciclos de 6 f, cada medio ciclo con elastico, brazos desfasados 1.5 f) y temblor del torso, la cadera y el cuello.
- T0+8..FIN (f392-419): barridos de cabeza de 6 f cada uno con elastico: izquierda (+60) <-> derecha (-60), amplitud decreciente (+-35 al final), con giro del torso; el aleteo y el temblor se atenuan en los ultimos 8 f; la animacion termina en f419 (FIN_SUSTO), porque desde f420 Alfred coge al pollo.
Se ejecuta dentro de Blender: exec(open(RUTA, encoding='utf-8').read()). Idempotente (borra sus claves >= T0 de Alfred antes de crear; antes de T0 Alfred sigue sobando el tobillo)."""
import bpy, math
from mathutils import Euler, Quaternion, Vector

T0 = int(globals().get('T0', 384))                                          # frame en que empieza la animacion
FIN = int(globals().get('FIN_SUSTO', 419))                                  # el panico termina en f419: a partir de f420 Alfred coge al pollo (`alfred_tira_pollo_parte7.py`)
AMP = float(globals().get('AMP', 0.25))                                     # amplitud del panico (barridos de cabeza, aleteo, retroceso del torso y temblores): 1 = original, 0.5 = la mitad, 0.25 = un cuarto
CENTRO = float(globals().get('CENTRO', 12.0))                                   # angulo (grados sobre la horizontal) de los brazos abiertos, centro del aleteo
ARCO = float(globals().get('ARCO', 33.0))                                        # semi-amplitud del aleteo de los brazos en grados (de CENTRO-ARCO a CENTRO+ARCO)
Dg = math.radians
sc = bpy.context.scene
exec(open(r'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/parte3/ik_brazos.py', encoding='utf-8').read(), globals())     # fk, mundo, resolver, AA, OO
EA = OO
ss = lambda x: 0.0 if x <= 0 else 1.0 if x >= 1 else x * x * (3 - 2 * x)
def ela(t):                                                                  # ELASTIC in-out (como creeper_susto_y_huida.py)
    if t <= 0: return 0.0
    if t >= 1: return 1.0
    c5 = (2 * math.pi) / 4.5
    return -(2 ** (20 * t - 10) * math.sin((20 * t - 11.125) * c5)) / 2 if t < 0.5 else (2 ** (-20 * t + 10) * math.sin((20 * t - 11.125) * c5)) / 2 + 1
def qint(q0, q1, u):                                                         # interpolacion por eje-angulo que permite u fuera de [0,1] (el elastico se pasa de 1)
    d = q0.rotation_difference(q1); ax, an = d.to_axis_angle(); return q0 @ Quaternion(ax, an * u) if an > 1e-9 else q0.copy()

# ---------- borrar claves propias anteriores (>= f296) y leer la pose de T0-1 ----------
act = AA.animation_data.action
for fc in [fc for l in act.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]:
    for i in range(len(fc.keyframe_points) - 1, -1, -1):
        if fc.keyframe_points[i].co.x >= T0: fc.keyframe_points.remove(fc.keyframe_points[i])
sc.frame_set(T0 - 1); bpy.context.view_layer.update()
BON = ["Hips_alfred", "Spine_alfred", "Spine1_alfred", "Spine2_alfred", "Neck_alfred", "RightUpArm_alfred", "Rightelbow_alfred", "LeftUpArm_alfred", "Leftelbow_alfred", "RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred"]
PB = {n: AA.pose.bones[n] for n in BON}
R0 = {n: tuple(PB[n].rotation_euler) for n in BON}; H0 = tuple(PB["Hips_alfred"].location); rt = tuple(EA.location); rz = EA.rotation_euler.z
R3 = Matrix.Rotation(rz, 3, 'Z'); FWD, DER, IZQ, ARR = R3 @ Vector((0, 1, 0)), R3 @ Vector((1, 0, 0)), R3 @ Vector((-1, 0, 0)), Vector((0, 0, 1))

# ---------- poses objetivo ----------
SP = ("Spine_alfred", "Spine1_alfred", "Spine2_alfred")
sp0 = R0["Spine_alfred"][0]; neck0 = R0["Neck_alfred"]; hips0 = R0["Hips_alfred"]
SP_ERGUIDO = Dg(6.0); SP_RETRO = SP_ERGUIDO + Dg(-16.0) * AMP; NECK_ARRIBA = Dg(-6.0)
A0 = {l: (Euler(R0[l + "UpArm_alfred"], 'XYZ').to_quaternion(), Euler(R0[l + "elbow_alfred"], 'XYZ').to_quaternion()) for l in ("Right", "Left")}
QE = Quaternion((1, 0, 0, 0))                                                # codo estirado (sin rotacion)
Mw = mundo(rt, rz)
def qdir(l, M, d):                                                           # rotacion del hombro para que el brazo ESTIRADO apunte a la direccion mundo d (el hueso apunta a su eje Y)
    Rsp = REST["Spine2_alfred"][0]; Rup = REST[l + "UpArm_alfred"][0]; A = (Mw @ (M["Spine2_alfred"] @ (Rsp.inverted() @ Rup))).to_3x3()
    dl = A.inverted() @ Vector(d); dl.normalize(); return Vector((0, 1, 0)).rotation_difference(dl)

# ---------- claves ----------
def key_rot(pb, f, v):
    pb.rotation_euler = v
    for ax in range(3): pb.keyframe_insert("rotation_euler", index=ax, frame=f, group=pb.name)
prev = {}
def euler_compat(n, q, ref):
    e = q.to_euler('XYZ', prev.get(n, Euler(ref, 'XYZ'))); prev[n] = e; return tuple(e)
# barridos de cabeza: (frame relativo a T0, Neck Y en grados; + = su izquierda); 6 f por barrido
BARRIDOS = [(8, 0.0), (14, 60.0), (20, -60.0), (26, 60.0), (32, -60.0), (38, 55.0), (44, -55.0), (50, 50.0), (56, -50.0), (62, 45.0), (68, -45.0), (74, 35.0), (80, 0.0)]
for n in BON: key_rot(PB[n], T0 - 1, R0[n])                                  # ancla: hasta T0-1 todo igual
for f in range(T0, FIN + 1):
    r = f - T0
    uU = ela((r + 1) / 4.0); uA = ela((r - 1) / 8.0) if r >= 2 else 0.0   # cabeza arriba (3 f) y brazos abiertos (7 f), elasticos
    fade = ss((r - 8) / 3.0) * (1.0 - ss((r - (FIN - T0 - 8)) / 8.0))                    # intensidad del panico (entra en T0+8, se atenua T0+78..96)
    rot = {n: list(R0[n]) for n in BON}
    sp = sp0 + (SP_ERGUIDO - sp0) * uU
    if r >= 2: sp = SP_ERGUIDO + (SP_RETRO - SP_ERGUIDO) * uA                 # retroceso del torso (elastico)
    sp += Dg(2.5) * AMP * math.sin(2 * math.pi * r / 4.0) * fade                     # temblor del torso
    for s in SP: rot[s][0] = sp
    rot["Hips_alfred"][2] = hips0[2] + Dg(2.0) * AMP * math.sin(2 * math.pi * r / 5.0 + 0.7) * fade
    rot["Neck_alfred"][0] = neck0[0] + (NECK_ARRIBA - neck0[0]) * uU + Dg(7.0) * AMP * math.sin(2 * math.pi * r / 6.0 + 1.0) * fade   # cabeceos rapidos al buscar
    if r >= 8:                                                                # barridos de cabeza con elastico
        k = max(i for i in range(len(BARRIDOS)) if BARRIDOS[i][0] <= r); k2 = min(k + 1, len(BARRIDOS) - 1)
        u = ela((r - BARRIDOS[k][0]) / float(max(1, BARRIDOS[k2][0] - BARRIDOS[k][0]))); yaw = Dg(BARRIDOS[k][1] + (BARRIDOS[k2][1] - BARRIDOS[k][1]) * u) * AMP
        rot["Neck_alfred"][1] = neck0[1] + yaw; rot["Spine2_alfred"][1] = 0.30 * yaw; rot["Spine1_alfred"][1] = 0.12 * yaw
    for n in BON:
        if "Arm" in n or "elbow" in n: continue
        key_rot(PB[n], f, tuple(rot[n]))
    Mf = fk(rot, {"Hips_alfred": H0}); fl = 0.0                              # aleteo en el plano frontal: brazos RECTOS que oscilan de arriba hacia abajo, simetricos (como alas)
    if r >= 10: ph = ((r - 10 + 1.5) % 6.0) / 6.0; tri = ela(2 * ph) if ph < 0.5 else ela(2 * (1 - ph)); fl = (2 * tri - 1) * fade      # medio ciclo de 3 f con elastico
    th = Dg(CENTRO) + Dg(ARCO) * fl                                          # angulo sobre la horizontal
    for l in ("Right", "Left"):
        q0, qe0 = A0[l]; d = (DER if l == "Right" else IZQ) * math.cos(th) + ARR * math.sin(th); qd = qdir(l, Mf, d)
        qa = qint(q0, qd if q0.dot(qd) >= 0 else -qd, uA); ea = qint(qe0, QE if qe0.dot(QE) >= 0 else -QE, uA)        # abrir los brazos (elastico) y estirar el codo
        key_rot(PB[l + "UpArm_alfred"], f, euler_compat(l + "u", qa, R0[l + "UpArm_alfred"])); key_rot(PB[l + "elbow_alfred"], f, euler_compat(l + "e", ea, R0[l + "elbow_alfred"]))
for fc in [fc for l in act.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]:
    for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
sc.frame_end = max(sc.frame_end, FIN)
sc.frame_set(T0 - 1)
print("Alfred PANICO: cabeza arriba f%d-%d, brazos f%d-%d, aleteo f%d-%d, barridos de cabeza f%d-%d, fin f%d" % (T0, T0 + 3, T0 + 2, T0 + 9, T0 + 10, T0 + 90, T0 + 8, T0 + 80, FIN))
