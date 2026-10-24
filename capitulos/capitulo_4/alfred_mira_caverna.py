# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: Alfred, con el pico de piedra en la mano derecha, abre la salida del tunel picando los dos bloques que la
tapan (4 golpes cada uno, con efecto_romper_bloque), camina con normalidad hasta bloque_stone_-99_-96_-19 (ciclo de caminar de
animacion_alfred (33).py, copiado en alfred_caminar_6_realistic.py; dobla un poco las rodillas solo al pasar el hueco de 2 m), y recien
ahi se da cuenta de la caverna: la mira con curiosidad (cabeza a los lados y arriba), se sorprende de lo profunda que es (respingo
elastico) y se arrodilla con la animacion de Mixamo "arrodillarse_1" (alfred_arrodillarse_1_mixamo.py). Solo huesos, el empty, el pico
y los bloques: NO toca las mallas de los ojos.
Para que pique y arranque de pie, el techo de las dos celdas del tunel detras del tapon sube a 3 m (como el final del tunel).
Uso: exec(open(ruta, encoding="utf8").read()); construir()      (repetible)
"""
import bpy, math, ast
from mathutils import Vector, Matrix

BASE = r"C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/alfred_cae_estalagmita.py"
ROMPER = r"C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/efecto_romper_bloque.py"
ARRODILLARSE = r"C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/alfred_arrodillarse_1_mixamo.py"
SUELO = 66.0157
X_TUNEL = 0.4529
DESTINO_Y = 83.8381                           # centro de bloque_stone_-99_-96_-19 (donde se arrodilla)
INICIO_Y = 86.8381                            # donde pica (celda -93)
TAPON_Y = 85.8381                             # celda -94: los dos bloques que tapan la salida
TAPON = [("bloque_stone_-99_-94_-17", 67.0157), ("bloque_andesite_-99_-94_-18", 66.0157)]   # arriba, abajo
TECHO_ALTO = ["bloque_stone_-99_-93_-16", "bloque_stone_-99_-92_-16"]                       # suben 1 bloque
HUECO_Y = (85.25, 86.45)                      # tramo de 2 m de alto (el tapon roto)
MALLAS = ["Mesh_%d_alfred" % i for i in range(6)]
PICO = "alfred_pico_piedra"
GOLPES_POR_BLOQUE = 4
F_GOLPE = 15
CICLO = 25                                    # frames por ciclo de pasos (animacion_alfred (33): 100 frames, 4 ciclos)
M_POR_CICLO = 1.0                             # metros por ciclo
F_MIRAR = 70                                  # se da cuenta y mira la caverna
F_SUSTO = 26                                  # respingo
F_MEZCLA = 8
HOMBROS = {"RightUpArm_alfred": (0.006604, 0.096746, -0.086079), "LeftUpArm_alfred": (0.013552, 0.074613, -0.085881)}
PIERNAS_ABIERTAS = {"RightUpLeg_alfred": (-0.030967, 0.605239, -0.163466), "LeftUpLeg_alfred": (0.005388, -0.342157, 0.195707)}   # animacion_alfred (35)
CODO_D, CODO_I, RODILLA_D = -0.822976, 0.334451, -0.20944    # parado_2 (animacion_alfred (34).py)
ANTORCHA_CARA = Vector((-0.55, 84.34, 67.52))   # punto de la cara -Y de bloque_stone_-100_-95_-18 donde la pone
ANTORCHA_MODELO = "antorcha_tunel5_9"
ANTORCHA_Z = 67.1656
ANTORCHA_NUEVA = "antorcha_alfred_salida"
F_ANT = (14, 14, 8, 12)                        # gira, alarga el brazo, la deja, vuelve
D = math.radians
MIRADA = [(0, 0.0, 0.1), (8, 0.0, 0.25), (20, D(38), -0.2), (34, D(42), -0.3), (48, D(-40), -0.15), (60, D(-30), 0.1), (70, D(0), 0.45)]


def _interp(tabla, f):
    for (a, *va), (b, *vb) in zip(tabla, tabla[1:]):
        if a <= f <= b:
            t = (f - a) / (b - a); t = t * t * (3 - 2 * t); return [x + (y - x) * t for x, y in zip(va, vb)]
    return list(tabla[-1][1:]) if f > tabla[-1][0] else list(tabla[0][1:])


def _zmin():
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); z = 1e9; zt = -1e9
    for n in MALLAS:
        o = bpy.data.objects[n]; e = o.evaluated_get(dg); me = e.to_mesh()
        zs = [(o.matrix_world @ v.co).z for v in me.vertices]; z = min(z, min(zs)); zt = max(zt, max(zs)); e.to_mesh_clear()
    return z, zt


# ----------------------------------------------------------------------------------------------- caminar (animacion_alfred (33))
R = dict(leg=D(50), knee=D(40), arm_x=D(90), arm_y=D(70), elbow=D(50), spine=D(0.1), neck=D(1.5))


def _sine(t): return -(math.cos(math.pi * t) - 1) / 2


def _cubic(t): return 4 * t ** 3 if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2


def _rodilla(ph):
    c = ph % 1.0
    return -R["knee"] * _sine(c / 0.5) if c < 0.5 else -R["knee"] * (1 - _sine((c - 0.5) / 0.5)) * 0.3


def _brazo(ph):
    return _sine(ph / 0.5) * R["arm_y"] * 2 - R["arm_y"] if ph < 0.5 else R["arm_y"] - _sine((ph - 0.5) / 0.5) * R["arm_y"] * 2


def _codo(ph):
    m = R["elbow"]
    if ph < 0.3: return _sine(ph / 0.3) * m * 0.85 + m * 0.15
    if ph < 0.7: return m - _cubic((ph - 0.3) / 0.4) * m * 0.6
    return m * 0.4 - _sine((ph - 0.7) / 0.3) * m * 0.25


def pose_caminar(pb, ciclo, amp=1.0, agacha=0.0):
    """valores locales de animacion_alfred (33).py; amp escala el paso (0 = quieto); agacha dobla las rodillas (hueco bajo)"""
    w = ciclo % 1.0
    pb["Spine_alfred"].rotation_euler = (math.sin(w * 2 * math.pi + math.pi / 6) * R["spine"] * amp, 0, math.cos(w * 2 * math.pi + math.pi / 3) * R["spine"] * 0.75 * amp)
    pb["Neck_alfred"].rotation_euler = (0, math.cos(w * 2 * math.pi + math.pi / 4) * R["neck"] * 0.5 * amp, math.sin(w * 2 * math.pi) * R["neck"] * amp)
    for lado, ph in (("Left", w), ("Right", (w + 0.5) % 1.0)):
        pb[lado + "UpLeg_alfred"].rotation_euler = (R["leg"] * math.sin(ph * 2 * math.pi) * amp + 0.5 * agacha, 0, 0)
        pb[lado + "knee_alfred"].rotation_euler = (_rodilla(ph) * amp - 1.0 * agacha, 0, 0)
    ph = (w + 0.25) % 1.0
    pb["RightUpArm_alfred"].rotation_euler = (R["arm_x"], _brazo(ph) * amp * 0.45, 0)        # con el pico: braceo mas corto
    pb["Rightelbow_alfred"].rotation_euler = (0, 0, -_codo(ph) * amp - 0.5)
    ph = (w + 0.75) % 1.0
    pb["LeftUpArm_alfred"].rotation_euler = (R["arm_x"], -_brazo(ph) * amp, 0)
    pb["Leftelbow_alfred"].rotation_euler = (0, 0, _codo(ph) * amp)
    for n in ("Hips_alfred", "Spine1_alfred", "Spine2_alfred", "face_alfred"): pb[n].rotation_euler = (0, 0, 0)


# ----------------------------------------------------------------------------------------------- escenario
def _preparar_tunel():
    """sube 1 bloque el techo de las celdas -93 y -92 (con pared a z 68 a los lados) y coloca los dos bloques del tapon"""
    O = bpy.data.objects
    for n in TECHO_ALTO: O[n].location.z = SUELO + 3              # origen abajo: el techo pasa de z 68 a z 69
    mod = O["bloque_stone_-98_-93_-17"]
    for n in TECHO_ALTO:
        y = O[n].location.y
        for x, lado in ((X_TUNEL - 1, "o"), (X_TUNEL + 1, "e")):
            nombre = "bloque_stone_pared_alta_%s_%s" % (n.split("_")[3], lado); o = O.get(nombre)
            if o is None:
                o = mod.copy(); o.name = nombre
                for c in mod.users_collection: c.objects.link(o)
            o.location = (x, y, SUELO + 2)
    for nombre, z in TAPON:
        o = O.get(nombre)
        if o is None:
            tipo = nombre.split("_")[1]; m = next(x for x in O if x.name.startswith("bloque_%s_" % tipo) and x.type == 'MESH')
            o = m.copy(); o.name = nombre
            for c in m.users_collection: c.objects.link(o)
        if o.animation_data: o.animation_data_clear()
        o.location = (X_TUNEL, TAPON_Y, z); o.rotation_euler = (0, 0, 0); o.hide_render = o.hide_viewport = False


def _pico():
    O = bpy.data.objects; p = O.get(PICO)
    if p is None:
        p = O["stone_pickaxe"].copy(); p.name = PICO
        for c in O["stone_pickaxe"].users_collection: c.objects.link(p)
    p.hide_render = False; p.hide_viewport = False; p.parent = None
    if p.animation_data: p.animation_data_clear()
    p.rotation_mode = 'QUATERNION'; return p


# ----------------------------------------------------------------------------------------------- construir
def construir():
    B = {"__name__": "b"}; exec(open(BASE, encoding="utf8").read(), B)
    O = bpy.data.objects; emp = O["alfred"]; arm = O["Armature"]; rig = B["Rig"](); pb = arm.pose.bones; sc = bpy.context.scene
    for o in (emp, arm):
        if o.animation_data: o.animation_data_clear()
    for b in pb: b.rotation_mode = 'XYZ'; b.location = (0, 0, 0)
    for n, loc in HOMBROS.items():                                        # hombros en su sitio (parado_2 / caminar de Mixamo)
        pb[n].location = loc; pb[n].keyframe_insert("location", frame=1)
    _preparar_tunel(); pico = _pico()
    emp.rotation_mode = 'XYZ'; emp.rotation_euler = (0, 0, math.pi)
    st = {"rel": None}

    def clave(f, y, llevar=False):
        pb["Hips_alfred"].location = (0, 0, 0)
        emp.location = (X_TUNEL, y, emp.location.z); zmin, ztop = _zmin(); emp.location.z += SUELO - zmin
        emp.keyframe_insert("location", frame=f); emp.keyframe_insert("rotation_euler", frame=f)
        for b in B["ORDEN"]: pb[b].keyframe_insert("rotation_euler", frame=f)
        bpy.context.view_layer.update()
        Mb = arm.matrix_world @ pb["Rightelbow_alfred"].matrix
        if st["rel"] is None:                                            # agarre como un martillo: mango perpendicular al antebrazo
            yb = (Mb.to_3x3() @ Vector((0, 1, 0))).normalized(); up = Vector((0, 0, 1)); d = (up - yb * up.dot(yb)).normalized()
            mano = Mb @ Vector((0, B["L_ANTEBRAZO"], 0))
            st["rel"] = Mb.inverted() @ (Matrix.Translation(mano) @ B["matriz_pico"](Vector((0, 0, 0)), d))
        if llevar:                                                       # caminando / parado: lo lleva con el mango hacia delante y arriba
            yb = (Mb.to_3x3() @ Vector((0, 1, 0))).normalized(); fw = emp.matrix_world.to_3x3() @ Vector((0, 1, 0))
            q = (fw * 0.75 + Vector((0, 0, 0.65))).normalized(); d = (q - yb * q.dot(yb)).normalized()
            B["poner_matriz"](pico, B["matriz_pico"](Mb @ Vector((0, B["L_ANTEBRAZO"], 0)), d))
        else:
            B["poner_matriz"](pico, Mb @ st["rel"])
        for dp in ("location", "rotation_quaternion", "scale"): pico.keyframe_insert(dp, frame=f)
        return ztop + SUELO - zmin

    # 1) picar los dos bloques (de pie, 4 golpes cada uno)
    Rb = {"__name__": "rb"}; exec(open(ROMPER, encoding="utf8").read(), Rb)
    f = 1; golpes = {}
    for n_b, (nombre, zb) in enumerate(TAPON):
        alto = 1.0 if n_b == 0 else 0.0; lista = []
        for g in range(GOLPES_POR_BLOQUE):
            for t in range(F_GOLPE):
                w = (t / 10.0) ** 0.7 if t < 10 else (1 - ((t - 9) / 3.0) ** 2 if t < 13 else 0.1 * (t - 12))
                w = max(0.0, min(1.0, w))
                th = 0.12 + 0.18 * (1 - w) + 0.3 * (1 - alto); cab = 0.05 + 0.3 * (1 - alto)
                dirs = B["pose_torso"](th, cab); dirs.update(B["piernas"](0.1, 0.2 + 0.4 * (1 - alto), -0.2 - 0.5 * (1 - alto)))
                dirs["LeftUpArm_alfred"] = (-0.25, 0.25, -1); dirs["Leftelbow_alfred"] = (-0.1, 0.5, -0.8)
                pose, _c = rig.resolver(dict(dirs, RightUpArm_alfred=(0.2, 0, -1), Rightelbow_alfred=(0.05, 0.2, -1)), {}, aplicar=False)
                hom = pose["RightUpArm_alfred"].translation
                golpe = hom + Vector((-0.02, 0.3, -0.1 - 0.5 * (1 - alto))); arriba = hom + Vector((0.14, -0.02, 0.5))
                B["resolver_con_brazos"](rig, dirs, golpe.lerp(arriba, w), None, polo_d=(1, -0.4, -0.6))
                clave(f, INICIO_Y)
                if t == 12: lista.append(f)
                f += 1
        golpes[nombre] = lista; ob = O[nombre]
        Rb["romper"](nombre, lista, contacto=(X_TUNEL, TAPON_Y + 0.5, zb + 0.5))
        for fr, v in ((1, False), (lista[-1], True)):
            ob.hide_viewport = v; ob.hide_render = v; ob.keyframe_insert("hide_viewport", frame=fr); ob.keyframe_insert("hide_render", frame=fr)
    f_pica = f + 3
    # 2) caminar con normalidad hasta el borde
    dist = INICIO_Y - DESTINO_Y; n_ciclos = dist / M_POR_CICLO; f_util = int(round(n_ciclos * CICLO)); f_andar = f_util + 8
    techo_max = 0.0
    for k in range(f_andar + 1):
        u = min(1.0, k / f_util); y = INICIO_Y - dist * u
        amp = min(1.0, k / 8.0, max(0.0, (f_util - k) / 8.0 + 0.0))
        dentro = max(0.0, min(1.0, min(y - HUECO_Y[0], HUECO_Y[1] + 0.45 - y) / 0.35))   # pasando el hueco bajo
        for c in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0):                   # dobla las rodillas solo lo justo para no tocar el techo
            pose_caminar(pb, n_ciclos * u, amp, c * dentro)
            emp.location = (X_TUNEL, y, emp.location.z); zmin, ztop = _zmin()
            if dentro == 0 or ztop - zmin + SUELO < 67.98: break
        alto_cab = clave(f_pica + k, y, llevar=True)
        if dentro > 0: techo_max = max(techo_max, alto_cab)
    f = f_pica + f_andar + 1
    # 2b) pone una antorcha nueva en la cara del bloque de su derecha (gira, la coloca con la mano izquierda y vuelve)
    f = _poner_antorcha(B, rig, emp, arm, pb, clave, f)
    # 3) recien se da cuenta: mira la caverna con curiosidad y se sorprende (de pie en el borde)
    for k in range(F_MIRAR + F_SUSTO):
        yaw, pitch = _interp(MIRADA, k)
        s = 0.0
        if k >= F_MIRAR:
            t = (k - F_MIRAR) / F_SUSTO; s = math.sin(math.pi * min(1, t * 1.6)) * math.exp(-2.2 * t) * (1 + 0.35 * math.sin(3 * math.pi * t))
        dirs = B["pose_torso"](0.06 + 0.15 * max(0.0, pitch) - 0.35 * s, pitch - 0.7 * s)   # sin direcciones de piernas: quedan rectas (reposo)
        giros = {"Neck_alfred": yaw * 0.45, "face_alfred": yaw * 0.55, "Spine2_alfred": yaw * 0.15}
        rig.resolver(dirs, giros, aplicar=True)
        _piernas_abiertas(pb, 1.0)                                         # parado con las piernas abiertas
        pb["RightUpArm_alfred"].rotation_euler = (R["arm_x"], 0, 0); pb["Rightelbow_alfred"].rotation_euler = (0, 0, CODO_D - 0.5 * s)
        pb["LeftUpArm_alfred"].rotation_euler = (R["arm_x"], 0, 0); pb["Leftelbow_alfred"].rotation_euler = (0, 0, CODO_I + 1.0 * s)
        clave(f + k, DESTINO_Y, llevar=True)
    f += F_MIRAR + F_SUSTO
    # 4) se arrodilla (Mixamo) en el bloque
    datos = _datos_mixamo(); k0 = f + F_MEZCLA
    for kf in range(1, 50):
        for n, claves in datos.items():
            if n in pb: pb[n].rotation_euler = claves[kf]
        clave(k0 + kf - 1, DESTINO_Y, llevar=True)
    _acelerar(VELOCIDAD)
    sc.frame_set(1)
    return {"picar": (1, f_pica - 1), "golpes": golpes, "andar": (f_pica, f_pica + f_andar), "mira_y_susto": (f - F_MIRAR - F_SUSTO, f),
            "arrodillarse": (k0, k0 + 48), "cabeza_en_hueco": round(techo_max, 3)}


def _piernas_abiertas(pb, w):
    """piernas abiertas de la pose parado (animacion_alfred (35).py), mezcladas con w (0 = juntas)"""
    for n, v in PIERNAS_ABIERTAS.items(): pb[n].rotation_euler = tuple(a * w for a in v)
    pb["Rightknee_alfred"].rotation_euler = (0, 0, 0); pb["Leftknee_alfred"].rotation_euler = (0, 0, 0)


def _antorcha_nueva():
    O = bpy.data.objects; mod = O[ANTORCHA_MODELO]; e = O.get(ANTORCHA_NUEVA)
    if e:
        for ch in list(e.children): bpy.data.objects.remove(ch, do_unlink=True)
        bpy.data.objects.remove(e, do_unlink=True)
    e = mod.copy(); e.name = ANTORCHA_NUEVA
    for c in mod.users_collection: c.objects.link(e)
    for ch in mod.children:
        n = ch.copy()
        if ch.type == 'LIGHT': n.data = ch.data.copy()
        if n.animation_data: n.animation_data_clear()
        for c in ch.users_collection: c.objects.link(n)
        n.parent = e; n.matrix_parent_inverse = ch.matrix_parent_inverse.copy()
    if e.animation_data: e.animation_data_clear()
    e.rotation_mode = 'XYZ'; return e


def _matriz_pared(e):
    """antorcha de pared en la cara -Y: inclinada 22.5 grados hacia -Y y con la base 4 cm dentro del bloque"""
    e.rotation_euler = (math.radians(22.5), 0, 0); e.location = ANTORCHA_CARA; bpy.context.view_layer.update()
    m = next(c for c in e.children if "main" in c.name); ps = [m.matrix_world @ v.co for v in m.data.vertices]
    base = min(ps, key=lambda p: p.z)
    e.location = e.location + Vector((ANTORCHA_CARA.x - base.x, (ANTORCHA_CARA.y + 0.04) - base.y, ANTORCHA_CARA.z - base.z))
    e.location.z = ANTORCHA_Z                                              # altura que pidio el usuario
    bpy.context.view_layer.update(); return e.matrix_world.copy(), base


def _poner_antorcha(B, rig, emp, arm, pb, clave, f):
    e = _antorcha_nueva(); M_pared, _ = _matriz_pared(e)
    m = next(c for c in e.children if "main" in c.name)
    yaw0 = emp.rotation_euler.z; w = Vector((ANTORCHA_CARA.x - X_TUNEL, ANTORCHA_CARA.y - DESTINO_Y)).normalized()
    yaw1 = math.atan2(-w.x, w.y); yaw1 = yaw0 + (yaw1 - yaw0 + math.pi) % (2 * math.pi) - math.pi
    t_gira, t_brazo, t_deja, t_vuelve = F_ANT; total = sum(F_ANT); f_suelta = f + t_gira + t_brazo
    for k in range(total + 1):
        if k <= t_gira: g = k / t_gira; r = 0.0
        elif k <= t_gira + t_brazo: g = 1.0; r = (k - t_gira) / t_brazo
        elif k <= t_gira + t_brazo + t_deja: g = 1.0; r = 1.0
        else: g = 1 - (k - t_gira - t_brazo - t_deja) / t_vuelve; r = g
        g = g * g * (3 - 2 * g); r = r * r * (3 - 2 * r)
        emp.rotation_euler.z = yaw0 + (yaw1 - yaw0) * g
        bpy.context.view_layer.update()
        dirs = B["pose_torso"](0.1 + 0.3 * r, 0.15 + 0.1 * r)
        rig.resolver(dirs, {}, aplicar=True)
        _piernas_abiertas(pb, min(1.0, k / 8.0))
        pb["RightUpArm_alfred"].rotation_euler = (R["arm_x"], 0, 0); pb["Rightelbow_alfred"].rotation_euler = (0, 0, CODO_D)
        pose, _c = rig.resolver({**dirs}, {}, aplicar=False)
        destino = arm.matrix_world.inverted() @ (ANTORCHA_CARA + Vector((0.0, -0.12, -0.05)))   # a la cara del bloque (marco armature)
        hom = pose["LeftUpArm_alfred"].translation; reposo = hom + Vector((-0.1, 0.25, -0.45))
        Gi = reposo.lerp(destino, r)
        B["resolver_con_brazos"](rig, dirs, None, Gi, polo_i=(-1, -0.5, -0.5))
        _piernas_abiertas(pb, min(1.0, k / 8.0))
        pb["RightUpArm_alfred"].rotation_euler = (R["arm_x"], 0, 0); pb["Rightelbow_alfred"].rotation_euler = (0, 0, CODO_D)
        clave(f + k, DESTINO_Y, llevar=True)
        if f + k < f_suelta:                                               # la lleva en la mano izquierda, de pie
            Mb = arm.matrix_world @ pb["Leftelbow_alfred"].matrix; mano = Mb @ Vector((0, B["L_ANTEBRAZO"], 0))
            e.matrix_world = Matrix.Translation(mano + Vector((0, 0, -0.08))) @ Matrix.Rotation(emp.rotation_euler.z, 4, 'Z')
        else:
            e.matrix_world = M_pared
        e.keyframe_insert("location", frame=f + k); e.keyframe_insert("rotation_euler", frame=f + k)
    for ch in [e] + list(e.children):                                     # aparece cuando la saca (antes no existe)
        for fr, h in ((1, True), (f, False)):
            ch.hide_render = h; ch.hide_viewport = h; ch.keyframe_insert("hide_render", frame=fr); ch.keyframe_insert("hide_viewport", frame=fr)
    emp.rotation_euler.z = yaw0
    return f + total + 1


VELOCIDAD = 0.7                               # toda la animacion un 30% mas rapida (los frames se escalan desde el 1)


def _objetos_animacion():
    O = bpy.data.objects
    nombres = ["alfred", "Armature", PICO, ANTORCHA_NUEVA] + [n for n, _ in TAPON]
    obs = [O[n] for n in nombres if n in O]
    obs += [c for c in O[ANTORCHA_NUEVA].children] if ANTORCHA_NUEVA in O else []
    obs += [o for o in O if any(o.name.startswith("FXR_" + n) for n, _ in TAPON)]
    return obs


def _acelerar(k):
    """escala el tiempo de todas las claves (y modificadores Cycles no hay) de la animacion de Alfred: f -> 1 + (f - 1) * k"""
    hechos = 0
    for o in _objetos_animacion():
        for idb in (o, o.data if o.type == 'LIGHT' else None):
            if idb is None or not idb.animation_data or not idb.animation_data.action: continue
            for lay in idb.animation_data.action.layers:
                for st in lay.strips:
                    for cb in st.channelbags:
                        for fc in cb.fcurves:
                            for kp in fc.keyframe_points:
                                for pt in (kp.co, kp.handle_left, kp.handle_right): pt[0] = 1 + (pt[0] - 1) * k
                            fc.update(); hechos += 1
    return hechos


def _datos_mixamo():
    arbol = ast.parse(open(ARRODILLARSE, encoding="utf8").read())
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and getattr(nodo.targets[0], "id", "") == "KEYFRAME_DATA":
            return ast.literal_eval(nodo.value)
    return {}
