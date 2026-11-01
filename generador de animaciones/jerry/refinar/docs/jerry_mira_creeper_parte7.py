# -*- coding: utf-8 -*-
"""Parte 7: Jerry cerca del creeper MIRA AL CREEPER (no al suelo), f608-670. Se corrige con el hueso `spine_2` (rotation_euler), que arrastra cuello y cabeza (cadena jaw_top > scull > scull_1 > spine_1 > spine_2).
Metodo: para cada clave de spine_2 en f608-670 se resolvio (Gauss-Newton, paso minimo) la rotacion de spine_2 con la que la mirada (de `scull`.head a `jaw_top`.tail) apunta a la cabeza del creeper (-108.5, -89.73, 15.48) con un cabeceo leve (-2 grados +-1.8 en el husmeo);
el delta (X ~ -26..-40, Y 4..10, Z 9..16 grados a pleno peso) se sumo a las claves con una rampa de 10 f (f608-618); desde f672 vuelve al guion original (el susto). Deltas en `recorridos/mira_creeper_delta_parte7.json` (radianes por frame clave, ya con el peso).
Resultado medido: angulo entre la mirada y el creeper 0.2-3.2 grados en f620-670 (antes 24-53) y cabeceo de la mirada -9..-13 grados (antes -27..-46).
Orden: `jerry_se_acerca_parte7.py` -> `jerry_sin_scull_acercamiento_parte7.py` (quita las rotaciones de `scull`; los deltas se calcularon sobre ese estado) -> este script. Este script SUMA (o resta con QUITAR = True) esos deltas a las claves de `spine_2`; ejecutar DESPUES de `jerry_se_acerca_parte7.py` (que borra las claves >= f568 y las rehace) y NO repetir sin QUITAR. Se ejecuta DENTRO de Blender con exec."""
import bpy, json
QUITAR = bool(globals().get("QUITAR", False)); SG = -1.0 if QUITAR else 1.0
D = json.load(open("C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/jerry/refinar/docs/recorridos/mira_creeper_delta_parte7.json"))["rotation_euler_delta"]
JA = next(o for o in bpy.data.objects if o.type == "ARMATURE" and "scull_1" in o.pose.bones)
fcs = [fc for l in JA.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]
for a in range(3):
    fc = next(f for f in fcs if f.data_path == 'pose.bones["spine_2"].rotation_euler' and f.array_index == a)
    for kp in fc.keyframe_points:
        k = str(int(round(kp.co.x)))
        if k in D:
            dv = SG * D[k][a]; kp.co.y += dv; kp.handle_left.y += dv; kp.handle_right.y += dv
    fc.update()
print("QUITADO" if QUITAR else "LISTO")
