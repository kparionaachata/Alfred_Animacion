# -*- coding: utf-8 -*-
"""Rotura de bloque como en Minecraft, para cualquier bloque `bloque_<tipo>_i_j_k` (cubo 1x1x1, origen abajo-centro):
- grietas: cubo apenas mayor que el bloque con las texturas destroy_stage_0..9 del juego; la etapa avanza con cada golpe;
- en cada golpe saltan unas pocas particulas desde el punto de contacto;
- al romperse: lluvia de particulas planas (trocitos 4x4 de la textura del propio bloque) que miran a la camara, salen hacia afuera,
  caen con gravedad y se encogen hasta desaparecer (como las particulas de bloque del juego).
Uso (Blender):  exec(open(ruta, encoding="utf8").read()); romper("bloque_iron_ore_-68_-19_-12", golpes=[12,28,44,60,76], contacto=(x,y,z))
Repetible: borra lo que creo antes para ese bloque (prefijo FXR_<bloque>).
"""
import bpy, bmesh, random, math, os
from mathutils import Vector

GRIETAS = r"C:\Users\user\Desktop\Alfred_Animacion\kebyn proyecto  1.20.1_analysis\kebyn proyecto  1.20.1\assets\minecraft\textures\block"
G = 9.8 / 24 / 24
TAM_PART = 0.11                 # lado de una particula (m)
N_ROTURA, N_GOLPE = 56, 5


def _mat_grieta(i):
    n = "FXR_destroy_stage_%d" % i
    m = bpy.data.materials.get(n)
    if m: return m
    m = bpy.data.materials.new(n); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); bs = nt.nodes.new("ShaderNodeBsdfPrincipled"); tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = bpy.data.images.load(os.path.join(GRIETAS, "destroy_stage_%d.png" % i), check_existing=True); tx.interpolation = 'Closest'
    nt.links.new(tx.outputs["Color"], bs.inputs["Base Color"]); nt.links.new(tx.outputs["Alpha"], bs.inputs["Alpha"]); nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    m.blend_method = 'BLEND' if hasattr(m, "blend_method") else None
    return m


def _imagen_bloque(ob):
    for s in ob.material_slots:
        if s.material and s.material.use_nodes:
            for n in s.material.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image: return n.image, s.material
    return None, None


def _mat_particula(img):
    n = "FXR_part_" + img.name
    m = bpy.data.materials.get(n)
    if m: return m
    m = bpy.data.materials.new(n); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); bs = nt.nodes.new("ShaderNodeBsdfPrincipled"); tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = img; tx.interpolation = 'Closest'
    nt.links.new(tx.outputs["Color"], bs.inputs["Base Color"]); nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m


def _quad(nombre, mat, u0, v0, du):
    bm = bmesh.new(); h = TAM_PART / 2
    vs = [bm.verts.new(p) for p in ((-h, 0, -h), (h, 0, -h), (h, 0, h), (-h, 0, h))]
    f = bm.faces.new(vs); uv = bm.loops.layers.uv.new("UVMap")
    for lp, (a, b) in zip(f.loops, ((u0, v0), (u0 + du, v0), (u0 + du, v0 + du), (u0, v0 + du))): lp[uv].uv = (a, b)
    me = bpy.data.meshes.new(nombre); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    return bpy.data.objects.new(nombre, me)


def _ocultar(ob, visible_desde, visible_hasta=None):
    for f, v in ((1, True), (visible_desde, False)) + (((visible_hasta, True),) if visible_hasta else ()):
        ob.hide_viewport = v; ob.hide_render = v
        ob.keyframe_insert("hide_viewport", frame=f); ob.keyframe_insert("hide_render", frame=f)
    for lay in ob.animation_data.action.layers:
        for s in lay.strips:
            for cb in s.channelbags:
                for fc in cb.fcurves:
                    if fc.data_path.startswith("hide"):
                        for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'


def quitar(bloque):
    for o in [o for o in bpy.data.objects if o.name.startswith("FXR_" + bloque)]:
        me = o.data; bpy.data.objects.remove(o, do_unlink=True)
        if me and me.users == 0: bpy.data.meshes.remove(me)


def romper(bloque, golpes, contacto=None, semilla=3):
    sc = bpy.context.scene; ob = bpy.data.objects[bloque]; quitar(bloque)
    col = ob.users_collection[0]; rec = bpy.data.collections.get("luz_entrada_receptores")
    def poner(o):
        col.objects.link(o)
        if rec and o.name not in rec.objects: rec.objects.link(o)
    c = ob.matrix_world.translation + Vector((0, 0, 0.5)); f_rompe = golpes[-1]
    # --- grietas: etapa 2, 4, 6, 8 tras cada golpe y 9 un instante antes de romperse
    etapas = [(golpes[i], min(9, 2 * (i + 1))) for i in range(len(golpes) - 1)] + [(f_rompe - 3, 9)]
    for n, (f0, st) in enumerate(etapas):
        f1 = etapas[n + 1][0] if n + 1 < len(etapas) else f_rompe
        me = bpy.data.meshes.new("FXR_%s_grieta_%d" % (bloque, st)); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.004); bm.to_mesh(me); bm.free()
        uv = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li, (a, b) in zip(poly.loop_indices, ((0, 0), (1, 0), (1, 1), (0, 1))): uv.data[li].uv = (a, b)
        me.materials.append(_mat_grieta(st))
        g = bpy.data.objects.new(me.name, me); g.location = c; poner(g); _ocultar(g, f0, f1)
    # --- particulas
    img, _ = _imagen_bloque(ob); mat = _mat_particula(img) if img else None
    cam = sc.camera; rnd = random.Random(semilla)
    def particula(nombre, p0, v, f0, vida):
        u0, v0 = rnd.randrange(4) / 4.0, rnd.randrange(4) / 4.0
        q = _quad(nombre, mat, u0, v0, 0.25); poner(q)
        if cam:
            con = q.constraints.new('TRACK_TO'); con.target = cam; con.track_axis = 'TRACK_NEGATIVE_Y'; con.up_axis = 'UP_Z'
        esc0 = rnd.uniform(0.6, 1.1)
        for k in range(vida + 1):
            pos = p0 + v * k + Vector((0, 0, -0.5 * G * k * k))
            if pos.z < c.z - 0.5 + TAM_PART * 0.3: pos.z = c.z - 0.5 + TAM_PART * 0.3      # se posa en el suelo
            q.location = pos; q.scale = (esc0 * (1 - 0.6 * k / vida),) * 3
            q.keyframe_insert("location", frame=f0 + k); q.keyframe_insert("scale", frame=f0 + k)
        _ocultar(q, f0, f0 + vida + 1)
    pc = Vector(contacto) if contacto else c + Vector((0, 0, 0.5))
    for gi, f in enumerate(golpes[:-1]):                                   # chispitas de cada golpe
        for i in range(N_GOLPE):
            v = Vector((rnd.uniform(-0.8, 0.8), rnd.uniform(-0.8, 0.8), rnd.uniform(0.8, 2.0))) / 24
            particula("FXR_%s_golpe_%d_%d" % (bloque, gi, i), pc + Vector((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), 0.02)), v, f, rnd.randint(8, 14))
    for i in range(N_ROTURA):                                                # el bloque se deshace
        p0 = c + Vector((rnd.uniform(-0.45, 0.45), rnd.uniform(-0.45, 0.45), rnd.uniform(-0.45, 0.45)))
        v = (p0 - c) * rnd.uniform(1.0, 2.2) / 24 + Vector((0, 0, rnd.uniform(0.5, 2.0) / 24))
        particula("FXR_%s_rotura_%02d" % (bloque, i), p0, v, f_rompe, rnd.randint(14, 32))
    return {"grietas": etapas, "particulas": N_ROTURA + N_GOLPE * (len(golpes) - 1)}
