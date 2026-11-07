A = 798
"""Alfred, desde que sale del agujero (f771) rodando/sacudiendose y tirado, debe tocar el suelo real (bloques Z 13 / 12 /
11 segun la casilla). En cada frame se mide, vertice por vertice, la separacion entre la malla de Alfred y el bloque que
tiene debajo, y la raiz 'alfred' se baja/sube con una capa NLA ADD ('Alfred_toca_suelo') para que el punto mas bajo
apoye. Los corcoveos de 'Alfred_forcejea_suelo' se miden apagados, asi que siguen despegandolo a proposito."""
import bpy, math
from mathutils import Vector
sc = bpy.context.scene
al = bpy.data.objects["Armature"]; root = bpy.data.objects["alfred"]
A, B = globals().get("A", 789), globals().get("B", sc.frame_end)   # desde que esta del todo fuera del agujero
NOMBRE = "Alfred_toca_suelo"
for t in list(root.animation_data.nla_tracks):
    if t.name == NOMBRE: root.animation_data.nla_tracks.remove(t)
if NOMBRE.lower() in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[NOMBRE.lower()])
mallas = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("Mesh_") and o.name.endswith("_alfred")]
excl = {o.name for o in bpy.data.objects if o.type == "MESH" and (o.name.endswith("_alfred") or "chicken" in o.name or "jerry" in o.name or "cerdo" in o.name or o.name.startswith("pluma") or "_mesh_1" in o.name)}
dg = bpy.context.evaluated_depsgraph_get()
cache = {}
BLOQUES = {"Grass_Block", "Stone", "Dirt", "Gravel", "Coarse_Dirt", "Andesite", "Cobblestone", "Podzol", "Coal_Ore", "Diorite", "Granite", "Sand", "Clay", "Mossy_Cobblestone", "Rooted_Dirt"}
def suelo(x, y):
    k = (math.floor(x), math.floor(y))
    if k not in cache:
        o = Vector((k[0] + 0.5, k[1] + 0.5, 30)); z = None
        for _ in range(12):
            h = sc.ray_cast(dg, o, Vector((0, 0, -1)))
            if not h[0]: break
            ob = h[4]
            if ob.name.split(".")[0] not in BLOQUES or h[2].z < 0.5:        # solo bloques del terreno (no tapa, pasto, mobs...)
                o = h[1] - Vector((0, 0, 0.001)); continue
            z = h[1].z; break
        cache[k] = round(z) if z is not None and abs(z - round(z)) < 0.02 else z
    return cache[k]
fz = [t for t in al.animation_data.nla_tracks if t.name == "Alfred_forcejea_suelo"]
for t in fz: t.mute = True
gap = {}
for f in range(A, B + 1):
    sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
    g = 9e9
    for o in mallas:
        e = o.evaluated_get(dg); m = e.to_mesh(); M = e.matrix_world
        for v in m.vertices:
            p = M @ v.co; s = suelo(p.x, p.y)
            if s is not None and p.z - s < g: g = p.z - s
        e.to_mesh_clear()
    gap[f] = g
for t in fz: t.mute = False
# suavizado corto (3 f) para que no tiemble, sin dejarlo hundirse
fr = sorted(gap); corr = {}
for i, f in enumerate(fr):
    vec = [gap[fr[j]] for j in range(max(0, i - 1), min(len(fr), i + 2))]
    corr[f] = -min(gap[f], sum(vec) / len(vec))
act = bpy.data.actions.new(NOMBRE.lower()); prev = root.animation_data.action; root.animation_data.action = act
l0 = root.location.copy()
root.location = (0, 0, 0); root.keyframe_insert("location", index=2, frame=A - 1)
for f in fr:
    root.location = (0, 0, corr[f]); root.keyframe_insert("location", index=2, frame=f)
for c in act.layers[0].strips[0].channelbags[0].fcurves:
    for k in c.keyframe_points: k.interpolation = "LINEAR"
sl = root.animation_data.action_slot; root.animation_data.action = prev; root.location = l0
tr = root.animation_data.nla_tracks.new(); tr.name = NOMBRE
st = tr.strips.new(act.name, A - 1, act); st.action_slot = sl; st.blend_type = "ADD"; st.extrapolation = "HOLD_FORWARD"
muestras = {f: (round(gap[f] * 100, 1), round(corr[f] * 100, 1)) for f in fr[::15]}
result = {"separacion_cm_y_correccion_cm": muestras, "max_flotaba_cm": round(max(gap.values()) * 100, 1), "min_cm": round(min(gap.values()) * 100, 1)}
