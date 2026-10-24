# -*- coding: utf-8 -*-
"""alfred_cueva_3.blend: filtros organicos y parpadeos de Alfred (mismas formulas y valores que filtros_organicos_y_parpadeos.py / estudio de Alfred):
 - respiracion en Spine/Spine1 (X y Z, amp 0.040, vel 0.020, fase 1.97), micro-movimiento de cabeza Neck/face (amp 0.023, vel 0.079, semilla 693),
   micro-escala Z de Spine1 (0.010); se SUMAN a las claves por frame de la accion de la armature (no se suaviza nada).
 - parpadeos de 9 frames cada 80-140 f (semilla fija) con la forma `Closed` de los dos ojos, en la pista base de los ojos (las voces los tapan en
   sus tramos) y saltando las ventanas con voz; no parpadea despues de que le cae la estalactita (inconsciente).
Repetible: guarda los deltas en la propiedad `organicos_cueva3` de la armature y los resta antes de volver a aplicar.
Uso: exec(open(ruta, encoding="utf8").read()); construir()
"""
import bpy, math, random, json

AMP_R, VEL_R, FASE_R = 0.040, 0.020, 1.97
AMP_M, VEL_M, SEM_M = 0.023, 0.079, 693
ESC = 0.010
SECUENCIA = (0, .25, .5, .75, 1, 1, .75, .5, .25)
F_FIN_PARPADEO = 329                       # le cae la estalactita en el 330


def _ruido(f, freq, seed, dim=0):
    v = math.sin(f * freq * 1.3 + seed * 7.3 + dim * 3.7) + math.sin(f * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5 + math.sin(f * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25
    return v / 1.75


def _fcs(a):
    return [fc for lay in a.layers for st in lay.strips for cb in st.channelbags for fc in cb.fcurves]


def organicos():
    sc = bpy.context.scene; arm = bpy.data.objects["Armature"]; act = arm.animation_data.action
    prev = json.loads(arm.get("organicos_cueva3", "{}")); nuevo = {}
    def delta(hueso, dp, i, f):
        if hueso in ("Spine_alfred", "Spine1_alfred") and dp == "rotation_euler":
            r = AMP_R * math.sin(2 * math.pi * VEL_R * f + FASE_R) * (0.6 if hueso == "Spine_alfred" else 1.0)
            return r if i == 0 else (0.35 * r if i == 2 else 0.0)
        if hueso in ("Neck_alfred", "face_alfred") and dp == "rotation_euler" and i in (0, 2):
            return AMP_M * _ruido(f, VEL_M, SEM_M, i) * (0.6 if hueso == "Neck_alfred" else 0.4)
        if hueso == "Spine1_alfred" and dp == "scale" and i == 2:
            return ESC * math.sin(2 * math.pi * VEL_R * f + FASE_R)
        return None
    for fc in _fcs(act):
        if '"' not in fc.data_path: continue
        hueso = fc.data_path.split('"')[1]; dp = fc.data_path.split(".")[-1]
        clave = "%s|%s|%d" % (hueso, dp, fc.array_index)
        if delta(hueso, dp, fc.array_index, 1) is None: continue
        viejo = prev.get(clave, {}); d = {}
        for kp in fc.keyframe_points:
            f = int(round(kp.co[0])); v = delta(hueso, dp, fc.array_index, f)
            dv = v - viejo.get(str(f), 0.0)
            kp.co[1] += dv; kp.handle_left[1] += dv; kp.handle_right[1] += dv; d[str(f)] = v
        fc.update(); nuevo[clave] = d
    # Spine1 escala Z (sin claves aun): canal nuevo por frame
    clave = "Spine1_alfred|scale|2"
    if clave not in nuevo:
        cb = act.layers[0].strips[0].channelbags[0]
        fc = cb.fcurves.find('pose.bones["Spine1_alfred"].scale', index=2) or cb.fcurves.new('pose.bones["Spine1_alfred"].scale', index=2)
        for kp in list(fc.keyframe_points): fc.keyframe_points.remove(kp)
        d = {}
        for f in range(1, sc.frame_end + 1):
            v = ESC * math.sin(2 * math.pi * VEL_R * f + FASE_R); kp = fc.keyframe_points.insert(f, 1.0 + v, options={'FAST'}); kp.interpolation = 'LINEAR'; d[str(f)] = v
        fc.update(); nuevo[clave] = d
        for i in (0, 1):
            f2 = cb.fcurves.find('pose.bones["Spine1_alfred"].scale', index=i) or cb.fcurves.new('pose.bones["Spine1_alfred"].scale', index=i)
            if not len(f2.keyframe_points): f2.keyframe_points.insert(1, 1.0)
    arm["organicos_cueva3"] = json.dumps(nuevo)
    return len(nuevo)


def parpadeos():
    sc = bpy.context.scene; ed = sc.sequence_editor
    voces = [(s.frame_final_start - 3, s.frame_final_end + 3) for s in ed.strips_all if s.name.startswith("VozAlfred_")] if ed else []
    rnd = random.Random(31); centros = []; f = rnd.randint(20, 40)
    while f + 9 <= F_FIN_PARPADEO:
        if not any(a <= f + 9 and f <= b for a, b in voces): centros.append(f)
        f += rnd.randint(80, 140)
    # tambien rellena huecos largos sin parpadeo (> 110 f) fuera de las voces
    libres = [(1, F_FIN_PARPADEO)]
    for a, b in sorted(voces):
        libres = [(x, y) for (x, y) in sum([[(x, min(y, a - 1)), (max(x, b + 1), y)] for (x, y) in libres], []) if y - x > 12]
    for x, y in libres:
        if not any(x <= c <= y for c in centros) and y - x > 30: centros.append((x + y) // 2 - 4)
    centros = sorted(set(centros))
    for n in ("ojo_izquierdo_alfred", "ojo_derecho_alfred"):
        key = bpy.data.objects[n].data.shape_keys; ad = key.animation_data
        tr = ad.nla_tracks.get("VozOjosBase_formas_" + n)
        st = tr.strips[0]; a = st.action
        fc = next((x for x in _fcs(a) if x.data_path == 'key_blocks["Closed"].value'), None)
        if fc is None: fc = a.layers[0].strips[0].channelbags[0].fcurves.new('key_blocks["Closed"].value', index=0)
        for kp in list(fc.keyframe_points): fc.keyframe_points.remove(kp)
        fc.keyframe_points.insert(1, 0.0)
        for c in centros:
            for k, v in enumerate(SECUENCIA):
                fc.keyframe_points.insert(c + k, v, options={'FAST'}).interpolation = 'LINEAR'
            fc.keyframe_points.insert(c + 9, 0.0, options={'FAST'})
        fc.keyframe_points.insert(sc.frame_end, 0.0, options={'FAST'})
        fc.update()
        st.action_frame_end = sc.frame_end; st.frame_end = sc.frame_end
    return centros


def construir():
    return {"canales_organicos": organicos(), "parpadeos": parpadeos()}
