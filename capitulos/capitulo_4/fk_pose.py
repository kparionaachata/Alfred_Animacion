# -*- coding: utf-8 -*-
"""FK estatico de torso_1 sobre una pose dada (espacio de la armadura, frente = +Y, arriba = +Z): sirve para disenar poses (carrera, gateo) midiendo puntos de contacto.
pose = {hueso: (rx, ry, rz) euler XYZ}, ry_root = desplazamiento vertical de root_1 (location.y)"""
import bpy, math
from mathutils import Vector, Matrix, Euler

AR = bpy.data.objects["torso_1"]
REST = {b.name: b.matrix_local.copy() for b in AR.data.bones}


def fkp(pose, root_y=-0.0876, root_x=0.0, extra_lat=0.0):
    cache = {}

    def pm(n):
        if n in cache:
            return cache[n]
        b = AR.data.bones[n]
        e = pose.get(n, (0, 0, 0))
        basis = Matrix.Translation((root_x if n == "root_1" else 0.0, root_y if n == "root_1" else 0.0, 0.0)) @ Euler(e).to_quaternion().to_matrix().to_4x4()
        m = (pm(b.parent.name) @ (REST[b.parent.name].inverted() @ REST[n]) @ basis) if b.parent else REST[n] @ basis
        cache[n] = m
        return m
    return pm


def puntos(pose, root_y=-0.0876):
    pm = fkp(pose, root_y)
    P = {}
    for s in ("L", "R"):
        sh = pm("shin.%s_1" % s)
        P["pie" + s] = sh @ Vector((0, -0.68, 0))
        P["rodilla" + s] = sh.translation
        P["cadera" + s] = pm("thigh.%s_1" % s).translation
        fi = pm("finger_2.%s_1" % s)
        P["mano" + s] = fi @ Vector((0, 0.28, 0))
        P["muneca" + s] = fi.translation
        P["codo" + s] = pm("forearm.%s_1" % s).translation
        P["hombro" + s] = pm("upper_arm.%s_1" % s).translation
    P["pecho"] = pm("chest_1").translation
    P["espina"] = pm("spine_1").translation
    h = pm("head_1")
    P["cabeza"] = h.translation
    P["cabeza_top"] = h @ Vector((0, 1.0, 0))
    return P


def mostrar(pose, root_y=-0.0876):
    P = puntos(pose, root_y)
    return {k: [round(x, 2) for x in v] for k, v in P.items()}
