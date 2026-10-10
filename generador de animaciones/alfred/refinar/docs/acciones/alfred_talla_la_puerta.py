# -*- coding: utf-8 -*-
"""Parte 6: tras saltar fuera de la fosa (f680-732, animacion Mixamo saltar_1) Alfred, de pie en el suelo del refugio (celda de la mesa, x -97..-96, y -109..-108), gira 90 grados a la derecha, saca el hacha de la espalda y TALA UNA PUERTA DE 1x2 en el muro que tiene a su derecha
(bloques `refugio_bloque_06` z14-15 y `refugio_bloque_07` z15-16, x -97..-96, y -108..-107): 3 golpes al de abajo (rompe en el 3.o) y 3 al de arriba (rompe en el 3.o) (f736-870).
Se ejecuta DENTRO de Blender con exec; requiere `IK` (ik_brazos.py). Nunca `raise SystemExit`. El brazo izquierdo mantiene los valores del usuario durante los golpes (LeftUpArm rot (75.358,-61.969,-33.305) loc (-0.025402,0.044715,0.10975) escala (0.997,1,1.002); Leftelbow rot (-3.2443,36.486,38.644))."""
import bpy, json, math, traceback
from mathutils import Vector, Matrix, Euler, Quaternion

try:
    sc = bpy.context.scene; ns = bpy.app.driver_namespace
    src = open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\parte3\ik_brazos.py", encoding="utf-8").read(); g = {"__name__": "ik"}; exec(src, g); ns["IK"] = g
    fk = g["fk"]; REST = g["REST"]; AA = g["AA"]; E = AA.parent
    ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
    axe = bpy.data.objects["stone_axe"]; shovel = bpy.data.objects["stone_shovel"]; b06 = bpy.data.objects["refugio_bloque_06"]; b07 = bpy.data.objects["refugio_bloque_07"]
    J = json.load(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\configuraciones\guiones\configuracion_portable_alfred_empuja_con_stick_f540_800.json", encoding="utf-8"))
    REL = {}
    for o in J["objetos"]:
        if o.get("nombre") in ("stone_axe", "stone_shovel"): m = o["espalda"]["matriz"]; REL[o["nombre"]] = Matrix([m[0:4], m[4:8], m[8:12], m[12:16]])
    _RAB = json.load(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\rel_espalda_alfred_blend.json", encoding="utf-8")); _m = _RAB["herramientas"]["stone_axe"]["matriz"]; REL["stone_axe"] = Matrix([_m[0:4], _m[4:8], _m[8:12], _m[12:16]])      # espalda como en alfred.blend
    # ---------- 1) giro de 90 grados a la derecha sobre los pies (f736-750) ----------
    sc.frame_set(732)
    pr = AA.matrix_world @ AA.pose.bones["Rightknee_alfred"].tail; pl = AA.matrix_world @ AA.pose.bones["Leftknee_alfred"].tail
    P = Vector(((pr.x + pl.x) / 2, (pr.y + pl.y) / 2, 0)); loc0 = Vector(E.location); rz0 = E.rotation_euler.z
    T0, T1 = 736, 750
    print("pies", [round(x, 3) for x in P], "empty", [round(x, 3) for x in loc0], "rz", round(math.degrees(rz0), 1))
    def rz_en(f): return rz0 - math.pi / 2 * ss((f - T0) / (T1 - T0))
    def loc_en(f):
        a = rz_en(f) - rz0; d = Vector((loc0.x - P.x, loc0.y - P.y, 0)); r = Matrix.Rotation(a, 3, 'Z') @ d; return Vector((P.x + r.x, P.y + r.y, loc0.z))
    for f in list(range(733, T1 + 1)) + [T1 + 1]:
        ff = min(max(f, T0), T1); E.location = loc_en(ff); E.rotation_euler = (E.rotation_euler.x, E.rotation_euler.y, rz_en(ff))
        E.keyframe_insert("location", frame=f); E.keyframe_insert("rotation_euler", frame=f)
    for fc in E.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    sc.frame_set(750); bpy.context.view_layer.update(); Mw = AA.matrix_world.copy()
    ROT = {pb.name: tuple(pb.rotation_euler) for pb in AA.pose.bones}; LOC = {pb.name: tuple(pb.location) for pb in AA.pose.bones}
    SP = ("Spine_alfred", "Spine1_alfred", "Spine2_alfred"); WS = (0.3, 0.3, 0.4); UPA, ELB, UPL, ELBL = "RightUpArm_alfred", "Rightelbow_alfred", "LeftUpArm_alfred", "Leftelbow_alfred"
    def pt(M, n, e="h"): return Mw @ (M[n].translation if e == "h" else M[n] @ Vector((0, REST[n][2], 0)))
    def rot_con(lean):
        r = dict(ROT)
        for b, w in zip(SP, WS): e = list(ROT[b]); e[0] += math.radians(w * lean); r[b] = tuple(e)
        return r
    M_REF = fk(rot_con(0.0), LOC); r_vec = (pt(M_REF, UPA) - pt(M_REF, UPL)); r_vec.z = 0; r_vec.normalize()
    FWD = (Mw.to_3x3() @ Vector((0, 0, 0))) if False else None
    print("derecha de Alfred (mundo):", [round(x, 2) for x in r_vec])
    # geometria del hacha (local)
    ESC = axe.scale.copy(); G_LOC = Vector((-0.375, -0.438, 0)) + (Vector((0.188, 0.438, 0)) - Vector((-0.375, -0.438, 0))) * 0.30
    u_loc = Vector((0.563, 0.876, 0)).normalized(); e1 = u_loc; e3 = Vector((0, 0, 1)); e2 = e3.cross(e1); vs = [v.co.copy() for v in axe.data.vertices]
    ordenados = sorted(vs, key=lambda v: v.dot(e1)); cabeza = ordenados[-max(1, len(vs) // 4):]; S_BLADE = 1.0 if sum(v.dot(e2) for v in cabeza) / len(cabeza) >= 0 else -1.0
    LARGO_CABEZA = (Vector((0.188, 0.438, 0)) - G_LOC).length * ESC.x
    LAT = Vector((1.0, 0.0, 0.0))                                                          # ahora el plano del golpe es Y-Z: el eje lateral es X
    def M_hacha(grip, d):
        E1 = d.normalized(); cand = LAT; E3 = cand if (S_BLADE * cand.cross(E1).z) <= 0 else -cand; E3 = (E3 - E1 * E3.dot(E1)).normalized(); E2 = E3.cross(E1)
        Rw = Matrix(((E1.x, E2.x, E3.x), (E1.y, E2.y, E3.y), (E1.z, E2.z, E3.z))); Rl = Matrix(((e1.x, e2.x, e3.x), (e1.y, e2.y, e3.y), (e1.z, e2.z, e3.z)))
        R = Rw @ Rl.transposed(); pos = grip - R @ Vector((G_LOC.x * ESC.x, G_LOC.y * ESC.y, G_LOC.z * ESC.z)); return Matrix.Translation(pos) @ R.to_4x4() @ Matrix.Diagonal(ESC).to_4x4()
    # ---------- 2) brazo derecho: al hacha de la espalda, saca y golpea ----------
    sc.frame_set(750); Sp1 = AA.matrix_world @ AA.pose.bones["Spine1_alfred"].matrix; GRIP_BACK = (Sp1 @ REL["stone_axe"]) @ G_LOC
    ARM0 = ROT[UPA]; ELB0 = ROT[ELB]; q_prev = Euler(ARM0, 'XYZ').to_quaternion(); x_prev = ELB0[0]
    def euler_de(q, prev): return q.to_euler('XYZ', Euler(prev, 'XYZ'))
    def resolver_wp(F, lean, hint_off, da, cabeza_obj=None, iters=6000, semilla=3):
        global q_prev, x_prev
        M = fk(rot_con(lean), LOC); sh = pt(M, UPA); d = Vector((0.4, 0.3, -0.6)).normalized(); hint = sh + r_vec * hint_off[0] + Vector((0, 0, hint_off[1]))
        if cabeza_obj is not None: F = cabeza_obj - da * LARGO_CABEZA
        for _ in range(3):
            tail_obj = F + d * 0.34
            q, qx, err, codo = g["resolver"]("Right", M["Spine2_alfred"], Mw, tail_obj, codo_hint=hint, inicio=(q_prev, x_prev), iters=iters, semilla=semilla, w_codo=0.3, w_giro=0.2)
            d = (tail_obj - codo).normalized()
        q_prev = q; x_prev = qx.to_euler('XYZ')[0]
        return {"q": q, "ex": qx.to_euler('XYZ')[0], "lean": lean, "err": err, "F": F, "d": d, "da": Vector(da).normalized()}
    CX = P.x                                                                              # los golpes caen frente a Alfred (x de los pies) sobre el muro de y -108.0
    D_READY = Vector((0.0, 0.55, 0.83)); D_UP = Vector((0.0, -0.20, 0.98)); D_HIT_L = Vector((0.0, 0.80, -0.60)); D_HIT_U = Vector((0.0, 0.88, -0.30)); D_FOLLOW = Vector((0.0, 0.35, -0.94))
    PARED_Y = -107.95                                                                     # la cabeza del hacha entra 5 cm en el bloque
    TL = Vector((CX, PARED_Y, 14.55)); TU = Vector((CX, PARED_Y, 15.55))
    z_base = (Mw @ Vector((0, 0, 0))).z
    UP_F = Vector((CX, P.y + 0.05, z_base + 2.05))
    HITS = [(775, "L"), (784, "L"), (792, "L"), (806, "U"), (814, "U"), (821, "U")]
    pasos = [(754, GRIP_BACK, 2, (0.10, -0.05), D_READY, None), (757, GRIP_BACK, 2, (0.10, -0.05), D_READY, None), (762, Vector((CX, P.y + 0.25, z_base + 1.45)), 4, (0.20, -0.05), D_READY, None)]
    for i, (h, lado) in enumerate(HITS):
        pasos.append((h - 6, UP_F, -2, (0.18, 0.25), D_UP, None)); pasos.append((h, None, 24 if lado == "L" else 12, (0.20, 0.0), D_HIT_L if lado == "L" else D_HIT_U, TL if lado == "L" else TU))
    pasos.append((828, Vector((CX, P.y + 0.25, z_base + 1.30)), 6, (0.20, 0.0), D_FOLLOW, None))
    SOL = []
    for f, F, lean, hint, da, cab in pasos:
        F0 = F if F is not None else Vector((CX, P.y + 0.6, z_base + 1.5)); w = resolver_wp(F0, lean, hint, da, cabeza_obj=cab); SOL.append((f, w)); print("paso f", f, "error", round(w["err"], 3))
    REPOSO = {"q": Euler(ARM0, 'XYZ').to_quaternion(), "ex": ELB0[0], "lean": 0.0, "F": None, "d": None, "da": Vector((0.0, 0.1, -1.0)).normalized()}
    SOL = [(750, REPOSO)] + SOL + [(848, REPOSO)]
    GOLPES = {h for h, _ in HITS}
    def arm_en(f):
        for (fa, A), (fb, B) in zip(SOL, SOL[1:]):
            if fa <= f <= fb:
                x = (f - fa) / (fb - fa) if fb > fa else 1.0; t = x * x if fb in GOLPES else ss(x)
                return {"q": A["q"].slerp(B["q"], t), "ex": A["ex"] + (B["ex"] - A["ex"]) * t, "lean": A["lean"] + (B["lean"] - A["lean"]) * t, "da": A["da"].lerp(B["da"], t).normalized()}
        return REPOSO
    arm = AA.pose.bones[UPA]; elb = AA.pose.bones[ELB]; neck = AA.pose.bones["Neck_alfred"]; spb = [AA.pose.bones[b] for b in SP]; n = 0; prev_e = Euler(ARM0, 'XYZ'); EULS = {}
    for f in range(750, 861):
        a = arm_en(f); e = euler_de(a["q"], prev_e); prev_e = e; EULS[f] = (e, a)
        arm.rotation_euler = e; elb.rotation_euler = (a["ex"], ELB0[1], ELB0[2])
        for ax in range(3): arm.keyframe_insert("rotation_euler", index=ax, frame=f, group=UPA); elb.keyframe_insert("rotation_euler", index=ax, frame=f, group=ELB); n += 2
        for b, w_, pb in zip(SP, WS, spb):
            pb.rotation_euler = (ROT[b][0] + math.radians(w_ * a["lean"]), ROT[b][1], ROT[b][2]); pb.keyframe_insert("rotation_euler", index=0, frame=f, group=b); n += 1
        ne = list(neck.rotation_euler); ne[0] = ROT["Neck_alfred"][0] - math.radians(0.6 * a["lean"]); neck.rotation_euler = ne; neck.keyframe_insert("rotation_euler", index=0, frame=f, group="Neck_alfred"); n += 1
    # brazo izquierdo: valores del usuario mientras golpea (sube f750-764, exacto f764-832, vuelve a colgar f832-848)
    upl = AA.pose.bones[UPL]; ell = AA.pose.bones[ELBL]; H_UP = Euler(ROT[UPL], 'XYZ'); H_LOC = Vector((-0.006601, 0.096746, -0.086081)); H_SC = Vector((1.0, 1.0, 1.0)); H_EL = Euler(ROT[ELBL], 'XYZ')
    G_UP = Euler(tuple(math.radians(x) for x in (75.358, -61.969, -33.305)), 'XYZ'); G_LOC_ = Vector((-0.025402, 0.044715, 0.10975)); G_SC = Vector((0.997, 1.0, 1.002)); G_EL = Euler(tuple(math.radians(x) for x in (-3.2443, 36.486, 38.644)), 'XYZ')
    for f in range(750, 861):
        t = ss((f - 750) / 14.0) if f <= 764 else (1.0 if f <= 832 else 1 - ss((f - 832) / 16.0))
        q = H_UP.to_quaternion().slerp(G_UP.to_quaternion(), t); e = q.to_euler('XYZ', H_UP) if 0 < t < 1 else (G_UP if t >= 1 else H_UP)
        upl.rotation_euler = e; upl.location = H_LOC.lerp(G_LOC_, t); upl.scale = H_SC.lerp(G_SC, t); ell.rotation_euler = Euler(tuple(H_EL[i] + (G_EL[i] - H_EL[i]) * t for i in range(3)), 'XYZ')
        for ax in range(3):
            upl.keyframe_insert("rotation_euler", index=ax, frame=f, group=UPL); upl.keyframe_insert("location", index=ax, frame=f, group=UPL); upl.keyframe_insert("scale", index=ax, frame=f, group=UPL); ell.keyframe_insert("rotation_euler", index=ax, frame=f, group=ELBL); n += 4
    for fc in AA.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'BEZIER' if fc.data_path.split('"')[1] not in () else kp.interpolation
    print("claves de Alfred", n)
    # ---------- 3) hacha: pegada a la espalda hasta agarrarla, en la mano despues ----------
    def estado_brazo(f):
        e, a = EULS[f]; r = rot_con(a["lean"]); r[UPA] = tuple(e); r[ELB] = (a["ex"], ELB0[1], ELB0[2]); M = fk(r, LOC); h = pt(M, ELB); t = pt(M, ELB, "t"); return h, (t - h).normalized()
    def poner(o, f, M):
        l, q, s = M.decompose(); o.location = l; o.rotation_quaternion = q; o.scale = s; o.keyframe_insert("location", frame=f); o.keyframe_insert("rotation_quaternion", frame=f); o.keyframe_insert("scale", frame=f)
    for f in range(700, 750):                                                     # durante el salto y el giro viajan pegadas a la espalda
        sc.frame_set(f); Spf = AA.matrix_world @ AA.pose.bones["Spine1_alfred"].matrix; poner(axe, f, Spf @ REL["stone_axe"]); poner(shovel, f, Spf @ REL["stone_shovel"])
    for f in range(750, 861):
        h, d = estado_brazo(f); grip = h + d * 0.34; Mh = M_hacha(grip, EULS[f][1]["da"]); t = ss((f - 757) / 6.0)
        if t >= 1.0: poner(axe, f, Mh)
        else:
            sc.frame_set(f); Spf = AA.matrix_world @ AA.pose.bones["Spine1_alfred"].matrix; Mb = Spf @ REL["stone_axe"]; lb, qb, sb = Mb.decompose(); lh, qh, sh_ = Mh.decompose()
            poner(axe, f, Matrix.Translation(lb.lerp(lh, t)) @ qb.slerp(qh, t).to_matrix().to_4x4() @ Matrix.Diagonal(ESC).to_4x4())
    for f in range(750, 900):
        sc.frame_set(f); Spf = AA.matrix_world @ AA.pose.bones["Spine1_alfred"].matrix; poner(shovel, f, Spf @ REL["stone_shovel"])
    for o in (axe, shovel):
        for fc in o.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
            for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    # ---------- 4) los bloques: se sacuden con cada golpe y se rompen en el 3.o ----------
    for blk, golpes in ((b06, [h for h, l in HITS if l == "L"]), (b07, [h for h, l in HITS if l == "U"])):
        blk.rotation_mode = 'XYZ'
        if blk.animation_data is None: blk.animation_data_create()
        blk.animation_data.action = bpy.data.actions.new(blk.name + "_se_talla")
        l0 = Vector((-96.5, -107.5, 14.0 if blk.name.endswith("06") else 15.0)); s0 = Vector((1.0, 1.0, 1.0)); rom = golpes[-1]      # estado ORIGINAL del bloque (no leerlo de la escena: ya estaria animado al repetir el script)
        def estado(f, blk=blk, l0=l0, s0=s0, golpes=golpes, rom=rom):
            loc = Vector(l0); esc = 1.0
            for i, h in enumerate(golpes):
                if h <= f <= h + 5 and h != rom: k = (f - h) / 5.0; dec = (1 - k) ** 2; loc += Vector((0.012 * math.sin(f * 2.7), 0.010 * math.cos(f * 3.3), 0.006 * math.sin(f * 1.9))) * dec
                if h < rom and f > h: esc = min(esc, 1.0 - 0.03 * (i + 1))
            if f >= rom: u = ss((f - rom) / 4.0); esc = 0.97 * (1.0 + 0.10 * math.sin(math.pi * u)) * (1 - u)
            return loc, esc
        for f in range(golpes[0] - 4, rom + 6):
            loc, esc = estado(f); blk.location = loc; blk.scale = s0 * esc
            blk.keyframe_insert("location", frame=f); blk.keyframe_insert("scale", frame=f)
        blk.hide_viewport = False; blk.hide_render = False; blk.keyframe_insert("hide_viewport", frame=rom + 3); blk.keyframe_insert("hide_render", frame=rom + 3)
        blk.hide_viewport = True; blk.hide_render = True; blk.keyframe_insert("hide_viewport", frame=rom + 4); blk.keyframe_insert("hide_render", frame=rom + 4)
        for fc in blk.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT' if fc.data_path.startswith("hide") else 'LINEAR'
    # ---------- verificacion ----------
    HEAD_L = Vector((0.188, 0.438, 0)); res = {}
    for f in (750, 762, 775, 784, 792, 806, 814, 821, 835, 860):
        sc.frame_set(f); res[f] = {"cabeza_hacha": [round(x, 2) for x in axe.matrix_world @ HEAD_L], "mano": [round(x, 2) for x in AA.matrix_world @ AA.pose.bones[ELB].tail]}
    sc.frame_set(120); print(res); print("LISTO")
except Exception:
    traceback.print_exc()
