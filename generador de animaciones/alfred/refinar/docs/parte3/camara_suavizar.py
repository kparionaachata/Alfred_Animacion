"""Parte 3 - SUAVIZAR LA CAMARA tras borrar keyframes (pedido de Kebyn). Se ejecuta DENTRO de Blender (exec) sobre base_parte_3.blend.
Toma los keyframes que QUEDAN en `Camara_Conversacion` (ubicacion, lente, apertura) y en `Foco_Conversacion` (el objetivo del Track To) y:
  1. guarda una copia de todos los keyframes en `camara_keys_antes_suavizar.json` (para volver atras),
  2. pasa la interpolacion de LINEAR (poligonal: esquinas en cada key) a BEZIER con manijas AUTO_CLAMPED (velocidad continua, sin rebasar los valores de los keys),
  3. mantiene los CORTES secos (saltos entre keys de frames consecutivos: f103->104 y f161->162): sus dos keys llevan manijas VECTOR para que la curva no se curve antes / despues del salto,
  4. deja el Foco con los MISMOS frames que la camara (a partir del primer hueco de la camara): si la camara tiene un key cada 15-30 frames y el Foco uno por frame, el Foco seguiria los cortes originales
     (saltos de 1 frame) mientras la camara se mueve despacio y el encuadre daria un tiron; con los mismos keys los dos hacen la misma transicion,
  5. mide el giro de la vista por frame (grados) y la posicion de la camara en cada frame (dentro de la sala, sin tocar mallas).
"""
import bpy, json, os, math
import numpy as np
from mathutils import Vector

DIR = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\parte3"
sc = bpy.context.scene; cam = bpy.data.objects["Camara_Conversacion"]; foco = bpy.data.objects["Foco_Conversacion"]; N = 480


def curvas(idb):
    ad = idb.animation_data
    if not ad or not ad.action: return []
    acc = ad.action
    return list(acc.fcurves) if hasattr(acc, "fcurves") else [c for l in acc.layers for s in l.strips for b in s.channelbags for c in b.fcurves]


FC_CAM = curvas(cam) + [c for c in curvas(cam.data) if c not in curvas(cam)]; FC_FOC = curvas(foco)
ruta_bak = os.path.join(DIR, "camara_keys_antes_suavizar.json")
if not os.path.exists(ruta_bak):
    json.dump({"cam": {f"{c.data_path}[{c.array_index}]": [(k.co[0], k.co[1]) for k in c.keyframe_points] for c in FC_CAM},
               "foco": {f"{c.data_path}[{c.array_index}]": [(k.co[0], k.co[1]) for k in c.keyframe_points] for c in FC_FOC}}, open(ruta_bak, "w"))
frames_cam = sorted({round(k.co[0]) for c in FC_CAM for k in c.keyframe_points})
huecos = [(a, b) for a, b in zip(frames_cam[:-1], frames_cam[1:]) if b - a > 1]; primer = huecos[0][0] if huecos else N + 1
# 4) el Foco con los mismos keys que la camara (desde el primer hueco)
borrados = 0
for c in FC_FOC:
    for k in reversed(list(c.keyframe_points)):
        if round(k.co[0]) > primer and round(k.co[0]) not in frames_cam: c.keyframe_points.remove(k, fast=True); borrados += 1
    c.update()
# cortes secos: keys consecutivos con un salto grande (ubicacion de la camara > 0.15 m)
cx = [c for c in FC_CAM if c.data_path == "location"]; cortes = []
if len(cx) == 3:
    fr = [round(k.co[0]) for k in cx[0].keyframe_points]; P = np.array([[k.co[1] for k in c.keyframe_points] for c in cx]).T
    for i in range(len(fr) - 1):
        if fr[i + 1] - fr[i] == 1 and np.linalg.norm(P[i + 1] - P[i]) > 0.15: cortes.append((fr[i], fr[i + 1]))
# 2) y 3) interpolacion
for c in FC_CAM + FC_FOC:
    ks = c.keyframe_points
    for k in ks: k.interpolation = 'BEZIER'; k.handle_left_type = 'AUTO_CLAMPED'; k.handle_right_type = 'AUTO_CLAMPED'; k.easing = 'AUTO'
    for a, b in cortes:
        for k in ks:
            if round(k.co[0]) in (a, b): k.handle_left_type = 'VECTOR'; k.handle_right_type = 'VECTOR'
    c.update()
print("keys de la camara en frames:", len(frames_cam), "| huecos desde f%d:" % primer, huecos, "| keys del Foco quitados:", borrados, "| cortes secos:", cortes)

# 5) medidas
cur = sc.frame_current; pos = []; tgt = []
try:
    for f in range(1, N + 1):
        pos.append(np.array([c.evaluate(f) for c in sorted([c for c in FC_CAM if c.data_path == "location"], key=lambda c: c.array_index)]))
        tgt.append(np.array([c.evaluate(f) for c in sorted(FC_FOC, key=lambda c: c.array_index)]))
finally:
    sc.frame_set(cur)
pos = np.array(pos); tgt = np.array(tgt); d = tgt - pos; d /= np.linalg.norm(d, axis=1, keepdims=True)
ang = np.degrees(np.arccos(np.clip((d[1:] * d[:-1]).sum(axis=1), -1, 1)))
for a, b in cortes: ang[a - 1] = 0.0
sal = [(int(i) + 2, round(float(ang[i]), 2)) for i in np.where(ang > 2.5)[0]]
print("giro max %.2f grados/frame (f%d), medio %.3f | frames con giro > 2.5: %s" % (ang.max(), int(ang.argmax()) + 2, ang.mean(), sal[:20]))
