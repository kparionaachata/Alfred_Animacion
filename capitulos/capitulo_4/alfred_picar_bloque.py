# -*- coding: utf-8 -*-
"""Alfred pica un bloque con el pico de piedra: animacion reutilizable e INDEPENDIENTE (no necesita otros guiones del proyecto).

Parte de la pose `preparado para picar` (manos delante, pico a la altura de la cintura, incluida en POSE_PREPARADO), levanta el pico delante y lo clava
en el bloque que tiene enfrente; el cuerpo retrocede un poco tras cada impacto y vuelve a la pose de partida. Un golpe cada `periodo` frames.
Todo se hornea por frame (24 fps): raiz del personaje, los 14 huesos del cuerpo y el pico (el pico se importa de PICO_BLEND si no existe).
El solucionador de poses (direcciones de huesos en el marco del personaje, IK de brazos) esta copiado de `alfred_cae_estalagmita.py`.

Uso rapido en Blender (escena con el rig `Armature` / empty `alfred`):
    exec(open(ruta, encoding="utf8").read())
    picar_bloque(punto=(-98.5, -41.5, -18.0), yaw_deg=-90, pared_dist=0.38, alto_golpe=0.95, f_ini=1, f_fin=261)
Con otro Alfred: picar_bloque(armature="Armature_carbon", raiz="alfred_carbon", pico="stone_pickaxe_carbon", ...).
Pasos sueltos: configurar(...); info, datos, rot = construir(); hornear(info, datos, rot); sonorizar()
Parametros (CFG): punto, yaw_deg (0 = mira +Y, -90 = +X, 90 = -X, 180 = -Y), pared_dist, alto_golpe, beta_golpe_deg, f_ini, f_fin, periodo, primer_golpe.
"""
import bpy, math
from mathutils import Vector, Matrix, Quaternion, Euler

ARM = "Armature"                           # lo fija construir() segun CFG["armature"]
L_BRAZO, L_ANTEBRAZO = 0.392, 0.37        # largo util del brazo: hueso del hombro y parte del antebrazo que cubre la malla
PUNTA_D, PUNTA_E = 0.263, 0.239            # de la mano a la punta del pico: a lo largo del mango y a lo largo de la cabeza
PICO_BLEND = "C:/Users/user/Desktop/Alfred_Animacion/objetos/vanilla/stone_pickaxe/stone_pickaxe.blend"

# ============================================================================================================
#  SOLUCIONADOR DE POSES (copiado de alfred_cae_estalagmita.py)
# ============================================================================================================
D = math.radians


ORDEN = ["Hips_alfred", "Spine_alfred", "Spine1_alfred", "Spine2_alfred", "Neck_alfred", "face_alfred",
         "RightUpArm_alfred", "Rightelbow_alfred", "LeftUpArm_alfred", "Leftelbow_alfred",
         "RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred"]


def norm(v):
    v = Vector(v)
    return v.normalized() if v.length > 1e-9 else Vector((0, 0, 1))


class Rig:
    """resuelve una pose a partir de la direccion (marco del personaje) del eje Y de cada hueso"""
    def __init__(self):
        self.arm = bpy.data.objects[ARM]
        self.pb = self.arm.pose.bones
        self.rest = {b.name: b.matrix_local.copy() for b in self.arm.data.bones}
        self.largo = {b.name: b.length for b in self.arm.data.bones}
        self.padre = {b.name: (b.parent.name if b.parent else None) for b in self.arm.data.bones}

    def resolver(self, dirs, giros=None, aplicar=True):
        """dirs: nombre -> direccion (3) del eje del hueso; giros: nombre -> torsion (rad) sobre su eje.
        Devuelve (poses_armature, colas) con la matriz de cada hueso y la posicion de su cola en el marco del personaje."""
        giros = giros or {}
        pose = {}
        colas = {}
        for n in ORDEN:
            rest = self.rest[n]
            p = self.padre[n]
            if p is None:
                P = rest.copy()
            else:
                P = pose[p] @ self.rest[p].inverted() @ rest
            d = norm(dirs[n]) if n in dirs else None
            if d is None:
                R = P.to_3x3()
            else:
                rest_y = rest.to_3x3() @ Vector((0, 1, 0))
                sw = rest_y.rotation_difference(d).to_matrix()
                R = sw @ rest.to_3x3()
            tw = giros.get(n, 0.0)
            if tw:
                R = R @ Matrix.Rotation(tw, 3, 'Y')
            T = P.translation
            M = Matrix.LocRotScale(T, R.to_quaternion(), None)
            pose[n] = M
            colas[n] = M @ Vector((0, self.largo[n], 0))
            if aplicar:
                basis = P.inverted() @ M
                self.pb[n].rotation_mode = 'XYZ'
                self.pb[n].rotation_euler = basis.to_euler('XYZ')
                self.pb[n].location = (0, 0, 0)
        return pose, colas

    def hips(self):
        return self.rest["Hips_alfred"].translation.copy()


def suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def vlerp(a, b, t):
    return Vector(a) * (1 - t) + Vector(b) * t


SUELO_PIE = 0.105                          # la suela esta 0.105 por encima de la cola del hueso de la rodilla


def ik_brazo(S, T, polo, l1=L_BRAZO, l2=L_ANTEBRAZO):
    """dos huesos: devuelve (dir_brazo, dir_antebrazo, mano_real)"""
    S, T = Vector(S), Vector(T)
    v = T - S
    d = min(v.length, l1 + l2 - 1e-4)
    d = max(d, abs(l1 - l2) + 1e-4)
    u = v.normalized() if v.length > 1e-9 else Vector((0, 0, -1))
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = math.sqrt(max(0.0, l1 * l1 - a * a))
    pp = Vector(polo) - Vector(polo).dot(u) * u
    pp = pp.normalized() if pp.length > 1e-6 else Vector((1, 0, 0))
    E = S + u * a + pp * h
    mano = S + u * d
    return (E - S).normalized(), (mano - E).normalized(), mano


def pose_torso(theta, cabeza=0.0, lado=0.0):
    """tronco inclinado hacia delante theta (rad) repartido en la columna; cabeza: pitch extra; lado: torsion lateral"""
    def d(a, x=0.0):
        return (x, math.sin(a), math.cos(a))
    return {"Hips_alfred": d(0.12 * theta), "Spine_alfred": d(0.35 * theta, 0.15 * lado), "Spine1_alfred": d(0.62 * theta, 0.3 * lado),
            "Spine2_alfred": d(0.88 * theta, 0.45 * lado), "Neck_alfred": d(theta + cabeza * 0.6, 0.5 * lado),
            "face_alfred": d(theta + cabeza, 0.5 * lado)}


def piernas(sep=0.05, cad=0.20, rod=-0.22):
    """piernas con las rodillas un poco flexionadas (cad: la cadera adelanta el muslo, rod: la rodilla lo devuelve)"""
    return {"RightUpLeg_alfred": (sep, cad, -1.0), "Rightknee_alfred": (0.0, rod, -1.0),
            "LeftUpLeg_alfred": (-sep, cad, -1.0), "Leftknee_alfred": (0.0, rod, -1.0)}


def resolver_con_brazos(rig, dirs, mano_d=None, mano_i=None, polo_d=(1, -0.6, 0), polo_i=(-1, -0.6, 0), giros=None, aplicar=True):
    """primero el tronco (para saber donde estan los hombros), despues IK de los dos brazos"""
    base = dict(dirs)
    for n in ("RightUpArm_alfred", "Rightelbow_alfred", "LeftUpArm_alfred", "Leftelbow_alfred"):
        base.setdefault(n, rig.rest[n].to_3x3() @ Vector((0, 1, 0)))
    pose, _ = rig.resolver(base, giros, aplicar=False)
    info = {}
    if mano_d is not None:
        S = pose["RightUpArm_alfred"].translation
        a, f, real = ik_brazo(S, mano_d, polo_d)
        base["RightUpArm_alfred"], base["Rightelbow_alfred"] = a, f
        info["mano_d"] = real
    if mano_i is not None:
        S = pose["LeftUpArm_alfred"].translation
        a, f, real = ik_brazo(S, mano_i, polo_i)
        base["LeftUpArm_alfred"], base["Leftelbow_alfred"] = a, f
        info["mano_i"] = real
    pose, colas = rig.resolver(base, giros, aplicar=aplicar)
    info["dirs"] = base
    return pose, colas, info


PICO_EJE = Vector((0.7071, 0.7071, 0.0))        # direccion del mango en la malla del pico de piedra (hacia la cabeza)


PICO_AGARRE = PICO_EJE * -0.35 + Vector((-0.7071, 0.7071, 0.0)) * -0.045   # punto del mango (local) que va a la mano


def aplicar_estado(rig, st):
    dirs = pose_torso(st["th"], st["cab"], st["lado"])
    dirs.update(piernas(st["sep"], st["cad"], st["rod"]))
    d = norm(st["d"])
    G = Vector(st["Gd"])
    Gi = Vector(st["Gi"]) if st.get("Gi") is not None else G - d * 0.22
    pose, colas, info = resolver_con_brazos(rig, dirs, G, Gi)
    return pose, colas, info, d


def matriz_pico(G, d):
    d = norm(d)
    lado = Vector((1, 0, 0)) if abs(d.x) < 0.9 else Vector((0, 1, 0))
    e = norm(d.cross(lado))
    R = base_item(PICO_EJE, d, d.cross(e))
    return Matrix.LocRotScale(Vector(G) - R @ (0.6 * PICO_AGARRE), R.to_quaternion(), Vector((0.6, 0.6, 0.6)))


def base_item(eje, d, n):
    """rotacion de una malla plana (XY): su mango (eje local) -> d, su cara plana (Z local) -> n"""
    d, n = norm(d), norm(n)
    w = n.cross(d)
    a = norm(eje)
    b = Vector((-a.y, a.x, 0))
    L = Matrix(((a.x, b.x, 0), (a.y, b.y, 0), (0, 0, 1)))
    Cw = Matrix(((d.x, w.x, n.x), (d.y, w.y, n.y), (d.z, w.z, n.z)))
    return Cw @ L.transposed()


# ============================================================================================================
#  POSE DE PARTIDA "preparado para picar" (eulers XYZ en radianes de cada hueso; viene de `preparado para picar.json`)
# ============================================================================================================
POSE_PREPARADO = {
    "Hips_alfred": (0.014246, 0.000043, -0.005972),
    "Spine_alfred": (0.179593, -0.002182, 0.01972),
    "Spine1_alfred": (0.039055, 0.001921, -0.02057),
    "Spine2_alfred": (0.0227, -0.000575, 0.006579),
    "Neck_alfred": (0.183966, 0.001152, -0.005028),
    "face_alfred": (0.068747, -0.004335, 0.017866),
    "RightUpArm_alfred": (0.888759, 0.365178, -0.237265),
    "Rightelbow_alfred": (0.733492, -0.152321, -1.897002),
    "LeftUpArm_alfred": (1.350422, -0.48432, 0.303346),
    "Leftelbow_alfred": (0.794884, 0.361136, 1.256212),
    "RightUpLeg_alfred": (0.037257, 0.004353, -0.120716),
    "Rightknee_alfred": (-0.16643, -0.042019, 0.151361),
    "LeftUpLeg_alfred": (0.037746, -0.000544, 0.064013),
    "Leftknee_alfred": (-0.146552, 0.020281, -0.050828),
}

# ============================================================================================================
#  PARAMETROS (cambialos con configurar(...) o pasando un dict a picar_bloque)
# ============================================================================================================
CFG = dict(
    armature="Armature",             # armature del Alfred que pica
    raiz="alfred",                   # empty raiz de ese Alfred
    pico="stone_pickaxe",            # objeto del pico (si no existe se importa de PICO_BLEND)
    punto=(-98.5, -41.5, -18.0),     # donde esta parado (z = suelo bajo sus pies)
    yaw_deg=-90.0,                   # hacia donde mira: 0 = +Y, -90 = +X, 90 = -X, 180 = -Y
    pared_dist=0.38,                 # de su posicion a la cara del bloque (en la direccion en que mira)
    alto_golpe=0.95,                 # altura del impacto sobre el suelo
    beta_golpe_deg=70.0,             # inclinacion del mango al impactar: la punta apunta al bloque
    f_ini=1, f_fin=261,              # frames que se hornean
    periodo=22,                      # frames entre golpes
    primer_golpe=None,               # frame del primer golpe (por defecto f_ini + periodo - 1)
    raiz_fija=None,                  # (x, y, z): el empty raiz NO se mueve; el hueso Hips lleva el desplazamiento (None = el empty se mueve)
)
SONIDO = "block.stone.break"         # evento del add-on Alfred Sonidos en cada golpe
ADDON_SONIDOS = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py"


def configurar(**kw):
    for k, v in kw.items():
        if k not in CFG:
            raise KeyError("parametro desconocido: " + k)
        CFG[k] = v
    return CFG


def golpes():
    p = CFG["primer_golpe"] or (CFG["f_ini"] + CFG["periodo"] - 1)
    return list(range(p, CFG["f_fin"] + 1, CFG["periodo"]))


def _arm():
    return bpy.data.objects[CFG["armature"]]


def fase_c(f, G):
    """posicion en el ciclo: 0 = preparado (pose del json), 1 = pico levantado delante, 2 = impacto contra el bloque"""
    r = CFG["periodo"] - 1
    for g in G:
        t = f - (g - r)
        if not 0 <= t <= r:
            continue
        if t < 4:
            return 0.0 if g == G[0] else 2.0 * (1.0 - suave(t / 4.0))      # tras el impacto vuelve a la posicion de partida
        if t < r - 13:
            return 0.0
        if t < r - 8:
            return suave((t - (r - 13)) / 5.0)                              # levanta el pico
        if t < r - 4:
            return 1.0
        u = (t - (r - 4)) / 4.0
        return 1.0 + u * u                                                  # golpe
    if f > G[-1]:
        return 2.0 * (1.0 - suave((f - G[-1]) / 4.0))
    return 0.0


def construir():
    """calcula el movimiento (sin tocar las llaves): devuelve (info, datos, rot); datos = [(frame, loc_raiz, {hueso: euler}, matriz_pico)]"""
    global ARM
    ARM = CFG["armature"]
    G = golpes()
    rig = Rig()
    pb = rig.pb
    punto = Vector(CFG["punto"])
    beta = math.radians(CFG["beta_golpe_deg"])
    json_eul = {n: Euler(e, 'XYZ') for n, e in POSE_PREPARADO.items()}
    json_q = {n: json_eul[n].to_quaternion() for n in ORDEN}
    guardada = {n: (pb[n].rotation_mode, pb[n].rotation_euler.copy(), pb[n].location.copy()) for n in ORDEN}

    def mano(lado):
        """punto de agarre (ultimo tramo util del antebrazo) en el marco del armature"""
        e = pb[lado + "elbow_alfred"]
        return Vector(e.head) + (Vector(e.tail) - Vector(e.head)).normalized() * L_ANTEBRAZO

    for n in ORDEN:
        pb[n].rotation_mode = 'XYZ'
        pb[n].rotation_euler = json_eul[n]
        pb[n].location = (0, 0, 0)
    bpy.context.view_layer.update()
    Gd0, Gi0 = mano("Right"), mano("Left")                               # donde tiene las manos en la pose de partida
    d0 = norm(Gd0 - Gi0)

    def estado_golpe():
        th, tg = 0.20, 0.30
        dirs = pose_torso(th, cabeza=0.12)
        dirs.update(piernas(0.06, tg, -tg))
        _, colas, _ = resolver_con_brazos(rig, dirs, aplicar=False)
        piso = min(colas["Rightknee_alfred"].z, colas["Leftknee_alfred"].z) + SUELO_PIE
        yf = (colas["Rightknee_alfred"].y + colas["Leftknee_alfred"].y) / 2
        d = Vector((0, math.sin(beta), math.cos(beta)))
        e = Vector((0, math.cos(beta), -math.sin(beta)))
        Gh = Vector((0, yf + CFG["pared_dist"] - 0.02, piso + CFG["alto_golpe"])) - d * PUNTA_D - e * PUNTA_E
        return dict(th=th, cab=0.12, lado=0.0, sep=0.06, cad=tg, rod=-tg, Gd=Gh, Gi=Gh - d * 0.22, d=d)

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

    rot = Quaternion((0, 0, 1), math.radians(CFG["yaw_deg"]))
    datos = []
    previo = {n: json_eul[n] for n in ORDEN}
    for f in range(CFG["f_ini"], CFG["f_fin"] + 1):
        c = fase_c(f, G)
        st = estado(c)
        kg = min([f - g for g in G if f > g] or [99])
        if 1 <= kg < 10:                                                  # el pico rebota y el cuerpo retrocede
            r = math.exp(-(kg - 1) / 2.5) * math.cos(0.9 * (kg - 1))
            st["th"] -= 0.08 * r
            st["Gd"] = Vector(st["Gd"]) + Vector((0, -0.03 * r, 0.06 * r))
        aplicar_estado(rig, st)
        w = min(1.0, c * 3.0)
        w = w * w * (3 - 2 * w)                                           # 0 = pose exacta del json
        eul = {}
        for n in ORDEN:
            qik = Euler(pb[n].rotation_euler, 'XYZ').to_quaternion()
            eul[n] = json_q[n].slerp(qik, w).to_euler('XYZ', previo[n])
            pb[n].rotation_euler = eul[n]
        bpy.context.view_layer.update()
        previo = eul
        rk, lk = Vector(pb["Rightknee_alfred"].tail), Vector(pb["Leftknee_alfred"].tail)
        piso = min(rk.z, lk.z) + SUELO_PIE
        yf = (rk.y + lk.y) / 2
        loc = Vector((punto.x, punto.y, 0.0)) - rot @ Vector((0, yf, 0)) + Vector((0, 0, punto.z - piso))
        M = Matrix.Translation(loc) @ rot.to_matrix().to_4x4() @ matriz_pico(mano("Right"), norm(st["d"]))
        datos.append((f, loc, {n: tuple(e) for n, e in eul.items()}, M))
    for n, (modo, e, l) in guardada.items():                              # deja el rig como estaba
        pb[n].rotation_mode = modo
        pb[n].rotation_euler = e
        pb[n].location = l
    bpy.context.view_layer.update()
    return dict(f_ini=CFG["f_ini"], f_fin=CFG["f_fin"], golpes=G), datos, rot


def asegurar_pico():
    obj = bpy.data.objects
    if CFG["pico"] in obj:
        return obj[CFG["pico"]]
    with bpy.data.libraries.load(PICO_BLEND, link=False) as (src, dst):
        dst.objects = ["stone_pickaxe"]
    nuevo = dst.objects[0]
    nuevo.name = CFG["pico"]
    nuevo.scale = (0.6, 0.6, 0.6)
    bpy.context.scene.collection.objects.link(nuevo)
    return nuevo


def hornear(info=None, datos=None, rot=None):
    """inserta las llaves: raiz, 14 huesos y pico"""
    if info is None:
        info, datos, rot = construir()
    obj = bpy.data.objects
    raiz, ar, pico = obj[CFG["raiz"]], _arm(), asegurar_pico()
    pico.hide_viewport = pico.hide_render = False
    raiz.rotation_mode = 'QUATERNION'
    pico.rotation_mode = 'QUATERNION'
    fija = Vector(CFG["raiz_fija"]) if CFG["raiz_fija"] else None
    if fija:
        r_hips = ar.data.bones["Hips_alfred"].matrix_local.to_3x3()
    for f, loc, eul, M in datos:
        raiz.location = fija if fija else loc
        raiz.rotation_quaternion = rot
        raiz.keyframe_insert("location", frame=f)
        raiz.keyframe_insert("rotation_quaternion", frame=f)
        for n, e in eul.items():
            ar.pose.bones[n].rotation_mode = 'XYZ'
            ar.pose.bones[n].rotation_euler = e
            ar.pose.bones[n].keyframe_insert("rotation_euler", frame=f)
        if fija:                                                          # el cuerpo se desplaza con el Hips (marco del armature = marco del personaje)
            ar.pose.bones["Hips_alfred"].location = r_hips.inverted() @ (rot.inverted() @ (loc - fija))
            ar.pose.bones["Hips_alfred"].keyframe_insert("location", frame=f)
        l, q, s = M.decompose()
        pico.location, pico.rotation_quaternion, pico.scale = l, q, s
        pico.keyframe_insert("location", frame=f)
        pico.keyframe_insert("rotation_quaternion", frame=f)
        pico.keyframe_insert("scale", frame=f)
    raiz["f_golpes"] = ",".join(str(g) for g in info["golpes"])
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    return info


def sonorizar(vol=0.5):
    """un golpe del add-on Alfred Sonidos (evento SONIDO) en cada impacto; tiras con origen 'picar_bloque'"""
    import importlib.util, sys
    m = sys.modules.get("alfred_sonidos_local")
    if m is None:
        spec = importlib.util.spec_from_file_location("alfred_sonidos_local", ADDON_SONIDOS)
        m = importlib.util.module_from_spec(spec)
        sys.modules["alfred_sonidos_local"] = m
        spec.loader.exec_module(m)
        m.register()
    sc = bpy.context.scene
    p = sc.mcsnd
    m.indice(p, forzar=True)
    ed = sc.sequence_editor or sc.sequence_editor_create()
    for t in [t for t in m._strips(ed) if t.name.startswith(m.PREFIJO) and t.get("mcsnd_origen") == "picar_bloque"]:
        m._strips(ed).remove(t)
    rng = m.rng_de(p)
    rutas = m.rutas_de(p, SONIDO)
    n = 0
    for g in golpes():
        t = m.colocar(bpy.context, p, rutas, g, "golpes", SONIDO.replace(".", "_"), vol * (0.85 + 0.3 * rng.random()), 0, rng)
        if t:
            t["mcsnd_origen"] = "picar_bloque"
            n += 1
    return n


def picar_bloque(sonido=True, **parametros):
    """todo en uno: configurar(**parametros) + hornear() (+ sonorizar())"""
    configurar(**parametros)
    info = hornear()
    if sonido:
        info["sonidos"] = sonorizar()
    return info
