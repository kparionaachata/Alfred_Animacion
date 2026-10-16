# -*- coding: utf-8 -*-
"""Parte 8: despues del golpe del pico de Jerry (f2030, reaccion de la cabeza f2031-2048), Alfred se SOBA la cabeza con la mano DERECHA.
Pose de sobarse = valores del usuario (parte 6, con el brazo corregido (-24, +12, -28) grados para que la mano llegue a la parte alta derecha de la cabeza en esta postura; `acciones/alfred_se_soba_la_cabeza.py`): `RightUpArm_alfred` rot (98.826, 214.36, 256.7) grados y loc (-0.003723, 0.09605, 0.10545);
`Rightelbow_alfred` rot (-2.5797, 8.3668, 59.379). Sube SUBE0->SUBE1 (slerp desde la pose actual), frota SUBE1->BAJA0 oscilando (brazo Y/Z +-4, codo Z +-10, irregular),
baja BAJA0->BAJA1 a la pose que tenia; el cuello se inclina un poco (confundido) mientras se soba (se SUMA a lo que hay, incluida la reaccion al golpe).
Escribe en la accion `tunel_alfred_armature` (claves por frame). Repetible: guarda los valores base la primera vez en `scene["alfred_soba_base"]`.
Ejecutar en Blender: exec(open(RUTA, encoding='utf-8').read())"""
import bpy, math
from mathutils import Euler, Quaternion

SUBE0, SUBE1, BAJA0, BAJA1 = [int(globals().get(k, v)) for k, v in (("SUBE0", 2034), ("SUBE1", 2046), ("BAJA0", 2204), ("BAJA1", 2218))]
ss = lambda t: 0.0 if t <= 0 else 1.0 if t >= 1 else t * t * (3 - 2 * t)
D = math.radians
OBJ = {"RightUpArm_alfred": ((D(254.826), D(337.64), D(48.7)), (-0.003723, 0.09605, 0.10545)), "Rightelbow_alfred": ((D(-2.5797), D(8.3668), D(59.379)), None)}
sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'Hips_alfred' in o.pose.bones)
FC = {(fc.data_path, fc.array_index): fc for l in arm.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves}
R = list(range(SUBE0, BAJA1 + 1))
CANALES = [("RightUpArm_alfred", "rotation_euler"), ("RightUpArm_alfred", "location"), ("Rightelbow_alfred", "rotation_euler"), ("Neck_alfred", "rotation_euler")]
base = sc.get("alfred_soba_base")
if base is None:
    base = {"%s|%s|%d" % (b, p, i): [FC[('pose.bones["%s"].%s' % (b, p), i)].evaluate(f) for f in R] for b, p in CANALES for i in range(3)}; sc["alfred_soba_base"] = base
B = lambda b, p, j: tuple(base["%s|%s|%d" % (b, p, i)][j] for i in range(3))
def key(b, p, i, f, v):
    k = FC[('pose.bones["%s"].%s' % (b, p), i)].keyframe_points.insert(f, v); k.interpolation = 'LINEAR'
def w_de(f):
    if f <= SUBE1: return ss((f - SUBE0) / (SUBE1 - SUBE0))
    if f <= BAJA0: return 1.0
    return 1.0 - ss((f - BAJA0) / (BAJA1 - BAJA0))
def frote(f):                                                                      # oscilacion irregular mientras frota (solo entre SUBE1 y BAJA0, entra y sale en 4 f)
    if f <= SUBE1 or f >= BAJA0: return 0.0, 0.0, 0.0
    a = min(1.0, (f - SUBE1) / 4.0, (BAJA0 - f) / 4.0)
    return a * (D(4) * math.sin(f * 0.9) + D(1.5) * math.sin(f * 2.3)), a * (D(4) * math.sin(f * 0.7 + 1.0)), a * (D(10) * math.sin(f * 0.9 + 0.6) + D(3) * math.sin(f * 1.9))
for j, f in enumerate(R):
    w = w_de(f); fy, fz, fe = frote(f)
    for b, (rot, loc) in OBJ.items():
        e0 = Euler(B(b, "rotation_euler", j), 'XYZ'); q = e0.to_quaternion().slerp(Euler(rot, 'XYZ').to_quaternion(), w); e = q.to_euler('XYZ', e0)
        e = list(e)
        if b == "RightUpArm_alfred": e[1] += fy; e[2] += fz
        else: e[2] += fe
        for i in range(3): key(b, "rotation_euler", i, f, e[i])
        if loc:
            l0 = B(b, "location", j)
            for i in range(3): key(b, "location", i, f, l0[i] + (loc[i] - l0[i]) * w)
    n0 = B("Neck_alfred", "rotation_euler", j)                                  # cuello: MIRA HACIA ARRIBA (X negativo) y GIRA la cabeza de izquierda a derecha (Y = giro del cuello) buscando de donde cayo
    busca = 0.55 * math.sin((f - SUBE1) * 2 * math.pi / 32.0) * min(1.0, max(0.0, (f - SUBE0) / 10.0))
    key("Neck_alfred", "rotation_euler", 0, f, n0[0] - 0.50 * w + 0.05 * w * math.sin(f * 0.37))
    key("Neck_alfred", "rotation_euler", 1, f, n0[1] + w * busca)
    key("Neck_alfred", "rotation_euler", 2, f, n0[2])
for fc in FC.values(): fc.update()
sc.frame_end = max(sc.frame_end, BAJA1 + 10)
print("Alfred se soba la cabeza: sube f%d-%d, frota f%d-%d, baja f%d-%d" % (SUBE0, SUBE1, SUBE1, BAJA0, BAJA0, BAJA1))
