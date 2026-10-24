# -*- coding: utf-8 -*-
"""alfred_cueva_4.blend: 10 frames despues de quedar sentado contra la estalagmita, Alfred se levanta despacio diciendo
"Ay, pero que pendejo que eres, de verdad" (animacion_alfred (31).py de la app: mallas de los ojos + audio, con ojos_alfred_desde_script).
Se levanta en tres poses: sentado (la del usuario) -> recoge las piernas, se inclina y apoya las manos en las rodillas -> de pie.
Uso: exec(open(ruta, encoding="utf8").read()); construir(f_ini)      (despues de jerry_pica_carbon.construir())
"""
import bpy, math
from mathutils import Vector, Matrix

BASE = r"C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/"
SCRIPT_OJOS = BASE + "voces_alfred/animacion_alfred_pendejo.py"
AUDIO = BASE + "voces_alfred/alfred_pendejo.mp3"
ETIQUETA = "pendejo_levanta"
F_AGACHA, F_PARA = 30, 42          # sentado -> agachado con las manos en las rodillas -> de pie (despacio)
ADELANTE = 0.30                    # al ponerse de pie da medio paso adelante, separandose de la estalagmita


def suave(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def construir(f_ini):
    ns = {"__name__": "b"}; exec(open(BASE + "alfred_cae_estalagmita.py", encoding="utf8").read(), ns); B = ns
    H = {"__name__": "h"}; exec(open(BASE + "alfred_mete_carbon_horno.py", encoding="utf8").read(), H)
    sc = bpy.context.scene; O = bpy.data.objects; arm = O["Armature"]; emp = O["alfred"]; pb = arm.pose.bones; rig = B["Rig"]()
    ORDEN = B["ORDEN"]
    # pose sentada (lo que hay en f_ini)
    sc.frame_set(f_ini); P0 = {n: tuple(pb[n].rotation_euler) for n in ORDEN}; R0 = emp.location.copy()
    rz = math.radians(H["ROT_Z"]); R3 = Matrix.Rotation(rz, 3, 'Z'); fw = R3 @ Vector((0, 1, 0))
    pie = Vector((R0.x, R0.y, H["POS"].z)) + fw * ADELANTE
    M_root = Matrix.Translation(pie) @ R3.to_4x4()
    d0 = B["pose_torso"](0.03, 0.0); d0.update(B["piernas"](0.08, 0.05, -0.05))
    _, c0, _ = B["resolver_con_brazos"](rig, d0, aplicar=False)
    ref = (min(c0["Rightknee_alfred"].z, c0["Leftknee_alfred"].z) + B["SUELO_PIE"], (c0["Rightknee_alfred"].y + c0["Leftknee_alfred"].y) / 2)

    def pose_ik(th, cab, sep, cad, rod, Gd, Gi):
        dirs = B["pose_torso"](th, cab, 0.0); dirs.update(B["piernas"](sep, cad, rod))
        _, colas, _ = B["resolver_con_brazos"](rig, dirs, Gd, Gi, polo_d=(1, -0.4, -0.3), polo_i=(-1, -0.4, -0.3))
        piso = min(colas["Rightknee_alfred"].z, colas["Leftknee_alfred"].z) + B["SUELO_PIE"]
        yf = (colas["Rightknee_alfred"].y + colas["Leftknee_alfred"].y) / 2
        raiz = (Matrix.Translation(M_root.to_3x3() @ Vector((0, ref[1] - yf, ref[0] - piso))) @ M_root).to_translation()
        return {n: tuple(pb[n].rotation_euler) for n in ORDEN}, raiz
    # agachado: tronco muy inclinado, rodillas dobladas, manos en las rodillas
    P1, R1 = pose_ik(0.85, -0.35, 0.12, 1.25, -0.55, Vector((0.16, 0.42, 0.62)), Vector((-0.16, 0.42, 0.62)))
    # de pie, brazos sueltos, mirando hacia Jerry
    P2, R2 = pose_ik(0.06, -0.05, 0.08, 0.05, -0.05, Vector((0.24, 0.06, 0.82)), Vector((-0.24, 0.06, 0.82)))
    fin = f_ini + F_AGACHA + F_PARA
    sc.frame_end = max(sc.frame_end, fin + 30)
    mezcla = lambda a, b, w: {n: tuple(x + (y - x) * w for x, y in zip(a[n], b[n])) for n in a}
    for f in range(f_ini, sc.frame_end + 1):
        t = f - f_ini
        if t <= F_AGACHA:
            w = suave(t / F_AGACHA); P = mezcla(P0, P1, w); R = R0.lerp(R1, w)
            R.z += 0.06 * math.sin(math.pi * w)                       # el impulso para despegar del suelo
        else:
            w = suave((t - F_AGACHA) / F_PARA); P = mezcla(P1, P2, w); R = R1.lerp(R2, w)
        resp = 0.012 * math.sin(2 * math.pi * f / 48.0) * (1.0 if t > F_AGACHA else 0.5)   # respira agitado
        for n, e in P.items():
            pb[n].rotation_euler = e
            if n in ("Spine1_alfred", "Spine2_alfred"): pb[n].rotation_euler.x += resp
            pb[n].keyframe_insert("rotation_euler", frame=f)
        pb["Hips_alfred"].location = (0, 0, 0); pb["Hips_alfred"].keyframe_insert("location", frame=f)
        emp.location = R; emp.keyframe_insert("location", frame=f)
    # que ninguna parte del cuerpo se hunda en el suelo al recoger las piernas (la pose sentada del usuario se respeta en f_ini)
    piso = H["POS"].z; mallas = [O["Mesh_%d_alfred" % i] for i in range(6)]
    for f in range(f_ini + 1, sc.frame_end + 1):
        sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); zmin = 9e9
        for o in mallas:
            e = o.evaluated_get(dg); m = e.to_mesh(); zmin = min(zmin, min((o.matrix_world @ v.co).z for v in m.vertices)); e.to_mesh_clear()
        hundido = piso - zmin
        if hundido > 0.005:
            emp.location.z += hundido * min(1.0, (f - f_ini) / 6.0); emp.keyframe_insert("location", index=2, frame=f)
    # voz y ojos: empieza a hablar cuando empieza a levantarse
    J = {"__name__": "ojos"}; exec(open(BASE + "ojos_alfred_desde_script.py", encoding="utf8").read(), J)
    voz = J["aplicar"](SCRIPT_OJOS, AUDIO, f_ini, ETIQUETA)
    sc.frame_set(1)
    return {"levanta": (f_ini, fin), "voz": voz, "frame_end": sc.frame_end}
