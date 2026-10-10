# -*- coding: utf-8 -*-
"""Parte 7: Alfred aparece despues del frame 130 corriendo por `recorridos/alfred_1.json`; en la ultima coordenada se le tuerce el tobillo derecho, cae al suelo y se soba el tobillo.
- Invisible hasta T_APARECE (130); visible desde T0 = T_APARECE + 1 ya corriendo en el punto 1.
- Correr = ciclo CORRER del estudio de Alfred (igual que la huida de la parte 6: ciclo 11 f, 6.2 f por bloque, brazos/piernas/rodillas/columna con los multiplicadores de CORRER).
- Tobillo + caida + sobarse: ver la seccion CAIDA (poses por cinematica directa/inversa de `docs/parte3/ik_brazos.py`).
Se ejecuta dentro de Blender:  exec(open(RUTA, encoding='utf-8').read()). Idempotente: borra lo que haya animado en Alfred antes de crear."""
import bpy, json, math
from mathutils import Euler, Matrix, Vector

T_APARECE = int(globals().get('T_APARECE', 130)); T0 = T_APARECE + 1
RUTA_JSON = r'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/parte7/recorridos/alfred_1.json'
sc = bpy.context.scene
EA = bpy.data.objects['alfred']; AA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.parent == EA)
PARTES = [o for o in bpy.data.objects if o.type == 'MESH' and (o.parent in (EA, AA) or any(m.type == 'ARMATURE' and m.object == AA for m in o.modifiers))] + [bpy.data.objects['stone_axe'], bpy.data.objects['stone_shovel']]
pts = [(k['coordinates']['x'], k['coordinates']['y'], k['coordinates']['z']) for k in json.load(open(RUTA_JSON))['key_points']]
D2R = math.pi / 180
ss = lambda x: 0.0 if x <= 0 else 1.0 if x >= 1 else x * x * (3 - 2 * x)

# ---------- limpiar lo que Alfred tenga animado (mallas, herramientas, root, armature) ----------
for o in [EA, AA] + PARTES:
    if o.animation_data and o.animation_data.action: o.animation_data.action = None
for a in [a for a in bpy.data.actions if a.users == 0 and not a.use_fake_user]: bpy.data.actions.remove(a)
NB = ["Hips_alfred", "Spine_alfred", "Spine1_alfred", "Spine2_alfred", "Neck_alfred", "RightUpArm_alfred", "Rightelbow_alfred", "LeftUpArm_alfred", "Leftelbow_alfred", "RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred"]
for b in AA.pose.bones: b.rotation_mode = 'XYZ'
PB = {n: AA.pose.bones[n] for n in NB}
H_LOC = Vector((0.029, 0.026, -0.197))                                      # ubicacion de la cadera de pie (la del estado base de la parte 6)
for n in NB: PB[n].rotation_euler = (0, 0, 0)
EA.rotation_euler = (EA.rotation_euler.x, EA.rotation_euler.y, 0.0); bpy.context.view_layer.update()
kr, kl = AA.matrix_world @ PB["Rightknee_alfred"].bone.tail_local, AA.matrix_world @ PB["Leftknee_alfred"].bone.tail_local
PIV = Vector(((kr.x + kl.x) / 2, (kr.y + kl.y) / 2, 0)); D0 = Vector((EA.location.x - PIV.x, EA.location.y - PIV.y, 0))   # origen del root respecto al punto entre los pies (rz = 0)

def key_rot(pb, f, v):
    pb.rotation_euler = v
    for ax in range(3): pb.keyframe_insert("rotation_euler", index=ax, frame=f, group=pb.name)
def key_hips_loc(f, v):
    PB["Hips_alfred"].location = v
    for ax in range(3): PB["Hips_alfred"].keyframe_insert("location", index=ax, frame=f, group="Hips_alfred")
def key_root(f, loc, rz):
    EA.location = loc; EA.rotation_euler = (EA.rotation_euler.x, EA.rotation_euler.y, rz); EA.keyframe_insert("location", frame=f); EA.keyframe_insert("rotation_euler", frame=f)

# ---------- CORRER del estudio de Alfred (copia de la huida de la parte 6) ----------
ST = dict(speed=0.5, cycle=0.55, arm_swing=1.6, elbow=1.7, leg=1.7, knee=1.8, spine=1.8, neck_tilt=0.6, arm_base=0.85, lean=0.12, bob=0.06)
FPU = (60.0 / 4.8284) * ST["speed"]; CICLO = 20.0 * ST["cycle"]; HALF = CICLO / 2.0
R = dict(arm_base_x=math.radians(90 * ST["arm_base"]), arm_swing_y=math.radians(70 * ST["arm_swing"]), elbow_flex=math.radians(50 * ST["elbow"]), leg_swing_x=math.radians(50 * ST["leg"]), knee_flex=math.radians(40 * ST["knee"]),
         hip_forward=math.radians(3), hip_sway=math.radians(4), hip_tilt=math.radians(4), spine_bend=math.radians(0.1 * ST["spine"]), neck_tilt=math.radians(1.5 * ST["neck_tilt"]), head_stab=0.25)
ease_s = lambda t: -(math.cos(math.pi * t) - 1) / 2
ease_c = lambda t: 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2
def leg_swing(ph): return R['leg_swing_x'] * math.sin(ph * 2 * math.pi)
def arm_swing(ph):
    m = R['arm_swing_y']; return ease_s(ph / 0.5) * m * 2 - m if ph < 0.5 else m - ease_s((ph - 0.5) / 0.5) * m * 2
def elbow(ph):
    m = R['elbow_flex']
    if ph < 0.3: return ease_s(ph / 0.3) * m * 0.85 + m * 0.15
    if ph < 0.7: return m - ease_c((ph - 0.3) / 0.4) * m * 0.6
    return m * 0.4 - ease_s((ph - 0.7) / 0.3) * m * 0.25
def knee(ph): return R['knee_flex'] * max(0.0, math.sin((ph - 0.75) * 2 * math.pi))
def pose_run(wc):
    sf = math.sin(wc * 2 * math.pi + math.pi / 6) * R['spine_bend'] + ST["lean"]; st = math.cos(wc * 2 * math.pi + math.pi / 3) * R['spine_bend'] * 0.75
    hf = -sf * 0.3 + R['hip_forward'] * math.sin(wc * 2 * math.pi); hs = math.sin(wc * 2 * math.pi + math.pi / 4) * R['hip_sway']; ht = math.sin(wc * 2 * math.pi) * R['hip_tilt']
    nf = -sf * R['head_stab']; nt = math.sin(wc * 2 * math.pi) * R['neck_tilt']; ns = math.cos(wc * 2 * math.pi + math.pi / 4) * R['neck_tilt'] * 0.5
    rc = (wc + 0.5) % 1.0; ra = (wc + 0.25) % 1.0; la = (wc + 0.75) % 1.0
    return {"Hips_alfred": (hf, hs, ht), "Spine_alfred": (sf, 0, st), "Spine1_alfred": (sf, 0, st), "Spine2_alfred": (sf, 0, st), "Neck_alfred": (nf, ns, nt),
            "LeftUpLeg_alfred": (leg_swing(wc), 0, 0), "Leftknee_alfred": (-knee(wc), 0, 0), "RightUpLeg_alfred": (leg_swing(rc), 0, 0), "Rightknee_alfred": (-knee(rc), 0, 0),
            "RightUpArm_alfred": (R['arm_base_x'], arm_swing(ra), 0), "Rightelbow_alfred": (0, 0, -elbow(ra)), "LeftUpArm_alfred": (R['arm_base_x'], -arm_swing(la), 0), "Leftelbow_alfred": (0, 0, elbow(la))}

dist = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))
n_half = max(1, round(dist * FPU / HALF)); TOT = max(1, round(n_half * HALF)); WC = TOT / CICLO; E = T0 + TOT          # E = frame en que llega a la ultima coordenada
def pos_en(u):                                                               # u en [0,1] a lo largo del recorrido (velocidad constante)
    d = u * dist; acc = 0.0
    for i in range(len(pts) - 1):
        L = math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        if d <= acc + L or i == len(pts) - 2:
            f = min(1.0, max(0.0, (d - acc) / L)); return tuple(pts[i][c] + (pts[i + 1][c] - pts[i][c]) * f for c in range(3))
        acc += L

key_hips_loc(T0, tuple(H_LOC))
for t in range(T0, E + 1):
    u = (t - T0) / max(1, E - T0); p = pos_en(u); wc = u * WC; bob = ST["bob"] * (0.5 - 0.5 * math.cos(wc * 4 * math.pi))
    key_root(t, (p[0] + D0.x, p[1] + D0.y, p[2] + bob), 0.0)
    for n, v in pose_run(wc).items(): key_rot(PB[n], t, v)

# ---------- CAIDA (tobillo, caida, sobarse): se anade abajo ----------
FIN = E
exec(open(r'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/parte7/alfred_tobillo_caida.py', encoding='utf-8').read()) if __import__('os').path.isfile(r'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/parte7/alfred_tobillo_caida.py') else None

# ---------- aparecer: oculto hasta T_APARECE ----------
for o in PARTES:
    for atr in ('hide_viewport', 'hide_render'):
        setattr(o, atr, True); o.keyframe_insert(atr, frame=1); setattr(o, atr, False); o.keyframe_insert(atr, frame=T0)       # oculto hasta T_APARECE (interpolacion constante)
def curvas(a): return [fc for l in a.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]
for o in [EA, AA] + PARTES:
    if o.animation_data and o.animation_data.action:
        for fc in curvas(o.animation_data.action):
            const = fc.data_path.startswith('hide')
            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT' if const else 'LINEAR'
for a in [a for a in bpy.data.actions if a.users == 0 and not a.use_fake_user]: bpy.data.actions.remove(a)
sc.frame_end = max(sc.frame_end, FIN + 10); sc.frame_set(T0)
print('Alfred: visible desde f', T0, '| llega a la ultima coordenada en f', E, '| fin de la toma f', FIN, '| recorrido', round(dist, 1), 'bloques,', TOT, 'f')
