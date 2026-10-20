# -*- coding: utf-8 -*-
"""alfred_se_levanta_en_la_mañana_2: Alfred (saltando hacia el conejo) y Jerry (saltando desde el noroeste) chocan las cabezas en F_HIT.
Accion/reaccion: cada uno sale despedido hacia atras de su direccion de salto, gira y cae boca arriba; luego se soban la cabeza.
El sombrero de Jerry sale volando y cae al suelo. El conejo suelta la zanahoria y huye saltando.
Se ejecuta dentro de Blender (exec) en un timer; deja el estado en driver_namespace['choque']."""
import bpy, json, math, os, random
from mathutils import Vector, Matrix, Quaternion, Euler

F_HIT = 780
sc = bpy.context.scene; vl = bpy.context.view_layer
AA = bpy.data.objects["Armature"]; EA = bpy.data.objects["alfred"]
J = bpy.data.objects["jerry"]; JR = bpy.data.objects["Dog_001_rig"]
RE = bpy.data.objects["rabbit_1"]; RA = bpy.data.objects["rabbit.arma_rabbit_1"]; ZA = bpy.data.objects["Zanahoria_Conejo"]
S = "C:\\Users\\user\\Desktop\\Alfred_Animacion\\sonidos\\sounds\\"
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))


def bags(ob):
    ad = ob.animation_data
    if not (ad and ad.action): return []
    return [cb for l in ad.action.layers for s in l.strips for cb in s.channelbags]


def borrar_desde(ob, f0, excepto=()):
    for cb in bags(ob):
        for fc in cb.fcurves:
            if any(e in fc.data_path for e in excepto): continue
            for k in [k for k in fc.keyframe_points if k.co.x >= f0][::-1]: fc.keyframe_points.remove(k)
            fc.update()


def zmin(obs):
    vl.update(); dg = bpy.context.evaluated_depsgraph_get(); z = 1e9
    for o in obs:
        ev = o.evaluated_get(dg); m = ev.to_mesh()
        if len(m.vertices): z = min(z, min((ev.matrix_world @ v.co).z for v in m.vertices))
        ev.to_mesh_clear()
    return z


MESH_A = [o for o in bpy.data.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == AA for m in o.modifiers)]
MESH_J = [o for o in JR.children if o.type == 'MESH']


# ====================================================================== ALFRED
def alfred():
    sc.frame_set(F_HIT); P_hit = Vector(EA.location); rx_hit = math.degrees(EA.rotation_euler.x); rz = math.degrees(EA.rotation_euler.z)
    face = AA.matrix_world @ AA.pose.bones["face_alfred"].head
    borrar_desde(EA, F_HIT + 1); borrar_desde(AA, F_HIT + 1, excepto=("constraints",))
    back = Vector((0, -1, 0)); L1 = F_HIT + 14
    # pose tumbado boca arriba (piernas estiradas, brazo izquierdo al lado)
    tumb = {"Hips_alfred": (0, 0, 0), "Spine_alfred": (0, 0, 0), "Spine1_alfred": (0, 0, 0), "Spine2_alfred": (0, 0, 0), "Neck_alfred": (8, 0, 0), "face_alfred": (0, 0, 0),
            "RightUpLeg_alfred": (-6, 0, -4), "LeftUpLeg_alfred": (-6, 0, 4), "Rightknee_alfred": (-14, 0, 0), "Leftknee_alfred": (-10, 0, 0),
            "LeftUpArm_alfred": (70, 0, 25), "Leftelbow_alfred": (20, 0, 0)}
    # reaccion: retroceso con rebote; rx gira de prono a boca arriba
    rx_end = 92.0
    for f in range(F_HIT + 1, L1 + 1):
        t = (f - F_HIT) / (L1 - F_HIT); tt = ss(t)
        pos = P_hit + back * 1.25 * (1 - (1 - t) ** 2)
        z = P_hit.z + 0.45 * math.sin(math.pi * min(1, t * 1.15)) * (1 - t)
        EA.location = (pos.x, pos.y, z); EA.rotation_euler = (math.radians(rx_hit + (rx_end - rx_hit) * tt), 0, math.radians(rz))
        EA.keyframe_insert("location", frame=f); EA.keyframe_insert("rotation_euler", frame=f)
    # pose de los huesos mezclada hacia tumbado
    sc.frame_set(F_HIT); b0 = {b: Euler(tuple(AA.pose.bones[b].rotation_euler)) for b in tumb}
    for f in range(F_HIT + 1, L1 + 1):
        w = ss((f - F_HIT) / (L1 - F_HIT))
        for b, v in tumb.items():
            e = Euler(tuple(math.radians(x) for x in v)); pb = AA.pose.bones[b]
            pb.rotation_euler = Euler([b0[b][i] + (e[i] - b0[b][i]) * w for i in range(3)]); pb.keyframe_insert("rotation_euler", frame=f)
    # golpe del choque: cabeza y cuello sacudidos
    for f, nx in ((F_HIT + 1, 25), (F_HIT + 3, -12), (F_HIT + 6, 6), (F_HIT + 10, 0)):
        pb = AA.pose.bones["Neck_alfred"]; e = Euler(tuple(pb.rotation_euler)); sc.frame_set(f); e = Euler(tuple(pb.rotation_euler)); e.x += math.radians(nx); pb.rotation_euler = e; pb.keyframe_insert("rotation_euler", frame=f)
    # apoyo en el suelo: ajustar z para que la espalda toque el suelo (z=9), con rebote
    sc.frame_set(L1); dz = 9.0 - zmin(MESH_A)
    zf = EA.location.z + dz
    for f, extra in ((L1, 0.0), (L1 + 3, 0.05), (L1 + 6, 0.0)):
        EA.location = (EA.location.x, EA.location.y, zf + extra); EA.keyframe_insert("location", frame=f)
        EA.rotation_euler = (math.radians(rx_end), 0, math.radians(rz)); EA.keyframe_insert("rotation_euler", frame=f)
    END = sc.frame_end
    EA.keyframe_insert("location", frame=END); EA.keyframe_insert("rotation_euler", frame=END)
    for b, v in tumb.items():
        pb = AA.pose.bones[b]; pb.rotation_euler = Euler(tuple(math.radians(x) for x in v)); pb.keyframe_insert("rotation_euler", frame=END)
    return dict(cae=L1, z=round(zf, 3), cara=[round(v, 2) for v in face])


def alfred_soba(f0, f1):
    TIP = Vector((-0.0148, 0.3668, 0.0172))
    UA, EL, F = AA.pose.bones["RightUpArm_alfred"], AA.pose.bones["Rightelbow_alfred"], AA.pose.bones["face_alfred"]
    def hand(): vl.update(); return AA.matrix_world @ EL.matrix @ TIP
    def ik(t):
        step = 0.25
        for _ in range(70):
            best = (hand() - t).length
            if best < 0.01: break
            imp = False
            for pb, i in ((UA, 0), (UA, 1), (UA, 2), (EL, 0), (EL, 2)):
                for s in (step, -step):
                    pb.rotation_euler[i] += s; d = (hand() - t).length
                    if d < best - 1e-5: best = d; imp = True; break
                    pb.rotation_euler[i] -= s
            if not imp: step *= 0.5
            if step < 0.002: break
    for f in range(f0, f1 + 1, 2):
        sc.frame_set(f); M = AA.matrix_world @ F.matrix
        up = M.col[1].to_3d().normalized(); fr = M.col[2].to_3d().normalized(); sd = M.col[0].to_3d().normalized()
        a = (f - f0) * 2 * math.pi / 12
        ik(M.translation.to_3d() + up * 0.30 + fr * 0.14 + sd * 0.05 * math.sin(a) + up * 0.03 * math.cos(a))
        UA.keyframe_insert("rotation_euler", frame=f); EL.keyframe_insert("rotation_euler", frame=f)


# ====================================================================== JERRY
def jerry(contact, d):
    """contact: punto del choque; d: direccion de su salto (xy, unitario)"""
    J.animation_data_clear(); JR.animation_data_clear()
    J.rotation_mode = 'QUATERNION'
    heading = math.degrees(math.atan2(d.y, d.x)); rz = math.radians(heading - 90.0)
    q_std = Euler((0, 0, rz)).to_quaternion()
    J.rotation_quaternion = q_std; J.location = (0, 0, 9.0); vl.update()
    sk = JR.matrix_world @ JR.pose.bones["scull"].head; ofs = sk - J.location                     # cabeza respecto a la raiz, de pie
    head_hit = contact - Vector((d.x, d.y, 0)) * 0.14
    root_hit = head_hit - ofs
    T0 = F_HIT - 30; TJ = F_HIT - 9                                                              # carrera 750-771, salto 771-780
    p_take = Vector((root_hit.x, root_hit.y, 9.0)) - Vector((d.x, d.y, 0)) * 2.0
    p_start = p_take - Vector((d.x, d.y, 0)) * 5.5
    # trote (poses guardadas)
    Dp = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\jerry\refinar\poses\jerry_trota_al_rincon_f10_33"
    ciclo = []
    for fr in range(15, 22):
        p = json.load(open(os.path.join(Dp, f"jerry_trota_al_rincon_f{fr}.json"), encoding="utf-8"))["poses"][0]["bones"]
        ciclo.append({b: [v["local_space"]["rotation_euler_deg"][a] for a in "xyz"] for b, v in p.items()})
    var = [b for b in ciclo[0] if b in JR.pose.bones and max(abs(c[b][i] - ciclo[0][b][i]) for c in ciclo for i in range(3)) > 0.5]
    media = {b: [sum(c[b][i] for c in ciclo) / 7.0 for i in range(3)] for b in var}
    for b in JR.pose.bones: b.rotation_mode = 'XYZ'
    def pose_trote(f, ph, amp):
        u = (ph % 1.0) * 7.0; i0 = int(u) % 7; i1 = (i0 + 1) % 7; k = u - int(u)
        for b in var:
            v = [ciclo[i0][b][c] + (ciclo[i1][b][c] - ciclo[i0][b][c]) * k for c in range(3)]
            JR.pose.bones[b].rotation_euler = Euler([math.radians((v[c] - media[b][c]) * amp) for c in range(3)]); JR.pose.bones[b].keyframe_insert("rotation_euler", frame=f)
    # oculto hasta T0
    for o in [J, JR] + MESH_J:
        o.hide_render = o.hide_viewport = True; o.keyframe_insert("hide_render", frame=T0 - 1); o.keyframe_insert("hide_viewport", frame=T0 - 1)
        o.hide_render = o.hide_viewport = False; o.keyframe_insert("hide_render", frame=T0); o.keyframe_insert("hide_viewport", frame=T0)
    for f in range(T0, TJ + 1):
        t = (f - T0) / (TJ - T0); p = p_start.lerp(p_take, t)
        J.location = (p.x, p.y, 9.0 + 0.05 * abs(math.sin(math.pi * 2.5 * t * 4))); J.rotation_quaternion = q_std
        J.keyframe_insert("location", frame=f); J.keyframe_insert("rotation_quaternion", frame=f)
        pose_trote(f, t * 4.0, 1.6)
    # salto: arco hasta el choque, cuerpo estirado (cabeza adelante)
    pitch_ax = (Matrix.Rotation(rz, 3, 'Z') @ Vector((1, 0, 0)))                                   # eje lateral (cabecea con el)
    for f in range(TJ + 1, F_HIT + 1):
        t = (f - TJ) / (F_HIT - TJ); p = p_take.lerp(Vector((root_hit.x, root_hit.y, 9.0)), t)
        z = 9.0 + (root_hit.z - 9.0) * t + 0.55 * 4 * t * (1 - t)
        J.location = (p.x, p.y, z); J.rotation_quaternion = Quaternion(pitch_ax, math.radians(-12 * math.sin(math.pi * t))) @ q_std
        J.keyframe_insert("location", frame=f); J.keyframe_insert("rotation_quaternion", frame=f)
        for b in var:
            JR.pose.bones[b].rotation_euler = (0, 0, 0); JR.pose.bones[b].keyframe_insert("rotation_euler", frame=f)
    # reaccion: retroceso, giro sobre su eje (boca arriba), cae
    L1 = F_HIT + 15; fwd_ax = Matrix.Rotation(rz, 3, 'Z') @ Vector((0, 1, 0))
    for f in range(F_HIT + 1, L1 + 1):
        t = (f - F_HIT) / (L1 - F_HIT); tt = ss(t)
        p = Vector((root_hit.x, root_hit.y, 0)) - Vector((d.x, d.y, 0)) * 1.4 * (1 - (1 - t) ** 2)
        z = root_hit.z + 0.35 * math.sin(math.pi * min(1, t * 1.1)) * (1 - t) + (9.0 - root_hit.z) * tt
        J.location = (p.x, p.y, z); J.rotation_quaternion = Quaternion(fwd_ax, math.radians(180 * tt)) @ Quaternion(pitch_ax, math.radians(25 * math.sin(math.pi * t))) @ q_std
        J.keyframe_insert("location", frame=f); J.keyframe_insert("rotation_quaternion", frame=f)
    # z en el suelo (boca arriba)
    sc.frame_set(L1); dz = 9.0 - zmin(MESH_J); zf = J.location.z + dz
    q_end = Quaternion(fwd_ax, math.radians(180)) @ q_std
    for f, extra in ((L1, 0.0), (L1 + 3, 0.06), (L1 + 6, 0.0), (sc.frame_end, 0.0)):
        J.location = (J.location.x, J.location.y, zf + extra); J.rotation_quaternion = q_end
        J.keyframe_insert("location", frame=f); J.keyframe_insert("rotation_quaternion", frame=f)
    # boca arriba: patas encogidas y pata delantera derecha se soba la cabeza
    pierna = {"thigh.R": (25, 0, 0), "thigh.L": (25, 0, 0), "shin.R": (-35, 0, 0), "shin.L": (-35, 0, 0),
              "front_thigh.L": (35, 0, 0), "front_shin.L": (-30, 0, 0), "tail_1": (20, 0, 0)}
    for b, v in pierna.items():
        if b not in JR.pose.bones: continue
        pb = JR.pose.bones[b]
        pb.rotation_euler = (0, 0, 0); pb.keyframe_insert("rotation_euler", frame=F_HIT)
        pb.rotation_euler = Euler([math.radians(x) for x in v]); pb.keyframe_insert("rotation_euler", frame=L1); pb.keyframe_insert("rotation_euler", frame=sc.frame_end)
    for f in range(F_HIT, sc.frame_end + 1, 2):
        rub = ss((f - L1 - 4) / 6); a = (f - L1) * 2 * math.pi / 12
        for b, base, amp in (("front_shoulder.R", 0, 0), ("front_thigh.R", 95, 12), ("front_shin.R", -70, 15)):
            if b not in JR.pose.bones: continue
            pb = JR.pose.bones[b]; pb.rotation_euler = (math.radians((base + amp * math.sin(a)) * rub), 0, 0); pb.keyframe_insert("rotation_euler", frame=f)
        pb = JR.pose.bones["scull_1"]; pb.rotation_euler = (math.radians(-20 * ss((f - F_HIT) / 3) * (1 - ss((f - F_HIT - 3) / 8))), 0, math.radians(6 * math.sin(a) * rub)); pb.keyframe_insert("rotation_euler", frame=f)
    return dict(head_hit=[round(v, 2) for v in head_hit], cae=L1, z=round(zf, 3), inicio=[round(v, 2) for v in p_start])


def sombrero(d):
    pb = JR.pose.bones["sombrero"]; pb.rotation_mode = 'QUATERNION'
    sc.frame_set(F_HIT); M0 = (JR.matrix_world @ pb.matrix).copy(); loc0, q0, s0 = M0.decompose()
    land = loc0 - Vector((d.x, d.y, 0)) * 1.9 + Vector((0.5 * d.y, -0.5 * d.x, 0)); land.z = 9.03
    q_rest = (Euler((0, 0, math.atan2(d.y, d.x) - math.pi / 2)).to_quaternion()) @ Euler((0, 0, 0)).to_quaternion()
    sc.frame_set(F_HIT - 2); qs = (JR.matrix_world @ pb.matrix).to_quaternion()       # orientacion de pie sobre la cabeza
    spin = Vector((d.y, -d.x, 0)).normalized(); L = F_HIT + 18
    for f in range(F_HIT + 1, L + 4):
        t = min(1.0, (f - F_HIT) / (L - F_HIT))
        p = loc0.lerp(land, t) + Vector((0, 0, 0.9 * 4 * t * (1 - t) * (1 - 0.3 * t)))
        if f > L: p = land + Vector((0, 0, 0.04 * math.sin(math.pi * (f - L) / 3)))
        q = Quaternion(spin, math.radians(-540 * ss(t))) @ q0
        if f >= L: q = q0
        Mw = Matrix.LocRotScale(p, q, s0); sc.frame_set(f)
        pb.matrix = JR.matrix_world.inverted() @ Mw; vl.update()
        pb.keyframe_insert("location", frame=f); pb.keyframe_insert("rotation_quaternion", frame=f)
    # se queda en el suelo: mantener el mundo fijo aunque Jerry se mueva
    for f in range(L + 4, sc.frame_end + 1, 2):
        sc.frame_set(f); pb.matrix = JR.matrix_world.inverted() @ Matrix.LocRotScale(land, q0, s0); vl.update()
        pb.keyframe_insert("location", frame=f); pb.keyframe_insert("rotation_quaternion", frame=f)
    pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0)
    pb.keyframe_insert("location", frame=F_HIT); pb.keyframe_insert("rotation_quaternion", frame=F_HIT)
    return dict(sombrero=[round(v, 2) for v in land])


# ====================================================================== CONEJO
def conejo():
    sc.frame_set(F_HIT); p0 = Vector(RE.location); yaw0 = RE.rotation_euler.z
    borrar_desde(RE, F_HIT + 1); borrar_desde(RA, F_HIT + 1)
    # zanahoria: se le cae al suelo
    zl = Vector(ZA.location); borrar_desde(ZA, F_HIT + 1, excepto=("hide", "Mordidas"))
    for f in range(F_HIT + 1, F_HIT + 8):
        t = (f - F_HIT) / 7; ZA.location = (zl.x, zl.y, zl.z + (9.03 - zl.z) * t * t); ZA.keyframe_insert("location", frame=f)
        ZA.rotation_euler = (math.radians(90 * (1 - t)), 0, ZA.rotation_euler.z); ZA.keyframe_insert("rotation_euler", frame=f)
    for b in [x for x in bpy.data.objects if x == ZA]:
        for cb in bags(ZA):
            for fc in cb.fcurves:
                if fc.data_path.startswith("hide"):
                    for k in [k for k in fc.keyframe_points if k.co.x > F_HIT][::-1]: fc.keyframe_points.remove(k)
                    fc.update()
        ZA.hide_render = ZA.hide_viewport = False; ZA.keyframe_insert("hide_render", frame=F_HIT + 1); ZA.keyframe_insert("hide_viewport", frame=F_HIT + 1)
    # huye hacia el este con saltos
    dirr = Vector((1, 0.15, 0)).normalized(); yaw = math.atan2(-dirr.x, dirr.y); H = 7; N = 6; F0 = F_HIT + 3
    S_ = "_rabbit_1"
    def key(b, ang, f):
        pb = RA.pose.bones[b + S_]; pb.rotation_quaternion = Quaternion((1, 0, 0), math.radians(ang)); pb.keyframe_insert("rotation_quaternion", frame=f)
    for b in [pb.name[:-len(S_)] for pb in RA.pose.bones]:
        RA.pose.bones[b + S_].location = (0, 0, 0); RA.pose.bones[b + S_].keyframe_insert("location", frame=F_HIT + 1)
        key(b, 0, F_HIT + 2)
    RE.location = p0 + Vector((0, 0, 0.12)); RE.rotation_euler = (0, 0, yaw0); RE.keyframe_insert("location", frame=F_HIT + 2); RE.keyframe_insert("rotation_euler", frame=F_HIT + 2)
    for f in range(F0, F0 + H * N + 1):
        u = (f - F0) / H; n = int(u); t = u - n
        if f == F0 + H * N: n, t = N - 1, 1.0
        a = ss(min(1, max(0, (t - 0.15) / 0.7))); air = math.sin(math.pi * min(1, max(0, (t - 0.15) / 0.7)))
        RE.location = p0 + dirr * 0.85 * (n + a) + Vector((0, 0, 0.32 * air))
        RE.rotation_euler = (0, 0, yaw0 + (yaw - yaw0) * ss((f - F0) / 6)); RE.keyframe_insert("location", frame=f); RE.keyframe_insert("rotation_euler", frame=f)
        for b in ("Femur_L", "Femur_R"): key(b, 45 * air, f)
        for b in ("Tibia_L", "Tibia_R"): key(b, -30 * air, f)
        for b in ("Humerus_L", "Humerus_R"): key(b, -40 * air, f)
        key("Chest", -8 * air, f); key("EarBase_L", 20 * air, f); key("EarBase_R", 20 * air, f)
    fend = F0 + H * N
    RE.keyframe_insert("location", frame=sc.frame_end); RE.keyframe_insert("rotation_euler", frame=sc.frame_end)
    return dict(huye_hasta=fend, fin=[round(v, 2) for v in RE.location])


def sonidos():
    st = sc.sequence_editor.strips
    for x in [x for x in st if x.name.startswith("choque_")]: st.remove(x)
    for x in [x for x in st if x.type == 'SOUND' and x.name.startswith(("conejo_come", "conejo_snd")) and x.frame_final_start > F_HIT]: st.remove(x)
    rnd = random.Random(21); ch = 22
    def add(n, p, f, v):
        s = st.new_sound("choque_" + n, S + p, ch, f); s.volume = v
    add("golpe1", "damage\\hit2.ogg", F_HIT, 1.0); add("golpe2", "damage\\hit3.ogg", F_HIT + 1, 0.7)
    add("alfred_cae", "damage\\fallsmall.ogg", F_HIT + 14, 0.8); add("jerry_cae", "damage\\fallsmall.ogg", F_HIT + 15, 0.7)
    add("sombrero", "step\\cloth1.ogg" if os.path.isfile(S + "step\\cloth1.ogg") else "step\\grass2.ogg", F_HIT + 18, 0.5)
    add("zanahoria", "step\\grass3.ogg", F_HIT + 7, 0.3)
    for k in range(6): add("conejo_hop%d" % k, "mob\\rabbit\\hop%d.ogg" % rnd.randint(1, 4), F_HIT + 3 + 7 * k + 2, 0.35)
    add("conejo_chillido", "mob\\rabbit\\hurt%d.ogg" % rnd.randint(1, 4), F_HIT + 2, 0.45)
    # trote de jerry
    for k in range(7): add("jerry_paso%d" % k, "step\\grass%d.ogg" % rnd.randint(1, 6), F_HIT - 30 + 3 * k, 0.15)


def run():
    sc.frame_end = max(sc.frame_end, 860)
    sc.frame_set(F_HIT); face = AA.matrix_world @ AA.pose.bones["face_alfred"].head
    sc.frame_set(F_HIT - 4); face_prev = AA.matrix_world @ AA.pose.bones["face_alfred"].head
    dir_a = (face - face_prev); dir_a.z = 0; dir_a.normalize()
    contact = face + dir_a * 0.14 + Vector((0, 0, 0.05))
    d = Vector((0.707, -0.707, 0))
    out = {"conejo": conejo()}
    out["jerry"] = jerry(contact, d)
    out["sombrero"] = sombrero(d)
    out["alfred"] = alfred()
    alfred_soba(F_HIT + 20, sc.frame_end)
    sonidos()
    sc.frame_set(1); bpy.ops.wm.save_mainfile()
    return out


def _job():
    ns = bpy.app.driver_namespace
    try: ns["choque"] = ("ok", run())
    except Exception:
        import traceback; ns["choque"] = traceback.format_exc()


bpy.app.driver_namespace["choque"] = "run"
bpy.app.timers.register(_job, first_interval=0.1)
