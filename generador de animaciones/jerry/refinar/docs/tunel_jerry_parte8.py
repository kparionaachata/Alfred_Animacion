# -*- coding: utf-8 -*-
"""Parte 8: Jerry sigue a Alfred por el tunel que este va cavando (`alfred/refinar/docs/parte8/tunel_alfred_parte8.py`).
- Empieza en f1 a 2 m detras de Alfred (este, x -102.5) mirando al oeste; mientras Alfred cava se queda quieto mirandolo (cola moviendose suave) y, cuando la distancia pasa de 3.2 m, trota hacia el oeste (ciclo de CORRER de Jerry, 12 f, 10 f por bloque)
  hasta quedar a 2.3 m de Alfred. Sigue la linea central del tunel (la de las columnas del plan), siempre dentro de lo ya cavado.
- Sin `scull` en las rotaciones (la cabeza queda quieta; solo cuerpo, patas, cola y orejas del ciclo) y sin sonidos / parpadeos / filtros (no pedidos).
Se ejecuta DENTRO de Blender con exec despues de `tunel_alfred_parte8.py` (usa su linea de tiempo). Repetible."""
import bpy, math, json
from mathutils import Vector

DOCS = "C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/jerry/refinar/"
ALF = "C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/parte8/tunel_alfred_parte8.py"
sc = bpy.context.scene
ga = {"__name__": "x"}; exec(open(ALF, encoding="utf-8").read(), ga); FIN = ga["construir"](); TLA = ga["TL"]; COLS = ga["COLS"]; CYm = ga["CY"]
g = {"__name__": "x"}; exec(open(DOCS + "docs/jerry_recorrido_parte7.py", encoding="utf-8").read().split("# ---------------- construccion")[0], g)
g["CL"] = 12; g["HALF"] = 6; g["RM"] = {"leg": 1.3, "leg_front": 1.3, "spine": 1.0, "tail": 1.5, "head": 0.0, "ear": 0.7}
pose_run, ss, mul = g["pose_run"], g["ss"], g["mul"]; root, arm = g["root"], g["arm"]
NB = [n for n in ["shoulder.L", "shoulder.R", "thigh.L", "thigh.R", "shin.L", "shin.R", "foot.L", "foot.R", "toe.L", "toe.R", "front_shoulder.L", "front_shoulder.R", "front_thigh.L", "front_thigh.R",
      "front_shin.L", "front_shin.R", "front_foot.L", "front_foot.R", "front_toe.L", "front_toe.R"] + ["spine_%d" % i for i in range(1, 8)] + ["tail_%d" % i for i in range(1, 4)] + ["ear.L", "ear.R"] if n in arm.pose.bones]
ZERO = (0.0, 0.0, 0.0); Z0 = 9.0; BOB = 0.03
FPB = 10.0; D_DES = 2.3; D_MAX = 3.2

def y_centro(x):                                                              # linea central del tunel: y de las columnas (centro de cada casilla), -69.5 fuera
    pts = [(-107.0, -69.5)] + [(c + 0.5, CYm[c] + 0.5) for c in COLS]
    if x >= pts[0][0]: return pts[0][1]
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        if xb <= x <= xa: return ya + (yb - ya) * (xa - x) / (xa - xb)
    return pts[-1][1]

# ---------------- linea de tiempo de Jerry ----------------
N = FIN + 12
JX = -102.5; fr = 0.0; mov = 0.0; rz = 90.0; TLJ = {}; wm = 0.0
for t in range(1, N + 1):
    a = TLA[min(t, FIN)]; ax, ay = a["x"], a["y"]
    d = JX - ax
    moving = (d > D_DES + 0.15) and (d > D_MAX or mov > 0.5)                  # arranca al pasar de D_MAX y sigue hasta quedar a D_DES
    mov = 1.0 if moving else 0.0
    wm += max(-1.0 / 5, min(1.0 / 5, mov - wm))                               # rampa de 5 f al arrancar y al parar
    if wm > 1e-3:
        step = 1.0 / FPB * wm; JX -= step; fr += wm
    JY = y_centro(JX)
    # rumbo: hacia donde anda (oeste, siguiendo la linea central) y, parado, mirando a Alfred
    fy = (y_centro(JX - 0.5) - JY) / 0.5
    rz_move = math.degrees(math.atan2(1.0, fy))                              # direccion (-1, fy): rz = atan2(-fx, fy)
    rz_look = math.degrees(math.atan2(-(ax - JX), (ay - JY)))
    objetivo = rz_move if wm > 0.3 else rz_look
    dz = objetivo - rz; dz = (dz + 180.0) % 360.0 - 180.0; rz += max(-6.0, min(6.0, dz))
    pr = pose_run(fr + 1); bob = BOB * (0.5 - 0.5 * math.cos(2 * math.pi * (fr % 12.0) / 12.0 * 2)) * ss(wm)
    pose = {n: mul(pr.get(n, ZERO), ss(wm)) for n in NB}
    for i in (1, 2, 3):                                                       # cola suave al estar parado
        v = list(pose["tail_%d" % i]); v[2] += 0.18 * (1 - ss(wm)) * math.sin(t * 0.13 + i * 0.5); pose["tail_%d" % i] = tuple(v)
    TLJ[t] = (JX, JY, Z0 + bob, rz, pose)

# ---------------- claves (acciones rapidas) ----------------
def accion(obj, nombre, canales, grupos=None):
    if obj.animation_data is None: obj.animation_data_create()
    ant = obj.animation_data.action; obj.animation_data.action = None
    if ant is not None and ant.users == 0: bpy.data.actions.remove(ant)
    a = bpy.data.actions.new(nombre); slot = a.slots.new(id_type='OBJECT', name=obj.name); layer = a.layers.new("Capa"); strip = layer.strips.new(type='KEYFRAME'); cb = strip.channelbag(slot, ensure=True)
    for (dp, i), pts in canales.items():
        gname = (grupos or {}).get(dp); fc = cb.fcurves.new(dp, index=i, group_name=gname) if gname else cb.fcurves.new(dp, index=i)
        fc.keyframe_points.add(len(pts)); fc.keyframe_points.foreach_set("co", [v for p in pts for v in p])
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
        fc.update()
    obj.animation_data.action = a; obj.animation_data.action_slot = slot
ts = sorted(TLJ)
accion(root, "tunel_jerry_root", {("location", 0): [(t, TLJ[t][0]) for t in ts], ("location", 1): [(t, TLJ[t][1]) for t in ts], ("location", 2): [(t, TLJ[t][2]) for t in ts], ("rotation_euler", 2): [(t, math.radians(TLJ[t][3])) for t in ts]})
can = {}
for n in NB:
    for ax in range(3): can[('pose.bones["%s"].rotation_euler' % n, ax)] = [(t, TLJ[t][4][n][ax]) for t in ts]
for pb in arm.pose.bones: pb.rotation_mode = 'XYZ'
accion(arm, "tunel_jerry_armature", can, grupos={k[0]: k[0].split('"')[1] for k in can})
sc.frame_set(1)
print("JERRY listo", N, "frames; x final", round(TLJ[N][0], 2), "y", round(TLJ[N][1], 2))
