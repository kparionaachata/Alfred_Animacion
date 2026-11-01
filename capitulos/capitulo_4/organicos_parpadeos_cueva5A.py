# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: filtros organicos y parpadeos de Alfred y de Jerry (mismas formulas y valores que alfred_organicos_parpadeos_cueva3.py y
ring/filtros_organicos_jerry.py), del frame 1 al final de la escena (se mantienen tambien mientras la camara los graba quietos al final).
 - Alfred: respiracion en Spine/Spine1 (X y Z, amp 0.040, vel 0.020, fase 1.97), micro-movimiento de cabeza Neck/face (amp 0.023, vel 0.079, semilla 693),
   micro-escala Z de Spine1 (0.010).
 - Jerry: respiracion de spine_1 (amp 0.05, vel 0.01) + micro-movimiento (0.008, 0.05, semilla 42) + escala Z (0.005), hombros (0.006, 0.07, semilla 123),
   orejas en Z (0.12, vel 0.06) y cola tail_2 en Z (0.524 x 0.35, vel 0.12) cuando esta quieto (desde COLA_JERRY).
 Se SUMAN por frame (claves LINEAR) a lo que ya anima cada canal; los deltas se guardan en organicos_cueva5A_<personaje>.json y se restan antes de volver a
 aplicar (repetible). Si se regenera la animacion de un personaje: aplicar(quitar=True) antes y aplicar() despues.
 - Parpadeos de 9 frames cada 80-140 f con la forma `Closed`: Alfred en la pista base de sus ojos (esquivando su voz), Jerry en los 4 (ojos y pupilas).
Uso en Blender: exec(open(ruta, encoding="utf8").read()); aplicar()    /    aplicar(quitar=True)
"""
import bpy, math, random, json, os

CARPETA = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/"
SEQ = (0.0, 0.25, 0.5, 0.75, 1.0, 1.0, 0.75, 0.5, 0.25)
AMP_ALFRED = 0.5                       # oscilaciones de Alfred a la mitad (pedido del usuario)
COLA_JERRY = 323                       # desde aqui (ya dejo el pico) mueve la cola


def ss(x):
    return 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))


def _ruido(f, freq, seed, dim=0):
    v = math.sin(f * freq * 1.3 + seed * 7.3 + dim * 3.7) + math.sin(f * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5 + math.sin(f * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25
    return v / 1.75


def _fcs(idb):
    a = idb.animation_data.action
    return [fc for lay in a.layers for st in lay.strips for cb in st.channelbags for fc in cb.fcurves]


def _buscar(idb, dp, axis):
    return next((fc for fc in _fcs(idb) if fc.data_path == dp and fc.array_index == axis), None)


def _deltas_alfred(fr):
    D = {}

    def suma(bone, tipo, axis, vals):
        D[('pose.bones["%s"].%s' % (bone, tipo), axis)] = list(vals)
    for bone, k in (("Spine_alfred", 0.6), ("Spine1_alfred", 1.0)):
        r = [AMP_ALFRED * 0.040 * k * math.sin(2 * math.pi * 0.020 * f + 1.97) for f in fr]
        suma(bone, "rotation_euler", 0, r)
        suma(bone, "rotation_euler", 2, [0.35 * v for v in r])
    for bone, k in (("Neck_alfred", 0.6), ("face_alfred", 0.4)):
        for ax in (0, 2):
            suma(bone, "rotation_euler", ax, [AMP_ALFRED * 0.023 * k * _ruido(f, 0.079, 693, ax) for f in fr])
    suma("Spine1_alfred", "scale", 2, [AMP_ALFRED * 0.010 * math.sin(2 * math.pi * 0.020 * f + 1.97) for f in fr])
    return D


def _deltas_jerry(fr):
    D = {}

    def suma(bone, tipo, axis, vals):
        k = ('pose.bones["%s"].%s' % (bone, tipo), axis)
        D[k] = [a + b for a, b in zip(D[k], vals)] if k in D else list(vals)
    suma("spine_1", "rotation_euler", 0, [0.05 * math.sin(f * 0.01 * 2 * math.pi) for f in fr])
    suma("spine_1", "rotation_euler", 2, [0.05 * 0.4 * math.sin(f * 0.01 * 2 * math.pi + 1.2) for f in fr])
    for ax in range(3):
        suma("spine_1", "rotation_euler", ax, [0.008 * _ruido(f, 0.05, 42, ax) for f in fr])
    suma("spine_1", "scale", 2, [0.005 * math.sin(f * 0.01 * 2 * math.pi) for f in fr])
    for ax in range(3):
        for b, off in (("front_shoulder.R", 0), ("front_shoulder.L", 17)):
            suma(b, "rotation_euler", ax, [0.006 * _ruido(f, 0.07, 123 + off, ax) for f in fr])
    for b, fase in (("ear.L", 0.0), ("ear.R", 1.57)):
        suma(b, "rotation_euler", 2, [0.12 * math.sin(f * 0.06 * 2 * math.pi + fase) for f in fr])
    suma("tail_2", "rotation_euler", 2, [0.524 * 0.35 * ss((f - (COLA_JERRY - 6)) / 6.0) * math.sin(f * 0.12 * 2 * math.pi) for f in fr])
    return D


def _organicos(arm, D, ruta_json, quitar):
    sc = bpy.context.scene
    FIN = sc.frame_end
    fr = range(1, FIN + 1)
    prev = json.load(open(ruta_json, encoding="utf-8")) if os.path.exists(ruta_json) else {}
    if quitar:
        D = {}
    for clave in prev:                                           # canales de antes que ya no se usan -> delta 0 (para restarlos)
        dp, ax = clave.rsplit(":", 1)
        D.setdefault((dp, int(ax)), [0.0] * len(fr))
    nuevo = {}
    for (dp, axis), deltas in D.items():
        fc = _buscar(arm, dp, axis)
        if fc is None:
            bag = arm.animation_data.action.layers[0].strips[0].channelbags[0]
            fc = bag.fcurves.new(dp, index=axis)
        p = prev.get("%s:%d" % (dp, axis), {})
        estatico = 1.0 if dp.endswith("scale") else 0.0
        base = [(fc.evaluate(f) if len(fc.keyframe_points) else estatico) - p.get(str(f), 0.0) for f in fr]
        kp = fc.keyframe_points
        for i in range(len(kp) - 1, -1, -1):
            if kp[i].co.x >= 1:                              # tambien las que pasan del final actual
                kp.remove(kp[i], fast=True)
        kp.add(len(fr))
        kp.foreach_set("co", [x for f, b, d in zip(fr, base, deltas) for x in (f, b + d)])
        for k in kp:
            k.interpolation = 'LINEAR'
        fc.update()
        if any(deltas):
            nuevo["%s:%d" % (dp, axis)] = {str(f): d for f, d in zip(fr, deltas)}
    json.dump(nuevo, open(ruta_json, "w", encoding="utf-8"))
    return len(nuevo)


def _centros(rnd, inicio, fin, evitar):
    out, f = [], inicio + rnd.randint(20, 40)
    while f + 9 <= fin:
        if any(a - 12 <= f <= b + 3 for a, b in evitar):
            f += 6
            continue
        out.append(f)
        f += rnd.randint(80, 140)
    return out


def _parpadeos_alfred(quitar):
    sc = bpy.context.scene
    ed = sc.sequence_editor
    voces = [(s.frame_final_start, s.frame_final_end) for s in ed.strips_all if s.name.startswith("VozAlfred_")] if ed else []
    centros = [] if quitar else _centros(random.Random(31), 1, sc.frame_end, voces)
    for n in ("ojo_izquierdo_alfred", "ojo_derecho_alfred"):
        key = bpy.data.objects[n].data.shape_keys
        tr = key.animation_data.nla_tracks.get("VozOjosBase_formas_" + n)
        st = tr.strips[0]
        a = st.action
        fc = next((x for lay in a.layers for s2 in lay.strips for cb in s2.channelbags for x in cb.fcurves if x.data_path == 'key_blocks["Closed"].value'), None)
        if fc is None:
            fc = a.layers[0].strips[0].channelbags[0].fcurves.new('key_blocks["Closed"].value', index=0)
        for i in range(len(fc.keyframe_points) - 1, -1, -1):
            fc.keyframe_points.remove(fc.keyframe_points[i])
        fc.keyframe_points.insert(1, 0.0)
        for c in centros:
            for k, v in enumerate(SEQ):
                fc.keyframe_points.insert(c + k, v, options={'FAST'}).interpolation = 'LINEAR'
            fc.keyframe_points.insert(c + 9, 0.0, options={'FAST'})
        fc.keyframe_points.insert(sc.frame_end, 0.0, options={'FAST'})
        fc.update()
        st.action_frame_end = sc.frame_end
        st.frame_end = sc.frame_end
    return centros


def _parpadeos_jerry(quitar):
    sc = bpy.context.scene
    ed = sc.sequence_editor
    voces = [(s.frame_final_start, s.frame_final_end + 6) for s in ed.strips_all if s.name.startswith("VozJerry_")] if ed else []
    centros = [] if quitar else _centros(random.Random(23), 1, sc.frame_end, voces)
    for n in ("ojo_izquierdo_jerry", "ojo_derecho_jerry", "pupila_izquierda_jerry", "pupila_derecha_jerry"):
        key = bpy.data.objects[n].data.shape_keys
        if key.animation_data and key.animation_data.action:
            for fc in [x for lay in key.animation_data.action.layers for s in lay.strips for cb in s.channelbags for x in cb.fcurves if x.data_path == 'key_blocks["Closed"].value']:
                for i in range(len(fc.keyframe_points) - 1, -1, -1):
                    fc.keyframe_points.remove(fc.keyframe_points[i])
        kb = key.key_blocks["Closed"]
        kb.value = 0.0
        if quitar:
            continue
        kb.keyframe_insert("value", frame=1)
        for c in centros:
            for k, v in enumerate(SEQ + (0.0,)):
                kb.value = v
                kb.keyframe_insert("value", frame=c + k)
        kb.value = 0.0
        kb.keyframe_insert("value", frame=sc.frame_end)
        for fc in [x for lay in key.animation_data.action.layers for s in lay.strips for cb in s.channelbags for x in cb.fcurves]:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    return centros


def aplicar(quitar=False):
    O = bpy.data.objects
    fr = range(1, bpy.context.scene.frame_end + 1)
    res = {}
    res["alfred_canales"] = _organicos(O["Armature"], _deltas_alfred(fr), CARPETA + "organicos_cueva5A_alfred.json", quitar)
    res["jerry_canales"] = _organicos(O["Dog_001_rig"], _deltas_jerry(fr), CARPETA + "organicos_cueva5A_jerry.json", quitar)
    res["parpadeos_alfred"] = _parpadeos_alfred(quitar)
    res["parpadeos_jerry"] = _parpadeos_jerry(quitar)
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    return res
