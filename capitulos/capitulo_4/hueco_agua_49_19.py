# -*- coding: utf-8 -*-
"""Segundo hueco de la cueva, en la celda (-49, -19): una chimenea abierta al cielo (igual que la de Alfred) por donde cae AGUA.
Otro personaje bajara por aqui, pero antes coloca el agua para no caer como Alfred (el agua amortigua la caida).

 - abrir_hueco(): quita el bloque del techo (-49,-19,-2) y levanta las paredes de la chimenea (4 columnas de bloques sueltos, k = -1 .. 7).
 - crear_agua(): columna de agua que baja desde z = 8 hasta el suelo y reparto como en Minecraft (altura 0.9 bajo la columna y 0.11 menos por cada bloque, hasta 7 bloques,
   solo sobre suelo plano de la cueva). Material water_flow (columna) / water_still (charco) del proyecto.
 - El agua aparece en F_AGUA: la columna crece hacia abajo en T_CAIDA frames, despues el charco se extiende en T_CHARCO frames.
Uso en Blender: exec(open(ruta).read()); abrir_hueco(); crear_agua()
"""
import bpy, bmesh, random
from mathutils import Vector

CELDA = (-49, -19)
K_TECHO, K_TOPE = -2, 7
Z_SUPERFICIE = 8.0
F_AGUA = 150                          # frame en que empieza a caer el agua
T_CAIDA = 100                         # la columna tarda 100 frames en llegar al suelo
TICK = 6                              # frames por bloque que se extiende el agua en el suelo (5 ticks de Minecraft)
RADIO_CHARCO = 7
COL, COL_AGUA, COL_RECEPTORES = "cueva_bloques", "agua_hueco_2", "luz_entrada_receptores"
TEX = "C:/Users/user/Desktop/Alfred_Animacion/MCprep_addon/MCprep_resources/resourcepacks/mcprep_default/assets/minecraft/textures/block"
GANANCIA = 1.2                         # la textura es gris medio (~0.4 lineal); la mitad de lo que era (2.4) para que brille menos
COLOR = (0.05951, 0.17144, 1.00000, 1.0)        # #4573FF en lineal
TINTE = tuple(c * GANANCIA for c in COLOR[:3]) + (1.0,)
FRAME_FLUJO = 2.4                      # video frames por cuadro de la textura de agua que cae (el juego usa 1 tick = 1.2 frames: aqui va a la mitad)
FRAME_QUIETA = 2.4                     # water_still: frametime 2 ticks
TIPOS = ("stone", "andesite", "diorite")
PESOS = (0.6, 0.25, 0.15)
VECINOS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def celdas():
    c = {}
    for ob in bpy.data.collections[COL].objects:
        p = ob.name.split("_")
        if p[0] == "bloque" and p[1] in TIPOS:
            l = ob.location
            c[(int(l.x // 1), int(l.y // 1), int(round(l.z)))] = ob
    return c


def abrir_hueco(semilla=5):
    rnd = random.Random(semilla)
    cs = celdas()
    col = bpy.data.collections[COL]
    x0, y0 = CELDA
    quitar = [cs[(x0, y0, k)] for k in range(K_TECHO, K_TOPE + 1) if (x0, y0, k) in cs]
    if quitar:
        bpy.data.batch_remove(quitar)
    nuevos = 0
    for dx, dy in VECINOS:
        x, y = x0 + dx, y0 + dy
        for k in range(K_TECHO + 1, K_TOPE + 1):
            if (x, y, k) in cs:
                continue
            t = rnd.choices(TIPOS, PESOS)[0]
            ob = bpy.data.objects.new(f"bloque_{t}_{x}_{y}_{k}", bpy.data.meshes[t])
            ob.location = (x + 0.5, y + 0.5, k)
            col.objects.link(ob)
            nuevos += 1
    return dict(quitados=len(quitar), nuevos=nuevos)


def suelo_k(cs, x, y, k_agua=-10):
    """el agua del charco va en k_agua si ahi hay aire y debajo hay bloque"""
    return (x, y, k_agua) not in cs and (x, y, k_agua - 1) in cs


def _caja(bm, x0, y0, z0, x1, y1, z1):
    v = [bm.verts.new(p) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([v[i] for i in f])


def _uv_cajas(me, repetir_v=1.0):
    """UV por cara: u 0..1 en horizontal; v 0..repetir_v en las caras verticales (el agua baja en tiras de 1 m)"""
    uv = me.uv_layers.new(name="UVMap")
    for p in me.polygons:
        vs = [me.vertices[me.loops[l].vertex_index].co for l in p.loop_indices]
        zs = [c.z for c in vs]
        for l, c in zip(p.loop_indices, vs):
            if abs(p.normal.z) > 0.5:
                uv.data[l].uv = (c.x + 0.5, c.y + 0.5)
            else:
                u = (c.x + 0.5) if abs(p.normal.y) > 0.5 else (c.y + 0.5)
                uv.data[l].uv = (u, c.z)
    return uv


def material_agua(nombre, textura, cada):
    """material con la textura de Minecraft (tira de 32 cuadros): cada `cada` frames de video pasa al cuadro siguiente; semitransparente, con algo de emision para que se vea en la oscuridad"""
    mat = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    n = nt.nodes
    L = nt.links.new
    img = bpy.data.images.load(TEX + "/" + textura, check_existing=True)
    img.alpha_mode = 'STRAIGHT'
    uv = n.new("ShaderNodeTexCoord")
    sep = n.new("ShaderNodeSeparateXYZ")
    L(uv.outputs["UV"], sep.inputs[0])
    fu = n.new("ShaderNodeMath"); fu.operation = 'FRACT'
    fv = n.new("ShaderNodeMath"); fv.operation = 'FRACT'
    L(sep.outputs[0], fu.inputs[0]); L(sep.outputs[1], fv.inputs[0])
    esc = n.new("ShaderNodeMath"); esc.operation = 'DIVIDE'; esc.inputs[1].default_value = 32.0       # un cuadro = 1/32 de la tira
    L(fv.outputs[0], esc.inputs[0])
    idx = n.new("ShaderNodeValue"); idx.label = "cuadro"                                              # V del cuadro actual (arriba = cuadro 0)
    fc = idx.outputs[0].driver_add("default_value").driver
    fc.type = 'SCRIPTED'
    fc.expression = f"1 - (floor(frame / {cada}) % 32 + 1) / 32"
    suma = n.new("ShaderNodeMath"); suma.operation = 'ADD'
    L(esc.outputs[0], suma.inputs[0]); L(idx.outputs[0], suma.inputs[1])
    com = n.new("ShaderNodeCombineXYZ")
    L(fu.outputs[0], com.inputs[0]); L(suma.outputs[0], com.inputs[1])
    tex = n.new("ShaderNodeTexImage"); tex.image = img; tex.interpolation = 'Closest'; tex.extension = 'EXTEND'
    L(com.outputs[0], tex.inputs["Vector"])
    tinte = n.new("ShaderNodeMix"); tinte.data_type = 'RGBA'; tinte.blend_type = 'MULTIPLY'
    tinte.inputs["Factor"].default_value = 1.0
    L(tex.outputs["Color"], tinte.inputs["A"]); tinte.inputs["B"].default_value = TINTE
    pr = n.new("ShaderNodeBsdfPrincipled")
    L(tinte.outputs["Result"], pr.inputs["Base Color"])
    pr.inputs["Roughness"].default_value = 0.3
    pr.inputs["IOR"].default_value = 1.33
    L(tinte.outputs["Result"], pr.inputs["Emission Color"]); pr.inputs["Emission Strength"].default_value = 0.1      # brillo propio minimo: la luz que da en cada cara manda (la cara que mira a la pared ya no brilla igual)
    tr = n.new("ShaderNodeBsdfTransparent")
    mez = n.new("ShaderNodeMixShader")
    alfa = n.new("ShaderNodeMath"); alfa.operation = 'MULTIPLY'; alfa.inputs[1].default_value = 1.2       # la textura trae alfa 0.7: queda ~0.85, una leve transparencia
    alfa.use_clamp = True
    L(tex.outputs["Alpha"], alfa.inputs[0])
    L(alfa.outputs[0], mez.inputs[0]); L(tr.outputs[0], mez.inputs[1]); L(pr.outputs[0], mez.inputs[2])
    sal = n.new("ShaderNodeOutputMaterial")
    L(mez.outputs[0], sal.inputs["Surface"])
    try:
        mat.surface_render_method = 'BLENDED'
    except Exception:
        pass
    mat.use_backface_culling = False
    return mat


def simular_flujo(cs, x0, y0, k_suelo, max_caida=12):
    """el agua que cae de la columna aterriza en (x0, y0, k_suelo) y se reparte como en Minecraft: nivel 7 en el punto de caida, -1 por bloque, sobre suelo firme;
    si al lado no hay suelo cae en vertical (agua cayendo, cuadro completo) y vuelve a empezar con nivel 7 donde aterriza. Devuelve {celda: (nivel, tick, cayendo)}"""
    import heapq
    mejor = {(x0, y0, k_suelo): (7, 0, False)}
    cola = [(0, -7, (x0, y0, k_suelo))]
    caen = {}
    while cola:
        tick, negn, (x, y, k) = heapq.heappop(cola)
        nivel = -negn
        if mejor.get((x, y, k), (0,))[0] > nivel:
            continue
        if nivel <= 1:
            continue
        for dx, dy in VECINOS:
            nx, ny = x + dx, y + dy
            if (nx, ny, k) in cs:
                continue
            if (nx, ny, k - 1) in cs:                              # suelo firme: sigue repartiendose, un nivel menos
                n = (nx, ny, k)
                if n not in mejor or mejor[n][0] < nivel - 1:
                    mejor[n] = (nivel - 1, tick + 1, False)
                    heapq.heappush(cola, (tick + 1, -(nivel - 1), n))
                continue
            kk = k                                                 # borde: cae hasta el siguiente suelo
            while (nx, ny, kk - 1) not in cs and k - kk < max_caida:
                kk -= 1
            if (nx, ny, kk - 1) not in cs:
                continue
            for kc in range(k, kk, -1):
                caen[(nx, ny, kc)] = (8, tick + 1 + (k - kc), True)
            n = (nx, ny, kk)
            t = tick + 1 + (k - kk)
            if n not in mejor or mejor[n][0] < 7:
                mejor[n] = (7, t, False)
                heapq.heappush(cola, (t, -7, n))
    mejor.update({c: v for c, v in caen.items() if c not in mejor})
    return mejor


def crear_agua(f_agua=None):
    f_agua = F_AGUA if f_agua is None else f_agua
    cs = celdas()
    x0, y0 = CELDA
    cx, cy = x0 + 0.5, y0 + 0.5
    col = bpy.data.collections.get(COL_AGUA) or bpy.data.collections.new(COL_AGUA)
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    for ob in list(col.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    k_suelo = -10
    mat_flow = material_agua("agua_mc_flow", "water_flow.png", FRAME_FLUJO)
    mat_quieta = material_agua("agua_mc_still", "water_still.png", FRAME_QUIETA)
    # columna: origen arriba (z = superficie), crece hacia abajo
    bm = bmesh.new()
    _caja(bm, -0.5, -0.5, k_suelo - Z_SUPERFICIE, 0.5, 0.5, 0.0)
    me = bpy.data.meshes.new("agua_hueco_columna")
    bm.to_mesh(me)
    bm.free()
    me.update()
    _uv_cajas(me)
    me.materials.append(mat_flow)
    colu = bpy.data.objects.new("agua_hueco_columna", me)
    colu.location = (cx, cy, Z_SUPERFICIE)
    col.objects.link(colu)
    # reparto del agua en el suelo, por "ticks" (cada tick = TICK frames): un objeto por tick y tipo, asi se ve como se va extendiendo
    flujo = simular_flujo(cs, x0, y0, k_suelo)
    grupos = {}
    for (x, y, k), (niv, tick, cae) in flujo.items():
        grupos.setdefault((tick, cae), []).append((x, y, k, niv))
    objetos = []
    for (tick, cae), celdas_ in sorted(grupos.items()):
        bm = bmesh.new()
        for x, y, k, niv in celdas_:
            h = 1.0 if cae else 0.875 * niv / 7.0
            _caja(bm, x - x0 - 0.5, y - y0 - 0.5, k - k_suelo, x - x0 + 0.5, y - y0 + 0.5, k - k_suelo + h)
        nombre = f"agua_hueco_{'cae' if cae else 'suelo'}_t{tick:02d}"
        m = bpy.data.meshes.new(nombre)
        bm.to_mesh(m)
        bm.free()
        m.update()
        _uv_cajas(m)
        m.materials.append(mat_flow if cae else mat_quieta)
        ob = bpy.data.objects.new(nombre, m)
        ob.location = (cx, cy, k_suelo)
        col.objects.link(ob)
        objetos.append((ob, tick))
    # animacion: aparece en f_agua; la columna crece hacia abajo en T_CAIDA frames; el agua del suelo se extiende un tick (TICK frames) por bloque
    def ocultar_hasta(ob, ini):
        for prop in ("hide_viewport", "hide_render"):
            setattr(ob, prop, True)
            ob.keyframe_insert(prop, frame=max(1, ini - 1))
            setattr(ob, prop, False)
            ob.keyframe_insert(prop, frame=ini)
    ocultar_hasta(colu, f_agua)
    colu.scale = (1, 1, 0.0)
    colu.keyframe_insert("scale", frame=f_agua)
    colu.scale = (1, 1, 1)
    colu.keyframe_insert("scale", frame=f_agua + T_CAIDA)
    for ob, tick in objetos:
        ocultar_hasta(ob, f_agua + T_CAIDA + int(round(tick * TICK)))
    r = bpy.data.collections.get(COL_RECEPTORES)                    # que las luces de la cueva tambien le lleguen
    if r:
        for ob in [colu] + [o for o, _ in objetos]:
            if ob.name not in r.objects:
                r.objects.link(ob)
    return dict(columna=colu.name, objetos=len(objetos), celdas=len(flujo), cayendo=sum(1 for v in flujo.values() if v[2]),
                niveles=sorted({k for (_x, _y, k) in flujo}), f_agua=f_agua, fin=f_agua + T_CAIDA + int(round(max(v[1] for v in flujo.values()) * TICK)))
