# -*- coding: utf-8 -*-
"""alfred_cueva_5E.blend: utilidades para animar the_stalker_1 (armature torso_1) saltando a la pared y trepando: FK propia sobre poses {hueso: quaternion} (sin evaluar la escena),
IK numerica de manos y pies contra la caverna (BVH de caverna_*) y las poses base (gateo de la 5D, poses5D.json).
pose = {"q": {hueso: Quaternion}, "loc": {hueso: Vector}}; EM = (location Vector, rotation_euler (rx, ry, rz)) del empty the_stalker_1."""
import bpy, math, json
from mathutils import Vector, Quaternion, Euler, Matrix

CARPETA = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/"
AR = bpy.data.objects["torso_1"]
EMP = bpy.data.objects["the_stalker_1"]
REST = {b.name: b.matrix_local.copy() for b in AR.data.bones}
PADRE = {b.name: (b.parent.name if b.parent else None) for b in AR.data.bones}
LARGO = {b.name: b.length for b in AR.data.bones}
NEUTRO = ("HL", "HR", "FL", "FR")
TIPO = {"HL": ("mano", "L"), "HR": ("mano", "R"), "FL": ("pierna", "L"), "FR": ("pierna", "R")}
LIM = {"mano": ("upper_arm.%s_1", "forearm.%s_1"), "pierna": ("thigh.%s_1", "shin.%s_1")}


def ss(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def cargar_pose(clave, ruta=CARPETA + "poses5D.json"):
    d = json.load(open(ruta))[str(clave)]
    return {"q": {n: Quaternion(v["q"]) for n, v in d["bones"].items()}, "loc": {n: Vector(v["loc"]) for n, v in d["bones"].items()}}


def copia(p):
    return {"q": {n: q.copy() for n, q in p["q"].items()}, "loc": {n: v.copy() for n, v in p["loc"].items()}}


def mundo_em(em):
    loc, rot = em
    return Matrix.Translation(loc) @ Euler(rot, 'XYZ').to_matrix().to_4x4() @ AR.matrix_parent_inverse @ AR.matrix_basis


def fk(pose, em, extra=None, huesos=None):
    """matrices mundo de `huesos`; extra = {hueso: Quaternion} se multiplica a la derecha de la rotacion de la pose"""
    extra = extra or {}
    W = mundo_em(em)
    cache = {}

    def pm(n):
        if n in cache:
            return cache[n]
        q = pose["q"][n]
        if n in extra:
            q = q @ extra[n]
        basis = Matrix.Translation(pose["loc"].get(n, Vector())) @ q.to_matrix().to_4x4()
        p = PADRE[n]
        cache[n] = (pm(p) @ (REST[p].inverted() @ REST[n]) @ basis) if p else REST[n] @ basis
        return cache[n]
    return {n: W @ pm(n) for n in (huesos or [])}


def punta(pose, em, nombre, extra=None):
    tipo, lado = TIPO[nombre]
    if tipo == "mano":
        return fk(pose, em, extra, ["finger_2.%s_1" % lado])["finger_2.%s_1" % lado] @ Vector((0, 0.28, 0))
    return fk(pose, em, extra, ["shin.%s_1" % lado])["shin.%s_1" % lado] @ Vector((0, -0.68, 0))


def evalua(bvh, pose, em, nombre, extra, holgura=0.18):
    """(punta, penalizacion): codo/rodilla y puntos medios de los segmentos a menos de `holgura` de la caverna"""
    tipo, lado = TIPO[nombre]
    if tipo == "mano":
        hs = ["upper_arm.%s_1" % lado, "forearm.%s_1" % lado, "finger_2.%s_1" % lado]
        M = fk(pose, em, extra, hs)
        tip = M[hs[2]] @ Vector((0, 0.28, 0))
        pts = [M[hs[1]].translation, M[hs[0]] @ Vector((0, -0.34, 0)), M[hs[1]] @ Vector((0, -0.56, 0))]
    else:
        hs = ["thigh.%s_1" % lado, "shin.%s_1" % lado]
        M = fk(pose, em, extra, hs)
        tip = M[hs[1]] @ Vector((0, -0.68, 0))
        pts = [M[hs[1]].translation, M[hs[1]] @ Vector((0, -0.34, 0)), M[hs[0]] @ Vector((0, -0.27, 0))]
    pen = 0.0
    if bvh is not None:
        for p_ in pts:
            r = bvh.find_nearest(p_)
            if r[0] is not None:
                d = (p_ - r[0]).dot(r[1])
                if d < holgura:
                    pen += (holgura - d) ** 2
    return tip, pen


def ik(bvh, pose, em, nombre, objetivo, prev, pesos=(1.0, 6.0, 0.004, 0.06), holgura=0.18, multi=True):
    """coordenadas descendentes sobre (hombro/cadera xyz, codo/rodilla x) hasta que la punta llegue a `objetivo`; devuelve (extra, params, error)"""
    tipo, lado = TIPO[nombre]
    n1, n2 = (s % lado for s in LIM[tipo])

    def ex_de(p_):
        return {n1: Euler((p_[0], p_[1], p_[2])).to_quaternion(), n2: Euler((p_[3], 0, 0)).to_quaternion()}

    def costo(p_):
        tip, pen = evalua(bvh, pose, em, nombre, ex_de(p_), holgura)
        return pesos[0] * (tip - objetivo).length_squared + pesos[1] * pen + pesos[2] * sum(x * x for x in p_) + pesos[3] * sum((a - b) ** 2 for a, b in zip(p_, prev))
    mejor, cb = list(prev), None

    def descenso(ini):
        p_ = list(ini)
        c0 = costo(p_)
        for paso in (0.4, 0.2, 0.1, 0.05, 0.025):
            for _ in range(4):
                mejoro = False
                for i in range(4):
                    for d in (paso, -paso):
                        q_ = list(p_)
                        q_[i] = max(-2.4, min(2.4, q_[i] + d))
                        cc = costo(q_)
                        if cc < c0:
                            c0, p_, mejoro = cc, q_, True
                if not mejoro:
                    break
        return c0, p_
    for ini in (list(prev), [0.0, 0.0, 0.0, 0.0]):
        c0, p_ = descenso(ini)
        if cb is None or c0 < cb:
            cb, mejor = c0, p_
    if multi and (evalua(bvh, pose, em, nombre, ex_de(mejor), holgura)[0] - objetivo).length > 0.12:       # minimo local: se prueban otros arranques (codo hacia otro lado)
        for ini in ([0.9, 0.0, 0.0, 0.8], [-0.9, 0.0, 0.0, 0.8], [0.0, 0.0, 0.9, -0.7], [0.0, 0.0, -0.9, -0.7], [1.4, 0.4, 0.0, 1.2], [-1.4, -0.4, 0.0, 1.2], [0.5, 0.0, 0.0, -1.0], [-0.5, 0.0, 0.0, -1.0]):
            c0, p_ = descenso(ini)
            if c0 < cb:
                cb, mejor = c0, p_
    ex = ex_de(mejor)
    return ex, mejor, (evalua(bvh, pose, em, nombre, ex, holgura)[0] - objetivo).length


def bvh_caverna():
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    vs, ps = [], []
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        if o.name.startswith("bloque_"):                    # bloques sueltos del tunel de la salida (plataforma sobre el acantilado donde esta Alfred)
            bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
            if not (min(b.z for b in bb) > 40 and -14 < min(b.x for b in bb) < 16 and 60 < min(b.y for b in bb) < 110):
                continue
        elif not o.name.startswith("caverna_") or "lava" in o.name or o.name.startswith("caverna_luz"):
            continue
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        n0 = len(vs)
        vs += [oe.matrix_world @ v.co for v in me.vertices]
        inv = o.name.startswith("bloque_")                   # los bloques sueltos tienen las normales hacia dentro: se invierte el orden para que +normal sea aire
        ps += [tuple(n0 + i for i in (reversed(p.vertices) if inv else p.vertices)) for p in me.polygons]
        oe.to_mesh_clear()
    return BVHTree.FromPolygons(vs, ps)
