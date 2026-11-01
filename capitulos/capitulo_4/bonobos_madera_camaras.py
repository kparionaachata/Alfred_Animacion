# -*- coding: utf-8 -*-
"""Camaras y cortes de 'Alfred tala arboles y los bonobos le tiran cosas'. Lee los frames de eventos de scene['bm_G'] y crea camaras (todas bm_cam_*) con Track To a empties
que siguen a Alfred / a los bonobos, y marcadores de camara en la linea de tiempo. Idempotente (borra y recrea lo suyo). 24 fps.
    exec(open(este_archivo).read()); armar_camaras()"""
import bpy, json, math
from mathutils import Vector

COL = 'bonobos_madera'


def _col():
    c = bpy.data.collections.get(COL) or bpy.data.collections.new(COL)
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c


def _borrar():
    for o in list(bpy.data.objects):
        if o.name.startswith('bm_cam_') or o.name.startswith('bm_foco_'):
            bpy.data.objects.remove(o, do_unlink=True)
    sc = bpy.context.scene
    for m in list(sc.timeline_markers):
        if m.name.startswith('bm_'):
            sc.timeline_markers.remove(m)


def _foco(nombre, objetivo, hueso=None, off=(0, 0, 0)):
    e = bpy.data.objects.new('bm_foco_' + nombre, None)
    e.empty_display_type = 'PLAIN_AXES'; e.empty_display_size = 0.2
    _col().objects.link(e)
    c = e.constraints.new('COPY_LOCATION'); c.target = objetivo
    if hueso:
        c.subtarget = hueso
    e.location = off
    return e


def _cam(nombre, loc, foco, lente=35, loc2=None, f_ini=None, f_fin=None):
    cd = bpy.data.cameras.new('bm_cam_' + nombre)
    cd.lens = lente; cd.clip_start = 0.1; cd.clip_end = 600
    o = bpy.data.objects.new('bm_cam_' + nombre, cd)
    _col().objects.link(o)
    o.location = loc
    t = o.constraints.new('TRACK_TO'); t.target = foco; t.track_axis = 'TRACK_NEGATIVE_Z'; t.up_axis = 'UP_Y'
    if loc2 is not None:
        o.keyframe_insert('location', frame=f_ini)
        o.location = loc2; o.keyframe_insert('location', frame=f_fin)
    return o


def armar_camaras():
    sc = bpy.context.scene
    G = json.loads(sc['bm_G'])
    _borrar()
    arm = bpy.data.objects['Armature']
    focoA = _foco('alfred', arm, 'Spine2_alfred')
    focoC = _foco('cara', arm, 'face_alfred')
    focoB = _foco('brazo', arm, 'Leftelbow_alfred')
    homes = json.loads(sc['bm_homes'])
    bon = {}
    for n in ('A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7'):
        r = bpy.data.objects['bonobo_' + n]
        rig = [o for o in r.children if o.type == 'ARMATURE'][0]
        h = [b.name for b in rig.data.bones if b.name.startswith('head_')][0]
        bon[n] = _foco(n, rig, h)
    grupo = bpy.data.objects.new('bm_foco_copa', None); _col().objects.link(grupo); grupo.location = (-79.5, 33.2, 25.5)
    # --- camaras (posiciones despejadas, buscadas con rayos en la escena: sin troncos ni hojas delante)
    camW = _cam('amplia', (-70.5, 29.0, 14.6), focoA, 26, loc2=(-72.8, 30.4, 14.0), f_ini=1, f_fin=100)
    e1 = {'norte': _cam('n1', (-77.5, 36.1, 13.4), focoA, 36), 'sur': _cam('s1', (-78.0, 30.15, 13.4), focoA, 36), 'frente': _cam('f1', (-80.45, 33.6, 13.4), focoC, 32),
          'este': _cam('e1', (-74.5, 33.1, 13.4), focoA, 34), 'se': _cam('se1', (-75.6, 30.8, 13.4), focoA, 38), 'ne': _cam('ne1', (-75.2, 35.0, 13.4), focoA, 38)}
    e2 = {'norte': _cam('n2', (-77.0, 33.4, 13.4), focoA, 36), 'sur': _cam('s2', (-75.07, 28.1, 14.0), focoA, 36), 'este': _cam('e2', (-74.0, 30.4, 13.4), focoA, 34),
          'frente': _cam('f2', (-78.25, 32.57, 13.0), focoC, 32)}
    camT = _cam('arriba', (-73.0, 33.0, 27.2), grupo, 32)                          # sobre la copa, mirando a los bonobos
    camP = _cam('desde_copa', (-76.5, 37.0, 22.2), focoA, 38)                      # punto de vista de los bonobos
    camL = _cam('suelo', (-77.35, 32.4, 12.9), focoA, 28)                          # a ras de suelo (desmayo)
    camBr = _cam('brazo', (-75.4, 30.4, 13.3), focoB, 50)                          # primer plano de la serpiente
    C1 = Vector((-77.6, 33.2, 13.9))
    def pos_b(n):
        h = Vector(homes['bonobo_' + n]); u = (C1 - h); u.z = 0; u.normalize()
        return h + u * 3.0 + Vector((0, 0, 2.4))
    camB = {n: _cam('bonobo_' + n, pos_b(n), bon[n], 42) for n in bon}
    # --- cortes
    cortes = []                                    # (frame, camara)
    era = lambda f: e1 if f < 990 else e2
    lado = lambda f, k: era(f)[k] if k in era(f) else era(f)['norte']
    cortes += [(1, camW), (73, e1['sur'])]
    ev = [(G['manzana_suelta'], 'A1', G['manzana_impacto']), (G['palo1_rel'], 'A2', G['palo1_imp']), (G['palo2_rel'], 'A3', G['palo2_imp']),
          (G['panal_rel'], 'A5', G['panal_imp']), (G['cacao_rel'], 'A4', G['cacao_imp']), (G['baya_imp'] - 24, 'A2', G['baya_imp']),
          (G['baya2_imp'] - 24, 'A4', G['baya2_imp']), (G['serpiente_rel'], 'A7', G['serpiente_imp'])]
    ocupado = []
    for rel, b, imp in ev:
        cortes.append((rel - 14, camB[b]))
        cortes.append((rel + 8, lado(rel, 'este')))
        cortes.append((imp - 6, lado(imp, 'norte')))
        cortes.append((imp + 26, lado(imp, 'frente')))
        ocupado.append((rel - 20, imp + 40))
    for rel, tag in ((G['silex_rel'], 'A1'), (G['rata_rel'], 'A3'), (G['pollo_rel'], 'A5')):
        cortes.append((rel - 20, lado(rel, 'sur'))); cortes.append((rel + 4, lado(rel, 'este'))); cortes.append((rel + 30, lado(rel, 'norte')))
        ocupado.append((rel - 22, rel + 50))
    ciclo = ['norte', 'sur', 'frente', 'este', 'se', 'ne']
    k = 0
    f = 129
    while f < G['fin'] - 60:
        if not any(a <= f <= b for a, b in ocupado):
            cortes.append((f, lado(f, ciclo[k % len(ciclo)]))); k += 1
        f += 64
    cortes += [(G['serpiente_imp'] + 26, camBr), (G['serpiente_imp'] + 60, e2['frente']), (G['mareo_ini'] - 20, e2['sur']), (G['rodillas'] - 30, camP),
               (G['rodillas'] + 14, camL), (G['rodillas'] + 50, e2['norte']), (G['fin'] - 40, camW)]
    cortes = sorted(set(cortes), key=lambda x: x[0])
    limpio = []
    for fr, c in cortes:
        if limpio and fr - limpio[-1][0] < 14:
            continue
        if limpio and limpio[-1][1] == c:
            continue
        limpio.append((fr, c))
    for fr, c in limpio:
        m = sc.timeline_markers.new('bm_' + c.name[7:], frame=int(fr))
        m.camera = c
    sc.camera = limpio[0][1]
    return limpio
