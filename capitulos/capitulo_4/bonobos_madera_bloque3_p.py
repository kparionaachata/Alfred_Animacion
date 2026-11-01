# -*- coding: utf-8 -*-
"""Bloque 3 (version P): Alfred se desplaza a la zona desde donde ve bien a los bonobos, (-72.5, 32.5, 12), y alli recibe los palos, cae sentado, devuelve palos, agarra el pollo,
recibe pollo y rata, se levanta y vuelve caminando a RS (-76.63, 32.5) para empalmar con el frame 854.
Uso (escena viva):  exec(open(este_archivo).read());  desbloquear_monos(); etapa_A(); base_monos(); reposo_monos(); etapa_B2(); etapa_C2(); etapa_D2(); etapa_E2(); etapa_F2(); cierre(); rebloquear_monos()"""
exec(open(r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\bonobos_madera_bloque3.py", encoding='utf8').read())

C0 = C1.copy()                                   # donde esta Alfred en el frame 534
PH = Vector((-72.5, 32.5, 12.0))                 # punto de vision de los bonobos (el otro valido: (-72.5, 30.5, 12.0))
C1 = PH.copy()                                   # las funciones de las etapas B-F usan C1 como el sitio donde recibe los golpes
CARA = PH + Vector((-0.07, 0.0, 1.6))
T_VUELO = 14
HITS = [('A2', 586, 'l', (PH.x + 1.53, PH.y - 0.9)), ('A4', 596, 'r', (PH.x + 1.73, PH.y + 0.6)), ('A6', 606, 'l', (PH.x + 1.33, PH.y - 0.1))]
F_SIT = 628
F_TOOLS = 642
DEVUELVE = [(654, 661, 'A2'), (663, 670, 'A4')]
F_CH0 = 695
F_A2_SUELTA = 732
RAT_REL = 741
F_UP = 765
F_CH_IMP = F_A2_SUELTA + T_VUELO
F_RAT_IMP = RAT_REL + T_VUELO
F_REPOSO1, F_REPOSO2 = 728, 742


def etapa_B2():
    arm, root = rig_alfred(); B = base_monos()
    sembrar_ult()
    palos = [clon_palo(n) for n in PALOS]
    for p in palos:
        quitar_todo(p)
    # 1) camina de donde esta a la zona de vision (la 1a zancada mide 1.13 por llegar justo a las coordenadas pedidas)
    global validar_recorrido
    _v = validar_recorrido; validar_recorrido = lambda p: None
    ruta = [(C0.x, C0.y, C0.z)] + [(-76.5 + i, 32.5, 12.0) for i in range(5)]
    fin = caminar_ruta(F0, ruta, yaw_ini=YAW, yaw_fin=YAW)
    validar_recorrido = _v
    quitar(arm, F0, F0 + 2)                                                    # el arranque se funde desde la pose de pie del 534
    for b in BONES_POSE:
        _ULT[(arm.name, b)] = arm.pose.bones[b].rotation_euler.copy()
    # 2) los bonobos lanzan, Alfred reacciona
    for nm, fr, lado, _ in HITS:
        tira(nm, fr, CARA, lado)
    for i, (nm, fr, lado, _) in enumerate(HITS):
        fi = fr + T_VUELO
        v = velocidad_golpe(mano_mono(B[nm], fr, lado), CARA, T_VUELO)
        p_listo(fi - 3); raiz(fi - 3, C1, YAW)
        reaccion(fi, v, MASA_OBJ['palo'], YAW, C1, D_CAB, D_LISTO, 12 if i < 2 else 6)
    # 3) cae sentado
    clip = cargar_clip('sentarse_alfred.py')
    ff, _M = poner_clip(arm, root, clip, F_SIT, Ts=matriz(C1, YAW), vel=2.0, desde=30, hasta=56, solo=BONES_POSE)
    for b in BONES_POSE:
        _ULT[(arm.name, b)] = arm.pose.bones[b].rotation_euler.copy()
    G['sentado'] = ff
    for (nm, fr, lado, land), palo in zip(HITS, palos):
        fi = fr + T_VUELO
        vuela_a_alfred(palo, fr, nm, lado, fi, 'face_alfred', aterriza=Vector((land[0], land[1], SUELO + 0.15)))
        ocultar_hasta(palo, fr)
    return dict(caminar_fin=fin, sentado=ff)


def etapa_C2():
    arm, root = rig_alfred(); B = monos()
    palos = [bpy.data.objects[n] for n in PALOS]
    clip = cargar_clip('sentado_tirar_herramientas_alfred.py')
    raiz(int(G['sentado']) + 2, C1, YAW)
    ff, _M = poner_clip(arm, root, clip, F_TOOLS, vel=2.0, desde=62, hasta=120, solo=BONES_POSE, mover_root=False)
    raiz(F_TOOLS, C1, YAW); raiz(int(ff), C1, YAW)
    for b in BONES_POSE:
        _ULT[(arm.name, b)] = arm.pose.bones[b].rotation_euler.copy()
    G['tools_fin'] = ff
    info = {}
    for (fg, fr, nm), palo, (_n, f_rel0, lado, land) in zip(DEVUELVE, palos, HITS):
        hueso, p_agarra = mano_agarra(fg)
        suelo_p = Vector((p_agarra.x, p_agarra.y, SUELO + 0.15))
        quitar_todo(palo)
        vuela_a_alfred(palo, f_rel0, _n, lado, f_rel0 + T_VUELO, 'face_alfred', aterriza=suelo_p)
        for f in range(fg, fr + 1):
            palo.location = hueso_alfred(f, hueso, cola=True)
            palo.keyframe_insert('location', frame=f)
        b = B[nm]
        mano = hueso_alfred(fr, hueso, cola=True)
        bpy.context.scene.frame_set(fr + T_VUELO)
        centro = hueso_mundo(b, 'cube_r1', cola=False)
        vuelo(palo, fr, mano, fr + T_VUELO, centro, suelo=SUELO + 0.15, centro=centro)
        info[nm] = (hueso, fg, fr, fr + T_VUELO)
    return info


# ------------------------------------------------------------------------------------------------ etapa C3: sentado, lanza los palos con la animacion de lanzar (solo la mitad superior)
LANZAR_VEL = 2.0
LANZAR_F0 = [642, 668]                       # inicio (indice 0) de cada lanzamiento; suelta en el indice 46 (frame f0 + 23), grab en el indice 2
TH = [('bm_stick_3', 'A2', 586, 'l', 'R'), ('bm_stick_4', 'A4', 596, 'r', 'L')]
_SENT = {}


def _clip_lanzar_lado(lado):
    """clip del usuario 'Alfred lanza un objeto' (brazo DERECHO); para 'L' se espeja (brazo izquierdo)"""
    c = cargar_clip('slot_001_lanzar_objeto_1.py')
    if lado == 'R':
        return {b: ch['rotation_euler'] for b, ch in c['bones'].items()}
    esp = {}
    for b, ch in c['bones'].items():
        nb = b.replace('Left', '@').replace('Right', 'Left').replace('@', 'Right')
        esp[nb] = [[v[0], -v[1], -v[2]] for v in ch['rotation_euler']]
    return esp


def _guardar_sentado(arm, f):
    bpy.context.scene.frame_set(int(f))
    _SENT['rot'] = {b: arm.pose.bones[b].rotation_euler.copy() for b in BONES_POSE}
    _SENT['loc'] = {b: arm.pose.bones[b].location.copy() for b in BONES_POSE}


SOLO_ABAJO = ('Hips_alfred', 'RightUpLeg_alfred', 'Rightknee_alfred', 'LeftUpLeg_alfred', 'Leftknee_alfred')


def _pose_lanzar_sentado(arm, esp, i):
    """pose en el indice (fraccionario) i del clip: la mitad superior (columna, cuello, brazos) del clip; cadera y piernas se quedan sentadas"""
    i0 = int(math.floor(i)); t = i - i0; i1 = min(i0 + 1, 105)
    reset_pose(arm)
    for b in BONES_POSE:
        pb = arm.pose.bones[b]
        if b in SOLO_ABAJO:
            pb.rotation_euler = _SENT['rot'][b]; pb.location = _SENT['loc'][b]
        elif b in esp:
            a, c_ = esp[b][i0], esp[b][i1]
            pb.rotation_euler = [a[k] + (c_[k] - a[k]) * t for k in range(3)]
    bpy.context.view_layer.update()


def etapa_C3():
    arm, root = rig_alfred(); B = monos()
    _guardar_sentado(arm, int(G['sentado']))
    raiz(int(G['sentado']) + 1, C1, YAW)
    info = {}
    yaw_prev = YAW
    for k, (pn, nm, f_rel0, lado_mono, mano) in enumerate(TH):
        f0 = LANZAR_F0[k]
        esp = _clip_lanzar_lado(mano)
        hand_arm = ('RightUpArm_alfred', 'Rightelbow_alfred') if mano == 'R' else ('LeftUpArm_alfred', 'Leftelbow_alfred')
        hueso = hand_arm[1]
        # a donde apunta el brazo al soltar con el cuerpo en yaw 0 -> yaw del root para que apunte al mono
        _pose_lanzar_sentado(arm, esp, 46)
        sh = arm.pose.bones[hand_arm[0]].head; ma = arm.pose.bones[hand_arm[1]].tail
        raiz(f0, C1, yaw_prev)
        bpy.context.view_layer.update()
        Rel = root.matrix_world.inverted() @ arm.matrix_world
        v = Rel.to_3x3() @ (ma - sh)
        phi = math.degrees(math.atan2(v.y, v.x))
        sc = bpy.context.scene; sc.frame_set(int(f0 + 23))
        objetivo = hueso_mundo(B[nm], 'cube_r1', cola=False)
        az = math.degrees(math.atan2(objetivo.y - C1.y, objetivo.x - C1.x))
        yaw_t = az - phi
        while yaw_t - YAW > 180: yaw_t -= 360
        while yaw_t - YAW < -180: yaw_t += 360
        # el clip (indices 0..52) a LANZAR_VEL; el cuerpo gira hacia el mono mientras toma la pose de entrada (indice 12)
        n = int(round(52 / LANZAR_VEL))
        for j in range(n + 1):
            f = f0 + j
            _pose_lanzar_sentado(arm, esp, min(j * LANZAR_VEL, 52))
            for b in BONES_POSE:
                _key(arm, b, f)
        raiz(f0, C1, yaw_prev)
        raiz(f0 + 6, C1, yaw_t)
        raiz(f0 + 24, C1, yaw_t)
        raiz(f0 + n, C1, YAW)
        yaw_prev = YAW
        info[pn] = (mano, yaw_t, f0, f0 + 23, f0 + n)
    G['tools_fin'] = LANZAR_F0[1] + 26
    # palos: caen donde la mano los agarra (indice 2), los lleva hasta soltar y vuelan al mono
    for k, (pn, nm, f_rel0, lado_mono, mano) in enumerate(TH):
        palo = bpy.data.objects[pn]
        hand = 'Rightelbow_alfred' if mano == 'R' else 'Leftelbow_alfred'
        f0 = LANZAR_F0[k]; fg = f0 + 1; fr = f0 + 23
        p_ag = hueso_alfred(fg, hand, cola=True)
        quitar_todo(palo)
        vuela_a_alfred(palo, f_rel0, nm, lado_mono, f_rel0 + T_VUELO, 'face_alfred', aterriza=Vector((p_ag.x, p_ag.y, SUELO + 0.15)))
        for f in range(fg, fr + 1):
            palo.location = hueso_alfred(f, hand, cola=True)
            palo.keyframe_insert('location', frame=f)
        mano_p = hueso_alfred(fr, hand, cola=True)
        bpy.context.scene.frame_set(fr + T_VUELO)
        centro = hueso_mundo(B[nm], 'cube_r1', cola=False)
        vuelo(palo, fr, mano_p, fr + T_VUELO, centro, suelo=SUELO + 0.15, centro=centro)
        ocultar_hasta(palo, f_rel0)
        info[pn] += (fg, fr, [round(v, 2) for v in p_ag])
    return info


def pollo_accion(fn, f0, lista, rz, esc=1.0, ejecutar=True):
    """accion del estudio del pollo (generate_caminar / saltar_bajar / saltar_subir / picotear_1) con puntos (x, y, z) en f0 (escala vieja);
    esc = factor al insertar las claves (0.8 en la escena retemporizada); devuelve el frame final"""
    m = mod_estudio('chicken')
    P = [{'index': i + 1, 'coordinates': {'x': float(x), 'y': float(y), 'z': float(z)}} for i, (x, y, z) in enumerate(lista)]
    g = getattr(m, fn)
    code, fe = g(1, f0, P, '2026-10-30', (0, 0, rz), 'RAPIDO') if fn == 'generate_caminar' else g(1, f0, P, '2026-10-30', (0, 0, rz))
    if not ejecutar:
        return fe
    objs = ('chicken_1', 'Armature_chicken_1')
    previas = {n: bpy.data.objects[n].animation_data.action for n in objs}
    exec(code, {'__name__': '__main__'})
    for n in objs:
        o = bpy.data.objects[n]; ad = o.animation_data
        nuevas = []
        for tr in list(ad.nla_tracks):
            if tr.name.startswith('Slot_'):
                nuevas += [s.action for s in tr.strips if s.action is not None]
                ad.nla_tracks.remove(tr)
        if ad.action is not previas[n] and ad.action is not None:
            nuevas.append(ad.action)
        ad.action = previas[n]
        datos = [(c.data_path, c.array_index, [(kp.co[0], kp.co[1]) for kp in c.keyframe_points]) for a_ in nuevas for c in _fcs(a_)]
        for path, idx, keys in datos:
            if path.startswith('hide'):
                continue
            duenio, _, attr = path.rpartition('.')
            tgt = o.path_resolve(duenio) if duenio else o
            for f, v in keys:
                getattr(tgt, attr)[idx] = v
                tgt.keyframe_insert(attr, index=idx, frame=1 + (f - 1) * esc)
        for a_ in nuevas:
            bpy.data.actions.remove(a_)
    return fe


def pollo_visible(ch):
    """el pollo esta en la escena desde el frame 1: fuera las claves de visibilidad (suyas y de sus hijos) y visible"""
    for o in [ch] + list(ch.children_recursive):
        ad = o.animation_data
        if ad and ad.action:
            for l in ad.action.layers:
                for s in l.strips:
                    for bag in s.channelbags:
                        for c in [c for c in bag.fcurves if c.data_path in ('hide_viewport', 'hide_render')]:
                            bag.fcurves.remove(c)
        o.hide_viewport = False; o.hide_render = False


def pollo_deambula(f_w, L0, esc=1.0, ejecutar=True):
    """el pollo da vueltas por la zona desde el frame 1 (picotea, camina, salta para bajar el escalon del sur y vuelve a subir) y llega caminando
    a L0 en f_w justo cuando empieza su caminata hacia la mano de Alfred (la sincronizacion con la mano no se toca). Sale del paso de Alfred (fila y=32.5)"""
    X, Y = L0
    S = SUELO
    def pt(k, m, z=S):
        return (X + k, Y + m, z)
    ruta_s = [pt(3, 1 - i) for i in range(6)]                                  # (3,1) -> (3,-4)
    ruta_final = [pt(3, -4)] + [pt(3, -3 + i) for i in range(5)] + [pt(2, 1), pt(1, 1), pt(0, 1), pt(-1, 1), pt(-1, 0), pt(0, 0)]
    plan = [('generate_picotear_1', [pt(3, 1), pt(3, 1)]),
            ('generate_caminar', ruta_s),
            ('generate_picotear_1', [pt(3, -4), pt(3, -4)]),
            ('generate_saltar_bajar', [pt(3, -4), pt(3, -5, S - 1)]),
            ('generate_picotear_1', [pt(3, -5, S - 1), pt(3, -5, S - 1)]),
            ('generate_saltar_subir', [pt(3, -5, S - 1), pt(3, -4)]),
            ('generate_caminar', ruta_final)]
    m = mod_estudio('chicken')
    hd = m._compute_direction_angle({'x': X + 3, 'y': Y + 1}, {'x': X + 3, 'y': Y})        # el pollo mira hacia donde va a ir
    f = 1; agenda = []
    for i, (fn, lista) in enumerate(plan):
        n = len(lista) - 1
        if i == len(plan) - 1:
            f = f_w - 28 * n                                                   # el ultimo tramo termina justo en f_w
        pts = [{'x': p[0], 'y': p[1], 'z': p[2]} for p in lista]
        rz = hd
        fe = pollo_accion(fn, f, lista, rz, esc, ejecutar)
        agenda.append((fn, f, fe))
        if fn != 'generate_picotear_1':
            hd = m._compute_direction_angle(pts[-2], pts[-1])
        f = fe + 3
    return agenda


def etapa_D2():
    arm, root = rig_alfred(); B = monos()
    ch = bpy.data.objects['chicken_1']; ach = bpy.data.objects['Armature_chicken_1']
    for o in (ch, ach):
        for tr in list(o.animation_data.nla_tracks):
            o.animation_data.nla_tracks.remove(tr)
        quitar_todo(o)
    clip = cargar_clip('agarra_al_pollo_y_lo_lanza_al_creeper_parte7_alfred.py')
    sc = bpy.context.scene
    ff, _M = poner_clip(arm, root, clip, F_CH0, desde=0, hasta=19, solo=BONES_POSE, mover_root=False)
    raiz(F_CH0, C1, YAW); raiz(int(ff), C1, YAW)
    for b in BONES_POSE:
        _ULT[(arm.name, b)] = arm.pose.bones[b].rotation_euler.copy()
    quitar(arm, F_CH0, F_CH0 + 3)                                              # se funde desde el final del clip de las herramientas
    R0 = mat(clip['root']['location'][0], clip['root']['rotation_euler'][0])
    Tm = matriz(C1, YAW) @ R0.inverted()
    co = clip['objetos']['chicken_1']

    def Mch(i):
        return Tm @ Matrix.LocRotScale(Vector(co['location'][i]), Quaternion(co['rotation_quaternion'][i]), Vector(co['scale'][i]))
    M0 = Mch(0)
    p0 = M0.translation; yaw0 = M0.to_euler('XYZ').z
    dx, dy = round(-math.sin(yaw0)), round(math.cos(yaw0))
    lista = [(p0.x - k * dx, p0.y - k * dy) for k in (3, 2, 1, 0)]
    fe = camina_estudio('chicken', 0, lista, 'RAPIDO', ejecutar=False)
    f_w = F_CH0 - fe
    camina_estudio('chicken', f_w, lista, 'RAPIDO')
    pollo_visible(ch)
    pollo_deambula(f_w, lista[0])                                              # esta en la escena desde el frame 1; solo se sincroniza con la mano de Alfred
    sc.frame_set(F_CH0)
    prev = Euler(tuple(ch.rotation_euler), 'XYZ')
    for i in range(0, 17):
        loc, q, _s = Mch(i).decompose(); e = q.to_euler('XYZ', prev); prev = e
        ch.location = loc; ch.rotation_euler = e
        ch.keyframe_insert('location', frame=F_CH0 + i); ch.keyframe_insert('rotation_euler', frame=F_CH0 + i)
    for i in list(range(5, 17)) + [19]:
        for bn, dat in co['rig_bones'].items():
            pb = ach.pose.bones.get(bn)
            if pb is None:
                continue
            pb.rotation_mode = 'XYZ'; pb.rotation_euler = dat['rotation_euler'][i]
            pb.keyframe_insert('rotation_euler', frame=F_CH0 + i)
    f_r = F_CH0 + 17; f_c = f_r + T_VUELO
    cara_s = hueso_alfred(int(ff), 'face_alfred')
    tira('A2', F_A2_SUELTA, cara_s, 'l')
    a2 = B['A2']
    yaw17 = Mch(17).to_euler('XYZ').z
    p17 = Mch(17).translation
    vuelo(ch, f_r, p17, f_c, mano_mono(a2, f_c, 'l'), giro=(0.0, 0.0, 0.0))
    seguir_mano_mono(ch, a2, f_c, F_A2_SUELTA, 'l', off=(0, 0, -0.35))
    mano_s = mano_mono(a2, F_A2_SUELTA, 'l') + Vector((0, 0, -0.35))
    dest = cara_s                                                              # aproximacion de la cara sentado; se afina con la reaccion en la etapa F
    land = Vector((PH.x - 1.97, PH.y - 1.1, SUELO))
    vuelo(ch, F_A2_SUELTA, mano_s, F_CH_IMP, dest, giro=(0.0, 0.0, 0.0))
    f_fin = vuelo(ch, F_CH_IMP, dest, F_CH_IMP + 14, land, giro=(0.0, 0.0, 0.0), suelo=SUELO, choca=False)
    yaw_keys(ch, f_r, yaw17)
    CH_AT.update(dict(f_w=f_w, f_r=f_r, f_c=f_c, f_fin=f_fin, yaw=yaw17, alfred_fin=int(ff)))
    return dict(CH_AT)


def etapa_E2():
    arm, root = rig_alfred(); B = monos()
    rat = bpy.data.objects['rat_1']; arat = bpy.data.objects['body1_1']; ch = bpy.data.objects['chicken_1']
    for o in (rat, arat):
        for tr in list(o.animation_data.nla_tracks):
            o.animation_data.nla_tracks.remove(tr)
        quitar_todo(o)
    a4 = B['A4']
    cara_s = hueso_alfred(CH_AT['alfred_fin'], 'face_alfred')
    tira('A4', RAT_REL, cara_s, 'r')
    ocultar_hasta(rat, RAT_REL - 10)
    for pb in arat.pose.bones:
        pb.rotation_mode = 'XYZ'; pb.rotation_euler = (0, 0, 0)
        pb.keyframe_insert('rotation_euler', frame=RAT_REL - 10)
    yaw_r = math.radians(yaw_hacia(mano_mono(a4, RAT_REL, 'r'), cara_s))
    rat.rotation_euler = (0, 0, yaw_r); rat.keyframe_insert('rotation_euler', frame=RAT_REL - 10)
    seguir_mano_mono(rat, a4, RAT_REL - 9, RAT_REL, 'r', off=(0, 0, -0.15))
    mano = mano_mono(a4, RAT_REL, 'r') + Vector((0, 0, -0.15))
    vuelo(rat, RAT_REL, mano, F_RAT_IMP, cara_s, giro=(0.0, 0.0, 0.0))
    f_r_fin = vuelo(rat, F_RAT_IMP, cara_s, F_RAT_IMP + 14, Vector((PH.x - 1.37, PH.y + 0.8, SUELO)), giro=(0.0, 0.0, 0.0), suelo=SUELO, choca=False)
    yaw_keys(rat, RAT_REL, yaw_r)
    pc = pos_obj(ch, CH_AT['f_fin']); pr = pos_obj(rat, f_r_fin)
    camina_estudio('chicken', CH_AT['f_fin'] + 3, [(pc.x, pc.y), (pc.x - 1.0, pc.y)], 'RAPIDO')
    camina_estudio('rat', f_r_fin + 3, [(pr.x, pr.y), (pr.x - 1.0, pr.y)], 'RAPIDO')
    a3 = B['A3']
    saltar_mono(a3, 793, 12, BASEM['A3'][0], S6_A3, 11.0)
    regreso('A3', 818)
    for nm, f in (('A6', 606 + 14 + 30), ('A2', F_A2_SUELTA + 14 + 30), ('A4', RAT_REL + 14 + 30)):
        regreso(nm, f)
    return dict(rat_fin=f_r_fin)


def etapa_F2():
    """Alfred desde que lanza el pollo hasta empalmar con el 854 (se rehace de forma idempotente)"""
    arm, root = rig_alfred(); B = monos()
    p854 = {(c.data_path, c.array_index): c.evaluate(F1 + 1) for c in _fcs(arm.animation_data.action) if c.data_path.startswith('pose.bones')}
    r854 = ([valor(root, 'location', i, F1 + 1) for i in range(3)], valor(root, 'rotation_euler', 2, F1 + 1))
    ffc = CH_AT['alfred_fin']
    quitar(arm, ffc + 1, F1); quitar(root, ffc + 1, F1)
    sent = cargar_clip('sentarse_alfred.py')
    for f in (F_REPOSO1, F_REPOSO2):
        poner_clip(arm, root, sent, f, desde=56, hasta=56, solo=BONES_POSE, mover_root=False)
        raiz(f, C1, YAW)
    for b in BONES_POSE:
        _ULT[(arm.name, b)] = arm.pose.bones[b].rotation_euler.copy()
    cara_s = hueso_alfred(ffc, 'face_alfred')
    v_p = velocidad_golpe(mano_mono(B['A2'], F_A2_SUELTA, 'l') + Vector((0, 0, -0.35)), cara_s, T_VUELO)
    golpe_sentado(F_CH_IMP, v_p, MASA_POLLO, 8)
    v_r = velocidad_golpe(mano_mono(B['A4'], RAT_REL, 'r') + Vector((0, 0, -0.15)), cara_s, T_VUELO)
    golpe_sentado(F_RAT_IMP, v_r, MASA_RATA, 8)
    clip = cargar_clip('se_levanta_cojeando_parte7_alfred.py')
    ff, _M = poner_clip(arm, root, clip, F_UP, vel=2.0, desde=0, hasta=30, solo=BONES_POSE, mover_root=False)
    raiz(F_UP, C1, YAW); raiz(int(ff), C1, YAW)
    for b in BONES_POSE:
        _ULT[(arm.name, b)] = arm.pose.bones[b].rotation_euler.copy()
    global validar_recorrido
    _v = validar_recorrido; validar_recorrido = lambda p: None
    ruta = [(PH.x + 0.0, PH.y, PH.z), (-73.5, 32.5, 12.0), (-74.5, 32.5, 12.0), (-75.5, 32.5, 12.0), tuple(RS)]     # vuelve a RS (la ultima zancada mide 1.13)
    fin = caminar_ruta(int(ff) + 1, ruta, yaw_ini=YAW, yaw_fin=-58.0)
    validar_recorrido = _v
    quitar(arm, int(ff) + 1, int(ff) + 3)                                        # arranca fundiendose desde la pose de pie
    for (path, idx), v in p854.items():                                          # el 853 copia la pose del 854 (sin salto con el Bloque 4)
        duenio, _, attr = path.rpartition('.')
        getattr(arm.path_resolve(duenio), attr)[idx] = v
    for b in BONES_POSE:
        pb = arm.pose.bones[b]
        pb.keyframe_insert('rotation_euler', frame=F1, group=b)
        if b in ('Hips_alfred', 'RightUpArm_alfred', 'LeftUpArm_alfred'):
            pb.keyframe_insert('location', frame=F1, group=b)
    root.location = Vector(r854[0]); root.rotation_euler = (0, 0, r854[1])
    root.keyframe_insert('location', frame=F1); root.keyframe_insert('rotation_euler', frame=F1)
    return dict(levanta_fin=ff, camina_fin=fin)


def cierre():
    arm, root = rig_alfred()
    desenrollar(arm); desenrollar(root)
    bpy.context.scene.frame_set(F0)


def ruta_a_arbol2(f_ini=781, fj=899, destino=(-75.63, 29.5)):
    """tras levantarse camina DIRECTO desde (-72.5, 32.5) al sitio de talar del 2o arbol (donde empalma el Bloque 4 en fj); antes volvia a RS sin motivo.
    Quita las claves de Alfred entre f_ini y fj-1 (vuelta a RS y primer tramo del Bloque 4) y empalma con la pose del Bloque 4 en fj"""
    arm, root = rig_alfred(); sc = bpy.context.scene
    sc.frame_set(fj)
    pj = {(c.data_path, c.array_index): c.evaluate(fj) for c in _fcs(arm.animation_data.action) if c.data_path.startswith('pose.bones')}
    rj = ([valor(root, 'location', i, fj) for i in range(3)], valor(root, 'rotation_euler', 2, fj))
    quitar(arm, f_ini, fj - 1); quitar(root, f_ini, fj - 1)
    global validar_recorrido
    _v = validar_recorrido; validar_recorrido = lambda p: None
    n = 3
    ruta = [(PH.x + (destino[0] - PH.x) * k / n, PH.y + (destino[1] - PH.y) * k / n, PH.z) for k in range(n + 1)]
    fin = caminar_ruta(f_ini, ruta, yaw_ini=YAW, yaw_fin=math.degrees(rj[1]))
    validar_recorrido = _v
    quitar(arm, f_ini, f_ini + 2)
    for f in (fin + 10, fj - 1):                                                  # se asienta en la pose del Bloque 4 y la mantiene hasta que empieza a talar
        for (path, idx), v in pj.items():
            duenio, _, attr = path.rpartition('.')
            getattr(arm.path_resolve(duenio), attr)[idx] = v
        for b in BONES_POSE:
            pb = arm.pose.bones[b]
            pb.keyframe_insert('rotation_euler', frame=f, group=b)
            if b in ('Hips_alfred', 'RightUpArm_alfred', 'LeftUpArm_alfred'):
                pb.keyframe_insert('location', frame=f, group=b)
        root.location = Vector(rj[0]); root.rotation_euler = (0, 0, rj[1])
        root.keyframe_insert('location', frame=f); root.keyframe_insert('rotation_euler', frame=f)
    desenrollar(arm); desenrollar(root)
    return dict(camina_fin=fin, pos_fin=[round(v, 2) for v in rj[0]], yaw_fin=round(math.degrees(rj[1]), 1))
