# -*- coding: utf-8 -*-
"""Parte 6: los 6 golpes de Alfred a la pared de madera (puerta 1x2, golpes en f775/784/792 al bloque de abajo y f806/814/821 al de arriba) con el movimiento del BRAZO DERECHO del archivo del usuario
(`acciones/animacion_brazo_derecho_espalda.json`, copia de `animacion_alfred (1)/(2).py`; el mismo que `alfred_brazo_a_la_espalda.py`): el hombro y el codo recorren las poses del archivo con indices fraccionarios u (0-12):
 u=12 brazo atras (el hacha sale de la espalda, f754-757), u=7 arriba, u=6 adelante a la altura del pecho, u=5 adelante y abajo, u=3 colgando.
Cada golpe: sube a u=12, baja rapido (t^2) hasta el u de impacto, rebota 0.7 y vuelve a subir. Tras el ultimo, u -> 3 (f828) y mezcla con el reposo hasta f848 (como antes).
HACHA APARENTADA DE VERDAD: Child Of `Mano` -> `Rightelbow_alfred` con `basis` CONSTANTE (agarre rigido en la mano) desde f757 (se aparenta al llegar la mano a la espalda) hasta f884 (el script de guardar la devuelve a `Espalda`). Nada de claves por frame.
El agarre (basis del hacha respecto a `Rightelbow_alfred`) son los VALORES DEL USUARIO: loc (0.17911, 0.43506, 0.043194), quat WXYZ (0.925, -0.015, -0.126, -0.356), escala 0.6; solo se busca el u de impacto de cada bloque (z 14.80 abajo / 15.55 arriba, cara y -107.95) para que la cabeza quede lo mas cerca del muro; se guarda en `acciones/agarre_hacha_alfred.json`.
Se ejecuta DENTRO de Blender con exec. Nunca `raise SystemExit`. Brazo izquierdo, bloques y sonidos no se tocan. Claves del brazo derecho/codo f758-860, columna/cuello f750-860 constantes."""
import bpy, json, math, traceback
from mathutils import Vector, Matrix, Euler, Quaternion

try:
    sc = bpy.context.scene
    AA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "Hips_alfred" in o.pose.bones)
    ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
    DIR = "C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/"
    axe = bpy.data.objects["stone_axe"]; arm = AA.pose.bones["RightUpArm_alfred"]; elb = AA.pose.bones["Rightelbow_alfred"]
    axe.rotation_mode = 'QUATERNION'                                                     # las claves de basis del hacha son cuaterniones (en modo XYZ se ignoraban y el hacha quedaba mal orientada)
    SPB = [AA.pose.bones[n] for n in ("Spine_alfred", "Spine1_alfred", "Spine2_alfred", "Neck_alfred")]
    PL = {k: {"rotation_euler": v} for k, v in json.load(open(DIR + "animacion_brazo_derecho_espalda.json", encoding="utf-8")).items() if k.startswith("Right")}
    TP = 2 * math.pi
    VA = [((x - TP if x > math.pi else x) - TP, y, z - TP) for x, y, z in PL["RightUpArm_alfred"]["rotation_euler"]]          # rama de Euler de la escena (f754: -453.8, -35.4, -169.8)
    VE = [tuple(v) for v in PL["Rightelbow_alfred"]["rotation_euler"]]
    def lerp_i(V, u):
        i = max(0, min(11, int(math.floor(u)))); k = u - i; return Euler(tuple(V[i][c] + (V[i + 1][c] - V[i][c]) * k for c in range(3)), 'XYZ')
    # ---- estados de referencia (leidos ANTES de cambiar nada) ----
    sc.frame_set(848); REST_A = Euler(tuple(arm.rotation_euler), 'XYZ'); REST_E = Euler(tuple(elb.rotation_euler), 'XYZ')
    sc.frame_set(750); SP0 = [tuple(pb.rotation_euler) for pb in SPB]
    # ---- geometria del hacha (local) ----
    ESC = axe.scale.copy(); G_LOC = Vector((-0.375, -0.438, 0)) + (Vector((0.188, 0.438, 0)) - Vector((-0.375, -0.438, 0))) * 0.30; HEAD_L = Vector((0.188, 0.438, 0))
    e1 = Vector((0.563, 0.876, 0)).normalized(); e3 = Vector((0, 0, 1)); e2 = e3.cross(e1); vs = [v.co.copy() for v in axe.data.vertices]
    ordenados = sorted(vs, key=lambda v: v.dot(e1)); cabeza = ordenados[-max(1, len(vs) // 4):]; S_BLADE = 1.0 if sum(v.dot(e2) for v in cabeza) / len(cabeza) >= 0 else -1.0
    Rl_T = Matrix(((e1.x, e2.x, e3.x), (e1.y, e2.y, e3.y), (e1.z, e2.z, e3.z))).transposed()
    def agarre(alfa, esg):                                                                  # matriz (hueso -> hacha) con el puno en (0, 0.34, 0) local del hueso; cabeza a `alfa` del antebrazo alrededor de X
        a = Vector((0.0, math.cos(alfa), math.sin(alfa))); E3 = Vector((esg, 0.0, 0.0)); E3 = (E3 - a * E3.dot(a)).normalized(); E2 = E3.cross(a)
        Rb = Matrix(((a.x, E2.x, E3.x), (a.y, E2.y, E3.y), (a.z, E2.z, E3.z))); R = Rb @ Rl_T; pos = Vector((0, 0.34, 0)) - R @ Vector((G_LOC.x * ESC.x, G_LOC.y * ESC.y, G_LOC.z * ESC.z))
        return Matrix.Translation(pos) @ R.to_4x4() @ Matrix.Diagonal(ESC).to_4x4()
    LARGO = (HEAD_L - G_LOC).length * ESC.x
    # ---- tabla de matrices de la mano por u (cuerpo quieto) ----
    sc.frame_set(775)
    for pb, v in zip(SPB, SP0): pb.rotation_euler = v
    HM = []
    for k in range(0, 91):
        u = 3.0 + k * 0.1; arm.rotation_euler = lerp_i(VA, u); elb.rotation_euler = lerp_i(VE, u); bpy.context.view_layer.update(); HM.append((u, AA.matrix_world @ elb.matrix))
    PARED_Y = -107.95; TZ = {"L": 14.80, "U": 15.55}
    # AGARRE DEL USUARIO (valores del hacha en uso, Child Of `Mano` -> Rightelbow_alfred; imagen del panel Transform de stone_axe)
    G_USER = {"loc": (0.17911, 0.43506, 0.043194), "quat": (0.925, -0.015, -0.126, -0.356), "scale": (0.6, 0.6, 0.6)}
    B_GRIP = Matrix.LocRotScale(Vector(G_USER["loc"]), Quaternion(G_USER["quat"]).normalized(), Vector(G_USER["scale"])); SEL = {}; U_HIT = {}
    for lado in ("L", "U"):                                                                 # u de impacto = el que deja la cabeza de la forma mas cercana a la cara del muro
        bl = None
        for u, H in HM:
            if u > 9.0: break
            W = H @ B_GRIP; tip = W @ HEAD_L; edge = (W.to_3x3() @ (e2 * S_BLADE)).normalized()
            if not (-97.0 <= tip.x <= -96.0): continue
            err = abs(tip.y - PARED_Y) + 0.5 * max(0.0, abs(tip.z - (14.5 if lado == 'L' else 15.5)) - 0.4)                  # cabeza en la cara del muro y dentro de la altura del bloque (+-0.4 m del centro)
            if bl is None or err < bl[0]: bl = (err, u, tip.copy(), edge.y, (H @ Vector((0, 0.34, 0))).y)
        U_HIT[lado] = bl[1]; SEL[lado] = bl
    print("agarre del usuario; impacto:", {k: ("u", round(v[1], 2), "cabeza", [round(x, 2) for x in v[2]], "filo.y", round(v[3], 2), "puno.y", round(v[4], 2), "error", round(v[0], 3)) for k, v in SEL.items()}, "largo cabeza", round(LARGO, 3))
    json.dump({"descripcion": "Agarre rigido del hacha en la mano derecha (valores del usuario): basis del Child Of `Mano` -> Rightelbow_alfred.", "loc": G_USER["loc"], "quat_wxyz": G_USER["quat"], "scale": G_USER["scale"], "matriz": [v for fila in B_GRIP for v in fila]}, open(DIR + "agarre_hacha_alfred.json", "w", encoding="utf-8"), indent=1)
    # ---- calendario de u(f) ----
    HITS = [(775, "L"), (784, "L"), (792, "L"), (806, "U"), (814, "U"), (821, "U")]; UP = 12.0; seg = [(757, UP, 770, UP, "l")]; ant_rise = 770
    for i, (h, lado) in enumerate(HITS):
        ini = max(h - 5, ant_rise) if i else h - 5; uh = U_HIT[lado]
        if ini > seg[-1][2]: seg.append((seg[-1][2], seg[-1][3], ini, UP, "l"))
        seg.append((ini, UP, h, uh, "q")); seg.append((h, uh, h + 1, uh + 0.7, "l"))
        if i < len(HITS) - 1: seg.append((h + 1, uh + 0.7, h + 4, UP, "s")); ant_rise = h + 4
    seg.append((822, U_HIT["U"] + 0.7, 828, 3.0, "s"))
    def u_de(f):
        for fa, ua, fb, ub, md in seg:
            if fa <= f <= fb:
                x = (f - fa) / (fb - fa) if fb > fa else 1.0; t = x * x if md == "q" else (ss(x) if md == "s" else x); return ua + (ub - ua) * t
        return 3.0
    # ---- brazo y codo derechos, columna/cuello ----
    n = 0
    for f in range(758, 861):
        if f < 828: a = lerp_i(VA, u_de(f)); e = lerp_i(VE, u_de(f))
        elif f < 848:
            t = ss((f - 828) / 20.0); a0 = lerp_i(VA, 3.0); e0 = lerp_i(VE, 3.0)
            a = Euler(tuple(a0[c] + (REST_A[c] - a0[c]) * t for c in range(3)), 'XYZ'); e = Euler(tuple(e0[c] + (REST_E[c] - e0[c]) * t for c in range(3)), 'XYZ')
        else: a = REST_A; e = REST_E
        arm.rotation_euler = a; elb.rotation_euler = e
        for ax in range(3): arm.keyframe_insert("rotation_euler", index=ax, frame=f, group="RightUpArm_alfred"); elb.keyframe_insert("rotation_euler", index=ax, frame=f, group="Rightelbow_alfred"); n += 2
    for f in range(750, 861):
        for pb, v in zip(SPB, SP0):
            pb.rotation_euler = v; pb.keyframe_insert("rotation_euler", index=0, frame=f, group=pb.name); n += 1
    for fc in AA.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        if ("RightUpArm" in fc.data_path or "Rightelbow" in fc.data_path) and fc.data_path.endswith("rotation_euler"):
            for kp in fc.keyframe_points:
                if 757 <= kp.co.x <= 848: kp.interpolation = 'LINEAR'
    print("claves:", n)
    # ---- hacha: aparentada a Rightelbow_alfred con basis constante (sin claves por frame) ----
    cM = axe.constraints["Mano"]; cE = axe.constraints["Espalda"]
    for fc in axe.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        if "influence" in fc.data_path: continue
        for i in range(len(fc.keyframe_points) - 1, -1, -1):
            if 758 <= fc.keyframe_points[i].co.x <= 884: fc.keyframe_points.remove(fc.keyframe_points[i])
    l, q, s = B_GRIP.decompose()
    for f in (757, 884):
        axe.location = l; axe.rotation_quaternion = q; axe.scale = s
        axe.keyframe_insert("location", frame=f); axe.keyframe_insert("rotation_quaternion", frame=f); axe.keyframe_insert("scale", frame=f)
    for fc in axe.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        for kp in fc.keyframe_points:
            if 757 <= kp.co.x <= 884 and "influence" not in fc.data_path: kp.interpolation = 'LINEAR'
    # ---- verificacion ----
    out = {}
    for f in (756, 757, 770, 774, 775, 776, 779, 784, 792, 806, 814, 821, 828, 848, 860, 884):
        sc.frame_set(f); W = axe.matrix_world; H = AA.matrix_world @ elb.matrix; fist = H @ Vector((0, 0.34, 0)); grip = W @ G_LOC
        out[f] = {"cabeza": [round(x, 2) for x in W @ HEAD_L], "puno": [round(x, 2) for x in fist], "puno-agarre": round((fist - grip).length, 4), "infl(Esp,Mano)": (round(cE.influence, 1), round(cM.influence, 1))}
    sc.frame_set(120); print(out); print("LISTO")
except Exception:
    traceback.print_exc()
