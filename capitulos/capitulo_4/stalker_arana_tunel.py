# -*- coding: utf-8 -*-
"""alfred_cueva_5.blend: el Stalker (the_stalker_1, mide ~2.9 m) esta al fondo del tunel de 1x2. Tras F_INI se contorsiona a sacudidas
(como Samara saliendo de la tele en El Aro) hasta quedar en cuatro patas como una arana, cabe en el tunel (todo por debajo de 2 m) y
avanza AVANCE bloques hacia +Y: primero lento y cada vez mas rapido. Al pasar junto a cada antorcha del tunel, esta parpadea y se apaga.
Pose por "direcciones": cada hueso apunta su geometria a una direccion (espacio del armature, +Y = adelante, +Z = arriba).
Uso: exec(open(ruta, encoding="utf8").read()); construir()      (repetible)
"""
import bpy, math, random
from mathutils import Vector, Matrix, Quaternion

RAIZ, RIG = "the_stalker_1", "torso_1"
Y0 = -96.5                    # donde lo puso el usuario (fondo del tunel)
F_INI = 61                    # empieza a contorsionarse (antes esta a oscuras)
F_CONTORSION = 30             # frames de la contorsion
F_ANDAR = 170                 # frames del avance
AVANCE = 30.0                 # bloques hacia +Y
ZANCADA = 0.9                 # m de avance por ciclo de pasos
SEMILLA = 7
ANTORCHAS = "antorcha_tunel5_"

# --- pose de arana (direcciones de la geometria de cada hueso; los huesos de este rig apuntan hacia arriba, las extremidades cuelgan
#     hacia -Y del hueso)
BAJA_CADERA = 0.86            # muy agachado (cadera de 1.22 a 0.36) para poder ir con el torso erguido en 2 m de alto
ARANA = {
    "spine_1": (0, 0.42, 0.91), "chest_1": (0, 0.3, 0.95), "neck_1": (0, 0.9, 0.42), "head_1": (0.2, 0.55, 0.8),   # torso erguido: se ve el pecho
    "thigh.L_1": (-0.12, 0.85, 0.5), "thigh.R_1": (0.12, 0.85, 0.5),          # rodillas muy dobladas hacia delante
    "shin.L_1": (0.06, -0.5, -0.86), "shin.R_1": (-0.06, -0.5, -0.86),
    "upper_arm.L_1": (-0.14, 0.45, 0.88), "upper_arm.R_1": (0.14, 0.45, 0.88),  # codos hacia las paredes
    "forearm.L_1": (-0.04, 0.8, -0.6), "forearm.R_1": (0.04, 0.8, -0.6),        # garras contra la pared, por delante
}
ROLL_CABEZA = math.radians(35)    # la cabeza ladeada
CUELGA = {"thigh.L_1", "thigh.R_1", "shin.L_1", "shin.R_1", "upper_arm.L_1", "upper_arm.R_1", "forearm.L_1", "forearm.R_1"}
ORDEN = ["root_1", "spine_1", "chest_1", "neck_1", "head_1", "neck_front_1", "thigh.L_1", "shin.L_1", "thigh.R_1", "shin.R_1",
         "upper_arm.L_1", "forearm.L_1", "upper_arm.R_1", "forearm.R_1"]
# andar ASIMETRICO: cada extremidad con su fase, su amplitud y su forma de empuje (los brazos empujan contra la pared)
PASO = {  # fase, amplitud (rad), parte del ciclo empujando
    "upper_arm.L_1": (0.0, 0.3, 0.3), "upper_arm.R_1": (0.41, 0.24, 0.42),
    "thigh.L_1": (0.63, 0.32, 0.55), "thigh.R_1": (0.17, 0.4, 0.5),
}


def empuje(t, parte):
    """ciclo asimetrico 0..1 -> (barrido -1..1, levantado 0..1): empuja hacia atras rapido (parte del ciclo) y vuelve adelante levantado"""
    t %= 1.0
    if t < parte:
        u = t / parte; return 1 - 2 * (u * u * (3 - 2 * u)), 0.0
    u = (t - parte) / (1 - parte); return -1 + 2 * (u * u * (3 - 2 * u)), math.sin(math.pi * u)


def suave(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def _rest_dir(b):
    d = (b.tail_local - b.head_local).normalized()
    return -d if b.name in CUELGA else d


def _girar(v, eje, ang): return Quaternion(eje, ang) @ v


def pose(rig, w, fase, t_twitch, rnd_twitch):
    """matrices (espacio armature) mezclando reposo -> arana erguida con peso w; fase = ciclo de pasos; t_twitch = tic de cabeza"""
    bones = rig.data.bones; out = {}
    balanceo = 0.1 * math.sin(2 * math.pi * fase + 0.7) + 0.05 * math.sin(2 * math.pi * fase * 2.3)   # el cuerpo se ladea irregular
    for n in ORDEN:
        b = bones[n]; R = b.matrix_local
        if n == "neck_front_1" and "head_1" in out:               # la pieza de la mandibula de abajo va con la cabeza (no se desubica)
            out[n] = out["head_1"] @ bones["head_1"].matrix_local.inverted() @ R; continue
        if b.parent and b.parent.name in out:
            base = out[b.parent.name] @ b.parent.matrix_local.inverted() @ R
        else:
            base = R.copy()
        head = base.to_translation(); rot = base.to_3x3()
        if n == "root_1":
            out[n] = Matrix.Translation(Vector((0, 0, -BAJA_CADERA * w))) @ base; continue
        if n in ARANA:
            g = (rot @ (Vector((0, -1, 0)) if n in CUELGA else Vector((0, 1, 0)))).normalized()
            obj = Vector(ARANA[n]).normalized()
            if n == "spine_1" and w > 0.99: obj = _girar(obj, Vector((0, 1, 0)), balanceo)
            if n in PASO and w > 0.99:
                f0, amp, parte = PASO[n]; barrido, alto = empuje(fase + f0, parte)
                if n.startswith("upper"):                          # brazo: alcanza la pared adelante, empuja hacia atras, se suelta
                    obj = _girar(obj, Vector((0, 0, 1)), amp * barrido * (1 if n.endswith(".L_1") else -1))
                    obj = (obj + Vector((0, 0, 0.5 * alto))).normalized()
                else:                                              # pierna: avanza levantando la rodilla
                    obj = _girar(obj, Vector((1, 0, 0)), -amp * barrido)
                    obj = (obj + Vector((0, 0, 0.3 * alto))).normalized()
            reposo = (R.to_3x3() @ (Vector((0, -1, 0)) if n in CUELGA else Vector((0, 1, 0)))).normalized()
            dest = reposo.lerp(obj, w).normalized()
            q = g.rotation_difference(dest); rot = q.to_matrix() @ rot
            if n == "head_1":
                rot = Quaternion(dest, ROLL_CABEZA * w + t_twitch).to_matrix() @ rot
        out[n] = Matrix.LocRotScale(head, rot.to_quaternion(), None)
    return out


def aplicar(rig, mats, f):
    for n in ORDEN:
        b = rig.data.bones[n]; pb = rig.pose.bones[n]
        base = (mats[b.parent.name] @ b.parent.matrix_local.inverted() @ b.matrix_local) if b.parent and b.parent.name in mats else b.matrix_local
        basis = base.inverted() @ mats[n]
        pb.rotation_mode = 'QUATERNION'; l, q, _ = basis.decompose(); pb.location = l; pb.rotation_quaternion = q
        pb.keyframe_insert("location", frame=f, group=n); pb.keyframe_insert("rotation_quaternion", frame=f, group=n)


def contorsion(t):
    """0..1 a sacudidas: avanza a golpes con pausas y algun retroceso (como Samara)"""
    golpes = [(0.0, 0.0), (0.12, 0.0), (0.18, 0.3), (0.3, 0.3), (0.34, 0.22), (0.4, 0.55), (0.55, 0.55), (0.6, 0.8), (0.72, 0.8), (0.76, 1.05), (0.85, 0.97), (1.0, 1.0)]
    for (a, va), (b, vb) in zip(golpes, golpes[1:]):
        if a <= t <= b: return va + (vb - va) * suave((t - a) / (b - a)) ** 0.5
    return 1.0


def distancia(u):
    return AVANCE * (0.12 * u + 0.88 * u * u)                      # lento al principio, cada vez mas rapido


def _limpiar_claves(rig):
    ad = rig.animation_data
    if not ad or not ad.action: return
    for lay in ad.action.layers:
        for st in lay.strips:
            for cb in st.channelbags:
                for fc in [fc for fc in cb.fcurves if any('"%s"' % n in fc.data_path for n in ORDEN)]: cb.fcurves.remove(fc)


def _antorchas(pasos):
    """cada antorcha del recorrido parpadea y se apaga cuando la cabeza del Stalker pasa a su altura"""
    O = bpy.data.objects; apagadas = []
    for e in sorted([o for o in O if o.name.startswith(ANTORCHAS) and o.parent is None], key=lambda o: o.matrix_world.translation.y):
        y = e.matrix_world.translation.y
        f = next((fr for fr, yc in pasos if yc >= y), None)
        if f is None: continue
        for ch in e.children:
            if ch.animation_data: ch.animation_data_clear()
            if ch.type == 'LIGHT' and ch.data.animation_data: ch.data.animation_data_clear()
        for ch in e.children:
            if ch.type == 'LIGHT':
                E = ch.data.energy if ch.data.energy > 0 else 100.0
                for df, k in ((-6, 1.0), (-5, 0.3), (-4, 1.0), (-2, 0.15), (-1, 0.8), (0, 0.0)):
                    ch.data.energy = E * k; ch.data.keyframe_insert("energy", frame=f + df)
                ch.data.energy = E
                for fc in [fc for lay in ch.data.animation_data.action.layers for s in lay.strips for cb in s.channelbags for fc in cb.fcurves]:
                    for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
            elif "flame" in ch.name or "smoke" in ch.name:                     # la llama y el humo desaparecen
                for fr, h in ((1, False), (f - 4, True), (f - 3, False), (f, True)):
                    ch.hide_render = h; ch.hide_viewport = h; ch.keyframe_insert("hide_render", frame=fr); ch.keyframe_insert("hide_viewport", frame=fr)
                ch.hide_render = ch.hide_viewport = False
        apagadas.append((e.name, round(y, 1), f))
    return apagadas


def construir():
    O = bpy.data.objects; sc = bpy.context.scene; raiz = O[RAIZ]; rig = O[RIG]; rnd = random.Random(SEMILLA)
    if raiz.animation_data: raiz.animation_data_clear()
    _limpiar_claves(rig)
    y0 = Y0; raiz.location.y = Y0; raiz.rotation_mode = 'XYZ'
    # reposo hasta F_INI
    aplicar(rig, pose(rig, 0.0, 0.0, 0.0, rnd), 1); aplicar(rig, pose(rig, 0.0, 0.0, 0.0, rnd), F_INI)
    raiz.keyframe_insert("location", frame=1); raiz.keyframe_insert("location", frame=F_INI)
    twitch = {}
    f_fin = F_INI + F_CONTORSION + F_ANDAR; pasos = []
    for f in range(F_INI + 1, f_fin + 1):
        t = f - F_INI
        if t <= F_CONTORSION:
            w = contorsion(t / F_CONTORSION); d = 0.0
        else:
            w = 1.0; d = distancia((t - F_CONTORSION) / F_ANDAR)
        # tics de la cabeza: giros bruscos de vez en cuando
        if rnd.random() < 0.06: twitch[f] = rnd.uniform(-0.6, 0.6)
        tw = sum(a * math.exp(-(f - fr) / 2.5) for fr, a in twitch.items() if fr <= f)
        fase = d / ZANCADA
        tiron = 0.0 if w < 0.99 else 0.06 * sum(max(0.0, -empuje(fase + PASO[b_][0], PASO[b_][2])[0]) for b_ in ("upper_arm.L_1", "upper_arm.R_1"))
        aplicar(rig, pose(rig, w, fase, tw, rnd), f)
        raiz.location.y = y0 + d + tiron; raiz.keyframe_insert("location", frame=f)
        pasos.append((f, y0 + d + 1.4 * w))                          # la cabeza va ~1.4 m por delante de la raiz
    raiz.location.y = y0
    sc.frame_end = max(sc.frame_end, f_fin + 30)
    apagadas = _antorchas(pasos)
    sc.frame_set(1)
    return {"contorsion": (F_INI, F_INI + F_CONTORSION), "avance": (F_INI + F_CONTORSION, f_fin), "y_final": round(y0 + AVANCE, 2), "antorchas": apagadas}
