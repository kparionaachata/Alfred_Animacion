# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: Jerry, ya sin el pico, gira hacia Alfred, lo mira y le dice "Como que esta aqui?" (enojo).
Reusa la cara de jerry_responde_pensando.py (ojos, pupilas, parpadeo, mandibula, hocico, cejas del script de la app como capas ADITIVAS):
animacion_jerry_como_que_esta_aqui.py (copia de `animacion_jerry (27).py`, 24 frames) + audios/jerry/jerry_como_que_esta_aqui.wav (0.77 s).
  GIRO_INI .. GIRO_INI+GIRO_N   el empty `jerry` pasa de su rotacion final (148 deg) a quedar de frente a Alfred (con un pequeno sobrepaso)
  F0                           empieza a hablar (Jerry espera quieto a que Alfred termine su frase)
Uso en Blender: exec(open(ruta, encoding="utf8").read()); construir()
OJO: la cara se hornea en la accion de Jerry (sumada a sus claves por frame); para repetirlo hay que regenerar antes la animacion de Jerry (jerry_llega_salida.py).
"""
import bpy, math, importlib.util

BASE = r"C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/"
F0 = 680                                    # despues de que Alfred dice "Bueno, hasta aqui bajamos." (627-658)
GIRO_INI, GIRO_N = 662, 14
ALFRED = "Armature"                         # hueso Hips_alfred = eje del cuerpo de Alfred
SCRIPT = BASE + "animacion_jerry_como_que_esta_aqui.py"
AUDIO = r"C:/Users/user/Desktop/Alfred_Animacion/audios/jerry/jerry_como_que_esta_aqui.wav"
TAG = "VozJerry_como_que"


def _modulo():
    spec = importlib.util.spec_from_file_location("jerry_responde_pensando_local", BASE + "jerry_responde_pensando.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.F0, m.SCRIPT_APP, m.AUDIO, m.TAG = F0, SCRIPT, AUDIO, TAG
    return m


def giro():
    sc = bpy.context.scene
    root = bpy.data.objects["jerry"]
    root.rotation_mode = 'XYZ'
    a = bpy.data.objects[ALFRED]
    sc.frame_set(GIRO_INI - 1)
    bpy.context.view_layer.update()
    ap = a.matrix_world @ a.pose.bones["Hips_alfred"].head
    p = root.location.copy()
    z0 = root.rotation_euler.z
    dx, dy = ap.x - p.x, ap.y - p.y
    z1 = math.atan2(-dx, dy)                                    # el empty mira a +Y con rotacion 0: avance = (-sin z, cos z)
    while z1 - z0 > math.pi: z1 -= 2 * math.pi
    while z1 - z0 < -math.pi: z1 += 2 * math.pi
    act = root.animation_data.action
    from bpy_extras import anim_utils
    cb = anim_utils.action_get_channelbag_for_slot(act, root.animation_data.action_slot)
    fc = next(x for x in cb.fcurves if x.data_path == "rotation_euler" and x.array_index == 2)
    for i in range(len(fc.keyframe_points) - 1, -1, -1):
        if fc.keyframe_points[i].co.x >= GIRO_INI:
            fc.keyframe_points.remove(fc.keyframe_points[i])
    curva = ((0, 0.0), (3, 0.35), (8, 1.08), (11, 0.98), (14, 1.0))      # arranque, giro, sobrepaso y asentamiento
    def u(t):
        for (s, vs), (e, ve) in zip(curva, curva[1:]):
            if s <= t <= e:
                k = (t - s) / (e - s)
                k = k * k * (3 - 2 * k)
                return vs + (ve - vs) * k
        return 1.0
    for t in range(0, GIRO_N + 1):
        fc.keyframe_points.insert(GIRO_INI + t, z0 + (z1 - z0) * u(t)).interpolation = 'LINEAR'
    fc.keyframe_points.insert(sc.frame_end, z1).interpolation = 'LINEAR'
    fc.update()
    sc.frame_set(1)
    return round(math.degrees(z0), 1), round(math.degrees(z1), 1)


def hornear_rig(m, tag=None):
    """la accion activa de Jerry lleva claves por frame de todos los huesos (REPLACE) y tapa a la capa aditiva de la cara: los deltas de la capa
    `<TAG>_rig` (mandibula, hocico, cabeza, cejas) se SUMAN a esa accion por frame y la capa se quita."""
    rig = bpy.data.objects[m.RIG]
    ad = rig.animation_data
    tag = tag or TAG
    capa = bpy.data.actions[f"{tag}_rig"]
    from bpy_extras import anim_utils
    cb_capa = anim_utils.action_get_channelbag_for_slot(capa, capa.slots[0])
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    sc = bpy.context.scene
    n = 0
    for fcc in cb_capa.fcurves:
        pts = {int(round(k.co.x)): k.co.y for k in fcc.keyframe_points}
        a, b = min(pts) - 1, max(pts) + 1
        fc = cb.fcurves.find(fcc.data_path, index=fcc.array_index)
        if fc is None:
            fc = cb.fcurves.new(fcc.data_path, index=fcc.array_index)
        if len(fc.keyframe_points):
            base = {f: fc.evaluate(f) for f in range(a, b + 1)}
        else:
            sc.frame_set(F0)
            hueso = fcc.data_path.split('"')[1]
            propiedad = fcc.data_path.split(".")[-1]
            v = getattr(rig.pose.bones[hueso], propiedad)[fcc.array_index]
            base = {f: v for f in range(a, b + 1)}
        for f in range(a, b + 1):
            fc.keyframe_points.insert(f, base[f] + pts.get(f, 0.0), options={'FAST'}).interpolation = 'LINEAR'
        fc.update()
        n += 1
    for t in list(ad.nla_tracks):
        if t.name == f"{tag}_rig":
            ad.nla_tracks.remove(t)
    bpy.data.actions.remove(capa)
    return n


def construir():
    m = _modulo()
    m.quitar()
    c = m.constantes()
    fin = m.cara(c)
    canales = hornear_rig(m)
    sc = bpy.context.scene
    ed = sc.sequence_editor or sc.sequence_editor_create()
    canal = max([s.channel for s in ed.strips_all] + [0]) + 1
    s = ed.strips.new_sound(TAG + "_aqui", AUDIO, min(canal, 128), F0)
    return {"canales_cara": canales, "habla": (F0, F0 + fin - 1), "audio": (s.frame_final_start, s.frame_final_end), "giro": giro()}


def decir(f0, script, audio, tag):
    """otra frase de Jerry (misma cara horneada) desde el frame f0: script de la app (animacion_jerry (N).py) + audio .wav"""
    m = _modulo()
    m.F0, m.SCRIPT_APP, m.AUDIO, m.TAG = f0, script, audio, tag
    m.quitar()
    fin = m.cara(m.constantes())
    canales = hornear_rig(m, tag)
    sc = bpy.context.scene
    ed = sc.sequence_editor or sc.sequence_editor_create()
    canal = max([s.channel for s in ed.strips_all] + [0]) + 1
    st = ed.strips.new_sound(tag + "_voz", audio, min(canal, 128), f0)
    sc.frame_set(1)
    return {"canales_cara": canales, "habla": (f0, f0 + fin - 1), "audio": (st.frame_final_start, st.frame_final_end)}


def segunda_frase():
    """"Oye, algun dia tienes que ser hombre." justo despues de "Como que esta aqui?" (esa termina en F0 + 23)"""
    return decir(F0 + 24, BASE + "animacion_jerry_algun_dia_hombre.py", r"C:/Users/user/Desktop/Alfred_Animacion/audios/jerry/jerry_algun_dia_hombre.wav", "VozJerry_algun_dia")
