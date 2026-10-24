# -*- coding: utf-8 -*-
"""Un segundo Alfred (clon del rig `alfred`) de pie en (-98.5, -41.5, -18.0), dentro del tunel, mirando a +X, picando con el pico de piedra la veta de carbon
de la pared este (bloques bloque_coal_ore_-98_-42_-18 / -17, cara en x = -98). Reutiliza el solucionador de poses (direcciones de huesos en el marco del personaje)
y el pico de `alfred_cae_estalagmita.py`; solo cambia el golpe: en vez de clavar el pico en el suelo, lo lleva de arriba hacia la pared a la altura del pecho.
Parte de la pose `preparado para picar.json` (manos delante, pico a la altura de la cintura), lo levanta delante y golpea; un golpe cada 22 frames (el cuerpo retrocede un poco tras cada impacto, como en la animacion original).
Uso en Blender: exec(open(ruta,encoding="utf8").read()); crear_clon(); hornear()
"""
import bpy, math, json
from mathutils import Vector, Matrix, Quaternion, Euler

CARPETA = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4"
FUENTE = CARPETA + r"\alfred_cae_estalagmita.py"
SUF = "_carbon"
ROOT, ARM, PICO = "alfred" + SUF, "Armature" + SUF, "stone_pickaxe" + SUF
ORIGEN = ["alfred", "Armature", "Mesh_0_alfred", "Mesh_1_alfred", "Mesh_2_alfred", "Mesh_3_alfred", "Mesh_4_alfred", "Mesh_5_alfred",
          "ojo_derecho_alfred", "ojo_izquierdo_alfred", "stone_pickaxe"]
PUNTO = Vector((-98.5, -41.5, -18.0))        # donde esta parado Alfred (suelo del tunel)
YAW = -math.pi / 2                            # mira hacia +X (la pared con el carbon)
PARED_DIST = 0.38                             # de su posicion a la cara de la pared (x = -98)
ALTO_GOLPE = 0.95                             # altura del impacto sobre el suelo (entre los dos bloques de carbon)
F0, F1 = 1, 261
PERIODO = 22
POSE_PREPARADO = 'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/poses/preparado para picar.json'
GOLPES = list(range(PERIODO, F1 + 1, PERIODO))
BETA_PARED = math.radians(70)                 # inclinacion del mango al impactar: la punta del pico apunta a la pared


def cargar():
    ns = {"__name__": "pica_carbon"}
    exec(open(FUENTE, encoding="utf8").read(), ns)
    ns["ARM"], ns["ROOT"] = ARM, ROOT
    return ns


def crear_clon():
    obj = bpy.data.objects
    nuevos = []
    if ROOT not in obj:
        vl = bpy.context.view_layer
        previo = [o for o in vl.objects if o.select_get()]
        activo = vl.objects.active
        ocultos = [n for n in ORIGEN if n in vl.objects and obj[n].hide_get()]
        for o in vl.objects:
            o.select_set(False)
        for n in ORIGEN[:-1]:                                      # el pico se copia aparte (no es hijo del rig)
            o = obj[n]
            o.hide_set(False)
            o.select_set(True)
        vl.objects.active = obj["Armature"]
        bpy.ops.object.duplicate(linked=False)
        nuevos = list(bpy.context.selected_objects)
        for o in nuevos:
            o.name = o.name.rsplit(".", 1)[0] + SUF
        for n in ocultos:                                          # el original vuelve a como estaba
            if n in obj:
                obj[n].hide_set(True)
        for o in vl.objects:
            o.select_set(False)
        for o in previo:
            if o.name in vl.objects:
                o.select_set(True)
        vl.objects.active = activo
    if PICO not in obj:
        src = obj["stone_pickaxe"]
        cp = src.copy()
        cp.data = src.data.copy()
        cp.name = PICO
        cp.hide_viewport = cp.hide_render = False                  # el original esta oculto
        for c in src.users_collection:
            c.objects.link(cp)
        nuevos.append(cp)
    ar = obj[ARM]                                                  # pose de reposo, sin animacion heredada
    ar.animation_data_clear()
    for pb in ar.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    for n in (ROOT, PICO):
        obj[n].animation_data_clear()
    rec = bpy.data.collections.get("luz_entrada_receptores")      # que reciba la luz de la entrada como el Alfred original
    if rec:
        for n in [o for o in ORIGEN]:
            o = obj[n + SUF]
            if o.name not in rec.objects:
                rec.objects.link(o)
    return [n + SUF for n in ORIGEN]


def cargar_pose_preparado():
    """eulers (rad) de los huesos de `preparado para picar.json` (pose de partida que dio el usuario)"""
    with open(POSE_PREPARADO, encoding="utf8") as fh:
        bones = json.load(fh)["poses"][0]["bones"]
    out = {}
    for n, b in bones.items():
        if not n.startswith("no_bone"):
            e = b["local_space"]["rotation_euler_rad"]
            out[n] = Euler((e["x"], e["y"], e["z"]), 'XYZ')
    return out


def suave_(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def fase_c(f):
    """posicion en el ciclo: 0 = preparado (pose del json), 1 = pico levantado delante, 2 = impacto en la pared"""
    r = PERIODO - 1
    for g in GOLPES:
        t = f - (g - r)
        if not 0 <= t <= r:
            continue
        if t < 4:
            return 0.0 if g == GOLPES[0] else 2.0 * (1.0 - suave_(t / 4.0))     # tras el impacto vuelve a la posicion de partida
        if t < r - 13:
            return 0.0
        if t < r - 8:
            return suave_((t - (r - 13)) / 5.0)                                 # levanta el pico
        if t < r - 4:
            return 1.0
        u = (t - (r - 4)) / 4.0
        return 1.0 + u * u                                                      # golpe
    if f > GOLPES[-1]:
        return 2.0 * (1.0 - suave_((f - GOLPES[-1]) / 4.0))
    return 0.0


def construir():
    ns = cargar()
    Rig, aplicar_estado = ns["Rig"], ns["aplicar_estado"]
    lerp, vlerp, norm, matriz_pico = ns["lerp"], ns["vlerp"], ns["norm"], ns["matriz_pico"]
    ORDEN, BETA_ALTO = ns["ORDEN"], ns["BETA_ALTO"]
    PUNTA_D, PUNTA_E, LARGO_ANT = ns["PUNTA_D"], ns["PUNTA_E"], ns["L_ANTEBRAZO"]
    rig = Rig()
    pb = rig.pb
    json_eul = cargar_pose_preparado()
    json_q = {n: json_eul[n].to_quaternion() for n in ORDEN}

    def mano(lado):
        """punto de agarre (ultimo tramo util del antebrazo) en el marco del armature"""
        e = pb[lado + "elbow_alfred"]
        return Vector(e.head) + (Vector(e.tail) - Vector(e.head)).normalized() * LARGO_ANT

    for n in ORDEN:                                               # pose de partida del usuario
        pb[n].rotation_mode = 'XYZ'
        pb[n].rotation_euler = json_eul[n]
        pb[n].location = (0, 0, 0)
    bpy.context.view_layer.update()
    Gd0, Gi0 = mano("Right"), mano("Left")                       # donde tiene las manos en esa pose
    d0 = norm(Gd0 - Gi0)

    def estado_golpe():
        th, tg = 0.20, 0.30
        dirs = ns["pose_torso"](th, cabeza=0.12)
        dirs.update(ns["piernas"](0.06, tg, -tg))
        _, colas, _ = ns["resolver_con_brazos"](rig, dirs, aplicar=False)
        piso = min(colas["Rightknee_alfred"].z, colas["Leftknee_alfred"].z) + ns["SUELO_PIE"]
        yf = (colas["Rightknee_alfred"].y + colas["Leftknee_alfred"].y) / 2
        d = Vector((0, math.sin(BETA_PARED), math.cos(BETA_PARED)))
        e = Vector((0, math.cos(BETA_PARED), -math.sin(BETA_PARED)))
        G = Vector((0, yf + PARED_DIST - 0.02, piso + ALTO_GOLPE)) - d * PUNTA_D - e * PUNTA_E
        return dict(th=th, cab=0.12, lado=0.0, sep=0.06, cad=tg, rod=-tg, Gd=G, Gi=G - d * 0.22, d=d)

    K0 = dict(th=0.24, cab=0.15, lado=0.0, sep=0.06, cad=0.05, rod=-0.05, Gd=Gd0, Gi=Gi0, d=d0)
    dw = norm((0.0, -0.25, 1.0))
    Gw = Gd0 + Vector((0.0, -0.02, 0.55))
    K1 = dict(th=0.06, cab=0.0, lado=0.0, sep=0.06, cad=0.10, rod=-0.10, Gd=Gw, Gi=Gw - dw * 0.22, d=dw)
    claves = [K0, K1, estado_golpe()]

    def estado(c):
        i = min(int(c), 1)
        t = c - i
        a, b = claves[i], claves[i + 1]
        return {k: (vlerp(a[k], b[k], t) if isinstance(a[k], Vector) else lerp(a[k], b[k], t)) for k in a}

    rot = Quaternion((0, 0, 1), YAW)
    datos = []
    previo = {n: json_eul[n] for n in ORDEN}
    for f in range(F0, F1 + 1):
        c = fase_c(f)
        st = estado(c)
        kg = min([f - g for g in GOLPES if f > g] or [99])
        if 1 <= kg < 10:                                          # el pico rebota y el cuerpo retrocede
            r = math.exp(-(kg - 1) / 2.5) * math.cos(0.9 * (kg - 1))
            st["th"] -= 0.08 * r
            st["Gd"] = Vector(st["Gd"]) + Vector((0, -0.03 * r, 0.06 * r))
        aplicar_estado(rig, st)
        w = min(1.0, c * 3.0)
        w = w * w * (3 - 2 * w)                                   # 0 = pose exacta del json
        eul = {}
        for n in ORDEN:
            qik = Euler(pb[n].rotation_euler, 'XYZ').to_quaternion()
            eul[n] = json_q[n].slerp(qik, w).to_euler('XYZ', previo[n])
            pb[n].rotation_euler = eul[n]
        bpy.context.view_layer.update()
        previo = eul
        rk, lk = Vector(pb["Rightknee_alfred"].tail), Vector(pb["Leftknee_alfred"].tail)
        piso = min(rk.z, lk.z) + ns["SUELO_PIE"]
        yf = (rk.y + lk.y) / 2
        loc = Vector((PUNTO.x, PUNTO.y, 0.0)) - rot @ Vector((0, yf, 0)) + Vector((0, 0, PUNTO.z - piso))
        M = Matrix.Translation(loc) @ rot.to_matrix().to_4x4() @ matriz_pico(mano("Right"), norm(st["d"]))
        datos.append((f, loc, {n: tuple(e) for n, e in eul.items()}, M))
    return dict(f_ini=F0, f_fin=F1, golpes=GOLPES), datos, rot


def hornear(info=None, datos=None, rot=None):
    if info is None:
        info, datos, rot = construir()
    obj = bpy.data.objects
    raiz, ar, pico = obj[ROOT], obj[ARM], obj[PICO]
    raiz.rotation_mode = 'QUATERNION'
    pico.rotation_mode = 'QUATERNION'
    for f, loc, eul, M in datos:
        raiz.location = loc
        raiz.rotation_quaternion = rot
        raiz.keyframe_insert("location", frame=f)
        raiz.keyframe_insert("rotation_quaternion", frame=f)
        for n, e in eul.items():
            ar.pose.bones[n].rotation_mode = 'XYZ'
            ar.pose.bones[n].rotation_euler = e
            ar.pose.bones[n].keyframe_insert("rotation_euler", frame=f)
        l, q, s = M.decompose()
        pico.location, pico.rotation_quaternion, pico.scale = l, q, s
        pico.keyframe_insert("location", frame=f)
        pico.keyframe_insert("rotation_quaternion", frame=f)
        pico.keyframe_insert("scale", frame=f)
    raiz["f_golpes"] = ",".join(str(g) for g in info["golpes"])
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    return info


def sonorizar(vol=0.5):
    """un golpe de piedra del add-on Alfred Sonidos en cada impacto del pico (tiras con origen 'alfred_carbon')"""
    import importlib.util, sys
    m = sys.modules.get("alfred_sonidos_local")
    if m is None:
        spec = importlib.util.spec_from_file_location("alfred_sonidos_local", CARPETA + r"\alfred_sonidos\__init__.py")
        m = importlib.util.module_from_spec(spec)
        sys.modules["alfred_sonidos_local"] = m
        spec.loader.exec_module(m)
        m.register()
    sc = bpy.context.scene
    p = sc.mcsnd
    m.indice(p, forzar=True)
    ed = sc.sequence_editor or sc.sequence_editor_create()
    for t in [t for t in m._strips(ed) if t.name.startswith(m.PREFIJO) and t.get("mcsnd_origen") == "alfred_carbon"]:
        m._strips(ed).remove(t)
    rng = m.rng_de(p)
    rutas = m.rutas_de(p, "block.stone.break")
    n = 0
    for g in GOLPES:
        t = m.colocar(bpy.context, p, rutas, g, "golpes", "block_stone_break", vol * (0.85 + 0.3 * rng.random()), 0, rng)
        if t:
            t["mcsnd_origen"] = "alfred_carbon"
            n += 1
    return n
