# -*- coding: utf-8 -*-
"""Crea `capitulos/capitulo_4/base_parte_5.blend`: el estado del frame 1236 de la parte 4 (Alfred acaba de colocar la antorcha) fijado como FRAME 1, sin ninguna animacion.
Se ejecuta en un Blender APARTE (no toca la sesion abierta ni `base_parte_4.blend` en disco):
    blender --background base_parte_4.blend --python crear_base_parte_5.py
1. Reproduce la animacion de colocar la antorcha (`docs/acciones/colocar_objeto.py` + `colocar_objeto_exterior/accion.json`), porque la sesion con la antorcha estaba sin guardar.
2. Evalua el frame 1236 y recoge el valor de TODOS los canales animados (acciones y NLA de objetos, datos, shape keys, materiales, luces, camaras, mundo).
3. Quita toda la animacion (acciones y pistas NLA, voces incluidas) y escribe esos valores como estaticos. Quita tambien las tiras de sonido del VSE (son de las partes anteriores).
4. frame_current = 1 y guarda como base_parte_5.blend (no sobrescribe si ya existe).
Metodo de `base_parte_2.blend` (frame 860 -> frame 1)."""
import json
import math
import os
import re
import sys

import bpy

RAIZ = r"C:\Users\user\Desktop\Alfred_Animacion"; REF = os.path.join(RAIZ, "generador de animaciones", "alfred", "refinar"); DESTINO = os.path.join(RAIZ, "capitulos", "capitulo_4", "base_parte_5.blend"); F = 1236
if os.path.exists(DESTINO): raise SystemExit("ya existe %s: no se sobrescribe" % DESTINO)
sc = bpy.context.scene
# 1) la antorcha
ns = {"__name__": "accion", "ACCION_JSON": os.path.join(REF, "docs", "acciones", "colocar_objeto_exterior", "accion.json")}
exec(open(os.path.join(REF, "docs", "acciones", "colocar_objeto.py"), encoding="utf-8").read(), ns)
sc.frame_set(F); bpy.context.view_layer.update()

# 2) todos los IDs con animacion
def ids_animados():
    out = []
    for coll in ("objects", "meshes", "shape_keys", "materials", "lights", "cameras", "worlds", "scenes", "armatures", "curves", "images", "node_groups", "textures", "grease_pencils", "speakers", "collections"):
        for idb in getattr(bpy.data, coll, []): out.append(idb)
    return out


def acciones_de(ad):
    acts = []
    if ad is None: return acts
    if ad.action: acts.append(ad.action)
    for t in ad.nla_tracks:
        for s in t.strips:
            if s.action and s.action not in acts: acts.append(s.action)
    return acts


def fcurves_de(act):
    out = []
    if hasattr(act, "layers"):
        for l in act.layers:
            for st in l.strips:
                for cb in getattr(st, "channelbags", []): out += list(cb.fcurves)
    else: out += list(act.fcurves)
    return out


def con_animacion(idb):
    cand = [(idb, getattr(idb, "animation_data", None))]
    nt = getattr(idb, "node_tree", None)
    if nt is not None: cand.append((nt, getattr(nt, "animation_data", None)))
    k = getattr(idb, "shape_keys", None)
    if k is not None: cand.append((k, getattr(k, "animation_data", None)))
    return [(o, ad) for o, ad in cand if ad is not None]


VALORES = []; n_ids = 0; sin_resolver = []
for idb in ids_animados():
    for dueno, ad in con_animacion(idb):
        acts = acciones_de(ad)
        if not acts: continue
        n_ids += 1; vistos = set()
        for a in acts:
            for fc in fcurves_de(a):
                clave = (fc.data_path, fc.array_index)
                if clave in vistos: continue
                vistos.add(clave)
                try:
                    v = dueno.path_resolve(fc.data_path)
                    v = v[fc.array_index] if hasattr(v, "__len__") and not isinstance(v, str) else v
                    VALORES.append((dueno, fc.data_path, fc.array_index, v))
                except Exception as e: sin_resolver.append((getattr(dueno, "name", "?"), fc.data_path, str(e)[:60]))
print("IDs con animacion: %d | canales: %d | sin resolver: %d" % (n_ids, len(VALORES), len(sin_resolver)))

# 3) quitar la animacion (acciones + NLA) y escribir los valores
acciones_quitar = set()
for idb in ids_animados():
    for dueno, ad in con_animacion(idb):
        for a in acciones_de(ad): acciones_quitar.add(a)
        dueno.animation_data_clear()
escritos = 0; fallos = []
for dueno, dp, idx, v in VALORES:
    try:
        m = re.match(r"^(.*)\.([A-Za-z_][A-Za-z0-9_]*)$", dp); m2 = re.match(r'^(.*)\["([^"]+)"\]$', dp)
        if m2 and (not m or len(m2.group(1)) > len(m.group(1))):
            owner = dueno.path_resolve(m2.group(1)) if m2.group(1) else dueno; cur = owner[m2.group(2)]
            if hasattr(cur, "__len__") and not isinstance(cur, str):
                cur = list(cur); cur[idx] = v; owner[m2.group(2)] = cur
            else: owner[m2.group(2)] = v
        else:
            owner = dueno.path_resolve(m.group(1)) if m else dueno; prop = m.group(2) if m else dp
            if idx >= 0 and hasattr(getattr(owner, prop), "__len__") and not isinstance(getattr(owner, prop), str): getattr(owner, prop)[idx] = v
            else: setattr(owner, prop, v)
        escritos += 1
    except Exception as e: fallos.append((getattr(dueno, "name", "?"), dp, idx, str(e)[:70]))
for a in list(bpy.data.actions):
    if a in acciones_quitar or a.users == 0: bpy.data.actions.remove(a)
print("valores escritos: %d | fallos: %d | acciones restantes: %d" % (escritos, len(fallos), len(bpy.data.actions)))
for f_ in fallos[:8]: print("  FALLO", f_)

# 4) sonidos del VSE (de las partes anteriores) y recuerdos del guion en la escena
ed = sc.sequence_editor; n_snd = 0
if ed:
    for s in list(ed.strips_all):
        if s.type == 'SOUND': ed.strips.remove(s); n_snd += 1
borrados = [k for k in list(sc.keys()) if k.endswith("guion_v2")]
for k in borrados: del sc[k]
print("tiras de sonido quitadas:", n_snd, "| recuerdos de guion quitados:", borrados)
sc.frame_set(1); sc.frame_current = 1; bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=DESTINO)
print("GUARDADO", DESTINO)
