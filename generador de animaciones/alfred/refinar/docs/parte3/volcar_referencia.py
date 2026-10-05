# -*- coding: utf-8 -*-
"""FASE 0 del plan: congela la animacion de Alfred de `sentarse_en_refugio.py` como REFERENCIA NUMERICA (`datos_guion/base_referencia_alfred.json`).
SE EJECUTA EN BLENDER (exec; tarda unos minutos porque ejecuta el generador completo):  exec(open(r"...\\volcar_referencia.py", encoding="utf-8").read())
Guarda, por frame 1..N y SIN voces de Voz Sync (el generador no las conoce):
  raw     rotaciones (rad) de todos los huesos y ubicaciones (Hips, UpArm) tal como salen de `alfred_at` (antes del suavizado de curvas)
  final   lo mismo despues de `alfred_final` (suavizado de todo menos los brazos)
  ajuste  ubicacion de Hips aplicada MENOS la de `final` (contacto con el suelo: HYK / KZ, resuelto contra la malla en Blender)
  root    [x, y, z, yaw_grados] de `root_at`   |   micro  escala Z de Spine1
y deja el espacio de nombres del generador en `bpy.app.driver_namespace["gen_parte3"]` para depurar. Despues hay que volver a sincronizar las voces (`audio_import.aplicar_guion`)."""
import json
import os
import time

import bpy

RUTA = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\parte3"
GEN = os.path.join(RUTA, "sentarse_en_refugio.py"); SALIDA = os.path.join(RUTA, "datos_guion", "base_referencia_alfred.json")
t0 = time.time(); bpy.context.scene.frame_set(1)
g = {"__name__": "__main__"}
exec(compile(open(GEN, encoding="utf-8").read(), GEN, "exec"), g)
bpy.app.driver_namespace["gen_parte3"] = g
N = g["N"]; PA = g["PA"]; r6 = lambda v: round(float(v), 7)
raw_r, raw_l, fin_r, fin_l, root, micro, adj = {}, {}, {}, {}, [], [], []
for k in range(1, N + 1):
    r, l = g["alfred_at"](k); f, fl = g["alfred_final"](k)
    for b, v in r.items(): raw_r.setdefault(b, []).append([r6(x) for x in v])
    for b, v in l.items(): raw_l.setdefault(b, []).append([r6(x) for x in v])
    for b, v in f.items(): fin_r.setdefault(b, []).append([r6(x) for x in v])
    for b, v in fl.items(): fin_l.setdefault(b, []).append([r6(x) for x in v])
    x, y, z, yaw = g["root_at"](k); root.append([r6(x), r6(y), r6(z), r6(yaw)]); micro.append(r6(g["micro_scale"](k)))
    g["apply_alfred"](k, key=False); h = fl["Hips_alfred"]; ap = PA["Hips_alfred"].location; adj.append([r6(ap[i] - h[i]) for i in range(3)])
bpy.context.scene.frame_set(1)
out = {"version": 1, "fuente": "docs/parte3/sentarse_en_refugio.py", "N": N, "fps": 24, "creado": time.strftime("%Y-%m-%dT%H:%M:%S"), "nota": "referencia numerica de Alfred sin voces; rotaciones en radianes",
       "raw": {"rot": raw_r, "loc": raw_l}, "final": {"rot": fin_r, "loc": fin_l}, "ajuste_hips": adj, "root": root, "micro": micro}
os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
with open(SALIDA + ".tmp", "w", encoding="utf-8") as f: json.dump(out, f, separators=(",", ":"))
os.replace(SALIDA + ".tmp", SALIDA)
print("referencia guardada: %s (%d frames, %d huesos, %.0f s, %.1f MB)" % (SALIDA, N, len(raw_r), time.time() - t0, os.path.getsize(SALIDA) / 1e6))
