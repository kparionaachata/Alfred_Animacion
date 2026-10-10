# -*- coding: utf-8 -*-
"""CONVENCION DE HERRAMIENTAS DE ALFRED (2026-10-08): las herramientas / armas van APARENTADAS al hueso, como en `estructura_lista/alfred.blend` (parent_type BONE a `Spine1_alfred`, matrix_parent_inverse = identidad;
el hacha de piedra casi pegada a la malla del torso, ~0.002 de hueco / 1.7 cm dentro; `wooden_pickaxe` a 0.039 y `wooden_axe` a 0.107 del torso, en capas hacia atras).
En una animacion el emparentado se cambia con 2 constraints Child Of por herramienta y la INFLUENCIA con claves (constantes):
  "Espalda" -> hueso `Spine1_alfred` (matriz relativa de `rel_espalda_alfred_blend.json`; `basis` = esa matriz),
  "Mano"    -> hueso `Rightelbow_alfred` (`basis` = pose de la herramienta relativa a la mano, con claves por frame).
Aparentar = Mano pasa a 1 y Espalda a 0 en el frame de agarre (la herramienta estaba en su sitio de la espalda, por lo que no salta); desaparentar = al reves en el frame en que queda guardada.
Cada vez que se saque o se guarde una herramienta se hace antes la animacion del brazo hacia la espalda (ver `alfred_rompe_la_mesa.py`, `alfred_guarda_el_hacha.py`, `alfred_talla_la_puerta.py`).
Se ejecuta DENTRO de Blender con exec despues de esos scripts (convierte las claves de mundo horneadas del hacha en emparentado y deja la pala siempre en la espalda). Nunca `raise SystemExit`.
Variables opcionales: FASES_MANO = [(frame_agarre, ultimo_frame_en_mano), ...] (el ultimo = frame anterior al de guardar; el hacha vuelve a la espalda en el siguiente)."""
import bpy, json, math, traceback
from mathutils import Matrix, Vector

try:
    sc = bpy.context.scene
    AA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "Hips_alfred" in o.pose.bones)
    axe = bpy.data.objects["stone_axe"]; shovel = bpy.data.objects["stone_shovel"]
    RAB = json.load(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\rel_espalda_alfred_blend.json", encoding="utf-8"))
    m = RAB["herramientas"]["stone_axe"]["matriz"]; REL_AXE = Matrix([m[0:4], m[4:8], m[8:12], m[12:16]])
    REL_SHOVEL = Matrix(((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
    # la pala no esta en alfred.blend: se conserva su sitio actual en la espalda (relativo a Spine1) tomado de la escena
    FASES = globals().get("FASES_MANO") or [(569, 661), (757, 900)]
    ULT = max(b for a, b in FASES); FIN_HACHA = 860
    # 1) pose deseada (mundo) del hacha en las fases en mano y pose actual de la pala, leidas de las claves horneadas
    sc.frame_set(1); Sp1_1 = AA.matrix_world @ AA.pose.bones["Spine1_alfred"].matrix; REL_SHOVEL = Sp1_1.inverted() @ shovel.matrix_world.copy()
    W = {}; HAND = {}
    for a, b in FASES:
        for f in range(a, min(b, FIN_HACHA) + 1):
            sc.frame_set(f); W[f] = axe.matrix_world.copy(); HAND[f] = (AA.matrix_world @ AA.pose.bones["Rightelbow_alfred"].matrix).copy()
    muestras = {}
    for f in (1, 300, 562, 700, 732, 860):
        sc.frame_set(f); muestras[f] = {"axe": axe.matrix_world.copy(), "shovel": shovel.matrix_world.copy(), "Sp1": (AA.matrix_world @ AA.pose.bones["Spine1_alfred"].matrix).copy()}
    # 2) quitar las claves horneadas y crear los constraints
    for o in (axe, shovel):
        if o.animation_data and o.animation_data.action:
            a = o.animation_data.action; o.animation_data.action = None; bpy.data.actions.remove(a)
        for c in list(o.constraints): o.constraints.remove(c)
        o.rotation_mode = 'QUATERNION'
    def cons(o, nombre, hueso):
        c = o.constraints.new('CHILD_OF'); c.name = nombre; c.target = AA; c.subtarget = hueso; c.influence = 1.0
        c.inverse_matrix = Matrix.Identity(4); return c
    cE = cons(axe, "Espalda", "Spine1_alfred"); cM = cons(axe, "Mano", "Rightelbow_alfred"); cE_p = cons(shovel, "Espalda", "Spine1_alfred")
    def basis(o, M, f=None):
        l, q, s = M.decompose(); o.location = l; o.rotation_quaternion = q; o.scale = s
        if f is not None: o.keyframe_insert("location", frame=f); o.keyframe_insert("rotation_quaternion", frame=f); o.keyframe_insert("scale", frame=f)
    def influencias(espalda, mano, f):
        cE.influence = espalda; cM.influence = mano; cE.keyframe_insert("influence", frame=f); cM.keyframe_insert("influence", frame=f)
    # pala: siempre en la espalda, sin claves
    basis(shovel, REL_SHOVEL)
    # hacha: espalda -> mano (aparentar) -> espalda (desaparentar) -> mano
    basis(axe, REL_AXE, 1); influencias(1.0, 0.0, 1)
    for i, (a, b) in enumerate(FASES):
        b = min(b, FIN_HACHA)
        basis(axe, REL_AXE, a - 1); influencias(1.0, 0.0, a - 1)                  # ultimo frame en la espalda (basis = espalda)
        for f in range(a, b + 1):
            basis(axe, HAND[f].inverted() @ W[f], f)
            if f == a: influencias(0.0, 1.0, f)                                    # APARENTAR a la mano
        if b < FIN_HACHA:
            basis(axe, REL_AXE, b + 1); influencias(1.0, 0.0, b + 1)               # DESAPARENTAR: vuelve a la espalda
    for fc in axe.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT' if "influence" in fc.data_path else 'LINEAR'
    # 3) verificacion: el resultado debe coincidir con la pose horneada anterior
    res = {}
    for f in (1, 300, 562, 700, 732, 860):
        sc.frame_set(f); dA = (axe.matrix_world.translation - muestras[f]["axe"].translation).length; dS = (shovel.matrix_world.translation - muestras[f]["shovel"].translation).length
        res[f] = {"hacha_dif": round(dA, 4), "pala_dif": round(dS, 4)}
    for f in (569, 575, 600, 640, 661, 662, 757, 800, 850):
        if f in W:
            sc.frame_set(f); res[f] = {"hacha_dif": round((axe.matrix_world.translation - W[f].translation).length, 4)}
    sc.frame_set(120); print("diferencias (m):", res); print("LISTO")
except Exception:
    traceback.print_exc()
