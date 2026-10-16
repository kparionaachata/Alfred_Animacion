# -*- coding: utf-8 -*-
"""Parte 9: rellena el SUELO DE LA CUEVA (alrededor de donde cae Alfred) con bloques de `bloques_dinamicos`: `bloque_de_stone.blend` (la mayoria), algunos `copper_ore.blend`
y algunos `coal_ore.blend`, de forma IRREGULAR como el suelo de una cueva de Minecraft.
- El suelo de la cueva es el FONDO del mundo exportado (caras de `Stone` a z 0 mirando hacia abajo: desde arriba se ve su cara de espalda, lisa). Se buscan las celdas del fondo
  con AIRE encima conectadas con el punto de caida de Alfred (relleno por vecinos, radio RADIO m) y en cada una se pone un bloque entero en z -1..0 (la superficie sigue en z 0);
  esas caras del fondo se retiran (copia oculta `piso_cueva_caras_originales` para deshacer: `QUITAR = True`).
- Relieve: montones de 1 o 2 bloques encima (z 0..2) segun un ruido suave, solo donde la celda es aire; zona LIBRE plana de radio LIBRE alrededor de la caida (-133.5, -70.5).
- Tipo: semilla fija; cobre P_COBRE, carbon P_CARBON, el resto piedra. Los bloques comparten la malla (copias enlazadas), coleccion `piso_cueva_parte9`.
Ejecutar con `bpy.app.timers.register` (tarda). Repetible."""
import bpy, bmesh, math, random
import numpy as np
from mathutils import Vector, Matrix

QUITAR = bool(globals().get('QUITAR', False))
CAE = (-133.5, -70.5); ESQUELETO = (-139.5, -70.5); RADIO = 28.0; LIBRE = 2.6; P_COBRE = 0.06; P_CARBON = 0.015; SEMILLA = 21
DIR = r"C:\Users\user\Desktop\Alfred_Animacion\bloques_dinamicos\\"
COLN = "piso_cueva_parte9"; COPIA = "piso_cueva_caras_originales"
sc = bpy.context.scene; st = bpy.data.objects["Stone"]

def quitar():
    col = bpy.data.collections.get(COLN)
    if col:
        for o in list(col.objects):
            if o.name.startswith(COPIA): continue
            bpy.data.objects.remove(o, do_unlink=True)
    for cp in [o for o in bpy.data.objects if o.name.startswith(COPIA)]:                    # devolver las caras del fondo a su malla de origen
        src = bpy.data.objects.get(cp.get("origen", "Stone"))
        if src is None: continue
        me = src.data; inv = src.matrix_world.inverted(); bm = bmesh.new(); bm.from_mesh(me); uvl = bm.loops.layers.uv.verify(); sm = cp.data; uvd = sm.uv_layers[0].data if sm.uv_layers else None
        for p in sm.polygons:
            try: f = bm.faces.new([bm.verts.new(inv @ (cp.matrix_world @ sm.vertices[v].co)) for v in p.vertices])
            except ValueError: continue
            f.material_index = p.material_index
            if uvd:
                for l, li in zip(f.loops, p.loop_indices): l[uvl].uv = uvd[li].uv
        bm.to_mesh(me); bm.free(); me.update(); m_ = cp.data; bpy.data.objects.remove(cp, do_unlink=True)
        if m_.users == 0: bpy.data.meshes.remove(m_)
    if col: bpy.data.collections.remove(col)
quitar()
if QUITAR:
    print("piso de la cueva quitado")
else:
    # ---------- mallas de los bloques (centradas) ----------
    def malla(archivo, obn, nom):
        if nom in bpy.data.meshes: return bpy.data.meshes[nom]
        with bpy.data.libraries.load(DIR + archivo, link=False) as (s_, d_): d_.objects = [obn]
        ob = d_.objects[0]; me = ob.data; me.name = nom; me.use_fake_user = True
        xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
        me.transform(Matrix.Translation(-Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2))))
        bpy.data.objects.remove(ob, do_unlink=True); return me
    M = {"piedra": malla("bloque_de_stone.blend", "stone", "piso_bloque_piedra"), "cobre": malla("copper_ore.blend", "copper_ore", "piso_bloque_cobre"),
         "carbon": malla("coal_ore.blend", "coal_ore", "piso_bloque_carbon")}
    # ---------- celdas del fondo con aire encima, conectadas con la caida ----------
    celda = {}                                                                              # celda -> [(objeto, indice de cara)] de TODAS las mallas del mundo con caras del fondo (Stone, Andesite...)
    for o_ in bpy.data.objects:
        if o_.type != 'MESH' or o_.name.startswith(("piso_", "tunel_", "techo_", "flecha", "pan_", "pared_", "tapa_")) or o_.name.endswith(("_alfred", "_jerry")) or o_.parent is not None: continue
        if any(m_.type == 'ARMATURE' for m_ in o_.modifiers): continue
        me_ = o_.data; n_ = len(me_.polygons)
        if n_ == 0: continue
        bb = [o_.matrix_world @ Vector(v) for v in o_.bound_box]
        if min(v.z for v in bb) > 0.01 or max(v.x for v in bb) < CAE[0] - RADIO - 1 or min(v.x for v in bb) > CAE[0] + RADIO + 1 or max(v.y for v in bb) < CAE[1] - RADIO - 1 or min(v.y for v in bb) > CAE[1] + RADIO + 1: continue
        c_ = np.empty(n_ * 3); me_.polygons.foreach_get("center", c_); c_ = c_.reshape(n_, 3); W_ = np.array(o_.matrix_world); cw_ = c_ @ W_[:3, :3].T + W_[:3, 3]
        sel_ = np.where((np.abs(cw_[:, 2]) < 0.01) & (np.abs(cw_[:, 0] - CAE[0]) < RADIO + 1) & (np.abs(cw_[:, 1] - CAE[1]) < RADIO + 1))[0]
        for i in sel_: celda.setdefault((math.floor(cw_[i, 0]), math.floor(cw_[i, 1])), []).append((o_, int(i)))
    dg = bpy.context.evaluated_depsgraph_get()
    OCU = {o.name for o in bpy.data.objects if o.type == 'MESH' and (o.name.endswith('_alfred') or o.name.startswith(('flecha', 'pan_alfred', 'tunel_jerry_pico', 'stone_pickaxe')))}
    def aire(x, y, z):
        """la celda (x, y, z) es aire: hacia arriba no hay nada hasta por lo menos el bloque siguiente"""
        p = Vector((x + .5, y + .5, z + .3))
        for _ in range(6):
            ok, loc, nor, i, o, m_ = sc.ray_cast(dg, p, Vector((0, 0, 1)), distance=40)
            if not ok: return True
            if o.original.name in OCU: p = loc + Vector((0, 0, 0.01)); continue
            return loc.z > z + 1.0 - 0.01                                              # el primer obstaculo hacia arriba esta a mas de 1 bloque (las caras del techo de esta cueva miran hacia ARRIBA: el exportador la trato como roca)
        return False
    ini = (math.floor(CAE[0]), math.floor(CAE[1])); vis = {ini}; cola = [ini]
    while cola:
        x, y = cola.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            k = (x + dx, y + dy)
            if k in celda and k not in vis and math.hypot(k[0] + .5 - CAE[0], k[1] + .5 - CAE[1]) <= RADIO and aire(k[0], k[1], 0): vis.add(k); cola.append(k)
    # ---------- relieve irregular y tipos ----------
    rng = random.Random(SEMILLA)
    fases = [(rng.uniform(0, 6.28), rng.uniform(0, 6.28)) for _ in range(3)]
    def ruido(x, y):
        return (math.sin(x * 0.55 + fases[0][0]) * math.cos(y * 0.47 + fases[0][1]) + 0.6 * math.sin(x * 1.3 + y * 0.9 + fases[1][0]) + 0.35 * math.sin(y * 1.9 - x * 0.7 + fases[2][1])) / 1.95
    def tipo(x, y, z):
        h = ((x * 73856093) ^ (y * 19349663) ^ (z * 83492791) ^ SEMILLA) & 0xFFFF; u = h / 65535.0
        return "cobre" if u < P_COBRE else ("carbon" if u < P_COBRE + P_CARBON else "piedra")
    BL = []
    for (x, y) in vis:
        BL.append((x, y, -1))
        if math.hypot(x + .5 - CAE[0], y + .5 - CAE[1]) < LIBRE or math.hypot(x + .5 - ESQUELETO[0], y + .5 - ESQUELETO[1]) < 1.6: continue     # libres: donde cae Alfred y donde dispara el esqueleto
        r = ruido(x, y) + rng.uniform(-0.25, 0.25)
        alto = 3 if r > 0.78 else (2 if r > 0.5 else (1 if r > 0.18 else 0))
        for z in range(alto):
            if aire(x, y, z) and aire(x, y, z + 1 if z + 1 < 2 else z): BL.append((x, y, z))
            else: break
    # ---------- colocar ----------
    col = bpy.data.collections.new(COLN); sc.collection.children.link(col)
    cuenta = {"piedra": 0, "cobre": 0, "carbon": 0}
    for (x, y, z) in BL:
        t = tipo(x, y, z); ob = bpy.data.objects.new("piso_%s_%d_%d_%d" % (t, x, y, z), M[t]); ob.location = (x + .5, y + .5, z + .5); col.objects.link(ob); cuenta[t] += 1
    # ---------- retirar las caras del fondo bajo los bloques (copia oculta) ----------
    por_obj = {}
    for k in vis:
        for o_, i in celda[k]: por_obj.setdefault(o_.name, set()).add(i)
    nret = 0
    for nom_, idxs in por_obj.items():
        o_ = bpy.data.objects[nom_]; me_ = o_.data; idx = sorted(idxs); nret += len(idx)
        bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap"); uvd = me_.uv_layers[0].data if me_.uv_layers else None; mw = o_.matrix_world
        for i in idx:
            p = me_.polygons[i]
            try: f = bm.faces.new([bm.verts.new(mw @ me_.vertices[v].co) for v in p.vertices])
            except ValueError: continue
            f.material_index = p.material_index
            if uvd:
                for l, li in zip(f.loops, p.loop_indices): l[uvl].uv = uvd[li].uv
        mc = bpy.data.meshes.new(COPIA + "_" + nom_); bm.to_mesh(mc); bm.free()
        for m_ in me_.materials: mc.materials.append(m_)
        cp = bpy.data.objects.new(COPIA + "_" + nom_, mc); cp["origen"] = nom_; col.objects.link(cp); cp.hide_viewport = True; cp.hide_render = True
        b2 = bmesh.new(); b2.from_mesh(me_); b2.faces.ensure_lookup_table(); bmesh.ops.delete(b2, geom=[b2.faces[i] for i in idx], context='FACES_ONLY'); b2.to_mesh(me_); b2.free(); me_.update()
    idx = list(range(nret))
    print("PISO CUEVA: %d celdas, %d bloques %s, %d caras del fondo retiradas" % (len(vis), len(BL), cuenta, len(idx)))
