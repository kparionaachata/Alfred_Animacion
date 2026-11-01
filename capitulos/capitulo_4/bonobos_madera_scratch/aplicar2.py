# -*- coding: utf-8 -*-
import bpy, math
from mathutils import Vector

p = r"C:\Users\user\AppData\Local\Temp\claude\C--Users-user-Desktop-Alfred-Animacion\593282e0-289f-4704-9bd2-cafc9b5be57b\scratchpad\lanzar.py"
ns = {}
exec(open(p, encoding='utf-8').read(), ns)
lanzar, mano_pos, fcs, G_F = ns['lanzar'], ns['mano_pos'], ns['fcs'], ns['G_F']
sc = bpy.context.scene
f_ini = sc.frame_current

ALFRED = Vector((-77.6, 32.5, 13.5))
# objeto, mono, frame de impacto, P1, azimut de llegada original (grados)
LANZ = [
    ('bm_apple_1', 3, 102, (-77.70, 32.37, 13.52), -133.7, 65),
    ('bm_stick_1', 7, 248, (-77.64, 32.49, 13.42), -26.3, 211),
    ('bm_stick_2', 0, 263, (-77.71, 34.00, 12.17), 89.7, 225),
    ('bm_stick_3', 7, 566, (-72.42, 32.48, 13.57), 5.4, 535),
    ('bm_stick_4', 6, 586, (-72.45, 32.47, 13.58), -14.9, 556),
    ('bm_stick_5', 1, 606, (-72.58, 32.54, 13.61), 12.6, 576),
    ('rat_1', 6, 804, (-73.01, 32.56, 12.74), 5.9, 756),
]
PICK = 20           # frames antes de soltar en que el mono recoge el objeto


def curvas(o, path):
    return sorted([c for c in fcs(o.animation_data.action) if c.data_path == path], key=lambda c: c.array_index)


def quitar_keys(c, a, b):
    for kp in reversed(list(c.keyframe_points)):
        if a <= kp.co[0] < b:
            c.keyframe_points.remove(kp)


def poner_key(c, f, v, interp='LINEAR'):
    kp = c.keyframe_points.insert(f, v, options={'FAST'})
    kp.interpolation = interp
    return kp


info = {}
# 1) animar los monos (todos los huesos)
for (nom, i, f1, P1, azo, R0) in LANZ:
    o = bpy.data.objects[nom]
    hide = [c for c in fcs(o.animation_data.action) if c.data_path == 'hide_viewport'][0]
    f0 = [k.co[0] for k in hide.keyframe_points if k.co[1] == 0][0]
    R = R0
    info[nom] = dict(f0=f0, R=R)
    lanzar(i, R, ALFRED)

# 2) sincronizar los objetos con las manos
for (nom, i, f1, P1, azo, R0) in LANZ:
    o = bpy.data.objects[nom]
    R = info[nom]['R']; f0 = info[nom]['f0']
    raiz, rig = ns['mono'](i)
    S = ns['suf'](rig)
    P1 = Vector(P1)
    L = curvas(o, 'location')
    # posicion original de todas las keys posteriores al impacto: guardar y girar despues
    # a) mano por frame desde la recogida hasta la suelta
    mano = {}
    for f in range(R - PICK, R + 1):
        sc.frame_set(f)
        mano[f] = Vector(mano_pos(rig, S, 'r'))
    p0 = mano[R]
    # b) vuelo con gravedad real de p0 (frame R) a P1 (frame f1)
    T = f1 - R
    v0 = (P1 - p0) / T
    v0.z += 0.5 * G_F * T
    vuelo = {}
    for f in range(R + 1, f1):
        t = f - R
        vuelo[f] = p0 + v0 * t - Vector((0, 0, 0.5 * G_F * t * t))
    # c) giro de la trayectoria posterior al impacto segun el nuevo azimut de llegada
    az_n = math.degrees(math.atan2(P1.y - p0.y, P1.x - p0.x))
    dth = math.radians(az_n - azo)
    co, si = math.cos(dth), math.sin(dth)
    info[nom].update(az_nuevo=round(az_n, 1), dtheta=round(math.degrees(dth), 1), T=T, p0=[round(x, 2) for x in p0])
    post = [(kx, ky) for kx, ky in zip(L[0].keyframe_points, L[1].keyframe_points) if kx.co[0] > f1 - 1e-6]
    for kx, ky in post:
        x, y = kx.co[1] - P1.x, ky.co[1] - P1.y
        nx, ny = x * co - y * si, x * si + y * co
        dx, dy = nx - x, ny - y
        for k, d in ((kx, dx), (ky, dy)):
            k.co[1] += d; k.handle_left[1] += d; k.handle_right[1] += d
    # d) quitar las keys antiguas del vuelo y poner las nuevas (mano -> vuelo)
    z_imp = None
    for c in L:
        quitar_keys(c, f0 - 0.01, f1 - 1e-6)
    for c in L:
        a = c.array_index
        for f in range(R - PICK, R + 1):
            poner_key(c, f, mano[f][a])
        for f, pt in vuelo.items():
            poner_key(c, f, pt[a])
        poner_key(c, f1, P1[a])
        c.update()
    # e) aparece en la mano al recogerlo
    for c in [c for c in fcs(o.animation_data.action) if c.data_path in ('hide_viewport', 'hide_render')]:
        for k in c.keyframe_points:
            if k.co[1] == 0:
                k.co[0] = R - PICK
        c.update()
sc.frame_set(f_ini)
result = info
