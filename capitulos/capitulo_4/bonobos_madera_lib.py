# -*- coding: utf-8 -*-
"""Utilidades para la animacion 'Alfred talando arboles vs bonobos' (base_tarde con las ranas.blend).
Reproduce clips de `codigos de animacion/alfred` (formato PAYLOAD y Mixamo KEYFRAME_DATA) en UNA sola accion con root encadenado, mueve el root a mano (caminar), y da poses FK propias.
Se usa con: exec(open(ruta).read()) dentro de Blender (escena viva). 24 fps."""
import bpy, math, os, importlib.util
from mathutils import Matrix, Vector, Euler, Quaternion

BIB = r"C:\Users\user\Desktop\Alfred_Animacion\codigos de animacion\alfred"
_cache = {}


def cargar_clip(nombre):
    """-> dict(n, bones{nombre:{canal:[valor por frame]}}, root{location,rotation_euler}|None, objetos)"""
    if nombre in _cache:
        return _cache[nombre]
    ruta = os.path.join(BIB, nombre)
    spec = importlib.util.spec_from_file_location('clip_%d' % abs(hash(nombre)), ruta)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    if hasattr(m, 'PAYLOAD') and isinstance(m.PAYLOAD, dict) and 'bones' in m.PAYLOAD:
        P = m.PAYLOAD
        n = None
        for ch in P['bones'].values():
            for v in ch.values():
                n = len(v)
                break
            break
        c = {'n': n, 'bones': P['bones'], 'root': P.get('root') if isinstance(P.get('root'), dict) and 'location' in P.get('root', {}) else None,
             'objetos': P.get('objetos', {}), 'nombre': nombre}
    else:
        K = m.KEYFRAME_DATA
        n = max(max(d) for d in K.values())
        bones = {}
        for b, d in K.items():
            lst = []
            ks = sorted(d)
            for f in range(1, n + 1):
                if f in d:
                    lst.append(list(d[f]))
                else:                       # hueco: se repite el anterior
                    lst.append(lst[-1] if lst else list(d[ks[0]]))
            bones[b] = {'rotation_euler': lst}
        c = {'n': n, 'bones': bones, 'root': None, 'objetos': {}, 'nombre': nombre}
    _cache[nombre] = c
    return c


def mat(l, e):
    return Matrix.LocRotScale(Vector(l), Euler(e, 'XYZ').to_quaternion(), Vector((1, 1, 1)))


def rig_alfred():
    return bpy.data.objects['Armature'], bpy.data.objects['alfred']


def accion_nueva(obj, nombre):
    obj.animation_data_create()
    a = bpy.data.actions.new(nombre)
    obj.animation_data.action = a
    return a


def key_huesos(arm, bones, i, ff, solo=None):
    for name, chans in bones.items():
        if solo is not None and name not in solo:
            continue
        pb = arm.pose.bones.get(name)
        if pb is None:
            continue
        pb.rotation_mode = 'XYZ'
        for ch, vals in chans.items():
            if i < len(vals):
                setattr(pb, ch, vals[i])
                pb.keyframe_insert(ch, frame=ff, group=name)


def poner_clip(arm, root, clip, f0, Ts=None, vel=1.0, desde=0, hasta=None, solo=None, mover_root=True):
    """Pone el clip en frames f0..; Ts = matriz de mundo del root al INICIO del clip (None = la actual). vel>1 = mas rapido.
    desde/hasta recortan por indice de frame del clip (0-based, hasta inclusive). Devuelve (f_final, matriz_root_final)."""
    n = clip['n']
    hasta = n - 1 if hasta is None else hasta
    R0 = mat(clip['root']['location'][desde], clip['root']['rotation_euler'][desde]) if clip['root'] else Matrix.Identity(4)
    if Ts is None:
        Ts = root.matrix_world.copy()
    T = Ts @ R0.inverted()
    prev = Euler(tuple(root.rotation_euler), 'XYZ')
    Mfin = Ts
    ff = f0
    for i in range(desde, hasta + 1):
        ff = f0 + (i - desde) / vel
        key_huesos(arm, clip['bones'], i, ff, solo)
        if clip['root'] and mover_root:
            M = T @ mat(clip['root']['location'][i], clip['root']['rotation_euler'][i])
            loc, q, _s = M.decompose()
            eul = q.to_euler('XYZ', prev); prev = eul
            root.location = loc; root.rotation_euler = eul
            root.keyframe_insert('location', frame=ff); root.keyframe_insert('rotation_euler', frame=ff)
            Mfin = M
        elif not clip['root'] and mover_root:
            root.keyframe_insert('location', frame=ff); root.keyframe_insert('rotation_euler', frame=ff)
    return ff, Mfin


def poner_root(root, f, loc, yaw_deg=None):
    root.location = loc
    if yaw_deg is not None:
        root.rotation_euler = (0, 0, math.radians(yaw_deg))
    root.keyframe_insert('location', frame=f)
    root.keyframe_insert('rotation_euler', frame=f)


def matriz(loc, yaw_deg):
    return Matrix.LocRotScale(Vector(loc), Euler((0, 0, math.radians(yaw_deg)), 'XYZ').to_quaternion(), Vector((1, 1, 1)))


def lineal(obj, solo_constantes=('influence', 'hide')):
    """interpolacion LINEAL en todas las fcurves de las acciones de obj (influence/hide constantes)"""
    ad = obj.animation_data
    if not ad or not ad.action:
        return
    a = ad.action
    if hasattr(a, 'fcurves'):
        fcs = list(a.fcurves)
    else:
        fcs = [c for l in a.layers for s in l.strips for b in s.channelbags for c in b.fcurves]
    for c in fcs:
        const = any(k in c.data_path for k in solo_constantes)
        for k in c.keyframe_points:
            k.interpolation = 'CONSTANT' if const else 'LINEAR'


def pose(arm, f, rots, cual=None):
    """rots: {hueso: (x,y,z) en radianes}; deja el resto como esta."""
    for name, r in rots.items():
        pb = arm.pose.bones.get(name)
        if pb is None:
            raise KeyError(name)
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = r
        pb.keyframe_insert('rotation_euler', frame=f, group=name)


# ------------------------------------------------------------------ FK por direccion
def apuntar(rig, hueso, d, giro_deg=0.0, f=None):
    """Gira el hueso (ya con su padre en la pose actual) para que su eje (cabeza->cola) apunte a la direccion d, dada en el espacio LOCAL del armature
    (el del personaje en reposo: x lado, y adelante, z arriba). El giro minimo desde la direccion actual; giro_deg gira ademas el hueso sobre su propio eje.
    Con f deja keyframe de rotation_euler. Llamar padre antes que hijo. La escala del hueso se fija en 1 (sin deformacion)."""
    pb = rig.pose.bones[hueso]
    pb.rotation_mode = 'XYZ'
    pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    M = pb.matrix.copy()                                   # espacio del armature
    head = M.translation.copy()
    q0 = M.to_quaternion()
    y = (q0 @ Vector((0, 1, 0))).normalized()
    d = Vector(d).normalized()
    q = y.rotation_difference(d) @ q0
    if giro_deg:
        q = Quaternion(d, math.radians(giro_deg)) @ q
    pb.matrix = Matrix.LocRotScale(head, q, Vector((1, 1, 1)))
    pb.scale = (1, 1, 1)
    if f is not None:
        bpy.context.view_layer.update()
        pb.keyframe_insert('rotation_euler', frame=f, group=hueso)
        pb.keyframe_insert('location', frame=f, group=hueso)


def reset_pose(rig, solo=None):
    for pb in rig.pose.bones:
        if solo is not None and pb.name not in solo:
            continue
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()


def desenrollar(obj):
    """evita giros de 360 grados: en cada fcurve de rotation_euler los valores sucesivos no difieren mas de pi (se suman/restan vueltas completas)"""
    ad = obj.animation_data
    if not ad or not ad.action:
        return
    a = ad.action
    fcs = list(a.fcurves) if hasattr(a, 'fcurves') else [c for l in a.layers for s in l.strips for b in s.channelbags for c in b.fcurves]
    for c in fcs:
        if not c.data_path.endswith('rotation_euler'):
            continue
        pts = sorted(c.keyframe_points, key=lambda k: k.co[0])
        prev = None
        for k in pts:
            v = k.co[1]
            if prev is not None:
                while v - prev > math.pi:
                    v -= 2 * math.pi
                while v - prev < -math.pi:
                    v += 2 * math.pi
                d = v - k.co[1]
                if d:
                    k.co[1] = v; k.handle_left[1] += d; k.handle_right[1] += d
            prev = k.co[1]
        c.update()
