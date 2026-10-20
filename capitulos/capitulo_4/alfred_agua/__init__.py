# -*- coding: utf-8 -*-
"""Alfred Agua - pone AGUA de Minecraft en la escena: cascadas por un hueco, agua que se reparte por el suelo y charcos. Pensado para que la IA lo use con una llamada.

EJEMPLO REAL (el de la cueva de Alfred, ya hecho con este addon): el hueco de la celda (-49, -19) tiene una columna de agua que empieza a caer en el frame 150, tarda 100 frames en llegar
al suelo, y despues el agua se reparte por el suelo de la cueva como en el juego. Se rehace con:
    agua.cascada(celda=(-49, -19), z_superficie=8, frame=150, duracion=100, abrir_hueco=True)

COMO FUNCIONA EL AGUA (reglas de Minecraft que usa el addon):
  - Una columna de agua cae en vertical (agua "cayendo": cubo completo, textura water_flow.png animada, v = 1 tira por metro).
  - Donde toca suelo firme se reparte: nivel 7 en el punto de caida, un nivel menos por cada bloque de distancia (altura 0.875 * nivel / 7), hasta nivel 1. Solo sobre suelo firme.
  - En un borde sin suelo el agua cae en vertical hasta el siguiente suelo (cubo completo) y vuelve a empezar con nivel 7 donde aterriza.
  - Tiempo: un bloque cada 5 ticks = 6 frames (TICK). La columna baja en `duracion` frames (crece desde arriba hacia abajo).
  - Textura: water_flow.png (32 cuadros de 32x32) para el agua que cae y water_still.png (16x512) para la del suelo, tenidas de azul (el juego las tine; son grises). Un cuadro cada 2.4 frames.
  - Color por defecto #4573FF, leve transparencia (~0.85), emision minima (0.1): la luz de la escena manda en cada cara (la cara que mira a la pared sale mas oscura).
  - El mundo se lee de los bloques sueltos `bloque_<tipo>_<i>_<j>_<k>` de una coleccion (por defecto `cueva_bloques`): la celda (i, j, k) ocupa x i..i+1, y j..j+1, z k..k+1.

USO PARA LA IA:
    import importlib.util, sys
    spec = importlib.util.spec_from_file_location("alfred_agua_local", r"C:\\Users\\user\\Desktop\\Alfred_Animacion\\capitulos\\capitulo_4\\alfred_agua\\__init__.py")
    agua = importlib.util.module_from_spec(spec); sys.modules["alfred_agua_local"] = agua; spec.loader.exec_module(agua); agua.register()

    agua.cascada(celda=(-49, -19), z_superficie=8, frame=150, duracion=100)       # columna desde z=8 hasta el suelo + reparto por el suelo
    agua.cascada(celda=(-49, -19), abrir_hueco=True)                                # ademas quita el techo y levanta las paredes de la chimenea (k = k_techo+1 .. k_tope)
    agua.derramar(en=(-30.5, -10.5, -9.0), frame=200)                               # solo reparto por el suelo desde un punto (como vaciar un cubo)
    agua.estado()   /   agua.quitar("cascada_-49_-19")   /   agua.quitar()          # lo puesto / quitar uno / quitar todo
    agua.analizar((-49, -19))                                                       # que hay en esa columna: bloques, suelo, techo; sirve para decidir antes de poner
    agua.plan_aplicar([{"tipo": "cascada", "celda": [-49, -19], "frame": 150, "duracion": 100}, {"tipo": "derramar", "en": [-30.5, -10.5, -9], "frame": 200}])
  Opciones comunes: color="#4573FF", alfa=0.85, emision=0.1, ganancia=1.2, cuadro=2.4 (frames por cuadro de textura), tick=6, radio=7, coleccion_bloques="cueva_bloques",
  receptores="luz_entrada_receptores" (coleccion de la luz con light linking a la que se anade el agua; vacio = ninguna), id="..." (para rehacerlo sin duplicar).
Todo lo creado vive en la coleccion `agua_mc` (un objeto por tick y tipo para que se vea como se extiende) y lleva `agua_id`; `quitar()` lo borra por completo.
"""
bl_info = {
    "name": "Alfred Agua",
    "author": "Kebyn",
    "version": (1, 0, 0),
    "blender": (4, 4, 0),
    "location": "Vista 3D > barra lateral (N) > Agua MC",
    "description": "Cascadas y agua repartida por el suelo con las texturas y reglas de Minecraft, desde el frame que se pida",
    "category": "Animation",
}

import heapq
import json
import math
import os
import re

import bmesh
import bpy
from bpy.props import BoolProperty, FloatProperty, IntProperty, IntVectorProperty, PointerProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup
from mathutils import Vector

CARPETA = r"C:\Users\user\Desktop\Alfred_Animacion"
TEXTURAS = CARPETA + "/MCprep_addon/MCprep_resources/resourcepacks/mcprep_default/assets/minecraft/textures/block"
COL_AGUA = "agua_mc"
COL_BLOQUES = "cueva_bloques"
RECEPTORES = "luz_entrada_receptores"
VECINOS = ((1, 0), (-1, 0), (0, 1), (0, -1))
BLOQUE = re.compile(r"^bloque_(.+)_(-?\d+)_(-?\d+)_(-?\d+)(\.\d+)?$")
TIPOS_PARED = ("stone", "andesite", "diorite")
PESOS_PARED = (0.6, 0.25, 0.15)
DEF = dict(color="#4573FF", alfa=0.85, emision=0.1, ganancia=1.2, cuadro=2.4, tick=6, radio=7, rugosidad=0.3)


# ------------------------------------------------------------------------------------------------------------------------------------ mundo
def celdas(coleccion=None):
    """{(i, j, k): objeto} de los bloques `bloque_<tipo>_<i>_<j>_<k>` de la coleccion"""
    col = bpy.data.collections.get(coleccion or COL_BLOQUES)
    if col is None:
        raise KeyError(f"no existe la coleccion de bloques {coleccion or COL_BLOQUES!r}")
    res = {}
    for ob in col.objects:
        if BLOQUE.match(ob.name):
            l = ob.location
            res[(int(l.x // 1), int(l.y // 1), int(round(l.z)))] = ob
    return res


def analizar(celda, coleccion=None):
    """que hay en la columna (i, j): alturas k con bloque, primer suelo bajo el techo, y si esta cerrada por arriba"""
    cs = celdas(coleccion)
    i, j = celda
    ks = sorted(k for (x, y, k) in cs if (x, y) == (i, j))
    vecinos = {d: sorted(k for (x, y, k) in cs if (x, y) == (i + d[0], j + d[1])) for d in VECINOS}
    return dict(celda=celda, bloques_k=ks, paredes={f"{d[0]},{d[1]}": (v[0], v[-1]) if v else None for d, v in vecinos.items()},
                suelo_k=_suelo(cs, i, j, max(ks) if ks else 8))


def _suelo(cs, i, j, desde_k):
    """k de la celda de aire que queda encima del primer bloque que hay hacia abajo desde `desde_k` (sin contar los de mas arriba)"""
    ks = [k for (x, y, k) in cs if (x, y) == (i, j)]
    abajo = [k for k in ks if k < desde_k]
    return (max(abajo) + 1) if abajo else None


def abrir_hueco(celda, k_techo=-2, k_tope=7, coleccion=None, semilla=5):
    """quita los bloques de la columna y levanta las 4 paredes (k_techo+1 .. k_tope) para que quede una chimenea; devuelve cuantos quito / puso"""
    import random
    rnd = random.Random(semilla)
    cs = celdas(coleccion)
    col = bpy.data.collections[coleccion or COL_BLOQUES]
    i, j = celda
    quitar_ = [cs[(i, j, k)] for k in range(k_techo, k_tope + 1) if (i, j, k) in cs]
    if quitar_:
        bpy.data.batch_remove(quitar_)
    nuevos = 0
    for dx, dy in VECINOS:
        x, y = i + dx, j + dy
        for k in range(k_techo + 1, k_tope + 1):
            if (x, y, k) in cs:
                continue
            t = rnd.choices(TIPOS_PARED, PESOS_PARED)[0]
            if t not in bpy.data.meshes:
                continue
            ob = bpy.data.objects.new(f"bloque_{t}_{x}_{y}_{k}", bpy.data.meshes[t])
            ob.location = (x + 0.5, y + 0.5, k)
            col.objects.link(ob)
            nuevos += 1
    return dict(quitados=len(quitar_), nuevos=nuevos)


_abrir = abrir_hueco


# ------------------------------------------------------------------------------------------------------------------------------------ material
def _lineal(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def color_hex(h):
    h = h.lstrip("#")
    return tuple(_lineal(int(h[i:i + 2], 16)) for i in (0, 2, 4))


def material(nombre, textura, cuadro=2.4, color="#4573FF", alfa=0.85, emision=0.1, ganancia=1.2, rugosidad=0.3):
    """material de agua con la textura de Minecraft (tira de 32 cuadros): cada `cuadro` frames pasa al siguiente; semitransparente; poca emision (la luz manda)"""
    mat = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    n, L = nt.nodes, nt.links.new
    img = bpy.data.images.load(TEXTURAS + "/" + textura, check_existing=True)
    img.alpha_mode = 'STRAIGHT'
    uv = n.new("ShaderNodeTexCoord")
    sep = n.new("ShaderNodeSeparateXYZ")
    L(uv.outputs["UV"], sep.inputs[0])
    fu = n.new("ShaderNodeMath"); fu.operation = 'FRACT'
    fv = n.new("ShaderNodeMath"); fv.operation = 'FRACT'
    L(sep.outputs[0], fu.inputs[0]); L(sep.outputs[1], fv.inputs[0])
    esc = n.new("ShaderNodeMath"); esc.operation = 'DIVIDE'; esc.inputs[1].default_value = 32.0
    L(fv.outputs[0], esc.inputs[0])
    idx = n.new("ShaderNodeValue"); idx.label = "cuadro"
    dr = idx.outputs[0].driver_add("default_value").driver
    dr.type = 'SCRIPTED'
    dr.expression = f"1 - (floor(frame / {cuadro}) % 32 + 1) / 32"
    suma = n.new("ShaderNodeMath"); suma.operation = 'ADD'
    L(esc.outputs[0], suma.inputs[0]); L(idx.outputs[0], suma.inputs[1])
    com = n.new("ShaderNodeCombineXYZ")
    L(fu.outputs[0], com.inputs[0]); L(suma.outputs[0], com.inputs[1])
    tex = n.new("ShaderNodeTexImage"); tex.image = img; tex.interpolation = 'Closest'; tex.extension = 'EXTEND'
    L(com.outputs[0], tex.inputs["Vector"])
    tinte = n.new("ShaderNodeMix"); tinte.data_type = 'RGBA'; tinte.blend_type = 'MULTIPLY'
    tinte.inputs["Factor"].default_value = 1.0
    L(tex.outputs["Color"], tinte.inputs["A"])
    r, g, b = color_hex(color)
    tinte.inputs["B"].default_value = (r * ganancia, g * ganancia, b * ganancia, 1.0)
    pr = n.new("ShaderNodeBsdfPrincipled")
    L(tinte.outputs["Result"], pr.inputs["Base Color"])
    pr.inputs["Roughness"].default_value = rugosidad
    pr.inputs["IOR"].default_value = 1.33
    L(tinte.outputs["Result"], pr.inputs["Emission Color"]); pr.inputs["Emission Strength"].default_value = emision
    tr = n.new("ShaderNodeBsdfTransparent")
    mez = n.new("ShaderNodeMixShader")
    al = n.new("ShaderNodeMath"); al.operation = 'MULTIPLY'; al.inputs[1].default_value = alfa / 0.7; al.use_clamp = True     # la textura trae alfa ~0.7
    L(tex.outputs["Alpha"], al.inputs[0])
    L(al.outputs[0], mez.inputs[0]); L(tr.outputs[0], mez.inputs[1]); L(pr.outputs[0], mez.inputs[2])
    sal = n.new("ShaderNodeOutputMaterial")
    L(mez.outputs[0], sal.inputs["Surface"])
    try:
        mat.surface_render_method = 'BLENDED'
    except Exception:
        pass
    mat.use_backface_culling = False
    return mat


# ------------------------------------------------------------------------------------------------------------------------------------ geometria
def _caja(bm, x0, y0, z0, x1, y1, z1):
    v = [bm.verts.new(p) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([v[i] for i in f])


def _uv(me):
    """u 0..1 en horizontal; v = z (una tira de textura por metro) en las caras verticales; v 0..1 en las tapas"""
    uv = me.uv_layers.new(name="UVMap")
    for p in me.polygons:
        for l in p.loop_indices:
            c = me.vertices[me.loops[l].vertex_index].co
            if abs(p.normal.z) > 0.5:
                uv.data[l].uv = (c.x + 0.5, c.y + 0.5)
            else:
                uv.data[l].uv = ((c.x + 0.5) if abs(p.normal.y) > 0.5 else (c.y + 0.5), c.z)


def _malla(nombre, bm, mat):
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    me.update()
    _uv(me)
    me.materials.append(mat)
    return me


def repartir(cs, x0, y0, k0, radio=7, max_caida=12):
    """reglas de Minecraft: nivel 7 en (x0,y0,k0), -1 por bloque sobre suelo firme; en un borde sin suelo cae hasta el siguiente suelo (cubo completo) y reinicia en nivel 7.
    Devuelve {(x, y, k): (nivel, tick, cayendo)}"""
    mejor = {(x0, y0, k0): (radio, 0, False)}
    cola = [(0, -radio, (x0, y0, k0))]
    caen = {}
    while cola:
        tick, negn, (x, y, k) = heapq.heappop(cola)
        nivel = -negn
        if mejor.get((x, y, k), (0,))[0] > nivel or nivel <= 1:
            continue
        for dx, dy in VECINOS:
            nx, ny = x + dx, y + dy
            if (nx, ny, k) in cs:
                continue
            if (nx, ny, k - 1) in cs:
                n = (nx, ny, k)
                if n not in mejor or mejor[n][0] < nivel - 1:
                    mejor[n] = (nivel - 1, tick + 1, False)
                    heapq.heappush(cola, (tick + 1, -(nivel - 1), n))
                continue
            kk = k
            while (nx, ny, kk - 1) not in cs and k - kk < max_caida:
                kk -= 1
            if (nx, ny, kk - 1) not in cs:
                continue
            for kc in range(k, kk, -1):
                caen[(nx, ny, kc)] = (radio + 1, tick + 1 + (k - kc), True)
            n = (nx, ny, kk)
            t = tick + 1 + (k - kk)
            if n not in mejor or mejor[n][0] < radio:
                mejor[n] = (radio, t, False)
                heapq.heappush(cola, (t, -radio, n))
    mejor.update({c: v for c, v in caen.items() if c not in mejor})
    return mejor


# ------------------------------------------------------------------------------------------------------------------------------------ registro
def _registro():
    return json.loads(bpy.context.scene.get("agua_registro", "{}"))


def _guardar(reg):
    bpy.context.scene["agua_registro"] = json.dumps(reg)


def estado():
    return sorted(_registro().values(), key=lambda d: (d["frame"], d["id"]))


def quitar(id=None):
    """quita un agua por id (o todas) con sus objetos y mallas"""
    reg = _registro()
    ids = {id} if id else set(reg) | {o["agua_id"] for o in bpy.data.objects if o.get("agua_id")}
    objs = [o for o in bpy.data.objects if o.get("agua_id") in ids]
    mallas = [o.data for o in objs if o.type == 'MESH']
    if objs:
        bpy.data.batch_remove(objs)
    huerf = [m for m in mallas if m and m.users == 0]
    if huerf:
        bpy.data.batch_remove(huerf)
    for i in ids:
        reg.pop(i, None)
    _guardar(reg)
    return len(ids)


def _col():
    c = bpy.data.collections.get(COL_AGUA) or bpy.data.collections.new(COL_AGUA)
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c


def _aparece(ob, frame):
    for prop in ("hide_viewport", "hide_render"):
        setattr(ob, prop, True)
        ob.keyframe_insert(prop, frame=max(1, frame - 1))
        setattr(ob, prop, False)
        ob.keyframe_insert(prop, frame=frame)


def _suelo_agua(cs, x0, y0, k0, grupos_id, frame0, opts, col, mats):
    """crea el reparto por el suelo: un objeto por (tick, cayendo); devuelve (objetos, fin)"""
    flujo = repartir(cs, x0, y0, k0, opts["radio"])
    grupos = {}
    for (x, y, k), (niv, tick, cae) in flujo.items():
        grupos.setdefault((tick, cae), []).append((x, y, k, niv))
    objs = []
    for (tick, cae), lista in sorted(grupos.items()):
        bm = bmesh.new()
        for x, y, k, niv in lista:
            h = 1.0 if cae else 0.875 * niv / opts["radio"]
            _caja(bm, x - x0 - 0.5, y - y0 - 0.5, k - k0, x - x0 + 0.5, y - y0 + 0.5, k - k0 + h)
        nombre = f"agua_{grupos_id}_{'cae' if cae else 'suelo'}_t{tick:02d}"
        ob = bpy.data.objects.new(nombre, _malla(nombre, bm, mats["flow"] if cae else mats["still"]))
        ob.location = (x0 + 0.5, y0 + 0.5, k0)
        ob["agua_id"] = grupos_id
        col.objects.link(ob)
        _aparece(ob, frame0 + int(round(tick * opts["tick"])))
        objs.append(ob)
    fin = frame0 + int(round(max(v[1] for v in flujo.values()) * opts["tick"]))
    return objs, fin, flujo


def _mats(opts):
    kw = dict(cuadro=opts["cuadro"], color=opts["color"], alfa=opts["alfa"], emision=opts["emision"], ganancia=opts["ganancia"], rugosidad=opts["rugosidad"])
    return dict(flow=material("agua_mc_flow", "water_flow.png", **kw), still=material("agua_mc_still", "water_still.png", **kw))


def _receptores(objs, receptores):
    r = bpy.data.collections.get(receptores) if receptores else None
    if r:
        for ob in objs:
            if ob.name not in r.objects:
                r.objects.link(ob)


# ------------------------------------------------------------------------------------------------------------------------------------ API
def cascada(celda, z_superficie=8.0, frame=1, duracion=100, k_suelo=None, abrir_hueco=False, k_techo=-2, k_tope=7, id=None,
            coleccion_bloques=None, receptores=RECEPTORES, **opciones):
    """columna de agua que cae por la celda (i, j) desde z_superficie hasta el suelo, y reparto por el suelo. Empieza en `frame`, la columna tarda `duracion` frames en llegar abajo
    y el agua del suelo se extiende un bloque cada `tick` frames. `abrir_hueco=True` antes quita el techo y levanta las paredes de la chimenea."""
    opts = dict(DEF, **opciones)
    i, j = celda
    pid = id or f"cascada_{i}_{j}"
    quitar(pid)
    info_hueco = None
    if abrir_hueco:
        info_hueco = _abrir(celda, k_techo, k_tope, coleccion_bloques)
    cs = celdas(coleccion_bloques)
    if k_suelo is None:
        k_suelo = _suelo(cs, i, j, int(z_superficie))
        if k_suelo is None:
            raise RuntimeError(f"no hay suelo bajo la celda {celda}: pasa k_suelo")
    if (i, j, k_suelo) in cs:
        raise RuntimeError(f"la celda {(i, j, k_suelo)} es un bloque: k_suelo debe ser el aire encima del suelo")
    col = _col()
    mats = _mats(opts)
    bm = bmesh.new()
    _caja(bm, -0.5, -0.5, k_suelo - z_superficie, 0.5, 0.5, 0.0)
    colu = bpy.data.objects.new(f"agua_{pid}_columna", _malla(f"agua_{pid}_columna", bm, mats["flow"]))
    colu.location = (i + 0.5, j + 0.5, z_superficie)
    colu["agua_id"] = pid
    col.objects.link(colu)
    _aparece(colu, frame)
    colu.scale = (1, 1, 0.0)
    colu.keyframe_insert("scale", frame=frame)
    colu.scale = (1, 1, 1)
    colu.keyframe_insert("scale", frame=frame + duracion)
    objs, fin, flujo = _suelo_agua(cs, i, j, k_suelo, pid, frame + duracion, opts, col, mats)
    _receptores([colu] + objs, receptores)
    info = dict(id=pid, tipo="cascada", celda=list(celda), frame=frame, duracion=duracion, z_superficie=z_superficie, k_suelo=k_suelo, fin=fin,
                celdas=len(flujo), objetos=len(objs) + 1, hueco=info_hueco)
    reg = _registro()
    reg[pid] = dict(info, params=dict(celda=list(celda), z_superficie=z_superficie, frame=frame, duracion=duracion, abrir_hueco=False, **{k: v for k, v in opciones.items()}))
    _guardar(reg)
    return info


def derramar(en, frame=1, id=None, coleccion_bloques=None, receptores=RECEPTORES, **opciones):
    """agua que se reparte por el suelo desde un punto (x, y, z) del mundo (como vaciar un cubo): la celda de aire donde cae es floor(x), floor(y), floor(z)"""
    opts = dict(DEF, **opciones)
    x, y, z = int(math.floor(en[0])), int(math.floor(en[1])), int(math.floor(en[2]))
    pid = id or f"derrame_{x}_{y}_{z}"
    quitar(pid)
    cs = celdas(coleccion_bloques)
    if (x, y, z) in cs:
        raise RuntimeError(f"el punto {en} esta dentro de un bloque")
    while (x, y, z - 1) not in cs and z > -200:
        z -= 1
    col = _col()
    objs, fin, flujo = _suelo_agua(cs, x, y, z, pid, frame, opts, col, _mats(opts))
    _receptores(objs, receptores)
    info = dict(id=pid, tipo="derramar", frame=frame, fin=fin, celda=[x, y, z], celdas=len(flujo), objetos=len(objs))
    reg = _registro()
    reg[pid] = dict(info, params=dict(en=list(en), frame=frame, **opciones))
    _guardar(reg)
    return info


def plan_aplicar(plan):
    """lista de dicts: {"tipo": "cascada" | "derramar", "frame": .., ...mismos nombres que la funcion}. Devuelve los ids"""
    if isinstance(plan, dict):
        plan = plan.get("agua", [])
    ids = []
    for d in plan:
        d = dict(d)
        tipo = d.pop("tipo")
        if tipo == "cascada":
            ids.append(cascada(celda=tuple(d.pop("celda")), **d)["id"])
        elif tipo == "derramar":
            ids.append(derramar(**d)["id"])
        else:
            raise ValueError(f"tipo desconocido: {tipo}")
    return ids


def plan_guardar(ruta):
    datos = []
    for d in estado():
        datos.append(dict(tipo=d["tipo"], id=d["id"], **d.get("params", {})))
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump({"agua": datos}, fh, ensure_ascii=False, indent=1)
    return len(datos)


def ejemplo_cascada_cueva():
    """el ejemplo del proyecto: hueco en la celda (-49, -19) con agua desde el frame 150 (100 frames en caer)"""
    return cascada(celda=(-49, -19), z_superficie=8, frame=150, duracion=100, abrir_hueco=True)


def ayuda():
    return __doc__


# ------------------------------------------------------------------------------------------------------------------------------------ interfaz
class AguaProps(PropertyGroup):
    celda: IntVectorProperty(name="Celda (i, j)", size=2, default=(0, 0))
    z_superficie: FloatProperty(name="Z superficie", default=8.0)
    frame: IntProperty(name="Frame", default=1, min=1)
    duracion: IntProperty(name="Duracion (frames)", default=100, min=1)
    abrir: BoolProperty(name="Abrir el hueco", default=False, description="quita el techo de la columna y levanta las paredes")
    color: StringProperty(name="Color", default="#4573FF")
    alfa: FloatProperty(name="Opacidad", default=0.85, min=0.1, max=1.0)
    emision: FloatProperty(name="Brillo propio", default=0.1, min=0.0, max=2.0)
    coleccion: StringProperty(name="Coleccion de bloques", default=COL_BLOQUES)
    info: StringProperty()


def P(ctx):
    return ctx.scene.aguamc


class AGUAMC_OT_cascada(Operator):
    bl_idname, bl_label, bl_description = "aguamc.cascada", "Poner cascada", "Columna de agua desde Z superficie hasta el suelo, con reparto por el suelo"

    def execute(self, ctx):
        p = P(ctx)
        try:
            r = cascada(tuple(p.celda), p.z_superficie, p.frame, p.duracion, abrir_hueco=p.abrir, coleccion_bloques=p.coleccion, color=p.color, alfa=p.alfa, emision=p.emision)
        except Exception as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        p.info = f"{r['id']}: suelo k={r['k_suelo']}, termina en el frame {r['fin']}"
        return {'FINISHED'}


class AGUAMC_OT_derramar(Operator):
    bl_idname, bl_label, bl_description = "aguamc.derramar", "Derramar en el cursor 3D", "Reparte agua por el suelo desde el cursor 3D"

    def execute(self, ctx):
        p = P(ctx)
        try:
            r = derramar(tuple(ctx.scene.cursor.location), p.frame, coleccion_bloques=p.coleccion, color=p.color, alfa=p.alfa, emision=p.emision)
        except Exception as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        p.info = f"{r['id']}: termina en el frame {r['fin']}"
        return {'FINISHED'}


class AGUAMC_OT_quitar(Operator):
    bl_idname, bl_label, bl_description = "aguamc.quitar", "Quitar todo el agua", "Quita todo lo que puso el addon"

    def execute(self, ctx):
        P(ctx).info = f"quitadas {quitar()}"
        return {'FINISHED'}


class AGUAMC_PT_panel(Panel):
    bl_idname, bl_label, bl_space_type, bl_region_type, bl_category = "AGUAMC_PT_panel", "Agua MC", 'VIEW_3D', 'UI', "Agua MC"

    def draw(self, ctx):
        l, p = self.layout, P(ctx)
        b = l.box()
        b.prop(p, "celda")
        b.prop(p, "z_superficie")
        b.prop(p, "frame")
        b.prop(p, "duracion")
        b.prop(p, "abrir")
        b.operator("aguamc.cascada", icon='MOD_FLUIDSIM')
        l.operator("aguamc.derramar", icon='CURSOR')
        c = l.box()
        c.prop(p, "color")
        c.prop(p, "alfa")
        c.prop(p, "emision")
        c.prop(p, "coleccion")
        l.operator("aguamc.quitar", icon='TRASH')
        for d in estado()[:10]:
            l.label(text=f"{d['frame']:>5}  {d['id']}  (hasta {d['fin']})")
        if p.info:
            l.label(text=p.info, icon='INFO')


CLASES = (AguaProps, AGUAMC_OT_cascada, AGUAMC_OT_derramar, AGUAMC_OT_quitar, AGUAMC_PT_panel)


def register():
    for c in CLASES:
        try:
            bpy.utils.register_class(c)
        except ValueError:
            pass
    bpy.types.Scene.aguamc = PointerProperty(type=AguaProps)


def unregister():
    for c in reversed(CLASES):
        try:
            bpy.utils.unregister_class(c)
        except RuntimeError:
            pass
    if hasattr(bpy.types.Scene, "aguamc"):
        del bpy.types.Scene.aguamc
