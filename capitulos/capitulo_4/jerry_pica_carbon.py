# -*- coding: utf-8 -*-
"""alfred_cueva_4.blend: Jerry pica los dos bloques de carbon (bloque_coal_ore_-83_-11_-10 y bloque_coal_ore_-83_-12_-10) con la animacion de
picar del Jerry Animation Studio (tunel_jerry.LineaJ: levanta la cabeza y la baja de golpe; piedra = 3 golpes) y un pico de piedra propio
sujeto entre los dientes, PERPENDICULAR a la boca (el mango cruzado, de lado a lado, como un perro con un palo). Pica primero el bloque que
tiene delante, se desplaza 1 m de lado y pica el otro. Los bloques se rompen con efecto_romper_bloque.py (grietas y particulas del juego).
Uso: exec(open(ruta, encoding="utf8").read()); construir()      (repetible)
"""
import bpy, math
from mathutils import Vector, Matrix, Euler, Quaternion

TUNEL = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\jerry\refinar\jerry_animation_studio\tunel_jerry.py"
BASE_ALFRED = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_cae_estalagmita.py"
ROMPER = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\efecto_romper_bloque.py"
BLOQUES = ["bloque_coal_ore_-83_-11_-10", "bloque_coal_ore_-83_-12_-10"]
ESC_PICO = 0.6
CFG = dict(ciclo=25, frame_ini=1, frames_golpe=16, frames_por_bloque=22, arco_salto=0.15)
INICIO, RZ_INICIO = (-80.987, -10.5, -10.0), 91.816   # donde lo puso el usuario
PATAS_V = {"front_thigh.L": 0.40, "front_thigh.R": -0.40, "thigh.L": 0.22, "thigh.R": -0.22}   # patas abiertas en V (+Z abre la izquierda)
BAJA_V = 0.0                               # baja la raiz lo que suben las patas al abrirse
CUERPO = {"spine_3": (0.10, 0, 0), "spine_4": (0.10, 0, 0), "spine_5": (0.08, 0, 0), "spine_6": (0.06, 0, 0),
          "thigh.L": (0.12, 0, 0), "thigh.R": (0.12, 0, 0), "front_thigh.L": (-0.10, 0, 0), "front_thigh.R": (-0.10, 0, 0), "tail_1": (-0.15, 0, 0)}   # +impacto / -carga
EMBESTIDA = 0.25                           # m de avance de la raiz por radian de spine_2
NGOL = 4                                # golpes por bloque (al 4.o se rompe y cae el carbon)
JAW_TOP = (12.62, -0.39805, -0.031797)     # grados (valores del usuario)
JAW_BOT = (-23.97, -0.76517, 0.20142)
REL_PICO = [[0.310716, 0.340091, 0.02848, 0.127948], [-0.144332, 0.096044, 0.42774, 0.096868], [0.30926, -0.296869, 0.171011, -0.087825], [0, 0, 0, 1]]   # pico relativo a jaw_top (posicion del usuario)
DIAG = 0.28                                # golpe en diagonal: arriba-un lado -> abajo-el otro
ALFRED = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/alfred_mete_carbon_horno.py"
VUELO = 16                                 # frames del carbon en el aire hasta la cara de Alfred
COAL_BLEND = r"C:\Users\user\Desktop\Alfred_Animacion\objetos\vanilla\coal\coal.blend"


def _ns(ruta, nombre):
    ns = {"__name__": nombre, "__file__": ruta}; exec(open(ruta, encoding="utf8").read(), ns); return ns


def construir():
    T = _ns(TUNEL, "tunel_jerry_local"); A = _ns(BASE_ALFRED, "base_alfred"); sc = bpy.context.scene; O = bpy.data.objects
    root = O["jerry"]; arm = O["Dog_001_rig"]; pb = arm.pose.bones
    (x0, y0, z0), rz = INICIO, RZ_INICIO               # fijo (no se lee de la escena: al re-ejecutar se acumulaba el paso de lado)
    for o in (root, arm):
        if o.animation_data: o.animation_data_clear()
    for k, s_ in (("ALTO", 1), ("IMPACTO", -1)):
        T[k] = dict(T[k])
        for h, v in CUERPO.items(): T[k][h] = tuple(a + b * (-s_) for a, b in zip(T[k].get(h, (0, 0, 0)), v))   # todo el cuerpo acompana
        for h, f_ in (("spine_2", 1.0), ("spine_1", 0.5)):
            T[k][h] = (T[k][h][0], s_ * DIAG * 0.7 * f_, s_ * DIAG * f_)
    L = T["LineaJ"](CFG, T["NB_TODOS"])
    L.ult.update(x=x0, y=y0, z=z0, rz=rz)
    L.reposo(12, x0, y0, z0, rz)
    golpes = {}
    golpes[BLOQUES[0]] = L.picar(x0, y0, z0, rz, bajo=False, ngol=NGOL)
    L.reposo(14, x0, y0, z0, rz)
    y1 = y0 - 1.0
    camina = []; a_ = L.cur
    L.caminar((x0, y0, z0), (x0, y1, z0), rz); camina.append((a_, L.cur - 1))                                      # paso de lado hacia el otro bloque
    L.reposo(8, x0, y1, z0, rz)
    golpes[BLOQUES[1]] = L.picar(x0, y1, z0, rz, bajo=False, ngol=NGOL)
    # --- tira el pico a su derecha
    L.reposo(6, x0, y1, z0, rz)
    girar(L, L.comp(T["CARGA"], {"spine_2": (-0.15, 0, 0)}), 7, x0, y1, z0, rz - 40)
    f_suelta = L.cur - 1
    girar(L, L.comp(T["CARGA"]), 8, x0, y1, z0, rz)
    # --- va rapido al primer carbon, ahi se voltea a Alfred ("Alfred! ... piensa rapido"), vuelve al carbon, lo coge y se voltea para lanzarlo
    c1 = O[BLOQUES[0]].matrix_world.translation; a1 = math.radians(rz); fw = Vector((-math.sin(a1), math.cos(a1), 0))
    x2, y2 = c1.x - fw.x * 0.7, c1.y - fw.y * 0.7
    rzc = math.degrees(math.atan2(-(x2 - x0), y2 - y1))
    a_ = L.cur; L.caminar((x0, y1, z0), (x2, y2, z0), rzc, fpb=12, paso=2); camina.append((a_, L.cur - 1))
    pa = O["alfred"].matrix_world.translation
    rza = math.degrees(math.atan2(-(pa.x - x2), pa.y - y2)); rza = rz + (rza - rz + 180) % 360 - 180
    girar(L, L.comp(T["CARGA"]), 8, x2, y2, z0, rza)
    f_voz = L.cur; L.reposo(36, x2, y2, z0, rza)
    girar(L, L.comp(T["CARGA"]), 7, x2, y2, z0, rz)
    abajo = L.comp(T["RECOGE"]); L.hacia(abajo, 7, x2, y2, z0, rz); f_agarre = L.cur - 1      # coge el carbon rapido
    girar(L, L.comp(T["CARGA"]), 8, x2, y2, z0, rza)
    L.reposo(2, x2, y2, z0, rza)
    # como un disco: tuerce la mitad delantera del cuerpo hacia la izquierda (impulso) y la suelta de golpe hacia la derecha
    carga = {"spine_1": (-0.10, 0, -0.30), "spine_2": (-0.12, 0, -0.35), "spine_3": (0, 0, -0.30), "spine_4": (0, 0, -0.25), "tail_1": (0, 0, 0.4)}
    latigo = {"spine_1": (0.05, 0, 0.30), "spine_2": (0.05, 0, 0.35), "spine_3": (0, 0, 0.30), "spine_4": (0, 0, 0.20), "tail_1": (0, 0, -0.4)}
    girar(L, L.comp(T["CARGA"], carga), 9, x2, y2, z0, rza + 30)
    L.reposo(0, x2, y2, z0, rza + 30)
    girar(L, L.comp(T["CARGA"], latigo), 5, x2, y2, z0, rza - 20)
    f_lanza = L.cur - 3; f_imp = f_lanza + VUELO
    girar(L, L.comp(T["CARGA"]), 12, x2, y2, z0, rza)
    fin = f_imp + 235; sc.frame_end = fin                                      # incluye cuando Alfred se levanta (alfred_se_levanta.py)
    L.reposo(max(10, fin - L.cur + 1), x2, y2, z0, rza)
    alf = _ns(ALFRED, "alfred_horno")["construir"](f_mira=f_voz + 10, f_imp=f_imp, f_fin=fin)
    # --- hornear raiz y huesos
    frames = sorted(L.TL); rx, ry = root.rotation_euler.x, root.rotation_euler.y
    root.rotation_mode = 'XYZ'
    for n in L.NB: pb[n].rotation_mode = 'XYZ'
    pico = O.get("jerry_pico")
    if pico is None:
        pico = O["stone_pickaxe"].copy(); pico.name = "jerry_pico"; bpy.data.collections["cueva_bloques"].objects.link(pico)
        rec = bpy.data.collections.get("luz_entrada_receptores")
        if rec: rec.objects.link(pico)
    pico.parent = None
    for c in list(pico.constraints): pico.constraints.remove(c)
    if pico.animation_data: pico.animation_data_clear()
    pico.rotation_mode = 'XYZ'; pico.hide_viewport = pico.hide_render = False
    Mj, boca = {}, {}
    for f in frames:
        d = L.TL[f]
        w = d["pose"]["spine_2"][0]; a_ = math.radians(d["rz"])          # embestida: la raiz va adelante al golpear y atras al cargar
        root.location = (d["x"] - math.sin(a_) * EMBESTIDA * w, d["y"] + math.cos(a_) * EMBESTIDA * w, d["z"]); root.rotation_euler = (rx, ry, math.radians(d["rz"]))
        for n, v in d["pose"].items(): pb[n].rotation_euler = v
        wv = min([1.0] + [min(1.0, max(0.0, max(a - f, f - b) / 4.0)) for a, b in camina])   # al caminar no abre las patas en V
        for n, dz in PATAS_V.items(): pb[n].rotation_euler.z += dz * wv
        root.location.z -= BAJA_V
        pb["jaw_top"].rotation_euler = [math.radians(a) for a in JAW_TOP]; pb["jaw_bot"].rotation_euler = [math.radians(a) for a in JAW_BOT]
        root.keyframe_insert("location", frame=f); root.keyframe_insert("rotation_euler", frame=f)
        for n in L.NB: pb[n].keyframe_insert("rotation_euler", frame=f)
        bpy.context.view_layer.update()
        Mj[f] = arm.matrix_world @ pb["jaw_top"].matrix; boca[f] = (arm.matrix_world @ pb["jaw_top"].tail + arm.matrix_world @ pb["jaw_bot"].tail) * 0.5
        if f > f_suelta: continue
        M = Mj[f] @ Matrix(REL_PICO)       # agarre del usuario, relativo a la mandibula superior
        l, q, s = M.decompose(); pico.location = l; pico.rotation_euler = q.to_euler('XYZ', pico.rotation_euler); pico.scale = s
        for dp in ("location", "rotation_euler", "scale"): pico.keyframe_insert(dp, frame=f)
    # --- los bloques se rompen
    R_ = _ns(ROMPER, "romper_local")
    for b, gs in golpes.items():
        ob = O[b]; c = ob.matrix_world.translation
        R_["romper"](b, gs, contacto=(c.x + 0.5, c.y, c.z + 0.5))
        if ob.animation_data: ob.animation_data_clear()
        for f, v in ((1, False), (gs[-1], True)):
            ob.hide_viewport = v; ob.hide_render = v; ob.keyframe_insert("hide_viewport", frame=f); ob.keyframe_insert("hide_render", frame=f)
        if b != BLOQUES[0]: _carbon_suelto(b, gs[-1], fin)
    _vuelo_pico(pico, f_suelta, x0, y1, z0, rz, fin)
    _carbon_suelto(BLOQUES[0], golpes[BLOQUES[0]][-1], fin, hasta=f_agarre - 6)
    sc.frame_set(f_imp); arm_a = O["Armature"]; fb = arm_a.pose.bones["face_alfred"]
    cara = arm_a.matrix_world @ ((fb.head + fb.tail) * 0.5)
    _lanzar_carbon(BLOQUES[0], Mj, boca, f_agarre, f_lanza, f_imp, cara, O["alfred"].matrix_world.translation.z + 0.03, fin)
    sc.frame_set(1)
    return {"golpes": golpes, "suelta_pico": f_suelta, "agarre": f_agarre, "lanza": f_lanza, "impacto": f_imp, "voz": f_voz, "fin": fin, "alfred": alf}


def girar(L, pose, n, x, y, z, rz):
    """gira en el sitio hacia `rz` llevando la pose a `pose`"""
    p0 = L.ult["pose"]; r0 = L.ult["rz"]
    for i in range(n):
        u = (i + 1) / n; u = u * u * (3 - 2 * u); L.poner(L.mezclar(p0, pose, u), x, y, z, r0 + (rz - r0) * u)


def _vuelo_pico(pico, f0, x, y, z, rz, fin):
    """sale de la boca hacia la derecha de Jerry, gira en el aire y queda tendido en el suelo"""
    a = math.radians(rz - 40); der = Vector((math.cos(a), math.sin(a), 0)); fw = Vector((-math.sin(a), math.cos(a), 0))
    bpy.context.scene.frame_set(f0); p0 = pico.location.copy(); e0 = pico.rotation_euler.copy(); n = 11
    p1 = Vector((x, y, z + 0.02)) + der * 0.85 + fw * 0.25
    e1 = Euler((0.0, 0.0, e0.z + 2.6))
    for k in range(1, n + 1):
        u = k / n; p = p0.lerp(p1, u); p.z += 0.35 * math.sin(math.pi * u)
        pico.location = p; pico.rotation_euler = (e0.x + (e1.x - e0.x) * u, e0.y + (e1.y - e0.y) * u, e0.z + (e1.z - e0.z) * u)
        for dp in ("location", "rotation_euler"): pico.keyframe_insert(dp, frame=f0 + k)
    pico.keyframe_insert("location", frame=fin); pico.keyframe_insert("rotation_euler", frame=fin)


def _lanzar_carbon(bloque, Mj, boca, f_ag, f_la, f_imp, cara, suelo, fin):
    """el carbon flotante va a la boca de Jerry, lo lleva, lo lanza en arco a la cara de Alfred, rebota y cae al suelo"""
    o = bpy.data.objects["coal_suelto_" + bloque.split("_ore_")[-1]]; f_a = f_ag - 6
    bpy.context.scene.frame_set(f_a); p_a = o.location.copy(); e_a = o.rotation_euler.copy(); esc = Vector((0.6,) * 3)
    Mrel = Mj[f_ag].inverted() @ Matrix.LocRotScale(boca[f_ag], e_a.to_quaternion(), esc)
    def key(f, M):
        l, q, s = M.decompose(); o.location = l; o.rotation_euler = q.to_euler('XYZ', o.rotation_euler); o.scale = s
        for dp in ("location", "rotation_euler", "scale"): o.keyframe_insert(dp, frame=f)
    for f in range(f_a + 1, f_ag + 1):                       # de donde flota a la boca
        u = (f - f_a) / (f_ag - f_a); key(f, Matrix.LocRotScale(p_a.lerp(boca[f], u * u * (3 - 2 * u)), e_a.to_quaternion(), esc))
    for f in range(f_ag + 1, f_la + 1): key(f, Mj[f] @ Mrel)  # en la boca
    p0 = (Mj[f_la] @ Mrel).to_translation(); q0 = (Mj[f_la] @ Mrel).to_quaternion(); g = Vector((0, 0, -9.8 / 576)); Tn = f_imp - f_la
    v = (cara - p0 - 0.5 * g * Tn * Tn) / Tn; eje = Vector((0.3, 1, 0.2)).normalized()
    disco = lambda k: Euler((0.12, 0.0, 0.9 * k)).to_quaternion()      # plano, girando en el aire como un disco
    for k in range(1, Tn + 1):
        q = q0.slerp(disco(k), min(1.0, k / 3.0)); key(f_la + k, Matrix.LocRotScale(p0 + v * k + 0.5 * g * k * k, q, esc))
    p = cara.copy(); v = Vector((-v.x * 0.25, -v.y * 0.25, 0.04)); q1 = disco(Tn); quieto = False
    for f in range(f_imp + 1, fin + 1):                       # rebota en la cara y cae
        if not quieto:
            v = v + g; p = p + v
            if p.z <= suelo: p.z = suelo; v = Vector((v.x * 0.4, v.y * 0.4, -v.z * 0.3)); quieto = v.z < 0.01
            q1 = Euler((0, 0, 0.7)).to_quaternion() if quieto else Quaternion(eje, 0.4) @ q1
        key(f, Matrix.LocRotScale(p, q1, esc))


def _carbon_suelto(bloque, f0, fin, hasta=None):
    """como el hierro de Alfred: sale el carbon del bloque roto, rebota y queda flotando y girando sobre el suelo"""
    O = bpy.data.objects; nombre = "coal_suelto_" + bloque.split("_ore_")[-1]; o = O.get(nombre)
    if o is None:
        with bpy.data.libraries.load(COAL_BLEND, link=False) as (src, dst): dst.objects = ["coal"]
        o = dst.objects[0]; o.name = nombre; bpy.data.collections["cueva_bloques"].objects.link(o)
        rec = bpy.data.collections.get("luz_entrada_receptores")
        if rec: rec.objects.link(o)
    if o.animation_data: o.animation_data_clear()
    o.rotation_mode = 'XYZ'; c = O[bloque].matrix_world.translation; g = 9.8 / 576
    p = Vector((c.x, c.y, c.z + 0.5)); v = Vector((0.0, 0.0, 2.5)) / 24; suelo = c.z + 0.03; rebotes = 0; ft = None
    for k in range(0, (hasta or fin) - f0 + 1):
        if rebotes < 2:
            p = p + v; v.z -= g
            if p.z <= suelo: p.z = suelo; v.z = -v.z * 0.35; rebotes += 1
            z = p.z
        else:
            ft = k if ft is None else ft
            z = suelo + min(1.0, (k - ft) / 10.0) * 0.4 + 0.06 * math.sin(2 * math.pi * (k - ft) / 48.0)
        o.location = (p.x, p.y, z); o.rotation_euler = (math.radians(91.5), math.radians(-25), 2 * math.pi * k / 72.0); o.scale = (0.6,) * 3
        for dp in ("location", "rotation_euler", "scale"): o.keyframe_insert(dp, frame=f0 + k)
    for f, h in ((1, True), (f0, False)):
        o.hide_viewport = h; o.hide_render = h; o.keyframe_insert("hide_viewport", frame=f); o.keyframe_insert("hide_render", frame=f)
