# -*- coding: utf-8 -*-
"""base_ranas_3, FASE 5 "Derribo" (frames de base_ranas_3, despues de regenerar la pelea con la variante ranas3 y desplazarla):
 1. (309-316) el guardian toma impulso y salta con un punetazo volador a la CARA de Alfred.
 2. (316-336) Alfred sale despedido: gira un poco con el golpe y cae de espaldas (pivota sobre los pies, cae acelerando),
    rebota y queda BOCA ARRIBA. Cae en direccion tangente a la antorcha (asi no la toca ni se sale del ring).
 3. (316-326) el guardian aterriza junto a las piernas de Alfred; (330-342) salta y se SUBE A SU PECHO.
 4. (344-FIN) le pega en la cara alternando punos (cada 9 f), inclinado sobre el; con cada golpe la cabeza de Alfred se
    va al lado contrario. Alfred primero manotea / empuja (344-378), despues se cubre la cara con los brazos, y patalea.
Reemplaza las claves de Alfred (raiz y huesos) desde F_CAE y del guardian desde F0 hasta el final.
Uso (exec en Blender): construir()
"""
import bpy, math
from mathutils import Vector, Matrix, Euler

DIR = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/"
bpy.app.driver_namespace["pelea_variante"] = "ranas3"
L = {"__name__": "luch"}
exec(open(DIR + "luchadores_rodean.py", encoding="utf-8").read(), L)
ik2, apuntar, rotar_mundo, suela, ss, ejes, desenrollar = L["ik2"], L["apuntar"], L["rotar_mundo"], L["suela"], L["ss"], L["ejes"], L["desenrollar"]
C, UP = L["C"], L["UP"]
sc = bpy.context.scene; vl = bpy.context.view_layer
D = math.radians

F0, F_IMP, F_CAE, F_SUELO, F_QUIETO = 309, 316, 316, 329, 336
F_ATERRIZA, F_SALTA, F_PECHO, F_GOLPES = 326, 330, 342, 344
F_CUBRE = 378
# valores del usuario (frame 338) para Alfred ya en el suelo: raiz y brazos
USER_LOC = (-37.7317, -10.9022, 9.027)
USER_ROT = (83.452, 1.026, 99.489)
USER_BRAZOS = {"LeftUpArm_alfred": (-17.709, -13.181, -15.66), "RightUpArm_alfred": (-13.185, 1.471, 18.483)}
BRAZOS_VENTANA = (330, 334, 342, 348)
CAIDA_HACIA = (0.89, 0.46, 0.0)              # hacia +x y un poco al norte (flecha del usuario); None = tangente a la antorcha
CADA = 9
VALLA = dict(x0=-40.5, x1=-34.5, y0=-14.5, y1=-9.5)
A_HUESOS = ["Hips_alfred", "Spine_alfred", "Spine1_alfred", "Spine2_alfred", "Neck_alfred", "face_alfred",
            "RightUpArm_alfred", "Rightelbow_alfred", "LeftUpArm_alfred", "Leftelbow_alfred",
            "RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred"]
G_HUESOS = ["body_guard_ribbit_1", "left_arm_guard_ribbit_1", "right_arm_guard_ribbit_1", "right_leg_guard_ribbit_1", "left_leg_guard_ribbit_1"]


def snap(u): u = min(1.0, max(0.0, u)); return 1 - (1 - u) ** 4


def ease_in(u): u = min(1.0, max(0.0, u)); return u * u


def ramp(f, a, b): return ss((f - a) / float(max(1e-6, b - a)))


def fcs(o):
    return [fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


def leer(o, paths, f):
    """valores de las curvas en el frame f: {(data_path, i): v}"""
    return {(fc.data_path, fc.array_index): fc.evaluate(f) for fc in fcs(o) if fc.data_path in paths}


# ---- golpes del guardian sentado en el pecho: (frame de inicio, lado "R"/"L"/"M" (martillo: los dos), fuerza)
PROGRAMA = [(344, "R", 0.7), (351, "L", 0.9), (359, "R", 1.25),                    # combo de 3: el ultimo mas fuerte
            (377, "L", 0.6), (383, "R", 0.75), (390, "L", 1.0),                    # (pausa: respira)
            (404, "M", 1.6),                                                       # martillo con los dos punos
            (425, "R", 0.8), (432, "L", 0.85), (440, "R", 1.15)]


def tiempos(lado, fuerza):
    """(carga, sale, impacto congelado, vuelta) en frames: mas fuerza = mas carga y mas recuperacion"""
    if lado == "M": return 8, 2, 2, 8
    return int(round(2 + 2.5 * fuerza)), 2, 1, int(round(4 + 2.5 * fuerza))


def contacto(g):
    st, lado, fu = g; W, S, H, R = tiempos(lado, fu); return st + W + S


def ext_golpe(t, lado, fuerza):
    """posicion del puno: <0 carga (atras y arriba), 1 = en la cara (con un pelo de sobrepaso), vuelve con rebote"""
    W, S, H, R = tiempos(lado, fuerza)
    if t < 0 or t >= W + S + H + R: return None
    if t < W: return -0.55 * ss(t / float(W))                                    # anticipacion
    if t < W + S: return -0.55 + 1.63 * snap((t - W + 1) / float(S))              # disparo explosivo (sobrepasa: 1.08)
    if t < W + S + H: return 1.08                                                # congelado en el impacto
    u = (t - W - S - H) / float(R)
    return 1.08 * (1 - ss(u)) - 0.12 * math.sin(math.pi * min(1.0, u * 1.4)) * (1 - u)   # retrocede y rebota


def resp(t, tau=2.0, extra=0.22):
    """respuesta al impacto (cabeza, pecho...): sube rapido (pico 1 en tau frames), vuelve y se pasa un poco (resorte)"""
    if t < 0: return 0.0
    r = (t / tau) * math.exp(1 - t / tau)
    if t > 3 * tau: r -= extra * math.exp(-(t - 3 * tau) / 6.0) * math.sin(math.pi * (t - 3 * tau) / 7.0)
    return r


def rebote(t, amp=1.0, per=5.0, amort=0.32):
    """rebote amortiguado (contacto con el suelo)"""
    if t < 0: return 0.0
    return amp * math.exp(-amort * t) * abs(math.sin(math.pi * t / per))


def construir():
    ra, aa = bpy.data.objects["alfred"], bpy.data.objects["Armature"]
    rg, ag = bpy.data.objects["guard_ribbit_1"], bpy.data.objects["main_guard_ribbit_1"]
    PA, PG = aa.pose.bones, ag.pose.bones; WA = lambda: aa.matrix_world; WG = lambda: ag.matrix_world
    FIN = min(sc.frame_end, 454)                                  # (despues sigue pelea_victoria.py)
    # ---------------- estado de partida (lo que dejo la pelea generada)
    FA, FG = F_CAE - 1, F0 - 1                                   # (frames anteriores al tramo: repetible, no lee lo ya reemplazado)
    a_root0 = leer(ra, ("location", "rotation_euler"), FA); g_root0 = leer(rg, ("location", "rotation_euler"), FG)
    A0 = Vector([a_root0[("location", i)] for i in range(3)]); yawA0 = a_root0[("rotation_euler", 2)]
    G0 = Vector([g_root0[("location", i)] for i in range(3)]); yawG0 = g_root0[("rotation_euler", 2)]
    rotA = {h: leer(aa, ('pose.bones["%s"].rotation_euler' % h,), FA) for h in A_HUESOS}
    rotA = {h: Vector([d.get(('pose.bones["%s"].rotation_euler' % h, i), 0.0) for i in range(3)]) for h, d in rotA.items()}
    rotG = {h: leer(ag, ('pose.bones["%s"].rotation_euler' % h,), FG) for h in G_HUESOS}
    rotG = {h: Vector([d.get(('pose.bones["%s"].rotation_euler' % h, i), 0.0) for i in range(3)]) for h, d in rotG.items()}
    ocultos = [o.name for r in (ra, rg) for o in [r] + list(r.children_recursive) if o.hide_viewport]
    for n in ocultos: bpy.data.objects[n].hide_viewport = False
    acts = (ra.animation_data.action, aa.animation_data.action, rg.animation_data.action, ag.animation_data.action)
    ra.animation_data.action = aa.animation_data.action = rg.animation_data.action = ag.animation_data.action = None
    try:
        # ---------------- hacia donde cae Alfred: tangente a la antorcha (el lado con mas sitio en el ring)
        rad = A0 - C; rad.z = 0; rad.normalize(); tg = UP.cross(rad)
        def holgura(d):
            p = A0 + d * 2.2
            return min(p.x - VALLA["x0"], VALLA["x1"] - p.x, p.y - VALLA["y0"], VALLA["y1"] - p.y)
        caida = tg if holgura(tg) >= holgura(-tg) else -tg
        caida = (caida * 0.85 + rad * 0.15).normalized()                         # un poco hacia afuera de la antorcha
        if CAIDA_HACIA is not None:                                              # direccion marcada por el usuario
            caida = Vector(CAIDA_HACIA).normalized()
            while holgura(caida) < 0.45 and caida.y > 0.02:                     # sin meter la cabeza en la valla norte
                caida = Vector((caida.x, caida.y - 0.05, 0)).normalized()
        yaw_caida = math.atan2(caida.x, -caida.y)                               # su frente mira al lado contrario de la caida
        while yaw_caida - yawA0 > math.pi: yaw_caida -= 2 * math.pi
        while yaw_caida - yawA0 < -math.pi: yaw_caida += 2 * math.pi
        if USER_ROT is not None:                                                 # orientacion final que puso el usuario
            yaw_caida = D(USER_ROT[2])
            while yaw_caida - yawA0 > math.pi: yaw_caida -= 2 * math.pi
            while yaw_caida - yawA0 < -math.pi: yaw_caida += 2 * math.pi
            caida = Vector((math.sin(yaw_caida), -math.cos(yaw_caida), 0))
        AX = USER_ROT[0] if USER_ROT is not None else 90.0
        fw_c, rt_c = ejes(yaw_caida)
        # ---------------- ALFRED
        out_a = {"loc": [], "rot": [], "h": {h: [] for h in A_HUESOS}}; caras = {}; pechos = {}; arriba_pecho = {}
        golpes = list(PROGRAMA)
        CAE0 = F_CAE + 2                                                          # la cabeza sale primero; el cuerpo cae 2 f despues
        def reaccion(f, retraso=0):
            """suma de las respuestas a todos los golpes: (lateral con signo, fuerza total)"""
            lat, tot = 0.0, 0.0
            for g in golpes:
                tc = contacto(g); st, lado, fu = g; r = resp(f - tc - retraso)
                cubre = 0.5 if tc >= F_CUBRE else 1.0
                sg = 0.0 if lado == "M" else (1.0 if lado == "R" else -1.0)
                lat += sg * fu * r * cubre; tot += fu * r * cubre
            return lat, tot
        for f in range(F_CAE, FIN + 1):
            u = (f - CAE0) / float(F_SUELO - CAE0)
            if f < CAE0: ang = 4.0 * (f - F_CAE)                                  # el golpe lo frena (hit-stop) y empieza a irse atras
            elif f <= F_SUELO: ang = 8.0 + (AX - 8.0) * ease_in(u)               # cae acelerando
            else: ang = AX - rebote(f - F_SUELO, 11.0, 5.0, 0.30)                 # rebota contra el suelo y se asienta
            yaw = yawA0 + (yaw_caida - yawA0) * snap((f - F_CAE) / 6.0)
            if USER_LOC is not None: pos = A0.lerp(Vector(USER_LOC), snap((f - F_CAE) / 8.0)); pos.z = A0.z
            else: pos = A0 - caida * 0.25 * snap((f - F_CAE) / 8.0); pos.z = A0.z
            giro_y = D(USER_ROT[1]) * ramp(f, F_CAE, F_SUELO) if USER_ROT is not None else 0.0
            ra.location = pos; ra.rotation_euler = (D(ang), giro_y, yaw)
            k_base = 1 - ramp(f, F_CAE, F_CAE + 4)
            for h in A_HUESOS: PA[h].rotation_mode = 'XYZ'; PA[h].rotation_euler = rotA[h] * k_base
            vl.update()
            M = ra.matrix_world.to_3x3(); fw = (M @ Vector((0, 1, 0))).normalized(); up = (M @ Vector((0, 0, 1))).normalized(); rt = (M @ Vector((1, 0, 0))).normalized()
            # cabeza: latigazo con el punetazo volador; en el suelo rebota; cada golpe la manda al lado contrario
            lat, tot = reaccion(f); lat_t, tot_t = reaccion(f, 1); lat_l, tot_l = reaccion(f, 2)   # (el cuerpo y los miembros llegan despues)
            latigazo = 38.0 * resp(f - F_CAE, 1.5, 0.3)
            suelo_c = rebote(f - F_SUELO - 1, 14.0, 5.0, 0.35)
            rotar_mundo(aa, "Spine2_alfred", rt, D(6.0 * tot_t))                  # el pecho se hunde con el golpe
            rotar_mundo(aa, "Neck_alfred", rt, D(latigazo * 0.8 + suelo_c + 8.0 * tot))
            rotar_mundo(aa, "Neck_alfred", up, D(30.0 * lat + 12.0 * resp(f - F_CAE, 1.5)))
            rotar_mundo(aa, "face_alfred", up, D(16.0 * lat_t))                   # la cara sigue a la nuca (superposicion)
            vl.update()
            cara = WA() @ PA["face_alfred"].head + (WA() @ PA["face_alfred"].tail - WA() @ PA["face_alfred"].head) * 0.35
            # brazos: arrastrados al caer (llegan tarde), sacudon con cada golpe
            for s, lado in (("Right", 1), ("Left", -1)):
                sh = WA() @ PA[s + "UpArm_alfred"].head
                arriba = sh + up * 0.55 + rt * lado * 0.55
                if f <= F_QUIETO + 4:
                    lag = ramp(f, CAE0 + 2, F_SUELO + 1)                          # al principio quedan atras y suben despues
                    T = (sh + fw * 0.35 - up * 0.10 + rt * lado * 0.30).lerp(arriba, lag) + fw * 0.12 * rebote(f - F_SUELO - 2, 1.0, 5.0, 0.3)
                elif f < F_CUBRE:                                                 # manotea / empuja al guardian
                    ph = 2 * math.pi * f / 11.0 + (0 if lado > 0 else 2.0)
                    T = sh + fw * (0.45 + 0.15 * math.sin(ph)) + up * (0.25 + 0.12 * math.cos(ph)) + rt * lado * (0.25 + 0.08 * math.sin(ph * 0.7))
                else:                                                             # se cubre la cara (cada vez mas debil)
                    deb = ramp(f, F_CUBRE + 40, FIN)
                    cubre = cara + fw * 0.18 + rt * lado * 0.10 + up * 0.05
                    caido = sh + rt * lado * 0.45 + up * 0.15 - fw * 0.10
                    T = cubre.lerp(caido, 0.6 * deb) + fw * 0.03 * math.sin(f * 0.9 + lado)
                if F_QUIETO < f < F_CUBRE + 6: T = arriba.lerp(T, ramp(f, F_QUIETO, F_QUIETO + 8))
                T = T + rt * lado * 0.10 * tot_l - fw * 0.06 * tot_l               # sacudon (llega 2 f tarde)
                ik2(aa, s + "UpArm_alfred", s + "elbow_alfred", T, -fw + rt * lado * 0.5)
            # piernas: rectas al caer; rebotan al tocar el suelo; patalean y dan un respingo con cada golpe
            for s, lado, fase in (("Right", 1, 0.0), ("Left", -1, 2.4)):
                hip = WA() @ PA[s + "UpLeg_alfred"].head
                pata = 0.0 if f < F_QUIETO else max(0.0, 0.05 + 0.09 * math.sin(2 * math.pi * f / 13.0 + fase)) * (1 - 0.6 * ramp(f, F_CUBRE + 40, FIN))
                pata += 0.10 * rebote(f - F_SUELO - 2, 1.0, 6.0, 0.35) + 0.07 * tot_l
                pie = hip - up * 0.93 + up * pata + fw * 0.02 + rt * lado * 0.10
                ik2(aa, s + "UpLeg_alfred", s + "knee_alfred", pie, fw + up * 0.2)
            # en el suelo: la espalda apoya en el pasto (z minima de la malla = 9.0)
            # brazos: los valores del usuario al quedar tendido
            wb = ramp(f, BRAZOS_VENTANA[0], BRAZOS_VENTANA[1]) * (1 - ramp(f, BRAZOS_VENTANA[2], BRAZOS_VENTANA[3]))
            if wb > 0:
                for h, e in USER_BRAZOS.items():
                    q = PA[h].rotation_euler.to_quaternion().slerp(Euler(tuple(D(x) for x in e)).to_quaternion(), wb)
                    PA[h].rotation_euler = q.to_euler('XYZ', PA[h].rotation_euler)
            vl.update(); z = suela(ra)
            if USER_LOC is not None and f >= F_SUELO:                            # tendido: la altura que puso el usuario (+ rebote)
                ra.location.z = USER_LOC[2] + 0.05 * rebote(f - F_SUELO, 1.0, 5.0, 0.30); vl.update()
            elif f >= F_SUELO - 2 or z < 9.0: ra.location.z += 9.0 - z; vl.update()
            caras[f] = WA() @ PA["face_alfred"].head + (WA() @ PA["face_alfred"].tail - WA() @ PA["face_alfred"].head) * 0.35
            pechos[f] = WA() @ PA["Spine2_alfred"].head
            # punto mas alto del pecho (donde se sienta el guardian)
            dg = bpy.context.evaluated_depsgraph_get(); zt = -1e9
            for x in ra.children:
                if x.type == 'MESH' and x.name.startswith("Mesh_"):
                    e = x.evaluated_get(dg); Mx = x.matrix_world
                    for v in e.data.vertices:
                        w = Mx @ v.co
                        if (Vector((w.x, w.y)) - Vector((pechos[f].x, pechos[f].y))).length < 0.18: zt = max(zt, w.z)
            arriba_pecho[f] = zt if zt > -1e8 else pechos[f].z + 0.15
            out_a["loc"].append((f, tuple(ra.location))); out_a["rot"].append((f, tuple(ra.rotation_euler)))
            for h in A_HUESOS: out_a["h"][h].append((f, tuple(PA[h].rotation_euler)))
        # ---------------- GUARDIAN
        out_g = {"loc": [], "rot": [], "h": {h: [] for h in G_HUESOS}}
        cara_imp = caras[F_CAE]
        P_hit = cara_imp - Vector((0, 0, 0.45)) + (G0 - cara_imp).normalized() * 0.15
        P_hit.z = cara_imp.z - 0.62
        lado_pies = (rt_c if (A0 + rt_c * 0.7 - C).length > (A0 - rt_c * 0.7 - C).length else -rt_c)
        P_land = A0 + lado_pies * 0.75; P_land.z = 9.0
        ys = []
        for f in range(F0, FIN + 1):
            mira = None
            if f <= F_IMP:                                                       # impulso y salto al punetazo volador
                u = (f - F0) / float(F_IMP - F0)
                p = G0.lerp(Vector((P_hit.x, P_hit.y, G0.z)), ss(u)); p.z = G0.z + (P_hit.z - G0.z) * math.sin(0.5 * math.pi * min(1.0, u * 1.15)) if u > 0.3 else G0.z
                mira = cara_imp
            elif f <= F_ATERRIZA:                                               # cae junto a las piernas de Alfred
                u = (f - F_IMP) / float(F_ATERRIZA - F_IMP)
                p = P_hit.lerp(P_land, ss(u)); p.z = P_hit.z * (1 - u * u) + 9.0 * u * u + 0.15 * math.sin(math.pi * u)
                mira = caras[min(f, FIN)]
            elif f < F_SALTA:
                p = P_land.copy(); mira = caras[f]
            elif f <= F_PECHO:                                                  # salta al pecho
                u = (f - F_SALTA) / float(F_PECHO - F_SALTA); dest = pechos[f].copy(); dest.z = arriba_pecho[f] - 0.03
                p = P_land.lerp(dest, ss(u)); p.z = 9.0 + (dest.z - 9.0) * ss(u) + 0.45 * math.sin(math.pi * u)
                mira = caras[f]
            else:                                                                # sentado en el pecho, mira a la cara
                p = pechos[f].copy(); p.z = arriba_pecho[f] - 0.03
                mira = caras[f]
            d = mira - p; d.z = 0
            ys.append(math.atan2(-d.x, d.y) if d.length > 1e-4 else yawG0)
            out_g["loc"].append((f, tuple(p)))
        ys = desenrollar([yawG0] + ys)[1:]
        for i, f in enumerate(range(F0, FIN + 1)):
            p = Vector(out_g["loc"][i][1]); yaw = ys[i]
            if f <= F0 + 3: yaw = yawG0 + (yaw - yawG0) * ss((f - F0) / 3.0)
            pitch = 0.0
            if F_IMP - 3 <= f <= F_IMP + 4: pitch = D(-38) * math.sin(math.pi * (f - (F_IMP - 3)) / 7.0)   # se estira en el punetazo
            rg.location = p; rg.rotation_euler = (pitch, 0, yaw)
            k_base = 1 - ramp(f, F0, F0 + 3)
            for h in G_HUESOS: PG[h].rotation_mode = 'XYZ'; PG[h].rotation_euler = rotG[h] * k_base
            vl.update()
            R3 = rg.matrix_world.to_3x3(); fw = (R3 @ Vector((0, 1, 0))).normalized(); rt = (R3 @ Vector((1, 0, 0))).normalized(); up = (R3 @ Vector((0, 0, 1))).normalized()
            sentado = f > F_PECHO
            # ---- accion y reaccion de cada golpe (se suman: los golpes se encadenan)
            act = {}; giro = 0.0; inclina = 0.0; dz = 0.0
            for g in golpes:
                st, lado, fu = g; t = f - st; x = ext_golpe(t, lado, fu)
                if x is None: continue
                W, S_, H, R = tiempos(lado, fu); tc = st + W + S_
                sg = 0.0 if lado == "M" else (1.0 if lado == "R" else -1.0)
                carga = ss(t / float(W)) if t < W else 0.0
                suelta = snap((t - W + 1) / float(S_)) if t >= W else 0.0
                vuelve = 1 - ss((t - W - S_ - H) / float(R + 3)) if t > W + S_ + H else 1.0
                giro += -sg * 22.0 * fu * carga + sg * 30.0 * fu * suelta * vuelve       # carga girando al lado contrario y descarga
                inclina += -12.0 * fu * carga + 16.0 * fu * suelta * vuelve             # se echa atras al cargar, encima al pegar
                dz += 0.05 * fu * carga - 0.05 * fu * resp(f - tc, 1.5, 0.35)           # sube al cargar, se hunde al pegar y rebota
                for s_ in (("right", "left") if lado == "M" else (("right",) if lado == "R" else ("left",))): act[s_] = (x, fu, lado)
            # el brazo que no pega hace de contrapeso (va atras)
            contra = {s_: 0.0 for s_ in ("right", "left")}
            for s_ in contra:
                otro = "left" if s_ == "right" else "right"
                if otro in act and s_ not in act and act[otro][0] > 0: contra[s_] = act[otro][0]
            base_inc = (-12 + (-26 if sentado else 0)) if f > F_IMP + 4 else -12
            if F0 <= f < F_IMP - 3: base_inc += 18 * math.sin(math.pi * (f - F0) / float(F_IMP - 3 - F0))   # se agacha para tomar impulso
            rotar_mundo(ag, "body_guard_ribbit_1", rt, D(base_inc - inclina))
            rotar_mundo(ag, "body_guard_ribbit_1", UP, D(giro + 3.0 * math.sin(f * 0.21)))
            for s, lado in (("left", -1), ("right", 1)):
                b = "%s_arm_guard_ribbit_1" % s; hom = WG() @ PG[b].head
                respira = 0.025 * math.sin(2 * math.pi * f / 26.0)
                T = hom + fw * 0.20 + up * (0.06 + respira) + rt * (-lado) * 0.04
                if F0 <= f < F_IMP - 3: T = T.lerp(hom - fw * 0.12 + up * 0.10 + rt * lado * 0.10, math.sin(math.pi * (f - F0) / float(F_IMP - 3 - F0)))   # brazos atras (impulso)
                if F_IMP - 3 <= f <= F_IMP + 1 and s == "right":                # punetazo volador (+ congelado en el impacto)
                    T = T.lerp(cara_imp, snap((f - (F_IMP - 3)) / 3.0))
                if F_IMP + 1 < f <= F_ATERRIZA:                                   # rebota hacia atras y abre los brazos para caer
                    T = T.lerp(hom + rt * lado * 0.25 + up * 0.15 - fw * 0.05, ramp(f, F_IMP + 1, F_IMP + 4))
                if s in act:
                    x, fu, lado_g = act[s]; cara = caras[f]
                    alto = 0.32 if lado_g == "M" else 0.20
                    carga = hom - fw * (0.08 + 0.04 * fu) + up * alto + rt * lado * (0.02 if lado_g == "M" else 0.07)
                    destino = cara + up * 0.04 + rt * lado * (0.05 if lado_g == "M" else 0.0)
                    T = T.lerp(carga, min(1.0, -x / 0.55)) if x < 0 else carga.lerp(destino, x)
                elif contra[s] > 0:
                    T = T.lerp(hom - fw * 0.08 + up * 0.12 + rt * lado * 0.06, 0.6 * min(1.0, contra[s]))
                apuntar(ag, b, lambda b=b: WG() @ PG[b].tail, T)
            for s, lado in (("right", 1), ("left", -1)):
                b = "%s_leg_guard_ribbit_1" % s; hip = WG() @ PG[b].head
                if sentado:                                                     # a horcajadas: patas abiertas a los lados del pecho (aprietan al pegar)
                    ab = 65 - 8 * min(1.0, abs(inclina) / 20.0)
                    pie = (-up * math.cos(D(ab)) + rt * lado * math.sin(D(ab)))
                elif F0 <= f < F_IMP - 3:                                       # agachado: patas dobladas para saltar
                    pie = (-up * 0.7 + fw * 0.45 + rt * lado * 0.25)
                elif F_IMP - 3 <= f <= F_ATERRIZA:                              # en el aire: recogidas
                    pie = (-up * 0.8 - fw * 0.5 + rt * lado * 0.3)
                else:
                    pie = (-up + rt * lado * 0.15)
                apuntar(ag, b, lambda b=b: WG() @ PG[b].tail, hip - pie.normalized() * 0.14)
            if not sentado and not (F_IMP - 3 <= f <= F_ATERRIZA + 1) and not (F_SALTA < f <= F_PECHO):   # pisa el pasto
                dg = bpy.context.evaluated_depsgraph_get(); z = 1e9
                for x in rg.children_recursive:
                    if x.type == 'MESH':
                        e = x.evaluated_get(dg); Mx = x.matrix_world; z = min(z, min((Mx @ v.co).z for v in e.data.vertices))
                rg.location.z += 9.0 - z; vl.update()
            if sentado: rg.location.z += dz                                    # sube al cargar, se hunde al pegar y rebota
            out_g["loc"][i] = (f, tuple(rg.location)); out_g["rot"].append((f, tuple(rg.rotation_euler)))
            for h in G_HUESOS: out_g["h"][h].append((f, tuple(PG[h].rotation_euler)))
    finally:
        ra.animation_data.action, aa.animation_data.action, rg.animation_data.action, ag.animation_data.action = acts
        for n in ocultos: bpy.data.objects[n].hide_viewport = True
    # ---------------- escribir (reemplaza el tramo)
    def poner(obj, path, datos, desde):
        a = obj.animation_data.action
        for i in range(3):
            fc = a.fcurve_ensure_for_datablock(obj, path, index=i); kp = fc.keyframe_points
            for j in range(len(kp) - 1, -1, -1):
                if kp[j].co.x >= desde: kp.remove(kp[j], fast=True)
            prev = None
            for f, v in datos:
                kp.insert(f, v[i], options={'FAST'}).interpolation = 'LINEAR'
            fc.update()
    def euler_cont(lista):
        out, prev = [], None
        from mathutils import Euler
        for f, e in lista:
            q = Euler(e).to_quaternion(); e2 = q.to_euler('XYZ', prev) if prev is not None else Euler(e); prev = e2; out.append((f, tuple(e2)))
        return out
    poner(ra, "location", out_a["loc"], F_CAE); poner(ra, "rotation_euler", out_a["rot"], F_CAE)
    for h in A_HUESOS: poner(aa, 'pose.bones["%s"].rotation_euler' % h, euler_cont(out_a["h"][h]), F_CAE)
    poner(rg, "location", out_g["loc"], F0); poner(rg, "rotation_euler", euler_cont(out_g["rot"]), F0)
    for h in G_HUESOS: poner(ag, 'pose.bones["%s"].rotation_euler' % h, euler_cont(out_g["h"][h]), F0)
    sc.frame_set(sc.frame_current)
    return {"caida_hacia": [round(v, 2) for v in caida], "cabeza_en_suelo": [round(v, 2) for v in caras[F_QUIETO]],
            "golpes": len(golpes), "contactos": [contacto(g) for g in golpes], "pecho_z": round(arriba_pecho[F_GOLPES], 3)}
