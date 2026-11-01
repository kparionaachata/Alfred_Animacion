# -*- coding: utf-8 -*-
# Mirada de los monos al lanzar: cabeza y pupilas siguen el destino (Alfred antes de soltar) y el objeto en vuelo.
import bpy, math
from mathutils import Vector, Matrix, Quaternion, Euler

SC = bpy.context.scene
LIM = math.radians(65)


def fcs(a):
    return [c for l in a.layers for s in l.strips for b in s.channelbags for c in b.fcurves]


def mirada(i, R, f1, obj_name, P1, TC=None):
    raiz = bpy.data.objects['bonobo_adulto_1' if i == 0 else 'bonobo_adulto_1.%03d' % i]
    rig = [c for c in raiz.children if c.type == 'ARMATURE'][0]
    S = '_' + [b.name for b in rig.data.bones if b.name.startswith('head_')][0][5:]
    obj = bpy.data.objects[obj_name]
    P1 = Vector(P1)
    ph = rig.pose.bones['head' + S]
    pupilas = [rig.pose.bones[l + 'pupil' + S] for l in ('left', 'right')]
    # ejes de reposo en el marco del hueso de la cabeza
    Mrest = ph.bone.matrix_local.to_3x3().inverted()
    f_loc = Mrest @ Vector((0, 1, 0))      # adelante de la cara
    l_loc = Mrest @ Vector((1, 0, 0))      # izquierda del mono
    u_loc = Mrest @ Vector((0, 0, 1))
    ini, fin = R - 34, f1 + 26
    frames = sorted(set(list(range(ini, fin + 1, 2)) + list(range(R - 26, R + 11)) + [R, f1]))
    datos = []
    for f in frames:
        SC.frame_set(f)
        bpy.context.view_layer.update()
        q_orig = ph.rotation_euler.copy().to_quaternion()
        obj_pos = obj.matrix_world.translation.copy()
        t_mundo = (obj_pos if (TC is not None and f < TC) or f >= R else P1)
        ph.rotation_euler = (0, 0, 0)
        bpy.context.view_layer.update()
        M0 = ph.matrix.copy()
        head = M0.translation.copy()
        t_arm = rig.matrix_world.inverted() @ t_mundo
        t_dir = (t_arm - head).normalized()
        f0 = (M0.to_3x3() @ f_loc).normalized()
        qd = f0.rotation_difference(t_dir)
        ang = qd.angle
        if ang > LIM:
            qd = Quaternion().slerp(qd, LIM / ang)
        qn = qd @ M0.to_quaternion()
        # el hueso queda con su posicion; la rotacion local = respecto a la pose sin rotar
        ph.matrix = Matrix.LocRotScale(head, qn, Vector((1, 1, 1)))
        bpy.context.view_layer.update()
        q_track = ph.rotation_euler.copy().to_quaternion()
        # peso: sube antes de armar el brazo, sigue hasta despues del impacto y vuelve suave a la pose
        if f <= R - 24:
            w = max(0.0, (f - (R - 34)) / 10.0)
        elif f <= f1 + 12:
            w = 1.0
        else:
            w = max(0.0, 1.0 - (f - (f1 + 12)) / 14.0)
        q = q_orig.slerp(q_track, w)
        # residuo para las pupilas (en el marco de la cabeza final)
        Mh = ph.matrix.to_3x3()
        td = (t_arm - ph.matrix.translation).normalized()
        lat = (Mh @ l_loc).normalized(); up = (Mh @ u_loc).normalized()
        rl, rv = td.dot(lat), td.dot(up)
        datos.append((f, q, rl * w, rv * w))
    # quitar keys viejas de la cabeza y las pupilas en el rango y escribir las nuevas
    a = rig.animation_data.action
    nombres = ['head' + S] + ['%spupil%s' % (l, S) for l in ('left', 'right')]
    for c in fcs(a):
        for n in nombres:
            if c.data_path.startswith('pose.bones["%s"]' % n) and (c.data_path.endswith('rotation_euler') if n == nombres[0] else c.data_path.endswith('location')):
                for kp in reversed(list(c.keyframe_points)):
                    if ini - 0.5 <= kp.co[0] <= fin + 0.5:
                        c.keyframe_points.remove(kp)
    prev = None
    for f, q, rl, rv in datos:
        e = q.to_euler('XYZ', prev) if prev is not None else q.to_euler('XYZ')
        prev = e
        ph.rotation_euler = e
        ph.keyframe_insert('rotation_euler', frame=f, group=ph.name)
        for pp in pupilas:
            off = pp.bone.matrix_local.to_3x3().inverted() @ Vector((rl * 0.012, 0, rv * 0.012))
            pp.location = off
            pp.keyframe_insert('location', frame=f, group=pp.name)
    SC.frame_set(1)
    return len(datos)
