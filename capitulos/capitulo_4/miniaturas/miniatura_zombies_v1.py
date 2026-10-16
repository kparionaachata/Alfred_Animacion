# -*- coding: utf-8 -*-
"""MINIATURA DE YOUTUBE: Alfred y Jerry huyen de los zombies (archivo aparte: no toca la escena ni la camara del proyecto).
blender -b --factory-startup --python miniatura_zombies.py   ->  miniatura_zombies.blend + miniatura_zombies.png (1920x1080)
Composicion: plano bajo y gran angular, los dos heroes corriendo hacia la camara, horda de zombies detras con ojos rojos
brillantes, noche con niebla y luna cuadrada, luz calida en los heroes y verde en los zombies, texto grande "¡CORRE!"."""
import bpy, math, os
TEX = os.path.join(os.environ.get("APPDATA", ""), "Blender Foundation/Blender/5.2/scripts/addons/MCprep_addon/MCprep_resources/resourcepacks/mcprep_default/assets/minecraft/textures/block/")
from mathutils import Vector, Matrix, Quaternion

E = "C:/Users/user/Desktop/Alfred_Animacion/estructura_lista/"
JERRY_RUN = "C:/Users/user/Desktop/Alfred_Animacion/de .fbx a blender/jerry/jerry_correr.blend"
OUT = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/miniaturas/"
FUENTE = "C:/Windows/Fonts/impact.ttf"
sc = bpy.context.scene; vl = bpy.context.view_layer
UP = Vector((0, 0, 1))

for o in list(bpy.data.objects): bpy.data.objects.remove(o)


# ------------------------------------------------------------------ utilidades
def anexar(archivo, raiz, nombre):
    col = bpy.data.collections.new(nombre); sc.collection.children.link(col)
    with bpy.data.libraries.load(E + archivo) as (src, dst):
        dst.objects = list(src.objects)
    for o in dst.objects:
        if o is None: continue
        if o.type in ('CAMERA', 'LIGHT') or (o.parent is None and o.name.split(".")[0] not in (raiz,)): bpy.data.objects.remove(o); continue
        col.objects.link(o)
    r = next(o for o in col.objects if o.parent is None and o.name.split(".")[0] == raiz)
    for o in list(col.objects):
        if o.parent is None and o is not r: bpy.data.objects.remove(o)
    r.name = nombre
    for o in [r] + list(r.children_recursive):
        if o.animation_data: o.animation_data.action = None
    return r


def arma_de(r): return max((c for c in r.children_recursive if c.type == 'ARMATURE'), key=lambda c: len(c.data.bones))


def mallas(r): return [c for c in r.children_recursive if c.type == 'MESH']


def puntos(r):
    vl.update(); dg = bpy.context.evaluated_depsgraph_get(); out = []
    for m in mallas(r):
        e = m.evaluated_get(dg); M = m.matrix_world; out += [M @ v.co for v in e.data.vertices]
    return out


def mirar_hacia(r, direccion):
    """gira la raiz para que la cara (donde estan los ojos) mire hacia `direccion` (horizontal)"""
    vl.update()
    ojos = [m for m in mallas(r) if m.name.startswith("ojo_")]
    c = sum((sum((m.matrix_world @ v.co for v in m.data.vertices), Vector()) / len(m.data.vertices) for m in ojos), Vector()) / len(ojos)
    f = c - r.matrix_world.translation; f.z = 0; f.normalize(); d = direccion.copy(); d.z = 0; d.normalize()
    r.rotation_euler.z += math.atan2(f.cross(d).z, f.dot(d)); vl.update()


def al_suelo(r, z=0.0):
    r.location.z += z - min(p.z for p in puntos(r)); vl.update()


def apuntar(arm, hueso, punta, objetivo):
    pb = arm.pose.bones[hueso]; vl.update()
    a = arm.matrix_world @ pb.head; b = punta()
    q = (b - a).normalized().rotation_difference((objetivo - a).normalized())
    R = Matrix.Translation(a) @ q.to_matrix().to_4x4() @ Matrix.Translation(-a)
    m = arm.convert_space(pose_bone=pb, matrix=arm.matrix_world.inverted() @ R @ arm.matrix_world @ pb.matrix, from_space='POSE', to_space='LOCAL')
    if pb.rotation_mode == 'QUATERNION': pb.rotation_quaternion = m.to_quaternion()
    else: pb.rotation_euler = m.to_euler(pb.rotation_mode, pb.rotation_euler)
    vl.update()


def rotar_mundo(arm, hueso, eje, ang):
    pb = arm.pose.bones[hueso]; vl.update(); a = arm.matrix_world @ pb.head
    R = Matrix.Translation(a) @ Quaternion(eje.normalized(), ang).to_matrix().to_4x4() @ Matrix.Translation(-a)
    m = arm.convert_space(pose_bone=pb, matrix=arm.matrix_world.inverted() @ R @ arm.matrix_world @ pb.matrix, from_space='POSE', to_space='LOCAL')
    if pb.rotation_mode == 'QUATERNION': pb.rotation_quaternion = m.to_quaternion()
    else: pb.rotation_euler = m.to_euler(pb.rotation_mode, pb.rotation_euler)
    vl.update()


def ik2(arm, muslo, pierna, T, polo):
    P = arm.pose.bones; W = arm.matrix_world; vl.update()
    S = W @ P[muslo].head; K = W @ P[pierna].head; F = W @ P[pierna].tail
    a = (K - S).length; b = (F - K).length; d = max(abs(a - b) + 1e-3, min(a + b - 1e-3, (T - S).length)); n = (T - S).normalized()
    ca = (a * a + d * d - b * b) / (2 * a * d); sa = math.sqrt(max(0.0, 1 - ca * ca))
    pp = polo - n * polo.dot(n); pp = pp.normalized() if pp.length > 1e-6 else n.orthogonal().normalized()
    apuntar(arm, muslo, lambda: arm.matrix_world @ P[pierna].head, S + n * a * ca + pp * a * sa)
    apuntar(arm, pierna, lambda: arm.matrix_world @ P[pierna].tail, T)


def ejes(r):
    R3 = r.matrix_world.to_3x3(); vl.update()
    ojos = [m for m in mallas(r) if m.name.startswith("ojo_")]
    c = sum((sum((m.matrix_world @ v.co for v in m.data.vertices), Vector()) / len(m.data.vertices) for m in ojos), Vector()) / len(ojos)
    f = c - r.matrix_world.translation; f.z = 0; f.normalize(); return f, f.cross(UP)


def mat_textura(nombre, archivo, tinte=None, alfa=False, por_metro=False, oscuro=1.0):
    """textura real de minecraft, pixelada (Closest); tinte = color del bioma para pasto/hojas"""
    m = bpy.data.materials.new(nombre); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; Lk = nt.links
    b = N["Principled BSDF"]; it = N.new("ShaderNodeTexImage"); it.image = bpy.data.images.load(TEX + archivo, check_existing=True); it.interpolation = 'Closest'
    if por_metro:
        tc = N.new("ShaderNodeTexCoord"); Lk.new(tc.outputs["Object"], it.inputs["Vector"])
    col = it.outputs["Color"]
    if tinte or oscuro != 1.0:
        mx = N.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs["Factor"].default_value = 1.0
        t = tinte or (1, 1, 1); mx.inputs[7].default_value = (t[0] * oscuro, t[1] * oscuro, t[2] * oscuro, 1)
        Lk.new(col, mx.inputs[6]); col = mx.outputs[2]
    Lk.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.95
    if alfa:
        Lk.new(it.outputs["Alpha"], b.inputs["Alpha"])
        try: m.surface_render_method = 'DITHERED'
        except Exception: m.blend_method = 'HASHED'
    return m


def mat_emision(nombre, color, fuerza):
    m = bpy.data.materials.new(nombre); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
    e.inputs[0].default_value = (*color, 1); e.inputs[1].default_value = fuerza; nt.links.new(e.outputs[0], o.inputs[0]); return m


def pose_corredor(r, sufijo, adelante_der=True, inclina=22, brazo_alto=0.12):
    """humanoide (rig tipo mixamo de Alfred / zombie) en zancada de sprint"""
    arm = arma_de(r); P = arm.pose.bones; fw, rt = ejes(r)
    for b in P: b.rotation_mode = 'XYZ'
    rotar_mundo(arm, "Spine_" + sufijo, rt, -math.radians(inclina * 0.5))
    rotar_mundo(arm, "Spine1_" + sufijo, rt, -math.radians(inclina * 0.5))
    W = lambda: arm.matrix_world
    for s, delante in (("Right", adelante_der), ("Left", not adelante_der)):
        hip = W() @ P[s + "UpLeg_" + sufijo].head
        T = hip + fw * 0.38 - UP * 0.72 if delante else hip - fw * 0.38 - UP * 0.82
        ik2(arm, s + "UpLeg_" + sufijo, s + "knee_" + sufijo, T, fw)
        sh = W() @ P[s + "UpArm_" + sufijo].head; lado = 1 if s == "Right" else -1
        # brazo contrario a la pierna: adelante doblado / atras
        if not delante: Tm = sh + fw * 0.38 - UP * 0.05 + rt * lado * 0.05; polo = -UP - fw * 0.4 + rt * lado * 0.6
        else: Tm = sh - fw * 0.35 - UP * 0.55 + rt * lado * 0.12; polo = -UP + fw * 0.5
        ik2(arm, s + "UpArm_" + sufijo, s + "elbow_" + sufijo, Tm, polo)


def pose_zombie(r, sufijo, paso, inclina=10):
    arm = arma_de(r); P = arm.pose.bones; fw, rt = ejes(r); W = lambda: arm.matrix_world
    for b in P: b.rotation_mode = 'XYZ'
    rotar_mundo(arm, "Spine1_" + sufijo, rt, -math.radians(inclina))
    rotar_mundo(arm, "Neck_" + sufijo, fw, math.radians(12 * paso))
    for s in ("Right", "Left"):
        lado = 1 if s == "Right" else -1; sh = W() @ P[s + "UpArm_" + sufijo].head
        T = sh + fw * 0.95 - UP * (0.05 + 0.08 * lado * paso) + rt * lado * 0.05            # brazos estirados al frente
        apuntar(arm, s + "UpArm_" + sufijo, lambda s=s: W() @ P[s + "UpArm_" + sufijo].tail, T)
        apuntar(arm, s + "elbow_" + sufijo, lambda s=s: W() @ P[s + "elbow_" + sufijo].tail, T + fw * 0.2)
        hip = W() @ P[s + "UpLeg_" + sufijo].head; d = 1 if (lado * paso) > 0 else -1
        ik2(arm, s + "UpLeg_" + sufijo, s + "knee_" + sufijo, hip + fw * 0.32 * d - UP * 0.95, fw)


# ------------------------------------------------------------------ personajes
HACIA_CAMARA = Vector((0, -1, 0))
alfred = anexar("alfred.blend", "alfred", "alfred_mini")
for o in [x for x in alfred.children_recursive if x.name.split(".")[0] in ("wooden_pickaxe", "wooden_axe", "stone_axe")]:
    bpy.data.objects.remove(o)                                              # sin herramientas colgando
alfred.location = (1.25, -1.75, 0); alfred.rotation_euler = (0, 0, 0); mirar_hacia(alfred, HACIA_CAMARA + Vector((-0.25, 0, 0)))
pose_corredor(alfred, "alfred", adelante_der=True, inclina=24)
fwA, rtA = ejes(alfred); rotar_mundo(arma_de(alfred), "Neck_alfred", UP, math.radians(-28))   # mira de reojo a la horda
al_suelo(alfred, 0.03)

jerry = anexar("jerry.blend", "jerry", "jerry_mini")
with bpy.data.libraries.load(JERRY_RUN) as (src, dst): dst.actions = ["Dog_001_run"]
rig = arma_de(jerry); rig.animation_data_create(); rig.animation_data.action = dst.actions[0]
if hasattr(rig.animation_data, "action_slot") and rig.animation_data.action_suitable_slots: rig.animation_data.action_slot = rig.animation_data.action_suitable_slots[0]
FRAME = 6; sc.frame_set(FRAME)
jerry.location = (-1.0, -2.45, 0); jerry.scale = (1.15, 1.15, 1.15); mirar_hacia(jerry, HACIA_CAMARA + Vector((0.3, 0, 0))); al_suelo(jerry, 0.02)

# ------------------------------------------------------------------ EXPRESIONES DE SUSTO
MANDIBULA = 18; CEJAS = 0.025
def escalar_malla(o, sx, sy, sz, sube=0.0):
    """agranda la malla alrededor de su centro (solo en esta miniatura)"""
    me = o.data; c = sum((v.co for v in me.vertices), Vector()) / len(me.vertices)
    keys = me.shape_keys.key_blocks if me.shape_keys else [None]
    for kb in keys:
        pts = kb.data if kb else me.vertices
        for v in pts: d = v.co - c; v.co = c + Vector((d.x * sx, d.y * sy, d.z * sz)) + Vector((0, 0, sube))

def mover_hueso(arm, b, off_mundo):
    pb = arm.pose.bones[b]; M = pb.matrix.copy(); M.translation += arm.matrix_world.inverted().to_3x3() @ off_mundo; pb.matrix = M; vl.update()

def girar_hasta(arm, b, eje, ang, quiero):
    """gira `b` el angulo cuyo signo cumple quiero(punta_antes, punta_despues)"""
    pb = arm.pose.bones[b]; guard = pb.rotation_quaternion.copy() if pb.rotation_mode == 'QUATERNION' else pb.rotation_euler.copy()
    t0 = arm.matrix_world @ pb.tail; rotar_mundo(arm, b, eje, ang)
    if not quiero(t0, arm.matrix_world @ pb.tail):
        if pb.rotation_mode == 'QUATERNION': pb.rotation_quaternion = guard
        else: pb.rotation_euler = guard
        vl.update(); rotar_mundo(arm, b, eje, -ang)

# Alfred: ojos muy abiertos (mas altos y anchos)
negro = mat_emision("pupila_susto", (0.0, 0.0, 0.0), 1.0)
def pupila_delante(ojo, fw_, tam, sube=0.0):
    """pupila negra diminuta pegada al frente del ojo (cara de panico)"""
    vl.update(); dg = bpy.context.evaluated_depsgraph_get(); e = ojo.evaluated_get(dg); M = ojo.matrix_world
    pts = [M @ v.co for v in e.data.vertices]; c = sum(pts, Vector()) / len(pts); frente = max((p - c).dot(fw_) for p in pts)
    bpy.ops.mesh.primitive_cube_add(size=1, location=c + fw_ * (frente + 0.004) + UP * sube); pu = bpy.context.object
    pu.name = "pupila_" + ojo.name; pu.scale = (tam, tam, tam); pu.rotation_euler = (0, 0, math.atan2(-fw_.x, fw_.y))
    pu.scale = (tam, 0.006, tam * 1.3); pu.data.materials.append(negro)
fwA2, rtA2 = ejes(alfred)
for n in ("ojo_derecho_alfred", "ojo_izquierdo_alfred"):
    o = bpy.data.objects.get(n)
    if o: escalar_malla(o, 1.3, 1.0, 1.7); pupila_delante(o, fwA2, 0.032, 0.01)
# Jerry: congelar el frame de carrera, abrir la boca, cejas arriba y arqueadas, pupilas chicas, ojos grandes, orejas atras
sc.frame_set(FRAME); vl.update()
guardado = {b.name: (b.matrix_basis.copy()) for b in rig.pose.bones}
rig.animation_data.action = None
for b in rig.pose.bones: b.matrix_basis = guardado[b.name]
vl.update()
fwJ, rtJ = ejes(jerry)
if "jaw_bot" in rig.pose.bones: girar_hasta(rig, "jaw_bot", rtJ, math.radians(MANDIBULA), lambda a, b: b.z < a.z)   # boca abierta
for n in ("sejas_1_jerry", "sejas_2_jerry"):
    if n in rig.pose.bones: mover_hueso(rig, n, UP * CEJAS)                 # cejas arriba
for n in ("pupila_derecha_jerry", "pupila_izquierda_jerry"):           # pupilas chicas (susto), un pelo por delante del ojo
    o = bpy.data.objects.get(n)
    if o:
        escalar_malla(o, 0.6, 0.6, 0.6)
        loc_fw = o.matrix_world.inverted().to_3x3() @ (fwJ * 0.012)
        for v in o.data.vertices: v.co += loc_fw
for n in ("ojo_derecho_jerry", "ojo_izquierdo_jerry"):                    # ojos mas grandes + pupila nueva delante
    o = bpy.data.objects.get(n)
    if o: escalar_malla(o, 1.3, 1.3, 1.3); pupila_delante(o, fwJ, 0.035)
for n in ("pupila_derecha_jerry", "pupila_izquierda_jerry"):
    o = bpy.data.objects.get(n)
    if o: o.hide_render = True
# gotas de sudor
gota = mat_emision("gota_sudor", (0.45, 0.8, 1.0), 2.5)
def gotas(r, lado):
    vl.update(); pts = puntos(r); top = max(p.z for p in pts); c = sum(pts, Vector()) / len(pts); fw_, rt_ = ejes(r)
    for k, (dx, dz, t) in enumerate(((0.32, -0.12, 0.07), (0.42, -0.30, 0.05), (-0.35, -0.2, 0.06))):
        bpy.ops.mesh.primitive_cube_add(size=t, location=Vector((c.x, c.y, top)) + rt_ * dx * lado + UP * dz + fw_ * 0.12)
        g = bpy.context.object; g.name = "sudor_%s_%d" % (r.name, k); g.scale = (1, 1, 1.6); g.data.materials.append(gota)
gotas(alfred, 1); gotas(jerry, -1)

ZOMBIS = [("zombie_1.blend", "zombie_1", (-1.9, 1.6), 1), ("zombie_2.blend", "zombie_2", (0.4, 2.6), -1), ("zombie_3.blend", "zombie_3", (2.6, 1.9), 1),
          ("zombie_4.blend", "zombie_4", (-3.6, 4.2), -1), ("zombie_5.blend", "zombie_5", (1.6, 5.4), 1), ("zombie_1.blend", "zombie_1", (-0.9, 7.5), -1),
          ("zombie_2.blend", "zombie_2", (3.8, 6.8), 1), ("zombie_baby_1.blend", "zombie_baby_1", (0.15, 0.2), 1)]
ojo_rojo = mat_emision("ojo_zombie_brillo", (1.0, 0.0, 0.0), 8.0)          # rojo puro (no se blanquea)
zombis = []
for i, (archivo, raiz, (x, y), paso) in enumerate(ZOMBIS):
    try: z = anexar(archivo, raiz, "zombi_mini_%d" % i)
    except Exception as e: print("sin", archivo, e); continue
    z.location = (x, y, 0); mirar_hacia(z, Vector((alfred.location.x * 0.4 - x, -1 - y, 0)))
    try:
        suf = next(b.name for b in arma_de(z).data.bones if b.name.startswith("Hips_")).split("Hips_")[1]
        pose_zombie(z, suf, paso)
    except Exception as e: print("pose zombie", e)
    al_suelo(z, 0.0)
    for m in mallas(z):
        if m.name.startswith("ojo_"):
            m.data.materials.clear(); m.data.materials.append(ojo_rojo)
            vl.update(); c = sum((m.matrix_world @ v.co for v in m.data.vertices), Vector()) / len(m.data.vertices)
            ld = bpy.data.lights.new("brillo_" + m.name, 'POINT'); ld.color = (1, 0.02, 0.0); ld.energy = 2.5 if "baby" in archivo else 5; ld.shadow_soft_size = 0.02; ld.use_shadow = False
            lo = bpy.data.objects.new("brillo_" + m.name, ld); sc.collection.objects.link(lo); lo.location = c + Vector((0, -0.18, 0))
    zombis.append(z)

# ------------------------------------------------------------------ suelo de pasto pixelado, luna cuadrada, niebla
bpy.ops.mesh.primitive_plane_add(size=120, location=(0, 20, 0)); suelo = bpy.context.object; suelo.name = "suelo_pasto"
m = bpy.data.materials.new("pasto_pixel"); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; Lk = nt.links
bsdf = N["Principled BSDF"]; tc = N.new("ShaderNodeTexCoord"); mul = N.new("ShaderNodeVectorMath"); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = (16, 16, 16)
fl = N.new("ShaderNodeVectorMath"); fl.operation = 'FLOOR'; wn = N.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = '3D'
cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.10, 0.28, 0.05, 1); cr.color_ramp.elements[1].color = (0.25, 0.55, 0.12, 1)
Lk.new(tc.outputs["Object"], mul.inputs[0]); Lk.new(mul.outputs[0], fl.inputs[0]); Lk.new(fl.outputs[0], wn.inputs["Vector"])
Lk.new(wn.outputs["Value"], cr.inputs[0]); Lk.new(cr.outputs[0], bsdf.inputs["Base Color"]); bsdf.inputs["Roughness"].default_value = 0.9
suelo.data.materials.clear(); suelo.data.materials.append(mat_textura("pasto_mc", "grass_block_top.png", (0.42, 0.68, 0.28), por_metro=True, oscuro=0.75))

bpy.ops.mesh.primitive_plane_add(size=7, location=(-30, 60, 36)); luna = bpy.context.object; luna.name = "luna_cuadrada"
luna.rotation_euler = (math.radians(90), 0, 0); luna.data.materials.append(mat_emision("luna", (0.85, 0.92, 1.0), 3.0)); bpy.data.objects.remove(luna)   # el bosque la tapa: fuera

w = bpy.data.worlds.new("noche_mini"); sc.world = w; w.use_nodes = True; wn_ = w.node_tree.nodes; wl = w.node_tree.links
wn_["Background"].inputs[0].default_value = (0.003, 0.005, 0.018, 1); wn_["Background"].inputs[1].default_value = 1.0
vol = wn_.new("ShaderNodeVolumePrincipled"); vol.inputs["Density"].default_value = 0.012; vol.inputs["Color"].default_value = (0.45, 0.6, 1.0, 1)
wn_.remove(vol)                                                            # sin niebla

def luz(tipo, nombre, loc, color, energia, mira=None, tam=1.0):
    d = bpy.data.lights.new(nombre, tipo); d.color = color; d.energy = energia
    if tipo == 'AREA': d.size = tam
    o = bpy.data.objects.new(nombre, d); sc.collection.objects.link(o); o.location = loc
    if mira is not None:
        v = Vector(mira) - Vector(loc); o.rotation_euler = v.to_track_quat('-Z', 'Y').to_euler()
    return o
luz('SUN', "luna_contraluz", (0, 30, 20), (0.55, 0.65, 1.0), 0.8, mira=(0, 0, 0))
luz('AREA', "fuego_frente", (-2.8, -5.0, 1.6), (1.0, 0.5, 0.15), 230, mira=(0.0, -2.2, 1.0), tam=2.0)
luz('AREA', "clave_frente", (2.6, -5.4, 3.0), (1.0, 0.9, 0.8), 140, mira=(0.8, -1.8, 1.2), tam=1.5)
luz('AREA', "contraluz_heroes", (0.0, 0.8, 3.5), (0.4, 0.6, 1.0), 450, mira=(0.0, -2.2, 1.0), tam=3.0)
luz('POINT', "verde_horda", (0.5, 4.5, 2.2), (0.3, 1.0, 0.35), 260)
luz('POINT', "rojo_horda", (-3, 6.5, 1.5), (1.0, 0.1, 0.05), 900)

# ------------------------------------------------------------------ bosque de arboles de bloques (tronco de roble + copas de hojas)
import bmesh, random

def mat_pixel(nombre, c0, c1, escala=16, rugo=0.95):
    m = bpy.data.materials.new(nombre); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; Lk = nt.links
    b = N["Principled BSDF"]; tc = N.new("ShaderNodeTexCoord"); mu = N.new("ShaderNodeVectorMath"); mu.operation = 'MULTIPLY'
    mu.inputs[1].default_value = (escala, escala, escala); fl_ = N.new("ShaderNodeVectorMath"); fl_.operation = 'FLOOR'
    wn = N.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = '3D'; cr_ = N.new("ShaderNodeValToRGB")
    cr_.color_ramp.elements[0].color = (*c0, 1); cr_.color_ramp.elements[1].color = (*c1, 1)
    Lk.new(tc.outputs["Object"], mu.inputs[0]); Lk.new(mu.outputs[0], fl_.inputs[0]); Lk.new(fl_.outputs[0], wn.inputs["Vector"])
    Lk.new(wn.outputs["Value"], cr_.inputs[0]); Lk.new(cr_.outputs[0], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = rugo
    return m

def bloques(nombre, celdas, mat):
    bm = bmesh.new(); bm.loops.layers.uv.new("UVMap")
    for (x, y, z) in celdas:
        r_ = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True); bmesh.ops.translate(bm, verts=r_["verts"], vec=Vector((x + 0.5, y + 0.5, z + 0.5)))
    me = bpy.data.meshes.new(nombre); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(nombre, me); sc.collection.objects.link(o); me.materials.append(mat); return o

rng = random.Random(7); troncos = []; hojas = []
puestos = []
for _ in range(400):
    x = rng.randint(-26, 26); y = rng.randint(3, 34)
    if abs(x) < 4 + y * 0.12 and y < 14: continue                       # deja libre el camino por donde huyen
    if any(abs(x - a) < 4 and abs(y - b_) < 4 for a, b_ in puestos): continue
    puestos.append((x, y))
    if len(puestos) >= 46: break
for x, y in puestos:
    h = rng.randint(4, 7)
    troncos += [(x, y, z) for z in range(h)]
    for z in range(h - 2, h + 2):
        rad = 2 if z < h else 1
        for dx in range(-rad, rad + 1):
            for dy in range(-rad, rad + 1):
                if abs(dx) == rad and abs(dy) == rad and rng.random() < 0.6: continue
                if dx == 0 and dy == 0 and z < h: continue
                hojas.append((x + dx, y + dy, z))
bloques("bosque_troncos", troncos, mat_textura("tronco_roble_mc", "oak_log.png", oscuro=0.8))
bloques("bosque_hojas", hojas, mat_textura("hojas_roble_mc", "oak_leaves.png", (0.30, 0.55, 0.18), alfa=True, oscuro=0.85))

# ------------------------------------------------------------------ camara (propia de la miniatura) y texto
cd = bpy.data.cameras.new("cam_mini"); cam = bpy.data.objects.new("cam_mini", cd); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0.1, -5.6, 0.55); objetivo = Vector((0.05, 0.5, 1.35))
cam.rotation_euler = (objetivo - cam.location).to_track_quat('-Z', 'Y').to_euler()
cd.lens = 22; cd.dof.use_dof = True; cd.dof.focus_object = alfred; cd.dof.aperture_fstop = 2.2

def texto(cuerpo, color, escala, pos, rot_z=0.0, borde=0.06):
    def uno(nombre, offset, mat, dz):
        tc_ = bpy.data.curves.new(nombre, 'FONT'); tc_.body = cuerpo; tc_.align_x = 'CENTER'; tc_.align_y = 'CENTER'
        if os.path.exists(FUENTE): tc_.font = bpy.data.fonts.load(FUENTE, check_existing=True)
        tc_.offset = offset; tc_.extrude = 0.02
        o = bpy.data.objects.new(nombre, tc_); sc.collection.objects.link(o); o.parent = cam
        o.location = (pos[0], pos[1], -3.0 + dz); o.scale = (escala,) * 3; o.rotation_euler = (0, 0, rot_z)
        o.data.materials.append(mat); return o
    negro = mat_emision("negro_" + cuerpo, (0, 0, 0), 1.0)                  # borde = 12 copias negras alrededor (sin picos)
    for k in range(12):
        ang = 2 * math.pi * k / 12; o = uno(cuerpo + "_borde%d" % k, 0.0, negro, -0.02)
        o.location.x += math.cos(ang) * borde * escala; o.location.y += math.sin(ang) * borde * escala
    uno(cuerpo, 0.0, mat_emision("color_" + cuerpo, color, 1.0), 0.0)
texto("¡CORRE!", (1.0, 0.86, 0.0), 0.62, (-0.62, 0.62), rot_z=math.radians(6), borde=0.07)

# ------------------------------------------------------------------ render
r = sc.render
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try: r.engine = eng; break
    except Exception: pass
r.resolution_x = 1920; r.resolution_y = 1080; r.resolution_percentage = 100
try:
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'Medium High Contrast'
except Exception: pass
try: sc.eevee.use_volumetric_shadows = True
except Exception: pass
sc.frame_set(FRAME)
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT + "miniatura_zombies.blend")
r.filepath = OUT + "miniatura_zombies.png"; r.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)
if os.environ.get("MINI_PRIMER_PLANO"):
    cc = bpy.data.cameras.new("cam_cara"); co = bpy.data.objects.new("cam_cara", cc); sc.collection.objects.link(co)
    fwJ2, _r = ejes(jerry); cab = jerry.matrix_world.translation + UP * 0.85
    co.location = cab + fwJ2 * 2.4 + UP * 0.2; co.rotation_euler = (cab - co.location).to_track_quat('-Z', 'Y').to_euler(); cc.lens = 35
    for o in sc.objects:
        if o.parent == cam: o.hide_render = True
    sc.camera = co; r.resolution_x = 800; r.resolution_y = 600; r.filepath = OUT + "_cara_jerry.png"; bpy.ops.render.render(write_still=True)
print("RESULTADO listo", len(zombis), "zombies")
