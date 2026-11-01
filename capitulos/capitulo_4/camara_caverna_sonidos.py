# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: sonidos de la caverna mientras la camara viaja por ella (frames F_INI-F_FIN, ver camara_caverna_replay.py).
Cada fuente tiene una posicion en el mundo y el volumen de cada sonido sale de la distancia a la camara en ese frame: sube al acercarse y baja al alejarse.
Fuentes: lagos de lava (borbotones, pop), cascadas de lava (cada una en su sitio), zombies y esqueletos caminando en cornisas lejanas, goteo de
calcitas (stalactitas/dripstone) y el ambiente de cueva. Add-on Alfred Sonidos, etiqueta mcsnd_origen = "caverna_viaje".
Uso en Blender: exec(open(ruta, encoding="utf8").read()); sonorizar()      (repetible)
"""
import bpy, importlib.util, sys, random, math, os, json
from mathutils import Vector

ADDON = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py"
ORIGEN = "caverna_viaje"
CAMARA = "Camera.001"
F_INI, F_FIN = 258, 920                    # el viaje incluye los 300 frames extra (520-860, camara_caverna_replay.TOUR)
SEMILLA = 7
AMB_INI, AMB_FIN, AMB_RAMPA = 0.04, 0.6, 900         # ambiente de cueva: volumen inicial, final y frames que tarda en subir
F_BAJAR = (860, 45)                        # (inicio, duracion): el ambiente baja al minimo mientras la camara regresa a Alfred y Jerry
F_LAVA_FIN = 920                          # desde aqui ya no se oye lava (la camara esta lejos de ella): se cortan las tiras que lo pasan
F_LAVA_MIN = 927                          # desde aqui la lava suena al minimo (baja suave en los 37 frames anteriores)
BOCA = Vector((0.5, 82.5, 66.0))          # salida del tunel: de aqui se mide cuanto se adentro la camara
PROFUNDO = 48.0                           # m desde la boca = "todo adentro"
# profundidad (0-1) a partir de la cual empieza a sonar cada tipo: primero goteo y lava lejana, luego cascadas, al final las criaturas
ENTRADA = {"goteo": 0.08, "ambiente": 0.1, "lava": 0.18, "cascada": 0.3, "pop": 0.4, "zombie": 0.5, "esqueleto": 0.68, "slime": 0.5}
C_EFECTIVA = 110.0                        # m/s: velocidad del sonido "de cine" (la real, 343, apenas se notaria) para el efecto Doppler
CARPETA_DOPPLER = r"C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/sonidos_doppler/"

# (nombre, posicion, tipo) fuentes puntuales fuera de la geometria: cornisas y paredes por donde pasa la camara
# zombies y esqueletos: suenan donde estan de verdad (objetos `zombie_cav_*`, `skeleton_*_cav_*`, `zombie_baby_cav_*` de criaturas_caverna.py)
GOTEOS = [Vector((2.0, 68.0, 66.5)), Vector((-6.0, 58.0, 62.0)), Vector((-12.0, 48.0, 56.0)), Vector((6.0, 74.0, 66.0)), Vector((-4.0, 64.0, 64.0)),
          # a lo largo del viaje extra: calcitas junto al recorrido bajo (RUTA de camara_caverna_replay.py)
          Vector((-24.0, 18.0, 30.0)), Vector((-14.0, 2.0, 25.0)), Vector((2.0, -2.0, 24.0)), Vector((14.0, 8.0, 24.0)), Vector((20.0, 28.0, 30.0)), Vector((12.0, 48.0, 38.0))]


def cargar_addon():
    m = sys.modules.get("alfred_sonidos_local")
    if m is None:
        spec = importlib.util.spec_from_file_location("alfred_sonidos_local", ADDON)
        m = importlib.util.module_from_spec(spec)
        sys.modules["alfred_sonidos_local"] = m
        spec.loader.exec_module(m)
        m.register()
    return m


def _suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _entra(cam_pos, tipo):
    """0 -> 1 progresivo segun lo adentro de la caverna que va la camara (se vuelve a apagar al regresar a la salida)"""
    prof = min(1.0, (cam_pos - BOCA).length / PROFUNDO)
    return _suave((prof - ENTRADA[tipo]) / 0.2)


def _atenua(d, alcance, curva=1.7):
    return max(0.0, 1.0 - d / alcance) ** curva


def _camara_por_frame():
    sc = bpy.context.scene
    cam = bpy.data.objects[CAMARA]
    g = sc.frame_current
    pos = {}
    for f in list(range(F_INI, F_FIN + 1, 4)) + [F_FIN]:
        sc.frame_set(f)
        pos[f] = cam.matrix_world.translation.copy()
    sc.frame_set(g)

    def en(f):
        a = max(F_INI, min(F_FIN, f)); a0 = F_INI + (a - F_INI) // 4 * 4; a1 = min(F_FIN, a0 + 4)
        u = 0 if a1 == a0 else (a - a0) / (a1 - a0)
        return pos[a0].lerp(pos[a1], u)
    return en


def _puntos_lava():
    O = bpy.data.objects
    lagos = []
    ob = O.get("caverna_lava_lagos")
    if ob is not None:
        vs = ob.data.vertices
        paso = max(1, len(vs) // 600)
        lagos = [ob.matrix_world @ vs[i].co for i in range(0, len(vs), paso)]
    cascadas = []
    for o in bpy.data.collections["caverna_superficies"].all_objects:
        if o.type == 'MESH' and any(s.material and s.material.name.startswith("caverna_lava_cae") for s in o.material_slots):
            c = sum((o.matrix_world @ Vector(v) for v in o.bound_box), Vector()) / 8
            cascadas.append(c)
    return lagos, cascadas


ECOS = ((0.17, 0.55), (0.36, 0.38), (0.60, 0.25), (0.90, 0.15), (1.25, 0.08))     # (retardo s, volumen): rebotes en las paredes de la caverna
ECOS_FUERTE = ((0.20, 0.75), (0.42, 0.55), (0.70, 0.40), (1.00, 0.28), (1.40, 0.18), (1.90, 0.10))     # eco largo y marcado (rebotes del pico)
VOL_CRIATURAS = 0.4                                                                    # ~ -8 dB: la camara esta lejos del suelo


def _procesado(ruta, k, eco):
    """copia de `ruta` con el tono multiplicado por k (efecto Doppler) y/o con eco de caverna (voz lejana apagada + rebotes); se guarda en
    CARPETA_DOPPLER y se reutiliza"""
    import aud
    os.makedirs(CARPETA_DOPPLER, exist_ok=True)
    out = CARPETA_DOPPLER + "%s_%.3f%s.wav" % (os.path.splitext(os.path.basename(ruta))[0], k, ("_eco_" + eco if isinstance(eco, str) else "_eco") if eco else "")
    if not os.path.isfile(out):
        src = aud.Sound(ruta)
        canales = int(src.specs[1])
        snd = src
        if eco:
            base = src.lowpass(3500.0, 0.7)                     # a distancia se pierden los agudos
            snd = base
            for retardo, vol in (ECOS_FUERTE if eco == "fuerte" else ECOS):
                snd = snd.mix(base.delay(retardo).volume(vol))
        snd.pitch(k).resample(44100, False).write(out, 44100, canales, aud.FORMAT_S16, aud.CONTAINER_WAV, aud.CODEC_PCM)
    return out


MAX_ZOMBIES, MAX_ESQUELETOS, MAX_SLIMES = 1, 1, 1      # criaturas que pueden sonar a la vez (las mas cercanas a la camara)
SECO = {"entity.zombie.step": 8, "entity.skeleton.step": 8, "entity.slime.jump": 14, "entity.slime.squish": 14, "entity.zombie.ambient": 20, "entity.skeleton.ambient": 20}
HUECO = 14                                               # frames: dos sonidos de criaturas separados menos que esto cuentan como un mismo tramo "con criaturas"


def sonorizar():
    from bpy_extras import anim_utils
    m = cargar_addon()
    sc = bpy.context.scene
    p = sc.mcsnd
    m.indice(p, forzar=True)
    ed = sc.sequence_editor or sc.sequence_editor_create()
    for t in [t for t in m._strips(ed) if t.name.startswith(m.PREFIJO) and t.get("mcsnd_origen") == ORIGEN]:
        m._strips(ed).remove(t)
    if sc.animation_data and sc.animation_data.action:
        sc.animation_data_clear()
    rng = random.Random(SEMILLA)
    cam = _camara_por_frame()
    lagos, cascadas = _puntos_lava()
    puestos = {}
    fps = sc.render.fps
    baja = lambda f: 1.0 - 0.95 * _suave((f - F_BAJAR[0]) / float(F_BAJAR[1]))     # al regresar la camara con los personajes el ambiente baja al minimo
    activos = []                                              # frames de los sonidos de criaturas: (inicio, fin)

    def poner(evento, f, vol, tipo, fuente=None, grupo="ambiente", eco=False, criatura=False):
        """vol: volumen por distancia; tipo: cuando empieza a sonar (progresivo); fuente: punto para el efecto Doppler; criatura=True registra el tramo para callar al ambiente"""
        if "lava" in evento and f >= F_LAVA_FIN:
            return None
        vol *= (1.0 if tipo == "libre" else _entra(cam(f), tipo)) * (VOL_CRIATURAS if eco else 1.0)
        if tipo in ("lava", "cascada", "pop"):                     # la lava baja a su minimo para cuando Alfred habla
            vol *= 1.0 - 0.97 * _suave((f - (F_LAVA_MIN - 37)) / 37.0)
        if not criatura:
            vol *= baja(f)
        if vol < 0.03:
            return None
        rutas = m.rutas_de(p, evento)
        if not rutas:
            print("sin sonido:", evento)
            return None
        ruta = rng.choice(rutas)
        if fuente is not None:                                  # Doppler: la camara se acerca (tono sube) o se aleja (baja) de la fuente
            v = ((cam(f + 3) - fuente).length - (cam(f - 3) - fuente).length) / (6.0 / fps)        # m/s, negativo = se acerca
            k = max(0.84, min(1.2, 1.0 / (1.0 + v / C_EFECTIVA)))
            if abs(k - 1.0) <= 0.015:
                k = 1.0
            if k != 1.0 or eco:
                ruta = (_procesado(ruta[0], k, eco), ruta[1])
        t = m.colocar(bpy.context, p, [ruta], int(f), grupo, evento.replace(".", "_"), min(vol, 1.5), 0, m.rng_de(p))
        if t and "lava" in evento and t.frame_final_end > F_LAVA_FIN:
            if t.frame_final_start >= F_LAVA_FIN:
                m._strips(ed).remove(t)
                return None
            t.frame_final_end = F_LAVA_FIN
        if t:
            t["mcsnd_origen"] = ORIGEN
            puestos[evento] = puestos.get(evento, 0) + 1
            if criatura:
                activos.append((int(f), int(f) + SECO.get(evento, 14)))
        return t

    def pos_obj(ob):
        cb = anim_utils.action_get_channelbag_for_slot(ob.animation_data.action, ob.animation_data.action_slot)
        fcs = [cb.fcurves.find("location", index=i) for i in range(3)]
        return lambda f: Vector([fc.evaluate(f) for fc in fcs])
    # ---- quien puede sonar en cada momento: los MAX mas cercanos a la camara de cada familia (con histeresis para no saltar entre ellos)
    grupos = {"zombie": [], "esqueleto": [], "slime": []}
    for ob in sorted([o for o in bpy.data.objects if o.parent is None and o.animation_data and o.animation_data.action], key=lambda o: o.name):
        n = ob.name
        if n.startswith("slime_cav_"):
            grupos["slime"].append((ob, pos_obj(ob)))
        elif "_cav_" in n:
            tipo = n.split("_cav_")[0]
            if tipo.startswith("zombie"):
                grupos["zombie"].append((ob, pos_obj(ob)))
            elif tipo == "skeleton":
                grupos["esqueleto"].append((ob, pos_obj(ob)))
    maximos = {"zombie": MAX_ZOMBIES, "esqueleto": MAX_ESQUELETOS, "slime": MAX_SLIMES}
    permitido = {g: {} for g in grupos}                        # grupo -> {frame (de 4 en 4): set de nombres}
    for g, lista in grupos.items():
        actual = set()
        for f in range(F_INI, F_FIN + 1, 4):
            dist = {ob.name: (cam(f) - q(f)).length for ob, q in lista}
            if not dist:
                permitido[g][f] = set()
                continue
            orden = sorted(dist, key=lambda n: dist[n])
            lim = 1.15 * dist[orden[min(maximos[g], len(orden)) - 1]]
            nuevo = set(n for n in actual if n in dist and dist[n] <= lim)
            for n in orden:
                if len(nuevo) >= maximos[g]:
                    break
                nuevo.add(n)
            if len(nuevo) > maximos[g]:
                nuevo = set(sorted(nuevo, key=lambda n: dist[n])[:maximos[g]])
            actual = nuevo
            permitido[g][f] = set(actual)
    suena = lambda g, nombre, f: nombre in permitido[g].get(F_INI + (max(F_INI, min(F_FIN, int(f))) - F_INI) // 4 * 4, ())
    # ---- 1) criaturas
    for g in ("zombie", "esqueleto"):
        for ob, q in grupos[g]:
            tipo = ob.name.split("_cav_")[0]
            zomb = g == "zombie"
            paso = (6, 8) if tipo == "zombie_baby" else (9, 11)
            f = F_INI + rng.randint(0, 12)
            while f < F_FIN:
                if not suena(g, ob.name, f):
                    f += 4
                    continue
                for _ in range(rng.randint(4, 8)):
                    if f < F_FIN and suena(g, ob.name, f):
                        poner("entity.zombie.step" if zomb else "entity.skeleton.step", f, 0.8 * VOL_CRIATURAS * _atenua((cam(f) - q(f)).length, 55.0, 1.3),
                              g, q(f), "pasos", False, True)                    # sin eco (pedido del usuario); mismo volumen bajo que antes
                    f += rng.randint(*paso)
                if rng.random() < 0.6 and f < F_FIN and suena(g, ob.name, f):
                    poner("entity.zombie.ambient" if zomb else "entity.skeleton.ambient", f, 0.9 * VOL_CRIATURAS * _atenua((cam(f) - q(f)).length, 60.0, 1.3),
                          g, q(f), "ambiente", False, True)
                f += rng.randint(25, 70)
    # slimes GRANDES: solo suena UNO (el mas cercano a la camara); al despegar entity.slime.jump y al caer entity.slime.squish, en los frames de `saltos`
    for ob, q in grupos["slime"]:
        for a, b in json.loads(ob["saltos"]):
            if suena("slime", ob.name, int(a)):
                poner("entity.slime.jump", a, 2.4 * _atenua((cam(a) - q(a)).length, 80.0, 1.2), "slime", q(a), "voces", False, True)
            if suena("slime", ob.name, int(b)):
                poner("entity.slime.squish", b, 2.6 * _atenua((cam(b) - q(b)).length, 80.0, 1.2), "slime", q(b), "golpes", False, True)
    # tramos con criaturas (se unen los sonidos separados menos de HUECO frames)
    tramos = []
    for a, b in sorted(activos):
        if tramos and a <= tramos[-1][1] + HUECO:
            tramos[-1][1] = max(tramos[-1][1], b)
        else:
            tramos.append([a, b])
    en_tramo = lambda f: any(a - 2 <= f <= b for a, b in tramos)

    def ambiente(evento, f, vol, tipo, fuente=None):
        """sonido de ambiente de la caverna: CONTINUO. Cuando la camara se acerca a las criaturas (tramos con criaturas sonando) su volumen baja a la MITAD con una rampa
        (6 frames al entrar, 8 al salir); no se corta ni se silencia"""
        t = poner(evento, f, vol, tipo, fuente)
        if t:
            a, b, v0 = t.frame_final_start, t.frame_final_end, t.volume
            cruza = [(ta, tb) for ta, tb in tramos if ta - 6 <= b and tb + 8 >= a]
            if cruza:
                claves = {}
                claves[a] = v0 * (0.5 if en_tramo(a) else 1.0)
                for ta, tb in cruza:
                    for fr, k in ((ta - 6, 1.0), (ta, 0.5), (tb, 0.5), (tb + 8, 1.0)):
                        if a < fr < b:
                            claves[fr] = v0 * k
                claves[b] = v0 * (0.5 if en_tramo(b) else 1.0)
                for fr in sorted(claves):
                    t.volume = claves[fr]
                    t.keyframe_insert("volume", frame=fr)
                t.volume = v0 * (0.5 if en_tramo(a) else 1.0)

    # ---- 2) ambiente de la caverna (continuo; a la mitad mientras la camara esta con criaturas)
    f = 1
    while f < sc.frame_end:
        ambiente("ambient.cave", f, AMB_INI + (AMB_FIN - AMB_INI) * _suave((f - 1) / float(AMB_RAMPA)), "libre")
        f += rng.randint(45, 65)
    for f in range(F_INI, F_FIN, 11):
        c = cam(f)
        q = min(lagos, key=lambda x: (c - x).length) if lagos else c
        d = (c - q).length
        ambiente("block.lava.ambient", f + rng.randint(0, 4), 0.9 * _atenua(d, 115.0, 1.5), "lava", q)
        if rng.random() < 0.55:
            ambiente("block.lava.pop", f + rng.randint(2, 9), 0.7 * _atenua(d, 80.0, 1.5), "pop", q)
    for k, q in enumerate(cascadas):
        for f in range(F_INI + 3 * k, F_FIN, 17):
            ambiente("block.lava.ambient", f, 0.85 * _atenua((cam(f) - q).length, 100.0, 1.5), "cascada", q)
    for q in GOTEOS:
        f = F_INI + rng.randint(0, 20)
        while f < F_FIN:
            ev = "block.pointed_dripstone.drip_water" if rng.random() < 0.8 else "block.pointed_dripstone.drip_lava"
            ambiente(ev, f, 0.9 * _atenua((cam(f) - q).length, 40.0, 1.2), "goteo", q)
            f += rng.randint(18, 46)
    sc.frame_set(sc.frame_current)
    puestos["_tramos_con_criaturas"] = len(tramos)
    return puestos
