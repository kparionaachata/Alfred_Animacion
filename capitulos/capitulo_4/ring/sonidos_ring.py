# -*- coding: utf-8 -*-
"""RING DE LUCHA (base_ranas_2): SONIDOS de las entidades, como una pelea callejera con el publico vitoreando.
- PELEA: silbido de cada golpe de Alfred (player.attack.sweep) y el impacto segun la reaccion del guardian
  (bloqueo = golpe flojo, recibe = golpe fuerte + quejido de ribbit, recibe fuerte = critico + quejido + caida, esquiva = salto de rana);
  ataques del guardian: punos contra el bloqueo de Alfred (player.hurt: Alfred recibe el impacto), embestida (golpe fuerte + player.hurt), patada voladora
  (long_jump + silbido + aterrizaje); pasos de Alfred en el pasto (cada ~0.45 m), aterrizajes del guardian en cada saltito.
- PUBLICO: cada ribbit vitorea (sonidos/ribbits ribbit_ambient) cuando a su luchador le va bien y se queja (ribbit_hurt) cuando no
  (mismos tiempos que su animacion), murmullo de fondo constante, rugido al empezar cada fase;
  animales: vaca = mugido, cerdo = grunido, pollo = cacareo + aleteo; vaca2 golpea la barra (wood.hit).
Cada tira lleva `mic_emisor` = la raiz de quien la produce -> despues el MICROFONO de camara (ultimo paso) pone volumen y paneo.
Repetible: borra sus tiras (SND_ring_*) y sus curvas."""
import bpy, sys, random, importlib.util, math, os
from mathutils import Vector
from bpy_extras import anim_utils

RIB = "C:/Users/user/Desktop/Alfred_Animacion/sonidos/ribbits/entity"
VITOREO = [(os.path.join(RIB, "ribbit_ambient%d.ogg" % i), 1.0) for i in range(1, 6)]
QUEJA = [(os.path.join(RIB, "ribbit_hurt%d.ogg" % i), 1.0) for i in range(1, 4)]
PASO_RIB = [(os.path.join(RIB, "ribbit_step%d.ogg" % i), 1.0) for i in range(1, 3)]
FASES = [160, 330, 500, 650]
LUCHA = 1.7       # sonidos de los dos peleadores (pasos, golpes, silbidos, saltos, quejidos)
PUBLICO = 0.45    # vitoreos, quejas, murmullo, animales


def _modulo(nombre, ruta):
    m = sys.modules.get(nombre)
    if m is None:
        sp = importlib.util.spec_from_file_location(nombre, ruta); m = importlib.util.module_from_spec(sp); sys.modules[nombre] = m; sp.loader.exec_module(m)
    return m


def _borrar_curvas(sc, prefijos):
    ad = sc.animation_data
    if not (ad and ad.action): return
    for l in ad.action.layers:
        for st in l.strips:
            for cb in st.channelbags:
                for fc in [fc for fc in cb.fcurves if any('["%s' % p in fc.data_path for p in prefijos)]: cb.fcurves.remove(fc)
    ad.action.update_tag(); sc.update_tag(); bpy.context.view_layer.update()


def _curva_loc(nombre):
    o = bpy.data.objects[nombre]; ad = o.animation_data
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    fc = [cb.fcurves.find("location", index=i) for i in range(3)]
    return lambda f: Vector([c.evaluate(f) for c in fc])


def construir():
    sc = bpy.context.scene; FIN = sc.frame_end; rng = random.Random(2026)
    m = _modulo("alfred_sonidos", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py")
    if not hasattr(sc, "mcsnd"): m.register()
    p = sc.mcsnd
    if not p.items: bpy.ops.mcsnd.indexar()
    ed = sc.sequence_editor_create(); S = m._strips(ed)
    for t in [t for t in S if t.name.startswith("SND_ring_")]: S.remove(t)
    _borrar_curvas(sc, ("SND_ring_",))

    PUB = {"__name__": "pub"}
    exec(open("C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/publico_ribbits.py", encoding="utf-8").read(), PUB)
    RX = PUB["RX"]; AP = PUB["AP"]; MOV = AP["MOV"]
    EV = []      # (frame, sonido: evento str o lista de rutas, grupo, volumen, etiqueta, emisor)
    ALF, GUA = "alfred", "guard_ribbit_1"

    # ---------------- PELEA: golpes de Alfred y reaccion del guardian
    golpes, _r = AP["programa"]()
    for (st, n), rea in zip(golpes, RX["REACCION"]):
        A, S_, H, R = MOV[n]["t"]; fi = st + A + S_
        patada = MOV[n]["m"] in ("RL", "LL", "RK")
        EV.append((st + A - 1, "entity.player.attack.sweep", "golpes", 0.75 if patada else 0.65, "ring_silbido", ALF))
        if rea == "bloqueo":
            EV.append((fi, "entity.player.attack.weak", "golpes", 0.9, "ring_bloqueado", GUA))
        elif rea in ("recibe", "recibe_fuerte", "recibe_arriba"):
            EV.append((fi, "entity.player.attack.strong", "golpes", 1.2, "ring_impacto", GUA))
            EV.append((fi + 2, QUEJA, "voces", 0.9, "ring_queja_guardian", GUA))
            if rea != "recibe":
                EV.append((fi, "entity.player.attack.crit", "golpes", 1.0, "ring_critico", GUA))
                EV.append((fi + 9, "entity.generic.small_fall", "golpes", 0.8, "ring_cae", GUA))
        else:                                                                    # esquiva / se agacha
            EV.append((fi - 3, "entity.frog.long_jump", "objetos", 2.0, "ring_esquiva", GUA))
        if MOV[n].get("salto"):                                                  # superman / rodilla voladora: aterrizaje
            EV.append((st + A + S_ + H + 3, "entity.player.small_fall", "pasos", 0.8, "ring_aterriza", ALF))

    # ---------------- ataques del guardian contra Alfred
    for e0, tipo, n in RX["ATAQUES_G"]:
        if tipo == "rafaga":
            for k in range(n):
                fi = e0 + 5 + k * 5 + 2
                EV.append((fi - 2, "entity.player.attack.sweep", "golpes", 0.45, "ring_silbido_g", GUA))
                EV.append((fi + 1, "entity.player.hurt", "voces", 0.6, "ring_alfred_recibe", ALF))
                EV.append((fi, "entity.player.attack.weak", "golpes", 0.6, "ring_puno_g", ALF))
        else:
            prep, vuelo = 4, (10 if tipo == "patada_voladora" else 7)
            e1 = e0 + prep; fi = e1 + vuelo
            EV.append((e1, "entity.frog.long_jump", "objetos", 2.0, "ring_salta_g", GUA))
            EV.append((e1 + vuelo // 2, "entity.player.attack.sweep", "golpes", 0.7, "ring_silbido_g", GUA))
            if tipo == "embestida":
                EV.append((fi, "entity.player.attack.strong", "golpes", 1.2, "ring_embestida", ALF))
                EV.append((fi + 3, "entity.player.hurt", "voces", 0.8, "ring_alfred_dolor", ALF))
            else:
                EV.append((fi + 1, "entity.frog.step", "pasos", 0.9, "ring_aterriza_g", GUA))

    # ---------------- pasos de Alfred (cada ~0.45 m recorridos) y saltitos del guardian
    Ap = _curva_loc(ALF); Gp = _curva_loc(GUA); rec = 0.0; prev = Ap(1)
    for f in range(2, FIN + 1):
        q = Ap(f); d = Vector((q.x - prev.x, q.y - prev.y)).length; prev = q; rec += d
        if rec >= 0.45:
            EV.append((f, "block.grass.step", "pasos", 0.35 + min(0.3, d * 3), "ring_paso", ALF)); rec = 0.0
    zprev = Gp(1).z
    for f in range(2, FIN + 1):
        z = Gp(f).z
        if zprev > 9.025 and z <= 9.012 and rng.random() < 0.7: EV.append((f, PASO_RIB, "pasos", 0.45, "ring_salto_g", GUA))
        zprev = z

    # ---------------- PUBLICO: vitoreos / quejas de cada espectador (mismos tiempos que su animacion)
    frogs = PUB["repartir"](); ev = PUB["eventos"]()
    espectadores = [f["nombre"] for f in frogs]

    def gritos(nombre, cel, des, son_cel, son_des, r):
        on = False; ultimo = -99
        for f in range(1, FIN + 1):
            v = cel.get(f, 0.0)
            if v > 0.5 and not on:
                on = True; EV.append((f, son_cel, "voces", r.uniform(0.75, 1.0), "ring_vitorea", nombre)); ultimo = f
            elif v > 0.5 and f - ultimo >= r.randint(16, 24) and r.random() < 0.3:
                EV.append((f, son_cel, "voces", r.uniform(0.55, 0.8), "ring_vitorea", nombre)); ultimo = f
            elif v <= 0.5: on = False
        on = False
        for f in range(1, FIN + 1):
            v = des.get(f, 0.0)
            if v > 0.5 and not on:
                on = True
                if son_des and r.random() < 0.65: EV.append((f + r.randint(0, 3), son_des, "voces", r.uniform(0.4, 0.6), "ring_queja", nombre))
            elif v <= 0.5: on = False

    for fr in frogs:
        cel, des, _s = PUB["capas_evento"](fr, ev)
        gritos(fr["nombre"], cel, des, VITOREO, QUEJA, random.Random(fr["nombre"] + "_voz"))
    # animales (mismos parametros que en cerdos_animan / vacas_animan)
    ANIMALES = [("cerdo_ring", "alfred", "entity.pig.ambient"), ("cerdo2_ring", "guard_ribbit_1", "entity.pig.ambient"),
                ("vaca_ring", "guard_ribbit_1", "entity.cow.ambient"), ("vaca2_ring", "alfred", "entity.cow.ambient"),
                ("pollo_ring", "alfred", "entity.chicken.ambient")]
    for nombre, luch, son in ANIMALES:
        if nombre not in bpy.data.objects: continue
        rr = random.Random(nombre)
        fr = dict(nombre=nombre, luchador=luch, seed=rr.randint(0, 10 ** 6), prob=0.9, retraso=rr.randint(2, 6), dur=rr.randint(18, 28), salto=0.0)
        cel, des, _s = PUB["capas_evento"](fr, ev)
        gritos(nombre, cel, des, son, None, random.Random(nombre + "_voz"))
    r2 = random.Random("pollo_alas")                                            # el pollo aletea todo el tiempo (rafagas)
    f = 8
    while f < FIN:
        EV.append((f, "entity.chicken.step", "objetos", 0.35, "ring_aleteo", "pollo_ring")); f += r2.randint(20, 40)
    r3 = random.Random("vaca2_golpes"); t = None                               # vaca2 golpea la barra (mismos golpes que su animacion)
    for a, b in ((190, 262), (430, 520)):
        t = a + 8
        while t < b - 14:
            d = r3.randint(14, 22); EV.append((t + int(d * 0.45), "block.wood.hit", "golpes", 0.8, "ring_vaca_barra", "vaca2_ring")); t += d + r3.randint(0, 7)
    # murmullo de fondo: siempre algun ribbit hablando
    rm = random.Random("murmullo"); f = 4; ult = None
    while f < FIN:
        n = rm.choice([x for x in espectadores if x != ult]); ult = n
        EV.append((f, VITOREO, "ambiente", rm.uniform(0.25, 0.4), "ring_murmullo", n)); f += rm.randint(9, 16)
    # rugido del publico al empezar cada fase
    for f0 in FASES:
        for n in random.Random(f0).sample(espectadores, 5):
            EV.append((f0 + random.Random(n + str(f0)).randint(0, 6), VITOREO, "voces", 0.95, "ring_rugido", n))

    # ---------------- el publico no tapa la pelea: como mucho TOPE voces del publico sonando a la vez (los rugidos de fase siempre)
    TOPE = 14; DUR = 50; activos = []; filtrado = []
    for e in sorted(EV, key=lambda x: x[0]):
        if e[4] in ("ring_vitorea", "ring_queja", "ring_murmullo"):
            activos = [a for a in activos if a > e[0]]
            if len(activos) >= TOPE: continue
            activos.append(e[0] + DUR)
        filtrado.append(e)
    EV = filtrado

    # ---------------- colocar
    techo = p.techo_voces; p.techo_voces = False                                 # el microfono de camara maneja los niveles
    n_ok = 0; falt = set()
    for f, son, g, v, et, emisor in sorted(EV, key=lambda x: x[0]):
        if not (1 <= f <= FIN): continue
        v = v * (LUCHA if emisor in (ALF, GUA) else PUBLICO)                     # la pelea siempre por encima del publico
        rutas = son if isinstance(son, list) else m.rutas_de(p, son)
        if not rutas: falt.add(son); continue
        t = m.colocar(bpy.context, p, rutas, int(f), g, et, v, 0, rng, False)
        if t is None: continue
        t["mic_emisor"] = emisor; n_ok += 1
        a, b = t.frame_final_start, t.frame_final_end                           # canal libre (el publico se superpone mucho)
        if any(o != t and o.channel == t.channel and o.frame_final_start < b and o.frame_final_end > a for o in S):
            for c in range(2, 129):
                if not any(o != t and o.channel == c and o.frame_final_start < b and o.frame_final_end > a for o in S): t.channel = c; break
    p.techo_voces = techo
    return dict(tiras=n_ok, faltan=sorted(map(str, falt)))
