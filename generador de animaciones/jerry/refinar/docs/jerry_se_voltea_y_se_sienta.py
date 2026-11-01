# -*- coding: utf-8 -*-
"""Parte 6, f710+: Jerry se VOLTEA a ver a Alfred (acaba de saltar fuera de la fosa), se SIENTA y dice (audio `audios/jerry/jerry_sentado_mira_alfred.wav`, 1.14 s = 27 f, voz continua en los frames 3-27 del clip). Sin animacion de rostro (ni ojos ni cejas).
Animacion de sentado = `SITTING_POSE` del script `audios/jerry/jerry_sentado_mira_alfred.hablar_original.py` (slot 54 `hablar`, 29 huesos en Euler absoluto; leida con `ast`, no se ejecuta) y, mientras habla, sus movimientos de cola, orejas, cabeza y columna (formulas del script, amplitud de la cola decreciente, con rampa de entrada/salida de 4 f); la mandibula (`jaw_bot`) sigue la ENVOLVENTE DEL AUDIO (X -25 grados * nivel, como la voz de Jerry en el despertar) en lugar de los 4 ciclos fijos del script, para que quede sincronizada.
 f710-722  gira (smoothstep, 12 f) de 270 a 380 grados = hacia Alfred (rumbo -20 grados desde Jerry, a (-96.5,-108.5)); gira a la izquierda (el camino corto).
 f714-728  se sienta (smoothstep, 14 f): de la pose de pie a la `SITTING_POSE`; el root baja 0.187 m (sentado la malla flotaba 0.187 m sobre el suelo).
 f722-748  voz (START=720: frame 1 del clip = f720; voz f722-746) con los movimientos de habla.
 f748-824  sentado, quieto. f824-836 se levanta (smoothstep, 12 f) a su pose de pie para que la marcha (`caminar_estudio_alfred_y_jerry.py`, S_J=841) arranque desde de pie.
Audio: tira `VozJerry_sentado_*` volumen 3.0 (+9.5 dB; pico crudo 0.30, -26.2 dB RMS), `duck_todos` (los sonidos de la animacion solapados bajan a la mitad, `ducking_voces.py`).
Se ejecuta DENTRO de Blender con exec. Se puede repetir (quita sus claves en f709-837). Nunca `raise SystemExit`. Variables: T0 (710)."""
import bpy, ast, math, wave, traceback
from mathutils import Vector

try:
    sc = bpy.context.scene; ed = sc.sequence_editor
    ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
    cerca = lambda b, t: b + 2 * math.pi * round((t - b) / (2 * math.pi))
    T0 = int(globals().get("T0", 710)); TURN = (T0, T0 + 12); SIT = (T0 + 4, T0 + 18); START = T0 + 10; TALK = (START + 2, START + 28); STAND = (824, 836); DZ = -0.187; D2R = math.pi / 180
    SRC = "C:/Users/user/Desktop/Alfred_Animacion/audios/jerry/jerry_sentado_mira_alfred.hablar_original.py"; WAV = "C:/Users/user/Desktop/Alfred_Animacion/audios/jerry/jerry_sentado_mira_alfred.wav"
    SP = None
    for nd in ast.parse(open(SRC, encoding="utf-8").read()).body:
        if isinstance(nd, ast.Assign) and isinstance(nd.targets[0], ast.Name) and nd.targets[0].id == "SITTING_POSE": SP = eval(compile(ast.Expression(nd.value), "x", "eval"), {"math": math, "__builtins__": {}})
    JA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "scull_1" in o.pose.bones); EJ = bpy.data.objects["jerry"]
    HUESOS = list(SP.keys()) + ["jaw_bot"]
    for n in HUESOS: JA.pose.bones[n].rotation_mode = 'XYZ'
    fcs = lambda o: o.animation_data.action.layers[0].strips[0].channelbags[0].fcurves
    for o, solo in ((JA, True), (EJ, False)):                                               # limpiar claves propias anteriores
        for fc in fcs(o):
            if solo and not any('"%s"' % n in fc.data_path for n in HUESOS): continue
            for i in range(len(fc.keyframe_points) - 1, -1, -1):
                if T0 - 1 <= fc.keyframe_points[i].co.x <= STAND[1] + 1: fc.keyframe_points.remove(fc.keyframe_points[i])
    sc.frame_set(T0 - 1); BASE = {n: tuple(JA.pose.bones[n].rotation_euler) for n in HUESOS}; loc0 = Vector(EJ.location); rz0 = EJ.rotation_euler.z; rx, ry = EJ.rotation_euler.x, EJ.rotation_euler.y
    SP["jaw_bot"] = (0.0, 0.0, 0.0)
    # ---------- rumbo hacia Alfred ----------
    sc.frame_set(TURN[1]); AA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "Hips_alfred" in o.pose.bones)
    pr = AA.matrix_world @ AA.pose.bones["Rightknee_alfred"].tail; pl = AA.matrix_world @ AA.pose.bones["Leftknee_alfred"].tail
    bearing = math.degrees(math.atan2((pr.x + pl.x) / 2 - loc0.x, (pr.y + pl.y) / 2 - loc0.y)); rz_t = -bearing; rz_t = math.degrees(rz0) + (((rz_t - math.degrees(rz0)) + 180) % 360 - 180)
    print("Jerry rz", round(math.degrees(rz0), 1), "->", round(rz_t, 1), "(rumbo a Alfred", round(bearing, 1), ")")
    # ---------- envolvente del audio por frame del clip ----------
    w = wave.open(WAV); n = w.getnframes(); sr = w.getframerate(); raw = w.readframes(n); w.close()
    import array
    smp = array.array('h'); smp.frombytes(raw); hop = sr // 24; env = [max(abs(x) for x in smp[i:i + hop]) / 32768.0 for i in range(0, len(smp), hop)]; mx = max(env) or 1.0; LV = {k + 1: min(1.0, e / mx) for k, e in enumerate(env)}
    NT = TALK[1] - TALK[0] + 1
    def hablar(f, bone, base):                                                              # movimientos del script `hablar` sobre la pose sentada
        k = f - TALK[0] + 1
        if not (1 <= k <= NT): return base
        t = (k - 1) / max(1, NT - 1); e = ss(k / 4.0) * ss((NT - k + 1) / 4.0); sw = lambda p, a, ph=0.0: a * math.sin(2 * math.pi * k / p + ph) * e; amp = 1.0 - t * 0.6; v = list(base)
        if bone in ("tail_1", "tail_2", "tail_3"):
            i = int(bone[-1]) - 1; v[0] += sw(8, 0.08 * (i + 1) * amp); v[1] += sw(6, 0.15 * (i + 1) * amp, 0.5); v[2] += sw(10, 0.05 * (i + 1) * amp)
        elif bone in ("ear.L", "ear.R"):
            i = 0 if bone == "ear.L" else 1; v[1] += sw(7, 0.08, i * math.pi); v[2] += sw(9, 0.05, i * math.pi)
        elif bone == "scull": v[1] += sw(12, 0.02); v[2] += sw(15, 0.015)
        elif bone in ("spine_1", "spine_4"):
            i = 0 if bone == "spine_1" else 1; v[1] += sw(10, 0.015 * (i + 1)); v[2] += sw(14, 0.01 * (i + 1))
        elif bone == "jaw_top": v[0] += 0.05 * 25 * D2R * LV.get(k + TALK[0] - START, 0.0) * e
        elif bone == "jaw_bot": v[0] -= 25 * D2R * LV.get(k + TALK[0] - START, 0.0)
        return tuple(v)
    # ---------- claves ----------
    for f in range(T0 - 1, STAND[1] + 2):
        wt = ss((f - TURN[0]) / float(TURN[1] - TURN[0])); rz = math.radians(math.degrees(rz0) + (rz_t - math.degrees(rz0)) * wt)
        ws = ss((f - SIT[0]) / float(SIT[1] - SIT[0])) * (1 - ss((f - STAND[0]) / float(STAND[1] - STAND[0])))                       # 0 de pie -> 1 sentado
        EJ.location = Vector((loc0.x, loc0.y, loc0.z + DZ * ws)); EJ.rotation_euler = (rx, ry, rz); EJ.keyframe_insert("location", frame=f); EJ.keyframe_insert("rotation_euler", frame=f)
        if f % 1 == 0 and not ((SIT[1] + 2 < f < TALK[0] - 2) or (TALK[1] + 2 < f < STAND[0] - 2)):                                    # claves por frame en transiciones y habla; el resto, solo extremos
            for nm in HUESOS:
                b = BASE[nm]; tgt = tuple(cerca(SP[nm][c], b[c]) for c in range(3)); tgt = hablar(f, nm, tgt) if nm in SP else tgt
                if nm == "jaw_bot": tgt = hablar(f, nm, (b[0], 0.0, 0.0)) if TALK[0] <= f <= TALK[1] else (0.0, 0.0, 0.0)
                v = tuple(b[c] + (tgt[c] - b[c]) * ws for c in range(3)) if nm != "jaw_bot" else tuple(tgt)
                pb = JA.pose.bones[nm]; pb.rotation_euler = v
                for ax in range(3): pb.keyframe_insert("rotation_euler", index=ax, frame=f, group=nm)
        elif f in (SIT[1] + 2, TALK[1] + 2, STAND[0] - 2): pass
    # ---------- audio ----------
    def canal_libre(a, b):
        for ch in range(1, 129):
            if not any(t.channel == ch and t.frame_final_start < b and a < t.frame_final_end for t in ed.strips_all): return ch
        raise RuntimeError("sin canal libre")
    for s_ in [s_ for s_ in ed.strips_all if str(s_.get("guion_id", "")) == "voz6_jerry_sentado"]: ed.strips.remove(s_)
    s_ = ed.strips.new_sound(f"VozJerry_sentado_{START + 2}", WAV, canal_libre(START, START + 300), START); n_tot = int(s_.frame_final_duration)
    s_.frame_offset_start = 0; s_.frame_offset_end = 0; s_.volume = 3.0; s_["vol_base"] = 3.0; s_["duck_todos"] = True; s_["guion_id"] = "voz6_jerry_sentado"
    print(s_.name, "canal", s_.channel, "tira f", int(s_.frame_final_start), "-", int(s_.frame_final_end), "voz f", START + 2, "-", START + 26)
    exec(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\ducking_voces.py", encoding="utf-8").read(), {"__name__": "x", "DUCK": 0.5})
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == JA for m in o.modifiers)]; res = {}
    for f in (T0 - 1, T0 + 6, TURN[1], SIT[1], START + 10, TALK[1], 800, STAND[0] + 6, STAND[1], 840):
        sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); z = min(min((o.evaluated_get(dg).matrix_world @ v.co).z for v in o.evaluated_get(dg).to_mesh().vertices) for o in meshes[:1])
        res[f] = {"rz": round(math.degrees(EJ.rotation_euler.z), 1), "z_malla_min": round(z, 3), "jaw": round(math.degrees(JA.pose.bones["jaw_bot"].rotation_euler[0]), 1), "spine_6": round(math.degrees(JA.pose.bones["spine_6"].rotation_euler[0]), 1)}
    sc.frame_set(120); print(res); print("LISTO")
except Exception:
    traceback.print_exc()
