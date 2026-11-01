# -*- coding: utf-8 -*-
"""Parte 6, f126-290: mejora la cara y la cabeza de Jerry mientras se ESTIRA al despertarse (estirada f133-190, patadas dormido f193-245, abre los ojos f250-258 y se levanta f258-283). Es una capa ADITIVA: se suma a lo que ya animan (voz de `voz_jerry_despierta.py`, cabeza, ojos) sin tocarlo.
 - Esfuerzo del estirón (f133-190, pico f153-187): cejas fruncidas (pose de cansancio de la app x0.55), ojos cerrados con fuerza (escala de las mallas de los ojos en Z -10 %, X +5 %, bajan 6 mm, forma `Cerrado` 0.7), cabeza levanta (`scull` -5 grados, `scull_1` -11) y se inclina con una oscilacion lenta (Z +-4), orejas hacia atras (+-8).
 - BOSTEZO en el hueco entre las dos frases (f163-200, pico f175-186): `jaw_bot` X -34 grados, `jaw_top` -5 y hocico +4 %, cabeza atras (`scull_1` -6).
 - Patadas dormido (f193-245): parpadeo/temblor de los parpados (escala Z de los ojos), cejas +0.25, sacudida de la cabeza (+-2.5) y de las orejas (+-6) al ritmo de las patas.
 - Despertar (f248-270): las cejas suben un instante (pose inversa x0.35), parpados pesados (`Cansado` 0.35 que baja hasta f283), mallas de los ojos algo mas abiertas; al abrir (f258+) las pupilas buscan en direcciones distintas (+-0.010 en X, +-0.003 en Z, decayendo hasta f284) y la cabeza mira alrededor (`scull_1` Y +-5 grados).
Repetible: los deltas aplicados se guardan en `jerry_estira_cara_delta.json` y se restan antes de volver a aplicarlos. Se ejecuta DENTRO de Blender con exec (despues de `voz_jerry_despierta.py`). Nunca `raise SystemExit`."""
import bpy, json, math, os, traceback
from mathutils import Vector

try:
    sc = bpy.context.scene
    ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
    F0, F1 = 126, 290; DJ = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\jerry\refinar\docs\jerry_estira_cara_delta.json"
    JA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "scull_1" in o.pose.bones)
    PREV = json.load(open(DJ, encoding="utf-8")) if os.path.exists(DJ) else {}; NEW = {}
    for n in ("jaw_bot", "jaw_top", "scull", "scull_1", "ear.L", "ear.R", "sejas_1_jerry", "sejas_2_jerry"): JA.pose.bones[n].rotation_mode = 'XYZ'
    BP = {"sejas_1_jerry": ((0.002696, -0.051839, -0.649442), (0.008732, -0.027737, 0.001994), (0.0, 0.0, 0.0), (0.006569, 0.000489, -0.000191)), "sejas_2_jerry": ((-0.04654, 0.063158, 0.5541), (0.020013, -0.031002, 0.003717), (0.0, 0.0, 0.0), (0.013395, -0.000836, 0.003522))}   # (rot pose, loc pose, rot base, loc base) del script de la app
    # ---------- envolventes ----------
    S = lambda f: ss((f - 133) / 18.0) * (1 - ss((f - 185) / 12.0))
    Yw = lambda f: ss((f - 163) / 12.0) * (1 - ss((f - 186) / 10.0))
    P = lambda f: ss((f - 190) / 6.0) * (1 - ss((f - 243) / 6.0))
    Wk = lambda f: ss((f - 248) / 5.0) * (1 - ss((f - 270) / 10.0))
    Lk = lambda f: ss((f - 258) / 4.0) * (1 - ss((f - 262) / 22.0))
    D2R = math.pi / 180
    def deltas(f):
        d = {}; s = S(f); y = Yw(f); p = P(f); w = Wk(f); l = Lk(f); sp = math.sin(f * 0.62); kick = p * sp
        d["bone:jaw_bot:rot"] = (-34 * D2R * y + 0.8 * D2R * s * math.sin(f * 0.9), 0, 0)
        d["bone:jaw_top:rot"] = (-5 * D2R * y, 0, 0); d["bone:jaw_top:scale"] = (0.04 * y, -0.015 * y, 0.02 * y)
        d["bone:scull:rot"] = (-5 * D2R * s - 2.5 * D2R * kick, 0, 0)
        d["bone:scull_1:rot"] = (-11 * D2R * s - 6 * D2R * y - 1.5 * D2R * kick, 5 * D2R * math.sin((f - 255) * 0.25) * l, 4 * D2R * math.sin(f * 0.13) * s)
        er = 8 * D2R * s + 6 * D2R * p * math.sin(f * 0.8)
        d["bone:ear.L:rot"] = (0, er, 0); d["bone:ear.R:rot"] = (0, -er, 0)
        for nm in ("sejas_1_jerry", "sejas_2_jerry"):
            rp, lp, rb, lb = BP[nm]; mix = 0.55 * s + 0.25 * p - 0.35 * w
            d["bone:%s:rot" % nm] = tuple((rp[a] - rb[a]) * mix for a in range(3)); d["bone:%s:loc" % nm] = tuple((lp[a] - lb[a]) * mix for a in range(3))
        for ei, nm in enumerate(("ojo_izquierdo_jerry", "ojo_derecho_jerry")):
            tw = 0.04 * p * abs(math.sin(f * 0.9 + ei * 0.4))
            d["obj:%s:scale" % nm] = (0.05 * s, 0.0, -0.10 * s - tw + 0.06 * w); d["obj:%s:loc" % nm] = (0, 0, -0.006 * s)
            d["sk:%s:Cerrado" % nm] = (0.7 * s,); d["sk:%s:Cansado" % nm] = (0.35 * ss((f - 248) / 6.0) * (1 - ss((f - 258) / 25.0)),)
        for pi_, nm in enumerate(("pupila_izquierda_jerry", "pupila_derecha_jerry")):
            side = 1.0 if pi_ == 0 else -1.0
            d["obj:%s:loc" % nm] = (side * 0.010 * math.sin((f - 258) * 0.28) * l, 0, 0.003 * math.sin((f - 258) * 0.45) * l)
        return d
    def leer(chan):
        t, nm, tipo = chan.split(":")
        if t == "bone": pb = JA.pose.bones[nm]; return list({"rot": pb.rotation_euler, "loc": pb.location, "scale": pb.scale}[tipo])
        if t == "obj": o = bpy.data.objects[nm]; return list({"scale": o.scale, "loc": o.location}[tipo])
        return [bpy.data.objects[nm].data.shape_keys.key_blocks[tipo].value]
    def escribir(chan, v, f):
        t, nm, tipo = chan.split(":")
        if t == "bone":
            pb = JA.pose.bones[nm]; prop = {"rot": "rotation_euler", "loc": "location", "scale": "scale"}[tipo]; setattr(pb, prop, tuple(v)); pb.keyframe_insert(prop, frame=f, group=nm)
        elif t == "obj":
            o = bpy.data.objects[nm]; prop = {"scale": "scale", "loc": "location"}[tipo]; setattr(o, prop, tuple(v)); o.keyframe_insert(prop, frame=f)
        else:
            kb = bpy.data.objects[nm].data.shape_keys.key_blocks[tipo]; kb.value = v[0]; kb.keyframe_insert("value", frame=f)
    chans = list(deltas(150).keys())
    # ---------- 1) base = valor actual - delta anterior (por frame) ----------
    BASE = {c: {} for c in chans}
    for f in range(F0, F1 + 1):
        sc.frame_set(f)
        for c in chans:
            cur = leer(c); pv = PREV.get(c, {}).get(str(f)); BASE[c][f] = [cur[i] - (pv[i] if pv else 0.0) for i in range(len(cur))]
    # ---------- 2) escribir base + delta nuevo ----------
    for c in chans: NEW[c] = {}
    for f in range(F0, F1 + 1):
        dd = deltas(f)
        for c in chans:
            v = [BASE[c][f][i] + dd[c][i] for i in range(len(dd[c]))]
            if c.startswith("obj:ojo") and c.endswith(":scale"): pass
            escribir(c, v, f); NEW[c][str(f)] = list(dd[c])
    json.dump(NEW, open(DJ, "w", encoding="utf-8"))
    res = {}
    for f in (126, 150, 170, 180, 195, 220, 252, 262, 275, 290):
        sc.frame_set(f); o = bpy.data.objects["ojo_izquierdo_jerry"]; res[f] = {"jaw_bot": round(math.degrees(JA.pose.bones["jaw_bot"].rotation_euler[0]), 1), "scull_1X": round(math.degrees(JA.pose.bones["scull_1"].rotation_euler[0]), 1), "ojoZscale": round(o.scale.z, 3), "Cerrado": round(o.data.shape_keys.key_blocks["Cerrado"].value, 2), "ceja1Z": round(math.degrees(JA.pose.bones["sejas_1_jerry"].rotation_euler[2]), 1)}
    sc.frame_set(120); print(res); print("LISTO")
except Exception:
    traceback.print_exc()
