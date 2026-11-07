"""La mano izquierda de Alfred agarra el mango de la pala (que lleva la derecha) en toda la animacion: IK temporal en
Leftelbow_alfred (cadena 2) con el objetivo ajustado para que la palma (punto (-0.04, 0.45, 0) del antebrazo) quede
sobre el mango, a MANGO_T del extremo del mango; se hornea frame a frame a rotaciones locales y se quita la IK."""
import bpy, math
from mathutils import Vector
from mathutils.geometry import intersect_point_line
sc = bpy.context.scene
al = bpy.data.objects["Armature"]; pb = al.pose.bones; pala = bpy.data.objects["stone_shovel"]
F0, F1 = 1, globals().get("FIN", 108)
MANGO_T = 0.45                               # 0 = extremo del mango, 1 = hoja
PALMA = Vector((-0.04, 0.45, 0.0))
A_, B_ = Vector((-0.31, -0.44, 0)), Vector((0.36, 0.29, 0))
act = al.animation_data.action; cb = act.layers[0].strips[0].channelbag(al.animation_data.action_slot)
for bn in ("LeftUpArm_alfred", "Leftelbow_alfred"):
    for i in range(3):
        fc = cb.fcurves.find('pose.bones["%s"].rotation_euler' % bn, index=i)
        if fc: cb.fcurves.remove(fc)
    pb[bn].rotation_mode = "XYZ"
emp = bpy.data.objects.new("_ik_izq_pala", None); sc.collection.objects.link(emp)
ik = pb["Leftelbow_alfred"].constraints.new("IK"); ik.name = "_IK_izq"; ik.target = emp; ik.chain_count = 2; ik.use_tail = True
palma = lambda: (al.matrix_world @ pb["Leftelbow_alfred"].matrix) @ PALMA
err = {}
for f in range(F0, F1 + 1):
    sc.frame_set(f)
    M = pala.matrix_world; objetivo = (M @ A_).lerp(M @ B_, MANGO_T)
    emp.location = objetivo + (al.matrix_world @ pb["Leftelbow_alfred"].tail - palma())
    for _ in range(8):
        bpy.context.view_layer.update()
        e = objetivo - palma()
        if e.length < 0.004: break
        emp.location = emp.location + e * 0.9
    bpy.context.view_layer.update()
    rots = {bn: al.convert_space(pose_bone=pb[bn], matrix=pb[bn].matrix, from_space="POSE", to_space="LOCAL").to_euler("XYZ", pb[bn].rotation_euler) for bn in ("LeftUpArm_alfred", "Leftelbow_alfred")}
    ik.mute = True
    for bn, r in rots.items(): pb[bn].rotation_euler = r; pb[bn].keyframe_insert("rotation_euler", frame=f)
    ik.mute = False
    err[f] = round((objetivo - palma()).length * 100, 1)
pb["Leftelbow_alfred"].constraints.remove(ik); bpy.data.objects.remove(emp)
for bn in ("LeftUpArm_alfred", "Leftelbow_alfred"):
    for i in range(3):
        fc = cb.fcurves.find('pose.bones["%s"].rotation_euler' % bn, index=i)
        for k in fc.keyframe_points: k.interpolation = "LINEAR"
# comprobar sin IK
chk = {}
for f in range(F0, F1 + 1, 8):
    sc.frame_set(f); M = pala.matrix_world
    q, l = intersect_point_line(palma(), M @ A_, M @ B_)
    chk[f] = (round((palma() - q).length * 100, 1), round(l, 2))
result = {"error_max_cm": max(err.values()), "control_dist_cm_y_posicion": chk}
