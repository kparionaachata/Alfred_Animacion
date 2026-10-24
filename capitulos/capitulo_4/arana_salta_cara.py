"""La arana (estructura_lista/spider_1.blend, coleccion `spider`) salta a la cara de Alfred despues de que el voltea (alfred_mira_arana.py,
f800-810). Aparece en el suelo delante de Alfred cuando Jerry grita "Una arana!", se agacha, salta, su pecho (lado ventral) queda paralelo
al rostro de Alfred y las patas se enrollan en la cabeza (delanteras por encima, del medio por los lados, traseras bajo el menton).
Las patas se resuelven con IK hacia puntos de la superficie de la cabeza y se guardan como rotaciones (sin constraints).
Tras aterrizar la raiz `spider_1` sigue al hueso `face_alfred` (horneado por frame).
Uso (Blender):  exec(open(r"...\\arana_salta_cara.py", encoding="utf8").read()); construir()      (repetible)
"""
import bpy, math
from mathutils import Vector, Matrix, Quaternion, Euler

ARCHIVO = r"C:\Users\user\Desktop\Alfred_Animacion\estructura_lista\spider_1.blend"
ESCALA = 1.0                      # tamano normal (2.2 m de punta a punta de las patas)
# accion y reaccion: el impacto empuja la cabeza y el torso de Alfred hacia atras (X negativa en Spine/Spine2/Neck), los brazos
# reaccionan con retraso; la arana sigue avanzando por inercia (se aplasta y cabecea contra la cara) y se asienta
REACCION = {"Neck_alfred": (0, -0.38), "Spine2_alfred": (0, -0.22), "Spine_alfred": (0, -0.16)}      # hueso: (eje, radianes en el pico)
REACCION_BRAZOS = {"RightUpArm_alfred": (1, 0.45), "LeftUpArm_alfred": (1, -0.45)}                  # los brazos van hacia la arana
RESIDUO = 0.25                    # se queda algo echado hacia atras sosteniendo el peso
APLASTA = 0.35                    # grosor (pecho-espalda) que le queda a la arana tras el choque contra la estalagmita
F_APARECE, F_AGACHA, F_SALTA, F_CARA = 522, 528, 534, 546
F_ABRAZA = (544, 548, 551, 554)   # patas: inicio, sobrepaso, rebote, quietas
DIST_SUELO = 2.0                  # metros delante de la cara de Alfred
LOCAL_PECHO = Vector((0.0, 0.18, 0.20))   # punto del pecho (espacio de spider_1) que se apoya en la cara
SEP_CARA = 0.02
HUESO_CARA, ARM_ALFRED = "face_alfred", "Armature"
PATAS = [(lado, fila) for lado in ("Left", "Right") for fila in ("Front", "Middle", "Back")]


def _asegurar_arana():
    sc = bpy.context.scene
    if not bpy.data.objects.get("spider_1"):
        with bpy.data.libraries.load(ARCHIVO, link=False) as (src, dst): dst.collections = ["spider"]
        sc.collection.children.link(dst.collections[0])
    col = bpy.data.collections["spider"]; raiz = bpy.data.objects["spider_1"]
    if raiz.name not in col.objects: col.objects.link(raiz)
    rec = bpy.data.collections.get("luz_entrada_receptores")             # light linking de la cueva
    if rec:
        for o in list(col.all_objects):
            if o.name not in rec.objects: rec.objects.link(o)
    return raiz, bpy.data.objects["spider.arma_spider_1"], col


def _cabeza(f):
    """centro, ejes (F adelante, U arriba, X = izquierda de Alfred = +X de la arana) y medidas de la cabeza de Alfred en el frame f."""
    sc = bpy.context.scene; sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
    arm = bpy.data.objects[ARM_ALFRED]; gi_name = HUESO_CARA
    o = bpy.data.objects["Mesh_0_alfred"]; gi = o.vertex_groups[gi_name].index; oe = o.evaluated_get(dg)
    pts = [oe.matrix_world @ oe.data.vertices[v.index].co for v in o.data.vertices if any(g.group == gi and g.weight > 0.5 for g in v.groups)]
    C = sum(pts, Vector()) / len(pts)
    ojos = []
    for n in ("ojo_izquierdo_alfred", "ojo_derecho_alfred"):
        e = bpy.data.objects[n].evaluated_get(dg); ojos += [e.matrix_world @ v.co for v in e.data.vertices]
    E = sum(ojos, Vector()) / len(ojos)
    U = (arm.matrix_world @ arm.pose.bones[HUESO_CARA].tail - arm.matrix_world @ arm.pose.bones[HUESO_CARA].head).normalized()
    Fw = (E - C); Fw -= U * Fw.dot(U); Fw.normalize()
    X = U.cross(Fw).normalized()
    med = lambda ax: (max((p - C).dot(ax) for p in pts), min((p - C).dot(ax) for p in pts))
    return C, Fw, U, X, med(Fw)[0], med(X)[0], med(U)[0], -med(U)[1]


def _matriz_raiz(P, Xs, Ys, Zs, s=ESCALA):
    R = Matrix((Xs, Ys, Zs)).transposed()
    M = Matrix.Translation(P) @ R.to_4x4() @ Matrix.Diagonal((s, s, s, 1.0))
    return M @ Matrix.Translation(-LOCAL_PECHO)


def _pose_patas(raiz, sa, cab, M_cara):
    """IK temporal de cada pata (Upper+Lower) hacia la superficie de la cabeza; devuelve {hueso: cuaternion basis}."""
    C, Fw, U, X, fr, lado, arriba, abajo = cab
    sc = bpy.context.scene; raiz.matrix_world = M_cara; bpy.context.view_layer.update()
    tmp, out = [], {}
    cara_atras = C + Fw * (fr - 0.20)                                # 20 cm detras del plano de la cara
    for ld, fila in PATAS:
        sx = 1.0 if ld == "Left" else -1.0
        if fila == "Front": t = cara_atras + U * (arriba + 0.02) + X * sx * 0.12
        elif fila == "Back": t = cara_atras - U * (abajo + 0.02) + X * sx * 0.12
        else: t = cara_atras + X * sx * (lado + 0.02)
        pole = t + X * sx * 0.4 + Fw * 0.3
        e1 = bpy.data.objects.new("tmp_ik_t", None); e2 = bpy.data.objects.new("tmp_ik_p", None)
        sc.collection.objects.link(e1); sc.collection.objects.link(e2); e1.location = t; e2.location = pole; tmp += [e1, e2]
        c = sa.pose.bones[f"Leg:{ld}:{fila}:Lower_spider_1"].constraints.new('IK')
        c.target = e1; c.pole_target = e2; c.chain_count = 2; c.pole_angle = 0.0
    bpy.context.view_layer.update()
    M = {pb.name: pb.matrix.copy() for pb in sa.pose.bones}
    for ld, fila in PATAS:
        for parte in ("Upper", "Lower"):
            b = sa.data.bones[f"Leg:{ld}:{fila}:{parte}_spider_1"]; par = b.parent
            P = M[par.name] @ par.matrix_local.inverted() @ b.matrix_local
            out[b.name] = (P.inverted() @ M[b.name]).to_quaternion()
        pb = sa.pose.bones[f"Leg:{ld}:{fila}:Lower_spider_1"]
        for c in list(pb.constraints): pb.constraints.remove(c)
    for e in tmp: bpy.data.objects.remove(e)
    bpy.context.view_layer.update()
    return out


def _limpiar(raiz, sa, col):
    for ob in [raiz, sa] + list(col.all_objects):
        if ob.animation_data: ob.animation_data_clear()
    for pb in sa.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)


def construir():
    sc = bpy.context.scene; f_act = sc.frame_current
    raiz, sa, col = _asegurar_arana(); _limpiar(raiz, sa, col)
    raiz.rotation_mode = 'QUATERNION'
    impacto_alfred()                                                    # antes de hornear la arana: ella sigue a la cabeza ya empujada
    cab = _cabeza(F_CARA); C, Fw, U, X, fr, lado, arriba, abajo = cab
    # --- en la cara: pecho paralelo al rostro (Z de la arana = adelante de Alfred, Y = arriba)
    P_cara = C + Fw * (fr + SEP_CARA)
    M_cara = _matriz_raiz(P_cara, X, U, Fw)
    patas = _pose_patas(raiz, sa, cab, M_cara)
    # --- en el suelo, mirando a Alfred
    dg = bpy.context.evaluated_depsgraph_get(); p = C + Fw * DIST_SUELO
    hit = sc.ray_cast(dg, p + Vector((0, 0, 0.5)), Vector((0, 0, -1)), distance=20)
    z_suelo = hit[1].z if hit[0] else C.z - 2.5
    Ys = Vector((-Fw.x, -Fw.y, 0)).normalized(); Zs = Vector((0, 0, 1)); Xs = Ys.cross(Zs)
    M_suelo = Matrix.Translation(Vector((p.x, p.y, z_suelo))) @ Matrix((Xs, Ys, Zs)).transposed().to_4x4() @ Matrix.Diagonal((ESCALA,) * 3 + (1.0,))
    # --- raiz por frame
    arm = bpy.data.objects[ARM_ALFRED]
    sc.frame_set(F_CARA); Mf0 = arm.matrix_world @ arm.pose.bones[HUESO_CARA].matrix; rel = Mf0.inverted() @ M_cara
    fin = sc.frame_end; q0 = M_suelo.to_quaternion(); q1 = M_cara.to_quaternion()
    if q0.dot(q1) < 0: q1.negate()
    t0 = M_suelo.translation.copy(); t1 = M_cara.translation.copy()
    claves = {}
    f_choque = int(bpy.data.objects["alfred"].get("f_choque", 0))            # alfred_choca_estalagmita.py
    f_suelta = f_choque + SUELTA if f_choque else 0
    for f in range(F_APARECE, fin + 1):
        if f_suelta and f >= f_suelta: break                           # desde aqui cae sola (abajo)
        if f < F_AGACHA: M = M_suelo
        elif f < F_SALTA:                                               # se agacha
            k = math.sin(math.pi * (f - F_AGACHA) / (F_SALTA - F_AGACHA)) * 0.5 + (f - F_AGACHA) / (F_SALTA - F_AGACHA) * 0.5
            M = Matrix.Translation((0, 0, -0.05 * ESCALA * k)) @ M_suelo
        elif f < F_CARA:                                                # salto parabolico, gira hasta quedar vertical
            u = (f - F_SALTA) / (F_CARA - F_SALTA)
            pos = t0.lerp(t1, u) + Vector((0, 0, 0.6 * 4 * u * (1 - u)))
            q = q0.slerp(q1, min(1.0, u * 1.15))
            M = Matrix.Translation(pos) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((ESCALA,) * 3 + (1.0,))
        else:
            sc.frame_set(f); M = (arm.matrix_world @ arm.pose.bones[HUESO_CARA].matrix) @ rel
            t = f - F_CARA
            k = 1.0 - 0.15 * math.sin(math.pi * t / 4) if t < 4 else 1.0           # aplastamiento contra la cara
            ang = 0.22 * _golpe(t, residuo=0.0)                                     # inercia: el cuerpo sigue hacia la cara y cabecea
            sxy = 1.0
            if f_choque and f_choque - 1 <= f < f_choque + 4:                      # aplastamiento contra la estalagmita: solo un efecto, recupera su volumen
                u = math.sin(math.pi * (f - f_choque + 1) / 5.0)
                k *= 1.0 - (1.0 - APLASTA) * u; sxy = 1.0 + 0.18 * u
            M = M @ Matrix.Translation(LOCAL_PECHO) @ Matrix.Rotation(ang, 4, 'X') @ Matrix.Diagonal((sxy, sxy, k, 1.0)) @ Matrix.Translation(-LOCAL_PECHO)
        claves[f] = M.copy()
    if f_suelta:                                                        # se suelta de la cara, gira 180 y cae boca arriba con las patas contraidas
        claves.update(_cae_muerta(raiz, sa, claves[f_suelta - 1], f_suelta, fin))
    for f, M in claves.items():
        loc, rot, esc = M.decompose()
        raiz.location = loc; raiz.rotation_quaternion = rot; raiz.scale = esc
        for dp in ("location", "rotation_quaternion", "scale"): raiz.keyframe_insert(dp, frame=f)
    # --- patas: reposo -> abrazo con sobrepaso
    for b, q in patas.items():
        pb = sa.pose.bones[b]
        for f, k in ((F_ABRAZA[0], 0.0), (F_ABRAZA[1], 1.12), (F_ABRAZA[2], 0.96), (F_ABRAZA[3], 1.0)):
            pb.rotation_quaternion = _sobre(q, k)
            pb.keyframe_insert("rotation_quaternion", frame=f)
    # --- patas al morir: del abrazo a contraidas (mientras cae) y dos espasmos al quedar boca arriba
    if f_suelta and _ST.get("muerta"):
        f_lleg = _ST["f_llega"]
        for b, qm in _ST["muerta"].items():
            pb = sa.pose.bones[b]; qa = patas.get(b, Quaternion())
            for f, q in ((f_suelta, qa), (f_suelta + 5, qa.slerp(qm, 0.6)), (f_lleg, qm),
                         (f_lleg + 4, _sobre(qm, 0.8)), (f_lleg + 7, qm), (f_lleg + 11, _sobre(qm, 0.88)), (f_lleg + 15, qm)):
                pb.rotation_quaternion = q; pb.keyframe_insert("rotation_quaternion", frame=f)
    # --- visible desde F_APARECE
    for ob in [raiz] + list(col.all_objects):
        if ob.name == "spider.arma.drivers_spider_1": continue
        for f, v in ((1, True), (F_APARECE, False)):
            ob.hide_viewport = v; ob.hide_render = v
            ob.keyframe_insert("hide_viewport", frame=f); ob.keyframe_insert("hide_render", frame=f)
    for ob in [raiz, sa] + list(col.all_objects):
        ad = ob.animation_data
        if ad and ad.action:
            for lay in ad.action.layers:
                for st in lay.strips:
                    for cb in st.channelbags:
                        for fc in cb.fcurves:
                            for kp in fc.keyframe_points:
                                kp.interpolation = 'CONSTANT' if fc.data_path.startswith("hide") else ('LINEAR' if ob == raiz else 'BEZIER')
    sc.frame_set(f_act)
    return {"suelo": [round(v, 2) for v in M_suelo.translation], "cara": [round(v, 2) for v in M_cara.translation], "frames": (F_APARECE, F_AGACHA, F_SALTA, F_CARA)}


MUERTA_UPPER, MUERTA_LOWER = (34.387, 1.772, 6.4305), (0.0, 0.0, 67.0)   # grados (pose del usuario para la arana muerta)
SUELTA = 2                         # frames despues del choque en que se despega de la cara (Alfred rebota)
CAE_F = 12                         # frames de caida hasta el suelo
ESTALAGMITA = Vector((-48.47, -14.5)); R_ESTALAGMITA = 0.32
_ST = {}


def _cae_muerta(raiz, sa, M0, f0, fin):
    """matrices de la raiz: cae desde M0 (en la cara) al suelo entre la estalagmita y los pies de Alfred, girando 180 grados hasta quedar
    boca arriba (lado ventral hacia el cielo) y de costado respecto del choque; guarda en _ST la pose de patas contraidas."""
    sc = bpy.context.scene
    q0 = M0.to_quaternion()
    alf = bpy.data.objects[ARM_ALFRED]; sc.frame_set(f0)
    h = ESTALAGMITA - (alf.matrix_world @ alf.pose.bones["Hips_alfred"].head).to_2d(); h = Vector((h.x, h.y, 0)).normalized()
    p0 = M0.translation.copy() - h * 0.3                                        # recupera su volumen hacia Alfred (la estalagmita no cede)
    up = Vector((0, 0, 1))
    Ys = h.cross(up).normalized(); Zs = -up; Xs = Ys.cross(Zs)                    # boca arriba, de costado
    # altura: el lomo (punto mas alto del cuerpo en espacio de spider_1) apoyado en el suelo
    body = bpy.data.objects["spider.body_spider_1"]; gi = {g.index for g in body.vertex_groups if g.name.startswith(("Body_", "Head_", "Back_"))}
    Mb = raiz.matrix_world.inverted() @ body.matrix_world
    zmax = max((Mb @ v.co).z for v in body.data.vertices if any(g.group in gi and g.weight > 0.5 for g in v.groups))
    centro = ESTALAGMITA.to_3d() - h * (R_ESTALAGMITA + 0.70)                     # entre la estalagmita y los pies de Alfred
    dg = bpy.context.evaluated_depsgraph_get()
    hit = sc.ray_cast(dg, Vector((centro.x, centro.y, -8.5)), Vector((0, 0, -1)), distance=3)
    z_suelo = hit[1].z if hit[0] else -9.0
    R = Matrix((Xs, Ys, Zs)).transposed()
    Mf = Matrix.Translation(Vector((centro.x, centro.y, z_suelo))) @ R.to_4x4() @ Matrix.Diagonal((ESCALA,) * 3 + (1.0,)) \
        @ Matrix.Translation(-Vector((LOCAL_PECHO.x, LOCAL_PECHO.y, zmax)))
    q1 = Mf.to_quaternion()
    if q0.dot(q1) < 0: q1.negate()
    p1 = Mf.translation.copy(); out = {}
    for f in range(f0, fin + 1):
        u = min(1.0, (f - f0) / CAE_F)
        if u < 1.0:
            pos = p0.lerp(p1, u) + Vector((0, 0, 0.35 * 4 * u * (1 - u))) - h * (0.9 * math.sin(math.pi * min(1.0, u * 1.4)))   # se despega de la estalagmita hacia Alfred y cae
            q = q0.slerp(q1, u * u * (3 - 2 * u))
        else:
            t = f - f0 - CAE_F; pos = p1 + Vector((0, 0, 0.08 * max(0.0, math.sin(math.pi * t / 4)) if t < 4 else 0.0)); q = q1
        out[f] = Matrix.Translation(pos) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((ESCALA,) * 3 + (1.0,))
    # patas contraidas hacia arriba: pose del usuario (Leg:Left:Back: Upper 34.4, 1.8, 6.4 / Lower Z 67 grados), espejada en las derechas
    raiz.matrix_world = Mf; bpy.context.view_layer.update(); res = {}
    for ld, fila in PATAS:
        sy = 1.0 if ld == "Left" else -1.0
        for parte, e in (("Upper", MUERTA_UPPER), ("Lower", MUERTA_LOWER)):
            res[f"Leg:{ld}:{fila}:{parte}_spider_1"] = Euler((math.radians(e[0]), math.radians(e[1]) * sy, math.radians(e[2]) * sy), 'XYZ').to_quaternion()
    _ST["muerta"] = res; _ST["f_llega"] = f0 + CAE_F
    return out


def _golpe(t, retraso=0.0, residuo=RESIDUO):
    """respuesta al impacto (t = frames desde el choque): sube en 2.5 f, rebota amortiguada y queda en `residuo`."""
    t -= retraso
    if t <= 0: return 0.0
    if t < 2.5: return math.sin(t / 2.5 * math.pi / 2)
    u = t - 2.5
    return residuo + (1.0 - residuo) * math.exp(-u / 5.0) * math.cos(2 * math.pi * u / 9.0)


def impacto_alfred():
    """capa ADD `Alfred_impacto_arana` en la armature de Alfred: reaccion al golpe (cabeza/torso atras, brazos hacia la arana)."""
    arm = bpy.data.objects[ARM_ALFRED]; ad = arm.animation_data; nombre = "Alfred_impacto_arana"
    for t in list(ad.nla_tracks):
        if t.name == nombre: ad.nla_tracks.remove(t)
    a = bpy.data.actions.get(nombre)
    if a: bpy.data.actions.remove(a)
    act = bpy.data.actions.new(nombre); slot = act.slots.new(arm.id_type, arm.name)
    cb = act.layers.new("Layer").strips.new(type='KEYFRAME').channelbags.new(slot)
    fin = bpy.context.scene.frame_end
    for tabla, retraso in ((REACCION, 0.0), (REACCION_BRAZOS, 2.0)):
        for b, (eje, amp) in tabla.items():
            fc = cb.fcurves.new(f'pose.bones["{b}"].rotation_euler', index=eje)
            fs = list(range(F_CARA, min(fin, F_CARA + 60) + 1)) + ([fin] if fin > F_CARA + 60 else [])
            fc.keyframe_points.add(len(fs))
            res = RESIDUO if tabla is REACCION else 0.0                            # los brazos vuelven del todo (despues van en V al correr)
            for kp, f in zip(fc.keyframe_points, fs): kp.co = (f, amp * _golpe(f - F_CARA, retraso, res)); kp.interpolation = 'BEZIER'
            fc.update()
    tr = ad.nla_tracks.new(); tr.name = nombre
    st = tr.strips.new(nombre, F_CARA, act); st.blend_type = 'ADD'; st.extrapolation = 'HOLD_FORWARD'
    try: st.action_slot = slot
    except Exception: pass


def _sobre(q, k):
    """rotacion de reposo->q escalada por k (k>1 = sobrepaso) via eje-angulo."""
    ax, ang = q.to_axis_angle()
    return Quaternion(ax, ang * k)
