"""Arma de cine: subdivide un arma de biblioteca_personajes/armas y le rehace las texturas. El .blend original no se guarda.

blender -b <arma>.blend --factory-startup --python arma_cine.py -- [carpeta_salida]
Salida por defecto: <carpeta del arma>/cine/
    <arma>_cine.blend            el arma montada: piezas bajo un empty <arma> con la propiedad "hueso" del original
    vista.png
    piezas/<pieza>/<pieza>.blend + vista.png   cada pieza por separado, como las prendas
1) Malla: suelda, marca como pliegue las aristas vivas y subdivide (2 niveles); las UV se conservan.
2) Piezas: cada cara se clasifica por el color del juego en su UV (madera / hierro / laton) y luego por piezas sueltas.
3) Texturas: el color del juego (2048 px para todo el equipo, borroso en el arma) queda de base y encima se dibuja
   en alta resolucion la veta de la madera, el pulido y las rayas del hierro y el laton, con desgaste de campana.
"""
import math, os, sys
import bpy, bmesh
import numpy as np
from mathutils import Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ORIGEN = bpy.data.filepath
NOMBRE = os.path.splitext(os.path.basename(ORIGEN))[0]
SALIDA = os.path.abspath(ARGS[0]) if ARGS and ARGS[0] else os.path.join(os.path.dirname(ORIGEN), "cine")
ANGULO_VIVO = 80          # aristas con mas angulo entre caras: pliegue total, no se redondean
NIVELES = 2
ISLA_MIN = 24       # caras (ya subdivididas): una pieza menor es ruido de la textura

src = next(o for o in bpy.data.objects if o.type == "MESH")
hueso = src.get("hueso", "")
img = next(n.image for n in src.data.materials[0].node_tree.nodes if n.type == "TEX_IMAGE" and n.image.name.endswith("_difusa"))
W, H = img.size
PX = np.array(img.pixels[:], np.float32).reshape(H, W, 4)[:, :, :3]


# ---------------------------------------------------------------- 1) malla subdividida
def subdividir(o):
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=.0004)
    cr = bm.edges.layers.float.get("crease_edge") or bm.edges.layers.float.new("crease_edge")
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(ANGULO_VIVO):e[cr] = 1.
    bm.to_mesh(me); bm.free()
    md = o.modifiers.new("sub", "SUBSURF"); md.levels = md.render_levels = NIVELES; md.uv_smooth = "PRESERVE_BOUNDARIES"
    md.use_limit_surface = True
    bpy.context.view_layer.objects.active = o
    with bpy.context.temp_override(object=o, active_object=o):bpy.ops.object.modifier_apply(modifier=md.name)


# ---------------------------------------------------------------- 2) clase de cada cara por el color del juego
def color_uv(u, v):return PX[int(np.clip(v % 1 * H, 0, H - 1)), int(np.clip(u % 1 * W, 0, W - 1))]
def clase(c):
    r, g, b = c
    if r - b > .09 and r > .25:return "laton"
    if r - b > .03 and r > g:return "madera"
    return "hierro"


def separar(o):
    me = o.data; uv = me.uv_layers.active.data
    cls = []
    for p in me.polygons:
        u = np.mean([uv[i].uv for i in p.loop_indices], axis=0)
        mu = [color_uv(*u)] + [color_uv(*(u * .5 + np.array(uv[i].uv) * .5)) for i in p.loop_indices]
        cls.append(clase(np.mean(mu, axis=0)))
    # una cara suelta rodeada de otra clase es ruido de la textura: toma la clase de sus vecinas
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    for _ in range(2):
        nuevo = list(cls)
        for f in bm.faces:
            vec = [cls[g.index] for e in f.edges for g in e.link_faces if g != f]
            if vec and vec.count(cls[f.index]) == 0:nuevo[f.index] = max(set(vec), key=vec.count)
        cls = nuevo
    # islas de pocas caras (esquirlas de la textura) pasan a la clase que las rodea
    for _ in range(6):
        hecho = set(); cambio = False
        for f0 in bm.faces:
            if f0.index in hecho:continue
            g = [f0]; st = [f0]; hecho.add(f0.index)
            while st:
                f = st.pop()
                for e in f.edges:
                    for h in e.link_faces:
                        if h.index not in hecho and cls[h.index] == cls[f0.index]:hecho.add(h.index); g.append(h); st.append(h)
            if len(g) < ISLA_MIN:
                ids = {f.index for f in g}
                vec = [cls[h.index] for f in g for e in f.edges for h in e.link_faces if h.index not in ids]
                if vec:
                    k = max(set(vec), key=vec.count)
                    for i in ids:cls[i] = k
                    cambio = True
        if not cambio:break
    bm.free()
    piezas = []
    for c in ("madera", "hierro", "laton"):
        idx = [i for i, k in enumerate(cls) if k == c]
        if not idx:continue
        bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if cls[f.index] != c], context="FACES")
        # piezas sueltas de esta clase
        caras = set(bm.faces); grupos = []
        while caras:
            f0 = caras.pop(); st = [f0]; g = [f0]
            while st:
                f = st.pop()
                for e in f.edges:
                    for h in e.link_faces:
                        if h in caras:caras.remove(h); st.append(h); g.append(h)
            grupos.append(g)
        grupos.sort(key=lambda g: -sum(f.calc_area() for f in g))
        for n, g in enumerate(grupos):
            b2 = bm.copy(); b2.faces.ensure_lookup_table(); keep = {f.index for f in g}
            bmesh.ops.delete(b2, geom=[f for f in b2.faces if f.index not in keep], context="FACES")
            m2 = bpy.data.meshes.new(f"{NOMBRE}_{c}_{n + 1:02d}"); b2.to_mesh(m2); b2.free()
            piezas.append((c, m2))
        bm.free()
    return piezas


# ---------------------------------------------------------------- 3) materiales de cine
def material(c):
    m = bpy.data.materials.new(f"{NOMBRE}_{c}_cine"); m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    p = next(n for n in N if n.type == "BSDF_PRINCIPLED")
    def nodo(t, **k):
        n = N.new(t)
        for a, v in k.items():setattr(n, a, v)
        return n
    def poner(s, v):
        if isinstance(v, (int, float, tuple)):s.default_value = v
        else:L.new(v, s)
    def mate(op, a, b=None, clamp=False):
        n = nodo("ShaderNodeMath", operation=op, use_clamp=clamp); poner(n.inputs[0], a)
        if b is not None:poner(n.inputs[1], b)
        return n.outputs[0]
    def rango(v, a, b, c_=0., d=1.):
        n = nodo("ShaderNodeMapRange", clamp=True, interpolation_type="SMOOTHSTEP"); poner(n.inputs[0], v)
        n.inputs[1].default_value, n.inputs[2].default_value, n.inputs[3].default_value, n.inputs[4].default_value = a, b, c_, d
        return n.outputs[0]
    def mezcla(f, a, b, tipo="MIX"):
        n = nodo("ShaderNodeMix", data_type="RGBA", blend_type=tipo, clamp_result=True)
        c4 = lambda x: tuple(x) + (1,) if isinstance(x, tuple) and len(x) == 3 else x
        poner(n.inputs[0], f); poner(n.inputs[6], c4(a)); poner(n.inputs[7], c4(b))
        return n.outputs[2]
    tc = nodo("ShaderNodeTexCoord").outputs["Object"]
    def ruido(esc, det=4., estira=(1, 1, 1), dist=0.):
        mp = nodo("ShaderNodeMapping"); L.new(tc, mp.inputs[0]); mp.inputs["Scale"].default_value = tuple(esc * k for k in estira)
        n = nodo("ShaderNodeTexNoise"); L.new(mp.outputs[0], n.inputs["Vector"]); n.inputs["Detail"].default_value = det
        n.inputs["Scale"].default_value = 1.; n.inputs["Distortion"].default_value = dist
        return n.outputs["Fac"]
    juego = nodo("ShaderNodeTexImage", interpolation="Cubic"); juego.image = img
    L.new(nodo("ShaderNodeUVMap", uv_map=src.data.uv_layers.active.name).outputs[0], juego.inputs[0])
    gris = nodo("ShaderNodeRGBToBW"); L.new(juego.outputs[0], gris.inputs[0]); val = gris.outputs[0]  # luz y sombra pintadas del juego
    sucio = rango(ruido(9, 5), .5, .66)                                    # hollin de la polvora y grasa de las manos
    roce = rango(ruido(30, 4), .56, .68)
    if c == "madera":                                                      # nogal: veta larga a lo largo del arma (eje X)
        mp = nodo("ShaderNodeMapping"); L.new(tc, mp.inputs[0]); mp.inputs["Scale"].default_value = (6, 90, 90)
        dn = nodo("ShaderNodeTexNoise"); L.new(mp.outputs[0], dn.inputs["Vector"]); dn.inputs["Scale"].default_value = .6; dn.inputs["Detail"].default_value = 3
        vm = nodo("ShaderNodeVectorMath", operation="ADD"); L.new(mp.outputs[0], vm.inputs[0]); L.new(dn.outputs["Color"], vm.inputs[1])
        wv = nodo("ShaderNodeTexWave", wave_type="RINGS", rings_direction="X"); L.new(vm.outputs[0], wv.inputs["Vector"])
        wv.inputs["Scale"].default_value = .22; wv.inputs["Distortion"].default_value = 9; wv.inputs["Detail"].default_value = 6
        veta = wv.outputs["Fac"]; poro = rango(ruido(900, 2, (1, 6, 6)), .55, .7)
        col = mezcla(mate("ADD", mate("MULTIPLY", rango(veta, .15, .9), .6), mate("MULTIPLY", ruido(40, 5, (.15, 1, 1)), .4)), (.055, .026, .012), (.15, .08, .036))
        col = mezcla(mate("MULTIPLY", poro, .5), col, (.03, .014, .007))
        col = mezcla(.35, col, mezcla(1., juego.outputs[0], (.55, .4, .3), "MULTIPLY"))
        col = mezcla(mate("MULTIPLY", roce, .5), col, (.26, .16, .09))            # barniz gastado en las aristas de agarre
        col = mezcla(mate("MULTIPLY", sucio, .55), col, (.025, .02, .015))
        rug = mate("ADD", .6, mate("ADD", mate("MULTIPLY", poro, .25), mate("MULTIPLY", sucio, .2)), True)   # aceite seco de campana: mate
        alto = mate("ADD", mate("MULTIPLY", veta, .4), mate("MULTIPLY", poro, -.6)); metal = 0.; dist = .0004
    else:                                                                  # hierro o laton de campana: mate, con polvo y hollin, sin oxido
        base = (.085, .085, .09) if c == "hierro" else (.30, .21, .08)
        raya = rango(ruido(260, 2, (.08, 1, 1)), .6, .66)                     # rayas a lo largo del canon
        picado = rango(ruido(450, 2), .68, .74)
        polvo = rango(ruido(14, 5), .46, .64)
        col = mezcla(.25, base, mezcla(1., juego.outputs[0], base, "MULTIPLY"))
        col = mezcla(mate("MULTIPLY", raya, .35), col, tuple(min(1, k * 1.3) for k in base))
        col = mezcla(mate("MULTIPLY", roce, .35), col, tuple(min(1, k * 1.2) for k in base))
        col = mezcla(mate("MULTIPLY", picado, .6), col, (.04, .032, .025))
        col = mezcla(mate("MULTIPLY", polvo, .3), col, (.11, .09, .065))           # polvo y barro seco
        col = mezcla(mate("MULTIPLY", sucio, .6), col, (.02, .018, .015))          # hollin y grasa
        rug = mate("ADD", .55, mate("ADD", mate("MULTIPLY", raya, -.08), mate("MULTIPLY", mate("MAXIMUM", mate("MAXIMUM", sucio, picado), polvo), .35)), True)
        alto = mate("ADD", mate("MULTIPLY", raya, .3), mate("MULTIPLY", picado, -.8)); dist = .00015
        metal = mate("SUBTRACT", 1., mate("MULTIPLY", mate("MAXIMUM", sucio, polvo), .7))
    col = mezcla(.5, col, mezcla(1., col, mate("MULTIPLY", rango(val, .05, .45, .55, 1.15), 1.), "MULTIPLY"))
    L.new(col, p.inputs["Base Color"]); L.new(rug, p.inputs["Roughness"])
    if isinstance(metal, float):p.inputs["Metallic"].default_value = metal
    else:L.new(metal, p.inputs["Metallic"])
    bp = nodo("ShaderNodeBump"); bp.inputs["Distance"].default_value = dist; bp.inputs["Strength"].default_value = .6; L.new(alto, bp.inputs["Height"])
    L.new(bp.outputs[0], p.inputs["Normal"])
    return m


# ---------------------------------------------------------------- foto
def foto(ruta, objs):
    sc = bpy.context.scene; r = sc.render; sc.render.engine = "CYCLES"; sc.cycles.device = "GPU"; sc.cycles.samples = 32
    r.resolution_x, r.resolution_y = 1400, 500; r.filepath = ruta; sc.view_settings.view_transform = "AgX"
    w = bpy.data.worlds.new("_f"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (.3, .34, .4, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = .7; sc.world = w; ex = []
    for nom, en, rot in (("_sol", 3.2, (58, 0, -35)), ("_con", 1.2, (70, 0, 150))):
        s = bpy.data.objects.new(nom, bpy.data.lights.new(nom, "SUN")); s.data.energy = en; s.data.angle = math.radians(6)
        s.rotation_euler = [math.radians(a) for a in rot]; sc.collection.objects.link(s); ex.append(s)
    bpy.context.view_layer.update()
    esq = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector([min(p[i] for p in esq) for i in range(3)]); hi = Vector([max(p[i] for p in esq) for i in range(3)])
    cen, med = (lo + hi) / 2, hi - lo; d = max(med.length * 1.25, .05)
    cam = bpy.data.objects.new("_cam", bpy.data.cameras.new("_cam")); sc.collection.objects.link(cam); ex.append(cam)
    cam.data.type = "ORTHO"; cam.data.ortho_scale = max(med.x, med.y, med.z) * 1.08; cam.data.clip_start = .001
    cam.location = cen + Vector((0, -d, d * .25))                       # de costado: el arma entera en la foto
    cam.rotation_euler = (cen - cam.location).to_track_quat("-Z", "Y").to_euler(); sc.camera = cam
    bpy.ops.render.render(write_still=True)
    for o in ex:bpy.data.objects.remove(o)
    sc.world = None; bpy.data.worlds.remove(w)


# ---------------------------------------------------------------- proceso
os.makedirs(SALIDA, exist_ok=True)
base = src.copy(); base.data = src.data.copy(); bpy.context.scene.collection.objects.link(base)
base.matrix_world = src.matrix_world
subdividir(base)
piezas = separar(base)
mats = {}
raiz = bpy.data.objects.new(NOMBRE, None); raiz.empty_display_size = .2; bpy.context.scene.collection.objects.link(raiz)
raiz.matrix_world = src.matrix_world.copy()
if hueso:raiz["hueso"] = hueso
objs = []
for c, me in piezas:
    me.materials.clear(); me.materials.append(mats.setdefault(c, material(c)))
    me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(ANGULO_VIVO))
    o = bpy.data.objects.new(me.name, me); bpy.context.scene.collection.objects.link(o); o.parent = raiz
    o.cycles.shadow_terminator_geometry_offset = .3; o["clase"] = c; objs.append(o)
bpy.data.objects.remove(base); bpy.data.objects.remove(src)
for i in [i for i in bpy.data.images if i.name != img.name]:bpy.data.images.remove(i)
img.pack()
# cada pieza por separado
for o in objs:
    d = os.path.join(SALIDA, "piezas", o.name); os.makedirs(d, exist_ok=True)
    otros = [x for x in objs if x != o]
    for x in otros:x.hide_render = True
    foto(os.path.join(d, "vista.png"), [o])
    for x in otros:x.hide_render = False
    s2 = bpy.data.scenes.new(o.name); s2.collection.objects.link(o)          # escena propia: al abrirla se ve la pieza
    bpy.data.libraries.write(os.path.join(d, o.name + ".blend"), {s2}, compress=True)
    bpy.data.scenes.remove(s2)
foto(os.path.join(SALIDA, "vista.png"), objs)
for i in [i for i in bpy.data.images if i.name == "Render Result"]:bpy.data.images.remove(i)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SALIDA, NOMBRE + "_cine.blend"), compress=True, check_existing=False)
print("PIEZAS", [(o.name, o["clase"], len(o.data.polygons)) for o in objs])
print("FIN", SALIDA)
