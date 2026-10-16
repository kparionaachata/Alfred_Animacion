# -*- coding: utf-8 -*-
"""base_ranas_3: cerdo_ring le responde a Jerry.
Cuando Jerry le pregunta (f130), el cerdo deja de agitar la pata: vuelve a apoyar las DOS patas delanteras en la
valla (la derecha copia en espejo la izquierda de la pose del usuario), gira la cabeza hacia Jerry y le responde
moviendo la cabeza (asiente), el hocico (`Mouth:Open`, `Pig:Snort`) y los ojos (parpadeo `Blink` + ojos hacia Jerry).
Despues vuelve a mirar la pelea y retoma su animacion de alentar (cerdos_animan.py).
Se mezcla SOBRE la accion actual del cerdo; las claves originales del tramo se guardan en
`cerdo_responde_original.json` y se restauran antes de volver a aplicar (repetible).
Uso (exec en Blender): aplicar()
"""
import bpy, json, math, os
from mathutils import Vector, Euler

DIR = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/"
ORIG = DIR + "cerdo_responde_original.json"
ARM, CABEZA = "pig.arma_cerdo_1", "pig.Head_cerdo_1"
D = math.radians

W = (140, 152, 262, 280)          # deja de alentar / vuelve a alentar
GIRO = (150, 162, 250, 262)       # gira la cabeza a Jerry / vuelve a la pelea
HABLA = [(188, 212), (218, 248)]  # responde (dos frases)
YAW = -95.0                       # Y local de la cabeza: - = hacia su derecha (Jerry)
BLINKS = [157, 197, 236]
SNORT = [200, 231]
REF_HEAD = (65.88, 0.8, -0.37); REF_BODY = (-25.0, 0.0, 0.0)
FR_LOC, FR_ROT = (0.1804, -0.2447, -0.1606), (15.92, 16.42, -2.03)      # espejo de Leg:FL (pose del usuario)
TOCADOS = ["Leg:FR_cerdo_1", "Leg:FR:Bend_cerdo_1", "Head_cerdo_1", "Body:Bend_cerdo_1"]


def ss(x):
    return 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))


def ramp(f, a, b):
    return ss((f - a) / max(1e-6, b - a))


def ventana(f, t):
    return ramp(f, t[0], t[1]) * (1 - ramp(f, t[2], t[3]))


def habla(f):
    """nivel de boca: silabas de ~7 f dentro de cada frase"""
    for a, b in HABLA:
        if a <= f <= b:
            env = ramp(f, a, a + 3) * (1 - ramp(f, b - 3, b))
            return env * (0.35 + 0.65 * max(0.0, math.sin(2 * math.pi * (f - a) / 7.0)) ** 1.3)
    return 0.0


def fcs(idb):
    return [fc for l in idb.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


def aplicar():
    arm = bpy.data.objects[ARM]; act = arm.animation_data.action
    fr = range(W[0] - 2, W[3] + 3)
    curvas = {(fc.data_path, fc.array_index): fc for fc in fcs(arm)}
    # ---- restaurar el tramo original (o guardarlo la primera vez)
    if os.path.exists(ORIG):
        orig = json.load(open(ORIG, encoding="utf-8"))
        for clave, pts in orig.items():
            dp, i = clave.rsplit("|", 1); fc = curvas.get((dp, int(i)))
            if fc is None: continue
            for f, v in pts: fc.keyframe_points.insert(f, v, options={'FAST'})
            fc.update()
    else:
        orig = {}
        for (dp, i), fc in curvas.items():
            if any('"%s"' % b in dp for b in TOCADOS):
                orig["%s|%d" % (dp, i)] = [(f, fc.evaluate(f)) for f in fr]
        json.dump(orig, open(ORIG, "w", encoding="utf-8"))
    base = {k: dict(v) for k, v in orig.items()}

    def val(b, ch, i, f):
        return base.get('pose.bones["%s"].%s|%d' % (b, ch, i), {}).get(f, 0.0)

    def poner(b, ch, valores):
        for i in range(3):
            fc = act.fcurve_ensure_for_datablock(arm, 'pose.bones["%s"].%s' % (b, ch), index=i)
            for f, v in valores:
                fc.keyframe_points.insert(f, v[i], options={'FAST'}).interpolation = 'LINEAR'
            fc.update()

    # ---- huesos: patas a la valla, cabeza a Jerry, asiente al hablar
    for b, ch, objetivo in (("Leg:FR_cerdo_1", "location", lambda f: FR_LOC), ("Leg:FR_cerdo_1", "rotation_euler", lambda f: tuple(D(x) for x in FR_ROT)),
                            ("Leg:FR:Bend_cerdo_1", "location", lambda f: (0, 0, 0)), ("Leg:FR:Bend_cerdo_1", "rotation_euler", lambda f: (0, 0, 0)),
                            ("Body:Bend_cerdo_1", "rotation_euler", lambda f: tuple(D(x) for x in REF_BODY)),
                            ("Head_cerdo_1", "rotation_euler", lambda f: (D(REF_HEAD[0] + 6 * habla(f) * math.sin(2 * math.pi * f / 9.0) - 4 * ventana(f, GIRO)),
                                                                         D(REF_HEAD[1] + YAW * ventana(f, GIRO)),
                                                                         D(REF_HEAD[2] + 4 * habla(f))))):
        out = []
        for f in fr:
            w = ventana(f, W) * (0.8 if b == "Body:Bend_cerdo_1" else 1.0)
            o = [val(b, ch, i, f) for i in range(3)]; t = objetivo(f)
            out.append((f, tuple(o[i] + (t[i] - o[i]) * w for i in range(3))))
        poner(b, ch, out)
    # ---- ojos hacia Jerry (desplazamiento a la derecha del cerdo, en el espacio de cada hueso)
    hx = arm.data.bones["Head_cerdo_1"].matrix_local.to_3x3() @ Vector((1, 0, 0))
    lado = Vector((1 if hx.x >= 0 else -1, 0, 0)) * 0.012
    for b in ("Eye-L_cerdo_1", "Eye-R_cerdo_1"):
        loc_b = arm.data.bones[b].matrix_local.to_3x3().inverted() @ lado
        poner(b, "location", [(W[0] - 2, (0, 0, 0))] + [(f, tuple(loc_b * ventana(f, GIRO))) for f in range(GIRO[0], GIRO[3] + 1)] + [(W[3] + 2, (0, 0, 0))])
    # ---- cara: boca, hocico y parpadeo (shape keys de la cabeza)
    key = bpy.data.objects[CABEZA].data.shape_keys
    SEQ = [0, .25, .5, .75, 1, 1, .75, .5, .25, 0]
    can = {'key_blocks["Mouth:Open"].value': [], 'key_blocks["Pig:Snort"].value': [], 'key_blocks["Blink"].value': []}
    for f in [1] + list(fr) + [bpy.context.scene.frame_end]:
        bl = max([SEQ[f - b0] for b0 in BLINKS if b0 <= f < b0 + 10] + [0.0])
        sn = max([math.sin(math.pi * (f - s0) / 6.0) for s0 in SNORT if s0 <= f <= s0 + 6] + [0.0])
        can['key_blocks["Mouth:Open"].value'].append((f, (habla(f),)))
        can['key_blocks["Pig:Snort"].value'].append((f, (sn,)))
        can['key_blocks["Blink"].value'].append((f, (bl,)))
    key.animation_data_create()
    viejo = bpy.data.actions.get("cerdo_ring_responde_cara")
    if viejo: bpy.data.actions.remove(viejo)
    a = bpy.data.actions.new("cerdo_ring_responde_cara"); key.animation_data.action = a
    for path, cl in can.items():
        fc = a.fcurve_ensure_for_datablock(key, path, index=0); fc.keyframe_points.add(len(cl))
        fc.keyframe_points.foreach_set("co", [x for f, v in cl for x in (f, v[0])]); fc.update()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    return {"tramo": [W[0], W[3]], "habla": HABLA, "curvas_guardadas": len(orig)}
