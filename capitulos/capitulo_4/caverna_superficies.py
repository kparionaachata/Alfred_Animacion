# -*- coding: utf-8 -*-
"""Caverna de 200 x 200 x 90 bloques hecha SOLO con superficies (una malla por material, sin objetos-bloque): se calcula una rejilla de
aire/piedra con ruido (estilo "cheese cave" de Minecraft: boveda irregular, suelo con montículos, paredes con entrantes, pilares y
estalactitas) y se crean unicamente las caras cubicas entre el aire y la roca, con la textura de bloque (16 px) en cada cara.
Materiales: los `<tipo>_all` de los bloques de la escena (piedra, andesita, diorita, carbon, cobre).
Centro del suelo en CENTRO. Uso: exec(open(ruta, encoding="utf8").read()); construir()      (repetible: borra lo anterior)
"""
import bpy, bmesh, math
import numpy as np
from mathutils import Vector

CENTRO = (-0.0471, 0.3381, 0.0157)       # alineada a la rejilla de bloques del tunel (que entra por (0.5, 82.5, 66))
NX, NY, NZ = 200, 200, 90
SEMILLA = 11
COL = "caverna_superficies"
TIPOS = ["stone", "andesite", "diorite", "coal_ore", "copper_ore"]
LAVA_DIR = r"C:/Users/user/AppData/Roaming/Blender Foundation/Blender/5.2/scripts/addons/MCprep_addon/MCprep_resources/resourcepacks/mcprep_default/assets/minecraft/textures/block/"
LAGOS = ((0, 22, 0.55), (1, 17, 0.45))   # (pilar en cuyo pie esta el lago, radio en bloques, irregularidad)
NIVEL_LAVA = 2.9                         # superficie de la lava (el fondo del lago esta en z 1)
CASCADAS = (5, 4, 2, 6)                 # pilares con cascada (los marcados por el usuario en la vista de Camera.001)
ALTURAS_CASCADAS = (64, 22, 42, 14)      # altura de salida de cada cascada: arriba, abajo, medio, muy abajo
BRILLO_CASCADA = 0.45                    # brillo base de la lava que cae
INTENSIDAD_CASCADAS = (                   # cada cascada distinta: (x brillo de la lava, x luz que refleja en la pared, color de la luz)
    (1.0, 1.0, (1.0, 0.35, 0.08)),        # normal
    (1.7, 1.6, (1.0, 0.42, 0.1)),         # caudal grande, muy viva
    (0.6, 0.45, (1.0, 0.28, 0.05)),       # fina, mas apagada y roja
    (1.3, 0.8, (1.0, 0.38, 0.09)),        # brillante pero refleja poco
)
LUZ_APERTURA = 50                        # grados del haz de las luces de lava (spread del area)
CAMARA = "Camera.001"                   # la cascada cae por la cara que mira al centro y que se ve desde esta camara
PILARES = []                             # (i, j, radio medio en bloques) de cada pilar, para los lagos y las cascadas
LAGO = None                              # mascara 2D de los lagos
SUELO = None                             # altura del suelo de cada columna (2D)


def _ruido(shape, celda, rng):
    """ruido de valor 3D suave (0..1): rejilla aleatoria cada `celda` bloques, interpolada con smoothstep"""
    gs = [s // celda + 3 for s in shape]; G = rng.random(gs).astype(np.float32); out = G
    for ax, n in enumerate(shape):
        t = (np.arange(n, dtype=np.float32) + 0.5) / celda; i0 = np.floor(t).astype(int); f = t - i0; f = f * f * (3 - 2 * f)
        a = np.take(out, i0, axis=ax); b = np.take(out, i0 + 1, axis=ax)
        sh = [1] * len(shape); sh[ax] = n; f = f.reshape(sh)
        out = a + (b - a) * f
    return out


def _fbm(shape, celda, rng, oct_=3):
    s = np.zeros(shape, np.float32); amp = 1.0; tot = 0.0
    for o in range(oct_):
        s += amp * _ruido(shape, max(2, celda // (2 ** o)), rng); tot += amp; amp *= 0.5
    return s / tot


def campo(rng):
    """True = aire"""
    i = (np.arange(NX) + 0.5 - NX / 2) / (NX / 2); j = (np.arange(NY) + 0.5 - NY / 2) / (NY / 2); k = np.arange(NZ) + 0.5
    ux, uy, z = i[:, None, None], j[None, :, None], k[None, None, :]
    rh = (ux ** 4 + uy ** 4) ** 0.25                                             # planta casi cuadrada con esquinas redondas
    n3 = _fbm((NX, NY, NZ), 24, rng, 3)                                          # irregularidad de paredes y boveda
    n2 = _fbm((NX, NY, 1), 16, rng, 3)                                           # relieve del suelo
    suelo = 2 + 9 * n2 ** 1.6                                                    # montículos
    techo = NZ - 3 - 26 * rh ** 2 - 14 * (n3 - 0.5)                              # boveda: alta al centro, baja en los bordes
    pared = 0.9 + 0.12 * (n3 - 0.5) - 0.05 * np.clip((z - 60) / 30, 0, 1)        # entrantes y salientes
    global SUELO; SUELO = np.array(suelo[:, :, 0])
    aire = (rh < pared) & (z > suelo) & (z < techo)
    # pilares de roca que van del suelo al techo
    PILARES.clear()
    for _ in range(7):
        cx, cy = rng.uniform(-0.6, 0.6, 2); r0 = rng.uniform(0.025, 0.06)
        PILARES.append(((cx + 1) * NX / 2, (cy + 1) * NY / 2, r0 * NX / 2))
        d = np.sqrt((ux - cx) ** 2 + (uy - cy) ** 2)
        r = r0 * (1 + 0.6 * np.abs(z / NZ - 0.5) * 2) * (0.8 + 0.4 * n3)          # mas anchos arriba y abajo
        aire &= ~(d < r)
    # estalactitas y estalagmitas
    for _ in range(140):
        cx, cy = rng.uniform(-0.85, 0.85, 2); r0 = rng.uniform(0.006, 0.02); L = rng.uniform(4, 18)
        d = np.sqrt((ux - cx) ** 2 + (uy - cy) ** 2) * (NX / 2)
        ii = min(NX - 1, int((cx + 1) * NX / 2)); jj = min(NY - 1, int((cy + 1) * NY / 2))
        if rng.random() < 0.6:
            col = np.where(aire[ii, jj, :])[0]
            if len(col) == 0: continue
            top = col.max(); cono = (z <= top + 1) & (z > top - L) & (d < r0 * (NX / 2) * (z - (top - L)) / L * 3)
        else:
            col = np.where(aire[ii, jj, :])[0]
            if len(col) == 0: continue
            bot = col.min(); cono = (z >= bot - 1) & (z < bot + L * 0.6) & (d < r0 * (NX / 2) * ((bot + L * 0.6) - z) / (L * 0.6) * 3)
        aire &= ~cono
    _lagos(aire, n2[:, :, 0])
    return aire


def _lagos(aire, n2):
    """dos lagos al pie de dos pilares: fondo en z 1, lava hasta NIVEL_LAVA, borde de roca a la misma altura alrededor"""
    global LAGO
    I, J = np.meshgrid(np.arange(NX) + 0.5, np.arange(NY) + 0.5, indexing='ij'); LAGO = np.zeros((NX, NY), bool)
    for p, R, irr in LAGOS:
        ci, cj, rp = PILARES[p]; ang = np.arctan2(J - cj, I - ci); d = np.hypot(I - ci, J - cj)
        borde = R * (1 + irr * 0.5 * (np.sin(3 * ang + p) * 0.6 + np.sin(5 * ang + 2 * p) * 0.4) + irr * (n2 - 0.5))
        dentro = ((I / NX * 2 - 1) ** 4 + (J / NY * 2 - 1) ** 4) ** 0.25 < 0.82
        lago = (d < borde) & (d > rp * 1.6 + 1) & dentro; anillo = (d < borde + 3) & ~lago & (d > rp * 1.6 + 1) & dentro
        aire[anillo, 0:3] = False                                         # borde de roca a ras de la lava
        for k in range(1, 12): aire[lago, k] = aire[lago, k] | (k >= 1)
        aire[lago, 0] = False; LAGO |= lago; SUELO[lago] = 1.0; SUELO[anillo] = np.maximum(SUELO[anillo], 3.0)


def _mat_lava(nombre, archivo, frames, frametime, pingpong, fuerza):
    """lava animada como en Minecraft: tira vertical de `frames` cuadros; un driver mueve el UV al cuadro que toca segun el frame"""
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    N = nt.nodes.new; L = nt.links.new
    img = bpy.data.images.load(LAVA_DIR + archivo, check_existing=True)
    tex = N("ShaderNodeTexImage"); tex.image = img; tex.interpolation = 'Closest'
    uv = N("ShaderNodeTexCoord"); mp = N("ShaderNodeMapping"); mp.inputs["Scale"].default_value[1] = 1.0 / frames
    if pingpong: expr = "floor(abs(fmod(frame/%d, %d) - %d)) / %d" % (frametime, 2 * frames - 2, frames - 1, frames)   # expresion simple (sin Python)
    else: expr = "floor(fmod(frame/%d, %d)) / %d" % (frametime, frames, frames)
    d = mp.inputs["Location"].driver_add("default_value", 1); d.driver.expression = "1 - 1.0/%d - (%s)" % (frames, expr)
    L(uv.outputs["UV"], mp.inputs["Vector"]); L(mp.outputs["Vector"], tex.inputs["Vector"])
    em = N("ShaderNodeEmission"); em.inputs["Strength"].default_value = fuerza; L(tex.outputs["Color"], em.inputs["Color"])
    out = N("ShaderNodeOutputMaterial"); L(em.outputs[0], out.inputs[0])
    return m


def _malla(nombre, quads, mat, col):
    Q = np.asarray(quads, np.float32); n = len(Q)
    me = bpy.data.meshes.new(nombre); me.vertices.add(n * 4); me.vertices.foreach_set("co", Q.reshape(-1).ravel())
    me.loops.add(n * 4); me.loops.foreach_set("vertex_index", np.arange(n * 4, dtype=np.int32))
    me.polygons.add(n); me.polygons.foreach_set("loop_start", np.arange(0, n * 4, 4, dtype=np.int32))
    uv = me.uv_layers.new(name="UVMap"); uv.data.foreach_set("uv", np.tile(np.array([0, 0, 1, 0, 1, 1, 0, 1], np.float32), n))
    me.update(calc_edges=True); me.materials.append(mat)
    o = bpy.data.objects.new(nombre, me); col.objects.link(o); return o


def _cubos(celdas, aire, ox, oy, oz):
    """caras exteriores de un conjunto de celdas (bloques de lava): solo donde el vecino no es lava ni roca"""
    caras = [((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]), ((-1, 0, 0), [(0, 1, 0), (0, 0, 0), (0, 0, 1), (0, 1, 1)]),
             ((0, 1, 0), [(1, 1, 0), (0, 1, 0), (0, 1, 1), (1, 1, 1)]), ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
             ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]), ((0, 0, -1), [(0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0)])]
    q = []
    for (i, j, k) in celdas:
        for d, esq in caras:
            v = (i + d[0], j + d[1], k + d[2])
            if v in celdas: continue
            if 0 <= v[0] < NX and 0 <= v[1] < NY and 0 <= v[2] < NZ and not aire[v]: continue     # pegado a la roca
            q.append([(i + a + ox, j + b + oy, k + c + oz) for a, b, c in esq])
    return q


def _planear_cascadas(aire, ox, oy):
    """elige, para cada pilar de CASCADAS, el punto de la pared de donde sale la lava (un bloque fuente hundido en la roca, como en
    Minecraft) y desde el que cae recta sin tocar nada; abre ese hueco en la roca. Devuelve [(i, j, tope, dx, dy)]"""
    rng = np.random.default_rng(SEMILLA + 7); plan = []
    for n_c, p in enumerate(CASCADAS):
        ci, cj, rp = PILARES[p]; i0, j0 = int(ci), int(cj)
        vx, vy = NX / 2 - ci, NY / 2 - cj                                  # hacia el centro de la caverna
        cam = bpy.data.objects.get(CAMARA); caras = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        if cam:                                                          # solo caras que se ven desde la camara
            cx_, cy_ = cam.location.x - (ci + ox), cam.location.y - (cj + oy)
            caras = [c for c in caras if c[0] * cx_ + c[1] * cy_ > 0] or caras
        dx, dy = max(caras, key=lambda c: c[0] * vx + c[1] * vy)
        px, py = -dy, dx                                                   # px, py: a lo largo de la cara del pilar
        def libre(i, j, k):                                                # la columna (i, j) esta libre desde k hasta el suelo?
            for kk in range(k, 0, -1):
                if kk < SUELO[i, j] or (LAGO[i, j] and kk < NIVEL_LAVA): return True
                if not aire[i, j, kk]: return False
            return True
        mejor = None
        objetivo = ALTURAS_CASCADAS[n_c % len(ALTURAS_CASCADAS)]
        for tope in sorted(range(8, 75), key=lambda t: abs(t - objetivo)):   # la altura libre mas parecida a la de esta cascada
            for lat in (0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6):
                i, j = i0 + px * lat, j0 + py * lat
                while 0 <= i < NX and 0 <= j < NY and not aire[i, j, tope]: i += dx; j += dy
                if (0 <= i < NX and 0 <= j < NY and not aire[i - dx, j - dy, tope] and not aire[i - dx, j - dy, tope + 1]
                        and aire[i, j, tope - 1]):                         # (si choca con un saliente, la lava lo recorre y sigue cayendo)
                    mejor = (i, j, tope); break                            # sale de la roca y cae recto sin tocar nada
            if mejor: break
        if mejor is None: continue
        i, j, tope = mejor; aire[i - dx, j - dy, tope] = True             # hueco de la fuente en la pared
        plan.append((i, j, tope, dx, dy))
    return plan


PLAN_CASCADAS = []


def _recorrido(aire, i, j, k, dx, dy):
    """celdas por las que pasa la lava como agua: cae recta; al chocar con roca avanza hacia fuera (dx, dy) por encima del saliente
    hasta que vuelve a tener aire debajo y sigue cayendo; termina en el suelo o en un lago"""
    c = []
    while k > 0:
        if not (0 <= i < NX and 0 <= j < NY) or not aire[i, j, k]: break
        c.append((i, j, k))
        if k - 1 < SUELO[i, j] or (LAGO[i, j] and k - 1 < NIVEL_LAVA): break
        if aire[i, j, k - 1]: k -= 1; continue
        pasos = 0                                                          # saliente: fluye hacia fuera sobre el
        while pasos < 12 and 0 <= i + dx < NX and 0 <= j + dy < NY and aire[i + dx, j + dy, k] and not aire[i, j, k - 1]:
            i += dx; j += dy; c.append((i, j, k)); pasos += 1
        if not aire[i, j, k - 1]: break                                    # se encharca
        k -= 1
    return c


def _rampa(i, j, tope, dx, dy, ox, oy, oz):
    """la diagonal de la salida: superficie inclinada desde lo alto de la fuente (en la pared) hasta el borde de fuera de la columna"""
    f = Vector((dx, dy, 0)); l = Vector((-dy, dx, 0))
    c = Vector((i + ox + 0.5, j + oy + 0.5, 0))                            # centro de la celda de la columna
    pared = c - f * 0.5; fuera = c + f * 0.5; zt = tope + oz
    A = pared - l * 0.5 + Vector((0, 0, zt + 1)); B = pared + l * 0.5 + Vector((0, 0, zt + 1))
    C = fuera + l * 0.5 + Vector((0, 0, zt)); D = fuera - l * 0.5 + Vector((0, 0, zt))
    E = pared - l * 0.5 + Vector((0, 0, zt)); F = pared + l * 0.5 + Vector((0, 0, zt))
    caras = []
    for cara, hacia in (([A, B, C, D], Vector((0, 0, 1)) + f), ([A, D, E, E], -l), ([B, F, C, C], l)):
        n = (cara[1] - cara[0]).cross(cara[2] - cara[0])
        if n.dot(hacia) < 0: cara = cara[::-1]
        caras.append([tuple(v) for v in cara])
    return caras


def _lava(aire, col, ox, oy, oz):
    """superficie de los lagos, cascadas por las caras de los pilares y luces naranjas"""
    quieta = _mat_lava("caverna_lava_quieta", "lava_still.png", 20, 2, True, 0.8)
    corre = _mat_lava("caverna_lava_cae", "lava_flow.png", 16, 2, False, BRILLO_CASCADA)
    q = []
    for i, j in zip(*np.nonzero(LAGO)):
        x, y, z = i + ox, j + oy, NIVEL_LAVA + oz
        q.append([(x, y, z), (x + 1, y, z), (x + 1, y + 1, z), (x, y + 1, z)])
    _malla("caverna_lava_lagos", q, quieta, col)
    luces = []
    for n, (i, j, tope, dx, dy) in enumerate(PLAN_CASCADAS):              # cada cascada es su propio objeto, con su brillo
        k_lava, k_luz, tono = INTENSIDAD_CASCADAS[n % len(INTENSIDAD_CASCADAS)]
        celdas = set(); fin = None
        celdas.add((i - dx, j - dy, tope))                                 # bloque fuente hundido en la pared
        for (ci_, cj_, k) in _recorrido(aire, i, j, tope - 1, dx, dy):     # cae; si choca con un saliente lo recorre y sigue cayendo
            celdas.add((ci_, cj_, k)); fin = (ci_ + ox + 0.5, cj_ + oy + 0.5, k + oz)
        q = _cubos(celdas, aire, ox, oy, oz) + _rampa(i, j, tope, dx, dy, ox, oy, oz)
        m = corre.copy(); m.name = "caverna_lava_cae_%d" % (n + 1)
        next(nd for nd in m.node_tree.nodes if nd.type == 'EMISSION').inputs["Strength"].default_value = BRILLO_CASCADA * k_lava
        _malla("caverna_lava_cascada_%d" % (n + 1), q, m, col)
        if fin:                                                          # luz de area alargada: mira a la pared, se iluminan los bloques de al lado
            alto = tope + oz + 1 - fin[2]; pos = Vector((fin[0] + dx * 1.6, fin[1] + dy * 1.6, fin[2] + alto / 2))
            luces.append((pos, Vector((-dx, -dy, 0)), (1.2, alto), 25.0 * alto * k_luz, 150, tono))
    for p, R, _ in LAGOS:
        ci, cj, _ = PILARES[p]
        # la luz sale de la propia superficie de la lava hacia arriba: solo alumbra lo que ve la lava (caras que miran al lago,
        # salientes por debajo); el suelo de alrededor, a la misma altura, apenas recibe luz rasante
        luces.append((Vector((ci + ox, cj + oy, NIVEL_LAVA + oz + 0.05)), Vector((0, 0, 1)), (R * 1.6, R * 1.6), 12.0 * R * R, 180, (1.0, 0.35, 0.08)))
    for n, (pos, normal, (sx, sy), e, apertura, tono) in enumerate(luces):
        ld = bpy.data.lights.new("caverna_luz_lava_%d" % n, "AREA"); ld.shape = 'RECTANGLE'; ld.size, ld.size_y = sx, sy
        ld.energy = e; ld.color = tono; ld.use_shadow = True
        ld.spread = math.radians(apertura); ld.cycles.max_bounces = 1     # haz estrecho y sin rebotes: techo y centro quedan a oscuras
        lo = bpy.data.objects.new(ld.name, ld); lo.location = pos; col.objects.link(lo)
        if normal.z > 0.5: lo.rotation_euler = (math.pi, 0, 0)          # el area emite hacia -Z: girada mira arriba
        elif normal.z < -0.5: lo.rotation_euler = (0, 0, 0)             # mira abajo
        else: lo.rotation_euler = (-normal).to_track_quat('Z', 'Y').to_euler()  # -Z hacia fuera del pilar, size_y vertical
    return len(q)


def _tipo_roca(rng):
    """material de cada celda de roca: piedra, vetas de andesita/diorita por zonas y minerales sueltos"""
    zona = _fbm((NX, NY, NZ), 14, rng, 2); zona2 = _fbm((NX, NY, NZ), 10, rng, 2); veta = rng.random((NX, NY, NZ))
    t = np.zeros((NX, NY, NZ), np.int8)
    t[zona > 0.66] = 1; t[zona2 > 0.7] = 2
    t[(veta < 0.012) & (zona < 0.6)] = 3; t[(veta > 0.994) & (zona < 0.6)] = 4
    return t


CONEXIONES = (((-0.03, 82.0, 66.03), (0.93, 178.0, 69.0)),)   # interior de tuneles que entran en la caverna: (min, max) del mundo


def abrir_conexion(caja):
    """borra las caras de la caverna que quedan dentro del hueco de un tunel (para conectar el tunel con la caverna)"""
    (x0, y0, z0), (x1, y1, z1) = caja; quitadas = 0
    for o in bpy.data.collections[COL].objects:
        if o.type != 'MESH': continue
        bm = bmesh.new(); bm.from_mesh(o.data); mw = o.matrix_world
        fuera = [f for f in bm.faces if (lambda c: x0 < c.x < x1 and y0 < c.y < y1 and z0 < c.z < z1)(mw @ f.calc_center_median())]
        if fuera:
            bmesh.ops.delete(bm, geom=fuera, context='FACES'); bm.to_mesh(o.data); o.data.update(); quitadas += len(fuera)
        bm.free()
    return quitadas


def construir():
    rng = np.random.default_rng(SEMILLA)
    aire = campo(rng); tipo = _tipo_roca(rng)
    PLAN_CASCADAS[:] = _planear_cascadas(aire, CENTRO[0] - NX / 2, CENTRO[1] - NY / 2)   # antes de la roca: abre los huecos de las fuentes
    col = bpy.data.collections.get(COL)
    if col:
        for o in list(col.objects):
            me = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if me and me.users == 0:
                (bpy.data.meshes if isinstance(me, bpy.types.Mesh) else bpy.data.lights).remove(me)
    else:
        col = bpy.data.collections.new(COL); bpy.context.scene.collection.children.link(col)
    pad = np.zeros((NX + 2, NY + 2, NZ + 2), bool); pad[1:-1, 1:-1, 1:-1] = aire
    caras = {t: [] for t in range(len(TIPOS))}
    # 6 direcciones: cara entre celda de aire (a) y roca vecina (a+d); normal hacia el aire
    dirs = [((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]), ((-1, 0, 0), [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
            ((0, 1, 0), [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)]), ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
            ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]), ((0, 0, -1), [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)])]
    tpad = np.zeros((NX + 2, NY + 2, NZ + 2), np.int8); tpad[1:-1, 1:-1, 1:-1] = tipo
    for d, esq in dirs:
        vec = np.roll(np.roll(np.roll(pad, -d[0], 0), -d[1], 1), -d[2], 2)
        tv = np.roll(np.roll(np.roll(tpad, -d[0], 0), -d[1], 1), -d[2], 2)
        ii, jj, kk = np.nonzero(pad & ~vec)
        tt = tv[ii, jj, kk]
        base = np.stack([ii - 1, jj - 1, kk - 1], 1).astype(np.float32)
        quad = np.stack([base + np.array(e, np.float32) for e in esq], 1)       # (n, 4, 3); orden: normal hacia la roca
        quad = quad[:, ::-1, :]                                                  # invertido: la cara mira al aire
        for t in range(len(TIPOS)):
            sel = quad[tt == t]
            if len(sel): caras[t].append(sel)
    ox, oy, oz = CENTRO[0] - NX / 2, CENTRO[1] - NY / 2, CENTRO[2]
    total = 0
    for t, lst in caras.items():
        if not lst: continue
        Q = np.concatenate(lst, 0); n = len(Q); total += n
        V = (Q.reshape(-1, 3) + np.array([ox, oy, oz], np.float32)).astype(np.float32)
        me = bpy.data.meshes.new("caverna_" + TIPOS[t])
        me.vertices.add(n * 4); me.vertices.foreach_set("co", V.ravel())
        me.loops.add(n * 4); me.loops.foreach_set("vertex_index", np.arange(n * 4, dtype=np.int32))
        me.polygons.add(n); me.polygons.foreach_set("loop_start", np.arange(0, n * 4, 4, dtype=np.int32))
        uv = me.uv_layers.new(name="UVMap"); uv.data.foreach_set("uv", np.tile(np.array([0, 0, 1, 0, 1, 1, 0, 1], np.float32), n))
        me.update(calc_edges=True); me.validate()
        mat = bpy.data.materials.get(TIPOS[t] + "_all")
        if mat: me.materials.append(mat)
        o = bpy.data.objects.new("caverna_" + TIPOS[t], me); col.objects.link(o)
    cascadas = _lava(aire, col, ox, oy, oz)
    for caja in CONEXIONES: abrir_conexion(caja)
    return {"caras": total, "aire_celdas": int(aire.sum()), "lava_lagos": int(LAGO.sum()), "lava_cascadas_caras": cascadas, "objetos": [o.name for o in col.objects]}
