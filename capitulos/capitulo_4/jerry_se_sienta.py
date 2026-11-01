# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: Jerry se sienta mientras habla (desde el frame F_SIT), con la animacion del usuario `animacion_jerry (29).py` (se sienta, 13 frames;
copia en animacion_jerry_se_sienta.py). Sus valores son absolutos de otra escena: se aplican como CAMBIO respecto a su primer cuadro y se SUMAN a lo que Jerry
ya hace (voz, mandibula, respiracion, orejas...): nuevo(f) = actual(f) + (cuadro_i - cuadro_0). Se mantiene sentado hasta el final de la escena.
No toca la cara (mandibula, cejas, cabeza) ni la cola tail_2 / orejas (ya tienen sus filtros), ni el giro del torso a los lados (spine_1 y, z) ni de la cabeza:
solo el movimiento de sentarse (columna, patas, hombros, cola tail_1/tail_3).
Uso en Blender: exec(open(ruta, encoding="utf8").read()); construir()    (NO repetible sin regenerar antes la animacion: se suma al estado actual)
"""
import bpy, ast
from bpy_extras import anim_utils

SCRIPT = r"C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/animacion_jerry_se_sienta.py"
F_SIT = 682                                   # empieza a sentarse mientras dice "Como que esta aqui?" (680)
SALTAR = {"scull", "scull_1", "ear.L", "ear.R", "tail_2"}
SOLO_X = {"spine_1"}                          # de spine_1 solo el cabeceo (x) y la escala


def _payload():
    for n in ast.parse(open(SCRIPT, encoding="utf8").read()).body:
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "PAYLOAD":
            return ast.literal_eval(n.value)


def construir():
    sc = bpy.context.scene
    rig = bpy.data.objects["Dog_001_rig"]
    P = _payload()
    N = P["info"]["frames"]
    fin = sc.frame_end
    cb = anim_utils.action_get_channelbag_for_slot(rig.animation_data.action, rig.animation_data.action_slot)
    hechos = 0
    for hueso, canales in P["bones"].items():
        if hueso in SALTAR or hueso not in rig.pose.bones:
            continue
        for prop, serie in canales.items():
            for idx in range(3):
                if hueso in SOLO_X and prop == "rotation_euler" and idx != 0:
                    continue
                delta = [serie[i][idx] - serie[0][idx] for i in range(N)]
                if prop == "scale":
                    delta = [serie[i][idx] / serie[0][idx] - 1.0 for i in range(N)]
                if not any(abs(d) > 1e-6 for d in delta):
                    continue
                dp = 'pose.bones["%s"].%s' % (hueso, prop)
                fc = cb.fcurves.find(dp, index=idx)
                if fc is None:
                    fc = cb.fcurves.new(dp, index=idx)
                if len(fc.keyframe_points):
                    base = {f: fc.evaluate(f) for f in range(F_SIT, fin + 1)}
                else:
                    sc.frame_set(F_SIT)
                    v = getattr(rig.pose.bones[hueso], prop)[idx]
                    base = {f: v for f in range(F_SIT, fin + 1)}
                for i in range(len(fc.keyframe_points) - 1, -1, -1):
                    if fc.keyframe_points[i].co.x >= F_SIT:
                        fc.keyframe_points.remove(fc.keyframe_points[i])
                for f in range(F_SIT, fin + 1):
                    d = delta[min(f - F_SIT, N - 1)]
                    fc.keyframe_points.insert(f, base[f] + (d * base[f] if prop == "scale" else d), options={'FAST'}).interpolation = 'LINEAR'
                fc.update()
                hechos += 1
    sc.frame_set(1)
    return {"canales": hechos, "se_sienta": (F_SIT, F_SIT + N - 1)}
