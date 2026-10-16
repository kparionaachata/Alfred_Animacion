# -*- coding: utf-8 -*-
"""Parte 11: Alfred VOLTEA la cabeza hacia Jerry y le RESPONDE "¿Que cocinaste para los dos?" mientras sigue sacandose las flechas.
Va despues de la pregunta de Jerry (voz_jerry_voy_a_ir_parte11.py) y del "Oh" de la flecha de la frente; termina antes de la ultima flecha.
Audio: audios/alfred/alfred_que_cocinaste_para_los_dos.mp3; ojos: .cara_original.py del usuario (NO se ejecuta: se leen sus datos).
- Cabeza y torso: pose del usuario al mirar a Jerry (Neck_alfred, face_alfred, Spine2_alfred, Spine1_alfred) mezclada sobre la accion de las flechas.
- Ojos: shape key 'Voz_que_cocinaste' + escala/posicion/rotacion del archivo del usuario SUMADAS a la expresion de "como paso esto".
Ejecutar despues de alfred_saca_flechas, voz_alfred_como_paso_esto y voz_jerry_voy_a_ir. Repetible (no suma dos veces). Aplica el MICROFONO al final."""
import bpy, ast, math, sys, importlib.util
from mathutils import Matrix, Quaternion

AUDIO = r"C:\Users\user\Desktop\Alfred_Animacion\audios\alfred\alfred_que_cocinaste_para_los_dos.mp3"
CARA = r"C:\Users\user\Desktop\Alfred_Animacion\audios\alfred\alfred_que_cocinaste_para_los_dos.cara_original.py"
NOMBRE = "VOZ_p11_alfred_que_cocinaste"; CANAL = 30; SHAPE = "Voz_que_cocinaste"; MARCA = "voz_que_cocinaste"
DESPUES_OH = 3                               # empieza 3 frames despues de que acaba el "Oh" de la flecha de la frente
# POSE AL MIRAR A JERRY: valores del usuario (grados, XYZ Euler). Se llega a ellos con una mezcla suave (SUBE), se mantienen
# mientras habla y se vuelve a la animacion de las flechas (BAJA).
MIRA = {"Neck_alfred": (13.677, 84.011, 20.277), "face_alfred": (0.74251, 4.0623, -12.078),
        "Spine2_alfred": (3.097, -0.21478, -0.4176), "Spine1_alfred": (-14.993, 17.545, 0.25393)}
SUBE, BAJA = 14, 16                          # frames para voltear y para regresar
FASES = ((0.00, 0.00), (0.12, 0.00), (0.28, 0.70), (0.42, 1.08), (0.57, 0.92), (0.72, 1.02), (0.86, 0.48), (1.00, 0.00))


def _datos():
    d = {}
    for n in ast.parse(open(CARA, encoding="utf-8").read()).body:
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id.isupper():
            try: d[n.targets[0].id] = ast.literal_eval(n.value)
            except Exception: pass
    return d


def _curvas(idb):
    ad = idb.animation_data
    return {(fc.data_path, fc.array_index): fc for l in ad.action.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves}


def _en(fc, f):
    for k in fc.keyframe_points:
        if int(round(k.co.x)) == f: return k
    raise RuntimeError("sin clave en %s[%d] frame %d" % (fc.data_path, fc.array_index, f))


def _centro_ojos():
    from mathutils import Vector
    dg = bpy.context.evaluated_depsgraph_get(); c = Vector()
    for n in ("ojo_izquierdo_alfred", "ojo_derecho_alfred"):
        o = bpy.data.objects[n]; e = o.evaluated_get(dg); m = e.to_mesh()
        c += sum((o.matrix_world @ v.co for v in m.vertices), Vector()) / len(m.vertices) / 2; e.to_mesh_clear()
    return c


def _angulo_a_jerry(sc, arm, f):
    """grados entre hacia donde mira la cara de Alfred (cuello -> centro de los ojos) y Jerry, en planta"""
    from mathutils import Vector
    sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); c = Vector()
    for n in ("ojo_izquierdo_alfred", "ojo_derecho_alfred"):
        o = bpy.data.objects[n]; e = o.evaluated_get(dg); m = e.to_mesh()
        c += sum((o.matrix_world @ v.co for v in m.vertices), Vector()) / len(m.vertices) / 2; e.to_mesh_clear()
    nk = arm.matrix_world @ arm.pose.bones["Neck_alfred"].head; j = bpy.data.objects["jerry_sin_armadura"].matrix_world.translation
    a = Vector((c.x - nk.x, c.y - nk.y)).normalized(); b = Vector((j.x - nk.x, j.y - nk.y)).normalized()
    return abs(math.degrees(math.atan2(a.x * b.y - a.y * b.x, a.dot(b))))


def _sstep(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


def construir():
    sc = bpy.context.scene; C = _datos(); N = C["END_FRAME"]
    ed = sc.sequence_editor; S_ = ed.strips if hasattr(ed, "strips") else ed.sequences
    oh = S_["VOZ_p11_alfred_como_paso_esto_oh_alfred"]
    F0 = oh.frame_final_end + DESPUES_OH; fr = lambda k: F0 + k - 1
    habla = {int(f): float(v) for f, v in C["SPEECH_CURVE"]}

    def peso(k):
        u = (k - 1) / max(1, N - 1)
        for (a, va), (b, vb) in zip(FASES, FASES[1:]):
            if a <= u <= b: return va + (vb - va) * (u - a) / max(1e-6, b - a)
        return 0.0

    # 1. audio
    for s in [s for s in S_ if s.name.startswith(NOMBRE)]: S_.remove(s)
    s = S_.new_sound(NOMBRE, AUDIO, CANAL, F0); s["mic_emisor"] = "alfred"

    # 2. voltear la cabeza hacia Jerry (se suma a la accion densa de las flechas)
    arm = bpy.data.objects["armature"]; act = arm.animation_data.action
    if act.get(MARCA) != F0:
        cv = _curvas(arm)
        if act.get(MARCA + "_deltas"):                                   # deshacer el giro de una version anterior
            for clave, dd in act[MARCA + "_deltas"].to_dict().items():
                hueso, eje = (clave.split(":") + ["2"])[:2]
                fc = cv[('pose.bones["%s"].rotation_euler' % hueso, int(eje))]
                for j, v in enumerate(dd["vals"]): k = _en(fc, dd["ini"] + j); k.co.y -= v; k.handle_left.y -= v; k.handle_right.y -= v
            for fc in cv.values(): fc.update()
        a0, a1 = F0 - SUBE + 4, fr(N) + 2; rango = list(range(a0 - 1, a1 + BAJA + 1))
        env = {f: _sstep((f - a0) / SUBE) * (1 - _sstep((f - a1) / BAJA)) for f in rango}
        deltas = {}
        for hueso, grados in MIRA.items():
            for i in range(3):
                fc = cv.get(('pose.bones["%s"].rotation_euler' % hueso, i))
                if fc is None: raise RuntimeError("la accion no anima " + hueso)
                vals = []
                for f in rango:
                    k = _en(fc, f); d = (math.radians(grados[i]) - k.co.y) * env[f]
                    k.co.y += d; k.handle_left.y += d; k.handle_right.y += d; vals.append(d)
                fc.update(); deltas["%s:%d" % (hueso, i)] = {"ini": rango[0], "vals": vals}
        act[MARCA] = F0; act[MARCA + "_deltas"] = deltas

    # 3. ojos: se suma a la expresion que ya tienen
    for i, (nombre, coords) in enumerate(C["COORDINATES"].items()):
        ojo = bpy.data.objects[nombre]; kb = ojo.data.shape_keys.key_blocks
        if kb.get(SHAPE): ojo.shape_key_remove(kb[SHAPE])
        sk = ojo.shape_key_add(name=SHAPE, from_mix=False); sk.slider_min = -2.0; sk.slider_max = 2.0
        sk.data.foreach_set("co", [c for v in coords for c in v])
        for f in (F0 - 1, fr(N) + 1): sk.value = 0.0; sk.keyframe_insert("value", frame=f)
        lado = 1.0 if ojo.matrix_world.translation.x > 0 else -1.0; amt = 1.0 if i == 0 else 0.86
        oact = ojo.animation_data.action; ya = oact.get(MARCA) == F0
        cv = _curvas(ojo); prev = 0.0
        for k in range(1, N + 1):
            w = peso(k); lv = habla.get(k, 0.0); ataque = max(0.0, lv - prev); ola = math.sin(k * 1.34 + i * 0.16); estira = ola * lv; f = fr(k)
            sk.value = C["SHAPE_VALUE"] * w * amt; sk.keyframe_insert("value", frame=f)
            if not ya:
                suma = {("location", 0): lado * C["LATERAL"] * w * (1.0 if i == 0 else -0.55),
                        ("location", 2): C["VERTICAL"] * w * (1.0 if k < N * 0.60 else 0.65) + C["SPEECH_VERTICAL"] * lv * ola * amt,
                        ("rotation_euler", 1): lado * (C["ROTATION"] * w + C["ATTACK_ROTATION"] * ataque) * amt}
                por = {("scale", 0): (1.0 + (C["SCALE_X"] - 1.0) * w * amt) * (1.0 + C["SPEECH_SCALE_X"] * lv - 0.040 * estira),
                       ("scale", 1): 1.0 - 0.025 * lv,
                       ("scale", 2): (1.0 + (C["SCALE_Z"] - 1.0) * w * amt) * (1.0 + C["SPEECH_SCALE_Z"] * lv + 0.065 * estira + 0.025 * ataque)}
                for key, d in suma.items():
                    kp = _en(cv[key], f); kp.co.y += d; kp.handle_left.y += d; kp.handle_right.y += d
                for key, m in por.items():
                    kp = _en(cv[key], f); kp.co.y *= m; kp.handle_left.y *= m; kp.handle_right.y *= m
            prev = lv
        for fc in cv.values(): fc.update()
        oact[MARCA] = F0
        cl = kb.get("Closed")
        if cl:
            for c in C["BLINK_CENTERS"]:
                for f, v in ((fr(c) - 2, 0.0), (fr(c), 1.0), (fr(c) + 2, 0.0)): cl.value = v; cl.keyframe_insert("value", frame=f)

    # 4. microfono (ultimo paso)
    if not hasattr(sc, "microfono"):
        sp = importlib.util.spec_from_file_location("microfono_camara", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\microfono_camara\__init__.py")
        m = importlib.util.module_from_spec(sp); sys.modules["microfono_camara"] = m; sp.loader.exec_module(m); m.register()
    bpy.ops.microfono.analizar(); bpy.ops.microfono.aplicar()
    sc["p11_voz_que_cocinaste"] = {"inicio": F0, "fin": fr(N)}
    print("VOZ ALFRED 'que cocinaste':", F0, "-", fr(N))
    return F0


if __name__ in ("__main__", "x"):
    construir()
