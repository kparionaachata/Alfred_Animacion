# -*- coding: utf-8 -*-
"""Parte 7: FILTROS ORGANICOS de cada personaje (Alfred, Jerry, Creeper y Pollo) y PARPADEOS de Alfred y de Jerry en la escena viva (los estudios los aplican al CONCATENAR; la parte 7 se construyo con scripts y no los tenia). Mismo metodo que
`docs/acciones/filtros_organicos_y_parpadeos.py` (parte 6): deltas aditivos por frame SUMADOS al valor que ya tiene cada canal, como claves LINEAR por frame; formulas de `_apply_organic_filters` de cada estudio con sus valores por omision:
 - ALFRED (f131-frame_end; antes esta oculto): respiracion Spine/Spine1 X y Z (amp 0.040, vel 0.020, fase 1.97), micro-movimiento de cabeza Neck/face (amp 0.023, vel 0.079, semilla 693), micro-escala Z de Spine1 (0.010).
 - JERRY (f1-frame_end): respiracion spine_1 (amp 0.05, vel 0.01), micro-movimiento de spine_1 (0.008, 0.05, semilla 42), micro-escala Z de spine_1 (0.005), noise de hombros front_shoulder.R/L (0.006, 0.07, semilla 123), orejas ear.L/R en Z (0.12, vel 0.06, fases 0 y 1.57)
   y cola tail_2 en Z (0.524 x 0.35, vel 0.12) SOLO cuando esta tranquilo: no corriendo, saltando ni tumbado (ventanas MASCARA_COLA).
 - CREERPER (f300-frame_end; empieza a andar en f300): respiracion body/upperbody (0.012, 0.08) y micro-movimiento de head/head.pos (0.008, 0.05, semilla 42).
 - POLLO (f1-frame_end): respiracion Spine1_M/Chest_M X y Z (0.012, 0.08) y micro-movimiento de Head_M/Jaw_M (0.008, 0.05, semilla 42) (el aleteo, el suavizado de fcurves y el follow-through del estudio NO se aplican: borran/duplican movimientos de la parte 7).
Parpadeos (secuencia de 9 f: cerrado 0, .25, .5, .75, 1, 1, .75, .5, .25), uno cada 80-140 f con semilla fija: ALFRED desde f140 (saltando f135-300: dice "espera Jerry" y se queja del tobillo con sus propios parpadeos) con la forma `Closed` + ocultar los ojos los 2 f cerrados (como `generate_caminar`); JERRY desde f6 (saltando f16-97, donde dice "corre, corre...") con `Closed` en ojos Y pupilas.
(El creeper y el pollo NO parpadean.)  Repetible: los deltas se guardan en `organicos_delta_parte7.json` y se restan antes de volver a aplicar. IMPORTANTE: si se vuelve a ejecutar un script de ANIMACION de un personaje (que reescribe sus claves),
ejecutar ANTES este script con `QUITAR = True` (resta los deltas y borra los parpadeos), y DESPUES con QUITAR = False. Se ejecuta DENTRO de Blender con exec (~15 s; si da timeout por MCP, desde `bpy.app.timers.register`)."""
import bpy, json, math, os, random, traceback

try:
    sc = bpy.context.scene
    DJ = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\parte7\organicos_delta_parte7.json"
    QUITAR = bool(globals().get('QUITAR', False))
    PREV = json.load(open(DJ, encoding="utf-8")) if os.path.exists(DJ) else {"canales": {}, "parpadeos": {}}; NEW = {"canales": {}, "parpadeos": {}}
    FIN = sc.frame_end
    ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
    def noise_at(frame, freq, seed, dim=0):
        v = math.sin(frame * freq * 1.3 + seed * 7.3 + dim * 3.7); v += math.sin(frame * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5; v += math.sin(frame * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25
        return v / 1.75
    def fcs(o): return [fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]
    def bolsa(o): return o.animation_data.action.layers[0].strips[0].channelbags[0].fcurves
    def buscar(o, dp, axis):
        for fc in fcs(o):
            if fc.data_path == dp and fc.array_index == axis: return fc
    def nuevo_fc(o, dp, axis, grupo):
        try: return bolsa(o).new(dp, index=axis, group_name=grupo)
        except TypeError: return bolsa(o).new(dp, index=axis, action_group=grupo)
    def aplicar(obj, dp, axis, grupo, f0, f1, deltas, base_static, clave):
        """suma deltas[f] al canal `dp[axis]` de `obj` en [f0, f1] como claves LINEAR por frame (restando antes el delta anterior de esta herramienta)"""
        fc = buscar(obj, dp, axis)
        if fc is None: fc = nuevo_fc(obj, dp, axis, grupo)
        prev = PREV["canales"].get(clave, {}); base = {}
        for f in range(f0, f1 + 1): base[f] = (fc.evaluate(f) if len(fc.keyframe_points) else base_static) - prev.get(str(f), 0.0)
        for i in range(len(fc.keyframe_points) - 1, -1, -1):
            if f0 <= fc.keyframe_points[i].co.x <= f1: fc.keyframe_points.remove(fc.keyframe_points[i])
        for f in range(f0, f1 + 1):
            kp = fc.keyframe_points.insert(f, base[f] + deltas[f - f0], options={'FAST'}); kp.interpolation = 'LINEAR'
        fc.update(); NEW["canales"][clave] = {str(f): deltas[f - f0] for f in range(f0, f1 + 1)}
    REG = {}                                                                                # (armature, hueso, canal, eje) -> [f0, f1, deltas acumulados, armature]
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
    AA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "Hips_alfred" in o.pose.bones); JA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "scull_1" in o.pose.bones)
    CA = bpy.data.objects["creeper.arma_creeper_1"]; PA = bpy.data.objects["Armature_chicken_1"]

    if QUITAR:                                                                              # restar los deltas anteriores y borrar los parpadeos (antes de regenerar animaciones)
        for clave, d in PREV["canales"].items():
            an, bone, tipo, axis = clave.split(":"); arm = bpy.data.objects[an]; fr_ = sorted(int(x) for x in d); f0, f1 = fr_[0], fr_[-1]
            dp = f'pose.bones["{bone}"].' + ("rotation_euler" if tipo == "rot" else "scale"); aplicar(arm, dp, int(axis), bone, f0, f1, [0.0] * (f1 - f0 + 1), 0.0, clave)
        NEW["canales"] = {}
    else:
        # ================= ALFRED =================
        F0, F1 = 131, FIN; fr = range(F0, F1 + 1)
        amp, sp, ph = 0.040, 0.020, 1.97
        for b in ("Spine_alfred", "Spine1_alfred"):
            rot(AA, b, 0, F0, F1, [amp * math.sin(f * sp * 2 * math.pi + ph) for f in fr]); rot(AA, b, 2, F0, F1, [amp * 0.4 * math.sin(f * sp * 2 * math.pi + ph + 1.2) for f in fr])
        for ax in range(3):
            d = [0.023 * noise_at(f, 0.079, 693, ax) for f in fr]
            for b in ("Neck_alfred", "face_alfred"): rot(AA, b, ax, F0, F1, d)
        esc(AA, "Spine1_alfred", 2, F0, F1, [0.010 * math.sin(f * sp * 2 * math.pi + ph) for f in fr])
        # ================= JERRY =================
        F0, F1 = 1, FIN; fr = range(F0, F1 + 1)
        amp, sp, ph = 0.05, 0.01, 0.0
        rot(JA, "spine_1", 0, F0, F1, [amp * math.sin(f * sp * 2 * math.pi + ph) for f in fr]); rot(JA, "spine_1", 2, F0, F1, [amp * 0.4 * math.sin(f * sp * 2 * math.pi + ph + 1.2) for f in fr])
        for ax in range(3): rot(JA, "spine_1", ax, F0, F1, [0.008 * noise_at(f, 0.05, 42, ax) for f in fr])
        esc(JA, "spine_1", 2, F0, F1, [0.005 * math.sin(f * 0.01 * 2 * math.pi) for f in fr])
        for ax in range(3):
            for b, off in (("front_shoulder.R", 0), ("front_shoulder.L", 17)): rot(JA, b, ax, F0, F1, [0.006 * noise_at(f, 0.07, 123 + off, ax) for f in fr])
        for b, fase in (("ear.L", 0.0), ("ear.R", 1.57)): rot(JA, b, 2, F0, F1, [0.12 * math.sin(f * 0.06 * 2 * math.pi + fase) for f in fr])
        MASCARA_COLA = [(152, 205), (311, 381), (544, 567), (667, 670), (752, FIN)]         # tranquilo: esperando en el punto 20, sentado mirando a Alfred, de pie tras levantarse, quieto antes del susto y al final
        def mascara_cola(f):
            return max(ss((f - (a - 6)) / 6.0) * (1 - ss((f - b) / 6.0)) for a, b in MASCARA_COLA)
        rot(JA, "tail_2", 2, F0, F1, [0.524 * 0.35 * mascara_cola(f) * math.sin(f * 0.12 * 2 * math.pi) for f in fr])
        # ================= CREEPER =================
        C0 = 300; F1 = FIN; fc_ = range(C0, F1 + 1)
        amp, sp, ph = 0.012, 0.08, 0.0
        for b in ("body_creeper_1", "upperbody_creeper_1"):
            rot(CA, b, 0, C0, F1, [amp * math.sin(f * sp * 2 * math.pi + ph) for f in fc_]); rot(CA, b, 2, C0, F1, [amp * 0.4 * math.sin(f * sp * 2 * math.pi + ph + 1.2) for f in fc_])
        for ax in range(3):
            d = [0.008 * noise_at(f, 0.05, 42, ax) for f in fc_]
            for b in ("head_creeper_1", "head.pos_creeper_1"): rot(CA, b, ax, C0, F1, d)
        # ================= POLLO =================
        F0 = 1; fr = range(F0, F1 + 1)
        amp, sp, ph = 0.012, 0.08, 0.0
        for b in ("Spine1_M_chicken_1", "Chest_M_chicken_1"):
            rot(PA, b, 0, F0, F1, [amp * math.sin(f * sp * 2 * math.pi + ph) for f in fr]); rot(PA, b, 2, F0, F1, [amp * 0.4 * math.sin(f * sp * 2 * math.pi + ph + 1.2) for f in fr])
        for ax in range(3):
            d = [0.008 * noise_at(f, 0.05, 42, ax) for f in fr]
            for b in ("Head_M_chicken_1", "Jaw_M_chicken_1"): rot(PA, b, ax, F0, F1, d)
        volcar()
        print("Filtros organicos: Alfred f131-%d, Jerry f1-%d, Creeper f300-%d, Pollo f1-%d (%d canales)" % (FIN, FIN, FIN, FIN, len(REG)))
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
    ojosA = [bpy.data.objects["ojo_izquierdo_alfred"], bpy.data.objects["ojo_derecho_alfred"]]
    ojosJ = [bpy.data.objects[n] for n in ("ojo_izquierdo_jerry", "ojo_derecho_jerry", "pupila_izquierda_jerry", "pupila_derecha_jerry")]
    borrar_ventanas("alfred", [(o, lambda fc: fc.data_path.startswith("hide")) for o in ojosA] + [(o.data.shape_keys, lambda fc: "Closed" in fc.data_path) for o in ojosA])
    borrar_ventanas("jerry", [(o.data.shape_keys, lambda fc: "Closed" in fc.data_path) for o in ojosJ])
    if QUITAR: NEW["parpadeos"] = {}
    else:
        # --- Alfred ---
        bA = horario(11, 140, FIN, [(135, 300)]); NEW["parpadeos"]["alfred"] = bA                   # sin parpadeos al azar mientras habla (f136-174 "espera Jerry" y f187-297 "mi tobillo"): los audios traen sus propios parpadeos
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
        bJ = horario(23, 1, FIN, [(28, 85)]); NEW["parpadeos"]["jerry"] = bJ                      # sin parpadeos al azar mientras dice "corre, corre..." (f32-82)
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
    json.dump(NEW, open(DJ, "w", encoding="utf-8"))
    sc.frame_set(440); print("LISTO" if not QUITAR else "QUITADO")
except Exception:
    traceback.print_exc()
