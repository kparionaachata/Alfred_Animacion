# -*- coding: utf-8 -*-
"""Parte 6, f160+: el quejido de Alfred (dormido) cuando Jerry le lanza el hacha y el pico de madera a la cabeza.
Audio del usuario `audios/alfred/alfred_quejido_golpe_cabeza.mp3` (copia de `Record (online-voice-recorder.com) (75).mp3`; 0.48 s = 11.5 f a 24 fps; envolvente por frame: 5 f de silencio y luego la voz en f5-f8 con el pico en f6).
Se coloca una tira por golpe con el INICIO DE LA VOZ 1 frame despues del impacto: golpe del hacha en f164 -> voz en f165 (tira desde f160), golpe del pico en f206 -> voz en f207 (tira desde f202). Sin animacion de ojos (Alfred duerme).
Volumen: la voz queda POR ENCIMA de los sonidos de la animacion: volumen de tira 3.0 (+9.5 dB, pico 0.80 sin recortar; el audio crudo pico 0.27 / -29.7 dB RMS frente a `fallbig` pico 0.94 / -21.4 dB RMS), y los sonidos de la animacion que se solapan con la voz bajan a la MITAD (x0.5, 2 f de rampa) via `ducking_voces.py` (propiedad `duck_todos` de la tira).
Se ejecuta DENTRO de Blender con exec. Repetible (borra sus tiras). Nunca `raise SystemExit`."""
import bpy, os, traceback

try:
    sc = bpy.context.scene; ed = sc.sequence_editor
    AUD = r"C:\Users\user\Desktop\Alfred_Animacion\audios\alfred\alfred_quejido_golpe_cabeza.mp3"; LEAD = 5; VOL = 3.0
    for s_ in [s_ for s_ in ed.strips_all if str(s_.get("guion_id", "")).startswith("voz6_alfred_golpe")]: ed.strips.remove(s_)
    libre = max([s_.channel for s_ in ed.strips_all] + [30]) + 1
    for i, (nombre, impacto) in enumerate((("hacha", 164), ("pico", 206))):
        ini = impacto + 1 - LEAD
        s_ = ed.strips.new_sound(f"VozGolpe_alfred_{nombre}_{impacto + 1}", AUD, libre + i, ini); s_.volume = VOL; s_["vol_base"] = VOL; s_["duck_todos"] = True; s_["guion_id"] = f"voz6_alfred_golpe_{nombre}"
        print(s_.name, "tira f", int(s_.frame_final_start), "-", int(s_.frame_final_end), "voz desde f", ini + LEAD, "volumen", s_.volume)
    DUCK = 0.5; exec(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\ducking_voces.py", encoding="utf-8").read(), {"__name__": "x", "DUCK": 0.5})
    print("LISTO")
except Exception:
    traceback.print_exc()
