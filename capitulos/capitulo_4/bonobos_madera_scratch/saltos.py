# -*- coding: utf-8 -*-
# Animacion de salto del mono entre copas: preparacion (agacharse), impulso, vuelo con gravedad real y caida (amortiguacion).
import bpy, math, json
from mathutils import Vector

ns = {}
exec(open(r"C:\Users\user\AppData\Local\Temp\claude\C--Users-user-Desktop-Alfred-Animacion\593282e0-289f-4704-9bd2-cafc9b5be57b\scratchpad\lanzar.py", encoding='utf-8').read(), ns)
pose_mono, key_todo, mono, suf, yaw_hacia, dir_local, fcs = ns['pose_mono'], ns['key_todo'], ns['mono'], ns['suf'], ns['yaw_hacia'], ns['dir_local'], ns['fcs']
G_F = ns['G_F']
V = lambda x, y, z: Vector((x, y, z))
SC = bpy.context.scene
SPOTS = {1: (-75.5, 36.5, 19.0), 2: (-72.5, 22.5, 18.0), 3: (-77.5, 20.5, 16.0), 4: (-79.5, 35.5, 19.0), 5: (-70.5, 21.5, 18.0),
         6: (-76.5, 37.5, 21.0), 7: (-71.5, 20.5, 20.0)}
ALF = Vector((-77.6, 32.5, 13.5))


def asegurar_acciones(raiz, rig):
    for ob in (raiz, rig):
        ob.animation_data_create()
    if rig.animation_data.action is None:
        rig.animation_data.action = bpy.data.actions.new(rig.name + '_acc')
    if raiz.animation_data.action is None:
        raiz.animation_data.action = bpy.data.actions.new(raiz.name + '_root')


def yaw_prev(raiz, f):
    a = raiz.animation_data.action if raiz.animation_data else None
    if a:
        for c in fcs(a):
            if c.data_path == 'rotation_euler' and c.array_index == 2:
                return math.degrees(c.evaluate(f))
    return math.degrees(raiz.rotation_euler.z)


def cerca(y, ref):
    return ref + ((y - ref + 180.0) % 360.0 - 180.0)


def salto(i, J, T, a, b):
    raiz, rig = mono(i)
    S = suf(rig)
    asegurar_acciones(raiz, rig)
    A = Vector(SPOTS[a]); B = Vector(SPOTS[b])
    L = J + T
    y0 = yaw_prev(raiz, J - 12)
    yv = cerca(yaw_hacia(A, B), y0)                       # yaw de vuelo: mira al destino
    yf = cerca(yaw_hacia(B, ALF), yv)                      # yaw final: mira a Alfred
    vel = (B - A) / T
    vz0 = vel.z + 0.5 * G_F * T
    vh = math.hypot(vel.x, vel.y)
    th = max(math.radians(12), min(math.radians(62), math.atan2(vz0, vh)))
    vzL = vz0 - G_F * T
    thL = max(math.radians(-45), min(math.radians(40), math.atan2(vzL, vh)))
    s = -1
    Aa = lambda x, y, z: V(x * s, y, z)
    Bb = lambda x, y, z: V(-x * s, y, z)
    dd = dir_local(raiz, yv, B + V(0, 0, 1.0), A + V(0, 0, 1.0))
    HEAD = lambda c: V(dd.x * 0.7, 0.55, c + dd.z * 0.5)
    mir = (0.0, max(-1.0, min(1.0, dd.z * 2)))

    def brazos(La, Lf, Lh=None):
        d = dict(Lsh=Aa(0.95, 0.0, 0.1), La=Aa(*La), Lf=Aa(*Lf), Nsh=Bb(0.95, 0.0, 0.1), Na=Bb(*La), Nf=Bb(*Lf))
        return d

    def piernas(lg, ls, lo):
        return dict(lg=V(*lg), ls=V(*ls), lo=V(*lo), rg=V(*lg), rs=V(*ls), ro=V(*lo))

    poses = []
    poses.append((J - 12, A, y0, {}))
    poses.append((J - 9, A + V(0, 0, -0.10), yv, dict(body=V(0, 0.55, 0.85), cube_r1=V(0, 0.6, 0.8), head=HEAD(0.85), mira=mir, boca=0.2, ceno=0.5, orejas=0.4,
                                                  **brazos((0.35, -0.5, -0.8), (0.2, -0.6, -0.7)), **piernas((0, 0.7, -0.7), (0, -0.7, -0.6), (0, 0.2, -0.5)))))
    poses.append((J - 4, A + V(0, 0, -0.24), yv, dict(body=V(0, 0.8, 0.55), cube_r1=V(0, 0.85, 0.45), head=HEAD(0.7), mira=mir, boca=0.3, ceno=0.8, orejas=0.7,
                                                  **brazos((0.3, -0.8, -0.55), (0.2, -0.9, -0.4)), **piernas((0, 0.95, -0.4), (0, -0.95, -0.35), (0, 0.2, -0.5)))))
    poses.append((J, A, yv, dict(body=V(0, math.cos(th), math.sin(th)), cube_r1=V(0, math.cos(th), math.sin(th)), head=HEAD(0.8), mira=mir, boca=0.6, ceno=0.6, orejas=0.8,
                                 **brazos((0.25, 0.85, 0.5), (0.15, 0.95, 0.35)), **piernas((0, -0.45, -0.9), (0, -0.35, -0.95), (0, -0.1, -0.95)))))
    Mid = A.lerp(B, 0.5)
    poses.append((J + T // 2, None, yv, dict(body=V(0, 0.97, 0.25), cube_r1=V(0, 0.97, 0.2), head=HEAD(0.5), mira=mir, boca=0.5, ceno=0.5, orejas=0.6,
                                             **brazos((0.3, 0.9, 0.1), (0.2, 0.95, 0.05)), **piernas((0, 0.5, -0.8), (0, -0.7, -0.6), (0, 0.3, -0.4)))))
    poses.append((L - 6, None, yv, dict(body=V(0, 0.5, 0.85), cube_r1=V(0, 0.45, 0.9), head=HEAD(0.9), mira=mir, boca=0.3, ceno=0.4, orejas=0.5,
                                        **brazos((0.35, 0.8, -0.45), (0.3, 0.85, -0.5)), **piernas((0, 0.75, -0.65), (0, -0.4, -0.9), (0, 0.35, -0.7)))))
    poses.append((L, B + V(0, 0, -0.12), yv, dict(body=V(0, 0.65, 0.75), cube_r1=V(0, 0.7, 0.7), head=HEAD(0.8), mira=mir, boca=0.2, ceno=0.3, orejas=0.4,
                                                  **brazos((0.8, 0.4, -0.55), (0.7, 0.5, -0.6)), **piernas((0, 0.9, -0.45), (0, -0.9, -0.4), (0, 0.2, -0.5)))))
    poses.append((L + 4, B + V(0, 0, -0.24), yv, dict(body=V(0, 0.8, 0.55), cube_r1=V(0, 0.85, 0.45), head=HEAD(0.7), mira=mir, boca=0.1, ceno=0.2, orejas=0.2,
                                                      **brazos((0.6, 0.6, -0.7), (0.5, 0.65, -0.7)), **piernas((0, 0.95, -0.4), (0, -0.95, -0.35), (0, 0.2, -0.5)))))
    poses.append((L + 11, B, cerca(yv + 0.5 * (yf - yv), yv), dict(body=V(0, 0.2, 1), cube_r1=V(0, 0.1, 1), head=V(0, 0.4, 1), mira=mir,
                                                                **brazos((0.1, 0.1, -1), (0.05, 0.15, -1)), **piernas((0, 0.2, -1), (0, -0.2, -1), (0, 0.15, -0.5)))))
    poses.append((L + 16, B, yf, {}))
    for (f, pos, yaw, p) in poses:
        if pos is None:
            t = f - J
            pos = A + vel * t + V(0, 0, vz0 * t - 0.5 * G_F * t * t) - V(0, 0, vel.z * t)
        raiz.location = pos
        raiz.rotation_euler = (0, 0, math.radians(yaw))
        bpy.context.view_layer.update()
        pose_mono(rig, S, p, 'r')
        key_todo(raiz, rig, f)
    # vuelo: la raiz sigue la parabola (inercia: velocidad horizontal constante, gravedad real)
    for f in range(J + 1, L):
        t = f - J
        raiz.location = A + vel * t + V(0, 0, vz0 * t - 0.5 * G_F * t * t) - V(0, 0, vel.z * t)
        raiz.rotation_euler = (0, 0, math.radians(yv))
        raiz.keyframe_insert('location', frame=f)
        raiz.keyframe_insert('rotation_euler', frame=f)
    # los tramos de vuelo son lineales por frame; fuera, suave
    raiz.location = B
    return (L, B[:])
