# -*- coding: utf-8 -*-
"""Alfred de 'Alfred tala arboles y los bonobos le tiran cosas' (base_tarde con las ranas.blend, 24 fps).
Alfred se anima con poses FK por direccion (`apuntar`, ver bonobos_madera_lib.py) y el caminar de la biblioteca (slot_001_caminar_1).
Ejecutar (en la escena viva): exec(open(este_archivo).read()); luego construir_alfred(hasta_escena).
Devuelve/llena G (frames de eventos: impactos, soltar objetos...) que usan los bonobos y los objetos lanzados."""
import bpy, math, os
from mathutils import Vector, Matrix, Euler, Quaternion

exec(open(r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\bonobos_madera_lib.py", encoding='utf8').read())

G = {}                      # eventos: nombre -> frame / dato
_ULT = {}                   # ultima euler por hueso (continuidad)
V = lambda x, y, z: Vector((x, y, z))
BONES_POSE = ['Hips_alfred', 'Spine_alfred', 'Spine1_alfred', 'Spine2_alfred', 'Neck_alfred', 'RightUpArm_alfred', 'Rightelbow_alfred', 'LeftUpArm_alfred',
              'Leftelbow_alfred', 'RightUpLeg_alfred', 'Rightknee_alfred', 'LeftUpLeg_alfred', 'Leftknee_alfred']

BASE = dict(R=V(0.12, 0.0, -1), Rf=V(0.10, 0.30, -0.95), L=V(-0.12, 0.0, -1), Lf=V(-0.10, 0.25, -0.95),
            rl=V(0.0, 0.10, -1), rs=V(0.0, -0.10, -1), ll=V(0.0, 0.10, -1), ls=V(0.0, -0.10, -1),
            lean=0.0, lean_lado=0.0, neck=0.0, neck_lado=0.0, hips_dz=0.0, hips_dy=0.0)


def _key(arm, name, f):
    pb = arm.pose.bones[name]
    e = pb.rotation_euler.copy()
    if (arm.name, name) in _ULT:
        e.make_compatible(_ULT[(arm.name, name)])
    _ULT[(arm.name, name)] = e.copy()
    pb.rotation_euler = e
    pb.keyframe_insert('rotation_euler', frame=f, group=name)
    if name in ('Hips_alfred', 'RightUpArm_alfred', 'LeftUpArm_alfred'):
        pb.keyframe_insert('location', frame=f, group=name)


def pa(f, **kw):
    """pose de Alfred en el frame f (direcciones en el espacio del personaje: x derecha, y adelante, z arriba)"""
    arm, root = rig_alfred()
    p = dict(BASE); p.update(kw)
    reset_pose(arm)
    hips = arm.pose.bones['Hips_alfred']
    if p['hips_dz'] or p['hips_dy']:
        bpy.context.view_layer.update()
        M = hips.matrix.copy()
        hips.matrix = Matrix.Translation((0, p['hips_dy'], -p['hips_dz'])) @ M
        bpy.context.view_layer.update()
    l = p['lean']; ll = p['lean_lado']
    for b, k in (('Spine_alfred', 0.30), ('Spine1_alfred', 0.35), ('Spine2_alfred', 0.35)):
        apuntar(arm, b, V(ll * k, l * k, 1.0))
    apuntar(arm, 'Neck_alfred', V(p['neck_lado'], p['neck'], 1.0))
    apuntar(arm, 'RightUpArm_alfred', p['R']); apuntar(arm, 'Rightelbow_alfred', p['Rf'])
    apuntar(arm, 'LeftUpArm_alfred', p['L']); apuntar(arm, 'Leftelbow_alfred', p['Lf'])
    apuntar(arm, 'RightUpLeg_alfred', p['rl']); apuntar(arm, 'Rightknee_alfred', p['rs'])
    apuntar(arm, 'LeftUpLeg_alfred', p['ll']); apuntar(arm, 'Leftknee_alfred', p['ls'])
    for b in BONES_POSE:
        _key(arm, b, f)


def raiz(f, loc, yaw):
    arm, root = rig_alfred()
    root.location = loc; root.rotation_euler = (0, 0, math.radians(yaw))
    root.keyframe_insert('location', frame=f); root.keyframe_insert('rotation_euler', frame=f)


# -------------------------------------------------------------------------- poses nombradas
def p_idle(f, **k):
    pa(f, **k)


def p_listo(f, **k):       # hacha al hombro, mirando al arbol
    d = dict(R=V(0.3, 0.2, -0.6), Rf=V(0.1, 0.55, 0.75), L=V(-0.3, 0.3, -0.6), Lf=V(-0.1, 0.7, -0.5), lean=0.1, neck=0.0)
    d.update(k); pa(f, **d)


def p_armado(f, **k):      # hacha arriba y atras
    d = dict(R=V(0.35, -0.2, 0.9), Rf=V(0.15, -0.55, 0.85), L=V(-0.3, 0.2, 0.2), Lf=V(-0.1, 0.5, 0.4), lean=-0.15, hips_dz=0.0, neck=-0.1)
    d.update(k); pa(f, **d)


def p_golpe(f, **k):       # hacha abajo-adelante
    d = dict(R=V(0.25, 0.75, -0.35), Rf=V(0.05, 0.95, -0.4), L=V(-0.3, 0.6, -0.5), Lf=V(-0.1, 0.9, -0.3), lean=0.55, hips_dz=0.06, hips_dy=0.04, neck=0.2,
             rl=V(0, 0.35, -1), rs=V(0, -0.25, -1), ll=V(0, 0.15, -1), ls=V(0, -0.1, -1))
    d.update(k); pa(f, **d)


def p_cabeza_golpe(f, **k):  # recibe un golpe en la cabeza
    d = dict(R=V(0.5, 0.0, -0.8), Rf=V(0.6, 0.1, -0.7), L=V(-0.4, 0.45, 0.7), Lf=V(0.1, 0.6, 0.7), lean=-0.25, neck=-0.6, hips_dz=0.07,
             rl=V(0, 0.4, -1), rs=V(0, -0.3, -1), ll=V(0, 0.2, -1), ls=V(0, -0.2, -1))
    d.update(k); pa(f, **d)


def p_amenaza(f, vaiven=0.0, **k):   # puno izquierdo en alto, hacha en la derecha alzada
    d = dict(R=V(0.45, 0.25, 0.75), Rf=V(0.3, 0.2, 0.95), L=V(-0.35, 0.3, 0.9), Lf=V(-0.25 + vaiven, 0.35, 0.9), lean=0.15, neck=-0.45, hips_dz=0.0)
    d.update(k); pa(f, **d)


# -------------------------------------------------------------------------- movimientos
_WALK = {}


def _modulo_llano():
    """animacion de caminar POR DEFECTO de Alfred: `slot_1_caminar_llanura_animated.py` (Alfred camina por terreno llano), se importa para usar su configuracion y sus formulas"""
    if 'm' not in _WALK:
        import importlib.util
        spec = importlib.util.spec_from_file_location('alfred_caminar_llano', os.path.join(BIB, 'slot_1_caminar_llanura_animated.py'))
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        _WALK['m'] = m
    return _WALK['m']


def pose_caminar(arm, f, fase):
    """pose del ciclo de caminar por terreno llano en la fase 0..1 (mismas formulas que el script del usuario) y keyframe en f"""
    m = _modulo_llano(); cfg = m.ANIMATION_CONFIG; R = cfg['ranges']
    reset_pose(arm)
    P = arm.pose.bones
    for b in BONES_POSE:
        P[b].rotation_mode = 'XYZ'
    wc = fase % 1.0
    spine_fwd = math.sin(wc * 2 * math.pi + math.pi / 6) * R['spine_bend']
    spine_tilt = math.cos(wc * 2 * math.pi + math.pi / 3) * R['spine_bend'] * 0.75
    P['Spine_alfred'].rotation_euler = (spine_fwd, 0, spine_tilt)
    st = R['head_stabilization']
    P['Neck_alfred'].rotation_euler = (-spine_fwd * st, math.cos(wc * 2 * math.pi + math.pi / 4) * R['neck_tilt'] * 0.5, math.sin(wc * 2 * math.pi) * R['neck_tilt'])
    P['LeftUpLeg_alfred'].rotation_euler = (m.calculate_leg_swing(wc, cfg), 0, 0)
    P['Leftknee_alfred'].rotation_euler = (m.calculate_knee_flex(wc, cfg), 0, 0)
    rc = (wc + 0.5) % 1.0
    P['RightUpLeg_alfred'].rotation_euler = (m.calculate_leg_swing(rc, cfg), 0, 0)
    P['Rightknee_alfred'].rotation_euler = (m.calculate_knee_flex(rc, cfg), 0, 0)
    ra = (wc + 0.25) % 1.0
    P['RightUpArm_alfred'].location = (0.006604, 0.096746, -0.086079)
    P['RightUpArm_alfred'].rotation_euler = (R['arm_base_x'], m.calculate_arm_swing(ra, cfg), R['arm_base_z'])
    P['Rightelbow_alfred'].rotation_euler = (0, 0, -m.calculate_elbow_flex(ra, cfg))
    la = (wc + 0.75) % 1.0
    P['LeftUpArm_alfred'].location = (0.013552, 0.074613, -0.085881)
    P['LeftUpArm_alfred'].rotation_euler = (R['arm_base_x'], -m.calculate_arm_swing(la, cfg), R['arm_base_z'])
    P['Leftelbow_alfred'].rotation_euler = (0, 0, m.calculate_elbow_flex(la, cfg))
    for b in BONES_POSE:
        _key(arm, b, f)


def cuenta_pasos(dist):
    """frames para recorrer 'dist' m caminando (1 m por paso; medio ciclo = 12.375 f), redondeado a pasos completos"""
    m = _modulo_llano(); cfg = m.ANIMATION_CONFIG
    medio = cfg['frame_count'] / cfg['walk_cycles'] / 2.0
    return int(round(max(1, round(dist / cfg['step_distance'])) * medio)), medio


def validar_recorrido(pts):
    """reglas de la skill sistema-recorrido: cada paso mide exactamente 1 bloque (recto en X o Y, o diagonal ±1/±1) y la Z es igual (caminar); si no, es un salto"""
    for a, b in zip(pts, pts[1:]):
        dx, dy, dz = b.x - a.x, b.y - a.y, b.z - a.z
        recto = (abs(abs(dx) - 1) < 1e-6 and abs(dy) < 1e-6) or (abs(dx) < 1e-6 and abs(abs(dy) - 1) < 1e-6)
        diag = abs(abs(dx) - 1) < 1e-6 and abs(abs(dy) - 1) < 1e-6
        if not (recto or diag):
            raise ValueError('paso de recorrido invalido (debe ser de 1 bloque): %s -> %s' % (tuple(a), tuple(b)))
        if round(dz, 2) != 0:
            raise ValueError('cambio de Z en un tramo de caminar (usar saltar_subir / saltar_bajar): %s -> %s' % (tuple(a), tuple(b)))


def caminar_ruta(f0, pts, yaw_ini=None, yaw_fin=None):
    """camina por una cadena de puntos a 1 bloque (skill sistema-recorrido; el primer punto conserva sus decimales) con la animacion por defecto de Alfred (caminar por terreno llano);
    el root gira hacia cada tramo. Devuelve el frame final"""
    arm, root = rig_alfred()
    pts = [Vector(p) for p in pts]
    validar_recorrido(pts)
    legs = [(p, q, (q - p).length) for p, q in zip(pts, pts[1:])]
    total = sum(l[2] for l in legs)
    n, medio = cuenta_pasos(total)
    head = [math.degrees(math.atan2(q.y - p.y, q.x - p.x)) - 90 for p, q, _l in legs]
    yaw = head[0] if yaw_ini is None else yaw_ini
    for i in range(n + 1):
        s = total * i / n; k = 0
        while k < len(legs) - 1 and s > legs[k][2] + 1e-9:
            s -= legs[k][2]; k += 1
        p, q, L = legs[k]
        pos = p.lerp(q, min(1.0, s / L))
        objetivo = yaw_fin if (yaw_fin is not None and i > n - 14) else head[k]
        d = (objetivo - yaw + 180) % 360 - 180
        yaw += max(-20.0, min(20.0, d))
        raiz(f0 + i, pos, yaw)
        pose_caminar(arm, f0 + i, i / (2 * medio))
    return f0 + n


# Herramienta/arma en la MANO DERECHA (valores fijados por el usuario, 30 oct; aplican a cualquier herramienta o arma que Alfred lleve en la derecha): Child Of 'Mano' al hueso
# Rightelbow_alfred con esta transformacion local del objeto. La mano = extremo visible del antebrazo (la malla acaba en y=0.37 del hueso; la cola del hueso esta 0.33 mas alla).
HERR_MANO_DER = dict(loc=(0.21937, 0.32673, -0.001575), rot_deg=(7.9831, 17.876, -56.916), esc=0.82)
HACHA_LOC = Vector(HERR_MANO_DER['loc'])
HACHA_ROT = Euler([math.radians(d) for d in HERR_MANO_DER['rot_deg']], 'XYZ')
HACHA_ESC = HERR_MANO_DER['esc']
HACHA_MANO = Vector((0.04, 0.35, 0.0))                       # punto de la mano en el espacio del hueso Rightelbow_alfred
HACHA_AGARRE = Matrix.LocRotScale(HACHA_LOC, HACHA_ROT, Vector((HACHA_ESC,) * 3)).inverted() @ HACHA_MANO   # punto del mango (coords locales del sprite) que la mano sujeta en esa pose
_CFIX = {}
HACHAZOS = []                                                # (f0, pos, yaw, golpes, parcial, vel) de cada tala(); se resuelven al final con aplicar_hacha_talas()


def _cfix_hacha():
    """matriz que lleva la geometria del hacha de piedra a la del pico de piedra de `mineria_cueva3.blend` (los dos son items planos con el mango en diagonal y la cabeza arriba a la
    derecha; el eje del mango del hacha esta 8.3 grados mas girado y mide 1.038 contra 1.061). Medido con SVD de los vertices (centro, eje, extremos del mango).
    M_hacha = M_pico_mundo @ C"""
    if 'C' not in _CFIX:
        a = math.radians(45.0) - math.atan2(0.801, 0.598)
        s = 1.061 / 1.038
        base_hacha = Vector((0.025 - 0.598 * 0.612, 0.028 - 0.801 * 0.612, 0.0))
        base_pico = Vector((0.076 - 0.707 * 0.638, 0.014 - 0.707 * 0.638, 0.0))
        _CFIX['C'] = Matrix.Translation(base_pico) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Scale(s, 4) @ Matrix.Translation(-base_hacha)
    return _CFIX['C']


def aplicar_hacha_talas():
    """Al TALAR el hacha sigue el movimiento del pico del clip (cabeza al frente, mango hacia Alfred) y el punto del mango de la pose fija HERR_MANO_DER se lleva a la mano en cada
    fotograma; el resto del tiempo va en la mano con esos valores fijos (Child Of). Se llama cuando el brazo de Alfred ya esta completo."""
    sc = bpy.context.scene; arm, root = rig_alfred(); ax = bpy.data.objects['stone_axe']; c = ax.constraints['Mano']
    pbm = arm.pose.bones['Rightelbow_alfred']
    clip = cargar_clip('01_pica_el_bloque_de_hierro_cueva3_alfred.py')
    r = clip['objetos']['stone_pickaxe']
    R0 = mat(clip['root']['location'][0], clip['root']['rotation_euler'][0])
    C = _cfix_hacha()
    ax.rotation_mode = 'XYZ'
    def fija(fr):
        ax.location = HACHA_LOC; ax.rotation_euler = HACHA_ROT; ax.scale = (HACHA_ESC,) * 3
        for ch in ('location', 'rotation_euler', 'scale'):
            ax.keyframe_insert(ch, frame=fr)
    for (f0, pos, yaw, golpes, parcial, vel) in HACHAZOS:
        ultimo = 11 + 16 * golpes - 3 if parcial else 11 + 16 * (golpes - 1) + 4
        T = matriz(pos, yaw) @ R0.inverted()
        prev = Euler((0, 0, 0), 'XYZ')
        c.influence = 1.0; c.keyframe_insert('influence', frame=f0 - 1); fija(f0 - 1)
        c.influence = 0.0; c.keyframe_insert('influence', frame=f0)
        for i in range(0, ultimo + 1):
            fr = f0 + i / vel
            M = T @ Matrix.LocRotScale(Vector(r['location'][i]), Quaternion(r['rotation_quaternion'][i]), Vector(r['scale'][i])) @ C
            sc.frame_set(int(round(fr)))
            M = Matrix.Translation(arm.matrix_world @ pbm.matrix @ HACHA_MANO - M @ HACHA_AGARRE) @ M
            loc, qq, sc_ = M.decompose()
            eul = qq.to_euler('XYZ', prev); prev = eul
            ax.location = loc; ax.rotation_euler = eul; ax.scale = sc_
            for ch in ('location', 'rotation_euler', 'scale'):
                ax.keyframe_insert(ch, frame=fr)
        ff = int(round(f0 + ultimo / vel))
        c.influence = 0.0; c.keyframe_insert('influence', frame=ff)
        c.influence = 1.0; c.keyframe_insert('influence', frame=ff + 1); fija(ff + 1)


def _ultimos_valores(arm, clip, idx):
    for b in BONES_POSE:
        ch = clip['bones'].get(b)
        if ch and 'rotation_euler' in ch:
            _ULT[(arm.name, b)] = Euler(ch['rotation_euler'][idx], 'XYZ')


def tala(f0, pos, yaw, golpes=3, parcial=False, vel=1.0):
    """Alfred corta madera con la animacion `01_pica_el_bloque_de_hierro` (golpes en los frames 12, 28, 44, 60 del clip, uno cada 16 f) con el HACHA DE PIEDRA en lugar del pico.
    golpes = hachazos completos; parcial=True sigue con el siguiente hachazo hasta 3 f antes de pegar (para que algo lo interrumpa). Alfred se queda en pos mirando a yaw.
    Devuelve (frame_final, [frames de golpe])"""
    arm, root = rig_alfred()
    clip = cargar_clip('01_pica_el_bloque_de_hierro_cueva3_alfred.py')
    ultimo = 11 + 16 * (golpes - 1) + (4 if not parcial else 16 - 3)
    if parcial:
        ultimo = 11 + 16 * golpes - 3
    Ts = matriz(pos, yaw)
    ff, Mfin = poner_clip(arm, root, clip, f0, Ts, vel=vel, desde=0, hasta=ultimo)
    _ultimos_valores(arm, clip, ultimo)
    HACHAZOS.append((f0, Vector(pos), yaw, golpes, parcial, vel))   # el hacha de estos hachazos se anima al final (aplicar_hacha_talas)
    choques = [f0 + (11 + 16 * k) / vel for k in range(golpes)]
    return int(round(ff)), [int(round(c_)) for c_ in choques]


def amenazar(f0, dur=72, giros=3):
    for i in range(giros * 2 + 1):
        p_amenaza(f0 + i * dur / (giros * 2), vaiven=(0.35 if i % 2 else -0.15))
    return f0 + dur


# -------------------------------------------------------------------------- accion y reaccion: Alfred recibe un impacto
G_MS = 9.81
HOMES = {'A1': (-76.5, 37.5, 21.0), 'A2': (-88.5, 34.5, 21.0), 'A3': (-73.5, 20.5, 18.0), 'A4': (-88.5, 36.5, 23.0), 'A5': (-74.5, 36.5, 18.0), 'A7': (-71.5, 19.5, 20.0)}
MASA_OBJ = {'manzana': 0.25, 'palo': 0.40, 'panal': 0.60, 'baya': 0.08, 'cacao': 0.15, 'serpiente': 0.35}
D_LISTO = dict(R=V(0.3, 0.2, -0.6), Rf=V(0.1, 0.55, 0.75), L=V(-0.3, 0.3, -0.6), Lf=V(-0.1, 0.7, -0.5), lean=0.1, neck=0.0)
D_CAB = dict(R=V(0.5, 0.0, -0.8), Rf=V(0.6, 0.1, -0.7), L=V(-0.4, 0.45, 0.7), Lf=V(0.1, 0.6, 0.7), lean=-0.25, neck=-0.6, hips_dz=0.07,
             rl=V(0, 0.4, -1), rs=V(0, -0.3, -1), ll=V(0, 0.2, -1), ls=V(0, -0.2, -1))
D_HOM = dict(R=V(0.6, -0.1, -0.7), Rf=V(0.5, 0.2, -0.8), L=V(-0.4, 0.4, 0.5), Lf=V(0.2, 0.6, 0.5), lean=0.05, lean_lado=-0.35, neck=0.1, neck_lado=-0.4, hips_dz=0.05)
D_BRAZO = dict(R=V(0.45, 0.2, -0.8), Rf=V(0.3, 0.55, 0.6), L=V(-0.2, 0.55, 0.15), Lf=V(-0.1, 0.4, 0.9), lean=0.15, neck=0.1, hips_dz=0.03)
_PERFIL = [(0.0, 0.45), (0.08, 1.0), (0.2, 0.8), (0.38, 0.35), (0.55, -0.18), (0.75, 0.06), (1.0, 0.0)]   # (fraccion de la duracion, factor): golpe instantaneo, pico, rebote elastico y vuelta


def velocidad_golpe(origen, destino, n_frames):
    """velocidad (m/s) con la que llega un objeto lanzado de 'origen' a 'destino' en n_frames con gravedad real"""
    T = n_frames / 24.0
    v = (Vector(destino) - Vector(origen)) / T
    v.z -= 0.5 * G_MS * T
    return v


def golpe(lanzador, pos, z, f_imp, T):
    """velocidad (m/s) con la que llega al personaje en 'pos' (altura z) el objeto que lanza el bonobo 'lanzador' desde su copa, T frames antes del impacto"""
    return velocidad_golpe(Vector(HOMES[lanzador]) + V(0, 0, 1.4), V(pos[0], pos[1], z), T)


def reaccion(fi, v, masa, yaw, pos, peak, fin, dur, brazo=None):
    """Alfred reacciona AL INSTANTE del impacto en fi segun el momento del objeto (masa * velocidad): la cabeza y el torso se van en la direccion que llevaba el objeto,
    las rodillas ceden si viene de arriba, el cuerpo se desliza un poco y luego rebota en sentido contrario (inercia) hasta recuperar 'fin' a los 'dur' frames.
    v = velocidad del objeto en mundo (m/s); peak/fin = diccionarios de pose (D_*)"""
    v = Vector(v)
    s = max(0.35, min(1.4, masa * v.length / 3.0))             # intensidad por cantidad de movimiento (manzana ~1.0)
    u = v.normalized()
    th = math.radians(yaw)
    xl = Vector((math.cos(th), math.sin(th), 0)); yl = Vector((-math.sin(th), math.cos(th), 0))
    ux, uy, uz = u.dot(xl), u.dot(yl), u.z                      # direccion del impacto en el espacio del personaje
    hz = Vector((u.x, u.y, 0)); hz = hz.normalized() if hz.length > 1e-6 else Vector((0, 0, 0))
    ya = {}
    for fr, k in _PERFIL:
        f = int(round(fi + fr * dur))
        if f in ya:
            continue
        ya[f] = k
    for f, k in sorted(ya.items()):
        kp = max(k, 0.0)
        d = {}
        for key in set(fin) | set(peak):
            a = fin.get(key, BASE.get(key)); b = peak.get(key, a)
            d[key] = a + (b - a) * kp
        d['lean'] = fin.get('lean', 0.0) + 0.55 * s * uy * k
        d['lean_lado'] = fin.get('lean_lado', 0.0) + 0.45 * s * ux * k
        d['neck'] = fin.get('neck', 0.0) + (1.0 * s * uy - 0.55 * s * uz) * k
        d['neck_lado'] = fin.get('neck_lado', 0.0) + 0.8 * s * ux * k
        d['hips_dz'] = fin.get('hips_dz', 0.0) + (0.10 * s * max(0.0, -uz)) * kp
        if brazo:                                              # el brazo golpeado se va en la direccion del impacto
            d[brazo] = d[brazo] + V(ux, uy, uz) * (0.55 * s * k)
        pa(f, **d)
        push = hz * (0.12 * s * k)
        raiz(f, Vector(pos) + push, yaw + 7.0 * s * ux * k)


def gesto_molesto(f0, pos, yaw):
    """animacion del usuario 'gesto con el brazo derecho' (molesto: agita el brazo enojado y lo sube mirando arriba), 38 f desde el indice 2 (los 2 primeros mezclaban con la escena de origen);
    devuelve el frame donde ya esta de vuelta en p_listo en 'pos'"""
    arm, root = rig_alfred()
    clip = cargar_clip('05_gesto_con_el_brazo_derecho_cueva3_alfred.py')
    p_amenaza(f0 - 1, vaiven=-0.15)                               # entra desde la amenaza
    for b in BONES_POSE:                                          # frame previo clavado para que no mezcle con la pose anterior
        _ULT.pop((arm.name, b), None)
    ff, _M = poner_clip(arm, root, clip, f0, Ts=matriz(pos, yaw), desde=2, solo=BONES_POSE)
    for b in BONES_POSE:
        pb = arm.pose.bones[b]; _ULT[(arm.name, b)] = pb.rotation_euler.copy()
    raiz(ff + 8, pos, yaw)
    p_listo(ff + 8)
    return int(ff) + 12


def construir_alfred_parte1():
    """idle -> camina al arbol 1 -> 3 hachazos -> manzana en la cabeza (f268) -> se sacude -> amenaza al bonobo"""
    arm, root = rig_alfred()
    for ob in (arm, root):
        ob.animation_data_create(); ob.animation_data.action = None
    for ob, nom in ((arm, 'Alfred_bonobos_huesos'), (root, 'Alfred_bonobos_root')):
        accion_nueva(ob, nom)
    _ULT.clear()
    A0 = V(-74.63, 32.5, 12.0); C1 = A0 + V(-3, 0, 0)
    # --- idle mirando los arboles
    raiz(1, A0, 85)
    p_idle(1)
    p_idle(24, neck=-0.25, lean=-0.03)                 # mira las copas
    p_idle(48, neck=-0.25, lean=-0.03, R=V(0.15, 0.0, -1))
    p_idle(66, neck=0.0)
    # --- camina al primer arbol
    f = caminar_ruta(72, [A0, A0 + V(-1, 0, 0), A0 + V(-2, 0, 0), C1], yaw_ini=85, yaw_fin=90)
    raiz(f + 6, C1, 90)
    G['tala1_ini'] = f + 6
    f2, ch = tala(f + 6, C1, 90, golpes=3, parcial=True)   # 3 hachazos y el 4o interrumpido por la manzana
    G['choques1'] = ch
    G['manzana_impacto'] = f2 + 2
    G['manzana_suelta'] = G['manzana_impacto'] - 22
    fi = G['manzana_impacto']
    reaccion(fi, golpe('A1', C1, 13.8, fi, 22), MASA_OBJ['manzana'], 90, C1, D_CAB, dict(D_CAB, neck=-0.3, lean=-0.2), 24)
    # --- mira al bonobo y lo amenaza
    raiz(fi + 24, C1, 90)
    raiz(fi + 40, C1, 112)                                # se gira hacia la copa del bonobo
    p_amenaza(fi + 40, vaiven=-0.15)
    f = amenazar(fi + 40, dur=72, giros=3)
    G['amenaza1_fin'] = f
    raiz(f, C1, 112)
    p_listo(f + 14)
    G['fin1'] = f + 14
    return f + 14


# -------------------------------------------------------------------------- poses nuevas
def p_hombro(f, **k):        # golpe en el hombro derecho: se tuerce hacia el lado
    d = dict(R=V(0.6, -0.1, -0.7), Rf=V(0.5, 0.2, -0.8), L=V(-0.4, 0.4, 0.5), Lf=V(0.2, 0.6, 0.5), lean=0.05, lean_lado=-0.35, neck=0.1, neck_lado=-0.4, hips_dz=0.05)
    d.update(k); pa(f, **d)


def p_agachado(f, **k):      # agachado a recoger del suelo
    d = dict(R=V(0.45, 0.2, -0.8), Rf=V(0.3, 0.55, 0.6), L=V(-0.2, 0.5, -0.8), Lf=V(-0.1, 0.55, -0.9), lean=1.0, hips_dz=0.30, hips_dy=0.10, neck=0.5,
             rl=V(0, 0.9, -0.5), rs=V(0, -0.7, -0.75), ll=V(0, 0.9, -0.5), ls=V(0, -0.7, -0.75))
    d.update(k); pa(f, **d)


def p_lanza_prep(f, **k):    # brazo izquierdo atras (lanzar un objeto)
    d = dict(R=V(0.45, 0.2, -0.8), Rf=V(0.3, 0.55, 0.6), L=V(-0.4, -0.75, 0.45), Lf=V(-0.3, -0.95, 0.25), lean=-0.25, neck=-0.2, hips_dz=0.04, lean_lado=0.0,
             rl=V(0, 0.2, -1), rs=V(0, -0.2, -1), ll=V(0, 0.5, -1), ls=V(0, -0.3, -1))
    d.update(k); pa(f, **d)


def p_lanza_suelta(f, **k):
    d = dict(R=V(0.45, 0.2, -0.8), Rf=V(0.3, 0.55, 0.6), L=V(-0.2, 0.75, 0.55), Lf=V(-0.1, 0.95, 0.3), lean=0.35, neck=-0.25, hips_dz=0.07,
             rl=V(0, 0.2, -1), rs=V(0, -0.2, -1), ll=V(0, 0.55, -1), ls=V(0, -0.45, -1))
    d.update(k); pa(f, **d)


def p_lanza_sigue(f, **k):
    d = dict(R=V(0.45, 0.2, -0.8), Rf=V(0.3, 0.55, 0.6), L=V(-0.25, 0.65, -0.55), Lf=V(-0.1, 0.8, -0.6), lean=0.5, neck=-0.1, hips_dz=0.05)
    d.update(k); pa(f, **d)


def p_mira_brazo(f, **k):    # mira el brazo izquierdo (serpiente clavada)
    d = dict(R=V(0.45, 0.2, -0.8), Rf=V(0.3, 0.55, 0.6), L=V(-0.2, 0.55, 0.15), Lf=V(-0.05, 0.35, 0.9), lean=0.3, neck=0.55, hips_dz=0.04)
    d.update(k); pa(f, **d)


def p_puno(f, vaiven=0.0, **k):   # puno derecho en alto (sin hacha) y brazo izquierdo colgando con la serpiente
    d = dict(R=V(0.3, 0.35, 0.9), Rf=V(0.2 + vaiven, 0.3, 1.0), L=V(-0.3, 0.2, -0.9), Lf=V(-0.2, 0.3, -0.9), lean=0.15, neck=-0.4)
    d.update(k); pa(f, **d)


def p_mareo(f, t=0.0, **k):       # tambaleo: t en 0..1 aumenta el desequilibrio y la caida
    d = dict(R=V(0.5, 0.0, -0.8), Rf=V(0.4, 0.3, -0.8), L=V(-0.3, 0.1, -0.9), Lf=V(-0.2, 0.3, -0.9), lean=0.1 + 0.5 * t, lean_lado=0.25 * t, neck=0.2 + 0.5 * t, neck_lado=0.3 * t,
             hips_dz=0.05 + 0.45 * t, rl=V(0, 0.3 + 0.7 * t, -1 + 0.4 * t), rs=V(0, -0.2 - 0.5 * t, -1 + 0.3 * t), ll=V(0, 0.3 + 0.7 * t, -1 + 0.4 * t), ls=V(0, -0.2 - 0.5 * t, -1 + 0.3 * t))
    d.update(k); pa(f, **d)


def p_tumbado(f, **k):            # tumbado de lado (el root gira aparte)
    d = dict(R=V(0.2, 0.6, -0.5), Rf=V(0.0, 0.7, -0.4), L=V(-0.2, 0.3, -0.9), Lf=V(-0.1, 0.5, -0.8), lean=0.0, neck=0.1, hips_dz=0.0,
             rl=V(0, 0.5, -0.9), rs=V(0, -0.6, -0.8), ll=V(0, 0.3, -1), ls=V(0, -0.2, -1))
    d.update(k); pa(f, **d)


def raiz_matriz(f, M):
    """root con una matriz completa (para tumbarse)"""
    arm, root = rig_alfred()
    loc, q, _s = M.decompose()
    root.location = loc
    root.rotation_euler = q.to_euler('XYZ', Euler(tuple(root.rotation_euler), 'XYZ'))
    root.keyframe_insert('location', frame=f); root.keyframe_insert('rotation_euler', frame=f)


def yaw_a(desde, hacia):
    return math.degrees(math.atan2(hacia[1] - desde[1], hacia[0] - desde[0])) - 90


_LZ = {}


def _clip_lanzar():
    """clip del usuario 'Alfred lanza un objeto' (slot_001_lanzar_objeto_1, Mixamo, 2 ciclos de 53 f; lanza con el brazo DERECHO) espejado para lanzar con el IZQUIERDO"""
    if 'c' not in _LZ:
        c = cargar_clip('slot_001_lanzar_objeto_1.py')
        esp = {}
        for b, ch in c['bones'].items():
            nb = b.replace('Left', '@').replace('Right', 'Left').replace('@', 'Right')
            esp[nb] = {'rotation_euler': [[v[0], -v[1], -v[2]] for v in ch['rotation_euler']]}
        _LZ['c'] = esp
    return _LZ['c']


def _poner_clip_lanzar(arm, i):
    """pose del clip espejado en el frame i (0-based, fraccionario) sin keyframe"""
    esp = _clip_lanzar()
    i0 = int(math.floor(i)); t = i - i0; i1 = min(i0 + 1, 105)
    reset_pose(arm)
    for b, ch in esp.items():
        pb = arm.pose.bones.get(b)
        if pb is None or b not in BONES_POSE and b != 'face_alfred':
            continue
        a, c_ = ch['rotation_euler'][i0], ch['rotation_euler'][i1]
        pb.rotation_euler = [a[k] + (c_[k] - a[k]) * t for k in range(3)]
    bpy.context.view_layer.update()


def _mirar(arm, objetivo_arm, w):
    """gira cuello y cara hacia el objetivo (punto en espacio del armature) con peso w (0 clip, 1 mirando); sobre la pose ya puesta"""
    if w <= 0:
        return
    up = Vector((0, 0, 1))
    for hueso, k in (('Neck_alfred', 0.55), ('face_alfred', 0.9)):
        pb = arm.pose.bones[hueso]
        bpy.context.view_layer.update()
        M = pb.matrix.copy()
        dc = (M.to_quaternion() @ Vector((0, 1, 0))).normalized()
        u = (Vector(objetivo_arm) - M.translation).normalized()
        dt = (up + u * k).normalized()
        apuntar(arm, hueso, (dc * (1 - w) + dt * w).normalized())


I_ENT, I_SUELTA, I_FIN = 12, 46, 52          # indices 0-based del clip: mano delante con el objeto / suelta / vuelta al inicio
VEL_LZ = 1.2


def lanzar_clip(f0, pos, yaw, objetivo, dur_agacha=18):
    """Alfred en 'pos' (de pie en f0): se agacha a recoger (grab), se incorpora girando hacia 'objetivo' (punto de mundo del mono), apunta mirandolo y lanza con el clip del usuario.
    La mirada (cuello y cara) sigue al mono. Devuelve dict(grab, soltar, fin)."""
    arm, root = rig_alfred()
    pos = Vector(pos); objetivo = Vector(objetivo)
    raiz(f0, pos, yaw)
    p_listo(f0)
    p_agachado(f0 + 12)
    p_agachado(f0 + dur_agacha)
    grab = f0 + dur_agacha
    # yaw del root para que el brazo de lanzar apunte al mono (direccion en espacio del armature a la suelta)
    _poner_clip_lanzar(arm, I_SUELTA + 1)
    sh = arm.pose.bones['LeftUpArm_alfred'].head; ma = arm.pose.bones['Leftelbow_alfred'].tail
    Rel = root.matrix_world.inverted() @ arm.matrix_world             # armature respecto al root
    v = Rel.to_3x3() @ (ma - sh)
    phi = math.degrees(math.atan2(v.y, v.x))
    az = math.degrees(math.atan2(objetivo.y - pos.y, objetivo.x - pos.x))
    yaw_t = az - phi
    while yaw_t - yaw > 180: yaw_t -= 360
    while yaw_t - yaw < -180: yaw_t += 360
    Mr = matriz(pos, yaw_t) @ Rel                                      # armature en mundo con el yaw final
    obj_arm = Mr.inverted() @ objetivo
    fc = grab + 12                                          # la pose de entrada del clip se alcanza al incorporarse
    raiz(grab + 3, pos, yaw)
    raiz(fc, pos, yaw_t)
    n = int(round((I_FIN - I_ENT) / VEL_LZ))
    for k in range(n + 1):
        f = fc + k
        i = I_ENT + k * VEL_LZ
        _poner_clip_lanzar(arm, min(i, I_FIN))
        w = 1.0 if i < I_SUELTA + 6 else max(0.0, 1.0 - (i - I_SUELTA - 6) / 6.0)
        _mirar(arm, obj_arm, w if k > 0 else 0.6)
        for b in BONES_POSE:
            _key(arm, b, f)
    rel = fc + int(round((I_SUELTA - I_ENT) / VEL_LZ))
    fin = fc + n
    raiz(fin, pos, yaw_t)
    p_listo(fin + 14)
    raiz(fin + 14, pos, yaw_t)
    return dict(grab=grab, soltar=rel, fin=fin + 14)


def agacharse_y_lanzar(f0, pos, yaw, yaw_tiro, f_prep=None, dur_agacha=18, objetivo=None):
    """camino ya hecho; desde f0 (de pie en 'pos'): se agacha (f0..f0+dur), recoge (grab=f0+dur), se incorpora y lanza con el brazo izquierdo. Devuelve dict de frames.
    Con 'objetivo' (punto de mundo del mono) usa el clip del usuario con mirada al mono"""
    if objetivo is not None:
        return lanzar_clip(f0, pos, yaw, objetivo, dur_agacha)
    raiz(f0, pos, yaw)
    p_listo(f0)
    p_agachado(f0 + 12)
    p_agachado(f0 + dur_agacha)
    grab = f0 + dur_agacha
    p_lanza_prep(f0 + dur_agacha + 14, )
    raiz(f0 + dur_agacha + 8, pos, yaw)
    raiz(f0 + dur_agacha + 18, pos, yaw_tiro)
    p_lanza_prep(f0 + dur_agacha + 20)
    rel = f0 + dur_agacha + 30
    p_lanza_suelta(rel)
    raiz(rel, pos, yaw_tiro)
    p_lanza_sigue(rel + 8)
    raiz(rel + 8, pos, yaw_tiro)
    p_listo(rel + 24)
    raiz(rel + 24, pos, yaw_tiro)
    return dict(grab=grab, soltar=rel, fin=rel + 24)


def construir_alfred_resto():
    """desde G['fin1']: palos, silex, panal, rata, pollo, bayas, serpiente, puno y desmayo"""
    arm, root = rig_alfred()
    C1 = V(-77.63, 32.5, 12.0)
    f = G['fin1']
    # ---------------- 2o arbol de golpes con palos
    raiz(f, C1, 112)
    raiz(f + 6, C1, 90)
    p_listo(f + 6)
    f2, ch = tala(f + 6, C1, 90, golpes=1, parcial=True)  # un hachazo y el siguiente interrumpido por el palo
    G['choques2'] = ch
    G['palo1_imp'] = f2 + 2                               # le da en el hombro con el hacha arriba
    G['palo1_rel'] = G['palo1_imp'] - 22
    G['palo2_imp'] = G['palo1_imp'] + 10                  # el 2o palo pasa de largo
    G['palo2_rel'] = G['palo2_imp'] - 22
    reaccion(G['palo1_imp'], golpe('A2', C1, 13.3, 0, 22), MASA_OBJ['palo'], 90, C1, D_HOM, dict(D_LISTO, neck=-0.4), 28)
    f = G['palo1_imp'] + 30
    # ---------------- molesto: amenaza corta
    raiz(f, C1, 90); raiz(f + 14, C1, 106)
    f = gesto_molesto(f + 14, C1, 106)
    # ---------------- recoge el pedernal y se lo lanza al bonobo A1
    FL = C1 + V(1, 0, 0)
    raiz(f, C1, 106)
    f = caminar_ruta(f, [C1, FL], yaw_ini=106, yaw_fin=190 - 90 + 12)
    G['silex_ini'] = f
    r = agacharse_y_lanzar(f, FL, 112, 0, objetivo=V(-76.5, 37.5, 21.5))   # pedernal -> A1
    G['silex_grab'] = r['grab']; G['silex_rel'] = r['soltar']; G['pos_silex'] = FL
    f = r['fin']
    # ---------------- vuelve al arbol y sigue talando (panal en la cabeza)
    raiz(f, FL, 100)
    f = caminar_ruta(f + 4, [FL, C1], yaw_ini=100, yaw_fin=90)
    raiz(f + 4, C1, 90)
    f3, ch = tala(f + 4, C1, 90, golpes=1, parcial=True)
    G['choques3'] = ch
    G['panal_imp'] = f3 + 2
    G['panal_rel'] = G['panal_imp'] - 24
    reaccion(G['panal_imp'], golpe('A5', C1, 13.8, 0, 24), MASA_OBJ['panal'], 90, C1, D_CAB, dict(D_LISTO, neck=-0.3), 34)
    f = G['panal_imp'] + 34
    # ---------------- segundo objeto (cacao) falla; mira
    G['cacao_imp'] = f - 6
    G['cacao_rel'] = G['cacao_imp'] - 22
    p_listo(f + 12, neck=-0.1)
    raiz(f + 12, C1, 90)
    # ---------------- espera a la rata
    G['rata_llega'] = max(f + 30, 744)
    f = G['rata_llega']
    p_idle(f - 10, neck=0.3, lean=0.05)
    p_listo(f)
    raiz(f, C1, 90)
    RAT = V(-75.9, 31.3, 12.0)
    raiz(f + 6, C1, 90)
    f = caminar_ruta(f + 6, [C1, C1 + V(1, 0, 0)], yaw_ini=90, yaw_fin=-35 + 0)
    r = agacharse_y_lanzar(f, (C1 + V(1, 0, 0)), -35, 0, dur_agacha=18, objetivo=V(-73.5, 20.5, 18.5))   # rata -> A3
    G['rata_grab'] = r['grab']; G['rata_rel'] = r['soltar']; G['pos_rata_mano'] = (C1 + V(1, 0, 0))
    f = r['fin']
    # ---------------- el pollo
    G['pollo_llega'] = max(f + 10, 834)
    f = G['pollo_llega']
    p_listo(f - 10, neck=-0.1)
    r = agacharse_y_lanzar(f, (C1 + V(1, 0, 0)), yaw_a((C1.x + 1, C1.y), (C1.x + 2.4, C1.y + 0.9)), 0, dur_agacha=18, objetivo=V(-74.5, 36.5, 18.5))   # pollo -> A5
    G['pollo_grab'] = r['grab']; G['pollo_rel'] = r['soltar']
    f = r['fin']
    # ---------------- va al arbol 2 y tala
    RS = C1 + V(1, 0, 0); C2 = RS + V(1, -3, 0)                         # 3 pasos de 1 bloque: diagonal + 2 rectos; hachazos a la cara este del tronco 2
    f = caminar_ruta(f + 4, [RS, RS + V(1, -1, 0), RS + V(1, -2, 0), C2], yaw_fin=90)
    raiz(f + 4, C2, 90)
    f4, ch = tala(f + 4, C2, 90, golpes=2, parcial=True)
    G['choques4'] = ch
    G['baya_imp'] = f4 + 2
    G['baya2_imp'] = G['baya_imp'] + 26
    reaccion(G['baya_imp'], golpe('A2', C2, 13.8, 0, 24), MASA_OBJ['baya'], 90, C2, D_CAB, dict(D_LISTO, neck=-0.3), 26)
    reaccion(G['baya2_imp'], golpe('A4', C2, 13.3, 0, 24), MASA_OBJ['baya'], 90, C2, D_HOM, dict(D_LISTO, neck=-0.2), 18)
    f = G['baya2_imp'] + 18
    raiz(f, C2, 90); raiz(f + 16, C2, 118)
    # ---------------- gran amenaza antes de la serpiente
    for i in range(7):
        p_amenaza(f + 16 + i * 9, vaiven=(0.4 if i % 2 else -0.2))
    f = f + 16 + 6 * 9 + 8
    G['serpiente_imp'] = f + 40
    G['serpiente_rel'] = G['serpiente_imp'] - 24
    p_listo(f)
    p_armado(f + 18)
    p_listo(f + 34, L=V(-0.25, 0.55, 0.15), Lf=V(-0.1, 0.4, 0.9))   # el brazo izquierdo sube justo cuando llega
    fi = G['serpiente_imp']
    p_listo(fi - 2, L=V(-0.25, 0.55, 0.15), Lf=V(-0.1, 0.4, 0.9))
    reaccion(fi, golpe('A7', C2, 13.2, 0, 24), MASA_OBJ['serpiente'], 118, C2, D_BRAZO, dict(D_BRAZO, neck=0.55, lean=0.3, hips_dz=0.04, L=V(-0.2, 0.55, 0.15), Lf=V(-0.05, 0.35, 0.9)), 6, brazo='L')
    for f_ in range(fi + 8, fi + 28, 2):                  # sacude el brazo con la serpiente colgando: oscilacion amortiguada (inercia del brazo y del cuerpo)
        tt = f_ - (fi + 6); aa = math.exp(-tt / 7.0); ww = 2 * math.pi / 9
        p_mira_brazo(f_, L=V(-0.2 + 0.35 * aa * math.sin(ww * tt), 0.55 + 0.25 * aa * math.cos(ww * tt), 0.15 + 0.3 * aa * math.sin(ww * tt + 1.2)),
                     Lf=V(-0.05 + 0.3 * aa * math.sin(ww * tt + 0.5), 0.35, 0.9 - 0.4 * aa * (1 + math.sin(ww * tt)) / 2), lean=0.3 + 0.12 * aa * math.sin(ww * tt), neck=0.55 + 0.1 * aa * math.cos(ww * tt))
    p_mira_brazo(fi + 28, lean=0.4, neck=0.7)
    # suelta el hacha y levanta el puno
    G['hacha_cae'] = fi + 34
    p_puno(fi + 44)
    for i in range(5):
        p_puno(fi + 44 + i * 14, vaiven=(0.5 if i % 2 else -0.2), lean_lado=0.05 * (i + 1) * (1 if i % 2 else -1), hips_dz=0.02 * i)
    f = fi + 44 + 4 * 14
    G['mareo_ini'] = f
    N = 6
    for i in range(N + 1):
        p_mareo(f + i * 14, t=0.3 + 0.7 * i / N, vaiven=0)
    f = f + N * 14
    G['rodillas'] = f
    # cae de lado
    yaw = 118
    raiz_matriz(f, matriz(C2, yaw))
    p_mareo(f, t=1.0)
    M2 = matriz(C2 + V(0, 0, 0.30), yaw) @ Matrix.Rotation(math.radians(90), 4, 'Y')
    p_tumbado(f + 14, hips_dz=0.3)
    p_tumbado(f + 28)

    def _cae(ff, ang):                                 # el cuerpo cae ACELERADO (angulo ~ t^2) y rebota al tocar el suelo
        raiz_matriz(ff, matriz(C2 + V(0, 0, 0.30 * (ang / 90.0) ** 1.3), yaw) @ Matrix.Rotation(math.radians(ang), 4, 'Y'))
    for i_ in range(0, 25, 2):
        _cae(f + i_, 90 * (i_ / 24.0) ** 2)
    _cae(f + 24, 90); _cae(f + 27, 83); _cae(f + 30, 90); _cae(f + 33, 87.5); _cae(f + 36, 90)
    raiz_matriz(f + 80, M2)
    p_tumbado(f + 80, R=V(0.2, 0.6, -0.5))
    G['fin'] = f + 80
    import json
    bpy.context.scene['bm_G'] = json.dumps({k: (list(v) if hasattr(v, '__len__') and not isinstance(v, (list, tuple)) else v) for k, v in G.items()})
    return f + 80


if __name__ == '__main__':
    pass
