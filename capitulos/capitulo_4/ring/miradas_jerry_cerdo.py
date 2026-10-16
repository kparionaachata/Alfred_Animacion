# -*- coding: utf-8 -*-
"""base_ranas_3: Jerry y cerdo_ring se miran a los ojos mientras hablan.
Por frame (frame_set) se resuelve la rotacion local que hace que la CARA apunte a los ojos del otro:
 - Jerry: hueso scull_1 (cara = direccion de la nariz en reposo, en el espacio de scull); objetivo = ojos del cerdo
   (cabezas de Eye-L/R). Pesos: ventanas en que Jerry mira al cerdo (jerry_ranas3.F_CERDO / F_OTRA).
 - Cerdo: hueso Head_cerdo_1 (cara = eje Y del hueso); objetivo = ojos de Jerry (cabezas de las cejas). Ventana GIRO.
Se conserva el giro sobre el propio eje (rotation_difference minima) y se mezcla con el peso de la ventana.
Las claves resultantes reemplazan las de scull_1 / Head_cerdo_1 en esos frames (los scripts de animacion las rehacen).
Uso (exec en Blender): iniciar()  (timer)  -> driver_namespace["miradas"]
"""
import bpy, math
from mathutils import Vector, Quaternion, Euler

DIR = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/"
JN = {}; exec(compile(open(DIR + "jerry_ranas3.py", encoding="utf8").read(), "jerry_ranas3.py", "exec"), JN)
CN = {}; exec(compile(open(DIR + "cerdo_responde_jerry.py", encoding="utf8").read(), "cerdo_responde_jerry.py", "exec"), CN)
JARM, PARM = "Dog_001_rig", "pig.arma_cerdo_1"


def peso_jerry(f):
    a, b, c, d = JN["F_CERDO"]; e, g, h, i = JN["F_OTRA"]
    return max(JN["ramp"](f, a, b) * (1 - JN["ramp"](f, c, d)), JN["ramp"](f, e, g) * (1 - JN["ramp"](f, h, i)))


def peso_cerdo(f):
    return CN["ventana"](f, CN["GIRO"])


def base_q(arm, pb):
    R_parent = (arm.matrix_world @ pb.parent.matrix).to_3x3()
    rest = pb.parent.bone.matrix_local.to_3x3().inverted() @ pb.bone.matrix_local.to_3x3()
    return (R_parent @ rest).normalized().to_quaternion()      # mundo del hueso con pose local = identidad (sin escala)


def giro_hacia(cara, pivote, ojo, objetivo, n=4):
    """rotacion de mundo (sobre el pivote) que hace mirar `cara` desde el ojo (que gira con la cabeza) al objetivo"""
    g = Quaternion()
    for _ in range(n):
        ojo_g = pivote + g @ (ojo - pivote)
        g = cara.rotation_difference((objetivo - ojo_g).normalized())
    return g


def a_local(arm, bone, g, w):
    pb = arm.pose.bones[bone]; B = base_q(arm, pb); q0 = pb.rotation_euler.to_quaternion()
    q_new = B.inverted() @ g @ B @ q0
    return q0.slerp(q_new, w).to_euler('XYZ', pb.rotation_euler)


def iniciar(sincrono=False):
    sc = bpy.context.scene
    ja, pa = bpy.data.objects[JARM], bpy.data.objects[PARM]
    # cara de Jerry en el espacio del hueso scull (en reposo mira a +Y del armature)
    cara_j = (ja.data.bones["scull"].matrix_local.to_3x3().inverted() @ Vector((0, 1, 0))).normalized()
    a, b, c, d = JN["F_CERDO"]; e, g, h, i = JN["F_OTRA"]; g0, g1 = CN["GIRO"][0], CN["GIRO"][3]
    frames = sorted(set(range(a, d + 1)) | set(range(e, i + 1)) | set(range(g0, g1 + 1)))
    st = {"cola": frames, "i": 0, "j": {}, "p": {}, "estado": "corriendo", "error": None, "cara_j": cara_j}
    # los objetos ocultos (p.ej. con el add-on de espectadores) NO se evaluan: se muestran mientras se calcula
    st["ocultos"] = [o.name for r in ("jerry", "cerdo_ring") for o in [bpy.data.objects[r]] + list(bpy.data.objects[r].children_recursive) if o.hide_viewport]
    for n in st["ocultos"]: bpy.data.objects[n].hide_viewport = False
    def restaurar():
        for n in st["ocultos"]: bpy.data.objects[n].hide_viewport = True
        st["ocultos"] = []
    bpy.app.driver_namespace["miradas"] = st

    def tick(lote=25):
        try:
            for _ in range(lote):
                if st["i"] >= len(st["cola"]):
                    escribir(st); restaurar(); st["estado"] = "listo"; return None
                f = st["cola"][st["i"]]; st["i"] += 1; sc.frame_set(f)
                if bpy.app.background and st["i"] % 20 == 0: print("RES frame", f, flush=True)
                ojos_p = sum(((pa.matrix_world @ pa.pose.bones[n].head) for n in ("Eye-L_cerdo_1", "Eye-R_cerdo_1")), Vector()) / 2
                ojos_j = sum(((ja.matrix_world @ ja.pose.bones[n].head) for n in ("sejas_1_jerry", "sejas_2_jerry")), Vector()) / 2
                wj, wp = peso_jerry(f), peso_cerdo(f)
                pb1, pbs = ja.pose.bones["scull_1"], ja.pose.bones["scull"]
                cara_j = ((ja.matrix_world @ pbs.matrix).to_3x3().normalized() @ st["cara_j"]).normalized()
                piv_j = ja.matrix_world @ pb1.head
                cara_p = ((pa.matrix_world @ pa.pose.bones["Head_cerdo_1"].matrix).to_3x3().normalized() @ Vector((0, 1, 0))).normalized()
                piv_p = pa.matrix_world @ pa.pose.bones["Head_cerdo_1"].head
                gj, gp = Quaternion(), Quaternion()
                for _ in range(4):                                  # los dos se mueven: se resuelven juntos
                    oj = piv_j + gj @ (ojos_j - piv_j); op = piv_p + gp @ (ojos_p - piv_p)
                    if wj > 0: gj = Quaternion().slerp(giro_hacia(cara_j, piv_j, ojos_j, op), wj)
                    if wp > 0: gp = Quaternion().slerp(giro_hacia(cara_p, piv_p, ojos_p, oj), wp)
                if wj > 0: st["j"][f] = tuple(a_local(ja, "scull_1", gj, 1.0))
                if wp > 0: st["p"][f] = tuple(a_local(pa, "Head_cerdo_1", gp, 1.0))
            return 0.01
        except Exception:
            import traceback; st["error"] = traceback.format_exc(); st["estado"] = "error"; restaurar(); return None
    if sincrono:                                            # Blender en segundo plano (sin timers)
        while st["estado"] == "corriendo" and tick(10 ** 6) is not None: pass
        return st
    bpy.app.timers.register(tick, first_interval=0.05)
    return st


def escribir(st):
    for objn, bone, datos in ((JARM, "scull_1", st["j"]), (PARM, "Head_cerdo_1", st["p"])):
        o = bpy.data.objects[objn]; a = o.animation_data.action
        for k in range(3):
            fc = a.fcurve_ensure_for_datablock(o, 'pose.bones["%s"].rotation_euler' % bone, index=k)
            for f, e in sorted(datos.items()):
                fc.keyframe_points.insert(f, e[k], options={'FAST'}).interpolation = 'LINEAR'
            fc.update()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
