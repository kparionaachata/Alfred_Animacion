# -*- coding: utf-8 -*-
"""Crea la base de la parte 7: el estado del frame 1265 de la parte 6 fijado como frame 1, sin animaciones (mismo metodo que base_parte_2 / base_parte_5).
Se ejecuta en segundo plano sobre una COPIA y guarda un archivo NUEVO (no toca el original):
    blender --background --disable-autoexec <base_parte_7.blend> --python crear_base_parte_7.py -- <salida.blend> [frame=1265]
Pasos: (1) corrige el driver de la cabeza del creeper que dependia del fotograma (`or frame<1035`); (2) lee los valores de todos los canales animados en el frame;
(3) borra acciones y NLA de objetos, shape keys, camaras, materiales y sus node trees (los drivers se conservan); (4) escribe los valores como fijos;
(5) elimina las tiras del secuenciador (voces y sonidos de la parte 6); (6) deja la escena en el frame 1 y verifica que f1 y f600 son identicos al estado original del frame."""
import bpy, sys

args = sys.argv[sys.argv.index('--') + 1:]
SALIDA = args[0]; FRAME = int(args[1]) if len(args) > 1 else 1265
sc = bpy.context.scene; vl = bpy.context.view_layer


def snap():
    vl.update(); d = {}
    for o in bpy.data.objects:
        d['M:' + o.name] = [round(v, 4) for r in o.matrix_world for v in r]
        d['H:' + o.name] = (o.hide_viewport, o.hide_render)
        for c in o.constraints: d['C:%s:%s' % (o.name, c.name)] = round(c.influence, 4)
        if o.type == 'ARMATURE':
            for pb in o.pose.bones:
                d['B:%s:%s' % (o.name, pb.name)] = [round(v, 4) for r in pb.matrix for v in r]
                for k in pb.keys():
                    try: d['P:%s:%s:%s' % (o.name, pb.name, k)] = round(float(pb[k]), 4)
                    except Exception: pass
        if o.type == 'CAMERA': d['L:' + o.name] = round(o.data.lens, 4)
    for sk in bpy.data.shape_keys:
        for kb in sk.key_blocks: d['K:%s:%s' % (sk.name, kb.name)] = round(kb.value, 4)
    return d


def cmp(a, b):
    mx = 0.0; mal = []
    for k, v in a.items():
        w = b.get(k)
        if w is None: mal.append(k); continue
        if isinstance(v, list): dif = max(abs(x - y) for x, y in zip(v, w)) if len(v) == len(w) else 99
        elif isinstance(v, tuple): dif = 0 if v == w else 1
        else: dif = abs(v - w)
        if dif > 1e-3: mal.append((k, round(dif, 4)))
        mx = max(mx, float(dif))
    return mx, mal


def idbags(ad):
    out = []
    for l in ad.action.layers:
        for s in l.strips:
            for cb in s.channelbags:
                if getattr(cb, 'slot', None) is None or ad.action_slot is None or cb.slot == ad.action_slot: out.append(cb)
    return out


def locate(idb, dp):
    if dp.endswith(']'):
        i = dp.rindex('['); key = eval(dp[i + 1:-1]); op = dp[:i]
        return (idb.path_resolve(op) if op else idb), 'c', key
    op, _, prop = dp.rpartition('.')
    return (idb.path_resolve(op) if op else idb), 'a', prop


# 1) driver dependiente del fotograma
head = bpy.data.objects.get('creeper.head.sadb_creeper_1')
if head and head.animation_data:
    for dr in head.animation_data.drivers:
        if 'frame' in dr.driver.expression: dr.driver.expression = dr.driver.expression.replace(' or frame<1035', '')

sc.frame_set(FRAME); vl.update(); antes = snap()

# 2) capturar
ids = list(bpy.data.objects) + list(bpy.data.shape_keys) + list(bpy.data.cameras) + list(bpy.data.node_groups)
for m in bpy.data.materials:
    ids.append(m)
    if m.node_tree: ids.append(m.node_tree)
vals = []; fallos = []
for idb in ids:
    ad = getattr(idb, 'animation_data', None)
    if not ad or not ad.action: continue
    for cb in idbags(ad):
        for fc in cb.fcurves:
            try:
                owner, kind, key = locate(idb, fc.data_path)
                v = owner[key] if kind == 'c' else getattr(owner, key)
                if fc.array_index >= 0 and hasattr(v, '__len__') and not isinstance(v, str): v = v[fc.array_index]
                vals.append((idb, fc.data_path, fc.array_index, v if isinstance(v, bool) else float(v)))
            except Exception as e: fallos.append((idb.name, fc.data_path, str(e)[:60]))
print('CANALES', len(vals), 'FALLOS_LECTURA', len(fallos), fallos[:5])

# 3) borrar acciones y NLA
n_ad = 0
for idb in ids + [sc]:
    ad = getattr(idb, 'animation_data', None)
    if not ad: continue
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    if ad.action: ad.action = None; n_ad += 1
acc = [a for a in bpy.data.actions if a.users == 0 and not a.use_fake_user]
for a in acc: bpy.data.actions.remove(a)
print('DESANIMADOS', n_ad, 'ACCIONES_BORRADAS', len(acc), 'QUEDAN', len(bpy.data.actions))

# 4) escribir fijos
for idb, dp, idx, v in vals:
    try:
        owner, kind, key = locate(idb, dp)
        if kind == 'c':
            cur = owner[key]
            if idx >= 0 and hasattr(cur, '__len__'):
                lst = list(cur); lst[idx] = v; owner[key] = lst
            else: owner[key] = v
        else:
            cur = getattr(owner, key)
            if idx >= 0 and hasattr(cur, '__len__') and not isinstance(cur, str): cur[idx] = v
            else: setattr(owner, key, v)
    except Exception as e: fallos.append(('escritura', idb.name, dp, str(e)[:50]))

# 5) secuenciador
se = sc.sequence_editor; n = 0
if se:
    while len(se.strips_all):
        s = se.strips_all[0]; (s.parent_meta().strips if s.parent_meta() else se.strips).remove(s); n += 1
print('TIRAS_ELIMINADAS', n)

# 6) verificar y guardar
sc.frame_set(1); des1 = snap(); sc.frame_set(600); des600 = snap(); sc.frame_set(1)
for nom, d in (('f1', des1), ('f600', des600)):
    mx, mal = cmp(antes, d); print('VERIF', nom, 'comparados', len(antes), 'max_dif', round(mx, 5), 'distintos', len(mal), mal[:8])
print('FALLOS', len(fallos), fallos[:6], '| rango', sc.frame_start, sc.frame_end, 'actual', sc.frame_current)
bpy.ops.wm.save_as_mainfile(filepath=SALIDA, copy=True)
print('GUARDADO', SALIDA)
