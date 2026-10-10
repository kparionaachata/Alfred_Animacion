# -*- coding: utf-8 -*-
"""DISTANCIA A LA CAMARA: mientras un personaje se aleja de la camara el volumen de SUS sonidos (voces `Voz*` y sonidos del juego `SND_*` de ese personaje) baja hasta un MINIMO de 0.5 (-6 dB, "maximo un 50 %"); al acercarse sube.
Ganancia = 1 - (1 - MIN) * smoothstep((d - D_CERCA) / (D_LEJOS - D_CERCA)), con d = distancia entre la camara de la escena (`scene.camera`, su ubicacion animada) y la raiz del personaje (empty `alfred`, `jerry`, `creeper_1`, `chicken_1`) EN CADA FRAME.
Valores de la parte 7 (d va de 4.1 a 12.6): D_CERCA = 4.0 (a esa distancia o menos: volumen completo), D_LEJOS = 12.5 (a esa o mas: la mitad), MIN = 0.5. Sin efecto de tono (el VSE de Blender no tiene pitch).
Duenos por nombre de la tira: `alfred` / `grass_step_armature` / `cuerpo_a.002` -> alfred; `jerry` -> jerry; `creeper` -> creeper_1; `pollo` / `chicken` -> chicken_1. Una tira sin dueno conocido no se toca (se lista en `sin_dueno`).
Se compone con el ducking de las voces: el volumen base de cada tira (`vol_base`, y las claves de ducking de los sonidos del juego) se multiplica por la ganancia y se guarda como claves LINEALES cada 3 frames (mas las claves del ducking). Repetible y sin acumular (parte siempre de `vol_base` + ducking).
Se activa con la propiedad de escena `scene["distancia_camara"] = True`: `ducking_voces.py` (que ya llaman todos los scripts de voz) lo ejecuta al final. Ejecucion directa: exec(open(RUTA).read(), {"__name__": "x"}) -> hace el ducking y luego la distancia.
Variables opcionales: D_CERCA, D_LEJOS, MIN, PASO, YA_DUCKING (lo pone ducking_voces al llamarlo)."""
import bpy

sc = bpy.context.scene; ed = sc.sequence_editor
D_CERCA = float(globals().get("D_CERCA", 4.0)); D_LEJOS = float(globals().get("D_LEJOS", 12.5)); MIN = float(globals().get("MIN", 0.5)); PASO = int(globals().get("PASO", 3))
RAIZ = {"alfred": "alfred", "jerry": "jerry", "creeper": "creeper_1", "pollo": "chicken_1"}
DIR = "C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/"

if not globals().get("YA_DUCKING"):                                                                    # estado limpio: el ducking quita las claves de volumen de los sonidos del juego (y NO vuelve a llamar a este script)
    exec(open(DIR + "ducking_voces.py", encoding="utf-8").read(), {"__name__": "x", "SIN_DISTANCIA": True})


def curvas(o):
    ad = o.animation_data
    return [fc for l in ad.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves] if ad and ad.action else []


def f_loc(o):
    cv = {fc.array_index: fc for fc in curvas(o) if fc.data_path == "location"}; base = tuple(o.location)
    return lambda f: tuple(cv[i].evaluate(f) if i in cv else base[i] for i in range(3))


def dueno(nombre):
    n = nombre.lower()
    if "alfred" in n or "grass_step_armature" in n or "cuerpo_a.002" in n: return "alfred"
    if "jerry" in n: return "jerry"
    if "creeper" in n: return "creeper"
    if "pollo" in n or "chicken" in n: return "pollo"
    return None


def ganancia(d):
    t = max(0.0, min(1.0, (d - D_CERCA) / (D_LEJOS - D_CERCA))); return 1.0 - (1.0 - MIN) * t * t * (3 - 2 * t)


def quitar_claves(nombre):
    ad = sc.animation_data
    if ad is None or ad.action is None: return
    ruta = 'sequence_editor.strips_all["%s"].volume' % nombre
    for capa in ad.action.layers:
        for tira in capa.strips:
            for cb in tira.channelbags:
                for fc in [f for f in cb.fcurves if f.data_path == ruta]: cb.fcurves.remove(fc)


def curva_volumen(nombre):
    ad = sc.animation_data
    if ad is None or ad.action is None: return None
    ruta = 'sequence_editor.strips_all["%s"].volume' % nombre
    for capa in ad.action.layers:
        for tira in capa.strips:
            for cb in tira.channelbags:
                for fc in cb.fcurves:
                    if fc.data_path == ruta: return fc
    return None


cam = f_loc(sc.camera); pos = {k: f_loc(bpy.data.objects[v]) for k, v in RAIZ.items()}
dist = lambda k, f: sum((a - b) ** 2 for a, b in zip(pos[k](f), cam(f))) ** 0.5
res = {"tiras": 0, "claves": 0, "sin_dueno": [], "ganancia_min": {}, "ganancia_max": {}}
if ed is not None:
    for s in [s for s in ed.strips_all if s.type == 'SOUND' and (s.name.startswith("Voz") or s.name.startswith("SND_"))]:
        k = dueno(s.name)
        if "vol_base" not in s.keys():
            s["vol_base"] = float(s.volume)
        if k is None:
            res["sin_dueno"].append(s.name)
            if s.name.startswith("Voz"): quitar_claves(s.name); s.volume = float(s["vol_base"])
            continue
        base = float(s["vol_base"]) if s.name.startswith("Voz") else float(s.volume); fc = curva_volumen(s.name)           # sonido del juego sin claves: su volumen actual (ya con el ducking "entera"); voz: su volumen base
        if s.name.startswith("Voz") and fc is not None:                                                  # las voces no llevan ducking: quitar las claves de una pasada anterior
            quitar_claves(s.name); s.volume = base; fc = None
        a, b = int(s.frame_final_start), int(s.frame_final_end)
        fr = set(range(a, b + 1, PASO)) | {a, b}
        if fc is not None: fr |= {int(round(p.co.x)) for p in fc.keyframe_points}
        val = {f: (fc.evaluate(f) if fc is not None else base) * ganancia(dist(k, f)) for f in sorted(fr)}
        quitar_claves(s.name)
        for f, v in val.items():
            s.volume = v; s.keyframe_insert("volume", frame=f); res["claves"] += 1
        fc2 = curva_volumen(s.name)
        if fc2:
            for p in fc2.keyframe_points: p.interpolation = 'LINEAR'
            fc2.update()
        g = [ganancia(dist(k, f)) for f in sorted(fr)]; res["ganancia_min"][k] = round(min(res["ganancia_min"].get(k, 1.0), min(g)), 3); res["ganancia_max"][k] = round(max(res["ganancia_max"].get(k, 0.0), max(g)), 3)
        s["dist_gain"] = round(sum(g) / len(g), 3); res["tiras"] += 1
sc["distancia_camara"] = True
print("DISTANCIA:", res)
