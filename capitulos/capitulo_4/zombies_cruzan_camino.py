# -*- coding: utf-8 -*-
"""alfred_cueva_5D.blend: entre el caminar y el correr de the_stalker_1 (frames ~500-680) se le cruzan zombies caminando perpendicular a su ruta; la criatura los aparta de un manotazo con
el brazo del lado por el que vienen (zombie desde la derecha -> brazo derecho; desde la izquierda -> brazo izquierdo): el brazo barre hacia fuera y el zombie sale despedido hacia el lado de
donde venia, cae de espaldas y se queda en el suelo.
Los zombies se CLONAN de zombie_cav_5 (raiz + armadura + armadura de cara + 15 mallas, con los modificadores Armature apuntando a las copias).
Requiere: el recorrido ya generado (curvas de the_stalker_1), BVH de la caverna en bpy.app.driver_namespace["ruta_bvh"], fk_clearance.py (para el barrido: _q, CAD, KEYS, preparar, indexar_claves).
Uso: cruzan_zombies()  (no repetir sin borrar los clones: borrar_clones())"""
import bpy, math
from mathutils import Vector, Euler

GOLPES = [(170, "L"), (300, "R"), (430, "L"), (560, "R")]     # (frame del impacto, lado por el que viene el zombie)
FUENTE = "zombie_cav_5"
V_ZOMBIE = 0.05                                               # m/frame
ALCANCE = 1.15                                                # distancia lateral al impactar
SUFIJO = "_cruza"
VX, VH = 0.18, 0.14                                           # velocidad inicial del despido: horizontal y vertical (m/frame)


def _ss(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _fcs(idb):
    return {(f.data_path, f.array_index): f for l in idb.animation_data.action.layers for s in l.strips for cb in s.channelbags for f in cb.fcurves}


def borrar_clones():
    for o in [o for o in bpy.data.objects if SUFIJO in o.name]:
        bpy.data.objects.remove(o)


def _clonar(k):
    O = bpy.data.objects
    src = O[FUENTE]
    col = src.users_collection[0]
    jer = [src]

    def rec(o):
        for c in o.children:
            jer.append(c)
            rec(c)
    rec(src)
    mapa = {}
    for o in jer:
        n = o.copy()
        n.name = o.name + SUFIJO + str(k)
        if o.animation_data:
            n.animation_data_clear()
        col.objects.link(n)
        mapa[o] = n
    for o in jer:
        n = mapa[o]
        if o.parent in mapa:
            n.parent = mapa[o.parent]
            n.matrix_parent_inverse = o.matrix_parent_inverse.copy()
        for m in n.modifiers:
            if m.type == 'ARMATURE' and m.object in mapa:
                m.object = mapa[m.object]
    return mapa[src], [mapa[o] for o in jer if o is not src]


# posturas finales en el suelo (una distinta por zombie): inclinacion final (pitch: - de espaldas, + de bruces), giro de costado/vuelta (roll; 6.283 = vuelta de campana completa), rotacion en el aire (spin),
# brazos (Z absoluta de cada hombro; None = pose base: brazos hacia delante) y piernas ({hueso: [(eje, delta)]})
ESTADOS = [
    dict(pitch=1.45, roll=6.283, spin=0.9, brazos={"LeftUpArm_zombie_1": 0.0, "RightUpArm_zombie_1": 0.0},                       # boca arriba, brazos pegados al cuerpo, piernas abiertas
         piernas={"LeftUpLeg_zombie_1": [(2, -0.35)], "RightUpLeg_zombie_1": [(2, 0.35)]}),
    dict(pitch=-1.45, roll=6.283, spin=-0.6, brazos={},                                                                              # de bruces, brazos estirados hacia delante, una pierna doblada hacia atras
         piernas={"RightUpLeg_zombie_1": [(0, -0.6)], "Rightknee_zombie_1": [(0, -1.0)]}),
    dict(pitch=-0.25, roll=1.5, spin=0.4, brazos={"RightUpArm_zombie_1": 0.0},                                                      # de costado, un brazo estirado y el otro caido, una pierna flexionada
         piernas={"LeftUpLeg_zombie_1": [(0, 0.9)], "Leftknee_zombie_1": [(0, -1.1)]}),
    dict(pitch=-0.3, roll=-1.5, spin=-0.8, brazos={"LeftUpArm_zombie_1": 0.45, "RightUpArm_zombie_1": -0.45},                      # de costado hecho un ovillo: piernas encogidas y brazos recogidos
         piernas={"LeftUpLeg_zombie_1": [(0, 1.3)], "RightUpLeg_zombie_1": [(0, 1.3)], "Leftknee_zombie_1": [(0, -1.7)], "Rightknee_zombie_1": [(0, -1.7)]}),
]


def _simular(cav, p0, v0, T, G=0.017, E_REB=0.35, MU=0.90, sub=6):
    """esfera de colision (centro sobre el origen del zombie, radio 0.5 de pie -> 0.25 tumbado, tras 12 frames) contra la malla de la caverna: gravedad, rebote contra suelo/paredes/techo
    (la velocidad normal se invierte y pierde energia), rozamiento al apoyar y amortiguacion. Devuelve {t: posicion del origen del zombie} para t=0..T"""
    pos = Vector(p0)
    v = Vector(v0)
    out = {0: Vector(pos)}
    dt = 1.0 / sub
    for t in range(1, T + 1):
        lie = _ss(t / 12.0)
        off = 0.9 * (1 - lie) + 0.25 * lie
        rad = 0.5 * (1 - lie) + 0.25 * lie
        for _ in range(sub):
            v.z -= G * dt
            pos += v * dt
            for _it in range(3):
                c = pos + Vector((0, 0, off))
                r = cav.find_nearest(c)
                if r[0] is None:
                    break
                n = r[1]
                d = (c - r[0]).dot(n)
                if d >= rad:
                    break
                pos += n * (rad - d)                                  # sacarlo de la superficie
                vn = v.dot(n)
                if vn < 0:
                    v -= (1 + E_REB) * vn * n                         # rebote
                    vt = v - v.dot(n) * n
                    v -= vt * (1 - MU) * 0.5                          # rozamiento en el choque
                if n.z > 0.7 and abs(v.dot(n)) < 0.02:               # apoyado en el suelo: desliza y se frena
                    vt = v - v.dot(n) * n
                    v -= vt * 0.05 * dt * sub / sub
                    v *= 0.995
        out[t] = Vector(pos)
    return out


_PUNTOS = [(0, 0, 0.12, 0.30), (0, 0, 0.5, 0.34), (0, 0, 0.9, 0.38), (0, 0, 1.4, 0.38), (0, 0, 1.85, 0.40), (0.3, 0, 1.0, 0.3), (-0.3, 0, 1.0, 0.3)]      # (x, y, z locales, radio de holgura: grosor real de la malla)


def _sin_penetrar(cav, pos, rot, iters=6):
    """sube (y aparta) el origen del zombie hasta que ninguno de los puntos del cuerpo este dentro de la caverna: holgura >= radio"""
    from mathutils import Matrix
    pos = Vector(pos)
    R = Euler(rot).to_matrix().to_4x4()
    for _ in range(iters):
        peor = None
        for x, y, z, rad in _PUNTOS:
            p = pos + (R @ Vector((x, y, z)))
            r = cav.find_nearest(p)
            if r[0] is None:
                continue
            d = (p - r[0]).dot(r[1])
            if d < rad and (peor is None or rad - d > peor[0]):
                peor = (rad - d, r[1])
        if peor is None:
            break
        pos += peor[1] * peor[0]
    return pos


def cruzan_zombies():
    O, sc = bpy.data.objects, bpy.context.scene
    st = O["the_stalker_1"]
    cav = bpy.app.driver_namespace["ruta_bvh"][0]
    fs = _fcs(st)
    loc = lambda fr: Vector([fs[("location", i)].evaluate(fr) for i in range(3)])
    yawf = lambda fr: fs[("rotation_euler", 2)].evaluate(fr)

    def suelo(x, y, z0):
        r = cav.ray_cast(Vector((x, y, z0 + 2.0)), Vector((0, 0, -1)), 6.0)
        return r[0].z if r[0] is not None else z0

    info, finales = [], []
    for k, (Fh0, lado0) in enumerate(GOLPES):
        sel = None
        for dF in (0, 8, -8, 16, -16, 24, -24, 32, -32, 40, -40):
            for lado in (lado0, "L" if lado0 == "R" else "R"):
                Fh = Fh0 + dF
                sg = 1.0 if lado == "R" else -1.0                       # el lado derecho de la criatura = +lateral
                yaw = yawf(Fh)
                fwd = Vector((-math.sin(yaw), math.cos(yaw), 0))
                lat = Vector((math.cos(yaw), math.sin(yaw), 0)) * sg    # hacia el lado de donde viene el zombie
                I = loc(Fh) + fwd * 0.15
                for cand in (6.0, 5.0, 4.0, 3.0, 2.5):
                    p0 = I + lat * cand
                    z0 = suelo(p0.x, p0.y, I.z)
                    dd = Vector((I.x - p0.x, I.y - p0.y, 0))
                    # libre: suelo parecido, sin bloques a la altura del cuerpo hasta la ruta ni detras (zona de despido)
                    p1 = I + lat * (cand + 0.0)
                    z1 = suelo(I.x + lat.x * (ALCANCE + 1.5), I.y + lat.y * (ALCANCE + 1.5), I.z)
                    ok = abs(z0 - I.z) < 0.8 and abs(z1 - I.z) < 0.8 and cav.ray_cast(Vector((p0.x, p0.y, z0 + 0.7)), dd.normalized(), dd.length)[0] is None                         and cav.ray_cast(Vector((I.x, I.y, I.z + 0.7)), lat, ALCANCE + 1.7)[0] is None and cav.ray_cast(Vector((I.x, I.y, I.z + 1.6)), lat, ALCANCE + 1.7)[0] is None
                    if ok:
                        sel = (Fh, lado, sg, lat, I, cand)
                        break
                if sel:
                    break
            if sel:
                break
        if not sel:
            info.append((Fh0, lado0, "sin hueco"))
            continue
        Fh, lado, sg, lat, I, d0 = sel
        finales.append((Fh, lado))
        root, hijos = _clonar(k)
        arm = next(o for o in hijos if o.type == 'ARMATURE' and o.name.startswith("zombie_1_Armature"))
        ts = int(Fh - (d0 - ALCANCE) / V_ZOMBIE)
        # animacion del zombie
        root.rotation_mode = 'XYZ'
        for o in hijos:
            if o.type == 'MESH' or o.type == 'ARMATURE':
                o.hide_viewport = True
                o.hide_render = True
                o.keyframe_insert("hide_viewport", frame=max(1, ts - 1))
                o.keyframe_insert("hide_render", frame=max(1, ts - 1))
                o.hide_viewport = False
                o.hide_render = False
                o.keyframe_insert("hide_viewport", frame=ts)
                o.keyframe_insert("hide_render", frame=ts)
        PB = arm.pose.bones
        for b in PB:
            b.rotation_mode = 'XYZ'
        base = {b.name: tuple(b.rotation_euler) for b in PB}
        T_END = Fh + 50
        out = -lat                                                  # el zombie camina hacia la criatura (direccion -lat)
        yaw_z = math.atan2(-out.x, out.y)
        # fisica del despido CON COLISIONES: el golpe da velocidad (inercia); esfera de colision contra la caverna (suelo, paredes, techo): rebota (e=0.35) perdiendo energia, rozamiento al deslizar
        p_hit = I + lat * ALCANCE
        p_hit = Vector((p_hit.x, p_hit.y, suelo(p_hit.x, p_hit.y, I.z)))
        sim = _simular(cav, p_hit, lat * VX + Vector((0, 0, VH)), T_END - Fh)
        for fr in range(max(1, ts - 1), T_END + 1):
            t = fr - Fh
            if fr <= Fh:
                d = d0 - V_ZOMBIE * (fr - ts)
                pos = I + lat * max(ALCANCE, d)
            else:
                pos = sim[t]
            if fr < ts:
                pos = I + lat * d0
            z = suelo(pos.x, pos.y, I.z) if fr <= Fh else pos.z
            tt = max(0.0, t)
            est = ESTADOS[k % len(ESTADOS)]
            pitch = est["pitch"] * _ss(tt / 12.0)                     # cae de espaldas (-) o de bruces (+)
            roll = est["roll"] * sg * _ss(tt / 16.0)                  # vuelta de campana en el aire (2 pi: acaba boca arriba/abajo) o de costado (1.5)
            spin = sg * est["spin"] * _ss(tt / 18.0)
            rot = (pitch, roll, yaw_z + spin)
            posv = Vector((pos.x, pos.y, z))
            if fr > Fh:
                posv = _sin_penetrar(cav, posv, rot)                  # ningun punto del cuerpo (pies, rodillas, cadera, pecho, cabeza) puede quedar dentro del suelo o la pared
            root.location = posv
            root.rotation_euler = rot
            root.keyframe_insert("location", frame=fr)
            root.keyframe_insert("rotation_euler", frame=fr)
            ph = 2 * math.pi * (fr - ts) / 26.0
            vivo = 1.0 if t <= 0 else 0.0
            br = _ss((t - 6) / 14.0) if t > 0 else 0.0                 # mezcla hacia la postura final en el suelo
            for bn, ax, val in (("LeftUpLeg_zombie_1", 0, 0.5 * math.sin(ph) * vivo + (0.0 if t <= 0 else 0.9 * math.sin(0.8 * t) * math.exp(-t / 14.0))),
                                ("RightUpLeg_zombie_1", 0, -0.5 * math.sin(ph) * vivo + (0.0 if t <= 0 else -0.9 * math.sin(0.8 * t + 0.7) * math.exp(-t / 14.0))),
                                ("Leftknee_zombie_1", 0, -0.45 * max(0.0, math.cos(ph)) * vivo - (0.0 if t <= 0 else 0.7 * max(0.0, math.sin(0.8 * t)) * math.exp(-t / 14.0))),
                                ("Rightknee_zombie_1", 0, -0.45 * max(0.0, -math.cos(ph)) * vivo - (0.0 if t <= 0 else 0.7 * max(0.0, math.sin(0.8 * t + 0.7)) * math.exp(-t / 14.0)))):
                e = list(base[bn])
                e[ax] += val
                for eje, delta in est["piernas"].get(bn, ()):             # postura final de las piernas (distinta en cada zombie), se instala tras la agitacion
                    e[eje] += delta * br
                PB[bn].rotation_euler = e
                PB[bn].keyframe_insert("rotation_euler", frame=fr)
            if t > 0:        # brazos del zombie salen disparados hacia arriba y atras por la inercia y oscilan hasta quedar en su postura final
                for bn, s2 in (("LeftUpArm_zombie_1", 1.0), ("RightUpArm_zombie_1", -1.0)):
                    e = list(base[bn])
                    flail = s2 * 1.5 * math.sin(0.7 * t) * math.exp(-t / 16.0)
                    z_fin = est["brazos"].get(bn)
                    e[2] = (base[bn][2] + flail * (1.0 - br) + (z_fin - base[bn][2]) * br) if z_fin is not None else base[bn][2] + flail
                    PB[bn].rotation_euler = e
                    PB[bn].keyframe_insert("rotation_euler", frame=fr)
        for idb in (root, arm):
            for fcv in _fcs(idb).values():
                for kp in fcv.keyframe_points:
                    kp.interpolation = 'LINEAR'
                fcv.update()
        info.append((Fh, lado, "d0=%.0f" % d0, "ts=%d" % ts))
    GOLPES[:] = finales
    return info


def _perfil(pts, t):
    """interpolacion suave (smoothstep) por tramos entre puntos (t, valor)"""
    if t <= pts[0][0]:
        return pts[0][1]
    if t >= pts[-1][0]:
        return pts[-1][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t0 <= t <= t1:
            return v0 + (v1 - v0) * _ss((t - t0) / float(t1 - t0))


# manotazo violento y coherente: TODO el cuerpo participa (la mano resuelta con IK es solo la ultima pieza de la cadena):
#   preparacion: el torso gira hacia el lado contrario y se inclina atras, la cabeza ya mira al zombie, el brazo se carga atras y cruzado;
#   golpe (5 frames): el torso gira hacia el zombie y se inclina hacia el, la mano barre en arco bajo hasta atravesar su posicion;
#   continuacion: el brazo sobrepasa y frena, el tronco se sacude y la criatura recibe el empujon de reaccion; luego todo vuelve al andar.
# Posiciones objetivo de la mano en el sistema local de la criatura (x: + = su derecha; y: + = delante; z: altura sobre el suelo), con x multiplicada por sg (lado del zombie)
_W = [(-14, 0.0), (-6, 1.0), (10, 1.0), (24, 0.0)]                                 # peso del objetivo frente al andar
_TX = [(-14, -0.3), (-6, -0.5), (-2, 0.35), (0, 1.15), (4, 2.0), (10, 1.6), (24, 1.0)]        # lateral (x sg)
_TY = [(-14, 0.8), (-6, 0.7), (-2, 0.55), (0, 0.15), (4, 0.1), (10, -0.2), (24, 0.3)]
_TZ = [(-14, 1.4), (-6, 1.7), (-2, 1.3), (0, 1.05), (4, 1.1), (10, 0.9), (24, 0.8)]
_PSI = [(-14, 0.0), (-6, -0.45), (0, 0.55), (4, 0.80), (10, 0.25), (24, 0.0)]       # giro del torso sobre la vertical (+ = hacia el zombie)
_ROLL = [(-14, 0.0), (-6, -0.10), (0, 0.16), (4, 0.20), (10, 0.05), (24, 0.0)]      # inclinacion lateral del torso (+ = hacia el zombie)
_CB = [(-14, 0.0), (-6, -0.12), (0, 0.0), (3, 0.14), (9, -0.05), (24, 0.0)]         # cabeceo del tronco: atras al cargar, sacudida al golpear (reaccion)
_RX = [(-14, 0.0), (-6, 0.05), (0, 0.0), (2, -0.16), (8, -0.10), (20, 0.0)]         # desplazamiento lateral de la cadera: carga, y empujon de reaccion en sentido contrario al del zombie
_HEAD = [(-18, 0.0), (-8, 1.0), (12, 1.0), (26, 0.0)]                                # peso de la mirada al zombie


def _guardar(NS, fr, n, dq):
    NS.setdefault("swipe", []).append((fr, n, dq))
    q = _q(n, fr) @ dq
    for i in range(4):
        fcv = CAD[('pose.bones["%s"].rotation_quaternion' % n, i)]
        kp = KEYS[fcv].get(fr)
        if kp:
            kp.co.y = q[i]
            kp.handle_left.y = q[i]
            kp.handle_right.y = q[i]


def barrer_brazos(ancho=24, invertir=False, indices=None, arranques=6):
    """manotazo coherente con accion-reaccion (ver arriba). Suma a las claves; las correcciones se guardan en bpy.app.driver_namespace['swipe'] para poder quitarlas (invertir=True)"""
    from mathutils import Matrix, Quaternion
    NS = bpy.app.driver_namespace
    preparar()
    indexar_claves()
    if invertir:
        for fr, n, dq in NS.pop("swipe", []):
            q = _q(n, fr) @ dq.inverted()
            for i in range(4):
                fcv = CAD[('pose.bones["%s"].rotation_quaternion' % n, i)]
                kp = KEYS[fcv].get(fr)
                if kp:
                    kp.co.y = q[i]
                    kp.handle_left.y = q[i]
                    kp.handle_right.y = q[i]
        for fr, n, qo in NS.pop("swipe_orig", []):               # devolver las claves originales del brazo (antes de la base limpia)
            for i in range(4):
                fcv = CAD[('pose.bones["%s"].rotation_quaternion' % n, i)]
                kp = KEYS[fcv].get(fr)
                if kp:
                    kp.co.y = qo[i]
                    kp.handle_left.y = qo[i]
                    kp.handle_right.y = qo[i]
        for fr, dy in NS.pop("swipe_root", []):
            fcv = CAD.get(('pose.bones["root_1"].location', 0))
            kp = KEYS[fcv].get(fr) if fcv else None
            if kp:
                kp.co.y -= dy
                kp.handle_left.y -= dy
                kp.handle_right.y -= dy
        for fcv in CAD.values():
            fcv.update()
        return
    guard_root = NS.setdefault("swipe_root", [])
    import random
    rnd = random.Random(7)
    O = bpy.data.objects

    def emp(fr):
        return Matrix.Translation(Vector([FE[("location", i)].evaluate(fr) for i in range(3)])) @ Euler((0, 0, FE[("rotation_euler", 2)].evaluate(fr))).to_matrix().to_4x4()

    def local(fr, p):
        return emp(fr).inverted() @ p

    def dq_mundo(fr, bone, axis, ang, extra=None):
        """cuaternion local que gira `bone` `ang` rad alrededor del eje MUNDO `axis` (independiente de la pose del hueso)"""
        R = fk(fr, extra, [bone])[bone].to_3x3().to_quaternion()
        return R.inverted() @ Quaternion(axis, ang) @ R

    for kk, (Fh, lado) in enumerate(GOLPES):
        if indices is not None and kk not in indices:
            continue
        sg = 1.0 if lado == "R" else -1.0
        ua, fa = "upper_arm.%s_1" % lado, "forearm.%s_1" % lado
        zr = O["zombie_cav_5" + SUFIJO + str(kk)]
        fz = _fcs(zr)
        zpos = lambda fr: Vector([fz[("location", i)].evaluate(fr) for i in range(3)])
        # base limpia del brazo: durante el golpe se parte del andar puro (sin las correcciones de choque con la caverna, que a veces dan saltos) y se funde con las claves originales en los extremos
        orig = NS.setdefault("swipe_orig", [])
        for fr in range(Fh - 14, Fh + ancho + 17):
            E0 = _paso_ph(_fase(fr), 1.0)
            t = fr - Fh
            wl = _ss((t + 14) / 6.0) * (1.0 - _ss((t - 30) / 10.0))
            for n in (ua, fa):
                qo = _q(n, fr)
                orig.append((fr, n, qo.copy()))
                qn = Euler(E0[n]).to_quaternion()
                if qn.dot(qo) < 0:
                    qn.negate()
                qq = qo.slerp(qn, wl)
                for i in range(4):
                    fcv = CAD[('pose.bones["%s"].rotation_quaternion' % n, i)]
                    kp = KEYS[fcv].get(fr)
                    if kp:
                        kp.co.y = qq[i]
                        kp.handle_left.y = qq[i]
                        kp.handle_right.y = qq[i]
        prm_prev = [0.0, 0.0, 0.0, 0.0]
        secuencia = {}
        torsos = {}
        for fr in range(Fh - 14, Fh + ancho + 1):
            t = fr - Fh
            yaw = FE[("rotation_euler", 2)].evaluate(fr)
            fwd = Vector((-math.sin(yaw), math.cos(yaw), 0.0))
            giro = (1.0 if lado == "L" else -1.0) * _perfil(_PSI, t)    # rotacion + sobre la vertical = a la izquierda: hacia el zombie de la izquierda (+) o de la derecha (-)
            roll = sg * _perfil(_ROLL, t)                                # + sobre el eje de avance = inclinarse a la derecha
            cb = _perfil(_CB, t)
            ex = {}
            for nombre, f_ in (("spine_1", 0.35), ("chest_1", 0.65)):
                d1 = dq_mundo(fr, nombre, Vector((0, 0, 1)), giro * f_)
                d2 = dq_mundo(fr, nombre, fwd, roll * f_)
                ex[nombre] = d1 @ d2 @ Euler((cb * (1.0 if nombre == "spine_1" else 0.5), 0, 0)).to_quaternion()
            torsos[fr] = ex
            w = _perfil(_W, t)
            base = local(fr, puntos_mano(fr, lado, ex)[4])
            tgt = Vector((sg * _perfil(_TX, t), _perfil(_TY, t), _perfil(_TZ, t)))
            meta = base.lerp(tgt, w)

            def costo(p_):
                e2 = dict(ex)
                e2[ua] = Euler((p_[0], p_[1], p_[2])).to_quaternion()
                e2[fa] = Euler((p_[3], 0, 0)).to_quaternion()
                return (local(fr, puntos_mano(fr, lado, e2)[4]) - meta).length_squared + (1.0 - w) * 0.6 * sum(x * x for x in p_)      # fuera del golpe el brazo vuelve al andar sin saltos
            inicios = [list(prm_prev), [0.0, 0.0, 0.0, 0.0]] + [[rnd.uniform(-1.6, 1.6), rnd.uniform(-1.0, 1.0), rnd.uniform(-1.6, 1.6), rnd.uniform(-0.5, 1.8)] for _ in range(max(0, arranques - 2))]
            mejor_J, mejor_p = 1e9, list(prm_prev)
            for ini in inicios:
                p0_ = list(ini)
                c0 = costo(p0_)
                for paso in (0.6, 0.3, 0.15, 0.07, 0.03):
                    for _ in range(5):
                        mejoro = False
                        for i in range(4):
                            for d in (paso, -paso):
                                q_ = list(p0_)
                                q_[i] = max(-2.4, min(2.4, q_[i] + d))
                                c = costo(q_)
                                if c < c0:
                                    c0, p0_, mejoro = c, q_, True
                        if not mejoro:
                            break
                J = c0 + 0.25 * sum((a_ - b_) ** 2 for a_, b_ in zip(p0_, prm_prev))      # continuidad: entre soluciones parecidas, la mas cercana al frame anterior (evita saltos de rama del IK)
                if J < mejor_J:
                    mejor_J, mejor_p = J, p0_
            if w <= 1e-3:
                mejor_p = [0.0, 0.0, 0.0, 0.0]
            mejor_p = [pp + max(-1.0, min(1.0, nn - pp)) for nn, pp in zip(mejor_p, prm_prev)]      # velocidad angular maxima: 1 rad/frame
            prm_prev = mejor_p
            secuencia[fr] = list(mejor_p)
        # suavizado temporal ligero de los angulos (no en el frame del golpe)
        frs = sorted(secuencia)
        suav = {}
        for fr in frs:
            if abs(fr - Fh) <= 1:
                suav[fr] = secuencia[fr]
                continue
            acc = [0.0] * 4
            tw = 0.0
            for i, wi in ((-1, 0.25), (0, 0.5), (1, 0.25)):
                g = min(frs[-1], max(frs[0], fr + i))
                tw += wi
                for j in range(4):
                    acc[j] += wi * secuencia[g][j]
            suav[fr] = [a_ / tw for a_ in acc]
        cab = {}
        for fr in frs:
            t = fr - Fh
            prm = suav[fr]
            ex = torsos[fr]
            for n, dq in (("spine_1", ex["spine_1"]), ("chest_1", ex["chest_1"]), (ua, Euler((prm[0], prm[1], prm[2])).to_quaternion()), (fa, Euler((prm[3], 0, 0)).to_quaternion())):
                _guardar(NS, fr, n, dq)
            # cabeza: mira al zombie (rotacion minima de la cara hacia el torso del zombie), limitada
            wh = _perfil(_HEAD, t)
            if wh > 1e-3:
                M = fk(fr, ex, ["head_1"])["head_1"]
                f = (M.to_3x3() @ Vector((0, 0, -1))).normalized()
                fd = ((zpos(fr) + Vector((0, 0, 1.5))) - M.translation).normalized()
                rot = f.rotation_difference(fd)
                if rot.angle > 1.0:
                    rot = Quaternion(rot.axis, 1.0)
                rot = Quaternion().slerp(rot, wh)
                Rq = M.to_3x3().to_quaternion()
                ax_, an_ = (Rq.inverted() @ rot @ Rq).to_axis_angle()
                cab[fr] = ax_ * an_
            dy = sg * _perfil(_RX, t)
            fcv = CAD.get(('pose.bones["root_1"].location', 0))
            kp = KEYS[fcv].get(fr) if fcv else None
            if kp:
                kp.co.y += dy
                kp.handle_left.y += dy
                kp.handle_right.y += dy
                guard_root.append((fr, dy))
        # cabeza: giros suavizados en el tiempo (gaussiana de 2.5 frames) para que la mirada siga al zombie sin sacudidas
        fh = sorted(cab)
        for fr in fh:
            acc, tw = Vector(), 0.0
            for i in range(-7, 8):
                wi = math.exp(-0.5 * (i / 2.5) ** 2)
                acc += cab[min(fh[-1], max(fh[0], fr + i))] * wi
                tw += wi
            v = acc / tw
            _guardar(NS, fr, "head_1", Quaternion(v.normalized(), v.length) if v.length > 1e-6 else Quaternion())
        for fcv in CAD.values():
            fcv.update()


# ---- brazos del zombie sin atravesar suelo/paredes tras la caida (FK propia de la armadura del zombie) ----
def _fk_zombie(root_m, arm, eul):
    """matrices mundo de los huesos del zombie para las rotaciones Euler `eul` {hueso: (x,y,z)} (resto: la pose base guardada en BASE)"""
    from mathutils import Matrix
    M0 = root_m @ arm.matrix_parent_inverse @ arm.matrix_basis
    cache = {}

    def pm(n):
        if n in cache:
            return cache[n]
        b = arm.data.bones[n]
        e = eul.get(n, BASE[n])
        basis = Euler(e).to_matrix().to_4x4()
        m = (pm(b.parent.name) @ (b.parent.matrix_local.inverted() @ b.matrix_local) @ basis) if b.parent else b.matrix_local @ basis
        cache[n] = m
        return m
    return pm, M0


BASE = {}


def _cargar_base():
    """pose base (de reposo) de la armadura del zombie, leida del modelo original (copia en disco)"""
    F = r"C:\Users\user\AppData\Local\Temp\claude\C--Users-user-Desktop-Alfred-Animacion\f2dc8c8c-28c2-4950-8dad-f7d558faab3c\scratchpad\fuente_zombie.blend"
    with bpy.data.libraries.load(F, link=False) as (df, dt):
        dt.objects = ["zombie_1_Armature.001"]
    o = dt.objects[0]
    antes = {x.name for x in bpy.data.objects}
    for pb in o.pose.bones:
        BASE[pb.name] = tuple(pb.rotation_euler)
    padre = o.parent
    bpy.data.objects.remove(o)
    if padre is not None and not padre.users_collection:          # al cargar la armadura tambien llega su padre: se quita si quedo huerfano
        bpy.data.objects.remove(padre)


def reparar_brazos(T_DESPUES=50, rad=0.2, t_ini=3, zombies=None):
    """tras el golpe, para cada frame prueba pequenas correcciones de los brazos (hombro X/Z y codo X) y se queda con la minima en la que ningun punto del brazo queda a menos de `rad` de la caverna"""
    import itertools
    O, sc = bpy.data.objects, bpy.context.scene
    cav = bpy.app.driver_namespace["ruta_bvh"][0]
    cands = sorted(itertools.product((0, 0.3, -0.3, 0.6, -0.6, 0.9, -0.9, 1.2, -1.2, 1.6, -1.6), (0, 0.3, -0.3, 0.6, -0.6, 0.9, -0.9, 1.2, -1.2), (0, 0.4, -0.4, 0.8, -0.8)), key=lambda c: abs(c[0]) + abs(c[1]) + 0.5 * abs(c[2]))
    res = {}
    for k, (Fh, lado) in enumerate(GOLPES):
        if zombies is not None and k not in zombies:
            continue
        root = O["zombie_cav_5" + SUFIJO + str(k)]
        arm = next(o for o in O if o.name == "zombie_1_Armature.001" + SUFIJO + str(k))
        fa = _fcs(arm)
        if not BASE:
            _cargar_base()
        # los brazos solo tenian claves desde el impacto (antes tomaban el valor de la primera clave): fijar la pose base hasta el golpe
        for nom in ("LeftUpArm_zombie_1", "RightUpArm_zombie_1"):
            pb = arm.pose.bones[nom]
            pb.rotation_euler = BASE[nom]
            for i in (0, 2):
                pb.keyframe_insert("rotation_euler", index=i, frame=Fh)
        fa = _fcs(arm)
        fr_root = _fcs(root)
        rm = lambda fr: __import__("mathutils").Matrix.Translation(Vector([fr_root[("location", i)].evaluate(fr) for i in range(3)])) @ Euler([fr_root[("rotation_euler", i)].evaluate(fr) for i in range(3)]).to_matrix().to_4x4()
        mal_antes = mal_despues = 0
        for fr in range(Fh + t_ini, Fh + T_DESPUES + 1):
            RM = rm(fr)
            cur = {}
            for nom in ("LeftUpArm_zombie_1", "RightUpArm_zombie_1", "Leftelbow_zombie_1", "Rightelbow_zombie_1"):
                cur[nom] = tuple(fa[('pose.bones["%s"].rotation_euler' % nom, i)].evaluate(fr) if ('pose.bones["%s"].rotation_euler' % nom, i) in fa else BASE[nom][i] for i in range(3))

            def libre(eul, lado_b):
                pm, M0 = _fk_zombie(RM, arm, eul)
                worst = 0.0
                for nom in (lado_b + "UpArm_zombie_1", lado_b + "elbow_zombie_1"):
                    m = M0 @ pm(nom)
                    L = arm.data.bones[nom].length
                    for f in (0.0, 0.5, 1.0):
                        p = m @ Vector((0, L * f, 0))
                        r = cav.find_nearest(p)
                        if r[0] is None:
                            continue
                        d = (p - r[0]).dot(r[1])
                        worst = max(worst, rad - d)
                return worst
            for lado_b in ("Left", "Right"):
                un, en = lado_b + "UpArm_zombie_1", lado_b + "elbow_zombie_1"
                sgn = 1.0 if lado_b == "Left" else -1.0
                w0 = libre(dict(cur), lado_b)
                mal_antes += 1 if w0 > 0.0 else 0
                if w0 <= 0.0:
                    continue
                best, bw = None, 9.0
                for dx, dz, de in cands:
                    e2 = dict(cur)
                    u = cur[un]
                    e2[un] = (u[0] + dx, u[1], u[2] + dz)
                    el = cur[en]
                    e2[en] = (el[0] + de, el[1], el[2])
                    w = libre(e2, lado_b)
                    if w <= 0.0:
                        best, bw = e2, w
                        break
                    if w < bw:
                        best, bw = e2, w
                if bw > 0.0:
                    mal_despues += 1
                for nom in (un, en):
                    for i in (0, 2):
                        fcv = fa.get(('pose.bones["%s"].rotation_euler' % nom, i))
                        if fcv is None:
                            fcv = None
                        pb = arm.pose.bones[nom]
                        e = list(pb.rotation_euler)
                        e[i] = best[nom][i]
                        pb.rotation_euler = e
                        pb.keyframe_insert("rotation_euler", index=i, frame=fr)
                cur[un], cur[en] = best[un], best[en]
        for fcv in _fcs(arm).values():
            for kp in fcv.keyframe_points:
                kp.interpolation = 'LINEAR'
            fcv.update()
        res[k] = (mal_antes, mal_despues)
    return res


def _asentar(cav, pos, rot, iters=400, paso=0.015):
    """reposo estatico del cuerpo (los 7 puntos de _PUNTOS): empuja fuera lo que penetre y, si cuelga en el aire (apoyado en una cornisa por un solo punto), lo hace volcar girando sobre el apoyo
    hasta que descansa; devuelve (posicion, euler) finales"""
    from mathutils import Quaternion
    R = Euler(rot).to_matrix()
    pos = Vector(pos)

    def gap(p, rad):
        r = cav.find_nearest(p)
        return (p - r[0]).dot(r[1]) - rad, r[1]
    for _ in range(iters):
        P = [pos + R @ Vector(l[:3]) for l in _PUNTOS]
        G = [gap(p, l[3]) for p, l in zip(P, _PUNTOS)]
        w = min(range(len(P)), key=lambda i: G[i][0])
        if G[w][0] < -0.005:
            pos += G[w][1] * (-G[w][0])
            continue
        sup = [i for i in range(len(P)) if G[i][0] < 0.03]
        if not sup:
            pos -= Vector((0, 0, 0.05))
            continue
        pv = sum((P[i] for i in sup), Vector()) / len(sup)
        tq = Vector()
        for p in P:
            tq += (p - pv).cross(Vector((0, 0, -1)))
        if tq.length < 1e-3 or (len(sup) >= 3 and tq.length < 0.15):
            break
        Rt = Quaternion(tq.normalized(), paso).to_matrix()
        R = Rt @ R
        pos = pv + Rt @ (pos - pv)
    return pos, R.to_euler('XYZ', Euler(rot))


def asentar_zombie(k, f_ini, f_fin):
    """el zombie k queda colgando de una cornisa al terminar la fisica: desde f_ini hasta f_fin vuelca (cae, acelerando) hasta su reposo estable; a partir de f_fin se queda quieto"""
    from mathutils import Quaternion
    cav = bpy.app.driver_namespace["ruta_bvh"][0]
    root = bpy.data.objects["zombie_cav_5" + SUFIJO + str(k)]
    fz = _fcs(root)
    p0 = Vector([fz[("location", i)].evaluate(f_ini) for i in range(3)])
    e0 = Euler([fz[("rotation_euler", i)].evaluate(f_ini) for i in range(3)])
    p1, e1 = _asentar(cav, p0, e0)
    q0, q1 = e0.to_quaternion(), e1.to_quaternion()
    prev = e0
    for fr in range(f_ini, max(f_fin, int(fz[("location", 0)].keyframe_points[-1].co.x)) + 1):
        u = min(1.0, (fr - f_ini) / float(f_fin - f_ini))
        w = u * u * (3 - 2 * u)
        w = w ** 1.5
        e = q0.slerp(q1, w).to_euler('XYZ', prev)
        prev = e
        p = p0.lerp(p1, w)
        if fr > f_ini:
            p = _sin_penetrar(cav, p, tuple(e))
        root.location = p
        root.rotation_euler = e
        root.keyframe_insert("location", frame=fr)
        root.keyframe_insert("rotation_euler", frame=fr)
    for fcv in fz.values():
        for kp in fcv.keyframe_points:
            kp.interpolation = 'LINEAR'
        fcv.update()
    return {"antes": [round(v, 2) for v in p0], "despues": [round(v, 2) for v in p1]}


def _puntos_malla(root, fr, paso=4):
    """vertices reales del zombie en `fr` (malla deformada por la armadura) en el sistema local de su origen"""
    sc = bpy.context.scene
    sc.frame_set(fr)
    dg = bpy.context.evaluated_depsgraph_get()
    inv = root.matrix_world.inverted()

    def desc(o):
        for c in o.children:
            yield c
            yield from desc(c)
    pts = []
    for o in desc(root):
        if o.type != 'MESH':
            continue
        e = o.evaluated_get(dg)
        me = e.to_mesh()
        mw = e.matrix_world
        pts += [inv @ (mw @ v.co) for i, v in enumerate(me.vertices) if i % paso == 0]
        e.to_mesh_clear()
    return pts


def _asentar_malla(cav, pos, rot, pts, iters=700, paso=0.012):
    """como _asentar pero con los vertices reales del zombie como puntos de apoyo (todos pesan igual): lo que penetre se empuja fuera; si cuelga con pocos apoyos vuelca sobre ellos hasta descansar con >= 3 apoyos"""
    from mathutils import Quaternion
    R = Euler(rot).to_matrix()
    pos = Vector(pos)
    for _ in range(iters):
        P = [pos + R @ q for q in pts]
        G = []
        for p in P:
            r = cav.find_nearest(p)
            G.append(((p - r[0]).dot(r[1]), r[1]))
        w = min(range(len(P)), key=lambda i: G[i][0])
        if G[w][0] < -0.02:
            pos += G[w][1] * (-G[w][0] + 0.01)
            continue
        sup = [i for i in range(len(P)) if G[i][0] < 0.04]
        if not sup:
            pos -= Vector((0, 0, max(0.02, G[w][0] - 0.01)))
            continue
        pv = sum((P[i] for i in sup), Vector()) / len(sup)
        tq = Vector()
        for p in P:
            tq += (p - pv).cross(Vector((0, 0, -1)))
        tq /= len(P)
        if tq.length < 0.04 and len(sup) >= 3:
            break
        if tq.length < 1e-3:
            break
        Rt = Quaternion(tq.normalized(), paso).to_matrix()
        R = Rt @ R
        pos = pv + Rt @ (pos - pv)
    return pos, R.to_euler('XYZ', Euler(rot))


def _voladizo(cav, pos, rot, pts):
    """fraccion de los puntos del cuerpo que quedan en voladizo: el suelo que tienen debajo esta mas de 0.6 m por debajo del suelo que sostiene al zombie (mediana bajo el 15 % de puntos mas bajos)"""
    R = Euler(rot).to_matrix()
    P = [pos + R @ q for q in pts[::2]]
    gz = []
    for p in P:
        r = cav.ray_cast(p + Vector((0, 0, 0.2)), Vector((0, 0, -1)), 30.0)
        gz.append(r[0].z if r[0] is not None else p.z - 30.0)
    bajos = sorted(range(len(P)), key=lambda i: P[i].z)[:max(3, len(P) // 7)]
    ref = sorted(gz[i] for i in bajos)[len(bajos) // 2]
    return sum(1 for g in gz if g < ref - 0.6) / float(len(P))


def _lejos_del_borde(cav, pos, rot, pts):
    """si el zombie quedaria con parte del cuerpo colgando sobre un desnivel (en el borde de un bloque) lo desplaza lo minimo hacia terreno plano donde quepa entero"""
    base = _voladizo(cav, pos, rot, pts)
    if base < 0.04:
        return pos
    mejor = (base, 0.0, pos)
    for rr in (0.3, 0.6, 0.9, 1.2, 1.5, 1.8, 2.1, 2.5):
        for a in range(16):
            ang = a * math.pi / 8.0
            c = pos + Vector((math.cos(ang) * rr, math.sin(ang) * rr, 0))
            r = cav.ray_cast(Vector((c.x, c.y, pos.z + 1.5)), Vector((0, 0, -1)), 6.0)
            if r[0] is None:
                continue
            c.z += r[0].z - cav.ray_cast(Vector((pos.x, pos.y, pos.z + 1.5)), Vector((0, 0, -1)), 6.0)[0].z + 0.15
            v = _voladizo(cav, c, rot, pts)
            if v < 0.04 and (mejor[0] >= 0.04 or rr < mejor[1]):
                mejor = (v, rr, c)
        if mejor[0] < 0.04:
            break
    return mejor[2]


def asentar_zombie_malla(k, f_ini, f_fin=None):
    """reposo estable del zombie k con sus vertices reales: de f_ini al ultimo frame vuelca/baja hasta quedar apoyado (acelerando) y despues se queda quieto"""
    from mathutils import Quaternion
    cav = bpy.app.driver_namespace["ruta_bvh"][0]
    root = bpy.data.objects["zombie_cav_5" + SUFIJO + str(k)]
    fz = _fcs(root)
    f_last = int(fz[("location", 0)].keyframe_points[-1].co.x)
    f_fin = f_fin or f_last - 6
    p0 = Vector([fz[("location", i)].evaluate(f_ini) for i in range(3)])
    e0 = Euler([fz[("rotation_euler", i)].evaluate(f_ini) for i in range(3)])
    pts = _puntos_malla(root, f_last)
    pf = Vector([fz[("location", i)].evaluate(f_last) for i in range(3)])
    ef = Euler([fz[("rotation_euler", i)].evaluate(f_last) for i in range(3)])
    pf = _lejos_del_borde(cav, pf, ef, pts)
    p1, e1 = _asentar_malla(cav, pf, ef, pts)
    q0, q1 = e0.to_quaternion(), e1.to_quaternion()
    prev = e0
    for fr in range(f_ini, f_last + 1):
        u = min(1.0, (fr - f_ini) / float(f_fin - f_ini))
        w = (1 - (1 - u) ** 2) if (p1 - p0).xy.length > 1.0 else (u * u * (3 - 2 * u)) ** 1.5      # si recorre mas de 1 m desliza frenando; si no, vuelca acelerando
        e = q0.slerp(q1, w).to_euler('XYZ', prev)
        prev = e
        p = p0.lerp(p1, w)
        if fr > f_ini and w < 1.0:
            p = _sin_penetrar(cav, p, tuple(e))                      # en el trayecto no atraviesa la caverna
            Rm = e.to_matrix()
            for _ in range(4):                                       # ...ni queda flotando: baja hasta que algun vertice toque
                gm = min(pp.z - (lambda r_: r_[0].z if r_[0] is not None else pp.z - 30.0)(cav.ray_cast(pp + Vector((0, 0, 0.05)), Vector((0, 0, -1)), 30.0)) for pp in (p + Rm @ q for q in pts[::2]))      # holgura VERTICAL (apoyado en el suelo, no solo rozando una pared)
                if gm < 0.03:
                    break
                p = p - Vector((0, 0, gm - 0.01))
        root.location = p
        root.rotation_euler = e
        root.keyframe_insert("location", frame=fr)
        root.keyframe_insert("rotation_euler", frame=fr)
    for fcv in fz.values():
        for kp in fcv.keyframe_points:
            kp.interpolation = 'LINEAR'
        fcv.update()
    return {"antes": [round(v, 2) for v in p0], "despues": [round(v, 2) for v in p1]}
