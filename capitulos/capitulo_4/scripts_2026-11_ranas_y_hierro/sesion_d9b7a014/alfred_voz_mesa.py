"""Respuesta de Alfred mientras saca la mesa de crafteo (f224): voz + ojos de sadsadasdas.py desplazados,
sin borrar las claves existentes (hide/Closed) de los ojos."""
import ast, bpy, math

SCRIPT = globals().get("SCRIPT", r"C:\Users\user\Downloads\sadsadasdas.py")
WAV = globals().get("WAV", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\voces_alfred\alfred_no_es_necesario.mp3")
O = globals().get("O", 158)   # 158: justo despues de la frase de Jerry (110-156)
SK = globals().get("SK", "Audio_procedural")      # una forma por audio: no cambia la de los audios anteriores
SN = globals().get("SN", "VozSync_alfred_no_es_necesario")
sc = bpy.context.scene
c = {}
for n in ast.parse(open(SCRIPT, encoding="utf-8").read()).body:
    if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
        try: c[n.targets[0].id] = ast.literal_eval(n.value)
        except Exception: pass
END = c["END_FRAME"]; G = lambda f: O + f - 1
PH = ((0.00, 0.00), (0.12, 0.00), (0.28, 0.70), (0.42, 1.08), (0.57, 0.92), (0.72, 1.02), (0.86, 0.48), (1.00, 0.00))


def ew(f):
    p = (f - 1) / max(1, END - 1)
    for i in range(len(PH) - 1):
        (a, va), (b, vb) = PH[i], PH[i + 1]
        if a <= p <= b: return va + (vb - va) * (p - a) / max(1e-6, b - a)
    return 0.0


speech = {int(f): float(l) for f, l in c["SPEECH_CURVE"]}
rep = {}
for ei, (name, coords) in enumerate(c["COORDINATES"].items()):
    eye = bpy.data.objects[name]
    if len(eye.data.vertices) != len(coords): raise RuntimeError("Topologia incompatible en " + name)
    kb = eye.data.shape_keys.key_blocks
    sh = kb.get(SK) or eye.shape_key_add(name=SK, from_mix=False)
    sh.slider_min, sh.slider_max = -2.0, 2.0
    for i, co in enumerate(coords): sh.data[i].co = co
    bl, bs, br = eye.location.copy(), eye.scale.copy(), eye.rotation_euler.copy()
    side = 1.0 if eye.matrix_world.translation.x > 0 else -1.0
    amt = 1.0 if ei == 0 else 0.86
    prev = 0.0
    for f in range(1, END + 1):
        w = ew(f); l = speech.get(f, 0.0); att = max(0.0, l - prev); prev = l
        wave = math.sin(f * 1.34 + ei * 0.16); st = wave * l
        sh.value = c["SHAPE_VALUE"] * w * amt; sh.keyframe_insert("value", frame=G(f))
        eye.location = bl.copy()
        eye.location.x += side * c["LATERAL"] * w * (1.0 if ei == 0 else -0.55)
        eye.location.z += c["VERTICAL"] * w * (1.0 if f < END * 0.60 else 0.65) + c["SPEECH_VERTICAL"] * l * wave * amt
        eye.scale = bs.copy()
        eye.scale.x *= (1.0 + (c["SCALE_X"] - 1.0) * w * amt) * (1.0 + c["SPEECH_SCALE_X"] * l - 0.040 * st)
        eye.scale.y *= 1.0 - 0.025 * l
        eye.scale.z *= (1.0 + (c["SCALE_Z"] - 1.0) * w * amt) * (1.0 + c["SPEECH_SCALE_Z"] * l + 0.065 * st + 0.025 * att)
        eye.rotation_euler = br.copy()
        eye.rotation_euler.y += side * c["ROTATION"] * w * amt + side * c["ATTACK_ROTATION"] * att * amt
        for p in ("location", "scale", "rotation_euler"): eye.keyframe_insert(p, frame=G(f))
    ck = kb.get("Closed")
    if ck:
        for cen in c["BLINK_CENTERS"]:
            for f, v in ((cen - 2, 0.0), (cen, 1.0), (cen + 2, 0.0)):
                ck.value = v; ck.keyframe_insert("value", frame=G(f))
    eye.location, eye.scale, eye.rotation_euler = bl, bs, br
    sh.value = 0.0
    rep[name] = len(coords)

ed = sc.sequence_editor
sn = SN
if sn in ed.strips_all: ed.strips.remove(ed.strips_all[sn])
s = ed.strips.new_sound(sn, WAV, 26, O); s["duck_todos"] = False
exec(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\ducking_voces.py", encoding="utf-8").read(), {"__name__": "x", "DUCK": 0.56})
result = {"ojos": rep, "voz": (s.frame_final_start, s.frame_final_end), "texto": c["TRANSCRIPT"]}
