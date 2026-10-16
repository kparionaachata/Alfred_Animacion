# -*- coding: utf-8 -*-
"""PATRULLA (base_ranas_2): 5 guardianes ribbit (guard_ribbit_16..20) patrullan la zona entre el ring y Jerry.
Ruta: rectangulo cerrado con esquinas redondeadas (norte y=-15.5, este x=-12.5, sur y=-24.5, oeste x=-25.5), trazado sobre el
mapa de alturas del terreno para que entre celdas vecinas nunca haya mas de 1 bloque de diferencia (sin arboles ni muros).
Caminan en sentido horario, separados por igual; paso de marcha (patas alternas segun la distancia), vaiven del cuerpo,
la lanza firme y el escudo balanceandose, saltito al subir/bajar un bloque, y a ratos miran a los lados.
Repetible: reanexa solo lo que falta y rehace las acciones <nombre>_patrulla."""
import bpy, math, random
from mathutils import Vector
import numpy as np

E = "C:/Users/user/Desktop/Alfred_Animacion/estructura_lista/guard_ribbit"
GUARDIAS = ["guard_ribbit_16", "guard_ribbit_17", "guard_ribbit_18", "guard_ribbit_19", "guard_ribbit_20"]
ESQUINAS = [(-25.5, -15.5), (-12.5, -15.5), (-12.5, -24.5), (-25.5, -24.5)]   # sentido horario visto desde arriba
RADIO_ESQ = 1.2; VEL = 0.85; ZANCADA = 0.32; FIN = 745
UP = Vector((0, 0, 1))
sc = bpy.context.scene; vl = bpy.context.view_layer

G = {"__name__": "ring_mod"}
exec(open("C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/espectadores_ring.py", encoding="utf-8").read(), G)
apuntar, rotar_mundo = G["apuntar"], G["rotar_mundo"]


def ss(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)


# ------------------------------------------------------------------ terreno
def mapa_alturas(x0=-28, x1=-9, y0=-29, y1=-12):
    cache = bpy.app.driver_namespace.get("alturas_patrulla")
    if cache and cache[1] == x0 and cache[2] == y0:                              # ya calculado en esta sesion
        alt = np.array(cache[0])
        def suelo(x, y):
            i, j = int(math.floor(x)) - x0, int(math.floor(y)) - y0
            return alt[i, j] if 0 <= i < alt.shape[0] and 0 <= j < alt.shape[1] else 9.0
        return suelo
    alt = np.full((x1 - x0, y1 - y0), -99.0)
    for o in bpy.data.objects:
        if o.type != 'MESH' or o.name.startswith(tuple(GUARDIAS)): continue
        me = o.data; n = len(me.vertices)
        if n < 8: continue
        co = np.empty(n * 3, dtype=np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        M = np.array(o.matrix_world); w = co @ M[:3, :3].T + M[:3, 3]
        sel = (w[:, 0] > x0 - .01) & (w[:, 0] < x1 + .01) & (w[:, 1] > y0 - .01) & (w[:, 1] < y1 + .01) & (w[:, 2] > 5) & (w[:, 2] < 20)
        if not sel.any(): continue
        ws = w[sel]
        if np.mean(np.abs(ws - np.round(ws)) < 0.02) < 0.95: continue          # plantas y props
        for x in range(x0, x1):
            m1 = (ws[:, 0] >= x - .01) & (ws[:, 0] <= x + 1.01)
            if not m1.any(): continue
            wx = ws[m1]
            for y in range(y0, y1):
                c = (wx[:, 1] >= y - .01) & (wx[:, 1] <= y + 1.01)
                if c.any(): alt[x - x0, y - y0] = max(alt[x - x0, y - y0], float(wx[c][:, 2].max()))
    bpy.app.driver_namespace["alturas_patrulla"] = (alt.tolist(), x0, y0)
    def suelo(x, y):
        i, j = int(math.floor(x)) - x0, int(math.floor(y)) - y0
        return alt[i, j] if 0 <= i < alt.shape[0] and 0 <= j < alt.shape[1] else 9.0
    return suelo


# ------------------------------------------------------------------ ruta (rectangulo con esquinas redondeadas)
def ruta_puntos(paso=0.05):
    pts = []; n = len(ESQUINAS)
    for k in range(n):
        a = Vector(ESQUINAS[k - 1] + (0,)); b = Vector(ESQUINAS[k] + (0,)); c = Vector(ESQUINAS[(k + 1) % n] + (0,))
        d1 = (b - a).normalized(); d2 = (c - b).normalized()
        p_in = b - d1 * RADIO_ESQ; p_out = b + d2 * RADIO_ESQ
        # recta desde la salida de la esquina anterior hasta la entrada de esta
        ini = a + d1 * RADIO_ESQ; L = (p_in - ini).length; m = max(1, int(L / paso))
        pts += [ini.lerp(p_in, t / m) for t in range(m)]
        m = 12                                                                    # curva (bezier cuadratica)
        pts += [(p_in * (1 - t / m) ** 2 + b * 2 * (1 - t / m) * (t / m) + p_out * (t / m) ** 2) for t in range(m)]
    acum = [0.0]
    for p, q in zip(pts, pts[1:] + pts[:1]): acum.append(acum[-1] + (q - p).length)
    return pts, acum


def en_ruta(pts, acum, s):
    L = acum[-1]; s %= L
    i = max(0, min(len(pts) - 1, int(np.searchsorted(acum, s, side="right")) - 1))
    p, q = pts[i], pts[(i + 1) % len(pts)]; seg = acum[i + 1] - acum[i]
    t = (s - acum[i]) / seg if seg > 1e-9 else 0.0
    return p.lerp(q, t), (q - p).normalized()


# ------------------------------------------------------------------ anexar
def anexar(nombre):
    r = bpy.data.objects.get(nombre)
    if r: return r
    col = bpy.data.collections.get("patrulla_guardianes") or bpy.data.collections.new("patrulla_guardianes")
    if col.name not in sc.collection.children: sc.collection.children.link(col)
    with bpy.data.libraries.load(E + "/" + nombre + ".blend", link=False) as (src, dst): dst.objects = list(src.objects)
    for o in dst.objects:
        if o is not None: col.objects.link(o)
    return bpy.data.objects[nombre]


def claves(obj, nombre, canales):
    obj.animation_data_create()
    viejo = bpy.data.actions.get(nombre)
    if viejo: bpy.data.actions.remove(viejo)
    act = bpy.data.actions.new(nombre); obj.animation_data.action = act
    for path, cl in canales.items():
        for i in range(len(cl[0][1])):
            fc = act.fcurve_ensure_for_datablock(obj, path, index=i); fc.keyframe_points.add(len(cl))
            fc.keyframe_points.foreach_set("co", [x for f, v in cl for x in (f, v[i])]); fc.update()


# ------------------------------------------------------------------ construir
def construir():
    suelo = mapa_alturas(); pts, acum = ruta_puntos(); L = acum[-1]; out = {"largo_ruta": round(L, 1)}
    for k, nombre in enumerate(GUARDIAS):
        r = anexar(nombre)
        arm = next(c for c in r.children_recursive if c.type == 'ARMATURE' and c.name.startswith("main_"))
        P = arm.pose.bones
        for o in [r] + list(r.children_recursive):
            if o.animation_data: o.animation_data.action = None
        nb = lambda pre: next(b.name for b in P if b.name.startswith(pre))
        B = dict(body=nb("body_"), larm=nb("left_arm"), rarm=nb("right_arm"), lleg=nb("left_leg"), rleg=nb("right_leg"))
        for b in B.values(): P[b].rotation_mode = 'XYZ'; P[b].rotation_euler = (0, 0, 0)
        rng = random.Random(nombre); vel = VEL * rng.uniform(0.95, 1.05); s0 = L * k / len(GUARDIAS)
        fase_mira = rng.uniform(0, 6.28); per_mira = rng.randint(120, 200)
        canal = {"location": [], "rotation_euler": []}; cb = {b: [] for b in B.values()}; prev = {}; yaw_prev = None
        # altura: nunca dentro de un bloque (maximo del suelo en +-0.3 m), suavizada en el tiempo sin bajar de ese minimo
        ss_ = [s0 + vel * (f - 1) / 24.0 for f in range(1, FIN + 1)]
        minimo = [max(suelo(*en_ruta(pts, acum, x + dd)[0].xy) for dd in np.linspace(-0.3, 0.3, 7)) for x in ss_]
        suave = [sum(minimo[max(0, i - 4):i + 5]) / len(minimo[max(0, i - 4):i + 5]) for i in range(len(minimo))]
        ZZ = [max(a_, b_) for a_, b_ in zip(suave, minimo)]
        SALTO = [0.0] * len(ZZ)
        for i in range(1, len(ZZ)):
            if minimo[i] != minimo[i - 1]:                                     # cambio de bloque: saltito de 8 frames
                for j in range(max(0, i - 4), min(len(ZZ), i + 4)): SALTO[j] = max(SALTO[j], 0.12 * math.sin(math.pi * (j - i + 4) / 8.0))
        for f in range(1, FIN + 1):
            s = s0 + vel * (f - 1) / 24.0
            p, d = en_ruta(pts, acum, s)
            z = ZZ[f - 1]; salto = SALTO[f - 1]
            yaw = math.atan2(-d.x, d.y)
            if yaw_prev is not None:
                while yaw - yaw_prev > math.pi: yaw -= 2 * math.pi
                while yaw - yaw_prev < -math.pi: yaw += 2 * math.pi
            yaw_prev = yaw
            paso = 2 * math.pi * s / (2 * ZANCADA)                                # un ciclo cada dos pasos
            bob = 0.025 * abs(math.sin(paso))
            r.location = (p.x, p.y, z + bob + salto); r.rotation_euler = (0, 0, yaw)
            for b in B.values(): P[b].rotation_euler = (0, 0, 0)
            vl.update()
            fw = Vector((-math.sin(yaw), math.cos(yaw), 0)); rt = Vector((math.cos(yaw), math.sin(yaw), 0))
            # cuerpo: un poco hacia adelante, vaiven lateral con el paso y a ratos mira a los lados
            mira = 22.0 * max(0.0, math.sin(2 * math.pi * f / per_mira + fase_mira)) ** 3 * (1 if k % 2 else -1)
            rotar_mundo(arm, B["body"], rt, math.radians(-6))
            rotar_mundo(arm, B["body"], fw, math.radians(3 * math.sin(paso)))
            rotar_mundo(arm, B["body"], UP, math.radians(mira))
            # patas: marcha (alternas); el hueso de la pata apunta hacia arriba -> el pie va al lado contrario
            for b, lado in ((B["lleg"], -1), (B["rleg"], 1)):
                rotar_mundo(arm, b, rt, math.radians(24 * math.sin(paso + (0 if lado > 0 else math.pi))))
            # brazo del escudo se balancea, el de la lanza firme
            rotar_mundo(arm, B["larm"], rt, math.radians(-12 * math.sin(paso)))
            for b in B.values():
                e = P[b].rotation_euler.to_quaternion().to_euler('XYZ', prev[b]) if b in prev else P[b].rotation_euler.copy()
                prev[b] = e; cb[b].append((f, tuple(e)))
            canal["location"].append((f, tuple(r.location))); canal["rotation_euler"].append((f, tuple(r.rotation_euler)))
        claves(r, nombre + "_patrulla_raiz", canal)
        claves(arm, nombre + "_patrulla", {'pose.bones["%s"].rotation_euler' % b: v for b, v in cb.items()})
        out[nombre] = dict(inicio=[round(v, 2) for v in en_ruta(pts, acum, s0)[0]][:2])
    sc.frame_set(1)
    return out


# ------------------------------------------------------------------ RUTAS DEL USUARIO (guardian_1..4.json, grabadas con el Path Tunnel Mapper)
RUTAS = {"guard_ribbit_16": "C:/Users/user/Desktop/guardian_1.json", "guard_ribbit_17": "C:/Users/user/Desktop/guardian_2.json",
         "guard_ribbit_18": "C:/Users/user/Desktop/guardian_3.json", "guard_ribbit_19": "C:/Users/user/Desktop/guardian_4.json"}
SOBRA = ["guard_ribbit_20"]
PAUSA = 30                                         # frames quieto en cada extremo (mira alrededor y se da la vuelta)


def borrar(nombre):
    r = bpy.data.objects.get(nombre)
    if r is None: return False
    for o in [r] + list(r.children_recursive):
        ad = o.animation_data
        if ad and ad.action and ad.action.users <= 1: a = ad.action; ad.action = None; bpy.data.actions.remove(a)
    for o in reversed([r] + list(r.children_recursive)): bpy.data.objects.remove(o)
    return True


def ruta_usuario(fichero):
    import json
    kp = json.load(open(fichero, encoding="utf-8"))["key_points"]
    celdas = [Vector((k["coordinates"]["x"], k["coordinates"]["y"], k["coordinates"]["z"])) for k in kp]
    xy = [Vector((c.x, c.y, 0)) for c in celdas]
    for _ in range(2):                                                            # esquinas suaves (Chaikin), extremos fijos
        n = [xy[0]]
        for a, b in zip(xy, xy[1:]): n += [a.lerp(b, 0.25), a.lerp(b, 0.75)]
        n.append(xy[-1]); xy = n
    pts = []
    for a, b in zip(xy, xy[1:]):
        m = max(1, int((b - a).length / 0.05)); pts += [a.lerp(b, t / m) for t in range(m)]
    pts.append(xy[-1])
    acum = [0.0]
    for p, q in zip(pts, pts[1:]): acum.append(acum[-1] + (q - p).length)

    def suelo(x, y):                                                              # altura = la del punto de la ruta mas cercano
        c = min(celdas, key=lambda c: (c.x - x) ** 2 + (c.y - y) ** 2); return c.z
    return pts, acum, suelo


def en_abierta(pts, acum, s):
    s = max(0.0, min(acum[-1], s))
    i = max(0, min(len(pts) - 2, int(np.searchsorted(acum, s, side="right")) - 1))
    p, q = pts[i], pts[i + 1]; seg = acum[i + 1] - acum[i]
    t = (s - acum[i]) / seg if seg > 1e-9 else 0.0
    return p.lerp(q, t), (q - p).normalized() if seg > 1e-9 else Vector((0, 1, 0))


def horario(L, vel, desfase):
    """posicion sobre la ruta por frame: ida, pausa, vuelta, pausa... -> (s, sentido, u_giro)"""
    out = []; s = desfase % L; sentido = 1; pausa = 0; giro = 0.0
    for f in range(1, FIN + 1):
        if pausa > 0:
            pausa -= 1; out.append((s, sentido, 1 - pausa / PAUSA, True))
            if pausa == 0: sentido = -sentido
            continue
        s += sentido * vel / 24.0
        if s >= L or s <= 0:
            s = max(0.0, min(L, s)); pausa = PAUSA
        out.append((s, sentido, 0.0, False))
    return out


def construir_rutas():
    out = {"borrados": [n for n in SOBRA if borrar(n)]}
    for k, (nombre, fichero) in enumerate(RUTAS.items()):
        pts, acum, suelo = ruta_usuario(fichero); L = acum[-1]
        r = anexar(nombre)
        arm = next(c for c in r.children_recursive if c.type == 'ARMATURE' and c.name.startswith("main_"))
        P = arm.pose.bones
        for o in [r] + list(r.children_recursive):
            if o.animation_data: o.animation_data.action = None
        nb = lambda pre: next(b.name for b in P if b.name.startswith(pre))
        B = dict(body=nb("body_"), larm=nb("left_arm"), rarm=nb("right_arm"), lleg=nb("left_leg"), rleg=nb("right_leg"))
        for b in B.values(): P[b].rotation_mode = 'XYZ'; P[b].rotation_euler = (0, 0, 0)
        rng = random.Random(nombre); vel = VEL * rng.uniform(0.92, 1.06)
        H = horario(L, vel, L * rng.uniform(0.0, 0.6))
        minimo = [max(suelo(*en_abierta(pts, acum, s + dd)[0].xy) for dd in np.linspace(-0.3, 0.3, 7)) for s, _a, _b, _c in H]
        suave = [sum(minimo[max(0, i - 4):i + 5]) / len(minimo[max(0, i - 4):i + 5]) for i in range(len(minimo))]
        ZZ = [max(a_, b_) for a_, b_ in zip(suave, minimo)]; SALTO = [0.0] * len(ZZ)
        for i in range(1, len(ZZ)):
            if minimo[i] != minimo[i - 1]:
                for j in range(max(0, i - 4), min(len(ZZ), i + 4)): SALTO[j] = max(SALTO[j], 0.12 * math.sin(math.pi * (j - i + 4) / 8.0))
        canal = {"location": [], "rotation_euler": []}; cb = {b: [] for b in B.values()}; prev = {}; yaw_prev = None
        fase_mira = rng.uniform(0, 6.28); per_mira = rng.randint(120, 200); dist = 0.0
        for f in range(1, FIN + 1):
            s, sentido, u, quieto = H[f - 1]
            p, d = en_abierta(pts, acum, s)
            yaw = math.atan2(-d.x, d.y) + (0 if sentido > 0 else math.pi)
            if quieto: yaw += math.pi * ss(u)                                      # se da la vuelta en la pausa
            if yaw_prev is not None:
                while yaw - yaw_prev > math.pi: yaw -= 2 * math.pi
                while yaw - yaw_prev < -math.pi: yaw += 2 * math.pi
            yaw_prev = yaw
            if not quieto: dist += vel / 24.0
            paso = 2 * math.pi * dist / (2 * ZANCADA); amp = 0.0 if quieto else 1.0
            r.location = (p.x, p.y, ZZ[f - 1] + 0.025 * abs(math.sin(paso)) * amp + SALTO[f - 1]); r.rotation_euler = (0, 0, yaw)
            for b in B.values(): P[b].rotation_euler = (0, 0, 0)
            vl.update()
            fw = Vector((-math.sin(yaw), math.cos(yaw), 0)); rt = Vector((math.cos(yaw), math.sin(yaw), 0))
            mira = 22.0 * max(0.0, math.sin(2 * math.pi * f / per_mira + fase_mira)) ** 3 * (1 if k % 2 else -1)
            if quieto: mira += 30.0 * math.sin(math.pi * u * 2)                    # en la pausa mira a ambos lados
            rotar_mundo(arm, B["body"], rt, math.radians(-6))
            rotar_mundo(arm, B["body"], fw, math.radians(3 * math.sin(paso) * amp))
            rotar_mundo(arm, B["body"], UP, math.radians(mira))
            for b, lado in ((B["lleg"], -1), (B["rleg"], 1)):
                rotar_mundo(arm, b, rt, math.radians(24 * amp * math.sin(paso + (0 if lado > 0 else math.pi))))
            rotar_mundo(arm, B["larm"], rt, math.radians(-12 * amp * math.sin(paso)))
            for b in B.values():
                e = P[b].rotation_euler.to_quaternion().to_euler('XYZ', prev[b]) if b in prev else P[b].rotation_euler.copy()
                prev[b] = e; cb[b].append((f, tuple(e)))
            canal["location"].append((f, tuple(r.location))); canal["rotation_euler"].append((f, tuple(r.rotation_euler)))
        claves(r, nombre + "_patrulla_raiz", canal)
        claves(arm, nombre + "_patrulla", {'pose.bones["%s"].rotation_euler' % b: v for b, v in cb.items()})
        out[nombre] = dict(ruta=fichero.split("/")[-1], largo=round(L, 1), vueltas_de_ida=sum(1 for h in H if h[3]) // PAUSA)
    sc.frame_set(1)
    return out
