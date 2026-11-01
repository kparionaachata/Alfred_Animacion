# -*- coding: utf-8 -*-
"""Bloque 3 nuevo de 'Alfred tala arboles y los bonobos le tiran cosas' (escena viva base_tarde con las ranas.blend, frames vivos 535-853, 24 fps).
Historia: los bonobos le tiran palos a la cara; tras varios impactos Alfred cae sentado; sentado les devuelve los palos; el pollo pasa por su mano, lo agarra y se lo lanza
a un bonobo; el bonobo se lo devuelve y luego le tiran una rata; Alfred se levanta y da un paso hacia el segundo arbol.
Usa los clips de la biblioteca (codigos de animacion/alfred): sentarse_alfred, sentado_tirar_herramientas_alfred, agarra_al_pollo_y_lo_lanza_al_creeper_parte7_alfred,
se_levanta_cojeando_parte7_alfred, y la fisica de bonobos_madera_fisica.py (skill inercia-accion-reaccion).
Se ejecuta en la escena viva (no regenera nada fuera de la ventana F0-F1):
    exec(open(este_archivo).read()); luego las funciones por etapas (ver abajo)."""
import bpy, math, json
from mathutils import Vector, Matrix, Euler

RUTA = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4"
for _m in ('bonobos_madera_alfred.py', 'bonobos_madera_bonobos.py', 'bonobos_madera_fisica.py'):
    exec(open(RUTA + '\\' + _m, encoding='utf8').read())

SUELO = 12.0
C1 = Vector((-77.63, 32.5, 12.0))
RS = Vector((-76.63, 32.5, 12.0))
YAW = 90.0
F0, F1 = 535, 853                       # ventana que se rehace (frames vivos)
PEND3 = []


def _fcs(a):
    return [c for l in a.layers for s in l.strips for b in s.channelbags for c in b.fcurves]


def quitar(obj, f0, f1, paths=None):
    a = obj.animation_data.action if obj.animation_data else None
    if not a:
        return 0
    n = 0
    for c in _fcs(a):
        if paths and not any(c.data_path.startswith(p) for p in paths):
            continue
        for kp in reversed(list(c.keyframe_points)):
            if f0 <= round(kp.co[0]) <= f1:
                c.keyframe_points.remove(kp); n += 1
        c.update()
    return n


def valor(obj, path, idx, f):
    a = obj.animation_data.action
    for c in _fcs(a):
        if c.data_path == path and c.array_index == idx:
            return c.evaluate(f)
    return None


def monos():
    return {o.name[len('bonobo_'):]: o for o in bpy.data.objects if o.name.startswith('bonobo_') and o.type == 'EMPTY' and o.parent is None}


def pos_mono(b, f):
    return Vector([valor(b, 'location', i, f) for i in range(3)])


def yaw_mono(b, f):
    return math.degrees(valor(b, 'rotation_euler', 2, f))


# ------------------------------------------------------------------------------------------------ etapa A: limpiar la ventana
def etapa_A():
    """borra las claves de Alfred, los bonobos, la rata y el pollo en F0-F1 y deja a los bonobos quietos en su sitio (pose de reposo)"""
    arm, root = rig_alfred()
    B = monos()
    base = {n: (pos_mono(b, F0 - 1), yaw_mono(b, F0 - 1)) for n, b in B.items()}
    n = quitar(arm, F0, F1) + quitar(root, F0, F1)
    for nm, b in B.items():
        n += quitar(b, F0, F1) + quitar(_rig(b), F0, F1)
    for nom in ('rat_1', 'chicken_1'):
        o = bpy.data.objects[nom]
        n += quitar(o, F0 - 4, F1 + 60, ('location', 'rotation_euler'))
    for nom in ('body1_1', 'Armature_chicken_1'):
        n += quitar(bpy.data.objects[nom], F0 - 4, F1 + 60, ('pose.bones',))
    for nm, b in B.items():
        p, y = base[nm]
        for f in (F0, F1):
            broot(b, f, p, y); bpose(b, f)
    return n, {k: (list(v[0]), v[1]) for k, v in base.items()}


# ------------------------------------------------------------------------------------------------ utilidades de las etapas B-E
T_VUELO = 22                                   # frames de vuelo de un objeto lanzado (suelta -> impacto)
BASEM = {}                                     # nombre de bonobo -> (posicion, yaw) de reposo


def base_monos():
    B = monos()
    for nm, b in B.items():
        BASEM[nm] = (pos_mono(b, F0 - 1), yaw_mono(b, F0 - 1))
    return B


def hueso_alfred(f, hueso, cola=False):
    arm, root = rig_alfred()
    bpy.context.scene.frame_set(int(f))
    pb = arm.pose.bones[hueso]
    return arm.matrix_world @ (pb.tail if cola else pb.head)


def mano_mono(b, f, lado='l'):
    bpy.context.scene.frame_set(int(f))
    return hueso_mundo(b, ('left' if lado == 'l' else 'right') + 'hand', cola=False)


def sembrar_ult():
    """continuidad de eulers: parte de la pose real del frame F0-1 (hay vueltas de 2pi acumuladas)"""
    arm, root = rig_alfred()
    bpy.context.scene.frame_set(F0 - 1)
    for b in BONES_POSE:
        _ULT[(arm.name, b)] = arm.pose.bones[b].rotation_euler.copy()


def clon_palo(nombre):
    """copia vinculada de bm_stick_1 (mismo sprite, escala 0.68)"""
    if nombre in bpy.data.objects:
        return bpy.data.objects[nombre]
    o0 = bpy.data.objects['bm_stick_1']
    o = o0.copy()
    o.name = nombre
    o.animation_data_clear()
    for c in o0.users_collection:
        c.objects.link(o)
    o.scale = o0.scale
    return o


def tira(nm, f_rel, objetivo, lado='l'):
    """el bonobo nm lanza a 'objetivo' (punto de mundo) soltando en f_rel (animacion de lanza_bonobo adaptada a un destino cualquiera)"""
    b = monos()[nm]
    pos = Vector(BASEM[nm][0]); y0 = BASEM[nm][1]
    objetivo = Vector(objetivo)
    yb = yaw_hacia(pos, objetivo)
    dh = math.hypot(objetivo.x - pos.x, objetivo.y - pos.y); dz = pos.z + 1.4 - objetivo.z
    elev = max(-0.05, min(0.6, 0.5 - 0.9 * dz / (dh + dz)))
    s = 1 if lado == 'l' else -1
    bpose(b, f_rel - 20); broot(b, f_rel - 20, pos, y0)
    b_vigila(b, f_rel - 16, head=V(0, 1.0, -0.35 * dz / (dh + dz)))
    broot(b, f_rel - 16, pos, yb)
    b_levanta(b, f_rel - 9, lado, jaw=20); broot(b, f_rel - 9, pos, yb - 6 * s)
    b_levanta(b, f_rel - 4, lado, jaw=30, **{('la' if lado == 'l' else 'ra'): V(0.45 * s, -0.55, 0.8)}); broot(b, f_rel - 4, pos, yb - 12 * s)
    kw = {('la' if lado == 'l' else 'ra'): V(0.15 * s, 0.85, elev), ('lf' if lado == 'l' else 'rf'): V(0.05 * s, 0.95, elev - 0.12)}
    b_suelta(b, f_rel, lado, **kw); broot(b, f_rel, pos + V(0, 0, 0.12), yb + 10 * s)
    b_sigue(b, f_rel + 3, lado); broot(b, f_rel + 3, pos, yb + 6 * s)
    b_levanta(b, f_rel + 11, lado, la=V(0.3, 0.3, 0.2), ra=V(-0.3, 0.3, 0.2), jaw=35); broot(b, f_rel + 11, pos, yb)
    bpose(b, f_rel + 18); broot(b, f_rel + 18, pos, yb)
    return f_rel + 18


def vuela_a_alfred(obj, f_rel, nm, lado, f_imp, hueso='face_alfred', aterriza=None, n2=14, suelo=SUELO + 0.15):
    """el objeto sale de la mano del bonobo en f_rel, golpea el hueso de Alfred en f_imp y rebota hacia 'aterriza' (punto en el suelo)"""
    b = monos()[nm]
    mano = mano_mono(b, f_rel, lado)
    dest = hueso_alfred(f_imp, hueso)
    vuelo(obj, f_rel, mano, f_imp, dest, centro=hueso_alfred(f_imp, 'Spine1_alfred'))
    if aterriza is not None:
        vuelo(obj, f_imp, dest, f_imp + n2, aterriza, giro=(4.0, 2.0, 3.0), suelo=suelo, choca=False)
    return dest


def ocultar_hasta(obj, f_on, f_off=None):
    """oculto hasta f_on (y despues de f_off); borra las claves de visibilidad anteriores del objeto y sus hijos"""
    for o in [obj] + list(obj.children_recursive):
        ad = o.animation_data
        if ad and ad.action:
            for l in ad.action.layers:
                for s in l.strips:
                    for bag in s.channelbags:
                        for c in [c for c in bag.fcurves if c.data_path in ('hide_viewport', 'hide_render')]:
                            bag.fcurves.remove(c)
    esconder(obj, f_on, f_off)


# ------------------------------------------------------------------------------------------------ etapa B: palos a la cara y cae sentado
CARA = Vector((-77.7, 32.5, 13.6))                         # cara de Alfred de pie (hueso face_alfred)
HITS = [('A2', 552, 'l', (-76.1, 31.6)), ('A4', 572, 'r', (-75.9, 33.1)), ('A6', 592, 'l', (-76.3, 32.4))]   # (bonobo, suelta, brazo, donde cae el palo)
F_SIT = 622                                                # frame donde empieza a sentarse (indice 30 del clip sentarse_alfred)
PALOS = ['bm_stick_3', 'bm_stick_4', 'bm_stick_5']


def etapa_B():
    arm, root = rig_alfred(); B = base_monos()
    sembrar_ult()
    p_listo(F0); raiz(F0, C1, YAW)
    palos = [clon_palo(n) for n in PALOS]
    for nm, fr, lado, _ in HITS:                                              # 1) los bonobos lanzan
        tira(nm, fr, CARA, lado)
    for i, (nm, fr, lado, land) in enumerate(HITS):                           # 2) Alfred recibe: reaccion al instante del impacto segun masa*velocidad
        fi = fr + T_VUELO
        mano = mano_mono(B[nm], fr, lado)
        v = velocidad_golpe(mano, CARA, T_VUELO)
        p_listo(fi - 3); raiz(fi - 3, C1, YAW)
        reaccion(fi, v, MASA_OBJ['palo'], YAW, C1, D_CAB, D_LISTO, 18 if i < 2 else 8)
    clip = cargar_clip('sentarse_alfred.py')                                   # 3) tras el tercero cae sentado
    ff, _M = poner_clip(arm, root, clip, F_SIT, Ts=matriz(C1, YAW), vel=1.4, desde=30, hasta=56, solo=BONES_POSE)
    for b in BONES_POSE:
        _ULT[(arm.name, b)] = arm.pose.bones[b].rotation_euler.copy()
    G['sentado'] = ff
    for (nm, fr, lado, land), palo in zip(HITS, palos):                       # 4) vuelos (con Alfred ya animado)
        fi = fr + T_VUELO
        vuela_a_alfred(palo, fr, nm, lado, fi, 'face_alfred', aterriza=Vector((land[0], land[1], SUELO + 0.15)))
        ocultar_hasta(palo, fr)
    return ff


# ------------------------------------------------------------------------------------------------ bloqueo de las curvas de los bonobos (el usuario las bloquea; se abren solo para animar este bloque y se restauran)
LOCKF = r"C:\Users\user\AppData\Local\Temp\claude\C--Users-user-Desktop-Alfred-Animacion\652ab5d2-c4b2-402d-87db-bd00c559cad5\scratchpad\monos_locks.json"


def _acciones_monos():
    for nm, b in monos().items():
        for o in (b, _rig(b)):
            if o.animation_data and o.animation_data.action:
                yield o, o.animation_data.action


def desbloquear_monos():
    """guarda el estado de lock de cada curva de los bonobos y las desbloquea; devuelve cuantas estaban bloqueadas"""
    import os
    est = json.load(open(LOCKF)) if os.path.exists(LOCKF) else {}
    n = 0
    for o, a in _acciones_monos():
        for c in _fcs(a):
            k = '%s|%s|%d' % (o.name, c.data_path, c.array_index)
            est.setdefault(k, bool(c.lock))
            if c.lock:
                n += 1
            c.lock = False
    json.dump(est, open(LOCKF, 'w'))
    return n


def rebloquear_monos():
    """deja las curvas de los bonobos como estaban (las nuevas, bloqueadas)"""
    est = json.load(open(LOCKF))
    n = 0
    for o, a in _acciones_monos():
        for c in _fcs(a):
            c.lock = est.get('%s|%s|%d' % (o.name, c.data_path, c.array_index), True)
            n += c.lock
    return n


def reposo_monos():
    """claves de reposo de todos los bonobos en F0 y F1 (las de la etapa A no se insertaron por el bloqueo)"""
    for nm, b in monos().items():
        p, y = BASEM[nm]
        for f in (F0, F1):
            broot(b, f, p, y); bpose(b, f)


# ------------------------------------------------------------------------------------------------ etapa C: sentado les devuelve los palos
F_TOOLS = 645                                              # frame del indice 62 del clip sentado_tirar_herramientas_alfred (sentado, empieza a alcanzar hacia atras)
DEVUELVE = [(669, 683, 'A2'), (687, 701, 'A4')]            # (agarra, suelta, bonobo destino) de los dos primeros palos


def quitar_todo(obj):
    return quitar(obj, -10 ** 6, 10 ** 6)


def mano_agarra(f):
    """la mano (derecha o izquierda) mas baja en el frame f: la que agarra del suelo"""
    d = hueso_alfred(f, 'Rightelbow_alfred', cola=True); i = hueso_alfred(f, 'Leftelbow_alfred', cola=True)
    return ('Rightelbow_alfred', d) if d.z < i.z else ('Leftelbow_alfred', i)


def etapa_C():
    arm, root = rig_alfred(); B = monos()
    palos = [bpy.data.objects[n] for n in PALOS]
    clip = cargar_clip('sentado_tirar_herramientas_alfred.py')
    raiz(G['sentado'] + 2, C1, YAW)
    ff, _M = poner_clip(arm, root, clip, F_TOOLS, desde=62, hasta=121, solo=BONES_POSE, mover_root=False)
    raiz(F_TOOLS, C1, YAW); raiz(ff, C1, YAW)
    for b in BONES_POSE:
        _ULT[(arm.name, b)] = arm.pose.bones[b].rotation_euler.copy()
    G['tools_fin'] = ff
    info = {}
    for (fg, fr, nm), palo, (_n, f_rel0, lado, land) in zip(DEVUELVE, palos, HITS):
        hueso, p_agarra = mano_agarra(fg)
        suelo_p = Vector((p_agarra.x, p_agarra.y, SUELO + 0.15))
        quitar_todo(palo)                                                     # re-vuelo del palo: ahora cae donde la mano lo agarra
        vuela_a_alfred(palo, f_rel0, _n, lado, f_rel0 + T_VUELO, 'face_alfred', aterriza=suelo_p)
        for f in range(fg, fr + 1):                                           # lo lleva en la mano
            palo.location = hueso_alfred(f, hueso, cola=True)
            palo.keyframe_insert('location', frame=f)
        T = 24
        b = B[nm]
        mano = hueso_alfred(fr, hueso, cola=True)
        bpy.context.scene.frame_set(fr + T)
        centro = hueso_mundo(b, 'cube_r1', cola=False)
        vuelo(palo, fr, mano, fr + T, centro, suelo=SUELO + 0.15, centro=centro + Vector((0.0, 0.0, 0.0)))
        info[nm] = (hueso, [round(v, 2) for v in p_agarra], fg, fr, fr + T)
    return info


# ------------------------------------------------------------------------------------------------ utilidades del estudio (pollo y rata) y golpes sentado
import importlib.util
GEN = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones" + "\\"
_EST = {}
MASA_POLLO = 1.5
MASA_RATA = 0.3


def mod_estudio(k):
    if k not in _EST:
        p = {'chicken': "chicken_1/refinar/chicken_1_animation_studio/generate_slots.py", 'rat': "rat_1/refinar/rat_1_animation_studio/generate_slots_rat_1.py"}[k]
        spec = importlib.util.spec_from_file_location('est_' + k, GEN + p)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        _EST[k] = m
    return _EST[k]


def pts_estudio(lista, z=SUELO):
    return [{'index': i + 1, 'coordinates': {'x': float(x), 'y': float(y), 'z': float(z)}} for i, (x, y) in enumerate(lista)]


def camina_estudio(k, f0, lista, estilo='NORMAL', ejecutar=True):
    """cadena de pasos de 1 bloque con el estudio de k ('chicken'|'rat'); keyframea el root y los huesos; devuelve el frame final (o los frames del tramo si no se ejecuta)"""
    m = mod_estudio(k); P = pts_estudio(lista)
    ang = m._compute_direction_angle(P[0]['coordinates'], P[1]['coordinates']) if k == 'chicken' else 0
    code, fe = m.generate_caminar(1, f0, P, '2026-10-30', (0, 0, ang), estilo)
    if ejecutar:
        objs = ('chicken_1', 'Armature_chicken_1') if k == 'chicken' else ('rat_1', 'body1_1')
        previas = {n: (bpy.data.objects[n].animation_data.action if bpy.data.objects[n].animation_data else None) for n in objs}
        exec(code, {'__name__': '__main__'})
        for n in objs:                                              # el estudio crea sus propias acciones (las deja en una pista NLA): sus claves se pasan a la accion que ya tenia el objeto
            o = bpy.data.objects[n]
            ad = o.animation_data
            nuevas = []
            for tr in list(ad.nla_tracks):
                if tr.name.startswith('Slot_'):
                    nuevas += [s.action for s in tr.strips if s.action is not None]
                    ad.nla_tracks.remove(tr)
            if ad.action is not previas[n] and ad.action is not None:
                nuevas.append(ad.action)
            ad.action = previas[n]
            if not nuevas:
                continue
            datos = [(c.data_path, c.array_index, [(kp.co[0], kp.co[1]) for kp in c.keyframe_points]) for a_ in nuevas for c in _fcs(a_)]
            for path, idx, keys in datos:
                if path.startswith('hide'):
                    continue
                duenio, _, attr = path.rpartition('.')
                tgt = o.path_resolve(duenio) if duenio else o
                for f, v in keys:
                    getattr(tgt, attr)[idx] = v
                    tgt.keyframe_insert(attr, index=idx, frame=int(round(f)))
            for a_ in nuevas:
                bpy.data.actions.remove(a_)
    return fe


def seguir_mano_mono(obj, b, f0, f1, lado='l', off=(0, 0, 0)):
    for f in range(int(f0), int(f1) + 1):
        obj.location = mano_mono(b, f, lado) + Vector(off)
        obj.keyframe_insert('location', frame=f)


def yaw_keys(obj, f0, dz):
    """suma dz (rad) a la rotacion Z de las claves de obj desde f0 (para que el vuelo conserve el rumbo que traia)"""
    a = obj.animation_data.action
    for c in _fcs(a):
        if c.data_path == 'rotation_euler' and c.array_index == 2:
            for kp in c.keyframe_points:
                if kp.co[0] >= f0:
                    kp.co[1] += dz; kp.handle_left[1] += dz; kp.handle_right[1] += dz
            c.update()


def enderezar(obj, f_a, f_b, yaw):
    """de f_a a f_b la rotacion del objeto pasa a la vertical (X,Y multiplos de 2pi, Z=yaw cercano) y se queda asi"""
    sc = bpy.context.scene; sc.frame_set(int(f_a))
    r0 = Vector(obj.rotation_euler)
    t2 = 2 * math.pi
    rz = yaw + t2 * round((r0.z - yaw) / t2)
    fin = Vector((t2 * round(r0.x / t2), t2 * round(r0.y / t2), rz))
    for f in range(int(f_a), int(f_b) + 1):
        t = min(1.0, (f - f_a) / max(1, (f_b - f_a)))
        obj.rotation_euler = r0.lerp(fin, t * t * (3 - 2 * t))
        obj.keyframe_insert('rotation_euler', frame=f)


def golpe_sentado(fi, v, masa, dur=16):
    """Alfred SENTADO recibe un impacto en fi: columna y cuello se van en la direccion del golpe (masa*velocidad), rebotan en sentido contrario y vuelven (mismo perfil que reaccion)"""
    arm, root = rig_alfred(); sc = bpy.context.scene
    v = Vector(v); s = max(0.35, min(1.4, masa * v.length / 3.0)); u = v.normalized()
    th = math.radians(YAW)
    xl = Vector((math.cos(th), math.sin(th), 0)); yl = Vector((-math.sin(th), math.cos(th), 0))
    ux, uy, uz = u.dot(xl), u.dot(yl), u.z
    hz = Vector((u.x, u.y, 0)); hz = hz.normalized() if hz.length > 1e-6 else Vector((0, 0, 0))
    frames = {}
    for fr, k in _PERFIL:
        frames.setdefault(int(round(fi + fr * dur)), k)
    cadena = (('Spine_alfred', 0.30), ('Spine1_alfred', 0.35), ('Spine2_alfred', 0.35), ('Neck_alfred', 1.0))
    base = {}
    for f in frames:                                                              # linea base antes de tocar nada
        sc.frame_set(f); bpy.context.view_layer.update()
        base[f] = {b: (arm.pose.bones[b].matrix.to_quaternion() @ Vector((0, 1, 0))).normalized() for b, _g in cadena}
    for f, k in sorted(frames.items()):
        sc.frame_set(f); bpy.context.view_layer.update()
        for b, g in cadena:
            if b == 'Neck_alfred':
                off = Vector((0.8 * s * ux * k, (1.0 * s * uy - 0.55 * s * uz) * k, 0.0))
            else:
                off = Vector((0.45 * s * ux * k * g, 0.55 * s * uy * k * g, 0.0))
            apuntar(arm, b, (base[f][b] + off).normalized(), f=f)
        raiz(f, C1 + hz * (0.06 * s * k), YAW + 5.0 * s * ux * k)
    return max(frames)


# ------------------------------------------------------------------------------------------------ etapa D: el pollo cruza, Alfred lo agarra y lo lanza; A2 se lo devuelve
F_CH0 = 705                    # frame 0 del clip agarra_al_pollo_y_lo_lanza (Alfred sentado; agarra en el 7, suelta en el 17)
F_A2_SUELTA = 760              # A2 devuelve el pollo
CH_AT = {}                     # eventos del pollo (para la etapa final)


def etapa_D():
    arm, root = rig_alfred(); B = monos()
    ch = bpy.data.objects['chicken_1']; ach = bpy.data.objects['Armature_chicken_1']
    clip = cargar_clip('agarra_al_pollo_y_lo_lanza_al_creeper_parte7_alfred.py')
    sc = bpy.context.scene
    # 1) Alfred: el clip (13 huesos del cuerpo; el root fijo en C1)
    ff, _M = poner_clip(arm, root, clip, F_CH0, desde=0, hasta=19, solo=BONES_POSE, mover_root=False)
    raiz(F_CH0, C1, YAW); raiz(ff, C1, YAW)
    for b in BONES_POSE:
        _ULT[(arm.name, b)] = arm.pose.bones[b].rotation_euler.copy()
    # 2) el pollo en mundo segun el clip (agarrado por el cuello)
    R0 = mat(clip['root']['location'][0], clip['root']['rotation_euler'][0])
    Tm = matriz(C1, YAW) @ R0.inverted()
    co = clip['objetos']['chicken_1']

    def Mch(i):
        return Tm @ Matrix.LocRotScale(Vector(co['location'][i]), Quaternion(co['rotation_quaternion'][i]), Vector(co['scale'][i]))
    M0 = Mch(0)
    p0 = M0.translation; yaw0 = M0.to_euler('XYZ').z
    dx, dy = round(-math.sin(yaw0)), round(math.cos(yaw0))
    lista = [(p0.x - k * dx, p0.y - k * dy) for k in (3, 2, 1, 0)]          # camina 3 bloques hasta quedar a la altura de su mano
    fe = camina_estudio('chicken', 0, lista, 'NORMAL', ejecutar=False)
    f_w = F_CH0 - fe
    ocultar_hasta(ch, f_w - 1)
    camina_estudio('chicken', f_w, lista, 'NORMAL')
    sc.frame_set(F_CH0)
    prev = Euler(tuple(ch.rotation_euler), 'XYZ')
    for i in range(0, 17):
        loc, q, _s = Mch(i).decompose(); e = q.to_euler('XYZ', prev); prev = e
        ch.location = loc; ch.rotation_euler = e
        ch.keyframe_insert('location', frame=F_CH0 + i); ch.keyframe_insert('rotation_euler', frame=F_CH0 + i)
    rb = co['rig_bones']
    for i in list(range(5, 17)) + [19]:
        for bn, dat in rb.items():
            pb = ach.pose.bones.get(bn)
            if pb is None:
                continue
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = dat['rotation_euler'][i]
            pb.keyframe_insert('rotation_euler', frame=F_CH0 + i)
    # 3) A2 lo recibe y se lo devuelve a Alfred
    f_r = F_CH0 + 17; f_c = f_r + 24
    cara_s = hueso_alfred(ff, 'face_alfred')
    tira('A2', F_A2_SUELTA, cara_s, 'l')
    a2 = B['A2']
    yaw17 = Mch(17).to_euler('XYZ').z
    p17 = Mch(17).translation
    mano_c = mano_mono(a2, f_c, 'l')
    vuelo(ch, f_r, p17, f_c, mano_c, giro=(0.0, 0.0, 0.0))
    seguir_mano_mono(ch, a2, f_c, F_A2_SUELTA, 'l', off=(0, 0, -0.35))
    f_i2 = F_A2_SUELTA + T_VUELO
    mano_s = mano_mono(a2, F_A2_SUELTA, 'l') + Vector((0, 0, -0.35))
    v = velocidad_golpe(mano_s, cara_s, T_VUELO)
    golpe_sentado(f_i2, v, MASA_POLLO, 16)
    dest = hueso_alfred(f_i2, 'face_alfred')
    vuelo(ch, F_A2_SUELTA, mano_s, f_i2, dest, giro=(0.0, 0.0, 0.0), centro=hueso_alfred(f_i2, 'Spine1_alfred'))
    land = Vector((-79.6, 31.4, SUELO))
    f_fin = vuelo(ch, f_i2, dest, f_i2 + 14, land, giro=(0.0, 0.0, 0.0), suelo=SUELO, choca=False)
    yaw_keys(ch, f_r, yaw17)
    CH_AT.update(dict(f_w=f_w, f_r=f_r, f_c=f_c, f_i2=f_i2, f_fin=f_fin, yaw=yaw17, land=tuple(land), alfred_fin=ff))
    return dict(CH_AT)


# ------------------------------------------------------------------------------------------------ etapa E: A4 lanza la rata, Alfred se levanta y da el paso; cierres
RAT_REL = 778                  # A4 suelta la rata (impacto 22 f despues)
F_UP = 813                     # empieza a levantarse (indice 0 de se_levanta_cojeando_parte7_alfred)
S6_A3 = Vector((-73.5, 18.5, 18.0))


def saltar_mono(b, f0, dur, p_ini, p_fin, yaw_fin, alto=2.0):
    """salto de copa en copa (como saltar() de bonobos_madera_main): agacha, vuela en parabola, cae"""
    p_ini = Vector(p_ini); p_fin = Vector(p_fin)
    yv = yaw_hacia(p_ini, p_fin)
    bpose(b, f0 - 7); broot(b, f0 - 7, p_ini, yaw_mono(b, f0 - 8))
    b_agacha(b, f0 - 3); broot(b, f0 - 3, p_ini, yv)
    for i in range(dur + 1):
        t = i / dur
        broot(b, f0 + i, p_ini.lerp(p_fin, t) + Vector((0, 0, alto * 4 * t * (1 - t))), yv + (yaw_fin - yv) * max(0.0, t - 0.6) / 0.4)
    b_vuela(b, f0 + 2); b_vuela(b, f0 + dur - 2); b_cae(b, f0 + dur); bpose(b, f0 + dur + 7)


def regreso(nm, f):
    b = monos()[nm]; p, y = BASEM[nm]
    broot(b, f, p, y); bpose(b, f)


def pos_obj(obj, f):
    bpy.context.scene.frame_set(int(f))
    return Vector(obj.matrix_world.translation)


def etapa_E():
    arm, root = rig_alfred(); B = monos()
    rat = bpy.data.objects['rat_1']; arat = bpy.data.objects['body1_1']; ch = bpy.data.objects['chicken_1']
    # 1) la rata: A4 la lanza a Alfred sentado
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
    f_i = RAT_REL + T_VUELO
    mano = mano_mono(a4, RAT_REL, 'r') + Vector((0, 0, -0.15))
    v = velocidad_golpe(mano, cara_s, T_VUELO)
    golpe_sentado(f_i, v, MASA_RATA, 12)
    dest = hueso_alfred(f_i, 'face_alfred')
    vuelo(rat, RAT_REL, mano, f_i, dest, giro=(0.0, 0.0, 0.0), centro=hueso_alfred(f_i, 'Spine1_alfred'))
    f_r_fin = vuelo(rat, f_i, dest, f_i + 14, Vector((-79.0, 33.3, SUELO)), giro=(0.0, 0.0, 0.0), suelo=SUELO, choca=False)
    yaw_keys(rat, RAT_REL, yaw_r)
    # 2) pollo y rata se van caminando (estudio, 1 bloque)
    pc = pos_obj(ch, CH_AT['f_fin']); pr = pos_obj(rat, f_r_fin)
    f_w_c = CH_AT['f_fin'] + 3; f_w_r = f_r_fin + 3
    camina_estudio('chicken', f_w_c, [(pc.x, pc.y), (pc.x - 1.0, pc.y)], 'NORMAL')
    camina_estudio('rat', f_w_r, [(pr.x, pr.y), (pr.x - 1.0, pr.y)], 'NORMAL')
    # 3) Alfred se levanta y da un paso a RS
    clip = cargar_clip('se_levanta_cojeando_parte7_alfred.py')
    ff, _M = poner_clip(arm, root, clip, F_UP, vel=1.4, desde=0, hasta=30, solo=BONES_POSE, mover_root=False)
    raiz(F_UP, C1, YAW); raiz(ff, C1, YAW)
    for b in BONES_POSE:
        _ULT[(arm.name, b)] = arm.pose.bones[b].rotation_euler.copy()
    fin = caminar_ruta(ff + 1, [tuple(C1), tuple(RS)], yaw_ini=YAW, yaw_fin=YAW)
    for b in BONES_POSE:
        _ULT[(arm.name, b)] = arm.pose.bones[b].rotation_euler.copy()
    p_listo(fin + 8); raiz(fin + 8, RS, YAW)
    p_listo(F1); raiz(F1, RS, YAW)
    # 4) A3 salta a S6 (la fiesta final lo espera alli) y los bonobos vuelven a su sitio
    a3 = B['A3']
    saltar_mono(a3, 818, 14, BASEM['A3'][0], S6_A3, 11.0)
    regreso('A3', 845)
    for nm, f in (('A6', 592 + 18 + 30), ('A2', F_A2_SUELTA + 18 + 30), ('A4', RAT_REL + 18 + 30)):
        regreso(nm, f)
    return dict(rat_imp=f_i, rat_fin=f_r_fin, up_fin=ff, paso_fin=fin)


# ------------------------------------------------------------------------------------------------ etapa F: Alfred desde que lanza el pollo hasta que da el paso (se rehace de forma idempotente)
F_CH_IMP = 782                                              # impacto del pollo (A2 lo devuelve; suelta en F_A2_SUELTA)
F_REPOSO1, F_REPOSO2 = 736, 778                             # sentado en reposo entre el lanzamiento del pollo y los golpes


def etapa_F():
    arm, root = rig_alfred(); B = monos()
    quitar(arm, 725, F1); quitar(root, 725, F1); quitar(arm, F1 + 2, F1 + 2); quitar(root, F1 + 2, F1 + 2)
    # reposo sentado (pose final de sentarse_alfred) entre el lanzamiento del pollo y los golpes
    sent = cargar_clip('sentarse_alfred.py')
    for f in (F_REPOSO1, F_REPOSO2):
        poner_clip(arm, root, sent, f, desde=56, hasta=56, solo=BONES_POSE, mover_root=False)
        raiz(f, C1, YAW)
    for b in BONES_POSE:
        _ULT[(arm.name, b)] = arm.pose.bones[b].rotation_euler.copy()
    cara_s = hueso_alfred(724, 'face_alfred')
    # golpes recibidos sentado: pollo (A2) y rata (A4)
    v_p = velocidad_golpe(mano_mono(B['A2'], F_A2_SUELTA, 'l') + Vector((0, 0, -0.35)), cara_s, T_VUELO)
    golpe_sentado(F_CH_IMP, v_p, MASA_POLLO, 16)
    v_r = velocidad_golpe(mano_mono(B['A4'], RAT_REL, 'r') + Vector((0, 0, -0.15)), cara_s, T_VUELO)
    golpe_sentado(RAT_REL + T_VUELO, v_r, MASA_RATA, 12)
    # se levanta (20 f) y da un paso a RS
    clip = cargar_clip('se_levanta_cojeando_parte7_alfred.py')
    ff, _M = poner_clip(arm, root, clip, F_UP, vel=1.5, desde=0, hasta=30, solo=BONES_POSE, mover_root=False)
    raiz(F_UP, C1, YAW); raiz(ff, C1, YAW)
    for b in BONES_POSE:
        _ULT[(arm.name, b)] = arm.pose.bones[b].rotation_euler.copy()
    fin = caminar_ruta(int(ff) + 1, [tuple(C1), tuple(RS)], yaw_ini=YAW, yaw_fin=YAW)
    for b in BONES_POSE:
        _ULT[(arm.name, b)] = arm.pose.bones[b].rotation_euler.copy()
    p_listo(int(fin) + 6); raiz(int(fin) + 6, RS, YAW)
    p_listo(F1); raiz(F1, RS, YAW)
    return dict(up_fin=ff, paso_fin=fin)
