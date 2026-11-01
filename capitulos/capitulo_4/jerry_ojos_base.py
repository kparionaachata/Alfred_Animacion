# -*- coding: utf-8 -*-
"""Jerry: posicion de las mallas de los ojos y pupilas. Las capas de la cara (pistas NLA ADD de `jerry_responde_pensando.cara`) dejaban en 0 la ubicacion de
los ojos y pupilas (sin una pista base el NLA pone 0 a los canales que anima): ojos a z = 0 (en el suelo) y pupilas con x = 0. Se crea una pista base
REPLACE + HOLD con la ubicacion/escala de reposo del modelo (estructura_lista/jerry.blend) DEBAJO de las capas, que se rehacen encima en el mismo orden.
Uso en Blender: exec(open(ruta, encoding="utf8").read()); reparar()       (repetible)
"""
import bpy

REPOSO = {                                   # ubicacion local de reposo en estructura_lista/jerry.blend
    "ojo_derecho_jerry": (0.1058, 0.7048, 0.7001),
    "ojo_izquierdo_jerry": (-0.1057, 0.7052, 0.6998),
    "pupila_derecha_jerry": (-0.0935, 0.7035, 0.6889),
    "pupila_izquierda_jerry": (0.094, 0.7037, 0.688),
}
BASE = "JerryOjosBase_"


def reparar():
    res = {}
    for nombre, loc in REPOSO.items():
        ob = bpy.data.objects[nombre]
        ad = ob.animation_data or ob.animation_data_create()
        capas = [(t.name, [(s.name, s.frame_start, s.action, s.blend_type, s.extrapolation) for s in t.strips]) for t in ad.nla_tracks if not t.name.startswith(BASE)]
        for t in list(ad.nla_tracks):
            ad.nla_tracks.remove(t)
        vieja = bpy.data.actions.get(BASE + nombre)
        if vieja:
            bpy.data.actions.remove(vieja)
        a = bpy.data.actions.new(BASE + nombre)
        sl = a.slots.new(ob.id_type, ob.name)
        cb = a.layers.new("L").strips.new(type='KEYFRAME').channelbags.new(sl)
        for i in range(3):
            cb.fcurves.new("location", index=i).keyframe_points.insert(1, loc[i])
            cb.fcurves.new("scale", index=i).keyframe_points.insert(1, 1.0)
        tr = ad.nla_tracks.new()
        tr.name = BASE + nombre
        st = tr.strips.new(BASE + nombre, 1, a)
        st.blend_type, st.extrapolation = 'REPLACE', 'HOLD'
        try:
            st.action_slot = sl
        except Exception:
            pass
        for tn, strips in capas:                       # las capas de la voz, encima y en el mismo orden
            t2 = ad.nla_tracks.new()
            t2.name = tn
            for sn, ini, act, bt, ex in strips:
                s2 = t2.strips.new(sn, int(ini), act)
                s2.blend_type, s2.extrapolation = bt, ex
                try:
                    s2.action_slot = act.slots[0]
                except Exception:
                    pass
        ob.location = loc
        ob.scale = (1.0, 1.0, 1.0)
        res[nombre] = len(capas)
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    return res
