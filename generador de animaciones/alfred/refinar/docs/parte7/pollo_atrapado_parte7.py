# -*- coding: utf-8 -*-
"""Parte 7: el pollo es cogido por el cuello por la mano derecha de Alfred (f427), lo lanza al creeper (suelta en f437, golpe en la cara en f440), REBOTA, sale disparado en sentido contrario y se ESTRELLA DE ESPALDAS contra el tronco
(f456) con las alas extendidas (pose `recorridos/pollo/de espalda contra la pared.json`), se queda pegado un momento, se desliza LENTAMENTE hacia abajo por el tronco (caricatura) hasta el suelo y CAE BOCA ABAJO
(con la misma pose de huesos), rebota contra el suelo de la cintura para arriba, y SE QUEDA ASI, inmovil, hasta el final del video. Requiere `pollo_parte7.py` (el pollo idle hasta f427) y `alfred_tira_pollo_parte7.py` (la mano de Alfred); se ejecuta dentro de Blender. Idempotente (borra sus claves >= f428).
- f427-437: colgado de la mano derecha (el cuello en la mano; la mano se muestrea de la escena), aleteando con los frames aereos de `saltar_bajar.py` (panico), girando hacia el creeper (rz 0 -> 180).
- f437-440: vuelo hasta la cara del creeper. f440-456: rebote hacia +y por una parabola de 16 f hasta el punto de choque (centro del pollo en (-109.5, cara del tronco, 18.5)), con dos vueltas de campana que terminan antes del choque;
  en el ultimo tramo la pose de aleteo pasa a la pose del JSON (de espaldas, alas extendidas) y la espalda toca la cara del tronco (y = -82, calculada con un rayo; el pollo mira a -y, hacia el creeper).
- f456-(456+H_HOLD): pegado al tronco. Despues N_SLIDE f deslizandose hacia abajo (suave, lento) hasta que los pies tocan el suelo (z 16); H_SUELO f quieto, 8 f cayendo hacia delante (gira sobre los pies, aceleracion), rebote de la cintura para arriba (38, 14 y 4 grados en 6+4+3 f: el cuerpo gira sobre la cintura, las patas quedan en el suelo), y queda tumbado, inmovil, hasta frame_end."""
import bpy, ast, math, json
from mathutils import Vector, Matrix, Euler

D = 'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/parte7/recorridos/pollo/'
T_GRAB, T_REL, T_IMP, T_WALL = 427, 437, 440, 456
H_HOLD = int(globals().get('H_HOLD', 12)); N_SLIDE = int(globals().get('N_SLIDE', 72)); H_SUELO = 6; N_LEVANTA = 10
WALL_X, WALL_Z = -109.5, 18.5                                                   # punto marcado en el tronco (centro del pollo al chocar)
sc = bpy.context.scene
ss = lambda x: 0.0 if x <= 0 else 1.0 if x >= 1 else x * x * (3 - 2 * x)
TAU = 2 * math.pi
ROOT = bpy.data.objects['chicken_1']; ARM = bpy.data.objects['Armature_chicken_1']
EA = bpy.data.objects['alfred']; AA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.parent == EA)
CR = bpy.data.objects['creeper_1']; CA = bpy.data.objects['creeper.arma_creeper_1']
def curvas(o): return [fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]
for o in (ROOT, ARM):
    for fc in curvas(o):
        for i in range(len(fc.keyframe_points) - 1, -1, -1):
            if fc.keyframe_points[i].co.x >= T_GRAB + 1: fc.keyframe_points.remove(fc.keyframe_points[i])

# ---------- animaciones del usuario y pose de espaldas contra la pared ----------
def leer(nombre):
    t = ast.parse(open(D + nombre + '.py', encoding='utf-8').read())
    return [ast.literal_eval(n.value) for n in t.body if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == 'KEYFRAME_DATA'][0]
ACC = {n: leer(n) for n in ('saltar_bajar', 'picotear', 'rascar')}
JP = json.load(open(D + 'de espalda contra la pared.json', encoding='utf-8'))['poses'][0]['bones']
WP_R = {b: tuple(JP[b]['local_space']['rotation_euler_rad'][c] for c in 'xyz') for b in JP if b in ARM.pose.bones}
WP_L = {b: tuple(JP[b]['local_space']['location'][c] for c in 'xyz') for b in JP if b in ARM.pose.bones}
HUESOS = sorted(({b for a in ACC.values() for b in a} | {b for b in WP_R if any(abs(v) > 1e-3 for v in WP_R[b])}) & {b.name for b in ARM.pose.bones})
LOCB = [b for b in WP_L if any(abs(v) > 1e-3 for v in WP_L[b])]                 # huesos con traslacion en la pose (escapulas y caderas)
WALL = {b: WP_R.get(b, (0.0, 0.0, 0.0)) for b in HUESOS}
def pose_de(acc, f, suave):
    out = {}
    for b in HUESOS:
        ks = ACC[acc].get(b)
        if not ks: out[b] = (0.0, 0.0, 0.0); continue
        fr = sorted(ks); f2 = min(max(f, fr[0]), fr[-1]); i = max(j for j in range(len(fr)) if fr[j] <= f2); j = min(i + 1, len(fr) - 1)
        u = 0.0 if j == i else (f2 - fr[i]) / float(fr[j] - fr[i]); u = ss(u) if suave else u
        out[b] = tuple(ks[fr[i]][c] + (ks[fr[j]][c] - ks[fr[i]][c]) * u for c in range(3))
    return out
def pose_aleteo(k):                                                            # aleteo desesperado: frames aereos 15..22 de `saltar_bajar.py`, ida y vuelta cada 6 f
    return pose_de('saltar_bajar', 15 + 7 * abs(((k % 6) / 3.0) - 1.0), False)
def pose_idle(n):                                                              # bucle de picotear x3 y rascar (como en pollo_parte7.py)
    n = n % 144; return pose_de('picotear', 1 + (n % 24), True) if n < 72 else pose_de('rascar', 1 + (n - 72), True)
def mezcla(pa, pb, w):                                                         # mezcla de dos poses por cuaternion (los angulos grandes no se deforman)
    return {b: tuple(Euler(pa[b], 'XYZ').to_quaternion().slerp(Euler(pb[b], 'XYZ').to_quaternion(), w).to_euler('XYZ', Euler(pa[b], 'XYZ'))) for b in HUESOS}
CERO = (0.0, 0.0, 0.0)

# ---------- datos de la escena: mano de Alfred, cara del creeper, suelo, tronco ----------
def mano(f):
    sc.frame_set(f); bpy.context.view_layer.update(); return AA.matrix_world @ AA.pose.bones['Rightelbow_alfred'].tail
sc.frame_set(T_GRAB); bpy.context.view_layer.update()
neck_h = ARM.matrix_world @ ARM.pose.bones['Neck_M_chicken_1'].head; neck_t = ARM.matrix_world @ ARM.pose.bones['Neck_M_chicken_1'].tail; root0 = Vector(ROOT.location); pose0 = {b: tuple(ARM.pose.bones[b].rotation_euler) for b in HUESOS}
G0 = (neck_h + (neck_t - neck_h) * 0.6) - root0                                # donde esta el punto de agarre en el cuello al agarrarlo (picoteando)
G1 = Vector((0.0, 0.14, 0.65))                                                  # punto de agarre con el pollo colgado y estirado (local)
H = {f: mano(f) for f in range(T_GRAB, T_REL + 1)}
sc.frame_set(T_IMP); bpy.context.view_layer.update()
ch, ct = CA.matrix_world @ CA.pose.bones['head_creeper_1'].head, CA.matrix_world @ CA.pose.bones['head_creeper_1'].tail
CARA = (ch + ct) / 2 + Vector((0, 0.30, 0))                                    # centro de la cara del creeper (el frente mira a +y)
dg = bpy.context.evaluated_depsgraph_get()
def suelo(x, y, defecto=15.0):
    ok, loc, n, i, ob, m = sc.ray_cast(dg, Vector((x, y, 18.5)), Vector((0, 0, -1)))
    return loc.z if ok and loc.z < 17.9 and ob is not None and ob.name not in ('Stone',) else defecto
ok, loc, n, i, ob, m = sc.ray_cast(dg, Vector((WALL_X, -86.0, WALL_Z)), Vector((0, 1, 0)))
WALL_Y = loc.y if ok and ob is not None and ob.name == 'Birch_Log' else -82.0   # cara del tronco (normal -y)

# ---------- colocacion de la pose de espaldas: el pollo mira a -y y su espalda toca el tronco ----------
guard = ({b.name: (tuple(b.rotation_euler), tuple(b.location)) for b in ARM.pose.bones}, tuple(ROOT.location), tuple(ROOT.rotation_euler))
for b in ARM.pose.bones: b.rotation_euler = WALL.get(b.name, CERO); b.location = WP_L.get(b.name, CERO)
ROOT.location = (0, 0, 0); ROOT.rotation_euler = (0, 0, math.pi); bpy.context.view_layer.update(); dg2 = bpy.context.evaluated_depsgraph_get()
MN = Vector((1e9,) * 3); MX = Vector((-1e9,) * 3)
for o in ARM.children_recursive:
    if o.type == 'MESH':
        ev = o.evaluated_get(dg2)
        for c in ev.bound_box:
            w = ev.matrix_world @ Vector(c)
            for k in range(3): MN[k] = min(MN[k], w[k]); MX[k] = max(MX[k], w[k])
for n_, (r_, l_) in guard[0].items(): ARM.pose.bones[n_].rotation_euler = r_; ARM.pose.bones[n_].location = l_
ROOT.location = guard[1]; ROOT.rotation_euler = guard[2]
W0 = Vector((WALL_X - (MN.x + MX.x) / 2, (WALL_Y - 0.01) - MX.y, WALL_Z - (MN.z + MX.z) / 2))    # origen del pollo al chocar (centro de la pose en el punto marcado, espalda a 1 cm del tronco)
PIES = MN.z                                                                    # altura de los pies respecto al origen del pollo en esa pose
SUELO = suelo(W0.x, W0.y); ZG = SUELO - PIES                                    # origen del pollo cuando los pies tocan el suelo al deslizarse

# ---------- trayectorias ----------
frames = {}; locs = {}                                                          # f -> (posicion root, (rx, ry, rz) en radianes, pose); f -> {hueso: traslacion}
Rz = lambda a: Matrix.Rotation(a, 3, 'Z')
for f in range(T_GRAB, T_REL + 1):                                              # colgado de la mano
    u = (f - T_GRAB) / float(T_REL - T_GRAB); rzf = math.pi * ss((f - T_GRAB - 2) / float(T_REL - T_GRAB - 2)); G = G0 + (G1 - G0) * ss((f - T_GRAB) / 4.0)
    pos = H[f] - Rz(rzf) @ G; w = ss((f - T_GRAB) / 3.0); pa = pose_aleteo(f - T_GRAB)
    pose = {b: tuple(pose0[b][c] * (1 - w) + pa[b][c] * w for c in range(3)) for b in HUESOS}
    frames[f] = (pos, (0.0, 0.0, rzf), pose)
p_rel = frames[T_REL][0]; hit = Vector((CARA.x, CARA.y + 0.2, CARA.z - 0.40))
for f in range(T_REL + 1, T_IMP + 1):                                           # vuelo hasta la cara
    u = (f - T_REL) / float(T_IMP - T_REL); pos = p_rel + (hit - p_rel) * u + Vector((0, 0, 0.12 * math.sin(math.pi * u)))
    frames[f] = (pos, (0.0, 0.0, math.pi), pose_aleteo(f - T_GRAB))
RXF = 2 * TAU                                                                   # rx tras las dos vueltas (720 grados = de pie): se mantiene para no deshacer la vuelta entre claves
T = T_WALL - T_IMP; ARCO = 2.0                                                  # rebote: parabola de T f desde la cara hasta el tronco (arco de 2 m sobre la recta)
for f in range(T_IMP + 1, T_WALL + 1):
    t = f - T_IMP; u = t / float(T); pos = hit + (W0 - hit) * u + Vector((0, 0, 4 * ARCO * u * (1 - u)))
    ur = min(1.0, u / 0.78); rx = RXF * (1 - (1 - ur) ** 2)                 # dos vueltas de campana hacia atras que terminan (rx = 720 grados) antes del choque
    w = ss((u - 0.55) / 0.45); frames[f] = (pos, (rx, 0.0, math.pi), mezcla(pose_aleteo(f - T_GRAB), WALL, w))
    locs[f] = {b: tuple(WP_L[b][c] * w for c in range(3)) for b in LOCB}
F_HOLD = T_WALL + H_HOLD; F_G = F_HOLD + N_SLIDE
for f in range(T_WALL + 1, F_HOLD + 1):                                         # pegado al tronco
    frames[f] = (Vector(W0), (RXF, 0.0, math.pi), dict(WALL)); locs[f] = {b: WP_L[b] for b in LOCB}
for f in range(F_HOLD + 1, F_G + 1):                                            # resbala hacia abajo, lento (suave)
    e = ss((f - F_HOLD) / float(N_SLIDE)); frames[f] = (Vector((W0.x, W0.y, W0.z + (ZG - W0.z) * e)), (RXF, 0.0, math.pi), dict(WALL)); locs[f] = {b: WP_L[b] for b in LOCB}
def zmin_en(rx, pose, loc, x, y):                                              # z minimo de las mallas (vertices evaluados) con el origen del pollo a z = 0
    for b in HUESOS: ARM.pose.bones[b].rotation_euler = pose[b]
    for b in LOCB: ARM.pose.bones[b].location = loc.get(b, CERO)
    ROOT.location = (x, y, 0.0); ROOT.rotation_euler = (rx, 0.0, math.pi); bpy.context.view_layer.update()
    dg3 = bpy.context.evaluated_depsgraph_get(); zm = 1e9
    for o in ARM.children_recursive:
        if o.type == 'MESH':
            ev = o.evaluated_get(dg3); mw = ev.matrix_world
            for v in ev.data.vertices: zm = min(zm, (mw @ v.co).z)
    return zm
WLOC = {b: WP_L[b] for b in LOCB}
F_S0 = F_G + H_SUELO; T_TIP = 8; F_LAND = F_S0 + T_TIP; PY = W0.y - 0.30
for f in range(F_G + 1, F_S0 + 1): frames[f] = (Vector((W0.x, W0.y, ZG)), (RXF, 0.0, math.pi), dict(WALL)); locs[f] = dict(WLOC)
for f in range(F_S0 + 1, F_LAND + 1):                                           # cae hacia delante (boca abajo) pivotando sobre los pies, aceleracion de gravedad, con la MISMA pose de huesos
    rx = RXF - (math.pi / 2) * ((f - F_S0) / float(T_TIP)) ** 2
    frames[f] = (Vector((W0.x, W0.y, SUELO - zmin_en(rx, WALL, WLOC, W0.x, W0.y))), (rx, 0.0, math.pi), dict(WALL)); locs[f] = dict(WLOC)
RXL = RXF - math.pi / 2; L_POS = Vector(frames[F_LAND][0])                      # tumbado boca abajo
ROOT.location = L_POS; ROOT.rotation_euler = (RXL, 0.0, math.pi); bpy.context.view_layer.update()
CAD = (ARM.matrix_world @ ARM.pose.bones['Hip_R_chicken_1'].head + ARM.matrix_world @ ARM.pose.bones['Hip_L_chicken_1'].head) / 2      # articulacion de la cintura (bisagra del rebote)
PIV = Vector((CAD.x, CAD.y, SUELO)); Rxw = lambda a: Matrix.Rotation(a, 3, 'X')
f = F_LAND
for dur, ang in ((6, 38.0), (4, 14.0), (3, 4.0)):                               # rebote contra el suelo SOLO de la cintura para arriba: el cuerpo gira sobre la cintura (el pecho y la cabeza suben), las patas se quedan en el suelo
    for k in range(1, dur + 1):
        th = math.radians(ang) * math.sin(math.pi * k / dur)
        frames[f + k] = (PIV + Rxw(-th) @ (L_POS - PIV), (RXL + th, 0.0, math.pi), dict(WALL)); locs[f + k] = dict(WLOC)
    f += dur
F_REST = f + 8; FIN_TOTAL = max(sc.frame_end, F_REST + 1)
frames[F_REST] = (Vector(L_POS), (RXL, 0.0, math.pi), dict(WALL)); locs[F_REST] = dict(WLOC)               # se queda tumbado boca abajo, sin moverse, hasta el final del video
frames[FIN_TOTAL] = (Vector(L_POS), (RXL, 0.0, math.pi), dict(WALL)); locs[FIN_TOTAL] = dict(WLOC)
prev = dict(pose0)                                                              # angulos continuos (sin saltos de 360 grados entre frames)
for f in sorted(frames):
    pose = frames[f][2]
    for b in HUESOS: pose[b] = tuple(v + TAU * round((prev[b][c] - v) / TAU) for c, v in enumerate(pose[b])); prev[b] = pose[b]

# ---------- claves ----------
def key_rot(pb, f, v):
    pb.rotation_euler = v
    for ax in range(3): pb.keyframe_insert('rotation_euler', index=ax, frame=f, group=pb.name)
def key_loc(pb, f, v):
    pb.location = v
    for ax in range(3): pb.keyframe_insert('location', index=ax, frame=f, group=pb.name)
for b in LOCB:                                                                  # ancla en cero hasta el agarre (sin esto la traslacion se extenderia hacia atras)
    key_loc(ARM.pose.bones[b], 1, CERO); key_loc(ARM.pose.bones[b], T_GRAB, CERO)
for f in sorted(frames):
    if f == T_GRAB: continue                                                    # f427 ya tiene la clave del bucle de picoteo
    pos, rot, pose = frames[f]; ROOT.location = pos; ROOT.rotation_euler = rot; ROOT.keyframe_insert('location', frame=f); ROOT.keyframe_insert('rotation_euler', frame=f)
    for b in HUESOS: key_rot(ARM.pose.bones[b], f, pose[b])
    for b in LOCB: key_loc(ARM.pose.bones[b], f, locs.get(f, {}).get(b, CERO))
for o in (ROOT, ARM):
    for fc in curvas(o):
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
sc.frame_set(T_GRAB)
print("Pollo atrapado: colgado f%d-%d, vuelo f%d-%d, rebota f%d-%d y choca de espaldas contra el tronco (y=%.2f) en (%.2f, %.2f, %.2f), pegado hasta f%d, resbala hasta f%d (suelo z %.2f), cae boca abajo f%d-%d, rebota hasta f%d y queda tumbado hasta f%d; frame_end %d" % (T_GRAB, T_REL, T_REL, T_IMP, T_IMP, T_WALL, WALL_Y, W0.x, W0.y, W0.z, F_HOLD, F_G, SUELO, F_S0, F_LAND, F_LAND + 13, FIN_TOTAL, sc.frame_end))
print("cara del creeper (impacto):", [round(v, 2) for v in CARA], "| bbox de la pose (origen en 0, rz 180):", [round(v, 2) for v in MN], [round(v, 2) for v in MX])
