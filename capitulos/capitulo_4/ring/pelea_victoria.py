# -*- coding: utf-8 -*-
"""base_ranas_3, despues de los golpes (pelea_derribo.py): VICTORIA del guardian.
 - Alfred se queda boca arriba con los brazos estirados hacia arriba y trata de levantarse SIN EXITO: tres intentos
   (cada uno mas debil) en que sube el torso y la cabeza temblando por el esfuerzo, dobla las piernas, y vuelve a caer
   con un rebote; entre intentos queda flojo, con los brazos tanteando el aire.
 - La rana se baja de su pecho de un salto, da una vuelta al ring a saltitos alrededor de la antorcha (sin pisar a Alfred)
   levantando y agitando los brazos como celebrando, y termina junto a la cabeza de Alfred mirando al publico.
La escena se alarga hasta F_FIN. Reemplaza las claves de Alfred (huesos) y del guardian (raiz y huesos) desde F_INI.
Uso (exec en Blender): construir()   (despues de pelea_derribo.py)
"""
import bpy, math
from mathutils import Vector, Euler

DIR = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/"
bpy.app.driver_namespace["pelea_variante"] = "ranas3"
L = {"__name__": "luch"}
exec(open(DIR + "luchadores_rodean.py", encoding="utf-8").read(), L)
ik2, apuntar, rotar_mundo, ss, desenrollar = L["ik2"], L["apuntar"], L["rotar_mundo"], L["ss"], L["desenrollar"]
C, UP = L["C"], L["UP"]
DR = {"__name__": "derribo"}
exec(open(DIR + "pelea_derribo.py", encoding="utf-8").read(), DR)
A_HUESOS, G_HUESOS, leer, resp, rebote, snap = DR["A_HUESOS"], DR["G_HUESOS"], DR["leer"], DR["resp"], DR["rebote"], DR["snap"]
sc = bpy.context.scene; vl = bpy.context.view_layer
D = math.radians

F_INI, F_FIN = 455, 600
F_BAJA = (458, 470)                                   # la rana salta del pecho al suelo
F_PASEO = (474, 584)                                  # vuelta al ring
INTENTOS = [(478, 34, 1.0), (542, 28, 0.75), (576, 24, 0.5)]   # (inicio, duracion, fuerza) de cada intento de levantarse
POSE_JSON = "C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/poses/tirado en el suelo boca arriba.json"
F_POSE = (512, 518, 538, 544)                         # tras el 1er intento: entra en la pose del usuario, la mantiene 20 f, sale
SUELO = 9.0                                           # el suelo del ring
ALREDEDOR = [(-37.75, -11.25), (-38.75, -10.95), (-39.65, -11.9), (-39.25, -13.5), (-37.5, -14.0),
             (-35.75, -13.5), (-35.15, -12.25), (-34.95, -11.15)]   # vuelta a la antorcha; termina junto a la cabeza de Alfred (al este)


def ramp(f, a, b): return ss((f - a) / float(max(1e-6, b - a)))


def chaikin(pts, n=3):
    for _ in range(n):
        q = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]): q += [a.lerp(b, 0.25), a.lerp(b, 0.75)]
        q.append(pts[-1]); pts = q
    return pts


def en_linea(pts, acum, s):
    s = max(0.0, min(acum[-1], s))
    for i in range(1, len(acum)):
        if acum[i] >= s:
            t = (s - acum[i - 1]) / max(1e-9, acum[i] - acum[i - 1]); return pts[i - 1].lerp(pts[i], t)
    return pts[-1].copy()


def esfuerzo(f):
    """(cuanto se levanta 0..1, temblor) segun los intentos: sube despacio temblando y se desploma"""
    lev, tie = 0.0, 0.0
    for a, dur, fu in INTENTOS:
        t = f - a
        if 0 <= t < dur:
            sube = 0.65 * dur
            if t < sube: v = fu * ss(t / sube)
            else: v = fu * (1 - min(1.0, ((t - sube) / (dur - sube)) ** 2))       # se desploma (cae acelerando)
            lev = max(lev, v); tie = max(tie, fu * (0.4 + 0.6 * ss(t / sube)) if t < sube else 0.0)
        caida = t - dur
        if 0 <= caida < 14: lev = max(lev, -0.12 * fu * rebote(caida, 1.0, 4.0, 0.35))  # rebote al caer de espaldas
    return lev, tie


def pose_usuario():
    import json
    d = json.load(open(POSE_JSON, encoding="utf-8"))["poses"][0]["bones"]
    rot = {h: Vector(tuple(v["local_space"]["rotation_euler_rad"].values())) for h, v in d.items()}
    loc = Vector(tuple(d["Hips_alfred"]["local_space"]["location"].values()))
    return rot, loc


def peso_pose(f):
    a, b, c, d = F_POSE
    return ramp(f, a, b) * (1 - ramp(f, c, d))


def construir():
    sc.frame_end = max(sc.frame_end, F_FIN)
    ROT_U, HIPS_U = pose_usuario()
    ra, aa = bpy.data.objects["alfred"], bpy.data.objects["Armature"]
    rg, ag = bpy.data.objects["guard_ribbit_1"], bpy.data.objects["main_guard_ribbit_1"]
    PA, PG = aa.pose.bones, ag.pose.bones; WA = lambda: aa.matrix_world; WG = lambda: ag.matrix_world
    F0 = F_INI - 1
    ar = leer(ra, ("location", "rotation_euler"), F0); A_loc = Vector([ar[("location", i)] for i in range(3)]); A_rot = Euler([ar[("rotation_euler", i)] for i in range(3)])
    gr = leer(rg, ("location", "rotation_euler"), F0); G_loc = Vector([gr[("location", i)] for i in range(3)]); G_rot = Euler([gr[("rotation_euler", i)] for i in range(3)])
    rotA = {h: Vector([leer(aa, ('pose.bones["%s"].rotation_euler' % h,), F0).get(('pose.bones["%s"].rotation_euler' % h, i), 0.0) for i in range(3)]) for h in A_HUESOS}
    rotG = {h: Vector([leer(ag, ('pose.bones["%s"].rotation_euler' % h,), F0).get(('pose.bones["%s"].rotation_euler' % h, i), 0.0) for i in range(3)]) for h in G_HUESOS}
    ocultos = [o.name for r in (ra, rg) for o in [r] + list(r.children_recursive) if o.hide_viewport]
    for n in ocultos: bpy.data.objects[n].hide_viewport = False
    acts = (ra.animation_data.action, aa.animation_data.action, rg.animation_data.action, ag.animation_data.action)
    ra.animation_data.action = aa.animation_data.action = rg.animation_data.action = ag.animation_data.action = None
    out_a = {h: [] for h in A_HUESOS}; out_g = {"loc": [], "rot": [], "h": {h: [] for h in G_HUESOS}}
    try:
        # ---------------- ALFRED (la raiz queda donde cayo)
        ra.location = A_loc; ra.rotation_euler = A_rot
        neutro = {h: Vector((0, 0, 0)) for h in A_HUESOS}
        cara_f = {}; alturas = {}; hips_l = {}; z_torso = None

        def zmin(r, solo=None, sin=()):
            """z mas baja de las mallas de Alfred (sin ojos); solo / sin: limitar a / excluir mallas"""
            dg = bpy.context.evaluated_depsgraph_get(); z = 1e9
            for x in r.children:
                if x.type != 'MESH' or not x.name.startswith("Mesh_"): continue
                if (solo and x.name not in solo) or x.name in sin: continue
                e = x.evaluated_get(dg); Mx = x.matrix_world; z = min(z, min((Mx @ v.co).z for v in e.data.vertices))
            return z
        for f in range(F_INI, F_FIN + 1):
            ra.location = A_loc.copy()
            k0 = 1 - ramp(f, F_INI, F_INI + 6)                                       # sale de la pose de los golpes
            for h in A_HUESOS: PA[h].rotation_mode = 'XYZ'; PA[h].rotation_euler = rotA[h] * k0
            PA["Hips_alfred"].location = (0, 0, 0)
            vl.update()
            M = ra.matrix_world.to_3x3(); fw = (M @ Vector((0, 1, 0))).normalized(); up = (M @ Vector((0, 0, 1))).normalized(); rt = (M @ Vector((1, 0, 0))).normalized()
            lev, tie = esfuerzo(f)
            tiembla = tie * (2.5 * math.sin(f * 2.3) + 1.5 * math.sin(f * 3.7))
            # torso: sube hacia adelante (fw = hacia el cielo) repartido en la columna, la cabeza sube un poco mas
            for h, k in (("Spine_alfred", 0.35), ("Spine1_alfred", 0.35), ("Spine2_alfred", 0.30)):
                rotar_mundo(aa, h, rt, D(-(40.0 * lev + tiembla) * k))
            cansado = 8.0 * math.sin(2 * math.pi * f / 60.0) * (1 - min(1.0, abs(lev) * 2))
            rotar_mundo(aa, "Neck_alfred", rt, D(-(22.0 * lev) + 4.0))
            rotar_mundo(aa, "Neck_alfred", up, D(cansado))                            # entre intentos la cabeza cae a un lado
            vl.update()
            # brazos estirados hacia arriba: tantean el aire; en cada intento empujan adelante (hacia los pies) para impulsarse
            for s, lado, fase in (("Right", 1, 0.0), ("Left", -1, 1.9)):
                sh = WA() @ PA[s + "UpArm_alfred"].head
                tantea = Vector((0, 0, 0)) + (fw * 0.06 * math.sin(2 * math.pi * f / 37.0 + fase) + rt * lado * 0.05 * math.cos(2 * math.pi * f / 29.0 + fase))
                arriba = sh + fw * 0.62 + up * 0.18 + rt * lado * 0.14 + tantea
                empuja = sh + fw * 0.45 - up * 0.45 + rt * lado * 0.20
                T = arriba.lerp(empuja, max(0.0, lev) * 0.8) + fw * 0.02 * tie * math.sin(f * 2.9 + lado)
                ik2(aa, s + "UpArm_alfred", s + "elbow_alfred", T, -up + rt * lado * 0.4)
            # piernas: dobla las rodillas al intentar levantarse, luego quedan estiradas y flojas
            for s, lado, fase in (("Right", 1, 0.0), ("Left", -1, 1.3)):
                hip = WA() @ PA[s + "UpLeg_alfred"].head
                dobla = 0.28 * max(0.0, lev) + 0.03 * math.sin(2 * math.pi * f / 41.0 + fase)
                pie = hip - up * 0.93 + up * dobla + fw * 0.02 + rt * lado * 0.12
                ik2(aa, s + "UpLeg_alfred", s + "knee_alfred", pie, fw + up * 0.2)
            vl.update()
            # pose del usuario (tirado boca arriba) despues del primer intento
            wp = peso_pose(f)
            if wp > 0:
                for h in A_HUESOS:
                    if h in ROT_U:
                        q = PA[h].rotation_euler.to_quaternion().slerp(Euler(ROT_U[h]).to_quaternion(), wp)
                        PA[h].rotation_euler = q.to_euler('XYZ', PA[h].rotation_euler)
            PA["Hips_alfred"].location = HIPS_U * wp
            vl.update()
            # la cabeza no atraviesa el suelo: si queda mas baja que la espalda, el cuello la levanta un poco
            for _it in range(14):
                zc, zb = zmin(ra, ("Mesh_0_alfred",)), zmin(ra, ("Mesh_1_alfred",))
                if zc >= zb - 0.004: break
                rotar_mundo(aa, "Neck_alfred", rt, D(-2.5)); vl.update()
            # apoya el torso a la misma altura que dejo el derribo (valores del usuario)
            zb = zmin(ra, ("Mesh_1_alfred",))
            if z_torso is None: z_torso = zb
            ra.location.z += z_torso - zb; vl.update()
            alturas[f] = ra.location.z; hips_l[f] = tuple(PA["Hips_alfred"].location)
            cara_f[f] = WA() @ PA["face_alfred"].head
            for h in A_HUESOS: out_a[h].append((f, tuple(PA[h].rotation_euler)))
        # ---------------- GUARDIAN: baja, vuelta al ring celebrando, termina junto a la cabeza de Alfred
        pts = chaikin([Vector((x, y, 0)) for x, y in ALREDEDOR])
        acum = [0.0]
        for a_, b_ in zip(pts[:-1], pts[1:]): acum.append(acum[-1] + (b_ - a_).length)
        Lr = acum[-1]; ini_paseo = pts[0].copy()
        fin = Vector((cara_f[F_FIN].x, cara_f[F_FIN].y, 0)); fin = pts[-1].copy()
        pos, alto = {}, {}
        for f in range(F_INI, F_FIN + 1):
            if f < F_BAJA[0]: p = Vector((G_loc.x, G_loc.y, 0)); h = G_loc.z - 9.0
            elif f <= F_BAJA[1]:
                u = (f - F_BAJA[0]) / float(F_BAJA[1] - F_BAJA[0]); p = Vector((G_loc.x, G_loc.y, 0)).lerp(ini_paseo, ss(u))
                h = (G_loc.z - 9.0) * (1 - u) + 0.35 * math.sin(math.pi * u)
            elif f < F_PASEO[0]: p = ini_paseo.copy(); h = 0.0
            elif f <= F_PASEO[1]:
                u = (f - F_PASEO[0]) / float(F_PASEO[1] - F_PASEO[0]); p = en_linea(pts, acum, Lr * u)
                h = 0.07 * abs(math.sin(math.pi * (f - F_PASEO[0]) / 9.0))              # saltitos de alegria
            else: p = fin.copy(); h = 0.04 * abs(math.sin(math.pi * (f - F_PASEO[1]) / 8.0))
            pos[f] = p; alto[f] = h
        ys = []
        for f in range(F_INI, F_FIN + 1):
            if F_PASEO[0] <= f <= F_PASEO[1]:
                d = pos[min(F_FIN, f + 3)] - pos[max(F_INI, f - 3)]
            elif f > F_PASEO[1]: d = Vector((0, -1, 0))                               # mira al publico (al sur)
            else: d = ini_paseo - Vector((G_loc.x, G_loc.y, 0))
            ys.append(math.atan2(-d.x, d.y) if d.length > 1e-4 else (ys[-1] if ys else G_rot.z))
        ys = desenrollar([G_rot.z] + ys)[1:]
        hs = list(ys)
        for i in range(1, len(hs)): hs[i] = hs[i - 1] + (ys[i] - hs[i - 1]) * 0.35         # gira suave
        for i, f in enumerate(range(F_INI, F_FIN + 1)):
            yaw = hs[i] if f > F_INI + 2 else G_rot.z + (hs[i] - G_rot.z) * ss((f - F_INI) / 2.0)
            rg.location = (pos[f].x, pos[f].y, 9.0 + alto[f]); rg.rotation_euler = (0, 0, yaw)
            k0 = 1 - ramp(f, F_INI, F_INI + 4)
            for h in G_HUESOS: PG[h].rotation_mode = 'XYZ'; PG[h].rotation_euler = rotG[h] * k0
            vl.update()
            R3 = rg.matrix_world.to_3x3(); fw = (R3 @ Vector((0, 1, 0))).normalized(); rt = (R3 @ Vector((1, 0, 0))).normalized(); up = (R3 @ Vector((0, 0, 1))).normalized()
            celebra = ramp(f, F_BAJA[1] - 2, F_BAJA[1] + 6)
            aire = alto[f] > 0.015
            rotar_mundo(ag, "body_guard_ribbit_1", rt, D(-12 * (1 - celebra) + 6 * celebra + 4 * math.sin(2 * math.pi * f / 9.0) * celebra))   # orgulloso, rebota
            rotar_mundo(ag, "body_guard_ribbit_1", UP, D(10 * math.sin(2 * math.pi * f / 18.0) * celebra))
            for s, lado, fase in (("left", -1, math.pi), ("right", 1, 0.0)):
                b = "%s_arm_guard_ribbit_1" % s; hom = WG() @ PG[b].head
                guardia = hom + fw * 0.20 + up * 0.06 + rt * (-lado) * 0.04
                bomba = 0.5 + 0.5 * math.sin(2 * math.pi * f / 12.0 + fase)               # brazos en alto, bombea alternando
                arriba = hom + up * (0.26 + 0.08 * bomba) + rt * lado * (0.10 + 0.04 * bomba) + fw * 0.03
                if F_BAJA[0] <= f <= F_BAJA[1]: arriba = hom + rt * lado * 0.22 + up * 0.14       # en el salto: brazos abiertos
                apuntar(ag, b, lambda b=b: WG() @ PG[b].tail, guardia.lerp(arriba, celebra))
            for s, lado in (("right", 1), ("left", -1)):
                b = "%s_leg_guard_ribbit_1" % s; hip = WG() @ PG[b].head
                if f < F_BAJA[0]: pie = (-up * math.cos(D(60)) + rt * lado * math.sin(D(60)))   # todavia a horcajadas
                elif aire: pie = (-up * 0.85 - fw * 0.35 + rt * lado * 0.2)
                else: pie = (-up + rt * lado * (0.15 + 0.08 * math.sin(2 * math.pi * f / 9.0)))
                apuntar(ag, b, lambda b=b: WG() @ PG[b].tail, hip - pie.normalized() * 0.14)
            if f >= F_BAJA[1] and not aire:                                            # en el suelo pisa el pasto
                dg = bpy.context.evaluated_depsgraph_get(); z = 1e9
                for x in rg.children_recursive:
                    if x.type == 'MESH':
                        e = x.evaluated_get(dg); Mx = x.matrix_world; z = min(z, min((Mx @ v.co).z for v in e.data.vertices))
                rg.location.z += 9.0 - z; vl.update()
            elif f >= F_BAJA[1]:
                dg = bpy.context.evaluated_depsgraph_get(); z = 1e9
                for x in rg.children_recursive:
                    if x.type == 'MESH':
                        e = x.evaluated_get(dg); Mx = x.matrix_world; z = min(z, min((Mx @ v.co).z for v in e.data.vertices))
                rg.location.z += max(0.0, 9.0 + alto[f] - z) if z < 9.0 + alto[f] else 0.0; vl.update()
            out_g["loc"].append((f, tuple(rg.location))); out_g["rot"].append((f, tuple(rg.rotation_euler)))
            for h in G_HUESOS: out_g["h"][h].append((f, tuple(PG[h].rotation_euler)))
    finally:
        ra.animation_data.action, aa.animation_data.action, rg.animation_data.action, ag.animation_data.action = acts
        for n in ocultos: bpy.data.objects[n].hide_viewport = True

    def poner(obj, path, datos, desde):
        a = obj.animation_data.action
        for i in range(3):
            fc = a.fcurve_ensure_for_datablock(obj, path, index=i); kp = fc.keyframe_points
            for j in range(len(kp) - 1, -1, -1):
                if kp[j].co.x >= desde: kp.remove(kp[j], fast=True)
            for f, v in datos: kp.insert(f, v[i], options={'FAST'}).interpolation = 'LINEAR'
            fc.update()

    def euler_cont(lista):
        out, prev = [], None
        for f, e in lista:
            q = Euler(e).to_quaternion(); e2 = q.to_euler('XYZ', prev) if prev is not None else Euler(e); prev = e2; out.append((f, tuple(e2)))
        return out
    poner(ra, "location", [(f, (A_loc.x, A_loc.y, alturas[f])) for f in range(F_INI, F_FIN + 1)], F_INI)
    poner(aa, 'pose.bones["Hips_alfred"].location', [(1, (0.0, 0.0, 0.0)), (F_INI - 1, (0.0, 0.0, 0.0))] + [(f, hips_l[f]) for f in range(F_INI, F_FIN + 1)], 0)
    poner(ra, "rotation_euler", [(f, tuple(A_rot)) for f in range(F_INI, F_FIN + 1, 5)], F_INI)
    for h in A_HUESOS: poner(aa, 'pose.bones["%s"].rotation_euler' % h, euler_cont(out_a[h]), F_INI)
    poner(rg, "location", out_g["loc"], F_INI); poner(rg, "rotation_euler", euler_cont(out_g["rot"]), F_INI)
    for h in G_HUESOS: poner(ag, 'pose.bones["%s"].rotation_euler' % h, euler_cont(out_g["h"][h]), F_INI)
    sc.frame_set(sc.frame_current)
    return {"frame_end": sc.frame_end, "vuelta_m": round(Lr, 2), "intentos": [a for a, d, f in INTENTOS]}
