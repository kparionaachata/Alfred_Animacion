# -*- coding: utf-8 -*-
"""Parte 7: despues de levantarse (f524) Alfred se acerca COJEANDO, con curiosidad y precaucion, a ver como esta el creeper tumbado e inconsciente (huella del creeper: x -108.82..-108.18, y -90.06..-88.05).
- Camina por una curva corta (de (-108.5, -85.6) a (-109.8, -89.0), al lado oeste del creeper) con el ciclo de CAMINAR del estudio de Alfred (`generate_caminar`: 20 f por ciclo, brazos 90 grados, columna, cuello...) pero LENTO (24 f por ciclo, un paso cada 12 f)
  y COJEANDO del tobillo derecho: la pierna derecha oscila poco (35 %) y flexiona poco la rodilla, la izquierda (sana) mas (60 %), brazos con poco balanceo y el cuerpo baja un poco al apoyar la derecha.
- Gestos (se hacen con el ciclo parado en una pose simetrica de pasos, con sus pesos suaves de 6 f):
  tres pasos -> PAUSA 'alerta' (se echa un poco hacia atras, antebrazos arriba en guardia, cabeza gacha que mira a los lados) -> cinco pasos seguidos con la cabeza gacha (sin retroceder)
  -> siempre con el cuerpo orientado a la cara del creeper (rz = rumbo a (-108.5, -89.7)); al llegar se queda 'mirando' (se inclina hacia delante, cabeza gacha que se ladea de un lado a otro con curiosidad) y mantiene esa pose.
Parte de la pose de f524 (la ultima de `alfred_se_levanta_cojeando_parte7.py`) y borra sus claves >= f525. Se ejecuta dentro de Blender: exec(open(RUTA, encoding='utf-8').read())."""
import bpy, math
from mathutils import Vector, Euler, Matrix

sc = bpy.context.scene
exec(open(r'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/parte3/ik_brazos.py', encoding='utf-8').read(), globals())     # fk, mundo, REST, AA, OO
EA = OO
T_STAND = 524; T0 = int(globals().get('T_ACERCA', 525)); BLEND = 6
NB = ["Hips_alfred", "Spine_alfred", "Spine1_alfred", "Spine2_alfred", "Neck_alfred", "RightUpArm_alfred", "Rightelbow_alfred", "LeftUpArm_alfred", "Leftelbow_alfred", "RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred"]
PB = {n: AA.pose.bones[n] for n in NB}
ss = lambda x: 0.0 if x <= 0 else 1.0 if x >= 1 else x * x * (3 - 2 * x)
Dg = math.radians
cerca = lambda ref, v: v + 2 * math.pi * round((ref - v) / (2 * math.pi))
H_LOC = Vector((0.029, 0.026, -0.197))                                     # cadera de pie (la de la marcha del estudio en este rig)

# ---------- pose de partida (f524) ----------
sc.frame_set(T_STAND); bpy.context.view_layer.update()
BASE = {n: tuple(PB[n].rotation_euler) for n in NB}; BASE_H = Vector(PB["Hips_alfred"].location); ROOT0 = Vector(EA.location); RZ0 = EA.rotation_euler.z
rx, ry = EA.rotation_euler.x, EA.rotation_euler.y

# ---------- camino ----------
PATH = [Vector(v) for v in ((ROOT0.x, ROOT0.y, ROOT0.z), (-108.95, -86.80, ROOT0.z), (-109.55, -88.00, ROOT0.z), (-109.80, -89.00, ROOT0.z))]
SEG = [(PATH[i + 1] - PATH[i]).length for i in range(len(PATH) - 1)]; LTOT = sum(SEG)
def en_camino(d):
    d = min(max(d, 0.0), LTOT); acc = 0.0
    for i, L in enumerate(SEG):
        if d <= acc + L or i == len(SEG) - 1: f = (d - acc) / L; return PATH[i].lerp(PATH[i + 1], min(1.0, max(0.0, f)))
        acc += L
def rumbo(d):                                                              # rz (Alfred mira a +y con rz 0): hacia donde va, suavizado
    a = en_camino(d - 0.25); b = en_camino(d + 0.25); v = b - a
    return -math.atan2(v.x, v.y)
LOOK = Vector((-108.5, -89.7, 15.5))                                       # cara del creeper tumbado: Alfred SIEMPRE mira hacia ahi mientras se acerca (el cuerpo gira con la posicion)
def mira_a(p, prev):                                                        # rz con el que Alfred (mira a +y con rz 0) mira al creeper desde p, continuo con el valor anterior
    rz = -math.atan2(LOOK.x - p.x, LOOK.y - p.y); return rz + 2 * math.pi * round((prev - rz) / (2 * math.pi))
# D0: desplazamiento del root respecto al punto entre los pies con la cadera de pie (rz = 0)
M0 = fk({}, {"Hips_alfred": tuple(H_LOC)}); Mw0 = mundo((0, 0, 0), 0.0)
tails = [Mw0 @ (M0[n] @ Vector((0, REST[n][2], 0))) for n in ("Rightknee_alfred", "Leftknee_alfred")]; D0 = Vector((-(tails[0].x + tails[1].x) / 2, -(tails[0].y + tails[1].y) / 2, 0.0))

# ---------- ciclo de caminar del estudio (lento y cojeando) ----------
R = dict(arm_base_x=Dg(90), arm_swing_y=Dg(70) * 0.4, elbow_flex=Dg(50) * 0.6, leg_swing_x=Dg(50), knee_flex=Dg(40), hip_forward=Dg(3), hip_sway=Dg(4), hip_tilt=Dg(4), spine_bend=Dg(0.1), neck_tilt=Dg(1.5), head_stab=0.25)
LS, RS, RK = 0.60, 0.35, 0.5                                               # oscilacion de la pierna izquierda (sana) y derecha (tobillo), flexion de la rodilla derecha
ease_s = lambda t: -(math.cos(math.pi * t) - 1) / 2
ease_c = lambda t: 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2
def leg_swing(ph, k): return R['leg_swing_x'] * k * math.sin(ph * 2 * math.pi)
def arm_swing(ph):
    m = R['arm_swing_y']
    return ease_s(ph / 0.5) * m * 2 - m if ph < 0.5 else m - ease_s((ph - 0.5) / 0.5) * m * 2
def elbow(ph):
    m = R['elbow_flex']
    if ph < 0.3: return ease_s(ph / 0.3) * m * 0.85 + m * 0.15
    if ph < 0.7: return m - ease_c((ph - 0.3) / 0.4) * m * 0.6
    return m * 0.4 - ease_s((ph - 0.7) / 0.3) * m * 0.25
def knee(ph, k=1.0): return R['knee_flex'] * k * max(0.0, math.sin((ph - 0.75) * 2 * math.pi))
def pose_walk(wc):
    sf = math.sin(wc * 2 * math.pi + math.pi / 6) * R['spine_bend'] + Dg(7); st = math.cos(wc * 2 * math.pi + math.pi / 3) * R['spine_bend'] * 0.75     # columna algo inclinada hacia delante (cuidado)
    hf = -sf * 0.3 + R['hip_forward'] * math.sin(wc * 2 * math.pi); hs = math.sin(wc * 2 * math.pi + math.pi / 4) * R['hip_sway']; ht = math.sin(wc * 2 * math.pi) * R['hip_tilt'] * 1.4
    nf = -sf * R['head_stab'] + Dg(10); nt = math.sin(wc * 2 * math.pi) * R['neck_tilt']; ns = math.cos(wc * 2 * math.pi + math.pi / 4) * R['neck_tilt'] * 0.5      # cabeza gacha
    rc = (wc + 0.5) % 1.0; ra = (wc + 0.25) % 1.0; la = (wc + 0.75) % 1.0
    return {"Hips_alfred": (hf, hs, ht), "Spine_alfred": (sf, 0, st), "Spine1_alfred": (sf, 0, st), "Spine2_alfred": (sf, 0, st), "Neck_alfred": (nf, ns, nt),
            "LeftUpLeg_alfred": (leg_swing(wc, LS), 0, 0), "Leftknee_alfred": (-knee(wc, 0.8), 0, 0), "RightUpLeg_alfred": (leg_swing(rc, RS), 0, 0), "Rightknee_alfred": (-knee(rc, RK), 0, 0),
            "RightUpArm_alfred": (R['arm_base_x'], arm_swing(ra), 0), "Rightelbow_alfred": (0, 0, -elbow(ra)), "LeftUpArm_alfred": (R['arm_base_x'], -arm_swing(la), 0), "Leftelbow_alfred": (0, 0, elbow(la))}
def bob_limp(wc):                                                          # el cuerpo baja un poco al apoyar la pierna derecha (la mala) y casi no sube al apoyar la izquierda
    return -0.045 * max(0.0, math.sin((wc + 0.5) * 2 * math.pi + math.pi / 2)) + 0.012 * math.sin(wc * 4 * math.pi)

# ---------- gestos (aditivos, con peso w y tiempo tt en frames desde el inicio de la pausa) ----------
def gesto(kind, w, tt):
    g = {n: [0.0, 0.0, 0.0] for n in NB}
    if kind == 'alerta':                                                   # se echa atras, guardia con los antebrazos, mira a los lados con la cabeza gacha
        for s in ("Spine_alfred", "Spine1_alfred", "Spine2_alfred"): g[s][0] = -Dg(4) * w
        g["Neck_alfred"][0] = Dg(8) * w; g["Neck_alfred"][1] = Dg(1.5) * w * math.sin(2 * math.pi * tt / 14.0)
        g["Leftelbow_alfred"][2] = Dg(45) * w; g["Rightelbow_alfred"][2] = -Dg(45) * w
        g["Hips_alfred"][0] = -Dg(2) * w
    elif kind == 'mira':                                                   # se inclina sobre el creeper, cabeza gacha que se ladea con curiosidad
        for s in ("Spine_alfred", "Spine1_alfred", "Spine2_alfred"): g[s][0] = Dg(8) * w
        g["Neck_alfred"][0] = Dg(8) * w; g["Neck_alfred"][2] = Dg(1.5) * w * math.sin(2 * math.pi * tt / 18.0); g["Neck_alfred"][1] = -Dg(0.3) * w * math.sin(2 * math.pi * tt / 18.0 + 0.8)       # oscilaciones de la cabeza al minimo (+-1.5 y +-0.3 grados; antes +-16 / +-3)
        g["Leftelbow_alfred"][2] = Dg(20) * w; g["Rightelbow_alfred"][2] = -Dg(20) * w
    return g

# ---------- guion: (tipo, valor): 'pasos' n con signo, 'pausa' frames + gesto ----------
STEP_F = 12; BACK_F = 10; RAMP = 18                                       # RAMP: frames que tarda en pasar de parado a la marcha cojeando (pose, amplitud del paso y velocidad)
SEGS = [('pasos', 3), ('pausa', 14, 'alerta'), ('pasos', 5), ('pausa', 40, 'mira')]
NET = sum(sg[1] for sg in SEGS if sg[0] == 'pasos'); STEP_L = LTOT / NET
frames = []; wc = 0.0; stp = 0.0                                           # wc: fase del ciclo (un paso = 0.5), stp: pasos netos hechos
for sg in SEGS:
    if sg[0] == 'pasos':
        n = abs(sg[1]); d = 1 if sg[1] > 0 else -1; per = STEP_F if d > 0 else BACK_F; tgt = n * 0.5; acc = 0.0
        while acc < tgt - 1e-9:                                            # la velocidad del ciclo y del avance arranca de cero y sube suave durante los primeros RAMP frames (arrancar a caminar cojeando)
            v = ss((len(frames) + 1) / float(RAMP)) if len(frames) < RAMP else 1.0; inc = min(tgt - acc, 0.5 / per * v); acc += inc; wc += d * inc; stp += d * inc * 2.0
            frames.append(dict(wc=wc, stp=stp, kind=None, w=0.0, tt=0))
    else:
        dur, kind = sg[1], sg[2]
        for k in range(dur): w = min(ss((k + 1) / 6.0), ss((dur - k) / 6.0) if kind != 'mira' else 1.0); frames.append(dict(wc=wc, stp=stp, kind=kind, w=w, tt=k))
# ---------- claves ----------
act = AA.animation_data.action
for fc in [fc for l in act.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]:
    for i in range(len(fc.keyframe_points) - 1, -1, -1):
        if fc.keyframe_points[i].co.x >= T0: fc.keyframe_points.remove(fc.keyframe_points[i])
if EA.animation_data and EA.animation_data.action:
    for fc in [fc for l in EA.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]:
        for i in range(len(fc.keyframe_points) - 1, -1, -1):
            if fc.keyframe_points[i].co.x >= T0: fc.keyframe_points.remove(fc.keyframe_points[i])
def key_rot(pb, f, v):
    pb.rotation_euler = v
    for ax in range(3): pb.keyframe_insert("rotation_euler", index=ax, frame=f, group=pb.name)
def key_hips(f, v):
    PB["Hips_alfred"].location = v
    for ax in range(3): PB["Hips_alfred"].keyframe_insert("location", index=ax, frame=f, group="Hips_alfred")
def key_root(f, loc, rz):
    EA.location = loc; EA.rotation_euler = (rx, ry, rz); EA.keyframe_insert("location", frame=f); EA.keyframe_insert("rotation_euler", frame=f)
t = T0 - 1; key_root(t, tuple(ROOT0), RZ0); key_hips(t, tuple(BASE_H))
for n in NB: key_rot(PB[n], t, BASE[n])
W0 = pose_walk(0.0); RZ_W0 = mira_a(PATH[0], RZ0)
W0E = {n: tuple(cerca(BASE[n][c], W0[n][c]) for c in range(3)) for n in NB}
TA = T0; prev_rz = RZ_W0
for i, fr in enumerate(frames):
    t = TA + i; p = en_camino(fr['stp'] * STEP_L); rz = mira_a(p, prev_rz); prev_rz = rz
    wb = ss((i + 1) / float(RAMP)); A = wb                                    # wb: de la pose de pie (f524) a la pose base de la marcha; A: amplitud de oscilacion del paso (0 -> 1) alrededor de esa pose base
    pw = pose_walk(fr['wc']); g = gesto(fr['kind'], fr['w'], fr['tt']) if fr['kind'] else None
    bob = bob_limp(fr['wc']) * A
    vals = {n: tuple(BASE[n][c] + (W0E[n][c] - BASE[n][c]) * wb + A * (pw[n][c] - W0[n][c]) + (g[n][c] if g else 0.0) for c in range(3)) for n in NB}
    if fr['kind'] == 'alerta': bob -= 0.02 * fr['w']
    Do = (Matrix.Rotation(rz, 3, 'Z') @ D0) * wb                               # el desplazamiento del root respecto a los pies de la marcha entra gradualmente (en f524 el root ya esta bien colocado: sin salto)
    key_root(t, (p.x + Do.x, p.y + Do.y, p.z + bob), rz); key_hips(t, tuple(BASE_H.lerp(H_LOC, wb)))
    for n in NB: key_rot(PB[n], t, vals[n])
T_FIN = TA + len(frames) - 1
for fc in [fc for l in act.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves] + ([fc for l in EA.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves] if EA.animation_data and EA.animation_data.action else []):
    for kp in fc.keyframe_points:
        if kp.co.x >= T0 - 1: kp.interpolation = 'LINEAR'
sc.frame_end = max(sc.frame_end, T_FIN)
sc.frame_set(T0 - 1)
print("Alfred se acerca cojeando: f%d-%d | %d pasos netos de %.2f m (camino %.2f m) | pausas: %s | siempre mirando al creeper, rz final %.0f" % (T0, T_FIN, NET, STEP_L, LTOT, [(sg[2], sg[1]) for sg in SEGS if sg[0] == 'pausa'], math.degrees(prev_rz)))
