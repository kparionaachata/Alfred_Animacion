# -*- coding: utf-8 -*-
"""Despues de romper la veta (alfred_pica_hierro.py) Alfred: se sorprende de que salga solo un hierro, se amarga, tira el pico al suelo,
mira toda la cueva, se enoja con ella levantando el puno, recoge el HIERRO EN BRUTO que encontro y lo lanza al techo (el pico se queda en el suelo); unos frames despues una estalactita entera
(nueva, colgando justo encima de el) se desprende, le cae en la cabeza y Alfred queda tirado boca abajo.
No se tocan las mallas de los ojos: solo la armature, el empty `alfred`, el pico y la estalactita.
Poses por estados (tronco, cabeza, giro de cabeza, piernas, manos por IK; Rig de alfred_cae_estalagmita.py) interpolados por frame;
transiciones expresivas (susto, enojo, golpe) con Elastic In-Out (regla del proyecto).
Uso: exec(open(ruta, encoding="utf8").read()); construir()      (repetible: rehace desde F0)
"""
import bpy, math, random
from mathutils import Vector, Matrix, Quaternion, Euler

BASE = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_cae_estalagmita.py"
PIE = Vector((-67.5, -17.5, -11.95)); R180 = Quaternion((0, 0, 1), math.pi)
F0 = 92                                   # primer frame de esta escena (alfred_pica_hierro termina de enderezarse ~91)
F_SUELTA_PICO, F_AGARRA, F_LANZA, F_TECHO = 136, 252, 280, 291
F_ESTAL_SUELTA = 312
F_FIN = 390
SUELO = -12.0
ESTAL_CELDA = (-68, -18)                  # justo encima de Alfred
ORIGEN = "amargado_estalactita"
PASO = 0.45                               # paso adelante al agacharse por el hierro


def _base():
    ns = {"__name__": "base_mina"}; exec(open(BASE, encoding="utf8").read(), ns); return ns


def suave(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def elastic(t):
    t = max(0.0, min(1.0, t))
    if t in (0.0, 1.0): return t
    c = (2 * math.pi) / 4.5
    if t < 0.5: return -(2 ** (20 * t - 10) * math.sin((20 * t - 11.125) * c)) / 2
    return (2 ** (-20 * t + 10) * math.sin((20 * t - 11.125) * c)) / 2 + 1


# estados: th, cab, lado, yaw (giro de cabeza, rad, + = a su izquierda), sep, cad, rod, Gd (mano der), Gi (mano izq) en el marco del personaje
def E(th=0.1, cab=0.0, lado=0.0, yaw=0.0, sep=0.09, cad=0.2, rod=-0.2, Gd=(0.30, 0.10, 0.85), Gi=(-0.30, 0.10, 0.85)):
    return dict(th=th, cab=cab, lado=lado, yaw=yaw, sep=sep, cad=cad, rod=rod, Gd=Vector(Gd) if Gd is not None else None, Gi=Vector(Gi))


CLAVES = [  # (frame, estado, curva hacia este estado)
    (95, E(th=0.10, cab=0.25, Gd=(0.38, 0.30, 1.05), Gi=(-0.32, 0.20, 0.90)), suave),                     # mira lo que salio
    (103, E(th=-0.18, cab=-0.35, sep=0.12, Gd=(0.48, 0.15, 1.30), Gi=(-0.48, 0.20, 1.35)), elastic),        # SORPRESA: atras, brazos abiertos
    (112, E(th=0.35, cab=0.50, Gd=(0.36, 0.25, 0.95), Gi=(-0.34, 0.18, 0.92)), suave),                     # se fija: solo uno
    (126, E(th=0.55, cab=0.75, lado=0.0, cad=0.25, rod=-0.30, Gd=(0.30, 0.12, 0.70), Gi=(-0.30, 0.08, 0.72)), suave),   # AMARGADO
    (131, E(th=0.05, cab=0.25, Gd=(0.42, -0.18, 1.55), Gi=(-0.30, 0.08, 0.80)), suave),                    # levanta el pico para tirarlo
    (136, E(th=0.50, cab=0.55, Gd=(0.45, 0.45, 0.62), Gi=(-0.30, 0.10, 0.80)), suave),                     # lo tira al suelo
    (146, E(th=0.15, cab=0.05, Gd=(0.30, 0.08, 0.85), Gi=(-0.30, 0.08, 0.85)), suave),
    (162, E(th=0.05, cab=-0.15, lado=0.35, yaw=0.75, Gd=(0.30, 0.05, 0.86), Gi=(-0.30, 0.05, 0.86)), suave),   # mira la cueva: izquierda
    (182, E(th=0.05, cab=-0.15, lado=-0.35, yaw=-0.75, Gd=(0.30, 0.05, 0.86), Gi=(-0.30, 0.05, 0.86)), suave), # derecha
    (198, E(th=-0.12, cab=-0.65, Gd=(0.30, 0.05, 0.88), Gi=(-0.30, 0.05, 0.88)), suave),                   # arriba (el techo)
    (206, E(th=-0.15, cab=-0.55, sep=0.18, cad=0.25, rod=-0.25, Gd=(0.30, 0.18, 2.05), Gi=(-0.36, 0.22, 0.98)), elastic),  # ENOJO: puno en alto
    (232, E(th=-0.10, cab=-0.50, sep=0.18, cad=0.25, rod=-0.25, Gd=(0.30, 0.18, 2.00), Gi=(-0.36, 0.22, 0.98)), suave),
    (244, E(th=0.70, cab=0.45, sep=0.14, cad=0.35, rod=-0.35, Gd=None, Gi=(-0.30, 0.20, 0.80)), suave),       # se agacha a recoger el pico
    (252, E(th=0.70, cab=0.45, sep=0.14, cad=0.35, rod=-0.35, Gd=None, Gi=(-0.30, 0.20, 0.80)), suave),
    (262, E(th=0.10, cab=0.0, Gd=(0.36, 0.10, 0.95), Gi=(-0.30, 0.10, 0.85)), suave),                      # de pie con el pico
    (272, E(th=0.30, cab=0.20, sep=0.14, cad=0.35, rod=-0.40, Gd=(0.32, -0.35, 0.70), Gi=(-0.35, 0.20, 0.90)), suave),   # toma impulso
    (280, E(th=-0.25, cab=-0.55, sep=0.14, Gd=(0.25, 0.35, 2.00), Gi=(-0.38, 0.15, 1.05)), elastic),       # LANZA hacia el techo
    (292, E(th=0.08, cab=0.0, Gd=(0.32, 0.10, 0.90), Gi=(-0.32, 0.10, 0.88)), suave),                     # tras lanzarlo: cabeza normal
    (312, E(th=0.08, cab=0.0, Gd=(0.30, 0.08, 0.86), Gi=(-0.30, 0.08, 0.86)), suave),
]


def construir():
    B = _base(); sc = bpy.context.scene; O = bpy.data.objects
    rig = B["Rig"](); arm = O["Armature"]; emp = O["alfred"]; pico = O["stone_pickaxe"]; W = lambda: arm.matrix_world
    # ---------------- estalactita nueva justo encima de Alfred (una pieza por bloque: base, tronco, punta)
    estal = _estalactita(O, sc)
    # ---------------- borrar claves desde F0
    for ob in (emp, arm, pico):
        ad = ob.animation_data
        if ad and ad.action:
            for lay in ad.action.layers:
                for s in lay.strips:
                    for cb in s.channelbags:
                        for fc in cb.fcurves:
                            for kp in reversed(list(fc.keyframe_points)):
                                if kp.co[0] >= F0: fc.keyframe_points.remove(kp)
    sc.frame_end = F_FIN
    # estado inicial = pose real del frame F0-1
    sc.frame_set(F0 - 1)
    eul_ini = {n: arm.pose.bones[n].rotation_euler.copy() for n in B["ORDEN"]}
    Mh0 = W() @ arm.pose.bones["Rightelbow_alfred"].matrix
    rel_pico = Mh0.inverted() @ pico.matrix_world
    loc_root = emp.matrix_world.translation.copy()
    # posicion del pico tirado (se calcula al soltarlo) y de recogida
    estado_pico = {"modo": "mano", "rel": rel_pico}
    claves = [(F0 - 1, None, suave)] + CLAVES
    def estado_en(f):
        for (fa, ea, _), (fb, eb, curva) in zip(claves, claves[1:]):
            if fa <= f <= fb:
                u = curva((f - fa) / max(1, fb - fa)); return ea, eb, u
        return claves[-1][1], claves[-1][1], 1.0
    def mezcla(a, b, u, Gd_def):
        if a is None: return b, u
        out = {}
        for k in b:
            va, vb = a[k], b[k]
            if va is None: va = Gd_def
            if vb is None: vb = Gd_def
            out[k] = va + (vb - va) * u if not isinstance(va, Vector) else va.lerp(vb, u) if u <= 1 else va + (vb - va) * u
        return out, u
    hierro = O["raw_iron_soltado"]; sc.frame_set(F_AGARRA - 1); M_hierro0 = hierro.matrix_world.copy(); sc.frame_set(F0 - 1)
    pico_suelo = {"agarre": M_hierro0.translation.copy()}                     # se agacha a recoger el hierro
    datos_hierro = {}; rel_hierro = None
    rnd = random.Random(4)
    datos_pico = {}
    f_contacto = None; info_fin = {}
    for f in range(F0, F_FIN + 1):
        ea, eb, u = estado_en(f)
        # mano derecha hacia el pico tirado al recogerlo
        gd_pico = None
        w_paso = suave((f - 236) / 8.0) * (1 - suave((f - 258) / 8.0))       # da un paso hacia el hierro para alcanzarlo
        paso = R180 @ Vector((0, PASO * w_paso, 0))
        if pico_suelo is not None:
            gd_pico = R180.inverted() @ (pico_suelo["agarre"] - (loc_root + paso))
        if ea is None:
            st = dict(eb); fa_u = u
            # desde la pose real: mezcla por euler al final
        else:
            st = {}
            for k in eb:
                va, vb = ea[k], eb[k]
                if va is None: va = gd_pico if gd_pico is not None else Vector((0.35, 0.3, 0.3))
                if vb is None: vb = gd_pico if gd_pico is not None else Vector((0.35, 0.3, 0.3))
                st[k] = va.lerp(vb, u) if isinstance(va, Vector) else va + (vb - va) * u
        # sacudir el puno y la cabeza de enojo
        if 206 <= f <= 232:
            k = (f - 206) / 26.0; a = math.sin(math.pi * k)
            st["Gd"] = st["Gd"] + Vector((0.05 * math.sin(f * 1.6), 0.04 * math.cos(f * 1.6), 0.07 * math.sin(f * 1.6))) * a
            st["yaw"] += 0.10 * math.sin(f * 1.1) * a
        dirs = B["pose_torso"](st["th"], st["cab"], st["lado"]); dirs.update(B["piernas"](st["sep"], st["cad"], st["rod"]))
        giros = {"Neck_alfred": st["yaw"] * 0.55, "face_alfred": st["yaw"] * 0.45, "Spine2_alfred": st["yaw"] * 0.0}
        if pico_suelo is not None and (eb.get("Gd") is None or (ea is not None and ea.get("Gd") is None)):
            _, c0, _ = B["resolver_con_brazos"](rig, dirs, aplicar=False, giros=giros)      # tronco y piernas primero: donde queda la raiz
            piso0 = min(c0["Rightknee_alfred"].z, c0["Leftknee_alfred"].z) + B["SUELO_PIE"]; yf0 = (c0["Rightknee_alfred"].y + c0["Leftknee_alfred"].y) / 2
            raiz0 = PIE - R180 @ Vector((0, yf0, piso0)) + paso
            objetivo = R180.inverted() @ (pico_suelo["agarre"] + Vector((0, 0, 0.05)) - raiz0)
            va = ea["Gd"] if (ea is not None and ea.get("Gd") is not None) else objetivo
            vb = eb["Gd"] if eb.get("Gd") is not None else objetivo
            st["Gd"] = va.lerp(vb, u)
        _, colas, info = B["resolver_con_brazos"](rig, dirs, Vector(st["Gd"]), Vector(st["Gi"]), polo_d=(1, -0.4, -0.3), polo_i=(-1, -0.4, -0.3), giros=giros)
        if ea is None:                                         # primer tramo: mezcla desde la pose real del final del minado
            for n in B["ORDEN"]:
                pb = arm.pose.bones[n]; q = eul_ini[n].to_quaternion().slerp(pb.rotation_euler.to_quaternion(), u)
                pb.rotation_euler = q.to_euler('XYZ', pb.rotation_euler)
        piso = min(colas["Rightknee_alfred"].z, colas["Leftknee_alfred"].z) + B["SUELO_PIE"]
        yf = (colas["Rightknee_alfred"].y + colas["Leftknee_alfred"].y) / 2
        loc = PIE - R180 @ Vector((0, yf, piso)) + paso; rot = R180.copy()
        # ---------------- golpe de la estalactita y caida boca abajo
        if f_contacto is not None:
            t = f - f_contacto
            st_reac = min(1.0, t / 5.0)
            for n, ax, a in (("Neck_alfred", 0, 0.5), ("Spine2_alfred", 0, 0.25)):
                arm.pose.bones[n].rotation_euler[ax] += a * elastic(st_reac) * (1 if t < 30 else 1)
            if t >= 4:
                v = min(1.0, (t - 4) / 14.0); ang = (math.pi / 2) * v * v
                fwd = R180 @ Vector((0, 1, 0)); fwd = Quaternion((0, 0, 1), math.radians(25) * suave(v)) @ fwd
                eje = Vector((0, 0, 1)).cross(fwd).normalized()
                pivote = PIE + fwd * 0.12
                Rq = Quaternion(eje, ang)
                loc = pivote + Rq @ (loc - pivote) + Vector((0, 0, 0.17 * v * v))
                rot = Rq @ Quaternion((0, 0, 1), math.radians(25) * suave(v)) @ rot
                if v >= 1.0:
                    rb = t - 18
                    if 0 <= rb < 6: loc = loc + Vector((0, 0, 0.06 * math.sin(math.pi * rb / 6)))
                for n in ("RightUpArm_alfred", "LeftUpArm_alfred"):
                    arm.pose.bones[n].rotation_euler.x += -0.6 * suave(v)
        emp.location = loc; emp.rotation_quaternion = rot
        emp.keyframe_insert("location", frame=f); emp.keyframe_insert("rotation_quaternion", frame=f)
        arm.pose.bones["Hips_alfred"].location = (0, 0, 0); arm.pose.bones["Hips_alfred"].keyframe_insert("location", frame=f)
        for n in B["ORDEN"]: arm.pose.bones[n].keyframe_insert("rotation_euler", frame=f)
        bpy.context.view_layer.update()
        Mh = W() @ arm.pose.bones["Rightelbow_alfred"].matrix
        # ---------------- pico
        if f < F_SUELTA_PICO:
            Mp = Mh @ estado_pico["rel"]
            datos_pico[f] = Mp
            if f == F_SUELTA_PICO - 1: estado_pico["v"] = (Mp.translation - datos_pico[f - 1].translation)
            if f == F_LANZA - 1: estado_pico["v"] = (Mp.translation - datos_pico[f - 1].translation)
        elif f == F_SUELTA_PICO:
            tray = _tirar(datos_pico[f - 1], estado_pico["v"] * 1.3, SUELO, F_SUELTA_PICO, F_FIN + 1, rnd)   # queda en el suelo
            datos_pico.update(tray)
        # ---------------- hierro: lo recoge, lo sostiene y lo lanza al techo
        if f == F_AGARRA: rel_hierro = Mh.inverted() @ M_hierro0
        if F_AGARRA <= f < F_LANZA:
            datos_hierro[f] = Mh @ rel_hierro
            if f == F_LANZA - 1: v_h = datos_hierro[f].translation - datos_hierro[f - 1].translation
        elif f == F_LANZA:
            destino = Vector((PIE.x + 0.15, PIE.y - 0.35, -4.15))                     # pega en el techo, junto a la base de la estalactita
            datos_hierro.update(_lanzar(datos_hierro[f - 1], destino, F_LANZA, F_TECHO, rnd, flotar=True))
        # ---------------- estalactita
        if f >= F_ESTAL_SUELTA and f_contacto is None:
            dz = 0.5 * 9.8 * ((f - F_ESTAL_SUELTA) / 24.0) ** 2
            punta_z = estal["punta_z"] - dz
            cabeza = (W() @ arm.pose.bones["face_alfred"].tail).z + 0.12
            if punta_z <= cabeza:
                f_contacto = f; info_fin["contacto"] = f
                estal["dz_contacto"] = dz
    # pico: claves
    if pico.animation_data is None: pico.animation_data_create()
    for f in sorted(datos_pico):
        if f < F0: continue
        B["poner_matriz"](pico, datos_pico[f])
        for dp in ("location", "rotation_quaternion", "scale"): pico.keyframe_insert(dp, frame=f)
    _claves_hierro(hierro, datos_hierro)
    _animar_estalactita(estal, info_fin.get("contacto", F_FIN), F_FIN)
    if info_fin.get("contacto"): _partir(estal, info_fin["contacto"], F_FIN)
    _sonidos(info_fin.get("contacto"))
    sc.frame_set(F0)
    return {"contacto_estalactita": info_fin.get("contacto"), "fin": F_FIN}


def _claves_hierro(h, datos):
    ad = h.animation_data
    if ad and ad.action:
        for lay in ad.action.layers:
            for s in lay.strips:
                for cb in s.channelbags:
                    for fc in cb.fcurves:
                        if not fc.data_path.startswith("hide"):
                            for kp in reversed(list(fc.keyframe_points)):
                                if kp.co[0] >= F_AGARRA: fc.keyframe_points.remove(kp)
    prev = None
    for f in sorted(datos):
        l, q, sc_ = datos[f].decompose(); e = q.to_euler('XYZ', prev) if prev else q.to_euler('XYZ'); prev = e
        h.location = l; h.rotation_euler = e; h.scale = sc_
        for dp in ("location", "rotation_euler", "scale"): h.keyframe_insert(dp, frame=f)


def _estalactita(O, sc):
    i, j = ESTAL_CELDA
    dg = bpy.context.evaluated_depsgraph_get()
    h = sc.ray_cast(dg, Vector((i + 0.5, j + 0.5, -8.0)), Vector((0, 0, 1)), distance=12)
    kc = int(round(h[1].z)) if h[0] else -4
    moldes = {"base": "estalactita_base_-104_-16_-3", "tronco": "estalactita_tronco_-104_-16_-4", "punta": "estalactita_punta_-104_-16_-7"}
    piezas = []
    for n, tipo in enumerate(("base", "tronco", "punta")):
        nombre = "estalactita_cae_%s" % tipo
        o = O.get(nombre) or bpy.data.objects.new(nombre, O[moldes[tipo]].data)
        if not o.users_collection: bpy.data.collections["cueva_bloques"].objects.link(o)
        rec = bpy.data.collections.get("luz_entrada_receptores")
        if rec and o.name not in rec.objects: rec.objects.link(o)
        if o.animation_data: o.animation_data_clear()
        o.parent = None; o.rotation_mode = 'XYZ'; o.rotation_euler = (0, 0, 0); o.location = (i + 0.5, j + 0.5, kc - 1 - n)
        piezas.append(o)
    # agrupar en un empty para animarla entera
    raiz = O.get("estalactita_cae") or bpy.data.objects.new("estalactita_cae", None)
    if not raiz.users_collection: bpy.data.collections["cueva_bloques"].objects.link(raiz)
    if raiz.animation_data: raiz.animation_data_clear()
    raiz.location = (i + 0.5, j + 0.5, kc); raiz.rotation_mode = 'XYZ'; raiz.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    for o in piezas:
        o.parent = raiz; o.matrix_parent_inverse = raiz.matrix_world.inverted()
    return {"raiz": raiz, "punta_z": kc - 3.0, "techo": kc}


def _animar_estalactita(e, f_c, fin):
    r = e["raiz"]; z0 = r.location.z; rnd = random.Random(2)
    for f in range(1, fin + 1):
        if f < F_TECHO:
            r.location.z = z0; r.rotation_euler = (0, 0, 0)
        elif f < F_ESTAL_SUELTA:                                               # el golpe del pico la afloja: tiembla
            a = 0.035 * (1 - (f - F_TECHO) / (F_ESTAL_SUELTA - F_TECHO) * 0.3)
            r.location.z = z0 - 0.01 * (f - F_TECHO) / (F_ESTAL_SUELTA - F_TECHO)
            r.rotation_euler = (a * math.sin(f * 2.3), a * math.cos(f * 1.9), 0)
        elif f <= f_c:
            r.location.z = z0 - 0.5 * 9.8 * ((f - F_ESTAL_SUELTA) / 24.0) ** 2; r.rotation_euler = (0, 0, 0)
        else:
            r.location.z = z0 - e.get("dz_contacto", 0.0)
        r.keyframe_insert("location", frame=f); r.keyframe_insert("rotation_euler", frame=f)


def _partir(e, f_c, fin):
    """al pegarle en la cabeza la estalactita se parte en sus piezas: cada una sale despedida girando y cae al suelo"""
    rnd = random.Random(9); g = 9.8 / 576; sc = bpy.context.scene; r = e["raiz"]
    piezas = sorted([o for o in r.children], key=lambda o: -o.matrix_world.translation.z)
    sc.frame_set(f_c)
    Ms = {o.name: o.matrix_world.copy() for o in piezas}
    previas = {}
    for f in range(1, f_c + 1):
        sc.frame_set(f); previas[f] = {o.name: o.matrix_world.copy() for o in piezas}
    for n, o in enumerate(piezas):
        Mw = Ms[o.name]; p = Mw.translation.copy(); q0 = Mw.to_quaternion(); ang = rnd.uniform(0, 2 * math.pi)
        v = Vector((math.cos(ang) * rnd.uniform(0.8, 1.6), math.sin(ang) * rnd.uniform(0.8, 1.6), rnd.uniform(0.8, 2.2))) / 24
        giro = Vector((rnd.uniform(-0.35, 0.35), rnd.uniform(-0.35, 0.35), rnd.uniform(-0.2, 0.2))); a = Vector((0, 0, 0)); quieto = False
        o.parent = None; o.rotation_mode = 'QUATERNION'
        if o.animation_data: o.animation_data_clear()
        for f in range(1, f_c + 1):
            l, qq, _ = previas[f][o.name].decompose(); o.location = l; o.rotation_quaternion = qq
            o.keyframe_insert("location", frame=f); o.keyframe_insert("rotation_quaternion", frame=f)
        for f in range(f_c + 1, fin + 1):
            if not quieto:
                p += v; v.z -= g; a += giro
                if p.z <= SUELO + 0.15:
                    p.z = SUELO + 0.15; v = Vector((v.x * 0.3, v.y * 0.3, -v.z * 0.25)); giro *= 0.3
                    if abs(v.z) < 0.012: quieto = True
            q = Quaternion((0, 1, 0), math.radians(90)) @ Quaternion((1, 0, 0), ang) if quieto else q0 @ Euler(a).to_quaternion()
            o.location = p; o.rotation_quaternion = q
            o.keyframe_insert("location", frame=f); o.keyframe_insert("rotation_quaternion", frame=f)


def _tirar(M0, v, suelo, f0, f1, rnd):
    """el pico cae al suelo con rebotes y queda plano"""
    out = {}; p = M0.translation.copy(); q0 = M0.to_quaternion(); s = M0.to_scale(); g = 9.8 / 576
    v = Vector(v); giro = Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.4, 0.4), rnd.uniform(-0.2, 0.2)))
    plano = Quaternion((1, 0, 0), math.radians(90)) @ Quaternion((0, 0, 1), math.radians(30))
    ang = Vector((0, 0, 0)); rebotes = 0
    for f in range(f0, f1):
        p += v; v.z -= g; ang += giro
        if p.z <= suelo + 0.03 and v.z < 0:
            p.z = suelo + 0.03; rebotes += 1; v = Vector((v.x * 0.4, v.y * 0.4, -v.z * 0.3)); giro *= 0.4
            if rebotes > 2: v = Vector((0, 0, 0)); giro = Vector((0, 0, 0))
        q = q0 @ Euler(ang).to_quaternion()
        k = min(1.0, (f - f0) / 14.0)
        q = q.slerp(plano, suave(k))
        out[f] = Matrix.LocRotScale(p.copy(), q, s)
    return out


def _lanzar(M0, destino, f0, f1, rnd, flotar=False):
    """lanzado al techo: llega a `destino` en f1 girando, rebota y cae al suelo"""
    out = {}; p0 = M0.translation.copy(); q0 = M0.to_quaternion(); s = M0.to_scale(); g = 9.8 / 576
    T = f1 - f0; v = (destino - p0 - Vector((0, 0, -0.5 * g * T * T))) / T
    p = p0.copy(); ang = 0.0
    for f in range(f0, f1 + 1):
        t = f - f0; p = p0 + v * t + Vector((0, 0, -0.5 * g * t * t)); ang += 0.55
        out[f] = Matrix.LocRotScale(p, q0 @ Quaternion((1, 0, 0), ang), s)
    vb = Vector((0.03, 0.02, -0.02)); pb = p.copy(); qb = out[f1].to_quaternion()
    plano = Quaternion((1, 0, 0), math.radians(90)) @ Quaternion((0, 0, 1), math.radians(-40))
    for f in range(f1 + 1, F_FIN + 1):
        if pb.z > SUELO + 0.03:
            pb = pb + vb; vb.z -= g; ang += 0.35; qb = q0 @ Quaternion((1, 0, 0), ang)
            if pb.z <= SUELO + 0.03: pb.z = SUELO + 0.03; qb = plano
        if flotar and pb.z <= SUELO + 0.031:                                    # como objeto soltado: flota y gira
            if "f_toca" not in locals(): f_toca = f
            fl = f - f_toca
            base = Quaternion((1, 0, 0), math.radians(91.5)) @ Quaternion((0, 1, 0), math.radians(-25))
            q = Quaternion((0, 0, 1), 2 * math.pi * fl / 72.0) @ base
            z = SUELO + 0.03 + min(1.0, fl / 10.0) * 0.52 + 0.06 * math.sin(2 * math.pi * fl / 48.0)
            out[f] = Matrix.LocRotScale(Vector((pb.x, pb.y, z)), q, s)
            continue
        out[f] = Matrix.LocRotScale(pb.copy(), qb if pb.z > SUELO + 0.031 else plano, s)
    return out


def _sonidos(f_contacto):
    import importlib.util, sys
    m = sys.modules.get("alfred_sonidos_local")
    if m is None:
        spec = importlib.util.spec_from_file_location("alfred_sonidos_local", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py")
        m = importlib.util.module_from_spec(spec); sys.modules["alfred_sonidos_local"] = m; spec.loader.exec_module(m); m.register()
    sc = bpy.context.scene; p = sc.mcsnd; m.indice(p, forzar=True); ed = sc.sequence_editor or sc.sequence_editor_create()
    for t in [t for t in m._strips(ed) if t.name.startswith(m.PREFIJO) and t.get("mcsnd_origen") == ORIGEN]: m._strips(ed).remove(t)
    rng = m.rng_de(p)
    def poner(evs, f, vol, grupo="golpes"):
        for ev in evs:
            r = m.rutas_de(p, ev)
            if r:
                t = m.colocar(bpy.context, p, r, int(f), grupo, ev.replace(".", "_"), vol, 0, rng)
                if t: t["mcsnd_origen"] = ORIGEN
                return
    poner(["block.stone.hit"], F_SUELTA_PICO + 5, 0.7)                                 # el pico cae al suelo
    poner(["block.stone.step"], 238, 0.4, "pasos"); poner(["block.stone.step"], 262, 0.4, "pasos")
    poner(["entity.player.attack.sweep", "entity.player.attack.nodamage"], F_LANZA - 2, 0.5)
    poner(["block.stone.hit"], F_TECHO, 0.9)                                           # el hierro pega en el techo
    poner(["block.pointed_dripstone.break", "block.stone.break"], F_TECHO + 1, 0.6)
    poner(["block.stone.fall"], F_TECHO + 14, 0.6)                                     # el hierro vuelve al suelo
    poner(["block.pointed_dripstone.hit", "block.stone.hit"], F_ESTAL_SUELTA - 10, 0.4)
    poner(["block.pointed_dripstone.break", "block.stone.break"], F_ESTAL_SUELTA, 0.9)
    if f_contacto:
        poner(["block.pointed_dripstone.land", "block.stone.fall"], f_contacto, 1.0)
        poner(["entity.player.attack.knockback"], f_contacto, 0.9)
        poner(["entity.player.big_fall", "entity.generic.big_fall"], f_contacto + 18, 1.0)
        poner(["block.pointed_dripstone.land", "block.stone.fall"], f_contacto + 14, 0.8)
