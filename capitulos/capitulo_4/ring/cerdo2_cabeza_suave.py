# -*- coding: utf-8 -*-
"""cerdo2_ring: sus huesos oscilaban demasiado (estilo "bombea" de cerdos_animan.py: cabeza 14 grados cada 5 f, pata
derecha 35 grados, cuerpo que rebota). En TODAS las curvas de rotacion y posicion de su armature se conserva el
movimiento lento (reacciones a la pelea: promedio movil de VENTANA f) y queda solo QUEDA de la oscilacion rapida.
Las curvas originales se guardan en `cerdo2_original.json` (repetible: siempre parte de ellas).
Uso (exec en Blender): aplicar()
"""
import bpy, json, os

ORIG = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/cerdo2_original.json"
ORIG_VIEJO = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/cerdo2_cabeza_original.json"   # primera version (solo cabeza)
ARM = "pig.arma_cerdo_1.001"
VENTANA, QUEDA = 15, 0.2


def fcs(o):
    return [fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


def aplicar():
    arm = bpy.data.objects[ARM]
    curvas = {"%s|%d" % (fc.data_path, fc.array_index): fc for fc in fcs(arm)
              if fc.data_path.endswith(("rotation_euler", "location")) and len(fc.keyframe_points) > VENTANA}
    if os.path.exists(ORIG):
        orig = json.load(open(ORIG, encoding="utf-8"))
    else:
        orig = {k: [list(p.co) for p in fc.keyframe_points] for k, fc in curvas.items()}
        if os.path.exists(ORIG_VIEJO):                                   # la cabeza ya se suavizo una vez: su original esta en el json viejo
            for i, pts in json.load(open(ORIG_VIEJO, encoding="utf-8")).items():
                orig['pose.bones["Head_cerdo_1"].rotation_euler|%s' % i] = pts
        json.dump(orig, open(ORIG, "w", encoding="utf-8"))
    res = {}
    for k, fc in curvas.items():
        if k not in orig: continue
        pts = orig[k]; fr = [p[0] for p in pts]; val = [p[1] for p in pts]
        h = VENTANA // 2; n = len(val); out = []
        for j in range(n):
            a, b = max(0, j - h), min(n, j + h + 1); m = sum(val[a:b]) / (b - a)
            out.append(m + QUEDA * (val[j] - m))
        kp = fc.keyframe_points
        for j in range(len(kp) - 1, -1, -1): kp.remove(kp[j], fast=True)
        kp.add(n); kp.foreach_set("co", [x for f, v in zip(fr, out) for x in (f, v)])
        for p in kp: p.interpolation = 'LINEAR'
        fc.update()
        salto = lambda vs: max(abs(vs[j] - vs[j - 1]) for j in range(1, len(vs)))
        if salto(val) > 1e-4:
            esc = 57.3 if "rotation" in k else 100.0                    # grados / cm
            res[k.replace('pose.bones["', '').replace('"].', '.')] = (round(salto(val) * esc, 1), round(salto(out) * esc, 1))
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    return res
