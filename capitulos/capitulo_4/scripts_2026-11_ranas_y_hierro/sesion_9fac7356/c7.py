"""Sonidos del cerdo: pasos de cerdo (vanilla/mob/pig/step) en cada apoyo de pezuna al caminar, golpe de superficie al
aterrizar de los saltos, gruñidos (say) en las paradas y de vez en cuando."""
import bpy
sc = bpy.context.scene; ed = sc.sequence_editor
S = r"C:\Users\user\Desktop\Alfred_Animacion\sonidos\vanilla"
CAM = [(1, 75), (124, 161), (180, 279), (322, 371), (407, 444), (493, 504), (568, 655), (701, 738), (779, 840)]
SALTOS_FIN = [(179, "gravel"), (406, "grass"), (567, "grass"), (700, "grass")]
PARADAS = [(76, 123), (280, 321), (445, 492), (739, 778)]
for s in [s for s in ed.strips_all if s.name.startswith("SND_cerdo")]: ed.strips.remove(s)
root = bpy.data.objects["cerdo_1"]
legs = [bpy.data.objects[n] for n in ("pig.Leg-FR_cerdo_1", "pig.Leg-FL_cerdo_1", "pig.Leg-BR_cerdo_1", "pig.Leg-BL_cerdo_1")]
# altura minima de cada pata relativa al suelo (root z) por frame
serie = {i: {} for i in range(4)}
for a, b in CAM:
    for f in range(a, b + 1):
        sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); rz = round(root.matrix_world.translation.z)
        for i, o in enumerate(legs):
            e = o.evaluated_get(dg); m = e.to_mesh(); M = e.matrix_world
            serie[i][f] = min((M @ v.co).z for v in m.vertices) - rz; e.to_mesh_clear()
result={i:[round(serie[i][f],3) for f in range(180,230)] for i in range(4)}
