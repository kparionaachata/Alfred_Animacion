# -*- coding: utf-8 -*-
"""base_ranas_3: RANA DE LAS APUESTAS (ribbit nuevo, modelo ribbit_7).
Lleva un PAPEL en la mano derecha (objetos/vanilla/paper) y un LAPIZ en la izquierda (modelado aqui: cuerpo hexagonal
amarillo, punta de madera con grafito, virola metalica y goma rosa). Camina por detras del publico del lado sur anotando
apuestas (se para frente a algunos espectadores y escribe). En F_JERRY llega por detras de Jerry y le pregunta; Jerry
(jerry_ranas3.py, APUESTA) baja de la valla, se gira, le dice "todo", saca 5 PEPITAS DE HIERRO (objetos/vanilla/iron_nugget)
"del bolsillo" y se las da: quedan sobre el papel, la rana anota la apuesta y se las guarda. Despues sigue anotando.
Uso (exec en Blender): construir()   (despues de regenerar a Jerry con jerry_ranas3.py)
"""
import bpy, bmesh, math, re
from mathutils import Vector, Euler, Matrix

DIR = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/"
BASE = "C:/Users/user/Desktop/Alfred_Animacion/"
bpy.app.driver_namespace["pelea_variante"] = "ranas3"
L = {"__name__": "luch"}
exec(open(DIR + "luchadores_rodean.py", encoding="utf-8").read(), L)
apuntar, rotar_mundo, ss, desenrollar = L["apuntar"], L["rotar_mundo"], L["ss"], L["desenrollar"]
UP = L["UP"]
JN = {"__name__": "j3"}
exec(compile(open(DIR + "jerry_ranas3.py", encoding="utf8").read(), "jerry_ranas3.py", "exec"), JN)
sc = bpy.context.scene; vl = bpy.context.view_layer
D = math.radians
SUELO = 9.0
HAND = 0.17                                         # el hueso del brazo apunta hacia ARRIBA y la malla cuelga hacia abajo: la mano esta en el extremo OPUESTO a la cola (0.19 bajo el hombro)
SUF = "_ribbit_7"
NOMBRE = "rana_apuestas"
F_JERRY = JN["APUESTA"][0]                         # 270
APUESTA_OFRECE = 308                               # frame en que la rana ya tiene el papel estirado bajo la pata
RECIBE = 314                                        # las pepitas pasan de la pata de Jerry al papel
GUARDA = 338                                        # se las guarda
# Recorrido: la rana esta activa desde el frame 1 y NUNCA se queda mucho en un sitio: va de espectador en espectador (de
# este a oeste y de vuelta), se para PARADA frames a conversar (pregunta senalando con el lapiz y anota) y sigue.
# La unica espera larga es la de Jerry (APUESTA), que fija el guion de Jerry. armar_plan() llena PLAN y MIRA:
# PLAN = [(frame, (x, y))]: puntos consecutivos iguales = esta parada; MIRA = {(f0, f1): a quien mira mientras conversa}
PLAN = []
MIRA = {}
# RODEA EL CUADRILATERO: una vuelta en sentido horario por un pasillo exterior al publico (rectangulo ESQUINAS), sin repetir
# ningun sitio. Empieza en el lado este (INICIO), llega al punto de Jerry (lado sur) justo en T_JERRY[0] y sigue la vuelta
# hasta el final de la escena. Cada espectador se visita UNA vez (separados >= SEP m a lo largo del pasillo).
ESQUINAS = [(-31.9, -9.4), (-31.9, -16.9), (-43.0, -16.9), (-43.0, -6.9), (-31.9, -6.9), (-31.9, -9.4)]   # horario; el primer y ultimo punto = INICIO
INICIO = ESQUINAS[0]
ESPECT_RE = r"^(ribbit_\w+_ring|guard_ribbit_(2|3|4|5|11|12|13|15))$"      # espectadores con los que conversa
SEP = 2.0                                                               # separacion minima (m) entre dos paradas
V_PRE = None                                                            # velocidades: se calculan para llegar a Jerry en T_JERRY[0] y cerrar la vuelta al final
PARADA = 20                                                             # frames conversando con cada espectador (maximo seguido en un sitio)
T_JERRY = (262, 346)                                                    # llega a Jerry en 262 y se va en 346 (APUESTA de jerry_ranas3.py)


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


def anexar(archivo, nombres, col):
    with bpy.data.libraries.load(BASE + archivo, link=False) as (src, dst): dst.objects = [n for n in nombres if n in src.objects]
    out = [o for o in dst.objects if o]
    for o in out: col.objects.link(o)
    return out


def material(nombre, color, rough=0.6, metal=0.0):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    m.use_nodes = True; b = m.node_tree.nodes.get("Principled BSDF")
    if b:
        b.inputs["Base Color"].default_value = (*color, 1.0); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    m.diffuse_color = (*color, 1.0)
    return m


def crear_lapiz(col):
    """lapiz de 12 cm a lo largo de +Z: cuerpo hexagonal amarillo, virola, goma rosa, punta de madera y grafito"""
    if "lapiz_apuestas" in bpy.data.objects: return bpy.data.objects["lapiz_apuestas"]
    me = bpy.data.meshes.new("lapiz_apuestas"); bm = bmesh.new()
    mats = [material("lapiz_amarillo", (0.95, 0.72, 0.05)), material("lapiz_madera", (0.86, 0.66, 0.42)),
            material("lapiz_grafito", (0.12, 0.12, 0.13), 0.4), material("lapiz_virola", (0.75, 0.75, 0.78), 0.3, 1.0),
            material("lapiz_goma", (0.95, 0.52, 0.62))]
    r = 0.0045

    def anillo(z, rad, n=6):
        return [bm.verts.new((rad * math.cos(2 * math.pi * k / n + math.pi / 6), rad * math.sin(2 * math.pi * k / n + math.pi / 6), z)) for k in range(n)]

    def tubo(a, b, mi):
        for k in range(6):
            f = bm.faces.new((a[k], a[(k + 1) % 6], b[(k + 1) % 6], b[k])); f.material_index = mi
    goma0, goma1 = anillo(0.0, r * 0.95), anillo(0.008, r * 0.95)
    vir0, vir1 = anillo(0.008, r * 1.05), anillo(0.016, r * 1.05)
    cue0, cue1 = anillo(0.016, r), anillo(0.10, r)
    f = bm.faces.new(list(reversed(goma0))); f.material_index = 4
    tubo(goma0, goma1, 4); tubo(vir0, vir1, 3); tubo(cue0, cue1, 0)
    punta_m = anillo(0.114, r * 0.3)
    tubo(cue1, punta_m, 1)
    tip = bm.verts.new((0, 0, 0.12))
    for k in range(6):
        f = bm.faces.new((punta_m[k], punta_m[(k + 1) % 6], tip)); f.material_index = 2
    bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    o = bpy.data.objects.new("lapiz_apuestas", me); col.objects.link(o)
    return o


def preparar():
    col = bpy.data.collections.get("rana_apuestas_col")
    if col is None: col = bpy.data.collections.new("rana_apuestas_col"); sc.collection.children.link(col)
    if NOMBRE not in bpy.data.objects:
        nuevos = anexar("estructura_lista/ribbits/ribbit_7.blend", ["ribbit_7", "ribbit.001_ribbit_7", "Mesh_0_ribbit_7"], col)
        raiz = next(o for o in nuevos if o.parent is None); raiz.name = NOMBRE
        for o in nuevos:
            if o.type == 'ARMATURE': o.name = NOMBRE + "_arm"
            if o.animation_data: o.animation_data.action = None
    if "papel_apuestas" not in bpy.data.objects:
        o = anexar("objetos/vanilla/paper/paper.blend", ["paper"], col)[0]; o.name = "papel_apuestas"
    lapiz = crear_lapiz(col)
    for k in range(5):
        n = "pepita_apuesta_%d" % (k + 1)
        if n not in bpy.data.objects:
            o = anexar("objetos/vanilla/iron_nugget/iron_nugget.blend", ["iron_nugget"], col)[0]; o.name = n
    return bpy.data.objects[NOMBRE], bpy.data.objects[NOMBRE + "_arm"], bpy.data.objects["papel_apuestas"], lapiz, [bpy.data.objects["pepita_apuesta_%d" % (k + 1)] for k in range(5)]


ADELANTE = 0.30                                      # los brazos nacen a mitad del cuerpo (y 0.03) y son cortos (0.19): se adelantan al frente del cuerpo (y 0.30) para que las manos se vean


def mover_mundo(arm, bone, delta):
    """traslada el hueso `delta` (vector mundo) con su posicion local de pose (igual que apuntar pero con traslacion)"""
    pb = arm.pose.bones[bone]; vl.update()
    nuevo = Matrix.Translation(arm.matrix_world.inverted().to_3x3() @ delta) @ pb.matrix
    m = arm.convert_space(pose_bone=pb, matrix=nuevo, from_space='POSE', to_space='LOCAL')
    pb.location = m.to_translation(); vl.update()


def escala_a(o, lado):
    """escala uniforme para que la mayor dimension del objeto mida `lado`"""
    o.scale = (1, 1, 1); vl.update(); dm = max(o.dimensions)
    if dm > 1e-6: s = lado / dm; o.scale = (s, s, s)


def en_plan(f):
    for i, ((f0, a), (f1, b)) in enumerate(zip(PLAN[:-1], PLAN[1:])):
        if f0 <= f <= f1:
            a, b = Vector(a), Vector(b)
            if (a - b).length < 1e-4: return a, False
            u = (f - f0) / float(max(1, f1 - f0))
            sale = i > 0 and (Vector(PLAN[i - 1][1]) - a).length < 1e-4                    # viene de una parada: acelera
            llega = i + 2 < len(PLAN) and (Vector(PLAN[i + 2][1]) - b).length < 1e-4       # va a una parada: frena
            u = ss(u) if (sale and llega) else (u * u if sale else (1 - (1 - u) ** 2 if llega else u))
            return a.lerp(b, u), True
    return Vector(PLAN[-1][1]), False


def mirando(f):
    for (a, b), quien in MIRA.items():
        if a <= f <= b: return quien
    return None


def inicio_charla(f):
    for (a, b) in MIRA:
        if a <= f <= b: return a
    return f


def _xy(n, f=1):
    q = pos_raiz(n, f); return Vector((q.x, q.y))


RADIO_ESQUINA = 1.5
DIST_CHARLA = 0.85                                      # a cuantos metros del espectador se para a conversar
DIST_PASILLO = 1.0                                      # el pasillo pasa a esta distancia de cada espectador (por fuera del cuadrilatero)
ANCLAS_RE = r"^(ribbit_\w+_ring|guard_ribbit_(2|3|4|5|11|12|13|15)|cerdo\d*_ring|vaca\d*_ring|pollo_ring)$"   # publico que se bordea
CENTRO = Vector((-37.5, -12.0))                         # centro del cuadrilatero
V_MAX = 0.075                                           # tope de velocidad al andar por el pasillo (m por frame); si no alcanza el tiempo, la vuelta queda sin cerrar
V_ACERCA = 0.06                                         # m por frame al acercarse / alejarse del espectador


def _camino():
    """pasillo que BORDEA al publico: pasa a DIST_PASILLO de cada espectador, por fuera del cuadrilatero, en sentido horario
    desde el este (INICIO), suavizado (Chaikin) y remuestreado cada ~0.3 m. Devuelve vertices (Vector) y largos acumulados."""
    gente = {o.name: _xy(o.name) for o in bpy.data.objects if o.parent is None and re.match(ANCLAS_RE, o.name)}
    a0 = math.atan2(INICIO[1] - CENTRO.y, INICIO[0] - CENTRO.x)
    def rel(q): return (a0 - math.atan2(q.y - CENTRO.y, q.x - CENTRO.x)) % (2 * math.pi)             # horario
    orden = sorted(gente.values(), key=rel)
    pts = [Vector(INICIO)]
    for q in orden:
        u = (q - CENTRO).normalized(); pts.append(q + u * DIST_PASILLO)
    pts.append(Vector(INICIO))
    for _ in range(2):                                                                                # Chaikin: esquinas suaves
        nuevo = [pts[0]]
        for p, q in zip(pts[:-1], pts[1:]): nuevo += [p * 0.75 + q * 0.25, p * 0.25 + q * 0.75]
        pts = nuevo + [pts[-1]]
    for _ in range(12):                                                                                # que ningun punto quede a menos de 0.8 m de alguien
        for i, p in enumerate(pts):
            for q in gente.values():
                d = p - q
                if d.length < 0.8: pts[i] = q + (d.normalized() if d.length > 1e-6 else (q - CENTRO).normalized()) * 0.8; p = pts[i]
    res = [pts[0]]                                                                                     # remuestreo ~0.3 m
    for p, q in zip(pts[:-1], pts[1:]):
        n = max(1, int((q - p).length / 0.3))
        for k in range(1, n + 1): res.append(p.lerp(q, k / n))
    acum = [0.0]
    for p, q in zip(res[:-1], res[1:]): acum.append(acum[-1] + (q - p).length)
    return res, acum


def _punto_en(pts, acum, s):
    s = max(0.0, min(acum[-1], s))
    for i in range(len(pts) - 1):
        if s <= acum[i + 1] + 1e-9:
            u = (s - acum[i]) / max(1e-9, acum[i + 1] - acum[i]); return pts[i].lerp(pts[i + 1], u)
    return pts[-1].copy()


def _s_mas_cercano(pts, acum, c):
    mejor = (1e9, 0.0)
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; ab = b - a; t = max(0.0, min(1.0, (c - a).dot(ab) / ab.dot(ab)))
        d = (a + ab * t - c).length
        if d < mejor[0]: mejor = (d, acum[i] + (ab * t).length)
    return mejor[1]


DIST_JERRY = 1.85                                       # distancia Jerry-rana al intercambiar (antes 1.3: los cuerpos se tocaban); la rana estira el brazo y Jerry ofrece la pata


def punto_jerry():
    """donde espera la rana a Jerry: en la misma direccion (Jerry -> rana) que usa jerry_ranas3.py para mirarla, pero a DIST_JERRY"""
    j = Vector(tuple(JN["J_ABAJO"])); d = Vector(tuple(JN["RANA_APUESTAS"])) - j
    return j + d.normalized() * DIST_JERRY


def armar_plan(FIN):
    """vuelta unica al cuadrilatero: PLAN/MIRA. En cada parada la rana sale del pasillo y se acerca a DIST_CHARLA del espectador.
    Velocidades calculadas para estar en Jerry en T_JERRY[0] y cerrar la vuelta en FIN."""
    PLAN.clear(); MIRA.clear()
    pts, acum = _camino(); L = acum[-1]
    JP = punto_jerry(); sJ = _s_mas_cercano(pts, acum, JP)
    esp = [o for o in bpy.data.objects if o.parent is None and re.match(ESPECT_RE, o.name)]
    cand = sorted(((_s_mas_cercano(pts, acum, _xy(o.name)), o.name) for o in esp), key=lambda t: t[0])
    paradas = []
    for s, n in cand:
        if abs(s - sJ) < SEP * 0.8 or (s < 2.0) or (s > L - 2.0): continue
        if all(abs(s - s2) >= SEP for s2, _n in paradas): paradas.append((s, n))
    otros = {o.name: _xy(o.name) for o in esp}

    def posicion_charla(s, n):
        c = _punto_en(pts, acum, s); q = otros[n]; d = q - c
        if d.length <= DIST_CHARLA: return c
        u = d.normalized(); mejor = c
        for k in range(1, 41):                                            # se acerca hasta DIST_CHARLA, pero sin pisar a otro espectador
            p = c + u * (d.length - DIST_CHARLA) * (k / 40.0)
            if all((p - o).length >= 0.75 for m, o in otros.items() if m != n): mejor = p
            else: break
        return mejor
    stands = {n: posicion_charla(s, n) for s, n in paradas}
    exc = {n: (stands[n] - _punto_en(pts, acum, s)).length for s, n in paradas}
    pre = [(s, n) for s, n in paradas if s < sJ]; post = [(s, n) for s, n in paradas if s > sJ]
    extra = lambda lista: sum(2 * exc[n] / V_ACERCA for _s, n in lista)       # frames de acercarse y alejarse
    t_pre = (T_JERRY[0] - 1) - len(pre) * PARADA - 14 - extra(pre)
    t_post = (FIN - T_JERRY[1]) - len(post) * PARADA - 14 - 6 - extra(post)
    v1, v2 = sJ / max(1, t_pre), (L - sJ) / max(1, t_post)
    v2 = min(v2, V_MAX)
    print('rana v1=%.3f v2=%.3f' % (v1, v2))
    st = {"t": 1, "s": 0.0}
    PLAN.append((1, (pts[0].x, pts[0].y)))

    def ir_a(s_dest, v):
        s0 = st["s"]; dur = max(2, int(round((s_dest - s0) / v)))
        for i in range(len(pts)):
            if s0 < acum[i] < s_dest: PLAN.append((st["t"] + int(round((acum[i] - s0) / v)), (pts[i].x, pts[i].y)))
        q = _punto_en(pts, acum, s_dest); PLAN.append((st["t"] + dur, (q.x, q.y))); st["t"] += dur; st["s"] = s_dest

    def charla(s, n):
        c = _punto_en(pts, acum, s); q = stands[n]; dt = max(2, int(round((q - c).length / V_ACERCA)))
        if dt > 2:
            PLAN.append((st["t"] + dt, (q.x, q.y))); st["t"] += dt
        PLAN.append((st["t"] + PARADA, (q.x, q.y))); MIRA[(st["t"], st["t"] + PARADA)] = n; st["t"] += PARADA
        if dt > 2:
            PLAN.append((st["t"] + dt, (c.x, c.y))); st["t"] += dt

    for s, n in pre: ir_a(s, v1); charla(s, n)
    ir_a(sJ, v1); c = _punto_en(pts, acum, sJ)
    PLAN.append((T_JERRY[0], (JP.x, JP.y)))
    PLAN.append((T_JERRY[1], (JP.x, JP.y))); MIRA[(T_JERRY[0], T_JERRY[1])] = "jerry"; st["t"] = T_JERRY[1]
    PLAN.append((T_JERRY[1] + 14, (c.x, c.y))); st["t"] = T_JERRY[1] + 14
    for s, n in post: ir_a(s, v2); charla(s, n)
    ir_a(L, v2)
    PLAN.append((10 ** 6, (pts[-1].x, pts[-1].y)))


def construir():
    FIN = sc.frame_end
    armar_plan(FIN)
    raiz, arm, papel, lapiz, pepitas = preparar()
    P = arm.pose.bones; W = lambda: arm.matrix_world
    mano_de = lambda b: W() @ (P[b].head - (P[b].tail - P[b].head).normalized() * HAND)
    B = {k: k + SUF for k in ("body", "left_arm", "right_arm", "right_leg", "left_leg")}
    for b in B.values(): P[b].rotation_mode = 'XYZ'
    escala_a(papel, 0.40); escala_a(lapiz, 0.26)                                  # el doble de la escala original (0.20 / 0.13)
    for o in pepitas: o.scale = (0.24, 0.24, 0.24)                                # 0.12 de lado (antes 0.06); fija: las pepitas ocultas dan dimensiones viejas a escala_a
    ESC_P, ESC_L = papel.scale.copy(), lapiz.scale.copy()
    jr, ja = bpy.data.objects["jerry"], bpy.data.objects["Dog_001_rig"]
    ocultos = [o.name for r in (raiz, jr) for o in [r] + list(r.children_recursive) if o.hide_viewport]
    for n in ocultos: bpy.data.objects[n].hide_viewport = False
    raiz.animation_data_clear(); arm.animation_data_clear()
    for obj in (papel, lapiz): obj.parent = None; obj.animation_data_clear(); obj.rotation_mode = 'XYZ'      # se animan en el mundo (orientacion controlada)
    raiz.location = (PLAN[0][1][0], PLAN[0][1][1], SUELO); raiz.rotation_euler = (0, 0, 0)
    for b in B.values(): P[b].rotation_euler = (0, 0, 0)
    vl.update()
    # pata de Jerry mientras ofrece las pepitas (la rana estira el papel hacia ella)
    a0, a1 = JN["APUESTA_BOLSILLO"][0] + 4, GUARDA
    toe = {}
    for f in range(a0, RECIBE + 1):
        sc.frame_set(f)
        for x in [jr] + list(jr.children_recursive): x.hide_viewport = False
        vl.update(); toe[f] = ja.matrix_world @ ja.pose.bones["front_toe.R"].tail
    # ---- recorrido de la rana
    out = {"loc": [], "rot": [], "h": {b: [] for b in B.values()}, "p": {b: [] for b in B.values()}, "papel": [], "papel_r": [], "lapiz": [], "lapiz_r": []}; papel_w = {}
    prev_p, prev_l = Euler((0, 0, 0)), Euler((0, 0, 0))
    ys = []
    for f in range(1, FIN + 1):
        p, anda = en_plan(f); quien = mirando(f)
        if quien:
            q = pos_raiz(quien, f)
            d = Vector((q.x - p.x, q.y - p.y, 0))
        elif anda:
            p2, _ = en_plan(min(FIN, f + 3)); d = Vector((p2.x - p.x, p2.y - p.y, 0))
        else:
            d = Vector((0, 1, 0))
        ys.append(math.atan2(-d.x, d.y) if d.length > 1e-3 else (ys[-1] if ys else 0.0))
    ys = desenrollar(ys); hs = list(ys)
    for i in range(1, len(hs)): hs[i] = hs[i - 1] + (ys[i] - hs[i - 1]) * 0.3
    for i, f in enumerate(range(1, FIN + 1)):
        p, anda = en_plan(f); quien = mirando(f)
        salto = 0.05 * abs(math.sin(math.pi * f / 8.0)) if anda else 0.0
        raiz.location = (p.x, p.y, SUELO + salto); raiz.rotation_euler = (0, 0, hs[i])
        for b in B.values(): P[b].rotation_euler = (0, 0, 0); P[b].location = (0, 0, 0)
        vl.update()
        R3 = raiz.matrix_world.to_3x3(); fw = (R3 @ Vector((0, 1, 0))).normalized(); rt = (R3 @ Vector((1, 0, 0))).normalized(); up = (R3 @ Vector((0, 0, 1))).normalized()
        anota = quien is not None and not anda
        # ---- pesos de la coreografia con Jerry (pregunta -> "todo" -> pata al costado -> ofrece las pepitas -> las guarda)
        es_j = quien == "jerry"
        alcance = ventana(f, JN["APUESTA_BOLSILLO"][0] + 2, APUESTA_OFRECE, RECIBE + 3, RECIBE + 9) if es_j else 0.0          # estira el papel hacia la pata
        guarda = ventana(f, GUARDA - 10, GUARDA - 5, GUARDA - 1, GUARDA + 5) if es_j else 0.0                                   # inclina el papel hacia el cuerpo para guardarlas
        rotar_mundo(arm, B["body"], rt, D(-8 if anota else -4) + D(2) * math.sin(f * 0.3) + D(-10) * alcance)
        if anda: rotar_mundo(arm, B["body"], UP, D(6 * math.sin(2 * math.pi * f / 16.0)))
        for bn in (B["right_arm"], B["left_arm"]): mover_mundo(arm, bn, fw * ADELANTE)          # manos por delante del cuerpo
        mover_mundo(arm, B["right_arm"], fw * (0.30 * alcance))                                    # y el brazo derecho se estira hacia Jerry
        # brazo derecho: sostiene el papel delante del pecho
        hom_r = W() @ P[B["right_arm"]].head
        Tr = hom_r + fw * 0.16 + up * 0.02 - rt * 0.05
        if es_j:
            ft = toe[max(a0, min(RECIBE, f))]
            Tr = Tr.lerp(Vector((ft.x, ft.y, ft.z - 0.06)), alcance)                                 # la mano queda bajo la pata
            Tr = Tr + up * (0.10 * guarda) - fw * (0.06 * guarda)
        apuntar(arm, B["right_arm"], lambda: mano_de(B["right_arm"]), Tr)
        vl.update()
        hoja = mano_de(B["right_arm"])
        # papel: plano, sujeto por el borde derecho; se inclina hacia el cuerpo al guardar
        tilt = D(12) + D(35) * guarda - D(12) * alcance
        zdir = (up * math.cos(tilt) - fw * math.sin(tilt)).normalized(); xdir = rt
        ydir = zdir.cross(xdir).normalized(); xdir = ydir.cross(zdir).normalized()
        cen = hoja - xdir * (0.12 * (1 - alcance)) + ydir * 0.05 + zdir * 0.02
        Mp = Matrix((xdir, ydir, zdir)).transposed()
        # brazo izquierdo: lapiz; senala a quien habla, escribe en el papel y se queda quieto al esperar
        hom_l = W() @ P[B["left_arm"]].head
        Tl = hom_l + fw * 0.12 - up * 0.02 + rt * 0.03
        w_esc = 0.0; w_sen = 0.0; q_sen = None
        if anota:
            q_sen = pos_raiz(quien, f) + Vector((0, 0, 0.3 if es_j else 0.4))
            if es_j:                                                                 # pregunta (senala) -> "todo": anota rapido -> espera la entrega -> anota tras recibir
                w_sen = ventana(f, F_JERRY, F_JERRY + 4, F_JERRY + 14, F_JERRY + 18)
                w_esc = ramp(f, JN["APUESTA_HABLA"][0] + 1, JN["APUESTA_HABLA"][0] + 4) * (1 - ramp(f, JN["APUESTA_HABLA"][1], JN["APUESTA_HABLA"][1] + 4)) + ramp(f, RECIBE + 3, RECIBE + 7) * (1 - ramp(f, GUARDA - 11, GUARDA - 6)) + ramp(f, GUARDA + 3, GUARDA + 8)
                w_esc = min(1.0, w_esc)
            else:                                                                    # conversa: primero pregunta senalando con el lapiz, luego anota
                t0 = inicio_charla(f)
                w_sen = ventana(f, t0, t0 + 3, t0 + 9, t0 + 12); w_esc = ramp(f, t0 + 9, t0 + 13)
                rotar_mundo(arm, B["body"], rt, D(3) * math.sin(f * 0.55) * (1 - w_esc))      # asiente mientras habla
        punta_esc = cen + zdir * 0.03 + xdir * (0.06 * math.sin(f * 1.6)) + ydir * (0.03 * math.sin(f * 0.8))
        Tl = Tl.lerp(hom_l + fw * 0.22 + up * 0.10, w_sen).lerp(punta_esc + zdir * 0.06, w_esc)
        apuntar(arm, B["left_arm"], lambda: mano_de(B["left_arm"]), Tl)
        for s, lado in (("right_leg", 1), ("left_leg", -1)):
            b = B[s]; hip = W() @ P[b].head
            pie = (-up * 0.85 - fw * 0.3 + rt * lado * 0.2) if salto > 0.015 else (-up + rt * lado * 0.12)
            apuntar(arm, b, lambda b=b: W() @ P[b].tail, hip - pie.normalized() * 0.14)
        vl.update()
        if salto <= 0.015:                                                     # pisa el suelo
            dg = bpy.context.evaluated_depsgraph_get(); z = 1e9
            for x in raiz.children_recursive:
                if x.type == 'MESH' and x not in (papel, lapiz):
                    e = x.evaluated_get(dg); M = x.matrix_world; z = min(z, min((M @ v.co).z for v in e.data.vertices))
            dz = SUELO - z; raiz.location.z += dz; vl.update()
        else: dz = 0.0
        # ---- papel y lapiz en el mundo, con orientacion controlada (el ajuste de suelo dz se suma a lo calculado antes)
        up_dz = Vector((0, 0, dz)); cen = cen + up_dz
        hl = mano_de(B["left_arm"])
        if q_sen is not None and (w_sen + w_esc) > 0.02:
            objetivo = q_sen.lerp(punta_esc + up_dz, w_esc / (w_esc + w_sen))                # senala -> escribe
        else:
            objetivo = hl + (fw * 0.55 - up * 0.75 + rt * 0.15).normalized() * 0.2          # en reposo: punta hacia delante y abajo
        dl = objetivo - hl
        if dl.length < 0.05: dl = fw * 0.05 - up * 0.05
        T = hl + dl.normalized() * min(dl.length, 0.24)                                      # la punta llega a T (como mucho a 0.24 de la mano)
        dirl = (T - hl).normalized()
        origen = T - dirl * 0.26                                                              # el lapiz mide 0.26 a lo largo de +Z
        ql = dirl.to_track_quat('Z', 'Y')
        pl = Matrix.LocRotScale(origen, ql, ESC_L); pp = Matrix.LocRotScale(cen, Mp.to_quaternion(), ESC_P)
        papel_w[f] = pp
        prev_p = pp.to_euler('XYZ', prev_p); prev_l = pl.to_euler('XYZ', prev_l)
        out["papel"].append((f, tuple(cen))); out["papel_r"].append((f, tuple(prev_p))); out["lapiz"].append((f, tuple(origen))); out["lapiz_r"].append((f, tuple(prev_l)))
        out["loc"].append((f, tuple(raiz.location))); out["rot"].append((f, tuple(raiz.rotation_euler)))
        for b in B.values(): out["h"][b].append((f, tuple(P[b].rotation_euler))); out["p"][b].append((f, tuple(P[b].location)))

    def claves(obj, canales, nombre, const=()):
        obj.animation_data_create(); old = bpy.data.actions.get(nombre)
        if old: bpy.data.actions.remove(old)
        act = bpy.data.actions.new(nombre); obj.animation_data.action = act
        for path, cl in canales.items():
            for i_ in range(len(cl[0][1])):
                fc = act.fcurve_ensure_for_datablock(obj, path, index=i_); fc.keyframe_points.add(len(cl))
                fc.keyframe_points.foreach_set("co", [x for f_, v_ in cl for x in (f_, v_[i_])])
                for k in fc.keyframe_points: k.interpolation = 'CONSTANT' if path in const else 'LINEAR'
                fc.update()
    claves(raiz, {"location": out["loc"], "rotation_euler": out["rot"]}, NOMBRE + "_raiz")
    can = {'pose.bones["%s"].rotation_euler' % b: v for b, v in out["h"].items()}
    can.update({'pose.bones["%s"].location' % b: v for b, v in out["p"].items()})
    claves(arm, can, NOMBRE + "_anima")
    claves(papel, {"location": out["papel"], "rotation_euler": out["papel_r"]}, "papel_apuestas_acc")
    claves(lapiz, {"location": out["lapiz"], "rotation_euler": out["lapiz_r"]}, "lapiz_apuestas_acc")
    # ---- pepitas: aparecen en la pata de Jerry ("del bolsillo"), pasan al papel y la rana se las guarda
    for k, o in enumerate(pepitas):
        o.parent = None; o.animation_data_clear(); o.rotation_mode = 'XYZ'
        off = Vector((0.025 * math.cos(2 * math.pi * k / 5), 0.025 * math.sin(2 * math.pi * k / 5), 0.012 * (k % 2)))
        locs, rots = [], []
        for f in range(a0 - 1, a1 + 2):
            sobre = lambda ff: papel_w[min(ff, FIN)].translation + off * 1.2 + Vector((0, 0, 0.03))
            if f <= RECIBE - 2: p = toe.get(max(a0, min(RECIBE, f)), toe[a0]) + off + Vector((0, 0, 0.02))
            elif f <= RECIBE + 2:                                               # caen sobre el papel
                u = (f - (RECIBE - 2)) / 4.0; dest = sobre(f)
                p = toe[RECIBE] + off + Vector((0, 0, 0.02)); p = p.lerp(dest, ss(u)); p.z += 0.03 * math.sin(math.pi * u)
            else: p = sobre(f)
            locs.append((f, tuple(p))); rots.append((f, (0.0, 0.0, 0.6 * k + 0.05 * f)))
        vis = [(1, (1.0,)), (a0, (0.0,)), (a1 + 1, (1.0,))]
        claves(o, {"location": locs, "rotation_euler": rots, "hide_viewport": vis, "hide_render": vis}, o.name + "_acc", const=("hide_viewport", "hide_render"))
    for n in ocultos: bpy.data.objects[n].hide_viewport = True
    sc.frame_set(sc.frame_current)
    return {"rana": NOMBRE, "pepitas": len(pepitas), "recibe": RECIBE, "jerry_apuesta": JN["APUESTA"]}
