# -*- coding: utf-8 -*-
"""alfred_cueva_4.blend: Alfred, ya sentado contra la estalagmita, se queda 80 frames con los ojos cerrados (shape key `Closed` de las mallas de
sus ojos) antes de levantarse; mientras, Jerry lo mira y se lleva la pata delantera izquierda a la cabeza como pensando
(postura del usuario jerry_pata_cabeza_pose.json; en el rig, la pata izquierda de Jerry son los huesos front_*.L).
Las dos cosas son pistas NLA REPLACE con influencia animada, encima de lo que ya hay.
Uso: exec(open(ruta, encoding="utf8").read()); construir(f_sentado, f_levanta)
"""
import bpy, json

BASE = r"C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/"
POSE_JERRY = BASE + "jerry_pata_cabeza_pose.json"
OJOS = ("ojo_izquierdo_alfred", "ojo_derecho_alfred")
F_CIERRA, F_ABRE = 6, 5           # frames que tardan los ojos en cerrarse / abrirse
F_SUBE, F_BAJA = 14, 12           # frames de la pata subiendo a la cabeza / bajando
SIN_UY = 11                       # frames del principio del audio de Jerry que se quitan ("Uy,")
CARA = ("jaw_top", "jaw_bot", "scull", "scull_1", "sejas_1_jerry", "sejas_2_jerry")
VOZ = (BASE + "voces_piensa_rapido/animacion_jerry_me_pase.py", r"C:/Users/user/Desktop/Alfred_Animacion/audios/jerry/jerry_creo_que_me_pase.wav", "VozJerry_me_pase")


def _pista(idb, nombre, canales, f0, f1, rampa):
    """accion constante con `canales` {(data_path, index): valor} en una pista REPLACE arriba de todo, con influencia 0 -> 1 -> 0"""
    ad = idb.animation_data or idb.animation_data_create()
    for t in list(ad.nla_tracks):
        if t.name == nombre: ad.nla_tracks.remove(t)
    vieja = bpy.data.actions.get(nombre)
    if vieja: bpy.data.actions.remove(vieja)
    a = bpy.data.actions.new(nombre); sl = a.slots.new(idb.id_type, idb.name)
    cb = a.layers.new("L").strips.new(type='KEYFRAME').channelbags.new(sl)
    for (dp, i), v in canales.items():
        fc = cb.fcurves.new(dp, index=i); fc.keyframe_points.insert(f0, v); fc.keyframe_points.insert(f1, v)
    tr = ad.nla_tracks.new(); tr.name = nombre
    st = tr.strips.new(nombre, f0, a); st.blend_type = 'REPLACE'; st.extrapolation = 'NOTHING'
    try: st.action_slot = sl
    except Exception: pass
    st.use_animated_influence = True; fi = st.fcurves.find("influence")
    for f, v in ((f0, 0.0), (f0 + rampa[0], 1.0), (f1 - rampa[1], 1.0), (f1, 0.0)):
        fi.keyframe_points.insert(f, v).interpolation = 'BEZIER'
    return tr


def construir(f_sentado, f_levanta):
    O = bpy.data.objects
    # Alfred: ojos cerrados mientras esta aturdido; los abre al empezar a levantarse
    for n in OJOS:
        _pista(O[n].data.shape_keys, "Alfred_aturdido_ojos_" + n, {('key_blocks["Closed"].value', 0): 1.0}, f_sentado - F_CIERRA, f_levanta + F_ABRE, (F_CIERRA, F_ABRE))
    # Jerry: pata izquierda a la cabeza, pensando
    d = json.load(open(POSE_JERRY, encoding="utf8"))["poses"][0]["bones"]; rig = O["Dog_001_rig"]; canales = {}
    for n, b in d.items():
        if n not in rig.pose.bones or n.startswith("no_bone") or n in CARA: continue   # la cara la mueve la voz
        rig.pose.bones[n].rotation_mode = 'XYZ'
        for i, k in enumerate("xyz"): canales[('pose.bones["%s"].rotation_euler' % n, i)] = b["local_space"]["rotation_euler_rad"][k]
    f0 = f_sentado + 4; f1 = f_levanta - 2
    _pista(rig, "Jerry_pata_cabeza", canales, f0, f1, (F_SUBE, F_BAJA))
    # "Uy, creo que me pase." con la pata ya en la cabeza (ojos, cejas, mandibula, hocico, cabeza: capas aditivas)
    v = {"__name__": "jerry_voz_me_pase"}; exec(open(BASE + "jerry_responde_pensando.py", encoding="utf8").read(), v)
    F0 = f0 + F_SUBE
    v.update(F0=F0, SCRIPT_APP=VOZ[0], AUDIO=VOZ[1], TAG=VOZ[2]); v["quitar"](); v["cara"](v["constantes"]()); v["audio"]()
    # sin el "Uy": se recorta el audio y la boca no lo dice (solo queda "creo que me pase")
    ed = bpy.context.scene.sequence_editor; tira = next(t for t in ed.strips_all if t.name.startswith(VOZ[2]))
    tira.frame_offset_start = SIN_UY
    for fc in [fc for lay in bpy.data.actions[VOZ[2] + "_rig"].layers for st in lay.strips for cb in st.channelbags for fc in cb.fcurves]:
        for kp in fc.keyframe_points:
            if kp.co[0] < F0 + SIN_UY: kp.co[1] = 0.0; kp.handle_left[1] = kp.handle_right[1] = 0.0
        fc.update()
    audio = (tira.frame_final_start, tira.frame_final_end)
    return {"ojos_cerrados": (f_sentado, f_levanta), "jerry_pata": (f0, f1), "voz_jerry": audio}
