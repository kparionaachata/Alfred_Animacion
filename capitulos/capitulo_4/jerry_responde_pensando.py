"""Jerry responde a Alfred ("Que raro, no recuerdo haberte dicho... Una arana!") despues de "Nada, no me ha dicho nada" (Alfred f708-744).
Reproduce el `animacion_jerry.py` de la app (resultados/20261021_001332_693902) como capas ADITIVAS desde F0, sin ejecutarlo
(el script de la app borra la animacion de los ojos y pone valores absolutos desde f1). Incluye la secuencia de emociones duda -> miedo.
Ademas: la mirada a Alfred (spine_1, pista Mirada_Jerry_a_Alfred_dialogo) se sostiene hasta el final de la escena y Jerry se lleva la
pata delantera derecha al menton mientras piensa (PATA_JSON = pierna de la pose del usuario `jerry/refinar/poses/pensando_A.json`).
Uso (Blender):  exec(open(r"...\\jerry_responde_pensando.py", encoding="utf8").read()); construir()
Repetible: borra sus pistas `VozJerry_que_raro*` / `Jerry_pata_menton` y su tira del VSE antes de ponerlas.
"""
import bpy, math, json, os, ast, importlib.util

F0 = 482                                   # inicio del audio de Jerry (Alfred termina su respuesta en 478)
SCRIPT_APP = r"C:/Users/user/Desktop/Alfred_Animacion/estudio_audio_expresion/resultados/20261021_001332_693902/animacion_jerry.py"
AUDIO = r"C:/Users/user/Desktop/Alfred_Animacion/audios/jerry/jerry_que_raro_arana.wav"
IMPORTADOR = r"C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/alfred_voz_sync/herramientas/importar_script_jerry.py"
PATA_JSON = r"C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/jerry_pata_menton_pose.json"
TAG = "VozJerry_que_raro"
RIG, OJOS, PUPILAS = "Dog_001_rig", ("ojo_izquierdo_jerry", "ojo_derecho_jerry"), ("pupila_izquierda_jerry", "pupila_derecha_jerry")
MIRADA_ACCION, MIRADA_FIN = "Jerry_mira_Alfred_dialogo", None     # None = hasta el final de la escena
# pata al menton: sube, piensa (con un leve frote) y baja al susto ("Una arana!", TRANSITION_FRAME del script)
PATA_SUBE = (F0 - 6, F0 + 8)
PATA_HUESOS = ("front_shoulder.R", "front_thigh.R", "front_shin.R", "front_foot.R")


def constantes():
    arbol = ast.parse(open(SCRIPT_APP, encoding="utf8").read()); c = {}
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and len(nodo.targets) == 1 and isinstance(nodo.targets[0], ast.Name):
            try: c[nodo.targets[0].id] = ast.literal_eval(nodo.value)
            except Exception: pass
    return c


def _importador():
    spec = importlib.util.spec_from_file_location("importar_script_jerry_local", IMPORTADOR)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def smooth(v):
    v = max(0.0, min(1.0, v)); return v * v * (3.0 - 2.0 * v)


def accion_aditiva(idb, nombre, canales, blend='ADD'):
    """canales {(data_path, index): [(frame, valor)]} -> accion + pista NLA (arriba de todo)."""
    ad = idb.animation_data or idb.animation_data_create()
    vieja = bpy.data.actions.get(nombre)
    if vieja: bpy.data.actions.remove(vieja)
    act = bpy.data.actions.new(nombre)
    slot = act.slots.new(idb.id_type, idb.name)
    cb = act.layers.new("Layer").strips.new(type='KEYFRAME').channelbags.new(slot)
    for (ruta, idx), claves in canales.items():
        fc = cb.fcurves.new(ruta, index=idx)
        fc.keyframe_points.add(len(claves))
        for kp, (f, v) in zip(fc.keyframe_points, claves): kp.co = (f, v); kp.interpolation = 'BEZIER'
        fc.update()
    tr = ad.nla_tracks.new(); tr.name = nombre
    st = tr.strips.new(nombre, int(act.frame_range[0]), act)
    st.blend_type = blend; st.extrapolation = 'NOTHING'
    try: st.action_slot = act.slots[0]
    except Exception: pass
    return tr, st


def quitar():
    ids = [bpy.data.objects.get(n) for n in (RIG,) + OJOS + PUPILAS]
    ids += [o.data.shape_keys for o in ids[1:] if o and o.data.shape_keys]
    for idb in ids:
        if idb is None or not idb.animation_data: continue
        for t in list(idb.animation_data.nla_tracks):
            if t.name.startswith(TAG) or t.name == "Jerry_pata_menton":
                acts = [s.action for s in t.strips if s.action]
                idb.animation_data.nla_tracks.remove(t)
                for a in acts:
                    if a.users == 0: bpy.data.actions.remove(a)
    ed = bpy.context.scene.sequence_editor
    if ed:
        for s in list(ed.strips_all):
            if s.name.startswith(TAG): ed.strips.remove(s)


def cara(c):
    """capas aditivas de la cara (ojos, pupilas, parpadeo, mandibula, hocico, cabeza, cejas) = el script de la app."""
    END = c["END_FRAME"]; fA = F0 - 1                            # frame 1 del script = F0
    fases = c["phase_data"] if "phase_data" in c else ((0, 0), (.12, 0), (.27, .68), (.43, 1.08), (.58, .93), (.73, 1.01), (.87, .42), (1, 0))
    seq = c.get("EMOTION_SEQUENCE"); TR = c.get("TRANSITION_FRAME", END)
    def pesos_seq(f):
        if not seq: return (1.0, 0.0)
        s = smooth((f - (TR - 4.0)) / 8.0); return (1.0 - s, s)
    def peso_emo(f):
        pos = (f - 1) / max(1, END - 1)
        for i in range(len(fases) - 1):
            (a, va), (b, vb) = fases[i], fases[i + 1]
            if a <= pos <= b: return va + (vb - va) * (pos - a) / max(1e-6, b - a)
        return 0.0
    imp = _importador(); parp = imp.parpadeos(1, END, c.get("BLINK_COUNT", 1), 9)      # [(frame, valor)] curva oficial 40/20/40
    rig = bpy.data.objects[RIG]
    sc = bpy.context.scene; f_act = sc.frame_current; sc.frame_set(F0)
    # ---- ojos
    for ei, on in enumerate(OJOS):
        ojo = bpy.data.objects[on]; bs, bl = ojo.scale.copy(), ojo.location.copy()
        delay = ei * max(1, int(END * 0.025)); asim = 1.0 if ei == 0 else 0.88
        cs, co = {}, {}
        for fase, w in fases:
            f = min(END, max(1, 1 + round((END - 1) * fase) + (delay if 0.15 < fase < 0.86 else 0)))
            if seq:
                w1, w2 = pesos_seq(f); tot = {}
                for nm, cw in c["SEQUENCE_COMPONENTS"][seq[0]]: tot[nm] = tot.get(nm, 0.0) + cw * w1
                for nm, cw in c["SEQUENCE_COMPONENTS"][seq[1]]: tot[nm] = tot.get(nm, 0.0) + cw * w2
            else: tot = dict(c["COMPONENTS"])
            for nm, cw in tot.items(): cs.setdefault((f'key_blocks["{nm}"].value', 0), []).append((fA + f, c["AMPLITUDE"] * cw * w * asim))
            co.setdefault(("scale", 0), []).append((fA + f, bs.x * (c["EYE_SCALE"] - 1.0) * w * asim))
            co.setdefault(("scale", 2), []).append((fA + f, bs.z * (c["EYE_SCALE"] - 1.0) * w * 0.55))
            co.setdefault(("location", 2), []).append((fA + f, 0.0025 * w * (1.0 if ei == 0 else 0.72)))
        cs[('key_blocks["Closed"].value', 0)] = [(fA + f, v) for f, v in parp]
        accion_aditiva(ojo.data.shape_keys, f"{TAG}_{on}_formas", cs)
        accion_aditiva(ojo, f"{TAG}_{on}_transform", co)
    # ---- pupilas
    for pi, pn in enumerate(PUPILAS):
        pu = bpy.data.objects.get(pn)
        if pu is None: continue
        lado = 1.0 if pi == 0 else -1.0; d = -1.0 if c["GENERATED_EMOTION"] == "enojo" else 1.0; co = {}
        for fase, w in fases:
            f = min(END, max(1, 1 + round((END - 1) * fase))); w1, w2 = pesos_seq(f)
            cant = (0.62 * w1 + 0.48 * w2) if seq else 1.0
            co.setdefault(("location", 0), []).append((fA + f, lado * c["PUPIL_SHIFT"] * w * d * cant))
            co.setdefault(("location", 2), []).append((fA + f, c["PUPIL_SHIFT"] * (0.18 * w1 + 0.32 * w2) * w))
        accion_aditiva(pu, f"{TAG}_{pn}_transform", co)
        if pu.data.shape_keys and "Closed" in pu.data.shape_keys.key_blocks:
            accion_aditiva(pu.data.shape_keys, f"{TAG}_{pn}_formas", {('key_blocks["Closed"].value', 0): [(fA + f, v) for f, v in parp]})
    # ---- huesos (deltas sobre lo que ya hace Jerry)
    habla = {int(f): float(v) for f, v in c["SPEECH_CURVE"]}; pico = c.get("SPEECH_PEAK", 1.0); norm = c.get("NORMALIZE_JAW_PEAK", True)
    jmax = math.radians(c.get("JAW_MAX_DEGREES", 25.0)); R = math.radians; ch = {}
    def k(b, ruta, i, f, v): ch.setdefault((f'pose.bones["{b}"].{ruta}', i), []).append((fA + f, v))
    prev = 0.0
    for f in range(1, END + 1):
        lv = habla.get(f, 0.0); jl = lv / pico if (norm and pico > 0) else lv; at = max(0.0, lv - prev)
        k("jaw_bot", "rotation_euler", 0, f, -jmax * max(0.0, min(1.0, jl))); k("jaw_bot", "rotation_euler", 2, f, R(0.45) * lv * math.sin(f * 0.73))
        k("jaw_bot", "scale", 0, f, 0.026 * lv); k("jaw_bot", "scale", 1, f, -0.010 * lv); k("jaw_bot", "scale", 2, f, 0.014 * lv)
        k("jaw_top", "rotation_euler", 0, f, -R(3.0) * lv); k("jaw_top", "rotation_euler", 1, f, R(1.0) * at); k("jaw_top", "rotation_euler", 2, f, R(0.45) * lv * math.sin(f * 0.61))
        k("jaw_top", "scale", 0, f, 0.035 * lv); k("jaw_top", "scale", 1, f, -0.012 * lv); k("jaw_top", "scale", 2, f, 0.020 * lv + 0.008 * at)
        for b, fo in (("scull", 1.0), ("scull_1", 0.55)):
            x = R(1.15) * lv * fo; z = 0.0
            if seq:
                rec = pesos_seq(f)[1] * peso_emo(f); x -= R(5.5) * rec * fo; z += R(1.8) * rec * fo
            k(b, "rotation_euler", 0, f, x); k(b, "rotation_euler", 1, f, R(0.55) * lv * math.sin(f * 0.19) * fo); k(b, "rotation_euler", 2, f, z)
        w = peso_emo(f)
        for bi, b in enumerate(("sejas_1_jerry", "sejas_2_jerry")):
            base = c["BROW_BASE"][b]; lado = 1.0 if bi == 0 else -1.0; e = [0.0] * 3; l = [0.0] * 3
            if seq:
                w1, w2 = pesos_seq(f); p1 = c["SEQUENCE_BROWS"][0]; p2 = c["SEQUENCE_BROWS"][1]
                m1 = w * w1 * p1["strength"]; m2 = w * w2 * p2["strength"]
                for a in range(3):
                    e[a] = (p1["pose"][b]["euler"][a] - base["euler"][a]) * m1 + (p2["pose"][b]["euler"][a] - base["euler"][a]) * m2
                    l[a] = (p1["pose"][b]["loc"][a] - base["loc"][a]) * m1 + (p2["pose"][b]["loc"][a] - base["loc"][a]) * m2
            else:
                mx = min(1.0, w * c["BROW_POSE_STRENGTH"])
                for a in range(3):
                    e[a] = (c["BROW_POSE"][b]["euler"][a] - base["euler"][a]) * mx; l[a] = (c["BROW_POSE"][b]["loc"][a] - base["loc"][a]) * mx
            e[2] += lado * R(2.2) * math.sin(f * 0.27 + bi * 0.24) * max(w, lv)
            e[0] += R(1.6) * lv * (1.0 if bi == 0 else 0.86)
            for a in range(3): k(b, "rotation_euler", a, f, e[a]); k(b, "location", a, f, l[a])
        prev = lv
    accion_aditiva(rig, f"{TAG}_rig", ch)
    for b in ("jaw_bot", "jaw_top", "scull", "scull_1", "sejas_1_jerry", "sejas_2_jerry"): rig.pose.bones[b].rotation_mode = 'XYZ'
    sc.frame_set(f_act)
    return END


def mirada_sostenida():
    """la pista de mirada (spine_1) sigue en -0.72 en vez de volver a 0 en f722."""
    sc = bpy.context.scene; rig = bpy.data.objects[RIG]; fin = MIRADA_FIN or sc.frame_end
    act = bpy.data.actions[MIRADA_ACCION]
    for lay in act.layers:
        for st in lay.strips:
            for cb in st.channelbags:
                for fc in cb.fcurves:
                    pts = sorted(fc.keyframe_points, key=lambda p: p.co[0]); hold = pts[-2].co[1] if len(pts) > 1 else pts[-1].co[1]
                    pts[-1].co = (fin, hold); pts[-1].handle_left = (fin - 4, hold); pts[-1].handle_right = (fin + 4, hold); fc.update()
    for t in rig.animation_data.nla_tracks:
        for s in t.strips:
            if s.action == act:
                s.action_frame_end = fin; s.frame_end = fin


def pata_menton(fin_habla, f_susto):
    """capa REPLACE de la pata delantera derecha con la pose de PATA_JSON (influencia: sube, piensa, baja al susto)."""
    if not os.path.isfile(PATA_JSON): return "falta " + PATA_JSON
    pose = json.load(open(PATA_JSON, encoding="utf8"))
    rig = bpy.data.objects[RIG]; ch = {}
    a0, a1 = PATA_SUBE; b0, b1 = f_susto, f_susto + 8
    claves_inf = [(a0, 0.0), (a1, 1.0), (b0, 1.0), (b1, 0.0)]
    for b in PATA_HUESOS:
        e = pose[b]
        for i in range(3):
            serie = []
            for f in range(a0, b1 + 1):
                v = e[i]
                if b == "front_foot.R" and i == 0:          # frote leve del menton mientras piensa
                    v += math.radians(6.0) * math.sin((f - a1) * 0.35) * (1.0 if a1 <= f <= b0 else 0.0)
                serie.append((f, v))
            ch[(f'pose.bones["{b}"].rotation_euler', i)] = serie
    tr, st = accion_aditiva(rig, "Jerry_pata_menton", ch, blend='REPLACE')
    st.use_animated_influence = True
    fc = st.fcurves.find("influence")
    for kp in list(fc.keyframe_points): fc.keyframe_points.remove(kp)
    for f, v in claves_inf:
        kp = fc.keyframe_points.insert(f, v); kp.interpolation = 'BEZIER'
    return "ok"


def audio():
    sc = bpy.context.scene; ed = sc.sequence_editor or sc.sequence_editor_create()
    canal = max([s.channel for s in ed.strips_all] + [0]) + 1
    s = ed.strips.new_sound(TAG + "_arana", AUDIO, min(canal, 128), F0)
    return (s.frame_final_start, s.frame_final_end)


GIRO_Z = -77.0                 # rotacion final del empty `jerry` (valor del usuario), en grados
GIRO_INI = F0 + 45             # "Una arana!": giro de alerta
GIRO_CURVA = ((0, 0.0), (2, -0.06), (5, 0.75), (7, 1.12), (10, 0.96), (13, 1.02), (16, 1.0))   # anticipo, golpe, sobrepaso y asentamiento


def giro_alerta():
    """el empty `jerry` (cuaterniones) gira de golpe como perro en alerta; claves por frame desde GIRO_INI."""
    from mathutils import Quaternion
    root = bpy.data.objects["jerry"]; root.rotation_mode = 'QUATERNION'
    act = root.animation_data.action; fcs = {}
    for lay in act.layers:
        for st in lay.strips:
            for cb in st.channelbags:
                for fc in cb.fcurves:
                    if fc.data_path == "rotation_quaternion": fcs[fc.array_index] = fc
    for fc in fcs.values():
        for kp in reversed(list(fc.keyframe_points)):
            if kp.co[0] > GIRO_INI - 1: fc.keyframe_points.remove(kp)
    q0 = Quaternion([fcs[i].evaluate(GIRO_INI) for i in range(4)])
    z0 = q0.to_euler().z; z1 = math.radians(GIRO_Z)
    def u(t):
        for (a, va), (b, vb) in zip(GIRO_CURVA, GIRO_CURVA[1:]):
            if a <= t <= b: s = (t - a) / (b - a); s = s * s * (3 - 2 * s); return va + (vb - va) * s
        return GIRO_CURVA[-1][1]
    for t in range(0, GIRO_CURVA[-1][0] + 1):
        q = Quaternion((0, 0, 1), z0 + (z1 - z0) * u(t))
        for i in range(4):
            kp = fcs[i].keyframe_points.insert(GIRO_INI + t, q[i]); kp.interpolation = 'LINEAR'
    return (GIRO_INI, GIRO_INI + GIRO_CURVA[-1][0], round(math.degrees(z0), 1), GIRO_Z)


ALERTA_JSON = r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/jerry/refinar/poses/posicion de alerta.json"
ALERTA_ENTRA = 8               # frames desde GIRO_INI hasta quedar en la pose de alerta


def alerta():
    """capa REPLACE con la pose de alerta del usuario (huesos que difieren de la animacion actual), entra con el giro y se sostiene."""
    rig = bpy.data.objects[RIG]; sc = bpy.context.scene
    pose = json.load(open(ALERTA_JSON, encoding="utf8"))["poses"][0]["bones"]
    for t in list(rig.animation_data.nla_tracks):
        if t.name == "Jerry_alerta":
            a = [s.action for s in t.strips]; rig.animation_data.nla_tracks.remove(t)
            for x in a:
                if x and x.users == 0: bpy.data.actions.remove(x)
    f_act = sc.frame_current; fin = sc.frame_end; sc.frame_set(fin)
    huesos = []
    for b, d in pose.items():
        e = [math.radians(d["raw_rotation_euler_deg"][a]) for a in "xyz"]
        if b in PATA_HUESOS or any(abs(e[i] - rig.pose.bones[b].rotation_euler[i]) > 1e-3 for i in range(3)): huesos.append((b, e))
    sc.frame_set(f_act)
    f0, f1 = GIRO_INI, GIRO_INI + ALERTA_ENTRA
    ch = {(f'pose.bones["{b}"].rotation_euler', i): [(f0, e[i]), (fin, e[i])] for b, e in huesos for i in range(3)}
    tr, st = accion_aditiva(rig, "Jerry_alerta", ch, blend='REPLACE')
    st.use_animated_influence = True; fc = st.fcurves.find("influence")
    for kp in list(fc.keyframe_points): fc.keyframe_points.remove(kp)
    for f, v in ((f0, 0.0), (f1, 1.0)): fc.keyframe_points.insert(f, v).interpolation = 'BEZIER'
    return [b for b, _ in huesos]


def construir():
    quitar()
    c = constantes(); END = cara(c)
    mirada_sostenida()
    f_susto = F0 - 1 + int(c.get("TRANSITION_FRAME", END)) - 4
    r = pata_menton(F0 - 1 + END, f_susto)
    a = audio()
    g = giro_alerta()
    al = alerta()
    return {"habla": (F0, F0 + END - 1), "susto": f_susto, "pata": r, "audio": a, "giro": g, "alerta": al}
