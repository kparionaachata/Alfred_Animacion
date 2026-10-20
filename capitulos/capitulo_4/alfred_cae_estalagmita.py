# -*- coding: utf-8 -*-
"""Alfred pica hacia abajo en la oscuridad, rompe el bloque del techo y cae de espaldas sobre la estalagmita.

Escena: alfred_cueva_2.blend (cueva de bloques del capitulo 4). Todo se hornea por frame (24 fps):
  1 .. F_ROMPE        Alfred, de pie sobre el bloque del techo (fondo del pozo), pica hacia abajo (4 golpes). A oscuras:
                      `luz_entrada_cueva` apagada.
  F_ROMPE             se rompe el bloque (desaparece, saltan trocitos) y la luz de entrada se enciende de golpe (rampa corta).
  F_ROMPE+1 .. F_IMP  cae por el pozo (caida libre, g = 9.8) girando hasta quedar boca arriba.
  F_IMP .. F_IMP+60   queda de espaldas sobre la punta de la estalagmita 60 frames, quejandose del dolor.
Uso (en Blender): exec(open(ruta).read());  construir()  /  construir(solo_prueba=True)
La pose se calcula con direcciones de huesos en el marco del personaje (x = derecha, y = frente, z = arriba), sin IK.
"""
import bpy, math, random
from mathutils import Vector, Matrix, Quaternion, Euler

D = math.radians
ARM, ROOT = "Armature", "alfred"
ESTALAGMITA = "estalagmita_punta_-53_-10_-7"
G = 9.8
FPS = 24
GOLPES = [10, 26, 42, 58]             # frame de cada golpe del pico (el ultimo rompe el bloque)
F_ROMPE = GOLPES[-1]
F_QUEJA = 60                          # frames que se queda quejandose
Z_BLOQUE_TOPE = -1.0                  # cara superior del bloque del techo (celda k=-2)
CENTRO = (-45.5, -14.5)               # centro del pozo
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


def reposo():
    r = Rig()
    r.resolver({n: r.rest[n].to_3x3() @ Vector((0, 1, 0)) for n in ORDEN})
    return r


# ============================================================================================================
#  UTILIDADES
# ============================================================================================================
def suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def vlerp(a, b, t):
    return Vector(a) * (1 - t) + Vector(b) * t


L_BRAZO, L_ANTEBRAZO = 0.392, 0.37        # largo util del brazo: hueso del hombro y parte del antebrazo que cubre la malla
SUELO_PIE = 0.105                          # la suela esta 0.105 por encima de la cola del hueso de la rodilla
HIPS_Y_ESPALDA = 0.041 + 0.14              # distancia de la cadera al plano de la espalda (el torso llega a y = -0.14)
LARGO_PICO = 0.65                          # mango del pico (0.6 de escala)


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


def suela_min(rig, colas):
    return min(colas["Rightknee_alfred"].z, colas["Leftknee_alfred"].z) + SUELO_PIE


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


# ============================================================================================================
#  ESTADOS DE POSE   (todo en el marco del personaje / armature; manos = objetivos absolutos)
# ============================================================================================================
BETA_ALTO, BETA_GOLPE = D(-15), D(125)     # inclinacion del mango del pico (0 = vertical, + = hacia delante)
CABEZA_PICO = 0.30                         # de la mano (agarre) al centro de la cabeza del pico, sobre el mango
PUNTA_D, PUNTA_E = 0.263, 0.239             # de la mano a la punta: a lo largo del mango y a lo largo de la cabeza
PICO_BLEND = "C:/Users/user/Desktop/Alfred_Animacion/objetos/vanilla/stone_pickaxe/stone_pickaxe.blend"
PICO_EJE = Vector((0.7071, 0.7071, 0.0))        # direccion del mango en la malla del pico de piedra (hacia la cabeza)
PICO_AGARRE = PICO_EJE * -0.35 + Vector((-0.7071, 0.7071, 0.0)) * -0.045   # punto del mango (local) que va a la mano


def estado_mina(rig, s):
    """s = 0 pico en alto, s = 1 pico clavado en el suelo"""
    th = lerp(0.15, 1.0, s)
    tg = lerp(0.28, 1.0, s)
    dirs = pose_torso(th, cabeza=lerp(0.05, 0.25, s))
    dirs.update(piernas(0.06, tg, -tg))
    _, colas, _ = resolver_con_brazos(rig, dirs, aplicar=False)
    piso = min(colas["Rightknee_alfred"].z, colas["Leftknee_alfred"].z) + SUELO_PIE
    yf = (colas["Rightknee_alfred"].y + colas["Leftknee_alfred"].y) / 2
    b = lerp(BETA_ALTO, BETA_GOLPE, s)
    d = Vector((0, math.sin(b), math.cos(b)))
    e = Vector((0, math.cos(b), -math.sin(b)))
    G1 = Vector((0, yf + 0.5, piso + 0.02)) - d * PUNTA_D - e * PUNTA_E
    G0 = Vector((0, yf + 0.15, piso + 1.95))
    return dict(th=th, cab=lerp(0.05, 0.25, s), lado=0.0, sep=0.06, cad=tg, rod=-tg,
                Gd=vlerp(G0, G1, s), Gi=None, d=d, yf=yf, piso=piso)


ESTADO_CAIDA = dict(th=0.1, cab=-0.1, lado=0.0, sep=0.20, cad=0.05, rod=-0.05, Gd=Vector((0.62, 0.0, 1.95)),
                    Gi=Vector((-0.62, 0.0, 1.75)), d=Vector((0.4, 0.0, 0.92)))
ESTADO_YACE = dict(th=-0.32, cab=-0.55, lado=0.0, sep=0.14, cad=1.1, rod=-1.0, Gd=Vector((0.74, -0.30, 1.30)),
                   Gi=Vector((-0.20, 0.32, 1.10)), d=Vector((0.35, -0.9, 0.25)))


def mezcla(a, b, q):
    out = {}
    for k in a:
        va, vb = a[k], b.get(k)
        if vb is None or va is None:
            out[k] = va if vb is None else vb
        elif isinstance(va, Vector):
            out[k] = vlerp(va, vb, q)
        else:
            out[k] = lerp(va, vb, q)
    return out


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


def _quitar(nombre):
    ob = bpy.data.objects.get(nombre)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)


def _clonar_bloque(origen, nombre, loc, escala=1.0):
    nuevo = bpy.data.objects.new(nombre, origen.data)
    for i, s in enumerate(origen.material_slots):
        if s.link == 'OBJECT':
            nuevo.material_slots[i].link = 'OBJECT'
            nuevo.material_slots[i].material = s.material
    (origen.users_collection[0]).objects.link(nuevo)
    nuevo.location = loc
    nuevo.scale = (escala,) * 3
    return nuevo


def crear_bloque_techo():
    _quitar("bloque_techo_pozo")
    src = bpy.data.objects["bloque_stone_-46_-16_-2"]
    return _clonar_bloque(src, "bloque_techo_pozo", (CENTRO[0], CENTRO[1], -2.0))


def crear_escombros(n=12, semilla=7):
    rnd = random.Random(semilla)
    src = bpy.data.objects["bloque_stone_-46_-16_-2"]
    lista = []
    for i in range(n):
        nombre = "escombro_techo_%02d" % i
        _quitar(nombre)
        ob = _clonar_bloque(src, nombre, (CENTRO[0], CENTRO[1], -1.0), rnd.uniform(0.07, 0.14))
        v0 = Vector((rnd.uniform(-0.25, 0.25), rnd.uniform(-0.25, 0.25), rnd.uniform(1.5, 3.2)))
        p0 = Vector((CENTRO[0] + rnd.uniform(-0.3, 0.3), CENTRO[1] - 0.25 + rnd.uniform(0.2, 0.6), -1.0 + rnd.uniform(0.0, 0.1)))
        giro = Vector((rnd.uniform(-6, 6), rnd.uniform(-6, 6), rnd.uniform(-6, 6)))
        lista.append((ob, p0, v0, giro))
    return lista


POSE_JSON = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\poses\caida_boca_abajo_cueva.json"
PICO_ORIGINAL = ((-32.37938690185547, -24.337142944335938, 8.071043968200684), (1.5229376554489136, -3.1900954246520996, 0.7842479944229126))
HACHA_AGARRE = Vector((0.025 - 0.15, 0.028 - 0.2, 0.0))     # punto del mango del hacha (coordenadas locales) que va a la cadera
HACHA_EJE = Vector((0.598, 0.801, 0.0))                       # direccion del mango en la malla del hacha
MOV_PICO, MOV_HACHA = Vector((1.5, 0.4, 1.1)), Vector((-1.3, -0.5, 1.3))


POSE_SUELO_JSON = "C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/poses/caida_al_suelo.json"


def cargar_pose_final(ruta=None):
    import json
    with open(ruta or POSE_JSON, encoding="utf8") as fh:
        pose = json.load(fh)["poses"][0]["bones"]
    eul = {n: Euler(tuple(pose[n]["local_space"]["rotation_euler_rad"][c] for c in "xyz"), 'XYZ') for n in ORDEN}
    h = pose["Hips_alfred"]["local_space"]["location"]
    return eul, Vector((h["x"], h["y"], h["z"]))


def cargar_raiz_final(ruta):
    import json
    with open(ruta, encoding="utf8") as fh:
        r = json.load(fh)["poses"][0]["root"]["location"]
    return Vector((r["x"], r["y"], r["z"]))


# accion y reaccion / inercia: tras un golpe el cuerpo rebota y cada parte sigue moviendose con retraso (la cadena tarda mas cuanto mas lejos del golpe)
CADENA = [("Hips_alfred", 0, 0.04), ("Spine_alfred", 1, 0.10), ("Spine1_alfred", 2, 0.14), ("Spine2_alfred", 3, 0.16),
          ("Neck_alfred", 4, 0.30), ("face_alfred", 5, 0.25),
          ("RightUpArm_alfred", 3, 0.50), ("Rightelbow_alfred", 5, 0.40), ("LeftUpArm_alfred", 3, 0.50), ("Leftelbow_alfred", 5, 0.40),
          ("RightUpLeg_alfred", 1, 0.25), ("Rightknee_alfred", 3, 0.20), ("LeftUpLeg_alfred", 1, 0.25), ("Leftknee_alfred", 3, 0.20)]


def reaccion(eul, k, amp=1.0, tau=5.0):
    """k = frames desde el golpe. Oscilacion amortiguada con retraso creciente a lo largo de la cadena (modifica eul)"""
    for n, lag, a in CADENA:
        t = k - lag
        if t > 0:
            eul[n].x += amp * a * math.exp(-t / tau) * math.sin(0.8 * t)


def escalar_luz(f):
    if f <= F_ROMPE:
        return 0.0
    return suave((f - F_ROMPE) / 6.0)


F_RESBALA = 48                        # frames que tarda en resbalar de la punta (lento al principio)
DELTA_RESBALA = D(65)                 # cuanto rueda sobre la punta (hacia el costado) antes de soltarse
RADIO_CUERPO = 0.12                   # grosor aproximado del cuerpo alrededor de los huesos
F_REPOSO = 24                         # frames que se queda quieto en el suelo
ROOT_Z_FINAL = -9.5                   # altura final del empty alfred tendido en el suelo (la fija el usuario)


def dolor(eul, ph, amp=1.0, aleteo=0.0):
    """gestos de dolor sobre la pose final (eul se modifica); amp apaga los gestos, aleteo agita los brazos al caer"""
    pico = max(0.0, math.sin(2 * math.pi * ph * 1.2)) ** 2
    a = amp * (1.0 - math.exp(-ph * 6))
    eul["Spine1_alfred"].x += a * (0.03 * math.sin(2 * math.pi * ph * 0.9) - 0.05 * pico)
    eul["Neck_alfred"].z += a * 0.25 * math.sin(2 * math.pi * ph * 0.35)
    eul["face_alfred"].x += a * 0.10 * math.sin(2 * math.pi * ph * 0.5 + 1.0)
    eul["RightUpLeg_alfred"].x += a * 0.08 * math.sin(2 * math.pi * ph * 0.7)
    eul["LeftUpLeg_alfred"].x += a * 0.08 * math.sin(2 * math.pi * ph * 0.7 + 1.5)
    eul["Leftelbow_alfred"].z += a * 0.15 * math.sin(2 * math.pi * ph * 0.8)
    if aleteo:
        eul["RightUpArm_alfred"].z += aleteo * 0.5 * math.sin(2 * math.pi * ph * 2.0)
        eul["LeftUpArm_alfred"].z += aleteo * 0.5 * math.sin(2 * math.pi * ph * 2.0 + 2.0)
        eul["Rightelbow_alfred"].z += aleteo * 0.3 * math.sin(2 * math.pi * ph * 2.6)


def rotx(th):
    return Matrix.Rotation(th, 3, 'X')


def rot_cuerpo(ph):
    """boca arriba (90 grados sobre X) y despues rueda ph sobre el eje largo del cuerpo (Y del mundo) hacia +X: ph = 180 -> boca abajo"""
    return Matrix.Rotation(ph, 3, 'Y') @ Matrix.Rotation(D(90), 3, 'X')


LADO_RESBALA = 0.45                   # cuanto se desliza de lado (+X) mientras resbala
ANGULO_CAIDA = D(160)                 # casi boca abajo cuando toca el suelo; luego termina de voltearse


def fase_final(rig, datos, fin_eul, fin_hips, f_imp, tip, eul2, hips2, raiz2):
    """despues de quejarse: resbala lentamente hacia un lado de la punta (rueda sobre ella hacia +X), se suelta, cae girando,
    aterriza casi boca abajo y se voltea del todo; queda tendido boca abajo. Un solo cuerpo rigido con la pose fija."""
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    for n in ORDEN:
        rig.pb[n].rotation_euler = fin_eul[n]
    rig.pb["Hips_alfred"].location = fin_hips
    bpy.context.view_layer.update()
    pts = []
    for n in ORDEN:
        pts += [Vector(rig.pb[n].head), Vector(rig.pb[n].tail)]
    c = sum(pts, Vector()) / len(pts)
    f0, L0 = datos[-1][0], Vector(datos[-1][1])
    Pl = rot_cuerpo(0).inverted() @ (tip - L0)             # punto del cuerpo (locales) que descansa sobre la punta

    def bajo(L, ph):
        R = rot_cuerpo(ph)
        puntos = [(L + R @ p) for p in pts]
        i = min(range(len(puntos)), key=lambda k: puntos[k].z)
        return puntos[i], pts[i], puntos[i].z - RADIO_CUERPO

    def suelo(p):
        z = suelo_z(dg, sc, p)
        return z if z is not None else -9.0

    nuevas = []          # (loc, angulo, amp, aleteo)
    # --- 1) resbala hacia el costado girando sobre la punta (cada vez mas rapido)
    ang_de = lambda u: DELTA_RESBALA * (u ** 2.2)
    L_de = lambda u: tip - rot_cuerpo(ang_de(u)) @ Pl + Vector((LADO_RESBALA * u ** 2.2, 0, 0))
    C_de = lambda u: L_de(u) + rot_cuerpo(ang_de(u)) @ c
    for k in range(1, F_RESBALA + 1):
        u = k / F_RESBALA
        nuevas.append((L_de(u), ang_de(u), 1.0, 0.0))
    u0 = 1.0 - 1.0 / F_RESBALA
    v0 = (C_de(1.0) - C_de(u0)) * FPS
    w0 = (ang_de(1.0) - ang_de(u0)) * FPS
    ph0 = ang_de(1.0)
    sub = 8
    dt = 1.0 / (FPS * sub)

    def vuelo(w):
        v, com, ang = Vector(v0), C_de(1.0), ph0
        marcos = []
        for _ in range(90):
            for _ in range(sub):
                v = Vector((v.x, v.y, v.z - G * dt))
                com = com + v * dt
                ang += w * dt
                L = com - rot_cuerpo(ang) @ c
                pb, pl, z = bajo(L, ang)
                if z <= suelo(pb):
                    return marcos, (L, ang, pb, pl, suelo(pb))
            marcos.append((com - rot_cuerpo(ang) @ c, ang))
        return marcos, None

    # --- 2) vuelo libre: la velocidad de giro se ajusta para llegar casi boca abajo al suelo
    w = max(w0, 1.0)
    for _ in range(6):
        marcos, cont = vuelo(w)
        if cont is None:
            break
        w *= (ANGULO_CAIDA - ph0) / max(cont[1] - ph0, 1e-3)
    marcos, cont = vuelo(w)
    for L, ang in marcos:
        nuevas.append((L, ang, 1.0, 1.0))
    f_aterriza = f0 + len(nuevas) + 1
    L, ang, pb, pl, zg = cont
    # --- 3) aterriza y se voltea del todo pivotando sobre el punto de apoyo
    Pc = Vector((pb.x, pb.y, zg + RADIO_CUERPO))
    nuevas.append((Pc - rot_cuerpo(ang) @ pl, ang, 0.6, 0.0))
    n_voltea = 8
    for k in range(1, n_voltea + 1):
        a = ang + (math.pi - ang) * suave(k / n_voltea)
        LL = Pc - rot_cuerpo(a) @ pl
        pb2, _, z2 = bajo(LL, a)
        zg2 = suelo(pb2)
        if z2 < zg2:
            LL = LL + Vector((0, 0, zg2 - z2))
        LL = LL + Vector((0, 0, 0.18 * math.exp(-k / 3.0) * abs(math.sin(math.pi * k / 5.0))))     # rebote al caer (reaccion del suelo)
        nuevas.append((LL, a, max(0.0, 0.6 - 0.07 * k), 0.0))
    f_tumba = f0 + len(nuevas)
    # --- 4) rebote al tumbarse y reposo
    base = nuevas[-1][0].copy()
    for k in range(1, F_REPOSO + 1):
        rebote = 0.07 * math.exp(-k / 3.0) * abs(math.sin(math.pi * k / 4.0))
        nuevas.append((base + Vector((0, 0, rebote)), math.pi, 0.15, 0.0))
    # --- el cuerpo termina en la pose de caida_al_suelo.json y en su lugar (x, y de la raiz)
    i_at, i_tu = f_aterriza - (f0 + 1), f_tumba - (f0 + 1)
    fin = nuevas[-1][0]
    d_xy = Vector((raiz2.x - fin.x, raiz2.y - fin.y, 0.0))
    q1 = {n: fin_eul[n].to_quaternion() for n in ORDEN}
    q2 = {n: eul2[n].to_quaternion() for n in ORDEN}
    previo = {n: Euler(datos[-1][3][n], 'XYZ') for n in ORDEN}
    for i, (L, ph_i, amp, ale) in enumerate(nuevas):
        f = f0 + 1 + i
        ph = (f - f_imp) / FPS
        w = (i / max(1, i_at)) ** 2 if i < i_at else 1.0           # la pose cambia despacio al principio y llega a la del suelo al aterrizar
        eul = {n: q1[n].slerp(q2[n], w).to_euler('XYZ', previo[n]) for n in ORDEN}
        dolor(eul, ph, amp, ale)
        reaccion(eul, f - f_aterriza, 1.4)                           # al aterrizar: el cuerpo se desploma y la cabeza, brazos y piernas siguen de largo
        reaccion(eul, f - f_tumba, 0.9)                              # al quedar tendido: ultimo golpe
        for n in ORDEN:
            eul[n] = eul[n].to_quaternion().to_euler('XYZ', previo[n])
        previo = eul
        desp = d_xy * (suave(i / max(1, i_tu)) if i < i_tu else 1.0)
        datos.append((f, Vector(L) + desp, rot_cuerpo(ph_i).to_quaternion(), {n: tuple(e) for n, e in eul.items()},
                      fin_hips.lerp(hips2, w), None))
    return f_aterriza, f_tumba


def construir(solo_prueba=False, hasta=None):
    rig = Rig()
    obj = bpy.data.objects
    est = obj[ESTALAGMITA]
    punta = Vector((est.location.x, est.location.y, est.location.z + 1.0))
    Hland = Vector((punta.x, punta.y + 0.95 - 0.877, punta.z + 0.28))      # cadera al reposar boca arriba
    fin_eul, fin_hips = cargar_pose_final()
    fin_q = {n: fin_eul[n].to_quaternion() for n in ORDEN}

    def s_de(f):
        for g in GOLPES:
            gp = g - 16
            if gp <= f <= g:
                if f < gp + 6:
                    return 1.0 - suave((f - gp) / 6.0)
                if f < g - 4:
                    return 0.0
                u = (f - (g - 4)) / 4.0
                return u * u
        return 0.0

    st58 = estado_mina(rig, 1.0)
    aplicar_estado(rig, st58)
    eul58 = {n: rig.pb[n].rotation_euler.copy() for n in ORDEN}
    q58 = {n: eul58[n].to_quaternion() for n in ORDEN}
    root_y58 = CENTRO[1] - 0.25 - st58["yf"]
    root_z58 = Z_BLOQUE_TOPE - st58["piso"]
    H0 = Vector((CENTRO[0], root_y58 + 0.041, root_z58 + 0.877))
    T = math.sqrt(2 * (H0.z - Hland.z) / G)
    f_imp = F_ROMPE + int(round(T * FPS))
    f_fin = f_imp + F_QUEJA
    if hasta:
        f_fin = min(f_fin, hasta)
    h_off = rig.hips()

    datos = []
    previo = None
    for f in range(1, f_fin + 1):
        hloc = Vector((0, 0, 0))
        if f <= F_ROMPE:
            st = estado_mina(rig, s_de(f))
            kg = min([f - g for g in GOLPES if f > g] or [99])      # frames desde el ultimo golpe: el pico rebota y el cuerpo retrocede (reaccion)
            if kg < 10:
                r = math.exp(-(kg - 1) / 2.5) * math.cos(0.9 * (kg - 1))
                st["th"] -= 0.10 * r
                st["Gd"] = Vector(st["Gd"]) + Vector((0, -0.03 * r, 0.06 * r))
            rot = Quaternion()
            _, colas, info, d = aplicar_estado(rig, st)
            loc = Vector((CENTRO[0], CENTRO[1] - 0.25 - st["yf"], Z_BLOQUE_TOPE - st["piso"]))
            eul = {n: rig.pb[n].rotation_euler.copy() for n in ORDEN}
            M_arm = matriz_pico(info["mano_d"], d)
        else:
            t = (f - F_ROMPE) / FPS
            tt = min(t, T)
            q = suave(tt / T)                                   # 0 = golpe final, 1 = pose final
            eul = {}
            for n in ORDEN:
                qq = q58[n].slerp(fin_q[n], q)
                eul[n] = qq.to_euler('XYZ', previo[n] if previo else eul58[n])
            hloc = fin_hips * q
            eul = {n: e.copy() for n, e in eul.items()}
            reaccion(eul, f - F_ROMPE, 0.8)                     # al romperse el techo pierde el apoyo: brazos y piernas se quedan atras (inercia)
            if f >= f_imp:
                ph = (f - f_imp) / FPS
                dolor(eul, ph)
                reaccion(eul, f - f_imp, 1.2)                   # el golpe contra la estalagmita lo hace rebotar y la cabeza / miembros siguen de largo
            rot = Quaternion((1, 0, 0), D(90) * suave((tt - 0.12 * T) / (0.88 * T)))
            hz = H0.z - 0.5 * G * tt * tt
            hxy = vlerp((H0.x, H0.y, 0), (Hland.x, Hland.y, 0), suave(tt / T))
            if f >= f_imp:
                u = (f - f_imp) / 6.0
                hz = Hland.z + (0.12 * math.sin(math.pi * u) if u < 1 else 0.0)
            loc = Vector((hxy.x, hxy.y, hz)) - rot @ h_off
            M_arm = None
        previo = eul
        datos.append((f, loc, rot, {n: tuple(e) for n, e in eul.items()}, hloc, M_arm))
    f_aterriza = f_tumba = None
    if not hasta:
        fin2_eul, fin2_hips = cargar_pose_final(POSE_SUELO_JSON)
        f_aterriza, f_tumba = fase_final(rig, datos, fin_eul, fin_hips, f_imp, punta, fin2_eul, fin2_hips, cargar_raiz_final(POSE_SUELO_JSON))
        f_fin = datos[-1][0]
    info = dict(T=T, f_imp=f_imp, f_fin=f_fin, f_aterriza=f_aterriza, f_tumba=f_tumba)
    if solo_prueba:
        return dict(info, n=len(datos))
    return info, datos


def poner(dato):
    """pone la escena en el estado de un frame calculado (sin animar); las herramientas se ponen aparte"""
    f, loc, rot, eul, hloc, M_arm = dato
    root = bpy.data.objects[ROOT]
    root.rotation_mode = 'QUATERNION'
    root.location = loc
    root.rotation_quaternion = rot
    ar = bpy.data.objects[ARM]
    for n, e in eul.items():
        pb = ar.pose.bones[n]
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = e
    ar.pose.bones["Hips_alfred"].location = hloc
    bpy.context.view_layer.update()


def ver(datos, f):
    poner(datos[f - 1])


def matriz_mundo(loc, rot, M_arm):
    return Matrix.Translation(loc) @ rot.to_matrix().to_4x4() @ M_arm


def poner_matriz(ob, Mw):
    ob.rotation_mode = 'QUATERNION'
    l, q, s = Mw.decompose()
    ob.location, ob.rotation_quaternion, ob.scale = l, q, s


# ============================================================================================================
#  HERRAMIENTAS: pico de piedra, hacha de piedra, caida con rebotes
# ============================================================================================================
def crear_pico_piedra():
    """pico de piedra del vanilla (objetos/vanilla/stone_pickaxe); quita la copia hecha del pico de madera si existe"""
    obj = bpy.data.objects
    viejo = obj.get("stone_pickaxe_copia_madera")
    if viejo:
        bpy.data.objects.remove(viejo, do_unlink=True)
    if "stone_pickaxe" not in obj:
        with bpy.data.libraries.load(PICO_BLEND, link=False) as (src, dst):
            dst.objects = ["stone_pickaxe"]
        bpy.context.scene.collection.objects.link(dst.objects[0])
    nuevo = obj["stone_pickaxe"]
    nuevo.scale = (0.6, 0.6, 0.6)
    return nuevo


def base_item(eje, d, n):
    """rotacion de una malla plana (XY): su mango (eje local) -> d, su cara plana (Z local) -> n"""
    d, n = norm(d), norm(n)
    w = n.cross(d)
    a = norm(eje)
    b = Vector((-a.y, a.x, 0))
    L = Matrix(((a.x, b.x, 0), (a.y, b.y, 0), (0, 0, 1)))
    Cw = Matrix(((d.x, w.x, n.x), (d.y, w.y, n.y), (d.z, w.z, n.z)))
    return Cw @ L.transposed()


def base_hacha(d, n):
    return base_item(HACHA_EJE, d, n)


def suelo_z(dg, sc, p):
    """altura del bloque de cueva que hay bajo p (ignora a Alfred y la estalagmita)"""
    o = Vector((p.x, p.y, p.z + 0.5))
    for _ in range(8):
        ok, pos, nor, idx, ob, mw = sc.ray_cast(dg, o, Vector((0, 0, -1)), distance=40)
        if not ok:
            return None
        if ob.name.startswith("bloque_"):
            return pos.z
        o = pos + Vector((0, 0, -0.01))
    return None


def simular_caida(dg, sc, M0, v0, grosor, n_frames, plano_y, yaw):
    """tira la herramienta desde la matriz M0: gravedad, rebotes y rozamiento sobre el suelo de la cueva.
    plano_y: la cara plana es el eje local Y (pico) o Z (hacha). Devuelve una matriz por frame (frame 0 = M0)."""
    l0, q0, esc = M0.decompose()
    h = Vector((math.cos(yaw), math.sin(yaw), 0))
    up = Vector((0, 0, 1))
    eje = PICO_EJE if plano_y == 'Y' else HACHA_EJE       # 'Y' = pico, 'Z' = hacha: las dos son mallas planas con el mango en diagonal
    Rf = base_item(eje, h, up)
    eje_giro = Vector((0, 0, 1)).cross(eje)
    qf = Rf.to_quaternion()
    p, v = l0.copy(), Vector(v0)
    sub = 8
    dt = 1.0 / (FPS * sub)
    salida = [M0.copy()]
    for k in range(1, n_frames + 1):
        for _ in range(sub):
            v.z -= G * dt
            p += v * dt
            z = suelo_z(dg, sc, p)
            if z is not None and p.z < z + grosor:
                p.z = z + grosor
                v.z = -v.z * 0.42 if v.z < -0.5 else 0.0
                v.x *= 0.80
                v.y *= 0.80
            elif z is not None and p.z < z + grosor + 0.002:
                v.x *= 0.93
                v.y *= 0.93
        s = min(k / (FPS * 1.4), 1.0)
        q = q0.slerp(qf, suave(s))
        q = q @ Quaternion(eje_giro, 2 * math.pi * 1.5 * 4 * s * (1 - s))
        salida.append(Matrix.LocRotScale(p.copy(), q, esc))
    return salida


def hornear(info, datos):
    sc = bpy.context.scene
    obj = bpy.data.objects
    root, arm = obj[ROOT], obj[ARM]
    f_imp, f_fin = info["f_imp"], info["f_fin"]
    rig = Rig()
    # --- herramientas
    mad = obj["wooden_pickaxe"]                         # el pico de madera vuelve a su sitio, sin animacion
    if mad.animation_data:
        mad.animation_data_clear()
    mad.rotation_mode = 'XYZ'
    mad.location, mad.rotation_euler, mad.scale = PICO_ORIGINAL[0], PICO_ORIGINAL[1], (0.6, 0.6, 0.6)
    pico = crear_pico_piedra()
    hacha = obj["stone_axe"]
    for ob in (root, arm, pico, hacha):
        if ob.animation_data:
            ob.animation_data_clear()
    for ojo in ("ojo_derecho_alfred", "ojo_izquierdo_alfred"):     # los ojos no se animan: se quitan mis llaves y vuelven a 0
        sk = obj[ojo].data.shape_keys
        if sk.animation_data:
            sk.animation_data_clear()
        for k in ("Enojado", "Sorpresa", "Cerrado", "Triste"):
            sk.key_blocks[k].value = 0.0
    # hacha colgada de la cadera izquierda (mango abajo, cabeza arriba, cara plana hacia fuera)
    d_h, n_h = Vector((0, 0, 1)), Vector((-1, 0, 0))
    R_h = base_hacha(d_h, n_h)
    agarre = Vector((-0.36, 0.04, 0.86))
    org = agarre - R_h @ (0.6 * HACHA_AGARRE)
    rel_hacha = rig.rest["Hips_alfred"].inverted() @ Matrix.LocRotScale(org, R_h.to_quaternion(), Vector((0.6, 0.6, 0.6)))
    # --- poses y herramientas, frame a frame
    rel_pico = None
    Mpico, Mhacha = {}, {}
    f_at, f_tu = info.get("f_aterriza"), info.get("f_tumba")
    dz_final = 0.0
    if f_tu:                                              # el empty queda en ROOT_Z_FINAL al tumbarse (x, y ya vienen de la pose del suelo)
        dz_final = ROOT_Z_FINAL - datos[f_tu - 1][1].z
    for d in datos:
        poner(d)
        f, loc, rot = d[0], d[1], d[2]
        if f_at and f >= f_at:
            loc = loc + Vector((0, 0, dz_final * (1.0 if f >= f_tu else suave((f - f_at) / max(1, f_tu - f_at)))))
            root.location = loc
        fore = arm.pose.bones["Rightelbow_alfred"].matrix
        if f <= F_ROMPE:
            M_arm = d[5]
            if f == F_ROMPE:
                rel_pico = fore.inverted() @ M_arm
        else:
            M_arm = fore @ rel_pico
        Mpico[f] = matriz_mundo(loc, rot, M_arm)
        Mhacha[f] = matriz_mundo(loc, rot, arm.pose.bones["Hips_alfred"].matrix @ rel_hacha)
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_quaternion", frame=f)
        for n in ORDEN:
            arm.pose.bones[n].keyframe_insert("rotation_euler", frame=f)
        arm.pose.bones["Hips_alfred"].keyframe_insert("location", frame=f)
    # --- caida con rebotes de las dos herramientas desde el golpe
    dg = bpy.context.evaluated_depsgraph_get()
    n_post = f_fin - f_imp
    caida_pico = simular_caida(dg, sc, Mpico[f_imp], MOV_PICO, 0.03, n_post, 'Y', math.atan2(MOV_PICO.y, MOV_PICO.x))
    caida_hacha = simular_caida(dg, sc, Mhacha[f_imp], MOV_HACHA, 0.015, n_post, 'Z', math.atan2(MOV_HACHA.y, MOV_HACHA.x))
    for f in range(1, f_fin + 1):
        if f < f_imp:
            Mp, Mh = Mpico[f], Mhacha[f]
        else:
            Mp, Mh = caida_pico[f - f_imp], caida_hacha[f - f_imp]
        for ob, M in ((pico, Mp), (hacha, Mh)):
            poner_matriz(ob, M)
            ob.keyframe_insert("location", frame=f)
            ob.keyframe_insert("rotation_quaternion", frame=f)
            ob.keyframe_insert("scale", frame=f)
    # --- bloque del techo, escombros y luces
    bloque = crear_bloque_techo()
    for prop in ("hide_viewport", "hide_render"):
        setattr(bloque, prop, False)
        bloque.keyframe_insert(prop, frame=1)
        bloque.keyframe_insert(prop, frame=F_ROMPE)
        setattr(bloque, prop, True)
        bloque.keyframe_insert(prop, frame=F_ROMPE + 1)
    for ob, p0, v0, giro in crear_escombros():
        ob.rotation_mode = 'XYZ'
        if ob.animation_data:
            ob.animation_data_clear()
        for prop in ("hide_viewport", "hide_render"):
            setattr(ob, prop, True)
            ob.keyframe_insert(prop, frame=1)
            ob.keyframe_insert(prop, frame=F_ROMPE - 1)
            setattr(ob, prop, False)
            ob.keyframe_insert(prop, frame=F_ROMPE)
        a_, b_, c_ = -0.5 * G, v0.z, p0.z + 8.9
        t_suelo = (-b_ - math.sqrt(b_ * b_ - 4 * a_ * c_)) / (2 * a_)
        for f in range(F_ROMPE, f_fin + 1):
            t = min((f - F_ROMPE) / FPS, t_suelo)
            ob.location = p0 + v0 * t + Vector((0, 0, -0.5 * G * t * t))
            ob.rotation_euler = tuple(g * min(t, 1.2) for g in giro)
            ob.keyframe_insert("location", frame=f)
            ob.keyframe_insert("rotation_euler", frame=f)
    for nombre in ("luz_entrada_cueva", "Point"):
        luz = obj.get(nombre)
        if not luz or luz.type != 'LIGHT':
            continue
        e0 = luz["energia_nominal"] if "energia_nominal" in luz.keys() else luz.data.energy
        luz["energia_nominal"] = e0
        if luz.data.animation_data:
            luz.data.animation_data_clear()
        for f in range(1, F_ROMPE + 9):
            luz.data.energy = e0 * escalar_luz(f)
            luz.data.keyframe_insert("energy", frame=f)
    root["f_aterriza"], root["f_tumba"], root["f_imp"], root["f_fin"] = f_at or 0, f_tu or 0, f_imp, f_fin
    sc.frame_set(1)
    return info
