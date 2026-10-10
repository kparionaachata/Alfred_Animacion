# -*- coding: utf-8 -*-
"""Alfred: piernas en su posicion por defecto (rotacion 0) mientras esta de pie, f326-f681 de la parte 6.
Tras levantarse apoyado en la pared (f284-337) los muslos se quedaban girados (RightUpLeg (-2.6, 41.7, -5.5), LeftUpLeg (-9.5, -46.3, 10.8) grados)
y asi seguian al sobarse la cabeza, en la mesa de crafteo y al empezar el salto. Se resta esa pose base: f326-337 entra suave, f337-677 queda en 0
(los golpes de la mesa f544-559 se conservan como movimiento sobre 0) y f677-681 vuelve a los valores del salto.
Idempotente: guarda los valores originales en piernas_defecto_original.json y siempre parte de ellos.
Uso (Blender con base_parte_6.blend):  exec(open(r'<ruta>/alfred_piernas_por_defecto.py', encoding='utf-8').read())"""
import bpy, json, os, math

RUTA = r'C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/piernas_defecto_original.json'
F_ENTRA0, F_ENTRA1, F_SALE0, F_SALE1 = 326, 337, 677, 681
BASE = {'RightUpLeg_alfred': (math.radians(-2.6), math.radians(41.7), math.radians(-5.5)),
        'LeftUpLeg_alfred': (math.radians(-9.5), math.radians(-46.3), math.radians(10.8))}


def _fcs(action):
    return [fc for l in action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


def _peso(f):
    if f <= F_ENTRA0 or f >= F_SALE1: return 0.0
    if f < F_ENTRA1: t = (f - F_ENTRA0) / (F_ENTRA1 - F_ENTRA0); return t * t * (3 - 2 * t)
    if f <= F_SALE0: return 1.0
    t = (f - F_SALE0) / (F_SALE1 - F_SALE0); return 1.0 - t * t * (3 - 2 * t)


arm = [o for o in bpy.data.objects if o.type == 'ARMATURE' and 'Hips_alfred' in o.pose.bones][0]
fcs = _fcs(arm.animation_data.action)
orig = json.load(open(RUTA)) if os.path.isfile(RUTA) else {}
frames = range(F_ENTRA0, F_SALE1 + 1)
for hueso, base in BASE.items():
    for i in range(3):
        dp = 'pose.bones["%s"].rotation_euler' % hueso
        fc = next(f for f in fcs if f.data_path == dp and f.array_index == i)
        key = '%s:%d' % (hueso, i)
        if key not in orig: orig[key] = {str(f): fc.evaluate(f) for f in frames}
        for f in frames:
            if hueso == 'RightUpLeg_alfred' and i == 0: b = orig[key][str(min(f, 543))]   # X deriva de 0 a -2.6 hasta f543: se resta tal cual
            else: b = base[i]
            v = orig[key][str(f)] - b * _peso(f)
            fc.keyframe_points.insert(f, v, options={'REPLACE'})
        for kp in fc.keyframe_points:
            if F_ENTRA0 <= kp.co[0] <= F_SALE1: kp.interpolation = 'LINEAR'
        fc.update()
json.dump(orig, open(RUTA, 'w'))
bpy.context.view_layer.update()
for hueso in BASE:
    pb = arm.pose.bones[hueso]
    for f in (300, 337, 400, 560, 677, 681, 700):
        bpy.context.scene.frame_set(f)
        print(hueso, f, [round(math.degrees(x), 1) for x in pb.rotation_euler])
