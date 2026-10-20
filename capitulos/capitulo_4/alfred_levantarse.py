# -*- coding: utf-8 -*-
"""Alfred se pone de pie despues de caer al suelo, con la animacion de levantarse (Mixamo) del usuario: `animacion_alfred (23).py` (slot_001_levantarse_3, 183 frames, 14 huesos).
Continua desde donde queda tras la caida (boca abajo, cabeza hacia -Y, frame 242):
  F_HOLD .. F_INI-1   se mezcla de la pose en el suelo a la pose inicial de la animacion (9 frames)
  F_INI .. F_INI+182  la animacion del usuario (su cuadro 1 cae en F_INI = 370)
El archivo del usuario solo trae rotaciones: el empty `alfred` se orienta una vez (rotacion Z 180: la cabeza apunta a -Y como al caer) y NO se mueve ni gira en ningun frame (siempre en -44.635, -13.547, -9.5): el desplazamiento del cuerpo lo hace el hueso Hips (ver construir).
Uso en Blender: exec(open(ruta).read()); datos = construir(); hornear(datos)
"""
import bpy, math
from mathutils import Vector, Quaternion

ANIM = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\animacion_alfred_levantarse_3.py"
ANIM_ORIGEN = r"C:\Users\user\Downloads\animacion_alfred (23).py"
F_INI = 370                        # frame en que empieza a ponerse de pie (cuadro 1 de la animacion)
F_MEZCLA = 9                       # frames de transicion desde la pose del suelo
F_HOLD = F_INI - F_MEZCLA          # ultimo frame con la pose de la caida
BLOQUE = "bloque_diorite_-45_-15_-10"         # el bloque diorita de la celda (-45, -15) cuya cara de arriba esta en z = -9 (no existe uno con k = -9 en la escena)
ROOT, ARM = "alfred", "Armature"
MALLAS = ["Mesh_%d_alfred" % i for i in range(6)]
ORDEN = ["Hips_alfred", "Spine_alfred", "Spine1_alfred", "Spine2_alfred", "Neck_alfred", "face_alfred", "RightUpArm_alfred", "Rightelbow_alfred",
         "LeftUpArm_alfred", "Leftelbow_alfred", "RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred"]


def cargar_animacion():
    import os, shutil
    ruta = ANIM if os.path.isfile(ANIM) else ANIM_ORIGEN
    if not os.path.isfile(ANIM) and os.path.isfile(ANIM_ORIGEN):
        shutil.copyfile(ANIM_ORIGEN, ANIM)                            # copia a la carpeta del proyecto para no depender de Descargas
    ns = {"__name__": "levantarse"}
    exec(open(ruta, encoding="utf8").read(), ns)
    return ns["KEYFRAME_DATA"]


def suelo_z(x, y):
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    o = Vector((x, y, -4.0))                                                          # bajo el techo de la cueva
    for _ in range(8):
        ok, pos, nor, idx, ob, mw = sc.ray_cast(dg, o, Vector((0, 0, -1)), distance=40)
        if not ok:
            return None
        if ob.name.startswith("bloque_"):
            return pos.z
        o = pos + Vector((0, 0, -0.01))
    return None


def minimo_malla(dg):
    zs = []
    for n in MALLAS:
        ob = bpy.data.objects[n].evaluated_get(dg)
        me = ob.to_mesh()
        zs.append(min((ob.matrix_world @ v.co).z for v in me.vertices))
        ob.to_mesh_clear()
    return min(zs)


def construir(suavizado=2):
    """El empty `alfred` NO se mueve ni gira en ningun frame (location y rotacion = las de la caida). El desplazamiento del cuerpo se hace con el hueso Hips:
    se calcula la transformacion 'virtual' que tendria el empty para esa animacion (cabeza a -Y, cadera en el mismo punto donde estaba tendido y el cuerpo apoyado en el suelo)
    y se traduce a location + rotation_euler del hueso Hips: basis = (root @ rest)^-1 @ T_virtual @ rest @ basis_anim. Los demas huesos llevan los valores de la animacion."""
    from mathutils import Matrix, Euler
    sc = bpy.context.scene
    obj = bpy.data.objects
    root, arm = obj[ROOT], obj[ARM]
    KD = cargar_animacion()
    n_anim = len(KD["Hips_alfred"])
    pb = arm.pose.bones
    sc.frame_set(242)
    bpy.context.view_layer.update()
    loc0, q0 = Vector(root.location), Quaternion(root.rotation_quaternion)
    eul_held = {n: tuple(pb[n].rotation_euler) for n in ORDEN}
    hips_held = Vector(pb["Hips_alfred"].location)
    Mroot = Matrix.LocRotScale(loc0, q0, None)
    rest = arm.data.bones["Hips_alfred"].matrix_local.copy()
    Mi = (Mroot @ rest).inverted()
    qz = Quaternion((0, 0, 1), math.pi)                                              # cabeza hacia -Y
    hips_world_held = (Mroot @ (rest @ Matrix.LocRotScale(hips_held, Euler(eul_held["Hips_alfred"], 'XYZ').to_quaternion(), None))).translation
    # 1) alturas: con el empty "virtual" en (x, y) = cadera tendida, el punto mas bajo del cuerpo sobre el suelo
    xy = (hips_world_held - qz @ rest.translation).to_2d()
    suelo = suelo_z(xy.x, xy.y)
    suelo = -9.0 if suelo is None else suelo
    root.rotation_mode = 'QUATERNION'
    bajos = []
    for k in range(1, n_anim + 1):
        root.rotation_quaternion = qz
        root.location = (xy.x, xy.y, 0.0)
        for n in ORDEN:
            pb[n].rotation_mode = 'XYZ'
            pb[n].rotation_euler = KD[n][k]
        pb["Hips_alfred"].location = (0, 0, 0)
        bpy.context.view_layer.update()
        bajos.append(minimo_malla(bpy.context.evaluated_depsgraph_get()))
    zs = [suelo - m for m in bajos]
    suav = []
    for i in range(len(zs)):
        a_, b_ = max(0, i - suavizado), min(len(zs), i + suavizado + 1)
        suav.append(sum(zs[a_:b_]) / (b_ - a_))
    # restaura el rig tal como estaba
    root.location, root.rotation_quaternion = loc0, q0
    for n in ORDEN:
        pb[n].rotation_euler = eul_held[n]
    pb["Hips_alfred"].location = hips_held
    bpy.context.view_layer.update()

    def basis_hips(Tv, rot_q, loc):
        """pose del Hips que reproduce, con el empty fijo, la transformacion virtual Tv del empty y la pose (rot_q, loc) del Hips"""
        return Mi @ Tv @ rest @ Matrix.LocRotScale(loc, rot_q, None)

    datos = []
    previo = Euler(eul_held["Hips_alfred"], 'XYZ')

    def agrega(f, Tv, eul, hips_q, hips_loc):
        nonlocal previo
        B = basis_hips(Tv, hips_q, hips_loc)
        l, q, _ = B.decompose()
        e = q.to_euler('XYZ', previo)
        previo = e
        eul = dict(eul)
        eul["Hips_alfred"] = tuple(e)
        datos.append((f, eul, tuple(l)))
    p1 = Vector((xy.x, xy.y, suav[0]))
    Tv1 = Matrix.LocRotScale(p1, qz, None)
    # 2) mezcla desde la pose de la caida (empty virtual = el real) hasta el cuadro 1
    qh0 = Euler(eul_held["Hips_alfred"], 'XYZ').to_quaternion()
    qa1 = Euler(KD["Hips_alfred"][1], 'XYZ').to_quaternion()
    for i in range(F_MEZCLA + 1):
        f = F_HOLD + i
        u = i / F_MEZCLA
        u = u * u * (3 - 2 * u)
        qv = q0.slerp(qz if q0.dot(qz) >= 0 else -qz, u)
        Tv = Matrix.LocRotScale(loc0.lerp(p1, u), qv, None)
        eul = {n: tuple(a + (b - a) * u for a, b in zip(eul_held[n], KD[n][1])) for n in ORDEN}
        agrega(f, Tv, eul, qh0.slerp(qa1, u), hips_held * (1 - u))
    # 3) la animacion del usuario
    for k in range(2, n_anim + 1):
        Tv = Matrix.LocRotScale(Vector((xy.x, xy.y, suav[k - 1])), qz, None)
        agrega(F_INI + k - 1, Tv, {n: KD[n][k] for n in ORDEN}, Euler(KD["Hips_alfred"][k], 'XYZ').to_quaternion(), Vector((0, 0, 0)))
    info = dict(f_hold=F_HOLD, f_ini=F_INI, f_fin=datos[-1][0], suelo=suelo, virtual_xy=(round(xy.x, 3), round(xy.y, 3)), empty=tuple(loc0))
    return info, datos


def hornear(info, datos):
    sc = bpy.context.scene
    obj = bpy.data.objects
    root, arm = obj[ROOT], obj[ARM]
    pb = arm.pose.bones
    root.rotation_mode = 'QUATERNION'
    loc0, q0 = Vector(info["empty"]), Quaternion(root.rotation_quaternion)
    for f in (F_HOLD, datos[-1][0]):                                              # el empty se queda quieto: llaves iguales a las de la caida
        root.location = loc0
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_quaternion", frame=f)
    for f, eul, hl in datos:
        for n, e in eul.items():
            pb[n].rotation_mode = 'XYZ'
            pb[n].rotation_euler = e
            pb[n].keyframe_insert("rotation_euler", frame=f)
        pb["Hips_alfred"].location = hl
        pb["Hips_alfred"].keyframe_insert("location", frame=f)
    root["f_levanta"] = info["f_ini"]
    sc.frame_set(sc.frame_current)
    return info
