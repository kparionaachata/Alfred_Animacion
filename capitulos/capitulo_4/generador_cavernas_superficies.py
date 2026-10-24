# -*- coding: utf-8 -*-
"""Generador de Cavernas de Superficies (add-on de Blender).

Crea una caverna grande al estilo Minecraft hecha SOLO con superficies: una malla por tipo de roca con unicamente las caras cubicas que
dan al aire (sin un objeto por bloque), con la textura de bloque de 16 px en cada cara. Opcionalmente:
  - pilares de roca de suelo a techo, estalactitas y estalagmitas;
  - lagos de lava al pie de algunos pilares (lava quieta animada, luz que sale de la superficie hacia arriba);
  - cascadas de lava en cubos que salen de un bloque fuente hundido en la pared (con su diagonal), caen recto como el agua y si
    chocan con un saliente lo recorren y siguen cayendo; cada cascada con su altura de salida, su brillo y su luz reflejada.
Es la version reutilizable de capitulos/capitulo_4/caverna_superficies.py (la caverna de alfred_cueva_5A.blend).

Uso: View3D > barra lateral (N) > pestana "Cavernas". Instalar este archivo como add-on (Preferences > Add-ons > Install from Disk)
o ejecutarlo con Alt+P desde el editor de texto. Cada caverna va en su propia coleccion (nombre configurable); "Generar" la rehace.
"""
bl_info = {
    "name": "Generador de Cavernas de Superficies",
    "author": "Alfred Animacion",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Cavernas",
    "description": "Cavernas estilo Minecraft solo con superficies texturizadas: pilares, lagos y cascadas de lava",
    "category": "Add Mesh",
}

import bpy, math, os, time
import numpy as np
from mathutils import Vector
from bpy.props import (IntProperty, FloatProperty, StringProperty, BoolProperty, FloatVectorProperty, PointerProperty)

TIPOS = ["stone", "andesite", "diorite", "coal_ore", "copper_ore"]
TEXTURAS_DEF = os.path.join(os.environ.get("APPDATA", ""), "Blender Foundation", "Blender", "5.2", "scripts", "addons", "MCprep_addon",
                            "MCprep_resources", "resourcepacks", "mcprep_default", "assets", "minecraft", "textures", "block")
TONOS = [(1.0, 0.35, 0.08), (1.0, 0.42, 0.1), (1.0, 0.28, 0.05), (1.0, 0.38, 0.09)]


class Cfg:
    """parametros de una caverna (se rellenan desde el panel) y estado del calculo"""
    def __init__(self, p):
        self.NX, self.NY, self.NZ = p.ancho, p.largo, p.alto
        self.CENTRO = tuple(p.centro); self.SEMILLA = p.semilla; self.COL = p.coleccion.strip() or "caverna"
        self.N_PILARES = p.pilares; self.N_PUNTAS = p.puntas; self.SUELO_RELIEVE = p.relieve_suelo
        self.N_LAGOS = p.lagos if p.usar_lava else 0; self.RADIO_LAGO = p.radio_lago
        self.N_CASCADAS = p.cascadas if p.usar_lava else 0; self.NIVEL_LAVA = 2.9
        self.BRILLO_LAGO = p.brillo_lago; self.BRILLO_CASCADA = p.brillo_cascada
        self.LUZ_LAGO = p.luz_lago; self.LUZ_CASCADA = p.luz_cascada; self.LUZ_APERTURA = 50
        self.CAMARA = p.camara; self.TEXTURAS = bpy.path.abspath(p.texturas) if p.texturas else TEXTURAS_DEF
        self.PILARES = []; self.LAGO = None; self.SUELO = None; self.PLAN = []; self.LAGOS = []
        self.ox, self.oy, self.oz = self.CENTRO[0] - self.NX / 2, self.CENTRO[1] - self.NY / 2, self.CENTRO[2]


# ----------------------------------------------------------------------------------------------------------------------- ruido
def _ruido(shape, celda, rng):
    """ruido de valor 3D suave (0..1): rejilla aleatoria cada `celda` bloques, interpolada con smoothstep"""
    gs = [s // celda + 3 for s in shape]; out = rng.random(gs).astype(np.float32)
    for ax, n in enumerate(shape):
        t = (np.arange(n, dtype=np.float32) + 0.5) / celda; i0 = np.floor(t).astype(int); f = t - i0; f = f * f * (3 - 2 * f)
        a = np.take(out, i0, axis=ax); b = np.take(out, i0 + 1, axis=ax)
        sh = [1] * len(shape); sh[ax] = n; out = a + (b - a) * f.reshape(sh)
    return out


def _fbm(shape, celda, rng, oct_=3):
    s = np.zeros(shape, np.float32); amp = 1.0; tot = 0.0
    for o in range(oct_):
        s += amp * _ruido(shape, max(2, celda // (2 ** o)), rng); tot += amp; amp *= 0.5
    return s / tot


# ----------------------------------------------------------------------------------------------------------------------- forma
def campo(C, rng):
    """rejilla de la caverna: True = aire. Planta casi cuadrada, boveda irregular, suelo con montículos, pilares y puntas"""
    NX, NY, NZ = C.NX, C.NY, C.NZ
    i = (np.arange(NX) + 0.5 - NX / 2) / (NX / 2); j = (np.arange(NY) + 0.5 - NY / 2) / (NY / 2); k = np.arange(NZ) + 0.5
    ux, uy, z = i[:, None, None], j[None, :, None], k[None, None, :]
    rh = (ux ** 4 + uy ** 4) ** 0.25
    esc = NZ / 90.0
    n3 = _fbm((NX, NY, NZ), 24, rng, 3); n2 = _fbm((NX, NY, 1), 16, rng, 3)
    suelo = 2 + C.SUELO_RELIEVE * n2 ** 1.6
    techo = NZ - 3 - 26 * esc * rh ** 2 - 14 * esc * (n3 - 0.5)
    pared = 0.9 + 0.12 * (n3 - 0.5) - 0.05 * np.clip((z - NZ * 0.66) / (NZ * 0.34), 0, 1)
    C.SUELO = np.array(suelo[:, :, 0])
    aire = (rh < pared) & (z > suelo) & (z < techo)
    C.PILARES = []
    for _ in range(C.N_PILARES):
        cx, cy = rng.uniform(-0.6, 0.6, 2); r0 = rng.uniform(0.025, 0.06)
        C.PILARES.append(((cx + 1) * NX / 2, (cy + 1) * NY / 2, r0 * NX / 2))
        d = np.sqrt((ux - cx) ** 2 + (uy - cy) ** 2)
        aire &= ~(d < r0 * (1 + 0.6 * np.abs(z / NZ - 0.5) * 2) * (0.8 + 0.4 * n3))
    for _ in range(C.N_PUNTAS):
        cx, cy = rng.uniform(-0.85, 0.85, 2); r0 = rng.uniform(0.006, 0.02); L = rng.uniform(4, 18) * esc
        d = np.sqrt((ux - cx) ** 2 + (uy - cy) ** 2) * (NX / 2)
        ii = min(NX - 1, int((cx + 1) * NX / 2)); jj = min(NY - 1, int((cy + 1) * NY / 2))
        col = np.where(aire[ii, jj, :])[0]
        if len(col) == 0: continue
        if rng.random() < 0.6:
            top = col.max(); cono = (z <= top + 1) & (z > top - L) & (d < r0 * (NX / 2) * (z - (top - L)) / L * 3)
        else:
            bot = col.min(); cono = (z >= bot - 1) & (z < bot + L * 0.6) & (d < r0 * (NX / 2) * ((bot + L * 0.6) - z) / (L * 0.6) * 3)
        aire &= ~cono
    _lagos(C, aire, n2[:, :, 0], rng)
    return aire


def _lagos(C, aire, n2, rng):
    """lagos al pie de pilares: fondo en z 1, lava hasta NIVEL_LAVA, borde de roca a ras de la lava"""
    NX, NY = C.NX, C.NY
    I, J = np.meshgrid(np.arange(NX) + 0.5, np.arange(NY) + 0.5, indexing='ij'); C.LAGO = np.zeros((NX, NY), bool); C.LAGOS = []
    pilares = list(range(len(C.PILARES))); rng.shuffle(pilares)
    for p in pilares[:C.N_LAGOS]:
        R = C.RADIO_LAGO * rng.uniform(0.75, 1.1); irr = rng.uniform(0.4, 0.6); C.LAGOS.append((p, R))
        ci, cj, rp = C.PILARES[p]; ang = np.arctan2(J - cj, I - ci); d = np.hypot(I - ci, J - cj)
        borde = R * (1 + irr * 0.5 * (np.sin(3 * ang + p) * 0.6 + np.sin(5 * ang + 2 * p) * 0.4) + irr * (n2 - 0.5))
        dentro = ((I / NX * 2 - 1) ** 4 + (J / NY * 2 - 1) ** 4) ** 0.25 < 0.82
        lago = (d < borde) & (d > rp * 1.6 + 1) & dentro; anillo = (d < borde + 3) & ~lago & (d > rp * 1.6 + 1) & dentro
        aire[anillo, 0:3] = False
        aire[lago, 1:12] = True; aire[lago, 0] = False
        C.LAGO |= lago; C.SUELO[lago] = 1.0; C.SUELO[anillo] = np.maximum(C.SUELO[anillo], 3.0)


def _tipo_roca(C, rng):
    """piedra, zonas de andesita / diorita y minerales sueltos (carbon, cobre)"""
    sh = (C.NX, C.NY, C.NZ)
    zona = _fbm(sh, 14, rng, 2); zona2 = _fbm(sh, 10, rng, 2); veta = rng.random(sh)
    t = np.zeros(sh, np.int8); t[zona > 0.66] = 1; t[zona2 > 0.7] = 2
    t[(veta < 0.012) & (zona < 0.6)] = 3; t[(veta > 0.994) & (zona < 0.6)] = 4
    return t


# ----------------------------------------------------------------------------------------------------------------------- materiales
def _mat_bloque(C, tipo):
    """usa `<tipo>_all` si ya existe en el archivo; si no, lo crea con la textura del bloque (pixelada)"""
    m = bpy.data.materials.get(tipo + "_all")
    if m: return m
    m = bpy.data.materials.new(tipo + "_all"); m.use_nodes = True; nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'); b.inputs["Roughness"].default_value = 0.9
    ruta = os.path.join(C.TEXTURAS, tipo + ".png")
    if os.path.isfile(ruta):
        tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(ruta, check_existing=True); tex.interpolation = 'Closest'
        nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    return m


def _mat_lava(C, nombre, archivo, frames, frametime, pingpong, fuerza):
    """lava animada como en Minecraft: tira vertical de cuadros; un driver (expresion simple) mueve el UV segun el frame"""
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    N = nt.nodes.new; L = nt.links.new
    tex = N("ShaderNodeTexImage"); tex.interpolation = 'Closest'
    ruta = os.path.join(C.TEXTURAS, archivo)
    if os.path.isfile(ruta): tex.image = bpy.data.images.load(ruta, check_existing=True)
    uv = N("ShaderNodeTexCoord"); mp = N("ShaderNodeMapping"); mp.inputs["Scale"].default_value[1] = 1.0 / frames
    if pingpong: expr = "floor(abs(fmod(frame/%d, %d) - %d)) / %d" % (frametime, 2 * frames - 2, frames - 1, frames)
    else: expr = "floor(fmod(frame/%d, %d)) / %d" % (frametime, frames, frames)
    d = mp.inputs["Location"].driver_add("default_value", 1); d.driver.expression = "1 - 1.0/%d - (%s)" % (frames, expr)
    L(uv.outputs["UV"], mp.inputs["Vector"]); L(mp.outputs["Vector"], tex.inputs["Vector"])
    em = N("ShaderNodeEmission"); em.inputs["Strength"].default_value = fuerza; L(tex.outputs["Color"], em.inputs["Color"])
    L(em.outputs[0], N("ShaderNodeOutputMaterial").inputs[0])
    return m


def _malla(nombre, quads, mat, col):
    Q = np.asarray(quads, np.float32); n = len(Q)
    me = bpy.data.meshes.new(nombre)
    if n:
        me.vertices.add(n * 4); me.vertices.foreach_set("co", Q.reshape(-1).ravel())
        me.loops.add(n * 4); me.loops.foreach_set("vertex_index", np.arange(n * 4, dtype=np.int32))
        me.polygons.add(n); me.polygons.foreach_set("loop_start", np.arange(0, n * 4, 4, dtype=np.int32))
        uv = me.uv_layers.new(name="UVMap"); uv.data.foreach_set("uv", np.tile(np.array([0, 0, 1, 0, 1, 1, 0, 1], np.float32), n))
        me.update(calc_edges=True); me.validate()
    if mat: me.materials.append(mat)
    o = bpy.data.objects.new(nombre, me); col.objects.link(o); return o


# ----------------------------------------------------------------------------------------------------------------------- cascadas
def _cubos(C, celdas, aire):
    """caras exteriores de un conjunto de bloques de lava (no entre lava ni contra la roca)"""
    caras = [((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]), ((-1, 0, 0), [(0, 1, 0), (0, 0, 0), (0, 0, 1), (0, 1, 1)]),
             ((0, 1, 0), [(1, 1, 0), (0, 1, 0), (0, 1, 1), (1, 1, 1)]), ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
             ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]), ((0, 0, -1), [(0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0)])]
    q = []
    for (i, j, k) in celdas:
        for d, esq in caras:
            v = (i + d[0], j + d[1], k + d[2])
            if v in celdas: continue
            if 0 <= v[0] < C.NX and 0 <= v[1] < C.NY and 0 <= v[2] < C.NZ and not aire[v]: continue
            q.append([(i + a + C.ox, j + b + C.oy, k + c + C.oz) for a, b, c in esq])
    return q


def _planear_cascadas(C, aire, rng):
    """para cada cascada: pilar, cara (hacia el centro y visible desde la camara), altura de salida repartida (arriba / medio / abajo)
    y el punto de la pared con roca encima; abre el hueco del bloque fuente. C.PLAN = [(i, j, tope, dx, dy, brillo, luz, tono)]"""
    C.PLAN = []
    if not C.PILARES or not C.N_CASCADAS: return
    con_lago = {p for p, _ in C.LAGOS}
    orden = [p for p in range(len(C.PILARES)) if p not in con_lago] + [p for p in range(len(C.PILARES)) if p in con_lago]
    fracs = [0.72, 0.25, 0.47, 0.15, 0.6, 0.35, 0.8, 0.2]                  # alturas de salida en fraccion del alto
    cam = bpy.data.objects.get(C.CAMARA) if C.CAMARA else None
    for n_c in range(C.N_CASCADAS):
        p = orden[n_c % len(orden)]; ci, cj, rp = C.PILARES[p]; i0, j0 = int(ci), int(cj)
        vx, vy = C.NX / 2 - ci, C.NY / 2 - cj; caras = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        if cam:
            cx_, cy_ = cam.location.x - (ci + C.ox), cam.location.y - (cj + C.oy)
            caras = [c for c in caras if c[0] * cx_ + c[1] * cy_ > 0] or caras
        dx, dy = max(caras, key=lambda c: c[0] * vx + c[1] * vy); px, py = -dy, dx
        objetivo = int(C.NZ * fracs[n_c % len(fracs)]); mejor = None
        for tope in sorted(range(8, C.NZ - 12), key=lambda t: abs(t - objetivo)):
            for lat in (0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6):
                i, j = i0 + px * lat, j0 + py * lat
                while 0 <= i < C.NX and 0 <= j < C.NY and not aire[i, j, tope]: i += dx; j += dy
                if (0 <= i < C.NX and 0 <= j < C.NY and not aire[i - dx, j - dy, tope] and not aire[i - dx, j - dy, tope + 1]
                        and aire[i, j, tope - 1]):
                    mejor = (i, j, tope); break
            if mejor: break
        if mejor is None: continue
        i, j, tope = mejor; aire[i - dx, j - dy, tope] = True
        C.PLAN.append((i, j, tope, dx, dy, rng.uniform(0.6, 1.7), rng.uniform(0.45, 1.6), TONOS[n_c % len(TONOS)]))


def _recorrido(C, aire, i, j, k, dx, dy):
    """la lava cae como el agua: recta; si choca con un saliente avanza por encima hacia fuera y sigue cayendo"""
    c = []
    while k > 0:
        if not (0 <= i < C.NX and 0 <= j < C.NY) or not aire[i, j, k]: break
        c.append((i, j, k))
        if k - 1 < C.SUELO[i, j] or (C.LAGO[i, j] and k - 1 < C.NIVEL_LAVA): break
        if aire[i, j, k - 1]: k -= 1; continue
        pasos = 0
        while pasos < 12 and 0 <= i + dx < C.NX and 0 <= j + dy < C.NY and aire[i + dx, j + dy, k] and not aire[i, j, k - 1]:
            i += dx; j += dy; c.append((i, j, k)); pasos += 1
        if not aire[i, j, k - 1]: break
        k -= 1
    return c


def _rampa(C, i, j, tope, dx, dy):
    """la diagonal de la salida: de lo alto del bloque fuente (en la pared) al borde de fuera de la columna"""
    f = Vector((dx, dy, 0)); l = Vector((-dy, dx, 0)); c = Vector((i + C.ox + 0.5, j + C.oy + 0.5, 0))
    pared = c - f * 0.5; fuera = c + f * 0.5; zt = tope + C.oz
    A = pared - l * 0.5 + Vector((0, 0, zt + 1)); B = pared + l * 0.5 + Vector((0, 0, zt + 1))
    Cc = fuera + l * 0.5 + Vector((0, 0, zt)); D = fuera - l * 0.5 + Vector((0, 0, zt))
    E = pared - l * 0.5 + Vector((0, 0, zt)); F = pared + l * 0.5 + Vector((0, 0, zt))
    caras = []
    for cara, hacia in (([A, B, Cc, D], Vector((0, 0, 1)) + f), ([A, D, E, E], -l), ([B, F, Cc, Cc], l)):
        if (cara[1] - cara[0]).cross(cara[2] - cara[0]).dot(hacia) < 0: cara = cara[::-1]
        caras.append([tuple(v) for v in cara])
    return caras


def _lava(C, aire, col):
    """lagos, cascadas (un objeto y un material por cascada) y luces de area de la lava"""
    pre = C.COL + "_"
    quieta = _mat_lava(C, pre + "lava_quieta", "lava_still.png", 20, 2, True, C.BRILLO_LAGO)
    corre = _mat_lava(C, pre + "lava_cae", "lava_flow.png", 16, 2, False, C.BRILLO_CASCADA)
    luces = []
    if C.LAGO is not None and C.LAGO.any():
        q = [[(i + C.ox, j + C.oy, C.NIVEL_LAVA + C.oz), (i + 1 + C.ox, j + C.oy, C.NIVEL_LAVA + C.oz),
              (i + 1 + C.ox, j + 1 + C.oy, C.NIVEL_LAVA + C.oz), (i + C.ox, j + 1 + C.oy, C.NIVEL_LAVA + C.oz)] for i, j in zip(*np.nonzero(C.LAGO))]
        _malla(pre + "lava_lagos", q, quieta, col)
    for n, (i, j, tope, dx, dy, k_lava, k_luz, tono) in enumerate(C.PLAN):
        celdas = {(i - dx, j - dy, tope)}; fin = None
        for (a, b, k) in _recorrido(C, aire, i, j, tope - 1, dx, dy):
            celdas.add((a, b, k)); fin = (a + C.ox + 0.5, b + C.oy + 0.5, k + C.oz)
        m = corre.copy(); m.name = pre + "lava_cae_%d" % (n + 1)
        next(nd for nd in m.node_tree.nodes if nd.type == 'EMISSION').inputs["Strength"].default_value = C.BRILLO_CASCADA * k_lava
        _malla(pre + "lava_cascada_%d" % (n + 1), _cubos(C, celdas, aire) + _rampa(C, i, j, tope, dx, dy), m, col)
        if fin:                                                          # luz alargada que mira a la pared: se iluminan los bloques de al lado
            alto = tope + C.oz + 1 - fin[2]
            luces.append((Vector((fin[0] + dx * 1.6, fin[1] + dy * 1.6, fin[2] + alto / 2)), Vector((-dx, -dy, 0)), (1.2, alto),
                          C.LUZ_CASCADA * alto * k_luz, 150, tono))
    for p, R in C.LAGOS:                                                 # luz desde la superficie de la lava hacia arriba
        ci, cj, _ = C.PILARES[p]
        luces.append((Vector((ci + C.ox, cj + C.oy, C.NIVEL_LAVA + C.oz + 0.05)), Vector((0, 0, 1)), (R * 1.6, R * 1.6), C.LUZ_LAGO * R * R, 180, TONOS[0]))
    for n, (pos, normal, (sx, sy), e, apertura, tono) in enumerate(luces):
        ld = bpy.data.lights.new(pre + "luz_lava_%d" % n, "AREA"); ld.shape = 'RECTANGLE'; ld.size, ld.size_y = sx, sy
        ld.energy = e; ld.color = tono; ld.use_shadow = True; ld.spread = math.radians(apertura)
        try: ld.cycles.max_bounces = 1                                   # sin rebotes: techo y centro quedan a oscuras
        except Exception: pass
        lo = bpy.data.objects.new(ld.name, ld); lo.location = pos; col.objects.link(lo)
        if normal.z > 0.5: lo.rotation_euler = (math.pi, 0, 0)
        elif normal.z < -0.5: lo.rotation_euler = (0, 0, 0)
        else: lo.rotation_euler = (-normal).to_track_quat('Z', 'Y').to_euler()
    return len(C.PLAN)


# ----------------------------------------------------------------------------------------------------------------------- construir
def borrar(nombre):
    col = bpy.data.collections.get(nombre)
    if not col: return False
    for o in list(col.objects):
        d = o.data; bpy.data.objects.remove(o, do_unlink=True)
        if d is not None and d.users == 0:
            (bpy.data.meshes if isinstance(d, bpy.types.Mesh) else bpy.data.lights).remove(d)
    for m in [m for m in bpy.data.materials if m.name.startswith(nombre + "_lava") and m.users == 0]: bpy.data.materials.remove(m)
    bpy.data.collections.remove(col)
    return True


def construir(C):
    t0 = time.time(); rng = np.random.default_rng(C.SEMILLA)
    aire = campo(C, rng); tipo = _tipo_roca(C, rng)
    _planear_cascadas(C, aire, np.random.default_rng(C.SEMILLA + 7))
    borrar(C.COL); col = bpy.data.collections.new(C.COL); bpy.context.scene.collection.children.link(col)
    NX, NY, NZ = C.NX, C.NY, C.NZ
    pad = np.zeros((NX + 2, NY + 2, NZ + 2), bool); pad[1:-1, 1:-1, 1:-1] = aire
    tpad = np.zeros((NX + 2, NY + 2, NZ + 2), np.int8); tpad[1:-1, 1:-1, 1:-1] = tipo
    dirs = [((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]), ((-1, 0, 0), [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
            ((0, 1, 0), [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)]), ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
            ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]), ((0, 0, -1), [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)])]
    caras = {t: [] for t in range(len(TIPOS))}
    for d, esq in dirs:
        vec = np.roll(np.roll(np.roll(pad, -d[0], 0), -d[1], 1), -d[2], 2)
        tv = np.roll(np.roll(np.roll(tpad, -d[0], 0), -d[1], 1), -d[2], 2)
        ii, jj, kk = np.nonzero(pad & ~vec); tt = tv[ii, jj, kk]
        base = np.stack([ii - 1, jj - 1, kk - 1], 1).astype(np.float32)
        quad = np.stack([base + np.array(e, np.float32) for e in esq], 1)[:, ::-1, :]   # la cara mira al aire
        for t in range(len(TIPOS)):
            sel = quad[tt == t]
            if len(sel): caras[t].append(sel)
    total = 0
    for t, lst in caras.items():
        if not lst: continue
        Q = np.concatenate(lst, 0) + np.array([C.ox, C.oy, C.oz], np.float32); total += len(Q)
        _malla(C.COL + "_" + TIPOS[t], Q, _mat_bloque(C, TIPOS[t]), col)
    n_casc = _lava(C, aire, col)
    return {"caras": total, "lagos": len(C.LAGOS), "cascadas": n_casc, "segundos": round(time.time() - t0, 1)}


# ----------------------------------------------------------------------------------------------------------------------- interfaz
class CAVERNA_Props(bpy.types.PropertyGroup):
    coleccion: StringProperty(name="Coleccion", default="caverna", description="Cada caverna va en su propia coleccion")
    centro: FloatVectorProperty(name="Centro del suelo", size=3, subtype='TRANSLATION', default=(0.0, 0.0, 0.0))
    ancho: IntProperty(name="Ancho (X)", default=200, min=40, max=400)
    largo: IntProperty(name="Largo (Y)", default=200, min=40, max=400)
    alto: IntProperty(name="Alto (Z)", default=90, min=30, max=200)
    semilla: IntProperty(name="Semilla", default=11, description="Cambiala para otra forma")
    pilares: IntProperty(name="Pilares", default=7, min=0, max=30)
    puntas: IntProperty(name="Estalactitas/estalagmitas", default=140, min=0, max=600)
    relieve_suelo: FloatProperty(name="Relieve del suelo", default=9.0, min=0.0, max=30.0)
    usar_lava: BoolProperty(name="Lava", default=True)
    lagos: IntProperty(name="Lagos de lava", default=2, min=0, max=8)
    radio_lago: FloatProperty(name="Radio de los lagos", default=20.0, min=4.0, max=60.0)
    cascadas: IntProperty(name="Cascadas de lava", default=4, min=0, max=12)
    brillo_lago: FloatProperty(name="Brillo lava lagos", default=0.8, min=0.0, max=10.0)
    brillo_cascada: FloatProperty(name="Brillo lava cascadas", default=0.45, min=0.0, max=10.0)
    luz_lago: FloatProperty(name="Luz de los lagos (W/m2)", default=12.0, min=0.0, max=200.0)
    luz_cascada: FloatProperty(name="Luz de las cascadas (W/m)", default=25.0, min=0.0, max=500.0)
    camara: StringProperty(name="Camara", default="", description="Las cascadas caen por la cara que se ve desde esta camara (opcional)")
    texturas: StringProperty(name="Texturas de bloque", subtype='DIR_PATH', default="",
                             description="Carpeta textures/block del resource pack (vacio = MCprep por defecto)")


class CAVERNA_OT_generar(bpy.types.Operator):
    bl_idname = "cavernas.generar"; bl_label = "Generar caverna"; bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Crea (o rehace) la caverna en su coleccion"

    def execute(self, context):
        r = construir(Cfg(context.scene.caverna_sup))
        self.report({'INFO'}, "Caverna: %d caras, %d lagos, %d cascadas (%.1f s)" % (r["caras"], r["lagos"], r["cascadas"], r["segundos"]))
        return {'FINISHED'}


class CAVERNA_OT_borrar(bpy.types.Operator):
    bl_idname = "cavernas.borrar"; bl_label = "Borrar caverna"; bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ok = borrar(context.scene.caverna_sup.coleccion)
        self.report({'INFO'}, "Borrada" if ok else "No existe esa coleccion")
        return {'FINISHED'}


class CAVERNA_OT_cursor(bpy.types.Operator):
    bl_idname = "cavernas.cursor"; bl_label = "Centro = cursor 3D"

    def execute(self, context):
        context.scene.caverna_sup.centro = context.scene.cursor.location; return {'FINISHED'}


class CAVERNA_OT_camara(bpy.types.Operator):
    bl_idname = "cavernas.camara"; bl_label = "Usar camara activa"

    def execute(self, context):
        if context.scene.camera: context.scene.caverna_sup.camara = context.scene.camera.name
        return {'FINISHED'}


class CAVERNA_PT_panel(bpy.types.Panel):
    bl_label = "Generador de Cavernas"; bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = "Cavernas"

    def draw(self, context):
        p = context.scene.caverna_sup; L = self.layout
        b = L.box(); b.label(text="Caverna", icon='OUTLINER_COLLECTION'); b.prop(p, "coleccion")
        b.prop(p, "centro"); b.operator("cavernas.cursor", icon='PIVOT_CURSOR')
        r = b.row(align=True); r.prop(p, "ancho"); r.prop(p, "largo"); r.prop(p, "alto")
        b.prop(p, "semilla")
        b = L.box(); b.label(text="Forma", icon='MESH_ICOSPHERE'); b.prop(p, "pilares"); b.prop(p, "puntas"); b.prop(p, "relieve_suelo")
        b = L.box(); r = b.row(); r.label(text="Lava", icon='LIGHT_SUN'); r.prop(p, "usar_lava", text="")
        c = b.column(); c.enabled = p.usar_lava
        c.prop(p, "lagos"); c.prop(p, "radio_lago"); c.prop(p, "cascadas")
        c.prop(p, "brillo_lago"); c.prop(p, "brillo_cascada"); c.prop(p, "luz_lago"); c.prop(p, "luz_cascada")
        r = c.row(align=True); r.prop(p, "camara"); r.operator("cavernas.camara", text="", icon='CAMERA_DATA')
        b = L.box(); b.prop(p, "texturas")
        r = L.row(align=True); r.scale_y = 1.5
        r.operator("cavernas.generar", icon='PLAY'); r.operator("cavernas.borrar", icon='TRASH')


CLASES = (CAVERNA_Props, CAVERNA_OT_generar, CAVERNA_OT_borrar, CAVERNA_OT_cursor, CAVERNA_OT_camara, CAVERNA_PT_panel)


def register():
    for c in CLASES: bpy.utils.register_class(c)
    bpy.types.Scene.caverna_sup = PointerProperty(type=CAVERNA_Props)


def unregister():
    del bpy.types.Scene.caverna_sup
    for c in reversed(CLASES): bpy.utils.unregister_class(c)


if __name__ == "__main__":
    try: unregister()
    except Exception: pass
    register()
