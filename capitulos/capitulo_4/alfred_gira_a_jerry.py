# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: mientras Jerry le habla ("Como que esta aqui?", frame 680), Alfred rota a la siguiente posicion para poder verlo: la pose del usuario
`generador de animaciones/alfred/refinar/poses/arrillado_3.json` (empty a 139 deg, cadera y torso girados, cuello mirando a Jerry, brazo derecho adelante).
Transicion F_INI -> F_FIN con retrasos (primero cabeza y cuello, luego el empty / cuerpo y al final los brazos); se mantiene hasta el final de la escena.
Se SUMA a las claves existentes (respiracion y micro-movimiento de los filtros organicos siguen vivos): nuevo(f) = actual(f) + (pose - actual(F_INI)) * peso(f).
Uso en Blender: exec(open(ruta, encoding="utf8").read()); construir()      (NO repetible sin regenerar antes la animacion: se suma al estado actual)
"""
import bpy, json, math
from bpy_extras import anim_utils

POSE = r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/poses/arrillado_3.json"
DESP = 340                                     # los tiempos de abajo estan escritos para Jerry hablando en 342; se desplazan DESP frames (Jerry habla en 680, tras la frase de Alfred 627-658)
F_INI = 340
GRUPOS = {                                     # (inicio, duracion) del peso de cada grupo
    "cabeza": (343, 14, ("Neck_alfred", "face_alfred")),
    "cuerpo": (345, 18, ("Hips_alfred", "Spine_alfred", "Spine1_alfred", "Spine2_alfred", "RightUpLeg_alfred", "Rightknee_alfred", "LeftUpLeg_alfred", "Leftknee_alfred")),
    "brazos": (350, 16, ("RightUpArm_alfred", "Rightelbow_alfred", "LeftUpArm_alfred", "Leftelbow_alfred")),
}
F_RAIZ = (345, 18)                             # empty: yaw y ubicacion


def _w(f, ini, dur, desp=0):
    t = max(0.0, min(1.0, (f - ini - desp) / float(dur)))
    s = t * t * (3 - 2 * t)
    return s + 0.05 * math.sin(math.pi * t) * t * t              # pequeno sobrepaso al asentarse


def _canales(ob):
    a = ob.animation_data.action
    return anim_utils.action_get_channelbag_for_slot(a, ob.animation_data.action_slot)


def _aplicar(ob, cb, dp, idx, destino, peso, fin, f_ini=F_INI, signo=1.0):
    fc = cb.fcurves.find(dp, index=idx)
    if fc is None:
        fc = cb.fcurves.new(dp, index=idx)
    base = {f: (fc.evaluate(f) if len(fc.keyframe_points) else None) for f in range(f_ini, fin + 1)}
    if base[f_ini] is None:                                       # canal sin claves: valor estatico actual
        prop = dp.split(".")[-1]
        obj = ob.pose.bones[dp.split('"')[1]] if "pose.bones" in dp else ob
        v = getattr(obj, prop)[idx]
        base = {f: v for f in base}
    v0 = base[f_ini]
    for i in range(len(fc.keyframe_points) - 1, -1, -1):
        if fc.keyframe_points[i].co.x >= f_ini:
            fc.keyframe_points.remove(fc.keyframe_points[i])
    for f in range(f_ini, fin + 1):
        fc.keyframe_points.insert(f, base[f] + signo * (destino - v0) * peso(f), options={'FAST'}).interpolation = 'LINEAR'
    fc.update()


def construir(desp=None, deshacer=False, desp_viejo=0):
    """pone el giro con los tiempos desplazados `desp` frames (por omision DESP). deshacer=True QUITA un giro hecho antes con `desp_viejo`"""
    sc = bpy.context.scene
    O = bpy.data.objects
    P = json.load(open(POSE, encoding="utf8"))["poses"][0]
    fin = sc.frame_end
    arm, emp = O["Armature"], O["alfred"]
    cb_a, cb_e = _canales(arm), _canales(emp)
    d = (desp_viejo if deshacer else (DESP if desp is None else desp))
    signo = -1.0 if deshacer else 1.0
    fi = F_INI + d
    for nombre, (ini, dur, huesos) in GRUPOS.items():
        peso = lambda f, i=ini, du=dur: _w(f, i, du, d)
        for h in huesos:
            b = P["bones"][h]["local_space"]
            for i, a in enumerate("xyz"):
                _aplicar(arm, cb_a, 'pose.bones["%s"].rotation_euler' % h, i, b["rotation_euler_rad"][a], peso, fin, fi, signo)
            if h == "Hips_alfred":
                for i, a in enumerate("xyz"):
                    _aplicar(arm, cb_a, 'pose.bones["%s"].location' % h, i, b["location"][a], peso, fin, fi, signo)
    peso = lambda f: _w(f, F_RAIZ[0], F_RAIZ[1], d)
    r = P["root"]
    for i, a in enumerate("xyz"):
        _aplicar(emp, cb_e, "location", i, r["location"][a], peso, fin, fi, signo)
    _aplicar(emp, cb_e, "rotation_euler", 2, math.radians(r["rotation_euler_deg"]["z"]), peso, fin, fi, signo)
    sc.frame_set(1)
    return {"desde": fi, "pose_final_en": F_RAIZ[0] + F_RAIZ[1] + d, "deshecho": deshacer}
