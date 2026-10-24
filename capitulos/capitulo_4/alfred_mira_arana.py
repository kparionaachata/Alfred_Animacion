"""Alfred gira a mirar la arana 5 frames despues de que Jerry voltea (giro de alerta de Jerry en jerry_responde_pensando.GIRO_INI = 795).
Pose del usuario: `alfred/refinar/poses/parado_mirando a la arana.json` (solo los huesos que difieren de la animacion actual).
Capa NLA REPLACE `Alfred_mira_arana` en la armature `Armature`; el empty `alfred` no se mueve.
Uso (Blender):  exec(open(r"...\\alfred_mira_arana.py", encoding="utf8").read()); construir()      (repetible)
"""
import bpy, json, math

POSE_JSON = r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/poses/parado_mirando a la araña.json"
F_INI = 527 + 5            # Jerry voltea en 527
F_LLEGA = F_INI + 10       # ya en la pose
PISTA = "Alfred_mira_arana"


def construir():
    sc = bpy.context.scene; arm = bpy.data.objects["Armature"]; ad = arm.animation_data
    for t in list(ad.nla_tracks):
        if t.name == PISTA:
            acts = [s.action for s in t.strips]; ad.nla_tracks.remove(t)
            for a in acts:
                if a and a.users == 0: bpy.data.actions.remove(a)
    pose = json.load(open(POSE_JSON, encoding="utf8"))["poses"][0]["bones"]
    f_act = sc.frame_current; sc.frame_set(F_INI); fin = sc.frame_end; canales = {}
    for b, d in pose.items():
        pb = arm.pose.bones[b]
        e = [math.radians(d["raw_rotation_euler_deg"][a]) for a in "xyz"]; l = [d["raw_location"][a] for a in "xyz"]
        if max(abs(e[i] - pb.rotation_euler[i]) for i in range(3)) > 0.005 or max(abs(l[i] - pb.location[i]) for i in range(3)) > 1e-3:
            for i in range(3):
                canales[(f'pose.bones["{b}"].rotation_euler', i)] = e[i]
                canales[(f'pose.bones["{b}"].location', i)] = l[i]
    sc.frame_set(f_act)
    act = bpy.data.actions.get(PISTA)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(PISTA); slot = act.slots.new(arm.id_type, arm.name)
    cb = act.layers.new("Layer").strips.new(type='KEYFRAME').channelbags.new(slot)
    for (ruta, i), v in canales.items():
        fc = cb.fcurves.new(ruta, index=i); fc.keyframe_points.add(2)
        fc.keyframe_points[0].co = (F_INI, v); fc.keyframe_points[1].co = (fin, v); fc.update()
    tr = ad.nla_tracks.new(); tr.name = PISTA
    st = tr.strips.new(PISTA, F_INI, act); st.blend_type = 'REPLACE'; st.extrapolation = 'HOLD_FORWARD'
    try: st.action_slot = slot
    except Exception: pass
    st.use_animated_influence = True; fc = st.fcurves.find("influence")
    for kp in list(fc.keyframe_points): fc.keyframe_points.remove(kp)
    for f, v in ((F_INI, 0.0), (F_LLEGA, 1.0)): fc.keyframe_points.insert(f, v).interpolation = 'BEZIER'
    return {"frames": (F_INI, F_LLEGA), "huesos": sorted({r.split('"')[1] for r, _ in canales})}
