# -*- coding: utf-8 -*-
"""Alfred Efectos - sincroniza los efectos de la carpeta `efectos` con la animacion (pensado para que la IA lo use con pocas llamadas).

QUE HAY EN LA CARPETA (analizado, 47 .blend):
  - sprites  : `<Nombre>_frame.blend` (Angry, Critical, Damage, Heart, Explosion, Generic, Spark, Sweep, Sculk_*, Soul...) = UNA particula de Minecraft: un EMPTY que instancia una coleccion de
               "laminas" (una por cuadro de la animacion) que se ven de a una con llaves hide_viewport / hide_render. Duran de 1 a 27 frames. Una particula sola no es un efecto: hay que EMITIR varias.
  - tnt      : TNT_slow_explode_frame_1 / TNT_instant_explode_1 = bloque que parpadea + explosiones + humo (particulas). Duran 103 y 12 frames.
  - clima    : Rain, Snow, Ash, Spores, Firefly, Leafy_Wind (modificador de nodos "Camera Weather Nodes", sigue a la camara) y Rain_1, Snow_1 (sistema de particulas).
  - modelo   : trueno.blend (rayos 3D), burbuja.blend (Bubble) y charco_de_agua.blend (Bubble pop) = sprites.
  Todos los sprites y los TNT empiezan en un frame fijo del archivo (casi siempre 0); el addon CLONA el efecto con las llaves movidas al frame que pidas (y estiradas a la duracion que pidas),
  asi cada efecto empieza donde quieres y no se pisa con los demas.

USO PARA LA IA (todo en `fx`, sin interfaz):
    import importlib.util, sys
    spec = importlib.util.spec_from_file_location("alfred_efectos_local", r"C:\\Users\\user\\Desktop\\Alfred_Animacion\\capitulos\\capitulo_4\\alfred_efectos\\__init__.py")
    fx = importlib.util.module_from_spec(spec); sys.modules["alfred_efectos_local"] = fx; spec.loader.exec_module(fx); fx.register()
    fx.catalogo()                                  # lista de efectos: id, etiqueta, tipo, duracion, etiquetas de uso
    fx.buscar("golpe")                             # busca por palabra (golpe, humo, fuego, magia, curar, agua, polvo, explosion...)
    fx.colocar("Critical_frame", 58, en="alfred:Rightelbow_alfred", patron="radial", cantidad=8)      # un efecto en un frame
    fx.colocar("Generic_frame", 83, en=(-45.5, -14.5, -6.0), patron="radial", cantidad=14, vida=16)  # en una posicion del mundo
    fx.colocar("Rain_1", 1, hasta=240)                                                                # clima entre dos frames
    fx.plan_aplicar([{...}, {...}])                # lista de efectos de una vez (idempotente: cada "id" se rehace)
    fx.eventos(1, 250)                             # detecta en la animacion: impactos, lanzamientos, apariciones, desapariciones
    fx.sugerir(1, 250); fx.aplicar_sugerencias()   # propone y pone efectos segun esos eventos
    fx.desde_sonidos(en="alfred")                  # pone efectos en los frames de las tiras SND_ (add-on Alfred Sonidos)
    fx.estado(); fx.quitar("id"); fx.quitar()      # ver lo puesto / quitar uno / quitar todo
  `en` acepta: (x, y, z) | "Objeto" | "Objeto:Hueso" (cabeza del hueso) | "Objeto:Hueso:tail" | "cursor" | {"objeto":.., "hueso":.., "punto":"tail"}; con `desplazar=(dx,dy,dz)` se mueve en el mundo.
  `seguir=True` hornea la posicion del objeto / hueso durante la vida del efecto (si se mueve).
Todo lo que crea el addon lleva el prefijo `FX_`, la propiedad `fx_id` y vive en la coleccion `FX_efectos`; las plantillas cargadas, ocultas, en `FX_biblioteca`.
"""
bl_info = {
    "name": "Alfred Efectos",
    "author": "Kebyn",
    "version": (1, 0, 0),
    "blender": (4, 4, 0),
    "location": "Vista 3D > barra lateral (N) > Efectos MC",
    "description": "Pone los efectos de Minecraft (particulas por cuadros, TNT, clima, trueno) en el frame y el lugar de la animacion; detecta eventos y los sincroniza solo",
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

CARPETA = r"C:\Users\user\Desktop\Alfred_Animacion\efectos"
COL_FX, COL_BIB = "FX_efectos", "FX_biblioteca"
PREFIJO = "FX_"

# id (nombre del .blend sin extension): (etiqueta, tipo, [etiquetas de uso], patron, vida, escala, nota)
CATALOGO = {
    "Angry_frame": ("Ira: vena de enfado", "sprites", ["enojo", "ira", "enfado", "furia", "grito", "angry"], "sube", 14, 1.0, "particula villager_angry"),
    "Big_smoke_frame": ("Humo grande", "sprites", ["humo", "fuego", "apagar", "vapor", "smoke", "desaparece"], "sube", 24, 1.4, "humo denso de fogata o fuego que se apaga"),
    "Cherry_frame": ("Petalos de cerezo", "sprites", ["petalos", "cerezo", "viento", "hojas", "naturaleza"], "cae", 36, 1.0, "caen girando"),
    "Critical_frame": ("Golpe critico", "sprites", ["golpe", "critico", "impacto", "dano", "pelea", "crit"], "radial", 14, 1.0, "chispas del golpe critico"),
    "Damage_frame": ("Dano (corazon negro)", "sprites", ["dano", "golpe", "herido", "pelea", "hurt"], "sube", 16, 1.0, "indicador de dano"),
    "Drip_frame": ("Gota", "sprites", ["gota", "agua", "lava", "estalactita", "gotea", "drip"], "cae", 18, 1.0, "gota que cae"),
    "Effect_frame": ("Efecto de pocion (remolino)", "sprites", ["pocion", "magia", "remolino", "efecto", "curar"], "sube", 20, 1.0, ""),
    "Enchanted_frame": ("Glifos de encantamiento", "sprites", ["encantar", "encantamiento", "magia", "mesa", "glifos"], "sube", 24, 1.0, ""),
    "Explosion_frame": ("Explosion", "sprites", ["explosion", "bomba", "tnt", "estallido", "romper", "explode"], "ninguno", 16, 2.5, "nube de explosion"),
    "Flame_frame": ("Llama", "sprites", ["fuego", "llama", "antorcha", "quemar", "flame"], "sube", 14, 0.8, ""),
    "Flash_frame": ("Destello", "sprites", ["destello", "flash", "luz", "fuego artificial"], "ninguno", 8, 2.0, ""),
    "Generic_frame": ("Polvo / humo generico", "sprites", ["polvo", "impacto", "caida", "aterrizar", "humo", "romper", "golpe suelo", "generic"], "radial", 16, 1.0, "particula comodin: polvo de impactos y caidas"),
    "Glint_frame": ("Brillo", "sprites", ["brillo", "brillar", "estrella", "magia", "glint"], "ninguno", 10, 1.0, ""),
    "Glitter_frame": ("Destellos (fuegos artificiales)", "sprites", ["destellos", "fiesta", "aparece", "magia", "fuego artificial", "glitter"], "radial", 18, 1.0, ""),
    "Glow_frame": ("Resplandor", "sprites", ["resplandor", "brillo", "calamar", "luz", "glow"], "ninguno", 14, 1.5, ""),
    "Goldheart_frame": ("Corazon dorado", "sprites", ["corazon", "curar", "absorcion", "amor", "vida"], "sube", 20, 1.0, ""),
    "Heart_frame": ("Corazon", "sprites", ["corazon", "amor", "curar", "domesticar", "vida", "heart"], "sube", 20, 1.0, ""),
    "Lava_frame": ("Chispa de lava", "sprites", ["lava", "chispa", "fuego", "magma"], "sube", 14, 0.8, ""),
    "Nautilus_frame": ("Nautilus (burbujas de tritón)", "sprites", ["agua", "mar", "nautilus", "burbujas"], "sube", 16, 1.0, ""),
    "Note_frame": ("Nota musical", "sprites", ["nota", "musica", "cantar", "sonido", "note"], "sube", 20, 1.0, ""),
    "Sculk_charge_frame": ("Carga sculk", "sprites", ["sculk", "carga", "oscuro", "energia"], "ninguno", 14, 1.0, ""),
    "Sculk_charge_pop_frame": ("Carga sculk (pop)", "sprites", ["sculk", "pop", "estallar", "oscuro"], "ninguno", 8, 1.0, ""),
    "Sculk_soul_frame": ("Alma sculk", "sprites", ["sculk", "alma", "muerte", "fantasma", "soul"], "sube", 20, 1.0, ""),
    "Sga_frame": ("Alfabeto galactico", "sprites", ["encantar", "runas", "magia", "letras", "galactico"], "sube", 30, 1.0, ""),
    "Shriek_frame": ("Grito sculk", "sprites", ["grito", "sculk", "chillido", "onda"], "ninguno", 14, 1.5, ""),
    "Sonic_boom_frame": ("Estampido sonico", "sprites", ["onda", "estampido", "sonico", "warden", "explosion"], "ninguno", 18, 2.0, ""),
    "Soul_fire_frame": ("Llama de almas", "sprites", ["fuego", "alma", "llama azul", "soul"], "sube", 14, 0.8, ""),
    "Soul_frame": ("Alma", "sprites", ["alma", "muerte", "fantasma", "soul"], "sube", 20, 1.0, ""),
    "Spark_frame": ("Chispa", "sprites", ["chispa", "fuego artificial", "electricidad", "golpe metal", "spark"], "radial", 12, 0.8, ""),
    "Spell_frame": ("Hechizo", "sprites", ["hechizo", "magia", "pocion", "aparece", "spell"], "sube", 20, 1.0, ""),
    "Splash_frame": ("Salpicadura de agua", "sprites", ["agua", "salpicar", "charco", "caer al agua", "splash"], "radial", 10, 1.0, ""),
    "Sweep_frame": ("Barrido de espada", "sprites", ["barrido", "espada", "ataque", "golpe", "swing", "sweep"], "ninguno", 10, 1.8, ""),
    "Vibration_frame": ("Vibracion sculk", "sprites", ["vibracion", "sculk", "sensor", "paso"], "ninguno", 14, 1.0, ""),
    "burbuja": ("Burbuja (y revienta)", "sprites", ["burbuja", "agua", "bubble"], "sube", 14, 1.0, "burbuja que sube y estalla"),
    "charco_de_agua": ("Burbuja que estalla", "sprites", ["burbuja", "agua", "charco", "pop"], "ninguno", 8, 1.0, ""),
    "TNT_slow_explode_frame_1": ("TNT mecha larga (103 frames)", "tnt", ["tnt", "bomba", "explosion", "mecha", "dinamita"], "ninguno", 103, 1.0, "bloque que parpadea y explota en el frame 103 del efecto"),
    "TNT_instant_explode_1": ("TNT explota ya (12 frames)", "tnt", ["tnt", "bomba", "explosion", "dinamita"], "ninguno", 12, 1.0, "explota casi de inmediato"),
    "Rain": ("Lluvia (sigue a la camara)", "clima_nodos", ["lluvia", "clima", "tormenta", "agua", "rain"], "ninguno", 0, 1.0, "nodos 'Camera Weather Nodes'"),
    "Snow": ("Nieve (sigue a la camara)", "clima_nodos", ["nieve", "clima", "frio", "snow"], "ninguno", 0, 1.0, ""),
    "Ash": ("Ceniza (sigue a la camara)", "clima_nodos", ["ceniza", "clima", "volcan", "nether", "ash"], "ninguno", 0, 1.0, ""),
    "Spores": ("Esporas (sigue a la camara)", "clima_nodos", ["esporas", "clima", "cueva", "hongos", "spores"], "ninguno", 0, 1.0, ""),
    "Firefly": ("Luciernagas (sigue a la camara)", "clima_nodos", ["luciernagas", "noche", "clima", "bosque", "firefly"], "ninguno", 0, 1.0, ""),
    "Leafy_Wind": ("Hojas con viento (sigue a la camara)", "clima_nodos", ["hojas", "viento", "clima", "otono", "leaves"], "ninguno", 0, 1.0, ""),
    "Rain_1": ("Lluvia (particulas, 40 m)", "clima_particulas", ["lluvia", "clima", "tormenta", "rain"], "ninguno", 0, 1.0, "plano de 40x40 m con 11272 gotas"),
    "Snow_1": ("Nieve (particulas, 40 m)", "clima_particulas", ["nieve", "clima", "frio", "snow"], "ninguno", 0, 1.0, "plano de 40x40 m con 8060 copos"),
    "trueno": ("Trueno / rayo", "modelo", ["trueno", "rayo", "tormenta", "relampago", "lightning"], "ninguno", 8, 1.0, "9 rayos 3D; parpadea unos frames"),
}
TEXTURAS = [os.path.join(os.path.dirname(CARPETA), "MCprep_addon", "MCprep_resources", "resourcepacks", "mcprep_default", "assets", "minecraft", "textures"),
            os.path.join(os.path.dirname(CARPETA), "kebyn proyecto  1.20.1_analysis", "kebyn proyecto  1.20.1", "assets", "minecraft", "textures")]
OMITIR = {"Rain_1_sin_plano"}              # variante del plano de lluvia: se ve igual que Rain_1

# evento de la animacion -> lista de (efecto, patron, cantidad base, escala, vida)
REGLAS = {
    "impacto": [("Generic_frame", "radial", 10, 1.0, 14)],
    "impacto_fuerte": [("Generic_frame", "radial", 18, 1.4, 18), ("Critical_frame", "radial", 8, 1.0, 12)],
    "lanzamiento": [("Sweep_frame", "ninguno", 1, 1.4, 8)],
    "aparece": [("Glitter_frame", "radial", 8, 1.0, 16)],
    "desaparece": [("Big_smoke_frame", "sube", 6, 1.0, 20)],
    "rompe": [("Generic_frame", "radial", 14, 1.2, 16), ("Big_smoke_frame", "sube", 4, 1.0, 20)],
}
# evento de sonido (sounds.json) -> efectos
SONIDO_A_EFECTO = [
    (r"\.break$", "rompe"), (r"explode", [("Explosion_frame", "ninguno", 1, 2.5, 16)]),
    (r"big_fall|small_fall|\.fall$", "impacto"), (r"attack\.crit", [("Critical_frame", "radial", 8, 1.0, 12)]),
    (r"attack\.sweep", [("Sweep_frame", "ninguno", 1, 1.6, 8)]), (r"attack\.(strong|weak)", [("Critical_frame", "radial", 5, 0.9, 10)]),
    (r"player\.hurt|generic\.hurt|\.hurt$", [("Damage_frame", "sube", 3, 1.0, 16)]),
    (r"\.place$", "aparece"), (r"extinguish", [("Big_smoke_frame", "sube", 6, 1.0, 20)]), (r"anvil|chain\.hit|trident\.hit", [("Spark_frame", "radial", 6, 0.8, 10)]),
]

_ST = {"cat": None}


def _fps():
    return bpy.context.scene.render.fps or 24


# ------------------------------------------------------------------------------------------------------------------------------------ catalogo
def _lee_blend(ruta):
    """nombres de objetos de un .blend sin cargarlo entero"""
    with bpy.data.libraries.load(ruta, link=False) as (src, _dst):
        return list(src.objects)


def catalogo(carpeta=None, forzar=False):
    """lista de dicts: id, etiqueta, tipo, etiquetas, patron, vida, escala, nota, archivo (los que no estan en la tabla se agregan como 'sprites'/'modelo' segun su nombre)"""
    if _ST["cat"] is not None and not forzar:
        return _ST["cat"]
    carpeta = carpeta or CARPETA
    res = []
    vistos = set()
    if os.path.isdir(carpeta):
        for f in sorted(os.listdir(carpeta)):
            if not f.lower().endswith(".blend") or f.lower().endswith(".blend1"):
                continue
            i = f[:-6]
            if i in OMITIR:
                continue
            vistos.add(i)
            if i in CATALOGO:
                et, tipo, tags, pat, vida, esc, nota = CATALOGO[i]
            else:
                et, tipo, tags, pat, vida, esc, nota = (i.replace("_", " "), "sprites" if "frame" in i.lower() else "modelo", [i.lower()], "ninguno", 16, 1.0, "no esta en la tabla del addon")
            res.append(dict(id=i, etiqueta=et, tipo=tipo, etiquetas=list(tags), patron=pat, vida=vida, escala=esc, nota=nota, archivo=os.path.join(carpeta, f)))
    _ST["cat"] = res
    return res


def _entrada(efecto):
    for e in catalogo():
        if e["id"] == efecto or e["id"].lower() == str(efecto).lower():
            return e
    cand = [e for e in catalogo() if str(efecto).lower() in e["id"].lower()]
    if len(cand) == 1:
        return cand[0]
    raise KeyError(f"efecto desconocido: {efecto!r}; usa fx.catalogo() o fx.buscar('palabra')")


def buscar(palabra):
    """efectos cuyo id / etiqueta / etiquetas contienen la palabra"""
    p = palabra.lower()
    return [e for e in catalogo() if p in e["id"].lower() or p in e["etiqueta"].lower() or any(p in t for t in e["etiquetas"])]


# ------------------------------------------------------------------------------------------------------------------------------------ acciones (compatible con acciones por capas)
def fcurvas(act):
    try:
        return list(act.fcurves)
    except Exception:
        pass
    res = []
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                res += list(cb.fcurves)
    return res


def _rango_llaves(act):
    xs = [k.co[0] for fc in fcurvas(act) for k in fc.keyframe_points]
    return (min(xs), max(xs)) if xs else None


def _mover_accion(act, t0, ini, k):
    """x' = ini + (x - t0) * k para todas las llaves (y sus manijas)"""
    for fc in fcurvas(act):
        for kp in fc.keyframe_points:
            for attr in ("co", "handle_left", "handle_right"):
                v = getattr(kp, attr)
                setattr(kp, attr, (ini + (v[0] - t0) * k, v[1]))
        fc.update()


def _asignar_accion(ob, act, ref=None):
    ob.animation_data_create()
    ob.animation_data.action = act
    try:
        if ob.animation_data.action_slot is None and len(act.slots):
            ob.animation_data.action_slot = act.slots[0]
    except Exception:
        pass


# ------------------------------------------------------------------------------------------------------------------------------------ plantillas
def _coleccion(nombre, ocultar=False, hijo_de_escena=True):
    c = bpy.data.collections.get(nombre)
    if c is None:
        c = bpy.data.collections.new(nombre)
    if hijo_de_escena and c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    if ocultar:
        c.hide_render = True
        c.hide_viewport = True
    return c


def _indice_texturas():
    if "tex" not in _ST:
        idx = {}
        for raiz in TEXTURAS:
            for d, _s, fs in os.walk(raiz):
                for f in fs:
                    idx.setdefault(f.lower(), os.path.join(d, f))
        _ST["tex"] = idx
    return _ST["tex"]


def reparar_texturas():
    """las plantillas apuntan a la carpeta de MCprep de Blender 4.5 (ya no existe): busca cada imagen que falta por nombre en las texturas del proyecto y la vuelve a enlazar. Devuelve cuantas arreglo"""
    n = 0
    idx = None
    for im in bpy.data.images:
        if im.source != 'FILE' or not im.filepath or im.packed_file:
            continue
        if os.path.isfile(bpy.path.abspath(im.filepath)):
            continue
        base = re.sub(r"\.\d{3}$", "", os.path.basename(im.filepath.replace("\\", "/")))
        idx = idx or _indice_texturas()
        ruta = idx.get(base.lower())
        if ruta:
            im.filepath = ruta
            im.reload()
            n += 1
    return n


def cargar(efecto):
    """trae (una sola vez) el efecto a la escena como plantilla oculta en FX_biblioteca. Devuelve la lista de objetos raiz de la plantilla"""
    e = _entrada(efecto)
    todos = e["tipo"] in ("clima_nodos", "modelo")            # estos traen todos los objetos (jerarquia / par objeto + origen); los demas, solo la raiz instanciadora
    ya = [o for o in bpy.data.objects if o.get("fx_base") == e["id"] and o.get("fx_raiz") is not None and o.get("fx_id") is None and (todos or o.get("fx_raiz"))]
    if ya:
        return ya
    nombres = _lee_blend(e["archivo"])
    if e["tipo"] in ("sprites",):
        raiz = [n for n in nombres if re.search(r"_frame_\d+@1\.00$", n) or re.search(r"_frame_\d+$", n) and "mcprep" not in n and "@" not in n]
        raiz = [n for n in raiz if "@2." not in n] or [n for n in nombres if "@1.00" in n]
    elif e["tipo"] == "tnt":
        raiz = [n for n in nombres if "mcprep" in n and "_frame_1" in n and "@" not in n]
    elif e["tipo"] == "clima_particulas":
        raiz = [n for n in nombres if n in ("Rain", "Snow")]
    elif e["tipo"] == "clima_nodos":                          # el plano con los nodos + su "origin" (el resto del archivo es relleno comun a todos los efectos)
        pref = e["id"].lower().replace("_", " ")
        raiz = [n for n in nombres if n.lower().replace("_", " ") in (pref, pref + " origin")]
    else:                                                     # modelo: todos los objetos (los hijos no vienen solos al traer al padre)
        raiz = list(nombres)
    if not raiz:
        raise RuntimeError(f"no encontre la raiz de {e['id']} en {e['archivo']}: {nombres[:6]}")
    with bpy.data.libraries.load(e["archivo"], link=False) as (src, dst):
        dst.objects = raiz
    reparar_texturas()
    col = _coleccion(COL_BIB, ocultar=True)
    res = []
    for ob in dst.objects:
        if ob is None:
            continue
        ob["fx_base"] = e["id"]
        ob["fx_raiz"] = (ob.parent is None)
        ob.hide_render = True
        ob.hide_viewport = True
        if ob.name not in col.objects:
            col.objects.link(ob)
        res.append(ob)
    return res if todos else [o for o in res if o["fx_raiz"]]


def _arbol_acciones(col_o_ob, vistos=None):
    """todas las acciones de un objeto instanciador y de las colecciones que instancia (recursivo)"""
    vistos = vistos if vistos is not None else set()
    acts = []

    def ob_(ob):
        if ob.animation_data and ob.animation_data.action:
            acts.append(ob.animation_data.action)
        if ob.instance_type == 'COLLECTION' and ob.instance_collection and ob.instance_collection.name not in vistos:
            vistos.add(ob.instance_collection.name)
            col_(ob.instance_collection)

    def col_(c):
        for o in c.objects:
            ob_(o)
        for h in c.children:
            col_(h)
    ob_(col_o_ob)
    return acts


def duracion_base(efecto):
    """(primer frame con llave, ultimo frame con llave) de la plantilla: p. ej. Explosion (0, 17); Cherry (17, 30); TNT lento (1, 103)"""
    rangos = []
    for r in cargar(efecto):
        for a in _arbol_acciones(r):
            rg = _rango_llaves(a)
            if rg:
                rangos.append(rg)
    if not rangos:
        return (0.0, 0.0)
    return (min(r[0] for r in rangos), max(r[1] for r in rangos))


class _Clonador:
    """copia un objeto (y las colecciones que instancia) moviendo todas las llaves: x' = ini + (x - t0) * k; las particulas (sistemas) tambien"""
    def __init__(self, pid, t0, ini, k):
        self.pid, self.t0, self.ini, self.k = pid, t0, ini, k
        self.cols = {}
        self.objs = {}

    def accion(self, ob2, ob):
        a = ob.animation_data.action if ob.animation_data else None
        ob2.animation_data_clear()
        if a:
            a2 = a.copy()
            _mover_accion(a2, self.t0, self.ini, self.k)
            _asignar_accion(ob2, a2)

    def objeto(self, ob):
        if ob.name in self.objs:
            return self.objs[ob.name]
        ob2 = ob.copy()
        self.objs[ob.name] = ob2
        ob2["fx_id"] = self.pid
        ob2["fx_raiz"] = False
        ob2.hide_render = ob.hide_render if ob.get("fx_base") is None else False
        ob2.hide_viewport = ob.hide_viewport if ob.get("fx_base") is None else False
        self.accion(ob2, ob)
        for m in ob2.modifiers:
            if m.type == 'PARTICLE_SYSTEM':
                st = m.particle_system.settings.copy()
                m.particle_system.settings = st
                st.frame_start = self.ini + (st.frame_start - self.t0) * self.k
                st.frame_end = self.ini + (st.frame_end - self.t0) * self.k
                st.lifetime = max(1.0, st.lifetime * self.k)
        if ob.instance_type == 'COLLECTION' and ob.instance_collection:
            ob2.instance_collection = self.coleccion(ob.instance_collection)
        return ob2

    def coleccion(self, c):
        if c.name in self.cols:
            return self.cols[c.name]
        c2 = bpy.data.collections.new(c.name + "_fx")
        c2["fx_id"] = self.pid
        self.cols[c.name] = c2
        for o in c.objects:
            c2.objects.link(self.objeto(o))
        for h in c.children:
            c2.children.link(self.coleccion(h))
        for o in c.objects:                                   # padres dentro de la copia
            if o.parent and o.parent.name in self.objs:
                self.objs[o.name].parent = self.objs[o.parent.name]
                self.objs[o.name].matrix_parent_inverse = o.matrix_parent_inverse.copy()
        return c2


# ------------------------------------------------------------------------------------------------------------------------------------ destino
def _frame_set(f):
    sc = bpy.context.scene
    if sc.frame_current != int(round(f)):
        sc.frame_set(int(round(f)))


def posicion(en, frame):
    """posicion en el mundo de `en` en ese frame. `en`: (x,y,z) | 'Objeto' | 'Objeto:Hueso[:head|tail]' | 'cursor' | dict"""
    sc = bpy.context.scene
    if en is None:
        return Vector(sc.cursor.location)
    if isinstance(en, (tuple, list, Vector)) and len(en) == 3 and all(isinstance(x, (int, float)) for x in en):
        return Vector(en)
    if isinstance(en, dict):
        d = dict(en)
        nombre = d.get("objeto")
        if d.get("hueso"):
            nombre += ":" + d["hueso"] + ":" + d.get("punto", "head")
        p = posicion(nombre, frame)
        return p + Vector(d.get("desplazar", (0, 0, 0)))
    if isinstance(en, str):
        if en.lower() == "cursor":
            return Vector(sc.cursor.location)
        partes = en.split(":")
        ob = bpy.data.objects.get(partes[0])
        if ob is None:
            raise KeyError(f"no existe el objeto {partes[0]!r}")
        _frame_set(frame)
        bpy.context.view_layer.update()
        if len(partes) >= 2 and ob.type == 'ARMATURE':
            pb = ob.pose.bones.get(partes[1])
            if pb is None:
                raise KeyError(f"{partes[0]} no tiene el hueso {partes[1]!r}")
            punto = partes[2] if len(partes) > 2 else "head"
            return ob.matrix_world @ (pb.tail if punto == "tail" else pb.head)
        return ob.matrix_world.translation.copy()
    raise TypeError(f"destino no valido: {en!r}")


# ------------------------------------------------------------------------------------------------------------------------------------ colocar
def _jsonable(d):
    res = {}
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, (Vector, tuple, list)):
            v = [round(float(x), 4) if isinstance(x, (int, float)) else x for x in v]
        res[k] = v
    return res


def _id_nuevo(efecto, frame):
    base = f"{efecto}_f{int(frame)}"
    usados = {c.get("fx_id") for c in bpy.data.objects if c.get("fx_id")}
    i, n = base, 1
    while i in usados:
        n += 1
        i = f"{base}_{n}"
    return i


def _camara():
    return bpy.context.scene.camera


def _anim_loc(ob, frames_pos):
    """frames_pos: [(frame, Vector)] -> llaves de location"""
    for f, p in frames_pos:
        ob.location = p
        ob.keyframe_insert("location", frame=f)


def _anim_escala(ob, pares):
    for f, s in pares:
        ob.scale = (s, s, s)
        ob.keyframe_insert("scale", frame=f)


def _constante(ob):
    if ob.animation_data and ob.animation_data.action:
        for fc in fcurvas(ob.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'


def _direccion(patron, rnd, direccion):
    if patron == "radial":
        a = rnd.uniform(0, 2 * math.pi)
        return Vector((math.cos(a), math.sin(a), rnd.uniform(0.0, 0.6))).normalized()
    if patron == "explota":
        v = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1)))
        return v.normalized() if v.length > 1e-6 else Vector((0, 0, 1))
    if patron == "sube":
        return Vector((rnd.uniform(-0.25, 0.25), rnd.uniform(-0.25, 0.25), 1.0)).normalized()
    if patron == "cae":
        return Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), -0.4)).normalized()
    if patron == "cono":
        d = Vector(direccion).normalized()
        j = Vector((rnd.uniform(-0.35, 0.35), rnd.uniform(-0.35, 0.35), rnd.uniform(-0.35, 0.35)))
        return (d + j).normalized()
    return Vector((0, 0, 0))


def colocar(efecto, frame, en=None, hasta=None, cantidad=None, patron=None, vida=None, escala=None, vel=None, grav=None, dispersion=0.15,
            retraso=0, direccion=(0, 0, 1), desplazar=(0, 0, 0), seguir=False, semilla=1, camara=True, id=None, origen="manual", **extra):
    """pone un efecto empezando en `frame`. Devuelve su id (para quitarlo / rehacerlo).
    efecto : id del catalogo (fx.catalogo()). en: ver posicion(). patron: ninguno | radial | sube | cae | explota | cono (como se mueven las particulas).
    cantidad: cuantas particulas (sprites); vida: duracion en frames de cada una; escala: tamano; vel (m/s) y grav (m/s2, + = cae); dispersion (m) de salida;
    retraso: frames al azar entre particulas; seguir: acompana al objeto / hueso; camara: las laminas miran a la camara; hasta: frame final (clima, trueno)."""
    e = _entrada(efecto)
    sc = bpy.context.scene
    f_orig = sc.frame_current
    argumentos = _jsonable(dict(en=en, hasta=hasta, cantidad=cantidad, patron=patron, vida=vida, escala=escala, vel=vel, grav=grav, dispersion=dispersion,
                                retraso=retraso, direccion=direccion, desplazar=desplazar, seguir=seguir, semilla=semilla, camara=camara, **extra))
    frame = int(frame)
    pid = id or _id_nuevo(e["id"], frame)
    quitar(pid, _silencio=True)
    cont = _coleccion(COL_FX)
    sub = bpy.data.collections.new(PREFIJO + pid)
    sub["fx_id"] = pid
    cont.children.link(sub)
    tipo = e["tipo"]
    p0 = posicion(en, frame) + Vector(desplazar)
    pos_f = (lambda f: posicion(en, f) + Vector(desplazar)) if seguir else (lambda f: p0)
    padre = bpy.data.objects.new(PREFIJO + pid, None)
    padre.empty_display_type = 'PLAIN_AXES'
    padre.empty_display_size = 0.3
    padre["fx_id"], padre["fx_raiz"], padre["fx_efecto"], padre["fx_frame"], padre["fx_origen"] = pid, True, e["id"], frame, origen
    sub.objects.link(padre)
    padre.location = p0
    escala = e["escala"] if escala is None else escala
    nres = {"id": pid, "efecto": e["id"], "tipo": tipo, "frame": frame, "origen": origen, "params": argumentos}
    if tipo in ("sprites", "tnt"):
        t0, t1 = duracion_base(e["id"])
        n_base = max(1.0, t1 - t0 - 1) if tipo == "sprites" else max(1.0, t1 - t0)       # sprites: la primera lamina se ve en t0+1 (las llaves van de t0 a t1)
        patron = e["patron"] if patron is None else patron
        cantidad = (1 if patron == "ninguno" else 8) if cantidad is None else cantidad
        vida = e["vida"] if vida is None else vida
        if tipo == "tnt":
            vida, cantidad, patron = n_base, 1, "ninguno"
        rnd = random.Random(semilla)
        vel = {"radial": 2.0, "sube": 0.8, "cae": 0.5, "explota": 3.0, "cono": 2.0}.get(patron, 0.0) if vel is None else vel
        grav = {"radial": 5.0, "cae": 3.0, "explota": 2.0}.get(patron, 0.0) if grav is None else grav
        bases = cargar(e["id"])
        creados = []
        for i in range(max(1, int(cantidad))):
            vi = max(2, int(round(vida * rnd.uniform(0.75, 1.25)))) if patron != "ninguno" or cantidad > 1 else int(round(vida))
            ini = frame + (rnd.randint(0, int(retraso)) if retraso else 0)
            k = vi / n_base if tipo == "sprites" else 1.0
            clon = _Clonador(pid + f"#{i}", t0, ini - k if tipo == "sprites" else ini, k)      # la primera lamina aparece justo en `ini`
            clon.pid = pid
            for b in bases:
                r = clon.objeto(b)
                r.hide_render = False
                r.hide_viewport = False
                r["fx_raiz"] = False
                r.name = f"{PREFIJO}{pid}.{i:02d}"
                for c in list(r.users_collection):
                    c.objects.unlink(r)
                sub.objects.link(r)
                r.parent = padre
                r.scale = (escala,) * 3 if tipo == "sprites" else (escala,) * 3
                # movimiento de la particula
                d = _direccion(patron, rnd, direccion)
                v0 = d * vel * rnd.uniform(0.6, 1.2)
                off = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.3, 1))) * dispersion if patron != "ninguno" else Vector((0, 0, 0))
                if patron != "ninguno":
                    pas = max(1, vi // 12)
                    marcos = sorted(set(list(range(0, vi, pas)) + [vi]))
                    pares = []
                    for m in marcos:
                        t = m / _fps()
                        pares.append((ini + m, off + v0 * t + Vector((0, 0, -0.5 * grav * t * t))))
                    _anim_loc(r, pares)
                    _anim_escala(r, [(ini - 1, 0.0), (ini, escala), (ini + vi * 0.7, escala), (ini + vi, escala * 0.15)])
                    _constante(r)
                else:
                    r.location = off
                if camara and _camara() and tipo == "sprites":
                    c = r.constraints.new('TRACK_TO')
                    c.target = _camara()
                    c.track_axis = 'TRACK_Z'
                    c.up_axis = 'UP_Y'
                    r["fx_billboard"] = True
                creados.append(r)
                nres["fin"] = max(nres.get("fin", 0), ini + vi)
        nres["particulas"] = len(creados)
        if tipo == "tnt":                                       # el TNT existe solo desde su frame (antes no hay bloque)
            _visibilidad(creados, [(frame, int(nres["fin"]) + 24)])
    elif tipo in ("clima_nodos", "clima_particulas"):
        hasta = int(hasta if hasta is not None else sc.frame_end)
        bases = cargar(e["id"])
        clon = _Clonador(pid, 0.0, frame, 1.0)
        mapa = {}
        for b in bases:
            r = clon.objeto(b)
            r.hide_render = False
            r.hide_viewport = False
            r.name = f"{PREFIJO}{pid}.{b.name}"
            r["fx_raiz"] = False
            for c in list(r.users_collection):
                c.objects.unlink(r)
            sub.objects.link(r)
            mapa[b.name] = r
        for b in bases:                                        # padres entre las copias
            if b.parent and b.parent.name in mapa:
                mapa[b.name].parent = mapa[b.parent.name]
        for r in mapa.values():
            if r.parent is None:
                r.parent = padre
            for m in r.modifiers:
                if m.type == 'NODES':
                    _entradas_nodos(m, extra, _camara())
        if tipo == "clima_particulas":
            for r in mapa.values():
                r.scale = tuple(escala * s for s in r.scale)
        _visibilidad(list(mapa.values()), [(frame, hasta)])
        nres["fin"] = hasta
    elif tipo == "modelo":
        hasta = int(hasta if hasta is not None else frame + e["vida"])
        bases = cargar(e["id"])
        clon = _Clonador(pid, 0.0, frame, 1.0)
        mapa = {}
        for b in bases:
            r = clon.objeto(b)
            r.hide_render = False
            r.hide_viewport = False
            r.name = f"{PREFIJO}{pid}.{b.name}"
            r["fx_raiz"] = False
            for c in list(r.users_collection):
                c.objects.unlink(r)
            sub.objects.link(r)
            mapa[b.name] = r
        for b in bases:
            if b.parent and b.parent.name in mapa:
                mapa[b.name].parent = mapa[b.parent.name]
        raices = [r for r in mapa.values() if r.parent is None]
        for r in raices:
            r.parent = padre
        padre.scale = (escala,) * 3
        if e["id"] == "trueno":                               # parpadea como un rayo: encendido / apagado / encendido
            largo = max(6, hasta - frame)
            tramos = [(frame, frame + max(1, largo // 4)), (frame + max(2, largo // 2), frame + max(3, largo * 3 // 4))]
        else:
            tramos = [(frame, hasta)]
        _visibilidad([r for r in mapa.values() if r.type != 'EMPTY'], tramos)
        nres["fin"] = hasta
    # seguir: la posicion del padre acompana al objeto
    if seguir and nres.get("fin"):
        _anim_loc(padre, [(f, pos_f(f)) for f in range(frame, int(nres["fin"]) + 1, 2)])
    registrar(nres)
    sc.frame_set(f_orig)
    return pid


def _entradas_nodos(m, extra, camara):
    """pone el seguidor (camara) y los ajustes que se pasen por nombre al modificador 'Camera Weather Nodes' (intenta por identificador y por nombre)"""
    ng = m.node_group
    if not ng:
        return
    pedidos = {"Weather Folower": camara}
    mapa = {"densidad": "Density", "semilla": "Seed", "tiempo": "Time", "extension": "Spread"}
    for k, v in extra.items():
        pedidos[mapa.get(k, k)] = v
    props = getattr(m, "properties", None)
    if camara is not None:
        pedidos["Camera Rotation"] = camara
    for it in ng.interface.items_tree:
        if getattr(it, "in_out", "") != 'INPUT' or it.name not in pedidos or pedidos[it.name] is None:
            continue
        try:
            if props is not None and hasattr(props, "inputs"):        # Blender 5.x: m.properties.inputs[identificador]["value"]
                props.inputs[it.identifier]["value"] = pedidos[it.name]
            else:
                m[it.identifier] = pedidos[it.name]
        except Exception as ex:
            print(f"[Efectos MC] no pude poner {it.name}: {ex}")


def _visibilidad(objs, tramos):
    """hide_viewport / hide_render: visibles solo dentro de los tramos [(a, b)] (ocultos antes, entre tramos y despues)"""
    for o in objs:
        for prop in ("hide_viewport", "hide_render"):
            setattr(o, prop, True)
            o.keyframe_insert(prop, frame=1)
            for a, b in tramos:
                setattr(o, prop, True)
                o.keyframe_insert(prop, frame=a - 1)
                setattr(o, prop, False)
                o.keyframe_insert(prop, frame=a)
                setattr(o, prop, False)
                o.keyframe_insert(prop, frame=b - 1)
                setattr(o, prop, True)
                o.keyframe_insert(prop, frame=b)
        if o.animation_data and o.animation_data.action:
            for fc in fcurvas(o.animation_data.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = 'CONSTANT'


# ------------------------------------------------------------------------------------------------------------------------------------ registro / quitar / estado
def registrar(info):
    sc = bpy.context.scene
    reg = json.loads(sc.get("fx_registro", "{}"))
    reg[info["id"]] = info
    sc["fx_registro"] = json.dumps(reg)


def estado():
    """lo que hay puesto: [{id, efecto, tipo, frame, fin, ...}] ordenado por frame"""
    reg = json.loads(bpy.context.scene.get("fx_registro", "{}"))
    return sorted(reg.values(), key=lambda d: (d["frame"], d["id"]))


def quitar(id=None, origen=None, _silencio=False):
    """quita un efecto por id (con todo lo que creo: copias, colecciones, acciones) o todos (`id=None`; `origen` = manual / plan / auto / sonido para quitar solo esos)"""
    sc = bpy.context.scene
    reg = json.loads(sc.get("fx_registro", "{}"))
    ids = {id} if id else set(reg) | {o["fx_id"] for o in bpy.data.objects if o.get("fx_id") and o.get("fx_raiz") is not None}
    if origen:
        ids = {i for i in ids if any(o.get("fx_id") == i and o.get("fx_origen") == origen for o in bpy.data.objects)}
    objs = [o for o in bpy.data.objects if o.get("fx_id") in ids]
    cols = [c for c in bpy.data.collections if c.get("fx_id") in ids]
    acts = {o.animation_data.action for o in objs if o.animation_data and o.animation_data.action}
    parts = {m.particle_system.settings for o in objs for m in o.modifiers if m.type == 'PARTICLE_SYSTEM'}
    for i in ids:
        reg.pop(i, None)
    if objs or cols:
        bpy.data.batch_remove(objs + cols)
    huerf = [a for a in acts if a and a.users == 0] + [s for s in parts if s and s.users == 0]
    if huerf:
        bpy.data.batch_remove(huerf)
    sc["fx_registro"] = json.dumps(reg)
    return len(ids)


# ------------------------------------------------------------------------------------------------------------------------------------ plan (lista de efectos para la IA)
def plan_aplicar(plan, quitar_antes=True):
    """plan: lista de dicts con las mismas claves que colocar() (efecto, frame, en, ...) y un `id` opcional. Con `quitar_antes` primero quita los efectos que vinieron de un plan anterior.
    Devuelve los ids creados."""
    if isinstance(plan, dict):
        plan = plan.get("efectos", [])
    if quitar_antes:
        quitar(origen="plan")
    ids = []
    for d in plan:
        d = dict(d)
        ef, fr = d.pop("efecto"), d.pop("frame")
        d["origen"] = "plan"
        ids.append(colocar(ef, fr, **d))
    return ids


def plan_cargar(ruta):
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def plan_guardar(ruta, origen=None):
    """guarda lo que hay puesto como plan (con todos sus parametros) para repetirlo con plan_aplicar. `origen`: solo los manual / plan / auto / sonido"""
    datos = []
    for d in estado():
        if origen and d.get("origen") != origen:
            continue
        datos.append(dict(id=d["id"], efecto=d["efecto"], frame=d["frame"], **d.get("params", {})))
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump({"efectos": datos}, fh, ensure_ascii=False, indent=1)
    return len(datos)


# ------------------------------------------------------------------------------------------------------------------------------------ eventos de la animacion
def _objetos_animados(nombres=None):
    obs = []
    for o in bpy.context.scene.objects:
        if o.name.startswith(PREFIJO) or o.get("fx_id") or o.type not in ('MESH', 'EMPTY', 'ARMATURE'):
            continue
        if nombres is not None and o.name not in nombres:
            continue
        if o.animation_data and o.animation_data.action and not o.hide_viewport:
            obs.append(o)
    return obs


def _llaves_visibilidad(o):
    """(frame, 'aparece'|'desaparece') por las llaves hide_viewport / hide_render / scale del objeto"""
    ev = []
    if not (o.animation_data and o.animation_data.action):
        return ev
    for fc in fcurvas(o.animation_data.action):
        pts = [(kp.co[0], kp.co[1]) for kp in fc.keyframe_points]
        if fc.data_path in ("hide_viewport", "hide_render"):
            for (a, va), (b, vb) in zip(pts, pts[1:]):
                if va >= 0.5 > vb:
                    ev.append((int(round(b)), "aparece"))
                elif va < 0.5 <= vb:
                    ev.append((int(round(b)), "desaparece"))
        elif fc.data_path == "scale" and fc.array_index == 0:
            for (a, va), (b, vb) in zip(pts, pts[1:]):
                if va > 0.5 * abs(pts[0][1] or 1) and vb < 0.02 and va > 0.05:
                    ev.append((int(round(b)), "desaparece"))
                elif va < 0.02 and vb > 0.05:
                    ev.append((int(round(a)), "aparece"))
    return ev


def eventos(f0=None, f1=None, objetos=None, v_choque=2.0, v_lanzar=4.0, mostrar_ocultos=False):
    """detecta en la animacion: impacto (el objeto baja rapido y rebota o se frena), lanzamiento (acelera de golpe), aparece / desaparece (visibilidad o escala).
    Devuelve [{frame, tipo, objeto, pos, fuerza}] ordenado. Solo mira objetos animados, visibles y que no sean del propio addon."""
    sc = bpy.context.scene
    f0 = sc.frame_start if f0 is None else int(f0)
    f1 = sc.frame_end if f1 is None else int(f1)
    obs = _objetos_animados(objetos)
    guardado = sc.frame_current
    series = {o.name: [] for o in obs}
    for f in range(f0 - 1, f1 + 2):
        sc.frame_set(f)
        for o in obs:
            series[o.name].append(o.matrix_world.translation.copy())
    sc.frame_set(guardado)
    res = []
    for o in obs:
        s = series[o.name]
        fps = _fps()
        v = [(s[i + 1] - s[i]) * fps for i in range(len(s) - 1)]                 # v[i] entre frame f0-1+i y f0+i
        for i in range(1, len(v) - 1):
            f = f0 - 1 + i + 1
            if not f0 <= f <= f1:
                continue
            vz_in, vz_out = v[i - 1].z, v[i].z
            if vz_in < -v_choque and vz_out > 0.5 * vz_in:                      # bajaba rapido y pierde mas de la mitad de la velocidad (rebota o se frena)
                res.append(dict(frame=f, tipo="impacto_fuerte" if -vz_in > 3 * v_choque else "impacto", objeto=o.name, pos=tuple(s[i + 1]), fuerza=round(-vz_in, 2)))
            sp_in, sp_out = v[i - 1].length, v[i].length
            if sp_in < 0.5 * v_lanzar and sp_out > v_lanzar and (sp_out - sp_in) > v_lanzar * 0.8:
                res.append(dict(frame=f, tipo="lanzamiento", objeto=o.name, pos=tuple(s[i + 1]), fuerza=round(sp_out, 2)))
        for f, t in _llaves_visibilidad(o):
            if f0 <= f <= f1:
                pos = s[min(max(f - f0 + 1, 0), len(s) - 1)]
                res.append(dict(frame=f, tipo=t, objeto=o.name, pos=tuple(pos), fuerza=1.0))
    # frames consecutivos del mismo objeto y tipo: uno solo
    res.sort(key=lambda d: (d["objeto"], d["tipo"], d["frame"]))
    lim = []
    for d in res:
        if lim and lim[-1]["objeto"] == d["objeto"] and lim[-1]["tipo"] == d["tipo"] and d["frame"] - lim[-1]["frame"] <= 3:
            continue
        lim.append(d)
    return sorted(lim, key=lambda d: (d["frame"], d["objeto"]))


def _reglas():
    r = dict(REGLAS)
    ruta = os.path.join(CARPETA, "reglas_usuario.json")
    if os.path.isfile(ruta):
        try:
            with open(ruta, encoding="utf-8") as fh:
                r.update({k: [tuple(x) for x in v] for k, v in json.load(fh).items()})
        except Exception as ex:
            print("[Efectos MC] reglas_usuario.json:", ex)
    return r


def sugerir(f0=None, f1=None, objetos=None, **kw):
    """propone efectos (lista de dicts para plan_aplicar) segun los eventos detectados. No pone nada."""
    reglas = _reglas()
    plan = []
    for ev in eventos(f0, f1, objetos, **kw):
        for j, (ef, pat, cant, esc, vida) in enumerate(reglas.get(ev["tipo"], [])):
            if ef not in {e["id"] for e in catalogo()}:
                continue
            f = min(1.0, max(0.4, ev["fuerza"] / 8.0)) if ev["tipo"].startswith("impacto") else 1.0
            plan.append(dict(id=f"auto_{ev['tipo']}_{ev['objeto']}_{ev['frame']}_{j}", efecto=ef, frame=ev["frame"], en=tuple(round(c, 3) for c in ev["pos"]),
                             patron=pat, cantidad=max(1, int(round(cant * f))), escala=round(esc * (0.7 + 0.3 * f), 2), vida=vida, evento=ev["tipo"], objeto=ev["objeto"]))
    return plan


def aplicar_sugerencias(f0=None, f1=None, objetos=None, **kw):
    plan = sugerir(f0, f1, objetos, **kw)
    quitar(origen="auto")
    ids = []
    for d in plan:
        d = dict(d)
        d.pop("evento", None)
        d.pop("objeto", None)
        ef, fr = d.pop("efecto"), d.pop("frame")
        d["origen"] = "auto"
        ids.append(colocar(ef, fr, **d))
    return ids


def desde_sonidos(en=None, prefijo="SND_"):
    """efectos en los frames de las tiras de sonido (add-on Alfred Sonidos: tiras `SND_<evento>_<frame>`): romper -> polvo + humo, caer -> polvo, golpe critico -> chispas, daño, explosion...
    `en`: donde ponerlos (por defecto el objeto activo). Devuelve los ids."""
    sc = bpy.context.scene
    ed = sc.sequence_editor
    if not ed:
        return []
    strips = ed.strips if hasattr(ed, "strips") else ed.sequences
    reglas = _reglas()
    quitar(origen="sonido")
    if en is None and bpy.context.view_layer.objects.active:
        en = bpy.context.view_layer.objects.active.name
    ids = []
    for t in strips:
        if t.type != 'SOUND' or not t.name.startswith(prefijo):
            continue
        evento = t.get("mcsnd_ev") or t.name[len(prefijo):].rsplit("_", 1)[0]
        evento = evento.replace("_", ".")
        for patron, sal in SONIDO_A_EFECTO:
            if re.search(patron, evento):
                lista = reglas.get(sal, []) if isinstance(sal, str) else sal
                for j, (ef, pat, cant, esc, vida) in enumerate(lista):
                    ids.append(colocar(ef, int(t.frame_final_start), en=en, patron=pat, cantidad=cant, escala=esc, vida=vida,
                                       id=f"snd_{t.name}_{j}", origen="sonido"))
                break
    return ids


def ayuda():
    return __doc__


# ------------------------------------------------------------------------------------------------------------------------------------ interfaz
class FxItem(PropertyGroup):
    name: StringProperty()
    etiqueta: StringProperty()
    tipo: StringProperty()


class FxProps(PropertyGroup):
    items: CollectionProperty(type=FxItem)
    activo: IntProperty()
    buscar: StringProperty(name="Buscar", description="id, nombre o etiqueta de uso: golpe, humo, fuego, magia, agua...")
    frame_manual: BoolProperty(name="Frame propio", default=False)
    frame: IntProperty(name="Frame", default=1)
    hasta: IntProperty(name="Hasta (clima / trueno)", default=0, min=0, description="0 = fin de la escena (clima) o duracion propia (trueno)")
    destino: StringProperty(name="En", description="vacio = objeto activo; 'Objeto' | 'Objeto:Hueso' | 'cursor' | x,y,z", default="")
    escala: FloatProperty(name="Escala", default=0.0, min=0.0, description="0 = la sugerida del efecto")
    cantidad: IntProperty(name="Particulas", default=0, min=0, description="0 = la sugerida del patron")
    patron: EnumProperty(name="Patron", items=[("AUTO", "Sugerido", ""), ("ninguno", "Ninguno (una lamina)", ""), ("radial", "Radial (suelo)", ""), ("sube", "Sube", ""), ("cae", "Cae", ""), ("explota", "Explota", ""), ("cono", "Cono", "")], default="AUTO")
    vida: IntProperty(name="Vida (frames)", default=0, min=0, description="0 = la sugerida")
    seguir: BoolProperty(name="Seguir al objeto", default=False)
    semilla: IntProperty(name="Semilla", default=1)
    plan: StringProperty(name="Plan (.json)", subtype='FILE_PATH', default="//efectos_plan.json")
    info: StringProperty()


def P(ctx):
    return ctx.scene.fxmc


def _llenar(p):
    p.items.clear()
    for e in catalogo(forzar=True):
        it = p.items.add()
        it.name, it.etiqueta, it.tipo = e["id"], e["etiqueta"], e["tipo"]


def _destino(p, ctx):
    t = p.destino.strip()
    if not t:
        a = ctx.view_layer.objects.active
        if a is None:
            return None
        if a.type == 'ARMATURE' and a.mode == 'POSE' and ctx.active_pose_bone:
            return f"{a.name}:{ctx.active_pose_bone.name}"
        return a.name
    if re.match(r"^\s*-?[\d.]+\s*,\s*-?[\d.]+\s*,\s*-?[\d.]+\s*$", t):
        return tuple(float(x) for x in t.split(","))
    return t


class FXMC_OT_leer(Operator):
    bl_idname, bl_label, bl_description = "fxmc.leer", "Leer carpeta", "Lee la carpeta de efectos y llena la lista"

    def execute(self, ctx):
        _llenar(P(ctx))
        P(ctx).info = f"{len(P(ctx).items)} efectos"
        return {'FINISHED'}


class FXMC_OT_poner(Operator):
    bl_idname, bl_label, bl_description = "fxmc.poner", "Poner efecto", "Pone el efecto elegido en el frame y el lugar indicados"

    def execute(self, ctx):
        p = P(ctx)
        if not p.items:
            _llenar(p)
        it = p.items[p.activo]
        fr = p.frame if p.frame_manual else ctx.scene.frame_current
        kw = {}
        if p.escala:
            kw["escala"] = p.escala
        if p.cantidad:
            kw["cantidad"] = p.cantidad
        if p.patron != "AUTO":
            kw["patron"] = p.patron
        if p.vida:
            kw["vida"] = p.vida
        if p.hasta:
            kw["hasta"] = p.hasta
        try:
            pid = colocar(it.name, fr, en=_destino(p, ctx), seguir=p.seguir, semilla=p.semilla, **kw)
        except Exception as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        p.info = f"puesto {pid}"
        return {'FINISHED'}


class FXMC_OT_eventos(Operator):
    bl_idname, bl_label, bl_description = "fxmc.eventos", "Detectar y poner efectos", "Detecta impactos, lanzamientos, apariciones y desapariciones en el rango de la escena y pone un efecto en cada uno"

    def execute(self, ctx):
        ids = aplicar_sugerencias()
        P(ctx).info = f"{len(ids)} efectos automaticos"
        return {'FINISHED'}


class FXMC_OT_sonidos(Operator):
    bl_idname, bl_label, bl_description = "fxmc.sonidos", "Efectos desde los sonidos", "Pone un efecto en el frame de cada tira SND_ (en el objeto activo)"

    def execute(self, ctx):
        ids = desde_sonidos()
        P(ctx).info = f"{len(ids)} efectos desde sonidos"
        return {'FINISHED'}


class FXMC_OT_plan(Operator):
    bl_idname, bl_label, bl_description = "fxmc.plan", "Aplicar plan (.json)", "Aplica el plan de efectos del archivo (lo que escribe la IA)"

    def execute(self, ctx):
        try:
            ids = plan_aplicar(plan_cargar(bpy.path.abspath(P(ctx).plan)))
        except Exception as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        P(ctx).info = f"plan: {len(ids)} efectos"
        return {'FINISHED'}


class FXMC_OT_guardar_plan(Operator):
    bl_idname, bl_label, bl_description = "fxmc.guardar_plan", "Guardar plan", "Guarda lo que hay puesto como plan .json"

    def execute(self, ctx):
        n = plan_guardar(bpy.path.abspath(P(ctx).plan))
        P(ctx).info = f"plan guardado ({n})"
        return {'FINISHED'}


class FXMC_OT_quitar(Operator):
    bl_idname, bl_label, bl_description = "fxmc.quitar", "Quitar todos", "Quita todos los efectos puestos por el addon"
    origen: StringProperty(default="")

    def execute(self, ctx):
        n = quitar(origen=self.origen or None)
        P(ctx).info = f"quitados {n}"
        return {'FINISHED'}


class FXMC_UL_lista(UIList):
    def draw_item(self, ctx, layout, data, item, icon, active_data, active_prop, index):
        layout.label(text=item.etiqueta, icon='PARTICLES')
        layout.label(text=item.tipo)

    def filter_items(self, ctx, data, propname):
        items = getattr(data, propname)
        q = P(ctx).buscar.lower()
        flt = [self.bitflag_filter_item] * len(items)
        if q:
            cat = {e["id"]: e for e in catalogo()}
            for i, it in enumerate(items):
                e = cat.get(it.name)
                txt = (it.name + " " + it.etiqueta + " " + " ".join(e["etiquetas"] if e else [])).lower()
                if q not in txt:
                    flt[i] = 0
        return flt, []


def _dibujar(self, ctx):
    l, p = self.layout, P(ctx)
    if not p.items:
        l.operator("fxmc.leer", icon='FILE_REFRESH')
        return
    b = l.box()
    b.prop(p, "buscar", icon='VIEWZOOM')
    b.template_list("FXMC_UL_lista", "", p, "items", p, "activo", rows=6)
    cat = {e["id"]: e for e in catalogo()}
    it = p.items[p.activo] if 0 <= p.activo < len(p.items) else None
    if it and it.name in cat:
        e = cat[it.name]
        b.label(text=f"{e['tipo']} | patron {e['patron']} | vida {e['vida']}")
        if e["nota"]:
            b.label(text=e["nota"])
    c = l.box()
    c.label(text="Poner")
    r = c.row(align=True)
    r.prop(p, "frame_manual", text="")
    r.prop(p, "frame") if p.frame_manual else r.label(text=f"Frame actual: {ctx.scene.frame_current}")
    c.prop(p, "destino")
    r = c.row(align=True)
    r.prop(p, "escala")
    r.prop(p, "cantidad")
    r = c.row(align=True)
    r.prop(p, "patron", text="")
    r.prop(p, "vida")
    r = c.row(align=True)
    r.prop(p, "hasta")
    r.prop(p, "semilla")
    c.prop(p, "seguir")
    c.operator("fxmc.poner", icon='ADD')
    a = l.box()
    a.label(text="Sincronizar con la animacion")
    a.operator("fxmc.eventos", icon='TIME')
    a.operator("fxmc.sonidos", icon='SOUND')
    a.prop(p, "plan")
    r = a.row(align=True)
    r.operator("fxmc.plan", icon='IMPORT')
    r.operator("fxmc.guardar_plan", icon='EXPORT')
    l.operator("fxmc.quitar", icon='TRASH')
    est = estado()
    if est:
        d = l.box()
        d.label(text=f"Puestos: {len(est)}")
        for e in est[:12]:
            d.label(text=f"{e['frame']:>5}  {e['efecto']}  ({e['id']})")
    if p.info:
        l.label(text=p.info, icon='INFO')


class FXMC_PT_principal(Panel):
    bl_idname, bl_label, bl_space_type, bl_region_type, bl_category = "FXMC_PT_principal", "Efectos MC", 'VIEW_3D', 'UI', "Efectos MC"
    draw = _dibujar


CLASES = (FxItem, FxProps, FXMC_OT_leer, FXMC_OT_poner, FXMC_OT_eventos, FXMC_OT_sonidos, FXMC_OT_plan, FXMC_OT_guardar_plan, FXMC_OT_quitar, FXMC_UL_lista, FXMC_PT_principal)


def register():
    for c in CLASES:
        try:
            bpy.utils.register_class(c)
        except ValueError:
            pass
    bpy.types.Scene.fxmc = PointerProperty(type=FxProps)


def unregister():
    for c in reversed(CLASES):
        try:
            bpy.utils.unregister_class(c)
        except RuntimeError:
            pass
    if hasattr(bpy.types.Scene, "fxmc"):
        del bpy.types.Scene.fxmc
