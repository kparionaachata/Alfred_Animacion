# -*- coding: utf-8 -*-
"""Alfred planta la antorcha (-44.5,-15.5,-9.0) con el brazo derecho MIENTRAS empieza a levantarse (aun de rodillas), en vez de agacharse
despues de estar de pie (alfred_coloca_antorcha.py, que queda sustituido).
- Brazo: capa NLA REPLACE `Alfred_antorcha_levantandose` (RightUpArm + Rightelbow) resuelta con IK por frame hacia la antorcha (la mano la
  sostiene a ALTO_MANO del suelo); el resto del cuerpo sigue la animacion de levantarse. Entra F_ALCANZA..F_PLANTA, sale F_PLANTA..F_SUELTA.
- Antorcha (antorcha_1_colocada, luz y llama): aparece en F_PLANTA (se mueven sus claves de visibilidad).
- Se borran las claves del agachado anterior de la accion base (F_VIEJA..F_VIEJA_FIN) y la tira de sobarse la espalda empieza en F_SOBARSE.
Uso (Blender):  exec(open(r"...\\alfred_antorcha_levantandose.py", encoding="utf8").read()); construir()
"""
import bpy, math
from mathutils import Vector, Matrix

ANTORCHA = Vector((-44.5, -15.5, -9.0)); ALTO_MANO = 0.30
F_ALCANZA, F_PLANTA, F_SUELTA = 290, 302, 316
F_VIEJA, F_VIEJA_FIN = 455, 489          # agachado viejo (dentro de la accion base de Alfred)
F_SOBARSE = 455
OBJ_ANTORCHA = ("antorcha_1_colocada", "torch1.light", "torch_on.flame.001_1", "torch_on.main.001_1", "torch_on.smoke.001_1")
HUESOS = ("RightUpArm_alfred", "Rightelbow_alfred")
PISTA = "Alfred_antorcha_levantandose"


def _fcs(a):
    r = []
    for lay in a.layers:
        for st in lay.strips:
            for cb in st.channelbags: r += list(cb.fcurves)
    return r


def construir():
    sc = bpy.context.scene; f_act = sc.frame_current
    arm = bpy.data.objects["Armature"]; ad = arm.animation_data; emp = bpy.data.objects["alfred"]
    for t in list(ad.nla_tracks):
        if t.name == PISTA:
            a = [s.action for s in t.strips]; ad.nla_tracks.remove(t)
            for x in a:
                if x and x.users == 0: bpy.data.actions.remove(x)
    # 1) quitar el agachado viejo de la accion base (queda de pie con la pose del final de levantarse)
    base = ad.nla_tracks["Base_ArmatureAction.009"].strips[0]
    if emp.get("antorcha_vieja_quitada") is None:
        for fc in _fcs(base.action):
            for kp in reversed(list(fc.keyframe_points)):
                if F_VIEJA <= kp.co[0] <= F_VIEJA_FIN: fc.keyframe_points.remove(kp)
            fc.update()
        emp["antorcha_vieja_quitada"] = True
    # 2) sobarse la espalda empieza en cuanto termina de levantarse
    so = ad.nla_tracks["Postura_Alfred_sobarse_espalda"].strips[0]
    if so.frame_start != F_SOBARSE:
        d = F_SOBARSE - so.frame_start; so.frame_start_ui = F_SOBARSE
        for k in ("f_sobarse_espalda", "f_sobarse_espalda_pose", "f_sobarse_espalda_fin"):
            if k in emp: emp[k] = int(emp[k] + d)
    # 3) brazo derecho: IK por frame hacia la antorcha
    tgt = bpy.data.objects.new("tmp_ik_antorcha", None); sc.collection.objects.link(tgt); tgt.location = ANTORCHA + Vector((0, 0, ALTO_MANO))
    pb = arm.pose.bones["Rightelbow_alfred"]; c = pb.constraints.new('IK'); c.target = tgt; c.chain_count = 2
    claves = {}
    for f in range(F_ALCANZA - 2, F_SUELTA + 3):
        sc.frame_set(f)
        M = {h: arm.pose.bones[h].matrix.copy() for h in HUESOS + ("Spine2_alfred",)}
        for h in HUESOS:
            b = arm.data.bones[h]; par = b.parent
            Mp = M[par.name] if par.name in M else arm.pose.bones[par.name].matrix
            P = Mp @ par.matrix_local.inverted() @ b.matrix_local
            claves.setdefault(h, []).append((f, (P.inverted() @ M[h]).to_euler('XYZ')))
    pb.constraints.remove(c); bpy.data.objects.remove(tgt)
    act = bpy.data.actions.get(PISTA)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(PISTA); slot = act.slots.new(arm.id_type, arm.name)
    cb = act.layers.new("Layer").strips.new(type='KEYFRAME').channelbags.new(slot)
    for h, cl in claves.items():
        for i in range(3):
            fc = cb.fcurves.new(f'pose.bones["{h}"].rotation_euler', index=i); fc.keyframe_points.add(len(cl))
            for kp, (f, e) in zip(fc.keyframe_points, cl): kp.co = (f, e[i]); kp.interpolation = 'LINEAR'
            fc.update()
    tr = ad.nla_tracks.new(); tr.name = PISTA
    st = tr.strips.new(PISTA, F_ALCANZA - 2, act); st.blend_type = 'REPLACE'; st.extrapolation = 'NOTHING'
    try: st.action_slot = slot
    except Exception: pass
    st.use_animated_influence = True; fi = st.fcurves.find("influence")
    for kp in list(fi.keyframe_points): fi.keyframe_points.remove(kp)
    for f, v in ((F_ALCANZA, 0.0), (F_PLANTA, 1.0), (F_PLANTA + 3, 1.0), (F_SUELTA, 0.0)): fi.keyframe_points.insert(f, v).interpolation = 'BEZIER'
    # 4) la antorcha aparece al plantarla
    vieja = int(emp.get("f_antorcha", F_PLANTA)); d = F_PLANTA - vieja
    if d:
        for n in OBJ_ANTORCHA:
            o = bpy.data.objects.get(n)
            if o and o.animation_data and o.animation_data.action:
                for fc in _fcs(o.animation_data.action):
                    for kp in fc.keyframe_points: kp.co.x += d; kp.handle_left.x += d; kp.handle_right.x += d
                    fc.update()
    emp["f_antorcha"] = F_PLANTA; emp["f_antorcha_fin"] = F_SUELTA
    sc.frame_set(F_PLANTA); mano = arm.matrix_world @ arm.pose.bones["Rightelbow_alfred"].tail
    err = (mano - (ANTORCHA + Vector((0, 0, ALTO_MANO)))).length
    sc.frame_set(f_act)
    return {"planta": F_PLANTA, "mano_a_la_antorcha_m": round(err, 3), "sobarse_desde": F_SOBARSE}
