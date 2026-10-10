# -*- coding: utf-8 -*-
"""Parte 6: desde f540 Alfred gira 180 grados, saca el HACHA de piedra de su espalda, golpea la mesa de crafteo (4 golpes) hasta romperla; la mesa se hace pequena, gira y flota y al final Alfred la absorbe (f540-680).
Se ejecuta DENTRO de Blender con exec. Requiere que ya esten hechos: el giro de Alfred (empty `alfred` + pasos, f540-562; claves en el action `alfred_giro_y_mesa`), `bpy.app.driver_namespace["IK"]` (ik_brazos.py), `ALF430` (pose de pie de Alfred a f430) y `ALF_TURN`.
Nunca usar SystemExit/raise SystemExit dentro de Blender (cierra el programa): los errores se imprimen.
Mano derecha por IK (resolver de ik_brazos): el puno es el punto de agarre del hacha (a 0.34 del codo, en la direccion del antebrazo); el hacha toma la direccion del antebrazo, con su plano plano en el plano del golpe (X-Z) y el filo hacia abajo.
Mesa = empty `mesa_de_crafteo_1` (escala 0.9): sacudida en cada golpe, se rompe en el 4.o (escala 0.9 -> 0.26), gira y flota, y vuela al pecho de Alfred (se encoge y desaparece)."""
import bpy, json, math, traceback
from mathutils import Vector, Matrix, Euler, Quaternion

try:
    ns = bpy.app.driver_namespace; g = ns["IK"]; fk = g["fk"]; REST = g["REST"]; AA = g["AA"]; sc = bpy.context.scene; E = AA.parent
    A430 = ns["ALF430"]; ROT430 = {k: tuple(v) for k, v in A430["rot"].items()}; LOC430 = {k: tuple(v) for k, v in A430["loc"].items()}
    ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
    axe = bpy.data.objects["stone_axe"]; shovel = bpy.data.objects["stone_shovel"]; mesa = bpy.data.objects["mesa_de_crafteo_1"]
    J = json.load(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\configuraciones\guiones\configuracion_portable_alfred_empuja_con_stick_f540_800.json", encoding="utf-8"))
    REL = {}
    for o in J["objetos"]:
        if o.get("nombre") in ("stone_axe", "stone_shovel"): m = o["espalda"]["matriz"]; REL[o["nombre"]] = Matrix([m[0:4], m[4:8], m[8:12], m[12:16]])
    # la espalda de Alfred segun alfred.blend: herramientas emparentadas (BONE) a Spine1_alfred, el hacha de piedra casi tocando la malla del torso (hueco ~0.002)
    _RAB = json.load(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\rel_espalda_alfred_blend.json", encoding="utf-8")); _m = _RAB["herramientas"]["stone_axe"]["matriz"]; REL["stone_axe"] = Matrix([_m[0:4], _m[4:8], _m[8:12], _m[12:16]])
    sc.frame_set(562); bpy.context.view_layer.update(); Mw = AA.matrix_world.copy()
    SP = ("Spine_alfred", "Spine1_alfred", "Spine2_alfred"); WS = (0.3, 0.3, 0.4)
    UPA, ELB = "RightUpArm_alfred", "Rightelbow_alfred"; UPL = "LeftUpArm_alfred"
    def pt(M, n, e="h"): return Mw @ (M[n].translation if e == "h" else M[n] @ Vector((0, REST[n][2], 0)))
    def rot_con(lean, arm=None, elb=None):
        r = dict(ROT430)
        for b, w in zip(SP, WS): e = list(ROT430[b]); e[0] += math.radians(w * lean); r[b] = tuple(e)
        if arm is not None: r[UPA] = tuple(arm)
        if elb is not None: r[ELB] = tuple(elb)
        return r
    M_REF = fk(rot_con(0.0), LOC430); r_vec = (pt(M_REF, UPA) - pt(M_REF, UPL)); r_vec.z = 0; r_vec.normalize()
    FWD = Vector((-1.0, 0.0, 0.0))                                                       # tras el giro Alfred mira hacia -X (la mesa)
    # geometria del hacha (local): mango en (-0.375, -0.438), cabeza hacia (0.188, 0.438); agarre al 30 % del mango
    vs = [v.co.copy() for v in axe.data.vertices]; u_loc = Vector((0.188 + 0.375, 0.438 + 0.438, 0)).normalized(); G_LOC = Vector((-0.375, -0.438, 0)) + (Vector((0.188, 0.438, 0)) - Vector((-0.375, -0.438, 0))) * 0.30
    e1 = u_loc; e3 = Vector((0, 0, 1)); e2 = e3.cross(e1); ordenados = sorted(vs, key=lambda v: v.dot(e1)); cabeza = ordenados[-max(1, len(vs) // 4):]
    S_BLADE = 1.0 if sum(v.dot(e2) for v in cabeza) / len(cabeza) >= 0 else -1.0
    ESC = axe.scale.copy(); LARGO_CABEZA = (Vector((0.188, 0.438, 0)) - G_LOC).length * ESC.x
    print("hacha: lado del filo", S_BLADE, "distancia agarre-cabeza", round(LARGO_CABEZA, 3))
    def M_hacha(grip, d):
        E1 = d.normalized(); cand = Vector((0, 1, 0)); E3 = cand if (S_BLADE * cand.cross(E1).z) <= 0 else -cand        # el lado del filo mira hacia abajo
        E3 = (E3 - E1 * E3.dot(E1)).normalized(); E2 = E3.cross(E1)
        Rw = Matrix(((E1.x, E2.x, E3.x), (E1.y, E2.y, E3.y), (E1.z, E2.z, E3.z))); Rl = Matrix(((e1.x, e2.x, e3.x), (e1.y, e2.y, e3.y), (e1.z, e2.z, e3.z)))
        R = Rw @ Rl.transposed(); S = Matrix.Diagonal(ESC).to_4x4(); pos = grip - R @ Vector((G_LOC.x * ESC.x, G_LOC.y * ESC.y, G_LOC.z * ESC.z))
        return Matrix.Translation(pos) @ R.to_4x4() @ S
    # ---------- puntos de paso del brazo derecho ----------
    ARMOS = {}
    sc.frame_set(562); Sp1 = AA.matrix_world @ AA.pose.bones["Spine1_alfred"].matrix; W_AXE_BACK = Sp1 @ REL["stone_axe"]; GRIP_BACK = W_AXE_BACK @ G_LOC
    TABLA_TOPE = Vector((-96.20, -108.47, 14.92)); HINT_B = Vector((0, 0, -0.10)); P = Vector(ns["ALF_TURN"]["P"])
    def euler_de(q, prev): return q.to_euler('XYZ', Euler(prev, 'XYZ'))
    ROT_ARM0 = ROT430[UPA]; ELB0 = ROT430[ELB]; q_prev = Euler(ROT_ARM0, 'XYZ').to_quaternion(); x_prev = ELB0[0]
    def resolver_wp(F, lean, hint_off, da, cabeza_obj=None, iters=6000, semilla=3):
        """F = punto de agarre (puno); da = direccion del mango del hacha en este paso (independiente del antebrazo); en un golpe F sale de que la cabeza del hacha toque `cabeza_obj`."""
        global q_prev, x_prev
        M = fk(rot_con(lean), LOC430); sh = pt(M, UPA); d = Vector((-0.4, 0.3, -0.6)).normalized(); hint = sh + r_vec * hint_off[0] + Vector((0, 0, hint_off[1]))
        if cabeza_obj is not None: F = cabeza_obj - da * LARGO_CABEZA
        for _ in range(3):
            tail_obj = F + d * 0.34
            q, qx, err, codo = g["resolver"]("Right", M["Spine2_alfred"], Mw, tail_obj, codo_hint=hint, inicio=(q_prev, x_prev), iters=iters, semilla=semilla, w_codo=0.3, w_giro=0.2)
            d = (tail_obj - codo).normalized()
        q_prev = q; x_prev = qx.to_euler('XYZ')[0]
        return {"q": q, "ex": qx.to_euler('XYZ')[0], "lean": lean, "err": err, "F": F, "d": d, "da": Vector(da).normalized()}
    D_READY = Vector((-0.55, 0.0, 0.83)); D_UP = Vector((0.20, 0.0, 0.98)); D_HIT = Vector((-0.72, 0.0, -0.69)); D_FOLLOW = Vector((-0.35, 0.0, -0.94))
    UP_F = Vector((-95.78, -108.47, 15.05))
    pasos = [(566, GRIP_BACK, 2, (0.10, -0.05), D_READY, None), (569, GRIP_BACK, 2, (0.10, -0.05), D_READY, None),
             (574, Vector((-95.99, -108.50, 14.60)), 4, (0.20, -0.05), D_READY, None),
             (584, UP_F, -2, (0.18, 0.25), D_UP, None), (590, None, 10, (0.20, 0.0), D_HIT, TABLA_TOPE),
             (595, UP_F, 0, (0.18, 0.25), D_UP, None), (601, None, 11, (0.20, 0.0), D_HIT, TABLA_TOPE),
             (605, UP_F, 0, (0.18, 0.25), D_UP, None), (611, None, 12, (0.20, 0.0), D_HIT, TABLA_TOPE),
             (613, UP_F, -2, (0.18, 0.25), D_UP, None), (620, None, 14, (0.20, 0.0), D_HIT, TABLA_TOPE),
             (626, Vector((-96.00, -108.48, 14.75)), 6, (0.20, 0.0), D_FOLLOW, None)]
    SOL = []
    for f, F, lean, hint, da, cab in pasos:
        F0 = F if F is not None else Vector((-95.95, -108.47, 15.20))
        w = resolver_wp(F0, lean, hint, da, cabeza_obj=cab); SOL.append((f, w)); print("paso f", f, "error", round(w["err"], 3), "agarre", [round(x, 2) for x in w["F"]])
    # reposo: brazo colgando sosteniendo el hacha
    REPOSO = {"q": Euler(ROT_ARM0, 'XYZ').to_quaternion(), "ex": ELB0[0], "lean": 0.0, "F": None, "d": None, "da": Vector((-0.10, 0.0, -1.0)).normalized()}
    SOL = [(540, REPOSO), (562, REPOSO)] + SOL + [(645, REPOSO)]
    def arm_en(f):
        for (fa, A), (fb, B) in zip(SOL, SOL[1:]):
            if fa <= f <= fb:
                if fb == fa: return A
                x = (f - fa) / (fb - fa)
                t = x * x if (B is not None and B.get("F") is not None and fb in (590, 601, 611, 620)) else ss(x)          # los golpes aceleran
                return {"q": A["q"].slerp(B["q"], t), "ex": A["ex"] + (B["ex"] - A["ex"]) * t, "lean": A["lean"] + (B["lean"] - A["lean"]) * t, "da": A["da"].lerp(B["da"], t).normalized()}
        return REPOSO
    ELB_ROT = Euler(ELB0, 'XYZ')
    # ---------- claves de Alfred ----------
    arm = AA.pose.bones[UPA]; elb = AA.pose.bones[ELB]; neck = AA.pose.bones["Neck_alfred"]; spb = [AA.pose.bones[b] for b in SP]; n = 0; prev_e = Euler(ROT_ARM0, 'XYZ'); EULS = {}
    for f in range(562, 646):
        a = arm_en(f); e = euler_de(a["q"], prev_e); prev_e = e; EULS[f] = (e, a)
        arm.rotation_euler = e; elb.rotation_euler = (a["ex"], ELB0[1], ELB0[2])
        for ax in range(3): arm.keyframe_insert("rotation_euler", index=ax, frame=f, group=UPA); elb.keyframe_insert("rotation_euler", index=ax, frame=f, group=ELB); n += 2
        for b, w_, pb in zip(SP, WS, spb):
            pb.rotation_euler = (ROT430[b][0] + math.radians(w_ * a["lean"]), ROT430[b][1], ROT430[b][2]); pb.keyframe_insert("rotation_euler", index=0, frame=f, group=b); n += 1
        ne = list(neck.rotation_euler); ne[0] = ROT430["Neck_alfred"][0] - math.radians(0.6 * a["lean"]); neck.rotation_euler = ne; neck.keyframe_insert("rotation_euler", index=0, frame=f, group="Neck_alfred"); n += 1
    for fc in AA.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'
    print("claves de Alfred", n)
    # ---------- hacha: de la espalda a la mano y de vuelta a colgar ----------
    def estado_brazo(f):
        e, a = EULS[f]; r = rot_con(a["lean"], arm=tuple(e), elb=(a["ex"], ELB0[1], ELB0[2])); M = fk(r, LOC430); h = pt(M, ELB); t = pt(M, ELB, "t"); return h, (t - h).normalized(), M
    if axe.animation_data is None: axe.animation_data_create()
    axe.animation_data.action = bpy.data.actions.new("stone_axe_golpea_la_mesa")
    axe.rotation_mode = 'QUATERNION'
    def poner(o, f, M):
        l, q, s = M.decompose(); o.location = l; o.rotation_quaternion = q; o.scale = s; o.keyframe_insert("location", frame=f); o.keyframe_insert("rotation_quaternion", frame=f); o.keyframe_insert("scale", frame=f)
    GRIP_F = {}
    for f in range(562, 646):
        h, d, M = estado_brazo(f); grip = h + d * 0.34; Mh = M_hacha(grip, EULS[f][1]["da"]); GRIP_F[f] = (grip, d)
        t = ss((f - 569) / 6.0)
        if t >= 1.0: poner(axe, f, Mh)
        else:
            sc.frame_set(f); Sp1f = AA.matrix_world @ AA.pose.bones["Spine1_alfred"].matrix; Mb = Sp1f @ REL["stone_axe"]
            lb, qb, sb = Mb.decompose(); lh, qh, sh_ = Mh.decompose(); poner(axe, f, Matrix.Translation(lb.lerp(lh, t)) @ qb.slerp(qh, t).to_matrix().to_4x4() @ Matrix.Diagonal(ESC).to_4x4())
    for fc in axe.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    # ---------- mesa: sacudidas, rotura, flotar y absorcion ----------
    HITS = [590, 601, 611, 620]; ROMPE = 620
    if mesa.animation_data is None: mesa.animation_data_create()
    mesa.animation_data.action = bpy.data.actions.new("mesa_de_crafteo_se_rompe")
    loc_m = Vector((-96.53, -108.47, 13.9946)); esc_m = Vector((0.9, 0.9, 0.9)); rz_m = 0.0              # estado ORIGINAL de la mesa (no leerlo de la escena: al repetir el script ya estaria animado y daria el estado del ultimo frame evaluado)
    sc.frame_set(620); chest = AA.matrix_world @ AA.pose.bones["Spine2_alfred"].matrix.translation
    flota = Vector((loc_m.x - 0.02, loc_m.y, loc_m.z + 0.42)); ESC_P = esc_m.x * 0.30
    def estado_mesa(f):
        loc = Vector(loc_m); esc = esc_m.x; rz = rz_m
        for i, h in enumerate(HITS[:3]):
            if h <= f <= h + 6:
                k = (f - h) / 6.0; dec = (1 - k) ** 2; loc += Vector((0.014 * math.sin(f * 2.3), 0.012 * math.cos(f * 3.1), 0.0)) * dec; esc = esc_m.x * (1 - 0.05 * dec * (1 + i * 0.4))
            if f > h + 6 or f > ROMPE: esc = min(esc, esc_m.x * (1 - 0.012 * (i + 1))) if f < ROMPE else esc
        if f < ROMPE: return loc, esc, rz
        t = ss((f - ROMPE) / 4.0)                                             # pop: se hace pequena y sube
        base = Vector(loc_m).lerp(flota, t); esc = esc_m.x + (ESC_P - esc_m.x) * t; rz = rz_m
        if f > ROMPE + 4:
            tt = f - (ROMPE + 4); base = flota + Vector((0, 0, 0.035 * math.sin(2 * math.pi * tt / 32.0))); rz = rz_m + math.radians(360.0 * tt / 40.0)
        FA = 668
        if f > 658:                                                           # absorcion: vuela al pecho de Alfred acelerando y se encoge
            u = ss_acel((f - 658) / (FA - 658)); b0 = flota + Vector((0, 0, 0.035 * math.sin(2 * math.pi * (658 - ROMPE - 4) / 32.0))); base = b0.lerp(chest + Vector((0, 0, -0.35 * 0.30)), u); esc = ESC_P * (1 - u)
            rz = rz_m + math.radians(360.0 * (658 - ROMPE - 4) / 40.0 + 540.0 * u)
        return base, esc, rz
    def ss_acel(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x) * 0.5 + x * x * 0.5
    for f in list(range(580, 672)):
        loc, esc, rz = estado_mesa(f)
        mesa.location = loc; mesa.scale = (esc, esc, esc); mesa.rotation_euler = (mesa.rotation_euler.x, mesa.rotation_euler.y, rz)
        mesa.keyframe_insert("location", frame=f); mesa.keyframe_insert("scale", frame=f); mesa.keyframe_insert("rotation_euler", frame=f)
    mesa.hide_viewport = False; mesa.hide_render = False; mesa.keyframe_insert("hide_viewport", frame=667); mesa.keyframe_insert("hide_render", frame=667)
    mesa.hide_viewport = True; mesa.hide_render = True; mesa.keyframe_insert("hide_viewport", frame=668); mesa.keyframe_insert("hide_render", frame=668)
    for fc in mesa.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR' if not fc.data_path.startswith("hide") else 'CONSTANT'
    # ---------- pala (y hacha antes de agarrarla) pegadas a la espalda durante todo el movimiento ----------
    for o in (shovel, axe):
        o.rotation_mode = 'QUATERNION'
        if o.animation_data is None: o.animation_data_create()
        if o.animation_data.action is None: o.animation_data.action = bpy.data.actions.new(o.name + "_espalda")
    for f in list(range(431, 563)) + list(range(563, 700, 1)):
        sc.frame_set(f); Sp1f = AA.matrix_world @ AA.pose.bones["Spine1_alfred"].matrix
        poner(shovel, f, Sp1f @ REL["stone_shovel"])
        if f < 562: poner(axe, f, Sp1f @ REL["stone_axe"])
    for o in (shovel, axe):
        for fc in o.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
            for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    sc.frame_set(120)
    print("LISTO")
except Exception:
    traceback.print_exc()
