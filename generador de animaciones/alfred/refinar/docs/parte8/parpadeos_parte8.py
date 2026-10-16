# -*- coding: utf-8 -*-
"""Parte 8: PARPADEOS de Alfred y de Jerry (mismo sistema que `parte7/filtros_organicos_y_parpadeos_parte7.py`): secuencia de 9 f (Closed 0, .25, .5, .75, 1, 1, .75, .5, .25),
uno cada 80-140 f con semilla fija.
 - ALFRED: shape key `Closed` de `ojo_izquierdo_alfred` / `ojo_derecho_alfred` + ojos OCULTOS los 2 f cerrados (hide_viewport / hide_render, CONSTANT).
 - JERRY: `Closed` en los ojos Y las pupilas a la vez.
Sin parpadeos al azar mientras hablan (EVITAR_*: las animaciones de voz traen su propia cara y parpadeo). Repetible: los inicios se guardan en `parpadeos_parte8.json` y sus claves
se borran antes de volver a ponerlos. Ejecutar en Blender con exec."""
import bpy, json, os, random
sc = bpy.context.scene; FIN = sc.frame_end
DJ = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\parte8\parpadeos_parte8.json"
PREV = json.load(open(DJ, encoding="utf-8")) if os.path.exists(DJ) else {}; NEW = {}
SEQ = [0.0, 0.25, 0.5, 0.75, 1.0, 1.0, 0.75, 0.5, 0.25]
EVITAR_A = [(2057, 2086), (2148, 2216), (2347, 2374), (2452, 2520), (2530, 2545)]          # voces de Alfred (+ el impacto de la flecha)
EVITAR_J = [(2100, 2140), (2230, 2260), (2271, 2342), (2420, 2458)]                        # voces de Jerry
def horario(seed, inicio, fin, evitar, gap=(80, 140)):
    rng = random.Random(seed); f = inicio + rng.randint(5, 40); out = []
    while f + 10 < fin:
        if any(a - 12 <= f <= b + 12 for a, b in evitar): f += 6; continue
        out.append(f); f += rng.randint(*gap)
    return out
def fcs(owner):
    if not owner.animation_data or not owner.animation_data.action: return []
    return [fc for l in owner.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]
def borrar(objs, inicios, con_hide):
    for o in objs:
        for owner, filtro in ((o.data.shape_keys, lambda fc: "Closed" in fc.data_path),) + (((o, lambda fc: fc.data_path.startswith("hide")),) if con_hide else ()):
            for fc in fcs(owner):
                if not filtro(fc): continue
                for i in range(len(fc.keyframe_points) - 1, -1, -1):
                    if any(s - 1 <= fc.keyframe_points[i].co.x <= s + 9 for s in inicios): fc.keyframe_points.remove(fc.keyframe_points[i])
                fc.update()
ojosA = [bpy.data.objects["ojo_izquierdo_alfred"], bpy.data.objects["ojo_derecho_alfred"]]
ojosJ = [bpy.data.objects[n] for n in ("ojo_izquierdo_jerry", "ojo_derecho_jerry", "pupila_izquierda_jerry", "pupila_derecha_jerry")]
borrar(ojosA, PREV.get("alfred", []), True); borrar(ojosJ, PREV.get("jerry", []), False)
# --- Alfred ---
bA = horario(31, 1, FIN, EVITAR_A); NEW["alfred"] = bA
for s in bA:
    for o in ojosA:
        ck = o.data.shape_keys.key_blocks["Closed"]
        ck.value = 0.0; ck.keyframe_insert("value", frame=s - 1); o.hide_viewport = False; o.hide_render = False; o.keyframe_insert("hide_viewport", frame=s - 1); o.keyframe_insert("hide_render", frame=s - 1)
        for i, v in enumerate(SEQ):
            ck.value = v; ck.keyframe_insert("value", frame=s + i); h = v >= 1.0; o.hide_viewport = h; o.hide_render = h; o.keyframe_insert("hide_viewport", frame=s + i); o.keyframe_insert("hide_render", frame=s + i)
        ck.value = 0.0; ck.keyframe_insert("value", frame=s + 9); o.hide_viewport = False; o.hide_render = False; o.keyframe_insert("hide_viewport", frame=s + 9); o.keyframe_insert("hide_render", frame=s + 9)
for o in ojosA:
    for owner in (o, o.data.shape_keys):
        for fc in fcs(owner):
            for kp in fc.keyframe_points:
                if any(s - 1 <= kp.co.x <= s + 9 for s in bA): kp.interpolation = 'CONSTANT' if fc.data_path.startswith("hide") else 'LINEAR'
# --- Jerry (ojos y pupilas) ---
bJ = horario(47, 1, FIN, EVITAR_J); NEW["jerry"] = bJ
for s in bJ:
    for o in ojosJ:
        ck = o.data.shape_keys.key_blocks["Closed"]
        for i, v in enumerate([0.0] + SEQ + [0.0]): ck.value = v; ck.keyframe_insert("value", frame=s - 1 + i)
for o in ojosJ:
    for fc in fcs(o.data.shape_keys):
        for kp in fc.keyframe_points:
            if any(s - 1 <= kp.co.x <= s + 9 for s in bJ): kp.interpolation = 'LINEAR'
for o in bpy.data.objects:                                                                  # los ojos de Alfred deben verse fuera de los parpadeos
    pass
json.dump(NEW, open(DJ, "w", encoding="utf-8"))
print("Parpadeos: Alfred %d %s | Jerry %d %s" % (len(bA), bA, len(bJ), bJ))
