# -*- coding: utf-8 -*-
"""base_ranas_3: la rana victoriosa (guard_ribbit_1) sigue celebrando por el ring y se detiene a SALUDAR a espectadores.
Recorrido a saltitos con los brazos en alto (bombea alternando); en cada parada: se gira hacia el espectador, le hace
adios con la mano derecha y le choca los cinco por encima de la valla; el espectador le responde (brazo arriba, saluda
y choca la mano). Cruza el paso de los lanzamientos de Jerry antes de que empiecen y se mantiene lejos de Alfred y de
los objetos que caen. Al final se queda celebrando con saltos.
Reemplaza las claves de la rana desde F_INI y las del brazo derecho de cada espectador en su saludo
(las originales se guardan en rana_saluda_original.json: repetible).
Uso (exec en Blender): construir()   (despues de jerry_lanza_cosas.py)
"""
import bpy, math, json, os
from mathutils import Vector, Euler

DIR = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/"
bpy.app.driver_namespace["pelea_variante"] = "ranas3"
L = {"__name__": "luch"}
exec(open(DIR + "luchadores_rodean.py", encoding="utf-8").read(), L)
apuntar, rotar_mundo, ss, desenrollar = L["apuntar"], L["rotar_mundo"], L["ss"], L["desenrollar"]
UP = L["UP"]
DR = {"__name__": "derribo"}
exec(open(DIR + "pelea_derribo.py", encoding="utf-8").read(), DR)
G_HUESOS, leer = DR["G_HUESOS"], DR["leer"]
sc = bpy.context.scene; vl = bpy.context.view_layer
D = math.radians
ORIG = DIR + "rana_saluda_original.json"

F_INI = 601
# (espectador, punto donde se para la rana, llega, empieza saludo, choque de manos, termina)
SALUDOS = [("guard_ribbit_12", (-34.95, -13.30), 630, 632, 646, 656),
           ("guard_ribbit_5", (-38.65, -14.05), 700, 702, 716, 726),
           ("guard_ribbit_2", (-39.85, -14.00), 742, 744, 758, 768),
           ("guard_ribbit_3", (-38.80, -9.98), 822, 824, 838, 848)]
FINAL = (-39.2, -11.2)                       # celebra aqui hasta el final (lejos de Alfred y de los objetos)
SUELO = 9.0


def ramp(f, a, b): return ss((f - a) / float(max(1e-6, b - a)))


def ventana(f, a, b, c, d): return ramp(f, a, b) * (1 - ramp(f, c, d))


def fcs(o):
    return [fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


def pos_raiz(nombre, f):
    o = bpy.data.objects[nombre]; v = list(o.location)
    if o.animation_data and o.animation_data.action:
        for fc in fcs(o):
            if fc.data_path == "location": v[fc.array_index] = fc.evaluate(f)
    return Vector(v)


def plan_recorrido(G0):
    """lista de (frame, punto) por donde pasa: tramos caminando entre paradas"""
    pts = [(F_INI, Vector((G0.x, G0.y)))]
    for esp, p, llega, a, choque, fin in SALUDOS:
        pts.append((llega, Vector(p))); pts.append((fin, Vector(p)))
    pts.append((SALUDOS[-1][5] + 30, Vector(FINAL)))
    return pts


def en_recorrido(pts, f):
    if f <= pts[0][0]: return pts[0][1].copy(), False
    for (f0, a), (f1, b) in zip(pts[:-1], pts[1:]):
        if f0 <= f <= f1:
            if (a - b).length < 1e-4: return a.copy(), False
            # por el sur (y = -14) entre la valla este y la sur, para no pasar cerca de Alfred ni de los objetos
            u = ss((f - f0) / float(f1 - f0)); return a.lerp(b, u), True
    return pts[-1][1].copy(), False


def construir():
    FIN = sc.frame_end
    rg, ag = bpy.data.objects["guard_ribbit_1"], bpy.data.objects["main_guard_ribbit_1"]; PG = ag.pose.bones; WG = lambda: ag.matrix_world
    gr0 = leer(rg, ("location", "rotation_euler"), F_INI - 1)
    G0 = Vector([gr0[("location", i)] for i in range(3)]); yaw0 = gr0[("rotation_euler", 2)]
    rotG = {h: Vector([leer(ag, ('pose.bones["%s"].rotation_euler' % h,), F_INI - 1).get(('pose.bones["%s"].rotation_euler' % h, i), 0.0) for i in range(3)]) for h in G_HUESOS}
    esp_objs = {e: bpy.data.objects[e] for e, *_ in SALUDOS}
    esp_arm = {e: next(c for c in o.children_recursive if c.type == 'ARMATURE') for e, o in esp_objs.items()}
    todos = [rg] + list(esp_objs.values())
    ocultos = [o.name for r in todos for o in [r] + list(r.children_recursive) if o.hide_viewport]
    for n in ocultos: bpy.data.objects[n].hide_viewport = False
    # ---- originales de los brazos de los espectadores (repetible)
    if os.path.exists(ORIG): orig = json.load(open(ORIG, encoding="utf-8"))
    else:
        orig = {}
        for e, p, llega, a, ch, fin in SALUDOS:
            arm = esp_arm[e]; b = "right_arm_" + e
            for fc in fcs(arm):
                if fc.data_path == 'pose.bones["%s"].rotation_euler' % b:
                    orig["%s|%d" % (e, fc.array_index)] = [(f, fc.evaluate(f)) for f in range(a - 6, fin + 7)]
        json.dump(orig, open(ORIG, "w", encoding="utf-8"))
    for k, pts in orig.items():
        e, i = k.split("|"); arm = esp_arm[e]
        fc = next(c for c in fcs(arm) if c.data_path == 'pose.bones["right_arm_%s"].rotation_euler' % e and c.array_index == int(i))
        for f, v in pts: fc.keyframe_points.insert(f, v, options={'FAST'})
        fc.update()
    acts = {o.name: o.animation_data.action for o in [rg, ag] + list(esp_arm.values())}
    rg.animation_data.action = None; ag.animation_data.action = None
    out = {"loc": [], "rot": [], "h": {h: [] for h in G_HUESOS}}; manos_rana = {}
    try:
        pts = plan_recorrido(G0)
        ys, poss = [], {}
        for f in range(F_INI, FIN + 1):
            p, camina = en_recorrido(pts, f); poss[f] = (p, camina)
            sal = next(((e, P, ll, a, ch, fi) for e, P, ll, a, ch, fi in SALUDOS if ll - 2 <= f <= fi), None)
            if sal:
                d = pos_raiz(sal[0], f) - Vector((p.x, p.y, 0))
            elif camina:
                p2, _ = en_recorrido(pts, min(FIN, f + 3)); d = Vector((p2.x - p.x, p2.y - p.y, 0))
            else:
                d = Vector((0, -1, 0))                                               # mira al publico
            d.z = 0
            ys.append(math.atan2(-d.x, d.y) if d.length > 1e-3 else (ys[-1] if ys else yaw0))
        ys = desenrollar([yaw0] + ys)[1:]
        hs = list(ys)
        for i in range(1, len(hs)): hs[i] = hs[i - 1] + (ys[i] - hs[i - 1]) * 0.3
        for i, f in enumerate(range(F_INI, FIN + 1)):
            p, camina = poss[f]
            sal = next(((e, P, ll, a, ch, fi) for e, P, ll, a, ch, fi in SALUDOS if a <= f <= fi), None)
            salto = 0.07 * abs(math.sin(math.pi * (f - F_INI) / 9.0)) if camina else (0.10 * abs(math.sin(math.pi * f / 8.0)) if f > SALUDOS[-1][5] + 30 else 0.0)
            if sal and abs(f - sal[4]) <= 2: salto = 0.05 * (1 - abs(f - sal[4]) / 2.0)                     # brinquito al chocar
            rg.location = (p.x, p.y, SUELO + salto); rg.rotation_euler = (0, 0, hs[i])
            k0 = 1 - ramp(f, F_INI, F_INI + 4)
            for h in G_HUESOS: PG[h].rotation_mode = 'XYZ'; PG[h].rotation_euler = rotG[h] * k0
            vl.update()
            R3 = rg.matrix_world.to_3x3(); fw = (R3 @ Vector((0, 1, 0))).normalized(); rt = (R3 @ Vector((1, 0, 0))).normalized(); up = (R3 @ Vector((0, 0, 1))).normalized()
            rotar_mundo(ag, "body_guard_ribbit_1", rt, D(5 + 4 * math.sin(2 * math.pi * f / 9.0)))       # orgulloso, rebota
            rotar_mundo(ag, "body_guard_ribbit_1", UP, D(9 * math.sin(2 * math.pi * f / 18.0)))
            for s, lado, fase in (("left", -1, math.pi), ("right", 1, 0.0)):
                b = "%s_arm_guard_ribbit_1" % s; hom = WG() @ PG[b].head
                bomba = 0.5 + 0.5 * math.sin(2 * math.pi * f / 12.0 + fase)
                T = hom + up * (0.26 + 0.08 * bomba) + rt * lado * (0.10 + 0.04 * bomba) + fw * 0.03     # celebra
                if sal:
                    e, P, ll, a, ch, fi = sal
                    if s == "right":
                        adios = hom + up * 0.30 + rt * 0.08 * math.sin(2 * math.pi * (f - a) / 6.0) + fw * 0.06
                        mano_esp = pos_raiz(e, f) + Vector((0, 0, 0.95))
                        choque = hom.lerp(mano_esp, 0.62) + up * 0.05
                        w_ch = ventana(f, ch - 4, ch, ch + 2, ch + 6)
                        T = T.lerp(adios, ventana(f, a, a + 3, fi - 3, fi)).lerp(choque, w_ch)
                        manos_rana[f] = choque
                apuntar(ag, b, lambda b=b: WG() @ PG[b].tail, T)
            aire = rg.location.z - SUELO > 0.015
            for s, lado in (("right", 1), ("left", -1)):
                b = "%s_leg_guard_ribbit_1" % s; hip = WG() @ PG[b].head
                pie = (-up * 0.85 - fw * 0.30 + rt * lado * 0.2) if aire else (-up + rt * lado * (0.15 + 0.06 * math.sin(2 * math.pi * f / 9.0)))
                apuntar(ag, b, lambda b=b: WG() @ PG[b].tail, hip - pie.normalized() * 0.14)
            vl.update()
            if not aire:                                                                 # pisa el pasto
                dg = bpy.context.evaluated_depsgraph_get(); z = 1e9
                for x in rg.children_recursive:
                    if x.type == 'MESH':
                        e_ = x.evaluated_get(dg); M = x.matrix_world; z = min(z, min((M @ v.co).z for v in e_.data.vertices))
                rg.location.z += SUELO - z; vl.update()
            out["loc"].append((f, tuple(rg.location))); out["rot"].append((f, tuple(rg.rotation_euler)))
            for h in G_HUESOS: out["h"][h].append((f, tuple(PG[h].rotation_euler)))
        # ---- espectadores: responden (brazo derecho arriba, saludan y chocan la mano)
        resp_esp = {}
        for e, P, ll, a, ch, fi in SALUDOS:
            arm = esp_arm[e]; PE = arm.pose.bones; b = "right_arm_" + e; ro = bpy.data.objects[e]
            arm.animation_data.action = acts[arm.name]; resp_esp[e] = []
            for f in range(a - 6, fi + 7):
                sc.frame_set(f)
                for x in [ro] + list(ro.children_recursive): x.hide_viewport = False
                vl.update()
                w = ventana(f, a - 2, a + 4, fi - 2, fi + 6)
                base = PE[b].rotation_euler.copy()
                arm.animation_data.action = None
                hom = arm.matrix_world @ PE[b].head; R3 = ro.matrix_world.to_3x3(); up = (R3 @ Vector((0, 0, 1))).normalized(); rt = (R3 @ Vector((1, 0, 0))).normalized()
                saluda = hom + up * 0.30 + rt * 0.08 * math.sin(2 * math.pi * (f - a) / 6.0 + 1.0)
                choque = manos_rana.get(ch, hom + up * 0.3)
                T = saluda.lerp(choque, ventana(f, ch - 4, ch, ch + 2, ch + 6))
                apuntar(arm, b, lambda: arm.matrix_world @ PE[b].tail, T)
                q = base.to_quaternion().slerp(PE[b].rotation_euler.to_quaternion(), w)
                resp_esp[e].append((f, tuple(q.to_euler('XYZ', base))))
                arm.animation_data.action = acts[arm.name]
    finally:
        rg.animation_data.action = acts[rg.name]; ag.animation_data.action = acts[ag.name]
        for o in esp_arm.values(): o.animation_data.action = acts[o.name]
        for n in ocultos: bpy.data.objects[n].hide_viewport = True

    def poner(obj, path, datos, desde, hasta=None):
        a = obj.animation_data.action
        for i in range(3):
            fc = a.fcurve_ensure_for_datablock(obj, path, index=i); kp = fc.keyframe_points
            for j in range(len(kp) - 1, -1, -1):
                if kp[j].co.x >= desde and (hasta is None or kp[j].co.x <= hasta): kp.remove(kp[j], fast=True)
            for f, v in datos: kp.insert(f, v[i], options={'FAST'}).interpolation = 'LINEAR'
            fc.update()

    def euler_cont(lista):
        o, prev = [], None
        for f, e in lista:
            q = Euler(e).to_quaternion(); e2 = q.to_euler('XYZ', prev) if prev is not None else Euler(e); prev = e2; o.append((f, tuple(e2)))
        return o
    poner(rg, "location", out["loc"], F_INI); poner(rg, "rotation_euler", euler_cont(out["rot"]), F_INI)
    for h in G_HUESOS: poner(ag, 'pose.bones["%s"].rotation_euler' % h, euler_cont(out["h"][h]), F_INI)
    for e, datos in resp_esp.items():
        poner(esp_arm[e], 'pose.bones["right_arm_%s"].rotation_euler' % e, euler_cont(datos), datos[0][0], datos[-1][0])
    sc.frame_set(sc.frame_current)
    return {"saludos": [(e, a, ch) for e, P, ll, a, ch, fi in SALUDOS], "final": FINAL}
