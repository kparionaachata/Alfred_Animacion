# -*- coding: utf-8 -*-
"""Parte 7: el pollo golpea al creeper en la cara en f440 (IMP): se corta su intento de explosion (la carga y los destellos paran de golpe), la cabeza se echa hacia atras y el creeper cae de ESPALDAS, quedando BOCA ARRIBA.
- f440-443: la deformacion de la carga vuelve a la base y los destellos se apagan (valor 0 desde f440); la cabeza se echa hacia atras (head X -35 grados) y vuelve.
- f440-449: el root gira en X de 0 a 90 grados cayendo hacia atras (aceleracion), se desliza 0.55 m hacia -y (lejos de Alfred) y sube 0.13 m (el espesor del cuerpo, para que la espalda apoye en el suelo); f449-453: rebote (82 grados) y asiento en 90 (la cara mira hacia arriba, +z).
Se ejecuta dentro de Blender: exec(open(RUTA, encoding='utf-8').read()). Requiere `creeper_intento_explosion_parte7.py` (el creeper hasta f440). Idempotente (borra sus claves >= IMP)."""
import bpy, math
from mathutils import Vector

IMP = int(globals().get('IMP', 440))
Dg = math.radians
sc = bpy.context.scene
ss = lambda x: 0.0 if x <= 0 else 1.0 if x >= 1 else x * x * (3 - 2 * x)
CA = bpy.data.objects['creeper.arma_creeper_1']; CR = bpy.data.objects['creeper_1']
def curvas(o): return [fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]
NAMES = ["body_creeper_1", "upperbody_creeper_1", "head_creeper_1", "hip_creeper_1"]
IKS = [CA.pose.bones.get("foot.IK" + s + "_creeper_1") for s in ("", ".001", ".002", ".003")]
# ---------- estado en el instante del golpe (antes de borrar) y estado base (f395, el creeper parado) ----------
sc.frame_set(IMP); bpy.context.view_layer.update()
imp_state = {n: (tuple(CA.pose.bones[n].rotation_euler), tuple(CA.pose.bones[n].scale), tuple(CA.pose.bones[n].location)) for n in NAMES}
imp_ik = [tuple(b.location) for b in IKS if b]; imp_scale = Vector(CR.scale); loc0 = Vector(CR.location)
sc.frame_set(395); bpy.context.view_layer.update()
base_state = {n: (tuple(CA.pose.bones[n].rotation_euler), tuple(CA.pose.bones[n].scale), tuple(CA.pose.bones[n].location)) for n in NAMES}
base_scale = Vector(CR.scale)
# ---------- borrar claves >= IMP del creeper y de los destellos ----------
for o in (CA, CR):
    for fc in curvas(o):
        for i in range(len(fc.keyframe_points) - 1, -1, -1):
            if fc.keyframe_points[i].co.x >= IMP: fc.keyframe_points.remove(fc.keyframe_points[i])
flash = []
for m in bpy.data.materials:
    if m.get('creeper_explosion_material') and m.node_tree and m.node_tree.animation_data and m.node_tree.animation_data.action:
        for l in m.node_tree.animation_data.action.layers:
            for s in l.strips:
                for cb in s.channelbags:
                    for fc in cb.fcurves:
                        for i in range(len(fc.keyframe_points) - 1, -1, -1):
                            if fc.keyframe_points[i].co.x >= IMP: fc.keyframe_points.remove(fc.keyframe_points[i])
        flash.append(m)
DP = 'nodes["CreeperExplosionFlash"].outputs[0].default_value'
for m in flash:
    m.node_tree.nodes['CreeperExplosionFlash'].outputs[0].default_value = 0.0; m.node_tree.keyframe_insert(data_path=DP, frame=IMP)     # los destellos paran en seco

# ---------- deformacion de la carga -> base (3 f) y cabeza hacia atras ----------
for f in range(IMP, IMP + 4):
    w = ss((f - IMP) / 3.0)
    for n in NAMES:
        b = CA.pose.bones[n]; r0, s0, l0 = imp_state[n]; r1, s1, l1 = base_state[n]
        b.rotation_euler = tuple(r0[c] + (r1[c] - r0[c]) * w for c in range(3)); b.scale = tuple(s0[c] + (s1[c] - s0[c]) * w for c in range(3)); b.location = tuple(l0[c] + (l1[c] - l0[c]) * w for c in range(3))
        if n == "head_creeper_1": b.rotation_euler = (b.rotation_euler[0] - Dg(35) * math.sin(math.pi * (f - IMP) / 6.0) * 1.0, b.rotation_euler[1], b.rotation_euler[2])
        for ch in ("rotation_euler", "scale", "location"): b.keyframe_insert(ch, frame=f, group=n)
    for i, b in enumerate([b for b in IKS if b]):
        b.location = tuple(imp_ik[i][c] * (1 - w) for c in range(3)); b.keyframe_insert("location", frame=f, group=b.name)
for f in range(IMP + 4, IMP + 7):                                              # la cabeza vuelve de atras
    for n in ("head_creeper_1",):
        b = CA.pose.bones[n]; r1 = base_state[n][0]; b.rotation_euler = (r1[0] - Dg(35) * math.sin(math.pi * (f - IMP) / 6.0) * (1 if f - IMP <= 6 else 0), r1[1], r1[2]); b.keyframe_insert("rotation_euler", frame=f, group=n)
b = CA.pose.bones["head_creeper_1"]; b.rotation_euler = base_state["head_creeper_1"][0]; b.keyframe_insert("rotation_euler", frame=IMP + 7, group="head_creeper_1")
for n in NAMES:                                                                # el resto queda en la base
    b = CA.pose.bones[n]
    if n != "head_creeper_1":
        r1, s1, l1 = base_state[n]; b.rotation_euler = r1; b.scale = s1; b.location = l1
        for ch in ("rotation_euler", "scale", "location"): b.keyframe_insert(ch, frame=IMP + 8, group=n)

# ---------- caida de espaldas ----------
T_FALL = 9; dir_atras = Vector((0, -1, 0)); ELEV = 0.13                       # el creeper mira a +y: cae hacia -y; ELEV = lo que sube el root (se ajusta con la geometria real)
def estado_root(f):
    t = f - IMP
    if t <= T_FALL: th = 90.0 * (t / float(T_FALL)) ** 2
    elif t <= T_FALL + 3: th = 90.0 - 8.0 * math.sin(math.pi * (t - T_FALL) / 3.0)                  # rebote (82 grados)
    else: th = 90.0
    desl = 0.55 * (1 - (1 - min(1.0, t / 10.0)) ** 2); elev = ELEV * ss(t / float(T_FALL))
    esc = imp_scale + (base_scale - imp_scale) * ss(t / 3.0)
    return th, loc0 + dir_atras * desl + Vector((0, 0, elev)), esc
def poner_claves():
    for f in range(IMP, IMP + 18):
        th, pos, esc = estado_root(f); CR.location = pos; CR.rotation_euler = (Dg(th), 0, 0); CR.scale = esc
        for ch in ("location", "rotation_euler", "scale"): CR.keyframe_insert(ch, frame=f)
poner_claves()
sc.frame_set(IMP + 12); bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); zmin = 99.0                 # tumbado: busca lo mas bajo (las patas traseras quedan debajo) y sube el root para apoyarlo en el suelo
for ob in CR.children_recursive:
    if ob.type == 'MESH' and not ob.hide_viewport:
        ev = ob.evaluated_get(dg); zmin = min(zmin, min((ev.matrix_world @ Vector(c)).z for c in ev.bound_box))
ELEV = ELEV + (loc0.z - zmin); poner_claves()
for o in (CA, CR):
    for fc in curvas(o):
        for k in fc.keyframe_points:
            if k.co.x >= IMP - 1: k.interpolation = 'LINEAR'
sc.frame_end = max(sc.frame_end, IMP + 18)
sc.frame_set(IMP)
print("elevacion final del root: %.2f m (z minimo de las mallas antes: %.2f)" % (ELEV, zmin)); print("Creeper golpeado en f%d: carga y destellos cortados, cae de espaldas f%d-%d y rebota hasta f%d (boca arriba, rx 90)" % (IMP, IMP, IMP + T_FALL, IMP + T_FALL + 3))
