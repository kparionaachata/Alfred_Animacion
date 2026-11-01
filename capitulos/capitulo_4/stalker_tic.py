# -*- coding: utf-8 -*-
"""alfred_cueva_5C.blend: tic nervioso de the_stalker_1: la cabeza (head_1, con un poco del cuello) gira de golpe hacia su DERECHA y vuelve, y el tic se hace cada vez mas rapido
(el intervalo baja de ~50 frames a ~9 frames entre el frame 1 y el final) y un poco mas fuerte. Cada tic: sube en 2 frames, se queda 2-3 frames y vuelve en 4 frames.
Se SUMA a lo que ya anima head_1 / neck_1 (claves por frame) y los deltas se guardan en stalker_tic.json para poder quitarlo (aplicar(quitar=True)).
Uso: exec(open(ruta, encoding="utf8").read()); aplicar()    /    aplicar(quitar=True)
"""
import bpy, math, random, json, os
from mathutils import Euler

JSON = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/stalker_tic.json"
GIRO_DER = -1.0                  # el giro hacia la derecha de la criatura es una rotacion negativa en Z local del hueso
I_INI, I_FIN = 50.0, 9.0         # intervalo entre tics al principio y al final (frames)
A_INI, A_FIN = 0.55, 0.95        # amplitud del giro (rad)


def _ss(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _forma(k):
    """k = frames desde el inicio del tic: 0 -> 1 en 2 f, mantiene hasta 4, baja hasta 8"""
    if k < 0 or k > 8:
        return 0.0
    if k <= 2:
        return _ss(k / 2.0)
    if k <= 4:
        return 1.0
    return 1.0 - _ss((k - 4) / 4.0)


def _eventos(fin, rnd):
    t, ev = 14.0, []
    while t < fin - 6:
        u = (t - 1) / float(fin - 1)
        ev.append((int(round(t)), _cl(A_INI, A_FIN, u) * rnd.uniform(0.85, 1.15)))
        t += max(I_FIN, _cl(I_INI, I_FIN, u)) * rnd.uniform(0.85, 1.15)
    return ev


def _cl(a, b, t):
    return a + (b - a) * t


def _fc(ar, n):
    a = ar.animation_data.action
    d = {}
    for l in a.layers:
        for s in l.strips:
            for cb in s.channelbags:
                for fc in cb.fcurves:
                    if fc.data_path == 'pose.bones["%s"].rotation_quaternion' % n:
                        d[fc.array_index] = fc
    return d


def aplicar(quitar=False, semilla=17):
    sc = bpy.context.scene
    ar = bpy.data.objects["torso_1"]
    fin = sc.frame_end
    fr = list(range(1, fin + 1))
    prev = json.load(open(JSON, encoding="utf-8")) if os.path.exists(JSON) else {}
    nuevo = {}
    rnd = random.Random(semilla)
    ev = [] if quitar else _eventos(fin, rnd)
    for bone, k in (("head_1", 1.0), ("neck_1", 0.3)):
        fcs = _fc(ar, bone)
        if len(fcs) < 4:
            continue
        # quaternion actual por frame, sin el delta anterior
        from mathutils import Quaternion
        q_actual = []
        for f in fr:
            q = Quaternion([fcs[i].evaluate(f) for i in range(4)])
            if bone in prev and str(f) in prev[bone]:
                q = q @ Quaternion(prev[bone][str(f)]).inverted()
            q_actual.append(q)
        deltas = {}
        for i, f in enumerate(fr):
            ang = 0.0
            for t0, amp in ev:
                ang += amp * _forma(f - t0)
            d = Quaternion(Euler((0, 0, GIRO_DER * ang * k)).to_quaternion())
            q = q_actual[i] @ d
            for j in range(4):
                kp = next((p for p in fcs[j].keyframe_points if round(p.co.x) == f), None)
                if kp is None:
                    kp = fcs[j].keyframe_points.insert(f, q[j], options={'FAST'})
                kp.co.y = q[j]
                kp.handle_left.y = q[j]
                kp.handle_right.y = q[j]
                kp.interpolation = 'LINEAR'
            if ang:
                deltas[str(f)] = list(d)
        for j in range(4):
            fcs[j].update()
        nuevo[bone] = deltas
    json.dump(nuevo, open(JSON, "w", encoding="utf-8"))
    sc.frame_set(sc.frame_current)
    return {"tics": len(ev), "intervalos": [ev[i + 1][0] - ev[i][0] for i in range(len(ev) - 1)]}
