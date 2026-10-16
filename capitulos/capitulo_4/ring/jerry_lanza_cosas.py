# -*- coding: utf-8 -*-
"""base_ranas_3, despues de la paliza (pelea_victoria.py), desde F0:
 - Alfred (tirado boca arriba) levanta la cabeza y busca a Jerry entre el publico (dos veces), lo encuentra y le dice
   "tira la toalla"; Jerry: "¿toalla? ¿de que hablas?"; Alfred: "bueno, entonces tira algo". (Sin audio: solo cuerpo/cabeza.)
 - Alfred se arrastra y queda CASI SENTADO apoyado en la valla norte, mirando a Jerry.
 - Jerry (de pie en la valla sur) le lanza: un STICK, un bloque de COBBLESTONE y por ultimo un POLLO. Cada uno: se agacha
   a tomarlo, lo sube en la pata derecha, carga, lo lanza; vuela en parabola girando y le da en la CARA a Alfred; rebota y cae.
 - Tras el primer impacto Alfred levanta la mano derecha pidiendo que pare; cada golpe lo deja mas aturdido; el pollo lo
   deja inconsciente: se desliza y queda boca arriba. El pollo cae al suelo mareado. La rana sigue celebrando.
Objetos: objetos/vanilla/stick/stick.blend (stick), bloques_dinamicos/cobblestone.blend (cobblestone, escalado),
estructura_lista/chicken/chicken_1.blend (pollo). Coleccion "lanzados_jerry". Repetible (reusa los objetos).
Uso (exec en Blender): construir()   (despues de pelea_victoria.py)
"""
import bpy, math, random
from mathutils import Vector, Euler, Quaternion, Matrix

DIR = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/"
BASE = "C:/Users/user/Desktop/Alfred_Animacion/"
bpy.app.driver_namespace["pelea_variante"] = "ranas3"
L = {"__name__": "luch"}
exec(open(DIR + "luchadores_rodean.py", encoding="utf-8").read(), L)
ik2, apuntar, rotar_mundo, ss, desenrollar = L["ik2"], L["apuntar"], L["rotar_mundo"], L["ss"], L["desenrollar"]
UP = L["UP"]
DR = {"__name__": "derribo"}
exec(open(DIR + "pelea_derribo.py", encoding="utf-8").read(), DR)
A_HUESOS, G_HUESOS, leer, resp, rebote, snap = DR["A_HUESOS"], DR["G_HUESOS"], DR["leer"], DR["resp"], DR["rebote"], DR["snap"]
sc = bpy.context.scene; vl = bpy.context.view_layer
D = math.radians

F0, F_FIN = 536, 930
BUSCA = [(538, 552, Vector((-40.6, -12.6, 10.2))), (556, 570, Vector((-34.3, -13.6, 10.2)))]
ENCUENTRA = 574
HABLA_A1, HABLA_J, HABLA_A2 = (586, 612), (616, 646), (650, 670)
SIENTA = (672, 688)
# (objeto, agarra, suelta, impacto, aturdimiento tras el golpe)
LANZA = [("stick", 688, 708, 726, 0.35), ("cobble", 736, 756, 774, 0.7), ("pollo", 788, 810, 830, 1.0)]
PARE = (730, 742)
# fisica de cada objeto: masa relativa (fuerza del golpe en la cabeza), de que lado le pega (-1 izq. de Alfred, +1 der.),
# restitucion contra la cara y contra el suelo, y hacia donde sale despedido (para que queden dispersos)
FISICA = {"stick": dict(masa=0.55, lado=-1.0, e_cara=0.45, e_suelo=0.40, dispersa=Vector((-1.15, -0.45, 0)), empuje=1.6),
          "cobble": dict(masa=1.0, lado=0.25, e_cara=0.28, e_suelo=0.25, dispersa=Vector((0.45, -1.3, 0)), empuje=2.1),
          "pollo": dict(masa=0.8, lado=1.0, e_cara=0.32, e_suelo=0.30, dispersa=Vector((1.2, -0.55, 0)), empuje=2.3)}
LIMITES = dict(x0=-40.35, x1=-34.65, y0=-14.35, y1=-9.8)     # dentro de la valla
# huida del pollo: voltereta en el aire, cae de pie, se marea, corre a la valla este (hueco entre la vaca y el guardian 12),
# la salta aleteando y se va corriendo de la escena
POLLO = dict(vuelta=16, mareo=6, aterriza_dist=0.9, valla_in=Vector((-34.85, -12.65)), valla_out=Vector((-34.05, -12.72)),
             salto=11, sale=Vector((-31.4, -12.95)), vel=2.0, cima_pies=10.12)
CICLO_POLLO = DIR + "pollo_ciclo_caminar.json"           # ciclo de caminar del usuario (las patas van adelante y atras: eje Z de la cadera)
DESMAYO = (832, 856)
SENTADO_CADERA = Vector((-36.75, -9.98, 9.14))    # cadera apoyada contra la valla norte
RECLINA = 32.0                                    # grados hacia atras (espalda en la valla)
SUELO = 9.0
J_HUESOS = None                                   # (se leen del rig de Jerry)


SENTADO_JSON = "C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/poses/sentando de espalda a la vallas.json"


def sentado_usuario():
    import json
    d = json.load(open(SENTADO_JSON, encoding="utf-8"))["poses"][0]
    r = d["root"]
    return {"loc": tuple(r["location"].values()), "rot": tuple(r["rotation_euler_deg"].values()),
            "bones": {h: Vector(tuple(v["local_space"]["rotation_euler_rad"].values())) for h, v in d["bones"].items()}}


def bvh_valla():
    from mathutils.bvhtree import BVHTree
    o = bpy.data.objects["valla_ring_lucha"]; M = o.matrix_world
    return BVHTree.FromPolygons([M @ v.co for v in o.data.vertices], [tuple(p.vertices) for p in o.data.polygons])


def choca(r, fence):
    """alguna malla de Alfred (sin ojos) se mete en la valla"""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    for x in r.children:
        if x.type != 'MESH' or not x.name.startswith("Mesh_"): continue
        e = x.evaluated_get(dg); me = e.to_mesh(); M = x.matrix_world
        t = BVHTree.FromPolygons([M @ v.co for v in me.vertices], [tuple(p.vertices) for p in me.polygons]); e.to_mesh_clear()
        if t.overlap(fence): return True
    return False


# valla norte (medida): cara interior de los postes y de las barras, postes, alturas de las barras
VALLA_N = dict(y_poste=-9.625, y_barra=-9.5625, postes=(-38.5, -37.5, -36.5, -35.5, -34.5), medio_poste=0.125,
               barras=((9.375, 9.5625), (9.75, 9.9375)), alto=10.0, tolerancia=0.01)


def penetracion(r):
    """cuanto se mete (m, hacia +y) la malla de Alfred en la valla norte: postes y barras (los huecos entre barras no cuentan)"""
    import numpy as np
    V = VALLA_N; dg = bpy.context.evaluated_depsgraph_get(); pen = 0.0
    for x in r.children:
        if x.type != 'MESH' or not x.name.startswith("Mesh_"): continue
        e = x.evaluated_get(dg); me = e.to_mesh()
        co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); e.to_mesh_clear()
        M = np.array(x.matrix_world); w = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
        w = w[(w[:, 1] > V["y_poste"]) & (w[:, 2] < V["alto"])]
        if not len(w): continue
        en_poste = np.zeros(len(w), bool)
        for px in V["postes"]: en_poste |= np.abs(w[:, 0] - px) < V["medio_poste"]
        if en_poste.any(): pen = max(pen, float((w[en_poste, 1] - V["y_poste"]).max()))
        en_barra = np.zeros(len(w), bool)
        for z0, z1 in V["barras"]: en_barra |= (w[:, 2] > z0) & (w[:, 2] < z1)
        en_barra &= w[:, 1] > V["y_barra"]
        if en_barra.any(): pen = max(pen, float((w[en_barra, 1] - V["y_barra"]).max()))
    return pen


POLLO_T = {}


def apoyar_pollo():
    """en los tramos en que el pollo esta en el suelo (mareo, corre, huye) sus patas pisan justo z = 9 (mide la malla)"""
    o = bpy.data.objects["pollo_lanzado"]; a = o.animation_data.action
    fz = next(c for l in a.layers for st in l.strips for cb in st.channelbags for c in cb.fcurves if c.data_path == "location" and c.array_index == 2)
    objs = [o] + list(o.children_recursive); ocultos = [x for x in objs if x.hide_viewport]
    tramos = [POLLO_T["mareo"], POLLO_T["corre"], (POLLO_T["huye"][0], min(F_FIN, POLLO_T["huye"][1]))]
    frames = sorted({f for a_, b_ in tramos for f in range(a_, b_ + 1)})
    ajuste = {}
    for f in frames:
        sc.frame_set(f)
        for x in objs: x.hide_viewport = False                               # (sus claves de visibilidad lo ocultan al salir)
        vl.update(); dg = bpy.context.evaluated_depsgraph_get(); z = 1e9
        for x in o.children_recursive:
            if x.type == 'MESH':
                e = x.evaluated_get(dg); M = x.matrix_world; z = min(z, min((M @ v.co).z for v in e.data.vertices))
        ajuste[f] = SUELO - z
    sc.frame_set(sc.frame_current)
    for k in fz.keyframe_points:
        f = int(round(k.co.x))
        if f in ajuste: k.co.y += ajuste[f]; k.handle_left.y += ajuste[f]; k.handle_right.y += ajuste[f]
    fz.update()
    return {"ajuste_medio_m": round(sum(ajuste.values()) / max(1, len(ajuste)), 3), "frames": len(ajuste)}


def huida_pollo(o, locs, rots, imp, P_i, v_out, alto_r):
    """voltereta (360 grados) cayendo de pie -> mareo -> corre a la valla -> la salta aleteando -> se va de la escena"""
    P = POLLO
    BASE = Euler((D(90), 0, math.pi)).to_quaternion()          # rotacion de reposo del modelo (Y arriba): de pie mirando a +Y
    out_l = [(f, l) for f, l in locs if f <= imp]
    out_r, prev = [], None
    for f, r in rots:                                          # en la pata y en el vuelo tambien lleva la rotacion base
        if f > imp: break
        e = (Euler(r).to_quaternion() @ BASE).to_euler('XYZ', prev) if prev is not None else (Euler(r).to_quaternion() @ BASE).to_euler('XYZ')
        prev = e; out_r.append((f, tuple(e)))
    def yaw_de(d): return math.atan2(-d.x, d.y)
    hz = Vector((v_out.x, v_out.y, 0)); hz = hz.normalized() if hz.length > 1e-4 else Vector((1, 0, 0))
    L1 = Vector((P_i.x, P_i.y, 0)) + hz * P["aterriza_dist"]
    f1 = imp + P["vuelta"]; f2 = f1 + P["mareo"]
    d_run = (P["valla_in"] - L1.xy).length; f3 = f2 + max(6, int(round(d_run / P["vel"] * 24)))
    f4 = f3 + P["salto"]; d_out = (P["sale"] - P["valla_out"]).length; f5 = f4 + int(round(d_out / P["vel"] * 24))
    eje_vuelta = Vector((-hz.y, hz.x, 0))
    yaw_run = yaw_de(Vector((P["valla_in"].x - L1.x, P["valla_in"].y - L1.y, 0)))
    yaw_out = yaw_de(Vector((P["sale"].x - P["valla_out"].x, P["sale"].y - P["valla_out"].y, 0)))
    z0 = SUELO + alto_r
    for f in range(imp + 1, F_FIN + 1):
        if f <= f1:                                                               # voltereta en el aire y cae de pie
            u = (f - imp) / float(P["vuelta"])
            p = Vector((P_i.x, P_i.y, 0)).lerp(L1, ss(u)); p.z = P_i.z * (1 - u) + z0 * u + 0.75 * math.sin(math.pi * u)
            q = Euler((0, 0, yaw_run)).to_quaternion() @ Quaternion(Vector((1, 0, 0)), 2 * math.pi * ss(u))
        elif f <= f2:                                                             # mareado: tambalea
            p = Vector((L1.x, L1.y, z0)); q = Euler((D(8) * math.sin(f * 1.3), D(6) * math.sin(f * 0.9), yaw_run + D(15) * math.sin(f * 0.7))).to_quaternion()
        elif f <= f3:                                                             # corre a la valla
            u = (f - f2) / float(f3 - f2); p = Vector((L1.x, L1.y, 0)).lerp(Vector((P["valla_in"].x, P["valla_in"].y, 0)), u)
            p.z = z0 + 0.04 * abs(math.sin(math.pi * (f - f2) / 3.0)); q = Euler((D(-12), 0, yaw_run)).to_quaternion()
        elif f <= f4:                                                             # salta la valla aleteando
            u = (f - f3) / float(P["salto"]); p = Vector((P["valla_in"].x, P["valla_in"].y, 0)).lerp(Vector((P["valla_out"].x, P["valla_out"].y, 0)), u)
            cima = P["cima_pies"] + alto_r
            p.z = z0 + (cima - z0) * math.sin(math.pi * u) * 1.0 + 0.0
            q = Euler((D(-15) * math.cos(math.pi * u), 0, yaw_run + (yaw_out - yaw_run) * u)).to_quaternion()
        else:                                                                     # se va corriendo
            u = min(1.0, (f - f4) / float(max(1, f5 - f4)))
            p = Vector((P["valla_out"].x, P["valla_out"].y, 0)).lerp(Vector((P["sale"].x, P["sale"].y, 0)), u)
            p.z = z0 + 0.04 * abs(math.sin(math.pi * (f - f4) / 3.0)); q = Euler((D(-12), 0, yaw_out)).to_quaternion()
        q = q @ BASE
        e = q.to_euler('XYZ', prev) if prev is not None else q.to_euler('XYZ'); prev = e
        out_l.append((f, tuple(p))); out_r.append((f, tuple(e)))
    vis = [(1, (1.0,)), (imp - 200 if False else LANZA[2][1], (0.0,)), (f5 + 1, (1.0,))]   # visible desde que Jerry lo agarra hasta que sale
    return out_l, out_r, vis, dict(vuelta=(imp, f1), mareo=(f1, f2), corre=(f2, f3), salto=(f3, f4), huye=(f4, f5))


def ramp(f, a, b): return ss((f - a) / float(max(1e-6, b - a)))


def ventana(f, a, b, c, d): return ramp(f, a, b) * (1 - ramp(f, c, d))


def apuntar_cara(arm, bone, cara_local, objetivo, w, ojo_bone=None):
    """gira `bone` en el mundo para que la cara (vector local del hueso `ojo_bone`) mire a objetivo (con peso w)"""
    if w <= 1e-4: return
    pb = arm.pose.bones[bone]; vl.update()
    M = (arm.matrix_world @ arm.pose.bones[ojo_bone or bone].matrix).to_3x3().normalized()
    cara = (M @ cara_local).normalized()
    ojo = arm.matrix_world @ arm.pose.bones[ojo_bone or bone].head
    q = cara.rotation_difference((objetivo - ojo).normalized())
    ang = q.angle * w
    if ang > 1e-4: rotar_mundo(arm, bone, q.axis, ang)


# ------------------------------------------------------------------ objetos
def anexar(archivo, nombres, coleccion):
    faltan = [n for n in nombres]
    with bpy.data.libraries.load(BASE + archivo, link=False) as (src, dst): dst.objects = [n for n in faltan if n in src.objects]
    out = {}
    for o in dst.objects:
        if o is None: continue
        coleccion.objects.link(o); out[o.name.rsplit(".", 1)[0] if "." in o.name else o.name] = o
    return dst.objects


def preparar_objetos():
    col = bpy.data.collections.get("lanzados_jerry")
    if col is None:
        col = bpy.data.collections.new("lanzados_jerry"); sc.collection.children.link(col)
    obs = {}
    if "stick_lanzado" not in bpy.data.objects:
        o = [x for x in anexar("objetos/vanilla/stick/stick.blend", ["stick"], col) if x][0]; o.name = "stick_lanzado"
    if "cobble_lanzado" not in bpy.data.objects:
        o = [x for x in anexar("bloques_dinamicos/cobblestone.blend", ["cobblestone"], col) if x][0]; o.name = "cobble_lanzado"
    if "pollo_lanzado" not in bpy.data.objects:
        nombres = ["WingR_chicken_1", "WingL_chicken_1", "LegL_chicken_1", "LegL.001_chicken_1", "Head_chicken_1", "Head2_chicken_1",
                   "Eyes_chicken_1", "chicken_1", "Body_chicken_1", "BeakTop_chicken_1", "BeakBottom_chicken_1", "Armature_chicken_1"]
        nuevos = [x for x in anexar("estructura_lista/chicken/chicken_1.blend", nombres, col) if x]
        raiz = next(x for x in nuevos if x.parent is None and x.type == 'EMPTY'); raiz.name = "pollo_lanzado"
        for x in nuevos:
            if x.type == 'ARMATURE': x.name = "pollo_lanzado_arm"
            if x.animation_data: x.animation_data.action = None
    for n in ("stick_lanzado", "cobble_lanzado", "pollo_lanzado"):
        o = bpy.data.objects[n]; o.parent = None if n != "pollo_lanzado" else o.parent
        obs[n] = o
    obs["cobble_lanzado"].scale = (0.42, 0.42, 0.42)
    obs["stick_lanzado"].scale = (0.6, 0.6, 0.6)
    return obs


def medidas(o):
    """semi-alto (z) del objeto en su orientacion de reposo, para apoyarlo en el suelo"""
    vl.update(); dg = bpy.context.evaluated_depsgraph_get(); zs = []
    for x in [o] + list(o.children_recursive):
        if x.type == 'MESH':
            e = x.evaluated_get(dg); M = x.matrix_world
            zs += [(M @ v.co).z for v in e.data.vertices]
    return (min(zs), max(zs)) if zs else (o.location.z, o.location.z)


def construir():
    sc.frame_end = max(sc.frame_end, F_FIN)
    obs = preparar_objetos()
    ra, aa = bpy.data.objects["alfred"], bpy.data.objects["Armature"]
    rj, aj = bpy.data.objects["jerry"], bpy.data.objects["Dog_001_rig"]
    rg, ag = bpy.data.objects["guard_ribbit_1"], bpy.data.objects["main_guard_ribbit_1"]
    PA, PJ, PG = aa.pose.bones, aj.pose.bones, ag.pose.bones
    WA, WJ, WG = (lambda: aa.matrix_world), (lambda: aj.matrix_world), (lambda: ag.matrix_world)
    # ---------------- estados de partida
    fa = F0 - 1
    ar = leer(ra, ("location", "rotation_euler"), fa)
    A_loc = Vector([ar[("location", i)] for i in range(3)]); A_rot = Euler([ar[("rotation_euler", i)] for i in range(3)])
    rotA = {h: Vector([leer(aa, ('pose.bones["%s"].rotation_euler' % h,), fa).get(('pose.bones["%s"].rotation_euler' % h, i), 0.0) for i in range(3)]) for h in A_HUESOS}
    hipsA = Vector([leer(aa, ('pose.bones["Hips_alfred"].location',), fa).get(('pose.bones["Hips_alfred"].location', i), 0.0) for i in range(3)])
    fj = 450
    jr0 = leer(rj, ("location", "rotation_euler"), fj)
    J_loc = Vector([jr0[("location", i)] for i in range(3)]); J_rot = Euler([jr0[("rotation_euler", i)] for i in range(3)])
    j_bones = [pb.name for pb in PJ]
    rotJ = {h: Vector([leer(aj, ('pose.bones["%s"].rotation_euler' % h,), fj).get(('pose.bones["%s"].rotation_euler' % h, i), 0.0) for i in range(3)]) for h in j_bones}
    gr0 = leer(rg, ("location", "rotation_euler"), 600)
    G_loc = Vector([gr0[("location", i)] for i in range(3)]); G_rot = Euler([gr0[("rotation_euler", i)] for i in range(3)])
    rotG = {h: Vector([leer(ag, ('pose.bones["%s"].rotation_euler' % h,), 600).get(('pose.bones["%s"].rotation_euler' % h, i), 0.0) for i in range(3)]) for h in G_HUESOS}
    todos = [ra, rj, rg] + [obs[n] for n in obs]
    ocultos = [o.name for r in todos for o in [r] + list(r.children_recursive) if o.hide_viewport]
    for n in ocultos: bpy.data.objects[n].hide_viewport = False
    acts = {o.name: o.animation_data.action for o in (ra, aa, rj, aj, rg, ag) if o.animation_data}
    for o in (ra, aa, rj, aj, rg, ag): o.animation_data.action = None
    cara_A = (aa.data.bones["face_alfred"].matrix_local.to_3x3().inverted() @ Vector((0, 1, 0))).normalized()
    cara_J = (aj.data.bones["scull"].matrix_local.to_3x3().inverted() @ Vector((0, 1, 0))).normalized()
    hips_local = Vector(aa.data.bones["Hips_alfred"].head_local)
    out_a = {"loc": [], "rot": [], "h": {h: [] for h in A_HUESOS}, "hips": []}
    out_j = {h: [] for h in j_bones}; out_g = {"loc": [], "rot": [], "h": {h: [] for h in G_HUESOS}}
    cara_alfred = {}; mano_jerry = {}; cabeza_jerry = {}
    try:
        # ================= ALFRED =================
        R_l = A_rot.to_quaternion(); L_l = A_loc.copy()
        SJ = sentado_usuario()                                         # pose del usuario: sentado de espaldas a la valla
        R_s = Euler(tuple(D(x) for x in SJ["rot"])).to_quaternion(); L_s = Vector(SJ["loc"])
        R_f = Euler((D(90), 0, math.pi)).to_quaternion()             # desmayado boca arriba (cabeza hacia la valla)
        # cadera sentado (mundo) -> al desmayarse se desliza hacia el ring y queda tendido
        ra.location = L_s; ra.rotation_euler = R_s.to_euler()
        for h in A_HUESOS: PA[h].rotation_mode = 'XYZ'; PA[h].rotation_euler = SJ["bones"].get(h, Vector((0, 0, 0)))
        PA["Hips_alfred"].location = (0, 0, 0); vl.update()
        cad_s = WA() @ PA["Hips_alfred"].head
        SEP0 = max(0.0, penetracion(ra) - VALLA_N["tolerancia"])          # separacion fija de la valla (la pose sentado sin golpes)
        L_f = Vector((cad_s.x, cad_s.y - 0.55 - 0.88, L_s.z))           # raiz (pies) del tendido final
        z_torso = None
        fence = bvh_valla()
        aturdido = lambda f: max([0.0] + [at * ramp(f, imp, imp + 6) for n, ag_, su, imp, at in LANZA])
        def resorte(t):
            """latigazo: pico ~2 f despues del impacto, vuelve pasando del centro (rebote) y se asienta"""
            return 0.0 if t < 0 else 1.35 * math.exp(-0.25 * t) * math.sin(2 * math.pi * t / 9.0)
        def impacto(f, retraso=0):
            return sum(resorte(f - imp - retraso) * FISICA[n]["masa"] * (0.8 + 0.5 * at) for n, ag_, su, imp, at in LANZA)
        def lateral(f, retraso=0):
            return sum(resorte(f - imp - retraso) * FISICA[n]["masa"] * FISICA[n]["lado"] for n, ag_, su, imp, at in LANZA)
        necesita = {}
        for f in range(F0, F_FIN + 1):
            t_s = ramp(f, SIENTA[0], SIENTA[1]); t_d = ramp(f, DESMAYO[0], DESMAYO[1])
            # ---- raiz: tendido -> sentado (pose del usuario) -> desmayado boca arriba
            if t_d <= 0:
                R = R_l.slerp(R_s, t_s); L = L_l.lerp(L_s, t_s) + Vector((0, 0, 0.10 * math.sin(math.pi * t_s)))
            else:
                R = R_s.slerp(R_f, t_d * t_d); L = L_s.lerp(L_f, t_d)
            ra.rotation_euler = R.to_euler('XYZ', ra.rotation_euler); ra.location = L
            # ---- huesos base: pose de tendido -> pose sentado del usuario -> flojo (sin pose) al desmayarse
            for h in A_HUESOS:
                PA[h].rotation_mode = 'XYZ'
                qa = Euler(rotA[h]).to_quaternion(); qb = Euler(SJ["bones"].get(h, Vector((0, 0, 0)))).to_quaternion()
                q = qa.slerp(qb, t_s)
                if t_d > 0: q = q.slerp(Quaternion(), t_d * 0.8)
                PA[h].rotation_euler = q.to_euler('XYZ')
            PA["Hips_alfred"].location = hipsA * (1 - ramp(f, SIENTA[0], SIENTA[0] + 10))
            vl.update()
            M3 = ra.matrix_world.to_3x3(); fw = (M3 @ Vector((0, 1, 0))).normalized(); up = (M3 @ Vector((0, 0, 1))).normalized(); rt = (M3 @ Vector((1, 0, 0))).normalized()
            # ---- tendido: levanta la cabeza y los hombros para buscar
            if t_s < 1:
                lev = ramp(f, F0, F0 + 8) * (1 - t_s)
                for h, k in (("Spine1_alfred", 0.5), ("Spine2_alfred", 0.5)): rotar_mundo(aa, h, rt, D(-16.0 * lev * k))
            # ---- a quien mira
            jerry_cab = J_loc + Vector((0, 0.2, 1.2))
            mira, wm = None, 0.0
            for a_, b_, P in BUSCA:
                w_ = ventana(f, a_, a_ + 5, b_ - 4, b_)
                if w_ > wm: mira, wm = P, w_
            if f >= ENCUENTRA - 4: mira, wm = jerry_cab, ramp(f, ENCUENTRA - 4, ENCUENTRA + 3)
            at = aturdido(f)
            if mira is not None and t_d < 1:
                apuntar_cara(aa, "Neck_alfred", cara_A, mira, 0.55 * wm * (1 - 0.6 * at) * (1 - t_d), "face_alfred")
                apuntar_cara(aa, "face_alfred", cara_A, mira, 0.8 * wm * (1 - 0.6 * at) * (1 - t_d))
            for a_, b_ in (HABLA_A1, HABLA_A2):
                if a_ <= f <= b_: rotar_mundo(aa, "Neck_alfred", rt, D(4 * math.sin(2 * math.pi * (f - a_) / 9.0)))
            # ---- golpes: latigazo (la cabeza va atras y al lado); aturdido: la cabeza cuelga y se bambolea
            imp = impacto(f)
            rotar_mundo(aa, "Spine2_alfred", rt, D(7 * impacto(f, 2)))           # el pecho acompana despues (inercia)
            rotar_mundo(aa, "Neck_alfred", rt, D(30 * imp))                         # la cabeza sale atras
            rotar_mundo(aa, "face_alfred", rt, D(14 * impacto(f, 1)))               # la cara sigue a la nuca
            rotar_mundo(aa, "Neck_alfred", up, D(-24 * lateral(f)))                  # y al lado contrario de donde le pega
            rotar_mundo(aa, "face_alfred", up, D(-12 * lateral(f, 1)))
            if at > 0 and t_d < 1:
                rotar_mundo(aa, "Neck_alfred", rt, D(-24 * at * (0.8 + 0.2 * math.sin(f * 0.13))))
                rotar_mundo(aa, "Neck_alfred", fw, D(16 * at * math.sin(f * 0.07)))
                rotar_mundo(aa, "Spine2_alfred", fw, D(7 * at))                     # se ladea
            if t_d > 0: rotar_mundo(aa, "Neck_alfred", fw, D(25 * t_d))
            vl.update()
            # ---- brazos: tendido con el gesto al hablar; sentado con la pose del usuario + "para!" con la derecha
            for s, lado in (("Right", 1), ("Left", -1)):
                sh = WA() @ PA[s + "UpArm_alfred"].head
                w_ = 0.0; T = None
                if s == "Right" and t_s < 1 and any(a_ <= f <= b_ + 6 for a_, b_ in (HABLA_A1, HABLA_A2)):
                    w_ = max(ventana(f, a_, a_ + 6, b_, b_ + 6) for a_, b_ in (HABLA_A1, HABLA_A2)) * (1 - t_s)
                    T = sh + fw * 0.55 + (jerry_cab - sh).normalized() * 0.2 + up * 0.1 + fw * 0.05 * math.sin(f * 0.6)
                if s == "Right" and t_s >= 1:
                    w_ = ramp(f, PARE[0], PARE[1]) * (1 - 0.45 * ramp(f, LANZA[1][3], LANZA[1][3] + 8)) * (1 - ramp(f, LANZA[2][3], LANZA[2][3] + 4))
                    T = sh + (jerry_cab - sh).normalized() * 0.62 + UP * 0.12 + rt * 0.05 * math.sin(f * 1.7) * (0.5 + at)
                if T is not None and w_ > 1e-3:
                    b0 = (PA[s + "UpArm_alfred"].rotation_euler.copy(), PA[s + "elbow_alfred"].rotation_euler.copy())
                    ik2(aa, s + "UpArm_alfred", s + "elbow_alfred", T, -up + rt * lado * 0.4)
                    for bn, e0 in zip((s + "UpArm_alfred", s + "elbow_alfred"), b0):
                        PA[bn].rotation_euler = e0.to_quaternion().slerp(PA[bn].rotation_euler.to_quaternion(), w_).to_euler('XYZ', PA[bn].rotation_euler)
                sac = impacto(f, 2)                                                  # sacudon del brazo con el golpe
                if sac > 0.01: rotar_mundo(aa, s + "UpArm_alfred", rt, D(-10 * sac))
            vl.update()
            # ---- apoyo: tendido -> torso a su altura; sentado -> la raiz del usuario; desmayado -> torso en el suelo
            dg = bpy.context.evaluated_depsgraph_get(); zb = 1e9
            for x in ra.children:
                if x.type == 'MESH' and x.name == "Mesh_1_alfred":
                    e = x.evaluated_get(dg); Mx = x.matrix_world; zb = min((Mx @ v.co).z for v in e.data.vertices)
            if z_torso is None: z_torso = zb
            if t_s <= 0: ra.location.z += z_torso - zb
            elif t_d > 0: ra.location.z += (SUELO - zb) * t_d
            vl.update()
            # ---- las mallas no atraviesan la valla: cuanto hay que separarlo hacia el ring (-y)
            necesita[f] = 0.0
            if f >= SIENTA[0]:                                                  # separacion FIJA (no se mueve antes de los golpes)
                ra.location.y -= SEP0 * t_s; vl.update()
                for _it in range(14):                                           # la cabeza que se va atras rebota en la valla
                    if penetracion(ra) <= VALLA_N["tolerancia"]: break
                    rotar_mundo(aa, "Neck_alfred", rt, D(-3.0)); vl.update()
                resto = max(0.0, penetracion(ra) - VALLA_N["tolerancia"])
                if resto > 0 and (f < SIENTA[1] or t_d > 0):                      # al sentarse / al quedar tendido el cuerpo ya se mueve:
                    ra.location.y -= resto; vl.update()                             # ahi si se separa lo justo
                necesita[f] = max(0.0, penetracion(ra) - VALLA_N["tolerancia"])
            cara_alfred[f] = WA() @ PA["face_alfred"].head + (WA() @ PA["face_alfred"].tail - WA() @ PA["face_alfred"].head) * 0.35 + ((WA().to_3x3() @ PA["face_alfred"].matrix.to_3x3()) @ cara_A).normalized() * 0.12
            out_a["loc"].append((f, tuple(ra.location))); out_a["rot"].append((f, tuple(ra.rotation_euler)))
            out_a["hips"].append((f, tuple(PA["Hips_alfred"].location)))
            for h in A_HUESOS: out_a["h"][h].append((f, tuple(PA[h].rotation_euler)))
        info_valla = {"separacion_fija_m": round(SEP0, 3), "frames_que_aun_tocan": sum(1 for f in necesita if necesita[f] > 0)}
        # ================= JERRY =================
        rj.location = J_loc; rj.rotation_euler = J_rot
        def guard_pos(f):
            return G_loc + Vector((0, 0, 0.6))
        for f in range(451, F_FIN + 1):
            for h in j_bones: PJ[h].rotation_mode = 'XYZ'; PJ[h].rotation_euler = rotJ[h]
            br = math.sin(2 * math.pi * f / 70.0)
            rotar_mundo(aj, "spine_4", Vector((1, 0, 0)), D(0.8 * br))
            vl.update()
            R3 = rj.matrix_world.to_3x3(); fwj = (R3 @ Vector((0, 1, 0))).normalized(); rtj = (R3 @ Vector((1, 0, 0))).normalized()
            # a quien mira
            if f < ENCUENTRA - 2:
                objetivo = Vector(guard_pos(f)) if f > 455 else None
            else:
                objetivo = cara_alfred.get(f, cara_alfred[F0])
            # lanzamientos: se agacha (mira abajo), sube con el objeto, carga, lanza (mira a Alfred)
            lanz = None
            for n, ag_, su, imp, at in LANZA:
                if ag_ - 2 <= f <= su + 14: lanz = (n, ag_, su, imp)
            if objetivo is not None:
                apuntar_cara(aj, "scull_1", cara_J, objetivo, 0.85, "scull")
            if HABLA_J[0] <= f <= HABLA_J[1]:                                   # "¿toalla? ¿de que hablas?": ladea la cabeza, orejas
                k = ventana(f, HABLA_J[0], HABLA_J[0] + 5, HABLA_J[1] - 5, HABLA_J[1])
                rotar_mundo(aj, "scull_1", fwj, D(14 * k * math.sin(2 * math.pi * (f - HABLA_J[0]) / 30.0)))
                for e_ in ("ear.L", "ear.R"): rotar_mundo(aj, e_, rtj, D(-18 * k))
            if lanz:
                n, ag_, su, imp = lanz
                agacha = ventana(f, ag_ - 2, ag_ + 3, ag_ + 6, ag_ + 11)              # baja a tomarlo
                rotar_mundo(aj, "spine_4", rtj, D(25 * agacha)); rotar_mundo(aj, "spine_1", rtj, D(35 * agacha))
                carga = ramp(f, ag_ + 9, su - 1) ; suelta = snap((f - su + 1) / 3.0) if f >= su - 1 else 0.0
                vuelve = ramp(f, su + 4, su + 14)
                ang = -120 * carga * (1 - suelta) + 45 * suelta * (1 - vuelve)         # la pata derecha sube atras y latiguea
                rotar_mundo(aj, "front_shoulder.R", rtj, D(ang))
                rotar_mundo(aj, "spine_4", rtj, D(-12 * carga * (1 - suelta) + 10 * suelta * (1 - vuelve)))   # el cuerpo acompana
                rotar_mundo(aj, "spine_6", UP, D(-14 * carga * (1 - suelta) + 18 * suelta * (1 - vuelve)))
            vl.update()
            mano_jerry[f] = WJ() @ PJ["front_toe.R"].tail
            cabeza_jerry[f] = WJ() @ PJ["scull"].head
            for h in j_bones: out_j[h].append((f, tuple(PJ[h].rotation_euler)))
        # ================= RANA: sigue celebrando junto a Alfred =================
        rg.location = G_loc; rg.rotation_euler = G_rot
        for f in range(601, F_FIN + 1):
            for h in G_HUESOS: PG[h].rotation_mode = 'XYZ'; PG[h].rotation_euler = rotG[h]
            rg.location = G_loc + Vector((0, 0, 0.03 * abs(math.sin(math.pi * f / 8.0))))
            vl.update()
            R3 = rg.matrix_world.to_3x3(); fw = (R3 @ Vector((0, 1, 0))).normalized(); rt = (R3 @ Vector((1, 0, 0))).normalized(); up = (R3 @ Vector((0, 0, 1))).normalized()
            rotar_mundo(ag, "body_guard_ribbit_1", UP, D(10 * math.sin(2 * math.pi * f / 18.0)))
            for s, lado, fase in (("left", -1, math.pi), ("right", 1, 0.0)):
                b = "%s_arm_guard_ribbit_1" % s; hom = WG() @ PG[b].head
                bomba = 0.5 + 0.5 * math.sin(2 * math.pi * f / 12.0 + fase)
                apuntar(ag, b, lambda b=b: WG() @ PG[b].tail, hom + up * (0.26 + 0.08 * bomba) + rt * lado * (0.10 + 0.04 * bomba) + fw * 0.03)
            out_g["loc"].append((f, tuple(rg.location))); out_g["rot"].append((f, tuple(rg.rotation_euler)))
            for h in G_HUESOS: out_g["h"][h].append((f, tuple(PG[h].rotation_euler)))
    finally:
        for o in (ra, aa, rj, aj, rg, ag): o.animation_data.action = acts.get(o.name)
        for n in ocultos: bpy.data.objects[n].hide_viewport = True

    # ================= OBJETOS: en la pata, vuelo en parabola, choque con la cara, rebotes, se deslizan y quedan dispersos ====
    g = 9.8; fps = 24.0; dt = 1.0 / fps; rng = random.Random(4)
    info = {}
    for n, ag_, su, imp, at in LANZA:
        o = obs[{"stick": "stick_lanzado", "cobble": "cobble_lanzado", "pollo": "pollo_lanzado"}[n]]; F = FISICA[n]
        o.animation_data_clear(); o.rotation_mode = 'XYZ'
        # orientacion de reposo (apoyado en su lado mas estable) y altura del origen sobre el suelo en esa orientacion
        o.rotation_euler = (0, 0, 0); zmn, zmx = medidas(o)
        dims = o.dimensions.copy()
        largo_vertical = n == "stick" and dims.z >= max(dims.x, dims.y)
        yaw_r = rng.uniform(0, math.pi)
        q_rest = Euler((D(90) if largo_vertical else 0.0, 0, yaw_r)).to_quaternion()
        if n == "pollo": q_rest = Euler((0, 0, yaw_r)).to_quaternion() @ Euler((D(90), 0, math.pi)).to_quaternion()   # de pie (modelo Y arriba)
        o.rotation_euler = q_rest.to_euler(); zmn_r, _ = medidas(o); alto_r = o.location.z - zmn_r
        o.rotation_euler = (0, 0, 0); radio = max(dims) * 0.5
        # vuelo
        P_r = mano_jerry[su] + Vector((0, 0.08, 0.05)); P_i = cara_alfred[imp]
        T = (imp - su) / fps; dz = P_i.z - P_r.z; vz0 = (dz + 0.5 * g * T * T) / T
        w_vuelo = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))).normalized() * (D(720) if n != "pollo" else D(260))
        v_in = (P_i - P_r) / T; v_in.z = vz0 - g * T
        # choque con la cara: sale rebotado (restitucion) + empuje lateral distinto para cada objeto (quedan dispersos)
        nrm = (-Vector((v_in.x, v_in.y, 0)).normalized() + Vector((0, 0, 0.45))).normalized()
        vn = v_in.dot(nrm)
        v = v_in - (1 + F["e_cara"]) * vn * nrm
        v = Vector((v.x * 0.35, v.y * 0.35, abs(v.z) * 0.6 + 1.2)) + F["dispersa"].normalized() * F["empuje"]
        v_out0 = v.copy()
        w = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))).normalized() * (D(540) * v.length / 3.0)
        p = P_i.copy(); q = Quaternion(w_vuelo.normalized(), w_vuelo.length * T)
        asentado = 0.0; quieto = False; rebotes = 0
        locs, rots = [], []; prev_e = None
        for f in range(ag_ - 1, F_FIN + 1):
            if f < ag_: pp = mano_jerry.get(ag_, P_r); qq = Quaternion()
            elif f <= su:                                                         # en la pata
                pp = mano_jerry[f] + Vector((0, 0.08, 0.05)); qq = Euler((0, 0, D(20) * math.sin(f * 0.4))).to_quaternion()
            elif f <= imp:                                                        # vuelo
                t = (f - su) / fps; u = (f - su) / float(imp - su)
                pp = P_r.lerp(P_i, u); pp.z = P_r.z + vz0 * t - 0.5 * g * t * t
                qq = Quaternion(w_vuelo.normalized(), w_vuelo.length * t)
            else:                                                                 # despues del choque: fisica simple
                if not quieto:
                    v.z -= g * dt; p += v * dt
                    if w.length > 1e-6: q = Quaternion(w.normalized(), w.length * dt) @ q
                    # paredes del ring (la valla): rebota con poca energia
                    for eje, a, b in ((0, LIMITES["x0"], LIMITES["x1"]), (1, LIMITES["y0"], LIMITES["y1"])):
                        if p[eje] < a: p[eje] = a; v[eje] = abs(v[eje]) * 0.35
                        if p[eje] > b: p[eje] = b; v[eje] = -abs(v[eje]) * 0.35
                    alto = radio * (1 - asentado) + alto_r * asentado
                    if p.z - alto <= SUELO:
                        p.z = SUELO + alto
                        if v.z < -0.7:                                            # rebota (cada vez menos)
                            v.z = -v.z * F["e_suelo"]; v.x *= 0.62; v.y *= 0.62; w *= 0.45; rebotes += 1
                        else:                                                     # ya en el suelo: se desliza y frena
                            v.z = 0.0; v.x *= 0.80; v.y *= 0.80; w *= 0.70
                        asentado = min(1.0, asentado + 0.30)
                    if asentado > 0: q = q.slerp(q_rest, 0.25 * asentado)          # se acuesta sobre su lado estable
                    if asentado >= 1.0 and Vector((v.x, v.y)).length < 0.03 and abs(v.z) < 1e-3:
                        quieto = True; q = q_rest.copy(); p.z = SUELO + alto_r
                pp = p.copy(); qq = q.copy()
            e = qq.to_euler('XYZ', prev_e) if prev_e is not None else qq.to_euler('XYZ'); prev_e = e
            locs.append((f, tuple(pp))); rots.append((f, tuple(e)))
        vis = [(1, (1.0,)), (ag_, (0.0,))]
        if n == "pollo":
            locs, rots, vis, tramos = huida_pollo(o, locs, rots, imp, P_i, v_out0, alto_r)
            POLLO_T.update(tramos)
        def claves(obj, canales, const=()):
            obj.animation_data_create(); nombre = obj.name + "_lanzado_acc"
            old = bpy.data.actions.get(nombre)
            if old: bpy.data.actions.remove(old)
            act = bpy.data.actions.new(nombre); obj.animation_data.action = act
            for path, cl in canales.items():
                for i_ in range(len(cl[0][1])):
                    fc = act.fcurve_ensure_for_datablock(obj, path, index=i_); fc.keyframe_points.add(len(cl))
                    fc.keyframe_points.foreach_set("co", [x for f_, v_ in cl for x in (f_, v_[i_])])
                    for k in fc.keyframe_points: k.interpolation = 'CONSTANT' if path in const else 'LINEAR'
                    fc.update()
        claves(o, {"location": locs, "rotation_euler": rots, "hide_viewport": vis, "hide_render": vis}, const=("hide_viewport", "hide_render"))
        for x in o.children_recursive:
            claves(x, {"hide_viewport": vis, "hide_render": vis}, const=("hide_viewport", "hide_render"))
        info[n] = dict(impacto=imp, rebotes=rebotes, queda=[round(v_, 2) for v_ in locs[-1][1]])
    # pollo: corre con el ciclo de caminar del usuario (acelerado a su velocidad), aletea al volar / voltereta / salto, mareado
    pa = bpy.data.objects.get("pollo_lanzado_arm")
    if pa and POLLO_T:
        import json
        C = json.load(open(CICLO_POLLO, encoding="utf-8")); N = C["frames_ciclo"]; H = C["huesos"]
        ritmo = POLLO["vel"] / (C["avance_m_por_frame"] * 24.0)                   # ciclos mas rapidos al correr (sin resbalar)
        def pose_ciclo(fase):
            k = fase % N; a = int(math.floor(k)); b = (a + 1) % N; t = k - a
            return {h: tuple(v[a][i_] * (1 - t) + v[b][i_] * t for i_ in range(3)) for h, v in H.items()}
        n, ag_, su, imp, at = LANZA[2]
        dentro = lambda f, t: t[0] <= f <= t[1]
        can = {h: [] for h in H}; fase = float(C["pie_de_apoyo_fase"])
        for f in range(ag_ - 1, F_FIN + 1):
            corre = dentro(f, POLLO_T["corre"]) or dentro(f, POLLO_T["huye"])
            if corre: fase += ritmo
            pose = pose_ciclo(fase if corre else C["pie_de_apoyo_fase"])
            aleteo = 0.0
            if su <= f <= imp or dentro(f, POLLO_T["vuelta"]): aleteo = 1.0
            if dentro(f, POLLO_T["salto"]): aleteo = 1.3
            flap = math.sin(2 * math.pi * f / 3.5)
            mareo = 1.0 if dentro(f, POLLO_T["mareo"]) else 0.0
            for h in H:
                r = list(pose[h])
                if h in ("Shoulder_R_chicken_1", "Shoulder_L_chicken_1"):           # aleteo
                    r[1] += D(60 * flap * aleteo) * (1 if h.endswith("R_chicken_1") else -1)
                if h == "Head_M_chicken_1":                                           # cabecea mareado
                    r[0] += D(18 * mareo * math.sin(f * 0.9)); r[2] += D(28 * mareo * math.sin(f * 0.6))
                if h in ("Hip_R_chicken_1", "Hip_L_chicken_1") and aleteo > 0.9:      # en el aire las patas pedalean (eje Z = adelante/atras)
                    r[2] += D(25 * math.sin(f * 0.8)) * (1 if h.startswith("Hip_R") else -1)
                can[h].append((f, tuple(r)))
        for b in H:
            if b in pa.pose.bones: pa.pose.bones[b].rotation_mode = 'XYZ'
        pa.animation_data_create(); old = bpy.data.actions.get("pollo_lanzado_aletea")
        if old: bpy.data.actions.remove(old)
        act = bpy.data.actions.new("pollo_lanzado_aletea"); pa.animation_data.action = act
        for h, cl in can.items():
            if h not in pa.pose.bones: continue
            for i_ in range(3):
                fc = act.fcurve_ensure_for_datablock(pa, 'pose.bones["%s"].rotation_euler' % h, index=i_); fc.keyframe_points.add(len(cl))
                fc.keyframe_points.foreach_set("co", [x for f_, v_ in cl for x in (f_, v_[i_])]); fc.update()
        info["pollo_huida"] = POLLO_T
        info["pollo_suelo"] = apoyar_pollo()

    # ================= escribir Alfred, Jerry y la rana =================
    def poner(obj, path, datos, desde, n=3):
        a = obj.animation_data.action
        for i in range(n):
            fc = a.fcurve_ensure_for_datablock(obj, path, index=i); kp = fc.keyframe_points
            for j in range(len(kp) - 1, -1, -1):
                if kp[j].co.x >= desde: kp.remove(kp[j], fast=True)
            for f, v in datos: kp.insert(f, v[i], options={'FAST'}).interpolation = 'LINEAR'
            fc.update()

    def euler_cont(lista):
        out, prev = [], None
        for f, e in lista:
            q = Euler(e).to_quaternion(); e2 = q.to_euler('XYZ', prev) if prev is not None else Euler(e); prev = e2; out.append((f, tuple(e2)))
        return out
    poner(ra, "location", out_a["loc"], F0); poner(ra, "rotation_euler", euler_cont(out_a["rot"]), F0)
    poner(aa, 'pose.bones["Hips_alfred"].location', out_a["hips"], F0)
    for h in A_HUESOS: poner(aa, 'pose.bones["%s"].rotation_euler' % h, euler_cont(out_a["h"][h]), F0)
    for h in j_bones: poner(aj, 'pose.bones["%s"].rotation_euler' % h, euler_cont(out_j[h]), 451)
    poner(rj, "location", [(f, tuple(J_loc)) for f in (451, F_FIN)], 451); poner(rj, "rotation_euler", [(f, tuple(J_rot)) for f in (451, F_FIN)], 451)
    poner(rg, "location", out_g["loc"], 601); poner(rg, "rotation_euler", euler_cont(out_g["rot"]), 601)
    for h in G_HUESOS: poner(ag, 'pose.bones["%s"].rotation_euler' % h, euler_cont(out_g["h"][h]), 601)
    sc.frame_set(sc.frame_current)
    return {"frame_end": sc.frame_end, "lanzamientos": info, "valla": info_valla}
