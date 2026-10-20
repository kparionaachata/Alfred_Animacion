# -*- coding: utf-8 -*-
"""Alfred, ya de pie (frame 552, alfred_levantarse.py), se agacha y planta una antorcha en (-44.5, -15.5, -9.0) con la animacion del usuario `animacion_alfred (24).py`
(slot_001_colocar_antorcha, 30 frames, 14 huesos). El empty `alfred` no se mueve: igual que al levantarse, el Hips lleva la transformacion 'virtual' del cuerpo.
  F_FIN_PIE+1 .. +F_MEZCLA   mezcla de la pose de pie a la pose inicial del slot
  F_ANIM .. F_ANIM+29        el slot (su cuadro 1 cae en F_ANIM); la antorcha aparece en el cuadro 16 del slot
Jerry espera (DEMORA_RUTA en jerry_baja_agua.py) y llega a su ultimo punto despues de F_ANIM+29.
Uso en Blender: exec(open(ruta).read()); info = hornear()
"""
import bpy, math, os, shutil
from mathutils import Vector, Quaternion, Matrix, Euler

CARPETA = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4"
ANIM = CARPETA + r"\animacion_alfred_colocar_antorcha.py"
ANIM_ORIGEN = r"C:\Users\user\Downloads\animacion_alfred (24).py"
LEVANTARSE = CARPETA + r"\alfred_levantarse.py"
ANTORCHA_BLEND = r"C:\Users\user\Desktop\Alfred_Animacion\bloques_dinamicos\antorcha_1.blend"
DESTINO = Vector((-44.5, -15.5, -9.0))              # cara de arriba del bloque de piedra
F_FIN_PIE = 552
F_MEZCLA = 6
F_ANIM = F_FIN_PIE + F_MEZCLA                       # cuadro 1 del slot
F_APARECE = F_ANIM + 15                             # TORCH_APPEAR_FRAME = 16 del slot
N_ANIM = 30
ROOT, ARM = "alfred", "Armature"
COLECCION_LUZ = "luz_entrada_receptores"


def _cargar(ruta):
    ns = {"__name__": "x"}
    exec(open(ruta, encoding="utf8").read(), ns)
    return ns


def datos_anim():
    if not os.path.isfile(ANIM) and os.path.isfile(ANIM_ORIGEN):
        shutil.copyfile(ANIM_ORIGEN, ANIM)
    return _cargar(ANIM)["KEYFRAME_DATA"]


def construir():
    L = _cargar(LEVANTARSE)
    ORDEN = L["ORDEN"]
    KD = datos_anim()
    KL = L["cargar_animacion"]()
    n_l = len(KL["Hips_alfred"])
    obj = bpy.data.objects
    root, arm = obj[ROOT], obj[ARM]
    pb = arm.pose.bones
    sc = bpy.context.scene
    sc.frame_set(F_FIN_PIE)
    bpy.context.view_layer.update()
    loc0, q0 = Vector(root.location), Quaternion(root.rotation_quaternion)
    Mroot = Matrix.LocRotScale(loc0, q0, None)
    rest = arm.data.bones["Hips_alfred"].matrix_local.copy()
    Mi = (Mroot @ rest).inverted()
    qz = Quaternion((0, 0, 1), math.pi)
    # cuerpo virtual: mismo punto y orientacion con que termina de levantarse
    eul_fin = {n: tuple(pb[n].rotation_euler) for n in ORDEN}
    hips_fin = Vector(pb["Hips_alfred"].location)
    B = Matrix.LocRotScale(hips_fin, Euler(eul_fin["Hips_alfred"], 'XYZ').to_quaternion(), None)
    xy = (Mroot @ (rest @ B)).translation.to_2d() - (qz @ rest.translation).to_2d()
    suelo = L["suelo_z"](xy.x, xy.y)
    suelo = -9.0 if suelo is None else suelo
    saved = ({n: tuple(pb[n].rotation_euler) for n in ORDEN}, Vector(pb["Hips_alfred"].location))
    root.rotation_mode = 'QUATERNION'
    bajos = []
    pb_set = lambda E: [setattr(pb[n], "rotation_euler", E[n]) for n in ORDEN]
    for E in [{n: KL[n][n_l] for n in ORDEN}] + [{n: KD[n][k] for n in ORDEN} for k in range(1, N_ANIM + 1)]:
        root.rotation_quaternion = qz
        root.location = (xy.x, xy.y, 0.0)
        for n in ORDEN:
            pb[n].rotation_mode = 'XYZ'
        pb_set(E)
        pb["Hips_alfred"].location = (0, 0, 0)
        bpy.context.view_layer.update()
        bajos.append(L["minimo_malla"](bpy.context.evaluated_depsgraph_get()))
    zs = [suelo - m for m in bajos]
    suav = [sum(zs[max(0, i - 2):i + 3]) / len(zs[max(0, i - 2):i + 3]) for i in range(len(zs))]
    root.location, root.rotation_quaternion = loc0, q0
    for n in ORDEN:
        pb[n].rotation_euler = saved[0][n]
    pb["Hips_alfred"].location = saved[1]
    bpy.context.view_layer.update()

    datos = []
    previo = Euler(eul_fin["Hips_alfred"], 'XYZ')

    def agrega(f, z, eul, hips_q):
        nonlocal previo
        Tv = Matrix.LocRotScale(Vector((xy.x, xy.y, z)), qz, None)
        M = Mi @ Tv @ rest @ Matrix.LocRotScale(Vector((0, 0, 0)), hips_q, None)
        l, q, _ = M.decompose()
        e = q.to_euler('XYZ', previo)
        previo = e
        eul = dict(eul)
        eul["Hips_alfred"] = tuple(e)
        datos.append((f, eul, tuple(l)))
    # mezcla de la pose de pie a la inicial del slot
    qa = Euler(KL["Hips_alfred"][n_l], 'XYZ').to_quaternion()
    qb = Euler(KD["Hips_alfred"][1], 'XYZ').to_quaternion()
    for i in range(1, F_MEZCLA):
        u = i / F_MEZCLA
        u = u * u * (3 - 2 * u)
        eul = {n: tuple(a + (b - a) * u for a, b in zip(KL[n][n_l], KD[n][1])) for n in ORDEN}
        agrega(F_FIN_PIE + i, suav[0] + (suav[1] - suav[0]) * u, eul, qa.slerp(qb, u))
    for k in range(1, N_ANIM + 1):
        agrega(F_ANIM + k - 1, suav[k], {n: KD[n][k] for n in ORDEN}, Euler(KD["Hips_alfred"][k], 'XYZ').to_quaternion())
    return dict(f_ini=F_FIN_PIE + 1, f_anim=F_ANIM, f_aparece=F_APARECE, f_fin=F_ANIM + N_ANIM - 1, virtual_xy=(round(xy.x, 3), round(xy.y, 3))), datos


def poner_antorcha():
    obj = bpy.data.objects
    for o in [o for o in obj if o.name.startswith("antorcha_1") and o.get("colocada_alfred")]:
        for c in list(o.children_recursive):
            obj.remove(c, do_unlink=True)
        obj.remove(o, do_unlink=True)
    with bpy.data.libraries.load(ANTORCHA_BLEND, link=False) as (src, dst):
        dst.objects = list(src.objects)
    raiz = [o for o in dst.objects if o.type == 'EMPTY' and o.parent is None][0]
    col = bpy.context.scene.collection
    usados = [raiz] + list(raiz.children_recursive)
    for o in dst.objects:
        if o in usados:
            col.objects.link(o)
        else:
            obj.remove(o, do_unlink=True)                                   # humo/llama sueltos que no cuelgan de la antorcha
    raiz.name = "antorcha_1_colocada"
    raiz["colocada_alfred"] = True
    raiz.location = DESTINO
    bpy.context.view_layer.update()
    zmin = min((o.matrix_world @ Vector(c)).z for o in usados if o.type == 'MESH' for c in o.bound_box)
    raiz.location.z += DESTINO.z - zmin                                     # la base queda sobre la cara de arriba del bloque
    rec = bpy.data.collections.get(COLECCION_LUZ)
    if rec:
        for o in usados:
            if o.name not in rec.objects:
                rec.objects.link(o)
    for o in usados:                                                        # oculta hasta el cuadro en que Alfred la suelta
        for prop in ("hide_viewport", "hide_render"):
            setattr(o, prop, True)
            o.keyframe_insert(prop, frame=F_APARECE - 1)
            setattr(o, prop, False)
            o.keyframe_insert(prop, frame=F_APARECE)
        o.hide_viewport = o.hide_render = False
    return raiz.name


def hornear(info=None, datos=None):
    if info is None:
        info, datos = construir()
    sc = bpy.context.scene
    arm = bpy.data.objects[ARM]
    pb = arm.pose.bones
    for f, eul, hl in datos:
        for n, e in eul.items():
            pb[n].rotation_mode = 'XYZ'
            pb[n].rotation_euler = e
            pb[n].keyframe_insert("rotation_euler", frame=f)
        pb["Hips_alfred"].location = hl
        pb["Hips_alfred"].keyframe_insert("location", frame=f)
    info["antorcha"] = poner_antorcha()
    bpy.data.objects[ROOT]["f_antorcha"] = info["f_aparece"]
    bpy.data.objects[ROOT]["f_antorcha_fin"] = info["f_fin"]
    sc.frame_set(sc.frame_current)
    return info
