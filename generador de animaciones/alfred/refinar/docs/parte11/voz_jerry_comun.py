# -*- coding: utf-8 -*-
"""Comun para las VOCES de Jerry en la parte 11 (usado por voz_jerry_voy_a_ir_parte11.py y voz_jerry_anda_ve_parte11.py).
Aplica una frase de Jerry desde el frame F0 con los datos del archivo de cara del usuario (`animacion_jerry*.py`, guardado como
audios/jerry/<frase>.cara_original.py). El archivo NO se ejecuta (borraria la animacion y cambiaria la duracion de la escena): se leen sus datos.
Anima, como ese archivo: mandibula (jaw_bot) y hocico (jaw_top) por silaba, cabeza (scull, scull_1), cejas (sejas_*), expresion de ojos
(COMPONENTS), escala/posicion de los ojos, pupilas y un parpadeo. Lo del rig se SUMA a la accion de jerry_nada_pescado_parte11.py.
Cada frase solo toca SU tramo de frames: varias frases conviven. Repetible (una marca por frase en la accion evita sumar dos veces)."""
import bpy, ast, math, sys, importlib, importlib.util

ESTUDIO = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\jerry\refinar"
RAIZ = "jerry_sin_armadura"; ARM = "Dog_001_rig"
FASES = ((0.00, 0.00), (0.12, 0.00), (0.27, 0.68), (0.43, 1.08), (0.58, 0.93), (0.73, 1.01), (0.87, 0.42), (1.00, 0.00))
PARPADEO = (0.0, 0.25, 0.5, 0.75, 1.0, 1.0, 0.75, 0.5, 0.25, 0.0)
OJOS = ("ojo_izquierdo_jerry", "ojo_derecho_jerry"); PUPILAS = ("pupila_izquierda_jerry", "pupila_derecha_jerry")


def datos(cara):
    d = {}; ajustes = {}
    for n in ast.parse(open(cara, encoding="utf-8").read()).body:
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
            try: d[n.targets[0].id] = ast.literal_eval(n.value)
            except Exception: pass
        if isinstance(n, ast.ClassDef) and n.name == "Settings":
            for a in n.body:
                if isinstance(a, ast.Assign) and isinstance(a.targets[0], ast.Name): ajustes[a.targets[0].id] = ast.literal_eval(a.value)
    d["_Settings"] = type("Settings", (), ajustes)
    return d


def _fc(act, ob, ruta, idx):
    return act.fcurve_ensure_for_datablock(ob, ruta, index=idx)


def _sumar(fc, f, delta):                    # suma a la clave densa del frame f (accion con una clave por frame desde el 1)
    k = fc.keyframe_points[f - 1]
    if int(round(k.co.x)) != f: raise RuntimeError("clave inesperada en %s %d" % (fc.data_path, f))
    k.co.y += delta; k.handle_left.y += delta; k.handle_right.y += delta


def _clave(fc, f, v):
    fc.keyframe_points.insert(f, v, options={'FAST'}).interpolation = 'LINEAR'


def _borrar_tramo(fc, f0, f1):
    for i in reversed(range(len(fc.keyframe_points))):
        if f0 <= fc.keyframe_points[i].co.x <= f1: fc.keyframe_points.remove(fc.keyframe_points[i], fast=True)
    fc.update()


def _borrar_tramo_id(idb, f0, f1):
    ad = getattr(idb, "animation_data", None)
    if ad and ad.action:
        for l in ad.action.layers:
            for st in l.strips:
                for cb in st.channelbags:
                    for fc in cb.fcurves: _borrar_tramo(fc, f0, f1)


def microfono():
    sc = bpy.context.scene
    if not hasattr(sc, "microfono"):
        sp = importlib.util.spec_from_file_location("microfono_camara", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\microfono_camara\__init__.py")
        m = importlib.util.module_from_spec(sp); sys.modules["microfono_camara"] = m; sp.loader.exec_module(m); m.register()
    bpy.ops.microfono.analizar(); bpy.ops.microfono.aplicar()


def aplicar(audio, cara, nombre, F0, marca, volumen=1.3, canal=31, con_microfono=True):
    sc = bpy.context.scene; C = datos(cara); N = C["END_FRAME"]
    habla = {int(f): float(v) for f, v in C["SPEECH_CURVE"]}
    fr = lambda k: F0 + k - 1; F1 = fr(N)

    def peso(k):
        u = (k - 1) / max(1, N - 1)
        for (a, va), (b, vb) in zip(FASES, FASES[1:]):
            if a <= u <= b: return va + (vb - va) * (u - a) / max(1e-6, b - a)
        return 0.0

    # 1. audio
    ed = sc.sequence_editor_create(); S_ = ed.strips if hasattr(ed, "strips") else ed.sequences
    for s in [s for s in S_ if s.name.startswith(nombre)]: S_.remove(s)
    s = S_.new_sound(nombre, audio, canal, F0); s["mic_emisor"] = RAIZ; s.volume = volumen

    # 2. rig: se suma a la accion densa de Jerry (solo una vez por accion)
    arm = bpy.data.objects[ARM]; act = arm.animation_data.action; pb = 'pose.bones["%s"].'
    ya = act.get(marca) == F0
    if act.get(marca) is not None and not ya: raise RuntimeError("la accion de Jerry ya tiene '%s' en otro frame: reconstruir jerry_nada_pescado antes" % marca)
    prev = 0.0
    for k in (range(0) if ya else range(1, N + 1)):
        lv = habla.get(k, 0.0); ataque = max(0.0, lv - prev); f = fr(k)
        _sumar(_fc(act, arm, pb % "jaw_bot" + "rotation_euler", 0), f, -math.radians(25.0) * max(0.0, min(1.0, lv)))
        _sumar(_fc(act, arm, pb % "jaw_bot" + "rotation_euler", 2), f, math.radians(0.45) * lv * math.sin(k * 0.73))
        _sumar(_fc(act, arm, pb % "jaw_top" + "rotation_euler", 0), f, -math.radians(3.0) * lv)
        _sumar(_fc(act, arm, pb % "jaw_top" + "rotation_euler", 1), f, math.radians(1.0) * ataque)
        _sumar(_fc(act, arm, pb % "jaw_top" + "rotation_euler", 2), f, math.radians(0.45) * lv * math.sin(k * 0.61))
        for hueso, sigue in (("scull", 1.0), ("scull_1", 0.55)):
            _sumar(_fc(act, arm, pb % hueso + "rotation_euler", 0), f, math.radians(1.15) * lv * sigue)
            _sumar(_fc(act, arm, pb % hueso + "rotation_euler", 1), f, math.radians(0.55) * lv * math.sin(k * 0.19) * sigue)
        prev = lv
    for hueso, esc in (("jaw_bot", (0.026, -0.010, 0.014)), ("jaw_top", (0.035, -0.012, 0.020))):   # compresion de la malla con la silaba
        for i in range(3):
            fc = _fc(act, arm, pb % hueso + "scale", i); _borrar_tramo(fc, F0 - 1, F1 + 1)
            _clave(fc, F0 - 1, 1.0); _clave(fc, F1 + 1, 1.0)
            for k in range(1, N + 1): _clave(fc, fr(k), 1.0 + esc[i] * habla.get(k, 0.0))
    for j, hueso in enumerate(("sejas_1_jerry", "sejas_2_jerry")):  # cejas: de su base a la pose de la emocion + oscilacion
        base, pose = C["BROW_BASE"][hueso], C["BROW_POSE"][hueso]; lado = 1.0 if j == 0 else -1.0
        locs = [_fc(act, arm, pb % hueso + "location", i) for i in range(3)]
        for i, fc in enumerate(locs):
            _borrar_tramo(fc, F0 - 1, F1 + 1); _clave(fc, F0 - 1, 0.0); _clave(fc, F1 + 1, 0.0)
            for k in range(1, N + 1):
                _clave(fc, fr(k), (pose["loc"][i] - base["loc"][i]) * min(1.0, peso(k) * C["BROW_POSE_STRENGTH"]))
        for k in (range(0) if ya else range(1, N + 1)):
            w = peso(k); sp = habla.get(k, 0.0); mix = min(1.0, w * C["BROW_POSE_STRENGTH"]); f = fr(k)
            for i in range(3): _sumar(_fc(act, arm, pb % hueso + "rotation_euler", i), f, (pose["euler"][i] - base["euler"][i]) * mix)
            _sumar(_fc(act, arm, pb % hueso + "rotation_euler", 2), f, lado * math.radians(2.2) * math.sin(k * 0.27 + j * 0.24) * max(w, sp))
            _sumar(_fc(act, arm, pb % hueso + "rotation_euler", 0), f, math.radians(1.6) * sp * (1.0 if j == 0 else 0.86))
    for fc in act.layers[0].strips[0].channelbags[0].fcurves: fc.update()
    act[marca] = F0

    # 3. ojos y pupilas: solo su tramo (las otras frases quedan); la base se lee justo antes de la frase
    if ESTUDIO not in sys.path: sys.path.insert(0, ESTUDIO)
    eye_system = importlib.import_module("jerry_animation_studio.eye_system")
    blink = fr(N // 2)
    for o in [bpy.data.objects.get(n) for n in OJOS + PUPILAS]:
        if o is None: continue
        _borrar_tramo_id(o, F0, F1)
        if o.data.shape_keys: _borrar_tramo_id(o.data.shape_keys, F0, F1)
    sc.frame_set(F0 - 1)
    for i, n in enumerate(OJOS):
        ojo = bpy.data.objects[n]
        if not (ojo.data.shape_keys and ojo.data.shape_keys.key_blocks.get("Sospecha")):
            eye_system.build_expression_shape_keys(ojo, C["_Settings"]())
        kb = ojo.data.shape_keys.key_blocks; bs, bl = ojo.scale.copy(), ojo.location.copy()
        retraso = i * max(1, int(N * 0.025)); asim = 1.0 if i == 0 else 0.88
        for fase, w in FASES:
            f = fr(min(N, max(1, 1 + round((N - 1) * fase) + (retraso if 0.15 < fase < 0.86 else 0))))
            for expr in ("Feliz", "Triste", "Enojado", "Sospecha"):
                cw = dict(C["COMPONENTS"]).get(expr, 0.0)
                kb[expr].value = C["AMPLITUDE"] * cw * w * asim; kb[expr].keyframe_insert("value", frame=f)
            ojo.scale = bs.copy(); ojo.scale.x *= 1.0 + (C["EYE_SCALE"] - 1.0) * w * asim; ojo.scale.z *= 1.0 + (C["EYE_SCALE"] - 1.0) * w * 0.55
            ojo.location = bl.copy(); ojo.location.z += 0.0025 * w * (1.0 if i == 0 else 0.72)
            ojo.keyframe_insert("scale", frame=f); ojo.keyframe_insert("location", frame=f)
        ojo.scale, ojo.location = bs, bl
        for o in (ojo, bpy.data.objects.get(PUPILAS[i])):
            cl = o.data.shape_keys.key_blocks.get("Closed") if o and o.data.shape_keys else None
            if cl:
                for d, v in enumerate(PARPADEO): cl.value = v; cl.keyframe_insert("value", frame=blink - 4 + d)
    for i, n in enumerate(PUPILAS):
        pu = bpy.data.objects.get(n)
        if pu is None: continue
        bl = pu.location.copy(); lado = 1.0 if i == 0 else -1.0
        for fase, w in FASES:
            pu.location = bl.copy(); pu.location.x += lado * C["PUPIL_SHIFT"] * w * (-1.0 if C.get("GENERATED_EMOTION") == "enojo" else 1.0)
            pu.location.z += C["PUPIL_SHIFT"] * 0.25 * w
            pu.keyframe_insert("location", frame=fr(min(N, max(1, 1 + round((N - 1) * fase)))))
        pu.location = bl

    if con_microfono: microfono()
    return F0, F1
