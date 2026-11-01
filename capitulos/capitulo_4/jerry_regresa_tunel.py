# -*- coding: utf-8 -*-
"""alfred_cueva_5E.blend: mientras la criatura trepa, Jerry se va de regreso por el tunel (sentido contrario a la caverna, hacia +Y) caminando con el pico de piedra (jerry_pico) en la boca.
Desde F_A: se coloca en su sitio junto al pico (FINAL), baja la cabeza, abre la boca, muerde el pico del suelo y lo levanta; gira hacia el tunel, pasa por CODO y camina recto por el eje del tunel
hasta F_FIN. Ciclo de caminar y agarre del pico en la boca: los mismos de jerry_llega_salida.py (camina con la antorcha en la boca.py repetida en bucle de 60 frames, REL_PICO relativo a jaw_top).
Uso: exec(open(ruta, encoding="utf8").read()); construir()      (repetible)"""
import bpy, math
from mathutils import Vector, Matrix, Euler

CAMINAR = r"C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/jerry_camina_payload.json"      # animacion de Jerry caminando con la antorcha en la boca (camina con la antorcha en la boca.py)
F_A = 84                                            # empieza a moverse (la criatura ya esta trepando)
F_FIN = 729
Z_JERRY = 66.15                                     # altura de su empty
CODO = Vector((0.4529, 85.95, Z_JERRY))             # eje del tunel, pasando el hueco del tapon
FINAL = Vector((-0.27542, 84.485, Z_JERRY))          # su sitio junto al pico
RZ_FINAL = math.radians(148)
VEL = 0.045                                         # m por frame (velocidad media de la animacion con la antorcha)
F_ACOMODA = 14                                      # de donde esta a FINAL
F_PICA = 34                                         # baja, muerde y levanta el pico
PICO = "jerry_pico"
PICO_SUELO = Vector((-0.463, 83.664, 66.05))
PICO_RZ = math.radians(-78.326)
JAW_TOP = (12.62, -0.39805, -0.031797)
JAW_BOT = (-23.97, -0.76517, 0.20142)
REL_PICO = [[0.310716, 0.340091, 0.02848, 0.127948], [-0.144332, 0.096044, 0.42774, 0.096868], [0.30926, -0.296869, 0.171011, -0.087825], [0, 0, 0, 1]]


def ss(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _ciclo():
    import json
    return json.load(open(CAMINAR))


LOOP, I0 = 60, 20                                    # tramo de la caminata que se repite: frames 20..79 (la diferencia entre i e i+60 es minima), con fundido de 8 frames al volver al inicio


def construir(f_a=F_A, f_fin=F_FIN):
    O = bpy.data.objects
    sc = bpy.context.scene
    root, arm, pico = O["jerry"], O["Dog_001_rig"], O[PICO]
    pb = arm.pose.bones
    p_ini, rz_ini = root.location.copy(), root.rotation_euler[2]
    p_ini.z = Z_JERRY
    floor_loc, floor_rot, floor_esc = PICO_SUELO.copy(), Euler((0.0, 0.0, PICO_RZ)), Vector((0.6, 0.6, 0.6))      # donde esta el pico en el suelo (jerry_llega_salida.py)
    for o in (root, arm, pico):
        if o.animation_data:
            o.animation_data_clear()
    for b in pb:
        b.rotation_mode = 'XYZ'
    pico.parent = None
    pico.rotation_mode = 'XYZ'
    pico.location, pico.rotation_euler = floor_loc, floor_rot
    C = _ciclo()
    B = C["bones"]
    jt_p = C["constantes"]["jaw_top"]["rotation_euler"]
    jb_p = C["constantes"]["jaw_bot"]["rotation_euler"]

    def andar(i, amp):
        """eulers de los huesos al caminar (frame i desde que empieza), en bucle, con la amplitud amp"""
        k = i % LOOP
        out = {}
        for n, ch in B.items():
            v = ch["rotation_euler"]
            a = v[I0 + k]
            if k < 8 and i >= LOOP:
                w = k / 8.0
                b = v[I0 + k + LOOP]
                a = [b[j] + (a[j] - b[j]) * w for j in range(3)]
            out[n] = tuple(x * amp for x in a)
        return out
    jt = [math.radians(a) for a in JAW_TOP]
    jb = [math.radians(a) for a in JAW_BOT]

    def pose_cero():
        for b in pb:
            b.rotation_euler = (0, 0, 0)

    def mandibula(w, abre=0.0):
        pb["jaw_top"].rotation_euler = tuple(v * w for v in jt)
        pb["jaw_bot"].rotation_euler = (jb[0] * w - 0.6 * abre, jb[1] * w, jb[2] * w)

    def clave(f, pos, rz, pico_modo):
        """pico_modo: 'suelo' (queda donde estaba), 'boca' (agarrado) o ('vuela', u)"""
        root.location = pos
        root.rotation_euler = (0, 0, rz)
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_euler", frame=f)
        for b in pb:
            b.keyframe_insert("rotation_euler", frame=f)
        if pico_modo == "suelo":
            pico.location, pico.rotation_euler = floor_loc, floor_rot
            pico.scale = floor_esc
        else:
            bpy.context.view_layer.update()
            M = arm.matrix_world @ pb["jaw_top"].matrix @ Matrix(REL_PICO)
            l, q, s = M.decompose()
            if pico_modo != "boca":
                u = ss(pico_modo[1])
                l = floor_loc.lerp(l, u)
                q = floor_rot.to_quaternion().slerp(q, u)
                s = floor_esc.lerp(s, u)
            pico.location = l
            pico.rotation_euler = q.to_euler('XYZ', pico.rotation_euler)
            pico.scale = s
        for dp in ("location", "rotation_euler", "scale"):
            pico.keyframe_insert(dp, frame=f)

    # antes: quieto como estaba
    pose_cero()
    clave(1, p_ini, rz_ini, "suelo")
    clave(f_a, p_ini, rz_ini, "suelo")
    f = f_a
    # 1) se acomoda junto al pico caminando
    for i in range(1, F_ACOMODA + 1):
        f = f_a + i
        u = ss(i / float(F_ACOMODA))
        amp = min(1.0, i / 4.0, (F_ACOMODA - i) / 4.0 + 0.001)
        pose_cero()
        for n, e in andar(f - f_a, amp).items():
            if n in pb:
                pb[n].rotation_euler = e
        clave(f, p_ini.lerp(FINAL, u), rz_ini + (RZ_FINAL - rz_ini) * u, "suelo")
    f_pica0 = f
    # 2) baja la cabeza, abre la boca, muerde el pico y lo levanta
    for k in range(1, F_PICA + 1):
        f = f_pica0 + k
        t = k / float(F_PICA)
        baja = ss(t / 0.4) * (1.0 - ss((t - 0.52) / 0.4))
        abre = ss((t - 0.15) / 0.2) * (1.0 - ss((t - 0.42) / 0.1))
        w = ss((t - 0.46) / 0.14)
        pose_cero()
        for n, a in (("spine_1", 0.45), ("spine_2", 0.45), ("spine_3", 0.3)):
            pb[n].rotation_euler = (a * baja, 0, 0)
        pb["front_shin.L"].rotation_euler = (-0.15 * baja, 0, 0)
        pb["front_shin.R"].rotation_euler = (-0.15 * baja, 0, 0)
        mandibula(w, abre)
        if t < 0.5:
            modo = "suelo"
        elif t < 0.62:
            modo = ("vuela", (t - 0.5) / 0.12)
        else:
            modo = "boca"
        clave(f, FINAL, RZ_FINAL, modo)
    f_giro0 = f
    # 3) gira hacia el tunel (por el este) y camina hasta CODO; luego recto por el eje del tunel
    n1 = int(round((CODO - FINAL).length / VEL))
    rz_fin = 2 * math.pi
    for i in range(1, f_fin - f_giro0 + 1):
        f = f_giro0 + i
        if i <= n1:
            u = ss(i / float(n1))
            pos = FINAL.lerp(CODO, u)
            rz = RZ_FINAL + (rz_fin - RZ_FINAL) * u
        else:
            pos = CODO + Vector((0, VEL * (i - n1), 0))
            rz = rz_fin
        amp = min(1.0, i / 6.0)
        pose_cero()
        for n, e in andar(f - f_a, amp).items():
            if n in pb:
                pb[n].rotation_euler = e
        c = ss(i / 6.0)                                                   # de la pose del mordisco a la mandibula de la animacion
        pb["jaw_top"].rotation_euler = tuple(a * (1 - c) + b * c for a, b in zip(jt, jt_p))
        pb["jaw_bot"].rotation_euler = tuple(a * (1 - c) + b * c for a, b in zip(jb, jb_p))
        clave(f, pos, rz, "boca")
    sc.frame_set(1)
    return {"acomoda": (f_a, f_pica0), "pica": (f_pica0, f_giro0), "camina": (f_giro0, f), "y_final": round(pos.y, 1)}
