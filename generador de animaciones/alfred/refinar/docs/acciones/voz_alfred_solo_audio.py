# -*- coding: utf-8 -*-
"""Voz de Alfred SOLO AUDIO (sin animacion de ojos): coloca una tira `VozAlfred_<TAG>_*` de `audios/alfred/<ARCHIVO>.mp3`, recortada a la voz (+-2 f), por encima de los sonidos de la animacion (volumen `VOL`) y con `duck_todos` (los sonidos solapados bajan a la mitad, `ducking_voces.py`).
Variables: START (frame donde cae el frame 1 del clip), TAG, ARCHIVO, VOL, VOZ = (primer frame con voz, ultimo) del clip.
Usada para `alfred_golpea_mesa` (Record (80).mp3, 1.37 s = 33 f, voz en los frames 10-28 del clip con crescendo hasta el pico en 22-23): START=576 (pedido del usuario: el audio empieza en f576): voz f585-603, pico en f598, cubre los golpes de f590 y f601 (golpes de la mesa en f590, 601, 611, 620; antes START=598 con el pico en el golpe final f620).
Se ejecuta DENTRO de Blender con exec. Repetible. Nunca `raise SystemExit`."""
import bpy, traceback

def canal_libre(ed, a, b):   # el VSE solo tiene 128 canales: busca uno sin tiras en [a, b] (new_sound desplaza la tira si el canal esta ocupado)
    for ch in range(1, 129):
        if not any(t.channel == ch and t.frame_final_start < b and a < t.frame_final_end for t in ed.strips_all): return ch
    raise RuntimeError('sin canal libre')
try:
    sc = bpy.context.scene; ed = sc.sequence_editor
    START = int(globals().get("START", 598)); TAG = globals().get("TAG", "golpea_mesa"); ARCHIVO = globals().get("ARCHIVO", "alfred_golpea_mesa"); VOL = float(globals().get("VOL", 2.4)); VOZ = globals().get("VOZ", (10, 28)); PAD = 2
    SEGS = [tuple(VOZ)] if isinstance(VOZ[0], (int, float)) else [tuple(v) for v in VOZ]            # VOZ = (A, B) o lista de tramos [(A1, B1), (A2, B2), ...] (frames del clip con voz); una tira recortada por tramo
    MP3 = "C:/Users/user/Desktop/Alfred_Animacion/audios/alfred/" + ARCHIVO + ".mp3"
    for s_ in [s_ for s_ in ed.strips_all if str(s_.get("guion_id", "")).startswith("voz6_alfred_" + TAG)]: ed.strips.remove(s_)
    for i, (A, B) in enumerate(SEGS):
        s_ = ed.strips.new_sound(f"VozAlfred_{TAG}_{i + 1}_{START + A - 1}", MP3, canal_libre(ed, START, START + 400), START); n_tot = int(s_.frame_final_duration)
        s_.frame_offset_start = max(0, A - 1 - PAD); s_.frame_offset_end = max(0, n_tot - (B + PAD)); s_.volume = VOL; s_["vol_base"] = VOL; s_["duck_todos"] = True; s_["guion_id"] = f"voz6_alfred_{TAG}_{i + 1}"
        print(s_.name, "canal", s_.channel, "tira f", int(s_.frame_final_start), "-", int(s_.frame_final_end), "voz f", START + A - 1, "-", START + B - 1, "volumen", s_.volume)
    exec(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\ducking_voces.py", encoding="utf-8").read(), {"__name__": "x", "DUCK": 0.5})
    print("LISTO")
except Exception:
    traceback.print_exc()
