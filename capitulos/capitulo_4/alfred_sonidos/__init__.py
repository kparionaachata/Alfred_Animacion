"""Alfred Sonidos - libreria de los sonidos originales de Minecraft para poner en la escena segun lo que esta pasando (pasos, antorcha, herramientas que caen, ladridos, golpes...).

Biblioteca: carpeta `C:\\Users\\user\\Desktop\\Alfred_Animacion\\sonidos` (contiene `sounds/` con los .ogg y `sounds.json`, el indice de Minecraft: 1650 eventos -> sus variantes).
Se pueden usar de tres maneras:
  1. BIBLIOTECA: buscar un EVENTO de Minecraft (p. ej. `entity.wolf.howl`, `block.wood.step`) o un ARCHIVO suelto, escucharlo y anadirlo en el frame actual (variante aleatoria o fija).
  2. EVENTOS DEL PROYECTO: lista corta ya armada (paso en madera / piedra / pasto, antorcha, herramienta que cae, lanzar, ladrido de Jerry, voz de zombie, golpe...). Se puede redefinir lo que suena
     en cada uno con `presets_usuario.json` (en la carpeta de sonidos): {"id": {"etiqueta": "..", "eventos": ["block.wood.step"], "grupo": "pasos", "vol": 0.9}}.
  3. AUTOMATICO, leyendo la animacion de la escena:
       - PASOS: detecta cuando cada pie toca el suelo (armature de Alfred, Jerry o un zombie) y pone un paso en cada contacto, con la superficie que elijas.
       - OBJETOS: detecta cuando un objeto (p. ej. las herramientas que Alfred lanza) sale disparado (silbido) y cuando choca contra el suelo (golpe), y pone el sonido en cada frame.
       - BUCLE: rellena un rango de frames con un sonido repetido (antorcha, fuego, ambiente).
Todo se crea como tiras de sonido del editor de secuencias (`SND_<evento>_<frame>`), una fila de canales por tipo (pasos, antorcha, objetos, voces, golpes, ambiente), asi se oyen al reproducir y entran
en el render de audio. "Mezcla WAV" exporta todo el audio de la escena (voces + sonidos) a un .wav.

v1.1 - COMO EN EL JUEGO: cada objeto o evento de la escena suena con los .ogg que le corresponden en Minecraft.
  - Cada OBJETO se reconoce por su nombre, el de su padre, sus materiales y las texturas (p. ej. `oak_planks_refugio_base` -> madera, `grass_block_top` -> pasto, `zombie_1_Armature` -> zombie, `wooden_axe` -> herramienta de madera)
    y se le asigna su tipo de sonido real (`block.wood.*`, `block.stone.*`, `entity.zombie.*`...). Los bloques tienen colocar / romper / golpear / caer / paso; los mobs tienen todos sus eventos (voz, herido, muerte, paso...).
  - PASOS "del juego": un mob con paso propio (zombie, lobo, esqueleto, arana...) usa SU evento (`entity.zombie.step`); el jugador (Alfred) y el resto usan el sonido de la SUPERFICIE que tiene bajo el pie en ese frame
    (se lanza un rayo hacia abajo y se lee el bloque: madera, pasto, piedra...), y cambia solo si el suelo cambia.
  - IMPACTOS "del juego": al chocar un objeto contra el suelo suena la superficie de abajo (`fall`) y el material del propio objeto (`hit`).
  - APARICION: los objetos que aparecen / desaparecen en la animacion (bloque que se coloca o se rompe) suenan con su `place` / `break`.
v1.2 - POR DEBAJO DE LAS VOCES: cada sonido que se anade se limita para quedar por debajo de la voz mas baja de la escena (tiras de sonido que no son SND_): su pico queda `margen_pico` dB (8) por debajo del pico de esa voz y
su volumen medio (RMS) `margen_rms` dB (3) por debajo del medio de esa voz. Los niveles se miden con `aud` sobre los archivos reales, asi que vale para cualquier voz y cualquier sonido.
v1.3 - AUTOMATICO, SEGUN AVANZA LA HISTORIA: "Sonorizar la historia" lee TODA la animacion de la escena y pone los sonidos solo, sin frames escritos a mano:
  - personajes (armatures animados, visibles; mob = jugador / lobo / zombie... por su nombre): sus pasos cuando CAMINAN (tramo a tramo, con el sonido de la superficie bajo el pie o el paso propio del mob) y el CONTACTO DEL CUERPO con el
    suelo (sentarse, echarse, caer: la cadera baja y se frena);
  - objetos animados reconocidos (herramientas, bloques): silbido al salir disparados, choque contra el suelo, `place` al aparecer y `break` al romperse / desaparecer (en el primer frame en que empiezan a encogerse);
  - cada sonido queda por debajo de la voz mas baja de la escena (v1.2) y se marca `mcsnd_auto` para poder rehacerlo.
  "Todo" rehace las tiras automaticas de toda la escena; "Solo lo nuevo" sigue desde el ultimo frame sonorizado (`auto_hasta`) hasta el final de la escena, asi se va completando cuando la historia crece sin tocar lo anterior.
  "Vigilar" (opcional) lo hace solo cada pocos segundos: si el final de la escena crece sonoriza lo nuevo, y si se anaden o cambian voces reajusta los volumenes.
Panel: Vista 3D > barra lateral (N) > "Sonidos MC" (y en el editor de secuencias).
"""
bl_info = {
    "name": "Alfred Sonidos",
    "author": "Kebyn",
    "version": (1, 3, 0),
    "blender": (4, 4, 0),
    "location": "Vista 3D / Secuenciador > barra lateral (N) > Sonidos MC",
    "description": "Libreria de sonidos de Minecraft: cada objeto / evento suena con sus .ogg del juego (pasos segun la superficie, impactos, colocar / romper, voces de mobs)",
    "category": "Animation",
}

import json
import math
import os
import random
import re

import bpy
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup, UIList
from mathutils import Vector

CARPETA = r"C:\Users\user\Desktop\Alfred_Animacion\sonidos"
PREFIJO = "SND_"
GRUPOS = {"pasos": 10, "antorcha": 16, "objetos": 22, "voces": 28, "golpes": 34, "ambiente": 40}      # canal base de cada tipo (las voces de Voz Sync usan los canales 2-3)

# id: (etiqueta, [eventos de sounds.json], grupo, volumen)
PRESETS = {
    "paso_madera": ("Paso - madera", ["block.wood.step"], "pasos", 0.9),
    "paso_piedra": ("Paso - piedra", ["block.stone.step"], "pasos", 0.9),
    "paso_pasto": ("Paso - pasto", ["block.grass.step"], "pasos", 0.9),
    "paso_grava": ("Paso - grava / tierra", ["block.gravel.step"], "pasos", 0.9),
    "paso_arena": ("Paso - arena", ["block.sand.step"], "pasos", 0.9),
    "paso_nieve": ("Paso - nieve", ["block.snow.step"], "pasos", 0.9),
    "paso_tela": ("Roce de tela (sentarse / acomodarse)", ["block.wool.step", "block.wool.place"], "pasos", 0.8),
    "paso_zombie": ("Paso - zombie", ["entity.zombie.step"], "pasos", 0.9),
    "paso_lobo": ("Paso - lobo / Jerry", ["entity.wolf.step"], "pasos", 0.8),
    "antorcha": ("Antorcha / fogata (crepitar)", ["block.campfire.crackle"], "antorcha", 0.7),
    "fuego": ("Fuego (ambiente)", ["block.fire.ambient"], "antorcha", 0.7),
    "fuego_apagar": ("Fuego se apaga", ["block.fire.extinguish"], "antorcha", 0.8),
    "herr_madera": ("Herramienta cae - madera", ["block.wood.fall", "block.wood.hit"], "objetos", 1.0),
    "herr_piedra": ("Herramienta cae - piedra", ["block.stone.fall", "block.stone.hit"], "objetos", 1.0),
    "herr_metal": ("Herramienta cae - metal / cadena", ["block.chain.fall", "block.chain.hit"], "objetos", 1.0),
    "herr_rascar": ("Hacha / pico rasca", ["item.axe.scrape"], "objetos", 0.9),
    "herr_equipar": ("Equipar / coger herramienta", ["item.armor.equip_generic", "item.armor.equip_iron"], "objetos", 0.8),
    "lanzar": ("Lanzar (silbido del brazo)", ["entity.player.attack.sweep"], "objetos", 0.8),
    "lanzar_fuerte": ("Lanzar (golpe de aire fuerte)", ["entity.player.attack.strong"], "objetos", 0.7),
    "lobo_ladrido": ("Jerry - ladrido / voz", ["entity.wolf.ambient"], "voces", 0.9),
    "lobo_gruni": ("Jerry - gruñido", ["entity.wolf.growl"], "voces", 0.9),
    "lobo_aullido": ("Jerry - aullido", ["entity.wolf.howl"], "voces", 0.9),
    "lobo_jadeo": ("Jerry - jadeo", ["entity.wolf.pant"], "voces", 0.8),
    "lobo_lamento": ("Jerry - lamento (bostezo / sueno)", ["entity.wolf.whine"], "voces", 0.8),
    "lobo_sacudir": ("Jerry - sacudirse", ["entity.wolf.shake"], "voces", 0.9),
    "lobo_herido": ("Jerry - herido", ["entity.wolf.hurt"], "voces", 0.9),
    "zombie_voz": ("Zombie - voz", ["entity.zombie.ambient"], "voces", 0.9),
    "zombie_herido": ("Zombie - herido", ["entity.zombie.hurt"], "voces", 0.9),
    "zombie_muere": ("Zombie - muere", ["entity.zombie.death"], "voces", 0.9),
    "zombie_golpea_puerta": ("Zombie - golpea la puerta", ["entity.zombie.attack_wooden_door"], "golpes", 0.9),
    "alfred_dolor": ("Alfred - dolor", ["entity.player.hurt"], "voces", 0.9),
    "alfred_respira": ("Alfred - respiracion", ["entity.player.breath"], "voces", 0.8),
    "alfred_eructo": ("Alfred - eructo", ["entity.player.burp"], "voces", 0.8),
    "golpe_fuerte": ("Golpe fuerte", ["entity.player.attack.strong"], "golpes", 1.0),
    "golpe_debil": ("Golpe debil", ["entity.player.attack.weak"], "golpes", 1.0),
    "golpe_critico": ("Golpe critico", ["entity.player.attack.crit"], "golpes", 1.0),
    "caida_chica": ("Caida pequena", ["entity.generic.small_fall"], "golpes", 1.0),
    "caida_grande": ("Caida grande", ["entity.generic.big_fall"], "golpes", 1.0),
    "explosion": ("Explosion", ["entity.generic.explode"], "golpes", 1.0),
    "puerta_abrir": ("Puerta de madera - abrir", ["block.wooden_door.open"], "golpes", 0.9),
    "puerta_cerrar": ("Puerta de madera - cerrar", ["block.wooden_door.close"], "golpes", 0.9),
    "bloque_colocar": ("Bloque de madera - colocar", ["block.wood.place"], "golpes", 1.0),
    "bloque_romper": ("Bloque de madera - romper", ["block.wood.break"], "golpes", 1.0),
    "beber": ("Beber", ["entity.generic.drink"], "voces", 0.8),
    "comer": ("Comer", ["entity.generic.eat"], "voces", 0.8),
}

_ST = {"idx": None, "play": None}


# ------------------------------------------------------------------------------------------------------------------------------------ indice
def _carpeta(p):
    return bpy.path.abspath(p.carpeta) if p.carpeta else CARPETA


def indexar(carpeta):
    """-> {"eventos": {evento: [(ruta_relativa, volumen)]}, "archivos": [ruta_relativa]} (solo archivos que existen)."""
    raiz = os.path.join(carpeta, "sounds")
    ruta_json = os.path.join(carpeta, "sounds.json")
    if not os.path.isdir(raiz): raise RuntimeError(f"No existe {raiz}")
    archivos = []
    for base, _d, fs in os.walk(raiz):
        for f in fs:
            if f.lower().endswith(".ogg"): archivos.append(os.path.relpath(os.path.join(base, f), raiz).replace("\\", "/")[:-4])
    archivos.sort(); existe = set(archivos); eventos = {}
    if os.path.isfile(ruta_json):
        with open(ruta_json, encoding="utf-8") as fh: crudo = json.load(fh)

        def resolver(ev, prof=0):
            salida = []
            for s in crudo.get(ev, {}).get("sounds", []):
                if isinstance(s, str): nombre, vol, tipo = s, 1.0, "sound"
                else: nombre, vol, tipo = s.get("name", ""), float(s.get("volume", 1.0)), s.get("type", "sound")
                if tipo == "event":
                    if prof < 4 and nombre in crudo: salida += resolver(nombre, prof + 1)
                elif nombre in existe: salida.append((nombre, vol))
            return salida
        for ev in crudo:
            r = resolver(ev)
            if r: eventos[ev] = r
    tipos = {}; mobs = {}
    for ev in eventos:
        m = re.match(r"block\.([a-z_]+)\.(step|break|place|hit|fall)$", ev)
        if m: tipos.setdefault(m.group(1), {})[m.group(2)] = ev
        m = re.match(r"entity\.([a-z_]+)\.(.+)$", ev)
        if m: mobs.setdefault(m.group(1), {})[m.group(2)] = ev
    mobs = {k: v for k, v in mobs.items() if {"ambient", "hurt", "death", "step"} & set(v)}                          # solo mobs de verdad (no `generic`, `item`, `arrow`...)
    return {"eventos": eventos, "archivos": archivos, "tipos": tipos, "mobs": mobs}


def indice(p, forzar=False):
    if _ST["idx"] is None or forzar: _ST["idx"] = indexar(_carpeta(p))
    return _ST["idx"]


def rutas_de(p, nombre):
    """lista [(ruta_absoluta, volumen)] de un evento o de un archivo."""
    idx = indice(p); raiz = os.path.join(_carpeta(p), "sounds")
    if nombre in idx["eventos"]: return [(os.path.normpath(os.path.join(raiz, r + ".ogg")), v) for r, v in idx["eventos"][nombre]]
    if nombre in idx["archivos"] or os.path.isfile(os.path.join(raiz, nombre + ".ogg")): return [(os.path.normpath(os.path.join(raiz, nombre + ".ogg")), 1.0)]
    return []


def cargar_presets(p):
    pres = dict(PRESETS)
    ruta = os.path.join(_carpeta(p), "presets_usuario.json")
    if os.path.isfile(ruta):
        try:
            with open(ruta, encoding="utf-8") as fh: extra = json.load(fh)
            for k, v in extra.items(): pres[k] = (v.get("etiqueta", k), list(v["eventos"]), v.get("grupo", "objetos"), float(v.get("vol", 1.0)))
        except Exception as e: print("[Sonidos MC] presets_usuario.json:", e)
    return pres


# ------------------------------------------------------------------------------------------------------------------------------------ colocar sonidos
def _strips(ed):
    return ed.strips if hasattr(ed, "strips") else ed.sequences


def colocar(context, p, rutas, frame, grupo, etiqueta, volumen=1.0, variante=0, rng=None, auto=False):
    """pone UNA tira de sonido en `frame`. `rutas`=[(ruta, volumen_del_json)]. variante 0 = al azar. Devuelve la tira."""
    sc = context.scene; ed = sc.sequence_editor or sc.sequence_editor_create(); rng = rng or random
    ruta, vj = rutas[(variante - 1) % len(rutas)] if variante > 0 else rng.choice(rutas)
    vol = max(0.0, volumen * vj * p.volumen_general * (1.0 + rng.uniform(-p.variacion, p.variacion)))
    vol0 = vol; tope = None
    if auto and f"{PREFIJO}{etiqueta}_{int(frame)}" in {x.name for x in _strips(ed)}: return None          # ya estaba (modo "solo lo nuevo")
    if p.techo_voces:
        tc = techo_voces(sc, p); nv = nivel(ruta)
        if tc and nv: tope = min(tc[0] / nv[0], tc[1] / nv[1]); vol = min(vol, tope)                      # nunca por encima de las voces
    nombre = f"{PREFIJO}{etiqueta}_{int(frame)}"
    canal = GRUPOS.get(grupo, 22) if p.canal_por_tipo else p.canal
    t = _strips(ed).new_sound(nombre, ruta, canal, int(frame))
    t.volume = min(vol, 6.0); t["mcsnd"] = grupo; t["mcsnd_ev"] = etiqueta
    t["mcsnd_vol0"] = round(vol0, 4)
    if auto: t["mcsnd_auto"] = 1
    if tope is not None: t["mcsnd_tope"] = round(tope, 4)
    a, b = t.frame_final_start, t.frame_final_end                                                          # new_sound no esquiva tiras solapadas: busca el primer canal libre a partir del base
    otras = [o for o in _strips(ed) if o != t]
    for c in range(canal, min(canal + 12, 129)):
        if not any(o.channel == c and o.frame_final_start < b and o.frame_final_end > a for o in otras): t.channel = c; break
    return t


_NIVEL = {}


def nivel(ruta):
    """(pico, rms) lineales de un archivo de audio (mono, con cache); None si no se puede leer."""
    if ruta in _NIVEL: return _NIVEL[ruta]
    try:
        import aud
        import numpy as np
        x = np.asarray(aud.Sound(ruta).data(), dtype=np.float32)
        if x.ndim > 1: x = x.mean(axis=1)
        r = (max(float(np.abs(x).max()), 1e-6), max(float(np.sqrt((x ** 2).mean())), 1e-6))
    except Exception as e:
        print("[Sonidos MC] nivel:", ruta, e); r = None
    _NIVEL[ruta] = r
    return r


def techo_voces(sc, p):
    """(pico, rms) lineales maximos para un efecto: `margen_pico` / `margen_rms` dB por debajo de la voz mas baja de la escena (tiras de sonido que no son SND_). None si no hay voces."""
    ed = sc.sequence_editor
    if not ed: return None
    pk = rm = None
    for t in _strips(ed):
        if t.type != 'SOUND' or t.name.startswith(PREFIJO) or t.mute: continue
        n = nivel(bpy.path.abspath(t.sound.filepath))
        if not n: continue
        a, b = n[0] * t.volume, n[1] * t.volume; pk = a if pk is None else min(pk, a); rm = b if rm is None else min(rm, b)
    if pk is None: return None
    return pk * 10 ** (-p.margen_pico / 20.0), rm * 10 ** (-p.margen_rms / 20.0)


def rutas_preset(p, pid):
    pres = cargar_presets(p); etiqueta, evs, grupo, vol = pres[pid]; rutas = []
    for e in evs: rutas += rutas_de(p, e)
    return etiqueta, rutas, grupo, vol


def rng_de(p):
    return random.Random(p.semilla)


# ------------------------------------------------------------------------------------------------------------------------------------ deteccion en la animacion
def muestrear(context, f0, f1, fn):
    """evalua `fn()` en cada frame f0..f1 y restaura el frame actual. -> [(frame, valor)]."""
    sc = context.scene; actual = sc.frame_current; out = []
    try:
        for f in range(int(f0), int(f1) + 1):
            sc.frame_set(f); out.append((f, fn()))
    finally:
        sc.frame_set(actual)
    return out


def huesos_apoyo(arm):
    """huesos cuya COLA es el pie: Alfred / zombies (Rightknee_*, Leftknee_*) o Jerry (foot.R, foot.L, front_foot.R, front_foot.L)."""
    pb = arm.pose.bones.keys()
    k = [n for n in pb if n.startswith(("Rightknee", "Leftknee"))]
    if k: return k
    j = [n for n in ("foot.R", "foot.L", "front_foot.R", "front_foot.L") if n in pb]
    if j: return j
    return [n for n in pb if "foot" in n.lower() or "toe" in n.lower()]


def detectar_pasos(series, fraccion, lev_min, dist_min, hueco):
    """series: {hueso: [(frame, Vector)]} -> [(frame, hueso)] cuando el pie baja a (punto mas bajo + `fraccion` de lo que se levanta) habiendo avanzado `dist_min` desde el paso anterior de ese pie.
    Un pie que no se levanta al menos `lev_min` metros en el rango se ignora."""
    pasos = []
    for b, ser in series.items():
        zs = [pt.z for _f, pt in ser]
        if not zs: continue
        if max(zs) - min(zs) < lev_min: continue
        lim = min(zs) + fraccion * (max(zs) - min(zs)); ultimo = None; ult_f = -10 ** 6
        for i in range(1, len(ser)):
            f, pt = ser[i]
            if zs[i - 1] > lim >= zs[i] and f - ult_f >= hueco and (ultimo is None or (pt - ultimo).xy.length >= dist_min):
                pasos.append((f, b)); ultimo = pt.copy(); ult_f = f
    fin = []
    for f, b in sorted(pasos):                                                                             # dos pies a la vez (o casi) suenan como un solo paso
        if not fin or f - fin[-1][0] >= max(2, hueco // 2): fin.append((f, b))
    return fin


def detectar_objeto(ser, fps, v_lanzar, v_choque, alto, hueco_l, hueco_c, rel=None):
    """ser: [(frame, Vector)] -> (lanzamientos, impactos). Lanzamiento = la velocidad cruza `v_lanzar` m/s hacia arriba; impacto = frenazo brusco (< 35 % de la velocidad anterior, que era > `v_choque`) a menos de `alto` m del punto mas bajo."""
    sp = [0.0] + [(ser[i][1] - ser[i - 1][1]).length * fps for i in range(1, len(ser))]
    spl = sp if rel is None else [0.0] + [(rel[i] - rel[i - 1]).length * fps for i in range(1, len(rel))]            # `rel` = posicion relativa al personaje mas cercano: un objeto llevado en la espalda no "sale disparado"
    zmin = min(pt.z for _f, pt in ser); lanz = []; imp = []; ul = ui = -10 ** 6
    for i in range(2, len(ser)):
        f = ser[i][0]
        if spl[i - 1] < v_lanzar <= spl[i] and f - ul >= hueco_l: lanz.append(f); ul = f
        if sp[i - 1] > v_choque and sp[i] < 0.35 * sp[i - 1] and ser[i][1].z - zmin <= alto and f - ui >= hueco_c: imp.append(f); ui = f
    return lanz, imp


# ------------------------------------------------------------------------------------------------------------------------------------ como en el juego
# palabras clave del nombre -> tipo de sonido del bloque (block.<tipo>.step / break / place / hit / fall), por orden de prioridad. Las palabras de 4 letras o menos deben ser una palabra completa.
TIPOS_BLOQUE = [
    (("soul_sand",), "soul_sand"), (("soul_soil",), "soul_soil"), (("netherrack",), "netherrack"), (("nether_brick",), "nether_bricks"), (("basalt",), "basalt"), (("bone_block",), "bone_block"),
    (("amethyst",), "amethyst_block"), (("deepslate_brick",), "deepslate_bricks"), (("deepslate_tile",), "deepslate_tiles"), (("polished_deepslate",), "polished_deepslate"), (("deepslate",), "deepslate"),
    (("tuff_brick",), "tuff_bricks"), (("tuff",), "tuff"), (("mud_brick",), "mud_bricks"), (("packed_mud",), "packed_mud"), (("mud",), "mud"), (("moss_carpet",), "moss_carpet"), (("moss",), "moss"),
    (("powder_snow",), "powder_snow"), (("snow",), "snow"), (("glass", "ice", "vidrio", "hielo"), "glass"), (("wool", "carpet"), "wool"), (("slime",), "slime_block"), (("honey",), "honey_block"), (("sponge",), "sponge"),
    (("scaffold",), "scaffolding"), (("ladder",), "ladder"), (("cobweb",), "cobweb"), (("chain",), "chain"), (("anvil",), "anvil"), (("lantern",), "lantern"), (("copper",), "copper"),
    (("netherite",), "netherite_block"), (("iron", "gold", "metal", "diamond", "emerald"), "metal"), (("bamboo",), "bamboo"), (("cherry_leaves",), "cherry_leaves"),
    (("leaves", "grass", "fern", "flower", "sapling", "bush", "crop", "wheat", "hay", "pumpkin", "melon", "mycelium", "pasto", "hierba", "arbusto", "cesped"), "grass"), (("vine",), "vine"),
    (("sandstone",), "stone"), (("sand", "arena"), "sand"), (("gravel", "dirt", "podzol", "clay", "coarse", "farmland", "path", "tierra", "grava"), "gravel"),
    (("log", "plank", "wood", "oak", "spruce", "birch", "jungle", "acacia", "mangrove", "door", "fence", "chest", "barrel", "crafting", "bookshelf", "trapdoor", "stick", "sign", "stem", "bed", "table", "jukebox", "madera", "tablon"), "wood"),
    (("stone", "cobble", "brick", "andesite", "diorite", "granite", "obsidian", "furnace", "ore", "concrete", "terracotta", "quartz", "prismarine", "end", "blackstone", "piedra", "roca"), "stone"),
]
ALIAS_MOB = {"alfred": "player", "steve": "player", "jugador": "player", "player": "player", "jerry": "wolf", "dog": "wolf", "perro": "wolf", "lobo": "wolf", "wolf": "wolf", "oveja": "sheep", "vaca": "cow",
             "cerdo": "pig", "gallina": "chicken", "pollo": "chicken", "arana": "spider", "esqueleto": "skeleton", "aldeano": "villager", "ribbit": "frog"}
MAT_HERR = {"wooden": "wood", "stone": "stone", "iron": "metal", "golden": "metal", "gold": "metal", "diamond": "metal", "netherite": "netherite_block"}
ACCIONES_BLOQUE = [("place", "Colocar"), ("break", "Romper"), ("hit", "Golpear"), ("fall", "Caer"), ("step", "Paso")]


def _tokens(nombres):
    out = []
    for n in nombres: out += [t for t in re.split(r"[^a-z0-9]+", n.lower()) if t and not t.isdigit()]
    return out


def nombres_objeto(ob):
    """nombres con los que se reconoce un objeto: el suyo, los de sus padres, sus materiales, las texturas de esos materiales y (armatures) los primeros huesos."""
    nombres = []; o = ob
    while o is not None and len(nombres) < 8: nombres.append(o.name); o = o.parent
    try:
        for ms in ob.material_slots:
            m = ms.material
            if not m: continue
            nombres.append(m.name)
            if m.use_nodes:
                for n in m.node_tree.nodes:
                    if n.type == 'TEX_IMAGE' and n.image: nombres.append(os.path.splitext(n.image.name)[0])
    except Exception: pass
    if ob.type == 'ARMATURE': nombres += [b.name for b in list(ob.pose.bones)[:3]]
    return nombres


def nombres_material(ob):
    n = []
    try:
        for ms in ob.material_slots:
            m = ms.material
            if not m: continue
            n.append(m.name)
            if m.use_nodes: n += [os.path.splitext(x.image.name)[0] for x in m.node_tree.nodes if x.type == 'TEX_IMAGE' and x.image]
    except Exception: pass
    return n


def resolver(ob, idx):
    """-> {"clase": "bloque" | "mob" | "herramienta" | None, "tipo": tipo de bloque, "mob": mob, "fuente": nombre que lo delato}."""
    nombres = nombres_objeto(ob); toks = _tokens(nombres); txt = "_" + "_".join(toks) + "_"
    if ob.type == 'MESH':                                                                                   # en una malla el material / textura manda sobre el nombre (Pasto_roto_Alfred -> short_grass -> pasto, no jugador)
        mt = _tokens(nombres_material(ob))
        for kws, tipo in TIPOS_BLOQUE:
            for kw in kws:
                if any((t == kw) if len(kw) <= 4 else (kw in t) for t in mt) and tipo in idx["tipos"]: return {"clase": "bloque", "tipo": tipo, "mob": None, "fuente": kw}
    m = re.search(r"_(wooden|stone|iron|golden|gold|diamond|netherite)_(axe|pickaxe|sword|shovel|hoe)_", txt)
    if m: return {"clase": "herramienta", "tipo": MAT_HERR[m.group(1)], "mob": None, "fuente": f"{m.group(1)}_{m.group(2)}"}
    for t in toks:
        if t in ALIAS_MOB and ALIAS_MOB[t] in idx["mobs"]: return {"clase": "mob", "tipo": None, "mob": ALIAS_MOB[t], "fuente": t}
    for mb in sorted(idx["mobs"], key=len, reverse=True):
        if mb not in ("item", "player") and f"_{mb}_" in txt: return {"clase": "mob", "tipo": None, "mob": mb, "fuente": mb}
    for kws, tipo in TIPOS_BLOQUE:
        for kw in kws:
            if any((t == kw) if len(kw) <= 4 else (kw in t) for t in toks) or (len(kw) > 4 and "_" in kw and kw in txt):
                if tipo in idx["tipos"]: return {"clase": "bloque", "tipo": tipo, "mob": None, "fuente": kw}
    return {"clase": None, "tipo": None, "mob": None, "fuente": ""}


def mob_de_rig(rig, idx):
    r = resolver(rig, idx)
    if r["clase"] == "mob": return r["mob"]
    for h in rig.children_recursive[:12]:
        r = resolver(h, idx)
        if r["clase"] == "mob": return r["mob"]
    return None


def propios(rig):
    """nombres de los objetos que son del personaje (hijos y mallas deformadas por su armature): el rayo del suelo no debe pegarles."""
    n = {rig.name} | {o.name for o in rig.children_recursive}
    for o in bpy.data.objects:
        if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers): n.add(o.name)
    return n


def superficie_bajo(context, punto, ignorar, idx):
    """lanza un rayo hacia abajo desde `punto` (saltando los objetos de `ignorar`) y devuelve (tipo de sonido, nombre del objeto) del primer bloque reconocido, o None."""
    sc = context.scene; dg = context.evaluated_depsgraph_get(); o = Vector(punto) + Vector((0, 0, 0.25))
    for _ in range(6):
        ok, loc, _n, _i, ob, _m = sc.ray_cast(dg, o, (0, 0, -1), distance=1.5)
        if not ok: return None
        if ob.name in ignorar: o = loc + Vector((0, 0, -0.003)); continue
        r = resolver(ob.original if hasattr(ob, "original") else ob, idx)
        if r["tipo"]: return r["tipo"], ob.name
        o = loc + Vector((0, 0, -0.003))
    return None


def rutas_evento(p, evento):
    return rutas_de(p, evento) if evento else []


# ------------------------------------------------------------------------------------------------------------------------------------ automatico
def _animado(o):
    ad = o.animation_data
    return bool(ad and (ad.action or ad.nla_tracks))


def _segmentos(mov, unir=8, pad=4, minimo=8):
    """indices [(i0, i1)] de los tramos en que `mov` es verdadero (huecos <= `unir` se unen, se amplian `pad` y se descartan los de menos de `minimo`)."""
    segs = []; ini = None; ult = None
    for i, v in enumerate(mov):
        if v:
            if ini is None: ini = i
            elif i - ult > unir: segs.append((ini, ult)); ini = i
            ult = i
    if ini is not None: segs.append((ini, ult))
    n = len(mov)
    return [(max(0, a - pad), min(n - 1, b + pad)) for a, b in segs if b - a + 1 >= minimo]


def detectar_contacto(zs, fps, v_min=0.15, bajada=0.06, ventana=12, hueco=20):
    """indices en que un cuerpo que BAJABA (> `v_min` m/s y al menos `bajada` m en `ventana` frames) se frena en seco: sentarse, echarse, caer."""
    vz = [0.0] + [(zs[i] - zs[i - 1]) * fps for i in range(1, len(zs))]; out = []; ult = -10 ** 6
    for i in range(2, len(zs)):
        if i - ult < hueco: continue
        bajaba = min(vz[max(0, i - 6):i]) < -v_min and zs[max(0, i - ventana)] - zs[i] >= bajada
        if bajaba and abs(vz[i]) < 0.4 * v_min: out.append(i); ult = i
    return out


def _fin_encogerse(ser_esc, i):
    """indice en que empezo a encogerse un objeto que desaparece en `i` (sube mientras la escala siga bajando)."""
    k = i
    while k > 1 and ser_esc[k - 1] < ser_esc[k - 2] - 1e-6: k -= 1
    return max(0, k - 1)


def sonorizar_auto(context, p, f0, f1, desde):
    """pone los sonidos de toda la animacion entre f0 y f1 (solo los de frames >= `desde`). Devuelve un resumen {tipo: cantidad}."""
    sc = context.scene; idx = indice(p); fps = sc.render.fps / sc.render.fps_base; rng = random.Random(p.semilla); res = {}; sc0 = sc.frame_current
    rigs = [o for o in sc.objects if o.type == 'ARMATURE' and o.visible_get() and not o.hide_render and _animado(o) and mob_de_rig(o, idx)]
    objs = [o for o in sc.objects if o.type == 'MESH' and _animado(o) and resolver(o, idx)["clase"] in ("bloque", "herramienta")]
    pies = {r.name: [n for n in huesos_apoyo(r) if n in r.pose.bones] for r in rigs}; raiz = {}
    for r in rigs:
        rb = [b for b in r.pose.bones if b.parent is None]; raiz[r.name] = rb[0] if rb else None
    vis = lambda o: (not o.hide_render) and (not o.hide_viewport) and max(abs(x) for x in o.matrix_world.to_scale()) > 0.001

    def leer():
        d = {"r": {}, "o": {}}
        for r in rigs:
            mw = r.matrix_world; d["r"][r.name] = ({n: mw @ r.pose.bones[n].tail for n in pies[r.name]}, (mw @ raiz[r.name].head) if raiz[r.name] else mw.translation.copy())
        for o in objs: d["o"][o.name] = (o.matrix_world.translation.copy(), vis(o), max(abs(x) for x in o.matrix_world.to_scale()))
        return d
    datos = muestrear(context, f0, f1, leer); frames = [f for f, _d in datos]; pend = []                                                  # pendientes: (frame, tipo, datos)
    for r in rigs:
        mob = mob_de_rig(r, idx); propio = idx["mobs"].get(mob, {}).get("step") if mob and mob != "player" else None
        rz = [d["r"][r.name][1] for _f, d in datos]
        if p.auto_pasos and pies[r.name]:
            mov = [(rz[min(len(rz) - 1, i + 2)] - rz[max(0, i - 2)]).xy.length / max(1, min(len(rz) - 1, i + 2) - max(0, i - 2)) > 0.004 for i in range(len(rz))]
            for a, b in _segmentos(mov):
                series = {n: [(frames[i], datos[i][1]["r"][r.name][0][n].copy()) for i in range(a, b + 1)] for n in pies[r.name]}
                for f, bn in detectar_pasos(series, p.umbral, p.lev_min, p.dist_min, p.hueco):
                    if f >= desde: pend.append((f, "paso", (r, bn, propio, mob)))
        if p.auto_cuerpo:
            for i in detectar_contacto([v.z for v in rz], fps):
                if frames[i] >= desde: pend.append((frames[i], "cuerpo", (r, mob)))
    for o in objs:
        pos = [d["o"][o.name][0] for _f, d in datos]; vs = [d["o"][o.name][1] for _f, d in datos]; es = [d["o"][o.name][2] for _f, d in datos]; info = resolver(o, idx)
        if p.auto_objetos and len(pos) > 3 and sum((pos[i] - pos[i - 1]).length for i in range(1, len(pos))) > 0.3:
            if rigs:
                cerca = min(rigs, key=lambda r: sum((pos[i] - datos[i][1]["r"][r.name][1]).length for i in range(0, len(pos), 4)))
                rel = [pos[i] - datos[i][1]["r"][cerca.name][1] for i in range(len(pos))]
            else: rel = None
            lanz, imp = detectar_objeto([(frames[i], pos[i]) for i in range(len(pos))], fps, p.v_lanzar, p.v_choque, p.alto, 8, 6, rel)
            for f in lanz:
                if f >= desde: pend.append((f, "lanzar", (o, info)))
            for f in imp:
                if f >= desde: pend.append((f, "choque", (o, info)))
        if p.auto_aparicion and info["tipo"]:
            for i in range(1, len(vs)):
                if not vs[i - 1] and vs[i] and frames[i] >= desde: pend.append((frames[i], "colocar", (o, info)))
                if vs[i - 1] and not vs[i]:
                    j = _fin_encogerse(es, i)
                    if frames[j] >= desde: pend.append((frames[j], "romper", (o, info)))
    try:
        for f, tipo, dt in sorted(pend, key=lambda x: x[0]):
            sc.frame_set(f); n = None
            if tipo == "paso":
                r, bn, propio, mob = dt; ev = propio; sup = ""
                if not ev:
                    hit = superficie_bajo(context, r.matrix_world @ r.pose.bones[bn].tail, propios(r), idx)
                    ev = idx["tipos"].get(hit[0], {}).get("step") if hit else None
                if ev: n = colocar(context, p, rutas_de(p, ev), f, "pasos", f"{ev.replace('block.', '').replace('entity.', '').replace('.', '_')}_{r.name}", p.paso_volumen, 0, rng, True)
            elif tipo == "cuerpo":
                r, mob = dt; rb = raiz[r.name]; hit = superficie_bajo(context, r.matrix_world @ rb.head, propios(r), idx) if rb else None
                ev = idx["tipos"].get(hit[0], {}).get("fall") if hit else None
                if ev: n = colocar(context, p, rutas_de(p, ev), f, "golpes", f"{ev.replace('block.', '').replace('.', '_')}_cuerpo_{r.name}", 0.7, 0, rng, True)
            elif tipo == "lanzar":
                o, info = dt; rl = rutas_preset(p, p.preset_lanzar)
                if rl[1]: n = colocar(context, p, rl[1], f, rl[2], f"{p.preset_lanzar}_{o.name}", rl[3], 0, rng, True)
            elif tipo == "choque":
                o, info = dt; hit = superficie_bajo(context, o.matrix_world.translation, {o.name} | {c.name for c in o.children_recursive}, idx); sup = hit[0] if hit else "gravel"
                ev_s = idx["tipos"].get(sup, {}).get("fall"); ev_o = idx["tipos"].get(info["tipo"], {}).get("hit") if info["tipo"] else None
                if ev_s: n = colocar(context, p, rutas_de(p, ev_s), f, "objetos", f"{ev_s.replace('block.', '').replace('.', '_')}_{o.name}", 0.9, 0, rng, True)
                if ev_o: colocar(context, p, rutas_de(p, ev_o), f, "objetos", f"{ev_o.replace('block.', '').replace('.', '_')}_{o.name}", 0.7, 0, rng, True)
            elif tipo in ("colocar", "romper"):
                o, info = dt; ev = idx["tipos"][info["tipo"]].get("place" if tipo == "colocar" else "break")
                if ev: n = colocar(context, p, rutas_de(p, ev), f, "golpes", f"{ev.replace('.', '_')}_{o.name}", 1.0, 0, rng, True)
            if n is not None: res[tipo] = res.get(tipo, 0) + 1
    finally:
        sc.frame_set(sc0)
    return res


def reajustar(context, p):
    """recalcula el tope bajo las voces de todas las tiras SND_ (por si se anadieron o cambiaron voces). Devuelve cuantas cambiaron."""
    if not p.techo_voces: return 0                                                     # con el techo apagado no se recorta nada (el microfono de camara maneja los niveles)
    sc = context.scene; tc = techo_voces(sc, p); n = 0
    if not tc: return 0
    for t in _nsnd(context):
        nv = nivel(bpy.path.abspath(t.sound.filepath)); v0 = t.get("mcsnd_vol0")
        if not nv or v0 is None: continue
        v = min(v0, tc[0] / nv[0], tc[1] / nv[1])
        if abs(v - t.volume) > 1e-4: t.volume = v; n += 1
    return n


def _fp_voces(sc):
    ed = sc.sequence_editor
    return tuple(sorted((t.name, int(t.frame_final_start), int(t.frame_final_end), round(t.volume, 3), t.mute) for t in _strips(ed) if not t.name.startswith(PREFIJO))) if ed else ()


_VIG = {"fp": {}}


def _vigilar():
    """temporizador de "Vigilar": sonoriza lo nuevo cuando el final de la escena crece y reajusta volumenes cuando cambian las voces."""
    try:
        for sc in bpy.data.scenes:
            p = getattr(sc, "mcsnd", None)
            if not p or not p.vigilar: continue
            ctx = bpy.context.copy(); ctx["scene"] = sc
            fp = _fp_voces(sc); ant = _VIG["fp"].get(sc.name)
            _VIG["fp"][sc.name] = fp
            if sc.frame_end > p.auto_hasta > 0:
                with bpy.context.temp_override(scene=sc): bpy.ops.mcsnd.sonorizar(modo="NUEVO")
            elif ant is not None and ant != fp:
                with bpy.context.temp_override(scene=sc): reajustar(bpy.context, p)
    except Exception as e: print("[Sonidos MC] vigilar:", e)
    return 5.0


# ------------------------------------------------------------------------------------------------------------------------------------ propiedades
class McItem(PropertyGroup):
    name: StringProperty()
    n: IntProperty()
    familia: StringProperty()


PRESET_ITEMS = [(k, v[0], "/".join(v[1])) for k, v in PRESETS.items()]


class McProps(PropertyGroup):
    carpeta: StringProperty(name="Carpeta de sonidos", subtype='DIR_PATH', default=CARPETA)
    modo: EnumProperty(name="Ver", items=[("EVENTOS", "Eventos", "Eventos de sounds.json (p. ej. entity.wolf.howl)"), ("ARCHIVOS", "Archivos", "Archivos .ogg sueltos por carpeta")], default="EVENTOS")
    items: CollectionProperty(type=McItem)
    activo: IntProperty()
    variante: IntProperty(name="Variante", description="0 = al azar entre las variantes del evento", default=0, min=0, max=200)
    volumen_general: FloatProperty(name="Volumen", default=1.0, min=0.0, max=4.0)
    techo_voces: BoolProperty(name="Por debajo de las voces", description="limita cada sonido para que quede por debajo de la voz mas baja de la escena", default=True)
    margen_pico: FloatProperty(name="Margen pico (dB)", description="el pico del sonido queda este margen por debajo del pico de la voz", default=8.0, min=0.0, max=40.0)
    margen_rms: FloatProperty(name="Margen medio (dB)", description="el volumen medio del sonido queda este margen por debajo del medio de la voz", default=3.0, min=0.0, max=40.0)
    variacion: FloatProperty(name="Variacion", description="variacion aleatoria del volumen de cada sonido", default=0.12, min=0.0, max=0.9)
    semilla: IntProperty(name="Semilla", default=1)
    canal_por_tipo: BoolProperty(name="Canal por tipo", description="cada tipo (pasos, antorcha, objetos...) va a su fila de canales", default=True)
    canal: IntProperty(name="Canal", default=20, min=1, max=128)
    frame_manual: BoolProperty(name="Frame propio", description="en vez del frame actual", default=False)
    frame: IntProperty(name="Frame", default=1)
    preset: EnumProperty(name="Evento", items=PRESET_ITEMS)
    # pasos
    rig: PointerProperty(name="Personaje", type=bpy.types.Object, poll=lambda s, o: o.type == 'ARMATURE')
    huesos: StringProperty(name="Huesos de apoyo", description="separados por coma (se usa la COLA del hueso); vacio = automatico")
    preset_paso: EnumProperty(name="Superficie", items=[(k, v[0], "") for k, v in PRESETS.items() if k.startswith("paso_")], default="paso_madera")
    rango_escena: BoolProperty(name="Rango de la escena", default=True)
    f_ini: IntProperty(name="Inicio", default=1)
    f_fin: IntProperty(name="Fin", default=100)
    umbral: FloatProperty(name="Umbral de contacto", description="el pie cuenta como apoyado cuando baja a esta fraccion de lo que se levanta (0 = el punto mas bajo)", default=0.35, min=0.05, max=0.9)
    lev_min: FloatProperty(name="Levantamiento minimo (m)", description="un pie que no se levanta al menos esto en el rango no suena", default=0.015, min=0.0, max=1.0)
    dist_min: FloatProperty(name="Avance minimo (m)", description="un pie solo hace otro paso si ha avanzado esta distancia desde el anterior (evita ruido al estar quieto)", default=0.08, min=0.0, max=2.0)
    hueco: IntProperty(name="Separacion minima (f)", default=4, min=1, max=60)
    paso_modo: EnumProperty(name="Sonido del paso", items=[("JUEGO", "Como en el juego", "mob con paso propio: su evento (zombie, lobo...); si no, el sonido de la superficie bajo el pie en ese frame"), ("MANUAL", "Superficie fija", "siempre la superficie elegida")], default="JUEGO")
    paso_volumen: FloatProperty(name="Volumen de pasos", description="en el juego los pasos suenan mas bajo que el resto", default=0.5, min=0.0, max=2.0)
    # objetos
    preset_lanzar: EnumProperty(name="Al salir disparado", items=PRESET_ITEMS, default="lanzar")
    preset_impacto: EnumProperty(name="Al chocar", items=PRESET_ITEMS, default="herr_madera")
    impacto_modo: EnumProperty(name="Sonido del choque", items=[("JUEGO", "Como en el juego", "superficie de abajo (fall) + material del objeto (hit)"), ("MANUAL", "Evento fijo", "el evento elegido en 'Al chocar'")], default="JUEGO")
    ap_colocar: BoolProperty(name="Al aparecer: colocar", default=True)
    ap_romper: BoolProperty(name="Al desaparecer: romper", default=True)
    info: StringProperty()
    auto_pasos: BoolProperty(name="Pasos", default=True)
    auto_cuerpo: BoolProperty(name="Cuerpo (sentarse / caer)", default=True)
    auto_objetos: BoolProperty(name="Objetos (lanzar / chocar)", default=True)
    auto_aparicion: BoolProperty(name="Aparecer / romper", default=True)
    auto_hasta: IntProperty(name="Sonorizado hasta", description="ultimo frame sonorizado automaticamente (0 = nada)", default=0, min=0)
    vigilar: BoolProperty(name="Vigilar", description="cada 5 s: sonoriza lo nuevo si el final de la escena crece y reajusta volumenes si cambian las voces", default=False)
    usar_lanzar: BoolProperty(name="Sonido al lanzar", default=True)
    usar_impacto: BoolProperty(name="Sonido al chocar", default=True)
    v_lanzar: FloatProperty(name="Velocidad de lanzamiento (m/s)", default=2.0, min=0.2, max=50.0)
    v_choque: FloatProperty(name="Velocidad minima de choque (m/s)", default=1.0, min=0.1, max=50.0)
    alto: FloatProperty(name="Altura max. del choque (m)", description="sobre el punto mas bajo del objeto", default=0.25, min=0.02, max=5.0)
    # bucle
    preset_bucle: EnumProperty(name="Sonido", items=PRESET_ITEMS, default="antorcha")
    b_ini: IntProperty(name="Inicio", default=1)
    b_fin: IntProperty(name="Fin", default=480)
    solape: IntProperty(name="Solape (f)", description="cada repeticion empieza este numero de frames antes de que acabe la anterior", default=4, min=0, max=30)
    mezcla: StringProperty(name="Archivo .wav", subtype='FILE_PATH', default="//mezcla_audio.wav", options={'PATH_SUPPORTS_BLEND_RELATIVE'})


def P(ctx): return ctx.scene.mcsnd


def _rango(p, ctx):
    return (ctx.scene.frame_start, ctx.scene.frame_end) if p.rango_escena else (p.f_ini, p.f_fin)


def _frame(p, ctx):
    return p.frame if p.frame_manual else ctx.scene.frame_current


def _nsnd(ctx):
    ed = ctx.scene.sequence_editor
    return [s for s in _strips(ed) if s.name.startswith(PREFIJO)] if ed else []


# ------------------------------------------------------------------------------------------------------------------------------------ operadores
class MCSND_OT_indexar(Operator):
    bl_idname = "mcsnd.indexar"; bl_label = "Leer biblioteca"; bl_description = "Lee sounds.json y la carpeta sounds/ y llena la lista"

    def execute(self, context):
        p = P(context)
        try: idx = indice(p, True)
        except Exception as e:
            self.report({'ERROR'}, str(e)); return {'CANCELLED'}
        p.items.clear()
        if p.modo == "EVENTOS":
            for ev in sorted(idx["eventos"]):
                it = p.items.add(); it.name = ev; it.n = len(idx["eventos"][ev]); it.familia = ev.split(".")[0]
        else:
            for a in idx["archivos"]:
                it = p.items.add(); it.name = a; it.n = 1; it.familia = a.split("/")[0]
        p.activo = 0
        self.report({'INFO'}, f"{len(idx['eventos'])} eventos, {len(idx['archivos'])} archivos"); return {'FINISHED'}


class MCSND_OT_probar(Operator):
    bl_idname = "mcsnd.probar"; bl_label = "Escuchar"; bl_description = "Reproduce el sonido elegido (variante elegida o al azar)"
    detener: BoolProperty(default=False)
    nombre: StringProperty()

    def execute(self, context):
        p = P(context)
        try:
            import aud
            if _ST["play"]:
                try: _ST["play"].stop()
                except Exception: pass
                _ST["play"] = None
            if self.detener: return {'FINISHED'}
            nombre = self.nombre or (p.items[p.activo].name if p.items else "")
            rs = rutas_de(p, nombre)
            if not rs: self.report({'WARNING'}, "Sin sonido"); return {'CANCELLED'}
            ruta, vj = rs[(p.variante - 1) % len(rs)] if p.variante > 0 else random.choice(rs)
            _ST["play"] = aud.Device().play(aud.Sound(ruta).volume(min(vj * p.volumen_general, 4.0)))
        except Exception as e:
            self.report({'ERROR'}, f"No se pudo reproducir: {e}"); return {'CANCELLED'}
        return {'FINISHED'}


class MCSND_OT_anadir(Operator):
    bl_idname = "mcsnd.anadir"; bl_label = "Anadir al frame"; bl_description = "Pone el sonido elegido de la lista en el frame actual (o el frame propio)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        p = P(context)
        if not p.items: self.report({'WARNING'}, "Lee la biblioteca primero"); return {'CANCELLED'}
        nombre = p.items[p.activo].name; rs = rutas_de(p, nombre)
        if not rs: self.report({'WARNING'}, "Sin sonido"); return {'CANCELLED'}
        t = colocar(context, p, rs, _frame(p, context), "ambiente" if p.modo == "ARCHIVOS" else "objetos", nombre.replace("/", ".").replace(" ", "_"), 1.0, p.variante, rng_de(p))
        p.semilla += 1; self.report({'INFO'}, f"{t.name} (canal {t.channel})"); return {'FINISHED'}


class MCSND_OT_preset(Operator):
    bl_idname = "mcsnd.preset"; bl_label = "Anadir evento"; bl_description = "Pone el evento del proyecto en el frame actual (o el frame propio)"
    bl_options = {'REGISTER', 'UNDO'}
    preset: StringProperty()

    def execute(self, context):
        p = P(context); pid = self.preset or p.preset
        et, rs, g, v = rutas_preset(p, pid)
        if not rs: self.report({'WARNING'}, f"Sin archivos para {et}"); return {'CANCELLED'}
        t = colocar(context, p, rs, _frame(p, context), g, pid, v, p.variante, rng_de(p)); p.semilla += 1
        self.report({'INFO'}, f"{et}: {t.name} (canal {t.channel})"); return {'FINISHED'}


class MCSND_OT_pasos(Operator):
    bl_idname = "mcsnd.pasos"; bl_label = "Detectar y anadir pasos"; bl_description = "Lee la animacion del personaje y pone un paso en cada contacto de pie con el suelo"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        p = P(context); rig = p.rig or (context.active_object if context.active_object and context.active_object.type == 'ARMATURE' else None)
        if not rig: self.report({'WARNING'}, "Elige el personaje (armature)"); return {'CANCELLED'}
        nombres = [n.strip() for n in p.huesos.split(",") if n.strip()] or huesos_apoyo(rig)
        nombres = [n for n in nombres if n in rig.pose.bones]
        if not nombres: self.report({'ERROR'}, "No encuentro huesos de apoyo; escribelos en 'Huesos de apoyo'"); return {'CANCELLED'}
        f0, f1 = _rango(p, context); et, rs, g, v = rutas_preset(p, p.preset_paso)
        idx = indice(p); mob = mob_de_rig(rig, idx) if p.paso_modo == "JUEGO" else None
        propio = idx["mobs"].get(mob, {}).get("step") if mob and mob != "player" else None                     # el jugador (Alfred) suena segun la superficie; los mobs con paso propio, con el suyo
        if p.paso_modo == "MANUAL" and not rs: self.report({'WARNING'}, "Sin archivos de pasos"); return {'CANCELLED'}
        cola = {n: rig.pose.bones[n] for n in nombres}
        datos = muestrear(context, f0, f1, lambda: {n: rig.matrix_world @ b.tail for n, b in cola.items()})
        series = {n: [(f, d[n].copy()) for f, d in datos] for n in nombres}
        pasos = detectar_pasos(series, p.umbral, p.lev_min, p.dist_min, p.hueco); rng = rng_de(p); usados = {}; ignorar = propios(rig) if p.paso_modo == "JUEGO" else set(); sc = context.scene; actual = sc.frame_current
        try:
            for f, b in pasos:
                if p.paso_modo == "MANUAL": rutas, etq, grp = rs, p.preset_paso, g
                else:
                    ev = propio; sup = ""
                    if not ev:
                        sc.frame_set(f); hit = superficie_bajo(context, rig.matrix_world @ cola[b].tail, ignorar, idx)
                        tipo, sup = hit if hit else (None, "")
                        ev = idx["tipos"].get(tipo, {}).get("step") if tipo else None
                    if not ev: rutas, etq, grp = rs, p.preset_paso, g                                      # sin suelo reconocido: la superficie elegida
                    else: rutas, etq, grp = rutas_de(p, ev), ev.replace("block.", "").replace("entity.", "").replace(".", "_"), "pasos"
                    usados[etq] = usados.get(etq, 0) + 1
                if rutas: colocar(context, p, rutas, f, grp, f"{etq}_{rig.name}", p.paso_volumen if p.paso_modo == "JUEGO" else v, 0, rng)
        finally: sc.frame_set(actual)
        p.semilla += 1; extra = (" | " + ", ".join(f"{k} x{n}" for k, n in usados.items())) if usados else ""
        self.report({'INFO'}, f"{len(pasos)} pasos ({', '.join(nombres)}) en f{f0}-{f1}{extra}"); return {'FINISHED'}


class MCSND_OT_objetos(Operator):
    bl_idname = "mcsnd.objetos"; bl_label = "Detectar lanzamientos e impactos"; bl_description = "Para los objetos seleccionados: silbido cuando salen disparados y golpe cuando chocan contra el suelo"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        p = P(context); objs = [o for o in context.selected_objects] or ([context.active_object] if context.active_object else [])
        if not objs: self.report({'WARNING'}, "Selecciona los objetos"); return {'CANCELLED'}
        f0, f1 = _rango(p, context); fps = context.scene.render.fps / context.scene.render.fps_base; rng = rng_de(p); nl = ni = 0
        rl = rutas_preset(p, p.preset_lanzar); ri = rutas_preset(p, p.preset_impacto); idx = indice(p)
        datos = muestrear(context, f0, f1, lambda: {o.name: o.matrix_world.translation.copy() for o in objs})
        sc = context.scene; actual = sc.frame_current
        try:
            for o in objs:
                ser = [(f, d[o.name]) for f, d in datos]
                lanz, imp = detectar_objeto(ser, fps, p.v_lanzar, p.v_choque, p.alto, 8, 6); info = resolver(o, idx)
                if p.usar_lanzar and rl[1]:
                    for f in lanz: colocar(context, p, rl[1], f, rl[2], f"{p.preset_lanzar}_{o.name}", rl[3], 0, rng); nl += 1
                if not p.usar_impacto: continue
                for f in imp:
                    if p.impacto_modo == "MANUAL":
                        if ri[1]: colocar(context, p, ri[1], f, ri[2], f"{p.preset_impacto}_{o.name}", ri[3], 0, rng); ni += 1
                        continue
                    sc.frame_set(f); hit = superficie_bajo(context, o.matrix_world.translation, {o.name} | {c.name for c in o.children_recursive}, idx); sup = hit[0] if hit else "wood"
                    ev_sup = idx["tipos"].get(sup, {}).get("fall"); ev_obj = idx["tipos"].get(info["tipo"], {}).get("hit") if info["tipo"] else None
                    if ev_sup: colocar(context, p, rutas_de(p, ev_sup), f, "objetos", f"{ev_sup.replace('block.', '').replace('.', '_')}_{o.name}", 0.9, 0, rng)
                    if ev_obj: colocar(context, p, rutas_de(p, ev_obj), f, "objetos", f"{ev_obj.replace('block.', '').replace('.', '_')}_{o.name}", 0.7, 0, rng)
                    ni += 1
        finally: sc.frame_set(actual)
        p.semilla += 1; self.report({'INFO'}, f"{nl} lanzamientos y {ni} impactos en f{f0}-{f1}"); return {'FINISHED'}


class MCSND_OT_objeto_evento(Operator):
    bl_idname = "mcsnd.objeto_evento"; bl_label = "Sonido del objeto"; bl_description = "Pone en el frame actual el sonido de ese evento del juego"
    bl_options = {'REGISTER', 'UNDO'}
    evento: StringProperty()
    volumen: FloatProperty(default=1.0)

    def execute(self, context):
        p = P(context); rs = rutas_de(p, self.evento)
        if not rs: self.report({'WARNING'}, f"Sin archivos para {self.evento}"); return {'CANCELLED'}
        ob = context.active_object; sufijo = f"_{ob.name}" if ob else ""
        t = colocar(context, p, rs, _frame(p, context), "voces" if self.evento.startswith("entity.") else "golpes", self.evento.replace(".", "_") + sufijo, self.volumen, p.variante, rng_de(p)); p.semilla += 1
        self.report({'INFO'}, f"{self.evento}: {t.name} (canal {t.channel})"); return {'FINISHED'}


class MCSND_OT_aparicion(Operator):
    bl_idname = "mcsnd.aparicion"; bl_label = "Detectar aparecer / desaparecer"; bl_description = "Objetos seleccionados: sonido de COLOCAR cuando aparecen y de ROMPER cuando desaparecen (visibilidad o escala animadas), segun su tipo de bloque"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        p = P(context); objs = list(context.selected_objects) or ([context.active_object] if context.active_object else [])
        if not objs: self.report({'WARNING'}, "Selecciona los objetos"); return {'CANCELLED'}
        idx = indice(p); f0, f1 = _rango(p, context); rng = rng_de(p); nc = nr = 0
        vis = lambda o: (not o.hide_render) and (not o.hide_viewport) and max(abs(x) for x in o.matrix_world.to_scale()) > 0.001
        datos = muestrear(context, f0, f1, lambda: {o.name: vis(o) for o in objs})
        for o in objs:
            info = resolver(o, idx)
            if not info["tipo"]: continue
            ev_p = idx["tipos"][info["tipo"]].get("place"); ev_b = idx["tipos"][info["tipo"]].get("break")
            for (fa, da), (fb, db) in zip(datos, datos[1:]):
                if not da[o.name] and db[o.name] and p.ap_colocar and ev_p: colocar(context, p, rutas_de(p, ev_p), fb, "golpes", f"{ev_p.replace('.', '_')}_{o.name}", 1.0, 0, rng); nc += 1
                if da[o.name] and not db[o.name] and p.ap_romper and ev_b: colocar(context, p, rutas_de(p, ev_b), fb, "golpes", f"{ev_b.replace('.', '_')}_{o.name}", 1.0, 0, rng); nr += 1
        p.semilla += 1; self.report({'INFO'}, f"{nc} colocados y {nr} rotos en f{f0}-{f1}"); return {'FINISHED'}


class MCSND_OT_analizar(Operator):
    bl_idname = "mcsnd.analizar"; bl_label = "Analizar objetos"; bl_description = "Muestra que sonido del juego le corresponde a cada objeto seleccionado (o a todos los visibles)"

    def execute(self, context):
        p = P(context); idx = indice(p); objs = list(context.selected_objects) or [o for o in context.visible_objects if o.type in {'MESH', 'ARMATURE'}]
        filas = []; cuenta = {}
        for o in objs:
            r = resolver(o, idx); k = r["tipo"] or r["mob"] or "?"; cuenta[(r["clase"], k)] = cuenta.get((r["clase"], k), 0) + 1
            if r["clase"] and len(filas) < 24: filas.append(f"{o.name}: {r['clase']} {r['tipo'] or r['mob']} ({r['fuente']})")
        resumen = ", ".join(f"{c or 'sin tipo'} {k} x{n}" for (c, k), n in sorted(cuenta.items(), key=lambda x: -x[1])[:10])
        p.info = "\n".join([resumen] + filas); print("[Sonidos MC] " + p.info)
        self.report({'INFO'}, resumen); return {'FINISHED'}


class MCSND_OT_sonorizar(Operator):
    bl_idname = "mcsnd.sonorizar"; bl_label = "Sonorizar la historia"; bl_description = "Lee la animacion de la escena y pone los sonidos solo (pasos, cuerpo, objetos, aparecer / romper), por debajo de las voces"
    bl_options = {'REGISTER', 'UNDO'}
    modo: EnumProperty(items=[("TODO", "Todo", "rehace los sonidos automaticos de toda la escena"), ("NUEVO", "Solo lo nuevo", "desde el ultimo frame sonorizado hasta el final")], default="TODO")

    def execute(self, context):
        p = P(context); sc = context.scene; f1 = sc.frame_end
        if self.modo == "NUEVO" and p.auto_hasta > 0:
            if f1 <= p.auto_hasta: self.report({'INFO'}, f"Ya sonorizado hasta f{p.auto_hasta}"); return {'FINISHED'}
            f0 = max(sc.frame_start, p.auto_hasta - 24); desde = p.auto_hasta - 1                                  # 24 f de contexto para detectar y se omite lo que ya esta
        else:
            f0 = sc.frame_start; desde = f0; ed = sc.sequence_editor
            for t in [t for t in (_strips(ed) if ed else []) if t.get("mcsnd_auto")]: _strips(ed).remove(t)
        try: res = sonorizar_auto(context, p, f0, f1, desde)
        except Exception as e:
            import traceback; traceback.print_exc(); self.report({'ERROR'}, str(e)); return {'CANCELLED'}
        p.auto_hasta = f1; aj = reajustar(context, p)
        self.report({'INFO'}, f"f{f0}-{f1}: " + (", ".join(f"{k} x{n}" for k, n in sorted(res.items())) or "nada nuevo") + (f" | {aj} volumenes reajustados" if aj else "")); return {'FINISHED'}


class MCSND_OT_reajustar(Operator):
    bl_idname = "mcsnd.reajustar"; bl_label = "Reajustar volumenes"; bl_description = "Vuelve a limitar todos los sonidos para que queden por debajo de las voces actuales"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        n = reajustar(context, P(context)); self.report({'INFO'}, f"{n} sonidos reajustados"); return {'FINISHED'}


class MCSND_OT_bucle(Operator):
    bl_idname = "mcsnd.bucle"; bl_label = "Rellenar rango"; bl_description = "Repite el sonido (variantes al azar) de punta a punta del rango"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        p = P(context); et, rs, g, v = rutas_preset(p, p.preset_bucle)
        if not rs: self.report({'WARNING'}, "Sin archivos"); return {'CANCELLED'}
        rng = rng_de(p); f = p.b_ini; n = 0
        while f < p.b_fin and n < 2000:
            t = colocar(context, p, rs, f, g, p.preset_bucle, v, 0, rng); n += 1
            if t.frame_final_end > p.b_fin: t.frame_final_end = p.b_fin; break
            f = max(f + 1, int(t.frame_final_end) - p.solape)
        p.semilla += 1; self.report({'INFO'}, f"{n} tiras en f{p.b_ini}-{p.b_fin}"); return {'FINISHED'}


class MCSND_OT_quitar(Operator):
    bl_idname = "mcsnd.quitar"; bl_label = "Quitar sonidos"; bl_description = "Quita las tiras SND_ (todas, o solo las de un tipo)"
    bl_options = {'REGISTER', 'UNDO'}
    grupo: StringProperty(default="")
    solo_rango: BoolProperty(default=False)

    def execute(self, context):
        ed = context.scene.sequence_editor; n = 0
        if not ed: return {'CANCELLED'}
        p = P(context)
        for s in list(_nsnd(context)):
            if self.grupo and s.get("mcsnd") != self.grupo: continue
            if self.solo_rango and not (p.b_ini <= s.frame_final_start <= p.b_fin): continue
            _strips(ed).remove(s); n += 1
        self.report({'INFO'}, f"{n} tiras quitadas"); return {'FINISHED'}


class MCSND_OT_mezcla(Operator):
    bl_idname = "mcsnd.mezcla"; bl_label = "Mezcla WAV"; bl_description = "Exporta todo el audio de la escena (voces + sonidos) a un .wav"

    def execute(self, context):
        p = P(context); ruta = bpy.path.abspath(p.mezcla)
        if not ruta.lower().endswith(".wav"): ruta += ".wav"
        try: bpy.ops.sound.mixdown(filepath=ruta, check_existing=False, container='WAV', codec='PCM', format='S16')
        except Exception as e:
            self.report({'ERROR'}, str(e)); return {'CANCELLED'}
        self.report({'INFO'}, ruta); return {'FINISHED'}


# ------------------------------------------------------------------------------------------------------------------------------------ interfaz
class MCSND_UL_lista(UIList):
    def draw_item(self, _ctx, layout, _data, item, _icon, _active, _prop):
        fila = layout.row(align=True); fila.label(text=item.name); fila.label(text=str(item.n) if item.n > 1 else "")

    def filter_items(self, _ctx, data, propname):
        items = getattr(data, propname); busca = self.filter_name.lower().replace("*", "")
        flt = [self.bitflag_filter_item if (not busca or all(w in it.name.lower() for w in busca.split())) else 0 for it in items]
        return flt, []


def _dibujar(self, context):
    l = self.layout; p = P(context)
    c = l.box().column(align=True); c.label(text="Sonorizar la historia (automatico)", icon='PLAY_SOUND')
    f = c.row(align=True); f.prop(p, "auto_pasos"); f.prop(p, "auto_cuerpo")
    f = c.row(align=True); f.prop(p, "auto_objetos"); f.prop(p, "auto_aparicion")
    f = c.row(align=True); op = f.operator("mcsnd.sonorizar", text="Todo", icon='FILE_REFRESH'); op.modo = "TODO"; op = f.operator("mcsnd.sonorizar", text="Solo lo nuevo", icon='FORWARD'); op.modo = "NUEVO"
    f = c.row(align=True); f.operator("mcsnd.reajustar", icon='SPEAKER'); f.prop(p, "vigilar", toggle=True)
    c.label(text=f"Sonorizado hasta f{p.auto_hasta}" if p.auto_hasta else "Sin sonorizar", icon='INFO')
    c = l.box().column(align=True); c.label(text="Biblioteca", icon='SOUND')
    c.prop(p, "carpeta", text="")
    f = c.row(align=True); f.prop(p, "modo", expand=True); f.operator("mcsnd.indexar", text="", icon='FILE_REFRESH')
    c.template_list("MCSND_UL_lista", "", p, "items", p, "activo", rows=6)
    f = c.row(align=True); f.prop(p, "variante"); f.prop(p, "volumen_general")
    f = c.row(align=True); f.operator("mcsnd.probar", icon='PLAY'); op = f.operator("mcsnd.probar", text="", icon='SNAP_FACE'); op.detener = True; f.operator("mcsnd.anadir", icon='ADD')
    f = c.row(align=True); f.prop(p, "frame_manual"); sub = f.row(); sub.enabled = p.frame_manual; sub.prop(p, "frame", text="")
    f = c.row(align=True); f.prop(p, "variacion"); f.prop(p, "semilla")
    f = c.row(align=True); f.prop(p, "techo_voces")
    if p.techo_voces: f.prop(p, "margen_pico", text="Pico"); f.prop(p, "margen_rms", text="Medio")
    f = c.row(align=True); f.prop(p, "canal_por_tipo"); sub = f.row(); sub.enabled = not p.canal_por_tipo; sub.prop(p, "canal", text="")
    c = l.box().column(align=True); c.label(text="Objeto activo (como en el juego)", icon='MESH_CUBE')
    ob = context.active_object
    if ob:
        try:
            r = resolver(ob, indice(p)); idx = indice(p)
            c.label(text=f"{ob.name}: {r['clase'] or 'sin sonido'} {r['tipo'] or r['mob'] or ''}" + (f"  ({r['fuente']})" if r["fuente"] else ""))
            if r["clase"] in ("bloque", "herramienta") and r["tipo"]:
                f = c.row(align=True)
                for acc, et in ACCIONES_BLOQUE:
                    ev = idx["tipos"].get(r["tipo"], {}).get(acc)
                    if ev: op = f.operator("mcsnd.objeto_evento", text=et); op.evento = ev
            elif r["clase"] == "mob":
                g = c.grid_flow(columns=2, align=True)
                for acc, ev in sorted(idx["mobs"].get(r["mob"], {}).items())[:16]:
                    op = g.operator("mcsnd.objeto_evento", text=acc.replace("_", " ")); op.evento = ev
        except Exception as e: c.label(text=f"({e})")
    else: c.label(text="Selecciona un objeto")
    f = c.row(align=True); f.prop(p, "ap_colocar"); f.prop(p, "ap_romper")
    f = c.row(align=True); f.operator("mcsnd.aparicion", icon='PLAY'); f.operator("mcsnd.analizar", icon='VIEWZOOM')
    for linea in p.info.split("\n")[:12]: c.label(text=linea)
    c = l.box().column(align=True); c.label(text="Eventos del proyecto", icon='OUTLINER_OB_SPEAKER')
    c.prop(p, "preset", text=""); c.operator("mcsnd.preset", icon='ADD')
    c = l.box().column(align=True); c.label(text="Pasos automaticos", icon='MOD_DYNAMICPAINT')
    c.prop(p, "rig"); c.prop(p, "huesos"); c.prop(p, "paso_modo", text=""); c.prop(p, "paso_volumen"); c.prop(p, "preset_paso", text="Si no hay suelo")
    f = c.row(align=True); f.prop(p, "rango_escena")
    if not p.rango_escena: f.prop(p, "f_ini", text="De"); f.prop(p, "f_fin", text="a")
    c.prop(p, "umbral"); c.prop(p, "lev_min"); c.prop(p, "dist_min"); c.prop(p, "hueco"); c.operator("mcsnd.pasos", icon='PLAY')
    c = l.box().column(align=True); c.label(text="Objetos lanzados (selecciona los objetos)", icon='OBJECT_DATA')
    f = c.row(align=True); f.prop(p, "usar_lanzar"); f.prop(p, "usar_impacto")
    c.prop(p, "impacto_modo", text=""); c.prop(p, "preset_lanzar"); c.prop(p, "preset_impacto"); c.prop(p, "v_lanzar"); c.prop(p, "v_choque"); c.prop(p, "alto"); c.operator("mcsnd.objetos", icon='PLAY')
    c = l.box().column(align=True); c.label(text="Bucle (antorcha, fuego, ambiente)", icon='FILE_REFRESH')
    c.prop(p, "preset_bucle", text=""); f = c.row(align=True); f.prop(p, "b_ini", text="De"); f.prop(p, "b_fin", text="a"); c.prop(p, "solape"); c.operator("mcsnd.bucle", icon='PLAY')
    c = l.box().column(align=True); c.label(text=f"En la escena: {len(_nsnd(context))} sonidos", icon='SEQUENCE')
    f = c.row(align=True)
    for g in GRUPOS: op = f.operator("mcsnd.quitar", text=g[:4]); op.grupo = g
    op = c.operator("mcsnd.quitar", text="Quitar todos", icon='TRASH'); op.grupo = ""
    c.prop(p, "mezcla", text=""); c.operator("mcsnd.mezcla", icon='EXPORT')


def _crear_panel(espacio, sufijo):
    return type(f"MCSND_PT_principal{sufijo}", (Panel,), {"bl_idname": f"MCSND_PT_principal{sufijo}", "bl_label": "Sonidos MC", "bl_space_type": espacio, "bl_region_type": 'UI', "bl_category": "Sonidos MC", "draw": _dibujar})


PANELES = [_crear_panel('VIEW_3D', "_3d"), _crear_panel('SEQUENCE_EDITOR', "_seq")]
CLASES = [McItem, McProps, MCSND_UL_lista, MCSND_OT_indexar, MCSND_OT_probar, MCSND_OT_anadir, MCSND_OT_preset, MCSND_OT_pasos, MCSND_OT_objetos, MCSND_OT_sonorizar, MCSND_OT_reajustar, MCSND_OT_objeto_evento, MCSND_OT_aparicion, MCSND_OT_analizar, MCSND_OT_bucle, MCSND_OT_quitar, MCSND_OT_mezcla] + PANELES


def _llenar():
    try:
        sc = bpy.context.scene
        if sc and hasattr(sc, "mcsnd") and not sc.mcsnd.items: bpy.ops.mcsnd.indexar()
    except Exception as e: print("[Sonidos MC]", e)
    return None


@bpy.app.handlers.persistent
def _al_abrir(_a=None):
    _ST["idx"] = None; bpy.app.timers.register(_llenar, first_interval=0.5)


def register():
    for c in CLASES: bpy.utils.register_class(c)
    bpy.types.Scene.mcsnd = PointerProperty(type=McProps)
    if _al_abrir not in bpy.app.handlers.load_post: bpy.app.handlers.load_post.append(_al_abrir)
    bpy.app.timers.register(_llenar, first_interval=0.5)
    if not bpy.app.timers.is_registered(_vigilar): bpy.app.timers.register(_vigilar, first_interval=5.0, persistent=True)


def unregister():
    if bpy.app.timers.is_registered(_vigilar): bpy.app.timers.unregister(_vigilar)
    if _al_abrir in bpy.app.handlers.load_post: bpy.app.handlers.load_post.remove(_al_abrir)
    del bpy.types.Scene.mcsnd
    for c in reversed(CLASES): bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
