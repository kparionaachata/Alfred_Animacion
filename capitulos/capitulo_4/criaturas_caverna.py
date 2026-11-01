# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: criaturas (Skeleton, Zombie, Zombie bebe, Creeper) caminando al azar por el suelo de la caverna, colocadas para que la camara
(camara_caverna_replay.py) las capture en su paso. Modelos: estructura_lista/{skeleton_1,zombie_1,zombie_baby_1,creeper_1}.blend.
Los ciclos de caminar salen de codigos de animacion/: Skeleton y Zombie (recorrido_caminar: piernas 50 deg, rodillas 40 deg, brazos), Zombie bebe
(03_camina_en_diagonal: brazos al frente, piernas rapidas), Creeper (marcha del estudio: 4 patas con los huesos foot.IK*).
Cada criatura camina en linea con deriva aleatoria y giros, sobre el suelo real (raycast), evitando lava y desniveles; el punto donde la camara
la mira (rayo bajo el centro del cuadro en el frame t_cam) esta en su recorrido. Todo animado entre F0 y F1.
Uso en Blender: exec(open(ruta, encoding="utf8").read()); planear(); animar(0) ... animar(6)       (repetible; animar(i) reemplaza la criatura i)
"""
import bpy, math, random, json
from mathutils import Vector, Quaternion

LISTA = r"C:/Users/user/Desktop/Alfred_Animacion/estructura_lista/"
CAMARA = "Camera.001"
COL = "caverna_criaturas"
F0, F1, PASO = 250, 900, 2                  # animacion desde F0 hasta F1, una clave cada PASO frames
SEMILLA = 21
# (tipo, frame en que la camara mira su sitio, angulo bajo el centro del cuadro, velocidad m/s, periodo del ciclo en frames)
CRIATURAS = [
    ("skeleton", 350, 22, 1.5, 20), ("zombie", 385, 20, 1.9, 20), ("zombie_baby", 420, 16, 2.6, 12), ("creeper", 455, 14, 2.0, 20),
    ("skeleton", 490, 14, 1.5, 20), ("zombie", 520, 14, 1.9, 20), ("creeper", 410, 18, 2.0, 20),
    # viaje extra (camara_caverna_replay.TOUR, frames 520-860): vuelta a baja altura que pasa cerca de cada una
    ("skeleton", 580, 20, 1.5, 20), ("zombie", 640, 18, 1.9, 20), ("zombie_baby", 690, 16, 2.6, 12), ("creeper", 740, 16, 2.0, 20),
    ("skeleton", 790, 18, 1.5, 20), ("zombie", 830, 20, 1.9, 20), ("creeper", 610, 22, 2.0, 20),
    # 5 zombies de ojos rojos (brillan), tambien en el viaje extra
    ("zombie_ojos_rojos", 560, 18, 1.9, 20), ("zombie_ojos_rojos", 625, 20, 1.9, 20), ("zombie_ojos_rojos", 670, 18, 1.9, 20),
    ("zombie_ojos_rojos", 735, 20, 1.9, 20), ("zombie_ojos_rojos", 800, 18, 1.9, 20),
]
BLENDS = {"skeleton": "skeleton_1.blend", "zombie": "zombie_1.blend", "zombie_ojos_rojos": "zombie_1.blend", "zombie_baby": "zombie_baby_1.blend", "creeper": "creeper_1.blend"}
FPS = 24
MAX_ESCALON = 1.05                          # desnivel maximo que sube o baja de un paso (m)


_ARB = {}


def _arboles():
    """un BVH (mathutils) por malla de la caverna: el raycast de la escena tarda ~20 ms por rayo (mallas de millones de caras); con el BVH es instantaneo"""
    if _ARB:
        return _ARB
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    for n in ("caverna_stone", "caverna_andesite", "caverna_diorite", "caverna_coal_ore", "caverna_copper_ore", "caverna_lava_lagos"):
        ob = bpy.data.objects[n]
        _ARB[n] = (BVHTree.FromObject(ob, dg), ob.matrix_world.copy(), ob.matrix_world.inverted())
    return _ARB


def _rayo(o, d, dist=400.0):
    """golpe mas cercano de un rayo contra la caverna -> (posicion, nombre) o (None, None)"""
    mejor = (None, None, 1e18)
    for n, (arb, M, Mi) in _arboles().items():
        ol = Mi @ o
        dl = (Mi.to_3x3() @ d).normalized()
        loc, nor, idx, dd = arb.ray_cast(ol, dl, dist)
        if loc is not None:
            pw = M @ loc
            k = (pw - o).length
            if k < mejor[2]:
                mejor = (pw, n, k)
    return mejor[0], mejor[1]


def _piso(sc, dg, x, y, z_ref):
    """altura del suelo en (x, y) cerca de z_ref (primer golpe hacia abajo entre z_ref - 2 y z_ref + 2; None si es lava o no hay)"""
    o = Vector((x, y, min(z_ref + 5.0, 62.0)))
    for _ in range(8):
        pw, n = _rayo(o, Vector((0, 0, -1)), 200.0)
        if pw is None:
            return None
        if abs(pw.z - z_ref) <= 2.0 or z_ref >= 61:
            return None if "lava" in n else pw.z
        o = pw + Vector((0, 0, -0.02))
    return None


def _sim(sc, dg, rng, p0, z0, h0, n, v):
    """camina n pasos de PASO frames desde p0 con rumbo h0 (rad); devuelve [(x, y, z, h)]"""
    x, y, z, h = p0[0], p0[1], z0, h0
    out = []
    for _ in range(n):
        h += rng.gauss(0, 0.10) + (rng.choice((-1, 1)) * rng.uniform(0.6, 1.4) if rng.random() < 0.05 else 0.0)
        for intento in range(16):
            nx, ny = x + math.cos(h) * v * PASO / FPS, y + math.sin(h) * v * PASO / FPS
            nz = _piso(sc, dg, nx, ny, z)
            if nz is not None and abs(nz - z) <= MAX_ESCALON and nz < 14:
                x, y, z = nx, ny, nz
                break
            h += rng.choice((-1, 1)) * rng.uniform(0.5, 1.6)
        out.append((x, y, z, h))
    return out


def _objetivo(sc, dg, cam, f, ang):
    """punto del suelo que la camara mira en el frame f, `ang` grados bajo el centro del cuadro"""
    sc.frame_set(f)
    bpy.context.view_layer.update()
    m = cam.matrix_world
    fwd, right = m.to_quaternion() @ Vector((0, 0, -1)), m.to_quaternion() @ Vector((1, 0, 0))
    for a in (ang, ang - 3, ang + 3, ang - 6, ang + 6):
        d = Quaternion(right, -math.radians(a)) @ fwd
        pos, nom = _rayo(m.translation.copy(), d, 400.0)
        if pos is not None and "lava" not in nom and _piso(sc, dg, pos.x, pos.y, pos.z + 0.1) is not None:
            return pos, Vector((fwd.x, fwd.y, 0)).normalized()
    return None, None


def planear():
    """recorrido de cada criatura (guardado en el texto `plan_criaturas`)"""
    sc = bpy.context.scene
    cam = bpy.data.objects[CAMARA]
    guardado = sc.frame_current
    dg = bpy.context.evaluated_depsgraph_get()
    rng = random.Random(SEMILLA)
    plan = []
    for i, (tipo, t_cam, ang, v, per) in enumerate(CRIATURAS):
        T, fwd = _objetivo(sc, dg, cam, t_cam, ang)
        if T is None:
            plan.append(None)
            continue
        dg = bpy.context.evaluated_depsgraph_get()
        for intento in range(30):
            base = math.atan2(fwd.y, fwd.x) + rng.choice((-1, 1)) * math.pi / 2 + rng.uniform(-0.7, 0.7)       # cruza el cuadro
            n_atras, n_ade = (t_cam - F0) // PASO, (F1 - t_cam) // PASO
            atras = _sim(sc, dg, rng, (T.x, T.y), T.z, base + math.pi, n_atras, v)
            ade = _sim(sc, dg, rng, (T.x, T.y), T.z, base, n_ade, v)
            trayecto = [(x, y, z, h + math.pi) for x, y, z, h in reversed(atras)] + [(T.x, T.y, T.z, base)] + ade
            if len({(round(p[0]), round(p[1])) for p in trayecto}) > len(trayecto) * 0.6:                  # no se queda dando vueltas
                break
        plan.append(dict(tipo=tipo, v=v, per=per, t_cam=t_cam, pts=[[round(c, 3) for c in p] for p in trayecto]))
    sc.frame_set(guardado)
    t = bpy.data.texts.get("plan_criaturas") or bpy.data.texts.new("plan_criaturas")
    t.clear()
    t.write(json.dumps(plan))
    return [(p["tipo"], p["t_cam"], p["pts"][(p["t_cam"] - F0) // PASO][:3]) if p else None for p in plan]


def _traer(tipo, k):
    obj = bpy.data.objects
    with bpy.data.libraries.load(LISTA + BLENDS[tipo], link=False) as (src, dst):
        dst.objects = list(src.objects)
    nuevos = [o for o in dst.objects if o is not None]
    col = bpy.data.collections.get(COL)
    if col is None:
        col = bpy.data.collections.new(COL)
        bpy.context.scene.collection.children.link(col)
    raiz = [o for o in nuevos if o.type == 'EMPTY' and o.parent is None][0]
    familia = {raiz} | set(raiz.children_recursive)
    for o in nuevos:
        if o in familia:
            col.objects.link(o)
        else:
            obj.remove(o, do_unlink=True)                           # objetos sueltos del archivo (cubos / ojos de prueba)
    raiz.name = "%s_cav_%d" % (tipo, k)
    if "ojos_rojos" in tipo:                                        # ojos rojos que brillan: copia del material de cada ojo con emision roja (los demas zombies no cambian)
        for o in familia:
            if o.type == 'MESH' and "ojo" in o.name:
                for sl in o.material_slots:
                    if sl.material is not None:
                        m = sl.material.copy()
                        m.name = "ojos_rojos_%d" % k
                        for n in m.node_tree.nodes:
                            if n.type == 'BSDF_PRINCIPLED':
                                n.inputs["Base Color"].default_value = (1.0, 0.0, 0.0, 1.0)
                                n.inputs["Emission Color"].default_value = (1.0, 0.02, 0.02, 1.0)
                                n.inputs["Emission Strength"].default_value = 15.0
                        sl.material = m
    for o in familia:
        if o.animation_data and o.animation_data.action:
            o.animation_data.action = None
    arm = next(o for o in familia if o.type == 'ARMATURE' and any(b.name.startswith(("LeftUpLeg", "left_leg", "MAIN_creeper")) or "foot.IK" in b.name for b in o.data.bones))
    return raiz, arm, sorted(familia, key=lambda o: o.name)


def _borrar(tipo, k):
    obj = bpy.data.objects
    r = obj.get("%s_cav_%d" % (tipo, k))
    if r is not None:
        for o in list(r.children_recursive):
            obj.remove(o, do_unlink=True)
        obj.remove(r, do_unlink=True)


def _huesos(arm):
    n = {b.name for b in arm.data.bones}
    suf = next((b[len("LeftUpLeg"):] for b in n if b.startswith("LeftUpLeg")), "")
    return n, suf


def _pose(tipo, n, suf, ph):
    """rotaciones (o ubicaciones) de ese instante del ciclo: dict hueso -> ('rot'|'loc', (x, y, z))"""
    tipo = tipo.split("_ojos")[0]
    L, R_ = math.sin(2 * math.pi * ph), math.sin(2 * math.pi * (ph + 0.5))
    d = {}
    if tipo == "zombie":
        # caminata del usuario (`animacion_zombie.py`, estilo NORMAL): piernas 50 deg, rodillas 40 deg, brazos fijos "estilo Minecraft" (Z -90 / +90), columna y cuello casi quietos
        R = math.radians
        sf = math.sin(2 * math.pi * ph + math.pi / 6) * R(0.1)
        st = math.cos(2 * math.pi * ph + math.pi / 3) * R(0.1) * 0.75
        nf, nt, ns_ = -sf * 0.25, math.sin(2 * math.pi * ph) * R(1.5), math.cos(2 * math.pi * ph + math.pi / 4) * R(1.5) * 0.5
        d["Hips" + suf] = ('rot', (0, 0, 0))
        for h in ("Spine", "Spine1", "Spine2"):
            d[h + suf] = ('rot', (sf, 0, st))
        d["face" + suf] = ('rot', (0, 0, 0))
        d["Neck" + suf] = ('rot', (nf, ns_, nt))
        d["LeftUpLeg" + suf] = ('rot', (R(50) * L, 0, 0))
        d["RightUpLeg" + suf] = ('rot', (R(50) * R_, 0, 0))
        d["Leftknee" + suf] = ('rot', (-R(40) * max(0.0, L), 0, 0))
        d["Rightknee" + suf] = ('rot', (-R(40) * max(0.0, R_), 0, 0))
        d["RightUpArm" + suf] = ('rot', (0, 0, -R(90)))
        d["LeftUpArm" + suf] = ('rot', (0, 0, R(90)))
        d["Rightelbow" + suf] = ('rot', (0, 0, 0))
        d["Leftelbow" + suf] = ('rot', (0, 0, 0))
    elif tipo == "skeleton":
        d["LeftUpLeg" + suf] = ('rot', (math.radians(50) * L, 0, 0))
        d["RightUpLeg" + suf] = ('rot', (math.radians(50) * R_, 0, 0))
        d["Leftknee" + suf] = ('rot', (-math.radians(40) * max(0.0, L), 0, 0))
        d["Rightknee" + suf] = ('rot', (-math.radians(40) * max(0.0, R_), 0, 0))
        d["RightUpArm" + suf] = ('rot', (-math.radians(70) * L, 0, -math.radians(90)))        # brazos caidos balanceandose al reves que las piernas
        d["LeftUpArm" + suf] = ('rot', (-math.radians(70) * R_, 0, math.radians(90)))
    elif tipo == "zombie_baby":
        s = "_zombie_baby_1"
        c = math.cos(2 * math.pi * ph)
        d["left_leg" + s] = ('rot', (0.96 * c, 0, 0))
        d["right_leg" + s] = ('rot', (-0.96 * c, 0, 0))
        d["left_arm" + s] = ('rot', (1.48 + 0.1 * c, 0, 0))
        d["right_arm" + s] = ('rot', (1.48 - 0.1 * c, 0, 0))
        d["body" + s] = ('rot', (0.14, 0, 0))
        d["head" + s] = ('rot', (-0.11, 0, 0))
    elif tipo == "creeper":
        for nom, sg in (("foot.IK", 1), ("foot.IK.001", -1), ("foot.IK.002", 1), ("foot.IK.003", -1)):
            d[nom + "_creeper_1"] = ('loc', (0.0, sg * 0.28 * math.sin(2 * math.pi * ph), 0.115 * (0.5 - 0.5 * math.cos(4 * math.pi * ph))))
    return {k: v for k, v in d.items() if k in n}


def animar(i):
    sc = bpy.context.scene
    P = json.loads(bpy.data.texts["plan_criaturas"].as_string())[i]
    if P is None:
        return "sin plan"
    tipo, per, pts = P["tipo"], P["per"], P["pts"]
    _borrar(tipo, i)
    raiz, arm, objs = _traer(tipo, i)
    n, suf = _huesos(arm)
    pb = arm.pose.bones
    for b in pb:
        b.rotation_mode = 'XYZ'
    raiz.rotation_mode = 'XYZ'
    hip_h = 0.02 if tipo == "skeleton" else 0.04
    for k, f in enumerate(range(F0, F1 + 1, PASO)):
        x, y, z, h = pts[min(k, len(pts) - 1)]
        ph = ((f - F0) / per) % 1.0
        raiz.location = (x, y, z + hip_h * abs(math.sin(2 * math.pi * ph)))
        raiz.rotation_euler = (0, 0, h - math.pi / 2)
        raiz.keyframe_insert("location", frame=f)
        raiz.keyframe_insert("rotation_euler", frame=f)
        for nombre, (tp, v) in _pose(tipo, n, suf, ph).items():
            if tp == 'rot':
                pb[nombre].rotation_euler = v
                pb[nombre].keyframe_insert("rotation_euler", frame=f)
            else:
                pb[nombre].location = v
                pb[nombre].keyframe_insert("location", frame=f)
    from bpy_extras import anim_utils                                # rumbos continuos (sin saltos de 2 pi)
    cb = anim_utils.action_get_channelbag_for_slot(raiz.animation_data.action, raiz.animation_data.action_slot)
    for fc in cb.fcurves:
        if fc.data_path == "rotation_euler" and fc.array_index == 2:
            prev = None
            for kp in fc.keyframe_points:
                if prev is not None:
                    while kp.co.y - prev > math.pi:
                        kp.co.y -= 2 * math.pi
                    while kp.co.y - prev < -math.pi:
                        kp.co.y += 2 * math.pi
                    kp.handle_left.y = kp.handle_right.y = kp.co.y
                prev = kp.co.y
            fc.update()
    sc.frame_set(sc.frame_current)
    return dict(i=i, tipo=tipo, raiz=raiz.name, huesos=len(_pose(tipo, n, suf, 0.0)))
