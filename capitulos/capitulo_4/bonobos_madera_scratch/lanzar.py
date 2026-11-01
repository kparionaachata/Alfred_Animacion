# -*- coding: utf-8 -*-
# Animacion de lanzamiento de los 8 monos adultos (todos sus huesos) sincronizada con los objetos lanzados.
import bpy, math
from mathutils import Vector, Matrix, Quaternion, Euler

SC = bpy.context.scene
G_F = 9.81 / 24.0 ** 2
ALFRED_PECHO = Vector((-77.6, 32.5, 13.5))
V = lambda x, y, z: Vector((x, y, z))


def fcs(a):
    return [c for l in a.layers for s in l.strips for b in s.channelbags for c in b.fcurves]


def mono(i):
    n = 'bonobo_adulto_1' if i == 0 else 'bonobo_adulto_1.%03d' % i
    raiz = bpy.data.objects[n]
    rig = [o for o in raiz.children if o.type == 'ARMATURE'][0]
    return raiz, rig


def suf(rig):
    return '_' + [b.name for b in rig.data.bones if b.name.startswith('head_')][0][5:]


def apuntar(rig, hueso, d):
    pb = rig.pose.bones[hueso]
    pb.rotation_mode = 'XYZ'
    pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    M = pb.matrix.copy()
    head = M.translation.copy()
    q0 = M.to_quaternion()
    y = (q0 @ Vector((0, 1, 0))).normalized()
    d = Vector(d).normalized()
    q = y.rotation_difference(d) @ q0
    pb.matrix = Matrix.LocRotScale(head, q, Vector((1, 1, 1)))
    pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()


def reset(rig):
    for pb in rig.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()


def yaw_hacia(p, q):
    return math.degrees(math.atan2(q[1] - p[1], q[0] - p[0])) - 90.0


def dir_local(raiz, yaw_deg, hacia, desde):
    """direccion (en el espacio del armature, sin yaw) de 'desde' a 'hacia'"""
    d = Vector(hacia) - Vector(desde)
    Rz = Matrix.Rotation(math.radians(-yaw_deg), 3, 'Z')
    return (Rz @ d).normalized()


# ---- poses (direcciones locales: x izquierda del mono, y adelante, z arriba). lado 'r' = brazo derecho lanza ----
def pose_mono(rig, S, p, lado):
    """p: dict con direcciones de huesos y valores de cara; deja la pose puesta (sin keys)"""
    reset(rig)
    L = lado
    LA = 'right' if L == 'r' else 'left'
    NA = 'left' if L == 'r' else 'right'
    s = -1 if L == 'r' else 1                       # signo x del lado que lanza
    for h in ('body', 'cube_r1', 'head'):
        if p.get(h) is not None:
            apuntar(rig, h + S, p[h])
    for (h, k) in (('shoulder', 'sh'), ('arm', 'a'), ('forearm', 'f'), ('hand', 'h')):
        for lad, pref in ((LA, 'L'), (NA, 'N')):
            d = p.get(pref + k)
            if d is not None:
                apuntar(rig, lad + h + S, d)
    for lad, pref in (('left', 'l'), ('right', 'r')):
        for h, k in (('leg', 'g'), ('shin', 's'), ('foot', 'o')):
            d = p.get(pref + k)
            if d is not None:
                apuntar(rig, lad + h + S, d)
    # cara
    pbs = rig.pose.bones
    boca = p.get('boca', 0.0)                        # 0..1 abierta (oh)
    pbs['mouth' + S].location = (0, 0.016 * boca, -0.088 * boca)
    pbs['mouthup' + S].location = (0, 0.016 * boca, 0.0)
    for lad in ('left', 'right'):
        sg = 1 if lad == 'left' else -1
        pbs[lad + 'mouth' + S].location = (-0.012 * sg * boca, 0, 0)          # comisuras se juntan al hacer la o
        pbs[lad + 'brow_in' + S].location = (0, 0, -0.03 * p.get('ceno', 0.0))   # cejas bajan (ceno)
        pbs[lad + 'brow_out' + S].location = (0, 0, 0.012 * p.get('ceno', 0.0))
        pbs[lad + 'ear' + S].rotation_euler = (math.radians(-18 * p.get('orejas', 0.0)), 0, math.radians(sg * 12 * p.get('orejas', 0.0)))
        ojo = p.get('ojo', 0.0)                                                # ojos se abren/entrecierran
        pbs[lad + 'eye' + S].scale = (1, 1, 1 + 0.0 * ojo)
        mir = p.get('mira')                                                    # (dx, dz) pupilas hacia el objetivo
        if mir is not None:
            pbs[lad + 'pupil' + S].location = (mir[0] * 0.012, 0, mir[1] * 0.012)
    pbs['nose' + S].location = (0, 0, 0.006 * p.get('ceno', 0.0))
    bpy.context.view_layer.update()


def key_todo(raiz, rig, f):
    for pb in rig.pose.bones:
        pb.keyframe_insert('location', frame=f, group=pb.name)
        pb.keyframe_insert('rotation_euler', frame=f, group=pb.name)
        pb.keyframe_insert('scale', frame=f, group=pb.name)
    raiz.keyframe_insert('location', frame=f)
    raiz.keyframe_insert('rotation_euler', frame=f)


def lanzar(i, R, destino, lado='r'):
    """mono i lanza hacia 'destino' soltando en el frame R. Devuelve (posicion mano al soltar, frame recogida)"""
    raiz, rig = mono(i)
    S = suf(rig)
    pos = Vector(raiz.location)
    # accion nueva solo si aun no tiene
    for ob in (raiz, rig):
        ob.animation_data_create()
    if rig.animation_data.action is None:
        rig.animation_data.action = bpy.data.actions.new(rig.name + '_acc')
    if raiz.animation_data.action is None:
        raiz.animation_data.action = bpy.data.actions.new(raiz.name + '_root')
    s = -1 if lado == 'r' else 1                      # signo x (local) del lado que lanza
    yb = yaw_hacia(pos, destino)
    cab = pos + V(0, 0, 1.0)
    dd = dir_local(raiz, yb, destino, cab)
    dz = destino.z - cab.z
    dh = math.hypot(destino.x - pos.x, destino.y - pos.y)
    inc = dz / (dh + 1e-6)
    elev = max(-0.2, min(0.55, inc * 2.0 + 0.3))
    A = lambda x, y, z: V(x * s, y, z)                 # brazo que lanza (x>0 = hacia fuera)
    B = lambda x, y, z: V(-x * s, y, z)                # brazo contrario
    HEAD = lambda a, b, c: V(dd.x * a, b, c + dd.z * 0.5)
    mir = (0.0, max(-1.0, min(1.0, inc * 2)))
    pie = dict(lg=V(0, 0.2, -1), ls=V(0, -0.2, -1), lo=V(0, 0.15, -0.5), rg=V(0, 0.2, -1), rs=V(0, -0.2, -1), ro=V(0, 0.15, -0.5))
    poses = [
        (-34, yb, 0, {}),
        (-26, yb, 0, dict(head=HEAD(0.6, 0.65, 0.3), mira=mir, ceno=0.4, orejas=0.3)),
        (-20, yb, -0.18, dict(body=V(0, 0.75, 0.55), cube_r1=V(0, 0.8, 0.45), head=HEAD(0.5, 0.7, 0.2),
                              Lsh=A(0.95, 0.1, -0.1), La=A(0.15, 0.6, -0.8), Lf=A(0.1, 0.75, -0.65),
                              Nsh=B(0.95, 0.1, -0.1), Na=B(0.2, 0.4, -0.9), Nf=B(0.1, 0.5, -0.85),
                              lg=V(0, 0.8, -0.6), ls=V(0, -0.8, -0.5), lo=V(0, 0.2, -0.5), rg=V(0, 0.8, -0.6), rs=V(0, -0.8, -0.5), ro=V(0, 0.2, -0.5),
                              mira=mir, ceno=0.6, orejas=0.5)),
        (-13, yb - 10 * s, 0.0, dict(body=V(-0.15 * s, 0.25, 1), cube_r1=V(-0.1 * s, 0.1, 1), head=HEAD(0.6, 0.55, 0.9),
                                     Lsh=A(0.95, 0.0, 0.3), La=A(0.4, -0.55, 0.75), Lf=A(0.3, -0.75, 0.55),
                                     Nsh=B(0.95, 0.1, 0.1), Na=B(0.35, 0.7, 0.55), Nf=B(0.25, 0.85, 0.4), **pie,
                                     mira=mir, boca=0.5, ceno=1.0, orejas=0.8)),
        (-5, yb - 24 * s, 0.05, dict(body=V(-0.3 * s, 0.1, 1), cube_r1=V(-0.35 * s, 0.0, 1), head=HEAD(0.7, 0.5, 0.85),
                                     Lsh=A(0.95, -0.1, 0.35), La=A(0.55, -0.75, 0.55), Lf=A(0.4, -0.9, 0.4),
                                     Nsh=B(0.95, 0.15, 0.1), Na=B(0.45, 0.8, 0.35), Nf=B(0.3, 0.9, 0.25),
                                     lg=V(0, -0.15, -1), ls=V(0, -0.3, -1), lo=V(0, 0.15, -0.5), rg=V(0, 0.5, -1), rs=V(0, -0.35, -1), ro=V(0, 0.15, -0.5),
                                     mira=mir, boca=0.8, ceno=1.0, orejas=1.0)),
        (0, yb + 12 * s, 0.14, dict(body=V(0.12 * s, 0.45, 1), cube_r1=V(0.15 * s, 0.6, 1), head=HEAD(0.8, 0.8, 0.7),
                                    Lsh=A(0.85, 0.35, 0.2), La=A(0.2, 0.8, 0.45 + elev), Lf=A(0.1, 0.95, 0.35 + elev), Lh=A(0.05, 1.0, 0.3 + elev),
                                    Nsh=B(0.95, -0.1, 0.0), Na=B(0.55, -0.3, -0.8), Nf=B(0.35, -0.5, -0.85),
                                    lg=V(0, 0.3, -1), ls=V(0, -0.3, -1), lo=V(0, 0.15, -0.9), rg=V(0, 0.2, -1), rs=V(0, -0.2, -1), ro=V(0, 0.15, -0.9),
                                    mira=mir, boca=1.0, ceno=0.6, orejas=0.4)),
        (4, yb + 20 * s, 0.04, dict(body=V(0.2 * s, 0.6, 0.95), cube_r1=V(0.2 * s, 0.75, 0.9), head=HEAD(0.8, 0.8, 0.6),
                                    Lsh=A(0.85, 0.35, -0.2), La=A(-0.15, 0.55, -0.75), Lf=A(-0.35, 0.6, -0.65),
                                    Nsh=B(0.95, -0.1, 0.0), Na=B(0.55, -0.2, -0.8), Nf=B(0.35, -0.3, -0.85),
                                    lg=V(0, 0.45, -1), ls=V(0, -0.3, -1), lo=V(0, 0.15, -0.8), rg=V(0, 0.1, -1), rs=V(0, -0.15, -1), ro=V(0, 0.15, -0.8),
                                    mira=mir, boca=0.6, ceno=0.3, orejas=0.2)),
        (13, yb + 6 * s, 0.0, dict(body=V(0, 0.2, 1), cube_r1=V(0, 0.1, 1), head=HEAD(0.5, 0.3, 1),
                                   Lsh=A(0.95, 0, 0.3), La=A(0.6, 0.2, 0.9), Lf=A(0.45, 0.3, 0.9),
                                   Nsh=B(0.95, 0, 0.3), Na=B(0.6, 0.2, 0.9), Nf=B(0.45, 0.3, 0.9), **pie,
                                   mira=mir, boca=1.0, ceno=0.2, orejas=0.0)),
        (26, yb, 0, {}),
    ]
    for (t, yaw, hop, p) in poses:
        f = R + t
        raiz.location = pos + V(0, 0, hop)
        raiz.rotation_euler = (0, 0, math.radians(yaw))
        bpy.context.view_layer.update()
        pose_mono(rig, S, p, lado)
        key_todo(raiz, rig, f)
    raiz.location = pos
    return raiz, rig, S


def mano_pos(rig, S, lado):
    return rig.matrix_world @ rig.pose.bones[('right' if lado == 'r' else 'left') + 'hand' + S].tail
