# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: desde el frame F_INI Jerry llega caminando por el tunel por detras de Alfred hasta su sitio (encima de
bloque_andesite_-104_-29_0, mirando a la caverna), con un pico de piedra (jerry_pico) en la boca. Al llegar baja la cabeza, abre la boca
y deja el pico en el suelo delante de el, para tener la boca libre.
Ciclo de caminar: animacion_jerry (26).py (estilo RAPIDO, copiado en jerry_caminar_rapido.py). Agarre del pico en la boca: el mismo
de jerry_pica_carbon.py (REL_PICO relativo a jaw_top, mandibulas JAW_TOP / JAW_BOT).
Uso: exec(open(ruta, encoding="utf8").read()); construir()      (repetible)
"""
import bpy, math
from mathutils import Vector, Matrix, Euler

CAMINAR = r"C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/jerry_caminar_rapido.py"
F_INI = 180
INICIO = Vector((0.4529, 92.8, 66.0157))            # dentro del tunel, detras de Alfred
CODO = Vector((0.4529, 85.95, 66.0157))             # justo pasando el hueco del tapon
FINAL = Vector((-0.27542, 84.485, 66.016))          # su sitio (posicion final indicada por el usuario)
RZ_FINAL = math.radians(148)                        # su rotacion Z al quedar
RZ = math.pi                                        # mirando a la caverna (-Y)
VEL = 0.07                                          # m por frame (caminar rapido)
F_GIRO_LADO = 14                                    # el ultimo tramo (de lado, hacia su sitio)
F_DEJA = 30                                         # baja la cabeza, suelta el pico, se endereza
PICO = "jerry_pico"
JAW_TOP = (12.62, -0.39805, -0.031797)
JAW_BOT = (-23.97, -0.76517, 0.20142)
REL_PICO = [[0.310716, 0.340091, 0.02848, 0.127948], [-0.144332, 0.096044, 0.42774, 0.096868], [0.30926, -0.296869, 0.171011, -0.087825], [0, 0, 0, 1]]
PICO_SUELO = Vector((-0.463, 83.664, 66.05))
PICO_RZ = math.radians(-78.326)                     # coordenada y rotacion finales del pico (indicadas por el usuario)          # donde lo deja (delante de sus patas, sobre el bloque)


def _ciclo():
    ns = {"__name__": "jerry_caminar"}; exec(open(CAMINAR, encoding="utf8").read(), ns); return ns


def construir():
    O = bpy.data.objects; sc = bpy.context.scene; root = O["jerry"]; arm = O["Dog_001_rig"]; pb = arm.pose.bones; pico = O[PICO]
    for o in (root, arm, pico):
        if o.animation_data: o.animation_data_clear()
    for b in pb: b.rotation_mode = 'XYZ'
    pico.parent = None; pico.rotation_mode = 'XYZ'; pico.hide_render = pico.hide_viewport = False
    C = _ciclo(); n1 = (INICIO - CODO).length / VEL; f_codo = F_INI + int(round(n1)); f_llega = f_codo + F_GIRO_LADO
    kf = C["generate_keyframes"](f_llega - F_INI + 1)
    jt = [math.radians(a) for a in JAW_TOP]; jb = [math.radians(a) for a in JAW_BOT]

    def pose_quieto():
        for b in pb: b.rotation_euler = (0, 0, 0)
        pb["jaw_top"].rotation_euler = jt; pb["jaw_bot"].rotation_euler = jb

    def clave(f, pos, rz, pico_en_boca=True):
        root.location = pos; root.rotation_euler = (0, 0, rz)
        root.keyframe_insert("location", frame=f); root.keyframe_insert("rotation_euler", frame=f)
        for b in pb: b.keyframe_insert("rotation_euler", frame=f)
        if pico_en_boca:
            bpy.context.view_layer.update()
            M = arm.matrix_world @ pb["jaw_top"].matrix @ Matrix(REL_PICO); l, q, s = M.decompose()
            pico.location = l; pico.rotation_euler = q.to_euler('XYZ', pico.rotation_euler); pico.scale = s
            for dp in ("location", "rotation_euler", "scale"): pico.keyframe_insert(dp, frame=f)

    # antes de F_INI: quieto en el tunel con el pico en la boca
    pose_quieto(); clave(1, INICIO, RZ); clave(F_INI, INICIO, RZ)
    # caminar: recto por el tunel y luego de lado hasta su sitio (girando un poco el cuerpo)
    for f in range(F_INI + 1, f_llega + 1):
        k = f - F_INI
        if f <= f_codo: pos = INICIO.lerp(CODO, (f - F_INI) / max(1, f_codo - F_INI)); rz = RZ
        else:
            u = (f - f_codo) / F_GIRO_LADO; u = u * u * (3 - 2 * u); pos = CODO.lerp(FINAL, u); rz = RZ + (RZ_FINAL - RZ) * u + math.radians(28) * math.sin(math.pi * u)
        amp = min(1.0, k / 6.0, max(0.0, (f_llega - f) / 6.0))
        for b in pb: b.rotation_euler = (0, 0, 0)
        for n, claves in kf.items():
            if n in pb: pb[n].rotation_euler = tuple(v * amp for v in claves[k])
        pb["jaw_top"].rotation_euler = jt; pb["jaw_bot"].rotation_euler = jb
        clave(f, pos + Vector((0, 0, C["VERTICAL_BOB"] * amp * (0.5 - 0.5 * math.cos(4 * math.pi * k / C["CYCLE_LENGTH"])))), rz)
    # dejar el pico delante: baja la cabeza, abre la boca, lo suelta, se endereza
    f0 = f_llega
    for k in range(1, F_DEJA + 1):
        f = f0 + k; t = k / F_DEJA
        baja = math.sin(math.pi * min(1.0, t / 0.8)) if t < 0.8 else 0.0
        abre = max(0.0, min(1.0, (t - 0.35) / 0.15)) * (1 - max(0.0, min(1.0, (t - 0.65) / 0.2)))
        pose_quieto()
        for n, a in (("spine_1", 0.45), ("spine_2", 0.45), ("spine_3", 0.3)): pb[n].rotation_euler = (a * baja, 0, 0)
        pb["front_shin.L"].rotation_euler = (-0.15 * baja, 0, 0); pb["front_shin.R"].rotation_euler = (-0.15 * baja, 0, 0)
        c = max(0.0, min(1.0, (t - 0.65) / 0.2)); c = c * c * (3 - 2 * c)                  # cierra la mandibula (sin el pico el agarre ya no aplica)
        pb["jaw_top"].rotation_euler = tuple(v * (1 - c) for v in jt)
        pb["jaw_bot"].rotation_euler = ((jb[0] - 0.35 * abre) * (1 - c), jb[1] * (1 - c), jb[2] * (1 - c))
        en_boca = t < 0.45
        clave(f, FINAL, RZ_FINAL, pico_en_boca=en_boca)
        if not en_boca:                                                       # cae y queda tendido en el suelo delante
            if k == int(0.45 * F_DEJA) + 1: p_suelta = pico.matrix_world.translation.copy()
            u = min(1.0, (t - 0.45) / 0.17); u = u * u
            pico.location = p_suelta.lerp(PICO_SUELO, u)
            pico.rotation_euler = Euler((0.0, 0.0, PICO_RZ)).to_quaternion().slerp(pico.rotation_euler.to_quaternion(), 1 - u).to_euler('XYZ')
            if u >= 1: pico.rotation_euler = (0.0, 0.0, PICO_RZ)
            pico.keyframe_insert("location", frame=f); pico.keyframe_insert("rotation_euler", frame=f)
    pose_quieto(); pb["jaw_top"].rotation_euler = (0, 0, 0); pb["jaw_bot"].rotation_euler = (0, 0, 0); clave(f0 + F_DEJA + 1, FINAL, RZ_FINAL, pico_en_boca=False)
    sc.frame_set(1)
    return {"camina": (F_INI, f_llega), "deja_pico": (f0, f0 + F_DEJA), "pico_suelto": int(f0 + 0.45 * F_DEJA) + 1}
