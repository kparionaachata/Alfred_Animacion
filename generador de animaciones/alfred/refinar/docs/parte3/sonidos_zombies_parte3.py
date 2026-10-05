"""SONIDOS DE LOS ZOMBIES (pedido de Kebyn): pasos sobre el pasto de los 5 zombies que rondan el refugio (f1094 en adelante) y los sonidos que hacen ellos (gemidos). Usa la biblioteca de `alfred_sonidos` (`colocar`).
Se ejecuta en Blender DESPUES de `zombies_rondan_parte3.py` (y de re-sincronizar voces / colocar el resto de sonidos); es repetible: borra antes las tiras `SND_zombie_*`.
  - PASOS: `block.grass.step` (step/grass1-6, el mismo pasto que los pasos de Alfred) en cada apoyo del pie: la pierna llega a su punto mas adelantado cuando la fase del ciclo (`2*pi*distancia/1.5 + PH0`) cruza pi/2 + m*pi. Misma
    formula que `zombies_rondan_parte3.py` (V, PH0, STRIDE, F0). Un apoyo por zombie cada ~0.75 m.
  - GEMIDOS: `entity.zombie.ambient` (mob/zombie/say1-3), escalonados: zombie_5 f1100, zombie_4 f1113, zombie_3 f1122, zombie_1 f1131, zombie_2 f1141, zombie_4 f1148.
  - Volumen y panorama segun la distancia / el lado respecto a la camara activa en ese frame (`Camera.001`): vol = (1 - d/16)^2 como en el juego (atenuacion lineal a 16 m, aqui al cuadrado) y pan = lado (-1 izquierda ... +1 derecha)."""
import bpy
import math
import random
import sys
from mathutils import Vector

sc = bpy.context.scene
mod = sys.modules.get("alfred_sonidos")
if mod is None:
    sys.path.insert(0, r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4"); import alfred_sonidos as mod; mod.register()
p = sc.mcsnd; ed = sc.sequence_editor
F0, N = 1094, sc.frame_end
STRIDE, V = 1.5, {1: 0.96, 2: 1.0, 3: 0.92, 4: 1.06, 5: 1.0}
PH0 = {1: 0.0, 2: 2.1, 3: 4.0, 4: 1.0, 5: 3.1}
ss = lambda t: (lambda u: u * u * (3 - 2 * u))(min(max(t, 0.0), 1.0))
GEMIDOS = [(5, 1100), (4, 1113), (3, 1122), (1, 1131), (2, 1141), (4, 1148)]
CAM = bpy.data.objects["Camera.001"]

for t in [t for t in mod._strips(ed) if t.name.startswith("SND_zombie_")]: mod._strips(ed).remove(t)           # repetible
rng = random.Random(11)
pasos = []
for n in range(1, 6):
    d = 0.0; prev = None
    for k in range(F0 - 4, N + 1):
        ph = 2 * math.pi * d / STRIDE + PH0[n]; c = math.floor((ph - math.pi / 2) / math.pi)
        if prev is not None and c > prev and k >= F0: pasos.append((k, n))
        prev = c; d += V[n] / 24.0 * ss((k - F0) / 10.0)
eventos = sorted([(k, n, "paso") for k, n in pasos] + [(k, n, "gemido") for n, k in GEMIDOS])
cuenta = {}
rg = mod.rutas_de(p, "block.grass.step"); rz = mod.rutas_de(p, "entity.zombie.ambient")
assert rg and rz, "no se encuentran los sonidos"
for k, n, tipo in eventos:
    sc.frame_set(k); bpy.context.view_layer.update()
    zc = bpy.data.objects["zombie_%d" % n].matrix_world.translation + Vector((0, 0, 1.0)); mw = CAM.matrix_world.inverted(); loc = mw @ zc; dist = (CAM.matrix_world.translation - zc).length
    atn = max(0.0, 1 - dist / 16.0) ** 2; lado = max(-1.0, min(1.0, math.atan2(loc.x, max(-loc.z, 0.01)) / math.radians(60)))
    t = mod.colocar(bpy.context, p, rg if tipo == "paso" else rz, k, "pasos" if tipo == "paso" else "voces", "zombie_%d_%s" % (n, tipo), volumen=(0.9 if tipo == "paso" else 1.0) * atn, rng=rng)
    try: t.pan = lado
    except Exception: pass
    t["zombie"] = n; cuenta[tipo] = cuenta.get(tipo, 0) + 1
sc.frame_set(1)
print("pasos:", cuenta.get("paso", 0), "gemidos:", cuenta.get("gemido", 0), "| por zombie:", {n: sum(1 for k, m in pasos if m == n) for n in range(1, 6)})
