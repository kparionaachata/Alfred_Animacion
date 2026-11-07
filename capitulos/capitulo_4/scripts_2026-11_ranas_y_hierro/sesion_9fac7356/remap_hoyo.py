"""Alfred se queda en el fondo del hoyo de f500 a f700: corrimiento global de tiempo +D desde T0 (todo lo que pasaba desde
T0 ocurre D frames despues; entre T0 y T0+D todo queda sostenido en su pose de T0).
Afecta: acciones activas (claves > T0), tiras NLA (las que empiezan >= T0 se mueven; las que cruzan T0 reciben el hueco
dentro de su accion), tiras del VSE que empiezan >= T0, marcadores, y el fin de escena.
NO afecta (se regeneran aparte con sus scripts o son de ambiente): cerdo, los 3 pollos, Jerry (rig, raiz y ojos),
plumas, y los sonidos del cerdo / pollo de ambiente / pollos del ataque / pasos de Jerry.
Parametros guardados en scene['remap_hoyo'] para poder invertirlo."""
import bpy, json
sc = bpy.context.scene
T0 = globals().get("T0", 610); D = globals().get("D", 90)
if sc.get("remap_hoyo"): raise RuntimeError("ya se aplico el remapeo: %s" % sc["remap_hoyo"])

def jer(n):
    o = bpy.data.objects.get(n); return [o] + list(o.children_recursive) if o else []
SKIP_OBJ = set()
for n in ("cerdo_1", "chicken_1", "chicken_2", "chicken_3", "jerry"): SKIP_OBJ |= {o.name for o in jer(n)}
for c in ("plumas_pollos", "cerdo_relleno", "pollo_relleno", "pollos_alfred"):
    if c in bpy.data.collections: SKIP_OBJ |= {o.name for o in bpy.data.collections[c].all_objects}
SKIP_SND = ("SND_cerdo", "SND_pollo_", "SND_pollos_alfred", "SND_pollos_desesp", "SND_paso_jerry_resig")

def mover_claves(action, desde_accion):
    n = 0
    for layer in action.layers:
        for st in layer.strips:
            for cb in st.channelbags:
                for fc in cb.fcurves:
                    for k in fc.keyframe_points:
                        if k.co.x > desde_accion + 1e-6:
                            k.co.x += D; k.handle_left.x += D; k.handle_right.x += D; n += 1
                    fc.update()
    return n

usos = {}
def todos_ids():
    for coll in (bpy.data.objects, bpy.data.shape_keys, bpy.data.materials, bpy.data.node_groups, bpy.data.cameras,
                 bpy.data.lights, bpy.data.worlds, bpy.data.scenes, bpy.data.meshes, bpy.data.armatures):
        for idb in coll:
            yield idb
def dueno_obj(idb):
    if isinstance(idb, bpy.types.Object): return idb.name
    if isinstance(idb, bpy.types.Key):
        u = idb.user
        for o in bpy.data.objects:
            if o.data == u: return o.name
    return None
for idb in todos_ids():
    ad = getattr(idb, "animation_data", None)
    if not ad: continue
    if dueno_obj(idb) in SKIP_OBJ: continue
    if ad.action: usos.setdefault(ad.action.name, []).append(("activa", idb))
    for t in ad.nla_tracks:
        for s in t.strips:
            if s.action: usos.setdefault(s.action.name, []).append(("tira", idb, t, s))

rep = {"acciones_activas": 0, "tiras_movidas": 0, "tiras_con_hueco": 0, "claves": 0, "sonidos": 0, "copias": 0}
hechas = set()
for idb in list(todos_ids()):
    ad = getattr(idb, "animation_data", None)
    if not ad or dueno_obj(idb) in SKIP_OBJ: continue
    if ad.action and ad.action.name not in hechas:
        rep["claves"] += mover_claves(ad.action, T0); hechas.add(ad.action.name); rep["acciones_activas"] += 1
    for t in ad.nla_tracks:
        for s in sorted(t.strips, key=lambda s: -s.frame_start):          # de atras hacia delante: sin solapes
            if s.frame_start >= T0:
                s.frame_start_ui = s.frame_start + D; rep["tiras_movidas"] += 1
            elif s.frame_end > T0 and s.action:
                act = s.action
                if len(usos.get(act.name, [])) > 1 or act.name in hechas:
                    act = act.copy(); slot = s.action_slot; s.action = act
                    try: s.action_slot = slot
                    except Exception: pass
                    rep["copias"] += 1
                a0 = s.action_frame_start + (T0 - s.frame_start) / max(1e-6, s.scale)
                rep["claves"] += mover_claves(act, a0); hechas.add(act.name)
                s.action_frame_end = s.action_frame_end + D
                s.frame_end_ui = s.frame_end + D
                rep["tiras_con_hueco"] += 1
ed = sc.sequence_editor
for s in sorted(ed.strips_all, key=lambda s: -s.frame_final_start):
    if s.frame_final_start >= T0 and not s.name.startswith(SKIP_SND):
        s.frame_start += D; rep["sonidos"] += 1
for m in sc.timeline_markers:
    if m.frame >= T0: m.frame += D
sc.frame_end = sc.frame_end + D
bpy.app.driver_namespace["_FIN_ESCENA"] = sc.frame_end
sc["remap_hoyo"] = json.dumps({"T0": T0, "D": D, "skip_obj": sorted(SKIP_OBJ)[:50]})
rep["frame_end"] = sc.frame_end
result = rep
