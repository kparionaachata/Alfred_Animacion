# -*- coding: utf-8 -*-
"""Parte 10: TODAS las flechas clavadas en Alfred quedan PERPENDICULARES a la parte frontal de su cuerpo, con +-10 grados de variacion (fija por flecha).
Se calcula en el frame 1 (Alfred boca arriba: el frente del cuerpo mira a +z): cada flecha conserva el punto donde esta su PUNTA y su escala, y su eje pasa a
apuntar hacia DENTRO del cuerpo (-frente) inclinado un angulo al azar de 0-10 grados en una direccion al azar. Siguen emparentadas a su hueso.
Ejecutar al final (despues de `jerry_arrastra_alfred_parte10.py`, que crea / coloca las flechas). Repetible."""
import bpy, math, random
from mathutils import Vector, Matrix, Quaternion

FLECHAS = ("flecha_alfred", "flecha_mano_der", "flecha_mano_izq", "flecha_entrepierna", "flecha_pecho")
sc = bpy.context.scene; vl = bpy.context.view_layer
ARM = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'Hips_alfred' in o.pose.bones)
D_loc = Vector((1, 1, 0)).normalized(); N_loc = Vector((0, 0, 1))                           # eje de la flecha en su malla (como en las partes 9 y 10)
sc.frame_set(1); vl.update()
H = ARM.matrix_world @ ARM.pose.bones["Hips_alfred"].matrix; S2 = ARM.matrix_world @ ARM.pose.bones["Spine2_alfred"].matrix
ARR = (S2.translation - H.translation).normalized()                                         # a lo largo del torso
LAT = (ARM.matrix_world @ ARM.pose.bones["LeftUpArm_alfred"].head - ARM.matrix_world @ ARM.pose.bones["RightUpArm_alfred"].head).normalized()
FRENTE = LAT.cross(ARR).normalized()
if FRENTE.z < 0: FRENTE = -FRENTE                                                           # boca arriba: el frente mira hacia arriba
rng = random.Random(10); hecho = {}
for n in FLECHAS:
    o = bpy.data.objects.get(n)
    if o is None: continue
    M = o.matrix_world.copy(); loc, rot, esc = M.decompose(); me = o.data
    punta_loc = max((v.co for v in me.vertices), key=lambda c: c.dot(D_loc)); punta_w = M @ punta_loc
    if n == "flecha_pecho":                                                                 # la del pecho: la punta 8 cm dentro del PECHO (superficie frontal del torso a la altura de Spine2)
        dg_ = bpy.context.evaluated_depsgraph_get(); e1 = bpy.data.objects["Mesh_1_alfred"].evaluated_get(dg_); c2 = S2.translation
        vt = [e1.matrix_world @ v.co for v in e1.data.vertices]; cerca = [v for v in vt if ((v - c2) - FRENTE * (v - c2).dot(FRENTE)).length < 0.12] or vt
        sup_ = max(cerca, key=lambda v: v.dot(FRENTE)); punta_w = c2 + FRENTE * ((sup_ - c2).dot(FRENTE) - 0.08)
    ang = math.radians(rng.uniform(0.0, 10.0)); az = rng.uniform(0, 2 * math.pi)
    perp = FRENTE.orthogonal().normalized(); perp = Quaternion(FRENTE, az) @ perp
    d = (Quaternion(perp, ang) @ (-FRENTE)).normalized()                                    # la flecha entra en el cuerpo (perpendicular +- 10 grados)
    lado = d.cross(Vector((0, 0, 1)))
    if lado.length < 1e-4: lado = LAT.copy()
    lado.normalize(); up = lado.cross(d).normalized(); perp_loc = N_loc.cross(D_loc).normalized()
    Rl = Matrix((D_loc, perp_loc, N_loc)).transposed(); R = (Matrix((d, up, lado)).transposed() @ Rl.inverted()).to_4x4()
    Ms = R @ Matrix.Diagonal((esc.x, esc.y, esc.z, 1.0)); Mn = Matrix.Translation(punta_w - (Ms @ punta_loc.to_4d()).to_3d()) @ Ms
    o.matrix_world = Mn; hecho[n] = round(math.degrees(ang), 1)
vl.update()
print("FLECHAS perpendiculares al frente (grados de desvio):", hecho)
# ---- la flecha en VUELO termina EXACTAMENTE donde queda clavada la del pecho (misma orientacion), viniendo del tunel ----
fv = bpy.data.objects.get("flecha_pecho_vuelo"); fp = bpy.data.objects.get("flecha_pecho"); TT = sc.get("p10_tiempos", {})
if fv and fp and "T_FLECHA" in TT:
    tf = int(TT["T_FLECHA"]); VUELO = 10; sc.frame_set(tf); vl.update(); Mc = fp.matrix_world.copy()
    eje = (Mc.to_3x3() @ D_loc).normalized()                                                # hacia donde apunta la flecha clavada
    ad = fv.animation_data
    if ad and ad.action:
        for c in [c for l in ad.action.layers for st in l.strips for b in st.channelbags for c in b.fcurves if not c.data_path.startswith("hide")]:
            while len(c.keyframe_points): c.keyframe_points.remove(c.keyframe_points[0])
    fv.rotation_mode = 'QUATERNION'
    for k in range(VUELO + 1):
        u = k / VUELO; off = -eje * 7.0 * (1 - u) + Vector((0, 0, 0.15 * 4 * u * (1 - u)))
        fv.matrix_world = Matrix.Translation(off) @ Mc
        for dp in ("location", "rotation_quaternion", "scale"): fv.keyframe_insert(dp, frame=tf - VUELO + k)
    print("vuelo de la flecha del pecho rehecho: termina en la clavada (f%d)" % tf)
sc.frame_set(1)
