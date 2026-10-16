# -*- coding: utf-8 -*-
"""RING DE LUCHA: el PUBLICO (ribbits y guardianes ribbit) alienta a su peleador. Ninguna animacion es igual:
- cada ribbit tiene su ESTILO propio (17 estilos distintos: saltarin, apoyado en la valla, golpea la valla, bombea los brazos,
  agita un brazo, sombra de boxeo, aplaude, senala, baila, nervioso, saltitos, molino, punos alternados, grita con las manos
  en la boca, salto con giro, aplauso lento...) con su propio tempo, fase, alturas y amplitudes;
- ademas REACCIONA a la pelea: cuando su peleador conecta o esquiva, celebra (brazos arriba, salta); cuando su peleador
  recibe, se agarra la cabeza y se encoge. Cada uno con su propio retraso y duracion.
- siempre mira hacia la pelea (el cuerpo gira siguiendo a los luchadores), pies en su slab / en el pasto.
Usa los mismos eventos que pelea_reacciones.py. No toca camara ni ojos. Repetible: rehace <nombre>_publico / _publico_raiz."""
import bpy, math, random
from mathutils import Vector
from bpy_extras import anim_utils

RX = {"__name__": "reac"}
exec(open("C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/pelea_reacciones.py", encoding="utf-8").read(), RX)
AP = RX["AP"]; L = RX["L"]; ESP = L["g"]
apuntar, rotar_mundo, claves, ss, snap = AP["apuntar"], AP["rotar_mundo"], AP["claves"], AP["ss"], AP["snap"]
E_RIBBITS = "C:/Users/user/Desktop/Alfred_Animacion/estructura_lista/ribbits"
FIN = AP["FIN"]; UP = Vector((0, 0, 1)); VALLA = ESP["VALLA"]; CADA = 1
sc = bpy.context.scene; vl = bpy.context.view_layer

LUCHADOR_SUELO = {"guard_ribbit_4": "alfred", "guard_ribbit_2": "guard_ribbit_1", "guard_ribbit_11": "alfred",
                  "ribbit_4_ring": "guard_ribbit_1", "ribbit_6_ring": "alfred"}
ESTILOS_VALLA = ["apoyado", "golpea_valla", "agita_valla"]           # necesitan llegar a la barra (solo los que estan en slab)
# guardianes en slab apoyados en la barra (escudo en la mano izquierda, lanza en la derecha), cada uno a su manera
GUARD_VALLA = ["g_escudo_valla", "g_lanza_arriba", "g_golpea", "g_apoyado_mira", "g_agita_lanza"]
ESTILOS = ESTILOS_VALLA + ["saltarin", "bombea", "agita", "sombra", "aplaude", "senala", "baila", "nervioso",
                           "saltitos", "molino", "alterna_punos", "bocina", "giro_salto", "aplauso_lento"]
# cuanto se mete cada uno en la valla con sus movimientos (medido): se retrasa eso desde la valla
METIDO = {"ribbit_1_ring": 0.078, "guard_ribbit_13": 0.146, "guard_ribbit_2": 0.181, "ribbit_2_ring": 0.103, "guard_ribbit_5": 0.247,
          "guard_ribbit_11": 0.26, "ribbit_4_ring": 0.031, "guard_ribbit_12": 0.246, "ribbit_5_ring": 0.212, "ribbit_8_ring": 0.161,
          "ribbit_7_ring": 0.053, "guard_ribbit_15": 0.184, "ribbit_3_ring": 0.25, "ribbit_4b_ring": 0.12}
APOYO = ESTILOS_VALLA + GUARD_VALLA
# pose de los brazos de los guardianes apoyados, puesta por el usuario en guard_ribbit_3 (lanza y escudo no atraviesan la valla)
POSE_GUARDIA = {"right_arm": ((0.1059, 0.056402, 0.04069), (-402.47, 31.842, 276.5)),
                "left_arm": ((0.10444, 0.062565, -0.10087), (-55.77, -38.431, -9.4748))}


def gesto_guardia(e, lado, q, lent, wc):
    """(levanta, agita) en grados, sumados a la pose del usuario: siempre hacia arriba, lejos de la valla"""
    lev = 0.0; agi = 0.0
    if lado > 0:
        if e == "g_escudo_valla": lev = 25 + 20 * math.sin(q)
        elif e == "g_lanza_arriba": lev = 60.0 if 15 < lent % 60 < 35 else 0.0
        elif e == "g_golpea": lev = 22 * max(0.0, math.sin(q)) ** 2
        elif e == "g_agita_lanza": lev = 20.0; agi = 20 * math.sin(q)
        lev += 55 * wc
    elif e == "g_apoyado_mira" and 20 < lent < 34: lev = 45.0
    return lev, agi
HACIA_RING = {"N": Vector((0, -1, 0)), "S": Vector((0, 1, 0)), "E": Vector((-1, 0, 0)), "O": Vector((1, 0, 0))}


# ------------------------------------------------------------------ eventos de la pelea (quien la pasa bien en cada momento)
def eventos():
    golpes, _r = AP["programa"](); MOV = AP["MOV"]; ev = []
    for (st, n), rea in zip(golpes, RX["REACCION"]):
        A, S, H, R = MOV[n]["t"]; fi = st + A + S
        if rea.startswith("recibe"): ev.append((fi, "alfred", {"recibe": 1.0, "recibe_fuerte": 1.5, "recibe_arriba": 1.3}[rea]))
        else: ev.append((fi, "guard_ribbit_1", 0.5))
    for e0, tipo, n in RX["ATAQUES_G"]:
        if tipo == "rafaga": ev.append((e0 + 5 + 2 * 5 + 2, "guard_ribbit_1", 0.7))
        elif tipo == "patada_voladora": ev.append((e0 + 14, "alfred", 0.8))
        else: ev.append((e0 + 11, "guard_ribbit_1", 1.2))
    return sorted(ev)


def curva_raiz(nombre):
    o = bpy.data.objects[nombre]; ad = o.animation_data
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    fc = [cb.fcurves.find("location", index=i) for i in range(2)]
    return lambda f: Vector((fc[0].evaluate(f), fc[1].evaluate(f), 9.0))


# ------------------------------------------------------------------ plan de cada ribbit (unico)
# ribbits extra para llenar huecos (en el pasto; saltan alto o levantan los brazos para verse sobre la valla)
# (nombre, archivo, lado, posicion a lo largo de la valla, distancia a la valla, estilo, luchador, altura de salto)
EXTRAS = [("ribbit_9_ring", "ribbit_2", "S", -41.25, 1.5, "saltarin", "alfred", 0.6),
          ("ribbit_10_ring", "ribbit_3", "E", -10.2, 1.85, "bombea", "guard_ribbit_1", 0.6),
          ("ribbit_11_ring", "ribbit_5", "O", -14.3, 1.3, "saltitos", "alfred", 0.6),
          ("ribbit_12_ring", "ribbit_6", "O", -8.85, 1.5, "giro_salto", "guard_ribbit_1", 0.6),
          ("ribbit_13_ring", "ribbit_7", "S", -37.1, 1.75, "saltarin", "guard_ribbit_1", 0.55),
          ("ribbit_14_ring", "ribbit_8", "N", -36.6, 1.75, "bombea", "alfred", 0.5)]


def colocar_extras():
    """anexa (si falta) y coloca cada ribbit extra en el pasto mirando al ring"""
    hechos = []
    for nombre, archivo, lado, pos, sep, estilo, luchador, salto in EXTRAS:
        r = bpy.data.objects.get(nombre)
        if r is None:
            r = ESP["anexar"](E_RIBBITS + "/" + archivo + ".blend", archivo, nombre)
        if r.get("_pub_base") is None:
            pt = ESP["punto_lado"](lado, pos, sep)
            r.location = (pt.x, pt.y, ESP["Z"]); r.rotation_euler = (0, 0, ESP["mirar_centro"](pt.x, pt.y)); vl.update()
            ESP["apoyar_en_suelo"](r)
        hechos.append(nombre)
    return hechos


def repartir():
    frogs = []
    for nombre, archivo, lado, pos, con_slab, luchador in ESP["FROGS"]:
        frogs.append(dict(nombre=nombre, lado=lado, pos=pos, slab=con_slab, luchador=luchador or LUCHADOR_SUELO.get(nombre, "alfred")))
    # apoyarse en la barra: solo ribbits en slab (los guardianes llevan lanza y escudo, que atravesarian la valla)
    # y de esos, los que quedan mas cerca del centro de un hueco entre postes (hay un poste cada metro, en las coordenadas x.5)
    rng = random.Random(2026); con = [f for f in frogs if f["slab"] and f["nombre"].startswith("ribbit")]
    con = sorted(con, key=lambda f: abs(f["pos"] - round(f["pos"])))[:len(ESTILOS_VALLA)]
    resto = [e for e in ESTILOS if e not in ESTILOS_VALLA]; rng.shuffle(resto); rng.shuffle(con)
    for f, e in zip(con, ESTILOS_VALLA): f["estilo"] = e
    libres = [f for f in frogs if "estilo" not in f]
    for f, e in zip(libres, resto): f["estilo"] = e
    for f, e in zip([f for f in frogs if f["slab"] and f["nombre"].startswith("guard")], GUARD_VALLA): f["estilo"] = e
    for nombre, archivo, lado, pos, sep, estilo, luchador, salto in EXTRAS:
        if bpy.data.objects.get(nombre) is not None:
            frogs.append(dict(nombre=nombre, lado=lado, pos=pos, slab=False, luchador=luchador, estilo=estilo, salto_fijo=salto))
    for f in frogs:
        r = random.Random(f["nombre"])
        f.update(per=r.randint(8, 15), fase=r.uniform(0, 6.28), amp=r.uniform(0.8, 1.2), salto=r.uniform(0.2, 0.4),
                 cada_salto=r.randint(38, 70), retraso=r.randint(2, 8), dur=r.randint(16, 30), prob=r.uniform(0.65, 1.0),
                 sway=r.uniform(3, 8), seed=r.randint(0, 10 ** 6))
        if f.get("salto_fijo"): f["salto"] = f["salto_fijo"]; f["cada_salto"] = r.randint(26, 44)    # extras: saltan alto y seguido
    return frogs


def en_valla(p):
    """el punto esta dentro de la valla (barras de 0.125 de grosor en dos bandas de altura, postes de 0.25 cada metro)"""
    X0, X1, Y0, Y1 = VALLA["x0"], VALLA["x1"], VALLA["y0"], VALLA["y1"]
    if 9.38 <= p.z <= 9.56 or 9.75 <= p.z <= 9.94:
        if (abs(p.y - Y0) < 0.0625 or abs(p.y - Y1) < 0.0625) and X0 <= p.x <= X1: return True
        if (abs(p.x - X0) < 0.0625 or abs(p.x - X1) < 0.0625) and Y0 <= p.y <= Y1: return True
    if 9.0 <= p.z <= 10.0:
        for px in (X0, X1):
            for k in range(int(Y1 - Y0) + 1):
                if abs(p.x - px) < 0.125 and abs(p.y - (Y0 + k)) < 0.125: return True
        for py in (Y0, Y1):
            for k in range(int(X1 - X0) + 1):
                if abs(p.y - py) < 0.125 and abs(p.x - (X0 + k)) < 0.125: return True
    return False


def envolvente(f, a, dur, sube=3, baja=8):
    if f < a or f > a + dur + baja: return 0.0
    if f < a + sube: return snap((f - a) / float(sube))
    if f <= a + dur: return 1.0
    return 1 - ss((f - a - dur) / float(baja))


def capas_evento(fr, ev):
    """por frame: (celebra, desanimo, salto_extra)"""
    rng = random.Random(fr["seed"]); cel = {}; des = {}; sal = {}
    for fe, favor, k in ev:
        if rng.random() > fr["prob"]: continue
        a = fe + fr["retraso"] + rng.randint(0, 3); dur = int(fr["dur"] * (0.7 + 0.3 * min(1.5, k)))
        bueno = favor == fr["luchador"]; salta = bueno and (k >= 0.9 or rng.random() < 0.5); h = fr["salto"] * min(1.0, 0.5 + 0.4 * k)
        for f in range(a, a + dur + 9):
            w = envolvente(f, a, dur)
            if bueno: cel[f] = max(cel.get(f, 0.0), w)
            else: des[f] = max(des.get(f, 0.0), w * (0.6 if k < 0.9 else 1.0))
            if salta:
                t = f - a; n = 12
                if 0 <= t < 2 * n: sal[f] = max(sal.get(f, 0.0), h * math.sin(math.pi * (t % n) / n) * (1.0 if t < n else 0.6))
    return cel, des, sal


# ------------------------------------------------------------------ cuerpo y brazos de cada estilo
def estilo_cuerpo(fr, f):
    """(inclina_adelante, balanceo, giro_extra, salto_z, giro_raiz)"""
    e = fr["estilo"]; ph = 2 * math.pi * f / fr["per"] + fr["fase"]; a = fr["amp"]; sw = fr["sway"] * math.sin(ph * 0.5)
    inc, bal, giro, z, spin = 4.0, sw, 0.0, 0.0, 0.0
    ciclo = (f + int(fr["fase"] * 10)) % fr["cada_salto"]
    if e in ("apoyado", "golpea_valla", "agita_valla"): inc = 10.0
    if e == "bocina": inc = 12.0 + 3 * math.sin(ph)
    if e == "saltarin" and ciclo < 12: z = fr["salto"] * math.sin(math.pi * ciclo / 12.0)
    if e == "saltitos": z = 0.07 * a * abs(math.sin(ph))
    if e in ("bombea", "golpea_valla", "aplaude"): z = 0.025 * a * abs(math.sin(ph))
    if e == "sombra": giro = 14.0 * math.sin(ph)
    if e == "baila": bal = 12.0 * math.sin(ph * 0.5); giro = 15.0 * math.sin(ph * 0.5 + 1.0)
    if e == "nervioso": inc = 6.0 * math.sin(ph * 0.7); z = 0.05 * max(0.0, math.sin(ph * 1.5)) ** 4
    if e == "giro_salto" and ciclo < 16:
        z = fr["salto"] * 1.1 * math.sin(math.pi * ciclo / 16.0); spin = 2 * math.pi * ss(ciclo / 16.0)
    return inc, bal, giro, z, spin


def estilo_brazos(fr, f, k):
    """objetivos (izq, der) y giro de puno; k = ejes y puntos del frame"""
    e = fr["estilo"]; ph = 2 * math.pi * f / fr["per"] + fr["fase"]; a = fr["amp"]
    fw, rt, up = k["fw"], k["rt"], k["up"]; out = {}
    lent = (f + int(fr["fase"] * 13)) % 80
    for s, lado in (("left", -1), ("right", 1)):
        h = k["hom"][s]; q = ph + (0 if lado > 0 else math.pi)
        reposo = h + fw * 0.12 - up * 0.14 + rt * lado * 0.05
        arriba = h + up * 0.27 * a + rt * lado * 0.07
        valla = k["valla"](h, False, lado) if e in APOYO else k["valla"](h)
        T = reposo; roll = 0.0
        if e == "apoyado":
            T = valla
            if (lado > 0) == (lent < 40) and 10 < lent % 40 < 28: T = h + up * 0.25 + rt * lado * 0.05        # a ratos levanta un puno
        elif e == "golpea_valla": T = valla + up * 0.09 * max(0.0, math.sin(q)) ** 2
        elif e == "agita_valla": T = valla if lado < 0 else h + up * 0.21 + rt * lado * (0.06 + 0.11 * math.sin(q)) + fw * 0.04; roll = 30 * math.sin(q) * (lado > 0)
        # --- guardianes apoyados (izquierda = escudo, derecha = lanza)
        elif e == "g_escudo_valla": T = valla if lado < 0 else h + up * (0.15 + 0.10 * math.sin(q)) * a + fw * 0.05     # bombea la lanza
        elif e == "g_lanza_arriba":
            T = valla
            if lado > 0 and 15 < lent % 60 < 35: T = h + up * 0.27 + rt * 0.04                                   # a ratos alza la lanza
        elif e == "g_golpea": T = valla if lado < 0 else valla + up * 0.12 * max(0.0, math.sin(q)) ** 2           # golpea la barra con la lanza
        elif e == "g_apoyado_mira":
            T = valla
            if lado < 0 and 20 < lent < 34: T = h + up * 0.22 + fw * 0.06                                         # levanta el escudo
        elif e == "g_agita_lanza": T = valla if lado < 0 else h + up * 0.2 + rt * 0.12 * math.sin(q) + fw * 0.04; roll = 25 * math.sin(q) * (lado > 0)
        elif e == "saltarin": T = arriba if k["z"] > 0.02 else h + up * 0.18 + rt * lado * 0.09 * math.sin(q)
        elif e == "bombea": T = h + up * (0.18 + 0.08 * math.sin(ph)) * a + rt * lado * 0.06
        elif e == "agita": T = (h + up * 0.21 + rt * lado * (0.06 + 0.12 * math.sin(q)) + fw * 0.04) if lado < 0 else reposo; roll = 25 * math.sin(q) * (lado < 0)
        elif e == "sombra":
            p = max(0.0, math.sin(q)) ** 3; T = h + fw * (0.08 + 0.2 * p) + up * 0.1 + rt * (-lado) * 0.03; roll = 80 * p
        elif e in ("aplaude", "aplauso_lento"):
            c = 0.5 + 0.5 * math.sin(ph * (0.5 if e == "aplauso_lento" else 1.0))
            T = k["pecho"] + rt * lado * (0.025 + 0.09 * c)
            if e == "aplauso_lento" and 50 < lent < 70: T = arriba
        elif e == "senala":
            T = (h + k["a_pelea"] * 0.27 + up * 0.06) if (lado > 0 and lent < 45) else arriba
        elif e == "baila": T = h + up * (0.12 + 0.1 * math.sin(q)) + rt * lado * (0.12 + 0.05 * math.cos(q)) + fw * 0.05
        elif e == "nervioso": T = k["cabeza"] + rt * lado * 0.05 + fw * 0.02
        elif e == "saltitos": T = h + up * (0.12 + 0.12 * max(0.0, math.sin(q))) + rt * lado * 0.05 + fw * 0.04
        elif e == "molino":
            T = (h + (up * math.cos(ph) + fw * math.sin(ph)) * 0.27 + rt * lado * 0.05) if lado > 0 else arriba; roll = 0
        elif e == "alterna_punos": T = arriba if math.sin(q) > 0.2 else reposo
        elif e == "bocina":
            T = (h + fw * 0.14 + up * 0.15 + rt * (-lado) * 0.09) if (f + int(fr["fase"] * 7)) % 60 > 18 else arriba
        elif e == "giro_salto": T = arriba if k["z"] > 0.03 else h + up * 0.19 + rt * lado * (0.07 + 0.1 * math.sin(q))
        out[s] = (T, roll)
    return out


# ------------------------------------------------------------------ construir un ribbit
def objs_de(r): return [r] + list(r.children_recursive)


def construir_uno(fr, ev, pelea):
    r = bpy.data.objects[fr["nombre"]]; arm = ESP["arma_de"](r); P = arm.pose.bones; W = lambda: arm.matrix_world
    ocultos = [o for o in objs_de(r) if o.hide_viewport]
    for o in ocultos: o.hide_viewport = False
    sl = bpy.data.objects.get("slab_" + fr["nombre"]); sl_oc = bool(sl and sl.hide_viewport)
    if sl_oc: sl.hide_viewport = False
    try:
        if r.get("_pub_base") is None: r["_pub_base"] = list(r.location) + [r.rotation_euler.z]
        bx, by, bz, yaw0 = r["_pub_base"]
        hacia = HACIA_RING[fr["lado"]]
        if fr["estilo"] in APOYO: yaw0 = math.atan2(-hacia.x, hacia.y)          # de frente a la valla: las dos manos llegan
        if fr["estilo"] in ESTILOS_VALLA:
            if fr["lado"] in ("N", "S"): bx = float(round(fr["pos"]))          # al centro del hueco entre dos postes
            else: by = float(round(fr["pos"]))
        atras = (0.03 if fr["slab"] else 0.0) + (0.0 if fr["estilo"] in APOYO else METIDO.get(fr["nombre"], 0.0) + 0.02 * (fr["nombre"] in METIDO))
        base = Vector((bx, by, bz)) - hacia * atras
        nb = lambda pre: next(b.name for b in P if b.name.startswith(pre))
        B = dict(body=nb("body_"), left=nb("left_arm"), right=nb("right_arm"), lleg=nb("left_leg"), rleg=nb("right_leg"))
        for o in (r, arm):
            if o.animation_data: o.animation_data.action = None
        for b in P: b.rotation_mode = 'XYZ'; b.rotation_euler = (0, 0, 0); b.rotation_quaternion = (1, 0, 0, 0)
        r.location = base; r.rotation_euler = (0, 0, yaw0); vl.update()
        mallas = [c for c in r.children_recursive if c.type == 'MESH']
        # la PUNTA DE LA MALLA de cada brazo/pata (en los ribbits el hueso del brazo apunta al reves que el bloque del brazo)
        cuerpo = next(c for c in arm.children if c.type == 'MESH' and c.vertex_groups.get(B["left"]))
        aA = arm.matrix_world.inverted() @ cuerpo.matrix_world; TIP = {}; LARGO = {}
        for b in (B["left"], B["right"], B["lleg"], B["rleg"]):
            vg = cuerpo.vertex_groups[b]; bone = arm.data.bones[b]; h = bone.head_local
            vs = [aA @ v.co for v in cuerpo.data.vertices if any(g.group == vg.index and g.weight > 0.5 for g in v.groups)]
            lejos = sorted(vs, key=lambda q: (q - h).length)[-max(1, len(vs) // 4):]; tip = sum(lejos, Vector()) / len(lejos)
            TIP[b] = bone.matrix_local.inverted() @ tip; LARGO[b] = (tip - h).length
        punta = lambda b: W() @ (P[b].matrix @ TIP[b])
        # que el BLOQUE DEL BRAZO no se meta en el cuerpo mas que en reposo (el hombro ya esta encajado por diseno)
        from mathutils.bvhtree import BVHTree
        vg_i = lambda b: cuerpo.vertex_groups[b].index
        v_de = {b: {v.index for v in cuerpo.data.vertices if any(g.group == vg_i(b) and g.weight > 0.5 for g in v.groups)} for b in (B["body"], B["left"], B["right"])}
        poly_cuerpo = [p.vertices[:] for p in cuerpo.data.polygons if all(v in v_de[B["body"]] for v in p.vertices)]

        def dentro_de(bvh, q):
            d = Vector((0.577, 0.577, 0.577)); n = 0; o = q.copy()
            for _ in range(20):
                hit = bvh.ray_cast(o, d)
                if hit[0] is None: break
                n += 1; o = hit[0] + d * 1e-4
            return n % 2 == 1

        def metidos(b, reposo=False):
            if reposo: vs = [v.co.copy() for v in cuerpo.data.vertices]
            else:
                dg = bpy.context.evaluated_depsgraph_get(); ev = cuerpo.evaluated_get(dg); M = cuerpo.matrix_world
                vs = [M @ v.co for v in ev.data.vertices]
            bvh = BVHTree.FromPolygons(vs, poly_cuerpo)
            return sum(1 for i in v_de[b] if dentro_de(bvh, vs[i]))
        tope = {b: metidos(b, True) + 2 for b in (B["left"], B["right"])}

        def mapa(b):
            par = P[b].parent
            return arm.matrix_world.to_3x3() @ (par.matrix @ par.bone.matrix_local.inverted() @ arm.data.bones[b].matrix_local).to_3x3()

        def minz():
            dg = bpy.context.evaluated_depsgraph_get(); z = 1e9
            for x in mallas:
                e = x.evaluated_get(dg); M = x.matrix_world; z = min(z, min((M @ v.co).z for v in e.data.vertices))
            return z
        piso = 9.5 if fr["slab"] else 9.0
        cel, des, sal = capas_evento(fr, ev)
        rail_z = VALLA["z_barra"] + 0.05                                     # el centro de la mano justo encima de la barra

        def valla(h, recortar=True, lado=0):
            q = h.copy()
            if fr["lado"] in ("N", "S"): q.y = VALLA["y1"] if fr["lado"] == "N" else VALLA["y0"]; a_lo_largo = Vector((1, 0, 0))
            else: q.x = VALLA["x1"] if fr["lado"] == "E" else VALLA["x0"]; a_lo_largo = Vector((0, 1, 0))
            q.z = rail_z; d = q - h
            if recortar: return h + d.normalized() * 0.3 if d.length > 0.3 else q
            if lado:                                                             # brazo que sobra: la mano se apoya mas al costado
                Lb = LARGO[B["right" if lado > 0 else "left"]]
                if d.length < Lb:
                    v = h - r.location; sg = 1.0 if v.dot(a_lo_largo) >= 0 else -1.0
                    q = q + a_lo_largo * sg * math.sqrt(Lb * Lb - d.length ** 2)
            return q

        # los que se apoyan: el cuerpo casi recto y lejos de la valla; los BRAZOS se desplazan hasta la barra
        inc_valla = 8.0 if fr["estilo"] in APOYO else None
        if fr["estilo"] in GUARD_VALLA:                                          # posicion donde lanza y escudo NO tocan la valla (pose del usuario)
            from mathutils.bvhtree import BVHTree
            def bvh_m(o):
                dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); M = o.matrix_world
                return BVHTree.FromPolygons([M @ v.co for v in ev.data.vertices], [p.vertices[:] for p in ev.data.polygons])
            vobj = bpy.data.objects["valla_ring_lucha"]; vh = vobj.hide_viewport; vobj.hide_viewport = False; vl.update(); bv = bvh_m(vobj)
            armas = [m for m in mallas if not m.name.startswith("Mesh_0")]
            slab = bpy.data.objects.get("slab_" + fr["nombre"])
            a_lo_largo = Vector((1, 0, 0)) if fr["lado"] in ("N", "S") else Vector((0, 1, 0))
            elegido = None
            for dp in [0.0, 0.04, 0.08, 0.12, 0.16, 0.2, 0.25, 0.3]:
                for dl in [0.0, 0.05, -0.05, 0.1, -0.1, 0.15, -0.15, 0.2, -0.2, 0.25, -0.25, 0.3, -0.3, 0.35, -0.35, 0.4, -0.4]:
                    r.location = base + a_lo_largo * dl - hacia * dp; r.rotation_euler = (0, 0, yaw0)
                    for b_ in B.values(): P[b_].rotation_euler = (0, 0, 0)
                    vl.update(); rt0 = (r.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized()
                    rotar_mundo(arm, B["body"], rt0, math.radians(-8.0))
                    for clave, b_ in (("right_arm", B["right"]), ("left_arm", B["left"])):
                        lo_, ro_ = POSE_GUARDIA[clave]; P[b_].location = lo_; P[b_].rotation_euler = [math.radians(v) for v in ro_]
                    vl.update(); r.location.z += piso - minz(); vl.update(); toca = False
                    for gi in (0.0, 9.0, -18.0):                                     # tambien con el cuerpo girado +-9 (sigue la pelea)
                        if gi: rotar_mundo(arm, B["body"], UP, math.radians(gi)); vl.update()
                        if any(bvh_m(m).overlap(bv) for m in armas): toca = True; break
                    rotar_mundo(arm, B["body"], UP, math.radians(9.0)); vl.update()
                    if toca: continue
                    if slab:
                        bb = [slab.matrix_world @ Vector(c) for c in slab.bound_box]; dg = bpy.context.evaluated_depsgraph_get(); pts = []
                        for x in mallas:
                            ev = x.evaluated_get(dg); M = x.matrix_world; pts += [M @ v.co for v in ev.data.vertices]
                        z0 = min(q.z for q in pts); pies = [q for q in pts if q.z < z0 + 0.02]
                        if sum(1 for q in pies if min(c.x for c in bb) <= q.x <= max(c.x for c in bb) and min(c.y for c in bb) <= q.y <= max(c.y for c in bb)) < 0.7 * len(pies): continue
                    elegido = (dl, dp); break
                if elegido: break
            vobj.hide_viewport = vh
            for b_ in (B["left"], B["right"]): P[b_].location = (0, 0, 0)
            if elegido: base = base + a_lo_largo * elegido[0] - hacia * elegido[1]
            fr["pos_guardia"] = elegido
        canal = {"location": [], "rotation_euler": []}; cb = {h: [] for h in B.values()}; prev = {}; zprev = 0.0; giro_prev = 0.0
        locs = {B["left"]: [], B["right"]: []}; aparta = {B["left"]: 0.0, B["right"]: 0.0}
        for b_ in locs: P[b_].location = (0, 0, 0)
        frames = list(range(1, FIN + 1, CADA))
        if frames[-1] != FIN: frames.append(FIN)
        for f in frames:
            inc, bal, giro, z, spin = estilo_cuerpo(fr, f)
            if inc_valla is not None: bal *= 0.3; giro *= 0.3
            wc = cel.get(f, 0.0); wd = des.get(f, 0.0); z = max(z, sal.get(f, 0.0))
            inc = inc * (1 - wc) - 8 * wc + 18 * wd; bal *= (1 - wd)
            if inc_valla is not None:                                          # apoyado en la barra: no se endereza ni salta
                inc = inc_valla + 2.0 * math.sin(2 * math.pi * f / (3 * fr["per"])); z = 0.0
            r.location = (base.x, base.y, base.z + z); r.rotation_euler = (0, 0, yaw0 + spin)
            for b in B.values(): P[b].rotation_euler = (0, 0, 0)
            for b_ in locs: P[b_].location = (0, 0, 0)
            vl.update()
            R3 = r.matrix_world.to_3x3(); fw = (R3 @ Vector((0, 1, 0))).normalized(); rt = (R3 @ Vector((1, 0, 0))).normalized()
            # sigue la pelea con el cuerpo (giro limitado y suavizado)
            pc = pelea(f); dP = pc - Vector((base.x, base.y, 9.0)); dP.z = 0; dP.normalize()
            ang = math.degrees(math.atan2(fw.cross(dP).z, fw.dot(dP))); lim = 8.0 if inc_valla is not None else 35.0
            ang = max(-lim, min(lim, ang))
            giro_prev = giro_prev + (ang - giro_prev) * 0.35
            rotar_mundo(arm, B["body"], rt, math.radians(-inc))
            rotar_mundo(arm, B["body"], fw, math.radians(bal))
            rotar_mundo(arm, B["body"], UP, math.radians(giro_prev + giro))
            # patas: empujan al subir, se estiran al bajar, se abren al aterrizar, pasan el peso
            vz = z - zprev; zprev = z; aire = z > 0.015
            for b, lado in ((B["rleg"], 1), (B["lleg"], -1)):
                adel = max(-30.0, min(30.0, -vz * 600.0)) if aire else 3.0 * math.sin(2 * math.pi * f / fr["per"] + lado)
                afuera = 7.0 + (10.0 if aire else 0.0) + 8.0 * wd + 4.0 * math.sin(2 * math.pi * f / (2 * fr["per"]) + (0 if lado > 0 else math.pi))
                pie = (-UP * math.cos(math.radians(adel)) + fw * math.sin(math.radians(adel))) * math.cos(math.radians(afuera)) + rt * lado * math.sin(math.radians(afuera))
                hip = W() @ P[b].head; apuntar(arm, b, lambda b=b: punta(b), hip + pie.normalized() * LARGO[b])
            vl.update()
            zs = minz()
            if not aire or zs < piso: r.location.z += piso - zs; vl.update()
            k = dict(fw=fw, rt=rt, up=UP, z=z, valla=valla,
                     hom={"left": W() @ P[B["left"]].head, "right": W() @ P[B["right"]].head},
                     cabeza=(W() @ P[B["body"]].tail) + UP * 0.08)
            k["pecho"] = (k["hom"]["left"] + k["hom"]["right"]) * 0.5 + fw * 0.2
            ap = pc + UP * 0.9 - (k["hom"]["left"] + k["hom"]["right"]) * 0.5; k["a_pelea"] = ap.normalized()
            br = estilo_brazos(fr, f, k)
            for s, lado in (("left", -1), ("right", 1)):
                h = k["hom"][s]; T, roll = br[s]
                apoyado = inc_valla is not None
                if wc and not (apoyado and lado < 0):                            # apoyado: celebra con un brazo, la otra mano sigue en la barra
                    T = T.lerp(h + UP * (0.26 + 0.03 * math.sin(f * 1.4 + lado)) + rt * lado * 0.08, wc); roll += 40 * wc * math.sin(f * 0.9 + lado)
                if wd and not apoyado: T = T.lerp(k["cabeza"] + rt * lado * 0.05, wd)
                b = B[s]
                if fr["estilo"] in GUARD_VALLA:                                  # pose del usuario + gesto
                    clave = "right_arm" if lado > 0 else "left_arm"; lo_, ro_ = POSE_GUARDIA[clave]
                    P[b].location = lo_; P[b].rotation_euler = [math.radians(v) for v in ro_]; vl.update()
                    lent = (f + int(fr["fase"] * 13)) % 80; q = 2 * math.pi * f / fr["per"] + fr["fase"] + (0 if lado > 0 else math.pi)
                    lev, agi = gesto_guardia(fr["estilo"], lado, q, lent, wc)
                    if lev: rotar_mundo(arm, b, rt, math.radians(lev))
                    if agi: rotar_mundo(arm, b, fw, math.radians(agi))
                    locs[b].append((f, tuple(P[b].location)))
                    continue
                if apoyado:                                                      # el hombro avanza (pose location) lo que le falta a la mano
                    P[b].location = (0, 0, 0); vl.update(); h0 = W() @ P[b].head; dd = T - h0; Lb = LARGO[b]
                    if dd.length > Lb * 0.95:
                        o = dd.normalized() * min(0.3, dd.length - Lb * 0.95); par = P[b].parent
                        A3 = arm.matrix_world.to_3x3() @ (par.matrix @ par.bone.matrix_local.inverted() @ arm.data.bones[b].matrix_local).to_3x3()
                        P[b].location = A3.inverted() @ o; vl.update()
                apuntar(arm, b, lambda b=b: punta(b), T)
                if abs(roll) > 0.5: rotar_mundo(arm, b, (T - h).normalized(), math.radians(lado * roll))
                # si el brazo atraviesa el cuerpo: el hombro se aparta hacia afuera y la mano tambien
                loc0 = P[b].location.copy(); fuera = 0.0
                for _it in range(10):
                    if metidos(b) <= tope[b]: break
                    fuera += 0.03; o = rt * lado * fuera
                    P[b].location = loc0 + mapa(b).inverted() @ o; vl.update()
                    T2 = T + rt * lado * fuera
                    apuntar(arm, b, lambda b=b: punta(b), T2)
                    if abs(roll) > 0.5: rotar_mundo(arm, b, (T2 - (W() @ P[b].head)).normalized(), math.radians(lado * roll))
                aparta[b] = max(aparta[b], fuera)
                locs[b].append((f, tuple(P[b].location)))
            vl.update(); zs = minz()                                             # (los brazos ya movidos no pueden atravesar el piso)
            if zs < piso: r.location.z += piso - zs; vl.update()
            canal["location"].append((f, tuple(r.location))); canal["rotation_euler"].append((f, tuple(r.rotation_euler)))
            for h in B.values():
                e = P[h].rotation_euler.to_quaternion().to_euler('XYZ', prev[h]) if h in prev else P[h].rotation_euler.copy()
                prev[h] = e; cb[h].append((f, tuple(e)))
        act_r = claves(r, fr["nombre"] + "_publico_raiz", canal)
        canales = {'pose.bones["%s"].rotation_euler' % h: v for h, v in cb.items()}
        for b_, v in locs.items():
            if v: canales['pose.bones["%s"].location' % b_] = v
        act_a = claves(arm, fr["nombre"] + "_publico", canales)
        for act in (act_r, act_a):                                                  # claves cada 2 frames: curvas suaves
            for fc in anim_utils.action_get_channelbag_for_slot(act, (r if act is act_r else arm).animation_data.action_slot).fcurves:
                for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'
                fc.update()
        viejo = bpy.data.actions.get(fr["nombre"] + "_anima")
        if viejo and viejo.users == 0: bpy.data.actions.remove(viejo)
        return dict(estilo=fr["estilo"], luchador=fr["luchador"], pos_guardia=fr.get("pos_guardia"),
                    aparta=round(max(aparta.values()), 3), hombro_max=round(max([Vector(v).length for l_ in locs.values() for _f, v in l_] or [0.0]), 3), celebra=round(sum(1 for v in cel.values() if v > 0.5) / 24.0, 1),
                    desanima=round(sum(1 for v in des.values() if v > 0.5) / 24.0, 1))
    finally:
        for o in ocultos: o.hide_viewport = True
        if sl_oc: sl.hide_viewport = True


def preparar():
    a = curva_raiz("alfred"); g = curva_raiz("guard_ribbit_1")
    return repartir(), eventos(), (lambda f: (a(f) + g(f)) * 0.5)


def construir():
    frogs, ev, pelea = preparar(); out = {}
    for fr in frogs: out[fr["nombre"]] = construir_uno(fr, ev, pelea)
    sc.frame_set(1); return out
