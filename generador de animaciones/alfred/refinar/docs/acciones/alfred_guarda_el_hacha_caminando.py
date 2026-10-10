# -*- coding: utf-8 -*-
"""Parte 6: mientras camina (f860+), Alfred GUARDA EL HACHA EN LA ESPALDA con la animacion del brazo del usuario (`Downloads/animacion_alfred (1).py`, ver `alfred_brazo_a_la_espalda.py`): ida f869-881 (llega a la espalda), pausa f882-884, el hacha pasa a la espalda en f885
(desaparentar de `Rightelbow_alfred` -> aparentar a `Spine1_alfred`; agarre rigido sin claves por frame: `agarre_hacha_alfred.json` de `alfred_golpes_pared_animacion_archivo.py`), regreso f885-896 y pausa hasta f900; desde f901 vuelve el balanceo de la marcha.
Se ejecuta DENTRO de Blender con exec despues de `caminar_alfred_y_jerry.py`. Nunca `raise SystemExit`. Variable opcional: F0 (inicio de la ida, 869)."""
import bpy, json, math, traceback
from mathutils import Vector, Matrix, Euler
try:
    sc = bpy.context.scene
    AA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "Hips_alfred" in o.pose.bones)
    ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
    axe = bpy.data.objects["stone_axe"]; arm = AA.pose.bones["RightUpArm_alfred"]; elb = AA.pose.bones["Rightelbow_alfred"]
    F0 = int(globals().get("F0", 869)); FS = F0 + 16                                                  # FS = frame en que el hacha queda guardada (alin. con el indice 16 del archivo)
    PL = {k: {"rotation_euler": list(v) + list(reversed(v[:12])) + [v[0]] * 4} for k, v in json.load(open("C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/animacion_brazo_derecho_espalda.json", encoding="utf-8")).items() if k.startswith("Right")}   # animacion del usuario (copia local del archivo de Descargas)
    VA = [(x - 2 * math.pi if x > math.pi else x, y, z) for x, y, z in PL["RightUpArm_alfred"]["rotation_euler"]]; VE = [tuple(v) for v in PL["Rightelbow_alfred"]["rotation_euler"]]
    def prog(V, idx): return [((V[idx][c] - V[0][c]) / (V[12][c] - V[0][c]) if abs(V[12][c] - V[0][c]) > 1e-9 else 0.0) for c in range(3)]
    def desde(V, S, idx, B):
        p = prog(V, idx); return Euler(tuple(S[c] + (B[c] - S[c]) * p[c] for c in range(3)), 'XYZ')
    def rama(Bv, S):                                                                                   # equivalente de la pose de la espalda mas cercano a la partida (en angulos Euler)
        B = list(Bv)
        for c in range(3):
            for k in (-4 * math.pi, -2 * math.pi, 0.0, 2 * math.pi, 4 * math.pi):
                if abs(Bv[c] + k - S[c]) < abs(B[c] - S[c]): B[c] = Bv[c] + k
        return Euler(tuple(B), 'XYZ')
    FIN = F0 + 32                                                                                    # 901
    sc.frame_set(F0); S0 = Euler(tuple(arm.rotation_euler), 'XYZ'); S0E = Euler(tuple(elb.rotation_euler), 'XYZ')
    sc.frame_set(FIN); S1 = Euler(tuple(arm.rotation_euler), 'XYZ'); S1E = Euler(tuple(elb.rotation_euler), 'XYZ')
    B0 = rama(VA[12], S0); B0E = rama(VE[12], S0E); B1 = rama(VA[12], S1); B1E = rama(VE[12], S1E)
    print("partida:", [round(math.degrees(x), 1) for x in S0], "-> espalda (rama):", [round(math.degrees(x), 1) for x in B0], "| fin:", [round(math.degrees(x), 1) for x in S1])
    E = {}; EN = {}
    for f in range(F0, FS):                                                                          # ida (indices 0-15)
        i = min(f - F0, 15); E[f] = desde(VA, S0, i, B0); EN[f] = desde(VE, S0E, i, B0E)
    for f in range(FS, FIN):                                                                         # regreso (indices 16-31): hacia el balanceo que tendra en f901
        i = 16 + (f - FS); E[f] = desde(VA, S1, i, B1); EN[f] = desde(VE, S1E, i, B1E)
    n = 0
    for f in range(F0, FIN):
        arm.rotation_euler = E[f]; elb.rotation_euler = EN[f]
        for ax in range(3): arm.keyframe_insert("rotation_euler", index=ax, frame=f, group="RightUpArm_alfred"); elb.keyframe_insert("rotation_euler", index=ax, frame=f, group="Rightelbow_alfred"); n += 2
    for fc in AA.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        if ("RightUpArm" in fc.data_path or "Rightelbow" in fc.data_path) and fc.data_path.endswith("rotation_euler"):
            for kp in fc.keyframe_points:
                if F0 <= kp.co.x <= FIN: kp.interpolation = 'LINEAR'
    print("claves del brazo:", n)
    # ---- hacha APARENTADA: en la mano (Child Of `Mano` -> Rightelbow_alfred, basis CONSTANTE = agarre de `agarre_hacha_alfred.json`) hasta que el brazo llega a la espalda; en FS se desaparenta de la mano y se aparenta a `Spine1_alfred` (`Espalda`, basis REL). Sin claves por frame. ----
    DIRA = "C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/"
    RAB = json.load(open(DIRA + "rel_espalda_alfred_blend.json", encoding="utf-8")); m = RAB["herramientas"]["stone_axe"]["matriz"]; REL = Matrix([m[0:4], m[4:8], m[8:12], m[12:16]])
    mg = json.load(open(DIRA + "agarre_hacha_alfred.json", encoding="utf-8"))["matriz"]; B_GRIP = Matrix([mg[0:4], mg[4:8], mg[8:12], mg[12:16]])
    axe.rotation_mode = 'QUATERNION'; cM = axe.constraints["Mano"]; cE = axe.constraints["Espalda"]
    for fc in axe.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        for k in range(len(fc.keyframe_points) - 1, -1, -1):                                       # borra TODAS las claves del hacha desde F0-1 (tambien las influencias y el agarre de la puerta que seguian hasta f884)
            if fc.keyframe_points[k].co.x >= F0 - 1: fc.keyframe_points.remove(fc.keyframe_points[k])
    def basis_key(f, M):
        l, q, s = M.decompose(); axe.location = l; axe.rotation_quaternion = q; axe.scale = s
        axe.keyframe_insert("location", frame=f); axe.keyframe_insert("rotation_quaternion", frame=f); axe.keyframe_insert("scale", frame=f)
    def infl(f, e, mn):
        cE.influence = e; cM.influence = mn; cE.keyframe_insert("influence", frame=f); cM.keyframe_insert("influence", frame=f)
    basis_key(F0 - 1, B_GRIP); basis_key(FS - 1, B_GRIP); infl(F0 - 1, 0.0, 1.0); infl(FS - 1, 0.0, 1.0)
    basis_key(FS, REL); infl(FS, 1.0, 0.0)                                                         # DESAPARENTAR de la mano -> APARENTAR a la espalda
    for fc in axe.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        for kp in fc.keyframe_points:
            if kp.co.x >= F0 - 1: kp.interpolation = 'CONSTANT' if "influence" in fc.data_path else 'LINEAR'
    # ---- sonidos ----
    import os
    ed = sc.sequence_editor; S = "C:\\Users\\user\\Desktop\\Alfred_Animacion\\sonidos\\sounds\\"; libre = max([s_.channel for s_ in ed.strips_all] + [30]) + 1
    for s_ in [s_ for s_ in ed.strips_all if str(s_.get("guion_id", "")).startswith("snd6_jerry_p_camina_guarda")]: ed.strips.remove(s_)
    for i, (et, arch, f, v) in enumerate((("camina_guarda_roce", "step/cloth2.ogg", F0 + 6, 0.25), ("camina_guarda_hacha", "item/armor/equip_generic1.ogg", FS, 0.55), ("camina_guarda_roce_2", "step/cloth4.ogg", FS + 8, 0.20))):
        s_ = ed.strips.new_sound(f"SND_jerry_p_{et}_{f}", os.path.normpath(S + arch.replace("/", "\\")), libre + i, f); s_.volume = v; s_["vol_base"] = v; s_["mcsnd"] = "objetos"; s_["mcsnd_ev"] = et; s_["guion_id"] = f"snd6_jerry_p_{et}"
    # ---- verificacion ----
    G_LOC = Vector((-0.375, -0.438, 0)) + (Vector((0.188, 0.438, 0)) - Vector((-0.375, -0.438, 0))) * 0.30
    res = {}
    for f in (F0 - 1, F0 + 6, F0 + 12, F0 + 14, FS - 1, FS, FS + 1, FS + 10, FIN + 20):
        sc.frame_set(f); h = AA.matrix_world @ AA.pose.bones["Rightelbow_alfred"].head; t = AA.matrix_world @ AA.pose.bones["Rightelbow_alfred"].tail; fist = h + (t - h).normalized() * 0.34; grip = axe.matrix_world @ G_LOC
        Mg = AA.matrix_world @ AA.pose.bones["Spine1_alfred"].matrix @ REL
        res[f] = {"dist_puno_agarre": round((fist - grip).length, 3), "dist_hacha_a_su_sitio_en_la_espalda": round((axe.matrix_world.translation - Mg.translation).length, 3), "influencias": (round(cE.influence, 1), round(cM.influence, 1))}
    sc.frame_set(120); print(res); print("LISTO")
except Exception:
    traceback.print_exc()
