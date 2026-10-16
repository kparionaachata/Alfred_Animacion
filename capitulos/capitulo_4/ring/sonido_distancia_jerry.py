# -*- coding: utf-8 -*-
"""Los sonidos de la pelea y del publico se oyen desde donde esta JERRY (base_ranas_2).

El oyente es la cabeza de Jerry (root `jerry` + 0.7 m) y cada emisor es la raiz de quien produce la tira
(`mic_emisor`) + 1 m. Misma ley que el add-on microfono_camara (inverso de la distancia: ref 3 m, -6 dB
por cada duplicacion, minimo 0.05). Parte del volumen ORIGINAL de cada tira (lo que guardo el microfono
en `mic_original`, sin el microfono de camara viejo) y deja los datos del microfono, asi "Quitar
microfono" sigue restaurando todo. Sin frame_set: las posiciones salen de las curvas de cada raiz.
Uso (exec en Blender): aplicar()
"""
import bpy, json, math, sys
from mathutils import Vector
from bpy_extras.anim_utils import action_get_channelbag_for_slot

OYENTE, ALTO_OYENTE, ALTO_EMISOR = "jerry", 0.7, 1.0
REF, CAIDA, MINIMO, PASO = 3.0, 1.0, 0.01, 2
LEJANIA = 0.3          # -10 dB extra: desde donde esta Jerry la pelea solo se oye leve


def _mic():
    for n, m in sys.modules.items():
        if n.endswith("microfono_camara") and hasattr(m, "poner_claves"): return m
    import importlib.util                                                      # sin registrar: solo sus funciones
    ruta = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/microfono_camara/__init__.py"
    spec = importlib.util.spec_from_file_location("microfono_camara_funciones", ruta)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def posicion(o):
    """funcion f -> location de la raiz (sin padre) leida de su accion"""
    ad = o.animation_data; base = o.location.copy()
    if not (ad and ad.action): return lambda f: base
    cb = action_get_channelbag_for_slot(ad.action, ad.action_slot)
    fcs = {fc.array_index: fc for fc in cb.fcurves if fc.data_path == "location"} if cb else {}
    return lambda f: Vector([fcs[i].evaluate(f) if i in fcs else base[i] for i in range(3)])


def aplicar():
    mc = _mic(); sc = bpy.context.scene
    oy = posicion(bpy.data.objects[OYENTE]); arriba_o = Vector((0, 0, ALTO_OYENTE)); arriba_e = Vector((0, 0, ALTO_EMISOR))
    pos = {}; res = {"tiras": 0, "por_emisor": {}}
    for s in [s for s in sc.sequence_editor.strips_all if s.type == 'SOUND']:
        e = s.get("mic_emisor")
        if not e or e == OYENTE or e not in bpy.data.objects: continue
        if e not in pos: pos[e] = posicion(bpy.data.objects[e])
        o = mc.original(sc, s)
        a, b = int(s.frame_final_start), int(s.frame_final_end)
        fr = sorted(set(range(a, b + 1, PASO)) | {a, b})
        gan = {}
        for f in fr:
            d = ((pos[e](f) + arriba_e) - (oy(f) + arriba_o)).length
            gan[f] = max(MINIMO, min(1.0, (REF / max(d, 1e-3)) ** CAIDA) * LEJANIA)
        rv = 'sequence_editor.strips_all["%s"].volume' % s.name; rp = 'sequence_editor.strips_all["%s"].pan' % s.name
        mc.poner_claves(sc, rv, [(f, mc.evaluar(o["vol_claves"], f, o["vol"]) * gan[f]) for f in fr])
        mc.quitar_curva(sc, rp); s.pan = o["pan"]
        if o["pan_claves"]: mc.poner_claves(sc, rp, o["pan_claves"])
        if s.sound and "mic_mono_original" in s.sound.keys(): s.sound.use_mono = bool(s.sound["mic_mono_original"])
        s["mic_original"] = json.dumps(o)
        s["mic_firma"] = mc.firma([mc.claves(mc.curva(sc, rv)), mc.claves(mc.curva(sc, rp))])
        db = [20 * math.log10(g) for g in gan.values()]
        s["mic_info"] = json.dumps({"emisor": e, "oyente": OYENTE, "db_min": round(min(db), 1), "db_max": round(max(db), 1)})
        r = res["por_emisor"].setdefault(e, [99, -99]); r[0] = min(r[0], round(min(db), 1)); r[1] = max(r[1], round(max(db), 1))
        res["tiras"] += 1
    sc.frame_set(sc.frame_current)
    return res
