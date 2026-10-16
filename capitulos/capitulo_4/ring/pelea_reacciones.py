# -*- coding: utf-8 -*-
"""RING DE LUCHA: pelea SINCRONIZADA. Encima de alfred_pelea.py (los combos de Alfred por fases):
1) EL GUARDIAN ATACA en los huecos entre los combos de Alfred y ALFRED SE PROTEGE:
   - rafaga de punetazos saltando (220, 628)  -> Alfred bloqueo bajo (antebrazos cruzados) y retrocede un poco
   - patada voladora (384): salta echado atras con los pies por delante -> Alfred la ESQUIVA hacia un lado
   - embestida (489): cabezazo en salto bajo -> Alfred bloquea y lo arrastra hacia atras
2) EL GUARDIAN REACCIONA a cada golpe de Alfred en el frame del impacto: bloquea (se cubre), esquiva (salta
   antes de que llegue: Alfred golpea el aire), se agacha, o lo recibe (sale despedido, el cuerpo se va atras,
   agita los brazos; el uppercut lo levanta, la patada giratoria lo manda lejos).
El guardian nunca sale del ring ni pisa la antorcha. No toca la camara ni los ojos. Repetible."""
import bpy, math
from mathutils import Vector

AP = {"__name__": "pelea"}
exec(open("C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/alfred_pelea.py", encoding="utf-8").read(), AP)
L = AP["L"]; MOV = AP["MOV"]; FIN = AP["FIN"]; UP = AP["UP"]
ss, snap, ejes, punto, yaw_hacia, desenrollar = AP["ss"], AP["snap"], AP["ejes"], AP["punto"], AP["yaw_hacia"], AP["desenrollar"]
apuntar, rotar_mundo, claves, limpiar, mezclar = AP["apuntar"], AP["rotar_mundo"], AP["claves"], AP["limpiar"], AP["mezclar"]
sc = bpy.context.scene; vl = bpy.context.view_layer
C = L["C"]
VALLA = dict(x0=-40.5, x1=-34.5, y0=-14.5, y1=-9.5)

RANGO_RAFAGA = 1.12                 # (hombros adelantados 0.17)
ATAQUES_G = [(220, "rafaga", 3), (384, "patada_voladora", 0), (489, "embestida", 0), (628, "rafaga", 2)]
if AP["VARIANTE"] == "ranas3":   # fase 4: el guardian golpea de verdad (Alfred no se cubre) y esquiva los golpes de Alfred
    ATAQUES_G = ATAQUES_G[:3] + [(544, "rafaga_golpea", 4), (609, "rafaga_golpea", 3)]
# reaccion del guardian a cada golpe de Alfred (en el orden de programa())
REACCION = ["bloqueo", "bloqueo", "recibe",                              # 175 jab directo patada_baja
            "recibe_fuerte",                                             # 255 teep
            "esquiva", "esquiva", "recibe",                              # 290 jab jab directo
            "bloqueo", "bloqueo",                                        # 345 finta superman
            "agacha",                                                    # 410 patada alta
            "recibe", "bloqueo",                                         # 455 rodillazo directo
            "bloqueo", "bloqueo", "recibe", "recibe_arriba", "bloqueo", "recibe_fuerte",   # 510 rafaga
            "esquiva"]                                                   # 590 rodilla voladora
if AP["VARIANTE"] == "ranas3":
    REACCION = REACCION[:12] + ["esquiva", "esquiva", "agacha",            # 500 jab directo gancho: no le da ninguno
                                "agacha"]                                  # 580 patada alta


def horiz(v): v = v.copy(); v.z = 0; return v.normalized() if v.length > 1e-6 else Vector((1, 0, 0))


def nuevo_D():
    return {"off": Vector((0, 0, 0)), "agacha": 0.0, "glide": False, "bajo": 0.0, "esquiva": (0.0, 1), "impacto": 0.0, "flexion": 0.0}


def golpe_recibido(t, sube=2, baja=7):
    """reaccion de Alfred a un impacto t frames despues: sube en 2 frames (seco, anime) y se recupera"""
    if t < 0: return 0.0
    if t < sube: return snap(t / float(sube))                         # en el frame del contacto todavia no cede
    return max(0.0, 1 - ss((t - sube) / float(baja)))


# ------------------------------------------------------------------ 1) ataques del guardian y defensas de Alfred
def plan_ataques(gbase, galto, abase):
    g_off = {f: Vector((0, 0, 0)) for f in range(1, FIN + 1)}; g_z = {f: galto[f] for f in range(1, FIN + 1)}
    g_pitch = {f: 0.0 for f in range(1, FIN + 1)}; g_brazos = {f: {} for f in range(1, FIN + 1)}
    defensa = {f: nuevo_D() for f in range(1, FIN + 1)}; ventanas = []
    for e0, tipo, n in ATAQUES_G:
        if tipo in ("rafaga", "rafaga_golpea"):
            golpea = tipo == "rafaga_golpea"
            entra, cada, sale = 5, 5, 8; fin_a = e0 + entra + n * cada; ventanas.append((e0, fin_a + sale))
            for f in range(e0 - 3, min(FIN, fin_a + sale) + 1):
                c = snap(max(0.0, f - e0) / entra) if f <= e0 + entra else (1.0 if f <= fin_a else 1 - ss((f - fin_a) / sale))
                d = horiz(abase[f] - gbase[f]); hz = 0.0; golpes_dados = 0; estoc = 0.0
                for k in range(n):
                    p0 = e0 + entra + k * cada; t = f - p0; lado = "right" if k % 2 == 0 else "left"
                    if -2 <= t < 5:                                                # -2..0 carga, 0..5 golpe
                        g_brazos[f][lado] = ("golpe", t)
                    if 0 <= t < 5:
                        w = snap(t / 2.0) if t < 2 else (1.0 if t < 3 else 1 - ss((t - 2) / 2.0))
                        hz = max(hz, 0.13 * math.sin(math.pi * t / 5.0)); estoc = max(estoc, w)
                    if t >= 2: golpes_dados += 1
                objetivo = abase[f] - d * (RANGO_RAFAGA - 0.20 * estoc); g_off[f] = (objetivo - gbase[f]) * c      # en cada golpe se lanza adelante
                g_z[f] = galto[f] * (1 - c) + hz
                # Alfred: bloqueo bajo, se agacha y cada golpe lo empuja un poco hacia atras
                wb = ss((f - (e0 - 3)) / 3.0) if f < fin_a else 1 - ss((f - fin_a) / 6.0)
                D = defensa[f]; D["glide"] = True
                if golpea:                                                     # NO se cubre: cada golpe lo dobla y lo echa atras
                    D["impacto"] = max([D["impacto"]] + [1.5 * golpe_recibido(f - (e0 + entra + k * cada + 2), 2, 9) for k in range(n)])
                    D["flexion"] = max([D["flexion"]] + [golpe_recibido(f - (e0 + entra + k * cada + 2), 2, 10) for k in range(n) if k % 2 == 1])
                    D["agacha"] = max(D["agacha"], 0.05 * wb)
                    emp = 0.11 * golpes_dados * (1 - ss((f - fin_a) / float(sale)) if f > fin_a else 1.0)
                else:
                    D["bajo"] = max(D["bajo"], wb); D["agacha"] = max(D["agacha"], 0.12 * wb)
                    D["impacto"] = max([D["impacto"]] + [golpe_recibido(f - (e0 + entra + k * cada + 2)) for k in range(n)])
                    emp = 0.05 * golpes_dados * (1 - ss((f - fin_a) / float(sale)) if f > fin_a else 1.0)
                D["off"] = D["off"] + d * emp                                   # d va del guardian a Alfred
        else:
            prep, vuelo, sale = 4, (10 if tipo == "patada_voladora" else 7), (12 if tipo == "patada_voladora" else 10)
            e1 = e0 + prep; fi = e1 + vuelo; ventanas.append((e0, fi + sale))
            d1 = horiz(abase[e1] - gbase[e1])
            destino = abase[e1] - d1 * (0.30 if tipo == "patada_voladora" else 0.72)
            # hacia donde esquiva Alfred: el lado que lo aleja de la antorcha
            lat = d1.cross(UP); lat = lat if (abase[e1] + lat * 0.6 - C).length > (abase[e1] - lat * 0.6 - C).length else -lat
            for f in range(e0, min(FIN, fi + sale) + 1):
                if f <= e1: c = 0.25 * ss((f - e0) / prep); z = 0.0; pit = 0.0
                elif f <= fi:
                    u = (f - e1) / float(vuelo); c = 0.25 + 0.75 * ss(u)
                    z = (0.45 if tipo == "patada_voladora" else 0.15) * math.sin(math.pi * u)
                    pit = (math.radians(75) if tipo == "patada_voladora" else -math.radians(35)) * math.sin(math.pi * u)
                else: c = 1 - ss((f - fi) / float(sale)); z = 0.05 * math.sin(math.pi * min(1.0, (f - fi) / 6.0)); pit = 0.0
                obj = destino if f <= fi else destino
                g_off[f] = (obj - gbase[f]) * c; g_z[f] = galto[f] * (1 - min(1.0, c * 2)) + z; g_pitch[f] = pit
                if tipo == "embestida" and e1 <= f <= fi + 2:
                    for lado in ("right", "left"): g_brazos[f][lado] = ("atras", 1.0)
                D = defensa[f]; D["glide"] = True
                if tipo == "patada_voladora":
                    we = snap((f - (e1 - 1)) / 4.0) if f < fi else 1 - ss((f - fi) / 10.0)
                    rtG = d1.cross(UP); lado_e = 1 if lat.dot(rtG) > 0 else -1
                    D["esquiva"] = (we, lado_e); D["off"] = D["off"] + lat * 0.6 * we
                else:
                    wb = ss((f - e0) / 3.0) if f < fi + 4 else 1 - ss((f - fi - 4) / 6.0)
                    D["bajo"] = max(D["bajo"], wb); D["agacha"] = max(D["agacha"], 0.12 * wb)
                    D["flexion"] = max(D["flexion"], golpe_recibido(f - fi, 2, 12))
                    D["impacto"] = max(D["impacto"], 0.6 * golpe_recibido(f - fi, 2, 8))
                    emp = 0.35 * snap((f - fi + 2) / 4.0) if f >= fi - 2 else 0.0
                    if f > fi + 8: emp *= 1 - ss((f - fi - 8) / 14.0)
                    D["off"] = D["off"] + d1 * emp
    gpre = {f: gbase[f] + g_off[f] for f in range(1, FIN + 1)}
    return gpre, g_z, g_pitch, g_brazos, defensa, ventanas


# ------------------------------------------------------------------ 2) reacciones del guardian a los golpes de Alfred
def reacciones(gpre, apos):
    golpes, _r = AP["programa"]()
    assert len(golpes) == len(REACCION), (len(golpes), len(REACCION))
    off = {f: Vector((0, 0, 0)) for f in range(1, FIN + 1)}; z = {f: 0.0 for f in range(1, FIN + 1)}
    atras = {f: 0.0 for f in range(1, FIN + 1)}; agacha = {f: 0.0 for f in range(1, FIN + 1)}; brazos = {f: {} for f in range(1, FIN + 1)}
    for (st, n), rea in zip(golpes, REACCION):
        A, S, H, R = MOV[n]["t"]; fi = st + A + S
        d = horiz(gpre[min(FIN, fi)] - apos[min(FIN, fi)]); lat = d.cross(UP)
        lat = lat if (gpre[min(FIN, fi)] + lat * 0.3 - C).length > (gpre[min(FIN, fi)] - lat * 0.3 - C).length else -lat

        def perfil(f, ent, sost, sal, a=fi):
            if f < a: return 0.0
            if f < a + ent: return snap((f - a) / float(ent))
            if f < a + ent + sost: return 1.0
            return max(0.0, 1 - ss((f - a - ent - sost) / float(sal)))
        for f in range(max(1, st - 2), min(FIN, fi + 45) + 1):
            if rea == "bloqueo":
                w = ss((f - (fi - 3)) / 3.0) if f < fi + H + 2 else 1 - ss((f - fi - H - 2) / 5.0)
                if w > 0: brazos[f]["cubre"] = max(brazos[f].get("cubre", 0.0), w)
                off[f] += d * 0.08 * perfil(f, 3, H + 2, 14)
            elif rea in ("recibe", "recibe_fuerte", "recibe_arriba"):
                k, ang = {"recibe": (0.25, 25), "recibe_fuerte": (0.5, 40), "recibe_arriba": (0.2, 35)}[rea]
                p = perfil(f, 4, H + 2, 18); off[f] += d * k * p
                pa = perfil(f, 3, 3, 10); atras[f] += ang * pa
                if pa > 0: brazos[f]["agita"] = max(brazos[f].get("agita", 0.0), pa)
                alto = {"recibe": 0.0, "recibe_fuerte": 0.12, "recibe_arriba": 0.25}[rea]
                if fi <= f < fi + 10: z[f] += alto * math.sin(math.pi * (f - fi) / 10.0)
            elif rea == "esquiva":
                dur = max(2, fi - st)
                if f <= fi: p = ss((f - st) / float(dur))
                elif f <= fi + H + 2: p = 1.0
                else: p = max(0.0, 1 - ss((f - fi - H - 2) / 14.0))
                off[f] += (d * 0.25 + lat * 0.30) * p
                if st <= f <= fi + 2: z[f] += 0.10 * math.sin(math.pi * (f - st) / float(dur + 2))
            elif rea == "agacha":
                p = ss((f - st) / float(max(2, fi - st))) if f <= fi else (1.0 if f <= fi + H + 2 else max(0.0, 1 - ss((f - fi - H - 2) / 8.0)))
                agacha[f] = max(agacha[f], 40 * p); off[f] += d * 0.12 * p
    return off, z, atras, agacha, brazos


def dentro(p, apos_f):
    """el guardian no sale del ring, no pisa la antorcha ni se mete en Alfred"""
    m = 0.45; p = p.copy()
    p.x = min(VALLA["x1"] - m, max(VALLA["x0"] + m, p.x)); p.y = min(VALLA["y1"] - m, max(VALLA["y0"] + m, p.y))
    for centro, rmin in ((C, 0.5), (apos_f, 0.6)):
        v = p - centro; v.z = 0
        if v.length < rmin: p = Vector((centro.x, centro.y, 0)) + (v.normalized() if v.length > 1e-6 else Vector((1, 0, 0))) * rmin
    p.z = 0; return p


# ------------------------------------------------------------------ 3) pose del guardian
# hombros adelantados (como los puso el usuario en el brazo derecho): asi los brazos se ven delante del cuerpo
HOMBRO_ADELANTE = Vector((0.098, 0.168, 0.036))           # en el espacio de la armadura: +x afuera (lado derecho), +y adelante, +z arriba


def hombros(arm):
    """location de pose de cada brazo para desplazar su hombro HOMBRO_ADELANTE (el izquierdo en espejo)"""
    out = {}
    for b, sx in (("right_arm_guard_ribbit_1", 1), ("left_arm_guard_ribbit_1", -1)):
        v = HOMBRO_ADELANTE.copy(); v.x *= sx
        out[b] = arm.data.bones[b].matrix_local.to_3x3().inverted() @ v
    return out


def ext_golpe(t):
    """perfil del punetazo por frame t: <0 carga (se echa atras, negativo), 0-2 sale explosivo, 2-3 impacto, 3-5 vuelve"""
    if t < 0: return -0.45 * ss((t + 2) / 2.0)
    if t < 2: return -0.45 + 1.45 * snap(t / 2.0)
    if t < 3: return 1.0
    return 1.0 - ss((t - 3) / 2.0)


def pose_guardian(gfin, gz, gpitch, gaire, apos, br_at, br_re, atras, agacha):
    """brazos y patas VIVOS: carga - golpe con giro del puno - vuelta, el cuerpo gira con cada golpe, las patas empujan al
    despegar, se recogen en el aire y se estiran para aterrizar, cargan el peso al golpear y se abren al bloquear;
    los pies siempre en el pasto cuando no salta"""
    r = bpy.data.objects["guard_ribbit_1"]; arm = bpy.data.objects["main_guard_ribbit_1"]; P = arm.pose.bones; W = lambda: arm.matrix_world
    limpiar(r); limpiar(arm)
    huesos = ["body_guard_ribbit_1", "left_arm_guard_ribbit_1", "right_arm_guard_ribbit_1", "right_leg_guard_ribbit_1", "left_leg_guard_ribbit_1"]
    for h in huesos: P[h].rotation_mode = 'XYZ'; P[h].rotation_euler = (0, 0, 0)
    am = L["amagos"](11, 90); jab = L["jab"]; HOM = hombros(arm)
    for b, v in HOM.items(): P[b].location = v
    mallas = [c for c in r.children_recursive if c.type == 'MESH']
    ys = desenrollar([yaw_hacia(gfin[f], apos[f]) for f in range(1, FIN + 1)])
    idx = lambda f: min(FIN, max(1, f))
    canal = {"location": [], "rotation_euler": []}; cb = {h: [] for h in huesos}; prev = {}

    def suelo_min():
        dg = bpy.context.evaluated_depsgraph_get(); z = 1e9
        for x in mallas:
            e = x.evaluated_get(dg); M = x.matrix_world; z = min(z, min((M @ v.co).z for v in e.data.vertices))
        return z

    for f in range(1, FIN + 1):
        yaw = ys[f - 1]; dA = horiz(apos[f] - gfin[f])
        vel = gfin[idx(f + 1)] - gfin[idx(f - 1)]; vel.z = 0; vz = gz[idx(f + 1)] - gz[idx(f - 1)]
        r.location = (gfin[f].x, gfin[f].y, 9.0 + gz[f]); r.rotation_euler = (gpitch[f], 0, yaw)
        for h in huesos: P[h].rotation_euler = (0, 0, 0)
        vl.update()
        R3 = r.matrix_world.to_3x3(); fw = (R3 @ Vector((0, 1, 0))).normalized(); rt = (R3 @ Vector((1, 0, 0))).normalized(); up = (R3 @ Vector((0, 0, 1))).normalized()
        golpes = {s: ext_golpe(v[1]) for s, v in br_at[f].items() if v[0] == "golpe"}
        wc = br_re[f].get("cubre", 0.0); wa = br_re[f].get("agita", 0.0)
        wd = min(1.0, max(0.0, gpitch[f]) / 0.6)                              # patada voladora (echado atras)
        we = 1.0 if any(v[0] == "atras" for v in br_at[f].values()) else 0.0  # embestida (brazos atras)
        # ---- cuerpo: inclinado, gira hacia el brazo que golpea (y al reves en la carga), se encoge al cubrirse
        giro = 25.0 * golpes.get("right", 0.0) - 25.0 * golpes.get("left", 0.0)
        idle = 1.0 - min(1.0, len(golpes) + wc + wa + wd + we)
        giro += 6.0 * math.sin(2 * math.pi * f / 28.0) * idle                    # balanceo de guardia
        rotar_mundo(arm, "body_guard_ribbit_1", rt, math.radians(-12 + atras[f] - agacha[f] - 10 * wc + 8 * wa * math.sin(f * 1.1)))
        rotar_mundo(arm, "body_guard_ribbit_1", UP, math.radians(giro))
        # ---- brazos
        for s, brazo, lado in (("left", 0, -1), ("right", 1, 1)):
            b = "%s_arm_guard_ribbit_1" % s; hom = W() @ P[b].head; ph = 2 * math.pi * f / 14.0 + brazo * math.pi
            j = jab(f, am, brazo) * idle
            T = hom + fw * (0.20 + 0.04 * math.sin(ph) + 0.12 * j) + up * (0.04 + 0.03 * math.sin(ph + 1.0) + 0.03 * j) \
                + rt * (-lado) * 0.04 + rt * lado * 0.02 * math.cos(ph)              # guardia: los punos dibujan circulos chicos
            giro_puno = 70.0 * j
            if s in golpes:
                x = golpes[s]; manos = Vector((apos[f].x, apos[f].y, 9.0)) + UP * 0.62 - dA * 0.55
                carga = hom - fw * 0.10 + up * 0.07 + rt * lado * 0.08
                T = T.lerp(carga, min(1.0, -x / 0.45)) if x < 0 else carga.lerp(manos, x)
                giro_puno = 90.0 * max(0.0, x)                                   # el puno gira (sacacorchos) al llegar
            if we: T = T.lerp(hom - fw * 0.25 - up * 0.04 + rt * lado * 0.06, we); giro_puno = -30.0
            if wd: T = T.lerp(hom - fw * 0.12 + rt * lado * 0.20 + up * 0.14, wd)   # brazos abiertos para equilibrar
            if wc: T = T.lerp(hom + fw * 0.10 + up * 0.25 + rt * (-lado) * 0.09, wc); giro_puno += -lado * 40.0 * wc
            if wa:
                agit = hom + rt * lado * 0.24 + up * (0.12 + 0.09 * math.sin(1.3 * f + brazo)) - fw * (0.08 - 0.07 * math.cos(1.7 * f + brazo))
                T = T.lerp(agit, wa); giro_puno += 50.0 * wa * math.sin(1.9 * f + brazo)
            apuntar(arm, b, lambda b=b: W() @ P[b].tail, T)
            if abs(giro_puno) > 0.5: rotar_mundo(arm, b, (T - hom).normalized(), math.radians(lado * giro_puno))
        # ---- patas (el hueso apunta hacia arriba: el pie va al lado contrario de la punta)
        m = horiz(vel) if vel.length > 0.01 else horiz(fw)
        aire = gz[f] > 0.015
        for s, lado in (("right", 1), ("left", -1)):
            b = "%s_leg_guard_ribbit_1" % s
            adel = 0.0; afuera = 6.0 + 4.0 * math.sin(2 * math.pi * f / 14.0 + (0 if lado > 0 else math.pi)) * idle   # pasa el peso de pata a pata
            if aire: adel_m = max(-35.0, min(35.0, -vz * 900.0)); afuera += 10.0          # sube: empuja atras / baja: se estira para aterrizar
            else: adel_m = 0.0
            if golpes:                                                         # golpe con un brazo: la pata contraria empuja atras
                xr, xl = golpes.get("right", 0.0), golpes.get("left", 0.0)
                adel += (10.0 * xr - 18.0 * xl) if lado > 0 else (10.0 * xl - 18.0 * xr)
            afuera += 12.0 * wc + 18.0 * agacha[f] / 40.0
            if wa: adel += 28.0 * wa * (1 + 0.3 * math.sin(1.5 * f + lado))            # el golpe recibido le saca los pies adelante
            if wd: adel += 25.0 * wd                                              # patada voladora: pies hacia Alfred
            if we: adel -= 20.0                                                  # embestida: patas atras
            pie = (-up * math.cos(math.radians(adel)) + fw * math.sin(math.radians(adel)) + m * math.sin(math.radians(adel_m))) \
                * math.cos(math.radians(afuera)) + rt * lado * math.sin(math.radians(afuera))
            hip = W() @ P[b].head
            apuntar(arm, b, lambda b=b: W() @ P[b].tail, hip - pie.normalized() * 0.14)
        vl.update()
        # ---- en el suelo los pies pisan el pasto (al doblar las patas el cuerpo baja)
        zs = suelo_min()
        if (not aire and abs(gpitch[f]) < 0.02) or zs < 9.0:                  # en el aire tampoco atraviesa el pasto
            r.location.z += 9.0 - zs; vl.update()
        canal["location"].append((f, tuple(r.location))); canal["rotation_euler"].append((f, tuple(r.rotation_euler)))
        for h in huesos:
            e = P[h].rotation_euler.to_quaternion().to_euler('XYZ', prev[h]) if h in prev else P[h].rotation_euler.copy()
            prev[h] = e; cb[h].append((f, tuple(e)))
    canales = {'pose.bones["%s"].rotation_euler' % h: v for h, v in cb.items()}
    for b, v in HOM.items(): canales['pose.bones["%s"].location' % b] = [(1, tuple(v)), (FIN, tuple(v))]
    claves(r, "guard_ribbit_1_rodea_ring", canal)
    claves(arm, "guard_ribbit_1_guardia_ring", canales)


def construir():
    th = L["angulos"](); gbase, galto, gaire = AP["saltos_guardian"](th)
    abase = {f: punto(th[f], f) for f in range(1, FIN + 1)}
    gpre, gz, gpitch, br_at, defensa, ventanas = plan_ataques(gbase, galto, abase)
    out, apos = AP["alfred_pelea"](th, gpre, gz, defensa)
    roff, rz, atras, agacha, br_re = reacciones(gpre, apos)
    gfin = {f: dentro(gpre[f] + roff[f], apos[f]) for f in range(1, FIN + 1)}
    gz2 = {f: gz[f] + rz[f] for f in range(1, FIN + 1)}
    pose_guardian(gfin, gz2, gpitch, gaire, apos, br_at, br_re, atras, agacha)
    AP["marcadores"](); sc.frame_set(1)
    out["ataques_guardian"] = [(e0, t) for e0, t, n in ATAQUES_G]
    out["dist_min_luchadores"] = round(min((gfin[f] - Vector((apos[f].x, apos[f].y, 0))).length for f in range(1, FIN + 1)), 3)
    return out
