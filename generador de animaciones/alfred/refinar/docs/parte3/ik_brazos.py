"""Parte 3 - cinematica directa e inversa de los brazos de Alfred (se ejecuta DENTRO de Blender con exec; no deja keyframes ni toca la escena).
`fk(rot, loc)` calcula las matrices de pose de TODOS los huesos (espacio del armature) a partir de las rotaciones Euler XYZ / ubicaciones por hueso, con las matrices de reposo del rig (sin view_layer.update, asi que funciona
aunque la escena tenga animacion). `mundo(O_loc, O_rz)` da la matriz armature -> mundo (root `Object` + constante). `resolver(...)` busca (cuat. hombro, cuat. codo X) para que la muneca (cola del hueso elbow) llegue al
objetivo (mundo) con el codo cerca de `codo_hint`. Verificado contra `pose_bone.matrix` de la escena con `verificar(rot, loc)`.
"""
import bpy, math, random
from mathutils import Euler, Matrix, Quaternion, Vector

AA = next(o for o in bpy.data.objects if o.type == "ARMATURE" and "Hips_alfred" in o.pose.bones); OO = AA.parent
REST = {b.name: (b.matrix_local.copy(), b.parent.name if b.parent else None, b.length) for b in AA.data.bones}
ORDEN = [b.name for b in AA.data.bones]            # los padres van antes que los hijos
C0 = OO.matrix_world.inverted() @ AA.matrix_world  # constante: armature respecto al root (se calcula una vez)


def fk(rot, loc):
    M = {}
    for n in ORDEN:
        R, par, _L = REST[n]; B = Matrix.Translation(Vector(loc.get(n, (0, 0, 0)))) @ Euler(rot.get(n, (0, 0, 0)), 'XYZ').to_matrix().to_4x4()
        M[n] = (R @ B) if par is None else (M[par] @ (REST[par][0].inverted() @ R) @ B)
    return M


def mundo(loc_root, rz):
    return Matrix.Translation(Vector(loc_root)) @ Matrix.Rotation(rz, 4, 'Z') @ C0


def cabeza_cola(M, n, Mw):
    return Mw @ M[n].translation, Mw @ (M[n] @ Vector((0, REST[n][2], 0)))


def verificar(rot, loc):
    """compara fk con la pose evaluada de la escena (usar tras sc.frame_set y con rot / loc leidos de la pose evaluada)."""
    bpy.context.view_layer.update(); M = fk(rot, loc); e = 0
    for n in ORDEN: e = max(e, (M[n].translation - AA.pose.bones[n].matrix.translation).length)
    return e


def resolver(lado, M_sp2, Mw, objetivo, codo_hint=None, inicio=None, loc_hombro=None, iters=6000, semilla=1, w_codo=0.15, w_giro=0.01, extra=None, z_fijo=None):
    """M_sp2 = matriz de pose de Spine2 (de `fk`), Mw = armature->mundo. Devuelve (q hombro, q codo, error mano, codo mundo)."""
    rng = random.Random(semilla); sgn = -1 if lado == "Left" else 1
    Rsp = REST["Spine2_alfred"][0]; Rup = REST[lado + "UpArm_alfred"][0]; Rel = REST[lado + "elbow_alfred"][0]; Lel = REST[lado + "elbow_alfred"][2]
    loc = Vector(loc_hombro) if loc_hombro is not None else Vector((0.006603 * sgn, 0.096746, -0.086079))
    q0, x0 = inicio if inicio else (Quaternion((1, 0, 0, 0)), 0.0); q0 = Quaternion(q0)
    objetivo = Vector(objetivo); hint = Vector(codo_hint) if codo_hint is not None else None
    T1 = M_sp2 @ (Rsp.inverted() @ Rup); T2 = Rup.inverted() @ Rel

    def cin(q, x):
        Mu = T1 @ (Matrix.Translation(loc) @ q.to_matrix().to_4x4()); Me = Mu @ T2 @ Euler((x, 0, 0), 'XYZ').to_matrix().to_4x4()
        return Mw @ Me.translation, Mw @ (Me @ Vector((0, Lel, 0)))

    def coste(par):
        q = Euler(par[:3], 'XYZ').to_quaternion(); codo, mun = cin(q, par[3]); c = (mun - objetivo).length
        if hint is not None: c += w_codo * (codo - hint).length
        if extra is not None: c += extra(codo, mun)
        if z_fijo is not None: c += 3 * abs(math.atan2(math.sin(par[2] - z_fijo), math.cos(par[2] - z_fijo)))          # giro Z del hombro (torsion) fijo: el brazo se lleva con X / Y
        if par[3] > 0.05: c += 5 * (par[3] - 0.05)                       # el codo no se hiperextiende
        if par[3] < -2.7: c += 5 * (-2.7 - par[3])                       # ni se dobla mas de ~155 grados
        return c + w_giro * q0.rotation_difference(q).angle + 0.002 * abs(par[3] - x0)
    e0 = q0.to_euler('XYZ'); mejor = None
    arranques = [[e0.x, e0.y, e0.z, x0]] + [[rng.uniform(-3.1, 3.1) for _ in range(3)] + [rng.uniform(-2.8, 0.3)] for _ in range(14)]
    for par in arranques:
        c = coste(par); paso = 0.6
        for it in range(iters // len(arranques)):
            cand = [v + rng.gauss(0, paso) for v in par]; cc = coste(cand)
            if cc < c: par, c = cand, cc
            elif it % 40 == 39: paso = max(paso * 0.8, 0.002)
        if mejor is None or c < mejor[0]: mejor = (c, par)
    c, par = mejor; q = Euler(par[:3], 'XYZ').to_quaternion(); codo, mun = cin(q, par[3])
    return q, Quaternion((math.cos(par[3] / 2), math.sin(par[3] / 2), 0, 0)), (mun - objetivo).length, codo
