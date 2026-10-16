# -*- coding: utf-8 -*-
"""Parte 11: JERRY (sin armadura) llega NADANDO desde el mar con un pescado en la boca, sale del agua, se SACUDE para
secarse y camina a la fogata a dejar el pescado junto a los otros dos.
- Modelo: estructura_lista/Jerry_sin_armadura.blend (jerry -> Dog_001_rig -> mallas), se anexa en la coleccion
  'jerry_sin_armadura_p11'. El Jerry con armadura (empty 'jerry' de la parte 10) se oculta: ya se quito la armadura.
- Movimientos de huesos: jerry_fuentes/nadar.py (dog paddle), secarse.py (sacudida), caminar_jerry.py (del usuario: 2 bloques en 64 frames, se usa SU velocidad).
  Este script solo pone la ruta del root, las mezclas entre fases y el gesto de soltar el pescado.
- Pescados de MCprep (spawn_item 'cod'), escala Z 0.8 (pedido del usuario), tambien los dos que ya estaban en la fogata.
- No toca la camara ni los ojos de Alfred. Repetible: reanexa nada si ya existe y reescribe su propia animacion."""
import bpy, math, importlib.util, os
from mathutils import Vector, Matrix, Euler

BASE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\parte11"
FUENTES = os.path.join(BASE, "jerry_fuentes")
BLEND = r"C:\Users\user\Desktop\Alfred_Animacion\estructura_lista\Jerry_sin_armadura.blend"
COL = "jerry_sin_armadura_p11"; ROOT = "jerry_sin_armadura"; ARM = "Dog_001_rig"

# ---- mundo (medido): agua desde x=-95 con superficie 7.89 y fondo 7 junto a la orilla; piedra z 8 en x<=-95
Z_NADO = 7.25; Z_SUELO = 8.0                    # lomo a ras del agua (7.89), ojos fuera
RUTA_NADO = [(-87.5, -66.6), (-93.7, -66.6)]                 # recto hacia el oeste, frente a la fogata (linea verde del usuario)
P_SECA = (-95.4, -66.6)                                       # se sacude en el borde de la orilla (patas traseras en x -95.1)
RUTA_CAMINA = [P_SECA, (-96.3, -66.75)]                       # dos pasos hasta la fogata
FOGATA_PEZ = (-97.25, -66.78, 8.51)                           # sobre los troncos (tope 8.455), junto a los otros 2
ESC_PEZ = (0.45, 0.45, 0.8)

GIRA = 26                                                     # despues de soltar el pescado gira hacia Alfred (pasitos)
F_NADO = (1, 160); F_SALTO = (161, 180); F_SECA = (181, 240)
F_SOLTAR = 36; SUELTA = 16; MEZCLA = 8


def _mod(nombre, archivo):
    sp = importlib.util.spec_from_file_location(nombre, os.path.join(FUENTES, archivo))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


def _sstep(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


def _chaikin(pts, n=3):
    for _ in range(n):
        q = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        q.append(pts[-1]); pts = q
    return pts


def _sobre(pts, s):
    """punto y tangente a la distancia s sobre la polilinea"""
    for a, b in zip(pts, pts[1:]):
        d = math.dist(a, b)
        if s <= d or b is pts[-1]:
            f = 0 if d == 0 else min(1, s / d)
            return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), ((b[0] - a[0]) / (d or 1), (b[1] - a[1]) / (d or 1))
        s -= d


def _largo(pts): return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def _yaw(t):  # el perro mira a +Y en reposo
    return math.atan2(-t[0], t[1])


# ---------------------------------------------------------------- 1. escena
def preparar():
    sc = bpy.context.scene
    col = bpy.data.collections.get(COL)
    if col is None:
        col = bpy.data.collections.new(COL); sc.collection.children.link(col)
        with bpy.data.libraries.load(BLEND, link=False) as (src, dst):
            dst.objects = list(src.objects)
        for o in dst.objects:
            if o is None: continue
            col.objects.link(o)
            if o.type == 'EMPTY' and o.parent is None: o.name = ROOT
            if o.type == 'ARMATURE': o.name = ARM
    vieja = bpy.data.objects.get("jerry")                      # el Jerry con armadura de la parte 10
    if vieja:
        for o in [vieja] + list(vieja.children_recursive):
            o.hide_viewport = True; o.hide_render = True
            if o.name.startswith(("ojo_", "pupila_", "sejas_")) and o.name.endswith("_jerry"): o.name = o.name + "_con_armadura"
    for o in bpy.data.objects[ARM].children:                   # ojos/pupilas/cejas del Jerry nuevo: nombres sin '.001' (los busca el eye_system)
        if "_jerry." in o.name: o.name = o.name.split(".")[0]
    return bpy.data.objects[ROOT], bpy.data.objects[ARM]


def _pez(nombre):
    o = bpy.data.objects.get(nombre)
    if o: return o
    sc = bpy.context.scene; L = [i.name for i in sc.mcprep_props.item_list]
    if not L: bpy.ops.mcprep.reload_items(); L = [i.name for i in sc.mcprep_props.item_list]
    sc.mcprep_props.item_list_index = L.index("cod")
    antes = set(bpy.data.objects); bpy.ops.mcprep.spawn_item()
    o = [x for x in bpy.data.objects if x not in antes][0]; o.name = nombre
    for c in list(o.users_collection): c.objects.unlink(o)
    bpy.data.collections["fogata_pescados"].objects.link(o)
    return o


# ---------------------------------------------------------------- 2. poses por fase
def construir():
    nadar = _mod("p11_nadar", "nadar.py"); secar = _mod("p11_secarse", "secarse.py"); cam = _mod("p11_caminar", "caminar_jerry.py")
    sc = bpy.context.scene; root, arm = preparar()
    huesos = [pb.name for pb in arm.pose.bones]
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'; pb.location = (0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
    for ob in (root, arm):
        if ob.animation_data: ob.animation_data_clear()
    root.location = (0, 0, 0); root.rotation_euler = (0, 0, 0); bpy.context.view_layer.update()

    # pescado en la boca: cruzado entre las mandibulas, hijo del hueso scull
    mallas = [o for o in arm.children if o.type == 'MESH' and o.name.split('.')[0] in ("boca superior", "boca imferior")]
    vs = [o.matrix_world @ v.co for o in mallas for v in o.data.vertices]
    frente = max(v.y for v in vs); zb = (min(v.z for v in vs) + max(v.z for v in vs)) / 2
    boca = _pez("pescado_boca_jerry"); boca.parent = None
    boca.matrix_world = Matrix.LocRotScale(Vector((0, frente - 0.1, zb)), Euler((math.pi / 2, 0, math.radians(25))), Vector(ESC_PEZ))
    mw = boca.matrix_world.copy(); boca.parent = arm; boca.parent_type = 'BONE'; boca.parent_bone = "scull"
    bpy.context.view_layer.update(); boca.matrix_world = mw
    fuego = _pez("pescado_fogata_jerry"); fuego.parent = None
    fuego.location = FOGATA_PEZ; fuego.rotation_euler = (0.05, -0.04, math.radians(95)); fuego.scale = ESC_PEZ
    for n in ("pescado_cod", "pescado_salmon"):                # los dos que ya se cocinan: escala Z 0.8 y apoyados
        o = bpy.data.objects.get(n)
        if o: o.scale = ESC_PEZ; o.location.z = 8.455 + 0.0625 * 0.8 / 2 + 0.002

    # ruta del root
    nado = _chaikin(RUTA_NADO); camina = _chaikin(RUTA_CAMINA)
    pts = cam.EMBEDDED_TRAJECTORY_POINTS; vel = math.dist(*[(q['coordinates']['x'], q['coordinates']['y']) for q in pts]) / cam.TOTAL_FRAMES
    n_cam = int(round(_largo(camina) / vel)) + 6                      # velocidad del archivo de caminata (0.031 m/frame)
    F_CAM = (F_SECA[1] + 1, F_SECA[1] + n_cam); F_SUELTA = (F_CAM[1] + 1, F_CAM[1] + F_SOLTAR)
    F_GIRA = (F_SUELTA[1] + 1, F_SUELTA[1] + GIRA)
    FIN = max(sc.frame_end, F_GIRA[1] + 60)
    walk = cam.generate_keyframes(n_cam); paso = cam.generate_keyframes(GIRA); shake = secar.build_bone_functions('')
    alf = bpy.data.objects["alfred"].matrix_world.translation; fin_c = RUTA_CAMINA[-1]
    YAW_ALFRED = math.atan2(-(alf.x - fin_c[0]), alf.y - fin_c[1])         # mirar a Alfred
    YAW_ALFRED = math.pi / 2 + ((YAW_ALFRED - math.pi / 2 + math.pi) % (2 * math.pi) - math.pi)   # giro mas corto desde -X

    def pose_fase(t):
        if t <= F_NADO[1]: return 0, {b: f(t - F_NADO[0] + 1) for b, f in nadar.BONE_FUNCTIONS.items()}
        if t <= F_SALTO[1]:
            u = (t - F_SALTO[0]) / (F_SALTO[1] - F_SALTO[0]); s = math.sin(math.pi * u)
            return 1, {"front_shoulder.L": (-0.5 * s, 0, 0), "front_shoulder.R": (-0.5 * s, 0, 0),
                       "shoulder.L": (0.4 * s, 0, 0), "shoulder.R": (0.4 * s, 0, 0), "tail_1": (0.3 * s, 0, 0)}
        if t <= F_SECA[1]: return 2, {b: f(t - F_SECA[0] + 1) for b, f in shake.items()}
        if t <= F_CAM[1]: return 3, {b: v[t - F_CAM[0] + 1] for b, v in walk.items()}
        if t <= F_SUELTA[1]:
            k = t - F_SUELTA[0]; h = _sstep(k / 12) * (1 - _sstep((k - 20) / 14)); ab = math.exp(-((k - SUELTA) / 4.0) ** 2)
            return 4, {"spine_1": (0.25 * h, 0, 0), "spine_2": (0.15 * h, 0, 0), "scull": (0.45 * h, 0, 0),
                       "jaw_bot": (-0.35 * ab, 0, 0), "tail_1": (0.2, 0.2 * math.sin(k / 3), 0)}
        if t <= F_GIRA[1]:                                        # gira en el sitio con pasitos y la cabeza adelantada
            k = t - F_GIRA[0] + 1; u = k / GIRA; lado = 1 if YAW_ALFRED > math.pi / 2 else -1
            pz = {b: tuple(c * (0.6 if ("shoulder" in b or "thigh" in b or "shin" in b or "foot" in b or "toe" in b) else 1.0) for c in v[k]) for b, v in paso.items()}
            pz["scull"] = (pz.get("scull", (0, 0, 0))[0], 0.35 * lado * math.sin(math.pi * u), 0)
            return 5, pz
        k = t - F_GIRA[1]                                         # espera junto a la fogata mirando a Alfred
        return 6, {"tail_1": (0.25, 0.25 * math.sin(k / 4), 0), "tail_2": (0, 0.15 * math.sin(k / 4 - 0.6), 0),
                   "spine_4": (0.015 * math.sin(k / 18), 0, 0), "ear.L": (0, 0.05 * math.sin(k / 30), 0),
                   "ear.R": (0, 0.05 * math.sin(k / 30 + 1), 0)}

    inicio = {0: F_NADO[0], 1: F_SALTO[0], 2: F_SECA[0], 3: F_CAM[0], 4: F_SUELTA[0], 5: F_GIRA[0], 6: F_GIRA[1] + 1}
    rot = {b: [] for b in huesos}; loc = []; yaws = []; yaw_f = None; fase_prev = 0; prev_pose = {}; ultima_fija = {}
    for t in range(1, FIN + 1):
        fase, p = pose_fase(t)
        if fase != fase_prev: ultima_fija = dict(prev_pose); fase_prev = fase   # mezcla desde la ultima pose de la fase anterior
        w = 1.0 if fase == 0 else _sstep((t - inicio[fase] + 1) / MEZCLA)
        if w < 1.0:
            p = {b: tuple(a * (1 - w) + c * w for a, c in zip(ultima_fija.get(b, (0, 0, 0)), p.get(b, (0, 0, 0)))) for b in huesos}
        prev_pose = p
        for b in huesos: rot[b].append(p.get(b, (0, 0, 0)))
        # root
        if fase == 0:
            u = (t - 1) / (F_NADO[1] - 1); s = _largo(nado) * (u - 0.12 * math.sin(math.pi * u) * u)
            (x, y), tg = _sobre(nado, s); z = Z_NADO + 0.03 * math.sin(2 * math.pi * t / 20); obj = _yaw(tg)
        elif fase == 1:
            u = (t - F_SALTO[0] + 1) / (F_SALTO[1] - F_SALTO[0] + 1); a = RUTA_NADO[-1]
            x = a[0] + (P_SECA[0] - a[0]) * _sstep(u); y = a[1] + (P_SECA[1] - a[1]) * _sstep(u)
            z = Z_NADO + (Z_SUELO - Z_NADO) * min(1, 2.2 * u) ** 0.5 + 0.4 * math.sin(math.pi * u); obj = yaw_f
        elif fase == 2: x, y = P_SECA; z = Z_SUELO; obj = yaw_f
        elif fase == 3:
            u = (t - F_CAM[0]) / (F_CAM[1] - F_CAM[0]); s = _largo(camina) * (u * u * (3 - 2 * u) * 0.25 + u * 0.75)
            (x, y), tg = _sobre(camina, s); z = Z_SUELO; obj = _yaw(tg)
        elif fase == 4: x, y = RUTA_CAMINA[-1]; z = Z_SUELO; obj = math.pi / 2  # mirando a la fogata (-X)
        else: x, y = RUTA_CAMINA[-1]; z = Z_SUELO; obj = None
        if fase == 5:
            if t == F_GIRA[0]: yaw_ini = yaw_f
            yaw_f = yaw_ini + (YAW_ALFRED - yaw_ini) * _sstep((t - F_GIRA[0] + 1) / GIRA)
        elif fase == 6: yaw_f = YAW_ALFRED
        else:
            if yaw_f is None: yaw_f = obj
            d = (obj - yaw_f + math.pi) % (2 * math.pi) - math.pi; yaw_f += d * (0.12 if fase >= 3 else 0.3)
        loc.append((x, y, z)); yaws.append(yaw_f)

    # claves densas (rapidas): una por frame
    def curvas(ob, datos):
        viejo = bpy.data.actions.get(ob.name + "_p11")                 # repetible sin dejar copias huerfanas (lag)
        if viejo: bpy.data.actions.remove(viejo)
        ob.animation_data_create(); act = bpy.data.actions.new(ob.name + "_p11"); ob.animation_data.action = act
        for path, idx, vals in datos:
            fc = act.fcurve_ensure_for_datablock(ob, path, index=idx); fc.keyframe_points.add(len(vals))
            co = [c for i, v in enumerate(vals) for c in (i + 1, v)]; fc.keyframe_points.foreach_set("co", co)
            fc.keyframe_points.foreach_set("interpolation", [1] * len(vals)); fc.update()   # LINEAR
    curvas(arm, [('pose.bones["%s"].rotation_euler' % b, i, [r[i] for r in rot[b]]) for b in huesos for i in range(3)])
    curvas(root, [("location", i, [l[i] for l in loc]) for i in range(3)] + [("rotation_euler", 2, yaws)])

    # en tierra: la sacudida/caminata baja las patas unos cm -> se sube el root lo que se hunda (medido en la malla)
    fz = next(fc for fc in root.animation_data.action.layers[0].strips[0].channelbags[0].fcurves if fc.data_path == "location" and fc.array_index == 2)
    ms = [o for o in arm.children if o.type == 'MESH' and not o.name.startswith("pescado")]
    for t in range(F_SECA[0], FIN + 1):
        sc.frame_set(t); dg = bpy.context.evaluated_depsgraph_get(); lo = 99
        for o in ms:
            e = o.evaluated_get(dg); m = e.to_mesh(); mw = o.matrix_world
            lo = min(lo, min((mw @ v.co).z for v in m.vertices)); e.to_mesh_clear()
        if lo < Z_SUELO: fz.keyframe_points[t - 1].co.y += Z_SUELO - lo
    fz.update()

    # el pescado cambia de la boca a la fogata al soltarlo
    D = F_SUELTA[0] + SUELTA
    for o, oculto_antes in ((boca, False), (fuego, True)):
        if o.animation_data:
            if o.animation_data.action: bpy.data.actions.remove(o.animation_data.action)
            o.animation_data_clear()
        for f, h in ((1, oculto_antes), (D, not oculto_antes)):
            o.hide_viewport = h; o.hide_render = h
            o.keyframe_insert("hide_viewport", frame=f); o.keyframe_insert("hide_render", frame=f)
    bpy.context.scene.frame_set(D - 1); m_boca = boca.matrix_world.copy()   # cae desde la boca hasta los troncos en 5 frames
    fuego.matrix_world = Matrix.LocRotScale(m_boca.translation, m_boca.to_quaternion(), Vector(ESC_PEZ))
    fuego.keyframe_insert("location", frame=D); fuego.keyframe_insert("rotation_euler", frame=D)
    fuego.location = FOGATA_PEZ; fuego.rotation_euler = (0.05, -0.04, math.radians(95))
    fuego.keyframe_insert("location", frame=D + 5); fuego.keyframe_insert("rotation_euler", frame=D + 5)
    bpy.context.scene.frame_set(1)
    sc.frame_end = FIN
    sc["p11_jerry"] = {"nado": F_NADO, "salto": F_SALTO, "seca": F_SECA, "camina": F_CAM, "suelta": F_SUELTA, "pez_fogata": D, "gira": F_GIRA, "mira_alfred": F_GIRA[1] + 1}
    print("JERRY P11:", dict(sc["p11_jerry"]), "fin", FIN)
    return dict(sc["p11_jerry"])


if __name__ in ("__main__", "x"):
    construir()
