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
from mathutils import Vector, Matrix

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


def golpe(t):
    """perfil de un punetazo hacia abajo, t frames desde que empieza: carga 0-3, sale 3-5, impacto 5-6, vuelve 6-9"""
    if t < 0 or t >= CADA: return 0.0, False
    if t < 3: return -0.4 * ss(t / 3.0), False
    if t < 5: return -0.4 + 1.4 * snap((t - 3) / 2.0), False
    if t < 6: return 1.0, True
    return 1.0 - ss((t - 6) / 3.0), False


def construir():
    ra, aa = bpy.data.objects["alfred"], bpy.data.objects["Armature"]
    rg, ag = bpy.data.objects["guard_ribbit_1"], bpy.data.objects["main_guard_ribbit_1"]
    PA, PG = aa.pose.bones, ag.pose.bones; WA = lambda: aa.matrix_world; WG = lambda: ag.matrix_world
    FIN = sc.frame_end
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
        yaw_caida = math.atan2(caida.x, -caida.y)                               # su frente mira al lado contrario de la caida
        while yaw_caida - yawA0 > math.pi: yaw_caida -= 2 * math.pi
        while yaw_caida - yawA0 < -math.pi: yaw_caida += 2 * math.pi
        fw_c, rt_c = ejes(yaw_caida)
        # ---------------- ALFRED
        out_a = {"loc": [], "rot": [], "h": {h: [] for h in A_HUESOS}}; caras = {}; pechos = {}; arriba_pecho = {}
        golpes = [F_GOLPES + k * CADA for k in range(int((FIN - F_GOLPES) / CADA) + 1)]
        for f in range(F_CAE, FIN + 1):
            u = (f - F_CAE) / float(F_SUELO - F_CAE)
            ang = 90.0 * ease_in(u) if f <= F_SUELO else 90.0 - 7.0 * math.sin(math.pi * min(1.0, (f - F_SUELO) / float(F_QUIETO - F_SUELO)))
            yaw = yawA0 + (yaw_caida - yawA0) * snap((f - F_CAE) / 6.0)
            pos = A0 - caida * 0.25 * snap((f - F_CAE) / 8.0); pos.z = A0.z
            ra.location = pos; ra.rotation_euler = (D(ang), 0, yaw)
            k_base = 1 - ramp(f, F_CAE, F_CAE + 4)
            for h in A_HUESOS: PA[h].rotation_mode = 'XYZ'; PA[h].rotation_euler = rotA[h] * k_base
            vl.update()
            M = ra.matrix_world.to_3x3(); fw = (M @ Vector((0, 1, 0))).normalized(); up = (M @ Vector((0, 0, 1))).normalized(); rt = (M @ Vector((1, 0, 0))).normalized()
            # cabeza: se va atras al caer; con cada golpe se va al lado contrario del puno
            lat = 0.0
            for k, g0 in enumerate(golpes):
                t = f - (g0 + 5)
                if 0 <= t < 14: lat += (1 if k % 2 == 0 else -1) * (snap(t / 2.0) if t < 2 else 1 - ss((t - 2) / 12.0))
            atras = 25 * math.sin(math.pi * min(1.0, u)) if f <= F_SUELO + 4 else 0.0
            rotar_mundo(aa, "Neck_alfred", rt, D(atras * 0.6))
            rotar_mundo(aa, "Neck_alfred", up, D(30 * lat)); rotar_mundo(aa, "face_alfred", up, D(18 * lat))
            vl.update()
            cara = WA() @ PA["face_alfred"].head + (WA() @ PA["face_alfred"].tail - WA() @ PA["face_alfred"].head) * 0.35
            pecho = WA() @ PA["Spine2_alfred"].head
            # brazos
            for s, lado in (("Right", 1), ("Left", -1)):
                sh = WA() @ PA[s + "UpArm_alfred"].head
                if f <= F_QUIETO + 4:                                             # al caer los brazos se van arriba y afuera
                    T = sh + up * 0.55 + rt * lado * 0.55 + fw * 0.25 * (1 - ramp(f, F_SUELO, F_QUIETO + 4))
                elif f < F_CUBRE:                                                 # manotea / empuja al guardian
                    ph = 2 * math.pi * f / 11.0 + (0 if lado > 0 else 2.0)
                    T = sh + fw * (0.45 + 0.15 * math.sin(ph)) + up * (0.25 + 0.12 * math.cos(ph)) + rt * lado * (0.25 + 0.08 * math.sin(ph * 0.7))
                else:                                                             # se cubre la cara (cada vez mas debil)
                    deb = ramp(f, F_CUBRE + 40, FIN)
                    cubre = cara + fw * 0.18 + rt * lado * 0.10 + up * 0.05
                    caido = sh + rt * lado * 0.45 + up * 0.15 - fw * 0.10
                    T = cubre.lerp(caido, 0.6 * deb) + fw * 0.03 * math.sin(f * 0.9 + lado)
                if F_QUIETO < f < F_CUBRE + 6: T = (sh + up * 0.55 + rt * lado * 0.55).lerp(T, ramp(f, F_QUIETO, F_QUIETO + 8))
                ik2(aa, s + "UpArm_alfred", s + "elbow_alfred", T, -fw + rt * lado * 0.5)
            # piernas: rectas al caer; despues patalea (rodillas arriba y abajo)
            for s, lado, fase in (("Right", 1, 0.0), ("Left", -1, 2.4)):
                hip = WA() @ PA[s + "UpLeg_alfred"].head
                pata = 0.0 if f < F_QUIETO else max(0.0, 0.05 + 0.09 * math.sin(2 * math.pi * f / 13.0 + fase)) * (1 - 0.6 * ramp(f, F_CUBRE + 40, FIN))
                pie = hip - up * 0.93 + up * pata + fw * 0.02 + rt * lado * 0.10
                ik2(aa, s + "UpLeg_alfred", s + "knee_alfred", pie, fw + up * 0.2)
            # en el suelo: la espalda apoya en el pasto (z minima de la malla = 9.0)
            vl.update(); z = suela(ra)
            if f >= F_SUELO - 2 or z < 9.0: ra.location.z += 9.0 - z; vl.update()
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
            if F_IMP - 3 <= f <= F_IMP + 4: pitch = D(-35) * math.sin(math.pi * (f - (F_IMP - 3)) / 7.0)   # se estira en el punetazo
            rg.location = p; rg.rotation_euler = (pitch, 0, yaw)
            k_base = 1 - ramp(f, F0, F0 + 3)
            for h in G_HUESOS: PG[h].rotation_mode = 'XYZ'; PG[h].rotation_euler = rotG[h] * k_base
            vl.update()
            R3 = rg.matrix_world.to_3x3(); fw = (R3 @ Vector((0, 1, 0))).normalized(); rt = (R3 @ Vector((1, 0, 0))).normalized(); up = (R3 @ Vector((0, 0, 1))).normalized()
            sentado = f > F_PECHO
            # cuerpo: inclinado sobre Alfred al pegar, gira con cada puno
            g_act = {}
            for k, g0 in enumerate(golpes):
                x, imp = golpe(f - g0)
                if x != 0.0: g_act["right" if k % 2 == 0 else "left"] = x
            inc = (-12 + (-28 if sentado else 0)) if f > F_IMP + 4 else -12
            rotar_mundo(ag, "body_guard_ribbit_1", rt, D(inc))
            rotar_mundo(ag, "body_guard_ribbit_1", UP, D(22 * g_act.get("right", 0.0) - 22 * g_act.get("left", 0.0)))
            for s, lado in (("left", -1), ("right", 1)):
                b = "%s_arm_guard_ribbit_1" % s; hom = WG() @ PG[b].head
                T = hom + fw * 0.20 + up * 0.06 + rt * (-lado) * 0.04 + up * 0.02 * math.sin(f * 0.5 + lado)
                if f <= F_IMP + 2 and s == "right":                             # punetazo volador
                    x = ss((f - (F_IMP - 4)) / 4.0) if f <= F_IMP else 1.0
                    T = T.lerp(cara_imp, x)
                if F_IMP < f <= F_ATERRIZA:                                       # brazos abiertos para caer
                    T = T.lerp(hom + rt * lado * 0.25 + up * 0.15, ramp(f, F_IMP + 2, F_IMP + 5))
                if s in g_act:
                    x = g_act[s]; cara = caras[f]
                    carga = hom - fw * 0.05 + up * 0.20 + rt * lado * 0.06
                    T = T.lerp(carga, min(1.0, -x / 0.4)) if x < 0 else carga.lerp(cara + up * 0.05, x)
                apuntar(ag, b, lambda b=b: WG() @ PG[b].tail, T)
            for s, lado in (("right", 1), ("left", -1)):
                b = "%s_leg_guard_ribbit_1" % s; hip = WG() @ PG[b].head
                if sentado:                                                     # a horcajadas: patas abiertas a los lados del pecho
                    pie = (-up * math.cos(D(65)) + rt * lado * math.sin(D(65)))
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
            if sentado: rg.location.z += 0.03 * abs(math.sin(math.pi * f / CADA))   # rebota con cada golpe
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
            "golpes": len([g for g in golpes if g <= FIN]), "pecho_z": round(arriba_pecho[F_GOLPES], 3)}
