# -*- coding: utf-8 -*-
"""Arboles talables de 'Alfred tala arboles y los bonobos le tiran cosas' (base_tarde con las ranas.blend, 24 fps).
Los dos robles con los que interactua Alfred (T1 en x-80,y32 y T2 en x-78,y29) estaban fundidos en las mallas gigantes del mundo (Oak_Log / Oak_Leaves). Aqui se
SACAN de esas mallas y se rehacen con bloques de verdad: troncos = `bloques_dinamicos/bloque_de_roble.blend`, hojas = cubo con el material `oak_leaves` del mundo.
Animacion de talar (se engancha a los frames de los hachazos de Alfred, G['choques1..4']):
  - ruptura PROGRESIVA como en Minecraft: el progreso sube de forma continua mientras Alfred talla (texturas destroy_stage_0..9 cambiando fotograma a fotograma),
    se acumula entre rafagas de hachazos y suelta astillas con gravedad real en cada impacto;
  - T1: el 5o hachazo completa la ruptura (astillas + el item del tronco que rebota en el suelo). Como en Minecraft el arbol NO cae: lo de arriba queda en su sitio;
  - T2: los hachazos solo lo agrietan (los interrumpen los bonobos).
Uso (escena viva):  exec(open(este_archivo).read()); talar_arboles()     (idempotente: restaura y reconstruye)"""
import bpy, bmesh, math, json, random
import numpy as np
from mathutils import Vector, Matrix

RUT = r"C:\Users\user\Desktop\Alfred_Animacion"
BLOQUE = RUT + r"\bloques_dinamicos\bloque_de_roble.blend"
GRIETA = RUT + r"\kebyn proyecto  1.20.1_analysis\kebyn proyecto  1.20.1\assets\minecraft\textures\block\destroy_stage_%d.png"
COL = 'arboles_talables'
SUELO_Z = 12.0
G_F = 9.81 / (24.0 * 24.0)
# troncos de cada arbol (celdas = esquina minima del bloque de 1 m); hojas y ramas se asignan al arbol mas cercano
TRONCO = {'T1': (-80, 32), 'T2': (-78, 29)}
CAJA_ARB = (-83.0, -75.0, 26.0, 36.0)         # x0, x1, y0, y1 donde estan las copas y las ramas de T1/T2
GOLPEA = {'T1': (-80, 32, 13), 'T2': (-78, 29, 13)}   # bloque que golpea el hacha de Alfred (z de la mano ~13.3)


def _celdas(obj):
    """celda (entera) a la que pertenece cada poligono de la malla (en mundo): centro - 0.5*normal"""
    me = obj.data; n = len(me.polygons)
    cen = np.empty(n * 3); nor = np.empty(n * 3)
    me.polygons.foreach_get('center', cen); me.polygons.foreach_get('normal', nor)
    M = np.array(obj.matrix_world); R = M[:3, :3]
    c = cen.reshape(-1, 3) @ R.T + M[:3, 3]; nn = nor.reshape(-1, 3) @ R.T
    return np.floor(c - 0.5 * nn + 1e-6).astype(int)


def _coleccion():
    c = bpy.data.collections.get(COL)
    if c is None:
        c = bpy.data.collections.new(COL); bpy.context.scene.collection.children.link(c)
    return c


def restaurar():
    """vuelve las mallas del mundo a su estado original y borra los bloques creados antes"""
    c = bpy.data.collections.get(COL)
    if c:
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    for nm in ('Oak_Log', 'Oak_Leaves'):
        orig = bpy.data.meshes.get(nm + '_orig_arboles')
        ob = bpy.data.objects.get(nm)
        if orig and ob:
            viejo = ob.data
            ob.data = orig.copy(); ob.data.name = nm
            if viejo.users == 0 and viejo is not orig:
                bpy.data.meshes.remove(viejo)


def _respaldo():
    for nm in ('Oak_Log', 'Oak_Leaves'):
        if bpy.data.meshes.get(nm + '_orig_arboles') is None:
            m = bpy.data.objects[nm].data.copy(); m.name = nm + '_orig_arboles'; m.use_fake_user = True


def _borrar_caras(obj, idx):
    bm = bmesh.new(); bm.from_mesh(obj.data); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in idx], context='FACES')
    bm.to_mesh(obj.data); bm.free(); obj.data.update()


def _plantillas():
    """malla del bloque de roble (de bloques_dinamicos) y la de hojas (mismo cubo con el material oak_leaves del mundo)"""
    if bpy.data.meshes.get('arb_bloque_roble') and bpy.data.meshes.get('arb_bloque_hojas'):
        return bpy.data.meshes['arb_bloque_roble'], bpy.data.meshes['arb_bloque_hojas']
    with bpy.data.libraries.load(BLOQUE, link=False) as (src, dst):
        dst.objects = list(src.objects)
    ob = dst.objects[0]
    log = ob.data; log.name = 'arb_bloque_roble'; log.use_fake_user = True
    mundo = {'lados': bpy.data.materials['oak_log'], 'tapas': bpy.data.materials['oak_log_top']}     # las texturas del .blend del bloque no cargan por ruta: se usan las del mundo (mismas imagenes)
    for i, m in enumerate(list(log.materials)):
        if m and m.name.startswith('oak_log_'):
            log.materials[i] = mundo['tapas'] if m.name.rsplit('.', 1)[0].endswith(('_up', '_down')) else mundo['lados']
    hoja = log.copy(); hoja.name = 'arb_bloque_hojas'; hoja.use_fake_user = True
    hoja.materials.clear(); hoja.materials.append(bpy.data.materials['oak_leaves'])
    for p in hoja.polygons:
        p.material_index = 0
    bpy.data.objects.remove(ob, do_unlink=True)
    return log, hoja


def _bloque(nombre, malla, celda, col, escala=1.0):
    o = bpy.data.objects.new(nombre, malla)
    o.location = (celda[0] + 0.5, celda[1] + 0.5, celda[2])
    o.scale = (escala,) * 3
    col.objects.link(o)
    return o


def construir():
    """saca los dos robles de las mallas del mundo y los rehace con bloques. Devuelve dict con troncos/hojas por arbol"""
    restaurar(); _respaldo()
    col = _coleccion()
    log, hoja = _plantillas()
    olog = bpy.data.objects['Oak_Log']; olv = bpy.data.objects['Oak_Leaves']
    cl = _celdas(olog); cv = _celdas(olv)
    x0, x1, y0, y1 = CAJA_ARB
    en = lambda c: (x0 <= c[0] < x1) and (y0 <= c[1] < y1)
    idx_log = [i for i, c in enumerate(cl) if en(c)]
    idx_lv = [i for i, c in enumerate(cv) if en(c) and c[2] >= 15]
    cel_log = sorted(set(map(tuple, cl[idx_log].tolist())))
    cel_lv = sorted(set(map(tuple, cv[idx_lv].tolist())))
    cen = {k: Vector((v[0] + 0.5, v[1] + 0.5)) for k, v in TRONCO.items()}

    def arbol(c):
        p = Vector((c[0] + 0.5, c[1] + 0.5))
        return min(cen, key=lambda k: (p - cen[k]).length)
    _borrar_caras(olog, idx_log); _borrar_caras(olv, idx_lv)
    res = {'T1': {'log': [], 'hoja': []}, 'T2': {'log': [], 'hoja': []}}
    for c in cel_log:
        k = arbol(c)
        res[k]['log'].append(_bloque('arb%s_log_%d_%d_%d' % (k, c[0], c[1], c[2]), log, c, col))
    for c in cel_lv:
        k = arbol(c)
        res[k]['hoja'].append(_bloque('arb%s_hoja_%d_%d_%d' % (k, c[0], c[1], c[2]), hoja, c, col))
    res['_mallas'] = (log, hoja)
    print('bloques de tronco', {k: len(v['log']) for k, v in res.items() if k[0] == 'T'}, 'hojas', {k: len(v['hoja']) for k, v in res.items() if k[0] == 'T'})
    return res


# ------------------------------------------------------------------ animacion
def _vis(o, f, oculto):
    o.hide_render = oculto; o.hide_viewport = oculto
    o.keyframe_insert('hide_render', frame=f); o.keyframe_insert('hide_viewport', frame=f)


def _constante(objs):
    for o in objs:
        ad = o.animation_data
        if not ad or not ad.action:
            continue
        a = ad.action
        fcs = list(a.fcurves) if hasattr(a, 'fcurves') else [c for l in a.layers for s in l.strips for b in s.channelbags for c in b.fcurves]
        for c in fcs:
            for k in c.keyframe_points:
                k.interpolation = 'CONSTANT' if 'hide' in c.data_path else 'LINEAR'


def _mat_grieta(n):
    """grieta destroy_stage_n del color de la madera del tronco: los pixeles oscuros/claros de la textura se tiñen con tonos marron de la corteza del roble (la alfa de la textura da la forma)"""
    nm = 'arb_grieta_m_%d' % n
    m = bpy.data.materials.get(nm)
    if m:
        return m
    m = bpy.data.materials.new(nm); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(GRIETA % n, check_existing=True); t.interpolation = 'Closest'
    bw = nt.nodes.new('ShaderNodeRGBToBW')
    rp = nt.nodes.new('ShaderNodeValToRGB')
    rp.color_ramp.elements[0].position = 0.2; rp.color_ramp.elements[0].color = (0.020, 0.011, 0.004, 1)     # corteza oscura del roble
    rp.color_ramp.elements[1].position = 0.65; rp.color_ramp.elements[1].color = (0.075, 0.044, 0.016, 1)    # veta mas clara
    b = nt.nodes.new('ShaderNodeBsdfPrincipled'); o = nt.nodes.new('ShaderNodeOutputMaterial')
    b.inputs['Roughness'].default_value = 1.0
    nt.links.new(t.outputs['Color'], bw.inputs['Color']); nt.links.new(bw.outputs['Val'], rp.inputs['Fac'])
    nt.links.new(rp.outputs['Color'], b.inputs['Base Color']); nt.links.new(t.outputs['Alpha'], b.inputs['Alpha']); nt.links.new(b.outputs['BSDF'], o.inputs['Surface'])
    for a, v in (('blend_method', 'HASHED'), ('surface_render_method', 'DITHERED')):
        try:
            setattr(m, a, v)
        except Exception:
            pass
    return m


def _malla_cubo(nombre, lado):
    """cubo con UV 0..1 en cada cara (las texturas destroy_stage_N cubren la cara entera)"""
    me = bpy.data.meshes.new(nombre)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=lado); bm.to_mesh(me); bm.free()
    uv = me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        n = p.normal; ax_ = max(range(3), key=lambda i: abs(n[i]))
        a, b = [i for i in range(3) if i != ax_]
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (co[a] / lado + 0.5, co[b] / lado + 0.5)
    return me


def _astillas(f0, origen, vel_base, n, log, col, rnd, escala=0.12, dur_vis=70, f_ocultar=None):
    """n astillas (cubitos de la textura del tronco) lanzadas con velocidad vel_base (m/f) mas dispersion; gravedad real, rebote en el suelo y rozamiento"""
    out = []
    for i in range(n):
        o = bpy.data.objects.new('arb_astilla', log); col.objects.link(o); o.scale = (escala,) * 3
        p = Vector(origen)
        v = Vector(vel_base) + Vector((rnd.uniform(-0.035, 0.035), rnd.uniform(-0.05, 0.05), rnd.uniform(0.0, 0.07)))
        w = Vector((rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4)))
        rot = Vector((0, 0, 0))
        _vis(o, 1, True)
        _vis(o, f0, False)
        f = f0
        for _ in range(dur_vis):
            o.location = p; o.rotation_euler = rot
            o.keyframe_insert('location', frame=f); o.keyframe_insert('rotation_euler', frame=f)
            f += 1; v.z -= G_F; p = p + v; rot = rot + w
            if p.z <= SUELO_Z and v.z < 0:
                p.z = SUELO_Z
                v = Vector((v.x * 0.6, v.y * 0.6, 0.0 if abs(v.z) < 0.03 else -v.z * 0.35)); w = w * 0.6
        _vis(o, f + 20, True)
        out.append(o)
    return out


def _progreso(h, rompe, swing=16):
    """progreso de ruptura (0..1) por fotograma: sube linealmente durante cada rafaga de hachazos (el golpe i deja i+1 partes de n) y se mantiene entre rafagas.
    Devuelve {frame: progreso}"""
    n = len(h) if rompe else len(h) / 0.7                      # T1 se completa en su ultimo hachazo; T2 se queda al ~70 %
    pts = [(h[0] - swing, 0.0)]
    for i, f in enumerate(h):
        if f - h[i - 1] > 2 * swing if i else False:           # hay pausa: el progreso se mantiene hasta el inicio del siguiente swing
            pts.append((f - swing, pts[-1][1]))
        pts.append((f, (i + 1) / n))
    prog = {}
    for (f0, p0), (f1, p1) in zip(pts, pts[1:]):
        for f in range(f0, f1 + 1):
            prog[f] = p0 + (p1 - p0) * (f - f0) / max(1, f1 - f0)
    return prog


def _grietas(k, h, rompe, centro, col, sc):
    """un cubo de grieta por destroy_stage (0..9) que se muestra cuando el progreso continuo cae en ese tramo"""
    prog = _progreso(h, rompe)
    f_ini = min(prog); f_fin = max(prog)
    stg = {f: min(9, int(p * 10)) for f, p in prog.items()}
    fin_vis = f_fin if rompe else sc.frame_end + 5            # al romperse el bloque desaparece la grieta
    objs = []
    for st in sorted(set(stg.values())):
        me = _malla_cubo('arb_grieta_%d_%s' % (st, k), 1.006)
        me.materials.append(_mat_grieta(st))
        o = bpy.data.objects.new('arb%s_grieta_%d' % (k, st), me); col.objects.link(o); o.location = centro
        _vis(o, 1, True)
        prev = False
        for f in range(f_ini, f_fin + 1):
            on = stg[f] == st
            if on != prev:
                _vis(o, f, not on); prev = on
        if prev:
            _vis(o, fin_vis, True)
        objs.append(o)
    return objs


POP = RUT + r"\sonidos\vanilla\random\pop.ogg"
ESC_ITEM = 0.25                                   # skill bloque-roto-drop: el item mide 0.25 del bloque


def _limpiar_anim(o):
    ad = o.animation_data
    if ad and ad.action:
        bpy.data.actions.remove(ad.action)
    o.animation_data_clear()


def item_roto(it, fr, centro, celda_bloque, vx=0.05, vy=0.01, quien='alfred', hueso='Spine1_alfred', arm_nombre='Armature'):
    """skill bloque-roto-drop: el bloque roto (frame fr) suelta un item de escala 0.25 que salta (vz 0.083 m/f), cae con gravedad real, se posa, gira 2.39 grados/f en Z y
    flota entre 0 y 0.2 m (periodo 75 f). >= 12 f tras la rotura y con el personaje a < 1 m, vuela ~5 f (ease-in, escala 0.25->0) a su pecho y se oculta; suena 'pop' al llegar.
    El item cae al suelo (SUELO_Z) salvo sobre la columna del tronco de debajo (celda_bloque), donde el suelo es SUELO_Z + 1."""
    sc = bpy.context.scene
    _limpiar_anim(it)
    alf = bpy.data.objects[quien]; arm = bpy.data.objects[arm_nombre]
    it.rotation_mode = 'XYZ'; it.rotation_euler = (0, 0, 0)
    bx, by = celda_bloque
    suelo = lambda x, y: SUELO_Z + 1.0 if (bx <= x <= bx + 1 and by <= y <= by + 1) else SUELO_Z
    w = math.radians(2.39); fase_giro = random.Random(7).uniform(0, 2 * math.pi)
    p = Vector((centro.x, centro.y, centro.z - 0.5 * ESC_ITEM)); v = Vector((vx, vy, 0.083))        # el origen del bloque esta en su base
    _vis(it, fr - 1, True); _vis(it, fr, False)
    t_posado = None; f = fr; absorbido = False
    while f < fr + 400 and not absorbido:
        it.scale = (ESC_ITEM,) * 3
        it.rotation_euler = (0, 0, fase_giro + w * (f - fr))
        if t_posado is None:
            it.location = p
        else:
            t = f - t_posado
            p.x += v.x; p.y += v.y; v.x *= 0.85; v.y *= 0.85                                           # se frena por friccion
            it.location = (p.x, p.y, suelo(p.x, p.y) + 0.1 + 0.1 * math.sin(2 * math.pi * t / 75.0 - math.pi / 2))
        it.keyframe_insert('location', frame=f); it.keyframe_insert('rotation_euler', frame=f); it.keyframe_insert('scale', frame=f)
        # absorcion
        if t_posado is not None and f >= fr + 12 and f - t_posado >= 12:
            sc.frame_set(f)
            pecho = arm.matrix_world @ arm.pose.bones[hueso].head
            if (Vector(it.location).xy - alf.matrix_world.translation.xy).length < 1.0:
                p0 = Vector(it.location); rz = it.rotation_euler.z
                for j in range(1, 6):
                    s = j / 5.0
                    sc.frame_set(f + j)
                    pecho = arm.matrix_world @ arm.pose.bones[hueso].head
                    it.location = p0.lerp(pecho, s * s)
                    it.rotation_euler = (0, 0, rz + w * j)
                    it.scale = (ESC_ITEM * (1 - s),) * 3
                    it.keyframe_insert('location', frame=f + j); it.keyframe_insert('rotation_euler', frame=f + j); it.keyframe_insert('scale', frame=f + j)
                _vis(it, f + 5, True)
                absorbido = True
                f_llega = f + 5
                break
        # fisica
        if t_posado is None:
            v.z -= G_F; p = p + v
            g = suelo(p.x, p.y)
            if p.z <= g and v.z < 0:
                p.z = g
                if abs(v.z) < 0.03:
                    t_posado = f + 1; v.z = 0.0; v.x *= 0.6; v.y *= 0.6
                else:
                    v = Vector((v.x * 0.6, v.y * 0.6, -v.z * 0.2))
        f += 1
    if absorbido:
        try:
            se = sc.sequence_editor or sc.sequence_editor_create()
            ch = 1
            while any(s.channel == ch for s in se.strips_all):
                ch += 1
            se.strips.new_sound('pop_item', POP, ch, f_llega)
        except Exception as e:
            print('pop no puesto', e)
    return f_llega if absorbido else None


def talar_arboles(G=None):
    sc = bpy.context.scene
    G = G or json.loads(sc['bm_G'])
    rnd = random.Random(5)
    res = construir()
    log, hoja = res.pop('_mallas')
    col = _coleccion()
    nuevos = []
    # hachazos de cada arbol (frames en que cae el hacha sobre el bloque)
    golpes = {'T1': list(G['choques1']) + list(G['choques2']) + list(G['choques3']), 'T2': list(G['choques4'])}
    rompe = {'T1': True, 'T2': False}                          # T1 se rompe con su ultimo hachazo; a T2 lo interrumpen los bonobos
    for k in ('T1', 'T2'):
        cx, cy, cz = GOLPEA[k]
        blk = next(o for o in res[k]['log'] if (round(o.location.x - 0.5), round(o.location.y - 0.5), round(o.location.z)) == (cx, cy, cz))
        centro = Vector((cx + 0.5, cy + 0.5, cz + 0.5))
        h = golpes[k]
        # cara que mira a Alfred (la del este en los dos arboles: Alfred talla de cara al oeste)
        cara = Vector((1, 0, 0))
        ov = _grietas(k, h, rompe[k], centro, col, sc)
        # astillas en cada hachazo
        for i, f in enumerate(h):
            if rompe[k] and i == len(h) - 1:
                continue
            nuevos += _astillas(f, centro + cara * 0.5, cara * 0.07, 4, log, col, rnd, 0.09)
        nuevos += ov
        if not rompe[k]:
            continue
        # --- ruptura del ultimo hachazo
        fr = h[-1]
        _vis(blk, 1, False); _vis(blk, fr, True)
        nuevos += _astillas(fr, centro + cara * 0.4, cara * 0.08, 10, log, col, rnd, 0.12)
        # item del tronco que suelta el bloque: salta, cae y rebota
        it = bpy.data.objects.new('arb_item_tronco', log); col.objects.link(it)
        item_roto(it, fr, centro, (cx, cy))
        nuevos.append(it)
    _constante(nuevos + [o for k in ('T1', 'T2') for o in res[k]['log'] + res[k]['hoja']])
    sc['arb_listo'] = 'ok'
    return res
