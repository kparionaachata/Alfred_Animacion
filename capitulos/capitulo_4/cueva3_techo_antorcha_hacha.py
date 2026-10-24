# -*- coding: utf-8 -*-
"""alfred_cueva_3.blend, zona donde Alfred pica la veta de hierro:
1) techo mas alto: en las columnas x -70..-64, y -23..-15 los bloques desde el techo hacia arriba suben SUBIR bloques (se mueven, no se borran);
2) estalactitas colgando del techo nuevo (copias de las piezas base/tronco/punta de la estalactita de (-104,-16));
3) antorcha (bloques_dinamicos/antorcha_1.blend) en (-66.5,-21.5,-11.0);
4) el hacha de piedra en la espalda de Alfred: hijo del hueso Spine1_alfred con la matriz de rel_espalda_alfred_blend.json.
Uso: exec(open(ruta, encoding="utf8").read()); construir()
"""
import bpy, json, re
from mathutils import Vector, Matrix

ZONA = (-70, -64, -23, -15)
SUBIR = 3
ESTALACTITAS = [((-69, -21), 3), ((-65, -17), 2), ((-69, -16), 2), ((-65, -22), 3), ((-67, -23), 2)]
MOLDE = {"base": "estalactita_base_-104_-16_-3", "tronco": "estalactita_tronco_-104_-16_-4", "punta": "estalactita_punta_-104_-16_-7"}
ANTORCHA_BLEND = r"C:\Users\user\Desktop\Alfred_Animacion\bloques_dinamicos\antorcha_1.blend"
ANTORCHA_EN = Vector((-66.5, -21.5, -11.0))
REL = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\rel_espalda_alfred_blend.json"
PAT = re.compile(r"^bloque_[a-z_]+?_(-?\d+)_(-?\d+)_(-?\d+)")


def techo():
    """techo actual de cada columna = primer bloque por encima del aire de la zona de trabajo (z >= -8)"""
    x0, x1, y0, y1 = ZONA; movidos = 0
    if bpy.context.scene.get("cueva3_techo_subido"): return 0
    cols = {}
    for o in bpy.data.collections["cueva_bloques"].all_objects:
        if not o.name.startswith("bloque_"): continue
        i, j, k = int(o.location.x // 1), int(o.location.y // 1), int(round(o.location.z))
        if x0 <= i <= x1 and y0 <= j <= y1 and k >= -8: cols.setdefault((i, j), []).append(o)
    for (i, j), obs in cols.items():
        for o in obs: o.location.z += SUBIR; movidos += 1
    bpy.context.scene["cueva3_techo_subido"] = True
    return movidos


def _copiar(src, nombre, loc):
    o = bpy.data.objects.get(nombre) or bpy.data.objects.new(nombre, src.data)
    if not o.users_collection: bpy.data.collections["cueva_bloques"].objects.link(o)
    o.location = loc; o.rotation_euler = src.rotation_euler; o.scale = src.scale
    rec = bpy.data.collections.get("luz_entrada_receptores")
    if rec and o.name not in rec.objects: rec.objects.link(o)
    return o


def estalactitas():
    hechos = []; sc = bpy.context.scene; dg = bpy.context.evaluated_depsgraph_get()
    for (i, j), largo in ESTALACTITAS:
        h = sc.ray_cast(dg, Vector((i + 0.5, j + 0.5, -10.0)), Vector((0, 0, 1)), distance=12)
        if not h[0]: continue
        kc = int(round(h[1].z))                                                         # cara de abajo del techo
        piezas = ["base"] + ["tronco"] * (largo - 2) + ["punta"]
        for n, tipo in enumerate(piezas):
            k = kc - 1 - n
            hechos.append(_copiar(bpy.data.objects[MOLDE[tipo]], f"estalactita_{tipo}_{i}_{j}_{k}", (i + 0.5, j + 0.5, k)).name)
    return hechos


def antorcha():
    o = bpy.data.objects.get("antorcha_cueva3")
    if o is None:
        with bpy.data.libraries.load(ANTORCHA_BLEND, link=False) as (src, dst): dst.objects = list(src.objects)
        nuevos = [x for x in dst.objects if x]
        for x in [x for x in nuevos if x.name.startswith("torch_flame_noImport")]: nuevos.remove(x); bpy.data.objects.remove(x)   # llama suelta sin textura
        for x in nuevos: bpy.context.scene.collection.objects.link(x)
        o = next(x for x in nuevos if x.name.startswith("antorcha_1")); o.name = "antorcha_cueva3"     # empty raiz de la antorcha
        for x in nuevos:
            if x.parent is None and x is not o: x.location += ANTORCHA_EN
        return o.name
        rec = bpy.data.collections.get("luz_entrada_receptores")
        if rec:
            for x in nuevos:
                if x.type != 'LIGHT' and x.name not in rec.objects: rec.objects.link(x)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box] if o.type == 'MESH' else [o.matrix_world.translation]
    zmin = min(p.z for p in pts)
    o.location += Vector((ANTORCHA_EN.x - o.matrix_world.translation.x, ANTORCHA_EN.y - o.matrix_world.translation.y, ANTORCHA_EN.z - zmin))
    return o.name


def hacha():
    d = json.load(open(REL, encoding="utf8")); arm = bpy.data.objects["Armature"]; ax = bpy.data.objects["stone_axe"]
    info = d["herramientas"]["stone_axe"]; hueso = d.get("hueso", "Spine1_alfred")
    if ax.animation_data: ax.animation_data_clear()
    for c in list(ax.constraints): ax.constraints.remove(c)
    ax.parent = arm; ax.parent_type = 'BONE'; ax.parent_bone = hueso
    ax.matrix_parent_inverse = Matrix.Identity(4)                                   # como en alfred.blend: inversa identidad
    m = info["matriz"]; ax.matrix_basis = Matrix([m[0:4], m[4:8], m[8:12], m[12:16]])
    return hueso


def construir():
    return {"bloques_subidos": techo(), "estalactitas": estalactitas(), "antorcha": antorcha(), "hacha_en": hacha()}
