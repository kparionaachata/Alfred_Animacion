# -*- coding: utf-8 -*-
"""
bloques.py -- Cerdo_1 Animation Studio: logica para COLOCAR BLOQUES de Minecraft (biblioteca `bloques_dinamicos`) en el mundo exportado.
Generaliza los scripts de la parte 9 (piso_cueva / pared_cueva / tapa_carbon). Cada operacion crea UNA coleccion marcada con `cerdo_1_st_bloques` y es repetible
(si la coleccion ya existe se rehace). Los bloques son copias enlazadas de una malla centrada por tipo (`blq_<archivo>`), 1 x 1 x 1 en la grilla del mundo.

  suelo(...)      rellena el SUELO de una cueva: celdas con cara de piso a z = nivel y AIRE encima, conectadas con el punto de inicio (relleno por vecinos, radio);
                  un bloque entero en z nivel-1 en cada celda (retira las caras planas del mundo, con copia oculta para deshacer) + montones irregulares por ruido.
  pared(...)      TAPA lo que sigue mas alla de una coleccion de suelo: columnas en las celdas del borde (desde el nivel hasta el techo) y filas escalonadas hacia dentro.
  caja(...)       llena una CAJA entre dos esquinas (solida o solo el cascaron / pared plana); opcion de irregularidad (quita bloques del borde superior al azar).
  reemplazar(...) cambia el tipo de bloque (todos o un % al azar) dentro de una coleccion, o pone bloques ENCIMA de los de un tipo (tapar).
  quitar(...)     borra una coleccion de bloques (y devuelve las caras del mundo si era un suelo).
"""
import bpy, bmesh, math, os, random
import numpy as np
from mathutils import Vector, Matrix

CARPETA = r"C:\Users\user\Desktop\Alfred_Animacion\bloques_dinamicos"
NO_CUBO = ("antorcha", "torch", "lantern", "campfire", "fogata", "fire", "banner", "arco", "slab", "smoke", "chest", "redstone_torch")
IGNORAR = ("flecha", "pan_", "miga_", "tunel_jerry_pico", "stone_pickaxe", "sombrero", "Bow_1", "skeleton")


# ---------------- biblioteca ----------------
def lista_bloques():
    """archivos .blend de bloques CUBICOS en la carpeta (sin antorchas, fogatas, cofres...)"""
    if not os.path.isdir(CARPETA): return []
    return sorted(f[:-6] for f in os.listdir(CARPETA) if f.endswith(".blend") and not any(k in f.lower() for k in NO_CUBO))


def malla(nombre):
    """malla centrada (1 m) del bloque `nombre` (archivo sin .blend); se importa una sola vez (`blq_<nombre>`, fake user)"""
    nm = "blq_" + nombre
    if nm in bpy.data.meshes: return bpy.data.meshes[nm]
    ruta = os.path.join(CARPETA, nombre + ".blend")
    with bpy.data.libraries.load(ruta, link=False) as (s_, d_): d_.objects = [n for n in s_.objects]
    obs = [o for o in d_.objects if o is not None]
    ob = max((o for o in obs if o.type == 'MESH'), key=lambda o: len(o.data.vertices), default=None)
    if ob is None: raise RuntimeError("%s no tiene mallas" % nombre)
    me = ob.data.copy(); me.name = nm; me.use_fake_user = True
    me.transform(ob.matrix_world)
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    me.transform(Matrix.Translation(-Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2))))
    for o in obs: bpy.data.objects.remove(o, do_unlink=True)
    return me


class Mezcla:
    """tipo de bloque por celda: principal + hasta 2 secundarios con su probabilidad (hash fijo por celda y semilla)"""
    def __init__(self, principal, sec1="", p1=0.0, sec2="", p2=0.0, semilla=1):
        self.t = [(sec1, p1), (sec2, p2)]; self.principal = principal; self.semilla = semilla; self.cache = {}

    def tipo(self, x, y, z):
        h = ((x * 73856093) ^ (y * 19349663) ^ (z * 83492791) ^ (self.semilla * 2654435761)) & 0xFFFFFFFF
        h ^= h >> 16; h = (h * 0x45D9F3B) & 0xFFFFFFFF; h ^= h >> 16; h = (h * 0x45D9F3B) & 0xFFFFFFFF; h ^= h >> 16      # mezcla de bits (el hash simple repetia valores)
        u = h / 4294967296.0; acc = 0.0
        for n, p in self.t:
            if n and p > 0:
                acc += p
                if u < acc: return n
        return self.principal

    def me(self, nombre):
        if nombre not in self.cache: self.cache[nombre] = malla(nombre)
        return self.cache[nombre]


# ---------------- utilidades de escena ----------------
def _es_personaje(o):
    return o.name.startswith(IGNORAR) or o.name.endswith(("_cerdo_1", "_jerry")) or any(m.type == 'ARMATURE' for m in getattr(o, "modifiers", []))


def coleccion(scene, nombre, modo):
    col = bpy.data.collections.get(nombre)
    if col: quitar(scene, nombre)
    col = bpy.data.collections.new(nombre); scene.collection.children.link(col); col["cerdo_1_st_bloques"] = modo; return col


def poner(col, mz, x, y, z, prefijo):
    t = mz.tipo(x, y, z); ob = bpy.data.objects.new("%s_%s_%d_%d_%d" % (prefijo, t, x, y, z), mz.me(t)); ob.location = (x + .5, y + .5, z + .5)
    col.objects.link(ob); return ob


def ocupadas(excluir=None):
    """celdas (x, y, z) ya ocupadas por bloques de TODAS las colecciones de bloques"""
    out = set()
    for c in bpy.data.collections:
        if "cerdo_1_st_bloques" in c and c.name != excluir:
            for o in c.objects:
                if o.type == 'MESH' and not o.hide_viewport: out.add((math.floor(o.location.x), math.floor(o.location.y), math.floor(o.location.z)))
    return out


def probador_aire(scene):
    dg = bpy.context.evaluated_depsgraph_get()
    def aire(x, y, z):
        """la celda (x, y, z) es aire: hacia arriba no hay nada hasta el bloque siguiente (los personajes no cuentan)"""
        p = Vector((x + .5, y + .5, z + .3))
        for _ in range(10):
            ok, loc, nor, i, o, m_ = scene.ray_cast(dg, p, Vector((0, 0, 1)), distance=60)
            if not ok: return True
            if _es_personaje(o.original): p = loc + Vector((0, 0, 0.01)); continue
            return loc.z > z + 1.0 - 0.01
        return False
    return aire


def caras_planas(nivel, centro, radio):
    """celda -> [(objeto, indice)] de las caras del mundo con centro a z = nivel (piso de la cueva), en un cuadrado de radio `radio`"""
    celda = {}
    for o_ in bpy.data.objects:
        if o_.type != 'MESH' or o_.parent is not None or _es_personaje(o_) or any("cerdo_1_st_bloques" in c for c in o_.users_collection): continue
        if o_.data.users > 1 or o_.name.startswith(("blq_", "piso_", "pared_", "tapa_")): continue   # bloques sueltos con malla COMPARTIDA: borrarles caras romperia todos
        me_ = o_.data; n_ = len(me_.polygons)
        if n_ == 0: continue
        bb = [o_.matrix_world @ Vector(v) for v in o_.bound_box]
        if min(v.z for v in bb) > nivel + 0.01 or max(v.z for v in bb) < nivel - 0.01: continue
        if max(v.x for v in bb) < centro[0] - radio - 1 or min(v.x for v in bb) > centro[0] + radio + 1 or max(v.y for v in bb) < centro[1] - radio - 1 or min(v.y for v in bb) > centro[1] + radio + 1: continue
        c_ = np.empty(n_ * 3); me_.polygons.foreach_get("center", c_); c_ = c_.reshape(n_, 3); W_ = np.array(o_.matrix_world); cw_ = c_ @ W_[:3, :3].T + W_[:3, 3]
        sel = np.where((np.abs(cw_[:, 2] - nivel) < 0.01) & (np.abs(cw_[:, 0] - centro[0]) < radio + 1) & (np.abs(cw_[:, 1] - centro[1]) < radio + 1))[0]
        for i in sel: celda.setdefault((math.floor(cw_[i, 0]), math.floor(cw_[i, 1])), []).append((o_, int(i)))
    return celda


def _retirar_caras(col, celdas, celda):
    """saca las caras planas del mundo bajo los bloques nuevos (evita el parpadeo); copia oculta `<col>_caras_<objeto>` para deshacer"""
    por = {}
    for k in celdas:
        for o_, i in celda.get(k, []): por.setdefault(o_.name, set()).add(i)
    n = 0
    for nom, idxs in por.items():
        o_ = bpy.data.objects[nom]; me_ = o_.data; idx = sorted(idxs); n += len(idx); mw = o_.matrix_world
        bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap"); uvd = me_.uv_layers[0].data if me_.uv_layers else None
        for i in idx:
            p = me_.polygons[i]
            try: f = bm.faces.new([bm.verts.new(mw @ me_.vertices[v].co) for v in p.vertices])
            except ValueError: continue
            f.material_index = p.material_index
            if uvd:
                for l, li in zip(f.loops, p.loop_indices): l[uvl].uv = uvd[li].uv
        mc = bpy.data.meshes.new(col.name + "_caras_" + nom); bm.to_mesh(mc); bm.free()
        for m_ in me_.materials: mc.materials.append(m_)
        cp = bpy.data.objects.new(col.name + "_caras_" + nom, mc); cp["origen"] = nom; cp["cerdo_1_st_caras"] = True; col.objects.link(cp); cp.hide_viewport = True; cp.hide_render = True
        b2 = bmesh.new(); b2.from_mesh(me_); b2.faces.ensure_lookup_table(); bmesh.ops.delete(b2, geom=[b2.faces[i] for i in idx], context='FACES_ONLY'); b2.to_mesh(me_); b2.free(); me_.update()
    return n


def _ruido(semilla):
    rng = random.Random(semilla); f = [(rng.uniform(0, 6.28), rng.uniform(0, 6.28)) for _ in range(3)]
    return lambda x, y: (math.sin(x * 0.55 + f[0][0]) * math.cos(y * 0.47 + f[0][1]) + 0.6 * math.sin(x * 1.3 + y * 0.9 + f[1][0]) + 0.35 * math.sin(y * 1.9 - x * 0.7 + f[2][1])) / 1.95


# ---------------- operaciones ----------------
def suelo(scene, nombre, mz, centro, radio=20.0, alto_max=2, densidad=0.5, libres=(), radio_libre=2.5, retirar=True, semilla=21):
    """rellena el suelo de la cueva desde `centro` (x, y, z = nivel del piso)"""
    nivel = round(centro[2]); celda = caras_planas(nivel, centro, radio); aire = probador_aire(scene); oc = ocupadas(nombre)
    ini = (math.floor(centro[0]), math.floor(centro[1]))
    if ini not in celda: raise RuntimeError("no hay cara de piso a z %d en la celda %s (pon el cursor ENCIMA del piso)" % (nivel, ini))
    vis = {ini}; cola = [ini]
    while cola:
        x, y = cola.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            k = (x + dx, y + dy)
            if k in celda and k not in vis and math.hypot(k[0] + .5 - centro[0], k[1] + .5 - centro[1]) <= radio and aire(k[0], k[1], nivel): vis.add(k); cola.append(k)
    col = coleccion(scene, nombre, "suelo"); col["nivel"] = nivel; rz = _ruido(semilla); rng = random.Random(semilla); n = 0
    umbrales = [1.0 - densidad * 0.9 * (0.55 ** j) for j in range(alto_max)]                  # mas densidad = mas montones; cada nivel mas raro
    for (x, y) in sorted(vis):
        if (x, y, nivel - 1) not in oc: poner(col, mz, x, y, nivel - 1, "blq"); n += 1
        if any(math.hypot(x + .5 - p[0], y + .5 - p[1]) < radio_libre for p in list(libres) + [centro]): continue
        r = (rz(x, y) * 0.5 + 0.5) + rng.uniform(-0.12, 0.12)
        for j in range(alto_max):
            z = nivel + j
            if r < umbrales[j] or (x, y, z) in oc or not aire(x, y, z): break
            poner(col, mz, x, y, z, "blq"); n += 1
    caras = _retirar_caras(col, vis, celda) if retirar else 0
    return {"celdas": len(vis), "bloques": n, "caras": caras}


def pared(scene, nombre, mz, nombre_suelo, alto_max=16, filas=4, semilla=33, libres=(), radio_libre=3.0):
    """tapa lo que sigue mas alla del suelo `nombre_suelo`: columnas en el borde + `filas` filas escalonadas hacia dentro"""
    cs = bpy.data.collections.get(nombre_suelo)
    if cs is None or cs.get("cerdo_1_st_bloques") != "suelo": raise RuntimeError("'%s' no es una coleccion de suelo del estudio" % nombre_suelo)
    nivel = int(cs.get("nivel", 0))
    llenas = {(math.floor(o.location.x), math.floor(o.location.y)) for o in cs.objects if o.type == 'MESH' and "cerdo_1_st_caras" not in o and math.floor(o.location.z) == nivel - 1}
    if not llenas: raise RuntimeError("el suelo esta vacio")
    xs = [k[0] for k in llenas]; ys = [k[1] for k in llenas]; c_ = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2); rad = max(max(xs) - min(xs), max(ys) - min(ys)) / 2 + 3
    fondo = caras_planas(nivel, c_, rad); aire = probador_aire(scene); oc = ocupadas(nombre)
    sobre = {}
    for o in cs.objects:
        if o.type == 'MESH' and "cerdo_1_st_caras" not in o and o.location.z > nivel: k = (math.floor(o.location.x), math.floor(o.location.y)); sobre[k] = max(sobre.get(k, nivel), math.floor(o.location.z) + 1)
    borde = set()
    for (x, y) in llenas:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            k = (x + dx, y + dy)
            if k not in llenas and k in fondo and aire(k[0], k[1], nivel): borde.add(k)
    col = coleccion(scene, nombre, "pared"); rng = random.Random(semilla); rz = _ruido(semilla); n = 0
    def columna(x, y, z0, h):
        nonlocal n
        z = z0
        while z < z0 + h and z < nivel + alto_max and (x, y, z) not in oc and aire(x, y, z): poner(col, mz, x, y, z, "blq"); n += 1; z += 1
    for (x, y) in sorted(borde): columna(x, y, nivel, alto_max)
    dist = {k: 0 for k in borde}; frente = list(borde)
    for d in range(1, filas + 1):
        nuevo = []
        for (x, y) in frente:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                k = (x + dx, y + dy)
                if k in llenas and k not in dist: dist[k] = d; nuevo.append(k)
        frente = nuevo
    for (x, y), d in sorted(dist.items()):
        if d == 0 or any(math.hypot(x + .5 - p[0], y + .5 - p[1]) < radio_libre for p in libres): continue
        prob = 0.85 * (0.62 ** (d - 1)); r = (rz(x, y) * 0.5 + 0.5) + rng.uniform(-0.2, 0.2)
        if r < 1.0 - prob: continue
        z0 = sobre.get((x, y), nivel); h_max = 0
        while z0 + h_max < nivel + alto_max and aire(x, y, z0 + h_max): h_max += 1
        frac = rng.uniform(max(0.0, 0.85 - 0.2 * d), max(0.15, 1.05 - 0.2 * d)); columna(x, y, z0, max(1, int(round(h_max * frac))))
    return {"borde": len(borde), "bloques": n}


def caja(scene, nombre, mz, a, b, hueca=False, irregular=0.0, semilla=7):
    """llena la caja de celdas entre las esquinas a y b (incluidas); hueca = solo el cascaron; irregular = prob. de quitar bloques de la capa superior"""
    x0, x1 = sorted((math.floor(a[0]), math.floor(b[0]))); y0, y1 = sorted((math.floor(a[1]), math.floor(b[1]))); z0, z1 = sorted((math.floor(a[2]), math.floor(b[2])))
    if (x1 - x0 + 1) * (y1 - y0 + 1) * (z1 - z0 + 1) > 60000: raise RuntimeError("caja demasiado grande (max 60000 bloques)")
    col = coleccion(scene, nombre, "caja"); oc = ocupadas(nombre); rng = random.Random(semilla); n = 0
    corte = {}
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            c = 0
            while c < (z1 - z0) and rng.random() < irregular: c += 1
            corte[(x, y)] = z1 - c
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in range(z0, corte[(x, y)] + 1):
                if hueca and x0 < x < x1 and y0 < y < y1 and z0 < z < z1: continue
                if (x, y, z) in oc: continue
                poner(col, mz, x, y, z, "blq"); n += 1
    return {"bloques": n}


def reemplazar(scene, nombre_col, tipo_de, tipo_a, porcentaje=1.0, encima=False, alto_encima=1, semilla=5):
    """en la coleccion: cambia los bloques `tipo_de` por `tipo_a` (un % al azar), o (encima=True) pone bloques `tipo_a` ENCIMA de ellos donde hay aire"""
    col = bpy.data.collections.get(nombre_col)
    if col is None or "cerdo_1_st_bloques" not in col: raise RuntimeError("'%s' no es una coleccion de bloques del estudio" % nombre_col)
    rng = random.Random(semilla); me_a = malla(tipo_a); objs = [o for o in col.objects if o.type == 'MESH' and o.data.name == "blq_" + tipo_de]; n = 0
    if not encima:
        for o in objs:
            if rng.random() < porcentaje: o.data = me_a; o.name = o.name.replace("_" + tipo_de + "_", "_" + tipo_a + "_"); n += 1
        return {"cambiados": n}
    aire = probador_aire(scene); oc = ocupadas()
    for o in objs:
        if rng.random() >= porcentaje: continue
        x, y, z = math.floor(o.location.x), math.floor(o.location.y), math.floor(o.location.z)
        for zz in range(z + 1, z + 1 + alto_encima):
            if (x, y, zz) in oc or not aire(x, y, zz): break
            ob = bpy.data.objects.new("blq_%s_%d_%d_%d" % (tipo_a, x, y, zz), me_a); ob.location = (x + .5, y + .5, zz + .5); col.objects.link(ob); oc.add((x, y, zz)); n += 1
    return {"encima": n}


def quitar(scene, nombre):
    """borra la coleccion de bloques; si tenia caras del mundo retiradas (suelo) las devuelve a su malla"""
    col = bpy.data.collections.get(nombre)
    if col is None: return 0
    dev = 0
    for cp in [o for o in col.objects if "cerdo_1_st_caras" in o]:
        src = bpy.data.objects.get(cp.get("origen", ""))
        if src is not None:
            me = src.data; inv = src.matrix_world.inverted(); bm = bmesh.new(); bm.from_mesh(me); uvl = bm.loops.layers.uv.verify(); sm = cp.data; uvd = sm.uv_layers[0].data if sm.uv_layers else None
            for p in sm.polygons:
                try: f = bm.faces.new([bm.verts.new(inv @ (cp.matrix_world @ sm.vertices[v].co)) for v in p.vertices])
                except ValueError: continue
                f.material_index = p.material_index; dev += 1
                if uvd:
                    for l, li in zip(f.loops, p.loop_indices): l[uvl].uv = uvd[li].uv
            bm.to_mesh(me); bm.free(); me.update()
        m_ = cp.data; bpy.data.objects.remove(cp, do_unlink=True)
        if m_.users == 0: bpy.data.meshes.remove(m_)
    for o in list(col.objects): bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(col)
    return dev
