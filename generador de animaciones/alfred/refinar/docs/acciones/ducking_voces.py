# -*- coding: utf-8 -*-
"""LAS VOCES DE LOS PERSONAJES MANDAN SOBRE LOS SONIDOS DEL JUEGO (ducking): los sonidos del juego (`SND_*`: pasos, voces de mobs, golpes, herramientas...) de los sonidos del juego SOLO los golpes a la madera (archivo con `wood`) y los sonidos de zombies bajan a `DUCK` x su volumen base (0.5 = la mitad) mientras suena una voz; lanzar, golpear, caminar y el resto se quedan a su volumen original SOLO en el tramo en que se solapan
con una voz de personaje (`VozSync_*`); fuera de ese tramo suenan a su volumen normal. Entra y sale con 2 frames de rampa (claves en el volumen de la tira). Si la voz cubre la tira entera, la tira queda fija en el volumen bajo (sin claves).
Una voz con la propiedad `duck_todos`=True (p.ej. `voz_alfred_golpes.py`) baja a `DUCK` TODOS los sonidos del juego que se solapan con ella, no solo madera/zombies. Repetible y sin acumular: el volumen original queda en la propiedad `vol_base` de cada tira y las claves anteriores se quitan antes de volver a calcular.
Dentro de Blender:  exec(open(r"...\\ducking_voces.py", encoding="utf-8").read(), {"__name__": "x"})   (se llama solo al final de `aplicar_secuencia.py` y `aplicar_sonidos_directo.py`; variables opcionales DUCK, RAMPA)."""
import bpy

DUCK = float(globals().get("DUCK", 0.5)); RAMPA = int(globals().get("RAMPA", 2)); sc = bpy.context.scene; ed = sc.sequence_editor


def quitar_claves(nombre):
    ad = sc.animation_data
    if ad is None or ad.action is None: return
    ruta = 'sequence_editor.strips_all["%s"].volume' % nombre
    for capa in ad.action.layers:
        for tira in capa.strips:
            for cb in tira.channelbags:
                for fc in [f for f in cb.fcurves if f.data_path == ruta]: cb.fcurves.remove(fc)


if ed is not None:
    S = [s for s in (ed.strips_all if hasattr(ed, "strips_all") else ed.sequences_all) if s.type == 'SOUND']
    voces = [s for s in S if s.name.startswith("Voz")]; juego = [s for s in S if s.name.startswith("SND_")]; rep = []
    def baja(s):
        """solo los golpes a la madera (archivo con `wood`) y los sonidos de zombies bajan cuando habla una voz; lanzar, golpear, caminar... se quedan a su volumen original."""
        try: ruta = s.sound.filepath.replace("\\", "/").lower()
        except Exception: ruta = ""
        return "wood" in ruta or s.name.lower().startswith("snd_zombie") or "/zombie/" in ruta                                  # (el golpe de Alfred al zombie, `stick_golpea_zombie`, es un golpe de Alfred: no baja)
    for s in juego:
        if "vol_base" not in s.keys(): s["vol_base"] = float(s.volume)
        vs = voces if baja(s) else [v for v in voces if v.get("duck_todos")]                        # una voz con `duck_todos` baja TODOS los sonidos del juego que se solapan con ella
        if not vs: quitar_claves(s.name); s.volume = float(s["vol_base"]); continue
        base = float(s["vol_base"]); a, b = s.frame_final_start, s.frame_final_end; quitar_claves(s.name); s.volume = base
        tramos = sorted((max(a, v.frame_final_start), min(b, v.frame_final_end)) for v in vs if v.frame_final_start < b and a < v.frame_final_end)
        if not tramos: continue
        if tramos[0][0] <= a and tramos[-1][1] >= b and len(tramos) == 1: s.volume = base * DUCK; rep.append((s.name, "entera", round(base * DUCK, 3))); continue                # la voz cubre toda la tira
        s.volume = base
        for (i, f) in tramos:
            for fr, v in ((i - RAMPA, base), (i, base * DUCK), (f, base * DUCK), (f + RAMPA, base)):
                s.volume = v; s.keyframe_insert("volume", frame=int(fr))
        s.volume = base; rep.append((s.name, "tramo %d-%d" % tramos[0], round(base * DUCK, 3)))
    print("DUCKING: %d de %d sonidos del juego bajan a x%.2f solo mientras suena una voz de personaje (%d voz/voces): %s" % (len(rep), len(juego), DUCK, len(voces), rep[:14]))
if sc.get("distancia_camara") and not globals().get("SIN_DISTANCIA"):                                  # escenas con `scene["distancia_camara"]` (parte 7): despues del ducking se aplica la atenuacion por distancia a la camara (`distancia_camara.py`)
    exec(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\distancia_camara.py", encoding="utf-8").read(), {"__name__": "x", "YA_DUCKING": True})
