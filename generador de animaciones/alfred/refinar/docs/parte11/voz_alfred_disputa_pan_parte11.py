# -*- coding: utf-8 -*-
"""Parte 11: VOCES de Alfred en la DISPUTA por el pan con la paloma (audios del usuario, transcritos con Whisper):
  - alfred_oye_no_mi_pan.mp3   "¡Oye! ¡No, mi pan, mi pan!"      -> el "¡Oye!" (frames 3-9 del audio) justo cuando la paloma MUERDE el pan
                                                                    (pan_llega) y el resto mientras empiezan a tirar;
  - alfred_no_no_no_mi_pan.mp3 "¡No, no, no, no, mi pan, mi pan!" -> cuando va perdiendo: el ultimo "mi pan" (frames 32-37 del audio)
                                                                    cae en el TIRON que lo lanza al mar (pan_gana).
Tiempos de `p11_tiempos` (alfred_saca_flechas_parte11.py). Alfred es el emisor (microfono de camara). Repetible. Aplica el MICROFONO al final."""
import bpy, sys, importlib.util

A = r"C:\Users\user\Desktop\Alfred_Animacion\audios\alfred"
VOCES = [  # (nombre de tira, archivo, frame del audio que se ancla, ancla en la escena)
    ("VOZ_p11_alfred_oye_mi_pan", A + r"\alfred_oye_no_mi_pan.mp3", 3, "pan_llega"),
    ("VOZ_p11_alfred_no_no_mi_pan", A + r"\alfred_no_no_no_mi_pan.mp3", 34, "pan_gana"),
]
CANAL = 30


def construir(con_microfono=True):
    sc = bpy.context.scene; T = sc["p11_tiempos"]
    ed = sc.sequence_editor_create(); S_ = ed.strips if hasattr(ed, "strips") else ed.sequences
    puestos = {}
    ad = sc.animation_data                                                    # curvas de volumen/pan de versiones anteriores de estas tiras (si no, se reaplican)
    if ad and ad.action:
        for l in ad.action.layers:
            for st in l.strips:
                for cb in st.channelbags:
                    for fc in [fc for fc in cb.fcurves if any('["%s"]' % v[0] in fc.data_path for v in VOCES)]: cb.fcurves.remove(fc)
        ad.action.update_tag(); sc.update_tag(); bpy.context.view_layer.update()
    for nombre, ruta, f_audio, ancla in VOCES:
        for s in [s for s in S_ if s.name.startswith(nombre)]: S_.remove(s)
        f0 = int(T[ancla]) - f_audio
        s = S_.new_sound(nombre, ruta, CANAL, f0); s["mic_emisor"] = "alfred"
        a, b = s.frame_final_start, s.frame_final_end                       # canal libre (no pisar otras voces)
        for c in range(CANAL, CANAL + 10):
            if not any(o != s and o.channel == c and o.frame_final_start < b and o.frame_final_end > a for o in S_): s.channel = c; break
        puestos[nombre] = (s.frame_final_start, s.frame_final_end)
    if con_microfono:
        try: bpy.ops.microfono.analizar()
        except Exception:
            sp = importlib.util.spec_from_file_location("microfono_camara", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\microfono_camara\__init__.py")
            m = importlib.util.module_from_spec(sp); sys.modules["microfono_camara"] = m; sp.loader.exec_module(m)
            try: m.register()
            except Exception: pass
            bpy.ops.microfono.analizar()
        bpy.ops.microfono.aplicar()
    sc["p11_voz_disputa_pan"] = {k: list(v) for k, v in puestos.items()}
    print("VOCES DISPUTA PAN:", puestos)
    return puestos


if __name__ in ("__main__", "x"):
    construir()
