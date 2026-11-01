# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: despues de "Pero acaso no me ves...", Alfred dice "mejor continuemos buscando hierro en esta capa" (voz 812-868, `animacion_alfred (39).py`)
y mientras habla: se empieza a poner de pie (a medias), explica con la mano derecha y con la izquierda intenta recoger su pico de piedra, pero al acercar la mano lo
empuja por el precipicio: el pico sale volando del borde, cae girando hasta el fondo de la caverna y rebota hasta quedar quieto (fisica con raycast sobre el suelo real).
Fases (frames): levantarse parcial 816-840 | mano derecha explica 818-872 | cuerpo se adelanta + brazo izquierdo alcanza 832-848 | empuje 852-866 (el pico sigue a la mano) |
suelta el pico en 866 | brazo vuelve 872-888. Todo SE SUMA a las claves actuales (no repetible sin regenerar antes la animacion de Alfred y del pico).
Uso en Blender: exec(open(ruta, encoding="utf8").read()); r = construir()      (devuelve los rebotes del pico para sonorizar: sonorizar_pico(r))
"""
import bpy, math, random
from mathutils import Matrix, Vector, Euler, Quaternion
from bpy_extras import anim_utils

ARM, EMP, PICO = "Armature", "alfred", "alfred_pico_piedra"
UP, CODO, PADRE = "LeftUpArm_alfred", "Leftelbow_alfred", "Spine2_alfred"
CUERPO = ("Hips_alfred", "Spine_alfred", "Spine1_alfred", "Spine2_alfred", "RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred")
F_PIE_REF = 245                 # frame con Alfred de pie (pose de referencia)
SUBE = (816, 24)                # levantarse a medias
PARCIAL = 0.55
ADELANTA1, ADELANTA2 = (832, 16), (852, 12)          # el cuerpo se adelanta para llegar al pico y luego sigue el empuje
ALCANZA, EMPUJA, VUELVE = (832, 16), (852, 12), (872, 16)
F_CONTACTO0, F_SUELTA = 848, 866
EXPLICA = (818, 12, 862, 10)    # sube, y baja desde 862 (duraciones)
EMPUJADOR, EMPUJA_OFF, EMPUJA_DIST = CODO, 0.12, 0.3          # hueso cuya punta empuja al pico, distancia por delante y distancia de contacto
ROCE, SUELTA = [], []         # frames del roce al empujar y de la suelta (los llena animar_pico)
BORDE_Y = 83.338                # borde del bloque donde esta Alfred (cara -Y)
PASA_BORDE = 0.04               # m que pasa el centro del pico del borde antes de soltarlo: ahi se inclina y cae
VEL_MIN_EMPUJE = 0.8            # m/s al soltarlo (lo empuja de un golpe)
G = 9.8
PICO_REPOSO = (0.47372, 83.431, 66.048)          # donde queda el pico desde el frame 300 (posicion indicada por el usuario: Alfred lo golpea sin querer al levantarse)
PICO_QUAT = (0.558, 0.011, 0.015, -0.830)
SIGNO = 1.0                     # -1 para DESHACER lo aplicado (se restan los mismos deltas)
REST = 0.32                     # restitucion de los rebotes del pico
TOPE_D1, TOPE_D2 = 0.0, 0.0    # m que se adelanta el cuerpo: NINGUNO (se levanta en su sitio; llega al pico estirando brazo y torso)
INCLINA = (0.35, 0.55)          # rad de inclinacion del torso (Spine y Spine1, cada uno) al alcanzar / empujar


def S(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def w(par, f):
    a, d = par
    return S((f - a) / float(d))


def _cb(ob):
    return anim_utils.action_get_channelbag_for_slot(ob.animation_data.action, ob.animation_data.action_slot)


def _canal(cb, dp, idx):
    fc = cb.fcurves.find(dp, index=idx)
    return fc if fc is not None else cb.fcurves.new(dp, index=idx)


def _sumar(ob, dp, idx, delta_fn, f0=800, f1=None):
    """nuevo(f) = actual(f) + delta_fn(f) para f0..f1 (claves por frame LINEAR); delta_fn(f)=0 antes de su rango"""
    sc = bpy.context.scene
    f1 = f1 or sc.frame_end
    cb = _cb(ob)
    fc = _canal(cb, dp, idx)
    base = {f: (fc.evaluate(f) if len(fc.keyframe_points) else None) for f in range(f0, f1 + 1)}
    if base[f0] is None:
        prop = dp.split(".")[-1]
        v = getattr(ob.pose.bones[dp.split('"')[1]] if "pose.bones" in dp else ob, prop)[idx]
        base = {f: v for f in base}
    for i in range(len(fc.keyframe_points) - 1, -1, -1):
        if fc.keyframe_points[i].co.x >= f0:
            fc.keyframe_points.remove(fc.keyframe_points[i])
    for f in range(f0, f1 + 1):
        fc.keyframe_points.insert(f, base[f] + SIGNO * delta_fn(f), options={'FAST'}).interpolation = 'LINEAR'
    fc.update()


def _fk(arm, M_padre, e_up, e_codo):
    up, co, pad = arm.pose.bones[UP], arm.pose.bones[CODO], arm.pose.bones[PADRE]
    bas = lambda pb, e: Matrix.Translation(pb.location) @ Euler(e, 'XYZ').to_matrix().to_4x4()
    M_up = M_padre @ (pad.bone.matrix_local.inverted() @ up.bone.matrix_local) @ bas(up, e_up)
    M_co = M_up @ (up.bone.matrix_local.inverted() @ co.bone.matrix_local) @ bas(co, e_codo)
    return M_up, M_co


def resolver_mano(arm, objetivo_w, inicio):
    """angulos (up x,y,z, codo z) que llevan la punta del antebrazo a `objetivo_w` (descenso de coordenadas); devuelve (angulos, error)"""
    M_padre = arm.pose.bones[PADRE].matrix.copy()
    obj = arm.matrix_world.inverted() @ objetivo_w
    co = arm.pose.bones[CODO]
    L = co.bone.length
    e_co = list(co.rotation_euler)

    def coste(p):
        M_up, M_co = _fk(arm, M_padre, p[:3], (e_co[0], e_co[1], p[3]))
        mano = M_co @ Vector((0, L, 0))
        return (mano - obj).length
    p, mejor, paso = list(inicio), None, 0.6
    mejor = coste(p)
    for _ in range(500):
        mejoro = False
        for i in range(4):
            for s in (+1, -1):
                q = list(p)
                q[i] += s * paso
                c = coste(q)
                if c < mejor - 1e-7:
                    p, mejor, mejoro = q, c, True
        if not mejoro:
            paso *= 0.6
            if paso < 1e-3:
                break
    return p, mejor


def _piso(sc, dg, x, y, z):
    o = Vector((x, y, z))
    for _ in range(10):
        ok, pos, nor, idx, ob, mw = sc.ray_cast(dg, o, Vector((0, 0, -1)), distance=200)
        if not ok:
            return None
        if ob.name.startswith(("caverna_", "bloque_")) or "Block" in ob.name:
            return pos.z
        o = pos + Vector((0, 0, -0.02))
    return None


def simular(sc, dg, p0, v0, q0, rng, om0=None):
    """cae, gira en el aire y rebota; devuelve (frames [(pos, quat)], rebotes [(frame_float, pos, velocidad_impacto)])"""
    dt, sub = 1.0 / 24.0, 8
    h = dt / sub
    p, v, q = Vector(p0), Vector(v0), Quaternion(q0)
    om = Vector(om0) if om0 is not None else Vector((rng.uniform(3, 5) * rng.choice((-1, 1)), rng.uniform(2, 4) * rng.choice((-1, 1)), rng.uniform(3, 6) * rng.choice((-1, 1))))
    out, reb, calma, n_reb = [], [], 0, 0
    t = 0.0
    for fr in range(0, 480):
        for _ in range(sub):
            v.z -= G * h
            p += v * h
            ang = om.length * h
            if ang > 1e-9:
                q = (Quaternion(om.normalized(), ang) @ q).normalized()
            if n_reb >= 4:                                         # despues del cuarto rebote se frena pronto (ya rueda sobre piedra)
                v *= max(0.0, 1 - 3.0 * h)
                om *= max(0.0, 1 - 4.0 * h)
            fz = _piso(sc, dg, p.x, p.y, p.z + 0.5)
            if fz is None:
                continue
            r = 0.05 if fz > p.z - 1.0 else (0.22 if om.length > 1.5 else 0.05)
            if p.z - r < fz and v.z < 0.2:
                p.z = fz + r
                s = -v.z
                if s > 1.0:
                    reb.append((fr + (_ + 1) / sub, p.copy(), s))
                    n_reb += 1
                    v.z = s * REST
                    v.x *= 0.7
                    v.y *= 0.7
                    om = om * 0.62 + Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * 0.18 * min(s, 12)
                else:
                    v.z = 0.0
                    v.x *= max(0.0, 1 - 4.0 * h)
                    v.y *= max(0.0, 1 - 4.0 * h)
                    om *= max(0.0, 1 - 6.0 * h)
        out.append((p.copy(), q.copy()))
        if n_reb >= 3 and v.length < 0.9 and om.length < 1.2:
            calma += 1
            if calma > 6:
                break
        else:
            calma = 0
    return out, reb


MALLAS = ["Mesh_%d_alfred" % i for i in range(6)]


def _suelo(sc, arm):
    """funcion f -> dz que mantiene el punto mas bajo de las mallas de Alfred en el suelo (el que tenia arrodillado en SUBE[0]-1); se muestrea cada 2 frames"""
    O = bpy.data.objects
    dg = bpy.context.evaluated_depsgraph_get()

    def minimo(f):
        sc.frame_set(f)
        bpy.context.view_layer.update()
        d = bpy.context.evaluated_depsgraph_get()
        zs = []
        for n in MALLAS:
            ob = O[n].evaluated_get(d)
            me = ob.to_mesh()
            zs.append(min((ob.matrix_world @ v.co).z for v in me.vertices))
            ob.to_mesh_clear()
        return min(zs)
    suelo = minimo(SUBE[0] - 1)
    tabla = {f: suelo - minimo(f) for f in range(SUBE[0] - 1, EXPLICA[2] + 41, 2)}
    sc.frame_set(1)
    ks = sorted(tabla)

    def dz(f):
        if f <= ks[0]:
            return 0.0
        if f >= ks[-1]:
            return tabla[ks[-1]]
        a = ks[0] + ((f - ks[0]) // 2) * 2
        b = a + 2
        return tabla[a] + (tabla[b] - tabla[a]) * (f - a) / 2.0
    return dz


def construir(deshacer=False, reponer=False):
    global SIGNO
    SIGNO = -1.0 if deshacer else 1.0
    deshacer_o_reponer = deshacer or reponer
    sc = bpy.context.scene
    O = bpy.data.objects
    arm, emp, pico = O[ARM], O[EMP], O[PICO]
    rng = random.Random(5)
    fin = sc.frame_end
    cb_a, cb_e = _cb(arm), _cb(emp)
    sc.frame_set(F_PIE_REF)
    bpy.context.view_layer.update()
    ref = {}
    for h in CUERPO:
        for dp, n in (("rotation_euler", 3), ("location", 3)):
            for i in range(n):
                fc = cb_a.fcurves.find('pose.bones["%s"].%s' % (h, dp), index=i)
                ref[(h, dp, i)] = fc.evaluate(F_PIE_REF) if fc is not None else (0.0 if dp == "location" else 0.0)
    z_ref = _canal(cb_e, "location", 2).evaluate(F_PIE_REF)
    # ---- 1) levantarse a medias (cuerpo + empty z)
    for h in CUERPO:
        for dp in ("rotation_euler", "location"):
            for i in range(3):
                if dp == "location" and h != "Hips_alfred":
                    continue
                fcx = cb_a.fcurves.find('pose.bones["%s"].%s' % (h, dp), index=i)
                v0 = fcx.evaluate(SUBE[0]) if fcx is not None and len(fcx.keyframe_points) else getattr(arm.pose.bones[h], dp)[i]
                T = ref[(h, dp, i)]
                _sumar(arm, 'pose.bones["%s"].%s' % (h, dp), i, lambda f, T=T, v0=v0: (T - v0) * PARCIAL * w(SUBE, f), SUBE[0] - 1)
    # ---- 2) el cuerpo se adelanta hacia el pico (empty x,y) e inclina el torso
    sc.frame_set(SUBE[0] - 1)
    bpy.context.view_layer.update()
    raiz = Vector(emp.location)
    pico0 = Vector(PICO_REPOSO)
    d1 = Vector((pico0.x - raiz.x, pico0.y - raiz.y, 0))
    D1 = d1.normalized() * min(TOPE_D1, max(0.0, d1.length - 0.2))
    tgt2 = Vector((pico0.x, pico0.y - 1.1, 0))
    d2 = Vector((tgt2.x - raiz.x, tgt2.y - raiz.y, 0))
    D2 = d2.normalized() * min(TOPE_D2, max(0.0, d2.length - 0.2))
    for h, k in (("Spine_alfred", 1.0), ("Spine1_alfred", 1.0)):
        _sumar(arm, 'pose.bones["%s"].rotation_euler' % h, 0, lambda f, k=k: INCLINA[0] * k * w(ADELANTA1, f) + (INCLINA[1] - INCLINA[0]) * k * w(ADELANTA2, f), SUBE[0] - 1)
    # ---- 3) mano derecha explica
    e0, d0, e1, d1_ = EXPLICA
    env = lambda f: S((f - e0) / float(d0)) * (1 - S((f - e1) / float(d1_)))
    _sumar(arm, 'pose.bones["RightUpArm_alfred"].rotation_euler', 0, lambda f: (0.35 + 0.18 * math.sin(2 * math.pi * (f - e0) / 21.0)) * env(f), e0 - 1)
    _sumar(arm, 'pose.bones["RightUpArm_alfred"].rotation_euler', 2, lambda f: (0.25 * math.sin(2 * math.pi * (f - e0) / 21.0 + 1.0)) * env(f), e0 - 1)
    _sumar(arm, 'pose.bones["Rightelbow_alfred"].rotation_euler', 2, lambda f: (-0.3 + 0.35 * math.sin(2 * math.pi * (f - e0) / 21.0 + 0.5)) * env(f), e0 - 1)
    # ---- 3b) el cuerpo se adelanta y se mantiene sobre el suelo moviendo el hueso Hips (el empty `alfred` queda quieto): dz(f) apoya el punto mas bajo del cuerpo en el suelo
    if deshacer_o_reponer:                                        # el Hips vuelve a su valor constante (no tiene otros filtros)
        for i in range(3):
            fcl = _canal(cb_a, 'pose.bones["Hips_alfred"].location', i)
            v_h = fcl.evaluate(SUBE[0] - 1)
            for j in range(len(fcl.keyframe_points) - 1, -1, -1):
                if fcl.keyframe_points[j].co.x >= SUBE[0] - 1:
                    fcl.keyframe_points.remove(fcl.keyframe_points[j])
            for f in range(SUBE[0] - 1, sc.frame_end + 1):
                fcl.keyframe_points.insert(f, v_h, options={'FAST'}).interpolation = 'LINEAR'
            fcl.update()
        dz = lambda f: 0.0
    else:
        dz = _suelo(sc, arm)
    Rw = arm.matrix_world.to_3x3()
    Rb = arm.pose.bones["Hips_alfred"].bone.matrix_local.to_3x3()
    F_FIN_SUELO = EXPLICA[2] + 40
    def sw(f):                                                    # desplazamiento horizontal pedido (mundo) + vertical de apoyo
        return Vector((D1.x * w(ADELANTA1, f) + (D2.x - D1.x) * w(ADELANTA2, f), D1.y * w(ADELANTA1, f) + (D2.y - D1.y) * w(ADELANTA2, f), dz(f)))
    loc_h = lambda f: Rb.inverted() @ (Rw.inverted() @ sw(f))
    if not deshacer_o_reponer:
        for i in range(3):
            _sumar(arm, 'pose.bones["Hips_alfred"].location', i, lambda f, i=i: loc_h(f)[i], SUBE[0] - 1)
    # ---- 4) mano izquierda: alcanza el pico (848) y lo empuja (864)
    f_a, f_b = 848, 864
    base = {}
    for (h, i) in ((UP, 0), (UP, 1), (UP, 2), (CODO, 2)):
        fc = _canal(cb_a, 'pose.bones["%s"].rotation_euler' % h, i)
        base[(h, i)] = fc.evaluate(828)
    ini = [base[(UP, 0)], base[(UP, 1)], base[(UP, 2)], base[(CODO, 2)]]
    if deshacer_o_reponer:                                       # los angulos aplicados se leen de las claves (en 848 y 864 el peso es 1)
        pa = [_canal(cb_a, 'pose.bones["%s"].rotation_euler' % h, i).evaluate(f_a) for (h, i) in ((UP, 0), (UP, 1), (UP, 2), (CODO, 2))]
        pb = [_canal(cb_a, 'pose.bones["%s"].rotation_euler' % h, i).evaluate(f_b) for (h, i) in ((UP, 0), (UP, 1), (UP, 2), (CODO, 2))]
        ea = eb = 0.0
    else:
        sc.frame_set(f_a)
        bpy.context.view_layer.update()
        obj_a = pico0 + Vector((0, 0, 0.08))
        pa, ea = resolver_mano(arm, obj_a, ini)
        obj_b = Vector((pico0.x, pico0.y - 0.85, pico0.z + 0.08))
        sc.frame_set(f_b)
        bpy.context.view_layer.update()
        pb, eb = resolver_mano(arm, obj_b, pa)
    canales = [(UP, 0), (UP, 1), (UP, 2), (CODO, 2)]
    for k, (h, i) in enumerate(canales):
        v0 = base[(h, i)]
        _sumar(arm, 'pose.bones["%s"].rotation_euler' % h, i,
               lambda f, v0=v0, a=pa[k], b=pb[k]: ((a - v0) * w(ALCANZA, f) + (b - a) * w(EMPUJA, f)) * (1 - w(VUELVE, f)), ALCANZA[0] - 1)
    if deshacer_o_reponer:
        sc.frame_set(1)
        return {'deshecho': deshacer, 'repuesto': reponer}
    # ---- 5) el pico
    rebotes, ult, sp = animar_pico()
    return {"rebotes": rebotes, "reposo_en": ult, "errores_mano": (round(ea, 3), round(eb, 3)), "adelanta": (tuple(round(x, 2) for x in D1), tuple(round(x, 2) for x in D2)), "vel_empuje": round(sp, 1)}


def animar_pico():
    """el pico sigue a la mano al empujarlo (se suaviza el contacto) y sale volando por el borde; rehace TODAS sus claves desde el contacto"""
    sc = bpy.context.scene
    O = bpy.data.objects
    arm, pico = O[ARM], O[PICO]
    rng = random.Random(5)
    pico0 = Vector(PICO_REPOSO)
    dg = bpy.context.evaluated_depsgraph_get()
    cbp = _cb(pico)
    pos = {}
    pushed = False
    prev_xy = Vector((pico0.x, pico0.y))
    q0 = Quaternion(PICO_QUAT)
    f_s = None
    for f in range(F_CONTACTO0, F_SUELTA + 1):
        sc.frame_set(f)
        bpy.context.view_layer.update()
        mano = arm.matrix_world @ arm.pose.bones[EMPUJADOR].tail
        mxy = Vector((mano.x, mano.y))
        if not pushed and (mxy - Vector((pico0.x, pico0.y))).length < EMPUJA_DIST:
            pushed = True
        xy = (mxy + Vector((0, -EMPUJA_OFF))) if pushed else Vector((pico0.x, pico0.y))
        if pushed and xy.y > prev_xy.y:
            xy = prev_xy                                         # solo avanza hacia el precipicio
        xy = Vector((xy.x, max(xy.y, BORDE_Y - PASA_BORDE)))      # solo se desplaza hasta pasar un poco el borde: ahi se inclina y cae
        pos[f] = pico0.lerp(Vector((xy.x, xy.y, pico0.z)), S((f - F_CONTACTO0) / 5.0))     # el contacto entra suave (sin salto)
        prev_xy = xy
        if pushed and pos[f].y <= BORDE_Y - PASA_BORDE + 1e-4:
            f_s = f
            break
    f_s = f_s or F_SUELTA
    v = (pos[f_s] - pos[f_s - 1]) * 24.0
    dirv = Vector((0, -1, 0)) if v.length < 0.2 else Vector((v.x, v.y, 0)).normalized()
    sp = max(VEL_MIN_EMPUJE, 0.0)
    v = dirv * sp
    sc.frame_set(1)
    dg = bpy.context.evaluated_depsgraph_get()
    om0 = (2.6, rng.uniform(-0.4, 0.4), rng.uniform(-0.3, 0.3))   # gira hacia adelante sobre el borde (el extremo delantero baja) y luego sigue girando al caer
    pa_, rebotes = simular(sc, dg, pos[f_s], v, q0, rng, om0)
    for i in range(len(cbp.fcurves)):
        fc = cbp.fcurves[i]
        for j in range(len(fc.keyframe_points) - 1, -1, -1):
            if fc.keyframe_points[j].co.x >= F_CONTACTO0 - 1:
                fc.keyframe_points.remove(fc.keyframe_points[j])
    def clave(f, p, q):
        pico.location, pico.rotation_quaternion = p, q
        pico.keyframe_insert("location", frame=f)
        pico.keyframe_insert("rotation_quaternion", frame=f)
    clave(F_CONTACTO0 - 1, Vector(PICO_REPOSO), q0)                   # quieto hasta que la mano llega
    for f in range(F_CONTACTO0, f_s + 1):
        clave(f, pos[f], q0)
    ult = None
    for k, (p, q) in enumerate(pa_):
        clave(f_s + 1 + k, p, q)
        ult = f_s + 1 + k
    ROCE[:] = list(range(F_CONTACTO0 + 1, f_s + 1, 2))
    SUELTA[:] = [f_s]
    for fc in cbp.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
        fc.update()
    sc.frame_set(1)
    return [(round(f_s + 1 + fl, 1), tuple(round(x, 2) for x in pp), round(s_, 1)) for fl, pp, s_ in rebotes], ult, sp


def sonorizar_pico(rebotes=None, camara="Camera.001"):
    """sonidos del empuje (roce de piedra) y de cada rebote del pico: golpes de piedra con eco de caverna, mas flojos cuanto mas lejos de la camara"""
    import importlib.util, sys, json
    sc = bpy.context.scene
    base = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/"
    spec = importlib.util.spec_from_file_location("camara_caverna_sonidos_local", base + "camara_caverna_sonidos.py")
    cs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cs)
    m = cs.cargar_addon()
    p = sc.mcsnd
    m.indice(p, forzar=True)
    ed = sc.sequence_editor or sc.sequence_editor_create()
    for t in [t for t in m._strips(ed) if t.name.startswith(m.PREFIJO) and t.get("mcsnd_origen") == "pico_cae"]:
        m._strips(ed).remove(t)
    if rebotes is None:
        rebotes = json.loads(bpy.data.texts["rebotes_pico"].as_string())
    rng = random.Random(3)
    cam = bpy.data.objects[camara].matrix_world.translation
    puestos = []

    def poner(ev, f, vol, eco=False):
        rutas = m.rutas_de(p, ev)
        if not rutas or vol < 0.02:
            return
        r = rng.choice(rutas)
        if eco:
            r = (cs._procesado(r[0], 1.0, True), r[1])
        t = m.colocar(bpy.context, p, [r], int(round(f)), "golpes", ev.replace(".", "_"), min(vol, 3.0), 0, m.rng_de(p))
        if t:
            t["mcsnd_origen"] = "pico_cae"
            puestos.append((t.name, int(round(f)), round(vol, 2)))
    for f in (ROCE or (850,)):                                   # el pico roza el suelo al ser empujado
        poner("block.stone.step", f, 0.55)
    for fl, pos, s in rebotes:
        d = (Vector(pos) - cam).length
        vol = min(1.0, s / 10.0) * max(0.0, 1 - d / 150.0) ** 0.9 * 2.4
        poner("block.stone.hit", fl, vol, eco="fuerte")
    return puestos
