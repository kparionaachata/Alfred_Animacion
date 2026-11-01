# -*- coding: utf-8 -*-
"""Fisica de los objetos lanzados (inercia y accion-reaccion) para 'Alfred tala arboles y los bonobos le tiran cosas'. Sustituye a `vuelo` de bonobos_madera_bonobos.py (misma firma, 24 fps).
- Vuelo antes del choque: parabola con la gravedad real (g = 9.81 m/s2 -> altura del arco = g*T^2/8), no un arco arbitrario.
- Choque: la velocidad que llevaba el objeto (inercia) se refleja en la superficie con un coeficiente de restitucion segun el objeto (manzana, palo, panal...), y sale rebotado con ella.
- Despues: cae con la gravedad, rebota contra el suelo perdiendo energia (restitucion y rozamiento), gira con la velocidad angular que traia y se queda quieto.
- Un objeto que falla (choca=False) sigue su trayectoria con la misma velocidad y cae mas alla."""
import bpy, math
from mathutils import Vector

G_M = 9.81
FPS = 24.0
G_F = G_M / (FPS * FPS)            # m/f^2

# (masa kg, restitucion contra Alfred, restitucion contra el suelo)
FISICA = {'apple': (0.25, 0.30, 0.45), 'stick': (0.40, 0.25, 0.30), 'honeycomb': (0.60, 0.10, 0.20), 'sweet_berries': (0.08, 0.15, 0.20),
          'cocoa_beans': (0.15, 0.25, 0.30), 'flint': (0.30, 0.20, 0.30), 'rat': (0.30, 0.15, 0.20), 'chicken': (1.5, 0.10, 0.15), 'snake': (0.35, 0.0, 0.0)}


def datos_fisicos(obj):
    for k, v in FISICA.items():
        if k in obj.name:
            return v
    return (0.3, 0.25, 0.3)


def velocidad_llegada(p0, p1, n):
    """velocidad (m/f) justo antes del choque en la parabola de n frames de p0 a p1 con gravedad real"""
    p0 = Vector(p0); p1 = Vector(p1)
    v = (p1 - p0) / n
    v.z -= 0.5 * G_F * n
    return v


def vuelo(obj, f0, p0, f1, p1, altura=None, giro=(7.0, 3.0, 5.0), suelo=None, caida=10, rebote=0.15, centro=None, choca=True):
    """parabola fisica de p0 (frame f0) a p1 (frame f1); si 'suelo' (z de reposo) hay tras el choque rebote + caida + rebotes en el suelo. 'centro' = centro de lo golpeado (para la normal del choque).
    Devuelve el frame final"""
    p0 = Vector(p0); p1 = Vector(p1)
    n = f1 - f0
    h = G_F * n * n / 8.0                                  # arco con gravedad real
    for i in range(n + 1):
        t = i / n
        p = p0.lerp(p1, t) + Vector((0, 0, h * 4 * t * (1 - t)))
        obj.location = p
        obj.rotation_euler = (giro[0] * t, giro[1] * t, giro[2] * t)
        obj.keyframe_insert('location', frame=f0 + i); obj.keyframe_insert('rotation_euler', frame=f0 + i)
    if suelo is None:
        return f1
    e_obj, e_suelo = datos_fisicos(obj)[1], datos_fisicos(obj)[2]
    vin = velocidad_llegada(p0, p1, n)
    if choca:
        nrm = -vin.normalized()
        if centro is not None:
            c = (p1 - Vector(centro))
            if c.length > 1e-4:
                nrm = (c.normalized() * 0.6 + nrm * 0.4).normalized()
        vn = vin.dot(nrm)
        v = vin - (1.0 + e_obj) * vn * nrm                # reflexion con restitucion
        v = Vector((v.x * 0.85, v.y * 0.85, v.z))          # rozamiento tangencial
    else:
        v = vin.copy()                                     # no choca: conserva su velocidad (inercia)
    w = Vector(giro) / n * (1.4 if choca else 1.0)         # velocidad angular (rad/f)
    rot = Vector(giro)
    p = p1.copy()
    f = f1
    rebotes = 0
    for _ in range(140):
        f += 1
        v.z -= G_F
        p = p + v
        rot = rot + w
        w = w * 0.97
        en_suelo = False
        if p.z <= suelo and v.z < 0:
            p.z = suelo
            en_suelo = True
            if abs(v.z) > 0.035 and rebotes < 3:
                v = Vector((v.x * 0.7, v.y * 0.7, -v.z * e_suelo)); rebotes += 1; w = w * 0.7
            else:
                v = Vector((v.x * 0.55, v.y * 0.55, 0.0)); w = w * 0.5
        obj.location = p
        obj.rotation_euler = (rot.x, rot.y, rot.z)
        obj.keyframe_insert('location', frame=f); obj.keyframe_insert('rotation_euler', frame=f)
        if en_suelo and v.length < 0.004 and w.length < 0.01:
            break
    return f
