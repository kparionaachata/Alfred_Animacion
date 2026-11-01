# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: Jerry adopta la pose `hablar_1.json` (usuario; `generador de animaciones/jerry/refinar/poses/hablar_1.json`) mientras dice "Como que hasta aqui" (voz 980-998,
cara 980-1003). SOLO HUESOS (el empty `jerry` no se mueve): spine_1 (cuello: -9.2, 1.6, -53.3 deg: mira a Alfred), spine_5, front_shoulder.L (pata delantera izquierda), orejas y cola.
Entra entre el 968 y el 978, se mantiene y sale entre el 1000 y el 1010 (cuando gira el cuerpo y se sienta). Se SUMA a lo que ya hace cada hueso: nuevo(f) = actual(f) + (pose - actual(F_REF)) * peso(f).
No toca la cara (mandibula, cejas, scull) ni la cabeza (scull_1: la maneja jerry_mira_a_alfred_habla.py).
Uso en Blender: exec(open(ruta, encoding="utf8").read()); construir()      (NO repetible sin deshacer: se suma al estado actual)
"""
import bpy, json, math
from bpy_extras import anim_utils

POSE = "C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/jerry/refinar/poses/hablar_1.json"
ENTRA, SALE = (968, 10), (1000, 10)
F_REF = 968
SKIP = {"scull", "scull_1", "jaw_top", "jaw_bot", "sejas_1_jerry", "sejas_2_jerry", "sombrero"}


def S(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def peso(f):
    return S((f - ENTRA[0]) / float(ENTRA[1])) * (1 - S((f - SALE[0]) / float(SALE[1])))


def construir(signo=1.0):
    sc = bpy.context.scene
    rig = bpy.data.objects["Dog_001_rig"]
    P = json.load(open(POSE, encoding="utf8"))["poses"][0]["bones"]
    cb = anim_utils.action_get_channelbag_for_slot(rig.animation_data.action, rig.animation_data.action_slot)
    fin = sc.frame_end
    n = 0
    for h, d in P.items():
        if h in SKIP or h.startswith("no_bone"):
            continue
        e = [math.radians(d["raw_rotation_euler_deg"][a]) for a in "xyz"]
        for i in range(3):
            fc = cb.fcurves.find('pose.bones["%s"].rotation_euler' % h, index=i)
            if fc is None or not len(fc.keyframe_points):
                continue
            base = {f: fc.evaluate(f) for f in range(F_REF, fin + 1)}
            v0 = base[F_REF]
            if abs(e[i] - v0) < 1e-4:
                continue
            for j in range(len(fc.keyframe_points) - 1, -1, -1):
                if fc.keyframe_points[j].co.x >= F_REF:
                    fc.keyframe_points.remove(fc.keyframe_points[j])
            for f in range(F_REF, fin + 1):
                fc.keyframe_points.insert(f, base[f] + signo * (e[i] - v0) * peso(f), options={'FAST'}).interpolation = 'LINEAR'
            fc.update()
            n += 1
    sc.frame_set(1)
    return {"canales": n, "entra": ENTRA, "sale": SALE}
