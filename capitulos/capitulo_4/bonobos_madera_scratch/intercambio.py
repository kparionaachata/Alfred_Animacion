# -*- coding: utf-8 -*-
# Alfred lanza el pollo al mono 3, el mono lo atrapa y se lo devuelve a la cara de Alfred.
import bpy, math
from mathutils import Vector, Euler, Quaternion

P = r"C:\Users\user\AppData\Local\Temp\claude\C--Users-user-Desktop-Alfred-Animacion\593282e0-289f-4704-9bd2-cafc9b5be57b\scratchpad"
ns = {}
exec(open(P + r"\lanzar.py", encoding='utf-8').read(), ns)
lanzar, mano_pos, pose_mono, key_todo, mono, suf, yaw_hacia, dir_local, fcs, G = [ns[k] for k in ('lanzar', 'mano_pos', 'pose_mono', 'key_todo', 'mono', 'suf', 'yaw_hacia', 'dir_local', 'fcs', 'G_F')]
V = lambda x, y, z: Vector((x, y, z))
SC = bpy.context.scene
RA, T1, T2 = 721, 24, 23
TC = RA + T1                    # el mono atrapa
R2 = TC + 20                    # el mono suelta
C = R2 + T2                     # impacto en la cara (788)
YAW_ALF = -321.3                # Alfred gira hacia el mono 3 (grados)
alfred = bpy.data.objects['alfred']
arm_alf = [c for c in alfred.children if c.type == 'ARMATURE'][0]
chicken = bpy.data.objects['chicken_1']
MONO = (-76.5, 37.5, 21.0)


def sample(f, fn):
    SC.frame_set(f); bpy.context.view_layer.update()
    return fn()


def curva(a, path, idx):
    return [c for c in fcs(a) if c.data_path == path and c.array_index == idx][0]


def put(c, f, v, it='LINEAR'):
    k = c.keyframe_points.insert(f, v); k.interpolation = it
    return k
