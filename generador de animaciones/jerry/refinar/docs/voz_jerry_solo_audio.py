# -*- coding: utf-8 -*-
"""Voz de Jerry sin animacion de rostro de la app: tira `VozJerry_<TAG>_*` de `audios/jerry/<ARCHIVO>.wav` (recortada a la voz +-2 f, volumen `VOL`, `duck_todos`: los sonidos de la animacion solapados bajan a la mitad con `ducking_voces.py`) y la MANDIBULA sincronizada con la ENVOLVENTE del audio (`jaw_bot` X -25 grados * nivel, `jaw_top` -3 grados * nivel), SUMADA al valor que ya tenga (no repetir sobre el mismo rango). Ojos, cejas y cuerpo no se tocan.
Variables: START (frame del clip que cae en f<START>; el frame 1 del clip), TAG, ARCHIVO, VOL, VOZ = (primer, ultimo) frame del clip con voz.
Usada para `jerry_habla_corriendo` (Record (84)_Jerry_*.wav, 0.96 s = 23 f, voz en los frames 2-22 del clip): START=918 -> voz en **f919-939**, mientras Jerry termina su recorrido (llega a (-92.5,-108.5) en f938 y gira a 270 en f939-950).
Se ejecuta DENTRO de Blender con exec. Nunca `raise SystemExit`."""
import bpy, math, wave, array, traceback

def canal_libre(ed, a, b):   # el VSE solo tiene 128 canales: busca uno sin tiras en [a, b]
    for ch in range(1, 129):
        if not any(t.channel == ch and t.frame_final_start < b and a < t.frame_final_end for t in ed.strips_all): return ch
    raise RuntimeError('sin canal libre')
try:
    sc = bpy.context.scene; ed = sc.sequence_editor; D2R = math.pi / 180
    START = int(globals().get("START", 918)); TAG = globals().get("TAG", "habla_corriendo"); ARCHIVO = globals().get("ARCHIVO", "jerry_habla_corriendo"); VOL = float(globals().get("VOL", 2.8)); A, B = globals().get("VOZ", (2, 22)); PAD = 2
    WAV = "C:/Users/user/Desktop/Alfred_Animacion/audios/jerry/" + ARCHIVO + ".wav"; F = lambda k: START + k - 1
    JA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "scull_1" in o.pose.bones); jb = JA.pose.bones["jaw_bot"]; jt = JA.pose.bones["jaw_top"]; jb.rotation_mode = 'XYZ'; jt.rotation_mode = 'XYZ'
    w = wave.open(WAV); raw = w.readframes(w.getnframes()); sr = w.getframerate(); w.close(); smp = array.array('h'); smp.frombytes(raw); hop = sr // 24
    env = [max(abs(x) for x in smp[i:i + hop]) / 32768.0 for i in range(0, len(smp), hop)]; mx = max(env) or 1.0; LV = {k + 1: min(1.0, e / mx) for k, e in enumerate(env)}
    ks = list(range(max(1, A - 1), B + 3)); BASE = {}
    for k in ks:
        sc.frame_set(F(k)); BASE[k] = (tuple(jb.rotation_euler), tuple(jt.rotation_euler))
    for k in ks:
        lv = LV.get(k, 0.0) if A <= k <= B else 0.0; rb, rt = BASE[k]
        jb.rotation_euler = (rb[0] - 25 * D2R * lv, rb[1], rb[2]); jt.rotation_euler = (rt[0] - 3 * D2R * lv, rt[1], rt[2])
        for pb in (jb, jt):
            for ax in range(3): pb.keyframe_insert("rotation_euler", index=ax, frame=F(k), group=pb.name)
    for s_ in [s_ for s_ in ed.strips_all if str(s_.get("guion_id", "")).startswith("voz6_jerry_" + TAG)]: ed.strips.remove(s_)
    s_ = ed.strips.new_sound(f"VozJerry_{TAG}_{F(A)}", WAV, canal_libre(ed, START, START + 300), START); n_tot = int(s_.frame_final_duration)
    s_.frame_offset_start = max(0, A - 1 - PAD); s_.frame_offset_end = max(0, n_tot - (B + PAD)); s_.volume = VOL; s_["vol_base"] = VOL; s_["duck_todos"] = True; s_["guion_id"] = "voz6_jerry_" + TAG
    print(s_.name, "canal", s_.channel, "tira f", int(s_.frame_final_start), "-", int(s_.frame_final_end), "voz f", F(A), "-", F(B), "volumen", s_.volume)
    exec(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\ducking_voces.py", encoding="utf-8").read(), {"__name__": "x", "DUCK": 0.5})
    res = {}
    for f in (F(A) - 1, F(A) + 3, F(A) + 10, F(B), F(B) + 2):
        sc.frame_set(f); res[f] = round(math.degrees(jb.rotation_euler[0]), 1)
    sc.frame_set(120); print("jaw_bot:", res); print("LISTO")
except Exception:
    traceback.print_exc()
