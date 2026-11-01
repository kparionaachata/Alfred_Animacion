# -*- coding: utf-8 -*-
"""Parte 6, f120+: Jerry (que dormia en el pasto) empieza a moverse al despertarse y dice "si que se duerme bien aqui en el pasto, me levanto o no me levanto" (emocion: cansancio).
Audio `audios/jerry/jerry_se_duerme_bien_pasto.wav` (8.96 s = 215 f; voz en los frames 12-41, 95-133 y 167-201 del clip) y animacion `audios/jerry/jerry_se_duerme_bien_pasto.cara_original.py` (script de la app `estudio_audio_expresion`).
NO se ejecuta el script de la app (borra con `animation_data_clear()` las claves de los ojos de la escena: el sueno, `Closed`...): sus constantes se leen con `ast` y la expresion se SUMA a lo que Jerry ya anima (valor evaluado + delta por frame), sin tocar lo demas:
 - mandibula inferior `jaw_bot`: X -25 grados * nivel de voz (+ temblor Z, escala), hocico `jaw_top`, cabeza `scull`/`scull_1` (seguimiento leve), cejas `sejas_1_jerry`/`sejas_2_jerry` (pose de cansancio * 0.48 + oscilacion), ojos `Cansado` 0.82 / `Cerrado` 0.18 (*amplitud 0.88, escala/ubicacion de los ojos y pupilas desplazadas) en las 8 fases del script. El parpadeo del script se omite: Jerry tiene los ojos cerrados (`Closed` = 1) hasta f250 y su propia animacion de `Closed`.
 - El frame 1 del clip = f120 (cuando Jerry empieza a levantarse): la voz sale en f131-160, f214-252 y f286-320, en los huecos de los quejidos de Alfred (f165 y f207).
Audio: 2 tiras `VozJerry_despierta_*` (una por tramo de voz, recortadas a la voz +-2 f para que el ducking solo baje los sonidos del juego mientras Jerry habla), volumen 3.0 (+9.5 dB; la grabacion cruda es baja: pico 0.31, -29.3 dB RMS) y propiedad `duck_todos`: los sonidos de la animacion que se solapan bajan a la mitad (`ducking_voces.py`, DUCK 0.5).
Se ejecuta DENTRO de Blender con exec. GENERICO: variables START (120), TAG ("despierta"), ARCHIVO (base de `audios/jerry/<ARCHIVO>.wav` y `.cara_original.py`), VOL (3.0), CORTE. Segundo uso: "¡Ay, mi sombrero!" (sorpresa): START=595, TAG="sombrero", ARCHIVO="jerry_ay_mi_sombrero", VOL=2.6.
OJO: la animacion se SUMA al valor actual de cada canal, asi que NO se debe repetir sobre el mismo rango (se duplicaria el efecto); las tiras de audio si se rehacen. Nunca `raise SystemExit`."""
import bpy, ast, math, traceback
from mathutils import Vector

def canal_libre(ed, a, b):   # el VSE solo tiene 128 canales: busca uno sin tiras en [a, b] (new_sound desplaza la tira si el canal esta ocupado)
    for ch in range(1, 129):
        if not any(t.channel == ch and t.frame_final_start < b and a < t.frame_final_end for t in ed.strips_all): return ch
    raise RuntimeError('sin canal libre')
try:
    sc = bpy.context.scene; ed = sc.sequence_editor
    START = int(globals().get("START", 120)); VOL = float(globals().get("VOL", 3.0)); PAD = 2; TAG = globals().get("TAG", "despierta")
    BASE_AUD = "C:/Users/user/Desktop/Alfred_Animacion/audios/jerry/" + globals().get("ARCHIVO", "jerry_se_duerme_bien_pasto"); SRC = BASE_AUD + ".cara_original.py"; WAV = BASE_AUD + ".wav"
    tree = ast.parse(open(SRC, encoding="utf-8").read()); C = {}
    for nd in tree.body:
        if isinstance(nd, ast.Assign) and len(nd.targets) == 1 and isinstance(nd.targets[0], ast.Name) and nd.targets[0].id in ("COMPONENTS", "END_FRAME", "AMPLITUDE", "PUPIL_SHIFT", "EYE_SCALE", "SPEECH_CURVE", "BROW_BASE", "BROW_POSE", "BROW_POSE_STRENGTH", "phase_data", "GENERATED_EMOTION"):
            C[nd.targets[0].id] = ast.literal_eval(nd.value)
    CORTE = globals().get("CORTE", 160 if TAG == "despierta" else 10 ** 6)                  # "despierta": el tramo 3 ("me levanto o no me levanto", clip 167-201) se BORRO a peticion del usuario
    END = C["END_FRAME"]; SPEECH = {int(k): (float(v) if int(k) < CORTE else 0.0) for k, v in C["SPEECH_CURVE"]}; PH = C["phase_data"]; F = lambda k: START + k - 1; FIN = F(END)
    JA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "scull_1" in o.pose.bones)
    fcs = lambda o: o.animation_data.action.layers[0].strips[0].channelbags[0].fcurves
    HUESOS = ("jaw_bot", "jaw_top", "scull", "scull_1", "sejas_1_jerry", "sejas_2_jerry")
    for n in HUESOS: JA.pose.bones[n].rotation_mode = 'XYZ'
    # ---------- 1) valores base (lo que ya anima Jerry) por frame ----------
    BASE = {n: {} for n in HUESOS}
    for f in range(F(1), FIN + 1):
        sc.frame_set(f)
        for n in HUESOS:
            pb = JA.pose.bones[n]; BASE[n][f] = (Vector(pb.rotation_euler), Vector(pb.location), Vector(pb.scale))
    emo = lambda k: next((PH[i][1] + (PH[i + 1][1] - PH[i][1]) * ((((k - 1) / max(1, END - 1)) - PH[i][0]) / max(1e-6, PH[i + 1][0] - PH[i][0])) for i in range(len(PH) - 1) if PH[i][0] <= (k - 1) / max(1, END - 1) <= PH[i + 1][0]), 0.0)
    # ---------- 2) mandibula, hocico, cabeza, cejas (aditivo) ----------
    prev = 0.0
    for k in range(1, END + 1):
        f = F(k); lv = SPEECH.get(k, 0.0); att = max(0.0, lv - prev); prev = lv; w = emo(k)
        # jaw_bot
        r, l, s = BASE["jaw_bot"][f]; pb = JA.pose.bones["jaw_bot"]; pb.rotation_euler = (r.x - math.radians(25.0) * max(0.0, min(1.0, lv)), r.y, r.z + math.radians(0.45) * lv * math.sin(k * 0.73)); pb.scale = (s.x * (1 + 0.026 * lv), s.y * (1 - 0.010 * lv), s.z * (1 + 0.014 * lv))
        pb.keyframe_insert("rotation_euler", frame=f, group="jaw_bot"); pb.keyframe_insert("scale", frame=f, group="jaw_bot")
        # jaw_top
        r, l, s = BASE["jaw_top"][f]; pb = JA.pose.bones["jaw_top"]; pb.rotation_euler = (r.x - math.radians(3.0) * lv, r.y + math.radians(1.0) * att, r.z + math.radians(0.45) * lv * math.sin(k * 0.61)); pb.scale = (s.x * (1 + 0.035 * lv), s.y * (1 - 0.012 * lv), s.z * (1 + 0.020 * lv + 0.008 * att))
        pb.keyframe_insert("rotation_euler", frame=f, group="jaw_top"); pb.keyframe_insert("scale", frame=f, group="jaw_top")
        # cabeza
        for nm, fol in (("scull", 1.0), ("scull_1", 0.55)):
            r, l, s = BASE[nm][f]; pb = JA.pose.bones[nm]; pb.rotation_euler = (r.x + math.radians(1.15) * lv * fol, r.y + math.radians(0.55) * lv * math.sin(k * 0.19) * fol, r.z); pb.keyframe_insert("rotation_euler", frame=f, group=nm)
        # cejas: delta de la pose de cansancio respecto a su base del script
        for bi, nm in enumerate(("sejas_1_jerry", "sejas_2_jerry")):
            r, l, s = BASE[nm][f]; pb = JA.pose.bones[nm]; mix = min(1.0, w * C["BROW_POSE_STRENGTH"]); side = 1.0 if bi == 0 else -1.0; b0 = C["BROW_BASE"][nm]; p0 = C["BROW_POSE"][nm]
            dr = [(p0["euler"][a] - b0["euler"][a]) * mix for a in range(3)]; dl = [(p0["loc"][a] - b0["loc"][a]) * mix for a in range(3)]
            osc = math.radians(2.2) * math.sin(k * 0.27 + bi * 0.24) * max(w, lv)
            pb.rotation_euler = (r.x + dr[0] + math.radians(1.6) * lv * (1.0 if bi == 0 else 0.86), r.y + dr[1], r.z + dr[2] + side * osc); pb.location = (l.x + dl[0], l.y + dl[1], l.z + dl[2])
            pb.keyframe_insert("rotation_euler", frame=f, group=nm); pb.keyframe_insert("location", frame=f, group=nm)
    # ---------- 3) ojos y pupilas (expresion en las fases del script) ----------
    sc.frame_set(F(1))
    for ei, nm in enumerate(("ojo_izquierdo_jerry", "ojo_derecho_jerry")):
        eye = bpy.data.objects[nm]; blocks = eye.data.shape_keys.key_blocks; bs = eye.scale.copy(); bl = eye.location.copy(); delay = ei * max(1, int(END * 0.025)); asym = 1.0 if ei == 0 else 0.88
        for ph, wt in PH:
            f = F(min(END, max(1, 1 + round((END - 1) * ph) + (delay if 0.15 < ph < 0.86 else 0))))
            for name, cw in C["COMPONENTS"]:
                key = blocks.get(name)
                if key: key.value = C["AMPLITUDE"] * cw * wt * asym; key.keyframe_insert("value", frame=f)
            eye.scale = bs.copy(); eye.scale.x *= 1.0 + (C["EYE_SCALE"] - 1.0) * wt * asym; eye.scale.z *= 1.0 + (C["EYE_SCALE"] - 1.0) * wt * 0.55
            eye.location = bl.copy(); eye.location.z += 0.0025 * wt * (1.0 if ei == 0 else 0.72); eye.keyframe_insert("scale", frame=f); eye.keyframe_insert("location", frame=f)
    for pi_, nm in enumerate(("pupila_izquierda_jerry", "pupila_derecha_jerry")):
        pu = bpy.data.objects.get(nm)
        if pu is None: continue
        bl = pu.location.copy(); side = 1.0 if pi_ == 0 else -1.0
        for ph, wt in PH:
            f = F(min(END, max(1, 1 + round((END - 1) * ph)))); pu.location = bl.copy(); pu.location.x += side * C["PUPIL_SHIFT"] * wt; pu.location.z += C["PUPIL_SHIFT"] * 0.25 * wt; pu.keyframe_insert("location", frame=f)
    # ---------- 4) audio: una tira por tramo de voz (recortada), por encima de la animacion ----------
    for s_ in [s_ for s_ in ed.strips_all if str(s_.get("guion_id", "")).startswith("voz6_jerry_" + TAG)]: ed.strips.remove(s_)
    ks = sorted(k for k, v in SPEECH.items() if v > 0.02); segs = []
    for k in ks:
        if segs and k - segs[-1][1] <= 3: segs[-1][1] = k
        else: segs.append([k, k])
    n_tot = None
    for i, (a, b) in enumerate(segs):
        s_ = ed.strips.new_sound(f"VozJerry_{TAG}_{i + 1}_{F(a)}", WAV, canal_libre(ed, START, START + 300), START)
        if n_tot is None: n_tot = int(s_.frame_final_duration)
        s_.frame_offset_start = max(0, a - 1 - PAD); s_.frame_offset_end = max(0, n_tot - (b + PAD)); s_.volume = VOL; s_["vol_base"] = VOL; s_["duck_todos"] = True; s_["guion_id"] = f"voz6_jerry_{TAG}_{i + 1}"
        print(s_.name, "tira f", int(s_.frame_final_start), "-", int(s_.frame_final_end), "voz clip", a, "-", b, "(f", F(a), "-", F(b), ")")
    exec(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\ducking_voces.py", encoding="utf-8").read(), {"__name__": "x", "DUCK": 0.5})
    sc.frame_end = max(sc.frame_end, FIN)
    res = {}
    for f in (F(1), F(20), F(30), F(105), F(188), F(210), FIN):
        sc.frame_set(f); res[f] = {"jaw_bot": round(math.degrees(JA.pose.bones["jaw_bot"].rotation_euler[0]), 1), "Cansado": round(bpy.data.objects["ojo_izquierdo_jerry"].data.shape_keys.key_blocks["Cansado"].value, 2), "Closed": round(bpy.data.objects["ojo_izquierdo_jerry"].data.shape_keys.key_blocks["Closed"].value, 2)}
    sc.frame_set(120); print(res); print("LISTO")
except Exception:
    traceback.print_exc()
