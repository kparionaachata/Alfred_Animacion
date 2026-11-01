# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: al levantarse, Alfred empuja su pico POR ACCIDENTE con el pie izquierdo (en vez de alcanzarlo con la mano). Sobre lo hecho por
alfred_explica_y_empuja_pico.py:
 - el brazo izquierdo deja de alcanzar el pico (queda en su valor de antes, constante desde el frame 828) y la inclinacion del torso se reduce a la mitad;
 - el pie izquierdo (LeftUpLeg + Leftknee, cinematica directa) se desliza hacia el pico (F_A) y lo arrastra hacia el borde (F_B); luego vuelve a su sitio;
 - el pico (animar_pico) sigue al pie en vez de a la mano.
Uso en Blender: exec(open(ruta, encoding="utf8").read()); construir()      (NO repetible sin deshacer: se suma al estado actual)
"""
import bpy, math
from mathutils import Matrix, Vector, Euler
from bpy_extras import anim_utils

BASE = r"C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/alfred_explica_y_empuja_pico.py"
PIERNA, RODILLA, CADERA = "LeftUpLeg_alfred", "Leftknee_alfred", "Hips_alfred"
F_A, F_B = (836, 6), (846, 6)           # aproxima el pie al pico, lo arrastra
F_VUELVE = (866, 16)
T_A = Vector((0.52, 83.62, 65.97))      # pie junto al pico, por detras
T_B = Vector((0.50, 83.33, 65.97))      # pie que lo empuja hacia el borde (y 83.338)


def _fk(arm, M_cadera, e_pierna, e_rodilla):
    up, co, pad = arm.pose.bones[PIERNA], arm.pose.bones[RODILLA], arm.pose.bones[CADERA]
    bas = lambda pb, e: Matrix.Translation(pb.location) @ Euler(e, 'XYZ').to_matrix().to_4x4()
    M_up = M_cadera @ (pad.bone.matrix_local.inverted() @ up.bone.matrix_local) @ bas(up, e_pierna)
    M_co = M_up @ (up.bone.matrix_local.inverted() @ co.bone.matrix_local) @ bas(co, e_rodilla)
    return M_up, M_co


def resolver(arm, objetivo_w):
    M_cad = arm.pose.bones[CADERA].matrix.copy()
    obj = arm.matrix_world.inverted() @ objetivo_w
    up, co = arm.pose.bones[PIERNA], arm.pose.bones[RODILLA]
    L = co.bone.length
    e0, c0 = list(up.rotation_euler), list(co.rotation_euler)

    def coste(p):
        M_up, M_co = _fk(arm, M_cad, p[:3], (p[3], c0[1], c0[2]))
        pie = M_co @ Vector((0, L, 0))
        return (pie - obj).length + 0.03 * sum(abs(p[i] - [e0[0], e0[1], e0[2], c0[0]][i]) for i in range(4))
    p = [e0[0], e0[1], e0[2], c0[0]]
    mejor, paso = coste(p), 0.4
    for _ in range(500):
        mejoro = False
        for i in range(4):
            for s in (+1, -1):
                q = list(p)
                q[i] += s * paso
                c = coste(q)
                if c < mejor - 1e-7:
                    p, mejor, mejoro = q, c, True
        if not mejoro:
            paso *= 0.6
            if paso < 1e-3:
                break
    return p, mejor


def S(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def construir():
    sc = bpy.context.scene
    O = bpy.data.objects
    arm = O["Armature"]
    cb = anim_utils.action_get_channelbag_for_slot(arm.animation_data.action, arm.animation_data.action_slot)
    fin = sc.frame_end

    def cur(dp, i, f):
        return cb.fcurves.find(dp, index=i).evaluate(f)

    def reescribir(dp, i, fn, f0):
        fc = cb.fcurves.find(dp, index=i)
        base = {f: fc.evaluate(f) for f in range(f0, fin + 1)}
        for j in range(len(fc.keyframe_points) - 1, -1, -1):
            if fc.keyframe_points[j].co.x >= f0:
                fc.keyframe_points.remove(fc.keyframe_points[j])
        for f in range(f0, fin + 1):
            fc.keyframe_points.insert(f, fn(f, base), options={'FAST'}).interpolation = 'LINEAR'
        fc.update()
    # 1) el brazo izquierdo ya no alcanza el pico: vuelve a su valor constante de antes
    for h, i in (("LeftUpArm_alfred", 0), ("LeftUpArm_alfred", 1), ("LeftUpArm_alfred", 2), ("Leftelbow_alfred", 2)):
        dp = 'pose.bones["%s"].rotation_euler' % h
        v = cur(dp, i, 828)
        reescribir(dp, i, lambda f, b, v=v: v, 829)
    # 2) menos inclinacion del torso (la mitad de la que se sumo): se resta el mismo perfil con peso 0.5
    ns = {}
    exec(open(BASE, encoding="utf8").read(), ns)
    w, ADEL1, ADEL2, INC = ns["w"], ns["ADELANTA1"], ns["ADELANTA2"], ns["INCLINA"]
    for h in ("Spine_alfred", "Spine1_alfred"):
        dp = 'pose.bones["%s"].rotation_euler' % h
        reescribir(dp, 0, lambda f, b: b[f] - 0.5 * (INC[0] * w(ADEL1, f) + (INC[1] - INC[0]) * w(ADEL2, f)), ADEL1[0] - 1)
    # 3) el pie izquierdo
    sc.frame_set(F_A[0] + F_A[1])
    bpy.context.view_layer.update()
    pa, ea = resolver(arm, T_A)
    sc.frame_set(F_B[0] + F_B[1])
    bpy.context.view_layer.update()
    pb_, eb = resolver(arm, T_B)
    canales = [(PIERNA, 0), (PIERNA, 1), (PIERNA, 2), (RODILLA, 0)]
    for k, (h, i) in enumerate(canales):
        dp = 'pose.bones["%s"].rotation_euler' % h
        v0 = cur(dp, i, F_A[0] - 1)
        reescribir(dp, i, lambda f, b, v0=v0, a=pa[k], bb=pb_[k]: b[f] + ((a - v0) * S((f - F_A[0]) / F_A[1]) + (bb - a) * S((f - F_B[0]) / F_B[1])) * (1 - S((f - F_VUELVE[0]) / F_VUELVE[1])), F_A[0] - 1)
    # 4) el pico sigue al pie
    ns["EMPUJADOR"], ns["EMPUJA_OFF"], ns["EMPUJA_DIST"] = RODILLA, 0.2, 0.45
    reb, ult, sp = ns["animar_pico"]()
    import json
    tx = bpy.data.texts.get("rebotes_pico") or bpy.data.texts.new("rebotes_pico")
    tx.clear()
    tx.write(json.dumps(reb))
    ns["sonorizar_pico"](reb)
    sc.frame_set(1)
    return {"errores_pie": (round(ea, 3), round(eb, 3)), "rebotes": reb, "reposo_en": ult, "roce": list(ns["ROCE"]), "suelta": list(ns["SUELTA"])}
