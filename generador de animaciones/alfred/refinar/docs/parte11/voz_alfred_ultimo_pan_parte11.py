# -*- coding: utf-8 -*-
"""Parte 11: Alfred responde a Jerry "Prefiero comer mi ultimo pan, estoy de mala suerte ultimamente" mientras saca el pan de su espalda,
lo levanta delante y lo mira orgulloso (el gesto y el pan los anima alfred_saca_flechas_parte11.py: tramo PAN, `p11_tiempos` pan_*).
Audio: audios/alfred/alfred_prefiero_comer_mi_ultimo_pan.mp3; ojos: .cara_original.py del usuario (NO se ejecuta: se leen sus datos).
Ojos: shape key 'Voz_ultimo_pan' + escala/posicion/rotacion del archivo del usuario, con claves solo en su tramo (la base se lee justo antes).
Repetible. Al final aplica el MICROFONO de camara."""
import bpy, ast, math, sys, importlib.util

AUDIO = r"C:\Users\user\Desktop\Alfred_Animacion\audios\alfred\alfred_prefiero_comer_mi_ultimo_pan.mp3"
CARA = r"C:\Users\user\Desktop\Alfred_Animacion\audios\alfred\alfred_prefiero_comer_mi_ultimo_pan.cara_original.py"
NOMBRE = "VOZ_p11_alfred_ultimo_pan"; CANAL = 30; SHAPE = "Voz_ultimo_pan"
FASES = ((0.00, 0.00), (0.12, 0.00), (0.28, 0.70), (0.42, 1.08), (0.57, 0.92), (0.72, 1.02), (0.86, 0.48), (1.00, 0.00))


def _datos():
    d = {}
    for n in ast.parse(open(CARA, encoding="utf-8").read()).body:
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id.isupper():
            try: d[n.targets[0].id] = ast.literal_eval(n.value)
            except Exception: pass
    return d


def _borrar_tramo(idb, f0, f1):
    ad = getattr(idb, "animation_data", None)
    if ad and ad.action:
        for l in ad.action.layers:
            for st in l.strips:
                for cb in st.channelbags:
                    for fc in cb.fcurves:
                        for i in reversed(range(len(fc.keyframe_points))):
                            if f0 <= fc.keyframe_points[i].co.x <= f1: fc.keyframe_points.remove(fc.keyframe_points[i], fast=True)
                        fc.update()


def construir(con_microfono=True):
    sc = bpy.context.scene; C = _datos(); N = C["END_FRAME"]; F0 = int(sc["p11_tiempos"]["pan_f0"])
    fr = lambda k: F0 + k - 1; F1 = fr(N)
    habla = {int(f): float(v) for f, v in C["SPEECH_CURVE"]}

    def peso(k):
        u = (k - 1) / max(1, N - 1)
        for (a, va), (b, vb) in zip(FASES, FASES[1:]):
            if a <= u <= b: return va + (vb - va) * (u - a) / max(1e-6, b - a)
        return 0.0

    ed = sc.sequence_editor_create(); S_ = ed.strips if hasattr(ed, "strips") else ed.sequences
    for s in [s for s in S_ if s.name.startswith(NOMBRE)]: S_.remove(s)
    s = S_.new_sound(NOMBRE, AUDIO, CANAL, F0); s["mic_emisor"] = "alfred"

    for i, (nombre, coords) in enumerate(C["COORDINATES"].items()):
        ojo = bpy.data.objects[nombre]; kb = ojo.data.shape_keys.key_blocks
        if kb.get(SHAPE): ojo.shape_key_remove(kb[SHAPE])
        sk = ojo.shape_key_add(name=SHAPE, from_mix=False); sk.slider_min = -2.0; sk.slider_max = 2.0
        sk.data.foreach_set("co", [c for v in coords for c in v])
        _borrar_tramo(ojo, F0, F1); _borrar_tramo(ojo.data.shape_keys, F0, F1)
        sc.frame_set(F0 - 1); bl, bs, br = ojo.location.copy(), ojo.scale.copy(), ojo.rotation_euler.copy()
        for f in (F0 - 1, F1 + 1): sk.value = 0.0; sk.keyframe_insert("value", frame=f)
        lado = 1.0 if ojo.matrix_world.translation.x > 0 else -1.0; amt = 1.0 if i == 0 else 0.86; prev = 0.0
        for k in range(1, N + 1):
            w = peso(k); lv = habla.get(k, 0.0); ataque = max(0.0, lv - prev); ola = math.sin(k * 1.34 + i * 0.16); estira = ola * lv; f = fr(k)
            sk.value = C["SHAPE_VALUE"] * w * amt; sk.keyframe_insert("value", frame=f)
            ojo.location = bl.copy(); ojo.location.x += lado * C["LATERAL"] * w * (1.0 if i == 0 else -0.55)
            ojo.location.z += C["VERTICAL"] * w * (1.0 if k < N * 0.60 else 0.65) + C["SPEECH_VERTICAL"] * lv * ola * amt
            ojo.scale = bs.copy()
            ojo.scale.x *= (1.0 + (C["SCALE_X"] - 1.0) * w * amt) * (1.0 + C["SPEECH_SCALE_X"] * lv - 0.040 * estira)
            ojo.scale.y *= 1.0 - 0.025 * lv
            ojo.scale.z *= (1.0 + (C["SCALE_Z"] - 1.0) * w * amt) * (1.0 + C["SPEECH_SCALE_Z"] * lv + 0.065 * estira + 0.025 * ataque)
            ojo.rotation_euler = br.copy(); ojo.rotation_euler.y += lado * (C["ROTATION"] * w + C["ATTACK_ROTATION"] * ataque) * amt
            for p in ("location", "scale", "rotation_euler"): ojo.keyframe_insert(p, frame=f)
            prev = lv
        for p, v in (("location", bl), ("scale", bs), ("rotation_euler", br)):    # vuelve a su base despues de la frase
            setattr(ojo, p, v); ojo.keyframe_insert(p, frame=F1 + 1)
        cl = kb.get("Closed")
        if cl:
            for c in C["BLINK_CENTERS"]:
                for f, v in ((fr(c) - 2, 0.0), (fr(c), 1.0), (fr(c) + 2, 0.0)): cl.value = v; cl.keyframe_insert("value", frame=f)

    if con_microfono:
        if not hasattr(bpy.ops.microfono, "aplicar") or not hasattr(sc, "microfono"):
            sp = importlib.util.spec_from_file_location("microfono_camara", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\microfono_camara\__init__.py")
            m = importlib.util.module_from_spec(sp); sys.modules["microfono_camara"] = m; sp.loader.exec_module(m)
            try: m.register()
            except Exception: pass
        bpy.ops.microfono.analizar(); bpy.ops.microfono.aplicar()
    sc["p11_voz_ultimo_pan"] = {"inicio": F0, "fin": F1}
    print("VOZ ALFRED 'ultimo pan':", F0, "-", F1)
    return F0


if __name__ in ("__main__", "x"):
    construir()
