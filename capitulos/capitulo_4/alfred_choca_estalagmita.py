# -*- coding: utf-8 -*-
"""En su ultima vuelta (alfred_corre_circulos.py) Alfred se desvia hacia la estalagmita de la celda (-48.5,-14.5) y se estrella de cara:
la arana queda aplastada entre la estalagmita y su cara (arana_salta_cara.py lee alfred["f_choque"]) y Alfred, por inercia, se hunde un poco
mas, rebota hacia atras y cae de espaldas al suelo (gira sobre los talones y se tuerce hacia el sur para no caer sobre Jerry), con un rebote
al tocar el suelo.
- empty `alfred`: claves por frame desde F_DESVIO (recta a la estalagmita, choque, rebote, caida).
- accion de la carrera (`Alfred_corre_circulos`): desde el choque las piernas se estiran, sin rebote de cadera; brazos y cabeza se congelan
  con un latigazo hacia atras.
Orden: alfred_corre_circulos -> alfred_choca_estalagmita -> arana_salta_cara -> jerry_mira_carrera -> sonidos_arana_carrera.
Uso (Blender):  exec(open(r"...\\alfred_choca_estalagmita.py", encoding="utf8").read()); construir()
"""
import bpy, math
from mathutils import Vector, Quaternion, Matrix

F_DESVIO = None                     # None = ultima pasada por el suroeste del ovalo (se busca en la ruta: angulo DESVIO_ANG, antes de F_ULTIMO)
DESVIO_ANG, F_ULTIMO = (195.0, 225.0), 690
ESTALAGMITA = Vector((-48.47, -14.5))
PIEZAS = ("estalagmita_base_-53_-15_-9", "estalagmita_tronco_-53_-15_-8", "estalagmita_punta_-53_-15_-6")
D_STOP = 1.25                       # distancia horizontal cadera-eje de la estalagmita al tocar (se ajusta con medir())
VEL = 4.5 / 24.0
HUNDE, REBOTE, F_REBOTE = 0.22, 0.15, 4      # inercia contra la estalagmita y retroceso
F_CAE, TORCER = 16, 0.0     # cae derecho hacia atras, en sentido contrario al impacto (pedido del usuario)           # frames de caida de espaldas; grados que se tuerce hacia el sur al caer
ESPESOR = 0.30                      # media espalda: la cadera queda a esta altura sobre el suelo al estar tumbado
F_FIN_ESCENA = 730
PISTA_CORRE = "Alfred_corre_circulos"


def _claves_empty(emp, desde):
    for lay in emp.animation_data.action.layers:
        for s in lay.strips:
            for cb in s.channelbags:
                for fc in cb.fcurves:
                    if fc.data_path in ("location", "rotation_quaternion"):
                        for kp in reversed(list(fc.keyframe_points)):
                            if kp.co[0] >= desde: fc.keyframe_points.remove(kp)


def _buscar_desvio(arm):
    sc = bpy.context.scene; mejor = None
    for f in range(600, F_ULTIMO):
        sc.frame_set(f); h = arm.matrix_world @ arm.pose.bones["Hips_alfred"].head
        a = math.degrees(math.atan2((h.y + 15.75) / 0.6, (h.x + 47.9) / 1.2)) % 360
        if DESVIO_ANG[0] <= a <= DESVIO_ANG[1]: mejor = f
    return mejor


def construir(d_stop=None):
    global F_DESVIO
    d_stop = D_STOP if d_stop is None else d_stop
    sc = bpy.context.scene; emp = bpy.data.objects["alfred"]; arm = bpy.data.objects["Armature"]
    if F_DESVIO is None: F_DESVIO = _buscar_desvio(arm)
    sc.frame_end = F_FIN_ESCENA
    sc.frame_set(F_DESVIO)
    E0 = emp.matrix_world.translation.copy(); q0 = emp.matrix_world.to_quaternion()
    H0 = arm.matrix_world @ arm.pose.bones["Hips_alfred"].head
    off = H0 - E0                                                          # cadera respecto del empty
    h = (ESTALAGMITA - H0.to_2d()).normalized(); h3 = Vector((h.x, h.y, 0))
    yaw_h = math.atan2(h.y, h.x)
    # rumbo actual del cuerpo (ojos - cadera)
    dg = bpy.context.evaluated_depsgraph_get(); ojos = []
    for n in ("ojo_izquierdo_alfred", "ojo_derecho_alfred"):
        e = bpy.data.objects[n].evaluated_get(dg); ojos += [e.matrix_world @ v.co for v in e.data.vertices]
    F = sum(ojos, Vector()) / len(ojos) - H0; F.z = 0; F.normalize()
    yaw0 = math.atan2(F.y, F.x)
    dyaw = yaw_h - yaw0
    while dyaw > math.pi: dyaw -= 2 * math.pi
    while dyaw < -math.pi: dyaw += 2 * math.pi
    impacto = ESTALAGMITA - h * d_stop
    largo = (impacto - H0.to_2d()).length
    n_aprox = max(2, int(math.ceil(largo / VEL)))
    fi = F_DESVIO + n_aprox
    claves = []                                                            # (frame, posicion de la cadera, giro en z extra, caida(rad), alza z)
    for k in range(0, n_aprox + 1):
        u = k / n_aprox
        p = H0.to_2d().lerp(impacto, u)
        claves.append((F_DESVIO + k, p, dyaw * min(1.0, k / 2.0), 0.0, 0.0))
    # inercia + rebote
    claves.append((fi + 1, impacto + h * HUNDE, dyaw, 0.0, 0.0))
    for k in range(1, F_REBOTE + 1):
        u = k / F_REBOTE; u = 1 - (1 - u) ** 2
        claves.append((fi + 1 + k, (impacto + h * HUNDE).lerp(impacto - h * REBOTE, u), dyaw, 0.0, 0.0))
    p_pie = impacto - h * REBOTE
    f_cae0 = fi + 1 + F_REBOTE
    for k in range(1, F_CAE + 1):
        u = k / F_CAE
        ang = (math.pi / 2) * u * u                                         # acelera al caer
        tw = math.radians(TORCER) * (3 * u * u - 2 * u * u * u)
        claves.append((f_cae0 + k, p_pie, dyaw, ang, ESPESOR * u * u, tw))
    f_suelo = f_cae0 + F_CAE
    for k, (a_extra, z_extra) in enumerate(((-0.12, 0.06), (-0.05, 0.02), (0.02, -0.005), (0.0, 0.0)), start=1):
        claves.append((f_suelo + 2 * k, p_pie, dyaw, math.pi / 2 + a_extra, ESPESOR + z_extra, math.radians(TORCER)))
    # --- empty: matriz por frame
    _claves_empty(emp, F_DESVIO + 1)
    M_E0 = emp.matrix_world.copy()
    piv0 = Vector((H0.x, H0.y, H0.z))
    ultimo = None
    for c in claves:
        f, p, gz, ang, alza = c[:5]; tw = c[5] if len(c) > 5 else 0.0
        Rz = Matrix.Rotation(gz + tw, 4, 'Z')
        T = Matrix.Translation(Vector((p.x, p.y, H0.z)) - piv0)
        M = T @ Matrix.Translation(piv0) @ Rz @ Matrix.Translation(-piv0) @ M_E0       # en pie, girado hacia la estalagmita
        if ang:
            hh = Vector((math.cos(yaw0 + gz + tw), math.sin(yaw0 + gz + tw), 0))         # rumbo del cuerpo ya girado
            eje = hh.cross(Vector((0, 0, 1))).normalized()
            talon = Vector((p.x, p.y, H0.z - 0.9)) + hh * 0.05                          # pivote: los talones en el suelo
            M = Matrix.Translation(talon) @ Matrix.Rotation(ang, 4, eje) @ Matrix.Translation(-talon) @ M
            M = Matrix.Translation((0, 0, alza)) @ M
        loc, rot, _ = M.decompose()
        if ultimo is not None and rot.dot(ultimo) < 0: rot.negate()
        ultimo = rot
        emp.location = loc; emp.rotation_quaternion = rot
        emp.keyframe_insert("location", frame=f); emp.keyframe_insert("rotation_quaternion", frame=f)
    # --- cuerpo: desde el choque piernas rectas y sin rebote; brazos y cabeza congelados con latigazo atras
    act = bpy.data.actions[PISTA_CORRE]
    for lay in act.layers:
        for s in lay.strips:
            for cb in s.channelbags:
                for fc in cb.fcurves:
                    nombre = fc.data_path.split('"')[1]; v_fi = fc.evaluate(fi)
                    for kp in reversed(list(fc.keyframe_points)):
                        if kp.co[0] > fi: fc.keyframe_points.remove(kp)
                    objetivo = v_fi
                    if nombre in ("RightUpLeg_alfred", "LeftUpLeg_alfred") and fc.array_index == 0: objetivo = 0.0 + _base_pierna(nombre)
                    elif nombre in ("Rightknee_alfred", "Leftknee_alfred") and fc.array_index == 0: objetivo = -0.08
                    elif nombre == "Neck_alfred" and fc.array_index == 0: objetivo = v_fi - 0.45
                    elif nombre == "Hips_alfred" and fc.data_path.endswith("location"): objetivo = fc.evaluate(F_DESVIO)  # sin rebote
                    elif nombre in BRAZOS: objetivo = _base_rot(nombre, fc.array_index)                               # baja los brazos al caer
                    pasos_u = ((fi + 4, 0.5), (fi + 10, 1.0), (F_FIN_ESCENA, 1.0)) if nombre in BRAZOS else ((fi + 2, 0.7), (fi + 5, 1.0), (F_FIN_ESCENA, 1.0))
                    for f, u in pasos_u:
                        fc.keyframe_points.insert(f, v_fi + (objetivo - v_fi) * u).interpolation = 'BEZIER'
                    fc.update()
    emp["f_choque"] = fi; emp["f_suelo"] = f_suelo
    sc.frame_set(fi)
    return {"desvio": F_DESVIO, "choque": fi, "cae": (f_cae0, f_suelo), "fin_escena": F_FIN_ESCENA}


BRAZOS = ("RightUpArm_alfred", "LeftUpArm_alfred", "Rightelbow_alfred", "Leftelbow_alfred")


def _base_rot(nombre, i):
    import json
    p = r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/poses/parado_mirando a la araña.json"
    d = json.load(open(p, encoding="utf8"))["poses"][0]["bones"][nombre]
    return math.radians(d["raw_rotation_euler_deg"]["xyz"[i]])


def _base_pierna(nombre):
    import json
    p = r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/poses/parado_mirando a la araña.json"
    d = json.load(open(p, encoding="utf8"))["poses"][0]["bones"][nombre]
    return math.radians(d["raw_rotation_euler_deg"]["x"])


def medir():
    """hueco (m) entre la arana y la estalagmita en el frame del choque (negativo = se meten)."""
    sc = bpy.context.scene; emp = bpy.data.objects["alfred"]; sc.frame_set(int(emp["f_choque"]))
    dg = bpy.context.evaluated_depsgraph_get(); mejor = 9.0
    piezas = [bpy.data.objects[n] for n in PIEZAS if n in bpy.data.objects]
    for o in bpy.data.collections["spider"].all_objects:
        if o.type != 'MESH': continue
        oe = o.evaluated_get(dg)
        for v in list(oe.data.vertices)[::3]:
            pw = oe.matrix_world @ v.co
            for pz in piezas:
                ok, loc, n, i = pz.closest_point_on_mesh(pz.matrix_world.inverted() @ pw)
                if ok:
                    d = (pz.matrix_world @ loc - pw).length
                    dentro = (pz.matrix_world.to_3x3() @ n).dot(pw - pz.matrix_world @ loc) < 0
                    mejor = min(mejor, -d if dentro else d)
    return round(mejor, 3)
