# -*- coding: utf-8 -*-
"""Parte 7: desde el frame 1 hay un pollo (`chicken_1`) indiferente a lo que pasa: salta para bajar el bloque, camina por su recorrido, picotea las flores, rasca el suelo...
Recorrido: `recorridos/pollo/Chicken_1.json` (12 puntos; el punto 1 esta sobre un bloque, z 16). Animaciones del usuario (en `recorridos/pollo/`): `saltar_bajar.py` (33 f), `caminar.py` (ciclo de 40 f, 1 bloque cada 41 f),
`picotear.py` (24 f) y `rascar.py` (72 f); se leen con `ast` (KEYFRAME_DATA / ROOT_LOCATION_DATA) y se aplican sobre el rig `Armature_chicken_1` / root `chicken_1` (importado de `estructura_lista/chicken_1.blend` si falta).
Secuencia (SECUENCIA): salta P1 -> P2 | camina P2 -> P6 (junto a las amapolas) | picotea x2 | camina P6 -> P8 (junto a los dientes de leon) | picotea x3 | camina P8 -> P12 (llega en T_LLEGA = f410) | picotea y rasca en bucle hasta el final (FIN_TOTAL). Entre animaciones la pose se mezcla en 6 f.
El pollo mira a +y con rz 0 (rz = -atan2(dx, dy)); suavizado de giros de 8 f. Se ejecuta dentro de Blender: exec(open(RUTA, encoding='utf-8').read()). Idempotente."""
import bpy, ast, json, math
from mathutils import Vector

D = 'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/parte7/recorridos/pollo/'
S = int(globals().get('S', 1)); BLEND = 6; CICLO = 40; T_LLEGA = int(globals().get('T_LLEGA', 410))      # T_LLEGA: frame en que llega a la ultima coordenada (punto 12)
sc = bpy.context.scene
ss = lambda x: 0.0 if x <= 0 else 1.0 if x >= 1 else x * x * (3 - 2 * x)

# ---------- importar el pollo si falta ----------
if 'chicken_1' not in bpy.data.objects:
    with bpy.data.libraries.load(r'C:\Users\user\Desktop\Alfred_Animacion\estructura_lista\chicken_1.blend', link=False) as (src, dst): dst.objects = list(src.objects)
    col = bpy.data.collections.new('chicken_1'); sc.collection.children.link(col)
    for o in dst.objects:
        if o is not None: col.objects.link(o)
ROOT = bpy.data.objects['chicken_1']; ARM = bpy.data.objects['Armature_chicken_1']
for o in (ROOT, ARM):
    if o.animation_data and o.animation_data.action: o.animation_data.action = None
for a in [a for a in bpy.data.actions if a.users == 0 and not a.use_fake_user]: bpy.data.actions.remove(a)
for b in ARM.pose.bones: b.rotation_mode = 'XYZ'

# ---------- leer las animaciones del usuario ----------
def leer(nombre):
    t = ast.parse(open(D + nombre + '.py', encoding='utf-8').read()); r = {}
    for n in t.body:
        if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') in ('KEYFRAME_DATA', 'ROOT_LOCATION_DATA'): r[n.targets[0].id] = ast.literal_eval(n.value)
    return r
ACC = {n: leer(n) for n in ('saltar_bajar', 'caminar', 'picotear', 'rascar')}
HUESOS = sorted({b for a in ACC.values() for b in a['KEYFRAME_DATA']} & {b.name for b in ARM.pose.bones})
DENSAS = {'saltar_bajar', 'caminar'}                                          # keys en (casi) todos los frames: interpolacion lineal; las demas (pocas claves): suavizada

def pose_de(acc, f):
    """pose (dict hueso -> euler) de la accion `acc` en el frame local f (1-based, fraccion permitida)."""
    kd = ACC[acc]['KEYFRAME_DATA']; out = {}
    for b in HUESOS:
        ks = kd.get(b)
        if not ks: out[b] = (0.0, 0.0, 0.0); continue
        fr = sorted(ks); f = min(max(f, fr[0]), fr[-1])
        i = max(j for j in range(len(fr)) if fr[j] <= f); j = min(i + 1, len(fr) - 1)
        u = 0.0 if j == i else (f - fr[i]) / float(fr[j] - fr[i]); u = u if acc in DENSAS else ss(u)
        out[b] = tuple(ks[fr[i]][c] + (ks[fr[j]][c] - ks[fr[i]][c]) * u for c in range(3))
    return out

# ---------- recorrido ----------
pts = [(k['coordinates']['x'], k['coordinates']['y'], k['coordinates']['z']) for k in json.load(open(D + 'Chicken_1.json', encoding='utf-8'))['key_points']]
P = lambda i: pts[i - 1]                                                      # puntos 1-based como en el .json
def largo(i, j): return sum(math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]) for k in range(i - 1, j - 1))
SECUENCIA = [('saltar', 1, 2), ('caminar', 2, 6), ('picotear', 2), ('caminar', 6, 8), ('picotear', 3), ('caminar', 8, 12), ('idle',)]                  # al llegar al ultimo punto sigue picoteando y rascando hasta el final de la linea de tiempo (nunca queda quieto)
IDLE = [('picotear', 3), ('rascar',)]; FIN_TOTAL = int(globals().get('FIN_TOTAL', max(sc.frame_end, 435)))        # sobre todo picotea (el rascado de `rascar.py` mueve solo la pata derecha y parece que esta parado)

# ---------- velocidad de la caminata para llegar al ultimo punto en T_LLEGA (las demas animaciones conservan su duracion) ----------
def dur_accion(it): return {'saltar': max(ACC['saltar_bajar']['KEYFRAME_DATA']['Root_M_chicken_1']), 'picotear': max(ACC['picotear']['KEYFRAME_DATA']['Root_M_chicken_1']) * (it[1] if it[0] == 'picotear' else 1), 'rascar': max(ACC['rascar']['KEYFRAME_DATA']['Root_M_chicken_1'])}[it[0]]
ult_cam = max(i for i, it in enumerate(SECUENCIA) if it[0] == 'caminar')
fijas = sum(dur_accion(it) for i, it in enumerate(SECUENCIA) if it[0] != 'caminar' and i < ult_cam)               # saltar + picoteos + rascar antes de la llegada
largo_tot = sum(largo(it[1], it[2]) for it in SECUENCIA if it[0] == 'caminar'); W_TOT = T_LLEGA - S + 1 - fijas
BLOQUE_F = W_TOT / largo_tot; TASA = 41.0 / BLOQUE_F                         # frames por bloque al caminar y velocidad de reproduccion del ciclo (1 = la de caminar.py)
_ex = [largo(it[1], it[2]) * BLOQUE_F for it in SECUENCIA if it[0] == 'caminar']; _n = [int(math.floor(x)) for x in _ex]
for k in sorted(range(len(_ex)), key=lambda k: -(_ex[k] - _n[k]))[:W_TOT - sum(_n)]: _n[k] += 1
N_CAM = iter(_n)

# ---------- linea de tiempo: para cada frame, (accion, frame local, posicion, rumbo objetivo) ----------
estados = []; t = S; rumbo = None; pos = Vector(P(1))
def rz_de(a, b): return -math.degrees(math.atan2(b[0] - a[0], b[1] - a[1]))
for it in SECUENCIA:
    tipo = it[0]
    if tipo == 'saltar':
        p0, p1 = Vector(P(it[1])), Vector(P(it[2])); rz = rz_de(p0, p1); dur = max(ACC['saltar_bajar']['KEYFRAME_DATA']['Root_M_chicken_1'])
        rl = ACC['saltar_bajar']['ROOT_LOCATION_DATA']; ks = sorted(rl)
        def loc_rl(f):
            f = min(max(f, ks[0]), ks[-1]); i = max(j for j in range(len(ks)) if ks[j] <= f); j = min(i + 1, len(ks) - 1)
            u = 0.0 if j == i else (f - ks[i]) / float(ks[j] - ks[i]); return tuple(rl[ks[i]][c] + (rl[ks[j]][c] - rl[ks[i]][c]) * u for c in range(3))
        d = (p1 - p0); d.z = 0; d.normalize()
        for k in range(dur):
            ly, lz = loc_rl(1 + k)[1], loc_rl(1 + k)[2]; q = p0 + d * ly; q.z = p1.z + lz
            estados.append(('saltar_bajar', 1 + k, q, rz)); t += 1
        pos = p1.copy(); rumbo = rz
    elif tipo == 'caminar':
        i, j = it[1], it[2]; segs = list(range(i - 1, j - 1)); n_f = next(N_CAM); acum = [0.0]
        for k in segs: acum.append(acum[-1] + math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]))
        for k in range(n_f):
            s = (k + 1) / float(n_f) * acum[-1]; sg = next((m for m in range(len(segs)) if s <= acum[m + 1] + 1e-9), len(segs) - 1)
            a, b = Vector(pts[segs[sg]]), Vector(pts[segs[sg] + 1]); u = (s - acum[sg]) / max(1e-9, acum[sg + 1] - acum[sg]); q = a + (b - a) * u
            estados.append(('caminar', (k * TASA) % CICLO + 1, q, rz_de(a, b))); t += 1
        pos = Vector(P(j))
    elif tipo == 'idle':                                                      # acciones de campo en bucle hasta FIN_TOTAL
        k_ = 0
        while t <= FIN_TOTAL:
            sub = IDLE[k_ % len(IDLE)]; acc = 'picotear' if sub[0] == 'picotear' else 'rascar'; reps = sub[1] if sub[0] == 'picotear' else 1; dur = max(ACC[acc]['KEYFRAME_DATA']['Root_M_chicken_1'])
            for r in range(reps):
                for kk in range(dur):
                    if t > FIN_TOTAL: break
                    estados.append((acc, 1 + kk, pos.copy(), None)); t += 1
            k_ += 1
    else:                                                                     # accion de campo en un punto (picotear / rascar)
        acc = 'picotear' if tipo == 'picotear' else 'rascar'; reps = it[1] if tipo == 'picotear' else 1; dur = max(ACC[acc]['KEYFRAME_DATA']['Root_M_chicken_1'])
        for r in range(reps):
            for k in range(dur): estados.append((acc, 1 + k, pos.copy(), None)); t += 1
FIN = S + len(estados) - 1

# ---------- escribir claves ----------
def key_rot(pb, f, v):
    pb.rotation_euler = v
    for ax in range(3): pb.keyframe_insert('rotation_euler', index=ax, frame=f, group=pb.name)
rz_ini = estados[0][3]; sm_t0 = None; sm_r0 = None; sm_tg = None; rz_act = rz_ini; prev_pose = None; ult_acc = None; t_acc = S; base_prev = None
for n, (acc, fl, q, rzt) in enumerate(estados):
    f = S + n
    # rumbo suavizado (8 f) hacia el objetivo del tramo; en las acciones de campo se mantiene
    if rzt is not None:
        dif = (rzt - rz_act + 180) % 360 - 180
        if abs(dif) < 0.5: rz_act = rzt; sm_t0 = None
        else:
            if sm_t0 is None or abs(((rzt - sm_tg + 180) % 360) - 180) > 0.5: sm_t0, sm_r0, sm_tg = f, rz_act, rzt
            u = ss((f - sm_t0 + 1) / 8.0); rz_act = sm_r0 + ((sm_tg - sm_r0 + 180) % 360 - 180) * u
    ROOT.location = (q.x, q.y, q.z); ROOT.rotation_euler = (0, 0, math.radians(rz_act)); ROOT.keyframe_insert('location', frame=f); ROOT.keyframe_insert('rotation_euler', frame=f)
    # pose: al cambiar de animacion se mezcla durante 6 f desde la ultima pose hacia la nueva
    if acc != ult_acc: t_acc = f; base_prev = dict(prev_pose) if prev_pose is not None else {h: (0.0, 0.0, 0.0) for h in HUESOS}
    actual = pose_de(acc, fl)
    if f - t_acc < BLEND:
        w = ss((f - t_acc + 1) / float(BLEND)); actual = {h: tuple(base_prev[h][c] * (1 - w) + actual[h][c] * w for c in range(3)) for h in HUESOS}
    for h in HUESOS: key_rot(ARM.pose.bones[h], f, actual[h])
    prev_pose = actual; ult_acc = acc
def curvas(a): return [fc for l in a.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]
for o in (ROOT, ARM):
    for fc in curvas(o.animation_data.action):
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
sc.frame_end = max(sc.frame_end, FIN)
sc.frame_set(S)
print('caminar: %.1f f por bloque (reproduccion del ciclo x%.2f); llega al punto 12 en f%d' % (BLOQUE_F, TASA, T_LLEGA)); print('Pollo: f%d-f%d (%d f) | acciones:' % (S, FIN, len(estados)), [(a, sum(1 for e in estados if e[0] == a)) for a in ('saltar_bajar', 'caminar', 'picotear', 'rascar')], '| huesos animados:', len(HUESOS))
