# -*- coding: utf-8 -*-
"""alfred_cueva_5B.blend: the_stalker_1 sostiene a un zombie (zombie_cav_12), lo levanta con las dos manos a la altura de su cabeza (el zombie, horizontal,
le tapa los ojos a la camara) y lo parte en dos por la cintura: al separarse las mitades se ven los ojos del Stalker. Las mitades caen y quedan en el suelo.
Cintura = z local 0.75 del zombie: arriba Body*/Arm*/Head*/ojo*, abajo Cube.* (piernas). La mitad de abajo es una COPIA de la jerarquia (empty + 2 armaduras + mallas).
Brazos del Stalker: rotacion de upper_arm.L_1 / upper_arm.R_1 (todo el brazo gira alrededor del hombro) en la accion de torso_1.
Frames (5B): 458-470 brazos al agarre / 474-494 levanta / 494-500 sostiene / 500-508 parte / 508-520 brazos caen y las mitades caen al suelo.
Uso: exec(open(ruta, encoding="utf8").read()); construir()      (repetible; borra y regenera las claves)
"""
import bpy, math
from mathutils import Vector, Quaternion, Matrix, Euler

ZOMBIE = "zombie_cav_12"
F_AGARRE0, F_AGARRE1, F_LEVANTA0, F_LEVANTA1, F_RIP0, F_RIP1, F_SUELTA, F_FIN = 428, 440, 442, 462, 486, 494, 506, 545
PISO = 6.02
F_GIRO0, F_GIRO1 = 498, 522                        # la cabeza gira hacia la camara mientras esta se acerca al rostro
CINTURA = 0.75
G = 9.8 / 24.0 ** 2


def ss(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _slerp_dir(a, b, t):
    q = a.rotation_difference(b)
    return (Quaternion((1, 0, 0, 0)).slerp(q, t) @ a).normalized()


def _basis_z(z, yref):
    z = z.normalized()
    x = yref.cross(z).normalized()
    y = z.cross(x)
    return Matrix((x, y, z)).transposed()


# postura base del Stalker: encorvado hacia delante, cabeza adelantada y patas abiertas (antinatural); rotaciones Euler XYZ locales de cada hueso
POSTURA = {"spine_1": (-0.50, 0.0, 0.10), "chest_1": (-0.40, 0.0, -0.08), "neck_1": (-0.20, 0.0, 0.10), "head_1": (0.45, 0.12, 0.12),
           "thigh.L_1": (0.14, 0.0, -0.45), "thigh.R_1": (0.14, 0.0, 0.45)}


def _postura(ar):
    """aplica la postura base (fija desde el frame 1) y baja root_1 lo justo para que los pies sigan en el suelo (z=PISO)"""
    O = bpy.data.objects
    PB = ar.pose.bones
    for n, e in POSTURA.items():
        PB[n].rotation_mode = 'QUATERNION'
        PB[n].rotation_quaternion = Euler(e).to_quaternion()
    PB["root_1"].location = (0, 0, 0)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    zmin = 1e9
    for n in ("Mesh_0_1", "Mesh_1", "Mesh_2_1", "Mesh_3_1"):
        o = O[n].evaluated_get(dg)
        me = o.to_mesh()
        zmin = min(zmin, min((o.matrix_world @ v.co).z for v in me.vertices))
        o.to_mesh_clear()
    PB["root_1"].location = (0, -(zmin - PISO), 0)
    bpy.context.view_layer.update()
    for n in list(POSTURA):
        PB[n].keyframe_insert("rotation_quaternion", frame=1)
    PB["root_1"].keyframe_insert("location", frame=1)
    return zmin - PISO


def _preparar_zombie():
    O = bpy.data.objects
    e = O[ZOMBIE]
    inf = O.get(ZOMBIE + "_inf")
    if inf is None:
        mapa = {}
        for o in [e] + list(e.children_recursive):
            c = o.copy()
            c.name = o.name + "_inf"
            mapa[o] = c
            for col in o.users_collection:
                col.objects.link(c)
        for o, c in mapa.items():
            c.parent = mapa.get(o.parent, o.parent)
            c.matrix_parent_inverse = o.matrix_parent_inverse.copy()
            for m in c.modifiers:
                if getattr(m, "object", None) in mapa:
                    m.object = mapa[m.object]
        inf = mapa[e]
    for raiz in (e, inf):
        for o in [raiz] + list(raiz.children_recursive):
            if o.animation_data:
                o.animation_data_clear()
            if o.type == 'ARMATURE':
                for pb in o.pose.bones:
                    pb.rotation_quaternion = (1, 0, 0, 0)
                    pb.rotation_euler = (0, 0, 0)
                    pb.location = (0, 0, 0)
                    pb.scale = (1, 1, 1)
            if o.type == 'MESH':
                pierna = o.name.startswith("Cube.")
                oculto = pierna if raiz is e else (not pierna)
                o.hide_render = oculto
                o.hide_viewport = oculto
        raiz.rotation_mode = 'QUATERNION'
        raiz.hide_render = False
        raiz.hide_viewport = False
    return e, inf


def _caja_local(raiz):
    """esquinas (en el espacio local del empty) de las mallas visibles"""
    inv = raiz.matrix_world.inverted()
    pts = []
    for o in raiz.children_recursive:
        if o.type == 'MESH' and not o.hide_render:
            for c in o.bound_box:
                pts.append(inv @ (o.matrix_world @ Vector(c)))
    return pts


def construir():
    O = bpy.data.objects
    sc = bpy.context.scene
    vl = bpy.context.view_layer
    st = O["the_stalker_1"]
    ar = O["torso_1"]
    e, inf = _preparar_zombie()
    vl.update()
    mw0 = ar.matrix_world
    yaw = st.matrix_world.to_euler().z
    f = Vector((-math.sin(yaw), math.cos(yaw), 0))
    r = Vector((math.cos(yaw), math.sin(yaw), 0))
    up = Vector((0, 0, 1))
    # brazos: reposo
    ad = ar.animation_data
    accion = ad.action
    PB = ar.pose.bones
    _postura(ar)
    huesos = [("upper_arm.%s_1" % l) for l in "LR"] + [("forearm.%s_1" % l) for l in "LR"]
    for n in huesos:
        PB[n].rotation_mode = 'QUATERNION'
        PB[n].rotation_quaternion = (1, 0, 0, 0)
    for l in accion.layers:
        for s_ in l.strips:
            for cb in s_.channelbags:
                for fc in list(cb.fcurves):
                    if fc.data_path.startswith(tuple('pose.bones["%s"]' % n for n in huesos)):
                        cb.fcurves.remove(fc)
    vl.update()

    def hombro(lado):
        return mw0 @ PB["upper_arm.%s_1" % lado].head

    def codo(lado):
        return mw0 @ PB["forearm.%s_1" % lado].head

    def punta(lado):
        return mw0 @ PB["finger_2.%s_1" % lado].head

    def mano(lado):
        h = punta(lado)
        return h + (codo(lado) - h).normalized() * 0.35

    v0u, v0f = {}, {}
    for lado in "LR":
        v0u[lado] = (codo(lado) - hombro(lado)).normalized()
        v0f[lado] = (punta(lado) - codo(lado)).normalized()
    pivote = {lado: hombro(lado) for lado in "LR"}
    s_ = {"L": -1.0, "R": 1.0}
    # (direccion hombro->codo, direccion codo->mano) por pose; el stalker mira a -camara: los brazos se abren en el plano de la camara (r)
    P_B = {l: ((f * 0.5 - up * 0.7 + r * s_[l] * 0.25).normalized(), (f * 0.6 - up * 0.55 + r * s_[l] * 0.1).normalized()) for l in "LR"}
    P_C = {l: ((r * s_[l] * 0.75 - up * 0.5 + f * 0.45).normalized(), (-r * s_[l] * 0.15 + up * 0.7 + f * 0.65).normalized()) for l in "LR"}
    P_X = {l: ((r * s_[l] * 0.95 + up * 0.25).normalized(), (r * s_[l] * 0.95 + up * 0.3).normalized()) for l in "LR"}
    P_0 = {l: (v0u[l], v0f[l]) for l in "LR"}

    def mezcla(A, B, t):
        return (_slerp_dir(A[0], B[0], t), _slerp_dir(A[1], B[1], t))

    def pose_en(lado, fr):
        if fr <= F_AGARRE0:
            return P_0[lado]
        if fr <= F_AGARRE1:
            return mezcla(P_0[lado], P_B[lado], ss((fr - F_AGARRE0) / (F_AGARRE1 - F_AGARRE0)))
        if fr <= F_LEVANTA0:
            return P_B[lado]
        if fr <= F_LEVANTA1:
            return mezcla(P_B[lado], P_C[lado], ss((fr - F_LEVANTA0) / (F_LEVANTA1 - F_LEVANTA0)))
        if fr <= F_RIP0:
            return P_C[lado]
        if fr <= F_RIP1:
            return mezcla(P_C[lado], P_X[lado], ss((fr - F_RIP0) / (F_RIP1 - F_RIP0)))
        if fr <= F_SUELTA:
            return mezcla(P_X[lado], P_0[lado], ss((fr - F_RIP1) / (F_SUELTA - F_RIP1)))
        return P_0[lado]

    manos = {}
    for fr in range(F_AGARRE0 - 1, F_FIN + 1):
        for lado in "LR":
            du, df = pose_en(lado, fr)
            pu, pf = PB["upper_arm.%s_1" % lado], PB["forearm.%s_1" % lado]
            pu.rotation_quaternion = (1, 0, 0, 0)
            pf.rotation_quaternion = (1, 0, 0, 0)
            vl.update()
            Mw = mw0 @ pu.matrix
            T = Matrix.Translation(pivote[lado]) @ v0u[lado].rotation_difference(du).to_matrix().to_4x4() @ Matrix.Translation(-pivote[lado])
            pu.matrix = mw0.inverted() @ (T @ Mw)
            vl.update()
            hc = codo(lado)
            vf = (punta(lado) - hc).normalized()
            T2 = Matrix.Translation(hc) @ vf.rotation_difference(df).to_matrix().to_4x4() @ Matrix.Translation(-hc)
            pf.matrix = mw0.inverted() @ (T2 @ (mw0 @ pf.matrix))
            pu.keyframe_insert("rotation_quaternion", frame=fr)
            pf.keyframe_insert("rotation_quaternion", frame=fr)
        vl.update()
        manos[fr] = (mano("L"), mano("R"))
    # zombie
    Yref = -f
    A_L = lambda fr: (manos[fr][0] - manos[fr][1])
    claves = {}
    ZH = {"sup": 1.15, "inf": 0.40}
    prevU = prevL = None
    caida = {}
    for fr in range(F_AGARRE0 - 1, F_RIP1 + 1):
        HL, HR = manos[fr]
        M = (HL + HR) * 0.5
        dLR = (HL - HR).normalized()
        tL = ss((fr - F_LEVANTA0) / (F_LEVANTA1 - F_LEVANTA0))
        zup = _slerp_dir(up, Vector((dLR.x, dLR.y, 0)).normalized(), tL)
        base = M - zup * CINTURA + up * (0.05 * tL) + f * 0.22        # las manos quedan por debajo y DETRAS del cuerpo (la camara ve al zombie delante de ellas)
        B0 = _basis_z(zup, Yref)
        if fr <= F_RIP0:
            claves[fr] = ((base, B0), (base, B0))
            continue
        w = ss((fr - F_RIP0) / 4.0)
        t = ss((fr - F_RIP0) / (F_RIP1 - F_RIP0))
        zu = _slerp_dir(zup, (-r * 0.35 + up * 0.9).normalized(), t)
        zl = _slerp_dir(zup, (r * 0.15 + up * 0.95).normalized(), t)
        Bu, Bl = _basis_z(zu, Yref), _basis_z(zl, Yref)
        pu = (HL - zu * ZH["sup"] + f * 0.22).lerp(base, 1 - w)
        pl_ = (HR - zl * ZH["inf"] + f * 0.22).lerp(base, 1 - w)
        claves[fr] = ((pu, Bu), (pl_, Bl))
    # caida
    finales = {}
    for idx, (raiz, eje_f) in enumerate(((e, (-r * 0.75 + f * 0.55).normalized()), (inf, (r * 0.55 + f * 0.8).normalized()))):
        (p1, B1) = claves[F_RIP1][idx]
        (p0, B0_) = claves[F_RIP1 - 1][idx]
        v = (p1 - p0)
        zvel = v.z
        pos = p1.copy()
        zaxis0 = B1.col[2].copy()
        # bbox para apoyar la mitad en el suelo (eje final horizontal)
        BF = _basis_z(eje_f, Yref)
        pts = _caja_local(raiz)
        zmin_rel = min((BF @ p).z for p in pts)
        z_reposo = PISO + 0.01 - zmin_rel
        seq = {}
        vxy = Vector((v.x, v.y, 0)) * 0.7
        tcaida = 0
        rebotes = 0
        z = pos.z
        vz = zvel
        xy = Vector((pos.x, pos.y, 0))
        quieto = False
        for fr in range(F_RIP1 + 1, F_FIN + 1):
            if not quieto:
                tcaida += 1
                vz -= G
                z += vz
                xy += vxy
                vxy *= 0.92
                if z <= z_reposo:
                    z = z_reposo
                    if rebotes == 0 and abs(vz) > 0.05:
                        vz = -vz * 0.25
                        rebotes = 1
                    else:
                        vz = 0
                        quieto = True
                ta = ss(tcaida / 16.0)
                za = _slerp_dir(zaxis0, eje_f, ta)
                seq[fr] = (Vector((xy.x, xy.y, z)), _basis_z(za, Yref))
            else:
                seq[fr] = (Vector((xy.x, xy.y, z_reposo)), BF)
        for fr, vv in seq.items():
            claves.setdefault(fr, [None, None])
            lst = list(claves[fr])
            lst[idx] = vv
            claves[fr] = tuple(lst)
    # claves
    for idx, raiz in enumerate((e, inf)):
        raiz.animation_data_create()
        for fr in sorted(claves):
            p, B = claves[fr][idx]
            raiz.location = p
            raiz.rotation_quaternion = B.to_quaternion()
            raiz.keyframe_insert("location", frame=fr)
            raiz.keyframe_insert("rotation_quaternion", frame=fr)
        # quieto antes del agarre
        p, B = claves[F_AGARRE0 - 1][idx]
        raiz.location = p
        raiz.rotation_quaternion = B.to_quaternion()
        raiz.keyframe_insert("location", frame=1)
        raiz.keyframe_insert("rotation_quaternion", frame=1)
        if raiz.animation_data and raiz.animation_data.action:
            for l in raiz.animation_data.action.layers:
                for s in l.strips:
                    for cb in s.channelbags:
                        for fc in cb.fcurves:
                            for k in fc.keyframe_points:
                                k.interpolation = 'LINEAR'
                            fc.update()
    sc.frame_end = max(sc.frame_end, F_FIN)
    _organicos_zombie(e, inf)
    _organicos_stalker(ar)
    sc.frame_set(1)
    return {"manos": len(manos), "frame_end": sc.frame_end}


def _ruido(fr, freq, seed, dim=0):
    v = math.sin(fr * freq * 1.3 + seed * 7.3 + dim * 3.7) + math.sin(fr * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5 + math.sin(fr * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25
    return v / 1.75


def _rot_hueso(pb, dir_nuevo):
    """gira el hueso (y sus hijos) alrededor de su cabeza para que apunte a dir_nuevo (espacio de la armadura)"""
    v = (pb.tail - pb.head).normalized()
    R = v.rotation_difference(dir_nuevo.normalized())
    h = pb.head.copy()
    T = Matrix.Translation(h) @ R.to_matrix().to_4x4() @ Matrix.Translation(-h)
    pb.matrix = T @ pb.matrix


def _organicos_zombie(e, inf):
    """colgante, sin postura en T: brazos caidos que se mecen, piernas y cabeza con micro-movimiento (todo el rango f1..F_FIN)"""
    for k, raiz in enumerate((e, inf)):
        arm = next(o for o in raiz.children if o.type == 'ARMATURE' and "face" not in o.name)
        if arm.animation_data and arm.animation_data.action:
            arm.animation_data_clear()
        arm.animation_data_create()
        PB = arm.pose.bones
        for fr in [1] + list(range(F_AGARRE0 - 1, F_FIN + 1, 2)):
            for pb in PB:
                pb.rotation_quaternion = (1, 0, 0, 0)
                pb.rotation_euler = (0, 0, 0)
            bpy.context.view_layer.update()
            # forcejeo: amplitud 1 mientras lo sostiene y lo parten, se vuelve flojo al caer
            amp = ss((fr - F_AGARRE0) / 6.0) * (1.0 - 0.85 * ss((fr - F_RIP1 - 2) / 10.0)) if fr > 1 else 0.0
            for lado, sg in (("Right", 1), ("Left", -1)):
                ph = 0.0 if sg > 0 else 2.3
                a1 = math.sin(fr * 0.42 + ph)
                a2 = math.sin(fr * 0.31 + ph + 1.1)
                a3 = math.sin(fr * 0.52 + ph + 2.0)
                base_x = 0.22 + 0.08 * _ruido(fr, 0.09, 11, 0) * (1 - amp)
                d = Vector((sg * (base_x + 0.7 * amp * a1), 0.75 * amp * a2, -1.0 + 0.9 * amp * (0.5 + 0.5 * a3)))
                _rot_hueso(PB["%sUpArm_zombie_1" % lado], d)
                bpy.context.view_layer.update()
                eb_dir = Vector((sg * (0.35 + 0.4 * amp * a2), 0.55 + 0.5 * amp * a1, -0.75 + 0.6 * amp * a3)).normalized()
                _rot_hueso(PB["%selbow_zombie_1" % lado], eb_dir)
                bpy.context.view_layer.update()
                pierna = PB["%sUpLeg_zombie_1" % lado]
                pa = math.sin(fr * 0.48 + ph + 0.7)
                dl = Vector((0.03 * sg + 0.2 * amp * a3 * sg, 0.12 * _ruido(fr, 0.08, 21, 2) * (1 - amp) + 0.75 * amp * pa, -1.0))
                _rot_hueso(pierna, dl)
                bpy.context.view_layer.update()
                rod = PB["%sknee_zombie_1" % lado]
                _rot_hueso(rod, Vector((0.0, -0.15 - 0.55 * amp * (0.5 - 0.5 * pa), -1.0)))
                bpy.context.view_layer.update()
            cuello = PB["Neck_zombie_1"]
            cuello.rotation_mode = 'XYZ'
            cuello.rotation_euler = (0.12 * _ruido(fr, 0.07, 5, 0) + 0.25 * amp * math.sin(fr * 0.6), 0.0, 0.2 * _ruido(fr, 0.06, 9, 2) + 0.35 * amp * math.sin(fr * 0.45))
            for pb in PB:
                if pb.name.startswith(("RightUpArm", "Rightelbow", "LeftUpArm", "Leftelbow", "RightUpLeg", "LeftUpLeg", "Rightknee", "Leftknee")):
                    pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_euler", frame=fr)
            cuello.keyframe_insert("rotation_euler", frame=fr)
        for fc in [x for l in arm.animation_data.action.layers for s in l.strips for cb in s.channelbags for x in cb.fcurves]:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
            fc.update()


def _organicos_stalker(ar):
    """respiracion (pecho/columna), micro-movimiento de cabeza y temblor del esfuerzo mientras sostiene (f440..F_FIN)"""
    PB = ar.pose.bones
    for fr in range(440, F_FIN + 1, 2):
        esf = ss((fr - F_LEVANTA0) / 10.0) * (1 - ss((fr - F_RIP1) / 6.0))
        for n, amp, vel, seed in (("spine_1", 0.03, 0.05, 1), ("chest_1", 0.035, 0.05, 2), ("head_1", 0.05, 0.07, 3)):
            ex = amp * math.sin(2 * math.pi * 0.012 * fr + seed) + amp * 0.5 * _ruido(fr, vel, seed, 0)
            ey = amp * 0.4 * _ruido(fr, vel, seed, 1)
            ez = amp * 0.8 * _ruido(fr, vel, seed, 2) + (0.03 * _ruido(fr, 0.35, seed + 4, 2) * esf if n == "head_1" else 0)
            pb = PB[n]
            pb.rotation_mode = 'QUATERNION'
            giro = Euler((0, 0, 0)).to_quaternion()
            if n == "head_1":                                   # mira de lado y abajo (hacia el zombie) y al acercarse la camara gira y la mira de frente
                t = ss((fr - F_GIRO0) / float(F_GIRO1 - F_GIRO0))
                giro = Euler((0.15 * (1 - t), 0.5 + (-0.2 - 0.5) * t, -0.2 * t)).to_quaternion()
            pb.rotation_quaternion = Euler(POSTURA[n]).to_quaternion() @ giro @ Euler((ex, ey, ez)).to_quaternion()
            pb.keyframe_insert("rotation_quaternion", frame=fr)
    for fc in [x for l in ar.animation_data.action.layers for s in l.strips for cb in s.channelbags for x in cb.fcurves if x.data_path.startswith(('pose.bones["spine_1"]', 'pose.bones["chest_1"]', 'pose.bones["head_1"]'))]:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
        fc.update()


def _elasticidad(e, inf):
    """estira el zombie al tirar de el (squash & stretch) y al partirlo vuelve con rebote elastico amortiguado"""
    for raiz in (e, inf):
        raiz.rotation_mode = 'QUATERNION'
        for fr in range(F_RIP0 - 4, F_RIP1 + 24):
            if fr < F_RIP1:
                a = ss((fr - (F_RIP0 - 4)) / float(F_RIP1 - F_RIP0 + 4))
                sz = 1.0 + 0.40 * a
            else:
                t = fr - F_RIP1
                sz = 1.0 + 0.40 * math.exp(-t / 4.5) * math.cos(2 * math.pi * t / 7.0)
            sxy = 1.0 / math.sqrt(sz)
            raiz.scale = (sxy, sxy, sz)
            raiz.keyframe_insert("scale", frame=fr)
        raiz.scale = (1, 1, 1)
        raiz.keyframe_insert("scale", frame=1)
        raiz.keyframe_insert("scale", frame=F_RIP0 - 5)
        raiz.keyframe_insert("scale", frame=F_RIP1 + 24)
        raiz.keyframe_insert("scale", frame=F_FIN)
        for l in raiz.animation_data.action.layers:
            for st in l.strips:
                for cb in st.channelbags:
                    for fc in cb.fcurves:
                        if fc.data_path == "scale":
                            for kp in fc.keyframe_points:
                                kp.interpolation = 'LINEAR'
                            fc.update()


def _particulas(e, inf, n=34, F_EMIT0=488, F_EMIT1=500):
    """cubos de sangre (rojo) y carne (verde zombie) que salen del corte en el frame de la particion y caen al suelo"""
    import random
    O, sc = bpy.data.objects, bpy.context.scene
    col = bpy.data.collections.get("efectos_zombie")
    if col is None:
        col = bpy.data.collections.new("efectos_zombie")
        sc.collection.children.link(col)
    for o in list(col.objects):
        bpy.data.objects.remove(o)
    mats = {}
    for nm, c, em in (("zombie_sangre", (0.35, 0.01, 0.01, 1), 0.0), ("zombie_carne", (0.12, 0.30, 0.12, 1), 0.0)):
        m = bpy.data.materials.get(nm) or bpy.data.materials.new(nm)
        m.use_nodes = True
        bsdf = next(nd for nd in m.node_tree.nodes if nd.type == 'BSDF_PRINCIPLED')
        bsdf.inputs["Base Color"].default_value = c
        bsdf.inputs["Emission Color"].default_value = c
        bsdf.inputs["Emission Strength"].default_value = em
        mats[nm] = m
    me = bpy.data.meshes.get("zombie_particula") or bpy.data.meshes.new("zombie_particula")
    if not me.vertices:
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bm.to_mesh(me)
        bm.free()
    rnd = random.Random(77)
    cortes = {}
    for fe in range(F_EMIT0, F_EMIT1 + 1):
        sc.frame_set(fe)
        cortes[fe] = [raiz.matrix_world @ Vector((0, 0, CINTURA)) for raiz in (e, inf)]
    for i in range(n * 2):
        o = bpy.data.objects.new("zombie_particula_%02d" % i, me)
        col.objects.link(o)
        o.data = me
        o.active_material = mats["zombie_sangre" if i % 3 else "zombie_carne"]
        o.rotation_mode = 'XYZ'
        o.hide_render = True
        o.hide_viewport = True
        o.keyframe_insert("hide_render", frame=1)
        o.keyframe_insert("hide_viewport", frame=1)
        Fr = F_EMIT0 + (i * (F_EMIT1 - F_EMIT0)) // (n * 2 - 1)
        puntos = cortes[Fr]
        centro = (puntos[0] + puntos[1]) * 0.5
        orig = puntos[i % 2] + Vector((rnd.uniform(-.12, .12), rnd.uniform(-.12, .12), rnd.uniform(-.12, .12)))
        out = (puntos[i % 2] - centro)
        out = out.normalized() if out.length > 1e-4 else Vector((0, 0, 1))
        v = out * rnd.uniform(0.05, 0.16) + Vector((rnd.uniform(-.09, .09), rnd.uniform(-.09, .09), rnd.uniform(0.04, 0.2)))
        tam = rnd.uniform(0.03, 0.08)
        spin = Vector((rnd.uniform(-.4, .4), rnd.uniform(-.4, .4), rnd.uniform(-.4, .4)))
        pos = orig.copy()
        rot = Vector((rnd.uniform(0, 3), rnd.uniform(0, 3), rnd.uniform(0, 3)))
        vida = rnd.randint(40, 70)
        quieto = False
        for k in range(vida + 1):
            fr = Fr + k
            if fr > F_FIN:
                break
            if k == 0:
                o.hide_render = False
                o.hide_viewport = False
                o.keyframe_insert("hide_render", frame=fr)
                o.keyframe_insert("hide_viewport", frame=fr)
            o.location = pos
            o.rotation_euler = rot
            o.scale = (tam,) * 3 if k > 0 else (0.001,) * 3
            o.keyframe_insert("location", frame=fr)
            o.keyframe_insert("rotation_euler", frame=fr)
            o.keyframe_insert("scale", frame=fr)
            if not quieto:
                v.z -= G
                pos = pos + v
                rot = rot + spin
                v.x *= 0.97
                v.y *= 0.97
                if pos.z <= PISO + tam * 0.5:
                    pos.z = PISO + tam * 0.5
                    quieto = True
        for fc in [x for l in o.animation_data.action.layers for st in l.strips for cb in st.channelbags for x in cb.fcurves]:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR' if fc.data_path != "hide_render" and fc.data_path != "hide_viewport" else 'CONSTANT'
            fc.update()
    sc.frame_set(1)
    return len(col.objects)
