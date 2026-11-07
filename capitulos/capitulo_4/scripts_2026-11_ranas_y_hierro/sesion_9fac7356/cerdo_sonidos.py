"""Sonidos del cerdo: pasos de cerdo (vanilla/mob/pig/step) en cada apoyo de pezuna al caminar, golpe de superficie al
aterrizar de los saltos, gruñidos (say) en las paradas y de vez en cuando."""
import bpy
sc = bpy.context.scene; ed = sc.sequence_editor
S = r"C:\Users\user\Desktop\Alfred_Animacion\sonidos\vanilla"
CAM = [(1, 75), (124, 161), (180, 279), (322, 371), (407, 444), (493, 530), (566, 653), (699, 736), (777, 838)]
SALTOS_FIN = [(179, "gravel"), (406, "grass"), (565, "grass"), (698, "grass")]
PARADAS = [(76, 123), (280, 321), (445, 492), (737, 776)]
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
pasos = []
for i in range(4):
    alto = False
    for f in sorted(serie[i]):
        d = serie[i][f]
        if d > 0.024: alto = True
        elif d < 0.0065 and alto: pasos.append(f); alto = False
pasos = sorted(set(pasos)); _p = []
for f in pasos:
    if not _p or f - _p[-1] > 2: _p.append(f)
pasos = _p   # pares diagonales que apoyan juntos = un solo sonido
def libre(f, n=20, ch0=41):
    for ch in range(ch0, 128):
        if not any(s.channel == ch and s.frame_final_start < f + n and s.frame_final_end > f for s in ed.strips_all): return ch
def poner(nombre, ruta, f, vol):
    ch = libre(f); x = ed.strips.new_sound(nombre, ruta, ch, f); x.volume = vol; x["vol_base"] = vol; return x
for k, f in enumerate(pasos): poner("SND_cerdo_paso_%d" % f, S + r"\mob\pig\step%d.ogg" % (k % 5 + 1), f, 0.22)
for k, (f, sup) in enumerate(SALTOS_FIN):
    poner("SND_cerdo_aterriza_%d" % f, S + r"\step\%s%d.ogg" % (sup, k % 4 + 1), f, 0.4)
    poner("SND_cerdo_aterriza_paso_%d" % f, S + r"\mob\pig\step%d.ogg" % (k % 5 + 1), f, 0.35)
gru = [a + 8 for a, b in PARADAS] + [a + 30 for a, b in PARADAS if b - a > 44] + [40, 230, 620, 810]
for k, f in enumerate(sorted(gru)): poner("SND_cerdo_grune_%d" % f, S + r"\mob\pig\say%d.ogg" % (k % 3 + 1), f, 0.55)
DUCK = 0.56
exec(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\ducking_voces.py", encoding="utf-8").read(), {"__name__": "x", "DUCK": DUCK})
result = {"pasos": len(pasos), "sep_media": round((pasos[-1] - pasos[0]) / max(1, len(pasos) - 1), 1), "grunidos": sorted(gru),
          "total": len([s for s in ed.strips_all if s.name.startswith("SND_cerdo")])}
