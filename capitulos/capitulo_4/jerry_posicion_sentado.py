# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: valores finales de Jerry al sentarse (indicados por el usuario): empty `jerry` en (-0.55385, 84.317, 66.016) con rotacion Z 259.36 deg y
hueso spine_1 (cuello) en (-15.835, 5.8934, -13.598) deg. Pasan de lo actual a esos valores durante el sentarse (F_SIT .. F_SIT + 12) y se mantienen; el valor
sumado a las claves por frame conserva los filtros organicos (respiracion, micro-movimiento).
Uso en Blender: exec(open(ruta, encoding="utf8").read()); construir()      (repetible: los valores finales son absolutos)
"""
import bpy, math
from bpy_extras import anim_utils

F_SIT, DUR = 682, 12
EMPTY_LOC = (-0.55385, 84.317, 66.016)
EMPTY_RZ = 259.36
CUELLO = "spine_1"
CUELLO_ROT = (-15.835, 5.8934, -13.598)


def _w(f):
    t = max(0.0, min(1.0, (f - F_SIT) / float(DUR)))
    return t * t * (3 - 2 * t)


def _llevar(ob, dp, idx, destino):
    cb = anim_utils.action_get_channelbag_for_slot(ob.animation_data.action, ob.animation_data.action_slot)
    fc = cb.fcurves.find(dp, index=idx)
    fin = bpy.context.scene.frame_end
    f_fin = F_SIT + DUR
    base = {f: fc.evaluate(f) for f in range(F_SIT, fin + 1)}
    final = base[f_fin]                                          # ya incluye la parte de la animacion de sentarse; se lleva al valor absoluto
    for i in range(len(fc.keyframe_points) - 1, -1, -1):
        if fc.keyframe_points[i].co.x >= F_SIT:
            fc.keyframe_points.remove(fc.keyframe_points[i])
    for f in range(F_SIT, fin + 1):
        fc.keyframe_points.insert(f, base[f] + (destino - final) * _w(f), options={'FAST'}).interpolation = 'LINEAR'
    fc.update()


def construir():
    O = bpy.data.objects
    sc = bpy.context.scene
    root, rig = O["jerry"], O[CUELLO and "Dog_001_rig"]
    root.rotation_mode = 'XYZ'
    z_ref = root.animation_data.action
    # el rumbo final se elige en el giro continuo mas cercano al actual (sin dar una vuelta)
    cb = anim_utils.action_get_channelbag_for_slot(root.animation_data.action, root.animation_data.action_slot)
    fcz = cb.fcurves.find("rotation_euler", index=2)
    z_act = fcz.evaluate(F_SIT + DUR)
    z_obj = math.radians(EMPTY_RZ)
    while z_obj - z_act > math.pi:
        z_obj -= 2 * math.pi
    while z_obj - z_act < -math.pi:
        z_obj += 2 * math.pi
    for i in range(3):
        _llevar(root, "location", i, EMPTY_LOC[i])
    _llevar(root, "rotation_euler", 2, z_obj)
    for i in range(3):
        _llevar(rig, 'pose.bones["%s"].rotation_euler' % CUELLO, i, math.radians(CUELLO_ROT[i]))
    sc.frame_set(1)
    return {"empty": EMPTY_LOC, "rz": EMPTY_RZ, "cuello": CUELLO_ROT}
