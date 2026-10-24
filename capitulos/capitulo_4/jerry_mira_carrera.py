# -*- coding: utf-8 -*-
"""Mientras Alfred corre en circulos con la arana en la cara (alfred_corre_circulos.py, desde F_INI), Jerry sigue atentamente su recorrido:
la cabeza (spine_1 + scull_1, capa NLA ADD `Jerry_mira_carrera`) apunta a la cara de Alfred con un pequeno retraso y, cuando el giro pasa de
LIM_CABEZA grados, gira el cuerpo (claves de rotacion del empty `jerry` sobre su sitio, mas lento). Alfred empieza al noreste y da vueltas
al oeste, por detras de Jerry, asi que Jerry se da la vuelta siguiendolo (antihorario).
Factores medidos en el rig (f550): scull_1 Z +0.2 rad -> -8 grados de giro de la cabeza; spine_1 Z +0.2 -> -11.2; spine_1 X +0.2 -> -11.2 de inclinacion.
Uso (Blender):  exec(open(r"...\\jerry_mira_carrera.py", encoding="utf8").read()); construir()      (repetible)
"""
import bpy, math
from mathutils import Vector, Quaternion

F_INI, ENTRA = 556, 8
LIM_CABEZA = 45.0          # grados que gira la cabeza antes de que gire el cuerpo
RETRASO_CABEZA, RETRASO_CUERPO = 0.45, 0.12      # filtros por frame (1 = sin retraso)
K_YAW = {"spine_1": -0.98, "scull_1": -0.70}     # grados de giro de la cabeza por grado de rotacion Z del hueso (medido)
K_PITCH = -0.98                                   # spine_1 X
PISTA = "Jerry_mira_carrera"


def _cabeza(rig):
    W = rig.matrix_world; h = W @ rig.pose.bones["scull"].head; t = W @ rig.pose.bones["jaw_top"].tail
    return h, t - h


def construir():
    sc = bpy.context.scene; fin = sc.frame_end; f_act = sc.frame_current
    rig = bpy.data.objects["Dog_001_rig"]; root = bpy.data.objects["jerry"]; alf = bpy.data.objects["Armature"]
    ad = rig.animation_data
    for t in list(ad.nla_tracks):
        if t.name == PISTA:
            a = [s.action for s in t.strips]; ad.nla_tracks.remove(t)
            for x in a:
                if x and x.users == 0: bpy.data.actions.remove(x)
    # claves del empty desde F_INI: se rehacen
    ra = root.animation_data.action
    for lay in ra.layers:
        for s in lay.strips:
            for cb in s.channelbags:
                for fc in cb.fcurves:
                    if fc.data_path == "rotation_quaternion":
                        for kp in reversed(list(fc.keyframe_points)):
                            if kp.co[0] > F_INI: fc.keyframe_points.remove(kp)
    sc.frame_set(F_INI)
    h0, f0 = _cabeza(rig); P = root.matrix_world.translation.copy(); q0 = root.rotation_quaternion.copy()
    yaw0 = math.degrees(math.atan2(f0.y, f0.x)); pitch0 = math.degrees(math.atan2(f0.z, f0.to_2d().length))
    psi_prev = None; body = 0.0; head_yaw = 0.0; head_pitch = 0.0
    canales = {}; claves_root = []
    for f in range(F_INI, fin + 1):
        sc.frame_set(f)
        objetivo = alf.matrix_world @ alf.pose.bones["face_alfred"].head
        hp = P + Quaternion((0, 0, 1), math.radians(body)) @ (h0 - P)            # cabeza de Jerry con el cuerpo ya girado
        d = objetivo - hp
        psi = math.degrees(math.atan2(d.y, d.x))
        if psi_prev is not None:
            while psi - psi_prev > 180: psi -= 360
            while psi - psi_prev < -180: psi += 360
        psi_prev = psi
        quiero = psi - yaw0                                                        # giro total respecto de donde mira ahora
        body += (quiero - body) * RETRASO_CUERPO if abs(quiero - body) > LIM_CABEZA * 0.6 else 0.0
        body = max(quiero - LIM_CABEZA, min(quiero + LIM_CABEZA, body))
        head_yaw += ((quiero - body) - head_yaw) * RETRASO_CABEZA
        elev = math.degrees(math.atan2(d.z, d.to_2d().length))
        head_pitch += ((elev - pitch0) - head_pitch) * RETRASO_CABEZA
        u = min(1.0, (f - F_INI) / ENTRA); u = u * u * (3 - 2 * u)
        reparto = {"spine_1": 0.5, "scull_1": 0.5}
        for b, k in K_YAW.items():
            canales.setdefault((f'pose.bones["{b}"].rotation_euler', 2), []).append((f, u * math.radians(head_yaw * reparto[b] / k)))
        canales.setdefault(('pose.bones["spine_1"].rotation_euler', 0), []).append((f, u * math.radians(head_pitch / K_PITCH)))
        q = Quaternion((0, 0, 1), math.radians(body)) @ q0
        if claves_root and q.dot(claves_root[-1][1]) < 0: q.negate()
        claves_root.append((f, q))
    act = bpy.data.actions.get(PISTA)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(PISTA); slot = act.slots.new(rig.id_type, rig.name)
    cb = act.layers.new("Layer").strips.new(type='KEYFRAME').channelbags.new(slot)
    for (ruta, i), cl in canales.items():
        fc = cb.fcurves.new(ruta, index=i); fc.keyframe_points.add(len(cl))
        for kp, (f, v) in zip(fc.keyframe_points, cl): kp.co = (f, v); kp.interpolation = 'LINEAR'
        fc.update()
    tr = ad.nla_tracks.new(); tr.name = PISTA
    st = tr.strips.new(PISTA, F_INI, act); st.blend_type = 'ADD'; st.extrapolation = 'HOLD_FORWARD'
    try: st.action_slot = slot
    except Exception: pass
    for f, q in claves_root:
        root.rotation_quaternion = q; root.keyframe_insert("rotation_quaternion", frame=f)
    sc.frame_set(f_act)
    return {"giro_cuerpo_final": round(claves_root[-1][1].to_euler().z * 57.3, 1), "frames": (F_INI, fin)}
