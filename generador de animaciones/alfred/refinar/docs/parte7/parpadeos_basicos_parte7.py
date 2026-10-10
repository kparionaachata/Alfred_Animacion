# -*- coding: utf-8 -*-
"""Parte 7: PARPADEOS BASICOS de Alfred y Jerry en TODO el tramo (f1-fin). Los scripts de voz borran las claves `Closed` de su rango (y los parpadeos al azar de `filtros_organicos_y_parpadeos_parte7.py` que caian ahi), asi que quedaban huecos de 100-150 f sin parpadear.
Este script mira los parpadeos que YA hay (picos de `Closed` = 1 en `ojo_izquierdo_*`: los de la expresion de cada voz y los al azar) y rellena cada hueco mayor de MAX_HUECO (110 f) con parpadeos extra espaciados ~OBJETIVO (90 f), con un poco de azar (semilla fija) y sin pisar otro parpadeo (+-14 f).
Mismo parpadeo que el resto: curva de 9 f 0-.25-.5-.75-1-1-.75-.5-.25 en `Closed`; Alfred ademas oculta los ojos (`hide_viewport`/`hide_render`, CONSTANT) mientras `Closed` = 1 (su truco); Jerry en ojos Y pupilas.
Repetible: los parpadeos que puso este script se guardan en `recorridos/parpadeos_basicos_delta_parte7.json` y se quitan antes de volver a calcular. EJECUTAR SIEMPRE DESPUES de los scripts de voz (cada voz borra las claves de su rango; si se corre una voz despues, volver a correr este).
Se ejecuta DENTRO de Blender con exec. Variables opcionales: QUITAR (solo quita los suyos), MAX_HUECO, OBJETIVO."""
import bpy, json, os, random

sc = bpy.context.scene
DJ = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\parte7\recorridos\parpadeos_basicos_delta_parte7.json"
QUITAR = bool(globals().get("QUITAR", False)); MAX_HUECO = int(globals().get("MAX_HUECO", 110)); OBJETIVO = int(globals().get("OBJETIVO", 90)); FIN = sc.frame_end
SEQ = [0.0, 0.25, 0.5, 0.75, 1.0, 1.0, 0.75, 0.5, 0.25]


def fcs(o):
    ad = o.animation_data
    return [fc for l in ad.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves] if ad and ad.action else []


ojosA = [bpy.data.objects[n] for n in ("ojo_izquierdo_alfred", "ojo_derecho_alfred")]
ojosJ = [bpy.data.objects[n] for n in ("ojo_izquierdo_jerry", "ojo_derecho_jerry", "pupila_izquierda_jerry", "pupila_derecha_jerry")]
PREV = json.load(open(DJ, encoding="utf-8")) if os.path.exists(DJ) else {"alfred": [], "jerry": []}


def borrar(objs, s, hide):
    for o in objs:
        for own in ((o, o.data.shape_keys) if hide else (o.data.shape_keys,)):
            for fc in fcs(own):
                if ("Closed" in fc.data_path) or (hide and own is o and fc.data_path.startswith("hide")):
                    for i in range(len(fc.keyframe_points) - 1, -1, -1):
                        if s - 1 <= fc.keyframe_points[i].co.x <= s + 9: fc.keyframe_points.remove(fc.keyframe_points[i])


def picos(o):
    pk = sorted({int(round(k.co.x)) for fc in fcs(o.data.shape_keys) if "Closed" in fc.data_path for k in fc.keyframe_points if k.co.y > 0.99}); out = []
    for f in pk:
        if out and f - out[-1][1] <= 2: out[-1][1] = f
        else: out.append([f, f])
    return [a for a, b in out]


NEW = {"alfred": [], "jerry": []}
for clave, objs, hide in (("alfred", ojosA, True), ("jerry", ojosJ, False)):
    for s in PREV.get(clave, []): borrar(objs, s, hide)                                              # quitar los de una pasada anterior
    if QUITAR: continue
    ev = [f for f in picos(objs[0]) if 1 <= f <= FIN]; rng = random.Random(7 if clave == "alfred" else 19); nuevos = []
    limites = [1 - OBJETIVO // 2] + ev + [FIN + OBJETIVO // 2]                                        # los extremos cuentan como un parpadeo virtual medio objetivo fuera
    for a, b in zip(limites, limites[1:]):
        if b - a <= MAX_HUECO: continue
        n = max(1, round((b - a) / OBJETIVO) - 1)
        for i in range(1, n + 1):
            f = int(round(a + (b - a) * i / (n + 1) + rng.randint(-8, 8)))
            if 1 <= f <= FIN - 12 and all(abs(f - e) > 14 for e in ev + nuevos): nuevos.append(f)
    NEW[clave] = sorted(nuevos)
    for s in NEW[clave]:
        for o in objs:
            ck = o.data.shape_keys.key_blocks["Closed"]
            ck.value = 0.0; ck.keyframe_insert("value", frame=s - 1)
            if hide: o.hide_viewport = False; o.hide_render = False; o.keyframe_insert("hide_viewport", frame=s - 1); o.keyframe_insert("hide_render", frame=s - 1)
            for i, v in enumerate(SEQ + ([] if hide else [0.0])):
                ck.value = v; ck.keyframe_insert("value", frame=s + i)
                if hide: h = v >= 1.0; o.hide_viewport = h; o.hide_render = h; o.keyframe_insert("hide_viewport", frame=s + i); o.keyframe_insert("hide_render", frame=s + i)
            if hide: ck.value = 0.0; ck.keyframe_insert("value", frame=s + 9); o.hide_viewport = False; o.hide_render = False; o.keyframe_insert("hide_viewport", frame=s + 9); o.keyframe_insert("hide_render", frame=s + 9)
        for o in objs:
            for own in ((o, o.data.shape_keys) if hide else (o.data.shape_keys,)):
                for fc in fcs(own):
                    if ("Closed" in fc.data_path) or (hide and own is o and fc.data_path.startswith("hide")):
                        for kp in fc.keyframe_points:
                            if s - 1 <= kp.co.x <= s + 9: kp.interpolation = "CONSTANT" if fc.data_path.startswith("hide") else "LINEAR"
os.makedirs(os.path.dirname(DJ), exist_ok=True); json.dump(NEW, open(DJ, "w", encoding="utf-8"))
sc.frame_set(440); print("QUITADO" if QUITAR else "Parpadeos nuevos:", NEW)
