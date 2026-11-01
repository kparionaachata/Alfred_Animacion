# -*- coding: utf-8 -*-
"""(copia para base(los 5 zombies subiendo).blend) EXPORTA las animaciones de Jerry de la PARTE 7 (escena viva) a archivos .py independientes en `codigos de animacion/jerry/`, uno por escena, con el formato de los demas (`PAYLOAD` + `execute_animation(start_frame, ...)`),
MAS los objetos con los que interactua (hacha y pico de madera que lanza con la cola, sombrero) empaquetados en `codigos de animacion/jerry/objetos/*.blend` (el .py los anade con `bpy.data.libraries.load` si faltan).
NO incluye hablar ni expresiones: ni voces, ni mandibula (`jaw_bot`/`jaw_top`), ni cejas (`sejas_*`), ni ojos y pupilas (expresiones, `Closed`, parpadeo), ni audio. Ademas se RESTA lo que las voces sumaron en la cabeza (acento de habla de `scull`/`scull_1`)
y los movimientos de cola/orejas/cabeza/columna de la animacion `hablar` al sentarse (formulas de `voz_jerry_despierta.py` y `jerry_se_voltea_y_se_sienta.py`).
Dos fases en la escena viva (el muestreo tarda): FASE="muestrear" con A, B (varias veces, datos en bpy.app.driver_namespace["JER_EXP"]) y FASE="escribir".
Los huesos o canales constantes en toda la escena van a `constantes` (el payload queda mucho mas chico)."""
import bpy, ast, json, math, os
from mathutils import Matrix, Vector, Euler, Quaternion

DEST = r"C:\Users\user\Desktop\Alfred_Animacion\codigos de animacion\jerry"; OBJ_DIR = os.path.join(DEST, "objetos")
ACC = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\jerry\refinar\docs"
FASE = globals().get("FASE", "muestrear"); sc = bpy.context.scene; ns = bpy.app.driver_namespace
JA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "scull_1" in o.pose.bones); EJ = JA.parent
EXCLUIR = {"jaw_bot", "jaw_top", "sejas_1_jerry", "sejas_2_jerry"}
PAQUETES = {}; MUNDO = {}; HIJO = set()
ESCENAS = [
    ("se_sienta_zombies_subiendo", 114, 126, "se sienta", []),
    ("sentado_jadeando_moviendo_la_cola_y_mirando_a_los_lados_zombies_subiendo", 127, 360, "sentado jadeando, moviendo la cola y mirando a los lados", []),
]
R5 = lambda v: round(float(v), 5); D2R = math.pi / 180
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))

if FASE == "muestrear":
    A, B = int(globals()["A"]), int(globals()["B"]); D = ns.setdefault("JER_EXP", {}); objs = sorted({o for e in ESCENAS for o in e[4]})
    for f in range(A, B + 1):
        sc.frame_set(f); bpy.context.view_layer.update(); fr = {"bones": {}, "root": [list(map(R5, EJ.location)), list(map(R5, EJ.rotation_euler))], "objs": {}}
        for b in JA.pose.bones:
            if b.name not in EXCLUIR: fr["bones"][b.name] = (list(map(R5, b.rotation_euler)), list(map(R5, b.location)), list(map(R5, b.scale)))
        for n in objs:
            o = bpy.data.objects[n]; h = [bool(o.hide_viewport), bool(o.hide_render)]
            if n in HIJO: fr["objs"][n] = {"hide": h}
            else:
                l, q, s = o.matrix_world.decompose(); fr["objs"][n] = {"loc": list(map(R5, l)), "quat": list(map(R5, q)), "scale": list(map(R5, s)), "hide": h}
        D[f] = fr
    sc.frame_set(1); print("muestreados f%d-%d; total en memoria: %d frames" % (A, B, len(D)))

elif FASE == "escribir":
    D = ns["JER_EXP"]; os.makedirs(DEST, exist_ok=True); os.makedirs(OBJ_DIR, exist_ok=True)
    # ---------- 1) paquetes de objetos (.blend) ----------
    for arch, nombres in PAQUETES.items():
        originales = [bpy.data.objects[n] for n in nombres]; copias = []; tmp = bpy.data.collections.new("__export_tmp"); sc.collection.children.link(tmp)
        try:
            for o in originales: o.name = o.name + "__orig"
            for o in originales:
                c = o.copy(); c.name = o.name[:-6]; c.animation_data_clear()
                for k in list(c.constraints): c.constraints.remove(k)
                c.parent = None; c.matrix_world = Matrix.Identity(4); tmp.objects.link(c); copias.append(c)
            bpy.data.libraries.write(os.path.join(OBJ_DIR, arch + ".blend"), set(copias), fake_user=True)
        finally:
            for c in copias: bpy.data.objects.remove(c, do_unlink=True)
            bpy.data.collections.remove(tmp)
            for o in originales: o.name = o.name[:-6]
        print("paquete", arch + ".blend", nombres)
    # ---------- 2) lo que sumaron las voces y la animacion `hablar` en la cabeza, cola, orejas y columna (para restarlo) ----------
    def curva(nombre, corte=10 ** 6):
        for nd in ast.parse(open(r"C:\Users\user\Desktop\Alfred_Animacion\audios\jerry\%s.cara_original.py" % nombre, encoding="utf-8").read()).body:
            if isinstance(nd, ast.Assign) and isinstance(nd.targets[0], ast.Name) and nd.targets[0].id == "SPEECH_CURVE": return {int(k): (float(v) if int(k) < corte else 0.0) for k, v in ast.literal_eval(nd.value)}
    def fin_de(nombre):
        for nd in ast.parse(open(r"C:\Users\user\Desktop\Alfred_Animacion\audios\jerry\%s.cara_original.py" % nombre, encoding="utf-8").read()).body:
            if isinstance(nd, ast.Assign) and isinstance(nd.targets[0], ast.Name) and nd.targets[0].id == "END_FRAME": return int(ast.literal_eval(nd.value))
    VOCES = []                                                                                  # parte 2: sin voces sumadas en la cabeza
    def acento(f, bone):                                                                       # delta (x, y, z) que sumaron las voces a `scull`/`scull_1`
        fol = 1.0 if bone == "scull" else 0.55 if bone == "scull_1" else None
        if fol is None: return (0.0, 0.0, 0.0)
        dx = dy = 0.0
        for start, cv, end in VOCES:
            k = f - start + 1
            if 1 <= k <= end: lv = cv.get(k, 0.0); dx += 1.15 * D2R * lv * fol; dy += 0.55 * D2R * lv * math.sin(k * 0.19) * fol
        return (dx, dy, 0.0)
    T0S = -10000; SITA, SITB, STA, STB = T0S + 4, T0S + 18, T0S + 100, T0S + 112; TALKA, TALKB = T0S + 12, T0S + 38; NT = TALKB - TALKA + 1   # (la animacion `hablar` sentado era solo de la parte 6)
    def habla_sentado(f, bone):                                                                # movimientos de cola/orejas/cabeza/columna de `hablar` (ya multiplicados por el peso de sentado)
        k = f - TALKA + 1
        if not (1 <= k <= NT): return (0.0, 0.0, 0.0)
        ws = ss((f - SITA) / float(SITB - SITA)) * (1 - ss((f - STA) / float(STB - STA))); t = (k - 1) / max(1, NT - 1); e = ss(k / 4.0) * ss((NT - k + 1) / 4.0); amp = 1 - t * 0.6
        sw = lambda p, a, ph=0.0: a * math.sin(2 * math.pi * k / p + ph) * e; d = [0.0, 0.0, 0.0]
        if bone in ("tail_1", "tail_2", "tail_3"): i = int(bone[-1]) - 1; d = [sw(8, 0.08 * (i + 1) * amp), sw(6, 0.15 * (i + 1) * amp, 0.5), sw(10, 0.05 * (i + 1) * amp)]
        elif bone in ("ear.L", "ear.R"): i = 0 if bone == "ear.L" else 1; d = [0.0, sw(7, 0.08, i * math.pi), sw(9, 0.05, i * math.pi)]
        elif bone == "scull": d = [0.0, sw(12, 0.02), sw(15, 0.015)]
        elif bone in ("spine_1", "spine_4"): i = 0 if bone == "spine_1" else 1; d = [0.0, sw(10, 0.015 * (i + 1)), sw(14, 0.01 * (i + 1))]
        return tuple(x * ws for x in d)
    # ---------- 3) un .py por escena ----------
    PLANTILLA = open(os.path.join(ACC, "plantilla_animacion_jerry.py.txt"), encoding="utf-8").read()
    for nombre, f0, f1, titulo, objs in ESCENAS:
        frames = list(range(f0, f1 + 1)); n = len(frames); bones = {}; const = {}
        for bn in D[f0]["bones"]:
            rot = []
            for f in frames:
                r = D[f]["bones"][bn][0]; a = acento(f, bn); h = habla_sentado(f, bn) if (SITA - 2 <= f <= STB + 2) else (0, 0, 0)
                rot.append([R5(r[i] - a[i] - h[i]) for i in range(3)])
            loc = [D[f]["bones"][bn][1] for f in frames]; esc = [D[f]["bones"][bn][2] for f in frames]
            for ch, vals in (("rotation_euler", rot), ("location", loc), ("scale", esc)):
                if max(abs(v[i] - vals[0][i]) for v in vals for i in range(3)) > 2e-5: bones.setdefault(bn, {})[ch] = vals
                else: const.setdefault(bn, {})[ch] = vals[0]
        payload = {"info": {"name": nombre + "_jerry", "frames": n, "fps": 24, "entity": "Jerry", "status": "sin aprobar", "fuente": "base(los 5 zombies subiendo) (escena viva) f%d-%d" % (f0, f1), "frame_original": f0, "descripcion": titulo, "objetos": objs,
                            "sin": "hablar ni expresiones (voz, mandibula, cejas, ojos, pupilas, parpadeo)"}, "bones": bones, "constantes": const,
                   "root": {"location": [D[f]["root"][0] for f in frames], "rotation_euler": [D[f]["root"][1] for f in frames]}, "objetos": {}}
        for on in objs:
            ds = [D[f]["objs"][on] for f in frames]; hide = [d["hide"] for d in ds]
            rec = {"tipo": "hijo" if on in HIJO else "mundo"}
            if on not in HIJO: rec.update({"archivo": "objetos/%s.blend" % MUNDO[on], "paquete": PAQUETES[MUNDO[on]], "location": [d["loc"] for d in ds], "rotation_quaternion": [d["quat"] for d in ds], "scale": [d["scale"] for d in ds]})
            if any(h != hide[0] for h in hide): rec["hide"] = hide
            else: rec["hide_const"] = hide[0]
            payload["objetos"][on] = rec
        txt = PLANTILLA.replace("@@TITULO@@", titulo).replace("@@NOMBRE@@", nombre).replace("@@F0@@", str(f0)).replace("@@F1@@", str(f1)).replace("@@N@@", str(n)).replace("@@DEST@@", DEST.replace("\\", "/")).replace("@@PAYLOAD@@", repr(payload))
        ruta = os.path.join(DEST, nombre + "_jerry.py"); open(ruta, "w", encoding="utf-8").write(txt); print("escrito", nombre + "_jerry.py", "%d KB" % (os.path.getsize(ruta) // 1024), "huesos animados:", len(bones), "constantes:", len(const), "objetos:", objs)
    sc.frame_set(1); print("LISTO")
