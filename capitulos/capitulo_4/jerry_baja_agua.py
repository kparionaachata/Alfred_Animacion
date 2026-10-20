# -*- coding: utf-8 -*-
"""Jerry baja por la columna de agua del hueco (-49, -19) con un cubo (bucket) en la boca, rebota en el agua, salta al suelo seco y se sacude para secarse.
Escena: alfred_cueva_2.blend. Jerry = empty `jerry` (escala 1.2, mira a +X en reposo) + armature `Dog_001_rig` (43 huesos). Todo se hornea por frame (24 fps).

 F_CAMINA .. F_BAJA   trota desde donde esta hasta el borde del hueco (esquivando el hueco de Alfred) y se agacha
 F_BAJA               salta de nariz al hueco y cae por la columna de agua (arrastre del agua: velocidad limite V_AGUA)
 impacto              toca el fondo con el hocico, rebota en el agua y se endereza en el aire
 despues              vadea hasta el borde del charco, salta al suelo seco, y se sacude (cuerpo, orejas y cola) para secarse
El cubo es `bucket_jerry` (objetos/vanilla/bucket/bucket.blend): va pegado a la mandibula (jaw_bot) y se hornea desde el hueso.
Uso en Blender: exec(open(ruta).read()); datos = construir(); hornear(datos)
"""
import bpy, math, random
from mathutils import Vector, Matrix, Quaternion, Euler

RIG, ROOT, BUCKET = "Dog_001_rig", "jerry", "bucket_jerry"
FPS = 24
S = 1.3                                   # escala del armature Dog_001_rig (jerry.blend de estructura_lista)
HOYO = (-48.5, -18.5)                     # centro del hueco de agua
F_BAJA = 378                              # frame en que empieza a bajar
V_TROTE, V_AGUA, V_VADEO = 3.4, 6.0, 2.2  # m/s: trote en superficie, caida limite dentro del agua, vadeo
G = 9.8
C_LOCAL = Vector((0.0, 0.1, 0.5))         # centro del cuerpo en el armature (sin escala)
NARIZ_LOCAL = Vector((0.0, 0.72, 0.42))   # punta del hocico
PUNTOS = [(-42.3, -8.52), (-43.5, -17.0), (-45.0, -22.5), (-48.5, -22.6), (-48.5, -19.6)]   # recorrido en la superficie: llega al borde SUR del hueco caminando hacia +Y (rotacion 0), esquivando el hueco de Alfred
BORDE = (-48.5, -19.6)
RUTA_JSON = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/jerry_ruta_a.json"   # recorrido hecho con blender_path_bloques.py: de donde se seca hasta Alfred
V_RUTA = 3.4                              # m/s caminando por ese recorrido (ciclo de caminata del usuario)
ESPERA_BORDE = 0                          # frames que espera en el borde (el agua aun cae) antes de saltar
DEMORA_RUTA = 0                           # frames quieto antes de caminar: Alfred planta la antorcha (alfred_coloca_antorcha.py) y Jerry llega despues
CICLO_RUTA = 14                          # ciclo de caminata lento: llega a Alfred despues de que plante la antorcha
F_ALFRED_DE_PIE = 552                     # frame en que Alfred ya esta de pie


def suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


# ------------------------------------------------------------------------------------------------------------------------------------ mundo
class Mundo:
    def __init__(self):
        col = bpy.data.collections["cueva_bloques"]
        self.cs = {}
        for ob in col.objects:
            if ob.name.startswith("bloque_"):
                l = ob.location
                self.cs[(int(l.x // 1), int(l.y // 1), int(round(l.z)))] = ob
        g = bpy.data.objects["Grass_Block"]
        self.g, self.gM, self.gMi = g, g.matrix_world, g.matrix_world.inverted()

    def pasto(self, x, y, defecto=8.0):
        """altura de la superficie (pasto) en x, y"""
        o = self.gMi @ Vector((x, y, 40.0))
        d = (self.gMi.to_3x3() @ Vector((0, 0, -1))).normalized()
        ok, loc, n, i = self.g.ray_cast(o, d, distance=200)
        if ok:
            return (self.gM @ loc).z
        if (int(math.floor(x)), int(math.floor(y)), 7) in self.cs:             # el borde del hueco son bloques de la cueva (k = 7: su cara de arriba esta en z = 8)
            return 8.0
        return defecto

    def suelo(self, x, y, desde=-3):
        """z del suelo de la cueva en la celda de (x, y): encima del primer bloque hacia abajo desde k = desde"""
        i, j = int(math.floor(x)), int(math.floor(y))
        for k in range(desde, -30, -1):
            if (i, j, k) in self.cs:
                return k + 1.0
        return -10.0

    def libre(self, i, j, k, alto=3):
        return all((i, j, k + a) not in self.cs for a in range(alto))


def zona_seca(mundo, pasos=4):
    """donde se seca: desde el borde del charco, un camino de `pasos` celdas secas con suelo y 3 bloques de aire encima (sin saltos de mas de 1 bloque).
    Devuelve la celda mojada pegada al camino, el camino [(celda, z_suelo)] y el flujo del agua"""
    import importlib.util, sys
    from collections import deque
    mod = sys.modules.get("hueco_agua_49_19")
    if mod is None:
        spec = importlib.util.spec_from_file_location("hueco_agua_49_19", "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/hueco_agua_49_19.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["hueco_agua_49_19"] = mod
        spec.loader.exec_module(mod)
    flujo = mod.simular_flujo(mundo.cs, mod.CELDA[0], mod.CELDA[1], -10)
    mojadas = {(x, y) for (x, y, k) in flujo}

    def piso(c):
        z = mundo.suelo(c[0] + 0.5, c[1] + 0.5)
        return z if mundo.libre(c[0], c[1], int(z)) else None

    vec = ((1, 0), (-1, 0), (0, 1), (0, -1))
    salidas = []
    for (x, y) in mojadas:
        for dx, dy in vec:
            n = (x + dx, y + dy)
            if n not in mojadas and piso(n) is not None:
                salidas.append((math.hypot(n[0] + 0.5 - HOYO[0], n[1] + 0.5 - HOYO[1]), (x, y), n))
    for _, mojada, ini in sorted(salidas):
        cola = deque([(ini, [ini])])
        vistos = {ini}
        while cola:
            c, camino = cola.popleft()
            if len(camino) == pasos:
                return dict(mojada=mojada, camino=[(q, piso(q)) for q in camino], flujo=flujo)
            for dx, dy in vec:
                n = (c[0] + dx, c[1] + dy)
                if n in vistos or n in mojadas or piso(n) is None or abs(piso(n) - piso(c)) > 1.0:
                    continue
                vistos.add(n)
                cola.append((n, camino + [n]))
    raise RuntimeError("no encontre donde se seque")


# ------------------------------------------------------------------------------------------------------------------------------------ rig
PATAS = {
    "trasera": [("shoulder.R", "shin.R", +1), ("shoulder.L", "shin.L", -1)],
    "delantera": [("front_shoulder.R", "front_shin.R", -1), ("front_shoulder.L", "front_shin.L", +1)],
}


def probar_signos(rig):
    """signo del eje X de cada hueso: +1 si girar +X lleva la punta hacia delante (+Y del armature)"""
    signos = {}
    pb = rig.pose.bones
    guardado = {b.name: tuple(b.rotation_euler) for b in pb}
    for n in ("shoulder.R", "shoulder.L", "front_shoulder.R", "front_shoulder.L", "shin.R", "shin.L", "front_shin.R", "front_shin.L", "scull_1", "tail_1", "ear.R", "ear.L", "spine_4", "spine_6"):
        b = pb[n]
        b.rotation_mode = 'XYZ'
        antes = Vector(b.tail)
        b.rotation_euler = (guardado[n][0] + 0.3, guardado[n][1], guardado[n][2])
        bpy.context.view_layer.update()
        d = Vector(b.tail) - antes
        signos[n] = (1 if d.y >= 0 else -1, 1 if d.z >= 0 else -1, d)
        b.rotation_euler = guardado[n]
    bpy.context.view_layer.update()
    return signos


class Pose:
    """valores de los huesos animados (rotation_euler) de un frame"""
    def __init__(self, signos):
        self.sg = signos
        self.v = {}

    def x(self, n, ang):
        self.v.setdefault(n, [0.0, 0.0, 0.0])[0] = ang

    def z(self, n, ang):
        self.v.setdefault(n, [0.0, 0.0, 0.0])[2] = ang

    def adelante(self, n, ang):
        """gira el hueso para llevar su punta hacia delante `ang` rad (negativo: hacia atras)"""
        self.x(n, ang * self.sg[n][0])


def trote(P, fase, amp=1.0, subida=0.55):
    """ciclo de trote: patas en diagonal (delantera derecha + trasera izquierda a la vez)"""
    for (hombro, rodilla, lado), delantera in ((PATAS["trasera"][0], False), (PATAS["trasera"][1], False), (PATAS["delantera"][0], True), (PATAS["delantera"][1], True)):
        f = fase + (math.pi if (lado > 0) != delantera else 0.0)
        swing = math.sin(f) * 0.55 * amp
        P.adelante(hombro, swing)
        lev = max(0.0, math.cos(f)) * subida * amp                            # la pata se dobla al pasar hacia delante
        P.adelante(rodilla, -lev)


def patas_quietas(P, flex=0.0):
    for hombro, rodilla, _ in PATAS["trasera"] + PATAS["delantera"]:
        P.adelante(hombro, 0.0)
        P.adelante(rodilla, -flex)


def patas_buceo(P, t):
    """de nariz al agua: patas recogidas hacia atras y cola arriba"""
    for hombro, rodilla, _ in PATAS["delantera"]:
        P.adelante(hombro, -0.7 * t)
        P.adelante(rodilla, -0.5 * t)
    for hombro, rodilla, _ in PATAS["trasera"]:
        P.adelante(hombro, 0.5 * t)
        P.adelante(rodilla, -0.6 * t)


# ------------------------------------------------------------------------------------------------------------------------------------ animaciones de Jerry del usuario
# Caminar: SniffingSearchCycle de "animacion_jerry (20).py" (slot_001_caminar). Secarse: "animacion_jerry (19).py" (slot_004_jerry_secandose_FINAL, 60 frames: 5 entrada + 50 sacudida + 5 salida).
# Los valores son los mismos de esos archivos (rotation_euler de cada hueso).
RM_NORMAL = {'leg': 1.0, 'spine': 1.0, 'tail': 1.0, 'head': 1.0, 'ear': 1.0}
RM_RAPIDO = {'leg': 1.35, 'spine': 1.2, 'tail': 1.2, 'head': 1.0, 'ear': 1.0}       # misma formula con mas amplitud (como los estilos RAPIDO / CORRER del archivo)


def _sin(n, periodo, amp, fase=0.0, desp=0.0):
    return amp * math.sin(2 * math.pi * n / periodo + fase) + desp


class CicloCaminata:
    def __init__(self, ciclo=25, rm=None):
        self.c = ciclo
        self.rm = rm or RM_NORMAL

    def n(self, f):
        return ((f - 1) % self.c) + 1

    def pata_swing(self, f, trasera, izq):
        n = self.n(f)
        fase = 0 if izq else math.pi
        amp = (0.4 if trasera else 0.3) * self.rm['leg']
        return (-_sin(n, self.c, amp, fase), -_sin(n, self.c, amp * 0.15, fase), -_sin(n, self.c, amp * 0.03, fase))

    def pata_doblar(self, f, trasera, izq):
        n = self.n(f)
        fase = 0 if izq else math.pi
        bb = (0.3 if trasera else 0.24) * self.rm['leg']
        return (-abs(_sin(n, self.c, bb, fase, bb)), -_sin(n, self.c, 0.1, fase), -_sin(n, self.c, 0.04, fase))

    def pie(self, f, trasera, izq):
        n = self.n(f)
        fase = 0 if izq else math.pi
        ax = (0.8 if trasera else 0.6) * self.rm['leg']
        return (-_sin(n, self.c, ax, fase, 0.4 if trasera else -0.1), abs(_sin(n, self.c, 0.04, fase, 0.02)) * (1.0 if trasera else 0.5),
                -_sin(n, self.c, 0.04 if trasera else 0.06, fase, 0.02))

    def dedos(self, f, trasera, izq):
        n = self.n(f)
        fase = 0 if izq else math.pi
        amp = 0.5 * self.rm['leg']
        return (abs(_sin(n, self.c, amp, fase, 0.4)), -_sin(n, self.c, 0.16, fase), -_sin(n, self.c, 0.08, fase, 0.04))

    def columna(self, f, seg, total=7):
        n = self.n(f)
        return (-_sin(n, self.c, 0.03 * self.rm['spine'], (seg / total) * math.pi, -0.08 * self.rm['spine']), 0, 0)

    def cola(self, f):
        n = self.n(f)
        t = self.rm['tail']
        return (_sin(n, self.c, 0.4 * t, 0, 0.2 * t), _sin(n, self.c, 0.06 * t), _sin(n, self.c, 0.16 * t))

    def cabeza(self, f):
        n = self.n(f)
        h = self.rm['head']
        sniff = (_sin(n, self.c, 0.03 * h), 0, 0)
        mira = (0, _sin(n, self.c, 0.05 * h), 0)
        tilt = (0, 0, _sin(n, self.c, 0.016 * h))
        return (sniff[0] + tilt[0] * 0.3, mira[1], tilt[2])

    def orejas(self, f):
        n = self.n(f)
        e = self.rm['ear']
        return (0, _sin(n, self.c, 0.2 * e), _sin(n, self.c, 0.1 * e))


def caminar(P, f, ciclo=25, rm=None, escala=1.0):
    """pone en P los huesos del ciclo de caminata del usuario (slot_001_caminar) en el cuadro f del ciclo; `escala` apaga el movimiento (frenado)"""
    c = CicloCaminata(ciclo, rm)

    def pon(n, v):
        P.v[n] = [x * escala for x in v]
    for lado, izq in (("L", True), ("R", False)):
        pon(f"shoulder.{lado}", c.pata_swing(f, True, izq))
        P.v[f"thigh.{lado}"] = [x * (0.01 if izq else -0.3) * escala for x in c.pata_swing(f, True, izq)]
        pon(f"shin.{lado}", c.pata_doblar(f, True, izq))
        pon(f"foot.{lado}", c.pie(f, True, izq))
        pon(f"toe.{lado}", c.dedos(f, True, izq))
        pon(f"front_shoulder.{lado}", c.pata_swing(f + 12, False, izq))
        P.v[f"front_thigh.{lado}"] = [x * (0.6 if izq else 0.4) * escala for x in c.pata_swing(f + 12, False, izq)]
        pon(f"front_shin.{lado}", c.pata_doblar(f + 12, False, izq))
        pon(f"front_foot.{lado}", c.pie(f + 12, False, izq))
        pon(f"front_toe.{lado}", c.dedos(f + 12, False, izq))
    for i in range(1, 8):
        pon(f"spine_{i}", c.columna(f, i))
    for i in range(1, 4):
        pon(f"tail_{i}", c.cola(f))
    pon("scull", c.cabeza(f))
    P.v["jaw_top"] = [0.224, 0, 0]
    pon("ear.L", c.orejas(f))
    pon("ear.R", c.orejas(f + 6))


# --- secarse (slot_004_jerry_secandose_FINAL): sacudida de la columna, cabeza, orejas, mandibula y cola; las patas no llevan llaves
def _momentum(t):
    if t < 0.2:
        return t / 0.2
    if t < 0.8:
        return 1.0
    return (1.0 - t) / 0.2


def _sacudida_columna(f, seg):
    t = f / 50.0
    m = _momentum(t)
    ciclos = t * 7 * 2 * math.pi
    amp = {6: 0.25, 7: 0.45, 5: 0.70, 4: 0.60, 3: 0.50, 2: 0.40, 1: 0.30}.get(seg, 0.5)
    return (math.sin(ciclos * 0.3) * 0.06 * amp * m, math.sin(ciclos * 0.5) * 0.12 * amp * m, math.sin(ciclos) * 0.45 * amp * m)


def _sacudida_cabeza(f, scull):
    t = f / 50.0
    m = _momentum(t)
    h = t * 5 * 2 * math.pi
    inten = 0.30 if scull else 0.40
    return (math.sin(h * 0.5) * 0.06 * m * inten, math.sin(h * 0.7) * 0.09 * m * inten, math.sin(h) * 0.275 * m * inten)


def _sacudida_orejas(f, lado):
    t = f / 50.0
    m = _momentum(t)
    c = t * 15 * 2 * math.pi
    off = 0 if lado == 'R' else math.pi * 0.3
    return (math.sin(c * 0.6 + off) * 0.15 * m, math.cos(c + off) * 0.35 * m, math.sin(c + off) * 0.65 * m)


def _sacudida_cola(f, seg):
    t = f / 50.0
    m = _momentum(t)
    c = t * 9 * 2 * math.pi
    amp = {1: 0.40, 2: 0.60, 3: 0.80}.get(seg, 0.6)
    return (math.sin(c * 0.5) * 0.18 * amp * m, math.sin(c * 0.7) * 0.35 * amp * m, math.sin(c) * 0.55 * amp * m)


def _fase_secado(frame):
    """(fase, frame relativo) del slot de 60 frames"""
    if frame <= 5:
        return 'entry', frame
    if frame <= 55:
        return 'main', frame - 5
    return 'exit', frame - 55


def secarse(P, frame):
    """huesos del frame (1..60) de la animacion de secarse del usuario"""
    fase, af = _fase_secado(frame)
    fac = 1.0 if fase == 'main' else ((frame - 1) / 4.0 if fase == 'entry' else (60 - frame) / 4.0)

    def pon(n, v):
        P.v[n] = [x * fac for x in v]
    for seg in range(1, 8):
        pon(f"spine_{seg}", _sacudida_columna(af, seg))
    pon("scull_1", _sacudida_cabeza(af, False))
    pon("scull", _sacudida_cabeza(af, True))
    pon("ear.R", _sacudida_orejas(af, 'R'))
    pon("ear.L", _sacudida_orejas(af, 'L'))
    mj = _momentum(af / 50.0)
    pon("jaw_bot", (-0.08 * mj, 0, 0))
    pon("jaw_top", (0, 0, 0))
    for seg in range(1, 4):
        pon(f"tail_{seg}", _sacudida_cola(af, seg))
    for hombro, rodilla, _ in PATAS["trasera"] + PATAS["delantera"]:                   # las patas quedan quietas (sin llaves en el original)
        P.v[hombro] = [0.0, 0.0, 0.0]
        P.v[rodilla] = [0.0, 0.0, 0.0]


# ------------------------------------------------------------------------------------------------------------------------------------ trayectoria
def rot_cuerpo(rumbo, cabeceo, alabeo=0.0):
    """rumbo: angulo del frente respecto a +X (rad); cabeceo: + sube el hocico, - lo baja; alabeo sobre el eje largo"""
    return Matrix.Rotation(rumbo - math.pi / 2, 3, 'Z') @ Matrix.Rotation(cabeceo, 3, 'X') @ Matrix.Rotation(alabeo, 3, 'Y')


def raiz_desde_com(com, R):
    return Vector(com) - R @ (C_LOCAL * S)


def segmentos_camino(puntos, v):
    """[(p0, p1, longitud, rumbo)] y frames que tarda cada tramo a velocidad v"""
    res = []
    for a, b in zip(puntos, puntos[1:]):
        d = Vector((b[0] - a[0], b[1] - a[1]))
        res.append((Vector(a), Vector(b), d.length, math.atan2(d.y, d.x)))
    return res


def construir():
    mundo = Mundo()
    rig = bpy.data.objects[RIG]
    signos = probar_signos(rig)
    zs = zona_seca(mundo)
    datos = []              # (frame, loc, quat, {hueso: (x, y, z)}, ojos...)

    def anade(f, com_o_raiz, R, P, es_com=True):
        loc = raiz_desde_com(com_o_raiz, R) if es_com else Vector(com_o_raiz)
        datos.append((f, loc, R.to_quaternion(), {n: tuple(v) for n, v in P.v.items()}))

    # ---- 1) trote por la superficie hasta el borde, agachada y salto
    segs = segmentos_camino(PUNTOS, V_TROTE)
    largo = sum(s[2] for s in segs)
    f_parada = F_BAJA - 8 - ESPERA_BORDE                                                         # llega al borde 8 frames antes de saltar (frenada + agachada)
    f_ini = f_parada - int(round(largo / V_TROTE * FPS))
    rumbo_final = segs[-1][3]
    z_ant = mundo.pasto(*PUNTOS[0])
    P = Pose(signos)
    for f in range(f_ini, f_parada + 1):
        d = (f - f_ini) / FPS * V_TROTE                                          # distancia recorrida
        acum = 0.0
        for a, b, L, rb in segs:
            if d <= acum + L or (a, b, L, rb) == segs[-1]:
                u = min(1.0, (d - acum) / L)
                p = a + (b - a) * u
                rumbo = rb
                break
            acum += L
        if f < f_ini + 6:                                                          # arranque: gira hacia el primer tramo
            rumbo = lerp(segs[0][3], rumbo, 1.0)
        z_s = mundo.pasto(p.x, p.y, 8.0)
        z_ant = lerp(z_ant, z_s, 0.35)
        P = Pose(signos)
        fr = min(1.0, (f_parada - f) / 6.0)                                        # frena en los ultimos 6 frames
        caminar(P, f - f_ini + 1, 14, RM_RAPIDO, 0.4 + 0.6 * fr)                  # caminata del usuario (slot_001_caminar), ciclo corto y mas amplitud para ir a 3.4 m/s
        bob = 0.05 * abs(math.sin((f - f_ini) / FPS * 2 * math.pi * 2.4)) * fr
        R = rot_cuerpo(rumbo, 0.0)
        raiz = Vector((p.x, p.y, z_ant + bob))
        anade(f, raiz, R, P, es_com=False)
    # agachada
    p_borde = Vector((BORDE[0], BORDE[1], mundo.pasto(BORDE[0], BORDE[1], 8.0)))
    for f in range(f_parada + 1, F_BAJA + 1):
        t = max(0.0, (f - (F_BAJA - 8)) / 8.0)
        P = Pose(signos)
        patas_quietas(P, flex=0.5 * suave(t))
        for hombro, rodilla, _ in PATAS["trasera"]:
            P.adelante(hombro, -0.3 * suave(t))
        R = rot_cuerpo(rumbo_final, 0.0)
        anade(f, Vector((p_borde.x, p_borde.y, p_borde.z - 0.12 * suave(t))), R, P, es_com=False)

    # ---- 2) salta al hueco y baja por la columna de agua con rotaciones (0, 0, 0): sin girar ni cabecear, cae de pie (arrastre del agua: velocidad limite)
    com = Vector((p_borde.x, p_borde.y, p_borde.z + C_LOCAL.z * S - 0.12))
    ox, oy = HOYO
    dirh = Vector((ox - com.x, oy - com.y, 0)).normalized()
    v = Vector((dirh.x * 3.2, dirh.y * 3.2, 2.8))
    f = F_BAJA
    z_pie = -10.0 + C_LOCAL.z * S                                                 # centro del cuerpo cuando esta de pie sobre el fondo del charco
    R0 = Matrix.Identity(3)                                                       # rotaciones 0, 0, 0
    centrado = False
    f_choque = None
    while f < F_BAJA + 400:
        f += 1
        dt = 1.0 / FPS
        v.z -= G * dt
        if centrado:
            v.x = v.y = 0.0
            v.z = max(v.z, -V_AGUA)
        elif Vector((ox - com.x, oy - com.y)).length < v.xy.length * dt:
            com.x, com.y = ox, oy
            centrado = True
            v.x = v.y = 0.0
        com += v * dt
        P = Pose(signos)
        patas_quietas(P, flex=0.1)
        for hombro, rodilla, _ in PATAS["delantera"]:
            P.adelante(hombro, 0.25)
        if centrado and com.z <= z_pie:
            f_choque = f
            com_choque = Vector((com.x, com.y, z_pie))
            v_in = -v.z
            anade(f, com_choque, R0, P)
            break
        anade(f, com, R0, P)
    # ---- 3) rebota en el agua (sube y cae de pie), siempre con rotacion 0
    t_reb = 14
    v0 = min(0.45 * v_in, 3.2)
    for k in range(1, t_reb + 4):
        f_k = f_choque + k
        t = k / FPS
        zc = max(com_choque.z + v0 * t - 0.5 * G * t * t, z_pie)
        P = Pose(signos)
        flex = 0.45 * math.exp(-k / 3.0) if zc <= z_pie + 0.01 else 0.0
        patas_quietas(P, flex=0.1 + flex)
        anade(f_k, Vector((ox, oy, zc)), R0, P)
    f_aterriza = f_choque + t_reb + 3
    cab = 0.0
    # ---- 4) vadea hasta el borde del charco, salta al suelo seco y trota hasta donde se sacude
    mx, my = zs["mojada"][0] + 0.5, zs["mojada"][1] + 0.5
    camino = zs["camino"]
    (c0, z0) = camino[0]
    sx, sy = c0[0] + 0.5, c0[1] + 0.5
    rumbo_final = math.pi / 2                                                        # hasta aqui miraba a +Y (rotacion 0)
    rumbo2 = math.atan2(my - oy, mx - ox) if math.hypot(mx - ox, my - oy) > 1e-6 else rumbo_final
    dist = math.hypot(mx - ox, my - oy)
    n_vadeo = max(1, int(round(dist / V_VADEO * FPS)))
    f = f_aterriza
    for k in range(1, n_vadeo + 1):
        f += 1
        u = k / n_vadeo
        P = Pose(signos)
        caminar(P, k, 25, RM_NORMAL, 0.9)
        R = rot_cuerpo(lerp_ang(rumbo_final, rumbo2, suave(min(1.0, k / 6))), 0.0)
        zc = z_pie + 0.04 * abs(math.sin(k / FPS * 2 * math.pi * 1.8))
        anade(f, Vector((lerp(ox, mx, u), lerp(oy, my, u), zc)), R, P)
    f_borde = f
    rumbo3 = math.atan2(sy - my, sx - mx)
    n_salto = 12
    z_ini = z_pie
    for k in range(1, n_salto + 1):                                                  # salto del charco al suelo seco
        f += 1
        u = k / n_salto
        P = Pose(signos)
        t_air = math.sin(math.pi * u)
        for hombro, rodilla, _ in PATAS["delantera"]:
            P.adelante(hombro, 0.6 * t_air)
            P.adelante(rodilla, -0.3 * t_air)
        for hombro, rodilla, _ in PATAS["trasera"]:
            P.adelante(hombro, -0.5 * t_air)
            P.adelante(rodilla, -0.5 * t_air)
        R = rot_cuerpo(lerp_ang(rumbo2, rumbo3, u), 0.25 * math.sin(math.pi * u) - 0.15 * u)
        zc = lerp(z_ini, z0 + C_LOCAL.z * S, u) + 0.9 * 4 * u * (1 - u)
        anade(f, Vector((lerp(mx, sx, u), lerp(my, sy, u), zc)), R, P)
    puntos = [(sx, sy)] + [(c[0] + 0.5, c[1] + 0.5) for c, _ in camino[1:]]
    zs_c = [z for _, z in camino]
    rumbo_f = rumbo3
    for (ax, ay), (bx, by), za, zb in zip(puntos, puntos[1:], zs_c, zs_c[1:]):      # trota por el camino seco
        rumbo_f = math.atan2(by - ay, bx - ax)
        n = max(1, int(round(math.hypot(bx - ax, by - ay) / 2.5 * FPS)))
        for k in range(1, n + 1):
            f += 1
            u = k / n
            P = Pose(signos)
            caminar(P, k, 18, RM_NORMAL, 1.0)
            R = rot_cuerpo(lerp_ang(rumbo3, rumbo_f, suave(min(1.0, k / 4))), 0.0)
            anade(f, Vector((lerp(ax, bx, u), lerp(ay, by, u), lerp(za, zb, u) + C_LOCAL.z * S)), R, P)
        rumbo3 = rumbo_f
    sx, sy = puntos[-1]
    z_seca = zs_c[-1] + C_LOCAL.z * S
    f_seco = f
    # ---- 5) se seca con la animacion del usuario (slot_004_jerry_secandose_FINAL, 60 frames), sin mover el root
    for k in range(1, 61):
        P = Pose(signos)
        secarse(P, k)
        anade(f_seco + k, Vector((sx, sy, z_seca)), rot_cuerpo(rumbo3, 0.0), P)
    n_sac = 60
    for k in range(1, 13):                                                          # queda quieto un momento
        anade(f_seco + n_sac + k, Vector((sx, sy, z_seca)), rot_cuerpo(rumbo3, 0.0), Pose(signos))
    for k in range(1, DEMORA_RUTA + 1):                                             # espera a que Alfred termine de plantar la antorcha
        anade(f_seco + n_sac + 12 + k, Vector((sx, sy, z_seca)), rot_cuerpo(rumbo3, 0.0), Pose(signos))
    # ---- 6) despues de secarse: camina por el recorrido jerry_ruta_a.json (de su sitio hasta Alfred), mira a Alfred y le tira el cubo
    import json as _json
    with open(RUTA_JSON, encoding="utf8") as fh:
        ruta = [(p["coordinates"]["x"], p["coordinates"]["y"], p["coordinates"]["z"]) for p in _json.load(fh)["key_points"]]
    sc_ = bpy.context.scene
    guardado = sc_.frame_current
    sc_.frame_set(F_ALFRED_DE_PIE)
    bpy.context.view_layer.update()
    arm_a = bpy.data.objects["Armature"]
    alfred_xy = Vector((arm_a.matrix_world @ arm_a.pose.bones["Hips_alfred"].head)[:2])        # eje del cuerpo de Alfred de pie
    z_alfred = ruta[-1][2]                                                                      # el suelo donde esta (cara superior del bloque)
    sc_.frame_set(guardado)
    f = datos[-1][0]
    rumbo = rumbo3
    pasos = 0
    for (ax, ay, az), (bx, by, bz) in zip(ruta, ruta[1:]):
        rb = math.atan2(by - ay, bx - ax)
        n = max(1, int(round(math.hypot(bx - ax, by - ay) / V_RUTA * FPS)))
        for k in range(1, n + 1):
            f += 1
            pasos += 1
            u = k / n
            P = Pose(signos)
            caminar(P, pasos, CICLO_RUTA, RM_RAPIDO, 1.0)
            anade(f, Vector((lerp(ax, bx, u), lerp(ay, by, u), lerp(az, bz, u))), rot_cuerpo(lerp_ang(rumbo, rb, suave(min(1.0, k / 8))), 0.0), P, es_com=False)
        rumbo = rb
    px, py, pz = ruta[-1]
    rumbo_a = math.atan2(alfred_xy.y - py, alfred_xy.x - px)
    for k in range(1, 9):                                                                      # frena y se gira hacia Alfred
        f += 1
        pasos += 1
        P = Pose(signos)
        caminar(P, pasos, CICLO_RUTA, RM_RAPIDO, 1.0 - suave(k / 8))
        anade(f, Vector((px, py, pz)), rot_cuerpo(lerp_ang(rumbo, rumbo_a, suave(k / 8)), 0.0), P, es_com=False)
    for k in range(1, 5):                                                                      # un momento quieto mirandolo
        f += 1
        anade(f, Vector((px, py, pz)), rot_cuerpo(rumbo_a, 0.0), Pose(signos), es_com=False)
    sz = signos["scull_1"][1]                                                                  # signo: + sube el hocico
    f_lanza0 = f
    N_LANZA = 16
    for k in range(1, N_LANZA + 1):                                                            # tiro: baja la cabeza (carga), la sube de golpe y suelta el cubo
        f += 1
        P = Pose(signos)
        if k <= 6:
            u = suave(k / 6)
            P.x("scull_1", -0.55 * u * sz)
            P.x("spine_3", -0.15 * u * sz)
        elif k <= 9:
            u = suave((k - 6) / 3)
            P.x("scull_1", (-0.55 + 1.05 * u) * sz)
            P.x("spine_3", (-0.15 + 0.3 * u) * sz)
        else:
            u = suave((k - 9) / 7)
            P.x("scull_1", 0.5 * (1 - u) * sz)
            P.x("spine_3", 0.15 * (1 - u) * sz)
        P.x("jaw_bot", -0.55 if 8 <= k <= 11 else 0.0)                                         # abre la boca al soltarlo
        anade(f, Vector((px, py, pz)), rot_cuerpo(rumbo_a, 0.0), P, es_com=False)
    f_rel = f_lanza0 + 8
    for k in range(1, 101):                                                                    # se queda mirando, moviendo la cola (mientras el cubo termina de rebotar y se asienta)
        f += 1
        P = Pose(signos)
        P.z("tail_1", 0.4 * math.sin(2 * math.pi * 2.2 * k / FPS))
        P.z("tail_2", 0.4 * math.sin(2 * math.pi * 2.2 * k / FPS - 0.8))
        anade(f, Vector((px, py, pz)), rot_cuerpo(rumbo_a, 0.0), P, es_com=False)
    ruta_info = dict(f_ruta_ini=f_seco + 73 + DEMORA_RUTA, f_lanza=f_lanza0, f_rel=f_rel, alfred_xy=(round(alfred_xy.x, 3), round(alfred_xy.y, 3)), z_suelo=z_alfred, rumbo_a=rumbo_a)
    info = dict(f_ini=f_ini, f_parada=f_parada, f_baja=F_BAJA, f_choque=f_choque, f_aterriza=f_aterriza, f_borde=f_borde, f_seco=f_seco, f_fin=datos[-1][0],
                seca=(round(sx - 0.5), round(sy - 0.5)), mojada=zs["mojada"])
    info.update(ruta_info)
    return info, datos


def lerp_ang(a, b, t):
    d = (b - a + math.pi) % (2 * math.pi) - math.pi
    return a + d * t


# ------------------------------------------------------------------------------------------------------------------------------------ escena
def preparar_cubo(rig):
    """trae bucket.blend si no esta; devuelve (objeto, matriz relativa a la mandibula)"""
    b = bpy.data.objects.get(BUCKET)
    if b is None:
        with bpy.data.libraries.load(r"C:\Users\user\Desktop\Alfred_Animacion\objetos\vanilla\bucket\bucket.blend", link=False) as (src, dst):
            dst.objects = ["bucket"]
        b = dst.objects[0]
        b.name = BUCKET
        bpy.context.scene.collection.objects.link(b)
    # el cubo cuelga de los dientes: centro 0.2 por debajo de la punta del hocico, lamina vertical vista de lado (normal = +X del armature)
    desired = Matrix(((0, 0, 1, 0), (1, 0, 0, 0.70), (0, 1, 0, 0.42 - 0.20), (0, 0, 0, 1)))                    # columnas: X-> +Y, Y-> +Z, Z-> +X  (con traslacion en la ultima columna)
    desired = Matrix(((0, 0, 1, 0.0), (1, 0, 0, 0.70), (0, 1, 0, 0.22), (0, 0, 0, 1)))
    desired = desired @ Matrix.Scale(0.5, 4)
    jaw = rig.data.bones["jaw_bot"].matrix_local
    return b, jaw.inverted() @ desired


def simular_cubo(M0, alfred_xy, z_suelo, n_frames, derecha=None, suelo_fn=None, radio=0.38, alto=1.9, e_cuerpo=0.45):
    """el cubo sale de la boca de Jerry (matriz M0) hacia el pecho de Alfred (vuelo balistico), rebota en su cuerpo (cilindro vertical), cae con rebotes y queda plano en el suelo.
    Devuelve (matrices por frame, indice del frame del golpe)"""
    import random
    rnd = random.Random(3)
    l0, q0, esc = M0.decompose()
    p = Vector(l0)
    eje = Vector((alfred_xy[0], alfred_xy[1]))
    T = Vector((alfred_xy[0], alfred_xy[1], z_suelo + 1.25))
    tf = 0.30
    v = (T - p) / tf + Vector((0, 0, 0.5 * G * tf))
    q = Quaternion(q0)
    w = Vector((0, 0, 0))
    golpeado, f_golpe = False, None
    sub = 8
    dt = 1.0 / (FPS * sub)
    salida = [M0.copy()]
    quieto = 0
    plano = None
    for k in range(1, n_frames + 1):
        for _ in range(sub):
            if plano is None:
                v.z -= G * dt
                p += v * dt
                if w.length > 1e-6:
                    q = Quaternion(w.normalized(), w.length * dt) @ q
                rel = Vector((p.x - eje.x, p.y - eje.y))
                if (not golpeado) and rel.length <= radio and z_suelo <= p.z <= z_suelo + alto:
                    n = rel.normalized() if rel.length > 1e-6 else Vector((-v.x, -v.y)).normalized()
                    n3 = Vector((n.x, n.y, 0))
                    vn = v.dot(n3)
                    if vn < 0:
                        v = v - (1 + e_cuerpo) * vn * n3
                        v.x *= 0.9
                        v.y *= 0.9
                        if derecha is not None:                                            # rebota hacia la DERECHA de Jerry (un poco hacia atras y hacia arriba)
                            lat = 1.6
                            v = Vector((derecha.x * lat + n.x * 0.6, derecha.y * lat + n.y * 0.6, max(v.z, 0.0) + 1.1))
                    p.x, p.y = eje.x + n.x * (radio + 0.01), eje.y + n.y * (radio + 0.01)
                    w = Vector((rnd.uniform(-9, 9), rnd.uniform(-9, 9), rnd.uniform(-9, 9)))
                    golpeado, f_golpe = True, k
                zg = suelo_fn(p.x, p.y) if suelo_fn else z_suelo
                if p.z < zg + 0.18 and v.z < 0:
                    p.z = zg + 0.18
                    v.z = -v.z * 0.4 if v.z < -0.6 else 0.0
                    v.x *= 0.7
                    v.y *= 0.7
                    w *= 0.6
                    if abs(v.z) < 0.1 and v.length < 0.4:
                        quieto += 1
                if quieto > 1:
                    plano = k
                    yaw = Quaternion(q).to_euler().z
                    q_plano = Quaternion((0, 0, 1), yaw)
                    q_ini = Quaternion(q)
                    k_plano = k
        if plano is not None:
            u = suave((k - k_plano) / 6.0)
            q_k = q_ini.slerp(q_plano, u)
            p.z = lerp(zg + 0.18, zg + 0.03, u)
            salida.append(Matrix.LocRotScale(p.copy(), q_k, esc))
        else:
            salida.append(Matrix.LocRotScale(p.copy(), Quaternion(q), esc))
    return salida, f_golpe


def hornear(info, datos, f0=None):
    sc = bpy.context.scene
    obj = bpy.data.objects
    root, rig = obj[ROOT], obj[RIG]
    cubo, rel = preparar_cubo(rig)
    for ob in (root, rig, cubo):
        if ob.animation_data:
            ob.animation_data_clear()
        ob.hide_viewport = False
        ob.hide_render = False
    for ch in root.children_recursive:
        ch.hide_viewport = False
        ch.hide_render = False
    root.rotation_mode = 'QUATERNION'
    cubo.rotation_mode = 'QUATERNION'
    for n in {n for d in datos for n in d[3]}:
        rig.pose.bones[n].rotation_mode = 'XYZ'
    animados = sorted({n for d in datos for n in d[3]})
    f_rel = info.get("f_rel")
    mats_cubo = None
    for f, loc, q, bones in datos:
        root.location = loc
        root.rotation_quaternion = q
        for n in animados:
            rig.pose.bones[n].rotation_euler = bones.get(n, (0, 0, 0))
        bpy.context.view_layer.update()
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_quaternion", frame=f)
        for n in animados:
            rig.pose.bones[n].keyframe_insert("rotation_euler", frame=f)
        Mw = rig.matrix_world @ rig.pose.bones["jaw_bot"].matrix @ rel
        if f_rel and f == f_rel:                                                           # lo suelta: desde aqui el cubo vuela y rebota en Alfred
            ra = info["rumbo_a"]
            mundo = Mundo()
            mats_cubo, f_golpe = simular_cubo(Mw, info["alfred_xy"], info["z_suelo"], datos[-1][0] - f_rel, derecha=Vector((math.sin(ra), -math.cos(ra))), suelo_fn=lambda x, y: mundo.suelo(x, y, desde=-4))
            info["f_golpe"] = f_rel + f_golpe if f_golpe else None
        elif f_rel and f > f_rel and mats_cubo is not None:
            Mw = mats_cubo[f - f_rel]
        l, qq, s = Mw.decompose()
        cubo.location, cubo.rotation_quaternion, cubo.scale = l, qq, s
        cubo.keyframe_insert("location", frame=f)
        cubo.keyframe_insert("rotation_quaternion", frame=f)
        cubo.keyframe_insert("scale", frame=f)
    root["jerry_agua"] = json_info(info)
    sc.frame_set(sc.frame_current)
    return info


def json_info(info):
    import json
    return json.dumps({k: (list(v) if isinstance(v, tuple) else v) for k, v in info.items()})
