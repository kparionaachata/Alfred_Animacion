# -*- coding: utf-8 -*-
"""Base estatica de alfred_cueva_3.blend: el estado del frame FRAME (final: Alfred tumbado, la arana muerta boca arriba, Jerry mirando)
queda fijo como frame 1. Se borran las animaciones (acciones y pistas NLA) de todo lo animado salvo la camara del usuario y su foco, y las
tiras de audio de los personajes (VozSync*, VozJerry*, Voz*, SND_*). Mismo metodo que crear_base_parte_8.py: se leen los valores evaluados de
cada canal animado en FRAME, se borra la animacion y se escriben como valores fijos.
Se ejecuta en Blender en segundo plano sobre el archivo del disco y guarda una copia nueva (no toca el original):
  blender -b alfred_cueva_3.blend --python crear_base_cueva_3.py
"""
import bpy, os

FRAME = 730
SALIDA = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_cueva_3_base.blend"
NO_TOCAR = {"Camera.001", "Foco_Conversacion"}
PREFIJOS_AUDIO = ("VozSync", "VozJerry", "Voz", "SND_")


def _fcurves(ad):
    acts = ([ad.action] if ad.action else []) + [s.action for t in ad.nla_tracks for s in t.strips if s.action]
    out = []
    for a in acts:
        for lay in a.layers:
            for st in lay.strips:
                for cb in st.channelbags: out += [(fc.data_path, fc.array_index) for fc in cb.fcurves]
    return out


def crear():
    sc = bpy.context.scene; sc.frame_set(FRAME)
    ids = [o for o in bpy.data.objects] + [k for k in bpy.data.shape_keys] + list(bpy.data.materials) + list(bpy.data.lights) + list(bpy.data.cameras) + list(bpy.data.worlds)
    capt = {}
    for idb in ids:
        if idb.name in NO_TOCAR or getattr(idb, "user", None) and idb.user.name in NO_TOCAR: continue
        ad = getattr(idb, "animation_data", None)
        if not ad or not (ad.action or len(ad.nla_tracks)): continue
        vals = []
        for dp, i in set(_fcurves(ad)):
            try:
                prop = idb.path_resolve(dp)
                v = prop[i] if hasattr(prop, "__len__") and not isinstance(prop, str) else prop
                vals.append((dp, i, v))
            except Exception:
                pass
        capt[idb] = vals
    n_canales = 0
    for idb, vals in capt.items():
        idb.animation_data_clear()
        for dp, i, v in vals:
            try:
                if "." in dp and not dp.startswith("["):
                    base, attr = dp.rsplit(".", 1); obj = idb.path_resolve(base)
                else:
                    obj, attr = idb, dp
                cur = getattr(obj, attr)
                if hasattr(cur, "__len__") and not isinstance(cur, str): cur[i] = v
                else: setattr(obj, attr, v)
                n_canales += 1
            except Exception:
                pass
    quitadas = 0
    ed = sc.sequence_editor
    if ed:
        for s in list(ed.strips_all):
            if s.name.startswith(PREFIJOS_AUDIO):
                ed.strips.remove(s); quitadas += 1
    for k in [k for k in sc.keys() if k.startswith(("_jerry", "alfred_guion"))]: del sc[k]
    sc.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=SALIDA, copy=True)
    return {"ids": len(capt), "canales": n_canales, "audios_quitados": quitadas, "restantes": [s.name for s in ed.strips_all] if ed else [], "salida": SALIDA}


if __name__ == "__main__":
    print(crear())
