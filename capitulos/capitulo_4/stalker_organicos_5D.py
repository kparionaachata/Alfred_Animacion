# -*- coding: utf-8 -*-
"""alfred_cueva_5D.blend: filtros organicos de the_stalker_1 (armature torso_1) del frame 1 al final: respiracion del pecho y la columna (el ritmo y la amplitud suben al correr y al gatear y se
vuelven profundos al quedarse observando el pico), micro-movimiento de cuello y cabeza y un balanceo suave de los tentaculos del pecho. Se SUMAN por frame a las claves de rotacion_quaternion
(delta a la derecha: q @ dq); los deltas se guardan en organicos_cueva5D_stalker.json y se quitan antes de volver a aplicar (repetible; si se regenera la animacion de la criatura: aplicar(quitar=True) antes).
Alfred y Jerry (quietos en la salida): aplicar_alfred_jerry() con las formulas de organicos_parpadeos_cueva5A.py.
Requiere fk_clearance.py ejecutado (CAD, KEYS, _q, preparar, indexar_claves).   Uso: aplicar(); aplicar(quitar=True)"""
import bpy, math, json, os
from mathutils import Euler, Quaternion

CARPETA = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/"
F_CORRE, F_GATEA, F_LLEGA, F_ARRIBA0 = 458, 686, 891, 975


def _ss(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _ruido(f, freq, seed, dim=0):
    v = math.sin(f * freq * 1.3 + seed * 7.3 + dim * 3.7) + math.sin(f * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5 + math.sin(f * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25
    return v / 1.75


def _ritmo(fr):
    """(ciclos por frame, amplitud relativa, peso de gateo/observacion): camina suave, corre jadeando, gatea con fuerza y al llegar jadea unos frames y se calma en respiraciones profundas"""
    w = 0.018 + 0.022 * _ss((fr - (F_CORRE - 20)) / 40.0) + 0.016 * _ss((fr - (F_GATEA - 20)) / 40.0)
    jad = _ss((fr - F_LLEGA) / 6.0) * (1.0 - _ss((fr - (F_LLEGA + 20)) / 60.0))              # recien llegado: sigue jadeando y se va calmando
    w = w * (1.0 - _ss((fr - F_LLEGA) / 6.0)) + (0.014 + 0.040 * jad) * _ss((fr - F_LLEGA) / 6.0)
    a = 1.0 + 0.5 * _ss((fr - (F_CORRE - 20)) / 40.0) + 0.3 * _ss((fr - (F_GATEA - 20)) / 40.0)
    a = a * (1.0 - _ss((fr - F_LLEGA) / 6.0)) + (1.1 + 0.5 * jad + 0.5 * _ss((fr - F_LLEGA - 40) / 40.0) * (1.0 - _ss((fr - F_ARRIBA0) / 30.0))) * _ss((fr - F_LLEGA) / 6.0)
    plantada = _ss((fr - (F_GATEA - 10)) / 20.0)                                              # a cuatro patas las manos estan plantadas: el tronco se mueve menos y trabajan cuello y cabeza
    return w, a, plantada


def _onda(fase):
    """inspiracion rapida y espiracion lenta, con un pequeno sostenido arriba"""
    return math.sin(fase + 0.55 * math.sin(fase))


def _deltas(bones, fin):
    D = {}
    fase = 0.0
    resp = {}
    for fr in range(1, fin + 1):
        w, a, pl = _ritmo(fr)
        fase += 2 * math.pi * w * (1.0 + 0.18 * _ruido(fr, 0.011, 5))                          # el ritmo no es perfectamente regular
        resp[fr] = (_onda(fase), a * (1.0 + 0.22 * _ruido(fr, 0.013, 17)), _onda(fase - 0.6), pl)
    for fr in range(1, fin + 1):
        s, a, s2, pl = resp[fr]
        t = 1.0 - 0.45 * pl
        for n, ax, amp in (("chest_1", 0, 0.075 * t), ("spine_1", 0, 0.040 * t), ("neck_1", 0, 0.028), ("head_1", 0, 0.018)):
            D.setdefault(n, {}).setdefault(fr, [0.0, 0.0, 0.0])[ax] += amp * a * s
        D["chest_1"][fr][2] += 0.35 * 0.075 * t * a * s2                                      # las costillas se abren hacia los lados al inspirar
        D["chest_1"][fr][1] += 0.015 * a * _ruido(fr, 0.02, 3)                                   # torsion leve irregular
        D["spine_1"][fr][2] += 0.012 * a * _ruido(fr, 0.017, 9)
        for ax in range(3):
            D.setdefault("neck_1", {}).setdefault(fr, [0.0, 0.0, 0.0])[ax] += 0.014 * _ruido(fr, 0.05, 11, ax)
            D.setdefault("head_1", {}).setdefault(fr, [0.0, 0.0, 0.0])[ax] += 0.018 * _ruido(fr, 0.06, 29, ax)
        for n, sg in (("upper_arm.L_1", 1.0), ("upper_arm.R_1", -1.0)):                       # los hombros suben al inspirar (solo cuando las manos no estan plantadas)
            D.setdefault(n, {}).setdefault(fr, [0.0, 0.0, 0.0])[2] += sg * 0.05 * a * s * (1.0 - pl)
        for n in ("jaw_1", "neck_front_1"):                                                     # la mandibula se entreabre al espirar
            D.setdefault(n, {}).setdefault(fr, [0.0, 0.0, 0.0])[0] += SIGNO_MANDIBULA * 0.035 * a * max(0.0, -s)
    return D


SIGNO_MANDIBULA = -1.0                      # -X baja la punta de la mandibula (comprobado con la FK)


def _asegurar_fcurves(nombres, fin):
    """huesos sin claves de rotacion (p. ej. neck_front_1, la mandibula): crea sus 4 canales con una clave por frame igual a la pose actual, para poder sumarles el movimiento"""
    arm = bpy.data.objects["torso_1"]
    bag = arm.animation_data.action.layers[0].strips[0].channelbags[0]
    for n in nombres:
        dp = 'pose.bones["%s"].rotation_quaternion' % n
        if (dp, 0) in CAD or n not in arm.pose.bones:
            continue
        q0 = arm.pose.bones[n].rotation_quaternion
        for i in range(4):
            fc = bag.fcurves.new(dp, index=i)
            fc.keyframe_points.add(fin)
            fc.keyframe_points.foreach_set("co", [x for f in range(1, fin + 1) for x in (f, q0[i])])
            for k in fc.keyframe_points:
                k.interpolation = 'LINEAR'
            fc.update()


def aplicar(quitar=False):
    preparar()
    indexar_claves()
    _asegurar_fcurves(("neck_front_1",), bpy.context.scene.frame_end)
    preparar()
    indexar_claves()
    NS = bpy.app.driver_namespace
    ruta = CARPETA + "organicos_cueva5D_stalker.json"
    fin = bpy.context.scene.frame_end
    prev = json.load(open(ruta, encoding="utf-8")) if os.path.exists(ruta) else {}
    for n, fr_d in prev.items():                                  # quitar lo aplicado antes
        for fr, q in fr_d.items():
            fr = int(fr)
            if all((('pose.bones["%s"].rotation_quaternion' % n), i) in CAD for i in range(4)):
                _escribe(n, fr, _q(n, fr) @ Quaternion(q).inverted())
    nuevo = {}
    if not quitar:
        bones = [b.name for b in bpy.data.objects["torso_1"].pose.bones]
        for n, fr_d in _deltas(bones, fin).items():
            if not all((('pose.bones["%s"].rotation_quaternion' % n), i) in CAD for i in range(4)):
                continue
            nuevo[n] = {}
            for fr, e in fr_d.items():
                dq = Euler(e).to_quaternion()
                _escribe(n, fr, _q(n, fr) @ dq)
                nuevo[n][str(fr)] = list(dq)
    for fc in CAD.values():
        fc.update()
    json.dump(nuevo, open(ruta, "w", encoding="utf-8"))
    return {"huesos": len(nuevo), "frames": fin}


def _escribe(n, fr, q):
    for i in range(4):
        fcv = CAD[('pose.bones["%s"].rotation_quaternion' % n, i)]
        kp = KEYS[fcv].get(fr)
        if kp:
            kp.co.y = q[i]
            kp.handle_left.y = q[i]
            kp.handle_right.y = q[i]
