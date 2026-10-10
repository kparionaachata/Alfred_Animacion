# -*- coding: utf-8 -*-
"""Parte 8: la GEOMETRIA del tunel que cava Alfred. El mundo esta hecho de mallas por tipo de bloque donde solo existen las caras expuestas (las interiores no estan), asi que "romper" un bloque es:
  1. TAPAS: las caras expuestas de la celda rota (las que miran a aire: entrada del tunel y la cueva) se copian a objetos `tunel_tapa_*` (visibles hasta el frame de la ruptura) y se BORRAN de la malla original (`a.001`, `Dirt`, `Stone`...);
  2. CARAS NUEVAS: las caras de los bloques vecinos que quedan a la vista (paredes, techo, suelo y el fondo del tunel) aparecen en el frame de la ruptura (`tunel_cara_*`, tierra = material `dirt` de `a.001`, piedra = material de `Stone`) y desaparecen si ese vecino se rompe despues.
Cada objeto se muestra/oculta con claves CONSTANT de `hide_viewport` / `hide_render`. Lee `tunel_eventos.json` (frame de impacto -> celdas, de `tunel_alfred_parte8.py`) y `tunel_plan.json`.
Hace falta que las celdas de las rupturas sean las del plan; NO repetir sin recargar la escena (las caras originales ya estan borradas). Se ejecuta DENTRO de Blender con exec."""
import bpy, bmesh, json, math, numpy as np
from mathutils import Vector

R = "C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/parte8/"
sc = bpy.context.scene
EV = json.load(open(R + "tunel_eventos.json", encoding="utf-8")); PLAN = json.load(open(R + "tunel_plan.json", encoding="utf-8"))
T_ROTO = {}                                                                     # celda -> frame en que se rompe
for e in EV["eventos"]:
    for c in e["celdas"]: T_ROTO[tuple(c)] = e["frame"]
DIRS = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
xs = [c[0] for c in T_ROTO]; ys = [c[1] for c in T_ROTO]; zs = [c[2] for c in T_ROTO]
BOX = (min(xs) - 1.6, max(xs) + 2.6, min(ys) - 1.6, max(ys) + 2.6, min(zs) - 1.6, max(zs) + 2.6)
IGNORAR = {"Short_Grass", "Fern", "Large_Fern", "Birch_Leaves", "Oak_Leaves", "Spruce_Leaves", "Allium", "Dandelion", "Azure_Bluet", "Poppy", "Seagrass", "Brown_Mushroom", "Glow_Lichen", "Stationary_Water"}
STONE_OBJ = bpy.data.objects["Stone"]; A001 = bpy.data.objects["a.001"]

# ---- indice de caras expuestas cerca del tunel ----
INDEX = {}
def indexar(o):
    me = o.data; n = len(me.polygons)
    if n == 0: return 0
    c = np.empty(n * 3); nr = np.empty(n * 3); me.polygons.foreach_get("center", c); me.polygons.foreach_get("normal", nr); c = c.reshape(n, 3); nr = nr.reshape(n, 3)
    M = np.array(o.matrix_world); cw = c @ M[:3, :3].T + M[:3, 3]; nw = nr @ M[:3, :3].T; nw /= np.maximum(np.linalg.norm(nw, axis=1, keepdims=True), 1e-9)
    ok = np.where((cw[:, 0] >= BOX[0]) & (cw[:, 0] <= BOX[1]) & (cw[:, 1] >= BOX[2]) & (cw[:, 1] <= BOX[3]) & (cw[:, 2] >= BOX[4]) & (cw[:, 2] <= BOX[5]))[0]
    for i in ok:
        k = (int(round(cw[i, 0] * 2)), int(round(cw[i, 1] * 2)), int(round(cw[i, 2] * 2)))
        INDEX.setdefault(k, []).append((o, int(i), nw[i].copy()))
    return len(ok)
tot = 0
for o in bpy.data.objects:
    if o.type == "MESH" and o.name not in IGNORAR and "minecraft_world_ecenario_2" in [c.name for c in o.users_collection]:
        mn = Vector([min((o.matrix_world @ Vector(v))[i] for v in o.bound_box) for i in range(3)]); mx = Vector([max((o.matrix_world @ Vector(v))[i] for v in o.bound_box) for i in range(3)])
        if mx.x < BOX[0] or mn.x > BOX[1] or mx.y < BOX[2] or mn.y > BOX[3] or mx.z < BOX[4] or mn.z > BOX[5]: continue
        tot += indexar(o)
print("caras indexadas", tot)

# ---- tipo de los bloques vecinos (piedra / tierra) ----
SV = [STONE_OBJ.matrix_world @ v.co for v in STONE_OBJ.data.vertices]
SV = [w for w in SV if BOX[0] - 2 <= w.x <= BOX[1] + 2 and BOX[2] - 2 <= w.y <= BOX[3] + 2 and BOX[4] - 2 <= w.z <= BOX[5] + 2]
def es_piedra(c):
    p = Vector((c[0] + .5, c[1] + .5, c[2] + .5)); return sum(1 for w in SV if (w - p).length < 0.9) >= 3
# ---- el vecino es solido? Rayo desde el centro de la cara compartida hacia el vecino: sin impacto o cara de frente = AIRE/cueva (no se pone cara); cara de espalda = macizo ----
_dg = bpy.context.evaluated_depsgraph_get(); _CACHE = {}
def es_solido_dir(fc, d):
    k = (round(fc[0] * 2), round(fc[1] * 2), round(fc[2] * 2), d)
    if k in _CACHE: return _CACHE[k]
    dv = Vector(d); ok, loc, nor, idx, ob, mat = sc.ray_cast(_dg, Vector(fc) + dv * 0.01, dv, distance=60)
    _CACHE[k] = bool(ok and nor.dot(dv) > 0); return _CACHE[k]
# ---- plantillas de textura ----
def rect_uv(o, pi):
    me = o.data; uv = me.uv_layers[0].data; p = me.polygons[pi]; us = [uv[l].uv[0] for l in p.loop_indices]; vs = [uv[l].uv[1] for l in p.loop_indices]
    return (min(us), min(vs), max(us), max(vs)), p.material_index
tmpl_dirt = None
for p in A001.data.polygons:
    if p.material_index == 1: tmpl_dirt = rect_uv(A001, p.index); break
tmpl_stone = rect_uv(STONE_OBJ, 0)
print("plantillas", tmpl_dirt, tmpl_stone)

# ---- calcular caras ----
cubiertas = {}                                                                  # t_off -> lista (obj, poly_index)
nuevas = {}                                                                     # (tipo, t_on, t_off) -> lista de (centro_cara, normal)
def cara_vecina(C, d):
    N = (C[0] + d[0], C[1] + d[1], C[2] + d[2]); return N
SKIP_X = globals().get('SKIP_CARAS_X')                                        # celdas con x <= SKIP_CARAS_X: no se ponen caras nuevas (el tunel ya desemboco en la cueva: nada de bloques al final)
for C, tC in T_ROTO.items():
    for d in DIRS:
        fc = (C[0] + .5 + .5 * d[0], C[1] + .5 + .5 * d[1], C[2] + .5 + .5 * d[2]); k = (int(round(fc[0] * 2)), int(round(fc[1] * 2)), int(round(fc[2] * 2)))
        propias = [(o, i) for (o, i, nw) in INDEX.get(k, []) if nw[0] * d[0] + nw[1] * d[1] + nw[2] * d[2] > 0.9]
        N = cara_vecina(C, d)
        if propias:                                                             # esa cara de C estaba expuesta (miraba a aire): tapa hasta tC
            cubiertas.setdefault(tC, []).extend(propias)
        elif SKIP_X is not None and C[0] <= SKIP_X and d[0] != 0:                             # tramo final: sin caras nuevas
            pass
        elif N in T_ROTO:                                                       # vecino tambien se rompe: la cara de C mirando a N aparece cuando se rompe N si N va antes y se va cuando se rompe C
            tN = T_ROTO[N]
            if tN < tC: nuevas.setdefault(("piedra" if es_piedra(C) else "tierra", tN, tC), []).append((fc, (-d[0], -d[1], -d[2])))
        elif es_solido_dir(fc, d):                                                      # vecino solido sin romper: su cara hacia C aparece en tC (si es aire/cueva no se pone nada)
            nuevas.setdefault(("piedra" if es_piedra(N) else "tierra", tC, 10 ** 6), []).append((fc, (-d[0], -d[1], -d[2])))

# ---- CASCARON del tunel donde la cueva no tiene piso / paredes / techo (pedido): caras de tierra y piedra alrededor del corredor, que aparecen cuando Alfred se acerca ----
HULL = globals().get('HULL_X')                                                  # (x_max, x_min) columnas del corredor a rellenar, p. ej. (-120, -130)
if HULL:
    import random as _rnd
    rng = _rnd.Random(3); YC_ = -70
    try: LL = {int(k): v for k, v in json.load(open(R + "tunel_llegadas.json", encoding="utf-8")).items()}
    except Exception: LL = {}
    for x in range(HULL[0], HULL[1] - 1, -1):
        zf = int(math.floor(9.0 - 3.0 * (-106.5 - (x + 0.5)) / 25.0 + 0.001)); t_on = max(2, LL.get(x + 4, 2))
        for z in range(zf, zf + 3):
            C = (x, YC_, z)
            for d in ((0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                N = (x + d[0], YC_ + d[1], z + d[2]); fc = (C[0] + .5 + .5 * d[0], C[1] + .5 + .5 * d[1], C[2] + .5 + .5 * d[2])
                if N[1] == YC_ and zf <= N[2] <= zf + 2: continue
                if es_solido_dir(fc, d): continue                                # ya hay roca ahi
                tipo_ = "tierra" if d == (0, 0, -1) else ("piedra" if rng.random() < 0.5 else "tierra")
                nuevas.setdefault((tipo_, t_on, 10 ** 6), []).append((fc, (-d[0], -d[1], -d[2])))
    print("cascaron: caras", sum(len(v) for k, v in nuevas.items()))

print("tapas", {t: len(v) for t, v in sorted(cubiertas.items())})
print("caras nuevas grupos", len(nuevas), "total", sum(len(v) for v in nuevas.values()))

# ---- crear objetos ----
col = bpy.data.collections.get("tunel") or bpy.data.collections.new("tunel")
if col.name not in [c.name for c in sc.collection.children]: sc.collection.children.link(col)
def accion_vis(o, t_on, t_off):
    pts = [(1, 1.0 if t_on > 1 else 0.0)]
    if t_on > 1: pts.append((t_on, 0.0))
    if t_off < 10 ** 5: pts.append((t_off, 1.0))
    o.hide_viewport = pts[0][1] > 0.5; o.hide_render = pts[0][1] > 0.5
    if o.animation_data is None: o.animation_data_create()
    a = bpy.data.actions.new("vis_" + o.name); slot = a.slots.new(id_type='OBJECT', name=o.name); layer = a.layers.new("Capa"); strip = layer.strips.new(type='KEYFRAME'); cb = strip.channelbag(slot, ensure=True)
    for dp in ("hide_viewport", "hide_render"):
        fc = cb.fcurves.new(dp, index=0); fc.keyframe_points.add(len(pts)); fc.keyframe_points.foreach_set("co", [v for p in pts for v in p])
        for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
        fc.update()
    o.animation_data.action = a; o.animation_data.action_slot = slot

def cuadrado(fc, n):                                                            # 4 vertices (mundo) de la cara con centro fc y normal n, con el sentido que apunta a n
    ax = [i for i in range(3) if n[i] != 0][0]; o1, o2 = [i for i in range(3) if i != ax]
    pts = []
    for s1, s2 in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        v = [fc[0], fc[1], fc[2]]; v[o1] += .5 * s1; v[o2] += .5 * s2; pts.append(Vector(v))
    nrm = (pts[1] - pts[0]).cross(pts[2] - pts[1])
    if nrm.dot(Vector(n)) < 0: pts.reverse()
    return pts

n_obj = 0; nombres = []
for (tipo, t_on, t_off), caras in sorted(nuevas.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0])):
    src = A001 if tipo == "tierra" else STONE_OBJ; (u0, v0, u1, v1), mi = tmpl_dirt if tipo == "tierra" else tmpl_stone
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    for (fc, n) in caras:
        vs = [bm.verts.new(p) for p in cuadrado(fc, n)]
        try: f = bm.faces.new(vs)
        except ValueError: continue
        f.material_index = mi
        for l, (u, v) in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))): l[uvl].uv = (u, v)
    me = bpy.data.meshes.new("tunel_cara_%d" % n_obj); bm.to_mesh(me); bm.free()
    for m in src.data.materials: me.materials.append(m)
    ob = bpy.data.objects.new("tunel_cara_%d_%s_%d" % (n_obj, tipo, t_on), me); col.objects.link(ob); accion_vis(ob, t_on, t_off); n_obj += 1; nombres.append(ob.name)

BORRAR = {}
def copiar_poligonos(lista, t_off):
    por_obj = {}
    for (o, i) in lista: por_obj.setdefault(o, set()).add(i)
    for o, idx in por_obj.items():
        me = o.data; mw = o.matrix_world; uvd = me.uv_layers[0].data if me.uv_layers else None
        bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
        for i in sorted(idx):
            p = me.polygons[i]; vs = [bm.verts.new(mw @ me.vertices[vi].co) for vi in p.vertices]
            try: f = bm.faces.new(vs)
            except ValueError: continue
            f.material_index = p.material_index
            if uvd:
                for l, li in zip(f.loops, p.loop_indices): l[uvl].uv = uvd[li].uv
        mc = bpy.data.meshes.new("tunel_tapa_m"); bm.to_mesh(mc); bm.free()
        for m in me.materials: mc.materials.append(m)
        ob = bpy.data.objects.new("tunel_tapa_%s_%d" % (o.name, t_off), mc); col.objects.link(ob); accion_vis(ob, 1, t_off); nombres.append(ob.name)
        BORRAR.setdefault(o, set()).update(idx)
for t_off, lista in sorted(cubiertas.items()): copiar_poligonos(list({(id(o), i): (o, i) for o, i in lista}.values()), t_off)
for o, idx in BORRAR.items():                                                   # borrar de las mallas originales (una sola vez por objeto: los indices no cambian antes)
    me = o.data; b2 = bmesh.new(); b2.from_mesh(me); b2.faces.ensure_lookup_table()
    bmesh.ops.delete(b2, geom=[b2.faces[i] for i in sorted(idx)], context='FACES_ONLY'); b2.to_mesh(me); b2.free(); me.update()
print("objetos creados", len(nombres), "| caras borradas", {o.name: len(v) for o, v in BORRAR.items()})
