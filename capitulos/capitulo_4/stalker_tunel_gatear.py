# -*- coding: utf-8 -*-
"""The Stalker (the_stalker_1, 1 x 3 m) avanzando por el tunel de 1 x 2 m (x -99..-98, z -18..-16, hacia +Y, directo a la camara).
No cabe de pie: avanza agachado, con el torso inclinado ~30 grados y la cabeza levantada mirando al frente (cara, dientes y pecho hacia la camara),
y se impulsa con los brazos: cada mano se AFERRA a la pared (cinematica inversa de 2 huesos con la mano fija en el mundo mientras tira del cuerpo,
luego la suelta y busca otro agarre mas adelante). Las piernas empujan contra el suelo con otro ritmo: ningun lado es simetrico (periodos, fases,
alturas de agarre y longitudes de paso distintos en cada extremidad).
Solo toca los 14 huesos del cuerpo (root, spine, chest, neck, head, neck_front, muslos, canillas, brazos, antebrazos) y la ubicacion Y del empty `the_stalker_1`;
los tentaculos (stalker_tentaculos) quedan como estaban. Se guarda copia de las acciones originales (sufijo .respaldo_caminar).
Uso en Blender: exec(open(ruta,encoding="utf8").read()); aplicar()
"""
import bpy, math, random
from mathutils import Vector, Quaternion, Euler

ARM, EMP = "torso_1", "the_stalker_1"
F0, F1 = 1, 261                    # F0..F1 = tiempo de marcha (frames de recorrido, sin contar la espera)
INICIO_MARCHA = 276                # el Stalker se queda parado hasta este frame y entonces empieza a avanzar
OJOS_FRAME = 216                   # desde este frame se ven solo sus ojos (el cuerpo aparece en INICIO_MARCHA)
Y0 = -96.5                         # inicio del recorrido (igual que la animacion original)
RECORRIDO = 15.2                   # metros avanzados entre F0 y F1 (llega casi a la camara, y = -82.5, hacia el frame 240)
MURO = 0.47                        # x de las paredes del tunel respecto al eje (mitad del ancho 1.0)
ALTURA_CADERA = 0.37               # la cadera baja de 1.22 a esto (agachado)
HUESOS = ["root_1", "spine_1", "chest_1", "neck_1", "head_1", "neck_front_1", "jaw_1", "thigh.L_1", "shin.L_1", "thigh.R_1", "shin.R_1",
          "upper_arm.L_1", "forearm.L_1", "upper_arm.R_1", "forearm.R_1"]

# parametros de cada extremidad: periodo, fase, fraccion del ciclo apoyada (tirando/empujando), alcance atras (m), altura del agarre, semilla
BRAZOS = {"L": dict(P=34, ph=3, d=0.50, fin=0.85, alt=1.15, jit=0.30, sem=1),
          "R": dict(P=39, ph=19, d=0.40, fin=0.90, alt=0.85, jit=0.40, sem=2)}
PIERNAS = {"L": dict(P=34, ph=21, d=0.50, atras=0.40, sem=3),
           "R": dict(P=52, ph=9, d=0.40, atras=0.50, sem=4)}


LIMITADO = {}                     # cuantas veces el objetivo quedo fuera del alcance de la cadena
DEPURA = {}                        # (cuadro, lado) -> (hombro, objetivo, codo) del ultimo calculo, para depurar


def suave(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def ciclo(f, p):
    """(k, estado, avance): k = numero de ciclo; estado 'balanceo' o 'apoyo'; avance 0-1 dentro del estado"""
    u = (f - p["ph"]) / p["P"]
    k = math.floor(u)
    u -= k
    lim = 1.0 - p["d"]
    return (k, "balanceo", u / lim) if u < lim else (k, "apoyo", (u - lim) / p["d"])


def inicio_apoyo(k, p):
    return p["ph"] + k * p["P"] + (1.0 - p["d"]) * p["P"]


def fin_apoyo(k, p):
    return p["ph"] + (k + 1) * p["P"]


class Rig:
    def __init__(self):
        self.arm = bpy.data.objects[ARM]
        d = self.arm.data.bones
        self.H = {b.name: Vector(b.head_local) for b in d}
        self.R = {b.name: b.matrix_local.to_3x3().to_quaternion() for b in d}


def rot(rx=0.0, ry=0.0, rz=0.0):
    return Euler((rx, ry, rz), 'XYZ').to_quaternion()


def arco(a, b):
    return a.normalized().rotation_difference(b.normalized())


def ik2(S, T, v1, v2, l2, pole, tag=""):
    """cadena de 2 huesos: hombro S, objetivo T; v1 = vector en reposo hombro->codo, v2 = codo->muneca (direccion), l2 = largo codo->punta.
    devuelve (D1, D2): rotaciones absolutas (espacio del armature) de cada hueso"""
    l1 = v1.length
    d = (T - S).length
    if d < abs(l1 - l2) + 0.02 or d > l1 + l2 - 0.01:
        LIMITADO[tag] = LIMITADO.get(tag, 0) + 1
    d = min(max(d, abs(l1 - l2) + 0.02), l1 + l2 - 0.01)
    u = (T - S).normalized()
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    pp = pole - u * pole.dot(u)
    pp = pp.normalized() if pp.length > 1e-6 else Vector((0, -1, 0))
    codo = S + u * a + pp * h
    dir1 = (codo - S).normalized()
    dir2 = (S + u * d - codo).normalized()
    return arco(v1, dir1), arco(v2, dir2), codo


def torso(f, sL, sR, vivo):
    """angulos del tronco en el cuadro f. sL, sR = 0..1 cuanto tira cada brazo (inclina y gira el torso hacia el brazo que tira)"""
    w = 2 * math.pi
    lat = -0.12 * (sL - sR)
    giro = 0.16 * (sL - sR)
    cab = 0.10 * math.sin(w * f / 61.0 + 0.7) + 0.06 * math.sin(w * f / 23.0)
    emb = 0.10 * math.sin(w * f / 29.0)                                       # embestida de la cabeza hacia la camara
    q = {}
    q["spine_1"] = rot(-0.46 - 0.05 * (sL + sR) * 0.5, lat * 0.6, giro * 0.5)
    q["chest_1"] = rot(-0.30 + 0.04 * math.sin(w * f / 37.0), lat * 0.7, giro * 0.7 + 0.04 * math.sin(w * f / 41.0))
    q["neck_1"] = rot(0.18 + emb * 0.5, cab * 0.3, cab * 0.5)
    q["head_1"] = rot(0.46 + emb, cab * 0.5 - lat * 0.3, cab * 0.9 - giro * 0.6)
    q["neck_front_1"] = rot(0.12 * vivo, 0.0, 0.0)
    q["jaw_1"] = rot(-0.18 * vivo, 0.0, 0.0)
    return q


def aplicar(guardar_respaldo=True):
    sc = bpy.context.scene
    rg = Rig()
    arm = rg.arm
    emp = bpy.data.objects[EMP]
    pb = arm.pose.bones
    if guardar_respaldo:
        for ob in (arm, emp):
            a = ob.animation_data.action
            if a and not any(x.name == a.name + ".respaldo_caminar" for x in bpy.data.actions):
                c = a.copy()
                c.name = a.name + ".respaldo_caminar"
                c.use_fake_user = True
    for b in HUESOS:
        pb[b].rotation_mode = 'QUATERNION'
    H = rg.H
    # ---------- 1) velocidad del cuerpo: avanza a tirones cuando algun brazo (o pierna) esta aferrado
    fr = list(range(-90, F1 + 100))
    v = {}
    for f in fr:
        s = 0.9
        for n, w in (("L", 1.0), ("R", 0.85)):
            k, est, p = ciclo(f, BRAZOS[n])
            if est == "apoyo":
                s += w * math.sin(math.pi * p) ** 2
        for n, w in (("L", 0.35), ("R", 0.5)):
            k, est, p = ciclo(f, PIERNAS[n])
            if est == "apoyo":
                s += w * math.sin(math.pi * p)
        v[f] = s
    tot = sum(v[f] for f in range(F0, F1))
    esc = RECORRIDO / tot
    y = {}
    acum = 0.0
    for f in range(F0, fr[-1] + 1):
        y[f] = Y0 + acum
        acum += v[f] * esc
    acum = 0.0
    for f in range(F0 - 1, fr[0] - 1, -1):
        acum -= v[f] * esc
        y[f] = Y0 + acum
    # ---------- 2) tronco: posiciones del hombro y de la cadera en el mundo
    pull = {}
    for f in fr:
        pull[f] = tuple((math.sin(math.pi * ciclo(f, BRAZOS[n])[2]) ** 2 if ciclo(f, BRAZOS[n])[1] == "apoyo" else 0.0) for n in ("L", "R"))
    sh = {}
    cad = {}
    for f in fr:
        vivo = 0.5 + 0.5 * math.sin(2 * math.pi * f / 47.0 + 1.3)
        q = torso(f, pull[f][0], pull[f][1], vivo)
        T = Vector((0.04 * math.sin(2 * math.pi * f / 34.0) , 0.0, ALTURA_CADERA - 1.22 + 0.04 * math.sin(2 * math.pi * f / 17.0)))
        Ds = q["spine_1"]
        Dc = Ds @ q["chest_1"]
        Pc = T + H["spine_1"] + Ds @ (H["chest_1"] - H["spine_1"])
        pos = {}
        for n, s in (("L", -1), ("R", 1)):
            pos[n] = Vector((0, y[f], -18.0)) + Pc + Dc @ (H["upper_arm.%s_1" % n] - H["chest_1"])
        sh[f] = (pos["L"], pos["R"])
        cad[f] = {n: Vector((0, y[f], -18.0)) + T + H["thigh.%s_1" % n] for n in ("L", "R")}
    # ---------- 3) puntos de agarre / apoyo (fijos en el mundo mientras la extremidad esta apoyada)
    def superficie(n, f):
        """a que se aferra cada brazo: primero las paredes (ambos), luego un brazo al suelo, luego el otro al techo, y vuelve a las paredes"""
        if n == "L" and 80 <= f < 145:
            return "suelo"
        if n == "R" and 145 <= f < 210:
            return "techo"
        return "pared"

    def punto_brazo(n, k):
        p = BRAZOS[n]
        s = -1 if n == "L" else 1
        rng = random.Random(p["sem"] * 1000 + k)
        i = 0 if n == "L" else 1
        fi, fe = int(round(inicio_apoyo(k, p))), int(round(fin_apoyo(k, p)))
        sup = superficie(n, fi)
        if sup == "suelo":
            x, z = s * (0.36 + 0.08 * rng.random()), -17.97
        elif sup == "techo":
            x, z = s * (0.36 + 0.08 * rng.random()), -16.03
        else:
            x, z = s * (MURO - 0.02 * rng.random()), -18.0 + 0.9 + 0.85 * rng.random()
        Si, Se = sh[fi][i], sh[fe][i]
        yf = Se.y + p["fin"] * (0.9 + 0.2 * rng.random())
        q = (z - Si.z) ** 2 + (x - Si.x) ** 2
        yf = min(yf, Si.y + math.sqrt(max(1.9 ** 2 - q, 0.05)))                # el brazo (2.1 m) no llega mas lejos al empezar el agarre
        qe = (z - Se.z) ** 2 + (x - Se.x) ** 2
        yf = max(yf, Se.y + (math.sqrt(0.85 ** 2 - qe) if qe < 0.85 ** 2 else -0.5))   # ni se pliega mas de lo posible al terminarlo
        SUP[(n, k)] = sup
        return Vector((x, yf, z))

    def punto_pie(n, k):
        p = PIERNAS[n]
        s = -1 if n == "L" else 1
        rng = random.Random(p["sem"] * 1000 + k)
        yf = cad[int(round(fin_apoyo(k, p)))][n].y if int(round(fin_apoyo(k, p))) in cad else y[F1]
        return Vector((s * (0.17 + 0.05 * rng.random()), yf - p["atras"] * (0.8 + 0.4 * rng.random()), -18.0 + 0.0))

    def objetivo(punto, p, f, alto_arco, lado_arco, s, base):
        """base(f) = posicion del hombro / cadera en el mundo. En el balanceo la mano va de su agarre anterior al siguiente medida DESDE el hombro
        (asi nunca queda demasiado cerca ni lejos del cuerpo aunque este avance mientras tanto)"""
        k, est, pr = ciclo(f, p)
        if est == "apoyo":
            return punto(k)
        f0 = int(round(p["ph"] + k * p["P"]))
        f1 = int(round(inicio_apoyo(k, p)))
        ra = punto(k - 1) - base(f0)
        rb = punto(k) - base(f1)
        e = suave(pr)
        arc = math.sin(math.pi * pr)
        pt = base(f) + ra.lerp(rb, e)
        pt.z += alto_arco * arc
        pt.x -= s * lado_arco * arc
        return pt

    SUP = {}
    POLO = {"pared": Vector((-0.4, -0.5, -1.0)), "suelo": Vector((0.7, -0.4, 0.8)), "techo": Vector((0.8, -0.2, -0.6))}      # x: + hacia afuera (pared), - hacia dentro; se multiplica por el lado
    v1 = {}
    v2 = {}
    for n in ("L", "R"):
        v1["a" + n] = H["forearm.%s_1" % n] - H["upper_arm.%s_1" % n]
        v2["a" + n] = H["finger_1.%s_1" % n] - H["forearm.%s_1" % n]
        v1["l" + n] = H["shin.%s_1" % n] - H["thigh.%s_1" % n]
        v2["l" + n] = Vector((0, 0, -0.68))
    # ---------- 4) un cuadro a la vez: tronco, brazos y piernas -> huesos
    LIMITADO.clear()
    emp.location.y = Y0
    maxz = -99
    for fk in range(F0, F1 + INICIO_MARCHA):
        f = max(fk - (INICIO_MARCHA - 1), F0)                                   # tiempo de marcha: antes de INICIO_MARCHA se queda parado
        sc.frame_set(fk)
        vivo = 0.5 + 0.5 * math.sin(2 * math.pi * f / 47.0 + 1.3)
        q = torso(f, pull[f][0], pull[f][1], vivo)
        if fk < INICIO_MARCHA:                                                   # parado: solo respira y mueve un poco la cabeza
            amort = 1.0 - suave((fk - (INICIO_MARCHA - 15)) / 15.0)
            resp = math.sin(2 * math.pi * fk / 72.0) * amort
            q["chest_1"] = q["chest_1"] @ rot(0.015 * resp, 0.0, 0.0)
            q["head_1"] = q["head_1"] @ rot(-0.012 * resp, 0.0, 0.02 * math.sin(2 * math.pi * fk / 130.0) * amort)
        T = Vector((0.04 * math.sin(2 * math.pi * f / 34.0), 0.0, ALTURA_CADERA - 1.22 + 0.04 * math.sin(2 * math.pi * f / 17.0)))
        D = {"root_1": Quaternion()}
        D["spine_1"] = q["spine_1"]
        D["chest_1"] = D["spine_1"] @ q["chest_1"]
        D["neck_1"] = D["chest_1"] @ q["neck_1"]
        D["head_1"] = D["neck_1"] @ q["head_1"]
        D["neck_front_1"] = D["head_1"] @ q["neck_front_1"]              # la mandibula inferior sigue a la cabeza (no al pecho)
        D["jaw_1"] = D["head_1"] @ q["jaw_1"]
        # posicion: la mandibula (hueso hijo del pecho) se traslada para quedar donde estaria si colgara de la cabeza
        Pe = T + H["spine_1"]
        Pc = Pe + D["spine_1"] @ (H["chest_1"] - H["spine_1"])
        Pn = Pc + D["chest_1"] @ (H["neck_1"] - H["chest_1"])
        Ph = Pn + D["neck_1"] @ (H["head_1"] - H["neck_1"])
        real = Pc + D["chest_1"] @ (H["neck_front_1"] - H["chest_1"])
        deseada = Ph + D["head_1"] @ (H["neck_front_1"] - H["head_1"])
        loc_mand = rg.R["neck_front_1"].inverted() @ (D["chest_1"].inverted() @ (deseada - real))
        origen = Vector((0, y[f], -18.0))
        S = {n: sh[f][0 if n == "L" else 1] for n in ("L", "R")}
        for n in ("L", "R"):
            s = -1 if n == "L" else 1
            pa = BRAZOS[n]
            Tm = objetivo(lambda k, n=n: punto_brazo(n, k), pa, f, 0.35, 0.10, s, lambda ff, n=n: sh[ff][0 if n == "L" else 1])
            kk, est, pr = ciclo(f, pa)
            punto_brazo(n, kk)
            if est == "apoyo":
                polo = POLO[SUP[(n, kk)]]
            else:
                punto_brazo(n, kk - 1)
                polo = POLO[SUP[(n, kk - 1)]].lerp(POLO[SUP[(n, kk)]], suave(pr))
            polo = Vector((s * polo.x, polo.y, polo.z))                            # el codo apunta hacia dentro (pared) o hacia afuera (suelo/techo) para no cruzar la cara
            Tm.z = min(Tm.z, -16.03)                                                # la mano no atraviesa el techo
            d1, d2, codo = ik2(S[n] - origen, Tm - origen, v1["a" + n], v2["a" + n], 1.44, polo, "brazo" + n)
            DEPURA[(f, n)] = (S[n] - origen, Tm - origen, codo)
            D["upper_arm.%s_1" % n] = d1
            D["forearm.%s_1" % n] = d2
            pl = PIERNAS[n]
            Tp = objetivo(lambda k, n=n: punto_pie(n, k), pl, f, 0.30, 0.0, s, lambda ff, n=n: cad[ff][n])
            c0 = cad[f][n] - origen
            e1, e2, rod = ik2(c0, Tp - origen, v1["l" + n], v2["l" + n], 0.68, Vector((s * 0.3, 0.9, 0.5)), "pierna" + n)
            D["thigh.%s_1" % n] = e1
            D["shin.%s_1" % n] = e2
        padre = {b: (arm.data.bones[b].parent.name if arm.data.bones[b].parent else None) for b in HUESOS}
        for b in HUESOS:
            Db = D[b]
            pn = padre[b]
            while pn is not None and pn not in D:
                pn = arm.data.bones[pn].parent.name if arm.data.bones[pn].parent else None
            Dp = D[pn] if pn else Quaternion()
            Rb = rg.R[b]
            bas = Rb.inverted() @ Dp.inverted() @ Db @ Rb
            pb[b].rotation_quaternion = bas
            pb[b].keyframe_insert("rotation_quaternion", frame=fk)
        pb["neck_front_1"].location = loc_mand
        pb["neck_front_1"].keyframe_insert("location", frame=fk)
        lx, lz = T.x, T.z
        pb["root_1"].location = Vector((lx, lz, 0.0))                       # el eje local Y del hueso es el Z del armature (Z local = -Y)
        pb["root_1"].keyframe_insert("location", frame=fk)
        emp.location.y = y[f]
        emp.keyframe_insert("location", index=1, frame=fk)
    sc.frame_set(sc.frame_current)
    return dict(y_ini=y[F0], y_fin=y[F1], fuera_de_alcance=dict(LIMITADO))


def _quitar_curvas_ocultar(ob):
    ad = ob.animation_data
    if not ad or not ad.action:
        return
    for l in ad.action.layers:
        for st in l.strips:
            for cb in st.channelbags:
                for fc in [fc for fc in cb.fcurves if fc.data_path in ("hide_viewport", "hide_render")]:
                    cb.fcurves.remove(fc)


def _visible_desde(ob, frame):
    """oculto hasta frame-1, visible desde `frame`"""
    for prop in ("hide_viewport", "hide_render"):
        setattr(ob, prop, True)
        ob.keyframe_insert(prop, frame=1)
        ob.keyframe_insert(prop, frame=frame - 1)
        setattr(ob, prop, False)
        ob.keyframe_insert(prop, frame=frame)


def apariciones(ojos=OJOS_FRAME, cuerpo=None):
    """del frame 1 al `ojos`-1 no se ve nada; desde `ojos` solo los ojos (rombos blancos en la oscuridad); el cuerpo, las luces y las gotas aparecen en `cuerpo`
    (por defecto INICIO_MARCHA, cuando empieza a avanzar)"""
    cuerpo = cuerpo or INICIO_MARCHA
    emp = bpy.data.objects[EMP]
    obs = [emp] + list(emp.children_recursive)
    for ob in obs:
        _quitar_curvas_ocultar(ob)
    n_ojos = 0
    for ob in obs:
        es_ojo = ob.name.startswith("Ojo_Terror")
        n_ojos += es_ojo
        _visible_desde(ob, ojos if (es_ojo or ob is emp) else cuerpo)
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    return dict(objetos=len(obs), ojos=n_ojos, ojos_desde=ojos, cuerpo_desde=cuerpo)
