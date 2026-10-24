# -*- coding: utf-8 -*-
"""alfred_cueva_4.blend: Alfred, quieto donde lo puso el usuario y mirando siempre en esa direccion, lleva en brazos 5 carbones
(objetos/vanilla/coal, escala 0.5) amontonados y desordenados, de pie / ladeados, como recogidos del suelo. El horno (copia del horno
encendido de la escena) le queda a la izquierda: uno a uno y despacio toma un carbon del monton con la mano derecha y lo mete por la
boca del horno (desaparece dentro); el brazo izquierdo sostiene el monton. Va algo cargado y se endereza a medida que se aligera.
Uso: exec(open(ruta, encoding="utf8").read()); construir()      (repetible)
"""
import bpy, math, random, json
from mathutils import Vector, Matrix, Quaternion, Euler

BASE = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_cae_estalagmita.py"
COAL_BLEND = r"C:\Users\user\Desktop\Alfred_Animacion\objetos\vanilla\coal\coal.blend"
N = 10
ESC = 0.5
F_PRIMERO, F_CICLO = 16, 40      # cada carbon: toma (0-12), lleva (12-26), suelta dentro (26), vuelve (26-38)
F_FIN = F_PRIMERO + N * F_CICLO + 20
SEMILLA = 8
MIRANDO_JSON = r"C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/alfred_parado_mirando_pose.json"   # postura del usuario al oir su nombre
SENTADO_JSON = r"C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/alfred_sentado_despues_golpe_pose.json"   # postura final del usuario
V_DER, V_IZQ = Vector((0.55, 0.05, 1.90)), Vector((-0.55, 0.05, 1.90))   # brazos en V al recibir el golpe
AJUSTE_SENTADO = 0.25           # la postura final del usuario atraviesa la estalagmita ~0.2 m: se adelanta lo justo
REBOTE = 0.06                    # cuanto rebota hacia delante al chocar con la estalagmita
ORDEN_MIRANDO = ("Hips_alfred", "Spine_alfred", "Spine1_alfred", "Spine2_alfred", "Neck_alfred", "face_alfred", "RightUpArm_alfred", "Rightelbow_alfred",
                 "LeftUpArm_alfred", "Leftelbow_alfred", "RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred")
DIR_CAIDA = Vector((math.sin(math.radians(66)), -math.cos(math.radians(66)), 0))   # atras girado 66 grados (detras tiene la estalagmita)
F_RETRO = 6                      # frames del golpe en la cara hasta chocar de espaldas con la estalagmita
RETRO = 0.05                     # cuanto retrocede hasta la estalagmita
F_SENTARSE = 40                  # resbala despacio hasta quedar sentado
ALTO_CADERA = 0.16               # altura de la cadera sobre el suelo, sentado
ESPALDA = 0.07                   # al quedar tendido, la espalda queda esta altura sobre el eje de giro de los talones
POS, ROT_Z = Vector((-76.128, -14.465, -10.997)), 98.853        # donde y hacia donde lo pone el usuario


def _base():
    ns = {"__name__": "b"}; exec(open(BASE, encoding="utf8").read(), ns); return ns


MIRANDO, SENTADO = {}, {}


def _mirando(ruta):
    d = json.load(open(ruta, encoding="utf8"))["poses"][0]; r = d["root"]["location"]
    return {"raiz": (r["x"], r["y"], r["z"]),
            "huesos": {n: tuple(b["local_space"]["rotation_euler_rad"][k] for k in "xyz") for n, b in d["bones"].items() if n in ORDEN_MIRANDO}}


def busca(t):
    """giros del cuello (rad) buscando de donde lo llaman: izquierda, derecha, otra vez izquierda y se queda mirando a Jerry"""
    claves = ((0, 0.0), (10, 0.0), (18, 0.45), (28, 0.45), (38, -0.40), (48, -0.40), (56, 0.25), (64, 0.25), (72, 0.0))
    if t >= claves[-1][0]: return 0.0
    for (a, va), (b, vb) in zip(claves, claves[1:]):
        if a <= t <= b: return va + (vb - va) * suave((t - a) / (b - a))
    return 0.0


def retroceso(tc):
    u = max(0.0, min(1.0, tc / F_RETRO)); return 1.0 - (1.0 - u) ** 2        # inercia: sale disparado y frena


def rebote(t):
    return 0.0 if t <= 0 else math.sin(min(1.0, t / 7.0) * math.pi) * math.exp(-t / 10.0)


def suave(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def construir(f_mira=None, f_imp=None, f_fin=None):
    """f_mira: levanta la cabeza para mirar a Jerry; f_imp: el carbon de Jerry le da en la cara, cae de espaldas y suelta los carbones"""
    F_FIN_ = f_fin or F_FIN; f_mira = f_mira or F_FIN_ + 1; f_imp = f_imp or F_FIN_ + 1
    B = _base(); MIRANDO.update(_mirando(MIRANDO_JSON)); SENTADO.update(_mirando(SENTADO_JSON)); sc = bpy.context.scene; O = bpy.data.objects
    rig = B["Rig"](); arm = O["Armature"]; emp = O["alfred"]; horno = O["horno"]
    for o in (emp, arm):
        if o.animation_data: o.animation_data_clear()
    rec = bpy.data.collections.get("luz_entrada_receptores"); coal = []
    for i in range(N):
        n = "coal_%d" % (i + 1); o = O.get(n)
        if o is None:
            with bpy.data.libraries.load(COAL_BLEND, link=False) as (s, d): d.objects = ["coal"]
            o = d.objects[0]; o.name = n; bpy.data.collections["cueva_bloques"].objects.link(o)
        if rec and o.name not in rec.objects: rec.objects.link(o)
        if o.animation_data: o.animation_data_clear()
        o.rotation_mode = 'QUATERNION'; coal.append(o)
    emp.rotation_mode = 'XYZ'; emp.location = POS; emp.rotation_euler = (0, 0, math.radians(ROT_Z)); bpy.context.view_layer.update()
    M_root = emp.matrix_world.copy(); Mi = M_root.inverted()            # orientacion del usuario, no se gira
    d0 = B["pose_torso"](0.03, 0.0); d0.update(B["piernas"](0.08, 0.05, -0.05))   # pose de pie con la que el usuario lo coloco
    _, c0, _ = B["resolver_con_brazos"](rig, d0, aplicar=False)
    ref = (min(c0["Rightknee_alfred"].z, c0["Leftknee_alfred"].z) + B["SUELO_PIE"], (c0["Rightknee_alfred"].y + c0["Leftknee_alfred"].y) / 2)
    ref_h = (c0["Hips_alfred"].z, c0["Hips_alfred"].y)
    boca = horno.matrix_world.translation + Vector((0, 0.52, -0.26)); dentro = horno.matrix_world.translation + Vector((0, 0.15, -0.28))   # boca de abajo del horno
    boca_c, dentro_c = Mi @ boca, Mi @ dentro
    # monton desordenado en brazos (marco del personaje: x derecha, y adelante, z arriba)
    rnd = random.Random(SEMILLA); centro = Vector((-0.10, 0.40, 0.98)); piezas = []      # monton en el brazo izquierdo
    for i in range(N):
        p = centro + Vector((rnd.uniform(-0.14, 0.14), rnd.uniform(-0.06, 0.08), 0.028 * i + rnd.uniform(-0.03, 0.06)))
        e = Euler((math.radians(90 + rnd.uniform(-35, 35)), math.radians(rnd.uniform(-30, 30)), math.radians(rnd.uniform(-60, 60))), 'XYZ')
        piezas.append((p, e.to_quaternion()))
    orden = sorted(range(N), key=lambda i: -piezas[i][0].z)              # los mete de arriba hacia abajo
    escala = Vector((ESC,) * 3)
    datos = {i: {} for i in range(N)}
    for f in range(1, F_FIN_ + 1):
        k = min(f, f_mira) - F_PRIMERO; n_hecho = min(N, max(0, (k + F_CICLO - 26) // F_CICLO)) if k >= 0 else 0
        peso = (N - n_hecho) / N
        Gi = centro + Vector((0.10, -0.04, -0.16))                      # el brazo izquierdo sostiene el monton por debajo
        Gd = centro + Vector((0.30, -0.02, -0.02))                      # la derecha libre, junto al monton
        th = 0.08 + 0.12 * peso; cad = 0.15 + 0.12 * peso; cab = 0.25; lado = 0.0
        idx = None
        if k >= 0 and k // F_CICLO < N:
            idx = orden[k // F_CICLO]; t = k % F_CICLO; pc = piezas[idx][0]
            agarre = pc + Vector((0.06, -0.04, 0.0))
            reposo_d = centro + Vector((0.30, -0.02, -0.02))
            if t < 12:
                Gd = reposo_d.lerp(agarre, suave(t / 12))
            elif t < 26:
                w = suave((t - 12) / 14); Gd = agarre.lerp(dentro_c, w); cab += 0.15 * w; th += 0.25 * w; cad += 0.15 * w
            else:
                w = suave((t - 26) / 12); Gd = dentro_c.lerp(reposo_d, w); cab += 0.15 * (1 - w); th += 0.25 * (1 - w); cad += 0.15 * (1 - w)
        cab -= 0.55 * suave((f - f_mira) / 6.0)                           # levanta la cabeza para mirar a Jerry
        cae = f >= f_imp; tc = f - f_imp
        sep, rod = 0.10, -cad; ws = 0.0
        if cae:                                                          # golpe en la cara: retrocede, choca con la estalagmita y resbala hasta quedar sentado
            ret = retroceso(tc); reb = rebote(tc - F_RETRO)
            cab -= 0.65 * suave(tc / 2.0) - 0.35 * reb                       # inercia: la cabeza se va atras primero; al chocar rebota adelante
            th -= 0.10 * ret - 0.08 * reb
            wv = min(1.0, tc / 3.0) * (1.0 + 0.15 * math.sin(min(1.0, tc / 8.0) * math.pi))   # brazos en V (con sobrepaso)
            Gd = Gd.lerp(V_DER, min(1.0, wv)) + Vector((0, 0, 0.08 * (wv - 1.0) if wv > 1 else 0)); Gi = Gi.lerp(V_IZQ, min(1.0, wv))
            ws = suave((tc - F_RETRO - 6) / F_SENTARSE)                      # se queda un instante y resbala despacio hasta sentarse
        dirs = B["pose_torso"](th, cab, lado); dirs.update(B["piernas"](sep, cad, rod))
        _, colas, info = B["resolver_con_brazos"](rig, dirs, Gd, Gi, polo_d=(1, -0.4, -0.3), polo_i=(-1, -0.4, -0.3))
        arm.pose.bones["Hips_alfred"].location = (0, 0, 0)
        piso = min(colas["Rightknee_alfred"].z, colas["Leftknee_alfred"].z) + B["SUELO_PIE"]
        yf = (colas["Rightknee_alfred"].y + colas["Leftknee_alfred"].y) / 2
        dy, dz = ref[1] - yf, ref[0] - piso                              # los pies no se mueven
        if cae:
            dy -= RETRO * retroceso(tc) - REBOTE * rebote(tc - F_RETRO)  # sale rapido, frena contra la estalagmita y rebota (accion y reaccion)
        Mbase = Matrix.Translation(M_root.to_3x3() @ Vector((0, dy, dz))) @ M_root
        emp.matrix_world = Mbase
        wp = suave((f - f_mira) / 6.0) * (1.0 - suave((f - f_imp) / 4.0))        # al oir su nombre: postura "parado mirando" del usuario
        if wp > 0:
            emp.location = emp.location.lerp(Vector(MIRANDO["raiz"]), wp)
            for n, e in MIRANDO["huesos"].items():
                b = arm.pose.bones[n]; b.rotation_euler = [a_ + (v - a_) * wp for a_, v in zip(b.rotation_euler, e)]
            arm.pose.bones["Neck_alfred"].rotation_euler.y += wp * busca(f - f_mira)   # mueve el cuello a los lados buscando a Jerry
        if ws > 0:                                                       # resbala por la estalagmita hasta la postura final del usuario
            emp.location = emp.location.lerp(Vector(SENTADO["raiz"]) + M_root.to_3x3() @ Vector((0, AJUSTE_SENTADO, 0)), ws)
            for n, e in SENTADO["huesos"].items():
                b = arm.pose.bones[n]; b.rotation_euler = [a_ + (v - a_) * ws for a_, v in zip(b.rotation_euler, e)]
        emp.keyframe_insert("location", frame=f); emp.keyframe_insert("rotation_quaternion" if emp.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f)
        arm.pose.bones["Hips_alfred"].keyframe_insert("location", frame=f)
        for n in B["ORDEN"]: arm.pose.bones[n].keyframe_insert("rotation_euler", frame=f)
        bpy.context.view_layer.update()
        mano_i = arm.matrix_world @ arm.pose.bones["Rightelbow_alfred"].matrix @ Vector((0, 0.37, 0))   # mano que lleva el carbon: la derecha
        Mb = arm.matrix_world @ arm.pose.bones["Leftelbow_alfred"].matrix   # el monton va con el antebrazo izquierdo
        if f == 1: Mb0i = Mb.inverted()
        Mrel = Mb @ Mb0i
        for i in range(N):
            p, q = piezas[i]; Mw = Mrel @ M_root @ Matrix.LocRotScale(p, q, escala); vis = True
            if idx is not None and i == idx:
                t = k % F_CICLO
                if t >= 12: Mw = Matrix.LocRotScale(mano_i, (M_root.to_quaternion() @ q), escala)
                if t >= 26: vis = False
            elif i in orden[:max(0, (k // F_CICLO) if k >= 0 else 0)]:
                vis = False
            datos[i][f] = (Mw, vis)
    # --- al caer suelta los carbones que llevaba: salen volando, caen al suelo y rebotan
    if f_imp <= F_FIN_:
        rnd2 = random.Random(3); suelo = POS.z + 0.03; f_choque = f_imp + 2
        for i in range(N):
            M1, v1 = datos[i][f_imp - 1]
            if not v1: continue
            for f in range(f_imp, f_choque): datos[i][f] = datos[i][f]          # los lleva hasta el choque
            M1 = datos[i][f_choque - 1][0]; p = M1.to_translation()
            a = rnd2.uniform(0, 2 * math.pi); hv = rnd2.uniform(0.02, 0.05)
            v = (p - datos[i][f_choque - 2][0].to_translation()) + Vector((math.cos(a) * hv, math.sin(a) * hv, rnd2.uniform(0.03, 0.07)))   # inercia del brazo + se esparcen
            f_imp_ = f_choque
            q0 = M1.to_quaternion(); eje = Vector((rnd2.uniform(-1, 1), rnd2.uniform(-1, 1), rnd2.uniform(-1, 1))).normalized(); giro = rnd2.uniform(0.2, 0.4); quieto = False
            plano = Euler((0, 0, rnd2.uniform(0, 6.28))).to_quaternion(); qf = None
            for f in range(f_imp_, F_FIN_ + 1):
                if not quieto:
                    v.z -= 9.8 / 576; p = p + v
                    if p.z <= suelo:
                        p.z = suelo; v = Vector((v.x * 0.5, v.y * 0.5, -v.z * 0.35))
                        if v.z < 0.012: quieto = True; qf = plano
                    q = (qf or (Quaternion(eje, giro * (f - f_imp_)) @ q0))
                datos[i][f] = (Matrix.LocRotScale(p, q, escala), True)
    for i, o in enumerate(coal):
        prev = None
        for f, (M, vis) in sorted(datos[i].items()):
            l, q, s = M.decompose(); o.location = l; o.rotation_quaternion = q; o.scale = s
            for dp in ("location", "rotation_quaternion", "scale"): o.keyframe_insert(dp, frame=f)
            if vis != prev:
                o.hide_viewport = o.hide_render = not vis; o.keyframe_insert("hide_viewport", frame=f); o.keyframe_insert("hide_render", frame=f); prev = vis
        for lay in o.animation_data.action.layers:
            for st in lay.strips:
                for cb in st.channelbags:
                    for fc in cb.fcurves:
                        if fc.data_path.startswith("hide"):
                            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
    sc.frame_start, sc.frame_end = 1, F_FIN_
    sc.frame_set(1)
    return {"metidos": [F_PRIMERO + j * F_CICLO + 26 for j in range(N) if F_PRIMERO + j * F_CICLO + 26 < f_mira], "fin": F_FIN_}
