"""Voces de Jerry mientras sube (salto 412-426) + rostro (animacion_jerry.py / _1.py desplazados).
No borra nada existente: ojos/pupilas reciben claves nuevas en sus acciones; el rig recibe una pista NLA ADD."""
import ast, bpy, importlib, math, sys

sys.path.insert(0, r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\jerry\refinar")
es = importlib.import_module("jerry_animation_studio.eye_system")
VOZ = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\voces_jerry"
CLIPS = [(r"C:\Users\user\AppData\Local\Temp\claude\d0772e74e53e6fa2\9fac7356-8ced-4d1a-a12c-3247350383c7\scratchpad\animacion_jerry_comodo.py", VOZ + r"\jerry_no_me_parece_comodo.wav", 625)]
NOMBRES = ["no_me_parece_comodo"]
LOOK = {}
SCULL = {}
PHASES = ((0.00, 0.00), (0.12, 0.00), (0.27, 0.68), (0.43, 1.08), (0.58, 0.93), (0.73, 1.01), (0.87, 0.42), (1.00, 0.00))
sc = bpy.context.scene
rig = bpy.data.objects["Dog_001_rig"]
eyes = [bpy.data.objects["ojo_izquierdo_jerry"], bpy.data.objects["ojo_derecho_jerry"]]
pupils = [bpy.data.objects["pupila_izquierda_jerry"], bpy.data.objects["pupila_derecha_jerry"]]


def leer(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    c, s = {}, {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
            try: c[n.targets[0].id] = ast.literal_eval(n.value)
            except Exception: pass
        if isinstance(n, ast.ClassDef) and n.name == "Settings":
            for m in n.body:
                if isinstance(m, ast.Assign): s[m.targets[0].id] = ast.literal_eval(m.value)
    c["Settings"] = type("Settings", (), s)()
    return c


def emotion_weight(f, end):
    p = (f - 1) / max(1, end - 1)
    for i in range(len(PHASES) - 1):
        (a, va), (b, vb) = PHASES[i], PHASES[i + 1]
        if a <= p <= b: return va + (vb - va) * (p - a) / max(1e-6, b - a)
    return 0.0


clips = [leer(p) for p, _, _ in CLIPS]

# --- shape keys de expresion en los ojos (se conservan Basis y Closed) ---
st = clips[0]["Settings"]
for eye in eyes:
    es._eye_ensure_subdivided(eye, st.subdivide_cuts)
    kb = eye.data.shape_keys.key_blocks
    base = [v.co.copy() for v in kb["Basis"].data]
    xs, ys, zs = [v.x for v in base], [v.y for v in base], [v.z for v in base]
    bounds = {"cx": (max(xs) + min(xs)) / 2, "cy": (max(ys) + min(ys)) / 2, "cz": (max(zs) + min(zs)) / 2,
              "rx": max(xs) - min(xs), "ry": max(ys) - min(ys), "rz": max(zs) - min(zs)}
    h, v, _ = es._eye_detect_axes(eye)
    for ex in ["feliz", "triste", "enojado", "sospecha", "cerrado", "cansado", "sorpresa"]:
        k = kb.get(ex.capitalize()) or eye.shape_key_add(name=ex.capitalize(), from_mix=False)
        k.slider_min, k.slider_max, k.value = -2.0, 2.0, 0.0
        for i, o in enumerate(base): k.data[i].co = es._eye_compute_vertex(o, h, v, bounds, ex, st)
eye_base = [(e.location.copy(), e.scale.copy()) for e in eyes]
pup_base = [p.location.copy() for p in pupils]

# --- rig: accion aditiva ---
nombre = "jerry_voz_comodo_rostro_arm"
old = bpy.data.actions.get(nombre)
for t in list(rig.animation_data.nla_tracks):
    if t.name == "Jerry_voz_comodo": rig.animation_data.nla_tracks.remove(t)
if old: bpy.data.actions.remove(old)
act = bpy.data.actions.new(nombre)
rig.animation_data.action = act
pb = rig.pose.bones
for b in ("jaw_bot", "jaw_top", "scull", "scull_1", "sejas_1_jerry", "sejas_2_jerry"): pb[b].rotation_mode = "XYZ"
keep_pose = {b.name: (b.rotation_euler.copy(), b.location.copy(), b.scale.copy()) for b in pb}


def key(b, rot=None, loc=None, scl=None, f=0):
    bone = pb[b]
    if rot is not None: bone.rotation_euler = rot; bone.keyframe_insert("rotation_euler", frame=f)
    if loc is not None: bone.location = loc; bone.keyframe_insert("location", frame=f)
    if scl is not None: bone.scale = scl; bone.keyframe_insert("scale", frame=f)


for c, (_, wav, O) in zip(clips, CLIPS):
    END = c["END_FRAME"]; G = lambda f: O + f - 1
    speech = {int(f): float(l) for f, l in c["SPEECH_CURVE"]}
    # ojos: expresion + escala/posicion
    for ei, eye in enumerate(eyes):
        kb = eye.data.shape_keys.key_blocks
        delay = ei * max(1, int(END * 0.025)); asym = 1.0 if ei == 0 else 0.88
        bl, bs = eye_base[ei]
        for ph, w in PHASES:
            f = min(END, max(1, 1 + round((END - 1) * ph) + (delay if 0.15 < ph < 0.86 else 0)))
            tot = {}
            for n, cw in c["COMPONENTS"]: tot[n] = tot.get(n, 0.0) + cw
            for n in ("Feliz", "Triste", "Enojado", "Sospecha", "Sorpresa"):
                kb[n].value = c["AMPLITUDE"] * tot.get(n, 0.0) * w * asym
                kb[n].keyframe_insert("value", frame=G(f))
            eye.scale = bs.copy()
            eye.scale.x *= 1.0 + (c["EYE_SCALE"] - 1.0) * w * asym
            eye.scale.z *= 1.0 + (c["EYE_SCALE"] - 1.0) * w * 0.55
            eye.location = bl.copy(); eye.location.z += 0.0025 * w * (1.0 if ei == 0 else 0.72)
            eye.keyframe_insert("scale", frame=G(f)); eye.keyframe_insert("location", frame=G(f))
    for pi, pup in enumerate(pupils):
        side = 1.0 if pi == 0 else -1.0
        for ph, w in PHASES:
            f = min(END, max(1, 1 + round((END - 1) * ph)))
            pup.location = pup_base[pi].copy()
            pup.location.x += side * c["PUPIL_SHIFT"] * w
            pup.location.z += c["PUPIL_SHIFT"] * 0.18 * w
            pup.keyframe_insert("location", frame=G(f))
    # parpadeo (curva oficial 40/20/40, 9 frames) sobre la curva Closed existente
    bmap, anchors = es._build_blink_map(G(1), G(END), c["BLINK_COUNT"], 9)
    for o in eyes + pupils:
        ck = o.data.shape_keys.key_blocks["Closed"]
        for f in sorted(set(bmap) | anchors):
            ck.value = bmap.get(f, 0.0); ck.keyframe_insert("value", frame=f)
    # rig (valores delta, la pista suma)
    prev = 0.0
    for f in range(1, END + 1):
        l = speech.get(f, 0.0); w = emotion_weight(f, END); att = max(0.0, l - prev); prev = l
        jl = max(0.0, min(1.0, l / c["SPEECH_PEAK"] if c["NORMALIZE_JAW_PEAK"] and c["SPEECH_PEAK"] > 0 else l))
        key("jaw_bot", rot=(-math.radians(c["JAW_MAX_DEGREES"]) * jl, 0, math.radians(0.45) * l * math.sin(f * 0.73)),
            scl=(0.026 * l, -0.010 * l, 0.014 * l), f=G(f))
        key("jaw_top", rot=(-math.radians(3.0) * l, math.radians(1.0) * att, math.radians(0.45) * l * math.sin(f * 0.61)),
            scl=(0.035 * l, -0.012 * l, 0.020 * l + 0.008 * att), f=G(f))
        for b, fo in (("scull", 1.0), ("scull_1", 0.55)):
            r = (math.radians(1.15) * l * fo, math.radians(0.55) * l * math.sin(f * 0.19) * fo, 0)
            if b == "scull": SCULL[G(f)] = r
            key(b, rot=r, f=G(f))
        for bi, b in enumerate(("sejas_1_jerry", "sejas_2_jerry")):
            bd, pd = c["BROW_BASE"][b], c["BROW_POSE"][b]; side = 1.0 if bi == 0 else -1.0
            mix = min(1.0, w * c["BROW_POSE_STRENGTH"])
            r = [(pd["euler"][a] - bd["euler"][a]) * mix for a in range(3)]
            r[2] += side * math.radians(2.2) * math.sin(f * 0.27 + bi * 0.24) * max(w, l)
            r[0] += math.radians(1.6) * l * (1.0 if bi == 0 else 0.86)
            key(b, rot=r, loc=[(pd["loc"][a] - bd["loc"][a]) * mix for a in range(3)], f=G(f))
    # voz
    sn = "VozSync_jerry_" + NOMBRES[[x[2] for x in CLIPS].index(O)]
    ed = sc.sequence_editor
    if sn in ed.strips_all: ed.strips.remove(ed.strips_all[sn])
    s = ed.strips.new_sound(sn, wav, 25, O); s["duck_todos"] = False

for f, d in LOOK.items():
    r = SCULL.get(f, (0.0, 0.0, 0.0))
    key("scull", rot=(r[0] + d[0], r[1] + d[1], r[2] + d[2]), f=f)

# restaurar ojos/pupilas en reposo y pasar la accion a una pista NLA ADD
for e, (l, s) in zip(eyes, eye_base): e.location, e.scale = l, s
for p, l in zip(pupils, pup_base): p.location = l
slot = rig.animation_data.action_slot
rig.animation_data.action = None
for n, (r, l, s) in keep_pose.items(): pb[n].rotation_euler, pb[n].location, pb[n].scale = r, l, s
tr = rig.animation_data.nla_tracks.new(); tr.name = "Jerry_voz_comodo"
fs = int(act.frame_range[0])
strip = tr.strips.new(nombre, fs, act)
if slot: strip.action_slot = slot
strip.blend_type = "ADD"; strip.extrapolation = "NOTHING"

DUCK = 0.56
exec(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\ducking_voces.py", encoding="utf-8").read(), {"__name__": "x", "DUCK": DUCK})
result = {"strip": (strip.frame_start, strip.frame_end),
          "voces": [(s.name, s.frame_final_start, s.frame_final_end) for s in sc.sequence_editor.strips_all if s.name.startswith("VozSync_jerry_no_me")]}
