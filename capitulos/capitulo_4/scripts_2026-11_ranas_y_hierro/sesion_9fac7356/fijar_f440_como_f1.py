"""alfred_buscando_hierro.blend: el estado del frame FIJO (440, el final) pasa a ser el frame 1. Para cada datablock con
animacion se leen los valores de TODAS las propiedades animadas (accion activa + tiras NLA) evaluadas en f440, se quitan
las acciones y las pistas NLA (los drivers se conservan) y se escriben esos valores fijos. Se quitan los sonidos del VSE."""
import bpy
sc = bpy.context.scene
FIJO = globals().get("FIJO", 440)

def colecciones():
    for c in (bpy.data.objects, bpy.data.shape_keys, bpy.data.materials, bpy.data.node_groups, bpy.data.cameras,
              bpy.data.lights, bpy.data.worlds, bpy.data.scenes, bpy.data.meshes, bpy.data.armatures, bpy.data.curves):
        for idb in c: yield idb
    for m in bpy.data.materials:
        if m.node_tree: yield m.node_tree
    for w in bpy.data.worlds:
        if w.node_tree: yield w.node_tree

def curvas(action):
    if action is None: return []
    if hasattr(action, "fcurves") and not hasattr(action, "layers"): return list(action.fcurves)
    return [c for l in action.layers for st in l.strips for cb in st.channelbags for c in cb.fcurves]

sc.frame_set(FIJO)
bpy.context.view_layer.update()
valores = []          # (idb, data_path, index, valor)
for idb in colecciones():
    ad = getattr(idb, "animation_data", None)
    if not ad: continue
    acts = [ad.action] + [s.action for t in ad.nla_tracks for s in t.strips]
    vistos = set()
    for act in acts:
        for fc in curvas(act):
            k = (fc.data_path, fc.array_index)
            if k in vistos: continue
            vistos.add(k)
            try:
                prop = idb.path_resolve(fc.data_path)
            except Exception:
                continue
            try: v = prop[fc.array_index] if hasattr(prop, "__len__") and not isinstance(prop, str) else prop
            except Exception: v = prop
            valores.append((idb, fc.data_path, fc.array_index, v))
n_ids = 0
for idb in colecciones():
    ad = getattr(idb, "animation_data", None)
    if not ad or (not ad.action and not ad.nla_tracks): continue
    ad.action = None
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    n_ids += 1
puestos = fallos = 0
def dueno(idb, dp):
    if dp.endswith("]") and dp.rfind("[") > dp.rfind("."):          # propiedad personalizada: obj["x"] / bone["x"]
        pre, key = dp[:dp.rfind("[")], dp[dp.rfind("[") + 1:-1].strip('"')
        return (idb.path_resolve(pre) if pre else idb), key, True
    pre, attr = dp.rsplit(".", 1) if "." in dp else ("", dp)
    return (idb.path_resolve(pre) if pre else idb), attr, False
for idb, dp, i, v in valores:
    try:
        owner, attr, custom = dueno(idb, dp)
        if custom:
            cur = owner[attr]
            if hasattr(cur, "__len__") and not isinstance(cur, str): cur[i] = v
            else: owner[attr] = v
        else:
            cur = getattr(owner, attr)
            if hasattr(cur, "__len__") and not isinstance(cur, str):
                arr = list(cur); arr[i] = v; setattr(owner, attr, arr)
            else: setattr(owner, attr, v)
        puestos += 1
    except Exception as e:
        fallos += 1
ed = sc.sequence_editor
n_snd = 0
if ed:
    for s in list(ed.strips_all):
        if s.type == "SOUND": ed.strips.remove(s); n_snd += 1
for m in list(sc.timeline_markers): sc.timeline_markers.remove(m)
sc.frame_set(1)
result = {"datablocks_sin_animacion": n_ids, "valores_fijados": puestos, "fallos": fallos, "sonidos_quitados": n_snd, "frame": sc.frame_current}
