# -*- coding: utf-8 -*-
"""alfred_cueva_5E.blend: mientras Jerry se va con el pico, Alfred (sentado en la punta de la plataforma) se pone de pie, retrocede un paso hacia el tunel, saca la mesa de crafteo de la espalda, la coloca,
pone dos palos y un bloque de cobblestone y craftea un PICO DE PIEDRA que se lleva a la espalda. Referencia: "Alfred saca la mesa de crafteo y craftea la pala.py" (alfred_craftea_payload.json: 134 frames);
en la referencia Alfred esta ARRODILLADO; aqui esta DE PIE: los objetos (mesa, palos, cobblestone, pala->pico) siguen la misma trayectoria respecto a su raiz y las manos llegan a los mismos puntos
(IK de los brazos, con el tronco inclinado lo justo para alcanzar; piernas rectas). La pala se sustituye por una copia del pico de piedra (jerry_pico).
Fases: F_LEVANTA..F_CRAFT = sentado -> agachado con las manos en las rodillas -> de pie; F_CRAFT..F_CRAFT+133 = la animacion de crafteo.
Uso: exec(open(ruta, encoding="utf8").read()); datos = preparar(); construir(datos)"""
import bpy, math, json, os
from mathutils import Vector, Matrix, Euler

BASE = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/"
PAYLOAD = BASE + "alfred_craftea_payload.json"
OBJ_DIR = "C:/Users/user/Desktop/Alfred_Animacion/codigos de animacion/alfred/"
F_LEVANTA, F_AGACHA, F_PARA = 150, 22, 30
F_CRAFT = F_LEVANTA + F_AGACHA + F_PARA
SUELO = 66.0                                        # cara superior de los bloques de la plataforma
POS_CRAFT = (0.5, 85.0)                             # donde se para (dentro del tunel, de espaldas a el), mirando a la caverna (-Y)
RZ_CRAFT = math.pi
ALCANCE = 0.392 + 0.37
PICO = "jerry_pico"
PICO_CRAFT = "pico_craft"
LADOS = (("R", "RightUpArm_alfred", "Rightelbow_alfred"), ("L", "LeftUpArm_alfred", "Leftelbow_alfred"))


def suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _cargar_toolkit():
    ns = {"__name__": "b"}
    exec(open(BASE + "alfred_cae_estalagmita.py", encoding="utf8").read(), ns)
    return ns


def _fk_euler(rig, eul, loc):
    """matrices (marco del armature) de los huesos para unos eulers/ubicaciones dados"""
    cache = {}

    def pm(n):
        if n in cache:
            return cache[n]
        b = Matrix.Translation(Vector(loc.get(n, (0, 0, 0)))) @ Euler(eul[n], 'XYZ').to_matrix().to_4x4()
        p = rig.padre[n]
        cache[n] = (pm(p) @ (rig.rest[p].inverted() @ rig.rest[n]) @ b) if p else rig.rest[n] @ b
        return cache[n]
    return {n: pm(n) for n in rig.rest}


def _manos_ref(rig, P, i):
    eul = {n: ch["rotation_euler"][i] for n, ch in P["bones"].items()}
    for n in rig.rest:
        eul.setdefault(n, (0, 0, 0))
    loc = {n: c["location"] for n, c in P["constantes"].items() if "location" in c}
    M = _fk_euler(rig, eul, loc)
    return {l: M[e] @ Vector((0, 0.37, 0)) for l, _, e in LADOS}


def _zmin_alfred():
    """altura minima (mundo) de la malla de Alfred con la pose actual"""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    z = 9e9
    for k in range(6):
        o = bpy.data.objects["Mesh_%d_alfred" % k]
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        z = min(z, min((o.matrix_world @ v.co).z for v in me.vertices))
        bpy.data.meshes.remove(me)
    return z


def preparar():
    """calcula (sin escribir claves) el tronco inclinado y las poses de pie de cada frame del crafteo; mide la altura de la raiz para que las suelas queden sobre SUELO"""
    B = _cargar_toolkit()
    P = json.load(open(PAYLOAD))
    O = bpy.data.objects
    sc = bpy.context.scene
    arm, emp = O["Armature"], O["alfred"]
    rig = B["Rig"]()
    F = P["info"]["frames"]
    # objetivos de las manos (marco del armature de la referencia) y inclinacion minima del tronco para alcanzarlos
    manos = [_manos_ref(rig, P, i) for i in range(F)]
    pierna = B["piernas"](0.10, 0.08, -0.08)

    def resolver(th, cab, Gd, Gi, aplicar=False):
        dirs = B["pose_torso"](th, cab, 0.0)
        dirs.update(pierna)
        return B["resolver_con_brazos"](rig, dirs, Gd, Gi, aplicar=aplicar)

    def error(th, Gd, Gi):
        pose, colas, info = resolver(th, -0.5 * th, Gd, Gi)
        e = [(info["mano_d"] - Gd).length if Gd.z > 0.6 else 0.0, (info["mano_i"] - Gi).length if Gi.z > 0.6 else 0.0]      # la mano que cuelga junto al cuerpo (objetivo bajo) no obliga a inclinar el tronco: el brazo cae hasta donde llega
        return max(e)

    # el hombro esta mas alto que en la referencia (de rodillas): la mano baja delta z; se mide con la raiz a la altura SUELO + delta (aqui delta = 0 y luego se corrige)
    # 1) pose de pie con el tronco recto para medir delta (suela sobre el suelo)
    pose, colas, info = resolver(0.05, -0.02, Vector((0.24, 0.06, 0.82)), Vector((-0.24, 0.06, 0.82)), aplicar=True)
    for n in ("Hips_alfred",):
        arm.pose.bones[n].location = (0, 0, 0)
    emp.location = Vector((POS_CRAFT[0], POS_CRAFT[1], SUELO))
    emp.rotation_euler = (0, 0, RZ_CRAFT)
    z0 = _zmin_alfred()
    delta = SUELO - z0                              # cuanto hay que subir la raiz para que la suela toque el suelo (+) o bajarla (-)
    # 2) por frame: menor inclinacion que alcanza las dos manos (en el marco de la raiz, la mano baja delta)
    ths = []
    for i in range(F):
        Gd = manos[i]["R"] - Vector((0, 0, delta))
        Gi = manos[i]["L"] - Vector((0, 0, delta))
        th = 0.05
        while th < 1.0 and error(th, Gd, Gi) > 0.012:
            th += 0.03
        ths.append(th)
    # suavizado (gaussiana) para que el tronco no tiemble
    sm = []
    for i in range(F):
        a = t = 0.0
        for k in range(-6, 7):
            w = math.exp(-0.5 * (k / 3.0) ** 2)
            a += w * ths[min(F - 1, max(0, i + k))]
            t += w
        sm.append(max(a / t, ths[i] * 0.0))
    # el tronco nunca menos inclinado de lo que hace falta
    sm = [max(sm[i], ths[i] if i in () else 0.0) for i in range(F)]
    poses = []
    maxerr = 0.0
    for i in range(F):
        Gd = manos[i]["R"] - Vector((0, 0, delta))
        Gi = manos[i]["L"] - Vector((0, 0, delta))
        th = max(sm[i], 0.05)
        pose, colas, info = resolver(th, -0.5 * th, Gd, Gi, aplicar=True)
        maxerr = max(maxerr, (info["mano_d"] - Gd).length if Gd.z > 0.6 else 0.0, (info["mano_i"] - Gi).length if Gi.z > 0.6 else 0.0)
        eul = {n: tuple(arm.pose.bones[n].rotation_euler) for n in B["ORDEN"]}
        poses.append(eul)
    return {"B": B, "P": P, "rig": rig, "poses": poses, "delta": delta, "z_raiz": SUELO + delta, "th": sm, "err_max": round(maxerr, 3)}


def _asegurar_objetos(P):
    O = bpy.data.objects
    sc = bpy.context.scene
    for nombre, rec in P["objetos"].items():
        if nombre in O or nombre == "stone_shovel":
            continue
        ruta = OBJ_DIR + rec["archivo"]
        faltan = [n for n in rec["paquete"] if n not in O]
        with bpy.data.libraries.load(ruta, link=False) as (src, dst):
            dst.objects = [n for n in faltan if n in src.objects]
        for o in dst.objects:
            if o is None:
                continue
            if o.name in P["objetos"] or (o.parent is not None and o.parent.name in P["objetos"]):
                sc.collection.objects.link(o)
            else:
                bpy.data.objects.remove(o)
    # el pico que se craftea (copia del pico de piedra de Jerry) ocupa el lugar de la pala
    if PICO_CRAFT not in O:
        src = O[PICO]
        o = bpy.data.objects.new(PICO_CRAFT, src.data)
        sc.collection.objects.link(o)
        o.rotation_mode = 'QUATERNION'


def construir(datos):
    B, P, rig, poses = datos["B"], datos["P"], datos["rig"], datos["poses"]
    O = bpy.data.objects
    sc = bpy.context.scene
    arm, emp = O["Armature"], O["alfred"]
    pb = arm.pose.bones
    F = P["info"]["frames"]
    ORDEN = B["ORDEN"]
    _asegurar_objetos(P)
    for ob in (arm, emp):
        if ob.animation_data:
            ob.animation_data_clear()
    # --- estado sentado actual (inicio) y posiciones
    P0 = {n: tuple(pb[n].rotation_euler) for n in ORDEN}
    H0 = tuple(pb["Hips_alfred"].location)
    R0 = emp.location.copy()
    rz0 = emp.rotation_euler[2]
    z_raiz = datos["z_raiz"]
    R2 = Vector((POS_CRAFT[0], POS_CRAFT[1], z_raiz))
    # --- pose agachada (manos en las rodillas)
    arm_tmp = rig
    dirs = B["pose_torso"](0.85, -0.35, 0.0)
    dirs.update(B["piernas"](0.12, 1.25, -0.55))
    B["resolver_con_brazos"](rig, dirs, Vector((0.16, 0.42, 0.62)), Vector((-0.16, 0.42, 0.62)), polo_d=(1, -0.4, -0.3), polo_i=(-1, -0.4, -0.3), aplicar=True)
    P1 = {n: tuple(pb[n].rotation_euler) for n in ORDEN}
    pb["Hips_alfred"].location = (0, 0, 0)
    emp.location = R0.lerp(R2, 0.4)
    emp.rotation_euler = (0, 0, rz0 + (RZ_CRAFT - rz0) * 0.4)
    z1 = _zmin_alfred()
    R1 = emp.location.copy()
    R1.z += SUELO - z1
    P2 = poses[0]
    mezcla = lambda a, b, w: {n: tuple(x + (y - x) * w for x, y in zip(a[n], b[n])) for n in a}
    # --- de sentado a de pie
    f_fin_levanta = F_CRAFT - 1
    for f in range(F_LEVANTA, F_CRAFT):
        t = f - F_LEVANTA
        if t <= F_AGACHA:
            w = suave(t / float(F_AGACHA))
            Pz = mezcla(P0, P1, w)
            R = R0.lerp(R1, w)
            R.z += 0.06 * math.sin(math.pi * w)
            hip = tuple(a * (1 - w) for a in H0)
        else:
            w = suave((t - F_AGACHA) / float(F_PARA))
            Pz = mezcla(P1, P2, w)
            R = R1.lerp(R2, w)
            hip = (0, 0, 0)
        rz = rz0 + (RZ_CRAFT - rz0) * (0.4 * suave(min(1.0, t / float(F_AGACHA))) + 0.6 * (suave((t - F_AGACHA) / float(F_PARA)) if t > F_AGACHA else 0.0))
        for n, e in Pz.items():
            pb[n].rotation_euler = e
            pb[n].keyframe_insert("rotation_euler", frame=f)
        pb["Hips_alfred"].location = hip
        pb["Hips_alfred"].keyframe_insert("location", frame=f)
        emp.location = R
        emp.rotation_euler = (0, 0, rz)
        emp.keyframe_insert("location", frame=f)
        emp.keyframe_insert("rotation_euler", frame=f)
    # antes de levantarse: quieto sentado
    # --- crafteo de pie
    mat = lambda l, e: Matrix.LocRotScale(Vector(l), Euler(e, 'XYZ').to_quaternion(), Vector((1, 1, 1)))
    R0r = mat(P["root"]["location"][0], P["root"]["rotation_euler"][0])
    Wxy = Matrix.Translation((POS_CRAFT[0], POS_CRAFT[1], 14.0)) @ Matrix.Rotation(RZ_CRAFT, 4, 'Z')
    T = Matrix.Translation((0, 0, SUELO - 14.0)) @ Wxy @ R0r.inverted()
    pb["Hips_alfred"].location = (0, 0, 0)
    prev = Euler((0, 0, RZ_CRAFT), 'XYZ')
    for i in range(F):
        f = F_CRAFT + i
        for n, e in poses[i].items():
            pb[n].rotation_euler = e
            pb[n].keyframe_insert("rotation_euler", frame=f)
        pb["Hips_alfred"].location = (0, 0, 0)
        pb["Hips_alfred"].keyframe_insert("location", frame=f)
        M = T @ mat(P["root"]["location"][i], P["root"]["rotation_euler"][i])
        loc, q, _s = M.decompose()
        eul = q.to_euler('XYZ', prev)
        prev = eul
        loc.z = z_raiz
        emp.location = loc
        emp.rotation_euler = eul
        emp.keyframe_insert("location", frame=f)
        emp.keyframe_insert("rotation_euler", frame=f)
    # --- objetos (mesa, palos, cobblestone, pala->pico): mundo relativo a la raiz de la referencia
    for name, rec in P["objetos"].items():
        ob = O[PICO_CRAFT if name == "stone_shovel" else name]
        for o_ in (ob,):
            if o_.animation_data:
                o_.animation_data_clear()
            if o_.parent is not None:
                m0 = o_.matrix_world.copy()
                o_.parent = None
                o_.matrix_world = m0
        ob.rotation_mode = 'QUATERNION'
        qprev = None
        for i in range(F):
            f = F_CRAFT + i
            from mathutils import Quaternion
            Mo = T @ Matrix.LocRotScale(Vector(rec["location"][i]), Quaternion(rec["rotation_quaternion"][i]), Vector(rec["scale"][i]))
            l, q, s = Mo.decompose()
            if qprev is not None and q.dot(qprev) < 0:
                q = -q
            qprev = q
            ob.location, ob.rotation_quaternion, ob.scale = l, q, s
            for ch in ("location", "rotation_quaternion", "scale"):
                ob.keyframe_insert(ch, frame=f)
            hv, hr = rec["hide"][i]
            ob.hide_viewport, ob.hide_render = hv, hr
            ob.keyframe_insert("hide_viewport", frame=f)
            ob.keyframe_insert("hide_render", frame=f)
        # antes de empezar: oculto (todavia no existe)
        ob.scale = (0, 0, 0)
        ob.keyframe_insert("scale", frame=max(1, F_CRAFT - 1))
        ob.keyframe_insert("scale", frame=1)
        for fc in _fcurves(ob):
            for k in fc.keyframe_points:
                k.interpolation = 'CONSTANT' if fc.data_path.startswith("hide") else 'LINEAR'
    for fc in _fcurves(arm) + _fcurves(emp):
        for k in fc.keyframe_points:
            k.interpolation = 'LINEAR'
    sc.frame_end = max(sc.frame_end, F_CRAFT + F - 1)
    sc.frame_set(1)
    return {"levanta": (F_LEVANTA, F_CRAFT - 1), "craftea": (F_CRAFT, F_CRAFT + F - 1)}


def _fcurves(ob):
    ad = ob.animation_data
    if not ad or not ad.action:
        return []
    return [fc for l in ad.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]
