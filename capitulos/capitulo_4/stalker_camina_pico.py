# -*- coding: utf-8 -*-
"""alfred_cueva_5B.blend: despues del primer plano de su rostro (f546) the_stalker_1 empieza a caminar hacia el pico (alfred_pico_piedra) con un andar antinatural y asimetrico,
y la camara le da una vuelta cinematografica (de 2 m a ~7 m, ~210 grados, altura y zoom cambiantes) sin dejar de mirarlo.
Requiere haber ejecutado antes stalker_parte_zombie.py (usa POSTURA, ss, _ruido). Frames 546-F_END.
 - Andar: ciclo irregular (la cadencia se acelera y frena) con la pierna izquierda de zancada larga y abierta y la derecha corta que arrastra; el cuerpo avanza a tirones
   con la fase; columna y pecho se retuercen a contratiempo; brazo izquierdo se balancea, el derecho cuelga rigido y se abre; la cabeza se inclina y SIGUE a la camara (clamp +-1 rad).
Uso: exec(stalker_parte_zombie.py); exec(este); caminar()    (repetible)
"""
import bpy, math
from mathutils import Vector, Euler

F0, F_OLD, F_END = 546, 780, 930        # F_OLD: fin de la vuelta de camara original; de F_OLD a F_END la camara sigue girando y se acerca
CICLO = 38.0                       # frames por paso medio
VEL = 0.09                         # m/frame medios
PICO = Vector((2.4, 78.4, 6.05))


def _fase(fr):
    t = fr - F0
    return 2 * math.pi * t / CICLO + 0.6 * math.sin(2 * math.pi * t / 110.0)


def caminar():
    O, sc = bpy.data.objects, bpy.context.scene
    st, ar, cam = O["the_stalker_1"], O["torso_1"], sc.camera
    PB = ar.pose.bones
    sc.frame_set(1)                    # el origen del recorrido es la posicion de reposo (frame 1), nunca la del frame en que este la escena
    yaw = st.matrix_world.to_euler().z
    f = Vector((-math.sin(yaw), math.cos(yaw), 0))
    r = Vector((math.cos(yaw), math.sin(yaw), 0))
    # posicion de reposo = la PRIMERA clave de location (nunca la evaluada en un frame ya animado)
    claves0 = [min(fc.keyframe_points, key=lambda k: k.co.x).co.y for ax in range(3) for l_ in st.animation_data.action.layers for s_ in l_.strips for cb_ in s_.channelbags for fc in cb_.fcurves if fc.data_path == "location" and fc.array_index == ax]
    inicio = Vector(claves0)
    D = Vector((PICO.x - inicio.x, PICO.y - inicio.y, 0)).normalized()
    sc.frame_end = max(sc.frame_end, F_END)
    # quitar claves anteriores de lo que se reescribe (> F0-1)
    def limpia(idb, prefijos=None):
        if not idb.animation_data or not idb.animation_data.action:
            return
        for l in idb.animation_data.action.layers:
            for s in l.strips:
                for cb in s.channelbags:
                    for fc in cb.fcurves:
                        if prefijos is None or fc.data_path.startswith(prefijos):
                            for i in range(len(fc.keyframe_points) - 1, -1, -1):
                                if fc.keyframe_points[i].co.x >= F0:
                                    fc.keyframe_points.remove(fc.keyframe_points[i], fast=True)
    huesos = ("spine_1", "chest_1", "head_1", "thigh.L_1", "thigh.R_1", "upper_arm.L_1", "upper_arm.R_1", "root_1")
    limpia(ar, tuple('pose.bones["%s"]' % h for h in huesos))
    limpia(st)
    limpia(cam.data if False else cam)
    # posicion del Stalker a tirones, segun la fase
    s_acum, pos = 0.0, {}
    for fr in range(F0 - 1, F_END + 1):
        if fr >= F0:
            ph = _fase(fr)
            v = VEL * (0.45 + 0.55 * (0.5 + 0.5 * math.sin(ph + 0.6))) * ss((fr - F0) / 25.0)
            s_acum += v
        pos[fr] = inicio + D * s_acum
    # camara: calibracion de la cabeza (a que direccion mira con y=-0.2 en f535)
    psi0 = math.atan2(f.y, f.x)
    # claves
    dg = bpy.context.evaluated_depsgraph_get()

    def suelo(x, y, z0):
        """suelo bajo (x, y) buscando hacia abajo desde un poco mas arriba del que pisaba (asi no se sube a techos ni salientes altos)"""
        p = Vector((x, y, z0 + 1.2))
        for _ in range(8):
            rr = sc.ray_cast(dg, p, Vector((0, 0, -1)), distance=6)
            if not rr[0]:
                return None
            if rr[4].name.startswith("caverna_"):
                return rr[1].z
            p = rr[1] - Vector((0, 0, 0.01))
    zs, zprev = {}, inicio.z
    for fr in sorted(pos):
        zz = suelo(pos[fr].x, pos[fr].y, zprev)
        zprev = zz if zz is not None else zprev
        zs[fr] = zprev
    for fr in range(F0 - 1, F_END + 1):
        w = [zs[g] for g in range(max(F0 - 1, fr - 3), min(F_END, fr + 3) + 1)]
        st.location = Vector((pos[fr].x, pos[fr].y, sum(w) / len(w)))
        st.keyframe_insert("location", frame=fr)
    def rn(fr, semilla, amp, freq=0.07, dim=0):
        return amp * _ruido(fr, freq, semilla, dim)

    def q(x, y, z):
        return Euler((x, y, z)).to_quaternion()
    todos = [b.name for b in PB if b.name.startswith(("shin", "forearm", "tent_finger", "tent_thumb", "thigh", "upper_arm", "spine_1", "chest_1", "neck_1", "jaw_1", "root_1"))]
    limpia(ar, tuple('pose.bones["%s"]' % h for h in todos))
    for n in todos:
        if n != "root_1":
            PB[n].rotation_mode = 'QUATERNION'
    # clave de partida (f545) con la postura base para que la entrada sea suave
    for n in todos:
        if n == "root_1":
            continue
        base = Euler(POSTURA[n]).to_quaternion() if n in POSTURA else Euler((0, 0, 0)).to_quaternion()
        PB[n].rotation_quaternion = base
        PB[n].keyframe_insert("rotation_quaternion", frame=F0 - 1)
    semillas = {n: 100 + i for i, n in enumerate(todos)}
    for fr in range(F0, F_END + 1):
        ph = _fase(fr)
        sw = ss((fr - F0) / 20.0)                       # entrada gradual del movimiento
        sL, sR = math.sin(ph), math.sin(ph + 2.5)
        cL, cR = math.cos(ph), math.cos(ph + 2.5)
        sa = math.sin(ph + 3.1)                          # balanceo del brazo izquierdo (contrario a la pierna izquierda)
        E = {}
        # piernas: izquierda larga, abierta y con rodilla muy flexionada al avanzar; derecha corta, rigida y arrastrada
        E["thigh.L_1"] = (0.14 + sw * 0.55 * sL, sw * 0.12 * sL, -0.45 - sw * 0.2 * max(0.0, sL))
        E["thigh.R_1"] = (0.14 + sw * 0.28 * sR, sw * 0.05 * sR, 0.45 + sw * 0.06 * cR)
        E["shin.L_1"] = (-sw * (0.30 + 1.0 * max(0.0, cL)), 0, sw * 0.08 * sL)
        E["shin.R_1"] = (-sw * (0.60 + 0.25 * max(0.0, cR)), 0, -sw * 0.05 * sR)
        # brazos: izquierdo se balancea con el codo que se dobla al ir hacia delante; derecho cuelga rigido y se abre
        E["upper_arm.L_1"] = (sw * 0.75 * sa, sw * 0.2 * sa, -sw * 0.15)
        E["forearm.L_1"] = (sw * (0.45 + 0.9 * max(0.0, math.sin(ph + 3.7))), 0, sw * 0.10 * math.sin(ph * 0.5))
        E["upper_arm.R_1"] = (sw * (-0.18 + 0.08 * math.sin(ph * 0.5)), 0, sw * (0.30 + 0.20 * math.sin(ph * 0.5 + 1.0)))
        E["forearm.R_1"] = (sw * (1.05 + 0.15 * math.sin(ph * 0.5 + 0.8)), 0, sw * 0.12 * math.sin(ph * 0.5 + 2.0))
        # dedos: sin animacion (se quedan en reposo para que no se separen de la mano)
        # cuello, mandibula (se abre a espasmos) y tronco retorcido a contratiempo
        E["neck_1"] = (POSTURA["neck_1"][0] + sw * 0.10 * math.sin(2 * ph + 0.4), POSTURA["neck_1"][1], POSTURA["neck_1"][2] + sw * 0.10 * math.sin(ph * 0.5 + 1.0))
        E["jaw_1"] = (sw * 0.30 * max(0.0, math.sin(ph * 0.9 + 2.0)) ** 3, 0, 0)
        E["spine_1"] = tuple(POSTURA["spine_1"][i] + (0.0, sw * 0.25 * math.sin(ph), sw * (0.12 * math.sin(ph + 1.2) + 0.10 * math.sin(ph * 0.5)))[i] for i in range(3))
        E["chest_1"] = tuple(POSTURA["chest_1"][i] + (0.0, -sw * 0.20 * math.sin(ph + 0.4), sw * 0.08 * math.sin(ph * 0.5 + 2.0))[i] for i in range(3))
        # filtros organicos encima de todos los huesos: respiracion en columna/pecho y micro-movimiento aleatorio en el resto
        for n, e in E.items():
            amp = 0.012 if n.startswith(("tent", "jaw")) else 0.03
            if n in ("spine_1", "chest_1"):
                resp = 0.03 * math.sin(2 * math.pi * 0.012 * fr + 1)
            else:
                resp = 0.0
            sd = semillas[n]
            ex = e[0] + resp + rn(fr, sd, amp, 0.07, 0)
            ey = e[1] + rn(fr, sd, amp * 0.6, 0.07, 1)
            ez = e[2] + rn(fr, sd, amp * 0.8, 0.07, 2)
            PB[n].rotation_quaternion = Euler((ex, ey, ez)).to_quaternion()
            PB[n].keyframe_insert("rotation_quaternion", frame=fr)
        PB["root_1"].location = (rn(fr, 7, 0.02, 0.05, 0) * 2 + sw * 0.03 * math.sin(ph), -0.0876 - sw * 0.05 * (0.5 + 0.5 * math.sin(2 * ph)) + rn(fr, 8, 0.01, 0.06, 1), sw * 0.04 * math.sin(ph))
        PB["root_1"].keyframe_insert("location", frame=fr)
    return pos


def camara_orbita(pos):
    """vuelta cinematografica: sigue a la criatura; ademas la cabeza gira para mantener la mirada en la camara"""
    O, sc = bpy.data.objects, bpy.context.scene
    st, ar, cam = O["the_stalker_1"], O["torso_1"], sc.camera
    PB = ar.pose.bones
    yaw = st.matrix_world.to_euler().z
    f = Vector((-math.sin(yaw), math.cos(yaw), 0))
    r = Vector((math.cos(yaw), math.sin(yaw), 0))
    a = cam.animation_data.action
    fcs = {(fc.data_path, fc.array_index): fc for l in a.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves}
    for fc in fcs.values():
        for i in range(len(fc.keyframe_points) - 1, -1, -1):
            if fc.keyframe_points[i].co.x >= F0:
                fc.keyframe_points.remove(fc.keyframe_points[i], fast=True)
    sc.frame_set(F0 - 1)
    e0 = Euler([fcs[("rotation_euler", i)].evaluate(F0 - 1) for i in range(3)])
    prev = e0
    psi0 = math.atan2(f.y, f.x)
    fz = next(fc for l_ in st.animation_data.action.layers for s_ in l_.strips for cb_ in s_.channelbags for fc in cb_.fcurves if fc.data_path == "location" and fc.array_index == 2)
    for fr in range(F0, F_END + 1):
        dz = fz.evaluate(fr) - 6.02                 # el suelo sube y baja: la camara y su objetivo acompanan esa altura
        u = min(1.0, (fr - F0) / float(F_OLD - F0))
        w = ss((fr - F_OLD) / float(F_END - F_OLD)) if fr > F_OLD else 0.0       # tramo extra: sigue girando y se acerca
        th = 3.7 * ss(u) + 1.5 * w
        R = 2.0 + 5.2 * ss((fr - F0) / 60.0) - 2.7 * w
        H = 8.2 + 1.2 * math.sin(1.5 * math.pi * u) if u > 0 else 8.05
        H = 8.05 + (H - 8.05) * ss(u * 4) + 0.8 * w
        c = pos[fr]
        d = f * math.cos(th) + r * math.sin(th)
        campos = Vector((c.x + 0.2 * f.x, c.y + 0.2 * f.y, 0)) + d * R
        campos.z = H + dz
        tz = 8.05 + (7.3 - 8.05) * ss((R - 2.0) / 3.0)
        tg = Vector((c.x + 0.35 * f.x, c.y + 0.35 * f.y, tz + dz))
        e = (tg - campos).to_track_quat('-Z', 'Y').to_euler('XYZ', prev)
        prev = e
        for i in range(3):
            fcs[("location", i)].keyframe_points.insert(fr, campos[i], options={'FAST'})
            fcs[("rotation_euler", i)].keyframe_points.insert(fr, e[i], options={'FAST'})
        lens = (40 + (28 - 40) * ss(u / 0.4) + (34 - 28) * ss((u - 0.4) / 0.6) if u > 0.4 else 40 + (28 - 40) * ss(u / 0.4)) + 4.0 * w
        fcs[("lens", 0)].keyframe_points.insert(fr, lens, options={'FAST'})
        # cabeza: gira hacia la camara (clamp +-1)
        ph = _fase(fr)
        sw = ss((fr - F0) / 20.0)
        psi = math.atan2(campos.y - c.y, campos.x - c.x)
        dpsi = (psi - psi0 + math.pi) % (2 * math.pi) - math.pi
        yy = max(-1.0, min(1.0, -0.2 + dpsi / 0.95))
        giro = Euler((0, yy, -0.2)).to_quaternion()
        ex, ey, ez = (0.05 * math.sin(2 * math.pi * 0.012 * fr + 3) + 0.025 * _ruido(fr, 0.07, 3, 0), 0.02 * _ruido(fr, 0.07, 3, 1), 0.04 * _ruido(fr, 0.07, 3, 2))
        tilt = Euler((0, 0, sw * 0.18 * math.sin(ph * 0.5 + 2.0))).to_quaternion()
        PB["head_1"].rotation_quaternion = Euler(POSTURA["head_1"]).to_quaternion() @ giro @ tilt @ Euler((ex, ey, ez)).to_quaternion()
        PB["head_1"].keyframe_insert("rotation_quaternion", frame=fr)
    for fc in fcs.values():
        fc.update()
    # interpolacion lineal de lo que se acaba de crear (un clave por frame)
    for idb in (ar, st):
        for l in idb.animation_data.action.layers:
            for s in l.strips:
                for cb in s.channelbags:
                    for fc in cb.fcurves:
                        for kp in fc.keyframe_points:
                            if kp.co.x >= F0 - 1:
                                kp.interpolation = 'LINEAR'
                        fc.update()
    sc.frame_set(F0)
