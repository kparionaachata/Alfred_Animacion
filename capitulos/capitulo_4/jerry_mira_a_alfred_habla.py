# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: Jerry mira a Alfred con la cabeza mientras Alfred habla. Restriccion DAMPED_TRACK (eje Y) en el hueso `scull` de Jerry hacia `face_alfred`, con la
influencia animada: 0 -> 0.85 al empezar cada frase de Alfred y de vuelta a 0 al terminar su gesto. Ventanas: 626-664 ("Bueno, hasta aqui bajamos.") y 748-886
("Pero acaso no me ves..." y "mejor continuemos..." con el empuje del pico). Entre ellas Jerry le habla o esta de frente a el.
Uso en Blender: exec(open(ruta, encoding="utf8").read()); construir()      (repetible)
"""
import bpy

RIG, HUESO, DESTINO, SUB = "Dog_001_rig", "scull", "Armature", "face_alfred"
CLAVES = [(618, 0.0), (626, 0.85), (664, 0.85), (672, 0.0), (738, 0.0), (748, 0.85), (852, 0.85), (862, 0.0), (950, 0.0), (965, 0.85), (1040, 0.85)]
PICO_ROT = (28.414, -14.285, 55.739)                                  # grados: valor de scull_1 (indicado por el usuario) para ver caer el pico
PICO_SUBE, PICO_BAJA = (850, 12), (945, 17)


def construir():
    O = bpy.data.objects
    b = O[RIG].pose.bones[HUESO]
    for c in list(b.constraints):
        if c.name == "Mirar_a_Alfred":
            b.constraints.remove(c)
    c = b.constraints.new('DAMPED_TRACK')
    c.name, c.target, c.subtarget, c.track_axis = "Mirar_a_Alfred", O[DESTINO], SUB, 'TRACK_Y'
    for f, v in CLAVES:
        c.influence = v
        c.keyframe_insert("influence", frame=f)
    for k in list(b.constraints):                              # sin restriccion para el pico: solo rota scull_1 (ver mira_pico)
        if k.name == "Mirar_pico_que_cae":
            b.constraints.remove(k)
    return len(CLAVES)


def mira_pico():
    """Jerry ve caer el pico SOLO rotando el hueso `scull_1`: sube a PICO_ROT entre 850 y 862, se mantiene y vuelve a su valor de antes entre 945 y 962.
    Se suma a las claves actuales (no repetible sin deshacer: pasar signo=-1)."""
    import math
    from bpy_extras import anim_utils
    rig = bpy.data.objects[RIG]
    cb = anim_utils.action_get_channelbag_for_slot(rig.animation_data.action, rig.animation_data.action_slot)
    fin = bpy.context.scene.frame_end
    S = lambda t: (lambda x: x * x * (3 - 2 * x))(max(0.0, min(1.0, t)))
    w = lambda f: S((f - PICO_SUBE[0]) / float(PICO_SUBE[1])) * (1 - S((f - PICO_BAJA[0]) / float(PICO_BAJA[1])))
    for i in range(3):
        fc = cb.fcurves.find('pose.bones["scull_1"].rotation_euler', index=i)
        base = {f: fc.evaluate(f) for f in range(PICO_SUBE[0] - 1, fin + 1)}
        v0 = base[PICO_SUBE[0]]
        for j in range(len(fc.keyframe_points) - 1, -1, -1):
            if fc.keyframe_points[j].co.x >= PICO_SUBE[0] - 1:
                fc.keyframe_points.remove(fc.keyframe_points[j])
        d = math.radians(PICO_ROT[i]) - v0
        for f in range(PICO_SUBE[0] - 1, fin + 1):
            fc.keyframe_points.insert(f, base[f] + d * w(f), options={'FAST'}).interpolation = 'LINEAR'
        fc.update()
    return PICO_ROT


# ---- v2: la restriccion DAMPED_TRACK sobre `scull` deformaba las mallas de la cabeza (giraba todo el hueso mas de 100 deg); ahora la cabeza gira con `scull_1`, como en la
# rotacion que dio el usuario para ver caer el pico (28.4, -14.3, 55.7 deg), con tope de 57 deg y el mismo peso (0.85) en las mismas ventanas (+300 por los frames insertados).
VENTANAS = [(918, 0.0), (926, 0.85), (964, 0.85), (972, 0.0), (1038, 0.0), (1048, 0.85), (1152, 0.85), (1162, 0.0), (1250, 0.0), (1265, 0.85), (1340, 0.85), (1360, 0.0)]     # entre el 972 y el 1038 mira con la pose hablar_1 (jerry_pose_hablar.py)
TOPE = 70.0                                                  # grados maximos de rotacion en Z de scull_1 (el valor del usuario era 55.7)
COEF = 0.715                                                 # grados de giro de la cabeza por grado de scull_1.z (medido); + en z = giro a la derecha


def mira_alfred_scull1(cada=3):
    import math
    from mathutils import Vector
    from bpy_extras import anim_utils
    sc = bpy.context.scene
    O = bpy.data.objects
    rig, jr, ar = O[RIG], O["jerry"], O[DESTINO]
    for c in list(rig.pose.bones[HUESO].constraints):
        if c.name.startswith("Mirar_"):
            rig.pose.bones[HUESO].constraints.remove(c)
    f0, f1 = VENTANAS[0][0], VENTANAS[-1][0]
    w = lambda f: next((v0 + (v1 - v0) * (f - a) / float(b - a) for (a, v0), (b, v1) in zip(VENTANAS, VENTANAS[1:]) if a <= f <= b), 0.0)
    muestras = {}
    for f in range(f0, f1 + 1, cada):
        if w(f) <= 0.0:
            muestras[f] = 0.0
            continue
        sc.frame_set(f)
        bpy.context.view_layer.update()
        h = rig.matrix_world @ rig.pose.bones[HUESO].head
        t = (ar.matrix_world @ ar.pose.bones[SUB].head) - h
        fw = jr.matrix_world.to_quaternion() @ Vector((0, 1, 0))
        ang = math.degrees(math.atan2(fw.cross(Vector((t.x, t.y, 0))).z, fw.dot(Vector((t.x, t.y, 0)))))      # + = Alfred a la izquierda
        muestras[f] = ang                                                                                      # giro de cabeza deseado (grados; + = hacia la izquierda)
    ks = sorted(muestras)

    def deseado(f):
        if f <= ks[0] or f >= ks[-1]:
            return muestras[ks[0] if f <= ks[0] else ks[-1]]
        a = ks[0] + ((f - ks[0]) // cada) * cada
        return muestras[a] + (muestras[min(a + cada, ks[-1])] - muestras[a]) * (f - a) / float(cada)
    cb = anim_utils.action_get_channelbag_for_slot(rig.animation_data.action, rig.animation_data.action_slot)
    fc = cb.fcurves.find('pose.bones["scull_1"].rotation_euler', index=2)
    # valor base de scull_1.z SIN el giro hacia Alfred: solo la rotacion que da el usuario para ver caer el pico (mira_pico: 55.739 deg entre 1150 y 1262), el resto es 0
    Sm = lambda t: (lambda x: x * x * (3 - 2 * x))(max(0.0, min(1.0, t)))
    base = {f: math.radians(PICO_ROT[2]) * Sm((f - PICO_SUBE[0] - 300) / float(PICO_SUBE[1])) * (1 - Sm((f - PICO_BAJA[0] - 300) / float(PICO_BAJA[1]))) for f in range(f0, f1 + 1)}
    for j in range(len(fc.keyframe_points) - 1, -1, -1):
        if f0 <= fc.keyframe_points[j].co.x <= f1:
            fc.keyframe_points.remove(fc.keyframe_points[j])
    for f in range(f0, f1 + 1):
        zdeg = max(-TOPE, min(TOPE, -deseado(f) * w(f) / COEF))       # + en z = giro a la derecha, por eso el signo
        fc.keyframe_points.insert(f, base[f] + math.radians(zdeg), options={'FAST'}).interpolation = 'LINEAR'
    fc.update()
    sc.frame_set(1)
    return {"max_z_deg": round(max(abs(max(-TOPE, min(TOPE, -deseado(f) * w(f) / COEF))) for f in range(f0, f1 + 1)), 1)}
