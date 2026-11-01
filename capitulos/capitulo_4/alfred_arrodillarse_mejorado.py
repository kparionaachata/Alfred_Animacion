# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: arrodillarse de Alfred mejorado (reemplaza las claves 247-292 de la animacion Mixamo anterior).
Pose final = la del usuario `generador de animaciones/alfred/refinar/poses/arrodillarse_2.json` (rodilla derecha en el suelo, pierna izquierda
adelante). Fases: 247-256 anticipacion (se echa un poco hacia atras y toma aire), 256-278 descenso con retraso entre piernas / torso / brazos /
cabeza (pisa con la pierna izquierda, la rodilla derecha baja), 276-284 rebote al tocar la rodilla y 284-292 asentarse. El empty se queda en x,y;
solo baja su z (arriba -> 65.5486 de la pose). Todo escalado y repetible: lee la pose en F_INI desde las claves existentes la primera vez.
Uso: exec(open(ruta, encoding="utf8").read()); construir()
"""
import bpy, json, math
from bpy_extras import anim_utils

POSE = r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/poses/arrodillarse_2.json"
F_INI, F_FIN, F_LIMPIA = 252, 292, 247           # pose de partida (de pie), pose final, desde aqui se reemplazan las claves
ARM = "Armature"
HUESOS = ["Hips_alfred", "Spine_alfred", "Spine1_alfred", "Spine2_alfred", "Neck_alfred", "face_alfred", "RightUpArm_alfred", "Rightelbow_alfred",
          "LeftUpArm_alfred", "Leftelbow_alfred", "RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred"]
# (inicio, duracion) de cada grupo de huesos: las piernas se adelantan, el torso, los brazos y la cabeza siguen con retraso
TIEMPOS = {"LeftUpLeg_alfred": (256, 16), "Leftknee_alfred": (256, 16), "RightUpLeg_alfred": (258, 18), "Rightknee_alfred": (259, 18),
           "Hips_alfred": (258, 22), "Spine_alfred": (260, 20), "Spine1_alfred": (261, 20), "Spine2_alfred": (262, 20),
           "RightUpArm_alfred": (263, 22), "Rightelbow_alfred": (263, 22), "LeftUpArm_alfred": (262, 22), "Leftelbow_alfred": (262, 22),
           "Neck_alfred": (264, 22), "face_alfred": (265, 22)}
ANTICIPA = {"Hips_alfred": (-0.05, 0, 0), "Spine_alfred": (-0.07, 0, 0), "Spine1_alfred": (-0.08, 0, 0), "Neck_alfred": (0.06, 0, 0),
            "RightUpArm_alfred": (-0.12, 0, 0), "LeftUpArm_alfred": (-0.12, 0, 0)}     # radianes: se echa atras y toma aire


def _suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _asienta(t, sobre=0.06):
    """sube a 1 con un pequeno rebote al final"""
    t = max(0.0, min(1.0, t))
    return _suave(t) + sobre * math.sin(math.pi * t) * t * t


def _fcurvas(ob):
    a = ob.animation_data.action
    return anim_utils.action_get_channelbag_for_slot(a, ob.animation_data.action_slot).fcurves


def _limpia(ob, desde, filtro=None):
    for fc in _fcurvas(ob):
        if filtro and not filtro(fc.data_path):
            continue
        for i in range(len(fc.keyframe_points) - 1, -1, -1):
            if fc.keyframe_points[i].co.x >= desde:
                fc.keyframe_points.remove(fc.keyframe_points[i])


def construir():
    O, sc = bpy.data.objects, bpy.context.scene
    emp, arm = O["alfred"], O[ARM]
    pb = arm.pose.bones
    P = json.load(open(POSE, encoding="utf8"))["poses"][0]
    fin = {n: tuple(P["bones"][n]["local_space"]["rotation_euler_rad"][k] for k in "xyz") for n in HUESOS}
    loc_fin = {n: tuple(P["bones"][n]["local_space"]["location"][k] for k in "xyz") for n in HUESOS}
    z_fin = P["root"]["location"]["z"]
    sc.frame_set(F_INI)
    ini = {n: tuple(pb[n].rotation_euler) for n in HUESOS}
    loc_ini = {n: tuple(pb[n].location) for n in HUESOS}
    z_ini = emp.location.z
    for ob in (emp, arm):
        _limpia(ob, F_LIMPIA)
    for f in range(F_LIMPIA, F_FIN + 1):
        for n in HUESOS:
            a0, d = TIEMPOS[n]
            u = (f - a0) / d
            w = _suave(u) if n not in ("Rightknee_alfred", "RightUpLeg_alfred") else _asienta(u, 0.05)    # la rodilla derecha rebota un poco al tocar
            v = [ini[n][i] + (fin[n][i] - ini[n][i]) * w for i in range(3)]
            if f < F_LIMPIA + 10 and n in ANTICIPA:
                s = math.sin(math.pi * (f - F_LIMPIA) / 9.0)
                v = [v[i] + ANTICIPA[n][i] * s for i in range(3)]
            pb[n].rotation_mode = 'XYZ'
            pb[n].rotation_euler = v
            pb[n].keyframe_insert("rotation_euler", frame=f)
            if loc_fin[n] != (0.0, 0.0, 0.0):
                pb[n].location = tuple(loc_ini[n][i] + (loc_fin[n][i] - loc_ini[n][i]) * _suave((f - 258) / 20) for i in range(3))
                pb[n].keyframe_insert("location", frame=f)
        z = z_ini + (z_fin - z_ini) * _suave((f - 258) / 20) - 0.035 * math.sin(math.pi * max(0.0, min(1.0, (f - 276) / 8.0)))
        emp.location.z = z
        emp.keyframe_insert("location", index=2, frame=f)
    sc.frame_set(1)
    return dict(inicio=F_LIMPIA, final=F_FIN, z=(round(z_ini, 3), z_fin))
