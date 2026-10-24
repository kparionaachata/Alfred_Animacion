"""Alfred, asustado con la arana en la cara, corre rapido en circulos con los brazos en V (despues del impacto, arana_salta_cara.F_CARA=814).
- Ruta: desde donde esta (cadera en ~(-44.56,-14.28)) corre al oeste y da vueltas (antihorario) en la zona plana z=-9 entre x -50 y -46
  (centro CIRCULO, radio RADIO), lejos de Jerry (-45.5,-15.5) y del hoyo (-47,-18). El empty `alfred` lleva posicion y rumbo (claves
  por frame desde F_INI); el suelo es plano asi que su z no cambia.
- Cuerpo: capa NLA REPLACE `Alfred_corre_circulos` (piernas, rodillas, cadera con rebote y balanceo, tronco inclinado, cabeza que se
  sacude, brazos en V que se agitan). Entra rapido en F_INI..F_INI+ENTRA.
- Despues hay que volver a ejecutar arana_salta_cara.construir() para que la arana siga a la cabeza en la carrera.
Uso (Blender):  exec(open(r"...\\alfred_corre_circulos.py", encoding="utf8").read()); construir()      (repetible)
"""
import bpy, math, json
from mathutils import Vector, Matrix, Quaternion, Euler

F_INI, ENTRA = 556, 6
# zona libre a z=-9 medida con rayos (los nombres de algunos bloques no coinciden con su sitio): suelo libre x -50..-44, y -17..-13;
# obstaculos: estalagmitas (-48.47,-14.5) y (-45.5,-14.5), Jerry (-45.5,-15.5), antorcha (-44.5,-15.5); agua en el suelo en y < -17.
# Ovalo entre la estalagmita oeste, Jerry y el agua (cuerpo de Alfred ~0.35 m de radio, holgura comprobada)
CIRCULO, RADIO, RADIO_Y, ANG0 = Vector((-47.9, -15.75)), 1.2, 0.6, math.radians(60)
SENTIDO = -1                       # -1 = horario (asi llega a la estalagmita desde el suroeste y al caer de espaldas no golpea a Jerry)
# entrada: por el pasillo norte (y -13.6) rodeando la estalagmita (-45.5,-14.5) y bajando entre las dos estalagmitas
ENTRADA = [Vector((-44.9, -13.6)), Vector((-46.4, -13.6)), Vector((-47.0, -14.6))]
VEL, ACEL_F = 4.5, 10              # m/s y frames hasta llegar a esa velocidad
GIRO_F = 8                          # frames para darse la vuelta (miraba al este, corre al oeste)
PERIODO = 14                        # frames por ciclo de carrera (2 pasos)
PIERNA, RODILLA = 45.0, 80.0        # grados
LEAN, SACUDE = 20.0, 12.0           # tronco hacia delante; sacudida de la cabeza
V_ABRE, AGITA = 0.55, 10.0          # apertura de la V (componente lateral) y agitado de los brazos (grados)
POSE_MIRA = r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/poses/parado_mirando a la araña.json"
PISTA = "Alfred_corre_circulos"
R = math.radians


def _base():
    b = json.load(open(POSE_MIRA, encoding="utf8"))["poses"][0]["bones"]
    return {n: ([R(d["raw_rotation_euler_deg"][a]) for a in "xyz"], [d["raw_location"][a] for a in "xyz"]) for n, d in b.items()}


def _ruta(P0, fin):
    """lista de puntos por frame (xy) desde F_INI hasta fin: entrada suave al circulo + vueltas a velocidad VEL."""
    pts = [P0.copy()] + [p.copy() for p in ENTRADA]
    a0 = ANG0; n = 600
    for i in range(n + 1):
        a = a0 + SENTIDO * 2 * math.pi * 12 * i / n
        pts.append(CIRCULO + Vector((math.cos(a) * RADIO, math.sin(a) * RADIO_Y)))
    for _ in range(3):                                                # Chaikin: redondea la entrada
        nuevo = [pts[0]]
        for p, q in zip(pts, pts[1:]): nuevo += [p.lerp(q, 0.25), p.lerp(q, 0.75)]
        nuevo.append(pts[-1]); pts = nuevo
    acum = [0.0]
    for p, q in zip(pts, pts[1:]): acum.append(acum[-1] + (q - p).length)
    def en(s):
        s = max(0.0, min(acum[-1], s)); lo, hi = 0, len(acum) - 1
        while hi - lo > 1:
            m = (lo + hi) // 2
            if acum[m] <= s: lo = m
            else: hi = m
        u = (s - acum[lo]) / max(1e-9, acum[hi] - acum[lo]); return pts[lo].lerp(pts[hi], u)
    v = VEL / 24.0; s = 0.0; out = []
    for f in range(F_INI, fin + 1):
        k = min(1.0, (f - F_INI) / ACEL_F); s += v * k * k * (3 - 2 * k) if f > F_INI else 0.0
        out.append((f, en(s), en(s + 0.05) - en(max(0.0, s - 0.05))))
    return out


def _brazo_v(arm, hueso, objetivo_w):
    """rotacion euler (basis) para que el brazo apunte a `objetivo_w` (mundo) con la pose actual de los padres."""
    pb = arm.pose.bones[hueso]; b = pb.bone; W = arm.matrix_world
    d0 = (W.to_3x3() @ (pb.tail - pb.head)).normalized()
    q = d0.rotation_difference(objetivo_w.normalized())
    Mw = W @ pb.matrix; t = Mw.translation.copy()
    Mn = Matrix.Translation(t) @ q.to_matrix().to_4x4() @ Matrix.Translation(-t) @ Mw
    Ma = W.inverted() @ Mn
    par = pb.parent; P = par.matrix @ par.bone.matrix_local.inverted() @ b.matrix_local
    return (P.inverted() @ Ma).to_euler('XYZ', pb.rotation_euler)


def construir():
    sc = bpy.context.scene; fin = sc.frame_end; f_act = sc.frame_current
    emp = bpy.data.objects["alfred"]; arm = bpy.data.objects["Armature"]; ad = arm.animation_data
    for t in list(ad.nla_tracks):
        if t.name == PISTA:
            a = [s.action for s in t.strips]; ad.nla_tracks.remove(t)
            for x in a:
                if x and x.users == 0: bpy.data.actions.remove(x)
    # --- estado al empezar (sin la capa de carrera)
    sc.frame_set(F_INI)
    E0 = emp.matrix_world.translation.copy(); q0 = emp.matrix_world.to_quaternion()
    H0 = arm.matrix_world @ arm.pose.bones["Hips_alfred"].head
    ojos = []
    dg = bpy.context.evaluated_depsgraph_get()
    for n in ("ojo_izquierdo_alfred", "ojo_derecho_alfred"):
        e = bpy.data.objects[n].evaluated_get(dg); ojos += [e.matrix_world @ v.co for v in e.data.vertices]
    cara = sum(ojos, Vector()) / len(ojos); F0 = (cara - H0); F0.z = 0; F0.normalize()
    rumbo0 = math.atan2(F0.y, F0.x); off = (H0 - E0); off.z = 0
    base = _base()
    # --- brazos en V (con el tronco inclinado de la carrera)
    pb = arm.pose.bones
    guard = {n: (tuple(pb[n].rotation_euler), tuple(pb[n].location)) for n in base}
    for n, (e, l) in base.items(): pb[n].rotation_euler = e; pb[n].location = l
    pb["Spine_alfred"].rotation_euler.x = base["Spine_alfred"][0][0] + R(LEAN)
    pb["Rightelbow_alfred"].rotation_euler = (0, 0, 0); pb["Leftelbow_alfred"].rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    W = arm.matrix_world                                               # V simetrica respecto del tronco (no del mundo)
    T = (W @ pb["Neck_alfred"].head - W @ pb["Spine_alfred"].head).normalized()
    Rb = (W @ pb["RightUpArm_alfred"].head - W @ pb["LeftUpArm_alfred"].head); Rb -= T * Rb.dot(T); Rb.normalize()
    Fb = T.cross(Rb).normalized()
    if Fb.dot(F0) < 0: Fb.negate()
    v_der = _brazo_v(arm, "RightUpArm_alfred", T + Rb * V_ABRE + Fb * 0.15)
    v_izq = _brazo_v(arm, "LeftUpArm_alfred", T - Rb * V_ABRE + Fb * 0.15)
    for n, (e, l) in guard.items(): pb[n].rotation_euler = e; pb[n].location = l
    # --- accion de la carrera
    act = bpy.data.actions.get(PISTA)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(PISTA); slot = act.slots.new(arm.id_type, arm.name)
    cb = act.layers.new("Layer").strips.new(type='KEYFRAME').channelbags.new(slot)
    canales = {}
    def k(h, ruta, i, f, v): canales.setdefault((f'pose.bones["{h}"].{ruta}', i), []).append((f, v))
    ruta = _ruta(H0.to_2d(), fin)
    claves_emp = []
    rumbo_prev = None
    for f, P, tg in ruta:
        t = f - F_INI; ph = 2 * math.pi * t / PERIODO
        amp = min(1.0, t / ACEL_F) if ACEL_F else 1.0; amp = amp * amp * (3 - 2 * amp)
        # piernas y rodillas
        for lado, sg, fase in (("Right", 1.0, 0.0), ("Left", -1.0, math.pi)):
            e, _ = base[f"{lado}UpLeg_alfred"]
            k(f"{lado}UpLeg_alfred", "rotation_euler", 0, f, e[0] + amp * R(PIERNA) * math.sin(ph + fase))
            k(f"{lado}UpLeg_alfred", "rotation_euler", 1, f, e[1]); k(f"{lado}UpLeg_alfred", "rotation_euler", 2, f, e[2])
            k(f"{lado}knee_alfred", "rotation_euler", 0, f, -amp * R(10 + RODILLA * max(0.0, math.cos(ph + fase))))
        # cadera: rebote (z local positiva = abajo), balanceo
        e, l = base["Hips_alfred"]
        sube = amp * (0.06 * (1 - abs(math.sin(ph))) - 0.03)
        k("Hips_alfred", "location", 0, f, l[0]); k("Hips_alfred", "location", 1, f, l[1]); k("Hips_alfred", "location", 2, f, l[2] - sube)
        k("Hips_alfred", "rotation_euler", 0, f, e[0]); k("Hips_alfred", "rotation_euler", 1, f, e[1])
        k("Hips_alfred", "rotation_euler", 2, f, e[2] + amp * R(8) * math.sin(ph))
        # tronco, cabeza
        e, _ = base["Spine_alfred"]
        k("Spine_alfred", "rotation_euler", 0, f, e[0] + R(LEAN)); k("Spine_alfred", "rotation_euler", 1, f, e[1]); k("Spine_alfred", "rotation_euler", 2, f, e[2] - amp * R(6) * math.sin(ph))
        e, _ = base["Neck_alfred"]
        k("Neck_alfred", "rotation_euler", 0, f, e[0] + R(6) * math.sin(2 * math.pi * t / 7)); k("Neck_alfred", "rotation_euler", 1, f, e[1])
        k("Neck_alfred", "rotation_euler", 2, f, e[2] + R(SACUDE) * math.sin(2 * math.pi * t / 10))
        # brazos en V agitandose
        for h, vv, s in (("RightUpArm_alfred", v_der, 1.0), ("LeftUpArm_alfred", v_izq, -1.0)):
            ag = R(AGITA) * math.sin(2 * math.pi * t / 6 + (0 if s > 0 else math.pi))
            k(h, "rotation_euler", 0, f, vv[0] + ag); k(h, "rotation_euler", 1, f, vv[1]); k(h, "rotation_euler", 2, f, vv[2] + 0.5 * ag)
        for h in ("Rightelbow_alfred", "Leftelbow_alfred"):
            for i in range(3): k(h, "rotation_euler", i, f, R(8) * math.sin(2 * math.pi * t / 6) if i == 0 else 0.0)
        # rumbo del empty: de mirar al este a la direccion de la ruta
        rumbo_t = math.atan2(tg.y, tg.x) if tg.length > 1e-6 else rumbo0
        if rumbo_prev is not None:
            while rumbo_t - rumbo_prev > math.pi: rumbo_t -= 2 * math.pi
            while rumbo_t - rumbo_prev < -math.pi: rumbo_t += 2 * math.pi
        if t < GIRO_F:
            u = t / GIRO_F; u = u * u * (3 - 2 * u)
            d = rumbo_t - rumbo0
            while d > math.pi: d -= 2 * math.pi
            while d < -math.pi: d += 2 * math.pi
            rumbo = rumbo0 + d * u
        else: rumbo = rumbo_t
        rumbo_prev = rumbo_t
        Rz = Quaternion((0, 0, 1), rumbo - rumbo0)
        loc = Vector((P.x, P.y, 0)) - Rz @ off; loc.z = E0.z
        qe = Rz @ q0
        if claves_emp and qe.dot(claves_emp[-1][2]) < 0: qe.negate()     # continuidad del cuaternion
        claves_emp.append((f, loc, qe))
    for (ruta_, i), cl in canales.items():
        fc = cb.fcurves.new(ruta_, index=i); fc.keyframe_points.add(len(cl))
        for kp, (f, v) in zip(fc.keyframe_points, cl): kp.co = (f, v); kp.interpolation = 'LINEAR'
        fc.update()
    tr = ad.nla_tracks.new(); tr.name = PISTA
    st = tr.strips.new(PISTA, F_INI, act); st.blend_type = 'REPLACE'; st.extrapolation = 'HOLD_FORWARD'
    try: st.action_slot = slot
    except Exception: pass
    st.use_animated_influence = True; fi = st.fcurves.find("influence")
    for kp in list(fi.keyframe_points): fi.keyframe_points.remove(kp)
    for f, v in ((F_INI, 0.0), (F_INI + ENTRA, 1.0)): fi.keyframe_points.insert(f, v).interpolation = 'BEZIER'
    # --- empty: borra sus claves desde F_INI y pone la ruta
    ea = emp.animation_data.action
    for lay in ea.layers:
        for s in lay.strips:
            for c in s.channelbags:
                for fc in c.fcurves:
                    if fc.data_path in ("location", "rotation_quaternion"):
                        for kp in reversed(list(fc.keyframe_points)):
                            if kp.co[0] >= F_INI: fc.keyframe_points.remove(kp)
    for f, loc, q in claves_emp:
        emp.location = loc; emp.rotation_quaternion = q
        emp.keyframe_insert("location", frame=f); emp.keyframe_insert("rotation_quaternion", frame=f)
    sc.frame_set(f_act)
    return {"inicio": F_INI}
