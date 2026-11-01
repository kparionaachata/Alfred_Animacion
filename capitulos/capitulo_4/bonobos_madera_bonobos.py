# -*- coding: utf-8 -*-
"""Animacion de los bonobos (poses FK por direccion con `apuntar`) y de los objetos lanzados. Requiere bonobos_madera_lib.py y bonobos_madera_escena.py ya cargados."""
import bpy, math, random
from mathutils import Vector, Matrix, Euler

V = lambda x, y, z: Vector((x, y, z))
_ULTB = {}


def _sufijo(rig):
    for b in rig.data.bones:
        if b.name.startswith('head_'):
            return b.name[5:]
    raise KeyError('head_')


def _rig(raiz):
    return [o for o in raiz.children if o.type == 'ARMATURE'][0]


HUESOS_B = ['body', 'cube_r1', 'head', 'leftshoulder', 'leftarm', 'leftforearm', 'lefthand', 'rightshoulder', 'rightarm', 'rightforearm', 'righthand',
            'leftleg', 'leftshin', 'leftfoot', 'rightleg', 'rightshin', 'rightfoot', 'jaw', 'lefteye', 'righteye', 'leftbrow_in', 'rightbrow_in', 'leftmouth', 'rightmouth']

REPOSO = dict(body=None, cube_r1=None, head=None, la=V(0.06, 0.12, -1), lf=V(0.0, 0.25, -1), lh=None, ra=V(-0.06, 0.12, -1), rf=V(0.0, 0.25, -1), rh=None,
              ll=V(0.0, 0.2, -1), ls=V(0.0, -0.15, -1), lfoot=None, rl=V(0.0, 0.2, -1), rs=V(0.0, -0.15, -1), rfoot=None, jaw=0.0, ojos=None)


def bpose(raiz, f, **kw):
    """pose del bonobo (raiz = empty 'bonobo_X'). Las direcciones (en el espacio del personaje: x izquierda del bonobo, y adelante, z arriba) pisan el reposo cuadrupedo.
    body/cube_r1/head: direccion del eje del hueso; la/lf/lh brazo izq (+X) antebrazo mano; ra/rf/rh derecho; ll/ls/lfoot rl/rs/rfoot piernas; jaw = grados de apertura."""
    rig = _rig(raiz); S = _sufijo(rig)
    d = dict(REPOSO); d.update(kw)
    for pb in rig.pose.bones:
        pb.rotation_mode = 'XYZ'; pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0); pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    if d['body'] is not None:
        apuntar(rig, 'body_' + S, d['body'])
    if d['cube_r1'] is not None:
        apuntar(rig, 'cube_r1_' + S, d['cube_r1'])
    if d['head'] is not None:
        apuntar(rig, 'head_' + S, d['head'])
    orden = [('leftarm', 'la'), ('leftforearm', 'lf'), ('lefthand', 'lh'), ('rightarm', 'ra'), ('rightforearm', 'rf'), ('righthand', 'rh'),
             ('leftleg', 'll'), ('leftshin', 'ls'), ('leftfoot', 'lfoot'), ('rightleg', 'rl'), ('rightshin', 'rs'), ('rightfoot', 'rfoot')]
    for hueso, k in orden:
        if d[k] is not None:
            apuntar(rig, hueso + '_' + S, d[k])
    jb = rig.pose.bones.get('jaw_' + S)
    if jb is not None and d['jaw']:
        jb.rotation_euler = (math.radians(-d['jaw']), 0, 0)
    for h in HUESOS_B:
        pb = rig.pose.bones.get(h + '_' + S)
        if pb is None:
            continue
        e = pb.rotation_euler.copy()
        key = (rig.name, h)
        if key in _ULTB:
            e.make_compatible(_ULTB[key])
        _ULTB[key] = e.copy()
        pb.rotation_euler = e
        pb.keyframe_insert('rotation_euler', frame=f, group=h)


def broot(raiz, f, loc=None, yaw=None):
    if loc is not None:
        raiz.location = loc
    if yaw is not None:
        raiz.rotation_euler = (0, 0, math.radians(yaw))
    raiz.keyframe_insert('location', frame=f)
    raiz.keyframe_insert('rotation_euler', frame=f)


def yaw_hacia(desde, hacia):
    """yaw (grados) para que un personaje que mira a +Y mire de 'desde' a 'hacia'"""
    return math.degrees(math.atan2(hacia[1] - desde[1], hacia[0] - desde[0])) - 90


def iniciar(raiz):
    rig = _rig(raiz)
    for ob in (raiz, rig):
        ob.animation_data_create(); ob.animation_data.action = None
    accion_nueva(rig, rig.name + '_acc'); accion_nueva(raiz, raiz.name + '_root')
    for k in [k for k in _ULTB if k[0] == rig.name]:
        del _ULTB[k]


# ---------------------------------------------------------------- poses nombradas
def b_vigila(raiz, f, mira=0.0, **k):         # cuadrupedo, cabeza girada
    bpose(raiz, f, **k)


def b_levanta(raiz, f, lado='l', **k):         # se pone de pie para lanzar (brazo 'lado' arriba atras)
    a = dict(body=V(0, 0.25, 1), cube_r1=V(0, 0.15, 1), head=V(0, 0.35, 0.95), ll=V(0, 0.2, -1), ls=V(0, -0.2, -1), rl=V(0, 0.2, -1), rs=V(0, -0.2, -1))
    if lado == 'l':
        a.update(la=V(0.35, -0.45, 0.85), lf=V(0.2, -0.65, 0.75), ra=V(-0.25, 0.25, -0.9), rf=V(-0.1, 0.45, -0.85))
    else:
        a.update(ra=V(-0.35, -0.45, 0.85), rf=V(-0.2, -0.65, 0.75), la=V(0.25, 0.25, -0.9), lf=V(0.1, 0.45, -0.85))
    a.update(k); bpose(raiz, f, **a)


def b_suelta(raiz, f, lado='l', **k):          # momento de soltar: brazo adelante, pecho adelante
    a = dict(body=V(0, 0.4, 1), cube_r1=V(0, 0.55, 1), head=V(0, 0.6, 0.9), ll=V(0, 0.35, -1), ls=V(0, -0.3, -1), rl=V(0, 0.15, -1), rs=V(0, -0.15, -1), jaw=20)
    if lado == 'l':
        a.update(la=V(0.15, 0.8, 0.55), lf=V(0.05, 0.95, 0.3), ra=V(-0.3, 0.1, -0.9), rf=V(-0.1, 0.35, -0.85))
    else:
        a.update(ra=V(-0.15, 0.8, 0.55), rf=V(-0.05, 0.95, 0.3), la=V(0.3, 0.1, -0.9), lf=V(0.1, 0.35, -0.85))
    a.update(k); bpose(raiz, f, **a)


def b_sigue(raiz, f, lado='l', **k):           # termina el lanzamiento
    a = dict(body=V(0, 0.55, 1), cube_r1=V(0, 0.7, 0.9), head=V(0, 0.75, 0.8), ll=V(0, 0.45, -1), ls=V(0, -0.3, -1), rl=V(0, 0.1, -1), rs=V(0, -0.1, -1), jaw=10)
    if lado == 'l':
        a.update(la=V(0.2, 0.75, -0.55), lf=V(0.1, 0.8, -0.55), ra=V(-0.3, 0.1, -0.9), rf=V(-0.1, 0.3, -0.9))
    else:
        a.update(ra=V(-0.2, 0.75, -0.55), rf=V(-0.1, 0.8, -0.55), la=V(0.3, 0.1, -0.9), lf=V(0.1, 0.3, -0.9))
    a.update(k); bpose(raiz, f, **a)


def b_grita(raiz, f, **k):                     # de pie, brazos arriba, boca abierta (amenaza / burla)
    a = dict(body=V(0, 0.2, 1), cube_r1=V(0, 0.1, 1), head=V(0, 0.25, 1), la=V(0.4, 0.2, 0.9), lf=V(0.3, 0.3, 0.9), ra=V(-0.4, 0.2, 0.9), rf=V(-0.3, 0.3, 0.9),
             ll=V(0, 0.2, -1), ls=V(0, -0.2, -1), rl=V(0, 0.2, -1), rs=V(0, -0.2, -1), jaw=40)
    a.update(k); bpose(raiz, f, **a)


def b_agacha(raiz, f, **k):                    # agachado para saltar
    a = dict(ll=V(0, 0.9, -0.55), ls=V(0, -0.9, -0.45), rl=V(0, 0.9, -0.55), rs=V(0, -0.9, -0.45), la=V(0.1, 0.5, -0.9), lf=V(0, 0.6, -0.8), ra=V(-0.1, 0.5, -0.9), rf=V(0, 0.6, -0.8))
    a.update(k); bpose(raiz, f, **a)


def b_vuela(raiz, f, **k):                     # en el aire: brazos adelante, piernas atras
    a = dict(body=V(0, 0.7, 0.7), cube_r1=V(0, 0.8, 0.6), head=V(0, 0.9, 0.4), la=V(0.2, 0.9, 0.4), lf=V(0.1, 0.9, 0.35), ra=V(-0.2, 0.9, 0.4), rf=V(-0.1, 0.9, 0.35),
             ll=V(0.1, -0.7, -0.7), ls=V(0, -0.8, -0.6), rl=V(-0.1, -0.7, -0.7), rs=V(0, -0.8, -0.6), jaw=15)
    a.update(k); bpose(raiz, f, **a)


def b_cae(raiz, f, **k):                       # aterriza: brazos abajo adelante, piernas flexionadas
    a = dict(la=V(0.1, 0.7, -0.7), lf=V(0, 0.8, -0.6), ra=V(-0.1, 0.7, -0.7), rf=V(0, 0.8, -0.6), ll=V(0, 0.8, -0.6), ls=V(0, -0.8, -0.5), rl=V(0, 0.8, -0.6), rs=V(0, -0.8, -0.5))
    a.update(k); bpose(raiz, f, **a)


def hueso_mundo(raiz, nombre_corto, cola=True):
    rig = _rig(raiz); S = _sufijo(rig)
    pb = rig.pose.bones[nombre_corto + '_' + S]
    return rig.matrix_world @ (pb.tail if cola else pb.head)


# ---------------------------------------------------------------- objetos lanzados
def esconder(obj, f_ini, f_fin=None):
    """oculto antes de f_ini (y despues de f_fin si se da); incluye a todos sus hijos (la visibilidad no se hereda)"""
    for o in [obj] + list(obj.children_recursive):
        for ch in ('hide_viewport', 'hide_render'):
            setattr(o, ch, True); o.keyframe_insert(ch, frame=1)
            setattr(o, ch, False); o.keyframe_insert(ch, frame=f_ini)
            if f_fin is not None:
                setattr(o, ch, True); o.keyframe_insert(ch, frame=f_fin)


def vuelo(obj, f0, p0, f1, p1, altura=1.5, giro=(7.0, 3.0, 5.0), suelo=None, caida=10, rebote=0.15):
    """parabola de p0 (frame f0) a p1 (frame f1); despues cae al suelo (si suelo) en 'caida' frames. Keys por frame, giro en rad/s"""
    p0 = Vector(p0); p1 = Vector(p1)
    n = f1 - f0
    for i in range(n + 1):
        t = i / n
        p = p0.lerp(p1, t) + Vector((0, 0, altura * 4 * t * (1 - t)))
        obj.location = p
        obj.rotation_euler = (giro[0] * t * 1.0, giro[1] * t, giro[2] * t)
        obj.keyframe_insert('location', frame=f0 + i); obj.keyframe_insert('rotation_euler', frame=f0 + i)
    if suelo is not None:
        z0 = p1.z
        for i in range(1, caida + 1):
            t = i / caida
            z = z0 + (suelo - z0) * t * t
            if t > 0.8:
                z = suelo + rebote * math.sin((t - 0.8) / 0.2 * math.pi)
            q = Vector((p1.x + 0.25 * t, p1.y + 0.1 * t, z))
            obj.location = q
            obj.rotation_euler = (giro[0] + t, giro[1] + t * 0.5, giro[2])
            obj.keyframe_insert('location', frame=f1 + i); obj.keyframe_insert('rotation_euler', frame=f1 + i)
        return f1 + caida
    return f1
