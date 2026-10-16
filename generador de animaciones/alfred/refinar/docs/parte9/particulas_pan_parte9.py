# -*- coding: utf-8 -*-
"""Parte 9: PARTICULAS AL COMER (como en Minecraft): en cada mordisco de Alfred (las tiras `SND_alfred_come_<f>` que pone `alfred_pan_flechas_cae_parte9.py`)
salen de la boca/pan 6 migas: cubitos pequenos con el material del pan, disparados hacia delante y arriba con dispersion, caen con gravedad, giran y se
achican hasta desaparecer (10-14 f). Coleccion `particulas_pan_parte9` (malla compartida `miga_pan`). Repetible. Ejecutar despues del script de Alfred."""
import bpy, math, random
from mathutils import Vector, Euler

sc = bpy.context.scene; COLN = "particulas_pan_parte9"; N = 6; G = 9.8 / (24 * 24); TAM = 0.035
col = bpy.data.collections.get(COLN)
if col:
    for o in list(col.objects): bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(col)
col = bpy.data.collections.new(COLN); sc.collection.children.link(col)
pan = bpy.data.objects["pan_alfred"]
me = bpy.data.meshes.get("miga_pan")
if me is None:
    import bmesh
    me = bpy.data.meshes.new("miga_pan"); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=TAM); bm.to_mesh(me); bm.free()
    if pan.data.materials: me.materials.append(pan.data.materials[0])
    if pan.data.uv_layers:                                                                 # UV a un punto del pan: la miga toma un color de su textura
        me.uv_layers.new(name=pan.data.uv_layers[0].name)
        u0 = pan.data.uv_layers[0].data[len(pan.data.uv_layers[0].data) // 2].uv.copy()
        for l in me.uv_layers[0].data: l.uv = u0
ed = sc.sequence_editor
MORD = sorted(int(t.name.rsplit("_", 1)[1]) for t in ed.strips_all if t.name.startswith("SND_alfred_come_"))
ARM = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'Hips_alfred' in o.pose.bones)
rng = random.Random(5); n = 0
for f0 in MORD:
    sc.frame_set(f0); bpy.context.view_layer.update()
    cab = ARM.matrix_world @ ARM.pose.bones["face_alfred"].matrix
    fw = (cab.to_3x3() @ Vector((0, 0, 1))).normalized() if False else None
    hd = ARM.matrix_world @ ARM.pose.bones["face_alfred"].head
    origen = hd.lerp(pan.matrix_world.translation, 0.65)                                     # entre la boca y el pan
    fw = (pan.matrix_world.translation - hd); fw.z = 0; fw = fw.normalized() if fw.length > 1e-4 else Vector((-1, 0, 0))
    lado = fw.cross(Vector((0, 0, 1)))
    for i in range(N):
        o = bpy.data.objects.new("miga_%d_%d" % (f0, i), me); col.objects.link(o); o.rotation_mode = 'XYZ'
        v = fw * rng.uniform(0.010, 0.030) + lado * rng.uniform(-0.020, 0.020) + Vector((0, 0, rng.uniform(0.015, 0.040)))
        p = origen + lado * rng.uniform(-0.03, 0.03) + Vector((0, 0, rng.uniform(-0.02, 0.02))); vida = rng.randint(10, 14)
        rot = Euler((rng.uniform(0, 6.28), rng.uniform(0, 6.28), 0)); w = Vector((rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4)))
        esc0 = rng.uniform(0.7, 1.2)
        o.hide_viewport = True; o.hide_render = True
        for dp in ("hide_viewport", "hide_render"): o.keyframe_insert(dp, frame=f0 - 1)
        for k in range(vida + 1):
            o.location = p; o.rotation_euler = rot; s_ = esc0 * (1.0 - 0.6 * (k / vida) ** 2); o.scale = (s_, s_, s_)
            for dp in ("location", "rotation_euler", "scale"): o.keyframe_insert(dp, frame=f0 + k)
            vis = k < vida; o.hide_viewport = not vis; o.hide_render = not vis
            for dp in ("hide_viewport", "hide_render"): o.keyframe_insert(dp, frame=f0 + k)
            p = p + v; v = v - Vector((0, 0, G)); rot = Euler((rot.x + w.x, rot.y + w.y, rot.z + w.z))
        for fc in [c for l in o.animation_data.action.layers for st in l.strips for cb in st.channelbags for c in cb.fcurves]:
            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT' if fc.data_path.startswith("hide") else 'LINEAR'
        n += 1
sc.frame_set(MORD[0] + 3 if MORD else 1)
print("MIGAS DE PAN: %d mordiscos %s, %d particulas" % (len(MORD), MORD, n))
