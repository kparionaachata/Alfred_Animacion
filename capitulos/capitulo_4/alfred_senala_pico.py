# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: Alfred, sentado y mirando a Jerry, senala con la mano izquierda su pico de piedra (`alfred_pico_piedra`) mientras dice
"Pero acaso no me ves, a la justas tengo un pico de piedra." (voz en 746-809). El brazo izquierdo (LeftUpArm + Leftelbow) se resuelve con cinematica directa
(busqueda por descenso de coordenadas) para que el antebrazo apunte desde el hombro al pico; sube en F_SUBE, se sostiene y baja en F_BAJA.
Se SUMA a las claves existentes: nuevo(f) = actual(f) + (pose_senalar - actual(F_HOLD)) * peso(f). No repetible sin regenerar antes la animacion del brazo.
Uso en Blender: exec(open(ruta, encoding="utf8").read()); construir()
"""
import bpy, math
from mathutils import Matrix, Vector, Euler
from bpy_extras import anim_utils

F_SUBE = (768, 12)                      # inicio y duracion de la subida (el gesto llega a la palabra "pico", ~frame 790)
F_BAJA = (806, 14)
F_HOLD = 788
ARM, UP, CODO, PADRE, PICO = "Armature", "LeftUpArm_alfred", "Leftelbow_alfred", "Spine2_alfred", "alfred_pico_piedra"


def _basis(pb, e):
    return Matrix.Translation(pb.location) @ Euler(e, 'XYZ').to_matrix().to_4x4()


def _fk(arm, M_padre, e_up, e_codo):
    up, co = arm.pose.bones[UP], arm.pose.bones[CODO]
    pad = arm.pose.bones[PADRE]
    M_up = M_padre @ (pad.bone.matrix_local.inverted() @ up.bone.matrix_local) @ _basis(up, e_up)
    M_co = M_up @ (up.bone.matrix_local.inverted() @ co.bone.matrix_local) @ _basis(co, e_codo)
    return M_up, M_co


def resolver(arm, objetivo_w):
    pad = arm.pose.bones[PADRE]
    M_padre = pad.matrix.copy()
    W = arm.matrix_world
    obj = W.inverted() @ objetivo_w
    up, co = arm.pose.bones[UP], arm.pose.bones[CODO]
    L_co = co.bone.length
    e_up, e_co = list(up.rotation_euler), list(co.rotation_euler)

    def coste(p):
        M_up, M_co = _fk(arm, M_padre, p[:3], (e_co[0], e_co[1], p[3]))
        hombro = M_up.translation
        mano = M_co @ Vector((0, L_co, 0))
        d = (obj - hombro)
        eje = (mano - M_co.translation).normalized()
        ang = math.acos(max(-1.0, min(1.0, eje.dot(d.normalized()))))
        reach = (hombro - M_co.translation).length + L_co
        mano_obj = hombro + d.normalized() * min(d.length, reach)
        return (mano - mano_obj).length + 0.6 * ang + 0.15 * abs(p[3] - 0.25)        # antebrazo apuntando al pico, codo casi estirado
    p = [e_up[0], e_up[1], e_up[2], e_co[2]]
    mejor = coste(p)
    paso = 0.6
    for _ in range(400):
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


def _w(f):
    a, d = F_SUBE
    b, e = F_BAJA
    s = lambda t: (lambda x: x * x * (3 - 2 * x))(max(0.0, min(1.0, t)))
    return s((f - a) / float(d)) * (1.0 - s((f - b) / float(e)))


def construir():
    sc = bpy.context.scene
    O = bpy.data.objects
    arm = O[ARM]
    sc.frame_set(F_HOLD)
    bpy.context.view_layer.update()
    pico = O[PICO].matrix_world.translation.copy()
    pico.z += 0.05
    p, c = resolver(arm, pico)
    cb = anim_utils.action_get_channelbag_for_slot(arm.animation_data.action, arm.animation_data.action_slot)
    fin = sc.frame_end
    destinos = {(UP, 0): p[0], (UP, 1): p[1], (UP, 2): p[2], (CODO, 2): p[3]}
    for (hueso, idx), destino in destinos.items():
        fc = cb.fcurves.find('pose.bones["%s"].rotation_euler' % hueso, index=idx)
        base = {f: fc.evaluate(f) for f in range(F_SUBE[0] - 2, fin + 1)}
        v0 = base[F_HOLD]
        for i in range(len(fc.keyframe_points) - 1, -1, -1):
            if fc.keyframe_points[i].co.x >= F_SUBE[0] - 2:
                fc.keyframe_points.remove(fc.keyframe_points[i])
        for f in range(F_SUBE[0] - 2, fin + 1):
            fc.keyframe_points.insert(f, base[f] + (destino - v0) * _w(f), options={'FAST'}).interpolation = 'LINEAR'
        fc.update()
    sc.frame_set(1)
    return {"angulos_deg": [round(math.degrees(x), 1) for x in p], "error": round(c, 3), "sube": F_SUBE, "baja": F_BAJA}
