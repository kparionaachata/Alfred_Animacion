# -*- coding: utf-8 -*-
"""Parte 7: cuando el creeper llega a su ultima coordenada (punto 8 en f383) y termina de pararse (f395), hace su INTENTO DE EXPLOSION 3 (sin detonar) en f396-449 (54 f): carga organica del estudio
(`creeper_1_animation_studio/explosion_runtime.py`: temblor y abultamiento de `body`/`upperbody`/`head`/`hip`, agachada, pies que vibran, el root crece un 16 %), 7 destellos blancos (`_flash_materials`, flash_count=7) y vuelve a su pose
base en los ultimos 12 f. Mismo codigo que el de la parte 6 (`docs/acciones/creeper_susto_y_huida.py`, bloque 4). Sin sonido (no pedido). Idempotente (borra sus claves >= IM). Variable opcional: IM (396)."""
import bpy, math
from mathutils import Vector

sc = bpy.context.scene
ss = lambda x: 0.0 if x <= 0 else 1.0 if x >= 1 else x * x * (3 - 2 * x)
IM = int(globals().get('IM', 396)); FLASH = 7
CA = bpy.data.objects['creeper.arma_creeper_1']; CR = bpy.data.objects['creeper_1']
def fcs(o): return [fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]
CH_END = IM + FLASH * 6; ATT_END = CH_END + 11

# ---------- limpiar claves propias anteriores ----------
for o in (CA, CR):
    for fc in fcs(o):
        for i in range(len(fc.keyframe_points) - 1, -1, -1):
            if fc.keyframe_points[i].co.x >= IM: fc.keyframe_points.remove(fc.keyframe_points[i])
sc.frame_set(IM - 1); bpy.context.view_layer.update()
NAMES = [("body_creeper_1", .055, 0), ("upperbody_creeper_1", .085, .6), ("head_creeper_1", .13, 1.1), ("hip_creeper_1", .045, 2)]
base_ro = {n: tuple(CA.pose.bones[n].rotation_euler) for n, a, p in NAMES}
IKS = [CA.pose.bones.get("foot.IK" + s + "_creeper_1") for s in ("", ".001", ".002", ".003")]
CR0 = Vector(CR.location); rz_c = CR.rotation_euler.z; cb = Vector(CR.scale)

def key_att(f, amp_charge, t):
    envelope = math.sin(t * math.pi / 2) ** 2; wave = math.sin(2 * math.pi * (2 * t + 3 * t * t)) * envelope; crouch = math.sin(math.pi * min(1, t / .8)) * .035
    for n, amount, phase in NAMES:
        b = CA.pose.bones[n]; r0 = base_ro[n]
        off = (amount * wave, amount * .45 * math.sin(t * 23 + phase) * envelope, amount * .35 * math.sin(t * 31 + phase) * envelope)
        b.rotation_euler = tuple(r0[c] + off[c] * amp_charge for c in range(3)); b.scale = (1 + .06 * envelope * amp_charge, 1 - .035 * envelope * amp_charge, 1 + .025 * wave * amp_charge)
        for ch in ("rotation_euler", "scale"): b.keyframe_insert(ch, frame=f, group=n)
        if n == "body_creeper_1": b.location = (0, 0, -crouch * amp_charge); b.keyframe_insert("location", frame=f, group=n)
    for i, b in enumerate(IKS):
        if b: b.location = (.015 * wave * (-1 if i % 2 else 1) * amp_charge, 0, .008 * max(0, math.sin(t * 27 + i * math.pi / 2)) * envelope * amp_charge); b.keyframe_insert("location", frame=f, group=b.name)
def key_root(f, a):
    CR.location = CR0; CR.rotation_euler = (0, 0, rz_c); CR.scale = tuple(v * (1 + a * (1 if i < 2 else .5)) for i, v in enumerate(cb))
    for ch in ("location", "rotation_euler", "scale"): CR.keyframe_insert(ch, frame=f)

for n, a, p in NAMES:                                                                   # ancla en IM-1 (estado base)
    b = CA.pose.bones[n]; b.rotation_euler = base_ro[n]; b.scale = (1, 1, 1)
    for ch in ("rotation_euler", "scale"): b.keyframe_insert(ch, frame=IM - 1, group=n)
    if n == "body_creeper_1": b.location = (0, 0, 0); b.keyframe_insert("location", frame=IM - 1, group=n)
for b in IKS:
    if b: b.location = (0, 0, 0); b.keyframe_insert("location", frame=IM - 1, group=b.name)
key_root(IM - 1, 0.0)
for f in range(IM, CH_END):                                                             # carga: 7 destellos de aceleracion creciente
    t = (f - IM) / max(1, CH_END - IM - 1); key_att(f, 1.0, t); key_root(f, .16 * t * t)
for f in range(CH_END, ATT_END + 1):                                                    # sin detonar: vuelve a la pose base en 12 f
    tt = (f - CH_END + 1) / 12.0; sm = ss(tt); key_att(f, 1.0 - sm, 1.0); key_root(f, .16 * (1 - sm))
src = open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\creeper_1\refinar\creeper_1_animation_studio\explosion_runtime.py", encoding="utf-8").read(); gx = {"__name__": "x"}; exec(src, gx)
gx["_flash_materials"]([o for o in CR.children_recursive if o.type == 'MESH'], IM, CH_END, flash_count=FLASH)
for o in (CA, CR):
    for fc in fcs(o):
        for k in fc.keyframe_points:
            if k.co.x >= IM - 1: k.interpolation = 'LINEAR'
sc.frame_end = max(sc.frame_end, ATT_END + 10)
sc.frame_set(IM - 1)
print("Creeper: intento de explosion 3 f%d-f%d (carga f%d-%d, 7 destellos, vuelve a la base hasta f%d)" % (IM, ATT_END, IM, CH_END - 1, ATT_END))
