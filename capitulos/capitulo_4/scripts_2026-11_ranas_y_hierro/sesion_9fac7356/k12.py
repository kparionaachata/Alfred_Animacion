import bpy, math
from mathutils import Vector
sc=bpy.context.scene; sc.frame_set(1)
al=bpy.data.objects["Armature"]; pb=al.pose.bones
F=(al.matrix_world@pb["face_alfred"].matrix).to_3x3()
fw=[round(x,2) for x in F.col[2].normalized()]
d=(Vector((-76.47,-15.3,-9.85))-al.matrix_world@pb["face_alfred"].head)
r={"frente_cara":fw,"dir_hueco":[round(x,2) for x in d.normalized()],"dist":round(d.length,2),
   "cara":[round(x,3) for x in al.matrix_world@pb["face_alfred"].head],
   "hombro_der":[round(x,3) for x in al.matrix_world@pb["RightUpArm_alfred"].head],"codo":[round(x,3) for x in al.matrix_world@pb["Rightelbow_alfred"].head],
   "mano_tail":[round(x,3) for x in al.matrix_world@pb["Rightelbow_alfred"].tail],
   "rot_modes":{b:pb[b].rotation_mode for b in ("RightUpArm_alfred","Rightelbow_alfred","Spine1_alfred","Spine2_alfred","Neck_alfred","face_alfred","Hips_alfred")},
   "rots":{b:[round(math.degrees(x),1) for x in pb[b].rotation_euler] for b in ("RightUpArm_alfred","Rightelbow_alfred","Spine1_alfred")},
   "pies_z":round(min((o.matrix_world@v.co).z for o in [bpy.data.objects[n] for n in ("Mesh_4_alfred","Mesh_5_alfred")] for v in o.data.vertices),3)}
result=r
