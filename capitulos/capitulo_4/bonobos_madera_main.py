# -*- coding: utf-8 -*-
"""Orquestador: arma TODA la animacion de 'Alfred tala arboles y los bonobos le tiran cosas' en la escena viva (base_tarde con las ranas.blend).
    exec(open(este_archivo).read()); armar()
Cada llamada re-genera las acciones de Alfred, de los bonobos y de los objetos desde cero (no toca el escenario). 24 fps."""
import bpy, math, json, random
from mathutils import Vector, Matrix

RUTA = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4"
for _m in ('bonobos_madera_alfred.py', 'bonobos_madera_escena.py', 'bonobos_madera_bonobos.py', 'bonobos_madera_fisica.py', 'bonobos_madera_foto.py'):
    exec(open(RUTA + '\\' + _m, encoding='utf8').read())

SUELO = 12.0
PEND = []          # vuelos pendientes (se resuelven cuando todo esta animado)
OCUP = {}          # ventanas de frames ocupadas por cada bonobo (para rellenar con vigilancia)


def pos_hueso_alfred(f, hueso, cola=False):
    arm, root = rig_alfred()
    bpy.context.scene.frame_set(int(f))
    pb = arm.pose.bones[hueso]
    return arm.matrix_world @ (pb.tail if cola else pb.head)


def pos_bonobo(raiz, f, hueso='head'):
    bpy.context.scene.frame_set(int(f))
    return hueso_mundo(raiz, hueso, cola=False)


def item(nombre, carpeta, lado_max=0.35):
    o = objeto_item(nombre, carpeta, 1.0)
    bpy.context.view_layer.update()
    d = max(o.dimensions) or 1.0
    o.scale = (lado_max / d,) * 3
    for ch in ('hide_viewport', 'hide_render'):
        setattr(o, ch, False)
    return o


def yaw_a_alfred(pos, f):
    """Alfred esta en C1 hasta que acaba con el pollo y despues en C2"""
    return yaw_hacia(pos, (-75.63, 29.5) if f >= G['pollo_rel'] + 10 else (-77.63, 32.5))


def lanza_bonobo(b, f_rel, obj, f_imp, pos, lado='l', hueso_destino='face_alfred', desvio=(0, 0, 0), fallar=False, altura=2.0, suelo=SUELO + 0.15, caida=10):
    """lanzamiento con la mejor animacion: se incorpora mirando a Alfred, arma el brazo con el torso girado, suelta con un saltito apuntando segun la distancia/altura y sigue de largo"""
    pos = Vector(pos)
    yb = yaw_a_alfred(pos, f_rel)
    obj_pt = Vector((-77.3, 31.8, 13.9))
    dh = math.hypot(obj_pt.x - pos.x, obj_pt.y - pos.y); dz = pos.z + 1.4 - obj_pt.z
    elev = max(-0.05, min(0.6, 0.5 - 0.9 * dz / (dh + dz)))             # mas hacia abajo cuanto mas alto esta
    s = 1 if lado == 'l' else -1
    b_vigila(b, f_rel - 16, head=V(0, 1.0, -0.35 * dz / (dh + dz)))
    broot(b, f_rel - 16, pos, yb)
    b_levanta(b, f_rel - 9, lado, jaw=20)                                  # se incorpora de golpe
    broot(b, f_rel - 9, pos, yb - 6 * s)
    b_levanta(b, f_rel - 4, lado, jaw=30, **{('la' if lado == 'l' else 'ra'): V(0.45 * s, -0.55, 0.8)})   # brazo atras
    broot(b, f_rel - 4, pos, yb - 12 * s)
    kw = {('la' if lado == 'l' else 'ra'): V(0.15 * s, 0.85, elev), ('lf' if lado == 'l' else 'rf'): V(0.05 * s, 0.95, elev - 0.12)}
    b_suelta(b, f_rel, lado, **kw)                                         # latigazo: 4 frames de brazo atras a soltar
    broot(b, f_rel, pos + V(0, 0, 0.12), yb + 10 * s)
    b_sigue(b, f_rel + 3, lado)
    broot(b, f_rel + 3, pos, yb + 6 * s)
    b_levanta(b, f_rel + 11, lado, la=V(0.3, 0.3, 0.2), ra=V(-0.3, 0.3, 0.2), jaw=35)   # grita de triunfo / frustracion
    broot(b, f_rel + 11, pos, yb)
    bpose(b, f_rel + 18)
    OCUP.setdefault(b.name, []).append((f_rel - 18, f_rel + 20))
    PEND.append(('a_alfred', b, f_rel, obj, f_imp, lado, hueso_destino, desvio, fallar, altura, suelo, caida))


def lanza_alfred(f_rel, obj, f_imp, bonobo_destino, grab=None, hueso_mano='Leftelbow_alfred', suelo=None, altura=3.0, caida=14):
    PEND.append(('a_bonobo', f_rel, obj, f_imp, bonobo_destino, grab, hueso_mano, suelo, altura, caida))


def resolver_pend():
    for p in PEND:
        if p[0] == 'a_alfred':
            _, b, f_rel, obj, f_imp, lado, hd, desvio, fallar, altura, suelo, caida = p
            mano = pos_bonobo(b, f_rel, ('left' if lado == 'l' else 'right') + 'hand')
            destino = pos_hueso_alfred(f_imp, hd) + Vector(desvio)
            if fallar:
                destino = destino + Vector((0.0, 0.9, -0.9))
            vuelo(obj, f_rel, mano, f_imp, destino, suelo=suelo, centro=(None if fallar else pos_hueso_alfred(f_imp, 'Spine1_alfred')), choca=not fallar)
            esconder(obj, f_rel)
        else:
            _, f_rel, obj, f_imp, bonobo_destino, grab, hueso_mano, suelo, altura, caida = p
            mano = pos_hueso_alfred(f_rel, hueso_mano, cola=True)
            destino = pos_bonobo(bonobo_destino, f_imp, 'cube_r1') if bonobo_destino is not None else mano + Vector((-3, 0, 1))
            vuelo(obj, f_rel, mano, f_imp, destino, suelo=suelo)
    PEND.clear()


def seguir_mano(obj, f0, f1, hueso='Leftelbow_alfred', off=(0, 0, 0)):
    for f in range(int(f0), int(f1) + 1):
        obj.location = pos_hueso_alfred(f, hueso, cola=True) + Vector(off)
        obj.keyframe_insert('location', frame=f)


def aparece_en(obj, f0, loc):
    obj.location = loc
    obj.keyframe_insert('location', frame=f0 - 1)


def saltar(b, f0, dur, p_ini, p_fin, yaw_fin, alto=2.5):
    OCUP.setdefault(b.name, []).append((f0 - 9, f0 + dur + 9))
    """salto de copa en copa: agacha, vuela en parabola, cae"""
    p_ini = Vector(p_ini); p_fin = Vector(p_fin)
    yv = yaw_hacia(p_ini, p_fin)
    bpose(b, f0 - 7)
    broot(b, f0 - 7, p_ini, yv)
    b_agacha(b, f0 - 3)                                  # se agazapa un instante y salta
    broot(b, f0 - 3, p_ini, yv)
    for i in range(dur + 1):
        t = i / dur
        p = p_ini.lerp(p_fin, t) + Vector((0, 0, alto * 4 * t * (1 - t)))
        broot(b, f0 + i, p, yv + (yaw_fin - yv) * max(0.0, t - 0.6) / 0.4)
    b_vuela(b, f0 + 2)
    b_vuela(b, f0 + dur - 2)
    b_cae(b, f0 + dur)
    bpose(b, f0 + dur + 7)


def animar_hacha_cae():
    """el hacha va siempre en la mano derecha (pose fija HERR_MANO_DER); al recibir la serpiente se le cae"""
    ax = bpy.data.objects['stone_axe']
    fd = G['hacha_cae']
    c = ax.constraints['Mano']
    c.influence = 1.0; c.keyframe_insert('influence', frame=fd - 1)
    ax.location = HACHA_LOC; ax.rotation_euler = HACHA_ROT; ax.scale = (HACHA_ESC,) * 3
    ax.keyframe_insert('location', frame=fd - 1); ax.keyframe_insert('rotation_euler', frame=fd - 1); ax.keyframe_insert('scale', frame=fd - 1)
    bpy.context.scene.frame_set(fd - 1)
    Mw = ax.matrix_world.copy()
    loc, q, s = Mw.decompose()
    c.influence = 0.0; c.keyframe_insert('influence', frame=fd)
    ax.location = loc; ax.rotation_euler = q.to_euler(); ax.scale = s
    ax.keyframe_insert('location', frame=fd); ax.keyframe_insert('rotation_euler', frame=fd); ax.keyframe_insert('scale', frame=fd)
    # cae con la gravedad (aceleracion, no a velocidad constante), gira hasta quedar tumbada y rebota una vez al tocar el suelo
    z0 = loc.z; zr = SUELO + 0.05; h_ = max(z0 - zr, 0.02)
    nf = max(3, int(math.ceil(math.sqrt(2 * h_ / G_F))))
    e0 = Vector(ax.rotation_euler); e1 = Vector((math.radians(80), 0.4, 1.0)); xy1 = Vector((loc.x - 0.1, loc.y + 0.15))
    for i in range(1, nf + 1):
        tt = i / nf
        xy = Vector((loc.x, loc.y)).lerp(xy1, tt)
        ax.location = (xy.x, xy.y, z0 - h_ * tt * tt)
        e = e0.lerp(e1, tt * tt)
        ax.rotation_euler = (e.x, e.y, e.z)
        ax.keyframe_insert('location', frame=fd + i); ax.keyframe_insert('rotation_euler', frame=fd + i)
    vb = math.sqrt(2 * G_F * h_) * 0.3
    for j in range(1, 2 * int(math.ceil(vb / G_F)) + 1):
        ax.location = (xy1.x, xy1.y, zr + vb * j - 0.5 * G_F * j * j)
        ax.keyframe_insert('location', frame=fd + nf + j)
    ax.location = (xy1.x, xy1.y, zr)
    ax.keyframe_insert('location', frame=fd + nf + 2 * int(math.ceil(vb / G_F)) + 1)


def armar():
    sc = bpy.context.scene
    sc['bm_listo'] = 'trabajando'
    PEND.clear()
    import re
    for o_ in list(bpy.data.objects):                                  # objetos lanzados de corridas anteriores (si no, quedan copias viejas visibles)
        if re.match(r'^bm_(apple|stick|honeycomb|cocoa_beans|sweet_berries|flint)_\d+$', o_.name):
            bpy.data.objects.remove(o_, do_unlink=True)
    ax0 = bpy.data.objects['stone_axe']                                 # claves viejas del hacha (de corridas anteriores) quedaban entre los hachazos nuevos
    ax0.animation_data_clear()
    HACHAZOS.clear()
    ax0.constraints['Mano'].influence = 1.0
    ax0.location = HACHA_LOC; ax0.rotation_euler = HACHA_ROT; ax0.scale = (HACHA_ESC,) * 3
    bon = preparar_bonobos()
    B = lambda n: bon['bonobo_' + n]
    construir_alfred_parte1()
    construir_alfred_resto()
    arm, root = rig_alfred()
    C1 = (-77.63, 32.5)
    OCUP.clear()
    HOME = {n: Vector(r.location) for n, r in bon.items()}          # cada bonobo en su casa (copa con vista despejada)
    sc['bm_homes'] = json.dumps({n: list(v) for n, v in HOME.items()})
    for nm, r in bon.items():
        iniciar(r)
        broot(r, 1, HOME[nm], yaw_hacia(HOME[nm], C1))
        bpose(r, 1)
    H = lambda n: HOME['bonobo_' + n]
    N3, S6, SW2 = Vector((-76.5, 36.5, 19.0)), Vector((-73.5, 18.5, 18.0)), Vector((-86.5, 25.5, 18.0))
    mi = G['manzana_impacto']
    A1 = B('A1'); A2 = B('A2'); A3 = B('A3'); A4 = B('A4'); A5 = B('A5'); A6 = B('A6'); A7 = B('A7'); B1 = B('B1'); B2 = B('B2'); B3 = B('B3')
    # ----------------------------------------------------------------- A1 (copa norte): manzana
    ap = item('apple', 'apple', 0.30)
    lanza_bonobo(A1, G['manzana_suelta'], ap, G['manzana_impacto'], H('A1'))
    b_grita(A1, mi + 8, jaw=45); broot(A1, mi + 8, H('A1') + V(0, 0, 0.15), yaw_hacia(H('A1'), C1))
    b_grita(A1, mi + 30, jaw=10); broot(A1, mi + 30, H('A1'), yaw_hacia(H('A1'), C1))
    OCUP.setdefault(A1.name, []).append((mi + 4, mi + 36))
    # silex de Alfred hacia A1: A1 se agacha y salta a otro punto de la copa
    saltar(A1, G['silex_rel'] + 4, 10, H('A1'), N3, yaw_hacia(N3, C1), alto=1.5)
    # ----------------------------------------------------------------- A2 (oeste): palo en el hombro, bayas
    stick1 = item('stick', 'stick', 0.55)
    lanza_bonobo(A2, G['palo1_rel'], stick1, G['palo1_imp'], H('A2'), hueso_destino='Spine2_alfred', desvio=(0.0, 0.0, 0.15))
    baya = item('sweet_berries', 'sweet_berries', 0.30)
    lanza_bonobo(A2, G['baya_imp'] - 24, baya, G['baya_imp'], H('A2'))
    # ----------------------------------------------------------------- A3 (sur): palo que falla; recibe la rata
    stick2 = item('stick', 'stick', 0.55)
    lanza_bonobo(A3, G['palo2_rel'], stick2, G['palo2_imp'], H('A3'), fallar=True, lado='r')
    b_grita(A3, G['rata_rel'] + 26, jaw=45); b_grita(A3, G['rata_rel'] + 40, jaw=45)
    OCUP.setdefault(A3.name, []).append((G['rata_rel'] + 20, G['rata_rel'] + 44))
    saltar(A3, G['rata_rel'] + 44, 10, H('A3'), S6, yaw_hacia(S6, (-75.63, 29.5)), alto=1.5)
    # ----------------------------------------------------------------- A4 (oeste alto): cacao que falla, bayas
    cacao = item('cocoa_beans', 'cocoa_beans', 0.28)
    lanza_bonobo(A4, G['cacao_rel'], cacao, G['cacao_imp'], H('A4'), fallar=True)
    baya2 = item('sweet_berries', 'sweet_berries', 0.30)
    lanza_bonobo(A4, G['baya2_imp'] - 24, baya2, G['baya2_imp'], H('A4'), lado='r', hueso_destino='Spine2_alfred')
    # ----------------------------------------------------------------- A5 (norte bajo): panal; recibe el pollo
    panal = item('honeycomb', 'honeycomb', 0.35)
    lanza_bonobo(A5, G['panal_rel'], panal, G['panal_imp'], H('A5'))
    b_grita(A5, G['pollo_rel'] + 28, jaw=45); b_grita(A5, G['pollo_rel'] + 44, jaw=45)
    OCUP.setdefault(A5.name, []).append((G['pollo_rel'] + 22, G['pollo_rel'] + 48))
    saltar(A5, G['pollo_rel'] + 48, 10, H('A5'), H('A1'), yaw_hacia(H('A1'), (-75.63, 29.5)), alto=1.5)
    # ----------------------------------------------------------------- A6, A7, bebes: gritan, cambian de punto
    saltar(A6, G['silex_rel'] + 41, 9, H('A6'), SW2, yaw_hacia(SW2, C1), alto=1.5)
    for nm in ('A6', 'A7', 'B1', 'B2', 'B3'):
        r = B(nm)
        f_g = (mi + 60) if nm in ('A7', 'B3') else (G['panal_imp'] + 4)
        b_grita(r, f_g, jaw=40)
        OCUP.setdefault(r.name, []).append((f_g - 8, f_g + 24))
    # ----------------------------------------------------------------- pedernal de Alfred
    flint = item('flint', 'flint', 0.28)
    aparece_en(flint, 1, Vector(G['pos_silex']) + Vector((0.0, -0.1, 0.1)))
    aparece_en(flint, G['silex_grab'], Vector(G['pos_silex']) + Vector((0.0, -0.1, 0.1)))
    seguir_mano(flint, G['silex_grab'], G['silex_rel'], off=(0, 0, 0.05))
    lanza_alfred(G['silex_rel'], flint, G['silex_rel'] + 26, A1, suelo=SUELO + 0.15, altura=4.0, caida=14)
    # ----------------------------------------------------------------- rata (camina y Alfred se la lanza a A3)
    rat = bpy.data.objects['rat_1']
    for o in [rat] + rat.children_recursive:
        o.hide_viewport = False; o.hide_render = False
    rat.scale = (0.6, 0.6, 0.6)
    f_ini = G['rata_llega'] - 110
    P0, P1 = Vector((-70.8, 29.5, SUELO)), Vector((-75.9, 31.3, SUELO))
    yr = yaw_hacia(P0, P1)
    esconder(rat, f_ini)
    for i in range(0, 111, 2):
        t = i / 110
        rat.location = P0.lerp(P1, t) + Vector((0, 0, 0.03 * math.sin(i * 1.3)))
        rat.rotation_euler = (0, 0, math.radians(yr + 4 * math.sin(i * 0.5)))
        rat.keyframe_insert('location', frame=f_ini + i); rat.keyframe_insert('rotation_euler', frame=f_ini + i)
    rat.location = P1; rat.keyframe_insert('location', frame=G['rata_grab'] - 1)
    seguir_mano(rat, G['rata_grab'], G['rata_rel'], off=(0, 0, -0.1))
    lanza_alfred(G['rata_rel'], rat, G['rata_rel'] + 26, A3, suelo=SUELO, altura=3.0, caida=18)
    # ----------------------------------------------------------------- pollo (camina y Alfred se lo lanza a A5)
    pol = bpy.data.objects['chicken_1']
    for o in [pol] + pol.children_recursive:
        o.hide_viewport = False; o.hide_render = False
    pol.scale = (0.7, 0.7, 0.7)
    f_ini = G['pollo_llega'] - 90
    Q0, Q1 = Vector((-71.5, 36.0, SUELO)), Vector((-75.2, 33.5, SUELO))
    yp = yaw_hacia(Q0, Q1)
    esconder(pol, f_ini)
    for i in range(0, 91, 2):
        t = i / 90
        pol.location = Q0.lerp(Q1, t) + Vector((0, 0, 0.04 * abs(math.sin(i * 0.7))))
        pol.rotation_euler = (0, 0, math.radians(yp + 6 * math.sin(i * 0.4)))
        pol.keyframe_insert('location', frame=f_ini + i); pol.keyframe_insert('rotation_euler', frame=f_ini + i)
    pol.location = Q1; pol.keyframe_insert('location', frame=G['pollo_grab'] - 1)
    seguir_mano(pol, G['pollo_grab'], G['pollo_rel'], off=(0, 0, -0.1))
    lanza_alfred(G['pollo_rel'], pol, G['pollo_rel'] + 26, A5, suelo=SUELO, altura=3.5, caida=24)
    # ----------------------------------------------------------------- hacha: se le cae al recibir la serpiente
    aplicar_hacha_talas()
    animar_hacha_cae()
    # ----------------------------------------------------------------- serpiente
    ser = bpy.data.objects['snake_plains']
    for o in [ser] + ser.children_recursive:
        o.hide_viewport = False; o.hide_render = False
    ser.scale = (0.45, 0.45, 0.45)
    fi = G['serpiente_imp']; fr = G['serpiente_rel']
    g_loc = Vector((-79.6, 34.0, 26.0))
    # en la mano de A2 (sube con el) hasta soltarla
    esconder(ser, fr)
    lanza_bonobo(A7, fr, ser, fi, H('A7'), hueso_destino='Leftelbow_alfred', suelo=None, caida=0)
    # ----------------------------------------------------------------- festejo final de todos, cada uno en su punto, mirando a Alfred (C2)
    C2 = (-75.63, 29.5)
    pos_final = {'A1': N3, 'A3': S6, 'A5': H('A1'), 'A6': SW2}
    for k, nm in enumerate(['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'B1', 'B2', 'B3']):
        r = B(nm)
        base = pos_final.get(nm, H(nm))
        yw = yaw_hacia(base, C2)
        f0 = G['serpiente_rel'] + 26 + (k % 3) * 3
        for j in range(0, 22):
            ff = f0 + j * 8
            if ff > G['fin'] - 5:
                break
            arriba = (j % 2 == 0)
            b_grita(r, ff, jaw=(45 if arriba else 15), la=(Vector((0.4, 0.2, 0.9)) if arriba else Vector((0.3, 0.5, 0.3))), ra=(Vector((-0.4, 0.2, 0.9)) if not arriba else Vector((-0.3, 0.5, 0.3))))
            broot(r, ff, base + Vector((0, 0, 0.18 if arriba else 0.0)), yw)
        OCUP.setdefault(r.name, []).append((G['serpiente_rel'] + 22, G['fin']))
    # ----------------------------------------------------------------- vigilancia entre acciones (miran a Alfred, giran la cabeza, se rascan, resoplan)
    rnd = random.Random(7)
    for nm, r in bon.items():
        ocu = sorted(OCUP.get(r.name, []))
        f = 10 + rnd.randint(0, 10)
        while f < G['fin'] - 20:
            hold = rnd.randint(5, 14)
            if not any(a0 - 4 <= f <= a1 + 2 or a0 - 4 <= f + hold + 4 <= a1 + 2 for a0, a1 in ocu):
                ang = rnd.choice((-0.7, -0.4, 0.4, 0.7))
                pose_i = rnd.choice(('mira', 'rasca', 'mira', 'resopla', 'salta'))
                kw = {'mira': dict(head=V(ang, 0.9, 0.2)),
                      'rasca': dict(head=V(-ang * 0.5, 0.9, 0.0), la=V(0.2, 0.6, 0.3), lf=V(-0.2, 0.7, 0.5)),
                      'resopla': dict(jaw=14, head=V(0, 0.9, 0.35)),
                      'salta': dict(head=V(ang, 0.9, 0.3), jaw=30, la=V(0.3, 0.5, 0.4), ra=V(-0.3, 0.5, 0.4))}[pose_i]
                bpose(r, f - 3)                                        # reposo hasta justo antes del tic
                bpose(r, f, **kw)                                      # cambia en 3 frames
                bpose(r, f + hold, **kw)                               # aguanta
                bpose(r, f + hold + 4)                                 # vuelve de golpe
            f += hold + rnd.randint(14, 34)
    resolver_pend()
    fi_s = G['serpiente_imp']
    sc2 = 0.45
    PT = {}
    for f in range(fi_s - 1, G['fin'] + 2):
        h = pos_hueso_alfred(f, 'Leftelbow_alfred', cola=False); c_ = pos_hueso_alfred(f, 'Leftelbow_alfred', cola=True)
        PT[f] = h + (c_ - h) * 0.45
    for f in range(fi_s, G['fin'] + 1):
        punto = PT[f]
        acc = PT[f + 1] - 2 * PT[f] + PT[f - 1]                          # aceleracion del brazo: la serpiente colgada se balancea en sentido contrario (inercia)
        ser.location = punto - Vector((0, 0, 0.92 * sc2))
        k_ = (f - fi_s)
        ser.rotation_euler = (math.pi / 2 + 0.18 * math.sin(k_ / 6.0) - max(-0.7, min(0.7, 4.0 * acc.y)), 0.12 * math.sin(k_ / 9.0) + max(-0.7, min(0.7, 4.0 * acc.z)), 0.15 * math.sin(k_ / 5.0) - max(-0.7, min(0.7, 4.0 * acc.x)))
        ser.keyframe_insert('location', frame=f); ser.keyframe_insert('rotation_euler', frame=f)
    for ob in [_rig(r) for r in bon.values()] + list(bon.values()) + [rig_alfred()[0], rig_alfred()[1]] + [o for o in bpy.data.objects if o.name.startswith('bm_') and o.animation_data]:
        desenrollar(ob)
        lineal(ob)
    sc.frame_start = 1
    sc.frame_end = G['fin'] + 30
    sc['bm_listo'] = 'ok frame_end=%d' % sc.frame_end
    return G
