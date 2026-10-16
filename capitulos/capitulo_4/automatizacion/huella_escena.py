# -*- coding: utf-8 -*-
"""HUELLA de la escena (dentro de Blender): un resumen de los DATOS guardados (objetos, acciones/claves, mallas, materiales, tiras de sonido,
propiedades) que NO depende del frame actual ni de la evaluacion. Sirve para saber si alguien toco la escena a mano desde la ultima reconstruccion
(si no se toco, se puede seguir desde un checkpoint sin perder nada). Devuelve {clave: md5} por cada bloque de datos -> se puede decir QUE cambio."""
import bpy, hashlib, json
import numpy as np

UI = {"show_expanded", "is_active", "is_override_data_editable", "show_in_editmode", "show_on_cage", "active", "show_viewport_bounds",
      "select", "hide_select", "is_property_set", "rna_type",
      "session_uid", "users", "is_runtime_data", "is_evaluated", "original", "is_missing", "is_embedded_data", "tag", "is_library_indirect",
      "use_extra_user", "is_editmode", "use_fake_user", "preview", "library_weak_reference", "override_library", "filepath", "filepath_raw"}


def _ruta(p):
    """ruta ABSOLUTA normalizada (las relativas cambian al guardar en otra carpeta)"""
    if not p: return p
    import os
    try: return os.path.normcase(os.path.normpath(bpy.path.abspath(p)))
    except Exception: return p


def _r(v, n=4):
    try: return round(float(v), n)
    except Exception: return str(v)


def _py(v):
    if hasattr(v, "to_dict"): return {k: _py(x) for k, x in v.to_dict().items()}
    if hasattr(v, "to_list"): return [_py(x) for x in v.to_list()]
    if isinstance(v, dict): return {k: _py(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)): return [_py(x) for x in v]
    if isinstance(v, float): return round(v, 4)
    if isinstance(v, (int, str, bool)) or v is None: return v
    if isinstance(v, bpy.types.ID): return "ID:" + v.name                    # un puntero a un objeto: su nombre (no la direccion en memoria)
    return str(v)


def _vivos(col):
    """los bloques sin usuarios no se guardan en el .blend: no cuentan"""
    return [x for x in col if x.users > 0 or x.use_fake_user]


def _props(idb):
    try: return {k: _py(idb[k]) for k in idb.keys() if not k.startswith(("_RNA_UI", "cadena_"))}       # cadena_*: opciones del panel
    except Exception: return {}


def _animadas(idb):
    """rutas (data_path) con claves o drivers: su valor cambia con el frame, no se miran"""
    s = set(); ad = getattr(idb, "animation_data", None)
    if not ad: return s
    for d in ad.drivers: s.add(d.data_path)
    acts = [ad.action] + [st.action for t in ad.nla_tracks for st in t.strips]
    for a in acts:
        if a is None: continue
        for l in a.layers:
            for st in l.strips:
                for cb in st.channelbags:
                    for fc in cb.fcurves: s.add(fc.data_path)
    return s


def _rna(x, an=(), pre=""):
    out = []
    for p in x.bl_rna.properties:
        k = p.identifier
        if k in UI or k == "name" or (pre + k) in an: continue
        try: v = getattr(x, k)
        except Exception: continue
        if p.type == "FLOAT": v = [_r(a) for a in np.ravel(np.array(v, dtype=float))] if getattr(p, "array_length", 0) else _r(v)
        elif p.type in ("INT", "BOOLEAN"): v = list(v) if getattr(p, "array_length", 0) else v
        elif p.type == "ENUM": v = sorted(v) if p.is_enum_flag else v
        elif p.type == "STRING": pass
        elif p.type == "POINTER" and not p.is_readonly: v = getattr(v, "name", None)
        else: continue
        out.append((k, v))
    return out


def _md5(*partes):
    h = hashlib.md5()
    for p in partes: h.update(p if isinstance(p, bytes) else repr(p).encode("utf-8", "replace"))
    return h.hexdigest()


def _arr(coleccion, attr, n, dtype=np.float32):
    a = np.empty(len(coleccion) * n, dtype=dtype)
    if len(coleccion): coleccion.foreach_get(attr, a)
    return np.round(a, 4).tobytes() if dtype == np.float32 else a.tobytes()


def _objeto(o):
    an = _animadas(o)
    d = [o.type, o.parent.name if o.parent else "", o.parent_type, o.parent_bone, o.data.name if o.data else "", o.rotation_mode,
         [_r(v) for fila in o.matrix_parent_inverse for v in fila]]
    for p in ("hide_viewport", "hide_render"):
        if p not in an: d.append((p, getattr(o, p)))
    for p in ("location", "rotation_euler", "rotation_quaternion", "scale", "delta_location", "delta_rotation_euler", "delta_scale"):
        if p not in an: d.append((p, [_r(v) for v in getattr(o, p)]))
    d.append([(m.name, m.type, _rna(m, an, 'modifiers["%s"].' % m.name)) for m in o.modifiers])
    d.append([(c.name, c.type, _rna(c, an, 'constraints["%s"].' % c.name)) for c in o.constraints])
    ad = o.animation_data
    if ad: d.append((ad.action.name if ad.action else "", getattr(getattr(ad, "action_slot", None), "identifier", ""), [t.name for t in ad.nla_tracks]))
    d.append(_props(o)); d.append([s.material.name if s.material else "" for s in o.material_slots])
    if o.type == "ARMATURE" and o.pose:
        for pb in o.pose.bones:
            pre = 'pose.bones["%s"].' % pb.name
            for p in ("location", "rotation_quaternion", "rotation_euler", "scale"):
                if pre + p not in an: d.append((pb.name, p, [_r(v) for v in getattr(pb, p)]))
            d.append((pb.name, _props(pb), [(c.name, c.type, _rna(c, an, pre + 'constraints["%s"].' % c.name)) for c in pb.constraints]))
    return _md5(d)


def _accion(a):
    partes = [a.name, [s.identifier for s in a.slots]]
    for l in a.layers:
        for st in l.strips:
            for cb in st.channelbags:
                partes.append(getattr(cb.slot, "identifier", ""))
                for fc in cb.fcurves:
                    kp = fc.keyframe_points
                    partes += [fc.data_path, fc.array_index, fc.extrapolation, fc.mute, len(fc.modifiers),
                               _arr(kp, "co", 2), _arr(kp, "handle_left", 2), _arr(kp, "handle_right", 2), _arr(kp, "interpolation", 1, np.int32)]
    return _md5(*partes)


def _arbol(nt, an):
    out = []
    for n in nt.nodes:
        ent = []
        for i, s in enumerate(n.inputs):
            if 'nodes["%s"].inputs[%d].default_value' % (n.name, i) in an or not hasattr(s, "default_value"): continue
            v = s.default_value
            ent.append([_r(x) for x in v] if hasattr(v, "__len__") and not isinstance(v, str) else _r(v) if isinstance(v, float) else getattr(v, "name", v))
        out.append((n.name, n.bl_idname, ent, getattr(getattr(n, "image", None), "name", None), getattr(getattr(n, "node_tree", None), "name", None)))
    out.append(sorted((l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier) for l in nt.links))
    return out


def huella(sc=None):
    sc = sc or bpy.context.scene; H = {}
    for o in _vivos(bpy.data.objects): H["OB:" + o.name] = _objeto(o)
    for a in _vivos(bpy.data.actions): H["AC:" + a.name] = _accion(a)
    for m in _vivos(bpy.data.meshes):
        H["ME:" + m.name] = _md5(len(m.vertices), len(m.edges), len(m.polygons), _arr(m.vertices, "co", 3), [x.name if x else "" for x in m.materials])
    for k in _vivos(bpy.data.shape_keys):
        an = _animadas(k)
        H["SK:" + k.name] = _md5(getattr(k.user, "name", ""), [(b.name, b.relative_key.name, b.mute, _r(b.slider_min), _r(b.slider_max),
                                 None if 'key_blocks["%s"].value' % b.name in an else _r(b.value), _arr(b.data, "co", 3)) for b in k.key_blocks])
    for m in _vivos(bpy.data.materials):
        an = _animadas(m.node_tree) if m.node_tree else set()
        H["MA:" + m.name] = _md5(_rna(m, _animadas(m)), _arbol(m.node_tree, an) if m.node_tree else None)
    for g in _vivos(bpy.data.node_groups): H["NG:" + g.name] = _md5(_arbol(g, _animadas(g)))
    for c in _vivos(bpy.data.cameras): H["CA:" + c.name] = _md5(_rna(c, _animadas(c)))
    for l in _vivos(bpy.data.lights): H["LA:" + l.name] = _md5(_rna(l, _animadas(l)))
    for i in _vivos(bpy.data.images): H["IM:" + i.name] = _md5(_ruta(i.filepath), i.source)
    for s in _vivos(bpy.data.sounds): H["SO:" + s.name] = _md5(_ruta(s.filepath))
    for c in _vivos(bpy.data.collections): H["CO:" + c.name] = _md5(sorted(o.name for o in c.objects), sorted(x.name for x in c.children), c.hide_viewport, c.hide_render)
    an = _animadas(sc)
    H["SC:escena"] = _md5(sc.name, sc.frame_start, sc.frame_end, sc.render.fps, sc.render.resolution_x, sc.render.resolution_y,
                          sc.camera.name if sc.camera else "", sc.world.name if sc.world else "", _props(sc))
    ed = sc.sequence_editor
    if ed:
        for s in ed.strips_all:
            pre = 'sequence_editor.strips_all["%s"].' % s.name
            H["SQ:" + s.name] = _md5(s.type, s.channel, s.frame_start, s.frame_offset_start, s.frame_offset_end, s.mute,
                                     _ruta(getattr(getattr(s, "sound", None), "filepath", None)), _ruta(getattr(s, "filepath", None)),
                                     None if pre + "volume" in an else _r(getattr(s, "volume", 0)), _props(s))

    def capas(lc, out):
        out.append((lc.name, lc.exclude, lc.hide_viewport))
        for c in lc.children: capas(c, out)
        return out
    H["VL:capas"] = _md5([capas(vl.layer_collection, []) for vl in sc.view_layers])
    return H


def total(H):
    return _md5(sorted(H.items()))


def diferencias(a, b, n=12):
    """claves que cambiaron entre dos huellas (para decir QUE se toco a mano)"""
    a = a or {}; b = b or {}
    d = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    return d[:n], len(d)
