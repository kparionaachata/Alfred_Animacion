"""Aleteo desesperado ENCIMA del picoteo: las claves capturadas de aletear_1 del estudio (_keyframes_aletear_1, solo
alas Scapula/Shoulder/Elbow R/L, 64 f) en una capa NLA ADD por pollo, sin cortar el picoteo (que sigue debajo).
Ventanas en driver_namespace['_pollos_aleteos'] para sonidos y plumas."""
import bpy, importlib, sys
sys.path.insert(0, r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\chicken_1\refinar")
gs = importlib.import_module("chicken_1_animation_studio.generate_slots")
KF = {b: v for b, v in gs._keyframes_aletear_1().items() if not b.startswith("Chest")}
N = gs.FRAMES_ALETEAR
VENTANAS = {"chicken_1": [910, 980], "chicken_2": [918, 986], "chicken_3": [932]}   # inicio de cada aleteo (64 f)
FIN = bpy.context.scene.frame_end
out = {}
for n, inicios in VENTANAS.items():
    arm = bpy.data.objects["Armature_" + n]; ad = arm.animation_data
    nombre = "pollo_aleteo_encima_" + n
    for t in list(ad.nla_tracks):
        if t.name == "Pollo_aleteo_encima": ad.nla_tracks.remove(t)
    if nombre in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[nombre])
    act = bpy.data.actions.new(nombre); ad.action = act
    keep = {b: arm.pose.bones[b].rotation_euler.copy() for b in KF}
    ok = []
    for a in inicios:
        if a > FIN - 30: continue          # el ultimo aleteo puede cortarse con el fin de la animacion
        for b, kfs in KF.items():
            pb = arm.pose.bones[b]; pb.rotation_mode = "XYZ"
            for f, v in kfs.items():
                pb.rotation_euler = v; pb.keyframe_insert("rotation_euler", frame=a + f)
        ok.append((a, a + N - 1))
    sl = ad.action_slot; ad.action = None
    for b, r in keep.items(): arm.pose.bones[b].rotation_euler = r
    tr = ad.nla_tracks.new(); tr.name = "Pollo_aleteo_encima"
    st = tr.strips.new(act.name, int(act.frame_range[0]), act); st.action_slot = sl
    st.blend_type = "ADD"; st.extrapolation = "NOTHING"
    out[n] = ok
bpy.app.driver_namespace["_pollos_aleteos"] = out
result = out
