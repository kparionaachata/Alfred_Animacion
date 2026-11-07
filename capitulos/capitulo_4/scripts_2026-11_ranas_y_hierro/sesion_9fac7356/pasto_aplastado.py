"""El pasto (Short_Grass, Tall_Grass, Fern) se aplasta por donde Alfred rueda y queda tirado (f771-fin). Short_Grass y Tall_Grass son una malla cada uno
(cada mata = 2 planos cruzados). Para cada mata se calcula el primer frame en que el cuerpo de Alfred (vertices a menos
de 35 cm del suelo) pasa a menos de 25 cm de ella -> atributo 'aplasta_t'; y la altura de su base -> 'z_base'.
Un modificador Geometry Nodes 'Pasto_aplastado' baja cada mata hacia su base desde ese frame: se aplasta en 3 frames
(85 %) y luego se levanta un poco (queda al 55 %), como el pasto real. No cambia la malla original (se puede quitar)."""
import bpy, math
from mathutils import Vector
sc = bpy.context.scene
A, B = 771, sc.frame_end
R_CONTACTO, ALTO_CONTACTO, CELDA = 0.25, 0.35, 0.25
mallas_alf = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("Mesh_") and o.name.endswith("_alfred")]
# --- 1) huella de Alfred en el suelo, frame a frame ---
huella = {}            # celda (i,j) -> primer frame
for f in range(A, B + 1):
    sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
    for o in mallas_alf:
        e = o.evaluated_get(dg); m = e.to_mesh(); M = e.matrix_world
        for v in m.vertices:
            p = M @ v.co
            suelo = math.floor(p.z + 1e-3) if False else None
            k = (math.floor(p.x / CELDA), math.floor(p.y / CELDA))
            # suelo aproximado: el bloque entero bajo el punto (Z 13 / 12 / 11): se usa la parte entera de la Z del punto
            if p.z - math.floor(p.z) < ALTO_CONTACTO and k not in huella: huella[k] = f
        e.to_mesh_clear()
nbr = int(math.ceil(R_CONTACTO / CELDA))
def primer_frame(x, y):
    i0, j0 = math.floor(x / CELDA), math.floor(y / CELDA); best = None
    for di in range(-nbr, nbr + 1):
        for dj in range(-nbr, nbr + 1):
            t = huella.get((i0 + di, j0 + dj))
            if t is not None:
                cx, cy = (i0 + di + 0.5) * CELDA, (j0 + dj + 0.5) * CELDA
                if (cx - x) ** 2 + (cy - y) ** 2 <= (R_CONTACTO + CELDA * 0.7) ** 2 and (best is None or t < best): best = t
    return best
# --- 2) atributos por mata ---
xs = [k[0] * CELDA for k in huella]; ys = [k[1] * CELDA for k in huella]
caja = (min(xs) - 1, max(xs) + 1, min(ys) - 1, max(ys) + 1)
res = {}
for nombre in ("Short_Grass", "Tall_Grass", "Fern"):
    o = bpy.data.objects[nombre]; me = o.data; W = o.matrix_world
    n = len(me.vertices)
    t_attr = [1.0e6] * n; zb = [0.0] * n
    co = [W @ v.co for v in me.vertices]
    for i in range(n): zb[i] = co[i].z
    tocadas = 0
    for poly in me.polygons:
        vs = list(poly.vertices)
        c = sum((co[i] for i in vs), Vector()) / len(vs)
        base = min(co[i].z for i in vs)
        for i in vs: zb[i] = min(zb[i], base)
        if not (caja[0] <= c.x <= caja[1] and caja[2] <= c.y <= caja[3]): continue
        t = primer_frame(c.x, c.y)
        if t is not None:
            tocadas += 1
            for i in vs: t_attr[i] = min(t_attr[i], float(t))
    for an, vals in (("aplasta_t", t_attr), ("z_base", zb)):
        if an in me.attributes: me.attributes.remove(me.attributes[an])
        at = me.attributes.new(an, "FLOAT", "POINT"); at.data.foreach_set("value", vals)
    res[nombre] = tocadas
# --- 3) Geometry Nodes ---
ng = bpy.data.node_groups.get("Pasto_aplastado")
if ng: bpy.data.node_groups.remove(ng)
ng = bpy.data.node_groups.new("Pasto_aplastado", "GeometryNodeTree")
ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
N = ng.nodes; L = ng.links
gi = N.new("NodeGroupInput"); go = N.new("NodeGroupOutput")
na_t = N.new("GeometryNodeInputNamedAttribute"); na_t.data_type = "FLOAT"; na_t.inputs["Name"].default_value = "aplasta_t"
na_z = N.new("GeometryNodeInputNamedAttribute"); na_z.data_type = "FLOAT"; na_z.inputs["Name"].default_value = "z_base"
pos = N.new("GeometryNodeInputPosition"); sep = N.new("ShaderNodeSeparateXYZ")
tiempo = N.new("GeometryNodeInputSceneTime")
def m(op, a=None, b=None, clamp=False):
    n = N.new("ShaderNodeMath"); n.operation = op; n.use_clamp = clamp
    for idx, v in ((0, a), (1, b)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[idx].default_value = v
        else: L.new(v, n.inputs[idx])
    return n.outputs[0]
dt = m("SUBTRACT", tiempo.outputs["Frame"], na_t.outputs[0])                  # frames desde que paso por encima
baja = m("MULTIPLY", m("DIVIDE", dt, 3.0, clamp=True), 0.85)                 # se aplasta en 3 frames
sube = m("MULTIPLY", m("DIVIDE", m("SUBTRACT", dt, 8.0), 30.0, clamp=True), 0.30)   # y se levanta un poco
k = m("SUBTRACT", baja, sube, clamp=True)
L.new(pos.outputs[0], sep.inputs[0])
alto = m("SUBTRACT", sep.outputs["Z"], na_z.outputs[0])
dz = m("MULTIPLY", m("MULTIPLY", alto, k), -1.0)
cmb = N.new("ShaderNodeCombineXYZ"); L.new(dz, cmb.inputs["Z"])
sp = N.new("GeometryNodeSetPosition")
L.new(gi.outputs[0], sp.inputs["Geometry"]); L.new(cmb.outputs[0], sp.inputs["Offset"]); L.new(sp.outputs[0], go.inputs[0])
for nombre in ("Short_Grass", "Tall_Grass", "Fern"):
    o = bpy.data.objects[nombre]
    for md in [md for md in o.modifiers if md.name == "Pasto_aplastado"]: o.modifiers.remove(md)
    md = o.modifiers.new("Pasto_aplastado", "NODES"); md.node_group = ng
res["celdas_huella"] = len(huella); res["frames"] = (A, B)
result = res
