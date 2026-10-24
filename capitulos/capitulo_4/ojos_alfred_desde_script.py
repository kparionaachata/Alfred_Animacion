# -*- coding: utf-8 -*-
"""Aplica un `animacion_alfred (N).py` de la app estudio_audio_expresion (ojos de Alfred) SIN ejecutarlo (el script borra la animacion de los
ojos y pone claves desde el frame 1): reproduce sus valores como pistas NLA REPLACE desde F0 en cada ojo (transform) y en sus shape keys
(formas), con una shape key nueva `Voz_<etiqueta>` con las coordenadas del script. Tambien pone el audio en el VSE en F0.
Uso: exec(open(ruta, encoding="utf8").read()); aplicar(script, audio, f0, etiqueta)
"""
import bpy, math, os, shutil

FASES = ((0.00, 0.00), (0.12, 0.00), (0.28, 0.70), (0.42, 1.08), (0.57, 0.92), (0.72, 1.02), (0.86, 0.48), (1.00, 0.00))
OJOS = ("ojo_izquierdo_alfred", "ojo_derecho_alfred")


def _peso(f, fin):
    p = (f - 1) / max(1, fin - 1)
    for (a, va), (b, vb) in zip(FASES, FASES[1:]):
        if a <= p <= b: return va + (vb - va) * (p - a) / max(1e-6, b - a)
    return 0.0


def _accion(idb, nombre, canales, f0):
    ad = idb.animation_data or idb.animation_data_create()
    for t in list(ad.nla_tracks):
        if t.name == nombre: ad.nla_tracks.remove(t)
    a = bpy.data.actions.get(nombre)
    if a: bpy.data.actions.remove(a)
    a = bpy.data.actions.new(nombre); sl = a.slots.new(idb.id_type, idb.name)
    cb = a.layers.new("L").strips.new(type='KEYFRAME').channelbags.new(sl)
    for (dp, i), cl in canales.items():
        fc = cb.fcurves.new(dp, index=i); fc.keyframe_points.add(len(cl))
        for kp, (f, v) in zip(fc.keyframe_points, cl): kp.co = (f, v); kp.interpolation = 'BEZIER'
        fc.update()
    tr = ad.nla_tracks.new(); tr.name = nombre
    st = tr.strips.new(nombre, f0, a); st.blend_type = 'REPLACE'; st.extrapolation = 'NOTHING'
    try: st.action_slot = sl
    except Exception: pass


def _base(idb, nombre, valores):
    """pista REPLACE + HOLD en el fondo con los valores normales (sin ella, fuera de las tiras el NLA deja los canales en 0/1)."""
    ad = idb.animation_data or idb.animation_data_create()
    previa = ad.nla_tracks.get(nombre)
    a = bpy.data.actions.get(nombre)
    if previa:
        cb = a.layers[0].strips[0].channelbags[0]
        for (dp, i), v in valores.items():
            if not cb.fcurves.find(dp, index=i):
                fc = cb.fcurves.new(dp, index=i); fc.keyframe_points.insert(1, v)
        return
    if a: bpy.data.actions.remove(a)
    a = bpy.data.actions.new(nombre); sl = a.slots.new(idb.id_type, idb.name)
    cb = a.layers.new("L").strips.new(type='KEYFRAME').channelbags.new(sl)
    for (dp, i), v in valores.items():
        fc = cb.fcurves.new(dp, index=i); fc.keyframe_points.insert(1, v)
    tr = ad.nla_tracks.new(); tr.name = nombre        # queda al fondo: la pista de la voz se rehace despues, encima
    st = tr.strips.new(nombre, 1, a); st.blend_type = 'REPLACE'; st.extrapolation = 'HOLD'
    try: st.action_slot = sl
    except Exception: pass


def aplicar(script, audio, f0, etiqueta):
    ns = {}; exec(open(script, encoding="utf8").read().split("eye_system = ")[0].replace("import bpy", "").replace("import importlib", ""), ns)
    fin = ns["END_FRAME"]; habla = {int(f): float(v) for f, v in ns["SPEECH_CURVE"]}; clave = ("Voz_" + etiqueta)[:56]
    sc = bpy.context.scene; f_act = sc.frame_current; sc.frame_set(f0 - 1)
    for ei, (nombre, coords) in enumerate(ns["COORDINATES"].items()):
        ojo = bpy.data.objects[nombre]; bl = ojo.data.shape_keys.key_blocks
        if len(coords) != len(ojo.data.vertices): raise RuntimeError("topologia distinta en " + nombre)
        sk = bl.get(clave) or ojo.shape_key_add(name=clave, from_mix=False)
        sk.slider_min, sk.slider_max = -2, 2
        for i, c in enumerate(coords): sk.data[i].co = c
        L, S, Rz = ojo.location.copy(), ojo.scale.copy(), ojo.rotation_euler.copy()
        lado = 1.0 if L.x > 0 else -1.0; amt = 1.0 if ei == 0 else 0.86
        ct = {}; cf = {}; prev = 0.0
        for f in range(1, fin + 1):
            w = _peso(f, fin); s = habla.get(f, 0.0); at = max(0.0, s - prev); wave = math.sin(f * 1.34 + ei * 0.16); st = wave * s
            x = L.x + lado * ns["LATERAL"] * w * (1.0 if ei == 0 else -0.55)
            z = L.z + ns["VERTICAL"] * w * (1.0 if f < fin * 0.6 else 0.65) + ns["SPEECH_VERTICAL"] * s * wave * amt
            sx = S.x * (1 + (ns["SCALE_X"] - 1) * w * amt) * (1 + ns["SPEECH_SCALE_X"] * s - 0.040 * st)
            sy = S.y * (1 - 0.025 * s)
            sz = S.z * (1 + (ns["SCALE_Z"] - 1) * w * amt) * (1 + ns["SPEECH_SCALE_Z"] * s + 0.065 * st + 0.025 * at)
            if ns.get("GENERATED_EMOTION") == "duda" and nombre == "ojo_izquierdo_alfred":
                d = 1 + (ns.get("DOUBT_LEFT_EYE_SCALE", 1.0) - 1) * w; sx *= d; sy *= d; sz *= d
            ry = Rz.y + lado * ns["ROTATION"] * w * amt + lado * ns["ATTACK_ROTATION"] * at * amt
            ff = f0 - 1 + f
            for dp, i, v in (("location", 0, x), ("location", 1, L.y), ("location", 2, z), ("scale", 0, sx), ("scale", 1, sy), ("scale", 2, sz),
                             ("rotation_euler", 0, Rz.x), ("rotation_euler", 1, ry), ("rotation_euler", 2, Rz.z)):
                ct.setdefault((dp, i), []).append((ff, v))
            for kb in bl:
                if kb.name == "Basis": continue
                v = ns["SHAPE_VALUE"] * w * amt if kb.name == clave else 0.0
                if kb.name == "Closed":
                    v = max([1.0 - min(1.0, abs(f - c) / 2.0) for c in ns.get("BLINK_CENTERS", [])] + [0.0])
                cf.setdefault(('key_blocks["%s"].value' % kb.name, 0), []).append((ff, v))
            prev = s
        _base(ojo, "VozOjosBase_" + nombre, {k: v[0][1] for k, v in ct.items()})                     # fuera del tramo los ojos se quedan como estaban
        _base(ojo.data.shape_keys, "VozOjosBase_formas_" + nombre, {k: v[0][1] for k, v in cf.items()})
        _accion(ojo, "VozOjos_%s_%s_transform" % (etiqueta, nombre), ct, f0)
        _accion(ojo.data.shape_keys, "VozOjos_%s_%s_formas" % (etiqueta, nombre), cf, f0)
    # audio
    dst = os.path.join(r"C:\Users\user\Desktop\Alfred_Animacion\audios\alfred", etiqueta + os.path.splitext(audio)[1])
    if not os.path.isfile(dst): shutil.copyfile(audio, dst)
    ed = sc.sequence_editor or sc.sequence_editor_create()
    for t in [t for t in ed.strips_all if t.name == "VozAlfred_" + etiqueta]: ed.strips.remove(t)
    canal = max([t.channel for t in ed.strips_all] + [0]) + 1
    t = ed.strips.new_sound("VozAlfred_" + etiqueta, dst, min(canal, 128), f0)
    sc.frame_set(f_act)
    return {"ojos": f"{f0}-{f0 + fin - 1}", "audio": (t.frame_final_start, t.frame_final_end), "texto": ns.get("TRANSCRIPT")}
