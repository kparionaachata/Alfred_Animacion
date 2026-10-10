# -*- coding: utf-8 -*-
"""Parte 6: FILTROS ORGANICOS y PARPADEOS de Alfred, Jerry y el Creeper en la escena viva (los estudios los aplican al CONCATENAR; aqui la parte 6 se construyo con scripts y no los tenia).
Filtros (formulas de `operators_anim._apply_organic_filters` de cada estudio, valores por omision de cada uno), SUMADOS por frame al valor que ya tiene cada canal (claves densas LINEAR en f1-1355 para Alfred/Jerry y f1035-1355 para el Creeper):
 - ALFRED (`_ORGANIC_DEFAULTS_REGLAS_ALFRED`): respiracion Spine/Spine1 X y Z (amp 0.040, vel 0.020, fase 1.97), micro-movimiento de cabeza Neck/face (amp 0.023, vel 0.079, semilla 693), micro-escala Z de Spine1 (0.010). (Desplazamiento de peso, noise de hombros y noise del root = desactivados en sus valores por omision.)
 - JERRY (`_ORGANIC_DEFAULTS_REGLAS_JERRY`): respiracion spine_1 (amp 0.05, vel 0.01), micro-movimiento (amp 0.008, vel 0.05, semilla 42; el estudio lo aplica a spine_1), micro-escala Z de spine_1 (0.005), noise de hombros front_shoulder.R/L (amp 0.006, vel 0.07, semilla 123), oscilacion de orejas ear.L/R en Z (amp 0.12, vel 0.06, fases 0 y 1.57) y oscilacion de cola tail_2 en Z (amp 0.524 x 0.35, vel 0.12) solo despierto y fuera de la marcha/huida. (El desplazamiento de peso usa el hueso `Dog_001_rig`, que no existe en este rig: se omite.)
 - CREEPER (valores por omision de su estudio): respiracion body/upperbody (amp 0.012, vel 0.08) y micro-movimiento de cabeza head/head.pos (amp 0.008, vel 0.05, semilla 42).
 NO se aplican "suavizar fcurves" ni "secondary motion de codos": reescriben las claves existentes (3 pasadas de suavizado borrarian los giros de 2 f, los golpes y los sustos aprobados).
Parpadeos (secuencia de 9 f: cerrado 0, .25, .5, .75, 1, 1, .75, .5, .25), uno cada 80-140 f con semilla fija, saltando las ventanas con animacion de ojos propia (voces): ALFRED desde f330 (dormido antes) con la forma `Closed` + ocultar los ojos los 2 f cerrados (como `generate_caminar`); JERRY desde f385 (sus parpadeos existentes terminan en f372) con `Closed` en ojos Y pupilas; CREEPER desde f1040 aplastando la escala Z de sus ojos (`Cube.001/002_creeper_1`; el .blend no tiene `ojo_*_creeper_1` con forma `Closed`), sin parpadear durante el intento de explosion (f1160-1220).
Repetible: los deltas aplicados se guardan en `organicos_delta.json` y se restan antes de volver a aplicar; los parpadeos creados se borran por su lista. Se ejecuta DENTRO de Blender con exec. Nunca `raise SystemExit`."""
import bpy, json, math, os, random, traceback
from mathutils import Vector

try:
    sc = bpy.context.scene
    DJ = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\organicos_delta.json"
    PREV = json.load(open(DJ, encoding="utf-8")) if os.path.exists(DJ) else {"canales": {}, "parpadeos": {}}; NEW = {"canales": {}, "parpadeos": {}}
    FIN = sc.frame_end
    ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
    def noise_at(frame, freq, seed, dim=0):
        v = math.sin(frame * freq * 1.3 + seed * 7.3 + dim * 3.7); v += math.sin(frame * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5; v += math.sin(frame * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25
        return v / 1.75
    def fcs(o): return o.animation_data.action.layers[0].strips[0].channelbags[0].fcurves
    def nuevo_fc(o, dp, axis, grupo):
        try: return fcs(o).new(dp, index=axis, group_name=grupo)
        except TypeError: return fcs(o).new(dp, index=axis, action_group=grupo)
    def aplicar(obj, dp, axis, grupo, f0, f1, deltas, base_static, clave):
        """suma deltas[f] al canal `dp[axis]` de `obj` en [f0, f1] como claves LINEAR por frame (restando antes el delta anterior de esta herramienta)"""
        fc = fcs(obj).find(dp, index=axis)
        if fc is None: fc = nuevo_fc(obj, dp, axis, grupo)
        prev = PREV["canales"].get(clave, {}); base = {}
        for f in range(f0, f1 + 1): base[f] = (fc.evaluate(f) if len(fc.keyframe_points) else base_static) - prev.get(str(f), 0.0)
        for i in range(len(fc.keyframe_points) - 1, -1, -1):
            if f0 <= fc.keyframe_points[i].co.x <= f1: fc.keyframe_points.remove(fc.keyframe_points[i])
        for f in range(f0, f1 + 1):
            kp = fc.keyframe_points.insert(f, base[f] + deltas[f - f0], options={'FAST'}); kp.interpolation = 'LINEAR'
        fc.update(); NEW["canales"][clave] = {str(f): deltas[f - f0] for f in range(f0, f1 + 1)}
    REG = {}                                                                                # (armature, hueso, canal, eje) -> [f0, f1, deltas acumulados]
    def _acum(arm, bone, tipo, axis, f0, f1, deltas):
        if arm.pose.bones.get(bone) is None: print("  (sin hueso)", bone); return
        k = (arm.name, bone, tipo, axis)
        if k in REG: REG[k][2] = [x + y for x, y in zip(REG[k][2], deltas)]
        else: REG[k] = [f0, f1, list(deltas), arm]
    def rot(arm, bone, axis, f0, f1, deltas): arm.pose.bones[bone].rotation_mode = 'XYZ'; _acum(arm, bone, "rot", axis, f0, f1, deltas)
    def esc(arm, bone, axis, f0, f1, deltas): _acum(arm, bone, "scale", axis, f0, f1, deltas)
    def volcar():
        for (an, bone, tipo, axis), (f0, f1, deltas, arm) in REG.items():
            pb = arm.pose.bones[bone]; dp = f'pose.bones["{bone}"].' + ("rotation_euler" if tipo == "rot" else "scale"); est = pb.rotation_euler[axis] if tipo == "rot" else pb.scale[axis]
            aplicar(arm, dp, axis, bone, f0, f1, deltas, est, f"{an}:{bone}:{tipo}:{axis}")
    AA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "Hips_alfred" in o.pose.bones); JA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "scull_1" in o.pose.bones); CA = bpy.data.objects["creeper.arma_creeper_1"]
    # ================= ALFRED =================
    F0, F1 = 1, FIN; fr = range(F0, F1 + 1)
    amp, sp, ph = 0.040, 0.020, 1.97
    for b in ("Spine_alfred", "Spine1_alfred"):
        rot(AA, b, 0, F0, F1, [amp * math.sin(f * sp * 2 * math.pi + ph) for f in fr]); rot(AA, b, 2, F0, F1, [amp * 0.4 * math.sin(f * sp * 2 * math.pi + ph + 1.2) for f in fr])
    for ax in range(3):
        d = [0.023 * noise_at(f, 0.079, 693, ax) for f in fr]
        for b in ("Neck_alfred", "face_alfred"): rot(AA, b, ax, F0, F1, d)
    esc(AA, "Spine1_alfred", 2, F0, F1, [0.010 * math.sin(f * sp * 2 * math.pi + ph) for f in fr])
    print("Alfred: filtros f%d-%d" % (F0, F1))
    # ================= JERRY =================
    amp, sp, ph = 0.05, 0.01, 0.0
    rot(JA, "spine_1", 0, F0, F1, [amp * math.sin(f * sp * 2 * math.pi + ph) for f in fr]); rot(JA, "spine_1", 2, F0, F1, [amp * 0.4 * math.sin(f * sp * 2 * math.pi + ph + 1.2) for f in fr])
    for ax in range(3): rot(JA, "spine_1", ax, F0, F1, [0.008 * noise_at(f, 0.05, 42, ax) for f in fr])   # micro-movimiento: el estudio de Jerry lo aplica a spine_1 (se suma a la respiracion en X y Z)
    esc(JA, "spine_1", 2, F0, F1, [0.005 * math.sin(f * 0.01 * 2 * math.pi) for f in fr])
    for ax in range(3):
        for b, off in (("front_shoulder.R", 0), ("front_shoulder.L", 17)): rot(JA, b, ax, F0, F1, [0.006 * noise_at(f, 0.07, 123 + off, ax) for f in fr])
    for b, fase in (("ear.L", 0.0), ("ear.R", 1.57)): rot(JA, b, 2, F0, F1, [0.12 * math.sin(f * 0.06 * 2 * math.pi + fase) for f in fr])
    def mascara_cola(f):                                                                    # despierto (desde f262) y fuera de la marcha (f841-938) y la huida (f1190-1260)
        m = ss((f - 262) / 12.0)
        for a, b in ((841, 938), (1190, 1260)): m *= 1 - (ss((f - (a - 6)) / 6.0) * (1 - ss((f - b) / 6.0)))
        return m
    rot(JA, "tail_2", 2, F0, F1, [0.524 * 0.35 * mascara_cola(f) * math.sin(f * 0.12 * 2 * math.pi) for f in fr])
    print("Jerry: filtros f%d-%d" % (F0, F1))
    # ================= CREEPER =================
    C0 = 1035; fc_ = range(C0, F1 + 1)
    amp, sp, ph = 0.012, 0.08, 0.0
    for b in ("body_creeper_1", "upperbody_creeper_1"):
        rot(CA, b, 0, C0, F1, [amp * math.sin(f * sp * 2 * math.pi + ph) for f in fc_]); rot(CA, b, 2, C0, F1, [amp * 0.4 * math.sin(f * sp * 2 * math.pi + ph + 1.2) for f in fc_])
    for ax in range(3):
        d = [0.008 * noise_at(f, 0.05, 42, ax) for f in fc_]
        for b in ("head_creeper_1", "head.pos_creeper_1"): rot(CA, b, ax, C0, F1, d)
    print("Creeper: filtros f%d-%d" % (C0, F1))
    volcar()
    # ================= PARPADEOS =================
    SEQ = [0.0, 0.25, 0.5, 0.75, 1.0, 1.0, 0.75, 0.5, 0.25]
    def horario(seed, inicio, fin, evitar, gap=(80, 140)):
        rng = random.Random(seed); f = inicio + rng.randint(5, 40); out = []
        while f + 10 < fin:
            if any(a - 12 <= f <= b + 12 for a, b in evitar): f += 6; continue
            out.append(f); f += rng.randint(*gap)
        return out
    def borrar_ventanas(clave_pers, objetos_fcurves):
        for s in PREV["parpadeos"].get(clave_pers, []):
            for o, filtro in objetos_fcurves:
                if o.animation_data and o.animation_data.action:
                    for fc in fcs(o):
                        if filtro(fc):
                            for i in range(len(fc.keyframe_points) - 1, -1, -1):
                                if s - 1 <= fc.keyframe_points[i].co.x <= s + 10: fc.keyframe_points.remove(fc.keyframe_points[i])
    # --- Alfred ---
    ojosA = [bpy.data.objects["ojo_izquierdo_alfred"], bpy.data.objects["ojo_derecho_alfred"]]
    borrar_ventanas("alfred", [(o, lambda fc: "Closed" in fc.data_path or fc.data_path.startswith("hide")) for o in ojosA] + [(o.data.shape_keys, lambda fc: "Closed" in fc.data_path) for o in ojosA])
    evitar_A = [(314, 360), (512, 578), (946, 1104), (1162, 1198)]; bA = horario(11, 330, FIN, evitar_A); NEW["parpadeos"]["alfred"] = bA
    for s in bA:
        for o in ojosA:
            ck = o.data.shape_keys.key_blocks["Closed"]
            ck.value = 0.0; ck.keyframe_insert("value", frame=s - 1); o.hide_viewport = False; o.hide_render = False; o.keyframe_insert("hide_viewport", frame=s - 1); o.keyframe_insert("hide_render", frame=s - 1)
            for i, v in enumerate(SEQ):
                ck.value = v; ck.keyframe_insert("value", frame=s + i); h = v >= 1.0; o.hide_viewport = h; o.hide_render = h; o.keyframe_insert("hide_viewport", frame=s + i); o.keyframe_insert("hide_render", frame=s + i)
            ck.value = 0.0; ck.keyframe_insert("value", frame=s + 9); o.hide_viewport = False; o.hide_render = False; o.keyframe_insert("hide_viewport", frame=s + 9); o.keyframe_insert("hide_render", frame=s + 9)
    for o in ojosA:
        for owner in (o, o.data.shape_keys):
            if owner.animation_data and owner.animation_data.action:
                for fc in fcs(owner):
                    for kp in fc.keyframe_points:
                        if any(s - 1 <= kp.co.x <= s + 9 for s in bA): kp.interpolation = 'CONSTANT' if fc.data_path.startswith("hide") else 'LINEAR'
    print("Alfred parpadea en", bA)
    # --- Jerry (ojos y pupilas) ---
    ojosJ = [bpy.data.objects[n] for n in ("ojo_izquierdo_jerry", "ojo_derecho_jerry", "pupila_izquierda_jerry", "pupila_derecha_jerry")]
    borrar_ventanas("jerry", [(o.data.shape_keys, lambda fc: "Closed" in fc.data_path) for o in ojosJ] + [(o, lambda fc: "Closed" in fc.data_path) for o in ojosJ])
    evitar_J = [(120, 375), (595, 620)]; bJ = horario(23, 385, FIN, evitar_J); NEW["parpadeos"]["jerry"] = bJ
    for s in bJ:
        for o in ojosJ:
            ck = o.data.shape_keys.key_blocks["Closed"]
            for i, v in enumerate(SEQ + [0.0]): ck.value = v; ck.keyframe_insert("value", frame=s + i)
    for o in ojosJ:
        for owner in (o, o.data.shape_keys):
            if owner.animation_data and owner.animation_data.action:
                for fc in fcs(owner):
                    for kp in fc.keyframe_points:
                        if any(s <= kp.co.x <= s + 9 for s in bJ): kp.interpolation = 'LINEAR'
    print("Jerry parpadea en", bJ)
    # --- Creeper (escala Z de sus ojos) ---
    ojosC = [bpy.data.objects["Cube.001_creeper_1"], bpy.data.objects["Cube.002_creeper_1"]]
    borrar_ventanas("creeper", [(o, lambda fc: fc.data_path == "scale" and fc.array_index == 2) for o in ojosC])
    bC = horario(37, 1040, FIN, [(1155, 1222)]); NEW["parpadeos"]["creeper"] = bC
    for o in ojosC:
        bz = o.scale[2]
        if o.animation_data is None or o.animation_data.action is None: o.keyframe_insert("scale", frame=1)
        for s in bC:
            o.scale[2] = bz; o.keyframe_insert("scale", index=2, frame=s - 1)
            for i, v in enumerate(SEQ): o.scale[2] = bz * (1 - 0.95 * v); o.keyframe_insert("scale", index=2, frame=s + i)
            o.scale[2] = bz; o.keyframe_insert("scale", index=2, frame=s + 9)
        o.scale[2] = bz
        for fc in fcs(o):
            if fc.data_path == "scale":
                for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    print("Creeper parpadea en", bC)
    json.dump(NEW, open(DJ, "w", encoding="utf-8"))
    chk = {}
    for f in (1, 300, 700, 1000, 1200):
        sc.frame_set(f); chk[f] = {"Spine1_A": round(math.degrees(AA.pose.bones["Spine1_alfred"].rotation_euler[0]), 2), "spine_1_J": round(math.degrees(JA.pose.bones["spine_1"].rotation_euler[0]), 2), "ear.L Z": round(math.degrees(JA.pose.bones["ear.L"].rotation_euler[2]), 2)}
    sc.frame_set(120); print(chk); print("LISTO")
except Exception:
    traceback.print_exc()
