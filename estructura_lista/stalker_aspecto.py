# -*- coding: utf-8 -*-
"""the_stalker_1.blend: aspecto del Stalker de las referencias (cuerpo de bloques que se deshace en fragmentos, vetas de carne roja,
boca circular con dientes en el pecho, ojos blancos brillantes que gotean).
Crea objetos nuevos (prefijo `stalker_fx_`) pesados al armature `torso_1` (cada fragmento copia los pesos del vertice mas cercano de
la malla sobre la que nace), asi se mueven con el rig. No cambia las mallas originales; solo sube el brillo de los ojos.
Uso: exec(open(ruta, encoding="utf8").read()); construir()      (repetible: borra lo que creo antes)
"""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, kdtree

RIG = "torso_1"
CUERPO, CABEZA = "Mesh_3_1", "Mesh_2_1"
OJOS = ("Ojo_Terror_Rombo_L_1", "Ojo_Terror_Rombo_R_1")
BOCA_C, BOCA_R = Vector((0.0, 0.135, 1.70)), 0.2   # centro y radio medio del agujero del pecho, a ras de la cara (y 0.144; el frente es +Y)
ELIPSE = (0.16, 0.27, math.radians(12))                # semiejes (ancho, alto) e inclinacion del agujero
N_TENT = 34                                        # paredes abiertas del pecho: cada una es un tentaculo con 2 huesos (base y punta)
SEG_TENT = 5                                       # tramos a lo largo de cada pared para que se pueda doblar
HUESOS_PECHO = ["chest_open_1", "heart_1"]
PREFIJOS_TENT = ("chest_flap_", "chest_tent_", "tent_", "tooth_")
DIENTES = (("Mesh_1", "jaw_1", "tooth_up"), ("Mesh_0_1", "neck_front_1", "tooth_low"))   # malla con dientes pintados, hueso padre, prefijo
DEDOS = [d + l + "_1" for l in (".L", ".R") for d in ("finger_1", "finger_2", "finger_3", "thumb")]
SEG_DEDO = 4                                       # huesos por dedo-tentaculo (de la mano a la punta)
EXTREMIDADES = 1.0                                 # parte de las particulas que se dejan en brazos y piernas
N_CUERPO, N_CABEZA = 3200, 450


def _mat(nombre, color, rough=0.8, emision=None, fuerza=0.0):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled"); b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    if emision:
        b.inputs["Emission Color"].default_value = (*emision, 1); b.inputs["Emission Strength"].default_value = fuerza
    nt.links.new(b.outputs[0], out.inputs[0]); return m


def _carne():
    """carne roja humeda con vetas oscuras (ruido)"""
    m = bpy.data.materials.get("stalker_fx_carne") or bpy.data.materials.new("stalker_fx_carne"); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 18; nz.inputs["Detail"].default_value = 8
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.025, 0.002, 0.003, 1); cr.color_ramp.elements[1].color = (0.22, 0.012, 0.015, 1)
    cr.color_ramp.elements[0].position = 0.35; cr.color_ramp.elements[1].position = 0.7
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"]); nt.links.new(nz.outputs["Fac"], cr.inputs[0]); nt.links.new(cr.outputs[0], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.5; nt.links.new(b.outputs[0], out.inputs[0])
    vena = nt.nodes.new("ShaderNodeValToRGB"); vena.color_ramp.elements[0].position = 0.62; vena.color_ramp.elements[1].position = 0.7   # solo las vetas brillan
    vena.color_ramp.elements[0].color = (0, 0, 0, 1); vena.color_ramp.elements[1].color = (0.9, 0.05, 0.02, 1)
    nt.links.new(nz.outputs["Fac"], vena.inputs[0]); nt.links.new(vena.outputs[0], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = 0.25                 # vetas apenas encendidas: no tapan el corazon
    return m


def _mat_corazon():
    """rojo intenso; el brillo sale del centro de cada cara que mira a la camara y se oscurece en los bordes y en las venas,
    asi se lee la forma del corazon aunque la escena este a oscuras"""
    m = _mat("stalker_fx_corazon", (0.45, 0.0, 0.004), 0.35, emision=(1.0, 0.0, 0.0), fuerza=1.2); nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.45
    borde = nt.nodes.new("ShaderNodeValToRGB"); borde.color_ramp.elements[0].color = (1.0, 0.02, 0.01, 1); borde.color_ramp.elements[1].color = (0.05, 0.0, 0.0, 1)
    borde.color_ramp.elements[1].position = 0.75
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 30; nz.inputs["Detail"].default_value = 6
    venas = nt.nodes.new("ShaderNodeValToRGB"); venas.color_ramp.elements[0].position = 0.45; venas.color_ramp.elements[1].position = 0.52
    venas.color_ramp.elements[0].color = (0.15, 0.0, 0.0, 1); venas.color_ramp.elements[1].color = (1, 1, 1, 1)
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
    nt.links.new(lw.outputs["Facing"], borde.inputs[0]); nt.links.new(nz.outputs["Fac"], venas.inputs[0])
    nt.links.new(borde.outputs[0], mx.inputs[6]); nt.links.new(venas.outputs[0], mx.inputs[7]); nt.links.new(mx.outputs[2], b.inputs["Emission Color"])
    return m


def _quitar():
    for o in [o for o in bpy.data.objects if o.name.startswith("stalker_fx_")]:
        me = o.data; bpy.data.objects.remove(o, do_unlink=True)
        if me and me.users == 0:
            if isinstance(me, bpy.types.Mesh): bpy.data.meshes.remove(me)
            elif isinstance(me, bpy.types.Light): bpy.data.lights.remove(me)


def _quitar_huesos():
    rig = bpy.data.objects[RIG]
    nombres = [b.name for b in rig.data.bones if b.name in HUESOS_PECHO or b.name.startswith(PREFIJOS_TENT)]
    if not nombres: return
    _modo_edicion(rig)
    for n in nombres: rig.data.edit_bones.remove(rig.data.edit_bones[n])
    bpy.ops.object.mode_set(mode='OBJECT')
    if rig.animation_data and rig.animation_data.action and rig.animation_data.action.name.startswith("stalker_tentaculos"):
        a = rig.animation_data.action; rig.animation_data.action = None; bpy.data.actions.remove(a)


def _modo_edicion(rig):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects: o.select_set(False)
    rig.select_set(True); bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT')


def _huesos_pecho(rad):
    """chest_open_1 (todo el pecho abierto) hijo de spine_1, heart_1 (latido) y chest_flap_N_1 (paredes por sectores, bisagra en el borde)"""
    rig = bpy.data.objects[RIG]; _modo_edicion(rig); eb = rig.data.edit_bones; Mi = rig.matrix_world.inverted()
    M = Matrix.Translation(BOCA_C) @ Matrix.Rotation(math.radians(-90), 4, 'X')
    raiz = eb.new("chest_open_1"); raiz.head = Mi @ (BOCA_C + Vector((0, -0.12, 0))); raiz.tail = Mi @ (BOCA_C + Vector((0, 0.02, 0))); raiz.parent = eb["spine_1"]
    hc = BOCA_C + Vector((0.0, -0.15, -0.01))
    h = eb.new("heart_1"); h.head = Mi @ hc; h.tail = Mi @ (hc + Vector((0, 0, 0.12))); h.parent = raiz
    for n in HUESOS_PECHO: eb[n].use_deform = True
    bpy.ops.object.mode_set(mode='OBJECT')


def _luces_pecho():
    """brillo rojo dentro del pecho (hijo del corazon) y un rebote suave en el borde"""
    rig = bpy.data.objects[RIG]
    for nombre, hueso, pos, e, rad_ in (("stalker_fx_luz_pecho", "chest_open_1", BOCA_C + Vector((0, 0.12, 0)), 1.5, 0.15),
                                         ("stalker_fx_luz_corazon", "heart_1", BOCA_C + Vector((0, -0.12, 0)), BRILLO_LUZ, 0.05)):
        ld = bpy.data.lights.new(nombre, "POINT"); ld.energy = e; ld.color = (1.0, 0.02, 0.01); ld.shadow_soft_size = rad_
        lo = bpy.data.objects.new(nombre, ld)
        for col in rig.users_collection: col.objects.link(lo)
        lo.parent = rig; lo.parent_type = 'BONE'; lo.parent_bone = hueso; bpy.context.view_layer.update(); lo.matrix_world = Matrix.Translation(pos)


LATIDO = 21                       # frames por latido a 24 fps = ~70 latidos por minuto (corazon en reposo)
# lub (cierre de las valvulas, fuerte) en 0, dub (mas debil) en 7, y diastole hasta el siguiente latido
CURVA_ESCALA = ((0, 1.0), (2, 1.14), (4, 1.0), (7, 1.0), (8, 1.08), (10, 0.98), (LATIDO, 1.0))
CURVA_BRILLO = ((0, 0.0), (1, 1.0), (3, 0.15), (6, 0.0), (8, 0.7), (10, 0.05), (13, 0.0), (LATIDO, 0.0))   # se enciende en cada golpe y se apaga
BRILLO_LUZ = 12.0                 # W de la luz del corazon en el golpe


def _ciclico(fc):
    for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'
    if not any(m.type == 'CYCLES' for m in fc.modifiers): fc.modifiers.new('CYCLES')


def _fcurves(idb):
    return [fc for lay in idb.animation_data.action.layers for st in lay.strips for cb in st.channelbags for fc in cb.fcurves]


def _latido():
    """la luz roja del corazon parpadea en bucle (modificador Cycles) con el lub-dub de un corazon real"""
    luz = bpy.data.objects["stalker_fx_luz_corazon"].data
    if luz.animation_data: luz.animation_data_clear()
    for f, v in CURVA_BRILLO:
        luz.energy = BRILLO_LUZ * v; luz.keyframe_insert("energy", frame=1 + f)
    for fc in _fcurves(luz):
        for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'
        fc.modifiers.new('CYCLES')


def _brillo_ojos():
    """una luz pequena delante de cada ojo (hija del hueso head_1): los ojos iluminan la cara como en la referencia"""
    rig = bpy.data.objects[RIG]
    for on in OJOS:
        ojo = bpy.data.objects[on]; ps = [ojo.matrix_world @ v.co for v in ojo.data.vertices]; c = sum(ps, Vector()) / len(ps)
        ld = bpy.data.lights.new("stalker_fx_luz_" + on, "POINT"); ld.energy = 6.0; ld.color = (0.8, 0.9, 1.0); ld.shadow_soft_size = 0.03
        lo = bpy.data.objects.new("stalker_fx_luz_" + on, ld)
        for col in rig.users_collection: col.objects.link(lo)
        lo.parent = rig; lo.parent_type = 'BONE'; lo.parent_bone = "head_1"
        bpy.context.view_layer.update(); lo.matrix_world = Matrix.Translation(c + Vector((0, 0.06, 0)))


def _nuevo(nombre, bm, mats):
    me = bpy.data.meshes.new(nombre); bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    o = bpy.data.objects.new(nombre, me); rig = bpy.data.objects[RIG]
    for c in rig.users_collection: c.objects.link(o)
    o.parent = rig; o.matrix_parent_inverse = rig.matrix_world.inverted()
    md = o.modifiers.new("Armature", "ARMATURE"); md.object = rig
    return o


def _pesos(o, fuente, vert_pesos):
    """vert_pesos: [(indices de vertices, indice del vertice de `fuente`)] -> copia los grupos de ese vertice"""
    for vi_list, src in vert_pesos:
        for g in fuente.data.vertices[src].groups:
            nombre = fuente.vertex_groups[g.group].name
            vg = o.vertex_groups.get(nombre) or o.vertex_groups.new(name=nombre)
            vg.add(vi_list, g.weight, 'REPLACE')


def _grupo_fijo(o, hueso):
    vg = o.vertex_groups.new(name=hueso); vg.add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')


def _fragmentos(nombre, fuente, n, rnd, mats, saltar):
    """cubitos sobre la superficie de `fuente` (muestreo por area), algunos despegados como si el cuerpo se deshiciera"""
    mw = fuente.matrix_world; me = fuente.data; kd = kdtree.KDTree(len(me.vertices))
    for v in me.vertices: kd.insert(mw @ v.co, v.index)
    kd.balance()
    caras = [(p, p.area) for p in me.polygons]; tot = sum(a for _, a in caras); acum = []; s = 0
    for p, a in caras: s += a; acum.append(s)
    import bisect
    bm = bmesh.new(); grupos = []; zmax = max((mw @ v.co).z for v in me.vertices)
    for _ in range(n * 3):
        if len(grupos) >= n: break
        p = me.polygons[min(len(caras) - 1, bisect.bisect(acum, rnd.random() * tot))]
        vs = [mw @ me.vertices[i].co for i in p.vertices]; w = [rnd.random() for _ in vs]; sw = sum(w)
        pt = sum((v * (k / sw) for v, k in zip(vs, w)), Vector()); nrm = (mw.to_3x3() @ p.normal).normalized()
        if saltar(pt, nrm): continue
        t = rnd.random(); lado = 0.012 + 0.045 * t * t                         # muchos chicos, pocos grandes
        fuera = lado * rnd.uniform(-0.45, 0.25) + (rnd.uniform(0.02, 0.07) if rnd.random() < 0.05 else 0.0)   # pegados a la piel; pocos se despegan
        c = pt + nrm * fuera
        z = nrm; x = z.orthogonal().normalized(); y = z.cross(x)
        if abs(z.z) < 0.7: x = Vector((0, 0, 1)).cross(z).normalized(); y = z.cross(x)      # placas alineadas como bloques
        R = Matrix((x, y, z)).transposed() @ Matrix.Rotation(rnd.uniform(-0.06, 0.06), 3, 'Z') @ Matrix.Rotation(rnd.uniform(-0.08, 0.08), 3, 'X')
        esc = Vector((lado * rnd.uniform(0.7, 1.6), lado * rnd.uniform(0.7, 1.4), lado * rnd.uniform(0.4, 1.0)))
        r = bmesh.ops.create_cube(bm, size=1.0)
        for v in r["verts"]: v.co = c + R @ Vector((v.co.x * esc.x, v.co.y * esc.y, v.co.z * esc.z))
        # color: oscuro casi siempre; carne roja mas abajo y en el centro (sangre que chorrea); a veces gris claro
        rojo = 0.08 + 0.22 * (1 - min(1.0, pt.z / zmax)) * (1 - min(1.0, abs(pt.x) / 0.35))
        u = rnd.random(); mi = 1 if u < rojo else (2 if u < rojo + 0.04 else 0)
        for f in {f for v in r["verts"] for f in v.link_faces}: f.material_index = mi
        _, src, _ = kd.find(pt); grupos.append(([v.index for v in r["verts"]], src))
    bm.verts.index_update()
    o = _nuevo(nombre, bm, mats); _pesos(o, fuente, grupos); return o


def perfil(semilla=21):
    """radio del agujero segun el angulo (marco local: x = derecha, y = abajo): elipse vertical asimetrica (mas ancha arriba, algo
    ladeada) con el borde roto en picos pequenos, como reventado desde dentro"""
    r = random.Random(semilla)
    ondas = [(k, r.uniform(0.02, 0.06) / k ** 0.5, r.uniform(0, 6.3)) for k in range(3, 11)]
    picos = [(r.uniform(0, 2 * math.pi), r.uniform(0.08, 0.22), r.uniform(0.08, 0.18)) for _ in range(9)]
    A, B, INCL = ELIPSE
    def rad(a):
        t = a - INCL
        base = A * B / math.sqrt((B * math.cos(t)) ** 2 + (A * math.sin(t)) ** 2)
        huevo = 1.0 - 0.16 * math.sin(a)                           # local y = abajo: mas ancha arriba, mas estrecha abajo
        f = 1.0 + sum(amp * math.sin(k * a + ph) for k, amp, ph in ondas)
        for a0, L, w in picos:
            d = math.atan2(math.sin(a - a0), math.cos(a - a0))
            f += L * max(0.0, 1 - abs(d) / w) ** 2
        return base * huevo * f
    return rad


def _boca(rnd, carne, dientes, negro):
    """pecho reventado: borde de carne desgarrado que sigue el perfil irregular, garganta irregular hacia dentro, dientes rotos sueltos,
    colgajos de la pared del pecho doblados hacia fuera (paredes al aire) y trozos despedidos"""
    rad = perfil(); bm = bmesh.new(); M = Matrix.Translation(BOCA_C) @ Matrix.Rotation(math.radians(-90), 4, 'X')   # eje local Z -> +Y del mundo
    seg = 120; ang = [2 * math.pi * i / seg for i in range(seg)]
    def P(a, rr, z): return M @ Vector((rr * math.cos(a), rr * math.sin(a), z))
    # garganta: capas que siguen el perfil, cada vez mas estrechas y hondas (carne -> negro)
    capas = [(1.0, 0.0), (0.97, -0.02), (0.82, -0.07), (0.62, -0.12), (0.4, -0.17), (0.15, -0.21)]
    prev = None
    for k, (fs, zz) in enumerate(capas):
        cur = [bm.verts.new(P(a, rad(a) * fs * rnd.uniform(0.94, 1.04), zz + rnd.uniform(-0.008, 0.008))) for a in ang]
        if prev:
            for i in range(seg):
                f = bm.faces.new((prev[i], prev[(i + 1) % seg], cur[(i + 1) % seg], cur[i])); f.material_index = 0 if k < 4 else 2; f.smooth = True
        prev = cur
    bm.faces.new(prev).material_index = 2
    # borde de carne desgarrado: tiras irregulares que asoman por el contorno
    for i in range(seg):
        a = ang[i]; r0 = rad(a); grosor = rnd.uniform(0.008, 0.03)
        if rnd.random() < 0.55:
            q = [P(a - 0.02, r0 - 0.01, 0.0), P(a + 0.03, r0 - 0.01, 0.0), P(a + 0.03, r0 + grosor, rnd.uniform(0.005, 0.02)), P(a - 0.02, r0 + grosor * 0.6, rnd.uniform(0.0, 0.015))]
            f = bm.faces.new([bm.verts.new(v) for v in q]); f.material_index = 0; f.smooth = True
    # dientes rotos: pocos, irregulares, algunos torcidos o partidos
    for i in range(34):
        a = rnd.uniform(0, 2 * math.pi); rr = rad(a) * rnd.uniform(0.6, 0.98); zz = -rnd.uniform(0.0, 0.1)
        L = rnd.uniform(0.02, 0.09) * (0.4 if rnd.random() < 0.25 else 1.0); w = rnd.uniform(0.008, 0.016)
        hacia = Vector((-math.cos(a), -math.sin(a), rnd.uniform(-0.3, 0.6))).normalized()
        lat = Vector((-math.sin(a), math.cos(a), 0)); base = Vector((rr * math.cos(a), rr * math.sin(a), zz))
        bs = [bm.verts.new(M @ (base + lat * w * math.cos(2 * math.pi * k / 5) + Vector((0, 0, w * math.sin(2 * math.pi * k / 5))))) for k in range(5)]
        pv = bm.verts.new(M @ (base + hacia * L))
        for k in range(5): bm.faces.new((bs[k], bs[(k + 1) % 5], pv)).material_index = 1
    # colgajos: trozos de la pared del pecho doblados hacia fuera desde el borde (cara exterior oscura, interior de carne)
    COLGAJOS.clear(); COLG_EXTRA.clear()
    for i in range(34):
        a = 2 * math.pi * i / 34 + rnd.uniform(-0.08, 0.08); r0 = rad(a); L = rnd.uniform(0.08, 0.2); w = rnd.uniform(0.05, 0.1); t = 0.02
        giro = math.radians(rnd.uniform(25, 75))                  # abiertas hacia fuera, como petalos del pecho reventado
        radial = Vector((math.cos(a), math.sin(a), 0)); tang = Vector((-math.sin(a), math.cos(a), 0))
        bisagra = radial * (r0 - 0.01) + Vector((0, 0, 0.01))
        dirc = (radial * math.cos(giro) + Vector((0, 0, 1)) * math.sin(giro)).normalized()   # se levanta hacia fuera del pecho
        nrm = dirc.cross(tang).normalized()
        if nrm.z < 0: nrm = -nrm
        L *= rnd.uniform(0.85, 1.15); secciones = []
        for si in range(SEG_TENT + 1):                            # secciones a lo largo de la pared (se estrecha hacia la punta)
            u = si / SEG_TENT; c = bisagra + dirc * L * u; ww = w * (1 - 0.45 * u); tt = t * (1 - 0.4 * u)
            secciones.append([bm.verts.new(M @ (c + tang * ww * v + nrm * tt * h)) for v, h in ((-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5))])
        for si in range(SEG_TENT):
            A, B_ = secciones[si], secciones[si + 1]
            for k in range(4):
                f = bm.faces.new((A[k], A[(k + 1) % 4], B_[(k + 1) % 4], B_[k])); f.material_index = 3 if k == 2 else 0   # cara exterior oscura, el resto carne
        bm.faces.new(list(reversed(secciones[0]))).material_index = 0; bm.faces.new(secciones[-1]).material_index = 0
        COLGAJOS.append((a, secciones, M @ bisagra, (M.to_3x3() @ dirc).normalized(), L))
        COLG_EXTRA.append(((M.to_3x3() @ nrm).normalized(), (M.to_3x3() @ tang).normalized(), w, t))
    _piel_rota(bm, M, rnd, rad)
    return _nuevo_boca(bm, carne, dientes, negro)


COLGAJOS = []
COLG_EXTRA = []                   # (normal exterior, tangente, ancho, grosor) de cada pared abierta, en el mundo


def nombre_tent(i, parte):
    return "chest_tent_%02d_%s_1" % (i + 1, parte)


def _nuevo_boca(bm, carne, dientes, negro):
    """todo el pecho abierto va al hueso chest_open_1; cada pared abierta a sus dos huesos de tentaculo (base -> punta, pesos graduales)"""
    bm.verts.index_update(); pesos = []
    for i, (a, secciones, _, _, _) in enumerate(COLGAJOS):
        for si, sec in enumerate(secciones):
            u = si / SEG_TENT; pesos.append(([v.index for v in sec], i, u))
    o = _nuevo("stalker_fx_boca", bm, [carne, dientes, negro, oscuro_mat()]); _grupo_fijo(o, "chest_open_1")
    for idx, i, u in pesos:
        o.vertex_groups["chest_open_1"].remove(idx)
        wb = 1.0 - max(0.0, min(1.0, (u - 0.3) / 0.5)); wt = 1.0 - wb
        for parte, wv in (("base", wb), ("punta", wt)):
            if wv > 0: (o.vertex_groups.get(nombre_tent(i, parte)) or o.vertex_groups.new(name=nombre_tent(i, parte))).add(idx, wv, 'REPLACE')
    return o


def nombre_dedo(dedo, k):
    return "tent_%s_%d" % (dedo, k + 1)


def _dedos_huesos_y_pesos():
    """cada dedo (un hueso largo que apunta hacia arriba) pasa a ser una cadena de SEG_DEDO huesos de la mano hacia la punta, hijos del
    antebrazo; los pesos del dedo en la malla del cuerpo se reparten por tramos segun la altura (mezcla suave entre tramos)"""
    rig = bpy.data.objects[RIG]; cuerpo = bpy.data.objects[CUERPO]; mw = rig.matrix_world
    datos = {}
    for d in DEDOS:
        b = rig.data.bones[d]; a, c = mw @ b.head_local, mw @ b.tail_local
        arriba, abajo = (c, a) if c.z > a.z else (a, c)              # de la mano (arriba) a la punta (abajo)
        datos[d] = (arriba, abajo, b.parent.name)
    _modo_edicion(rig); eb = rig.data.edit_bones; Mi = mw.inverted()
    for d, (arriba, abajo, padre) in datos.items():
        prev = eb[padre]
        for k in range(SEG_DEDO):
            h = arriba.lerp(abajo, k / SEG_DEDO); t = arriba.lerp(abajo, (k + 1) / SEG_DEDO)
            nb = eb.new(nombre_dedo(d, k)); nb.head = Mi @ h; nb.tail = Mi @ t; nb.parent = prev; nb.use_connect = k > 0; prev = nb
    bpy.ops.object.mode_set(mode='OBJECT')
    # pesos: del grupo del dedo a los tramos
    me = cuerpo.data; cw = cuerpo.matrix_world; movidos = 0
    for d, (arriba, abajo, _) in datos.items():
        vg = cuerpo.vertex_groups.get(d)
        if vg is None: continue
        nuevos = [cuerpo.vertex_groups.get(nombre_dedo(d, k)) or cuerpo.vertex_groups.new(name=nombre_dedo(d, k)) for k in range(SEG_DEDO)]
        largo = (arriba.z - abajo.z)
        for v in me.vertices:
            w = next((g.weight for g in v.groups if g.group == vg.index), 0.0)
            if w <= 0: continue
            u = max(0.0, min(0.999, (arriba.z - (cw @ v.co).z) / largo)) * SEG_DEDO - 0.5   # posicion en tramos (centro de cada tramo)
            k0 = int(math.floor(u)); f = u - k0
            for k, wk in ((k0, 1 - f), (k0 + 1, f)):
                k = max(0, min(SEG_DEDO - 1, k))
                if wk > 0: nuevos[k].add([v.index], w * wk, 'ADD')
            vg.remove([v.index]); movidos += 1
    return movidos


PUNO_TRAMOS = (0.0, 0.22, 0.38, 0.5)   # radianes por tramo al cerrar el puno (el primero fijo: el dedo nunca se despega)
PUNO_ABRE = -0.35                      # al abrir la palma, cuanto se abren hacia fuera (fraccion del cierre)
PUNO_PERIODO = 64                      # frames de abrir-cerrar
PUNO_RETRASO = 3                       # frames que tarda el movimiento en bajar de un tramo al siguiente (onda)


def _curva_puno(t):
    """0..1 a lo largo del ciclo -> cierre: palma abierta (negativo), cierra suave, aprieta, abre despacio"""
    c = 0.5 - 0.5 * math.cos(2 * math.pi * t)                      # 0 abierta -> 1 puno -> 0
    c = c ** 1.4
    return PUNO_ABRE + (1 - PUNO_ABRE) * c


def _dedos_mover(rnd):
    """las manos se abren (palma) y se cierran (puno): cada dedo se dobla en un solo plano, hacia la palma (que mira al cuerpo; el
    pulgar hacia los otros dedos), y el doblez baja de la mano a la punta con retraso para que sea organico. Cada dedo arranca 1-3
    frames despues que el anterior y la mano derecha va desfasada"""
    from mathutils import Quaternion
    rig = bpy.data.objects[RIG]; mw = rig.matrix_world
    for lado, desfase in ((".L", 0), (".R", 17)):
        hacia_cuerpo = Vector((1, 0, 0)) if lado == ".L" else Vector((-1, 0, 0))
        for n, d in enumerate([d for d in DEDOS if lado in d]):
            palma = -hacia_cuerpo if d.startswith("thumb") else hacia_cuerpo     # direccion a la que va la punta al cerrar
            inicio = desfase + n * 2 + rnd.randint(0, 1); fuerza = rnd.uniform(0.9, 1.1)
            for k in range(SEG_DEDO):
                hb = rig.data.bones[nombre_dedo(d, k)]; pb = rig.pose.bones[hb.name]; pb.rotation_mode = 'QUATERNION'
                eje = (hb.matrix_local.to_3x3().inverted() @ mw.to_3x3().inverted() @ Vector((0, 0, -1)).cross(palma)).normalized()
                for j in range(0, PUNO_PERIODO + 1, 4):
                    t = (j - inicio - PUNO_RETRASO * k) / PUNO_PERIODO
                    pb.rotation_quaternion = Quaternion(eje, PUNO_TRAMOS[k] * fuerza * _curva_puno(t))
                    pb.keyframe_insert("rotation_quaternion", frame=1 + j, group=pb.name)
                pb.rotation_quaternion = (1, 0, 0, 0)


BRILLO_FRAG = 5.0                      # brillo maximo de los trozos rojos del cuerpo
BRILLO_FREC = (0.04, 0.22)             # radianes por frame: cada trozo parpadea a su ritmo (entre ~1 y ~6 s por ciclo)


def _mat_rojo_parpadeo():
    """material de los trozos rojos: carne que se enciende y se apaga; cada trozo lee su atributo `brillo_rnd` (0..1) y con el
    saca su frecuencia y su fase; el tiempo sale de un driver (frame)"""
    m = bpy.data.materials.get("stalker_fx_rojo_parpadeo") or bpy.data.materials.new("stalker_fx_rojo_parpadeo"); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); N = nt.nodes.new; L = nt.links.new
    out = N("ShaderNodeOutputMaterial"); b = N("ShaderNodeBsdfPrincipled"); b.inputs["Base Color"].default_value = (0.2, 0.01, 0.012, 1); b.inputs["Roughness"].default_value = 0.5
    b.inputs["Emission Color"].default_value = (1.0, 0.04, 0.02, 1)
    at = N("ShaderNodeAttribute"); at.attribute_type = 'GEOMETRY'; at.attribute_name = "brillo_rnd"
    tiempo = N("ShaderNodeValue"); tiempo.name = "tiempo"
    fcd = tiempo.outputs[0].driver_add("default_value"); fcd.driver.expression = "frame"
    def op(o, a_, b_=None, v=None):
        n = N("ShaderNodeMath"); n.operation = o
        L(a_, n.inputs[0])
        if b_ is not None: L(b_, n.inputs[1])
        elif v is not None: n.inputs[1].default_value = v
        return n.outputs[0]
    frec = op('ADD', op('MULTIPLY', at.outputs["Fac"], v=BRILLO_FREC[1] - BRILLO_FREC[0]), v=BRILLO_FREC[0])
    fase = op('MULTIPLY', at.outputs["Fac"], v=731.0)
    onda = op('SINE', op('ADD', op('MULTIPLY', tiempo.outputs[0], frec), fase))
    nivel = op('POWER', op('MULTIPLY_ADD' if False else 'ADD', op('MULTIPLY', onda, v=0.5), v=0.5), v=3.0)   # 0..1, picos cortos
    L(op('MULTIPLY', nivel, v=BRILLO_FRAG), b.inputs["Emission Strength"]); L(b.outputs[0], out.inputs[0])
    return m


def _dientes():
    """los dientes (franjas rojas pintadas en la cara de delante de la mandibula y del cuello) se separan de la malla (cada columna de
    caras con textura opaca es un diente) y cada uno recibe su propio hueso, colgado del de la mandibula / cuello, con la raiz arriba"""
    rig = bpy.data.objects[RIG]; img = bpy.data.images["Image_0"]; W, H = img.size; px = img.pixels[:]
    def opaco(u, v):
        x = min(W - 1, int(u * W)); y = min(H - 1, int(v * H)); i = (y * W + x) * 4; return px[i + 3] > 0.5, px[i] > 0.4
    huesos = []
    for malla, padre, pref in DIENTES:
        o = bpy.data.objects[malla]; mw = o.matrix_world; bm = bmesh.new(); bm.from_mesh(o.data)
        uvl = bm.loops.layers.uv.active; dl = bm.verts.layers.deform.verify()
        ymax = max((mw @ v.co).y for v in bm.verts)
        frente = [f for f in bm.faces if (mw @ f.calc_center_median()).y > ymax - 0.01]
        cols = {}
        for f in frente:
            u = sum(l[uvl].uv.x for l in f.loops) / len(f.loops); v = sum(l[uvl].uv.y for l in f.loops) / len(f.loops)
            op, rojo = opaco(u, v); c = mw @ f.calc_center_median()
            cols.setdefault(round(c.x, 3), []).append((c.z, f, op, rojo))
        dientes = []
        for x, fs in sorted(cols.items()):
            if not any(rojo for _, _, _, rojo in fs): continue
            fs.sort(key=lambda t: -t[0]); caras = []
            if not fs[0][2]: fs.reverse()                          # dientes de abajo: crecen hacia arriba desde la encia
            for z, f, op, rojo in fs:                              # desde la encia mientras sea opaco
                if not op: break
                caras.append(f)
            if caras: dientes.append(caras)
        todas = {f for d in dientes for f in d}
        borde = [e for e in bm.edges if len(e.link_faces) == 2 and sum(f in todas for f in e.link_faces) == 1]
        borde += [e for e in bm.edges if len(e.link_faces) == 2 and all(f in todas for f in e.link_faces) and
                  next(i for i, d in enumerate(dientes) if e.link_faces[0] in d) != next(i for i, d in enumerate(dientes) if e.link_faces[1] in d)]
        bmesh.ops.split_edges(bm, edges=borde)                        # cada diente queda suelto del resto de la malla
        nombres = []
        for k, caras in enumerate(dientes):
            n = "%s_%d_1" % (pref, k + 1); vg = o.vertex_groups.get(n) or o.vertex_groups.new(name=n)
            vs = {v for f in caras for v in f.verts}
            for v in vs:
                v[dl].clear(); v[dl][vg.index] = 1.0
            ps = [mw @ v.co for v in vs]; top = max(p.z for p in ps); bot = min(p.z for p in ps); cx = sum(p.x for p in ps) / len(ps); cy = sum(p.y for p in ps) / len(ps)
            raiz, punta = (top, bot) if (mw @ caras[0].calc_center_median()).z > (mw @ caras[-1].calc_center_median()).z or len(caras) == 1 and fs[0][1] is caras[0] else (bot, top)
            nombres.append((n, Vector((cx, cy, raiz)), Vector((cx, cy, punta))))   # cabeza del hueso en la encia
        bm.to_mesh(o.data); bm.free(); o.data.update()
        huesos.append((padre, nombres))
    _modo_edicion(rig); eb = rig.data.edit_bones; Mi = rig.matrix_world.inverted()
    for padre, nombres in huesos:
        for n, h, t in nombres:
            b = eb.get(n) or eb.new(n); b.head = Mi @ h; b.tail = Mi @ t; b.parent = eb[padre]
    bpy.ops.object.mode_set(mode='OBJECT')
    return [n for _, ns_ in huesos for n, _, _ in ns_]


def _quitar_mitad_rojos(o, rnd):
    """borra la mitad de los trozos que parpadean (material 3) de `o`; devuelve cuantos borro"""
    bm = bmesh.new(); bm.from_mesh(o.data); bm.faces.ensure_lookup_table()
    cubos = {}
    for f in bm.faces:
        if f.material_index == 3: cubos.setdefault(f.index // 6, []).append(f)
    elegidos = rnd.sample(sorted(cubos), len(cubos) // 2)
    verts = {v for k in elegidos for f in cubos[k] for v in f.verts}
    bmesh.ops.delete(bm, geom=list(verts), context='VERTS'); bm.to_mesh(o.data); bm.free(); o.data.update()
    return len(elegidos)


ROJOS_EXTREMIDADES = 0.5          # parte de los puntos rojos de brazos y piernas que se borra


def _reducir_rojos_extremidades(o, rnd):
    """borra ROJOS_EXTREMIDADES de los trozos que parpadean en brazos y piernas (z < 1.22 o |x| > 0.27)"""
    bm = bmesh.new(); bm.from_mesh(o.data); bm.faces.ensure_lookup_table(); mw = o.matrix_world; cubos = {}
    for f in bm.faces:
        if f.material_index == 3: cubos.setdefault(f.index // 6, []).append(f)
    ext = [k for k, fs in cubos.items() if (lambda c: c.z < 1.22 or abs(c.x) > 0.27)(mw @ fs[0].calc_center_median())]
    elegidos = rnd.sample(sorted(ext), int(len(ext) * ROJOS_EXTREMIDADES))
    bmesh.ops.delete(bm, geom=list({v for k in elegidos for f in cubos[k] for v in f.verts}), context='VERTS'); bm.to_mesh(o.data); bm.free(); o.data.update()
    return len(elegidos)


def _rojos_en_pecho(n, rnd):
    """n trozos rojos que parpadean pegados sobre las paredes abiertas del pecho; pesados a los huesos de su tentaculo"""
    bm = bmesh.new(); pesos = []
    for _ in range(n):
        i = rnd.randrange(len(COLGAJOS)); a, _s, base, dirc, L = COLGAJOS[i]; nrm, tang, w, t = COLG_EXTRA[i]
        u = rnd.uniform(0.1, 0.92); lado = rnd.uniform(0.012, 0.03)
        c = base + dirc * L * u + tang * w * (1 - 0.45 * u) * rnd.uniform(-0.35, 0.35) + nrm * (t * (1 - 0.4 * u) * 0.5 + lado * 0.25)
        R = Matrix((dirc, tang, nrm)).transposed()
        r = bmesh.ops.create_cube(bm, size=1.0)
        for v in r["verts"]: v.co = c + R @ Vector((v.co.x * lado * rnd.uniform(1, 1.6), v.co.y * lado, v.co.z * lado * 0.6))
        pesos.append((r["verts"], i, u))
    bm.verts.index_update(); pesos = [([v.index for v in vs], i, u) for vs, i, u in pesos]
    o = _nuevo("stalker_fx_rojos_pecho", bm, [bpy.data.materials["stalker_fx_rojo_parpadeo"]])
    for idx, i, u in pesos:
        wb = 1.0 - max(0.0, min(1.0, (u - 0.3) / 0.5))
        for parte, wv in (("base", wb), ("punta", 1 - wb)):
            if wv > 0: (o.vertex_groups.get(nombre_tent(i, parte)) or o.vertex_groups.new(name=nombre_tent(i, parte))).add(idx, wv, 'REPLACE')
    at = o.data.attributes.new("brillo_rnd", 'FLOAT', 'FACE'); vals = []
    for k in range(len(o.data.polygons) // 6): vals += [rnd.random()] * 6
    at.data.foreach_set("value", vals)
    return o


def _parpadeo_fragmentos(objetos, rnd):
    """los trozos de carne (material 1) pasan al material que parpadea; cada trozo (6 caras de un cubo) recibe su propio brillo_rnd"""
    m = _mat_rojo_parpadeo()
    for o in objetos:
        me = o.data
        if len(me.materials) < 4: me.materials.append(m)
        at = me.attributes.get("brillo_rnd") or me.attributes.new("brillo_rnd", 'FLOAT', 'FACE')
        vals = [0.0] * len(me.polygons); cubo = None
        for p in me.polygons:
            if p.index % 6 == 0: cubo = rnd.random()
            vals[p.index] = cubo
            if p.material_index == 1: p.material_index = 3
        at.data.foreach_set("value", vals)


TENT_PERIODO = (40, 80)           # frames de un vaiven (cada tentaculo el suyo)
TENT_AMPLITUD = (0.18, 0.35)      # radianes del vaiven de la base; la punta se mueve mas y con retraso (onda)


def _tentaculos(semilla=31):
    """dos huesos por pared abierta (hijos de chest_open_1) y un movimiento propio de cada una: vaiven lento en dos ejes, con periodo,
    fase y amplitud al azar, y la punta con retraso para que ondulen como tentaculos (bucle con modificador Cycles)"""
    rnd = random.Random(semilla); rig = bpy.data.objects[RIG]; _modo_edicion(rig); eb = rig.data.edit_bones; Mi = rig.matrix_world.inverted()
    for i, (a, secciones, base, dirc, L) in enumerate(COLGAJOS):
        mid = base + dirc * L * 0.5; fin = base + dirc * L
        b1 = eb.new(nombre_tent(i, "base")); b1.head = Mi @ base; b1.tail = Mi @ mid; b1.parent = eb["chest_open_1"]
        b2 = eb.new(nombre_tent(i, "punta")); b2.head = Mi @ mid; b2.tail = Mi @ fin; b2.parent = b1; b2.use_connect = True
    bpy.ops.object.mode_set(mode='OBJECT')
    ad = rig.animation_data_create(); act = bpy.data.actions.new("stalker_tentaculos"); ad.action = act
    for i in range(len(COLGAJOS)):
        P = rnd.randint(*TENT_PERIODO); fase = rnd.uniform(0, 1); amp = rnd.uniform(*TENT_AMPLITUD); eje2 = rnd.uniform(0.4, 0.9)
        for parte, mult, retraso in (("base", 1.0, 0.0), ("punta", 1.6, 0.22)):
            pb = rig.pose.bones[nombre_tent(i, parte)]; pb.rotation_mode = 'XYZ'
            for k in range(9):                                    # 8 claves por ciclo
                t = k / 8; f = 1 + round(P * t)
                ang = 2 * math.pi * (t + fase - retraso)
                pb.rotation_euler = (amp * mult * math.sin(ang), 0.0, amp * mult * eje2 * math.sin(ang * 2 + 1.1) * 0.5)
                pb.keyframe_insert("rotation_euler", frame=f, group=pb.name)
            pb.rotation_euler = (0, 0, 0)
    # los dedos quedan quietos (los huesos tent_finger/thumb siguen en el rig por si se quieren animar: _dedos_mover)
    for fc in _fcurves(rig):
        for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'
        if not any(m.type == 'CYCLES' for m in fc.modifiers): fc.modifiers.new('CYCLES')


def oscuro_mat():
    return bpy.data.materials["stalker_fx_oscuro"]


def _piel_rota(bm, M, rnd, rad):
    """trozos despedidos por la explosion alrededor del agujero, levantados e inclinados"""
    for i in range(60):
        a = rnd.uniform(0, 2 * math.pi); rr = rad(a) * rnd.uniform(1.05, 1.5); lado = rnd.uniform(0.015, 0.045)
        c = Vector((rr * math.cos(a), rr * math.sin(a), rnd.uniform(0.0, 0.05)))
        R = Matrix.Rotation(a, 3, 'Z') @ Matrix.Rotation(rnd.uniform(-1.0, -0.2), 3, 'Y') @ Matrix.Rotation(rnd.uniform(-0.5, 0.5), 3, 'X')
        r = bmesh.ops.create_cube(bm, size=1.0)
        for v in r["verts"]: v.co = M @ (c + R @ Vector((v.co.x * lado * 1.3, v.co.y * lado, v.co.z * 0.014)))
        for f in {f for v in r["verts"] for f in v.link_faces}: f.material_index = 3 if rnd.random() < 0.6 else 0


def _corazon(rnd, mat, venas):
    """corazon dentro de la garganta: dos lobulos arriba, punta abajo y arterias saliendo por arriba (en coordenadas del mundo)"""
    C = BOCA_C + Vector((0.0, -0.15, -0.01)); bm = bmesh.new()
    for x in (-0.045, 0.045):                                      # lobulos
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=0.07, matrix=Matrix.Translation(C + Vector((x, 0, 0.03))))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.006, radius2=0.1, depth=0.15, matrix=Matrix.Translation(C + Vector((0, 0, -0.06))))
    for f in bm.faces: f.smooth = True; f.material_index = 0
    for x, ang in ((-0.035, -0.35), (0.01, 0.1), (0.045, 0.5)):    # arterias
        r = bmesh.ops.create_cone(bm, cap_ends=False, segments=8, radius1=0.02, radius2=0.015, depth=0.09,
                                  matrix=Matrix.Translation(C + Vector((x, -0.01, 0.12))) @ Matrix.Rotation(ang, 4, 'Y'))
        for f in {f for v in r["verts"] for f in v.link_faces}: f.smooth = True; f.material_index = 1
    bmesh.ops.rotate(bm, verts=bm.verts, cent=C, matrix=Matrix.Rotation(math.radians(-12), 3, 'Y'))   # algo ladeado
    o = _nuevo("stalker_fx_corazon", bm, [mat, venas]); _grupo_fijo(o, "heart_1")
    sd = o.modifiers.new("Subdivision", "SUBSURF"); sd.levels = sd.render_levels = 1
    o.modifiers.move(o.modifiers.find("Subdivision"), 0)
    return o


def _abrir_pecho():
    """agujero irregular en el pecho: boolean (diferencia) en la malla del cuerpo con un prisma del mismo perfil, hijo del hueso spine_1"""
    rig = bpy.data.objects[RIG]; cuerpo = bpy.data.objects[CUERPO]; rad = perfil()
    M = Matrix.Translation(BOCA_C) @ Matrix.Rotation(math.radians(-90), 4, 'X'); bm = bmesh.new(); seg = 120
    angs = [2 * math.pi * i / seg for i in range(seg)]
    arriba = [bm.verts.new(M @ Vector((rad(a) * 0.97 * math.cos(a), rad(a) * 0.97 * math.sin(a), 0.12))) for a in angs]
    abajo = [bm.verts.new(M @ Vector((rad(a) * 0.97 * math.cos(a), rad(a) * 0.97 * math.sin(a), -0.18))) for a in angs]
    for i in range(seg): bm.faces.new((arriba[i], arriba[(i + 1) % seg], abajo[(i + 1) % seg], abajo[i]))
    bm.faces.new(arriba); bm.faces.new(list(reversed(abajo))); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("stalker_fx_corte_pecho"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("stalker_fx_corte_pecho", me)
    for c in rig.users_collection: c.objects.link(o)
    o.parent = rig; o.parent_type = 'BONE'; o.parent_bone = "spine_1"; bpy.context.view_layer.update()
    o.matrix_world = Matrix.Identity(4); o.display_type = 'WIRE'; o.hide_render = True
    md = cuerpo.modifiers.get("stalker_boca") or cuerpo.modifiers.new("stalker_boca", "BOOLEAN")
    md.operation = 'DIFFERENCE'; md.solver = 'EXACT'; md.use_self = True; md.use_hole_tolerant = True; md.object = o   # el cuerpo tiene capas superpuestas
    return o


def _gotas_ojos(rnd, mat):
    """churretes oscuros que caen de los ojos"""
    bm = bmesh.new()
    for on in OJOS:
        ojo = bpy.data.objects[on]; ps = [ojo.matrix_world @ v.co for v in ojo.data.vertices]
        c = sum(ps, Vector()) / len(ps); zb = min(p.z for p in ps)
        for k in range(3):
            L = rnd.uniform(0.05, 0.16); w = rnd.uniform(0.008, 0.016); x = c.x + rnd.uniform(-0.03, 0.03)
            r = bmesh.ops.create_cube(bm, size=1.0)
            for v in r["verts"]: v.co = Vector((x + v.co.x * w, c.y + 0.004 + v.co.y * 0.006, zb + 0.01 - L / 2 + v.co.z * L))
    o = _nuevo("stalker_fx_gotas_ojos", bm, [mat]); _grupo_fijo(o, "head_1"); return o


def _oscurecer_base():
    """la textura original (Material_0) se oscurece casi a negro, como el cuerpo de la referencia (una sola vez)"""
    m = bpy.data.materials["Material_0"]; nt = m.node_tree
    if nt.nodes.get("stalker_oscurecer"): return
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'); entrada = b.inputs["Base Color"]
    if not entrada.links: return
    src = entrada.links[0].from_socket
    mx = nt.nodes.new("ShaderNodeMix"); mx.name = "stalker_oscurecer"; mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
    mx.inputs[0].default_value = 1.0; mx.inputs[7].default_value = (0.3, 0.29, 0.31, 1)
    nt.links.new(src, mx.inputs[6]); nt.links.new(mx.outputs[2], entrada)


ROJO_BRILLO = 6.0                 # cuanto brillan las partes rojas de la textura (franjas/dientes del cuello y pecho)


def _brillo_rojo_textura():
    """en Material_0 las partes rojas de la textura brillan con su propio color, mas cuanto mas roja es la zona (R - max(G, B))"""
    nt = bpy.data.materials["Material_0"].node_tree
    if nt.nodes.get("stalker_rojo_brilla"): return
    img = next(n for n in nt.nodes if n.type == 'TEX_IMAGE'); b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    sep = nt.nodes.new("ShaderNodeSeparateColor"); sep.name = "stalker_rojo_brilla"
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = 'MAXIMUM'
    rojo = nt.nodes.new("ShaderNodeMath"); rojo.operation = 'SUBTRACT'; rojo.use_clamp = True
    k = nt.nodes.new("ShaderNodeMath"); k.operation = 'MULTIPLY'; k.inputs[1].default_value = ROJO_BRILLO
    nt.links.new(img.outputs["Color"], sep.inputs[0]); nt.links.new(sep.outputs[1], mx.inputs[0]); nt.links.new(sep.outputs[2], mx.inputs[1])
    nt.links.new(sep.outputs[0], rojo.inputs[0]); nt.links.new(mx.outputs[0], rojo.inputs[1]); nt.links.new(rojo.outputs[0], k.inputs[0])
    nt.links.new(img.outputs["Color"], b.inputs["Emission Color"]); nt.links.new(k.outputs[0], b.inputs["Emission Strength"])


def construir(semilla=13):
    global RAD; RAD = perfil()
    _quitar(); _quitar_huesos(); _huesos_pecho(RAD); _dedos_huesos_y_pesos(); _dientes()
    rnd = random.Random(semilla); _quitar(); O = bpy.data.objects
    oscuro = _mat("stalker_fx_oscuro", (0.012, 0.011, 0.013), 0.9)
    carne = _carne()
    gris = _mat("stalker_fx_gris", (0.035, 0.034, 0.037), 0.75)
    sangre = _mat("stalker_fx_sangre", (0.08, 0.0, 0.003), 0.15)
    dientes = _mat("stalker_fx_dientes", (0.35, 0.16, 0.13), 0.3)
    negro = _mat("stalker_fx_garganta", (0.0, 0.0, 0.0), 1.0)
    def fuera_boca(pt, n):                                         # no tapar la boca del pecho; pocas en brazos y piernas
        d = Vector((pt.x - BOCA_C.x, BOCA_C.z - pt.z)); en_boca = d.length; lim = RAD(math.atan2(d.y, d.x))   # local de la boca: x, y = -z del mundo
        if (n.y > 0.3 and en_boca < lim + 0.05) or (pt.y > -0.06 and en_boca < lim + 0.02): return True   # ni encima ni dentro del agujero
        extremidad = pt.z < 1.22 or abs(pt.x) > 0.27
        return extremidad and rnd.random() > EXTREMIDADES
    def fuera_ojos(pt, n):                                         # no tapar los ojos
        return n.y > 0.5 and pt.z > 2.66 and abs(pt.x) < 0.17
    fr = _fragmentos("stalker_fx_fragmentos", O[CUERPO], N_CUERPO, rnd, [oscuro, carne, gris], fuera_boca)
    fc = _fragmentos("stalker_fx_fragmentos_cabeza", O[CABEZA], N_CABEZA, rnd, [oscuro, carne, gris], fuera_ojos)
    _parpadeo_fragmentos((fr, fc), rnd)
    boca = _boca(rnd, carne, dientes, negro); _tentaculos()
    movidos = sum(_quitar_mitad_rojos(o, rnd) for o in (fr, fc)); _rojos_en_pecho(movidos, rnd)
    _reducir_rojos_extremidades(fr, rnd)
    venas = _mat("stalker_fx_venas", (0.12, 0.02, 0.05), 0.35)
    # el corazon es una luz roja que parpadea con el ritmo de un corazon real (ver _latido)
    _abrir_pecho(); _luces_pecho(); _latido()
    gotas = _gotas_ojos(rnd, sangre)
    _oscurecer_base(); _brillo_rojo_textura()                    # los ojos brillan solo por su malla (emision), sin luces
    # ojos blancos brillantes
    for on in OJOS:
        for s in O[on].material_slots:
            for nd in s.material.node_tree.nodes:
                if nd.type == 'EMISSION': nd.inputs["Color"].default_value = (0.85, 0.93, 1.0, 1); nd.inputs["Strength"].default_value = 25.0
    return {"fragmentos_cuerpo": len(fr.data.polygons) // 6, "fragmentos_cabeza": len(fc.data.polygons) // 6, "boca_caras": len(boca.data.polygons), "gotas": len(gotas.data.polygons) // 6}
