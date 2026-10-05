"""CAMARA TRAS ROMPER EL BLOQUE (pedidos de Kebyn). Se ejecuta en Blender DESPUES de `sentarse_en_refugio.py` (no toca las claves anteriores a f1062; borra las que haya desde f1062 y las vuelve a crear).
  1) apenas Alfred termina de romper el bloque de madera (f1062) la camara `Camera.001` y el foco `Foco_Conversacion` pasan, con un movimiento suave de 12 frames (f1062 -> f1074, como los cambios de plano anteriores),
     a estos valores: camara (-95.646, -109.17, 14.847) y foco (-94.315, -108.59, 14.902). Antes de f1062 conservan el plano que tenian.
  2) despues de que Alfred dice "¿Que estara pasando afuera?" (voz f1064-1093) la camara cambia (f1094 -> f1106) a (-91.623, -107.82, 14.847) mientras Alfred se asoma a mirar; el foco no cambia."""
import bpy

CAM, FOCO = bpy.data.objects["Camera.001"], bpy.data.objects["Foco_Conversacion"]
ETAPAS = [(CAM, 1062, 1074, (-95.646, -109.17, 14.847)), (FOCO, 1062, 1074, (-94.315, -108.59, 14.902)), (CAM, 1094, 1106, (-91.623, -107.82, 14.847))]
F_MIN = 1062
sc = bpy.context.scene

for ob in (CAM, FOCO):
    for l in ob.animation_data.action.layers:                             # claves anteriores de este tramo (si se ejecuta dos veces)
        for st in l.strips:
            for cb in st.channelbags:
                for fc in cb.fcurves:
                    if fc.data_path == "location":
                        for i in range(len(fc.keyframe_points) - 1, -1, -1):
                            if fc.keyframe_points[i].co[0] >= F_MIN: fc.keyframe_points.remove(fc.keyframe_points[i])
for ob, f0, f1, dest in ETAPAS:
    sc.frame_set(f0 - 1); bpy.context.view_layer.update(); hold = tuple(ob.location)      # el plano que tiene justo antes del cambio
    ob.location = hold; ob.keyframe_insert("location", frame=f0)
    ob.location = dest; ob.keyframe_insert("location", frame=f1)
sc.frame_set(1)
print("camara:", [tuple(round(x, 3) for x in CAM.location)], "foco:", [tuple(round(x, 3) for x in FOCO.location)])
